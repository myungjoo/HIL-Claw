"""The kernel source of an attempt, read from its ``output/`` (ADR-0055).

``ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`` is the rule:
decision 5 (N1, N2) fixes which file names are admitted and decision 3 (R1 to
R8) fixes how a reader goes from the path of the ``output/`` of an attempt to
the compiled set. :func:`is_admitted_name` is the first and
:func:`read_compiled_set` the second. Who applies the reader, and to which
path, is ADR-0056 decision 3: the operation of a backend that builds, to the
path the tool function forms with :func:`hilclaw.layout.attempt_artefact`.
Nothing calls this module yet.

:func:`read_compiled_set` has three outcomes. It returns a
:class:`KernelSource` whose ``compiled_set`` is not empty and whose ``missing``
is ``None``; or one whose ``compiled_set`` is empty and whose ``missing`` is one
of :data:`NO_KERNEL_SOURCE_CASES` ("no kernel source", R1 and R4); or it raises
:class:`KernelSourceReadError`, whose ``failure`` is one of
:data:`READER_FAILURES` (R8). The reader lists the attempt directory and
``output/`` and determines the kind of every entry of both; the answer depends
on listed names and kinds alone, never on the order of a listing, on the case
sensitivity of the file system or on a normalisation.

Conventions of this module, which are not rules of the record:

- The path is a ``str`` or an :class:`os.PathLike` of ``str`` and is used as
  :class:`pathlib.Path` holds it: not resolved, not made absolute, a trailing
  separator and ``.`` components dropped. A value of another type, a path that
  holds a NUL character, and a path whose last component is not exactly
  ``output``, is a mistake of the caller and raises
  :class:`InvalidOutputPathError`; it is not "no kernel source".
- The attempt directory is whatever the system lists at the parent of the
  path, so an attempt directory that is a symbolic link to a directory counts
  as a directory: the reader cannot tell it from a link in any component above
  it (a data root below a linked home or temporary directory), and R1 denies a
  link only for the entry ``output`` and R2 for a kernel file.
- A listing of the attempt path that fails because nothing is there or because
  it is not a directory is "no kernel source"; any other error of that
  listing, every error of the listing of ``output/`` and every error of asking
  for the kind of an entry is a failure, also where the error leaves open
  whether the directory exists. The original error is the ``__cause__``.
- The text of a :class:`KernelSourceReadError` is its ``failure`` and nothing
  else: no path, no name of an entry and no text of the system's error.
- :func:`is_admitted_name` answers ``False`` for a value that is not exactly a
  ``str``; it raises nothing.

What this module does not do: it opens, reads, executes, writes, creates and
removes nothing, and asks for no size (R6, R7); it judges no content (L2); it
applies no bound on the number or size of files, which are rules of the
bring-in (B2, B3); it brings nothing in; it builds nothing and knows no
compiler or flag; it does not tell a finished bring-in from an unfinished one
(L5); and it raises no tool failure and names no kind of one (ADR-0056
decision 6 maps the outcomes to kinds, at the operation). The two listings and
the questions for kinds are separate calls of the system, not one snapshot.
"""

import os
import re
import stat
from pathlib import Path
from typing import NamedTuple

OUTPUT_NAME = "output"

NO_ATTEMPT_DIRECTORY = "no_attempt_directory"
NO_OUTPUT_DIRECTORY = "no_output_directory"
NO_COMPILED_FILE = "no_compiled_file"
NO_KERNEL_SOURCE_CASES = (NO_ATTEMPT_DIRECTORY, NO_OUTPUT_DIRECTORY, NO_COMPILED_FILE)

ATTEMPT_DIRECTORY_UNLISTABLE = "attempt_directory_unlistable"
OUTPUT_DIRECTORY_UNLISTABLE = "output_directory_unlistable"
ENTRY_KIND_UNDETERMINED = "entry_kind_undetermined"
READER_FAILURES = (
    ATTEMPT_DIRECTORY_UNLISTABLE,
    OUTPUT_DIRECTORY_UNLISTABLE,
    ENTRY_KIND_UNDETERMINED,
)

_ADMITTED = re.compile(r"[a-z0-9][a-z0-9_-]{0,61}\.[ch]")
_RESERVED_STEMS = frozenset(
    ("con", "prn", "aux", "nul")
    + tuple(f"{device}{number}" for device in ("com", "lpt") for number in range(1, 10))
)


class KernelSource(NamedTuple):
    """Answer of :func:`read_compiled_set`.

    ``compiled_set`` holds the paths of the kernel files whose name ends in
    ``.c``, each the given path joined with the listed name, in ascending byte
    order of the names (R3). ``missing`` is ``None`` when the set is not empty,
    else the one of :data:`NO_KERNEL_SOURCE_CASES` that says why it is empty.
    """

    compiled_set: tuple[Path, ...]
    missing: str | None


class InvalidOutputPathError(ValueError):
    """The value given as the path of an ``output/`` cannot be one; nothing was looked at."""


class KernelSourceReadError(Exception):
    """The reader could not see what it has to see (R8); ``failure`` is one of :data:`READER_FAILURES`."""

    def __init__(self, failure):
        super().__init__(failure)
        self.failure = failure


def is_admitted_name(name):
    """Return whether ``name`` is an admitted file name (ADR-0055 decision 5).

    N1: it matches ``[a-z0-9][a-z0-9_-]{0,61}\\.[ch]`` in full. N2: the part
    before the dot is none of ``con``, ``prn``, ``aux``, ``nul``, ``com1`` to
    ``com9`` and ``lpt1`` to ``lpt9``. Only the name is judged, never a file.
    """
    if type(name) is not str or not _ADMITTED.fullmatch(name):
        return False
    return name[:-2] not in _RESERVED_STEMS


def read_compiled_set(output_path):
    """Apply the reader of ADR-0055 decision 3 to the path of an ``output/``.

    Returns a :class:`KernelSource`. The ``output/`` is the entry of the parent
    of ``output_path`` that is listed as exactly ``output`` and is itself a
    directory (R1); its kernel files are the entries directly below it that
    are themselves regular files under an admitted name (R2), and those whose
    name ends in ``.c`` are the compiled set (R3). A symbolic link is neither.

    Raises :class:`InvalidOutputPathError` for a value that is no path of an
    ``output/`` and :class:`KernelSourceReadError` for a failure of the reader.
    """
    output = _checked_output_path(output_path)
    try:
        listed = os.listdir(output.parent)
    except (FileNotFoundError, NotADirectoryError):
        return KernelSource((), NO_ATTEMPT_DIRECTORY)
    except OSError as error:
        raise KernelSourceReadError(ATTEMPT_DIRECTORY_UNLISTABLE) from error
    if not stat.S_ISDIR(_modes(output.parent, listed).get(OUTPUT_NAME, 0)):
        return KernelSource((), NO_OUTPUT_DIRECTORY)
    try:
        listed = os.listdir(output)
    except OSError as error:
        raise KernelSourceReadError(OUTPUT_DIRECTORY_UNLISTABLE) from error
    names = sorted(
        name
        for name, mode in _modes(output, listed).items()
        if stat.S_ISREG(mode) and name.endswith(".c") and is_admitted_name(name)
    )
    return KernelSource(
        tuple(output / name for name in names), None if names else NO_COMPILED_FILE
    )


def _checked_output_path(value):
    try:
        text = os.fspath(value)
    except TypeError:
        text = None
    if type(text) is not str or "\0" in text:
        raise InvalidOutputPathError(
            "output_path: must be a str or an os.PathLike of str without a NUL character, "
            f"got {type(value).__name__}"
        )
    path = Path(text)
    if path.name != OUTPUT_NAME:
        raise InvalidOutputPathError(
            f"output_path: the last component must be {OUTPUT_NAME}"
        )
    return path


def _modes(directory, names):
    modes = {}
    for name in names:
        try:
            modes[name] = os.lstat(os.path.join(directory, name)).st_mode
        except OSError as error:
            raise KernelSourceReadError(ENTRY_KIND_UNDETERMINED) from error
    return modes
