import ast
import copy
import inspect
import io
import re
import struct
import tokenize
from pathlib import Path

import numpy as np
import pytest

from hilclaw import (
    check_answer,
    check_operation,
    check_result,
    contract_table,
    journaled_step,
    mock_check,
    tools,
)
from hilclaw.build_log import LogKeeper
from hilclaw.check_operation import (
    KIND_OPERATION_ANSWER_INVALID,
    OperationAnswerInvalid,
    ask,
)
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.harness.verification import END_MARK
from hilclaw.harness.verification_arrays import (
    VerificationArgumentError,
    check_value,
    draw_inputs,
    reference,
)

# Test values, not a seed, a number of draws, dimensions or a tolerance of the package.
SEED = 7
DRAWS = 3
SHAPE = {"m": 3, "k": 4, "n": 5}
PARAMETERS = CheckParameters(seed=SEED, draws=DRAWS, **SHAPE)
GEMM_ENTRY = contract_table.TABLE["gemm", "fp32", "row_major", "c"]
EXAMPLE_TOLERANCE = {"rtol": 1e-5, "atol": 1e-6}
OTHER_TOLERANCE = {"rtol": 0.5, "atol": 0.25}
REQUEST = {"run_id": "r1", "execution": 1}
HW_PROFILE = {"accelerator": "mock"}
MARKER = "zq7-marker-zq7"
PATH_MARKER = "zq7-path-zq7"
# A test value: nothing lies there, and no test makes it.
OUTPUT_PATH = Path(PATH_MARKER) / "runs" / "r1" / "output"
# A test value: nothing lies there, no test makes it, and no test hands over a log.
LOG_PATH = Path(PATH_MARKER) / "runs" / "r1" / "build-log.txt"
MESSAGE_LIMIT = 120


def rounded_references():
    outputs = []
    for draw in range(DRAWS):
        a, b = draw_inputs(**SHAPE, seed=SEED, draw=draw)
        outputs.append(reference(a, b).astype(np.float32))
    return outputs


def report_of(outputs):
    parts = []
    for draw, output in enumerate(outputs):
        value = check_value(*draw_inputs(**SHAPE, seed=SEED, draw=draw))
        parts.append(struct.pack("=I", value))
        parts.append(np.ascontiguousarray(output, dtype=np.float32).tobytes())
    return b"".join(parts) + END_MARK


def failing_report():
    outputs = rounded_references()
    outputs[1][2, 4] += np.float32(0.25)
    return report_of(outputs)


GOOD = report_of(rounded_references())


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


def expected(answer, parameters=PARAMETERS, tolerance=EXAMPLE_TOLERANCE):
    return check_answer.from_answer(answer, **parameters._asdict(), **tolerance)


def asked(
    operation,
    parameters=PARAMETERS,
    tolerance=EXAMPLE_TOLERANCE,
    output_path=OUTPUT_PATH,
):
    return ask(
        operation,
        REQUEST,
        HW_PROFILE,
        parameters,
        output_path,
        LogKeeper(),
        log_path=LOG_PATH,
        **tolerance,
    )


def invalid(
    operation,
    parameters=PARAMETERS,
    tolerance=EXAMPLE_TOLERANCE,
    output_path=OUTPUT_PATH,
):
    with pytest.raises(OperationAnswerInvalid) as caught:
        asked(operation, parameters, tolerance, output_path)
    error = caught.value
    assert type(error) is OperationAnswerInvalid
    assert error.kind == "operation_answer_invalid"
    assert type(error.message) is str
    assert 0 < len(error.message) <= MESSAGE_LIMIT
    assert error.args == (error.message,)
    assert vars(error) == {"message": error.message}
    assert error.__cause__ is None
    assert error.__context__ is None
    assert MARKER not in error.message
    assert PATH_MARKER not in error.message
    return error


def held_by_the_module(error):
    held = []
    traceback = error.__traceback__
    while traceback is not None:
        if traceback.tb_frame.f_code.co_filename == check_operation.__file__:
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


class Closed:
    def __getattribute__(self, name):
        raise RuntimeError(MARKER)


class Liar:
    @property
    def __class__(self):
        return bytes


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


class NamelessMeta(type):
    @property
    def __name__(cls):
        return 5


class HostileValue(metaclass=HostileMeta):
    pass


class NamelessValue(metaclass=NamelessMeta):
    pass


class HostileError(Exception, metaclass=HostileMeta):
    def __str__(self):
        raise RuntimeError(MARKER)

    __repr__ = __str__

    def __getattribute__(self, name):
        raise RuntimeError(MARKER)


LongNameError = type(MARKER + "E" * 10_000, (Exception,), {})
LongNameValue = type(MARKER + "V" * 10_000, (), {})


class PosingAsToolFailure(ValueError):
    @property
    def __class__(self):
        return tools.ToolFailure


class OwnFailure(tools.ToolFailure):
    pass


NEITHER_FORM = [
    "pass",
    None,
    "report_form",
    "check_value",
    "build_time_limit ",
    "BUILD_EXIT_STATUS",
    "build_exit",
    "build_status",
    "",
    0,
    True,
    1.5,
    {"outcome": "pass", MARKER: MARKER},
    [MARKER],
    (MARKER,),
    {MARKER},
    bytearray(GOOD),
    memoryview(GOOD),
    MARKER,
    MARKER * 800,
    "x" * 10_000,
    Unprintable(),
    Closed(),
    Liar(),
    HostileValue(),
    NamelessValue(),
    LongNameValue(),
    check_answer.NeitherFormError(MARKER),
]

RAISED = [
    ValueError(MARKER),
    TypeError(MARKER),
    RuntimeError(MARKER),
    KeyError(MARKER),
    OSError(5, MARKER, MARKER),
    FileNotFoundError(2, MARKER),
    MemoryError(),
    OverflowError(MARKER),
    VerificationArgumentError(MARKER),
    check_answer.NeitherFormError(MARKER),
    journaled_step.StepFailed({"x": 1}, "some_kind", MARKER),
    OperationAnswerInvalid(MARKER),
    HostileError(MARKER),
    LongNameError(MARKER),
    PosingAsToolFailure(MARKER),
    ExceptionGroup(MARKER, [ValueError(MARKER)]),
]

PASSED_ON = [
    tools.ToolFailure(tools.KIND_INVALID_REQUEST, MARKER),
    tools.ToolFailure("some_kind", MARKER),
    tools.ToolFailure(KIND_OPERATION_ANSWER_INVALID, MARKER),
    OwnFailure("some_kind", MARKER),
    SystemExit(3),
    KeyboardInterrupt(),
    GeneratorExit(),
]

BAD_PARAMETERS = [
    ("m", 0, ValueError),
    ("draws", 0, VerificationArgumentError),
    ("seed", -1, VerificationArgumentError),
]
BAD_TOLERANCE = [
    ("rtol", -0.1, VerificationArgumentError),
    ("atol", float("nan"), VerificationArgumentError),
]


def by_index(values):
    names = [type.__dict__["__name__"].__get__(type(value))[:40] for value in values]
    return pytest.mark.parametrize("index", range(len(values)), ids=names)


def imported_modules(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            found.add(module)
            found |= {f"{module}.{alias.name}" for alias in node.names}
    return found


def test_a_good_report_passes_and_the_operation_is_called_once_with_the_four():
    operation = Recording(answer=GOOD)
    request = dict(REQUEST)
    hw_profile = dict(HW_PROFILE)
    parameters = CheckParameters(seed=SEED, draws=DRAWS, **SHAPE)
    output_path = Path(OUTPUT_PATH)
    keeper = LogKeeper()
    result = ask(
        operation,
        request,
        hw_profile,
        parameters,
        output_path,
        keeper,
        log_path=LOG_PATH,
        **EXAMPLE_TOLERANCE,
    )
    assert result["outcome"] == "pass"
    assert result == expected(GOOD)
    assert type(result) is dict
    assert len(operation.calls) == 1
    args, kwargs = operation.calls[0]
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
    "output_path",
    [Path("elsewhere") / "output", Path(), PATH_MARKER, b"output", None, 17, object()],
    ids=["path", "empty_path", "str", "bytes", "none", "int", "object"],
)
@pytest.mark.parametrize("answer", [GOOD, "time_limit", "exit_status"])
def test_the_output_path_is_handed_on_whatever_it_is_and_changes_no_result(
    answer, output_path
):
    operation = Recording(answer=answer)
    result = asked(operation, output_path=output_path)
    assert result == expected(answer)
    ((args, kwargs),) = operation.calls
    assert kwargs == {}
    assert len(args) == 5
    assert args[3] is output_path
    assert type(args[4]) is LogKeeper


def test_an_output_path_that_cannot_be_read_is_handed_on_unread():
    output_path = Closed()
    operation = Recording(answer=GOOD)
    assert asked(operation, output_path=output_path) == expected(GOOD)
    assert operation.calls[0][0][3] is output_path
    invalid(Recording(answer=None), output_path=output_path)


def test_an_operation_that_takes_three_things_only_is_an_invalid_answer():
    called = []

    def of_three(request, hw_profile, parameters):
        called.append(parameters)
        return GOOD

    error = invalid(of_three)
    assert called == []
    assert error.message == invalid(Recording(error=TypeError())).message
    assert not any(value is OUTPUT_PATH for value in vars(error).values())


@pytest.mark.parametrize("output_path", [OUTPUT_PATH, str(OUTPUT_PATH), PATH_MARKER])
@pytest.mark.parametrize(
    "operation",
    [
        lambda: Recording(answer=None),
        lambda: Recording(answer="pass"),
        lambda: Recording(error=ValueError(MARKER)),
        lambda: Recording(error=OSError(2, "missing", PATH_MARKER)),
    ],
    ids=["none", "str", "value_error", "system_error"],
)
def test_an_invalid_answer_holds_nothing_of_the_output_path(operation, output_path):
    with pytest.raises(OperationAnswerInvalid) as caught:
        asked(operation(), output_path=output_path)
    error = caught.value
    assert error.__cause__ is None
    assert error.__context__ is None
    assert error.args == (error.message,)
    assert vars(error) == {"message": error.message}
    assert PATH_MARKER not in error.message
    assert PATH_MARKER not in str(error)
    assert PATH_MARKER not in repr(error)


def test_a_report_with_one_element_off_fails():
    report = failing_report()
    result = asked(Recording(answer=report))
    assert result["outcome"] == "fail"
    assert result == expected(report)


@pytest.mark.parametrize(
    "condition", ["time_limit", "exit_status", "build_time_limit", "build_exit_status"]
)
def test_one_of_the_four_strings_gives_the_broken_result(condition):
    result = asked(Recording(answer=condition))
    assert result["outcome"] == "broken"
    assert result["condition"] == condition
    assert result == expected(condition)


def test_the_default_script_of_the_mock_passes():
    operation = mock_check.operation(mock_check.default_script)
    result = asked(operation)
    assert result["outcome"] == "pass"
    assert result["shape"] == SHAPE
    assert result["draws"] == DRAWS


@pytest.mark.parametrize(("name", "value"), [("m", 0), ("draws", 0), ("seed", -1)])
def test_an_error_of_the_default_script_is_an_invalid_answer(name, value):
    parameters = PARAMETERS._replace(**{name: value})
    error = invalid(mock_check.operation(mock_check.default_script), parameters)
    assert error.message == raised_message()


@pytest.mark.parametrize("report", [GOOD[:-1], b"", GOOD + b"\x00"])
def test_a_report_cut_short_is_a_broken_result_and_no_exception(report):
    result = asked(Recording(answer=report))
    assert result["outcome"] == "broken"
    assert result["condition"] == "report_form"
    assert result == expected(report)


@pytest.mark.parametrize("answer", [GOOD, failing_report(), b"", "exit_status"])
def test_two_calls_call_twice_and_give_equal_and_distinct_results(answer):
    operation = Recording(answer=answer)
    first = asked(operation)
    second = asked(operation)
    assert len(operation.calls) == 2
    assert first == second
    assert first is not second
    kept = copy.deepcopy(second)
    first["outcome"] = "changed"
    first["shape"]["m"] = 99
    assert second == kept


@pytest.mark.parametrize("answer", [GOOD, "time_limit"])
def test_the_tolerance_reaches_the_result(answer):
    result = asked(Recording(answer=answer), tolerance=OTHER_TOLERANCE)
    assert result["tolerance"] == OTHER_TOLERANCE
    assert result == expected(answer, tolerance=OTHER_TOLERANCE)


def test_the_five_values_reach_the_result():
    parameters = CheckParameters(seed=SEED, draws=5, m=2, k=3, n=4)
    result = asked(Recording(answer="time_limit"), parameters)
    assert result["shape"] == {"m": 2, "k": 3, "n": 4}
    assert result["draws"] == 5
    assert result == check_result.v2_broken(
        "time_limit", GEMM_ENTRY, (2, 3, 4), draws=5, **EXAMPLE_TOLERANCE
    )


@by_index(NEITHER_FORM)
def test_a_returned_value_of_neither_form_is_an_invalid_answer(index):
    answer = NEITHER_FORM[index]
    operation = Recording(answer=answer)
    error = invalid(operation)
    assert len(operation.calls) == 1
    assert error.message != raised_message()
    if type(answer) is str and len(answer) > 3:
        assert answer not in error.message
    assert not any(value is answer for value in vars(error).values())
    assert not any(value is answer for value in held_by_the_module(error))


def test_a_returned_value_is_named_by_a_word_of_the_module_only():
    messages = {
        type(answer): invalid(Recording(answer=answer)).message
        for answer in (None, True, 0, 1.5, "", bytearray(), [], (), {})
    }
    assert len(set(messages.values())) == len(messages)
    other = returned_message()
    assert other not in messages.values()
    for answer in (Unprintable(), HostileValue(), LongNameValue(), {1}, 1j):
        assert invalid(Recording(answer=answer)).message == other
    assert invalid(Recording(answer="pass")).message == messages[str]
    assert invalid(Recording(answer="x" * 10_000)).message == messages[str]
    assert invalid(Recording(answer=[MARKER])).message == messages[list]


@pytest.mark.parametrize(
    "answer", ["build_exit", "build_time_limit ", "report_form", "check_value"]
)
def test_a_returned_str_near_a_condition_is_shown_by_its_type_only(answer):
    message = invalid(Recording(answer=answer)).message
    assert message == invalid(Recording(answer="pass")).message
    assert "four conditions" in message
    assert answer.strip() not in message
    assert "build" not in message


@by_index(RAISED)
def test_a_raised_error_is_an_invalid_answer(index):
    raised = RAISED[index]
    operation = Recording(error=raised)
    error = invalid(operation)
    assert len(operation.calls) == 1
    assert error is not raised
    assert error.message != returned_message()
    assert not any(value is raised for value in vars(error).values())
    assert not any(value is raised for value in held_by_the_module(error))
    assert not hasattr(error, "spend")


def test_a_raised_error_is_named_by_a_word_of_the_module_only():
    messages = {
        kind: invalid(Recording(error=kind())).message
        for kind in (ValueError, TypeError, KeyError, OSError, MemoryError)
    }
    assert len(set(messages.values())) == len(messages)
    other = raised_message()
    assert other not in messages.values()
    for raised in (
        HostileError(),
        LongNameError(),
        FileNotFoundError(),
        OperationAnswerInvalid("x"),
        journaled_step.StepFailed({}, "some_kind", "x"),
    ):
        assert invalid(Recording(error=raised)).message == other
    assert invalid(Recording(error=ValueError(MARKER))).message == messages[ValueError]


def test_an_invalid_answer_inside_a_handler_does_not_show_the_raised_error():
    raised = ValueError(MARKER)
    outer = LookupError()
    with pytest.raises(OperationAnswerInvalid) as caught:
        try:
            raise outer
        except LookupError:
            asked(Recording(error=raised))
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
        type("Derived", (CheckParameters,), {})(*PARAMETERS),
    ],
)
def test_parameters_of_another_type_are_refused_before_the_call(parameters):
    operation = Recording(answer=GOOD)
    with pytest.raises(TypeError) as caught:
        asked(operation, parameters)
    assert type(caught.value) is TypeError
    assert operation.calls == []


@pytest.mark.parametrize("operation", [None, GOOD, "time_limit", 3, object()])
def test_an_operation_that_is_not_callable_is_refused(operation):
    with pytest.raises(TypeError) as caught:
        asked(operation)
    assert type(caught.value) is TypeError


def test_the_call_itself_is_checked_by_python():
    operation = Recording(answer=GOOD)
    four = (operation, REQUEST, HW_PROFILE, PARAMETERS)
    five = (*four, OUTPUT_PATH, LogKeeper())
    tolerance = {**EXAMPLE_TOLERANCE, "log_path": LOG_PATH}
    cases = [
        ((operation, REQUEST, HW_PROFILE), tolerance),
        (four, tolerance),
        (five, {"rtol": 1e-5, "log_path": LOG_PATH}),
        (five, {"atol": 1e-6, "log_path": LOG_PATH}),
        ((*five, 1e-5, 1e-6), {"log_path": LOG_PATH}),
        ((*five, 1e-5), {"atol": 1e-6, "log_path": LOG_PATH}),
        (five, {**tolerance, "draws": 3}),
        (five, {**tolerance, "output_path": OUTPUT_PATH}),
    ]
    for args, kwargs in cases:
        with pytest.raises(TypeError) as caught:
            ask(*args, **kwargs)
        assert type(caught.value) is TypeError
    assert operation.calls == []


@pytest.mark.parametrize(("name", "value", "raised"), BAD_PARAMETERS)
def test_a_bad_value_of_the_five_beside_a_report_is_the_callers_own(
    name, value, raised
):
    parameters = PARAMETERS._replace(**{name: value})
    operation = Recording(answer=GOOD)
    with pytest.raises(raised) as caught:
        asked(operation, parameters)
    assert type(caught.value) is raised
    assert not isinstance(caught.value, OperationAnswerInvalid)
    with pytest.raises(raised) as direct:
        expected(GOOD, parameters)
    assert str(caught.value) == str(direct.value)
    assert len(operation.calls) == 1
    invalid(Recording(answer="pass"), parameters)


@pytest.mark.parametrize(("name", "value", "raised"), BAD_TOLERANCE)
def test_a_bad_tolerance_beside_a_report_is_the_callers_own(name, value, raised):
    tolerance = {**EXAMPLE_TOLERANCE, name: value}
    with pytest.raises(raised) as caught:
        asked(Recording(answer=GOOD), tolerance=tolerance)
    assert type(caught.value) is raised
    assert not isinstance(caught.value, OperationAnswerInvalid)
    with pytest.raises(ValueError) as beside_a_condition:
        asked(Recording(answer="time_limit"), tolerance=tolerance)
    assert not isinstance(beside_a_condition.value, OperationAnswerInvalid)
    invalid(Recording(answer="pass"), tolerance=tolerance)


def test_only_bytes_and_str_are_handed_to_the_judging(monkeypatch):
    handed = []

    def recording(answer, **arguments):
        handed.append(answer)
        raise check_answer.NeitherFormError(MARKER)

    monkeypatch.setattr(check_answer, "from_answer", recording)
    for answer in (None, 0, bytearray(GOOD), HostileValue(), Liar()):
        invalid(Recording(answer=answer))
    assert handed == []
    invalid(Recording(answer=GOOD))
    invalid(Recording(answer="pass"))
    assert handed == [GOOD, "pass"]


def test_an_error_of_the_judging_is_not_taken_for_a_raised_error(monkeypatch):
    raised = RuntimeError(MARKER)

    def broken_judging(answer, **arguments):
        raise raised

    monkeypatch.setattr(check_answer, "from_answer", broken_judging)
    with pytest.raises(RuntimeError) as caught:
        asked(Recording(answer=GOOD))
    assert caught.value is raised


def test_the_kind_is_a_name_and_not_reserved():
    assert KIND_OPERATION_ANSWER_INVALID == "operation_answer_invalid"
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", KIND_OPERATION_ANSWER_INVALID)
    assert KIND_OPERATION_ANSWER_INVALID not in tools.RESERVED_KINDS
    tools.ToolFailure(KIND_OPERATION_ANSWER_INVALID, "x")


def test_the_exception_is_the_modules_own_and_states_no_spend():
    assert OperationAnswerInvalid.__bases__ == (Exception,)
    assert not issubclass(
        OperationAnswerInvalid, (tools.ToolFailure, journaled_step.StepFailed)
    )
    assert OperationAnswerInvalid.__module__ == "hilclaw.check_operation"
    assert OperationAnswerInvalid.kind == KIND_OPERATION_ANSWER_INVALID
    assert not hasattr(OperationAnswerInvalid, "spend")
    error = OperationAnswerInvalid("some text")
    assert error.kind == KIND_OPERATION_ANSWER_INVALID
    assert error.message == "some text"
    assert str(error) == "some text"
    assert not hasattr(error, "spend")


@pytest.mark.parametrize("message", [None, b"x", 3, type("Text", (str,), {})("x")])
def test_the_exception_takes_a_str_only(message):
    with pytest.raises(TypeError) as caught:
        OperationAnswerInvalid(message)
    assert type(caught.value) is TypeError
    with pytest.raises(TypeError):
        OperationAnswerInvalid()


@pytest.mark.parametrize(
    "operation", [Recording(answer=None), Recording(error=ValueError(MARKER))]
)
def test_a_tool_failure_and_a_failed_step_can_be_built_from_it(operation):
    error = invalid(operation)
    failure = tools.ToolFailure(error.kind, error.message)
    assert failure.error_object() == {
        "error": {"kind": "operation_answer_invalid", "message": error.message}
    }
    # The empty spend is this test's example, no rule.
    failed = journaled_step.StepFailed({}, error.kind, error.message)
    assert (failed.kind, failed.message) == (error.kind, error.message)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    asked(Recording(answer=GOOD))
    asked(Recording(answer=GOOD[:-1]))
    asked(Recording(answer="time_limit"))
    asked(mock_check.operation(mock_check.default_script))
    invalid(Recording(answer="pass"))
    invalid(Recording(error=ValueError(MARKER)))
    with pytest.raises(tools.ToolFailure):
        asked(Recording(error=tools.ToolFailure("some_kind", "x")))
    with pytest.raises(SystemExit):
        asked(Recording(error=SystemExit(3)))
    with pytest.raises(TypeError):
        asked(Recording(answer=GOOD), None)
    with pytest.raises(ValueError):
        asked(Recording(answer=GOOD), PARAMETERS._replace(m=0))
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_three_only_and_has_no_entry():
    own = Path(check_operation.__file__)
    imported = imported_modules(own)
    assert imported == {
        "hilclaw",
        "hilclaw.build_log",
        "hilclaw.check_answer",
        "hilclaw.check_parameters",
        "hilclaw.tools",
    }
    assert not hasattr(check_operation, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    text = Path(check_operation.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING)
        and not token.string.startswith('"""')
    ]
    for kept_out in ("point", "sim", "board", "tolerance_not_stated"):
        assert not [string for string in code if kept_out in string], kept_out


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_operation).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"KIND_OPERATION_ANSWER_INVALID", "OperationAnswerInvalid", "ask"}
    parameters = list(inspect.signature(ask).parameters.values())
    assert [parameter.name for parameter in parameters] == [
        "operation",
        "request",
        "hw_profile",
        "parameters",
        "output_path",
        "keeper",
        "log_path",
        "rtol",
        "atol",
    ]
    for parameter in parameters:
        assert parameter.default is inspect.Parameter.empty, parameter
    positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(parameter.kind is positional for parameter in parameters[:6])
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    assert all(parameter.kind is keyword_only for parameter in parameters[6:])


# A check of a bf16 kind (ADR-0177 decision 3, "What the operations are handed")

# Test values, not dimensions, draws, a seed or a tolerance of the package.
SWIGLU_KEY = {"kind": "swiglu", "dtype": "bf16", "layout": "row_major"}
BF16_PARAMETERS = Bf16CheckParameters(SEED, 2, "swiglu", "bf16", (3, 5))
BF16_TOLERANCE = {"rtol": 2**-8, "atol": 0}
BF16_REPORT = mock_check.default_script(None, None, None, BF16_PARAMETERS, None, None)


def test_bf16_parameters_reach_the_operation_as_they_are_and_are_judged():
    operation = Recording(BF16_REPORT)
    result = asked(operation, BF16_PARAMETERS, BF16_TOLERANCE)
    assert operation.calls[0][0][2] is BF16_PARAMETERS
    assert result == {
        "outcome": "pass",
        "contract_key": SWIGLU_KEY,
        "shape": {"m": 3, "n": 5},
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
        "counts": {"out": [{"failed": 0, "non_finite": 0}] * 2},
    }


def test_a_bf16_report_that_fails_and_one_that_is_broken():
    wrong = bytearray(BF16_REPORT)
    struct.pack_into("=H", wrong, 4 + 2 * 15 + 4 + 2 * 7, 0x4780)
    result = asked(Recording(bytes(wrong)), BF16_PARAMETERS, BF16_TOLERANCE)
    assert result["counts"] == {
        "out": [{"failed": 0, "non_finite": 0}, {"failed": 1, "non_finite": 0}]
    }
    short = asked(Recording(BF16_REPORT[:-1]), BF16_PARAMETERS, BF16_TOLERANCE)
    assert short["condition"] == "report_form"


@pytest.mark.parametrize("condition", check_result.CONDITIONS[:4])
def test_a_bf16_condition_gives_a_broken_result_of_the_bf16_shape(condition):
    result = asked(Recording(condition), BF16_PARAMETERS, BF16_TOLERANCE)
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "contract_key": SWIGLU_KEY,
        "shape": {"m": 3, "n": 5},
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
    }


@pytest.mark.parametrize("answer", ["report_form", None, bytearray(BF16_REPORT)])
def test_a_bf16_answer_of_neither_form_is_invalid(answer):
    with pytest.raises(OperationAnswerInvalid):
        asked(Recording(answer), BF16_PARAMETERS, BF16_TOLERANCE)


@pytest.mark.parametrize("dtype", ["fp32", "BF16", None])
def test_bf16_parameters_of_another_dtype_are_refused_before_the_call(dtype):
    operation = Recording(BF16_REPORT)
    with pytest.raises(ValueError, match=r"^parameters\.dtype: "):
        asked(operation, BF16_PARAMETERS._replace(dtype=dtype), BF16_TOLERANCE)
    assert operation.calls == []


@pytest.mark.parametrize(
    ("kind", "dims"), [("rope", (3, 5)), ("swiglu", (3, 5, 1)), ("gemm", (3, 5))]
)
def test_bf16_parameters_the_judge_refuses_pass_through_after_the_call(kind, dims):
    operation = Recording(BF16_REPORT)
    parameters = BF16_PARAMETERS._replace(kind=kind, dims=dims)
    with pytest.raises(ValueError, match=r"^dims: "):
        asked(operation, parameters, BF16_TOLERANCE)
    assert len(operation.calls) == 1
    with pytest.raises(ValueError):
        asked(Recording("exit_status"), parameters, BF16_TOLERANCE)


# An sdpa_kv_cache check (ADR-0177 decision 3, HQ-0077; ADR-0165 decision 8)

# Test values, not dimensions, draws, a seed or a tolerance of the package.
SDPA_PARAMETERS = Bf16CheckParameters(SEED, 2, "sdpa_kv_cache", "bf16", (1, 2, 3, 3, 2))
SDPA_TOLERANCE = {"rtol": 0, "atol": 2.154e-3}
SDPA_REPORT = mock_check.default_script(None, None, None, SDPA_PARAMETERS, None, None)


def test_sdpa_parameters_reach_the_operation_and_are_judged_with_the_cache():
    operation = Recording(SDPA_REPORT)
    result = asked(operation, SDPA_PARAMETERS, SDPA_TOLERANCE)
    assert operation.calls[0][0][2] is SDPA_PARAMETERS
    assert result == {
        "outcome": "pass",
        "contract_key": {
            "kind": "sdpa_kv_cache",
            "dtype": "bf16",
            "layout": "row_major",
        },
        "shape": {"m": 1, "l": 2, "h": 3, "h_kv": 3, "d": 2},
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2.154e-3},
        "counts": {
            "cache_k": [{"differs": 0}] * 2,
            "cache_v": [{"differs": 0}] * 2,
            "out": [{"failed": 0, "non_finite": 0}] * 2,
        },
    }
    changed = bytearray(SDPA_REPORT)
    struct.pack_into("=H", changed, 4 + 2 * 6, 0x1234)
    failed = asked(Recording(bytes(changed)), SDPA_PARAMETERS, SDPA_TOLERANCE)
    assert failed["outcome"] == "fail"
    assert [failed["counts"][name][0] for name in ("cache_k", "cache_v", "out")] == [
        {"differs": 1},
        {"differs": 0},
        {"failed": 0, "non_finite": 0},
    ]


def test_an_sdpa_condition_and_an_sdpa_answer_of_neither_form():
    broken = asked(Recording("exit_status"), SDPA_PARAMETERS, SDPA_TOLERANCE)
    assert broken["condition"] == "exit_status"
    assert broken["shape"] == {"m": 1, "l": 2, "h": 3, "h_kv": 3, "d": 2}
    with pytest.raises(OperationAnswerInvalid):
        asked(Recording(bytearray(SDPA_REPORT)), SDPA_PARAMETERS, SDPA_TOLERANCE)


def test_sdpa_dims_the_judge_refuses_pass_through_after_the_call():
    operation = Recording(SDPA_REPORT)
    parameters = SDPA_PARAMETERS._replace(dims=(2, 1, 3, 3, 2))
    with pytest.raises(ValueError, match=r"^dims: "):
        asked(operation, parameters, SDPA_TOLERANCE)
    assert len(operation.calls) == 1
