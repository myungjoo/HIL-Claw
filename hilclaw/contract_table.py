"""The one table of the kernel contracts a run may be about (ADR-0177 decisions 1 and 2).

``ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`` makes this
module the one place in the package that lists the operational contracts an
instance, a spec and a run tool may be about: the fp32 ``gemm`` contract of
ADR-0008 (:mod:`hilclaw.gemm_contract`) and the six bf16 contracts of
ADR-0156 and ADR-0158 to ADR-0162 (the ``hilclaw.*_bf16_contract`` modules).
Each entry is keyed by the ``kind``, ``dtype``, ``layout`` and ``language``
of its contract and holds the contract module itself, so no constant of a
contract is copied here, and two flags that say which tools serve it after
the slices landed so far (ADR-0177 decision 2):

* ``checked``: ``correctness.check`` judges a run of the contract;
* ``timed``: ``sim.run`` and ``board.run`` time a kernel of it.

The predicates, each exactly a ``bool``, and the place that binds each
(ADR-0177 decision 2):

* :func:`covers`: some entry covers the record - ``spec.write``;
* :func:`check_covers`: a ``checked`` entry covers it - ``correctness.check``;
* :func:`run_covers`: a ``timed`` entry covers it - ``sim.run`` and
  ``board.run``;
* :func:`start_covers`: an entry that is both ``checked`` and ``timed``
  covers it - the instance start, so that it admits no contract a tool round
  0 calls refuses (ADR-0177 decision 2; ADR-0138, ADR-0142).

A record is covered by an entry when the entry's ``covers`` (the predicate
of ADR-0041 decision 5 read per contract) answers ``True`` for it; a record
that matches no entry is not covered. The record states no language
(ADR-0031 decision 2), so the table holds at most one entry per ``kind``,
``dtype`` and ``layout`` (ADR-0177 decision 1). :func:`entry` returns the
covering entry, and :func:`task_contract` the ``task.contract`` of a covered
record's shape under it.

What the module does not do: it builds no spec, judges and times nothing,
reads and writes no file, starts no process, keeps nothing between calls
and has no command-line entry. It imports no NumPy.
"""

import collections
import inspect
import types

from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    keys,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)

#: One entry of :data:`TABLE`: the contract module and the two flags.
Entry = collections.namedtuple("Entry", ("contract", "checked", "timed"))

_ENTRIES = (
    Entry(gemm_contract, checked=True, timed=True),
    Entry(gemm_bf16_contract, checked=True, timed=True),
    Entry(rmsnorm_bf16_contract, checked=True, timed=True),
    Entry(elementwise_add_bf16_contract, checked=True, timed=True),
    Entry(swiglu_bf16_contract, checked=True, timed=True),
    Entry(rope_bf16_contract, checked=True, timed=True),
    Entry(sdpa_kv_cache_bf16_contract, checked=True, timed=True),
)

#: The table: ``(kind, dtype, layout, language)`` to :class:`Entry`, in the order of ADR-0177 decision 1.
TABLE = types.MappingProxyType(
    {
        (e.contract.KIND, e.contract.DTYPE, e.contract.LAYOUT, e.contract.LANGUAGE): e
        for e in _ENTRIES
    }
)


def entry(record):
    """Return the :class:`Entry` of :data:`TABLE` that covers the op_signature ``record``, or ``None``.

    The entries are asked in the order of :data:`TABLE`, each through its
    contract's ``covers``, and the first that answers ``True`` is returned;
    ``None`` says that no entry covers the record. ``record`` is first
    validated by :func:`hilclaw.keys.op_signature_key`, and
    :class:`hilclaw.keys.InvalidRecordError` is raised as that function raises
    it, a ``kind`` it does not know included. ``record`` is not modified.
    """
    return _first(record, lambda e: True)


def covers(record):
    """Return whether any entry of :data:`TABLE` covers the op_signature ``record``.

    The predicate of ``spec.write`` (ADR-0177 decision 2). Raises as
    :func:`entry` raises.
    """
    return entry(record) is not None


def check_covers(record):
    """Return whether a ``checked`` entry covers the op_signature ``record``.

    The predicate of ``correctness.check`` (ADR-0177 decision 2). Only the
    ``checked`` entries are asked. Raises as :func:`entry` raises.
    """
    return _first(record, lambda e: e.checked) is not None


def run_covers(record):
    """Return whether a ``timed`` entry covers the op_signature ``record``.

    The predicate of ``sim.run`` and ``board.run`` (ADR-0177 decision 2).
    Only the ``timed`` entries are asked. Raises as :func:`entry` raises.
    """
    return _first(record, lambda e: e.timed) is not None


def start_covers(record):
    """Return whether an entry that is both ``checked`` and ``timed`` covers the op_signature ``record``.

    The predicate of the instance start (ADR-0177 decision 2): a run the
    start admits is admitted by every tool its round 0 calls. Only those
    entries are asked. Raises as :func:`entry` raises.
    """
    return _first(record, lambda e: e.checked and e.timed) is not None


def task_contract(record):
    """Return the ``task.contract`` object of the covered op_signature ``record``.

    The result is what the covering entry's ``task_contract`` returns for the
    members of ``record["shape"]``, passed in the order of that function's
    parameters (ADR-0177 decision 1). Raises :class:`ValueError` when no entry
    covers a valid ``record``, and otherwise as :func:`entry` raises.
    """
    found = entry(record)
    if found is None:
        raise ValueError("op_signature: the record is not covered by any contract")
    function = found.contract.task_contract
    shape = record["shape"]
    return function(*(shape[name] for name in inspect.signature(function).parameters))


def _first(record, wanted):
    keys.op_signature_key(record)
    for candidate in TABLE.values():
        if wanted(candidate) and candidate.contract.covers(record):
            return candidate
    return None
