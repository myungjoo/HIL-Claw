"""Build-and-run path of the graph program of ADR-0193 decision 5: resolve, check, builds, one run.

``ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`` decision 5
is the rule, with ``ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md``
(decisions 3 "Loading", 5 and 6). This module joins
:mod:`hilclaw.model_graph`, :mod:`hilclaw.model_build` and the run of
``model_graph.c``, as :mod:`hilclaw.model_forward_execute` joins those of the
forward program. :func:`execute` takes these steps, in order:

1. The graph is read with :func:`hilclaw.model_graph.read` when it is a path
   and resolved with :func:`hilclaw.model_graph.resolve`; a
   :class:`hilclaw.model_graph.GraphFileError` of either is raised.
2. The input values are checked as :func:`hilclaw.model_graph.encode` checks
   them, without building the bytes: a :class:`ValueError` it would raise is
   the outcome **invalid input**, ``"invalid_input"`` with the error's
   parameter and text as its reason.
3. The binding is checked with :func:`hilclaw.model_graph.check_binding`:
   **no kernel** and **kernel unfit**. If an outcome is found, nothing is
   built, written or started.
4. A build directory of its own is made and removed as
   :func:`hilclaw.model_execute.execute` does; each kernel of
   :func:`hilclaw.model_graph.libraries` is built with
   :func:`hilclaw.model_build.build_kernel_library`, then the program with
   :func:`hilclaw.model_build.build_graph_program`. The first failed build is
   **build failed**, a :class:`hilclaw.model_execute.BuildFailed`.
5. The input file is written and the program is run once with
   :func:`hilclaw.local_run.run`; a run that timed out, ended with a status
   other than 0 or left no complete report
   (:func:`hilclaw.model_graph.parse_report`) is **run failed**, carried by a
   :class:`hilclaw.model_forward_run.ForwardProgramResult` as in
   :mod:`hilclaw.model_forward_run`.

:func:`execute_timed` is the timed generation of
``ARCHITECTURE/decisions/ADR-0206-od33-llm-level-evaluation.md`` decision 3:
steps 1 to 4 as above for the generation mode at ``lm_head_rows`` ``"last"``
with the timed input (``encode(..., timed=True)``), then R runs of the
program, each a new process with the same input file, with no warm-up run.
The first run that timed out, ended with a status other than 0, left no
complete timed report (:func:`hilclaw.model_graph.parse_timed_report`) or a
report whose readings do not increase strictly ends it as **run failed**
(ADR-0206 decision 5), with that run's result and no figures.

What this module does not do: it selects no token, which the program does;
it gives no default to any dimension, scalar, RoPE constant (HQ-0070), time
limit or number of runs; it chooses no flag, container or environment; it
has no fallback to another kernel; it summarises, compares, stores, keeps or
retries nothing; and it writes nothing outside its build directory.

Where it may be used (``ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md``
decision 7): every build and the run of this module are host processes, so it
is only for kernels the caller wrote itself, as the driver's tests write them.
A kernel an instance or a coder wrote must not be built or run by this module;
nothing here checks who wrote a kernel.
"""

import enum
import os
import tempfile
from typing import NamedTuple

from hilclaw import local_run, model_binding, model_build, model_graph
from hilclaw.model_execute import (
    BuildFailed,
    _checked_keep_out,
    _checked_parent,
    _checked_prefix,
    _remove,
)
from hilclaw.model_forward_run import ForwardProgramResult
from hilclaw.model_graph import _parameter, _parts
from hilclaw.model_run import RunFailed

PREFIX = "hilclaw-graph-"
"""Name prefix of every build directory this module makes."""


class GraphExecution(NamedTuple):
    """Outcome of one :func:`execute` call, read as :class:`hilclaw.model_forward_execute.ForwardExecution`.

    ``plan`` is the resolved :class:`hilclaw.model_graph.Plan`; ``check`` a
    :class:`hilclaw.model_binding.BindingCheck` holding the invalid-input
    outcome, or else the binding check's.
    """

    plan: model_graph.Plan
    check: model_binding.BindingCheck
    build_failed: BuildFailed | None
    run: ForwardProgramResult | None
    removed: bool | None


class TimedRunFailed(enum.Enum):
    """The condition of a timed run that failed: the three of :class:`hilclaw.model_run.RunFailed`, then readings that do not increase strictly."""

    TIMEOUT = enum.auto()
    EXIT_STATUS = enum.auto()
    REPORT_FORM = enum.auto()
    NOT_INCREASING = enum.auto()


class TimedRun(NamedTuple):
    """One run of :func:`execute_timed`: ``failed`` ``None`` and its :class:`hilclaw.model_graph.TimedReport`, or the failed condition and ``report`` ``None``.

    ``run`` is what :func:`hilclaw.local_run.run` captured, with ``stdout``
    replaced by ``b""``.
    """

    failed: TimedRunFailed | None
    report: model_graph.TimedReport | None
    run: local_run.RunResult


class TimedExecution(NamedTuple):
    """Outcome of one :func:`execute_timed` call.

    ``plan``, ``check``, ``build_failed`` and ``removed`` are read as in
    :class:`GraphExecution`. When every run succeeded, ``runs`` holds the R
    :class:`TimedRun` in run order and ``failed`` is ``None``; when a run
    failed, ``runs`` is ``None`` and ``failed`` is that run's
    :class:`TimedRun`; when nothing was run, both are ``None``.
    """

    plan: model_graph.Plan
    check: model_binding.BindingCheck
    build_failed: BuildFailed | None
    runs: tuple[TimedRun, ...] | None
    failed: TimedRun | None
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
    compiler=None,
    env=None,
    prefix=(),
    parent=None,
    keep_out=(),
):
    """Resolve, check, build and run one bf16 generation of the graph program; return a :class:`GraphExecution`.

    ``graph`` is a :class:`hilclaw.model_graph.Graph` or the path of a graph
    file. ``dimensions``, ``generation_length`` G and ``lm_head_rows`` go to
    :func:`hilclaw.model_graph.resolve` with S the length of ``prompt``;
    ``binding`` goes to :func:`hilclaw.model_graph.check_binding`;
    ``scalars``, ``tables``, ``weights``, ``prompt`` and ``given`` (G token
    ids, or ``None`` for the generation mode) to
    :func:`hilclaw.model_graph.encode`. Kernels are built with their own
    ``sources`` and ``flags``, ``build_timeout_s``, ``compiler`` and ``env``;
    the program with ``program_flags``, ``program_trailing_flags``,
    ``build_timeout_s``, ``compiler`` and ``env``, and run with
    ``run_timeout_s`` and ``env``. ``prefix``, ``parent`` and ``keep_out``
    are those of :func:`hilclaw.model_forward_execute.execute`. No argument
    but the flags, ``compiler``, ``env``, ``prefix``, ``parent`` and
    ``keep_out`` has a default.

    Raised before anything is made: what reading, resolving and the binding
    check raise, then the :class:`TypeError` of the encoding; then
    :class:`TypeError` or :class:`ValueError` for ``prefix``, ``keep_out``,
    ``parent`` and ``program_flags``. What a build or the run raises is
    passed on after the directory was removed.
    """
    inputs = {
        "scalars": scalars,
        "tables": tables,
        "weights": weights,
        "prompt": prompt,
        "given": given,
    }
    plan, check, prefix, roots, place = _prepare(
        graph,
        dimensions,
        binding,
        inputs,
        generation_length,
        lm_head_rows,
        prefix,
        keep_out,
        parent,
        program_flags,
    )
    if not check.ok:
        return GraphExecution(plan, check, None, None, None)
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    try:
        build_failed, command = _build(
            directory,
            plan,
            check,
            inputs,
            prefix,
            build_timeout_s=build_timeout_s,
            compiler=compiler,
            env=env,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
        )
        run = None
        if build_failed is None:
            mode = "generation" if given is None else "given"
            run = _run_once(command, plan, mode, run_timeout_s, env)
    except BaseException:
        _remove(directory, roots)
        raise
    return GraphExecution(plan, check, build_failed, run, _remove(directory, roots))


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
    build_timeout_s,
    run_timeout_s,
    program_flags=(),
    program_trailing_flags=(),
    compiler=None,
    env=None,
    prefix=(),
    parent=None,
    keep_out=(),
):
    """Resolve, check, build and run the timed generation ``repetitions`` times; return a :class:`TimedExecution`.

    The arguments are those of :func:`execute`, with no ``given`` (the
    generation mode) and no ``lm_head_rows`` (``"last"``, ADR-0206 decision
    3); ``run_timeout_s`` is the limit of each run. ``repetitions`` R, an
    ``int`` that is odd and at least 1 (ADR-0206 decision 3), is the number
    of runs, each a new process with the same input file; no warm-up run is
    made. A plan whose passes report other than one row each is the outcome
    invalid input with ``timed`` in its reason.

    Raised before anything is read or made: :class:`TypeError` for
    ``repetitions`` that is not an ``int`` (``bool`` included) and
    :class:`ValueError` for one that is even or below 1, ``parameter``
    ``"repetitions"``; then what :func:`execute` raises, in its order. What
    a build or a run raises is passed on after the directory was removed.
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
    plan, check, prefix, roots, place = _prepare(
        graph,
        dimensions,
        binding,
        inputs,
        generation_length,
        "last",
        prefix,
        keep_out,
        parent,
        program_flags,
    )
    if not check.ok:
        return TimedExecution(plan, check, None, None, None, None)
    directory = tempfile.mkdtemp(prefix=PREFIX, dir=place)
    try:
        build_failed, command = _build(
            directory,
            plan,
            check,
            inputs,
            prefix,
            build_timeout_s=build_timeout_s,
            compiler=compiler,
            env=env,
            program_flags=program_flags,
            program_trailing_flags=program_trailing_flags,
        )
        runs = failed = None
        if build_failed is None:
            runs = []
            for _ in range(repetitions):
                one = _timed_run(command, plan, run_timeout_s, env)
                if one.failed is not None:
                    runs, failed = None, one
                    break
                runs.append(one)
            runs = None if runs is None else tuple(runs)
    except BaseException:
        _remove(directory, roots)
        raise
    return TimedExecution(
        plan, check, build_failed, runs, failed, _remove(directory, roots)
    )


def _prepare(
    graph,
    dimensions,
    binding,
    inputs,
    generation_length,
    lm_head_rows,
    prefix,
    keep_out,
    parent,
    program_flags,
):
    if not isinstance(graph, model_graph.Graph):
        graph = model_graph.read(graph)
    plan = model_graph.resolve(
        graph,
        dimensions,
        prompt_length=len(inputs["prompt"]),
        generation_length=generation_length,
        lm_head_rows=lm_head_rows,
    )
    check = model_graph.check_binding(plan, binding)
    reason = _invalid(plan, inputs)
    if reason is not None:
        outcome = model_binding.Outcome(model_binding.INVALID_INPUT, None, None, reason)
        check = model_binding.BindingCheck(False, (outcome, *check.outcomes), ())
    prefix = _checked_prefix(prefix)
    roots = _checked_keep_out(keep_out)
    place = _checked_parent(parent, roots)
    if not isinstance(program_flags, (tuple, list)) or not all(
        isinstance(flag, str) for flag in program_flags
    ):
        raise TypeError("program_flags: must be a tuple or list of str")
    return plan, check, prefix, roots, place


def _invalid(plan, inputs):
    anything = model_binding.KernelReference(("-",), None, ())
    calls = []
    for step in (s for p in plan.passes for s in p.steps):
        if isinstance(step, model_graph.KernelStep):
            calls.append((step.site, step.shape, anything))
    covering = model_binding.BindingCheck(True, (), tuple(calls))
    try:
        _parts(plan, covering, **inputs)
    except ValueError as error:
        return f"{getattr(error, 'parameter', '?')}: {error}"
    return None


def _build(
    directory,
    plan,
    check,
    inputs,
    prefix,
    *,
    build_timeout_s,
    compiler,
    env,
    program_flags,
    program_trailing_flags,
):
    libraries = []
    for index, kernel in enumerate(model_graph.libraries(check)):
        library = os.path.join(directory, f"kernel-{index}.so")
        build = model_build.build_kernel_library(
            kernel.sources,
            library,
            timeout_s=build_timeout_s,
            flags=kernel.flags,
            compiler=compiler,
            env=env,
        )
        if not build.ok:
            return BuildFailed(index, build), None
        libraries.append(library)
    program = os.path.join(directory, "model_graph")
    build = model_build.build_graph_program(
        program,
        timeout_s=build_timeout_s,
        flags=program_flags,
        trailing_flags=program_trailing_flags,
        compiler=compiler,
        env=env,
    )
    if not build.ok:
        return BuildFailed(None, build), None
    input_file = os.path.join(directory, "input.bin")
    with open(input_file, "xb") as stream:
        stream.write(model_graph.encode(plan, check, **inputs))
    return None, (*prefix, program, input_file, *libraries)


def _run_once(command, plan, mode, run_timeout_s, env):
    run = local_run.run(command, timeout_s=run_timeout_s, env=env)
    stdout, run = run.stdout, run._replace(stdout=b"")
    if run.timed_out:
        return ForwardProgramResult(RunFailed.TIMEOUT, None, run)
    if run.returncode != 0:
        return ForwardProgramResult(RunFailed.EXIT_STATUS, None, run)
    report = model_graph.parse_report(stdout, plan, mode=mode)
    if report is None:
        return ForwardProgramResult(RunFailed.REPORT_FORM, None, run)
    return ForwardProgramResult(None, report, run)


def _timed_run(command, plan, run_timeout_s, env):
    run = local_run.run(command, timeout_s=run_timeout_s, env=env)
    stdout, run = run.stdout, run._replace(stdout=b"")
    if run.timed_out:
        return TimedRun(TimedRunFailed.TIMEOUT, None, run)
    if run.returncode != 0:
        return TimedRun(TimedRunFailed.EXIT_STATUS, None, run)
    report = model_graph.parse_timed_report(stdout, plan)
    if report is None:
        return TimedRun(TimedRunFailed.REPORT_FORM, None, run)
    if not report.increasing:
        return TimedRun(TimedRunFailed.NOT_INCREASING, None, run)
    return TimedRun(None, report, run)
