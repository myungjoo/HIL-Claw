"""The figure and the verdict of a memory ceiling at ``cpu_standin`` (ADR-0052).

``ARCHITECTURE/decisions/ADR-0052-od13-memory-ceiling-measurement.md`` is the
rule. The figure (decision 3) is the maximum resident set size of the process
of one completed timing run, in bytes, one number with no baseline subtracted.
:func:`figure` turns the ``ru_maxrss`` the runner handed on
(:attr:`hilclaw.local_run.RunResult.max_rss`) into it by the unit rule of
decision 4: on ``linux`` (WSL included) the value times 1024, on ``darwin`` the
value as is, on any other platform no figure; a value that is not a positive
integer is no figure either. :func:`verdict` compares a figure with a ``bound``
as decision 5 says and has exactly three outcomes, :class:`Verdict`; *not
judged* is never *within*.

What this module does not do: it measures nothing itself and reads no platform
(the caller states it); it does not decide which run yields a figure (that is
:func:`hilclaw.harness.timing.run_timing`, for a completed run only); it admits
no ``memory_ceiling``, validates no spec or instance and calls no verdict for
any caller; it adds no margin, rounding, tolerance or statistic over runs; and
it names no member of the data plane.
"""

import enum
import reprlib

BOUND_MAX = 2**53 - 1

_BYTES_PER_UNIT = {"linux": 1024, "darwin": 1}


class MemoryCeilingError(ValueError):
    """A figure or a ``bound`` handed to :func:`verdict` is outside its domain."""


class Verdict(enum.Enum):
    """The three outcomes of ADR-0052 decision 5."""

    WITHIN = enum.auto()
    OVER = enum.auto()
    NOT_JUDGED = enum.auto()


def figure(max_rss, platform):
    """Return the figure in bytes as an ``int``, or ``None`` where there is none.

    ``max_rss`` is the raw ``ru_maxrss`` and ``platform`` the value of
    :data:`sys.platform` the caller read. The figure is ``max_rss * 1024`` for
    ``"linux"`` and ``max_rss`` for ``"darwin"``; every other ``platform``, and
    a ``max_rss`` that is not exactly an ``int`` of at least 1 (``None``, a
    ``bool``, a ``float``, ...), give ``None``. Never raises.
    """
    unit = _BYTES_PER_UNIT.get(platform) if type(platform) is str else None
    if unit is None or type(max_rss) is not int or max_rss < 1:
        return None
    return max_rss * unit


def verdict(figure_bytes, bound):
    """Return the :class:`Verdict` of ``figure_bytes`` against ``bound``.

    ``figure_bytes`` is a figure as :func:`figure` returns it. The result is
    ``Verdict.NOT_JUDGED`` if it is ``None``, ``Verdict.WITHIN`` if
    ``figure_bytes <= bound`` (equality is within) and ``Verdict.OVER`` if
    ``figure_bytes > bound``. ``bound`` is exactly an ``int`` with
    0 <= ``bound`` <= :data:`BOUND_MAX` (an integer of ADR-0001, in bytes) and
    ``figure_bytes`` is ``None`` or exactly an ``int`` of at least 1; a
    ``bool`` is not an ``int`` here. Raises :class:`MemoryCeilingError`
    otherwise.
    """
    if type(bound) is not int or not 0 <= bound <= BOUND_MAX:
        _fail("bound", "an int with 0 <= bound <= 2**53 - 1", bound)
    if figure_bytes is None:
        return Verdict.NOT_JUDGED
    if type(figure_bytes) is not int or figure_bytes < 1:
        _fail("figure_bytes", "None or an int of at least 1", figure_bytes)
    return Verdict.WITHIN if figure_bytes <= bound else Verdict.OVER


def _fail(name, rule, value):
    if isinstance(value, int) and value.bit_length() > 64:
        shown = f"of {value.bit_length()} bits"
    else:
        shown = reprlib.repr(value)
    message = f"{name}: must be {rule}, got {type(value).__name__} {shown}"
    raise MemoryCeilingError(message)
