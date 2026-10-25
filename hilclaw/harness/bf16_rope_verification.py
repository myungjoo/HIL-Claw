"""Python side of a bf16 RoPE verification run of ADR-0164: judge its report, or start it and judge.

``ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`` is the
rule, for kind ``rope`` at ``cpu_standin``; a decision cited by its number
alone is one of that record. A bf16 RoPE verification executable (the program
``bf16_verification_rope.c`` built with one kernel of ADR-0161) reads the
``freqs_cis`` rows of the run on its standard input, draws ``x`` of each draw
from a seed in a process of its own and reports a check value and the
kernel's output per draw. :func:`judge_report` takes such a report and judges
it: whether it has the form of a complete report, whether the check value of
each draw is the one of ``x`` regenerated from the seed followed by the rows
(decision 9, a disagreement being broken and never a fail), and, if both hold,
the float64 reference and the count of the elements outside the tolerance per
draw (decisions 9 and 10) with :mod:`hilclaw.harness.bf16_rope_arrays`.
:func:`run_bf16_rope_verification` starts that process for an executable that
is already built, decides whether it timed out or failed and judges its report
in the same way. The result types and the end mark are the objects of
:mod:`hilclaw.harness.verification`, imported and not copied.

Command line (decision 7), the arguments of :func:`program_arguments`, each
decimal digits with no sign, no space and no leading zero::

    <executable> <m> <h> <d> <draws> <seed>

The start position P (``start``) is not on it (decision 4).

Standard input (decision 3): the 4·m·d bytes of
:func:`hilclaw.harness.bf16_rope_arrays.table_rows` for ``dims`` and
``start``, rows P … P+m−1, in memory order and the byte order of the host,
sent once per run and then closed. The rows are built once per run
(decision 5) and the same array serves every draw's check value and
reference, so no part of the reference rests on bytes from the process.

A complete report, read from the standard output, has
``draws * (4 + 2*m*h*d) + 4`` bytes: for each draw in order the check value
as the 4 bytes of a ``uint32_t``, then the m·h·d elements of the output as
the bytes of their ``uint16_t`` bf16 patterns, both in the byte order of the
host; after the last draw the 4 bytes ``end\\n`` (decision 10 and the header
comment of the program).

Conventions of this module (not rules of the record): those of
:mod:`hilclaw.harness.bf16_verification`, with ``dims`` and ``start`` in
place of ``kind`` and ``dims``. ``start`` is checked after ``dims``,
``draws`` and ``seed`` and before the tolerance, and every argument this
module checks is refused before the rows are built and before anything is
started; what :func:`hilclaw.local_run.run` refuses is refused after the
build and before the start.

What this module does not do: it builds nothing and holds no path of a
program; it holds no tolerance, seed, number of draws, dimension, start
position or time limit and gives none of them a default (decision 12); it
passes no tolerance and no P to the program (decisions 4 and 10); it sets no
environment variable and parses no standard error; it does not retry, repair,
store or cache anything and writes no file; it returns no element of the
inputs, the rows, the reference or the output; and it registers ``rope`` with
neither ``correctness.check``, ``spec.write`` nor the instance start
(ADR-0164 Boundaries).
"""

import math
import os
import struct

import numpy as np

from hilclaw import local_run
from hilclaw.harness import bf16_rope_arrays, verification_arrays
from hilclaw.harness.bf16_rope_arrays import _dims, _start
from hilclaw.harness.verification import (
    END_MARK,
    Broken,
    Judgement,
    Verdict,
    VerificationResult,
    _digits,
)

__all__ = [
    "END_MARK",
    "Broken",
    "Judgement",
    "Verdict",
    "VerificationResult",
    "judge_report",
    "program_arguments",
    "run_bf16_rope_verification",
]


def program_arguments(dims, *, draws, seed):
    """Return the arguments of the bf16 RoPE verification program as a tuple of ``str``.

    ``dims`` is exactly a ``tuple`` of three ``int``, ``(m, h, d)``, each at
    least 1, with ``d`` even. ``draws`` is an ``int`` with
    1 <= ``draws`` < 2**64 and ``seed`` an ``int`` with 0 <= ``seed`` < 2**64;
    a ``bool`` is not an ``int`` here. The result is ``m``, ``h``, ``d``,
    ``draws`` and ``seed``, spelled as in the module docstring. Raises
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
    otherwise, in the order of the parameters, also for an ``int`` the
    interpreter cannot write in decimal digits.
    """
    _dims(dims)
    last = verification_arrays.SEED_LIMIT - 1
    rule = "an int of at least 1 that can be written in decimal digits"
    sizes = [
        _digits(f"dims[{index}]", value, 1, math.inf, rule)
        for index, value in enumerate(dims)
    ]
    count = _digits("draws", draws, 1, last, "an int with 1 <= draws < 2**64")
    return (
        *sizes,
        count,
        _digits("seed", seed, 0, last, "an int with 0 <= seed < 2**64"),
    )


def judge_report(report, dims, *, start, draws, seed, rtol, atol):
    """Judge one report of a bf16 RoPE verification process and return a :class:`Judgement`.

    ``report`` is what the process wrote on its report channel, as exactly
    ``bytes`` in the form of the module docstring; ``dims``, ``draws`` and
    ``seed`` are the parameters that process was started with, as in
    :func:`program_arguments`, ``start`` the start position P of the rows it
    was sent, an ``int`` of at least 0 with (start + m)·d <= 2**53 - 1, and
    ``rtol`` and ``atol`` the tolerance of
    :func:`hilclaw.harness.bf16_rope_arrays.count_failures`. Every parameter
    after ``dims`` is keyword-only and none has a default.

    In this order: the length of a complete report for ``dims`` and ``draws``
    is compared with the length of ``report`` and the end mark is looked for,
    and a report that fails either is ``Broken.REPORT_FORM``; then the rows
    are built once and for each draw in order ``x`` is regenerated from
    ``seed``, the reported check value is compared with the one of ``x`` and
    the rows, and the output is counted against the float64 reference under
    the tolerance. The first check value that disagrees is
    ``Broken.CHECK_VALUE``. Otherwise the verdict is a pass when no element of
    any draw failed and a fail when one did. ``Broken.TIMEOUT`` and
    ``Broken.EXIT_STATUS`` are never returned.

    Raised before any byte of ``report`` is looked at and before the rows are
    built, in this order:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError` as
    in :func:`program_arguments`, the same for a refused ``start`` and for a
    tolerance that :func:`hilclaw.harness.verification_arrays.check_tolerance`
    refuses, and :class:`TypeError` for a ``report`` that is not exactly
    ``bytes``.
    """
    program_arguments(dims, draws=draws, seed=seed)
    _start(dims, start)
    verification_arrays.check_tolerance(rtol, atol)
    if type(report) is not bytes:
        raise TypeError(f"report: must be bytes, got {type(report).__name__}")
    return _judgement(report, dims, start, None, draws, seed, rtol, atol)


def run_bf16_rope_verification(
    executable,
    dims,
    *,
    start,
    draws,
    seed,
    rtol,
    atol,
    timeout_s,
    cwd=None,
    env=None,
):
    """Run one bf16 RoPE verification executable once and return a :class:`VerificationResult`.

    The rows of ``dims`` and ``start`` are built once, and one process
    ``<executable> <arguments>`` is started with :func:`hilclaw.local_run.run`
    with their bytes as its standard input, where the arguments are those of
    :func:`program_arguments`; ``timeout_s``, ``cwd`` and ``env`` are handed
    over unchanged. ``executable`` is a ``str`` or :class:`os.PathLike`, or a
    non-empty sequence that is used as the start of the command, and must have
    been built for ``rope``. ``start``, ``rtol`` and ``atol`` stay on this
    side.

    The run is completed only if it did not time out, its exit status is 0,
    its standard output has the form of a complete report and the check value
    of every draw agrees with the one of ``x`` and the rows that were sent;
    every other run is broken. The last two conditions and the verdict are
    those of :func:`judge_report`, with the same rows; a run that timed out or
    failed, including the program's status for wrong standard input, is broken
    whatever it wrote.

    Raised before the rows are built and anything is started, in this order:
    what :func:`judge_report` raises for its arguments,
    :class:`TypeError` for an ``executable`` that is neither a path nor
    iterable and :class:`ValueError` for an empty ``executable`` sequence;
    then, after the rows are built and before anything is started, what
    :func:`hilclaw.local_run.run` raises for the command, the time limit,
    ``env`` and ``cwd``. Its other errors are passed on as well.
    """
    arguments = program_arguments(dims, draws=draws, seed=seed)
    _start(dims, start)
    verification_arrays.check_tolerance(rtol, atol)
    if isinstance(executable, (str, bytes, os.PathLike)):
        prefix = (executable,)
    else:
        prefix = tuple(executable)
        if not prefix:
            raise ValueError("executable command prefix is empty")
    rows = bf16_rope_arrays.table_rows(dims, start=start)
    run = local_run.run(
        (*prefix, *arguments),
        timeout_s=timeout_s,
        cwd=cwd,
        env=env,
        stdin_data=rows.tobytes(),
    )
    report = run.stdout
    run = run._replace(stdout=b"")
    if run.timed_out:
        return VerificationResult(Broken.TIMEOUT, None, None, run)
    if run.returncode != 0:
        return VerificationResult(Broken.EXIT_STATUS, None, None, run)
    judgement = _judgement(report, dims, start, rows, draws, seed, rtol, atol)
    return VerificationResult(*judgement, run)


def _judgement(report, dims, start, rows, draws, seed, rtol, atol):
    m, h, d = dims
    block = 4 + 2 * m * h * d
    if len(report) != draws * block + 4 or not report.endswith(END_MARK):
        return Judgement(Broken.REPORT_FORM, None, None)
    if rows is None:
        rows = bf16_rope_arrays.table_rows(dims, start=start)
    counts = []
    for draw in range(draws):
        taken = _counts(report, draw * block, dims, rows, seed, draw, rtol, atol)
        if taken is None:
            return Judgement(Broken.CHECK_VALUE, None, None)
        counts.append(taken)
    failed = any(count.failed for count in counts)
    return Judgement(None, Verdict.FAIL if failed else Verdict.PASS, tuple(counts))


def _counts(report, offset, dims, rows, seed, draw, rtol, atol):
    arrays = bf16_rope_arrays
    x = arrays.draw_x(dims, seed=seed, draw=draw)
    (reported,) = struct.unpack_from("=I", report, offset)
    if reported != arrays.check_value(x, rows):
        return None
    output = np.frombuffer(report, dtype=np.uint16, count=x.size, offset=offset + 4)
    expected = arrays.reference(x, rows)
    return arrays.count_failures(output.reshape(dims), expected, rtol=rtol, atol=atol)
