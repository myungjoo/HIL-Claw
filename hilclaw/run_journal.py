"""The two files of one run read together: ``STATE.json`` and the tail of the log.

``ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`` says that the
current spend view is the stored view folded over the tail, the complete lines
after the stored position (decision 6, *Replay*), and that the tail alone
decides the state of a step about the round in progress (decision 6, last
bullet). ``ADR-0012`` puts the stored view into ``runs/<run_id>/STATE.json``.
This module joins :func:`hilclaw.run_state.parse`, :func:`hilclaw.events.read`
and :func:`hilclaw.journal.fold` / :func:`hilclaw.journal.step_state` over the
files of a run. The paths come from :func:`hilclaw.layout.run_file`.

``data_root`` is given by the caller and must be an existing directory
(:class:`FileNotFoundError` or :class:`NotADirectoryError` otherwise); it is
not resolved. ``run_id`` is checked first, then an ``identity``, then the file
system; an error of :mod:`hilclaw.layout`, of :mod:`hilclaw.events` and of
:mod:`hilclaw.journal` and an :class:`OSError` pass through.

Conventions of this module, which the records do not fix:

- ``STATE.json`` is read before the log. Lines are only appended and the stored
  view moves only when a round ends, so a state read first names a position the
  log read afterwards has reached whenever the two files were consistent. The
  two reads are not atomic and no lock is taken (ADR-0004 decision 10).
- A missing ``STATE.json`` (no file, no run directory, a file in the place of a
  directory above it) raises :class:`MissingStateError`. The start values of
  ADR-0012 decision 4 are not answered in its place: what a run directory
  without the file means is open (sub-question 10 of ADR-0012).
- A path that is not a regular file (a symbolic link is not followed) raises
  :class:`hilclaw.run_state.InvalidStateError`: no state can be read from it
  and nothing is repaired, as for an invalid content.
- An error about the content of ``STATE.json`` names the file by its path
  relative to the data root, in front of the message of the parser.
- A stored position beyond the end of the log raises
  :class:`hilclaw.events.PositionBeyondLogError` as the reader of the log
  raises it; its message names the log, the position and the lines found.

It writes, creates and removes nothing, never folds from the first line and
compares no stored view with such a fold, interprets no member besides the
three of ADR-0012, reads no other version and decides nothing about an open
step, a budget limit, a lock or who calls it (OD-10, OD-11, OD-19, OD-23, the
rest of OD-17).
"""

import os
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import events, journal, layout, run_state


class MissingStateError(Exception):
    """The run has no ``STATE.json`` (ADR-0012 decision 2); the message names the path."""


class Current(NamedTuple):
    """Result of :func:`current`: the stored state, the view now, the fold's reports, the tail."""

    state: run_state.RunState
    view: journal.SpendView
    reports: tuple
    torn_tail: int


def read_state(data_root, run_id):
    """Return the :class:`hilclaw.run_state.RunState` stored for the run ``run_id``.

    The bytes of ``runs/<run_id>/STATE.json`` are given to
    :func:`hilclaw.run_state.parse` and nothing else is interpreted. Raises
    :class:`MissingStateError` when there is no file,
    :class:`hilclaw.run_state.InvalidStateError` for a path that is not a
    regular file and for an invalid content, an empty file included, and
    :class:`hilclaw.run_state.UnsupportedVersionError` for another version
    (ADR-0012 decision 6): nothing is returned and nothing is repaired.
    """
    path = layout.run_file(data_root, run_id, "STATE.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    file = path.relative_to(root).as_posix()
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        raise MissingStateError(f"{file}: is missing") from None
    if not stat.S_ISREG(status.st_mode):
        raise run_state.InvalidStateError(f"{file}: is not a regular file")
    try:
        return run_state.parse(path.read_bytes())
    except (run_state.InvalidStateError, run_state.UnsupportedVersionError) as error:
        raise type(error)(f"{file}: {error}") from None


def current(data_root, run_id):
    """Return the :class:`Current` of the run ``run_id`` (ADR-0011 decision 6, *Replay*).

    ``state`` is what :func:`read_state` returns, ``view`` the stored view
    folded over the tail, ``reports`` the reports of that fold with the line
    numbers of the file, and ``torn_tail`` the number of bytes of a torn tail,
    which is not removed. Raises as :func:`read_state`,
    :func:`hilclaw.events.read` and :func:`hilclaw.journal.fold` do, among them
    :class:`hilclaw.events.PositionBeyondLogError` when the log holds fewer
    complete lines than the stored position: nothing is returned then and the
    stored view is not used. Lines before the position are not interpreted.
    """
    state, tail, torn_tail = _state_and_tail(data_root, run_id)
    view, reports = journal.fold(tail, state.budget_spent)
    return Current(state, view, reports, torn_tail)


def step_state(data_root, run_id, identity):
    """Return the :class:`hilclaw.journal.StepState` of ``identity`` in the run ``run_id``.

    The answer is that of :func:`hilclaw.journal.step_state` for the stored
    view and the tail. Limit: it is right for a step whose lines lie after the
    stored position, as those of the round in progress; a step that ended
    before the position answers ``NO_LINE``, and the log is not read from its
    first line (ADR-0011 decision 6, sub-question 1). An invalid ``identity``
    is reported before any file is read; otherwise raises as :func:`current`.
    """
    layout.check_run_id(run_id)
    journal.step_state(identity, ())
    state, tail, _ = _state_and_tail(data_root, run_id)
    return journal.step_state(identity, tail, state.budget_spent)


def _state_and_tail(data_root, run_id):
    state = read_state(data_root, run_id)
    tail = events.read(data_root, run_id, state.budget_spent.position)
    return state, *tail
