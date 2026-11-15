"""The ``cuda_gpu`` operation of ``sim.run`` and ``board.run`` in containers (ADR-0207 decision 9, slice 5).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md``
decision 8 has both points of ``cuda_gpu`` run the same local GPU run
(HQ-0095 (2) (a)): :func:`operation_for` builds one operation that serves
both run tools, called as :func:`hilclaw.run_operation.ask` calls an
operation, with five positional things: the request, the hw_profile, the
timing parameters, the output path and the log keeper. The results of the two
tools differ only by the existing ``step`` values (ADR-0194 decision 5); the
operation adds no member. In the order of :mod:`hilclaw.cuda_check` and of
:mod:`hilclaw.standin_run` (ADR-0145 decision 3, ADR-0170) it:

1. checks its own arguments and computes the eight arguments of the timing
   driver (:func:`hilclaw.harness.timing.driver_arguments`) and the time
   limit of the timing process
   (:func:`hilclaw.standin_settings.timing_process_time_limit_s` with the
   target's cap);
2. reads the image (:func:`hilclaw.cuda_check.container_image`; C1, C2) and
   makes the build directory of the call (S3);
3. runs the device check in a probe container with ``--gpus all``
   (:func:`hilclaw.cuda_check.confirm_device`): ``device_unavailable`` before
   any build and any process of the attempt (ADR-0207 decision 6);
4. copies the selected kernel files with
   :data:`hilclaw.harness.cuda_programs.TIMING_DRIVER_SOURCE` and the waiter's
   source :data:`hilclaw.standin_run.WAITER_SOURCE` beside it
   (:func:`hilclaw.cuda_check.place_sources`);
5. builds the driver, then the copies, into :data:`TIMING_EXECUTABLE_NAME`
   with ``nvcc`` at the target's flags and trailing flags in a build container
   with ``--gpus all`` (:func:`hilclaw.cuda_check.build_in_container`), handing
   the keeper the compiler's log of that build (ADR-0170 decisions 2 and 3);
6. builds the waiter of ADR-0145 into :data:`WAITER_EXECUTABLE_NAME` with
   ``nvcc`` at the target's ``waiter_flags`` (ADR-0207 decision 3), no
   trailing flag, in its own build container with ``--gpus all``, within
   what is left of the build limit, handing the keeper nothing; with
   ``"build_time_limit"`` and no container where nothing is left;
7. runs the timing process under the waiter in a process container with
   ``--gpus all`` (:func:`hilclaw.cuda_check.run_process`), with the target's
   ``memory_limit_bytes`` (``None`` for ``cuda_gpu``), reads it with
   :func:`hilclaw.standin_answer.read_timing_process` as
   :mod:`hilclaw.standin_run` reads it, and returns the pair
   ``(report, memory_bytes)``, the form (A) of :mod:`hilclaw.run_operation`,
   or ``"time_limit"`` or ``"exit_status"``.

The build directory is removed on every path where every container of the
call allows it (:func:`hilclaw.standin_check.carry_out`). The timing boundary
is ADR-0194 decision 4 as the timing driver implements it (transfers outside
the interval). ``memory_bytes`` is the waiter's figure of the host process
(ADR-0145); no GPU memory figure is reported (HQ-0090). The unit of the
report is ``ns`` (the target's ``units_per_ns`` 1). A non-zero status or an
incomplete report of the attempt's process is never a tool failure; a device
lost after the probe went on is that process's ``"exit_status"``. A timing
process stream with status 0 and no waiter's line raises
:class:`RuntimeError`, as in :mod:`hilclaw.standin_run`.

**The kernel's files are the caller's** and **only in containers**, as in
:mod:`hilclaw.cuda_check`: the kernel's files are those the selection
``sources`` names, given by name with no default. The ``cuda_gpu`` entry of
:func:`hilclaw.check_definition.default_table` offers this operation for
both run tools with :func:`hilclaw.cuda_check.compiled_sources`, the
selection of an attempt's own ``output/`` after the owner's HQ-0104 (a)
(``ARCHITECTURE/decisions/ADR-0208-od33-cuda-kernel-record-in-a-run.md``
decisions 1 and 5).

Choices that are this module's own and no rule of a record: the waiter's
build is given the build limit less the time of :func:`time.monotonic` from
just before the timing build's container to just before the waiter's, as in
:mod:`hilclaw.standin_run`; before anything is started, :class:`TypeError` is
raised for timing parameters that are not exactly a
:class:`hilclaw.run_parameters.TimingParameters` (a bf16 run is no run of
this contract) or a keeper that is not exactly a
:class:`hilclaw.build_log.LogKeeper`, and what the functions of step 1 raise
for their values passes.
"""

from time import monotonic

from hilclaw import (
    cuda_check,
    run_failure,
    run_parameters,
    standin_answer,
    standin_check,
    standin_run,
    standin_settings,
    standin_waiter_line,
)
from hilclaw.harness import cuda_programs, timing

TIMING_EXECUTABLE_NAME = "timing"
WAITER_EXECUTABLE_NAME = "waiter"
BUILD_DIR_PREFIX = "hilclaw-cuda-run-"

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


def operation_for(target, *, sources):
    """Return the ``sim.run`` and ``board.run`` operation of ``target`` in containers.

    ``target`` and ``sources`` as :func:`hilclaw.cuda_check.operation_for`,
    with the same refusals; the target's waiter flags are also the call's.
    The operation takes the five positional arguments of
    :func:`hilclaw.run_operation.ask`, reads neither the request nor the
    hw_profile, and returns ``(report, memory_bytes)`` as a plain ``tuple``
    (``memory_bytes`` an ``int`` or ``None``) or one of
    ``"build_time_limit"``, ``"build_exit_status"``, ``"time_limit"`` and
    ``"exit_status"``; it raises :class:`hilclaw.tools.ToolFailure` of a
    backend kind of :mod:`hilclaw.run_failure`, ``device_unavailable``
    before any build. What no row places, and every request to end, passes
    as it is.
    """
    cuda_check.check_target(target)
    cuda_check.check_sources(sources)

    def operation(request, hw_profile, parameters, output_path, keeper, /):
        arguments, limit = _checked(parameters, keeper, target.process_time_limit_cap_s)
        image = cuda_check.container_image()
        build_dir = standin_check.make_build_dir(BUILD_DIR_PREFIX)
        return standin_check.carry_out(
            build_dir,
            lambda outcomes: _carry_out(
                target,
                sources,
                image,
                build_dir,
                output_path,
                keeper,
                arguments,
                limit,
                outcomes,
            ),
        )

    return operation


def _checked(parameters, keeper, cap_s):
    if type(parameters) is not run_parameters.TimingParameters:
        raise TypeError(
            f"parameters must be TimingParameters, not {type(parameters).__name__}"
        )
    cuda_check.check_keeper(keeper)
    arguments = timing.driver_arguments(**parameters._asdict())
    m, k, n, n_max, _, _ = parameters
    limit = standin_settings.timing_process_time_limit_s(m, k, n, n_max, cap_s)
    return arguments, limit


def _carry_out(
    target, sources, image, build_dir, output_path, keeper, arguments, limit, outcomes
):
    cuda_check.confirm_device(image, build_dir, outcomes)
    copies = cuda_check.place_sources(
        sources,
        output_path,
        cuda_programs.TIMING_DRIVER_SOURCE,
        build_dir,
        (standin_run.WAITER_SOURCE,),
    )
    built = _build(target, image, build_dir, copies, keeper, outcomes)
    if built is not standin_answer.GO_ON:
        return built
    ran = cuda_check.run_process(
        outcomes,
        image,
        build_dir,
        _WAITER_EXECUTABLE,
        (_TIMING_EXECUTABLE, *arguments),
        limit,
        target.memory_limit_bytes,
    )
    if type(ran) is str:
        return ran
    answer = standin_answer.read_timing_process(ran)
    if type(answer) is standin_waiter_line.WaiterRead:
        return (answer.report, answer.memory_bytes)
    if type(answer) is str:
        return answer
    raise RuntimeError(_NOT_PLACED)


def _build(target, image, build_dir, copies, keeper, outcomes):
    sources = (copies.harness, *copies.compiled_set)
    started = monotonic()
    built = cuda_check.build_in_container(
        outcomes,
        image,
        build_dir,
        (
            *target.flags,
            *(standin_check.in_container(source) for source in sources),
            *target.trailing_flags,
            "-o",
            _TIMING_EXECUTABLE,
        ),
        target.build_time_limit_s,
        keeper=keeper,
        executable=TIMING_EXECUTABLE_NAME,
        missing=_NO_TIMING_EXECUTABLE,
    )
    if built is not standin_answer.GO_ON:
        return built
    left = target.build_time_limit_s - (monotonic() - started)
    if not left > 0:
        return "build_time_limit"
    return cuda_check.build_in_container(
        outcomes,
        image,
        build_dir,
        (
            *target.waiter_flags,
            standin_check.in_container(standin_run.WAITER_SOURCE.name),
            "-o",
            _WAITER_EXECUTABLE,
        ),
        left,
        keeper=None,
        executable=WAITER_EXECUTABLE_NAME,
        missing=_NO_WAITER,
    )
