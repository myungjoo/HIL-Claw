"""Journal of a journaled step and the spend of a run, over parsed event lines (ADR-0011).

``ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`` fixes the two
kinds around a journaled step and their ``data`` (decisions 3 and 7), the
identity of a step (3), its three states (3 and 4) and the fold of lines into
a spend view (6). This module is those rules as pure functions of lines that
are already parsed, as :func:`hilclaw.events.read` returns them.

Conventions of this module, which ADR-0011 does not fix:

- The values returned are Python values in memory. None of them is the form
  of ``budget_spent`` in ``STATE.json`` (PLAN P1-8).
- ``lines`` is any iterable of events in the order of the file, read once.
  Every line is checked with :func:`hilclaw.events.validate` and, when it is a
  step line, as by :func:`check_step`. The first line that fails raises the
  error of that check with ``line <number>:`` in front, and nothing is
  returned: no line is skipped and none is counted in part. This is not a rule
  about damage (ADR-0006 decision 6 defines damage for the envelope only).
- A line number counts from 1 and continues the position of the view given:
  it is the number in the file when that view is the view of the lines before.
- ``failure`` is read as an object with exactly ``kind``, a name, and
  ``message``, a ``str``. ``result`` is a ``dict``; its members are not looked
  at. That ``data`` is strict JSON is the event module's concern.
- A name is that of ADR-0001 and an integer exactly an ``int`` of at most
  :data:`hilclaw.keys.MAX_INTEGER`. A total is the exact sum and may be larger.
- No argument is modified and nothing returned shares mutable state with one.

It reads and writes no file, appends no line, runs no step, names no step, no
axis and no result member, compares no total with a limit and decides nothing
about an open step (OD-10, OD-19, the rest of OD-17 and of OD-18).
"""

import copy
import enum
import re
import reprlib
from collections.abc import Mapping
from types import MappingProxyType
from typing import NamedTuple

from hilclaw import events, keys

STEP_STARTED = "step_started"
STEP_ENDED = "step_ended"

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_ENDED = ("step", "execution", "spend", "result", "failure")
_MEMBERS = {STEP_STARTED: _ENDED[:2], STEP_ENDED: _ENDED}
_NUMBERS = ("round", "candidate", "attempt")


class JournalError(ValueError):
    """A step line, an identity or a view breaks a rule; the message names the member."""


class Identity(NamedTuple):
    """What makes two calls the same step (decision 3); ``None`` is an absent envelope number."""

    step: str
    execution: int
    round: int | None = None
    candidate: int | None = None
    attempt: int | None = None


class SpendView(NamedTuple):
    """Spend view (decision 1): total per axis, number of lines folded, the open identities."""

    totals: Mapping
    position: int
    open_steps: frozenset


Problem = enum.Enum("Problem", "END_NOT_OPEN START_REPEATED")
State = enum.Enum("State", "NO_LINE OPEN ENDED")


class Report(NamedTuple):
    """A line the fold counted and reports (decision 6, *Disagreement*); see :func:`fold`."""

    line: int
    identity: Identity
    problem: Problem


class StepState(NamedTuple):
    """One of the three states of decision 4; for ``ENDED``, what the end line holds."""

    state: State
    result: dict | None = None
    failure: dict | None = None
    spend: dict | None = None


EMPTY = SpendView(MappingProxyType({}), 0, frozenset())


def check_step(event):
    """Check ``event``, a parsed step line, against the table of decision 3; return ``None``.

    The envelope is checked with :func:`hilclaw.events.validate`, whose errors
    pass through. ``data`` must hold exactly ``step`` (a name) and
    ``execution`` (an integer from 1) and, for ``step_ended``, ``spend`` (an
    object from an axis name to an integer from 0, possibly empty) and exactly
    one of ``result`` and ``failure``. Raises :class:`JournalError` for the
    first rule found broken, which includes an event of any other kind.
    """
    identity_of(event)


def identity_of(event):
    """Return the :class:`Identity` of the step line ``event``, checked as by :func:`check_step`."""
    identity = _checked(event)
    if identity is None:
        _fail("kind", f"{STEP_STARTED} or {STEP_ENDED}", event["kind"])
    return identity


def step_identity(step, execution, round=None, candidate=None, attempt=None):
    """Return the :class:`Identity` of these values, for a caller that names a step to look up.

    The values are checked as those of a start line (``candidate`` only with
    ``round``, ``attempt`` only with ``candidate``), with the same errors:
    :class:`hilclaw.events.InvalidEventError` for an envelope number.
    """
    event = {"schema_version": events.SCHEMA_VERSION, "time": "2026-01-01T00:00:00Z"}
    numbers = zip(_NUMBERS, (round, candidate, attempt))
    event.update({name: value for name, value in numbers if value is not None})
    data = {"step": step, "execution": execution}
    return identity_of(event | {"kind": STEP_STARTED, "data": data})


def fold(lines, view=EMPTY):
    """Fold ``lines`` into ``view``; return ``(view, reports)`` after them (decisions 6 and 7).

    ``view`` is the spend view of the lines before ``lines``; :data:`EMPTY` is
    that of no line. In the :class:`SpendView` returned, ``totals`` has every
    axis an end line named, with the sum of its amounts (possibly 0),
    ``position`` has grown by the number of lines of every kind, and
    ``open_steps`` holds the identities whose last step line is a start line.
    Folding a tail from the view of its prefix gives the view of the whole.

    ``reports`` is a tuple of :class:`Report` in the order of the lines;
    nothing is raised for such a line. ``END_NOT_OPEN``: an end line whose
    identity is not open at that line (a second end line, one without a start
    line, or one whose start line the view does not show); its amounts are
    counted. ``START_REPEATED``: a start line whose identity is open, or ended
    on one of ``lines``; the identity is open afterwards. A view holds no
    ended identity, so a start line after an end line that lies before
    ``lines`` opens its identity unreported.

    Raises :class:`JournalError` for a malformed ``view``, before any line is
    read, and the error of the line check for a line that fails it.
    """
    totals, start, open_steps = _checked_view(view)
    position = start
    ended, reports = set(), []
    for position, event in enumerate(lines, start + 1):
        identity = _checked_line(position, event)
        if identity is None:
            continue
        if event["kind"] == STEP_STARTED:
            if identity in open_steps or identity in ended:
                reports.append(Report(position, identity, Problem.START_REPEATED))
            open_steps.add(identity)
            continue
        if identity not in open_steps:
            reports.append(Report(position, identity, Problem.END_NOT_OPEN))
        open_steps.discard(identity)
        ended.add(identity)
        for axis, amount in event["data"]["spend"].items():
            totals[axis] = totals.get(axis, 0) + amount
    folded = SpendView(MappingProxyType(totals), position, frozenset(open_steps))
    return folded, tuple(reports)


def step_state(identity, lines, view=EMPTY):
    """Return the :class:`StepState` of ``identity`` after ``lines`` (decisions 3 and 4).

    ``ENDED`` when ``lines`` holds an end line of the identity, with copies of
    what the first such line holds: later end lines never change the answer.
    Otherwise ``OPEN`` when ``lines`` holds its start line or ``view`` lists
    it as open, and ``NO_LINE`` when neither. Every line is read and checked.

    Limit (decision 6, sub-question 1 of ADR-0011): a view does not show an
    identity that ended before its position. The answer is right for a step
    whose lines lie after the position of ``view``, as those of the round in
    progress, and for :data:`EMPTY` with the whole log.

    Raises as :func:`fold` does, :class:`JournalError` for an ``identity`` of
    another type and the error of :func:`step_identity` for values it refuses.
    """
    _checked_identity(identity, "identity")
    _, position, open_steps = _checked_view(view)
    started = identity in open_steps
    end = None
    for number, event in enumerate(lines, position + 1):
        if _checked_line(number, event) != identity:
            continue
        started = True
        if end is None and event["kind"] == STEP_ENDED:
            end = copy.deepcopy(event["data"])
    if end is None:
        return StepState(State.OPEN if started else State.NO_LINE)
    return StepState(State.ENDED, *map(end.get, ("result", "failure", "spend")))


def _fail(place, rule, value):
    try:
        got = reprlib.repr(value)
    except ValueError:
        got = "a value too long to show"
    raise JournalError(f"{place}: must be {rule}, got {type(value).__name__} {got}")


def _name(place, value):
    if type(value) is not str or not _NAME.fullmatch(value):
        _fail(place, f"a name matching {_NAME.pattern}", value)


def _integer(place, value, least):
    if type(value) is not int or not least <= value <= keys.MAX_INTEGER:
        _fail(place, f"an int from {least} to {keys.MAX_INTEGER}", value)


def _checked(event):
    events.validate(event)
    kind, data = event["kind"], event["data"]
    if kind not in _MEMBERS:
        return None
    for name in data:
        if name not in _MEMBERS[kind]:
            _fail("data", f"an object of a {kind} line, without the member", name)
    for name in _MEMBERS[kind][:3]:
        if name not in data:
            raise JournalError(f"data: lacks the member {name}")
    _name("data.step", data["step"])
    _integer("data.execution", data["execution"], 1)
    if kind == STEP_ENDED:
        _check_end(data)
    return Identity(data["step"], data["execution"], *map(event.get, _NUMBERS))


def _check_end(data):
    if ("result" in data) == ("failure" in data):
        raise JournalError("data: must hold exactly one of result and failure")
    if type(data["spend"]) is not dict:
        _fail("data.spend", "an object", data["spend"])
    for axis, amount in data["spend"].items():
        _name("data.spend: member name", axis)
        _integer(f"data.spend.{axis}", amount, 0)
    if "result" in data:
        if type(data["result"]) is not dict:
            _fail("data.result", "an object", data["result"])
        return
    failure = data["failure"]
    if type(failure) is not dict or set(failure) != {"kind", "message"}:
        _fail("data.failure", "an object with exactly kind and message", failure)
    _name("data.failure.kind", failure["kind"])
    if type(failure["message"]) is not str:
        _fail("data.failure.message", "a str", failure["message"])


def _checked_line(number, event):
    try:
        return _checked(event)
    except (ValueError, events.UnsupportedVersionError) as error:
        raise type(error)(f"line {number}: {error}") from None


def _checked_identity(value, place):
    if type(value) is not Identity:
        _fail(place, "an Identity", value)
    step_identity(*value)


def _checked_view(view):
    if type(view) is not SpendView:
        _fail("view", "a SpendView", view)
    totals, position, open_steps = view
    if type(position) is not int or position < 0:
        _fail("view.position", "an int from 0", position)
    if not isinstance(totals, Mapping):
        _fail("view.totals", "a mapping", totals)
    for axis, total in totals.items():
        _name("view.totals: member name", axis)
        if type(total) is not int or total < 0:
            _fail(f"view.totals.{axis}", "an int from 0", total)
    if type(open_steps) not in (frozenset, set):
        _fail("view.open_steps", "a frozenset or a set", open_steps)
    for identity in open_steps:
        try:
            _checked_identity(identity, "member")
        except ValueError as error:
            raise JournalError(f"view.open_steps: {error}") from None
    return dict(totals), position, set(open_steps)
