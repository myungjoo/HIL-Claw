"""The build record of an attempt, ``.../measure/.../build.json`` (ADR-0004, ADR-0198).

``ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`` gives the file
its place below the measurement role of an attempt.
``ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md``
gives it the owner's form of HQ-0089 ②, for an attempt of the candidate kind
``compile_settings`` only (decision 5): an object with exactly
``schema_version`` (the integer 1), ``outcome`` (``"built"`` or
``"broken"``), ``condition`` exactly when the outcome is ``"broken"``
(``"build_time_limit"`` or ``"build_exit_status"``, the answers of a failed
build of :mod:`hilclaw.check_build`), and ``flags`` and ``trailing_flags``,
the exact arguments of the build, each an array of strings.

:func:`parse` and :func:`validate` are pure functions of the bytes of a
content and of a parsed document; :func:`read` reads the file of an attempt.
Nothing here writes the file, and no tool reads it yet (ADR-0198 decision 8).

Conventions of this module, which the record does not fix: a content is
exactly ``bytes``, UTF-8 without a byte order mark, one JSON text with no
member name twice in any object; values are as :func:`json.loads` returns
them, an integer exactly an ``int``; an argument is a ``str`` of at least one
character without the character U+0000, which no argument of a process can
hold. The version comes first, then the members in the order above; the
first rule found broken is reported, naming its place.
"""

import codecs
import json
import os
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import json_text, keys, layout

SCHEMA_VERSION = 1
OUTCOMES = ("built", "broken")
CONDITIONS = ("build_time_limit", "build_exit_status")

_MEMBERS = ("schema_version", "outcome", "flags", "trailing_flags")


class InvalidBuildRecordError(ValueError):
    """A content, a document or a path breaks a rule; the message names it."""


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


class MissingBuildRecordError(Exception):
    """No build record was written for the attempt; the message names the path."""


class BuildRecord(NamedTuple):
    """What a valid build record states (ADR-0198 decision 5).

    ``condition`` is ``None`` when ``outcome`` is ``"built"``. ``flags`` and
    ``trailing_flags`` are the arrays of the file, unchanged.
    """

    outcome: str
    condition: str | None
    flags: list
    trailing_flags: list


def parse(content):
    """Return the :class:`BuildRecord` of ``content``, the bytes of a ``build.json``.

    Raises :class:`TypeError` when ``content`` is no ``bytes``,
    :class:`InvalidBuildRecordError` when it is not UTF-8 without a byte order
    mark, not exactly one JSON text, holds a member name twice in an object
    or is a document :func:`validate` refuses, and
    :class:`UnsupportedVersionError` as that function does.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidBuildRecordError("content: starts with a byte order mark")
    try:
        document = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=json_text.distinct_members,
            parse_constant=json_text.no_constant,
        )
    except RecursionError:
        raise InvalidBuildRecordError(
            "content: is nested too deeply to parse"
        ) from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidBuildRecordError(reason) from None
    return _checked(document)


def validate(document):
    """Check ``document``, a parsed ``build.json``, against ADR-0198 decision 5.

    Raises :class:`UnsupportedVersionError` for an integer ``schema_version``
    from 0 to :data:`hilclaw.keys.MAX_INTEGER` other than 1, before any other
    member is looked at, and :class:`InvalidBuildRecordError` for the first
    other rule found broken: a member missing or not admitted, an
    ``outcome`` or ``condition`` outside its list, a ``condition`` with the
    outcome ``"built"`` or none with ``"broken"``, or an argument array that
    is not one of strings of at least one character without U+0000.
    """
    _checked(document)


def read(data_root, run_id, round, candidate, attempt):
    """Return the :class:`BuildRecord` of an attempt, read from its ``build.json``.

    The path is :func:`hilclaw.layout.attempt_artefact` for the tuple and
    ``build.json``; no other file is read and nothing is written. Raises
    :class:`hilclaw.layout.InvalidPathValueError` for a tuple that names no
    attempt; :class:`FileNotFoundError` or :class:`NotADirectoryError` when
    ``data_root`` is no existing directory; :class:`MissingBuildRecordError`
    when there is no file; :class:`InvalidBuildRecordError` when the path is
    no regular file or the content is invalid, and
    :class:`UnsupportedVersionError` for another version, each message
    prefixed with the path below ``data_root``; an :class:`OSError` of the
    file system, unchanged, when the file cannot be read.
    """
    numbers = round, candidate, attempt
    path = layout.attempt_artefact(data_root, run_id, *numbers, "build.json")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    file = path.relative_to(root).as_posix()
    try:
        status = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        reason = f"{file}: is missing: no build record was written for this attempt"
        raise MissingBuildRecordError(reason) from None
    if not stat.S_ISREG(status.st_mode):
        raise InvalidBuildRecordError(f"{file}: is not a regular file")
    try:
        return parse(path.read_bytes())
    except (InvalidBuildRecordError, UnsupportedVersionError) as error:
        raise type(error)(f"{file}: {error}") from None


def _fail(place, rule, value):
    raise InvalidBuildRecordError(f"{place}: must be {rule}, got {reprlib.repr(value)}")


def _checked(document):
    if type(document) is not dict:
        _fail("document", "an object", document)
    if "schema_version" not in document:
        raise InvalidBuildRecordError("document: lacks the member schema_version")
    version = document["schema_version"]
    if type(version) is not int or not 0 <= version <= keys.MAX_INTEGER:
        _fail("schema_version", f"an int from 0 to {keys.MAX_INTEGER}", version)
    if version != SCHEMA_VERSION:
        raise UnsupportedVersionError(f"schema_version: {version} is not supported")
    for name in _MEMBERS:
        if name not in document:
            raise InvalidBuildRecordError(f"document: lacks the member {name}")
    for name in document:
        if name not in (*_MEMBERS, "condition"):
            _fail("document", "an object without the member", name)
    outcome = document["outcome"]
    if type(outcome) is not str or outcome not in OUTCOMES:
        _fail("outcome", " or ".join(OUTCOMES), outcome)
    condition = None
    if outcome == "broken":
        if "condition" not in document:
            raise InvalidBuildRecordError("document: lacks the member condition")
        condition = document["condition"]
        if type(condition) is not str or condition not in CONDITIONS:
            _fail("condition", " or ".join(CONDITIONS), condition)
    elif "condition" in document:
        _fail("condition", 'absent when outcome is "built"', document["condition"])
    flags = _arguments("flags", document["flags"])
    trailing = _arguments("trailing_flags", document["trailing_flags"])
    return BuildRecord(outcome, condition, flags, trailing)


def _arguments(place, value):
    if type(value) is not list:
        _fail(place, "an array", value)
    for index, item in enumerate(value):
        if type(item) is not str or not item or "\0" in item:
            _fail(
                f"{place}[{index}]",
                "a str of at least one character without U+0000",
                item,
            )
    return value
