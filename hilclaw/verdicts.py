"""Validation of the verdicts of the hypotheses of a round (ADR-0071).

``ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`` fixes the
file ``runs/<run_id>/rounds/<RRRR>/eval/verdicts.json`` (decision 1), which
:func:`hilclaw.layout.verdict_record` builds, and the rules of its version 1:
the file as a whole (decision 2), one verdict and its evidence (decision 3),
the rule of each value (decision 4) and round 0 (decision 6).
:func:`validate` checks an already-parsed document against the rules of those
decisions that one document shows (decision 4, "What the file itself makes
checkable"), and nothing else.

The top level is open (ADR-0071 decision 2, read with ADR-0059 decision 2): a
member that ADR-0071 does not define is passed over, neither interpreted nor
checked. Every object below it holds exactly its listed members; an evidence
entry holds exactly those of its ``kind``. Every metric other than
``latency_minimisation`` is refused, the constraint type ``memory_ceiling`` of
ADR-0050 among them (ADR-0071 decision 3). A ``supported`` or ``refuted``
verdict must hold at least one counted comparison: a ``comparison`` at
``board`` for whose ``measured`` and ``against`` the same verdict holds a
``check`` at ``board`` with ``outcome`` ``pass`` (decision 4).

*name*, *string* and *integer* are the types of ADR-0001 and are exactly ``str``
and ``int`` as in :mod:`hilclaw.keys`; a *text* is a ``str`` of at least one
character and a *ref* is that of ADR-0002, as in :mod:`hilclaw.spec`; an
object is a ``Mapping`` and an array is a ``list``.

Not checked, because one document does not show it: that ``run_id`` and
``round`` agree with the path the file is found under (decision 2); that the
verdicts correspond one to one to the ``id`` of the hypotheses of the round's
``hypotheses.json`` (decision 1); that a ``verdict`` follows the rule of
decision 4 against the hypothesis's ``expected`` entries and that
``measured.candidate`` is in its ``tested_by`` (decisions 3 and 4, rules
between two files); and that a ``ref`` names an attempt that exists. Which
attempt ``against`` must be, the base of the comparison, is left open by
decision 4 and is not checked. The recommendation on shared candidates
(decision 5) is a recommendation and is not enforced.

This module reads and writes no file. The text form of the file, the setting
apart of another ``schema_version`` (OD-11), the final name derived from the
content and the write of the file (ADR-0071 decisions 1 and 2, by ADR-0029)
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
_TOP = ("schema_version", "run_id", "round", "verdicts")
_VERDICT = ("hypothesis", "verdict", "cause", "evidence")
_EVIDENCE = {
    "check": ("kind", "ref", "point", "outcome"),
    "comparison": ("kind", "metric", "point", "measured", "against", "difference"),
}
_REF = ("round", "candidate", "attempt")
_VERDICTS = ("supported", "refuted", "inconclusive")
_POINTS = ("sim", "board")
_OUTCOMES = ("pass", "fail", "broken")
_METRICS = ("latency_minimisation",)
_DIFFERENCES = ("lower", "higher", "not_different")


class InvalidVerdictRecordError(ValueError):
    """A verdicts file breaks a rule of ADR-0071; the message names the field path and the rule."""


def validate(document):
    """Return when ``document`` is a valid version-1 verdicts file (ADR-0071).

    ``document`` is the parsed JSON document: a mapping with
    ``schema_version`` (the integer :data:`SCHEMA_VERSION`), ``run_id`` (a
    string), ``round`` (an integer of at least 1) and ``verdicts`` (an array of
    at least one verdict); any other top-level member is passed over. Each
    verdict has exactly ``hypothesis`` (a name unique in the document),
    ``verdict``, ``cause`` and ``evidence``; ``evidence`` is empty only when
    ``verdict`` is ``inconclusive``. A ``check`` entry has ``ref``, ``point``
    and ``outcome``, and no two of one verdict share ``ref`` and ``point``. A
    ``comparison`` entry has ``metric``, ``point``, ``measured`` (a ref of the
    document's ``round``), ``against`` (a ref of a round not above it, other
    than ``measured``) and ``difference``. A ``supported`` or ``refuted``
    verdict holds at least one counted comparison. ``document`` is not
    modified.

    Raises :class:`InvalidVerdictRecordError` for the first rule found broken.
    A ``schema_version`` of any other value, another integer among them, is
    refused as any other wrong value.
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
    verdicts = document["verdicts"]
    _array("verdicts", verdicts, partial(_verdict, round=document["round"]))
    _unique("verdicts", [entry["hypothesis"] for entry in verdicts], "hypothesis")


def _broken(path, rule):
    raise InvalidVerdictRecordError(f"{path}: {rule}")


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


def _array(path, value, entry, *, empty=False):
    if not isinstance(value, list):
        _fail(path, "an array", value)
    if not value and not empty:
        _fail(path, "an array of at least one entry", value)
    for index, item in enumerate(value):
        entry(f"{path}[{index}]", item)


def _unique(path, values, member):
    seen = set()
    for index, value in enumerate(values):
        if value in seen:
            _fail(f"{path}[{index}].{member}", "unique in the array", value)
        seen.add(value)


def _ref(path, value):
    _object(path, value, _REF)
    _integer(f"{path}.round", value["round"])
    _integer(f"{path}.candidate", value["candidate"], 1)
    _integer(f"{path}.attempt", value["attempt"], 1)
    return value["round"], value["candidate"], value["attempt"]


def _verdict(path, entry, *, round):
    _object(path, entry, _VERDICT)
    _name(f"{path}.hypothesis", entry["hypothesis"])
    verdict = entry["verdict"]
    _one_of(f"{path}.verdict", verdict, _VERDICTS)
    _text(f"{path}.cause", entry["cause"])
    evidence = entry["evidence"]
    checks, comparisons = {}, []
    collect = partial(_evidence, round=round, checks=checks, comparisons=comparisons)
    _array(f"{path}.evidence", evidence, collect, empty=True)
    judged = verdict != "inconclusive"
    if judged and not evidence:
        _fail(f"{path}.evidence", f"an array of at least one entry when {verdict}", [])
    counted = any(
        checks.get((measured, "board")) == "pass"
        and checks.get((against, "board")) == "pass"
        for point, measured, against in comparisons
        if point == "board"
    )
    if judged and not counted:
        _broken(
            f"{path}.evidence",
            f"must hold a counted comparison when {verdict}: a comparison at board "
            "whose measured and against both have a check at board with outcome pass",
        )


def _evidence(path, entry, *, round, checks, comparisons):
    if not isinstance(entry, Mapping):
        _fail(path, "an object", entry)
    if "kind" not in entry:
        _broken(f"{path}.kind", "required member is missing")
    kind = entry["kind"]
    _one_of(f"{path}.kind", kind, tuple(_EVIDENCE))
    _object(path, entry, _EVIDENCE[kind])
    _one_of(f"{path}.point", entry["point"], _POINTS)
    point = entry["point"]
    if kind == "check":
        ref = _ref(f"{path}.ref", entry["ref"])
        _one_of(f"{path}.outcome", entry["outcome"], _OUTCOMES)
        if (ref, point) in checks:
            _broken(path, "a check with the same ref and point is already in evidence")
        checks[ref, point] = entry["outcome"]
        return
    _one_of(f"{path}.metric", entry["metric"], _METRICS)
    measured = _ref(f"{path}.measured", entry["measured"])
    if measured[0] != round:
        _fail(f"{path}.measured.round", f"equal to round ({round})", measured[0])
    against = _ref(f"{path}.against", entry["against"])
    if against[0] > round:
        _fail(f"{path}.against.round", f"at most round ({round})", against[0])
    if against == measured:
        _broken(f"{path}.against", "must be other than measured")
    _one_of(f"{path}.difference", entry["difference"], _DIFFERENCES)
    comparisons.append((point, measured, against))
