"""Array side of the bf16 SDPA-with-KV-cache verification run of ADR-0165: inputs, caches, reference, counts.

``ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md``
is the rule, for kind ``sdpa_kv_cache`` at ``cpu_standin``. This module holds
the NumPy computations of such a run and nothing else, as
:mod:`hilclaw.harness.bf16_verification_arrays` does for the kinds of
ADR-0163, whose generator, widening and counts it reuses.

``dims`` is ``(m, l, h, h_kv, d)``, the dimensions in the prototype's order,
with l ≥ m and h a multiple of h_kv (decision 3); P = l − m is derived and is
never an argument (decision 1). ``q`` and ``out`` are (m, h, d), element
(i, j, e) at ``q[(i*h + j)*d + e]``; ``k_new`` and ``v_new`` are (m, h_kv, d);
cache element (t, g, e) is at ``(t*h_kv + g)*d + e`` (ADR-0162 decisions 4
and 5).

Inputs (decision 4). The elements of draw ``draw`` form one sequence of
m·(h + 2·h_kv)·d + 2·P·h_kv·d indices: ``q``, ``k_new``, ``v_new``, then
rows 0 … P − 1 of ``cache_k`` (``cached_k``) and of ``cache_v``
(``cached_v``), each in memory order. The pattern of index ``e`` is that of
``word(draw, e)`` with bits = 8 in the generator of
:mod:`hilclaw.harness.bf16_verification_arrays` (its ``base(d)`` and
``word(d, e)``), so it lies in the value set of ADR-0162 decision 13.

Allocations (decision 5). Each cache is an allocation of l + 2m rows of
h_kv·d elements: m leading guard rows, the l rows of the operand, m trailing
guard rows; operand row t is allocation row m + t. Before the call, operand
rows 0 … P − 1 hold the drawn rows and every other row holds :data:`FILL`,
``0x7FC0``. After the call a conforming kernel leaves the same allocation
with operand row P + i equal to row i of ``k_new`` (``v_new`` for
``cache_v``), i = 0 … m − 1 (decision 8).

Check value (decision 7). ``zlib.crc32`` of ``q``, ``k_new``, ``v_new``, the
whole ``cache_k`` allocation and the whole ``cache_v`` allocation before the
call, in that order, 2 bytes per element in memory order and host byte order.

Reference (decision 6). Every operand is widened as in ADR-0163 (pattern
``p`` becomes the binary32 ``p << 16``, then float64). K is ``cached_k``
followed by ``k_new`` and V is ``cached_v`` followed by ``v_new``, l rows each;
no reported data enters. For each query head j, with g = j // (h // h_kv)
and c = 1 / sqrt(d) as a float64 multiplier::

    s = (Q_j @ K_g.T) * c,  s[i, t] = -inf for t > P + i
    y[:, j, :] = softmax(s) @ V_g    (row maximum subtracted, numpy.exp)

in NumPy float64 with no bf16 emulation, one query head at a time, so one
m × l score array is held at once.

Conventions of this module (not rules of the record): those of
:mod:`hilclaw.harness.bf16_verification_arrays`, with ``dims`` exactly a
``tuple`` of five ``int`` (``bool`` refused), each at least 1, checked before
l ≥ m and before the multiple. Every array argument is a ``uint16`` array of
the exact shape the function names for ``dims``, only ``cached_k`` and
``cached_v`` holding a 0 dimension (at P = 0); ``count_failures`` takes a
``float64`` ``expected``. :func:`draw_inputs` works on the whole sequence
without chunks, with a peak under 48 bytes per drawn element, of which 2 are
returned.

What this module does not do: it starts no process, builds nothing, reads or
splits no report and gives no verdict; it holds no tolerance, seed, number of
draws or dimension and gives no argument a default; and it returns no index,
region or element beyond the counts (decision 8).
"""

import math
import zlib
from typing import NamedTuple

import numpy as np

from hilclaw.harness.bf16_verification_arrays import _patterns, _widened
from hilclaw.harness.bf16_verification_arrays import (
    count_failures as _count_failures,
)
from hilclaw.harness.verification_arrays import (
    GOLDEN,
    SEED_LIMIT,
    Counts,
    VerificationArgumentError,
    _fail,
    _integer,
    _mix,
    _shown,
    check_tolerance,
)

__all__ = [
    "FILL",
    "Counts",
    "Inputs",
    "VerificationArgumentError",
    "allocation_after",
    "allocation_before",
    "check_value",
    "count_cache_differences",
    "count_failures",
    "draw_inputs",
    "reference",
]

FILL = 0x7FC0


class Inputs(NamedTuple):
    """The five drawn arrays of one draw, in the order of the sequence."""

    q: np.ndarray
    k_new: np.ndarray
    v_new: np.ndarray
    cached_k: np.ndarray
    cached_v: np.ndarray


def draw_inputs(dims, *, seed, draw):
    """Return the :class:`Inputs` of draw ``draw`` (counted from 0) for ``seed``.

    The five arrays are C-contiguous ``uint16`` views of one buffer that do
    not overlap, holding bit for bit what the verification program draws:
    ``q`` (m, h, d), ``k_new`` and ``v_new`` (m, h_kv, d), ``cached_k`` and
    ``cached_v`` (P, h_kv, d). ``seed`` is from 0 to 2**64 - 1 and ``draw``
    from 0 to 2**64 - 2.
    """
    m, l, h, h_kv, d = _dims(dims)
    _integer("seed", seed, 0, SEED_LIMIT - 1, "an int with 0 <= seed < 2**64")
    _integer("draw", draw, 0, SEED_LIMIT - 2, "an int with 0 <= draw < 2**64 - 1")
    shapes = [(m, h, d), (m, h_kv, d), (m, h_kv, d)] + [(l - m, h_kv, d)] * 2
    sizes = [math.prod(shape) for shape in shapes]
    start = np.array([(seed + (draw + 1) * GOLDEN) % SEED_LIMIT], dtype=np.uint64)
    words = np.arange(1, sum(sizes) + 1, dtype=np.uint64)
    words *= GOLDEN
    words += _mix(start)
    _mix(words)
    patterns = np.empty(sum(sizes), dtype=np.uint16)
    patterns[...] = _patterns(words, 8)
    parts = np.split(patterns, np.cumsum(sizes)[:-1])
    return Inputs(*(part.reshape(shape) for part, shape in zip(parts, shapes)))


def allocation_before(dims, cached):
    """Return a cache allocation before the call: ``cached`` in operand rows 0 … P − 1.

    ``cached`` is the (P, h_kv, d) array of drawn rows. The result is a new
    C-contiguous ``uint16`` array of shape (l + 2m, h_kv, d) whose other rows
    hold :data:`FILL`.
    """
    m, l, _, h_kv, d = _dims(dims)
    _array("cached", cached, (l - m, h_kv, d))
    return _allocation(dims, cached)


def allocation_after(dims, cached, new):
    """Return the allocation a conforming kernel leaves: as before, with ``new`` in rows P … l − 1.

    ``cached`` is (P, h_kv, d) and ``new`` (``k_new`` or ``v_new``)
    (m, h_kv, d); operand row P + i is row i of ``new``. The guard rows hold
    :data:`FILL`.
    """
    m, l, _, h_kv, d = _dims(dims)
    _array("cached", cached, (l - m, h_kv, d))
    _array("new", new, (m, h_kv, d))
    result = _allocation(dims, cached)
    result[l : l + m] = new
    return result


def check_value(dims, q, k_new, v_new, cache_k, cache_v):
    """Return the check value of a draw as an ``int``: ``zlib.crc32`` of the five arrays.

    ``cache_k`` and ``cache_v`` are whole (l + 2m, h_kv, d) allocations. The
    bytes are those of the memory order; a C-contiguous array is not copied.
    The result is what the verification program reports as a ``uint32_t``.
    """
    m, l, h, h_kv, d = _dims(dims)
    _array("q", q, (m, h, d))
    _array("k_new", k_new, (m, h_kv, d))
    _array("v_new", v_new, (m, h_kv, d))
    _array("cache_k", cache_k, (l + 2 * m, h_kv, d))
    _array("cache_v", cache_v, (l + 2 * m, h_kv, d))
    crc = 0
    for array in (q, k_new, v_new, cache_k, cache_v):
        crc = zlib.crc32(np.ascontiguousarray(array), crc)
    return crc


def reference(dims, q, k_new, v_new, cached_k, cached_v):
    """Return the ``float64`` (m, h, d) reference of ADR-0165 decision 6.

    The arguments are the drawn arrays of the shapes :func:`draw_inputs`
    returns for ``dims``; the formula is the one of the module docstring. A
    NaN or infinity in an input propagates. The reference's own rounding is
    not accounted for.
    """
    m, l, h, h_kv, d = _dims(dims)
    _array("q", q, (m, h, d))
    _array("k_new", k_new, (m, h_kv, d))
    _array("v_new", v_new, (m, h_kv, d))
    _array("cached_k", cached_k, (l - m, h_kv, d))
    _array("cached_v", cached_v, (l - m, h_kv, d))
    query = _widened(q).astype(np.float64)
    k_rows = _widened(np.concatenate([cached_k, k_new])).astype(np.float64)
    v_rows = _widened(np.concatenate([cached_v, v_new])).astype(np.float64)
    masked = np.arange(l)[np.newaxis, :] > (l - m + np.arange(m))[:, np.newaxis]
    scale = 1 / math.sqrt(d)
    result = np.empty((m, h, d), dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        for j in range(h):
            g = j // (h // h_kv)
            scores = (query[:, j, :] @ k_rows[:, g, :].T) * scale
            scores[masked] = -np.inf
            scores -= scores.max(axis=1, keepdims=True)
            np.exp(scores, out=scores)
            scores /= scores.sum(axis=1, keepdims=True)
            result[:, j, :] = scores @ v_rows[:, g, :]
    return result


def count_failures(output, expected, *, rtol, atol):
    """Return the :class:`Counts` of one draw's ``out`` against its reference.

    ``output`` is the kernel's ``out`` as a ``uint16`` pattern array of three
    dimensions and ``expected`` the ``float64`` reference of the same shape,
    none of their dimensions 0. The tolerance is checked by
    :func:`check_tolerance` first; the predicate and counts are those of
    :func:`hilclaw.harness.bf16_verification_arrays.count_failures`.
    """
    check_tolerance(rtol, atol)
    _array("output", output, None)
    _array("expected", expected, None, np.float64)
    if output.shape != expected.shape:
        rule = f"of the shape of expected, {expected.shape}"
        _fail("output", rule, f"shape {output.shape}")
    m, h, d = output.shape
    return _count_failures(
        output.reshape(m * h, d), expected.reshape(m * h, d), rtol=rtol, atol=atol
    )


def count_cache_differences(dims, reported, expected):
    """Return the number of elements whose patterns differ between two allocations.

    Both are ``uint16`` (l + 2m, h_kv, d) allocations, compared bit for bit
    as integers with no tolerance, so ``0x7FC0`` equals ``0x7FC0``.
    """
    m, l, _, h_kv, d = _dims(dims)
    _array("reported", reported, (l + 2 * m, h_kv, d))
    _array("expected", expected, (l + 2 * m, h_kv, d))
    return int(np.count_nonzero(reported != expected))


def _dims(dims):
    if type(dims) is not tuple or len(dims) != 5:
        _fail("dims", "a tuple of five ints (m, l, h, h_kv, d)", _shown(dims))
    for index, value in enumerate(dims):
        _integer(f"dims[{index}]", value, 1, math.inf, "an int of at least 1")
    m, l, h, h_kv, _ = dims
    if l < m:
        _fail("dims[1]", f"at least dims[0] ({m})", _shown(l))
    if h % h_kv:
        _fail("dims[2]", f"a multiple of dims[3] ({h_kv})", _shown(h))
    return dims


def _allocation(dims, cached):
    m, l, _, h_kv, d = dims
    result = np.full((l + 2 * m, h_kv, d), FILL, dtype=np.uint16)
    result[m:l] = cached
    return result


def _array(name, value, shape, dtype=np.uint16):
    if type(value) is not np.ndarray or value.dtype != dtype:
        valid = False
    elif shape is None:
        valid = value.ndim == 3 and 0 not in value.shape
    else:
        valid = value.shape == shape
    if not valid:
        if shape is None:
            rule = f"a {dtype.__name__} array of three dimensions, none of them 0"
        else:
            rule = f"a {dtype.__name__} array of shape {shape}"
        _fail(name, rule, _shown(value))
