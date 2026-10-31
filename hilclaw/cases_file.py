"""The stored hypothesis-outcome case of a round as a file: its text form, its final name and its write (ADR-0072).

``ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`` fixes
the file ``db/<hw_profile_key>/<op_signature>/case-<run_id>-<RRRR>.json``: its
place and its write (decision 1) and the file as a whole (decision 2), by the
rules ADR-0029 decisions 2, 4, 6 and 7 give the spec file. This module is the
counterpart of :mod:`hilclaw.verdicts_file` for this record: :func:`parse`
turns the bytes of a content into its document or refuses them,
:func:`final_name` gives the one path its ``run_id`` and ``round`` format to
below a key directory, and :func:`write` puts a valid content under that path
if the name is free. The rule "the name is formed from its ``run_id`` and
``round``" of decision 2 is ``final_name(data_root, hw_profile_key,
op_signature, parse(content)) == path`` for whoever holds both; no function
here takes a path.

The rules :func:`parse` holds, in this order: the type; the byte order mark;
the encoding and the JSON text, with no member name twice in any object,
unknown members and both copies included (a rule for the whole text, ADR-0018
decision 2); that the text is an object; the versions; the document is valid
by ADR-0072 decisions 2 and 3 (:func:`hilclaw.cases.validate`), each copy by
its own record, the hypothesis copy by the in-file rules of ADR-0073
decisions 2 and 3 too; and a number at an *integer* place is written in
decimal digits without sign, fraction or exponent, so ``-0``, which parses to
the ``int`` 0, is refused by its text. That last rule covers what stands below
a defined top-level member of the case (``schema_version``, ``run_id``,
``round``) and below a defined top-level member of each copy (those of
ADR-0059 and ``cases_read`` of ADR-0073 for the hypothesis copy, those of
ADR-0071 for the verdict copy), so that a copy obeys the text rule its source
file obeys in :mod:`hilclaw.hypotheses_file` and :mod:`hilclaw.verdicts_file`.
Both top levels are open: below a top-level member of the case or of a copy
that its records do not define, ADR-0072, ADR-0059, ADR-0073 and ADR-0071 set
no rule for a number, and neither does this module. A sign, a fraction, an
exponent, ``-0`` and an integer above 2**53 - 1 are accepted there and
returned as parsed; a number beyond the float range there is read as an
infinity.

The versions are set apart before anything else is validated, and are not
called damage (OD-11): a content whose ``schema_version`` is an *integer*
other than 1; then, its own version being 1, one whose ``hypothesis_record``
is an object whose ``schema_version`` is such an *integer*; then likewise for
a present ``verdict_record``, for each copy carries its own version
(ADR-0072 decision 2). No other member of such a content is looked at. A
content this interpreter cannot read (an integer literal too long for it,
nesting too deep) is refused too, though that is a limit of this reader and no
rule of the record.

The steps :func:`write` holds (ADR-0029 decisions 4, 6 and 7, with this final
name; decision 5 is replaced by ADR-0072 decision 1): the checks first, in
the order :func:`parse`, :func:`final_name`, the written form (the content
ends with a line feed and holds no carriage return byte; no member order,
indentation or line count is checked), the key directory (an existing
directory); then :func:`hilclaw.once_write.write_once` writes the temporary
file ``case-<run_id>-<RRRR>.json.<token>.tmp`` in the key directory, brings it
to stable storage, gives the final name by a hard link with no fallback to a
replacing rename, and removes the temporary file. **No directory is ever
created**: a missing ``data_root``, ``db/``, hardware directory or key
directory fails the write with nothing stored (ADR-0072 decision 1). The other
conventions are those :mod:`hilclaw.hypotheses_file` states, with its names
read as those of this module.

Limits of :func:`write` (ADR-0029 decision 7): when the final name was not
taken before the write, the death of the writing process leaves no file under
it or the whole one. This holds on the POSIX systems of C-7 whose file system
gives the hard link; nothing is stated for a network file system, for a
Windows drive seen from WSL or for native Windows. Two writers at once are not
prevented: one is given the name and the other finds it taken. Since the
write reads no key record file, a case can be written into a key directory
that holds no record, below a key that is not stored (ADR-0072 decision 1).

What this module does not do: :func:`parse` and :func:`final_name` read,
create and list no file or directory. :func:`write` reads no file, neither the
one under the final name nor the source files in ``runs/``, ``instance.json``,
``op_signature.json`` or ``hw_profile.json``; it lists and creates no
directory, knows no "same content", composes no content
(:func:`hilclaw.cases.build` gives a document; its bytes are the caller's),
takes no lock and makes no commit. Nothing here checks that the key directory
is that of the run's instance, that the copies equal the source files in
``runs/``, that a *ref* names an attempt that exists, or the rules between
files of ADR-0073 decisions 2 and 3 for the hypothesis copy. It reads no other
version (OD-11) and is no tool, no hook and no command. For the runs of
ADR-0120 decision 1, :func:`write` is called by the tool ``case.write``
(:mod:`hilclaw.case_tool`, ADR-0133), which reads the source files and the
key records, composes the bytes and decides which rounds are promoted and
when (a round without verdicts is; a taken name is ``case_exists``). Still
open (ADR-0072 Boundaries): ``best.json`` and ``technique_stats.json``
(OD-20, OD-7), OD-29, OD-25, NFR-1, OD-17 beyond ADR-0133 decision 5, the
creation of the key directory (OD-26) and promotion in runs outside ADR-0120
decision 1. The lookup of the cases of a key directory (ADR-0073 decision 1)
is :mod:`hilclaw.case_lookup`.
"""

import codecs
import json
from pathlib import Path

from hilclaw import cases, hypotheses, json_text, keys, layout, once_write, verdicts

_DEFINED = ("schema_version", "run_id", "round")
_COPIES = {
    "hypothesis_record": (
        hypotheses.SCHEMA_VERSION,
        (
            "schema_version",
            "run_id",
            "round",
            "candidates",
            "hypotheses",
            "cases_read",
        ),
    ),
    "verdict_record": (
        verdicts.SCHEMA_VERSION,
        ("schema_version", "run_id", "round", "verdicts"),
    ),
}


class InvalidCaseFileError(ValueError):
    """A content breaks the text form or a rule of ADR-0072 decisions 2 and 3, or cannot be read by this interpreter.

    The message names the field path and the rule. The second case is a
    limit of this reader and no rule of the record (module docstring).
    """


class UnsupportedVersionError(Exception):
    """The case's or a copy's ``schema_version`` is an integer other than 1: not damage, and nothing is interpreted (OD-11)."""


class WrittenFormError(ValueError):
    """A valid content is not in the written form of ADR-0029 decision 2; the message names the rule.

    It is no :class:`InvalidCaseFileError`: :func:`parse` accepts the content.
    """


class NameTakenError(Exception):
    """The last step found the final name taken; the content was not written.

    It is no :class:`OSError`. It says nothing of what is under the name:
    that entry was not opened, read or compared.
    """


def parse(content):
    """Return the document of ``content``, the bytes of a version-1 case file (ADR-0072 decision 2).

    The result is the ``dict`` :func:`json.loads` gives for the text. Any
    order of members, any white space of JSON, any line ends and a missing
    final line feed are accepted. ``content`` is not modified or kept.

    Raises :class:`TypeError` when ``content`` is not exactly ``bytes``.
    Raises :class:`InvalidCaseFileError` when ``content`` is not UTF-8
    without a byte order mark, is not exactly one JSON text (``NaN``,
    ``Infinity`` and ``-Infinity`` are no JSON; an empty content is none), is
    no object, holds a member name twice in any object, is a document
    :func:`hilclaw.cases.validate` refuses (its message unchanged, chained) or
    writes ``-0`` at an *integer* place, and when this interpreter cannot
    read the text. Raises :class:`UnsupportedVersionError`, before any other
    member is looked at, when ``schema_version`` is an ``int`` from 0 to
    :data:`hilclaw.keys.MAX_INTEGER` other than 1 and not written ``-0``;
    then, that version being 1, when the ``schema_version`` of the object
    ``hypothesis_record`` and then of a present object ``verdict_record`` is
    such an ``int``. The message names the field path.
    """
    if type(content) is not bytes:
        raise TypeError(f"content must be bytes, got {type(content).__name__}")
    if content.startswith(codecs.BOM_UTF8):
        raise InvalidCaseFileError("content: starts with a byte order mark")
    try:
        text = content.decode("utf-8")
        document = json.loads(
            text,
            object_pairs_hook=json_text.distinct_members,
            parse_constant=json_text.no_constant,
        )
        spelling = json.loads(text, parse_int=json_text.mark_minus_zero)
    except RecursionError:
        raise InvalidCaseFileError("content: is nested too deeply to parse") from None
    except ValueError as error:
        reason = f"content: cannot be read as one JSON text: {error}"
        raise InvalidCaseFileError(reason) from None
    if type(document) is not dict:
        kind = type(document).__name__
        raise InvalidCaseFileError(f"content: must be a JSON object, got {kind}")
    version = _version("", document, spelling, cases.SCHEMA_VERSION)
    if type(version) is int and version == cases.SCHEMA_VERSION:
        for name, (expected, _) in _COPIES.items():
            if type(document.get(name)) is dict:
                _version(f"{name}.", document[name], spelling[name], expected)
    try:
        cases.validate(document)
    except cases.InvalidCaseError as error:
        raise InvalidCaseFileError(str(error)) from error
    for name, value in spelling.items():
        if name in _DEFINED:
            _unsigned(name, value)
        elif name in _COPIES:
            for member, item in value.items():
                if member in _COPIES[name][1]:
                    _unsigned(f"{name}.{member}", item)
    return document


def final_name(data_root, hw_profile_key, op_signature, document):
    """Return the path of the case ``document`` in the key directory of the two key names (ADR-0072 decisions 1 and 2).

    The result is what :func:`hilclaw.layout.case_record` builds for the key
    names and the ``run_id`` and ``round`` of ``document`` below
    ``Path(data_root)``, which is used as given. Nothing is read, created,
    resolved or checked on disk, and ``document`` is not modified. Whether the
    key directory is that of the run's instance (ADR-0072 decision 1) is a
    rule between files and is not checked.

    ``document`` is validated first: raises
    :class:`hilclaw.cases.InvalidCaseError` for a document
    :func:`hilclaw.cases.validate` refuses, a document of another
    ``schema_version`` among them. Raises
    :class:`hilclaw.layout.InvalidPathValueError` for a key name that is no
    directory name and for a valid document whose ``run_id`` is no run
    directory name, and :class:`TypeError` for a ``data_root`` that is no
    path.
    """
    cases.validate(document)
    run_id, round = document["run_id"], document["round"]
    return layout.case_record(data_root, hw_profile_key, op_signature, run_id, round)


def write(data_root, hw_profile_key, op_signature, content):
    """Put ``content`` under its :func:`final_name` if that name is free; return ``None``.

    The final name is ``final_name(data_root, hw_profile_key, op_signature,
    parse(content))``. ``content`` is the whole file as ``bytes``. A call that
    returns has given the final name to a file of exactly these bytes. The
    final name is never opened, and this call puts nothing under it before the
    last step. The key directory must exist; no directory is created, and
    nothing else below ``data_root`` is required, read or listed.

    Raises, before the file system is touched and in this order: what
    :func:`parse` raises for ``content`` (:class:`TypeError`,
    :class:`InvalidCaseFileError`, :class:`UnsupportedVersionError`); what
    :func:`final_name` raises (:class:`hilclaw.layout.InvalidPathValueError`,
    :class:`TypeError` for a ``data_root`` that is no path);
    :class:`WrittenFormError` for a content that does not end with a line
    feed or holds a carriage return byte; :class:`FileNotFoundError` or
    :class:`NotADirectoryError` for a key directory that is no existing
    directory. Nothing is created then.

    Raises the :class:`OSError` of the step that failed (the creation of the
    temporary file, the write, the flush, the link): this call has then put
    nothing under the final name, and its temporary file is removed where that
    is possible. Raises :class:`NameTakenError` when the link finds the final
    name taken, equal bytes included; the entry under the name is left as it
    was found. Nothing is retried.
    """
    path = final_name(data_root, hw_profile_key, op_signature, parse(content))
    if not content.endswith(b"\n"):
        raise WrittenFormError("content: does not end with a line feed")
    if b"\r" in content:
        raise WrittenFormError("content: holds a carriage return byte")
    key_dir = path.parent
    if not key_dir.is_dir():
        error = NotADirectoryError if key_dir.exists() else FileNotFoundError
        raise error(f"key directory is not an existing directory: {key_dir}")
    if once_write.write_once(path, content) is not None:
        file = path.relative_to(Path(data_root)).as_posix()
        reason = f"{file}: the name is taken; the content was not written"
        raise NameTakenError(reason) from None


def _version(prefix, record, spelling, expected):
    version = record.get("schema_version")
    other = type(version) is int and version != expected
    if other and 0 <= version <= keys.MAX_INTEGER:
        path = f"{prefix}schema_version"
        _unsigned(path, spelling["schema_version"])
        raise UnsupportedVersionError(f"{path}: is {version}, not {expected}")
    return version


def _unsigned(path, value):
    json_text.refuse_minus_zero(path, value, InvalidCaseFileError)
