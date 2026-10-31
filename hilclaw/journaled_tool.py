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
requires. ``step`` is the contract's and is never read from a request. A
contract with one ``step`` value states it when the function is built. A
contract with several states them all then, with the callable that gives the
``step`` of a checked request from its other members (ADR-0040 decision 3 has
such a tool): :func:`stepped_function` is the check of the request for it.

A call, in this order:

1. The request is checked: the five members here, by the rules of
   :func:`hilclaw.layout.check_run_id` and
   :func:`hilclaw.journal.step_identity`, then the tool's own check. A refusal
   is a :class:`hilclaw.tools.ToolFailure` of the reserved kind
   ``invalid_request``: nothing was asked, read, written or consumed.
2. The data root is asked, once, through
   :func:`hilclaw.data_root_source.obtain`; its ``no_data_root`` passes through.
   Then the layout version stamp of the run is read (ADR-0030 decision 3):
   ``runs/<run_id>/instance.json`` below that data root, as a whole, by
   :func:`hilclaw.instance.layout_version_of`, before ``STATE.json`` or the
   log is opened. When the stamp cannot be had, the call is a tool failure of
   one of the four reserved kinds of ADR-0019 decision 2, and what follows
   under 3 does not take place (ADR-0030 decision 4; the cases are below).
3. The step of the identity is carried out by ``journaled_step.run``. What it
   returns is returned and what it raises passes through unchanged: the tool
   failure of one of the same four kinds for what the lookup finds in
   ``STATE.json`` or in the log, the tool failure of an ended step with a
   ``failure``, ``step_open``, every other exception.

What the read of the stamp raises for ``runs/<run_id>/instance.json`` is
answered with a ``ToolFailure`` chained to the error it answers for, by the
rows ADR-0019 decision 3 has for that file and the borders of its decision 4:

- ``run_file_missing``: :class:`hilclaw.instance.MissingInstanceError`, and a
  :class:`FileNotFoundError` or :class:`NotADirectoryError` (a data root that
  is no existing directory at the read, a file gone during the read).
- ``run_file_invalid``: :class:`hilclaw.instance.InvalidInstanceError` (an
  invalid content, an empty file included, or a path that is no regular file).
- ``run_file_unsupported``: :class:`hilclaw.instance.UnsupportedVersionError`.
- ``run_file_unreadable``: every other :class:`OSError`.

Such a call appended no line, opened neither ``STATE.json`` nor the log and
did not call the step. The kind is answered for every identity and says
nothing about it: the lookup was not carried out, so an ended or an open
identity of such a run is not answered from the log (ADR-0030 decision 4).
The same request again is answered as if the failed call had not been made.
Everything else the read raises passes through unchanged, a ``ToolFailure``
and a :class:`BaseException` included.

Conventions of this module, which the records do not fix:

- The numbers a contract requires are a prefix of ``round``, ``candidate``,
  ``attempt``: the envelope rule makes every valid set one.
- A number the contract does not require is refused, also when it is ``null``:
  the identity would otherwise drop what the caller stated.
- No other member is looked at: it is the tool's own check's.
- What the tool's own check raises passes through unchanged, whatever it is.
- Nothing is kept between calls (ADR-0010 decision 7): the stamp is read at
  each call that has a data root.
- The stamp is read in the one function :func:`checked_function` and
  :func:`stepped_function` return, the part the builders share, so that they cannot differ. It is therefore read for whatever ``carry_out`` they are
  handed; that is the placement of this module and no rule of the record for
  another user of them.
- With several ``step`` values the ``step`` of a call is obtained last in the
  check of the request, after the five members and the tool's own check, so
  that its callable sees a checked request only. A value it returns that is
  none of the stated ones is a defect of the contract and no refused request:
  it is a :class:`RuntimeError`, raised before the data root is asked.
- The reader of the stamp is no parameter: ADR-0030 decision 3 names the file
  and ADR-0024 decision 4 the condition, and
  :func:`hilclaw.instance.layout_version_of` is both.
- What that function returns is compared with nothing (ADR-0030 decision 5).
- Only the read of the stamp is answered this way here: the same classes out
  of the tool's own check or out of ``carry_out`` are not.
- The message of such a failure starts with ``runs/<run_id>/instance.json``
  (ADR-0019 decision 6): for the three classes it is the message of the
  reader as it is, and for an :class:`OSError` it is composed by
  :mod:`hilclaw.run_files`. Nothing may depend on the rest of the wording.

Limits it does not remove (ADR-0015 decision 7): a caller that states the
numbers of another target or raises ``execution`` by itself, a round above the
stored ``round``, two calls at once, a check that accepts what the stated
schema excludes, and a step that states a reserved kind. A run that cannot be
used at a call (no run directory, an ``instance.json`` from which the stamp
cannot be had, no valid ``STATE.json``, a damaged log, a stored position
beyond the log) is found only by reading: it is no refused request, and the
read of the stamp or ``journaled_step.run`` answers it with a tool failure of
kind ``run_file_missing``, ``run_file_unreadable``, ``run_file_invalid`` or
``run_file_unsupported`` (ADR-0019 decisions 2 to 4, ADR-0030 decision 4).
The file can change or go between the read of the stamp and a later read of
the same call, and nothing checks the tree of the run against the stamp
(ADR-0030 decision 7).

The tool function of a journaled HW tool has one moment more, the selection of
a backend between the lookup and the start line (ADR-0016 decision 2):
:mod:`hilclaw.hw_tool` builds it over the same check of the request and the
same read of the stamp, which :func:`checked_function` and
:func:`stepped_function` hold for the builders of both modules.

It registers nothing, names no tool, no step, no axis and no result member and
reads no configuration.
"""

from hilclaw import (
    data_root_source,
    events,
    instance,
    journal,
    journaled_step,
    layout,
    run_files,
    tools,
)

_NUMBERS = ("round", "candidate", "attempt")
_INVALID = (
    layout.InvalidPathValueError,
    journal.JournalError,
    events.InvalidEventError,
)
_STAMP_KINDS = {
    instance.MissingInstanceError: tools.KIND_RUN_FILE_MISSING,
    instance.InvalidInstanceError: tools.KIND_RUN_FILE_INVALID,
    instance.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
}


def tool_function(*, step, numbers, source, check, perform):
    """Return the tool function of the journaled tool that these five state.

    - ``step``: the ``step`` name the tool's contract fixes, for a contract
      that fixes one.
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
    with a message that names the member, or says that the request is no
    object; of one of the four kinds ``run_file_missing``,
    ``run_file_unreadable``, ``run_file_invalid`` and
    ``run_file_unsupported`` when the layout version stamp of the run cannot
    be had (ADR-0030 decision 4; the module docstring has the cases), having
    appended no line and not called ``perform``; and otherwise what ``check``,
    :func:`hilclaw.data_root_source.obtain`, the read of the stamp and
    :func:`hilclaw.journaled_step.run` raise, among them the ``ToolFailure``
    of one of the same four kinds for what the lookup finds. It does not
    modify the request.
    """

    def carry_out(data_root, run_id, identity, request):
        return journaled_step.run(
            data_root, run_id, identity, lambda: perform(data_root, request)
        )

    return checked_function(
        step=step,
        numbers=numbers,
        carry_out=carry_out,
        source=source,
        check=check,
        perform=perform,
    )


def checked_function(*, step, numbers, carry_out, source, check, **others):
    """Return a function of one request that checks it and hands on to ``carry_out``.

    This is the part :func:`tool_function` and
    :func:`hilclaw.hw_tool.tool_function` share, for a contract with one
    ``step`` (:func:`stepped_function` is it for a contract with several): the
    check when built and, at
    a call, the check of the request, the tool's own check, the data root
    asked once and the read of the layout version stamp of the run (ADR-0030
    decision 3). Everything after that is ``carry_out``'s. It does not hand on
    right after the data root: the stamp is read first, whatever ``carry_out``
    it was given.

    - ``step``, ``numbers``, ``source``, ``check``: as in
      :func:`tool_function`.
    - ``carry_out``: called as ``carry_out(data_root, run_id, identity,
      request)`` with the data root, a :class:`pathlib.Path`, the checked
      ``run_id``, the :class:`hilclaw.journal.Identity` formed from ``step``
      and the request, and the request as the caller gave it; once in a call,
      and only after both checks passed, the data root was obtained and
      :func:`hilclaw.instance.layout_version_of` returned for that data root
      and that ``run_id``.
    - ``others``: further arguments by name, meant for the callables
      ``carry_out`` uses. Each is checked for being callable when built and
      is not used otherwise.

    Raises, in this order: :class:`ValueError` when ``step`` is no name;
    :class:`TypeError` when ``numbers`` is no ``tuple`` and
    :class:`ValueError` when it is no such prefix; :class:`TypeError`, with a
    message that starts with the name of the argument, for the first of
    ``carry_out``, ``source``, ``check`` and the ``others`` in the order given
    that is not callable. Building calls none of them.

    The function returned takes one request and returns what ``carry_out``
    returns. It raises ``ToolFailure`` of kind ``invalid_request`` with a
    message that names the member, or says that the request is no object; of
    one of the four kinds ``run_file_missing``, ``run_file_unreadable``,
    ``run_file_invalid`` and ``run_file_unsupported`` when the stamp cannot be
    had, with ``carry_out`` not called (the module docstring has the cases);
    and otherwise what ``check``, :func:`hilclaw.data_root_source.obtain`, the
    read of the stamp and ``carry_out`` raise, unchanged. It does not modify
    the request itself; what ``check`` and ``carry_out`` do with it is theirs.

    What it does not do: it calls no function of
    :mod:`hilclaw.journaled_step`, so the lookup, the two step lines and the
    step are the part of ``carry_out``, and nothing here checks that
    ``carry_out`` carries them out. The function returned is the tool function
    of a journaled tool in the sense of ADR-0015 decision 5 only if
    ``carry_out`` carries out the step by the sequence of ADR-0011 decision 3.
    It registers nothing and names no tool.
    """
    journal.step_identity(step, 1)
    parts = {"carry_out": carry_out, "source": source, "check": check, **others}
    _check_parts(numbers, parts)
    return _function((step,), lambda request: step, numbers, carry_out, source, check)


def stepped_function(*, steps, step_of, numbers, carry_out, source, check, **others):
    """Return a function of one request whose ``step`` follows from that request.

    The function returned is that of :func:`checked_function` but for the
    ``step`` of the identity, which is no argument here: it is obtained from
    each request, so two requests that differ only in what it follows from
    are two identities.

    - ``steps``: the ``step`` names of the tool's contract, a non-empty
      ``tuple`` of distinct names.
    - ``step_of``: called as ``step_of(request)``, once in a call, after the
      five members were checked and ``check`` returned, and before the data
      root is asked. It returns one of ``steps``, exactly a ``str``. It is
      not called for a request refused before. No member ``step`` of a
      request is read here (ADR-0015 decision 4).
    - ``numbers``, ``carry_out``, ``source``, ``check``, ``others``: as in
      :func:`checked_function`. The identity ``carry_out`` is handed holds
      the ``step`` that ``step_of`` returned, and the ``execution`` and the
      numbers as they were checked before ``check`` was called.

    Raises, in this order: :class:`TypeError` when ``steps`` is no ``tuple``
    and :class:`ValueError` when it is empty, when one of them is no name
    (for the first such, the error of :func:`hilclaw.journal.step_identity`)
    or when two are equal; then what :func:`checked_function` raises for
    ``numbers``; then :class:`TypeError` for the first of ``step_of``,
    ``carry_out``, ``source``, ``check`` and the ``others`` in the order
    given that is not callable. Building calls none of them.

    The function returned raises what that of :func:`checked_function`
    raises, and besides: what ``step_of`` raises, unchanged, and
    :class:`RuntimeError` when ``step_of`` returned what is none of
    ``steps``, an instance of a subclass of ``str`` included. In both cases
    the data root was not asked, nothing was read and ``carry_out`` was not
    called. Such a value is a defect of the contract and not of the caller,
    so it is no ``invalid_request``; at :func:`hilclaw.tools.call` it is
    ``tool_crashed``. With one ``step`` in ``steps`` the function returned
    answers a caller as that of :func:`checked_function` with that ``step``.
    """
    _check_steps(steps)
    parts = {"step_of": step_of, "carry_out": carry_out, "source": source}
    _check_parts(numbers, parts | {"check": check, **others})
    return _function(steps, step_of, numbers, carry_out, source, check)


def _check_steps(steps):
    if type(steps) is not tuple:
        raise TypeError(f"steps must be a tuple, got {type(steps).__name__}")
    if not steps:
        raise ValueError("steps must name at least one step")
    for step in steps:
        journal.step_identity(step, 1)
    if len(set(steps)) != len(steps):
        raise ValueError(f"steps must be distinct, got {steps}")


def _check_parts(numbers, parts):
    if type(numbers) is not tuple:
        raise TypeError(f"numbers must be a tuple, got {type(numbers).__name__}")
    if numbers != _NUMBERS[: len(numbers)]:
        raise ValueError(f"numbers must be a prefix of {_NUMBERS}, got {numbers}")
    for name, value in parts.items():
        if not callable(value):
            raise TypeError(f"{name} must be callable, got {type(value).__name__}")


def _function(steps, step_of, numbers, carry_out, source, check):
    def journaled(request):
        run_id, identity = _checked(steps[0], numbers, request)
        check(request)
        identity = identity._replace(step=_step(steps, step_of(request)))
        data_root = data_root_source.obtain(source)
        with run_files.reading(data_root, run_id, "instance.json", _STAMP_KINDS):
            instance.layout_version_of(data_root, run_id)
        return carry_out(data_root, run_id, identity, request)

    return journaled


def _step(steps, step):
    if type(step) is not str or step not in steps:
        got = repr(step) if type(step) is str else type(step).__name__
        raise RuntimeError(f"step_of must return one of {steps}, got {got}")
    return step


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
