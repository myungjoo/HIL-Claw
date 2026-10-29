import ast
import inspect
import io
import struct
import tokenize
from pathlib import Path

import numpy as np
import pytest

from hilclaw import (
    check_answer,
    check_ending,
    check_failure,
    check_operation,
    journaled_step,
    mock_check,
    tools,
)
from hilclaw.build_log import LogKeeper
from hilclaw.check_ending import EndedWithoutOutcome, carry_out
from hilclaw.check_parameters import CheckParameters
from hilclaw.harness.verification import END_MARK
from hilclaw.harness.verification_arrays import (
    check_value,
    draw_inputs,
    reference,
)

# Test values, not a seed, a number of draws, dimensions or a tolerance of the package.
SEED = 7
DRAWS = 3
SHAPE = {"m": 3, "k": 4, "n": 5}
PARAMETERS = CheckParameters(seed=SEED, draws=DRAWS, **SHAPE)
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
# Stand-ins of this file: no record gives either name a meaning.
EXAMPLE_KIND = "example_kind"
EXAMPLE_BACKEND_KIND = "example_backend_kind"
# The two names as ADR-0056 decision 6 spells them.
THE_TWO = ["no_kernel_source", "kernel_source_unreadable"]
# The six names as ADR-0060 decision 4 spells them.
THE_SIX = [
    "build_directory_unusable",
    "settings_refused",
    "build_input_missing",
    "compiler_unavailable",
    "build_output_missing",
    "executable_unstartable",
]
THE_EIGHT = [*THE_TWO, *THE_SIX]


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


class OwnFailure(tools.ToolFailure):
    pass


class Text(str):
    pass


class BothFailure(tools.ToolFailure, check_operation.OperationAnswerInvalid):
    def __init__(self, kind, message):
        Exception.__init__(self, kind, message)
        self.kind = kind
        self.message = message


class EndingKind(tools.ToolFailure):
    @property
    def kind(self):
        raise SystemExit(3)

    @kind.setter
    def kind(self, value):
        pass


def failure(kind, message=MARKER):
    return tools.ToolFailure(kind, message)


def carried(
    operation,
    parameters=PARAMETERS,
    tolerance=EXAMPLE_TOLERANCE,
    output_path=OUTPUT_PATH,
):
    return carry_out(
        operation,
        REQUEST,
        HW_PROFILE,
        parameters,
        output_path,
        LogKeeper(),
        log_path=LOG_PATH,
        **tolerance,
    )


def asked(operation, parameters=PARAMETERS, tolerance=EXAMPLE_TOLERANCE):
    return check_operation.ask(
        operation,
        REQUEST,
        HW_PROFILE,
        parameters,
        OUTPUT_PATH,
        LogKeeper(),
        log_path=LOG_PATH,
        **tolerance,
    )


def ended(
    operation,
    parameters=PARAMETERS,
    tolerance=EXAMPLE_TOLERANCE,
    output_path=OUTPUT_PATH,
):
    with pytest.raises(EndedWithoutOutcome) as caught:
        carried(operation, parameters, tolerance, output_path)
    error = caught.value
    assert type(error) is EndedWithoutOutcome
    assert type(error.kind) is str
    assert type(error.message) is str
    assert vars(error) == {"kind": error.kind, "message": error.message}
    assert error.args == (error.kind, error.message)
    assert error.__cause__ is None
    assert error.__context__ is None
    assert MARKER not in error.message
    assert PATH_MARKER not in error.kind
    assert PATH_MARKER not in error.message
    return error


def message_of_ask(operation):
    with pytest.raises(check_operation.OperationAnswerInvalid) as caught:
        asked(operation)
    return caught.value.message


def held_by_the_module(error):
    held = []
    traceback = error.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code.co_filename == check_ending.__file__:
            held.extend(frame.f_locals.values())
            for value in frame.f_locals.values():
                for cell in getattr(value, "__closure__", None) or ():
                    held.append(cell.cell_contents)
        traceback = traceback.tb_next
    return held


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


NEITHER_FORM = [
    None,
    "pass",
    "build_exit",
    "",
    0,
    True,
    1.5,
    [MARKER],
    {MARKER: MARKER},
    object(),
]
NEITHER_FORM_IDS = [
    "none",
    "word",
    "near-build-value",
    "empty",
    "int",
    "bool",
    "float",
    "list",
    "dict",
    "object",
]


def raised_errors():
    return {
        "value-error": ValueError(MARKER),
        "type-error": TypeError(MARKER),
        "os-error": OSError(5, MARKER),
        "lookup-error": LookupError(MARKER),
        "invalid-answer": check_operation.OperationAnswerInvalid(MARKER),
        "failed-step": journaled_step.StepFailed({"x": 1}, EXAMPLE_KIND, MARKER),
        "ending": EndedWithoutOutcome(EXAMPLE_KIND, MARKER),
    }


def test_a_good_report_passes_and_the_operation_is_called_once_with_the_four():
    operation = Recording(answer=GOOD)
    request = dict(REQUEST)
    hw_profile = dict(HW_PROFILE)
    parameters = CheckParameters(seed=SEED, draws=DRAWS, **SHAPE)
    output_path = Path(OUTPUT_PATH)
    keeper = LogKeeper()
    result = carry_out(
        operation,
        request,
        hw_profile,
        parameters,
        output_path,
        keeper,
        log_path=LOG_PATH,
        **EXAMPLE_TOLERANCE,
    )
    assert type(result) is dict
    assert result["outcome"] == "pass"
    assert result == asked(Recording(answer=GOOD))
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
    [Path("elsewhere") / "output", PATH_MARKER, None, 17, object()],
    ids=["path", "str", "none", "int", "object"],
)
def test_the_output_path_is_handed_on_whatever_it_is_and_changes_nothing(output_path):
    for answer in (GOOD, "time_limit", "exit_status"):
        operation = Recording(answer=answer)
        assert carried(operation, output_path=output_path) == asked(
            Recording(answer=answer)
        )
        ((args, kwargs),) = operation.calls
        assert kwargs == {}
        assert len(args) == 5
        assert args[3] is output_path
        assert type(args[4]) is LogKeeper
    for make in (
        lambda: Recording(answer=None),
        lambda: Recording(error=ValueError(MARKER)),
        lambda: Recording(error=failure(EXAMPLE_KIND)),
    ):
        operation = make()
        error = ended(operation, output_path=output_path)
        assert operation.calls[0][0][3] is output_path
        assert (error.kind, error.message) == (
            ended(make()).kind,
            ended(make()).message,
        )
        assert not any(value is output_path for value in vars(error).values())
        assert not any(value is output_path for value in error.args)


def test_ask_is_handed_the_very_four_objects(monkeypatch):
    handed = []
    made = {"outcome": "made"}

    def recording(call, *args, **kwargs):
        handed.append((call, args, kwargs))
        return made

    monkeypatch.setattr(check_operation, "ask", recording)
    operation = Recording(answer=GOOD)
    request, hw_profile = dict(REQUEST), dict(HW_PROFILE)
    output_path = Path(OUTPUT_PATH)
    keeper = LogKeeper()
    assert (
        carry_out(
            operation,
            request,
            hw_profile,
            PARAMETERS,
            output_path,
            keeper,
            log_path=LOG_PATH,
            **EXAMPLE_TOLERANCE,
        )
        is made
    )
    ((call, args, kwargs),) = handed
    assert kwargs == {**EXAMPLE_TOLERANCE, "log_path": LOG_PATH}
    assert len(args) == 5
    assert args[0] is request
    assert args[1] is hw_profile
    assert args[2] is PARAMETERS
    assert args[3] is output_path
    assert args[4] is keeper
    assert operation.calls == []
    assert call(request, hw_profile, PARAMETERS, output_path, keeper) is GOOD
    assert operation.calls == [
        ((request, hw_profile, PARAMETERS, output_path, keeper), {})
    ]
    for wrong in ((request, hw_profile, PARAMETERS), (request,) * 6):
        with pytest.raises(TypeError):
            call(*wrong)
    assert len(operation.calls) == 1


def test_an_operation_that_takes_three_things_only_ends_with_the_kind_of_adr_0045():
    called = []

    def of_three(request, hw_profile, parameters):
        called.append(parameters)
        return GOOD

    error = ended(of_three)
    assert called == []
    assert error.kind == check_operation.KIND_OPERATION_ANSWER_INVALID
    assert error.message == message_of_ask(Recording(error=TypeError()))


def test_the_result_is_the_object_the_judging_made(monkeypatch):
    made = {"outcome": "pass"}
    monkeypatch.setattr(check_answer, "from_answer", lambda answer, **arguments: made)
    assert carried(Recording(answer=GOOD)) is made


def test_a_report_with_one_element_off_fails():
    report = failing_report()
    result = carried(Recording(answer=report))
    assert result["outcome"] == "fail"
    assert result == asked(Recording(answer=report))


@pytest.mark.parametrize(
    "condition", ["time_limit", "exit_status", "build_time_limit", "build_exit_status"]
)
def test_one_of_the_four_strings_gives_the_broken_result(condition):
    result = carried(Recording(answer=condition))
    assert result["outcome"] == "broken"
    assert result["condition"] == condition
    assert result == asked(Recording(answer=condition))


def test_the_default_script_of_the_mock_passes():
    result = carried(mock_check.operation(mock_check.default_script))
    assert result["outcome"] == "pass"
    assert result["shape"] == SHAPE
    assert result["draws"] == DRAWS


def test_the_tolerance_and_the_five_values_reach_the_result():
    parameters = CheckParameters(seed=SEED, draws=5, m=2, k=3, n=4)
    result = carried(Recording(answer="time_limit"), parameters, OTHER_TOLERANCE)
    assert result["tolerance"] == OTHER_TOLERANCE
    assert result["shape"] == {"m": 2, "k": 3, "n": 4}
    assert result["draws"] == 5
    assert result == asked(Recording(answer="time_limit"), parameters, OTHER_TOLERANCE)


@pytest.mark.parametrize("answer", NEITHER_FORM, ids=NEITHER_FORM_IDS)
def test_a_returned_value_of_neither_form_ends_with_the_kind_of_adr_0045(answer):
    operation = Recording(answer=answer)
    error = ended(operation)
    assert len(operation.calls) == 1
    assert error.kind == check_operation.KIND_OPERATION_ANSWER_INVALID
    assert error.message == message_of_ask(Recording(answer=answer))
    assert not any(value is answer for value in vars(error).values())


@pytest.mark.parametrize("name", list(raised_errors()))
def test_a_raised_error_ends_with_the_kind_of_adr_0045(name):
    raised = raised_errors()[name]
    operation = Recording(error=raised)
    error = ended(operation)
    assert len(operation.calls) == 1
    assert error is not raised
    assert error.kind == check_operation.KIND_OPERATION_ANSWER_INVALID
    assert error.message == message_of_ask(Recording(error=raised_errors()[name]))
    assert not any(value is raised for value in vars(error).values())
    assert not any(value is raised for value in held_by_the_module(error))


def test_a_raised_tool_failure_ends_with_the_kind_of_adr_0047():
    raised = failure(EXAMPLE_KIND)
    operation = Recording(error=raised)
    error = ended(operation)
    assert len(operation.calls) == 1
    assert (error.kind, error.message) == check_failure.ended_with(
        failure(EXAMPLE_KIND)
    )
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert EXAMPLE_KIND not in error.message
    assert not any(value is raised for value in vars(error).values())
    assert not any(value is raised for value in held_by_the_module(error))
    assert raised.__cause__ is None
    assert raised.__context__ is None


@pytest.mark.parametrize("kind", sorted(tools.RESERVED_KINDS))
def test_a_raised_reserved_kind_is_never_the_kind_of_the_ending(kind):
    error = ended(Recording(error=failure(kind)))
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert error.kind != kind
    assert (error.kind, error.message) == check_failure.ended_with(failure(kind))


@pytest.mark.parametrize(
    "kind", ["operation_answer_invalid", "operation_failure_invalid"]
)
def test_a_raised_kind_of_the_tool_itself_gives_the_kind_of_adr_0047(kind):
    error = ended(Recording(error=failure(kind)))
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert error.kind != check_operation.KIND_OPERATION_ANSWER_INVALID
    assert (error.kind, error.message) == check_failure.ended_with(failure(kind))


def test_an_instance_of_a_subclass_of_tool_failure_is_answered_alike():
    error = ended(Recording(error=OwnFailure(EXAMPLE_KIND, MARKER)))
    assert (error.kind, error.message) == check_failure.ended_with(
        failure(EXAMPLE_KIND)
    )


@pytest.mark.parametrize("kind", [EXAMPLE_KIND, tools.KIND_STEP_OPEN])
def test_a_tool_failure_that_is_an_invalid_answer_too_is_a_tool_failure(kind):
    raised = BothFailure(kind, MARKER)
    operation = Recording(error=raised)
    error = ended(operation)
    assert len(operation.calls) == 1
    assert (error.kind, error.message) == check_failure.ended_with(failure(kind))
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert not any(value is raised for value in held_by_the_module(error))
    raised.message = None
    assert ended(Recording(error=raised)).message == error.message


def test_a_tool_failure_of_the_judging_that_is_an_invalid_answer_too_passes(
    monkeypatch,
):
    raised = BothFailure(EXAMPLE_KIND, MARKER)

    def broken_judging(answer, **arguments):
        raise raised

    monkeypatch.setattr(check_answer, "from_answer", broken_judging)
    with pytest.raises(tools.ToolFailure) as caught:
        carried(Recording(answer=GOOD))
    assert caught.value is raised


def test_a_backend_kind_gives_the_raised_kind_and_message(monkeypatch):
    monkeypatch.setattr(
        check_failure, "BACKEND_KINDS", frozenset({EXAMPLE_BACKEND_KIND})
    )
    with pytest.raises(EndedWithoutOutcome) as caught:
        carried(Recording(error=failure(EXAMPLE_BACKEND_KIND, "the raised text")))
    error = caught.value
    assert type(error) is EndedWithoutOutcome
    assert (error.kind, error.message) == (EXAMPLE_BACKEND_KIND, "the raised text")
    assert error.__cause__ is None
    assert error.__context__ is None
    other = ended(Recording(error=failure(EXAMPLE_KIND)))
    assert other.kind == check_failure.KIND_OPERATION_FAILURE_INVALID


@pytest.mark.parametrize("kind", THE_EIGHT)
def test_each_backend_kind_as_shipped_gives_the_raised_kind_and_message(kind):
    raised = failure(kind, "the raised text")
    operation = Recording(error=raised)
    with pytest.raises(EndedWithoutOutcome) as caught:
        carried(operation)
    error = caught.value
    assert type(error) is EndedWithoutOutcome
    assert (error.kind, error.message) == (kind, "the raised text")
    assert check_failure.ended_with(raised) == (kind, "the raised text")
    assert vars(error) == {"kind": kind, "message": "the raised text"}
    assert error.__cause__ is None
    assert error.__context__ is None
    assert len(operation.calls) == 1
    assert not any(value is raised for value in held_by_the_module(error))
    tools.ToolFailure(error.kind, error.message)
    journaled_step.StepFailed({}, error.kind, error.message)


@pytest.mark.parametrize("kind", THE_EIGHT)
def test_a_backend_kind_with_a_replaced_message_gives_the_kind_of_adr_0047(kind):
    raised = failure(kind)
    raised.message = None
    error = ended(Recording(error=raised))
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert kind not in error.message


@pytest.mark.parametrize(
    "kind",
    [
        "no_kernel_sources",
        "kernel_source",
        "seed_not_drawn",
        "settings_refuse",
        "compiler_unavailable_",
        "build_exit_status",
        "build_time_limit",
    ],
)
def test_a_kind_beside_the_eight_still_gives_the_kind_of_adr_0047(kind):
    error = ended(Recording(error=failure(kind)))
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    assert (error.kind, error.message) == check_failure.ended_with(
        failure(EXAMPLE_KIND)
    )


@pytest.mark.parametrize("kind", THE_EIGHT)
def test_a_backend_kind_the_judging_raises_is_not_the_operations(monkeypatch, kind):
    raised = failure(kind)

    def broken_judging(answer, **arguments):
        raise raised

    monkeypatch.setattr(check_answer, "from_answer", broken_judging)
    operation = Recording(answer=GOOD)
    with pytest.raises(tools.ToolFailure) as caught:
        carried(operation)
    assert caught.value is raised
    assert (raised.kind, raised.message) == (kind, MARKER)
    assert len(operation.calls) == 1


def test_a_tool_failure_of_the_judging_is_not_the_operations(monkeypatch):
    raised = failure(EXAMPLE_KIND)

    def broken_judging(answer, **arguments):
        raise raised

    monkeypatch.setattr(check_answer, "from_answer", broken_judging)
    operation = Recording(answer=GOOD)
    with pytest.raises(tools.ToolFailure) as caught:
        carried(operation)
    assert caught.value is raised
    assert len(operation.calls) == 1


def test_an_error_of_the_judging_passes_through(monkeypatch):
    raised = ValueError(MARKER)

    def broken_judging(answer, **arguments):
        raise raised

    monkeypatch.setattr(check_answer, "from_answer", broken_judging)
    with pytest.raises(ValueError) as caught:
        carried(Recording(answer=GOOD))
    assert caught.value is raised


def test_an_ending_inside_a_handler_shows_only_the_outer_error():
    outer = LookupError()
    for raised in (ValueError(MARKER), failure(EXAMPLE_KIND)):
        with pytest.raises(EndedWithoutOutcome) as caught:
            try:
                raise outer
            except LookupError:
                carried(Recording(error=raised))
        assert caught.value.__cause__ is None
        assert caught.value.__context__ is outer


@pytest.mark.parametrize(
    "make",
    [lambda: failure(EXAMPLE_KIND), lambda: ValueError(MARKER)],
    ids=["tool-failure", "error"],
)
def test_two_calls_with_fresh_equal_operations_end_alike(make):
    first = ended(Recording(error=make()))
    second = ended(Recording(error=make()))
    assert first is not second
    assert (first.kind, first.message) == (second.kind, second.message)


@pytest.mark.parametrize(
    "raised",
    [SystemExit(3), KeyboardInterrupt(), GeneratorExit()],
    ids=["system-exit", "keyboard-interrupt", "generator-exit"],
)
def test_a_request_to_end_passes_through_as_the_same_object(raised):
    operation = Recording(error=raised)
    with pytest.raises(BaseException) as caught:
        carried(operation)
    assert caught.value is raised
    assert len(operation.calls) == 1


def test_a_request_to_end_out_of_a_read_of_the_tool_failure_is_not_caught():
    with pytest.raises(SystemExit):
        carried(Recording(error=EndingKind(EXAMPLE_KIND, MARKER)))


@pytest.mark.parametrize(
    "parameters",
    [None, tuple(PARAMETERS), PARAMETERS._asdict(), list(PARAMETERS)],
    ids=["none", "tuple", "dict", "list"],
)
def test_parameters_of_another_type_are_refused_before_the_call(parameters):
    operation = Recording(answer=GOOD)
    with pytest.raises(TypeError) as caught:
        carried(operation, parameters)
    assert type(caught.value) is TypeError
    assert operation.calls == []


@pytest.mark.parametrize("operation", [None, "time_limit", 3, GOOD])
def test_an_operation_that_is_not_callable_is_refused(operation):
    with pytest.raises(TypeError) as caught:
        carried(operation)
    assert type(caught.value) is TypeError
    with pytest.raises(TypeError) as direct:
        asked(operation)
    assert str(caught.value) == str(direct.value)


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
            carry_out(*args, **kwargs)
        assert type(caught.value) is TypeError
    assert operation.calls == []


@pytest.mark.parametrize(
    ("changed", "tolerance"),
    [
        ({"m": 0}, EXAMPLE_TOLERANCE),
        ({"draws": 0}, EXAMPLE_TOLERANCE),
        ({"seed": -1}, EXAMPLE_TOLERANCE),
        ({}, {**EXAMPLE_TOLERANCE, "rtol": -0.1}),
        ({}, {**EXAMPLE_TOLERANCE, "atol": float("nan")}),
    ],
    ids=["m", "draws", "seed", "rtol", "atol"],
)
def test_a_bad_value_beside_a_report_raises_what_ask_raises(changed, tolerance):
    parameters = PARAMETERS._replace(**changed)
    operation = Recording(answer=GOOD)
    with pytest.raises(ValueError) as caught:
        carried(operation, parameters, tolerance)
    with pytest.raises(ValueError) as direct:
        asked(Recording(answer=GOOD), parameters, tolerance)
    assert type(caught.value) is type(direct.value)
    assert str(caught.value) == str(direct.value)
    assert len(operation.calls) == 1


@pytest.mark.parametrize(
    "kind", [None, Text(EXAMPLE_KIND)], ids=["none", "str-subclass"]
)
def test_a_tampered_tool_failure_gives_the_kind_of_adr_0047(kind):
    raised = failure(EXAMPLE_KIND)
    raised.kind = kind
    error = ended(Recording(error=raised))
    assert error.kind == check_failure.KIND_OPERATION_FAILURE_INVALID
    again = failure(EXAMPLE_KIND)
    again.kind = kind
    assert (error.kind, error.message) == check_failure.ended_with(again)
    assert EXAMPLE_KIND not in error.message


def test_the_exception_is_the_modules_own_and_states_no_spend():
    assert EndedWithoutOutcome.__bases__ == (Exception,)
    assert not issubclass(
        EndedWithoutOutcome,
        (
            tools.ToolFailure,
            journaled_step.StepFailed,
            check_operation.OperationAnswerInvalid,
        ),
    )
    assert EndedWithoutOutcome.__module__ == "hilclaw.check_ending"
    assert not hasattr(EndedWithoutOutcome, "spend")
    assert not hasattr(EndedWithoutOutcome, "kind")
    error = EndedWithoutOutcome(EXAMPLE_KIND, "some text")
    assert (error.kind, error.message) == (EXAMPLE_KIND, "some text")
    assert not hasattr(error, "spend")


@pytest.mark.parametrize("value", [None, b"x", 3, Text("x")])
def test_the_exception_takes_two_str_only(value):
    for arguments in ((value, "x"), ("x", value)):
        with pytest.raises(TypeError) as caught:
            EndedWithoutOutcome(*arguments)
        assert type(caught.value) is TypeError
    with pytest.raises(TypeError):
        EndedWithoutOutcome("x")


@pytest.mark.parametrize(
    "make",
    [
        lambda: Recording(answer=None),
        lambda: Recording(error=ValueError(MARKER)),
        lambda: Recording(error=failure(EXAMPLE_KIND)),
        lambda: Recording(error=failure(tools.KIND_STEP_OPEN)),
    ],
    ids=["neither-form", "error", "tool-failure", "reserved-kind"],
)
def test_a_tool_failure_and_a_failed_step_can_be_built_from_it(make):
    error = ended(make())
    built = tools.ToolFailure(error.kind, error.message)
    assert built.error_object() == {
        "error": {"kind": error.kind, "message": error.message}
    }
    # The empty spend is this test's example, no rule.
    failed = journaled_step.StepFailed({}, error.kind, error.message)
    assert (failed.kind, failed.message) == (error.kind, error.message)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    carried(Recording(answer=GOOD))
    carried(Recording(answer="time_limit"))
    carried(mock_check.operation(mock_check.default_script))
    ended(Recording(answer="pass"))
    ended(Recording(error=ValueError(MARKER)))
    ended(Recording(error=failure(EXAMPLE_KIND)))
    with pytest.raises(SystemExit):
        carried(Recording(error=SystemExit(3)))
    with pytest.raises(TypeError):
        carried(Recording(answer=GOOD), None)
    with pytest.raises(TypeError):
        carried(None)
    with pytest.raises(ValueError):
        carried(Recording(answer=GOOD), PARAMETERS._replace(m=0))
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_three_only_and_has_no_entry():
    own = Path(check_ending.__file__)
    assert imported_modules(own) == {
        "hilclaw",
        "hilclaw.build_log",
        "hilclaw.check_failure",
        "hilclaw.check_operation",
        "hilclaw.tools",
    }
    assert not hasattr(check_ending, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_the_text_and_the_code_hold_none_of_the_kept_out_strings():
    text = Path(check_ending.__file__).read_text(encoding="utf-8")
    assert "gemm_contract" not in text
    assert "standin_profile" not in text
    code = [
        token.string
        for token in tokenize.generate_tokens(io.StringIO(text).readline)
        if token.type in (tokenize.NAME, tokenize.STRING)
        and not token.string.startswith('"""')
    ]
    for kept_out in (
        "point",
        "sim",
        "board",
        "correctness_check_sim",
        "correctness_check_board",
        "tolerance_not_stated",
        "operation_answer_invalid",
        "operation_failure_invalid",
    ):
        assert not [string for string in code if kept_out in string], kept_out


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_ending).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"EndedWithoutOutcome", "carry_out"}
    parameters = list(inspect.signature(carry_out).parameters.values())
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
    assert inspect.signature(carry_out) == inspect.signature(check_operation.ask)
    for parameter in parameters:
        assert parameter.default is inspect.Parameter.empty, parameter
    positional = inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert all(parameter.kind is positional for parameter in parameters[:6])
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    assert all(parameter.kind is keyword_only for parameter in parameters[6:])
