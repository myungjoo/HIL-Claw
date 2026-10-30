"""Python side of a bf16 timing run of ADR-0181: the command line of a kind, and a run judged by :mod:`hilclaw.harness.timing`.

``ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`` decision 2 is the
rule. A timing program of :data:`KINDS`, built by
:mod:`hilclaw.harness.bf16_timing_build`, takes its arguments from
:func:`program_arguments` and reports in the form of ADR-0009 decision 8;
:func:`run_bf16_timing` starts it and judges it as
:func:`hilclaw.harness.timing.run_timing` does::

    <executable> <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>   gemm
    <executable> <m> <h> <d> <n_min> <n_max> <cv_max> <sample_form> <seed>   rope
    <executable> <m> <l> <h> <h_kv> <d> <n_min> <n_max> <cv_max> <sample_form> <seed>   sdpa_kv_cache
    <executable> <m> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>       the others

A ``rope`` run also takes the ``freqs_cis`` rows on standard input, at the
start position of ADR-0180 decision 1 for its seed; no other kind has standard
input. Building them is what needs NumPy, so the imports that do are made when
a ``rope`` run starts and importing this module imports no NumPy.

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

_DIMENSIONS = {
    "gemm": 3,
    "rmsnorm": 2,
    "elementwise_add": 2,
    "swiglu": 2,
    "rope": 3,
    "sdpa_kv_cache": 5,
}

KINDS = tuple(_DIMENSIONS)

__all__ = ["KINDS", "program_arguments", "run_bf16_timing"]


def program_arguments(kind, dims, *, n_max, sample_form, seed):
    """Return the arguments of the timing program of ``kind`` as a tuple of ``str``.

    ``kind`` is exactly a ``str`` of :data:`KINDS`; ``dims`` is exactly a
    ``tuple`` of ``int`` (not ``bool``), each at least 1: ``(m, k, n)`` for
    ``gemm``, ``(m, h, d)`` with ``d`` even for ``rope``, ``(m, l, h, h_kv, d)``
    with l >= m and ``h`` a multiple of ``h_kv`` for ``sdpa_kv_cache``, and
    ``(m, n)`` otherwise. The dimensions are followed by the
    last five arguments of :func:`hilclaw.harness.timing.driver_arguments`,
    which checks ``n_max``, ``sample_form`` and ``seed``. Raises
    :class:`hilclaw.harness.timing.TimingArgumentError` otherwise, testing
    ``kind``, then ``dims``, then the rest.
    """
    if type(kind) is not str or kind not in KINDS:
        _fail("kind", f"one of {KINDS}", kind)
    length = _DIMENSIONS[kind]
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
    if kind == "rope" and dims[2] % 2:
        _fail("dims[2]", "even for rope", dims[2])
    if kind == "sdpa_kv_cache":
        if dims[1] < dims[0]:
            _fail("dims[1]", "at least m for sdpa_kv_cache", dims[1])
        if dims[2] % dims[3]:
            _fail("dims[2]", "a multiple of h_kv for sdpa_kv_cache", dims[2])
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

    For ``rope`` the process gets the rows of ``dims`` at
    :func:`hilclaw.harness.bf16_rope_verification.start_position` for ``seed``
    as its standard input, built after those checks; a position whose rows the
    table cannot have raises :class:`hilclaw.harness.timing.TimingArgumentError`
    before anything is started. The program's status for wrong input is a
    ``Broken.EXIT_STATUS``.
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
    stdin_data = _rope_rows(dims, seed) if kind == "rope" else None
    run = local_run.run(
        (*prefix, *arguments),
        timeout_s=timeout_s,
        cwd=cwd,
        env=env,
        stdin_data=stdin_data,
    )
    if run.timed_out:
        return TimingResult(Broken.TIMEOUT, None, None, None, run)
    if run.returncode != 0:
        return TimingResult(Broken.EXIT_STATUS, None, None, None, run)
    judgement = timing.judge_report(run.stdout, sample_form=sample_form, n_max=n_max)
    if judgement.broken is not None:
        return TimingResult(*judgement, run)
    memory = memory_ceiling.figure(run.max_rss, sys.platform)
    return TimingResult(*judgement, run, memory)


def _rope_rows(dims, seed):
    from hilclaw.harness import bf16_rope_arrays, bf16_rope_verification
    from hilclaw.harness.verification_arrays import VerificationArgumentError

    try:
        start = bf16_rope_verification.start_position(dims, seed=seed)
    except VerificationArgumentError as error:
        raise TimingArgumentError(str(error)) from error
    return bf16_rope_arrays.table_rows(dims, start=start).tobytes()


def _fail(name, rule, value):
    try:
        shown = reprlib.repr(value)
    except ValueError:
        shown = "too long to show"
    raise TimingArgumentError(
        f"{name}: must be {rule}, got {type(value).__name__} {shown}"
    )
