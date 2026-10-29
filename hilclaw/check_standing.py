"""The standing of one attempt at one execution point of ``correctness.check`` (ADR-0110).

``ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`` is
the rule; a decision cited by its number alone is one of that record. The
module renders its decisions 2, 3 and 5 as one pure function of parsed lines:

* :class:`Standing`: the three standings of decision 3.
* :data:`UNSTARTED_KINDS`: the kinds of class (i) of decision 2, "no
  executable of the check was started". Every other ``failure`` kind is of
  class (ii), "a verdict may have existed", an unknown kind included: "any
  kind a later record adds unless that record places its situations in (i)".
* :func:`standing`: the standing of the attempt ``(round, candidate,
  attempt)`` at the point ``step`` after the lines given. Every end line of
  that identity counts, an end line without a start line and a second end
  line of one identity included (decision 2). Not verified when a counting
  result is ``"fail"`` or ``"broken"``; else verified when one is ``"pass"``,
  no identity of the point is open (a start line and no end line) and no end
  line holds a ``failure`` of class (ii); else undetermined (decision 3). A
  ``failure`` of class (i) counts neither way. Only the lines of the point's
  ``step`` count (decision 5), and the order of the lines does not matter.
* :data:`STEPS_OF` and :func:`point_standing`: the standing of the attempt
  at a point whose lines are those of its one ``step`` value,
  ``correctness_check_sim_v2`` or ``correctness_check_board_v2``, the value
  of every contract, as the readers of a check take it
  (``ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md``
  decisions 2 and 8, in place of the two values per point of ADR-0178
  decision 1). A line under a value ADR-0183 retired is neither read nor
  refused: it is a line of another step (ADR-0100 decision 5).

Choices that are this module's own and no rule of the record:

* The names of the module, of the function and of its public values. The
  record names none as binding (Consequences).
* ``lines`` is any iterable of events in the form that
  :func:`hilclaw.events.read` returns them, read once. Every line is checked
  with :func:`hilclaw.events.validate` and, when it is a step line, as by
  :func:`hilclaw.journal.identity_of`. The first line that fails raises the
  error of that check with ``line <number>:`` (from 1) in front, as
  :func:`hilclaw.journal.fold` does, and no standing is returned.
* ``step`` must be one of :data:`hilclaw.check_identity.STEPS`, exactly a
  ``str``. The three numbers are all required and are checked as
  :func:`hilclaw.journal.step_identity` checks them.
* Of a result of a matching end line only ``outcome`` is read. A result whose
  ``outcome`` is missing, not a ``str`` or not one of
  :data:`hilclaw.check_result.PASS`, :data:`~hilclaw.check_result.FAIL` and
  :data:`~hilclaw.check_result.BROKEN` is refused with
  :class:`hilclaw.journal.JournalError` naming the line: the record does not
  say what such a line means, and :mod:`hilclaw.journal` does not look into
  results.
* No argument is modified.

What the module does not do: it decides nothing of the second part of OD-18
sub-question ⑭ (what keeps a caller from asking for a further check). It
appends no line and reads no file. Its consumers are the tool ``checks.read``
(:mod:`hilclaw.checks_tool`, ADR-0131 decision 3), which folds the standing
into its read of a run's log, ``verdicts.write`` and
:mod:`hilclaw.spec_feedback`. It merges no two
points, judges no result again and sorts no result by cause. It does not
check that the run is one of the first case or one whose hw_profile names the
mock: that scope is the caller's (decision 1).
"""

import enum
import reprlib

from hilclaw import check_failure, check_identity, check_result, events, journal


class Standing(enum.Enum):
    """The three standings of ADR-0110 decision 3: words of that record, not values of any file."""

    NOT_VERIFIED = "not verified"
    VERIFIED = "verified"
    UNDETERMINED = "undetermined"


#: The ``failure`` kinds of class (i) of ADR-0110 decision 2; every other kind is of class (ii).
UNSTARTED_KINDS = frozenset(
    {
        check_failure.KIND_NO_KERNEL_SOURCE,
        check_failure.KIND_KERNEL_SOURCE_UNREADABLE,
        check_failure.KIND_BUILD_DIRECTORY_UNUSABLE,
        check_failure.KIND_BUILD_INPUT_MISSING,
        check_failure.KIND_COMPILER_UNAVAILABLE,
        check_failure.KIND_BUILD_OUTPUT_MISSING,
        check_failure.KIND_EXECUTABLE_UNSTARTABLE,
    }
)

#: The ``step`` values whose lines are those of each point, a one-item tuple of its v2 value (ADR-0183 decision 8).
STEPS_OF = {
    check_identity.SIM: (check_identity.STEP_SIM,),
    check_identity.BOARD: (check_identity.STEP_BOARD,),
}

_OUTCOMES = (check_result.PASS, check_result.FAIL, check_result.BROKEN)
_STEP_KINDS = (journal.STEP_STARTED, journal.STEP_ENDED)


def standing(lines, step, round, candidate, attempt):
    """Return the :class:`Standing` of the attempt ``(round, candidate, attempt)`` at ``step``.

    ``lines`` is an iterable of parsed events, as
    ``hilclaw.events.read(...).events`` holds them, and is read once. A line
    matches when it is a ``step_started`` or ``step_ended`` line whose
    ``step`` is ``step`` and whose ``round``, ``candidate`` and ``attempt``
    are the three given; every other line is checked and then ignored.

    Raises :class:`hilclaw.journal.JournalError` naming ``step`` for a
    ``step`` not in :data:`hilclaw.check_identity.STEPS`, and naming the
    number for a number that is missing (``None``); the error of
    :func:`hilclaw.journal.step_identity` for a number it refuses; and, with
    ``line <number>:`` in front, the error of the line check for the first
    line that fails it, or :class:`hilclaw.journal.JournalError` for a
    matching end line whose result has no admitted ``outcome``.
    """
    if type(step) is not str or step not in check_identity.STEPS:
        rule = f"one of {', '.join(check_identity.STEPS)}"
        raise journal.JournalError(_message("step", rule, step))
    return _standing(lines, (step,), round, candidate, attempt)


def point_standing(lines, point, round, candidate, attempt):
    """Return the :class:`Standing` of the attempt ``(round, candidate, attempt)`` at ``point``, over its ``step`` value.

    ``point`` is :data:`hilclaw.check_identity.SIM` or
    :data:`~hilclaw.check_identity.BOARD`, exactly a ``str``. The answer is
    that of :func:`standing` for the one value of :data:`STEPS_OF` for
    ``point`` (ADR-0183 decision 8).

    Raises :class:`hilclaw.journal.JournalError` naming ``point`` for a
    ``point`` that is not one of the two, and otherwise what
    :func:`standing` raises for the same arguments.
    """
    if type(point) is not str or point not in STEPS_OF:
        rule = f"one of {', '.join(STEPS_OF)}"
        raise journal.JournalError(_message("point", rule, point))
    return _standing(lines, STEPS_OF[point], round, candidate, attempt)


def _standing(lines, steps, round, candidate, attempt):
    numbers = (round, candidate, attempt)
    for name, value in zip(check_identity.NUMBERS, numbers):
        if value is None:
            raise journal.JournalError(f"{name}: is required")
    journal.step_identity(steps[0], 1, *numbers)
    started, ended = set(), set()
    failed = passed = blocked = False
    for number, event in enumerate(lines, 1):
        identity = _checked_line(number, event)
        if identity is None or identity.step not in steps or identity[2:] != numbers:
            continue
        if event["kind"] == journal.STEP_STARTED:
            started.add(identity)
            continue
        ended.add(identity)
        data = event["data"]
        if "failure" in data:
            blocked |= data["failure"]["kind"] not in UNSTARTED_KINDS
            continue
        outcome = _outcome(number, data["result"])
        failed |= outcome != check_result.PASS
        passed |= outcome == check_result.PASS
    if failed:
        return Standing.NOT_VERIFIED
    if passed and not blocked and started <= ended:
        return Standing.VERIFIED
    return Standing.UNDETERMINED


def _message(place, rule, value):
    try:
        got = reprlib.repr(value)
    except ValueError:
        got = "a value too long to show"
    return f"{place}: must be {rule}, got {type(value).__name__} {got}"


def _checked_line(number, event):
    try:
        events.validate(event)
        if event["kind"] not in _STEP_KINDS:
            return None
        return journal.identity_of(event)
    except (ValueError, events.UnsupportedVersionError) as error:
        raise type(error)(f"line {number}: {error}") from None


def _outcome(number, result):
    if "outcome" not in result:
        raise journal.JournalError(
            f"line {number}: data.result: lacks the member outcome"
        )
    outcome = result["outcome"]
    if type(outcome) is not str or outcome not in _OUTCOMES:
        rule = f"one of {', '.join(_OUTCOMES)}"
        message = _message("data.result.outcome", rule, outcome)
        raise journal.JournalError(f"line {number}: {message}")
    return outcome
