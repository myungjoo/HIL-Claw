import inspect
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from hilclaw import (
    config,
    data_root_source,
    further_turn,
    keys,
    run_commit,
    selfcheck,
    selfcheck_login,
    selfcheck_outcome,
    tools,
    turn_loop,
    turn_start,
)
from hilclaw.instance_file import write
from hilclaw.journal import EMPTY
from hilclaw.layout import InvalidPathValueError
from hilclaw.run_state import dump
from hilclaw.run_state_file import replace
from hilclaw.turn_start import (
    BAD_USAGE,
    ERROR,
    EXIT_ERROR,
    EXIT_FAILED_TURN,
    EXIT_OPEN_STATE,
    EXIT_RUN_OVER,
    EXIT_STOPPED_AT_CHECK,
    EXIT_UNCHANGED_TURN,
    EXIT_UNKNOWN_RUN_STATUS,
    FAILED_TURN,
    FAULT,
    NO_CLAUDE,
    NO_DATA_ROOT,
    OPEN_STATE,
    RUN_OVER,
    STOPPED_AT_CHECK,
    UNCHANGED_TURN,
    UNKNOWN_RUN_STATUS,
    main,
    prompt,
)

RUN = "run-a"
GIT = shutil.which("git")
REPOSITORY = Path(__file__).resolve().parent.parent
PROFILE = {
    "schema_version": 1,
    "accelerator": "acc_a",
    "revision": "rev 1",
    "toolchain": {"cc": "1.0"},
    "host": {"cpu": "cpu x", "os": "os y"},
    "hw_source": "external",
}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 4, "k": 4, "n": 4},
    "dtype": "fp32",
    "layout": "row_major",
}
IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
}
LOCATING = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_CONFIG",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "EMAIL",
)
STATE = f"runs/{RUN}/STATE.json"
INSTANCE = f"runs/{RUN}/instance.json"
LEAD = "Carry out the next turn of your run as your instructions say. Your run id is "
EDGE_IDS = [
    "a",
    "7",
    "a" * 64,
    "a-b_c",
    "run-",
    "x_-",
    "20261009t012331z-9f3a6c1e0b7d4a52",
]

COMMIT = "commit"
LOGGED_IN = json.dumps({"loggedIn": True, "authMethod": "claude.ai"})
NOT_LOGGED_IN = json.dumps({"loggedIn": False, "authMethod": "none"})
PLANTED = "[Errno 13] Permission denied: '/home/alice-the-user/.claude/x'"

STUB = r"""
import json, os, subprocess, sys
from pathlib import Path

here = Path(__file__).parent
scenario = json.loads((here / "scenario.json").read_text(encoding="utf-8"))
argv = sys.argv[1:]
kind = "turn"
if argv == ["auth", "status"]:
    kind = "login"
elif "--no-session-persistence" in argv:
    kind = "check"
with (here / "started.ndjson").open("a", encoding="utf-8") as record:
    entry = {"argv": argv, "listing": sorted(os.listdir(".")), "kind": kind}
    record.write(json.dumps(entry) + "\n")
check = scenario["check"]
if kind == "login":
    sys.stdout.write(check["auth_output"])
    sys.exit(check["auth_exit"])
if kind == "check":
    sys.path.insert(0, check["repo"])
    from hilclaw import selfcheck_stream as names

    def option(name):
        return argv[argv.index(name) + 1]

    config = json.loads(Path(option("--mcp-config")).read_text(encoding="utf-8"))
    entry = config["mcpServers"][names.SERVER_NAME]
    allowed = option("--allowedTools").split(",")
    tools, reply = [], []
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
        return json.loads(server.stdout.readline())

    client = {"name": "stub", "version": "0.0.0-stub"}
    asked = {"protocolVersion": "2025-11-25", "capabilities": {}}
    ask("initialize", {**asked, "clientInfo": client}, 1)
    if check["upto"] in ("list", "call"):
        ask("notifications/initialized")
        for tool in ask("tools/list", None, 2)["result"]["tools"]:
            tools.append(names.TOOL_PREFIX + tool["name"])
    if check["upto"] == "call":
        for number, tool in enumerate(tools, 3):
            if tool in allowed:
                answer = ask("tools/call", {"name": tool[len(names.TOOL_PREFIX):]}, number)
                reply.extend(block["text"] for block in answer["result"]["content"])
    server.stdin.close()
    server.wait()
    named = {names.SERVER_NAME_KEY: names.SERVER_NAME, names.SERVER_STATUS_KEY: check["status"]}
    for event in (
        {
            names.EVENT_KIND_KEY: names.INIT_KIND,
            names.EVENT_SUBKIND_KEY: names.INIT_SUBKIND,
            names.SERVERS_KEY: [named],
            names.TOOLS_KEY: tools,
        },
        {names.EVENT_KIND_KEY: names.RESULT_KIND, names.REPLY_KEY: " and ".join(reply)},
    ):
        sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()
    sys.exit(check["exit"])
lines = (here / "started.ndjson").read_text(encoding="utf-8").splitlines()
started = sum(json.loads(line)["kind"] == "turn" for line in lines)
steps = scenario["steps"]
step = steps[min(started, len(steps)) - 1]
for name, text in step["writes"]:
    path = Path(scenario["root"], name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
if step["commit"]:
    for args in (["add", "-A"], ["commit", "-q", "-m", "turn"]):
        subprocess.run([scenario["git"], "-C", scenario["root"], *args], check=True)
sys.exit(step["status"])
"""


CHECKED = {
    "passed": {},
    "no_call": {"upto": "list"},
    "not_logged_in": {"auth_exit": 1, "auth_output": NOT_LOGGED_IN},
    "login_unreadable": {"auth_exit": 3},
    "front_refused": {"upto": "initialize", "status": "failed"},
    "session_failed": {"exit": 3},
}


class Stub:
    def __init__(self, directory, root):
        self.directory = directory
        self.root = root
        self.steps = []

    def install(self, *steps, check="passed"):
        self.steps = [
            {"status": status, "writes": writes, "commit": COMMIT in rest}
            for status, writes, *rest in steps
        ]
        script = self.directory / "stub.py"
        script.write_text(STUB, encoding="utf-8")
        checked = {
            "repo": str(REPOSITORY),
            "auth_output": LOGGED_IN,
            "auth_exit": 0,
            "upto": "call",
            "status": "connected",
            "exit": 0,
            **CHECKED[check],
        }
        scenario = {
            "root": str(self.root),
            "git": GIT,
            "steps": self.steps,
            "check": checked,
        }
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

    def every_call(self):
        file = self.directory / "started.ndjson"
        if not file.exists():
            return []
        lines = file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def calls(self):
        return [call for call in self.every_call() if call["kind"] == "turn"]

    def kinds(self):
        return [call["kind"] for call in self.every_call()]

    def written(self):
        made = {}
        for index in range(len(self.calls())):
            step = self.steps[min(index, len(self.steps) - 1)]
            for name, text in step["writes"]:
                made[name] = text.encode("utf-8")
        return made


def markers_above(path):
    own = (Path.home() / ".claude").resolve()
    return any(
        os.path.lexists(directory / name) and (directory / name).resolve() != own
        for directory in Path(path).resolve().parents
        for name in turn_loop.MARKERS
    )


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch, tmp_path_factory):
    assert GIT is not None, "these tests need git on PATH"
    config = tmp_path_factory.mktemp("git-config") / "global"
    config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in LOCATING:
        monkeypatch.delenv(name, raising=False)
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(run_commit, "GIT", GIT)


def git(root, *args):
    subprocess.run(
        [GIT, "-C", str(root), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )


def settle(root):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "by hand")


@pytest.fixture
def root(tmp_path, isolated_git):
    directory = tmp_path / "data"
    directory.mkdir()
    git(directory, "init", "-q", "-b", "main")
    return directory


@pytest.fixture
def parent(tmp_path):
    directory = tmp_path / "sessions"
    directory.mkdir()
    return directory


@pytest.fixture(autouse=True)
def stub(tmp_path, root, monkeypatch):
    if markers_above(tmp_path):
        pytest.skip("a directory above the test's temporary directory holds a marker")
    directory = tmp_path / "bin"
    work = tmp_path / "work"
    directory.mkdir()
    work.mkdir()
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.chdir(work)
    assert shutil.which("claude") is None
    return Stub(directory, root)


@pytest.fixture(autouse=True)
def only_the_stub(stub, monkeypatch):
    real = subprocess.run

    def checked(command, **options):
        program = Path(command[0]).resolve()
        if program.name.startswith("claude"):
            assert program.parent == stub.directory.resolve()
        return real(command, **options)

    monkeypatch.setattr(subprocess, "run", checked)


def instance_bytes(budget=5):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
    }
    if budget is not None:
        document["round_budget"] = budget
    return json.dumps(document, indent=2).encode() + b"\n"


def state_text(round, others=None):
    return dump(round, EMPTY, others).decode("ascii")


def started(root, budget=5):
    write(root, RUN, instance_bytes(budget))


def stated(root, round=1, others=None, budget=5):
    started(root, budget)
    replace(root, RUN, round, EMPTY, others)


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): (
            None if path.is_dir() else path.read_bytes()
        )
        for path in directory.rglob("*")
        if ".git" not in path.relative_to(directory).parts
    }


def over(root, round=5):
    stated(root, round, {"run_status": "over"})
    settle(root)


def owed(root):
    stated(root, 4)
    settle(root)
    replace(root, RUN, 5, EMPTY, {"run_status": "over"})


def report(outcome=selfcheck_outcome.PASSED):
    return {
        "outcome": outcome,
        "refused_a": False,
        "refused_b": False,
        "login": {"auth_method": "claude.ai", "exit_status": 0, "timed_out": False},
        "system": {"os_name": "os", "os_release": "1", "python_version": "3"},
    }


class Standin:
    def __init__(self, outcome=selfcheck_outcome.PASSED, error=None):
        self.report = report(outcome)
        self.error = error
        self.calls = []

    def __call__(self, **options):
        self.calls.append(options)
        if self.error is not None:
            raise self.error
        return self.report


class Started:
    def __init__(self, status, stdout, stderr, check):
        self.status = status
        self.lines = stdout.getvalue().splitlines()
        self.stderr = stderr.getvalue().decode("utf-8")
        self.check = check

    @property
    def told(self):
        assert len(self.lines) == 1
        return json.loads(self.lines[0])


def start(parent, args=(RUN,), source=None, **changes):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    root = changes.pop("root", None)
    if source is None:
        source = lambda: root
    arguments = {
        "source": source,
        "check": Standin(),
        "parent": parent,
        "stdout": stdout,
        "stderr": stderr,
        **changes,
    }
    status = main(list(args), **arguments)
    return Started(status, stdout, stderr, arguments["check"])


class Watched:
    def __init__(self, root, stub):
        self.root = root
        self.stub = stub
        self.before = snapshot(root)

    def check(self):
        expected = dict(self.before)
        for name, content in self.stub.written().items():
            parts = Path(name).parts
            for depth in range(1, len(parts)):
                expected.setdefault("/".join(parts[:depth]), None)
            expected[name] = content
        assert snapshot(self.root) == expected


@pytest.fixture
def go(root, parent, stub):
    def go(*steps, **changes):
        if steps:
            stub.install(*steps)
        watched = Watched(root, stub)
        found = start(changes.pop("parent", parent), root=root, **changes)
        watched.check()
        assert list(parent.iterdir()) == []
        return found

    return go


def named(text):
    head, found, rest = text.partition(LEAD)
    assert head == "" and found and LEAD not in rest and rest.endswith(".")
    return rest[:-1]


def told_once(found, status, told):
    assert found.status == status
    line = dict(found.told)
    if isinstance(found.check, Standin):
        if found.check.calls:
            assert line.pop("check") == found.check.report
        assert "check" not in line
    assert line == told
    if status == EXIT_ERROR:
        assert len(found.stderr.splitlines()) == 1
    else:
        assert found.stderr == ""


# --- names ---


def test_public_names():
    public = sorted(
        name
        for name, value in vars(turn_start).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    )
    assert public == [
        "BAD_USAGE",
        "ERROR",
        "EXIT_ERROR",
        "EXIT_FAILED_TURN",
        "EXIT_OPEN_STATE",
        "EXIT_RUN_OVER",
        "EXIT_STOPPED_AT_CHECK",
        "EXIT_UNCHANGED_TURN",
        "EXIT_UNKNOWN_RUN_STATUS",
        "FAILED_TURN",
        "FAULT",
        "NO_CLAUDE",
        "NO_DATA_ROOT",
        "OPEN_STATE",
        "RUN_OVER",
        "STOPPED_AT_CHECK",
        "UNCHANGED_TURN",
        "UNKNOWN_RUN_STATUS",
        "main",
        "prompt",
    ]
    statuses = [
        EXIT_RUN_OVER,
        EXIT_UNKNOWN_RUN_STATUS,
        EXIT_FAILED_TURN,
        EXIT_UNCHANGED_TURN,
        EXIT_OPEN_STATE,
        EXIT_STOPPED_AT_CHECK,
        EXIT_ERROR,
    ]
    assert EXIT_RUN_OVER == 0
    assert len(set(statuses)) == 7
    assert not {1, 2} & set(statuses)
    kinds = {RUN_OVER, UNKNOWN_RUN_STATUS, FAILED_TURN, UNCHANGED_TURN, OPEN_STATE}
    assert len(kinds | {STOPPED_AT_CHECK, ERROR}) == 7
    assert prompt(RUN) == f"{LEAD}{RUN}."
    assert turn_start.__doc__
    names = tools.default_registry(lambda: None).names()
    assert not [name for name in names if "turn" in name]


# --- happy ---


def test_a_fresh_run_goes_from_round_zero_to_over(root, go, stub):
    started(root)
    found = go(
        (0, [(STATE, state_text(1))]),
        (0, [(STATE, state_text(2))]),
        (0, [(STATE, state_text(3, {"run_status": "over"}))], COMMIT),
    )
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    calls = stub.calls()
    assert len(calls) == 3
    for call in calls:
        assert call["argv"][:2] == [turn_loop.OPT_PRINT, prompt(RUN)]
        assert named(call["argv"][1]) == RUN
        assert "--no-session-persistence" not in call["argv"]
        mode = call["argv"].index("--permission-mode")
        assert call["argv"][mode + 1] == "dontAsk"
        allowed = call["argv"][call["argv"].index("--allowedTools") + 1]
        assert "Agent(evaluator)" in allowed.split(",")
        assert call["argv"][1].count(RUN) == 1
        assert "CLAUDE.md" in call["listing"]


def test_every_start_on_a_run_gives_the_same_prompt(root, go, stub):
    started(root)
    for _ in range(2):
        told_once(go((0, [])), EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    first, second = stub.calls()
    assert first["argv"] == second["argv"]
    assert first["argv"][1] == prompt(RUN)


@pytest.mark.parametrize("run_id", EDGE_IDS)
def test_the_prompt_names_any_valid_run_id(run_id):
    text = prompt(run_id)
    turn_loop._check_prompt(text)
    assert not text.startswith("-")
    assert named(text) == run_id
    assert text == f"{LEAD}{run_id}."


def test_a_built_run_id_is_in_the_prompt_once():
    run_id = EDGE_IDS[-1]
    assert prompt(run_id).count(run_id) == 1


@pytest.mark.parametrize("run_id", ["run-", "x_-", EDGE_IDS[-1]])
def test_a_run_id_with_a_hyphen_reaches_the_stub_unchanged(root, go, stub, run_id):
    write(root, run_id, instance_bytes())
    found = go((0, []), args=(run_id,))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    (call,) = stub.calls()
    assert call["argv"][1] == prompt(run_id)
    assert named(call["argv"][1]) == run_id


def test_over_at_once_starts_no_turn(root, go, stub):
    over(root)
    found = go((0, []))
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    assert stub.calls() == []


def test_a_str_data_root(root, parent, stub):
    over(root)
    found = start(parent, root=str(root))
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})


# --- decision 2 ---


def test_a_failed_turn_on_a_fresh_run(root, go, stub):
    started(root)
    found = go((3, []))
    told_once(found, EXIT_FAILED_TURN, {"outcome": FAILED_TURN, "exit_status": 3})
    assert len(stub.calls()) == 1


def test_a_failed_turn_in_p4(root, go, stub):
    stated(root, 2)
    found = go((1, []))
    told_once(found, EXIT_FAILED_TURN, {"outcome": FAILED_TURN, "exit_status": 1})
    assert len(stub.calls()) == 1


def test_a_failed_turn_that_ended_a_round(root, go, stub):
    stated(root, 2)
    found = go((7, [(STATE, state_text(3))]))
    told_once(found, EXIT_FAILED_TURN, {"outcome": FAILED_TURN, "exit_status": 7})
    assert len(stub.calls()) == 1


def test_a_failed_turn_after_progress(root, go, stub):
    started(root)
    found = go((0, [(STATE, state_text(1))]), (4, []))
    told_once(found, EXIT_FAILED_TURN, {"outcome": FAILED_TURN, "exit_status": 4})
    assert len(stub.calls()) == 2


# --- decision 3 ---


def test_a_placeholder_turn_on_a_fresh_run(root, go, stub):
    started(root)
    found = go((0, []))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 1


def test_p4_with_the_same_round(root, go, stub):
    stated(root, 3)
    found = go((0, []))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 1


def test_a_write_inside_the_round_is_no_progress(root, go, stub):
    stated(root, 3)
    found = go((0, [(STATE, state_text(3, {"phase": "board_done"}))]))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 1


def test_round_zero_then_an_unchanged_turn(root, go, stub):
    started(root)
    found = go((0, [(STATE, state_text(1))]), (0, []))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 2


def test_round_is_not_compared_with_the_budget(root, go, stub):
    stated(root, 5, budget=5)
    found = go((0, [(STATE, state_text(9))]), (0, []))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 2


def test_a_lower_round_is_another_round(root, go, stub):
    stated(root, 4)
    found = go((0, [(STATE, state_text(2))]), (0, []))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 2


# --- open states ---


def open_missing_state(root):
    started(root)
    (root / "runs" / RUN / "events.ndjson").write_bytes(b"")


def open_invalid_state(root):
    started(root)
    (root / STATE).write_bytes(b"{")


def open_state_version(root):
    started(root)
    (root / STATE).write_bytes(b'{"schema_version": 2}\n')


def open_missing_instance(root):
    stated(root)
    (root / INSTANCE).unlink()


def open_invalid_instance(root):
    stated(root)
    (root / INSTANCE).write_bytes(b"{")


def open_instance_version(root):
    stated(root)
    (root / INSTANCE).write_bytes(b'{"schema_version": 2}\n')


def open_no_budget(root):
    stated(root, budget=None)


OPEN_STATES = [
    (open_missing_state, further_turn.STATE_MISSING),
    (open_invalid_state, further_turn.STATE_INVALID),
    (open_state_version, further_turn.STATE_VERSION),
    (open_missing_instance, further_turn.INSTANCE_MISSING),
    (open_invalid_instance, further_turn.INSTANCE_INVALID),
    (open_instance_version, further_turn.INSTANCE_VERSION),
    (open_no_budget, further_turn.NO_ROUND_BUDGET),
]


@pytest.mark.parametrize(("arrange", "reason"), OPEN_STATES)
def test_an_open_state_starts_no_turn(root, go, stub, arrange, reason):
    arrange(root)
    found = go((0, [(STATE, state_text(1))]))
    told_once(found, EXIT_OPEN_STATE, {"outcome": OPEN_STATE, "reason": reason})
    assert stub.calls() == []


def test_an_empty_data_root_is_an_open_state(go, stub):
    found = go((0, []))
    told = {"outcome": OPEN_STATE, "reason": further_turn.STATE_MISSING}
    told_once(found, EXIT_OPEN_STATE, told)
    assert stub.calls() == []


def test_an_open_state_after_a_failed_turn(root, go, stub):
    started(root)
    found = go((4, [(STATE, "{")]))
    told = {
        "outcome": OPEN_STATE,
        "reason": further_turn.STATE_INVALID,
        "exit_status": 4,
    }
    told_once(found, EXIT_OPEN_STATE, told)
    assert len(stub.calls()) == 1


def test_an_open_state_after_a_turn_that_exited_with_zero(root, go, stub):
    stated(root, 1)
    found = go((0, [(INSTANCE, instance_bytes(None).decode())]))
    told = {"outcome": OPEN_STATE, "reason": further_turn.NO_ROUND_BUDGET}
    told_once(found, EXIT_OPEN_STATE, told)
    assert len(stub.calls()) == 1


# --- precedence and P3 ---


def test_over_committed_by_a_failed_turn_is_run_over(root, go, stub):
    started(root)
    found = go((5, [(STATE, state_text(1, {"run_status": "over"}))], COMMIT))
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    assert len(stub.calls()) == 1


def test_over_written_by_a_failed_turn_without_a_commit(root, go, stub):
    started(root)
    found = go((5, [(STATE, state_text(1, {"run_status": "over"}))]))
    told_once(found, EXIT_FAILED_TURN, {"outcome": FAILED_TURN, "exit_status": 5})
    assert len(stub.calls()) == 1


def test_an_unknown_value_written_by_a_failed_turn(root, go, stub):
    stated(root, 1)
    found = go((5, [(STATE, state_text(1, {"run_status": "stopped"}))]))
    told = {"outcome": UNKNOWN_RUN_STATUS, "run_status": "stopped"}
    told_once(found, EXIT_UNKNOWN_RUN_STATUS, told)


@pytest.mark.parametrize("value", ["stopped", "Over", "", None, 1, True, {"a": []}])
def test_p3_reports_the_value(root, go, stub, value):
    stated(root, 1, {"run_status": value})
    found = go((0, []))
    told = {"outcome": UNKNOWN_RUN_STATUS, "run_status": value}
    told_once(found, EXIT_UNKNOWN_RUN_STATUS, told)
    assert type(found.told["run_status"]) is type(value)
    assert stub.calls() == []


# --- owed P2 (ADR-0127 decision 6) ---


def test_owed_p2_checks_and_its_turn_commits(root, go, stub):
    owed(root)
    standin = Standin()
    found = go((0, [], COMMIT), check=standin)
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    assert len(standin.calls) == 1 and stub.kinds() == ["turn"]
    assert found.told["check"] == standin.report


def test_owed_p2_left_owed_is_an_unchanged_turn(root, go, stub):
    owed(root)
    standin = Standin()
    found = go((0, []), check=standin)
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(standin.calls) == 1 and len(stub.calls()) == 1


def test_owed_p2_left_owed_with_another_round_is_unchanged(root, go, stub):
    owed(root)
    found = go((0, [(STATE, state_text(6, {"run_status": "over"}))]))
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(stub.calls()) == 1


@pytest.mark.parametrize("status", [1, 9])
def test_a_failed_turn_in_owed_p2(root, go, stub, status):
    owed(root)
    found = go((status, []))
    told = {"outcome": FAILED_TURN, "exit_status": status}
    told_once(found, EXIT_FAILED_TURN, told)
    assert len(stub.calls()) == 1


def test_p4_to_owed_p2_gives_one_more_turn_without_a_check(root, go, stub):
    stated(root, 4)
    settle(root)
    standin = Standin()
    found = go(
        (0, [(STATE, state_text(5, {"run_status": "over"}))]),
        (0, [], COMMIT),
        check=standin,
    )
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    assert len(standin.calls) == 1 and len(stub.calls()) == 2


@pytest.mark.parametrize(
    "outcome", [selfcheck_login.NOT_LOGGED_IN, selfcheck_outcome.SESSION_FAILED]
)
def test_owed_p2_with_a_check_that_does_not_pass(root, go, stub, outcome):
    owed(root)
    standin = Standin(outcome)
    found = go((0, [], COMMIT), check=standin)
    told_once(found, EXIT_STOPPED_AT_CHECK, {"outcome": STOPPED_AT_CHECK})
    assert len(standin.calls) == 1 and stub.calls() == []


def test_p2_without_a_repository(parent, stub, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    stated(plain, 5, {"run_status": "over"})
    stub.install((0, [], COMMIT))
    standin = Standin()
    found = start(parent, root=plain, check=standin)
    told = {"outcome": OPEN_STATE, "reason": further_turn.NO_REPOSITORY}
    told_once(found, EXIT_OPEN_STATE, told)
    assert standin.calls == [] and stub.kinds() == []


def test_p2_when_git_cannot_be_started(root, go, stub, tmp_path, monkeypatch):
    over(root)
    monkeypatch.setattr(run_commit, "GIT", str(tmp_path / "no-such-git"))
    standin = Standin()
    found = go((0, []), check=standin)
    told = {"outcome": OPEN_STATE, "reason": further_turn.NO_REPOSITORY}
    told_once(found, EXIT_OPEN_STATE, told)
    assert standin.calls == [] and stub.kinds() == []


def test_p2_with_a_round_below_head_is_commit_refused(root, go, stub):
    over(root)
    replace(root, RUN, 4, EMPTY, {"run_status": "over"})
    standin = Standin()
    found = go((0, []), check=standin)
    told = {"outcome": OPEN_STATE, "reason": further_turn.COMMIT_REFUSED}
    told_once(found, EXIT_OPEN_STATE, told)
    assert standin.calls == [] and stub.kinds() == []


def test_commit_refused_after_a_failed_turn(root, go, stub):
    stated(root, 3)
    settle(root)
    found = go((4, [(STATE, state_text(2, {"run_status": "over"}))]))
    told = {
        "outcome": OPEN_STATE,
        "reason": further_turn.COMMIT_REFUSED,
        "exit_status": 4,
    }
    told_once(found, EXIT_OPEN_STATE, told)
    assert len(stub.calls()) == 1


def test_no_repository_after_a_turn_that_exited_with_zero(root, go, stub, monkeypatch):
    stated(root, 4)
    settle(root)
    monkeypatch.setattr(run_commit, "GIT", "no-such-git")
    found = go((0, [(STATE, state_text(5, {"run_status": "over"}))]))
    told = {"outcome": OPEN_STATE, "reason": further_turn.NO_REPOSITORY}
    told_once(found, EXIT_OPEN_STATE, told)
    assert len(stub.calls()) == 1


# --- errors and negative cases ---


@pytest.mark.parametrize("args", [(), (RUN, RUN), ("Run-a",), ("",), ("../x",)])
def test_a_bad_command_line(root, go, stub, args):
    started(root)
    called = []
    found = go((0, []), args=args, source=lambda: called.append(1))
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": BAD_USAGE})
    assert called == [] and stub.calls() == []


def test_a_data_root_source_that_raises(root, go, stub):
    started(root)

    def failing():
        raise config.ConfigError("no configuration")

    found = go((0, []), source=failing)
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": NO_DATA_ROOT})
    assert "no configuration" in found.stderr
    assert stub.calls() == []


@pytest.mark.parametrize("named", ["absent", "file", ""])
def test_a_data_root_that_is_no_directory(root, go, stub, tmp_path, named):
    started(root)
    (tmp_path / "file").write_bytes(b"")
    path = str(tmp_path / named) if named else ""
    found = go((0, []), source=lambda: path)
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": NO_DATA_ROOT})
    assert stub.calls() == []


def test_a_data_root_source_that_is_not_callable(root, go, stub):
    started(root)
    found = go((0, []), source=7)
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": FAULT})


def test_the_default_data_root_source(root, parent, stub, monkeypatch):
    over(root)
    repo = config.DataRepo("url", root)
    monkeypatch.setattr(config, "load_data_repo", lambda: repo)
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = main([RUN], parent=parent, stdout=stdout, stderr=stderr)
    assert status == EXIT_RUN_OVER
    parameters = inspect.signature(main).parameters
    assert parameters["source"].default is data_root_source.configured
    assert parameters["check"].default is selfcheck.check


def test_no_claude_on_the_path(root, go, stub):
    started(root)
    found = go()
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": NO_CLAUDE})
    assert stub.calls() == []


def test_a_refused_parent(root, go, stub, tmp_path):
    started(root)
    refused = tmp_path / "refused"
    refused.mkdir()
    (refused / "CLAUDE.md").write_bytes(b"")
    found = go((0, []), parent=refused)
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": FAULT})
    assert "ValueError" in found.stderr
    assert stub.calls() == []
    assert [entry.name for entry in refused.iterdir()] == ["CLAUDE.md"]


def test_a_parent_inside_the_data_root(root, go, stub):
    started(root)
    found = go((0, []), parent=root)
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": FAULT})
    assert stub.calls() == []


def test_an_unexpected_exception_of_the_loop(root, go, stub, monkeypatch):
    started(root)

    def broken(**arguments):
        raise RuntimeError("broken loop")

    monkeypatch.setattr(turn_loop, "run", broken)
    found = go((0, []))
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": FAULT})
    assert "RuntimeError: broken loop" in found.stderr


def test_an_exception_of_reading_the_run(root, go, stub, monkeypatch):
    started(root)

    def denied(data_root, run_id):
        raise PermissionError("denied")

    monkeypatch.setattr(further_turn, "classify", denied)
    found = go((0, []))
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": FAULT})
    assert stub.calls() == []


def test_an_exception_without_words(root, go, stub, monkeypatch):
    class Wordless(Exception):
        def __str__(self):
            raise ValueError("no words")

    def broken(**arguments):
        raise Wordless

    started(root)
    monkeypatch.setattr(turn_loop, "run", broken)
    found = go((0, []))
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": FAULT})
    assert found.stderr == "hilclaw.turn_start: Wordless\n"


@pytest.mark.parametrize("error", [KeyboardInterrupt, SystemExit])
def test_an_interrupt_is_not_caught(root, parent, stub, monkeypatch, error):
    started(root)

    def interrupted(**arguments):
        raise error

    monkeypatch.setattr(turn_loop, "run", interrupted)
    with pytest.raises(error):
        start(parent, root=root)


# --- the standard streams ---


class Failing(io.BytesIO):
    def __init__(self, short=False):
        super().__init__()
        self.short = short

    def write(self, data):
        if self.short:
            return super().write(data[:1])
        raise OSError("broken pipe")


@pytest.mark.parametrize("short", [False, True])
def test_standard_output_that_cannot_be_written(root, parent, stub, short):
    over(root)
    stderr = io.BytesIO()
    status = main(
        [RUN], source=lambda: root, parent=parent, stdout=Failing(short), stderr=stderr
    )
    assert status == EXIT_ERROR
    lines = stderr.getvalue().decode().splitlines()
    assert len(lines) == 1 and "cannot write standard output" in lines[0]


def test_missing_standard_output_starts_no_turn(root, parent, stub, monkeypatch):
    started(root)
    stub.install((0, []))
    monkeypatch.setattr(sys, "stdout", object())
    stderr = io.BytesIO()
    standin = Standin()
    status = main(
        [RUN], source=lambda: root, check=standin, parent=parent, stderr=stderr
    )
    assert standin.calls == []
    assert status == EXIT_ERROR
    assert stub.calls() == []
    assert len(stderr.getvalue().splitlines()) == 1


def test_standard_error_that_cannot_be_written(root, parent, stub, monkeypatch):
    stdout = io.BytesIO()
    status = main([], stdout=stdout, stderr=Failing())
    assert status == EXIT_ERROR
    assert json.loads(stdout.getvalue()) == {"outcome": ERROR, "error": BAD_USAGE}
    monkeypatch.setattr(sys, "stderr", object())
    assert main([], stdout=io.BytesIO()) == EXIT_ERROR
    assert main([], stdout=io.BytesIO(), stderr=io.StringIO()) == EXIT_ERROR


@pytest.mark.parametrize(
    "run_id", ["", "-a", "Run-a", "a" * 65, "a.b", "a b", "../x", None, 1]
)
def test_no_prompt_for_an_invalid_run_id(run_id):
    with pytest.raises(InvalidPathValueError):
        prompt(run_id)


def test_one_line_on_standard_error(root, go, stub):
    found = go(source=lambda: "a\nb\rc")
    assert found.stderr.count("\n") == 1


def test_the_default_arguments(root, stub, monkeypatch, tmp_path):
    over(root)
    sessions = tmp_path / "default"
    sessions.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(sessions))
    monkeypatch.setattr(sys, "argv", ["turn_start", RUN])
    stdout = io.BytesIO()
    assert main(source=lambda: root, stdout=stdout, stderr=io.BytesIO()) == 0
    assert json.loads(stdout.getvalue()) == {"outcome": RUN_OVER}
    write(root, "run-b", instance_bytes())
    monkeypatch.setattr(sys, "argv", ["turn_start", "run-b"])
    stub.install((0, []))
    status = main(
        source=lambda: root, check=Standin(), stdout=io.BytesIO(), stderr=io.BytesIO()
    )
    assert status == EXIT_UNCHANGED_TURN
    assert len(stub.calls()) == 1
    assert list(sessions.iterdir()) == []


def test_the_module_runs_as_a_program(tmp_path):
    environment = dict(os.environ, PYTHONPATH=str(REPOSITORY))
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.turn_start"],
        capture_output=True,
        env=environment,
        cwd=tmp_path,
        check=False,
    )
    assert done.returncode == EXIT_ERROR
    assert json.loads(done.stdout) == {"outcome": ERROR, "error": BAD_USAGE}
    assert len(done.stderr.splitlines()) == 1


# --- the self-check (ADR-0125) ---


@pytest.fixture
def checks(tmp_path, monkeypatch):
    directory = tmp_path / "checks"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


def stopped(found, outcome):
    assert found.status == EXIT_STOPPED_AT_CHECK
    assert set(found.told) == {"outcome", "check"}
    assert found.told["outcome"] == STOPPED_AT_CHECK
    assert found.told["check"]["outcome"] == outcome
    assert found.stderr == ""


def test_a_passed_check_runs_once_before_the_first_turn(root, go, stub, checks):
    started(root)
    found = go(
        (0, [(STATE, state_text(1))]),
        (0, [(STATE, state_text(2, {"run_status": "over"}))], COMMIT),
        check=selfcheck.check,
    )
    assert found.status == EXIT_RUN_OVER and found.stderr == ""
    assert set(found.told) == {"outcome", "check"}
    assert found.told["outcome"] == RUN_OVER
    assert found.told["check"]["outcome"] == selfcheck_outcome.PASSED
    assert stub.kinds() == ["login", "check", "turn", "turn"]
    assert list(checks.iterdir()) == []


def test_not_logged_in_stops_before_any_session(root, go, stub, checks):
    started(root)
    stub.install((0, [(STATE, state_text(1))]), check="not_logged_in")
    before = snapshot(root)
    found = go(check=selfcheck.check)
    assert snapshot(root) == before
    stopped(found, selfcheck_login.NOT_LOGGED_IN)
    assert found.told["check"]["instruction"] == selfcheck_login.LOGIN_INSTRUCTION
    assert stub.kinds() == ["login"]


@pytest.mark.parametrize(
    "outcome", [selfcheck_outcome.FRONT_REFUSED, selfcheck_outcome.SESSION_FAILED]
)
def test_a_check_session_that_fails_starts_no_turn(root, go, stub, checks, outcome):
    stated(root, 2)
    stub.install((0, [(STATE, state_text(3))]), check=outcome)
    found = go(check=selfcheck.check)
    stopped(found, outcome)
    assert stub.kinds() == ["login", "check"]
    assert list(checks.iterdir()) == []


def test_no_call_lets_the_turn_start(root, go, stub, checks):
    started(root)
    stub.install((0, []), check="no_call")
    found = go(check=selfcheck.check)
    assert found.status == EXIT_UNCHANGED_TURN
    assert found.told["check"]["outcome"] == selfcheck_outcome.NO_CALL
    assert stub.kinds() == ["login", "check", "turn"]


def test_the_check_names_the_start_s_data_root(root, go, stub, checks, monkeypatch):
    started(root)
    handed, real = [], selfcheck.selfcheck_session.run

    def run(**options):
        handed.append(options["keep_out"])
        return real(**options)

    def configured():
        raise AssertionError("asked")

    monkeypatch.setattr(selfcheck.selfcheck_session, "run", run)
    monkeypatch.setattr(data_root_source, "configured", configured)
    found = go((0, []), check=selfcheck.check)
    assert found.status == EXIT_UNCHANGED_TURN
    assert handed == [(root,)]


@pytest.mark.parametrize("outcome", selfcheck_outcome.OUTCOMES)
def test_each_outcome_of_the_check(root, go, stub, outcome):
    started(root)
    standin = Standin(outcome)
    found = go((0, []), check=standin)
    turn = outcome in (selfcheck_outcome.PASSED, selfcheck_outcome.NO_CALL)
    if turn:
        told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    else:
        told_once(found, EXIT_STOPPED_AT_CHECK, {"outcome": STOPPED_AT_CHECK})
    assert len(stub.calls()) == (1 if turn else 0)
    assert standin.calls == [{"data_root": root}]


def test_a_fault_of_the_check_says_the_class_only(root, go, stub):
    started(root)
    standin = Standin(error=PermissionError(PLANTED))
    found = go((0, []), check=standin)
    assert found.status == EXIT_STOPPED_AT_CHECK
    assert found.told == {"outcome": STOPPED_AT_CHECK, "check_fault": "PermissionError"}
    assert found.stderr == "hilclaw.turn_start: fault of the check: PermissionError\n"
    assert "alice" not in found.lines[0].decode() + found.stderr
    assert stub.calls() == []


@pytest.mark.parametrize(
    "answer", [None, [], "passed", {}, {"outcome": 7}, {"outcome": "Passed"}]
)
def test_a_report_without_an_outcome_word_stops(root, go, stub, answer):
    started(root)
    standin = Standin()
    standin.report = answer
    found = go((0, []), check=standin)
    assert found.status == EXIT_STOPPED_AT_CHECK
    told = {"outcome": STOPPED_AT_CHECK}
    if type(answer) is dict:
        told["check"] = answer
    assert found.told == told
    assert found.stderr == ""
    assert stub.calls() == []


@pytest.mark.parametrize(
    "arrange",
    [
        over,
        lambda root: stated(root, 1, {"run_status": "stopped"}),
        open_missing_state,
    ],
)
def test_no_check_when_the_first_step_answers_no_turn(root, go, stub, arrange):
    arrange(root)
    standin = Standin()
    found = go((0, []), check=standin)
    assert "check" not in found.told
    assert standin.calls == [] and stub.kinds() == []


def test_no_check_after_an_error_before_the_first_step(root, go, stub):
    started(root)
    standin = Standin()
    found = go((0, []), args=(), check=standin)
    assert found.told == {"outcome": ERROR, "error": BAD_USAGE}

    def failing():
        raise config.ConfigError("no configuration")

    found = go((0, []), source=failing, check=standin)
    assert found.told == {"outcome": ERROR, "error": NO_DATA_ROOT}
    assert standin.calls == [] and stub.kinds() == []


def test_no_check_between_turns(root, go, stub):
    started(root)
    standin = Standin()
    found = go(
        (0, [(STATE, state_text(1))]),
        (0, [(STATE, state_text(2))]),
        (0, [(STATE, state_text(3))]),
        (0, []),
        check=standin,
    )
    told_once(found, EXIT_UNCHANGED_TURN, {"outcome": UNCHANGED_TURN})
    assert len(standin.calls) == 1 and len(stub.calls()) == 4


def test_a_later_start_checks_again(root, go, stub):
    started(root)
    standin = Standin()
    found = go((3, [(STATE, state_text(1))]), check=standin)
    told_once(found, EXIT_FAILED_TURN, {"outcome": FAILED_TURN, "exit_status": 3})
    found = go(
        (0, [(STATE, state_text(2, {"run_status": "over"}))], COMMIT), check=standin
    )
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    assert len(standin.calls) == 2 and len(stub.calls()) == 2


def test_no_claude_for_a_turn_keeps_the_report(root, go, stub):
    started(root)
    standin = Standin()
    found = go(check=standin)
    told_once(found, EXIT_ERROR, {"outcome": ERROR, "error": NO_CLAUDE})
    assert found.told["check"]["outcome"] == selfcheck_outcome.PASSED


def test_no_claude_for_the_check_is_no_error(root, go, stub, checks):
    started(root)
    found = go(check=selfcheck.check)
    stopped(found, selfcheck_login.NO_CLAUDE)
    assert found.told["outcome"] != ERROR
    assert stub.kinds() == []


@pytest.mark.parametrize("error", [KeyboardInterrupt, SystemExit])
def test_an_interrupt_of_the_check_is_not_caught(root, parent, stub, error):
    started(root)
    stub.install((0, []))
    with pytest.raises(error):
        start(parent, root=root, check=Standin(error=error()))
    assert stub.calls() == []
