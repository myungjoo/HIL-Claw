"""Store of the two key record files of the knowledge tree ``db/`` (ADR-0001, ADR-0004).

``ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`` decision 5 places
the full hw_profile record at ``db/<hw_profile_key>/hw_profile.json`` and the
full op_signature record at
``db/<hw_profile_key>/<op_signature>/op_signature.json``. This module writes
and reads these two files and implements two rules of
``ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md``: the collision check of
decision 3 (a stored canonical form that differs from the caller's is an error
and nothing is written) and the exact-match lookup of decision 4. Records are
validated and named by :mod:`hilclaw.keys` and every path comes from
:mod:`hilclaw.layout`.

``data_root`` is always given by the caller and must be an existing directory
(:class:`FileNotFoundError` or :class:`NotADirectoryError` otherwise). Errors
of :mod:`hilclaw.keys` and :mod:`hilclaw.layout` for the caller's arguments
pass through unchanged, and so does an :class:`OSError` of the file system.

Conventions of this module, which the two ADRs do not fix:

- A key is stored if and only if its record file exists as a regular file. A
  key directory without its record file counts as not stored.
- A stored record file is never modified, replaced or deleted. A store call
  for a key that is already stored writes nothing, also when the attributes
  (``hw_source``, ``label``) of the given record differ from the stored ones:
  whether a stored attribute may be updated is not decided (OD-26). The load
  functions show what is stored.
- A stored file that is not a valid record of schema version
  :data:`hilclaw.keys.SCHEMA_VERSION` is reported as
  :class:`CorruptKeyRecordError`. Reading a record of another schema version is
  not attempted (OD-11).
- A stored record that is valid but does not belong to its directory is
  reported as :class:`KeyCollisionError` by every function.
- A file is written as UTF-8 JSON with the members sorted by name, an
  indentation of two spaces, ``\\n`` line ends and one final newline, and holds
  exactly the members of the given record. No reader may depend on this text
  form: the functions here accept any JSON text of a valid record.
- A file comes to be by the steps of ADR-0014 decision 3: the content is
  written into a new file ``<final name>.<token>.tmp`` in the key directory
  (``<token>`` is the process id, a hyphen and 16 random hexadecimal
  characters), flushed, and given the final name by a hard link, a step that
  fails when the name exists and replaces nothing; the temporary name is then
  removed. There is no fallback to a replacing rename: where the link is not
  possible the store fails. A record that took the name in between is treated
  as one found before the write.
- When writing fails, the temporary file and the directories the call created
  are removed where possible. A file of that name form which another write
  left is never read, listed, removed or given the final name, and makes no
  key stored. The death of the writing process leaves no record file or the
  whole one on the POSIX systems of C-7 whose file system gives hard links;
  nothing is stated for a network file system or for native Windows (ADR-0014
  decision 6).
- Only the record file itself must be a regular file; a symbolic link in its
  place is not followed. The directories above it are used as they are.

What this module does not do: it reads no configuration, runs no ``git`` and
commits nothing; it neither reads nor writes ``best.json``,
``technique_stats.json`` or any other file of the tree; it lists no directory,
registers no key on its own and matches nothing but equal canonical forms (the
rest of OD-4); it takes no lock: of two writers of one key the first record
stays and the other writes nothing (OD-17, ADR-0014 decision 6); and it gives
no atomicity between the two record files or with a commit (ADR-0004 decision
10).
"""

import contextlib
import json
import os
import secrets
import stat
from collections.abc import Mapping
from pathlib import Path
from typing import NamedTuple

from hilclaw import keys, layout

_OP_RECORD = "op_signature.json"


class Stored(NamedTuple):
    """Result of a store call: the key of the record and whether this call created its file."""

    key: keys.Key
    created: bool


class KeyRecordNotFoundError(LookupError):
    """No record file is stored for the requested key; the message names the path."""


class KeyCollisionError(Exception):
    """A stored canonical form differs from the one its directory stands for (ADR-0001 decision 3)."""


class CorruptKeyRecordError(Exception):
    """A stored record file is not a valid record; the message names the path and the reason."""


def store_hw_profile(data_root, record):
    """Store the hw_profile ``record`` and return a :class:`Stored`.

    ``record`` is validated by :func:`hilclaw.keys.hw_profile_key` and is not
    modified. When ``db/<hw_profile_key>/hw_profile.json`` does not exist it is
    created, with the directories above it, and ``created`` is true. When it
    exists and holds the same canonical form, nothing is written and
    ``created`` is false; the stored attributes are kept as they are.

    Raises :class:`KeyCollisionError` when the stored canonical form differs
    and :class:`CorruptKeyRecordError` when the stored file is not a valid
    record; no record file is written in either case.
    """
    key = keys.hw_profile_key(record)
    path = layout.hw_profile_record(data_root, key.name)
    return _store(_root(data_root), path, keys.hw_profile_key, key, record)


def store_op_signature(data_root, hw_profile_key, record):
    """Store the op_signature ``record`` below the stored hw_profile ``hw_profile_key``.

    ``hw_profile_key`` is the directory name of the hw_profile
    (:attr:`hilclaw.keys.Key.name`), and its record must be stored: no key
    directory is created below a hw_profile without a record. ``record`` is
    validated by :func:`hilclaw.keys.op_signature_key`; the file is
    ``db/<hw_profile_key>/<op_signature>/op_signature.json`` and the result is
    as for :func:`store_hw_profile`.

    Raises :class:`KeyRecordNotFoundError` when the hw_profile is not stored,
    and :class:`KeyCollisionError` or :class:`CorruptKeyRecordError` for the
    stored record of either key; no record file is written in these cases.
    """
    key = keys.op_signature_key(record)
    hw_path = layout.hw_profile_record(data_root, hw_profile_key)
    path = layout.op_signature_file(data_root, hw_profile_key, key.name, _OP_RECORD)
    root = _root(data_root)
    _load(root, hw_path, keys.hw_profile_key)
    return _store(root, path, keys.op_signature_key, key, record)


def load_hw_profile(data_root, hw_profile_key):
    """Return the hw_profile record stored for the directory name ``hw_profile_key``.

    The result is the full record (key fields and attributes) as plain
    ``dict``, ``str`` and ``int`` values. Raises
    :class:`KeyRecordNotFoundError` when it is not stored,
    :class:`CorruptKeyRecordError` when the file is not a valid record and
    :class:`KeyCollisionError` when the record derives another name than that
    of its directory.
    """
    path = layout.hw_profile_record(data_root, hw_profile_key)
    return _load(_root(data_root), path, keys.hw_profile_key)


def load_op_signature(data_root, hw_profile_key, op_signature):
    """Return the op_signature record stored at ``db/<hw_profile_key>/<op_signature>/``.

    Both arguments are directory names. Only the op_signature record file is
    read; the result and the errors are as for :func:`load_hw_profile`.
    """
    path = layout.op_signature_file(data_root, hw_profile_key, op_signature, _OP_RECORD)
    return _load(_root(data_root), path, keys.op_signature_key)


def lookup(data_root, hw_record, op_record):
    """Look the pair (``hw_record``, ``op_record``) up by exact match (ADR-0001 decision 4).

    Both records are validated. Returns the tuple of their two
    :class:`hilclaw.keys.Key` values (hw_profile, op_signature) when both
    record files exist and the canonical forms derived from the stored records
    are byte-equal to those of the given records, and ``None`` when either
    record file does not exist. Attributes take no part in the match.

    Only the two record files are read. A hit says that knowledge of the pair
    may be stored, as a hint and never as ground truth (Requirements FR-15);
    this module neither reads nor interprets it.

    Raises :class:`KeyCollisionError` when a stored canonical form differs and
    :class:`CorruptKeyRecordError` when a stored file is not a valid record.
    """
    hw = keys.hw_profile_key(hw_record)
    op = keys.op_signature_key(op_record)
    root = _root(data_root)
    hw_path = layout.hw_profile_record(root, hw.name)
    op_path = layout.op_signature_file(root, hw.name, op.name, _OP_RECORD)
    if _read(root, hw_path, keys.hw_profile_key, hw) is None:
        return None
    if _read(root, op_path, keys.op_signature_key, op) is None:
        return None
    return hw, op


def _root(data_root):
    root = Path(data_root)
    if not root.is_dir():
        error = NotADirectoryError if root.exists() else FileNotFoundError
        raise error(f"data root is not an existing directory: {root}")
    return root


def _object(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a JSON object repeats a member name")
    return members


def _read(root, path, derive, wanted=None):
    where = path.relative_to(root).as_posix()
    try:
        mode = os.lstat(path).st_mode
    except (FileNotFoundError, NotADirectoryError):
        return None
    if not stat.S_ISREG(mode):
        raise CorruptKeyRecordError(f"{where}: is not a regular file")
    try:
        text = path.read_bytes().decode("utf-8")
        record = json.loads(text, object_pairs_hook=_object)
        key = derive(record)
    except (ValueError, RecursionError) as error:
        rule = "must be UTF-8 JSON of a valid record (ADR-0001 decisions 1 and 2)"
        raise CorruptKeyRecordError(f"{where}: {rule}: {error}") from error
    rule = "(ADR-0001 decision 3)"
    if wanted is not None and key.canonical != wanted.canonical:
        raise KeyCollisionError(
            f"{where}: the stored canonical form differs from the given one {rule}: "
            f"stored sha256 {key.digest}, given sha256 {wanted.digest}"
        )
    if key.name != path.parent.name:
        raise KeyCollisionError(
            f"{where}: the stored record derives the name {key.name}, "
            f"not the name of its directory {rule}"
        )
    return record


def _load(root, path, derive):
    record = _read(root, path, derive)
    if record is None:
        where = path.relative_to(root).as_posix()
        raise KeyRecordNotFoundError(f"{where}: no key record is stored")
    return record


def _plain(value):
    if isinstance(value, Mapping):
        return {name: _plain(item) for name, item in value.items()}
    return value


def _store(root, path, derive, key, record):
    if _read(root, path, derive, key) is not None:
        return Stored(key, False)
    text = json.dumps(_plain(record), sort_keys=True, indent=2) + "\n"
    content = text.encode("utf-8")
    missing = []
    directory = path.parent
    while not directory.is_dir():
        missing.append(directory)
        directory = directory.parent
    token = f"{os.getpid()}-{secrets.token_hex(8)}"
    temporary = path.with_name(f"{path.name}.{token}.tmp")
    made = []
    created = False
    linked = True
    try:
        for directory in reversed(missing):
            directory.mkdir()
            made.append(directory)
        with open(temporary, "xb") as f:
            created = True
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if _read(root, path, derive, key) is None:
                raise
            linked = False
    except BaseException:
        if created:
            with contextlib.suppress(OSError):
                os.unlink(temporary)
        for directory in reversed(made):
            with contextlib.suppress(OSError):
                directory.rmdir()
        raise
    with contextlib.suppress(OSError):
        os.unlink(temporary)
    return Stored(key, linked)
