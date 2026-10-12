import ast
import copy
import enum
import inspect
import json
import struct
from pathlib import Path

import numpy as np
import pytest

from hilclaw import check_judging, check_result, tools
from hilclaw.check_judging import condition_of, from_judgement, from_report
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

# The record's example values (ADR-0042 decision 7); its draws are a placeholder.
EXAMPLE_DRAWS = 2
EXAMPLE = {
    "m": 1,
    "k": 2048,
    "n": 8192,
    "draws": EXAMPLE_DRAWS,
    "rtol": 1e-4,
    "atol": 0.01,
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

# Test values, not tolerances, dimensions, draws or a seed of the package.
SHAPE = (3, 4, 5)
DRAWS = 3
SEED = 7
LAST = 2**64 - 1
SMALL = {"m": 3, "k": 4, "n": 5, "draws": DRAWS, "rtol": 1e-5, "atol": 1e-6}
CALL = {**SMALL, "seed": SEED}
# For this seed the product of the 1 x 1 x 1 draw is exact in binary32.
EXACT_SEED = 302510
ZEROS = (Counts(0, 0),) * DRAWS
ONE_FAILED = (Counts(0, 0), Counts(1, 0), Counts(0, 0))
PASSED = Judgement(None, Verdict.PASS, ZEROS)
FAILED = Judgement(None, Verdict.FAIL, ONE_FAILED)

BAD_INTEGERS = [(0, ValueError), (True, TypeError), (1.0, TypeError)]
BAD_NUMBERS = [(-0.1, ValueError), (float("nan"), ValueError), ("0", TypeError)]
BAD_PARAMETERS = [
    (name, value, expected)
    for name in ("m", "k", "n", "draws")
    for value, expected in BAD_INTEGERS
] + [
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


def test_condition_of_over_the_enumeration_is_the_tuple_of_conditions():
    values = tuple(condition_of(member) for member in Broken)
    assert values == check_result.CONDITIONS
    assert len(list(Broken)) == 4


@pytest.mark.parametrize(
    "value",
    [None, "time_limit", "TIMEOUT", 1, True, Verdict.PASS, Other.TIMEOUT, Broken],
    ids=repr,
)
def test_condition_of_refuses_what_is_no_member_of_broken(value):
    refused(TypeError, "broken", condition_of, value)


def test_a_pass_judgement_gives_the_completed_result():
    result = from_judgement(PASSED, **SMALL)
    assert result == {
        "outcome": "pass",
        "shape": {"m": 3, "k": 4, "n": 5},
        "draws": 3,
        "tolerance": {"rtol": 1e-5, "atol": 1e-6},
        "counts": [{"failed": 0, "non_finite": 0}] * 3,
    }
    assert result == check_result.completed(**SMALL, counts=((0, 0),) * 3)
    assert_sound(result, COMPLETED_MEMBERS)


def test_a_fail_judgement_gives_the_second_example_of_the_record():
    judgement = Judgement(None, Verdict.FAIL, (Counts(0, 0), Counts(37, 2)))
    result = from_judgement(judgement, **EXAMPLE)
    assert result == ADR_FAIL
    assert result == check_result.completed(**EXAMPLE, counts=((0, 0), (37, 2)))
    assert_sound(result, COMPLETED_MEMBERS)


@pytest.mark.parametrize("member", list(Broken), ids=lambda member: member.name)
def test_a_broken_judgement_gives_the_broken_result(member):
    result = from_judgement(Judgement(member, None, None), **EXAMPLE)
    assert result == {**ADR_BROKEN, "condition": condition_of(member)}
    assert result == check_result.broken(condition_of(member), **EXAMPLE)
    assert_sound(result, BROKEN_MEMBERS)


def test_a_timeout_judgement_gives_the_third_example_of_the_record():
    result = from_judgement(Judgement(Broken.TIMEOUT, None, None), **EXAMPLE)
    assert result == ADR_BROKEN
    assert list(result) == ["outcome", "condition", "shape", "draws", "tolerance"]


def test_from_judgement_takes_the_counts_as_a_list_too():
    judgement = Judgement(None, Verdict.FAIL, list(ONE_FAILED))
    assert from_judgement(judgement, **SMALL) == from_judgement(FAILED, **SMALL)


def test_from_report_passes_a_report_of_rounded_references():
    result = from_report(GOOD, **CALL)
    assert result["outcome"] == "pass"
    assert result["counts"] == [{"failed": 0, "non_finite": 0}] * DRAWS
    assert result == from_judgement(PASSED, **SMALL)
    assert_sound(result, COMPLETED_MEMBERS)
    assert "seed" not in result


def test_from_report_fails_one_element_outside_the_tolerance():
    result = from_report(failing_report(), **CALL)
    assert result == from_judgement(FAILED, **SMALL)
    assert result["outcome"] == "fail"
    assert [entry["failed"] for entry in result["counts"]] == [0, 1, 0]
    assert_sound(result, COMPLETED_MEMBERS)


def test_from_report_counts_a_non_finite_output_in_both_counts():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    outputs[0][1, 1] = np.nan
    outputs[0][0, 0] = 70.0
    outputs[2][0, 3] = -np.inf
    result = from_report(report_of(*SHAPE, SEED, outputs), **CALL)
    assert result["outcome"] == "fail"
    assert result["counts"] == [
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
def test_from_report_of_a_wrong_form_is_broken(report):
    result = from_report(report, **CALL)
    assert result == check_result.broken("report_form", **SMALL)
    assert_sound(result, BROKEN_MEMBERS)


@pytest.mark.parametrize("draw", [0, 1, 2])
def test_from_report_with_a_wrong_check_value_is_broken(draw):
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    report = report_of(*SHAPE, SEED, outputs, wrong_check={draw})
    result = from_report(report, **CALL)
    assert result == check_result.broken("check_value", **SMALL)
    assert "counts" not in result
    assert_sound(result, BROKEN_MEMBERS)


def test_from_report_drops_the_counts_before_a_wrong_check_value():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    outputs[0][0, :] = 9.0
    report = report_of(*SHAPE, SEED, outputs, wrong_check={2})
    result = from_report(report, **CALL)
    assert result == check_result.broken("check_value", **SMALL)
    assert set(result) == BROKEN_MEMBERS


def test_from_report_of_a_report_made_for_another_seed_is_broken():
    report = passing_report(*SHAPE, DRAWS, SEED + 1)
    assert from_report(report, **CALL)["condition"] == "check_value"
    assert from_report(report, **{**CALL, "seed": SEED + 1})["outcome"] == "pass"


@pytest.mark.parametrize("seed", [0, LAST])
def test_from_report_takes_the_whole_range_of_seeds(seed):
    arguments = {**CALL, "draws": 2, "seed": seed}
    result = from_report(passing_report(*SHAPE, 2, seed), **arguments)
    assert result["outcome"] == "pass"
    assert result["draws"] == 2


def test_from_report_of_the_smallest_check():
    unit = {"m": 1, "k": 1, "n": 1, "draws": 1}
    report = passing_report(1, 1, 1, 1, SEED)
    result = from_report(report, **unit, seed=SEED, rtol=1e-5, atol=1e-6)
    assert result == {
        "outcome": "pass",
        "shape": {"m": 1, "k": 1, "n": 1},
        "draws": 1,
        "tolerance": {"rtol": 1e-5, "atol": 1e-6},
        "counts": [{"failed": 0, "non_finite": 0}],
    }
    off = report_of(1, 1, 1, SEED, [np.full((1, 1), np.inf, dtype=np.float32)])
    result = from_report(off, **unit, seed=SEED, rtol=1e-5, atol=1e-6)
    assert result["counts"] == [{"failed": 1, "non_finite": 1}]


@pytest.mark.parametrize("zero", [0.0, 0])
def test_from_report_with_a_zero_tolerance(zero):
    unit = {"m": 1, "k": 1, "n": 1, "draws": 1, "seed": EXACT_SEED}
    a, b = draw_inputs(1, 1, 1, seed=EXACT_SEED, draw=0)
    output = reference(a, b).astype(np.float32)
    result = from_report(
        report_of(1, 1, 1, EXACT_SEED, [output]), **unit, rtol=zero, atol=zero
    )
    assert result["outcome"] == "pass"
    assert result["tolerance"] == {"rtol": 0.0, "atol": 0.0}
    assert type(result["tolerance"]["rtol"]) is float
    off = np.nextafter(output, np.float32(2.0))
    result = from_report(
        report_of(1, 1, 1, EXACT_SEED, [off]), **unit, rtol=zero, atol=zero
    )
    assert result["outcome"] == "fail"
    assert result["counts"] == [{"failed": 1, "non_finite": 0}]


def test_from_report_with_integer_tolerances():
    report = report_of(*SHAPE, SEED, [np.zeros((3, 5), dtype=np.float32)] * DRAWS)
    passed = from_report(report, **{**CALL, "rtol": 1, "atol": 0})
    assert passed["outcome"] == "pass"
    assert passed["tolerance"] == {"rtol": 1.0, "atol": 0.0}
    failed = from_report(report, **{**CALL, "rtol": 0, "atol": 0})
    assert failed["counts"] == [{"failed": 15, "non_finite": 0}] * DRAWS
    assert_sound(failed, COMPLETED_MEMBERS)


def test_from_report_of_a_wrong_form_for_many_draws_builds_no_counts():
    many = {**CALL, "draws": 2**63}
    result = from_report(GOOD, **many)
    assert result == check_result.broken("report_form", **{**SMALL, "draws": 2**63})
    assert_sound(result, BROKEN_MEMBERS)


def test_from_report_is_the_judging_followed_by_from_judgement():
    outputs = rounded_references(*SHAPE, DRAWS, SEED)
    reports = {
        "pass": GOOD,
        "fail": failing_report(),
        "report_form": GOOD[:-1],
        "check_value": report_of(*SHAPE, SEED, outputs, wrong_check={1}),
    }
    seen = set()
    for report in reports.values():
        judgement = judge_report(report, **CALL)
        result = from_report(report, **CALL)
        assert result == from_judgement(judgement, **SMALL)
        assert result == from_report(report, **CALL)
        if judgement.broken is None:
            assert result["outcome"] == judgement.verdict.name.lower()
            assert len(result["counts"]) == len(judgement.counts)
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
def test_from_judgement_refuses_what_is_not_exactly_a_judgement(judgement):
    refused(TypeError, "judgement", from_judgement, judgement, **SMALL)


@pytest.mark.parametrize("fields", [(), (None,), (None, Verdict.PASS, ZEROS, None)])
def test_from_judgement_refuses_a_judgement_without_its_three_fields(fields):
    judgement = tuple.__new__(Judgement, fields)
    refused(ValueError, "judgement", from_judgement, judgement, **SMALL)


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
def test_from_judgement_refuses_fields_that_do_not_agree(judgement, expected, name):
    refused(expected, name, from_judgement, judgement, **SMALL)


@pytest.mark.parametrize(
    ("counts", "expected", "name"),
    [
        (ZEROS[:2], ValueError, "counts"),
        (ZEROS + ZEROS, ValueError, "counts"),
        ((), ValueError, "counts"),
        (
            (Counts(0, 0), Counts(1, 2), Counts(0, 0)),
            ValueError,
            "counts[1].non_finite",
        ),
        ((Counts(0, 0), Counts(0, 0), Counts(16, 0)), ValueError, "counts[2].failed"),
        ((Counts(-1, 0),) * 3, ValueError, "counts[0].failed"),
        ((Counts(True, 0),) * 3, TypeError, "counts[0].failed"),
        (([0, 0],) * 3, TypeError, "counts[0]"),
        (((0, 0, 0),) * 3, ValueError, "counts[0]"),
        (0, TypeError, "counts"),
        ("000", TypeError, "counts"),
        ({0: 0}, TypeError, "counts"),
    ],
    ids=str,
)
@pytest.mark.parametrize("verdict", list(Verdict), ids=lambda verdict: verdict.name)
def test_from_judgement_passes_on_what_the_builder_refuses_of_counts(
    verdict, counts, expected, name
):
    judgement = Judgement(None, verdict, counts)
    refused(expected, name, from_judgement, judgement, **SMALL)
    with pytest.raises(expected) as caught:
        check_result.completed(**SMALL, counts=counts)
    with pytest.raises(expected) as passed_on:
        from_judgement(judgement, **SMALL)
    assert str(passed_on.value) == str(caught.value)


@pytest.mark.parametrize(("name", "value", "expected"), BAD_PARAMETERS, ids=str)
@pytest.mark.parametrize(
    "judgement",
    [PASSED, FAILED, Judgement(Broken.REPORT_FORM, None, None)],
    ids=["pass", "fail", "broken"],
)
def test_from_judgement_passes_on_what_the_builder_refuses_of_a_parameter(
    judgement, name, value, expected
):
    refused(expected, name, from_judgement, judgement, **{**SMALL, name: value})


def test_from_judgement_checks_the_judgement_before_the_parameters():
    bad = {**SMALL, "m": 0}
    refused(TypeError, "judgement", from_judgement, None, **bad)
    refused(
        TypeError, "judgement.verdict", from_judgement, Judgement(None, 1, ZEROS), **bad
    )
    broken = Judgement(Broken.TIMEOUT, Verdict.PASS, None)
    refused(ValueError, "judgement.verdict", from_judgement, broken, **bad)
    refused(
        ValueError, "m", from_judgement, Judgement(None, Verdict.FAIL, ZEROS), **bad
    )


@pytest.mark.parametrize("judgement", [PASSED, Judgement(Broken.TIMEOUT, None, None)])
def test_from_judgement_takes_exactly_its_keyword_arguments(judgement):
    for name in SMALL:
        arguments = {key: value for key, value in SMALL.items() if key != name}
        with pytest.raises(TypeError, match=name):
            from_judgement(judgement, **arguments)
    with pytest.raises(TypeError, match="seed"):
        from_judgement(judgement, **SMALL, seed=SEED)
    with pytest.raises(TypeError, match="counts"):
        from_judgement(judgement, **SMALL, counts=ZEROS)
    with pytest.raises(TypeError):
        from_judgement(judgement, *SMALL.values())
    with pytest.raises(TypeError, match="judgement"):
        from_judgement(**SMALL)


@pytest.mark.parametrize(
    "report",
    [bytearray(GOOD), GOOD.decode("latin-1"), None, memoryview(GOOD), [GOOD]],
    ids=["bytearray", "str", "none", "memoryview", "list"],
)
def test_from_report_refuses_a_report_that_is_not_bytes(report):
    refused(TypeError, "report", from_report, report, **CALL)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("seed", -1),
        ("seed", 2**64),
        ("seed", True),
        ("seed", None),
        ("m", 0),
        ("k", True),
        ("n", 1.0),
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
def test_from_report_passes_on_what_the_judging_refuses(name, value):
    refused(VerificationArgumentError, name, from_report, GOOD, **{**CALL, name: value})
    refused(VerificationArgumentError, name, from_report, None, **{**CALL, name: value})


def test_from_report_takes_exactly_its_keyword_arguments():
    for name in CALL:
        arguments = {key: value for key, value in CALL.items() if key != name}
        with pytest.raises(TypeError, match=name):
            from_report(GOOD, **arguments)
    with pytest.raises(TypeError, match="counts"):
        from_report(GOOD, **CALL, counts=ZEROS)
    with pytest.raises(TypeError):
        from_report(GOOD, *CALL.values())
    with pytest.raises(TypeError, match="report"):
        from_report(**CALL)


def test_from_judgement_leaves_its_arguments_and_shares_nothing():
    counts = [Counts(0, 0), Counts(2, 1), Counts(0, 0)]
    judgement = Judgement(None, Verdict.FAIL, counts)
    before = copy.deepcopy(judgement)
    arguments = dict(SMALL)
    first = from_judgement(judgement, **arguments)
    second = from_judgement(judgement, **arguments)
    expected = copy.deepcopy(second)
    assert first == second
    assert first is not second
    first["counts"][1]["failed"] = 9
    first["counts"].append({"failed": 0, "non_finite": 0})
    first["shape"]["m"] = 99
    first["tolerance"]["rtol"] = 9.0
    first["outcome"] = "pass"
    assert judgement == before
    assert counts == before.counts
    assert arguments == SMALL
    assert second == expected
    assert from_judgement(judgement, **arguments) == expected

    broken = Judgement(Broken.CHECK_VALUE, None, None)
    one = from_judgement(broken, **SMALL)
    other = from_judgement(broken, **SMALL)
    one["shape"]["k"] = 99
    one["condition"] = "time_limit"
    assert broken == Judgement(Broken.CHECK_VALUE, None, None)
    assert other == check_result.broken("check_value", **SMALL)


def test_from_report_gives_equal_results_for_equal_arguments():
    report = failing_report()
    kept = bytes(report)
    first = from_report(report, **CALL)
    first["counts"][1]["failed"] = 0
    assert from_report(report, **CALL) == from_report(kept, **CALL)
    assert from_report(report, **CALL)["counts"][1] == {"failed": 1, "non_finite": 0}
    assert report == kept


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    condition_of(Broken.TIMEOUT)
    from_judgement(PASSED, **SMALL)
    from_judgement(Judgement(Broken.EXIT_STATUS, None, None), **SMALL)
    from_report(GOOD, **CALL)
    from_report(GOOD[:-1], **CALL)
    with pytest.raises(TypeError):
        condition_of("time_limit")
    with pytest.raises(ValueError):
        from_judgement(Judgement(None, None, None), **SMALL)
    with pytest.raises(TypeError):
        from_report(None, **CALL)
    assert list(tmp_path.iterdir()) == []


def test_module_imports_the_builder_and_the_judging_only_and_has_no_entry():
    own = Path(check_judging.__file__)
    imported = imported_modules(own)
    assert imported == {
        "hilclaw",
        "hilclaw.check_result",
        "hilclaw.harness",
        "hilclaw.harness.verification",
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
    assert public == {"condition_of", "from_judgement", "from_report"}
    for name in public:
        parameters = inspect.signature(getattr(check_judging, name)).parameters
        for parameter in parameters.values():
            assert parameter.default is inspect.Parameter.empty, (name, parameter)
    keyword_only = inspect.Parameter.KEYWORD_ONLY
    for function, names in (
        (from_judgement, ["m", "k", "n", "draws", "rtol", "atol"]),
        (from_report, ["m", "k", "n", "draws", "seed", "rtol", "atol"]),
    ):
        parameters = list(inspect.signature(function).parameters.values())
        assert [parameter.name for parameter in parameters[1:]] == names
        assert all(parameter.kind is keyword_only for parameter in parameters[1:])
