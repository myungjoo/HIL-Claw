import json
import os
import pathlib
import subprocess

import pytest

from hilclaw import events, keys, layout, mcp_front, run_commit, run_state, tools
from hilclaw.run_commit import commit, definition, owed_rounds

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


def commit_by_hand(root, *paths):
    git(root, "add", "-f", "--", *paths)
    git(root, "commit", "-q", "-m", "by hand")


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


def tool(root):
    source = Source(root)
    return definition(source).function, source


# Happy paths


def test_round_zero_end_of_a_fresh_run_is_committed(root):
    write_instance(root)
    before = head(root)
    assert owed_rounds(root, RUN) == range(0)
    assert commit(root, RUN) is False
    write_state(root, 0)
    assert commit(root, RUN) is False
    assert head(root) == before
    write_events(root, b'{"line": 1}\n')
    write_state(root, 1)
    assert owed_rounds(root, RUN) == range(1)
    assert commit(root, RUN) is True
    after = head(root)
    assert git(root, "rev-parse", "HEAD~1").strip().decode() == before
    assert changed(root) == {
        f"runs/{RUN}/instance.json",
        f"runs/{RUN}/STATE.json",
        f"runs/{RUN}/events.ndjson",
    }
    assert git(root, "log", "-1", "--format=%s").strip().decode() == run_commit.MESSAGE
    assert git(root, "status", "--porcelain").strip() == b""
    assert commit(root, RUN) is False
    assert head(root) == after
    assert owed_rounds(root, RUN) == range(1, 1)


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
def test_a_repository_without_head_owes_nothing_at_round_zero_or_without_a_state(
    tmp_path, round
):
    data = new_repository(tmp_path / "data")
    write_instance(data)
    if round is not None:
        write_state(data, round)
    before = snapshot(data)
    assert owed_rounds(data, RUN) == range(0)
    assert commit(data, RUN) is False
    assert snapshot(data) == before


def test_no_run_directory_owes_nothing(root):
    before = snapshot(root)
    assert owed_rounds(root, RUN) == range(0)
    assert commit(root, RUN) is False
    assert snapshot(root) == before


# Branches


def test_inside_a_round_nothing_is_committed_even_with_changed_files(root):
    a_run(root, 0)
    write_state(root, 2)
    assert commit(root, RUN) is True
    after = head(root)
    write_events(root, b'{"line": 1}\n{"line": 2}\n{"torn"')
    write(root, f"runs/{RUN}/rounds/0002/decision/log.json", b"{}\n")
    before = snapshot(root)
    assert owed_rounds(root, RUN) == range(2, 2)
    assert commit(root, RUN) is False
    assert snapshot(root) == before
    assert head(root) == after


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


def refused_unchanged(root, error, match=None):
    before = snapshot(root)
    with pytest.raises(error, match=match):
        owed_rounds(root, RUN)
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


def test_a_missing_file_is_refused_only_when_a_round_end_is_owed(root):
    a_run(root, 1)
    write(root, f"runs/{RUN}/rounds/0000/a.json", b"{}\n")
    commit_by_hand(root, f"runs/{RUN}")
    (root / f"runs/{RUN}/rounds/0000/a.json").unlink()
    write_events(root, TORN)
    assert owed_rounds(root, RUN) == range(1, 1)
    assert commit(root, RUN) is False
    write_state(root, 2)
    write(root, case(1), b"{}\n")
    refused_unchanged(root, run_commit.FileMissingError, "rounds/0000/a.json")


def test_events_that_are_no_regular_file_are_refused_only_when_owed(root):
    write_instance(root)
    write_state(root, 1)
    commit_by_hand(root, f"runs/{RUN}")
    (root / f"runs/{RUN}/events.ndjson").mkdir()
    write(root, f"runs/{RUN}/events.ndjson/inner", b"x")
    assert commit(root, RUN) is False
    write_state(root, 2)
    refused_unchanged(root, run_commit.EventsNotRegularError, "events.ndjson")


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


def test_a_failed_index_replacement_leaves_the_commit_and_the_old_index(
    root, monkeypatch
):
    a_run(root, 1)
    before = snapshot(root)

    def refusing(source, target):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(run_commit.os, "replace", refusing)
    assert commit(root, RUN) is True
    monkeypatch.undo()
    assert head(root) != before[0]
    assert (root / ".git" / "index").read_bytes() == before[1]
    assert not (root / ".git" / "index.lock").exists()
    assert f"runs/{RUN}/STATE.json" in committed(root)


def test_a_head_that_names_no_commit_is_refused(root):
    a_run(root, 1)
    ref = root / ".git" / "refs" / "heads" / "main"
    ref.write_text("1234567890123456789012345678901234567890", encoding="ascii")
    with pytest.raises(run_commit.HeadStateError, match="names no commit"):
        owed_rounds(root, RUN)
    function, _ = tool(root)
    with pytest.raises(tools.ToolFailure) as failed:
        function({"run_id": RUN})
    assert failed.value.kind == "commit_refused"


# The read-only function


STATES = {
    "fresh": lambda root: write_instance(root),
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
    "fresh": range(0),
    "owed": range(2),
    "inside": range(0),
    "behind": run_commit.RoundBehindError,
    "torn and owed": range(1),
}


@pytest.mark.parametrize("state", list(STATES))
def test_the_read_only_answer_writes_nothing(root, state):
    STATES[state](root)
    before = snapshot(root)
    answer = ANSWERS[state]
    if isinstance(answer, range):
        assert owed_rounds(root, RUN) == answer
        assert owed_rounds(root, RUN) == answer
    else:
        with pytest.raises(answer):
            owed_rounds(root, RUN)
    assert snapshot(root) == before


def test_the_read_only_answer_refuses_a_bad_run_id(root):
    with pytest.raises(layout.InvalidPathValueError):
        owed_rounds(root, "Bad Id")


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
