"""The four answers of ``correctness.check`` between the selection of the backend and the start line.

ADR-0021, ADR-0041 and ADR-0046 fix four answers a call of this tool gives
there for a content of ``instance.json``, and what a check takes from a
content that has none of them. The module renders that part, ahead of the
tool function:

* :data:`KIND_OP_SIGNATURE_NOT_STATED`: the content states no op_signature
  (ADR-0041 decision 4).
* :data:`KIND_OP_SIGNATURE_NOT_COVERED`: the stated op_signature is one the
  contract does not cover (ADR-0041 decision 5).
* :data:`KIND_DRAWS_NOT_STATED`: the content states no number of draws
  (ADR-0046 decision 5).
* :data:`KIND_TOLERANCE_NOT_STATED`: the content states no tolerance
  (ADR-0021 decision 4).
* :data:`KINDS`: the four in the order of the answers, which is the order of
  the row of moment 4 in ADR-0046 decision 8. A content with several of these
  faults has one answer, the first whose condition holds (ADR-0046
  decision 5).
* :func:`admit`: the answer for one content, or the :class:`Admitted` of a
  content that has none of the four: the dimensions (ADR-0041 decision 2),
  the number of draws (ADR-0046 decision 2) and the tolerance (ADR-0021
  decision 4), each as the content states it. For a record whose ``dtype``
  is ``bf16`` it is a :class:`Bf16Admitted`, with the shape members of the
  record's kind (ADR-0041 decision 2 read per kind, ADR-0177 decision 3).
  A covered record is admitted whatever its ``dtype``: the ``step`` of a
  call follows from its point alone, and the rule of ADR-0177 decision 3
  that refused a record whose ``dtype`` was not the one the ``step`` was
  taken for has no object (ADR-0183 decision 2).

Each kind is a tool failure of this tool's own kind and no reserved kind
(ADR-0021 decision 4; ADR-0041 decisions 4 and 5; ADR-0046 decision 5).

Choices that are this module's own and no rule of a record:

* "Covered" reaches :func:`admit` as a callable its caller hands over. The
  reading of the word is ADR-0041 decision 5 and is rendered by the contract
  module of the first case; this module holds no reading of its own and does
  not import that module.
* An ``instance`` whose type is not exactly :class:`hilclaw.instance.Instance`
  and a ``covers`` that is not callable are :class:`TypeError`, raised before
  anything else is done. An answer of ``covers`` whose type is not exactly
  ``bool`` is :class:`TypeError` and is never taken as "covered".
* The values of an ``Instance`` are taken as :func:`hilclaw.instance.read`
  returns them and are not validated again. An ``Instance`` built by hand
  with other values is the caller's.
* The answer for an admitted content is a :class:`typing.NamedTuple`, and
  the field names and their order are this module's. A bf16 record has a
  type of its own, :class:`Bf16Admitted`, so that the :class:`Admitted` of
  an fp32 ``gemm`` record is what it was.
* A bf16 record that ``covers`` answers ``True`` for is answered
  :data:`KIND_OP_SIGNATURE_NOT_COVERED` when no bf16 entry of
  :data:`hilclaw.contract_table.TABLE` has its kind and its ``layout``:
  there is no check for it, whatever the predicate handed over says.
  Through the predicate the registry binds, such a record is refused by
  the predicate first.
* The order of the dimensions of a :class:`Bf16Admitted` is that of the
  parameters of the ``task_contract`` of that entry (ADR-0177 decisions 1
  and 3), read when the module is imported.
* The messages. Each is built when the module is imported, is at most 200
  characters long, starts with the name of the member it is about and shows
  nothing of the content. Nothing may depend on the wording.

What the module does not do: it is no tool and no step and is bound to none.
It is this tool's and reserves no kind. It reads no file and does not say
which read the instance is from: whoever calls says so by calling. It selects
no backend, and it does not come before or after ``no_backend`` or
``not_offered`` by itself: that its answers follow the selection is the
caller's to keep. It does not check that the run is one the records speak of
(ADR-0041 decision 1), and it has no answer of its own for another
accelerator, another kernel language or a kernel that is not of the stated
operation (ADR-0041 decisions 5 and 7): it does not tell such a run apart,
and its answer is the same whatever the hw_profile names. It draws no seed
and builds no check parameters. It appends no line; by the records no kind
of the four is ever the ``failure`` of an end line (ADR-0021 decision 4;
ADR-0041 decisions 4 and 5; ADR-0046 decision 5). It says nothing of what
anybody does after an answer, of whether the start of an instance checks
these members, or of which number of draws or which tolerance is enough for
anything. It keeps nothing between calls. It imports :mod:`inspect`,
:mod:`typing`, :mod:`hilclaw.check_parameters`,
:mod:`hilclaw.contract_table`, :mod:`hilclaw.instance` and
:mod:`hilclaw.tools` and nothing else.
"""

import inspect
import typing

from hilclaw import check_parameters, contract_table, tools
from hilclaw import instance as instances

#: The kind of ADR-0041 decision 4: the content states no op_signature.
KIND_OP_SIGNATURE_NOT_STATED = "op_signature_not_stated"

#: The kind of ADR-0041 decision 5: the stated op_signature is not covered.
KIND_OP_SIGNATURE_NOT_COVERED = "op_signature_not_covered"

#: The kind of ADR-0046 decision 5: the content states no number of draws.
KIND_DRAWS_NOT_STATED = "draws_not_stated"

#: The kind of ADR-0021 decision 4: the content states no tolerance.
KIND_TOLERANCE_NOT_STATED = "tolerance_not_stated"

#: The four kinds in the order of the answers (ADR-0046 decision 8, the row of moment 4). The order is the rule: the first whose condition holds is the answer.
KINDS = (
    KIND_OP_SIGNATURE_NOT_STATED,
    KIND_OP_SIGNATURE_NOT_COVERED,
    KIND_DRAWS_NOT_STATED,
    KIND_TOLERANCE_NOT_STATED,
)

_MESSAGES = {
    KIND_OP_SIGNATURE_NOT_STATED: "op_signature: the content of the instance record states none, and nothing stands in for it",
    KIND_OP_SIGNATURE_NOT_COVERED: "op_signature: the stated record is one this contract has no check for",
    KIND_DRAWS_NOT_STATED: "draws: the content of the instance record states no number of draws, and nothing stands in for it",
    KIND_TOLERANCE_NOT_STATED: "tolerance: the content of the instance record states none, and nothing stands in for it",
}


class Admitted(typing.NamedTuple):
    """What a check that is admitted takes from the content of ``instance.json``.

    - ``m``, ``k``, ``n``: the dimensions of the check, the ``shape.m``,
      ``shape.k`` and ``shape.n`` of the stated op_signature record (ADR-0041
      decision 2).
    - ``draws``: the number of draws of the check, the stated number
      (ADR-0046 decision 2).
    - ``rtol``, ``atol``: those of the stated tolerance (ADR-0021 decision 4).

    As :func:`admit` returns it, each value is the one the instance holds,
    unchanged. No field has a default.
    """

    m: int
    k: int
    n: int
    draws: int
    rtol: float
    atol: float


class Bf16Admitted(typing.NamedTuple):
    """What a check of a bf16 kind that is admitted takes from the content of ``instance.json`` (ADR-0177 decision 3).

    - ``kind``, ``dtype``: those of the stated op_signature record, the
      ``kind`` and the ``dtype`` of the table key of the covering entry.
    - ``dims``: the values of the record's ``shape`` members, a ``tuple`` in
      the order of the parameters of the contract's ``task_contract``
      (``(m, k, n)`` for ``gemm``, ``(m, n)`` for ``rmsnorm``,
      ``elementwise_add`` and ``swiglu``, ``(m, h, d)`` for ``rope``,
      ``(m, l, h, h_kv, d)`` for ``sdpa_kv_cache``).
    - ``draws``, ``rtol``, ``atol``: as in :class:`Admitted`.

    As :func:`admit` returns it, each value is the one the instance holds,
    unchanged. No field has a default.
    """

    kind: str
    dtype: str
    dims: tuple
    draws: int
    rtol: float
    atol: float


def admit(instance, *, covers):
    """Return the :class:`Admitted` of ``instance``, or raise the one answer it has.

    - ``instance``: the :class:`hilclaw.instance.Instance` that one
      :func:`hilclaw.instance.read` returned for the run of the call. Which
      read that is is the caller's statement and is not checked.
    - ``covers``: the predicate of ADR-0041 decision 5, a callable that is
      handed an op_signature record and returns ``True`` when the contract
      covers it and ``False`` when it does not.

    No parameter has a default, and ``covers`` is given by name. First,
    :class:`TypeError` is raised when the type of ``instance`` is not exactly
    ``Instance``, and then when ``covers`` is not callable.

    The answers, the first whose condition holds and no other (ADR-0046
    decisions 5 and 8). Each of the four is a
    :class:`hilclaw.tools.ToolFailure` that is raised:

    1. ``instance.op_signature`` is ``None``:
       :data:`KIND_OP_SIGNATURE_NOT_STATED`. ``covers`` is not called.
    2. ``covers`` returns ``False`` for the stated record:
       :data:`KIND_OP_SIGNATURE_NOT_COVERED`. ``covers`` is called once, with
       the record object the instance holds. What it raises passes through
       unchanged, and :class:`TypeError` is raised when what it returns is
       not exactly a ``bool``. The same kind is raised for a record whose
       ``dtype`` is ``bf16`` and for which there is no check (see the module
       docstring).
    3. ``instance.draws`` is ``None``: :data:`KIND_DRAWS_NOT_STATED`.
    4. ``instance.tolerance`` is ``None``: :data:`KIND_TOLERANCE_NOT_STATED`.
    5. Otherwise the :class:`Admitted` is returned, or for a record whose
       ``dtype`` is ``bf16`` the :class:`Bf16Admitted`.

    Nothing else of the instance is looked at: not ``hw_profile``,
    ``hw_profile_key``, ``others`` or the key of the op_signature. Of the
    record this function itself reads, after ``covers`` answered ``True``,
    the ``dtype``, for a bf16 record the ``kind`` and the ``layout``, and the
    ``shape`` only for an admitted content: ``m``, ``k`` and ``n`` for a
    record of another ``dtype``, as before, and the members of its kind for a
    bf16 record. What ``covers`` reads of it is that callable's. No value is
    compared with a limit, and none is derived, rounded or replaced.

    ``instance`` is not modified or kept, and no file is read or written.
    """
    if type(instance) is not instances.Instance:
        raise TypeError("instance: must be exactly a hilclaw.instance.Instance")
    if not callable(covers):
        raise TypeError("covers: must be callable")
    return _admit(instance, covers)


def _admit(instance, covers):
    stated = instance.op_signature
    if stated is None:
        raise _failure(KIND_OP_SIGNATURE_NOT_STATED)
    record = stated.record
    covered = covers(record)
    if type(covered) is not bool:
        raise TypeError("covers: must return exactly a bool")
    if not covered:
        raise _failure(KIND_OP_SIGNATURE_NOT_COVERED)
    bf16 = record["dtype"] == check_parameters.BF16
    names = _BF16_NAMES.get((record["kind"], record["layout"])) if bf16 else None
    if bf16 and names is None:
        raise _failure(KIND_OP_SIGNATURE_NOT_COVERED)
    if instance.draws is None:
        raise _failure(KIND_DRAWS_NOT_STATED)
    tolerance = instance.tolerance
    if tolerance is None:
        raise _failure(KIND_TOLERANCE_NOT_STATED)
    shape = record["shape"]
    if bf16:
        return Bf16Admitted(
            record["kind"],
            record["dtype"],
            tuple(shape[name] for name in names),
            instance.draws,
            tolerance.rtol,
            tolerance.atol,
        )
    return Admitted(
        shape["m"],
        shape["k"],
        shape["n"],
        instance.draws,
        tolerance.rtol,
        tolerance.atol,
    )


_BF16_NAMES = {
    (contract.KIND, contract.LAYOUT): tuple(
        inspect.signature(contract.task_contract).parameters
    )
    for contract in (entry.contract for entry in contract_table.TABLE.values())
    if contract.DTYPE == check_parameters.BF16
}


def _failure(kind):
    return tools.ToolFailure(kind, _MESSAGES[kind])
