"""The result object of a check of ``correctness.check`` (ADR-0042 decision 7).

``ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md``
fixes the members of a result and closes the member list (decision 7): a
result has ``outcome`` (decision 2), ``condition`` (decision 3), ``shape``,
``draws`` and ``tolerance`` (decision 5) and ``counts`` (decision 4), and no
other. This module renders that table as plain Python values:

* :data:`PASS`, :data:`FAIL` and :data:`BROKEN`: the three values of
  ``outcome``.
* :data:`CONDITIONS`: the six values of ``condition``, in the order of
  decision 3 as ADR-0060 decision 4 amends it.
* :func:`completed`: the result of a completed run, from its per-draw counts.
  It has ``outcome``, ``shape``, ``draws``, ``tolerance`` and ``counts`` and
  no ``condition``.
* :func:`broken`: the result of a broken run, from its condition. It has
  ``outcome``, ``condition``, ``shape``, ``draws`` and ``tolerance`` and no
  ``counts``.
* :func:`bf16_completed` and :func:`bf16_broken`: the same two results of a
  check of a bf16 kind of :data:`BF16_KINDS`, the list the owner gave
  (``ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md``
  decision 3, HQ-0077): ADR-0042's list with ``shape`` holding the shape
  members of the kind, named and ordered as the parameters of the
  contract's ``task_contract``, and ``failed`` at most the number of output
  elements of the kind (``m * n``, and ``m * h * d`` for ``rope`` and
  ``sdpa_kv_cache``; for ``rope`` the shape is ``m``, ``h``, ``d`` with ``d``
  even, the rule of ADR-0161 decision 11).
  Each ``counts`` entry of an ``sdpa_kv_cache`` check also holds
  ``cache_differs``, the number of cache elements over both allocations
  that differ in that draw (ADR-0165 decision 8), and such a result is a
  fail when some ``failed`` or some ``cache_differs`` is 1 or more. Such a
  result holds no ``kind``, ``dtype`` or ``layout``.

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
imports ``inspect``, ``math`` and ``reprlib`` of the standard library and
:mod:`hilclaw.contract_table`, whose entries' ``task_contract`` parameters
name the shape members, and nothing else; it reads the table and changes
nothing in it.
"""

import inspect
import math
import reprlib

from hilclaw import contract_table

PASS = "pass"
FAIL = "fail"
BROKEN = "broken"
CONDITIONS = (
    "build_time_limit",
    "build_exit_status",
    "time_limit",
    "exit_status",
    "report_form",
    "check_value",
)
#: The kinds whose bf16 check results this module builds (those of ADR-0163 to ADR-0165), in table order.
BF16_KINDS = ("gemm", "rmsnorm", "elementwise_add", "swiglu", "rope", "sdpa_kv_cache")
_SDPA = "sdpa_kv_cache"
_ROPE = "rope"
_EVEN = {_ROPE: ("d",)}
_BF16_SHAPES = {
    kind: tuple(inspect.signature(entry.contract.task_contract).parameters)
    for kind in BF16_KINDS
    for (key_kind, dtype, _, _), entry in contract_table.TABLE.items()
    if (key_kind, dtype) == (kind, "bf16")
}


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
    result shares no mutable object with ``counts``.
    """
    return _completed(_common({"m": m, "k": k, "n": n}, draws, rtol, atol), counts)


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
    does; a ``str`` that is none of the six values is a :class:`ValueError`.
    """
    _condition(condition)
    return _broken(condition, _common({"m": m, "k": k, "n": n}, draws, rtol, atol))


def bf16_completed(kind, dims, *, draws, rtol, atol, counts):
    """Return the result of a completed run of a bf16 check of ``kind``.

    As :func:`completed`, with ``shape`` a new ``dict`` that pairs the
    shape members of ``kind`` with ``dims`` in their order (``{"m": ...,
    "k": ..., "n": ...}`` for ``gemm``, ``{"m": ..., "l": ..., "h": ...,
    "h_kv": ..., "d": ...}`` for ``sdpa_kv_cache``, ``{"m": ..., "h": ...,
    "d": ...}`` for ``rope``, ``{"m": ..., "n": ...}`` for the other three
    kinds), and each ``failed`` at most the number of output elements of the
    kind: ``m * n``, or ``m * h * d`` for ``rope`` and ``sdpa_kv_cache``.
    For ``rope`` ``d`` must also be even (ADR-0161 decision 11), as in every
    record the contract covers.

    For ``sdpa_kv_cache`` (ADR-0177 decision 3, HQ-0077; ADR-0165
    decision 8) each entry of ``counts`` is a ``tuple`` of three items,
    ``(failed, non_finite, cache_differs)``, such as a
    :class:`hilclaw.harness.bf16_sdpa_kv_cache_verification.DrawCounts`;
    ``cache_differs`` is exactly an ``int`` of at least 0 and at most
    ``2 * (l + 2 * m) * h_kv * d``, the number of elements of both cache
    allocations. Each entry of the result is a new ``dict``
    ``{"failed": ..., "non_finite": ..., "cache_differs": ...}``, and
    ``outcome`` is :data:`FAIL` when at least one ``failed`` or one
    ``cache_differs`` is 1 or more and :data:`PASS` otherwise. No relation
    between the five dimensions is checked.

    * ``kind`` is exactly a ``str`` of :data:`BF16_KINDS`.
    * ``dims`` is exactly a ``tuple`` with one item per shape member of
      ``kind``, each exactly an ``int`` of at least 1; a message about an
      item names its member.
    * ``draws``, ``rtol``, ``atol`` and ``counts`` (keyword-only, no default)
      follow the rules of :func:`completed`, with the entries of
      ``sdpa_kv_cache`` above.

    Checked in the order ``kind``, ``dims``, ``draws``, ``rtol``, ``atol``,
    ``counts``. Raises :class:`TypeError` and :class:`ValueError` as the
    module docstring says.
    """
    common = _common(_shape(kind, dims), draws, rtol, atol, _EVEN.get(kind, ()))
    if kind == _ROPE:
        m, h, d = common["shape"].values()
        return _completed(common, counts, ("m * h * d", m * h * d))
    if kind != _SDPA:
        return _completed(common, counts)
    m, l, h, h_kv, d = common["shape"].values()
    bounds = (
        ("m * h * d", m * h * d),
        ("2 * (l + 2 * m) * h_kv * d", 2 * (l + 2 * m) * h_kv * d),
    )
    return _completed(common, counts, *bounds)


def bf16_broken(condition, kind, dims, *, draws, rtol, atol):
    """Return the result of a broken run of a bf16 check of ``kind``.

    As :func:`broken`, with ``shape`` as in :func:`bf16_completed`.
    ``condition`` is checked first, then the other arguments in the order of
    :func:`bf16_completed`.
    """
    _condition(condition)
    common = _common(_shape(kind, dims), draws, rtol, atol, _EVEN.get(kind, ()))
    return _broken(condition, common)


def _condition(condition):
    if type(condition) is not str:
        raise TypeError(f"condition: must be a str, got {type(condition).__name__}")
    if condition not in CONDITIONS:
        shown = reprlib.repr(condition)
        raise ValueError(f"condition: must be one of {CONDITIONS}, got {shown}")


def _broken(condition, common):
    return {"outcome": BROKEN, "condition": condition, **common}


def _completed(common, counts, output=None, cache=None):
    if output is None:
        shape = common["shape"]
        output = ("m * n", shape["m"] * shape["n"])
    entries = _counts(counts, common["draws"], output, cache)
    failing = any(entry["failed"] or entry.get("cache_differs") for entry in entries)
    return {"outcome": FAIL if failing else PASS, **common, "counts": entries}


def _shape(kind, dims):
    if type(kind) is not str:
        raise TypeError(f"kind: must be a str, got {type(kind).__name__}")
    if kind not in _BF16_SHAPES:
        raise ValueError(f"kind: must be one of {BF16_KINDS}, got {reprlib.repr(kind)}")
    names = _BF16_SHAPES[kind]
    if type(dims) is not tuple:
        raise TypeError(f"dims: must be a tuple, got {type(dims).__name__}")
    if len(dims) != len(names):
        raise ValueError(
            f"dims: must have {len(names)} items for {kind}, got {len(dims)}"
        )
    return dict(zip(names, dims, strict=True))


def _common(shape, draws, rtol, atol, even=()):
    for name, value in (*shape.items(), ("draws", draws)):
        _integer(name, value, 1)
        if name in even and value % 2:
            raise ValueError(f"{name}: must be even, got {reprlib.repr(value)}")
    return {
        "shape": dict(shape),
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


def _counts(counts, draws, output, cache):
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
        width = 2 if cache is None else 3
        if len(items) != width:
            raise ValueError(f"counts[{i}]: must have {width} items, got {len(items)}")
        failed, non_finite = items[:2]
        _integer(f"counts[{i}].failed", failed, 0)
        _integer(f"counts[{i}].non_finite", non_finite, 0)
        _at_most(f"counts[{i}].failed", failed, *output)
        _at_most(f"counts[{i}].non_finite", non_finite, "failed", failed)
        taken = {"failed": failed, "non_finite": non_finite}
        if cache is not None:
            _integer(f"counts[{i}].cache_differs", items[2], 0)
            _at_most(f"counts[{i}].cache_differs", items[2], *cache)
            taken["cache_differs"] = items[2]
        entries.append(taken)
    return entries


def _at_most(name, value, bound_name, bound):
    if value > bound:
        raise ValueError(
            f"{name}: must be at most {bound_name}, got {reprlib.repr(value)}"
        )
