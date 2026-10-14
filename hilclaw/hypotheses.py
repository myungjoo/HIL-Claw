"""Validation of the hypothesis record of a round (ADR-0059).

``ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`` fixes the
file ``runs/<run_id>/rounds/<RRRR>/decision/hypotheses.json`` (decision 1),
which :func:`hilclaw.layout.hypothesis_record` builds, and the rules of its
version 1: the file as a whole (decision 2), one hypothesis (decision 3), how
the hypotheses map to the candidates of the round (decision 4) and round 0
(decision 5). :func:`validate` checks an already-parsed document against the
rules of those decisions that one document shows, and nothing else.

The top level is open (ADR-0059 decision 2, read with ADR-0018 decision 2): a
member that ADR-0059 does not define is passed over, neither interpreted nor
checked. Every object below it holds exactly its listed members. The values
that ADR-0059 defines and does not admit, the basis kind ``case`` and the
origin ``injected``, are refused as any other value, and so is every metric
other than ``latency_minimisation``, the constraint type ``memory_ceiling`` of
ADR-0050 among them (ADR-0059 decision 3).

*name*, *string* and *integer* are the types of ADR-0001 and are exactly ``str``
and ``int`` as in :mod:`hilclaw.keys`; a *text* is a ``str`` of at least one
character and a *ref* is that of ADR-0002, as in :mod:`hilclaw.spec`; an
object is a ``Mapping`` and an array is a ``list``.

Not checked, because one document does not show it: that ``run_id`` and
``round`` agree with the path the file is found under (ADR-0059 decision 2),
that ``candidates`` equals the ``id.candidates`` of the round's specs
(decision 4), that a ``ref`` names an attempt that exists, and that the
``metric`` of an expected effect is an objective of the run's
``instance.json``. The recommendation on causal misattribution (decision 4) is
a recommendation and is not enforced.

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
_HYPOTHESIS = ("id", "statement", "basis", "expected", "origin", "tested_by")
_BASIS = {
    "attempt": ("kind", "ref", "text"),
    "external": ("kind", "source", "version", "text"),
}
_REF = ("round", "candidate", "attempt")
_METRICS = ("latency_minimisation",)
_DIRECTIONS = ("lower", "higher")
_ORIGINS = ("system",)


class InvalidHypothesisRecordError(ValueError):
    """A hypothesis record breaks a rule of ADR-0059; the message names the field path and the rule."""


def validate(document):
    """Return when ``document`` is a valid version-1 hypothesis record (ADR-0059).

    ``document`` is the parsed JSON document: a mapping with
    ``schema_version`` (the integer :data:`SCHEMA_VERSION`), ``run_id`` (a
    string), ``round`` (an integer of at least 1), ``candidates`` (an integer
    of at least 1) and ``hypotheses`` (an array of at least one hypothesis);
    any other top-level member is passed over. Each hypothesis has exactly
    ``id``, ``statement``, ``basis``, ``expected``, ``origin`` and
    ``tested_by``; its ``id`` is unique in the document. Every value of a
    ``tested_by`` is at most ``candidates``, and every integer from 1 to
    ``candidates`` is in the ``tested_by`` of at least one hypothesis.
    ``document`` is not modified.

    Raises :class:`InvalidHypothesisRecordError` for the first rule found
    broken. A ``schema_version`` of any other value, another integer among
    them, is refused as any other wrong value.
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
    round, candidates = document["round"], document["candidates"]
    hypothesis = partial(_hypothesis, round=round, candidates=candidates)
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


def _hypothesis(path, entry, *, round, candidates):
    _object(path, entry, _HYPOTHESIS)
    _name(f"{path}.id", entry["id"])
    _text(f"{path}.statement", entry["statement"])
    _array(f"{path}.basis", entry["basis"], partial(_basis, round=round))
    _array(f"{path}.expected", entry["expected"], _expected)
    _unique(
        f"{path}.expected", [item["metric"] for item in entry["expected"]], "metric"
    )
    _one_of(f"{path}.origin", entry["origin"], _ORIGINS)
    tested_by = entry["tested_by"]
    _array(f"{path}.tested_by", tested_by, partial(_candidate, candidates=candidates))
    _unique(f"{path}.tested_by", tested_by)


def _basis(path, entry, *, round):
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
    ref = entry["ref"]
    _object(f"{path}.ref", ref, _REF)
    _integer(f"{path}.ref.round", ref["round"])
    _integer(f"{path}.ref.candidate", ref["candidate"], 1)
    _integer(f"{path}.ref.attempt", ref["attempt"], 1)
    if ref["round"] >= round:
        _fail(f"{path}.ref.round", f"lower than round ({round})", ref["round"])


def _expected(path, entry):
    _object(path, entry, ("metric", "direction"))
    _one_of(f"{path}.metric", entry["metric"], _METRICS)
    _one_of(f"{path}.direction", entry["direction"], _DIRECTIONS)


def _candidate(path, value, *, candidates):
    _integer(path, value, 1)
    if value > candidates:
        _fail(path, f"at most candidates ({candidates})", value)
