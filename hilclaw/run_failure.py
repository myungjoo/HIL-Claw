"""What the end line of a call of ``sim.run`` or ``board.run`` holds after its operation raised a tool failure.

``ARCHITECTURE/decisions/ADR-0068-od18-run-tools-operation-tool-failure.md``
is the rule for a tool failure an operation of these two tools raises; a
decision cited by its number alone is one of that record. The module renders,
ahead of the tool function, the part of its decisions 3 to 6 that needs no
log:

* :func:`ended_with`: from a tool failure an operation raised to the kind and
  the message the ``failure`` of the end line holds. For a backend kind it is
  the kind and the message that were raised; for every other kind it is
  :data:`KIND_OPERATION_FAILURE_INVALID` with a message of this module
  (decision 4).
* :data:`KIND_OPERATION_FAILURE_INVALID`: the kind of decision 4.
* :data:`BACKEND_KINDS`: the backend kinds of the run tools' contract as this
  source has it (decisions 3 and 5): the eight of ``correctness.check`` for
  the rows S1 to S6, S9 and S10, defined again by this contract.
  :data:`KIND_NO_KERNEL_SOURCE`, :data:`KIND_KERNEL_SOURCE_UNREADABLE`,
  :data:`KIND_BUILD_DIRECTORY_UNUSABLE`, :data:`KIND_SETTINGS_REFUSED`,
  :data:`KIND_BUILD_INPUT_MISSING`, :data:`KIND_COMPILER_UNAVAILABLE`,
  :data:`KIND_BUILD_OUTPUT_MISSING` and :data:`KIND_EXECUTABLE_UNSTARTABLE`,
  in that order of the rows; for these tools the executable is the timing
  executable and the program of S5 the driver program (decision 3).
* The kinds outside the contract (decision 4) are every other: the reserved
  kinds, the six kinds of the run tools' admission, seed and objective
  answers, ``operation_answer_invalid``, ``build_log_unwritable`` (which only
  the tool function raises), :data:`KIND_OPERATION_FAILURE_INVALID` itself and
  any other name.

The nine kind constants are those of :mod:`hilclaw.check_failure`, imported:
decisions 3 and 4 give the run tools' kinds the spelling and the meaning of
``correctness.check``'s on purpose. :data:`BACKEND_KINDS` is a set of this
module, built from the eight, so that a kind a later record adds to one
contract alone is added to that contract's set alone.

What a message of a backend kind may show is said by decision 6, as a rule
for the code of an operation that raises; "a message that breaks it ... is not
detected", and this module checks nothing of a message beyond its type. A
backend kind raised for a situation it does not mean "is taken as it is"
(ADR-0047 Limits, cited by decision 4): nothing here decides whether a kind
fits.

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
* What the message names. The message of
  :data:`KIND_OPERATION_FAILURE_INVALID` says that the operation raised a tool
  failure of a kind the contract does not let a backend raise, and whether
  that kind is reserved; for a reserved kind it names it, which is then one of
  :data:`hilclaw.tools.RESERVED_KINDS`. Decision 6 allows more: the message
  may also name a kind of this contract. The module says less and names none,
  so that it needs no list of the run tools' other kinds. It never shows the
  raised message. Every message of this module is built when the module is
  imported.

What the module does not do: it is no tool and no step, is bound to none and
is called by :func:`hilclaw.run_tool.tool_function`. It calls no operation and catches nothing
an operation raises; whoever calls says that an operation raised the tool
failure. It appends no line and states no spend. It writes no compiler log:
where the operation handed a log over, ADR-0108 decision 7 comes first in the
tool function, and that is not this module's. It raises no backend kind,
composes no message of one and maps no situation to one. It keeps nothing of
the raised tool failure and nothing between calls. It gives no rule for
``correctness.check`` or ``profiler.collect``. It imports
:mod:`hilclaw.check_failure` and :mod:`hilclaw.tools` and nothing else.
"""

from hilclaw import check_failure, tools

#: The kind of decision 4: the run tools' own, not reserved, and no backend kind.
KIND_OPERATION_FAILURE_INVALID = check_failure.KIND_OPERATION_FAILURE_INVALID

#: The backend kind of decision 3 for S1: the attempt has no kernel source.
KIND_NO_KERNEL_SOURCE = check_failure.KIND_NO_KERNEL_SOURCE

#: The backend kind of decision 3 for S2: the reader of the kernel source failed.
KIND_KERNEL_SOURCE_UNREADABLE = check_failure.KIND_KERNEL_SOURCE_UNREADABLE

#: The backend kind of decision 3 for S3: the build directory cannot be made or written.
KIND_BUILD_DIRECTORY_UNUSABLE = check_failure.KIND_BUILD_DIRECTORY_UNUSABLE

#: The backend kind of decision 3 for S4: a setting of the timing build or run is one the functions refuse.
KIND_SETTINGS_REFUSED = check_failure.KIND_SETTINGS_REFUSED

#: The backend kind of decision 3 for S5: a file of the compiled set is no longer a regular file, or the driver program is missing.
KIND_BUILD_INPUT_MISSING = check_failure.KIND_BUILD_INPUT_MISSING

#: The backend kind of decision 3 for S6: the compiler is not found or cannot be started.
KIND_COMPILER_UNAVAILABLE = check_failure.KIND_COMPILER_UNAVAILABLE

#: The backend kind of decision 3 for S9: status 0 and no timing executable at the path, or it cannot be moved there.
KIND_BUILD_OUTPUT_MISSING = check_failure.KIND_BUILD_OUTPUT_MISSING

#: The backend kind of decision 3 for S10: the timing executable cannot be started.
KIND_EXECUTABLE_UNSTARTABLE = check_failure.KIND_EXECUTABLE_UNSTARTABLE

#: The backend kinds of decision 5. A kind is added only when a record of the run tools' contract names it.
BACKEND_KINDS = frozenset(
    {
        KIND_NO_KERNEL_SOURCE,
        KIND_KERNEL_SOURCE_UNREADABLE,
        KIND_BUILD_DIRECTORY_UNUSABLE,
        KIND_SETTINGS_REFUSED,
        KIND_BUILD_INPUT_MISSING,
        KIND_COMPILER_UNAVAILABLE,
        KIND_BUILD_OUTPUT_MISSING,
        KIND_EXECUTABLE_UNSTARTABLE,
    }
)

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

    - ``raised``: the tool failure an operation of ``sim.run`` or
      ``board.run`` raised, an instance of :class:`hilclaw.tools.ToolFailure`.
      That an operation raised it is the caller's statement and is not
      checked.

    The parameter has no default. First, :class:`TypeError` is raised when
    ``raised`` is no instance of ``ToolFailure``.

    1. The kind is no member of :data:`BACKEND_KINDS`, a kind outside the
       contract: the pair is :data:`KIND_OPERATION_FAILURE_INVALID` and a
       message of this module, whichever kind was raised: a reserved kind,
       another kind of the run tools' contract and
       :data:`KIND_OPERATION_FAILURE_INVALID` itself included (decision 4).
    2. The kind is a member of :data:`BACKEND_KINDS`: the pair is the raised
       kind and the raised message, as they are (decision 4). What such a
       message may show is said by decision 6 and is not checked here, and
       neither is whether the kind fits the situation it was raised for.
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
