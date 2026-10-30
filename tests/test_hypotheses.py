import copy
import json
from types import MappingProxyType

import pytest

from hilclaw import hypotheses
from hilclaw.hypotheses import InvalidHypothesisRecordError, validate

REMOVE = object()

# The example of ADR-0059 (Example), copied from the record.
ADR_EXAMPLE = json.loads(
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

# Member names copied from the tables of ADR-0059 decisions 2 and 3.
ADR_TOP = ["schema_version", "run_id", "round", "candidates", "hypotheses"]
ADR_HYPOTHESIS = ["id", "statement", "basis", "expected", "origin", "tested_by"]

BAD_NAMES = ["", "Upper", "1digit", "with-hyphen", "a" * 33, "name\n", 7, None]
BAD_STRINGS = ["", "s" * 256, "line\nbreak", "café", 7, None, True, ["s"]]
BAD_TEXTS = ["", 7, None, True, ["text"], {"a": "b"}, b"text"]
NOT_OBJECTS = [None, "text", 1, 1.5, True, ["a"], [("a", 1)]]
NOT_ARRAYS = [None, "text", 1, True, {"a": 1}, ("a",)]


class IntSubclass(int):
    pass


BAD_INTEGERS = [-1, 2**53, True, False, 1.0, "1", None, [1], IntSubclass(1)]
BAD_POSITIVE_INTEGERS = [0, *BAD_INTEGERS]


def attempt_basis(round=0, candidate=1, attempt=1, text="observed"):
    ref = {"round": round, "candidate": candidate, "attempt": attempt}
    return {"kind": "attempt", "ref": ref, "text": text}


def external_basis():
    return {
        "kind": "external",
        "source": "synthetic-paper",
        "version": "sha256:0123",
        "text": "material",
    }


def entry(ident="h1", tested_by=(1,), basis=None, direction="lower"):
    return {
        "id": ident,
        "statement": "synthetic statement",
        "basis": basis if basis is not None else [attempt_basis()],
        "expected": [{"metric": "latency_minimisation", "direction": direction}],
        "origin": "system",
        "tested_by": list(tested_by),
    }


def record(*entries, round=1, candidates=1):
    return {
        "schema_version": 1,
        "run_id": "synthetic-run_01",
        "round": round,
        "candidates": candidates,
        "hypotheses": list(entries) or [entry()],
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
    with pytest.raises(InvalidHypothesisRecordError) as caught:
        validate(document)
    assert str(caught.value).startswith(f"{path}: ")
    return str(caught.value)


def test_schema_version_is_one():
    assert hypotheses.SCHEMA_VERSION == 1


def test_error_is_a_value_error():
    assert issubclass(InvalidHypothesisRecordError, ValueError)


def test_adr_example_is_valid():
    assert validate(ADR_EXAMPLE) is None


def test_document_is_not_modified():
    document = record(entry(basis=[attempt_basis(), external_basis()]))
    before = copy.deepcopy(document)
    validate(document)
    assert document == before


def test_read_only_mappings_are_accepted():
    basis = attempt_basis()
    basis["ref"] = MappingProxyType(basis["ref"])
    hypothesis = entry(basis=[MappingProxyType(basis)])
    hypothesis["expected"] = [MappingProxyType(hypothesis["expected"][0])]
    validate(MappingProxyType(record(MappingProxyType(hypothesis))))


def test_one_hypothesis_spanning_two_candidates():
    validate(record(entry(tested_by=[2, 1]), candidates=2))


def test_two_hypotheses_on_one_candidate():
    validate(record(entry("h1"), entry("h2"), candidates=1))


def test_one_hypothesis_per_candidate():
    validate(record(entry("h1", [1]), entry("h2", [2]), candidates=2))


def test_overlapping_hypotheses():
    validate(record(entry("h1", [1, 2]), entry("h2", [2]), candidates=2))


def test_external_basis():
    validate(record(entry(basis=[external_basis()])))


def test_mixed_basis():
    validate(record(entry(basis=[external_basis(), attempt_basis(round=3)]), round=4))


def test_direction_higher():
    validate(record(entry(direction="higher")))


@pytest.mark.parametrize(
    "value", [None, True, 1.5, "text", [1, "a"], {"nested": {"deep": [None]}}, -1]
)
@pytest.mark.parametrize("name", ["cases", "Unknown-Name", ""])
def test_unknown_top_level_member_is_passed_over(name, value):
    validate({**record(), name: value})


def test_non_string_top_level_member_name_is_passed_over():
    validate({**record(), 1: "x"})


@pytest.mark.parametrize("value", [1, 2**53 - 1])
def test_round_bounds_are_valid(value):
    validate(record(entry(basis=[attempt_basis(round=value - 1)]), round=value))


def test_ref_bounds_are_valid():
    big = 2**53 - 1
    basis = [attempt_basis(round=0, candidate=big, attempt=big)]
    validate(record(entry(basis=basis)))


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
    message = rejected(with_value(record(), ["round"], 0), "round")
    assert "from 1" in message


@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_candidates_is_rejected(value):
    rejected(with_value(record(), ["candidates"], value), "candidates")


@pytest.mark.parametrize("value", [*NOT_ARRAYS, []])
def test_bad_hypotheses_is_rejected(value):
    rejected(with_value(record(), ["hypotheses"], value), "hypotheses")


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_hypothesis_that_is_not_an_object_is_rejected(value):
    rejected(record(value), "hypotheses[0]")


@pytest.mark.parametrize("name", ADR_HYPOTHESIS)
def test_missing_hypothesis_member_is_rejected(name):
    path = ["hypotheses", 0, name]
    message = rejected(with_value(record(), path, REMOVE), f"hypotheses[0].{name}")
    assert "required member is missing" in message


@pytest.mark.parametrize("name", ["verdict", "technique", 1])
def test_unknown_hypothesis_member_is_rejected(name):
    path = ["hypotheses", 0, name]
    message = rejected(with_value(record(), path, "x"), "hypotheses[0]")
    assert "unknown member" in message


@pytest.mark.parametrize("value", BAD_NAMES)
def test_bad_hypothesis_id_is_rejected(value):
    rejected(with_value(record(), ["hypotheses", 0, "id"], value), "hypotheses[0].id")


@pytest.mark.parametrize("value", ["a", "a" * 32, "h_1", "z9"])
def test_hypothesis_id_at_its_limits_is_valid(value):
    validate(with_value(record(), ["hypotheses", 0, "id"], value))


def test_duplicate_hypothesis_id_is_rejected():
    message = rejected(record(entry("h1"), entry("h1")), "hypotheses[1].id")
    assert "unique" in message


@pytest.mark.parametrize("value", BAD_TEXTS)
def test_bad_statement_is_rejected(value):
    path = ["hypotheses", 0, "statement"]
    rejected(with_value(record(), path, value), "hypotheses[0].statement")


@pytest.mark.parametrize("value", ["x", "x" * 300, "line\nbreak", "café 가설"])
def test_statement_has_no_character_or_length_restriction(value):
    validate(with_value(record(), ["hypotheses", 0, "statement"], value))


@pytest.mark.parametrize("name", ["basis", "expected", "tested_by"])
@pytest.mark.parametrize("value", [*NOT_ARRAYS, []])
def test_bad_hypothesis_array_is_rejected(name, value):
    path = ["hypotheses", 0, name]
    rejected(with_value(record(), path, value), f"hypotheses[0].{name}")


@pytest.mark.parametrize("value", [*NOT_OBJECTS, "case"])
def test_basis_entry_that_is_not_an_object_is_rejected(value):
    rejected(record(entry(basis=[value])), "hypotheses[0].basis[0]")


def test_basis_without_kind_is_rejected():
    basis = attempt_basis()
    del basis["kind"]
    message = rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].kind")
    assert "required member is missing" in message


@pytest.mark.parametrize("kind", ["paper", "injected", "", None, 1, ["attempt"]])
def test_basis_kind_not_admitted_is_rejected(kind):
    basis = {**attempt_basis(), "kind": kind}
    rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].kind")


def test_case_basis_with_a_reference_member_is_rejected():
    basis = {"kind": "case", "case": "synthetic", "text": "stored case"}
    rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].case")


@pytest.mark.parametrize(
    ("build", "name"),
    [
        (attempt_basis, "ref"),
        (attempt_basis, "text"),
        (external_basis, "source"),
        (external_basis, "version"),
        (external_basis, "text"),
    ],
)
def test_missing_basis_member_is_rejected(build, name):
    basis = build()
    del basis[name]
    path = f"hypotheses[0].basis[0].{name}"
    assert "required member is missing" in rejected(record(entry(basis=[basis])), path)


@pytest.mark.parametrize(
    ("build", "name"),
    [
        (attempt_basis, "source"),
        (attempt_basis, "extra"),
        (external_basis, "ref"),
        (external_basis, "extra"),
    ],
)
def test_unknown_basis_member_is_rejected(build, name):
    basis = {**build(), name: "x"}
    message = rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0]")
    assert "unknown member" in message


@pytest.mark.parametrize("build", [attempt_basis, external_basis])
@pytest.mark.parametrize("value", BAD_TEXTS)
def test_bad_basis_text_is_rejected(build, value):
    basis = {**build(), "text": value}
    rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].text")


@pytest.mark.parametrize("name", ["source", "version"])
@pytest.mark.parametrize("value", BAD_STRINGS)
def test_bad_external_string_is_rejected(name, value):
    basis = {**external_basis(), name: value}
    rejected(record(entry(basis=[basis])), f"hypotheses[0].basis[0].{name}")


@pytest.mark.parametrize("name", ["source", "version"])
@pytest.mark.parametrize("value", ["s", "s" * 255, " ~"])
def test_external_string_at_its_limits_is_valid(name, value):
    validate(record(entry(basis=[{**external_basis(), name: value}])))


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_ref_that_is_not_an_object_is_rejected(value):
    basis = {**attempt_basis(), "ref": value}
    rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].ref")


@pytest.mark.parametrize("name", ["round", "candidate", "attempt"])
def test_missing_ref_member_is_rejected(name):
    basis = attempt_basis()
    del basis["ref"][name]
    path = f"hypotheses[0].basis[0].ref.{name}"
    assert "required member is missing" in rejected(record(entry(basis=[basis])), path)


def test_unknown_ref_member_is_rejected():
    basis = attempt_basis()
    basis["ref"]["run_id"] = "other"
    message = rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].ref")
    assert "unknown member" in message


@pytest.mark.parametrize("value", BAD_INTEGERS)
def test_bad_ref_round_is_rejected(value):
    basis = attempt_basis()
    basis["ref"]["round"] = value
    rejected(record(entry(basis=[basis])), "hypotheses[0].basis[0].ref.round")


@pytest.mark.parametrize("name", ["candidate", "attempt"])
@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_ref_candidate_or_attempt_is_rejected(name, value):
    basis = attempt_basis()
    basis["ref"][name] = value
    rejected(record(entry(basis=[basis])), f"hypotheses[0].basis[0].ref.{name}")


@pytest.mark.parametrize("value", [3, 4, 2**53 - 1])
def test_ref_round_not_lower_than_the_round_is_rejected(value):
    document = record(entry(basis=[attempt_basis(round=value)]), round=3)
    message = rejected(document, "hypotheses[0].basis[0].ref.round")
    assert "lower than round (3)" in message


def test_ref_round_just_below_the_round_is_valid():
    validate(record(entry(basis=[attempt_basis(round=2)]), round=3))


def test_later_bad_basis_entry_is_reported_with_its_index():
    basis = [attempt_basis(), {**external_basis(), "kind": "paper"}]
    rejected(record(entry(basis=basis)), "hypotheses[0].basis[1].kind")


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_expected_entry_that_is_not_an_object_is_rejected(value):
    path = ["hypotheses", 0, "expected", 0]
    rejected(with_value(record(), path, value), "hypotheses[0].expected[0]")


@pytest.mark.parametrize("name", ["metric", "direction"])
def test_missing_expected_member_is_rejected(name):
    path = ["hypotheses", 0, "expected", 0, name]
    expected = f"hypotheses[0].expected[0].{name}"
    assert "required member is missing" in rejected(
        with_value(record(), path, REMOVE), expected
    )


@pytest.mark.parametrize("name", ["magnitude", "against", 1])
def test_unknown_expected_member_is_rejected(name):
    path = ["hypotheses", 0, "expected", 0, name]
    message = rejected(with_value(record(), path, 1), "hypotheses[0].expected[0]")
    assert "unknown member" in message


@pytest.mark.parametrize(
    "value",
    ["memory_ceiling", "latency", "throughput", "", None, 1, ["latency_minimisation"]],
)
def test_metric_not_admitted_is_rejected(value):
    path = ["hypotheses", 0, "expected", 0, "metric"]
    rejected(with_value(record(), path, value), "hypotheses[0].expected[0].metric")


@pytest.mark.parametrize("value", ["better", "worse", "Lower", "", None, 1, True])
def test_bad_direction_is_rejected(value):
    path = ["hypotheses", 0, "expected", 0, "direction"]
    rejected(with_value(record(), path, value), "hypotheses[0].expected[0].direction")


def test_duplicate_metric_is_rejected():
    document = record()
    expected = document["hypotheses"][0]["expected"]
    expected.append({"metric": "latency_minimisation", "direction": "higher"})
    message = rejected(document, "hypotheses[0].expected[1].metric")
    assert "unique" in message


@pytest.mark.parametrize("value", ["case", "System", "", None, 1])
def test_origin_not_admitted_is_rejected(value):
    path = ["hypotheses", 0, "origin"]
    rejected(with_value(record(), path, value), "hypotheses[0].origin")


@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_tested_by_value_is_rejected(value):
    path = ["hypotheses", 0, "tested_by"]
    rejected(with_value(record(), path, [value]), "hypotheses[0].tested_by[0]")


def test_duplicate_tested_by_value_is_rejected():
    document = record(entry(tested_by=[1, 2, 1]), candidates=2)
    message = rejected(document, "hypotheses[0].tested_by[2]")
    assert "unique" in message


@pytest.mark.parametrize("value", [3, 2**53 - 1])
def test_tested_by_value_above_candidates_is_rejected(value):
    document = record(entry(tested_by=[1, value]), candidates=2)
    message = rejected(document, "hypotheses[0].tested_by[1]")
    assert "at most candidates (2)" in message


def test_tested_by_value_equal_to_candidates_is_valid():
    validate(record(entry(tested_by=[1, 2, 3]), candidates=3))


@pytest.mark.parametrize(
    ("entries", "candidates", "missing"),
    [
        ([entry("h1", [1])], 2, 2),
        ([entry("h1", [2])], 2, 1),
        ([entry("h1", [1]), entry("h2", [3])], 3, 2),
        ([entry("h1", [1])], 2**53 - 1, 2),
    ],
)
def test_candidate_tested_by_no_hypothesis_is_rejected(entries, candidates, missing):
    message = rejected(record(*entries, candidates=candidates), "hypotheses")
    assert f"candidate {missing} is in the tested_by of no entry" in message


def test_first_rule_broken_is_reported():
    document = record(entry("h1"), entry("h1", tested_by=[5]))
    rejected(document, "hypotheses[1].tested_by[0]")


# The example of ADR-0073 (Example), copied from the record.
ADR_0073_EXAMPLE = json.loads(
    """
{
  "schema_version": 1, "run_id": "20261020t093000z-0f1e2d3c4b5a6978", "round": 1, "candidates": 1,
  "cases_read": [{"run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1}],
  "hypotheses": [
    {"id": "h1", "statement": "NOT-DECIDED-HERE",
     "basis": [
       {"kind": "case", "case": {"run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1, "hypothesis": "h1"}, "text": "NOT-DECIDED-HERE"},
       {"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}],
     "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
     "origin": "system", "tested_by": [1]}
  ]
}
"""
)

OWN_RUN = "synthetic-run_01"
OTHER_RUN = "other-run_02"


def case_basis(run_id=OTHER_RUN, round=1, hypothesis="h1", text="stored case"):
    case = {"run_id": run_id, "round": round, "hypothesis": hypothesis}
    return {"kind": "case", "case": case, "text": text}


def read_entry(run_id=OTHER_RUN, round=1):
    return {"run_id": run_id, "round": round}


def with_cases(*read, basis=None):
    document = record(entry(basis=basis if basis is not None else [case_basis()]))
    document["cases_read"] = list(read)
    return document


def test_adr_0073_example_is_valid():
    assert validate(ADR_0073_EXAMPLE) is None


def test_adr_0073_example_is_not_modified():
    before = copy.deepcopy(ADR_0073_EXAMPLE)
    validate(ADR_0073_EXAMPLE)
    assert before == ADR_0073_EXAMPLE


def test_empty_cases_read_without_case_entry_is_valid():
    validate(with_cases(basis=[attempt_basis()]))


def test_absent_cases_read_without_case_entry_is_valid():
    assert "cases_read" not in record()
    validate(record())


def test_cases_read_none_of_which_is_rested_on_is_valid():
    read = [read_entry(), read_entry("third-run", 4)]
    validate(with_cases(*read, basis=[attempt_basis(), external_basis()]))


def test_cases_read_beyond_the_rested_on_cases_is_valid():
    validate(with_cases(read_entry(), read_entry("third-run", 4)))


def test_cases_read_order_is_not_checked():
    validate(with_cases(read_entry("zz-run"), read_entry("aa-run", 2), read_entry()))


def test_same_run_with_different_rounds_is_no_duplicate():
    basis = [case_basis(round=1), case_basis(round=2, hypothesis="h9")]
    validate(with_cases(read_entry(round=1), read_entry(round=2), basis=basis))


def test_case_entry_of_any_stored_hypothesis_id_is_valid():
    validate(with_cases(read_entry(), basis=[case_basis(hypothesis="refuted_h7")]))


def test_two_case_entries_on_one_case_are_valid():
    basis = [case_basis(), case_basis(hypothesis="h2", text="another")]
    validate(with_cases(read_entry(), basis=basis))


def test_case_entry_bounds_are_valid():
    top = hypotheses.keys.MAX_INTEGER
    basis = [case_basis(run_id="s" * 255, round=top, hypothesis="h" * 32)]
    validate(with_cases(read_entry("s" * 255, top), basis=basis))


def test_read_only_case_mappings_are_accepted():
    basis = case_basis()
    basis["case"] = MappingProxyType(basis["case"])
    read = MappingProxyType(read_entry())
    document = with_cases(read, basis=[MappingProxyType(basis)])
    validate(MappingProxyType(document))


@pytest.mark.parametrize("value", NOT_ARRAYS)
def test_cases_read_that_is_not_an_array_is_rejected(value):
    document = {**record(), "cases_read": value}
    assert "must be an array" in rejected(document, "cases_read")


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_cases_read_entry_that_is_not_an_object_is_rejected(value):
    rejected(with_cases(value, basis=[attempt_basis()]), "cases_read[0]")


@pytest.mark.parametrize("name", ["run_id", "round"])
def test_missing_cases_read_member_is_rejected(name):
    read = read_entry()
    del read[name]
    document = with_cases(read, basis=[attempt_basis()])
    message = rejected(document, f"cases_read[0].{name}")
    assert "required member is missing" in message


@pytest.mark.parametrize("name", ["hypothesis", "extra", 1])
def test_unknown_cases_read_member_is_rejected(name):
    document = with_cases({**read_entry(), name: "x"}, basis=[attempt_basis()])
    assert "unknown member" in rejected(document, "cases_read[0]")


@pytest.mark.parametrize("value", BAD_STRINGS)
def test_bad_cases_read_run_id_is_rejected(value):
    document = with_cases(read_entry(run_id=value), basis=[attempt_basis()])
    rejected(document, "cases_read[0].run_id")


@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_cases_read_round_is_rejected(value):
    document = with_cases(read_entry(round=value), basis=[attempt_basis()])
    rejected(document, "cases_read[0].round")


def test_cases_read_entry_of_the_own_run_is_rejected():
    read = [read_entry(), read_entry(run_id=OWN_RUN)]
    message = rejected(with_cases(*read), "cases_read[1].run_id")
    assert f"other than run_id ({OWN_RUN})" in message


def test_duplicate_cases_read_entry_is_rejected():
    read = [read_entry(), read_entry("third-run", 4), read_entry()]
    message = rejected(with_cases(*read), "cases_read[2]")
    assert "unique in the array" in message


@pytest.mark.parametrize("name", ["case", "text"])
def test_missing_case_basis_member_is_rejected(name):
    basis = case_basis()
    del basis[name]
    document = with_cases(read_entry(), basis=[basis])
    message = rejected(document, f"hypotheses[0].basis[0].{name}")
    assert "required member is missing" in message


@pytest.mark.parametrize("name", ["ref", "source", "extra"])
def test_unknown_case_basis_member_is_rejected(name):
    document = with_cases(read_entry(), basis=[{**case_basis(), name: "x"}])
    assert "unknown member" in rejected(document, "hypotheses[0].basis[0]")


@pytest.mark.parametrize("value", BAD_TEXTS)
def test_bad_case_basis_text_is_rejected(value):
    document = with_cases(read_entry(), basis=[{**case_basis(), "text": value}])
    rejected(document, "hypotheses[0].basis[0].text")


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_case_member_that_is_not_an_object_is_rejected(value):
    document = with_cases(read_entry(), basis=[{**case_basis(), "case": value}])
    assert "must be an object" in rejected(document, "hypotheses[0].basis[0].case")


@pytest.mark.parametrize("name", ["run_id", "round", "hypothesis"])
def test_missing_case_member_is_rejected(name):
    basis = case_basis()
    del basis["case"][name]
    document = with_cases(read_entry(), basis=[basis])
    message = rejected(document, f"hypotheses[0].basis[0].case.{name}")
    assert "required member is missing" in message


@pytest.mark.parametrize("name", ["id", "candidate", "extra"])
def test_unknown_case_member_is_rejected(name):
    basis = case_basis()
    basis["case"][name] = 1
    document = with_cases(read_entry(), basis=[basis])
    assert "unknown member" in rejected(document, "hypotheses[0].basis[0].case")


@pytest.mark.parametrize("value", BAD_STRINGS)
def test_bad_case_run_id_is_rejected(value):
    document = with_cases(read_entry(), basis=[case_basis(run_id=value)])
    rejected(document, "hypotheses[0].basis[0].case.run_id")


@pytest.mark.parametrize("value", BAD_POSITIVE_INTEGERS)
def test_bad_case_round_is_rejected(value):
    document = with_cases(read_entry(), basis=[case_basis(round=value)])
    rejected(document, "hypotheses[0].basis[0].case.round")


@pytest.mark.parametrize("value", BAD_NAMES)
def test_bad_case_hypothesis_is_rejected(value):
    document = with_cases(read_entry(), basis=[case_basis(hypothesis=value)])
    rejected(document, "hypotheses[0].basis[0].case.hypothesis")


def test_case_entry_of_the_own_run_is_rejected():
    document = with_cases(read_entry(), basis=[case_basis(run_id=OWN_RUN)])
    message = rejected(document, "hypotheses[0].basis[0].case.run_id")
    assert f"other than run_id ({OWN_RUN})" in message


@pytest.mark.parametrize(
    "read",
    [
        [],
        [read_entry(round=2)],
        [read_entry(run_id="third-run")],
        [read_entry(run_id="third-run", round=2), read_entry(round=3)],
    ],
)
def test_case_entry_not_in_cases_read_is_rejected(read):
    message = rejected(with_cases(*read), "hypotheses[0].basis[0].case")
    assert "no entry of cases_read" in message


def test_case_entry_without_cases_read_is_rejected():
    document = record(entry(basis=[case_basis()]))
    message = rejected(document, "hypotheses[0].basis[0].case")
    assert "no entry of cases_read" in message


def test_case_entry_of_a_later_hypothesis_is_reported_with_its_index():
    document = with_cases(read_entry(), basis=[attempt_basis()])
    document["candidates"] = 2
    basis = [external_basis(), case_basis(round=5)]
    document["hypotheses"].append(entry("h2", tested_by=(2,), basis=basis))
    rejected(document, "hypotheses[1].basis[1].case")


def test_cases_read_is_checked_before_the_hypotheses():
    basis = [case_basis(hypothesis="Bad")]
    rejected(with_cases(read_entry(round=0), basis=basis), "cases_read[0].round")


def test_cases_read_is_checked_after_the_top_level_members():
    document = {**with_cases(read_entry(round=0)), "candidates": 0}
    rejected(document, "candidates")


def test_cases_read_entries_are_checked_before_their_uniqueness():
    read = [read_entry(), read_entry(), read_entry(round=0)]
    rejected(with_cases(*read), "cases_read[2].round")


def test_case_form_is_checked_before_its_in_file_rules():
    basis = [case_basis(run_id=OWN_RUN, hypothesis="Bad")]
    rejected(record(entry(basis=basis)), "hypotheses[0].basis[0].case.hypothesis")


def test_case_own_run_is_checked_before_cases_read_membership():
    basis = [case_basis(run_id=OWN_RUN)]
    rejected(record(entry(basis=basis)), "hypotheses[0].basis[0].case.run_id")


def test_injected_origin_without_injection_is_rejected_with_cases_read():
    document = with_cases(read_entry())
    document["hypotheses"][0]["origin"] = "injected"
    message = rejected(document, "hypotheses[0].injection")
    assert message == "hypotheses[0].injection: required member is missing"


# The round-1 hypotheses.json of the example of ADR-0075 (Example), copied from the record.
ADR_0075_EXAMPLE = json.loads(
    """
{
  "schema_version": 1, "run_id": "20261021t080000z-3c5e7a9b1d2f4608", "round": 1, "candidates": 2,
  "hypotheses": [
    {"id": "h1", "statement": "SYNTHETIC: blocking the inner loop lowers the kernel time",
     "basis": [{"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}],
     "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
     "origin": "injected", "injection": "u1", "tested_by": [1]},
    {"id": "h2", "statement": "NOT-DECIDED-HERE",
     "basis": [{"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}],
     "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
     "origin": "system", "tested_by": [2]}
  ]
}
"""
)


def injected(ident="h1", injection="u1", **changes):
    made = {**entry(ident, **changes), "origin": "injected", "injection": injection}
    return made


def test_adr_0075_example_is_valid():
    before = copy.deepcopy(ADR_0075_EXAMPLE)
    assert validate(ADR_0075_EXAMPLE) is None
    assert before == ADR_0075_EXAMPLE


def test_injected_entry_has_the_six_members_and_injection():
    assert sorted(injected()) == sorted([*ADR_HYPOTHESIS, "injection"])
    validate(record(injected()))


def test_injected_entry_with_an_external_basis_is_valid():
    validate(record(injected(basis=[external_basis()])))


def test_injected_entry_with_a_case_basis_is_valid_with_cases_read():
    document = record(injected(basis=[case_basis()]))
    document["cases_read"] = [read_entry()]
    validate(document)


def test_two_entries_with_the_same_injection_are_valid():
    document = record(
        injected("h1", "u2", tested_by=(1,)),
        injected("h2", "u2", tested_by=(2,), basis=[external_basis()]),
        candidates=2,
    )
    validate(document)


def test_injection_names_no_input_that_is_checked():
    validate(record(injected(injection="never_injected")))


@pytest.mark.parametrize("value", ["u", "a" * 32, "u_1"])
def test_injection_at_the_limits_of_a_name_is_valid(value):
    validate(record(injected(injection=value)))


def test_injected_entry_without_injection_is_rejected():
    document = with_value(record(injected()), ["hypotheses", 0, "injection"], REMOVE)
    message = rejected(document, "hypotheses[0].injection")
    assert message == "hypotheses[0].injection: required member is missing"


def test_system_entry_with_injection_is_rejected():
    document = record({**entry(), "injection": "u1"})
    message = rejected(document, "hypotheses[0]")
    assert message == "hypotheses[0]: unknown member 'injection'"


@pytest.mark.parametrize("value", BAD_NAMES)
def test_bad_injection_is_rejected(value):
    rejected(record(injected(injection=value)), "hypotheses[0].injection")


@pytest.mark.parametrize("value", ["case", "System", "", None, 1])
def test_injection_beside_an_origin_not_admitted_is_unknown(value):
    document = record({**entry(), "origin": value, "injection": "u1"})
    message = rejected(document, "hypotheses[0]")
    assert message == "hypotheses[0]: unknown member 'injection'"


@pytest.mark.parametrize("value", ["case", "System", "", None, 1])
def test_origin_not_admitted_is_reported_without_injection(value):
    rejected(record({**entry(), "origin": value}), "hypotheses[0].origin")


def test_entry_without_origin_takes_the_member_set_of_system():
    document = record(injected())
    del document["hypotheses"][0]["origin"]
    message = rejected(document, "hypotheses[0]")
    assert message == "hypotheses[0]: unknown member 'injection'"
    del document["hypotheses"][0]["injection"]
    message = rejected(document, "hypotheses[0].origin")
    assert message == "hypotheses[0].origin: required member is missing"


def test_injected_entry_breaking_basis_reports_the_basis_first():
    document = record(injected(injection="Bad", basis=[]))
    rejected(document, "hypotheses[0].basis")


def test_injected_entry_breaking_its_id_reports_the_id_first():
    rejected(record(injected("Bad", injection="Bad")), "hypotheses[0].id")


def test_injected_entry_breaking_tested_by_reports_the_injection_first():
    document = record(injected(injection="Bad", tested_by=(5,)))
    rejected(document, "hypotheses[0].injection")


def test_injected_entries_are_bound_by_id_uniqueness():
    document = record(injected("h1"), injected("h1", tested_by=(2,)), candidates=2)
    message = rejected(document, "hypotheses[1].id")
    assert "unique" in message


def test_injected_entries_are_bound_by_the_candidate_cover():
    document = record(injected(), candidates=2)
    rejected(document, "hypotheses")
