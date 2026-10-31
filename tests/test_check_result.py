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
    BROKEN,
    CONDITIONS,
    FAIL,
    PASS,
    output_operands,
    v2_broken,
    v2_completed,
)
from hilclaw.harness.verification_arrays import Counts

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


def refused(expected, function, name, *positional, **arguments):
    with pytest.raises(expected) as caught:
        function(*positional, **arguments)
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
        "BIT_EXACT",
        "output_operands",
        "v2_completed",
        "v2_broken",
    }


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


# The rules of every value of a result, over both builders

SMALL_DIMS = (2, 3, 4)
SMALL_COMMON = {"draws": 2, "rtol": 0.5, "atol": 0.25}
SMALL_COUNTS = {"c": [(0, 0), (0, 0)]}


def call_completed(dims=SMALL_DIMS, **changed):
    arguments = {**SMALL_COMMON, "counts": SMALL_COUNTS, **changed}
    return v2_completed(GEMM_ENTRY, dims, **arguments)


def call_broken(dims=SMALL_DIMS, **changed):
    return v2_broken("exit_status", GEMM_ENTRY, dims, **{**SMALL_COMMON, **changed})


BOTH = [call_completed, call_broken]


def values_of(value):
    yield value
    if isinstance(value, dict):
        for member in value.values():
            yield from values_of(member)
    if isinstance(value, list):
        for item in value:
            yield from values_of(item)


@pytest.mark.parametrize("function", BOTH)
def test_a_result_is_a_json_object_with_no_null_and_no_tuple(function):
    result = function()
    tools.check_json_object(result)
    assert json.loads(tools.encode(result)) == result
    for value in values_of(result):
        assert value is not None
        assert type(value) is not tuple


def test_the_smallest_arguments():
    result = v2_completed(
        GEMM_ENTRY, (1, 1, 1), draws=1, rtol=0, atol=0, counts={"c": [(1, 1)]}
    )
    assert result == {
        "outcome": FAIL,
        "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
        "shape": {"m": 1, "k": 1, "n": 1},
        "draws": 1,
        "tolerance": {"rtol": 0.0, "atol": 0.0},
        "counts": {"c": [{"failed": 1, "non_finite": 1}]},
    }


def test_counts_as_a_list_a_tuple_and_the_tuples_of_the_harness():
    expected = call_completed(counts={"c": [(8, 0), (0, 0)]})
    assert call_completed(counts={"c": ((8, 0), (0, 0))}) == expected
    assert call_completed(counts={"c": [Counts(8, 0), Counts(0, 0)]}) == expected


def test_a_tuple_subclass_is_read_as_the_tuple_it_is():
    result = call_completed(counts={"c": [Pair((1, 0)), (0, 0)]})
    assert result["counts"]["c"][0] == {"failed": 1, "non_finite": 0}
    with pytest.raises(ValueError, match=r"^counts\.c\[0\]: must have 2 items"):
        call_completed(counts={"c": [Pair((0, 0, 0)), (0, 0)]})


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
@pytest.mark.parametrize(("value", "expected"), [*BAD_INTEGERS, (Number(1), TypeError)])
def test_a_bad_number_of_draws_is_refused(function, value, expected):
    refused(expected, function, "draws", draws=value)


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize(("value", "expected"), [*BAD_INTEGERS, (Number(1), TypeError)])
def test_a_bad_dimension_is_refused(function, position, value, expected):
    dims = list(SMALL_DIMS)
    dims[position] = value
    refused(expected, function, "mkn"[position], tuple(dims))


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["rtol", "atol"])
@pytest.mark.parametrize(("value", "expected"), [*BAD_NUMBERS, (-1, ValueError)])
def test_a_bad_tolerance_is_refused(function, name, value, expected):
    refused(expected, function, name, **{name: value})


@pytest.mark.parametrize("function", BOTH)
def test_an_int_without_decimal_text_is_refused(function, decimal_limit):
    for value in (decimal_limit, -decimal_limit):
        refused(ValueError, function, "draws", draws=value)
        refused(ValueError, function, "m", (value, 3, 4))


@pytest.mark.parametrize("function", BOTH)
@pytest.mark.parametrize("name", ["rtol", "atol"])
def test_a_tolerance_int_without_decimal_text_is_refused(function, name, decimal_limit):
    refused(ValueError, function, name, **{name: decimal_limit})


def test_a_count_without_decimal_text_is_refused(decimal_limit):
    refused(
        ValueError,
        call_completed,
        "counts.c[0].failed",
        counts={"c": [(decimal_limit, 0), (0, 0)]},
    )
    refused(
        ValueError,
        sdpa_v2,
        "counts.cache_k[0].differs",
        sdpa_counts(cache_k=(decimal_limit, 0)),
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
        ("TIME_LIMIT", ValueError),
        (" time_limit", ValueError),
        ("build_time_limit ", ValueError),
        ("BUILD_EXIT_STATUS", ValueError),
        ("build_exit", ValueError),
        ("build_status", ValueError),
        ("build_timeout", ValueError),
        (b"time_limit", TypeError),
        (("time_limit",), TypeError),
        (Condition.TIME_LIMIT, TypeError),
        (Text("time_limit"), TypeError),
        (Text("build_exit_status"), TypeError),
    ],
)
def test_a_condition_of_another_form_is_refused(condition, expected):
    refused(
        expected,
        v2_broken,
        "condition",
        condition,
        GEMM_ENTRY,
        SMALL_DIMS,
        **SMALL_COMMON,
    )


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ([0, 0], TypeError),
        ((), ValueError),
        ((0,), ValueError),
        ((0, 0, 0), ValueError),
    ],
)
@pytest.mark.parametrize("position", [0, 1])
def test_an_entry_that_is_no_pair_is_refused(entry, expected, position):
    entries = [(0, 0), (0, 0)]
    entries[position] = entry
    refused(expected, call_completed, f"counts.c[{position}]", counts={"c": entries})


@pytest.mark.parametrize(("value", "expected"), [*BAD_COUNT_ITEMS, ("1", TypeError)])
@pytest.mark.parametrize("position", [0, 1])
def test_a_bad_count_is_refused(value, expected, position):
    item = [0, 0]
    item[position] = value
    name = ("failed", "non_finite")[position]
    refused(
        expected,
        call_completed,
        f"counts.c[0].{name}",
        counts={"c": [tuple(item), (0, 0)]},
    )


def test_keyword_arguments_are_required_and_closed():
    with_counts = {**SMALL_COMMON, "counts": SMALL_COUNTS}
    for name in with_counts:
        arguments = {key: value for key, value in with_counts.items() if key != name}
        with pytest.raises(TypeError, match=name):
            v2_completed(GEMM_ENTRY, SMALL_DIMS, **arguments)
    for name in SMALL_COMMON:
        arguments = {key: value for key, value in SMALL_COMMON.items() if key != name}
        with pytest.raises(TypeError, match=name):
            v2_broken("time_limit", GEMM_ENTRY, SMALL_DIMS, **arguments)
    with pytest.raises(TypeError, match="counts"):
        v2_broken("time_limit", GEMM_ENTRY, SMALL_DIMS, **with_counts)
    with pytest.raises(TypeError, match="seed"):
        v2_completed(GEMM_ENTRY, SMALL_DIMS, **with_counts, seed=1)
    with pytest.raises(TypeError):
        v2_completed(GEMM_ENTRY, SMALL_DIMS, *SMALL_COMMON.values(), SMALL_COUNTS)


def test_a_refused_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        v2_broken("timeout", GEMM_ENTRY, SMALL_DIMS, **SMALL_COMMON)
    with pytest.raises(TypeError):
        call_completed(counts=None)
    assert list(tmp_path.iterdir()) == []
