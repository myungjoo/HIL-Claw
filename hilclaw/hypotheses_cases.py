"""The rules between a round's hypothesis record and the stored cases of its key (ADR-0073 decisions 2 and 3).

``ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`` states
rules between ``decision/hypotheses.json`` of a round and the cases of the key
directory of the run's instance that neither file shows alone: each entry of
``cases_read`` names a valid case in that key directory (decision 3), and the
case a ``basis`` entry of kind ``case`` names is such a case whose
``hypothesis_record`` holds a hypothesis whose ``id`` is ``case.hypothesis``
(decision 2). :func:`check` holds them for a parsed record, after
:func:`hilclaw.hypotheses.validate`, against a :class:`hilclaw.case_lookup.Found`;
:func:`check_run` obtains that value by :func:`hilclaw.case_lookup.lookup`
first. The conventions of types and field paths are those of
:mod:`hilclaw.hypotheses`.

``found`` must be the lookup of the record's own run: :func:`check` cannot
tell, :func:`check_run` ensures it. Then a named case is a valid case in the
key directory exactly when its ``run_id`` and ``round`` are those of a case of
``found.cases``: the lookup gives every valid case there except those of the
reader's own run (decision 1), and the in-file rules forbid a ``cases_read``
or ``case`` entry with the record's own ``run_id``. A case whose file the
lookup reported is not in ``found.cases`` and so breaks the rule.

Not checked: that ``cases_read`` is what the lookup gave at selection time,
which later promotions make uncheckable afterwards (decision 3), so a case of
``found.cases`` that ``cases_read`` does not name is no mismatch; anything of
the verdict of a named case (decision 2); the *refs* inside a case; the copies
against ``runs/``; the rules of a ``hypotheses.json`` copied inside a case;
and cases of another key or version (OD-4, OD-11). It does not decide who
calls it or when, whether a write is refused on a mismatch, how a report of
the lookup is carried or what follows a mismatch (ADR-0073 Boundaries; OD-18,
OD-23). It is no tool, no hook and no command; it writes, creates, removes
and repairs nothing, takes no lock and logs nothing, and it reads only what
:func:`hilclaw.case_lookup.lookup` reads.
"""

import reprlib

from hilclaw import case_lookup
from hilclaw.hypotheses import validate as validate_hypotheses


class MismatchError(ValueError):
    """A valid hypothesis record and the cases of its key directory break a rule between them; the message names the field path in the hypothesis record and the rule."""


def check(hypotheses, found):
    """Return when the parsed ``hypotheses`` keeps the rules between files of ADR-0073 decisions 2 and 3 against ``found``.

    ``hypotheses`` is a parsed hypothesis record (ADR-0059, version 1) and
    ``found`` the :class:`hilclaw.case_lookup.Found` of the record's run. The
    checks come in this order, and the first rule found broken raises:

    1. :class:`TypeError` when ``found`` is not a
       :class:`hilclaw.case_lookup.Found`; then
       :func:`hilclaw.hypotheses.validate` of ``hypotheses``, whose error
       passes through unchanged.
    2. When ``cases_read`` is present, every entry in order has the
       ``run_id`` and ``round`` of a case of ``found.cases`` (decision 3).
       When it is absent nothing of it is checked: the absence is never read
       as "no case read".
    3. For every hypothesis in order and every ``basis`` entry of kind
       ``case`` in order, the ``hypothesis_record`` of the named case holds a
       hypothesis whose ``id`` is ``case.hypothesis`` (decision 2). That the
       named case is in ``found.cases`` follows from step 2, since its pair
       is an entry of ``cases_read`` (in-file rule).

    Neither argument is modified and no file is read. Raises
    :class:`MismatchError` for a rule of steps 2 and 3.
    """
    if not isinstance(found, case_lookup.Found):
        raise TypeError(f"found must be a Found, got {type(found).__name__}")
    validate_hypotheses(hypotheses)
    stored = {(case["run_id"], case["round"]): case for case in found.cases}
    for index, entry in enumerate(hypotheses.get("cases_read", ())):
        pair = (entry["run_id"], entry["round"])
        if pair not in stored:
            _broken(
                f"cases_read[{index}]",
                f"must name a valid case in the key directory of the run's "
                f"instance, got {reprlib.repr(pair)}",
            )
    for index, hypothesis in enumerate(hypotheses["hypotheses"]):
        for at, item in enumerate(hypothesis["basis"]):
            if item["kind"] != "case":
                continue
            case = item["case"]
            held = stored[(case["run_id"], case["round"])]["hypothesis_record"]
            ids = [entry["id"] for entry in held["hypotheses"]]
            if case["hypothesis"] not in ids:
                _broken(
                    f"hypotheses[{index}].basis[{at}].case.hypothesis",
                    f"must be an id of the hypothesis_record of the named case "
                    f"({reprlib.repr(ids)}), got {reprlib.repr(case['hypothesis'])}",
                )


def check_run(data_root, hypotheses):
    """Return the :class:`hilclaw.case_lookup.Found` of the record's run after :func:`check` passes against it.

    ``hypotheses`` is validated first by :func:`hilclaw.hypotheses.validate`,
    before any file is read; then :func:`hilclaw.case_lookup.lookup` of
    ``data_root`` and the record's ``run_id`` gives the value :func:`check`
    is held against. The errors of both pass through unchanged, and so does
    :class:`MismatchError`. The returned value lets a caller see the reports
    of the lookup.
    """
    validate_hypotheses(hypotheses)
    found = case_lookup.lookup(data_root, hypotheses["run_id"])
    check(hypotheses, found)
    return found


def _broken(path, rule):
    raise MismatchError(f"{path}: {rule}")
