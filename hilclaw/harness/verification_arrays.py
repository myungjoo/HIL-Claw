"""Array side of a verification run of ADR-0017: inputs, check value, reference, counts.

``ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`` is the
rule. The Python side of a verification run regenerates the inputs of each draw
from the seed (decisions 3 and 4), compares the check value of its arrays with
the one the verification program reported (decision 4), computes the float64
reference (decision 4) and counts the elements of the kernel's output that fail
the tolerance (decisions 5 and 7). This module holds those four computations on
NumPy arrays and nothing else: it starts no process, builds nothing and reads
no report bytes.

Generator and check value. They are the second implementation of what the
header comment of ``verification_program.c`` defines, and both implementations
must give the same bit patterns. With all arithmetic on unsigned 64-bit
integers modulo 2**64::

    G          = 0x9E3779B97F4A7C15
    mix(x)     : x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9
                 x = (x ^ (x >> 27)) * 0x94D049BB133111EB
                 the result is x ^ (x >> 31)
    base(d)    = mix(seed + (d + 1) * G)
    word(d, e) = mix(base(d) + (e + 1) * G)    element e = 0 .. m*k + k*n - 1
    bits(d, e) = (word & 1) << 31 | 126 << 23 | word >> 41

Element ``e < m*k`` is ``a[e]`` and element ``e >= m*k`` is ``b[e - m*k]`` in
row-major order; ``bits`` is the binary32 bit pattern of the element in the
byte order of the host. The check value of a draw is ``zlib.crc32`` of the
bytes of ``a`` followed by the bytes of ``b``.

Conventions of this module (not rules of the record):

- One rule for every argument: a number is exactly a built-in ``int`` (or, for
  a tolerance, ``int`` or ``float``) and an array is exactly a
  ``numpy.ndarray``. A ``bool``, a NumPy scalar, a zero-dimensional array and
  an instance of a subclass are refused, and so is an ``int`` tolerance that
  a ``float`` cannot hold.
- An array argument has two dimensions, none of them 0, and the dtype named by
  the function in the byte order of the host.
- Everything else outside what a function states raises
  :class:`VerificationArgumentError`, whose message names the argument and
  shows the value only of an ``int``, ``float``, ``bool``, ``str`` or
  ``None``: of an array it shows the dtype and the shape, of anything else the
  type. What NumPy raises for arrays it cannot allocate (``MemoryError``, or
  a plain ``ValueError`` for a size it cannot hold) is passed on.
- :func:`draw_inputs` works on whole arrays without chunks: its peak is about
  16 bytes for each of the ``m*k + k*n`` elements, of which 4 are returned.
  ``a`` and ``b`` are views of one buffer and do not overlap.
- ``expected`` is not required to be finite; the reference of drawn inputs is.

What this module does not do: it starts no process and builds nothing; it does
not split or read a report, decide completed or broken, or give a verdict over
draws; it holds no tolerance value, seed, number of draws, dimension or time
limit and gives no argument a default (decision 6); and it returns no index,
deviation or element beyond the two counts (decision 7).
"""

import math
import reprlib
import zlib
from typing import NamedTuple

import numpy as np

GOLDEN = 0x9E3779B97F4A7C15
SEED_LIMIT = 2**64


class VerificationArgumentError(ValueError):
    """An argument is outside what this module states; nothing was computed."""


class Counts(NamedTuple):
    """Counts of one draw: elements failing the predicate, and non-finite elements."""

    failed: int
    non_finite: int


def draw_inputs(m, k, n, *, seed, draw):
    """Return ``(a, b)``, the inputs of draw ``draw`` (counted from 0) for ``seed``.

    ``a`` has shape ``(m, k)`` and ``b`` shape ``(k, n)``; both are C-contiguous
    ``float32`` arrays holding, bit for bit, what the verification program
    draws. ``m``, ``k`` and ``n`` are at least 1, ``seed`` is from 0 to
    2**64 - 1 and ``draw`` from 0 to 2**64 - 2.
    """
    for name, value in (("m", m), ("k", k), ("n", n)):
        _integer(name, value, 1, math.inf, "an int of at least 1")
    _integer("seed", seed, 0, SEED_LIMIT - 1, "an int with 0 <= seed < 2**64")
    _integer("draw", draw, 0, SEED_LIMIT - 2, "an int with 0 <= draw < 2**64 - 1")
    start = np.array([(seed + (draw + 1) * GOLDEN) % SEED_LIMIT], dtype=np.uint64)
    words = np.arange(1, m * k + k * n + 1, dtype=np.uint64)
    words *= GOLDEN
    words += _mix(start)
    _mix(words)
    sign = words & 1
    sign <<= 31
    words >>= 41
    words |= sign
    del sign
    words |= 126 << 23
    values = words.astype(np.uint32).view(np.float32)
    return values[: m * k].reshape(m, k), values[m * k :].reshape(k, n)


def check_value(a, b):
    """Return the check value of a draw as an ``int``: ``zlib.crc32`` of ``a`` then ``b``.

    ``a`` is a ``float32`` array of shape ``(m, k)`` and ``b`` one of shape
    ``(k, n)``. The bytes are those of the row-major layout; a C-contiguous
    array is not copied. The result is what the verification program reports
    as a ``uint32_t``.
    """
    _operands(a, b)
    return zlib.crc32(np.ascontiguousarray(b), zlib.crc32(np.ascontiguousarray(a)))


def reference(a, b):
    """Return the reference of a draw: the ``float64`` product of ``a`` and ``b``.

    ``a`` is a ``float32`` array of shape ``(m, k)`` and ``b`` one of shape
    ``(k, n)``; both are widened to ``float64`` (exactly) and multiplied there.
    The result has shape ``(m, n)``. Its own rounding error is not accounted
    for (decision 5).
    """
    _operands(a, b)
    return np.matmul(a.astype(np.float64), b.astype(np.float64))


def check_tolerance(rtol, atol):
    """Refuse a tolerance that is not valid (decision 5); return ``None`` otherwise.

    Each of ``rtol`` and ``atol`` must be an ``int`` or a ``float`` that is
    finite, not negative and, for an ``int``, within what a ``float`` holds.
    Raises :class:`VerificationArgumentError` naming the parameter.
    """
    for name, value in (("rtol", rtol), ("atol", atol)):
        try:
            valid = type(value) in (int, float) and 0 <= float(value) < math.inf
        except OverflowError:
            valid = False
        if not valid:
            _fail(name, "a finite int or float that is not negative", _shown(value))


def count_failures(output, expected, *, rtol, atol):
    """Return the :class:`Counts` of one draw's output against its reference.

    ``output`` is the kernel's output as a ``float32`` array and ``expected``
    the ``float64`` reference of the same shape. ``output`` is widened to
    ``float64`` and an element passes when it is finite and
    ``|output - expected| <= atol + rtol * |expected|`` holds in ``float64``.
    ``failed`` counts the elements that do not pass and ``non_finite`` the
    elements of ``output`` that are NaN or an infinity, each of which is also
    counted in ``failed``. The tolerance is checked by :func:`check_tolerance`
    first.
    """
    check_tolerance(rtol, atol)
    _matrix("output", output, np.float32)
    _matrix("expected", expected, np.float64)
    if output.shape != expected.shape:
        rule = f"of the shape of expected, {expected.shape}"
        _fail("output", rule, f"shape {output.shape}")
    finite = np.isfinite(output)
    with np.errstate(over="ignore", invalid="ignore"):
        deviation = np.abs(output.astype(np.float64) - expected)
        within = deviation <= float(atol) + float(rtol) * np.abs(expected)
    passed = int(np.count_nonzero(finite & within))
    return Counts(output.size - passed, output.size - int(np.count_nonzero(finite)))


def _mix(words):
    words ^= words >> 30
    words *= 0xBF58476D1CE4E5B9
    words ^= words >> 27
    words *= 0x94D049BB133111EB
    words ^= words >> 31
    return words


def _integer(name, value, minimum, maximum, rule):
    if type(value) is not int or not minimum <= value <= maximum:
        _fail(name, rule, _shown(value))


def _operands(a, b):
    _matrix("a", a, np.float32)
    _matrix("b", b, np.float32)
    if a.shape[1] != b.shape[0]:
        rule = f"of as many rows as a has columns, {a.shape[1]}"
        _fail("b", rule, f"shape {b.shape}")


def _matrix(name, value, dtype):
    if type(value) is np.ndarray and value.dtype == dtype and value.ndim == 2:
        valid = 0 not in value.shape
    else:
        valid = False
    if not valid:
        rule = f"a {dtype.__name__} array of two dimensions, none of them 0"
        _fail(name, rule, _shown(value))


def _shown(value):
    if isinstance(value, np.ndarray):
        return f"a {value.dtype} array of shape {value.shape}"
    if type(value) not in (int, float, bool, str, type(None)):
        return type(value).__name__
    try:
        return f"{type(value).__name__} {reprlib.repr(value)}"
    except ValueError:
        return f"{type(value).__name__} too long to show"


def _fail(name, rule, shown):
    raise VerificationArgumentError(f"{name}: must be {rule}, got {shown}")
