import io
import json
import os
import re
import subprocess
from datetime import UTC, datetime, timedelta

import pytest

from hilclaw import artifacts, blob_gc, cas, layout
from hilclaw.blob_gc import (
    EXIT_DONE,
    EXIT_FAULT,
    EXIT_REPORTED,
    EXIT_USAGE,
    IN_GRACE,
    OPEN,
    PAST_GRACE,
    UNDETERMINED,
    UNREADABLE,
    CommitNotMadeError,
    GitNotRunError,
    NoRepositoryError,
)

# Synthetic values only: no hash, kind, run or time of a real run.
NOW = datetime(2026, 11, 1, tzinfo=UTC)
LONG_AGO = NOW - timedelta(days=60)
RECENT = NOW - timedelta(days=5)
KIND = "example_kind"
TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
BUDGET = {"totals": {}, "position": 0, "open_steps": []}


def git(root, *args, when=NOW):
    stamp = f"@{int(when.timestamp())} +0000"
    env = dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(name, None)
    done = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, env=env, check=True
    )
    return done.stdout.decode()


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    git(path, "init", "-q")
    git(path, "config", "user.name", "Synthetic")
    git(path, "config", "user.email", "synthetic@example.invalid")
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "core.autocrlf", "false")
    (path / ".gitignore").write_text("blobs/sha256/\n*.tmp\n")
    git(path, "add", ".gitignore")
    git(path, "commit", "-q", "-m", "start", when=LONG_AGO - timedelta(days=1))
    return path


def state(status="over"):
    document = {"schema_version": 1, "round": 5, "budget_spent": BUDGET}
    if status is not None:
        document["run_status"] = status
    return json.dumps(document).encode()


def run(root, run_id, *records, status="over", ended=LONG_AGO, commit=True):
    refs = []
    for content, retention_class in records:
        ref = cas.put_bytes(root, content)
        artifacts.add_record(
            root, run_id, ref, type=KIND, round=0, retention_class=retention_class
        )
        refs.append(ref.digest)
    directory = root / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "STATE.json").write_bytes(state(status))
    if commit:
        git(root, "add", f"runs/{run_id}")
        git(root, "commit", "-q", "-m", f"run {run_id}", when=ended)
    return refs


def records(root, run_id):
    return {r["sha256"]: r for r in artifacts.load(root, run_id)}


def head(root):
    return git(root, "rev-parse", "HEAD").strip()


def snapshot(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }, head(root)


def digests(blobs):
    return [b.sha256 for b in blobs]


def reading(planned, run_id):
    return next(r for r in planned.runs if r.run_id == run_id)


def call(argv):
    out, err = io.BytesIO(), io.BytesIO()
    status = blob_gc.main(argv, stdout=out, stderr=err)
    return status, out.getvalue(), err.getvalue()


# --- happy ---


def test_an_ended_run_past_its_grace_loses_its_intermediate_and_failed_blobs(root):
    contents = [
        (b"a", "intermediate"),
        (b"b", "failed"),
        (b"c", "best"),
        (b"d", "final"),
    ]
    gone_a, gone_b, best, final = run(root, "r1", *contents)
    before = head(root)

    planned, removal, committed = blob_gc.collect(root, now=NOW)

    assert digests(planned.removable) == sorted([gone_a, gone_b])
    assert reading(planned, "r1") == (
        "r1",
        PAST_GRACE,
        LONG_AGO.strftime("%Y-%m-%dT%H:%M:%SZ"),
        None,
    )
    assert [d for d, _ in removal.removed] == sorted([gone_a, gone_b])
    assert removal.edited == ("r1",) and not removal.failed and not removal.unrecorded
    held = records(root, "r1")
    for digest in (gone_a, gone_b):
        assert not cas.has_blob(root, digest)
        assert TIME.fullmatch(held[digest]["gc_at"])
    for digest in (best, final):
        assert cas.has_blob(root, digest) and "gc_at" not in held[digest]
    assert committed.index_updated
    assert git(root, "rev-parse", "HEAD~1").strip() == before
    assert git(root, "log", "-1", "--format=%s").strip() == blob_gc.MESSAGE
    changed = git(root, "show", "--name-only", "--format=", "HEAD").split()
    assert changed == ["runs/r1/artifacts.json"]
    assert git(root, "status", "--porcelain") == ""


def test_the_plan_writes_nothing(root):
    run(root, "r1", (b"a", "intermediate"))
    before = snapshot(root)

    planned = blob_gc.plan(root, now=NOW)

    assert len(planned.removable) == 1
    assert planned.now == "2026-11-01T00:00:00Z" and planned.grace_days == 30
    assert snapshot(root) == before


def test_the_command_line_reports_by_default_and_removes_on_request(root):
    (digest,) = run(root, "r1", (b"a", "failed"))
    before = snapshot(root)

    status, out, err = call(["--data-root", str(root)])

    document = json.loads(out)
    assert (status, err) == (EXIT_DONE, b"")
    assert document["mode"] == "report"
    assert document["removable"] == [
        {"sha256": digest, "runs": ["r1"], "lacking": ["r1"]}
    ]
    assert snapshot(root) == before

    status, out, err = call(["--remove", "--grace-days", "1", "--data-root", str(root)])

    document = json.loads(out)
    assert (status, err) == (EXIT_DONE, b"")
    assert [r["sha256"] for r in document["removed"]] == [digest]
    assert document["commit"] == head(root) and document["index_updated"] is True
    assert not cas.has_blob(root, digest)


# --- branches ---


def test_a_run_within_its_grace_keeps_its_blobs(root):
    (digest,) = run(root, "r1", (b"a", "intermediate"), ended=RECENT)

    planned = blob_gc.plan(root, now=NOW)

    assert reading(planned, "r1").state == IN_GRACE
    assert planned.removable == ()
    assert blob_gc.plan(root, now=NOW, grace_days=5).removable[0].sha256 == digest


@pytest.mark.parametrize("committed", [True, False])
def test_a_run_that_has_not_ended_keeps_its_blobs(root, committed):
    run(root, "r1", (b"a", "intermediate"), status=None, commit=committed)
    run(root, "r2", (b"b", "intermediate"), commit=False)

    planned = blob_gc.plan(root, now=NOW)

    assert [r.state for r in planned.runs] == [OPEN, OPEN]
    assert planned.removable == ()


def test_a_hash_best_in_one_run_and_intermediate_in_another_is_kept(root):
    (digest,) = run(root, "r1", (b"a", "best"))
    run(root, "r2", (b"a", "intermediate"))

    planned, removal, committed = blob_gc.collect(root, now=NOW)

    assert planned.removable == () and removal.removed == () and committed is None
    assert cas.has_blob(root, digest)


def test_a_hash_of_two_ended_runs_gets_gc_at_in_both(root):
    (digest,) = run(root, "r1", (b"a", "failed"))
    run(root, "r2", (b"a", "intermediate"))

    _, removal, _ = blob_gc.collect(root, now=NOW)

    assert removal.edited == ("r1", "r2")
    gc_at = removal.removed[0][1]
    assert records(root, "r1")[digest]["gc_at"] == gc_at
    assert records(root, "r2")[digest]["gc_at"] == gc_at


def test_a_blob_no_record_names_is_kept(root):
    loose = cas.put_bytes(root, b"loose").digest
    run(root, "r1", (b"a", "intermediate"))

    blob_gc.collect(root, now=NOW)

    assert cas.has_blob(root, loose)


def test_a_blob_already_gone_is_reported_and_its_record_kept(root):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    cas.blob_path(root, digest).unlink()

    planned, removal, committed = blob_gc.collect(root, now=NOW)

    assert digests(planned.absent) == [digest] and planned.removable == ()
    assert removal.removed == () and committed is None
    assert "gc_at" not in records(root, "r1")[digest]
    assert blob_gc.exit_status(blob_gc.report(planned)) == EXIT_REPORTED


def test_a_collected_blob_is_not_reported_again(root):
    run(root, "r1", (b"a", "intermediate"))
    blob_gc.collect(root, now=NOW)

    planned = blob_gc.plan(root, now=NOW)

    assert (planned.removable, planned.absent, planned.damaged) == ((), (), ())
    assert blob_gc.exit_status(blob_gc.report(planned)) == EXIT_DONE


def test_content_stored_again_after_a_gc(root, monkeypatch):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    _, first, _ = blob_gc.collect(root, now=NOW)
    gc_at = first.removed[0][1]
    run(root, "r2", (b"a", "intermediate"), status=None, ended=NOW)

    assert blob_gc.plan(root, now=NOW).removable == ()
    assert cas.has_blob(root, digest)

    (root / "runs" / "r2" / "STATE.json").write_bytes(state())
    git(root, "commit", "-q", "-am", "r2 over", when=LONG_AGO)
    monkeypatch.setattr(blob_gc, "_clock", lambda: NOW + timedelta(days=1))
    planned, second, _ = blob_gc.collect(root, now=NOW)

    assert planned.removable[0].lacking == ("r2",)
    assert second.removed == ((digest, "2026-11-02T00:00:00Z"),)
    assert records(root, "r1")[digest]["gc_at"] == gc_at
    assert records(root, "r2")[digest]["gc_at"] == "2026-11-02T00:00:00Z"


def test_a_blob_that_is_not_intact_is_reported_and_kept(root):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    cas.blob_path(root, digest).write_bytes(b"other")

    planned, removal, _ = blob_gc.collect(root, now=NOW)

    assert digests(planned.damaged) == [digest] and removal.removed == ()
    assert cas.blob_path(root, digest).read_bytes() == b"other"


@pytest.mark.parametrize(
    "content",
    [state("paused"), b"{}", json.dumps({"schema_version": 2}).encode()],
)
def test_a_run_whose_end_cannot_be_read_keeps_only_its_own_hashes(root, content):
    (kept,) = run(root, "r1", (b"a", "intermediate"))
    (gone,) = run(root, "r2", (b"b", "intermediate"))
    (root / "runs" / "r1" / "STATE.json").write_bytes(content)
    git(root, "commit", "-q", "-am", "r1 changed", when=LONG_AGO)

    planned = blob_gc.plan(root, now=NOW)

    assert reading(planned, "r1").state == UNDETERMINED
    assert reading(planned, "r1").message.startswith("runs/r1/STATE.json")
    assert digests(planned.removable) == [gone] and kept != gone
    assert blob_gc.exit_status(blob_gc.report(planned)) == EXIT_REPORTED


def test_uncommitted_records_keep_the_hashes_of_their_run(root):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    artifacts.set_retention_class(root, "r1", digest, "failed")

    planned = blob_gc.plan(root, now=NOW)

    assert reading(planned, "r1")[1:] == (
        UNDETERMINED,
        LONG_AGO.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runs/r1/artifacts.json: differs from HEAD",
    )
    assert planned.removable == ()


def test_entries_of_runs_that_hold_no_records(root):
    assert blob_gc.plan(root, now=NOW).runs == ()
    (root / "runs").mkdir()
    (root / "runs" / ".gitkeep").write_bytes(b"")

    planned = blob_gc.plan(root, now=NOW)

    assert (planned.runs, planned.blocked) == ((), ())


def test_a_repository_without_a_commit(tmp_path):
    root = tmp_path / "empty"
    root.mkdir()
    git(root, "init", "-q")
    run(root, "r1", (b"a", "intermediate"), commit=False)

    planned = blob_gc.plan(root, now=NOW)

    assert reading(planned, "r1").state == OPEN and planned.removable == ()
    with pytest.raises(CommitNotMadeError, match="HEAD names no commit"):
        blob_gc.commit(root, ["r1"])


def test_commit_without_anything_to_commit(root):
    run(root, "r1", (b"a", "intermediate"))

    assert blob_gc.commit(root, []) is None
    assert blob_gc.commit(root, ["r1"]) is None
    with pytest.raises(layout.InvalidPathValueError):
        blob_gc.commit(root, ["Not A Run"])


def test_the_report_after_a_removal(root):
    run(root, "r1", (b"a", "intermediate"))
    planned, removal, committed = blob_gc.collect(root, now=NOW)

    document = blob_gc.report(planned, removal, committed)

    assert document["mode"] == "remove" and document["commit_error"] is None
    assert document["runs"][0]["state"] == PAST_GRACE
    assert blob_gc.exit_status(document) == EXIT_DONE
    assert blob_gc.exit_status(dict(document, index_updated=False)) == EXIT_REPORTED


# --- negative ---


@pytest.mark.parametrize(
    "damage", [b"not json", b'{"schema_version": 1, "artifacts": [{}]}']
)
def test_an_invalid_artifacts_file_blocks_every_removal(root, damage):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    run(root, "r2", status=None)
    (root / "runs" / "r2" / "artifacts.json").write_bytes(damage)

    planned, removal, committed = blob_gc.collect(root, now=NOW)

    assert reading(planned, "r2").state == UNREADABLE
    assert planned.blocked[0].startswith("runs/r2/artifacts.json")
    assert planned.removable == () and removal.removed == () and committed is None
    assert cas.has_blob(root, digest)
    assert blob_gc.remove(root, planned._replace(removable=(1,))).removed == ()


def test_a_directory_name_layout_refuses_blocks_every_removal(root):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    (root / "runs" / "Not-A-Run").mkdir()

    planned = blob_gc.plan(root, now=NOW)

    assert planned.blocked[0].startswith("runs/Not-A-Run: run_id: must be")
    assert planned.removable == ()
    assert cas.has_blob(root, digest)


def test_a_symbolic_link_in_runs_blocks_every_removal(root, tmp_path):
    run(root, "r1", (b"a", "intermediate"))
    try:
        os.symlink(tmp_path, root / "runs" / "r2", target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links cannot be made here")

    planned = blob_gc.plan(root, now=NOW)

    assert planned.blocked == ("runs/r2: is a symbolic link",)


@pytest.mark.parametrize("grace_days", [0, -1])
def test_a_grace_period_below_one_day(root, grace_days):
    with pytest.raises(ValueError, match="grace_days must be at least 1"):
        blob_gc.plan(root, grace_days=grace_days)


@pytest.mark.parametrize("grace_days", [1.5, True, "30", None])
def test_a_grace_period_that_is_no_int(root, grace_days):
    with pytest.raises(TypeError, match="grace_days must be an int"):
        blob_gc.plan(root, grace_days=grace_days)


@pytest.mark.parametrize("now", [NOW.replace(tzinfo=None), "2026-11-01T00:00:00Z"])
def test_a_moment_that_is_no_aware_datetime(root, now):
    with pytest.raises(TypeError, match="now must be an aware datetime"):
        blob_gc.plan(root, now=now)


def test_a_data_root_that_is_no_git_working_tree(root, tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (root / "runs").mkdir()

    for where in (plain, root / "runs"):
        with pytest.raises(NoRepositoryError):
            blob_gc.plan(where, now=NOW)
        with pytest.raises(NoRepositoryError):
            blob_gc.commit(where, ["r1"])
    with pytest.raises(FileNotFoundError):
        blob_gc.plan(tmp_path / "missing", now=NOW)
    with pytest.raises(NotADirectoryError):
        blob_gc.remove(root / ".gitignore", None)


def test_git_that_cannot_be_run(root, tmp_path, monkeypatch):
    monkeypatch.setattr(blob_gc, "GIT", str(tmp_path / "no-such-git"))

    with pytest.raises(GitNotRunError):
        blob_gc.plan(root, now=NOW)


def test_a_removal_that_fails_leaves_the_record_without_gc_at(root, monkeypatch):
    (digest,) = run(root, "r1", (b"a", "intermediate"))

    def refuse(path):
        raise PermissionError(13, "synthetic refusal")

    monkeypatch.setattr(blob_gc.os, "unlink", refuse)
    planned, removal, committed = blob_gc.collect(root, now=NOW)

    assert digests(planned.removable) == [digest]
    assert removal.failed == ((digest, "[Errno 13] synthetic refusal"),)
    assert removal.removed == () and committed is None
    assert cas.has_blob(root, digest)
    assert "gc_at" not in records(root, "r1")[digest]
    report = blob_gc.report(planned, removal, committed)
    assert blob_gc.exit_status(report) == EXIT_REPORTED


@pytest.mark.parametrize("change", ["altered", "gone"])
def test_a_blob_that_changed_after_the_plan_is_left(root, change):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    planned = blob_gc.plan(root, now=NOW)
    path = cas.blob_path(root, digest)
    path.write_bytes(b"other") if change == "altered" else path.unlink()

    removal = blob_gc.remove(root, planned)

    assert removal.removed == () and removal.failed[0][0] == digest
    assert "gc_at" not in records(root, "r1")[digest]


def test_a_record_that_cannot_be_written_is_reported(root, monkeypatch):
    (digest,) = run(root, "r1", (b"a", "intermediate"))

    def refuse(*args):
        raise artifacts.CorruptArtifactsError("runs/r1/artifacts.json: synthetic")

    monkeypatch.setattr(blob_gc.artifacts, "set_gc_at", refuse)
    _, removal, committed = blob_gc.collect(root, now=NOW)

    assert removal.removed[0][0] == digest and not cas.has_blob(root, digest)
    assert removal.unrecorded == (("r1", digest, "runs/r1/artifacts.json: synthetic"),)
    assert removal.edited == () and committed is None


def test_a_commit_that_git_refuses_leaves_head(root):
    (digest,) = run(root, "r1", (b"a", "intermediate"))
    blob_gc.remove(root, blob_gc.plan(root, now=NOW))
    before = head(root)
    branch = git(root, "symbolic-ref", "--short", "HEAD").strip()
    lock = root / ".git" / "refs" / "heads" / f"{branch}.lock"
    lock.write_text("")

    with pytest.raises(CommitNotMadeError, match="git update-ref"):
        blob_gc.commit(root, ["r1"])

    lock.unlink()
    assert head(root) == before
    assert "gc_at" in records(root, "r1")[digest]


def test_an_index_that_cannot_be_updated(root):
    run(root, "r1", (b"a", "intermediate"))
    blob_gc.remove(root, blob_gc.plan(root, now=NOW))
    lock = root / ".git" / "index.lock"
    lock.write_text("")

    committed = blob_gc.commit(root, ["r1"])

    lock.unlink()
    assert committed == (head(root), False)


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["--remove"],
        ["--data-root"],
        ["--data-root", ""],
        ["--data-root", "x", "--data-root", "y"],
        ["--data-root", "x", "--grace-days", "0"],
        ["--data-root", "x", "--grace-days", "1.5"],
        ["--data-root", "x", "--grace-days", "-3"],
        ["--data-root", "x", "--grace-days", "1234567890"],
        ["--data-root", "x", "--other"],
    ],
)
def test_a_command_line_that_is_refused(argv):
    status, out, err = call(argv)

    assert (status, out) == (EXIT_USAGE, b"")
    assert err == f"hilclaw.blob_gc: {blob_gc.USAGE}\n".encode()


def test_a_command_line_fault(root, tmp_path):
    status, out, err = call(["--data-root", str(tmp_path / "missing")])

    assert (status, out) == (EXIT_FAULT, b"")
    assert err.startswith(b"hilclaw.blob_gc: fault: FileNotFoundError: ")

    class Short(io.BytesIO):
        def write(self, data):
            return 0

    status = blob_gc.main(
        ["--data-root", str(root)], stdout=Short(), stderr=io.BytesIO()
    )
    assert status == EXIT_FAULT


def test_a_commit_error_on_the_command_line_is_reported(root, monkeypatch):
    run(root, "r1", (b"a", "intermediate"))

    def refuse(data_root, run_ids):
        raise CommitNotMadeError("synthetic")

    monkeypatch.setattr(blob_gc, "commit", refuse)
    status, out, _ = call(["--data-root", str(root), "--remove"])

    document = json.loads(out)
    assert status == EXIT_REPORTED
    assert (document["commit"], document["commit_error"]) == (None, "synthetic")
