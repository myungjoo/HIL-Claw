import ast
import copy
import inspect
import struct
from pathlib import Path

import numpy as np
import pytest

from hilclaw import mock_backend, mock_check
from hilclaw.backends import Backend, BackendTable, select
from hilclaw.build_log import LogKeeper
from hilclaw.check_answer import from_answer
from hilclaw.check_operation import ask
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.check_result import CONDITIONS
from hilclaw.harness import (
    bf16_sdpa_kv_cache_arrays,
    bf16_sdpa_kv_cache_verification,
    bf16_verification,
    bf16_verification_arrays,
    verification_arrays,
)
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
PATH_MARKER = "zq7-path-zq7"
# A test value: nothing lies there, and no test makes it.
OUTPUT_PATH = Path(PATH_MARKER) / "runs" / "r1" / "output"

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

    def __call__(self, tool, request, hw_profile, parameters, output_path, keeper):
        self.calls.append((tool, request, hw_profile, parameters, output_path, keeper))
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
    def script(tool, request, hw_profile, parameters, output_path, keeper):
        raise error

    return script


def answer_for(parameters, output_path=OUTPUT_PATH):
    return default_script(TOOL, REQUEST, record(), parameters, output_path, LogKeeper())


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


def test_the_script_is_asked_once_with_the_tool_and_the_very_four_objects():
    script = Asked(b"an answer of the tests")
    request, hw_profile = dict(REQUEST), record()
    output_path = Path(OUTPUT_PATH)
    keeper = LogKeeper()
    operation(script)(request, hw_profile, PARAMETERS, output_path, keeper)
    (
        (
            tool,
            asked_request,
            asked_hw_profile,
            asked_parameters,
            asked_path,
            asked_keeper,
        ),
    ) = script.calls
    assert tool == TOOL
    assert asked_request is request
    assert asked_hw_profile is hw_profile
    assert asked_parameters is PARAMETERS
    assert asked_path is output_path
    assert asked_keeper is keeper
    assert output_path == OUTPUT_PATH


@pytest.mark.parametrize(
    "fourth",
    [None, PATH_MARKER, b"output", 17, object()],
    ids=["None", "a str", "bytes", "an int", "an object"],
)
def test_a_fourth_thing_that_is_no_path_reaches_the_script(fourth):
    script = Asked(b"an answer of the tests")
    made = operation(script)
    assert made(REQUEST, record(), PARAMETERS, fourth, LogKeeper()) is script.answer
    assert script.calls[0][4] is fourth


@pytest.mark.parametrize(
    "answer",
    [
        b"a report of the tests",
        b"",
        "time_limit",
        "exit_status",
        "build_time_limit",
        "build_exit_status",
        None,
        {"outcome": "pass"},
        "pass",
        object(),
    ],
    ids=lambda answer: repr(answer)[:24],
)
def test_the_operation_returns_the_very_object_the_script_returned(answer):
    assert (
        operation(Asked(answer))(
            REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper()
        )
        is answer
    )


def test_building_asks_nothing_and_each_call_asks_once():
    script = Asked()
    made = operation(script)
    assert script.calls == []
    made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper())
    made(REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper())
    assert len(script.calls) == 2


def test_two_operations_over_two_scripts_stay_apart():
    a, b = Asked("answered by a"), Asked("answered by b")
    one, other = operation(a), operation(b)
    assert one is not other
    keeper = LogKeeper()
    assert one(REQUEST, record(), PARAMETERS, OUTPUT_PATH, keeper) == "answered by a"
    assert other(REQUEST, record(), PARAMETERS, OUTPUT_PATH, keeper) == "answered by b"
    assert one(REQUEST, record(), PARAMETERS, OUTPUT_PATH, keeper) == "answered by a"
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
    assert (
        select(table, record(), TOOL)(
            REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper()
        )
        is script.answer
    )
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
    operation(script)(REQUEST, record(), third, OUTPUT_PATH, LogKeeper())
    assert script.calls[0][3] is third


def test_a_call_leaves_its_four_objects_as_they_are():
    request, hw_profile = copy.deepcopy(REQUEST), record()
    output_path = Path(OUTPUT_PATH)
    operation(Asked())(request, hw_profile, PARAMETERS, output_path, LogKeeper())
    assert (request, hw_profile) == (REQUEST, record())
    assert PARAMETERS == CheckParameters(SEED, DRAWS, 3, 4, 5)
    assert output_path == OUTPUT_PATH


@pytest.mark.parametrize(
    "call",
    [
        lambda made: made(REQUEST, record()),
        lambda made: made(REQUEST, record(), PARAMETERS),
        lambda made: made(
            REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper(), "more"
        ),
        lambda made: made(),
        lambda made: made(
            hw_profile=record(),
            parameters=PARAMETERS,
            request=REQUEST,
            output_path=OUTPUT_PATH,
            keeper=LogKeeper(),
        ),
        lambda made: made(REQUEST, PARAMETERS, OUTPUT_PATH, hw_profile=record()),
        lambda made: made(REQUEST, record(), OUTPUT_PATH, parameters=PARAMETERS),
        lambda made: made(
            REQUEST,
            record(),
            PARAMETERS,
            output_path=OUTPUT_PATH,
            keeper=LogKeeper(),
        ),
        lambda made: made(
            REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper(), data_root="x"
        ),
    ],
    ids=[
        "two arguments",
        "three arguments",
        "five arguments",
        "nothing",
        "the request by keyword",
        "the hw_profile by keyword",
        "the check parameters by keyword",
        "the output path by keyword",
        "a further keyword",
    ],
)
def test_an_operation_takes_four_positional_things_and_nothing_else(call):
    script = Asked()
    with pytest.raises(TypeError):
        call(operation(script))
    assert script.calls == []


@pytest.mark.parametrize(
    "error",
    [
        ToolFailure("example_fault", "a message of the tests"),
        ToolFailure("no_backend", "a message of the tests"),
        ToolFailure("compiler_unavailable", "a message of the tests"),
        RuntimeError("a fault of the tests"),
        KeyError("example_member"),
        SystemExit(3),
        KeyboardInterrupt(),
    ],
    ids=lambda error: type(error).__name__,
)
def test_what_the_script_raises_passes_through_as_the_same_object(error):
    with pytest.raises(BaseException) as raised:
        operation(raising(error))(
            REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper()
        )
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
        (None, None, None, None),
        (TOOL, {**REQUEST, "point": "board", "execution": 2}, record(), OUTPUT_PATH),
        ("sim.run", {"candidate": 2}, record("acc_a"), Path("elsewhere") / "output"),
        (7, [], "no record", PATH_MARKER),
    ]
    before = copy.deepcopy(asked)
    for tool, request, hw_profile, output_path in asked:
        answer = default_script(
            tool, request, hw_profile, PARAMETERS, output_path, LogKeeper()
        )
        assert answer == expected
    assert asked == before
    assert PARAMETERS == CheckParameters(SEED, DRAWS, 3, 4, 5)


def test_the_answer_is_the_same_bytes_whatever_lies_at_the_output_path(tmp_path):
    missing = tmp_path / "missing" / "output"
    present = tmp_path / "present" / "output"
    present.mkdir(parents=True)
    (present / "kernel.c").write_bytes(b"int kernel;\n")
    a_file = tmp_path / "a_file"
    a_file.write_bytes(b"no directory")
    expected = answer_for(PARAMETERS, missing)
    assert type(expected) is bytes
    for output_path in (present, a_file, a_file / "below", 17, b"output", object()):
        assert answer_for(PARAMETERS, output_path) == expected
    assert not missing.parent.exists()
    assert [entry.name for entry in present.iterdir()] == ["kernel.c"]


@pytest.mark.parametrize(
    "output_path",
    [OUTPUT_PATH, None, 17],
    ids=["a path", "None", "an int"],
)
def test_what_is_raised_and_its_order_do_not_depend_on_the_output_path(
    output_path, monkeypatch
):
    monkeypatch.setattr(verification_arrays, "draw_inputs", never_drawn)
    with pytest.raises(TypeError) as of_type:
        default_script(
            TOOL, REQUEST, record(), (-1, 0, 0, 0, 0), output_path, LogKeeper()
        )
    assert type(of_type.value) is TypeError
    assert PATH_MARKER not in str(of_type.value)
    with pytest.raises(VerificationArgumentError) as of_value:
        answer_for(PARAMETERS._replace(draws=0), output_path)
    assert str(of_value.value).startswith("draws: ")
    assert PATH_MARKER not in str(of_value.value)


def test_the_same_report_fails_under_a_tolerance_that_admits_no_rounding():
    report = answer_for(PARAMETERS)
    assert judged(report, PARAMETERS, EXAMPLE_TOLERANCE)["outcome"] == "pass"
    assert judged(report, PARAMETERS, NO_TOLERANCE)["outcome"] == "fail"


def test_the_report_through_the_operation_is_that_of_a_direct_call():
    through = operation(default_script)(
        REQUEST, record(), PARAMETERS, OUTPUT_PATH, LogKeeper()
    )
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
    operation(default_script)(REQUEST, record(), SMALLEST, OUTPUT_PATH, LogKeeper())
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
        "hilclaw.harness.bf16_verification",
        "hilclaw.harness.bf16_verification_arrays",
        "hilclaw.harness.bf16_sdpa_kv_cache_verification",
        "hilclaw.harness.bf16_sdpa_kv_cache_arrays",
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
    assert list(parameters) == [
        "tool",
        "request",
        "hw_profile",
        "parameters",
        "output_path",
        "keeper",
    ]
    for parameter in parameters.values():
        assert parameter.default is inspect.Parameter.empty, parameter
    assert list(inspect.signature(operation).parameters) == ["script"]


# A check of a bf16 kind (ADR-0177 decision 3, "The mock")

# Test values, not dimensions, draws, a seed or a tolerance of the package.
BF16_SHAPES = {
    "gemm": [(1, 1, 1), (3, 5, 4)],
    "rmsnorm": [(1, 1), (3, 7)],
    "elementwise_add": [(1, 1), (4, 6)],
    "swiglu": [(1, 1), (5, 3)],
}
BF16_CASES = [(kind, dims) for kind, shapes in BF16_SHAPES.items() for dims in shapes]
BF16_DRAWS = 2
# Half a unit in the last place of bf16, relative (ADR-0163 decision 7).
BF16_TOLERANCE = {"rtol": 2**-8, "atol": 0}
FAR_PATTERN = 0x4780
NAN_PATTERN = 0x7FC0
LOG_PATH = Path(PATH_MARKER) / "runs" / "r1" / "build-log.txt"


def bf16_parameters(kind, dims, draws=BF16_DRAWS, dtype="bf16"):
    return Bf16CheckParameters(
        seed=SEED, draws=draws, kind=kind, dtype=dtype, dims=dims
    )


def bf16_shape(kind, dims):
    names = ("m", "k", "n") if kind == "gemm" else ("m", "n")
    return dict(zip(names, dims, strict=True))


def with_pattern(report, dims, draw, element, pattern):
    changed = bytearray(report)
    start = draw * (4 + 2 * dims[0] * dims[-1]) + 4 + 2 * element
    struct.pack_into("=H", changed, start, pattern)
    return bytes(changed)


def asked_through_the_mock(script, parameters):
    return ask(
        operation(script),
        REQUEST,
        record(),
        parameters,
        OUTPUT_PATH,
        LogKeeper(),
        log_path=LOG_PATH,
        **BF16_TOLERANCE,
    )


def standing_for(answer):
    def script(tool, request, hw_profile, parameters, output_path, keeper):
        return answer(parameters)

    return script


@pytest.mark.parametrize(("kind", "dims"), BF16_CASES)
def test_the_bf16_answer_is_a_complete_report_the_judge_passes(kind, dims):
    report = answer_for(bf16_parameters(kind, dims))
    assert type(report) is bytes
    assert len(report) == BF16_DRAWS * (4 + 2 * dims[0] * dims[-1]) + 4
    assert report.endswith(END_MARK)
    judgement = bf16_verification.judge_report(
        report, kind, dims, draws=BF16_DRAWS, seed=SEED, **BF16_TOLERANCE
    )
    assert judgement == bf16_verification.Judgement(
        None, bf16_verification.Verdict.PASS, ((0, 0),) * BF16_DRAWS
    )


@pytest.mark.parametrize(("kind", "dims"), BF16_CASES)
def test_each_bf16_draw_holds_the_check_value_and_the_nearest_patterns(kind, dims):
    report = answer_for(bf16_parameters(kind, dims))
    arrays = bf16_verification_arrays
    block = 4 + 2 * dims[0] * dims[-1]
    for draw in range(BF16_DRAWS):
        first, second = arrays.draw_inputs(kind, dims, seed=SEED, draw=draw)
        (value,) = struct.unpack_from("=I", report, draw * block)
        assert value == arrays.check_value(first, second)
        output = np.frombuffer(
            report, dtype=np.uint16, count=dims[0] * dims[-1], offset=draw * block + 4
        )
        widened = arrays.widen(output).reshape(dims[0], dims[-1])
        expected = arrays.reference(kind, first, second)
        error = np.abs(widened - expected)
        for step in (-1, 1):
            moved = (output.astype(np.int32) + step).astype(np.uint16)
            neighbour = arrays.widen(moved).reshape(error.shape)
            assert np.all(error <= np.abs(neighbour - expected))


def test_a_bf16_tie_goes_to_the_even_pattern():
    tied = np.array([[1 + 2**-8, 1 + 3 * 2**-8, -(1 + 2**-8)]])
    assert mock_check._nearest_bf16(tied).tolist() == [[0x3F80, 0x3F82, 0xBF80]]


@pytest.mark.parametrize(("kind", "dims"), BF16_CASES)
def test_the_bf16_report_through_the_operation_is_judged_pass(kind, dims):
    result = asked_through_the_mock(default_script, bf16_parameters(kind, dims))
    assert result == {
        "outcome": "pass",
        "shape": bf16_shape(kind, dims),
        "draws": BF16_DRAWS,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
        "counts": [{"failed": 0, "non_finite": 0}] * BF16_DRAWS,
    }


@pytest.mark.parametrize(("kind", "dims"), BF16_CASES)
def test_a_script_for_a_kernel_with_one_wrong_element_fails_that_draw(kind, dims):
    def wrong(parameters):
        return with_pattern(answer_for(parameters), dims, 1, 0, FAR_PATTERN)

    result = asked_through_the_mock(standing_for(wrong), bf16_parameters(kind, dims))
    assert result["outcome"] == "fail"
    assert result["counts"] == [
        {"failed": 0, "non_finite": 0},
        {"failed": 1, "non_finite": 0},
    ]


@pytest.mark.parametrize(("kind", "dims"), BF16_CASES)
def test_a_script_for_a_kernel_with_a_non_finite_output_counts_it(kind, dims):
    def not_finite(parameters):
        return with_pattern(answer_for(parameters), dims, 0, 0, NAN_PATTERN)

    result = asked_through_the_mock(
        standing_for(not_finite), bf16_parameters(kind, dims)
    )
    assert result["outcome"] == "fail"
    assert result["counts"][0] == {"failed": 1, "non_finite": 1}


@pytest.mark.parametrize("condition", CONDITIONS[:4])
@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_script_answering_a_condition_gives_a_broken_bf16_result(kind, condition):
    dims = BF16_SHAPES[kind][1]
    result = asked_through_the_mock(
        standing_for(lambda parameters: condition), bf16_parameters(kind, dims)
    )
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "shape": bf16_shape(kind, dims),
        "draws": BF16_DRAWS,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
    }


def shortened(parameters):
    return answer_for(parameters)[:-1]


def mismatched(parameters):
    report = bytearray(answer_for(parameters))
    report[0] ^= 1
    return bytes(report)


@pytest.mark.parametrize(
    ("answer", "condition"),
    [(shortened, "report_form"), (mismatched, "check_value")],
)
@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_malformed_or_mismatched_bf16_report_is_broken(kind, answer, condition):
    dims = BF16_SHAPES[kind][1]
    result = asked_through_the_mock(standing_for(answer), bf16_parameters(kind, dims))
    assert result["outcome"] == "broken"
    assert result["condition"] == condition
    assert result["shape"] == bf16_shape(kind, dims)


@pytest.mark.parametrize(
    ("kind", "dims"),
    [
        ("rope", (1, 1, 2)),
        ("conv", (1, 1)),
        (None, (1, 1)),
        ("gemm", (1, 1)),
        ("rmsnorm", (1, 1, 1)),
        ("swiglu", (1,)),
        ("elementwise_add", (True, 1)),
        ("gemm", (1, 0, 1)),
        ("rmsnorm", [1, 1]),
    ],
)
def test_bf16_parameters_the_harness_refuses_are_refused_before_a_draw(
    kind, dims, monkeypatch
):
    monkeypatch.setattr(bf16_verification_arrays, "draw_inputs", never_drawn)
    error = refused(bf16_parameters(kind, dims), VerificationArgumentError)
    assert type(error) is VerificationArgumentError


@pytest.mark.parametrize("dtype", ["fp32", "fp16", "BF16", None])
def test_a_bf16_type_of_another_dtype_is_refused(dtype, monkeypatch):
    monkeypatch.setattr(bf16_verification_arrays, "draw_inputs", never_drawn)
    error = refused(bf16_parameters("gemm", (1, 1, 1), dtype=dtype), ValueError)
    assert str(error).startswith("parameters.dtype: ")


@pytest.mark.parametrize(
    ("name", "value"), [("seed", -1), ("draws", 0), ("draws", True)]
)
def test_a_bf16_seed_or_draws_the_harness_refuses_is_refused(name, value):
    parameters = bf16_parameters("swiglu", (1, 1))._replace(**{name: value})
    refused(parameters, VerificationArgumentError)


# An sdpa_kv_cache check (ADR-0177 decision 3, "The mock"; ADR-0165 decision 8)

# Test values, not dimensions, draws, a seed or a tolerance of the package.
SDPA = "sdpa_kv_cache"
SDPA_CASES = [(1, 1, 1, 1, 1), (2, 3, 4, 2, 4), (1, 2, 3, 3, 2), (3, 5, 4, 1, 2)]
# The absolute bound of ADR-0165 decision 9 at l = 128 and the smallest atol of
# its calibration (decision 10); rtol 0.
SDPA_TOLERANCE = {"rtol": 0, "atol": 2.154e-3}


def sdpa_block(dims):
    m, l, h, h_kv, d = dims
    return 4 + 2 * m * h * d + 4 * (l + 2 * m) * h_kv * d


@pytest.mark.parametrize("dims", SDPA_CASES)
def test_the_sdpa_answer_is_a_complete_report_the_judge_passes(dims):
    report = answer_for(bf16_parameters(SDPA, dims))
    assert type(report) is bytes
    assert len(report) == BF16_DRAWS * sdpa_block(dims) + 4
    assert report.endswith(END_MARK)
    judgement = bf16_sdpa_kv_cache_verification.judge_report(
        report, dims, draws=BF16_DRAWS, seed=SEED, **SDPA_TOLERANCE
    )
    zeros = bf16_sdpa_kv_cache_verification.DrawCounts(0, 0, 0)
    assert judgement == bf16_sdpa_kv_cache_verification.Judgement(
        None, bf16_sdpa_kv_cache_verification.Verdict.PASS, (zeros,) * BF16_DRAWS
    )


@pytest.mark.parametrize("dims", SDPA_CASES)
def test_each_sdpa_draw_holds_the_check_value_the_nearest_out_and_the_caches(dims):
    report = answer_for(bf16_parameters(SDPA, dims))
    arrays = bf16_sdpa_kv_cache_arrays
    m, l, h, h_kv, d = dims
    block = sdpa_block(dims)
    cache_size = (l + 2 * m) * h_kv * d
    for draw in range(BF16_DRAWS):
        inputs = arrays.draw_inputs(dims, seed=SEED, draw=draw)
        before_k = arrays.allocation_before(dims, inputs.cached_k)
        before_v = arrays.allocation_before(dims, inputs.cached_v)
        (value,) = struct.unpack_from("=I", report, draw * block)
        expected_value = arrays.check_value(
            dims, inputs.q, inputs.k_new, inputs.v_new, before_k, before_v
        )
        assert value == expected_value
        offset = draw * block + 4
        output = np.frombuffer(report, np.uint16, m * h * d, offset)
        expected = arrays.reference(dims, *inputs).reshape(-1)
        widened = bf16_verification_arrays.widen(output)
        error = np.abs(widened - expected)
        for step in (-1, 1):
            moved = (output.astype(np.int32) + step).astype(np.uint16)
            neighbour = bf16_verification_arrays.widen(moved)
            assert np.all(error <= np.abs(neighbour - expected))
        offset += 2 * m * h * d
        for cached, new in (
            (inputs.cached_k, inputs.k_new),
            (inputs.cached_v, inputs.v_new),
        ):
            cache = np.frombuffer(report, np.uint16, cache_size, offset)
            after = arrays.allocation_after(dims, cached, new)
            assert np.array_equal(cache, after.reshape(-1))
            offset += 2 * cache_size


def test_the_sdpa_answer_passes_at_the_shape_of_the_functional_test():
    dims = (128, 128, 32, 8, 64)
    report = answer_for(bf16_parameters(SDPA, dims, draws=1))
    judgement = bf16_sdpa_kv_cache_verification.judge_report(
        report, dims, draws=1, seed=SEED, **SDPA_TOLERANCE
    )
    assert judgement.verdict is bf16_sdpa_kv_cache_verification.Verdict.PASS
    assert judgement.counts == ((0, 0, 0),)


def test_the_sdpa_report_through_the_operation_is_judged_pass():
    dims = (2, 3, 4, 2, 4)
    result = ask(
        operation(default_script),
        REQUEST,
        record(),
        bf16_parameters(SDPA, dims),
        OUTPUT_PATH,
        LogKeeper(),
        log_path=LOG_PATH,
        **SDPA_TOLERANCE,
    )
    assert result == {
        "outcome": "pass",
        "shape": {"m": 2, "l": 3, "h": 4, "h_kv": 2, "d": 4},
        "draws": BF16_DRAWS,
        "tolerance": {"rtol": 0.0, "atol": 2.154e-3},
        "counts": [{"failed": 0, "non_finite": 0, "cache_differs": 0}] * BF16_DRAWS,
    }


def test_the_sdpa_answer_follows_from_the_parameters_alone():
    parameters = bf16_parameters(SDPA, (2, 3, 4, 2, 4))
    first = answer_for(parameters)
    assert answer_for(parameters, output_path=None) == first
    other = answer_for(parameters._replace(seed=SEED + 1))
    assert other != first
    assert len(other) == len(first)


@pytest.mark.parametrize(
    "dims",
    [
        (2, 1, 4, 2, 4),
        (2, 3, 3, 2, 4),
        (2, 3, 4, 0, 4),
        (2, 3, 4, 2),
        [2, 3, 4, 2, 4],
        (2, 3, True, 2, 4),
    ],
)
def test_sdpa_dims_the_harness_refuses_are_refused_before_a_draw(dims, monkeypatch):
    monkeypatch.setattr(bf16_sdpa_kv_cache_arrays, "draw_inputs", never_drawn)
    refused(bf16_parameters(SDPA, dims), VerificationArgumentError)


@pytest.mark.parametrize(
    ("name", "value"), [("seed", -1), ("seed", 2**64), ("draws", 0), ("draws", True)]
)
def test_an_sdpa_seed_or_draws_the_harness_refuses_is_refused(name, value, monkeypatch):
    monkeypatch.setattr(bf16_sdpa_kv_cache_arrays, "draw_inputs", never_drawn)
    parameters = bf16_parameters(SDPA, (1, 1, 1, 1, 1))._replace(**{name: value})
    refused(parameters, VerificationArgumentError)


def test_an_sdpa_parameters_of_another_dtype_is_refused_first(monkeypatch):
    monkeypatch.setattr(bf16_sdpa_kv_cache_arrays, "draw_inputs", never_drawn)
    parameters = bf16_parameters(SDPA, (2, 1, 4, 2, 4), dtype="fp32")
    error = refused(parameters, ValueError)
    assert str(error).startswith("parameters.dtype: ")


def test_a_kind_that_only_equals_sdpa_is_answered_by_the_other_harness():
    class Kind(str):
        pass

    refused(bf16_parameters(Kind(SDPA), (1, 1, 1, 1, 1)), VerificationArgumentError)
