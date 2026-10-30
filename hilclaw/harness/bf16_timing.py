"""Python side of a bf16 timing run of ADR-0181: the command line of a kind, and a run judged by :mod:`hilclaw.harness.timing`.

``ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`` decision 2 is the
rule. A timing program of :data:`KINDS`, built by
:mod:`hilclaw.harness.bf16_timing_build`, takes its arguments from
:func:`program_arguments` and reports in the form of ADR-0009 decision 8;
:func:`run_bf16_timing` starts it and judges it as
:func:`hilclaw.harness.timing.run_timing` does::

    <executable> <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>   gemm
    <executable> <m> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>       the others

It builds nothing, gives no default to the sample form, the seed or the time
limit, and registers no kind with a run tool (ADR-0181 decision 8).
"""

import os
import reprlib
import sys

from hilclaw import local_run
from hilclaw.harness import memory_ceiling, timing
from hilclaw.harness.measurement import N_MAX_DEFAULT
from hilclaw.harness.timing import Broken, TimingArgumentError, TimingResult

KINDS = ("gemm", "rmsnorm", "elementwise_add", "swiglu")

__all__ = ["KINDS", "program_arguments", "run_bf16_timing"]


def program_arguments(kind, dims, *, n_max, sample_form, seed):
    """Return the arguments of the timing program of ``kind`` as a tuple of ``str``.

    ``kind`` is exactly a ``str`` of :data:`KINDS`; ``dims`` is exactly a
    ``tuple`` of ``int`` (not ``bool``), ``(m, k, n)`` for ``gemm`` and
    ``(m, n)`` otherwise, each at least 1. The dimensions are followed by the
    last five arguments of :func:`hilclaw.harness.timing.driver_arguments`,
    which checks ``n_max``, ``sample_form`` and ``seed``. Raises
    :class:`hilclaw.harness.timing.TimingArgumentError` otherwise, testing
    ``kind``, then ``dims``, then the rest.
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
    """Run one bf16 timing executable built for ``kind`` once and return a :class:`hilclaw.harness.timing.TimingResult`.

    The process and the result are those of
    :func:`hilclaw.harness.timing.run_timing` with the arguments of
    :func:`program_arguments`: ``Broken.TIMEOUT`` and ``Broken.EXIT_STATUS``
    first, then :func:`hilclaw.harness.timing.judge_report` on the standard
    output, and the memory figure of
    :func:`hilclaw.harness.memory_ceiling.figure` for a completed run only.
    What is raised before anything is started is also as there, with
    :func:`program_arguments` in place of ``driver_arguments``.
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
