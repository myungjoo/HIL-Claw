import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from hilclaw import (
    budget_check,
    caller_check,
    checkout_boundary,
    coder_runtime,
    config,
    key_records,
    keys,
    layout,
    mcp_front,
    run_commit,
    standin_image,
    stop_check,
    turn_loop,
    turn_permissions,
)
from hilclaw.instance_file import write as write_instance
from hilclaw.journal import EMPTY
from hilclaw.run_state_file import replace as replace_state
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
LOOP_RUN = "loop-run-7"
DEFINITION = "definition.md"
MEETS = "the session directory would meet a checkout"
MARKER = "an instruction file or a foreign .claude lies above the session directory"
FIXED = ",".join(sorted(turn_permissions.ROUND_MANAGER_TOOLS))
IDLE = "CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT"
NO_BACKGROUND = "CLAUDE_CODE_DISABLE_BACKGROUND_TASKS"
AUTO_BACKGROUND = "CLAUDE_AUTO_BACKGROUND_TASKS"
UNRELATED = "HILCLAW_TEST_UNRELATED"
CODER_IMAGE = coder_runtime.ENV_IMAGE
CODER_TOKEN = coder_runtime.ENV_TOKEN
REFERENCE = "${HILCLAW_CODER_OAUTH_TOKEN}"
SENTINEL = "synthetic-coder-token-T0425-sentinel"
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
import json, os, re, sys
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
EXACT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_- ,|")


def matches(matcher, name):
    if matcher in ("", "*"):
        return True
    if set(matcher) <= EXACT:
        return name in [part.strip() for part in re.split(r"[|,]", matcher)]
    return re.search(matcher, name) is not None


hooks = None
if scenario["hook_inputs"] and settings is not None:
    import subprocess

    entries = json.loads(settings)["hooks"]["PreToolUse"]
    hook_env = {**os.environ, "CLAUDE_PROJECT_DIR": os.getcwd()}
    hooks = []
    for hook_input in scenario["hook_inputs"]:
        ran = []
        for index, entry in enumerate(entries):
            if not matches(entry.get("matcher", ""), hook_input["tool_name"]):
                continue
            for handler in entry["hooks"]:
                done = subprocess.run(
                    [handler["command"], *handler["args"]],
                    input=json.dumps(hook_input).encode("utf-8"),
                    env=hook_env,
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
                ran.append(
                    {
                        "entry": index,
                        "status": done.returncode,
                        "stdout": done.stdout.decode(),
                        "stderr": done.stderr.decode(),
                    }
                )
        hooks.append(ran)
stops = None
if scenario["stop_inputs"] and settings is not None:
    import subprocess

    stop_entries = json.loads(settings)["hooks"].get("Stop", [])
    hook_env = {**os.environ, "CLAUDE_PROJECT_DIR": os.getcwd()}
    stops = []
    for stop_input in scenario["stop_inputs"]:
        ran = []
        for index, entry in enumerate(stop_entries):
            for handler in entry["hooks"]:
                done = subprocess.run(
                    [handler["command"], *handler["args"]],
                    input=json.dumps(stop_input).encode("utf-8"),
                    env=hook_env,
                    capture_output=True,
                    timeout=120,
                    check=False,
                )
                ran.append(
                    {
                        "entry": index,
                        "status": done.returncode,
                        "stdout": done.stdout.decode(),
                        "stderr": done.stderr.decode(),
                    }
                )
        stops.append(ran)
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
        "stops": stops,
        "env": {name: os.environ.get(name) for name in scenario["names"]},
    }
    record.write(json.dumps(entry) + "\n")
for name, stream in (("out", sys.stdout), ("err", sys.stderr)):
    if scenario[name]:
        stream.buffer.write(scenario[name].encode("utf-8"))
        stream.flush()
started = len((here / "started.ndjson").read_text(encoding="utf-8").splitlines())
statuses = scenario["statuses"]
sys.exit(statuses[min(started, len(statuses)) - 1])
"""


class Stub:
    def __init__(self, directory):
        self.directory = directory

    def install(self, statuses=(0,), hook_inputs=(), stop_inputs=(), out="", err=""):
        script = self.directory / "stub.py"
        script.write_text(STUB, encoding="utf-8")
        scenario = {
            "statuses": list(statuses),
            "out": out,
            "err": err,
            "names": RECORDED,
            "hook_inputs": list(hook_inputs),
            "stop_inputs": list(stop_inputs),
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
        "run_id": LOOP_RUN,
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
        assert call["settings"] == settings_text(data_root)
        assert not cwd.exists()
    assert list(parent.iterdir()) == []


def clear_coder(monkeypatch):
    monkeypatch.delenv(CODER_IMAGE, raising=False)
    monkeypatch.delenv(CODER_TOKEN, raising=False)


def test_configuration_content(stub, data_root, parent, monkeypatch):
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    clear_coder(monkeypatch)
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
    clear_coder(monkeypatch)
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
    clear_coder(monkeypatch)
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


def test_configuration_forwards_the_coder_image(stub, data_root, parent, monkeypatch):
    image = "Example/coder@sha256:" + "cd" * 32
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    monkeypatch.delenv(CODER_TOKEN, raising=False)
    monkeypatch.setenv(CODER_IMAGE, image)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call) == {
        config.ENV_LOCAL_PATH: os.path.realpath(data_root),
        CODER_IMAGE: image,
    }


def test_configuration_forwards_the_coder_image_unchecked(
    stub, data_root, parent, monkeypatch
):
    monkeypatch.setenv(CODER_IMAGE, "--privileged")
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call)[CODER_IMAGE] == "--privileged"


@pytest.mark.parametrize("value", [None, ""])
@pytest.mark.parametrize("name", [CODER_IMAGE, CODER_TOKEN])
def test_configuration_without_a_coder_variable(
    stub, data_root, parent, monkeypatch, name, value
):
    monkeypatch.setenv(CODER_IMAGE, "example/coder:1")
    monkeypatch.setenv(CODER_TOKEN, SENTINEL)
    if value is None:
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(name, value)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert name not in server_env(call)
    other = CODER_TOKEN if name == CODER_IMAGE else CODER_IMAGE
    assert other in server_env(call)


def written_texts(call):
    return [*call["contents"].values(), call["settings"], *call["argv"]]


def test_configuration_holds_the_token_reference_and_never_the_value(
    stub, data_root, parent, monkeypatch
):
    monkeypatch.setenv(CODER_TOKEN, SENTINEL)
    stub.install(statuses=(0, 0))
    go(data_root, parent, further_turn=Predicate(2))
    calls = stub.calls()
    assert len(calls) == 2
    for call in calls:
        assert server_env(call)[CODER_TOKEN] == REFERENCE
        assert REFERENCE in call["contents"][CONFIG_FILE]
        for text in written_texts(call):
            assert SENTINEL not in text
    assert list(parent.iterdir()) == []


def test_configuration_writes_the_reference_for_a_value_that_is_the_reference(
    stub, data_root, parent, monkeypatch
):
    monkeypatch.setenv(CODER_TOKEN, REFERENCE)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call)[CODER_TOKEN] == REFERENCE
    assert call["contents"][CONFIG_FILE].count("HILCLAW_CODER_OAUTH_TOKEN") == 2


def test_configuration_copies_nothing_else_of_the_environment(
    stub, data_root, parent, monkeypatch
):
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    clear_coder(monkeypatch)
    for name in ("CLAUDE_CODE_OAUTH_TOKEN", "DOCKER_HOST", "DOCKER_CONTEXT", UNRELATED):
        monkeypatch.setenv(name, SENTINEL)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call) == {config.ENV_LOCAL_PATH: os.path.realpath(data_root)}
    assert SENTINEL not in call["contents"][CONFIG_FILE]


def test_configuration_with_every_variable(stub, data_root, parent, monkeypatch):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "example/standin:1")
    monkeypatch.setenv(CODER_IMAGE, "example/coder:1")
    monkeypatch.setenv(CODER_TOKEN, SENTINEL)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", SENTINEL)
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    assert server_env(call) == {
        config.ENV_LOCAL_PATH: os.path.realpath(data_root),
        standin_image.ENV_IMAGE: "example/standin:1",
        CODER_IMAGE: "example/coder:1",
        CODER_TOKEN: REFERENCE,
    }


@pytest.mark.parametrize("later", [None, "changed"])
def test_coder_variables_read_once_per_loop(
    stub, data_root, parent, monkeypatch, later
):
    monkeypatch.setenv(CODER_IMAGE, "example/coder:1")
    monkeypatch.setenv(CODER_TOKEN, SENTINEL)

    def further_turn(previous):
        if previous is not None:
            for name in (CODER_IMAGE, CODER_TOKEN):
                if later is None:
                    monkeypatch.delenv(name, raising=False)
                else:
                    monkeypatch.setenv(name, later)
        return len(stub.calls()) < 3

    stub.install(statuses=(0, 0, 0))
    go(data_root, parent, further_turn=further_turn)
    calls = stub.calls()
    assert len(calls) == 3
    for call in calls:
        assert server_env(call)[CODER_IMAGE] == "example/coder:1"
        assert server_env(call)[CODER_TOKEN] == REFERENCE


def test_coder_variables_not_set_at_start_stay_out(
    stub, data_root, parent, monkeypatch
):
    clear_coder(monkeypatch)

    def further_turn(previous):
        monkeypatch.setenv(CODER_IMAGE, "example/coder:3")
        monkeypatch.setenv(CODER_TOKEN, SENTINEL)
        return len(stub.calls()) < 2

    stub.install(statuses=(0, 0))
    go(data_root, parent, further_turn=further_turn)
    calls = stub.calls()
    assert len(calls) == 2
    for call in calls:
        assert CODER_IMAGE not in server_env(call)
        assert CODER_TOKEN not in server_env(call)


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


REPLY = "the reply of the session\n"
DIAGNOSTIC = "a diagnostic of the session\n"


def no_standard_error(monkeypatch):
    real = os.fstat

    def fstat(fd):
        if fd == 2:
            raise OSError(9, "Bad file descriptor")
        return real(fd)

    monkeypatch.setattr(os, "fstat", fstat)


def test_session_streams_go_to_standard_error(stub, data_root, parent, capfd):
    stub.install(out=REPLY, err=DIAGNOSTIC)
    capfd.readouterr()
    assert go(data_root, parent) == (Turn(0, True),)
    found = capfd.readouterr()
    assert found.out == ""
    assert found.err == REPLY + DIAGNOSTIC


def test_session_output_of_every_turn_in_order(stub, data_root, parent, capfd):
    stub.install(statuses=(0, 4), out=REPLY, err=DIAGNOSTIC)
    capfd.readouterr()
    found = go(data_root, parent, further_turn=Predicate(2))
    assert found == (Turn(0, True), Turn(4, True))
    captured = capfd.readouterr()
    assert captured.out == ""
    assert captured.err == (REPLY + DIAGNOSTIC) * 2


def test_reply_without_a_line_feed(stub, data_root, parent, capfd):
    stub.install(statuses=(3,), out="no line feed")
    capfd.readouterr()
    assert go(data_root, parent) == (Turn(3, True),)
    found = capfd.readouterr()
    assert found.out == ""
    assert found.err == "no line feed"


def test_session_that_writes_nothing(stub, data_root, parent, capfd):
    stub.install()
    capfd.readouterr()
    assert go(data_root, parent) == (Turn(0, True),)
    assert capfd.readouterr() == ("", "")


def test_without_standard_error_the_reply_is_discarded(
    stub, data_root, parent, capfd, monkeypatch
):
    stub.install(statuses=(5,), out=REPLY, err=DIAGNOSTIC)
    no_standard_error(monkeypatch)
    capfd.readouterr()
    assert go(data_root, parent) == (Turn(5, True),)
    found = capfd.readouterr()
    assert found.out == ""
    assert found.err == DIAGNOSTIC


def test_session_streams_are_not_read(stub, data_root, parent, monkeypatch):
    stub.install(out=REPLY)
    real = subprocess.run
    seen = []

    def recorded(command, **options):
        seen.append(options)
        return real(command, **options)

    monkeypatch.setattr(subprocess, "run", recorded)
    go(data_root, parent)
    (options,) = seen
    assert options["stdout"] == 2
    assert "stderr" not in options
    assert "capture_output" not in options
    no_standard_error(monkeypatch)
    seen.clear()
    go(data_root, parent)
    (options,) = seen
    assert options["stdout"] is subprocess.DEVNULL
    assert "stderr" not in options


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
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    clear_coder(monkeypatch)
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


def expected_settings(root, run_id=LOOP_RUN):
    def entry(matcher, *args):
        hook = {
            "type": "command",
            "command": os.path.abspath(sys.executable),
            "args": ["-I", "-c", *args],
            "timeout": turn_loop.HOOK_TIMEOUT_S,
            "onFailure": "block",
        }
        return {"matcher": matcher, "hooks": [hook]}

    package = checkout_boundary.PACKAGE_DIRECTORY
    real = os.path.realpath(root)
    return {
        "hooks": {
            "PreToolUse": [
                entry("^" + caller_check.TOOL_PREFIX, caller_check.START, package),
                entry(
                    "|".join(budget_check.SPENDING_TOOLS),
                    budget_check.START,
                    package,
                    real,
                ),
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": os.path.abspath(sys.executable),
                            "args": [
                                "-I",
                                "-c",
                                stop_check.START,
                                package,
                                run_id,
                                real,
                            ],
                            "timeout": turn_loop.STOP_HOOK_TIMEOUT_S,
                        }
                    ]
                }
            ],
        }
    }


def settings_text(root, run_id=LOOP_RUN):
    return json.dumps(expected_settings(root, run_id))


def hook_input(tool, agent=None, tool_input=None):
    payload = {
        "session_id": "session",
        "transcript_path": "transcript.jsonl",
        "cwd": ".",
        "permission_mode": "dontAsk",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": {} if tool_input is None else tool_input,
        "tool_use_id": "use",
    }
    if agent is not None:
        payload["agent_id"] = "agent-1"
        payload["agent_type"] = agent
    return payload


RUN = "run-a"
CODER = "mcp__hilclaw__coder_run"
CHECK = "mcp__hilclaw__correctness_check"
HW_PROFILE = {
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


def stated(root, at=0, others=None, budget=5):
    document = {
        "schema_version": 1,
        "hw_profile": {
            "key": keys.hw_profile_key(HW_PROFILE).name,
            "record": HW_PROFILE,
        },
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "round_budget": budget,
    }
    write_instance(root, RUN, json.dumps(document).encode() + b"\n")
    replace_state(root, RUN, at, EMPTY, others)


SPENDER = f"---\nname: spender\ntools: Grep, {CODER}, {CHECK}\n---\n"


def spending(tool=CHECK, run_id=RUN, agent="spender"):
    tool_input = {} if run_id is None else {"run_id": run_id}
    return hook_input(tool, agent=agent, tool_input=tool_input)


def hooks_run(stub, data_root, parent, *inputs):
    stub.install(hook_inputs=inputs)
    go(data_root, parent, put_definition=put_agent(SPENDER))
    return stub.calls()[0]["hooks"]


def refusal(tool):
    return budget_check.REFUSAL.format(f" of {tool}")


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
    assert type(turn_loop.STOP_HOOK_TIMEOUT_S) is int
    assert 0 < turn_loop.STOP_HOOK_TIMEOUT_S < 600


def test_settings_content(stub, data_root, parent):
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    settings = json.loads(call["settings"])
    assert settings == expected_settings(data_root)
    assert set(settings) == {"hooks"}
    assert list(settings["hooks"]) == ["PreToolUse", "Stop"]
    first, second = settings["hooks"]["PreToolUse"]
    (hook,) = first["hooks"]
    assert hook["command"] == os.path.abspath(sys.executable)
    assert os.path.isabs(hook["command"])
    server = call["config"][SERVERS_MEMBER][mcp_front.SERVER_NAME]
    assert os.path.samefile(hook["command"], server["command"])
    assert hook["args"][:2] == server["args"][:2]
    assert hook["args"][2] == caller_check.START
    assert hook["args"][3:] == server["args"][3:]
    assert first["matcher"].startswith("^")
    assert not set(first["matcher"]) <= EXACT_MATCH
    (budget,) = second["hooks"]
    assert set(budget) == set(hook)
    assert budget["command"] == hook["command"]
    assert budget["args"][:2] == ["-I", "-c"]
    assert budget["args"][2] == budget_check.START
    assert budget["args"][3] == checkout_boundary.PACKAGE_DIRECTORY
    root = budget["args"][4]
    assert root == os.path.realpath(data_root)
    assert root == server["env"][config.ENV_LOCAL_PATH]
    assert os.path.isabs(root)
    assert budget["onFailure"] == "block"
    assert 0 < budget["timeout"] < 600
    assert set(second["matcher"]) <= EXACT_MATCH
    assert "^" not in second["matcher"]
    assert second["matcher"].split("|") == list(budget_check.SPENDING_TOOLS)


def test_settings_written_in_every_turn(stub, data_root, parent):
    stub.install(statuses=(0, 0))
    go(data_root, parent, further_turn=Predicate(2))
    calls = stub.calls()
    assert len(calls) == 2
    assert [call["settings"] for call in calls] == [settings_text(data_root)] * 2
    assert list(parent.iterdir()) == []


def budget_root(call):
    return json.loads(call["settings"])["hooks"]["PreToolUse"][1]["hooks"][0]["args"][
        -1
    ]


def stop_args(call):
    return json.loads(call["settings"])["hooks"]["Stop"][0]["hooks"][0]["args"]


def test_settings_name_the_real_data_root_given_relative(stub, tmp_path, parent):
    stub.install()
    real = tmp_path / "real-data"
    real.mkdir()
    go(os.path.relpath(real, Path.cwd()), parent)
    (call,) = stub.calls()
    assert budget_root(call) == os.path.realpath(real)
    assert budget_root(call) == server_env(call)[config.ENV_LOCAL_PATH]
    assert os.path.isabs(budget_root(call))
    assert stop_args(call)[-1] == budget_root(call)


def test_settings_name_the_real_data_root_given_a_link(stub, tmp_path, parent):
    stub.install()
    real = tmp_path / "real-data"
    real.mkdir()
    link = tmp_path / "linked-data"
    make_link(real, link)
    go(link, parent)
    (call,) = stub.calls()
    assert os.path.normcase(budget_root(call)) == os.path.normcase(
        os.path.realpath(real)
    )
    assert budget_root(call) == server_env(call)[config.ENV_LOCAL_PATH]
    assert stop_args(call)[-1] == budget_root(call)


@pytest.mark.parametrize(
    "placeholder",
    ["${CLAUDE_PROJECT_DIR}", "${CLAUDE_PLUGIN_ROOT}", "${CLAUDE_PLUGIN_DATA}"],
)
def test_data_root_holding_a_placeholder_refused(stub, tmp_path, parent, placeholder):
    stub.install()
    root = tmp_path / placeholder / "data"
    root.mkdir(parents=True)
    further = Predicate(1)
    with pytest.raises(ValueError) as caught:
        go(root, parent, further_turn=further)
    assert str(caught.value) == "data_root holds a hook path placeholder"
    assert further.seen == []
    assert stub.calls() == []


@pytest.mark.parametrize(
    "name", ["$CLAUDE_PROJECT_DIR", "${OTHER}", "{CLAUDE_PLUGIN_ROOT}"]
)
def test_data_root_with_other_dollar_names_accepted(stub, tmp_path, parent, name):
    stub.install()
    root = tmp_path / name
    root.mkdir()
    go(root, parent)
    (call,) = stub.calls()
    assert budget_root(call) == os.path.realpath(root)


def statuses(ran):
    return [(hook["entry"], hook["status"]) for hook in ran]


def test_hook_runs_as_written_for_the_main_session(stub, data_root, parent):
    stub.install(
        hook_inputs=(
            hook_input("mcp__hilclaw__state_write"),
            hook_input("mcp__hilclaw__verdicts_write"),
        )
    )
    go(data_root, parent)
    (call,) = stub.calls()
    assert [statuses(ran) for ran in call["hooks"]] == [
        [(0, caller_check.EXIT_PASS)],
        [(0, caller_check.EXIT_REFUSE)],
    ]
    assert [[hook["stdout"] for hook in ran] for ran in call["hooks"]] == [[""], [""]]


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
    assert [statuses(ran) for ran in call["hooks"]] == [
        [(0, caller_check.EXIT_PASS)],
        [(0, caller_check.EXIT_REFUSE)],
    ]


def test_spending_call_within_budget_passes_both(stub, data_root, parent):
    stated(data_root, at=0, budget=5)
    for ran in hooks_run(stub, data_root, parent, spending(CHECK), spending(CODER)):
        first, second = ran
        assert (first["entry"], first["status"], first["stdout"]) == (0, 0, "")
        assert (second["entry"], second["status"], second["stdout"]) == (1, 0, "")
        assert second["stderr"] == ""


def refused_by_the_budget(ran, tool):
    first, second = ran
    assert (first["entry"], first["status"]) == (0, caller_check.EXIT_PASS)
    assert (second["entry"], second["status"]) == (1, budget_check.EXIT_REFUSE)
    assert second["stdout"] == ""
    assert second["stderr"].splitlines() == [refusal(tool)]


def test_spending_call_on_a_run_over_refused(stub, data_root, parent):
    stated(data_root, at=1, others={"run_status": "over"}, budget=5)
    (ran,) = hooks_run(stub, data_root, parent, spending(CHECK))
    refused_by_the_budget(ran, CHECK)


def test_spending_call_at_the_round_budget_refused(stub, data_root, parent):
    stated(data_root, at=5, budget=5)
    found = hooks_run(stub, data_root, parent, spending(CHECK), spending(CODER))
    for ran, tool in zip(found, (CHECK, CODER), strict=True):
        refused_by_the_budget(ran, tool)


def test_spending_call_on_an_unreadable_run_refused(stub, data_root, parent):
    (ran,) = hooks_run(stub, data_root, parent, spending(CHECK, run_id="run-missing"))
    refused_by_the_budget(ran, CHECK)


def test_spending_call_without_a_run_id_refused(stub, data_root, parent):
    stated(data_root)
    (ran,) = hooks_run(stub, data_root, parent, spending(CODER, run_id=None))
    refused_by_the_budget(ran, CODER)


def test_coder_run_of_a_sub_agent_on_a_run_over_refused(stub, data_root, parent):
    stated(data_root, at=2, others={"run_status": "over"}, budget=5)
    (ran,) = hooks_run(stub, data_root, parent, spending(CODER))
    refused_by_the_budget(ran, CODER)


def test_main_session_spending_call_meets_both_checks(stub, data_root, parent):
    stated(data_root, at=0, budget=5)
    (ran,) = hooks_run(stub, data_root, parent, spending(CHECK, agent=None))
    assert statuses(ran) == [(0, caller_check.EXIT_REFUSE), (1, budget_check.EXIT_PASS)]


def test_non_spending_call_runs_the_caller_check_only(stub, data_root, parent):
    stated(data_root, at=2, others={"run_status": "over"}, budget=5)
    read = hook_input("mcp__hilclaw__state_read", tool_input={"run_id": RUN})
    (ran,) = hooks_run(stub, data_root, parent, read)
    assert statuses(ran) == [(0, caller_check.EXIT_PASS)]


def test_settings_beside_the_agents(stub, data_root, parent):
    stub.install()
    put_definition = put_agent("---\nname: helper\ntools: Grep\n---\nbody\n")
    go(data_root, parent, put_definition=put_definition)
    (call,) = stub.calls()
    assert call["claude_listing"] == ["agents", turn_loop.SETTINGS_FILE]
    assert call["settings"] == settings_text(data_root)
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
    (target / "kept.txt").write_text("unchanged", encoding="utf-8")

    def make(session):
        _winapi.CreateJunction(str(target), str(session / ".claude"))

    refused(stub, data_root, parent, make, NOT_PLAIN)
    assert [path.name for path in target.iterdir()] == ["kept.txt"]
    assert (target / "kept.txt").read_text(encoding="utf-8") == "unchanged"


def stop_entry(call):
    return json.loads(call["settings"])["hooks"]["Stop"]


def test_stop_entry_has_no_matcher_and_no_on_failure(stub, data_root, parent):
    stub.install()
    go(data_root, parent)
    (call,) = stub.calls()
    (entry,) = stop_entry(call)
    assert set(entry) == {"hooks"}
    (hook,) = entry["hooks"]
    assert set(hook) == {"type", "command", "args", "timeout"}
    assert hook["type"] == "command"
    assert hook["command"] == os.path.abspath(sys.executable)
    assert hook["timeout"] == turn_loop.STOP_HOOK_TIMEOUT_S
    assert hook["timeout"] < 600
    assert hook["args"] == [
        "-I",
        "-c",
        stop_check.START,
        checkout_boundary.PACKAGE_DIRECTORY,
        LOOP_RUN,
        os.path.realpath(data_root),
    ]
    assert hook["args"][-1] == budget_root(call)
    assert hook["args"][-1] == server_env(call)[config.ENV_LOCAL_PATH]


EDGE_IDS = [
    "a",
    "7",
    "a" * 64,
    "a-b_c",
    "run-",
    "20261009t012331z-9f3a6c1e0b7d4a52",
]


@pytest.mark.parametrize("run_id", EDGE_IDS)
def test_any_valid_run_id_reaches_the_stop_entry(stub, data_root, parent, run_id):
    stub.install()
    go(data_root, parent, run_id=run_id)
    (call,) = stub.calls()
    assert stop_args(call)[-2] == run_id
    assert call["settings"] == settings_text(data_root, run_id)


def test_run_id_not_compared_with_the_prompt(stub, data_root, parent):
    stub.install()
    run_id = "zz-not-in-the-prompt"
    assert run_id not in PROMPT
    go(data_root, parent, run_id=run_id)
    (call,) = stub.calls()
    assert call["argv"] == expected_argv()
    assert stop_args(call)[-2] == run_id


def test_run_id_appears_nowhere_but_the_stop_entry(stub, data_root, parent):
    stub.install()
    run_id = "zq-unique-run-id-41"
    go(data_root, parent, run_id=run_id)
    (call,) = stub.calls()
    settings = json.loads(call["settings"])
    assert settings["hooks"]["Stop"][0]["hooks"][0]["args"].pop(-2) == run_id
    assert run_id not in json.dumps(settings)
    assert run_id not in json.dumps(call["config"])
    assert run_id not in json.dumps(call["argv"])
    assert run_id not in json.dumps(call["env"])
    assert run_id not in json.dumps(call["contents"])


def test_missing_run_id_is_a_type_error(stub, data_root, parent):
    stub.install()
    further = Predicate(1)
    with pytest.raises(TypeError):
        run(
            further_turn=further,
            put_definition=put(),
            prompt=PROMPT,
            data_root=data_root,
            parent=parent,
        )
    assert further.seen == []
    assert stub.calls() == []
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize(
    "run_id",
    [None, 1, b"run-a", "", "Run-A", "-a", "a" * 65, "a/b", "..\\a", "a b", "a\n"],
)
def test_refused_run_id(stub, data_root, parent, monkeypatch, run_id):
    stub.install()
    made = []
    real = tempfile.mkdtemp

    def watched(*args, **options):
        made.append(1)
        return real(*args, **options)

    monkeypatch.setattr(tempfile, "mkdtemp", watched)
    further = Predicate(1)
    definition = put()
    with pytest.raises(layout.InvalidPathValueError):
        go(
            data_root,
            parent,
            further_turn=further,
            put_definition=definition,
            run_id=run_id,
        )
    assert issubclass(layout.InvalidPathValueError, ValueError)
    assert made == []
    assert further.seen == []
    assert definition.made == []
    assert stub.calls() == []
    assert list(parent.iterdir()) == []


def test_every_turn_writes_the_same_stop_entry(stub, data_root, parent):
    stub.install(statuses=(0, 0))
    go(data_root, parent, further_turn=Predicate(2))
    first, second = stub.calls()
    assert stop_entry(first) == stop_entry(second)
    assert stop_args(first)[-2:] == [LOOP_RUN, os.path.realpath(data_root)]


GIT = shutil.which("git")
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Test Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
}
GIT_LOCATING = (
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


@pytest.fixture
def isolated_git(stub, monkeypatch, tmp_path_factory):
    if GIT is None:
        pytest.skip("git is not on PATH, so the hook cannot read a data checkout")
    config_file = tmp_path_factory.mktemp("git-config") / "global"
    config_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config_file))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in GIT_LOCATING:
        monkeypatch.delenv(name, raising=False)
    for name, value in GIT_IDENTITY.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv(
        "PATH", os.pathsep.join([str(stub.directory), os.path.dirname(GIT)])
    )


def git(root, *args):
    subprocess.run(
        [GIT, "-C", str(root), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )


@pytest.fixture
def checkout(tmp_path, isolated_git):
    root = tmp_path / "data-checkout"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / ".gitignore").write_bytes(b"blobs/sha256/\n*.tmp\n")
    git(root, "add", ".gitignore")
    git(root, "commit", "-q", "-m", "start")
    return root


def committed(root):
    stated(root, at=0)
    (root / "runs" / RUN / "events.ndjson").write_bytes(b'{"line": 1}\n')
    key_records.store_hw_profile(root, HW_PROFILE)
    key_records.store_op_signature(root, keys.hw_profile_key(HW_PROFILE).name, OP)
    git(root, "add", "-f", "--", "runs", "db")
    git(root, "commit", "-q", "-m", "by hand")
    assert run_commit.commit_owed(root, RUN) is False
    return root


def owing_a_new_file(root):
    committed(root)
    spec = root / "runs" / RUN / "rounds" / "0000" / "spec.json"
    spec.parent.mkdir(parents=True)
    spec.write_bytes(b"{}\n")
    assert run_commit.commit_owed(root, RUN) is True


def owing_a_changed_file(root):
    committed(root)
    (root / "runs" / RUN / "events.ndjson").write_bytes(b'{"line": 1}\n{"line": 2}\n')
    assert run_commit.commit_owed(root, RUN) is True


def stop_input(active=False):
    return {
        "session_id": "session",
        "transcript_path": "transcript.jsonl",
        "cwd": ".",
        "permission_mode": "dontAsk",
        "hook_event_name": "Stop",
        "stop_hook_active": active,
        "last_assistant_message": "done",
    }


def stops_run(stub, root, parent, *inputs, run_id=RUN):
    stub.install(stop_inputs=inputs)
    go(root, parent, run_id=run_id)
    (call,) = stub.calls()
    return call["stops"]


def let_through(ran):
    assert [(hook["entry"], hook["status"]) for hook in ran] == [
        (0, stop_check.EXIT_PASS)
    ]
    assert (ran[0]["stdout"], ran[0]["stderr"]) == ("", "")


@pytest.mark.parametrize("owing", [owing_a_new_file, owing_a_changed_file])
def test_stop_hook_refuses_a_first_stop_owing_a_commit(stub, checkout, parent, owing):
    owing(checkout)
    first, continued = stops_run(
        stub, checkout, parent, stop_input(False), stop_input(True)
    )
    (hook,) = first
    assert (hook["entry"], hook["status"]) == (0, stop_check.EXIT_REFUSE)
    assert hook["stdout"] == ""
    assert hook["stderr"].replace("\r\n", "\n") == stop_check.REFUSAL + "\n"
    let_through(continued)


def test_stop_hook_lets_a_committed_run_through(stub, checkout, parent):
    committed(checkout)
    (ran,) = stops_run(stub, checkout, parent, stop_input(False))
    let_through(ran)


def test_stop_hook_lets_a_plain_directory_through(stub, tmp_path, parent, isolated_git):
    plain = tmp_path / "plain-data"
    plain.mkdir()
    stated(plain, at=0)
    (ran,) = stops_run(stub, plain, parent, stop_input(False))
    let_through(ran)


def test_stop_hook_asks_of_the_loop_run_only(stub, checkout, parent):
    owing_a_new_file(checkout)
    (ran,) = stops_run(stub, checkout, parent, stop_input(False), run_id="run-other")
    let_through(ran)
