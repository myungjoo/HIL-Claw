"""Keys of ``hw_profile`` and ``op_signature`` records, as fixed by ADR-0001.

``ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`` defines the key fields of
both records (decisions 1 and 2), their canonical form, its digest and the
directory name derived from it (decision 3). This module implements those rules
as pure functions over already-parsed values: it validates a record, serialises
its key fields and returns the name of its directory under
``db/<hw_profile_key>/<op_signature>/`` (Requirements FR-13).

The value types of the record are: a *name* matches ``[a-z][a-z0-9_]{0,31}``, a
*string* is 1 to 255 printable ASCII characters, an *integer* is in the range 0
to :data:`MAX_INTEGER`, and the member names of a map are names. Strings and
integers are exactly ``str`` and ``int``: a subclass (``bool``, an ``enum``
member) is rejected, because it may print differently from the value it holds.

This module reads and writes no file and builds no path: it returns names and
the caller joins them. Where a record is stored, the collision check against a
stored canonical form and the lookup are not part of it (OD-8), and neither is
reading a record of another schema version (OD-11).
"""

import hashlib
import json
import re
from collections.abc import Mapping
from typing import NamedTuple

SCHEMA_VERSION = 1
MAX_INTEGER = 2**53 - 1
NAME_DIGEST_LENGTH = 16
HW_SOURCES = ("external", "in_house")

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_STRING = re.compile(r"[\x20-\x7e]{1,255}")
_SHAPE_MEMBERS = {"gemm": frozenset({"m", "k", "n"})}
_HW_REQUIRED = (
    "schema_version",
    "accelerator",
    "revision",
    "toolchain",
    "host",
    "hw_source",
)
_OP_REQUIRED = ("schema_version", "kind", "shape", "dtype", "layout")
_OPTIONAL = ("ext", "label")


class Key(NamedTuple):
    """A derived key: the directory name, the SHA-256 hex digest and the canonical form."""

    name: str
    digest: str
    canonical: bytes


class InvalidRecordError(ValueError):
    """A record or a value breaks a rule of ADR-0001; the message names the field and the rule."""


def canonical_form(key_fields):
    """Return the canonical form (ADR-0001 decision 3, step 1) of ``key_fields`` as UTF-8 bytes.

    ``key_fields`` is a mapping that already holds exactly the key fields of a
    record. The result is its JSON text with the members sorted by name at every
    level, no whitespace, integers in plain decimal and strings escaped only for
    ``"`` and ``\\``.

    Only the value set is checked, not which fields exist: every member name is
    a name and every value is a string, an integer or a mapping of the same
    kind, which may be empty (the record functions reject an empty ``ext``).
    Raises :class:`InvalidRecordError` otherwise, for example for a float,
    ``None``, a list, a member name that is not a ``str``, or maps nested too
    deeply for the interpreter (which includes a map that contains itself).
    """
    try:
        plain = _map("", key_fields, _value)
        text = json.dumps(plain, sort_keys=True, separators=(",", ":"))
    except RecursionError:
        raise InvalidRecordError("record: maps are nested too deeply") from None
    return text.encode("ascii")


def directory_name(prefix, canonical):
    """Return the :class:`Key` of the canonical form ``canonical`` (decision 3, steps 2 and 3).

    The digest is the SHA-256 of ``canonical`` and the name is ``prefix``, a
    hyphen and the first :data:`NAME_DIGEST_LENGTH` characters of the digest.
    Raises :class:`InvalidRecordError` when ``prefix`` is not a name and
    :class:`TypeError` when ``canonical`` is not ``bytes``.
    """
    _name("prefix", prefix)
    if not isinstance(canonical, bytes):
        raise TypeError(f"canonical must be bytes, not {type(canonical).__name__}")
    digest = hashlib.sha256(canonical).hexdigest()
    return Key(f"{prefix}-{digest[:NAME_DIGEST_LENGTH]}", digest, canonical)


def hw_profile_key(record):
    """Validate the hw_profile ``record`` (decision 1) and return its :class:`Key`.

    ``record`` is a mapping with the key fields ``schema_version`` (the integer
    :data:`SCHEMA_VERSION`), ``accelerator`` (name), ``revision`` (string),
    ``toolchain`` (map of name to string, at least one member), ``host`` (map of
    name to string or integer, with ``cpu`` and ``os``) and optionally ``ext``
    (non-empty map of name to string or integer), and with the attributes
    ``hw_source`` (one of :data:`HW_SOURCES`, required) and ``label`` (string,
    optional). The attributes are checked and then left out of the key, whose
    name starts with ``accelerator``. ``record`` is not modified.

    Raises :class:`InvalidRecordError` for the first rule found broken, which
    includes a field that is neither a key field nor an attribute.
    """
    _fields(record, _HW_REQUIRED)
    key = {
        "schema_version": _version(record["schema_version"]),
        "accelerator": _name("accelerator", record["accelerator"]),
        "revision": _string("revision", record["revision"]),
        "toolchain": _map("toolchain", record["toolchain"], _string, empty=False),
        "host": _map("host", record["host"], _scalar),
    }
    for member in ("cpu", "os"):
        if member not in key["host"]:
            raise InvalidRecordError(f"host.{member}: required member is missing")
    _optional(record, key)
    source = record["hw_source"]
    if type(source) is not str or source not in HW_SOURCES:
        _fail("hw_source", " or ".join(HW_SOURCES), source)
    return directory_name(key["accelerator"], canonical_form(key))


def op_signature_key(record):
    """Validate the op_signature ``record`` (decision 2) and return its :class:`Key`.

    ``record`` is a mapping with the key fields ``schema_version`` (the integer
    :data:`SCHEMA_VERSION`), ``kind``, ``dtype`` and ``layout`` (names),
    ``shape`` (map of name to integer whose member names are fixed by the kind:
    ``m``, ``k`` and ``n`` for ``gemm``) and optionally ``ext`` (non-empty map of
    name to string or integer), and with the optional attribute ``label``
    (string), which is checked and then left out of the key. The name of the key
    starts with ``kind``. ``record`` is not modified.

    Raises :class:`InvalidRecordError` for the first rule found broken, which
    includes an unknown field and a ``kind`` whose shape members this module
    does not know (only ``gemm`` is known).
    """
    _fields(record, _OP_REQUIRED)
    key = {
        "schema_version": _version(record["schema_version"]),
        "kind": _name("kind", record["kind"]),
        "shape": _map("shape", record["shape"], _integer),
        "dtype": _name("dtype", record["dtype"]),
        "layout": _name("layout", record["layout"]),
    }
    members = _SHAPE_MEMBERS.get(key["kind"])
    if members is None:
        _fail("kind", "a known kind: " + ", ".join(sorted(_SHAPE_MEMBERS)), key["kind"])
    if set(key["shape"]) != members:
        rule = f"a map with exactly the members {', '.join(sorted(members))}"
        _fail("shape", rule, record["shape"])
    _optional(record, key)
    return directory_name(key["kind"], canonical_form(key))


def _fail(path, rule, value):
    raise InvalidRecordError(f"{path or 'record'}: must be {rule}, got {value!r}")


def _name(path, value):
    if type(value) is not str or not _NAME.fullmatch(value):
        _fail(path, f"a name matching {_NAME.pattern}", value)
    return value


def _string(path, value):
    if type(value) is not str or not _STRING.fullmatch(value):
        _fail(path, "a string of 1 to 255 printable ASCII characters", value)
    return value


def _integer(path, value):
    if type(value) is not int or not 0 <= value <= MAX_INTEGER:
        _fail(path, "an integer from 0 to 2**53 - 1", value)
    return value


def _scalar(path, value):
    if type(value) is str:
        return _string(path, value)
    if type(value) is int:
        return _integer(path, value)
    _fail(path, "a string or an integer", value)


def _value(path, value):
    if isinstance(value, Mapping):
        return _map(path, value, _value)
    if type(value) is str:
        return _string(path, value)
    if type(value) is int:
        return _integer(path, value)
    _fail(path, "a string, an integer or a map", value)


def _map(path, value, member, *, empty=True):
    if not isinstance(value, Mapping):
        _fail(path, "a map", value)
    if not value and not empty:
        _fail(path, "a map with at least one member", value)
    plain = {}
    for name, item in value.items():
        _name(f"{path or 'record'}: member name", name)
        plain[name] = member(f"{path}.{name}" if path else name, item)
    return plain


def _fields(record, required):
    if not isinstance(record, Mapping):
        _fail("", "a map", record)
    for name in record:
        if name not in required and name not in _OPTIONAL:
            raise InvalidRecordError(f"{name!r}: unknown field")
    for name in required:
        if name not in record:
            raise InvalidRecordError(f"{name}: required field is missing")


def _version(value):
    if type(value) is not int or value != SCHEMA_VERSION:
        _fail("schema_version", f"the integer {SCHEMA_VERSION}", value)
    return value


def _optional(record, key):
    if "ext" in record:
        key["ext"] = _map("ext", record["ext"], _scalar, empty=False)
    if "label" in record:
        _string("label", record["label"])
