import inspect
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from hilclaw import further_turn, keys, run_commit, turn_loop
from hilclaw.further_turn import (
    COMMIT_NOT_MADE,
    COMMIT_REFUSED,
    DUE,
    FRESH,
    INSTANCE_INVALID,
    INSTANCE_MISSING,
    INSTANCE_VERSION,
    NO_REPOSITORY,
    NO_ROUND_BUDGET,
    OPEN,
    OVER_CASE,
    OWED,
    STATE_INVALID,
    STATE_MISSING,
    STATE_VERSION,
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
REASONS = [
    STATE_MISSING,
    STATE_INVALID,
    STATE_VERSION,
    INSTANCE_MISSING,
    INSTANCE_INVALID,
    INSTANCE_VERSION,
    NO_ROUND_BUDGET,
    NO_REPOSITORY,
    COMMIT_REFUSED,
    COMMIT_NOT_MADE,
]
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
UNKNOWN_VALUES = ["stopped", "Over", "", None, 1, True, {}, []]


def instance_bytes(**members):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        **members,
    }
    return json.dumps(document, indent=2).encode() + b"\n"


@pytest.fixture(autouse=True)
def isolated_git(monkeypatch, tmp_path_factory):
    config = tmp_path_factory.mktemp("git-config") / "global"
    config.write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in LOCATING:
        monkeypatch.delenv(name, raising=False)
    for name, value in IDENTITY.items():
        monkeypatch.setenv(name, value)


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def git(root, *args):
    subprocess.run(
        ["git", "-C", str(root), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
    )


def repository(root):
    if not (root / ".git").exists():
        git(root, "init", "-q", "-b", "main")
    return root


def settle(root):
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "by hand")


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
    repository(root)
    stated(root, 5, {"run_status": "over"})
    settle(root)
    return run_dir(root)


def owed(root):
    repository(root)
    stated(root, 4)
    settle(root)
    replace(root, RUN, 5, EMPTY, {"run_status": "over"})
    return run_dir(root)


def owed_without_head(root):
    repository(root)
    return stated(root, 1, {"run_status": "over"})


def over_uncommitted(root):
    repository(root)
    stated(root, 5)
    settle(root)
    replace(root, RUN, 5, EMPTY, {"run_status": "over"})
    return run_dir(root)


def over_with_tmp(root):
    over(root)
    (run_dir(root) / "STATE.json.tmp").write_bytes(b"{")
    return run_dir(root)


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
        "COMMIT_NOT_MADE",
        "COMMIT_REFUSED",
        "DUE",
        "FRESH",
        "Finding",
        "INSTANCE_INVALID",
        "INSTANCE_MISSING",
        "INSTANCE_VERSION",
        "NO_REPOSITORY",
        "NO_ROUND_BUDGET",
        "OPEN",
        "OVER",
        "OVER_CASE",
        "OWED",
        "RUN_STATUS",
        "STATE_INVALID",
        "STATE_MISSING",
        "STATE_VERSION",
        "UNKNOWN_STATUS",
        "classify",
        "predicate",
    ]
    assert further_turn.RUN_STATUS == "run_status"
    assert further_turn.OVER == "over"
    assert len({FRESH, OVER_CASE, UNKNOWN_STATUS, DUE, OWED, OPEN}) == 6
    assert len(set(REASONS)) == 10
    assert NO_REPOSITORY == run_commit.KIND_NO_REPOSITORY == "no_repository"
    assert COMMIT_REFUSED == run_commit.KIND_COMMIT_REFUSED == "commit_refused"
    assert COMMIT_NOT_MADE == run_commit.KIND_COMMIT_NOT_MADE == "commit_not_made"
    assert all(type(reason) is str for reason in REASONS)
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
    assert classify(root, RUN) == Finding(DUE, round)
    further, fallback, report = make(root)
    assert further(previous) is True
    assert fallback.seen == [] and report.seen == []


def test_p4_ignores_other_members(root):
    stated(root, 2, {"example_member": "over"})
    assert classify(root, RUN) == Finding(DUE, 2)


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
    (open_missing_state, STATE_MISSING),
    (open_bad_json, STATE_INVALID),
    (open_directory_state, STATE_INVALID),
    (open_state_version_2, STATE_VERSION),
    (open_missing_instance, INSTANCE_MISSING),
    (open_invalid_instance, INSTANCE_INVALID),
    (open_instance_directory, INSTANCE_INVALID),
    (open_instance_version_2, INSTANCE_VERSION),
    (open_no_budget, NO_ROUND_BUDGET),
]


@pytest.mark.parametrize("answer", [True, False])
@pytest.mark.parametrize(("arrange", "reason"), OPEN_STATES)
def test_open_asks_the_fallback(root, arrange, reason, answer):
    arrange(root)
    assert classify(root, RUN) == Finding(OPEN, reason)
    further, fallback, report = make(root, fallback=Recorder(answer))
    assert further(None) is answer
    assert further(0) is answer
    assert fallback.seen == [None, 0]
    assert report.seen == []


def test_a_run_without_any_file_is_open(root):
    assert classify(root, RUN) == Finding(OPEN, STATE_MISSING)


@pytest.mark.parametrize("answer", [True, False])
@pytest.mark.parametrize("previous", [1, -9, 2])
@pytest.mark.parametrize("arrange", [started, stated, owed])
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
    repository(root)
    started(root)
    assert further(None) is True
    replace(root, RUN, 1, EMPTY)
    assert further(0) is True
    replace(root, RUN, 5, EMPTY, {"run_status": "over"})
    assert further(0) is True
    settle(root)
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
    monkeypatch.setattr(run_commit, "commit_owed", refuse)
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
    real = subprocess.run

    def git_only(command, **options):
        assert command[0] == run_commit.GIT
        return real(command, **options)

    monkeypatch.setattr(shutil, "which", refuse)
    monkeypatch.setattr(subprocess, "run", git_only)
    further, fallback, report = make(root)
    made = []
    turns = turn_loop.run(
        further_turn=further,
        put_definition=made.append,
        prompt="go",
        data_root=root,
        run_id="run-a",
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
        owed,
        owed_without_head,
        over_uncommitted,
        over_with_tmp,
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


# --- P2 and the owed rule (ADR-0127 decision 6, ADR-0143 decision 6) ---


def counted(monkeypatch):
    calls = []
    real = run_commit.commit_owed

    def commit_owed(data_root, run_id):
        calls.append((data_root, run_id))
        return real(data_root, run_id)

    monkeypatch.setattr(run_commit, "commit_owed", commit_owed)
    monkeypatch.setattr(run_commit, "owed_rounds", refuse)
    return calls


@pytest.mark.parametrize(
    ("arrange", "case"),
    [(over, OVER_CASE), (owed, OWED), (over_uncommitted, OWED)],
)
def test_p2_asks_the_rule_once(root, monkeypatch, arrange, case):
    arrange(root)
    calls = counted(monkeypatch)
    assert classify(root, RUN) == Finding(case, None)
    assert calls == [(root, RUN)]


def test_p2_at_round_zero_without_head_is_owed(root):
    repository(root)
    stated(root, 0, {"run_status": "over"})
    assert classify(root, RUN) == Finding(OWED, None)


def test_p2_committed_with_nothing_changed_owes_nothing(root):
    over(root)
    assert classify(root, RUN) == Finding(OVER_CASE, None)


@pytest.mark.parametrize("previous", [None, 0])
def test_over_written_without_a_round_end_and_not_committed_is_owed(root, previous):
    over_uncommitted(root)
    assert classify(root, RUN) == Finding(OWED, None)
    further, fallback, report = make(root)
    assert further(previous) is True
    assert fallback.seen == [] and report.seen == []


@pytest.mark.parametrize("held", [b"", b'{"line": 1}\n'])
def test_a_torn_tail_alone_owes_nothing(root, held):
    over(root)
    events = run_dir(root) / "events.ndjson"
    if held:
        events.write_bytes(held)
        settle(root)
    events.write_bytes(held + b'{"torn')
    assert classify(root, RUN) == Finding(OVER_CASE, None)


def test_key_record_files_alone_owe_nothing(root):
    over(root)
    directory = root / "db" / keys.hw_profile_key(PROFILE).name
    signature = directory / keys.op_signature_key(OP).name
    signature.mkdir(parents=True)
    (directory / "hw_profile.json").write_bytes(b"{}\n")
    (signature / "op_signature.json").write_bytes(b"{}\n")
    assert classify(root, RUN) == Finding(OVER_CASE, None)


def test_a_changed_tracked_file_alone_is_owed(root):
    over(root)
    (run_dir(root) / "notes.txt").write_bytes(b"a\n")
    settle(root)
    (run_dir(root) / "notes.txt").write_bytes(b"b\n")
    assert classify(root, RUN) == Finding(OWED, None)


def test_a_new_untracked_file_alone_is_owed(root):
    over(root)
    (run_dir(root) / "notes.txt").write_bytes(b"a\n")
    assert classify(root, RUN) == Finding(OWED, None)


def test_a_tmp_file_alone_owes_nothing(root):
    over_with_tmp(root)
    assert classify(root, RUN) == Finding(OVER_CASE, None)


@pytest.mark.parametrize("arrange", [owed, owed_without_head, over_uncommitted])
@pytest.mark.parametrize("previous", [None, 0])
def test_owed_p2_is_a_further_turn(root, arrange, previous):
    arrange(root)
    assert classify(root, RUN) == Finding(OWED, None)
    further, fallback, report = make(root)
    assert further(previous) is True
    assert fallback.seen == [] and report.seen == []


def test_owed_p2_compares_equal_before_and_after(root):
    owed(root)
    first = classify(root, RUN)
    replace(root, RUN, 6, EMPTY, {"run_status": "over"})
    assert classify(root, RUN) == first


@pytest.mark.parametrize("previous", [1, -1, False, 0.0, "0"])
def test_owed_p2_after_a_failed_turn_asks_the_fallback(root, previous):
    owed(root)
    further, fallback, report = make(root, fallback=Recorder(False))
    assert further(previous) is False
    assert fallback.seen == [previous] and report.seen == []


def no_repository(root):
    stated(root, 5, {"run_status": "over"})


def round_behind(root):
    repository(root)
    stated(root, 5, {"run_status": "over"})
    settle(root)
    replace(root, RUN, 4, EMPTY, {"run_status": "over"})


def invalid_in_head(root):
    repository(root)
    started(root)
    (run_dir(root) / "STATE.json").write_bytes(b"{")
    settle(root)
    replace(root, RUN, 5, EMPTY, {"run_status": "over"})


def tracked_file_missing(root):
    over(root)
    (run_dir(root) / "notes.txt").write_bytes(b"a\n")
    settle(root)
    (run_dir(root) / "notes.txt").unlink()


def owed_without_key_directory(root):
    owed(root)
    document = json.loads((run_dir(root) / "instance.json").read_bytes())
    del document["op_signature"]
    (run_dir(root) / "instance.json").write_bytes(json.dumps(document).encode())


P2_OPEN = [
    (no_repository, NO_REPOSITORY),
    (round_behind, COMMIT_REFUSED),
    (invalid_in_head, COMMIT_REFUSED),
    (owed_without_key_directory, COMMIT_REFUSED),
    (tracked_file_missing, COMMIT_REFUSED),
]


@pytest.mark.parametrize("answer", [True, False])
@pytest.mark.parametrize(("arrange", "reason"), P2_OPEN)
def test_p2_where_the_rule_cannot_be_applied_is_open(root, arrange, reason, answer):
    arrange(root)
    assert classify(root, RUN) == Finding(OPEN, reason)
    further, fallback, report = make(root, fallback=Recorder(answer))
    assert further(None) is answer
    assert further(0) is answer
    assert fallback.seen == [None, 0] and report.seen == []


def test_a_subdirectory_of_a_working_tree_is_no_repository(tmp_path):
    outer = tmp_path / "outer"
    outer.mkdir()
    repository(outer)
    data = outer / "data"
    data.mkdir()
    stated(data, 5, {"run_status": "over"})
    assert classify(data, RUN) == Finding(OPEN, NO_REPOSITORY)


def test_git_that_cannot_be_started_is_no_repository(root, monkeypatch, tmp_path):
    over(root)
    monkeypatch.setattr(run_commit, "GIT", str(tmp_path / "no-such-git"))
    assert classify(root, RUN) == Finding(OPEN, NO_REPOSITORY)


@pytest.mark.parametrize(
    "error",
    [
        run_commit.FileMissingError("x"),
        run_commit.StateMissingError("x"),
        run_commit.NoKeyDirectoryError("x"),
        run_commit.EventsNotRegularError("x"),
    ],
)
def test_every_refusal_is_commit_refused(root, monkeypatch, error):
    no_repository(root)

    def refused(data_root, run_id):
        raise error

    monkeypatch.setattr(run_commit, "commit_owed", refused)
    assert classify(root, RUN) == Finding(OPEN, COMMIT_REFUSED)


@pytest.mark.parametrize("answer", [True, False])
def test_a_commit_not_made_is_open(root, monkeypatch, answer):
    over_uncommitted(root)

    def failing(data_root, run_id):
        raise run_commit.CommitNotMadeError("x")

    monkeypatch.setattr(run_commit, "commit_owed", failing)
    assert classify(root, RUN) == Finding(OPEN, COMMIT_NOT_MADE)
    further, fallback, report = make(root, fallback=Recorder(answer))
    assert further(None) is answer
    assert fallback.seen == [None] and report.seen == []


@pytest.mark.parametrize("error", [PermissionError("x"), ValueError()])
def test_another_exception_of_the_rule_passes_through(root, monkeypatch, error):
    no_repository(root)

    def failing(data_root, run_id):
        raise error

    monkeypatch.setattr(run_commit, "commit_owed", failing)
    with pytest.raises(type(error)) as raised:
        classify(root, RUN)
    assert raised.value is error
    further, fallback, _ = make(root)
    with pytest.raises(type(error)):
        further(None)
    assert fallback.seen == []


@pytest.mark.parametrize(
    ("arrange", "finding"),
    [
        (started, Finding(FRESH, None)),
        (stated, Finding(DUE, 0)),
        (
            lambda root: stated(root, 2, {"run_status": "stopped"}),
            Finding(UNKNOWN_STATUS, "stopped"),
        ),
        (open_no_budget, Finding(OPEN, NO_ROUND_BUDGET)),
        (open_bad_json, Finding(OPEN, STATE_INVALID)),
    ],
)
def test_other_states_need_no_git(root, monkeypatch, arrange, finding):
    arrange(root)
    monkeypatch.setattr(run_commit, "commit_owed", refuse)
    monkeypatch.setattr(run_commit, "GIT", "no-such-git")
    assert classify(root, RUN) == finding
    assert not (root / ".git").exists()


def test_a_missing_data_root_raises_before_the_rule(tmp_path, monkeypatch):
    monkeypatch.setattr(run_commit, "commit_owed", refuse)
    with pytest.raises(FileNotFoundError):
        classify(tmp_path / "absent", RUN)
