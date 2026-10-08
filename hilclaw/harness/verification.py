"""Python side of a verification run of ADR-0017: judge its report, or start it and judge.

``ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`` is the
rule; a decision cited by its number alone is one of that record. A
verification executable (the verification program of the harness built with
one kernel) draws the inputs of each draw from a seed in a process of its own
and reports a check value and the kernel's output per draw.
:func:`judge_report` takes such a report and judges it: whether it has the
form of a complete report, whether the check value of each draw is the one of
the inputs regenerated from the seed, and, if both hold, the reference and the
count of the elements outside the tolerance per draw with
:mod:`hilclaw.harness.verification_arrays` (decisions 4, 5 and 7).
:func:`run_verification` starts that process for an executable that is already
built, decides whether it timed out or failed (decision 7) and judges its
report in the same way.

The judging is available without a process start because
``ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md`` (its
decision 2) gives all of it to the side that is the same for every backend.
:func:`run_verification` remains the run of a verification on one machine and
is about no run of the data plane.

Command line and report are those of the header comment of
``verification_program.c``. Exactly five arguments, each decimal digits with no
sign, no space and no leading zero::

    <executable> <m> <k> <n> <draws> <seed>

A complete report, read from the standard output, has
``draws * (4 + 4*m*n) + 4`` bytes: for each draw in order the check value as
the 4 bytes of a ``uint32_t``, then the ``m*n`` elements of the output in
row-major order as the ``4*m*n`` bytes of their ``float`` values, both in the
byte order of the host; after the last draw the 4 bytes ``end\\n``.

Conventions of this module (not rules of the record):

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
  the draws; :func:`judge_report` and :func:`run_verification` both use it.
- The ``report`` argument of :func:`judge_report` is exactly ``bytes``. For
  anything else, a ``bytearray``, a ``memoryview`` and an instance of a
  subclass included, it raises a ``TypeError`` and never reports a wrong
  form: that condition is a statement about what a process wrote.
- ``run`` of a :class:`VerificationResult` is what the runner captured apart
  from the report: its ``stdout`` is replaced by ``b""`` and every other
  member is passed on unfiltered. The record says so of a broken run; this
  module carries the same member for a completed run. Standard error and the
  command line are not free of the inputs (decision 7); what a caller may
  keep of them is not decided here.
- ``executable`` is a path or a sequence used as a command prefix, as in
  :func:`hilclaw.harness.timing.run_timing`.
- A parameter of the program or a tolerance outside what is stated raises
  :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
  before anything is started and before a report is looked at, so one class
  covers the whole verification. An ``executable`` that is an empty sequence
  or neither a path nor iterable raises a plain ``ValueError`` or
  ``TypeError``, and what :func:`hilclaw.local_run.run` raises is passed on.
- What NumPy raises for arrays it cannot allocate (``MemoryError``, or a plain
  ``ValueError`` for a size it cannot hold) is passed on. In
  :func:`run_verification` it arrives after the process has ended, and the
  caller gets no result for that run.

What this module does not do: it builds nothing and holds no path of the
program; it holds no tolerance value, seed, source of a seed, number of draws
or dimension and gives none of them, nor the time limit, a default (decision
6); it passes no tolerance to the program (decision 5); it sets no environment
variable and parses no standard error; it puts no time limit on its own work
(decision 10); it does not retry, repair or store anything and writes no file;
and it returns no index, deviation or element (decision 7).
"""

import enum
import math
import os
import reprlib
import struct
from typing import NamedTuple

import numpy as np

from hilclaw import local_run
from hilclaw.harness import verification_arrays
from hilclaw.harness.verification_arrays import Counts, VerificationArgumentError

END_MARK = b"end\n"


class Broken(enum.Enum):
    """The condition of a completed run (decision 7) that a broken run failed first."""

    TIMEOUT = enum.auto()
    EXIT_STATUS = enum.auto()
    REPORT_FORM = enum.auto()
    CHECK_VALUE = enum.auto()


class Verdict(enum.Enum):
    """The verdict of a completed run (decision 7)."""

    PASS = enum.auto()
    FAIL = enum.auto()


class Judgement(NamedTuple):
    """Outcome of one :func:`judge_report` call: the judgement of one report.

    For a report that has the form of a complete report and whose check
    values all agree, ``broken`` is ``None``, ``verdict`` is ``Verdict.PASS``
    when no element of any draw failed the tolerance and ``Verdict.FAIL``
    otherwise, and ``counts`` holds one
    :class:`hilclaw.harness.verification_arrays.Counts` per draw in order. For
    any other report ``broken`` is ``Broken.REPORT_FORM`` or
    ``Broken.CHECK_VALUE`` and ``verdict`` and ``counts`` are ``None``,
    whatever the draws of the report hold: it is neither a pass nor a fail.

    Nothing else is held: no capture of a process, no byte of the report, no
    seed, and no index, deviation or element of the inputs, the reference or
    the output (decision 7).
    """

    broken: Broken | None
    verdict: Verdict | None
    counts: tuple[Counts, ...] | None


class VerificationResult(NamedTuple):
    """Outcome of one :func:`run_verification` call.

    The first three members are those of :class:`Judgement`, with the two
    conditions a process can fail before it has a report to judge added.
    For a completed run ``broken`` is ``None``, ``verdict`` is
    ``Verdict.PASS`` when no element of any draw failed the tolerance and
    ``Verdict.FAIL`` otherwise, and ``counts`` holds one
    :class:`hilclaw.harness.verification_arrays.Counts` per draw in order. For
    a broken run ``broken`` names the failed condition and ``verdict`` and
    ``counts`` are ``None``, whatever the draws it reported hold: a broken run
    is neither a pass nor a fail. ``run`` is what the runner captured with an
    empty ``stdout``, in both cases.
    """

    broken: Broken | None
    verdict: Verdict | None
    counts: tuple[Counts, ...] | None
    run: local_run.RunResult


def program_arguments(*, m, k, n, draws, seed):
    """Return the five arguments of the verification program as a tuple of ``str``.

    The order and spelling are those of the module docstring. ``m``, ``k`` and
    ``n`` are exactly ``int`` and at least 1, ``draws`` is an ``int`` with
    1 <= ``draws`` < 2**64 and ``seed`` an ``int`` with 0 <= ``seed`` < 2**64;
    a ``bool`` is not an ``int`` here. Raises
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
    otherwise, also for an ``int`` the interpreter cannot write in decimal
    digits.
    """
    last = verification_arrays.SEED_LIMIT - 1
    rule = "an int of at least 1 that can be written in decimal digits"
    sizes = [
        _digits(name, value, 1, math.inf, rule)
        for name, value in (("m", m), ("k", k), ("n", n))
    ]
    count = _digits("draws", draws, 1, last, "an int with 1 <= draws < 2**64")
    return (
        *sizes,
        count,
        _digits("seed", seed, 0, last, "an int with 0 <= seed < 2**64"),
    )


def judge_report(report, *, m, k, n, draws, seed, rtol, atol):
    """Judge one report of a verification process and return a :class:`Judgement`.

    ``report`` is what a verification process wrote on its report channel, as
    exactly ``bytes`` in the form of the module docstring; ``m``, ``k``, ``n``,
    ``draws`` and ``seed`` are the parameters that process was started with,
    as in :func:`program_arguments`, and ``rtol`` and ``atol`` the tolerance
    of :func:`hilclaw.harness.verification_arrays.count_failures`. All but
    ``report`` are keyword-only and none has a default.

    In this order: the length of a complete report for ``m``, ``n`` and
    ``draws`` is compared with the length of ``report`` and the end mark is
    looked for, and a report that fails either is ``Broken.REPORT_FORM``; then
    for each draw in order the inputs are regenerated from ``seed``, the
    reported check value is compared with theirs, and the output is counted
    against the float64 reference under the tolerance. The first check value
    that disagrees is ``Broken.CHECK_VALUE``. Otherwise the verdict is a pass
    when no element of any draw failed and a fail when one did.

    Whether a process ended by itself, with which status and within which
    time is not known here: ``Broken.TIMEOUT`` and ``Broken.EXIT_STATUS`` are
    never returned, and what a process that timed out or failed wrote is not
    a report to hand over.

    The function starts no process, reads and writes no file, reads no
    environment variable, clock or random source and keeps nothing between
    calls: its outcome follows from its arguments alone.

    Raised before any byte of ``report`` is looked at, in this order:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError` as
    in :func:`program_arguments`, the same for a tolerance that
    :func:`hilclaw.harness.verification_arrays.check_tolerance` refuses, and
    :class:`TypeError` for a ``report`` that is not exactly ``bytes``. What
    NumPy raises for arrays it cannot allocate is passed on.
    """
    program_arguments(m=m, k=k, n=n, draws=draws, seed=seed)
    verification_arrays.check_tolerance(rtol, atol)
    if type(report) is not bytes:
        raise TypeError(f"report: must be bytes, got {type(report).__name__}")
    return _judgement(report, m, k, n, draws, seed, rtol, atol)


def run_verification(
    executable,
    *,
    m,
    k,
    n,
    draws,
    seed,
    rtol,
    atol,
    timeout_s,
    cwd=None,
    env=None,
):
    """Run one verification executable once and return a :class:`VerificationResult`.

    One process ``<executable> <arguments>`` is started with
    :func:`hilclaw.local_run.run`, where the arguments are those of
    :func:`program_arguments`; ``timeout_s``, ``cwd`` and ``env`` are handed
    over unchanged. ``executable`` is a ``str`` or :class:`os.PathLike`, or a
    non-empty sequence that is used as the start of the command. ``rtol`` and
    ``atol`` are the tolerance of
    :func:`hilclaw.harness.verification_arrays.count_failures`; they stay on
    this side.

    The run is completed only if it did not time out, its exit status is 0,
    its standard output has the form of a complete report for ``m``, ``n`` and
    ``draws``, and the check value of every draw equals the one of the inputs
    regenerated from ``seed``. Every other run is broken. The last two
    conditions and the verdict are those of :func:`judge_report` for the
    standard output; a run that timed out or failed is broken whatever it
    wrote.

    Raised before anything is started, in this order:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError` as
    in :func:`program_arguments`, the same for a tolerance that
    :func:`hilclaw.harness.verification_arrays.check_tolerance` refuses,
    :class:`TypeError` for an ``executable`` that is neither a path nor
    iterable, :class:`ValueError` for an empty ``executable`` sequence, and
    what :func:`hilclaw.local_run.run` raises for the command and the time
    limit. Its other errors, and those of NumPy for arrays it cannot allocate,
    are passed on as well.
    """
    arguments = program_arguments(m=m, k=k, n=n, draws=draws, seed=seed)
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
    judgement = _judgement(report, m, k, n, draws, seed, rtol, atol)
    return VerificationResult(*judgement, run)


def _judgement(report, m, k, n, draws, seed, rtol, atol):
    block = 4 + 4 * m * n
    if len(report) != draws * block + 4 or not report.endswith(END_MARK):
        return Judgement(Broken.REPORT_FORM, None, None)
    counts = []
    for draw in range(draws):
        taken = _counts(report, draw * block, m, k, n, seed, draw, rtol, atol)
        if taken is None:
            return Judgement(Broken.CHECK_VALUE, None, None)
        counts.append(taken)
    failed = any(count.failed for count in counts)
    return Judgement(None, Verdict.FAIL if failed else Verdict.PASS, tuple(counts))


def _counts(report, start, m, k, n, seed, draw, rtol, atol):
    a, b = verification_arrays.draw_inputs(m, k, n, seed=seed, draw=draw)
    (reported,) = struct.unpack_from("=I", report, start)
    if reported != verification_arrays.check_value(a, b):
        return None
    output = np.frombuffer(report, dtype=np.float32, count=m * n, offset=start + 4)
    expected = verification_arrays.reference(a, b)
    return verification_arrays.count_failures(
        output.reshape(m, n), expected, rtol=rtol, atol=atol
    )


def _digits(name, value, minimum, maximum, rule):
    if type(value) is int and minimum <= value <= maximum:
        try:
            return str(value)
        except ValueError:
            pass
    shown = type(value).__name__
    if type(value) in (float, bool, str, type(None)) or (
        type(value) is int and abs(value) < verification_arrays.SEED_LIMIT**2
    ):
        shown += f" {reprlib.repr(value)}"
    raise VerificationArgumentError(f"{name}: must be {rule}, got {shown}")
