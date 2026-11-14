"""The ``cuda_gpu`` operation of ``sim.run`` and ``board.run`` on the host executor (ADR-0207 decision 9, slice 4).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md``
decision 8 has both points of ``cuda_gpu`` run the same local GPU run
(HQ-0095 (2) (a)): :func:`operation_for` builds one operation that serves
both run tools, called as :func:`hilclaw.run_operation.ask` calls an
operation, with five positional things: the request, the hw_profile, the
timing parameters, the output path and the log keeper. The results of the two
tools differ only by the existing ``step`` values (ADR-0194 decision 5); the
operation adds no member. In the order of :mod:`hilclaw.cuda_check` it:

1. checks its own arguments and computes the eight arguments of the timing
   driver (:func:`hilclaw.harness.timing.driver_arguments`) and the time
   limit of the timing process
   (:func:`hilclaw.standin_settings.timing_process_time_limit_s` with the
   target's cap);
2. runs the device check (:func:`hilclaw.cuda_check.confirm_device`):
   ``device_unavailable`` before any build and any process of the attempt
   (ADR-0207 decision 6);
3. asks the selection ``sources`` for the kernel's files
   (:func:`hilclaw.cuda_check.select_sources`);
4. makes the build directory of the call, removed on every path;
5. builds :data:`hilclaw.harness.cuda_programs.TIMING_DRIVER_SOURCE`, then the
   selected files, into :data:`TIMING_EXECUTABLE_NAME` with ``nvcc`` at the
   target's flags (:func:`hilclaw.cuda_check.build_executable`), handing the
   keeper the compiler's log of that build (ADR-0108);
6. runs the timing process on the host (the command of
   :func:`hilclaw.cuda_adapter.assemble_timing`, :func:`hilclaw.local_run.run`)
   and returns what :func:`hilclaw.vendor_adapter.measure` gives: the pair
   ``(report, memory_bytes)`` after status 0, the form (A) of
   :mod:`hilclaw.run_operation`, or ``"time_limit"`` or ``"exit_status"``.

The timing boundary is ADR-0194 decision 4 as the timing driver implements it
(transfers outside the interval). ``memory_bytes`` is the host process's
figure, :func:`hilclaw.harness.memory_ceiling.figure` of the process's
``max_rss`` (ADR-0052), as :mod:`hilclaw.harness.timing` takes it; no GPU
memory figure is reported (HQ-0090). The unit of the report is ``ns`` (the
target's ``units_per_ns`` 1). The waiter of ADR-0145 is not built: the host
executor reads the process's usage itself. A non-zero status or an incomplete
report of the attempt's process is never a tool failure; a device lost after
the check went on is that process's ``"exit_status"``.

**The kernel's files are the caller's** and **the host executor is
test-only**, as in :mod:`hilclaw.cuda_check`: which files of an attempt's
``output/`` a CUDA kernel is stays HQ-0104's question, ``sources`` is given
by name with no default, :func:`hilclaw.check_definition.default_table` is
not changed (a call about ``cuda_gpu`` through the default registry is
``no_backend``), and slice 5 moves the build and the process into containers
(NFR-4).

Before anything is started, :class:`TypeError` is raised for timing
parameters that are not exactly a
:class:`hilclaw.run_parameters.TimingParameters` (a bf16 run is no run of
this contract) or a keeper that is not exactly a
:class:`hilclaw.build_log.LogKeeper`, and what the functions of step 1 raise
for their values passes. A program the run cannot start is
``executable_unstartable`` (:func:`hilclaw.vendor_adapter.interpret_run`).
"""

import sys

from hilclaw import (
    cuda_adapter,
    cuda_check,
    local_run,
    run_parameters,
    standin_settings,
    tools,
    vendor_adapter,
)
from hilclaw.harness import cuda_programs, memory_ceiling, timing

TIMING_EXECUTABLE_NAME = "timing"
BUILD_DIR_PREFIX = "hilclaw-cuda-run-"


def operation_for(target, *, sources):
    """Return the ``sim.run`` and ``board.run`` operation of ``target`` on the host executor.

    ``target`` and ``sources`` as :func:`hilclaw.cuda_check.operation_for`,
    with the same refusals. The operation takes the five positional
    arguments of :func:`hilclaw.run_operation.ask`, reads neither the
    request nor the hw_profile, and returns ``(report, memory_bytes)`` as a
    plain ``tuple`` (``memory_bytes`` an ``int`` or ``None``) or one of
    ``"build_time_limit"``, ``"build_exit_status"``, ``"time_limit"`` and
    ``"exit_status"``; it raises :class:`hilclaw.tools.ToolFailure` of a
    backend kind of :mod:`hilclaw.run_failure`, ``device_unavailable`` first
    of all. What no row places, and every request to end, passes as it is.
    """
    cuda_check.check_target(target)
    cuda_check.check_sources(sources)

    def operation(request, hw_profile, parameters, output_path, keeper, /):
        limit = _checked(parameters, keeper, target.process_time_limit_cap_s)
        return cuda_check.carry_out(
            target,
            sources,
            output_path,
            keeper,
            program=cuda_programs.TIMING_DRIVER_SOURCE,
            executable_name=TIMING_EXECUTABLE_NAME,
            prefix=BUILD_DIR_PREFIX,
            run=lambda executable: _time(target, executable, parameters, limit),
        )

    return operation


def _checked(parameters, keeper, cap_s):
    if type(parameters) is not run_parameters.TimingParameters:
        raise TypeError(
            f"parameters must be TimingParameters, not {type(parameters).__name__}"
        )
    cuda_check.check_keeper(keeper)
    timing.driver_arguments(**parameters._asdict())
    m, k, n, n_max, _, _ = parameters
    return standin_settings.timing_process_time_limit_s(m, k, n, n_max, cap_s)


def _time(target, executable, parameters, limit):
    call = cuda_adapter.assemble_timing(target, executable, parameters, timeout_s=limit)
    try:
        result = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    except Exception as error:
        outcome = vendor_adapter.interpret_run(error, call.command[0])
        if outcome is None:
            raise
        raise tools.ToolFailure(outcome.kind, outcome.message) from None
    figure = memory_ceiling.figure(result.max_rss, sys.platform)
    return vendor_adapter.measure(result, figure)
