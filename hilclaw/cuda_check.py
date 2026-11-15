"""The ``cuda_gpu`` operation of ``correctness.check`` in containers (ADR-0207 decision 9, slice 5).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`` gives
the target ``cuda_gpu`` the fp32 ``gemm`` contract in the language ``cuda``
(decision 4), a device check before the attempt's process (decision 6) and
containers of one image given the GPU with ``--gpus all`` (decision 7).
:func:`operation_for` builds the operation of ``correctness.check`` of that
target, called as :func:`hilclaw.check_operation.ask` calls an operation,
with five positional things: the request, the hw_profile, the check
parameters, the output path and the log keeper. In the order of ADR-0056
decision 7 and the Walk-through of ADR-0168 it:

1. checks its own arguments (as :mod:`hilclaw.standin_check` does for fp32
   ``gemm``) and computes the process's arguments ``m k n draws seed``
   (ADR-0017 decision 2) and its time limit
   (:func:`hilclaw.standin_settings.verification_process_time_limit_s` with
   the target's cap);
2. reads the image named by :data:`hilclaw.cuda_image.ENV_IMAGE`
   (:func:`container_image`): none named is ``compiler_unavailable`` (C1), a
   refused value the same (C2);
3. makes the build directory of the call
   (:func:`hilclaw.standin_check.make_build_dir`; S3);
4. runs the device check in a probe container of that image with
   ``--gpus all`` (:func:`confirm_device`,
   :func:`hilclaw.cuda_adapter.check_device_in_container`): everything but a
   usable device is the tool failure ``device_unavailable`` (decision 6),
   raised before any build and any process of the attempt;
5. asks the selection ``sources`` for the kernel's files
   (:func:`select_sources`) and copies them below
   :data:`hilclaw.standin_copies.KERNEL_DIR` with
   :data:`hilclaw.harness.cuda_programs.VERIFICATION_PROGRAM_SOURCE` beside
   them (:func:`place_sources`; C12, C13);
6. builds the program, then the copies in the selection's order, into
   :data:`EXECUTABLE_NAME` with ``nvcc`` at the target's flags and trailing
   flags in a build container with ``--gpus all`` (:func:`build_in_container`;
   ``-arch=native`` needs the GPU), within the target's build time limit; the
   keeper is handed the compiler's log as ADR-0169 decisions 2 and 3 say, and
   the build is answered by ADR-0168 (C5 to C7, C10, S9);
7. runs the executable with the process's arguments in a process container
   with ``--gpus all`` (:func:`run_process`), with the target's
   ``memory_limit_bytes`` (``None`` for ``cuda_gpu``: no bound) and the
   limit of step 1, and returns its standard output, as ``bytes``, after
   status 0; a time limit is ``"time_limit"`` and any other status, 125 to
   127 included, ``"exit_status"`` (C8). The tool function judges the report
   (``hilclaw.harness.verification``; the oracle of HQ-0096 (2) (a)).

The build directory is removed before the operation returns or raises, where
every container of the call allows it, the probe's included
(:func:`hilclaw.standin_check.carry_out`; ADR-0168 decision 5). Every
:class:`hilclaw.standin_answer.Failure` is raised as
:class:`hilclaw.tools.ToolFailure` with its kind and message; what no row
places and every request to end passes as it is. A non-zero status or an
incomplete report of the attempt's process is never a tool failure
(ADR-0110 decision 3): a device lost after the probe went on is that
process's ``"exit_status"`` (decision 6).

**The kernel's files are the caller's.** Which files of an attempt's
``output/`` a CUDA kernel is (a ``.cu`` name) is HQ-0104's question, which
this module does not answer: :func:`hilclaw.kernel_source.read_compiled_set`
admits no ``.cu`` name and is not used here. ``sources`` is a callable given
by name with no default; it is called with the output path and returns the
paths of the kernel's source files, which are copied into the build directory
(:func:`hilclaw.standin_copies.place_selected_copies`) and handed to ``nvcc``
there. A test gives a selection of a test-placed fixture; slice 6 gives the
one HQ-0104's answer provides.

**Only in containers.** The build and the process run only in containers of
the named image (NFR-4; decision 7); nothing of the attempt runs on the host.
:func:`hilclaw.check_definition.default_table` holds no ``cuda_gpu`` entry
(slice 6), so a call about ``cuda_gpu`` through the default registry is
``no_backend``.

Choices that are this module's own and no rule of a record:

* The device query is given :data:`DEVICE_QUERY_TIMEOUT_S`, its forced
  removal :data:`hilclaw.standin_check.REMOVAL_TIMEOUT_S`.
* ``sources`` returns a ``tuple`` or ``list``; an empty one is
  ``no_kernel_source`` (S1), a path that is not a regular file (a link
  included) ``build_input_missing`` (S5), and an :class:`Exception` it raises
  ``kernel_source_unreadable`` (S2). Another value, or an element that is no
  ``str`` or :class:`os.PathLike`, raises :class:`TypeError`.
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
:func:`container_image`, :func:`confirm_device`, :func:`select_sources`,
:func:`place_sources`, :func:`build_in_container` and :func:`run_process`
are the steps this operation shares with the ``cuda_gpu`` operation of the
run tools, :func:`hilclaw.cuda_run.operation_for`.
"""

import os
import stat

from hilclaw import (
    build_log,
    check_failure,
    check_parameters,
    cuda_adapter,
    cuda_image,
    standin_answer,
    standin_check,
    standin_copies,
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
_EXECUTABLE = standin_check.in_container(EXECUTABLE_NAME)
_IMAGE_REFUSED = "the container image named is refused"
_SELECTION_FAILED = "the selection of the kernel's source files failed"
_NO_SOURCE = "the selection named no kernel source file"
_NOT_REGULAR = "a selected kernel source file is not a regular file"
_NO_EXECUTABLE = standin_answer.Failure(
    check_failure.KIND_BUILD_OUTPUT_MISSING,
    "the build ended with status 0 and left no executable",
)


def operation_for(target, *, sources):
    """Return the ``correctness.check`` operation of ``target`` in containers.

    ``target`` is exactly a :class:`hilclaw.targets.Target` (for
    ``cuda_gpu``, ``targets.target(targets.CUDA_GPU)``); its flags, trailing
    flags, build time limit, process time-limit cap and memory limit are the
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
    :mod:`hilclaw.check_failure`, ``device_unavailable`` before any build.
    What no row places, and every request to end, passes as it is.
    """
    check_target(target)
    check_sources(sources)

    def operation(request, hw_profile, parameters, output_path, keeper, /):
        arguments, limit = _checked(parameters, keeper, target.process_time_limit_cap_s)
        image = container_image()
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


def container_image():
    """Return the image reference :func:`hilclaw.cuda_image.read_image` gives (C1, C2).

    Raises :class:`hilclaw.tools.ToolFailure` ``compiler_unavailable`` where
    no image is named (the answer of
    :func:`hilclaw.standin_answer.read_image_value`) or the value is refused
    (:class:`hilclaw.cuda_image.ImageRefusedError`); lets pass anything else.
    """
    try:
        value = cuda_image.read_image()
    except cuda_image.ImageRefusedError:
        raise tools.ToolFailure(
            check_failure.KIND_COMPILER_UNAVAILABLE, _IMAGE_REFUSED
        ) from None
    answer = standin_answer.read_image_value(value)
    if answer is not standin_answer.GO_ON:
        raise tools.ToolFailure(answer.kind, answer.message)
    return value


def confirm_device(image, build_dir, outcomes):
    """Run the device check of ADR-0207 decision 6 in a probe container; return ``None`` for a usable device.

    :func:`hilclaw.cuda_adapter.check_device_in_container` with ``image``,
    ``build_dir``, :data:`DEVICE_QUERY_TIMEOUT_S` and
    :data:`hilclaw.standin_check.REMOVAL_TIMEOUT_S`; what its container gave
    is appended to ``outcomes``. Raises
    :class:`hilclaw.standin_check.Answered` with the
    :class:`hilclaw.standin_answer.Failure` ``device_unavailable`` and the
    probe's message for every outcome but a usable device; lets pass what
    that function lets pass.
    """
    outcome = cuda_adapter.check_device_in_container(
        image,
        build_dir,
        timeout_s=DEVICE_QUERY_TIMEOUT_S,
        removal_timeout_s=standin_check.REMOVAL_TIMEOUT_S,
        outcomes=outcomes,
    )
    if outcome.form != vendor_adapter.GO_ON:
        raise standin_check.Answered(
            standin_answer.Failure(outcome.kind, outcome.message)
        )


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


def place_sources(sources, output_path, program, build_dir, further=()):
    """Copy the selected kernel files, ``program`` and ``further`` into ``build_dir``; return the :class:`hilclaw.standin_copies.Copies`.

    The files are those :func:`select_sources` gives for ``sources`` and
    ``output_path`` (whose answers pass), copied with ``program`` by
    :func:`hilclaw.standin_copies.place_selected_copies`; each harness
    program of ``further`` is then copied beside ``program``
    (:func:`hilclaw.standin_copies.place_harness_copy`). What a copy raises
    is placed by :func:`hilclaw.standin_answer.place_error` at
    :data:`hilclaw.standin_answer.COPIES` and raised as
    :class:`hilclaw.standin_check.Answered`; what no row places passes.
    """
    selected = select_sources(sources, output_path)
    try:
        copies = standin_copies.place_selected_copies(selected, program, build_dir)
        for harness in further:
            standin_copies.place_harness_copy(harness, build_dir)
    except Exception as error:
        answer = standin_answer.place_error(error, standin_answer.COPIES)
        if type(answer) is not standin_answer.Failure:
            raise
        raise standin_check.Answered(answer) from None
    return copies


def build_in_container(
    outcomes, image, build_dir, command, timeout_s, *, keeper, executable, missing
):
    """Run ``nvcc`` with ``command`` in one build container with ``--gpus all`` and read it.

    :func:`hilclaw.standin_check.run_build` with the compiler
    :data:`hilclaw.cuda_adapter.PROGRAM` and ``gpus`` true (ADR-0207
    decision 7), its arguments otherwise as given, and its answers.
    """
    return standin_check.run_build(
        outcomes,
        image,
        build_dir,
        command,
        timeout_s,
        keeper=keeper,
        executable=executable,
        missing=missing,
        compiler=cuda_adapter.PROGRAM,
        gpus=True,
    )


def run_process(
    outcomes, image, build_dir, program, arguments, timeout_s, memory_limit_bytes
):
    """Run ``program`` in one process container with ``--gpus all``; return what :func:`hilclaw.standin_check.run_container` gives.

    The step is :data:`hilclaw.standin_answer.PROCESS`; ``memory_limit_bytes``
    is handed on as it is (ADR-0193 decision 4).
    """
    return standin_check.run_container(
        outcomes,
        standin_answer.PROCESS,
        image,
        build_dir,
        program,
        arguments,
        timeout_s,
        memory_limit_bytes=memory_limit_bytes,
        gpus=True,
    )


def _carry_out(
    target, sources, image, build_dir, output_path, keeper, arguments, limit, outcomes
):
    confirm_device(image, build_dir, outcomes)
    copies = place_sources(
        sources, output_path, cuda_programs.VERIFICATION_PROGRAM_SOURCE, build_dir
    )
    built = build_in_container(
        outcomes,
        image,
        build_dir,
        (
            *target.flags,
            *(
                standin_check.in_container(source)
                for source in (copies.harness, *copies.compiled_set)
            ),
            *target.trailing_flags,
            "-o",
            _EXECUTABLE,
        ),
        target.build_time_limit_s,
        keeper=keeper,
        executable=EXECUTABLE_NAME,
        missing=_NO_EXECUTABLE,
    )
    if built is not standin_answer.GO_ON:
        return built
    ran = run_process(
        outcomes,
        image,
        build_dir,
        _EXECUTABLE,
        arguments,
        limit,
        target.memory_limit_bytes,
    )
    if type(ran) is str:
        return ran
    answer = standin_answer.read_process(ran)
    if answer is standin_answer.GO_ON:
        return ran.stdout
    return standin_check.settled(answer)
