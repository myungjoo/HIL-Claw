"""The two answers of the run tools for the member ``objective`` of a run, and what a covered one gives.

ADR-0061 decisions 4 and 6 fix what a call of ``sim.run`` or ``board.run``
answers for the value :func:`hilclaw.instance.objective_of` returns, and what
it takes from a value that has neither answer. The module renders that part,
ahead of any tool function:

* :data:`KIND_OBJECTIVE_NOT_STATED`: a valid file without the member
  (ADR-0061 decision 4; ADR-0053 decision 5).
* :data:`KIND_OBJECTIVE_NOT_COVERED`: a present member this contract does not
  cover (ADR-0061 decision 4).
* :data:`KINDS`: the two in the order they are tested.
* :func:`admit`: the answer for one value, or the :class:`Admitted` of a
  covered one: the sample form (ADR-0061 decision 4) and the ``bound`` of the
  ``memory_ceiling`` entry or that no ceiling is stated (ADR-0061 decision 6).

Each kind is a tool failure of the run tools' contract and no reserved kind
(ADR-0061 decision 4). Neither is ever the ``failure`` of an end line.

Choices that are this module's own and no rule of a record:

* Not stated is tested before anything else, and so wins over every other
  answer and over every :class:`TypeError` below.
* A value :func:`hilclaw.instance.read` cannot return is :class:`TypeError`
  and is never taken as covered: one that is neither ``None`` nor exactly a
  ``dict``; a ``dict`` whose members are not exactly ``objectives`` and
  ``constraints``; either of those not exactly a ``list``; an entry of either
  that is not exactly a ``dict``; a constraint entry without a ``type`` that is
  exactly a ``str``. These are raised before coverage is looked at.
* Of a covered value, a ``memory_ceiling`` entry whose members are not exactly
  ``type`` and ``bound``, or two such entries, are :class:`TypeError`; a
  ``bound`` that is not exactly an ``int`` is :class:`TypeError` and one below
  0 or above :data:`hilclaw.harness.memory_ceiling.BOUND_MAX` is
  :class:`ValueError` (the written form of ADR-0053 decision 4, checked again
  here). No valid file holds such an entry today (ADR-0053 decision 4).
* The answer for a covered value is a :class:`typing.NamedTuple`, and the
  field names and their order are this module's.
* The messages. Each is at most 200 characters long, starts with the name of
  the member it is about and shows nothing of the value. Nothing may depend
  on the wording.

What the module does not do: it is no tool, registers nothing and reads no
file. It computes no verdict and admits no ``memory_ceiling``. It takes no
default and no other source for the objective or the ``bound``: not the
request, not a spec, not a value kept from an earlier call (ADR-0061
decision 6); it keeps nothing between calls. Its place relative to the
answers for the op_signature and ``n_max`` is not its own to decide (OD-18
sub-question ⑲ (가)): whoever calls places it.
"""

import typing

from hilclaw import tools
from hilclaw.harness import memory_ceiling

#: The kind of ADR-0061 decision 4: the file of the run states no objective.
KIND_OBJECTIVE_NOT_STATED = "objective_not_stated"

#: The kind of ADR-0061 decision 4: the stated objective is not covered by the run tools' contract.
KIND_OBJECTIVE_NOT_COVERED = "objective_not_covered"

#: The two kinds in the order they are tested.
KINDS = (KIND_OBJECTIVE_NOT_STATED, KIND_OBJECTIVE_NOT_COVERED)

_MESSAGES = {
    KIND_OBJECTIVE_NOT_STATED: "objective: the instance record of the run states none, and nothing stands in for it",
    KIND_OBJECTIVE_NOT_COVERED: "objective: the stated objectives or constraints are ones the run tools have no sample form or verdict for",
}

_SAMPLE_FORM = "interval"
_COVERED_OBJECTIVE = {"type": "latency_minimisation"}
_CEILING = "memory_ceiling"


class Admitted(typing.NamedTuple):
    """What a run tool takes from a covered ``objective``.

    - ``sample_form``: ``"interval"``, the sample form ADR-0061 decision 4
      derives from the one objective ``latency_minimisation``.
    - ``bound``: the ``bound`` of the ``memory_ceiling`` entry as stated, or
      ``None`` when ``constraints`` is empty. ``None`` here means *no ceiling
      stated* and never *not judged* or *within* (ADR-0061 decision 6;
      ADR-0050 decision 5).
    """

    sample_form: str
    bound: int | None


def admit(objective):
    """Return the :class:`Admitted` of ``objective``, or raise the one answer it has.

    ``objective`` is the value :func:`hilclaw.instance.objective_of` returns:
    ``None`` or the ``dict`` of the member. The parameter has no default.

    1. ``None``: :class:`hilclaw.tools.ToolFailure` of
       :data:`KIND_OBJECTIVE_NOT_STATED`.
    2. A value of a form ``read`` cannot return: :class:`TypeError` (see the
       module's own choices).
    3. Not covered (ADR-0061 decision 4): ``objectives`` does not hold exactly
       one entry that is exactly ``{"type": "latency_minimisation"}``, or
       ``constraints`` holds an entry of a type other than
       ``memory_ceiling``: :class:`hilclaw.tools.ToolFailure` of
       :data:`KIND_OBJECTIVE_NOT_COVERED`.
    4. Otherwise the :class:`Admitted`, after the ``memory_ceiling`` entry, if
       any, is checked as the module's own choices say.

    No verdict is computed, nothing is compared with a figure, and
    ``objective`` is not modified or kept.
    """
    if objective is None:
        raise _failure(KIND_OBJECTIVE_NOT_STATED)
    if type(objective) is not dict:
        raise TypeError("objective: must be None or exactly a dict")
    if set(objective) != {"objectives", "constraints"}:
        raise TypeError(
            "objective: must have exactly the members objectives and constraints"
        )
    objectives = objective["objectives"]
    constraints = objective["constraints"]
    for name, entries in (("objectives", objectives), ("constraints", constraints)):
        if type(entries) is not list:
            raise TypeError(f"objective.{name}: must be exactly a list")
        if any(type(entry) is not dict for entry in entries):
            raise TypeError(f"objective.{name}: each entry must be exactly a dict")
    if any(type(entry.get("type")) is not str for entry in constraints):
        raise TypeError(
            "objective.constraints: each entry must have a type that is exactly a str"
        )
    if objectives != [_COVERED_OBJECTIVE] or any(
        entry["type"] != _CEILING for entry in constraints
    ):
        raise _failure(KIND_OBJECTIVE_NOT_COVERED)
    if not constraints:
        return Admitted(_SAMPLE_FORM, None)
    if len(constraints) != 1 or set(constraints[0]) != {"type", "bound"}:
        raise TypeError(
            "objective.constraints: at most one memory_ceiling entry, with exactly type and bound"
        )
    bound = constraints[0]["bound"]
    if type(bound) is not int:
        raise TypeError("objective.constraints: the bound must be exactly an int")
    if not 0 <= bound <= memory_ceiling.BOUND_MAX:
        raise ValueError("objective.constraints: the bound is outside 0 to BOUND_MAX")
    return Admitted(_SAMPLE_FORM, bound)


def _failure(kind):
    return tools.ToolFailure(kind, _MESSAGES[kind])
