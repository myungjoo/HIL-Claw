import errno
import io
import json
import os
from pathlib import Path

import pytest

from hilclaw import catalog, catalog_tool, keys, layout, mcp_front, spec_tool, tools
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
INSTANCE_PATH = f"runs/{RUN}/instance.json"
ACCELERATOR = "synthetic_hw"
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}


def hw(**changes):
    record = {
        "schema_version": 1,
        "accelerator": ACCELERATOR,
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    return record | changes


def instance_document(hw_record=None, **changes):
    machine = hw() if hw_record is None else hw_record
    record = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "fp32",
        "layout": "row_major",
    }
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(machine).name, "record": machine},
        "op_signature": {"key": keys.op_signature_key(record).name, "record": record},
        "candidates_per_round": 1,
        "objective": OBJECTIVE,
    }
    return document | changes


def encoded(document):
    return (json.dumps(document, indent=2) + "\n").encode()


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def instance_path(root):
    return layout.run_file(root, RUN, "instance.json")


def run(root, document=None):
    place(instance_path(root), encoded(document or instance_document()))


def entry(entry_id, when="Worth trying."):
    lines = "\n".join(catalog.APPLIES_TO)
    return (
        f"# {entry_id}\n\n## Applies to\n\n{lines}\n\n## When\n\n{when}\n\n"
        f"## Guidance\n\nUse {entry_id}.\n"
    ).encode()


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
    return directory


@pytest.fixture
def shelf(tmp_path, monkeypatch):
    source = tmp_path / "catalog"
    directory = source / ACCELERATOR
    directory.mkdir(parents=True)
    monkeypatch.setattr(catalog, "SOURCE", source)
    return directory


def tree(path):
    found = {}
    for directory, _, files in os.walk(path):
        here = Path(directory)
        found[here.relative_to(path).as_posix()] = None
        for name in files:
            found[(here / name).relative_to(path).as_posix()] = (
                here / name
            ).read_bytes()
    return found


def read(source, request=None):
    _, function, _, _ = catalog_tool.definition(source)
    return function({"run_id": RUN} if request is None else request)


def refused(root, request=None, *, source=None):
    with pytest.raises(ToolFailure) as caught:
        read(Source(root) if source is None else source, request)
    return caught.value


# The definition


def test_public_names_and_documentation():
    assert catalog_tool.__doc__
    assert catalog_tool.definition.__doc__
    assert catalog_tool.NAME == "catalog.read"
    assert catalog_tool.KIND_CATALOG_UNUSABLE == spec_tool.KIND_CATALOG_UNUSABLE
    assert catalog_tool.KIND_CATALOG_UNUSABLE == "catalog_unusable"


def test_the_definition_is_a_tool_definition():
    made = catalog_tool.definition(lambda: Path("."))
    assert isinstance(made, ToolDefinition)
    name, function, description, schema = made
    assert name == "catalog.read"
    assert callable(function)
    assert "When section" in description and "catalog_unusable" in description
    assert schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}
        },
        "required": ["run_id"],
        "additionalProperties": False,
    }


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="callable"):
        catalog_tool.definition(source)


# The result


def test_every_entry_with_its_criteria_in_id_order(root, shelf):
    run(root)
    place(shelf / "tiling.md", entry("tiling", "When the matrices\n\nare large."))
    place(shelf / "loop_order.md", entry("loop_order"))
    source = Source(root)
    before = tree(root)
    assert read(source) == {
        "entries": [
            {"id": "loop_order", "when": "Worth trying."},
            {"id": "tiling", "when": "When the matrices\n\nare large."},
        ]
    }
    assert source.calls == 1
    assert tree(root) == before


def test_an_empty_directory_gives_no_entry(root, shelf):
    run(root)
    assert read(Source(root)) == {"entries": []}


def test_the_committed_catalog_of_cpu_standin(root):
    run(root, instance_document(hw(accelerator="cpu_standin")))
    result = read(Source(root))
    criteria = catalog.criteria("cpu_standin")
    assert [e["id"] for e in result["entries"]] == sorted(criteria)
    assert {e["id"]: e["when"] for e in result["entries"]} == criteria
    assert all(e["when"].strip() for e in result["entries"])


def test_the_directory_is_the_accelerator_of_the_instance(root, shelf):
    other = shelf.parent / "other_hw"
    other.mkdir()
    place(other / "fused.md", entry("fused"))
    place(shelf / "tiling.md", entry("tiling"))
    run(root, instance_document(hw(accelerator="other_hw")))
    assert read(Source(root)) == {"entries": [{"id": "fused", "when": "Worth trying."}]}


# Every kind, in order


@pytest.mark.parametrize(
    ("request_", "message"),
    [
        ({}, "the request lacks the member run_id"),
        (
            {"run_id": RUN, "round": 1},
            "the request takes the member run_id only, not 'round'",
        ),
        (
            {"run_id": RUN, "b": 1, "a": 2},
            "the request takes the member run_id only, not 'a', 'b'",
        ),
    ],
)
def test_a_request_of_other_members_is_invalid(root, request_, message):
    source = Source(root)
    failure = refused(root, request_, source=source)
    assert (failure.kind, failure.message) == ("invalid_request", message)
    assert source.calls == 0


@pytest.mark.parametrize("run_id", [3, None, "", "Run-A", "../x", "a" * 65, True])
def test_a_run_id_that_is_none_is_invalid(root, run_id):
    source = Source(root)
    failure = refused(root, {"run_id": run_id}, source=source)
    assert failure.kind == "invalid_request"
    assert failure.message.startswith("the request's ")
    assert source.calls == 0


def test_no_data_root(root, shelf):
    run(root)
    source = FailingSource()
    assert refused(root, source=source).kind == "no_data_root"
    assert source.calls == 1


def test_a_missing_instance_is_run_file_missing(root, shelf):
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(INSTANCE_PATH)
    assert tree(root) == {".": None}


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{", "run_file_invalid"),
        (encoded({"schema_version": 1}), "run_file_invalid"),
        (encoded(instance_document(schema_version=2)), "run_file_unsupported"),
    ],
)
def test_an_instance_that_cannot_be_used_is_its_kind(root, shelf, content, kind):
    place(instance_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(INSTANCE_PATH)


def test_an_unreadable_instance_is_run_file_unreadable(root, shelf, monkeypatch):
    run(root)
    original = Path.read_bytes

    def read_bytes(path):
        if path.name == "instance.json":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ToolFailure) as caught:
        read(Source(root))
    monkeypatch.undo()
    assert caught.value.kind == "run_file_unreadable"


def test_a_missing_catalog_directory_is_catalog_unusable(root, tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "SOURCE", tmp_path / "missing")
    run(root)
    failure = refused(root)
    assert failure.kind == "catalog_unusable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: the catalog directory is not there"
    )


def test_a_mock_run_has_no_catalog(root):
    run(root, instance_document(hw(accelerator="mock")))
    failure = refused(root)
    assert failure.kind == "catalog_unusable"
    assert failure.message == "catalog/mock: the catalog directory is not there"


def test_a_catalog_refused_by_its_rules_is_catalog_unusable(root, shelf):
    run(root)
    place(shelf / "tiling.md", entry("tiling"))
    place(shelf / "notes.txt", b"x")
    failure = refused(root)
    assert failure.kind == "catalog_unusable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: the catalog directory is refused: the catalog "
        "holds a file not named '<name>.md'"
    )


def test_an_empty_when_section_is_catalog_unusable(root, shelf):
    run(root)
    place(shelf / "tiling.md", entry("tiling", "  "))
    failure = refused(root)
    assert failure.kind == "catalog_unusable"
    assert failure.message.endswith("is refused: the When section is empty")


def test_a_catalog_that_cannot_be_read_is_catalog_unusable(root, shelf, monkeypatch):
    run(root)
    place(shelf / "tiling.md", entry("tiling"))

    def scandir(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(catalog.os, "scandir", scandir)
    failure = refused(root)
    monkeypatch.undo()
    assert failure.kind == "catalog_unusable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: the catalog directory cannot be read: "
        "PermissionError: Permission denied"
    )


# Order


def test_invalid_request_comes_before_no_data_root():
    source = FailingSource()
    with pytest.raises(ToolFailure) as caught:
        read(source, {"run_id": RUN, "x": 1})
    assert caught.value.kind == "invalid_request"
    assert source.calls == 0


def test_the_instance_comes_before_the_catalog(root, tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, "SOURCE", tmp_path / "missing")
    assert refused(root).kind == "run_file_missing"


def test_a_failing_call_creates_nothing(root, shelf):
    run(root)
    place(shelf / "bad.md", b"# bad\n")
    before, kept = tree(root), tree(shelf.parent)
    assert refused(root).kind == "catalog_unusable"
    assert (tree(root), tree(shelf.parent)) == (before, kept)


# The registry and the MCP front


def test_the_default_registry_holds_catalog_read(root, shelf):
    place(shelf / "tiling.md", entry("tiling"))
    run(root)
    registry = default_registry(lambda: root)
    assert "catalog.read" in registry.names()
    assert tools.call(registry, "catalog.read", {"run_id": RUN}) == {
        "entries": [{"id": "tiling", "when": "Worth trying."}]
    }


def _mcp(request_id, method, params):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return json.dumps(document).encode() + b"\n"


def test_the_mcp_front_lists_and_serves_catalog_read(root, shelf):
    place(shelf / "tiling.md", entry("tiling"))
    run(root)
    data = b"".join(
        [
            _mcp(1, "tools/list", {}),
            _mcp(
                2, "tools/call", {"name": "catalog_read", "arguments": {"run_id": RUN}}
            ),
            _mcp(3, "tools/call", {"name": "catalog_read", "arguments": {}}),
        ]
    )
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(lambda: root),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    listed, served, failed = (
        json.loads(line) for line in stdout.getvalue().splitlines()
    )
    assert "catalog_read" in [tool["name"] for tool in listed["result"]["tools"]]
    assert mcp_front.mcp_name("catalog.read") == "catalog_read"
    assert served["result"]["isError"] is False
    assert json.loads(served["result"]["content"][0]["text"]) == {
        "entries": [{"id": "tiling", "when": "Worth trying."}]
    }
    assert failed["result"]["isError"] is True
    error = json.loads(failed["result"]["content"][0]["text"])["error"]
    assert error["kind"] == "invalid_request"
