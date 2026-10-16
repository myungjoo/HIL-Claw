import copy
import json
import reprlib

import pytest

from hilclaw import cases, keys
from hilclaw.cases import SCHEMA_VERSION, InvalidCaseError, build, validate
from hilclaw.hypotheses import InvalidHypothesisRecordError
from hilclaw.verdicts import InvalidVerdictRecordError
from hilclaw.verdicts_hypotheses import MismatchError

# The example of ADR-0072 (Example), copied from the record.
CASE_EXAMPLE = json.loads(
    """
{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "hypothesis_record": {
    "schema_version": 1, "run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1, "candidates": 1,
    "hypotheses": [
      {"id": "h1", "statement": "NOT-DECIDED-HERE",
       "basis": [{"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}],
       "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
       "origin": "system", "tested_by": [1]}
    ]
  },
  "verdict_record": {
    "schema_version": 1, "run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1,
    "verdicts": [
      {"hypothesis": "h1", "verdict": "supported", "cause": "NOT-DECIDED-HERE",
       "evidence": [
         {"kind": "check", "ref": {"round": 1, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
         {"kind": "check", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
         {"kind": "comparison", "metric": "latency_minimisation", "point": "board",
          "measured": {"round": 1, "candidate": 1, "attempt": 1},
          "against": {"round": 0, "candidate": 1, "attempt": 1}, "difference": "lower"}]}
    ]
  }
}
"""
)

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

RUN_ID = "20261009t012331z-9f3a6c1e0b7d4a52"
MEMBERS = ["hypothesis_record", "verdict_record"]
COPY_ERROR = {
    "hypothesis_record": InvalidHypothesisRecordError,
    "verdict_record": InvalidVerdictRecordError,
}


def example():
    return copy.deepcopy(CASE_EXAMPLE)


def with_verdict(value, difference=None):
    case = example()
    entry = case["verdict_record"]["verdicts"][0]
    entry["verdict"] = value
    if difference is None:
        entry["evidence"] = []
    else:
        entry["evidence"][2]["difference"] = difference
    return case


def invalid(document, message, cause=None):
    before = copy.deepcopy(document)
    with pytest.raises(InvalidCaseError) as raised:
        validate(document)
    assert str(raised.value) == message
    assert document == before
    if cause is None:
        assert raised.value.__cause__ is None
    else:
        assert type(raised.value.__cause__) is cause
    return raised.value


def assert_shares_nothing(left, right):
    if isinstance(left, dict):
        assert left is not right
        for name in left:
            assert_shares_nothing(left[name], right[name])
    elif isinstance(left, list):
        assert left is not right
        for a, b in zip(left, right, strict=True):
            assert_shares_nothing(a, b)


def test_adr_0072_example_is_valid():
    assert validate(CASE_EXAMPLE) is None
    assert CASE_EXAMPLE["hypothesis_record"] == HYPOTHESES_EXAMPLE
    assert CASE_EXAMPLE["verdict_record"] == VERDICTS_EXAMPLE


def test_schema_version_and_error_class():
    assert SCHEMA_VERSION == 1
    assert issubclass(InvalidCaseError, ValueError)
    for other in (InvalidHypothesisRecordError, InvalidVerdictRecordError):
        assert not issubclass(InvalidCaseError, other)
    assert not issubclass(InvalidCaseError, MismatchError)


def test_build_of_the_two_examples_is_the_adr_0072_example():
    assert build(HYPOTHESES_EXAMPLE, VERDICTS_EXAMPLE) == CASE_EXAMPLE


def test_build_without_verdicts_has_no_verdict_record():
    case = build(HYPOTHESES_EXAMPLE)
    assert case == {
        "schema_version": 1,
        "run_id": RUN_ID,
        "round": 1,
        "hypothesis_record": HYPOTHESES_EXAMPLE,
    }
    assert validate(case) is None
    assert build(HYPOTHESES_EXAMPLE, None) == case


def test_absent_verdict_record_is_valid():
    case = example()
    del case["verdict_record"]
    assert validate(case) is None


@pytest.mark.parametrize(
    "value, difference", [("refuted", "higher"), ("inconclusive", None)]
)
def test_refuted_and_inconclusive_verdicts_are_kept(value, difference):
    case = with_verdict(value, difference)
    assert validate(case) is None
    built = build(case["hypothesis_record"], case["verdict_record"])
    assert built == case
    assert built["verdict_record"]["verdicts"][0]["verdict"] == value


def test_unknown_top_level_members_are_passed_over_and_kept():
    case = example()
    case["note"] = {"run_id": "other", "round": 0}
    case["hypothesis_record"]["extra"] = [1, 2]
    case["verdict_record"]["later"] = None
    assert validate(case) is None
    built = build(case["hypothesis_record"], case["verdict_record"])
    assert "note" not in built
    assert built["hypothesis_record"]["extra"] == [1, 2]
    assert built["verdict_record"]["later"] is None
    assert validate(built) is None


def test_build_does_not_modify_or_share_its_inputs():
    hypotheses, verdicts = copy.deepcopy((HYPOTHESES_EXAMPLE, VERDICTS_EXAMPLE))
    built = build(hypotheses, verdicts)
    assert (hypotheses, verdicts) == (HYPOTHESES_EXAMPLE, VERDICTS_EXAMPLE)
    assert_shares_nothing(built["hypothesis_record"], hypotheses)
    assert_shares_nothing(built["verdict_record"], verdicts)
    hypotheses["hypotheses"][0]["statement"] = "changed"
    hypotheses["run_id"] = "changed"
    verdicts["verdicts"][0]["evidence"].clear()
    assert built == CASE_EXAMPLE


def test_validate_does_not_modify_its_input():
    case = example()
    validate(case)
    assert case == CASE_EXAMPLE


@pytest.mark.parametrize("document", [None, [], "case", 1, json.dumps(CASE_EXAMPLE)])
def test_non_object_case(document):
    invalid(document, f"case: must be an object, got {reprlib.repr(document)}")


@pytest.mark.parametrize(
    "name", ["schema_version", "run_id", "round", "hypothesis_record"]
)
def test_required_member_missing(name):
    case = example()
    del case[name]
    invalid(case, f"{name}: required member is missing")


def test_first_missing_member_wins():
    invalid({"verdict_record": {}}, "schema_version: required member is missing")


@pytest.mark.parametrize("value", [2, 0, "1", True, 1.0, None])
def test_schema_version_other_than_the_integer_1(value):
    case = example()
    case["schema_version"] = value
    invalid(case, f"schema_version: must be the integer 1, got {reprlib.repr(value)}")


@pytest.mark.parametrize("value", [1, None, "", "rün", "a" * 256, "a\n", b"run"])
def test_run_id_not_a_string(value):
    case = example()
    case["run_id"] = value
    error = invalid(
        case,
        "run_id: must be a string of 1 to 255 printable ASCII characters, "
        f"got {reprlib.repr(value)}",
    )
    assert len(str(error)) < 200


def test_run_id_of_255_characters_is_a_string():
    case = example()
    case["run_id"] = "a" * 255
    invalid(
        case,
        "hypothesis_record.run_id: must be equal to the run_id of the case "
        f"({reprlib.repr('a' * 255)}), got {reprlib.repr(RUN_ID)}",
    )


@pytest.mark.parametrize("value", [0, -1, True, 1.0, "1", None, keys.MAX_INTEGER + 1])
def test_round_out_of_range(value):
    case = example()
    case["round"] = value
    invalid(
        case,
        f"round: must be an integer from 1 to 2**53 - 1, got {reprlib.repr(value)}",
    )


def test_round_of_max_integer_is_held_against_the_copy():
    case = example()
    case["round"] = keys.MAX_INTEGER
    invalid(
        case,
        "hypothesis_record.round: must be equal to the round of the case "
        f"({keys.MAX_INTEGER}), got 1",
    )


@pytest.mark.parametrize("value", [None, [], "record", 1])
def test_hypothesis_record_not_an_object(value):
    case = example()
    case["hypothesis_record"] = value
    invalid(
        case,
        f"hypothesis_record: must be an object, got {reprlib.repr(value)}",
        InvalidHypothesisRecordError,
    )


def test_hypothesis_record_invalid_inside():
    case = example()
    case["hypothesis_record"]["hypotheses"][0]["id"] = "H1"
    rule = "must be a name matching [a-z][a-z0-9_]{0,31}, got 'H1'"
    error = invalid(
        case,
        f"hypothesis_record.hypotheses[0].id: {rule}",
        InvalidHypothesisRecordError,
    )
    assert str(error.__cause__) == f"hypotheses[0].id: {rule}"


@pytest.mark.parametrize("member", MEMBERS)
def test_copy_of_schema_version_2(member):
    case = example()
    case[member]["schema_version"] = 2
    invalid(
        case,
        f"{member}.schema_version: must be the integer 1, got 2",
        COPY_ERROR[member],
    )


@pytest.mark.parametrize("member", MEMBERS)
def test_copy_run_id_differs_from_the_case(member):
    case = example()
    case[member]["run_id"] = "other"
    invalid(
        case,
        f"{member}.run_id: must be equal to the run_id of the case "
        f"({reprlib.repr(RUN_ID)}), got 'other'",
    )


@pytest.mark.parametrize("member", MEMBERS)
def test_copy_round_differs_from_the_case(member):
    case = example()
    case[member]["round"] = 2
    evidence = case["verdict_record"]["verdicts"][0]["evidence"]
    if member == "verdict_record":
        evidence[0]["ref"]["round"] = 2
        evidence[2]["measured"]["round"] = 2
    invalid(case, f"{member}.round: must be equal to the round of the case (1), got 2")


@pytest.mark.parametrize("value", [None, [], [VERDICTS_EXAMPLE], "verdicts", 0])
def test_present_verdict_record_not_an_object(value):
    case = example()
    case["verdict_record"] = value
    invalid(
        case,
        f"verdict_record: must be an object, got {reprlib.repr(value)}",
        InvalidVerdictRecordError,
    )


def test_verdict_record_invalid_inside():
    case = example()
    case["verdict_record"]["verdicts"][0]["verdict"] = "maybe"
    invalid(
        case,
        "verdict_record.verdicts[0].verdict: must be supported or refuted or "
        "inconclusive, got 'maybe'",
        InvalidVerdictRecordError,
    )


def test_verdict_record_missing_a_verdict_for_a_hypothesis():
    case = example()
    second = copy.deepcopy(case["hypothesis_record"]["hypotheses"][0])
    second["id"] = "h2"
    case["hypothesis_record"]["hypotheses"].append(second)
    invalid(
        case,
        "verdict_record.verdicts: must hold a verdict for hypothesis 'h2' "
        "(hypotheses[1].id of the hypothesis record)",
        MismatchError,
    )


def test_verdict_record_with_a_wrong_value():
    case = with_verdict("refuted", "lower")
    invalid(
        case,
        "verdict_record.verdicts[0].verdict: must be 'supported' by the rule of "
        "ADR-0071 decision 4, got 'refuted'",
        MismatchError,
    )


def test_hypothesis_copy_error_wins_over_verdict_copy_error():
    case = example()
    case["hypothesis_record"]["candidates"] = 0
    case["verdict_record"] = None
    invalid(
        case,
        "hypothesis_record.candidates: must be an integer from 1 to 2**53 - 1, got 0",
        InvalidHypothesisRecordError,
    )


def test_case_member_error_wins_over_copy_error():
    case = example()
    case["hypothesis_record"] = None
    case["round"] = 0
    invalid(case, "round: must be an integer from 1 to 2**53 - 1, got 0")


@pytest.mark.parametrize("value", [None, [], "record", 7])
def test_build_of_a_non_object(value):
    with pytest.raises(InvalidCaseError) as raised:
        build(value)
    assert str(raised.value) == (
        f"hypothesis_record: must be an object, got {reprlib.repr(value)}"
    )
    assert type(raised.value.__cause__) is InvalidHypothesisRecordError


@pytest.mark.parametrize("name", ["run_id", "round"])
def test_build_of_a_hypothesis_record_lacking_a_member(name):
    hypotheses = copy.deepcopy(HYPOTHESES_EXAMPLE)
    del hypotheses[name]
    with pytest.raises(InvalidCaseError) as raised:
        build(hypotheses, VERDICTS_EXAMPLE)
    assert str(raised.value) == f"hypothesis_record.{name}: required member is missing"


def test_build_of_a_mismatched_pair():
    verdicts = copy.deepcopy(VERDICTS_EXAMPLE)
    verdicts["verdicts"][0]["verdict"] = "refuted"
    before = copy.deepcopy(verdicts)
    with pytest.raises(InvalidCaseError) as raised:
        build(HYPOTHESES_EXAMPLE, verdicts)
    assert str(raised.value).startswith("verdict_record.verdicts[0].verdict: ")
    assert type(raised.value.__cause__) is MismatchError
    assert verdicts == before


def test_build_of_a_verdict_record_of_another_run():
    verdicts = copy.deepcopy(VERDICTS_EXAMPLE)
    verdicts["run_id"] = "other"
    with pytest.raises(
        InvalidCaseError, match=r"^verdict_record\.run_id: must be equal"
    ):
        build(HYPOTHESES_EXAMPLE, verdicts)


@pytest.mark.parametrize("verdicts", [[], "verdicts", 0, False])
def test_build_of_a_non_object_verdict_record(verdicts):
    with pytest.raises(InvalidCaseError, match=r"^verdict_record: must be an object"):
        build(HYPOTHESES_EXAMPLE, verdicts)


def test_module_defines_no_reader_writer_or_entry_point():
    defined = {
        name
        for name, value in vars(cases).items()
        if getattr(value, "__module__", None) == cases.__name__
        and not name.startswith("_")
    }
    assert defined == {"InvalidCaseError", "build", "validate"}
