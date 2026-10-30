"""Python side of a bf16 timing run of ADR-0181: form the command line of a kind, start it and judge.

``ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`` is the rule
(decision 2), for the kinds of :data:`KINDS`; the loop, the clock, the report
and its judging are those of ADR-0009 unchanged. A bf16 timing executable (the
timing program of one kind built with one kernel of that kind by
:func:`hilclaw.harness.bf16_timing_build.build_bf16_timing_executable`) takes
the repeats of one measurement in a process of its own and reports them on its
standard output in the form of :mod:`hilclaw.harness.timing`.
:func:`program_arguments` forms its command line and :func:`run_bf16_timing`
starts it and judges its report with
:func:`hilclaw.harness.timing.judge_report`, so the result is a
:class:`hilclaw.harness.timing.TimingResult` with the
:class:`hilclaw.harness.timing.Broken` values of
:func:`hilclaw.harness.timing.run_timing`.

Command line (decision 2), the arguments of :func:`program_arguments`: the
kind's dimensions in the order of its ``task_contract`` parameters, then the
five arguments that :func:`hilclaw.harness.timing.driver_arguments` gives
after ``m``, ``k`` and ``n``, spelled as it spells them::

    <executable> <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>   gemm
    <executable> <m> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>       the others

Conventions of this module (not rules of the record):

- A parameter outside what :func:`program_arguments` states raises
  :class:`hilclaw.harness.timing.TimingArgumentError` before anything is
  started, ``kind`` first, then ``dims``, then ``n_max``, ``sample_form`` and
  ``seed`` in the order of ``driver_arguments``. An ``executable`` that is an
  empty sequence or neither a path nor iterable raises a plain
  ``ValueError`` or ``TypeError``, and what :func:`hilclaw.local_run.run`
  raises is passed on.
- ``run`` of the result is what the runner captured, unfiltered.

What this module does not do: it builds nothing and holds no path of a
program; it gives no default to the sample form, the seed or the time limit;
it holds no ``eps`` (the ``rmsnorm`` program compiles it in); it passes no
input value to the program; and it registers no kind with ``sim.run``,
``board.run`` or the instance start (ADR-0181 decision 8).
"""

import os
import reprlib
import sys

from hilclaw import local_run
from hilclaw.harness import memory_ceiling, timing
from hilclaw.harness.measurement import N_MAX_DEFAULT
from hilclaw.harness.timing import Broken, TimingArgumentError, TimingResult

KINDS = ("gemm", "rmsnorm", "elementwise_add", "swiglu")
"""The kinds that have a bf16 timing program, in the order of ADR-0163."""

__all__ = ["KINDS", "program_arguments", "run_bf16_timing"]


def program_arguments(kind, dims, *, n_max, sample_form, seed):
    """Return the arguments of the timing program of ``kind`` as a tuple of ``str``.

    ``kind`` is exactly a ``str`` of :data:`KINDS`. ``dims`` is exactly a
    ``tuple`` of ``int``, ``(m, k, n)`` for ``gemm`` and ``(m, n)`` otherwise,
    each at least 1; a ``bool`` is not an ``int`` here. ``n_max``,
    ``sample_form`` and ``seed`` are those of
    :func:`hilclaw.harness.timing.driver_arguments`, and ``n_min`` and
    ``cv_max`` come from :mod:`hilclaw.harness.measurement` exactly as there.
    The result is the dimensions in order, then ``n_min``, ``n_max``,
    ``cv_max``, ``sample_form`` and ``seed``. Raises
    :class:`hilclaw.harness.timing.TimingArgumentError` otherwise, also for a
    dimension the interpreter cannot write in decimal digits.
    """
    if type(kind) is not str or kind not in KINDS:
        _fail("kind", f"one of {KINDS}", kind)
    length = 3 if kind == "gemm" else 2
    if type(dims) is not tuple or len(dims) != length:
        _fail("dims", f"a tuple of {length} ints for {kind}", dims)
    sizes = []
    for index, value in enumerate(dims):
        if type(value) is not int or value < 1:
            _fail(f"dims[{index}]", "an int of at least 1", value)
        try:
            sizes.append(str(value))
        except ValueError:
            _fail(
                f"dims[{index}]", "an int that can be written in decimal digits", value
            )
    rest = timing.driver_arguments(
        m=1, k=1, n=1, n_max=n_max, sample_form=sample_form, seed=seed
    )[3:]
    return (*sizes, *rest)


def run_bf16_timing(
    executable,
    kind,
    dims,
    *,
    sample_form,
    seed,
    timeout_s,
    n_max=N_MAX_DEFAULT,
    cwd=None,
    env=None,
):
    """Run one bf16 timing executable once and return a :class:`hilclaw.harness.timing.TimingResult`.

    One process ``<executable> <arguments>`` is started with
    :func:`hilclaw.local_run.run`, where the arguments are those of
    :func:`program_arguments`; ``timeout_s``, ``cwd`` and ``env`` are handed
    over unchanged. ``executable`` is a ``str`` or :class:`os.PathLike`, or a
    non-empty sequence that is used as the start of the command, and must have
    been built for ``kind``. Standard error is captured and never parsed.

    A run that timed out is ``Broken.TIMEOUT`` and one with an exit status
    other than 0 is ``Broken.EXIT_STATUS``, whatever it wrote. Otherwise its
    standard output is judged by :func:`hilclaw.harness.timing.judge_report`
    with ``sample_form`` and ``n_max``, giving ``Broken.REPORT_FORM``,
    ``Broken.ZERO_INTERVAL``, ``Broken.REPLAY`` or a completed run, as
    :func:`hilclaw.harness.timing.run_timing` does. Only a completed run, in
    either state, carries a memory figure: that of
    :func:`hilclaw.harness.memory_ceiling.figure` for ``run.max_rss`` and the
    :data:`sys.platform` read at the call.

    Raised before anything is started, in this order:
    :class:`hilclaw.harness.timing.TimingArgumentError` as in
    :func:`program_arguments`, :class:`TypeError` for an ``executable`` that
    is neither a path nor iterable, :class:`ValueError` for an empty
    ``executable`` sequence, and what :func:`hilclaw.local_run.run` raises for
    the command and the time limit. Its other errors, such as an
    :class:`OSError` from starting the process, are passed on as well.
    """
    arguments = program_arguments(
        kind, dims, n_max=n_max, sample_form=sample_form, seed=seed
    )
    if isinstance(executable, (str, bytes, os.PathLike)):
        prefix = (executable,)
    else:
        prefix = tuple(executable)
        if not prefix:
            raise ValueError("executable command prefix is empty")
    run = local_run.run((*prefix, *arguments), timeout_s=timeout_s, cwd=cwd, env=env)
    if run.timed_out:
        return TimingResult(Broken.TIMEOUT, None, None, None, run)
    if run.returncode != 0:
        return TimingResult(Broken.EXIT_STATUS, None, None, None, run)
    judgement = timing.judge_report(run.stdout, sample_form=sample_form, n_max=n_max)
    if judgement.broken is not None:
        return TimingResult(*judgement, run)
    memory = memory_ceiling.figure(run.max_rss, sys.platform)
    return TimingResult(*judgement, run, memory)


def _fail(name, rule, value):
    try:
        shown = reprlib.repr(value)
    except ValueError:
        shown = "too long to show"
    raise TimingArgumentError(
        f"{name}: must be {rule}, got {type(value).__name__} {shown}"
    )
