import io
import json
import os
import subprocess
import sys

import pytest

from hilclaw import (
    caller_check,
    checkout_boundary,
    config,
    key_records,
    keys,
    layout,
    mcp_front,
    run_commit,
    run_state,
    stop_check,
    tools,
)
from hilclaw.stop_check import (
    COMMIT_TOOL,
    EVENT,
    EXIT_PASS,
    EXIT_REFUSE,
    REFUSAL,
    START,
    main,
)

RUN = "zq-distinct-run-7"
EMPTY = run_state.from_stored({"totals": {}, "position": 0, "open_steps": []})
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
HW = {
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
HW_KEY = keys.hw_profile_key(HW).name
MISSING_FILE_WORDINGS = (
    "no such file",
    "no such directory",
    "not found",
    "missing",
    "does not exist",
    "doesn't exist",
    "cannot find",
    "can't find",
    "enoent",
)


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


def git(root, *args, env=None):
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        env=env,
    )
    return done.stdout


def head(root):
    done = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"],
        stdin=subprocess.DEVNULL,
        check=False,
        capture_output=True,
    )
    return done.stdout.strip().decode() if done.returncode == 0 else None


def new_repository(root):
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / ".gitignore").write_bytes(b"blobs/sha256/\n*.tmp\n")
    return root


@pytest.fixture
def root(tmp_path):
    data = new_repository(tmp_path / "distinct-data-root-xq9")
    git(data, "add", ".gitignore")
    git(data, "commit", "-q", "-m", "start")
    return data


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def write_instance(root, run_id=RUN):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": HW_KEY, "record": HW},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
    }
    return write(root, f"runs/{run_id}/instance.json", json.dumps(document).encode())


def write_state(root, round, run_id=RUN, others=None):
    return write(
        root, f"runs/{run_id}/STATE.json", run_state.dump(round, EMPTY, others)
    )


def write_events(root, content, run_id=RUN):
    return write(root, f"runs/{run_id}/events.ndjson", content)


def a_run(root, round=0, run_id=RUN):
    write_instance(root, run_id)
    write_state(root, round, run_id)
    write_events(root, b'{"line": 1}\n', run_id)
    return root


def store_keys(root):
    key_records.store_hw_profile(root, HW)
    key_records.store_op_signature(root, HW_KEY, OP)


def commit_by_hand(root, *paths):
    git(root, "add", "-f", "--", *paths)
    git(root, "commit", "-q", "-m", "by hand")


def committed_run(root, round=0):
    a_run(root, round)
    store_keys(root)
    commit_by_hand(root, "runs", "db")
    assert run_commit.commit_owed(root, RUN) is False
    return root


def owed_run(root):
    committed_run(root)
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    assert run_commit.commit_owed(root, RUN) is True
    return root


def payload(**fields):
    document = {
        "session_id": "session-1",
        "transcript_path": "/somewhere/transcript.jsonl",
        "cwd": "/somewhere",
        "permission_mode": "dontAsk",
        "hook_event_name": "Stop",
        "stop_hook_active": False,
        "last_assistant_message": "done",
    }
    for name, value in fields.items():
        if value is ABSENT:
            document.pop(name, None)
        else:
            document[name] = value
    return json.dumps(document).encode()


ABSENT = object()


class Counted:
    def __init__(self, monkeypatch):
        self.calls = []
        self.real = run_commit.commit_owed
        monkeypatch.setattr(run_commit, "commit_owed", self)

    def __call__(self, data_root, run_id):
        self.calls.append((data_root, run_id))
        return self.real(data_root, run_id)


def decided(data, args, capsys=None):
    stream = io.StringIO()
    status = main(data, stream, args)
    if capsys is not None:
        out, err = capsys.readouterr()
        assert (out, err) == ("", "")
    return status, stream.getvalue()


def passes(data, args, capsys=None):
    assert decided(data, args, capsys) == (EXIT_PASS, "")


def refuses(data, args, capsys=None):
    assert decided(data, args, capsys) == (EXIT_REFUSE, REFUSAL + "\n")


def snapshot(root):
    index = (root / ".git" / "index").read_bytes()
    quiet = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    status = git(root, "status", "--porcelain=v1", "-z", "--ignored", env=quiet)
    return head(root), index, status


def test_constants():
    assert (EXIT_PASS, EXIT_REFUSE, EVENT) == (0, 2, "Stop")
    assert "from hilclaw.stop_check import main" in START
    assert "sys.argv.pop(1)" in START
    assert "main(args=sys.argv[1:])" in START


def test_commit_tool_is_the_mcp_name_of_run_commit():
    registered = tools.default_registry(lambda: ".").names()
    assert "run.commit" in registered
    assert COMMIT_TOOL == caller_check.TOOL_PREFIX + mcp_front.mcp_name("run.commit")
    assert COMMIT_TOOL == "mcp__hilclaw__run_commit"


def test_the_line_is_one_line_and_says_what_decision_5_asks():
    assert "\n" not in REFUSAL and "\r" not in REFUSAL
    assert REFUSAL.count(COMMIT_TOOL) == 2
    assert "owed" in REFUSAL
    assert "once" in REFUSAL
    assert '"The end of a session"' in REFUSAL
    assert "no valid run id" in REFUSAL
    assert "failed in this turn" in REFUSAL
    assert "end at once without calling it" in REFUSAL


def test_the_line_reads_as_no_missing_file_message():
    lowered = REFUSAL.lower()
    for wording in MISSING_FILE_WORDINGS:
        assert wording not in lowered


def test_the_line_shows_no_run_id_or_data_root(root, capsys):
    owed_run(root)
    status, line = decided(payload(), [RUN, str(root)], capsys)
    assert status == EXIT_REFUSE
    assert line == REFUSAL + "\n"
    for shown in (RUN, str(root), root.name, "distinct", "zq-"):
        assert shown not in line


def test_a_round_end_owed_is_refused(root, capsys):
    a_run(root, 1)
    store_keys(root)
    assert run_commit.owed_rounds(root, RUN) == range(1)
    refuses(payload(), [RUN, str(root)], capsys)


def test_a_changed_run_file_inside_a_round_is_refused(root, capsys):
    committed_run(root, 2)
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    assert run_commit.owed_rounds(root, RUN) == range(2, 2)
    refuses(payload(), [RUN, str(root)], capsys)


def test_an_untracked_new_run_file_is_refused(root, capsys):
    committed_run(root)
    write(root, f"runs/{RUN}/rounds/0000/spec.json", b"{}\n")
    refuses(payload(), [RUN, str(root)], capsys)


def test_a_stale_index_lock_is_refused_and_left_alone(root, capsys):
    owed_run(root)
    lock = root / ".git" / "index.lock"
    lock.write_bytes(b"")
    with pytest.raises(run_commit.CommitNotMadeError):
        run_commit.commit(root, RUN)
    refuses(payload(), [RUN, str(root)], capsys)
    assert lock.read_bytes() == b""


def test_an_owed_run_at_a_continued_stop_passes(root, capsys):
    owed_run(root)
    passes(payload(stop_hook_active=True), [RUN, str(root)], capsys)


@pytest.mark.parametrize(
    "value", [True, None, ABSENT, 0, 0.0, -0.0, "false", "", [], {}, [False]]
)
def test_stop_hook_active_other_than_false_passes_without_asking(
    root, monkeypatch, value
):
    owed_run(root)
    counted = Counted(monkeypatch)
    passes(payload(stop_hook_active=value), [RUN, str(root)])
    assert counted.calls == []


def test_zero_and_zero_point_zero_are_not_false(root, monkeypatch):
    owed_run(root)
    counted = Counted(monkeypatch)
    passes(b'{"hook_event_name": "Stop", "stop_hook_active": 0}', [RUN, str(root)])
    passes(b'{"hook_event_name": "Stop", "stop_hook_active": 0.0}', [RUN, str(root)])
    refuses(b'{"hook_event_name": "Stop", "stop_hook_active": false}', [RUN, str(root)])
    assert len(counted.calls) == 1


@pytest.mark.parametrize(
    "event",
    ["SubagentStop", "PreToolUse", "StopFailure", "stop", "Stop ", "", None, 1, ABSENT],
)
def test_an_event_other_than_stop_passes_without_asking(root, monkeypatch, event):
    owed_run(root)
    counted = Counted(monkeypatch)
    passes(payload(hook_event_name=event), [RUN, str(root)])
    assert counted.calls == []


@pytest.mark.parametrize(
    "data",
    [
        b"",
        b"not json",
        b"\xff\xfe{}",
        b'{"hook_event_name": "Stop", "stop_hook_active": false',
        b'{"hook_event_name": "Stop", "stop_hook_active": false, "stop_hook_active": false}',
        b'{"hook_event_name": "Stop", "stop_hook_active": false, "x": {"a": 1, "a": 2}}',
        b'{"hook_event_name": "Stop", "stop_hook_active": false, "x": NaN}',
        b'{"hook_event_name": "Stop", "stop_hook_active": false, "x": [Infinity]}',
        b'{"hook_event_name": "Stop", "stop_hook_active": false, "x": -Infinity}',
        b'\xef\xbb\xbf{"hook_event_name": "Stop", "stop_hook_active": false}',
        b"[]",
        b'["Stop", false]',
        b'"Stop"',
        b"null",
        b"1",
        b"[" * 100000,
    ],
    ids=lambda data: f"{len(data)}:{data[:24]!r}",
)
def test_input_that_is_not_one_strict_json_object_passes(root, monkeypatch, data):
    owed_run(root)
    counted = Counted(monkeypatch)
    passes(data, [RUN, str(root)])
    assert counted.calls == []


def test_the_strict_control_input_is_refused(root):
    owed_run(root)
    refuses(b'{"hook_event_name": "Stop", "stop_hook_active": false}', [RUN, str(root)])


@pytest.mark.parametrize(
    "args",
    [
        [],
        [RUN],
        ["DATA"],
        [RUN, "DATA", "extra"],
        ["DATA", RUN],
    ],
)
def test_an_argument_list_other_than_two_passes(root, monkeypatch, args):
    owed_run(root)
    counted = Counted(monkeypatch)
    passes(payload(), [str(root) if a == "DATA" else a for a in args])
    assert counted.calls == []


@pytest.mark.parametrize(
    "run_id", ["", "Run-A", "-run", "run.a", "../run", "a" * 65, None, 1, b"run-a"]
)
def test_a_run_id_check_run_id_refuses_passes(root, monkeypatch, run_id):
    owed_run(root)
    with pytest.raises(layout.InvalidPathValueError):
        layout.check_run_id(run_id)
    counted = Counted(monkeypatch)
    passes(payload(), [run_id, str(root)])
    assert counted.calls == []


def test_a_data_root_that_names_no_directory_passes(root, monkeypatch, tmp_path):
    owed_run(root)
    counted = Counted(monkeypatch)
    plain = write(tmp_path, "plain-file", b"x")
    for data_root in (
        str(tmp_path / "nowhere"),
        str(plain),
        "",
        None,
        1,
        os.fsencode(root),
        root,
    ):
        passes(payload(), [RUN, data_root])
    assert counted.calls == []


def test_a_relative_data_root_is_used_as_given(root, monkeypatch):
    owed_run(root)
    monkeypatch.chdir(root.parent)
    refuses(payload(), [RUN, root.name])
    passes(payload(), [RUN, "nowhere"])


def test_a_plain_directory_is_no_repository_and_passes(tmp_path):
    plain = tmp_path / "plain"
    a_run(plain)
    with pytest.raises(run_commit.NoRepositoryError):
        run_commit.commit_owed(plain, RUN)
    passes(payload(), [RUN, str(plain)])


def test_an_invalid_working_state_passes(root):
    committed_run(root)
    write(root, f"runs/{RUN}/STATE.json", b"{not a state")
    with pytest.raises(run_commit.WorkingStateError):
        run_commit.commit_owed(root, RUN)
    passes(payload(), [RUN, str(root)])


def test_a_tracked_run_file_missing_is_commit_refused_and_passes(root):
    committed_run(root)
    write(root, f"runs/{RUN}/rounds/0000/spec.json", b"{}\n")
    commit_by_hand(root, "runs")
    (root / "runs" / RUN / "rounds" / "0000" / "spec.json").unlink()
    with pytest.raises(run_commit.FileMissingError):
        run_commit.commit_owed(root, RUN)
    passes(payload(), [RUN, str(root)])


def test_git_that_cannot_be_started_passes(root, monkeypatch):
    owed_run(root)
    monkeypatch.setattr(run_commit, "GIT", "hilclaw-no-such-git-program-q7")
    with pytest.raises(run_commit.GitNotRunError):
        run_commit.commit_owed(root, RUN)
    passes(payload(), [RUN, str(root)])


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("boom"),
        OSError("disk"),
        ValueError("bad"),
        layout.InvalidPathValueError("run_id"),
        run_commit.CommitNotMadeError("not made"),
        run_commit.HeadStateError("head"),
        RecursionError("deep"),
    ],
)
def test_any_exception_of_commit_owed_passes(root, monkeypatch, capsys, error):
    owed_run(root)

    def raising(data_root, run_id):
        raise error

    monkeypatch.setattr(run_commit, "commit_owed", raising)
    passes(payload(), [RUN, str(root)], capsys)


@pytest.mark.parametrize("answer", [1, "yes", [True], None])
def test_an_answer_other_than_true_passes(root, monkeypatch, answer):
    owed_run(root)
    monkeypatch.setattr(run_commit, "commit_owed", lambda data_root, run_id: answer)
    passes(payload(), [RUN, str(root)])


def test_a_committed_run_passes(root, capsys):
    committed_run(root)
    passes(payload(), [RUN, str(root)], capsys)


def test_a_repository_without_the_run_passes(root):
    assert run_commit.commit_owed(root, RUN) is False
    passes(payload(), [RUN, str(root)])


@pytest.mark.parametrize(
    "fields",
    [
        {"transcript_path": ABSENT, "last_assistant_message": ABSENT},
        {"transcript_path": None, "last_assistant_message": None},
        {"transcript_path": 7, "last_assistant_message": ["x"]},
        {"transcript_path": {"a": 1}, "last_assistant_message": False},
        {"session_id": ABSENT, "cwd": ABSENT, "permission_mode": ABSENT},
        {"background_tasks": "x", "session_crons": 1},
    ],
)
def test_other_input_fields_change_nothing(root, fields):
    owed_run(root)
    refuses(payload(**fields), [RUN, str(root)])
    commit_by_hand(root, "runs")
    passes(payload(**fields), [RUN, str(root)])


def test_commit_owed_is_asked_once_with_the_arguments(root, monkeypatch):
    owed_run(root)
    counted = Counted(monkeypatch)
    refuses(payload(), [RUN, str(root)])
    assert counted.calls == [(str(root), RUN)]
    commit_by_hand(root, "runs")
    passes(payload(), [RUN, str(root)])
    assert counted.calls == [(str(root), RUN)] * 2


def test_nothing_is_read_from_the_environment(root, monkeypatch, tmp_path):
    owed_run(root)
    other = new_repository(tmp_path / "other")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other))
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(other))
    monkeypatch.setenv(config.ENV_URL, "https://example.invalid/data.git")
    refuses(payload(), [RUN, str(root)])
    passes(payload(), [RUN, str(other)])


def test_the_hook_writes_nothing_into_the_data_checkout(root):
    owed_run(root)
    write(root, "blobs/sha256/ignored.bin", b"ignored")
    write(root, f"runs/{RUN}/rounds/0000/new.json", b"{}\n")
    before = snapshot(root)
    refuses(payload(), [RUN, str(root)])
    assert snapshot(root) == before
    commit_by_hand(root, "runs")
    before = snapshot(root)
    passes(payload(), [RUN, str(root)])
    assert snapshot(root) == before


def test_input_that_is_not_bytes_passes(root):
    owed_run(root)
    passes(payload().decode(), [RUN, str(root)])


def test_an_argument_list_that_has_no_length_passes(root):
    owed_run(root)
    passes(payload(), 5)
    passes(payload(), iter([RUN, str(root)]))


def test_a_fault_of_the_program_itself_passes(root, monkeypatch, capsys):
    owed_run(root)

    def broken(*_):
        raise KeyError("own fault")

    monkeypatch.setattr(stop_check, "_owed", broken)
    passes(payload(), [RUN, str(root)], capsys)


class Failing(io.StringIO):
    def __init__(self, fail_on):
        super().__init__()
        self.fail_on = fail_on

    def write(self, text):
        if self.fail_on == "write":
            raise OSError("closed")
        return super().write(text)

    def flush(self):
        if self.fail_on == "flush":
            raise OSError("closed")
        return super().flush()


@pytest.mark.parametrize("fail_on", ["write", "flush"])
def test_a_line_that_cannot_be_written_lets_the_stop_through(root, capsys, fail_on):
    owed_run(root)
    assert main(payload(), Failing(fail_on), [RUN, str(root)]) == EXIT_PASS
    assert capsys.readouterr() == ("", "")


def test_a_closed_standard_error_lets_the_stop_through(root, monkeypatch, capsys):
    owed_run(root)
    monkeypatch.setattr(sys, "stderr", None)
    assert main(payload(), None, [RUN, str(root)]) == EXIT_PASS
    assert capsys.readouterr() == ("", "")


def test_the_defaults_are_the_process_own(root, monkeypatch, capsys):
    owed_run(root)

    class Stdin:
        buffer = io.BytesIO(payload())

    monkeypatch.setattr(sys, "stdin", Stdin())
    monkeypatch.setattr(sys, "argv", ["-c", RUN, str(root)])
    assert main() == EXIT_REFUSE
    out, err = capsys.readouterr()
    assert (out, err) == ("", REFUSAL + "\n")


def test_a_failed_read_of_standard_input_passes(root, monkeypatch, capsys):
    owed_run(root)

    class Stdin:
        pass

    monkeypatch.setattr(sys, "stdin", Stdin())
    assert main(args=[RUN, str(root)]) == EXIT_PASS
    assert capsys.readouterr() == ("", "")


def test_walk_through_committed_then_stop(root):
    a_run(root)
    store_keys(root)
    assert run_commit.commit(root, RUN) is True
    passes(payload(), [RUN, str(root)])


def test_walk_through_stop_without_the_call_then_a_continued_stop(root):
    a_run(root)
    store_keys(root)
    refuses(payload(), [RUN, str(root)])
    passes(payload(stop_hook_active=True), [RUN, str(root)])
    assert run_commit.commit(root, RUN) is True
    passes(payload(stop_hook_active=True), [RUN, str(root)])
    passes(payload(), [RUN, str(root)])


def test_walk_through_a_run_that_is_over_and_committed(root):
    committed_run(root, 3)
    write_state(root, 3, others={"run_status": "over"})
    refuses(payload(), [RUN, str(root)])
    assert run_commit.commit(root, RUN) is True
    passes(payload(), [RUN, str(root)])


def test_walk_through_a_round_end_committed(root):
    committed_run(root)
    write_state(root, 1)
    refuses(payload(), [RUN, str(root)])
    assert run_commit.commit(root, RUN) is True
    passes(payload(), [RUN, str(root)])


def test_walk_through_state_written_after_the_end_call(root):
    committed_run(root, 3)
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    assert run_commit.commit(root, RUN) is True
    passes(payload(), [RUN, str(root)])
    write_state(root, 3, others={"note": "after the call"})
    refuses(payload(), [RUN, str(root)])
    assert run_commit.commit(root, RUN) is True
    passes(payload(), [RUN, str(root)])


def started(data, *args):
    return subprocess.run(
        [sys.executable, "-I", "-c", START, checkout_boundary.PACKAGE_DIRECTORY, *args],
        input=data,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_started_as_the_turn_loop_will_refuses_an_owed_run(root):
    owed_run(root)
    done = started(payload(), RUN, str(root))
    assert done.returncode == EXIT_REFUSE
    assert done.stdout == b""
    assert done.stderr.decode("utf-8").replace("\r\n", "\n") == REFUSAL + "\n"


def test_started_as_the_turn_loop_will_passes_a_run_that_owes_nothing(root):
    committed_run(root)
    done = started(payload(), RUN, str(root))
    assert (done.returncode, done.stdout, done.stderr) == (EXIT_PASS, b"", b"")


def test_started_without_the_data_root_argument_passes(root):
    owed_run(root)
    done = started(payload(), RUN)
    assert (done.returncode, done.stdout, done.stderr) == (EXIT_PASS, b"", b"")
