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
  decision 4), each as the content states it.

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
  the field names and their order are this module's.
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
anything. It keeps nothing between calls. It imports :mod:`typing`, :mod:`hilclaw.instance` and
:mod:`hilclaw.tools` and nothing else.
"""

import typing

from hilclaw import instance as instances
from hilclaw import tools

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
       not exactly a ``bool``.
    3. ``instance.draws`` is ``None``: :data:`KIND_DRAWS_NOT_STATED`.
    4. ``instance.tolerance`` is ``None``: :data:`KIND_TOLERANCE_NOT_STATED`.
    5. Otherwise the :class:`Admitted` is returned.

    Nothing else of the instance is looked at: not ``hw_profile``,
    ``hw_profile_key``, ``others`` or the key of the op_signature. Of the
    record this function itself reads the ``shape`` only, and only for an
    admitted content; what ``covers`` reads of it is that callable's. No
    value is compared with another or with a limit, and none is derived,
    rounded or replaced.

    ``instance`` is not modified or kept, and no file is read or written.
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
    if instance.draws is None:
        raise _failure(KIND_DRAWS_NOT_STATED)
    tolerance = instance.tolerance
    if tolerance is None:
        raise _failure(KIND_TOLERANCE_NOT_STATED)
    shape = stated.record["shape"]
    return Admitted(
        shape["m"],
        shape["k"],
        shape["n"],
        instance.draws,
        tolerance.rtol,
        tolerance.atol,
    )


def _failure(kind):
    return tools.ToolFailure(kind, _MESSAGES[kind])
