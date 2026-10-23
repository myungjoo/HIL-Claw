"""The reader of the technique catalog (ADR-0150 decision 2 and Consequences slice 1).

:func:`check` checks one accelerator's directory of the catalog and
:func:`technique` returns what one entry gives a spec. ``spec.write``
(:mod:`hilclaw.spec_tool`) calls :func:`technique` for each id of its request
and checks the rule of decision 4 against the spec it composes (ADR-0151
decision 2 (b)); which ids a spec carries is the selection side's (HQ-0048).
It is no registry tool, calls no model, starts no process and writes nothing.

**Decided by ADR-0150** and only applied here: the catalog is ``catalog/``
(:data:`SOURCE`), with one directory per ``accelerator`` value holding one file
``<id>.md`` per entry, the id a *name* of ADR-0001, and nothing else; an entry
file is UTF-8 with LF line ends and has, in this order and with no other
heading of level 1 or 2, ``# <id>``, ``## Applies to`` with the lines of
:data:`APPLIES_TO`, ``## When`` and ``## Guidance``; its ``text`` is the content
of ``## Guidance`` to the end of the file with leading and trailing line feeds
removed, and it gives a spec exactly ``{"id": <id>, "text": <text>}``
(decisions 2 to 4).

**Choices of this module**; a breach of them or of the rules above raises
:class:`InvalidCatalogError`:

- the accelerator's directory is a plain directory holding plain files only:
  no symbolic link, junction or subdirectory;
- a file does not start with a byte order mark;
- a heading is a line that starts with ``#`` or ``##`` once leading blanks,
  ``>`` and list markers are removed, or that holds an ``<h1`` or ``<h2`` tag,
  inside a fenced code block too; below a non-blank line, a line of ``=`` or
  ``-`` signs is refused, with any leading spaces, tabs or ``>`` and any
  trailing white space;
- the lines of :data:`APPLIES_TO` come in that order, with only blank lines
  before and after them; ``## When`` and the ``text`` are not blank.

An empty directory gives no entry. The rule of decision 4 against a spec is
not checked here: ``spec.write`` checks it. **Also raised**: :class:`TypeError` for an
``accelerator`` or id that is not a ``str`` or a ``source`` that is not a
``str`` or path object; :class:`FileNotFoundError` for a missing directory;
:class:`KeyError` for a well-formed id that names no entry; and, unchanged,
what reading the directory or a file raises.
"""

import os
import re
import stat
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "catalog"
APPLIES_TO = ("- kind: gemm", "- dtype: fp32", "- layout: row_major", "- language: c")

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_FILE_NAME = re.compile(r"([a-z][a-z0-9_]{0,31})\.md")
_PREFIX = re.compile(r"(?:[ \t]*(?:>|[-*+](?=[ \t])|[0-9]{1,9}[.)](?=[ \t])))*[ \t]*")
_HEADING = re.compile(r"#{1,2}(?:[ \t]|$)")
_HTML_HEADING = re.compile(r"<h[12](?:[\s/>]|$)", re.IGNORECASE)
_UNDERLINE = re.compile(r"(?:=+|-+)[ \t]*")
_BOM = b"\xef\xbb\xbf"
_JUNCTION_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)


class InvalidCatalogError(ValueError):
    """An accelerator's directory or an entry file breaks a rule of ADR-0150 or of this module."""


def _path(value, what):
    if isinstance(value, (str, os.PathLike)):
        value = os.fspath(value)
    if type(value) is not str:
        raise TypeError(f"{what} must be a str or a path")
    return value


def _name(value, what):
    if type(value) is not str:
        raise TypeError(f"{what} must be a str")
    if not _NAME.fullmatch(value):
        raise InvalidCatalogError(f"{what} must be a name matching {_NAME.pattern}")


def _kind(path):
    examined = os.lstat(path)
    tag = getattr(examined, "st_reparse_tag", 0)
    if stat.S_ISLNK(examined.st_mode) or tag == _JUNCTION_TAG:
        return "link"
    if stat.S_ISDIR(examined.st_mode):
        return "directory"
    if stat.S_ISREG(examined.st_mode):
        return "file"
    return "other"


def _headings(lines):
    found = []
    above = False
    for index, line in enumerate(lines):
        body = line[_PREFIX.match(line).end() :]
        if _HEADING.match(body) or _HTML_HEADING.search(line):
            found.append(index)
            above = False
            continue
        if above and _UNDERLINE.fullmatch(line.lstrip(" \t>")):
            raise InvalidCatalogError("an entry file underlines a line as a heading")
        above = bool(body.strip())
    return found


def _entry(path, entry_id):
    data = Path(path).read_bytes()
    if data.startswith(_BOM):
        raise InvalidCatalogError("an entry file starts with a byte order mark")
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidCatalogError("an entry file is not UTF-8") from None
    if "\r" in content:
        raise InvalidCatalogError("an entry file holds a carriage return")
    lines = content.split("\n")
    if lines[0] != f"# {entry_id}":
        raise InvalidCatalogError("an entry file does not start with '# ' and its id")
    found = _headings(lines)
    expected = [f"# {entry_id}", "## Applies to", "## When", "## Guidance"]
    if [lines[index] for index in found] != expected:
        raise InvalidCatalogError("an entry file has other headings than ADR-0150's")
    applies = [line.strip() and line for line in lines[found[1] + 1 : found[2]]]
    if "\n".join(applies).strip("\n").split("\n") != list(APPLIES_TO):
        raise InvalidCatalogError("Applies to is not the four lines of ADR-0150")
    if not "\n".join(lines[found[2] + 1 : found[3]]).strip():
        raise InvalidCatalogError("the When section is empty")
    text = "\n".join(lines[found[3] + 1 :]).strip("\n")
    if not text.strip():
        raise InvalidCatalogError("the Guidance section is empty")
    return text


def _read(accelerator, source):
    _name(accelerator, "accelerator")
    origin = _path(SOURCE if source is None else source, "source")
    directory = os.path.join(origin, accelerator)
    if not os.path.lexists(directory):
        raise FileNotFoundError(f"no catalog directory: {directory!r}")
    if _kind(directory) != "directory":
        raise InvalidCatalogError("the accelerator's catalog is not a plain directory")
    texts = {}
    for entry in sorted(os.scandir(directory), key=lambda entry: entry.name):
        kind = _kind(entry.path)
        if kind == "link":
            raise InvalidCatalogError("the catalog holds a symbolic link or a junction")
        if kind != "file":
            raise InvalidCatalogError("the catalog holds an entry that is not a file")
        matched = _FILE_NAME.fullmatch(entry.name)
        if not matched:
            raise InvalidCatalogError("the catalog holds a file not named '<name>.md'")
        texts[matched.group(1)] = _entry(entry.path, matched.group(1))
    return texts


def check(accelerator, *, source=None):
    """Check the catalog directory of ``accelerator`` and return the ids of its entries.

    ``accelerator`` is the ``accelerator`` value of a hw_profile, a ``str`` of
    the *name* form; ``source`` (a ``str`` or path object; ``None``:
    :data:`SOURCE`) names the catalog root that holds the directory
    ``<accelerator>``. Every file of that directory is read and checked as the
    module docstring says. Returns a ``tuple`` of the ids in sorted order.
    Raises as the module docstring lists.
    """
    return tuple(_read(accelerator, source))


def technique(accelerator, entry_id, *, source=None):
    """Return what the entry ``entry_id`` of ``accelerator`` gives a spec.

    ``accelerator`` and ``source`` are as for :func:`check`; ``entry_id`` is
    a ``str`` of the *name* form. After the whole directory has passed
    :func:`check`, returns a new ``dict`` ``{"id": entry_id, "text": text}``,
    the member of ``guidance.techniques`` of ADR-0150 decision 4; the rule of
    that decision against a spec is checked by ``spec.write``
    (:mod:`hilclaw.spec_tool`), not here. Raises :class:`KeyError` when
    no entry has the id, and otherwise as the module docstring lists.
    """
    _name(entry_id, "entry_id")
    texts = _read(accelerator, source)
    if entry_id not in texts:
        raise KeyError(entry_id)
    return {"id": entry_id, "text": texts[entry_id]}
