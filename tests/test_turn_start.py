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
    tools,
    turn_loop,
    turn_start,
)
from hilclaw.instance_file import write
from hilclaw.journal import EMPTY
from hilclaw.run_state import dump
from hilclaw.run_state_file import replace
from hilclaw.turn_start import (
    BAD_USAGE,
    ERROR,
    EXIT_ERROR,
    EXIT_FAILED_TURN,
    EXIT_OPEN_STATE,
    EXIT_RUN_OVER,
    EXIT_UNCHANGED_TURN,
    EXIT_UNKNOWN_RUN_STATUS,
    FAILED_TURN,
    FAULT,
    NO_CLAUDE,
    NO_DATA_ROOT,
    OPEN_STATE,
    PROMPT,
    RUN_OVER,
    UNCHANGED_TURN,
    UNKNOWN_RUN_STATUS,
    main,
)

RUN = "run-a"
REPOSITORY = Path(__file__).resolve().parent.parent
PROFILE = {
    "schema_version": 1,
    "accelerator": "acc_a",
    "revision": "rev 1",
    "toolchain": {"cc": "1.0"},
    "host": {"cpu": "cpu x", "os": "os y"},
    "hw_source": "external",
}
STATE = f"runs/{RUN}/STATE.json"
INSTANCE = f"runs/{RUN}/instance.json"

STUB = r"""
import json, os, sys
from pathlib import Path

here = Path(__file__).parent
scenario = json.loads((here / "scenario.json").read_text(encoding="utf-8"))
with (here / "started.ndjson").open("a", encoding="utf-8") as record:
    entry = {"argv": sys.argv[1:], "listing": sorted(os.listdir("."))}
    record.write(json.dumps(entry) + "\n")
started = len((here / "started.ndjson").read_text(encoding="utf-8").splitlines())
steps = scenario["steps"]
step = steps[min(started, len(steps)) - 1]
for name, text in step["writes"]:
    path = Path(scenario["root"], name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
sys.exit(step["status"])
"""


class Stub:
    def __init__(self, directory, root):
        self.directory = directory
        self.root = root
        self.steps = []

    def install(self, *steps):
        self.steps = [{"status": status, "writes": writes} for status, writes in steps]
        script = self.directory / "stub.py"
        script.write_text(STUB, encoding="utf-8")
        scenario = {"root": str(self.root), "steps": self.steps}
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


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
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
    }


class Started:
    def __init__(self, status, stdout, stderr):
        self.status = status
        self.lines = stdout.getvalue().splitlines()
        self.stderr = stderr.getvalue().decode("utf-8")

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
        "parent": parent,
        "stdout": stdout,
        "stderr": stderr,
        **changes,
    }
    status = main(list(args), **arguments)
    return Started(status, stdout, stderr)


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


def told_once(found, status, told):
    assert found.status == status
    assert found.told == told
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
        "EXIT_UNCHANGED_TURN",
        "EXIT_UNKNOWN_RUN_STATUS",
        "FAILED_TURN",
        "FAULT",
        "NO_CLAUDE",
        "NO_DATA_ROOT",
        "OPEN_STATE",
        "PROMPT",
        "RUN_OVER",
        "UNCHANGED_TURN",
        "UNKNOWN_RUN_STATUS",
        "main",
    ]
    statuses = [
        EXIT_RUN_OVER,
        EXIT_UNKNOWN_RUN_STATUS,
        EXIT_FAILED_TURN,
        EXIT_UNCHANGED_TURN,
        EXIT_OPEN_STATE,
        EXIT_ERROR,
    ]
    assert EXIT_RUN_OVER == 0
    assert len(set(statuses)) == 6
    assert not {1, 2} & set(statuses)
    kinds = {RUN_OVER, UNKNOWN_RUN_STATUS, FAILED_TURN, UNCHANGED_TURN, OPEN_STATE}
    assert len(kinds | {ERROR}) == 6
    assert turn_loop._PROMPT.fullmatch(PROMPT)
    assert RUN not in PROMPT
    assert turn_start.__doc__
    names = tools.default_registry(lambda: None).names()
    assert not [name for name in names if "turn" in name]


# --- happy ---


def test_a_fresh_run_goes_from_round_zero_to_over(root, go, stub):
    started(root)
    found = go(
        (0, [(STATE, state_text(1))]),
        (0, [(STATE, state_text(2))]),
        (0, [(STATE, state_text(3, {"run_status": "over"}))]),
    )
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    calls = stub.calls()
    assert len(calls) == 3
    for call in calls:
        assert call["argv"][:2] == [turn_loop.OPT_PRINT, PROMPT]
        assert "CLAUDE.md" in call["listing"]


def test_over_at_once_starts_no_turn(root, go, stub):
    stated(root, 5, {"run_status": "over"})
    found = go((0, []))
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
    assert stub.calls() == []


def test_a_str_data_root(root, parent, stub):
    stated(root, 5, {"run_status": "over"})
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


def test_over_written_by_a_failed_turn_is_run_over(root, go, stub):
    started(root)
    found = go((5, [(STATE, state_text(1, {"run_status": "over"}))]))
    told_once(found, EXIT_RUN_OVER, {"outcome": RUN_OVER})
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
    stated(root, 5, {"run_status": "over"})
    repo = config.DataRepo("url", root)
    monkeypatch.setattr(config, "load_data_repo", lambda: repo)
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = main([RUN], parent=parent, stdout=stdout, stderr=stderr)
    assert status == EXIT_RUN_OVER
    assert inspect.signature(main).parameters["source"].default is (
        data_root_source.configured
    )


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
    stated(root, 5, {"run_status": "over"})
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
    status = main([RUN], source=lambda: root, parent=parent, stderr=stderr)
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


def test_one_line_on_standard_error(root, go, stub):
    found = go(source=lambda: "a\nb\rc")
    assert found.stderr.count("\n") == 1


def test_the_default_arguments(root, stub, monkeypatch, tmp_path):
    stated(root, 5, {"run_status": "over"})
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
    status = main(source=lambda: root, stdout=io.BytesIO(), stderr=io.BytesIO())
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
