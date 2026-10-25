"""The hypothesis record of a round as a file: its text form, its final name and its write (ADR-0059).

``ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`` fixes the
file ``runs/<run_id>/rounds/<RRRR>/decision/hypotheses.json``: its place and
its write (decision 1) and the file as a whole (decision 2), both by the rules
ADR-0029 decisions 2 to 7 give the spec file. This module is the counterpart
of :mod:`hilclaw.spec_file` for this record: :func:`parse` turns the bytes of
a content into its document or refuses them, :func:`final_name` gives the one
path its ``run_id`` and ``round`` format to, and :func:`write` puts a valid
content under that path if the name is free. The rule "``run_id`` and
``round`` against the path" of decision 2 is
``final_name(data_root, parse(content)) == path`` for whoever holds both; no
function here takes a path.

The rules :func:`parse` holds: the content is exactly one JSON text that is an
object, in UTF-8 without a byte order mark, with no member name twice in any
object, unknown top-level members included (a rule for the whole text,
ADR-0018 decision 2); the document is valid by ADR-0059 decisions 2 to 5 and
by the in-file rules of ADR-0073 decisions 2 and 3 for the basis kind ``case``
and the optional top-level member ``cases_read`` and of ADR-0075 decision 3
for the origin ``injected`` and its member ``injection``
(:func:`hilclaw.hypotheses.validate`); and a number at an *integer* place,
below ``cases_read`` included, is written in decimal digits without sign,
fraction or exponent, so ``-0``, which parses to the ``int`` 0, is refused by
its text. The top level is open: below a top-level member that neither
ADR-0059 nor ADR-0073 defines, the record sets no rule for a number, and
neither does this module. A sign, a fraction, an exponent and an
integer above 2**53 - 1 are accepted there and returned as parsed; a number
beyond the float range there is read as an infinity. Every other number of a
valid document stands at an *integer* place. A content whose
``schema_version`` is an *integer* other than 1 is set apart and not called
damage (OD-11): no member of it but ``schema_version`` is looked at.

The checks of :func:`parse` come in this order: the type; the byte order mark;
the encoding and the JSON text, a member name twice included; that the text is
an object; the version; :func:`hilclaw.hypotheses.validate`; the spelling
``-0``. A content this interpreter cannot read (an integer literal too long for
it, nesting too deep) is refused too, though that is a limit of this reader
and no rule of the record.

The steps :func:`write` holds (ADR-0029 decisions 4 to 7, with this final
name): the checks first, in the order :func:`parse`, :func:`final_name`, the
written form (the content ends with a line feed and holds no carriage return
byte; no member order, indentation or line count is checked), ``data_root``
(an existing directory, never created); then every missing directory between
``data_root`` and the final name is created, and
:func:`hilclaw.once_write.write_once` writes the temporary file
``hypotheses.json.<token>.tmp`` in ``decision/``, brings it to stable storage,
gives the final name by a hard link with no fallback to a replacing rename,
and removes the temporary file. Nothing is created before the last check.

The conventions of :mod:`hilclaw.spec_file` that the record does not fix apply
here as stated there, with its names read as those of this module: a content
is exactly ``bytes``; the document is a new ``dict`` with nothing added,
defaulted or repaired; one class, :class:`InvalidHypothesisFileError`, says
"invalid" for a content and wraps what :func:`hilclaw.hypotheses.validate`
raises with its message unchanged; :func:`final_name` validates its document
itself and lets :class:`hilclaw.hypotheses.InvalidHypothesisRecordError` and
:class:`hilclaw.layout.InvalidPathValueError` pass through; ``data_root`` is
a ``str`` or a path, used as given and not resolved; ``<token>`` and the
handling of the temporary file are those of
:func:`hilclaw.once_write.write_once`, which removes only the file this call
created and never touches a leftover of another write; a taken name raises
:class:`NameTakenError` and every other failing step its :class:`OSError`
unchanged; the directories created stay.

Limits of :func:`write` (ADR-0029 decision 7): when the final name was not
taken before the write, the death of the writing process leaves no file under
it or the whole one. This holds on the POSIX systems of C-7 whose file system
gives the hard link; nothing is stated for a network file system, for a
Windows drive seen from WSL or for native Windows. Two writers at once are not
prevented: one is given the name and the other finds it taken. Nothing here
prevents a process from writing, replacing or removing the file by other
means.

What this module does not do: :func:`parse` and :func:`final_name` read,
create and list no file or directory. :func:`write` reads no file, the one
under the final name included, lists no directory, knows no "same content",
composes no content, takes no lock and makes no commit. Nothing here checks
what one content does not show: ``candidates`` against the ``id.candidates``
of the round's specs, a ``ref`` naming an attempt that exists, a ``metric``
against the run's ``instance.json``, the rules between files of ADR-0073
decisions 2 and 3 (a ``case`` entry or a ``cases_read`` entry against the
cases of the key directory) and of ADR-0075 decision 3 (an ``injection``
against the ``injections`` of the run's ``instance.json``). It reads no other
version (OD-11) and is no tool. Which agent writes the file and when, what follows a taken name and
what a second write for a round means are open (ADR-0059 Boundaries; OD-23,
OD-18, OD-17).
"""

import codecs
import json
from pathlib import Path

from hilclaw import hypotheses, keys, layout, once_write

_DEFINED = (
    "schema_version",
    "run_id",
    "round",
    "candidates",
    "hypotheses",
    "cases_read",
)
_MINUS_ZERO = object()


class InvalidHypothesisFileError(ValueError):
    """A content breaks the text form, a rule of ADR-0059 decisions 2 to 5 or of ADR-0073, or cannot be read by this interpreter.

    The message names the field path and the rule. The second case is a
    limit of this reader and no rule of the record (module docstring).
    """


class UnsupportedVersionError(Exception):
    """``schema_version`` is an integer other than 1: not damage, and nothing is interpreted (OD-11)."""


class WrittenFormError(ValueError):
    """A valid content is not in the written form of ADR-0029 decision 2; the message names the rule.

    It is no :class:`InvalidHypothesisFileError`: :func:`parse` accepts the
    content.
    """


class NameTakenError(Exception):
    """The last step found the final name taken; the content was not written.

    It is no :class:`OSError`. It says nothing of what is under the name:
    that entry was not opened, read or compared.
    """


def parse(content):
    """Return the document of ``content``, the bytes of a version-1 hypothesis record file (ADR-0059 decision 2).

    The result is the ``dict`` :func:`json.loads` gives for the text. Any
    order of members, any white space of JSON, any line ends and a missing
    final line feed are accepted. ``content`` is not modified or kept.

    Raises :class:`TypeError` when ``content`` is not exactly ``bytes``.
    Raises :class:`InvalidHypothesisFileError` when ``content`` is not UTF-8
    without a byte order mark, is not exactly one JSON text (``NaN``,
    ``Infinity`` and ``-Infinity`` are no JSON; an empty content is none), is
    no object, holds a member name twice in any object, is a document
    :func:`hilclaw.hypotheses.validate` refuses or writes ``-0`` at an
    *integer* place, and when this interpreter cannot read the text. Raises
    :class:`UnsupportedVersionError`, before any other member is looked at,
    when ``schema_version`` is an ``int`` from 0 to
    :data:`hilclaw.keys.MAX_INTEGER` other than 1 and not written ``-0``.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidHypothesisFileError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_object, parse_constant=_nan)
        spelling = json.loads(text, parse_int=_literal)
    except RecursionError:
        reason = "content: is nested too deeply to parse"
        raise InvalidHypothesisFileError(reason) from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidHypothesisFileError(reason) from None
    if type(document) is not dict:
        kind = type(document).__name__
        raise InvalidHypothesisFileError(f"content: must be a JSON object, got {kind}")
    version = document.get("schema_version")
    other = type(version) is int and version != hypotheses.SCHEMA_VERSION
    if other and 0 <= version <= keys.MAX_INTEGER:
        _unsigned("schema_version", spelling["schema_version"])
        expected = hypotheses.SCHEMA_VERSION
        raise UnsupportedVersionError(f"schema_version: is {version}, not {expected}")
    try:
        hypotheses.validate(document)
    except hypotheses.InvalidHypothesisRecordError as error:
        raise InvalidHypothesisFileError(str(error)) from error
    for name, value in spelling.items():
        if name in _DEFINED:
            _unsigned(name, value)
    return document


def final_name(data_root, document):
    """Return the path the ``run_id`` and ``round`` of ``document`` format to (ADR-0059 decisions 1 and 2).

    The result is what :func:`hilclaw.layout.hypothesis_record` builds for
    ``run_id`` and ``round`` below ``Path(data_root)``, which is used as
    given. Nothing is read, created, resolved or checked on disk, and
    ``document`` is not modified.

    ``document`` is validated first: raises
    :class:`hilclaw.hypotheses.InvalidHypothesisRecordError` for a document
    :func:`hilclaw.hypotheses.validate` refuses, a document of another
    ``schema_version`` among them. Raises
    :class:`hilclaw.layout.InvalidPathValueError` for a valid document whose
    ``run_id`` is no run directory name, and :class:`TypeError` for a
    ``data_root`` that is no path.
    """
    hypotheses.validate(document)
    return layout.hypothesis_record(data_root, document["run_id"], document["round"])


def write(data_root, content):
    """Put ``content`` under ``final_name(data_root, parse(content))`` if that name is free; return ``None``.

    ``content`` is the whole file as ``bytes``. A call that returns has given
    the final name to a file of exactly these bytes. The final name is never
    opened, and this call puts nothing under it before the last step. Every
    missing directory between ``data_root`` and the final name is created;
    nothing else below ``data_root`` is required, read or listed.

    Raises, before the file system is touched and in this order: what
    :func:`parse` raises for ``content`` (:class:`TypeError`,
    :class:`InvalidHypothesisFileError`, :class:`UnsupportedVersionError`);
    what :func:`final_name` raises (:class:`hilclaw.layout.InvalidPathValueError`,
    :class:`TypeError` for a ``data_root`` that is no path);
    :class:`WrittenFormError` for a content that does not end with a line
    feed or holds a carriage return byte; :class:`FileNotFoundError` or
    :class:`NotADirectoryError` for a ``data_root`` that is no existing
    directory. Nothing is created then.

    Raises the :class:`OSError` of the step that failed (the creation of a
    directory or of the temporary file, the write, the flush, the link): this
    call has then put nothing under the final name, its temporary file is
    removed where that is possible, and the directories it created stay.
    Raises :class:`NameTakenError` when the link finds the final name taken,
    equal bytes included; the entry under the name is left as it was found.
    Nothing is retried.
    """
    path = final_name(data_root, parse(content))
    if not content.endswith(b"\n"):
        raise WrittenFormError("content: does not end with a line feed")
    if b"\r" in content:
        raise WrittenFormError("content: holds a carriage return byte")
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if once_write.write_once(path, content) is not None:
        file = path.relative_to(root).as_posix()
        reason = f"{file}: the name is taken; the content was not written"
        raise NameTakenError(reason) from None


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
    if value is _MINUS_ZERO:
        message = f"{path}: is written as -0, which is no integer"
        raise InvalidHypothesisFileError(message)
    if isinstance(value, dict):
        for name, item in value.items():
            _unsigned(f"{path}.{name}", item)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _unsigned(f"{path}[{index}]", item)
