"""The result object of a check of ``correctness.check`` (ADR-0042 decision 7).

``ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md``
fixes the members of a result and closes the member list (decision 7): a
result has ``outcome`` (decision 2), ``condition`` (decision 3), ``shape``,
``draws`` and ``tolerance`` (decision 5) and ``counts`` (decision 4), and no
other. This module renders that table as plain Python values:

* :data:`PASS`, :data:`FAIL` and :data:`BROKEN`: the three values of
  ``outcome``.
* :data:`CONDITIONS`: the four values of ``condition``, in the order of
  decision 3.
* :func:`completed`: the result of a completed run, from its per-draw counts.
  It has ``outcome``, ``shape``, ``draws``, ``tolerance`` and ``counts`` and
  no ``condition``.
* :func:`broken`: the result of a broken run, from its condition. It has
  ``outcome``, ``condition``, ``shape``, ``draws`` and ``tolerance`` and no
  ``counts``.

A result is a new ``dict`` that is one JSON object in the strict sense
(decision 1). No member holds ``None``: a member that does not apply is left
out.

Choices that are this module's own and no rule of the record:

* The order of the members in a returned ``dict`` is that of the table:
  ``outcome``, ``condition``, ``shape``, ``draws``, ``tolerance``, ``counts``.
* ``rtol`` and ``atol`` are returned as the ``float`` of the argument, so the
  number in a result is the binary64 value itself (decision 5 leaves the
  spelling of the literal open). A negative zero is not negative; it is
  returned as it is.
* An argument the table does not admit is refused with :class:`TypeError` when
  it is of a type that is not accepted and with :class:`ValueError` when it is
  of an accepted type but not an admitted value. The message starts with the
  name of the parameter. Nothing is returned then.
* An ``int`` that this interpreter does not convert to decimal text (the limit
  of ``sys.get_int_max_str_digits``) is refused with :class:`ValueError`,
  although the table states no upper bound: this interpreter does not write
  an object that holds one as JSON text.

What the module does not do: it judges nothing and compares no output with a
reference. It maps nothing from a type of the harness or from what an
operation returns. It is no tool and is bound to none, and it checks no stored
result against the table. It gives no default of any value: no number of
draws, no tolerance and no dimension. It reads and writes no file, starts no
process, keeps nothing between calls and has no command-line entry. It
imports ``math`` and ``reprlib`` of the standard library and nothing else.
"""

import math
import reprlib

PASS = "pass"
FAIL = "fail"
BROKEN = "broken"
CONDITIONS = ("time_limit", "exit_status", "report_form", "check_value")


def completed(*, m, k, n, draws, rtol, atol, counts):
    """Return the result of a completed run with the per-draw ``counts``.

    The result is a new ``dict`` with exactly the members ``outcome``,
    ``shape`` (a new ``dict`` ``{"m": m, "k": k, "n": n}``), ``draws``,
    ``tolerance`` (a new ``dict`` ``{"rtol": float(rtol), "atol":
    float(atol)}``) and ``counts``: a new ``list`` with one new ``dict``
    ``{"failed": ..., "non_finite": ...}`` for each entry of the argument, in
    its order. It has no ``condition``. ``outcome`` is derived from the
    counts and is not an argument: :data:`PASS` when every ``failed`` is 0
    and :data:`FAIL` when at least one is 1 or more (ADR-0042 decision 4).

    All parameters are keyword-only and none has a default.

    * ``m``, ``k``, ``n`` and ``draws`` are each exactly an ``int`` (``bool``
      and other subclasses are refused) of at least 1.
    * ``rtol`` and ``atol`` are each exactly an ``int`` or a ``float``,
      finite, not negative and, for an ``int``, within what a ``float``
      holds.
    * ``counts`` is exactly a ``list`` or a ``tuple`` with ``draws`` entries.
      Each entry is a ``tuple`` of two items, ``(failed, non_finite)``; an
      instance of a subclass of ``tuple``, such as
      :class:`hilclaw.harness.verification_arrays.Counts`, is read as the
      tuple it is. Each item is exactly an ``int`` of at least 0, with
      ``non_finite <= failed <= m * n`` (the relations of decision 4).

    Raises :class:`TypeError` for an argument of another type and
    :class:`ValueError` for another value of an accepted type, as the module
    docstring says; the message names the parameter, and for a count the
    entry (``counts[1].failed``). No argument is modified or kept, and the
    result shares no object with ``counts``.
    """
    common = _common(m, k, n, draws, rtol, atol)
    entries = _counts(counts, draws, m * n)
    outcome = FAIL if any(entry["failed"] for entry in entries) else PASS
    return {"outcome": outcome, **common, "counts": entries}


def broken(condition, *, m, k, n, draws, rtol, atol):
    """Return the result of a broken run that failed ``condition`` first.

    The result is a new ``dict`` with exactly the members ``outcome``
    (:data:`BROKEN`), ``condition``, ``shape``, ``draws`` and ``tolerance``,
    the last three as in :func:`completed`. It has no ``counts`` (ADR-0042
    decision 4), and the function takes none.

    ``condition`` is exactly a ``str`` that is one of :data:`CONDITIONS`. A
    value of another type that stands for a condition elsewhere, such as a
    member of an enumeration, is refused like any other value that is no
    ``str``. The other parameters are keyword-only, none has a default, and
    each follows the rule of :func:`completed`.

    Raises :class:`TypeError` and :class:`ValueError` as :func:`completed`
    does; a ``str`` that is none of the four values is a :class:`ValueError`.
    """
    if type(condition) is not str:
        raise TypeError(f"condition: must be a str, got {type(condition).__name__}")
    if condition not in CONDITIONS:
        shown = reprlib.repr(condition)
        raise ValueError(f"condition: must be one of {CONDITIONS}, got {shown}")
    return {
        "outcome": BROKEN,
        "condition": condition,
        **_common(m, k, n, draws, rtol, atol),
    }


def _common(m, k, n, draws, rtol, atol):
    for name, value in (("m", m), ("k", k), ("n", n), ("draws", draws)):
        _integer(name, value, 1)
    return {
        "shape": {"m": m, "k": k, "n": n},
        "draws": draws,
        "tolerance": {"rtol": _number("rtol", rtol), "atol": _number("atol", atol)},
    }


def _integer(name, value, minimum):
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


def _number(name, value):
    if type(value) not in (int, float):
        raise TypeError(
            f"{name}: must be an int or a float, got {type(value).__name__}"
        )
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"{name}: an int beyond what a float holds") from None
    if not 0 <= number < math.inf:
        raise ValueError(f"{name}: must be finite and not negative, got {number!r}")
    return number


def _counts(counts, draws, elements):
    if type(counts) not in (list, tuple):
        raise TypeError(
            f"counts: must be a list or a tuple, got {type(counts).__name__}"
        )
    if len(counts) != draws:
        raise ValueError(f"counts: must have {draws} entries, got {len(counts)}")
    entries = []
    for i, entry in enumerate(counts):
        if not isinstance(entry, tuple):
            raise TypeError(f"counts[{i}]: must be a tuple, got {type(entry).__name__}")
        items = tuple(tuple.__iter__(entry))
        if len(items) != 2:
            raise ValueError(f"counts[{i}]: must have 2 items, got {len(items)}")
        failed, non_finite = items
        _integer(f"counts[{i}].failed", failed, 0)
        _integer(f"counts[{i}].non_finite", non_finite, 0)
        if failed > elements:
            raise ValueError(
                f"counts[{i}].failed: must be at most m * n, got {reprlib.repr(failed)}"
            )
        if non_finite > failed:
            shown = reprlib.repr(non_finite)
            raise ValueError(
                f"counts[{i}].non_finite: must be at most failed, got {shown}"
            )
        entries.append({"failed": failed, "non_finite": non_finite})
    return entries
