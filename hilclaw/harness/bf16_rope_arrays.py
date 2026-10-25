"""Array side of the bf16 RoPE verification run of ADR-0164: ``x``, table rows, check value, reference, counts.

``ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`` is the
rule, for kind ``rope`` at ``cpu_standin``. The Python side of such a run
regenerates ``x`` of each draw from the seed (decision 6), builds the
``freqs_cis`` rows it sends on standard input and keeps (decisions 3 to 5),
compares the check value of ``x`` and the rows with the one the verification
program reported (decision 9), computes the float64 reference (decision 9) and
counts the elements of the kernel's output that fail the tolerance
(decision 10). This module holds those computations on NumPy arrays and
nothing else, as :mod:`hilclaw.harness.bf16_verification_arrays` does for the
kinds of ADR-0163, whose generator, widening and counts it reuses.

``dims`` is ``(m, h, d)``: ``m`` tokens, ``h`` heads and the head dimension
``d``, which is even (ADR-0161 decision 11).

``x``. The m·h·d elements of draw ``draw`` take sequence indices
0 … m·h·d − 1 in memory order, element (i, j, k) at index ``x[(i*h + j)*d + k]``
(ADR-0161 decision 6), each with bits = 8: the pattern of index ``e`` is that
of ``word(draw, e)`` with bits = 8 in the generator of
:mod:`hilclaw.harness.bf16_verification_arrays` (its ``base(d)`` and
``word(d, e)``), so ``x`` is bit for bit the first operand that module draws
for ``elementwise_add`` at dims ``(m*h, d)``. There is no second drawn operand.

Rows. Row ``i`` of the ``float32`` (m, d) rows, entry ``rows[i*d + c]`` in
memory order, is row ``start + i`` of :func:`hilclaw.rope_table.build` with
``head_dim`` = d, ``positions`` = start + m and the constants of
:data:`TABLE_CONSTANTS`: θ = 500000, s = 8, a = 1, b = 4, L = 8192
(ADR-0161 decision 13, ADR-0164 decision 4), for every even ``d``.

Check value. ``zlib.crc32`` of the 2·m·h·d bytes of ``x`` followed by the
4·m·d bytes of the rows, both in memory order and the byte order of the host
(decision 9).

Reference. ``x`` is widened as in ADR-0163 (pattern ``p`` becomes the binary32
``p << 16``, then float64) and the rows to float64, both exactly. With
x₀ = x[i, j, 2p], x₁ = x[i, j, 2p + 1], c = rows[i, 2p] and
s = rows[i, 2p + 1], the row of token i serving every head j::

    y[i, j, 2p]     = x₀·c − x₁·s
    y[i, j, 2p + 1] = x₀·s + x₁·c

in NumPy float64; a NaN or infinity in the rows propagates.

Conventions of this module (not rules of the record): those of
:mod:`hilclaw.harness.bf16_verification_arrays`, with ``dims`` exactly a
``tuple`` of three ``int`` (``bool`` refused), each at least 1, ``d`` even,
checked in that order. ``x`` and ``output`` are ``uint16`` arrays of three
dimensions, ``rows`` a ``float32`` array of two and ``expected`` a ``float64``
array of three, none of their dimensions 0. :func:`draw_x` works on the whole
array without chunks, with a peak under 48 bytes per element, of which 2 are
returned.

What this module does not do: it starts no process, builds nothing, reads no
report and gives no verdict; it holds no tolerance, seed, number of draws,
dimension or start position and gives no argument a default; and it caches no
table between calls.
"""

import math
import types
import zlib

import numpy as np

from hilclaw import keys, rope_table
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
    "TABLE_CONSTANTS",
    "Counts",
    "VerificationArgumentError",
    "check_value",
    "count_failures",
    "draw_x",
    "reference",
    "table_rows",
]

TABLE_CONSTANTS = types.MappingProxyType(
    {
        "theta": 500000.0,
        "scale_factor": 8.0,
        "low_freq_factor": 1.0,
        "high_freq_factor": 4.0,
        "old_context_len": 8192,
    }
)


def table_rows(dims, *, start):
    """Return the ``freqs_cis`` rows of a run: rows ``start`` … ``start + m - 1`` of the table.

    The result is a new C-contiguous ``float32`` array of shape (m, d), sliced
    from one call of :func:`hilclaw.rope_table.build` with ``head_dim`` = d,
    ``positions`` = start + m and :data:`TABLE_CONSTANTS`. ``start`` is an
    ``int`` of at least 0; when (start + m)·d exceeds 2**53 - 1 it is refused
    before the table is built.
    """
    m, _, d = _dims(dims)
    _integer("start", start, 0, math.inf, "an int of at least 0")
    if (start + m) * d > keys.MAX_INTEGER:
        rule = f"such that (start + m) * d <= 2**53 - 1 for dims {dims}"
        _fail("start", rule, _shown(start))
    table = rope_table.build(head_dim=d, positions=start + m, **TABLE_CONSTANTS)
    return table[start:].copy()


def draw_x(dims, *, seed, draw):
    """Return ``x`` of draw ``draw`` (counted from 0): a C-contiguous ``uint16`` (m, h, d) array.

    It holds, bit for bit, what the verification program draws. ``seed`` is
    from 0 to 2**64 - 1 and ``draw`` from 0 to 2**64 - 2.
    """
    m, h, d = _dims(dims)
    _integer("seed", seed, 0, SEED_LIMIT - 1, "an int with 0 <= seed < 2**64")
    _integer("draw", draw, 0, SEED_LIMIT - 2, "an int with 0 <= draw < 2**64 - 1")
    start = np.array([(seed + (draw + 1) * GOLDEN) % SEED_LIMIT], dtype=np.uint64)
    words = np.arange(1, m * h * d + 1, dtype=np.uint64)
    words *= GOLDEN
    words += _mix(start)
    _mix(words)
    x = np.empty(m * h * d, dtype=np.uint16)
    x[...] = _patterns(words, 8)
    return x.reshape(m, h, d)


def check_value(x, rows):
    """Return the check value of a draw as an ``int``: ``zlib.crc32`` of ``x`` then ``rows``.

    ``x`` is a ``uint16`` (m, h, d) array and ``rows`` a ``float32`` (m, d)
    array. The bytes are those of the memory order; a C-contiguous array is
    not copied. The result is what the verification program reports as a
    ``uint32_t``.
    """
    _operands(x, rows)
    crc = zlib.crc32(np.ascontiguousarray(x))
    return zlib.crc32(np.ascontiguousarray(rows), crc)


def reference(x, rows):
    """Return the ``float64`` (m, h, d) reference of ADR-0164 decision 9 for ``x`` and ``rows``.

    The arguments are checked as by :func:`check_value`. The formula is the
    one of the module docstring; the reference's own rounding is not
    accounted for.
    """
    _operands(x, rows)
    wide = _widened(x).astype(np.float64)
    table = rows.astype(np.float64)[:, np.newaxis, :]
    first, second = wide[..., 0::2], wide[..., 1::2]
    cos, sin = table[..., 0::2], table[..., 1::2]
    result = np.empty(x.shape, dtype=np.float64)
    with np.errstate(over="ignore", invalid="ignore"):
        result[..., 0::2] = first * cos - second * sin
        result[..., 1::2] = first * sin + second * cos
    return result


def count_failures(output, expected, *, rtol, atol):
    """Return the :class:`Counts` of one draw's output against its reference.

    ``output`` is the kernel's output as a ``uint16`` (m, h, d) pattern array
    and ``expected`` the ``float64`` reference of the same shape. The
    tolerance is checked by :func:`check_tolerance` first; the predicate and
    counts are those of
    :func:`hilclaw.harness.bf16_verification_arrays.count_failures`.
    """
    check_tolerance(rtol, atol)
    _array("output", output, np.uint16, 3)
    _array("expected", expected, np.float64, 3)
    if output.shape != expected.shape:
        rule = f"of the shape of expected, {expected.shape}"
        _fail("output", rule, f"shape {output.shape}")
    m, h, d = output.shape
    return _count_failures(
        output.reshape(m * h, d), expected.reshape(m * h, d), rtol=rtol, atol=atol
    )


def _dims(dims):
    if type(dims) is not tuple or len(dims) != 3:
        _fail("dims", "a tuple of three ints (m, h, d)", _shown(dims))
    for index, value in enumerate(dims):
        _integer(f"dims[{index}]", value, 1, math.inf, "an int of at least 1")
    if dims[2] % 2:
        _fail("dims[2]", "even", _shown(dims[2]))
    return dims


def _operands(x, rows):
    _array("x", x, np.uint16, 3)
    _array("rows", rows, np.float32, 2)
    wanted = (x.shape[0], x.shape[2])
    if rows.shape != wanted:
        _fail("rows", f"of shape (m, d) of x, {wanted}", f"shape {rows.shape}")


def _array(name, value, dtype, ndim):
    if type(value) is np.ndarray and value.dtype == dtype and value.ndim == ndim:
        valid = 0 not in value.shape
    else:
        valid = False
    if not valid:
        noun = ("two", "three")[ndim - 2]
        rule = f"a {dtype.__name__} array of {noun} dimensions, none of them 0"
        _fail(name, rule, _shown(value))
