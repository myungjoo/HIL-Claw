"""Container path of the graph program: copies, builds and runs, each build and each run in a new container.

``ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md``
(decisions 2 to 8) is the rule of the path, applied to the graph program of
``ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`` decision 5;
``ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`` (decisions
3 to 5, slice 2 of decision 7) is that of the timed runs. As
:mod:`hilclaw.model_forward_container` is to
:func:`hilclaw.model_forward_execute.execute`, this module is to
:mod:`hilclaw.model_graph_execute`: it takes the same steps with every build
and every run carried out in a new container of ADR-0144 through
:func:`hilclaw.standin_container.run_in_container`, and it is the path for a
kernel an instance or a coder wrote (ADR-0182 decision 7). Its steps:

1. The graph is read, resolved and checked, and the input values checked, as
   :func:`hilclaw.model_graph_execute.execute` and
   :func:`hilclaw.model_graph_execute.execute_timed` do; an outcome of that
   check (**invalid input**, **no kernel**, **kernel unfit**) is returned and
   nothing is read, made or started.
2. The image named by :data:`hilclaw.standin_image.ENV_IMAGE`, read with
   :func:`hilclaw.standin_image.read_image`. None named, or a refused value,
   is **container unavailable** and nothing is made or started.
3. A build directory of its own with the prefix :data:`PREFIX`. Into it, by
   copy: ``model_graph.c`` and, for the timed runs, the waiter's source
   :data:`hilclaw.standin_run.WAITER_SOURCE`, each under its basename, and the
   sources then the headers of kernel ``i`` of
   :func:`hilclaw.model_graph.libraries` under their basenames in the
   sub-directory ``kernel-<i>``.
4. One build container per kernel, built into ``kernel-<i>.so`` with its
   ``flags`` and :data:`hilclaw.model_build.LIBRARY_FLAGS`; one for the
   program, built into ``model_graph`` with ``program_flags``, its copy and
   ``program_trailing_flags``; for the timed runs one for the waiter, built
   into ``waiter`` with ``waiter_flags`` and its copy alone, no trailing flag
   (ADR-0145 decision 3). The commands are those of
   :mod:`hilclaw.model_forward_container`.
5. The input file of :func:`hilclaw.model_graph.encode`, written as
   ``input.bin`` into the build directory on the host. :func:`execute` then
   starts one process container that runs the program with the input file and
   the libraries; its standard output is read with
   :func:`hilclaw.model_graph.parse_report`. :func:`execute_timed` starts R
   process containers, one after another, each a new container in which the
   waiter is process 1 and starts the timed program, with the same input file
   and libraries, as its one child (ADR-0145 decision 3; ADR-0206 decision 4).

Outcomes, after an ``ok`` check:

- **Container unavailable**: a :class:`hilclaw.model_forward_container.Unavailable`,
  with its reasons, for no image named, a refused image, no client, no
  numeric user and a build container ended with 125 to 127 (ADR-0168
  decision 3). Nothing after it is started.
- **Build failed**: a :class:`hilclaw.model_execute.BuildFailed` of the first
  build that timed out, ended with another non-zero status or left no
  regular file, as in :mod:`hilclaw.model_forward_container`; its ``kernel``
  is ``None`` for the program and for the waiter, told apart by the build's
  ``output``.
- **Run failed** of :func:`execute`: a
  :class:`hilclaw.model_forward_container.ContainerRun` with ``failed`` set,
  read as that module reads its process container.
- **Run failed** of :func:`execute_timed`: the first :class:`TimedContainerRun`
  whose ``failed`` is set ends the execution with no figures (ADR-0206
  decision 5). The process container is read in the order of ADR-0168
  decision 4: a timeout is :attr:`TimedRunFailed.TIMEOUT`; otherwise any
  status other than 0, 125 to 127 included (the program's under the waiter,
  with or without a waiter's line), is :attr:`TimedRunFailed.EXIT_STATUS`;
  status 0 with no waiter's line (:func:`hilclaw.standin_waiter_line.read`)
  is :attr:`TimedRunFailed.WAITER_LINE`; a report before the line that is not
  a complete timed report (:func:`hilclaw.model_graph.parse_timed_report`) is
  :attr:`TimedRunFailed.REPORT_FORM`; readings that do not increase strictly
  are :attr:`TimedRunFailed.NOT_INCREASING`.

A run that succeeded carries its timed report — the G intervals and
``resolution`` among it — and its memory figure: ``memory_bytes`` is the
waiter's ``ru_maxrss`` in KiB times 1024, or ``None`` where the waiter's value
is not a positive integer or it wrote the none line (ADR-0052 decision 4;
ADR-0206 decision 4).

The build directory is removed as :mod:`hilclaw.model_forward_container`
removes its own; ``removed`` is ``None`` when none was made.

Raised before anything is made: for :func:`execute_timed`,
:class:`TypeError` for ``repetitions`` that is not an ``int`` (``bool``
included) and :class:`ValueError` for one that is even or below 1, both with
``parameter`` ``"repetitions"`` and before the graph is read; then what
reading, resolving, the binding check and the encoding's type checks raise,
and :class:`TypeError` or :class:`ValueError` for ``keep_out``, ``parent``
and ``program_flags``, as :mod:`hilclaw.model_graph_execute` raises them;
then, as :func:`hilclaw.model_forward_container.execute` raises them, for
``program_flags``, ``program_trailing_flags``, ``build_timeout_s``,
``run_timeout_s`` and ``environ``; and for :func:`execute_timed`
:class:`TypeError` for ``waiter_flags`` that is not a ``tuple`` or ``list``
of ``str``. These are raised whatever the check's outcome. What the copies,
the containers and the encoding raise is passed on as in
:mod:`hilclaw.model_forward_container`.

What this module does not do: it builds and starts nothing on the host, names
no image, gives no default to any time limit, number of runs, flag, prompt or
length, sets no resource bound and hands no variable of its environment into
a container; it computes no summary (median, rate or maximum), ties no tokens
to another run, writes no record, starts no command, and stores, keeps or
retries nothing (ADR-0206 slices 3 and 4).
"""

import enum
import os
import tempfile
from typing import NamedTuple

from hilclaw import (
    model_binding,
    model_build,
    model_graph,
    model_run,
    standin_check,
    standin_container,
    standin_copies,
    standin_run,
    standin_waiter_line,
)
from hilclaw.model_execute import BuildFailed
from hilclaw.model_forward_container import (
    ContainerRun,
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
from hilclaw.model_graph import _parameter
from hilclaw.model_graph_execute import _prepare

PREFIX = "hilclaw-graph-container-"
"""Name prefix of every build directory this module makes."""

_PROGRAM_NAME = "model_graph"
_WAITER_NAME = "waiter"
_INPUT_NAME = "input.bin"


class TimedRunFailed(enum.Enum):
    """The condition of a timed run that failed in its container.

    Those of :class:`hilclaw.model_graph_execute.TimedRunFailed`, and
    ``WAITER_LINE``: status 0 and no waiter's line.
    """

    TIMEOUT = enum.auto()
    EXIT_STATUS = enum.auto()
    WAITER_LINE = enum.auto()
    REPORT_FORM = enum.auto()
    NOT_INCREASING = enum.auto()


class GraphContainerExecution(NamedTuple):
    """Outcome of one :func:`execute` call.

    ``plan`` and ``check`` are read as in
    :class:`hilclaw.model_graph_execute.GraphExecution`; ``unavailable``,
    ``build_failed``, ``run`` and ``removed`` as in
    :class:`hilclaw.model_forward_container.ForwardContainerExecution`, the
    report of ``run`` being that of :func:`hilclaw.model_graph.parse_report`.
    """

    plan: model_graph.Plan
    check: model_binding.BindingCheck
    unavailable: Unavailable | None
    build_failed: BuildFailed | None
    run: ContainerRun | None
    removed: bool | None


class TimedContainerRun(NamedTuple):
    """One timed run of :func:`execute_timed`.

    ``failed`` is ``None`` with the run's :class:`hilclaw.model_graph.TimedReport`
    and its ``memory_bytes`` (an ``int`` of bytes, or ``None``), or the failed
    condition with ``report`` and ``memory_bytes`` ``None``. ``container`` is
    the :class:`hilclaw.standin_container.ContainerResult` with its ``stdout``
    replaced by ``b""``.
    """

    failed: TimedRunFailed | None
    report: model_graph.TimedReport | None
    memory_bytes: int | None
    container: standin_container.ContainerResult


class TimedContainerExecution(NamedTuple):
    """Outcome of one :func:`execute_timed` call.

    ``plan``, ``check``, ``unavailable``, ``build_failed`` and ``removed`` are
    read as in :class:`GraphContainerExecution`. When every run succeeded,
    ``runs`` holds the R :class:`TimedContainerRun` in run order and
    ``failed`` is ``None``; when a run failed, ``runs`` is ``None`` and
    ``failed`` is that run; when no run was made, both are ``None``.
    """

    plan: model_graph.Plan
    check: model_binding.BindingCheck
    unavailable: Unavailable | None
    build_failed: BuildFailed | None
    runs: tuple[TimedContainerRun, ...] | None
    failed: TimedContainerRun | None
    removed: bool | None


def execute(
    graph,
    dimensions,
    binding,
    *,
    scalars,
    tables,
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
    """Check, build and run one bf16 generation of the graph program in containers; return a :class:`GraphContainerExecution`.

    ``graph``, ``dimensions``, ``binding``, ``scalars``, ``tables``,
    ``weights``, ``prompt``, ``given``, ``generation_length`` and
    ``lm_head_rows`` are those of :func:`hilclaw.model_graph_execute.execute`.
    ``build_timeout_s`` is the time limit of each build container and
    ``run_timeout_s`` that of the process container. ``program_flags``,
    ``program_trailing_flags``, ``environ``, ``parent`` and ``keep_out`` are
    those of :func:`hilclaw.model_forward_container.execute`. No other
    argument has a default. See the module docstring for the steps, the
    outcomes and what is raised.
    """
    inputs = {
        "scalars": scalars,
        "tables": tables,
        "weights": weights,
        "prompt": prompt,
        "given": given,
    }
    plan, check, roots, place, image, unavailable = _prepared(
        graph,
        dimensions,
        binding,
        inputs,
        generation_length,
        lm_head_rows,
        (program_flags, program_trailing_flags, build_timeout_s, run_timeout_s),
        environ,
        parent,
        keep_out,
    )
    if not check.ok or unavailable is not None:
        return GraphContainerExecution(plan, check, unavailable, None, None, None)
    mode = "generation" if given is None else "given"
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    outcomes = []
    build_failed = run = None
    try:
        command = _build_all(
            image,
            directory,
            outcomes,
            plan,
            check,
            inputs,
            build_timeout_s=build_timeout_s,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
            waiter_flags=None,
        )
        run = _run_once(image, directory, outcomes, command, plan, mode, run_timeout_s)
    except _Stop as stop:
        if type(stop.outcome) is Unavailable:
            unavailable = stop.outcome
        else:
            build_failed = stop.outcome
    except BaseException:
        _settle(directory, roots, outcomes)
        raise
    removed = _settle(directory, roots, outcomes)
    return GraphContainerExecution(plan, check, unavailable, build_failed, run, removed)


def execute_timed(
    graph,
    dimensions,
    binding,
    *,
    scalars,
    tables,
    weights,
    prompt,
    generation_length,
    repetitions,
    waiter_flags,
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    environ=None,
    parent=None,
    keep_out=(),
):
    """Build the timed graph program and the waiter in containers and run it ``repetitions`` times; return a :class:`TimedContainerExecution`.

    The arguments are those of :func:`execute`, with no ``given`` (the
    generation mode) and no ``lm_head_rows`` (``"last"``, ADR-0206 decision
    3), as in :func:`hilclaw.model_graph_execute.execute_timed`;
    ``run_timeout_s`` is the limit of each process container. ``repetitions``
    R, an ``int`` that is odd and at least 1, is the number of runs, each a
    new process container with the same input file; no warm-up run is made.
    ``waiter_flags`` are the flags of the waiter's build, the target's
    :attr:`hilclaw.targets.Target.waiter_flags`, with no default. See the
    module docstring for the steps, the outcomes and what is raised.
    """
    with _parameter("repetitions"):
        if type(repetitions) is not int:
            raise TypeError(f"must be an int, got {type(repetitions).__name__}")
        if repetitions < 1 or repetitions % 2 == 0:
            raise ValueError(f"must be odd and at least 1, got {repetitions}")
    inputs = {
        "scalars": scalars,
        "tables": tables,
        "weights": weights,
        "prompt": prompt,
        "given": None,
        "timed": True,
    }
    plan, check, roots, place, image, unavailable = _prepared(
        graph,
        dimensions,
        binding,
        inputs,
        generation_length,
        "last",
        (program_flags, program_trailing_flags, build_timeout_s, run_timeout_s),
        environ,
        parent,
        keep_out,
        waiter_flags=waiter_flags,
    )
    if not check.ok or unavailable is not None:
        return TimedContainerExecution(plan, check, unavailable, None, None, None, None)
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    outcomes = []
    build_failed = runs = failed = None
    try:
        command = _build_all(
            image,
            directory,
            outcomes,
            plan,
            check,
            inputs,
            build_timeout_s=build_timeout_s,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
            waiter_flags=waiter_flags,
        )
        done = []
        for _ in range(repetitions):
            one = _timed_run(image, directory, outcomes, command, plan, run_timeout_s)
            if one.failed is not None:
                failed = one
                break
            done.append(one)
        runs = None if failed is not None else tuple(done)
    except _Stop as stop:
        if type(stop.outcome) is Unavailable:
            unavailable = stop.outcome
        else:
            build_failed = stop.outcome
    except BaseException:
        _settle(directory, roots, outcomes)
        raise
    removed = _settle(directory, roots, outcomes)
    return TimedContainerExecution(
        plan, check, unavailable, build_failed, runs, failed, removed
    )


def _prepared(
    graph,
    dimensions,
    binding,
    inputs,
    generation_length,
    lm_head_rows,
    container_arguments,
    environ,
    parent,
    keep_out,
    *,
    waiter_flags=(),
):
    program_flags, program_trailing_flags, build_timeout_s, run_timeout_s = (
        container_arguments
    )
    plan, check, _, roots, place = _prepare(
        graph,
        dimensions,
        binding,
        inputs,
        generation_length,
        lm_head_rows,
        (),
        keep_out,
        parent,
        program_flags,
    )
    _check_container_arguments(
        program_flags, program_trailing_flags, build_timeout_s, run_timeout_s, environ
    )
    if not isinstance(waiter_flags, (tuple, list)) or not all(
        isinstance(flag, str) for flag in waiter_flags
    ):
        raise TypeError("waiter_flags: must be a tuple or list of str")
    if not check.ok:
        return plan, check, roots, place, None, None
    image, unavailable = _named_image(environ)
    return plan, check, roots, place, image, unavailable


def _build_all(
    image,
    directory,
    outcomes,
    plan,
    check,
    inputs,
    *,
    build_timeout_s,
    program_flags,
    program_trailing_flags,
    waiter_flags,
):
    program_source = standin_copies.place_harness_copy(
        model_build.GRAPH_PROGRAM_SOURCE, directory
    )
    waiter_source = None
    if waiter_flags is not None:
        waiter_source = standin_copies.place_harness_copy(
            standin_run.WAITER_SOURCE, directory
        )
    kernels = model_graph.libraries(check)
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
            standin_check.in_container(program_source),
            *program_trailing_flags,
            "-o",
            standin_check.in_container(_PROGRAM_NAME),
        ),
        _PROGRAM_NAME,
        None,
        build_timeout_s,
    )
    if waiter_source is not None:
        _build(
            image,
            directory,
            outcomes,
            (
                *waiter_flags,
                standin_check.in_container(waiter_source),
                "-o",
                standin_check.in_container(_WAITER_NAME),
            ),
            _WAITER_NAME,
            None,
            build_timeout_s,
        )
    with open(os.path.join(directory, _INPUT_NAME), "xb") as stream:
        stream.write(model_graph.encode(plan, check, **inputs))
    return (
        standin_check.in_container(_PROGRAM_NAME),
        standin_check.in_container(_INPUT_NAME),
        *libraries,
    )


def _run_once(image, directory, outcomes, command, plan, mode, timeout_s):
    program, *arguments = command
    result = _container(image, directory, outcomes, program, arguments, timeout_s)
    stdout, result = result.stdout, result._replace(stdout=b"")
    if result.timed_out:
        return ContainerRun(model_run.RunFailed.TIMEOUT, None, result)
    if result.returncode != 0:
        return ContainerRun(model_run.RunFailed.EXIT_STATUS, None, result)
    report = model_graph.parse_report(stdout, plan, mode=mode)
    if report is None:
        return ContainerRun(model_run.RunFailed.REPORT_FORM, None, result)
    return ContainerRun(None, report, result)


def _timed_run(image, directory, outcomes, command, plan, timeout_s):
    result = _container(
        image,
        directory,
        outcomes,
        standin_check.in_container(_WAITER_NAME),
        command,
        timeout_s,
    )
    stdout, result = result.stdout, result._replace(stdout=b"")
    if result.timed_out:
        return TimedContainerRun(TimedRunFailed.TIMEOUT, None, None, result)
    if result.returncode != 0:
        return TimedContainerRun(TimedRunFailed.EXIT_STATUS, None, None, result)
    waiter = standin_waiter_line.read(stdout)
    if waiter is None:
        return TimedContainerRun(TimedRunFailed.WAITER_LINE, None, None, result)
    report = model_graph.parse_timed_report(waiter.report, plan)
    if report is None:
        return TimedContainerRun(TimedRunFailed.REPORT_FORM, None, None, result)
    if not report.increasing:
        return TimedContainerRun(TimedRunFailed.NOT_INCREASING, None, None, result)
    return TimedContainerRun(None, report, waiter.memory_bytes, result)
