"""Python side of a bf16 SDPA-with-KV-cache verification run of ADR-0165: judge its report, or start it and judge.

``ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md``
is the rule, for kind ``sdpa_kv_cache`` at ``cpu_standin``; a decision cited
by its number alone is one of that record. A bf16 SDPA-with-KV-cache
verification executable (the program ``bf16_verification_sdpa_kv_cache.c``
built with one kernel of ADR-0162) draws the inputs of each draw from a seed
in a process of its own, sets the fills of both cache allocations and reports
a check value, the kernel's output and both allocations per draw.
:func:`judge_report` takes such a report and judges it: whether it has the
form of a complete report, whether the check value of each draw is the one of
the inputs and allocations regenerated from the seed (decision 7, a
disagreement being broken and never a fail), and, if both hold, the count of
the elements of ``out`` outside the tolerance against the float64 reference
(decisions 6 and 9) and the count of the cache elements that differ (decision
8), with :mod:`hilclaw.harness.bf16_sdpa_kv_cache_arrays`.
:func:`run_bf16_sdpa_kv_cache_verification` starts that process for an
executable that is already built, decides whether it timed out or failed and
judges its report in the same way. The result types and the end mark are the
objects of :mod:`hilclaw.harness.verification`, imported and not copied.

Command line (decision 3), the arguments of :func:`program_arguments`, each
decimal digits with no sign, no space and no leading zero::

    <executable> <m> <l> <h> <h_kv> <d> <draws> <seed>

P = l − m, the number of cached rows, is derived on both sides and is not on
it. No standard input is sent (decision 2): the process gets the null device.

A complete report, read from the standard output, has
``draws * (4 + 2*m*h*d + 4*(l + 2*m)*h_kv*d) + 4`` bytes: for each draw in
order the check value as the 4 bytes of a ``uint32_t``, then the m·h·d
elements of ``out``, then the (l + 2m)·h_kv·d elements of the ``cache_k``
allocation and then those of the ``cache_v`` allocation, each element as the
bytes of its ``uint16_t`` bf16 pattern, all in the byte order of the host;
after the last draw the 4 bytes ``end\\n`` (decision 8 and the header comment
of the program).

Cache comparison (decision 8): each reported allocation is compared bit for
bit, with no tolerance, with the allocation a conforming kernel leaves,
:func:`hilclaw.harness.bf16_sdpa_kv_cache_arrays.allocation_after` of the
Python side's own regenerated arrays; no expected byte and no part of the
reference is taken from the report.

Verdict (decision 8): a completed run passes iff in every draw no element of
``out`` fails the tolerance and no element of either allocation differs, and
fails otherwise. Its counts are one :class:`DrawCounts` per draw.

Conventions of this module (not rules of the record): those of
:mod:`hilclaw.harness.bf16_rope_verification`, with ``dims`` the five
entries ``(m, l, h, h_kv, d)`` checked as in
:mod:`hilclaw.harness.bf16_sdpa_kv_cache_arrays`, and no ``start``.

What this module does not do: it builds nothing and holds no path of a
program; it holds no tolerance, seed, number of draws, dimension or time
limit and gives none of them a default (decision 11); it passes no tolerance
to the program (decision 9), sends no standard input, sets no environment
variable and parses no standard error; it does not retry, repair, store or
cache anything and writes no file; it returns no element, index or region of
the inputs, the allocations, the reference or the output; and it registers
``sdpa_kv_cache`` with neither ``correctness.check``, ``spec.write`` nor the
instance start (ADR-0165 Boundaries).
"""

import math
import os
import struct
from typing import NamedTuple

import numpy as np

from hilclaw import local_run
from hilclaw.harness import bf16_sdpa_kv_cache_arrays, verification_arrays
from hilclaw.harness.bf16_sdpa_kv_cache_arrays import _dims
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
    "DrawCounts",
    "Judgement",
    "Verdict",
    "VerificationResult",
    "judge_report",
    "program_arguments",
    "run_bf16_sdpa_kv_cache_verification",
]


class DrawCounts(NamedTuple):
    """The counts of one draw (ADR-0165 decision 8).

    ``failed`` and ``non_finite`` are the
    :class:`hilclaw.harness.verification_arrays.Counts` of ``out``;
    ``cache_differences`` is the number of elements of the ``cache_k`` and the
    ``cache_v`` allocation together whose patterns differ from the expected
    ones. No index, element or region is returned.
    """

    failed: int
    non_finite: int
    cache_differences: int


def program_arguments(dims, *, draws, seed):
    """Return the arguments of the bf16 SDPA-with-KV-cache verification program as a tuple of ``str``.

    ``dims`` is exactly a ``tuple`` of five ``int``, ``(m, l, h, h_kv, d)``,
    each at least 1, with l >= m and ``h`` a multiple of ``h_kv``. ``draws``
    is an ``int`` with 1 <= ``draws`` < 2**64 and ``seed`` an ``int`` with
    0 <= ``seed`` < 2**64; a ``bool`` is not an ``int`` here. The result is
    ``m``, ``l``, ``h``, ``h_kv``, ``d``, ``draws`` and ``seed``, spelled as in
    the module docstring. Raises
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


def judge_report(report, dims, *, draws, seed, rtol, atol):
    """Judge one report of a bf16 SDPA-with-KV-cache verification process and return a :class:`Judgement`.

    ``report`` is what the process wrote on its report channel, as exactly
    ``bytes`` in the form of the module docstring; ``dims``, ``draws`` and
    ``seed`` are the parameters that process was started with, as in
    :func:`program_arguments`, and ``rtol`` and ``atol`` the tolerance of
    :func:`hilclaw.harness.bf16_sdpa_kv_cache_arrays.count_failures`, which
    applies to ``out`` only. Every parameter after ``dims`` is keyword-only
    and none has a default.

    In this order: the length of a complete report for ``dims`` and ``draws``
    is compared with the length of ``report`` and the end mark is looked for,
    and a report that fails either is ``Broken.REPORT_FORM``; then for each
    draw in order the inputs and the two allocations before the call are
    regenerated from ``seed``, the reported check value is compared with
    theirs, ``out`` is counted against the float64 reference under the
    tolerance and each reported allocation is compared with the expected one.
    The first check value that disagrees is ``Broken.CHECK_VALUE``. Otherwise
    the verdict is a pass when no draw has a failed element of ``out`` or a
    differing cache element and a fail when one has, with one
    :class:`DrawCounts` per draw. ``Broken.TIMEOUT`` and
    ``Broken.EXIT_STATUS`` are never returned.

    Raised before any byte of ``report`` is looked at and before anything is
    regenerated, in this order:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError` as
    in :func:`program_arguments` and for a tolerance that
    :func:`hilclaw.harness.verification_arrays.check_tolerance` refuses, and
    :class:`TypeError` for a ``report`` that is not exactly ``bytes``.
    """
    program_arguments(dims, draws=draws, seed=seed)
    verification_arrays.check_tolerance(rtol, atol)
    if type(report) is not bytes:
        raise TypeError(f"report: must be bytes, got {type(report).__name__}")
    return _judgement(report, dims, draws, seed, rtol, atol)


def run_bf16_sdpa_kv_cache_verification(
    executable,
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
    """Run one bf16 SDPA-with-KV-cache verification executable once and return a :class:`VerificationResult`.

    One process ``<executable> <arguments>`` is started with
    :func:`hilclaw.local_run.run` and no standard input, where the arguments
    are those of :func:`program_arguments`; ``timeout_s``, ``cwd`` and ``env``
    are handed over unchanged. ``executable`` is a ``str`` or
    :class:`os.PathLike`, or a non-empty sequence that is used as the start of
    the command, and must have been built for ``sdpa_kv_cache``. ``rtol`` and
    ``atol`` stay on this side.

    The run is completed only if it did not time out, its exit status is 0,
    its standard output has the form of a complete report and the check value
    of every draw agrees with the regenerated one; every other run is broken.
    The last two conditions, the verdict and the counts are those of
    :func:`judge_report`; a run that timed out or failed is broken whatever it
    wrote. The ``run`` member is the runner's result with ``stdout`` replaced
    by ``b""``.

    Raised before anything is started, in this order: what
    :func:`judge_report` raises for its arguments other than ``report``,
    :class:`TypeError` for an ``executable`` that is neither a path nor
    iterable and :class:`ValueError` for an empty ``executable`` sequence;
    then what :func:`hilclaw.local_run.run` raises for the command, the time
    limit, ``env`` and ``cwd``. Its other errors are passed on as well.
    """
    arguments = program_arguments(dims, draws=draws, seed=seed)
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
    judgement = _judgement(report, dims, draws, seed, rtol, atol)
    return VerificationResult(*judgement, run)


def _judgement(report, dims, draws, seed, rtol, atol):
    m, l, h, h_kv, d = dims
    block = 4 + 2 * m * h * d + 4 * (l + 2 * m) * h_kv * d
    if len(report) != draws * block + len(END_MARK) or not report.endswith(END_MARK):
        return Judgement(Broken.REPORT_FORM, None, None)
    counts = []
    for draw in range(draws):
        taken = _counts(report, draw * block, dims, seed, draw, rtol, atol)
        if taken is None:
            return Judgement(Broken.CHECK_VALUE, None, None)
        counts.append(taken)
    failed = any(count.failed or count.cache_differences for count in counts)
    return Judgement(None, Verdict.FAIL if failed else Verdict.PASS, tuple(counts))


def _counts(report, offset, dims, seed, draw, rtol, atol):
    arrays = bf16_sdpa_kv_cache_arrays
    m, l, h, h_kv, d = dims
    inputs = arrays.draw_inputs(dims, seed=seed, draw=draw)
    before_k = arrays.allocation_before(dims, inputs.cached_k)
    before_v = arrays.allocation_before(dims, inputs.cached_v)
    (reported,) = struct.unpack_from("=I", report, offset)
    check = arrays.check_value(
        dims, inputs.q, inputs.k_new, inputs.v_new, before_k, before_v
    )
    if reported != check:
        return None
    offset += 4
    output = np.frombuffer(report, dtype=np.uint16, count=m * h * d, offset=offset)
    expected = arrays.reference(dims, *inputs)
    counts = arrays.count_failures(
        output.reshape(m, h, d), expected, rtol=rtol, atol=atol
    )
    offset += 2 * m * h * d
    shape = (l + 2 * m, h_kv, d)
    differences = 0
    for cached, new in (
        (inputs.cached_k, inputs.k_new),
        (inputs.cached_v, inputs.v_new),
    ):
        size = math.prod(shape)
        reported_cache = np.frombuffer(
            report, dtype=np.uint16, count=size, offset=offset
        ).reshape(shape)
        expected_cache = arrays.allocation_after(dims, cached, new)
        differences += arrays.count_cache_differences(
            dims, reported_cache, expected_cache
        )
        offset += 2 * size
    return DrawCounts(counts.failed, counts.non_finite, differences)
