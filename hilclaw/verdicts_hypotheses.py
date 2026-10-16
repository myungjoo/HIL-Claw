"""The rules between the verdicts file and the hypothesis record of one round (ADR-0071).

``ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`` states
three rules between ``eval/verdicts.json`` and ``decision/hypotheses.json`` of
the same round that neither file shows alone: one verdict per hypothesis
``id`` (decision 1), ``measured`` within the judged hypothesis's ``tested_by``
(decision 3) and the value of each verdict against the hypothesis's
``expected`` entries (decision 4). :func:`check` holds them for two parsed
documents, after :func:`hilclaw.verdicts.validate` and
:func:`hilclaw.hypotheses.validate`; the conventions of types, field paths and
the open top level are those of :mod:`hilclaw.verdicts` and
:mod:`hilclaw.hypotheses`. A caller that holds the bytes uses
:func:`hilclaw.verdicts_file.parse` and :func:`hilclaw.hypotheses_file.parse`
first.

Not checked: that a ``ref`` names an attempt that exists; which attempt
``against`` must be, the base of the comparison, and so which comparisons a
verdict must include (OD-20, OD-28; decision 4); a magnitude, drift, the text
of ``cause``; and the recommendation on shared candidates (decision 5).
``against`` is not held against ``tested_by``. This module reads, writes and
logs nothing, and it does not decide who calls it or when, whether a write is
refused on a mismatch, or what follows one (ADR-0071 Boundaries; OD-23,
OD-16, OD-18, P2-3). It is no tool, no hook and no command.
"""

import reprlib

from hilclaw import hypotheses as hypothesis_record
from hilclaw import verdicts as verdict_record

_CONTRARY = {"lower": "higher", "higher": "lower"}


class MismatchError(ValueError):
    """Two valid documents of a round break a rule between them; the message names the field path in the verdicts document and the rule."""


def check(verdicts, hypotheses):
    """Return when the parsed ``verdicts`` and ``hypotheses`` of one round keep the rules between them.

    ``verdicts`` is a parsed verdicts file (ADR-0071) and ``hypotheses`` a
    parsed hypothesis record (ADR-0059), both of version 1 (OD-11). The checks
    come in this order, and the first rule found broken raises:

    1. :func:`hilclaw.verdicts.validate` of ``verdicts``, then
       :func:`hilclaw.hypotheses.validate` of ``hypotheses``; their errors
       pass through unchanged.
    2. ``run_id``, then ``round``, are the same in both documents.
    3. Every verdict's ``hypothesis`` is an ``id`` of ``hypotheses``; then
       every ``id`` has a verdict (decision 1). A hypothesis without a verdict
       has none: the absence is never read as ``inconclusive`` or as any other
       value.
    4. For every verdict in turn, every ``comparison`` entry, counted or not,
       has its ``measured.candidate`` in the ``tested_by`` of the judged
       hypothesis (decision 3).
    5. For every verdict in turn, ``verdict`` is the value the rule of
       decision 4 gives. A *counted comparison* is a ``comparison`` at
       ``board`` for whose ``measured`` and ``against`` the same verdict holds
       a ``check`` at ``board`` with ``outcome`` ``pass``. Read against the
       ``expected`` entry of its ``metric``, it is *as expected* when
       ``difference`` equals ``direction``, *contrary* when it is the other of
       ``lower`` and ``higher`` and *no difference* when it is
       ``not_different``; one of a metric the hypothesis does not expect
       counts for nothing (in version 1 both records admit only
       ``latency_minimisation`` and ``expected`` holds at least one entry, so
       no such comparison passes the validators). The value is ``supported``
       when every ``expected`` entry has a counted comparison of its metric
       and all of them are as expected, ``refuted`` when one is contrary and
       none is as expected, and ``inconclusive`` otherwise.

    Neither document is modified. Raises :class:`MismatchError` for a rule of
    steps 2 to 5.
    """
    verdict_record.validate(verdicts)
    hypothesis_record.validate(hypotheses)
    for name in ("run_id", "round"):
        if verdicts[name] != hypotheses[name]:
            _fail(
                name,
                f"equal to the {name} of the hypothesis record "
                f"({reprlib.repr(hypotheses[name])})",
                verdicts[name],
            )
    judged = {entry["id"]: entry for entry in hypotheses["hypotheses"]}
    entries = verdicts["verdicts"]
    for index, entry in enumerate(entries):
        if entry["hypothesis"] not in judged:
            _fail(
                f"verdicts[{index}].hypothesis",
                "an id of the hypothesis record",
                entry["hypothesis"],
            )
    have = {entry["hypothesis"] for entry in entries}
    for index, ident in enumerate(judged):
        if ident not in have:
            _broken(
                "verdicts",
                f"hold no verdict for hypothesis {reprlib.repr(ident)} "
                f"(hypotheses[{index}].id of the hypothesis record)",
            )
    for index, entry in enumerate(entries):
        tested_by = judged[entry["hypothesis"]]["tested_by"]
        for at, item in enumerate(entry["evidence"]):
            if item["kind"] == "comparison":
                candidate = item["measured"]["candidate"]
                if candidate not in tested_by:
                    _fail(
                        f"verdicts[{index}].evidence[{at}].measured.candidate",
                        f"in the tested_by of hypothesis "
                        f"{reprlib.repr(entry['hypothesis'])} "
                        f"({reprlib.repr(tested_by)})",
                        candidate,
                    )
    for index, entry in enumerate(entries):
        value = _value(entry["evidence"], judged[entry["hypothesis"]]["expected"])
        if entry["verdict"] != value:
            _fail(
                f"verdicts[{index}].verdict",
                f"{reprlib.repr(value)} by the rule of ADR-0071 decision 4",
                entry["verdict"],
            )


def _broken(path, rule):
    raise MismatchError(f"{path}: {rule}")


def _fail(path, rule, value):
    _broken(path, f"must be {rule}, got {reprlib.repr(value)}")


def _key(ref):
    return ref["round"], ref["candidate"], ref["attempt"]


def _value(evidence, expected):
    passed = {
        _key(item["ref"])
        for item in evidence
        if item["kind"] == "check"
        and item["point"] == "board"
        and item["outcome"] == "pass"
    }
    direction = {item["metric"]: item["direction"] for item in expected}
    reached, as_expected, contrary, other = set(), False, False, False
    for item in evidence:
        if (
            item["kind"] != "comparison"
            or item["point"] != "board"
            or _key(item["measured"]) not in passed
            or _key(item["against"]) not in passed
            or item["metric"] not in direction
        ):
            continue
        reached.add(item["metric"])
        if item["difference"] == direction[item["metric"]]:
            as_expected = True
        elif item["difference"] == _CONTRARY[direction[item["metric"]]]:
            contrary = True
        else:
            other = True
    if as_expected and not contrary and not other and reached == set(direction):
        return "supported"
    if contrary and not as_expected:
        return "refuted"
    return "inconclusive"
