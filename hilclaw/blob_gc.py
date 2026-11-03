"""The GC of the content-addressed store (Requirements C-3; ADR-0195).

Command line: ``python -m hilclaw.blob_gc --data-root <path> [--grace-days <n>]
[--remove]``. A person or a script starts it; no runtime step does (ADR-0195
decision 2). Without ``--remove`` it only reports what a removal would do.

**Plan** (:func:`plan`, read-only). ``runs/`` is listed (one directory of
known path; no tree is walked) and each run's ``artifacts.json`` is read by
:func:`hilclaw.artifacts.load`. A run is *ended* when the ``STATE.json`` that
the commit ``HEAD`` holds for it is valid at version 1 and has ``run_status``
``"over"`` (ADR-0121); its end is the committer time of the last commit
reachable from ``HEAD`` that changed that file (ADR-0195 decision 4). A run
is *past its grace* when it is ended, its ``artifacts.json`` in the working
tree is as ``HEAD`` holds it, and at least ``grace_days`` times 86400 seconds
have passed since its end. A hash is *eligible* when every record of every
run that names it has the class ``intermediate`` or ``failed`` and belongs to
a run past its grace (ADR-0195 decision 6). An eligible hash whose blob is in
the store and intact is *removable*; one whose blob is not intact is reported
and kept; one whose blob is gone is reported when a record that names it has
no ``gc_at``. A ``runs/`` entry that could hold records and cannot be read —
a directory whose name :func:`hilclaw.layout.check_run_id` refuses, a
symbolic link, an ``artifacts.json`` that is invalid or unreadable — makes
nothing removable at all (ADR-0195 decision 7).

**Removal** (:func:`remove`). For each removable hash the blob is checked
again, the file at its place below ``blobs/sha256/`` is unlinked, the UTC
clock is read, and :func:`hilclaw.artifacts.set_gc_at` adds that moment to
every record naming the hash that has no ``gc_at``. Nothing else is deleted:
nothing below ``runs/`` or ``db/`` and no blob the plan did not name.

**Commit** (:func:`commit`). The ``artifacts.json`` files that got a
``gc_at`` are committed on ``HEAD`` in one local commit holding them alone,
built in a temporary index; then the index entries of those paths are set to
the commit. Nothing is pushed (#5 A-3). ``git`` is run with an argument list
and no shell, with the variables that point it at another repository
removed from its environment, as :mod:`hilclaw.run_commit` runs it.

**Report and exit statuses.** Standard output gets one JSON document and one
LF. :data:`EXIT_DONE` (0): nothing to report beyond what was done;
:data:`EXIT_REPORTED` (10): a condition was reported (a run whose end cannot
be read, a blocked plan, a blob gone or not intact, a removal, record or
commit that failed); :data:`EXIT_USAGE` (20): an argument was refused and
nothing was read; :data:`EXIT_FAULT` (21): the data root is no directory or
not the top of a git working tree, ``git`` cannot be run, or the report
cannot be written. Standard error gets one line only when no report was
written.
"""

import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from hilclaw import artifacts, cas, layout, run_state

DEFAULT_GRACE_DAYS = 30
SECONDS_PER_DAY = 86400
GC_CLASSES = ("intermediate", "failed")

PAST_GRACE = "past_grace"
IN_GRACE = "in_grace"
OPEN = "open"
UNDETERMINED = "undetermined"
UNREADABLE = "unreadable"

EXIT_DONE = 0
EXIT_REPORTED = 10
EXIT_USAGE = 20
EXIT_FAULT = 21

#: The program run as ``git``: a name looked up on ``PATH``, or a path.
GIT = "git"
#: The message of every commit this module makes.
MESSAGE = "Record gc_at of the blobs removed by the GC (hilclaw.blob_gc)"

USAGE = (
    "usage: python -m hilclaw.blob_gc --data-root <path> [--grace-days <n>] [--remove]"
)

_LOCATING = frozenset(
    {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_IMPLICIT_WORK_TREE",
        "GIT_COMMON_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_PREFIX",
    }
)
_DIGITS = re.compile(r"[0-9]{1,9}")
_ABSENT = object()


class NoRepositoryError(Exception):
    """The data root is not the top directory of a git working tree."""


class GitNotRunError(Exception):
    """The program :data:`GIT` could not be started."""


class CommitNotMadeError(Exception):
    """``git`` did not make the commit; ``HEAD`` is as it was."""


class RunReading(NamedTuple):
    """What the plan read of one run: its state, its end and why it is not past its grace."""

    run_id: str
    state: str
    ended_at: str | None
    message: str | None


class Blob(NamedTuple):
    """An eligible hash, the runs whose records name it, and those whose record lacks ``gc_at``."""

    sha256: str
    runs: tuple
    lacking: tuple


class Plan(NamedTuple):
    """Result of :func:`plan`; ``removable`` is empty whenever ``blocked`` is not."""

    now: str
    grace_days: int
    blocked: tuple
    runs: tuple
    removable: tuple
    absent: tuple
    damaged: tuple


class Removal(NamedTuple):
    """Result of :func:`remove`."""

    removed: tuple
    failed: tuple
    unrecorded: tuple
    edited: tuple


class Commit(NamedTuple):
    """Result of :func:`commit`: the commit made and whether the index entries were set."""

    commit: str
    index_updated: bool


def plan(data_root, *, grace_days=DEFAULT_GRACE_DAYS, now=None):
    """Return the :class:`Plan` of the GC of ``data_root``; nothing is written.

    ``grace_days`` is an ``int`` of at least 1 (a ``bool`` is none) and
    ``now`` an aware :class:`datetime.datetime`, the clock of this process in
    UTC when ``None``. Raises :class:`ValueError` or :class:`TypeError` for
    them, :class:`FileNotFoundError` or :class:`NotADirectoryError` when
    ``data_root`` is no existing directory, :class:`GitNotRunError` when
    ``git`` cannot be started and :class:`NoRepositoryError` when
    ``data_root`` is not the top directory of a git working tree. Every other
    condition is a reading of the plan.
    """
    _check_grace(grace_days)
    now = datetime.now(UTC) if now is None else now
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise TypeError("now must be an aware datetime")
    root = _root(data_root)
    _top(root)
    head = _head(root)
    blocked, readings, holders = [], [], {}
    for run_id, problem in _runs(root):
        if problem is not None:
            blocked.append(problem)
            continue
        try:
            records = artifacts.load(root, run_id)
        except (artifacts.CorruptArtifactsError, OSError) as error:
            message = _text(error)
            blocked.append(message)
            readings.append(RunReading(run_id, UNREADABLE, None, message))
            continue
        reading = _reading(root, head, run_id, int(now.timestamp()), grace_days)
        readings.append(reading)
        for record in records:
            holders.setdefault(record["sha256"], []).append((reading, record))
    removable, absent, damaged = [], [], []
    if not blocked:
        for digest in sorted(holders):
            held = holders[digest]
            if not all(_collectable(reading, record) for reading, record in held):
                continue
            runs = tuple(reading.run_id for reading, _ in held)
            lacking = tuple(r.run_id for r, record in held if "gc_at" not in record)
            blob = Blob(digest, runs, lacking)
            if not cas.has_blob(root, digest):
                if lacking:
                    absent.append(blob)
            elif _intact(root, digest):
                removable.append(blob)
            else:
                damaged.append(blob)
    return Plan(
        _moment(now),
        grace_days,
        tuple(blocked),
        tuple(readings),
        tuple(removable),
        tuple(absent),
        tuple(damaged),
    )


def remove(data_root, plan):
    """Remove the removable blobs of ``plan`` and add ``gc_at`` to their records.

    For each :class:`Blob` of ``plan.removable``, in order: the blob is
    re-hashed, and when it is gone or not intact it is left and reported in
    ``failed``; else its file is unlinked, and when that raises an
    :class:`OSError` it is reported in ``failed`` and no record changes;
    else the UTC clock is read and :func:`hilclaw.artifacts.set_gc_at` is
    called for each run of ``lacking``, a failure being reported in
    ``unrecorded``. Returns a :class:`Removal`; ``edited`` lists the runs
    whose file got a ``gc_at``. A plan with ``blocked`` removes nothing.
    """
    root = _root(data_root)
    removed, failed, unrecorded, edited = [], [], [], []
    for blob in () if plan.blocked else plan.removable:
        try:
            intact = cas.verify_blob(root, blob.sha256)
        except (cas.BlobNotFoundError, OSError) as error:
            failed.append((blob.sha256, _text(error)))
            continue
        if not intact:
            failed.append((blob.sha256, "the blob is no longer intact"))
            continue
        try:
            os.unlink(cas.blob_path(root, blob.sha256))
        except OSError as error:
            failed.append((blob.sha256, _text(error)))
            continue
        gc_at = _moment(_clock())
        removed.append((blob.sha256, gc_at))
        for run_id in blob.lacking:
            try:
                record = artifacts.set_gc_at(root, run_id, blob.sha256, gc_at)
            except (
                artifacts.ArtifactNotFoundError,
                artifacts.BlobPresentError,
                artifacts.CorruptArtifactsError,
                OSError,
            ) as error:
                unrecorded.append((run_id, blob.sha256, _text(error)))
                continue
            if record.get("gc_at") == gc_at and run_id not in edited:
                edited.append(run_id)
    return Removal(tuple(removed), tuple(failed), tuple(unrecorded), tuple(edited))


def commit(data_root, run_ids):
    """Commit the ``artifacts.json`` of each of ``run_ids`` on ``HEAD``; return a :class:`Commit`.

    Returns ``None`` when ``run_ids`` is empty or the files are as ``HEAD``
    holds them. The commit holds, against ``HEAD``, those files and nothing
    else, whatever else the working tree or the index holds; then the index
    entries of those paths are set to the commit, and ``index_updated`` says
    whether that succeeded (the commit stands either way). Raises
    :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that is
    none, :class:`GitNotRunError`, :class:`NoRepositoryError`, and
    :class:`CommitNotMadeError` when ``HEAD`` names no commit or ``git``
    fails a step before ``HEAD`` moves.
    """
    paths = sorted({f"runs/{layout.check_run_id(r)}/artifacts.json" for r in run_ids})
    root = _root(data_root)
    if not paths:
        return None
    _top(root)
    head = _head(root)
    if head is None:
        raise CommitNotMadeError("HEAD names no commit")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        index = os.path.join(scratch, "index")

        def step(*args):
            return _ok(_git(root, *args, index=index), f"git {args[0]}")

        step("read-tree", head)
        step("add", "--", *paths)
        tree = step("write-tree").strip().decode()
        held = _ok(_git(root, "rev-parse", f"{head}^{{tree}}"), "git rev-parse")
        if tree == held.strip().decode():
            return None
        made = step("commit-tree", tree, "-p", head, "-m", MESSAGE).strip().decode()
    done = _git(root, "update-ref", "-m", MESSAGE, "HEAD", made, head)
    _ok(done, "git update-ref")
    done = _git(root, "reset", "-q", made, "--", *paths)
    return Commit(made, done.returncode == 0)


def collect(data_root, *, grace_days=DEFAULT_GRACE_DAYS, now=None):
    """Plan, remove and commit in one call; return ``(plan, removal, commit)``.

    ``commit`` is ``None`` when no file got a ``gc_at``, else what
    :func:`commit` returns; a :class:`CommitNotMadeError` passes out after
    the removal, so the blobs stay removed and the edited files uncommitted.
    Raises what :func:`plan` raises before anything is removed.
    """
    planned = plan(data_root, grace_days=grace_days, now=now)
    removal = remove(data_root, planned)
    return planned, removal, commit(data_root, removal.edited)


def report(planned, removal=None, committed=None, commit_error=None):
    """Return the report document of a plan and, after a removal, of its outcome."""
    document = {
        "mode": "report" if removal is None else "remove",
        "now": planned.now,
        "grace_days": planned.grace_days,
        "blocked": list(planned.blocked),
        "runs": [r._asdict() for r in planned.runs],
        "removable": [_blob(b) for b in planned.removable],
        "absent": [_blob(b) for b in planned.absent],
        "damaged": [_blob(b) for b in planned.damaged],
    }
    if removal is not None:
        document.update(
            removed=[{"sha256": d, "gc_at": t} for d, t in removal.removed],
            failed=[{"sha256": d, "message": m} for d, m in removal.failed],
            unrecorded=[
                {"run_id": r, "sha256": d, "message": m}
                for r, d, m in removal.unrecorded
            ],
            commit=None if committed is None else committed.commit,
            index_updated=None if committed is None else committed.index_updated,
            commit_error=commit_error,
        )
    return document


def exit_status(document):
    """Return :data:`EXIT_DONE` or :data:`EXIT_REPORTED` for a report document."""
    shown = ("blocked", "absent", "damaged", "failed", "unrecorded")
    if any(document.get(name) for name in shown) or document.get("commit_error"):
        return EXIT_REPORTED
    if document.get("index_updated") is False:
        return EXIT_REPORTED
    states = (UNDETERMINED, UNREADABLE)
    if any(r["state"] in states for r in document["runs"]):
        return EXIT_REPORTED
    return EXIT_DONE


def main(argv=None, *, stdout=None, stderr=None):
    """Run the command line and return its exit status; no :class:`Exception` leaves the call."""
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    try:
        data_root, grace_days, removing = _arguments(args)
    except ValueError:
        _say(stderr, USAGE)
        return EXIT_USAGE
    try:
        if stdout is None:
            raise OSError("standard output is closed")
        if removing:
            planned = plan(data_root, grace_days=grace_days)
            removal = remove(data_root, planned)
            try:
                committed, error = commit(data_root, removal.edited), None
            except (CommitNotMadeError, GitNotRunError, NoRepositoryError) as e:
                committed, error = None, _text(e)
            document = report(planned, removal, committed, error)
        else:
            document = report(plan(data_root, grace_days=grace_days))
        text = (json.dumps(document, ensure_ascii=True) + "\n").encode("ascii")
        if stdout.write(text) != len(text):
            raise OSError("standard output took a part of the report")
        stdout.flush()
    except Exception as fault:  # noqa: BLE001
        _say(stderr, f"fault: {type(fault).__name__}: {_text(fault)}")
        return EXIT_FAULT
    return exit_status(document)


def _arguments(args):
    data_root, grace_days, removing = None, DEFAULT_GRACE_DAYS, False
    seen = set()
    position = 0
    while position < len(args):
        name = args[position]
        if name in seen:
            raise ValueError(name)
        seen.add(name)
        if name == "--remove":
            removing = True
            position += 1
            continue
        if name not in ("--data-root", "--grace-days") or position + 1 == len(args):
            raise ValueError(name)
        value = args[position + 1]
        if name == "--data-root":
            if not value:
                raise ValueError(name)
            data_root = value
        else:
            if not _DIGITS.fullmatch(value):
                raise ValueError(name)
            grace_days = int(value)
            _check_grace(grace_days)
        position += 2
    if data_root is None:
        raise ValueError("--data-root")
    return data_root, grace_days, removing


def _check_grace(grace_days):
    if type(grace_days) is not int:
        raise TypeError(f"grace_days must be an int, got {type(grace_days).__name__}")
    if grace_days < 1:
        raise ValueError(f"grace_days must be at least 1, got {grace_days}")


def _runs(root):
    try:
        entries = sorted(os.scandir(root / "runs"), key=lambda e: e.name)
    except (FileNotFoundError, NotADirectoryError):
        return
    for entry in entries:
        try:
            mode = entry.stat(follow_symlinks=False).st_mode
        except OSError as error:
            yield None, f"runs/{entry.name}: {_text(error)}"
            continue
        if stat.S_ISLNK(mode):
            yield None, f"runs/{entry.name}: is a symbolic link"
        elif stat.S_ISDIR(mode):
            try:
                yield layout.check_run_id(entry.name), None
            except layout.InvalidPathValueError as error:
                yield None, f"runs/{entry.name}: {error}"


def _reading(root, head, run_id, now, grace_days):
    prefix = f"runs/{run_id}"
    state_path = f"{prefix}/STATE.json"
    if head is None:
        return RunReading(run_id, OPEN, None, None)
    listed = _git(root, "ls-tree", "-z", head, "--", state_path)
    if listed.returncode:
        return RunReading(
            run_id, UNDETERMINED, None, f"{state_path}: git ls-tree failed"
        )
    if not listed.stdout:
        return RunReading(run_id, OPEN, None, None)
    content = _git(root, "cat-file", "blob", f"{head}:{state_path}")
    if content.returncode:
        return RunReading(
            run_id, UNDETERMINED, None, f"{state_path}: is no file in HEAD"
        )
    try:
        status = run_state.parse(content.stdout).others.get("run_status", _ABSENT)
    except (run_state.InvalidStateError, run_state.UnsupportedVersionError) as error:
        return RunReading(run_id, UNDETERMINED, None, f"{state_path} in HEAD: {error}")
    if status is _ABSENT:
        return RunReading(run_id, OPEN, None, None)
    if status != "over":
        message = f"{state_path} in HEAD: run_status {status!r} is not known"
        return RunReading(run_id, UNDETERMINED, None, message)
    logged = _git(root, "log", "-1", "--format=%ct", head, "--", state_path)
    try:
        if logged.returncode:
            raise ValueError("git log failed")
        ended = int(logged.stdout.decode("ascii").strip())
        ended_at = _moment(datetime.fromtimestamp(ended, UTC))
    except (ValueError, OverflowError, OSError) as error:
        message = f"{state_path}: the time of its last commit cannot be read: {error}"
        return RunReading(run_id, UNDETERMINED, None, message)
    files = f"{prefix}/artifacts.json"
    status = _git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", files
    )
    if status.returncode or status.stdout:
        message = f"{files}: differs from HEAD"
        return RunReading(run_id, UNDETERMINED, ended_at, message)
    if now - ended < grace_days * SECONDS_PER_DAY:
        return RunReading(run_id, IN_GRACE, ended_at, None)
    return RunReading(run_id, PAST_GRACE, ended_at, None)


def _collectable(reading, record):
    return reading.state == PAST_GRACE and record["retention_class"] in GC_CLASSES


def _intact(root, digest):
    try:
        return cas.verify_blob(root, digest)
    except (cas.BlobNotFoundError, OSError):
        return False


def _blob(blob):
    return {
        "sha256": blob.sha256,
        "runs": list(blob.runs),
        "lacking": list(blob.lacking),
    }


def _moment(when):
    return when.astimezone(UTC).replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def _clock():
    return datetime.now(UTC)


def _root(data_root):
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    return root


def _top(root):
    done = _git(root, "rev-parse", "--is-inside-work-tree", "--show-prefix")
    if done.returncode or done.stdout.splitlines()[:2] != [b"true", b""]:
        raise NoRepositoryError(
            f"the data root is not the top directory of a git working tree: {root}"
        )


def _head(root):
    done = _git(root, "rev-parse", "--verify", "-q", "HEAD^{commit}")
    return done.stdout.strip().decode() if done.returncode == 0 else None


def _git(root, *args, index=None):
    env = {name: value for name, value in os.environ.items() if name not in _LOCATING}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    if index is not None:
        env["GIT_INDEX_FILE"] = index
    command = [GIT, "--literal-pathspecs", "-C", os.fspath(root), *args]
    try:
        return subprocess.run(
            command, capture_output=True, env=env, check=False, stdin=subprocess.DEVNULL
        )
    except OSError as e:
        raise GitNotRunError(f"git could not be run: {type(e).__name__}: {e}") from e


def _ok(done, what):
    if done.returncode:
        said = " ".join(done.stderr.decode("utf-8", "replace").split())[:400]
        raise CommitNotMadeError(
            f"{what}: git failed with status {done.returncode}: {said}"
        )
    return done.stdout


def _text(error):
    return " ".join(str(error).split())[:400] or type(error).__name__


def _standard(name):
    stream = getattr(sys, name, None)
    return getattr(stream, "buffer", None)


def _say(stderr, text):
    try:
        if stderr is not None:
            stderr.write(
                f"hilclaw.blob_gc: {text}\n".encode("ascii", "backslashreplace")
            )
            stderr.flush()
    except (OSError, ValueError):
        pass


if __name__ == "__main__":
    raise SystemExit(main())
