"""The frame of a vendor adapter: its values and its interpret parts (ADR-0194 decisions 2, 3 and 6).

``ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md``
splits an adapter of one job (build, run or measure) into three parts:
**assemble**, a pure function from a target's values and the attempt's inputs
to the values one executor call takes; **execute**, one of the existing
executors, unchanged (:func:`hilclaw.clang_build.build` or
:func:`hilclaw.local_run.run` on the host,
:func:`hilclaw.standin_container.run_in_container` in a container); and
**interpret**, a pure function from what that executor returned or raised to
one :class:`Outcome`. No adapter starts a process of its own. This module
holds what every adapter shares:

* :class:`Outcome` and its three forms :data:`GO_ON`, :data:`BROKEN` and
  :data:`TOOL_FAILURE`, built by :func:`go_on`, :func:`broken` and
  :func:`tool_failure` (decision 3). A condition is one of the first four
  values of :data:`hilclaw.run_result.CONDITIONS`, taken from
  :data:`hilclaw.check_result.CONDITIONS`, whose first four are the same
  strings (the tests of ``run_result`` keep a closed list of the modules
  that import it); a kind is one of
  ``compiler_unavailable``, ``build_output_missing``,
  ``executable_unstartable`` and ``device_unavailable`` of
  :mod:`hilclaw.check_failure` (the last of ADR-0207 decision 6, given by a
  device probe and never by an interpret part of this module).
* :class:`BuildCall` and :class:`RunCall`: what an assemble part returns, the
  arguments of one executor call and the files to place before it.
* :class:`Probe` and its states :data:`PRESENT`, :data:`ABSENT` and
  :data:`UNREADABLE`: what a probe's interpret part returns (decision 7).
* The interpret parts on the host, :func:`interpret_build` and
  :func:`interpret_run`, and in a container,
  :func:`interpret_container_build` and :func:`interpret_container_run`.
  The host build reuses :func:`hilclaw.check_build.read_build` and the
  container reuses :func:`hilclaw.standin_answer.read_build`,
  :func:`~hilclaw.standin_answer.read_process` and
  :func:`~hilclaw.standin_answer.place_error`, so no table of ADR-0060 or
  ADR-0168 is copied here.
* :func:`measure`: the measure part, from one ended timing process on the
  host to the form (A) or (B) of :mod:`hilclaw.run_operation` (ADR-0065
  decision 4). A timing process in a container is read by
  :func:`hilclaw.standin_answer.read_timing_process` (ADR-0168 decision 4)
  and is not measured here.

Each interpret part takes the executor's returned value or the
:class:`Exception` it raised. For a returned value it gives an
:class:`Outcome`; for an exception it gives an :class:`Outcome` where a row of
decision 3 holds and ``None`` where none does, and the execute part then
raises that exception unchanged, so the frame does not swallow a fault of its
own. A request to end (an exception that is no :class:`Exception`) is never
placed. The time limit, the killing of the process and the container's
properties stay the executors'.

Choices that are this module's own and no rule of a record: an interpret part
refuses a value of a type its executor does not return with
:class:`TypeError` naming its type; a returned value that no row holds (a
status that is not exactly an ``int``) raises :class:`ValueError`; on the host
an :class:`OSError` of :func:`hilclaw.local_run.run` is a program that cannot
start only when it carries no ``path_role`` and its ``filename`` has the last
component of the program, as :mod:`subprocess` names the program in the error
of a failed start on POSIX (on native Windows that error names no file, and it
is passed on); and the message of each outcome is a fixed text that shows no
path, byte of output or text of an error (ADR-0060 decision 5).

It starts no process, reads no environment variable or clock and keeps
nothing between calls. The only file it reads is the stat of the artefact
path handed to :func:`interpret_container_build`. It is bound to no tool,
backend or target table.
"""

import math
import os
import stat
from typing import NamedTuple

from hilclaw import (
    check_build,
    check_failure,
    check_result,
    clang_build,
    local_run,
    standin_answer,
    standin_container,
)

GO_ON = "go_on"
BROKEN = "broken"
TOOL_FAILURE = "tool_failure"
FORMS = (GO_ON, BROKEN, TOOL_FAILURE)

_CONDITIONS = check_result.CONDITIONS[:4]
BUILD_TIME_LIMIT, BUILD_EXIT_STATUS, TIME_LIMIT, EXIT_STATUS = _CONDITIONS
KINDS = (
    check_failure.KIND_COMPILER_UNAVAILABLE,
    check_failure.KIND_BUILD_OUTPUT_MISSING,
    check_failure.KIND_EXECUTABLE_UNSTARTABLE,
    check_failure.KIND_DEVICE_UNAVAILABLE,
)
_INTERPRETED_KINDS = KINDS[:3]

PRESENT = "present"
ABSENT = "absent"
UNREADABLE = "unreadable"
PROBE_STATES = (PRESENT, ABSENT, UNREADABLE)

_MESSAGES = {
    GO_ON: "the step ended as expected",
    BUILD_TIME_LIMIT: "the build did not end within its time limit",
    BUILD_EXIT_STATUS: "the compiler ended with a non-zero status or by a signal",
    TIME_LIMIT: "the process did not end within its time limit",
    EXIT_STATUS: "the process ended with a non-zero status or by a signal",
    check_failure.KIND_COMPILER_UNAVAILABLE: "the compiler was not found or could not be started",
    check_failure.KIND_BUILD_OUTPUT_MISSING: "the compiler ended with status 0 and left no artefact",
    check_failure.KIND_EXECUTABLE_UNSTARTABLE: "the program was not found or could not be started",
    check_failure.KIND_DEVICE_UNAVAILABLE: "the device probe found no usable device",
}


class Outcome(NamedTuple):
    """One outcome of an interpret part (ADR-0194 decision 3).

    ``form`` is :data:`GO_ON`, :data:`BROKEN` or :data:`TOOL_FAILURE`.
    ``carried`` is what the next job needs after :data:`GO_ON` (the artefact
    path after a build, the process's standard output bytes after a run) and
    ``None`` otherwise; ``condition`` is set only for :data:`BROKEN` and
    ``kind`` only for :data:`TOOL_FAILURE`. ``message`` is a ``str``. Build it
    with :func:`go_on`, :func:`broken` or :func:`tool_failure`.
    """

    form: str
    message: str
    carried: object = None
    condition: str | None = None
    kind: str | None = None


class BuildCall(NamedTuple):
    """The arguments of one :func:`hilclaw.clang_build.build` call and the files to place.

    ``compiler`` is a ``tuple`` of ``str``, the program and any prefix;
    ``files`` is a ``tuple`` of pairs of a path and the ``bytes`` to write
    there before the call.
    """

    compiler: tuple
    flags: tuple
    sources: tuple
    trailing_flags: tuple
    output: object
    env: object
    timeout_s: object
    files: tuple = ()


class RunCall(NamedTuple):
    """The arguments of one :func:`hilclaw.local_run.run` call and the files to place.

    ``command`` is a ``tuple``: the program followed by ``str`` arguments.
    """

    command: tuple
    env: object
    timeout_s: object
    files: tuple = ()


class Probe(NamedTuple):
    """What a probe's interpret part found: ``state`` of :data:`PROBE_STATES`,
    ``version`` (a ``str`` when :data:`PRESENT`, else ``None``) and ``message``."""

    state: str
    version: str | None
    message: str


def _message(message, default):
    if message is None:
        return default
    if type(message) is not str:
        raise TypeError(f"message must be str, not {type(message).__name__}")
    return message


def go_on(carried, message=None):
    """Return the :data:`GO_ON` outcome that carries ``carried``."""
    return Outcome(GO_ON, _message(message, _MESSAGES[GO_ON]), carried=carried)


def broken(condition, message=None):
    """Return the :data:`BROKEN` outcome of ``condition``.

    Raises :class:`TypeError` when ``condition`` is not a ``str`` and
    :class:`ValueError` when it is not one of the first four values of
    :data:`hilclaw.run_result.CONDITIONS` (:data:`hilclaw.check_result.CONDITIONS`).
    """
    if type(condition) is not str:
        raise TypeError(f"condition must be str, not {type(condition).__name__}")
    if condition not in _CONDITIONS:
        raise ValueError(f"condition must be one of {_CONDITIONS}")
    return Outcome(BROKEN, _message(message, _MESSAGES[condition]), condition=condition)


def tool_failure(kind, message=None):
    """Return the :data:`TOOL_FAILURE` outcome of ``kind``.

    Raises :class:`TypeError` when ``kind`` is not a ``str`` and
    :class:`ValueError` when it is not one of :data:`KINDS`.
    """
    if type(kind) is not str:
        raise TypeError(f"kind must be str, not {type(kind).__name__}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    return Outcome(TOOL_FAILURE, _message(message, _MESSAGES[kind]), kind=kind)


def _answer_type(answer, *types):
    if isinstance(answer, BaseException) or type(answer) in types:
        return
    names = " or ".join(t.__name__ for t in types)
    error = TypeError(
        f"answer must be {names} or an exception, not {type(answer).__name__}"
    )
    error.parameter = "answer"
    raise error


def _from_condition_or_kind(value):
    if value in _CONDITIONS:
        return broken(value)
    return tool_failure(value)


def interpret_build(answer):
    """Return the outcome of what one :func:`hilclaw.clang_build.build` call gave.

    For a :class:`hilclaw.clang_build.BuildResult`, by
    :func:`hilclaw.check_build.read_build`: ``ok``, :data:`GO_ON` carrying
    ``output``; ``timed_out``, :data:`BROKEN` ``build_time_limit``; a
    non-zero ``returncode`` (a signal included), ``build_exit_status``;
    ``returncode`` 0 without ``ok``, which :mod:`hilclaw.clang_build` gives
    when the compiler left no artefact, :data:`TOOL_FAILURE`
    ``build_output_missing``. A result no row holds raises
    :class:`ValueError`. For :class:`hilclaw.clang_build.CompilerNotFoundError`
    or :class:`hilclaw.clang_build.CompilerNotStartedError`,
    ``compiler_unavailable``; for any other exception ``None``. Raises
    :class:`TypeError` with ``parameter`` ``"answer"`` for any other value.
    """
    _answer_type(answer, clang_build.BuildResult)
    if isinstance(answer, BaseException):
        if isinstance(
            answer,
            (clang_build.CompilerNotFoundError, clang_build.CompilerNotStartedError),
        ):
            return tool_failure(check_failure.KIND_COMPILER_UNAVAILABLE)
        return None
    read = check_build.read_build(answer)
    if read is check_build.BUILT:
        return go_on(answer.output)
    if read is None:
        raise ValueError("no row holds a build that is not ok and has no status")
    return _from_condition_or_kind(read)


def _path_text(value, parameter):
    if not isinstance(value, (str, os.PathLike)):
        error = TypeError(
            f"{parameter} must be str or os.PathLike, not {type(value).__name__}"
        )
    else:
        value = os.fspath(value)
        if not isinstance(value, str):
            error = TypeError(f"{parameter} must be a str path, not bytes")
        elif not value:
            error = ValueError(f"{parameter} is empty")
        else:
            return value
    error.parameter = parameter
    raise error


def _names_program(error, program):
    if getattr(error, "path_role", None) is not None:
        return False
    filename = getattr(error, "filename", None)
    if not isinstance(filename, str) or not filename:
        return False
    return os.path.basename(filename) == os.path.basename(program)


def _status_outcome(returncode, timed_out, stdout):
    if timed_out:
        return broken(TIME_LIMIT)
    if type(returncode) is not int:
        raise ValueError(
            "no row holds a process that did not time out and has no status"
        )
    if returncode == 0:
        return go_on(stdout)
    return broken(EXIT_STATUS)


def interpret_run(answer, program):
    """Return the outcome of what one :func:`hilclaw.local_run.run` call gave.

    For a :class:`hilclaw.local_run.RunResult`: ``timed_out``,
    :data:`BROKEN` ``time_limit``; status 0, :data:`GO_ON` carrying
    ``stdout``; any other status (a signal included), ``exit_status``; a
    status that is not exactly an ``int``, :class:`ValueError`. For
    :class:`hilclaw.local_run.ProgramNotFoundError`, or an :class:`OSError`
    without ``path_role`` whose ``filename`` names ``program`` (the first
    element of the command handed to the run; the failed start of the
    program), :data:`TOOL_FAILURE` ``executable_unstartable``; for any other
    exception ``None``. Raises :class:`TypeError` with ``parameter``
    ``"answer"`` for any other value, and :class:`TypeError` or
    :class:`ValueError` with ``parameter`` ``"program"`` for a ``program``
    that is not a non-empty ``str`` or :class:`os.PathLike` of ``str``.
    """
    _answer_type(answer, local_run.RunResult)
    program = _path_text(program, "program")
    if isinstance(answer, BaseException):
        if isinstance(answer, local_run.ProgramNotFoundError) or (
            isinstance(answer, OSError) and _names_program(answer, program)
        ):
            return tool_failure(check_failure.KIND_EXECUTABLE_UNSTARTABLE)
        return None
    return _status_outcome(answer.returncode, answer.timed_out, answer.stdout)


def _from_container_answer(read, carried):
    if read is standin_answer.GO_ON:
        return go_on(carried)
    if read is None:
        return None
    if type(read) is str:
        return broken(read)
    if read.kind in _INTERPRETED_KINDS:
        return tool_failure(read.kind, read.message)
    return None


def _artefact_present(artefact):
    try:
        mode = os.stat(artefact).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return False
    return stat.S_ISREG(mode)


def interpret_container_build(answer, artefact):
    """Return the outcome of what one build's :func:`hilclaw.standin_container.run_in_container` gave.

    For a :class:`hilclaw.standin_container.ContainerResult`, the answer of
    :func:`hilclaw.standin_answer.read_build` (ADR-0168): go on, where a
    regular file is at the host path ``artefact``, :data:`GO_ON` carrying
    ``artefact``, else :data:`TOOL_FAILURE` ``build_output_missing``; a
    condition, :data:`BROKEN`; 125 to 127, ``compiler_unavailable``; no row,
    :class:`ValueError`. For an exception, the answer of
    :func:`hilclaw.standin_answer.place_error` at its build step, ``None``
    where that answer is none or a kind outside the first three of :data:`KINDS`. An
    :class:`OSError` from the stat of ``artefact`` other than an absent path
    is passed on. Raises :class:`TypeError` with ``parameter`` ``"answer"``
    for any other value, and :class:`TypeError` or :class:`ValueError` with
    ``parameter`` ``"artefact"`` for an ``artefact`` that is not a non-empty
    ``str`` or :class:`os.PathLike` of ``str``.
    """
    _answer_type(answer, standin_container.ContainerResult)
    _path_text(artefact, "artefact")
    if isinstance(answer, BaseException):
        return _from_container_answer(
            standin_answer.place_error(answer, standin_answer.BUILD), None
        )
    read = standin_answer.read_build(answer)
    if read is None:
        raise ValueError(
            "no row holds a container that did not time out and has no status"
        )
    if read is standin_answer.GO_ON and not _artefact_present(artefact):
        return tool_failure(check_failure.KIND_BUILD_OUTPUT_MISSING)
    return _from_container_answer(read, artefact)


def interpret_container_run(answer):
    """Return the outcome of what one process's :func:`hilclaw.standin_container.run_in_container` gave.

    For a :class:`hilclaw.standin_container.ContainerResult`, the answer of
    :func:`hilclaw.standin_answer.read_process`: status 0, :data:`GO_ON`
    carrying ``stdout``; any other status, 125 to 127 included (ADR-0168
    decision 3), :data:`BROKEN` ``exit_status``; past the limit,
    ``time_limit``; no row, :class:`ValueError`. For an exception, as
    :func:`interpret_container_build` at the process step. Raises
    :class:`TypeError` with ``parameter`` ``"answer"`` for any other value.
    """
    _answer_type(answer, standin_container.ContainerResult)
    if isinstance(answer, BaseException):
        return _from_container_answer(
            standin_answer.place_error(answer, standin_answer.PROCESS), None
        )
    read = standin_answer.read_process(answer)
    if read is None:
        raise ValueError(
            "no row holds a container that did not time out and has no status"
        )
    return _from_container_answer(read, answer.stdout)


def _check_figure(figure):
    if figure is None:
        return
    if type(figure) is not int:
        error = TypeError(f"figure must be int or None, not {type(figure).__name__}")
    elif figure < 1:
        error = ValueError("figure must be at least 1")
    else:
        return
    error.parameter = "figure"
    raise error


def measure(answer, figure=None):
    """Return the form (A) or (B) of :mod:`hilclaw.run_operation` for one ended timing process.

    ``answer`` is the :class:`hilclaw.local_run.RunResult` of the timing
    process on the host;
    ``figure`` is the caller's memory figure, exactly an ``int`` of at least 1,
    or ``None``. Status 0 gives the pair ``(stdout, figure)``, the form (A);
    a time limit ``"time_limit"`` and any other status, a signal included,
    ``"exit_status"``, the form (B). It reads nothing but its
    arguments and computes no figure. Raises :class:`TypeError` or
    :class:`ValueError` with ``parameter`` ``"answer"`` or ``"figure"`` for a
    refused argument, and :class:`ValueError` for a status no row holds.
    """
    if type(answer) is not local_run.RunResult:
        error = TypeError(f"answer must be a RunResult, not {type(answer).__name__}")
        error.parameter = "answer"
        raise error
    _check_figure(figure)
    outcome = _status_outcome(answer.returncode, answer.timed_out, answer.stdout)
    if outcome.form == GO_ON:
        return (answer.stdout, figure)
    return outcome.condition


def check_timeout(timeout_s, parameter="timeout_s"):
    """Raise unless ``timeout_s`` is a positive finite ``int`` or ``float``.

    :class:`TypeError` for another type (a ``bool`` included) and
    :class:`ValueError` for a value that is not positive and finite, each with
    the attribute ``parameter`` set to ``parameter``.
    """
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        error = TypeError(
            f"{parameter} must be a number, not {type(timeout_s).__name__}"
        )
    elif not 0 < timeout_s < math.inf:
        error = ValueError(f"{parameter} must be positive and finite")
    else:
        return
    error.parameter = parameter
    raise error
