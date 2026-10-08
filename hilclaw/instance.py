"""The instance record of one run, ``runs/<run_id>/instance.json`` (ADR-0018).

``ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md`` fixes the
file as a whole (decision 2), the member ``hw_profile`` in which a run states
the hw_profile it was started with (decisions 3 and 5) and how a call of a HW
tool reads it (decision 4). This module is those rules: :func:`parse` and
:func:`validate` are pure functions of the bytes of a content and of a parsed
document, and :func:`read` and :func:`hw_profile_of` read the file of a run.
:func:`hw_profile_of` has the call form of the parameter ``hw_profile_of`` of
:func:`hilclaw.hw_tool.tool_function`; nothing here binds it to a tool.

Conventions of this module, which ADR-0018 does not fix:

- A content is exactly ``bytes`` (:class:`TypeError` otherwise: the encoding is
  part of validity). Values are as :func:`json.loads` returns them, an integer
  exactly an ``int``: ``true`` and ``1.0`` are none.
- Every other broken rule of a content or of a document raises
  :class:`InvalidInstanceError` naming the place, and another version raises
  :class:`UnsupportedVersionError` of this module.
- The rules for the whole text come first, whatever the version, then
  ``schema_version``, then ``hw_profile``. A content this interpreter cannot
  read (an integer too long for it anywhere in the text, nesting too deep)
  raises :class:`InvalidInstanceError` too, though it is a limit of this reader
  and not damage; the limits stay as the interpreter has them. A number beyond
  the float range in a member not defined here is read as an infinity and is
  no error, as :mod:`hilclaw.run_state` has it.
- ``schema_version`` is an integer of ADR-0001, from 0 to
  :data:`hilclaw.keys.MAX_INTEGER`: a value outside that range is no integer of
  the records and makes the content invalid, it is not another version. ``-0``
  is read as the integer 0, as :mod:`hilclaw.run_state` reads it, and is then
  the unsupported version 0.
- Inside ``hw_profile`` the order is: an object, no member besides ``key`` and
  ``record``, both present, ``key`` a ``str``, ``record`` an object, the record
  valid, ``key`` the derived name. The first rule found broken is reported. An
  empty ``key`` and one of another form are reported as not the derived name.
- The file is read as :mod:`hilclaw.run_journal` reads ``STATE.json``:
  ``run_id`` is checked first, then ``data_root``, which is used as given and
  must be an existing directory (:class:`FileNotFoundError` or
  :class:`NotADirectoryError` otherwise). A missing file (no file, no run
  directory, a file in the place of a directory above it) raises
  :class:`MissingInstanceError`. A path that is not a regular file (a symbolic
  link is not followed) raises :class:`InvalidInstanceError`. An error about
  the content names the file by its path relative to the data root, in front
  of the message of the parser. A file that disappears between the check and
  the read is an :class:`OSError`, as every other failure of the file system.

It writes, creates and removes no file and composes no content. It defines no
member besides the two and interprets none: a file it accepts is not thereby a
complete instance record, and not enough to start a run (decisions 1 and 2).
It reads no other file, so the stored record of the key below ``db/`` is not
read or compared (decision 4) and this reader does not need it to exist; how
the two records relate is open (OD-8 sub-question 18). None of its errors is a
:class:`hilclaw.tools.ToolFailure`: the kind a call of a tool answers for them
is given by the tool function that calls this reader (:mod:`hilclaw.hw_tool`,
ADR-0019), not here. It reads no other version
(OD-11) and says nothing of what writes the file, of when, or of a run
directory without it (OD-8 sub-questions 10 and 17). Nothing is kept between
calls, so a file changed between two calls is read as changed (decision 6).
"""

import codecs
import json
import os
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import keys, layout

SCHEMA_VERSION = 1

_MAX = keys.MAX_INTEGER
_DEFINED = ("schema_version", "hw_profile")
_SECTION = ("key", "record")


class InvalidInstanceError(ValueError):
    """A content, a document or a path breaks a rule of ADR-0018; the message names it."""


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class MissingInstanceError(Exception):
    """No instance record was written for the ``run_id``; the message names the path."""


class Instance(NamedTuple):
    """Result of :func:`parse`: the key name, the hw_profile record, the members not defined."""

    hw_profile_key: str
    hw_profile: dict
    others: dict


def parse(content):
    """Return the :class:`Instance` of ``content``, the bytes of an ``instance.json``.

    ``hw_profile_key`` is ``hw_profile.key`` and ``hw_profile`` is
    ``hw_profile.record``, the ``dict`` parsed from this content; ``others``
    holds every top-level member ADR-0018 does not define, as parsed and not
    interpreted, whatever its name and value. Any order of members and any
    white space of JSON are accepted.

    Raises :class:`InvalidInstanceError` when ``content`` is not UTF-8 without
    a byte order mark, is not exactly one JSON text (the tokens ``NaN``,
    ``Infinity`` and ``-Infinity`` are no JSON; an empty content is none),
    holds a member name twice in any object or is a document :func:`validate`
    refuses, and :class:`UnsupportedVersionError` as that function does.
    Nothing is returned then, and nothing is repaired.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidInstanceError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_object, parse_constant=_nan)
    except RecursionError:
        raise InvalidInstanceError("content: is nested too deeply to parse") from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidInstanceError(reason) from None
    return _checked(document)


def validate(document):
    """Check ``document``, a parsed ``instance.json``, against ADR-0018 decisions 2 and 3.

    ``document`` must be a ``dict`` with ``schema_version`` (an ``int`` from 0
    to :data:`hilclaw.keys.MAX_INTEGER`) and, at version 1, ``hw_profile``: a
    ``dict`` with exactly ``key`` and ``record``, the record a ``dict`` that
    :func:`hilclaw.keys.hw_profile_key` accepts and the key the name derived
    from it. Its other members are not looked at. The rules for the text (the
    encoding, a member name twice) cannot be checked on a parsed value.

    Raises :class:`InvalidInstanceError` for the first rule found broken,
    naming the place (for example ``hw_profile.record.accelerator``). The
    version comes first: an integer other than :data:`SCHEMA_VERSION` raises
    :class:`UnsupportedVersionError` before any other member is looked at.
    """
    _checked(document)


def read(data_root, run_id):
    """Return the :class:`Instance` of the run ``run_id``, read from its ``instance.json``.

    The bytes of ``runs/<run_id>/instance.json`` below ``data_root`` are given
    to :func:`parse`; no other file is read and nothing is written. The whole
    file is read at each call and nothing is kept, so each call returns new
    objects.

    Raises :class:`hilclaw.layout.InvalidPathValueError` for a ``run_id`` that
    is none, before the file system is touched; :class:`FileNotFoundError` or
    :class:`NotADirectoryError` when ``data_root`` is no existing directory;
    then one error for each situation of ADR-0018 decision 4:
    :class:`MissingInstanceError` when there is no file, an :class:`OSError`
    of the file system, unchanged, when it cannot be read,
    :class:`InvalidInstanceError` for an invalid content, an empty file
    included, and :class:`UnsupportedVersionError` for another version. A path
    that is not a regular file is none of the four: by the convention of this
    module it raises :class:`InvalidInstanceError`.
    """
    path = layout.run_file(data_root, run_id, "instance.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    file = path.relative_to(root).as_posix()
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        reason = f"{file}: is missing: no instance record was written for this run_id"
        raise MissingInstanceError(reason) from None
    if not stat.S_ISREG(status.st_mode):
        raise InvalidInstanceError(f"{file}: is not a regular file")
    try:
        return parse(path.read_bytes())
    except (InvalidInstanceError, UnsupportedVersionError) as error:
        raise type(error)(f"{file}: {error}") from None


def hw_profile_of(data_root, run_id):
    """Return the hw_profile record the run ``run_id`` states (ADR-0018 decision 4).

    It is the ``hw_profile`` of what :func:`read` returns: the
    ``hw_profile.record`` of ``runs/<run_id>/instance.json``, a ``dict`` valid
    by ADR-0001 and new at each call, which the caller may hand to
    :func:`hilclaw.backends.select`. Raises what :func:`read` raises.
    """
    return read(data_root, run_id).hw_profile


def _fail(place, rule, value):
    got = type(value).__name__
    if type(value) is str:
        got = f"{got} {reprlib.repr(value)}"
    raise InvalidInstanceError(f"{place}: must be {rule}, got {got}")


def _checked(document):
    if type(document) is not dict:
        _fail("document", "an object", document)
    if "schema_version" not in document:
        raise InvalidInstanceError("document: lacks the member schema_version")
    version = document["schema_version"]
    if type(version) is not int or not 0 <= version <= _MAX:
        _fail("schema_version", f"an int from 0 to {_MAX}", version)
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    if "hw_profile" not in document:
        raise InvalidInstanceError("document: lacks the member hw_profile")
    key, record = _hw_profile(document["hw_profile"])
    others = {name: value for name, value in document.items() if name not in _DEFINED}
    return Instance(key, record, others)


def _hw_profile(section):
    if type(section) is not dict:
        _fail("hw_profile", "an object", section)
    for name in section:
        if name not in _SECTION:
            _fail("hw_profile", "an object without the member", name)
    for name in _SECTION:
        if name not in section:
            raise InvalidInstanceError(f"hw_profile: lacks the member {name}")
    key, record = section["key"], section["record"]
    if type(key) is not str:
        _fail("hw_profile.key", "a str", key)
    if type(record) is not dict:
        _fail("hw_profile.record", "an object", record)
    try:
        name = keys.hw_profile_key(record).name
    except keys.InvalidRecordError as error:
        raise InvalidInstanceError(f"hw_profile.record.{error}") from None
    if key != name:
        _fail("hw_profile.key", f"{name}, the name derived from hw_profile.record", key)
    return key, record


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _nan(name):
    raise ValueError(f"{name} is not a JSON value")
