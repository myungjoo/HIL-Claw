"""The fresh-run-directory test of ADR-0120 decision 4.

``ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`` decides, for the
runs of ADR-0076 decision 1, that a run directory is *fresh* when it holds
``instance.json`` under its final name and no other file of the run tree: no
``STATE.json``, ``events.ndjson``, ``artifacts.json`` or ``rounds/``. A fresh
directory is a started run whose round 0 has not begun; the turn loop takes
it up, and the Round-Manager of the round-0 turn writes the first
``STATE.json`` only into it. :func:`is_fresh` is that test, for the loop's
step-1 predicate and for the round-0 entry.

Every name is checked at its known path of :mod:`hilclaw.layout`, so nothing
is listed and a leftover of a write (ADR-0013 decision 4; ADR-0025 decision 6)
does not change the answer. "Not there" is an :class:`OSError` in
:data:`hilclaw.run_files.NOT_THERE`. The test writes, creates, lists and
removes nothing, reads nothing but the one read below, keeps nothing between
calls and is no FR-10 tool;
the registry tool ``run.fresh`` of :mod:`hilclaw.run_file_tools` is a tool
over it (ADR-0124).

A run whose ``instance.json`` states given code (version 3, ADR-0200
decision 6) gets its ``artifacts.json`` from the start, which records the
given code there before any turn (ADR-0200 decision 5). For such a run that
file does not count against freshness (ADR-0201 decision 1): when
``artifacts.json`` is present, ``instance.json`` is read once and the run is
fresh only if :func:`hilclaw.instance.parse_given` accepts it and it states
``given_code``. This is the only read of the test.

What it does not decide: what a directory with ``instance.json``, other files
of the tree and no ``STATE.json`` means, and what a turn does in a run that is
not fresh (ADR-0120 decision 4, open); the rest of the loop's predicate
(OD-8, OD-19); what follows a failed turn (OD-10, OD-17, OD-19, OD-27); and
the layout stamp of ``instance.json``, whose content is not read (㉗ (가)).
The Round-Manager reaches ``replace`` through the tool ``state.write``
(ADR-0124).
"""

import os
import stat

from hilclaw import instance, layout, run_files

_INSTANCE = "instance.json"
_ARTIFACTS = "artifacts.json"


def is_fresh(data_root, run_id):
    """Return whether ``runs/<run_id>`` below ``data_root`` is a fresh run directory (ADR-0120 decision 4).

    ``True`` exactly when ``instance.json`` is a regular file by
    :func:`os.stat` (a symbolic link to a regular file counts) and none of
    ``STATE.json``, ``events.ndjson``, ``artifacts.json`` and ``rounds`` is an
    entry of any kind by :func:`os.lstat` (a broken link or a directory counts
    as present). A path that is not there (a missing data root, ``runs/`` or
    run directory, or a file in the place of a directory above it) is absent.
    The one exception (ADR-0201 decision 1): an ``artifacts.json`` beside an
    ``instance.json`` that :func:`hilclaw.instance.parse_given` accepts and
    that states ``given_code`` does not count; an ``instance.json`` it
    refuses, or one of version 1 or 2, leaves the directory not fresh.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for an invalid
    ``run_id`` before anything is checked, and any other :class:`OSError` of a
    check unchanged.
    """
    path = layout.run_file(data_root, run_id, _INSTANCE)
    artifacts = layout.run_file(data_root, run_id, _ARTIFACTS)
    others = [
        layout.run_file(data_root, run_id, name)
        for name in layout.RUN_FILES
        if name not in (_INSTANCE, _ARTIFACTS)
    ]
    others.append(layout.round_dir(data_root, run_id, 0).parent)
    try:
        if not stat.S_ISREG(os.stat(path).st_mode):
            return False
    except run_files.NOT_THERE:
        return False
    if any(_present(other) for other in others):
        return False
    return not _present(artifacts) or _states_given_code(path)


def _states_given_code(path):
    try:
        content = path.read_bytes()
    except run_files.NOT_THERE:
        return False
    try:
        return instance.parse_given(content).given_code is not None
    except (instance.InvalidInstanceError, instance.UnsupportedVersionError):
        return False


def _present(path):
    try:
        os.lstat(path)
    except run_files.NOT_THERE:
        return False
    return True
