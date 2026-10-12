"""What the end line of a check of ``correctness.check`` holds after its operation raised a tool failure.

``ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md``
is the rule for a tool failure an operation of this tool raises; a decision
cited by its number alone is one of that record. The module renders, ahead of
the tool function, the part of its decisions 4 and 5 that needs no log:

* :func:`ended_with`: from a tool failure an operation raised to the kind and
  the message the ``failure`` of the end line holds. For a kind outside the
  contract that is the tool's own kind with a message of this module; for a
  backend kind it is the kind and the message that were raised (decision 4).
* :data:`KIND_OPERATION_FAILURE_INVALID`: the kind of decision 4.
* :data:`BACKEND_KINDS`: the backend kinds of the contract as this source has
  it, which are none (decision 5). Every tool failure an operation raises is
  therefore answered with :data:`KIND_OPERATION_FAILURE_INVALID`.
* The message of that kind says that the operation raised a tool failure of a
  kind the contract does not let a backend raise. It carries nothing of the
  message that was raised and shows no raised kind that is not reserved
  (decision 4).

Choices that are this module's own and no rule of a record:

* The answer is a pair and no exception. The code that ends the step has the
  amounts of the step, and this module states no spend.
* How the raised object is read. ``kind`` and ``message`` are attributes that
  the code of a backend can replace after the tool failure was built. ``kind``
  is read once, and ``message`` once and only where the kind is a backend
  kind. A read that raises an :class:`Exception`, a ``kind`` whose type is not
  exactly ``str``, and, for a backend kind, a ``message`` whose type is not
  exactly ``str`` are each answered with
  :data:`KIND_OPERATION_FAILURE_INVALID` and a message that says so: no such
  value can stand as the ``failure`` of an end line. The record does not
  speak of such an object. A :class:`BaseException` that is no ``Exception``
  out of a read is not caught.
* What the message says of the raised kind: whether it is a reserved kind,
  and for a reserved kind its name, which is then one of
  :data:`hilclaw.tools.RESERVED_KINDS`. Decision 4 allows more: the message
  may tell a kind of this contract from any other name and may name it. The
  module says less because it holds no list of the kinds of this contract.
  Every message of this module is built when the module is imported.
* The backend-kind row is rendered although no call takes it: the tool
  function then has one place for the list of decision 5. The row is the rule
  "a record that names a backend kind meets; such a record may decide
  otherwise for its kind" (decision 4), and what the message of such a kind
  may hold is that record's to say. This module checks nothing of it beyond
  its type.

What the module does not do: it is no tool and no step and is bound to none.
It is this tool's and gives no rule for another tool. It calls no operation
and catches nothing an operation raises. It does not say which tool failure
was raised by an operation: whoever calls says so by calling. It appends no
line and states no spend. It names no backend kind. It keeps nothing of the
raised tool failure and nothing between calls. It says nothing of what
anybody does after the answer. It imports :mod:`hilclaw.tools` and nothing
else.
"""

from hilclaw import tools

#: The kind of ADR-0047 decision 4: the tool's own, not reserved, and no backend kind.
KIND_OPERATION_FAILURE_INVALID = "operation_failure_invalid"

#: The backend kinds of ADR-0047 decision 5: none. A kind is added only when a record of this tool's contract names it.
BACKEND_KINDS = frozenset()

_OUTSIDE = "the operation raised a tool failure of a kind the contract does not let a backend raise: "
_RESERVED = {
    kind: _OUTSIDE + "the reserved kind " + kind for kind in tools.RESERVED_KINDS
}
_OTHER = _OUTSIDE + "a kind that is not reserved"
_NOT_READ = (
    "the operation raised a tool failure whose kind or message could not be read as "
    "exactly a string; it is answered as a kind the contract does not let a backend raise"
)


def ended_with(raised):
    """Return the pair ``(kind, message)`` the ``failure`` of the end line holds.

    - ``raised``: the tool failure an operation of ``correctness.check``
      raised, an instance of :class:`hilclaw.tools.ToolFailure`. That an
      operation raised it is the caller's statement and is not checked.

    The parameter has no default. Before anything is read,
    :class:`TypeError` is raised when ``raised`` is no instance of
    ``ToolFailure``.

    1. The kind is no member of :data:`BACKEND_KINDS`, a kind outside the
       contract: the pair is :data:`KIND_OPERATION_FAILURE_INVALID` and a
       message of this module, whichever kind was raised, a reserved kind
       and :data:`KIND_OPERATION_FAILURE_INVALID` itself included (ADR-0047
       decision 4). As long as :data:`BACKEND_KINDS` is empty this is every
       tool failure (decision 5).
    2. The kind is a member of :data:`BACKEND_KINDS`: the pair is the raised
       kind and the raised message, as they are (decision 4).
    3. The kind, or for a backend kind the message, cannot be read as exactly
       a ``str``: the pair is :data:`KIND_OPERATION_FAILURE_INVALID` and a
       message of this module. This is the module's own choice (see the
       module docstring).

    Each member of the pair is exactly a ``str`` and the kind is a name, so
    :class:`hilclaw.tools.ToolFailure` can be built from the pair. A message
    of this module has a bounded length, shows nothing of the raised message
    and no raised kind that is not reserved, and composing it calls no code
    of ``raised``. Nothing may depend on its wording.

    ``raised`` is not modified or kept, and no file is read or written.
    """
    if not isinstance(raised, tools.ToolFailure):
        raise TypeError("raised: must be a ToolFailure")
    try:
        kind = raised.kind
        backend = type(kind) is str and kind in BACKEND_KINDS
        message = raised.message if backend else None
    except Exception:  # noqa: BLE001
        return KIND_OPERATION_FAILURE_INVALID, _NOT_READ
    if type(kind) is not str:
        return KIND_OPERATION_FAILURE_INVALID, _NOT_READ
    if not backend:
        return KIND_OPERATION_FAILURE_INVALID, _RESERVED.get(kind, _OTHER)
    if type(message) is not str:
        return KIND_OPERATION_FAILURE_INVALID, _NOT_READ
    return kind, message
