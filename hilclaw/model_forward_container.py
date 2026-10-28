"""Container path of the bf16 forward pass: check, copies, builds and one run, each build and the run in a new container.

``ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md`` is the
rule (code slice 1); a decision cited by its number alone is one of that
record. :func:`execute` does what :func:`hilclaw.model_forward_execute.execute`
does — the whole-generation check, the per-pass library table, the builds, the
input file, one run and the parsed report — with every build and the
generation process carried out in a new container of ADR-0144 through
:func:`hilclaw.standin_container.run_in_container`, whose properties
(ADR-0144 decision 6) it takes unchanged (decision 2). It takes these steps, in
order:

1. The whole-generation check of :func:`hilclaw.model_forward_check.check` at
   the dtype ``"bf16"``. If its result is not ``ok``, the result carries it and
   nothing is read, made or started.
2. The image named by :data:`hilclaw.standin_image.ENV_IMAGE`, read with
   :func:`hilclaw.standin_image.read_image` (decision 3). None named, or a
   refused value, is the outcome **container unavailable** (decision 8) and
   nothing is made or started.
3. A build directory of its own, made and removed as
   :func:`hilclaw.model_execute.execute` makes and removes one, with the prefix
   :data:`PREFIX`. Into it, by copy (decision 4): the forward program's source
   under its basename, and the source files of kernel ``i`` under their
   basenames in the sub-directory ``kernel-<i>``, which holds nothing else.
4. One build container per distinct kernel, in the order of the check's
   ``calls``: :data:`hilclaw.standin_check.COMPILER` with the kernel's
   ``flags``, :data:`hilclaw.model_build.LIBRARY_FLAGS`, its copies and
   ``-o`` the library ``kernel-<i>.so`` in the build directory; then one for
   the forward program: the compiler with ``program_flags``, the program's
   copy, ``program_trailing_flags`` and ``-o`` the executable
   ``model_forward``. Every path handed in is the absolute path inside the
   container (:func:`hilclaw.standin_check.in_container`).
5. The input file of :func:`hilclaw.model_forward_run.encode_input`, written as
   ``input.bin`` into the build directory on the host, and one process
   container that runs the executable with the input file and the libraries,
   their paths inside the container. Its standard output is the report, read
   with :func:`hilclaw.model_forward_run.parse_report`.

Outcomes, after an ``ok`` check (decision 8):

- **Container unavailable** (:class:`Unavailable`): one of :data:`REASONS`;
  :data:`RUNTIME_STATUS` is a build container that ended with 125, 126 or
  127, the container runtime's statuses for a build as ADR-0168 decision 3
  reads them. Nothing after it is started.
- **Build failed** (:class:`hilclaw.model_execute.BuildFailed`): the first
  build container that timed out, ended with another non-zero status, or ended
  with 0 and left no regular file at its output. Its ``build`` is a
  :class:`hilclaw.clang_build.BuildResult` whose ``output`` is the host path
  of the output, whose ``log`` is the client's standard output then its
  standard error, each decoded as UTF-8 with invalid bytes replaced (ADR-0169
  decision 2), and whose ``command`` is the client's command line.
- **Run failed** (:class:`ContainerRun` with ``failed`` set): the process
  container timed out (:attr:`hilclaw.model_run.RunFailed.TIMEOUT`), ended
  with a status other than 0 — 125 to 127 included, the program's for a process
  as ADR-0168 decision 3 reads them — (``EXIT_STATUS``), or left no complete
  report (``REPORT_FORM``).

A forced removal is given :data:`hilclaw.standin_check.REMOVAL_TIMEOUT_S`
(decision 5). The build directory is removed only where
:func:`hilclaw.standin_answer.build_dir_removable` is true of every container
(ADR-0168 decision 5); otherwise it is left and ``removed`` is false.

Raised before anything is made: first what the check raises, unchanged; then
:class:`TypeError` or :class:`ValueError` for ``keep_out`` and ``parent`` as
:func:`hilclaw.model_execute.execute` raises them; :class:`TypeError` for
``program_flags`` or ``program_trailing_flags`` that is not a ``tuple`` or
``list`` of ``str``; :class:`TypeError` or :class:`ValueError` for a
``build_timeout_s`` or ``run_timeout_s`` that is not a positive finite number;
:class:`TypeError` for an ``environ`` that is neither ``None`` nor a mapping.
These are raised whatever the check's outcome. The :class:`OSError` of making
the directory is raised as it is. What the copies raise
(:class:`hilclaw.standin_copies.CopyError` among them), what
:func:`hilclaw.standin_container.run_in_container` raises apart from the two
errors that are **container unavailable** (any other :class:`OSError` among
them, ADR-0168 C14), and what the input's encoding or writing raises are
passed on unchanged after the directory was removed where it may be.

What this module does not do: it never builds or starts anything on the host
(ADR-0144 decision 4; decision 2); it names no image and pulls, installs or
changes none; it gives no time limit a default and sets no resource bound
(decisions 5, 6); it hands no variable of its own environment into a container;
it copies no header of a kernel, since a
:class:`hilclaw.model_binding.KernelReference` names none (decision 9); it
selects no token, has no reference or tolerance, casts no array, has no
fallback to another kernel, and stores, keeps or retries nothing.
"""

import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

from hilclaw import (
    clang_build,
    local_run,
    model_binding,
    model_build,
    model_forward_check,
    model_forward_run,
    model_run,
    standin_answer,
    standin_check,
    standin_container,
    standin_copies,
    standin_image,
)
from hilclaw.model_execute import (
    BuildFailed,
    _checked_keep_out,
    _checked_parent,
    _remove,
)
from hilclaw.model_forward_execute import _distinct_kernels, _library_table
from hilclaw.standin_check import _log, _regular_file
from hilclaw.standin_container import _check_limit
from hilclaw.standin_copies import _read, _write_new, _writing

PREFIX = "hilclaw-forward-container-"
"""Name prefix of every build directory this module makes."""

NO_IMAGE = "no_image"
IMAGE_REFUSED = "image_refused"
NO_CLIENT = "no_client"
NO_NUMERIC_USER = "no_numeric_user"
RUNTIME_STATUS = "runtime_status"
REASONS = (NO_IMAGE, IMAGE_REFUSED, NO_CLIENT, NO_NUMERIC_USER, RUNTIME_STATUS)
"""Every ``reason`` of :class:`Unavailable`."""

_PROGRAM_NAME = "model_forward"
_INPUT_NAME = "input.bin"
_RUNTIME_STATUSES = frozenset((125, 126, 127))


class Unavailable(NamedTuple):
    """The outcome **container unavailable**: ``reason`` is one of :data:`REASONS`.

    ``detail`` is the :class:`hilclaw.standin_container.ContainerResult` of
    the build container for :data:`RUNTIME_STATUS`, the error raised for
    :data:`IMAGE_REFUSED`, :data:`NO_CLIENT` and :data:`NO_NUMERIC_USER`, and
    ``None`` for :data:`NO_IMAGE`.
    """

    reason: str
    detail: object


class ContainerRun(NamedTuple):
    """The generation process's container: ``failed`` and ``report`` as in :class:`hilclaw.model_forward_run.ForwardProgramResult`.

    ``container`` is the :class:`hilclaw.standin_container.ContainerResult`
    with its ``stdout`` replaced by ``b""``.
    """

    failed: model_run.RunFailed | None
    report: model_forward_run.ForwardReport | None
    container: standin_container.ContainerResult


class ForwardContainerExecution(NamedTuple):
    """Outcome of one :func:`execute` call.

    ``check`` is the :class:`hilclaw.model_binding.BindingCheck` of the
    whole-generation check. At most one of ``unavailable``, ``build_failed``
    and a ``run`` whose ``failed`` is set holds an outcome; ``run`` is
    ``None`` unless the process container was started and ended. ``removed``
    is ``None`` when no build directory was made, else whether it no longer
    exists afterwards.
    """

    check: model_binding.BindingCheck
    unavailable: Unavailable | None
    build_failed: BuildFailed | None
    run: ContainerRun | None
    removed: bool | None


class _Stop(Exception):
    def __init__(self, outcome):
        super().__init__()
        self.outcome = outcome


def execute(
    dimensions,
    binding,
    *,
    eps,
    rope,
    weights,
    prompt,
    given,
    generation_length,
    lm_head_rows,
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    environ=None,
    parent=None,
    keep_out=(),
):
    """Check, build and run one bf16 generation in containers; return a :class:`ForwardContainerExecution`.

    ``dimensions``, ``binding``, ``eps``, ``rope``, ``weights``, ``prompt``,
    ``given``, ``generation_length`` and ``lm_head_rows`` are those of
    :func:`hilclaw.model_forward_execute.execute`. ``build_timeout_s`` is the
    time limit of each build container and ``run_timeout_s`` that of the
    process container; neither has a default (decision 5). ``program_flags``
    and ``program_trailing_flags`` are the forward program build's, as in
    :func:`hilclaw.model_build.build_forward_program`; whether the image's C
    library needs ``-ldl`` is the caller's. ``environ`` is the mapping the
    image is read from (``None``: :data:`os.environ`). ``parent`` and
    ``keep_out`` are those of :func:`hilclaw.model_execute.execute`. See the
    module docstring for the steps, the outcomes and what is raised.
    """
    check = model_forward_check.check(
        dimensions,
        binding,
        dtype="bf16",
        eps=eps,
        rope=rope,
        weights=weights,
        prompt=prompt,
        given=given,
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
    )
    roots = _checked_keep_out(keep_out)
    place = _checked_parent(parent, roots)
    for name, flags in (
        ("program_flags", program_flags),
        ("program_trailing_flags", program_trailing_flags),
    ):
        if not isinstance(flags, (tuple, list)) or not all(
            isinstance(flag, str) for flag in flags
        ):
            raise TypeError(f"{name}: must be a tuple or list of str")
    _check_limit(build_timeout_s, "build_timeout_s")
    _check_limit(run_timeout_s, "run_timeout_s")
    if environ is not None and not isinstance(environ, Mapping):
        raise TypeError(f"environ: must be a mapping, not {type(environ).__name__}")
    if not check.ok:
        return ForwardContainerExecution(check, None, None, None, None)
    try:
        image = standin_image.read_image(environ)
    except standin_image.ImageRefusedError as error:
        return ForwardContainerExecution(
            check, Unavailable(IMAGE_REFUSED, error), None, None, None
        )
    if image is None:
        return ForwardContainerExecution(
            check, Unavailable(NO_IMAGE, None), None, None, None
        )
    kernels = _distinct_kernels(check.calls)
    libraries = _library_table(
        dimensions,
        check.calls,
        kernels,
        prompt_length=len(prompt),
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
    )
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    outcomes = []
    unavailable = build_failed = run = None
    try:
        run = _build_and_run(
            image,
            directory,
            kernels,
            outcomes,
            build_timeout_s=build_timeout_s,
            run_timeout_s=run_timeout_s,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
            dimensions=dimensions,
            input_arguments={
                "eps": eps,
                "rope": rope,
                "weights": weights,
                "prompt": prompt,
                "given": given,
                "generation_length": generation_length,
                "lm_head_rows": lm_head_rows,
                "libraries": libraries,
                "library_count": len(kernels),
            },
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
    return ForwardContainerExecution(check, unavailable, build_failed, run, removed)


def _settle(directory, roots, outcomes):
    if all(standin_answer.build_dir_removable(outcome) for outcome in outcomes):
        return _remove(directory, roots)
    return not os.path.lexists(directory)


def _build_and_run(
    image,
    directory,
    kernels,
    outcomes,
    *,
    build_timeout_s,
    run_timeout_s,
    program_flags,
    program_trailing_flags,
    dimensions,
    input_arguments,
):
    program_source = standin_copies.place_harness_copy(
        model_build.FORWARD_PROGRAM_SOURCE, directory
    )
    copies = [
        _copy_kernel(directory, index, kernel) for index, kernel in enumerate(kernels)
    ]
    libraries = []
    for index, (kernel, sources) in enumerate(zip(kernels, copies, strict=True)):
        library = f"kernel-{index}.so"
        _build(
            image,
            directory,
            outcomes,
            (
                *kernel.flags,
                *model_build.LIBRARY_FLAGS,
                *(standin_check.in_container(source) for source in sources),
                "-o",
                standin_check.in_container(library),
            ),
            library,
            index,
            build_timeout_s,
        )
        libraries.append(standin_check.in_container(library))
    _build(
        image,
        directory,
        outcomes,
        (
            *program_flags,
            standin_check.in_container(program_source),
            *program_trailing_flags,
            "-o",
            standin_check.in_container(_PROGRAM_NAME),
        ),
        _PROGRAM_NAME,
        None,
        build_timeout_s,
    )
    data = model_forward_run.encode_input(dimensions, **input_arguments)
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
    report = model_forward_run.parse_report(
        stdout,
        dimensions,
        prompt_length=len(input_arguments["prompt"]),
        generation_length=input_arguments["generation_length"],
        lm_head_rows=input_arguments["lm_head_rows"],
        mode="generation" if input_arguments["given"] is None else "given",
    )
    if report is None:
        return ContainerRun(model_run.RunFailed.REPORT_FORM, None, result)
    return ContainerRun(None, report, result)


def _copy_kernel(directory, index, kernel):
    read = [
        (
            os.path.basename(os.fspath(source)),
            _read(source, harness=False),
        )
        for source in kernel.sources
    ]
    sub_directory = f"kernel-{index}"
    with _writing():
        os.mkdir(os.path.join(directory, sub_directory))
        for name, data in read:
            _write_new(os.path.join(directory, sub_directory, name), data)
    return tuple(f"{sub_directory}/{name}" for name, _ in read)


def _build(image, directory, outcomes, arguments, output, kernel, timeout_s):
    result = _container(
        image, directory, outcomes, standin_check.COMPILER, arguments, timeout_s
    )
    if not result.timed_out and result.returncode in _RUNTIME_STATUSES:
        raise _Stop(Unavailable(RUNTIME_STATUS, result))
    host_output = os.path.join(directory, output)
    ok = not result.timed_out and result.returncode == 0 and _regular_file(host_output)
    if not ok:
        build = clang_build.BuildResult(
            ok=False,
            returncode=result.returncode,
            timed_out=result.timed_out,
            output=Path(host_output),
            log=_log(result),
            command=result.command,
            duration_s=result.duration_s,
        )
        raise _Stop(BuildFailed(kernel, build))


def _container(image, directory, outcomes, program, arguments, timeout_s):
    try:
        try:
            result = standin_container.run_in_container(
                image,
                directory,
                program,
                arguments,
                timeout_s=timeout_s,
                removal_timeout_s=standin_check.REMOVAL_TIMEOUT_S,
            )
        except BaseException as error:
            outcomes.append(error)
            raise
    except local_run.ProgramNotFoundError as error:
        raise _Stop(Unavailable(NO_CLIENT, error)) from None
    except standin_container.NoNumericUserError as error:
        raise _Stop(Unavailable(NO_NUMERIC_USER, error)) from None
    outcomes.append(result)
    return result
