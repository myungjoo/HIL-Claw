"""The imprecise-timing finding of a measurement and of a run, derived from end lines (ADR-0103, ADR-0104).

``ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md`` fixes
when a measurement of ``sim.run`` or ``board.run`` is found imprecise on the
measured ground (decision 3), with the constant of decision 7, and when a run
is (decision 5). ``ARCHITECTURE/decisions/ADR-0104-od13-imprecise-timing-mark.md``
decides that both findings are derived and nothing is stored (decision 2): the
finding of a measurement from the ``result`` of its run tools' end line
(decision 3), that of a run by a fold over those lines in log order (decision
4). This module is those rules as pure functions of parsed lines, as
:func:`hilclaw.events.read` returns them:

* :data:`RESOLUTION_SHARE_MAX`: ``resolution_share_max`` = 1 %, a constant of
  the policy in the harness source (ADR-0103 decision 7).
* :func:`measurement_found`: the measured ground of one result.
* :func:`line_finding`: the finding of one line, ``None`` for a line that is
  not a run tools' end line.
* :func:`run_found_at`: the number of the first line at which a run is found.

Choices that are this module's own and no rule of a record:

* :data:`RESOLUTION_SHARE_MAX` is the :class:`fractions.Fraction` ``1/100``,
  and the coarse-clock test compares ``resolution`` with it times the
  smallest interval in exact rational arithmetic: for every admitted integer
  it is 100 × ``resolution`` > the smallest interval, with no float
  rounding.
* A result that the members read do not admit gives no finding and is
  refused (ADR-0104 decision 5 leaves open what a reader does with one):
  :class:`TypeError` for a type that is not accepted, :class:`ValueError` for
  an accepted type with a value that is not admitted or for an absent member.
  The message starts with the name of the member and shows nothing of the
  value, so no code of the value is called.
* The members read are those of the v2 result (ADR-0183 decision 8):
  ``resolution`` and ``intervals`` (ADR-0063 decision 4's ``resolution_ns``
  and ``intervals_ns`` renamed). ``unit`` is not read: both are in the one
  unit it states, so the coarse-clock test needs none.
* ``resolution`` and ``intervals`` are read and checked for both
  ``"converged"`` and ``"not_converged"``, although the not-converged ground
  needs neither.
* Every line given to :func:`line_finding` is checked as an envelope first;
  only a run tools' end line is checked further.
* :func:`run_found_at` reads and checks every line, also after the first
  finding, as :func:`hilclaw.journal.fold` does.
* The three values of ``outcome`` (ADR-0063 decision 2) are spelled here and
  not imported from :mod:`hilclaw.run_result`, which no other module of the
  package imports.

What the module does not do: it reads or writes no file, appends no line and
calls no :func:`hilclaw.events.read`; it reads no ``instance.json`` and no
``source_commit``. It starts no process and reads no clock. It is no tool and
is registered nowhere. It shows no warning (OD-13 sub-question ⑪ (라), OD-27)
and adds nothing to the data plane. It decides no reuse across runs and no
absolute-target judgement (⑪ (다)), and it does not establish the class input
of ADR-0103 decision 4 or OD-14 sub-question ①. It does not replay the
stopping rule: ``outcome`` is believed as stored (ADR-0104 decision 3; ADR-0063
Limit 2), and no other member of a result is checked against the table of
ADR-0183 decision 4. It changes nothing of :mod:`hilclaw.harness.measurement`,
:mod:`hilclaw.run_result`, :mod:`hilclaw.run_identity` or
:mod:`hilclaw.journal`.
"""

from fractions import Fraction

from hilclaw import events, journal, run_identity

RESOLUTION_SHARE_MAX = Fraction(1, 100)

_CONVERGED = "converged"
_NOT_CONVERGED = "not_converged"
_BROKEN = "broken"
_OUTCOMES = (_CONVERGED, _NOT_CONVERGED, _BROKEN)
_STEP_KINDS = (journal.STEP_STARTED, journal.STEP_ENDED)


def measurement_found(result):
    """Return whether the measurement of ``result`` is found imprecise on the measured ground.

    - ``result``: one result object of ``sim.run`` or ``board.run``, a parsed
      ``dict`` (ADR-0183 decision 4).

    ``True`` for ``outcome`` ``"not_converged"``; for ``"converged"``, ``True``
    exactly when ``resolution`` is greater than
    :data:`RESOLUTION_SHARE_MAX` times the smallest entry of ``intervals``,
    so a ``resolution`` of 0 never gives ``True``; ``False`` for
    ``"broken"``, a broken run being no measurement (ADR-0103 decision 3).

    Only ``outcome`` is read, and ``resolution`` and ``intervals`` when
    the outcome is not ``"broken"``. No other member is checked against the
    table of ADR-0183 decision 4. Raises :class:`TypeError` when ``result`` is
    not exactly a ``dict``, ``outcome`` not exactly a ``str``,
    ``resolution`` or an entry of ``intervals`` not exactly an ``int``,
    or ``intervals`` not exactly a ``list`` or a ``tuple``. Raises
    :class:`ValueError` for another ``outcome``, an absent member read,
    ``resolution`` below 0, an entry below 1, and an empty
    ``intervals`` with ``"converged"``. The refusals are this module's
    choice (see the module docstring). ``result`` is not modified.
    """
    if type(result) is not dict:
        raise TypeError("result: must be exactly a dict")
    outcome = _member(result, "outcome")
    if type(outcome) is not str:
        raise TypeError("outcome: must be exactly a str")
    if outcome not in _OUTCOMES:
        raise ValueError("outcome: must be converged, not_converged or broken")
    if outcome == _BROKEN:
        return False
    resolution = _member(result, "resolution")
    if type(resolution) is not int:
        raise TypeError("resolution: must be exactly an int")
    if resolution < 0:
        raise ValueError("resolution: must be at least 0")
    intervals = _member(result, "intervals")
    if type(intervals) not in (list, tuple):
        raise TypeError("intervals: must be exactly a list or a tuple")
    for interval in intervals:
        if type(interval) is not int:
            raise TypeError("intervals: every entry must be exactly an int")
        if interval < 1:
            raise ValueError("intervals: every entry must be at least 1")
    if outcome == _NOT_CONVERGED:
        return True
    if not intervals:
        raise ValueError("intervals: must not be empty when outcome is converged")
    return resolution > RESOLUTION_SHARE_MAX * min(intervals)


def line_finding(event):
    """Return the finding of the measurement of the parsed line ``event``, or ``None``.

    ``None`` when ``event`` is not a run tools' end line: its ``kind`` is not
    ``step_ended`` or its ``data.step`` is not in
    :data:`hilclaw.run_identity.STEPS`. Lines under another ``step`` are not
    read further (ADR-0104 decision 3). A run tools' end line is checked as
    :func:`hilclaw.journal.check_step` checks it and gives ``False`` when it
    holds ``failure``, otherwise :func:`measurement_found` of
    ``data.result``.

    Raises the error of :func:`hilclaw.events.validate` for any line that
    fails it, and the errors of :func:`hilclaw.journal.check_step` and
    :func:`measurement_found` for a run tools' end line. ``event`` is not
    modified.
    """
    events.validate(event)
    if _is_run_end(event):
        journal.check_step(event)
    return _finding(event)


def run_found_at(lines):
    """Return the number of the first line of ``lines`` at which the run is found imprecise, or ``None``.

    - ``lines``: any iterable of parsed lines in the order of the file, read
      once.

    The number counts from 1 within ``lines`` and is that of the first line
    for which :func:`line_finding` gives ``True``: ground (a) of ADR-0103
    decision 5, as the fold of ADR-0104 decision 4. The end lines of both
    tools count, a second end line of one identity or one without a start
    line like any other. ``None`` when there is no such line. A prefix of the
    log gives the finding at the moment of its last line.

    The class ground (b) never holds here: its input does not exist until a
    later record produces it (ADR-0103 decision 4; ADR-0104 decision 4).
    Whether the run is in the scope is for the caller to decide, from the
    hw_profile of its ``instance.json`` (ADR-0104 decision 1).

    Every line is read and checked, also after the first finding, as
    :func:`hilclaw.journal.fold` checks lines: :func:`hilclaw.events.validate`,
    and :func:`hilclaw.journal.check_step` for a step line, and then the
    result as :func:`line_finding` reads it. The first line that fails raises
    its error with ``line <number>:`` in front, and nothing is returned.
    """
    found = None
    for number, event in enumerate(lines, 1):
        try:
            events.validate(event)
            if event["kind"] in _STEP_KINDS:
                journal.check_step(event)
            finding = _finding(event)
        except (TypeError, ValueError, events.UnsupportedVersionError) as error:
            raise type(error)(f"line {number}: {error}") from None
        if finding and found is None:
            found = number
    return found


def _member(result, name):
    if name not in result:
        raise ValueError(f"{name}: is absent")
    return result[name]


def _is_run_end(event):
    kind, data = event["kind"], event["data"]
    return kind == journal.STEP_ENDED and data.get("step") in run_identity.STEPS


def _finding(event):
    if not _is_run_end(event):
        return None
    if "result" not in event["data"]:
        return False
    return measurement_found(event["data"]["result"])
