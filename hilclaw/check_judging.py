"""From the harness's judgement of a report to the result of a check of ``correctness.check``.

``ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md`` (decision
2) gives all of the judging of a report to the code that is the same for every
backend; :func:`hilclaw.harness.verification.judge_report` carries it out and
returns a :class:`hilclaw.harness.verification.Judgement`.
``ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`` (decisions 3
and 6) fixes the members of a result, and :mod:`hilclaw.check_result` builds
one from plain values. This module joins the two:

* :func:`condition_of`: the value of ``condition`` (ADR-0042 decision 3) for a
  member of :class:`hilclaw.harness.verification.Broken`.
* :func:`operand_counts`, :func:`from_v2_judgement` and
  :func:`from_v2_report`: the v2 result of a check of any entry of
  :data:`hilclaw.contract_table.TABLE`, built by
  :func:`hilclaw.check_result.v2_completed` or
  :func:`hilclaw.check_result.v2_broken`, with the counts of each draw
  split per output operand by :func:`operand_counts`. Every result of the
  tool is judged by :func:`from_v2_report` (:mod:`hilclaw.check_answer`).

The judge of a bf16 check is
:func:`hilclaw.harness.bf16_verification.judge_report` with the kind and the
dimensions (``ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md``
decision 3). For ``sdpa_kv_cache`` it is
:func:`hilclaw.harness.bf16_sdpa_kv_cache_verification.judge_report` with the
dimensions (ADR-0165 decision 8), whose counts per draw also hold the number
of cache elements that differ in each allocation. For ``rope`` it is
:func:`hilclaw.harness.bf16_rope_verification.judge_report` with the
dimensions and the start position that
:func:`hilclaw.harness.bf16_rope_verification.start_position` gives for the
dimensions and the seed (ADR-0164 decision 10; ADR-0180 decision 1). The
verdict classes and the conditions are those of
:func:`hilclaw.harness.verification.judge_report`: ADR-0163 to ADR-0165 have
them as ADR-0017 decision 7, with the same types.

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
  ``judgement.counts: `` (or ``judgement.counts[i]: ``). What :mod:`hilclaw.check_result` and
  ``judge_report`` raise is passed on unchanged. Nothing is returned then.
* The order of the checks, stated with each function.
* A judge's counts of one draw hold ``(failed, non_finite)`` of each output
  operand judged by tolerance, in contract order, then the differences of
  each operand of :data:`hilclaw.check_result.BIT_EXACT`, in its order:
  :class:`hilclaw.harness.verification_arrays.Counts` for one operand and
  :class:`hilclaw.harness.bf16_sdpa_kv_cache_verification.DrawCounts` for
  ``out``, ``cache_k`` and ``cache_v``. :func:`operand_counts` reads them
  so by position.
* The judge of :func:`from_v2_report` is chosen by the ``kind`` and
  ``dtype`` of the entry's contract: fp32 ``gemm`` is judged by
  :func:`hilclaw.harness.verification.judge_report`, every other kind by
  the judge of a bf16 check above.

What the module does not do: it is no tool and is bound to none. It calls no
operation and says nothing of what an operation returns or of how a report
reaches a caller. It draws no seed and reads no random source or clock. It
reads no file of a run and writes none. It gives no default of any value: no
number of draws, no tolerance, no dimension and no seed. It stores nothing,
keeps nothing between calls and has no command-line entry. It imports
:mod:`hilclaw.check_result`, :mod:`hilclaw.harness.verification`,
:mod:`hilclaw.harness.bf16_verification`,
:mod:`hilclaw.harness.bf16_rope_verification` and
:mod:`hilclaw.harness.bf16_sdpa_kv_cache_verification` and nothing else.
"""

from hilclaw import check_result
from hilclaw.harness import (
    bf16_rope_verification,
    bf16_sdpa_kv_cache_verification,
    bf16_verification,
    verification,
)

_CONDITIONS = dict(zip(verification.Broken, check_result.CONDITIONS[-4:], strict=True))
_SDPA = "sdpa_kv_cache"
_ROPE = "rope"
_FP32_GEMM = ("gemm", "fp32")
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


def _wrong_type(name, rule, value):
    return f"{name}: must be {rule}, got {type(value).__name__}"


def _bf16_judge(report, kind, dims, common):
    if kind == _SDPA:
        return bf16_sdpa_kv_cache_verification.judge_report(report, dims, **common)
    if kind == _ROPE:
        rope = bf16_rope_verification
        start = rope.start_position(dims, seed=common["seed"])
        return rope.judge_report(report, dims, start=start, **common)
    return bf16_verification.judge_report(report, kind, dims, **common)


def operand_counts(entry, dims, counts):
    """Return a judge's per-draw ``counts`` as the per-operand counts of a v2 result.

    ``entry`` and ``dims`` are those of
    :func:`hilclaw.check_result.output_operands`, checked first and as it
    checks them. ``counts`` is the ``counts`` of a completed
    :class:`hilclaw.harness.verification.Judgement`: exactly a ``tuple`` or
    a ``list`` of one ``tuple`` per draw (a subclass is read as the tuple it
    is), each of ``2 * t + b`` items, ``t`` the output operands judged by
    tolerance and ``b`` those of :data:`hilclaw.check_result.BIT_EXACT`
    for the entry's contract, laid out as the module docstring says.

    The result is a new ``dict`` with one member per name of
    ``output_operands(entry, dims)``, in that order, each a new ``list``
    with one item per draw: a new ``tuple`` ``(failed, non_finite)`` for an
    operand judged by tolerance and the difference itself for a bit-exact
    one, the form :func:`hilclaw.check_result.v2_completed` takes. The
    values are not checked here; that builder checks them. For an
    ``sdpa_kv_cache`` draw ``DrawCounts(f, n, k, v)`` gives ``cache_k`` the
    item ``k``, ``cache_v`` the item ``v`` and ``out`` the item ``(f, n)``.

    Raises :class:`TypeError` for a ``counts`` or an entry of another type
    and :class:`ValueError` for an entry of another number of items; the
    message starts with ``judgement.counts``.
    """
    names = check_result.output_operands(entry, dims)
    contract = entry.contract
    exact = check_result.BIT_EXACT.get(
        (contract.KIND, contract.DTYPE, contract.LAYOUT), ()
    )
    judged = [name for name in names if name not in exact]
    if type(counts) not in (list, tuple):
        rule = "a tuple or a list"
        raise TypeError(_wrong_type("judgement.counts", rule, counts))
    width = 2 * len(judged) + len(exact)
    taken = {name: [] for name in names}
    for i, entry_counts in enumerate(counts):
        label = f"judgement.counts[{i}]"
        if not isinstance(entry_counts, tuple):
            raise TypeError(_wrong_type(label, "a tuple", entry_counts))
        items = tuple(tuple.__iter__(entry_counts))
        if len(items) != width:
            raise ValueError(f"{label}: must have {width} items, got {len(items)}")
        for position, name in enumerate(judged):
            taken[name].append(items[2 * position : 2 * position + 2])
        for position, name in enumerate(exact, start=2 * len(judged)):
            taken[name].append(items[position])
    return taken


def from_v2_judgement(judgement, entry, dims, *, draws, rtol, atol):
    """Return the v2 result of a check of ``entry``'s contract for ``judgement``, as a new ``dict``.

    ``judgement`` is exactly a
    :class:`hilclaw.harness.verification.Judgement`. ``entry``, ``dims``,
    ``draws``, ``rtol`` and ``atol`` are those the report was judged with
    (``draws`` and the tolerance keyword-only, none with a default).

    * ``judgement.broken`` is ``None``: the result is that of
      :func:`hilclaw.check_result.v2_completed` from :func:`operand_counts`
      of ``judgement.counts``. Its ``outcome`` is derived from the counts of
      all operands, and ``judgement.verdict`` must be the member of
      :class:`hilclaw.harness.verification.Verdict` that says the same
      (ADR-0183 decision 3).
    * ``judgement.broken`` is a member of ``Broken``: the result is that of
      :func:`hilclaw.check_result.v2_broken` with the condition of
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
    4. What :func:`operand_counts` and the builders of
       :mod:`hilclaw.check_result` raise, unchanged.
    5. For a completed judgement, :class:`ValueError` for a ``verdict`` that
       disagrees with the ``outcome`` of the counts.

    No argument is modified or kept, and the result shares no mutable object
    with ``judgement``.
    """
    common = {"draws": draws, "rtol": rtol, "atol": atol}
    return _from_judgement(
        judgement,
        lambda condition: check_result.v2_broken(condition, entry, dims, **common),
        lambda counts: check_result.v2_completed(
            entry, dims, **common, counts=operand_counts(entry, dims, counts)
        ),
    )


def from_v2_report(report, entry, dims, *, draws, seed, rtol, atol):
    """Judge one ``report`` of a check of ``entry``'s contract and return its v2 result, as a new ``dict``.

    ``entry`` and ``dims`` are first checked as
    :func:`hilclaw.check_result.output_operands` checks them. The report is
    then judged by the judge of the entry's contract (module docstring):
    for fp32 ``gemm`` :func:`hilclaw.harness.verification.judge_report`
    with ``dims`` as ``m``, ``k``, ``n``, otherwise as
    by the judge of a bf16 check of the contract's ``kind``, with ``dims``,
    ``draws``, ``seed``, ``rtol`` and ``atol``, and for ``rope`` with the
    ``start`` of :func:`hilclaw.harness.bf16_rope_verification.start_position`
    for ``dims`` and ``seed``. Its judgement is handed to :func:`from_v2_judgement` with the same
    values but ``seed``, which is no member of the result (ADR-0042
    decision 6). All but ``report``, ``entry`` and ``dims`` are
    keyword-only and none has a default.

    What each other argument must be, the order of the checks and what is
    raised are those of the ``judge_report`` called and are passed on
    unchanged:
    :class:`hilclaw.harness.verification_arrays.VerificationArgumentError`
    for a number of draws, seed or tolerance it refuses (for ``rope``, first
    what ``start_position`` refuses of the seed), then :class:`TypeError` for
    a ``report`` that is not exactly ``bytes``, and what NumPy raises for
    arrays it cannot allocate. Nothing is returned then.
    """
    check_result.output_operands(entry, dims)
    common = {"draws": draws, "seed": seed, "rtol": rtol, "atol": atol}
    kind = entry.contract.KIND
    if (kind, entry.contract.DTYPE) == _FP32_GEMM:
        m, k, n = dims
        judgement = verification.judge_report(report, m=m, k=k, n=n, **common)
    else:
        judgement = _bf16_judge(report, kind, dims, common)
    return from_v2_judgement(judgement, entry, dims, draws=draws, rtol=rtol, atol=atol)


def _from_judgement(judgement, broken_result, completed_result):
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
    if broken is not None:
        if verdict is not None:
            raise ValueError("judgement.verdict: must be None when broken is set")
        if counts is not None:
            raise ValueError("judgement.counts: must be None when broken is set")
        return broken_result(condition_of(broken))
    if verdict is None:
        raise ValueError("judgement.verdict: must not be None when broken is None")
    if counts is None:
        raise ValueError("judgement.counts: must not be None when broken is None")
    result = completed_result(counts)
    if result["outcome"] != _OUTCOMES[verdict]:
        raise ValueError(
            f"judgement.verdict: {verdict.name} beside counts of the outcome "
            f"{result['outcome']}"
        )
    return result
