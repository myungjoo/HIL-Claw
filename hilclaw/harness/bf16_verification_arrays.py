"""Array side of a bf16 verification run of ADR-0163: inputs, check value, reference, counts.

``ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`` is the rule,
for the kinds of :data:`KINDS` at ``cpu_standin``. The Python side of such a
run regenerates the inputs of each draw from the seed (decisions 4 and 6),
compares the check value of its arrays with the one the verification program
reported (decision 6), widens the bf16 patterns and computes the float64
reference of the kind (decision 6), and counts the elements of the kernel's
output that fail the tolerance (decision 7). This module holds those
computations on NumPy arrays and nothing else, as
:mod:`hilclaw.harness.verification_arrays` does for the first case.

Generator. With all arithmetic on unsigned 64-bit integers modulo 2**64, and
``G``, ``mix`` and ``base`` those of the first case (the header comment of
``verification_program.c``), as ADR-0163 decision 4 permits::

    G          = 0x9E3779B97F4A7C15
    mix(x)     : x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9
                 x = (x ^ (x >> 27)) * 0x94D049BB133111EB
                 the result is x ^ (x >> 31)
    base(d)    = mix(seed + (d + 1) * G)
    word(d, e) = mix(base(d) + (e + 1) * G)    element e = 0 .. F + S - 1
    r(d, e)    = word(d, e) >> (64 - bits)
    bits = 8:  pattern = 0x3F00 | (r & 0x7F) | ((r >> 7) << 15)
    bits = 10: pattern = (0x3F00 + (r & 0x1FF)) | ((r >> 9) << 15)

The elements of draw ``d`` form one sequence: the F elements of the first
operand in row-major order, then the S elements of the second (``gemm``:
``a`` (m, k) then ``b`` (k, n); ``rmsnorm``: ``x`` (m, n) then ``w`` (n);
``elementwise_add``: ``a`` then ``b``, both (m, n); ``swiglu``: ``gate`` then
``up``, both (m, n)). ``bits`` is 10 for ``gate`` and 8 for every other
operand, and ``pattern`` is the ``uint16_t`` bf16 bit pattern of the
element in the byte order of the host; the pattern of index ``r`` is element ``r`` of the
contract module's tuple. Changing anything in this paragraph or the one above
changes the contract of the verification programs, which must reproduce it
bit for bit. The check value of a draw is ``zlib.crc32`` of the bytes of the
first operand followed by the bytes of the second, 2 bytes per element.

Conventions of this module (not rules of the record): those of
:mod:`hilclaw.harness.verification_arrays`, whose argument checks, error
class and :func:`~hilclaw.harness.verification_arrays.check_tolerance` this
module reuses, with these differences:

- ``dims`` is exactly a ``tuple`` of ``int``: ``(m, k, n)`` for ``gemm`` and
  ``(m, n)`` for the other kinds, each at least 1; ``kind`` is a ``str`` of
  :data:`KINDS`.
- An array argument is a ``uint16`` pattern array, except ``expected``, which
  is ``float64``; it has the number of dimensions the function names (``w``
  of ``rmsnorm`` has one), none of them 0, in the byte order of the host.
- :func:`draw_inputs` works on whole arrays without chunks: its peak is under
  48 bytes for each element of the two operands, of which 2 are returned.
  The two operands are views of one buffer and do not overlap.

What this module does not do: it starts no process and builds nothing; it does
not split or read a report, decide completed or broken, or give a verdict over
draws (decision 8); it holds no tolerance value, seed, number of draws or
dimension and gives no argument a default; and it returns no index, deviation
or element beyond the two counts (decision 8).
"""

import math
import zlib

import numpy as np

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
from hilclaw.harness.verification_arrays import count_failures as _count_failures

__all__ = [
    "EPS_BITS",
    "KINDS",
    "Counts",
    "VerificationArgumentError",
    "check_value",
    "count_failures",
    "draw_inputs",
    "reference",
    "widen",
]

KINDS = ("gemm", "rmsnorm", "elementwise_add", "swiglu")
EPS_BITS = 0x3727C5AC

_EPS = float(np.array([EPS_BITS], dtype=np.uint32).view(np.float32)[0])


def draw_inputs(kind, dims, *, seed, draw):
    """Return ``(first, second)``, the operands of draw ``draw`` (counted from 0) of ``kind``.

    ``dims`` is ``(m, k, n)`` for ``gemm`` and ``(m, n)`` otherwise. The
    operands are C-contiguous ``uint16`` arrays holding, bit for bit, what the
    verification program draws: ``a`` (m, k) and ``b`` (k, n) for ``gemm``,
    ``x`` (m, n) and ``w`` (n,) for ``rmsnorm``, and two (m, n) arrays for
    ``elementwise_add`` and ``swiglu``. ``seed`` is from 0 to 2**64 - 1 and
    ``draw`` from 0 to 2**64 - 2.
    """
    shapes = _shapes(kind, dims)
    _integer("seed", seed, 0, SEED_LIMIT - 1, "an int with 0 <= seed < 2**64")
    _integer("draw", draw, 0, SEED_LIMIT - 2, "an int with 0 <= draw < 2**64 - 1")
    sizes = [math.prod(shape) for shape in shapes]
    start = np.array([(seed + (draw + 1) * GOLDEN) % SEED_LIMIT], dtype=np.uint64)
    words = np.arange(1, sum(sizes) + 1, dtype=np.uint64)
    words *= GOLDEN
    words += _mix(start)
    _mix(words)
    patterns = np.empty(sum(sizes), dtype=np.uint16)
    first, second = patterns[: sizes[0]], patterns[sizes[0] :]
    first[...] = _patterns(words[: sizes[0]], 10 if kind == "swiglu" else 8)
    second[...] = _patterns(words[sizes[0] :], 8)
    return first.reshape(shapes[0]), second.reshape(shapes[1])


def check_value(first, second):
    """Return the check value of a draw as an ``int``: ``zlib.crc32`` of ``first`` then ``second``.

    Each is a ``uint16`` array of one or two dimensions. The bytes are those of
    the row-major layout; a C-contiguous array is not copied. The result is
    what the verification program reports as a ``uint32_t``.
    """
    _array("first", first, np.uint16, (1, 2))
    _array("second", second, np.uint16, (1, 2))
    crc = zlib.crc32(np.ascontiguousarray(first))
    return zlib.crc32(np.ascontiguousarray(second), crc)


def widen(patterns):
    """Return ``patterns``, a ``uint16`` array of one or two dimensions, as ``float64``.

    Pattern ``p`` becomes the binary32 pattern ``p << 16``, which is widened to
    ``float64``. Both steps are exact; ``0x7FC0`` becomes a NaN.
    """
    _array("patterns", patterns, np.uint16, (1, 2))
    return _widened(patterns).astype(np.float64)


def reference(kind, first, second):
    """Return the ``float64`` (m, n) reference of ``kind`` on the widened operands.

    The operands are ``uint16`` arrays of the shapes :func:`draw_inputs`
    returns for some ``dims``. The formulas are those of ADR-0163 decision 6:
    ``gemm`` ``a @ b``; ``rmsnorm`` ``x * w / sqrt(mean(x**2) + eps)`` per
    row, with ``eps`` the binary32 value of :data:`EPS_BITS`;
    ``elementwise_add`` ``a + b``; ``swiglu`` ``g / (1 + exp(-g)) * u`` with
    ``numpy.exp``. The reference's own rounding is not accounted for.
    """
    _kind(kind)
    _array("first", first, np.uint16, (2,))
    _array("second", second, np.uint16, (1,) if kind == "rmsnorm" else (2,))
    if kind == "gemm":
        wanted = (first.shape[1], second.shape[1])
    elif kind == "rmsnorm":
        wanted = (first.shape[1],)
    else:
        wanted = first.shape
    if second.shape != wanted:
        _fail("second", f"of shape {wanted} for {kind}", f"shape {second.shape}")
    left, right = widen(first), widen(second)
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        if kind == "gemm":
            return np.matmul(left, right)
        if kind == "rmsnorm":
            scale = np.sqrt(np.mean(left * left, axis=1, keepdims=True) + _EPS)
            return left * right / scale
        if kind == "elementwise_add":
            return left + right
        return left / (1 + np.exp(-left)) * right


def count_failures(output, expected, *, rtol, atol):
    """Return the :class:`Counts` of one draw's output against its reference.

    ``output`` is the kernel's output as a ``uint16`` pattern array of two
    dimensions and ``expected`` the ``float64`` reference of the same shape.
    ``output`` is widened and the predicate and counts are those of
    :func:`hilclaw.harness.verification_arrays.count_failures`. The tolerance
    is checked by :func:`check_tolerance` first.
    """
    check_tolerance(rtol, atol)
    _array("output", output, np.uint16, (2,))
    _array("expected", expected, np.float64, (2,))
    if output.shape != expected.shape:
        rule = f"of the shape of expected, {expected.shape}"
        _fail("output", rule, f"shape {output.shape}")
    return _count_failures(_widened(output), expected, rtol=rtol, atol=atol)


def _shapes(kind, dims):
    _kind(kind)
    length = 3 if kind == "gemm" else 2
    if type(dims) is not tuple or len(dims) != length:
        _fail("dims", f"a tuple of {length} ints for {kind}", _shown(dims))
    for index, value in enumerate(dims):
        _integer(f"dims[{index}]", value, 1, math.inf, "an int of at least 1")
    if kind == "gemm":
        m, k, n = dims
        return (m, k), (k, n)
    m, n = dims
    return (m, n), ((n,) if kind == "rmsnorm" else (m, n))


def _patterns(words, bits):
    index = words >> (64 - bits)
    if bits == 8:
        return 0x3F00 | (index & 0x7F) | ((index >> 7) << 15)
    return (0x3F00 + (index & 0x1FF)) | ((index >> 9) << 15)


def _widened(patterns):
    return (patterns.astype(np.uint32) << 16).view(np.float32)


def _kind(kind):
    if type(kind) is not str or kind not in KINDS:
        _fail("kind", f"one of {KINDS}", _shown(kind))


def _array(name, value, dtype, ndims):
    if type(value) is np.ndarray and value.dtype == dtype and value.ndim in ndims:
        valid = 0 not in value.shape
    else:
        valid = False
    if not valid:
        counts = " or ".join(("one", "two")[n - 1] for n in ndims)
        noun = "dimension" if ndims == (1,) else "dimensions"
        rule = f"a {dtype.__name__} array of {counts} {noun}, none of them 0"
        _fail(name, rule, _shown(value))
