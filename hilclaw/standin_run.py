"""The ``cpu_standin`` operation of ``sim.run`` and ``board.run`` in three containers (ADR-0144 slice (4), the run tools' part; ADR-0170).

``ARCHITECTURE/decisions/ADR-0170-od18-standin-run-operation.md`` decides
that the compiler's log of the waiter's build is not kept and how the keeper
is handed the timing build's log in a call that builds twice; a decision
cited by its number alone is one of that record. :func:`operation` is the
operation of both run tools at a run of ADR-0144 decision 1: the two tools
carry out the same local run, and that the two operations may be one piece
of code is the code's (ADR-0038 decision 2). It is called
as :func:`hilclaw.run_operation.ask` calls an operation, with five positional
things: the request, the hw_profile, the timing parameters, the output path
and the log keeper. In the order of the Walk-through of ADR-0168, ADR-0145
decision 3 and decision 3 it:

1. checks its own arguments and computes the eight arguments of the timing
   driver (:func:`hilclaw.harness.timing.driver_arguments`) and the time
   limit of the timing process
   (:func:`hilclaw.standin_settings.timing_process_time_limit_s`);
2. reads the image (C1, C2) and makes the build directory of the call (S3),
   as :mod:`hilclaw.standin_check` does;
3. copies the kernel files and :data:`hilclaw.harness.timing_build.DRIVER_SOURCE`
   (:func:`hilclaw.standin_copies.place_copies`), then :data:`WAITER_SOURCE`
   beside the driver (:func:`hilclaw.standin_copies.place_harness_copy`;
   C12, C13, C15);
4. runs the timing build in one container: :data:`hilclaw.standin_check.COMPILER`
   with :data:`hilclaw.standin_settings.FLAGS`, the driver source first and
   the kernel's compiled set in the reader's order, the trailing flags and
   ``-o`` :data:`TIMING_EXECUTABLE_NAME`, within
   :data:`hilclaw.standin_settings.BUILD_TIME_LIMIT_S`; hands the keeper its
   log by ADR-0169 decisions 2 and 3, before anything else is looked at
   (decision 3); answers a status 0 that left no executable
   ``build_output_missing`` (S9);
5. runs the waiter's build in a second container: the flags, the waiter's
   source and ``-o`` :data:`WAITER_EXECUTABLE_NAME`, no trailing flag
   (decision 4), within what is left of the build limit; hands the keeper
   nothing for it (decision 2); answers it by C19, with
   ``"build_time_limit"`` and no container where nothing is left;
6. runs the timing process in a third container, which starts the waiter with
   the timing executable's path and the driver's eight arguments, within the
   process limit, reads it with
   :func:`hilclaw.standin_answer.read_timing_process` and returns the pair
   of the report and the figure, or a value of ``condition``;
7. removes the build directory before it returns or raises, where every
   container of the call allows it (ADR-0168 decision 5).

The pair is a plain ``tuple``, the form (A) that :func:`hilclaw.run_operation.ask`
tells apart, which makes a :class:`hilclaw.run_operation.Reported` of it; a
``Reported`` returned here would be no pair there. Every
:class:`hilclaw.standin_answer.Failure` is raised as
:class:`hilclaw.tools.ToolFailure` with its kind and message, and what a
step raises is placed by :func:`hilclaw.standin_answer.place_error`; what no
row places (C14, C16) and every request to end (C18) passes as it is. A
timing process stream with status 0 and no waiter's line, which ADR-0168
decision 4 leaves open, and a status that is not exactly an ``int`` raise
:class:`RuntimeError`, which the landed rule answers
``operation_answer_invalid``. Every forced removal of a container is given
:data:`hilclaw.standin_check.REMOVAL_TIMEOUT_S` (ADR-0169 decision 5). The
steps shared with :mod:`hilclaw.standin_check` are its functions.

Choices that are this module's own and no rule of a record:

* The build directory has the prefix :data:`BUILD_DIR_PREFIX`; where it lies
  and how it is removed are those of :mod:`hilclaw.standin_check`.
* The executables are :data:`TIMING_EXECUTABLE_NAME` and
  :data:`WAITER_EXECUTABLE_NAME` directly in the build directory; the copies
  keep the basenames of their sources.
* The operation's own work between the two builds counts against the build
  limit (ADR-0145 decision 3 gives this to the code): the waiter's build is
  given the limit less the time of :func:`time.monotonic` from just before
  the timing build's container to just before the waiter's. Where that is
  not above zero no container is started.
* The waiter's build that ended with status 0 and left no regular file at
  its executable's path is ``build_output_missing`` with a message of its
  own, which shows no path.
* Before anything is read or made, :class:`TypeError` is raised for timing
  parameters that are not exactly a
  :class:`hilclaw.run_parameters.TimingParameters` or a keeper that is not
  exactly a :class:`hilclaw.build_log.LogKeeper`, and what
  :func:`hilclaw.harness.timing.driver_arguments` and the process limit
  raise for their values passes (C16: no row; the tool function admits these
  values before the call).

It hands the compiler nothing derived from the seed (ADR-0108 decision 4):
the seed is only among the timing process's arguments. It imports no NumPy
(the judging is the tool function's, ADR-0061 decision 3), reads no
environment variable of its own (the image's is read by
:func:`hilclaw.standin_image.read_image`) and keeps nothing between calls.
It is bound to no backend table: the default table and the registry do not
name it yet (ADR-0167 Boundaries).
"""

from time import monotonic

from hilclaw import (
    build_log,
    run_failure,
    run_parameters,
    standin_answer,
    standin_check,
    standin_copies,
    standin_settings,
    standin_waiter_line,
)
from hilclaw.harness import timing, timing_build

#: The waiter's source in the installation (ADR-0145 decision 3).
WAITER_SOURCE = timing_build.DRIVER_SOURCE.with_name("timing_waiter.c")

TIMING_EXECUTABLE_NAME = "timing"
WAITER_EXECUTABLE_NAME = "waiter"
BUILD_DIR_PREFIX = "hilclaw-standin-run-"

_TIMING_EXECUTABLE = standin_check.in_container(TIMING_EXECUTABLE_NAME)
_WAITER_EXECUTABLE = standin_check.in_container(WAITER_EXECUTABLE_NAME)
_NO_TIMING_EXECUTABLE = standin_answer.Failure(
    run_failure.KIND_BUILD_OUTPUT_MISSING,
    "the timing build ended with status 0 and left no executable",
)
_NO_WAITER = standin_answer.Failure(
    run_failure.KIND_BUILD_OUTPUT_MISSING,
    "the waiter's build ended with status 0 and left no executable",
)
_NOT_PLACED = "no row places what the timing process container handed back"


def operation(request, hw_profile, parameters, output_path, keeper, /):
    """Carry out one timing run at ``cpu_standin`` in three containers; return the report and figure or a condition.

    ``request`` and ``hw_profile`` are not read. ``parameters`` are the
    timing parameters, exactly a :class:`hilclaw.run_parameters.TimingParameters`;
    ``output_path`` is handed to :func:`hilclaw.standin_copies.place_copies`
    as it is; ``keeper`` is the call's :class:`hilclaw.build_log.LogKeeper`,
    handed at most the timing build's log (ADR-0170 decisions 2 and 3).

    Returns ``(report, memory_bytes)`` as a plain ``tuple`` after a waiter's
    line and status 0 — the ``bytes`` before the line and the figure or
    ``None`` — or one of ``"build_time_limit"``, ``"build_exit_status"``,
    ``"time_limit"`` and ``"exit_status"``. Raises
    :class:`hilclaw.tools.ToolFailure` of a backend kind for every row of
    ADR-0168 that is one, with a message that shows no path, image
    reference, container name, stream byte or error text. Lets pass what no
    row places and every request to end. See the module docstring for the
    order and the module's own choices.
    """
    arguments, process_limit = _checked(parameters, keeper)
    image = standin_check.container_image()
    build_dir = standin_check.make_build_dir(BUILD_DIR_PREFIX)
    return standin_check.carry_out(
        build_dir,
        lambda outcomes: _carry_out(
            image, build_dir, output_path, keeper, arguments, process_limit, outcomes
        ),
    )


def _checked(parameters, keeper):
    if type(parameters) is not run_parameters.TimingParameters:
        raise TypeError(
            f"parameters must be TimingParameters, not {type(parameters).__name__}"
        )
    if type(keeper) is not build_log.LogKeeper:
        raise TypeError(f"keeper must be a LogKeeper, not {type(keeper).__name__}")
    m, k, n, n_max, sample_form, seed = parameters
    arguments = timing.driver_arguments(
        m=m, k=k, n=n, n_max=n_max, sample_form=sample_form, seed=seed
    )
    return arguments, standin_settings.timing_process_time_limit_s(m, k, n, n_max)


def _carry_out(image, build_dir, output_path, keeper, arguments, limit, outcomes):
    copies, waiter = _placed_copies(output_path, build_dir)
    built = _build(image, build_dir, copies, waiter, keeper, outcomes)
    if built is not standin_answer.GO_ON:
        return built
    ran = standin_check.run_container(
        outcomes,
        standin_answer.PROCESS,
        image,
        build_dir,
        _WAITER_EXECUTABLE,
        (_TIMING_EXECUTABLE, *arguments),
        limit,
    )
    if type(ran) is str:
        return ran
    answer = standin_answer.read_timing_process(ran)
    if type(answer) is standin_waiter_line.WaiterRead:
        return (answer.report, answer.memory_bytes)
    if type(answer) is str:
        return answer
    raise RuntimeError(_NOT_PLACED)


def _placed_copies(output_path, build_dir):
    try:
        copies = standin_copies.place_copies(
            output_path, timing_build.DRIVER_SOURCE, build_dir
        )
        answer = standin_answer.read_copies(copies)
        if answer is not standin_answer.GO_ON:
            raise standin_check.Answered(answer)
        waiter = standin_copies.place_harness_copy(WAITER_SOURCE, build_dir)
    except standin_check.Answered:
        raise
    except Exception as error:
        answer = standin_answer.place_error(error, standin_answer.COPIES)
        if type(answer) is not standin_answer.Failure:
            raise
        raise standin_check.Answered(answer) from None
    return copies, waiter


def _build(image, build_dir, copies, waiter, keeper, outcomes):
    flags = standin_settings.FLAGS
    sources = (copies.harness, *copies.compiled_set)
    started = monotonic()
    built = standin_check.run_build(
        outcomes,
        image,
        build_dir,
        (
            *flags,
            *(standin_check.in_container(source) for source in sources),
            *standin_settings.TRAILING_FLAGS,
            "-o",
            _TIMING_EXECUTABLE,
        ),
        standin_settings.BUILD_TIME_LIMIT_S,
        keeper=keeper,
        executable=TIMING_EXECUTABLE_NAME,
        missing=_NO_TIMING_EXECUTABLE,
    )
    if built is not standin_answer.GO_ON:
        return built
    left = standin_settings.BUILD_TIME_LIMIT_S - (monotonic() - started)
    if not left > 0:
        return "build_time_limit"
    return standin_check.run_build(
        outcomes,
        image,
        build_dir,
        (*flags, standin_check.in_container(waiter), "-o", _WAITER_EXECUTABLE),
        left,
        keeper=None,
        executable=WAITER_EXECUTABLE_NAME,
        missing=_NO_WAITER,
    )
