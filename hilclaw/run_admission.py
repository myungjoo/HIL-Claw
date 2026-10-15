"""The answers of ``sim.run`` and ``board.run`` for the members of a run, and what an admitted run gives.

``ARCHITECTURE/decisions/ADR-0067-od18-run-tools-admission-kinds.md`` fixes
what a call of either run tool answers for a valid ``instance.json`` that
states no op_signature, one the run tools' contract does not cover, or no
``n_max``, and the order of every answer of moment 4; a decision cited by its
number alone is one of that record. ADR-0061 decisions 3, 4 and 6 fix what
the tool function takes from the read of moment 4. The module renders steps
3 to 7 of the order of decision 5, ahead of any tool function:

* :data:`KIND_OP_SIGNATURE_NOT_STATED`: the content states no op_signature
  (decision 2).
* :data:`KIND_OP_SIGNATURE_NOT_COVERED`: the stated op_signature is one the
  run tools' contract does not cover (decision 3).
* :data:`KIND_N_MAX_NOT_STATED`: the content states no ``n_max``
  (decision 4). No bound stands in for it.
* :data:`KINDS`: the five answers of steps 3 to 7 in their order, the two of
  :mod:`hilclaw.run_objective` (ADR-0061 decision 4) at steps 5 and 6. A
  content with several of these faults has one answer, the first whose
  condition holds (decision 5).
* :func:`admit`: the answer for one content, or the :class:`Admitted` of a
  content that has none of the five: the dimensions and ``n_max``
  (ADR-0061 decision 3), the sample form (ADR-0061 decision 4) and the
  ``bound`` (ADR-0061 decision 6), each as the content states it.

Each of the three kinds is a tool failure of the run tools' contract and no
reserved kind (decisions 2 to 4). The two op_signature kinds have the
spelling of those of ``correctness.check`` on purpose (decision 6).

Choices that are this module's own and no rule of a record:

* The two op_signature kinds are defined here and not imported from
  :mod:`hilclaw.check_admission`: they are the run tools' kinds, and
  this module does not depend on the check's.
* "Covered" reaches :func:`admit` as a callable its caller hands over, the
  predicate of ADR-0041 decision 5 (decision 3); this module holds no
  reading of its own.
* An ``instance`` whose type is not exactly :class:`hilclaw.instance.Instance`
  and a ``covers`` that is not callable are :class:`TypeError`, raised before
  anything else is done. An answer of ``covers`` whose type is not exactly
  ``bool`` is :class:`TypeError` and is never taken as "covered".
* Steps 5 and 6 are :func:`hilclaw.run_objective.admit`, whose answers and
  errors pass through unchanged.
* The values of an ``Instance`` are taken as :func:`hilclaw.instance.read`
  returns them and are not validated again.
* The answer for an admitted content is a :class:`typing.NamedTuple`, and
  the field names and their order are this module's. It holds no seed and
  is no :class:`hilclaw.run_parameters.TimingParameters`.
* The messages. Each is built when the module is imported, is at most 200
  characters long, starts with the name of the member it is about and shows
  nothing of the content. Nothing may depend on the wording.

What the module does not do: it is no tool and no step, registers nothing
and reads no file. It selects no backend: steps 1 and 2 of decision 5 (the
``run_file_*`` kinds, ``no_backend`` and ``not_offered``) are the caller's
to keep before it. It draws no seed: the draw comes after its last answer
and is the caller's. It appends no line; by the records no kind it answers
is ever the ``failure`` of an end line (decision 6). It substitutes no bound
and no dimensions. It keeps nothing between calls and reserves no kind. It
imports :mod:`typing`, :mod:`hilclaw.instance`, :mod:`hilclaw.run_objective`
and :mod:`hilclaw.tools` and nothing else.
"""

import typing

from hilclaw import instance as instances
from hilclaw import run_objective, tools

#: The kind of decision 2: the content states no op_signature. The spelling of ``correctness.check``'s kind.
KIND_OP_SIGNATURE_NOT_STATED = "op_signature_not_stated"

#: The kind of decision 3: the stated op_signature is not covered by the run tools' contract.
KIND_OP_SIGNATURE_NOT_COVERED = "op_signature_not_covered"

#: The kind of decision 4: the content states no ``n_max``.
KIND_N_MAX_NOT_STATED = "n_max_not_stated"

#: The five answers of steps 3 to 7 of decision 5, in that order. The order is the rule.
KINDS = (
    KIND_OP_SIGNATURE_NOT_STATED,
    KIND_OP_SIGNATURE_NOT_COVERED,
    run_objective.KIND_OBJECTIVE_NOT_STATED,
    run_objective.KIND_OBJECTIVE_NOT_COVERED,
    KIND_N_MAX_NOT_STATED,
)

_MESSAGES = {
    KIND_OP_SIGNATURE_NOT_STATED: "op_signature: the instance record of the run states none, and nothing stands in for it",
    KIND_OP_SIGNATURE_NOT_COVERED: "op_signature: the stated record is not covered by the contract of the run tools",
    KIND_N_MAX_NOT_STATED: "n_max: the instance record of the run states no bound of the repeats, and nothing stands in for it",
}


class Admitted(typing.NamedTuple):
    """What a run tool takes from the content of ``instance.json`` of an admitted run.

    - ``m``, ``k``, ``n``: the ``shape.m``, ``shape.k`` and ``shape.n`` of
      the stated op_signature record (ADR-0061 decision 3).
    - ``n_max``: the stated bound of the repeats (ADR-0061 decision 3).
    - ``sample_form``, ``bound``: those of the
      :class:`hilclaw.run_objective.Admitted` of the stated objective
      (ADR-0061 decisions 4 and 6); ``bound`` ``None`` says no ceiling is
      stated.

    As :func:`admit` returns it, each value is the one it is taken from,
    unchanged. No field has a default.
    """

    m: int
    k: int
    n: int
    n_max: int
    sample_form: str
    bound: int | None


def admit(instance, *, covers):
    """Return the :class:`Admitted` of ``instance``, or raise the one answer it has.

    - ``instance``: the :class:`hilclaw.instance.Instance` of the read of
      moment 4 of the call. Which read that is is the caller's statement and
      is not checked.
    - ``covers``: the predicate of ADR-0041 decision 5, a callable that is
      handed an op_signature record and returns ``True`` when the contract
      covers it and ``False`` when it does not.

    No parameter has a default, and ``covers`` is given by name. First,
    :class:`TypeError` is raised when the type of ``instance`` is not exactly
    ``Instance``, and then when ``covers`` is not callable.

    The answers, the first whose condition holds and no other (decision 5,
    steps 3 to 7):

    3. ``instance.op_signature`` is ``None``: a
       :class:`hilclaw.tools.ToolFailure` of
       :data:`KIND_OP_SIGNATURE_NOT_STATED`. ``covers`` is not called.
    4. ``covers`` returns ``False`` for the stated record: a ``ToolFailure``
       of :data:`KIND_OP_SIGNATURE_NOT_COVERED`. ``covers`` is called once,
       with the record object the instance holds. What it raises passes
       through unchanged, and :class:`TypeError` is raised when what it
       returns is not exactly a ``bool``.
    5. and 6. :func:`hilclaw.run_objective.admit` of ``instance.objective``:
       what it raises passes through unchanged.
    7. ``instance.n_max`` is ``None``: a ``ToolFailure`` of
       :data:`KIND_N_MAX_NOT_STATED`. No bound is substituted.

    Otherwise the :class:`Admitted` is returned. Nothing else of the instance
    is looked at: not ``hw_profile``, ``hw_profile_key``, ``tolerance``,
    ``draws``, ``others`` or the key of the op_signature. ``instance`` is not
    modified or kept, and no file is read or written.
    """
    if type(instance) is not instances.Instance:
        raise TypeError("instance: must be exactly a hilclaw.instance.Instance")
    if not callable(covers):
        raise TypeError("covers: must be callable")
    stated = instance.op_signature
    if stated is None:
        raise _failure(KIND_OP_SIGNATURE_NOT_STATED)
    covered = covers(stated.record)
    if type(covered) is not bool:
        raise TypeError("covers: must return exactly a bool")
    if not covered:
        raise _failure(KIND_OP_SIGNATURE_NOT_COVERED)
    objective = run_objective.admit(instance.objective)
    if instance.n_max is None:
        raise _failure(KIND_N_MAX_NOT_STATED)
    shape = stated.record["shape"]
    return Admitted(
        shape["m"],
        shape["k"],
        shape["n"],
        instance.n_max,
        objective.sample_form,
        objective.bound,
    )


def _failure(kind):
    return tools.ToolFailure(kind, _MESSAGES[kind])
