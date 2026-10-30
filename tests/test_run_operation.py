import ast
import inspect
import re
from pathlib import Path

import pytest

from hilclaw import (
    build_log,
    check_operation,
    run_objective,
    run_operation,
    run_result,
    run_seed,
    tools,
)
from hilclaw.build_log import BuildLogUnwritable, HandOverRefused, LogKeeper
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.run_operation import (
    CONDITIONS,
    KIND_OPERATION_ANSWER_INVALID,
    OperationAnswerInvalid,
    Reported,
    ask,
)
from hilclaw.run_parameters import Bf16TimingParameters, TimingParameters

# Test values, not dimensions, a bound, a seed or a figure of the package.
SEED_MARKER = 918273645546372819
PARAMETERS = TimingParameters(
    m=3, k=4, n=5, n_max=9, sample_form="interval", seed=SEED_MARKER
)
REQUEST = {"run_id": "r1", "execution": 1}
HW_PROFILE = {"accelerator": "mock"}
MARKER = "zq7-marker-zq7"
BYTE_MARKER = MARKER.encode()
FIGURE_MARKER = 734251
PATH_MARKER = "zq7-path-zq7"
# A test value: nothing lies there, and no test makes it.
OUTPUT_PATH = Path(PATH_MARKER) / "runs" / "r1" / "output"
LOG_PATH = Path(PATH_MARKER) / "runs" / "r1" / "build-log.txt"
REPORT = b"report " + BYTE_MARKER
MESSAGE_LIMIT = 120


class Recording:
    def __init__(self, answer=None, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.error is not None:
            raise self.error
        return self.answer


def asked(operation, parameters=PARAMETERS, output_path=OUTPUT_PATH):
    return ask(
        operation,
        REQUEST,
        HW_PROFILE,
        parameters,
        output_path,
        LogKeeper(),
        log_path=LOG_PATH,
    )


def invalid(operation, parameters=PARAMETERS, output_path=OUTPUT_PATH):
    with pytest.raises(OperationAnswerInvalid) as caught:
        asked(operation, parameters, output_path)
    error = caught.value
    assert type(error) is OperationAnswerInvalid
    assert error.kind == "operation_answer_invalid"
    assert type(error.message) is str
    assert 0 < len(error.message) <= MESSAGE_LIMIT
    assert error.args == (error.message,)
    assert vars(error) == {"message": error.message}
    assert error.__cause__ is None
    assert error.__context__ is None
    for kept_out in (MARKER, PATH_MARKER, str(SEED_MARKER), str(FIGURE_MARKER)):
        assert kept_out not in error.message
    return error


def held_by_the_module(error):
    held = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename == run_operation.__file__:
            held.extend(traceback.tb_frame.f_locals.values())
        traceback = traceback.tb_next
    return held


def returned_message():
    return invalid(Recording(answer=object())).message


def raised_message():
    return invalid(Recording(error=LookupError())).message


class Unprintable:
    payload = MARKER

    def __repr__(self):
        raise RuntimeError(MARKER)

    __str__ = __repr__
    __eq__ = __repr__
    __hash__ = __repr__
    __len__ = __repr__
    __bool__ = __repr__


class Liar:
    @property
    def __class__(self):
        return tuple


class HostileMeta(type):
    @property
    def __name__(cls):
        raise RuntimeError(MARKER)

    def __eq__(cls, other):
        raise RuntimeError(MARKER)

    def __hash__(cls):
        raise RuntimeError(MARKER)

    def __repr__(cls):
        raise RuntimeError(MARKER)


class HostileValue(metaclass=HostileMeta):
    pass


class HostileError(Exception, metaclass=HostileMeta):
    def __str__(self):
        raise RuntimeError(MARKER)

    __repr__ = __str__

    def __getattribute__(self, name):
        raise RuntimeError(MARKER)


class OwnError(Exception):
    pass


class OwnFailure(tools.ToolFailure):
    pass


class Text(str):
    pass


class Whole(int):
    pass


class Pair(tuple):
    pass


class Report(bytes):
    pass


LongNameValue = type(MARKER + "V" * 10_000, (), {})
LongNameError = type(MARKER + "E" * 10_000, (Exception,), {})


NEITHER_FORM = [
    None,
    0,
    FIGURE_MARKER,
    True,
    1.5,
    REPORT,
    b"",
    (REPORT, 0),
    (REPORT, -FIGURE_MARKER),
    (REPORT, True),
    (REPORT, False),
    (REPORT, float(FIGURE_MARKER)),
    (REPORT, str(FIGURE_MARKER)),
    (REPORT, Whole(FIGURE_MARKER)),
    (MARKER, FIGURE_MARKER),
    (bytearray(REPORT), FIGURE_MARKER),
    (memoryview(REPORT), None),
    (Report(REPORT), None),
    (None, None),
    (REPORT,),
    (REPORT, FIGURE_MARKER, None),
    (),
    [REPORT, FIGURE_MARKER],
    Pair((REPORT, FIGURE_MARKER)),
    Reported(REPORT, FIGURE_MARKER),
    "report_form",
    "replay",
    "zero_interval",
    "pass",
    "",
    "time_limit ",
    "EXIT_STATUS",
    MARKER,
    Text("time_limit"),
    {"report": REPORT, "memory_bytes": FIGURE_MARKER},
    bytearray(REPORT),
    Unprintable(),
    Liar(),
    HostileValue(),
    LongNameValue(),
]

RAISED = [
    ValueError(MARKER),
    TypeError(MARKER),
    OSError(5, MARKER, PATH_MARKER),
    FileNotFoundError(2, MARKER),
    RuntimeError(MARKER),
    KeyError(MARKER),
    OwnError(MARKER),
    OperationAnswerInvalid(MARKER),
    check_operation.OperationAnswerInvalid(MARKER),
    HostileError(MARKER),
    LongNameError(MARKER),
    ExceptionGroup(MARKER, [ValueError(MARKER)]),
]

PASSED_ON = [
    tools.ToolFailure(tools.KIND_INVALID_REQUEST, MARKER),
    tools.ToolFailure("some_kind", MARKER),
    tools.ToolFailure(run_seed.KIND_SEED_NOT_DRAWN, MARKER),
    tools.ToolFailure(run_objective.KIND_OBJECTIVE_NOT_STATED, MARKER),
    tools.ToolFailure(run_objective.KIND_OBJECTIVE_NOT_COVERED, MARKER),
    tools.ToolFailure(KIND_OPERATION_ANSWER_INVALID, MARKER),
    OwnFailure("some_kind", MARKER),
    SystemExit(3),
    KeyboardInterrupt(),
    GeneratorExit(),
]


def by_index(values):
    names = [type.__dict__["__name__"].__get__(type(value))[:40] for value in values]
    return pytest.mark.parametrize("index", range(len(values)), ids=names)


def test_a_report_with_its_figure_is_reported_and_the_five_are_handed_as_they_are():
    operation = Recording(answer=(REPORT, FIGURE_MARKER))
    request = dict(REQUEST)
    hw_profile = dict(HW_PROFILE)
    parameters = TimingParameters(*PARAMETERS)
    output_path = Path(OUTPUT_PATH)
    keeper = LogKeeper()
    answer = ask(
        operation,
        request,
        hw_profile,
        parameters,
        output_path,
        keeper,
        log_path=LOG_PATH,
    )
    assert type(answer) is Reported
    assert answer == (REPORT, FIGURE_MARKER)
    assert answer.report is REPORT
    assert answer.memory_bytes == FIGURE_MARKER
    ((args, kwargs),) = operation.calls
    assert kwargs == {}
    assert len(args) == 5
    assert args[0] is request
    assert args[1] is hw_profile
    assert args[2] is parameters
    assert args[3] is output_path
    assert args[4] is keeper
    assert request == REQUEST
    assert hw_profile == HW_PROFILE
    assert parameters == PARAMETERS
    assert output_path == OUTPUT_PATH


@pytest.mark.parametrize(
    ("report", "figure"),
    [
        (REPORT, None),
        (b"", None),
        (b"", 1),
        (REPORT, 1),
        (REPORT, 2**53 + 1),
        (REPORT, 2**200),
    ],
)
def test_every_byte_string_in_a_pair_with_a_figure_or_none_is_reported(report, figure):
    operation = Recording(answer=(report, figure))
    answer = asked(operation)
    assert type(answer) is Reported
    assert answer.report is report
    assert answer.memory_bytes is figure or answer.memory_bytes == figure
    assert len(operation.calls) == 1


@pytest.mark.parametrize("condition", list(run_result.CONDITIONS[:4]))
def test_one_of_the_four_strings_is_returned_as_it_is(condition):
    operation = Recording(answer=condition)
    answer = asked(operation)
    assert type(answer) is str
    assert answer == condition
    assert len(operation.calls) == 1


@pytest.mark.parametrize(
    "output_path",
    [Path("elsewhere"), PATH_MARKER, b"output", None, 17, object()],
    ids=["path", "str", "bytes", "none", "int", "object"],
)
def test_the_output_path_is_handed_on_whatever_it_is(output_path):
    operation = Recording(answer="time_limit")
    assert asked(operation, output_path=output_path) == "time_limit"
    assert operation.calls[0][0][3] is output_path


def test_two_calls_call_twice_and_keep_nothing():
    before = dict(vars(run_operation))
    operation = Recording(answer=(REPORT, None))
    first = asked(operation)
    second = asked(operation)
    assert len(operation.calls) == 2
    assert first == second
    assert first is not second
    assert vars(run_operation) == before


@by_index(NEITHER_FORM)
def test_a_returned_value_of_neither_form_is_an_invalid_answer(index):
    answer = NEITHER_FORM[index]
    operation = Recording(answer=answer)
    error = invalid(operation)
    assert len(operation.calls) == 1
    assert error.message != raised_message()
    assert "returned" in error.message
    assert not any(value is answer for value in vars(error).values())
    held = held_by_the_module(error)
    assert not any(value is answer for value in held)
    if type(answer) is tuple:
        for part in answer:
            assert not any(value is part for value in held)


def test_a_returned_value_is_named_by_a_word_of_the_module_only():
    messages = {
        type(answer): invalid(Recording(answer=answer)).message
        for answer in (None, True, 0, 1.5, "", b"", bytearray(), [], (), {})
    }
    assert len(set(messages.values())) == len(messages)
    other = returned_message()
    assert other not in messages.values()
    for answer in (
        Unprintable(),
        HostileValue(),
        LongNameValue(),
        Text("time_limit"),
        Pair((REPORT, 1)),
        Reported(REPORT, 1),
        Liar(),
    ):
        assert invalid(Recording(answer=answer)).message == other
    assert invalid(Recording(answer="report_form")).message == messages[str]
    assert invalid(Recording(answer=(REPORT, 0))).message == messages[tuple]
    assert invalid(Recording(answer=(REPORT,))).message == messages[tuple]
    assert invalid(Recording(answer=REPORT)).message == messages[bytes]


@by_index(RAISED)
def test_a_raised_error_is_an_invalid_answer(index):
    raised = RAISED[index]
    operation = Recording(error=raised)
    error = invalid(operation)
    assert len(operation.calls) == 1
    assert error is not raised
    assert error.message != returned_message()
    assert "raised" in error.message
    assert not any(value is raised for value in vars(error).values())
    assert not any(value is raised for value in held_by_the_module(error))


def test_a_raised_error_is_named_by_a_word_of_the_module_only():
    messages = {
        kind: invalid(Recording(error=kind())).message
        for kind in (ValueError, TypeError, KeyError, OSError, RuntimeError)
    }
    assert len(set(messages.values())) == len(messages)
    other = raised_message()
    assert other not in messages.values()
    for raised in (
        HostileError(),
        LongNameError(),
        OwnError(),
        FileNotFoundError(),
        check_operation.OperationAnswerInvalid("x"),
    ):
        assert invalid(Recording(error=raised)).message == other


def test_the_returned_and_the_raised_messages_differ():
    assert returned_message() != raised_message()
    assert invalid(Recording(answer=None)).message != raised_message()
    assert invalid(Recording(error=ValueError())).message != returned_message()


def test_an_invalid_answer_inside_a_handler_shows_only_the_outer_error():
    raised = ValueError(MARKER)
    outer = LookupError()
    for operation in (Recording(error=raised), Recording(answer=(REPORT, 0))):
        with pytest.raises(OperationAnswerInvalid) as caught:
            try:
                raise outer
            except LookupError:
                asked(operation)
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is outer


@by_index(PASSED_ON)
def test_a_tool_failure_and_a_request_to_end_pass_through_as_they_are(index):
    raised = PASSED_ON[index]
    operation = Recording(error=raised)
    with pytest.raises(BaseException) as caught:
        asked(operation)
    assert caught.value is raised
    assert raised.__cause__ is None
    assert raised.__context__ is None
    assert len(operation.calls) == 1
    assert not isinstance(raised, OperationAnswerInvalid)


@pytest.mark.parametrize(
    "parameters",
    [
        None,
        tuple(PARAMETERS),
        PARAMETERS._asdict(),
        list(PARAMETERS),
        type("Derived", (TimingParameters,), {})(*PARAMETERS),
    ],
)
def test_parameters_of_another_type_are_refused_before_the_call(parameters):
    operation = Recording(answer=(REPORT, None))
    with pytest.raises(TypeError) as caught:
        asked(operation, parameters)
    assert type(caught.value) is TypeError
    assert operation.calls == []


def test_check_parameters_are_refused_before_the_call():
    operation = Recording(answer="time_limit")
    with pytest.raises(TypeError):
        asked(operation, CheckParameters(1, 2, 3, 4, 5))
    assert operation.calls == []


BF16_PARAMETERS = Bf16TimingParameters("rmsnorm", "bf16", (2, 3), 40, "interval", 9)


@pytest.mark.parametrize(
    "parameters",
    [
        Bf16CheckParameters(1, 2, "rmsnorm", "bf16", (2, 3)),
        tuple(BF16_PARAMETERS),
        BF16_PARAMETERS._asdict(),
        type("DerivedBf16", (Bf16TimingParameters,), {})(*BF16_PARAMETERS),
    ],
)
def test_bf16_lookalike_parameters_are_refused_before_the_call(parameters):
    operation = Recording(answer="time_limit")
    with pytest.raises(TypeError):
        asked(operation, parameters)
    assert operation.calls == []


def test_bf16_parameters_are_handed_on_as_the_same_object():
    operation = Recording(answer=(REPORT, None))
    assert asked(operation, BF16_PARAMETERS) == Reported(REPORT, None)
    ((args, _),) = operation.calls
    assert args[2] is BF16_PARAMETERS


@pytest.mark.parametrize("operation", [None, REPORT, "time_limit", 3, object()])
def test_an_operation_that_is_not_callable_is_refused(operation):
    with pytest.raises(TypeError) as caught:
        asked(operation)
    assert type(caught.value) is TypeError


def test_an_operation_that_takes_three_things_only_is_an_invalid_answer():
    called = []

    def of_three(request, hw_profile, parameters):
        called.append(parameters)
        return (REPORT, None)

    error = invalid(of_three)
    assert called == []
    assert error.message == invalid(Recording(error=TypeError())).message


def test_the_kind_is_the_checks_and_none_of_the_run_tools_others():
    assert KIND_OPERATION_ANSWER_INVALID == "operation_answer_invalid"
    assert (
        KIND_OPERATION_ANSWER_INVALID == check_operation.KIND_OPERATION_ANSWER_INVALID
    )
    assert KIND_OPERATION_ANSWER_INVALID not in run_objective.KINDS
    assert KIND_OPERATION_ANSWER_INVALID != run_seed.KIND_SEED_NOT_DRAWN
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", KIND_OPERATION_ANSWER_INVALID)
    assert KIND_OPERATION_ANSWER_INVALID not in tools.RESERVED_KINDS


def test_the_four_strings_are_the_first_four_conditions_of_a_result():
    assert CONDITIONS == run_result.CONDITIONS[:4]
    assert CONDITIONS == (
        "build_time_limit",
        "build_exit_status",
        "time_limit",
        "exit_status",
    )
    assert type(CONDITIONS) is tuple


def test_the_exception_is_the_modules_own_and_states_no_spend():
    assert OperationAnswerInvalid.__bases__ == (Exception,)
    assert OperationAnswerInvalid is not check_operation.OperationAnswerInvalid
    assert not issubclass(OperationAnswerInvalid, tools.ToolFailure)
    assert OperationAnswerInvalid.__module__ == "hilclaw.run_operation"
    assert OperationAnswerInvalid.kind == KIND_OPERATION_ANSWER_INVALID
    error = OperationAnswerInvalid("some text")
    assert error.kind == KIND_OPERATION_ANSWER_INVALID
    assert error.message == "some text"
    assert str(error) == "some text"
    assert not hasattr(error, "spend")


@pytest.mark.parametrize("message", [None, b"x", 3, Text("x")])
def test_the_exception_takes_a_str_only(message):
    with pytest.raises(TypeError) as caught:
        OperationAnswerInvalid(message)
    assert type(caught.value) is TypeError
    with pytest.raises(TypeError):
        OperationAnswerInvalid()


def test_a_tool_failure_can_be_built_from_it():
    error = invalid(Recording(answer=None))
    failure = tools.ToolFailure(error.kind, error.message)
    assert failure.error_object() == {
        "error": {"kind": "operation_answer_invalid", "message": error.message}
    }


def test_the_messages_are_constants_of_str():
    messages = [message for _, message in run_operation._VALUES + run_operation._ERRORS]
    messages += [run_operation._OTHER_VALUE, run_operation._OTHER_ERROR]
    assert all(type(message) is str for message in messages)
    assert len(set(messages)) == len(messages)


def test_reported_is_a_pair_of_two_named_fields():
    assert Reported._fields == ("report", "memory_bytes")
    assert Reported._field_defaults == {}
    assert Reported.__module__ == "hilclaw.run_operation"
    with pytest.raises(TypeError):
        Reported(REPORT)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    asked(Recording(answer=(REPORT, FIGURE_MARKER)))
    asked(Recording(answer="exit_status"))
    asked(Recording(answer=(REPORT, None)), output_path=tmp_path)
    invalid(Recording(answer="report_form"))
    invalid(Recording(error=OSError(2, MARKER, str(tmp_path))))
    with pytest.raises(tools.ToolFailure):
        asked(Recording(error=tools.ToolFailure("some_kind", "x")))
    with pytest.raises(SystemExit):
        asked(Recording(error=SystemExit(3)))
    with pytest.raises(TypeError):
        asked(Recording(answer="time_limit"), None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_four_only_and_has_no_entry():
    own = Path(run_operation.__file__)
    found = set()
    for node in ast.walk(ast.parse(own.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            found.add(module)
            found |= {f"{module}.{alias.name}" for alias in node.names}
    assert found == {
        "typing",
        "hilclaw",
        "hilclaw.build_log",
        "hilclaw.run_parameters",
        "hilclaw.tools",
    }
    assert not hasattr(run_operation, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(run_operation).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "CONDITIONS",
        "KIND_OPERATION_ANSWER_INVALID",
        "OperationAnswerInvalid",
        "Reported",
        "ask",
    }
    parameters = list(inspect.signature(ask).parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "operation",
        "request",
        "hw_profile",
        "parameters",
        "output_path",
        "keeper",
        "log_path",
    ]
    positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
    for parameter in parameters:
        assert parameter.default is inspect.Parameter.empty, parameter
        expected = (
            inspect.Parameter.KEYWORD_ONLY
            if parameter.name == "log_path"
            else positional
        )
        assert parameter.kind is expected, parameter


# The log keeper and the write of the log (ADR-0108 decisions 5 and 7)

LOG = "gemm.c:3:5: warning: unused variable ‘x’ ünïcode\r\nline two"


class Handing:
    """An operation that hands ``log`` to its keeper, then answers ``answer``."""

    def __init__(self, answer, log=LOG):
        self.answer = answer
        self.log = log
        self.keepers = []

    def __call__(self, request, hw_profile, parameters, output_path, keeper):
        self.keepers.append(keeper)
        keeper.hand_over(self.log)
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


def log_asked(operation, log_path, keeper=None):
    return ask(
        operation,
        REQUEST,
        HW_PROFILE,
        PARAMETERS,
        OUTPUT_PATH,
        LogKeeper() if keeper is None else keeper,
        log_path=log_path,
    )


HANDED_ANSWERS = [
    (REPORT, FIGURE_MARKER),
    "build_exit_status",
    None,
    ValueError(MARKER),
    tools.ToolFailure("compiler_unavailable", MARKER),
]


@pytest.mark.parametrize(
    "keeper", [None, object(), "keeper", type("Derived", (LogKeeper,), {})()]
)
def test_a_keeper_of_another_type_is_refused_before_the_call(tmp_path, keeper):
    operation = Recording(answer=(REPORT, None))
    with pytest.raises(TypeError) as caught:
        ask(
            operation,
            REQUEST,
            HW_PROFILE,
            PARAMETERS,
            OUTPUT_PATH,
            keeper,
            log_path=tmp_path / "log.txt",
        )
    assert type(caught.value) is TypeError
    assert operation.calls == []


@pytest.mark.parametrize("index", range(len(HANDED_ANSWERS)))
def test_a_handed_log_is_written_and_the_keeper_closed_whatever_came_back(
    tmp_path, index
):
    path = tmp_path / "a" / "b" / "build-log.txt"
    operation = Handing(HANDED_ANSWERS[index])
    try:
        log_asked(operation, path)
    except (tools.ToolFailure, OperationAnswerInvalid):
        pass
    assert path.read_bytes() == LOG.encode("utf-8")
    (keeper,) = operation.keepers
    assert keeper.held() == LOG
    with pytest.raises(HandOverRefused):
        keeper.hand_over("later")


def test_the_answer_is_kept_when_the_log_was_written(tmp_path):
    answer = log_asked(Handing((REPORT, FIGURE_MARKER)), tmp_path / "1.txt")
    assert answer == Reported(REPORT, FIGURE_MARKER)
    assert log_asked(Handing("time_limit"), tmp_path / "2.txt") == "time_limit"
    raised = tools.ToolFailure("compiler_unavailable", MARKER)
    with pytest.raises(tools.ToolFailure) as caught:
        log_asked(Handing(raised), tmp_path / "3.txt")
    assert caught.value is raised
    with pytest.raises(OperationAnswerInvalid):
        log_asked(Handing(None), tmp_path / "4.txt")


def test_an_empty_log_is_written_as_an_empty_file(tmp_path):
    path = tmp_path / "build-log.txt"
    assert log_asked(Handing("exit_status", log=""), path) == "exit_status"
    assert path.read_bytes() == b""


def test_nothing_handed_writes_nothing_and_closes_the_keeper(tmp_path):
    keeper = LogKeeper()
    path = tmp_path / "missing" / "build-log.txt"
    assert log_asked(Recording(answer="exit_status"), path, keeper) == "exit_status"
    assert keeper.held() is None
    assert not path.parent.exists()
    with pytest.raises(HandOverRefused):
        keeper.hand_over(LOG)


@pytest.mark.parametrize("index", range(len(HANDED_ANSWERS)))
def test_a_failed_write_raises_a_fresh_unwritable_in_place_of_any_answer(
    tmp_path, index
):
    path = tmp_path / "build-log.txt"
    path.write_bytes(b"taken")
    with pytest.raises(BuildLogUnwritable) as caught:
        log_asked(Handing(HANDED_ANSWERS[index]), path)
    error = caught.value
    assert type(error) is BuildLogUnwritable
    assert error.kind == "build_log_unwritable"
    assert error.__cause__ is None
    assert error.__context__ is None
    for kept_out in (MARKER, str(tmp_path), LOG):
        assert kept_out not in error.message
    assert path.read_bytes() == b"taken"


def test_a_refused_directory_is_unwritable(tmp_path):
    blocker = tmp_path / "attempt"
    blocker.write_bytes(b"a file where a directory is needed")
    with pytest.raises(BuildLogUnwritable):
        log_asked(Handing((REPORT, None)), blocker / "build-log.txt")


@pytest.mark.parametrize("ending", [KeyboardInterrupt(), SystemExit(3)])
def test_a_request_to_end_passes_and_writes_nothing(tmp_path, ending):
    path = tmp_path / "build-log.txt"
    operation = Handing(ending)
    with pytest.raises(BaseException) as caught:
        log_asked(operation, path)
    assert caught.value is ending
    assert not path.exists()
    with pytest.raises(HandOverRefused):
        operation.keepers[0].hand_over("later")


def test_an_unwritable_the_operation_raises_is_an_invalid_answer(tmp_path):
    error = invalid(Recording(error=BuildLogUnwritable(MARKER)))
    assert error.kind == KIND_OPERATION_ANSWER_INVALID
    assert list(tmp_path.iterdir()) == []


def test_a_second_hand_over_let_pass_is_an_invalid_answer_with_the_first_written(
    tmp_path,
):
    def twice(request, hw_profile, parameters, output_path, keeper):
        keeper.hand_over(LOG)
        keeper.hand_over("second")
        return (REPORT, None)

    path = tmp_path / "build-log.txt"
    with pytest.raises(OperationAnswerInvalid):
        log_asked(twice, path)
    assert path.read_bytes() == LOG.encode("utf-8")


@pytest.mark.parametrize("log", [LOG.encode(), None, 17, "\ud800"])
def test_a_refused_hand_over_let_pass_is_an_invalid_answer_and_writes_nothing(
    tmp_path, log
):
    path = tmp_path / "build-log.txt"
    with pytest.raises(OperationAnswerInvalid) as caught:
        log_asked(Handing((REPORT, None), log=log), path)
    assert caught.value.message == raised_message()
    assert not path.exists()


def test_a_refused_hand_over_caught_by_the_operation_keeps_its_answer(tmp_path):
    def caught(request, hw_profile, parameters, output_path, keeper):
        try:
            keeper.hand_over(b"bytes")
        except HandOverRefused:
            pass
        return "build_time_limit"

    path = tmp_path / "build-log.txt"
    assert log_asked(caught, path) == "build_time_limit"
    assert not path.exists()


def test_a_log_path_the_write_cannot_take_passes_through():
    with pytest.raises(TypeError):
        log_asked(Handing((REPORT, None)), None)


def test_the_kind_of_the_write_is_that_of_build_log():
    assert BuildLogUnwritable.kind == build_log.KIND_BUILD_LOG_UNWRITABLE
