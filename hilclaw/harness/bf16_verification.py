"""Python side of a bf16 verification run of ADR-0163: judge its report, or start it and judge.

``ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`` is the rule,
for the kinds of :data:`hilclaw.harness.bf16_verification_arrays.KINDS` at
``cpu_standin``; a decision cited by its number alone is one of that record.
A bf16 verification executable (the verification program of one kind built
with one kernel of that kind) draws the inputs of each draw from a seed in a
process of its own and reports a check value and the kernel's output per draw.
:func:`judge_report` takes such a report and judges it: whether it has the
form of a complete report, whether the check value of each draw is the one of
the inputs regenerated from the seed (decision 6, a disagreement being broken
and never a fail), and, if both hold, the float64 reference and the count of
the elements outside the tolerance per draw (decisions 6 and 7) with
:mod:`hilclaw.harness.bf16_verification_arrays`.
:func:`run_bf16_verification` starts that process for an executable that is
already built, decides whether it timed out or failed and judges its report in
the same way. Completed, broken, pass and fail are those of ADR-0017 decision 7
with the length of decision 8, so the result types and the end mark are the
objects of :mod:`hilclaw.harness.verification`, imported and not copied: a
caller handles one set of result types for both runs.

Command line (decision 3), the arguments of :func:`program_arguments`, each
decimal digits with no sign, no space and no leading zero::

    <executable> <m> <k> <n> <draws> <seed>     gemm
    <executable> <m> <n> <draws> <seed>         rmsnorm, elementwise_add, swiglu

A complete report, read from the standard output, has
``draws * (4 + 2*m*n) + 4`` bytes, with ``m`` and ``n`` the first and the last
dimension: for each draw in order the check value as the 4 bytes of a
``uint32_t``, then the ``m*n`` elements of the output in row-major order as the
``2*m*n`` bytes of their ``uint16_t`` bf16 patterns, both in the byte order of
the host; after the last draw the 4 bytes ``end\\n`` (decision 8 and the header
comments of the four programs).

Conventions of this module (not rules of the record), those of
:mod:`hilclaw.harness.verification` with ``kind`` and ``dims`` in place of
``m``, ``k`` and ``n``:

- The conditions of a completed run are tested in the order of
  :class:`Broken`, and the first that fails is the one reported. A signal is
  not told apart from a non-zero exit status; ``run.returncode`` shows it.
  :func:`judge_report` has no process and tests the last two only.
- The length of a complete report is computed from ``m``, ``n`` and ``draws``
  alone and compared before any byte is read; no output byte is interpreted
  to find a boundary, and nothing is allocated from the expected length.
- Draws are handled one at a time and in order: the inputs are regenerated,
  the check value is compared, then the counts are taken. The first check
  value that disagrees makes the run broken and the counts taken so far are
  dropped. No array of a draw is kept for the next.
- The module holds one implementation of the form check and of the loop over
  the draws; :func:`judge_report` and :func:`run_bf16_verification` both use
  it.
- The ``report`` argument of :func:`judge_report` is exactly ``bytes``; for
  anything else it raises a ``TypeError`` and never reports a wrong form.
- ``run`` of a :class:`VerificationResult` is what the runner captured apart
  from the report: its ``stdout`` is replaced by ``b""`` and every other
  member is passed on unfiltered, for a completed and for a broken run.
- ``executable`` is a path or a sequence used as a command prefix.
- ``kind``, ``dims``, ``draws``, ``seed`` or a tolerance outside what is
  stated raises
  :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
  before anything is started and before a report is looked at. An
  ``executable`` that is an empty sequence or neither a path nor iterable
  raises a plain ``ValueError`` or ``TypeError``, and what
  :func:`hilclaw.local_run.run` raises is passed on, as are NumPy's errors for
  arrays it cannot allocate.

What this module does not do: it builds nothing and holds no path of a
program; it holds no tolerance value, seed, number of draws, dimension or time
limit and gives none of them a default (decision 10); it passes no tolerance
and no ``eps`` to the program (decisions 3 and 7); it sets no environment
variable and parses no standard error; it does not retry, repair or store
anything and writes no file; it returns no index, deviation or element of the
inputs, the reference or the output (decision 8); and it registers no kind
with ``correctness.check``, ``spec.write`` or the instance start (ADR-0163
Boundaries).
"""

import math
import os
import struct

import numpy as np

from hilclaw import local_run
from hilclaw.harness import bf16_verification_arrays, verification_arrays
from hilclaw.harness.bf16_verification_arrays import _shapes
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
    "run_bf16_verification",
]


def program_arguments(kind, dims, *, draws, seed):
    """Return the arguments of the verification program of ``kind`` as a tuple of ``str``.

    ``kind`` is exactly a ``str`` of
    :data:`hilclaw.harness.bf16_verification_arrays.KINDS`. ``dims`` is exactly
    a ``tuple`` of ``int``, ``(m, k, n)`` for ``gemm`` and ``(m, n)``
    otherwise, each at least 1. ``draws`` is an ``int`` with
    1 <= ``draws`` < 2**64 and ``seed`` an ``int`` with 0 <= ``seed`` < 2**64;
    a ``bool`` is not an ``int`` here. The result is the dimensions in order,
    then ``draws``, then ``seed``, spelled as in the module docstring. Raises
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
    otherwise, in the order of the parameters, also for an ``int`` the
    interpreter cannot write in decimal digits.
    """
    _shapes(kind, dims)
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


def judge_report(report, kind, dims, *, draws, seed, rtol, atol):
    """Judge one report of a bf16 verification process and return a :class:`Judgement`.

    ``report`` is what the process wrote on its report channel, as exactly
    ``bytes`` in the form of the module docstring; ``kind``, ``dims``,
    ``draws`` and ``seed`` are the parameters that process was started with,
    as in :func:`program_arguments`, and ``rtol`` and ``atol`` the tolerance
    of :func:`hilclaw.harness.bf16_verification_arrays.count_failures`.
    ``draws``, ``seed``, ``rtol`` and ``atol`` are keyword-only and no
    parameter has a default.

    In this order: the length of a complete report for ``m``, ``n`` and
    ``draws`` is compared with the length of ``report`` and the end mark is
    looked for, and a report that fails either is ``Broken.REPORT_FORM``; then
    for each draw in order the operands are regenerated from ``seed``, the
    reported check value is compared with theirs, and the output is counted
    against the float64 reference of ``kind`` under the tolerance. The first
    check value that disagrees is ``Broken.CHECK_VALUE``. Otherwise the
    verdict is a pass when no element of any draw failed and a fail when one
    did. ``Broken.TIMEOUT`` and ``Broken.EXIT_STATUS`` are never returned.

    The function starts no process, reads and writes no file and keeps nothing
    between calls: its outcome follows from its arguments alone.

    Raised before any byte of ``report`` is looked at, in this order:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError` as
    in :func:`program_arguments`, the same for a tolerance that
    :func:`hilclaw.harness.verification_arrays.check_tolerance` refuses, and
    :class:`TypeError` for a ``report`` that is not exactly ``bytes``.
    """
    program_arguments(kind, dims, draws=draws, seed=seed)
    verification_arrays.check_tolerance(rtol, atol)
    if type(report) is not bytes:
        raise TypeError(f"report: must be bytes, got {type(report).__name__}")
    return _judgement(report, kind, dims, draws, seed, rtol, atol)


def run_bf16_verification(
    executable,
    kind,
    dims,
    *,
    draws,
    seed,
    rtol,
    atol,
    timeout_s,
    cwd=None,
    env=None,
):
    """Run one bf16 verification executable once and return a :class:`VerificationResult`.

    One process ``<executable> <arguments>`` is started with
    :func:`hilclaw.local_run.run`, where the arguments are those of
    :func:`program_arguments`; ``timeout_s``, ``cwd`` and ``env`` are handed
    over unchanged. ``executable`` is a ``str`` or :class:`os.PathLike`, or a
    non-empty sequence that is used as the start of the command, and must have
    been built for ``kind``. ``rtol`` and ``atol`` stay on this side.

    The run is completed only if it did not time out, its exit status is 0,
    its standard output has the form of a complete report and the check value
    of every draw agrees; every other run is broken. The last two conditions
    and the verdict are those of :func:`judge_report` for the standard output;
    a run that timed out or failed is broken whatever it wrote.

    Raised before anything is started, in this order:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError` as
    in :func:`program_arguments`, the same for a tolerance that
    :func:`hilclaw.harness.verification_arrays.check_tolerance` refuses,
    :class:`TypeError` for an ``executable`` that is neither a path nor
    iterable, :class:`ValueError` for an empty ``executable`` sequence, and
    what :func:`hilclaw.local_run.run` raises for the command and the time
    limit. Its other errors are passed on as well.
    """
    arguments = program_arguments(kind, dims, draws=draws, seed=seed)
    verification_arrays.check_tolerance(rtol, atol)
    if isinstance(executable, (str, bytes, os.PathLike)):
        prefix = (executable,)
    else:
        prefix = tuple(executable)
        if not prefix:
            raise ValueError("executable command prefix is empty")
    run = local_run.run((*prefix, *arguments), timeout_s=timeout_s, cwd=cwd, env=env)
    report = run.stdout
    run = run._replace(stdout=b"")
    if run.timed_out:
        return VerificationResult(Broken.TIMEOUT, None, None, run)
    if run.returncode != 0:
        return VerificationResult(Broken.EXIT_STATUS, None, None, run)
    judgement = _judgement(report, kind, dims, draws, seed, rtol, atol)
    return VerificationResult(*judgement, run)


def _judgement(report, kind, dims, draws, seed, rtol, atol):
    m, n = dims[0], dims[-1]
    block = 4 + 2 * m * n
    if len(report) != draws * block + 4 or not report.endswith(END_MARK):
        return Judgement(Broken.REPORT_FORM, None, None)
    counts = []
    for draw in range(draws):
        taken = _counts(report, draw * block, kind, dims, seed, draw, rtol, atol)
        if taken is None:
            return Judgement(Broken.CHECK_VALUE, None, None)
        counts.append(taken)
    failed = any(count.failed for count in counts)
    return Judgement(None, Verdict.FAIL if failed else Verdict.PASS, tuple(counts))


def _counts(report, start, kind, dims, seed, draw, rtol, atol):
    arrays = bf16_verification_arrays
    first, second = arrays.draw_inputs(kind, dims, seed=seed, draw=draw)
    (reported,) = struct.unpack_from("=I", report, start)
    if reported != arrays.check_value(first, second):
        return None
    m, n = dims[0], dims[-1]
    output = np.frombuffer(report, dtype=np.uint16, count=m * n, offset=start + 4)
    expected = arrays.reference(kind, first, second)
    return arrays.count_failures(output.reshape(m, n), expected, rtol=rtol, atol=atol)
