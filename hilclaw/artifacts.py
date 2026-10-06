"""Blob records of one run, ``runs/<run_id>/artifacts.json`` (ADR-0005).

``ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md`` fixes the content of
the file: its shape (decision 2), the six members of a record (decision 3),
identity by ``sha256`` (decision 6), the changes a record may undergo
(decision 7) and the order "blob first, then record" (decision 8). This module
validates a parsed file, reads the file of a run, adds the record of a blob that
:mod:`hilclaw.cas` has stored and replaces the retention class of a record. The
path comes from :func:`hilclaw.layout.run_file`.

``data_root`` is given by the caller and must be an existing directory
(:class:`FileNotFoundError` or :class:`NotADirectoryError` otherwise). Arguments
are checked before the file system is looked at and are not modified; an error
of :mod:`hilclaw.layout` for ``run_id`` and an :class:`OSError` pass through.

Conventions of this module, which ADR-0005 does not fix:

- Strings and integers are exactly ``str`` and ``int``, objects and arrays
  exactly ``dict`` and ``list``, as :func:`json.loads` returns them.
- The file is written with the layout of the Example of ADR-0005: one line per
  record, its members in the order of the table of decision 3, UTF-8, ``\\n``
  line ends and one final newline. A reader accepts any JSON text of the shape.
  Every write rewrites the whole file, so a file last written in another form
  is normalised by the next write; the values of every record, a ``gc_at``
  included, are written back unchanged.
- The file is written in place, without a temporary file: no path of ``runs/``
  is a scratch location (ADR-0004 decision 7). When a write fails, the error
  passes through; a file this call was creating is removed where possible (the
  directories it created stay), and a file that existed stays as the failed
  write left it, possibly partial; so can a process killed while it writes.
  Only what was committed is recovered, from the history of the data
  repository (ADR-0005 decision 10).
- A stored file that is not a regular file (a symbolic link is not followed) or
  not a valid file of version :data:`SCHEMA_VERSION` makes every function that
  reads it raise :class:`CorruptArtifactsError`; nothing is written or repaired.
  Reading another version is not attempted (OD-11).
- :func:`add_record` creates ``runs/<run_id>/`` when it is missing (ADR-0004
  decision 1) and does not know whether the run exists. It asks only whether
  the blob is in the store: the given size is recorded as it is, compared with
  nothing, and the blob is not re-hashed (:func:`hilclaw.cas.verify_blob` does).

What this module does not do: it stores and deletes no blob; it never removes
or moves a record, never changes ``sha256``, ``size``, ``type`` or ``round`` of
one and never writes ``gc_at`` (the MVP has no GC tool); it knows no list of
``type`` values and judges no change of class (OD-20, OD-29, OD-23); it reads
no configuration, runs no ``git`` and commits nothing; and it gives no locking
and no atomicity (OD-17, ADR-0004 decision 10).
"""

import contextlib
import json
import os
import re
import reprlib
import stat
from pathlib import Path
from typing import NamedTuple

from hilclaw import cas, keys, layout

SCHEMA_VERSION = 1
RETENTION_CLASSES = ("best", "final", "intermediate", "failed")

_FILE = "artifacts.json"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_STRING = re.compile(r"[\x20-\x7e]{1,255}")
_MAX = keys.MAX_INTEGER
_INTEGER = (int, range(_MAX + 1).__contains__, f"an int from 0 to {_MAX}")
_CLASS = "one of " + ", ".join(RETENTION_CLASSES)
_CHECKS = {
    "sha256": (str, _SHA256.fullmatch, "a str of 64 lowercase hexadecimal characters"),
    "size": _INTEGER,
    "type": (str, _NAME.fullmatch, f"a str matching {_NAME.pattern}"),
    "round": _INTEGER,
    "retention_class": (str, RETENTION_CLASSES.__contains__, _CLASS),
    "gc_at": (str, _STRING.fullmatch, "a str of 1 to 255 printable ASCII characters"),
}
_REQUIRED = tuple(name for name in _CHECKS if name != "gc_at")


class Added(NamedTuple):
    """Result of :func:`add_record`: the record and whether this call added it."""

    record: dict
    created: bool


class InvalidArtifactsError(ValueError):
    """A document or an argument breaks a rule of ADR-0005; the message names the place."""


class CorruptArtifactsError(Exception):
    """A stored ``artifacts.json`` cannot be used; the message names the path and the reason."""


class ArtifactNotFoundError(LookupError):
    """The file holds no record with the given hash, or the store no blob to record."""


class SizeConflictError(Exception):
    """A hash is recorded with another size than the one given (ADR-0005 decision 6)."""


def validate(document):
    """Check ``document``, a parsed ``artifacts.json``, against ADR-0005 decisions 2, 3 and 6.

    ``document`` must be a ``dict`` with exactly ``schema_version`` (the ``int``
    :data:`SCHEMA_VERSION`) and ``artifacts`` (a ``list`` of ``dict``), every
    record with exactly the members of decision 3 in their types and forms and
    no ``sha256`` twice. A ``gc_at`` is checked to be a string of ADR-0001 and
    nothing more. The order of members and of records is not checked, and
    ``type`` is checked against no vocabulary. Raises
    :class:`InvalidArtifactsError` for the first rule found broken, naming the
    place (for example ``artifacts[2].size``); returns ``None``.
    """
    _records(document)


def load(data_root, run_id):
    """Return the records of the run ``run_id`` as a list of ``dict``, in the order of the file.

    A missing file gives an empty list, as a file with an empty array does
    (ADR-0005 decision 2). Raises :class:`CorruptArtifactsError` when the stored
    file is not a regular file or not UTF-8 JSON that :func:`validate` accepts.
    """
    path = layout.run_file(data_root, run_id, _FILE)
    return _read(_root(data_root), path)


def add_record(data_root, run_id, ref, *, type, round, retention_class):
    """Record the stored blob ``ref`` in the file of the run and return an :class:`Added`.

    ``ref`` is the :class:`hilclaw.cas.BlobRef` of the blob, or an equal tuple
    of digest and size, and the blob must be in the store (ADR-0005 decision
    8). ``type``, ``round`` and ``retention_class`` are the other members of
    the record and have no default (decision 7).

    When the file has no record with this hash, the record is appended at the
    end and the file is written, with the directories above it when they are
    missing. When it has one, nothing is written, ``created`` is false and
    ``record`` is the stored record, also when ``type``, ``round`` or
    ``retention_class`` differ from it (decision 6).

    Raises :class:`InvalidArtifactsError` for an argument that breaks a rule of
    decision 3, :class:`ArtifactNotFoundError` when the blob is not in the store,
    :class:`SizeConflictError` when the hash is recorded with another size and
    :class:`CorruptArtifactsError` for an invalid stored file; nothing is written.
    """
    path = layout.run_file(data_root, run_id, _FILE)
    if not isinstance(ref, tuple) or len(ref) != 2:
        _fail("ref", "a tuple of digest and size", ref)
    digest = _member("sha256", ref[0], "ref.digest")
    record = {
        "sha256": digest,
        "size": _member("size", ref[1], "ref.size"),
        "type": _member("type", type),
        "round": _member("round", round),
        "retention_class": _member("retention_class", retention_class),
    }
    root = _root(data_root)
    if not cas.has_blob(root, digest):
        rule = "a record never precedes its blob (ADR-0005 decision 8)"
        raise ArtifactNotFoundError(f"blob {digest} is not in the store: {rule}")
    records = _read(root, path)
    for stored in records:
        if stored["sha256"] == digest:
            if stored["size"] != record["size"]:
                raise SizeConflictError(
                    f"{_where(root, path)}: sha256 {digest} is recorded with size "
                    f"{stored['size']}, given size {record['size']} (ADR-0005 decision 6)"
                )
            return Added(stored, False)
    _write(path, [*records, record])
    return Added(record, True)


def set_retention_class(data_root, run_id, sha256, retention_class):
    """Replace the retention class of the record ``sha256`` and return the record after the call.

    This is the one edit of ADR-0005 decision 7 this module performs. Any of
    :data:`RETENTION_CLASSES` may replace any other, also on a record that has
    ``gc_at``; no other member changes. When the record already has the given
    class, nothing is written.

    Raises :class:`InvalidArtifactsError` for a malformed ``sha256`` or a class
    outside the four, :class:`ArtifactNotFoundError` when the file has no record
    with this hash, :class:`CorruptArtifactsError` as :func:`load`; nothing is written.
    """
    path = layout.run_file(data_root, run_id, _FILE)
    _member("sha256", sha256)
    _member("retention_class", retention_class)
    root = _root(data_root)
    records = _read(root, path)
    for record in records:
        if record["sha256"] == sha256:
            if record["retention_class"] != retention_class:
                record["retention_class"] = retention_class
                _write(path, records)
            return record
    raise ArtifactNotFoundError(f"{_where(root, path)}: no record with sha256 {sha256}")


def _fail(place, rule, value):
    got = f"{type(value).__name__} {reprlib.repr(value)}"
    raise InvalidArtifactsError(f"{place}: must be {rule}, got {got}")


def _member(name, value, place=None):
    kind, accepts, rule = _CHECKS[name]
    if type(value) is not kind or not accepts(value):
        _fail(place or name, rule, value)
    return value


def _members(place, value, required, optional=()):
    if type(value) is not dict:
        _fail(place, "an object", value)
    for name in value:
        if name not in required and name not in optional:
            unknown = reprlib.repr(name)
            raise InvalidArtifactsError(f"{place}: has the unknown member {unknown}")
    for name in required:
        if name not in value:
            raise InvalidArtifactsError(f"{place}: lacks the member {name}")


def _records(document):
    _members("document", document, ("schema_version", "artifacts"))
    version = document["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail("schema_version", f"the int {SCHEMA_VERSION}", version)
    if type(document["artifacts"]) is not list:
        _fail("artifacts", "an array", document["artifacts"])
    records = []
    seen = {}
    for index, value in enumerate(document["artifacts"]):
        place = f"artifacts[{index}]"
        _members(place, value, _REQUIRED, ("gc_at",))
        names = [name for name in _CHECKS if name in value]
        record = {name: _member(name, value[name], f"{place}.{name}") for name in names}
        first = seen.setdefault(record["sha256"], index)
        if first != index:
            rule = f"repeats the sha256 of artifacts[{first}] (ADR-0005 decision 6)"
            raise InvalidArtifactsError(f"{place}.sha256: {rule}")
        records.append(record)
    return records


def _root(data_root):
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    return root


def _where(root, path):
    return path.relative_to(root).as_posix()


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _read(root, path):
    try:
        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return []
    if not stat.S_ISREG(mode):
        raise CorruptArtifactsError(f"{_where(root, path)}: is not a regular file")
    try:
        text = path.read_bytes().decode("utf-8")
        return _records(json.loads(text, object_pairs_hook=_object))
    except (ValueError, RecursionError) as error:
        rule = "must be UTF-8 JSON of a valid file (ADR-0005 decisions 2 and 3)"
        raise CorruptArtifactsError(f"{_where(root, path)}: {rule}: {error}") from error


def _write(path, records):
    lines = ",\n".join(json.dumps(record) for record in records)
    text = f'{{\n"schema_version": {SCHEMA_VERSION},\n"artifacts": [\n{lines}\n]\n}}\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    creating = not path.exists()
    try:
        with open(path, "wb") as f:
            f.write(text.encode("utf-8"))
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        if creating:
            with contextlib.suppress(OSError):
                path.unlink()
        raise
