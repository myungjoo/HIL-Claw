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
- Where the state is read (decision 6, last bullet): for an identity whose
  ``round`` is the ``round`` stored in ``STATE.json`` the stored view and the
  tail decide, and the lines before the stored position are not interpreted.
  For every other identity (another round, or none) the log is read from its
  first line. Whether such steps exist or need an index is open (sub-question
  1 of OD-17). A stored position beyond the log raises
  :class:`hilclaw.events.PositionBeyondLogError` on both paths, before
  anything is appended: an append would hide it.
- ``STATE.json`` is required as :func:`hilclaw.run_journal.read_state`
  requires it. An error of that read, of the read of the log or of the lookup
  passes through: nothing is appended and the step is not called.
- A failed append passes through. After a failed start line the step is not
  called: the identity has no line, or is open, though nothing ran, when the
  failure came after the line feed (:mod:`hilclaw.events`; the opposite
  failure decision 2 accepts). After a failed end line the outcome is not
  returned in the place of the error: the step is open, or ended when the
  failure came after the line feed.
- A first call returns the ``result`` as the end line holds it, the copy
  :func:`hilclaw.events.append` returns; a failure is raised as a
  ``ToolFailure`` of the ``kind`` and ``message`` on the line, with no cause
  attached. A repeated call gives equal values from the first end line.
- An open step is reported with a ``ToolFailure`` of kind :data:`KIND_STEP_OPEN`.
  The kind is not reserved: a step that fails with it is answered like any
  other ended step, and the kind then does not tell the two apart.
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

It is not a tool and not a hook: nothing registers or calls it, and where the
append is placed stays open (the rest of OD-18). It names no step, no axis and
no result member, derives no identity and raises no ``execution``, runs no
open or ended step again, compares no total with a limit, writes no
``STATE.json`` and reads no configuration (OD-10, OD-19, OD-23, the rest of
OD-17).
"""

from hilclaw import events, journal, layout, run_journal, tools

KIND_STEP_OPEN = "step_open"

_NUMBERS = ("round", "candidate", "attempt")


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
    :class:`TypeError` for ``step``, each before any file is read;
    :class:`InvalidOutcomeError` for an outcome of ``step`` that an end line
    cannot hold; and what :func:`hilclaw.run_journal.read_state`,
    :func:`hilclaw.events.read`, :func:`hilclaw.journal.step_state`,
    :func:`hilclaw.events.append` and ``step`` raise, unchanged.
    """
    layout.check_run_id(run_id)
    journal.step_state(identity, ())
    if not callable(step):
        raise TypeError(f"step must be callable, got {type(step).__name__}")
    found = _state(data_root, run_id, identity)
    if found.state is journal.State.OPEN:
        raise tools.ToolFailure(KIND_STEP_OPEN, f"{_named(identity)} is open")
    if found.state is journal.State.ENDED:
        return _answer(found.result, found.failure)
    numbers = dict(zip(_NUMBERS, identity[2:]))
    data = {"step": identity.step, "execution": identity.execution}
    events.append(data_root, run_id, journal.STEP_STARTED, dict(data), **numbers)
    try:
        outcome = _outcome(step())
    except StepFailed as failed:
        failure = {"kind": failed.kind, "message": failed.message}
        outcome = {"spend": failed.spend, "failure": failure}
    end_data = _checked_end(numbers, data | outcome)
    end = events.append(data_root, run_id, journal.STEP_ENDED, end_data, **numbers)
    return _answer(end["data"].get("result"), end["data"].get("failure"))


def _state(data_root, run_id, identity):
    state = run_journal.read_state(data_root, run_id)
    view = state.budget_spent if identity.round == state.round else journal.EMPTY
    log = events.read(data_root, run_id, view.position)
    stored, lines = state.budget_spent.position, view.position + len(log.events)
    if lines < stored:
        file = f"runs/{run_id}/events.ndjson"
        end = f"the end of the log, complete lines: {lines}"
        raise events.PositionBeyondLogError(
            f"{file}: position {stored} is beyond {end}"
        )
    return journal.step_state(identity, log.events, view)


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
