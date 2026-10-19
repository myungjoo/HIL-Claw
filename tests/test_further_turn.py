import inspect
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from hilclaw import further_turn, keys, turn_loop
from hilclaw.further_turn import (
    DUE,
    FRESH,
    OPEN,
    OVER_CASE,
    UNKNOWN_STATUS,
    Finding,
    classify,
    predicate,
)
from hilclaw.instance_file import write
from hilclaw.journal import EMPTY
from hilclaw.layout import InvalidPathValueError
from hilclaw.run_state_file import replace

RUN = "run-a"
PROFILE = {
    "schema_version": 1,
    "accelerator": "acc_a",
    "revision": "rev 1",
    "toolchain": {"cc": "1.0"},
    "host": {"cpu": "cpu x", "os": "os y"},
    "hw_source": "external",
}
UNKNOWN_VALUES = ["stopped", "Over", "", None, 1, True, {}, []]


def instance_bytes(**members):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        **members,
    }
    return json.dumps(document, indent=2).encode() + b"\n"


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def run_dir(root):
    return root / "runs" / RUN


def started(root, budget=5):
    members = {} if budget is None else {"round_budget": budget}
    write(root, RUN, instance_bytes(**members))
    return run_dir(root)


def stated(root, round=0, others=None, budget=5):
    started(root, budget)
    replace(root, RUN, round, EMPTY, others)
    return run_dir(root)


def over(root):
    return stated(root, 5, {"run_status": "over"})


class Recorder:
    def __init__(self, answer=True):
        self.answer = answer
        self.seen = []

    def __call__(self, value):
        self.seen.append(value)
        return self.answer


def make(root, fallback=None, report=None):
    fallback = Recorder() if fallback is None else fallback
    report = Recorder() if report is None else report
    return predicate(root, RUN, fallback=fallback, report=report), fallback, report


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): (
            None if path.is_dir() else path.read_bytes()
        )
        for path in directory.rglob("*")
    }


def test_the_public_names():
    public = sorted(
        name
        for name, value in vars(further_turn).items()
        if not name.startswith("_")
        and not inspect.ismodule(value)
        and value is not further_turn.NamedTuple
    )
    assert public == [
        "DUE",
        "FRESH",
        "Finding",
        "OPEN",
        "OVER",
        "OVER_CASE",
        "RUN_STATUS",
        "UNKNOWN_STATUS",
        "classify",
        "predicate",
    ]
    assert further_turn.RUN_STATUS == "run_status"
    assert further_turn.OVER == "over"
    assert len({FRESH, OVER_CASE, UNKNOWN_STATUS, DUE, OPEN}) == 5
    assert list(inspect.signature(predicate).parameters) == [
        "data_root",
        "run_id",
        "fallback",
        "report",
    ]


# --- happy ---


def test_p1_a_fresh_directory_is_a_further_turn(root):
    started(root)
    assert classify(root, RUN) == Finding(FRESH, None)
    further, fallback, report = make(root)
    assert further(None) is True
    assert fallback.seen == [] and report.seen == []


def test_p1_with_a_string_data_root(root):
    started(root)
    assert classify(str(root), RUN) == Finding(FRESH, None)


@pytest.mark.parametrize("previous", [None, 0, 1])
def test_p2_over_is_no_further_turn(root, previous):
    over(root)
    assert classify(root, RUN) == Finding(OVER_CASE, None)
    further, fallback, report = make(root)
    assert further(previous) is False
    assert fallback.seen == [] and report.seen == []


@pytest.mark.parametrize("round", [0, 4, 5, 9])
@pytest.mark.parametrize("previous", [None, 0])
def test_p4_a_stated_budget_is_a_further_turn_whatever_round_is(root, round, previous):
    stated(root, round)
    assert classify(root, RUN) == Finding(DUE, None)
    further, fallback, report = make(root)
    assert further(previous) is True
    assert fallback.seen == [] and report.seen == []


def test_p4_ignores_other_members(root):
    stated(root, 2, {"example_member": "over"})
    assert classify(root, RUN) == Finding(DUE, None)


# --- branch ---


@pytest.mark.parametrize("value", UNKNOWN_VALUES)
def test_p3_another_value_is_reported_and_no_further_turn(root, value):
    stated(root, 1, {"run_status": value})
    finding = classify(root, RUN)
    assert finding.case == UNKNOWN_STATUS
    assert finding.value == value and type(finding.value) is type(value)
    further, fallback, report = make(root)
    assert further(0) is False
    assert report.seen == [value]
    assert fallback.seen == []


def test_p3_whatever_previous_is(root):
    stated(root, 1, {"run_status": "stopped"})
    further, fallback, report = make(root)
    assert further(None) is False
    assert further(3) is False
    assert report.seen == ["stopped", "stopped"]
    assert fallback.seen == []


def open_missing_state(root):
    (started(root) / "events.ndjson").write_bytes(b"")


def open_bad_json(root):
    (started(root) / "STATE.json").write_bytes(b"{")


def open_directory_state(root):
    (started(root) / "STATE.json").mkdir()


def open_state_version_2(root):
    (started(root) / "STATE.json").write_bytes(b'{"schema_version": 2}\n')


def open_missing_instance(root):
    stated(root)
    (run_dir(root) / "instance.json").unlink()


def open_invalid_instance(root):
    stated(root)
    (run_dir(root) / "instance.json").write_bytes(b"{")


def open_instance_directory(root):
    stated(root)
    (run_dir(root) / "instance.json").unlink()
    (run_dir(root) / "instance.json").mkdir()


def open_instance_version_2(root):
    stated(root)
    (run_dir(root) / "instance.json").write_bytes(b'{"schema_version": 2}\n')


def open_no_budget(root):
    stated(root, budget=None)


OPEN_STATES = [
    open_missing_state,
    open_bad_json,
    open_directory_state,
    open_state_version_2,
    open_missing_instance,
    open_invalid_instance,
    open_instance_directory,
    open_instance_version_2,
    open_no_budget,
]


@pytest.mark.parametrize("answer", [True, False])
@pytest.mark.parametrize("arrange", OPEN_STATES)
def test_open_asks_the_fallback(root, arrange, answer):
    arrange(root)
    assert classify(root, RUN) == Finding(OPEN, None)
    further, fallback, report = make(root, fallback=Recorder(answer))
    assert further(None) is answer
    assert further(0) is answer
    assert fallback.seen == [None, 0]
    assert report.seen == []


def test_a_run_without_any_file_is_open(root):
    assert classify(root, RUN) == Finding(OPEN, None)


@pytest.mark.parametrize("answer", [True, False])
@pytest.mark.parametrize("previous", [1, -9, 2])
@pytest.mark.parametrize("arrange", [started, stated])
def test_p1_and_p4_after_a_failed_turn_ask_the_fallback(
    root, arrange, previous, answer
):
    arrange(root)
    further, fallback, report = make(root, fallback=Recorder(answer))
    assert further(previous) is answer
    assert fallback.seen == [previous]
    assert report.seen == []


@pytest.mark.parametrize("previous", [False, 0.0])
def test_p1_a_previous_that_is_no_int_zero_asks_the_fallback(root, previous):
    started(root)
    further, fallback, _ = make(root)
    further(previous)
    assert fallback.seen == [previous]


def test_the_fallback_answer_is_returned_unchanged(root):
    started(root)
    answer = object()
    further, _, _ = make(root, fallback=lambda previous: answer)
    assert further(1) is answer


def test_nothing_is_kept_between_calls(root):
    further, fallback, report = make(root)
    started(root)
    assert further(None) is True
    replace(root, RUN, 1, EMPTY)
    assert further(0) is True
    replace(root, RUN, 5, EMPTY, {"run_status": "over"})
    assert further(0) is False
    replace(root, RUN, 5, EMPTY, {"run_status": "paused"})
    assert further(0) is False
    assert fallback.seen == []
    assert report.seen == ["paused"]


# --- negative and error ---


def refuse(*args, **kwargs):
    raise AssertionError("no file may be read")


@pytest.mark.parametrize("name", ["fallback", "report"])
@pytest.mark.parametrize("value", [None, 1, "f"])
def test_a_callback_that_is_not_callable(root, monkeypatch, name, value):
    monkeypatch.setattr(further_turn, "classify", refuse)
    monkeypatch.setattr(further_turn.fresh_run, "is_fresh", refuse)
    arguments = {"fallback": Recorder(), "report": Recorder(), name: value}
    with pytest.raises(TypeError, match=name):
        predicate(root, RUN, **arguments)


@pytest.mark.parametrize("run_id", ["", "Run-a", "..", 7, None, b"run-a"])
def test_an_invalid_run_id(root, monkeypatch, run_id):
    with pytest.raises(InvalidPathValueError):
        classify(root, run_id)
    monkeypatch.setattr(further_turn.fresh_run, "is_fresh", refuse)
    with pytest.raises(InvalidPathValueError):
        predicate(root, run_id, fallback=Recorder(), report=Recorder())


def test_a_permission_error_of_the_state_read_passes_through(root, monkeypatch):
    stated(root)
    error = PermissionError("denied")

    def denied(data_root, run_id):
        raise error

    monkeypatch.setattr(further_turn.run_journal, "read_state", denied)
    with pytest.raises(PermissionError) as raised:
        classify(root, RUN)
    assert raised.value is error
    further, fallback, report = make(root)
    with pytest.raises(PermissionError):
        further(None)
    assert fallback.seen == [] and report.seen == []


def test_a_permission_error_of_the_instance_read_passes_through(root, monkeypatch):
    stated(root)

    def denied(data_root, run_id):
        raise PermissionError("denied")

    monkeypatch.setattr(further_turn.instance, "read", denied)
    with pytest.raises(PermissionError):
        classify(root, RUN)


def test_a_missing_data_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        classify(tmp_path / "absent", RUN)
    further, fallback, _ = make(tmp_path / "absent")
    with pytest.raises(FileNotFoundError):
        further(None)
    assert fallback.seen == []


def test_a_file_as_data_root(tmp_path):
    file = tmp_path / "file"
    file.write_bytes(b"")
    with pytest.raises(NotADirectoryError):
        classify(file, RUN)


def test_an_exception_of_report_passes_through(root):
    stated(root, 1, {"run_status": "stopped"})

    def report(value):
        raise RuntimeError("report failed")

    further, _, _ = make(root, report=report)
    with pytest.raises(RuntimeError, match="report failed"):
        further(None)


def test_an_exception_of_fallback_passes_through(root):
    open_no_budget(root)

    def fallback(previous):
        raise RuntimeError("fallback failed")

    further, _, _ = make(root, fallback=fallback)
    with pytest.raises(RuntimeError, match="fallback failed"):
        further(None)


# --- with the loop ---


def markers_above(path):
    own = (Path.home() / ".claude").resolve()
    return any(
        os.path.lexists(directory / name) and (directory / name).resolve() != own
        for directory in Path(path).resolve().parents
        for name in turn_loop.MARKERS
    )


def test_the_loop_on_a_run_that_is_over_starts_nothing(root, tmp_path, monkeypatch):
    if markers_above(tmp_path):
        pytest.skip("a directory above the test's temporary directory holds a marker")
    over(root)
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    monkeypatch.setattr(shutil, "which", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    further, fallback, report = make(root)
    made = []
    turns = turn_loop.run(
        further_turn=further,
        put_definition=made.append,
        prompt="go",
        data_root=root,
        parent=sessions,
    )
    assert turns == ()
    assert made == []
    assert list(sessions.iterdir()) == []
    assert fallback.seen == [] and report.seen == []


# --- no side effect ---


@pytest.mark.parametrize(
    "arrange",
    [
        started,
        stated,
        over,
        open_no_budget,
        open_bad_json,
        lambda root: stated(root, 1, {"run_status": "stopped"}),
    ],
)
def test_nothing_in_the_run_changes(root, arrange):
    arrange(root)
    before = snapshot(root)
    classify(root, RUN)
    further, _, _ = make(root)
    further(None)
    further(1)
    assert snapshot(root) == before
