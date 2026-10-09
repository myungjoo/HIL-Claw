"""One journaled step of a run, carried out by the rule of the repeated call (ADR-0011).

``ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`` says that the
tool layer establishes the state of the identity of a journaled step from the
log before the step starts and then, for no line, appends the start line, runs
the step and appends the end line; for an ended step returns what the end line
holds and runs nothing; and for an open step reports that it is open (decision
3, "The repeated call", with decisions 2, 4 and 7). :func:`run` is that
sequence for any step, over :func:`hilclaw.run_journal.read_state`,
:func:`hilclaw.events.read`, :func:`hilclaw.journal.step_state` and
:func:`hilclaw.events.append`.

Conventions of this module, which the records do not fix:

- The step is a callable without arguments. It returns the pair ``(spend,
  result)``, or raises :class:`StepFailed` when it ended without an outcome.
  An end line is written only for one of the two, so only with amounts the
  step stated itself (decision 7; sub-question 2 of OD-17 stays open).
- Any other exception out of the step passes through unchanged, a plain
  :class:`hilclaw.tools.ToolFailure` and a :class:`BaseException` included,
  and no end line is appended: the step stays open, its outcome and amount
  unknown (the second death point).
- An outcome the end line cannot hold raises :class:`InvalidOutcomeError` and
  no end line is appended, so the step stays open: a line the fold refuses is
  never written. It is checked as :func:`hilclaw.journal.check_step` checks an
  end line and as :func:`hilclaw.tools.check_json_object` checks a result, and
  it is looked up once as :func:`hilclaw.journal.step_state` copies what an
  end line holds, at the call depth of the lookup of a repeated call.
- The checks come in this order: ``run_id``, ``identity``, that ``step`` is
  callable (:class:`TypeError`), then ``data_root`` and the files.
- :func:`run_prepared` is :func:`run` with one place more, between the lookup
  and the start line: there the tool function of a journaled HW tool selects
  its backend (ADR-0016 decision 2), after the lookup so that an ended or an
  open identity is answered from the log alone, and before the start line so
  that a call that fails there has not started the step and leaves no line.
- Where the state is read (decision 6, last bullet): for an identity whose
  ``round`` is the ``round`` stored in ``STATE.json`` the stored view and the
  tail decide, and the lines before the stored position are not interpreted.
  For every other identity (another round, or none) the log is read from its
  first line. Whether such steps exist or need an index is open (sub-question
  1 of OD-17). A stored position beyond the log is found on both paths,
  before anything is appended: an append would hide it.
- ``STATE.json`` is required as :func:`hilclaw.run_journal.read_state`
  requires it. What the lookup finds in ``STATE.json`` or in the log that
  ADR-0019 decisions 3 and 4 count as a situation is answered with a
  ``ToolFailure`` of one of the four kinds of its decision 2, chained to the
  error it answers for; this call then appended nothing and did not call the
  step. ``run_file_missing``: no ``STATE.json`` (no run directory included),
  or a data root that is no existing directory at a read. ``run_file_invalid``:
  an invalid ``STATE.json``, a damaged complete line among the lines read, a
  step line among them that breaks ADR-0011, a stored position beyond the log,
  a path of either file that is no regular file. ``run_file_unsupported``:
  another ``schema_version`` of ``STATE.json`` or of a line read.
  ``run_file_unreadable``: any other :class:`OSError` of either read.
- A log that is not there below a data root that is there is no such
  situation, also when it goes between the check and the read of one call:
  the log is then read once more, so that the reader says what is there, and
  only when it goes again in that read the lookup goes on with no line read.
- Only the reads and the lookup are answered this way: the same classes out
  of ``before_start``, out of the step or out of an append are not. Out of an
  append an :class:`OSError` and a :class:`hilclaw.events.CorruptEventsError`
  are answered with the kind of the append (below) and the others pass
  through.
- The message of such a failure starts with the path of the file relative to
  the data root, ``runs/<run_id>/STATE.json`` or ``runs/<run_id>/events.ndjson``
  (ADR-0019 decision 6); nothing may depend on the rest of its wording.
- A failed append of a step line is answered with a ``ToolFailure`` of one of
  the two kinds of ADR-0026 decision 3, chained to the error it answers for.
  ``start_line_failed``: the append of the start line of this call failed, and
  this call did not call the step and appended no end line.
  ``end_line_failed``: the append of the end line of this call failed; this
  call ran the step to its end, and neither a ``result`` nor the ``failure``
  of the step is returned or raised in its place. Neither kind says which
  state the identity is in: where the log is as this call left it, it has no
  line or is open after the first, and is open or ended after the second
  (:mod:`hilclaw.events`: a failure can come after the line feed). The call
  does not read the log again and does not try the append again.
- A failed append is an :class:`OSError` or a
  :class:`hilclaw.events.CorruptEventsError` out of one of the two calls of
  :func:`hilclaw.events.append`, and only there (ADR-0026 decisions 1 and 6).
  Everything else an append raises passes through unchanged, a
  :class:`hilclaw.events.InvalidEventError` included.
- The message of such a failure starts with ``runs/<run_id>/events.ndjson``
  and carries nothing of the outcome (ADR-0026 decision 6): the message of a
  ``CorruptEventsError`` is used as it is, and for an ``OSError`` it is
  composed from the class and the text of the system, without the path the
  system gave. Nothing may depend on the rest of its wording.
- A first call returns the ``result`` as the end line holds it, the copy
  :func:`hilclaw.events.append` returns; a failure is raised as a
  ``ToolFailure`` of the ``kind`` and ``message`` on the line, with no cause
  attached. A repeated call gives equal values from the first end line.
- An open step is reported with a ``ToolFailure`` of kind :data:`KIND_STEP_OPEN`,
  which is reserved for the open step (ADR-0015 decision 2). A step that
  states it anyway is not detected and is answered like any other ended step.
- A torn tail is skipped by the read and removed by the append, as
  :mod:`hilclaw.events` does it; nothing is added to that.

Limits (decision 9): two turns at once can both find no line and both start
the step, since no lock is taken and the lookup and the append are not atomic.
A death between the outcome and the completed end line leaves the step open
and its outcome lost. An amount is what the step stated: nothing verifies it.
A step about a round above the stored ``round`` (ADR-0012 decision 3: no such
round has begun) is found only until that round is the stored one: its lines
then lie before the stored position, the tail shows no line and the step runs
again, counted twice and not reported. How deeply a ``result`` may be nested
depends on the interpreter and on the depth of the call: a lookup made from a
deeper call than the one that wrote the line can fail to copy it.

It is not a tool and not a hook: the tool function of a journaled tool, built
by :mod:`hilclaw.journaled_tool` or :mod:`hilclaw.hw_tool`, calls it (ADR-0015
decision 5).
It names no step, no axis and no result member, derives no identity and raises
no ``execution``, runs no open or ended step again, compares no total with a
limit, writes no ``STATE.json`` and reads no configuration (OD-10, OD-19,
OD-23, the rest of OD-17).
"""

from hilclaw import (
    events,
    journal,
    layout,
    run_files,
    run_journal,
    run_state,
    tools,
)

KIND_STEP_OPEN = tools.KIND_STEP_OPEN

_NUMBERS = ("round", "candidate", "attempt")
_STATE_KINDS = {
    run_journal.MissingStateError: tools.KIND_RUN_FILE_MISSING,
    run_state.InvalidStateError: tools.KIND_RUN_FILE_INVALID,
    run_state.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
}
_APPEND_KINDS = {
    journal.STEP_STARTED: tools.KIND_START_LINE_FAILED,
    journal.STEP_ENDED: tools.KIND_END_LINE_FAILED,
}
_LOG_KINDS = {
    events.CorruptEventsError: tools.KIND_RUN_FILE_INVALID,
    events.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
}


class StepFailed(Exception):
    """Raised by a step that ended without an outcome: its amounts and the tool failure.

    ``spend`` is what the step consumed, ``kind`` a name and ``message`` a
    ``str``, as a ``failure`` of an end line holds them. Nothing is checked
    here: :func:`run` checks the three before it appends the end line.
    """

    def __init__(self, spend, kind, message):
        super().__init__(spend, kind, message)
        self.spend = spend
        self.kind = kind
        self.message = message


class InvalidOutcomeError(ValueError):
    """What a step returned or raised cannot stand on an end line; the message says why."""


def run(data_root, run_id, identity, step):
    """Carry out the journaled step ``identity`` of the run ``run_id``; return its ``result``.

    ``identity`` is a :class:`hilclaw.journal.Identity` given by the caller and
    ``step`` a callable without arguments that performs the step. The state of
    the identity is established first, from ``STATE.json`` and the log:

    - no line: the start line is appended and complete before ``step`` is
      called, once; the end line is appended as soon as ``step`` returned
      ``(spend, result)`` or raised :class:`StepFailed`, with that ``spend``.
    - ended: ``step`` is not called and nothing is appended; the answer is
      what the first end line holds.
    - open: ``step`` is not called and nothing is appended.

    Returns the ``result``, a ``dict``. Raises
    :class:`hilclaw.tools.ToolFailure` with the ``kind`` and ``message`` of the
    ``failure`` when the step ended without an outcome, and of kind
    :data:`KIND_STEP_OPEN`, naming the identity, when the step is open.

    Raises also :class:`hilclaw.layout.InvalidPathValueError` for ``run_id``,
    :class:`hilclaw.journal.JournalError` or
    :class:`hilclaw.events.InvalidEventError` for ``identity`` and
    :class:`TypeError` for ``step``, each before any file is read; a
    ``ToolFailure`` of kind ``run_file_missing``, ``run_file_unreadable``,
    ``run_file_invalid`` or ``run_file_unsupported`` for what the lookup finds
    in ``STATE.json`` or in the log (ADR-0019 decisions 2 to 4; the module
    docstring has the cases), with nothing appended and ``step`` not called;
    a ``ToolFailure`` of kind ``start_line_failed`` or ``end_line_failed`` for
    a failed append of the start line or of the end line (ADR-0026 decision 3;
    the module docstring has the classes), after the first with ``step`` not
    called and after the second with ``step`` called and no outcome returned;
    :class:`InvalidOutcomeError` for an outcome of ``step`` that an end line
    cannot hold; and everything else :func:`hilclaw.events.append` raises and
    what ``step`` raises, unchanged.
    """
    return run_prepared(data_root, run_id, identity, step, before_start=_nothing)


def run_prepared(data_root, run_id, identity, step, *, before_start):
    """Carry out the journaled step ``identity`` as :func:`run` does, after ``before_start``.

    ``before_start`` is a callable without arguments. It is called exactly
    once and only for an identity with no line, after the state was
    established and before the start line is appended; what it returns is not
    used, so what it prepared reaches ``step`` through the caller. For an ended
    or an open identity it is not called.

    What ``before_start`` raises passes through unchanged, whatever it is:
    nothing was appended and ``step`` was not called, so the identity still has
    no line and the same call can be repeated.

    Everything else is as in :func:`run`: the ``ToolFailure`` of one of the
    four kinds of ADR-0019 for what the lookup finds is raised before
    ``before_start`` is called. Raises also :class:`TypeError` when
    ``before_start`` is not callable, ``None`` included, after the check of
    ``step`` and before any file is read.
    """
    layout.check_run_id(run_id)
    journal.step_state(identity, ())
    for name, value in (("step", step), ("before_start", before_start)):
        if not callable(value):
            raise TypeError(f"{name} must be callable, got {type(value).__name__}")
    found = _state(data_root, run_id, identity)
    if found.state is journal.State.OPEN:
        raise tools.ToolFailure(KIND_STEP_OPEN, f"{_named(identity)} is open")
    if found.state is journal.State.ENDED:
        return _answer(found.result, found.failure)
    before_start()
    numbers = dict(zip(_NUMBERS, identity[2:]))
    data = {"step": identity.step, "execution": identity.execution}
    _append(data_root, run_id, journal.STEP_STARTED, dict(data), numbers)
    try:
        outcome = _outcome(step())
    except StepFailed as failed:
        failure = {"kind": failed.kind, "message": failed.message}
        outcome = {"spend": failed.spend, "failure": failure}
    end_data = _checked_end(numbers, data | outcome)
    end = _append(data_root, run_id, journal.STEP_ENDED, end_data, numbers)
    return _answer(end["data"].get("result"), end["data"].get("failure"))


def _nothing():
    return None


def _append(data_root, run_id, kind, data, numbers):
    try:
        return events.append(data_root, run_id, kind, data, **numbers)
    except events.CorruptEventsError as error:
        raise tools.ToolFailure(_APPEND_KINDS[kind], str(error)) from error
    except OSError as error:
        file = run_files.relative(run_id, "events.ndjson")
        reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
        message = f"{file}: the line could not be appended: {reported}"
        raise tools.ToolFailure(_APPEND_KINDS[kind], message) from error


def _state(data_root, run_id, identity):
    with run_files.reading(data_root, run_id, "STATE.json", _STATE_KINDS):
        state = run_journal.read_state(data_root, run_id)
    view = state.budget_spent if identity.round == state.round else journal.EMPTY
    file = run_files.relative(run_id, "events.ndjson")
    with run_files.reading(data_root, run_id, "events.ndjson", _LOG_KINDS):
        lines, read = _lines(data_root, run_id, view.position)
        stored = state.budget_spent.position
        if lines < stored:
            end = f"the end of the log, complete lines: {lines}"
            raise events.PositionBeyondLogError(
                f"{file}: position {stored} is beyond {end}"
            )
    try:
        return journal.step_state(identity, read, view)
    except journal.JournalError as error:
        message = f"{file}: {error}"
        raise tools.ToolFailure(tools.KIND_RUN_FILE_INVALID, message) from error


def _lines(data_root, run_id, position):
    for last in (False, True):
        try:
            read = events.read(data_root, run_id, position).events
        except run_files.NOT_THERE:
            if not run_files.data_root_is_there(data_root):
                raise
            if last:
                return 0, []
        else:
            return position + len(read), read


def _answer(result, failure):
    if failure is not None:
        raise tools.ToolFailure(failure["kind"], failure["message"])
    return result


def _named(identity):
    numbers = zip(_NUMBERS, identity[2:])
    target = "".join(f" {name} {value}" for name, value in numbers if value is not None)
    return f"the step {identity.step} execution {identity.execution}{target}"


def _outcome(returned):
    if type(returned) is not tuple or len(returned) != 2:
        got = type(returned).__name__
        raise InvalidOutcomeError(
            f"step: must return the pair (spend, result), got {got}"
        )
    return dict(zip(("spend", "result"), returned))


def _checked_end(numbers, data):
    probe = {"schema_version": events.SCHEMA_VERSION, "time": "2026-01-01T00:00:00Z"}
    probe.update({name: value for name, value in numbers.items() if value is not None})
    probe.update({"kind": journal.STEP_ENDED, "data": data})
    try:
        identity = journal.identity_of(probe)
        tools.check_json_object(data)
        journal.step_state(identity, [probe])
    except RecursionError:
        raise InvalidOutcomeError(
            "data: is nested too deeply to copy at this call depth"
        ) from None
    except ValueError as error:
        raise InvalidOutcomeError(str(error)) from None
    return data
