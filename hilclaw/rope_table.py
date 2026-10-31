"""Host-side builder of the RoPE frequency table (ADR-0161 decision 4).

``ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`` defines the
bf16 contract of kind ``rope`` on ``cpu_standin``. Its decision 4 puts the
frequency table outside the kernels: the host side builds it once per
generation from the model parameters ``head_dim``, ``rope_theta`` and the four
scaling constants (ADR-0153 decision 3 (a), "the RoPE constants"), and hands
it to the model program as one more array (ADR-0153 decision 3 (b)). Pair i of
a head takes table columns 2i and 2i + 1 (decision 5); the operand
``freqs_cis`` of a call is ``fp32`` and its row i is the table row of position
P + i (decision 6); the verification value sets are rows of this table built
with Meta's constants (decision 13). This module has three functions:

* :func:`frequencies`: the scaled frequencies g(i), each the binary64 value
  nearest to the exact one.
* :func:`build`: the table, a ``float32`` array with rows for positions 0 to
  ``positions`` - 1.
* :func:`constant_refusals`: the values of the five constants that the two
  functions above refuse, all of them, without computing a frequency.

**The rule** (decision 4), with d = ``head_dim``, θ = ``theta``,
s = ``scale_factor``, a = ``low_freq_factor``, b = ``high_freq_factor`` and
L = ``old_context_len``: for i = 0 ... d/2 - 1, f(i) = θ^(-2i/d);
λ = 2π / f(i); g(i) = f(i)/s if λ > L/a; g(i) = (1 - σ) · f(i)/s + σ · f(i)
with σ = (L/λ - a)/(b - a) if L/b ≤ λ ≤ L/a; g(i) = f(i) otherwise;
angle(t, i) = t · g(i); entry (t, 2i) = cos angle(t, i) and entry
(t, 2i + 1) = sin angle(t, i). The scaling always applies; there is no switch.

**Precision.** Each entry is the binary32 value nearest to the exact cosine or
sine of the exact angle, ties to even, with every input taken as its exact
value (a ``float`` is its exact binary value). Row 0 is exactly 1.0 and +0.0.

**Method** (decision 4 leaves it to the builder). Nothing rests on a binary64
``cos``, ``sin`` or ``pow``. At a working precision of P decimal digits
(:mod:`decimal`), every quantity up to the reduced angle is an interval that
contains the exact value: sums, products and quotients are rounded outward,
``ln`` and ``exp`` (correctly rounded by :mod:`decimal`) are widened by one
unit in the last place, and π comes from Machin's formula in integer
arithmetic with a bound on its truncation. The band of a column is taken only
when the interval of λ lies inside it. The angle is reduced by a whole number
of turns to an interval [r0, r1] with |r0| < 3.2, and cos and sin are summed
together from the series of exp(i r0) at P digits until a term below
10^(1-P), after at least four terms. With M terms the sums are within
100 · M · 10^(1-P) of cos r0 and sin r0: each term is within a relative
3 · M · 10^(1-P) of its exact value, the terms add up to at most e^3.2 < 25,
each addition errs by at most half a unit in the last place of a sum below
25, and the omitted tail of each alternating series is below its first
omitted term. Adding r1 - r0 (cos and sin change by at most the change of
their argument) gives a bound E, and an entry is taken when v - E and v + E
round to the same binary32 value, sign included. A column whose band is not
decided, or an entry or frequency that is not taken, is recomputed at twice
the precision. λ never equals L/a or L/b (it is transcendental), and in the
outer bands cos and sin of a nonzero algebraic angle are transcendental, so
never on a rounding boundary; for the middle band no theorem rules a boundary
out, and none has been met. P starts at 36 digits plus the integer digits of
the largest angle. The rounding to binary32 (or binary64) is a single exact
rounding of a decimal value, ties to even.

**Inputs.** Every constant is a required keyword argument with no default.
The scale factor Llama 3.2 1B needs is 32 (the owner's answer to HQ-0070;
ADR-0176 O2); it is the caller's input, not this module's choice. Two limits
are conventions of this module, not rules of the record: ``high_freq_factor`` must exceed
``low_freq_factor``, so b - a is never 0, and ``positions * head_dim`` must not
exceed :data:`hilclaw.keys.MAX_INTEGER`.

What the module does not do: it has no model parameters type and holds no
Llama constant. It binds nothing, knows no call site, slices no rows for a
position P and calls no kernel. It has no model program, reads and writes no
file, starts no process, is no tool and has no command-line entry. It has no
harness mechanism and builds no bf16 or float64 table.
"""

import contextlib
import decimal
import math
from decimal import Decimal

import numpy

from hilclaw import keys

_DIGITS = 36
_BINARY32 = (24, -126, 127)
_BINARY64 = (53, -1022, 1023)
_CONSTANTS = (
    "theta",
    "scale_factor",
    "low_freq_factor",
    "high_freq_factor",
    "old_context_len",
)


def frequencies(
    *,
    head_dim,
    theta,
    scale_factor,
    low_freq_factor,
    high_freq_factor,
    old_context_len,
):
    """Return the scaled frequencies g(0) ... g(d/2 - 1) of ADR-0161 decision 4, as a ``tuple`` of ``float``.

    The arguments are d, θ, s, a, b and L of the rule. Entry i of the result is
    the binary64 value nearest to the exact g(i), ties to even (an infinity
    where g(i) is beyond the binary64 range); these are the g(i) :func:`build`
    uses. ``head_dim`` is exactly an ``int`` (``bool`` refused), even, from 2
    to 2**53 - 1; each of the five constants is exactly an ``int`` or a
    ``float`` (``bool`` refused), finite and greater than 0, and
    ``high_freq_factor`` is greater than ``low_freq_factor``. The arguments
    are checked in the order of the signature; the first bad one raises
    :class:`TypeError` for a wrong type and :class:`ValueError` otherwise,
    with ``parameter`` set to its name.
    """
    constants = _checked(
        head_dim,
        (theta, scale_factor, low_freq_factor, high_freq_factor, old_context_len),
    )
    result = []
    for i in range(head_dim // 2):
        digits = _DIGITS
        while True:
            arithmetic, g = _frequency(i, head_dim, constants, digits)
            value = _rounded(g, _BINARY64)
            if value is not None:
                break
            digits = 2 * arithmetic.digits
        result.append(value)
    return tuple(result)


def build(
    *,
    head_dim,
    theta,
    scale_factor,
    low_freq_factor,
    high_freq_factor,
    old_context_len,
    positions,
):
    """Return the RoPE frequency table of ADR-0161 decision 4 for positions 0 to ``positions`` - 1.

    The result is a new C-contiguous ``numpy.ndarray`` of dtype ``float32``
    and shape ``(positions, head_dim)``: entry ``[t, 2i]`` is cos(t · g(i))
    and entry ``[t, 2i + 1]`` is sin(t · g(i)), each the binary32 value
    nearest to the exact value, ties to even. The other arguments are those of
    :func:`frequencies`, checked as there; ``positions``, checked last, is
    exactly an ``int`` (``bool`` refused) from 1 to 2**53 - 1 with
    ``positions * head_dim`` no larger than 2**53 - 1. Raises
    :class:`TypeError` or :class:`ValueError` with ``parameter`` as
    :func:`frequencies` does.
    """
    constants = _checked(
        head_dim,
        (theta, scale_factor, low_freq_factor, high_freq_factor, old_context_len),
    )
    with _parameter("positions"):
        _integer(positions, 1)
        if positions * head_dim > keys.MAX_INTEGER:
            raise ValueError("positions * head_dim exceeds 2**53 - 1")
    table = numpy.empty((positions, head_dim), dtype=numpy.float32)
    table[0, 0::2] = 1.0
    table[0, 1::2] = 0.0
    if positions == 1:
        return table
    columns = [
        _frequency(i, head_dim, constants, _DIGITS) for i in range(head_dim // 2)
    ]
    largest = columns[0][0].ceiling.multiply(
        max(g[1] for _, g in columns), positions - 1
    )
    start = _DIGITS + max(0, largest.adjusted() + 1)
    for i in range(head_dim // 2):
        cache = {}
        for t in range(1, positions):
            digits = start
            while True:
                if digits not in cache:
                    cache[digits] = _frequency(i, head_dim, constants, digits)
                arithmetic, g = cache[digits]
                entry = _entry(t, arithmetic, g)
                if entry is not None:
                    break
                digits = 2 * arithmetic.digits
            table[t, 2 * i], table[t, 2 * i + 1] = entry
    return table


def constant_refusals(
    *,
    theta,
    scale_factor,
    low_freq_factor,
    high_freq_factor,
    old_context_len,
):
    """Return the refusals of the values of the five RoPE constants, as a ``tuple`` of ``(name, reason)`` pairs.

    The constants are those of :func:`frequencies`, refused by the same rules,
    but every one is looked at and nothing is computed. First each constant,
    in the order of the signature, must be exactly an ``int`` or a ``float``
    (``bool`` refused); the first that is not raises :class:`TypeError` with
    ``parameter`` set to its name. Then the result holds, in signature order,
    one pair for each constant that is not finite or not greater than 0, and
    one for ``high_freq_factor`` when it is not greater than a
    ``low_freq_factor`` that is itself not refused. ``reason`` is the text the
    :class:`ValueError` of :func:`frequencies` carries. An empty result means
    :func:`frequencies` and :func:`build` accept the constants.
    """
    constants = (
        theta,
        scale_factor,
        low_freq_factor,
        high_freq_factor,
        old_context_len,
    )
    for name, value in zip(_CONSTANTS, constants):
        with _parameter(name):
            _constant_type(value)
    refusals = []
    for name, value in zip(_CONSTANTS, constants):
        reason = _constant_value(name, value, constants[2])
        if reason is not None:
            refusals.append((name, reason))
    return tuple(refusals)


class _Arithmetic:
    def __init__(self, digits):
        self.digits = digits
        options = {"prec": digits, "Emax": decimal.MAX_EMAX, "Emin": decimal.MIN_EMIN}
        self.floor = decimal.Context(rounding=decimal.ROUND_FLOOR, **options)
        self.ceiling = decimal.Context(rounding=decimal.ROUND_CEILING, **options)
        self.near = decimal.Context(rounding=decimal.ROUND_HALF_EVEN, **options)
        self.tau = self.mul((Decimal(2), Decimal(2)), _pi(self))

    def add(self, x, y):
        return self.floor.add(x[0], y[0]), self.ceiling.add(x[1], y[1])

    def sub(self, x, y):
        return self.floor.subtract(x[0], y[1]), self.ceiling.subtract(x[1], y[0])

    def mul(self, x, y):
        return self._outward(self.floor.multiply, self.ceiling.multiply, x, y)

    def div(self, x, y):
        return self._outward(self.floor.divide, self.ceiling.divide, x, y)

    def exp(self, x):
        low, high = (self._widened(self.near.exp(end)) for end in x)
        return low[0], high[1]

    def ln(self, value):
        return self._widened(self.near.ln(value))

    def _widened(self, value):
        return value.next_minus(self.near), value.next_plus(self.near)

    @staticmethod
    def _outward(low, high, x, y):
        return (
            min(low(p, q) for p in x for q in y),
            max(high(p, q) for p in x for q in y),
        )


def _pi(arithmetic):
    scale = arithmetic.digits + 10
    unit = 10**scale
    total = error = 0
    for weight, n in ((16, 5), (-4, 239)):
        series, terms = _arctan_inverse(n, unit)
        total += weight * series
        error += abs(weight) * (terms + 1)
    return (
        Decimal(total - error).scaleb(-scale, arithmetic.floor),
        Decimal(total + error).scaleb(-scale, arithmetic.ceiling),
    )


def _arctan_inverse(n, unit):
    term = unit // n
    total = terms = 0
    while term:
        part = term // (2 * terms + 1)
        total += -part if terms % 2 else part
        term //= n * n
        terms += 1
    return total, terms


def _frequency(i, head_dim, constants, digits):
    while True:
        arithmetic = _Arithmetic(digits)
        g = _scaled(i, head_dim, constants, arithmetic)
        if g is not None:
            return arithmetic, g
        digits *= 2


def _scaled(i, head_dim, constants, arithmetic):
    a = arithmetic
    theta, s, low, high, length = ((value, value) for value in constants)
    exponent = (a.floor.divide(-2 * i, head_dim), a.ceiling.divide(-2 * i, head_dim))
    f = a.exp(a.mul(exponent, a.ln(theta[0])))
    wavelength = a.div(a.tau, f)
    upper = a.div(length, low)
    lower = a.div(length, high)
    if wavelength[0] > upper[1]:
        return a.div(f, s)
    if wavelength[1] < lower[0]:
        return f
    if wavelength[0] >= lower[1] and wavelength[1] <= upper[0]:
        sigma = a.div(a.sub(a.div(length, wavelength), low), a.sub(high, low))
        one = (Decimal(1), Decimal(1))
        return a.add(a.mul(a.sub(one, sigma), a.div(f, s)), a.mul(sigma, f))
    return None


def _entry(t, arithmetic, g):
    a = arithmetic
    angle = (a.floor.multiply(t, g[0]), a.ceiling.multiply(t, g[1]))
    turns = a.near.divide(angle[0], a.tau[0]).to_integral_value(context=a.near)
    low = a.floor.subtract(angle[0], a.ceiling.multiply(turns, a.tau[1]))
    high = a.ceiling.subtract(angle[1], a.floor.multiply(turns, a.tau[0]))
    cosine, sine, error = _cos_sin(low, a)
    error = a.ceiling.add(error, a.ceiling.subtract(high, low))
    result = []
    for value in (cosine, sine):
        rounded = _rounded(
            (a.floor.subtract(value, error), a.ceiling.add(value, error)), _BINARY32
        )
        if rounded is None:
            return None
        result.append(rounded)
    return tuple(result)


def _cos_sin(r, arithmetic):
    near = arithmetic.near
    small = Decimal(1).scaleb(1 - arithmetic.digits)
    term = Decimal(1)
    sums = [term, Decimal(0)]
    n = 0
    while n < 4 or abs(term) >= small:
        n += 1
        term = near.divide(near.multiply(term, r), n)
        part = n % 2
        if n % 4 < 2:
            sums[part] = near.add(sums[part], term)
        else:
            sums[part] = near.subtract(sums[part], term)
    return sums[0], sums[1], Decimal(100 * n).scaleb(1 - arithmetic.digits)


def _rounded(interval, binary):
    low, high = (_nearest(value, *binary) for value in interval)
    if low == high and math.copysign(1.0, low) == math.copysign(1.0, high):
        return low
    return None


def _nearest(value, bits, emin, emax):
    numerator, denominator = value.as_integer_ratio()
    magnitude = abs(numerator)
    sign = -1.0 if numerator < 0 else 1.0
    exponent = magnitude.bit_length() - denominator.bit_length()
    if magnitude << max(-exponent, 0) < denominator << max(exponent, 0):
        exponent -= 1
    quantum = max(exponent, emin) - bits + 1
    if quantum < 0:
        quotient, rest = divmod(magnitude << -quantum, denominator)
        twice, whole = 2 * rest, denominator
    else:
        quotient, rest = divmod(magnitude, denominator << quantum)
        twice, whole = 2 * rest, denominator << quantum
    if twice > whole or (twice == whole and quotient % 2):
        quotient += 1
    if quotient.bit_length() + quantum > emax + 1:
        return math.copysign(math.inf, sign)
    return math.copysign(math.ldexp(quotient, quantum), sign)


def _checked(head_dim, constants):
    with _parameter("head_dim"):
        _integer(head_dim, 2)
        if head_dim % 2:
            raise ValueError(f"must be even, got {head_dim}")
    for name, value in zip(_CONSTANTS, constants):
        with _parameter(name):
            _constant_type(value)
            reason = _constant_value(name, value, constants[2])
            if reason is not None:
                raise ValueError(reason)
    return tuple(Decimal(value) for value in constants)


def _constant_type(value):
    if type(value) not in (int, float):
        raise TypeError(f"must be an int or a float, got {type(value).__name__}")


def _constant_value(name, value, low):
    if not _positive(value):
        return f"must be finite and greater than 0, got {value!r}"
    if name == "high_freq_factor" and _positive(low) and value <= low:
        return "must be greater than low_freq_factor"
    return None


def _positive(value):
    return value > 0 and (type(value) is int or math.isfinite(value))


def _integer(value, least):
    if type(value) is not int:
        raise TypeError(f"must be an int, got {type(value).__name__}")
    if not least <= value <= keys.MAX_INTEGER:
        raise ValueError(f"must be from {least} to 2**53 - 1, got {value}")


@contextlib.contextmanager
def _parameter(name):
    try:
        yield
    except (TypeError, ValueError) as error:
        error.parameter = name
        raise
