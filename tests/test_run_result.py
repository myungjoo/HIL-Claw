import ast
import copy
import enum
import inspect
import json
import sys
from pathlib import Path

import pytest

from hilclaw import run_result, tools
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
    WITHIN,
    broken,
    completed,
)

EXAMPLE_N_MAX = 10
EXAMPLE_SHAPE = {"m": 1, "k": 2048, "n": 8192}
EXAMPLE_RUN = {**EXAMPLE_SHAPE, "n_max": EXAMPLE_N_MAX, "sample_form": "interval"}
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
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "resolution_ns": 1,
    "intervals_ns": [104200311, 99870122, 101004517, 100310960, 102118803],
    "memory_bytes": 72351744,
    "ceiling": "not_stated",
}
ADR_NOT_CONVERGED = {
    "outcome": "not_converged",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "resolution_ns": 1,
    "intervals_ns": [
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
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "ceiling": "not_stated",
}
ADR_RUN_BROKEN = {
    "outcome": "broken",
    "condition": "exit_status",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "ceiling": "not_judged",
    "bound": 80000000,
}
TABLE_ORDER = [
    "outcome",
    "condition",
    "shape",
    "n_max",
    "sample_form",
    "resolution_ns",
    "intervals_ns",
    "memory_bytes",
    "ceiling",
    "bound",
]
INTEGER_MAX = 2**53 - 1
SMALL_RUN = {"m": 2, "k": 3, "n": 4, "n_max": 5, "sample_form": "interval"}
SMALL_MEASUREMENT = {"intervals_ns": [7, 8, 9], "resolution_ns": 1}


class Outcome(enum.Enum):
    CONVERGED = "converged"


class Condition(enum.Enum):
    REPLAY = "replay"


class Text(str):
    pass


class Number(int):
    pass


def call_completed(**changed):
    arguments = {
        **SMALL_RUN,
        **SMALL_MEASUREMENT,
        "memory_bytes": 100,
        "bound": None,
        **changed,
    }
    outcome = arguments.pop("outcome", CONVERGED)
    return completed(outcome, **arguments)


def call_broken(**changed):
    arguments = {**SMALL_RUN, "bound": None, **changed}
    condition = arguments.pop("condition", "replay")
    return broken(condition, **arguments)


BOTH = [call_completed, call_broken]

CASES = [
    lambda: completed(
        "converged",
        intervals_ns=CONVERGED_INTERVALS,
        resolution_ns=1,
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
    lambda: call_completed(intervals_ns=[]),
    lambda: call_completed(intervals_ns=(1,), resolution_ns=0),
    lambda: call_broken(),
    lambda: call_broken(bound=0),
    lambda: call_broken(bound=INTEGER_MAX, sample_form="reciprocal"),
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
            intervals_ns=CONVERGED_INTERVALS,
            resolution_ns=1,
            memory_bytes=EXAMPLE_FIGURE,
            bound=None,
            **EXAMPLE_RUN,
        ),
        completed(
            "not_converged",
            intervals_ns=NOT_CONVERGED_INTERVALS,
            resolution_ns=1,
            memory_bytes=EXAMPLE_FIGURE,
            bound=None,
            **EXAMPLE_RUN,
        ),
        broken("build_exit_status", bound=None, **EXAMPLE_RUN),
        broken("exit_status", bound=EXAMPLE_BOUND, **EXAMPLE_RUN),
    ]
    examples = [ADR_CONVERGED, ADR_NOT_CONVERGED, ADR_BUILD_BROKEN, ADR_RUN_BROKEN]
    for result, example in zip(results, examples, strict=True):
        assert result == example
        assert set(result) == set(example)
        assert list(result) == list(example)
        assert list(result["shape"]) == ["m", "k", "n"]
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
    assert ("resolution_ns" in result) == (not is_broken)
    assert ("intervals_ns" in result) == (not is_broken)
    if is_broken:
        assert "memory_bytes" not in result
    assert ("bound" in result) == (result["ceiling"] != "not_stated")
    for name in ("outcome", "shape", "n_max", "sample_form", "ceiling"):
        assert name in result
    assert result["outcome"] in ("converged", "not_converged", "broken")
    assert result["ceiling"] in ("within", "over", "not_judged", "not_stated")
    assert result["sample_form"] in ("interval", "reciprocal")
    if result["ceiling"] in ("within", "over"):
        assert "memory_bytes" in result
    if result["ceiling"] == "not_judged":
        assert "memory_bytes" not in result
    assert all(value is not None for value in values_of(result))
    assert list(result["shape"]) == ["m", "k", "n"]
    assert type(result.get("intervals_ns", [])) is list


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
                "shape": {"m": 2, "k": 3, "n": 4},
                "n_max": 5,
                "sample_form": sample_form,
                "resolution_ns": 1,
                "intervals_ns": [7, 8, 9],
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
        "shape": {"m": 2, "k": 3, "n": 4},
        "n_max": 5,
        "sample_form": sample_form,
        "ceiling": "not_stated",
    }
    arguments = {**SMALL_RUN, "sample_form": sample_form, "bound": None}
    assert broken(condition=condition, **arguments) == result


def test_smallest_arguments():
    smallest = {"m": 1, "k": 1, "n": 1, "n_max": 5, "sample_form": "interval"}
    assert completed(
        "converged",
        intervals_ns=[1],
        resolution_ns=0,
        memory_bytes=1,
        bound=0,
        **smallest,
    ) == {
        "outcome": "converged",
        "shape": {"m": 1, "k": 1, "n": 1},
        "n_max": 5,
        "sample_form": "interval",
        "resolution_ns": 0,
        "intervals_ns": [1],
        "memory_bytes": 1,
        "ceiling": "over",
        "bound": 0,
    }


def test_an_empty_intervals_array_is_admitted():
    assert call_completed(intervals_ns=[])["intervals_ns"] == []
    assert call_completed(intervals_ns=())["intervals_ns"] == []


@pytest.mark.parametrize("function", BOTH)
def test_largest_integers(function):
    result = function(m=INTEGER_MAX, k=INTEGER_MAX, n=INTEGER_MAX, n_max=INTEGER_MAX)
    assert result["shape"] == {"m": INTEGER_MAX, "k": INTEGER_MAX, "n": INTEGER_MAX}
    assert result["n_max"] == INTEGER_MAX
    assert function(bound=INTEGER_MAX)["bound"] == INTEGER_MAX


def test_measurement_values_have_no_upper_bound():
    large = [2**53, 2**64 + 1, 10**100]
    result = call_completed(
        intervals_ns=large, resolution_ns=2**60, memory_bytes=10**40, bound=None
    )
    assert result["intervals_ns"] == large
    assert result["resolution_ns"] == 2**60
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
    refused(expected, call_completed, "resolution_ns", resolution_ns=value)


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
    refused(expected, call_completed, "intervals_ns", intervals_ns=value)


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
    refused(
        expected, call_completed, f"intervals_ns[{position}]", intervals_ns=intervals
    )
    refused(
        expected,
        call_completed,
        f"intervals_ns[{position}]",
        intervals_ns=tuple(intervals),
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


@pytest.mark.parametrize("name", ["resolution_ns", "memory_bytes"])
def test_a_measurement_int_without_decimal_text_is_refused(name, decimal_limit):
    refused(ValueError, call_completed, name, **{name: decimal_limit})
    with pytest.raises(ValueError):
        tools.check_json_object({name: decimal_limit})


def test_an_interval_without_decimal_text_is_refused(decimal_limit):
    refused(
        ValueError, call_completed, "intervals_ns[1]", intervals_ns=[1, decimal_limit]
    )


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["m", "k", "n", "n_max", "bound"])
def test_an_integer_without_decimal_text_is_refused(function, name, decimal_limit):
    refused(ValueError, function, name, **{name: decimal_limit})
    refused(ValueError, function, name, **{name: -decimal_limit})


def test_keyword_arguments_are_required_and_closed():
    full = {**SMALL_RUN, **SMALL_MEASUREMENT, "memory_bytes": 100, "bound": None}
    for name in full:
        arguments = dict(full)
        del arguments[name]
        with pytest.raises(TypeError):
            completed("converged", **arguments)
    with pytest.raises(TypeError):
        completed(**full)
    for name in (*SMALL_RUN, "bound"):
        arguments = {**SMALL_RUN, "bound": None}
        del arguments[name]
        with pytest.raises(TypeError):
            broken("replay", **arguments)
    with pytest.raises(TypeError):
        broken(**SMALL_RUN, bound=None)
    for surplus in ("seed", "point", "ceiling", "n_min", "cv_max", "step"):
        with pytest.raises(TypeError):
            completed("converged", **full, **{surplus: 1})
        with pytest.raises(TypeError):
            broken("replay", **SMALL_RUN, bound=None, **{surplus: 1})
    for name in ("intervals_ns", "resolution_ns", "memory_bytes"):
        with pytest.raises(TypeError):
            broken("replay", **SMALL_RUN, bound=None, **{name: full[name]})
    with pytest.raises(TypeError):
        completed("converged", **full, condition="replay")
    with pytest.raises(TypeError):
        broken("replay", 2, 3, 4, 5, "interval", None)


def test_no_parameter_has_a_default():
    assert list(inspect.signature(completed).parameters) == [
        "outcome",
        "intervals_ns",
        "resolution_ns",
        "memory_bytes",
        "m",
        "k",
        "n",
        "n_max",
        "sample_form",
        "bound",
    ]
    assert list(inspect.signature(broken).parameters) == [
        "condition",
        "m",
        "k",
        "n",
        "n_max",
        "sample_form",
        "bound",
    ]
    for function, first in ((completed, "outcome"), (broken, "condition")):
        for parameter in inspect.signature(function).parameters.values():
            assert parameter.default is inspect.Parameter.empty
            if parameter.name != first:
                assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_arguments_are_not_modified_and_results_share_nothing():
    intervals = [5, 6, 7]
    arguments = {**SMALL_RUN, "intervals_ns": intervals, "resolution_ns": 1}
    arguments |= {"memory_bytes": 9, "bound": 10}
    before = copy.deepcopy(arguments)
    first = completed("converged", **arguments)
    second = completed("converged", **arguments)
    assert arguments == before
    assert first == second
    assert first is not second
    assert first["intervals_ns"] is not intervals
    assert first["intervals_ns"] is not second["intervals_ns"]
    assert first["shape"] is not second["shape"]
    expected = copy.deepcopy(second)
    first["intervals_ns"].append(1)
    first["intervals_ns"][0] = 99
    first["shape"]["m"] = 99
    first["ceiling"] = "over"
    assert arguments == before
    assert intervals == [5, 6, 7]
    assert second == expected
    assert completed("converged", **arguments) == expected

    one = call_broken(bound=3)
    other = call_broken(bound=3)
    assert one == other
    assert one["shape"] is not other["shape"]
    one["shape"]["k"] = 99
    assert other == call_broken(bound=3)


def test_a_tuple_of_intervals_is_returned_as_a_list():
    result = call_completed(intervals_ns=(3, 2, 1))
    assert result["intervals_ns"] == [3, 2, 1]
    assert type(result["intervals_ns"]) is list


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    call_completed()
    call_completed(bound=1)
    call_broken(bound=1)
    with pytest.raises(ValueError):
        call_broken(condition="timeout")
    with pytest.raises(TypeError):
        call_completed(intervals_ns=None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_and_has_no_entry():
    own = Path(run_result.__file__)
    text = own.read_text(encoding="utf-8")
    assert imported_modules(own) == {
        "reprlib",
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
        "WITHIN",
        "OVER",
        "NOT_JUDGED",
        "NOT_STATED",
        "completed",
        "broken",
    }
