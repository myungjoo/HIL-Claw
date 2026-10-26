"""The copies of a first-case build into its build directory (ADR-0144 slice (2)).

``ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md``
decision 2, Q3, decides that what a build in a container needs crosses into
the build directory by copy, before the build and on the host: copies with
their own bytes, never a link, of the kernel files the reader of ADR-0055 found
at that call (the compiled set and the kernel's own headers, R2, R3 and R5)
and of the harness program of the build. The kernel's copies lie in a
sub-directory of the build directory that holds nothing else, and the harness
program's copy beside it, so that a kernel file named like the harness program
is a second file and never a replacement of it. :func:`place_copies` is that
slice. It is bound to no tool and no backend operation; nothing calls it yet.

:func:`place_harness_copy` copies one further harness program beside the
first, as the waiter's source of ADR-0145 decision 3 is copied with the timing
driver (ADR-0170).

Conventions of this module, which are not rules of the record:

- The kernel sub-directory is :data:`KERNEL_DIR` directly below the build
  directory and each kernel copy keeps its listed name. The harness copy is
  the basename of the harness program directly below the build directory.
- Every source is read whole before anything is written, without following a
  link: :func:`os.lstat` shows a regular file, the open uses ``O_NOFOLLOW``
  where the platform has it, and :func:`os.fstat` of the open file shows a
  regular file of the same device and inode. Each copy is a new regular file
  made with ``O_CREAT | O_EXCL``, holding the bytes read and nothing carried
  over: no mode bit, owner or time. The sub-directory is made new with
  :func:`os.mkdir`; nothing already at a name is reused or written through.
- A failure to copy raises :class:`CopyError`, whose ``failure`` is one of
  :data:`COPY_FAILURES`, whose text is that value alone and whose
  ``__cause__`` is the original error where there is one. A failure of reading
  writes nothing. A failure of making the sub-directory or of writing a copy
  (:data:`ENTRY_EXISTS`, :data:`COPY_UNWRITABLE`) leaves what was already
  written in place: the caller removes the whole build directory, as ADR-0056
  decision 4 and ADR-0144 Q4 say. :data:`ENTRY_EXISTS` is the
  :class:`FileExistsError` of the system; where the system reports a name
  taken otherwise (on Windows, a directory at the name of a file copy usually
  gives :class:`PermissionError`), the answer is :data:`COPY_UNWRITABLE`.

What this module does not decide or do: the failure kinds and rows a tool
answers for its failures and for "no kernel source" (ADR-0144 decision 7,
ADR-0056 decision 5, ADR-0060 decision 4), so each reaches the caller as a
plain fact; the making and the removal of the build directory (ADR-0056
decision 4, ADR-0144 Q4); the name of the executable; the in-container path
and the order of the sources of a build. It writes nothing outside the build
directory, starts no program, reads no environment variable and no
configuration of its own, and bounds neither the number nor the size of the
copies (R7; ADR-0144 Q7).
"""

import contextlib
import errno
import os
import stat
from typing import NamedTuple

from hilclaw import kernel_source

KERNEL_DIR = "kernel"

KERNEL_FILE_UNREADABLE = "kernel_file_unreadable"
KERNEL_FILE_CHANGED = "kernel_file_changed"
HARNESS_UNREADABLE = "harness_unreadable"
HARNESS_NOT_REGULAR_FILE = "harness_not_regular_file"
HARNESS_CHANGED = "harness_changed"
ENTRY_EXISTS = "entry_exists"
COPY_UNWRITABLE = "copy_unwritable"
COPY_FAILURES = (
    KERNEL_FILE_UNREADABLE,
    KERNEL_FILE_CHANGED,
    HARNESS_UNREADABLE,
    HARNESS_NOT_REGULAR_FILE,
    HARNESS_CHANGED,
    ENTRY_EXISTS,
    COPY_UNWRITABLE,
)

_JUNCTION_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)
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


class Copies(NamedTuple):
    """Answer of :func:`place_copies`.

    Each path is relative to the build directory, in POSIX form (``/``
    separators). ``compiled_set`` holds the copies of the compiled set in the
    reader's order (R3), for example ``kernel/gemm.c``; ``headers`` those of
    the kernel's own headers in the same order; ``harness`` the copy of the
    harness program. When the reader answered "no kernel source", ``missing``
    is its value unchanged (one of
    :data:`hilclaw.kernel_source.NO_KERNEL_SOURCE_CASES`), both tuples are
    empty and ``harness`` is ``None``; otherwise ``missing`` is ``None``.
    """

    compiled_set: tuple[str, ...]
    headers: tuple[str, ...]
    harness: str | None
    missing: str | None


class CopyError(Exception):
    """A copy could not be made; ``failure`` is one of :data:`COPY_FAILURES`."""

    def __init__(self, failure):
        super().__init__(failure)
        self.failure = failure


def place_copies(output_path, harness_program, build_dir):
    """Copy the kernel files of ``output_path`` and ``harness_program`` into ``build_dir``.

    Applies :func:`hilclaw.kernel_source.read_compiled_set` to ``output_path``
    once. For "no kernel source" it creates and writes nothing and returns a
    :class:`Copies` carrying the reader's ``missing``. Otherwise it reads every
    file of the compiled set and every header the reader answered and the
    harness program, then makes :data:`KERNEL_DIR` below ``build_dir``, writes
    there a copy of each kernel file under its listed name, writes the copy of
    the harness program directly into ``build_dir`` under its basename, and
    returns the relative paths of the copies.

    Raised before the file system is looked at, each a :class:`TypeError` or
    :class:`ValueError` with an attribute ``parameter`` naming the argument: a
    ``harness_program`` or ``build_dir`` that is not a ``str`` or an
    :class:`os.PathLike` of ``str`` or holds NUL; a ``build_dir`` that is not
    absolute; a ``harness_program`` whose basename is empty, ``.``, ``..`` or
    :data:`KERNEL_DIR` in any case. Then the :class:`OSError` of
    :func:`os.lstat` on ``build_dir`` unchanged, or :class:`NotADirectoryError`
    where ``build_dir`` is not itself a directory (a symbolic link or a
    junction is not). Then, from the reader and unchanged,
    :class:`hilclaw.kernel_source.InvalidOutputPathError` and
    :class:`hilclaw.kernel_source.KernelSourceReadError`. Then
    :class:`CopyError`: the reading failures before anything is written, and
    :data:`ENTRY_EXISTS` or :data:`COPY_UNWRITABLE` for the
    :class:`OSError` of making the sub-directory or writing a copy, wrapped,
    with what was written before it left in place.
    """
    harness_program, harness_name, build_dir = _check(harness_program, build_dir)
    _check_build_directory(build_dir)
    answer = kernel_source.read_compiled_set(output_path)
    if answer.missing is not None:
        return Copies((), (), None, answer.missing)
    harness = _read(harness_program, harness=True)
    kernel = [
        (path.name, _read(path, harness=False))
        for path in answer.compiled_set + answer.headers
    ]
    kernel_dir = os.path.join(build_dir, KERNEL_DIR)
    with _writing():
        os.mkdir(kernel_dir)
        for name, data in kernel:
            _write_new(os.path.join(kernel_dir, name), data)
        _write_new(os.path.join(build_dir, harness_name), harness)
    return Copies(
        tuple(f"{KERNEL_DIR}/{path.name}" for path in answer.compiled_set),
        tuple(f"{KERNEL_DIR}/{path.name}" for path in answer.headers),
        harness_name,
        None,
    )


def place_harness_copy(harness_program, build_dir):
    """Copy one further ``harness_program`` directly into ``build_dir``; return its name.

    For a build directory that :func:`place_copies` has filled. The copy is
    made as that function makes the copy of its harness program, under the
    basename of ``harness_program``, which is returned. Raises, as
    :func:`place_copies` does: :class:`TypeError` or :class:`ValueError` with
    ``parameter`` for the arguments; :class:`CopyError` with a reading
    failure of a harness program before anything is written; and
    :class:`CopyError` :data:`ENTRY_EXISTS` or :data:`COPY_UNWRITABLE` for the
    write, an entry already at that name included. ``build_dir`` itself is
    not examined again.
    """
    harness_program, harness_name, build_dir = _check(harness_program, build_dir)
    harness = _read(harness_program, harness=True)
    with _writing():
        _write_new(os.path.join(build_dir, harness_name), harness)
    return harness_name


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise


def _check(harness_program, build_dir):
    with _parameter("harness_program"):
        harness = _path_text(harness_program, "harness_program")
        name = os.path.basename(harness)
        if name in ("", ".", "..") or name.casefold() == KERNEL_DIR:
            raise ValueError(
                f"harness_program must have a file name other than {KERNEL_DIR}"
            )
    with _parameter("build_dir"):
        directory = _path_text(build_dir, "build_dir")
        if not os.path.isabs(directory):
            raise ValueError("build_dir must be absolute")
    return harness, name, directory


def _path_text(value, what):
    if not isinstance(value, (str, os.PathLike)):
        raise TypeError(
            f"{what} must be str or os.PathLike, not {type(value).__name__}"
        )
    text = os.fspath(value)
    if not isinstance(text, str):
        raise TypeError(f"{what} must be a str path, not bytes")
    if "\0" in text:
        raise ValueError(f"{what} contains a NUL character")
    return text


def _check_build_directory(build_dir):
    examined = os.lstat(build_dir)
    if (
        not stat.S_ISDIR(examined.st_mode)
        or getattr(examined, "st_reparse_tag", 0) == _JUNCTION_TAG
    ):
        raise NotADirectoryError(errno.ENOTDIR, "build_dir is not itself a directory")


def _read(source, *, harness):
    unreadable = HARNESS_UNREADABLE if harness else KERNEL_FILE_UNREADABLE
    changed = HARNESS_CHANGED if harness else KERNEL_FILE_CHANGED
    try:
        examined = os.lstat(source)
    except OSError as error:
        raise CopyError(unreadable) from error
    if not stat.S_ISREG(examined.st_mode):
        raise CopyError(HARNESS_NOT_REGULAR_FILE if harness else changed)
    try:
        descriptor = os.open(source, _READ_FLAGS)
    except OSError as error:
        raise CopyError(
            changed if error.errno in _LINK_ERRNOS else unreadable
        ) from error
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != examined.st_dev
            or opened.st_ino != examined.st_ino
        ):
            raise CopyError(changed)
        chunks = []
        while chunk := os.read(descriptor, 65536):
            chunks.append(chunk)
    except OSError as error:
        raise CopyError(unreadable) from error
    finally:
        os.close(descriptor)
    return b"".join(chunks)


@contextlib.contextmanager
def _writing():
    try:
        yield
    except FileExistsError as error:
        raise CopyError(ENTRY_EXISTS) from error
    except OSError as error:
        raise CopyError(COPY_UNWRITABLE) from error


def _write_new(path, data):
    descriptor = os.open(path, _WRITE_FLAGS, 0o666)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view) :]
    finally:
        os.close(descriptor)
