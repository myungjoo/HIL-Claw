"""The v2 result object of a call of ``sim.run`` or ``board.run`` (ADR-0183 decision 4).

``ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`` decision 4
fixes the members of a v2 result of either run tool and closes the member
list: a result has ``outcome``, ``condition``, ``contract_key``, ``shape``,
``n_max``, ``sample_form``, ``unit``, ``resolution``, ``intervals``,
``memory_bytes``, ``ceiling`` and ``bound``, and no other. One list serves
both tools and every contract of :data:`hilclaw.contract_table.TABLE`.
``outcome``, ``condition``, ``n_max``, ``sample_form``, ``memory_bytes``,
``ceiling`` and ``bound`` are those of ADR-0063 (decisions 2, 3, 5, 6 and
7); ``resolution`` and ``intervals`` are its ``resolution_ns`` and
``intervals_ns`` renamed (ADR-0063 decision 4), in the unit ``unit`` states.
This module renders that table as plain Python values:

* :data:`CONVERGED`, :data:`NOT_CONVERGED` and :data:`BROKEN`: the three
  values of ``outcome``.
* :data:`CONDITIONS`: the seven values of ``condition``, in the order of
  ADR-0063 decision 3.
* :data:`SAMPLE_FORMS`: the two values of ``sample_form``.
* :data:`UNITS`: the values of ``unit``, ``"ns"`` alone (HQ-0078 ⑤).
* :data:`WITHIN`, :data:`OVER`, :data:`NOT_JUDGED` and :data:`NOT_STATED`: the
  four values of ``ceiling``.
* :func:`completed`: the result of a completed run of a covering entry, from
  its outcome, its unit, resolution and intervals and its figure or the
  absence of one.
* :func:`broken`: the result of a broken run of a covering entry, from its
  condition. It holds no ``unit``, ``resolution``, ``intervals`` or
  ``memory_bytes`` (ADR-0183 decision 6).

A result is a new ``dict`` that is one JSON object in the strict sense
(ADR-0183 decision 1). No member holds ``None``: a member that does not apply
is left out.

Choices that are this module's own and no rule of a record:

* The contract is handed over as its :class:`hilclaw.contract_table.Entry`,
  any entry of the table whether ``timed`` or not, and the dimensions as a
  ``tuple`` in the order of the parameters of its ``task_contract``.
* ``ceiling`` is derived and is no argument, so no call can state a verdict
  its figure contradicts: :data:`NOT_STATED` when ``bound`` is ``None``,
  otherwise the verdict of :func:`hilclaw.harness.memory_ceiling.verdict` for
  the figure (none for a broken run) and ``bound``.
* The order of the members in a returned ``dict`` is that of the table;
  within ``contract_key`` ``kind``, ``dtype``, ``layout``; within ``shape``
  the order of the parameters of ``task_contract``.
* ``intervals`` may be empty: the table states no length, and no relation
  between the intervals, ``n_max`` and ``outcome`` is checked here.
* An argument the table does not admit is refused with :class:`TypeError` when
  it is of a type that is not accepted and with :class:`ValueError` when it is
  of an accepted type but not an admitted value. The message starts with the
  name of the parameter (a dimension is named by its parameter name).
  Nothing is returned then.
* An ``int`` that this interpreter does not convert to decimal text (the limit
  of ``sys.get_int_max_str_digits``) is refused with :class:`ValueError`,
  although the table states no upper bound for ``resolution``, ``intervals``
  and ``memory_bytes``: this interpreter does not write an object that holds
  one as JSON text.

What the module does not do: it judges no report and replays no stopping
rule; it computes no summary. It maps nothing from a type of the harness or
from what an operation returns. It is no tool, is registered nowhere and
checks no stored result against the table. It decides no admission: whether
a tool times a contract is :func:`hilclaw.contract_table.run_covers`'s. It
gives no default of any value and admits no ``memory_ceiling`` constraint. It
reads and writes no file, starts no process, keeps nothing between calls and
has no command-line entry.
"""

import inspect
import reprlib

from hilclaw import contract_table
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
UNITS = ("ns",)
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
    entry,
    dims,
    *,
    unit,
    resolution,
    intervals,
    memory_bytes,
    n_max,
    sample_form,
    bound,
):
    """Return the v2 result of a completed run of ``entry``'s contract whose report ended in ``outcome``.

    The result is a new ``dict`` with exactly the members ``outcome``,
    ``contract_key``, ``shape``, ``n_max``, ``sample_form`` (as in
    :func:`broken`), ``unit``, ``resolution``, ``intervals`` (a new ``list``
    of the entries of the argument, in its order), ``memory_bytes`` when it
    is not ``None``, ``ceiling`` and ``bound`` when it is not ``None``, in
    that order (ADR-0183 decision 4). It has no ``condition``. ``ceiling`` is
    :data:`NOT_STATED` when ``bound`` is ``None``, whether or not there is a
    figure; otherwise :data:`NOT_JUDGED` when ``memory_bytes`` is ``None``,
    :data:`WITHIN` when ``memory_bytes <= bound`` and :data:`OVER` when
    ``memory_bytes > bound`` (ADR-0063 decision 7, after ADR-0052
    decision 5).

    ``outcome``, ``entry`` and ``dims`` may be given by position; the other
    parameters are keyword-only. No parameter has a default.

    * ``outcome`` is exactly a ``str``, :data:`CONVERGED` or
      :data:`NOT_CONVERGED`.
    * ``entry``, ``dims``, ``n_max``, ``sample_form`` and ``bound`` follow the
      rules of :func:`broken`.
    * ``unit`` is exactly a ``str`` that is one of :data:`UNITS`.
    * ``resolution`` is exactly an ``int`` of at least 0, with no upper bound.
    * ``intervals`` is exactly a ``list`` or a ``tuple`` whose entries are
      each exactly an ``int`` of at least 1, with no upper bound.
    * ``memory_bytes`` is ``None`` (the run yielded no figure) or exactly an
      ``int`` of at least 1, with no upper bound.

    Checked in the order ``outcome``, ``entry``, ``dims``, ``n_max``,
    ``sample_form``, ``bound``, ``unit``, ``resolution``, ``intervals``,
    ``memory_bytes``. ``bool`` and other subclasses of ``int`` or ``str`` are
    refused, as is a member of an enumeration that stands for a value
    elsewhere. Raises :class:`TypeError` for an argument of another type and
    :class:`ValueError` for another value of an accepted type, as the module
    docstring says; the message names the parameter, and for an interval the
    entry (``intervals[2]``). No argument is modified or kept, and the result
    shares no mutable object with an argument.
    """
    _choice("outcome", outcome, (CONVERGED, NOT_CONVERGED))
    common = _common(entry, dims, n_max, sample_form, bound)
    _choice("unit", unit, UNITS)
    _integer("resolution", resolution, 0)
    taken = _intervals(intervals)
    if memory_bytes is not None:
        _integer("memory_bytes", memory_bytes, 1)
    result = {
        "outcome": outcome,
        **common,
        "unit": unit,
        "resolution": resolution,
        "intervals": taken,
    }
    if memory_bytes is not None:
        result["memory_bytes"] = memory_bytes
    return _with_ceiling(result, memory_bytes, bound)


def broken(condition, entry, dims, *, n_max, sample_form, bound):
    """Return the v2 result of a broken run of ``entry``'s contract that failed ``condition`` first.

    The result is a new ``dict`` with exactly the members ``outcome``
    (:data:`BROKEN`), ``condition``, ``contract_key``, ``shape``, ``n_max``,
    ``sample_form``, ``ceiling`` and ``bound`` when it is not ``None``, in
    that order. It has no ``unit``, ``resolution``, ``intervals`` or
    ``memory_bytes``, and the function takes none (ADR-0183 decisions 4
    and 6). ``ceiling`` is :data:`NOT_STATED` when ``bound`` is ``None`` and
    :data:`NOT_JUDGED` otherwise (ADR-0063 decision 7).

    ``condition``, ``entry`` and ``dims`` may be given by position; the other
    parameters are keyword-only. No parameter has a default.

    * ``condition`` is exactly a ``str`` that is one of :data:`CONDITIONS`.
    * ``entry`` is exactly a :class:`hilclaw.contract_table.Entry` that
      equals, as a tuple, an entry of :data:`hilclaw.contract_table.TABLE`,
      ``timed`` or not; anything else is refused, a plain ``tuple``
      included. ``contract_key`` is a new ``dict`` of its contract's
      ``kind``, ``dtype`` and ``layout``.
    * ``dims`` is exactly a ``tuple`` with one item per parameter of the
      contract's ``task_contract``, in their order, each exactly an ``int``
      with 1 <= value <= 2**53 - 1 (integers of ADR-0001), the message about
      an item naming its parameter. A shape for which ``task_contract``
      gives no ``task.contract`` (for example an odd ``d`` for ``rope``) is
      refused with :class:`ValueError` and a message that starts with
      ``dims: ``. ``shape`` is a new ``dict`` that pairs the parameter names
      with ``dims``, in that order: ``m``, ``k``, ``n`` for ``gemm``.
    * ``n_max`` is exactly an ``int`` with 5 <= value <= 2**53 - 1.
    * ``sample_form`` is exactly a ``str`` that is one of
      :data:`SAMPLE_FORMS`.
    * ``bound`` is ``None`` (no ceiling stated) or exactly an ``int`` with
      0 <= value <= 2**53 - 1 (ADR-0050 decision 4).

    Checked in the order of the parameters. Raises :class:`TypeError` and
    :class:`ValueError` as :func:`completed` does; a ``str`` that is none of
    the seven values is a :class:`ValueError`.
    """
    _choice("condition", condition, CONDITIONS)
    result = {
        "outcome": BROKEN,
        "condition": condition,
        **_common(entry, dims, n_max, sample_form, bound),
    }
    return _with_ceiling(result, None, bound)


def _common(entry, dims, n_max, sample_form, bound):
    key, shape = _contract(entry, dims)
    _integer("n_max", n_max, 5, _INTEGER_MAX)
    _choice("sample_form", sample_form, SAMPLE_FORMS)
    if bound is not None:
        _integer("bound", bound, 0, _INTEGER_MAX)
    return {
        "contract_key": key,
        "shape": shape,
        "n_max": n_max,
        "sample_form": sample_form,
    }


def _contract(entry, dims):
    if type(entry) is not contract_table.Entry:
        name = type(entry).__name__
        raise TypeError(f"entry: must be an Entry of contract_table.TABLE, got {name}")
    if entry not in tuple(contract_table.TABLE.values()):
        raise ValueError(
            f"entry: must be an entry of contract_table.TABLE, got {reprlib.repr(entry)}"
        )
    contract = entry.contract
    names = tuple(inspect.signature(contract.task_contract).parameters)
    if type(dims) is not tuple:
        raise TypeError(f"dims: must be a tuple, got {type(dims).__name__}")
    if len(dims) != len(names):
        raise ValueError(
            f"dims: must have {len(names)} items for {contract.KIND}, got {len(dims)}"
        )
    for name, value in zip(names, dims, strict=True):
        _integer(name, value, 1, _INTEGER_MAX)
    try:
        contract.task_contract(*dims)
    except ValueError as error:
        raise ValueError(f"dims: {error}") from None
    key = {"kind": contract.KIND, "dtype": contract.DTYPE, "layout": contract.LAYOUT}
    return key, dict(zip(names, dims, strict=True))


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


def _intervals(intervals):
    if type(intervals) not in (list, tuple):
        raise TypeError(
            f"intervals: must be a list or a tuple, got {type(intervals).__name__}"
        )
    for i, interval in enumerate(intervals):
        _integer(f"intervals[{i}]", interval, 1)
    return list(intervals)
