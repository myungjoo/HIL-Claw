import json
import os
import pathlib
import subprocess

import pytest

from hilclaw import (
    events,
    key_records,
    keys,
    layout,
    mcp_front,
    run_commit,
    run_state,
    tools,
)
from hilclaw.run_commit import commit, commit_owed, definition, owed_rounds

RUN = "run-a"
OTHER = "run-b"
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
OP_KEY = keys.op_signature_key(OP).name
HW_RECORD = layout.hw_profile_record(pathlib.Path(), HW_KEY).as_posix()
OP_RECORD = layout.op_signature_file(
    pathlib.Path(), HW_KEY, OP_KEY, "op_signature.json"
).as_posix()
OTHER_HW_KEY = keys.hw_profile_key({**HW, "revision": "rev 2"}).name
RUN_FILES = {
    f"runs/{RUN}/instance.json",
    f"runs/{RUN}/STATE.json",
    f"runs/{RUN}/events.ndjson",
}


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


def git(root, *args, input=None):
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        input=input,
        stdin=None if input is not None else subprocess.DEVNULL,
        capture_output=True,
        check=True,
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


def committed(root, revision="HEAD"):
    out = git(root, "ls-tree", "-r", "-z", "--name-only", revision)
    return {path.decode() for path in out.split(b"\0") if path}


def changed(root):
    out = git(root, "diff-tree", "--root", "-r", "-z", "--name-only", "HEAD")
    return {path.decode() for path in out.split(b"\0")[1:] if path}


def blob(root, path, revision="HEAD"):
    return git(root, "cat-file", "blob", f"{revision}:{path}")


def staged(root):
    out = git(root, "diff", "--cached", "--name-only", "-z")
    return {path.decode() for path in out.split(b"\0") if path}


def new_repository(root, ignore=b"blobs/sha256/\n*.tmp\n"):
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    if ignore is not None:
        (root / ".gitignore").write_bytes(ignore)
    return root


@pytest.fixture
def root(tmp_path):
    data = new_repository(tmp_path / "data")
    git(data, "add", ".gitignore")
    git(data, "commit", "-q", "-m", "start")
    return data


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def instance_document(op=True):
    document = {"schema_version": 1, "hw_profile": {"key": HW_KEY, "record": HW}}
    if op:
        document["op_signature"] = {"key": OP_KEY, "record": OP}
    return json.dumps(document).encode()


def write_instance(root, run_id=RUN, op=True):
    return write(root, f"runs/{run_id}/instance.json", instance_document(op))


def write_state(root, round, run_id=RUN):
    return write(root, f"runs/{run_id}/STATE.json", run_state.dump(round, EMPTY))


def write_events(root, content, run_id=RUN):
    return write(root, f"runs/{run_id}/events.ndjson", content)


def case(round, run_id=RUN):
    return layout.case_record(pathlib.Path(), HW_KEY, OP_KEY, run_id, round).as_posix()


def a_run(root, round=0, run_id=RUN, op=True):
    write_instance(root, run_id, op)
    write_state(root, round, run_id)
    write_events(root, b'{"line": 1}\n', run_id)
    return root


def store_keys(root, op=True):
    key_records.store_hw_profile(root, HW)
    if op:
        key_records.store_op_signature(root, HW_KEY, OP)


def commit_by_hand(root, *paths):
    git(root, "add", "-f", "--", *paths)
    git(root, "commit", "-q", "-m", "by hand")


def objects(root):
    return git(root, "count-objects", "-v")


def round_in_head(root, run_id=RUN):
    return run_state.parse(blob(root, f"runs/{run_id}/STATE.json")).round


def snapshot(root):
    files = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        files[relative] = path.read_bytes() if path.is_file() else None
    index = root / ".git" / "index"
    return head(root), index.read_bytes() if index.exists() else None, files


class Source:
    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.root


INDEX_NOT_UPDATED_LINE = (
    "run.commit: the commit was made and the index was not updated\n"
)


def tool(root):
    source = Source(root)
    return definition(source).function, source


# Happy paths


def test_round_zero_end_of_a_fresh_run_is_committed(root):
    write_instance(root)
    start = head(root)
    assert owed_rounds(root, RUN) == range(0)
    assert commit_owed(root, RUN) is True
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/instance.json"}
    assert commit(root, RUN) is False
    write_state(root, 0)
    write_events(root, b'{"line": 1}\n')
    assert owed_rounds(root, RUN) == range(0)
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", f"runs/{RUN}/events.ndjson"}
    assert round_in_head(root) == 0
    before = head(root)
    write_state(root, 1)
    assert owed_rounds(root, RUN) == range(1)
    assert commit(root, RUN) is True
    after = head(root)
    assert git(root, "rev-parse", "HEAD~1").strip().decode() == before
    assert git(root, "rev-parse", "HEAD~3").strip().decode() == start
    assert changed(root) == {f"runs/{RUN}/STATE.json"}
    assert git(root, "log", "-1", "--format=%s").strip().decode() == run_commit.MESSAGE
    assert git(root, "status", "--porcelain").strip() == b""
    assert commit(root, RUN) is False
    assert commit_owed(root, RUN) is False
    assert head(root) == after
    assert owed_rounds(root, RUN) == range(1, 1)


def test_a_round_zero_stop_commits_the_run_files_and_the_new_record_files(root):
    write_instance(root)
    assert commit(root, RUN) is True
    write_state(root, 0)
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    write(root, f"runs/{RUN}/rounds/0000/spec.json", b"{}\n")
    store_keys(root)
    assert commit_owed(root, RUN) is True
    assert commit(root, RUN) is True
    assert changed(root) == {
        f"runs/{RUN}/STATE.json",
        f"runs/{RUN}/events.ndjson",
        f"runs/{RUN}/rounds/0000/spec.json",
        HW_RECORD,
        OP_RECORD,
    }
    assert round_in_head(root) == 0
    assert git(root, "status", "--porcelain").strip() == b""
    assert commit(root, RUN) is False
    write_state(root, 1)
    assert owed_rounds(root, RUN) == range(1)
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json"}
    assert round_in_head(root) == 1


def test_a_later_round_end_commits_the_changed_files_and_the_cases_of_its_range(root):
    a_run(root, 0)
    write_state(root, 1)
    assert commit(root, RUN) is True
    write_state(root, 3)
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    write(root, f"runs/{RUN}/rounds/0001/decision/log.json", b"{}\n")
    write(root, case(1), b'{"case": 1}\n')
    write(root, case(2), b'{"case": 2}\n')
    assert owed_rounds(root, RUN) == range(1, 3)
    assert commit(root, RUN) is True
    assert changed(root) == {
        f"runs/{RUN}/STATE.json",
        f"runs/{RUN}/events.ndjson",
        f"runs/{RUN}/rounds/0001/decision/log.json",
        case(1),
        case(2),
    }
    assert blob(root, case(2)) == b'{"case": 2}\n'
    assert git(root, "status", "--porcelain").strip() == b""


def test_the_first_commit_of_a_repository_without_head(tmp_path):
    data = new_repository(tmp_path / "data")
    a_run(data, 1)
    assert head(data) is None
    assert owed_rounds(data, RUN) == range(1)
    assert commit(data, RUN) is True
    assert git(data, "rev-list", "--count", "HEAD").strip() == b"1"
    assert git(data, "log", "-1", "--format=%P").strip() == b""
    assert committed(data) == {
        f"runs/{RUN}/instance.json",
        f"runs/{RUN}/STATE.json",
        f"runs/{RUN}/events.ndjson",
    }
    assert git(data, "status", "--porcelain").decode().splitlines() == ["?? .gitignore"]
    assert commit(data, RUN) is False


@pytest.mark.parametrize("round", [None, 0])
def test_a_repository_without_head_commits_the_run_at_round_zero_or_without_a_state(
    tmp_path, round
):
    data = new_repository(tmp_path / "data")
    write_instance(data)
    expected = {f"runs/{RUN}/instance.json"}
    if round is not None:
        write_state(data, round)
        expected.add(f"runs/{RUN}/STATE.json")
    assert owed_rounds(data, RUN) == range(0)
    assert commit_owed(data, RUN) is True
    assert commit(data, RUN) is True
    assert git(data, "rev-list", "--count", "HEAD").strip() == b"1"
    assert committed(data) == expected
    assert commit(data, RUN) is False


def test_no_run_directory_owes_nothing(root):
    before = snapshot(root)
    assert owed_rounds(root, RUN) == range(0)
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    assert snapshot(root) == before


# Branches


def test_inside_a_round_the_changed_files_are_committed_with_the_round_unchanged(root):
    a_run(root, 0)
    write_state(root, 2)
    assert commit(root, RUN) is True
    after = head(root)
    write_events(root, b'{"line": 1}\n{"line": 2}\n{"torn"')
    write(root, f"runs/{RUN}/rounds/0002/decision/log.json", b"{}\n")
    assert owed_rounds(root, RUN) == range(2, 2)
    assert commit_owed(root, RUN) is True
    assert commit(root, RUN) is True
    assert git(root, "rev-parse", "HEAD~1").strip().decode() == after
    assert changed(root) == {
        f"runs/{RUN}/events.ndjson",
        f"runs/{RUN}/rounds/0002/decision/log.json",
    }
    assert round_in_head(root) == 2
    stored = blob(root, f"runs/{RUN}/events.ndjson")
    assert stored == b'{"line": 1}\n{"line": 2}\n'
    assert (root / f"runs/{RUN}/events.ndjson").read_bytes() == stored
    assert git(root, "status", "--porcelain").strip() == b""
    again = head(root)
    assert commit(root, RUN) is False
    assert head(root) == again
    write_state(root, 3)
    write(root, case(2), b'{"case": 2}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", case(2)}


def test_a_torn_tail_alone_owes_nothing_and_is_not_removed(root):
    a_run(root, 2)
    assert commit(root, RUN) is True
    write_events(root, b'{"line": 1}\n{"to')
    write(root, f"runs/{RUN}/scratch.tmp", b"partial")
    (root / f"runs/{RUN}/empty").mkdir()
    before = snapshot(root)
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    assert snapshot(root) == before


def test_a_new_log_of_a_torn_tail_alone_owes_nothing(root):
    write_instance(root)
    assert commit(root, RUN) is True
    write_events(root, b'{"to')
    before = snapshot(root)
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    assert snapshot(root) == before
    write_events(root, b'{"line": 1}\n{"to')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/events.ndjson"}
    assert blob(root, f"runs/{RUN}/events.ndjson") == b'{"line": 1}\n'


def test_a_case_of_the_round_in_progress_waits_for_its_round_end(root):
    a_run(root, 3)
    assert commit(root, RUN) is True
    write(root, case(3), b'{"case": 3}\n')
    before = snapshot(root)
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    assert snapshot(root) == before
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/events.ndjson"}
    lines = git(root, "status", "--porcelain", "-uall").decode().splitlines()
    assert lines == [f"?? {case(3)}"]
    write_state(root, 4)
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", case(3)}


def test_a_changed_tracked_file_alone_is_committed(root):
    a_run(root, 1)
    write(root, f"runs/{RUN}/rounds/0000/a.json", b"old\n")
    commit_by_hand(root, f"runs/{RUN}")
    write(root, f"runs/{RUN}/rounds/0000/a.json", b"new\n")
    assert commit_owed(root, RUN) is True
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/rounds/0000/a.json"}
    assert commit_owed(root, RUN) is False


def test_a_new_tmp_name_owes_nothing_whatever_the_ignore_file_says(tmp_path):
    data = new_repository(tmp_path / "data", ignore=None)
    a_run(data, 1)
    assert commit(data, RUN) is True
    write(data, f"runs/{RUN}/rounds/0001/note.tmp", b"partial")
    assert commit_owed(data, RUN) is False
    assert commit(data, RUN) is False


def test_a_changed_tracked_tmp_name_owes_nothing(root):
    a_run(root, 1)
    write(root, f"runs/{RUN}/old.tmp", b"one")
    commit_by_hand(root, f"runs/{RUN}")
    write(root, f"runs/{RUN}/old.tmp", b"two")
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False


def test_a_mode_change_is_judged_as_git_records_it(root):
    a_run(root, 1)
    script = write(root, f"runs/{RUN}/rounds/0000/run.sh", b"echo\n")
    commit_by_hand(root, f"runs/{RUN}")
    os.chmod(script, 0o755)
    trusted = git(root, "config", "--bool", "core.filemode").strip() == b"true"
    if trusted and not os.access(script, os.X_OK):
        pytest.skip("no executable bit can be set here")
    assert commit_owed(root, RUN) is trusted
    assert commit(root, RUN) is trusted
    if trusted:
        assert changed(root) == {f"runs/{RUN}/rounds/0000/run.sh"}
        entry = git(root, "ls-tree", "HEAD", "--", f"runs/{RUN}/rounds/0000/run.sh")
        assert entry.startswith(b"100755 ")
    assert commit(root, RUN) is False


def test_a_log_changed_by_more_than_a_torn_tail_is_compared_by_its_lines(root):
    a_run(root, 1)
    assert commit(root, RUN) is True
    write_events(root, b'{"line": 9}\n{"to')
    assert commit_owed(root, RUN) is True
    assert commit(root, RUN) is True
    assert blob(root, f"runs/{RUN}/events.ndjson") == b'{"line": 9}\n'


@pytest.mark.parametrize("tracked", [True, False])
def test_a_log_that_is_a_symbolic_link_owes_a_commit_and_is_refused(root, tracked):
    write_instance(root)
    write_state(root, 1)
    if tracked:
        write_events(root, b'{"line": 1}\n')
    commit_by_hand(root, f"runs/{RUN}")
    target = write(root, "elsewhere.ndjson", b'{"line": 1}\n')
    log = root / f"runs/{RUN}/events.ndjson"
    log.unlink(missing_ok=True)
    try:
        os.symlink(target, log)
    except (OSError, NotImplementedError):
        pytest.skip("no symbolic link can be created here")
    assert owed_rounds(root, RUN) == range(1, 1)
    before = snapshot(root)
    for call in (commit_owed, commit):
        with pytest.raises(run_commit.EventsNotRegularError):
            call(root, RUN)
    assert snapshot(root) == before


def test_a_case_of_the_range_is_taken_when_it_exists_and_skipped_when_not(root):
    a_run(root, 1)
    assert commit(root, RUN) is True
    write_state(root, 3)
    write(root, case(2), b'{"case": 2}\n')
    write(root, case(3), b'{"case": 3}\n')
    write(root, case(1, OTHER), b'{"other": 1}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", case(2)}
    assert not (root / case(1)).exists()
    lines = git(root, "status", "--porcelain", "-uall").decode().splitlines()
    assert sorted(lines) == sorted([f"?? {case(1, OTHER)}", f"?? {case(3)}"])


def test_a_changed_case_that_head_holds_is_taken(root):
    a_run(root, 1)
    write(root, case(1), b'{"case": "old"}\n')
    commit_by_hand(root, f"runs/{RUN}", case(1))
    write_state(root, 2)
    write(root, case(1), b'{"case": "new"}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", case(1)}
    assert blob(root, case(1)) == b'{"case": "new"}\n'


def test_round_zero_needs_no_key_directory_without_an_op_signature(root):
    a_run(root, 1, op=False)
    assert owed_rounds(root, RUN) == range(1)
    assert commit(root, RUN) is True
    assert f"runs/{RUN}/STATE.json" in committed(root)


def test_a_round_from_one_without_an_op_signature_is_refused(root):
    a_run(root, 1, op=False)
    assert commit(root, RUN) is True
    write_state(root, 2)
    write_events(root, b'{"line": 1}\n{"torn')
    before = snapshot(root)
    with pytest.raises(run_commit.NoKeyDirectoryError, match="no op_signature"):
        owed_rounds(root, RUN)
    with pytest.raises(run_commit.NoKeyDirectoryError):
        commit(root, RUN)
    assert snapshot(root) == before


def test_a_torn_tail_is_removed_before_the_commit(root):
    a_run(root, 0)
    write_events(root, b'{"line": 1}\n{"line": 2}\n{"li')
    write_state(root, 1)
    assert commit(root, RUN) is True
    stored = blob(root, f"runs/{RUN}/events.ndjson")
    assert stored == b'{"line": 1}\n{"line": 2}\n'
    assert stored.endswith(b"\n")
    assert (root / f"runs/{RUN}/events.ndjson").read_bytes() == stored


def test_a_run_without_events_is_committed(root):
    write_instance(root)
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/instance.json", f"runs/{RUN}/STATE.json"}


# What is never taken in


def test_temporary_ignored_blob_and_foreign_paths_stay_out_and_unchanged(root):
    (root / ".gitignore").write_bytes(b"blobs/sha256/\n*.tmp\nscratch.txt\n")
    a_run(root, 0)
    a_run(root, 0, OTHER)
    write(root, f"db/{HW_KEY}/{OP_KEY}/best.json", b'{"best": 0}\n')
    write(root, "notes.txt", b"old\n")
    commit_by_hand(root, ".gitignore", "runs", "db", "notes.txt")
    write_state(root, 2)
    write(root, f"runs/{RUN}/STATE.json.k3j9.tmp", b"partial")
    write(root, f"runs/{RUN}/scratch.txt", b"ignored")
    write(root, "blobs/sha256/ab/abcdef", b"\x00blob")
    write(root, "blobs/loose.bin", b"\x00loose")
    write_state(root, 1, OTHER)
    write(root, f"db/{HW_KEY}/{OP_KEY}/best.json", b'{"best": 1}\n')
    write(root, f"db/{OTHER_HW_KEY}/hw_profile.json", b'{"other": 1}\n')
    write(root, f"db/{OTHER_HW_KEY}/{OP_KEY}/op_signature.json", b'{"other": 2}\n')
    write(root, case(5), b'{"case": 5}\n')
    write(root, "notes.txt", b"new\n")
    git(root, "add", "notes.txt")
    write(root, "loose.txt", b"untracked\n")
    kept = {
        name: content
        for name, content in snapshot(root)[2].items()
        if not name.startswith(f"runs/{RUN}/")
    }
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json"}
    assert {
        name: content
        for name, content in snapshot(root)[2].items()
        if not name.startswith(f"runs/{RUN}/")
    } == kept
    assert (root / f"runs/{RUN}/STATE.json.k3j9.tmp").read_bytes() == b"partial"
    assert staged(root) == {"notes.txt"}
    assert blob(root, "notes.txt", "") == b"new\n"
    lines = git(root, "status", "--porcelain", "-uall").decode().splitlines()
    assert sorted(lines) == sorted(
        [
            "M  notes.txt",
            f" M db/{HW_KEY}/{OP_KEY}/best.json",
            f" M runs/{OTHER}/STATE.json",
            f"?? {case(5)}",
            f"?? db/{OTHER_HW_KEY}/hw_profile.json",
            f"?? db/{OTHER_HW_KEY}/{OP_KEY}/op_signature.json",
            "?? blobs/loose.bin",
            "?? loose.txt",
        ]
    )


def test_a_tmp_name_stays_out_whatever_the_ignore_file_says(tmp_path):
    data = new_repository(tmp_path / "data", ignore=None)
    a_run(data, 1)
    write(data, f"runs/{RUN}/STATE.json.x1.tmp", b"partial")
    write(data, f"runs/{RUN}/rounds/0000/note.tmp", b"partial")
    assert commit(data, RUN) is True
    assert committed(data) == {
        f"runs/{RUN}/instance.json",
        f"runs/{RUN}/STATE.json",
        f"runs/{RUN}/events.ndjson",
    }


def test_an_entry_staged_below_the_run_is_committed_as_the_working_tree_holds_it(root):
    a_run(root, 0)
    write(root, f"runs/{RUN}/rounds/0000/a.json", b"staged\n")
    git(root, "add", f"runs/{RUN}/rounds/0000/a.json")
    write(root, f"runs/{RUN}/rounds/0000/a.json", b"working\n")
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert blob(root, f"runs/{RUN}/rounds/0000/a.json") == b"working\n"
    assert git(root, "status", "--porcelain").strip() == b""


# The key record files (ADR-0134 decision 7)


def test_the_round_zero_commit_of_a_fresh_key_holds_both_record_files(root):
    a_run(root, 0)
    store_keys(root)
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES | {HW_RECORD, OP_RECORD}
    assert blob(root, HW_RECORD) == (root / HW_RECORD).read_bytes()
    assert git(root, "status", "--porcelain").strip() == b""


def test_record_files_created_after_the_last_commit_join_the_next_one(root):
    a_run(root, 0)
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES
    store_keys(root)
    write_state(root, 2)
    write(root, case(1), b'{"case": 1}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", case(1), HW_RECORD, OP_RECORD}
    assert git(root, "status", "--porcelain").strip() == b""


def test_each_record_file_is_taken_by_the_first_commit_after_it_exists(root):
    a_run(root, 0)
    store_keys(root, op=False)
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES | {HW_RECORD}
    key_records.store_op_signature(root, HW_KEY, OP)
    write_state(root, 2)
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", OP_RECORD}
    assert git(root, "status", "--porcelain").strip() == b""


def test_record_files_another_run_of_the_key_created_join_this_runs_commit(root):
    a_run(root, 0, OTHER)
    store_keys(root)
    a_run(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES | {HW_RECORD, OP_RECORD}
    lines = git(root, "status", "--porcelain").decode().splitlines()
    assert lines == [f"?? runs/{OTHER}/"]


def test_a_record_file_head_holds_is_never_taken_in_again(root):
    a_run(root, 0)
    store_keys(root)
    write_state(root, 1)
    assert commit(root, RUN) is True
    stored = blob(root, HW_RECORD)
    write(root, HW_RECORD, b'{"changed": "by hand"}\n')
    write_state(root, 2)
    write(root, case(1), b'{"case": 1}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/STATE.json", case(1)}
    assert blob(root, HW_RECORD) == stored
    assert staged(root) == set()
    lines = git(root, "status", "--porcelain").decode().splitlines()
    assert lines == [f" M {HW_RECORD}"]


def test_with_nothing_owed_no_record_file_is_staged_or_committed(root):
    a_run(root, 1)
    commit_by_hand(root, "runs")
    store_keys(root)
    before = snapshot(root)
    assert owed_rounds(root, RUN) == range(1, 1)
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    assert snapshot(root) == before
    assert staged(root) == set()


def test_a_changed_record_file_alone_owes_nothing(root):
    a_run(root, 1)
    store_keys(root)
    assert commit(root, RUN) is True
    write(root, HW_RECORD, b'{"changed": "by hand"}\n')
    before = snapshot(root)
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    assert snapshot(root) == before


def test_no_key_directory_is_asked_for_when_no_round_end_is_owed(root):
    a_run(root, 2, op=False)
    commit_by_hand(root, f"runs/{RUN}")
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    write(root, HW_RECORD, b'{"hw": 1}\n')
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/events.ndjson"}


@pytest.mark.parametrize(
    "content",
    [
        None,
        b"{}",
        b'{"schema_version": 9, "hw_profile": {}}',
        instance_document(op=False),
    ],
)
def test_an_instance_that_gives_no_key_takes_in_no_record_file(root, content):
    write_state(root, 1)
    write_events(root, b'{"line": 1}\n')
    if content is not None:
        write(root, f"runs/{RUN}/instance.json", content)
    write(root, HW_RECORD, b'{"hw": 1}\n')
    write(root, OP_RECORD, b'{"op": 1}\n')
    assert commit(root, RUN) is True
    assert f"runs/{RUN}/STATE.json" in changed(root)
    assert not changed(root) & {HW_RECORD, OP_RECORD}
    lines = git(root, "status", "--porcelain", "-uall").decode().splitlines()
    assert sorted(lines) == sorted([f"?? {HW_RECORD}", f"?? {OP_RECORD}"])


def test_the_refusal_without_a_key_stands_with_record_files_present(root):
    a_run(root, 1, op=False)
    assert commit(root, RUN) is True
    write(root, HW_RECORD, b'{"hw": 1}\n')
    write(root, OP_RECORD, b'{"op": 1}\n')
    write_state(root, 2)
    write_events(root, TORN)
    refused_unchanged(root, run_commit.NoKeyDirectoryError, "no op_signature")
    assert staged(root) == set()


def test_a_record_path_that_is_a_directory_is_not_taken_in(root):
    a_run(root, 0)
    write(root, f"{HW_RECORD}/inner", b"x")
    write(root, f"{OP_RECORD}/inner", b"y")
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES


def test_a_record_path_that_is_a_symbolic_link_is_not_taken_in(root):
    a_run(root, 0)
    store_keys(root, op=False)
    target = write(root, "elsewhere.json", b"{}\n")
    linked = root / OP_RECORD
    linked.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, linked)
    except (OSError, NotImplementedError):
        pytest.skip("no symbolic link can be created here")
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES | {HW_RECORD}
    assert linked.is_symlink()


def test_an_ignored_record_path_is_not_taken_in(root):
    (root / ".gitignore").write_bytes(b"blobs/sha256/\n*.tmp\nhw_profile.json\n")
    commit_by_hand(root, ".gitignore")
    a_run(root, 0)
    store_keys(root)
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES | {OP_RECORD}
    assert (root / HW_RECORD).is_file()


def test_the_content_of_a_record_file_is_not_read(root):
    a_run(root, 0)
    write(root, HW_RECORD, b"\x00not a record{")
    write(root, OP_RECORD, b"")
    write_state(root, 1)
    assert commit(root, RUN) is True
    assert changed(root) == RUN_FILES | {HW_RECORD, OP_RECORD}
    assert blob(root, HW_RECORD) == b"\x00not a record{"
    assert blob(root, OP_RECORD) == b""


# Failures: no_repository


def test_a_plain_directory_is_no_repository(tmp_path):
    data = tmp_path / "plain"
    a_run(data, 1)
    before = snapshot(data)
    with pytest.raises(run_commit.NoRepositoryError, match="top directory"):
        owed_rounds(data, RUN)
    with pytest.raises(run_commit.NoRepositoryError):
        commit(data, RUN)
    assert snapshot(data) == before


def test_a_data_root_below_another_repository_top_is_no_repository(root):
    below = root / "inner"
    a_run(below, 1)
    with pytest.raises(run_commit.NoRepositoryError):
        commit(below, RUN)
    assert head(root) is not None
    assert git(root, "rev-list", "--count", "HEAD").strip() == b"1"


def test_the_git_directory_is_no_repository(root):
    with pytest.raises(run_commit.NoRepositoryError):
        owed_rounds(root / ".git", RUN)


def test_git_that_cannot_be_run_is_its_own_error(root, monkeypatch, tmp_path):
    a_run(root, 1)
    monkeypatch.setattr(run_commit, "GIT", str(tmp_path / "no-such-git"))
    with pytest.raises(run_commit.GitNotRunError, match="could not be run"):
        owed_rounds(root, RUN)
    function, _ = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == run_commit.KIND_NO_REPOSITORY == "no_repository"


def test_a_variable_that_points_git_elsewhere_is_not_followed(root, monkeypatch):
    a_run(root, 1)
    monkeypatch.setenv("GIT_DIR", str(root / "nowhere"))
    monkeypatch.setenv("GIT_INDEX_FILE", str(root / "nowhere-index"))
    assert commit(root, RUN) is True
    monkeypatch.delenv("GIT_DIR")
    monkeypatch.delenv("GIT_INDEX_FILE")
    assert f"runs/{RUN}/STATE.json" in committed(root)


# Failures: commit_refused


def refused_unchanged(root, error, match=None, rounds=None):
    before = snapshot(root)
    if rounds is None:
        with pytest.raises(error, match=match):
            owed_rounds(root, RUN)
    else:
        assert owed_rounds(root, RUN) == rounds
    with pytest.raises(error, match=match):
        commit_owed(root, RUN)
    with pytest.raises(error, match=match):
        commit(root, RUN)
    assert snapshot(root) == before
    function, _ = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == run_commit.KIND_COMMIT_REFUSED == "commit_refused"
    assert snapshot(root) == before


TORN = b'{"line": 1}\n{"to'


@pytest.mark.parametrize(
    ("content", "match"),
    [
        (b"{}", "STATE.json"),
        (b'{"schema_version": 2}', "STATE.json"),
        (b"\xef\xbb\xbf{}", "byte order mark"),
    ],
)
def test_an_invalid_working_state_is_refused(root, content, match):
    a_run(root, 0)
    write_events(root, TORN)
    write(root, f"runs/{RUN}/STATE.json", content)
    refused_unchanged(root, run_commit.WorkingStateError, match)


def test_a_working_state_that_is_no_regular_file_is_refused(root):
    write_instance(root)
    write_events(root, TORN)
    (root / f"runs/{RUN}/STATE.json").mkdir()
    write(root, f"runs/{RUN}/STATE.json/inner", b"x")
    refused_unchanged(root, run_commit.WorkingStateError, "not a regular file")


def test_an_unreadable_working_state_is_refused(root, monkeypatch):
    a_run(root, 1)
    original = pathlib.Path.read_bytes

    def read_bytes(self):
        if self.name == "STATE.json":
            raise PermissionError(13, "Permission denied")
        return original(self)

    before = head(root)
    monkeypatch.setattr(pathlib.Path, "read_bytes", read_bytes)
    with pytest.raises(run_commit.WorkingStateError, match="could not be read"):
        commit(root, RUN)
    monkeypatch.undo()
    assert head(root) == before


def test_an_invalid_state_in_head_is_refused(root):
    a_run(root, 0)
    write(root, f"runs/{RUN}/STATE.json", b'{"schema_version": 1}')
    commit_by_hand(root, f"runs/{RUN}")
    write_state(root, 2)
    write_events(root, TORN)
    refused_unchanged(root, run_commit.HeadStateError, "in HEAD")


def test_a_state_in_head_that_is_a_directory_is_refused(root):
    a_run(root, 0)
    (root / f"runs/{RUN}/STATE.json").unlink()
    write(root, f"runs/{RUN}/STATE.json/inner", b"x")
    commit_by_hand(root, f"runs/{RUN}")
    (root / f"runs/{RUN}/STATE.json/inner").unlink()
    (root / f"runs/{RUN}/STATE.json").rmdir()
    write_state(root, 1)
    refused_unchanged(root, run_commit.HeadStateError, "not a regular file")


def test_a_working_round_below_that_of_head_is_refused(root):
    a_run(root, 3)
    commit_by_hand(root, f"runs/{RUN}")
    write_state(root, 2)
    write_events(root, TORN)
    refused_unchanged(root, run_commit.RoundBehindError, "below round 3")


def test_a_state_head_holds_and_the_working_tree_lacks_is_refused(root):
    a_run(root, 1)
    commit_by_hand(root, f"runs/{RUN}")
    (root / f"runs/{RUN}/STATE.json").unlink()
    write_events(root, TORN)
    refused_unchanged(root, run_commit.StateMissingError, "HEAD holds it")


def test_a_missing_file_is_refused_inside_a_round_and_at_its_end(root):
    a_run(root, 1)
    write(root, f"runs/{RUN}/rounds/0000/a.json", b"{}\n")
    commit_by_hand(root, f"runs/{RUN}")
    (root / f"runs/{RUN}/rounds/0000/a.json").unlink()
    write_events(root, TORN)
    refused_unchanged(
        root, run_commit.FileMissingError, "rounds/0000/a.json", range(1, 1)
    )
    write_state(root, 2)
    write(root, case(1), b"{}\n")
    refused_unchanged(root, run_commit.FileMissingError, "rounds/0000/a.json")


def test_events_that_are_no_regular_file_are_refused_whenever_owed(root):
    write_instance(root)
    write_state(root, 1)
    commit_by_hand(root, f"runs/{RUN}")
    (root / f"runs/{RUN}/events.ndjson").mkdir()
    assert commit_owed(root, RUN) is False
    assert commit(root, RUN) is False
    write(root, f"runs/{RUN}/events.ndjson/inner", b"x")
    refused_unchanged(
        root, run_commit.EventsNotRegularError, "events.ndjson", range(1, 1)
    )
    write_state(root, 2)
    refused_unchanged(root, run_commit.EventsNotRegularError, "events.ndjson")


@pytest.mark.parametrize("state", ["invalid", "behind", "missing"])
def test_the_checks_of_every_call_refuse_before_anything_is_compared(
    root, monkeypatch, state
):
    a_run(root, 2)
    commit_by_hand(root, f"runs/{RUN}")
    write_events(root, b'{"line": 1}\n{"line": 2}\n')
    if state == "invalid":
        write(root, f"runs/{RUN}/STATE.json", b"{}")
        error = run_commit.WorkingStateError
    elif state == "behind":
        write_state(root, 1)
        error = run_commit.RoundBehindError
    else:
        (root / f"runs/{RUN}/STATE.json").unlink()
        error = run_commit.StateMissingError

    def compared(*args):
        raise AssertionError("compared")

    monkeypatch.setattr(run_commit, "_changed", compared)
    refused_unchanged(root, error)


@pytest.mark.parametrize(
    "content", [None, b"{}", b'{"schema_version": 9, "hw_profile": {}}']
)
def test_an_instance_that_gives_no_key_directory_is_refused(root, content):
    write_state(root, 2)
    write_events(root, TORN)
    if content is not None:
        write(root, f"runs/{RUN}/instance.json", content)
    refused_unchanged(root, run_commit.NoKeyDirectoryError, "no key directory")


def test_a_log_the_removal_finds_corrupt_is_refused(root, monkeypatch):
    a_run(root, 1)
    before = head(root)

    def corrupt(data_root, run_id):
        raise events.CorruptEventsError(
            "runs/run-a/events.ndjson: is not a regular file"
        )

    monkeypatch.setattr(events, "remove_torn_tail", corrupt)
    with pytest.raises(run_commit.EventsNotRegularError):
        commit(root, RUN)
    assert head(root) == before


# Failures: commit_not_made


def test_no_author_identity_is_commit_not_made(root, monkeypatch):
    a_run(root, 0)
    git(root, "config", "user.useConfigOnly", "true")
    write_events(root, TORN)
    write_state(root, 1)
    before = snapshot(root)
    for name in IDENTITY:
        monkeypatch.delenv(name)
    with pytest.raises(run_commit.CommitNotMadeError, match="commit-tree"):
        commit(root, RUN)
    assert head(root) == before[0]
    assert before[1] == snapshot(root)[1]
    assert (root / f"runs/{RUN}/events.ndjson").read_bytes() == b'{"line": 1}\n'
    function, _ = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == run_commit.KIND_COMMIT_NOT_MADE == "commit_not_made"
    assert head(root) == before[0]


def test_a_held_lock_inside_a_round_is_commit_not_made_and_the_next_call_commits(
    root,
):
    a_run(root, 1)
    assert commit(root, RUN) is True
    write(root, f"runs/{RUN}/rounds/0001/a.json", b"{}\n")
    lock = root / ".git" / "index.lock"
    lock.write_bytes(b"")
    before = snapshot(root)
    with pytest.raises(run_commit.CommitNotMadeError, match="index lock"):
        commit(root, RUN)
    function, _ = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == "commit_not_made"
    assert snapshot(root) == before
    lock.unlink()
    assert commit(root, RUN) is True
    assert changed(root) == {f"runs/{RUN}/rounds/0001/a.json"}


@pytest.mark.parametrize("failed", ["update-index", "diff", "ls-files", "hash-object"])
def test_a_git_that_fails_a_step_of_the_comparison_is_commit_not_made(
    root, monkeypatch, failed
):
    a_run(root, 1)
    assert commit(root, RUN) is True
    write_events(root, b'{"line": 1}\n{"to')
    before = snapshot(root)
    real = run_commit._git

    def failing(data_root, *args, **kwargs):
        if failed in args:
            at = args.index(failed)
            args = (*args[:at], failed, "--no-such-option")
        return real(data_root, *args, **kwargs)

    monkeypatch.setattr(run_commit, "_git", failing)
    for call in (commit_owed, commit):
        with pytest.raises(run_commit.CommitNotMadeError, match=f"git {failed}"):
            call(root, RUN)
    assert snapshot(root) == before


def test_a_log_that_cannot_be_read_for_the_comparison_is_commit_not_made(
    root, monkeypatch
):
    a_run(root, 1)
    assert commit(root, RUN) is True
    write_events(root, b'{"line": 1}\n{"to')
    original = pathlib.Path.read_bytes

    def read_bytes(self):
        if self.name == "events.ndjson":
            raise PermissionError(13, "Permission denied")
        return original(self)

    before = head(root)
    monkeypatch.setattr(pathlib.Path, "read_bytes", read_bytes)
    with pytest.raises(run_commit.CommitNotMadeError, match="could not be read"):
        commit_owed(root, RUN)
    monkeypatch.undo()
    assert head(root) == before


def test_a_held_index_lock_is_commit_not_made_and_the_next_call_commits(root):
    a_run(root, 1)
    lock = root / ".git" / "index.lock"
    lock.write_bytes(b"")
    before = head(root)
    with pytest.raises(run_commit.CommitNotMadeError, match="index lock"):
        commit(root, RUN)
    assert head(root) == before
    assert lock.read_bytes() == b""
    lock.unlink()
    assert commit(root, RUN) is True
    assert head(root) != before


def test_a_failed_removal_is_commit_not_made(root, monkeypatch):
    a_run(root, 1)
    before = head(root)

    def failing(data_root, run_id):
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(events, "remove_torn_tail", failing)
    with pytest.raises(run_commit.CommitNotMadeError, match="torn tail"):
        commit(root, RUN)
    assert head(root) == before


@pytest.mark.parametrize("failed", ["read-tree", "add", "reset", "update-ref"])
def test_a_git_that_fails_a_step_is_commit_not_made(root, monkeypatch, failed):
    a_run(root, 1)
    before = snapshot(root)
    real = run_commit._git

    def failing(data_root, *args, **kwargs):
        if args[0] == failed:
            args = (failed, "--no-such-option")
        return real(data_root, *args, **kwargs)

    monkeypatch.setattr(run_commit, "_git", failing)
    with pytest.raises(run_commit.CommitNotMadeError, match=f"git {failed}"):
        commit(root, RUN)
    assert snapshot(root) == before
    assert not (root / ".git" / "index.lock").exists()


def test_a_failed_index_replacement_sets_the_entries_through_git(root, monkeypatch):
    a_run(root, 1)
    before = head(root)

    def refusing(source, target):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(run_commit.os, "replace", refusing)
    assert commit(root, RUN) is True
    monkeypatch.undo()
    assert head(root) != before
    assert not (root / ".git" / "index.lock").exists()
    assert f"runs/{RUN}/STATE.json" in committed(root)
    assert git(root, "status", "--porcelain").strip() == b""


def test_a_commit_and_a_fallback_that_works_write_no_line(root, monkeypatch, capsys):
    a_run(root, 1)
    assert commit(root, RUN) is True
    assert capsys.readouterr() == ("", "")
    (root / "runs" / RUN / "note.txt").write_text("more", encoding="utf-8")

    def refusing(source, target):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(run_commit.os, "replace", refusing)
    assert commit(root, RUN) is True
    assert capsys.readouterr() == ("", "")


def test_a_failed_replacement_and_reset_leave_the_commit_and_the_old_index(
    root, monkeypatch, capsys
):
    a_run(root, 1)
    before = snapshot(root)
    real = run_commit._git

    def refusing(source, target):
        raise PermissionError(13, "Permission denied")

    def failing(data_root, *args, **kwargs):
        if args[0] == "reset" and kwargs.get("index") is None:
            args = ("reset", "--no-such-option")
        return real(data_root, *args, **kwargs)

    monkeypatch.setattr(run_commit.os, "replace", refusing)
    monkeypatch.setattr(run_commit, "_git", failing)
    assert commit(root, RUN) is True
    monkeypatch.undo()
    assert head(root) != before[0]
    assert (root / ".git" / "index").read_bytes() == before[1]
    assert not (root / ".git" / "index.lock").exists()
    assert capsys.readouterr() == ("", INDEX_NOT_UPDATED_LINE)


def git_gone_at_the_fallback(monkeypatch):
    real = run_commit._git

    def refusing(source, target):
        raise PermissionError(13, "Permission denied")

    def gone(data_root, *args, **kwargs):
        if args[0] == "reset" and kwargs.get("index") is None:
            raise run_commit.GitNotRunError("git could not be run: secret")
        return real(data_root, *args, **kwargs)

    monkeypatch.setattr(run_commit.os, "replace", refusing)
    monkeypatch.setattr(run_commit, "_git", gone)


def test_git_not_run_at_the_fallback_leaves_the_commit_and_the_old_index(
    root, monkeypatch, capsys
):
    a_run(root, 1)
    before = snapshot(root)
    git_gone_at_the_fallback(monkeypatch)
    assert commit(root, RUN) is True
    monkeypatch.undo()
    assert head(root) != before[0]
    assert (root / ".git" / "index").read_bytes() == before[1]
    assert not (root / ".git" / "index.lock").exists()
    assert capsys.readouterr() == ("", INDEX_NOT_UPDATED_LINE)


def test_the_tool_answers_committed_when_the_index_was_not_updated(
    root, monkeypatch, capsys
):
    a_run(root, 1)
    function, _ = tool(root)
    git_gone_at_the_fallback(monkeypatch)
    assert function({"run_id": RUN}) == {"committed": True}
    assert capsys.readouterr() == ("", INDEX_NOT_UPDATED_LINE)


def test_no_standard_error_keeps_the_answer_and_standard_output(
    root, monkeypatch, capsys
):
    a_run(root, 1)
    git_gone_at_the_fallback(monkeypatch)
    monkeypatch.setattr(run_commit.sys, "stderr", None)
    assert commit(root, RUN) is True
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "content", ["1234567890123456789012345678901234567890", "not a ref"]
)
def test_a_head_that_names_no_commit_is_refused(root, content):
    a_run(root, 1)
    ref = root / ".git" / "refs" / "heads" / "main"
    ref.write_bytes(content.encode())
    before = snapshot(root)
    with pytest.raises(run_commit.HeadStateError, match="names no commit"):
        owed_rounds(root, RUN)
    function, _ = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == "commit_refused"
    assert snapshot(root) == before


# The read-only function


STATES = {
    "fresh": lambda root: write_instance(root),
    "nothing": lambda root: (a_run(root, 1), commit_by_hand(root, "runs")),
    "inside changed": lambda root: (
        a_run(root, 1),
        commit_by_hand(root, "runs"),
        write_events(root, b'{"line": 1}\n{"line": 2}\n{"to'),
        write(root, f"runs/{RUN}/rounds/0001/a.json", b"{}\n"),
        write(root, f"runs/{RUN}/instance.json", b"{}"),
        write(root, case(1), b"{}\n"),
        store_keys(root),
        write(root, "staged.txt", b"s"),
        git(root, "add", "staged.txt"),
    ),
    "owed": lambda root: a_run(root, 2),
    "inside": lambda root: (
        a_run(root, 0),
        commit_by_hand(root, "runs"),
        write_events(root, TORN),
    ),
    "behind": lambda root: (
        a_run(root, 2),
        commit_by_hand(root, "runs"),
        write_state(root, 1),
    ),
    "torn and owed": lambda root: (
        a_run(root, 0),
        commit_by_hand(root, "runs"),
        write_events(root, TORN),
        write_state(root, 1),
        write(root, f"runs/{RUN}/x.tmp", b"t"),
        write(root, "staged.txt", b"s"),
        git(root, "add", "staged.txt"),
    ),
}
ANSWERS = {
    "fresh": (range(0), True),
    "nothing": (range(1, 1), False),
    "inside changed": (range(1, 1), True),
    "owed": (range(2), True),
    "inside": (range(0), False),
    "behind": (run_commit.RoundBehindError, run_commit.RoundBehindError),
    "torn and owed": (range(1), True),
}


@pytest.mark.parametrize("state", list(STATES))
def test_the_read_only_answers_write_nothing(root, state):
    STATES[state](root)
    before = snapshot(root)
    count = objects(root)
    for function, answer in zip((owed_rounds, commit_owed), ANSWERS[state]):
        for _ in range(2):
            if isinstance(answer, type):
                with pytest.raises(answer):
                    function(root, RUN)
            else:
                assert function(root, RUN) == answer
    assert snapshot(root) == before
    assert objects(root) == count


@pytest.mark.parametrize("function", [owed_rounds, commit_owed])
def test_the_read_only_answers_refuse_a_bad_run_id(root, function):
    with pytest.raises(layout.InvalidPathValueError):
        function(root, "Bad Id")


def test_every_refusal_is_a_commit_refused_error():
    for error in (
        run_commit.WorkingStateError,
        run_commit.HeadStateError,
        run_commit.RoundBehindError,
        run_commit.StateMissingError,
        run_commit.FileMissingError,
        run_commit.EventsNotRegularError,
        run_commit.NoKeyDirectoryError,
    ):
        assert issubclass(error, run_commit.CommitRefusedError)
    for error in (
        run_commit.NoRepositoryError,
        run_commit.GitNotRunError,
        run_commit.CommitNotMadeError,
    ):
        assert not issubclass(error, run_commit.CommitRefusedError)


# The tool


def test_the_tool_commits_and_answers_committed(root):
    a_run(root, 1)
    function, source = tool(root)
    assert function({"run_id": RUN}) == {"committed": True}
    assert function({"run_id": RUN}) == {"committed": False}
    assert source.calls == 2


@pytest.mark.parametrize(
    "request_",
    [
        {},
        {"run_id": RUN, "data_root": "/elsewhere"},
        {"round": 1},
        {"run_id": "Bad Id"},
        {"run_id": 3},
        {"run_id": ""},
    ],
)
def test_the_tool_refuses_an_invalid_request_before_asking_the_source(root, request_):
    function, source = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function(request_)
    assert failed.value.kind == "invalid_request"
    assert source.calls == 0


def test_the_tool_without_a_data_root_is_no_data_root():
    def failing():
        raise RuntimeError("no data root in this test")

    with pytest.raises(tools.ToolFailure) as failed:
        definition(failing).function({"run_id": RUN})
    assert failed.value.kind == "no_data_root"


def test_the_tool_on_a_plain_directory_is_no_repository(tmp_path):
    a_run(tmp_path / "plain", 1)
    function, _ = tool(tmp_path / "plain")
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == "no_repository"


@pytest.mark.parametrize("source", [None, "data", 3])
def test_the_definition_refuses_a_source_that_is_not_callable(source):
    with pytest.raises(TypeError, match="must be callable"):
        definition(source)


def test_the_definition_states_its_name_schema_and_failures():
    held = definition(lambda: None)
    assert held.name == "run.commit"
    assert held.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}
        },
        "required": ["run_id"],
        "additionalProperties": False,
    }
    for word in (
        "never part of the request",
        "no_repository",
        "commit_refused",
        "commit_not_made",
        '{"committed": true or false}',
    ):
        assert word in held.description


def test_the_default_registry_and_the_mcp_front_hold_run_commit(root):
    a_run(root, 1)
    registry = tools.default_registry(lambda: root)
    assert "run.commit" in registry.names()
    held = registry.definition("run.commit")
    expected = definition(lambda: root)
    assert (held.description, held.input_schema) == (
        expected.description,
        expected.input_schema,
    )
    assert mcp_front.mcp_names(registry)["run_commit"] == "run.commit"
    assert tools.call(registry, "run.commit", {"run_id": RUN}) == {"committed": True}
    assert os.path.isfile(root / f"runs/{RUN}/STATE.json")
