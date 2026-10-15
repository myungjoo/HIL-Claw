"""The result object of a call of ``sim.run`` or ``board.run`` (ADR-0063).

``ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`` fixes the
members of a result of either run tool and closes the member list (decision
9): a result has ``outcome`` (decision 2), ``condition`` (decision 3),
``shape``, ``n_max`` and ``sample_form`` (decision 5), ``resolution_ns`` and
``intervals_ns`` (decision 4), ``memory_bytes`` (decision 6) and ``ceiling``
and ``bound`` (decision 7), and no other. One list serves both tools
(decision 1). This module renders that table as plain Python values:

* :data:`CONVERGED`, :data:`NOT_CONVERGED` and :data:`BROKEN`: the three
  values of ``outcome``.
* :data:`CONDITIONS`: the seven values of ``condition``, in the order of
  decision 3.
* :data:`SAMPLE_FORMS`: the two values of ``sample_form``.
* :data:`WITHIN`, :data:`OVER`, :data:`NOT_JUDGED` and :data:`NOT_STATED`: the
  four values of ``ceiling``.
* :func:`completed`: the result of a completed run, from its outcome, its
  intervals and resolution and its figure or the absence of one.
* :func:`broken`: the result of a broken run, from its condition. It holds no
  measurement and no figure (decision 3).

A result is a new ``dict`` that is one JSON object in the strict sense
(decision 1). No member holds ``None``: a member that does not apply is left
out.

Choices that are this module's own and no rule of the record:

* ``ceiling`` is derived and is no argument, so no call can state a verdict
  its figure contradicts: :data:`NOT_STATED` when ``bound`` is ``None``,
  otherwise the verdict of :func:`hilclaw.harness.memory_ceiling.verdict` for
  the figure (none for a broken run) and ``bound``.
* The order of the members in a returned ``dict`` is that of the table:
  ``outcome``, ``condition``, ``shape``, ``n_max``, ``sample_form``,
  ``resolution_ns``, ``intervals_ns``, ``memory_bytes``, ``ceiling``,
  ``bound``; within ``shape`` ``m``, ``k``, ``n``.
* ``intervals_ns`` may be empty: the table states no length, and no relation
  between the intervals, ``n_max`` and ``outcome`` is checked here.
* An argument the table does not admit is refused with :class:`TypeError` when
  it is of a type that is not accepted and with :class:`ValueError` when it is
  of an accepted type but not an admitted value. The message starts with the
  name of the parameter. Nothing is returned then.
* An ``int`` that this interpreter does not convert to decimal text (the limit
  of ``sys.get_int_max_str_digits``) is refused with :class:`ValueError`,
  although the table states no upper bound for ``resolution_ns``,
  ``intervals_ns`` and ``memory_bytes``: this interpreter does not write an
  object that holds one as JSON text.

What the module does not do: it judges no report and replays no stopping
rule; it computes no summary. It maps nothing from a type of the harness or
from what an operation returns. It is no tool, is registered nowhere and
checks no stored result against the table. It gives no default of any value
and admits no ``memory_ceiling`` constraint. It reads and writes no file,
starts no process, keeps nothing between calls and has no command-line entry.
"""

import reprlib

from hilclaw.harness import memory_ceiling

CONVERGED = "converged"
NOT_CONVERGED = "not_converged"
BROKEN = "broken"
CONDITIONS = (
    "build_time_limit",
    "build_exit_status",
    "time_limit",
    "exit_status",
    "report_form",
    "zero_interval",
    "replay",
)
SAMPLE_FORMS = ("interval", "reciprocal")
WITHIN = "within"
OVER = "over"
NOT_JUDGED = "not_judged"
NOT_STATED = "not_stated"

_INTEGER_MAX = 2**53 - 1
_VERDICTS = {
    memory_ceiling.Verdict.WITHIN: WITHIN,
    memory_ceiling.Verdict.OVER: OVER,
    memory_ceiling.Verdict.NOT_JUDGED: NOT_JUDGED,
}


def completed(
    outcome,
    *,
    intervals_ns,
    resolution_ns,
    memory_bytes,
    m,
    k,
    n,
    n_max,
    sample_form,
    bound,
):
    """Return the result of a completed run whose report ended in ``outcome``.

    The result is a new ``dict`` with exactly the members ``outcome``,
    ``shape`` (a new ``dict`` ``{"m": m, "k": k, "n": n}``), ``n_max``,
    ``sample_form``, ``resolution_ns``, ``intervals_ns`` (a new ``list`` of
    the entries of the argument, in its order), ``memory_bytes`` when it is
    not ``None``, ``ceiling`` and ``bound`` when it is not ``None``. It has no
    ``condition``. ``ceiling`` is :data:`NOT_STATED` when ``bound`` is
    ``None``, whether or not there is a figure; otherwise :data:`NOT_JUDGED`
    when ``memory_bytes`` is ``None``, :data:`WITHIN` when
    ``memory_bytes <= bound`` and :data:`OVER` when ``memory_bytes > bound``
    (ADR-0063 decision 7, after ADR-0052 decision 5).

    ``outcome`` may be given by position; the other parameters are
    keyword-only. No parameter has a default.

    * ``outcome`` is exactly a ``str``, :data:`CONVERGED` or
      :data:`NOT_CONVERGED`.
    * ``intervals_ns`` is exactly a ``list`` or a ``tuple`` whose entries are
      each exactly an ``int`` of at least 1, with no upper bound.
    * ``resolution_ns`` is exactly an ``int`` of at least 0, with no upper
      bound.
    * ``memory_bytes`` is ``None`` (the run yielded no figure) or exactly an
      ``int`` of at least 1, with no upper bound.
    * ``m``, ``k``, ``n``, ``n_max``, ``sample_form`` and ``bound`` follow the
      rules of :func:`broken`.

    ``bool`` and other subclasses of ``int`` or ``str`` are refused, as is a
    member of an enumeration that stands for a value elsewhere. Raises
    :class:`TypeError` for an argument of another type and :class:`ValueError`
    for another value of an accepted type, as the module docstring says; the
    message names the parameter, and for an interval the entry
    (``intervals_ns[2]``). No argument is modified or kept, and the result
    shares no mutable object with an argument.
    """
    _choice("outcome", outcome, (CONVERGED, NOT_CONVERGED))
    common = _common(m, k, n, n_max, sample_form, bound)
    _integer("resolution_ns", resolution_ns, 0)
    intervals = _intervals(intervals_ns)
    if memory_bytes is not None:
        _integer("memory_bytes", memory_bytes, 1)
    result = {
        "outcome": outcome,
        **common,
        "resolution_ns": resolution_ns,
        "intervals_ns": intervals,
    }
    if memory_bytes is not None:
        result["memory_bytes"] = memory_bytes
    return _with_ceiling(result, memory_bytes, bound)


def broken(condition, *, m, k, n, n_max, sample_form, bound):
    """Return the result of a broken run that failed ``condition`` first.

    The result is a new ``dict`` with exactly the members ``outcome``
    (:data:`BROKEN`), ``condition``, ``shape``, ``n_max``, ``sample_form``,
    ``ceiling`` and ``bound`` when it is not ``None``. It has no
    ``resolution_ns``, ``intervals_ns`` or ``memory_bytes``, and the function
    takes none (ADR-0063 decision 3). ``ceiling`` is :data:`NOT_STATED` when
    ``bound`` is ``None`` and :data:`NOT_JUDGED` otherwise (decision 7).

    ``condition`` may be given by position; the other parameters are
    keyword-only. No parameter has a default.

    * ``condition`` is exactly a ``str`` that is one of :data:`CONDITIONS`.
    * ``m``, ``k`` and ``n`` are each exactly an ``int`` with
      1 <= value <= 2**53 - 1, and ``n_max`` one with 5 <= value <= 2**53 - 1
      (integers of ADR-0001).
    * ``sample_form`` is exactly a ``str`` that is one of
      :data:`SAMPLE_FORMS`.
    * ``bound`` is ``None`` (no ceiling stated) or exactly an ``int`` with
      0 <= value <= 2**53 - 1 (ADR-0050 decision 4).

    Raises :class:`TypeError` and :class:`ValueError` as :func:`completed`
    does; a ``str`` that is none of the seven values is a
    :class:`ValueError`.
    """
    _choice("condition", condition, CONDITIONS)
    result = {
        "outcome": BROKEN,
        "condition": condition,
        **_common(m, k, n, n_max, sample_form, bound),
    }
    return _with_ceiling(result, None, bound)


def _common(m, k, n, n_max, sample_form, bound):
    for name, value in (("m", m), ("k", k), ("n", n)):
        _integer(name, value, 1, _INTEGER_MAX)
    _integer("n_max", n_max, 5, _INTEGER_MAX)
    _choice("sample_form", sample_form, SAMPLE_FORMS)
    if bound is not None:
        _integer("bound", bound, 0, _INTEGER_MAX)
    return {
        "shape": {"m": m, "k": k, "n": n},
        "n_max": n_max,
        "sample_form": sample_form,
    }


def _with_ceiling(result, memory_bytes, bound):
    if bound is None:
        result["ceiling"] = NOT_STATED
    else:
        result["ceiling"] = _VERDICTS[memory_ceiling.verdict(memory_bytes, bound)]
        result["bound"] = bound
    return result


def _choice(name, value, admitted):
    if type(value) is not str:
        raise TypeError(f"{name}: must be a str, got {type(value).__name__}")
    if value not in admitted:
        raise ValueError(
            f"{name}: must be one of {admitted}, got {reprlib.repr(value)}"
        )


def _integer(name, value, minimum, maximum=None):
    if type(value) is not int:
        raise TypeError(f"{name}: must be an int, got {type(value).__name__}")
    try:
        str(value)
    except ValueError:
        bits = value.bit_length()
        raise ValueError(
            f"{name}: an int of {bits} bits has no decimal text here"
        ) from None
    if value < minimum:
        raise ValueError(
            f"{name}: must be at least {minimum}, got {reprlib.repr(value)}"
        )
    if maximum is not None and value > maximum:
        raise ValueError(
            f"{name}: must be at most 2**53 - 1, got {reprlib.repr(value)}"
        )


def _intervals(intervals_ns):
    if type(intervals_ns) not in (list, tuple):
        raise TypeError(
            "intervals_ns: must be a list or a tuple, "
            f"got {type(intervals_ns).__name__}"
        )
    for i, interval in enumerate(intervals_ns):
        _integer(f"intervals_ns[{i}]", interval, 1)
    return list(intervals_ns)
