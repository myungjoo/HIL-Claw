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
  :func:`hilclaw.spec_file.parse_versioned`; the file belongs to the attempt
  at its path only when the ``id`` of the document formats to that path
  (:func:`hilclaw.layout.attempt_artefact`).

An attempt whose spec is of version 2 is a coder attempt and holds its own
kernel. An attempt whose spec is of version 3 is a candidate of the kind
``compile_settings`` (ADR-0198 decisions 2 and 4): its ``output/`` is empty
and its kernel is that of the attempt its ``task.build`` names
(``kernel_round``, ``kernel_candidate``, ``kernel_attempt``), whose spec must
be of version 2: an attempt with a version-3 spec is no kernel source.
:func:`kernel_attempt` says which attempt holds the kernel of an attempt and
with which candidate flags; :func:`kernel_reference` reads that kernel.

The caller of :func:`kernel_reference` passes the build settings the attempt
was built with, for example :data:`hilclaw.standin_settings.FLAGS` for a
``cpu_standin`` run (ADR-0116 decision 2); this module reads no record of
build settings and chooses none. The caller also names the attempt, the call
site and the shapes of a binding entry: the reader chooses no kernel
(ADR-0153 decision 3).

Outcomes of :func:`kernel_attempt` and :func:`kernel_reference`, checked in
this order:

* A malformed argument raises :class:`TypeError` or :class:`ValueError` with
  the attribute ``parameter``, the name of the argument, before anything is
  read. ``data_root`` that is not a ``str`` or an :class:`os.PathLike` of
  ``str`` is a :class:`TypeError`, one holding a NUL character a
  :class:`ValueError`. A ``run_id``, ``round``, ``candidate`` or ``attempt``
  that :mod:`hilclaw.layout` refuses raises its
  :class:`hilclaw.layout.InvalidPathValueError` (a :class:`ValueError`),
  passed through with ``parameter`` added; a ``bool`` or a negative number is
  among them. ``flags`` of :func:`kernel_reference` that is not a ``tuple``
  or ``list`` of ``str`` is a :class:`TypeError`.
* Every other outcome but the answer raises :class:`AttemptKernelError`,
  whose ``reason`` is one of :data:`REASONS`; the original error, where one
  exists, is its ``__cause__``. The spec reasons hold for the spec of the
  attempt asked about and, where that spec is of version 3, for the spec of
  the attempt it names:

  - :data:`NO_SPEC_FILE`: nothing is at the path of the spec, or a component
    above it is no directory (the attempt directory is missing among them).
  - :data:`SPEC_UNREADABLE`: any other error of opening or reading the spec.
  - :data:`SPEC_INVALID`: :func:`hilclaw.spec_file.parse_versioned` refuses
    the content as invalid (:class:`hilclaw.spec_file.InvalidSpecFileError`).
  - :data:`SPEC_OTHER_VERSION`: the content is of a version other than 2 and
    3, version 1 among them (:class:`hilclaw.spec_file.UnsupportedVersionError`,
    ADR-0051 decision 3), or the spec of the attempt a version-3 spec names
    is of version 3 (ADR-0198 decision 2).
  - :data:`SPEC_OTHER_ATTEMPT`: the ``id`` of the document formats to another
    path than the one read, or to none
    (:class:`hilclaw.layout.InvalidPathValueError`).
  - one of :data:`hilclaw.kernel_source.NO_KERNEL_SOURCE_CASES`
    (:func:`kernel_reference` only): the attempt that holds the kernel has
    no kernel source (R1, R4). The specs are read first, so
    :data:`hilclaw.kernel_source.NO_ATTEMPT_DIRECTORY` comes only when the
    attempt directory is gone after its spec was read.
  - one of :data:`hilclaw.kernel_source.READER_FAILURES`
    (:func:`kernel_reference` only): the reader of ADR-0055 failed (R8,
    :class:`hilclaw.kernel_source.KernelSourceReadError`).

* Otherwise :func:`kernel_attempt` returns a :class:`KernelAttempt` and
  :func:`kernel_reference` a :class:`hilclaw.model_binding.KernelReference`.

Conventions of this module, which are not rules of the records: a spec is
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
and creates nothing, reads no file of the run but the specs, lists nothing
but what the reader of ADR-0055 lists and walks no directory (ADR-0004
decision 3); and it is no tool and exposes no executor (OD-31, OD-18, OD-23).
"""

import contextlib
import os
from typing import NamedTuple

from hilclaw import kernel_source, layout, spec, spec_file
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


class KernelAttempt(NamedTuple):
    """Answer of :func:`kernel_attempt`: the attempt that holds a kernel, and a candidate's flags.

    ``round``, ``candidate`` and ``attempt`` name the attempt whose
    ``output/`` holds the kernel: the attempt asked about when its spec is of
    version 2, else the attempt its ``task.build`` names. ``flags`` is
    ``None`` for a version-2 spec and the ``tuple`` of ``task.build.flags``
    of a version-3 spec. ``contract`` is the ``task.contract`` of the spec of
    the attempt that holds the kernel.
    """

    round: int
    candidate: int
    attempt: int
    flags: tuple | None
    contract: dict


def kernel_attempt(data_root, run_id, round, candidate, attempt):
    """Return the :class:`KernelAttempt` of one attempt of a run (ADR-0198 decision 2).

    The attempt is ``round``, ``candidate`` and ``attempt`` of the run
    ``run_id`` below ``data_root``. Its spec is read and, when it is of
    version 3, the spec of the attempt its ``task.build`` names, which must
    be of version 2. No ``output/`` is read: whether the attempt that holds
    the kernel has a compiled set is not looked at here.

    Raises as the module docstring lists: :class:`TypeError` or
    :class:`ValueError` with ``parameter`` for a malformed argument, and
    :class:`AttemptKernelError` with a spec reason.
    """
    _check_attempt(data_root, run_id, round, candidate, attempt)
    return _followed(data_root, run_id, (round, candidate, attempt))


def kernel_reference(data_root, run_id, round, candidate, attempt, *, flags):
    """Return the :class:`hilclaw.model_binding.KernelReference` of one attempt of a run.

    The attempt is ``round``, ``candidate`` and ``attempt`` of the run
    ``run_id`` below ``data_root`` (ADR-0004 decisions 2 and 3). The kernel is
    that of the attempt :func:`kernel_attempt` gives: the attempt itself for
    a version-2 spec, the attempt its ``task.build`` names for a version-3
    spec (ADR-0198 decision 2). The answer's ``sources`` is the compiled set
    of that attempt's ``output/`` in the order of R3; its ``contract`` is the
    ``task.contract`` of that attempt's spec; its ``flags`` is
    ``tuple(flags)``, whatever the version of the spec, so a version-3 spec's
    own flags are not added; its ``headers`` is the kernel's own headers of
    R5 in the reader's order. ``flags`` is required: the caller passes the
    settings the attempt was built with, for example
    :data:`hilclaw.standin_settings.FLAGS` for a ``cpu_standin`` run.

    Raises as the module docstring lists: :class:`TypeError` or
    :class:`ValueError` with ``parameter`` for a malformed argument, and
    :class:`AttemptKernelError` for an attempt that gives no reference.
    """
    _check_attempt(data_root, run_id, round, candidate, attempt)
    with _parameter("flags"):
        _check_flags(flags)
    followed = _followed(data_root, run_id, (round, candidate, attempt))
    numbers = followed.round, followed.candidate, followed.attempt
    output = layout.attempt_artefact(data_root, run_id, *numbers, "output")
    try:
        source = kernel_source.read_compiled_set(output)
    except kernel_source.KernelSourceReadError as error:
        raise AttemptKernelError(error.failure) from error
    if source.missing is not None:
        raise AttemptKernelError(source.missing)
    return KernelReference(
        tuple(source.compiled_set),
        followed.contract,
        tuple(flags),
        tuple(source.headers),
    )


def _check_attempt(data_root, run_id, round, candidate, attempt):
    with _parameter("data_root"):
        _check_data_root(data_root)
    with _parameter("run_id"):
        layout.check_run_id(run_id)
    with _parameter("round"):
        layout.round_dir(data_root, run_id, round)
    with _parameter("candidate"):
        layout.attempt_dir(data_root, run_id, round, "coder", candidate, 1)
    with _parameter("attempt"):
        layout.attempt_artefact(
            data_root, run_id, round, candidate, attempt, "spec.json"
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


def _followed(data_root, run_id, numbers):
    document = _spec(data_root, run_id, numbers)
    if document["schema_version"] == spec.SCHEMA_VERSION:
        return KernelAttempt(*numbers, None, document["task"]["contract"])
    build = document["task"]["build"]
    named = build["kernel_round"], build["kernel_candidate"], build["kernel_attempt"]
    kernel = _spec(data_root, run_id, named)
    if kernel["schema_version"] != spec.SCHEMA_VERSION:
        raise AttemptKernelError(SPEC_OTHER_VERSION)
    return KernelAttempt(*named, tuple(build["flags"]), kernel["task"]["contract"])


def _spec(data_root, run_id, numbers):
    path = layout.attempt_artefact(data_root, run_id, *numbers, "spec.json")
    try:
        with open(path, "rb") as file:
            content = file.read()
    except (FileNotFoundError, NotADirectoryError) as error:
        raise AttemptKernelError(NO_SPEC_FILE) from error
    except OSError as error:
        raise AttemptKernelError(SPEC_UNREADABLE) from error
    try:
        document = spec_file.parse_versioned(content)
    except spec_file.InvalidSpecFileError as error:
        raise AttemptKernelError(SPEC_INVALID) from error
    except spec_file.UnsupportedVersionError as error:
        raise AttemptKernelError(SPEC_OTHER_VERSION) from error
    ident = document["id"]
    named = ident["round"], ident["candidate"], ident["attempt"]
    try:
        formatted = layout.attempt_artefact(
            data_root, ident["run_id"], *named, "spec.json"
        )
    except layout.InvalidPathValueError as error:
        raise AttemptKernelError(SPEC_OTHER_ATTEMPT) from error
    if formatted != path:
        raise AttemptKernelError(SPEC_OTHER_ATTEMPT)
    return document


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise
