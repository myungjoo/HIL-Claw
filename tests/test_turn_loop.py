import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from hilclaw import (
    caller_check,
    checkout_boundary,
    config,
    mcp_front,
    standin_image,
    turn_loop,
    turn_permissions,
)
from hilclaw.turn_loop import (
    CONFIG_FILE,
    MARKERS,
    OPT_MCP_CONFIG,
    OPT_PRINT,
    OPT_STRICT_MCP_CONFIG,
    PROGRAM,
    SERVERS_MEMBER,
    ClaudeNotFoundError,
    Turn,
    run,
)

PROMPT = "Run the next turn of the run, then stop."
DEFINITION = "definition.md"
MEETS = "the session directory would meet a checkout"
MARKER = "an instruction file or a foreign .claude lies above the session directory"
FIXED = ",".join(sorted(turn_permissions.ROUND_MANAGER_TOOLS))
IDLE = "CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT"
NO_BACKGROUND = "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"
AUTO_BACKGROUND = "CLAUDE_AUTO_BACKGROUND_TASKS"
UNRELATED = "HILCLAW_TEST_UNRELATED"
LEFT_ALONE = (
    "MCP_TOOL_TIMEOUT",
    "CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS",
    "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS",
)
SESSION = {IDLE: "0", NO_BACKGROUND: "1", AUTO_BACKGROUND: None}
RECORDED = [IDLE, NO_BACKGROUND, AUTO_BACKGROUND, UNRELATED, *LEFT_ALONE]
BYPASS = (
    "--dangerously-skip-permissions",
    "--allow-dangerously-skip-permissions",
    "bypassPermissions",
    "acceptEdits",
    "auto",
)

STUB = r"""
import json, os, sys
from pathlib import Path

here = Path(__file__).parent
scenario = json.loads((here / "scenario.json").read_text(encoding="utf-8"))
argv = sys.argv[1:]
config = None
if "--mcp-config" in argv:
    name = argv[argv.index("--mcp-config") + 1]
    if os.path.exists(name):
        config = json.loads(Path(name).read_text(encoding="utf-8"))
listing = sorted(os.listdir("."))
contents = {
    name: Path(name).read_text(encoding="utf-8")
    for name in listing
    if os.path.isfile(name)
}
settings_file = Path(".claude", "settings.json")
settings = (
    settings_file.read_text(encoding="utf-8") if settings_file.is_file() else None
)
claude_listing = sorted(os.listdir(".claude")) if os.path.isdir(".claude") else None
hooks = None
if scenario["hook_inputs"] and settings is not None:
    import subprocess

    handler = json.loads(settings)["hooks"]["PreToolUse"][0]["hooks"][0]
    hook_env = {**os.environ, "CLAUDE_PROJECT_DIR": os.getcwd()}
    hooks = []
    for hook_input in scenario["hook_inputs"]:
        done = subprocess.run(
            [handler["command"], *handler["args"]],
            input=json.dumps(hook_input).encode("utf-8"),
            env=hook_env,
            capture_output=True,
            timeout=120,
            check=False,
        )
        hooks.append({"status": done.returncode, "stdout": done.stdout.decode()})
with (here / "started.ndjson").open("a", encoding="utf-8") as record:
    entry = {
        "argv": argv,
        "cwd": os.getcwd(),
        "stdin": sys.stdin.read(),
        "listing": listing,
        "contents": contents,
        "config": config,
        "settings": settings,
        "claude_listing": claude_listing,
        "hooks": hooks,
        "env": {name: os.environ.get(name) for name in scenario["names"]},
    }
    record.write(json.dumps(entry) + "\n")
started = len((here / "started.ndjson").read_text(encoding="utf-8").splitlines())
statuses = scenario["statuses"]
sys.exit(statuses[min(started, len(statuses)) - 1])
"""


class Stub:
    def __init__(self, directory):
        self.directory = directory

    def install(self, statuses=(0,), hook_inputs=()):
        script = self.directory / "stub.py"
        script.write_text(STUB, encoding="utf-8")
        scenario = {
            "statuses": list(statuses),
            "names": RECORDED,
            "hook_inputs": list(hook_inputs),
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

    def calls(self):
        file = self.directory / "started.ndjson"
        if not file.exists():
            return []
        lines = file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]


@pytest.fixture(autouse=True)
def stub(tmp_path, monkeypatch):
    own = (Path.home() / ".claude").resolve()
    if markers_above(tmp_path, own=own):
        pytest.skip("a directory above the test's temporary directory holds a marker")
    directory = tmp_path / "bin"
    work = tmp_path / "work"
    directory.mkdir()
    work.mkdir()
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.chdir(work)
    assert shutil.which("claude") is None
    return Stub(directory)


@pytest.fixture(autouse=True)
def only_the_stub(stub, monkeypatch):
    real = subprocess.run

    def checked(command, **options):
        program = Path(command[0]).resolve()
        if program.name.startswith("claude"):
            assert program.parent == stub.directory.resolve()
        return real(command, **options)

    monkeypatch.setattr(subprocess, "run", checked)


@pytest.fixture
def data_root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


@pytest.fixture
def parent(tmp_path):
    directory = tmp_path / "sessions"
    directory.mkdir()
    return directory


class Predicate:
    def __init__(self, turns, answer=True):
        self.turns = turns
        self.answer = answer
        self.seen = []

    def __call__(self, previous):
        self.seen.append(previous)
        return self.answer if len(self.seen) <= self.turns else False


def put(text="the definition"):
    made = []

    def put_definition(directory):
        assert isinstance(directory, Path)
        (directory / DEFINITION).write_text(text, encoding="utf-8")
        made.append(directory)

    put_definition.made = made
    return put_definition


def go(data_root, parent, **changes):
    arguments = {
        "further_turn": Predicate(1),
        "put_definition": put(),
        "prompt": PROMPT,
        "data_root": data_root,
        "parent": parent,
    }
    arguments.update(changes)
    return run(**arguments)


def expected_argv(tools="", allowed=FIXED):
    return [
        OPT_PRINT,
        PROMPT,
        OPT_MCP_CONFIG,
        CONFIG_FILE,
        OPT_STRICT_MCP_CONFIG,
        "--setting-sources",
        "project",
        "--tools",
        tools,
        "--permission-mode",
        "dontAsk",
        "--allowedTools",
        allowed,
    ]


def put_agent(text):
    made = []

    def put_definition(directory):
        agents = directory / ".claude" / "agents"
        agents.mkdir(parents=True)
        (agents / "helper.md").write_text(text, encoding="utf-8")
        made.append(directory)

    put_definition.made = made
    return put_definition


def markers_above(path, *, own=None):
    for directory in Path(path).resolve().parents:
        for name in MARKERS:
            found = directory / name
            if os.path.lexists(found) and found.resolve() != own:
                return True
    return False


def test_public_names():
    assert PROGRAM == "claude"
    assert CONFIG_FILE != ".mcp.json"
    assert os.path.basename(CONFIG_FILE) == CONFIG_FILE
    assert SERVERS_MEMBER == "mcpServers"
    assert set(MARKERS) == {"CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude"}
    assert issubclass(ClaudeNotFoundError, LookupError)
    assert Turn._fields == ("exit_status", "removed")
    assert turn_loop.__doc__


def test_two_turns_then_stop(stub, data_root, parent):
    stub.install(statuses=(0, 0))
    further = Predicate(2)
    found = go(data_root, parent, further_turn=further)
    assert found == (Turn(0, True), Turn(0, True))
    assert further.seen == [None, 0, 0]
    calls = stub.calls()
    assert [call["argv"] for call in calls] == [expected_argv()] * 2
    assert [call["stdin"] for call in calls] == ["", ""]


def test_fresh_directory_per_turn(stub, data_root, parent):
    stub.install(statuses=(0, 0))
    put_definition = put("round manager")
    go(data_root, parent, further_turn=Predicate(2), put_definition=put_definition)
    calls = stub.calls()
    cwds = [Path(call["cwd"]).resolve() for call in calls]
    assert cwds == [path.resolve() for path in put_definition.made]
    assert cwds[0] != cwds[1]
    for call, cwd in zip(calls, cwds):
        assert cwd.parent == parent.resolve()
        assert call["listing"] == sorted([CONFIG_FILE, DEFINITION, ".claude"])
        assert call["contents"][DEFINITION] == "round manager"
        assert call["settings"] == settings_text()
        assert not cwd.exists()
    assert list(parent.iterdir()) == []


def test_configuration_content(stub, data_root, parent, monkeypatch):
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert set(call["config"]) == {SERVERS_MEMBER}
    assert set(call["config"][SERVERS_MEMBER]) == {mcp_front.SERVER_NAME}
    entry = call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]
    assert set(entry) == {"command", "args", "env"}
    assert entry["command"] == sys.executable
    assert entry["args"][:2] == ["-I", "-c"]
    assert entry["args"][3:] == [checkout_boundary.PACKAGE_DIRECTORY]
    assert "hilclaw.mcp_front" in entry["args"][2]
    assert entry["env"] == {config.ENV_LOCAL_PATH: os.path.realpath(data_root)}
    assert os.path.isabs(entry["env"][config.ENV_LOCAL_PATH])


def test_configuration_names_the_real_data_root(stub, tmp_path, parent):
    stub.install()
    real = tmp_path / "real-data"
    real.mkdir()
    relative = os.path.relpath(real, Path.cwd())
    go(relative, parent)
    (call,) = stub.calls()
    entry = call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]
    assert entry["env"][config.ENV_LOCAL_PATH] == os.path.realpath(real)


def server_env(call):
    return call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]["env"]


def test_configuration_forwards_the_image(stub, data_root, parent, monkeypatch):
    image = "Example/standin@sha256:" + "ab" * 32
    monkeypatch.setenv(standin_image.ENV_IMAGE, image)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call) == {
        config.ENV_LOCAL_PATH: os.path.realpath(data_root),
        standin_image.ENV_IMAGE: image,
    }


def test_configuration_forwards_the_image_unchecked(
    stub, data_root, parent, monkeypatch
):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "--privileged")
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call)[standin_image.ENV_IMAGE] == "--privileged"


@pytest.mark.parametrize("value", [None, ""])
def test_configuration_without_an_image(stub, data_root, parent, monkeypatch, value):
    if value is None:
        monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    else:
        monkeypatch.setenv(standin_image.ENV_IMAGE, value)
    monkeypatch.setenv(UNRELATED, "kept out")
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call) == {config.ENV_LOCAL_PATH: os.path.realpath(data_root)}


@pytest.mark.parametrize("later", [None, "example/standin:2"])
def test_image_read_once_per_loop(stub, data_root, parent, monkeypatch, later):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "example/standin:1")

    def further_turn(previous):
        if previous is not None:
            if later is None:
                monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
            else:
                monkeypatch.setenv(standin_image.ENV_IMAGE, later)
        return len(stub.calls()) < 3

    stub.install(statuses=(0, 0, 0))
    go(data_root, parent, further_turn=further_turn)
    calls = stub.calls()
    assert len(calls) == 3
    for call in calls:
        assert server_env(call)[standin_image.ENV_IMAGE] == "example/standin:1"


def test_image_not_set_at_start_stays_out(stub, data_root, parent, monkeypatch):
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)

    def further_turn(previous):
        monkeypatch.setenv(standin_image.ENV_IMAGE, "example/standin:3")
        return len(stub.calls()) < 2

    stub.install(statuses=(0, 0))
    go(data_root, parent, further_turn=further_turn)
    calls = stub.calls()
    assert len(calls) == 2
    for call in calls:
        assert standin_image.ENV_IMAGE not in server_env(call)


def test_no_turn_at_once(stub, data_root, parent):
    stub.install()
    further = Predicate(0)
    put_definition = put()
    assert (
        go(data_root, parent, further_turn=further, put_definition=put_definition) == ()
    )
    assert further.seen == [None]
    assert stub.calls() == []
    assert put_definition.made == []
    assert list(parent.iterdir()) == []


def test_failed_turn_status_passed_on_and_loop_goes_on(stub, data_root, parent):
    stub.install(statuses=(3, 0))
    further = Predicate(2)
    found = go(data_root, parent, further_turn=further)
    assert found == (Turn(3, True), Turn(0, True))
    assert further.seen == [None, 3, 0]
    assert isinstance(found[0].exit_status, int)


def test_keep_out_empty_and_given(stub, tmp_path, data_root, parent):
    stub.install(statuses=(0,))
    other = tmp_path / "other"
    other.mkdir()
    assert go(data_root, parent, keep_out=()) == (Turn(0, True),)
    assert go(data_root, parent, keep_out=[other]) == (Turn(0, True),)
    assert go(data_root, parent, keep_out=(str(other),)) == (Turn(0, True),)
    assert len(stub.calls()) == 3


def test_default_parent_is_the_temporary_directory(
    stub, tmp_path, data_root, monkeypatch
):
    stub.install()
    temporary = tmp_path / "tmp"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    assert go(data_root, None) == (Turn(0, True),)
    (call,) = stub.calls()
    assert Path(call["cwd"]).resolve().parent == temporary.resolve()


def test_given_parent(stub, data_root, parent):
    stub.install()
    go(data_root, str(parent))
    (call,) = stub.calls()
    assert Path(call["cwd"]).resolve().parent == parent.resolve()


@pytest.mark.parametrize("answer", [None, 1, 0, "yes", []])
def test_answer_not_a_bool(stub, data_root, parent, answer):
    stub.install()
    with pytest.raises(TypeError, match="bool"):
        go(data_root, parent, further_turn=lambda previous: answer)
    assert stub.calls() == []
    assert list(parent.iterdir()) == []


def test_answer_not_a_bool_after_a_turn(stub, data_root, parent):
    stub.install()
    answers = iter([True, 1])
    with pytest.raises(TypeError, match="bool"):
        go(data_root, parent, further_turn=lambda previous: next(answers))
    assert len(stub.calls()) == 1


@pytest.mark.parametrize("name", ["further_turn", "put_definition"])
@pytest.mark.parametrize("value", [None, 1, "callable"])
def test_not_callable(stub, data_root, parent, name, value):
    stub.install()
    with pytest.raises(TypeError, match=name):
        go(data_root, parent, **{name: value})
    assert stub.calls() == []


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "two\nlines",
        "line\r",
        "a;b",
        'quote"',
        "100%",
        "café",
        "a&b",
        "x|y",
        "\t",
        "-",
        "-p",
        "--x y",
        "-run-a",
        "a-b\n",
    ],
)
def test_bad_prompt_value(stub, data_root, parent, prompt):
    stub.install()
    with pytest.raises(ValueError, match="prompt"):
        go(data_root, parent, prompt=prompt)
    assert stub.calls() == []


@pytest.mark.parametrize("prompt", [None, b"bytes", 1, ["a"]])
def test_bad_prompt_type(stub, data_root, parent, prompt):
    stub.install()
    with pytest.raises(TypeError, match="prompt"):
        go(data_root, parent, prompt=prompt)


@pytest.mark.parametrize(
    "prompt",
    [
        "Az09 .,_",
        "Your run id is 20261009t012331z-9f3a6c1e0b7d4a52.",
        "run-a",
        "ends in -",
        "run-",
        "a--b - c",
        " -x",
    ],
)
def test_allowed_prompt_characters(stub, data_root, parent, prompt):
    stub.install()
    go(data_root, parent, prompt=prompt)
    (call,) = stub.calls()
    assert call["argv"][1] == prompt


def test_data_root_missing(stub, tmp_path, parent):
    stub.install()
    with pytest.raises(ValueError, match="existing directory"):
        go(tmp_path / "absent", parent)
    assert stub.calls() == []


def test_data_root_not_a_directory(stub, tmp_path, parent):
    stub.install()
    file = tmp_path / "file"
    file.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="existing directory"):
        go(file, parent)


@pytest.mark.parametrize("value", [None, 1, b"/tmp", ["/tmp"]])
def test_data_root_wrong_type(stub, parent, value):
    stub.install()
    with pytest.raises(TypeError, match="data_root"):
        go(value, parent)


class BytesPath:
    def __fspath__(self):
        return b"/tmp"


def test_data_root_bytes_path(stub, parent):
    with pytest.raises(TypeError, match="data_root"):
        go(BytesPath(), parent)


@pytest.mark.parametrize("make", [str, Path])
def test_keep_out_one_path(stub, tmp_path, data_root, parent, make):
    stub.install()
    with pytest.raises(TypeError, match="sequence"):
        go(data_root, parent, keep_out=make(tmp_path / "other"))


def test_keep_out_bad_item(stub, data_root, parent):
    with pytest.raises(TypeError, match="keep_out"):
        go(data_root, parent, keep_out=[1])


def test_parent_wrong_type(stub, data_root):
    with pytest.raises(TypeError, match="parent"):
        go(data_root, 1)


def test_parent_missing(stub, tmp_path, data_root):
    with pytest.raises(ValueError, match="existing directory"):
        go(data_root, tmp_path / "absent")


def test_parent_inside_the_package_directory(stub, data_root):
    stub.install()
    with pytest.raises(ValueError, match=MEETS):
        go(data_root, checkout_boundary.PACKAGE_DIRECTORY)
    with pytest.raises(ValueError, match=MEETS):
        go(data_root, Path(checkout_boundary.PACKAGE_DIRECTORY) / "hilclaw")
    assert stub.calls() == []


def test_parent_inside_data_root(stub, data_root):
    stub.install()
    inner = data_root / "runs"
    inner.mkdir()
    with pytest.raises(ValueError, match=MEETS):
        go(data_root, data_root)
    with pytest.raises(ValueError, match=MEETS):
        go(data_root, inner)
    assert list(inner.iterdir()) == []
    assert stub.calls() == []


def test_parent_containing_data_root(stub, tmp_path):
    stub.install()
    parent = tmp_path / "outer"
    root = parent / "data"
    root.mkdir(parents=True)
    with pytest.raises(ValueError, match=MEETS):
        go(root, parent)
    assert stub.calls() == []


def test_parent_inside_or_containing_keep_out(stub, tmp_path, data_root, parent):
    stub.install()
    other = tmp_path / "other"
    inner = other / "inner"
    inner.mkdir(parents=True)
    with pytest.raises(ValueError, match=MEETS):
        go(data_root, inner, keep_out=[other])
    with pytest.raises(ValueError, match=MEETS):
        go(data_root, tmp_path / "other", keep_out=[inner])
    assert stub.calls() == []


@pytest.mark.parametrize("name", ["CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"])
@pytest.mark.parametrize("depth", [0, 2])
def test_instruction_file_above(stub, tmp_path, data_root, name, depth):
    stub.install()
    top = tmp_path / "tree"
    parent = top.joinpath(*["level"] * depth)
    parent.mkdir(parents=True)
    (top / name).write_text("instructions", encoding="utf-8")
    with pytest.raises(ValueError, match=MARKER):
        go(data_root, parent)
    assert stub.calls() == []


def test_foreign_claude_directory_above(stub, tmp_path, data_root):
    stub.install()
    top = tmp_path / "tree"
    parent = top / "a" / "b"
    parent.mkdir(parents=True)
    (top / ".claude").mkdir()
    with pytest.raises(ValueError, match=MARKER):
        go(data_root, parent)
    assert stub.calls() == []


def test_own_claude_directory_accepted(stub, tmp_path, data_root, monkeypatch):
    if markers_above(tmp_path):
        pytest.skip("a directory above the test's temporary directory holds a marker")
    stub.install()
    home = tmp_path / "home"
    parent = home / "work"
    parent.mkdir(parents=True)
    (home / ".claude").mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    assert go(data_root, parent) == (Turn(0, True),)
    (home / "AGENTS.md").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=MARKER):
        go(data_root, parent)


def test_home_unknown_counts_claude_as_foreign(stub, tmp_path, data_root, monkeypatch):
    stub.install()
    top = tmp_path / "tree"
    parent = top / "p"
    parent.mkdir(parents=True)
    (top / ".claude").mkdir()

    def unknown(cls):
        raise RuntimeError("no home")

    monkeypatch.setattr(Path, "home", classmethod(unknown))
    with pytest.raises(ValueError, match=MARKER):
        go(data_root, parent)


def test_marker_placed_between_turns(stub, data_root, parent):
    stub.install(statuses=(0, 0))
    seen = []

    def further_turn(previous):
        seen.append(previous)
        if len(seen) == 2:
            (parent / "CLAUDE.md").write_text("late", encoding="utf-8")
        return True

    with pytest.raises(ValueError, match=MARKER):
        go(data_root, parent, further_turn=further_turn)
    assert seen == [None, 0]
    assert len(stub.calls()) == 1
    assert [path.name for path in parent.iterdir()] == ["CLAUDE.md"]


@pytest.mark.parametrize("directory", [False, True])
def test_definition_holds_the_configuration_name(stub, data_root, parent, directory):
    stub.install()
    made = []

    def put_definition(session):
        made.append(session)
        if directory:
            (session / CONFIG_FILE).mkdir()
        else:
            (session / CONFIG_FILE).write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="configuration file"):
        go(data_root, parent, put_definition=put_definition)
    assert stub.calls() == []
    assert not made[0].exists()


def test_definition_raises(stub, data_root, parent):
    stub.install()
    made = []

    def put_definition(session):
        made.append(session)
        (session / DEFINITION).write_text("partial", encoding="utf-8")
        raise OSError("copy failed")

    with pytest.raises(OSError, match="copy failed"):
        go(data_root, parent, put_definition=put_definition)
    assert stub.calls() == []
    assert not made[0].exists()
    assert list(parent.iterdir()) == []


def test_predicate_raises(stub, data_root, parent):
    stub.install()
    answers = iter([True])

    def further_turn(previous):
        return next(answers)

    with pytest.raises(StopIteration):
        go(data_root, parent, further_turn=further_turn)
    assert len(stub.calls()) == 1
    assert list(parent.iterdir()) == []


def test_claude_missing(stub, data_root, parent):
    put_definition = put()
    with pytest.raises(ClaudeNotFoundError, match="claude"):
        go(data_root, parent, put_definition=put_definition)
    assert len(put_definition.made) == 1
    assert not put_definition.made[0].exists()
    assert list(parent.iterdir()) == []


def test_claude_looked_up_at_each_turn(stub, data_root, parent):
    stub.install()
    seen = []

    def further_turn(previous):
        seen.append(previous)
        if len(seen) == 2:
            for launcher in stub.directory.glob("claude*"):
                launcher.unlink()
        return True

    with pytest.raises(ClaudeNotFoundError):
        go(data_root, parent, further_turn=further_turn)
    assert seen == [None, 0]
    assert len(stub.calls()) == 1


def test_executable_unknown(stub, data_root, parent, monkeypatch):
    stub.install()
    monkeypatch.setattr(sys, "executable", "")
    further = Predicate(1)
    with pytest.raises(RuntimeError, match="own path"):
        go(data_root, parent, further_turn=further)
    assert further.seen == []
    assert stub.calls() == []


def test_failed_removal_is_carried(stub, data_root, parent, monkeypatch):
    stub.install()
    monkeypatch.setattr(turn_loop, "_REMOVE_PAUSES_S", (0.0,))
    monkeypatch.setattr(shutil, "rmtree", lambda path, ignore_errors: None)
    assert go(data_root, parent) == (Turn(0, False),)


def test_server_entry_starts_the_front_from_elsewhere(
    stub, tmp_path, data_root, parent
):
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    entry = call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    done = subprocess.run(
        [entry["command"], *entry["args"]],
        cwd=elsewhere,
        env={**os.environ, **entry["env"]},
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == mcp_front.EXIT_END_OF_INPUT == 0
    assert done.stdout == b""


def test_an_agent_reaches_the_permission_options(stub, data_root, parent):
    stub.install()
    text = "---\nname: helper\ntools: Grep, mcp__hilclaw__blob_fetch\n---\nbody\n"
    go(data_root, parent, put_definition=put_agent(text))
    (call,) = stub.calls()
    allowed = sorted(
        {
            *turn_permissions.ROUND_MANAGER_TOOLS,
            "Agent(helper)",
            "Grep",
            "mcp__hilclaw__blob_fetch",
        }
    )
    assert call["argv"] == expected_argv("Agent,Grep", ",".join(allowed))
    for argument in call["argv"]:
        for word in BYPASS:
            assert word not in argument


def test_a_refused_agent_stops_the_turn(stub, data_root, parent):
    stub.install()
    put_definition = put_agent("---\nname: helper\ntools: Bash\n---\n")
    further = Predicate(1)
    with pytest.raises(ValueError, match="not admitted"):
        go(data_root, parent, further_turn=further, put_definition=put_definition)
    assert further.seen == [None]
    assert stub.calls() == []
    assert not put_definition.made[0].exists()
    assert list(parent.iterdir()) == []


def clear_session_variables(monkeypatch):
    for name in (*SESSION, UNRELATED, *LEFT_ALONE):
        monkeypatch.delenv(name, raising=False)


def session_part(call):
    return {name: call["env"][name] for name in SESSION}


def test_session_environment_with_nothing_set(stub, data_root, parent, monkeypatch):
    clear_session_variables(monkeypatch)
    monkeypatch.setenv(UNRELATED, "kept as it is")
    stub.install(statuses=(0, 0))
    assert go(data_root, parent, further_turn=Predicate(2)) == (
        Turn(0, True),
        Turn(0, True),
    )
    calls = stub.calls()
    assert len(calls) == 2
    for call in calls:
        assert session_part(call) == SESSION
        assert call["env"][UNRELATED] == "kept as it is"
        for name in LEFT_ALONE:
            assert call["env"][name] is None
    for name in SESSION:
        assert name not in os.environ


def test_session_environment_replaces_the_callers_values(
    stub, data_root, parent, monkeypatch
):
    clear_session_variables(monkeypatch)
    monkeypatch.setenv(IDLE, "60000")
    monkeypatch.setenv(NO_BACKGROUND, "0")
    monkeypatch.setenv(AUTO_BACKGROUND, "1")
    for name, value in zip(LEFT_ALONE, ("1000", "2000", "3000")):
        monkeypatch.setenv(name, value)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert session_part(call) == SESSION
    assert [call["env"][name] for name in LEFT_ALONE] == ["1000", "2000", "3000"]
    assert os.environ[IDLE] == "60000"
    assert os.environ[NO_BACKGROUND] == "0"
    assert os.environ[AUTO_BACKGROUND] == "1"


def test_session_environment_read_at_each_turn(stub, data_root, parent, monkeypatch):
    clear_session_variables(monkeypatch)
    monkeypatch.setenv(UNRELATED, "first")
    stub.install(statuses=(0, 0))
    seen = []

    def further_turn(previous):
        seen.append(previous)
        if len(seen) == 2:
            os.environ[UNRELATED] = "second"
            os.environ[IDLE] = "5"
            os.environ[NO_BACKGROUND] = "false"
            os.environ[AUTO_BACKGROUND] = "1"
        return len(seen) <= 2

    go(data_root, parent, further_turn=further_turn)
    first, second = stub.calls()
    assert first["env"][UNRELATED] == "first"
    assert second["env"][UNRELATED] == "second"
    assert session_part(first) == session_part(second) == SESSION
    assert os.environ[IDLE] == "5"
    assert os.environ[NO_BACKGROUND] == "false"
    assert os.environ[AUTO_BACKGROUND] == "1"


def test_callers_environment_unchanged_when_a_later_turn_raises(
    stub, data_root, parent, monkeypatch
):
    clear_session_variables(monkeypatch)
    monkeypatch.setenv(IDLE, "60000")
    monkeypatch.setenv(AUTO_BACKGROUND, "1")
    stub.install()
    before = dict(os.environ)
    seen = []

    def further_turn(previous):
        seen.append(previous)
        if len(seen) == 2:
            for launcher in stub.directory.glob("claude*"):
                launcher.unlink()
        return True

    with pytest.raises(ClaudeNotFoundError):
        go(data_root, parent, further_turn=further_turn)
    (call,) = stub.calls()
    assert session_part(call) == SESSION
    assert dict(os.environ) == before
    assert NO_BACKGROUND not in os.environ


def test_settings_file_beside_the_configuration(stub, data_root, parent, monkeypatch):
    clear_session_variables(monkeypatch)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert call["listing"] == sorted([CONFIG_FILE, DEFINITION, ".claude"])
    assert call["claude_listing"] == [turn_loop.SETTINGS_FILE]
    entry = call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]
    assert entry["env"] == {config.ENV_LOCAL_PATH: os.path.realpath(data_root)}
    assert list(parent.iterdir()) == []


@pytest.mark.skipif(os.name != "nt", reason="names fold to one case on Windows only")
def test_lower_case_names_on_windows(stub, data_root, parent, monkeypatch):
    clear_session_variables(monkeypatch)
    monkeypatch.setenv(AUTO_BACKGROUND.lower(), "1")
    monkeypatch.setenv(IDLE.lower(), "60000")
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert session_part(call) == SESSION
    assert os.environ[AUTO_BACKGROUND] == "1"


SETTINGS_TAKEN = "the definition holds the hook settings file"
NOT_PLAIN = "the session directory's .claude is no plain directory"
EXACT_MATCH = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- ,|")


def expected_settings():
    hook = {
        "type": "command",
        "command": os.path.abspath(sys.executable),
        "args": [
            "-I",
            "-c",
            caller_check.START,
            checkout_boundary.PACKAGE_DIRECTORY,
        ],
        "timeout": turn_loop.HOOK_TIMEOUT_S,
        "onFailure": "block",
    }
    matcher = "^" + caller_check.TOOL_PREFIX
    return {"hooks": {"PreToolUse": [{"matcher": matcher, "hooks": [hook]}]}}


def settings_text():
    return json.dumps(expected_settings())


def hook_input(tool, agent=None):
    payload = {
        "session_id": "session",
        "transcript_path": "transcript.jsonl",
        "cwd": ".",
        "permission_mode": "dontAsk",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {},
        "tool_use_id": "use",
    }
    if agent is not None:
        payload["agent_id"] = "agent-1"
        payload["agent_type"] = agent
    return payload


def make_link(target, link):
    try:
        os.symlink(target, link, target_is_directory=os.path.isdir(target))
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be made here")


def test_settings_names():
    assert turn_loop.SETTINGS_DIRECTORY == ".claude"
    assert turn_loop.SETTINGS_FILE == "settings.json"
    assert type(turn_loop.HOOK_TIMEOUT_S) is int
    assert 0 < turn_loop.HOOK_TIMEOUT_S < 600


def test_settings_content(stub, data_root, parent):
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    settings = json.loads(call["settings"])
    assert settings == expected_settings()
    assert set(settings) == {"hooks"}
    (group,) = settings["hooks"]["PreToolUse"]
    (hook,) = group["hooks"]
    assert hook["command"] == os.path.abspath(sys.executable)
    assert os.path.isabs(hook["command"])
    server = call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]
    assert os.path.samefile(hook["command"], server["command"])
    assert hook["args"][:2] == server["args"][:2]
    assert hook["args"][2] == caller_check.START
    assert hook["args"][3:] == server["args"][3:]
    assert group["matcher"].startswith("^")
    assert not set(group["matcher"]) <= EXACT_MATCH


def test_settings_written_in_every_turn(stub, data_root, parent):
    stub.install(statuses=(0, 0))
    go(data_root, parent, further_turn=Predicate(2))
    calls = stub.calls()
    assert len(calls) == 2
    assert [call["settings"] for call in calls] == [settings_text()] * 2
    assert list(parent.iterdir()) == []


def test_hook_runs_as_written_for_the_main_session(stub, data_root, parent):
    stub.install(
        hook_inputs=(
            hook_input("mcp__hilclaw__state_write"),
            hook_input("mcp__hilclaw__verdicts_write"),
        )
    )
    go(data_root, parent)
    (call,) = stub.calls()
    assert [hook["status"] for hook in call["hooks"]] == [
        caller_check.EXIT_PASS,
        caller_check.EXIT_REFUSE,
    ]
    assert [hook["stdout"] for hook in call["hooks"]] == ["", ""]


def test_hook_runs_as_written_for_a_sub_agent(stub, data_root, parent):
    stub.install(
        hook_inputs=(
            hook_input("mcp__hilclaw__verdicts_write", agent="helper"),
            hook_input("mcp__hilclaw__state_write", agent="helper"),
        )
    )
    text = "---\nname: helper\ntools: Grep, mcp__hilclaw__verdicts_write\n---\n"
    go(data_root, parent, put_definition=put_agent(text))
    (call,) = stub.calls()
    assert [hook["status"] for hook in call["hooks"]] == [
        caller_check.EXIT_PASS,
        caller_check.EXIT_REFUSE,
    ]


def test_settings_beside_the_agents(stub, data_root, parent):
    stub.install()
    put_definition = put_agent("---\nname: helper\ntools: Grep\n---\nbody\n")
    go(data_root, parent, put_definition=put_definition)
    (call,) = stub.calls()
    assert call["claude_listing"] == ["agents", turn_loop.SETTINGS_FILE]
    assert call["settings"] == settings_text()
    assert "Agent(helper)" in call["argv"][-1].split(",")
    assert not put_definition.made[0].exists()


def test_claude_directory_made_when_absent(stub, data_root, parent):
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert ".claude" in call["listing"]
    assert call["claude_listing"] == [turn_loop.SETTINGS_FILE]


def test_claude_directory_made_by_the_definition_kept(stub, data_root, parent):
    stub.install()

    def put_definition(session):
        (session / ".claude").mkdir()
        (session / ".claude" / "note.txt").write_text("kept", encoding="utf-8")

    go(data_root, parent, put_definition=put_definition)
    (call,) = stub.calls()
    assert call["claude_listing"] == ["note.txt", turn_loop.SETTINGS_FILE]


def refused(stub, data_root, parent, make, message):
    stub.install()
    made = []

    def put_definition(session):
        made.append(session)
        make(session)

    further = Predicate(1)
    with pytest.raises(ValueError) as caught:
        go(data_root, parent, further_turn=further, put_definition=put_definition)
    assert str(caught.value) == message
    assert further.seen == [None]
    assert stub.calls() == []
    assert not made[0].exists()
    assert list(parent.iterdir()) == []


def test_definition_settings_file_refused(stub, data_root, parent):
    def make(session):
        (session / ".claude").mkdir()
        (session / ".claude" / "settings.json").write_text("{}", encoding="utf-8")

    refused(stub, data_root, parent, make, SETTINGS_TAKEN)


def test_definition_settings_directory_refused(stub, data_root, parent):
    def make(session):
        (session / ".claude" / "settings.json").mkdir(parents=True)

    refused(stub, data_root, parent, make, SETTINGS_TAKEN)


def test_definition_settings_dangling_link_refused(stub, tmp_path, data_root, parent):
    missing = tmp_path / "missing.json"

    def make(session):
        (session / ".claude").mkdir()
        make_link(missing, session / ".claude" / "settings.json")

    refused(stub, data_root, parent, make, SETTINGS_TAKEN)
    assert not os.path.lexists(missing)


def test_claude_a_file_refused(stub, data_root, parent):
    def make(session):
        (session / ".claude").write_text("not a directory", encoding="utf-8")

    refused(stub, data_root, parent, make, NOT_PLAIN)


def test_claude_a_link_refused(stub, tmp_path, data_root, parent):
    target = tmp_path / "elsewhere"
    target.mkdir()
    (target / "kept.txt").write_text("unchanged", encoding="utf-8")

    def make(session):
        make_link(target, session / ".claude")

    refused(stub, data_root, parent, make, NOT_PLAIN)
    assert [path.name for path in target.iterdir()] == ["kept.txt"]
    assert (target / "kept.txt").read_text(encoding="utf-8") == "unchanged"


@pytest.mark.skipif(os.name != "nt", reason="junctions exist on Windows only")
def test_claude_a_junction_refused(stub, tmp_path, data_root, parent):
    import _winapi

    target = tmp_path / "elsewhere"
    target.mkdir()

    def make(session):
        _winapi.CreateJunction(str(target), str(session / ".claude"))

    refused(stub, data_root, parent, make, NOT_PLAIN)
    assert list(target.iterdir()) == []
