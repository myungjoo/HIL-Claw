import errno
import hashlib
import inspect
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import __main__ as command_line
from hilclaw import blob_tools, cas, config, mcp_front, tools
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

REPO_ROOT = Path(__file__).resolve().parent.parent
EMPTY = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
DATA = b"HIL-Claw blob \x00\xff\n"
DIGEST = hashlib.sha256(DATA).hexdigest()
NAMES = ("blob.fetch", "blob.push")
SCHEMA = {
    "type": "object",
    "properties": {"sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}},
    "required": ["sha256"],
    "additionalProperties": False,
}
REFUSED = [
    {},
    {"sha256": DIGEST.upper()},
    {"sha256": DIGEST[:63]},
    {"sha256": DIGEST + "0"},
    {"sha256": ""},
    {"sha256": "sha256:" + DIGEST},
    {"sha256": DIGEST + "\n"},
    {"sha256": "g" + DIGEST[1:]},
    {"sha256": " " + DIGEST[1:]},
    {"sha256": int(DIGEST[:8], 16)},
    {"sha256": None},
    {"sha256": [DIGEST]},
    {"sha256": {"sha256": DIGEST}},
    {"sha256": True},
    {"sha256": DIGEST, "run_id": "r1"},
    {"sha256": DIGEST, "round": 1},
    {"sha256": DIGEST, "candidate": 1},
    {"sha256": DIGEST, "attempt": 1},
    {"sha256": DIGEST, "execution": 1},
    {"sha256": DIGEST, "verify": False},
    {"hash": DIGEST},
    {"SHA256": DIGEST},
]


class Source:
    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.root


@pytest.fixture(params=NAMES)
def name(request):
    return request.param


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def ask(root, name, sha256):
    return tools.call(default_registry(lambda: root), name, {"sha256": sha256})


def place(root, sha256):
    path = cas.blob_path(root, sha256)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def link(path, target):
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


def tree(root):
    return sorted(
        (
            path.relative_to(root).as_posix(),
            path.is_dir(),
            None if path.is_dir() else hashlib.sha256(path.read_bytes()).hexdigest(),
        )
        for path in root.rglob("*")
    )


def only_at(target, replacement, real):
    def replaced(path, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)) and Path(path) == target:
            return replacement(path, *args, **kwargs)
        return real(path, *args, **kwargs)

    return replaced


def raising(error):
    def raise_it(*args, **kwargs):
        raise error

    return raise_it


class BrokenFile(io.BytesIO):
    def read(self, *args):
        raise OSError(errno.EIO, "Input/output error")


# The definitions


def test_the_kind_of_the_pair_is_not_a_reserved_kind():
    assert blob_tools.KIND_BLOB_UNREADABLE == "blob_unreadable"
    assert blob_tools.KIND_BLOB_UNREADABLE not in tools.RESERVED_KINDS
    assert ToolFailure(blob_tools.KIND_BLOB_UNREADABLE, "m").kind == "blob_unreadable"


def test_definitions_are_the_two_tools_with_the_schema_of_the_record(root):
    source = Source(root)
    fetch, push = blob_tools.definitions(source)
    assert isinstance(fetch, ToolDefinition) and isinstance(push, ToolDefinition)
    assert (fetch.name, push.name) == NAMES
    assert fetch.input_schema == push.input_schema == SCHEMA
    assert fetch.input_schema is not push.input_schema
    assert blob_tools.definitions(source)[0].input_schema is not fetch.input_schema
    assert callable(fetch.function) and callable(push.function)
    assert source.calls == 0


def test_each_description_says_what_the_tool_does_and_answers(root):
    fetch, push = blob_tools.definitions(lambda: root)
    assert fetch.description != push.description
    for description in (fetch.description, push.description):
        assert "local" in description and "nothing is copied" in description
        for member in ('"sha256"', '"present"', '"intact"'):
            assert member in description
        for promise in ("remote", "backup", "transfer", "upload", "download"):
            assert promise not in description.lower()


@pytest.mark.parametrize("source", [None, "data", b"data", 3, {}, Path(".")])
def test_definitions_refuse_a_source_that_is_not_callable(source):
    with pytest.raises(TypeError, match="must be callable"):
        blob_tools.definitions(source)


def test_a_tool_function_can_be_called_without_a_registry(root):
    cas.put_bytes(root, DATA)
    for definition in blob_tools.definitions(lambda: root):
        assert definition.function({"sha256": DIGEST}) == {
            "sha256": DIGEST,
            "present": True,
            "intact": True,
        }
        with pytest.raises(ToolFailure) as refused:
            definition.function({})
        assert refused.value.kind == "invalid_request"


def test_the_default_registry_holds_the_definitions(root):
    registry = default_registry(lambda: root)
    assert registry.names() == (
        *NAMES,
        "correctness.check",
        "instance.read",
        "run.fresh",
        "state.read",
        "state.write",
    )
    for held in blob_tools.definitions(lambda: root):
        assert registry.definition(held.name).description == held.description
        assert registry.definition(held.name).input_schema == SCHEMA


# Present


@pytest.mark.parametrize("size", [1, 0, cas.CHUNK_SIZE + 17, 2 * cas.CHUNK_SIZE])
def test_a_stored_blob_is_present_and_intact(root, name, size):
    digest = cas.put_bytes(root, b"\x00" * size).digest
    result = ask(root, name, digest)
    assert result == {"sha256": digest, "present": True, "intact": True}
    assert list(result) == ["sha256", "present", "intact"]
    assert result["present"] is True and result["intact"] is True


def test_the_empty_blob_of_the_walk_through(root, name):
    assert cas.put_bytes(root, b"").digest == EMPTY
    assert ask(root, name, EMPTY) == {"sha256": EMPTY, "present": True, "intact": True}


def test_a_file_whose_content_is_not_its_name_is_present_and_not_intact(root, name):
    path = place(root, EMPTY)
    path.write_bytes(b"x")
    result = ask(root, name, EMPTY)
    assert result == {"sha256": EMPTY, "present": True, "intact": False}
    assert result["intact"] is False
    assert path.read_bytes() == b"x"


def test_a_symbolic_link_to_a_regular_file_counts_as_a_file(root, name, tmp_path):
    target = tmp_path / "elsewhere"
    target.write_bytes(DATA)
    link(place(root, DIGEST), target)
    assert ask(root, name, DIGEST) == {
        "sha256": DIGEST,
        "present": True,
        "intact": True,
    }
    target.write_bytes(b"changed")
    assert ask(root, name, DIGEST)["intact"] is False


# Not there


def absent(root, name, sha256=DIGEST):
    result = ask(root, name, sha256)
    assert result == {"sha256": sha256, "present": False}
    assert list(result) == ["sha256", "present"] and result["present"] is False
    return result


def test_an_empty_data_root_holds_nothing_and_gets_nothing(root, name):
    absent(root, name)
    assert list(root.iterdir()) == []


def test_a_store_without_the_hash(root, name):
    cas.put_bytes(root, b"another blob")
    (root / "blobs" / "sha256" / DIGEST[:2]).mkdir(exist_ok=True)
    before = tree(root)
    absent(root, name)
    assert tree(root) == before


def test_a_store_without_the_directory_of_the_hash(root, name):
    (root / "blobs" / "sha256").mkdir(parents=True)
    absent(root, name)
    assert tree(root) == [("blobs", True, None), ("blobs/sha256", True, None)]


def test_a_directory_at_the_place_is_not_there(root, name):
    path = place(root, EMPTY)
    path.mkdir()
    (path / "inside").write_bytes(b"")
    before = tree(root)
    absent(root, name, EMPTY)
    assert tree(root) == before


@pytest.mark.parametrize(
    "part", ["blobs", "blobs/sha256", f"blobs/sha256/{DIGEST[:2]}"]
)
def test_a_part_of_the_path_that_is_no_directory_is_not_there(root, name, part):
    path = root / part
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(DATA)
    absent(root, name)
    assert path.read_bytes() == DATA


def test_a_symbolic_link_that_leads_nowhere_is_not_there(root, name, tmp_path):
    path = place(root, DIGEST)
    link(path, tmp_path / "missing")
    absent(root, name)
    assert path.is_symlink()


def test_a_symbolic_link_to_a_directory_is_not_there(root, name, tmp_path):
    link(place(root, DIGEST), tmp_path)
    absent(root, name)


@pytest.mark.parametrize("error", [FileNotFoundError, NotADirectoryError])
def test_a_look_that_finds_no_file_is_not_there(root, name, monkeypatch, error):
    path = cas.put_bytes(root, DATA) and cas.blob_path(root, DIGEST)
    answer = raising(error(errno.ENOENT, "no file"))
    monkeypatch.setattr(os, "stat", only_at(path, answer, os.stat))
    absent(root, name)


@pytest.mark.parametrize("error", [FileNotFoundError, NotADirectoryError])
def test_a_file_gone_between_the_look_and_the_read_is_not_there(
    root, name, monkeypatch, error
):
    cas.put_bytes(root, DATA)
    opened = []

    def gone(path, *args):
        opened.append(Path(path))
        raise error(errno.ENOENT, "gone")

    monkeypatch.setattr(blob_tools, "open", gone, raising=False)
    absent(root, name)
    assert opened == [cas.blob_path(root, DIGEST)]


def test_no_answer_is_kept_between_two_calls(root, name):
    registry = default_registry(lambda: root)
    request = {"sha256": DIGEST}
    assert tools.call(registry, name, request)["present"] is False
    cas.put_bytes(root, DATA)
    assert tools.call(registry, name, request) == {
        "sha256": DIGEST,
        "present": True,
        "intact": True,
    }
    cas.blob_path(root, DIGEST).write_bytes(b"damaged")
    assert tools.call(registry, name, request)["intact"] is False
    cas.blob_path(root, DIGEST).unlink()
    assert tools.call(registry, name, request) == {"sha256": DIGEST, "present": False}
    assert request == {"sha256": DIGEST}


# Refused requests


@pytest.mark.parametrize("request_", REFUSED, ids=repr)
def test_a_refused_request_asks_no_source_and_looks_at_nothing(
    root, name, monkeypatch, request_
):
    cas.put_bytes(root, DATA)
    source = Source(root)
    registry = default_registry(source)
    path = cas.blob_path(root, DIGEST)
    looked = raising(AssertionError("looked"))
    monkeypatch.setattr(os, "stat", only_at(path, looked, os.stat))
    monkeypatch.setattr(blob_tools, "open", raising(AssertionError("read")), False)
    sent = json.loads(json.dumps(request_))
    with pytest.raises(ToolFailure) as refused:
        tools.call(registry, name, sent)
    monkeypatch.undo()
    assert refused.value.kind == tools.KIND_INVALID_REQUEST == "invalid_request"
    assert "sha256" in refused.value.message
    assert source.calls == 0
    assert sent == request_


def test_a_refusal_names_the_members_it_does_not_take(root, name):
    request = {"sha256": DIGEST, "run_id": "r1", "attempt": 2}
    with pytest.raises(ToolFailure) as refused:
        tools.call(default_registry(lambda: root), name, request)
    assert "'attempt', 'run_id'" in refused.value.message


# The data root


def test_the_source_is_asked_once_at_each_call_and_its_answer_is_not_kept(
    root, name, tmp_path
):
    other = tmp_path / "other"
    other.mkdir()
    cas.put_bytes(root, DATA)
    source = Source(root)
    registry = default_registry(source)
    assert source.calls == 0
    assert tools.call(registry, name, {"sha256": DIGEST})["present"] is True
    assert source.calls == 1
    source.root = str(other)
    assert tools.call(registry, name, {"sha256": DIGEST})["present"] is False
    assert source.calls == 2
    assert list(other.iterdir()) == []


def test_a_source_that_raises_is_no_data_root(name):
    error = RuntimeError("no configuration")
    with pytest.raises(ToolFailure) as failed:
        tools.call(default_registry(raising(error)), name, {"sha256": DIGEST})
    assert failed.value.kind == tools.KIND_NO_DATA_ROOT == "no_data_root"
    assert failed.value.__cause__ is error


@pytest.mark.parametrize("named", ["missing", "a file", None, ""])
def test_a_source_that_names_no_existing_directory_is_no_data_root(
    tmp_path, name, named
):
    (tmp_path / "a file").write_bytes(b"")
    answer = named and str(tmp_path / named)
    with pytest.raises(ToolFailure) as failed:
        tools.call(default_registry(lambda: answer), name, {"sha256": DIGEST})
    assert failed.value.kind == "no_data_root"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a file"]


# The look or the read fails


def unreadable(root, name, error):
    with pytest.raises(ToolFailure) as failed:
        ask(root, name, DIGEST)
    assert failed.value.kind == blob_tools.KIND_BLOB_UNREADABLE
    assert failed.value.__cause__ is error
    assert DIGEST in failed.value.message
    assert type(error).__name__ in failed.value.message


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(errno.EACCES, "Permission denied"),
        OSError(errno.ELOOP, "Too many levels of symbolic links"),
        OSError(errno.EIO, "Input/output error"),
    ],
    ids=["permission", "loop", "io"],
)
@pytest.mark.parametrize("stored", [True, False], ids=["stored", "not stored"])
def test_a_failed_look_is_a_tool_failure_and_not_an_absent_blob(
    root, name, monkeypatch, error, stored
):
    if stored:
        cas.put_bytes(root, DATA)
    path = cas.blob_path(root, DIGEST)
    before = tree(root)
    monkeypatch.setattr(os, "stat", only_at(path, raising(error), os.stat))
    unreadable(root, name, error)
    monkeypatch.undo()
    assert tree(root) == before


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(errno.EACCES, "Permission denied"),
        IsADirectoryError(errno.EISDIR, "Is a directory"),
        OSError(errno.EIO, "Input/output error"),
    ],
    ids=["permission", "directory", "io"],
)
def test_a_failed_open_is_a_tool_failure(root, name, monkeypatch, error):
    cas.put_bytes(root, DATA)
    before = tree(root)
    monkeypatch.setattr(blob_tools, "open", raising(error), raising=False)
    unreadable(root, name, error)
    monkeypatch.undo()
    assert tree(root) == before


def test_a_failed_read_is_a_tool_failure_and_the_file_is_closed(
    root, name, monkeypatch
):
    cas.put_bytes(root, DATA)
    opened = []

    def broken(path, mode):
        assert mode == "rb"
        opened.append(BrokenFile(DATA))
        return opened[-1]

    monkeypatch.setattr(blob_tools, "open", broken, raising=False)
    with pytest.raises(ToolFailure) as failed:
        ask(root, name, DIGEST)
    assert failed.value.kind == "blob_unreadable"
    assert isinstance(failed.value.__cause__, OSError)
    assert [f.closed for f in opened] == [True]


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_a_file_without_read_permission_is_a_tool_failure(root, name):
    cas.put_bytes(root, DATA)
    path = cas.blob_path(root, DIGEST)
    path.chmod(0)
    try:
        if os.access(path, os.R_OK):
            pytest.skip("this account reads a file of mode 000")
        with pytest.raises(ToolFailure) as failed:
            ask(root, name, DIGEST)
        assert failed.value.kind == "blob_unreadable"
        assert isinstance(failed.value.__cause__, PermissionError)
    finally:
        path.chmod(0o600)
    assert path.read_bytes() == DATA


def test_the_content_is_read_in_chunks(root, name, monkeypatch):
    digest = cas.put_bytes(root, b"b" * (2 * cas.CHUNK_SIZE + 1)).digest
    sizes = []

    class Counted(io.FileIO):
        def read(self, size=-1):
            sizes.append(size)
            return super().read(size)

    monkeypatch.setattr(blob_tools, "open", Counted, raising=False)
    assert ask(root, name, digest)["intact"] is True
    assert sizes == [cas.CHUNK_SIZE] * 4


# A call writes nothing


def test_calls_of_every_kind_leave_the_data_root_as_it_was(root, name, monkeypatch):
    cas.put_bytes(root, DATA)
    cas.put_bytes(root, b"")
    damaged = "a" * 64
    place(root, damaged).write_bytes(b"not the content of that name")
    occupied = "b" * 64
    place(root, occupied).mkdir()
    place(root, "c" * 64).parent.rmdir()
    (root / "blobs" / "sha256" / "cc").write_bytes(b"a file, no directory")
    (root / "runs").mkdir()
    (root / "runs" / "artifacts.json").write_bytes(b"{}")
    before = tree(root)
    registry = default_registry(lambda: root)
    answers = [
        tools.call(registry, name, {"sha256": sha256})
        for sha256 in (DIGEST, EMPTY, damaged, occupied, "c" * 64, "d" * 64)
    ]
    assert [(a["present"], a.get("intact")) for a in answers] == [
        (True, True),
        (True, True),
        (True, False),
        (False, None),
        (False, None),
        (False, None),
    ]
    for request in REFUSED:
        with pytest.raises(ToolFailure):
            tools.call(registry, name, dict(request))
    error = OSError(errno.EIO, "Input/output error")
    monkeypatch.setattr(blob_tools, "open", raising(error), raising=False)
    with pytest.raises(ToolFailure):
        tools.call(registry, name, {"sha256": DIGEST})
    monkeypatch.undo()
    assert tree(root) == before


def test_the_module_imports_nothing_that_writes_or_runs():
    values = vars(blob_tools).values()
    origins = {getattr(value, "__module__", None) for value in values}
    origins |= {value.__name__ for value in values if inspect.ismodule(value)}
    assert not origins & {
        "hilclaw.artifacts",
        "hilclaw.journaled_tool",
        "hilclaw.journaled_step",
        "hilclaw.hw_tool",
        "hilclaw.backends",
        "subprocess",
    }
    assert {"hilclaw.cas", "hilclaw.tools", "os"} <= origins


# Through the command-line front


@pytest.fixture
def configured(root, tmp_path, monkeypatch):
    path = tmp_path / "hilclaw.config.json"
    document = {"data_repo": {"url": "u", "local_path": str(root)}}
    path.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.delenv(config.ENV_LOCAL_PATH, raising=False)
    monkeypatch.delenv(config.ENV_URL, raising=False)
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", path)
    return root


def run(name, request):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    data = json.dumps(request).encode()
    status = command_line.main(
        [name], stdin=io.BytesIO(data), stdout=stdout, stderr=stderr
    )
    out = stdout.getvalue()
    assert out.endswith(b"\n") and out.count(b"\n") == 1
    return status, json.loads(out), stderr.getvalue()


def test_the_walk_through_on_the_command_line(configured, name):
    request = {"sha256": EMPTY}
    assert run(name, request) == (0, {"sha256": EMPTY, "present": False}, b"")
    assert list(configured.iterdir()) == []
    cas.put_bytes(configured, b"")
    assert run(name, request) == (
        0,
        {"sha256": EMPTY, "present": True, "intact": True},
        b"",
    )
    path = cas.blob_path(configured, EMPTY)
    path.write_bytes(b"x")
    assert run(name, request) == (
        0,
        {"sha256": EMPTY, "present": True, "intact": False},
        b"",
    )
    assert path.read_bytes() == b"x"
    path.unlink()
    path.mkdir()
    assert run(name, request) == (0, {"sha256": EMPTY, "present": False}, b"")
    assert path.is_dir()


@pytest.mark.parametrize(
    "request_",
    [
        {},
        {"sha256": EMPTY.upper()},
        {"sha256": EMPTY[:63]},
        {"sha256": EMPTY, "run_id": "r1"},
    ],
    ids=repr,
)
def test_a_refused_request_on_the_command_line(configured, name, request_):
    cas.put_bytes(configured, b"")
    status, answer, err = run(name, request_)
    assert status == command_line.EXIT_TOOL_FAILURE == 3
    assert list(answer) == ["error"]
    assert answer["error"]["kind"] == "invalid_request"
    assert err.startswith(b"hilclaw: invalid_request: ")


def test_no_data_root_on_the_command_line(configured, name, tmp_path, monkeypatch):
    configured.rmdir()
    status, answer, err = run(name, {"sha256": EMPTY})
    assert (status, answer["error"]["kind"]) == (3, "no_data_root")
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", tmp_path / "missing.json")
    status, answer, err = run(name, {"sha256": EMPTY})
    assert (status, answer["error"]["kind"]) == (3, "no_data_root")
    assert err.startswith(b"hilclaw: no_data_root: ")


def test_a_failed_read_on_the_command_line(configured, name, monkeypatch):
    cas.put_bytes(configured, b"")
    error = OSError(errno.EIO, "Input/output error")
    monkeypatch.setattr(blob_tools, "open", raising(error), raising=False)
    status, answer, err = run(name, {"sha256": EMPTY})
    assert (status, answer["error"]["kind"]) == (3, "blob_unreadable")
    assert EMPTY.encode() in err


def test_the_command_line_front_as_a_process(root, name):
    cas.put_bytes(root, DATA)
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw", name],
        input=json.dumps({"sha256": DIGEST}).encode(),
        capture_output=True,
        cwd=REPO_ROOT,
        env={**os.environ, config.ENV_LOCAL_PATH: str(root)},
        timeout=60,
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, b"")
    assert json.loads(done.stdout) == {
        "sha256": DIGEST,
        "present": True,
        "intact": True,
    }


# Through the MCP front


def message(method, request_id, params=None):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        document["params"] = params
    return json.dumps(document).encode() + b"\n"


def mcp_call(request_id, name, arguments):
    params = {"name": mcp_front.mcp_name(name), "arguments": arguments}
    return message("tools/call", request_id, params)


def serve(data):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main([], stdin=io.BytesIO(data), stdout=stdout, stderr=stderr)
    assert (status, stderr.getvalue()) == (0, b"")
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def outcome(document, is_error=False):
    result = document["result"]
    assert result["isError"] is is_error
    (block,) = result["content"]
    return json.loads(block["text"])


def test_the_mcp_front_lists_the_two_tools_and_correctness_check(configured):
    (listed,) = serve(message("tools/list", 1))
    fetch, push = blob_tools.definitions(lambda: configured)
    *blob, check = listed["result"]["tools"][:3]
    assert check["name"] == "correctness_check"
    assert [tool["name"] for tool in listed["result"]["tools"][3:]] == [
        "instance_read",
        "run_fresh",
        "state_read",
        "state_write",
    ]
    assert {"tools": blob} == {
        "tools": [
            {
                "name": "blob_fetch",
                "description": fetch.description,
                "inputSchema": SCHEMA,
            },
            {
                "name": "blob_push",
                "description": push.description,
                "inputSchema": SCHEMA,
            },
        ]
    }


def test_the_walk_through_through_the_mcp_front(configured, name):
    request = {"sha256": EMPTY}
    (nothing,) = serve(mcp_call(1, name, request))
    assert outcome(nothing) == {"sha256": EMPTY, "present": False}
    assert list(configured.iterdir()) == []
    cas.put_bytes(configured, b"")
    (intact,) = serve(mcp_call(2, name, request))
    assert outcome(intact) == {"sha256": EMPTY, "present": True, "intact": True}
    path = cas.blob_path(configured, EMPTY)
    path.write_bytes(b"x")
    (damaged,) = serve(mcp_call(3, name, request))
    assert outcome(damaged) == {"sha256": EMPTY, "present": True, "intact": False}
    assert path.read_bytes() == b"x"
    path.unlink()
    path.mkdir()
    (occupied,) = serve(mcp_call(4, name, request))
    assert outcome(occupied) == {"sha256": EMPTY, "present": False}
    assert path.is_dir()


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"sha256": EMPTY.upper()},
        {"sha256": EMPTY[:63]},
        {"sha256": EMPTY, "run_id": "r1"},
    ],
    ids=repr,
)
def test_a_refused_request_through_the_mcp_front(configured, name, arguments):
    cas.put_bytes(configured, b"")
    (refused,) = serve(mcp_call(1, name, arguments))
    answer = outcome(refused, is_error=True)
    assert list(answer) == ["error"]
    assert answer["error"]["kind"] == "invalid_request"


def test_no_data_root_through_the_mcp_front(configured, name, tmp_path, monkeypatch):
    configured.rmdir()
    (failed,) = serve(mcp_call(1, name, {"sha256": EMPTY}))
    assert outcome(failed, is_error=True)["error"]["kind"] == "no_data_root"
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", tmp_path / "missing.json")
    (failed,) = serve(mcp_call(2, name, {"sha256": EMPTY}))
    assert outcome(failed, is_error=True)["error"]["kind"] == "no_data_root"


def test_the_mcp_front_as_a_process(root):
    cas.put_bytes(root, DATA)
    data = b"".join(
        mcp_call(i, name, {"sha256": DIGEST}) for i, name in enumerate(NAMES, 1)
    )
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.mcp_front"],
        input=data,
        capture_output=True,
        cwd=REPO_ROOT,
        env={**os.environ, config.ENV_LOCAL_PATH: str(root)},
        timeout=60,
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, b"")
    for line in done.stdout.splitlines():
        assert outcome(json.loads(line)) == {
            "sha256": DIGEST,
            "present": True,
            "intact": True,
        }
    assert len(done.stdout.splitlines()) == 2
