"""Validation of a codegen spec, the input of one coder invocation (ADR-0002).

``ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md`` fixes the sections and
fields of version 1 of the spec, their types and the rules across fields
(decisions 2 to 5 and 7, Consequences). :func:`validate` checks an
already-parsed spec against those rules and nothing else. The two embedded
records are validated, and their keys derived, by :mod:`hilclaw.keys`.

*name*, *string* and *integer* are the types of ADR-0001 and are exactly ``str``
and ``int`` as in :mod:`hilclaw.keys`; a *text* is a ``str`` of at least one
character; an object or a map is a ``Mapping`` and an array is a ``list``.

Not checked, because one spec does not show it or the record does not state it
as a rule: that a ref names an earlier call, that ``feedback.base`` is also an
entry of ``feedback.attempts``, that ``failure`` is present exactly when the
attempt failed, that no field carries verification inputs, and that a repair
spec copies the sections of attempt 1. Not inspected: ``task.objective``, the
members of ``profile``, the values of ``ext``, and the vocabularies of
``language``, ``dtype`` and the member names of ``task.build`` and ``ext``.

This module reads and writes no file and builds no spec. The file name and
location of a spec are not part of it (OD-8), and neither is reading a spec of
another schema version (OD-11).
"""

import re
import reprlib
from collections.abc import Mapping
from functools import partial

from hilclaw import keys

SCHEMA_VERSION = 1

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_STRING = re.compile(r"[\x20-\x7e]{1,255}")
_RELATIONS = ("single", "same_technique", "different_techniques")
_ROLES = ("input", "output", "inout")
_STAGES = ("compile", "sim", "board")
_REPAIR_STAGES = ("compile", "sim")
_TOP = ("schema_version", "id", "hw_profile", "task", "guidance", "feedback")
_ID = ("run_id", "round", "candidate", "attempt", "candidates", "relation")
_REF = ("round", "candidate", "attempt")


class InvalidSpecError(ValueError):
    """A spec breaks a rule of ADR-0002; the message names the field path and the rule."""


def validate(spec):
    """Return when ``spec`` is a valid version-1 codegen spec (ADR-0002).

    ``spec`` is the parsed JSON document: a mapping with ``schema_version``
    (the integer :data:`SCHEMA_VERSION`), ``id``, ``hw_profile``, ``task``,
    ``guidance`` and ``feedback``, with ``repair`` exactly when ``id.attempt``
    is greater than 1, and optionally ``ext``. It is not modified.

    Raises :class:`InvalidSpecError` for the first rule found broken. A problem
    inside an embedded key record is reported with its path below
    ``hw_profile.record`` or ``task.op_signature.record``.
    """
    _object("", spec, _TOP, ("repair", "ext"))
    version = spec["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail("schema_version", f"the integer {SCHEMA_VERSION}", version)
    attempt = _id(spec["id"])
    _keyed("hw_profile", spec["hw_profile"], keys.hw_profile_key)
    _task(spec["task"])
    guidance = _object("guidance", spec["guidance"], ("techniques",))
    _array("guidance.techniques", guidance["techniques"], _technique)
    feedback = _object("feedback", spec["feedback"], ("attempts",), ("base",))
    _array("feedback.attempts", feedback["attempts"], _attempt)
    if "base" in feedback:
        _ref("feedback.base", feedback["base"])
    if ("repair" in spec) != (attempt > 1):
        _broken("repair", "must be present exactly when id.attempt is greater than 1")
    if "repair" in spec:
        _repair(spec["repair"], attempt)
    if "ext" in spec:
        _open_map("ext", spec["ext"])


def _broken(path, rule):
    raise InvalidSpecError(f"{path}: {rule}")


def _fail(path, rule, value):
    _broken(path, f"must be {rule}, got {reprlib.repr(value)}")


def _name(path, value):
    if type(value) is not str or not _NAME.fullmatch(value):
        _fail(path, f"a name matching {_NAME.pattern}", value)


def _string(path, value):
    if type(value) is not str or not _STRING.fullmatch(value):
        _fail(path, "a string of 1 to 255 printable ASCII characters", value)


def _text(path, value):
    if type(value) is not str or not value:
        _fail(path, "a text of at least one character", value)


def _integer(path, value, minimum=0):
    if type(value) is not int or not minimum <= value <= keys.MAX_INTEGER:
        _fail(path, f"an integer from {minimum} to 2**53 - 1", value)


def _one_of(path, value, allowed):
    if type(value) is not str or value not in allowed:
        _fail(path, " or ".join(allowed), value)


def _object(path, value, required, optional=()):
    if not isinstance(value, Mapping):
        _fail(path or "spec", "an object", value)
    for name in value:
        if type(name) is not str or name not in required + optional:
            _broken(path or "spec", f"unknown member {reprlib.repr(name)}")
    for name in required:
        if name not in value:
            _broken(f"{path}.{name}" if path else name, "required member is missing")
    return value


def _array(path, value, entry, *, empty=True):
    if not isinstance(value, list):
        _fail(path, "an array", value)
    if not value and not empty:
        _fail(path, "an array of at least one entry", value)
    for index, item in enumerate(value):
        entry(f"{path}[{index}]", item)


def _open_map(path, value, member=None):
    if not isinstance(value, Mapping) or not value:
        _fail(path, "a map with at least one member", value)
    for name, item in value.items():
        _name(f"{path}: member name", name)
        if member is not None:
            member(f"{path}.{name}", item)


def _id(ident):
    _object("id", ident, _ID, ("variant",))
    _string("id.run_id", ident["run_id"])
    _integer("id.round", ident["round"])
    for name in ("candidate", "attempt", "candidates"):
        _integer(f"id.{name}", ident[name], 1)
    relation, candidates = ident["relation"], ident["candidates"]
    _one_of("id.relation", relation, _RELATIONS)
    if (relation == "single") != (candidates == 1):
        _fail("id.relation", "single exactly when id.candidates is 1", relation)
    if ("variant" in ident) != (relation == "same_technique"):
        _broken(
            "id.variant", "must be present exactly when id.relation is same_technique"
        )
    if "variant" in ident:
        _text("id.variant", ident["variant"])
    if ident["candidate"] > candidates:
        _fail(
            "id.candidate", f"at most id.candidates ({candidates})", ident["candidate"]
        )
    return ident["attempt"]


def _keyed(path, value, derive):
    _object(path, value, ("key", "record"))
    _string(f"{path}.key", value["key"])
    try:
        name = derive(value["record"]).name
    except keys.InvalidRecordError as error:
        raise InvalidSpecError(f"{path}.record: {error}") from error
    if value["key"] != name:
        _fail(
            f"{path}.key", f"{name}, the name derived from {path}.record", value["key"]
        )


def _task(task):
    _object("task", task, ("op_signature", "contract", "objective"), ("build",))
    _keyed("task.op_signature", task["op_signature"], keys.op_signature_key)
    sizes = frozenset(task["op_signature"]["record"]["shape"].values())
    contract = _object(
        "task.contract", task["contract"], ("language", "prototype", "operands")
    )
    _name("task.contract.language", contract["language"])
    _text("task.contract.prototype", contract["prototype"])
    operand = partial(_operand, sizes=sizes)
    _array("task.contract.operands", contract["operands"], operand, empty=False)
    if "build" in task:
        _open_map("task.build", task["build"], _build_value)


def _operand(path, operand, *, sizes):
    _object(path, operand, ("name", "role", "dtype", "shape"))
    _string(f"{path}.name", operand["name"])
    _one_of(f"{path}.role", operand["role"], _ROLES)
    _name(f"{path}.dtype", operand["dtype"])
    _array(f"{path}.shape", operand["shape"], partial(_size, sizes=sizes))


def _size(path, value, *, sizes):
    _integer(path, value)
    if value not in sizes:
        _fail(path, "a value of task.op_signature.record.shape", value)


def _build_value(path, value):
    if isinstance(value, list):
        _array(path, value, _string)
    elif type(value) is str:
        _string(path, value)
    elif type(value) is int:
        _integer(path, value)
    else:
        _fail(path, "a string, an integer or an array of strings", value)


def _technique(path, technique):
    _object(path, technique, ("id", "text"))
    _string(f"{path}.id", technique["id"])
    _text(f"{path}.text", technique["text"])


def _ref(path, ref, required=_REF, optional=()):
    _object(path, ref, required, optional)
    _integer(f"{path}.round", ref["round"])
    _integer(f"{path}.candidate", ref["candidate"], 1)
    _integer(f"{path}.attempt", ref["attempt"], 1)


def _attempt(path, attempt):
    _ref(path, attempt, (*_REF, "techniques"), ("failure", "profile"))
    _array(f"{path}.techniques", attempt["techniques"], _string)
    if "failure" in attempt:
        failure = _object(f"{path}.failure", attempt["failure"], ("stage", "report"))
        _one_of(f"{path}.failure.stage", failure["stage"], _STAGES)
        _text(f"{path}.failure.report", failure["report"])
    if "profile" in attempt and not isinstance(attempt["profile"], Mapping):
        _fail(f"{path}.profile", "an object", attempt["profile"])


def _repair(repair, attempt):
    _object("repair", repair, ("failures",))
    failures = repair["failures"]
    _array("repair.failures", failures, _repair_failure, empty=False)
    for index in range(1, len(failures)):
        value = failures[index]["attempt"]
        if value <= failures[index - 1]["attempt"]:
            path = f"repair.failures[{index}].attempt"
            _fail(path, "greater than that of the entry before it", value)
    last = failures[-1]["attempt"]
    if last != attempt - 1:
        path = f"repair.failures[{len(failures) - 1}].attempt"
        _fail(path, f"id.attempt - 1 ({attempt - 1}) in the last entry", last)


def _repair_failure(path, failure):
    _object(path, failure, ("attempt", "stage", "report"))
    _integer(f"{path}.attempt", failure["attempt"], 1)
    _one_of(f"{path}.stage", failure["stage"], _REPAIR_STAGES)
    _text(f"{path}.report", failure["report"])
