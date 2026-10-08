"""The instance record of one run, ``runs/<run_id>/instance.json`` (ADR-0018, ADR-0020).

``ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md`` fixes the
file as a whole (decision 2), the member ``hw_profile`` in which a run states
the hw_profile it was started with (decisions 3 and 5) and how a call of a HW
tool reads it (decision 4).
``ARCHITECTURE/decisions/ADR-0020-od8-instance-record-tolerance.md`` adds the
member ``tolerance``, in which a run states the ``rtol`` and the ``atol`` of
its correctness check in the vocabulary of the first case (decisions 2 to 4),
and says where the tolerance of a run is read from (decision 5). This module
is those rules: :func:`parse` and :func:`validate` are pure functions of the
bytes of a content and of a parsed document, and :func:`read`,
:func:`hw_profile_of` and :func:`tolerance_of` read the file of a run.
:func:`hw_profile_of` has the call form of the parameter ``hw_profile_of`` of
:func:`hilclaw.hw_tool.tool_function`; nothing here binds it or
:func:`tolerance_of` to a tool.

Conventions of this module, which the two records do not fix:

- A content is exactly ``bytes`` (:class:`TypeError` otherwise: the encoding is
  part of validity). Values are as :func:`json.loads` returns them, an integer
  exactly an ``int``: ``true`` and ``1.0`` are none.
- Every other broken rule of a content or of a document raises
  :class:`InvalidInstanceError` naming the place, and another version raises
  :class:`UnsupportedVersionError` of this module.
- The rules for the whole text come first, whatever the version, then
  ``schema_version``, then ``hw_profile``, then ``tolerance`` when the document
  holds it. A content this interpreter cannot
  read (an integer too long for it anywhere in the text, nesting too deep)
  raises :class:`InvalidInstanceError` too, though it is a limit of this reader
  and not damage; the limits stay as the interpreter has them. A number beyond
  the float range in a member not defined here is read as an infinity and is
  no error, as :mod:`hilclaw.run_state` has it; in ``tolerance`` it makes the
  content invalid (ADR-0020 decision 4).
- ``schema_version`` is an integer of ADR-0001, from 0 to
  :data:`hilclaw.keys.MAX_INTEGER`: a value outside that range is no integer of
  the records and makes the content invalid, it is not another version. ``-0``
  is read as the integer 0, as :mod:`hilclaw.run_state` reads it, and is then
  the unsupported version 0.
- Inside ``hw_profile`` the order is: an object, no member besides ``key`` and
  ``record``, both present, ``key`` a ``str``, ``record`` an object, the record
  valid, ``key`` the derived name. The first rule found broken is reported. An
  empty ``key`` and one of another form are reported as not the derived name.
- Inside ``tolerance`` the order is: an object, no member besides ``rtol`` and
  ``atol``, both present, ``rtol`` a valid value, ``atol`` a valid value. A
  value is exactly an ``int`` or a ``float`` (``true`` is none) whose ``float``
  is finite and not negative, so an ``int`` that no ``float`` holds is invalid.
  The first rule found broken is reported. The rule for a value is written
  here and agrees with ``check_tolerance`` of the verification harness, which
  this module does not import.
- The tolerance is handed out as a :class:`Tolerance` of two ``float``, also
  for an integer literal, and a zero as ``0.0`` whatever its sign in the file.
  A content without the member has ``None`` in that place: it states no
  tolerance, and that is no error of the content.
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
member besides the three and interprets no other: a file it accepts is not
thereby a complete instance record, and not enough to start a run (ADR-0018
decisions 1 and 2). Of the tolerance it gives what the file states and nothing
else: it holds no default and substitutes no value (ADR-0020 decision 3), does
not check that a run is of the first case, and gives the member no meaning for
a run of another case (#5 B-7). A file it accepts need not state a tolerance,
and where it is checked that an instance states one is open (OD-8
sub-question 19). Which tool or component reads the member, at which moment
of a call, and what a call answers when no tolerance is stated is not said
here; "not stated" is no error and has no tool-failure kind.
It reads no other file, so the stored record of the key below ``db/`` is not
read or compared (ADR-0018 decision 4) and no reader here needs it to exist; how
the two records relate is open (OD-8 sub-question 18). None of its errors is a
:class:`hilclaw.tools.ToolFailure`: the kind a call of a tool answers for them
is given by the tool function that calls :func:`hw_profile_of`
(:mod:`hilclaw.hw_tool`, ADR-0019), not here. It reads no other version
(OD-11) and says nothing of what writes the file, of when, or of a run
directory without it (OD-8 sub-questions 10 and 17). Nothing is kept between
calls, so a file changed between two calls is read as changed (ADR-0018
decision 6).
"""

import codecs
import json
import math
import os
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import keys, layout

SCHEMA_VERSION = 1

_MAX = keys.MAX_INTEGER
_DEFINED = ("schema_version", "hw_profile", "tolerance")
_SECTION = ("key", "record")
_TOLERANCE = ("rtol", "atol")


class InvalidInstanceError(ValueError):
    """A content, a document or a path breaks a rule of ADR-0018 or ADR-0020; the message names it."""


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class MissingInstanceError(Exception):
    """No instance record was written for the ``run_id``; the message names the path."""


class Tolerance(NamedTuple):
    """The tolerance a content states (ADR-0020 decision 2): ``rtol`` and ``atol``.

    As :func:`parse` returns it, both are ``float``, finite and not negative.
    They are what the content states, in the vocabulary of the first case; no
    value here is a default.
    """

    rtol: float
    atol: float


class Instance(NamedTuple):
    """Result of :func:`parse`: what a content states and the members not defined.

    ``tolerance`` is a :class:`Tolerance`, or ``None`` for a content without
    the member ``tolerance``. ``others`` is the last field.
    """

    hw_profile_key: str
    hw_profile: dict
    tolerance: Tolerance | None
    others: dict


def parse(content):
    """Return the :class:`Instance` of ``content``, the bytes of an ``instance.json``.

    ``hw_profile_key`` is ``hw_profile.key`` and ``hw_profile`` is
    ``hw_profile.record``, the ``dict`` parsed from this content;
    ``tolerance`` is the :class:`Tolerance` of the member ``tolerance``, each
    value the ``float`` of its literal (``2`` gives ``2.0``; ``-0``, ``-0.0``,
    ``-1e-999`` and ``1e-999`` give ``0.0``), or ``None`` when the content has
    no such member, and no value is substituted then; ``others`` holds every
    top-level member that is none of ``schema_version``, ``hw_profile`` and
    ``tolerance``, as parsed and not interpreted, whatever its name and value
    (``tolerence`` or a top-level ``rtol`` among them). Any order of members
    and any white space of JSON are accepted.

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
    """Check ``document``, a parsed ``instance.json``, against ADR-0018 and ADR-0020.

    ``document`` must be a ``dict`` with ``schema_version`` (an ``int`` from 0
    to :data:`hilclaw.keys.MAX_INTEGER`) and, at version 1, ``hw_profile``: a
    ``dict`` with exactly ``key`` and ``record``, the record a ``dict`` that
    :func:`hilclaw.keys.hw_profile_key` accepts and the key the name derived
    from it (ADR-0018 decisions 2 and 3). It may hold ``tolerance``, which is
    then a ``dict`` with exactly ``rtol`` and ``atol``, each exactly an ``int``
    or a ``float`` whose ``float`` is finite and not negative (ADR-0020
    decisions 2 to 4): for a value built in memory, an infinity, a NaN and an
    ``int`` that no ``float`` holds are invalid, and a ``bool`` is no number.
    Its other members are not looked at. The rules for the text (the
    encoding, a member name twice) cannot be checked on a parsed value.

    Raises :class:`InvalidInstanceError` for the first rule found broken,
    naming the place (for example ``hw_profile.record.accelerator`` or
    ``tolerance.rtol``). The
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
    :func:`hilclaw.backends.select`. Raises what :func:`read` raises, so
    :class:`InvalidInstanceError` also for a file whose ``tolerance`` is
    invalid: no member of an invalid file is used (ADR-0020 decision 3).
    """
    return read(data_root, run_id).hw_profile


def tolerance_of(data_root, run_id):
    """Return the tolerance the run ``run_id`` states, or ``None`` when it states none.

    It is the ``tolerance`` of what :func:`read` returns (ADR-0020 decision
    5): a :class:`Tolerance` with the ``rtol`` and the ``atol`` of the member
    ``tolerance`` of ``runs/<run_id>/instance.json``, new at each call, or
    ``None`` for a valid file without that member. ``None`` says that no
    tolerance is stated; no value stands in for it, here or in a default of
    this module. Raises what :func:`read` raises, so no tolerance is returned
    for a missing, unreadable or invalid file or one of another version.
    """
    return read(data_root, run_id).tolerance


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
    tolerance = _tolerance(document["tolerance"]) if "tolerance" in document else None
    others = {name: value for name, value in document.items() if name not in _DEFINED}
    return Instance(key, record, tolerance, others)


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


def _tolerance(section):
    if type(section) is not dict:
        _fail("tolerance", "an object", section)
    for name in section:
        if name not in _TOLERANCE:
            _fail("tolerance", "an object without the member", name)
    for name in _TOLERANCE:
        if name not in section:
            raise InvalidInstanceError(f"tolerance: lacks the member {name}")
    return Tolerance(*(_number(name, section[name]) for name in _TOLERANCE))


def _number(name, value):
    try:
        number = float(value) if type(value) in (int, float) else math.nan
    except OverflowError:
        number = math.inf
    if not 0 <= number < math.inf:
        _fail(f"tolerance.{name}", "a finite number that is not negative", value)
    return abs(number)


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _nan(name):
    raise ValueError(f"{name} is not a JSON value")
