import ast
import copy
import enum
import inspect
import json
import sys
from pathlib import Path

import pytest

from hilclaw import (
    contract_table,
    gemm_contract,
    rmsnorm_bf16_contract,
    run_result,
    sdpa_kv_cache_bf16_contract,
    tools,
)
from hilclaw.harness import memory_ceiling, timing
from hilclaw.run_result import (
    BROKEN,
    CONDITIONS,
    CONVERGED,
    NOT_CONVERGED,
    NOT_JUDGED,
    NOT_STATED,
    OVER,
    SAMPLE_FORMS,
    UNITS,
    WITHIN,
    broken,
    completed,
)

GEMM = next(e for e in contract_table.TABLE.values() if e.contract is gemm_contract)
RMSNORM = next(
    e for e in contract_table.TABLE.values() if e.contract is rmsnorm_bf16_contract
)
SDPA = next(
    e
    for e in contract_table.TABLE.values()
    if e.contract is sdpa_kv_cache_bf16_contract
)
GEMM_KEY = {"kind": "gemm", "dtype": "fp32", "layout": "row_major"}
EXAMPLE_N_MAX = 10
EXAMPLE_DIMS = (1, 2048, 8192)
EXAMPLE_RUN = {"n_max": EXAMPLE_N_MAX, "sample_form": "interval"}
EXAMPLE_BOUND = 80000000
CONVERGED_INTERVALS = [104200311, 99870122, 101004517, 100310960, 102118803]
NOT_CONVERGED_INTERVALS = [
    100000000,
    130000000,
    95000000,
    140000000,
    98000000,
    135000000,
    101000000,
    128000000,
    97000000,
    133000000,
]
EXAMPLE_FIGURE = 72351744

ADR_CONVERGED = {
    "outcome": "converged",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "unit": "ns",
    "resolution": 1,
    "intervals": [104200311, 99870122, 101004517, 100310960, 102118803],
    "memory_bytes": 72351744,
    "ceiling": "not_stated",
}
ADR_NOT_CONVERGED = {
    "outcome": "not_converged",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "unit": "ns",
    "resolution": 1,
    "intervals": [
        100000000,
        130000000,
        95000000,
        140000000,
        98000000,
        135000000,
        101000000,
        128000000,
        97000000,
        133000000,
    ],
    "memory_bytes": 72351744,
    "ceiling": "not_stated",
}
ADR_BUILD_BROKEN = {
    "outcome": "broken",
    "condition": "build_exit_status",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "ceiling": "not_stated",
}
ADR_RUN_BROKEN = {
    "outcome": "broken",
    "condition": "exit_status",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "ceiling": "not_judged",
    "bound": 80000000,
}
ADR_0183_LINES = [
    (
        '{"outcome": "converged", "contract_key": {"kind": "gemm", "dtype": "fp32", '
        '"layout": "row_major"}, "shape": {"m": 1, "k": 2048, "n": 8192}, '
        '"n_max": 10, "sample_form": "interval", "unit": "ns", "resolution": 1, '
        '"intervals": [104200311, 99870122, 101004517, 100310960, 102118803], '
        '"memory_bytes": 72351744, "ceiling": "not_stated"}'
    ),
    (
        '{"outcome": "broken", "condition": "exit_status", "contract_key": '
        '{"kind": "gemm", "dtype": "fp32", "layout": "row_major"}, "shape": '
        '{"m": 1, "k": 2048, "n": 8192}, "n_max": 10, "sample_form": "interval", '
        '"ceiling": "not_stated"}'
    ),
]
TABLE_ORDER = [
    "outcome",
    "condition",
    "contract_key",
    "shape",
    "n_max",
    "sample_form",
    "unit",
    "resolution",
    "intervals",
    "memory_bytes",
    "ceiling",
    "bound",
]
INTEGER_MAX = 2**53 - 1
SMALL_RUN = {"m": 2, "k": 3, "n": 4, "n_max": 5, "sample_form": "interval"}
SMALL_KEYWORDS = {"n_max": 5, "sample_form": "interval"}
SMALL_MEASUREMENT = {"unit": "ns", "intervals": [7, 8, 9], "resolution": 1}


class Outcome(enum.Enum):
    CONVERGED = "converged"


class Condition(enum.Enum):
    REPLAY = "replay"


class Text(str):
    pass


class Number(int):
    pass


def contract_of(arguments):
    dims = tuple(arguments.pop(name) for name in ("m", "k", "n"))
    entry = arguments.pop("entry", GEMM)
    return entry, arguments.pop("dims", dims)


def call_completed(**changed):
    arguments = {
        **SMALL_RUN,
        **SMALL_MEASUREMENT,
        "memory_bytes": 100,
        "bound": None,
        **changed,
    }
    outcome = arguments.pop("outcome", CONVERGED)
    return completed(outcome, *contract_of(arguments), **arguments)


def call_broken(**changed):
    arguments = {**SMALL_RUN, "bound": None, **changed}
    condition = arguments.pop("condition", "replay")
    return broken(condition, *contract_of(arguments), **arguments)


BOTH = [call_completed, call_broken]

CASES = [
    lambda: completed(
        "converged",
        GEMM,
        EXAMPLE_DIMS,
        unit="ns",
        intervals=CONVERGED_INTERVALS,
        resolution=1,
        memory_bytes=EXAMPLE_FIGURE,
        bound=None,
        **EXAMPLE_RUN,
    ),
    lambda: call_completed(memory_bytes=None),
    lambda: call_completed(memory_bytes=99, bound=100),
    lambda: call_completed(memory_bytes=100, bound=100),
    lambda: call_completed(memory_bytes=101, bound=100),
    lambda: call_completed(memory_bytes=None, bound=100),
    lambda: call_completed(memory_bytes=1, bound=0),
    lambda: call_completed(memory_bytes=INTEGER_MAX + 1, bound=INTEGER_MAX),
    lambda: call_completed(outcome=NOT_CONVERGED, sample_form="reciprocal"),
    lambda: call_completed(intervals=[]),
    lambda: call_completed(intervals=(1,), resolution=0),
    lambda: call_broken(),
    lambda: call_broken(bound=0),
    lambda: call_broken(bound=INTEGER_MAX, sample_form="reciprocal"),
    lambda: call_completed(entry=RMSNORM, dims=(512, 2048)),
    lambda: call_broken(entry=RMSNORM, dims=(512, 2048), bound=7),
    lambda: call_completed(entry=SDPA, dims=(1, 128, 32, 8, 64), bound=100),
    *(
        lambda condition=condition: call_broken(condition=condition)
        for condition in CONDITIONS
    ),
]


def refused(expected, function, name, **arguments):
    with pytest.raises(expected) as caught:
        function(**arguments)
    assert type(caught.value) is expected
    assert str(caught.value).startswith(f"{name}: ")


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


def values_of(value):
    yield value
    if isinstance(value, dict):
        for member in value.values():
            yield from values_of(member)
    if isinstance(value, list):
        for item in value:
            yield from values_of(item)


@pytest.fixture
def decimal_limit():
    before = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(4300)
    yield 10**5000
    sys.set_int_max_str_digits(before)


def test_constants_are_those_of_the_record():
    assert (CONVERGED, NOT_CONVERGED, BROKEN) == (
        "converged",
        "not_converged",
        "broken",
    )
    assert CONDITIONS == (
        "build_time_limit",
        "build_exit_status",
        "time_limit",
        "exit_status",
        "report_form",
        "zero_interval",
        "replay",
    )
    assert SAMPLE_FORMS == ("interval", "reciprocal")
    assert UNITS == ("ns",)
    assert type(UNITS) is tuple
    assert (WITHIN, OVER, NOT_JUDGED, NOT_STATED) == (
        "within",
        "over",
        "not_judged",
        "not_stated",
    )
    assert type(CONDITIONS) is tuple
    assert type(SAMPLE_FORMS) is tuple


def test_sample_forms_are_those_of_the_harness():
    assert SAMPLE_FORMS == timing.SAMPLE_FORMS
    assert memory_ceiling.BOUND_MAX == INTEGER_MAX


def test_the_four_examples_of_the_record():
    results = [
        completed(
            "converged",
            GEMM,
            EXAMPLE_DIMS,
            unit="ns",
            intervals=CONVERGED_INTERVALS,
            resolution=1,
            memory_bytes=EXAMPLE_FIGURE,
            bound=None,
            **EXAMPLE_RUN,
        ),
        completed(
            "not_converged",
            GEMM,
            EXAMPLE_DIMS,
            unit="ns",
            intervals=NOT_CONVERGED_INTERVALS,
            resolution=1,
            memory_bytes=EXAMPLE_FIGURE,
            bound=None,
            **EXAMPLE_RUN,
        ),
        broken("build_exit_status", GEMM, EXAMPLE_DIMS, bound=None, **EXAMPLE_RUN),
        broken("exit_status", GEMM, EXAMPLE_DIMS, bound=EXAMPLE_BOUND, **EXAMPLE_RUN),
    ]
    examples = [ADR_CONVERGED, ADR_NOT_CONVERGED, ADR_BUILD_BROKEN, ADR_RUN_BROKEN]
    for result, example in zip(results, examples, strict=True):
        assert result == example
        assert set(result) == set(example)
        assert list(result) == list(example)
        assert list(result["shape"]) == ["m", "k", "n"]
        assert list(result["contract_key"]) == ["kind", "dtype", "layout"]
        tools.check_json_object(result)
        assert json.loads(tools.encode(result)) == example
        encoded = list(json.loads(tools.encode(result)))
        assert encoded == [name for name in TABLE_ORDER if name in example]


@pytest.mark.parametrize("build", CASES)
def test_the_presence_rules_of_the_table(build):
    result = build()
    tools.check_json_object(result)
    assert json.loads(tools.encode(result)) == result
    assert type(result) is dict
    assert set(result) <= set(TABLE_ORDER)
    assert list(result) == [name for name in TABLE_ORDER if name in result]
    is_broken = result["outcome"] == "broken"
    assert ("condition" in result) == is_broken
    assert ("unit" in result) == (not is_broken)
    assert ("resolution" in result) == (not is_broken)
    assert ("intervals" in result) == (not is_broken)
    assert result.get("unit", "ns") == "ns"
    if is_broken:
        assert "memory_bytes" not in result
    assert ("bound" in result) == (result["ceiling"] != "not_stated")
    for name in (
        "outcome",
        "contract_key",
        "shape",
        "n_max",
        "sample_form",
        "ceiling",
    ):
        assert name in result
    assert result["outcome"] in ("converged", "not_converged", "broken")
    assert result["ceiling"] in ("within", "over", "not_judged", "not_stated")
    assert result["sample_form"] in ("interval", "reciprocal")
    if result["ceiling"] in ("within", "over"):
        assert "memory_bytes" in result
    if result["ceiling"] == "not_judged":
        assert "memory_bytes" not in result
    assert all(value is not None for value in values_of(result))
    assert list(result["contract_key"]) == ["kind", "dtype", "layout"]
    assert type(result.get("intervals", [])) is list


@pytest.mark.parametrize(
    ("memory_bytes", "bound", "ceiling"),
    [
        (100, None, "not_stated"),
        (None, None, "not_stated"),
        (99, 100, "within"),
        (100, 100, "within"),
        (101, 100, "over"),
        (None, 100, "not_judged"),
        (1, 0, "over"),
        (INTEGER_MAX, INTEGER_MAX, "within"),
        (INTEGER_MAX + 1, INTEGER_MAX, "over"),
        (10**30, INTEGER_MAX, "over"),
        (1, INTEGER_MAX, "within"),
    ],
)
def test_ceiling_of_a_completed_result(memory_bytes, bound, ceiling):
    result = call_completed(memory_bytes=memory_bytes, bound=bound)
    assert result["ceiling"] == ceiling
    assert ("memory_bytes" in result) == (memory_bytes is not None)
    if memory_bytes is not None:
        assert result["memory_bytes"] == memory_bytes
    assert ("bound" in result) == (bound is not None)
    if bound is not None:
        assert result["bound"] == bound


@pytest.mark.parametrize(
    ("bound", "ceiling"),
    [(None, "not_stated"), (0, "not_judged"), (INTEGER_MAX, "not_judged")],
)
def test_ceiling_of_a_broken_result(bound, ceiling):
    result = call_broken(bound=bound)
    assert result["ceiling"] == ceiling
    assert ("bound" in result) == (bound is not None)
    assert "memory_bytes" not in result


def test_a_completed_result_of_each_outcome_and_sample_form():
    for outcome in ("converged", "not_converged"):
        for sample_form in ("interval", "reciprocal"):
            result = call_completed(outcome=outcome, sample_form=sample_form)
            assert result == {
                "outcome": outcome,
                "contract_key": GEMM_KEY,
                "shape": {"m": 2, "k": 3, "n": 4},
                "n_max": 5,
                "sample_form": sample_form,
                "unit": "ns",
                "resolution": 1,
                "intervals": [7, 8, 9],
                "memory_bytes": 100,
                "ceiling": "not_stated",
            }


@pytest.mark.parametrize(
    "condition",
    [
        "build_time_limit",
        "build_exit_status",
        "time_limit",
        "exit_status",
        "report_form",
        "zero_interval",
        "replay",
    ],
)
@pytest.mark.parametrize("sample_form", ["interval", "reciprocal"])
def test_each_condition_gives_a_broken_result(condition, sample_form):
    result = call_broken(condition=condition, sample_form=sample_form)
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "contract_key": GEMM_KEY,
        "shape": {"m": 2, "k": 3, "n": 4},
        "n_max": 5,
        "sample_form": sample_form,
        "ceiling": "not_stated",
    }
    arguments = {**SMALL_KEYWORDS, "sample_form": sample_form, "bound": None}
    named = broken(condition=condition, entry=GEMM, dims=(2, 3, 4), **arguments)
    assert named == result


def test_smallest_arguments():
    smallest = {"n_max": 5, "sample_form": "interval"}
    assert completed(
        "converged",
        GEMM,
        (1, 1, 1),
        unit="ns",
        intervals=[1],
        resolution=0,
        memory_bytes=1,
        bound=0,
        **smallest,
    ) == {
        "outcome": "converged",
        "contract_key": GEMM_KEY,
        "shape": {"m": 1, "k": 1, "n": 1},
        "n_max": 5,
        "sample_form": "interval",
        "unit": "ns",
        "resolution": 0,
        "intervals": [1],
        "memory_bytes": 1,
        "ceiling": "over",
        "bound": 0,
    }


def test_an_empty_intervals_array_is_admitted():
    assert call_completed(intervals=[])["intervals"] == []
    assert call_completed(intervals=())["intervals"] == []


@pytest.mark.parametrize("function", BOTH)
def test_largest_integers(function):
    result = function(m=INTEGER_MAX, k=INTEGER_MAX, n=INTEGER_MAX, n_max=INTEGER_MAX)
    assert result["shape"] == {"m": INTEGER_MAX, "k": INTEGER_MAX, "n": INTEGER_MAX}
    assert result["n_max"] == INTEGER_MAX
    assert function(bound=INTEGER_MAX)["bound"] == INTEGER_MAX


def test_measurement_values_have_no_upper_bound():
    large = [2**53, 2**64 + 1, 10**100]
    result = call_completed(
        intervals=large, resolution=2**60, memory_bytes=10**40, bound=None
    )
    assert result["intervals"] == large
    assert result["resolution"] == 2**60
    assert result["memory_bytes"] == 10**40
    tools.check_json_object(result)
    assert json.loads(tools.encode(result)) == result


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["m", "k", "n"])
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, ValueError),
        (-1, ValueError),
        (2**53, ValueError),
        (True, TypeError),
        (1.0, TypeError),
        ("1", TypeError),
        (None, TypeError),
        (Number(1), TypeError),
    ],
)
def test_a_bad_dimension_is_refused(function, name, value, expected):
    refused(expected, function, name, **{name: value})


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (4, ValueError),
        (0, ValueError),
        (2**53, ValueError),
        (True, TypeError),
        (5.0, TypeError),
        (None, TypeError),
        (Number(5), TypeError),
    ],
)
def test_a_bad_n_max_is_refused(function, value, expected):
    refused(expected, function, "n_max", n_max=value)


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-1, ValueError),
        (2**53, ValueError),
        (10**30, ValueError),
        (True, TypeError),
        (False, TypeError),
        (1.0, TypeError),
        ("0", TypeError),
        (Number(0), TypeError),
    ],
)
def test_a_bad_bound_is_refused(function, value, expected):
    refused(expected, function, "bound", bound=value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(-1, ValueError), (True, TypeError), (1.0, TypeError), (None, TypeError)],
)
def test_a_bad_resolution_is_refused(value, expected):
    refused(expected, call_completed, "resolution", resolution=value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, TypeError),
        ("123", TypeError),
        ({0: 1}, TypeError),
        (iter([1, 2]), TypeError),
        ((n for n in [1, 2]), TypeError),
        (7, TypeError),
    ],
)
def test_bad_intervals_are_refused(value, expected):
    refused(expected, call_completed, "intervals", intervals=value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (1.0, TypeError),
        (None, TypeError),
        ("1", TypeError),
        (Number(1), TypeError),
    ],
)
@pytest.mark.parametrize("position", [0, 2])
def test_a_bad_interval_is_refused(value, expected, position):
    intervals = [5, 6, 7]
    intervals[position] = value
    refused(expected, call_completed, f"intervals[{position}]", intervals=intervals)
    refused(
        expected,
        call_completed,
        f"intervals[{position}]",
        intervals=tuple(intervals),
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (1.0, TypeError),
        ("1", TypeError),
        (Number(1), TypeError),
    ],
)
@pytest.mark.parametrize("bound", [None, 100])
def test_a_bad_memory_figure_is_refused(value, expected, bound):
    refused(expected, call_completed, "memory_bytes", memory_bytes=value, bound=bound)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("broken", ValueError),
        ("CONVERGED", ValueError),
        ("stop converged", ValueError),
        ("", ValueError),
        (None, TypeError),
        (1, TypeError),
        (b"converged", TypeError),
        (Outcome.CONVERGED, TypeError),
        (Text("converged"), TypeError),
    ],
)
def test_a_bad_outcome_is_refused(value, expected):
    refused(expected, call_completed, "outcome", outcome=value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("converged", ValueError),
        ("broken", ValueError),
        ("check_value", ValueError),
        ("TIMEOUT", ValueError),
        ("timeout", ValueError),
        ("REPLAY", ValueError),
        ("ZERO_INTERVAL", ValueError),
        (" replay", ValueError),
        ("", ValueError),
        (None, TypeError),
        (1, TypeError),
        (b"replay", TypeError),
        (Condition.REPLAY, TypeError),
        (Text("replay"), TypeError),
    ],
)
def test_a_bad_condition_is_refused(value, expected):
    refused(expected, call_broken, "condition", condition=value)


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Interval", ValueError),
        ("INTERVAL", ValueError),
        ("", ValueError),
        (None, TypeError),
        (0, TypeError),
        (Text("interval"), TypeError),
    ],
)
def test_a_bad_sample_form_is_refused(function, value, expected):
    refused(expected, function, "sample_form", sample_form=value)


@pytest.mark.parametrize("name", ["resolution", "memory_bytes"])
def test_a_measurement_int_without_decimal_text_is_refused(name, decimal_limit):
    refused(ValueError, call_completed, name, **{name: decimal_limit})
    with pytest.raises(ValueError):
        tools.check_json_object({name: decimal_limit})


def test_an_interval_without_decimal_text_is_refused(decimal_limit):
    refused(ValueError, call_completed, "intervals[1]", intervals=[1, decimal_limit])


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["m", "k", "n", "n_max", "bound"])
def test_an_integer_without_decimal_text_is_refused(function, name, decimal_limit):
    refused(ValueError, function, name, **{name: decimal_limit})
    refused(ValueError, function, name, **{name: -decimal_limit})


def test_keyword_arguments_are_required_and_closed():
    contract = (GEMM, (2, 3, 4))
    full = {**SMALL_KEYWORDS, **SMALL_MEASUREMENT, "memory_bytes": 100, "bound": None}
    for name in full:
        arguments = dict(full)
        del arguments[name]
        with pytest.raises(TypeError):
            completed("converged", *contract, **arguments)
    with pytest.raises(TypeError):
        completed(**full)
    with pytest.raises(TypeError):
        completed("converged", GEMM, **full)
    for name in (*SMALL_KEYWORDS, "bound"):
        arguments = {**SMALL_KEYWORDS, "bound": None}
        del arguments[name]
        with pytest.raises(TypeError):
            broken("replay", *contract, **arguments)
    with pytest.raises(TypeError):
        broken(*contract, **SMALL_KEYWORDS, bound=None)
    for surplus in ("seed", "point", "ceiling", "n_min", "cv_max", "step", "m"):
        with pytest.raises(TypeError):
            completed("converged", *contract, **full, **{surplus: 1})
        with pytest.raises(TypeError):
            broken("replay", *contract, **SMALL_KEYWORDS, bound=None, **{surplus: 1})
    for name in ("unit", "intervals", "resolution", "memory_bytes"):
        with pytest.raises(TypeError):
            broken(
                "replay", *contract, **SMALL_KEYWORDS, bound=None, **{name: full[name]}
            )
    for name in ("intervals_ns", "resolution_ns", "contract_key", "shape"):
        with pytest.raises(TypeError):
            completed("converged", *contract, **full, **{name: 1})
    with pytest.raises(TypeError):
        completed("converged", *contract, **full, condition="replay")
    with pytest.raises(TypeError):
        broken("replay", *contract, 5, "interval", None)


def test_no_parameter_has_a_default():
    assert list(inspect.signature(completed).parameters) == [
        "outcome",
        "entry",
        "dims",
        "unit",
        "resolution",
        "intervals",
        "memory_bytes",
        "n_max",
        "sample_form",
        "bound",
    ]
    assert list(inspect.signature(broken).parameters) == [
        "condition",
        "entry",
        "dims",
        "n_max",
        "sample_form",
        "bound",
    ]
    for function, first in ((completed, "outcome"), (broken, "condition")):
        for parameter in inspect.signature(function).parameters.values():
            assert parameter.default is inspect.Parameter.empty
            if parameter.name in (first, "entry", "dims"):
                kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
            else:
                kind = inspect.Parameter.KEYWORD_ONLY
            assert parameter.kind is kind


def test_arguments_are_not_modified_and_results_share_nothing():
    intervals = [5, 6, 7]
    dims = (2, 3, 4)
    arguments = {**SMALL_KEYWORDS, "intervals": intervals, "resolution": 1}
    arguments |= {"unit": "ns", "memory_bytes": 9, "bound": 10}
    before = copy.deepcopy(arguments)
    first = completed("converged", GEMM, dims, **arguments)
    second = completed("converged", GEMM, dims, **arguments)
    assert arguments == before
    assert first == second
    assert first is not second
    assert first["intervals"] is not intervals
    assert first["intervals"] is not second["intervals"]
    assert first["shape"] is not second["shape"]
    assert first["contract_key"] is not second["contract_key"]
    expected = copy.deepcopy(second)
    first["intervals"].append(1)
    first["intervals"][0] = 99
    first["shape"]["m"] = 99
    first["contract_key"]["kind"] = "rope"
    first["ceiling"] = "over"
    assert arguments == before
    assert intervals == [5, 6, 7]
    assert dims == (2, 3, 4)
    assert second == expected
    assert completed("converged", GEMM, dims, **arguments) == expected
    assert GEMM.contract.KIND == "gemm"

    one = call_broken(bound=3)
    other = call_broken(bound=3)
    assert one == other
    assert one["shape"] is not other["shape"]
    one["shape"]["k"] = 99
    assert other == call_broken(bound=3)


def test_a_tuple_of_intervals_is_returned_as_a_list():
    result = call_completed(intervals=(3, 2, 1))
    assert result["intervals"] == [3, 2, 1]
    assert type(result["intervals"]) is list


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    call_completed()
    call_completed(bound=1)
    call_broken(bound=1)
    with pytest.raises(ValueError):
        call_broken(condition="timeout")
    with pytest.raises(TypeError):
        call_completed(intervals=None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_and_has_no_entry():
    own = Path(run_result.__file__)
    text = own.read_text(encoding="utf-8")
    assert imported_modules(own) == {
        "inspect",
        "reprlib",
        "hilclaw",
        "hilclaw.contract_table",
        "hilclaw.harness",
        "hilclaw.harness.memory_ceiling",
    }
    assert not hasattr(run_result, "main")
    assert "__main__" not in text
    assert "gemm_contract" not in text
    assert "standin_profile" not in text


def test_no_other_module_of_the_package_but_the_tool_function_imports_it():
    package = Path(run_result.__file__).parent
    for path in package.rglob("*.py"):
        if path.parent == package and path.name in ("run_result.py", "run_tool.py"):
            continue
        assert not any(name.endswith("run_result") for name in imported_modules(path))


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(run_result).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "CONVERGED",
        "NOT_CONVERGED",
        "BROKEN",
        "CONDITIONS",
        "SAMPLE_FORMS",
        "UNITS",
        "WITHIN",
        "OVER",
        "NOT_JUDGED",
        "NOT_STATED",
        "completed",
        "broken",
    }


def test_the_two_run_lines_of_adr_0183_decision_5():
    results = [
        completed(
            "converged",
            GEMM,
            EXAMPLE_DIMS,
            unit="ns",
            resolution=1,
            intervals=CONVERGED_INTERVALS,
            memory_bytes=EXAMPLE_FIGURE,
            bound=None,
            **EXAMPLE_RUN,
        ),
        broken("exit_status", GEMM, EXAMPLE_DIMS, bound=None, **EXAMPLE_RUN),
    ]
    for result, line in zip(results, ADR_0183_LINES, strict=True):
        assert json.dumps(result) == line
        assert list(result) == list(json.loads(line))


@pytest.mark.parametrize(
    ("entry", "dims", "key", "shape"),
    [
        (
            RMSNORM,
            (512, 2048),
            {"kind": "rmsnorm", "dtype": "bf16", "layout": "row_major"},
            {"m": 512, "n": 2048},
        ),
        (
            SDPA,
            (1, 128, 32, 8, 64),
            {"kind": "sdpa_kv_cache", "dtype": "bf16", "layout": "row_major"},
            {"m": 1, "l": 128, "h": 32, "h_kv": 8, "d": 64},
        ),
    ],
)
@pytest.mark.parametrize("function", BOTH)
def test_any_covering_entry_gives_its_contract_key_and_shape(
    function, entry, dims, key, shape
):
    result = function(entry=entry, dims=dims)
    assert result["contract_key"] == key
    assert result["shape"] == shape
    assert list(result["shape"]) == list(shape)
    assert entry.timed


@pytest.mark.parametrize("entry", list(contract_table.TABLE.values()))
def test_every_entry_of_the_table_is_taken(entry):
    names = tuple(inspect.signature(entry.contract.task_contract).parameters)
    dims = {
        "gemm": (2, 3, 4),
        "rope": (2, 4, 8),
        "sdpa_kv_cache": (1, 2, 4, 2, 8),
    }.get(entry.contract.KIND, (2, 3))
    result = call_broken(entry=entry, dims=dims)
    assert tuple(result["shape"]) == names
    assert result["contract_key"]["kind"] == entry.contract.KIND
    assert result["contract_key"]["dtype"] == entry.contract.DTYPE


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, TypeError),
        (tuple(GEMM), TypeError),
        (gemm_contract, TypeError),
        ("gemm", TypeError),
        (GEMM._replace(timed=False), ValueError),
        (contract_table.Entry(gemm_contract, checked=True, timed=None), ValueError),
    ],
)
def test_a_bad_entry_is_refused(function, value, expected):
    refused(expected, function, "entry", entry=value)


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize(
    ("entry", "value", "expected", "name"),
    [
        (GEMM, [2, 3, 4], TypeError, "dims"),
        (GEMM, None, TypeError, "dims"),
        (GEMM, {"m": 2, "k": 3, "n": 4}, TypeError, "dims"),
        (GEMM, (2, 3), ValueError, "dims"),
        (GEMM, (2, 3, 4, 5), ValueError, "dims"),
        (GEMM, (), ValueError, "dims"),
        (RMSNORM, (2, 3, 4), ValueError, "dims"),
        (RMSNORM, (0, 3), ValueError, "m"),
        (RMSNORM, (2, True), TypeError, "n"),
        (RMSNORM, (2, 2**53), ValueError, "n"),
        (SDPA, (4, 1, 2, 2, 2), ValueError, "dims"),
        (SDPA, (1, 4, 3, 2, 2), ValueError, "dims"),
        (SDPA, (1, 4, 2, 2, 2.0), TypeError, "d"),
        (
            next(e for e in contract_table.TABLE.values() if e.contract.KIND == "rope"),
            (2, 4, 3),
            ValueError,
            "dims",
        ),
    ],
)
def test_bad_dims_are_refused(function, entry, value, expected, name):
    refused(expected, function, name, entry=entry, dims=value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ms", ValueError),
        ("us", ValueError),
        ("NS", ValueError),
        ("", ValueError),
        (None, TypeError),
        (1, TypeError),
        (b"ns", TypeError),
        (Text("ns"), TypeError),
    ],
)
def test_a_unit_other_than_ns_is_refused(value, expected):
    refused(expected, call_completed, "unit", unit=value)


def test_the_entry_is_checked_before_the_unit_and_after_the_outcome():
    refused(TypeError, call_completed, "outcome", outcome=None, entry=None, unit="s")
    refused(TypeError, call_completed, "entry", entry=None, unit="s")
    refused(ValueError, call_completed, "n_max", n_max=1, unit="s")
    refused(ValueError, call_completed, "unit", unit="s", resolution=-1)
