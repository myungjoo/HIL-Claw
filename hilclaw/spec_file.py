"""The spec of a coder call as a file: its text form and its final name (ADR-0029).

``ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`` fixes what the bytes of
the file ``.../coder/candidates/<CC>/attempts/<AA>/spec.json`` are (decision 2)
and how the ``id`` of its content stands to the path it is under (decision 3).
This module is those two decisions as far as one content shows them, as pure
functions: :func:`parse` turns the bytes of a content into its document or
refuses them, and :func:`final_name` gives the one path the ``id`` of a
document formats to. The rule of decision 3 for a file at a path is
``final_name(data_root, parse(content)) == path`` for whoever holds both; no
function here takes a path.

The rules of the record that :func:`parse` holds: the content is exactly one
JSON text that is an object, in UTF-8 without a byte order mark, with no
member name twice in any object; the document it parses to is valid by
ADR-0002 (:func:`hilclaw.spec.validate`, with the limits of its docstring);
and a number at an *integer* place is written in decimal digits without sign,
fraction or exponent. ``1.0`` and ``1e0`` are refused there by
:func:`hilclaw.spec.validate`, which takes an integer as exactly an ``int``.
``-0`` parses to the ``int`` 0, so it is refused by its text. In a document
:func:`hilclaw.spec.validate` accepts, every number stands at an *integer*
place unless it is below one of the three places where ADR-0002 allows any
JSON value or lists no members: ``task.objective``, the ``profile`` of an
entry of ``feedback.attempts`` and the top-level ``ext``. The ``ext`` of an
embedded record is none of the three: its values are strings or integers.
Below those three places the record adds no rule for a number beyond the
grammar of JSON, and neither does this module: a sign, a fraction, an
exponent and an integer above 2**53 - 1 are accepted there and returned as
parsed, and nothing here says that such a number is a value of its member.
A content whose ``schema_version`` is an *integer* other than 1 is set apart
from an invalid one (decision 2; what such a file is and how it is read is
OD-11).

Conventions of this module, which the record does not fix:

- A content is exactly ``bytes`` (:class:`TypeError` otherwise: the encoding is
  part of validity). The document is returned as :func:`json.loads` gives it:
  a new ``dict`` at every call, with nothing added, defaulted, normalised or
  repaired.
- Every broken rule of the text and of ADR-0002 raises
  :class:`InvalidSpecFileError`, so one class says "invalid" for a content;
  what :func:`hilclaw.spec.validate` raises is wrapped with its message
  unchanged. Another version raises :class:`UnsupportedVersionError` of this
  module, which is no :class:`ValueError`.
- The checks of :func:`parse` come in this order: the type; the byte order
  mark; the encoding and the JSON text, a member name twice included; that
  the text is an object; the version; :func:`hilclaw.spec.validate`; the
  spelling ``-0``. The rules for the whole text therefore come before the
  version, and the version before every other member.
- A content this interpreter cannot read (an integer literal too long for it
  anywhere in the text, nesting too deep) raises :class:`InvalidSpecFileError`
  too, though it is a limit of this reader and no rule of the record; the
  limits stay as the interpreter has them. A number beyond the float range
  below one of the three places is read as an infinity and is no error, as
  :mod:`hilclaw.run_state` has it.
- :func:`final_name` validates its document itself and lets
  :class:`hilclaw.spec.InvalidSpecError` pass through: its argument is a
  document and no content, and the spelling of a number is not its matter. A
  valid document whose ``id.run_id`` is no run directory name has no path
  (decision 3): :class:`hilclaw.layout.InvalidPathValueError` passes through,
  the class of the module that holds the rule for that name. :func:`parse`
  accepts such a content, which stays a valid document.

What this module does not do: it writes, reads, opens, creates and lists no
file or directory; it does not check the written form (line ends, a final
line feed), which binds a writer; it builds no spec and no bytes; it does not
say that a content is right beyond the two decisions, that a coder was or will
be called with it or that the coder reads the file; it compares a content with
no other file; it reads no other version; and it is no tool. The write by the
steps of decision 4 is not in it.
"""

import codecs
import json
import re

from hilclaw import keys, layout, spec

_FREE = re.compile(r"ext|task\.objective|feedback\.attempts\[[0-9]+\]\.profile")
_MINUS_ZERO = object()


class InvalidSpecFileError(ValueError):
    """A content breaks a rule of ADR-0029 decision 2 or cannot be read by this interpreter.

    The message names the place. The second case is a limit of this reader
    and no rule of the record (module docstring).
    """


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted."""


def parse(content):
    """Return the document of ``content``, the bytes of a spec file (ADR-0029 decision 2).

    The result is the ``dict`` :func:`json.loads` gives for the text. Any
    order of members, any white space of JSON, any line ends and a missing
    final line feed are accepted. ``content`` is not modified or kept.

    Raises :class:`InvalidSpecFileError` when ``content`` is not UTF-8 without
    a byte order mark, is not exactly one JSON text (the tokens ``NaN``,
    ``Infinity`` and ``-Infinity`` are no JSON; an empty content is none), is
    no object, holds a member name twice in any object, is a document
    :func:`hilclaw.spec.validate` refuses or writes ``-0`` at an *integer*
    place, and also when this interpreter cannot read the text (an integer
    literal too long for it, nesting too deep), which is no rule of the
    record. Raises :class:`UnsupportedVersionError`, before any other member is
    looked at, when the text passes the rules for the whole text and its
    ``schema_version`` is an ``int`` from 0 to :data:`hilclaw.keys.MAX_INTEGER`
    other than 1 and not written ``-0``. Nothing is returned then, and nothing
    is repaired. The order of the checks is in the module docstring.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidSpecFileError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_object, parse_constant=_nan)
        spelling = json.loads(text, parse_int=_literal)
    except RecursionError:
        raise InvalidSpecFileError("content: is nested too deeply to parse") from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidSpecFileError(reason) from None
    if type(document) is not dict:
        kind = type(document).__name__
        raise InvalidSpecFileError(f"content: must be a JSON object, got {kind}")
    version = document.get("schema_version")
    other = type(version) is int and version != spec.SCHEMA_VERSION
    if other and 0 <= version <= keys.MAX_INTEGER:
        _unsigned("schema_version", spelling["schema_version"])
        raise UnsupportedVersionError(f"schema_version: is {version}, not 1")
    try:
        spec.validate(document)
    except spec.InvalidSpecError as error:
        raise InvalidSpecFileError(str(error)) from error
    _unsigned("", spelling)
    return document


def final_name(data_root, document):
    """Return the path the ``id`` of ``document`` formats to (ADR-0029 decision 3).

    The result is what :func:`hilclaw.layout.attempt_artefact` builds for
    ``id.run_id``, ``id.round``, ``id.candidate``, ``id.attempt`` and
    ``spec.json`` below ``Path(data_root)``, which is used as given. Nothing
    is read, created, resolved or checked on disk, and ``document`` is not
    modified.

    ``document`` is validated first, so no unchecked member yields a path:
    raises :class:`hilclaw.spec.InvalidSpecError` for a document
    :func:`hilclaw.spec.validate` refuses, a document of another
    ``schema_version`` among them. Raises
    :class:`hilclaw.layout.InvalidPathValueError` for a valid document whose
    ``id.run_id`` is no run directory name: it has no path.
    """
    spec.validate(document)
    ident = document["id"]
    numbers = ident["round"], ident["candidate"], ident["attempt"]
    return layout.attempt_artefact(data_root, ident["run_id"], *numbers, "spec.json")


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _nan(name):
    raise ValueError(f"{name} is not a JSON value")


def _literal(literal):
    return _MINUS_ZERO if literal == "-0" else None


def _unsigned(path, value):
    if _FREE.fullmatch(path):
        return
    if value is _MINUS_ZERO:
        raise InvalidSpecFileError(f"{path}: is written as -0, which is no integer")
    if isinstance(value, dict):
        for name, item in value.items():
            _unsigned(f"{path}.{name}" if path else name, item)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _unsigned(f"{path}[{index}]", item)
