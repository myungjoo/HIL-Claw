import errno
import io
import json
import os
import sys
from pathlib import Path

import pytest

from hilclaw import __main__ as command_line
from hilclaw import (
    fresh_run,
    keys,
    mcp_front,
    run_file_tools,
    run_journal,
    run_state,
    run_state_file,
    tools,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
NAMES = ("state.read", "instance.read", "run.fresh", "state.write")
START = {
    "schema_version": 1,
    "round": 0,
    "budget_spent": {"totals": {}, "position": 0, "open_steps": []},
}
LATER = {
    "schema_version": 1,
    "round": 3,
    "budget_spent": {
        "totals": {"tokens": keys.MAX_INTEGER + 5, "board_s": 7},
        "position": 12,
        "open_steps": [{"round": 3, "step": "sim_run", "execution": 1}],
    },
    "run_status": "running",
    "note": {"nested": [1, 2.5, None, True]},
}


def hw_record():
    return {
        "schema_version": 1,
        "accelerator": "acc_a",
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }


INSTANCE = {
    "schema_version": 1,
    "hw_profile": {"key": keys.hw_profile_key(hw_record()).name, "record": hw_record()},
    "extra_member": {"kept": [1, "two"]},
}


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


def run_dir(root):
    return root / "runs" / RUN


def started(root, instance=INSTANCE):
    run_dir(root).mkdir(parents=True)
    (run_dir(root) / "instance.json").write_text(json.dumps(instance, indent=2) + "\n")


def with_state(root, state=LATER):
    started(root)
    (run_dir(root) / "STATE.json").write_bytes(
        json.dumps(state, indent=1).encode() + b"\n"
    )


def ask(source, name, request):
    return tools.call(default_registry(source), name, request)


def failure(source, name, request):
    with pytest.raises(ToolFailure) as e:
        ask(source, name, request)
    return e.value


def tree(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


# Definitions


def test_definitions_are_four_tool_definitions_in_order(root):
    held = run_file_tools.definitions(lambda: root)
    assert tuple(d.name for d in held) == NAMES
    assert all(type(d) is ToolDefinition for d in held)
    assert len({d.description for d in held}) == 4
    for definition in held:
        assert "data root is never part of the request" in definition.description
        assert definition.input_schema["additionalProperties"] is False


def test_the_input_schemas(root):
    schemas = {d.name: d.input_schema for d in run_file_tools.definitions(Path)}
    run_id = {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}
    for name in NAMES[:3]:
        assert schemas[name] == {
            "type": "object",
            "properties": {"run_id": run_id},
            "required": ["run_id"],
            "additionalProperties": False,
        }
    assert schemas["state.write"]["properties"] == {
        "run_id": run_id,
        "state": {"type": "object"},
    }
    assert schemas["state.write"]["required"] == ["run_id", "state"]


@pytest.mark.parametrize("source", [None, "data", 3, {}, Path(".")])
def test_definitions_refuse_a_source_that_is_not_callable(source):
    with pytest.raises(TypeError, match="callable"):
        run_file_tools.definitions(source)


def test_building_asks_no_source():
    source = FailingSource()
    run_file_tools.definitions(source)
    default_registry(source)
    assert source.calls == 0


def test_the_new_kinds_are_not_reserved():
    for kind in (
        run_file_tools.KIND_RUN_DIR_UNREADABLE,
        run_file_tools.KIND_STATE_NOT_WRITTEN,
    ):
        assert kind not in tools.RESERVED_KINDS
        ToolFailure(kind, "a name of the tool layer")


# Happy


def test_state_read_returns_the_stored_members(root):
    with_state(root)
    result = ask(Source(root), "state.read", {"run_id": RUN})
    stored = json.loads((run_dir(root) / "STATE.json").read_bytes())
    assert result == {"state": stored}
    assert result["state"]["budget_spent"]["totals"]["tokens"] > keys.MAX_INTEGER
    assert result["state"]["run_status"] == "running"
    assert list(result["state"]) == list(LATER)


def test_instance_read_returns_the_stored_members(root):
    started(root)
    result = ask(Source(root), "instance.read", {"run_id": RUN})
    assert result == {"instance": INSTANCE}
    assert result["instance"]["extra_member"] == {"kept": [1, "two"]}


def test_each_read_reads_its_file_once(root, monkeypatch):
    with_state(root)
    reads = []
    real = Path.read_bytes

    def counting(path):
        reads.append(path.name)
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", counting)
    ask(Source(root), "state.read", {"run_id": RUN})
    ask(Source(root), "instance.read", {"run_id": RUN})
    assert reads == ["STATE.json", "instance.json"]


def test_run_fresh_follows_the_state_file(root):
    started(root)
    source = Source(root)
    assert ask(source, "run.fresh", {"run_id": RUN}) == {"fresh": True}
    (run_dir(root) / "STATE.json").write_bytes(run_state.dump(0, _view(START)))
    assert ask(source, "run.fresh", {"run_id": RUN}) == {"fresh": False}
    assert source.calls == 2


def _view(state):
    return run_state.from_stored(state["budget_spent"])


def test_state_write_writes_then_replaces(root):
    started(root)
    source = Source(root)
    assert ask(source, "state.write", {"run_id": RUN, "state": START}) == {}
    path = run_dir(root) / "STATE.json"
    assert path.read_bytes() == run_state.dump(0, _view(START))
    assert ask(source, "state.write", {"run_id": RUN, "state": LATER}) == {}
    others = {"note": LATER["note"], "run_status": "running"}
    assert path.read_bytes() == run_state.dump(3, _view(LATER), others)
    assert ask(source, "state.read", {"run_id": RUN}) == {
        "state": json.loads(path.read_bytes())
    }
    assert ask(source, "state.read", {"run_id": RUN})["state"] == LATER
    assert run_journal.read_state(root, RUN) == run_state.RunState(
        3, _view(LATER), others
    )
    assert tree(root) == [
        "runs",
        f"runs/{RUN}",
        *_files(("STATE.json", "instance.json")),
    ]


def _files(names):
    return [f"runs/{RUN}/{name}" for name in names]


def test_state_write_carries_nothing_over(root):
    with_state(root)
    ask(Source(root), "state.write", {"run_id": RUN, "state": START})
    assert ask(Source(root), "state.read", {"run_id": RUN}) == {"state": START}


def test_state_write_creates_the_run_directory(root):
    ask(Source(root), "state.write", {"run_id": RUN, "state": START})
    assert tree(root) == ["runs", f"runs/{RUN}", *_files(("STATE.json",))]


# Walk-through of ADR-0124


def test_the_round_zero_sequence(root):
    started(root)
    source = Source(root)
    missing = failure(source, "state.read", {"run_id": RUN})
    assert missing.kind == tools.KIND_RUN_FILE_MISSING
    assert missing.message.startswith(f"runs/{RUN}/STATE.json: ")
    assert ask(source, "run.fresh", {"run_id": RUN}) == {"fresh": True}
    assert ask(source, "instance.read", {"run_id": RUN}) == {"instance": INSTANCE}
    assert ask(source, "state.write", {"run_id": RUN, "state": START}) == {}
    assert ask(source, "state.read", {"run_id": RUN}) == {"state": START}
    assert ask(source, "run.fresh", {"run_id": RUN}) == {"fresh": False}


def test_neither_file_is_there(root):
    source = Source(root)
    assert failure(source, "state.read", {"run_id": RUN}).kind == (
        tools.KIND_RUN_FILE_MISSING
    )
    assert failure(source, "instance.read", {"run_id": RUN}).kind == (
        tools.KIND_RUN_FILE_MISSING
    )
    assert ask(source, "run.fresh", {"run_id": RUN}) == {"fresh": False}
    assert tree(root) == []


# Refused requests


REFUSED = [
    ("state.read", {}),
    ("state.read", {"run_id": RUN, "round": 0}),
    ("state.read", {"run_id": RUN, "data_root": "/"}),
    ("state.read", {"run": RUN}),
    ("instance.read", {"run_id": RUN, "state": START}),
    ("instance.read", {"run_id": "Run-A"}),
    ("run.fresh", {"run_id": ""}),
    ("run.fresh", {"run_id": 3}),
    ("run.fresh", {"run_id": "../x"}),
    ("run.fresh", {"run_id": "a" * 65}),
    ("state.write", {"run_id": RUN}),
    ("state.write", {"state": START}),
    ("state.write", {"run_id": RUN, "state": START, "round": 0}),
    ("state.write", {"run_id": "x y", "state": START}),
    ("state.write", {"run_id": RUN, "state": None}),
    ("state.write", {"run_id": RUN, "state": [START]}),
    ("state.write", {"run_id": RUN, "state": "{}"}),
    ("state.write", {"run_id": RUN, "state": {}}),
    ("state.write", {"run_id": RUN, "state": START | {"schema_version": 2}}),
    ("state.write", {"run_id": RUN, "state": START | {"schema_version": True}}),
    ("state.write", {"run_id": RUN, "state": START | {"round": -1}}),
    ("state.write", {"run_id": RUN, "state": START | {"round": keys.MAX_INTEGER + 1}}),
    ("state.write", {"run_id": RUN, "state": {"schema_version": 1, "round": 0}}),
    (
        "state.write",
        {
            "run_id": RUN,
            "state": START | {"budget_spent": {"totals": {"Bad": 1}, "position": 0}},
        },
    ),
    (
        "state.write",
        {
            "run_id": RUN,
            "state": START
            | {"budget_spent": {"totals": {}, "position": 0, "open_steps": [{}]}},
        },
    ),
]


@pytest.mark.parametrize(("name", "request_"), REFUSED)
def test_a_refused_request_asks_no_source_and_writes_nothing(root, name, request_):
    started(root)
    before = tree(root)
    source = Source(root)
    refused = failure(source, name, request_)
    assert refused.kind == tools.KIND_INVALID_REQUEST
    assert source.calls == 0
    assert tree(root) == before


def test_another_version_is_refused_by_its_class(root):
    refused = failure(
        Source(root),
        "state.write",
        {"run_id": RUN, "state": START | {"schema_version": 2}},
    )
    assert refused.message == "state: schema_version: 2 is not supported"
    assert isinstance(refused.__cause__, run_state.UnsupportedVersionError)


def test_a_total_too_long_to_write_is_refused(root):
    limit = getattr(sys, "get_int_max_str_digits", lambda: 0)()
    if not limit:
        pytest.skip("this interpreter writes integers of any length")
    totals = {"t": 10 ** (limit + 1)}
    state = START | {"budget_spent": START["budget_spent"] | {"totals": totals}}
    source = Source(root)
    write = run_file_tools.definitions(source)[3].function
    with pytest.raises(ToolFailure) as e:
        write({"run_id": RUN, "state": state})
    assert e.value.kind == tools.KIND_INVALID_REQUEST
    assert source.calls == 0
    assert tree(root) == []


@pytest.mark.parametrize("name", NAMES)
def test_a_failing_source_is_no_data_root(name):
    source = FailingSource()
    request = (
        {"run_id": RUN, "state": START} if name == "state.write" else {"run_id": RUN}
    )
    assert failure(source, name, request).kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1


# Frame files that cannot be used


STATE_PATH = f"runs/{RUN}/STATE.json"
INSTANCE_PATH = f"runs/{RUN}/instance.json"


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", tools.KIND_RUN_FILE_INVALID),
        (b"{", tools.KIND_RUN_FILE_INVALID),
        (b'{"schema_version": 1}', tools.KIND_RUN_FILE_INVALID),
        (b'{"schema_version": 2}', tools.KIND_RUN_FILE_UNSUPPORTED),
    ],
)
def test_state_read_of_an_unusable_file(root, content, kind):
    started(root)
    (run_dir(root) / "STATE.json").write_bytes(content)
    refused = failure(Source(root), "state.read", {"run_id": RUN})
    assert refused.kind == kind
    assert refused.message.startswith(f"{STATE_PATH}: ")


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", tools.KIND_RUN_FILE_INVALID),
        (b"[]", tools.KIND_RUN_FILE_INVALID),
        (b'{"schema_version": 1}', tools.KIND_RUN_FILE_INVALID),
        (b'{"schema_version": 7}', tools.KIND_RUN_FILE_UNSUPPORTED),
    ],
)
def test_instance_read_of_an_unusable_file(root, content, kind):
    run_dir(root).mkdir(parents=True)
    (run_dir(root) / "instance.json").write_bytes(content)
    refused = failure(Source(root), "instance.read", {"run_id": RUN})
    assert refused.kind == kind
    assert refused.message.startswith(f"{INSTANCE_PATH}: ")


@pytest.mark.parametrize(
    ("name", "file"), [("state.read", "STATE.json"), ("instance.read", "instance.json")]
)
def test_a_directory_in_the_place_of_the_file_is_invalid(root, name, file):
    (run_dir(root) / file).mkdir(parents=True)
    refused = failure(Source(root), name, {"run_id": RUN})
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message == f"runs/{RUN}/{file}: is not a regular file"


@pytest.mark.parametrize(
    ("name", "file"), [("state.read", "STATE.json"), ("instance.read", "instance.json")]
)
def test_a_read_that_fails_is_unreadable(root, monkeypatch, name, file):
    with_state(root)

    def refusing(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(Path, "read_bytes", refusing)
    refused = failure(Source(root), name, {"run_id": RUN})
    assert refused.kind == tools.KIND_RUN_FILE_UNREADABLE
    assert refused.message == (
        f"runs/{RUN}/{file}: could not be read: PermissionError: Permission denied"
    )
    assert str(root) not in refused.message


def test_a_file_in_the_place_of_the_run_directory_is_missing(root):
    (root / "runs").mkdir()
    (root / "runs" / RUN).write_text("")
    refused = failure(Source(root), "state.read", {"run_id": RUN})
    assert refused.kind == tools.KIND_RUN_FILE_MISSING
    assert refused.message == f"{STATE_PATH}: is missing"


def test_run_fresh_answers_a_failed_look(root, monkeypatch):
    started(root)

    def failing(data_root, run_id):
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(fresh_run, "is_fresh", failing)
    refused = failure(Source(root), "run.fresh", {"run_id": RUN})
    assert refused.kind == run_file_tools.KIND_RUN_DIR_UNREADABLE
    assert refused.message == (
        f"runs/{RUN}: could not be looked at: PermissionError: Permission denied"
    )
    assert isinstance(refused.__cause__, PermissionError)


def test_state_write_that_fails_leaves_the_previous_file(root, monkeypatch):
    with_state(root)
    path = run_dir(root) / "STATE.json"
    before = path.read_bytes()

    def failing(descriptor):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(os, "fsync", failing)
    refused = failure(Source(root), "state.write", {"run_id": RUN, "state": START})
    assert refused.kind == run_file_tools.KIND_STATE_NOT_WRITTEN
    assert refused.message == (
        f"{STATE_PATH}: was not written: OSError: Input/output error"
    )
    assert path.read_bytes() == before
    assert tree(root) == [
        "runs",
        f"runs/{RUN}",
        *_files(("STATE.json", "instance.json")),
    ]


# Not journaled


def test_no_call_appends_to_the_log_or_creates_another_file(root):
    started(root)
    source = Source(root)
    ask(source, "run.fresh", {"run_id": RUN})
    ask(source, "state.write", {"run_id": RUN, "state": START})
    ask(source, "state.read", {"run_id": RUN})
    ask(source, "instance.read", {"run_id": RUN})
    assert tree(root) == [
        "runs",
        f"runs/{RUN}",
        *_files(("STATE.json", "instance.json")),
    ]
    assert not (run_dir(root) / "events.ndjson").exists()


# The fronts


def test_the_command_line_front_serves_state_read(root):
    with_state(root)
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        ["state.read"],
        registry=default_registry(lambda: root),
        stdin=io.BytesIO(json.dumps({"run_id": RUN}).encode()),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    assert json.loads(stdout.getvalue()) == {"state": LATER}


def test_the_command_line_front_reports_a_missing_state(root):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        ["state.read"],
        registry=default_registry(lambda: root),
        stdin=io.BytesIO(json.dumps({"run_id": RUN}).encode()),
        stdout=stdout,
        stderr=stderr,
    )
    assert status == 3
    assert json.loads(stdout.getvalue())["error"]["kind"] == "run_file_missing"


def _mcp(request_id, name, arguments):
    document = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    return json.dumps(document).encode() + b"\n"


def test_the_mcp_front_serves_the_four_tools(root):
    started(root)
    data = b"".join(
        [
            _mcp(1, "run_fresh", {"run_id": RUN}),
            _mcp(2, "state_write", {"run_id": RUN, "state": START}),
            _mcp(3, "state_read", {"run_id": RUN}),
            _mcp(4, "instance_read", {"run_id": RUN}),
            _mcp(5, "state_write", {"run_id": RUN, "state": {}}),
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
    answers = [json.loads(line) for line in stdout.getvalue().splitlines()]
    texts = [json.loads(a["result"]["content"][0]["text"]) for a in answers]
    errors = [a["result"]["isError"] for a in answers]
    assert texts[:4] == [{"fresh": True}, {}, {"state": START}, {"instance": INSTANCE}]
    assert errors == [False, False, False, False, True]
    assert texts[4]["error"]["kind"] == "invalid_request"


def test_a_number_beyond_the_float_range_is_no_result(root):
    with_state(root, START | {"note": 0})
    path = run_dir(root) / "STATE.json"
    path.write_bytes(path.read_bytes().replace(b'"note": 0', b'"note": 1e999'))
    assert run_journal.read_state(root, RUN).others == {"note": float("inf")}
    refused = failure(Source(root), "state.read", {"run_id": RUN})
    assert refused.kind == tools.KIND_BAD_RESULT


def test_a_vanished_data_root_is_named_without_its_path(root, monkeypatch):
    real = run_state_file.replace

    def vanishing(data_root, *args):
        root.rmdir()
        return real(data_root, *args)

    monkeypatch.setattr(run_state_file, "replace", vanishing)
    refused = failure(Source(root), "state.write", {"run_id": RUN, "state": START})
    assert refused.kind == run_file_tools.KIND_STATE_NOT_WRITTEN
    assert refused.message == (
        f"{STATE_PATH}: was not written: FileNotFoundError: "
        "the data root is not an existing directory"
    )
    assert str(root) not in refused.message


def test_a_failed_look_without_strerror_gives_no_text_of_the_error(root, monkeypatch):
    def failing(data_root, run_id):
        raise OSError(f"{data_root} could not be looked at")

    monkeypatch.setattr(fresh_run, "is_fresh", failing)
    refused = failure(Source(root), "run.fresh", {"run_id": RUN})
    assert refused.kind == run_file_tools.KIND_RUN_DIR_UNREADABLE
    assert refused.message == f"runs/{RUN}: could not be looked at: OSError"
