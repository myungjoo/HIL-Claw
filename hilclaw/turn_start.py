"""The command-line entry of the turn loop for a first-case run (ADR-0122).

Command line: ``python -m hilclaw.turn_start <run_id>``. The run id is the
only argument and no option exists; nothing is read from standard input. This
is runtime code: on a runtime machine each turn starts the real ``claude`` and
spends plan usage. It is built and tested against a stub ``claude`` that the
tests write, never against a real one (D16).

**One start** asks :func:`hilclaw.data_root_source.obtain` of the data-root
source once (by default :func:`hilclaw.data_root_source.configured`, so
``hilclaw.config``), then calls :func:`hilclaw.turn_loop.run` once with
:func:`hilclaw.turn_definition.put` (its default ``SOURCE``), the prompt
:func:`prompt` builds from the run id, that data root, the given ``parent``
and, as ``run_id``, the same run id, which the loop writes into the ``Stop``
hook's arguments (ADR-0148 decision 4). It returns when the loop returns and
tells the starter why. Its order: the run id, standard output, the data root
and the loop's checks; the first step 1; the self-check, only when that step
answered a turn due; the first turn.

**The self-check** (ADR-0125): :func:`hilclaw.selfcheck.check` runs in this
process, at most once per start, with the start's data root as its
``data_root``, after the first step 1 answered a further turn (P1, P4 or owed
P2) and before the loop makes the session directory of the first turn; never
after a first step 1 that answers no turn, never in a start that ends with an
error before it, never between two turns. ``passed`` and ``no_call`` let the
first turn start. Every other outcome word, a report that is no ``dict`` or
names none, and an :class:`Exception` of the check start no turn and end the
start :data:`STOPPED_AT_CHECK`. Nothing is retried and nothing skips the
check.

**Step 1** (each call of the loop's ``further_turn``) makes exactly one
:func:`hilclaw.further_turn.classify` call on the run and answers from that
finding, from the finding of the step 1 before (kept for this start only) and
from the exit status of the last turn. In this order (ADR-0122 decision 5):

1. P2, ``run_status`` ``"over"``, with no commit owed: no further turn,
   :data:`RUN_OVER`, whatever the exit status was;
2. P3, any other ``run_status`` value: no further turn,
   :data:`UNKNOWN_RUN_STATUS` with the value;
3. an open state (decision 4), before the first turn as after any turn: no
   turn, :data:`OPEN_STATE` with the reason constant of
   :mod:`hilclaw.further_turn`, and with the exit status after a failed turn;
4. after a turn whose exit status is not 0, in P1, P4 or owed P2 (ADR-0127
   decision 6): no further turn, :data:`FAILED_TURN` with that status
   (decision 2);
5. after a turn whose exit status is 0, P1 both before and after it, P4
   both before and after it with the same ``round``, or owed P2 both before
   and after it: no further turn, :data:`UNCHANGED_TURN` (decision 3).
   ``round`` is compared for equality only, never with ``round_budget``.

Otherwise P1, P4 and owed P2 answer a further turn: before the first turn of
a start, after the self-check let it start (above), and after an exit-0 turn
that moved P1 to P4, changed ``round`` or reached owed P2.

**What the starter is told**, through the process only. Standard output gets
exactly one line, a compact JSON object in ASCII ended by one LF, whose member
``outcome`` names the kind; the datum is a further member:

=========================  ======  =========================================
``outcome``                status  further members
=========================  ======  =========================================
``run_over``               0       none
``unknown_run_status``     10      ``run_status``: the value as parsed
``failed_turn``            11      ``exit_status``
``unchanged_turn``         12      none
``open_state``             13      ``reason``, and ``exit_status`` as above
``stopped_at_check``       14      ``check``, ``check_fault`` or neither (below)
``error``                  20      ``error``: the error kind (below)
=========================  ======  =========================================

"Run over" alone has status 0. No status is 1 or 2, which the interpreter
uses. **The member** ``check`` holds the report of the check unchanged (the
``dict`` of :func:`hilclaw.selfcheck_report.build`) on every line of a start
in which a check ran and returned a ``dict``: on ``stopped_at_check`` and on any
outcome or error that follows a check that let the turn start. A start
without a check has no such member. After a fault of the check the line
holds ``check_fault``, the name of the exception's class, and no ``check``.
The check's ``no_claude`` is ``check.outcome`` under ``stopped_at_check``,
never the error kind ``no_claude``. The entry writes nothing to standard
error for an outcome, except after a fault of the check: one line naming the
exception's class and **never its text**, which may name a path. The error
gives one line of free text, which is never parsed. When the line cannot be
written to standard output, the status is :data:`EXIT_ERROR` and standard
error gets one line saying so. **What the turn sessions write** to their
standard output and standard error, a ``-p`` session's reply included, goes
to the entry's standard error as :mod:`hilclaw.turn_loop` passes it on,
unread, before the entry's own line if any (ADR-0175); it is not the entry's
text, tells no outcome and is never parsed, and its last line may lack a line
feed, so the entry's own line may follow it on the same line. Nothing of a
turn session reaches standard output, unless the starter gave the entry
one stream for both.

**The error** is told apart from the six outcomes, and no traceback reaches
the starter: ``bad_usage`` for not exactly one argument or an invalid run id
(:func:`hilclaw.layout.check_run_id`, checked before anything is read);
``no_data_root`` when the data-root source fails or names no existing
directory; ``no_claude`` for :class:`hilclaw.turn_loop.ClaudeNotFoundError`;
``fault`` for a standard output that the process does not have (seen before
any turn) and for any other :class:`Exception` of the loop or of reading the
run, a refused place (:class:`ValueError` of the loop) included.
:class:`KeyboardInterrupt` and :class:`SystemExit` are not caught.

**Kept from ADR-0122 decision 1**: the entry writes nothing into the run or
anywhere else on the starter's behalf (no ``run_status``, no file, no
notification), makes no judgement, calls no model beyond the check's own
session and is no FR-10 tool. It has no retry, retry count, pause or bound on
the number of turns.

**The limit it states and does not enforce** (ADR-0122 Consequences): until
the lock of two loops on one run exists (rest of OD-17), no starter may start
this entry on a run where a loop may still be running, so no schedule may
start it yet.

**The run of a turn** (ADR-0123): the prompt of every turn names the run by
its id and nothing else hands over a place of the run. This is no access
control; no tool, front or loop checks what a session does with it.

Runtime acceptance items it depends on: those of :mod:`hilclaw.turn_loop`,
ADR-0118 items (v) and (vi) as ADR-0122 uses them, ADR-0123 item (ix), the
self-check's items (i) to (viii) of ADR-0054 and (ix) to (xv) of ADR-0057, and
ADR-0125 item (xvi): what ``claude auth status`` reports for an expired login
that cannot be refreshed.
"""

import contextlib
import sys

from hilclaw import (
    data_root_source,
    further_turn,
    layout,
    selfcheck,
    selfcheck_outcome,
    tools,
    turn_definition,
    turn_loop,
)

_LEAD = "Carry out the next turn of your run as your instructions say. Your run id is "

RUN_OVER = "run_over"
UNKNOWN_RUN_STATUS = "unknown_run_status"
FAILED_TURN = "failed_turn"
UNCHANGED_TURN = "unchanged_turn"
OPEN_STATE = "open_state"
STOPPED_AT_CHECK = "stopped_at_check"
ERROR = "error"

BAD_USAGE = "bad_usage"
NO_DATA_ROOT = "no_data_root"
NO_CLAUDE = "no_claude"
FAULT = "fault"

EXIT_RUN_OVER = 0
EXIT_UNKNOWN_RUN_STATUS = 10
EXIT_FAILED_TURN = 11
EXIT_UNCHANGED_TURN = 12
EXIT_OPEN_STATE = 13
EXIT_STOPPED_AT_CHECK = 14
EXIT_ERROR = 20

_STATUS = {
    RUN_OVER: EXIT_RUN_OVER,
    UNKNOWN_RUN_STATUS: EXIT_UNKNOWN_RUN_STATUS,
    FAILED_TURN: EXIT_FAILED_TURN,
    UNCHANGED_TURN: EXIT_UNCHANGED_TURN,
    OPEN_STATE: EXIT_OPEN_STATE,
    STOPPED_AT_CHECK: EXIT_STOPPED_AT_CHECK,
    ERROR: EXIT_ERROR,
}
_TURN_AFTER = (selfcheck_outcome.PASSED, selfcheck_outcome.NO_CALL)


def prompt(run_id):
    """Return the prompt of every turn of the run ``run_id``.

    The prompt is the fixed text ``Carry out the next turn of your run as your
    instructions say. Your run id is``, one space, the run id unchanged and a
    final ``.``. ``run_id`` is checked by :func:`hilclaw.layout.check_run_id`,
    whose :class:`hilclaw.layout.InvalidPathValueError` is raised unchanged.
    """
    return f"{_LEAD}{layout.check_run_id(run_id)}."


def _outcome(before, after, previous):
    if after.case == further_turn.OVER_CASE:
        return {"outcome": RUN_OVER}
    if after.case == further_turn.UNKNOWN_STATUS:
        return {"outcome": UNKNOWN_RUN_STATUS, "run_status": after.value}
    failed = previous is not None and previous != 0
    if after.case == further_turn.OPEN:
        told = {"outcome": OPEN_STATE, "reason": after.value}
        if failed:
            told["exit_status"] = previous
        return told
    if failed:
        return {"outcome": FAILED_TURN, "exit_status": previous}
    if previous is not None and after == before:
        return {"outcome": UNCHANGED_TURN}
    return None


class _Step:
    def __init__(self, data_root, run_id, check):
        self.data_root = data_root
        self.run_id = run_id
        self.check = check
        self.before = None
        self.told = None
        self.report = None
        self.fault = None

    def __call__(self, previous):
        after = further_turn.classify(self.data_root, self.run_id)
        self.told = _outcome(self.before, after, previous)
        self.before = after
        if self.told is None and previous is None:
            self.told = self._checked()
        return self.told is None

    def _checked(self):
        try:
            report = self.check(data_root=self.data_root)
        except Exception as e:  # noqa: BLE001
            self.fault = type(e).__name__
            return {"outcome": STOPPED_AT_CHECK, "check_fault": self.fault}
        if type(report) is not dict:
            return {"outcome": STOPPED_AT_CHECK}
        self.report = report
        outcome = report.get("outcome")
        if type(outcome) is str and outcome in _TURN_AFTER:
            return None
        return {"outcome": STOPPED_AT_CHECK}


def _described(error):
    try:
        return f"{type(error).__name__}: {error}"
    except Exception:  # noqa: BLE001
        return type(error).__name__


def _error(kind, text):
    return {"outcome": ERROR, "error": kind}, text


def _start(args, source, parent, stdout, check):
    if len(args) != 1:
        return _error(BAD_USAGE, f"usage: expected one run id, got {len(args)}")
    try:
        run_id = layout.check_run_id(args[0])
    except layout.InvalidPathValueError as e:
        return _error(BAD_USAGE, _described(e))
    if stdout is None:
        return _error(FAULT, "standard output is closed")
    try:
        root = data_root_source.obtain(source)
    except tools.ToolFailure as e:
        return _error(NO_DATA_ROOT, e.message)
    except Exception as e:  # noqa: BLE001
        return _error(FAULT, _described(e))
    step = _Step(root, run_id, check)
    told, text = _looped(step, run_id, root, parent)
    if step.report is not None:
        told["check"] = step.report
    return told, text


def _looped(step, run_id, root, parent):
    try:
        turn_loop.run(
            further_turn=step,
            put_definition=turn_definition.put,
            prompt=prompt(run_id),
            data_root=root,
            run_id=run_id,
            parent=parent,
        )
    except turn_loop.ClaudeNotFoundError as e:
        return _error(NO_CLAUDE, _described(e))
    except Exception as e:  # noqa: BLE001
        return _error(FAULT, _described(e))
    if step.fault is not None:
        return step.told, f"fault of the check: {step.fault}"
    return step.told, None


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _say(stderr, text):
    with contextlib.suppress(Exception):
        if stderr is not None:
            line = f"hilclaw.turn_start: {text}".replace("\r", " ").replace("\n", " ")
            stderr.write((line + "\n").encode("utf-8", "backslashreplace"))
            stderr.flush()


def main(
    argv=None,
    *,
    source=data_root_source.configured,
    check=selfcheck.check,
    parent=None,
    stdout=None,
    stderr=None,
):
    """Drive the run named by the one argument turn by turn and return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``. ``source`` is the data-root source
    (:mod:`hilclaw.data_root_source`), asked once. ``check`` is the
    self-check, called at most once with the keyword ``data_root`` and
    answering a report as :func:`hilclaw.selfcheck.check` does. ``parent``
    is passed to :func:`hilclaw.turn_loop.run` unchanged (``None``: the
    temporary directory of the system). ``stdout`` and ``stderr`` are binary
    streams and default to the standard ones; a standard stream that the
    process does not have, or that has no binary layer, is missing; the
    turn sessions write to the process's file descriptor 2 whatever
    ``stderr`` is (:mod:`hilclaw.turn_loop`). Returns
    the status of the module docstring's table; no :class:`Exception` leaves
    the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    told, text = _start(args, source, parent, stdout, check)
    status = _STATUS[told["outcome"]]
    try:
        if stdout is None:
            raise OSError("it is closed")
        line = tools.encode(told)
        if stdout.write(line) != len(line):
            raise OSError("it took a part of the line")
        stdout.flush()
    except Exception as e:  # noqa: BLE001
        text = f"cannot write standard output: {_described(e)}"
        status = EXIT_ERROR
    if text is not None:
        _say(stderr, text)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
