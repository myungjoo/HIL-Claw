"""The scratch of a coder call: its creation with the copy of the spec, and its removal.

``ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`` decision 3
fixes that each coder call has one scratch directory of its own, new for that
call, outside both checkouts and inside neither's ``.git/``; decision 4 that
what is placed in it before the call is a copy of the bytes of the spec file of
the call, never a link of any kind, and that any further kind of file is a
later record's; P4 that its removal follows no symbolic link.
``ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`` decision 5 adds
that what is copied in is never placed in the place (the entry ``output``
directly below the scratch root). :func:`create` is slice (a) of ADR-0049 and
:func:`remove` slice (c). :func:`hilclaw.coder_call.call` calls them.

Conventions of this module, which are not rules of the records:

- Every path argument is a ``str`` or an :class:`os.PathLike` of ``str``
  without a NUL character. "Outside both checkouts" is checked by
  :mod:`hilclaw.checkout_boundary` on real paths, compared as
  :func:`os.path.normcase` folds them, against the directory that holds this
  package and the directories of ``keep_out``: the module knows no other
  checkout, so the caller names the data root in ``keep_out``.
- The scratch is made by :func:`tempfile.mkdtemp`, with the permissions it
  gives, under ``parent`` (by default the temporary directory of the system),
  with the name prefix :data:`PREFIX`. Its path is returned as a ``str``.
- The copy is the regular file :data:`SPEC_COPY_NAME` directly below the
  scratch root. That name is a convention of this code, not of a record; the
  coder process is pointed at the copy by that relative name (ADR-0126
  decision 5). The source is read whole, without following a link, before
  the scratch is made; its bytes are not parsed, checked or changed, and no
  mode bit or time is carried over.
- A failure after the scratch was made removes the scratch, and the original
  exception arrives.
- :func:`remove` removes the scratch and everything below it with
  :func:`shutil.rmtree`, which removes a symbolic link or a junction met
  below the root as a name and never descends into it. Where
  ``shutil.rmtree.avoids_symlink_attacks`` is false (Windows), a name swapped
  for a link during the removal is a race this module does not close; after
  P4 no process of the call is expected to be running (ADR-0049 decision 4,
  not verified - L1). A removal that fails is tried again a few times within
  about two seconds (a file handle can outlive a process on Windows); before
  each retry, every directory below the root reached without following a
  link is given the owner's read, write and search permission and, on
  Windows, every regular file loses its read-only attribute (a coder can
  ``chmod`` what it made). That step checks each directory with
  :func:`os.lstat` and then changes it by its path, so on every platform a
  directory swapped for a link in between gives the link's target those
  owner bits: the same race, not closed either.
- What is raised: :class:`InvalidScratchArgumentError` for an argument that
  cannot be what it stands for, :class:`TypeError` for a ``keep_out`` given
  as one path, :class:`ScratchError` for a source that cannot be copied, and
  the :class:`OSError` of making the scratch or writing the copy, with the
  system's own text, which may name a path. The texts of the module's own
  exceptions hold no path.

What this module does not do: no container (slice (d)); no bring-in (slice
(b), :mod:`hilclaw.bring_in`); no moment of removal, which is the caller's;
nothing about a scratch left by a dead process or one whose removal failed
(ADR-0049 sub-question ㉝ (나)): :func:`remove` only reports whether the
scratch is gone; no bound on the size of a scratch (L7); no check of what a
coder writes. It logs and writes nothing else.
"""

import contextlib
import errno
import os
import shutil
import stat
import tempfile
import time

from hilclaw import checkout_boundary as _checkout_boundary

SPEC_COPY_NAME = "spec.json"
PREFIX = "hilclaw-coder-"

SPEC_UNREADABLE = "spec_unreadable"
SPEC_NOT_REGULAR_FILE = "spec_not_regular_file"
SPEC_CHANGED = "spec_changed"
SCRATCH_FAILURES = (SPEC_UNREADABLE, SPEC_NOT_REGULAR_FILE, SPEC_CHANGED)

_JUNCTION_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)
_REMOVE_PAUSES_S = (0.0, 0.2, 0.6, 1.2)
_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_BINARY", 0)
)
_WRITE_FLAGS = (
    os.O_WRONLY
    | os.O_CREAT
    | os.O_EXCL
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_BINARY", 0)
)
_LINK_ERRNOS = frozenset(
    (errno.ELOOP, errno.EMLINK, getattr(errno, "EFTYPE", errno.ELOOP))
)


class InvalidScratchArgumentError(ValueError):
    """An argument cannot be what it stands for; nothing was made or removed."""


class ScratchError(Exception):
    """The spec file cannot be copied; ``failure`` is one of :data:`SCRATCH_FAILURES`."""

    def __init__(self, failure):
        super().__init__(failure)
        self.failure = failure


def create(spec_path, *, parent=None, keep_out=()):
    """Make a new scratch holding a copy of the bytes of ``spec_path``; return its path.

    ``parent`` is the existing directory the scratch is made in (``None``: the
    temporary directory of the system); it must not be or lie inside the
    directory that holds this package or a directory of the sequence
    ``keep_out``. ``spec_path`` must be, per :func:`os.lstat`, a regular file;
    its bytes become the new file :data:`SPEC_COPY_NAME` directly below the
    scratch root, and nothing else is placed.

    Raises :class:`InvalidScratchArgumentError` for a path argument of the
    wrong type or with a NUL character, or a ``parent`` inside a checkout;
    :class:`TypeError` for a ``keep_out`` that is one path;
    :class:`ScratchError` with :data:`SPEC_UNREADABLE` (a missing or unreadable
    source), :data:`SPEC_NOT_REGULAR_FILE` or :data:`SPEC_CHANGED` (the opened
    file is not the one examined). Nothing is made then. The :class:`OSError`
    of making the scratch or writing the copy is raised as it is, after the
    scratch was removed.
    """
    source = _checked_path("spec_path", spec_path)
    place = _refuse_inside_checkout(
        tempfile.gettempdir() if parent is None else parent,
        keep_out,
        argument="parent",
        containing=False,
    )
    data = _read_source(source)
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    try:
        _write_new(os.path.join(directory, SPEC_COPY_NAME), data)
    except BaseException:
        _remove(directory)
        raise
    return directory


def remove(scratch, *, keep_out=()):
    """Remove ``scratch`` and everything below it, following no link; return whether it is gone.

    ``scratch`` must be, per :func:`os.lstat`, a directory - not a symbolic
    link and not a junction - whose real path neither is, contains nor lies
    inside the directory that holds this package or a directory of the
    sequence ``keep_out``. Returns ``True`` when ``scratch`` no longer exists
    afterwards and ``False`` otherwise; a failure of the removal raises
    nothing.

    Raises :class:`InvalidScratchArgumentError` for an argument of the wrong
    type or with a NUL character, a ``scratch`` that does not exist, cannot
    be examined or is no directory, or one that meets a checkout as above;
    :class:`TypeError` for a ``keep_out`` that is one path. Nothing is
    removed then.
    """
    path = _checked_path("scratch", scratch)
    try:
        examined = os.lstat(path)
    except FileNotFoundError as error:
        raise InvalidScratchArgumentError("scratch: does not exist") from error
    except OSError as error:
        raise InvalidScratchArgumentError("scratch: cannot be examined") from error
    if not _is_plain_directory(examined):
        raise InvalidScratchArgumentError(
            "scratch: must be a directory, not a link, a junction or a file"
        )
    _refuse_inside_checkout(path, keep_out, argument="scratch", containing=True)
    return _remove(path)


def _checked_path(argument, value):
    try:
        text = os.fspath(value)
    except TypeError:
        text = None
    if type(text) is not str or "\0" in text:
        raise InvalidScratchArgumentError(
            f"{argument}: must be a str or an os.PathLike of str without a NUL character, "
            f"got {type(value).__name__}"
        )
    return text


def _refuse_inside_checkout(path, keep_out, *, argument, containing):
    _checkout_boundary.refuse_one_path(keep_out)
    roots = [_checked_path("keep_out", root) for root in keep_out]
    real = os.path.realpath(_checked_path(argument, path))
    if _checkout_boundary.meets_checkout(real, roots, containing=containing):
        raise InvalidScratchArgumentError(
            f"{argument}: must not be or lie inside a checkout"
            + (", nor contain one" if containing else "")
        )
    return real


def _is_plain_directory(examined):
    return (
        stat.S_ISDIR(examined.st_mode)
        and getattr(examined, "st_reparse_tag", 0) != _JUNCTION_TAG
    )


def _read_source(source):
    try:
        examined = os.lstat(source)
    except OSError as error:
        raise ScratchError(SPEC_UNREADABLE) from error
    if not stat.S_ISREG(examined.st_mode):
        raise ScratchError(SPEC_NOT_REGULAR_FILE)
    try:
        descriptor = os.open(source, _READ_FLAGS)
    except OSError as error:
        failure = SPEC_CHANGED if error.errno in _LINK_ERRNOS else SPEC_UNREADABLE
        raise ScratchError(failure) from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != examined.st_dev
            or opened.st_ino != examined.st_ino
        ):
            raise ScratchError(SPEC_CHANGED)
        chunks = []
        while chunk := os.read(descriptor, 65536):
            chunks.append(chunk)
    except OSError as error:
        raise ScratchError(SPEC_UNREADABLE) from error
    finally:
        os.close(descriptor)
    return b"".join(chunks)


def _write_new(path, data):
    descriptor = os.open(path, _WRITE_FLAGS, 0o666)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view) :]
    finally:
        os.close(descriptor)


def _remove(directory):
    for attempt, pause in enumerate(_REMOVE_PAUSES_S):
        time.sleep(pause)
        if attempt:
            _make_writable(directory)
        shutil.rmtree(directory, ignore_errors=True)
        if not os.path.lexists(directory):
            return True
    return False


def _make_writable(top):
    pending = [top]
    while pending:
        directory = pending.pop()
        try:
            examined = os.lstat(directory)
            if not _is_plain_directory(examined):
                continue
            os.chmod(directory, stat.S_IMODE(examined.st_mode) | stat.S_IRWXU)
            names = os.listdir(directory)
        except OSError:
            continue
        for name in names:
            path = os.path.join(directory, name)
            try:
                found = os.lstat(path)
            except OSError:
                continue
            if stat.S_ISDIR(found.st_mode):
                pending.append(path)
            elif os.name == "nt" and stat.S_ISREG(found.st_mode):
                with contextlib.suppress(OSError):
                    os.chmod(path, stat.S_IMODE(found.st_mode) | stat.S_IWRITE)
