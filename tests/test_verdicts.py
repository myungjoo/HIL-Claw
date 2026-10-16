import copy
import json
from types import MappingProxyType

import pytest

from hilclaw import verdicts
from hilclaw.verdicts import InvalidVerdictRecordError, validate

REMOVE = object()

# The example of ADR-0071 (Example), copied from the record.
ADR_EXAMPLE = json.loads(
    """
{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "verdicts": [
    {
      "hypothesis": "h1",
      "verdict": "supported",
      "cause": "NOT-DECIDED-HERE",
      "evidence": [
        {"kind": "check", "ref": {"round": 1, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
        {"kind": "check", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
        {"kind": "comparison", "metric": "latency_minimisation", "point": "board",
         "measured": {"round": 1, "candidate": 1, "attempt": 1},
         "against": {"round": 0, "candidate": 1, "attempt": 1}, "difference": "lower"}
      ]
    }
  ]
}
"""
)

# Member names copied from the tables and lists of ADR-0071 decisions 2 and 3.
ADR_TOP = ["schema_version", "run_id", "round", "verdicts"]
ADR_VERDICT = ["hypothesis", "verdict", "cause", "evidence"]
ADR_CHECK = ["kind", "ref", "point", "outcome"]
ADR_COMPARISON = ["kind", "metric", "point", "measured", "against", "difference"]

BAD_NAMES = ["", "Upper", "1digit", "with-hyphen", "a" * 33, "name\n", 7, None]
BAD_STRINGS = ["", "s" * 256, "line\nbreak", "café", 7, None, True, ["s"]]
BAD_TEXTS = ["", 7, None, True, ["text"], {"a": "b"}, b"text"]
NOT_OBJECTS = [None, "text", 1, 1.5, True, ["a"], [("a", 1)]]
NOT_ARRAYS = [None, "text", 1, True, {"a": 1}, ("a",)]


class IntSubclass(int):
    pass


BAD_INTEGERS = [-1, 2**53, True, False, 1.0, "1", None, [1], IntSubclass(1)]
BAD_POSITIVE_INTEGERS = [0, *BAD_INTEGERS]


def ref(round=1, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


def check(at=None, point="board", outcome="pass"):
    return {
        "kind": "check",
        "ref": dict(at or ref()),
        "point": point,
        "outcome": outcome,
    }


def comparison(measured=None, against=None, point="board", difference="lower"):
    return {
        "kind": "comparison",
        "metric": "latency_minimisation",
        "point": point,
        "measured": measured or ref(),
        "against": against or ref(round=0),
        "difference": difference,
    }


def counted(measured=None, against=None, difference="lower"):
    measured, against = measured or ref(), against or ref(round=0)
    return [
        check(measured),
        check(against),
        comparison(measured, against, difference=difference),
    ]


def verdict(hypothesis="h1", value="supported", evidence=None):
    return {
        "hypothesis": hypothesis,
        "verdict": value,
        "cause": "synthetic cause",
        "evidence": counted() if evidence is None else evidence,
    }


def record(*entries, round=1):
    return {
        "schema_version": 1,
        "run_id": "synthetic-run_01",
        "round": round,
        "verdicts": list(entries) or [verdict()],
    }


def with_value(document, path, value):
    document = copy.deepcopy(document)
    *parents, last = path
    target = document
    for step in parents:
        target = target[step]
    if value is REMOVE:
        del target[last]
    else:
        target[last] = value
    return document


def rejected(document, path):
    with pytest.raises(InvalidVerdictRecordError) as caught:
        validate(document)
    assert str(caught.value).startswith(f"{path}: ")
    return str(caught.value)


EVIDENCE = ["verdicts", 0, "evidence"]
CHECK = [*EVIDENCE, 0]
COMPARISON = [*EVIDENCE, 2]
CHECK_PATH = "verdicts[0].evidence[0]"
COMPARISON_PATH = "verdicts[0].evidence[2]"


def test_schema_version_is_one():
    assert verdicts.SCHEMA_VERSION == 1


def test_error_is_a_value_error():
    assert issubclass(InvalidVerdictRecordError, ValueError)


def test_adr_example_is_valid():
    assert validate(ADR_EXAMPLE) is None


def test_document_is_not_modified():
    document = record(verdict(), verdict("h2", "inconclusive", []))
    before = copy.deepcopy(document)
    validate(document)
    assert document == before


def test_read_only_mappings_are_accepted():
    evidence = [MappingProxyType(item) for item in counted()]
    validate(MappingProxyType(record(MappingProxyType(verdict(evidence=evidence)))))


def test_inconclusive_with_empty_evidence():
    validate(record(verdict(value="inconclusive", evidence=[])))


def test_inconclusive_with_only_sim_comparisons():
    evidence = [
        check(ref(), "sim"),
        check(ref(round=0), "sim"),
        comparison(point="sim"),
    ]
    validate(record(verdict(value="inconclusive", evidence=evidence)))


def test_inconclusive_with_a_counted_comparison():
    validate(record(verdict(value="inconclusive", evidence=counted())))


@pytest.mark.parametrize("difference", ["lower", "higher", "not_different"])
def test_refuted_with_a_counted_comparison(difference):
    evidence = counted(difference=difference)
    validate(record(verdict(value="refuted", evidence=evidence)))


def test_two_verdicts_sharing_one_candidates_comparison():
    validate(record(verdict("h1"), verdict("h2", "refuted")))


def test_check_at_sim_and_at_board_for_the_same_ref():
    evidence = [check(ref(), "sim", "fail"), *counted()]
    validate(record(verdict(evidence=evidence)))


def test_against_of_another_candidate_of_the_round():
    against = ref(round=3, candidate=2, attempt=1)
    evidence = counted(measured=ref(round=3), against=against)
    validate(record(verdict(evidence=evidence), round=3))


def test_against_of_another_attempt_of_the_same_candidate():
    evidence = counted(measured=ref(attempt=2), against=ref(attempt=1))
    validate(record(verdict(evidence=evidence)))


def test_check_of_any_round_is_valid():
    evidence = [check(ref(round=9), "sim", "broken"), *counted()]
    validate(record(verdict(evidence=evidence)))


def test_counted_comparison_beside_uncounted_ones():
    evidence = [
        comparison(against=ref(round=0, candidate=2), point="sim"),
        comparison(against=ref(round=0, candidate=3)),
        *counted(),
    ]
    validate(record(verdict(evidence=evidence)))


@pytest.mark.parametrize(
    "value", [None, True, 1.5, "text", [1, "a"], {"nested": {"deep": [None]}}, -1]
)
@pytest.mark.parametrize("name", ["ranking", "Unknown-Name", ""])
def test_unknown_top_level_member_is_passed_over(name, value):
    validate({**record(), name: value})


def test_non_string_top_level_member_name_is_passed_over():
    validate({**record(), 1: "x"})


@pytest.mark.parametrize("value", [1, 2**53 - 1])
def test_round_bounds_are_valid(value):
    evidence = counted(measured=ref(round=value), against=ref(round=value - 1))
    validate(record(verdict(evidence=evidence), round=value))


def test_ref_bounds_are_valid():
    big = 2**53 - 1
    evidence = counted(measured=ref(1, big, big), against=ref(0, big, big))
    validate(record(verdict(evidence=evidence)))


@pytest.mark.parametrize("value", [*NOT_OBJECTS, b"{}", object()])
def test_document_that_is_not_a_mapping_is_rejected(value):
    rejected(value, "record")


@pytest.mark.parametrize("name", ADR_TOP)
def test_missing_top_level_member_is_rejected(name):
    message = rejected(with_value(record(), [name], REMOVE), name)
    assert "required member is missing" in message


@pytest.mark.parametrize("value", [0, 2, -1, "1", True, 1.0, None, IntSubclass(1)])
def test_schema_version_other_than_the_integer_one_is_rejected(value):
    rejected(with_value(record(), ["schema_version"], value), "schema_version")


@pytest.mark.parametrize("value", BAD_STRINGS)
def test_bad_run_id_is_rejected(value):
    rejected(with_value(record(), ["run_id"], value), "run_id")


@pytest.mark.parametrize("value", ["a", "s" * 255, " ~", "UPPER/and.dots"])
def test_run_id_is_a_string_not_a_directory_name(value):
    validate(with_value(record(), ["run_id"], value))


@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_round_is_rejected(value):
    rejected(with_value(record(), ["round"], value), "round")


def test_round_zero_is_rejected():
    evidence = [check(ref(round=0)), comparison(ref(round=0), ref(round=0, attempt=2))]
    document = record(verdict(value="inconclusive", evidence=evidence), round=0)
    assert "from 1" in rejected(document, "round")


@pytest.mark.parametrize("value", [*NOT_ARRAYS, []])
def test_bad_verdicts_is_rejected(value):
    rejected(with_value(record(), ["verdicts"], value), "verdicts")


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_verdict_that_is_not_an_object_is_rejected(value):
    rejected(record(value), "verdicts[0]")


@pytest.mark.parametrize("name", ADR_VERDICT)
def test_missing_verdict_member_is_rejected(name):
    path = ["verdicts", 0, name]
    message = rejected(with_value(record(), path, REMOVE), f"verdicts[0].{name}")
    assert "required member is missing" in message


@pytest.mark.parametrize("name", ["id", "expected", "shared_with", 1])
def test_unknown_verdict_member_is_rejected(name):
    message = rejected(with_value(record(), ["verdicts", 0, name], "x"), "verdicts[0]")
    assert "unknown member" in message


@pytest.mark.parametrize("value", BAD_NAMES)
def test_bad_hypothesis_is_rejected(value):
    path = ["verdicts", 0, "hypothesis"]
    rejected(with_value(record(), path, value), "verdicts[0].hypothesis")


@pytest.mark.parametrize("value", ["a", "a" * 32, "h_1", "z9"])
def test_hypothesis_at_its_limits_is_valid(value):
    validate(with_value(record(), ["verdicts", 0, "hypothesis"], value))


def test_duplicate_hypothesis_is_rejected():
    document = record(verdict("h1"), verdict("h2"), verdict("h1", "inconclusive", []))
    assert "unique" in rejected(document, "verdicts[2].hypothesis")


@pytest.mark.parametrize(
    "value",
    ["partially_supported", "Supported", "unknown", "", None, 1, True, ["refuted"]],
)
def test_verdict_value_not_admitted_is_rejected(value):
    path = ["verdicts", 0, "verdict"]
    rejected(with_value(record(), path, value), "verdicts[0].verdict")


@pytest.mark.parametrize("value", BAD_TEXTS)
def test_bad_cause_is_rejected(value):
    path = ["verdicts", 0, "cause"]
    rejected(with_value(record(), path, value), "verdicts[0].cause")


@pytest.mark.parametrize("value", ["x", "x" * 300, "line\nbreak", "café 원인"])
def test_cause_has_no_character_or_length_restriction(value):
    validate(with_value(record(), ["verdicts", 0, "cause"], value))


@pytest.mark.parametrize("value", NOT_ARRAYS)
def test_bad_evidence_is_rejected(value):
    rejected(with_value(record(), EVIDENCE, value), "verdicts[0].evidence")


@pytest.mark.parametrize("value", ["supported", "refuted"])
def test_judged_verdict_with_empty_evidence_is_rejected(value):
    message = rejected(
        record(verdict(value=value, evidence=[])), "verdicts[0].evidence"
    )
    assert f"at least one entry when {value}" in message


def board_comparison_with(measured_check, against_check):
    measured, against = ref(), ref(round=0)
    evidence = [comparison(measured, against)]
    if measured_check:
        evidence.append(check(measured, *measured_check))
    if against_check:
        evidence.append(check(against, *against_check))
    return evidence


@pytest.mark.parametrize("value", ["supported", "refuted"])
@pytest.mark.parametrize(
    "evidence",
    [
        [check(ref(), "sim"), check(ref(round=0), "sim"), comparison(point="sim")],
        [check(), check(ref(round=0)), comparison(point="sim")],
        [check(), check(ref(round=0))],
        board_comparison_with(None, ("board", "pass")),
        board_comparison_with(("board", "pass"), None),
        board_comparison_with(None, None),
        board_comparison_with(("board", "fail"), ("board", "pass")),
        board_comparison_with(("board", "broken"), ("board", "pass")),
        board_comparison_with(("board", "pass"), ("board", "fail")),
        board_comparison_with(("board", "pass"), ("board", "broken")),
        board_comparison_with(("sim", "pass"), ("board", "pass")),
        board_comparison_with(("board", "pass"), ("sim", "pass")),
        board_comparison_with(("sim", "pass"), ("sim", "pass")),
        [check(ref(attempt=2)), check(ref(round=0)), comparison()],
    ],
)
def test_judged_verdict_without_a_counted_comparison_is_rejected(value, evidence):
    message = rejected(
        record(verdict(value=value, evidence=evidence)), "verdicts[0].evidence"
    )
    assert f"counted comparison when {value}" in message


def test_counted_comparison_needs_checks_of_the_same_verdict():
    other = verdict("h2", "inconclusive", [check(), check(ref(round=0))])
    alone = verdict("h1", evidence=[comparison()])
    rejected(record(other, alone), "verdicts[1].evidence")


@pytest.mark.parametrize("value", [*NOT_OBJECTS, "check"])
def test_evidence_entry_that_is_not_an_object_is_rejected(value):
    rejected(record(verdict(value="inconclusive", evidence=[value])), CHECK_PATH)


def test_evidence_without_kind_is_rejected():
    entry = check()
    del entry["kind"]
    message = rejected(record(verdict(evidence=[entry])), f"{CHECK_PATH}.kind")
    assert "required member is missing" in message


@pytest.mark.parametrize(
    "kind", ["attempt", "measurement", "Check", "", None, 1, ["check"]]
)
def test_evidence_kind_not_admitted_is_rejected(kind):
    rejected(with_value(record(), [*CHECK, "kind"], kind), f"{CHECK_PATH}.kind")


@pytest.mark.parametrize(
    ("index", "name"),
    [(0, name) for name in ADR_CHECK[1:]] + [(2, name) for name in ADR_COMPARISON[1:]],
)
def test_missing_evidence_member_is_rejected(index, name):
    path = [*EVIDENCE, index, name]
    message = rejected(
        with_value(record(), path, REMOVE), f"verdicts[0].evidence[{index}].{name}"
    )
    assert "required member is missing" in message


@pytest.mark.parametrize(
    ("index", "name"),
    [(0, "metric"), (0, "measured"), (0, "path"), (2, "ref"), (2, "outcome"), (2, 1)],
)
def test_unknown_evidence_member_is_rejected(index, name):
    path = [*EVIDENCE, index, name]
    message = rejected(
        with_value(record(), path, "x"), f"verdicts[0].evidence[{index}]"
    )
    assert "unknown member" in message


@pytest.mark.parametrize("value", ["hil", "Board", "", None, 1, ["board"]])
@pytest.mark.parametrize("index", [0, 2])
def test_bad_point_is_rejected(index, value):
    path = [*EVIDENCE, index, "point"]
    rejected(with_value(record(), path, value), f"verdicts[0].evidence[{index}].point")


@pytest.mark.parametrize("value", ["passed", "error", "Pass", "", None, True])
def test_bad_outcome_is_rejected(value):
    rejected(with_value(record(), [*CHECK, "outcome"], value), f"{CHECK_PATH}.outcome")


def test_duplicate_check_of_ref_and_point_is_rejected():
    evidence = [*counted(), check(ref(), "board", "fail")]
    message = rejected(record(verdict(evidence=evidence)), "verdicts[0].evidence[3]")
    assert "same ref and point" in message


@pytest.mark.parametrize(
    "value",
    ["memory_ceiling", "latency", "throughput", "", None, 1, ["latency_minimisation"]],
)
def test_metric_not_admitted_is_rejected(value):
    path = [*COMPARISON, "metric"]
    rejected(with_value(record(), path, value), f"{COMPARISON_PATH}.metric")


@pytest.mark.parametrize(
    "value", ["different", "same", "Lower", "equal", "", None, 1, True]
)
def test_bad_difference_is_rejected(value):
    path = [*COMPARISON, "difference"]
    rejected(with_value(record(), path, value), f"{COMPARISON_PATH}.difference")


REF_PLACES = [(CHECK, f"{CHECK_PATH}.ref", "ref")] + [
    (COMPARISON, f"{COMPARISON_PATH}.{name}", name) for name in ("measured", "against")
]


@pytest.mark.parametrize(("entry", "where", "name"), REF_PLACES)
@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_ref_that_is_not_an_object_is_rejected(entry, where, name, value):
    rejected(with_value(record(), [*entry, name], value), where)


@pytest.mark.parametrize(("entry", "where", "name"), REF_PLACES)
@pytest.mark.parametrize("member", ["round", "candidate", "attempt"])
def test_missing_ref_member_is_rejected(entry, where, name, member):
    document = with_value(record(), [*entry, name, member], REMOVE)
    assert "required member is missing" in rejected(document, f"{where}.{member}")


@pytest.mark.parametrize(("entry", "where", "name"), REF_PLACES)
def test_unknown_ref_member_is_rejected(entry, where, name):
    document = with_value(record(), [*entry, name, "run_id"], "other")
    assert "unknown member" in rejected(document, where)


@pytest.mark.parametrize(("entry", "where", "name"), REF_PLACES)
@pytest.mark.parametrize("value", BAD_INTEGERS)
def test_bad_ref_round_is_rejected(entry, where, name, value):
    document = with_value(record(), [*entry, name, "round"], value)
    rejected(document, f"{where}.round")


@pytest.mark.parametrize(("entry", "where", "name"), REF_PLACES)
@pytest.mark.parametrize("member", ["candidate", "attempt"])
@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_ref_candidate_or_attempt_is_rejected(entry, where, name, member, value):
    document = with_value(record(), [*entry, name, member], value)
    rejected(document, f"{where}.{member}")


@pytest.mark.parametrize("value", [0, 1, 3, 2**53 - 1])
def test_measured_of_another_round_is_rejected(value):
    evidence = [comparison(ref(round=value), ref(round=0, candidate=2))]
    document = record(verdict(value="inconclusive", evidence=evidence), round=2)
    message = rejected(document, "verdicts[0].evidence[0].measured.round")
    assert "equal to round (2)" in message


@pytest.mark.parametrize("value", [3, 4, 2**53 - 1])
def test_against_of_a_later_round_is_rejected(value):
    evidence = [comparison(ref(round=2), ref(round=value))]
    document = record(verdict(value="inconclusive", evidence=evidence), round=2)
    message = rejected(document, "verdicts[0].evidence[0].against.round")
    assert "at most round (2)" in message


def test_against_equal_to_measured_is_rejected():
    evidence = [check(), comparison(ref(), ref())]
    message = rejected(
        record(verdict(evidence=evidence)), "verdicts[0].evidence[1].against"
    )
    assert "other than measured" in message


def test_later_bad_evidence_entry_is_reported_with_its_index():
    evidence = [*counted(), {**check(), "kind": "case"}]
    rejected(record(verdict(evidence=evidence)), "verdicts[0].evidence[3].kind")


def test_first_rule_broken_is_reported():
    document = record(verdict("h1"), verdict("h1", evidence=[]))
    rejected(document, "verdicts[1].evidence")
