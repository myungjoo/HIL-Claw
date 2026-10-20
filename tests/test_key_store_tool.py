import errno
import io
import json
import os
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    case_tool,
    key_records,
    key_store_tool,
    keys,
    layout,
    mcp_front,
    once_write,
    run_admission,
    run_file_tools,
    tools,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
INSTANCE_PATH = f"runs/{RUN}/instance.json"


def hw(**changes):
    record = {
        "schema_version": 1,
        "accelerator": "synthetic_hw",
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    return record | changes


def op(**changes):
    record = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }
    return record | changes


HW_KEY = keys.hw_profile_key(hw())
OP_KEY = keys.op_signature_key(op())
HW_FILE = f"db/{HW_KEY.name}/hw_profile.json"
OP_FILE = f"db/{HW_KEY.name}/{OP_KEY.name}/op_signature.json"


def instance_document(with_op=True):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": HW_KEY.name, "record": hw()},
    }
    if with_op:
        document["op_signature"] = {"key": OP_KEY.name, "record": op()}
    return document


def encoded(document):
    return (json.dumps(document, indent=2) + "\n").encode()


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class Source:
    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.root


class FailingSource:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise RuntimeError("no data root in this test")


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    yield directory
    assert not list(tmp_path.rglob("events.ndjson"))


def instance_path(root):
    return layout.run_file(root, RUN, "instance.json")


def hw_path(root):
    return layout.hw_profile_record(root, HW_KEY.name)


def op_path(root):
    return layout.op_signature_file(root, HW_KEY.name, OP_KEY.name, "op_signature.json")


def run(root, with_op=True):
    place(instance_path(root), encoded(instance_document(with_op)))


def request(**changes):
    return {"run_id": RUN} | changes


def store(source, body=None):
    return key_store_tool.definition(source).function(
        request() if body is None else body
    )


def tree(root):
    found = {}
    for directory, _, files in os.walk(root):
        here = Path(directory)
        found[here.relative_to(root).as_posix()] = None
        for name in files:
            path = here / name
            with open(path, "rb") as file:
                found[path.relative_to(root).as_posix()] = file.read()
    return found


def refused(root, body=None, source=None):
    before = tree(root)
    with pytest.raises(ToolFailure) as failure:
        store(source or Source(root), body)
    assert tree(root) == before
    return failure.value


def failed(root, body=None, source=None):
    with pytest.raises(ToolFailure) as failure:
        store(source or Source(root), body)
    return failure.value


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = key_store_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == key_store_tool.NAME == "key.store"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
        },
        "required": ["run_id"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert key_store_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="callable"):
        key_store_tool.definition(source)


KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_invalid",
    "run_file_unsupported",
    "run_file_unreadable",
    "op_signature_not_stated",
    "key_record_invalid",
    "key_not_written",
)


def test_the_description_names_every_kind_in_order():
    description = key_store_tool.definition(lambda: None).description
    places = [description.index(kind) for kind in KINDS]
    assert places == sorted(places)
    assert (
        '{"hw_profile_created": true or false, "op_signature_created": true or false}'
        in description
    )
    assert "never part of the request" in description


def test_the_kinds_are_those_of_the_record():
    assert key_store_tool.KIND_KEY_NOT_WRITTEN == "key_not_written"
    assert key_store_tool.KIND_OP_SIGNATURE_NOT_STATED == "op_signature_not_stated"
    assert (
        key_store_tool.KIND_OP_SIGNATURE_NOT_STATED
        is run_admission.KIND_OP_SIGNATURE_NOT_STATED
    )
    assert key_store_tool.KIND_KEY_RECORD_INVALID is case_tool.KIND_KEY_RECORD_INVALID


# Happy paths (ADR-0134 Walk-through)


def test_a_fresh_key_creates_both_files(root):
    run(root)
    source = Source(root)
    instance = instance_path(root).read_bytes()
    assert key_store_tool.definition(source).function(request()) == {
        "hw_profile_created": True,
        "op_signature_created": True,
    }
    assert source.calls == 1
    assert hw_path(root).is_file()
    assert op_path(root).is_file()
    assert key_records.lookup(root, hw(), op()) == (HW_KEY, OP_KEY)
    assert key_records.load_hw_profile(root, HW_KEY.name) == hw()
    assert key_records.load_op_signature(root, HW_KEY.name, OP_KEY.name) == op()
    assert instance_path(root).read_bytes() == instance


def test_a_second_call_creates_nothing_and_changes_nothing(root):
    run(root)
    store(Source(root))
    before = tree(root)
    assert store(Source(root)) == {
        "hw_profile_created": False,
        "op_signature_created": False,
    }
    assert tree(root) == before


@pytest.mark.parametrize(
    "stored", [hw(hw_source="external"), hw(label="another label")]
)
def test_a_key_stored_with_other_attributes_is_kept_as_it_is(root, stored):
    run(root)
    key_records.store_hw_profile(root, stored)
    key_records.store_op_signature(root, HW_KEY.name, op(label="stored label"))
    before = tree(root)
    assert store(Source(root)) == {
        "hw_profile_created": False,
        "op_signature_created": False,
    }
    assert tree(root) == before
    assert key_records.load_hw_profile(root, HW_KEY.name) == stored
    assert json.loads(instance_path(root).read_bytes()) == instance_document()


def test_a_stored_hw_profile_without_op_signature_creates_the_op_signature(root):
    run(root)
    key_records.store_hw_profile(root, hw())
    stored = hw_path(root).read_bytes()
    assert store(Source(root)) == {
        "hw_profile_created": False,
        "op_signature_created": True,
    }
    assert hw_path(root).read_bytes() == stored
    assert op_path(root).is_file()


def hypotheses_document():
    basis = {
        "kind": "attempt",
        "ref": {"round": 0, "candidate": 1, "attempt": 1},
        "text": "the baseline",
    }
    return {
        "schema_version": 1,
        "run_id": RUN,
        "round": 1,
        "candidates": 1,
        "hypotheses": [
            {
                "id": "h1",
                "statement": "h1 lowers latency",
                "basis": [basis],
                "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
                "origin": "system",
                "tested_by": [1],
            }
        ],
    }


def test_a_case_write_after_the_store_finds_the_key(root):
    run(root)
    state = {
        "schema_version": 1,
        "round": 1,
        "budget_spent": {"totals": {}, "position": 0, "open_steps": []},
    }
    place(layout.run_file(root, RUN, "STATE.json"), encoded(state))
    place(layout.hypothesis_record(root, RUN, 1), encoded(hypotheses_document()))
    write = case_tool.definition(Source(root)).function
    with pytest.raises(ToolFailure) as failure:
        write(request(round=1))
    assert failure.value.kind == "key_not_stored"
    store(Source(root))
    assert write(request(round=1)) == {"with_verdicts": False}
    assert layout.case_record(root, HW_KEY.name, OP_KEY.name, RUN, 1).is_file()


def test_the_tool_answers_through_the_registry(root):
    run(root)
    registry = default_registry(Source(root))
    assert tools.call(registry, "key.store", request()) == {
        "hw_profile_created": True,
        "op_signature_created": True,
    }
    assert mcp_front.mcp_names(registry)["key_store"] == "key.store"


def test_the_tool_answers_by_its_mcp_name(root):
    run(root)
    params = {"name": "key_store", "arguments": request()}
    data = (
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
        )
        + "\n"
    ).encode()
    stdout = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(Source(root)),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0
    result = json.loads(stdout.getvalue())["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {
        "hw_profile_created": True,
        "op_signature_created": True,
    }
    assert op_path(root).is_file()


# Negative requests


@pytest.mark.parametrize(
    "body",
    [
        request(extra=1),
        request(round=1),
        {},
        {"round": 1},
        request(run_id="Bad Run"),
        request(run_id=""),
        request(run_id="../x"),
        request(run_id=3),
        request(run_id=None),
    ],
)
def test_a_request_that_is_not_exactly_run_id_is_invalid(root, body):
    run(root)
    source = Source(root)
    failure = refused(root, body, source)
    assert failure.kind == "invalid_request"
    assert source.calls == 0


def test_an_extra_member_is_named(root):
    failure = refused(root, request(zeta=1, alpha=2))
    assert "not 'alpha', 'zeta'" in failure.message


def test_a_missing_run_id_is_named(root):
    assert "lacks the member run_id" in refused(root, {}).message


# Every kind, in order


def test_no_data_root(root):
    run(root)
    source = FailingSource()
    failure = refused(root, source=source)
    assert failure.kind == "no_data_root"
    assert source.calls == 1


def test_a_missing_instance_is_run_file_missing(root):
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(INSTANCE_PATH)


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{", "run_file_invalid"),
        (encoded({"schema_version": 1}), "run_file_invalid"),
        (encoded(instance_document() | {"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_an_instance_that_cannot_be_used_is_its_kind(root, content, kind):
    place(instance_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(INSTANCE_PATH)


def test_a_directory_in_the_place_of_the_instance_is_run_file_invalid(root):
    instance_path(root).mkdir(parents=True)
    failure = refused(root)
    assert failure.kind == "run_file_invalid"


def test_an_unreadable_instance_is_run_file_unreadable(root, monkeypatch):
    run(root)
    original = Path.read_bytes

    def read_bytes(path):
        if path.name == "instance.json":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original(path)

    before = tree(root)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ToolFailure) as failure:
        store(Source(root))
    monkeypatch.undo()
    assert failure.value.kind == "run_file_unreadable"
    assert failure.value.message.startswith(INSTANCE_PATH)
    assert tree(root) == before


def test_an_instance_without_op_signature_stores_nothing(root):
    run(root, with_op=False)
    failure = refused(root)
    assert failure.kind == "op_signature_not_stated"
    assert failure.message.startswith(INSTANCE_PATH)
    assert not (root / "db").exists()


def corrupt(path, content=b"not json"):
    place(path, content)


def colliding_hw(root):
    other = hw(revision="another-r2")
    place(hw_path(root), json.dumps(other).encode())


@pytest.mark.parametrize("damage", ["corrupt", "colliding", "directory"])
def test_an_invalid_stored_hw_profile_is_key_record_invalid(root, damage):
    run(root)
    if damage == "corrupt":
        corrupt(hw_path(root))
    elif damage == "colliding":
        colliding_hw(root)
    else:
        hw_path(root).mkdir(parents=True)
    failure = refused(root)
    assert failure.kind == "key_record_invalid"
    assert failure.message.startswith(HW_FILE)
    assert not op_path(root).parent.exists()


@pytest.mark.parametrize("damage", ["corrupt", "colliding"])
def test_an_invalid_stored_op_signature_is_key_record_invalid(root, damage):
    run(root)
    key_records.store_hw_profile(root, hw())
    if damage == "corrupt":
        corrupt(op_path(root))
    else:
        place(op_path(root), json.dumps(op(dtype="another_dtype")).encode())
    failure = refused(root)
    assert failure.kind == "key_record_invalid"
    assert failure.message.startswith(OP_FILE)


def test_a_refusal_at_the_op_signature_keeps_the_hw_profile_created(root):
    run(root)
    corrupt(op_path(root))
    failure = failed(root)
    assert failure.kind == "key_record_invalid"
    assert key_records.load_hw_profile(root, HW_KEY.name) == hw()


def failing_write(monkeypatch, name):
    original = once_write.write_once

    def write_once(path, content):
        if path.name == name:
            raise OSError(errno.EIO, "Input/output error", str(path))
        return original(path, content)

    monkeypatch.setattr(once_write, "write_once", write_once)


def test_a_failing_write_of_the_hw_profile_is_key_not_written(root, monkeypatch):
    run(root)
    failing_write(monkeypatch, "hw_profile.json")
    failure = refused(root)
    assert failure.kind == "key_not_written"
    assert failure.message == f"{HW_FILE}: was not written: OSError: Input/output error"
    assert str(root) not in failure.message


def test_a_failing_write_of_the_op_signature_keeps_the_hw_profile(root, monkeypatch):
    run(root)
    failing_write(monkeypatch, "op_signature.json")
    failure = failed(root)
    assert failure.kind == "key_not_written"
    assert failure.message.startswith(f"{OP_FILE}: was not written: OSError")
    assert key_records.load_hw_profile(root, HW_KEY.name) == hw()
    assert not op_path(root).exists()
    monkeypatch.undo()
    assert store(Source(root)) == {
        "hw_profile_created": False,
        "op_signature_created": True,
    }


def test_a_name_taken_and_free_again_is_key_not_written(root, monkeypatch):
    run(root)

    def write_once(path, content):
        return FileExistsError(errno.EEXIST, "File exists", str(path))

    monkeypatch.setattr(once_write, "write_once", write_once)
    failure = failed(root)
    assert failure.kind == "key_not_written"
    assert (
        failure.message == f"{HW_FILE}: was not written: FileExistsError: File exists"
    )


def test_an_unreadable_stored_record_is_key_not_written(root, monkeypatch):
    run(root)
    key_records.store_hw_profile(root, hw())
    original = Path.read_bytes

    def read_bytes(path):
        if path.name == "hw_profile.json":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original(path)

    before = tree(root)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ToolFailure) as failure:
        store(Source(root))
    monkeypatch.undo()
    assert failure.value.kind == "key_not_written"
    assert failure.value.message.startswith(f"{HW_FILE}: was not written: Permission")
    assert tree(root) == before


def test_a_data_root_gone_since_it_was_obtained_is_key_not_written(root, monkeypatch):
    run(root)
    original = run_file_tools.read

    def read(data_root, run_id, name):
        found = original(data_root, run_id, name)
        shutil.rmtree(data_root)
        return found

    monkeypatch.setattr(run_file_tools, "read", read)
    failure = failed(root)
    assert failure.kind == "key_not_written"
    assert failure.message == (
        f"{HW_FILE}: was not written: FileNotFoundError: "
        "the data root is not an existing directory"
    )
    assert not root.exists()


def test_a_hw_profile_gone_since_its_store_is_key_not_written(root, monkeypatch):
    run(root)
    original = key_records.store_hw_profile

    def store_hw_profile(data_root, record):
        stored = original(data_root, record)
        hw_path(root).unlink()
        return stored

    monkeypatch.setattr(key_records, "store_hw_profile", store_hw_profile)
    failure = failed(root)
    assert failure.kind == "key_not_written"
    assert failure.message == (
        f"{OP_FILE}: was not written: {HW_FILE}: no key record is stored"
    )
    assert not op_path(root).parent.exists()


# Order


def test_invalid_request_comes_before_no_data_root(root):
    source = FailingSource()
    assert refused(root, request(extra=1), source).kind == "invalid_request"
    assert source.calls == 0


def test_a_run_file_kind_comes_before_anything_in_db(root):
    corrupt(hw_path(root))
    assert refused(root).kind == "run_file_missing"


def test_op_signature_not_stated_comes_before_a_corrupt_hw_profile(root):
    run(root, with_op=False)
    corrupt(hw_path(root))
    assert refused(root).kind == "op_signature_not_stated"


def test_no_data_root_comes_before_run_file_missing(root, tmp_path):
    assert refused(root, source=Source(tmp_path / "missing")).kind == "no_data_root"


# What is not mapped


def test_an_error_of_the_keys_module_is_not_mapped(root, monkeypatch):
    run(root)

    def store_hw_profile(data_root, record):
        raise keys.InvalidRecordError("synthetic")

    monkeypatch.setattr(key_records, "store_hw_profile", store_hw_profile)
    with pytest.raises(keys.InvalidRecordError):
        store(Source(root))
    registry = default_registry(Source(root))
    with pytest.raises(ToolFailure) as failure:
        tools.call(registry, "key.store", request())
    assert failure.value.kind == "tool_crashed"
    assert not (root / "db").exists()


def test_each_call_asks_the_source_once_and_reads_no_state(root, monkeypatch):
    run(root)
    names = []
    original = run_file_tools.read

    def read(data_root, run_id, name):
        names.append(name)
        return original(data_root, run_id, name)

    monkeypatch.setattr(run_file_tools, "read", read)
    source = Source(root)
    definition = key_store_tool.definition(source)
    definition.function(request())
    definition.function(request())
    assert source.calls == 2
    assert names == ["instance.json", "instance.json"]
    assert not layout.run_file(root, RUN, "STATE.json").exists()
