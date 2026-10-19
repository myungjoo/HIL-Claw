"""Step 1 of the turn loop for a first-case run (ADR-0121 decision 5).

``ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`` decides, for the
runs of ADR-0120 decision 1, which states of ``runs/<run_id>/`` the step 1 of
the turn loop of ADR-0118 decision 3 answers by itself, and only these:

- P1, a fresh run directory (ADR-0120 decision 4): a further turn;
- P2, ``STATE.json`` valid, version 1, with ``run_status`` ``"over"``: no
  further turn;
- P3, ``STATE.json`` valid, version 1, with ``run_status`` holding any other
  value, a non-string included (ADR-0121 decision 2): no further turn, and the
  value is reported;
- P4, ``STATE.json`` valid, version 1, without ``run_status``, and
  ``instance.json`` valid, version 1, with ``round_budget``: a further turn,
  whatever ``round`` is.

In every other state the code asks its caller's predicate (ADR-0121 decision
5, last bullet). :func:`classify` tells the state; :func:`predicate` makes the
``further_turn`` that :func:`hilclaw.turn_loop.run` takes.

**A choice of this module**: P1 and P4 say that a turn is due, not how often a
failing one is retried. So they answer a further turn only before the first
turn (``previous`` is ``None``) or after a turn session whose exit status was
0; after any other exit status the caller's predicate answers. Otherwise a
round-0 turn that keeps failing would leave the directory fresh and the loop
would start turns without end, spending plan usage. A turn that exits with 0
and leaves the run as it found it is not caught: P1 and P4 answer a further
turn again, as ADR-0121 decision 5 has it, so this predicate alone bounds no
usage. P2 and P3 answer no further turn whatever ``previous`` is.

It writes, creates, removes and lists nothing, keeps nothing between calls,
compares no number, interprets no member besides ``run_status`` and
``round_budget``, and is no FR-10 tool. It passes on ``round`` in the finding
of P4 without interpreting it.

**Open** for ADR-0121, each asked of the caller's predicate where it is a
state: a run whose ``instance.json`` states no ``round_budget`` (OD-8 ㉙ (나));
a ``STATE.json`` or ``instance.json`` that is missing beyond P1, invalid or of
another version (OD-8). For the runs of ADR-0120 decision 1, ADR-0122 answers
what the loop does in these states and after a failed turn or an exit-0 turn
that left the run as it found it, and :mod:`hilclaw.turn_start`, the loop's
command-line entry, applies it on :func:`classify` directly; :func:`predicate`
keeps the answers above, so it alone still does not catch such an exit-0
turn. Still open: the lock of two loops on one run (rest of OD-17) and a run
that is over and whose commit is still owed (OD-8 ⑪).
"""

from typing import NamedTuple

from hilclaw import fresh_run, instance, layout, run_journal, run_state

RUN_STATUS = "run_status"
OVER = "over"

FRESH = "fresh"
OVER_CASE = "over"
UNKNOWN_STATUS = "unknown_status"
DUE = "due"
OPEN = "open"

STATE_MISSING = "state_missing"
STATE_INVALID = "state_invalid"
STATE_VERSION = "state_version"
INSTANCE_MISSING = "instance_missing"
INSTANCE_INVALID = "instance_invalid"
INSTANCE_VERSION = "instance_version"
NO_ROUND_BUDGET = "no_round_budget"


class Finding(NamedTuple):
    """Result of :func:`classify`: the ``case`` and its ``value``.

    ``value`` is the ``run_status`` value for :data:`UNKNOWN_STATUS`, the
    ``round`` of ``STATE.json`` for :data:`DUE`, one of the seven reason
    constants (:data:`STATE_MISSING` to :data:`NO_ROUND_BUDGET`) for
    :data:`OPEN`, and ``None`` for :data:`FRESH` and :data:`OVER_CASE`.
    """

    case: str
    value: object


def classify(data_root, run_id):
    """Return the :class:`Finding` of the run ``run_id`` below ``data_root``.

    In this order: :data:`FRESH` when :func:`hilclaw.fresh_run.is_fresh` is
    true (P1); :data:`OPEN` with :data:`STATE_MISSING`, :data:`STATE_INVALID`
    or :data:`STATE_VERSION` when :func:`hilclaw.run_journal.read_state` finds
    no ``STATE.json``, an invalid one or another version; :data:`OVER_CASE`
    when its ``run_status`` is exactly the ``str`` ``"over"`` (P2);
    :data:`UNKNOWN_STATUS` with the value as parsed when ``run_status`` holds
    any other value (P3); without ``run_status``, :data:`OPEN` with
    :data:`INSTANCE_MISSING`, :data:`INSTANCE_INVALID` or
    :data:`INSTANCE_VERSION` when :func:`hilclaw.instance.read` finds no
    ``instance.json``, an invalid one or another version, :data:`OPEN` with
    :data:`NO_ROUND_BUDGET` for one without ``round_budget``, and :data:`DUE`
    with the ``round`` of that same ``STATE.json`` read when it states one
    (P4).

    Raises :class:`hilclaw.layout.InvalidPathValueError` for an invalid
    ``run_id`` before anything is checked, :class:`FileNotFoundError` or
    :class:`NotADirectoryError` for a ``data_root`` that is no existing
    directory, and any other :class:`OSError` unchanged.
    """
    if fresh_run.is_fresh(data_root, run_id):
        return Finding(FRESH, None)
    try:
        state = run_journal.read_state(data_root, run_id)
    except run_journal.MissingStateError:
        return Finding(OPEN, STATE_MISSING)
    except run_state.InvalidStateError:
        return Finding(OPEN, STATE_INVALID)
    except run_state.UnsupportedVersionError:
        return Finding(OPEN, STATE_VERSION)
    if RUN_STATUS in state.others:
        value = state.others[RUN_STATUS]
        if type(value) is str and value == OVER:
            return Finding(OVER_CASE, None)
        return Finding(UNKNOWN_STATUS, value)
    try:
        stated = instance.read(data_root, run_id)
    except instance.MissingInstanceError:
        return Finding(OPEN, INSTANCE_MISSING)
    except instance.InvalidInstanceError:
        return Finding(OPEN, INSTANCE_INVALID)
    except instance.UnsupportedVersionError:
        return Finding(OPEN, INSTANCE_VERSION)
    if stated.round_budget is None:
        return Finding(OPEN, NO_ROUND_BUDGET)
    return Finding(DUE, state.round)


def predicate(data_root, run_id, *, fallback, report):
    """Return ``further_turn(previous)`` for :func:`hilclaw.turn_loop.run` on the run ``run_id``.

    Each call runs :func:`classify` afresh. :data:`OVER_CASE` answers
    ``False``. :data:`UNKNOWN_STATUS` calls ``report(value)`` once and answers
    ``False``. :data:`FRESH` and :data:`DUE` answer ``True`` when ``previous``
    is ``None`` or the ``int`` 0; for any other ``previous``, and for
    :data:`OPEN`, the answer is ``fallback(previous)``, returned unchanged.
    ``fallback`` and ``report`` are called in no other case, and what they or
    :func:`classify` raise passes through.

    Raises :class:`TypeError` when ``fallback`` or ``report`` is not callable
    and :class:`hilclaw.layout.InvalidPathValueError` for an invalid
    ``run_id``, both before any file is read.
    """
    for name, value in (("fallback", fallback), ("report", report)):
        if not callable(value):
            raise TypeError(f"{name} must be callable")
    layout.check_run_id(run_id)

    def further_turn(previous):
        finding = classify(data_root, run_id)
        if finding.case == OVER_CASE:
            return False
        if finding.case == UNKNOWN_STATUS:
            report(finding.value)
            return False
        if finding.case in (FRESH, DUE) and (
            previous is None or (type(previous) is int and previous == 0)
        ):
            return True
        return fallback(previous)

    return further_turn
