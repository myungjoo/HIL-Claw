import ast
import copy
import enum
import inspect
import json
import math
import sys
from pathlib import Path

import pytest

from hilclaw import check_result, contract_table, tools
from hilclaw.check_result import (
    BF16_KINDS,
    BROKEN,
    CONDITIONS,
    FAIL,
    PASS,
    bf16_broken,
    bf16_completed,
    broken,
    completed,
    output_operands,
    v2_broken,
    v2_completed,
)
from hilclaw.harness.bf16_sdpa_kv_cache_verification import DrawCounts
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
    assert imported_modules(own) == {
        "inspect",
        "math",
        "reprlib",
        "types",
        "hilclaw",
        "hilclaw.contract_table",
    }
    assert not hasattr(check_result, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module():
    public = {
        name
        for name, value in vars(check_result).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "PASS",
        "FAIL",
        "BROKEN",
        "CONDITIONS",
        "BF16_KINDS",
        "completed",
        "broken",
        "bf16_completed",
        "bf16_broken",
        "BIT_EXACT",
        "output_operands",
        "v2_completed",
        "v2_broken",
    }


# Test values, not dimensions, draws or a tolerance of the package.
BF16_SHAPES = {
    "gemm": ((2, 3, 4), {"m": 2, "k": 3, "n": 4}),
    "rmsnorm": ((2, 4), {"m": 2, "n": 4}),
    "elementwise_add": ((2, 4), {"m": 2, "n": 4}),
    "swiglu": ((2, 4), {"m": 2, "n": 4}),
}
BF16_COMMON = {"draws": 2, "rtol": 2**-8, "atol": 0}


def test_the_bf16_kinds_are_the_six_of_the_harnesses_in_table_order():
    assert BF16_KINDS == (
        "gemm",
        "rmsnorm",
        "elementwise_add",
        "swiglu",
        "rope",
        "sdpa_kv_cache",
    )


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_completed_bf16_result_names_the_shape_members_of_its_kind(kind):
    dims, shape = BF16_SHAPES[kind]
    passed = bf16_completed(kind, dims, **BF16_COMMON, counts=[(0, 0), (0, 0)])
    assert passed == {
        "outcome": PASS,
        "shape": shape,
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
        "counts": [{"failed": 0, "non_finite": 0}, {"failed": 0, "non_finite": 0}],
    }
    assert list(passed["shape"]) == list(shape)
    failed = bf16_completed(kind, dims, **BF16_COMMON, counts=[(0, 0), (8, 3)])
    assert failed["outcome"] == FAIL
    assert failed["counts"][1] == {"failed": 8, "non_finite": 3}
    assert not {"kind", "dtype", "layout", "condition"} & set(failed)
    json.dumps(failed, allow_nan=False)


@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_broken_bf16_result_has_the_condition_and_the_shape(kind, condition):
    dims, shape = BF16_SHAPES[kind]
    assert bf16_broken(condition, kind, dims, **BF16_COMMON) == {
        "outcome": BROKEN,
        "condition": condition,
        "shape": shape,
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
    }


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_failed_is_bounded_by_the_output_elements_of_the_kind(kind):
    dims, _ = BF16_SHAPES[kind]
    at_bound = bf16_completed(kind, dims, draws=1, rtol=0, atol=0, counts=[(8, 0)])
    assert at_bound["counts"] == [{"failed": 8, "non_finite": 0}]
    with pytest.raises(ValueError, match=r"^counts\[0\]\.failed: "):
        bf16_completed(kind, dims, draws=1, rtol=0, atol=0, counts=[(9, 0)])


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (None, TypeError),
        (b"gemm", TypeError),
        ("conv", ValueError),
        ("GEMM", ValueError),
    ],
)
def test_an_unknown_bf16_kind_is_refused(kind, expected):
    with pytest.raises(expected, match=r"^kind: "):
        bf16_completed(kind, (2, 4), **BF16_COMMON, counts=[(0, 0), (0, 0)])
    with pytest.raises(expected, match=r"^kind: "):
        bf16_broken("time_limit", kind, (2, 4), **BF16_COMMON)


@pytest.mark.parametrize(
    ("kind", "dims", "expected", "name"),
    [
        ("gemm", [2, 3, 4], TypeError, "dims"),
        ("gemm", (2, 4), ValueError, "dims"),
        ("rmsnorm", (2, 3, 4), ValueError, "dims"),
        ("swiglu", (2,), ValueError, "dims"),
        ("elementwise_add", (), ValueError, "dims"),
        ("gemm", (2, True, 4), TypeError, "k"),
        ("rmsnorm", (0, 4), ValueError, "m"),
        ("swiglu", (2, 0), ValueError, "n"),
        ("elementwise_add", (2, 4.0), TypeError, "n"),
    ],
)
def test_bf16_dims_outside_the_rule_are_refused(kind, dims, expected, name):
    with pytest.raises(expected, match=rf"^{name}: "):
        bf16_completed(kind, dims, **BF16_COMMON, counts=[(0, 0), (0, 0)])
    with pytest.raises(expected, match=rf"^{name}: "):
        bf16_broken("exit_status", kind, dims, **BF16_COMMON)


def test_the_bf16_condition_is_checked_before_the_kind():
    with pytest.raises(ValueError, match=r"^condition: "):
        bf16_broken("cache_differs", "conv", (2, 4), **BF16_COMMON)
    with pytest.raises(TypeError, match=r"^condition: "):
        bf16_broken(None, "gemm", (2, 3, 4), **BF16_COMMON)


@pytest.mark.parametrize(
    ("name", "value", "expected"),
    [
        ("draws", 0, ValueError),
        ("draws", True, TypeError),
        ("rtol", -1, ValueError),
        ("atol", "0", TypeError),
    ],
)
def test_bf16_draws_and_tolerance_follow_the_rule_of_the_first_case(
    name, value, expected
):
    given = {**BF16_COMMON, name: value}
    with pytest.raises(expected, match=rf"^{name}: "):
        bf16_broken("report_form", "rmsnorm", (2, 4), **given)


def test_bf16_counts_follow_the_rule_of_the_first_case():
    with pytest.raises(ValueError, match=r"^counts: "):
        bf16_completed("swiglu", (2, 4), **BF16_COMMON, counts=[(0, 0)])
    with pytest.raises(ValueError, match=r"^counts\[1\]\.non_finite: "):
        bf16_completed("swiglu", (2, 4), **BF16_COMMON, counts=[(0, 0), (1, 2)])


# A rope check (ADR-0177 decision 3, HQ-0077; ADR-0180)

# Test values, not dimensions, draws or a tolerance of the package.
ROPE_DIMS = (2, 3, 4)
ROPE_SHAPE = {"m": 2, "h": 3, "d": 4}
ROPE_OUTPUT = 2 * 3 * 4


def test_a_rope_result_names_m_h_and_d():
    passed = bf16_completed("rope", ROPE_DIMS, **BF16_COMMON, counts=[(0, 0)] * 2)
    assert passed == {
        "outcome": PASS,
        "shape": ROPE_SHAPE,
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
        "counts": [{"failed": 0, "non_finite": 0}] * 2,
    }
    assert list(passed["shape"]) == ["m", "h", "d"]
    failed = bf16_completed("rope", ROPE_DIMS, **BF16_COMMON, counts=[(0, 0), (1, 0)])
    assert failed["outcome"] == FAIL
    assert failed["counts"] == [
        {"failed": 0, "non_finite": 0},
        {"failed": 1, "non_finite": 0},
    ]
    json.dumps(failed, allow_nan=False)


@pytest.mark.parametrize("condition", CONDITIONS)
def test_a_broken_rope_result_has_the_condition_and_m_h_d(condition):
    assert bf16_broken(condition, "rope", ROPE_DIMS, **BF16_COMMON) == {
        "outcome": BROKEN,
        "condition": condition,
        "shape": ROPE_SHAPE,
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
    }


def test_rope_failed_is_bounded_by_m_h_d():
    at_bound = bf16_completed(
        "rope", ROPE_DIMS, draws=1, rtol=0, atol=0, counts=[(ROPE_OUTPUT, 3)]
    )
    assert at_bound["counts"] == [{"failed": ROPE_OUTPUT, "non_finite": 3}]
    with pytest.raises(ValueError, match=r"^counts\[0\]\.failed: .*m \* h \* d"):
        bf16_completed(
            "rope", ROPE_DIMS, draws=1, rtol=0, atol=0, counts=[(ROPE_OUTPUT + 1, 0)]
        )
    with pytest.raises(ValueError, match=r"^counts\[0\]: must have 2 items"):
        bf16_completed("rope", ROPE_DIMS, draws=1, rtol=0, atol=0, counts=[(0, 0, 0)])


@pytest.mark.parametrize(
    ("dims", "expected", "name"),
    [
        ((2, 4), ValueError, "dims"),
        ((2, 3, 4, 5), ValueError, "dims"),
        ([2, 3, 4], TypeError, "dims"),
        ((True, 3, 4), TypeError, "m"),
        ((2, 0, 4), ValueError, "h"),
        ((2, 3, 0), ValueError, "d"),
        ((2, 3, 5), ValueError, "d"),
        ((2, 3, 4.0), TypeError, "d"),
    ],
)
def test_rope_dims_outside_the_contract_are_refused(dims, expected, name):
    with pytest.raises(expected, match=rf"^{name}: "):
        bf16_completed("rope", dims, **BF16_COMMON, counts=[(0, 0), (0, 0)])
    with pytest.raises(expected, match=rf"^{name}: "):
        bf16_broken("time_limit", "rope", dims, **BF16_COMMON)


def test_an_odd_d_is_refused_before_draws():
    with pytest.raises(ValueError, match=r"^d: must be even, got 3$"):
        bf16_broken("time_limit", "rope", (1, 1, 3), draws=0, rtol=0, atol=0)


# An sdpa_kv_cache check (ADR-0177 decision 3, HQ-0077; ADR-0165 decision 8)

# Test values, not dimensions, draws or a tolerance of the package.
SDPA = "sdpa_kv_cache"
SDPA_DIMS = (2, 3, 4, 2, 4)
SDPA_SHAPE = {"m": 2, "l": 3, "h": 4, "h_kv": 2, "d": 4}
SDPA_OUTPUT = 2 * 4 * 4
SDPA_CACHE = 2 * (3 + 2 * 2) * 2 * 4
SDPA_COMMON = {"draws": 2, "rtol": 0, "atol": 2**-9}


def sdpa_completed(counts, dims=SDPA_DIMS):
    return bf16_completed(SDPA, dims, **SDPA_COMMON, counts=counts)


def test_a_passing_sdpa_result_has_the_five_members_and_cache_differs():
    passed = sdpa_completed([(0, 0, 0), (0, 0, 0)])
    assert passed == {
        "outcome": PASS,
        "shape": SDPA_SHAPE,
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2**-9},
        "counts": [{"failed": 0, "non_finite": 0, "cache_differs": 0}] * 2,
    }
    assert list(passed) == ["outcome", "shape", "draws", "tolerance", "counts"]
    assert list(passed["shape"]) == ["m", "l", "h", "h_kv", "d"]
    assert list(passed["counts"][0]) == ["failed", "non_finite", "cache_differs"]
    assert not {"kind", "dtype", "layout", "condition"} & set(passed)
    assert json.loads(json.dumps(passed, allow_nan=False)) == passed


@pytest.mark.parametrize(
    "entry",
    [(1, 0, 0), (0, 0, 1), (3, 1, 5), (SDPA_OUTPUT, SDPA_OUTPUT, SDPA_CACHE)],
    ids=["failed-only", "cache-only", "both", "both-at-bounds"],
)
def test_an_sdpa_result_fails_by_failed_or_by_cache_differs(entry):
    failed = sdpa_completed([(0, 0, 0), entry])
    assert failed["outcome"] == FAIL
    assert failed["counts"][1] == dict(
        zip(("failed", "non_finite", "cache_differs"), entry, strict=True)
    )


def test_an_sdpa_entry_may_be_draw_counts_of_the_judge():
    entries = (DrawCounts(0, 0, 0, 0), DrawCounts(0, 0, 1, 1))
    failed = sdpa_completed(entries)
    assert failed["outcome"] == FAIL
    assert failed["counts"][1] == {"failed": 0, "non_finite": 0, "cache_differs": 2}
    assert type(failed["counts"][1]) is dict


@pytest.mark.parametrize(
    ("dims", "output", "cache"),
    [((2, 3, 4, 2, 4), 32, 112), ((1, 2, 3, 3, 2), 6, 48), ((3, 3, 2, 2, 1), 6, 36)],
    ids=["h-multiple-of-h_kv", "h-equals-h_kv", "no-cached-row"],
)
def test_the_sdpa_bounds_are_the_output_and_the_cache_elements(dims, output, cache):
    at = sdpa_completed([(output, 0, cache)] * 2, dims)
    assert at["counts"][0] == {
        "failed": output,
        "non_finite": 0,
        "cache_differs": cache,
    }
    with pytest.raises(ValueError, match=r"^counts\[0\]\.failed: .*m \* h \* d"):
        sdpa_completed([(output + 1, 0, 0), (0, 0, 0)], dims)
    with pytest.raises(
        ValueError, match=r"^counts\[1\]\.cache_differs: .*2 \* \(l \+ 2 \* m\)"
    ):
        sdpa_completed([(0, 0, 0), (0, 0, cache + 1)], dims)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-1, ValueError),
        (1.0, TypeError),
        (True, TypeError),
        (False, TypeError),
        ("0", TypeError),
        (None, TypeError),
        (2**70, ValueError),
    ],
)
def test_a_cache_differs_outside_the_rule_is_refused(value, expected):
    with pytest.raises(expected, match=r"^counts\[1\]\.cache_differs: "):
        sdpa_completed([(0, 0, 0), (0, 0, value)])


@pytest.mark.parametrize("entry", [(0, 0), (0, 0, 0, 0), ()])
def test_an_sdpa_entry_of_another_length_is_refused(entry):
    with pytest.raises(ValueError, match=r"^counts\[0\]: must have 3 items"):
        sdpa_completed([entry, (0, 0, 0)])


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_an_entry_with_cache_differs_is_refused_for_the_other_kinds(kind):
    dims, _ = BF16_SHAPES[kind]
    with pytest.raises(ValueError, match=r"^counts\[0\]: must have 2 items"):
        bf16_completed(kind, dims, **BF16_COMMON, counts=[(0, 0, 0), (0, 0)])
    with pytest.raises(ValueError, match=r"^counts\[0\]: must have 2 items"):
        completed(**SMALL, counts=[(0, 0, 0), (0, 0)])


def test_the_sdpa_failed_and_non_finite_keep_the_rule_of_the_first_case():
    with pytest.raises(ValueError, match=r"^counts\[0\]\.non_finite: "):
        sdpa_completed([(1, 2, 0), (0, 0, 0)])
    with pytest.raises(TypeError, match=r"^counts\[0\]\.failed: "):
        sdpa_completed([(True, 0, 0), (0, 0, 0)])
    with pytest.raises(ValueError, match=r"^counts\[0\]\.failed: "):
        sdpa_completed([(-1, 0, 0), (0, 0, 0)])
    with pytest.raises(ValueError, match=r"^counts: "):
        sdpa_completed([(0, 0, 0)])


def test_the_counts_of_an_sdpa_result_share_nothing_with_the_argument():
    counts = [(0, 0, 1), (2, 0, 0)]
    result = sdpa_completed(counts)
    assert counts == [(0, 0, 1), (2, 0, 0)]
    other = sdpa_completed(counts)
    assert result == other
    assert result["counts"][0] is not other["counts"][0]


@pytest.mark.parametrize("condition", CONDITIONS)
def test_a_broken_sdpa_result_has_the_condition_and_the_five_members(condition):
    assert bf16_broken(condition, SDPA, SDPA_DIMS, **SDPA_COMMON) == {
        "outcome": BROKEN,
        "condition": condition,
        "shape": SDPA_SHAPE,
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2**-9},
    }


@pytest.mark.parametrize(
    ("dims", "expected", "name"),
    [
        ((2, 4), ValueError, "dims"),
        ((2, 3, 4, 2, 4, 1), ValueError, "dims"),
        ([2, 3, 4, 2, 4], TypeError, "dims"),
        ((2, 3, 4, 0, 4), ValueError, "h_kv"),
        ((2, 3, True, 2, 4), TypeError, "h"),
        ((2, 3.0, 4, 2, 4), TypeError, "l"),
        ((2, 3, 4, 2, 0), ValueError, "d"),
    ],
)
def test_sdpa_dims_outside_the_rule_are_refused(dims, expected, name):
    with pytest.raises(expected, match=rf"^{name}: "):
        sdpa_completed([(0, 0, 0), (0, 0, 0)], dims)
    with pytest.raises(expected, match=rf"^{name}: "):
        bf16_broken("check_value", SDPA, dims, **SDPA_COMMON)


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_the_four_kinds_and_fp32_gemm_give_the_results_they_gave(kind):
    dims, _ = BF16_SHAPES[kind]
    result = bf16_completed(kind, dims, **BF16_COMMON, counts=[(0, 0), (8, 3)])
    assert result["counts"] == [
        {"failed": 0, "non_finite": 0},
        {"failed": 8, "non_finite": 3},
    ]
    assert result["outcome"] == FAIL
    assert completed(**EXAMPLE, counts=ZEROS) == ADR_PASS
    assert completed(**EXAMPLE, counts=((0, 0), (37, 2))) == ADR_FAIL
    with pytest.raises(
        ValueError, match=r"^counts\[0\]\.failed: must be at most m \* n"
    ):
        bf16_completed(kind, dims, draws=1, rtol=0, atol=0, counts=[(9, 0)])


# The v2 result of correctness.check (ADR-0183 decisions 3, 5 and 6)

# Test values, not dimensions, draws or a tolerance of the package.
V2_COMMON = {"draws": 2, "rtol": 1e-4, "atol": 0.01}
V2_TOLERANCE = {"rtol": 1e-4, "atol": 0.01}
V2_CASES = {
    ("gemm", "fp32"): ((1, 2, 3), ("m", "k", "n"), ("c",), {"c": 3}),
    ("gemm", "bf16"): ((1, 2, 3), ("m", "k", "n"), ("c",), {"c": 3}),
    ("rmsnorm", "bf16"): ((2, 4), ("m", "n"), ("y",), {"y": 8}),
    ("elementwise_add", "bf16"): ((2, 4), ("m", "n"), ("c",), {"c": 8}),
    ("swiglu", "bf16"): ((2, 4), ("m", "n"), ("out",), {"out": 8}),
    ("rope", "bf16"): ((1, 2, 4), ("m", "h", "d"), ("out",), {"out": 8}),
    ("sdpa_kv_cache", "bf16"): (
        (2, 3, 4, 2, 4),
        ("m", "l", "h", "h_kv", "d"),
        ("cache_k", "cache_v", "out"),
        {"cache_k": 56, "cache_v": 56, "out": 32},
    ),
}
SDPA_TRIPLE = ("sdpa_kv_cache", "bf16", "row_major")


def table_entry(kind, dtype):
    (found,) = (
        entry for key, entry in contract_table.TABLE.items() if key[:2] == (kind, dtype)
    )
    return found


SDPA_ENTRY = table_entry("sdpa_kv_cache", "bf16")
GEMM_ENTRY = table_entry("gemm", "fp32")
SDPA_V2_DIMS = (2, 3, 4, 2, 4)


def zero_counts(case, names, draws=2):
    exact = check_result.BIT_EXACT.get((*case, "row_major"), ())
    return {name: [0 if name in exact else (0, 0)] * draws for name in names}


def sdpa_v2(counts, dims=SDPA_V2_DIMS, **changes):
    return v2_completed(SDPA_ENTRY, dims, **{**V2_COMMON, **changes}, counts=counts)


def sdpa_counts(cache_k=(0, 0), cache_v=(0, 0), out=((0, 0), (0, 0))):
    return {"cache_k": list(cache_k), "cache_v": list(cache_v), "out": list(out)}


def test_the_table_has_the_seven_contracts_of_the_cases():
    assert [key[:2] for key in contract_table.TABLE] == list(V2_CASES)


@pytest.mark.parametrize("case", list(V2_CASES), ids="-".join)
def test_a_passing_v2_result_of_each_contract(case):
    kind, dtype = case
    dims, members, names, _ = V2_CASES[case]
    entry = table_entry(kind, dtype)
    assert output_operands(entry, dims) == names
    result = v2_completed(entry, dims, **V2_COMMON, counts=zero_counts(case, names))
    assert list(result) == [
        "outcome",
        "contract_key",
        "shape",
        "draws",
        "tolerance",
        "counts",
    ]
    assert result["outcome"] == PASS
    assert result["contract_key"] == {
        "kind": kind,
        "dtype": dtype,
        "layout": "row_major",
    }
    assert list(result["shape"]) == list(members)
    assert tuple(result["shape"].values()) == dims
    assert result["draws"] == 2
    assert result["tolerance"] == V2_TOLERANCE
    assert list(result["counts"]) == list(names)
    for name, entries in result["counts"].items():
        bit_exact = case == SDPA_TRIPLE[:2] and name != "out"
        expected = {"differs": 0} if bit_exact else {"failed": 0, "non_finite": 0}
        assert entries == [expected, expected]
        assert type(entries) is list
    assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize("case", list(V2_CASES), ids="-".join)
def test_a_v2_result_fails_by_one_failed_and_holds_the_operand_bounds(case):
    dims, _, names, sizes = V2_CASES[case]
    entry = table_entry(*case)
    tolerance = names[-1]
    counts = zero_counts(case, names)
    counts[tolerance] = [(0, 0), (1, 0)]
    assert v2_completed(entry, dims, **V2_COMMON, counts=counts)["outcome"] == FAIL
    size = sizes[tolerance]
    counts[tolerance] = [(size, size), (0, 0)]
    result = v2_completed(entry, dims, **V2_COMMON, counts=counts)
    assert result["counts"][tolerance][0] == {"failed": size, "non_finite": size}
    counts[tolerance] = [(0, 0), (size + 1, 0)]
    pattern = rf"^counts\.{tolerance}\[1\]\.failed: must be at most the {size} "
    with pytest.raises(ValueError, match=pattern):
        v2_completed(entry, dims, **V2_COMMON, counts=counts)


def test_the_three_check_lines_of_adr_0183_decision_5():
    first = v2_completed(
        GEMM_ENTRY,
        (1, 2048, 8192),
        **V2_COMMON,
        counts={"c": [(0, 0), (0, 0)]},
    )
    second = v2_completed(
        SDPA_ENTRY,
        (1, 128, 32, 8, 64),
        **V2_COMMON,
        counts=sdpa_counts(cache_k=(0, 64)),
    )
    third = v2_broken(
        "build_exit_status",
        table_entry("rmsnorm", "bf16"),
        (512, 2048),
        **V2_COMMON,
    )
    lines = [
        {
            "outcome": "pass",
            "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
            "shape": {"m": 1, "k": 2048, "n": 8192},
            "draws": 2,
            "tolerance": {"rtol": 1e-4, "atol": 0.01},
            "counts": {
                "c": [{"failed": 0, "non_finite": 0}, {"failed": 0, "non_finite": 0}]
            },
        },
        {
            "outcome": "fail",
            "contract_key": {
                "kind": "sdpa_kv_cache",
                "dtype": "bf16",
                "layout": "row_major",
            },
            "shape": {"m": 1, "l": 128, "h": 32, "h_kv": 8, "d": 64},
            "draws": 2,
            "tolerance": {"rtol": 1e-4, "atol": 0.01},
            "counts": {
                "cache_k": [{"differs": 0}, {"differs": 64}],
                "cache_v": [{"differs": 0}, {"differs": 0}],
                "out": [
                    {"failed": 0, "non_finite": 0},
                    {"failed": 0, "non_finite": 0},
                ],
            },
        },
        {
            "outcome": "broken",
            "condition": "build_exit_status",
            "contract_key": {
                "kind": "rmsnorm",
                "dtype": "bf16",
                "layout": "row_major",
            },
            "shape": {"m": 512, "n": 2048},
            "draws": 2,
            "tolerance": {"rtol": 1e-4, "atol": 0.01},
        },
    ]
    for result, line in zip((first, second, third), lines, strict=True):
        assert result == line
        assert list(result) == list(line)
        assert json.loads(json.dumps(result)) == result


@pytest.mark.parametrize(
    ("counts", "outcome"),
    [
        (sdpa_counts(), PASS),
        (sdpa_counts(out=((0, 0), (1, 1))), FAIL),
        (sdpa_counts(cache_k=(0, 1)), FAIL),
        (sdpa_counts(cache_v=(1, 0)), FAIL),
        (sdpa_counts(cache_k=(56, 0), cache_v=(0, 56), out=((32, 0), (0, 0))), FAIL),
    ],
    ids=["all-zero", "failed-only", "cache_k-only", "cache_v-only", "at-bounds"],
)
def test_the_v2_outcome_is_over_all_operands(counts, outcome):
    result = sdpa_v2(counts)
    assert result["outcome"] == outcome
    assert result["counts"]["cache_k"] == [{"differs": n} for n in counts["cache_k"]]
    assert result["counts"]["cache_v"] == [{"differs": n} for n in counts["cache_v"]]


@pytest.mark.parametrize("condition", CONDITIONS)
@pytest.mark.parametrize("case", list(V2_CASES), ids="-".join)
def test_a_broken_v2_result_has_no_counts(condition, case):
    dims, members, _, _ = V2_CASES[case]
    result = v2_broken(condition, table_entry(*case), dims, **V2_COMMON)
    assert result == {
        "outcome": BROKEN,
        "condition": condition,
        "contract_key": {"kind": case[0], "dtype": case[1], "layout": "row_major"},
        "shape": dict(zip(members, dims, strict=True)),
        "draws": 2,
        "tolerance": V2_TOLERANCE,
    }
    assert list(result) == [
        "outcome",
        "condition",
        "contract_key",
        "shape",
        "draws",
        "tolerance",
    ]


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (None, TypeError),
        (tuple(GEMM_ENTRY), TypeError),
        (("gemm", "fp32", "row_major", "c"), TypeError),
        (contract_table.Entry(GEMM_ENTRY.contract, True, False), ValueError),
        (contract_table.Entry(check_result, True, True), ValueError),
    ],
    ids=["none", "plain-tuple", "table-key", "other-flags", "no-contract"],
)
def test_an_entry_not_of_the_table_is_refused(entry, expected):
    with pytest.raises(expected, match=r"^entry: "):
        v2_completed(entry, (1, 2, 3), **V2_COMMON, counts={"c": [(0, 0)] * 2})
    with pytest.raises(expected, match=r"^entry: "):
        v2_broken("time_limit", entry, (1, 2, 3), **V2_COMMON)
    with pytest.raises(expected, match=r"^entry: "):
        output_operands(entry, (1, 2, 3))


@pytest.mark.parametrize(
    ("case", "dims", "expected", "name"),
    [
        (("gemm", "fp32"), (1, 2), ValueError, "dims"),
        (("gemm", "fp32"), [1, 2, 3], TypeError, "dims"),
        (("gemm", "fp32"), (1, 2, 3, 4), ValueError, "dims"),
        (("gemm", "fp32"), (1, 0, 3), ValueError, "k"),
        (("gemm", "fp32"), (1, 2.0, 3), TypeError, "k"),
        (("gemm", "fp32"), (True, 2, 3), TypeError, "m"),
        (("gemm", "fp32"), (2**53, 2, 3), ValueError, "dims"),
        (("rope", "bf16"), (1, 2, 3), ValueError, "d"),
        (("sdpa_kv_cache", "bf16"), (3, 2, 4, 2, 4), ValueError, "dims"),
        (("sdpa_kv_cache", "bf16"), (2, 3, 3, 2, 4), ValueError, "dims"),
    ],
    ids=[
        "too-few",
        "list",
        "too-many",
        "zero",
        "float",
        "bool",
        "beyond-a-record",
        "rope-odd-d",
        "sdpa-l-below-m",
        "sdpa-h-not-a-multiple",
    ],
)
def test_dims_outside_the_contract_are_refused(case, dims, expected, name):
    entry = table_entry(*case)
    with pytest.raises(expected, match=rf"^{name}: "):
        v2_broken("time_limit", entry, dims, **V2_COMMON)
    with pytest.raises(expected, match=rf"^{name}: "):
        output_operands(entry, dims)


@pytest.mark.parametrize(
    ("changes", "expected", "name"),
    [
        ({"draws": 0}, ValueError, "draws"),
        ({"draws": 2.0}, TypeError, "draws"),
        ({"rtol": -1.0}, ValueError, "rtol"),
        ({"rtol": math.nan}, ValueError, "rtol"),
        ({"atol": "0.01"}, TypeError, "atol"),
        ({"atol": math.inf}, ValueError, "atol"),
    ],
)
def test_draws_and_tolerance_outside_the_rule_are_refused(changes, expected, name):
    with pytest.raises(expected, match=rf"^{name}: "):
        sdpa_v2(sdpa_counts(), **changes)
    with pytest.raises(expected, match=rf"^{name}: "):
        v2_broken("time_limit", SDPA_ENTRY, SDPA_V2_DIMS, **{**V2_COMMON, **changes})


@pytest.mark.parametrize(
    ("condition", "expected"),
    [("timeout", ValueError), (None, TypeError), ("", ValueError), (3, TypeError)],
)
def test_a_v2_broken_condition_outside_the_list_is_refused(condition, expected):
    with pytest.raises(expected, match=r"^condition: "):
        v2_broken(condition, SDPA_ENTRY, SDPA_V2_DIMS, **V2_COMMON)


def without(counts, name):
    return {key: value for key, value in counts.items() if key != name}


@pytest.mark.parametrize(
    ("counts", "expected", "pattern"),
    [
        (None, TypeError, r"^counts: must be a dict"),
        (list(sdpa_counts().items()), TypeError, r"^counts: must be a dict"),
        (without(sdpa_counts(), "cache_v"), ValueError, r"^counts: .*'cache_v'"),
        (without(sdpa_counts(), "out"), ValueError, r"^counts: .*'out'"),
        ({**sdpa_counts(), "q": [(0, 0)] * 2}, ValueError, r"^counts: .*'q'"),
        ({**sdpa_counts(), 1: [(0, 0)] * 2}, ValueError, r"^counts: .*1"),
        (sdpa_counts(cache_k=[0]), ValueError, r"^counts\.cache_k: must have 2"),
        (sdpa_counts(out=[(0, 0)] * 3), ValueError, r"^counts\.out: must have 2"),
        ({**sdpa_counts(), "out": None}, TypeError, r"^counts\.out: must be a list"),
        (
            sdpa_counts(cache_k=((0, 0), 0)),
            TypeError,
            r"^counts\.cache_k\[0\]\.differs: ",
        ),
        (
            sdpa_counts(out=(0, (0, 0))),
            TypeError,
            r"^counts\.out\[0\]: must be a tuple",
        ),
        (
            sdpa_counts(out=((0, 0, 0), (0, 0))),
            ValueError,
            r"^counts\.out\[0\]: must have 2",
        ),
        (
            sdpa_counts(out=([0, 0], (0, 0))),
            TypeError,
            r"^counts\.out\[0\]: must be a tuple",
        ),
        (
            sdpa_counts(cache_k=(0, 57)),
            ValueError,
            r"^counts\.cache_k\[1\]\.differs: must be at most \(l \+ 2 \* m\)",
        ),
        (
            sdpa_counts(cache_v=(57, 0)),
            ValueError,
            r"^counts\.cache_v\[0\]\.differs: must be at most \(l \+ 2 \* m\)",
        ),
        (sdpa_counts(cache_v=(-1, 0)), ValueError, r"^counts\.cache_v\[0\]\.differs"),
        (sdpa_counts(cache_v=(True, 0)), TypeError, r"^counts\.cache_v\[0\]\.differs"),
        (sdpa_counts(cache_v=(1.0, 0)), TypeError, r"^counts\.cache_v\[0\]\.differs"),
        (
            sdpa_counts(out=((33, 0), (0, 0))),
            ValueError,
            r"^counts\.out\[0\]\.failed: must be at most the 32 elements of out",
        ),
        (
            sdpa_counts(out=((1, 2), (0, 0))),
            ValueError,
            r"^counts\.out\[0\]\.non_finite: must be at most failed",
        ),
        (sdpa_counts(out=((-1, 0), (0, 0))), ValueError, r"^counts\.out\[0\]\.failed"),
        (
            sdpa_counts(out=((0, 0), (0, -1))),
            ValueError,
            r"^counts\.out\[1\]\.non_finite",
        ),
        (sdpa_counts(out=((0.0, 0), (0, 0))), TypeError, r"^counts\.out\[0\]\.failed"),
        (
            sdpa_counts(out=((0, None), (0, 0))),
            TypeError,
            r"^counts\.out\[0\]\.non_finite",
        ),
        (
            sdpa_counts(cache_k=(2**70, 0)),
            ValueError,
            r"^counts\.cache_k\[0\]\.differs",
        ),
    ],
)
def test_v2_counts_outside_the_rule_are_refused(counts, expected, pattern):
    with pytest.raises(expected, match=pattern):
        sdpa_v2(counts)


def test_a_tolerance_operand_takes_counts_of_the_judge_and_the_bound_per_size():
    counts = {"c": (Counts(0, 0), Counts(8, 8))}
    result = v2_completed(GEMM_ENTRY, (2, 3, 4), **V2_COMMON, counts=counts)
    assert result["counts"] == {
        "c": [{"failed": 0, "non_finite": 0}, {"failed": 8, "non_finite": 8}]
    }
    assert result["outcome"] == FAIL
    with pytest.raises(ValueError, match=r"^counts\.c\[0\]\.failed: .*8 elements"):
        v2_completed(GEMM_ENTRY, (2, 3, 4), **V2_COMMON, counts={"c": [(9, 0)] * 2})


def test_a_gemm_counts_entry_of_the_bit_exact_form_is_refused():
    with pytest.raises(TypeError, match=r"^counts\.c\[0\]: must be a tuple"):
        v2_completed(GEMM_ENTRY, (1, 2, 3), **V2_COMMON, counts={"c": [0, 0]})


def test_only_the_caches_of_sdpa_are_bit_exact():
    assert dict(check_result.BIT_EXACT) == {SDPA_TRIPLE: ("cache_k", "cache_v")}
    with pytest.raises(TypeError):
        check_result.BIT_EXACT[("gemm", "fp32", "row_major")] = ("c",)


def test_the_v2_checks_follow_their_order():
    nothing = {"draws": None, "rtol": None, "atol": None}
    with pytest.raises(TypeError, match=r"^condition: "):
        v2_broken(None, None, None, **nothing)
    with pytest.raises(TypeError, match=r"^entry: "):
        v2_completed(None, None, **nothing, counts=None)
    with pytest.raises(TypeError, match=r"^dims: "):
        v2_completed(SDPA_ENTRY, None, **nothing, counts=None)
    with pytest.raises(TypeError, match=r"^draws: "):
        sdpa_v2(None, **nothing)
    with pytest.raises(TypeError, match=r"^rtol: "):
        sdpa_v2(None, rtol=None, atol=None)
    with pytest.raises(TypeError, match=r"^atol: "):
        sdpa_v2(None, atol=None)
    with pytest.raises(TypeError, match=r"^counts: "):
        sdpa_v2(None)


def test_a_v2_result_shares_nothing_with_its_arguments():
    counts = sdpa_counts(out=[(1, 0), (0, 0)])
    before = copy.deepcopy(counts)
    one = sdpa_v2(counts)
    assert counts == before
    one["counts"]["out"][0]["failed"] = 9
    one["shape"]["m"] = 9
    one["contract_key"]["kind"] = "x"
    one["tolerance"]["rtol"] = 9.0
    assert sdpa_v2(counts) != one
    assert counts == before
    assert SDPA_ENTRY.contract.KIND == "sdpa_kv_cache"


def test_v2_builders_have_no_default_and_keyword_only_values():
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    for function, positional in (
        (v2_completed, ["entry", "dims"]),
        (v2_broken, ["condition", "entry", "dims"]),
        (output_operands, ["entry", "dims"]),
    ):
        parameters = list(inspect.signature(function).parameters.values())
        assert all(p.default is inspect.Parameter.empty for p in parameters)
        assert [p.name for p in parameters[: len(positional)]] == positional
        assert all(p.kind is keyword_only for p in parameters[len(positional) :])


def test_a_v2_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sdpa_v2(sdpa_counts())
    v2_broken("time_limit", SDPA_ENTRY, SDPA_V2_DIMS, **V2_COMMON)
    assert list(tmp_path.iterdir()) == []


# An sdpa_kv_cache result of today from per-allocation DrawCounts (ADR-0183 decision 9 item 1)


def test_an_sdpa_result_of_today_sums_the_two_allocations():
    result = sdpa_completed([DrawCounts(0, 0, 3, 4), DrawCounts(0, 0, 0, 0)])
    assert result["counts"][0] == {"failed": 0, "non_finite": 0, "cache_differs": 7}
    assert result["outcome"] == FAIL
    at = sdpa_completed([DrawCounts(0, 0, 56, 56)] * 2)
    assert at["counts"][1]["cache_differs"] == SDPA_CACHE


@pytest.mark.parametrize(
    ("entry", "expected", "pattern"),
    [
        (DrawCounts(0, 0, 57, 0), ValueError, r"^counts\[0\]\.cache_k_differences: "),
        (DrawCounts(0, 0, 0, 57), ValueError, r"^counts\[0\]\.cache_v_differences: "),
        (DrawCounts(0, 0, -1, 1), ValueError, r"^counts\[0\]\.cache_k_differences: "),
        (DrawCounts(0, 0, 0, True), TypeError, r"^counts\[0\]\.cache_v_differences: "),
        (DrawCounts(0, 0, 0, 1.0), TypeError, r"^counts\[0\]\.cache_v_differences: "),
        (DrawCounts(33, 0, 0, 0), ValueError, r"^counts\[0\]\.failed: "),
    ],
)
def test_per_allocation_counts_outside_the_rule_are_refused(entry, expected, pattern):
    with pytest.raises(expected, match=pattern):
        sdpa_completed([entry, (0, 0, 0)])
