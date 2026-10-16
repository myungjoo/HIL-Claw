import copy
import json
import os

import pytest

from hilclaw import (
    case_lookup,
    cases,
    cases_file,
    instance,
    instance_file,
    key_records,
    keys,
    layout,
)
from hilclaw.case_lookup import Found
from hilclaw.hypotheses import InvalidHypothesisRecordError
from hilclaw.hypotheses_cases import MismatchError, check, check_run

READER = "20261020t093000z-0f1e2d3c4b5a6978"
OTHER_A = "20261009t012331z-9f3a6c1e0b7d4a52"
OTHER_B = "20261001t000000z-0000000000000001"
PLACEHOLDER = "NOT-DECIDED-HERE"


def hw():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_hw",
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }


def op():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }


HW_KEY = keys.hw_profile_key(hw())
OP_KEY = keys.op_signature_key(op())


def ref(round):
    return {"round": round, "candidate": 1, "attempt": 1}


def hypothesis(ident, candidate, basis=None):
    return {
        "id": ident,
        "statement": PLACEHOLDER,
        "basis": basis or [{"kind": "attempt", "ref": ref(0), "text": PLACEHOLDER}],
        "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
        "origin": "system",
        "tested_by": [candidate],
    }


def hypothesis_record(run_id, round, ids=("h1",)):
    return {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "candidates": len(ids),
        "hypotheses": [hypothesis(ident, at + 1) for at, ident in enumerate(ids)],
    }


def verdict_record(run_id, round, value="inconclusive"):
    evidence = [
        {"kind": "check", "ref": ref(round), "point": "board", "outcome": "pass"}
    ]
    if value == "refuted":
        evidence.append(
            {"kind": "check", "ref": ref(0), "point": "board", "outcome": "pass"}
        )
        evidence.append(
            {
                "kind": "comparison",
                "metric": "latency_minimisation",
                "point": "board",
                "measured": ref(round),
                "against": ref(0),
                "difference": "higher",
            }
        )
    return {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "verdicts": [
            {
                "hypothesis": "h1",
                "verdict": value,
                "cause": PLACEHOLDER,
                "evidence": evidence,
            }
        ],
    }


def case_entry(run_id, round, ident):
    return {
        "kind": "case",
        "case": {"run_id": run_id, "round": round, "hypothesis": ident},
        "text": PLACEHOLDER,
    }


def reader_record(read, rested=()):
    """The hypothesis record of round 1 of READER, in the form of the ADR-0073 Example."""
    document = hypothesis_record(READER, 1)
    if read is not None:
        document["cases_read"] = [{"run_id": r, "round": n} for r, n in read]
    document["hypotheses"][0]["basis"] = [case_entry(*item) for item in rested] + [
        {"kind": "attempt", "ref": ref(0), "text": PLACEHOLDER}
    ]
    return document


def case(run_id, round, ids=("h1",), verdict="inconclusive"):
    verdicts = verdict_record(run_id, round, verdict) if verdict else None
    return cases.build(hypothesis_record(run_id, round, ids), verdicts)


def written(document):
    return json.dumps(document, indent=2).encode() + b"\n"


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


@pytest.fixture
def key_dir(root):
    key_records.store_hw_profile(root, hw())
    key_records.store_op_signature(root, HW_KEY.name, op())
    return layout.op_signature_dir(root, HW_KEY.name, OP_KEY.name)


def store(root, document):
    cases_file.write(root, HW_KEY.name, OP_KEY.name, written(document))
    return document


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def case_path(root, run_id, round):
    return layout.case_record(root, HW_KEY.name, OP_KEY.name, run_id, round)


def write_instance(root, run_id, with_op=True):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": HW_KEY.name, "record": hw()},
    }
    if with_op:
        document["op_signature"] = {"key": OP_KEY.name, "record": op()}
    instance_file.write(root, run_id, written(document))


@pytest.fixture
def two_cases(root, key_dir):
    store(root, case(OTHER_A, 1, ids=("h1", "h2"), verdict=None))
    store(root, case(OTHER_B, 2, verdict=None))
    write_instance(root, READER)


def found_of(*documents):
    return Found(None, tuple(documents), ())


def test_mismatch_error_is_a_value_error():
    assert issubclass(MismatchError, ValueError)


def test_a_record_naming_two_stored_cases_passes(root, two_cases):
    document = reader_record(
        [(OTHER_A, 1), (OTHER_B, 2)], [(OTHER_A, 1, "h2"), (OTHER_B, 2, "h1")]
    )
    found = case_lookup.lookup(root, READER)

    assert check(document, found) is None
    assert check_run(root, document) == found
    assert len(found.cases) == 2


def test_a_record_naming_some_of_the_cases_passes(root, two_cases):
    document = reader_record([(OTHER_B, 2)], [(OTHER_B, 2, "h1")])

    assert check_run(root, document) == case_lookup.lookup(root, READER)


@pytest.mark.parametrize("verdict", ["refuted", None])
def test_a_case_entry_passes_whatever_the_verdict_of_the_case(verdict):
    stored = case(OTHER_A, 1, verdict=verdict)
    document = reader_record([(OTHER_A, 1)], [(OTHER_A, 1, "h1")])

    check(document, found_of(stored))


@pytest.mark.parametrize("stored", [(), (OTHER_A,)])
def test_a_record_without_cases_read_passes_against_any_found(stored):
    check(reader_record(None), found_of(*(case(run_id, 1) for run_id in stored)))


def test_an_empty_cases_read_passes_against_an_empty_found():
    check(reader_record([]), Found(None, (), ()))


@pytest.mark.parametrize("with_op", [True, False])
def test_check_run_passes_an_empty_cases_read_without_a_case(root, with_op):
    write_instance(root, READER, with_op=with_op)

    assert check_run(root, reader_record([])) == Found(None, (), ())


def test_check_run_on_a_key_without_valid_cases_of_another_run(root, key_dir):
    store(root, case(READER, 1))
    write_instance(root, READER)

    found = check_run(root, reader_record([]))
    assert found.key is not None and found.cases == ()


def test_a_case_not_stored_breaks_cases_read(root, two_cases):
    document = reader_record([(OTHER_A, 1), (OTHER_A, 3)])

    with pytest.raises(MismatchError, match=r"^cases_read\[1\]: .*valid case"):
        check_run(root, document)


def stored_aside(root, key_dir, how):
    if how == "invalid":
        place(case_path(root, OTHER_B, 2), b"{not json")
    elif how == "set_apart":
        document = case(OTHER_B, 2)
        document["schema_version"] = 2
        place(case_path(root, OTHER_B, 2), written(document))
    else:
        case_path(root, OTHER_B, 2).mkdir()


@pytest.mark.parametrize("how", ["invalid", "set_apart", "directory"])
def test_a_reported_case_breaks_cases_read(root, key_dir, how):
    store(root, case(OTHER_A, 1))
    stored_aside(root, key_dir, how)
    write_instance(root, READER)
    document = reader_record([(OTHER_A, 1), (OTHER_B, 2)], [(OTHER_B, 2, "h1")])

    with pytest.raises(MismatchError, match=r"^cases_read\[1\]: "):
        check_run(root, document)
    assert len(case_lookup.lookup(root, READER).reports) == 1


def test_any_cases_read_breaks_against_an_empty_found():
    with pytest.raises(MismatchError, match=r"^cases_read\[0\]: "):
        check(reader_record([(OTHER_A, 1)]), Found(None, (), ()))


def test_a_case_entry_naming_no_stored_hypothesis_breaks(root, two_cases):
    document = reader_record(
        [(OTHER_A, 1), (OTHER_B, 2)], [(OTHER_A, 1, "h1"), (OTHER_B, 2, "h2")]
    )

    with pytest.raises(
        MismatchError,
        match=r"^hypotheses\[0\]\.basis\[1\]\.case\.hypothesis: .*'h1'.*got 'h2'",
    ):
        check_run(root, document)


def test_the_case_entries_of_a_later_hypothesis_are_checked():
    document = reader_record([(OTHER_A, 1)])
    document["candidates"] = 2
    document["hypotheses"].append(hypothesis("h2", 2, [case_entry(OTHER_A, 1, "h9")]))

    with pytest.raises(MismatchError, match=r"^hypotheses\[1\]\.basis\[0\]\."):
        check(document, found_of(case(OTHER_A, 1)))


def test_the_first_broken_rule_is_reported():
    document = reader_record([(OTHER_A, 1), (OTHER_B, 2)], [(OTHER_A, 1, "h9")])

    with pytest.raises(MismatchError, match=r"^cases_read\[1\]: "):
        check(document, found_of(case(OTHER_A, 1)))


@pytest.mark.parametrize("value", [None, (), {"cases": ()}, (None, (), ())])
def test_check_refuses_a_found_that_is_no_found(value):
    with pytest.raises(TypeError, match="must be a Found"):
        check(reader_record(None), value)


def test_check_refuses_the_found_before_the_record():
    with pytest.raises(TypeError):
        check({}, None)


def test_check_refuses_an_invalid_record():
    document = reader_record([(OTHER_A, 1)], [(OTHER_B, 2, "h1")])

    with pytest.raises(InvalidHypothesisRecordError):
        check(document, found_of(case(OTHER_A, 1), case(OTHER_B, 2)))


def test_check_run_refuses_an_invalid_record_before_reading(tmp_path, monkeypatch):
    def refused(*args):
        raise AssertionError("no file may be read")

    monkeypatch.setattr(case_lookup, "lookup", refused)
    with pytest.raises(InvalidHypothesisRecordError):
        check_run(tmp_path / "absent", {"schema_version": 1})


def test_check_run_passes_on_a_missing_instance(root):
    with pytest.raises(instance.MissingInstanceError):
        check_run(root, reader_record([]))


def test_check_run_passes_on_a_missing_data_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        check_run(tmp_path / "absent", reader_record([]))


def test_check_run_passes_on_a_data_root_that_is_a_file(tmp_path):
    with pytest.raises(NotADirectoryError):
        check_run(place(tmp_path / "file", b""), reader_record([]))


def test_check_run_passes_on_a_bad_run_id(root):
    document = reader_record([])
    document["run_id"] = "Bad"

    with pytest.raises(layout.InvalidPathValueError):
        check_run(root, document)


def test_neither_argument_is_modified(root, two_cases):
    document = reader_record([(OTHER_A, 1)], [(OTHER_A, 1, "h2")])
    found = case_lookup.lookup(root, READER)
    before = copy.deepcopy((document, found))

    check(document, found)
    check_run(root, document)

    assert (document, found) == before


def test_check_run_writes_nothing(root, two_cases):
    names = sorted(os.listdir(root / "db" / HW_KEY.name / OP_KEY.name))

    check_run(root, reader_record([(OTHER_A, 1)]))

    assert sorted(os.listdir(root / "db" / HW_KEY.name / OP_KEY.name)) == names
