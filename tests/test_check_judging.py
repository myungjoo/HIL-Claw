import ast
import copy
import enum
import inspect
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from hilclaw import check_judging, check_result, contract_table, mock_check, tools
from hilclaw.check_judging import (
    condition_of,
    from_v2_judgement,
    from_v2_report,
    operand_counts,
)
from hilclaw.check_parameters import Bf16CheckParameters
from hilclaw.harness import bf16_rope_verification
from hilclaw.harness.bf16_sdpa_kv_cache_verification import DrawCounts
from hilclaw.harness.verification import (
    END_MARK,
    Broken,
    Judgement,
    Verdict,
    VerificationResult,
    judge_report,
)
from hilclaw.harness.verification_arrays import (
    Counts,
    VerificationArgumentError,
    check_value,
    draw_inputs,
    reference,
)

COMPLETED_MEMBERS = {"outcome", "contract_key", "shape", "draws", "tolerance", "counts"}
BROKEN_MEMBERS = {
    "outcome",
    "condition",
    "contract_key",
    "shape",
    "draws",
    "tolerance",
}

# Test values, not tolerances, dimensions, draws or a seed of the package.
SHAPE = (3, 4, 5)
DRAWS = 3
SEED = 7
LAST = 2**64 - 1
SMALL_V2 = {"draws": DRAWS, "rtol": 1e-5, "atol": 1e-6}
CALL_V2 = {**SMALL_V2, "seed": SEED}
# For this seed the product of the 1 x 1 x 1 draw is exact in binary32.
EXACT_SEED = 302510
ZEROS = (Counts(0, 0),) * DRAWS
ONE_FAILED = (Counts(0, 0), Counts(1, 0), Counts(0, 0))
PASSED = Judgement(None, Verdict.PASS, ZEROS)
FAILED = Judgement(None, Verdict.FAIL, ONE_FAILED)
GEMM_KEY = {"kind": "gemm", "dtype": "fp32", "layout": "row_major"}
GEMM_SHAPE = {"m": 3, "k": 4, "n": 5}

BAD_INTEGERS = [(0, ValueError), (True, TypeError), (1.0, TypeError)]
BAD_NUMBERS = [(-0.1, ValueError), (float("nan"), ValueError), ("0", TypeError)]
BAD_PARAMETERS = [("draws", value, expected) for value, expected in BAD_INTEGERS] + [
    (name, value, expected)
    for name in ("rtol", "atol")
    for value, expected in BAD_NUMBERS
]


class Other(enum.Enum):
    TIMEOUT = enum.auto()


def rounded_references(m, k, n, draws, seed):
    outputs = []
    for draw in range(draws):
        a, b = draw_inputs(m, k, n, seed=seed, draw=draw)
        outputs.append(reference(a, b).astype(np.float32))
    return outputs


def report_of(m, k, n, seed, outputs, wrong_check=()):
    parts = []
    for draw, output in enumerate(outputs):
        value = check_value(*draw_inputs(m, k, n, seed=seed, draw=draw))
        if draw in wrong_check:
            value ^= 1
        parts.append(struct.pack("=I", value))
        parts.append(np.ascontiguousarray(output, dtype=np.float32).tobytes())
    return b"".join(parts) + END_MARK


def passing_report(m, k, n, draws, seed):
    return report_of(m, k, n, seed, rounded_references(m, k, n, draws, seed))


def failing_report():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    outputs[1][2, 4] += np.float32(0.25)
    return report_of(*SHAPE, SEED, outputs)


GOOD = passing_report(*SHAPE, DRAWS, SEED)


def refused(expected, name, function, *positional, **arguments):
    with pytest.raises(expected) as caught:
        function(*positional, **arguments)
    assert type(caught.value) is expected
    assert str(caught.value).startswith(f"{name}: ")


def assert_sound(result, members):
    assert type(result) is dict
    assert set(result) == members
    tools.check_json_object(result)
    assert json.loads(tools.encode(result)) == result


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


def table_entry(kind, dtype):
    (found,) = (
        entry for key, entry in contract_table.TABLE.items() if key[:2] == (kind, dtype)
    )
    return found


GEMM_ENTRY = table_entry("gemm", "fp32")


def judged(judgement, dims=SHAPE, **changed):
    return from_v2_judgement(judgement, GEMM_ENTRY, dims, **{**SMALL_V2, **changed})


def reported(report, dims=SHAPE, **changed):
    return from_v2_report(report, GEMM_ENTRY, dims, **{**CALL_V2, **changed})


def broken_v2(condition, dims=SHAPE, **changed):
    return check_result.v2_broken(
        condition, GEMM_ENTRY, dims, **{**SMALL_V2, **changed}
    )


@pytest.mark.parametrize(
    ("member", "condition"),
    [
        (Broken.TIMEOUT, "time_limit"),
        (Broken.EXIT_STATUS, "exit_status"),
        (Broken.REPORT_FORM, "report_form"),
        (Broken.CHECK_VALUE, "check_value"),
    ],
)
def test_condition_of_gives_the_value_of_the_record(member, condition):
    assert condition_of(member) == condition
    assert type(condition_of(member)) is str


def test_condition_of_over_the_enumeration_gives_the_four_run_conditions():
    values = tuple(condition_of(member) for member in Broken)
    assert values == ("time_limit", "exit_status", "report_form", "check_value")
    assert values == check_result.CONDITIONS[-4:]
    assert not {"build_time_limit", "build_exit_status"} & set(values)
    assert len(list(Broken)) == 4


@pytest.mark.parametrize(
    "value",
    [None, "time_limit", "TIMEOUT", 1, True, Verdict.PASS, Other.TIMEOUT, Broken],
    ids=repr,
)
def test_condition_of_refuses_what_is_no_member_of_broken(value):
    refused(TypeError, "broken", condition_of, value)


def test_a_pass_judgement_gives_the_completed_result():
    result = judged(PASSED)
    assert result == {
        "outcome": "pass",
        "contract_key": GEMM_KEY,
        "shape": GEMM_SHAPE,
        "draws": 3,
        "tolerance": {"rtol": 1e-5, "atol": 1e-6},
        "counts": {"c": [{"failed": 0, "non_finite": 0}] * 3},
    }
    assert_sound(result, COMPLETED_MEMBERS)


def test_a_fail_judgement_gives_the_counts_of_each_draw():
    result = judged(FAILED)
    assert result["outcome"] == "fail"
    assert result["counts"] == {
        "c": [
            {"failed": 0, "non_finite": 0},
            {"failed": 1, "non_finite": 0},
            {"failed": 0, "non_finite": 0},
        ]
    }
    assert_sound(result, COMPLETED_MEMBERS)


@pytest.mark.parametrize("member", list(Broken))
def test_a_broken_judgement_gives_the_broken_result(member):
    result = judged(Judgement(member, None, None))
    assert result == broken_v2(condition_of(member))
    assert_sound(result, BROKEN_MEMBERS)


def test_a_judgement_takes_the_counts_as_a_list_too():
    judgement = Judgement(None, Verdict.FAIL, list(ONE_FAILED))
    assert judged(judgement) == judged(FAILED)


def test_a_report_of_rounded_references_passes():
    result = reported(GOOD)
    assert result["outcome"] == "pass"
    assert result == judged(PASSED)
    assert_sound(result, COMPLETED_MEMBERS)
    assert "seed" not in result


def test_a_report_fails_one_element_outside_the_tolerance():
    result = reported(failing_report())
    assert result == judged(FAILED)
    assert result["outcome"] == "fail"
    assert_sound(result, COMPLETED_MEMBERS)


def test_a_non_finite_output_is_in_both_counts():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    outputs[0][1, 1] = np.nan
    outputs[0][0, 0] = 70.0
    outputs[2][0, 3] = -np.inf
    result = reported(report_of(*SHAPE, SEED, outputs))
    assert result["outcome"] == "fail"
    assert result["counts"]["c"] == [
        {"failed": 2, "non_finite": 1},
        {"failed": 0, "non_finite": 0},
        {"failed": 1, "non_finite": 1},
    ]
    assert_sound(result, COMPLETED_MEMBERS)


@pytest.mark.parametrize(
    "report",
    [GOOD[:-1], GOOD + b"\n", GOOD[:-4] + b"end.", GOOD[:-4], b""],
    ids=["short", "long", "no-end-mark", "cut-before-the-mark", "empty"],
)
def test_a_report_of_a_wrong_form_is_broken(report):
    result = reported(report)
    assert result == broken_v2("report_form")
    assert_sound(result, BROKEN_MEMBERS)


@pytest.mark.parametrize("draw", [0, 1, 2])
def test_a_report_with_a_wrong_check_value_is_broken(draw):
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    report = report_of(*SHAPE, SEED, outputs, wrong_check={draw})
    result = reported(report)
    assert result == broken_v2("check_value")
    assert_sound(result, BROKEN_MEMBERS)


def test_a_wrong_check_value_drops_the_counts_before_it():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    outputs[0][0, :] = 9.0
    report = report_of(*SHAPE, SEED, outputs, wrong_check={2})
    result = reported(report)
    assert result == broken_v2("check_value")
    assert set(result) == BROKEN_MEMBERS


def test_a_report_made_for_another_seed_is_broken():
    report = passing_report(*SHAPE, DRAWS, SEED + 1)
    assert reported(report)["condition"] == "check_value"
    assert reported(report, seed=SEED + 1)["outcome"] == "pass"


@pytest.mark.parametrize("seed", [0, LAST])
def test_a_report_takes_the_whole_range_of_seeds(seed):
    result = reported(passing_report(*SHAPE, 2, seed), draws=2, seed=seed)
    assert result["outcome"] == "pass"
    assert result["draws"] == 2


def test_a_report_of_the_smallest_check():
    unit = {"draws": 1, "seed": SEED}
    result = reported(passing_report(1, 1, 1, 1, SEED), (1, 1, 1), **unit)
    assert result == {
        "outcome": "pass",
        "contract_key": GEMM_KEY,
        "shape": {"m": 1, "k": 1, "n": 1},
        "draws": 1,
        "tolerance": {"rtol": 1e-5, "atol": 1e-6},
        "counts": {"c": [{"failed": 0, "non_finite": 0}]},
    }
    off = report_of(1, 1, 1, SEED, [np.full((1, 1), np.inf, dtype=np.float32)])
    result = reported(off, (1, 1, 1), **unit)
    assert result["counts"]["c"] == [{"failed": 1, "non_finite": 1}]


@pytest.mark.parametrize("zero", [0.0, 0])
def test_a_report_with_a_zero_tolerance(zero):
    unit = {"draws": 1, "seed": EXACT_SEED, "rtol": zero, "atol": zero}
    a, b = draw_inputs(1, 1, 1, seed=EXACT_SEED, draw=0)
    output = reference(a, b).astype(np.float32)
    result = reported(report_of(1, 1, 1, EXACT_SEED, [output]), (1, 1, 1), **unit)
    assert result["outcome"] == "pass"
    assert result["tolerance"] == {"rtol": 0.0, "atol": 0.0}
    assert type(result["tolerance"]["rtol"]) is float
    off = np.nextafter(output, np.float32(2.0))
    result = reported(report_of(1, 1, 1, EXACT_SEED, [off]), (1, 1, 1), **unit)
    assert result["outcome"] == "fail"
    assert result["counts"]["c"] == [{"failed": 1, "non_finite": 0}]


def test_a_report_with_integer_tolerances():
    report = report_of(*SHAPE, SEED, [np.zeros((3, 5), dtype=np.float32)] * DRAWS)
    passed = reported(report, rtol=1, atol=0)
    assert passed["outcome"] == "pass"
    assert passed["tolerance"] == {"rtol": 1.0, "atol": 0.0}
    failed = reported(report, rtol=0, atol=0)
    assert failed["counts"]["c"] == [{"failed": 15, "non_finite": 0}] * DRAWS
    assert_sound(failed, COMPLETED_MEMBERS)


def test_a_report_of_a_wrong_form_for_many_draws_builds_no_counts():
    result = reported(GOOD, draws=2**63)
    assert result == broken_v2("report_form", draws=2**63)
    assert_sound(result, BROKEN_MEMBERS)


def test_a_report_is_the_judging_followed_by_the_judgement():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    reports = {
        "pass": GOOD,
        "fail": failing_report(),
        "report_form": GOOD[:-1],
        "check_value": report_of(*SHAPE, SEED, outputs, wrong_check={1}),
    }
    seen = set()
    for report in reports.values():
        judgement = judge_report(report, m=3, k=4, n=5, **CALL_V2)
        result = reported(report)
        assert result == judged(judgement)
        assert result == reported(report)
        if judgement.broken is None:
            assert result["outcome"] == judgement.verdict.name.lower()
            assert len(result["counts"]["c"]) == len(judgement.counts)
            seen.add(result["outcome"])
        else:
            assert result["outcome"] == "broken"
            assert result["condition"] == condition_of(judgement.broken)
            seen.add(result["condition"])
    assert seen == set(reports)


@pytest.mark.parametrize(
    "judgement",
    [
        None,
        (None, Verdict.PASS, ZEROS),
        {"broken": None, "verdict": Verdict.PASS, "counts": ZEROS},
        VerificationResult(None, Verdict.PASS, ZEROS, None),
        [None, Verdict.PASS, ZEROS],
        "pass",
        Judgement,
    ],
    ids=["none", "tuple", "dict", "verification-result", "list", "str", "class"],
)
def test_what_is_not_exactly_a_judgement_is_refused(judgement):
    refused(TypeError, "judgement", judged, judgement)


@pytest.mark.parametrize("fields", [(), (None,), (None, Verdict.PASS, ZEROS, None)])
def test_a_judgement_without_its_three_fields_is_refused(fields):
    refused(ValueError, "judgement", judged, tuple.__new__(Judgement, fields))


@pytest.mark.parametrize(
    ("judgement", "expected", "name"),
    [
        (Judgement("time_limit", None, None), TypeError, "judgement.broken"),
        (Judgement("TIMEOUT", None, None), TypeError, "judgement.broken"),
        (Judgement(Other.TIMEOUT, None, None), TypeError, "judgement.broken"),
        (Judgement(1, None, None), TypeError, "judgement.broken"),
        (Judgement(False, Verdict.PASS, ZEROS), TypeError, "judgement.broken"),
        (Judgement("time_limit", "pass", None), TypeError, "judgement.broken"),
        (Judgement(None, "pass", ZEROS), TypeError, "judgement.verdict"),
        (Judgement(None, True, ZEROS), TypeError, "judgement.verdict"),
        (Judgement(None, Broken.TIMEOUT, ZEROS), TypeError, "judgement.verdict"),
        (Judgement(Broken.TIMEOUT, "fail", None), TypeError, "judgement.verdict"),
        (Judgement(None, None, None), ValueError, "judgement.verdict"),
        (Judgement(None, None, ZEROS), ValueError, "judgement.verdict"),
        (Judgement(None, Verdict.PASS, None), ValueError, "judgement.counts"),
        (Judgement(None, Verdict.FAIL, None), ValueError, "judgement.counts"),
        (Judgement(None, Verdict.PASS, ONE_FAILED), ValueError, "judgement.verdict"),
        (Judgement(None, Verdict.FAIL, ZEROS), ValueError, "judgement.verdict"),
        (
            Judgement(Broken.CHECK_VALUE, Verdict.FAIL, None),
            ValueError,
            "judgement.verdict",
        ),
        (
            Judgement(Broken.TIMEOUT, Verdict.PASS, ZEROS),
            ValueError,
            "judgement.verdict",
        ),
        (Judgement(Broken.REPORT_FORM, None, ZEROS), ValueError, "judgement.counts"),
        (Judgement(Broken.EXIT_STATUS, None, ()), ValueError, "judgement.counts"),
        (Judgement(Broken.EXIT_STATUS, None, 0), ValueError, "judgement.counts"),
    ],
    ids=str,
)
def test_a_judgement_whose_fields_do_not_agree_is_refused(judgement, expected, name):
    refused(expected, name, judged, judgement)


@pytest.mark.parametrize(
    ("counts", "expected", "name"),
    [
        (ZEROS[:2], ValueError, "counts.c"),
        (ZEROS + ZEROS, ValueError, "counts.c"),
        ((), ValueError, "counts.c"),
        (
            (Counts(0, 0), Counts(1, 2), Counts(0, 0)),
            ValueError,
            "counts.c[1].non_finite",
        ),
        ((Counts(0, 0), Counts(0, 0), Counts(16, 0)), ValueError, "counts.c[2].failed"),
        ((Counts(-1, 0),) * 3, ValueError, "counts.c[0].failed"),
        ((Counts(True, 0),) * 3, TypeError, "counts.c[0].failed"),
        (([0, 0],) * 3, TypeError, "judgement.counts[0]"),
        (((0, 0, 0),) * 3, ValueError, "judgement.counts[0]"),
        (0, TypeError, "judgement.counts"),
        ("000", TypeError, "judgement.counts"),
        ({0: 0}, TypeError, "judgement.counts"),
    ],
    ids=str,
)
@pytest.mark.parametrize("verdict", list(Verdict), ids=lambda verdict: verdict.name)
def test_what_the_builder_refuses_of_counts_is_passed_on(
    verdict, counts, expected, name
):
    refused(expected, name, judged, Judgement(None, verdict, counts))


@pytest.mark.parametrize(("name", "value", "expected"), BAD_PARAMETERS, ids=str)
@pytest.mark.parametrize(
    "judgement",
    [PASSED, FAILED, Judgement(Broken.REPORT_FORM, None, None)],
    ids=["pass", "fail", "broken"],
)
def test_what_the_builder_refuses_of_a_parameter_is_passed_on(
    judgement, name, value, expected
):
    refused(expected, name, judged, judgement, **{name: value})


@pytest.mark.parametrize(
    "judgement",
    [PASSED, FAILED, Judgement(Broken.REPORT_FORM, None, None)],
    ids=["pass", "fail", "broken"],
)
@pytest.mark.parametrize(("value", "expected"), BAD_INTEGERS, ids=str)
def test_what_the_builder_refuses_of_a_dimension_is_passed_on(
    judgement, value, expected
):
    refused(expected, "k", judged, judgement, (3, value, 5))


def test_the_judgement_is_checked_before_the_parameters():
    bad = {"dims": (0, 4, 5)}
    refused(TypeError, "judgement", judged, None, **bad)
    refused(TypeError, "judgement.verdict", judged, Judgement(None, 1, ZEROS), **bad)
    broken = Judgement(Broken.TIMEOUT, Verdict.PASS, None)
    refused(ValueError, "judgement.verdict", judged, broken, **bad)
    refused(ValueError, "m", judged, Judgement(None, Verdict.FAIL, ZEROS), **bad)


@pytest.mark.parametrize("judgement", [PASSED, Judgement(Broken.TIMEOUT, None, None)])
def test_a_judgement_takes_exactly_its_keyword_arguments(judgement):
    for name in SMALL_V2:
        arguments = {key: value for key, value in SMALL_V2.items() if key != name}
        with pytest.raises(TypeError, match=name):
            from_v2_judgement(judgement, GEMM_ENTRY, SHAPE, **arguments)
    with pytest.raises(TypeError, match="seed"):
        from_v2_judgement(judgement, GEMM_ENTRY, SHAPE, **SMALL_V2, seed=SEED)
    with pytest.raises(TypeError, match="counts"):
        from_v2_judgement(judgement, GEMM_ENTRY, SHAPE, **SMALL_V2, counts=ZEROS)
    with pytest.raises(TypeError):
        from_v2_judgement(judgement, GEMM_ENTRY, SHAPE, *SMALL_V2.values())
    with pytest.raises(TypeError, match="judgement"):
        from_v2_judgement(entry=GEMM_ENTRY, dims=SHAPE, **SMALL_V2)


@pytest.mark.parametrize(
    "report",
    [bytearray(GOOD), GOOD.decode("latin-1"), None, memoryview(GOOD), [GOOD]],
    ids=["bytearray", "str", "none", "memoryview", "list"],
)
def test_a_report_that_is_not_bytes_is_refused(report):
    refused(TypeError, "report", reported, report)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("seed", -1),
        ("seed", 2**64),
        ("seed", True),
        ("seed", None),
        ("draws", 0),
        ("draws", 2**64),
        ("draws", True),
        ("rtol", -0.1),
        ("rtol", "0"),
        ("atol", float("nan")),
        ("atol", float("inf")),
    ],
    ids=str,
)
def test_what_the_judging_refuses_is_passed_on(name, value):
    refused(VerificationArgumentError, name, reported, GOOD, **{name: value})
    refused(VerificationArgumentError, name, reported, None, **{name: value})


def test_a_report_takes_exactly_its_keyword_arguments():
    for name in CALL_V2:
        arguments = {key: value for key, value in CALL_V2.items() if key != name}
        with pytest.raises(TypeError, match=name):
            from_v2_report(GOOD, GEMM_ENTRY, SHAPE, **arguments)
    with pytest.raises(TypeError, match="counts"):
        from_v2_report(GOOD, GEMM_ENTRY, SHAPE, **CALL_V2, counts=ZEROS)
    with pytest.raises(TypeError):
        from_v2_report(GOOD, GEMM_ENTRY, SHAPE, *CALL_V2.values())
    with pytest.raises(TypeError, match="report"):
        from_v2_report(entry=GEMM_ENTRY, dims=SHAPE, **CALL_V2)


def test_a_judgement_is_left_as_it_is_and_shares_nothing_with_the_result():
    counts = [Counts(0, 0), Counts(2, 1), Counts(0, 0)]
    judgement = Judgement(None, Verdict.FAIL, counts)
    before = copy.deepcopy(judgement)
    first = judged(judgement)
    second = judged(judgement)
    expected = copy.deepcopy(second)
    assert first == second
    assert first is not second
    first["counts"]["c"][1]["failed"] = 9
    first["counts"]["c"].append({"failed": 0, "non_finite": 0})
    first["shape"]["m"] = 99
    first["contract_key"]["kind"] = "x"
    first["tolerance"]["rtol"] = 9.0
    first["outcome"] = "pass"
    assert judgement == before
    assert counts == before.counts
    assert second == expected
    assert judged(judgement) == expected

    broken = Judgement(Broken.CHECK_VALUE, None, None)
    one = judged(broken)
    other = judged(broken)
    one["shape"]["k"] = 99
    one["condition"] = "time_limit"
    assert broken == Judgement(Broken.CHECK_VALUE, None, None)
    assert other == broken_v2("check_value")


def test_a_report_gives_equal_results_for_equal_arguments():
    report = failing_report()
    kept = bytes(report)
    first = reported(report)
    first["counts"]["c"][1]["failed"] = 0
    assert reported(report) == reported(kept)
    assert reported(report)["counts"]["c"][1] == {"failed": 1, "non_finite": 0}
    assert report == kept


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    condition_of(Broken.TIMEOUT)
    judged(PASSED)
    judged(Judgement(Broken.EXIT_STATUS, None, None))
    reported(GOOD)
    reported(GOOD[:-1])
    with pytest.raises(TypeError):
        condition_of("time_limit")
    with pytest.raises(ValueError):
        judged(Judgement(None, None, None))
    with pytest.raises(TypeError):
        reported(None)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_builder_and_the_judging_only_and_has_no_entry():
    own = Path(check_judging.__file__)
    imported = imported_modules(own)
    assert imported == {
        "hilclaw",
        "hilclaw.check_result",
        "hilclaw.harness",
        "hilclaw.harness.verification",
        "hilclaw.harness.bf16_verification",
        "hilclaw.harness.bf16_rope_verification",
        "hilclaw.harness.bf16_sdpa_kv_cache_verification",
    }
    assert not imported & {"secrets", "random", "os", "time"}
    assert not hasattr(check_judging, "main")
    assert "__main__" not in own.read_text(encoding="utf-8")


def test_public_names_of_the_module_and_no_default():
    public = {
        name
        for name, value in vars(check_judging).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "condition_of",
        "operand_counts",
        "from_v2_judgement",
        "from_v2_report",
    }
    for name in public:
        parameters = inspect.signature(getattr(check_judging, name)).parameters
        for parameter in parameters.values():
            assert parameter.default is inspect.Parameter.empty, (name, parameter)


# A check of a bf16 kind (ADR-0177 decision 3, "The judge")

# Test values, not dimensions, draws, a seed or a tolerance of the package.
BF16_SHAPES = {
    "gemm": ((2, 3, 4), {"m": 2, "k": 3, "n": 4}),
    "rmsnorm": ((2, 4), {"m": 2, "n": 4}),
    "elementwise_add": ((2, 4), {"m": 2, "n": 4}),
    "swiglu": ((2, 4), {"m": 2, "n": 4}),
}
BF16_CALL = {"draws": 2, "seed": SEED, "rtol": 2**-8, "atol": 0}
BF16_BUILD = {"draws": 2, "rtol": 2**-8, "atol": 0}


def bf16_report(kind, dims):
    parameters = Bf16CheckParameters(SEED, 2, kind, "bf16", dims)
    return mock_check.default_script(None, None, None, parameters, None, None)


def v2_key(kind, dtype):
    return {"kind": kind, "dtype": dtype, "layout": "row_major"}


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_report_of_the_wrong_form_or_check_value_is_broken(kind):
    dims, shape = BF16_SHAPES[kind]
    entry = table_entry(kind, "bf16")
    good = bf16_report(kind, dims)
    short = from_v2_report(good[:-4], entry, dims, **BF16_CALL)
    assert short == {
        "outcome": "broken",
        "condition": "report_form",
        "contract_key": v2_key(kind, "bf16"),
        "shape": shape,
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
    }
    mismatched = bytearray(good)
    mismatched[1] ^= 0x10
    result = from_v2_report(bytes(mismatched), entry, dims, **BF16_CALL)
    assert result["condition"] == "check_value"


def test_a_bf16_report_that_is_no_bytes_raises_type_error():
    dims, _ = BF16_SHAPES["rmsnorm"]
    entry = table_entry("rmsnorm", "bf16")
    with pytest.raises(TypeError, match=r"^report: "):
        from_v2_report(bytearray(b"x"), entry, dims, **BF16_CALL)


@pytest.mark.parametrize("member", list(Broken))
def test_a_broken_bf16_judgement_gives_its_condition(member):
    dims, shape = BF16_SHAPES["swiglu"]
    judgement = Judgement(member, None, None)
    entry = table_entry("swiglu", "bf16")
    result = from_v2_judgement(judgement, entry, dims, **BF16_BUILD)
    assert result["condition"] == condition_of(member)
    assert result["shape"] == shape


def test_a_completed_bf16_judgement_gives_its_counts_and_outcome():
    dims, shape = BF16_SHAPES["gemm"]
    entry = table_entry("gemm", "bf16")
    judgement = Judgement(None, Verdict.FAIL, (Counts(0, 0), Counts(8, 2)))
    result = from_v2_judgement(judgement, entry, dims, **BF16_BUILD)
    assert result["outcome"] == "fail"
    assert result["shape"] == shape
    assert result["counts"]["c"][1] == {"failed": 8, "non_finite": 2}
    with pytest.raises(ValueError, match=r"^counts\.c\[1\]\.failed: "):
        from_v2_judgement(
            Judgement(None, Verdict.FAIL, (Counts(0, 0), Counts(9, 0))),
            entry,
            dims,
            **BF16_BUILD,
        )


@pytest.mark.parametrize(
    ("judgement", "expected"),
    [
        ((None, Verdict.PASS, ((0, 0), (0, 0))), TypeError),
        (Judgement(None, None, ((0, 0), (0, 0))), ValueError),
        (Judgement(Broken.REPORT_FORM, Verdict.PASS, None), ValueError),
        (Judgement(None, Verdict.FAIL, ((0, 0), (0, 0))), ValueError),
    ],
)
def test_a_bf16_judgement_that_does_not_agree_is_refused(judgement, expected):
    dims, _ = BF16_SHAPES["elementwise_add"]
    entry = table_entry("elementwise_add", "bf16")
    with pytest.raises(expected):
        from_v2_judgement(judgement, entry, dims, **BF16_BUILD)


# An sdpa_kv_cache check (ADR-0183 decision 3; ADR-0165 decision 8)

# Test values, not dimensions, draws, a seed or a tolerance of the package.
SDPA = "sdpa_kv_cache"
SDPA_CASES = {
    "h-multiple-of-h_kv": (
        (2, 3, 4, 2, 4),
        {"m": 2, "l": 3, "h": 4, "h_kv": 2, "d": 4},
    ),
    "h-equals-h_kv": ((1, 2, 3, 3, 2), {"m": 1, "l": 2, "h": 3, "h_kv": 3, "d": 2}),
}
SDPA_DIMS, SDPA_SHAPE = SDPA_CASES["h-multiple-of-h_kv"]
SDPA_CALL = {"draws": 2, "seed": SEED, "rtol": 0, "atol": 2.154e-3}
SDPA_BUILD = {"draws": 2, "rtol": 0, "atol": 2.154e-3}
SDPA_ZEROS = {
    "cache_k": [{"differs": 0}] * 2,
    "cache_v": [{"differs": 0}] * 2,
    "out": [{"failed": 0, "non_finite": 0}] * 2,
}
SDPA_ENTRY = table_entry(SDPA, "bf16")


def sdpa_offsets(dims, draw):
    m, l, h, h_kv, d = dims
    block = 4 + 2 * m * h * d + 4 * (l + 2 * m) * h_kv * d
    out = draw * block + 4
    return out, out + 2 * m * h * d


def with_patterns(report, changes):
    changed = bytearray(report)
    for offset, pattern in changes:
        struct.pack_into("=H", changed, offset, pattern)
    return bytes(changed)


@pytest.mark.parametrize("case", list(SDPA_CASES))
def test_a_conforming_sdpa_report_is_judged_pass(case):
    dims, shape = SDPA_CASES[case]
    result = from_v2_report(bf16_report(SDPA, dims), SDPA_ENTRY, dims, **SDPA_CALL)
    assert result == {
        "outcome": "pass",
        "contract_key": v2_key(SDPA, "bf16"),
        "shape": shape,
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2.154e-3},
        "counts": SDPA_ZEROS,
    }


@pytest.mark.parametrize(
    ("where", "out_entry", "cache_k_entry"),
    [
        ("out", {"failed": 1, "non_finite": 0}, {"differs": 0}),
        ("cache", {"failed": 0, "non_finite": 0}, {"differs": 1}),
        ("both", {"failed": 1, "non_finite": 0}, {"differs": 1}),
    ],
)
def test_an_sdpa_report_fails_by_out_by_the_cache_or_by_both(
    where, out_entry, cache_k_entry
):
    out, cache = sdpa_offsets(SDPA_DIMS, 1)
    changes = {"out": [(out, 0x4780)], "cache": [(cache, 0x0000)]}
    changes["both"] = changes["out"] + changes["cache"]
    report = with_patterns(bf16_report(SDPA, SDPA_DIMS), changes[where])
    result = from_v2_report(report, SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert result["outcome"] == "fail"
    assert result["counts"] == {
        "cache_k": [{"differs": 0}, cache_k_entry],
        "cache_v": [{"differs": 0}] * 2,
        "out": [{"failed": 0, "non_finite": 0}, out_entry],
    }


def test_an_sdpa_report_of_the_wrong_form_or_check_value_is_broken():
    good = bf16_report(SDPA, SDPA_DIMS)
    short = from_v2_report(good[:-4], SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert short == {
        "outcome": "broken",
        "condition": "report_form",
        "contract_key": v2_key(SDPA, "bf16"),
        "shape": SDPA_SHAPE,
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2.154e-3},
    }
    longer = from_v2_report(good + b"\0\0", SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert longer["condition"] == "report_form"
    mismatched = bytearray(good)
    mismatched[1] ^= 0x10
    result = from_v2_report(bytes(mismatched), SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert result["condition"] == "check_value"
    call = {**SDPA_CALL, "seed": 1}
    other_seed = from_v2_report(good, SDPA_ENTRY, SDPA_DIMS, **call)
    assert other_seed["condition"] == "check_value"


@pytest.mark.parametrize(
    ("name", "value"), [("draws", 0), ("seed", -1), ("rtol", -1.0), ("atol", None)]
)
def test_an_sdpa_report_of_values_the_judge_refuses_raises(name, value):
    with pytest.raises(VerificationArgumentError):
        from_v2_report(b"", SDPA_ENTRY, SDPA_DIMS, **{**SDPA_CALL, name: value})


@pytest.mark.parametrize("member", list(Broken))
def test_a_broken_sdpa_judgement_gives_its_condition(member):
    result = from_v2_judgement(
        Judgement(member, None, None), SDPA_ENTRY, SDPA_DIMS, **SDPA_BUILD
    )
    assert result["condition"] == condition_of(member)
    assert result["shape"] == SDPA_SHAPE
    assert "counts" not in result


@pytest.mark.parametrize(
    ("judgement", "expected"),
    [
        (Judgement(None, Verdict.PASS, (DrawCounts(0, 0, 1, 0),) * 2), ValueError),
        (Judgement(None, Verdict.PASS, (DrawCounts(1, 0, 0, 0),) * 2), ValueError),
        (Judgement(None, Verdict.FAIL, (DrawCounts(0, 0, 0, 0),) * 2), ValueError),
        (Judgement(None, Verdict.PASS, ((0, 0), (0, 0))), ValueError),
        (Judgement(None, Verdict.PASS, (DrawCounts(0, 0, -1, 0),) * 2), ValueError),
        (Judgement(None, Verdict.PASS, ((0, 0, 1.0, 0),) * 2), TypeError),
        (Judgement(Broken.CHECK_VALUE, Verdict.FAIL, None), ValueError),
        (Judgement(None, None, (DrawCounts(0, 0, 0, 0),) * 2), ValueError),
        ((None, Verdict.PASS, (DrawCounts(0, 0, 0, 0),) * 2), TypeError),
    ],
)
def test_an_sdpa_judgement_that_does_not_agree_is_refused(judgement, expected):
    with pytest.raises(expected):
        from_v2_judgement(judgement, SDPA_ENTRY, SDPA_DIMS, **SDPA_BUILD)


def test_an_sdpa_judgement_beside_counts_of_the_other_outcome_names_the_verdict():
    judgement = Judgement(
        None, Verdict.PASS, (DrawCounts(0, 0, 0, 0), DrawCounts(0, 0, 4, 0))
    )
    with pytest.raises(ValueError, match=r"^judgement\.verdict: PASS beside .* fail"):
        from_v2_judgement(judgement, SDPA_ENTRY, SDPA_DIMS, **SDPA_BUILD)


# A rope check (ADR-0177 decision 3, HQ-0077; ADR-0180 decision 1)

# Test values, not dimensions, draws, a seed or a tolerance of the package.
ROPE = "rope"
ROPE_TOLERANCE = {"rtol": 0, "atol": 2**-8 + 2**-21}
ROPE_CALL = {"draws": 2, "seed": SEED, **ROPE_TOLERANCE}
ROPE_SMALLEST = (1, 1, 2)

ROPE_ENTRY = table_entry(ROPE, "bf16")


def rope_report(dims, seed=SEED):
    parameters = Bf16CheckParameters(seed, 2, ROPE, "bf16", dims)
    return mock_check.default_script(None, None, None, parameters, None, None)


def rope_shape(dims):
    return dict(zip(("m", "h", "d"), dims, strict=True))


@pytest.mark.parametrize(
    ("dims", "seed"),
    [(ROPE_SMALLEST, SEED), ((1, 8, 64), 6), ((1, 8, 64), 7), ((128, 8, 64), SEED)],
    ids=["smallest", "m1-even-seed", "m1-odd-seed", "m128"],
)
def test_a_conforming_rope_report_is_judged_pass_at_the_start_of_the_rule(
    dims, seed, monkeypatch
):
    starts = []
    judge = bf16_rope_verification.judge_report

    def spy(report, judged, **named):
        starts.append(named["start"])
        return judge(report, judged, **named)

    monkeypatch.setattr(bf16_rope_verification, "judge_report", spy)
    call = {**ROPE_CALL, "seed": seed}
    result = from_v2_report(rope_report(dims, seed), ROPE_ENTRY, dims, **call)
    assert result == {
        "outcome": "pass",
        "contract_key": v2_key(ROPE, "bf16"),
        "shape": rope_shape(dims),
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2**-8 + 2**-21},
        "counts": {"out": [{"failed": 0, "non_finite": 0}] * 2},
    }
    expected = 0 if dims[0] > 1 else (127 if seed % 2 == 0 else 2047)
    assert starts == [expected]


def test_a_rope_report_judged_at_another_start_has_another_check_value():
    dims = (1, 8, 64)
    report = rope_report(dims, seed=6)
    judged = {
        start: bf16_rope_verification.judge_report(
            report, dims, start=start, draws=2, seed=6, **ROPE_TOLERANCE
        )
        for start in (127, 2047)
    }
    assert judged[127].verdict is Verdict.PASS
    assert judged[2047] == Judgement(Broken.CHECK_VALUE, None, None)


@pytest.mark.parametrize(
    ("pattern", "non_finite"), [(0x7F80, 1), (0x4000, 0)], ids=["inf", "two"]
)
def test_a_rope_report_with_a_wrong_element_is_judged_fail(pattern, non_finite):
    dims = (2, 2, 4)
    report = bytearray(rope_report(dims))
    block = 4 + 2 * 2 * 2 * 4
    struct.pack_into("=H", report, block + 4 + 2 * 5, pattern)
    result = from_v2_report(bytes(report), ROPE_ENTRY, dims, **ROPE_CALL)
    assert result["outcome"] == "fail"
    assert result["shape"] == rope_shape(dims)
    assert result["counts"]["out"] == [
        {"failed": 0, "non_finite": 0},
        {"failed": 1, "non_finite": non_finite},
    ]


def test_a_rope_report_of_the_wrong_form_or_check_value_is_broken():
    good = rope_report((2, 2, 4))
    short = from_v2_report(good[:-1], ROPE_ENTRY, (2, 2, 4), **ROPE_CALL)
    assert short == {
        "outcome": "broken",
        "condition": "report_form",
        "contract_key": v2_key(ROPE, "bf16"),
        "shape": {"m": 2, "h": 2, "d": 4},
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2**-8 + 2**-21},
    }
    mismatched = bytearray(good)
    mismatched[0] ^= 0x01
    result = from_v2_report(bytes(mismatched), ROPE_ENTRY, (2, 2, 4), **ROPE_CALL)
    assert result["condition"] == "check_value"


@pytest.mark.parametrize("member", list(Broken))
def test_a_broken_rope_judgement_gives_its_condition_and_m_h_d(member):
    result = from_v2_judgement(
        Judgement(member, None, None), ROPE_ENTRY, (2, 3, 4), draws=2, **ROPE_TOLERANCE
    )
    assert result["condition"] == condition_of(member)
    assert result["shape"] == {"m": 2, "h": 3, "d": 4}


def test_a_completed_rope_judgement_is_bounded_by_m_h_d():
    counts = (Counts(0, 0), Counts(24, 2))
    result = from_v2_judgement(
        Judgement(None, Verdict.FAIL, counts),
        ROPE_ENTRY,
        (2, 3, 4),
        draws=2,
        **ROPE_TOLERANCE,
    )
    assert result["counts"]["out"][1] == {"failed": 24, "non_finite": 2}
    with pytest.raises(ValueError, match=r"^counts\.out\[1\]\.failed: "):
        from_v2_judgement(
            Judgement(None, Verdict.FAIL, (Counts(0, 0), Counts(25, 0))),
            ROPE_ENTRY,
            (2, 3, 4),
            draws=2,
            **ROPE_TOLERANCE,
        )


@pytest.mark.parametrize(
    ("dims", "seed"),
    [((1, 2, 2), -1), ((1, 2, 2), True), ((1, 1, 2**52), 1)],
    ids=["negative-seed", "bool-seed", "rows-beyond-the-table"],
)
def test_a_rope_report_of_what_the_start_rule_refuses_raises(dims, seed):
    with pytest.raises(VerificationArgumentError):
        from_v2_report(b"", ROPE_ENTRY, dims, **{**ROPE_CALL, "seed": seed})


@pytest.mark.parametrize(
    ("dims", "expected", "pattern"),
    [
        ((1, 2), ValueError, r"^dims: "),
        ((1, 2, 3), ValueError, r"^d: "),
        ((0, 2, 2), ValueError, r"^m: "),
        ((True, 2, 2), TypeError, r"^m: "),
    ],
    ids=["two-dims", "odd-d", "zero-m", "bool-m"],
)
def test_a_rope_report_of_dims_outside_the_rule_is_refused(dims, expected, pattern):
    with pytest.raises(expected, match=pattern):
        from_v2_report(b"", ROPE_ENTRY, dims, **ROPE_CALL)


# The v2 result per operand (ADR-0183 decisions 3 and 9 item 1)


ROPE_CALL_6 = {**ROPE_CALL, "seed": 6}


def cache_v_offset(dims, draw):
    m, l, _, h_kv, d = dims
    return sdpa_offsets(dims, draw)[1] + 2 * (l + 2 * m) * h_kv * d


@pytest.mark.parametrize(
    ("case", "dims", "counts", "expected"),
    [
        (
            ("gemm", "fp32"),
            (3, 4, 5),
            (Counts(0, 0), Counts(2, 1)),
            {"c": [(0, 0), (2, 1)]},
        ),
        (("gemm", "bf16"), (2, 3, 4), [(1, 0), (0, 0)], {"c": [(1, 0), (0, 0)]}),
        (("rmsnorm", "bf16"), (2, 4), (Counts(0, 0),) * 2, {"y": [(0, 0), (0, 0)]}),
        (("elementwise_add", "bf16"), (2, 4), ((3, 3),), {"c": [(3, 3)]}),
        (("swiglu", "bf16"), (2, 4), (), {"out": []}),
        (("rope", "bf16"), (1, 2, 4), (Counts(4, 0),), {"out": [(4, 0)]}),
        (
            (SDPA, "bf16"),
            SDPA_DIMS,
            (DrawCounts(1, 0, 2, 3), DrawCounts(0, 0, 0, 5)),
            {"cache_k": [2, 0], "cache_v": [3, 5], "out": [(1, 0), (0, 0)]},
        ),
    ],
    ids=["fp32-gemm", "gemm", "rmsnorm", "elementwise_add", "swiglu", "rope", "sdpa"],
)
def test_operand_counts_of_each_judge(case, dims, counts, expected):
    taken = operand_counts(table_entry(*case), dims, counts)
    assert taken == expected
    assert list(taken) == list(expected)
    assert all(type(entries) is list for entries in taken.values())
    items = [item for entries in taken.values() for item in entries]
    assert all(type(item) in (tuple, int) for item in items)


@pytest.mark.parametrize(
    ("counts", "expected", "pattern"),
    [
        (None, TypeError, r"^judgement\.counts: "),
        ({0: DrawCounts(0, 0, 0, 0)}, TypeError, r"^judgement\.counts: "),
        ([[0, 0, 0, 0]], TypeError, r"^judgement\.counts\[0\]: must be a tuple"),
        ([(0, 0, 0)], ValueError, r"^judgement\.counts\[0\]: must have 4 items"),
        ([Counts(0, 0)], ValueError, r"^judgement\.counts\[0\]: must have 4 items"),
    ],
)
def test_operand_counts_of_another_form_are_refused(counts, expected, pattern):
    with pytest.raises(expected, match=pattern):
        operand_counts(SDPA_ENTRY, SDPA_DIMS, counts)


def test_operand_counts_checks_the_entry_and_dims_first():
    with pytest.raises(TypeError, match=r"^entry: "):
        operand_counts(("gemm", "fp32"), (1, 2, 3), None)
    with pytest.raises(ValueError, match=r"^dims: "):
        operand_counts(SDPA_ENTRY, (3, 2, 4, 2, 4), None)
    with pytest.raises(ValueError, match=r"^judgement\.counts\[0\]: must have 2"):
        operand_counts(GEMM_ENTRY, (1, 2, 3), [DrawCounts(0, 0, 0, 0)])


@pytest.mark.parametrize(
    ("counts", "verdict", "expected"),
    [
        ((DrawCounts(0, 0, 0, 0),) * 2, Verdict.PASS, "pass"),
        ((DrawCounts(0, 0, 0, 0), DrawCounts(0, 0, 1, 0)), Verdict.FAIL, "fail"),
        ((DrawCounts(0, 0, 0, 1), DrawCounts(0, 0, 0, 0)), Verdict.FAIL, "fail"),
        ((DrawCounts(2, 2, 0, 0), DrawCounts(0, 0, 0, 0)), Verdict.FAIL, "fail"),
    ],
    ids=["pass", "cache_k", "cache_v", "out"],
)
def test_a_completed_sdpa_judgement_gives_its_v2_result(counts, verdict, expected):
    judgement = Judgement(None, verdict, counts)
    result = from_v2_judgement(judgement, SDPA_ENTRY, SDPA_DIMS, **SDPA_BUILD)
    assert result == {
        "outcome": expected,
        "contract_key": v2_key(SDPA, "bf16"),
        "shape": SDPA_SHAPE,
        "draws": 2,
        "tolerance": {"rtol": 0.0, "atol": 2.154e-3},
        "counts": {
            "cache_k": [{"differs": count.cache_k_differences} for count in counts],
            "cache_v": [{"differs": count.cache_v_differences} for count in counts],
            "out": [
                {"failed": count.failed, "non_finite": count.non_finite}
                for count in counts
            ],
        },
    }


@pytest.mark.parametrize("member", list(Broken))
def test_a_broken_judgement_gives_its_v2_condition(member):
    result = from_v2_judgement(
        Judgement(member, None, None), GEMM_ENTRY, SHAPE, **SMALL_V2
    )
    assert result == {
        "outcome": "broken",
        "condition": condition_of(member),
        "contract_key": v2_key("gemm", "fp32"),
        "shape": {"m": 3, "k": 4, "n": 5},
        "draws": DRAWS,
        "tolerance": {"rtol": 1e-5, "atol": 1e-6},
    }


@pytest.mark.parametrize(
    ("judgement", "expected", "pattern"),
    [
        ((None, Verdict.PASS, ZEROS), TypeError, r"^judgement: "),
        (Judgement(None, Verdict.FAIL, ZEROS), ValueError, r"^judgement\.verdict: "),
        (Judgement(None, Verdict.PASS, ONE_FAILED), ValueError, r"^judgement\.verdict"),
        (Judgement(None, None, ZEROS), ValueError, r"^judgement\.verdict: "),
        (Judgement(None, Verdict.PASS, None), ValueError, r"^judgement\.counts: "),
        (Judgement(Broken.TIMEOUT, Verdict.PASS, None), ValueError, r"^judgement\."),
        (Judgement(None, Verdict.PASS, ZEROS[:2]), ValueError, r"^counts\.c: "),
        (
            Judgement(None, Verdict.FAIL, (Counts(21, 0),) * 3),
            ValueError,
            r"^counts\.c\[0\]\.failed: ",
        ),
    ],
)
def test_a_judgement_that_does_not_agree_is_refused_under_v2(
    judgement, expected, pattern
):
    with pytest.raises(expected, match=pattern):
        from_v2_judgement(judgement, GEMM_ENTRY, SHAPE, **SMALL_V2)


def test_a_conforming_fp32_report_gives_a_passing_v2_result():
    report = passing_report(*SHAPE, DRAWS, SEED)
    result = from_v2_report(report, GEMM_ENTRY, SHAPE, **SMALL_V2, seed=SEED)
    assert result == {
        "outcome": "pass",
        "contract_key": v2_key("gemm", "fp32"),
        "shape": {"m": 3, "k": 4, "n": 5},
        "draws": DRAWS,
        "tolerance": {"rtol": 1e-5, "atol": 1e-6},
        "counts": {"c": [{"failed": 0, "non_finite": 0}] * DRAWS},
    }
    failing = from_v2_report(failing_report(), GEMM_ENTRY, SHAPE, **SMALL_V2, seed=SEED)
    assert failing["outcome"] == "fail"
    assert failing["counts"]["c"][1] == {"failed": 1, "non_finite": 0}
    short = from_v2_report(report[:-4], GEMM_ENTRY, SHAPE, **SMALL_V2, seed=SEED)
    assert short["condition"] == "report_form"


@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_bf16_report_gives_its_v2_result(kind):
    dims, shape = BF16_SHAPES[kind]
    entry = table_entry(kind, "bf16")
    (name,) = check_result.output_operands(entry, dims)
    report = bf16_report(kind, dims)
    result = from_v2_report(report, entry, dims, **BF16_CALL)
    assert result == {
        "outcome": "pass",
        "contract_key": v2_key(kind, "bf16"),
        "shape": shape,
        "draws": 2,
        "tolerance": {"rtol": 2**-8, "atol": 0.0},
        "counts": {name: [{"failed": 0, "non_finite": 0}] * 2},
    }
    wrong = bytearray(report)
    struct.pack_into("=H", wrong, 4, 0x7F80)
    failed = from_v2_report(bytes(wrong), entry, dims, **BF16_CALL)
    assert failed["counts"][name][0] == {"failed": 1, "non_finite": 1}
    assert failed["outcome"] == "fail"


def test_a_rope_report_gives_its_v2_result_at_the_start_of_the_rule():
    dims = (1, 8, 64)
    result = from_v2_report(rope_report(dims, 6), ROPE_ENTRY, dims, **ROPE_CALL_6)
    assert result["outcome"] == "pass"
    assert result["contract_key"] == v2_key(ROPE, "bf16")
    assert result["counts"] == {"out": [{"failed": 0, "non_finite": 0}] * 2}
    other = from_v2_report(rope_report(dims, 7), ROPE_ENTRY, dims, **ROPE_CALL_6)
    assert other["condition"] == "check_value"


def test_an_sdpa_report_gives_per_allocation_v2_counts():
    cache_k = sdpa_offsets(SDPA_DIMS, 1)[1]
    cache_v = cache_v_offset(SDPA_DIMS, 1)
    changes = [(cache_k, 0x0000), (cache_v, 0x0000), (cache_v + 2, 0x0000)]
    report = with_patterns(bf16_report(SDPA, SDPA_DIMS), changes)
    result = from_v2_report(report, SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert result["outcome"] == "fail"
    assert result["counts"] == {
        "cache_k": [{"differs": 0}, {"differs": 1}],
        "cache_v": [{"differs": 0}, {"differs": 2}],
        "out": [{"failed": 0, "non_finite": 0}] * 2,
    }
    passing = bf16_report(SDPA, SDPA_DIMS)
    zeros = from_v2_report(passing, SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert zeros["outcome"] == "pass"
    broken_report = from_v2_report(passing[:-1], SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)
    assert broken_report["condition"] == "report_form"
    assert "counts" not in broken_report


@pytest.mark.parametrize(
    ("entry", "dims", "expected", "pattern"),
    [
        (None, SHAPE, TypeError, r"^entry: "),
        (GEMM_ENTRY, (3, 4), ValueError, r"^dims: "),
        (GEMM_ENTRY, [3, 4, 5], TypeError, r"^dims: "),
        (ROPE_ENTRY, (1, 2, 3), ValueError, r"^d: "),
        (SDPA_ENTRY, (3, 2, 4, 2, 4), ValueError, r"^dims: "),
    ],
)
def test_a_v2_report_of_an_entry_or_dims_outside_the_rule_is_refused_unjudged(
    entry, dims, expected, pattern, monkeypatch
):
    def judged(*arguments, **named):
        raise AssertionError("judged")

    monkeypatch.setattr(check_judging.verification, "judge_report", judged)
    with pytest.raises(expected, match=pattern):
        from_v2_report(b"", entry, dims, **SMALL_V2, seed=SEED)


def test_a_v2_report_passes_on_what_the_judge_raises():
    with pytest.raises(VerificationArgumentError):
        from_v2_report(b"", GEMM_ENTRY, SHAPE, **{**SMALL_V2, "rtol": -1.0}, seed=SEED)
    with pytest.raises(TypeError, match=r"^report: "):
        from_v2_report(bytearray(b"x"), SDPA_ENTRY, SDPA_DIMS, **SDPA_CALL)


def test_the_v2_functions_have_no_default_and_keyword_only_values():
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    for function, names in (
        (from_v2_judgement, ["draws", "rtol", "atol"]),
        (from_v2_report, ["draws", "seed", "rtol", "atol"]),
    ):
        parameters = list(inspect.signature(function).parameters.values())
        assert [parameter.name for parameter in parameters[3:]] == names
        assert all(parameter.kind is keyword_only for parameter in parameters[3:])
    assert list(inspect.signature(operand_counts).parameters) == [
        "entry",
        "dims",
        "counts",
    ]
