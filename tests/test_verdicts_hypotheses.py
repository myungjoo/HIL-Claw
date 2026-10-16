import copy
import json
import reprlib

import pytest

from hilclaw.hypotheses import InvalidHypothesisRecordError
from hilclaw.verdicts import InvalidVerdictRecordError
from hilclaw.verdicts_hypotheses import MismatchError, check

# The example of ADR-0059 (Example), copied from the record.
HYPOTHESES_EXAMPLE = json.loads(
    """
{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "candidates": 1,
  "hypotheses": [
    {
      "id": "h1",
      "statement": "NOT-DECIDED-HERE",
      "basis": [
        {"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}
      ],
      "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
      "origin": "system",
      "tested_by": [1]
    }
  ]
}
"""
)

# The example of ADR-0071 (Example), copied from the record.
VERDICTS_EXAMPLE = json.loads(
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

BASE = (0, 1, 1)


def ref(round=1, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


def check_entry(at, point="board", outcome="pass"):
    return {"kind": "check", "ref": ref(*at), "point": point, "outcome": outcome}


def comparison(measured=(1, 1, 1), against=BASE, difference="lower", point="board"):
    return {
        "kind": "comparison",
        "metric": "latency_minimisation",
        "point": point,
        "measured": ref(*measured),
        "against": ref(*against),
        "difference": difference,
    }


def counted(measured=(1, 1, 1), difference="lower"):
    return [
        check_entry(measured),
        check_entry(BASE),
        comparison(measured, difference=difference),
    ]


def verdict(value, evidence, hypothesis="h1"):
    return {
        "hypothesis": hypothesis,
        "verdict": value,
        "cause": "because",
        "evidence": evidence,
    }


def hypothesis(ident="h1", tested_by=(1,), direction="lower"):
    entry = copy.deepcopy(HYPOTHESES_EXAMPLE["hypotheses"][0])
    entry.update(
        id=ident,
        tested_by=list(tested_by),
        expected=[{"metric": "latency_minimisation", "direction": direction}],
    )
    return entry


def pair(entries, hyps=None, candidates=1):
    verdicts = copy.deepcopy(VERDICTS_EXAMPLE)
    verdicts["verdicts"] = entries
    hypotheses = copy.deepcopy(HYPOTHESES_EXAMPLE)
    hypotheses["candidates"] = candidates
    hypotheses["hypotheses"] = hyps or [hypothesis()]
    return verdicts, hypotheses


def mismatch(verdicts, hypotheses, message):
    with pytest.raises(MismatchError) as raised:
        check(verdicts, hypotheses)
    assert str(raised.value) == message
    assert not isinstance(raised.value, InvalidVerdictRecordError)
    assert not isinstance(raised.value, InvalidHypothesisRecordError)
    assert isinstance(raised.value, ValueError)


def test_adr_examples_form_a_valid_pair():
    assert check(VERDICTS_EXAMPLE, HYPOTHESES_EXAMPLE) is None


def test_documents_are_not_modified():
    verdicts, hypotheses = pair([verdict("refuted", counted(difference="higher"))])
    before = copy.deepcopy((verdicts, hypotheses))
    check(verdicts, hypotheses)
    assert (verdicts, hypotheses) == before
    before = copy.deepcopy((verdicts, hypotheses))
    verdicts["verdicts"][0]["verdict"] = "supported"
    before[0]["verdicts"][0]["verdict"] = "supported"
    with pytest.raises(MismatchError):
        check(verdicts, hypotheses)
    assert (verdicts, hypotheses) == before


def test_unknown_top_level_members_are_ignored():
    verdicts, hypotheses = copy.deepcopy((VERDICTS_EXAMPLE, HYPOTHESES_EXAMPLE))
    verdicts["note"] = {"run_id": "other", "round": 9}
    hypotheses["extra"] = [1, 2]
    check(verdicts, hypotheses)


def test_shared_candidate_each_verdict_reached_alone():
    hyps = [hypothesis("h1"), hypothesis("h2", direction="higher")]
    entries = [
        verdict("refuted", counted(), hypothesis="h2"),
        verdict("supported", counted(), hypothesis="h1"),
    ]
    check(*pair(entries, hyps))


def test_two_candidates_two_hypotheses():
    hyps = [hypothesis("h1", (1,)), hypothesis("h2", (2, 1))]
    entries = [
        verdict("supported", counted((1, 1, 1))),
        verdict("inconclusive", counted((1, 2, 1), "not_different"), "h2"),
    ]
    check(*pair(entries, hyps, candidates=2))


@pytest.mark.parametrize(
    "value, evidence",
    [
        ("inconclusive", []),
        ("refuted", counted(difference="higher")),
        (
            "refuted",
            [*counted(difference="higher"), comparison(difference="not_different")],
        ),
        ("supported", [*counted(), comparison(difference="lower", point="sim")]),
        ("supported", [*counted(), comparison((1, 1, 2), difference="higher")]),
        ("inconclusive", counted(difference="not_different")),
        ("inconclusive", [*counted(), comparison(difference="higher")]),
        ("inconclusive", [*counted(), comparison(difference="not_different")]),
        (
            "inconclusive",
            [check_entry((1, 1, 1)), check_entry(BASE), comparison(point="sim")],
        ),
        (
            "inconclusive",
            [
                check_entry((1, 1, 1), point="sim"),
                check_entry(BASE, point="sim"),
                comparison(point="sim"),
            ],
        ),
        (
            "inconclusive",
            [check_entry((1, 1, 1), outcome="fail"), check_entry(BASE), comparison()],
        ),
        (
            "inconclusive",
            [check_entry((1, 1, 1)), check_entry(BASE, outcome="broken"), comparison()],
        ),
        ("inconclusive", [check_entry((1, 1, 1)), comparison()]),
        ("inconclusive", [check_entry(BASE), comparison()]),
        (
            "inconclusive",
            [check_entry((1, 1, 1), point="sim"), check_entry(BASE), comparison()],
        ),
        ("inconclusive", [comparison(difference="higher")]),
    ],
)
def test_value_follows_the_rule(value, evidence):
    check(*pair([verdict(value, evidence)]))


@pytest.mark.parametrize("direction", ["lower", "higher"])
def test_direction_is_read_from_expected(direction):
    other = "higher" if direction == "lower" else "lower"
    hyps = [hypothesis(direction=direction)]
    check(*pair([verdict("supported", counted(difference=direction))], hyps))
    check(*pair([verdict("refuted", counted(difference=other))], hyps))


@pytest.mark.parametrize(
    "recorded, computed, evidence",
    [
        ("supported", "refuted", counted(difference="higher")),
        ("supported", "inconclusive", counted(difference="not_different")),
        ("supported", "inconclusive", [*counted(), comparison(difference="higher")]),
        ("refuted", "supported", counted()),
        ("refuted", "inconclusive", counted(difference="not_different")),
        ("refuted", "inconclusive", [*counted(difference="higher"), comparison()]),
        ("inconclusive", "supported", counted()),
        ("inconclusive", "refuted", counted(difference="higher")),
    ],
)
def test_recorded_value_differs_from_rule(recorded, computed, evidence):
    mismatch(
        *pair([verdict(recorded, evidence)]),
        f"verdicts[0].verdict: must be '{computed}' by the rule of ADR-0071 "
        f"decision 4, got '{recorded}'",
    )


def test_value_mismatch_names_the_entry():
    hyps = [hypothesis("h1"), hypothesis("h2")]
    entries = [
        verdict("supported", counted()),
        verdict("supported", counted(difference="higher"), "h2"),
    ]
    mismatch(
        *pair(entries, hyps),
        "verdicts[1].verdict: must be 'refuted' by the rule of ADR-0071 decision 4, "
        "got 'supported'",
    )


def test_invalid_verdicts_document_passes_through():
    verdicts = copy.deepcopy(VERDICTS_EXAMPLE)
    del verdicts["round"]
    with pytest.raises(
        InvalidVerdictRecordError, match=r"^round: required member is missing$"
    ):
        check(verdicts, HYPOTHESES_EXAMPLE)


def test_invalid_hypothesis_record_passes_through():
    hypotheses = copy.deepcopy(HYPOTHESES_EXAMPLE)
    hypotheses["candidates"] = 0
    with pytest.raises(InvalidHypothesisRecordError, match=r"^candidates: must be "):
        check(VERDICTS_EXAMPLE, hypotheses)


def test_invalid_verdicts_wins_over_invalid_hypotheses():
    verdicts, hypotheses = copy.deepcopy((VERDICTS_EXAMPLE, HYPOTHESES_EXAMPLE))
    verdicts["run_id"] = ""
    hypotheses["run_id"] = ""
    with pytest.raises(InvalidVerdictRecordError, match=r"^run_id: "):
        check(verdicts, hypotheses)


@pytest.mark.parametrize("which", [0, 1])
def test_other_schema_version_is_refused(which):
    documents = list(copy.deepcopy((VERDICTS_EXAMPLE, HYPOTHESES_EXAMPLE)))
    documents[which]["schema_version"] = 2
    error = (InvalidVerdictRecordError, InvalidHypothesisRecordError)[which]
    with pytest.raises(error, match=r"^schema_version: must be the integer 1, got 2$"):
        check(*documents)


@pytest.mark.parametrize(
    "verdicts, hypotheses, error",
    [
        (None, HYPOTHESES_EXAMPLE, InvalidVerdictRecordError),
        ([VERDICTS_EXAMPLE], HYPOTHESES_EXAMPLE, InvalidVerdictRecordError),
        (VERDICTS_EXAMPLE, "text", InvalidHypothesisRecordError),
        (VERDICTS_EXAMPLE, 1, InvalidHypothesisRecordError),
    ],
)
def test_non_mapping_inputs_are_refused(verdicts, hypotheses, error):
    with pytest.raises(error, match=r"^record: must be an object, got "):
        check(verdicts, hypotheses)


def test_run_id_differs():
    verdicts = copy.deepcopy(VERDICTS_EXAMPLE)
    verdicts["run_id"] = "other-run"
    mismatch(
        verdicts,
        HYPOTHESES_EXAMPLE,
        "run_id: must be equal to the run_id of the hypothesis record "
        f"({reprlib.repr(HYPOTHESES_EXAMPLE['run_id'])}), got 'other-run'",
    )


def test_round_differs():
    verdicts, hypotheses = copy.deepcopy((VERDICTS_EXAMPLE, HYPOTHESES_EXAMPLE))
    hypotheses["round"] = 2
    mismatch(
        verdicts,
        hypotheses,
        "round: must be equal to the round of the hypothesis record (2), got 1",
    )


def test_run_id_is_checked_before_round():
    verdicts, hypotheses = copy.deepcopy((VERDICTS_EXAMPLE, HYPOTHESES_EXAMPLE))
    verdicts["run_id"] = "other-run"
    hypotheses["round"] = 2
    with pytest.raises(MismatchError, match=r"^run_id: "):
        check(verdicts, hypotheses)


def test_verdict_for_unknown_id():
    entries = [verdict("supported", counted()), verdict("inconclusive", [], "h9")]
    mismatch(
        *pair(entries),
        "verdicts[1].hypothesis: must be an id of the hypothesis record, got 'h9'",
    )


def test_hypothesis_without_verdict():
    hyps = [hypothesis("h1"), hypothesis("h2")]
    mismatch(
        *pair([verdict("supported", counted())], hyps),
        "verdicts: hold no verdict for hypothesis 'h2' "
        "(hypotheses[1].id of the hypothesis record)",
    )


def test_unknown_id_is_reported_before_missing_verdict():
    hyps = [hypothesis("h1"), hypothesis("h2")]
    entries = [verdict("supported", counted()), verdict("inconclusive", [], "h9")]
    with pytest.raises(MismatchError, match=r"^verdicts\[1\]\.hypothesis: "):
        check(*pair(entries, hyps))


def test_missing_verdict_is_reported_before_measured_outside_tested_by():
    hyps = [hypothesis("h1"), hypothesis("h2", (2,))]
    entries = [verdict("inconclusive", [comparison((1, 2, 1))])]
    with pytest.raises(
        MismatchError, match=r"^verdicts: hold no verdict for hypothesis 'h2'"
    ):
        check(*pair(entries, hyps, candidates=2))


@pytest.mark.parametrize(
    "value, evidence, at",
    [
        ("supported", counted((1, 2, 1)), 2),
        ("inconclusive", [comparison((1, 2, 1), point="sim")], 0),
        (
            "inconclusive",
            [check_entry((1, 2, 1)), comparison((1, 2, 1), difference="not_different")],
            1,
        ),
        ("supported", [*counted(), comparison((1, 2, 1), point="sim")], 3),
    ],
)
def test_measured_outside_tested_by(value, evidence, at):
    hyps = [hypothesis("h1", (1,)), hypothesis("h2", (2,))]
    entries = [verdict(value, evidence), verdict("inconclusive", [], "h2")]
    mismatch(
        *pair(entries, hyps, candidates=2),
        f"verdicts[0].evidence[{at}].measured.candidate: must be in the tested_by "
        "of hypothesis 'h1' ([1]), got 2",
    )


def test_against_is_not_held_against_tested_by():
    hyps = [hypothesis("h1", (1,)), hypothesis("h2", (2,))]
    evidence = [
        check_entry((1, 1, 1)),
        check_entry((1, 2, 1)),
        comparison(against=(1, 2, 1)),
    ]
    entries = [verdict("supported", evidence), verdict("inconclusive", [], "h2")]
    check(*pair(entries, hyps, candidates=2))


def test_tested_by_is_checked_for_every_verdict_before_any_value():
    hyps = [hypothesis("h1", (1,)), hypothesis("h2", (2,))]
    entries = [
        verdict("refuted", counted()),
        verdict("inconclusive", [comparison((1, 1, 1))], "h2"),
    ]
    with pytest.raises(
        MismatchError, match=r"^verdicts\[1\]\.evidence\[0\]\.measured\.candidate: "
    ):
        check(*pair(entries, hyps, candidates=2))
