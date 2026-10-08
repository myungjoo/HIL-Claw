"""The tool function of a journaled tool (ADR-0015 decisions 4 and 5).

A *journaled tool* is a tool one call of which is one journaled step.
:func:`tool_function` builds its tool function from what the tool's contract
states. That function is what a registry holds for the tool, so its step is
reached only through :func:`hilclaw.journaled_step.run`: the lookup, the start
line, the step and the end line of ADR-0011 decision 3.

Five members of a request have one meaning in every tool, at the top level:
``run_id``, ``execution`` and the envelope numbers ``round``, ``candidate``
and ``attempt``. The request of a journaled tool carries ``run_id``,
``execution`` (required, without a default) and the numbers its contract
requires. ``step`` is the contract's and is never read from a request.

A call, in this order:

1. The request is checked: the five members here, by the rules of
   :func:`hilclaw.layout.check_run_id` and
   :func:`hilclaw.journal.step_identity`, then the tool's own check. A refusal
   is a :class:`hilclaw.tools.ToolFailure` of the reserved kind
   ``invalid_request``: nothing was asked, read, written or consumed.
2. The data root is asked, once, through
   :func:`hilclaw.data_root_source.obtain`; its ``no_data_root`` passes through.
3. The step of the identity is carried out by ``journaled_step.run``. What it
   returns is returned and what it raises passes through unchanged: the tool
   failure of an ended step with a ``failure``, ``step_open``, every other
   exception.

Conventions of this module, which the records do not fix:

- The numbers a contract requires are a prefix of ``round``, ``candidate``,
  ``attempt``: the envelope rule makes every valid set one.
- A number the contract does not require is refused, also when it is ``null``:
  the identity would otherwise drop what the caller stated.
- No other member is looked at: it is the tool's own check's.
- What the tool's own check raises passes through unchanged, whatever it is.
- Nothing is kept between calls (ADR-0010 decision 7).

Limits it does not remove (ADR-0015 decision 7): a caller that states the
numbers of another target or raises ``execution`` by itself, a round above the
stored ``round``, two calls at once, a check that accepts what the stated
schema excludes, and a step that states a reserved kind. A run that cannot be
used (no run directory, no valid ``STATE.json``, a damaged log, a stored
position beyond the log) is found only by reading: it is no refused request,
and what ``journaled_step.run`` raises for it passes through with no kind given
here (OD-18 sub-question 4, open).

The tool function of a journaled HW tool has one moment more, the selection of
a backend between the lookup and the start line (ADR-0016 decision 2):
:mod:`hilclaw.hw_tool` builds it over the same check of the request.

It registers nothing, names no tool, no step, no axis and no result member and
reads no configuration.
"""

from hilclaw import data_root_source, events, journal, journaled_step, layout, tools

_NUMBERS = ("round", "candidate", "attempt")
_INVALID = (
    layout.InvalidPathValueError,
    journal.JournalError,
    events.InvalidEventError,
)


def tool_function(*, step, numbers, source, check, perform):
    """Return the tool function of the journaled tool that these five state.

    - ``step``: the ``step`` name the tool's contract fixes.
    - ``numbers``: a ``tuple``, the prefix of ``("round", "candidate",
      "attempt")`` the contract requires; ``()`` for none.
    - ``source``: the data-root source the tool is bound to (ADR-0015
      decision 3), a callable without arguments.
    - ``check``: called as ``check(request)`` after the five members are
      checked and before the data root is asked; it refuses the other members
      of the request by raising a ``ToolFailure`` of kind ``invalid_request``.
    - ``perform``: the step, called as ``perform(data_root, request)`` with a
      :class:`pathlib.Path` and the request as the caller gave it, only for an
      identity with no line. It returns ``(spend, result)`` or raises
      :class:`hilclaw.journaled_step.StepFailed`.

    Raises :class:`ValueError` when ``step`` is no name or ``numbers`` no such
    prefix and :class:`TypeError` when ``numbers`` is no ``tuple`` or one of
    the last three is not callable. Building calls none of the three.

    The function returned takes one request and returns the ``result`` of the
    step, a ``dict``. It raises ``ToolFailure`` of kind ``invalid_request``
    with a message that names the member, and otherwise what ``check``,
    :func:`hilclaw.data_root_source.obtain` and
    :func:`hilclaw.journaled_step.run` raise. It does not modify the request.
    """

    def carry_out(data_root, run_id, identity, request):
        return journaled_step.run(
            data_root, run_id, identity, lambda: perform(data_root, request)
        )

    return _built(step, numbers, carry_out, source=source, check=check, perform=perform)


def _built(step, numbers, carry_out, *, source, check, **others):
    journal.step_identity(step, 1)
    if type(numbers) is not tuple:
        raise TypeError(f"numbers must be a tuple, got {type(numbers).__name__}")
    if numbers != _NUMBERS[: len(numbers)]:
        raise ValueError(f"numbers must be a prefix of {_NUMBERS}, got {numbers}")
    for name, value in {"source": source, "check": check, **others}.items():
        if not callable(value):
            raise TypeError(f"{name} must be callable, got {type(value).__name__}")

    def journaled(request):
        run_id, identity = _checked(step, numbers, request)
        check(request)
        data_root = data_root_source.obtain(source)
        return carry_out(data_root, run_id, identity, request)

    return journaled


def _refuse(message, cause=None):
    raise tools.ToolFailure(tools.KIND_INVALID_REQUEST, message) from cause


def _checked(step, numbers, request):
    if type(request) is not dict:
        _refuse(f"the request must be an object, got {type(request).__name__}")
    for name in ("run_id", "execution", *numbers):
        if name not in request:
            _refuse(f"{name}: is required")
    for name in _NUMBERS:
        if name in request and name not in numbers:
            _refuse(f"{name}: is no member of a request of this tool")
        if name in numbers and request[name] is None:
            _refuse(f"{name}: must be an integer, got null")
    given = (request[name] for name in numbers)
    try:
        run_id = layout.check_run_id(request["run_id"])
        return run_id, journal.step_identity(step, request["execution"], *given)
    except _INVALID as error:
        _refuse(str(error).removeprefix("data."), error)
