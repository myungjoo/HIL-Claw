"""Validation of the hypothesis record of a round (ADR-0059).

``ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`` fixes the
file ``runs/<run_id>/rounds/<RRRR>/decision/hypotheses.json`` (decision 1),
which :func:`hilclaw.layout.hypothesis_record` builds, and the rules of its
version 1: the file as a whole (decision 2), one hypothesis (decision 3), how
the hypotheses map to the candidates of the round (decision 4) and round 0
(decision 5).
``ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`` admits
the basis kind ``case`` (decision 2) and defines the optional top-level member
``cases_read`` (decision 3), neither of which raises the version.
:func:`validate` checks an already-parsed document against the rules of those
decisions that one document shows, and nothing else.

The top level is open (ADR-0059 decision 2, read with ADR-0018 decision 2): a
member that neither ADR-0059 nor ADR-0073 defines is passed over, neither
interpreted nor checked. Every object below it holds exactly its listed
members. ``cases_read``, when present, is an array, possibly empty, of objects
with ``run_id`` and ``round``, with no pair twice and none whose ``run_id`` is
the record's; its order is not checked, and when it is absent nothing of it is
checked. A basis entry of kind ``case`` names a stored hypothesis by
``case.run_id``, ``case.round`` and ``case.hypothesis``; its ``run_id`` is not
the record's and its pair is an entry of ``cases_read``, so a record without
``cases_read`` holds no such entry (ADR-0073 decisions 2 and 3, in-file
rules). The value that ADR-0059 defines and does not admit, the origin
``injected``, is refused as any other value, and so is every metric other than
``latency_minimisation``, the constraint type ``memory_ceiling`` of ADR-0050
among them (ADR-0059 decision 3).

*name*, *string* and *integer* are the types of ADR-0001 and are exactly ``str``
and ``int`` as in :mod:`hilclaw.keys`; a *text* is a ``str`` of at least one
character and a *ref* is that of ADR-0002, as in :mod:`hilclaw.spec`; an
object is a ``Mapping`` and an array is a ``list``.

Not checked, because one document does not show it: that ``run_id`` and
``round`` agree with the path the file is found under (ADR-0059 decision 2),
that ``candidates`` equals the ``id.candidates`` of the round's specs
(decision 4), that a ``ref`` names an attempt that exists, and that the
``metric`` of an expected effect is an objective of the run's
``instance.json``; nor the rules between files of ADR-0073 decisions 2 and 3:
that a ``case`` entry names a valid case in the key directory of the run's
instance whose ``hypothesis_record`` holds ``case.hypothesis``, and that
``cases_read`` names valid cases there and is what a lookup gave. The
recommendation on causal misattribution (decision 4) is a recommendation and
is not enforced.

This module reads and writes no file. The text form of the file, the setting
apart of another ``schema_version`` (OD-11), the final name derived from the
content and the write of the file (ADR-0059 decisions 1 and 2, by ADR-0029)
are not part of it.
"""

import re
import reprlib
from collections.abc import Mapping
from functools import partial

from hilclaw import keys

SCHEMA_VERSION = 1

_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")
_STRING = re.compile(r"[\x20-\x7e]{1,255}")
_TOP = ("schema_version", "run_id", "round", "candidates", "hypotheses")
_CASE_READ = ("run_id", "round")
_HYPOTHESIS = ("id", "statement", "basis", "expected", "origin", "tested_by")
_BASIS = {
    "attempt": ("kind", "ref", "text"),
    "external": ("kind", "source", "version", "text"),
    "case": ("kind", "case", "text"),
}
_CASE = ("run_id", "round", "hypothesis")
_REF = ("round", "candidate", "attempt")
_METRICS = ("latency_minimisation",)
_DIRECTIONS = ("lower", "higher")
_ORIGINS = ("system",)


class InvalidHypothesisRecordError(ValueError):
    """A hypothesis record breaks a rule of ADR-0059 or ADR-0073; the message names the field path and the rule."""


def validate(document):
    """Return when ``document`` is a valid version-1 hypothesis record (ADR-0059, ADR-0073).

    ``document`` is the parsed JSON document: a mapping with
    ``schema_version`` (the integer :data:`SCHEMA_VERSION`), ``run_id`` (a
    string), ``round`` (an integer of at least 1), ``candidates`` (an integer
    of at least 1), ``hypotheses`` (an array of at least one hypothesis) and
    optionally ``cases_read`` (an array of objects with exactly ``run_id``, a
    string other than the record's, and ``round``, an integer of at least 1,
    with no pair twice); any other top-level member is passed over. Each
    hypothesis has exactly ``id``, ``statement``, ``basis``, ``expected``,
    ``origin`` and ``tested_by``; its ``id`` is unique in the document. The
    ``case.run_id`` and ``case.round`` of a basis entry of kind ``case`` are
    a pair of ``cases_read``, and that ``run_id`` is not the record's. Every
    value of a ``tested_by`` is at most ``candidates``, and every integer from
    1 to ``candidates`` is in the ``tested_by`` of at least one hypothesis.
    ``document`` is not modified.

    Raises :class:`InvalidHypothesisRecordError` for the first rule found
    broken: the top-level members first, then ``cases_read``, then
    ``hypotheses``. A ``schema_version`` of any other value, another integer
    among them, is refused as any other wrong value.
    """
    if not isinstance(document, Mapping):
        _fail("record", "an object", document)
    for name in _TOP:
        if name not in document:
            _broken(name, "required member is missing")
    version = document["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail("schema_version", f"the integer {SCHEMA_VERSION}", version)
    _string("run_id", document["run_id"])
    _integer("round", document["round"], 1)
    _integer("candidates", document["candidates"], 1)
    run_id, round = document["run_id"], document["round"]
    candidates = document["candidates"]
    read = frozenset()
    if "cases_read" in document:
        read = _cases_read(document["cases_read"], run_id)
    hypothesis = partial(
        _hypothesis, run_id=run_id, round=round, candidates=candidates, read=read
    )
    hypotheses = document["hypotheses"]
    _array("hypotheses", hypotheses, hypothesis)
    _unique("hypotheses", [entry["id"] for entry in hypotheses], "id")
    tested = {value for entry in hypotheses for value in entry["tested_by"]}
    for candidate in range(1, candidates + 1):
        if candidate not in tested:
            _broken(
                "hypotheses",
                f"candidate {candidate} is in the tested_by of no entry",
            )


def _broken(path, rule):
    raise InvalidHypothesisRecordError(f"{path}: {rule}")


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


def _object(path, value, members):
    if not isinstance(value, Mapping):
        _fail(path, "an object", value)
    for name in value:
        if type(name) is not str or name not in members:
            _broken(path, f"unknown member {reprlib.repr(name)}")
    for name in members:
        if name not in value:
            _broken(f"{path}.{name}", "required member is missing")


def _array(path, value, entry):
    if not isinstance(value, list):
        _fail(path, "an array", value)
    if not value:
        _fail(path, "an array of at least one entry", value)
    for index, item in enumerate(value):
        entry(f"{path}[{index}]", item)


def _unique(path, values, member=None):
    seen = set()
    for index, value in enumerate(values):
        if value in seen:
            where = f"{path}[{index}]" + (f".{member}" if member else "")
            _fail(where, "unique in the array", value)
        seen.add(value)


def _cases_read(value, run_id):
    if not isinstance(value, list):
        _fail("cases_read", "an array", value)
    for index, entry in enumerate(value):
        path = f"cases_read[{index}]"
        _object(path, entry, _CASE_READ)
        _string(f"{path}.run_id", entry["run_id"])
        _integer(f"{path}.round", entry["round"], 1)
        _other_run(f"{path}.run_id", entry["run_id"], run_id)
    pairs = [(entry["run_id"], entry["round"]) for entry in value]
    _unique("cases_read", pairs)
    return frozenset(pairs)


def _other_run(path, value, run_id):
    if value == run_id:
        _fail(path, f"other than run_id ({run_id})", value)


def _hypothesis(path, entry, *, run_id, round, candidates, read):
    _object(path, entry, _HYPOTHESIS)
    _name(f"{path}.id", entry["id"])
    _text(f"{path}.statement", entry["statement"])
    basis = partial(_basis, run_id=run_id, round=round, read=read)
    _array(f"{path}.basis", entry["basis"], basis)
    _array(f"{path}.expected", entry["expected"], _expected)
    _unique(
        f"{path}.expected", [item["metric"] for item in entry["expected"]], "metric"
    )
    _one_of(f"{path}.origin", entry["origin"], _ORIGINS)
    tested_by = entry["tested_by"]
    _array(f"{path}.tested_by", tested_by, partial(_candidate, candidates=candidates))
    _unique(f"{path}.tested_by", tested_by)


def _basis(path, entry, *, run_id, round, read):
    if not isinstance(entry, Mapping):
        _fail(path, "an object", entry)
    if "kind" not in entry:
        _broken(f"{path}.kind", "required member is missing")
    kind = entry["kind"]
    _one_of(f"{path}.kind", kind, tuple(_BASIS))
    _object(path, entry, _BASIS[kind])
    _text(f"{path}.text", entry["text"])
    if kind == "external":
        _string(f"{path}.source", entry["source"])
        _string(f"{path}.version", entry["version"])
        return
    if kind == "case":
        _case(f"{path}.case", entry["case"], run_id, read)
        return
    ref = entry["ref"]
    _object(f"{path}.ref", ref, _REF)
    _integer(f"{path}.ref.round", ref["round"])
    _integer(f"{path}.ref.candidate", ref["candidate"], 1)
    _integer(f"{path}.ref.attempt", ref["attempt"], 1)
    if ref["round"] >= round:
        _fail(f"{path}.ref.round", f"lower than round ({round})", ref["round"])


def _case(path, case, run_id, read):
    _object(path, case, _CASE)
    _string(f"{path}.run_id", case["run_id"])
    _integer(f"{path}.round", case["round"], 1)
    _name(f"{path}.hypothesis", case["hypothesis"])
    _other_run(f"{path}.run_id", case["run_id"], run_id)
    if (case["run_id"], case["round"]) not in read:
        _broken(path, "its run_id and round are no entry of cases_read")


def _expected(path, entry):
    _object(path, entry, ("metric", "direction"))
    _one_of(f"{path}.metric", entry["metric"], _METRICS)
    _one_of(f"{path}.direction", entry["direction"], _DIRECTIONS)


def _candidate(path, value, *, candidates):
    _integer(path, value, 1)
    if value > candidates:
        _fail(path, f"at most candidates ({candidates})", value)
