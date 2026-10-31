"""The result object of a check of ``correctness.check`` (ADR-0183 decisions 3 and 6).

``ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`` fixes the
v2 result of the tool, for any entry of :data:`hilclaw.contract_table.TABLE`;
every result of the tool is one (:mod:`hilclaw.check_answer`).
``ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md``
gives the values of ``outcome`` (decision 2) and of ``condition`` (decision 3)
and the form of ``tolerance`` (decision 5). This module renders them as plain
Python values:

* :data:`PASS`, :data:`FAIL` and :data:`BROKEN`: the three values of
  ``outcome``.
* :data:`CONDITIONS`: the six values of ``condition``, in the order of
  ADR-0042 decision 3 as ADR-0060 decision 4 amends it.
* :data:`BIT_EXACT`: the output operands judged bit for bit, keyed by the
  ``(kind, dtype, layout)`` of their contract; every other output operand
  is judged by tolerance.
* ``output_operands(entry, dims)``: the names of the output and inout
  operands of the contract of ``entry`` for ``dims``, in contract order.
* ``v2_completed(entry, dims, *, draws, rtol, atol, counts)``: the result
  of a completed run, ``counts`` holding the per-draw entries of each
  output operand by its name.
* ``v2_broken(condition, entry, dims, *, draws, rtol, atol)``: the result
  of a broken run.

A result has the members ``outcome``, ``condition``, ``contract_key``,
``shape``, ``draws``, ``tolerance`` and ``counts`` in that order, a member
that does not apply left out.

A result is a new ``dict`` that is one JSON object in the strict sense
(ADR-0042 decision 1). No member holds ``None``.

Choices that are this module's own and no rule of the record:

* ``rtol`` and ``atol`` are returned as the ``float`` of the argument, so the
  number in a result is the binary64 value itself (ADR-0042 decision 5 leaves
  the spelling of the literal open). A negative zero is not negative; it is
  returned as it is.
* An argument the record does not admit is refused with :class:`TypeError` when
  it is of a type that is not accepted and with :class:`ValueError` when it is
  of an accepted type but not an admitted value. The message starts with the
  name of the parameter. Nothing is returned then.
* An ``int`` that this interpreter does not convert to decimal text (the limit
  of ``sys.get_int_max_str_digits``) is refused with :class:`ValueError`,
  although the record states no upper bound: this interpreter does not write
  an object that holds one as JSON text.

What the module does not do: it judges nothing and compares no output with a
reference. It maps nothing from what an operation returns, and it reads no
field of a type of the harness. It is no tool and is bound to none, and it
checks no stored result against the table. It gives no default of any value:
no number of draws, no tolerance and no dimension. It reads and writes no file,
starts no process, keeps nothing between calls and has no command-line entry.
It imports ``inspect``, ``math``, ``reprlib`` and ``types`` of the standard
library and :mod:`hilclaw.contract_table`, whose entries' ``task_contract`` parameters
name the shape members, and nothing else; it reads the table and changes
nothing in it.
"""

import inspect
import math
import reprlib
import types

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
_EVEN = {"rope": ("d",)}
_SDPA_KEY = ("sdpa_kv_cache", "bf16", "row_major")
#: Output operands judged bit for bit, by ``(kind, dtype, layout)`` (ADR-0183 decision 3).
BIT_EXACT = types.MappingProxyType({_SDPA_KEY: ("cache_k", "cache_v")})
_ALLOCATION = {
    _SDPA_KEY: (
        "(l + 2 * m) * h_kv * d",
        lambda shape: (shape["l"] + 2 * shape["m"]) * shape["h_kv"] * shape["d"],
    )
}


def _condition(condition):
    if type(condition) is not str:
        raise TypeError(f"condition: must be a str, got {type(condition).__name__}")
    if condition not in CONDITIONS:
        shown = reprlib.repr(condition)
        raise ValueError(f"condition: must be one of {CONDITIONS}, got {shown}")


def _common(shape, draws, rtol, atol):
    _integer("draws", draws, 1)
    return {
        "shape": shape,
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


def _at_most(name, value, bound_name, bound):
    if value > bound:
        raise ValueError(
            f"{name}: must be at most {bound_name}, got {reprlib.repr(value)}"
        )


def output_operands(entry, dims):
    """Return the names of the output and inout operands of ``entry``'s contract for ``dims``.

    ``entry`` is exactly a :class:`hilclaw.contract_table.Entry` that equals,
    as a tuple, an entry of :data:`hilclaw.contract_table.TABLE`; anything
    else is refused, a plain ``tuple`` and an ``Entry`` of another contract
    or of other flag values included. ``dims`` is
    exactly a ``tuple`` with one item per parameter of the contract's
    ``task_contract``, in their order, each exactly an ``int`` of at least 1
    (a message about an item names its parameter) and ``d`` even for
    ``rope`` (ADR-0161 decision 11); a shape for which ``task_contract``
    gives no ``task.contract`` (for example ``l < m`` for ``sdpa_kv_cache``)
    is refused with :class:`ValueError` and a message that starts with
    ``dims: ``.

    The result is a new ``tuple`` of the ``name`` of each operand of
    ``task_contract(*dims)`` whose ``role`` is ``output`` or ``inout``, in
    the order of the contract (ADR-0183 decision 3): ``("c",)`` for
    ``gemm`` and ``elementwise_add``, ``("y",)`` for ``rmsnorm``,
    ``("out",)`` for ``swiglu`` and ``rope``, and ``("cache_k", "cache_v",
    "out")`` for ``sdpa_kv_cache``. Checked in the order ``entry``,
    ``dims``; raises :class:`TypeError` and :class:`ValueError` as the
    module docstring says.
    """
    return tuple(_contract(entry, dims)[2])


def v2_completed(entry, dims, *, draws, rtol, atol, counts):
    """Return the v2 result of a completed run of a check of ``entry``'s contract.

    The result is a new ``dict`` with exactly the members ``outcome``,
    ``contract_key`` (a new ``dict`` of the contract's ``kind``, ``dtype``
    and ``layout``, no ``language``), ``shape`` (a new ``dict`` that pairs
    the parameters of ``task_contract`` with ``dims``), ``draws``,
    ``tolerance`` (a new ``dict`` ``{"rtol": float(rtol), "atol":
    float(atol)}``) and ``counts``, in that order,
    and no ``condition`` (ADR-0183 decision 3). ``outcome`` is :data:`PASS`
    when every ``failed`` and every ``differs`` of every draw is 0, and
    :data:`FAIL` otherwise.

    ``entry`` and ``dims`` follow :func:`output_operands`. ``draws``,
    ``rtol``, ``atol`` and ``counts`` are keyword-only and none has a
    default. ``draws`` is exactly an ``int`` (``bool`` and other subclasses
    are refused) of at least 1. ``rtol`` and ``atol`` are each exactly an
    ``int`` or a ``float``, finite, not negative and, for an ``int``, within
    what a ``float`` holds. ``counts`` is exactly a ``dict`` whose keys are
    exactly the names :func:`output_operands` returns; each value is
    exactly a ``list`` or a ``tuple`` of ``draws`` entries in draw order.
    For an operand of :data:`BIT_EXACT` an entry is ``differs``, exactly an
    ``int`` of at least 0 and at most the number of elements of its
    allocation, ``(l + 2 * m) * h_kv * d`` for the caches of
    ``sdpa_kv_cache`` (ADR-0165 decisions 5 and 8). For any other operand
    an entry is a ``tuple`` of two items ``(failed, non_finite)`` (a
    subclass such as :class:`hilclaw.harness.verification_arrays.Counts` is
    read as the tuple it is), each exactly an ``int``, with ``0 <=
    non_finite <= failed <=`` the number of elements of the operand, the
    product of its ``shape`` in ``task_contract(*dims)``. In the result
    ``counts`` is a new ``dict`` in the order of :func:`output_operands`,
    each member a new ``list`` of new ``dict`` entries ``{"differs": ...}``
    or ``{"failed": ..., "non_finite": ...}``.

    Checked in the order ``entry``, ``dims``, ``draws``, ``rtol``, ``atol``,
    ``counts``; a message about a count names the operand and the draw
    (``counts.out[1].failed``). Raises :class:`TypeError` and
    :class:`ValueError` as the module docstring says. No argument is
    modified or kept, and the result shares no mutable object with them.
    """
    key, common, operands = _v2_common(entry, dims, draws, rtol, atol)
    taken = _v2_counts(counts, common, key, operands)
    failing = any(
        item.get("failed") or item.get("differs")
        for entries in taken.values()
        for item in entries
    )
    outcome = FAIL if failing else PASS
    return {"outcome": outcome, "contract_key": key, **common, "counts": taken}


def v2_broken(condition, entry, dims, *, draws, rtol, atol):
    """Return the v2 result of a broken run of a check of ``entry``'s contract.

    The result is a new ``dict`` with exactly the members ``outcome``
    (:data:`BROKEN`), ``condition``, ``contract_key``, ``shape``, ``draws``
    and ``tolerance``, the last four as in :func:`v2_completed`, and no
    ``counts`` (ADR-0183 decision 6). ``condition`` is exactly a ``str``
    that is one of :data:`CONDITIONS`: a value of another type is a
    :class:`TypeError`, a member of an enumeration that stands for a condition
    elsewhere included, and a ``str`` that is none of the six a
    :class:`ValueError`. It is checked first, then the other arguments in the
    order of :func:`v2_completed`.
    """
    _condition(condition)
    key, common, _ = _v2_common(entry, dims, draws, rtol, atol)
    return {"outcome": BROKEN, "condition": condition, "contract_key": key, **common}


def _contract(entry, dims):
    if type(entry) is not contract_table.Entry:
        name = type(entry).__name__
        raise TypeError(f"entry: must be an Entry of contract_table.TABLE, got {name}")
    if entry not in tuple(contract_table.TABLE.values()):
        shown = reprlib.repr(entry)
        raise ValueError(
            f"entry: must be an entry of contract_table.TABLE, got {shown}"
        )
    contract = entry.contract
    names = tuple(inspect.signature(contract.task_contract).parameters)
    if type(dims) is not tuple:
        raise TypeError(f"dims: must be a tuple, got {type(dims).__name__}")
    if len(dims) != len(names):
        raise ValueError(
            f"dims: must have {len(names)} items for {contract.KIND}, got {len(dims)}"
        )
    shape = dict(zip(names, dims, strict=True))
    for name, value in shape.items():
        _integer(name, value, 1)
        if name in _EVEN.get(contract.KIND, ()) and value % 2:
            raise ValueError(f"{name}: must be even, got {reprlib.repr(value)}")
    try:
        task = contract.task_contract(*dims)
    except ValueError as error:
        raise ValueError(f"dims: {error}") from None
    operands = {
        operand["name"]: math.prod(operand["shape"])
        for operand in task["operands"]
        if operand["role"] in ("output", "inout")
    }
    return contract, shape, operands


def _v2_common(entry, dims, draws, rtol, atol):
    contract, shape, operands = _contract(entry, dims)
    key = {"kind": contract.KIND, "dtype": contract.DTYPE, "layout": contract.LAYOUT}
    return key, _common(shape, draws, rtol, atol), operands


def _v2_counts(counts, common, key, operands):
    if type(counts) is not dict:
        raise TypeError(f"counts: must be a dict, got {type(counts).__name__}")
    for name in operands:
        if name not in counts:
            raise ValueError(f"counts: must have the operand {name!r}")
    for name in counts:
        if name not in operands:
            raise ValueError(f"counts: has no output operand {reprlib.repr(name)}")
    triple = tuple(key.values())
    exact = BIT_EXACT.get(triple, ())
    draws = common["draws"]
    taken = {}
    for name, size in operands.items():
        entries = counts[name]
        label = f"counts.{name}"
        if type(entries) not in (list, tuple):
            kind = type(entries).__name__
            raise TypeError(f"{label}: must be a list or a tuple, got {kind}")
        if len(entries) != draws:
            raise ValueError(f"{label}: must have {draws} entries, got {len(entries)}")
        if name in exact:
            bound_name, allocation = _ALLOCATION[triple]
            bound = allocation(common["shape"])
            taken[name] = [
                _differs(f"{label}[{i}]", entry, bound_name, bound)
                for i, entry in enumerate(entries)
            ]
        else:
            bound_name = f"the {size} elements of {name}"
            taken[name] = [
                _judged(f"{label}[{i}]", entry, bound_name, size)
                for i, entry in enumerate(entries)
            ]
    return taken


def _differs(label, entry, bound_name, bound):
    _integer(f"{label}.differs", entry, 0)
    _at_most(f"{label}.differs", entry, bound_name, bound)
    return {"differs": entry}


def _judged(label, entry, bound_name, bound):
    if not isinstance(entry, tuple):
        raise TypeError(f"{label}: must be a tuple, got {type(entry).__name__}")
    items = tuple(tuple.__iter__(entry))
    if len(items) != 2:
        raise ValueError(f"{label}: must have 2 items, got {len(items)}")
    failed, non_finite = items
    _integer(f"{label}.failed", failed, 0)
    _integer(f"{label}.non_finite", non_finite, 0)
    _at_most(f"{label}.failed", failed, bound_name, bound)
    _at_most(f"{label}.non_finite", non_finite, "failed", failed)
    return {"failed": failed, "non_finite": non_finite}
