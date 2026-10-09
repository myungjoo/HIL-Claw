"""The spec of a coder call as a file: its text form, its final name and its write (ADR-0029).

``ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md`` fixes what the bytes of
the file ``.../coder/candidates/<CC>/attempts/<AA>/spec.json`` are (decision 2),
how the ``id`` of its content stands to the path it is under (decision 3) and
by which steps the bytes come under that name (decisions 4 to 7). This module
is the first two as far as one content shows them, as two pure functions, and
the steps as a third function: :func:`parse` turns the bytes of a content into
its document or refuses them, :func:`final_name` gives the one path the ``id``
of a document formats to, and :func:`write` puts a valid content of version 1
under that path if the name is free. The rule of decision 3 for a file at a
path is ``final_name(data_root, parse(content)) == path`` for whoever holds
both; no function here takes a path.

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

The steps of the record that :func:`write` holds (decision 4): the whole
content first, valid by decisions 2 and 3 as far as one content shows it and
in the written form; a new temporary file beside the final name, holding the
whole content; its content brought to stable storage; one last step that
gives the final name only if that name does not exist and otherwise changes
nothing; and the temporary file removed when a step fails before the name is
given. The final name is the path the ``id`` of the content formats to and no
other (decision 3). The temporary file is ``spec.json.<token>.tmp`` in the
attempt directory of the final name (decision 6). The last step is a hard
link from the temporary name to the final name, followed by the removal of
the temporary name. There is no fallback to a replacing rename: where the
link is not possible the write fails and has put nothing under the final
name. Every missing directory between the data root and the final name is
created, and neither the presence nor the absence of any of them nor of any
other file below the data root is required (decision 5).

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
- :func:`write` takes the content as ``bytes`` and writes it as given: it
  builds no bytes from a document, and it takes no tuple, no ``run_id`` and no
  path.
- The checks of :func:`write` come in this order: the validity of the content
  (:func:`parse`), then its path (:func:`final_name`), then its written form,
  then ``data_root``, then the file system. Nothing is created before the
  last of them. A ``data_root`` that is no path is the :class:`TypeError` of
  :func:`final_name` and so comes with the path.
- What :func:`parse` and :func:`final_name` raise for a content passes through
  :func:`write` unchanged: a content of another version keeps
  :class:`UnsupportedVersionError` and a content without a path keeps
  :class:`hilclaw.layout.InvalidPathValueError`. A valid content with a path
  that is not in the written form of decision 2 raises
  :class:`WrittenFormError`. The written form is checked as: the content ends
  with a line feed and holds no carriage return byte. No member order,
  indentation or number of lines is checked.
- ``data_root`` is a ``str`` or a path, is not resolved and must be an existing
  directory (:class:`FileNotFoundError` or :class:`NotADirectoryError`
  otherwise); it is never created. The directories a write creates stay when a
  later step fails.
- ``<token>`` is the process id, a hyphen and 16 random hexadecimal characters.
- A final name that the last step finds taken raises :class:`NameTakenError`,
  which is no :class:`OSError`. Every other step that fails raises its
  :class:`OSError` unchanged, as the other writers of the package do; a
  temporary name in use and a file in the place of a directory are among
  them, and may be a :class:`FileExistsError`.
- The temporary file is removed after any exception raised before the final
  name is given, an interrupt included. A removal that fails is not reported
  in the place of the failure it follows. Once the final name is given, a
  removal that fails is not reported at all: the write has happened and the
  temporary name stays as a second name of the file. An interrupt that
  arrives after the link leaves the file under the final name.
- Only the file this call created is removed: a file of the name form that
  another write left is not listed, read, removed or given the final name
  (decision 6).
- The new file has the mode a newly created file gets from the process, and
  the directories above the final name are used as the operating system
  resolves them.

Limits of :func:`write` (decision 7): when the final name was not taken before
the write, the death of the writing process leaves no file under it or the
whole one; a name that was taken holds what it held. Nothing is promised for
the loss of the machine, and the directory entry is not flushed. This holds on
the POSIX systems of C-7 whose file system gives the hard link: nothing is
stated for a network file system, for a Windows drive seen from WSL or for
native Windows. Two writers at once are not prevented: one is given the name,
the other finds it taken, and the file is never a mixture of the two. The
name is given once only against another write by these steps: nothing here
prevents a process from writing, replacing or removing the file by other
means.

What this module does not do: :func:`parse` and :func:`final_name` write,
read, open, create and list no file or directory, and they do not check the
written form, which binds a write. :func:`write` reads no file, the one under
the final name included, lists no directory, compares nothing and knows no
"same content"; it creates, enters, reads and lists no ``output`` in the
attempt directory of the final name (decision 6); it composes no content and
fills in no value; it takes no lock, makes no commit and writes no other
file. The module builds no spec and no bytes; it
does not say that a content is right beyond decisions 2 and 3, that a coder
was or will be called with it or that the coder reads the file; it reads no
other version; and it is no tool. What composes or writes a spec, when, in
which order against any other file, what follows a taken name and what a
second write for a tuple means are open (OD-23, sub-questions 10 and 26 of
OD-8).
"""

import codecs
import contextlib
import json
import os
import re
import secrets
from pathlib import Path

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


class WrittenFormError(ValueError):
    """A valid content is not in the written form of ADR-0029 decision 2; the message names the rule.

    It is no :class:`InvalidSpecFileError`: :func:`parse` accepts the content.
    """


class NameTakenError(Exception):
    """The last step found the final name taken; the content was not written.

    It is no :class:`OSError`, so a failure of the file system and a taken
    name are told apart by class. It says nothing of what is under the name:
    that entry was not opened, read or compared.
    """


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


def write(data_root, content):
    """Put ``content`` under the path its ``id`` formats to if that name is free; return ``None``.

    ``content`` is the whole file as ``bytes``, and the final name is
    ``final_name(data_root, parse(content))`` (ADR-0029 decisions 3 and 4). A
    call that returns has given the final name to a file of exactly these
    bytes: nothing is added, removed, defaulted or normalised. The final name
    is never opened, and this call puts nothing under it before the last
    step. Every missing directory between ``data_root`` and the final name is
    created; nothing else below ``data_root`` is required, read or listed.

    Raises, before the file system is touched and in this order: what
    :func:`parse` raises for ``content`` (:class:`TypeError`,
    :class:`InvalidSpecFileError`, or :class:`UnsupportedVersionError` for
    another version, which is not written); what :func:`final_name` raises
    (:class:`hilclaw.layout.InvalidPathValueError` for a valid content whose
    ``id.run_id`` is no run directory name, :class:`TypeError` for a
    ``data_root`` that is no path); :class:`WrittenFormError` for a content
    that does not end with a line feed or holds a carriage return byte.
    Nothing is created then.

    Raises :class:`FileNotFoundError` or :class:`NotADirectoryError` for a
    ``data_root`` that is no existing directory, and the :class:`OSError` of
    the step that failed (the creation of a directory or of the temporary
    file, the write, the flush, the link). This call has then put nothing
    under the final name, and its temporary file is removed where that is
    possible; the directories it created stay.

    Raises :class:`NameTakenError` when the link finds the final name taken,
    whatever is there and whatever its content: equal bytes are reported as
    any other. This call leaves the entry under the name as it found it and
    removes its temporary file where that is possible. Nothing is retried.
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
    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    temporary = path.with_name(f"{path.name}.{token}.tmp")
    created = False
    try:
        with open(temporary, "xb") as f:
            created = True
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            file = path.relative_to(root).as_posix()
            reason = f"{file}: the name is taken; the content was not written"
            raise NameTakenError(reason) from None
    except BaseException:
        if created:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
        raise
    with contextlib.suppress(OSError):
        os.unlink(temporary)


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
