import ast
import copy
import enum
import inspect
import json
import math
import sys
from pathlib import Path

import pytest

from hilclaw import check_result, tools
from hilclaw.check_result import BROKEN, CONDITIONS, FAIL, PASS, broken, completed
from hilclaw.harness.verification_arrays import Counts

EXAMPLE_DRAWS = 2
EXAMPLE = {
    "m": 1,
    "k": 2048,
    "n": 8192,
    "draws": EXAMPLE_DRAWS,
    "rtol": 1e-4,
    "atol": 0.01,
}
ADR_PASS = {
    "outcome": "pass",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "draws": 2,
    "tolerance": {"rtol": 1e-4, "atol": 0.01},
    "counts": [{"failed": 0, "non_finite": 0}, {"failed": 0, "non_finite": 0}],
}
ADR_FAIL = {
    "outcome": "fail",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "draws": 2,
    "tolerance": {"rtol": 1e-4, "atol": 0.01},
    "counts": [{"failed": 0, "non_finite": 0}, {"failed": 37, "non_finite": 2}],
}
ADR_BROKEN = {
    "outcome": "broken",
    "condition": "time_limit",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "draws": 2,
    "tolerance": {"rtol": 1e-4, "atol": 0.01},
}
COMPLETED_MEMBERS = {"outcome", "shape", "draws", "tolerance", "counts"}
BROKEN_MEMBERS = {"outcome", "condition", "shape", "draws", "tolerance"}
ZEROS = ((0, 0), (0, 0))
SMALL = {"m": 2, "k": 3, "n": 4, "draws": 2, "rtol": 0.5, "atol": 0.25}

BAD_INTEGERS = [
    (0, ValueError),
    (-1, ValueError),
    (True, TypeError),
    (1.0, TypeError),
    ("1", TypeError),
    (None, TypeError),
]
BAD_NUMBERS = [
    (-0.1, ValueError),
    (float("nan"), ValueError),
    (float("inf"), ValueError),
    (10**400, ValueError),
    (True, TypeError),
    ("0", TypeError),
    (None, TypeError),
]
BAD_COUNT_ITEMS = [
    (-1, ValueError),
    (True, TypeError),
    (1.0, TypeError),
    (None, TypeError),
]


class Condition(enum.Enum):
    TIME_LIMIT = "time_limit"


class Text(str):
    pass


class Number(int):
    pass


class Pair(tuple):
    def __iter__(self):
        return iter((0, 0, 0))

    def __len__(self):
        return 3


def call_completed(**changed):
    return completed(**{**SMALL, "counts": ZEROS, **changed})


def call_broken(**changed):
    return broken("exit_status", **{**SMALL, **changed})


BOTH = [call_completed, call_broken]

HAPPY = [
    lambda: completed(**EXAMPLE, counts=ZEROS),
    lambda: completed(**EXAMPLE, counts=((0, 0), (37, 2))),
    lambda: completed(m=1, k=1, n=1, draws=1, rtol=0, atol=0, counts=[(1, 1)]),
    lambda: completed(**SMALL, counts=(Counts(8, 0), Counts(0, 0))),
    *(
        lambda condition=condition: broken(condition, **EXAMPLE)
        for condition in CONDITIONS
    ),
    lambda: broken("check_value", m=1, k=1, n=1, draws=1, rtol=0.0, atol=0.0),
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
    assert (PASS, FAIL, BROKEN) == ("pass", "fail", "broken")
    assert CONDITIONS == (
        "build_time_limit",
        "build_exit_status",
        "time_limit",
        "exit_status",
        "report_form",
        "check_value",
    )
    assert type(CONDITIONS) is tuple


def test_the_three_examples_of_the_record():
    passed = completed(**EXAMPLE, counts=ZEROS)
    failed = completed(**EXAMPLE, counts=((0, 0), (37, 2)))
    timed_out = broken("time_limit", **EXAMPLE)
    assert passed == ADR_PASS
    assert failed == ADR_FAIL
    assert timed_out == ADR_BROKEN
    assert set(passed) == set(failed) == COMPLETED_MEMBERS
    assert set(timed_out) == BROKEN_MEMBERS


@pytest.mark.parametrize("build", HAPPY)
def test_a_result_is_a_json_object_with_one_of_the_two_member_sets(build):
    result = build()
    tools.check_json_object(result)
    assert json.loads(tools.encode(result)) == result
    assert type(result) is dict
    assert set(result) in (COMPLETED_MEMBERS, BROKEN_MEMBERS)
    assert ("condition" in result) == (result["outcome"] == "broken")
    assert ("counts" in result) == (result["outcome"] in ("pass", "fail"))
    assert all(value is not None for value in values_of(result))
    assert set(result["shape"]) == {"m", "k", "n"}
    assert set(result["tolerance"]) == {"rtol", "atol"}
    assert all(type(result["shape"][name]) is int for name in ("m", "k", "n"))
    assert type(result["draws"]) is int
    assert all(type(result["tolerance"][name]) is float for name in ("rtol", "atol"))
    for entry in result.get("counts", []):
        assert type(entry) is dict
        assert set(entry) == {"failed", "non_finite"}
        assert type(entry["failed"]) is int
        assert type(entry["non_finite"]) is int


def test_member_order_is_that_of_the_table():
    assert list(completed(**EXAMPLE, counts=ZEROS)) == [
        "outcome",
        "shape",
        "draws",
        "tolerance",
        "counts",
    ]
    assert list(broken("report_form", **EXAMPLE)) == [
        "outcome",
        "condition",
        "shape",
        "draws",
        "tolerance",
    ]
    result = completed(**EXAMPLE, counts=ZEROS)
    assert list(result["shape"]) == ["m", "k", "n"]
    assert list(result["tolerance"]) == ["rtol", "atol"]
    assert list(result["counts"][0]) == ["failed", "non_finite"]


def test_smallest_arguments():
    assert completed(m=1, k=1, n=1, draws=1, rtol=0, atol=0.0, counts=[(0, 0)]) == {
        "outcome": "pass",
        "shape": {"m": 1, "k": 1, "n": 1},
        "draws": 1,
        "tolerance": {"rtol": 0.0, "atol": 0.0},
        "counts": [{"failed": 0, "non_finite": 0}],
    }
    assert broken("check_value", m=1, k=1, n=1, draws=1, rtol=0.0, atol=0) == {
        "outcome": "broken",
        "condition": "check_value",
        "shape": {"m": 1, "k": 1, "n": 1},
        "draws": 1,
        "tolerance": {"rtol": 0.0, "atol": 0.0},
    }


def test_counts_at_their_upper_bounds():
    result = call_completed(counts=((8, 8), (8, 0)))
    assert result["outcome"] == "fail"
    assert result["counts"] == [
        {"failed": 8, "non_finite": 8},
        {"failed": 8, "non_finite": 0},
    ]


def test_a_broken_result_of_a_large_check_has_no_counts():
    result = broken(
        "exit_status", m=2**53, k=10**100, n=2**64, draws=10**30, rtol=0, atol=0
    )
    assert result["shape"] == {"m": 2**53, "k": 10**100, "n": 2**64}
    assert result["draws"] == 10**30
    assert set(result) == BROKEN_MEMBERS
    tools.check_json_object(result)


def test_outcome_is_pass_exactly_when_every_failed_is_zero():
    assert call_completed(draws=3, counts=((0, 0),) * 3)["outcome"] == "pass"
    for position in range(3):
        counts = [(0, 0)] * 3
        counts[position] = (1, 0)
        assert call_completed(draws=3, counts=counts)["outcome"] == "fail"
    assert call_completed(draws=3, counts=((1, 1),) * 3)["outcome"] == "fail"


@pytest.mark.parametrize(
    "condition",
    [
        "build_time_limit",
        "build_exit_status",
        "time_limit",
        "exit_status",
        "report_form",
        "check_value",
    ],
)
def test_each_condition_gives_a_broken_result(condition):
    result = broken(condition, **SMALL)
    assert result == {
        "outcome": "broken",
        "condition": condition,
        "shape": {"m": 2, "k": 3, "n": 4},
        "draws": 2,
        "tolerance": {"rtol": 0.5, "atol": 0.25},
    }
    assert broken(condition=condition, **SMALL) == result


def test_counts_as_a_list_a_tuple_and_the_tuples_of_the_harness():
    expected = [{"failed": 3, "non_finite": 1}, {"failed": 0, "non_finite": 0}]
    for counts in ([(3, 1), (0, 0)], ((3, 1), (0, 0)), (Counts(3, 1), Counts(0, 0))):
        result = call_completed(counts=counts)
        assert result["counts"] == expected
        assert type(result["counts"]) is list


def test_a_tuple_subclass_is_read_as_the_tuple_it_is():
    assert call_completed(counts=(Pair((5, 2)), Pair((0, 0))))["counts"] == [
        {"failed": 5, "non_finite": 2},
        {"failed": 0, "non_finite": 0},
    ]
    refused(ValueError, call_completed, "counts[0]", counts=(Pair((0, 0, 0)), (0, 0)))


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("value", [1e-4, 0.01, 0.0, 1.5, 1, 0, 2**53 + 1, 10**300])
def test_tolerance_is_the_float_of_the_argument(function, value):
    for name in ("rtol", "atol"):
        returned = function(**{name: value})["tolerance"][name]
        assert type(returned) is float
        assert returned == float(value)
        assert returned.hex() == float(value).hex()


@pytest.mark.parametrize("function", BOTH)
def test_a_negative_zero_tolerance_is_returned_as_it_is(function):
    tolerance = function(rtol=-0.0, atol=-0.0)["tolerance"]
    assert tolerance == {"rtol": 0.0, "atol": 0.0}
    assert math.copysign(1.0, tolerance["rtol"]) == -1.0
    assert math.copysign(1.0, tolerance["atol"]) == -1.0


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["m", "k", "n", "draws"])
@pytest.mark.parametrize(("value", "expected"), [*BAD_INTEGERS, (Number(1), TypeError)])
def test_a_bad_dimension_or_number_of_draws_is_refused(function, name, value, expected):
    refused(expected, function, name, **{name: value})


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["rtol", "atol"])
@pytest.mark.parametrize(("value", "expected"), [*BAD_NUMBERS, (-1, ValueError)])
def test_a_bad_tolerance_is_refused(function, name, value, expected):
    refused(expected, function, name, **{name: value})


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["m", "k", "n", "draws"])
def test_an_int_without_decimal_text_is_refused(function, name, decimal_limit):
    refused(ValueError, function, name, **{name: decimal_limit})
    refused(ValueError, function, name, **{name: -decimal_limit})


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["rtol", "atol"])
def test_a_tolerance_int_without_decimal_text_is_refused(function, name, decimal_limit):
    refused(ValueError, function, name, **{name: decimal_limit})


def test_a_count_without_decimal_text_is_refused(decimal_limit):
    large = {"m": 10**4000, "n": 10**4000, "draws": 1}
    tools.check_json_object(call_completed(**large, counts=[(10**4000, 10**4000)]))
    refused(
        ValueError,
        call_completed,
        "counts[0].failed",
        **large,
        counts=[(decimal_limit, 0)],
    )
    with pytest.raises(ValueError):
        tools.check_json_object({"failed": decimal_limit})


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        ("pass", ValueError),
        ("fail", ValueError),
        ("broken", ValueError),
        ("TIMEOUT", ValueError),
        ("timeout", ValueError),
        ("TIME_LIMIT", ValueError),
        (" time_limit", ValueError),
        ("build_time_limit ", ValueError),
        ("BUILD_EXIT_STATUS", ValueError),
        ("build_exit", ValueError),
        ("build_status", ValueError),
        ("build_timeout", ValueError),
        ("", ValueError),
        (None, TypeError),
        (1, TypeError),
        (b"time_limit", TypeError),
        (("time_limit",), TypeError),
        (Condition.TIME_LIMIT, TypeError),
        (Text("time_limit"), TypeError),
        (Text("build_exit_status"), TypeError),
        (b"build_time_limit", TypeError),
    ],
)
def test_a_bad_condition_is_refused(condition, expected):
    refused(expected, broken, "condition", condition=condition, **SMALL)


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        (None, TypeError),
        ("ab", TypeError),
        ({0: (0, 0), 1: (0, 0)}, TypeError),
        (iter(ZEROS), TypeError),
        (2, TypeError),
        (((0, 0),), ValueError),
        (((0, 0),) * 3, ValueError),
        ((), ValueError),
    ],
)
def test_bad_counts_are_refused(counts, expected):
    refused(expected, call_completed, "counts", counts=counts)


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (0, TypeError),
        ("ab", TypeError),
        ([0, 0], TypeError),
        ({"failed": 0, "non_finite": 0}, TypeError),
        (None, TypeError),
        ((0, 0, 0), ValueError),
        ((0,), ValueError),
        ((), ValueError),
    ],
)
@pytest.mark.parametrize("position", [0, 1])
def test_an_entry_that_is_no_pair_is_refused(entry, expected, position):
    counts = [(0, 0), (0, 0)]
    counts[position] = entry
    refused(expected, call_completed, f"counts[{position}]", counts=counts)


@pytest.mark.parametrize(("value", "expected"), [*BAD_COUNT_ITEMS, ("1", TypeError)])
@pytest.mark.parametrize("position", [0, 1])
def test_a_bad_count_is_refused(value, expected, position):
    counts = [(0, 0), (0, 0)]
    counts[position] = (value, 0)
    refused(expected, call_completed, f"counts[{position}].failed", counts=counts)
    counts[position] = (1, value)
    refused(expected, call_completed, f"counts[{position}].non_finite", counts=counts)


def test_counts_the_definitions_cannot_produce_are_refused():
    refused(ValueError, call_completed, "counts[1].non_finite", counts=((0, 0), (1, 2)))
    refused(ValueError, call_completed, "counts[0].non_finite", counts=((0, 1), (0, 0)))
    refused(ValueError, call_completed, "counts[1].failed", counts=((8, 0), (9, 0)))
    refused(ValueError, call_completed, "counts[0].failed", counts=((9, 9), (0, 0)))
    refused(
        ValueError,
        completed,
        "counts[0].failed",
        **{**SMALL, "k": 100},
        counts=((9, 0), (0, 0)),
    )


def test_keyword_arguments_are_required_and_closed():
    for name in (*SMALL, "counts"):
        arguments = {**SMALL, "counts": ZEROS}
        del arguments[name]
        with pytest.raises(TypeError):
            completed(**arguments)
    for name in SMALL:
        arguments = dict(SMALL)
        del arguments[name]
        with pytest.raises(TypeError):
            broken("time_limit", **arguments)
    with pytest.raises(TypeError):
        broken(**SMALL)
    for surplus in ("seed", "point", "verdict", "outcome"):
        with pytest.raises(TypeError):
            completed(**SMALL, counts=ZEROS, **{surplus: 1})
        with pytest.raises(TypeError):
            broken("time_limit", **SMALL, **{surplus: 1})
    with pytest.raises(TypeError):
        broken("time_limit", **SMALL, counts=ZEROS)
    with pytest.raises(TypeError):
        completed(**SMALL, counts=ZEROS, condition="time_limit")
    with pytest.raises(TypeError):
        completed(2, 3, 4, 2, 0.5, 0.25, ZEROS)
    with pytest.raises(TypeError):
        broken("time_limit", 2, 3, 4, 2, 0.5, 0.25)


def test_no_parameter_has_a_default():
    assert list(inspect.signature(completed).parameters) == [
        "m",
        "k",
        "n",
        "draws",
        "rtol",
        "atol",
        "counts",
    ]
    assert list(inspect.signature(broken).parameters) == [
        "condition",
        "m",
        "k",
        "n",
        "draws",
        "rtol",
        "atol",
    ]
    for function in (completed, broken):
        for parameter in inspect.signature(function).parameters.values():
            assert parameter.default is inspect.Parameter.empty
            if parameter.name != "condition":
                assert parameter.kind is inspect.Parameter.KEYWORD_ONLY


def test_arguments_are_not_modified_and_results_share_nothing():
    counts = [(3, 1), (0, 0)]
    arguments = {**SMALL, "counts": counts}
    before = copy.deepcopy(arguments)
    first = completed(**arguments)
    second = completed(**arguments)
    assert arguments == before
    assert first == second
    assert first is not second
    for name in ("shape", "tolerance", "counts"):
        assert first[name] is not second[name]
    assert first["counts"][0] is not second["counts"][0]
    expected = copy.deepcopy(second)
    first["counts"][0]["failed"] = 7
    first["counts"].append({"failed": 0, "non_finite": 0})
    first["shape"]["m"] = 99
    first["tolerance"]["rtol"] = 9.0
    first["outcome"] = "pass"
    assert arguments == before
    assert second == expected
    assert completed(**arguments) == expected

    one = broken("report_form", **SMALL)
    other = broken("report_form", **SMALL)
    assert one == other
    assert one["shape"] is not other["shape"]
    assert one["tolerance"] is not other["tolerance"]
    one["shape"]["k"] = 99
    one["tolerance"]["atol"] = 9.0
    assert other == broken("report_form", **SMALL)
    assert CONDITIONS == (
        "build_time_limit",
        "build_exit_status",
        "time_limit",
        "exit_status",
        "report_form",
        "check_value",
    )


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    completed(**EXAMPLE, counts=ZEROS)
    broken("time_limit", **EXAMPLE)
    with pytest.raises(ValueError):
        broken("timeout", **EXAMPLE)
    with pytest.raises(TypeError):
        completed(**EXAMPLE, counts=None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_standard_library_only_and_has_no_entry():
    own = Path(check_result.__file__)
    assert imported_modules(own) == {"math", "reprlib"}
    assert not hasattr(check_result, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(check_result).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"PASS", "FAIL", "BROKEN", "CONDITIONS", "completed", "broken"}
