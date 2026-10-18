import contextlib
import copy
import json
import os
import re

import pytest

from hilclaw import artifacts, cas, keys, layout
from hilclaw.artifacts import (
    Added,
    ArtifactNotFoundError,
    CorruptArtifactsError,
    InvalidArtifactsError,
    SizeConflictError,
    add_record,
    load,
    set_retention_class,
    validate,
)

# Synthetic values only: no hash, kind or time of a real run or artefact.
RUN = "run-a"
FILE = f"runs/{RUN}/artifacts.json"
KIND = "example_kind"
ONES = "1" * 64
MEMBERS = ["sha256", "size", "type", "round", "retention_class"]
TEMPORARY = re.compile(r"artifacts\.json\.[a-z0-9-]{1,64}\.tmp")
LEFTOVER = f"runs/{RUN}/artifacts.json.4242-0123456789abcdef.tmp"

# The Example of ADR-0005, its gc_at placeholder replaced by a time of ADR-0099.
EXAMPLE = (
    b"{\n"
    b'"schema_version": 1,\n'
    b'"artifacts": [\n'
    b'{"sha256": "1111111111111111111111111111111111111111111111111111111111111111",'
    b' "size": 18432, "type": "example_kind", "round": 0,'
    b' "retention_class": "intermediate"},\n'
    b'{"sha256": "2222222222222222222222222222222222222222222222222222222222222222",'
    b' "size": 20480, "type": "example_kind", "round": 3, "retention_class": "best"},\n'
    b'{"sha256": "3333333333333333333333333333333333333333333333333333333333333333",'
    b' "size": 0, "type": "example_kind", "round": 3, "retention_class": "failed",'
    b' "gc_at": "2024-01-02T03:04:05Z"}\n'
    b"]\n"
    b"}\n"
)


def rec(sha256=ONES, **changes):
    record = {
        "sha256": sha256,
        "size": 7,
        "type": KIND,
        "round": 0,
        "retention_class": "intermediate",
    }
    record.update(changes)
    return record


def without(member):
    record = rec()
    del record[member]
    return record


def doc(*records, **changes):
    document = {"schema_version": 1, "artifacts": list(records)}
    document.update(changes)
    return document


def line(record):
    parts = [
        f'"sha256": "{record["sha256"]}"',
        f'"size": {record["size"]}',
        f'"type": "{record["type"]}"',
        f'"round": {record["round"]}',
        f'"retention_class": "{record["retention_class"]}"',
    ]
    if "gc_at" in record:
        parts.append(f'"gc_at": "{record["gc_at"]}"')
    return "{" + ", ".join(parts) + "}"


def text(*records):
    lines = ",\n".join(line(record) for record in records)
    return f'{{\n"schema_version": 1,\n"artifacts": [\n{lines}\n]\n}}\n'.encode()


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


def snapshot(tmp_path):
    return {
        path.relative_to(tmp_path).as_posix(): (
            (path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else None
        )
        for path in tmp_path.rglob("*")
    }


def put(root, number=1):
    return cas.put_bytes(root, b"synthetic content %d" % number)


def add(root, ref, run=RUN, **changes):
    members = {"type": KIND, "round": 0, "retention_class": "intermediate"}
    members.update(changes)
    return add_record(root, run, ref, **members)


def place(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def stored(ref, **changes):
    return rec(ref.digest, size=ref.size, **changes)


def held(root):
    path = root / FILE
    return path.read_bytes() if path.is_file() else None


def run_files(root):
    directory = root / "runs" / RUN
    if not directory.is_dir():
        return {}
    return {path.name: path.read_bytes() for path in directory.iterdir()}


def temporaries(root):
    return [name for name in run_files(root) if TEMPORARY.fullmatch(name)]


# --- happy ---


def test_add_record_creates_the_file_next_to_the_blob(root, tmp_path):
    ref = put(root)

    result = add(root, ref)

    files = sorted(name for name, content in snapshot(tmp_path).items() if content)
    blob = f"data/blobs/sha256/{ref.digest[:2]}/{ref.digest}"
    assert files == sorted([blob, f"data/{FILE}"])
    assert result == Added(stored(ref), True)
    assert result.created is True
    assert list(result.record) == MEMBERS
    assert load(root, RUN) == [stored(ref)]
    assert validate(json.loads((root / FILE).read_bytes())) is None
    assert layout.run_file(root, RUN, "artifacts.json") == root / FILE


def test_records_are_kept_in_the_order_of_addition(root):
    refs = [put(root, 1), put(root, 2), cas.put_bytes(root, b"")]
    for ref, round in zip(refs, [0, 3, 3], strict=True):
        assert add(root, ref, round=round).created

    records = load(root, RUN)

    assert [record["sha256"] for record in records] == [ref.digest for ref in refs]
    assert [record["round"] for record in records] == [0, 3, 3]
    assert records[2]["size"] == 0
    assert refs[2].size == 0


def test_the_written_form(root):
    first, second, third = put(root, 1), put(root, 2), put(root, 3)
    add(root, first, retention_class="failed")
    add(root, second, round=3)
    two = (root / FILE).read_bytes()

    assert two == text(stored(first, retention_class="failed"), stored(second, round=3))
    assert not two.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in two
    assert two.endswith(b"}\n") and not two.endswith(b"\n\n")
    assert two.decode("utf-8").isascii()
    lines = two.split(b"\n")
    assert len(lines) == 8
    for written in lines[3:5]:
        assert list(json.loads(written.rstrip(b","))) == MEMBERS

    add(root, third)
    three = (root / FILE).read_bytes().split(b"\n")

    assert three[:3] == lines[:3]
    assert three[3] == lines[3]
    assert three[4] == lines[4] + b","
    assert three[5] == line(stored(third)).encode()
    assert three[6:] == lines[5:]


def test_the_same_content_gives_the_same_bytes(root, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    for data_root in (root, other):
        add(data_root, put(data_root, 1))
        add(data_root, put(data_root, 2), round=3)
    before = (root / FILE).read_bytes()
    assert (other / FILE).read_bytes() == before

    digest = put(root, 2).digest
    set_retention_class(root, RUN, digest, "best")
    assert (root / FILE).read_bytes() != before
    set_retention_class(root, RUN, digest, "intermediate")

    assert (root / FILE).read_bytes() == before


def test_the_writer_keeps_the_layout_of_the_adr_example(root):
    place(root, FILE, EXAMPLE)
    ref = put(root)

    assert add(root, ref, round=4, retention_class="final").created

    added = line(stored(ref, round=4, retention_class="final")).encode()
    assert (root / FILE).read_bytes() == EXAMPLE[:-5] + b",\n" + added + b"\n]\n}\n"


@pytest.mark.parametrize("target", ["best", "final", "intermediate", "failed"])
def test_set_retention_class_changes_one_member_of_one_record(root, target):
    refs = [put(root, number) for number in (1, 2, 3)]
    for ref in refs:
        add(root, ref, retention_class="best" if target != "best" else "failed")
    before = (root / FILE).read_bytes().split(b"\n")

    result = set_retention_class(root, RUN, refs[1].digest, target)

    assert result == stored(refs[1], retention_class=target)
    after = (root / FILE).read_bytes().split(b"\n")
    assert after[:4] == before[:4]
    assert after[5:] == before[5:]
    assert after[4] == line(result).encode() + b","
    assert load(root, RUN)[1] == result


def test_validate_accepts_the_example_of_adr_0005():
    document = json.loads(EXAMPLE)
    assert len(document["artifacts"]) == 3
    assert "gc_at" in document["artifacts"][2]

    assert validate(document) is None


@pytest.mark.parametrize(
    "document",
    [
        doc(),
        doc(rec(type="a_kind_nobody_listed")),
        doc(rec(size=0, round=keys.MAX_INTEGER)),
        doc(
            rec(gc_at="0001-01-01T00:00:00Z"),
            rec("2" * 64, gc_at="9999-12-31T23:59:59Z"),
        ),
        doc(
            rec(gc_at="2024-02-29T12:00:00Z"),
            rec("2" * 64, gc_at="2000-02-29T00:00:00Z"),
        ),
        {"artifacts": [dict(reversed(rec().items()))], "schema_version": 1},
        doc(rec(round=3), rec("0123456789abcdef" * 4, round=0)),
    ],
)
def test_validate_accepts(document):
    before = copy.deepcopy(document)

    assert validate(document) is None
    assert document == before


# --- branch ---


@pytest.mark.parametrize("prepare", ["nothing", "runs", "run", "empty array"])
def test_load_without_a_record_returns_an_empty_list(root, tmp_path, prepare):
    if prepare == "runs":
        (root / "runs").mkdir()
    elif prepare == "run":
        (root / "runs" / RUN).mkdir(parents=True)
    elif prepare == "empty array":
        place(root, FILE, b'{"schema_version": 1, "artifacts": []}')
    before = snapshot(tmp_path)

    assert load(root, RUN) == []
    assert snapshot(tmp_path) == before


def test_a_repeated_add_keeps_the_first_record(root, tmp_path):
    ref = put(root)
    add(root, ref)
    before = snapshot(tmp_path)

    result = add(root, ref, type="another_kind", round=5, retention_class="best")

    assert result == Added(stored(ref), False)
    assert result.created is False
    assert snapshot(tmp_path) == before


def test_the_same_hash_in_the_files_of_two_runs(root):
    ref = put(root)

    assert add(root, ref, round=1, retention_class="best").created
    assert add(root, ref, run="run-b", round=2, retention_class="failed").created

    assert load(root, RUN) == [stored(ref, round=1, retention_class="best")]
    assert load(root, "run-b") == [stored(ref, round=2, retention_class="failed")]


def test_a_file_in_another_valid_form_is_read_and_normalised_by_the_next_write(root):
    ref = put(root)
    records = [rec(gc_at="2001-02-03T04:05:06Z"), rec("2" * 64, round=9)]
    shuffled = [dict(reversed(record.items())) for record in records]
    by_hand = json.dumps({"artifacts": shuffled, "schema_version": 1}, indent=4)
    place(root, FILE, by_hand.replace("\n", "\r\n").encode())

    loaded = load(root, RUN)

    assert loaded == records
    assert list(loaded[0]) == [*MEMBERS, "gc_at"]
    assert list(loaded[1]) == MEMBERS

    assert add(root, ref).created

    assert (root / FILE).read_bytes() == text(*records, stored(ref))


def test_set_retention_class_to_the_current_class_writes_nothing(root, tmp_path):
    by_hand = json.dumps(doc(rec(retention_class="final")), indent=2).encode()
    place(root, FILE, by_hand)
    before = snapshot(tmp_path)

    assert set_retention_class(root, RUN, ONES, "final") == rec(retention_class="final")
    assert snapshot(tmp_path) == before


def test_set_retention_class_on_a_record_with_gc_at(root):
    records = [
        rec(gc_at="2001-02-03T04:05:06Z", retention_class="failed"),
        rec("2" * 64),
    ]
    place(root, FILE, text(*records))

    result = set_retention_class(root, RUN, ONES, "best")

    assert result == rec(gc_at="2001-02-03T04:05:06Z", retention_class="best")
    assert (root / FILE).read_bytes() == text(result, records[1])


def test_data_root_as_str_and_ref_as_plain_tuple(root):
    ref = put(root)

    result = add(str(root), (ref.digest, ref.size))

    assert result == Added(stored(ref), True)
    assert load(str(root), RUN) == load(root, RUN) == [stored(ref)]
    changed = set_retention_class(str(root), RUN, ref.digest, "final")
    assert changed == stored(ref, retention_class="final")


def test_a_loaded_record_is_independent_of_the_file(root):
    ref = put(root)
    add(root, ref)

    load(root, RUN)[0]["retention_class"] = "best"

    assert load(root, RUN) == [stored(ref)]


def test_error_types():
    assert issubclass(InvalidArtifactsError, ValueError)
    assert issubclass(ArtifactNotFoundError, LookupError)
    for error in (CorruptArtifactsError, SizeConflictError):
        assert not issubclass(error, (ValueError, LookupError, OSError))
    assert artifacts.SCHEMA_VERSION == 1
    assert artifacts.RETENTION_CLASSES == ("best", "final", "intermediate", "failed")


# --- negative: validate ---

BAD_SHA256 = {
    "upper case": "A" * 64,
    "63 characters": "1" * 63,
    "65 characters": "1" * 65,
    "not hexadecimal": "g" * 64,
    "prefixed": "sha256:" + ONES,
    "trailing newline": ONES + "\n",
    "bytes": ONES.encode(),
    "integer": 1,
    "none": None,
}
BAD_INTEGER = {
    "negative": -1,
    "2^53": 2**53,
    "float": 1.0,
    "true": True,
    "string": "1",
    "none": None,
}
BAD_TYPE = {
    "empty": "",
    "upper case": "Example_kind",
    "33 characters": "a" * 33,
    "hyphen": "example-kind",
    "leading digit": "1kind",
    "integer": 1,
    "none": None,
}
BAD_CLASS = {
    "outside the four": "permanent",
    "another case": "Best",
    "empty": "",
    "list": ["best"],
    "none": None,
}
BAD_GC_AT = {
    "number": 0,
    "none": None,
    "empty": "",
    "not ascii": "té",
    "control character": "a\tb",
    "256 characters": "x" * 256,
    "placeholder of adr-0005": "TIME-FORM-NOT-DECIDED-HERE",
    "x": "x",
    "lower-case t": "2024-01-02t03:04:05Z",
    "lower-case z": "2024-01-02T03:04:05z",
    "offset": "2024-01-02T03:04:05+00:00",
    "fractions": "2024-01-02T03:04:05.000Z",
    "space for t": "2024-01-02 03:04:05Z",
    "19 characters": "2024-01-02T03:04:05",
    "21 characters": "2024-01-02T03:04:05ZZ",
    "trailing newline": "2024-01-02T03:04:05Z\n",
    "non-ascii digits": "\u0662\u0660\u0662\u0664-01-02T03:04:05Z",
    "feb 29 of a common year": "2023-02-29T00:00:00Z",
    "feb 30": "2024-02-30T00:00:00Z",
    "hour 24": "2024-01-02T24:00:00Z",
    "minute 60": "2024-01-02T03:60:00Z",
    "second 60": "2024-01-02T03:04:60Z",
    "year 0000": "0000-01-01T00:00:00Z",
    "month 13": "2024-13-01T00:00:00Z",
    "day 00": "2024-01-00T00:00:00Z",
}
BAD_MEMBERS = {
    "sha256": BAD_SHA256,
    "size": BAD_INTEGER,
    "type": BAD_TYPE,
    "round": BAD_INTEGER,
    "retention_class": BAD_CLASS,
    "gc_at": BAD_GC_AT,
}
INVALID_DOCUMENTS = {
    "a list": ([], "document"),
    "a string": ("synthetic", "document"),
    "none": (None, "document"),
    "no schema_version": ({"artifacts": []}, "document: lacks the member schema_ver"),
    "no artifacts": ({"schema_version": 1}, "document: lacks the member artifacts"),
    "extra top-level member": (doc(synthetic=1), "document: has the unknown member"),
    "member name not a str": ({1: 1}, "document: has the unknown member 1"),
    "schema_version 2": (doc(schema_version=2), "schema_version"),
    "schema_version 0": (doc(schema_version=0), "schema_version"),
    "schema_version 1.0": (doc(schema_version=1.0), "schema_version"),
    "schema_version true": (doc(schema_version=True), "schema_version"),
    "schema_version string": (doc(schema_version="1"), "schema_version"),
    "schema_version none": (doc(schema_version=None), "schema_version"),
    "artifacts an object": (doc(artifacts={}), "artifacts: must be an array"),
    "artifacts a tuple": (doc(artifacts=()), "artifacts: must be an array"),
    "artifacts none": (doc(artifacts=None), "artifacts: must be an array"),
    "record a list": (doc(rec(), []), "artifacts[1]: must be an object"),
    "record a string": (doc("synthetic"), "artifacts[0]: must be an object"),
    "record none": (doc(None), "artifacts[0]: must be an object"),
    "same sha256 twice": (
        doc(rec(), rec("2" * 64), rec(round=4, retention_class="best")),
        "artifacts[2].sha256: repeats the sha256 of artifacts[0]",
    ),
}
for _member in MEMBERS:
    INVALID_DOCUMENTS[f"record without {_member}"] = (
        doc(rec("2" * 64), without(_member)),
        f"artifacts[1]: lacks the member {_member}",
    )
for _member in ("pushed", "location", "ext", "candidate", "attempt", "hash"):
    INVALID_DOCUMENTS[f"unknown member {_member}"] = (
        doc(rec(**{_member: "synthetic"})),
        f"artifacts[0]: has the unknown member '{_member}'",
    )
for _member, _values in BAD_MEMBERS.items():
    for _case, _value in _values.items():
        INVALID_DOCUMENTS[f"{_member} {_case}"] = (
            doc(rec("2" * 64), rec("3" * 64), rec(**{_member: _value})),
            f"artifacts[2].{_member}: must be ",
        )


@pytest.mark.parametrize("case", INVALID_DOCUMENTS)
def test_validate_rejects(case):
    document, message = INVALID_DOCUMENTS[case]
    before = copy.deepcopy(document)

    with pytest.raises(InvalidArtifactsError) as excinfo:
        validate(document)

    assert str(excinfo.value).startswith(message)
    assert document == before


def test_an_error_message_shows_a_bounded_value():
    with pytest.raises(InvalidArtifactsError) as excinfo:
        validate(doc(rec(type="x" * 100_000)))

    assert len(str(excinfo.value)) < 200
    assert "got str 'xxx" in str(excinfo.value)


# --- negative: arguments ---

INVALID_ADDS = {
    "ref a list": ({"ref": [ONES, 7]}, "ref: must be a tuple"),
    "ref a string": ({"ref": ONES}, "ref: must be a tuple"),
    "ref none": ({"ref": None}, "ref: must be a tuple"),
    "ref of three": ({"ref": (ONES, 7, 7)}, "ref: must be a tuple"),
    "ref of one": ({"ref": (ONES,)}, "ref: must be a tuple"),
}
for _case, _value in BAD_SHA256.items():
    INVALID_ADDS[f"digest {_case}"] = ({"ref": (_value, 7)}, "ref.digest: must be ")
for _case, _value in BAD_INTEGER.items():
    INVALID_ADDS[f"size {_case}"] = ({"ref": (ONES, _value)}, "ref.size: must be ")
    INVALID_ADDS[f"round {_case}"] = ({"round": _value}, "round: must be ")
for _case, _value in BAD_TYPE.items():
    INVALID_ADDS[f"type {_case}"] = ({"type": _value}, "type: must be ")
for _case, _value in BAD_CLASS.items():
    INVALID_ADDS[f"class {_case}"] = (
        {"retention_class": _value},
        "retention_class: must be one of best, final, intermediate, failed",
    )


@pytest.mark.parametrize("case", INVALID_ADDS)
def test_add_record_rejects_an_invalid_argument(root, tmp_path, case):
    changes, message = INVALID_ADDS[case]
    ref = put(root)
    before = snapshot(tmp_path)

    with pytest.raises(InvalidArtifactsError) as excinfo:
        add(
            root,
            changes.get("ref", ref),
            **{k: v for k, v in changes.items() if k != "ref"},
        )

    assert str(excinfo.value).startswith(message)
    assert snapshot(tmp_path) == before


def test_add_record_has_no_default_for_the_members(root, tmp_path):
    ref = put(root)
    before = snapshot(tmp_path)

    with pytest.raises(TypeError):
        add_record(root, RUN, ref)
    with pytest.raises(TypeError):
        add_record(root, RUN, ref, type=KIND, round=0)
    with pytest.raises(TypeError):
        add_record(root, RUN, ref, KIND, 0, "best")
    assert snapshot(tmp_path) == before


def test_add_record_requires_the_blob(root, tmp_path):
    put(root)
    before = snapshot(tmp_path)

    with pytest.raises(ArtifactNotFoundError, match=f"blob {ONES} is not in the store"):
        add(root, (ONES, 7))

    assert snapshot(tmp_path) == before


def test_add_record_requires_the_blob_also_for_a_recorded_hash(root, tmp_path):
    place(root, FILE, text(rec(gc_at="2001-02-03T04:05:06Z")))
    before = snapshot(tmp_path)

    with pytest.raises(ArtifactNotFoundError, match="decision 8"):
        add(root, (ONES, 7))

    assert snapshot(tmp_path) == before


def test_add_record_reports_a_differing_size(root, tmp_path):
    ref = put(root)
    add(root, ref)
    before = snapshot(tmp_path)

    with pytest.raises(SizeConflictError) as excinfo:
        add(root, (ref.digest, ref.size + 1))

    message = str(excinfo.value)
    assert message.startswith(f"{FILE}: sha256 {ref.digest}")
    assert f"size {ref.size}," in message and f"given size {ref.size + 1}" in message
    assert snapshot(tmp_path) == before


CALLS = {
    "load": lambda data_root, run, digest: load(data_root, run),
    "add_record": lambda data_root, run, digest: add(data_root, (digest, 19), run=run),
    "set_retention_class": lambda data_root, run, digest: set_retention_class(
        data_root, run, digest, "best"
    ),
}
BAD_RUN_IDS = ["..", "run/a", "runs\\a", "Run-a", "", "-run", "a" * 65, None, 1]


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("run_id", BAD_RUN_IDS)
def test_an_invalid_run_id(root, tmp_path, call, run_id):
    ref = put(root)
    add(root, ref)
    before = snapshot(tmp_path)

    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        CALLS[call](root, run_id, ref.digest)

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", CALLS)
def test_a_data_root_that_is_not_an_existing_directory(tmp_path, call):
    place(tmp_path, "a-file", b"synthetic")
    before = snapshot(tmp_path)

    with pytest.raises(FileNotFoundError, match="data root"):
        CALLS[call](tmp_path / "missing", RUN, ONES)
    with pytest.raises(NotADirectoryError, match="data root"):
        CALLS[call](tmp_path / "a-file", RUN, ONES)
    with pytest.raises(NotADirectoryError, match="data root"):
        CALLS[call](str(tmp_path / "a-file"), RUN, ONES)

    assert snapshot(tmp_path) == before


def test_arguments_are_checked_before_the_file_system(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(InvalidArtifactsError, match="^round"):
        add(missing, (ONES, 7), round=-1)
    with pytest.raises(InvalidArtifactsError, match="^retention_class"):
        set_retention_class(missing, RUN, ONES, "permanent")
    with pytest.raises(layout.InvalidPathValueError):
        load(missing, "..")
    with pytest.raises(layout.InvalidPathValueError):
        add(missing, (ONES, -1), run="..")
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("present", [True, False])
def test_set_retention_class_of_an_unknown_hash(root, tmp_path, present):
    if present:
        add(root, put(root))
    before = snapshot(tmp_path)

    with pytest.raises(ArtifactNotFoundError) as excinfo:
        set_retention_class(root, RUN, ONES, "best")

    assert str(excinfo.value) == f"{FILE}: no record with sha256 {ONES}"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("case", BAD_CLASS)
def test_set_retention_class_rejects_a_class(root, tmp_path, case):
    ref = put(root)
    add(root, ref)
    before = snapshot(tmp_path)

    with pytest.raises(InvalidArtifactsError, match="^retention_class: must be one of"):
        set_retention_class(root, RUN, ref.digest, BAD_CLASS[case])

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("case", BAD_SHA256)
def test_set_retention_class_rejects_a_malformed_hash(root, tmp_path, case):
    add(root, put(root))
    before = snapshot(tmp_path)

    with pytest.raises(InvalidArtifactsError, match="^sha256: must be a str of 64"):
        set_retention_class(root, RUN, BAD_SHA256[case], "best")

    assert snapshot(tmp_path) == before


# --- negative: the stored file ---


def corrupt_contents():
    valid = text(rec(size=19))
    return {
        "empty": b"",
        "not utf-8": b"\xff\xfe" + valid,
        "byte order mark": b"\xef\xbb\xbf" + valid,
        "not json": valid[:-3],
        "array": b"[]",
        "string": b'"synthetic"',
        "repeated top-level member": b'{"schema_version": 1,' + valid[1:],
        "repeated member in a record": valid.replace(
            b'"size": 19,', b'"size": 19,' * 2
        ),
        "nan": valid.replace(b'"size": 19', b'"size": NaN'),
        "float size": valid.replace(b'"size": 19', b'"size": 19.0'),
        "exponent size": valid.replace(b'"size": 19', b'"size": 1e1'),
        "null gc_at": valid.replace(b'"}', b'", "gc_at": null}'),
        "unknown member": valid.replace(b'"}', b'", "pushed": "yes"}'),
        "unknown top-level member": valid.replace(b"\n}", b',\n"synthetic": 1\n}'),
        "schema_version 2": valid.replace(
            b'"schema_version": 1', b'"schema_version": 2'
        ),
        "no schema_version": valid.replace(b'"schema_version": 1,', b""),
        "duplicated sha256": text(rec(size=19), rec(size=19)),
        "nested too deeply": b"[" * 100_000,
    }


CORRUPT = corrupt_contents()


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("case", CORRUPT)
def test_a_stored_file_that_is_not_valid(root, tmp_path, call, case):
    digest = cas.put_bytes(root, b"synthetic content").digest
    place(root, FILE, CORRUPT[case].replace(ONES.encode(), digest.encode()))
    before = snapshot(tmp_path)

    with pytest.raises(CorruptArtifactsError) as excinfo:
        CALLS[call](root, RUN, digest)

    message = str(excinfo.value)
    assert message.startswith(f"{FILE}: must be UTF-8 JSON of a valid file")
    assert len(message) < 400
    assert snapshot(tmp_path) == before


def test_validate_names_the_place_and_the_form_of_gc_at():
    document = doc(rec("2" * 64), rec(gc_at="TIME-FORM-NOT-DECIDED-HERE"))

    with pytest.raises(InvalidArtifactsError) as excinfo:
        validate(document)

    rule = "a str YYYY-MM-DDThh:mm:ssZ of an existing date and time"
    assert str(excinfo.value).startswith(f"artifacts[1].gc_at: must be {rule}, got str")


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize(
    "value", ["TIME-FORM-NOT-DECIDED-HERE", "2023-02-29T00:00:00Z"]
)
def test_a_stored_gc_at_not_of_the_time_form(root, tmp_path, call, value):
    digest = cas.put_bytes(root, b"synthetic content").digest
    place(root, FILE, text(rec(digest, size=19, gc_at=value)))
    before = snapshot(tmp_path)

    reason = r"artifacts\[0\]\.gc_at: must be a str YYYY-MM-DDThh:mm:ssZ"
    with pytest.raises(CorruptArtifactsError, match=reason):
        CALLS[call](root, RUN, digest)

    assert snapshot(tmp_path) == before


def test_the_reason_of_a_corrupt_file_names_the_place(root):
    place(root, FILE, CORRUPT["float size"])

    with pytest.raises(
        CorruptArtifactsError, match=r"artifacts\[0\]\.size: must be"
    ) as e:
        load(root, RUN)

    assert isinstance(e.value.__cause__, InvalidArtifactsError)


@pytest.mark.parametrize("call", CALLS)
def test_the_file_path_is_a_directory(root, tmp_path, call):
    ref = put(root)
    (root / FILE).mkdir(parents=True)
    before = snapshot(tmp_path)

    with pytest.raises(CorruptArtifactsError) as excinfo:
        CALLS[call](root, RUN, ref.digest)

    assert str(excinfo.value) == f"{FILE}: is not a regular file"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", CALLS)
def test_a_symbolic_link_in_the_place_of_the_file_is_not_followed(root, tmp_path, call):
    ref = put(root)
    target = place(tmp_path, "outside.json", text(stored(ref)))
    (root / "runs" / RUN).mkdir(parents=True)
    try:
        (root / FILE).symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")

    with pytest.raises(CorruptArtifactsError, match="is not a regular file"):
        CALLS[call](root, RUN, ref.digest)

    assert target.read_bytes() == text(stored(ref))


@pytest.mark.parametrize("occupied", ["runs", f"runs/{RUN}"])
def test_a_file_in_the_place_of_a_directory(root, tmp_path, occupied):
    ref = put(root)
    place(root, occupied, b"not a directory")
    before = snapshot(tmp_path)

    assert load(root, RUN) == []
    with pytest.raises(OSError):
        add(root, ref)
    with pytest.raises(ArtifactNotFoundError):
        set_retention_class(root, RUN, ref.digest, "best")
    assert snapshot(tmp_path) == before


# --- negative: a failing write ---


def failing(error):
    def fail(*args, **kwargs):
        raise error

    return fail


@pytest.mark.parametrize("error", [OSError("synthetic failure"), KeyboardInterrupt()])
def test_a_failing_first_write_leaves_no_file(root, monkeypatch, error):
    ref = put(root)
    monkeypatch.setattr(artifacts.os, "fsync", failing(error))

    with pytest.raises(type(error)) as excinfo:
        add(root, ref)

    assert excinfo.value is error
    assert not (root / FILE).exists()
    assert temporaries(root) == []
    monkeypatch.undo()
    assert load(root, RUN) == []
    assert add(root, ref) == Added(stored(ref), True)


def test_a_file_that_cannot_be_opened(root, monkeypatch):
    ref = put(root)
    error = OSError("synthetic failure")
    monkeypatch.setattr(artifacts, "open", failing(error), raising=False)

    with pytest.raises(OSError) as excinfo:
        add(root, ref)

    assert excinfo.value is error
    assert not (root / FILE).exists()
    assert temporaries(root) == []


class TornFile:
    def __init__(self, file):
        self.file = file

    def write(self, data):
        self.file.write(data[:10])
        raise OSError("synthetic failure")


@contextlib.contextmanager
def torn_open(path, mode):
    with open(path, mode) as f:
        yield TornFile(f)


@pytest.mark.parametrize("existing", [False, True])
def test_a_write_that_fails_midway(root, monkeypatch, existing):
    first, second = put(root, 1), put(root, 2)
    if existing:
        add(root, first)
    previous = held(root)
    monkeypatch.setattr(artifacts, "open", torn_open, raising=False)

    with pytest.raises(OSError, match="synthetic failure"):
        add(root, second)

    monkeypatch.undo()
    assert held(root) == previous
    assert temporaries(root) == []
    assert load(root, RUN) == ([stored(first)] if existing else [])
    assert add(root, second).created


@pytest.mark.parametrize("edit", ["add_record", "set_retention_class"])
def test_a_failing_rewrite_keeps_the_file_in_its_place(root, monkeypatch, edit):
    first, second = put(root, 1), put(root, 2)
    add(root, first)
    previous = held(root)
    error = OSError("synthetic failure")
    monkeypatch.setattr(artifacts.os, "fsync", failing(error))

    with pytest.raises(OSError) as excinfo:
        if edit == "add_record":
            add(root, second)
        else:
            set_retention_class(root, RUN, first.digest, "best")

    assert excinfo.value is error
    assert held(root) == previous == text(stored(first))
    assert temporaries(root) == []


# --- the write as a replacement (ADR-0014 decision 2) ---

WRITES = ("first file", "add_record", "set_retention_class")
STEPS = ("creation", "write", "flush", "move")


def prepare(root, write):
    first, second = put(root, 1), put(root, 2)
    if write == "first file":
        return None, text(stored(second)), lambda: add(root, second)
    add(root, first)
    if write == "add_record":
        new = text(stored(first), stored(second))
        return held(root), new, lambda: add(root, second)
    new = text(stored(first, retention_class="best"))
    return held(root), new, lambda: set_retention_class(root, RUN, first.digest, "best")


def watch(monkeypatch, root):
    seen = []
    flush, move = os.fsync, os.replace

    def fsync(descriptor):
        files = run_files(root)
        seen.append({"step": "flush", "held": files.pop("artifacts.json", None)})
        status = os.fstat(descriptor)
        same = [
            name
            for name in files
            if os.path.samestat(status, os.stat(root / "runs" / RUN / name))
        ]
        seen[-1].update(descriptor=descriptor, files=files, flushed=same)
        return flush(descriptor)

    def replacing(source, target):
        with pytest.raises(OSError):
            os.fstat(seen[-1]["descriptor"])
        content = source.read_bytes()
        seen.append({"step": "move", "held": held(root), "content": content})
        seen[-1].update(source=source, target=target)
        return move(source, target)

    monkeypatch.setattr(artifacts.os, "fsync", fsync)
    monkeypatch.setattr(artifacts.os, "replace", replacing)
    return seen


def spy_on_open(monkeypatch):
    opened = []

    def spy(file, mode="r", *arguments, **named):
        opened.append((file, mode))
        return open(file, mode, *arguments, **named)

    monkeypatch.setattr(artifacts, "open", spy, raising=False)
    return opened


def break_step(monkeypatch, step, error):
    if step == "creation":
        monkeypatch.setattr(artifacts, "open", failing(error), raising=False)
    elif step == "write":
        monkeypatch.setattr(artifacts, "open", torn_open, raising=False)
    else:
        name = {"flush": "fsync", "move": "replace", "removal": "unlink"}[step]
        monkeypatch.setattr(artifacts.os, name, failing(error))


@pytest.mark.parametrize("write", WRITES)
def test_a_write_leaves_the_file_and_no_temporary_file(root, write):
    _, new, call = prepare(root, write)

    call()

    assert run_files(root) == {"artifacts.json": new}


def test_a_first_write_creates_the_file_and_its_directories_only(root, tmp_path):
    ref = put(root)
    before = set(snapshot(tmp_path))

    add(root, ref)

    created = {"data/runs", f"data/runs/{RUN}", f"data/{FILE}"}
    assert set(snapshot(tmp_path)) - before == created


@pytest.mark.parametrize("write", WRITES)
def test_the_final_name_holds_the_previous_content_until_the_move(
    root, monkeypatch, write
):
    previous, new, call = prepare(root, write)
    seen = watch(monkeypatch, root)

    call()

    flush, move = seen
    assert (flush["step"], move["step"]) == ("flush", "move")
    assert flush["held"] == move["held"] == previous
    assert held(root) == new


@pytest.mark.parametrize("write", WRITES)
def test_the_temporary_file_is_whole_and_beside_the_final_one(root, monkeypatch, write):
    _, new, call = prepare(root, write)
    seen = watch(monkeypatch, root)

    call()

    flush, move = seen
    source = move["source"]
    assert source.parent == root / "runs" / RUN
    assert move["target"] == layout.run_file(root, RUN, "artifacts.json")
    assert TEMPORARY.fullmatch(source.name)
    assert source.name not in layout.RUN_FILES
    assert move["content"] == new
    assert flush["files"] == {source.name: new}
    assert flush["flushed"] == [source.name]
    assert temporaries(root) == []


def test_two_writes_use_two_temporary_names(root, monkeypatch):
    refs = [put(root, number) for number in (1, 2, 3)]
    seen = watch(monkeypatch, root)

    for ref in refs:
        add(root, ref)
    set_retention_class(root, RUN, refs[0].digest, "final")

    sources = [entry["source"].name for entry in seen if entry["step"] == "move"]
    assert len(set(sources)) == 4
    assert all(TEMPORARY.fullmatch(name) for name in sources)


@pytest.mark.parametrize("write", WRITES)
def test_only_a_new_file_of_the_temporary_name_is_opened(root, monkeypatch, write):
    _, new, call = prepare(root, write)
    opened = spy_on_open(monkeypatch)

    call()

    ((path, mode),) = opened
    assert mode == "xb"
    assert path.parent == root / "runs" / RUN
    assert TEMPORARY.fullmatch(path.name)
    assert held(root) == new


def test_a_call_that_writes_nothing_takes_no_step(root, monkeypatch):
    ref = put(root)
    add(root, ref)
    seen = watch(monkeypatch, root)
    opened = spy_on_open(monkeypatch)

    assert not add(root, ref, round=5).created
    assert set_retention_class(root, RUN, ref.digest, "intermediate") == stored(ref)

    assert seen == [] and opened == []
    assert run_files(root) == {"artifacts.json": text(stored(ref))}


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("whole", [False, True])
def test_a_leftover_is_neither_read_nor_moved_nor_removed(root, existing, whole):
    first, second = put(root, 1), put(root, 2)
    leftover = text(rec("2" * 64, retention_class="best"))
    place(root, LEFTOVER, leftover if whole else leftover[:9])
    if existing:
        add(root, first)
    records = [stored(first)] if existing else []

    assert load(root, RUN) == records
    assert add(root, second).created
    changed = set_retention_class(root, RUN, second.digest, "final")

    assert load(root, RUN) == [*records, changed]
    assert temporaries(root) == [LEFTOVER.rpartition("/")[2]]
    assert (root / LEFTOVER).read_bytes() == (leftover if whole else leftover[:9])


@pytest.mark.parametrize("write", WRITES)
@pytest.mark.parametrize(
    ("step", "kind"),
    [(step, OSError) for step in STEPS]
    + [(step, KeyboardInterrupt) for step in ("creation", "flush", "move")],
)
def test_a_failed_step_leaves_the_final_name_and_no_temporary_file(
    root, monkeypatch, write, step, kind
):
    previous, new, call = prepare(root, write)
    records = load(root, RUN)
    error = kind("synthetic failure")
    break_step(monkeypatch, step, error)

    with pytest.raises(kind, match="synthetic failure") as excinfo:
        call()
    monkeypatch.undo()

    assert step == "write" or excinfo.value is error
    assert held(root) == previous
    assert temporaries(root) == []
    assert load(root, RUN) == records
    call()
    assert run_files(root) == {"artifacts.json": new}


@pytest.mark.parametrize("write", WRITES)
def test_a_temporary_name_in_use_is_an_error_and_that_file_stays(
    root, monkeypatch, write
):
    previous, _, call = prepare(root, write)
    monkeypatch.setattr(artifacts.secrets, "token_hex", lambda size: "0" * 2 * size)
    name = f"artifacts.json.{os.getpid()}-{'0' * 16}.tmp"
    place(root, f"runs/{RUN}/{name}", b"of another writer")
    before = run_files(root)

    with pytest.raises(OSError):
        call()

    assert run_files(root) == before
    assert before[name] == b"of another writer"
    assert held(root) == previous


def test_a_removal_that_fails_does_not_hide_the_failure_of_the_step(root, monkeypatch):
    previous, new, call = prepare(root, "add_record")
    error = OSError("synthetic failure")
    break_step(monkeypatch, "move", error)
    break_step(monkeypatch, "removal", OSError("removal refused"))

    with pytest.raises(OSError) as excinfo:
        call()
    monkeypatch.undo()

    assert excinfo.value is error
    assert held(root) == previous
    (leftover,) = temporaries(root)
    assert run_files(root)[leftover] == new


@pytest.mark.parametrize("edit", ["add_record", "set_retention_class"])
def test_an_invalid_previous_file_takes_no_step(root, monkeypatch, edit):
    ref = put(root)
    place(root, FILE, CORRUPT["not json"])
    seen = watch(monkeypatch, root)
    opened = spy_on_open(monkeypatch)

    with pytest.raises(CorruptArtifactsError):
        CALLS[edit](root, RUN, ref.digest)

    assert seen == [] and opened == []
    assert run_files(root) == {"artifacts.json": CORRUPT["not json"]}
