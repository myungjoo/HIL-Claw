"""The kernel reference of one named attempt of a run, read for the model executor (ADR-0153 decision 3).

``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`` decision 3 says
what a kernel reference is: a kernel's source files with the
``task.contract`` of the spec it was written to and its build settings
(:class:`hilclaw.model_binding.KernelReference`). The records say where an
attempt holds the first two:

* the source files are the compiled set of the attempt's ``output/``
  (ADR-0055 decision 3, R1 to R8), read with
  :func:`hilclaw.kernel_source.read_compiled_set`; the kernel's own headers
  that the reader answers (R5) are in the reference's ``headers``;
* the spec is the attempt's ``coder/.../spec.json`` (ADR-0029 decisions 2 and
  3 with ADR-0051 decisions 1 to 3), read with
  :func:`hilclaw.spec_file.parse`; the file belongs to the attempt at its path
  only when ``final_name(data_root, parse(content)) == path``.

:func:`kernel_reference` applies both to the attempt its caller names. The
caller passes the build settings the attempt was built with, for example
:data:`hilclaw.standin_settings.FLAGS` for a ``cpu_standin`` run (ADR-0116
decision 2); this module reads no record of build settings and chooses none.
The caller also names the attempt, the call site and the shapes of a binding
entry: the reader chooses no kernel (ADR-0153 decision 3).

Outcomes of :func:`kernel_reference`, checked in this order:

* A malformed argument raises :class:`TypeError` or :class:`ValueError` with
  the attribute ``parameter``, the name of the argument, before anything is
  read. ``data_root`` that is not a ``str`` or an :class:`os.PathLike` of
  ``str`` is a :class:`TypeError`, one holding a NUL character a
  :class:`ValueError`. A ``run_id``, ``round``, ``candidate`` or ``attempt``
  that :mod:`hilclaw.layout` refuses raises its
  :class:`hilclaw.layout.InvalidPathValueError` (a :class:`ValueError`),
  passed through with ``parameter`` added; a ``bool`` or a negative number is
  among them. ``flags`` that is not a ``tuple`` or ``list`` of ``str`` is a
  :class:`TypeError`.
* Every other outcome but the answer raises :class:`AttemptKernelError`,
  whose ``reason`` is one of :data:`REASONS`; the original error, where one
  exists, is its ``__cause__``:

  - :data:`NO_SPEC_FILE`: nothing is at the path of the spec, or a component
    above it is no directory (the attempt directory is missing among them).
  - :data:`SPEC_UNREADABLE`: any other error of opening or reading the spec.
  - :data:`SPEC_INVALID`: :func:`hilclaw.spec_file.parse` refuses the content
    as invalid (:class:`hilclaw.spec_file.InvalidSpecFileError`).
  - :data:`SPEC_OTHER_VERSION`: the content is of another version than 2,
    version 1 among them (:class:`hilclaw.spec_file.UnsupportedVersionError`,
    ADR-0051 decision 3).
  - :data:`SPEC_OTHER_ATTEMPT`: the ``id`` of the document formats to another
    path than the one read, or to none
    (:class:`hilclaw.layout.InvalidPathValueError` of
    :func:`hilclaw.spec_file.final_name`).
  - one of :data:`hilclaw.kernel_source.NO_KERNEL_SOURCE_CASES`: the attempt
    has no kernel source (R1, R4). The spec is read first, so
    :data:`hilclaw.kernel_source.NO_ATTEMPT_DIRECTORY` comes only when the
    attempt directory is gone after the spec was read.
  - one of :data:`hilclaw.kernel_source.READER_FAILURES`: the reader of
    ADR-0055 failed (R8, :class:`hilclaw.kernel_source.KernelSourceReadError`).

* Otherwise it returns a :class:`hilclaw.model_binding.KernelReference`.

Conventions of this module, which are not rules of the records: the spec is
read before ``output/``, so an attempt that lacks both is
:data:`NO_SPEC_FILE`; the spec file is opened as the system resolves its
path; ``data_root`` is used as given, not resolved and not made absolute; the
text of an :class:`AttemptKernelError` is its ``reason`` and nothing else.

What this module does not do: it judges no attempt (no correctness or timing
result, no ``events.ndjson``, no ``eval/``, no ``best.json``) and chooses no
attempt for a call site (:mod:`hilclaw.model_run_binding` does, ADR-0189); it
checks no fit of the contract to a call site, which
:mod:`hilclaw.model_binding` does when the executor runs; it
reads no ``build.json`` or other record of build settings (OD-6); it writes
and creates nothing, reads no file of the run but the spec, lists nothing but
what the reader of ADR-0055 lists and walks no directory (ADR-0004 decision
3); and it is no tool and exposes no executor (OD-31, OD-18, OD-23).
"""

import contextlib
import os

from hilclaw import kernel_source, layout, spec_file
from hilclaw.model_binding import KernelReference

NO_SPEC_FILE = "no_spec_file"
SPEC_UNREADABLE = "spec_unreadable"
SPEC_INVALID = "spec_invalid"
SPEC_OTHER_VERSION = "spec_other_version"
SPEC_OTHER_ATTEMPT = "spec_other_attempt"
REASONS = (
    NO_SPEC_FILE,
    SPEC_UNREADABLE,
    SPEC_INVALID,
    SPEC_OTHER_VERSION,
    SPEC_OTHER_ATTEMPT,
    *kernel_source.NO_KERNEL_SOURCE_CASES,
    *kernel_source.READER_FAILURES,
)
"""Every ``reason`` of :class:`AttemptKernelError`, in the order of the checks."""


class AttemptKernelError(Exception):
    """The named attempt gives no kernel reference; ``reason`` is one of :data:`REASONS`."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def kernel_reference(data_root, run_id, round, candidate, attempt, *, flags):
    """Return the :class:`hilclaw.model_binding.KernelReference` of one attempt of a run.

    The attempt is ``round``, ``candidate`` and ``attempt`` of the run
    ``run_id`` below ``data_root`` (ADR-0004 decisions 2 and 3). The answer's
    ``sources`` is the compiled set of the attempt's ``output/`` in the order
    of R3; its ``contract`` is the ``task.contract`` of the attempt's spec as
    :func:`hilclaw.spec_file.parse` returns it; its ``flags`` is
    ``tuple(flags)``; its ``headers`` is the kernel's own headers of R5 in the
    reader's order. ``flags`` is required: the caller passes
    the settings the attempt was built with, for example
    :data:`hilclaw.standin_settings.FLAGS` for a ``cpu_standin`` run.

    Raises as the module docstring lists: :class:`TypeError` or
    :class:`ValueError` with ``parameter`` for a malformed argument, and
    :class:`AttemptKernelError` for an attempt that gives no reference.
    """
    with _parameter("data_root"):
        _check_data_root(data_root)
    with _parameter("run_id"):
        layout.check_run_id(run_id)
    with _parameter("round"):
        layout.round_dir(data_root, run_id, round)
    with _parameter("candidate"):
        layout.attempt_dir(data_root, run_id, round, "coder", candidate, 1)
    with _parameter("attempt"):
        spec_path = layout.attempt_artefact(
            data_root, run_id, round, candidate, attempt, "spec.json"
        )
    with _parameter("flags"):
        _check_flags(flags)
    contract = _contract(data_root, spec_path)
    output = layout.attempt_artefact(
        data_root, run_id, round, candidate, attempt, "output"
    )
    try:
        source = kernel_source.read_compiled_set(output)
    except kernel_source.KernelSourceReadError as error:
        raise AttemptKernelError(error.failure) from error
    if source.missing is not None:
        raise AttemptKernelError(source.missing)
    return KernelReference(
        tuple(source.compiled_set), contract, tuple(flags), tuple(source.headers)
    )


def _check_data_root(value):
    try:
        text = os.fspath(value)
    except TypeError:
        text = None
    if type(text) is not str:
        raise TypeError(
            "data_root must be a str or an os.PathLike of str, "
            f"got {type(value).__name__}"
        )
    if "\0" in text:
        raise ValueError("data_root holds a NUL character")


def _check_flags(value):
    if not isinstance(value, (tuple, list)) or not all(
        isinstance(flag, str) for flag in value
    ):
        raise TypeError("flags must be a tuple or list of str")


def _contract(data_root, path):
    try:
        with open(path, "rb") as file:
            content = file.read()
    except (FileNotFoundError, NotADirectoryError) as error:
        raise AttemptKernelError(NO_SPEC_FILE) from error
    except OSError as error:
        raise AttemptKernelError(SPEC_UNREADABLE) from error
    try:
        document = spec_file.parse(content)
    except spec_file.InvalidSpecFileError as error:
        raise AttemptKernelError(SPEC_INVALID) from error
    except spec_file.UnsupportedVersionError as error:
        raise AttemptKernelError(SPEC_OTHER_VERSION) from error
    try:
        named = spec_file.final_name(data_root, document)
    except layout.InvalidPathValueError as error:
        raise AttemptKernelError(SPEC_OTHER_ATTEMPT) from error
    if named != path:
        raise AttemptKernelError(SPEC_OTHER_ATTEMPT)
    return document["task"]["contract"]


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise
