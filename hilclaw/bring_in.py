"""The bring-in of a coder call: admitted files of a scratch into the ``output/`` of an attempt.

``ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`` decision 5 (B1
to B6, with the admitted names N1 and N2 of :mod:`hilclaw.kernel_source`) is
the rule; ``ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md``
decision 4 fixes that the bring-in reads regular files below the scratch only,
follows no symbolic link, executes nothing and writes only below the
``output/`` of the attempt. :func:`bring_in` is that function, slice (b) of
ADR-0049. Nothing calls it yet.

Conventions of this module, which are not rules of the records:

- Both paths are a ``str`` or an :class:`os.PathLike` of ``str`` without a NUL
  character and are used as :class:`pathlib.Path` holds them. The last
  component of ``output_path`` is exactly ``output``, as
  :func:`hilclaw.layout.attempt_artefact` forms it. A scratch root that is a
  symbolic link to a directory counts as a directory, as the attempt directory
  does for the reader; the place itself never does (B1).
- It is only the bring-in of ADR-0055's scope, into an ``output/`` that did not
  exist before it. It refuses with :class:`OutputExistsError` when the attempt
  directory lists an entry ``output`` of any kind, before anything below the
  scratch is read, and again when the creation of ``output/`` finds the name
  taken. This decides nothing about what a bring-in does then.
- Only an entry of the place whose listed name is admitted has its kind asked
  for; every other name is passed over unexamined.
- A failure to see what has to be seen raises :class:`BringInError` before
  ``output/`` is created; its ``failure`` is one of :data:`BRING_IN_FAILURES`,
  its text is that value alone and its ``__cause__`` the original error.
- Each file is created with ``os.open`` and ``O_CREAT | O_EXCL`` in the
  ``output/`` this call has just created, not with
  :func:`hilclaw.once_write.write_once`: the exclusive creation already never
  replaces or writes through an entry, and it needs no hard link and leaves no
  temporary name. Any :class:`OSError` of creating ``output/`` or its parents
  (other than the name taken) or of writing a file is raised as it is, and the
  files written before it stay.

What this module does not do: it judges no content (L2); it reports nothing
that was not taken and writes no record of it (OD-23 sub-question ① (나));
it handles no existing ``output/`` (① (가)); it does not tell a
finished bring-in from one that died part-way, which looks the same (L5); it
knows nothing of containers, of the moment of the call or of a call that did
not end normally (OD-19); and it creates, writes and removes no scratch
(ADR-0049 slices (a) and (c)).
"""

import errno
import os
import stat
from pathlib import Path

from hilclaw import checkout_boundary as _checkout_boundary
from hilclaw.kernel_source import OUTPUT_NAME, is_admitted_name

MAX_FILES = 16  # ADR-0055 decision 6: provisional value of the record.
MAX_FILE_BYTES = 262_144  # ADR-0055 decision 6: provisional value of the record.

ATTEMPT_DIRECTORY_UNLISTABLE = "attempt_directory_unlistable"
SCRATCH_ROOT_UNLISTABLE = "scratch_root_unlistable"
PLACE_UNLISTABLE = "place_unlistable"
ENTRY_KIND_UNDETERMINED = "entry_kind_undetermined"
CANDIDATE_UNREADABLE = "candidate_unreadable"
BRING_IN_FAILURES = (
    ATTEMPT_DIRECTORY_UNLISTABLE,
    SCRATCH_ROOT_UNLISTABLE,
    PLACE_UNLISTABLE,
    ENTRY_KIND_UNDETERMINED,
    CANDIDATE_UNREADABLE,
)

_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_BINARY", 0)
)
_LINK_ERRNOS = frozenset(
    (errno.ELOOP, errno.EMLINK, getattr(errno, "EFTYPE", errno.ELOOP))
)
_WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)


class InvalidBringInArgumentError(ValueError):
    """An argument cannot be what it stands for; nothing was read or written."""


class OutputExistsError(Exception):
    """The attempt already has an entry ``output``; this bring-in takes nothing into it.

    Only a bring-in into an ``output/`` that did not exist is this module's
    (ADR-0055 decision 1); what a bring-in does otherwise is not decided
    (OD-23 sub-question ① (가)), and this refusal decides nothing about it.
    """


class BringInError(Exception):
    """The bring-in could not see what it has to see; ``failure`` is one of :data:`BRING_IN_FAILURES`."""

    def __init__(self, failure):
        super().__init__(failure)
        self.failure = failure


def bring_in(scratch_root, output_path):
    """Bring the admitted regular files of the place of ``scratch_root`` into ``output_path``.

    The place is the entry of the scratch root listed as exactly ``output``
    that is itself a directory (B1). An entry directly below it is a candidate
    when it is itself a regular file under an admitted name of at most
    :data:`MAX_FILE_BYTES` bytes (B2). More than :data:`MAX_FILES` candidates
    take nothing (B3). Each candidate is read without following a link and
    taken unless it is no longer the file that was examined or yields more
    than :data:`MAX_FILE_BYTES` bytes; it becomes a new file of the same name
    and bytes below ``output_path``, with no attribute carried over (B4). The
    scratch is never changed (B5), and ``output_path`` and its missing parents
    are created only when a file is taken (B6), after every read.

    Returns the names taken, in ascending byte order; ``()`` when none is.

    Raises :class:`InvalidBringInArgumentError` for an argument of the wrong
    type, with a NUL character, an ``output_path`` whose last component is not
    ``output``, or two paths of which, resolved, one is or lies inside the
    other; :class:`OutputExistsError` when the attempt has an entry ``output``;
    :class:`BringInError` when the attempt directory (other than missing), the
    scratch root (missing included) or the place cannot be listed, the kind of
    an admitted entry cannot be determined or a candidate cannot be read; and
    the :class:`OSError` of creating ``output_path`` or writing a file, after
    which the files already written stay.
    """
    scratch = _checked_path("scratch_root", scratch_root)
    output = _checked_path("output_path", output_path)
    if output.name != OUTPUT_NAME:
        raise InvalidBringInArgumentError(
            f"output_path: the last component must be {OUTPUT_NAME}"
        )
    real_scratch = os.path.normcase(os.path.realpath(scratch))
    real_output = os.path.normcase(
        os.path.join(os.path.realpath(output.parent), OUTPUT_NAME)
    )
    if _checkout_boundary.within(
        real_scratch, real_output
    ) or _checkout_boundary.within(real_output, real_scratch):
        raise InvalidBringInArgumentError(
            "scratch_root and output_path: neither may be or lie inside the other"
        )
    _refuse_existing_output(output)
    taken = [(name, data) for name, data in _read_place(scratch) if data is not None]
    if not taken:
        return ()
    os.makedirs(output.parent, exist_ok=True)
    try:
        os.mkdir(output)
    except FileExistsError as error:
        raise OutputExistsError(OUTPUT_NAME) from error
    for name, data in taken:
        _write_new(output / name, data)
    return tuple(name for name, _ in taken)


def _checked_path(argument, value):
    try:
        text = os.fspath(value)
    except TypeError:
        text = None
    if type(text) is not str or "\0" in text:
        raise InvalidBringInArgumentError(
            f"{argument}: must be a str or an os.PathLike of str without a NUL character, "
            f"got {type(value).__name__}"
        )
    return Path(text)


def _refuse_existing_output(output):
    try:
        listed = os.listdir(output.parent)
    except (FileNotFoundError, NotADirectoryError):
        return
    except OSError as error:
        raise BringInError(ATTEMPT_DIRECTORY_UNLISTABLE) from error
    if OUTPUT_NAME in listed:
        raise OutputExistsError(OUTPUT_NAME)


def _read_place(scratch):
    try:
        listed = os.listdir(scratch)
    except OSError as error:
        raise BringInError(SCRATCH_ROOT_UNLISTABLE) from error
    if OUTPUT_NAME not in listed:
        return []
    place = scratch / OUTPUT_NAME
    if not stat.S_ISDIR(_lstat(place).st_mode):
        return []
    try:
        listed = os.listdir(place)
    except OSError as error:
        raise BringInError(PLACE_UNLISTABLE) from error
    candidates = []
    for name in sorted(name for name in listed if is_admitted_name(name)):
        examined = _lstat(place / name)
        if stat.S_ISREG(examined.st_mode) and examined.st_size <= MAX_FILE_BYTES:
            candidates.append((name, examined))
    if len(candidates) > MAX_FILES:
        return []
    return [(name, _read(place / name, examined)) for name, examined in candidates]


def _lstat(path):
    try:
        return os.lstat(path)
    except OSError as error:
        raise BringInError(ENTRY_KIND_UNDETERMINED) from error


def _read(path, examined):
    try:
        descriptor = os.open(path, _READ_FLAGS)
    except OSError as error:
        if error.errno in _LINK_ERRNOS:
            return None
        raise BringInError(CANDIDATE_UNREADABLE) from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != examined.st_dev
            or opened.st_ino != examined.st_ino
        ):
            return None
        chunks = []
        remaining = MAX_FILE_BYTES + 1
        while remaining > 0:
            chunk = os.read(descriptor, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
    except OSError as error:
        raise BringInError(CANDIDATE_UNREADABLE) from error
    finally:
        os.close(descriptor)
    data = b"".join(chunks)
    return data if len(data) <= MAX_FILE_BYTES else None


def _write_new(path, data):
    descriptor = os.open(path, _WRITE_FLAGS, 0o666)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view) :]
    finally:
        os.close(descriptor)
