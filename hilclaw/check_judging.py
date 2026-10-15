"""From the harness's judgement of a report to the result of a check of ``correctness.check``.

``ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md`` (decision
2) gives all of the judging of a report to the code that is the same for every
backend; :func:`hilclaw.harness.verification.judge_report` carries it out and
returns a :class:`hilclaw.harness.verification.Judgement`.
``ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md``
(decisions 2 to 4 and 7) fixes the members of a result, and
:mod:`hilclaw.check_result` builds one from plain values. This module joins
the two:

* :func:`condition_of`: the value of ``condition`` (ADR-0042 decision 3) for a
  member of :class:`hilclaw.harness.verification.Broken`.
* :func:`from_judgement`: the result for a ``Judgement``, built by
  :func:`hilclaw.check_result.completed` or
  :func:`hilclaw.check_result.broken`.
* :func:`from_report`: the result for one report, which is ``judge_report``
  followed by :func:`from_judgement` with the same dimensions, number of draws
  and tolerance on both sides.

Choices that are this module's own and no rule of a record:

* The four members of ``Broken`` and the last four values of
  :data:`hilclaw.check_result.CONDITIONS` are paired by their position; both
  are in the order of ADR-0021 decision 5. The two values ADR-0060 decision 4
  puts before them are found by an operation and stand for no member. All
  four members are mapped, also the two that ``judge_report`` never returns.
  Nothing is said thereby of where a condition is found in a call.
* ``judgement`` is exactly a ``Judgement``. A plain tuple, a
  :class:`hilclaw.harness.verification.VerificationResult` and anything else
  are refused.
* A ``Judgement`` whose fields do not agree is refused and never repaired:
  one that is neither broken nor holds a verdict, a broken one that holds a
  verdict or counts ("A run has no partial verdict", ADR-0017 decision 7), a
  completed one without counts, and a verdict that is not the ``outcome`` its
  counts give (ADR-0042 decision 4).
* A refused argument raises :class:`TypeError` when it, or a field of the
  judgement, is of a type that is not accepted, and :class:`ValueError` when
  a judgement does not have its three fields or when its fields are of
  accepted types and do not agree. The message starts with ``broken: ``,
  ``judgement: ``, ``judgement.broken: ``, ``judgement.verdict: `` or
  ``judgement.counts: ``. What :mod:`hilclaw.check_result` and
  ``judge_report`` raise is passed on unchanged. Nothing is returned then.
* The order of the checks, stated with each function.

What the module does not do: it is no tool and is bound to none. It calls no
operation and says nothing of what an operation returns or of how a report
reaches a caller. It draws no seed and reads no random source or clock. It
reads no file of a run and writes none. It gives no default of any value: no
number of draws, no tolerance, no dimension and no seed. It stores nothing,
keeps nothing between calls and has no command-line entry. It imports
:mod:`hilclaw.check_result` and :mod:`hilclaw.harness.verification` and
nothing else.
"""

from hilclaw import check_result
from hilclaw.harness import verification

_CONDITIONS = dict(zip(verification.Broken, check_result.CONDITIONS[-4:], strict=True))
_OUTCOMES = {
    verification.Verdict.PASS: check_result.PASS,
    verification.Verdict.FAIL: check_result.FAIL,
}


def condition_of(broken):
    """Return the value of ``condition`` for ``broken``, a member of ``Broken``.

    ``Broken.TIMEOUT`` gives ``"time_limit"``, ``Broken.EXIT_STATUS``
    ``"exit_status"``, ``Broken.REPORT_FORM`` ``"report_form"`` and
    ``Broken.CHECK_VALUE`` ``"check_value"`` (ADR-0042 decision 3). The
    returned ``str`` is the item of :data:`hilclaw.check_result.CONDITIONS`.

    Raises :class:`TypeError` for anything that is not a member of
    :class:`hilclaw.harness.verification.Broken`: ``None``, a ``str`` such as
    ``"time_limit"`` or ``"TIMEOUT"``, an ``int`` and a member of another
    enumeration included.
    """
    if type(broken) is not verification.Broken:
        raise TypeError(_wrong_type("broken", "a member of Broken", broken))
    return _CONDITIONS[broken]


def from_judgement(judgement, *, m, k, n, draws, rtol, atol):
    """Return the result of a check for ``judgement``, as a new ``dict``.

    ``judgement`` is exactly a
    :class:`hilclaw.harness.verification.Judgement`. ``m``, ``k``, ``n``,
    ``draws``, ``rtol`` and ``atol`` are the dimensions, the number of draws
    and the tolerance the report was judged with; they are keyword-only, none
    has a default, and each follows the rule of
    :func:`hilclaw.check_result.completed`.

    * ``judgement.broken`` is ``None``: the result is that of
      :func:`hilclaw.check_result.completed` with ``judgement.counts`` handed
      over as it is. Its ``outcome`` is derived from the counts, and
      ``judgement.verdict`` must be the member of
      :class:`hilclaw.harness.verification.Verdict` that says the same.
    * ``judgement.broken`` is a member of ``Broken``: the result is that of
      :func:`hilclaw.check_result.broken` with the condition of
      :func:`condition_of`. ``judgement.verdict`` and ``judgement.counts``
      must be ``None``.

    The checks are made in this order, and the first that fails raises:

    1. :class:`TypeError` for a ``judgement`` that is not exactly a
       ``Judgement``, and :class:`ValueError` for one that does not have its
       three fields.
    2. :class:`TypeError` for a ``broken`` that is neither ``None`` nor a
       member of ``Broken``, then for a ``verdict`` that is neither ``None``
       nor a member of ``Verdict``.
    3. For a broken judgement, :class:`ValueError` for a ``verdict`` that is
       not ``None``, then for a ``counts`` that is not ``None``. For any
       other, :class:`ValueError` for a ``verdict`` that is ``None``, then
       for a ``counts`` that is ``None``.
    4. What the builder of :mod:`hilclaw.check_result` raises for ``m``,
       ``k``, ``n``, ``draws``, ``rtol``, ``atol`` and the counts, unchanged.
    5. For a completed judgement, :class:`ValueError` for a ``verdict`` that
       disagrees with the ``outcome`` of the counts.

    No argument is modified or kept, and the result shares no mutable object
    with ``judgement``.
    """
    if type(judgement) is not verification.Judgement:
        raise TypeError(_wrong_type("judgement", "a Judgement", judgement))
    fields = tuple(judgement)
    if len(fields) != 3:
        raise ValueError(f"judgement: must have 3 fields, got {len(fields)}")
    broken, verdict, counts = fields
    if broken is not None and type(broken) is not verification.Broken:
        rule = "None or a member of Broken"
        raise TypeError(_wrong_type("judgement.broken", rule, broken))
    if verdict is not None and type(verdict) is not verification.Verdict:
        rule = "None or a member of Verdict"
        raise TypeError(_wrong_type("judgement.verdict", rule, verdict))
    common = {"m": m, "k": k, "n": n, "draws": draws, "rtol": rtol, "atol": atol}
    if broken is not None:
        if verdict is not None:
            raise ValueError("judgement.verdict: must be None when broken is set")
        if counts is not None:
            raise ValueError("judgement.counts: must be None when broken is set")
        return check_result.broken(condition_of(broken), **common)
    if verdict is None:
        raise ValueError("judgement.verdict: must not be None when broken is None")
    if counts is None:
        raise ValueError("judgement.counts: must not be None when broken is None")
    result = check_result.completed(**common, counts=counts)
    if result["outcome"] != _OUTCOMES[verdict]:
        raise ValueError(
            f"judgement.verdict: {verdict.name} beside counts of the outcome "
            f"{result['outcome']}"
        )
    return result


def from_report(report, *, m, k, n, draws, seed, rtol, atol):
    """Judge one ``report`` and return the result of the check, as a new ``dict``.

    The report is judged by
    :func:`hilclaw.harness.verification.judge_report` with all eight
    arguments, and its judgement is handed to :func:`from_judgement` with the
    same ``m``, ``k``, ``n``, ``draws``, ``rtol`` and ``atol``, so the result
    names the dimensions, the number of draws and the tolerance the report
    was judged with. ``seed`` is used for the judging only and is no member
    of the result (ADR-0042 decision 6). All but ``report`` are keyword-only
    and none has a default.

    What each argument must be, the order of the checks and what is raised
    are those of ``judge_report`` and are passed on unchanged:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
    for a parameter or a tolerance it refuses, then :class:`TypeError` for a
    ``report`` that is not exactly ``bytes``, and what NumPy raises for arrays
    it cannot allocate. Nothing is returned then.

    Apart from what ``judge_report`` computes the function is pure: equal
    arguments give equal results.
    """
    judgement = verification.judge_report(
        report, m=m, k=k, n=n, draws=draws, seed=seed, rtol=rtol, atol=atol
    )
    return from_judgement(judgement, m=m, k=k, n=n, draws=draws, rtol=rtol, atol=atol)


def _wrong_type(name, rule, value):
    return f"{name}: must be {rule}, got {type(value).__name__}"
