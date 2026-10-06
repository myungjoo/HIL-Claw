"""Event log of one run, ``runs/<run_id>/events.ndjson`` (ADR-0006).

``ARCHITECTURE/decisions/ADR-0006-od8-events-log.md`` fixes what a line is
(decision 2), the members of every line (3), the order (4), append only (5),
the torn tail and what counts as damage (6) and the version in every line (8).
This module checks a parsed line, appends a line, reads the file of a run and
removes a torn tail. The path comes from :func:`hilclaw.layout.run_file`.

``data_root`` is given by the caller and must be an existing directory
(:class:`FileNotFoundError` or :class:`NotADirectoryError` otherwise). Arguments
are checked before the file system is looked at and are not modified; an error
of :mod:`hilclaw.layout` for ``run_id`` and an :class:`OSError` pass through.

Conventions of this module, which ADR-0006 does not fix:

- Values are exactly ``dict``, ``list``, ``str``, ``int``, ``float``, ``bool``
  and ``None``, as :func:`json.loads` returns them.
- A line is written as :func:`json.dumps` writes it by default, as in the
  Example of ADR-0006: ``", "`` and ``": "`` as separators, every character
  outside ASCII escaped. A reader accepts any JSON text of the shape.
- An append ends with ``flush`` and ``os.fsync``; nothing beyond the death of
  the process is claimed (decision 10). When an append fails, the error passes
  through and nothing is removed: the earlier complete lines are as they were,
  and the new line is absent, a torn tail, or complete when the failure came
  after its line feed was written.
- A path that is not a regular file (a symbolic link in its place is not
  followed) raises :class:`CorruptEventsError`, as a damaged line does in
  :func:`read`; nothing is repaired. A line this interpreter cannot parse
  (nested too deeply, an integer too long) is reported as damaged, whatever
  its version; a number beyond the float range is read as an infinity.
- A complete line of another version makes :func:`read` raise
  :class:`UnsupportedVersionError`: it is neither skipped nor interpreted.
  Whether one file may hold lines of two versions is OD-11, not decided here.

It knows no event kind and no member of ``data``, never edits, removes or
reorders a complete line, reads no configuration, runs no ``git``, commits
nothing and gives no locking and no atomicity (OD-17, decision 10).
"""

import functools
import json
import math
import os
import re
import reprlib
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple

from hilclaw import keys, layout

SCHEMA_VERSION = 1

_CHUNK = 65536
_MAX = keys.MAX_INTEGER
_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_TIME = re.compile("([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})Z")
_SCALARS = (str, int, bool, type(None))
_utc_now = functools.partial(datetime.now, UTC)


def _is_time(value):
    match = _TIME.fullmatch(value)
    try:
        return bool(match and datetime(*map(int, match.groups()), tzinfo=UTC))
    except ValueError:
        return False


_INTEGER = (int, range(_MAX + 1).__contains__, f"an int from 0 to {_MAX}")
_FROM_ONE = (int, range(1, _MAX + 1).__contains__, f"an int from 1 to {_MAX}")
_CHECKS = {
    "schema_version": _INTEGER,
    "time": (str, _is_time, "a str YYYY-MM-DDThh:mm:ssZ of an existing date and time"),
    "kind": (str, _NAME.fullmatch, f"a str matching {_NAME.pattern}"),
    "round": _INTEGER,
    "candidate": _FROM_ONE,
    "attempt": _FROM_ONE,
    "data": (dict, None, "an object"),
}
_REQUIRED = ("schema_version", "time", "kind", "data")
_TOGETHER = (("candidate", "round"), ("attempt", "candidate"))


class Log(NamedTuple):
    """Result of :func:`read`: the events and the number of bytes of a torn tail (0 for none)."""

    events: list
    torn_tail: int


class InvalidEventError(ValueError):
    """An event or an argument breaks ADR-0006 decision 3; the message names the member."""


class CorruptEventsError(Exception):
    """A stored ``events.ndjson`` is damaged or not usable; the message names the path."""


class UnsupportedVersionError(Exception):
    """A line has another ``schema_version``: not damage (decision 6), and not interpreted."""


def validate(event):
    """Check ``event``, a parsed line, against ADR-0006 decision 3; return ``None``.

    ``event`` must be a ``dict`` with exactly ``schema_version``, ``time``,
    ``kind``, ``data`` and optionally ``round``, ``candidate`` (only with
    ``round``) and ``attempt`` (only with ``candidate``), in the types and forms
    of decision 3. ``kind`` is checked against no vocabulary and the content of
    ``data`` is not checked. Raises :class:`InvalidEventError` for the first
    rule found broken. The version comes first: an integer of ADR-0001 other
    than :data:`SCHEMA_VERSION` raises :class:`UnsupportedVersionError` before
    any other member is looked at.
    """
    if type(event) is not dict:
        _fail("event", "an object", event)
    version = _member("schema_version", event.get("schema_version"))
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    for name in event:
        if name not in _CHECKS:
            _fail("event", "without the unknown member", name)
    for name in _REQUIRED:
        if name not in event:
            raise InvalidEventError(f"event: lacks the member {name}")
    for name in _CHECKS:
        if name in event:
            _member(name, event[name])
    for name, other in _TOGETHER:
        if name in event and other not in event:
            raise InvalidEventError(f"{name}: is given only together with {other}")


def append(data_root, run_id, kind, data, *, round=None, candidate=None, attempt=None):
    """Append one event to the log of the run ``run_id`` and return it as written.

    The line has ``schema_version`` :data:`SCHEMA_VERSION`, ``time`` read from
    the clock of this process in UTC (the caller cannot state it), ``kind``,
    those of ``round``, ``candidate`` and ``attempt`` that are not ``None``,
    and ``data``, in this order; :func:`validate` must accept it. ``data`` must
    also be strict JSON: member names that are ``str``, no ``NaN`` or infinity,
    no value outside JSON. The returned ``dict`` holds a copy of ``data``.

    The file and ``runs/<run_id>/`` are created when missing (ADR-0004 decision
    1). A torn tail is removed first (decision 6); only the end of the file is
    read. The line feed is the last byte written. Raises
    :class:`InvalidEventError` for an argument that breaks a rule and
    :class:`CorruptEventsError` for a path that is not a regular file; nothing
    is written.
    """
    path = layout.run_file(data_root, run_id, "events.ndjson")
    time = _utc_now().replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
    event = {"schema_version": SCHEMA_VERSION, "time": time, "kind": kind}
    numbers = {"round": round, "candidate": candidate, "attempt": attempt}
    event.update({name: value for name, value in numbers.items() if value is not None})
    event["data"] = data
    validate(event)
    try:
        event["data"] = _plain("data", data)
        line = json.dumps(event, allow_nan=False).encode("ascii") + b"\n"
    except (RecursionError, ValueError) as error:
        if isinstance(error, InvalidEventError):
            raise
        raise InvalidEventError(f"data: is not strict JSON: {error!r}") from error
    _lstat(_root(data_root), path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab+") as f:
        _drop_tail(f)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
    return event


def read(data_root, run_id):
    """Return the :class:`Log` of the run ``run_id``: its events in the order of the file.

    Every complete line gives one event, a ``dict`` as parsed; the file is split
    at the line feed only. A missing and an empty file give no event (decision
    2). A torn tail is never an event, also when its bytes parse; its length is
    reported and the file is not changed.

    Raises :class:`CorruptEventsError`, naming the path and the line number
    (from 1), for a damaged complete line (decision 6): not UTF-8, not exactly
    one JSON text that is an object, a member name twice in an object, ``NaN``
    or an infinity, or an envelope :func:`validate` rejects. A line of another
    version raises :class:`UnsupportedVersionError` with the same place.
    """
    path = layout.run_file(data_root, run_id, "events.ndjson")
    root = _root(data_root)
    if _lstat(root, path) is None:
        return Log([], 0)
    *lines, tail = path.read_bytes().split(b"\n")
    events = []
    for number, line in enumerate(lines, 1):
        where = f"{path.relative_to(root).as_posix()}: line {number}"
        try:
            text = line.decode("utf-8")
            event = json.loads(text, object_pairs_hook=_object, parse_constant=_nan)
            validate(event)
        except UnsupportedVersionError as error:
            raise UnsupportedVersionError(f"{where}: {error}") from None
        except (ValueError, RecursionError) as error:
            raise CorruptEventsError(f"{where}: is damaged: {error}") from error
        events.append(event)
    return Log(events, len(tail))


def remove_torn_tail(data_root, run_id):
    """Remove the torn tail of the log of the run ``run_id``; return the number of bytes removed.

    This is the removal :func:`append` performs, for the step that commits the
    data repository (decision 6): exactly the bytes after the last line feed,
    the whole content when there is none; no earlier line is read. Returns 0,
    and writes nothing, when the file is missing, empty or ends with a line
    feed. Raises :class:`CorruptEventsError` for a path that is not a regular file.
    """
    path = layout.run_file(data_root, run_id, "events.ndjson")
    if _lstat(_root(data_root), path) is None:
        return 0
    with open(path, "rb+") as f:
        removed = _drop_tail(f)
        if removed:
            os.fsync(f.fileno())
    return removed


def _fail(place, rule, value):
    got = f"{type(value).__name__} {reprlib.repr(value)}"
    raise InvalidEventError(f"{place[:200]}: must be {rule}, got {got}")


def _member(name, value):
    kind, accepts, rule = _CHECKS[name]
    if type(value) is not kind or (accepts and not accepts(value)):
        _fail(name, rule, value)
    return value


def _plain(place, value):
    kind = type(value)
    if kind is dict:
        for name in value:
            if type(name) is not str:
                _fail(f"{place}: member name", "a str", name)
        return {name: _plain(f"{place}.{name}", item) for name, item in value.items()}
    if kind is list:
        return [_plain(f"{place}[{index}]", item) for index, item in enumerate(value)]
    if kind not in _SCALARS and not (kind is float and math.isfinite(value)):
        _fail(place, "a dict, list, str, int, bool, None or finite float", value)
    return value


def _root(data_root):
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    return root


def _lstat(root, path):
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    if not stat.S_ISREG(status.st_mode):
        where = path.relative_to(root).as_posix()
        raise CorruptEventsError(f"{where}: is not a regular file")
    return status


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _nan(name):
    raise ValueError(f"{name} is not a JSON value")


def _drop_tail(f):
    end = start = f.seek(0, os.SEEK_END)
    found = -1
    while start and found < 0:
        step = min(_CHUNK, start)
        start -= step
        f.seek(start)
        found = f.read(step).rfind(b"\n")
    keep = start + found + 1
    if keep < end:
        f.truncate(keep)
    f.seek(keep)
    return end - keep
