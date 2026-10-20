"""Validation and building of the stored hypothesis-outcome case of a round (ADR-0072).

``ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`` fixes
the file ``db/<hw_profile_key>/<op_signature>/case-<run_id>-<RRRR>.json``
(decision 1), which :func:`hilclaw.layout.case_record` builds, the file as a
whole (decision 2) and what one case holds (decision 3): ``hypothesis_record``
and the optional ``verdict_record`` are whole, unchanged copies of the round's
``decision/hypotheses.json`` and ``eval/verdicts.json``. :func:`validate`
checks a parsed case against the rules one document shows; :func:`build`
forms a case from the two parsed documents. The conventions of types, field
paths and the open top level are those of :mod:`hilclaw.hypotheses` and
:mod:`hilclaw.verdicts`; an error of a copy is reported with its field path
prefixed by the member name and chained to the error of the copy's own check.

Not checked or done here: that the file name is formed from the case's
``run_id`` and ``round`` (decision 2; it needs the path); that the case lies in
the key directory of the run's instance (decision 1, a rule between files);
that the copies equal the source files in ``runs/`` (audit, NFR-2); that a
``ref`` names an attempt that exists; reading a case or a copy of another
``schema_version`` (only version 1 of each is read; setting apart is the
caller's, OD-11); the text form, final name and write of the file (ADR-0029
decisions 2, 4, 6 and 7). The hypothesis copy is checked by
:func:`hilclaw.hypotheses.validate`, which admits the ``basis`` kind ``case``
and ``cases_read`` by the in-file rules of ADR-0073 decisions 2 and 3; the
rules between files of those decisions are not checked here. Nothing of the
lookup (ADR-0073 decision 1), promotion, ``best.json``,
``technique_stats.json`` or injection is done here. For the runs of ADR-0120
decision 1 a round's case is built here and written by the tool
``case.write`` (:mod:`hilclaw.case_tool`, ADR-0133), whose record decides
which rounds are promoted and when. Still open: ``best.json`` and
``technique_stats.json`` (OD-20, OD-7), OD-29, OD-25, NFR-1, OD-17 beyond
ADR-0133 decision 5, the creation of the key directory (OD-26) and promotion
in runs outside ADR-0120 decision 1. This module reads, writes and logs
nothing; it is no tool, no hook and no command.
"""

import copy
import re
import reprlib
from collections.abc import Mapping

from hilclaw import keys
from hilclaw.hypotheses import InvalidHypothesisRecordError
from hilclaw.hypotheses import validate as validate_hypotheses
from hilclaw.verdicts import InvalidVerdictRecordError
from hilclaw.verdicts import validate as validate_verdicts
from hilclaw.verdicts_hypotheses import MismatchError
from hilclaw.verdicts_hypotheses import check as check_pair

SCHEMA_VERSION = 1

_STRING = re.compile(r"[\x20-\x7e]{1,255}")
_TOP = ("schema_version", "run_id", "round", "hypothesis_record")
_COPY_ERRORS = (InvalidHypothesisRecordError, InvalidVerdictRecordError, MismatchError)


class InvalidCaseError(ValueError):
    """A case breaks a rule of ADR-0072, or a copy in it a rule of its own record; the message names the field path and the rule."""


def validate(document):
    """Return when ``document`` is a valid version-1 case (ADR-0072 decisions 2 and 3).

    ``document`` is the parsed JSON document. The checks come in this order,
    and the first rule found broken raises:

    1. ``document`` is a mapping with ``schema_version`` (the integer
       :data:`SCHEMA_VERSION`), ``run_id`` (a string of ADR-0001),
       ``round`` (an integer from 1 to :data:`hilclaw.keys.MAX_INTEGER`) and
       ``hypothesis_record``.
    2. ``hypothesis_record`` passes :func:`hilclaw.hypotheses.validate`, and
       its ``run_id`` and ``round`` equal the case's.
    3. If ``verdict_record`` is present, it passes
       :func:`hilclaw.verdicts.validate`, its ``run_id`` and ``round`` equal
       the case's, and :func:`hilclaw.verdicts_hypotheses.check` holds for the
       pair. A present ``verdict_record`` that is not an object, ``null``
       among them, is invalid. An absent one is valid and is never read as
       ``inconclusive`` or as any other value.

    Any other top-level member is passed over. ``document`` is not modified.
    Raises :class:`InvalidCaseError`; for an error of a copy it is chained to
    the error of the copy's check.
    """
    if not isinstance(document, Mapping):
        _fail("case", "an object", document)
    for name in _TOP:
        if name not in document:
            _broken(name, "required member is missing")
    version = document["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        _fail("schema_version", f"the integer {SCHEMA_VERSION}", version)
    run_id, round = document["run_id"], document["round"]
    if type(run_id) is not str or not _STRING.fullmatch(run_id):
        _fail("run_id", "a string of 1 to 255 printable ASCII characters", run_id)
    if type(round) is not int or not 1 <= round <= keys.MAX_INTEGER:
        _fail("round", "an integer from 1 to 2**53 - 1", round)
    hypothesis_record = document["hypothesis_record"]
    _copy("hypothesis_record", validate_hypotheses, hypothesis_record)
    _same("hypothesis_record", hypothesis_record, document)
    if "verdict_record" in document:
        verdict_record = document["verdict_record"]
        _copy("verdict_record", validate_verdicts, verdict_record)
        _same("verdict_record", verdict_record, document)
        _copy(
            "verdict_record",
            check_pair,
            verdict_record,
            hypothesis_record,
        )


def build(hypotheses, verdicts=None):
    """Return a new case of the parsed hypothesis record and, if given, verdicts file.

    The case holds ``schema_version`` :data:`SCHEMA_VERSION`, the ``run_id``
    and ``round`` of ``hypotheses``, a deep copy of ``hypotheses`` as
    ``hypothesis_record`` and, only when ``verdicts`` is not ``None``, a deep
    copy of ``verdicts`` as ``verdict_record``; without verdicts the member is
    absent, never ``null``. Nothing in the copies is added, removed or altered
    (ADR-0072 decision 3). Whether a round without verdicts is promoted is the
    caller's (ADR-0072 Boundaries). The inputs are not modified and the result
    shares no mutable object with them. Both are parsed JSON documents, whose
    objects are ``dict``; another mapping is copied only if
    :func:`copy.deepcopy` copies it.

    Raises :class:`InvalidCaseError` when the result would not pass
    :func:`validate`.
    """
    _copy("hypothesis_record", validate_hypotheses, hypotheses)
    record = copy.deepcopy(hypotheses)
    case = {
        "schema_version": SCHEMA_VERSION,
        "run_id": record["run_id"],
        "round": record["round"],
        "hypothesis_record": record,
    }
    if verdicts is not None:
        case["verdict_record"] = copy.deepcopy(verdicts)
    validate(case)
    return case


def _broken(path, rule):
    raise InvalidCaseError(f"{path}: {rule}")


def _fail(path, rule, value):
    _broken(path, f"must be {rule}, got {reprlib.repr(value)}")


def _copy(member, check, *documents):
    try:
        check(*documents)
    except _COPY_ERRORS as err:
        path, _, rule = str(err).partition(": ")
        path = member if path == "record" else f"{member}.{path}"
        raise InvalidCaseError(f"{path}: {rule}") from err


def _same(member, record, document):
    for name in ("run_id", "round"):
        if record[name] != document[name]:
            _fail(
                f"{member}.{name}",
                f"equal to the {name} of the case ({reprlib.repr(document[name])})",
                record[name],
            )
