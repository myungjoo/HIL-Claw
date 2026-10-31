"""What a ``cpu_standin`` call answers for what its container slices return or raise (ADR-0168).

``ARCHITECTURE/decisions/ADR-0168-od18-standin-container-situations.md``
places every situation a container adds to a call of ``correctness.check``,
``sim.run`` or ``board.run`` at a run of ADR-0144 decision 1 under a backend
kind or a value of ``condition`` both contracts already have; a decision or a
row cited by its number alone (C1 to C19) is one of that record. This module
renders its table, ahead of the operations of ADR-0144 slice (4), as pure
functions over what the slices return or raise:

* :func:`read_image_value`: the value :func:`hilclaw.standin_image.read_image`
  returned (C1).
* :func:`read_copies`: the :class:`hilclaw.standin_copies.Copies` that
  :func:`hilclaw.standin_copies.place_copies` returned (C15).
* :func:`read_build`: the :class:`hilclaw.standin_container.ContainerResult`
  of a build container (the verification, timing or waiter's build): 0, go
  on; 125 to 127, ``compiler_unavailable`` (C5); any other status,
  ``"build_exit_status"`` (C6); past the limit, ``"build_time_limit"`` (C10).
* :func:`read_process`: the result of a verification process container: 0,
  go on; any other status, 125 to 127 included, ``"exit_status"`` (C8); past
  the limit, ``"time_limit"`` (C10).
* :func:`read_timing_process`: the result of a timing process container, the
  waiter's line looked for before the status (decision 4): a line and 0, the
  :class:`hilclaw.standin_waiter_line.WaiterRead`; a line or none with any
  other status, ``"exit_status"``; no line and 0, not placed (open under
  OD-18 sub-question 19 (na)); past the limit, ``"time_limit"``.
* :func:`place_error`: what one of the four steps raised, by the step:
  :data:`IMAGE` (C2), :data:`COPIES` (C12 to C16), :data:`BUILD` or
  :data:`PROCESS` (C2 to C4, C10, C11, C13, C14, C16, C17); a request to end
  is never placed (C18).
* :func:`build_dir_removable`: whether the operation may remove the build
  directory after a container, by decision 5.

An answer is one of: :data:`GO_ON`, the marker that the program's own result
is read on (for a timing process the ``WaiterRead`` instead); a value of
``condition`` (``"build_time_limit"``, ``"build_exit_status"``,
``"time_limit"``, ``"exit_status"``, each a value of both
:data:`hilclaw.check_result.CONDITIONS` and
:data:`hilclaw.run_result.CONDITIONS`); a :class:`Failure`, a backend kind of
:mod:`hilclaw.check_failure` (the run tools' are the same strings,
:mod:`hilclaw.run_failure`) with its message; or ``None``, not placed: the
operation lets it pass, and the landed rules answer ``operation_answer_invalid``
(ADR-0045 decision 4; ADR-0065 decision 7), which is no answer of the record.
The answers are the same for both contracts; only the timing process, which
the check does not have, is read differently from the verification process.

Choices that are this module's own and no rule of the record: a status counts
only when its type is exactly :class:`int`; a value that is not exactly the
type a function reads raises :class:`TypeError` naming its type and not the
value; the wording of each message, which shows no path, image reference,
container name, stream byte or error text (decision 6); the steps as four
strings; and the reading of the exception attributes ``container_name``,
``removal``, ``parameter`` and ``failure`` with :func:`getattr`. Where the
record leaves a situation open (C14, the timing stream with status 0 and no
waiter's line) the module answers ``None`` and invents nothing.

It starts no process, reads no environment variable, file or clock, imports
no NumPy and keeps nothing between calls. It is bound to no tool or backend;
:mod:`hilclaw.standin_check`, :mod:`hilclaw.standin_run` and
:mod:`hilclaw.model_forward_container` import it.
"""

from typing import NamedTuple

from hilclaw import (
    check_failure,
    check_result,
    kernel_source,
    local_run,
    standin_container,
    standin_copies,
    standin_image,
    standin_waiter_line,
)

#: The answer that the program's own result is read on.
GO_ON = object()

IMAGE = "image"
COPIES = "copies"
BUILD = "build"
PROCESS = "process"
STEPS = (IMAGE, COPIES, BUILD, PROCESS)

_BUILD_TIME_LIMIT, _BUILD_EXIT_STATUS, _TIME_LIMIT, _EXIT_STATUS = (
    check_result.CONDITIONS[:4]
)
_RUNTIME_STATUSES = frozenset((125, 126, 127))
_TIME_LIMIT_SETTINGS = ("timeout_s", "removal_timeout_s")
_READ_FAILURES = frozenset(
    (
        standin_copies.KERNEL_FILE_UNREADABLE,
        standin_copies.KERNEL_FILE_CHANGED,
        standin_copies.HARNESS_UNREADABLE,
        standin_copies.HARNESS_NOT_REGULAR_FILE,
        standin_copies.HARNESS_CHANGED,
    )
)
_WRITE_FAILURES = frozenset(
    (standin_copies.ENTRY_EXISTS, standin_copies.COPY_UNWRITABLE)
)
_ABSENT = object()


class Failure(NamedTuple):
    """A backend kind and the message the operation raises it with."""

    kind: str
    message: str


_NO_IMAGE = Failure(
    check_failure.KIND_COMPILER_UNAVAILABLE, "no container image is named"
)
_IMAGE_REFUSED = Failure(
    check_failure.KIND_COMPILER_UNAVAILABLE, "the container image named is refused"
)
_NO_KERNEL_SOURCE = Failure(
    check_failure.KIND_NO_KERNEL_SOURCE, "the attempt has no kernel source"
)
_READER_FAILED = Failure(
    check_failure.KIND_KERNEL_SOURCE_UNREADABLE,
    "the reader of the kernel source failed",
)
_INPUT_NOT_COPIED = Failure(
    check_failure.KIND_BUILD_INPUT_MISSING,
    "an input of the build could not be copied as a regular file",
)
_DIRECTORY_UNUSABLE = Failure(
    check_failure.KIND_BUILD_DIRECTORY_UNUSABLE,
    "the build directory could not be used or written",
)
_SETTING_REFUSED = Failure(
    check_failure.KIND_SETTINGS_REFUSED, "a time limit of a container is refused"
)
_RUNTIME_STATUS = Failure(
    check_failure.KIND_COMPILER_UNAVAILABLE,
    "the container runtime ended the build's container with a status of its own",
)
_NOT_STARTED = {
    BUILD: {
        "client": Failure(
            check_failure.KIND_COMPILER_UNAVAILABLE,
            "the container runtime's client was not found",
        ),
        "user": Failure(
            check_failure.KIND_COMPILER_UNAVAILABLE,
            "no numeric user and group can be had for a container",
        ),
        "image": Failure(
            check_failure.KIND_COMPILER_UNAVAILABLE,
            "the container image named is refused",
        ),
    },
    PROCESS: {
        "client": Failure(
            check_failure.KIND_EXECUTABLE_UNSTARTABLE,
            "the container runtime's client was not found",
        ),
        "user": Failure(
            check_failure.KIND_EXECUTABLE_UNSTARTABLE,
            "no numeric user and group can be had for a container",
        ),
        "image": Failure(
            check_failure.KIND_EXECUTABLE_UNSTARTABLE,
            "the container image named is refused",
        ),
    },
}


def _container_result(result):
    if type(result) is not standin_container.ContainerResult:
        raise TypeError(
            "result must be a standin_container.ContainerResult, "
            f"not {type(result).__name__}"
        )


def read_image_value(value):
    """Return the answer of the value :func:`hilclaw.standin_image.read_image` returned.

    :data:`GO_ON` for a ``str``; for ``None``, no image named, the
    :class:`Failure` ``compiler_unavailable`` (C1). Raises :class:`TypeError`
    for any other value.
    """
    if value is None:
        return _NO_IMAGE
    if type(value) is not str:
        raise TypeError(f"value must be str or None, not {type(value).__name__}")
    return GO_ON


def read_copies(copies):
    """Return the answer of the :class:`hilclaw.standin_copies.Copies` ``copies``.

    The :class:`Failure` ``no_kernel_source`` where the reader answered "no
    kernel source" (``missing`` set; C15), else :data:`GO_ON`. Raises
    :class:`TypeError` when ``copies`` is not exactly a ``Copies``.
    """
    if type(copies) is not standin_copies.Copies:
        raise TypeError(
            f"copies must be a standin_copies.Copies, not {type(copies).__name__}"
        )
    if copies.missing is not None:
        return _NO_KERNEL_SOURCE
    return GO_ON


def read_build(result):
    """Return the answer of the ``result`` of one build container.

    ``"build_time_limit"`` where it timed out, whatever its removal gave
    (C10); else by the status: 0, :data:`GO_ON` (C7; the operation then looks
    for the executable); 125, 126 or 127, the :class:`Failure`
    ``compiler_unavailable`` (C5); any other ``int``, a negative one included,
    ``"build_exit_status"`` (C6); a status that is not exactly an ``int``,
    ``None``. Raises :class:`TypeError` when ``result`` is not exactly a
    :class:`hilclaw.standin_container.ContainerResult`.
    """
    _container_result(result)
    if result.timed_out:
        return _BUILD_TIME_LIMIT
    status = result.returncode
    if type(status) is not int:
        return None
    if status == 0:
        return GO_ON
    if status in _RUNTIME_STATUSES:
        return _RUNTIME_STATUS
    return _BUILD_EXIT_STATUS


def read_process(result):
    """Return the answer of the ``result`` of one verification process container.

    ``"time_limit"`` where it timed out, whatever its removal gave (C10); else
    by the status, read as the program's: 0, :data:`GO_ON` (the operation
    reads the report on its standard output); any other ``int``, 125 to 127
    and a negative one included, ``"exit_status"`` (C8); a status that is not
    exactly an ``int``, ``None``. Raises :class:`TypeError` as
    :func:`read_build` does.
    """
    _container_result(result)
    if result.timed_out:
        return _TIME_LIMIT
    status = result.returncode
    if type(status) is not int:
        return None
    if status == 0:
        return GO_ON
    return _EXIT_STATUS


def read_timing_process(result):
    """Return the answer of the ``result`` of one timing process container (decision 4).

    ``"time_limit"`` where it timed out, whatever its removal gave (C10).
    Otherwise the waiter's line is looked for first, by
    :func:`hilclaw.standin_waiter_line.read` on its standard output: with a
    line and status 0 the answer is that
    :class:`hilclaw.standin_waiter_line.WaiterRead` (the report before the
    line and the figure); with a line or without one and any other ``int``
    status, 125 to 127 included, ``"exit_status"``; with no line and status
    0, ``None``, which the record leaves open; a status that is not exactly
    an ``int``, ``None``. Raises :class:`TypeError` as :func:`read_build`
    does, and as :func:`hilclaw.standin_waiter_line.read` does for a
    standard output that is not exactly ``bytes``.
    """
    _container_result(result)
    if result.timed_out:
        return _TIME_LIMIT
    waiter = standin_waiter_line.read(result.stdout)
    status = result.returncode
    if type(status) is not int:
        return None
    if status != 0:
        return _EXIT_STATUS
    return waiter


def _time_limit(step):
    return _BUILD_TIME_LIMIT if step == BUILD else _TIME_LIMIT


def _place_container_error(error, step):
    if getattr(error, "container_name", _ABSENT) is not _ABSENT:
        if getattr(error, "removal", _ABSENT) is _ABSENT:
            return _time_limit(step)
        if isinstance(error, OverflowError):
            return _SETTING_REFUSED
        return None
    if isinstance(error, local_run.ProgramNotFoundError):
        return _NOT_STARTED[step]["client"]
    if isinstance(error, standin_container.NoNumericUserError):
        return _NOT_STARTED[step]["user"]
    if isinstance(error, NotADirectoryError):
        return _DIRECTORY_UNUSABLE
    if isinstance(error, (TypeError, ValueError)):
        parameter = getattr(error, "parameter", None)
        if parameter == "image":
            return _NOT_STARTED[step]["image"]
        if parameter in _TIME_LIMIT_SETTINGS:
            return _SETTING_REFUSED
        if parameter == "build_dir" and isinstance(error, ValueError):
            return _DIRECTORY_UNUSABLE
    return None


def _place_copies_error(error):
    if isinstance(error, standin_copies.CopyError):
        failure = getattr(error, "failure", None)
        if failure in _READ_FAILURES:
            return _INPUT_NOT_COPIED
        if failure in _WRITE_FAILURES:
            return _DIRECTORY_UNUSABLE
        return None
    if isinstance(error, kernel_source.KernelSourceReadError):
        return _READER_FAILED
    if isinstance(error, NotADirectoryError):
        return _DIRECTORY_UNUSABLE
    return None


def place_error(error, step):
    """Return the answer of ``error``, raised at ``step``, or ``None`` when no row holds it.

    ``step`` is one of :data:`STEPS`: :data:`IMAGE` for
    :func:`hilclaw.standin_image.read_image`, :data:`COPIES` for
    :func:`hilclaw.standin_copies.place_copies`, :data:`BUILD` and
    :data:`PROCESS` for :func:`hilclaw.standin_container.run_in_container`
    of a build or a process container. The first test that holds:

    1. no :class:`Exception` (a request to end): ``None`` (C18);
    2. :data:`IMAGE`: :class:`hilclaw.standin_image.ImageRefusedError`, the
       :class:`Failure` ``compiler_unavailable`` (C2); anything else ``None``
       (C16);
    3. :data:`COPIES`: :class:`hilclaw.standin_copies.CopyError` of a reading
       failure, ``build_input_missing`` (C12), of a writing failure,
       ``build_directory_unusable`` (C13), of any other ``failure``, ``None``;
       :class:`hilclaw.kernel_source.KernelSourceReadError`,
       ``kernel_source_unreadable`` (C15); :class:`NotADirectoryError`,
       ``build_directory_unusable`` (C13); anything else, any other
       :class:`OSError` included (C14, open),
       :class:`hilclaw.kernel_source.InvalidOutputPathError` and the checks
       with ``parameter`` (C16), ``None``;
    4. :data:`BUILD` or :data:`PROCESS`: an error with ``container_name`` and
       no ``removal`` (raised by the forced removal after a timeout), the time
       limit, ``"build_time_limit"`` for a build and ``"time_limit"`` for a
       process (C10); one with both, :class:`OverflowError`
       ``settings_refused`` (C11), else ``None``;
       :class:`hilclaw.local_run.ProgramNotFoundError` (C3),
       :class:`hilclaw.standin_container.NoNumericUserError` (C4) and a
       :class:`TypeError` or :class:`ValueError` with ``parameter``
       ``"image"`` (C2), ``compiler_unavailable`` for a build and
       ``executable_unstartable`` for a process; :class:`NotADirectoryError`
       and a :class:`ValueError` with ``parameter`` ``"build_dir"``,
       ``build_directory_unusable`` (C13); a :class:`TypeError` or
       :class:`ValueError` with ``parameter`` ``"timeout_s"`` or
       ``"removal_timeout_s"``, ``settings_refused`` (C17); anything else,
       any other :class:`OSError` included (C14, open), ``None``.

    Raises :class:`TypeError` when ``step`` is not a ``str`` and
    :class:`ValueError` when it is not one of :data:`STEPS`. ``error`` is not
    modified; no message, ``args`` or chain of it is read.
    """
    if type(step) is not str:
        raise TypeError(f"step must be str, not {type(step).__name__}")
    if step not in STEPS:
        raise ValueError(f"step must be one of {STEPS}")
    if not isinstance(error, Exception):
        return None
    if step == IMAGE:
        if isinstance(error, standin_image.ImageRefusedError):
            return _IMAGE_REFUSED
        return None
    if step == COPIES:
        return _place_copies_error(error)
    return _place_container_error(error, step)


def build_dir_removable(outcome):
    """Return whether the build directory may be removed after ``outcome`` (decision 5).

    ``outcome`` is what one :func:`hilclaw.standin_container.run_in_container`
    call gave: its :class:`hilclaw.standin_container.ContainerResult`, or the
    :class:`BaseException` it raised. ``True`` where no container of it can
    still run: a result that did not time out (the container was removed with
    its end), a forced removal shown to have succeeded (a
    :class:`hilclaw.standin_container.Removal` with status 0 that did not time
    out), or an exception without ``container_name`` that is no
    :class:`OSError` (nothing was started). ``False`` otherwise, an
    :class:`OSError` without ``container_name`` included, which may come
    after the start and leave the container running (C14): the directory is
    left, and the answer of the call is not changed by it. Raises :class:`TypeError` for any other ``outcome``.
    """
    if type(outcome) is standin_container.ContainerResult:
        if not outcome.timed_out:
            return True
        return _removed(outcome.removal)
    if isinstance(outcome, BaseException):
        if getattr(outcome, "container_name", _ABSENT) is _ABSENT:
            return not isinstance(outcome, OSError)
        return _removed(getattr(outcome, "removal", None))
    raise TypeError(
        "outcome must be a standin_container.ContainerResult or an exception, "
        f"not {type(outcome).__name__}"
    )


def _removed(removal):
    return (
        type(removal) is standin_container.Removal
        and not removal.timed_out
        and type(removal.returncode) is int
        and removal.returncode == 0
    )
