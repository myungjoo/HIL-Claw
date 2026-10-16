import json
import os
from pathlib import Path

import pytest

from hilclaw import (
    case_lookup,
    cases,
    cases_file,
    hypotheses,
    instance,
    instance_file,
    key_records,
    keys,
    layout,
)
from hilclaw.case_lookup import Found, Report, cases_read, find, lookup

READER = "20261020t093000z-0f1e2d3c4b5a6978"
OTHER_A = "20261009t012331z-9f3a6c1e0b7d4a52"
OTHER_B = "20261001t000000z-0000000000000001"
PLACEHOLDER = "NOT-DECIDED-HERE"


def hw(**changes):
    record = {
        "schema_version": 1,
        "accelerator": "synthetic_hw",
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    record.update(changes)
    return record


def op(**changes):
    record = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }
    record.update(changes)
    return record


HW_KEY = keys.hw_profile_key(hw())
OP_KEY = keys.op_signature_key(op())


def ref(round):
    return {"round": round, "candidate": 1, "attempt": 1}


def hypothesis_record(run_id, round):
    return {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "candidates": 1,
        "hypotheses": [
            {
                "id": "h1",
                "statement": PLACEHOLDER,
                "basis": [{"kind": "attempt", "ref": ref(0), "text": PLACEHOLDER}],
                "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
                "origin": "system",
                "tested_by": [1],
            }
        ],
    }


def verdict_record(run_id, round):
    return {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "verdicts": [
            {
                "hypothesis": "h1",
                "verdict": "inconclusive",
                "cause": PLACEHOLDER,
                "evidence": [
                    {
                        "kind": "check",
                        "ref": ref(round),
                        "point": "board",
                        "outcome": "pass",
                    }
                ],
            }
        ],
    }


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


def store_case(root, run_id, round, verdicts=True, **extra):
    document = cases.build(
        hypothesis_record(run_id, round),
        verdict_record(run_id, round) if verdicts else None,
    )
    document.update(extra)
    cases_file.write(root, HW_KEY.name, OP_KEY.name, written(document))
    return document


def case_name(run_id, round):
    return f"case-{run_id}-{round:04d}.json"


def relative(root, path):
    return Path(path).relative_to(root).as_posix()


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def write_instance(root, run_id, with_op=True):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": HW_KEY.name, "record": hw()},
    }
    if with_op:
        document["op_signature"] = {"key": OP_KEY.name, "record": op()}
    instance_file.write(root, run_id, written(document))


@pytest.fixture
def read_paths(monkeypatch):
    seen = []
    original = Path.read_bytes

    def tracked(self):
        seen.append(self.name)
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", tracked)
    return seen


def test_find_returns_the_cases_of_other_runs_in_byte_order_of_names(root, key_dir):
    own = store_case(root, READER, 1)
    a = store_case(root, OTHER_A, 2, synthetic_extra={"kept": [1, 2]})
    b = store_case(root, OTHER_B, 3, verdicts=False)

    result = find(root, hw(), op(), READER)

    assert result == Found((HW_KEY, OP_KEY), (b, a), ())
    assert result.cases[1]["synthetic_extra"] == {"kept": [1, 2]}
    assert "verdict_record" not in result.cases[0]
    assert own not in result.cases
    for document in result.cases:
        name = case_name(document["run_id"], document["round"])
        assert document == cases_file.parse((key_dir / name).read_bytes())


def test_cases_read_gives_the_entries_a_hypothesis_record_accepts(root, key_dir):
    store_case(root, OTHER_A, 1)
    store_case(root, OTHER_B, 2)

    result = find(root, hw(), op(), READER)
    entries = cases_read(result)

    assert entries == [
        {"run_id": OTHER_B, "round": 2},
        {"run_id": OTHER_A, "round": 1},
    ]
    assert cases_read(result) is not entries
    document = hypothesis_record(READER, 1)
    document["cases_read"] = entries
    document["hypotheses"][0]["basis"].append(
        {
            "kind": "case",
            "case": {"run_id": OTHER_A, "round": 1, "hypothesis": "h1"},
            "text": PLACEHOLDER,
        }
    )
    hypotheses.validate(document)


def test_cases_read_is_empty_for_no_case():
    assert cases_read(Found(None, (), ())) == []


@pytest.mark.parametrize("value", [None, (), {"cases": ()}, (None, (), ())])
def test_cases_read_refuses_a_value_that_is_no_found(value):
    with pytest.raises(TypeError, match="must be a Found"):
        cases_read(value)


def test_lookup_reads_the_records_of_the_instance(root, key_dir):
    store_case(root, OTHER_A, 1)
    store_case(root, READER, 1)
    write_instance(root, READER)

    result = lookup(root, READER)

    assert result == find(root, hw(), op(), READER)
    assert [case["run_id"] for case in result.cases] == [OTHER_A]


def test_lookup_of_an_instance_without_op_signature_reads_nothing_below_db(
    root, read_paths
):
    write_instance(root, READER, with_op=False)

    assert lookup(root, READER) == Found(None, (), ())
    assert read_paths == ["instance.json"]
    assert not (root / "db").exists()


def test_find_without_op_signature_reads_no_file(root, key_dir, read_paths):
    store_case(root, OTHER_A, 1)

    assert find(root, hw(), None, READER) == Found(None, (), ())
    assert read_paths == []


def test_find_without_db_is_a_miss(root):
    assert find(root, hw(), op(), READER) == Found(None, (), ())


def test_find_without_hw_profile_record_is_a_miss(root, read_paths):
    place(
        layout.case_record(root, HW_KEY.name, OP_KEY.name, OTHER_A, 1),
        written(cases.build(hypothesis_record(OTHER_A, 1))),
    )

    assert find(root, hw(), op(), READER) == Found(None, (), ())
    assert read_paths == []


def test_find_without_op_signature_record_is_a_miss(root, monkeypatch, read_paths):
    key_records.store_hw_profile(root, hw())
    place(
        layout.case_record(root, HW_KEY.name, OP_KEY.name, OTHER_A, 1),
        written(cases.build(hypothesis_record(OTHER_A, 1))),
    )

    def listed(path):
        raise AssertionError(f"listed {path}")

    monkeypatch.setattr(os, "listdir", listed)

    assert find(root, hw(), op(), READER) == Found(None, (), ())
    assert read_paths == ["hw_profile.json"]


def test_find_on_an_empty_key_directory_gives_the_key_and_nothing_else(root, key_dir):
    assert find(root, hw(), op(), READER) == Found((HW_KEY, OP_KEY), (), ())


def test_find_leaves_out_cases_of_the_own_run_without_report(root, key_dir):
    store_case(root, READER, 1)
    store_case(root, READER, 2)

    assert find(root, hw(), op(), READER) == Found((HW_KEY, OP_KEY), (), ())


def test_find_reports_a_colliding_hw_profile_record(root, key_dir, read_paths):
    store_case(root, OTHER_A, 1)
    path = layout.hw_profile_record(root, HW_KEY.name)
    place(path, written(hw(accelerator="other_hw")))

    result = find(root, hw(), op(), READER)

    assert result.key is None
    assert result.cases == ()
    [report] = result.reports
    assert report.path == relative(root, path)
    assert report.kind == "key_record"
    assert "ADR-0001 decision 3" in report.reason
    assert all(not name.startswith("case-") for name in read_paths)


def test_find_reports_a_corrupt_op_signature_record(root, key_dir, read_paths):
    store_case(root, OTHER_A, 1)
    path = key_dir / "op_signature.json"
    path.write_bytes(b"{not json")

    result = find(root, hw(), op(), READER)

    assert result == Found(
        None,
        (),
        (Report(relative(root, path), "key_record", result.reports[0].reason),),
    )
    assert result.reports[0].reason.startswith(relative(root, path))
    assert all(not name.startswith("case-") for name in read_paths)


def test_find_reports_a_colliding_op_signature_record(root, key_dir):
    path = key_dir / "op_signature.json"
    path.write_bytes(written(op(dtype="other_dtype")))

    [report] = find(root, hw(), op(), READER).reports

    assert report.path == relative(root, path)
    assert report.kind == "key_record"


def test_find_reports_invalid_files_and_still_returns_the_others(root, key_dir):
    a = store_case(root, OTHER_A, 1)
    b = store_case(root, OTHER_B, 1)
    bad_json = place(key_dir / case_name(OTHER_A, 7), b"{not json")
    moved = place(
        key_dir / case_name(OTHER_B, 9),
        written(cases.build(hypothesis_record(OTHER_B, 2))),
    )
    misnamed = place(
        key_dir / "case-x.json", written(cases.build(hypothesis_record(OTHER_A, 3)))
    )
    directory = key_dir / "case-y.json"
    directory.mkdir()
    upper = place(
        key_dir / f"case-{OTHER_A.upper()}-0004.json",
        written(cases.build(hypothesis_record(OTHER_A.upper(), 4))),
    )

    result = find(root, hw(), op(), READER)

    assert result.cases == (b, a)
    kinds = {report.path: report.kind for report in result.reports}
    assert kinds == {
        relative(root, path): "invalid"
        for path in (bad_json, moved, misnamed, directory, upper)
    }
    paths = [report.path for report in result.reports]
    assert paths == sorted(paths, key=lambda path: path.encode())
    reasons = {report.path: report.reason for report in result.reports}
    assert "is not a regular file" in reasons[relative(root, directory)]
    assert "run_id and round" in reasons[relative(root, moved)]
    assert "cannot be read as one JSON text" in reasons[relative(root, bad_json)]
    assert "run_id" in reasons[relative(root, upper)]


def test_find_reports_a_symbolic_link_of_the_name_form(root, key_dir, tmp_path):
    store_case(root, OTHER_A, 1)
    target = place(
        tmp_path / "elsewhere.json", written(cases.build(hypothesis_record(OTHER_B, 1)))
    )
    link = key_dir / case_name(OTHER_B, 1)
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links are not available")

    result = find(root, hw(), op(), READER)

    assert [case["run_id"] for case in result.cases] == [OTHER_A]
    assert result.reports == (
        Report(relative(root, link), "invalid", "is not a regular file"),
    )


@pytest.mark.parametrize("copy", [None, "hypothesis_record", "verdict_record"])
def test_find_sets_apart_another_version(root, key_dir, copy):
    a = store_case(root, OTHER_A, 1)
    document = cases.build(hypothesis_record(OTHER_B, 1), verdict_record(OTHER_B, 1))
    if copy is None:
        document["schema_version"] = 2
    else:
        document[copy]["schema_version"] = 2
    path = place(key_dir / case_name(OTHER_B, 1), written(document))

    result = find(root, hw(), op(), READER)

    assert result.cases == (a,)
    [report] = result.reports
    assert (report.path, report.kind) == (relative(root, path), "set_apart")
    assert "schema_version" in report.reason


def test_find_reports_set_apart_and_invalid_files_of_the_own_run(root, key_dir):
    document = cases.build(hypothesis_record(READER, 1))
    document["schema_version"] = 2
    place(key_dir / case_name(READER, 1), written(document))
    place(key_dir / case_name(READER, 2), b"[]")

    result = find(root, hw(), op(), READER)

    assert result.cases == ()
    assert [report.kind for report in result.reports] == ["set_apart", "invalid"]


def test_find_reports_an_unreadable_file_and_reads_the_rest(root, key_dir, monkeypatch):
    a = store_case(root, OTHER_A, 1)
    store_case(root, OTHER_B, 1)
    original = Path.read_bytes

    def failing(self):
        if self.name == case_name(OTHER_B, 1):
            raise PermissionError(13, "synthetic denial", str(self))
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", failing)

    result = find(root, hw(), op(), READER)

    assert result.cases == (a,)
    [report] = result.reports
    assert report.path == relative(root, key_dir / case_name(OTHER_B, 1))
    assert report.kind == "unreadable"
    assert "synthetic denial" in report.reason


def test_find_reports_an_entry_whose_kind_cannot_be_taken(root, key_dir, monkeypatch):
    a = store_case(root, OTHER_A, 1)
    store_case(root, OTHER_B, 1)
    original = os.lstat

    def failing(path, *args, **kwargs):
        if Path(path).name == case_name(OTHER_B, 1):
            raise FileNotFoundError(2, "synthetic vanish", str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(case_lookup.os, "lstat", failing)

    result = find(root, hw(), op(), READER)

    assert result.cases == (a,)
    assert [report.kind for report in result.reports] == ["unreadable"]


def test_find_ignores_entries_not_of_the_name_form(root, key_dir, read_paths):
    a = store_case(root, OTHER_A, 1)
    valid = written(cases.build(hypothesis_record(OTHER_B, 1)))
    ignored = [
        f"{case_name(OTHER_B, 1)}.4242-0123456789abcdef.tmp",
        "case-x.txt",
        f"notcase-{OTHER_B}-0001.json",
        "Case-x.json",
    ]
    for name in ignored:
        place(key_dir / name, b"{not json")
    place(key_dir / "sub" / case_name(OTHER_B, 1), valid)
    place(key_dir / "subdir.json" / case_name(OTHER_B, 2), valid)

    result = find(root, hw(), op(), READER)

    assert result == Found((HW_KEY, OP_KEY), (a,), ())
    assert sorted(name for name in read_paths if "case" in name.lower()) == [
        case_name(OTHER_A, 1)
    ]


def test_find_is_independent_of_the_listing_order(root, key_dir, monkeypatch):
    store_case(root, OTHER_A, 1)
    store_case(root, OTHER_B, 1)
    store_case(root, OTHER_B, 2)
    place(key_dir / case_name(OTHER_A, 5), b"{}")
    place(key_dir / case_name(OTHER_A, 6), b"[]")
    first = find(root, hw(), op(), READER)
    original = os.listdir

    for order in (sorted, lambda names: sorted(names, reverse=True)):
        monkeypatch.setattr(
            os, "listdir", lambda path, order=order: order(original(path))
        )
        assert find(root, hw(), op(), READER) == first

    assert find(root, hw(), op(), READER) == first
    assert len(first.cases) == 3
    assert len(first.reports) == 2


def test_find_writes_nothing(root, key_dir):
    store_case(root, OTHER_A, 1)
    place(key_dir / case_name(OTHER_B, 1), b"{}")
    before = sorted(path.as_posix() for path in root.rglob("*"))

    find(root, hw(), op(), READER)

    assert sorted(path.as_posix() for path in root.rglob("*")) == before


@pytest.mark.parametrize("run_id", ["", "UPPER", "a/b", None, 7])
def test_find_refuses_a_bad_run_id_before_reading(root, key_dir, read_paths, run_id):
    with pytest.raises(layout.InvalidPathValueError):
        find(root, hw(), op(), run_id)
    assert read_paths == []


def test_find_refuses_a_missing_data_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        find(tmp_path / "absent", hw(), op(), READER)


def test_find_refuses_a_data_root_that_is_a_file(tmp_path):
    path = place(tmp_path / "file", b"")
    with pytest.raises(NotADirectoryError):
        find(path, hw(), None, READER)


def test_find_passes_on_an_invalid_record(root):
    with pytest.raises(keys.InvalidRecordError):
        find(root, hw(schema_version="x"), op(), READER)
    with pytest.raises(keys.InvalidRecordError):
        find(root, hw(), op(kind=7), READER)


def test_find_passes_on_an_error_of_listing(root, key_dir, monkeypatch):
    def failing(path):
        raise PermissionError(13, "synthetic denial", str(path))

    monkeypatch.setattr(os, "listdir", failing)

    with pytest.raises(PermissionError):
        find(root, hw(), op(), READER)


def test_lookup_refuses_a_missing_instance(root):
    with pytest.raises(instance.MissingInstanceError):
        lookup(root, READER)


def test_lookup_refuses_an_invalid_instance(root):
    place(layout.run_file(root, READER, "instance.json"), b"{}")
    with pytest.raises(instance.InvalidInstanceError):
        lookup(root, READER)


def test_lookup_sets_apart_an_instance_of_another_version(root):
    place(layout.run_file(root, READER, "instance.json"), b'{"schema_version": 2}\n')
    with pytest.raises(instance.UnsupportedVersionError):
        lookup(root, READER)


def test_lookup_refuses_a_bad_run_id(root):
    with pytest.raises(layout.InvalidPathValueError):
        lookup(root, "Bad")
