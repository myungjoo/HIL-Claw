"""Container path of the model program: copies, builds and one run, each build and the run in a new container.

``ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md`` is the
rule (code slice 3); a decision cited by its number alone is one of that
record. :func:`execute` does what :func:`hilclaw.model_execute.execute` does
for the model program of ADR-0153 slice 1, with every build and the one process
carried out in a new container of ADR-0144 through
:func:`hilclaw.standin_container.run_in_container`, whose properties (ADR-0144
decision 6) it takes unchanged (decision 2). It takes these steps, in order:

1. The image named by :data:`hilclaw.standin_image.ENV_IMAGE`, read with
   :func:`hilclaw.standin_image.read_image` (decision 3). None named, or a
   refused value, is the outcome **container unavailable** (decision 8) and
   nothing is made or started.
2. A build directory of its own, made and removed as
   :func:`hilclaw.model_execute.execute` makes and removes one, with the prefix
   :data:`PREFIX`. Into it, by copy (decision 4): the program's source
   :data:`hilclaw.model_build.PROGRAM_SOURCE` under its basename, and the source
   files of kernel ``i`` then its own headers under their basenames in the
   sub-directory ``kernel-<i>``, which holds nothing else. Two of them of one
   basename are a :class:`hilclaw.standin_copies.CopyError` of
   :data:`hilclaw.standin_copies.ENTRY_EXISTS`.
3. One build container per kernel, in index order:
   :data:`hilclaw.standin_check.COMPILER` with the kernel's ``flags``,
   :data:`hilclaw.model_build.LIBRARY_FLAGS`, the copies of its sources (none of
   its headers) and ``-o`` the library ``kernel-<i>.so`` in the build directory;
   then one for the program: the compiler with ``program_flags``,
   ``hilclaw.model_build.PROGRAM_DTYPE_FLAGS[dtype]``, the program's copy,
   ``program_trailing_flags`` and ``-o`` the executable ``model_program``. Every
   path handed in is the absolute path inside the container
   (:func:`hilclaw.standin_check.in_container`).
4. The input file of :func:`hilclaw.model_run.encode_input`, written as
   ``input.bin`` into the build directory on the host, and one process container
   that runs the executable with the input file and the libraries, their paths
   inside the container. Its standard output is the report, read with
   :func:`hilclaw.model_run.parse_report`.

Outcomes (decision 8), in a :class:`ModelContainerExecution`:

- **Container unavailable**
  (:class:`hilclaw.model_forward_container.Unavailable`): one of
  :data:`hilclaw.model_forward_container.REASONS`, a build container that ended
  with 125, 126 or 127 among them. Nothing after it is started.
- **Build failed** (:class:`hilclaw.model_execute.BuildFailed`): the first build
  container that timed out, ended with another non-zero status, or ended with 0
  and left no regular file at its output. Its ``kernel`` is the index, or
  ``None`` for the program.
- **Run failed** (:class:`ContainerRun` with ``failed`` set): the process
  container timed out (:attr:`hilclaw.model_run.RunFailed.TIMEOUT`), ended with
  a status other than 0 — 125 to 127 included, the program's for a process —
  (``EXIT_STATUS``), or left no complete report (``REPORT_FORM``).

A forced removal is given :data:`hilclaw.standin_check.REMOVAL_TIMEOUT_S`
(decision 5). The build directory is removed only where
:func:`hilclaw.standin_answer.build_dir_removable` is true of every container
(ADR-0168 decision 5); otherwise it is left and ``removed`` is false.

Raised before anything is made, ``dtype`` first: :class:`TypeError` or
:class:`ValueError` for ``dtype``, ``kernels`` and ``calls`` as
:func:`hilclaw.model_execute.execute` raises them, a call index not below
``len(kernels)`` among them; :class:`TypeError` for a kernel without
``headers``, for ``sources``, ``flags`` or ``headers`` that is not a ``tuple``
or ``list``, or for an item of them of the wrong type, each naming the kernel's
position; :class:`ValueError` for a kernel with no source or a path with a NUL
character; then :class:`TypeError` or :class:`ValueError` for ``keep_out`` and
``parent`` and for ``program_flags``, its item naming ``HILCLAW_MODEL_BF16``
included, as that function raises them; :class:`TypeError` for
``program_trailing_flags`` that is not a ``tuple`` or ``list`` of ``str``;
:class:`TypeError` or :class:`ValueError` for a ``build_timeout_s`` or
``run_timeout_s`` that is not a positive finite number; :class:`TypeError` for
an ``environ`` that is neither ``None`` nor a mapping. The :class:`OSError` of
making the directory is raised as it is. What the copies raise
(:class:`hilclaw.standin_copies.CopyError` among them), what
:func:`hilclaw.standin_container.run_in_container` raises apart from the two
errors that are **container unavailable** (any other :class:`OSError` among
them, ADR-0168 C14), and what the input's writing raises are passed on unchanged
after the directory was removed where it may be.

What this module does not do: it never builds or starts anything on the host
(ADR-0144 decision 4; decision 2) and has no fallback to it; it makes no binding
check and no fit check of a kernel to a call; it names no image and pulls,
installs or changes none; it gives no time limit a default and sets no resource
bound or memory figure (decisions 5, 6); it hands no variable of its own
environment into a container; it hands a kernel's headers to no compiler and
passes no include flag; it adds no ``-ldl``, which is the caller's
``program_trailing_flags``; it compares nothing, casts no array, and stores,
keeps or retries nothing.
"""

import os
import tempfile
from typing import NamedTuple

from hilclaw import (
    model_build,
    model_run,
    standin_check,
    standin_container,
    standin_copies,
)
from hilclaw.model_execute import (
    _INPUT_NAME,
    _PROGRAM_NAME,
    BuildFailed,
    _check_indices,
    _checked_dtype,
    _checked_keep_out,
    _checked_kernels,
    _checked_parent,
    _checked_program_flags,
    _path,
)
from hilclaw.model_forward_container import (
    Unavailable,
    _build,
    _build_kernels,
    _check_container_arguments,
    _container,
    _copy_kernel,
    _named_image,
    _settle,
    _Stop,
)

PREFIX = "hilclaw-model-container-"
"""Name prefix of every build directory this module makes."""


class ContainerRun(NamedTuple):
    """The process container: ``failed`` and ``outputs`` as in :class:`hilclaw.model_run.ModelProgramResult`.

    ``outputs`` holds one array per call, in call order, when ``failed`` is
    ``None``. ``container`` is the
    :class:`hilclaw.standin_container.ContainerResult` with its ``stdout``
    replaced by ``b""``.
    """

    failed: model_run.RunFailed | None
    outputs: tuple | None
    container: standin_container.ContainerResult


class ModelContainerExecution(NamedTuple):
    """Outcome of one :func:`execute` call.

    At most one of ``unavailable``, ``build_failed`` and a ``run`` whose
    ``failed`` is set holds an outcome; ``run`` is ``None`` unless the process
    container was started and ended. ``removed`` is ``None`` when no build
    directory was made, else whether it no longer exists afterwards.
    """

    unavailable: Unavailable | None
    build_failed: BuildFailed | None
    run: ContainerRun | None
    removed: bool | None


class _Kernel(NamedTuple):
    sources: tuple
    flags: tuple
    headers: tuple


def execute(
    kernels,
    calls,
    *,
    dtype,
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    environ=None,
    parent=None,
    keep_out=(),
):
    """Build ``kernels`` and the model program and run ``calls`` once, in containers; return a :class:`ModelContainerExecution`.

    ``dtype``, ``calls``, ``parent`` and ``keep_out`` are those of
    :func:`hilclaw.model_execute.execute`. ``kernels`` is a non-empty sequence
    of objects with the attributes ``sources``, ``flags`` and ``headers``, the
    attributes of :class:`hilclaw.model_binding.KernelReference`.
    ``build_timeout_s`` is the time limit of each build container and
    ``run_timeout_s`` that of the process container; neither has a default
    (decision 5). ``program_flags`` and ``program_trailing_flags`` are the
    program build's; whether the image's C library needs ``-ldl`` is the
    caller's. ``environ`` is the mapping the image is read from (``None``:
    :data:`os.environ`). See the module docstring for the steps, the outcomes
    and what is raised.
    """
    _checked_dtype(dtype)
    kernels = _container_kernels(kernels)
    shapes = model_run.output_shapes(calls, dtype=dtype)
    _check_indices(calls, kernels)
    roots = _checked_keep_out(keep_out)
    place = _checked_parent(parent, roots)
    _checked_program_flags(program_flags)
    _check_container_arguments(
        program_flags, program_trailing_flags, build_timeout_s, run_timeout_s, environ
    )
    image, unavailable = _named_image(environ)
    if unavailable is not None:
        return ModelContainerExecution(unavailable, None, None, None)
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    outcomes = []
    build_failed = run = None
    try:
        run = _build_and_run(
            image,
            directory,
            kernels,
            calls,
            shapes,
            outcomes,
            dtype=dtype,
            build_timeout_s=build_timeout_s,
            run_timeout_s=run_timeout_s,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
        )
    except _Stop as stop:
        if type(stop.outcome) is Unavailable:
            unavailable = stop.outcome
        else:
            build_failed = stop.outcome
    except BaseException:
        _settle(directory, roots, outcomes)
        raise
    removed = _settle(directory, roots, outcomes)
    return ModelContainerExecution(unavailable, build_failed, run, removed)


def _build_and_run(
    image,
    directory,
    kernels,
    calls,
    shapes,
    outcomes,
    *,
    dtype,
    build_timeout_s,
    run_timeout_s,
    program_flags,
    program_trailing_flags,
):
    program_source = standin_copies.place_harness_copy(
        model_build.PROGRAM_SOURCE, directory
    )
    copies = [
        _copy_kernel(directory, index, kernel) for index, kernel in enumerate(kernels)
    ]
    libraries = _build_kernels(
        image, directory, outcomes, kernels, copies, build_timeout_s
    )
    _build(
        image,
        directory,
        outcomes,
        (
            *program_flags,
            *model_build.PROGRAM_DTYPE_FLAGS[dtype],
            standin_check.in_container(program_source),
            *program_trailing_flags,
            "-o",
            standin_check.in_container(_PROGRAM_NAME),
        ),
        _PROGRAM_NAME,
        None,
        build_timeout_s,
    )
    data = model_run.encode_input(calls, dtype=dtype)
    with open(os.path.join(directory, _INPUT_NAME), "xb") as stream:
        stream.write(data)
    result = _container(
        image,
        directory,
        outcomes,
        standin_check.in_container(_PROGRAM_NAME),
        (standin_check.in_container(_INPUT_NAME), *libraries),
        run_timeout_s,
    )
    stdout = result.stdout
    result = result._replace(stdout=b"")
    if result.timed_out:
        return ContainerRun(model_run.RunFailed.TIMEOUT, None, result)
    if result.returncode != 0:
        return ContainerRun(model_run.RunFailed.EXIT_STATUS, None, result)
    outputs = model_run.parse_report(stdout, shapes, dtype=dtype)
    if outputs is None:
        return ContainerRun(model_run.RunFailed.REPORT_FORM, None, result)
    return ContainerRun(None, outputs, result)


def _container_kernels(kernels):
    kernels = _checked_kernels(kernels)
    checked = []
    for position, kernel in enumerate(kernels):
        name = f"kernels[{position}]"
        if not hasattr(kernel, "headers"):
            raise TypeError(f"{name}: has no attribute 'headers'")
        for attribute in ("sources", "flags", "headers"):
            if not isinstance(getattr(kernel, attribute), (tuple, list)):
                raise TypeError(f"{name}: {attribute} must be a tuple or list")
        if not kernel.sources:
            raise ValueError(f"{name}: no source")
        if not all(isinstance(flag, str) for flag in kernel.flags):
            raise TypeError(f"{name}: flags must hold str only")
        for attribute in ("sources", "headers"):
            for at, path in enumerate(getattr(kernel, attribute)):
                _path(path, f"{name}.{attribute}[{at}]")
        checked.append(
            _Kernel(tuple(kernel.sources), tuple(kernel.flags), tuple(kernel.headers))
        )
    return tuple(checked)
