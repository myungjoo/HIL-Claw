"""The commit of a round end and the tool ``run.commit`` (ADR-0127, slice (1)).

A round end of the run ``run_id`` is *owed* when the working tree's
``runs/<run_id>/STATE.json`` is valid at version 1 with ``round`` *W* and
either the commit ``HEAD`` holds no ``STATE.json`` for the run and *W* >= 1,
or holds one, valid at version 1, with ``round`` *H* < *W* (ADR-0127
decision 4). Only ``round`` is read for this; no commit message or author is.
:func:`owed_rounds` answers the rule read-only; :func:`commit` makes the owed
commit; :func:`definition` is the registry tool ``run.commit`` over it.

The commit holds, against ``HEAD``, every new or changed file below
``runs/<run_id>/`` and the existing case files of the rounds *H* to *W* - 1
from round 1 (ADR-0072 decisions 1 and 3), and nothing else. A path whose name
ends with ``.tmp``, a path the repository ignores and anything below
``blobs/`` is never taken in; no content is inspected.

The module runs the ``git`` program of the machine (:data:`GIT`) with an
argument list and no shell, with the variables that point ``git`` at another
repository removed from its environment. The tool is not an FR-10 tool: it is
not journaled, appends nothing to ``events.ndjson`` and selects no backend
(ADR-0127 decision 4, as ADR-0124 decision 3 reads its tools).
"""

import os
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

from hilclaw import data_root_source, events, instance, layout, run_state, tools

#: The data root is not the top directory of a git working tree, or ``git`` cannot be run.
KIND_NO_REPOSITORY = "no_repository"
#: The run's files are in a state the commit does not repair; nothing was removed or committed.
KIND_COMMIT_REFUSED = "commit_refused"
#: The torn tail could not be removed or ``git`` did not make the commit; ``HEAD`` is as it was.
KIND_COMMIT_NOT_MADE = "commit_not_made"

#: The program run as ``git``: a name looked up on ``PATH``, or a path.
GIT = "git"
#: The message of every commit this module makes; nothing reads it.
MESSAGE = "Commit an owed round end (run.commit)"

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
_REGULAR_MODES = ("100644", "100755")
_RUN_ID_SCHEMA = {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}
_DESCRIPTION = (
    "Commit the round end of the run run_id when one is owed: when the round of "
    "the run's STATE.json in the data repository's working tree is beyond the "
    "round of the STATE.json of the last commit (HEAD), a torn tail of "
    "events.ndjson is removed and one commit is made that holds every new or "
    "changed file below runs/<run_id>/ and the case files of the rounds that "
    "ended. Files named *.tmp, ignored paths and anything below blobs/ are never "
    "committed, and nothing else of the working tree or the index changes. When "
    "nothing is owed, nothing is written, so the call is safe at every entry. "
    'The result is {"committed": true or false}. The data root is never part of '
    "the request; the tool knows it. It fails with no_repository when the data "
    "root is not the top directory of a git working tree or git cannot be run, "
    "commit_refused when the run's files are in a state the commit does not "
    "repair (nothing is removed or committed), and commit_not_made when the torn "
    "tail could not be removed or git did not make the commit (HEAD is unchanged)."
)


class NoRepositoryError(Exception):
    """The data root is not the top directory of a git working tree."""


class GitNotRunError(Exception):
    """The program :data:`GIT` could not be started."""


class CommitRefusedError(Exception):
    """A state of the run that the commit does not repair; the subclass names the condition."""


class WorkingStateError(CommitRefusedError):
    """The working tree's ``STATE.json`` is invalid, of another version, no regular file or unreadable."""


class HeadStateError(CommitRefusedError):
    """The ``STATE.json`` that ``HEAD`` holds for the run is not valid at version 1, or cannot be read."""


class RoundBehindError(CommitRefusedError):
    """The working tree's ``round`` is below that of ``HEAD``."""


class StateMissingError(CommitRefusedError):
    """``HEAD`` holds a ``STATE.json`` for the run and the working tree does not."""


class FileMissingError(CommitRefusedError):
    """A file that ``HEAD`` holds below ``runs/<run_id>/`` is missing from the working tree."""


class EventsNotRegularError(CommitRefusedError):
    """``runs/<run_id>/events.ndjson`` is there and is no regular file."""


class NoKeyDirectoryError(CommitRefusedError):
    """The owed range holds a round from 1 and ``instance.json`` gives no key directory."""


class CommitNotMadeError(Exception):
    """The torn tail could not be removed or ``git`` did not make the commit; ``HEAD`` is unchanged."""


class _Found(NamedTuple):
    rounds: range
    head: str | None
    held: tuple
    keys: tuple | None


def owed_rounds(data_root, run_id):
    """Return the rounds whose end is owed for the run ``run_id``: ``range(H, W)``, empty when none is.

    ``H`` is the ``round`` of the ``STATE.json`` that ``HEAD`` holds for the
    run (0 when it holds none) and ``W`` that of the working tree's
    (ADR-0127 decision 4). Nothing is written to the working tree, the index
    or ``HEAD``, and no optional lock of ``git`` is taken.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that
    is none; :class:`GitNotRunError` when ``git`` cannot be started;
    :class:`NoRepositoryError` when ``data_root`` is not the top directory of a
    git working tree; then, at every call, :class:`WorkingStateError`,
    :class:`HeadStateError`, :class:`RoundBehindError` and
    :class:`StateMissingError`; and, only when a round end is owed,
    :class:`FileMissingError`, :class:`EventsNotRegularError` and
    :class:`NoKeyDirectoryError`. All of the latter seven are
    :class:`CommitRefusedError`.
    """
    return _assess(data_root, run_id).rounds


def commit(data_root, run_id):
    """Make the owed commit of the run ``run_id``; return whether a commit was made.

    With nothing owed (:func:`owed_rounds` empty) nothing is written and the
    result is ``False``. Otherwise the torn tail of ``events.ndjson`` is
    removed (:func:`hilclaw.events.remove_torn_tail`), one commit holding the
    paths of the module docstring is made on ``HEAD`` (the repository's first
    when there is no ``HEAD``), the index entries of exactly those paths are
    set to the commit, and the result is ``True``. Nothing else of the working
    tree or the index is changed; a path staged elsewhere stays staged.

    Raises what :func:`owed_rounds` raises, with nothing removed or committed,
    and :class:`CommitNotMadeError` when the removal fails with an
    :class:`OSError`, ``git`` fails a step of the commit, or the index lock is
    held; ``HEAD`` is then as it was, and a removed torn tail stays removed.
    """
    found = _assess(data_root, run_id)
    if not found.rounds:
        return False
    cases = ()
    if found.keys is not None:
        cases = tuple(
            layout.case_record(Path(), *found.keys, run_id, r).as_posix()
            for r in found.rounds
            if r >= 1
        )
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        index = os.path.join(scratch, "index")

        def step(*args, input=None):
            done = _git(data_root, *args, index=index, input=input)
            return _ok(done, CommitNotMadeError, f"git {args[0]}")

        step("read-tree", *((found.head,) if found.head else ("--empty",)))
        listed = step(
            "ls-files",
            "-z",
            "--cached",
            "--others",
            "--exclude-standard",
            "--",
            f"runs/{run_id}/",
            *cases,
        )
        paths = sorted(
            path
            for path in set(_paths(listed))
            if not path.endswith((".tmp", "/")) and _is_file(data_root, path)
        )
        try:
            events.remove_torn_tail(data_root, run_id)
        except events.CorruptEventsError as e:
            raise EventsNotRegularError(str(e)) from e
        except OSError as e:
            raise CommitNotMadeError(f"the torn tail was not removed: {e}") from e
        listing = b"\0".join(os.fsencode(path) for path in paths)
        if paths:
            step("add", "--pathspec-from-file=-", "--pathspec-file-nul", input=listing)
        tree = step("write-tree").strip().decode()
        parents = ("-p", found.head) if found.head else ()
        made = step("commit-tree", tree, *parents, "-m", MESSAGE).strip().decode()
    lock = _ok(
        _git(data_root, "rev-parse", "--git-path", "index.lock"),
        CommitNotMadeError,
        "git rev-parse",
    )
    if os.path.lexists(os.path.join(data_root, lock.strip().decode())):
        raise CommitNotMadeError("the index lock of the repository is held")
    done = _git(data_root, "update-ref", "-m", MESSAGE, "HEAD", made, found.head or "")
    _ok(done, CommitNotMadeError, "git update-ref")
    if paths:
        _git(
            data_root,
            "reset",
            "-q",
            made,
            "--pathspec-from-file=-",
            "--pathspec-file-nul",
            input=listing,
        )
    return True


def definition(source):
    """Return the :class:`hilclaw.tools.ToolDefinition` of ``run.commit``, bound to ``source``.

    ``source`` is the data-root source of ADR-0015 decision 3, asked at each
    call after the request was checked; raises :class:`TypeError` when it is
    not callable. The tool function takes exactly ``{"run_id": ...}`` and
    returns ``{"committed": bool}`` of :func:`commit`. It raises
    :class:`hilclaw.tools.ToolFailure` of kind ``invalid_request`` for any
    other request or a ``run_id`` :func:`hilclaw.layout.check_run_id`
    refuses, ``no_data_root`` as :func:`hilclaw.data_root_source.obtain`
    does, :data:`KIND_NO_REPOSITORY` for :class:`NoRepositoryError` and
    :class:`GitNotRunError`, :data:`KIND_COMMIT_REFUSED` for
    :class:`CommitRefusedError` and :data:`KIND_COMMIT_NOT_MADE` for
    :class:`CommitNotMadeError`.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def run_commit(request):
        run_id = _run_id(request)
        data_root = data_root_source.obtain(source)
        try:
            return {"committed": commit(data_root, run_id)}
        except (NoRepositoryError, GitNotRunError) as e:
            raise tools.ToolFailure(KIND_NO_REPOSITORY, str(e)) from e
        except CommitRefusedError as e:
            raise tools.ToolFailure(KIND_COMMIT_REFUSED, str(e)) from e
        except CommitNotMadeError as e:
            raise tools.ToolFailure(KIND_COMMIT_NOT_MADE, str(e)) from e

    schema = {
        "type": "object",
        "properties": {"run_id": dict(_RUN_ID_SCHEMA)},
        "required": ["run_id"],
        "additionalProperties": False,
    }
    return tools.ToolDefinition("run.commit", run_commit, _DESCRIPTION, schema)


def _run_id(request):
    others = sorted(name for name in request if name != "run_id")
    if others:
        raise tools.ToolFailure(
            tools.KIND_INVALID_REQUEST,
            f"the request takes the member run_id only, not {', '.join(map(repr, others))}",
        )
    if "run_id" not in request:
        raise tools.ToolFailure(
            tools.KIND_INVALID_REQUEST, "the request lacks the member run_id"
        )
    try:
        return layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise tools.ToolFailure(tools.KIND_INVALID_REQUEST, f"the request's {e}") from e


def _assess(data_root, run_id):
    prefix = f"runs/{layout.check_run_id(run_id)}/"
    done = _git(data_root, "rev-parse", "--is-inside-work-tree", "--show-prefix")
    if done.returncode or done.stdout.splitlines()[:2] != [b"true", b""]:
        raise NoRepositoryError(
            f"the data root is not the top directory of a git working tree: {data_root}"
        )
    done = _git(data_root, "rev-parse", "--verify", "-q", "HEAD^{commit}")
    head = done.stdout.strip().decode() if done.returncode == 0 else None
    held = ()
    if head is not None:
        listed = _git(data_root, "ls-tree", "-r", "-z", head, "--", prefix)
        held = tuple(_entries(_ok(listed, HeadStateError, f"{prefix} in HEAD")))
    working = _working_round(data_root, run_id, prefix)
    committed = _head_round(data_root, prefix, held)
    if working is None:
        if committed is not None:
            raise StateMissingError(
                f"{prefix}STATE.json: HEAD holds it and the working tree does not"
            )
        return _Found(range(0), head, held, None)
    start = 0 if committed is None else committed
    if working < start:
        raise RoundBehindError(
            f"{prefix}STATE.json: round {working} is below round {start} of HEAD"
        )
    rounds = range(start, working)
    if not rounds:
        return _Found(rounds, head, held, None)
    for path, _, kind, _ in held:
        if kind == "blob" and not _is_file(data_root, path):
            raise FileMissingError(
                f"{path}: HEAD holds it and the working tree does not"
            )
    log = layout.run_file(data_root, run_id, "events.ndjson")
    try:
        regular = stat.S_ISREG(os.lstat(log).st_mode)
    except OSError:
        regular = True
    if not regular:
        raise EventsNotRegularError(f"{prefix}events.ndjson: is not a regular file")
    keys = None
    if working >= 2:
        keys = _keys(data_root, run_id, prefix)
    return _Found(rounds, head, held, keys)


def _working_round(data_root, run_id, prefix):
    path = layout.run_file(data_root, run_id, "STATE.json")
    file = f"{prefix}STATE.json"
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise WorkingStateError(f"{file}: is not a regular file")
        content = path.read_bytes()
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError as e:
        raise WorkingStateError(f"{file}: could not be read: {e}") from e
    try:
        return run_state.parse(content).round
    except (run_state.InvalidStateError, run_state.UnsupportedVersionError) as e:
        raise WorkingStateError(f"{file}: {e}") from None


def _head_round(data_root, prefix, held):
    file = f"{prefix}STATE.json"
    entry = next((entry for entry in held if entry[0] == file), None)
    if entry is None:
        if any(path.startswith(file + "/") for path, *_ in held):
            raise HeadStateError(f"{file} in HEAD: is not a regular file")
        return None
    _, mode, kind, oid = entry
    if kind != "blob" or mode not in _REGULAR_MODES:
        raise HeadStateError(f"{file} in HEAD: is not a regular file")
    content = _ok(_git(data_root, "cat-file", "blob", oid), HeadStateError, file)
    try:
        return run_state.parse(content).round
    except (run_state.InvalidStateError, run_state.UnsupportedVersionError) as e:
        raise HeadStateError(f"{file} in HEAD: {e}") from None


def _keys(data_root, run_id, prefix):
    try:
        record = instance.read(data_root, run_id)
    except (
        instance.MissingInstanceError,
        instance.InvalidInstanceError,
        instance.UnsupportedVersionError,
        OSError,
    ) as e:
        raise NoKeyDirectoryError(f"no key directory for the case files: {e}") from e
    if record.op_signature is None:
        raise NoKeyDirectoryError(
            f"no key directory for the case files: {prefix}instance.json states no op_signature"
        )
    return record.hw_profile_key, record.op_signature.key


def _git(data_root, *args, index=None, input=None):
    env = {name: value for name, value in os.environ.items() if name not in _LOCATING}
    env["GIT_OPTIONAL_LOCKS"] = "0"
    if index is not None:
        env["GIT_INDEX_FILE"] = index
    feed = {"stdin": subprocess.DEVNULL} if input is None else {"input": input}
    command = [GIT, "--literal-pathspecs", "-C", os.fspath(data_root), *args]
    try:
        return subprocess.run(
            command, capture_output=True, env=env, check=False, **feed
        )
    except OSError as e:
        raise GitNotRunError(f"git could not be run: {type(e).__name__}: {e}") from e


def _ok(done, error, what):
    if done.returncode:
        said = " ".join(done.stderr.decode("utf-8", "replace").split())[:400]
        raise error(f"{what}: git failed with status {done.returncode}: {said}")
    return done.stdout


def _paths(output):
    return [os.fsdecode(path) for path in output.split(b"\0") if path]


def _entries(output):
    for record in output.split(b"\0"):
        if record:
            info, path = record.split(b"\t", 1)
            mode, kind, oid = info.decode().split(" ")
            yield os.fsdecode(path), mode, kind, oid


def _is_file(data_root, path):
    try:
        return not stat.S_ISDIR(os.lstat(Path(data_root) / path).st_mode)
    except OSError:
        return False
