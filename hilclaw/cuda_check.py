"""The ``cuda_gpu`` operation of ``correctness.check`` on the host executor (ADR-0207 decision 9, slice 4).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`` gives
the target ``cuda_gpu`` the fp32 ``gemm`` contract in the language ``cuda``
(decision 4) and a device check before the attempt's process (decision 6).
:func:`operation_for` builds the operation of ``correctness.check`` of that
target, called as :func:`hilclaw.check_operation.ask` calls an operation,
with five positional things: the request, the hw_profile, the check
parameters, the output path and the log keeper. In the order of ADR-0056
decision 7 it:

1. checks its own arguments (as :mod:`hilclaw.standin_check` does for fp32
   ``gemm``) and computes the process's arguments ``m k n draws seed``
   (ADR-0017 decision 2) and its time limit
   (:func:`hilclaw.standin_settings.verification_process_time_limit_s` with
   the target's cap);
2. runs the device check, :func:`confirm_device`
   (:func:`hilclaw.cuda_adapter.check_device`): no usable device, an absent
   query program and an unreadable query are the tool failure
   ``device_unavailable`` (ADR-0207 decision 6), raised before any build and
   before any process of the attempt;
3. asks the selection ``sources`` for the kernel's files
   (:func:`select_sources`);
4. makes the build directory of the call
   (:func:`hilclaw.standin_check.make_build_dir`), removed by
   :func:`hilclaw.standin_check.remove_build_dir` before the operation
   returns or raises, on every path;
5. builds :data:`hilclaw.harness.cuda_programs.VERIFICATION_PROGRAM_SOURCE`,
   then the selected files, into :data:`EXECUTABLE_NAME` in that directory
   with ``nvcc`` at the target's flags (:func:`build_executable`), hands the
   keeper the compiler's log where ADR-0078 decision 2 keeps it, and answers
   the build by the rows of ADR-0060 decision 4 as
   :func:`hilclaw.check_build.read_build` and
   :func:`hilclaw.check_build.place_error` give them (no new kind);
6. runs the executable with the process's arguments within the limit
   (:func:`hilclaw.cuda_adapter.run`) and returns its standard output, as
   ``bytes``, after status 0; a time limit is ``"time_limit"`` and any other
   status ``"exit_status"``. The tool function judges the report
   (``hilclaw.harness.verification``; the oracle of HQ-0096 (2) (a)).

A non-zero status or an incomplete report of the attempt's process is never a
tool failure (ADR-0110 decision 3): a device lost after the check went on is
that process's ``"exit_status"`` (ADR-0207 decision 6).

**The kernel's files are the caller's.** Which files of an attempt's
``output/`` a CUDA kernel is (a ``.cu`` name) is HQ-0104's question, which
this module does not answer: :func:`hilclaw.kernel_source.read_compiled_set`
admits no ``.cu`` name and is not used here. ``sources`` is a callable given
by name with no default; it is called with the output path and returns the
paths of the kernel's source files, which are handed to ``nvcc`` where they
are, after the program. A test gives a selection of a test-placed fixture;
slice 6 gives the one HQ-0104's answer provides.

**The host executor is test-only.** The build and the process run on the host
through :func:`hilclaw.clang_build.build` and :func:`hilclaw.local_run.run`,
outside any container. The runtime builds and runs kernels only in containers
(NFR-4), so :func:`hilclaw.check_definition.default_table` holds no ``cuda_gpu``
entry and a call about ``cuda_gpu`` through the default registry is
``no_backend``; slice 5 moves the build and the process into containers.

Choices that are this module's own and no rule of a record:

* The device query is given :data:`DEVICE_QUERY_TIMEOUT_S`.
* ``sources`` returns a ``tuple`` or ``list``; an empty one is
  ``no_kernel_source`` (S1), a path that is not a regular file (a link
  included) ``build_input_missing`` (S5), and an :class:`Exception` it raises
  ``kernel_source_unreadable`` (S2). Another value, or an element that is no
  ``str`` or :class:`os.PathLike`, raises :class:`TypeError`.
* A kind a build row gives is raised with a fixed message of this module,
  which shows no path or byte of the log.
* No candidate build (ADR-0198 decision 6) is read: the target's flags are
  the build's.
* Before anything is started, :class:`TypeError` is raised for check
  parameters that are not exactly a
  :class:`hilclaw.check_parameters.CheckParameters` (a bf16 check is no
  check of this contract) or a keeper that is not exactly a
  :class:`hilclaw.build_log.LogKeeper`, and :class:`TypeError` or
  :class:`ValueError` for a value the process limit refuses or a seed that is
  not an ``int`` from 0 to below ``2**64``.

:func:`check_target`, :func:`check_sources`, :func:`check_keeper`,
:func:`confirm_device`, :func:`select_sources`, :func:`build_executable` and
:func:`carry_out` are the steps this operation shares with the ``cuda_gpu``
operation of the run tools, :func:`hilclaw.cuda_run.operation_for`.
"""

import os
import stat

from hilclaw import (
    build_log,
    check_build,
    check_failure,
    check_parameters,
    clang_build,
    cuda_adapter,
    standin_check,
    standin_settings,
    targets,
    tools,
    vendor_adapter,
)
from hilclaw.harness import cuda_programs

#: Time limit in seconds of the device query of :func:`confirm_device`.
DEVICE_QUERY_TIMEOUT_S = 30

EXECUTABLE_NAME = "verification"
BUILD_DIR_PREFIX = "hilclaw-cuda-check-"

_SEED_LIMIT = 2**64
_CONDITIONS = ("build_time_limit", "build_exit_status")
_SELECTION_FAILED = "the selection of the kernel's source files failed"
_NO_SOURCE = "the selection named no kernel source file"
_NOT_REGULAR = "a selected kernel source file is not a regular file"
_BUILD_MESSAGES = {
    check_failure.KIND_BUILD_DIRECTORY_UNUSABLE: "the build directory could not be used",
    check_failure.KIND_SETTINGS_REFUSED: "a setting of the build is refused",
    check_failure.KIND_BUILD_INPUT_MISSING: "an input of the build is not a regular file",
    check_failure.KIND_COMPILER_UNAVAILABLE: "the compiler was not found or could not be started",
    check_failure.KIND_BUILD_OUTPUT_MISSING: "the build ended with status 0 and left no executable",
}
_NO_STATUS = "the build is not ok, did not time out and has no status"


def operation_for(target, *, sources):
    """Return the ``correctness.check`` operation of ``target`` on the host executor.

    ``target`` is exactly a :class:`hilclaw.targets.Target` (for
    ``cuda_gpu``, ``targets.target(targets.CUDA_GPU)``); its flags, trailing
    flags, ``env``, build time limit and process time-limit cap are the
    call's. ``sources`` is the selection of the kernel's source files, a
    callable of the output path, required and keyword-only (the module
    docstring). Raises :class:`TypeError` for a ``target`` that is not
    exactly a ``Target`` or a ``sources`` that is not callable.

    The operation takes the five positional arguments of
    :func:`hilclaw.check_operation.ask` and reads neither the request nor
    the hw_profile. It returns the verification process's standard output
    as ``bytes`` after status 0, or one of ``"build_time_limit"``,
    ``"build_exit_status"``, ``"time_limit"`` and ``"exit_status"``, and
    raises :class:`hilclaw.tools.ToolFailure` of a backend kind of
    :mod:`hilclaw.check_failure`, ``device_unavailable`` first of all. What
    no row places, and every request to end, passes as it is.
    """
    check_target(target)
    check_sources(sources)

    def operation(request, hw_profile, parameters, output_path, keeper, /):
        arguments, limit = _checked(parameters, keeper, target.process_time_limit_cap_s)
        return carry_out(
            target,
            sources,
            output_path,
            keeper,
            program=cuda_programs.VERIFICATION_PROGRAM_SOURCE,
            executable_name=EXECUTABLE_NAME,
            prefix=BUILD_DIR_PREFIX,
            run=lambda executable: _verify(target, executable, arguments, limit),
        )

    return operation


def check_target(target):
    """Raise :class:`TypeError` unless ``target`` is exactly a :class:`hilclaw.targets.Target`."""
    if type(target) is not targets.Target:
        raise TypeError(f"target must be a Target, not {type(target).__name__}")


def check_sources(sources):
    """Raise :class:`TypeError` unless ``sources`` is callable."""
    if not callable(sources):
        raise TypeError(
            f"sources must be a callable selection, not {type(sources).__name__}"
        )


def check_keeper(keeper):
    """Raise :class:`TypeError` unless ``keeper`` is exactly a :class:`hilclaw.build_log.LogKeeper`."""
    if type(keeper) is not build_log.LogKeeper:
        raise TypeError(f"keeper must be a LogKeeper, not {type(keeper).__name__}")


def _checked(parameters, keeper, cap_s):
    if type(parameters) is not check_parameters.CheckParameters:
        raise TypeError(
            f"parameters must be CheckParameters, not {type(parameters).__name__}"
        )
    check_keeper(keeper)
    seed, draws, m, k, n = parameters
    limit = standin_settings.verification_process_time_limit_s(m, k, n, draws, cap_s)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError(f"seed must be an int, not {type(seed).__name__}")
    if not 0 <= seed < _SEED_LIMIT:
        raise ValueError("seed must be an int from 0 to below 2**64")
    return tuple(str(int(value)) for value in (m, k, n, draws, seed)), limit


def confirm_device():
    """Run the device check of ADR-0207 decision 6; return ``None`` for a usable device.

    Raises :class:`hilclaw.tools.ToolFailure` ``device_unavailable`` with the
    probe's message for every other outcome of
    :func:`hilclaw.cuda_adapter.check_device`, which is given
    :data:`DEVICE_QUERY_TIMEOUT_S`. An exception that function lets pass
    passes as it is.
    """
    outcome = cuda_adapter.check_device(timeout_s=DEVICE_QUERY_TIMEOUT_S)
    if outcome.form != vendor_adapter.GO_ON:
        raise tools.ToolFailure(outcome.kind, outcome.message)


def select_sources(sources, output_path):
    """Return the kernel's source files ``sources(output_path)`` names, as a ``tuple``.

    Raises :class:`hilclaw.tools.ToolFailure` ``kernel_source_unreadable``
    when the selection raises an :class:`Exception`, ``no_kernel_source``
    when it names no file and ``build_input_missing`` when a path it names is
    not a regular file (:func:`os.lstat`, so a link is none); raises
    :class:`TypeError` when it returns no ``tuple`` or ``list`` or an element
    that is no ``str`` or :class:`os.PathLike`.
    """
    try:
        selected = sources(output_path)
    except Exception:  # noqa: BLE001
        raise tools.ToolFailure(
            check_failure.KIND_KERNEL_SOURCE_UNREADABLE, _SELECTION_FAILED
        ) from None
    if type(selected) not in (tuple, list):
        raise TypeError(
            f"the selection must return a tuple or list, not {type(selected).__name__}"
        )
    for path in selected:
        if not isinstance(path, (str, os.PathLike)):
            raise TypeError(
                f"a selected path must be str or os.PathLike, not {type(path).__name__}"
            )
    if not selected:
        raise tools.ToolFailure(check_failure.KIND_NO_KERNEL_SOURCE, _NO_SOURCE)
    if not all(_regular_file(path) for path in selected):
        raise tools.ToolFailure(check_failure.KIND_BUILD_INPUT_MISSING, _NOT_REGULAR)
    return tuple(selected)


def _regular_file(path):
    try:
        return stat.S_ISREG(os.lstat(path).st_mode)
    except (OSError, ValueError):
        return False


def build_executable(target, sources, executable, keeper):
    """Build ``sources`` into ``executable`` with ``nvcc`` at ``target``; return ``None`` when it was built.

    The call is :func:`hilclaw.cuda_adapter.assemble_build`'s, carried out by
    :func:`hilclaw.clang_build.build`. Where the compiler ran and ended, the
    keeper is handed its log before anything else is read (ADR-0078
    decision 2): that of a returned :class:`hilclaw.clang_build.BuildResult`,
    and for an error a row places, that of the build it carries as ``result``
    or the ``log`` of a :class:`hilclaw.clang_build.CompilerRunError`. Returns ``"build_time_limit"`` or
    ``"build_exit_status"``; raises :class:`hilclaw.tools.ToolFailure` of the
    kind :func:`hilclaw.check_build.read_build` or
    :func:`hilclaw.check_build.place_error` gives (ADR-0060 decision 4) with a
    fixed message. An error no row places passes as it is, and a returned
    build no row holds raises :class:`RuntimeError`.
    """
    call = cuda_adapter.assemble_build(target, sources, executable)
    try:
        result = clang_build.build(
            call.sources,
            call.output,
            timeout_s=call.timeout_s,
            flags=call.flags,
            trailing_flags=call.trailing_flags,
            compiler=call.compiler,
            env=call.env,
        )
    except Exception as error:
        answer = check_build.place_error(error)
        if answer is None:
            raise
        log = _carried_log(error)
        if log is not None:
            keeper.hand_over(log)
    else:
        keeper.hand_over(result.log)
        answer = check_build.read_build(result)
        if answer is None:
            raise RuntimeError(_NO_STATUS)
    if answer is check_build.BUILT:
        return None
    if answer in _CONDITIONS:
        return answer
    raise tools.ToolFailure(answer, _BUILD_MESSAGES[answer])


def _carried_log(error):
    carried = getattr(error, "result", None)
    if type(carried) is clang_build.BuildResult:
        return carried.log
    if isinstance(error, clang_build.CompilerRunError) and type(error.log) is str:
        return error.log
    return None


def carry_out(
    target, sources, output_path, keeper, *, program, executable_name, prefix, run
):
    """Carry out the device check, the selection, the build and ``run`` in a build directory of its own.

    In order: :func:`confirm_device`; :func:`select_sources`; a build
    directory with ``prefix`` (:func:`hilclaw.standin_check.make_build_dir`);
    :func:`build_executable` of ``program`` followed by the selected files
    into ``executable_name`` there; then ``run(executable)`` with the
    executable's path, whose answer is returned. A condition of the build is
    returned without ``run``. The build directory is removed
    (:func:`hilclaw.standin_check.remove_build_dir`) before this returns or
    raises.
    """
    confirm_device()
    selected = select_sources(sources, output_path)
    build_dir = standin_check.make_build_dir(prefix)
    try:
        executable = os.path.join(build_dir, executable_name)
        built = build_executable(target, (program, *selected), executable, keeper)
        if built is not None:
            return built
        return run(executable)
    finally:
        standin_check.remove_build_dir(build_dir)


def _verify(target, executable, arguments, limit):
    outcome = cuda_adapter.run(target, executable, arguments, timeout_s=limit)
    if outcome.form == vendor_adapter.GO_ON:
        return outcome.carried
    if outcome.form == vendor_adapter.BROKEN:
        return outcome.condition
    raise tools.ToolFailure(outcome.kind, outcome.message)
