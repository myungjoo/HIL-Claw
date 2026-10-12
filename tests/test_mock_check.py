import ast
import copy
import inspect
import struct
from pathlib import Path

import numpy as np
import pytest

from hilclaw import mock_backend, mock_check
from hilclaw.backends import Backend, BackendTable, select
from hilclaw.check_answer import from_answer
from hilclaw.check_parameters import CheckParameters
from hilclaw.harness import verification_arrays
from hilclaw.harness.verification import END_MARK, judge_report
from hilclaw.harness.verification_arrays import (
    VerificationArgumentError,
    check_value,
    draw_inputs,
    reference,
)
from hilclaw.journaled_step import StepFailed
from hilclaw.mock_check import default_script, operation
from hilclaw.tools import ToolFailure

TOOL = "correctness.check"

# Test values, not a seed, a number of draws, dimensions or a tolerance of the package.
SEED = 7
DRAWS = 3
SHAPE = {"m": 3, "k": 4, "n": 5}
PARAMETERS = CheckParameters(seed=SEED, draws=DRAWS, **SHAPE)
SMALLEST = CheckParameters(seed=SEED, draws=1, m=1, k=1, n=1)
EXAMPLE_TOLERANCE = {"rtol": 1e-5, "atol": 1e-6}
NO_TOLERANCE = {"rtol": 0, "atol": 0}
REQUEST = {"run_id": "r1", "execution": 1, "point": "sim"}

NOT_PARAMETERS = [None, (SEED, DRAWS, 3, 4, 5), dict(PARAMETERS._asdict()), [7, 3, 3]]
BAD_VALUES = (
    [("seed", value) for value in (-1, 2**64, None, True)]
    + [("draws", value) for value in (0, 2**64, 1.0)]
    + [(name, value) for name in ("m", "k", "n") for value in (0, -1, True, "1")]
)


class Asked:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = []

    def __call__(self, tool, request, hw_profile, parameters):
        self.calls.append((tool, request, hw_profile, parameters))
        return self.answer


def record(accelerator=mock_backend.NAME):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }


def raising(error):
    def script(tool, request, hw_profile, parameters):
        raise error

    return script


def answer_for(parameters):
    return default_script(TOOL, REQUEST, record(), parameters)


def judged(report, parameters, tolerance):
    return from_answer(report, **parameters._asdict(), **tolerance)


def blocks(report, parameters):
    size = 4 + 4 * parameters.m * parameters.n
    for draw in range(parameters.draws):
        block = report[draw * size : (draw + 1) * size]
        (value,) = struct.unpack("=I", block[:4])
        output = np.frombuffer(block, dtype=np.float32, offset=4)
        yield draw, value, output.reshape(parameters.m, parameters.n)


def inputs_of(parameters, draw):
    return draw_inputs(
        parameters.m, parameters.k, parameters.n, seed=parameters.seed, draw=draw
    )


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


# The operation: what the script is asked with, and when


def test_the_script_is_asked_once_with_the_tool_and_the_very_three_objects():
    script = Asked(b"an answer of the tests")
    request, hw_profile = dict(REQUEST), record()
    operation(script)(request, hw_profile, PARAMETERS)
    ((tool, asked_request, asked_hw_profile, asked_parameters),) = script.calls
    assert tool == TOOL
    assert asked_request is request
    assert asked_hw_profile is hw_profile
    assert asked_parameters is PARAMETERS


@pytest.mark.parametrize(
    "answer",
    [
        b"a report of the tests",
        b"",
        "time_limit",
        "exit_status",
        None,
        {"outcome": "pass"},
        "pass",
        object(),
    ],
    ids=lambda answer: repr(answer)[:24],
)
def test_the_operation_returns_the_very_object_the_script_returned(answer):
    assert operation(Asked(answer))(REQUEST, record(), PARAMETERS) is answer


def test_building_asks_nothing_and_each_call_asks_once():
    script = Asked()
    made = operation(script)
    assert script.calls == []
    made(REQUEST, record(), PARAMETERS)
    made(REQUEST, record(), PARAMETERS)
    assert len(script.calls) == 2


def test_two_operations_over_two_scripts_stay_apart():
    a, b = Asked("answered by a"), Asked("answered by b")
    one, other = operation(a), operation(b)
    assert one is not other
    assert one(REQUEST, record(), PARAMETERS) == "answered by a"
    assert other(REQUEST, record(), PARAMETERS) == "answered by b"
    assert one(REQUEST, record(), PARAMETERS) == "answered by a"
    assert (len(a.calls), len(b.calls)) == (2, 1)


def test_the_operation_is_selected_through_a_backend_of_the_mock():
    script = Asked(b"an answer of the tests")
    made = operation(script)
    assert callable(made)
    assert repr(made) == "<operation of the mock backend for 'correctness.check'>"
    backend = Backend(mock_backend.NAME, {TOOL: made})
    assert backend.offered() == (TOOL,)
    table = BackendTable([backend])
    assert select(table, record(), TOOL) is made
    assert script.calls == []
    assert select(table, record(), TOOL)(REQUEST, record(), PARAMETERS) is script.answer
    assert len(script.calls) == 1


def test_a_record_of_another_accelerator_does_not_reach_the_script():
    script = Asked()
    table = BackendTable([Backend(mock_backend.NAME, {TOOL: operation(script)})])
    with pytest.raises(ToolFailure) as raised:
        select(table, record("acc_a"), TOOL)
    assert raised.value.kind == "no_backend"
    assert script.calls == []


@pytest.mark.parametrize(
    "third", [None, {"seed": 7}, (7, 3, 3, 4, 5)], ids=["None", "a dict", "a tuple"]
)
def test_a_third_thing_that_is_no_check_parameters_reaches_the_script(third):
    script = Asked()
    operation(script)(REQUEST, record(), third)
    assert script.calls[0][3] is third


def test_a_call_leaves_its_three_objects_as_they_are():
    request, hw_profile = copy.deepcopy(REQUEST), record()
    operation(Asked())(request, hw_profile, PARAMETERS)
    assert (request, hw_profile) == (REQUEST, record())
    assert PARAMETERS == CheckParameters(SEED, DRAWS, 3, 4, 5)


@pytest.mark.parametrize(
    "call",
    [
        lambda made: made(REQUEST, record()),
        lambda made: made(REQUEST, record(), PARAMETERS, "more"),
        lambda made: made(),
        lambda made: made(hw_profile=record(), parameters=PARAMETERS, request=REQUEST),
        lambda made: made(REQUEST, PARAMETERS, hw_profile=record()),
        lambda made: made(REQUEST, record(), parameters=PARAMETERS),
        lambda made: made(REQUEST, record(), PARAMETERS, data_root="x"),
    ],
    ids=[
        "two arguments",
        "four arguments",
        "nothing",
        "the request by keyword",
        "the hw_profile by keyword",
        "the check parameters by keyword",
        "a further keyword",
    ],
)
def test_an_operation_takes_three_positional_things_and_nothing_else(call):
    script = Asked()
    with pytest.raises(TypeError):
        call(operation(script))
    assert script.calls == []


@pytest.mark.parametrize(
    "error",
    [
        ToolFailure("example_fault", "a message of the tests"),
        ToolFailure("no_backend", "a message of the tests"),
        RuntimeError("a fault of the tests"),
        KeyError("example_member"),
        SystemExit(3),
        KeyboardInterrupt(),
    ],
    ids=lambda error: type(error).__name__,
)
def test_what_the_script_raises_passes_through_as_the_same_object(error):
    with pytest.raises(BaseException) as raised:
        operation(raising(error))(REQUEST, record(), PARAMETERS)
    assert raised.value is error
    assert raised.value.__cause__ is None


@pytest.mark.parametrize("script", [None, "script", 7, {TOOL: 1}, b"script"])
def test_a_script_that_is_not_callable_is_refused_at_building(script):
    with pytest.raises(TypeError, match="must be callable"):
        operation(script)


# The default script: the report


@pytest.mark.parametrize("parameters", [PARAMETERS, SMALLEST], ids=["3x4x5", "1x1x1"])
def test_the_answer_is_a_complete_report_that_passes(parameters):
    report = answer_for(parameters)
    assert type(report) is bytes
    draws, m, n = parameters.draws, parameters.m, parameters.n
    assert len(report) == draws * (4 + 4 * m * n) + 4
    assert report.endswith(END_MARK)
    judgement = judge_report(report, **parameters._asdict(), **EXAMPLE_TOLERANCE)
    assert judgement.broken is None
    result = judged(report, parameters, EXAMPLE_TOLERANCE)
    assert result["outcome"] == "pass"
    assert result["counts"] == [{"failed": 0, "non_finite": 0}] * draws


@pytest.mark.parametrize("parameters", [PARAMETERS, SMALLEST], ids=["3x4x5", "1x1x1"])
def test_each_draw_holds_the_check_value_and_the_rounded_product(parameters):
    report = answer_for(parameters)
    seen = 0
    for draw, value, output in blocks(report, parameters):
        a, b = inputs_of(parameters, draw)
        assert value == check_value(a, b)
        assert np.array_equal(output, reference(a, b).astype(np.float32))
        seen += 1
    assert seen == parameters.draws


def test_no_fp32_neighbour_is_nearer_to_the_float64_product():
    report = answer_for(PARAMETERS)
    for draw, _, output in blocks(report, PARAMETERS):
        exact = reference(*inputs_of(PARAMETERS, draw))
        own = np.abs(output.astype(np.float64) - exact)
        even = output.view(np.uint32) % 2 == 0
        for towards in (np.float32(np.inf), np.float32(-np.inf)):
            neighbour = np.nextafter(output, towards)
            assert neighbour.dtype == np.float32
            other = np.abs(neighbour.astype(np.float64) - exact)
            assert np.all(own <= other)
            assert np.all(even[own == other])


def test_equal_check_parameters_give_equal_bytes_and_another_seed_others():
    first = answer_for(PARAMETERS)
    assert answer_for(PARAMETERS) == first
    assert answer_for(CheckParameters(*PARAMETERS)) == first
    other = answer_for(PARAMETERS._replace(seed=SEED + 1))
    assert len(other) == len(first)
    assert other != first


def test_the_answer_reads_nothing_but_the_check_parameters():
    expected = answer_for(PARAMETERS)
    asked = [
        (None, None, None),
        (TOOL, {**REQUEST, "point": "board", "execution": 2}, record()),
        ("sim.run", {"candidate": 2}, record("acc_a")),
        (7, [], "no record"),
    ]
    before = copy.deepcopy(asked)
    for tool, request, hw_profile in asked:
        assert default_script(tool, request, hw_profile, PARAMETERS) == expected
    assert asked == before
    assert PARAMETERS == CheckParameters(SEED, DRAWS, 3, 4, 5)


def test_the_same_report_fails_under_a_tolerance_that_admits_no_rounding():
    report = answer_for(PARAMETERS)
    assert judged(report, PARAMETERS, EXAMPLE_TOLERANCE)["outcome"] == "pass"
    assert judged(report, PARAMETERS, NO_TOLERANCE)["outcome"] == "fail"


def test_the_report_through_the_operation_is_that_of_a_direct_call():
    through = operation(default_script)(REQUEST, record(), PARAMETERS)
    assert type(through) is bytes
    assert through == answer_for(PARAMETERS)


# The default script: check parameters it computes no report for


def never_drawn(*arguments, **named):
    raise AssertionError("an input was drawn")


def refused(parameters, expected):
    with pytest.raises(expected) as raised:
        answer_for(parameters)
    error = raised.value
    assert not isinstance(error, (ToolFailure, StepFailed))
    assert not hasattr(error, "kind")
    assert not hasattr(error, "spend")
    return error


@pytest.mark.parametrize(
    "parameters", NOT_PARAMETERS, ids=lambda value: type(value).__name__
)
def test_what_is_no_check_parameters_is_refused(parameters, monkeypatch):
    monkeypatch.setattr(verification_arrays, "draw_inputs", never_drawn)
    error = refused(parameters, TypeError)
    assert type(error) is TypeError
    assert type(parameters).__name__ in str(error)


def test_an_instance_of_a_subclass_is_refused():
    class More(CheckParameters):
        pass

    refused(More(*PARAMETERS), TypeError)


@pytest.mark.parametrize(("name", "value"), BAD_VALUES)
def test_a_bad_value_is_refused_before_any_input_is_drawn(name, value, monkeypatch):
    monkeypatch.setattr(verification_arrays, "draw_inputs", never_drawn)
    error = refused(PARAMETERS._replace(**{name: value}), VerificationArgumentError)
    assert type(error) is VerificationArgumentError
    assert str(error).startswith(f"{name}: ")


def test_a_dimension_too_large_to_hold_raises_and_is_no_tool_failure():
    refused(PARAMETERS._replace(m=2**62), Exception)


def test_the_type_is_looked_at_before_the_values():
    refused((-1, 0, 0, 0, 0), TypeError)


# Purity and the module


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    answer_for(PARAMETERS)
    operation(default_script)(REQUEST, record(), SMALLEST)
    refused(None, TypeError)
    refused(PARAMETERS._replace(draws=0), VerificationArgumentError)
    assert list(tmp_path.iterdir()) == []


def test_the_module_imports_the_harness_and_the_type_only_and_has_no_entry():
    own = Path(mock_check.__file__)
    imported = imported_modules(own)
    assert imported == {
        "struct",
        "numpy",
        "hilclaw",
        "hilclaw.check_parameters",
        "hilclaw.harness",
        "hilclaw.harness.verification",
        "hilclaw.harness.verification_arrays",
    }
    assert not imported & {
        "time",
        "random",
        "secrets",
        "os",
        "hilclaw.tools",
        "hilclaw.journaled_step",
        "hilclaw.check_answer",
        "hilclaw.check_judging",
        "hilclaw.check_result",
        "hilclaw.hw_tool",
        "hilclaw.journaled_tool",
        "hilclaw.instance",
    }
    assert not hasattr(mock_check, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(mock_check).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"operation", "default_script"}
    parameters = inspect.signature(default_script).parameters
    assert list(parameters) == ["tool", "request", "hw_profile", "parameters"]
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty, parameter
    assert list(inspect.signature(operation).parameters) == ["script"]
