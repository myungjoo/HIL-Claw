"""Measurement policy of ADR-0007: stopping test, summary and difference verdict.

``ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`` fixes, for the
samples of a measurement, when the repeats stop (decision 4), which number
stands for them (decision 5) and when two measurements are called different
(decision 7), with the values of decision 8, the constants below. This module
is those rules as pure functions of sequences of numbers. It knows neither the
measured quantity nor its direction: a verdict says "different" or "not
different" and nothing more.

Conventions of this module (not rules of the record):

- A sequence of samples is exactly a ``list`` or a ``tuple``, in the order
  taken, and each sample is exactly an ``int`` or a ``float`` that is positive
  and finite. ``len(values) * max(values)`` must not exceed the largest float,
  so that no sum of samples or of resampled samples can leave the float range.
  Each function states the fewest values it takes. Anything else raises
  :class:`InvalidSamplesError` before anything is computed; nothing is skipped,
  clipped or corrected, and no argument is modified.
- Samples are converted to ``float``. Sums are taken with :func:`math.fsum`,
  which is correctly rounded on every interpreter (the built-in ``sum`` of
  floats changed in CPython 3.12).
- The resampling generator is a ``random.Random(SEED)`` created inside each
  call, and every index is drawn as ``int(rng.random() * n)``: the sequence of
  ``random()`` for a seed is the one the Python documentation keeps across
  versions, which it does not promise for ``choices`` or ``randrange``. For
  each replicate the values of the first sequence are drawn before those of
  the second. The global generator of :mod:`random` is not used.
- Only ``n_max`` is a parameter of a call (decision 8). No function takes a
  seed, a generator or another constant.

What this module does not do: it takes no sample (no timer, no clock, no kernel
run) and reads or writes no file; it pairs or interleaves nothing and labels no
sample as steady state; it offers no defence against a forged measurement; and
it decides nothing about what a consumer does with a measurement that is not
converged.
"""

import enum
import math
import random
import reprlib
import sys
from fractions import Fraction

N_MIN = 5
N_MAX_DEFAULT = 10
CV_MAX = 0.05
TRIM = 1
DELTA = 0.02
CONFIDENCE = 0.95
RESAMPLES = 2000
SEED = 20261007

_TAIL = (1 - Fraction(str(CONFIDENCE))) / 2
_LOW = math.floor(_TAIL * RESAMPLES)
_HIGH = math.ceil((1 - _TAIL) * RESAMPLES) - 1
_RATIO_LIMIT = sys.float_info.max / 2


class InvalidSamplesError(ValueError):
    """An argument is outside the policy; the message names the argument and the rule."""


class State(enum.Enum):
    """What the stopping rule of decision 4 says about the samples taken so far."""

    CONTINUE = enum.auto()
    CONVERGED = enum.auto()
    NOT_CONVERGED = enum.auto()


def coefficient_of_variation(samples):
    """Return the spread of ``samples`` as CV = s / m (decision 4).

    m is the arithmetic mean and s the sample standard deviation with the
    divisor n - 1, both over all values given. At least two values are needed.
    Raises :class:`InvalidSamplesError` for input outside the policy.
    """
    return _cv(_checked("samples", samples, 2))


def stopping_state(samples, *, n_max=N_MAX_DEFAULT):
    """Return the :class:`State` of a measurement after the ``samples`` taken so far.

    With n = ``len(samples)``: fewer than :data:`N_MIN` samples is
    ``CONTINUE``, whatever the spread, and so is an empty sequence. From
    :data:`N_MIN` on the measurement is ``CONVERGED`` when
    :func:`coefficient_of_variation` of all samples is strictly below
    :data:`CV_MAX`; otherwise it is ``CONTINUE`` while n < ``n_max`` and
    ``NOT_CONVERGED`` at n = ``n_max``.

    The function sees only the sequence it is given and does not know whether
    a shorter prefix had already met the rule: the caller takes a repeat, asks
    again, and stops at the first state that is not ``CONTINUE``.

    ``n_max`` is the upper bound of repeats of the instance, an ``int`` of at
    least :data:`N_MIN`. More than ``n_max`` samples is an error: the record
    defines no such measurement. Raises :class:`InvalidSamplesError`.
    """
    values = _checked("samples", samples, 0)
    if type(n_max) is not int or n_max < N_MIN:
        _fail("n_max", f"an int of at least {N_MIN}", _shown(n_max))
    if len(values) > n_max:
        _fail("samples", f"a sequence of at most n_max = {n_max} values", len(values))
    if len(values) < N_MIN:
        return State.CONTINUE
    if _cv(values) < CV_MAX:
        return State.CONVERGED
    return State.CONTINUE if len(values) < n_max else State.NOT_CONVERGED


def trimmed_mean(values):
    """Return the trimmed mean of ``values`` (decision 5) as a ``float``.

    The values are sorted, the :data:`TRIM` lowest and the :data:`TRIM` highest
    are left out, and the arithmetic mean of the rest is returned. At least
    ``2 * TRIM + 1`` values are needed; that is the domain of the function,
    while a summary under the policy exists only for a measurement. Raises
    :class:`InvalidSamplesError` for input outside the policy.
    """
    return _trimmed(_checked("values", values, 2 * TRIM + 1))


def ratio_interval(a, b):
    """Return ``(low, high)``, the interval of decision 7 for the ordered pair (``a``, ``b``).

    :data:`RESAMPLES` replicates are drawn. For each, ``len(a)`` values are
    drawn from ``a`` and ``len(b)`` values from ``b``, independently and with
    replacement, and the ratio of the :func:`trimmed_mean` of the values drawn
    from ``b`` to that of the values drawn from ``a`` is taken. Of the sorted
    ratios the interval is the pair at the 1-based ranks
    ``floor((1 - c) / 2 * R) + 1`` and ``ceil((1 + c) / 2 * R)``, with
    c = :data:`CONFIDENCE` and R = :data:`RESAMPLES`: 51 and 1950.

    Each argument must be a measurement, that is hold at least :data:`N_MIN`
    samples; no upper limit is checked. The ratio of any sample of one to any
    sample of the other must not exceed half the largest float. Raises
    :class:`InvalidSamplesError` otherwise. The same arguments always give the
    same interval; exchanging them need not give the exact reciprocals.
    """
    x = _checked("a", a, N_MIN)
    y = _checked("b", b, N_MIN)
    if max(y) / min(x) > _RATIO_LIMIT or max(x) / min(y) > _RATIO_LIMIT:
        rule = "sequences whose sample ratios stay within half the largest float"
        _fail(
            "a, b",
            rule,
            f"a from {min(x)!r} to {max(x)!r}, b from {min(y)!r} to {max(y)!r}",
        )
    rng = random.Random(SEED)
    ratios = []
    for _ in range(RESAMPLES):
        base = _trimmed(_resampled(rng, x))
        ratios.append(_trimmed(_resampled(rng, y)) / base)
    ratios.sort()
    return ratios[_LOW], ratios[_HIGH]


def is_different(a, b):
    """Return whether the measurements ``a`` and ``b`` are different (decision 7).

    ``True`` when :func:`ratio_interval` of (``a``, ``b``) lies wholly above
    ``1 + DELTA`` or wholly below ``1 / (1 + DELTA)``, both strictly; ``False``
    otherwise. The verdict belongs to the ordered pair and has no direction.
    Arguments and errors are those of :func:`ratio_interval`.
    """
    low, high = ratio_interval(a, b)
    return low > 1 + DELTA or high < 1 / (1 + DELTA)


def _cv(values):
    mean = math.fsum(values) / len(values)
    squares = math.fsum(((value - mean) / mean) ** 2 for value in values)
    return math.sqrt(squares / (len(values) - 1))


def _trimmed(values):
    kept = sorted(values)[TRIM : len(values) - TRIM]
    return math.fsum(kept) / len(kept)


def _resampled(rng, values):
    return [values[int(rng.random() * len(values))] for _ in values]


def _checked(argument, values, minimum):
    if type(values) not in (list, tuple):
        _fail(argument, "a list or a tuple of samples", _shown(values))
    for position, value in enumerate(values):
        if type(value) not in (int, float) or not 0 < value < math.inf:
            rule = "an int or a float that is positive and finite"
            _fail(f"{argument}[{position}]", rule, _shown(value))
    if len(values) < minimum:
        _fail(argument, f"a sequence of at least {minimum} values", len(values))
    if values and len(values) * max(values) > sys.float_info.max:
        rule = "a sequence with len * max within the float range"
        _fail(argument, rule, f"{len(values)} values up to {_shown(max(values))}")
    return [float(value) for value in values]


def _shown(value):
    try:
        return f"{type(value).__name__} {reprlib.repr(value)}"
    except ValueError:
        return f"{type(value).__name__} too long to show"


def _fail(argument, rule, got):
    raise InvalidSamplesError(f"{argument}: must be {rule}, got {got}")
