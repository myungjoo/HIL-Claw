import copy
import json
import os
from types import MappingProxyType

import pytest

from hilclaw import key_records, keys, layout
from hilclaw.key_records import (
    CorruptKeyRecordError,
    KeyCollisionError,
    KeyRecordNotFoundError,
    Stored,
    load_hw_profile,
    load_op_signature,
    lookup,
    store_hw_profile,
    store_op_signature,
)

# Synthetic records: no hardware, toolchain or operation of a real instance.
PLACEHOLDER = "NOT-DECIDED-HERE"
HEX = "0123456789abcdef"
BAD_NAMES = [
    "synthetic_hw",
    "synthetic_hw-" + HEX.upper(),
    "Synthetic-" + HEX,
    "syn/thetic-" + HEX,
    "../synthetic_hw-" + HEX,
    "..",
    "",
    None,
    keys.Key("synthetic_hw-" + HEX, "0" * 64, b"{}"),
]


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


def without(record, field):
    del record[field]
    return record


HW_NAME = keys.hw_profile_key(hw()).name
OP_NAME = keys.op_signature_key(op()).name
HW_FILE = f"db/{HW_NAME}/hw_profile.json"
OP_FILE = f"db/{HW_NAME}/{OP_NAME}/op_signature.json"

INVALID_HW = {
    "missing field": (without(hw(), "revision"), "revision"),
    "unknown field": (hw(synthetic_unknown="x"), "synthetic_unknown"),
    "float": (hw(host={"cpu": 1.5, "os": "synthetic os"}), "host.cpu"),
    "true": (hw(ext={"synthetic": True}), "ext.synthetic"),
    "none": (hw(revision=None), "revision"),
    "empty ext": (hw(ext={}), "ext"),
    "schema_version 2": (hw(schema_version=2), "schema_version"),
    "not a mapping": ([("schema_version", 1)], "record"),
}
INVALID_OP = {
    "missing field": (without(op(), "layout"), "layout"),
    "unknown field": (op(synthetic_unknown="x"), "synthetic_unknown"),
    "float": (op(shape={"m": 2.0, "k": 3, "n": 5}), "shape.m"),
    "true": (op(ext={"synthetic": True}), "ext.synthetic"),
    "none": (op(dtype=None), "dtype"),
    "empty ext": (op(ext={}), "ext"),
    "schema_version 2": (op(schema_version=2), "schema_version"),
    "not a mapping": ("synthetic", "record"),
}


def compact(record):
    return json.dumps(record, separators=(",", ":")).encode()


def corrupt_contents(record, nested, example):
    valid = compact(record)
    duplicate = nested.encode()
    assert valid.count(duplicate) == 1
    return {
        "empty": b"",
        "not utf-8": b"\xff\xfe" + valid,
        "not json": valid[:-1],
        "array": b"[" + valid + b"]",
        "string": b'"synthetic"',
        "repeated member": b'{"schema_version":1,' + valid[1:],
        "repeated nested member": valid.replace(duplicate, duplicate * 2),
        "float": compact(dict(record, ext={"synthetic": 1.5})),
        "true": compact(dict(record, ext={"synthetic": True})),
        "null": compact(dict(record, ext={"synthetic": None})),
        "nan": compact(dict(record, ext={"synthetic": float("nan")})),
        "unknown field": compact(dict(record, synthetic_unknown=1)),
        "schema_version 2": compact(dict(record, schema_version=2)),
        "nested too deeply": b"[" * 100_000,
        "adr-0001 example": compact(dict(record, **example)),
    }


CORRUPT_HW = corrupt_contents(
    hw(), '"cpu":"synthetic cpu",', {"hw_source": PLACEHOLDER}
)
CORRUPT_OP = corrupt_contents(op(), '"m":2,', {"layout": PLACEHOLDER})


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


def files(root):
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if not path.is_dir()
    )


def place(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_store_hw_profile_creates_exactly_the_record_file(root):
    record = hw(label="synthetic label", ext={"synthetic_rev": 7})

    result = store_hw_profile(root, record)

    key = keys.hw_profile_key(record)
    assert result == Stored(key, True)
    assert (result.key, result.created) == (key, True)
    assert files(root) == [f"db/{key.name}/hw_profile.json"]
    assert root / f"db/{key.name}/hw_profile.json" == layout.hw_profile_record(
        root, key.name
    )
    assert load_hw_profile(root, key.name) == record


def test_store_op_signature_creates_exactly_the_record_file(root):
    record = op(label="synthetic label", ext={"synthetic_variant": "a"})
    store_hw_profile(root, hw())

    result = store_op_signature(root, HW_NAME, record)

    key = keys.op_signature_key(record)
    assert result == Stored(key, True)
    assert files(root) == sorted(
        [HW_FILE, f"db/{HW_NAME}/{key.name}/op_signature.json"]
    )
    assert load_op_signature(root, HW_NAME, key.name) == record
    assert load_hw_profile(root, HW_NAME) == hw()


def test_lookup_returns_both_keys_of_a_stored_pair(root):
    store_hw_profile(root, hw())
    store_op_signature(root, HW_NAME, op())

    found = lookup(root, hw(), op())

    assert found == (keys.hw_profile_key(hw()), keys.op_signature_key(op()))
    assert found[0].canonical == keys.hw_profile_key(hw()).canonical
    assert found[1].canonical == keys.op_signature_key(op()).canonical
    assert (found[0].name, found[1].name) == (HW_NAME, OP_NAME)


def test_lookup_ignores_attributes(root):
    store_hw_profile(root, hw(label="stored label"))
    store_op_signature(root, HW_NAME, op(label="stored label"))

    found = lookup(root, hw(hw_source="external"), op(label="other label"))

    assert found == (keys.hw_profile_key(hw()), keys.op_signature_key(op()))


def test_written_files_are_utf8_json_with_lf_and_one_final_newline(root):
    store_hw_profile(root, hw(label="synthetic label"))
    store_op_signature(root, HW_NAME, op(label="synthetic label"))

    for relative, record in ((HW_FILE, hw()), (OP_FILE, op())):
        data = (root / relative).read_bytes()
        assert b"\r" not in data
        assert data.endswith(b"\n") and not data.endswith(b"\n\n")
        assert json.loads(data.decode("utf-8")) == dict(record, label="synthetic label")


def test_the_same_record_gives_the_same_bytes_whatever_its_member_order(root, tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    store_hw_profile(root, hw())
    store_hw_profile(other, dict(reversed(hw().items())))

    assert (other / HW_FILE).read_bytes() == (root / HW_FILE).read_bytes()


def test_record_arguments_are_not_modified(root):
    hw_record, op_record = hw(label="synthetic"), op(ext={"synthetic": 1})
    hw_before, op_before = copy.deepcopy(hw_record), copy.deepcopy(op_record)

    store_hw_profile(root, hw_record)
    store_op_signature(root, HW_NAME, op_record)
    lookup(root, hw_record, op_record)

    assert (hw_record, op_record) == (hw_before, op_before)


def test_read_only_mappings_are_stored_as_json_objects(root):
    hw_record = MappingProxyType(
        hw(
            host=MappingProxyType(hw()["host"]),
            toolchain=MappingProxyType(hw()["toolchain"]),
        )
    )
    op_record = MappingProxyType(op(shape=MappingProxyType(op()["shape"])))

    assert store_hw_profile(root, hw_record).created is True
    assert store_op_signature(root, HW_NAME, op_record).created is True

    stored = load_hw_profile(root, HW_NAME)
    assert stored == hw()
    assert type(stored) is dict and type(stored["host"]) is dict
    assert load_op_signature(root, HW_NAME, OP_NAME) == op()
    assert lookup(root, hw_record, op_record) is not None


def test_storing_the_same_record_twice_keeps_the_file(root):
    store_hw_profile(root, hw())
    store_op_signature(root, HW_NAME, op())
    for relative in (HW_FILE, OP_FILE):
        os.utime(root / relative, (1_000_000_000, 1_000_000_000))
    before = snapshot(root)

    assert store_hw_profile(root, hw()) == Stored(keys.hw_profile_key(hw()), False)
    assert store_op_signature(root, HW_NAME, op()) == Stored(
        keys.op_signature_key(op()), False
    )

    assert snapshot(root) == before
    assert (root / HW_FILE).stat().st_mtime == 1_000_000_000


def test_a_different_attribute_does_not_change_the_stored_record(root):
    store_hw_profile(root, hw(label="first"))
    store_op_signature(root, HW_NAME, op(label="first"))
    before = snapshot(root)

    assert store_hw_profile(root, hw(label="second")).created is False
    assert store_hw_profile(root, hw(hw_source="external")).created is False
    assert store_op_signature(root, HW_NAME, op(label="second")).created is False
    assert store_op_signature(root, HW_NAME, op()).created is False

    assert snapshot(root) == before
    assert load_hw_profile(root, HW_NAME) == hw(label="first")
    assert load_op_signature(root, HW_NAME, OP_NAME) == op(label="first")


def test_a_key_directory_without_its_record_file_is_not_stored(root):
    (root / "db" / HW_NAME).mkdir(parents=True)

    with pytest.raises(KeyRecordNotFoundError, match=HW_FILE):
        load_hw_profile(root, HW_NAME)
    assert lookup(root, hw(), op()) is None
    assert store_hw_profile(root, hw()).created is True
    assert load_hw_profile(root, HW_NAME) == hw()

    (root / "db" / HW_NAME / OP_NAME).mkdir()
    with pytest.raises(KeyRecordNotFoundError, match=OP_FILE):
        load_op_signature(root, HW_NAME, OP_NAME)
    assert lookup(root, hw(), op()) is None
    assert store_op_signature(root, HW_NAME, op()).created is True
    assert files(root) == sorted([HW_FILE, OP_FILE])


@pytest.mark.parametrize(
    "form",
    [
        lambda record: json.dumps(record, separators=(",", ":")),
        lambda record: json.dumps(dict(reversed(record.items()))),
        lambda record: json.dumps(record, indent=4).replace("\n", "\r\n") + "\r\n",
    ],
    ids=["compact", "other member order", "crlf"],
)
def test_any_json_text_of_a_valid_record_is_read(root, form):
    place(root, HW_FILE, form(hw(label="by hand")).encode())
    place(root, OP_FILE, form(op(label="by hand")).encode())
    before = snapshot(root)

    assert load_hw_profile(root, HW_NAME) == hw(label="by hand")
    assert load_op_signature(root, HW_NAME, OP_NAME) == op(label="by hand")
    assert lookup(root, hw(), op()) is not None
    assert store_hw_profile(root, hw()).created is False
    assert store_op_signature(root, HW_NAME, op()).created is False
    assert snapshot(root) == before


def test_lookup_misses(root):
    other_m = op(shape={"m": 32, "k": 3, "n": 5})
    assert lookup(root, hw(), op()) is None

    store_hw_profile(root, hw())
    assert lookup(root, hw(), op()) is None

    store_op_signature(root, HW_NAME, op())
    before = snapshot(root)
    assert lookup(root, hw(), other_m) is None
    assert lookup(root, hw(revision="synthetic-r2"), op()) is None
    assert lookup(root, hw(), op()) is not None
    assert snapshot(root) == before


def test_lookup_misses_when_only_the_op_signature_is_stored(root):
    place(root, OP_FILE, compact(op()))

    assert lookup(root, hw(), op()) is None


def test_two_op_signatures_below_one_hw_profile_are_independent(root):
    other = op(shape={"m": 32, "k": 3, "n": 5}, label="synthetic m=32")
    other_name = keys.op_signature_key(other).name
    store_hw_profile(root, hw())

    assert store_op_signature(root, HW_NAME, op()).created is True
    assert store_op_signature(root, HW_NAME, other).created is True

    assert other_name != OP_NAME
    assert load_op_signature(root, HW_NAME, OP_NAME) == op()
    assert load_op_signature(root, HW_NAME, other_name) == other
    assert lookup(root, hw(), other)[1].name == other_name
    assert files(root) == sorted(
        [HW_FILE, OP_FILE, f"db/{HW_NAME}/{other_name}/op_signature.json"]
    )


def test_one_op_signature_below_two_hw_profiles(root):
    other_hw = hw(revision="synthetic-r2")
    other_name = keys.hw_profile_key(other_hw).name
    store_hw_profile(root, hw())
    store_hw_profile(root, other_hw)

    store_op_signature(root, other_name, op())

    assert lookup(root, other_hw, op()) is not None
    assert lookup(root, hw(), op()) is None


def test_data_root_as_str_and_as_path(root):
    assert store_hw_profile(str(root), hw()).created is True
    assert store_hw_profile(root, hw()).created is False
    assert store_op_signature(str(root), HW_NAME, op()).created is True
    assert store_op_signature(root, HW_NAME, op()).created is False
    assert load_hw_profile(str(root), HW_NAME) == load_hw_profile(root, HW_NAME)
    assert load_op_signature(str(root), HW_NAME, OP_NAME) == op()
    assert lookup(str(root), hw(), op()) == lookup(root, hw(), op())
    assert files(root) == sorted([HW_FILE, OP_FILE])


def test_lookup_reads_only_the_two_record_files(root):
    store_hw_profile(root, hw())
    store_op_signature(root, HW_NAME, op())
    place(root, f"db/{HW_NAME}/{OP_NAME}/best.json", b"\xff not json")
    place(root, f"db/{HW_NAME}/{OP_NAME}/technique_stats.json", b"")
    before = snapshot(root)

    assert lookup(root, hw(), op()) is not None
    assert snapshot(root) == before


def test_other_files_of_the_tree_are_left_alone(root):
    place(root, "db/.gitkeep", b"")
    place(root, "runs/.gitkeep", b"")
    place(root, "unrelated.txt", b"keep")

    store_hw_profile(root, hw())
    store_op_signature(root, HW_NAME, op())

    assert files(root) == sorted(
        [HW_FILE, OP_FILE, "db/.gitkeep", "runs/.gitkeep", "unrelated.txt"]
    )
    assert (root / "unrelated.txt").read_bytes() == b"keep"


@pytest.mark.parametrize("case", INVALID_HW)
def test_invalid_hw_profile_record_is_rejected(root, tmp_path, case):
    record, field = INVALID_HW[case]
    before = snapshot(tmp_path)

    with pytest.raises(keys.InvalidRecordError, match=field):
        store_hw_profile(root, record)
    with pytest.raises(keys.InvalidRecordError, match=field):
        lookup(root, record, op())
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("case", INVALID_OP)
def test_invalid_op_signature_record_is_rejected(root, tmp_path, case):
    record, field = INVALID_OP[case]
    store_hw_profile(root, hw())
    before = snapshot(tmp_path)

    with pytest.raises(keys.InvalidRecordError, match=field):
        store_op_signature(root, HW_NAME, record)
    with pytest.raises(keys.InvalidRecordError, match=field):
        lookup(root, hw(), record)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("name", BAD_NAMES)
def test_invalid_hw_profile_key_name_is_rejected(root, tmp_path, name):
    store_hw_profile(root, hw())
    before = snapshot(tmp_path)
    calls = [
        lambda: load_hw_profile(root, name),
        lambda: load_op_signature(root, name, OP_NAME),
        lambda: store_op_signature(root, name, op()),
    ]

    for call in calls:
        with pytest.raises(layout.InvalidPathValueError, match=r"^hw_profile_key: "):
            call()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("name", BAD_NAMES)
def test_invalid_op_signature_name_is_rejected(root, tmp_path, name):
    store_hw_profile(root, hw())
    before = snapshot(tmp_path)

    with pytest.raises(layout.InvalidPathValueError, match=r"^op_signature: "):
        load_op_signature(root, HW_NAME, name)
    assert snapshot(tmp_path) == before


def every_call(data_root):
    return [
        lambda: store_hw_profile(data_root, hw()),
        lambda: store_op_signature(data_root, HW_NAME, op()),
        lambda: load_hw_profile(data_root, HW_NAME),
        lambda: load_op_signature(data_root, HW_NAME, OP_NAME),
        lambda: lookup(data_root, hw(), op()),
    ]


def test_a_data_root_that_does_not_exist(tmp_path):
    absent = tmp_path / "typo" / "data"

    for call in every_call(absent):
        with pytest.raises(FileNotFoundError, match="data root"):
            call()
    assert list(tmp_path.iterdir()) == []


def test_a_data_root_that_is_a_regular_file(tmp_path):
    root_file = tmp_path / "data"
    root_file.write_bytes(b"not a directory")
    before = snapshot(tmp_path)

    for call in every_call(root_file):
        with pytest.raises(NotADirectoryError, match="data root"):
            call()
    assert snapshot(tmp_path) == before


def test_loading_a_record_that_is_not_stored(root, tmp_path):
    with pytest.raises(KeyRecordNotFoundError, match=HW_FILE) as caught:
        load_hw_profile(root, HW_NAME)
    assert isinstance(caught.value, LookupError)
    assert not isinstance(caught.value, OSError)
    with pytest.raises(KeyRecordNotFoundError, match=OP_FILE):
        load_op_signature(root, HW_NAME, OP_NAME)

    store_hw_profile(root, hw())
    before = snapshot(tmp_path)
    with pytest.raises(KeyRecordNotFoundError, match=OP_FILE):
        load_op_signature(root, HW_NAME, OP_NAME)
    assert snapshot(tmp_path) == before


def test_store_op_signature_needs_a_stored_hw_profile(root, tmp_path):
    with pytest.raises(KeyRecordNotFoundError, match=HW_FILE):
        store_op_signature(root, HW_NAME, op())
    assert list(root.iterdir()) == []

    (root / "db" / HW_NAME).mkdir(parents=True)
    before = snapshot(tmp_path)
    with pytest.raises(KeyRecordNotFoundError, match=HW_FILE):
        store_op_signature(root, HW_NAME, op())
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("case", ["empty", "not json", "unknown field"])
def test_store_op_signature_below_a_corrupt_hw_profile(root, tmp_path, case):
    place(root, HW_FILE, CORRUPT_HW[case])
    before = snapshot(tmp_path)

    with pytest.raises(CorruptKeyRecordError, match=HW_FILE):
        store_op_signature(root, HW_NAME, op())
    assert snapshot(tmp_path) == before


def test_hw_profile_record_in_the_directory_of_another_key(root, tmp_path):
    other = hw(revision="synthetic-r2")
    other_name = keys.hw_profile_key(other).name
    relative = f"db/{other_name}/hw_profile.json"
    place(root, relative, compact(hw()))
    before = snapshot(tmp_path)
    calls = [
        lambda: store_hw_profile(root, other),
        lambda: lookup(root, other, op()),
        lambda: load_hw_profile(root, other_name),
        lambda: store_op_signature(root, other_name, op()),
    ]

    for call in calls:
        with pytest.raises(KeyCollisionError, match=relative) as caught:
            call()
        assert "ADR-0001 decision 3" in str(caught.value)
    assert snapshot(tmp_path) == before


def test_op_signature_record_in_the_directory_of_another_key(root, tmp_path):
    other = op(shape={"m": 32, "k": 3, "n": 5})
    other_name = keys.op_signature_key(other).name
    relative = f"db/{HW_NAME}/{other_name}/op_signature.json"
    store_hw_profile(root, hw())
    place(root, relative, compact(op()))
    before = snapshot(tmp_path)
    calls = [
        lambda: store_op_signature(root, HW_NAME, other),
        lambda: lookup(root, hw(), other),
        lambda: load_op_signature(root, HW_NAME, other_name),
    ]

    for call in calls:
        with pytest.raises(KeyCollisionError, match=relative) as caught:
            call()
        assert "ADR-0001 decision 3" in str(caught.value)
    assert snapshot(tmp_path) == before


def test_collision_message_names_both_digests(root):
    other = hw(revision="synthetic-r2")
    other_key = keys.hw_profile_key(other)
    place(root, f"db/{other_key.name}/hw_profile.json", compact(hw()))

    with pytest.raises(KeyCollisionError) as caught:
        store_hw_profile(root, other)

    message = str(caught.value)
    assert keys.hw_profile_key(hw()).digest in message
    assert other_key.digest in message
    assert not isinstance(caught.value, (ValueError, LookupError, OSError))


@pytest.mark.parametrize("case", CORRUPT_HW)
def test_corrupt_hw_profile_file(root, tmp_path, case):
    place(root, HW_FILE, CORRUPT_HW[case])
    before = snapshot(tmp_path)
    calls = [
        lambda: load_hw_profile(root, HW_NAME),
        lambda: store_hw_profile(root, hw()),
        lambda: lookup(root, hw(), op()),
    ]

    for call in calls:
        with pytest.raises(CorruptKeyRecordError, match=HW_FILE):
            call()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("case", CORRUPT_OP)
def test_corrupt_op_signature_file(root, tmp_path, case):
    store_hw_profile(root, hw())
    place(root, OP_FILE, CORRUPT_OP[case])
    before = snapshot(tmp_path)
    calls = [
        lambda: load_op_signature(root, HW_NAME, OP_NAME),
        lambda: store_op_signature(root, HW_NAME, op()),
        lambda: lookup(root, hw(), op()),
    ]

    for call in calls:
        with pytest.raises(CorruptKeyRecordError, match=OP_FILE):
            call()
    assert snapshot(tmp_path) == before


def test_a_record_of_the_other_kind_is_corrupt(root):
    place(root, HW_FILE, compact(op()))

    with pytest.raises(CorruptKeyRecordError, match="unknown field"):
        load_hw_profile(root, HW_NAME)


def test_corrupt_error_names_the_rule_and_does_not_dump_the_file(root):
    place(root, HW_FILE, compact(hw(label="x" * 100_000)))

    with pytest.raises(CorruptKeyRecordError) as caught:
        load_hw_profile(root, HW_NAME)

    message = str(caught.value)
    assert message.startswith(f"{HW_FILE}: must be UTF-8 JSON of a valid record")
    assert "label" in message
    assert len(message) < 400
    assert isinstance(caught.value.__cause__, keys.InvalidRecordError)
    assert not isinstance(caught.value, (ValueError, LookupError, OSError))


def test_a_record_file_path_that_is_a_directory(root, tmp_path):
    (root / HW_FILE).mkdir(parents=True)
    before = snapshot(tmp_path)
    calls = [
        lambda: load_hw_profile(root, HW_NAME),
        lambda: store_hw_profile(root, hw()),
        lambda: lookup(root, hw(), op()),
        lambda: store_op_signature(root, HW_NAME, op()),
    ]

    for call in calls:
        with pytest.raises(CorruptKeyRecordError, match=HW_FILE):
            call()
    assert snapshot(tmp_path) == before


def test_a_record_file_that_is_a_symbolic_link_is_not_followed(root, tmp_path):
    target = tmp_path / "outside.json"
    target.write_bytes(compact(hw()))
    (root / "db" / HW_NAME).mkdir(parents=True)
    try:
        (root / HW_FILE).symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")

    with pytest.raises(CorruptKeyRecordError, match="not a regular file"):
        load_hw_profile(root, HW_NAME)
    with pytest.raises(CorruptKeyRecordError, match="not a regular file"):
        store_hw_profile(root, hw())
    assert target.read_bytes() == compact(hw())


@pytest.mark.parametrize("occupied", ["db", f"db/{HW_NAME}"])
def test_a_file_in_the_place_of_a_directory(root, tmp_path, occupied):
    place(root, occupied, b"not a directory")
    before = snapshot(tmp_path)

    with pytest.raises(OSError):
        store_hw_profile(root, hw())
    with pytest.raises(KeyRecordNotFoundError):
        load_hw_profile(root, HW_NAME)
    assert lookup(root, hw(), op()) is None
    assert snapshot(tmp_path) == before


def test_a_failing_write_leaves_nothing_behind(root, tmp_path, monkeypatch):
    synced = []

    def failing_fsync(descriptor):
        synced.append(descriptor)
        raise OSError("injected failure")

    monkeypatch.setattr(key_records.os, "fsync", failing_fsync)
    with pytest.raises(OSError, match="injected failure"):
        store_hw_profile(root, hw())
    assert len(synced) == 1
    assert list(root.iterdir()) == []

    (root / "db").mkdir()
    place(root, "db/.gitkeep", b"")
    with pytest.raises(OSError, match="injected failure"):
        store_hw_profile(root, hw())
    assert files(root) == ["db/.gitkeep"]
    assert sorted(path.name for path in (root / "db").iterdir()) == [".gitkeep"]

    monkeypatch.undo()
    assert store_hw_profile(root, hw()).created is True
    before = snapshot(tmp_path)

    monkeypatch.setattr(key_records.os, "fsync", failing_fsync)
    with pytest.raises(OSError, match="injected failure"):
        store_op_signature(root, HW_NAME, op())
    assert snapshot(tmp_path) == before

    monkeypatch.undo()
    assert store_op_signature(root, HW_NAME, op()).created is True
    assert lookup(root, hw(), op()) is not None


def test_a_failing_write_keeps_a_key_directory_that_already_existed(root, monkeypatch):
    (root / "db" / HW_NAME).mkdir(parents=True)

    def failing_fsync(descriptor):
        raise OSError("injected failure")

    monkeypatch.setattr(key_records.os, "fsync", failing_fsync)
    with pytest.raises(OSError, match="injected failure"):
        store_hw_profile(root, hw())

    assert [path.name for path in (root / "db").iterdir()] == [HW_NAME]
    assert list((root / "db" / HW_NAME).iterdir()) == []


def test_module_defines_no_other_public_name_and_no_entry_point():
    defined = {
        name
        for name, value in vars(key_records).items()
        if getattr(value, "__module__", None) == key_records.__name__
        and not name.startswith("_")
    }
    assert defined == {
        "CorruptKeyRecordError",
        "KeyCollisionError",
        "KeyRecordNotFoundError",
        "Stored",
        "load_hw_profile",
        "load_op_signature",
        "lookup",
        "store_hw_profile",
        "store_op_signature",
    }
