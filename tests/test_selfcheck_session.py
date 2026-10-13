import inspect
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

import pytest

from hilclaw import (
    local_run,
    selfcheck_server,
    selfcheck_session,
    selfcheck_stream,
    selfcheck_wire,
)
from hilclaw.selfcheck_outcome import (
    FRONT_REFUSED,
    NO_CALL,
    PASSED,
    SESSION_FAILED,
    SessionEvidence,
    Verdict,
    decide,
)
from hilclaw.selfcheck_session import (
    ALLOWED_TOOLS,
    ALLOWED_TOOLS_SEPARATOR,
    COMMAND,
    CONFIG_FILE,
    PROMPT,
    SERVERS_MEMBER,
    WIRE_COPY_FILE,
    SessionRun,
    run,
)
from hilclaw.selfcheck_stream import (
    FAIL_TOOL_SESSION_NAME,
    SERVER_NAME,
    TOKEN_TOOL_SESSION_NAME,
    StreamFacts,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 60
ACCOUNT = "alice-the-account"
EMAIL = "alice@example.com"
HOME = "/home/alice-the-user/.claude"
SECRETS = (ACCOUNT, EMAIL, HOME, "alice-the-user")
UNSET = ("ENABLE_TOOL_SEARCH", "MCP_TIMEOUT", "CLAUDE_CODE_SIMPLE")
FIXED_REFUSAL = "the directory of the check would lie inside a checkout"
BAD_TIMEOUT_VALUES = [0, -1, 0.0, float("nan"), float("inf")]
BAD_TIMEOUT_TYPES = [None, True, "10"]

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")

STUB = r"""
import json, os, subprocess, sys, time
from pathlib import Path

here = Path(__file__).parent
scenario = json.loads((here / "scenario.json").read_text(encoding="utf-8"))
sys.path.insert(0, scenario["repo"])
from hilclaw import selfcheck_server, selfcheck_stream as names

argv = sys.argv[1:]
out, err = sys.stdout.buffer, sys.stderr.buffer


def note(file, value):
    with (here / file).open("a", encoding="utf-8") as record:
        record.write(json.dumps(value) + "\n")


def emit(event):
    out.write(json.dumps(event).encode() + b"\n")
    out.flush()


def option(name):
    return argv[argv.index(name) + 1] if name in argv else None


note(
    "started.ndjson",
    {
        "argv": argv,
        "cwd": os.getcwd(),
        "stdin": sys.stdin.read(),
        "env": dict(os.environ),
        "listing": sorted(os.listdir(".")),
    },
)
noise = " ".join(scenario["noise"]) + " " + os.getcwd()
err.write(noise.encode() + b"\n")
err.flush()
if scenario["garbage"]:
    cut = json.dumps({names.EVENT_KIND_KEY: names.RESULT_KIND})[:-1]
    out.write(b"\x00\xff no json\n[1, 2]\n" + cut.encode() + b"\n")
    out.flush()
    sys.exit(0)

config = json.loads(Path(option("--mcp-config")).read_text(encoding="utf-8"))
note("configs.ndjson", config)
entry = config.get(scenario["servers_member"], {}).get(names.SERVER_NAME)
allowed = option("--allowedTools") or ""
allowed = allowed.split(",") if scenario["allowed_form"] == "comma" else [allowed]
upto = scenario["upto"]
tools, reply = [], []


def serve():
    place = entry["env"][selfcheck_server.ENV_WIRE_COPY]
    if scenario["squat"]:
        Path(place).write_bytes(b"something else\n")
    server = subprocess.Popen(
        [entry["command"], *entry["args"]],
        env={**os.environ, **entry["env"]},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    def ask(method, params=None, request_id=None):
        message = {"jsonrpc": "2.0", "method": method}
        if request_id is not None:
            message["id"] = request_id
        if params is not None:
            message["params"] = params
        server.stdin.write(json.dumps(message).encode() + b"\n")
        server.stdin.flush()
        if request_id is None:
            return None
        line = server.stdout.readline()
        if not line:
            raise EOFError
        return json.loads(line)

    try:
        revision = {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}
        ask("server/discover", {"_meta": revision}, "server-discover-probe-1")
        client = {"name": "stub", "version": "0.0.0-stub"}
        asked = {"protocolVersion": "2025-11-25", "capabilities": {}}
        ask("initialize", {**asked, "clientInfo": client}, 1)
        if upto in ("list", "call"):
            ask("notifications/initialized")
            for tool in ask("tools/list", None, 2)["result"]["tools"]:
                tools.append(names.TOOL_PREFIX + tool["name"])
        if upto == "call":
            for number, tool in enumerate(tools, 3):
                if tool in allowed:
                    short = tool[len(names.TOOL_PREFIX):]
                    answer = ask("tools/call", {"name": short}, number)
                    reply.extend(block["text"] for block in answer["result"]["content"])
    except (OSError, EOFError):
        pass
    try:
        server.stdin.close()
    except OSError:
        pass
    server.wait()
    if scenario["tear"]:
        whole = Path(place).read_bytes()
        Path(place).write_bytes(whole[:-5])


if entry is not None and upto != "nothing":
    serve()
status = scenario["status"]
named = {names.SERVER_NAME_KEY: names.SERVER_NAME, names.SERVER_STATUS_KEY: status}
emit(
    {
        names.EVENT_KIND_KEY: names.INIT_KIND,
        names.EVENT_SUBKIND_KEY: names.INIT_SUBKIND,
        "cwd": os.getcwd(),
        "account": noise,
        names.SERVERS_KEY: [] if status is None else [named],
        names.TOOLS_KEY: tools,
    }
)
emit({names.EVENT_KIND_KEY: "assistant", "message": {"content": noise}})
time.sleep(scenario["sleep"])
emit(
    {
        names.EVENT_KIND_KEY: names.RESULT_KIND,
        names.REPLY_KEY: scenario["say"] or " and ".join(reply),
        "by": noise,
    }
)
sys.exit(scenario["exit"])
"""


class Stub:
    def __init__(self, directory):
        self.directory = directory

    def install(self, **changes):
        scenario = {
            "repo": str(REPO_ROOT),
            "noise": [ACCOUNT, EMAIL, HOME],
            "servers_member": SERVERS_MEMBER,
            "allowed_form": "comma",
            "upto": "call",
            "status": "connected",
            "exit": 0,
            "sleep": 0,
            "garbage": False,
            "squat": False,
            "tear": False,
            "say": None,
        }
        assert set(changes) <= set(scenario)
        scenario.update(changes)
        script = self.directory / "stub.py"
        script.write_text(STUB, encoding="utf-8")
        (self.directory / "scenario.json").write_text(
            json.dumps(scenario), encoding="utf-8"
        )
        if os.name == "posix":
            launcher = self.directory / "claude"
            launcher.write_text(
                f"#!/bin/sh\nexec '{sys.executable}' '{script}' \"$@\"\n",
                encoding="utf-8",
            )
            launcher.chmod(0o755)
        else:
            launcher = self.directory / "claude.cmd"
            launcher.write_text(
                f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
            )
        assert os.path.samefile(shutil.which("claude"), launcher)

    def _notes(self, name):
        file = self.directory / name
        if not file.exists():
            return []
        lines = file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def calls(self):
        return self._notes("started.ndjson")

    def configs(self):
        return self._notes("configs.ndjson")

    def entry(self):
        (config,) = self.configs()
        return config[SERVERS_MEMBER][SERVER_NAME]

    def tokens(self):
        env = self.entry()["env"]
        return env[selfcheck_server.ENV_TOKEN], env[selfcheck_server.ENV_FAIL_TOKEN]


@pytest.fixture(autouse=True)
def stub(tmp_path, monkeypatch):
    directory = tmp_path / "bin"
    work = tmp_path / "work"
    directory.mkdir()
    work.mkdir()
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.chdir(work)
    for name in UNSET:
        monkeypatch.delenv(name, raising=False)
    assert shutil.which("claude") is None
    return Stub(directory)


@pytest.fixture(autouse=True)
def starts(stub, monkeypatch):
    seen = []
    real = local_run.run

    def only_the_stub(command, **options):
        found = shutil.which("claude")
        assert found is None or Path(found).resolve().parent == (
            stub.directory.resolve()
        )
        seen.append((tuple(command), options))
        return real(command, **options)

    monkeypatch.setattr(local_run, "run", only_the_stub)
    return seen


@pytest.fixture
def parent(tmp_path):
    directory = tmp_path / "checks"
    directory.mkdir()
    return directory


def outcome_of(found):
    verdict = decide(None, found.session, found.wire, torn=found.torn)
    assert isinstance(verdict, Verdict)
    return verdict.outcome


def assert_nothing_leaked(found, stub, capfd):
    captured = capfd.readouterr()
    assert (captured.out, captured.err) == ("", "")
    secrets = list(SECRETS)
    for call in stub.calls():
        secrets += [call["cwd"], os.path.basename(call["cwd"])]
    for config in stub.configs():
        env = config[SERVERS_MEMBER][SERVER_NAME]["env"]
        secrets += [env[selfcheck_server.ENV_TOKEN]]
        secrets += [env[selfcheck_server.ENV_FAIL_TOKEN]]
    for text in (repr(found), str(tuple(found))):
        for secret in secrets:
            assert secret not in text
        assert not re.search(r"[0-9a-f]{32}", text)
        assert PROMPT not in text


def test_public_names():
    public = {name for name in vars(selfcheck_session) if not name.startswith("_")}
    modules = {
        name for name in public if inspect.ismodule(vars(selfcheck_session)[name])
    }
    assert modules == {
        "json",
        "os",
        "shutil",
        "tempfile",
        "time",
        "local_run",
        "selfcheck_outcome",
        "selfcheck_server",
        "selfcheck_stream",
        "selfcheck_wire",
    }
    assert public - modules - {"NamedTuple"} == {
        "ALLOWED_TOOLS",
        "ALLOWED_TOOLS_SEPARATOR",
        "COMMAND",
        "CONFIG_FILE",
        "NO_TOOLS",
        "OPT_ALLOWED_TOOLS",
        "OPT_MCP_CONFIG",
        "OPT_NO_SESSION_PERSISTENCE",
        "OPT_OUTPUT_FORMAT",
        "OPT_PERMISSION_MODE",
        "OPT_PRINT",
        "OPT_SETTING_SOURCES",
        "OPT_STRICT_MCP_CONFIG",
        "OPT_TOOLS",
        "OPT_VERBOSE",
        "OUTPUT_FORMAT",
        "PERMISSION_MODE",
        "PROGRAM",
        "PROMPT",
        "SERVERS_MEMBER",
        "SETTING_SOURCES",
        "SessionRun",
        "WIRE_COPY_FILE",
        "run",
    }


def test_the_command_line_is_the_one_of_the_record():
    assert COMMAND == (
        "claude",
        "-p",
        PROMPT,
        "--mcp-config",
        CONFIG_FILE,
        "--strict-mcp-config",
        "--setting-sources",
        "project",
        "--tools",
        "",
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        ALLOWED_TOOLS,
        "--no-session-persistence",
        "--output-format",
        "stream-json",
        "--verbose",
    )
    assert ALLOWED_TOOLS_SEPARATOR == ","
    assert ALLOWED_TOOLS == f"{TOKEN_TOOL_SESSION_NAME},{FAIL_TOOL_SESSION_NAME}"
    assert COMMAND == (
        selfcheck_session.PROGRAM,
        selfcheck_session.OPT_PRINT,
        PROMPT,
        selfcheck_session.OPT_MCP_CONFIG,
        CONFIG_FILE,
        selfcheck_session.OPT_STRICT_MCP_CONFIG,
        selfcheck_session.OPT_SETTING_SOURCES,
        selfcheck_session.SETTING_SOURCES,
        selfcheck_session.OPT_TOOLS,
        selfcheck_session.NO_TOOLS,
        selfcheck_session.OPT_PERMISSION_MODE,
        selfcheck_session.PERMISSION_MODE,
        selfcheck_session.OPT_ALLOWED_TOOLS,
        ALLOWED_TOOLS,
        selfcheck_session.OPT_NO_SESSION_PERSISTENCE,
        selfcheck_session.OPT_OUTPUT_FORMAT,
        selfcheck_session.OUTPUT_FORMAT,
        selfcheck_session.OPT_VERBOSE,
    )


@pytest.mark.parametrize(
    "word",
    [
        "dangerously",
        "bypass",
        "--model",
        "--bare",
        "--max-turns",
        "--restricted",
        "--safe-mode",
    ],
)
def test_the_command_line_holds_no_forbidden_option(word):
    assert all(word not in argument for argument in COMMAND)


def test_the_file_names_are_plain_names():
    assert CONFIG_FILE != WIRE_COPY_FILE
    for name in (CONFIG_FILE, WIRE_COPY_FILE):
        assert re.fullmatch(r"[a-z.]+", name)
    assert SERVERS_MEMBER == "mcpServers"


def test_the_prompt():
    assert TOKEN_TOOL_SESSION_NAME in PROMPT
    assert FAIL_TOOL_SESSION_NAME in PROMPT
    assert re.fullmatch(r"[A-Za-z0-9 .,_]+", PROMPT)
    assert not re.search(r"[0-9a-f]{32}", PROMPT)
    assert len(PROMPT) < 400


def test_result_fields():
    assert SessionRun._fields == ("session", "wire", "torn", "stream", "removed")


def test_a_session_that_does_everything_passes(stub, starts, parent, capfd):
    stub.install()
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert isinstance(found, SessionRun)
    assert outcome_of(found) == PASSED
    assert found.removed is True
    assert found.torn is False
    assert found.session == SessionEvidence(
        started=True,
        exit_status=0,
        init_read=True,
        server_status="connected",
        token_tool_listed=True,
        fail_tool_listed=True,
        result_read=True,
        token_in_reply=True,
        fail_token_in_reply=True,
    )
    assert isinstance(found.stream, StreamFacts)
    assert sorted(found.stream.session_tools) == sorted(
        [TOKEN_TOOL_SESSION_NAME, FAIL_TOOL_SESSION_NAME]
    )
    assert isinstance(found.wire, selfcheck_wire.WireFacts)
    assert found.wire.probe_before_initialize is True
    assert found.wire.probe_error == -32601
    assert found.wire.client_version == "0.0.0-stub"
    assert found.wire.token_call_answered and found.wire.fail_call_answered
    assert os.listdir(parent) == []
    assert len(stub.calls()) == 1
    assert len(starts) == 1
    assert_nothing_leaked(found, stub, capfd)


def test_the_command_line_and_the_file_as_the_stub_saw_them(
    stub, starts, parent, tmp_path, monkeypatch
):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "marked")
    data_root = tmp_path / "data"
    data_root.mkdir()
    stub.install()
    before = dict(os.environ)
    run(timeout_s=TIMEOUT, parent=parent, keep_out=[data_root])
    (call,) = stub.calls()
    assert call["argv"] == list(COMMAND[1:])
    assert call["argv"][call["argv"].index("--tools") + 1] == ""
    assert call["stdin"] == ""
    assert call["listing"] == [CONFIG_FILE]
    cwd = Path(call["cwd"])
    assert not cwd.exists()
    assert cwd.parent.resolve() == parent.resolve()
    assert REPO_ROOT not in cwd.resolve().parents
    assert data_root.resolve() not in cwd.resolve().parents
    assert call["env"]["HILCLAW_TEST_MARK"] == "marked"
    assert not set(UNSET) & set(call["env"])
    assert dict(os.environ) == before
    ((command, options),) = starts
    assert command == COMMAND
    assert set(options) == {"timeout_s", "cwd"}
    assert options["timeout_s"] == TIMEOUT
    assert Path(options["cwd"]).resolve() == cwd.resolve()

    (config,) = stub.configs()
    assert list(config) == [SERVERS_MEMBER]
    assert list(config[SERVERS_MEMBER]) == [SERVER_NAME]
    entry = stub.entry()
    token, fail_token = stub.tokens()
    place = entry["env"][selfcheck_server.ENV_WIRE_COPY]
    assert entry == selfcheck_server.server_entry(
        token=token, fail_token=fail_token, wire_copy=place
    )
    assert Path(place).resolve() == (cwd / WIRE_COPY_FILE).resolve()
    assert token != fail_token
    for value in (token, fail_token):
        assert all(value not in argument for argument in call["argv"])
        assert all(value not in text for text in call["env"].values())
    said = json.dumps(config)
    assert "marked" not in said
    assert str(tmp_path / "bin") not in said


def test_the_default_parent_is_the_temporary_directory_of_the_system(stub):
    stub.install()
    found = run(timeout_s=TIMEOUT)
    assert outcome_of(found) == PASSED
    assert found.removed is True
    cwd = Path(stub.calls()[0]["cwd"])
    assert not cwd.exists()
    assert cwd.parent.resolve() == Path(tempfile.gettempdir()).resolve()


def test_the_parent_may_be_a_str(stub, parent):
    stub.install()
    assert outcome_of(run(timeout_s=TIMEOUT, parent=str(parent))) == PASSED
    assert os.listdir(parent) == []


def test_each_call_makes_a_new_directory_and_new_tokens(stub, parent):
    stub.install()
    assert outcome_of(run(timeout_s=TIMEOUT, parent=parent)) == PASSED
    assert outcome_of(run(timeout_s=TIMEOUT, parent=parent)) == PASSED
    first, second = stub.calls()
    assert first["cwd"] != second["cwd"]
    tokens = []
    for config in stub.configs():
        env = config[SERVERS_MEMBER][SERVER_NAME]["env"]
        tokens += [
            env[selfcheck_server.ENV_TOKEN],
            env[selfcheck_server.ENV_FAIL_TOKEN],
        ]
    assert len(set(tokens)) == 4
    assert os.listdir(parent) == []


WALK_THROUGH = {
    "the model calls nothing": ({"upto": "list"}, NO_CALL),
    "the model answers without the tokens": ({"say": "done"}, NO_CALL),
    "dropped after initialize, named failed": (
        {"upto": "initialize", "status": "failed"},
        FRONT_REFUSED,
    ),
    "dropped after initialize, not named": (
        {"upto": "initialize", "status": None},
        FRONT_REFUSED,
    ),
    "dropped after initialize, named pending": (
        {"upto": "initialize", "status": "pending"},
        SESSION_FAILED,
    ),
    "a usage limit": (
        {"upto": "list", "say": "Usage limit reached", "exit": 1},
        SESSION_FAILED,
    ),
    "a non-zero status after everything": ({"exit": 3}, SESSION_FAILED),
}


@pytest.mark.parametrize(
    "changes, outcome", WALK_THROUGH.values(), ids=WALK_THROUGH.keys()
)
def test_the_walk_through_of_the_record(changes, outcome, stub, parent, capfd):
    stub.install(**changes)
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert outcome_of(found) == outcome
    assert found.wire is not None and found.wire.reached
    assert found.removed is True
    assert os.listdir(parent) == []
    assert len(stub.calls()) == 1
    assert_nothing_leaked(found, stub, capfd)


NO_WIRE_COPY = {
    "the server is never started": {"upto": "nothing"},
    "a wrong member name for the servers": {"servers_member": "servers"},
    "something else where the wire copy belongs": {"squat": True},
    "garbage and exit status 0": {"garbage": True},
}


@pytest.mark.parametrize("changes", NO_WIRE_COPY.values(), ids=NO_WIRE_COPY.keys())
def test_no_wire_copy_is_a_failed_session(changes, stub, parent, capfd):
    stub.install(**changes)
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert found.wire is None
    assert found.torn is False
    assert found.session.started is True
    assert isinstance(found.stream, StreamFacts)
    assert outcome_of(found) == SESSION_FAILED
    assert found.removed is True
    assert os.listdir(parent) == []
    assert len(stub.calls()) == 1
    assert_nothing_leaked(found, stub, capfd)


def test_garbage_establishes_nothing(stub, parent):
    stub.install(garbage=True)
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert found.stream == StreamFacts()
    assert found.session == SessionEvidence(started=True, exit_status=0)


def test_the_other_form_of_the_allowed_tools_allows_no_call(stub, parent, capfd):
    stub.install(allowed_form="separate")
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert found.wire.list_both_tools is True
    assert found.wire.token_call_requested is False
    assert found.wire.fail_call_requested is False
    assert outcome_of(found) == NO_CALL
    assert os.listdir(parent) == []
    assert_nothing_leaked(found, stub, capfd)


def test_a_wire_copy_cut_in_the_middle_is_torn_and_never_passes(stub, parent, capfd):
    stub.install(tear=True)
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert found.torn is True
    assert found.session.token_in_reply and found.session.fail_token_in_reply
    assert found.wire.token_call_requested and found.wire.fail_call_requested
    answered = (found.wire.token_call_answered, found.wire.fail_call_answered)
    assert sorted(answered) == [False, True]
    assert outcome_of(found) in (NO_CALL, SESSION_FAILED)
    assert os.listdir(parent) == []
    assert_nothing_leaked(found, stub, capfd)


def test_the_time_limit(stub, parent, capfd):
    stub.install(sleep=12)
    before = time.monotonic()
    found = run(timeout_s=5, parent=parent)
    assert time.monotonic() - before < 40
    assert found.session.started is True
    assert found.session.timed_out is True
    assert found.session.exit_status is None
    assert found.session.init_read is True
    if os.name == "posix":
        assert found.session.result_read is False
    assert outcome_of(found) == SESSION_FAILED
    assert found.removed is True
    assert os.listdir(parent) == []
    assert len(stub.calls()) == 1
    assert_nothing_leaked(found, stub, capfd)


NOT_STARTED = SessionRun(SessionEvidence(), None, False, None, True)


def test_no_claude_on_the_path(stub, starts, parent, capfd):
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert found == NOT_STARTED
    assert outcome_of(found) == SESSION_FAILED
    assert stub.calls() == []
    assert len(starts) == 1
    assert os.listdir(parent) == []
    assert_nothing_leaked(found, stub, capfd)


def test_a_claude_file_that_is_not_a_program(stub, parent):
    marker = stub.directory / "ran"
    program = stub.directory / "claude"
    program.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
    program.chmod(0o644)
    assert run(timeout_s=TIMEOUT, parent=parent) == NOT_STARTED
    assert not marker.exists()
    assert os.listdir(parent) == []


@posix_only
def test_a_claude_file_the_system_cannot_execute(stub, parent, capfd):
    program = stub.directory / "claude"
    program.write_bytes(b"\x00\x01\x02 " + EMAIL.encode() + b"\n")
    program.chmod(0o755)
    found = run(timeout_s=TIMEOUT, parent=parent)
    assert found == NOT_STARTED
    assert os.listdir(parent) == []
    assert_nothing_leaked(found, stub, capfd)


def test_an_error_of_a_reader_arrives_after_the_removal(stub, parent, monkeypatch):
    stub.install()

    def fail(output, **tokens):
        raise RuntimeError("the reader failed")

    monkeypatch.setattr(selfcheck_stream, "read", fail)
    with pytest.raises(RuntimeError, match="the reader failed"):
        run(timeout_s=TIMEOUT, parent=parent)
    assert len(stub.calls()) == 1
    assert os.listdir(parent) == []


def test_an_error_of_the_start_arrives_after_the_removal(stub, parent, monkeypatch):
    stub.install()

    def fail(command, **options):
        raise OverflowError("timeout is too large")

    monkeypatch.setattr(local_run, "run", fail)
    with pytest.raises(OverflowError):
        run(timeout_s=TIMEOUT, parent=parent)
    assert os.listdir(parent) == []


def test_a_configuration_file_that_cannot_be_written_is_raised(
    stub, parent, monkeypatch
):
    stub.install()

    def fail(value, file):
        raise OSError("the disk is full")

    monkeypatch.setattr(json, "dump", fail)
    with pytest.raises(OSError, match="the disk is full"):
        run(timeout_s=TIMEOUT, parent=parent)
    assert stub.calls() == []
    assert os.listdir(parent) == []


def test_a_removal_that_fails_keeps_the_evidence(stub, parent, monkeypatch, capfd):
    stub.install()
    tries, pauses = [], []
    with monkeypatch.context() as patch:
        patch.setattr(shutil, "rmtree", lambda path, **how: tries.append(how))
        patch.setattr(time, "sleep", pauses.append)
        found = run(timeout_s=TIMEOUT, parent=parent)
    assert found.removed is False
    assert outcome_of(found) == PASSED
    assert 1 < len(tries) <= 10
    assert all(how == {"ignore_errors": True} for how in tries)
    assert sum(pauses) <= 3
    assert len(os.listdir(parent)) == 1
    assert len(stub.calls()) == 1
    assert_nothing_leaked(found, stub, capfd)


def test_a_removal_that_works_at_a_later_try(stub, parent, monkeypatch):
    stub.install()
    real, tries = shutil.rmtree, []

    def second_time(path, **how):
        tries.append(path)
        if len(tries) > 1:
            real(path, **how)

    with monkeypatch.context() as patch:
        patch.setattr(shutil, "rmtree", second_time)
        patch.setattr(time, "sleep", lambda pause: None)
        found = run(timeout_s=TIMEOUT, parent=parent)
    assert found.removed is True
    assert len(tries) == 2
    assert os.listdir(parent) == []


@pytest.mark.parametrize("inside", ["", "tests", "hilclaw"])
def test_a_parent_inside_the_checkout_is_refused(inside, stub, starts):
    stub.install()
    place = REPO_ROOT / inside
    before = sorted(os.listdir(place))
    with pytest.raises(ValueError) as caught:
        run(timeout_s=TIMEOUT, parent=place)
    assert str(caught.value) == FIXED_REFUSAL
    assert sorted(os.listdir(place)) == before
    assert starts == [] and stub.calls() == []


@pytest.mark.parametrize("inside", ["", "sub"])
def test_a_parent_inside_a_keep_out_directory_is_refused(
    inside, stub, starts, tmp_path
):
    stub.install()
    data_root = tmp_path / "data"
    place = data_root / inside
    place.mkdir(parents=True)
    for keep_out in ([data_root], (str(data_root),), [tmp_path / "other", data_root]):
        with pytest.raises(ValueError) as caught:
            run(timeout_s=TIMEOUT, parent=place, keep_out=keep_out)
        assert str(caught.value) == FIXED_REFUSAL
    assert os.listdir(place) == []
    assert starts == [] and stub.calls() == []


@posix_only
def test_a_parent_that_links_into_a_keep_out_directory_is_refused(stub, tmp_path):
    stub.install()
    data_root = tmp_path / "data"
    data_root.mkdir()
    link = tmp_path / "link"
    link.symlink_to(data_root, target_is_directory=True)
    with pytest.raises(ValueError, match=FIXED_REFUSAL):
        run(timeout_s=TIMEOUT, parent=link, keep_out=[data_root])
    assert os.listdir(data_root) == []
    assert stub.calls() == []


def test_a_directory_that_only_shares_a_name_prefix_is_not_kept_out(stub, tmp_path):
    stub.install()
    place = tmp_path / "data2"
    place.mkdir()
    found = run(timeout_s=TIMEOUT, parent=place, keep_out=[tmp_path / "data"])
    assert outcome_of(found) == PASSED
    assert os.listdir(place) == []


def test_a_parent_that_does_not_exist(stub, starts, tmp_path):
    stub.install()
    with pytest.raises(FileNotFoundError):
        run(timeout_s=TIMEOUT, parent=tmp_path / "absent")
    assert not (tmp_path / "absent").exists()
    assert starts == [] and stub.calls() == []


@pytest.mark.parametrize(
    "options",
    [
        {"parent": 3},
        {"parent": b"/tmp"},
        {"keep_out": "/data"},
        {"keep_out": b"/data"},
        {"keep_out": Path("/data")},
        {"keep_out": [3]},
        {"keep_out": [b"/data"]},
        {"keep_out": 3},
    ],
)
def test_a_place_of_another_type_is_refused(options, stub, starts, parent):
    stub.install()
    with pytest.raises(TypeError):
        run(timeout_s=TIMEOUT, **{"parent": parent, **options})
    assert os.listdir(parent) == []
    assert starts == [] and stub.calls() == []


@pytest.mark.parametrize("value", BAD_TIMEOUT_VALUES)
def test_timeout_must_be_positive_and_finite(value, stub, parent):
    stub.install()
    with pytest.raises(ValueError, match="timeout_s"):
        run(timeout_s=value, parent=parent)
    assert stub.calls() == []
    assert os.listdir(parent) == []


@pytest.mark.parametrize("value", BAD_TIMEOUT_TYPES)
def test_timeout_must_be_a_number(value, stub, parent):
    stub.install()
    with pytest.raises(TypeError, match="timeout_s"):
        run(timeout_s=value, parent=parent)
    assert stub.calls() == []
    assert os.listdir(parent) == []


def test_timeout_has_no_default_and_is_keyword_only(stub, parent):
    stub.install()
    with pytest.raises(TypeError):
        run(parent=parent)
    with pytest.raises(TypeError):
        run(TIMEOUT, parent=parent)
    assert stub.calls() == []
    assert os.listdir(parent) == []
