"""The S6 metric of one pair of runs, computed from their recorded facts (ADR-0074; PLAN P2-8).

``ARCHITECTURE/decisions/ADR-0074-od30-s6-metric-one-pair.md`` is the rule; a
decision cited by its number alone is one of that record. It judges one ordered
pair and combines nothing: how many pairs, a control run and the spend are the
owner's (OD-30 sub-question ③, HQ-0081).

**Usage** (the owner's, PLAN P2-9)::

    python -m hilclaw.s6_metric <first_run_id> <second_run_id>

The order of the two ids decides the verdict and is never derived from them. The
data root comes from :func:`hilclaw.data_root_source.configured`. Standard output
gets one compact JSON object in ASCII and one LF, whose ``outcome`` names the kind:

==================  ======  ====================================================
``outcome``         status  further members
==================  ======  ====================================================
``verdict``         0       ``verdict``, ``reason``, the report (below)
``not_a_pair``      10      ``members``: the members of decision 1 that differ
``outside_metric``  11      ``reason``, ``run_id``
``read_failure``    12      ``kind``, ``run_id``, ``reason``
``bad_usage``       20      ``reason``; also an id that is no ``run_id``, or two
                            equal ids, which are not two runs
``no_data_root``    21      ``reason``
``fault``           22      ``fault``: the class name of the exception, if any
==================  ======  ====================================================

Status 0 is any of the three verdicts, because a verdict is an answer. Standard
error gets one line only when standard output is missing or cannot be written;
the status is then that of ``fault``.

**Which ``instance.json``.** Each is read as it stands at the call, with
:func:`hilclaw.instance.read`: the file may change after the start (ADR-0023
decision 6), this tool reads current facts only, and it walks no git history,
which the data root it is given need not hold.

**Before a verdict**, in order: no ``op_signature`` forms no pair
(``outside_metric``, ``no_op_signature``); differing members of decision 1 give
``not_a_pair`` (both leaving one out is equal; ``label``, ``hw_source``,
``source_commit`` and ``draws`` are no condition); then ``outside_metric`` with
``accelerator`` (neither ``cpu_standin`` nor the mock), ``contract``
(:func:`hilclaw.contract_table.start_covers` is false) or ``objective`` (not
exactly ``latency_minimisation`` with no constraint, absence included). **A
limit:** ADR-0120 decision 1 also requires a new run written by the start
function, and the files do not record that, so a resumed, continued or branched
run with the same members is judged like any other.

**A verdict** is exactly ``met``, ``not met`` or ``not applicable``, the words of
the record. ``reason`` is, in the order of decision 3: for ``not applicable``
``(i)`` no first-run best, ``(ii)`` a first-run round of 0 or 1, ``(iii)`` a
second-run round of 0; for ``not met`` ``not_reached``, ``not_fewer_rounds`` or
``no_case_entry``; ``null`` for ``met``.

**The report** beside it: ``first_run_id``, ``second_run_id``; ``first_run_best``
(``round``, ``candidate``, ``attempt``, or ``null``); ``first_run_round`` (or
``null``); ``second_run_round`` (or ``"not reached"``, also with nothing to
reach); ``reaching_attempt`` (or ``null``); ``case_entries``, the ``round``,
``hypothesis`` and ``case`` of each ``case`` entry naming the first run in rounds
1 to the second-run round. Under each of ``first_run`` and ``second_run``:
``board_measurements`` (``up_to_round``, ``count``), up to the run's count or its
last recorded round where it has no such round; ``left_out`` (``up_to_count`` and
``in_all``, each the number of attempts by reason, and ``did_not_reach``, the
attempts that did not reach for a reason of decision 2 other than the interval);
``first_verified_round`` (or ``null``); ``cases_read_runs``; ``imprecise``
(``found``, and ``line``, from :func:`hilclaw.harness.timing_finding.run_found_at`).
Then ``token_spend``, always ``"not available"`` with no figure (OD-19, NFR-5, #5
A-8), ``same_source_commit`` and ``same_draws``.

**Choices of this module, no rule of the record.** An attempt left out is counted
once, under its first reason in the order of :data:`LEFT_OUT_REASONS`: the
measurement rule, then the outcome, then the standing. A qualifying attempt whose
samples the trimmed mean refuses cannot be ordered, so it is no first-run best and
is listed in ``did_not_reach`` with ``samples_out_of_domain``. Among attempts of
the second-run round that reach, the one reported is the lowest candidate, then
attempt. The last recorded round is the highest ``round`` of any line of the log.

**A failure to read** is told apart from a verdict and is never ``not met``:
``instance_missing``, ``instance_invalid``, ``instance_unsupported`` and
``instance_unreadable``; ``run_file_missing`` for a log that is not there, and
the kinds of :func:`hilclaw.checks_tool.log_lines`,
:func:`~hilclaw.checks_tool.checks_of` and
:func:`hilclaw.timings_tool.timing_lines`, ``timing_result_invalid`` also for a
result the imprecise finding refuses; the four kinds of
:func:`hilclaw.hypotheses_tool.read`, ``hypotheses_invalid`` also for a file that
names another ``run_id`` or ``round``. Every record below ``rounds/`` is read for
``cases_read_runs``, so a damaged one in any round is a failure. A missing one is
a failure in a round the case condition reads to decide the verdict; elsewhere
it is passed over, since a round that closed early need not hold one.

It writes no file (Boundaries), starts no process and no build, reads no
``best.json`` or ``best_ref`` (OD-20), does not check that a named case exists
(decision 4), and is no tool: no entry in :mod:`hilclaw.tools`, no MCP name. The
comparison and measurement rules are :mod:`hilclaw.timings_tool`'s, called.
"""

import contextlib
import os
import re
import sys
from typing import NamedTuple

from hilclaw import (
    check_identity,
    check_standing,
    checks_tool,
    contract_table,
    data_root_source,
    hypotheses_tool,
    instance,
    keys,
    layout,
    run_files,
    timings_tool,
    tools,
)
from hilclaw.harness import measurement, timing_finding

VERDICT = "verdict"
NOT_A_PAIR = "not_a_pair"
OUTSIDE_METRIC = "outside_metric"
READ_FAILURE = "read_failure"
BAD_USAGE = "bad_usage"
NO_DATA_ROOT = "no_data_root"
FAULT = "fault"

EXIT_STATUS = {
    VERDICT: 0,
    NOT_A_PAIR: 10,
    OUTSIDE_METRIC: 11,
    READ_FAILURE: 12,
    BAD_USAGE: 20,
    NO_DATA_ROOT: 21,
    FAULT: 22,
}

MET = "met"
NOT_MET = "not met"
NOT_APPLICABLE = "not applicable"

#: The reasons an attempt is left out, in the order it is counted under the first that applies.
LEFT_OUT_REASONS = (
    "several_completed",
    "failure_or_open",
    "only_broken",
    "not_converged",
    "not_verified",
)

_REASON_OF = {
    timings_tool.KIND_MEASUREMENT_SEVERAL: "several_completed",
    timings_tool.KIND_MEASUREMENT_UNKNOWN: "failure_or_open",
    timings_tool.KIND_MEASUREMENT_MISSING: "only_broken",
}
_ACCELERATORS = ("cpu_standin", "mock")
_LATENCY_ONLY = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
_ROUND_NAME = re.compile("[0-9]{4,}")
_OUT_OF_REACH = (
    timings_tool.KIND_SHAPES_DIFFER,
    timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN,
)
_INSTANCE_KINDS = (
    (instance.MissingInstanceError, "instance_missing"),
    (FileNotFoundError, "instance_missing"),
    (NotADirectoryError, "instance_missing"),
    (instance.InvalidInstanceError, "instance_invalid"),
    (instance.UnsupportedVersionError, "instance_unsupported"),
    (OSError, "instance_unreadable"),
)
_FIELDS = (
    "objective",
    "tolerance",
    "candidates_per_round",
    "round_budget",
    "wall_clock_budget_s",
    "n_max",
    "coder_model",
    "injections",
)


class _Unread(Exception):
    def __init__(self, run_id, kind, reason):
        super().__init__(reason)
        self.run_id = run_id
        self.kind = kind
        self.reason = reason


class _Run(NamedTuple):
    run_id: str
    timing: dict
    qualifying: dict
    left_out: dict
    last_round: int | None
    first_verified_round: int | None
    records: dict
    imprecise_line: int | None


def _check_ids(first_run, second_run):
    layout.check_run_id(first_run)
    layout.check_run_id(second_run)
    if first_run == second_run:
        raise ValueError(f"the two runs must differ, both are {first_run}")


def _stated(data_root, run_id):
    try:
        return instance.read(data_root, run_id)
    except tuple(error for error, _ in _INSTANCE_KINDS) as e:
        kind = next(kind for error, kind in _INSTANCE_KINDS if isinstance(e, error))
        raise _Unread(run_id, kind, str(e)) from e


def _outside(reason, run_id):
    return {"outcome": OUTSIDE_METRIC, "reason": reason, "run_id": run_id}


def _differing(first, second):
    keys_of = [
        ("hw_profile", first.hw_profile_key, second.hw_profile_key),
        ("op_signature", first.op_signature.key, second.op_signature.key),
        *((name, getattr(first, name), getattr(second, name)) for name in _FIELDS),
    ]
    return [name for name, one, other in keys_of if one != other]


def _no_verdict(runs, stated):
    both = tuple(zip(runs, stated))
    for run_id, one in both:
        if one.op_signature is None:
            return _outside("no_op_signature", run_id)
    differing = _differing(*stated)
    if differing:
        return {"outcome": NOT_A_PAIR, "members": differing}
    for run_id, one in both:
        if one.hw_profile["accelerator"] not in _ACCELERATORS:
            return _outside("accelerator", run_id)
        if not contract_table.start_covers(one.op_signature.record):
            return _outside("contract", run_id)
        if one.objective != _LATENCY_ONLY:
            return _outside("objective", run_id)
    return None


def _lines(data_root, run_id):
    if not os.path.lexists(layout.run_file(data_root, run_id, checks_tool.LOG)):
        file = run_files.relative(run_id, checks_tool.LOG)
        raise tools.ToolFailure(tools.KIND_RUN_FILE_MISSING, f"{file}: is missing")
    return checks_tool.log_lines(data_root, run_id)


def _verified_attempts(run_id, lines):
    steps = check_standing.STEPS_OF[check_identity.BOARD]
    checked = checks_tool.checks_of(run_id, lines, lambda key: key[0] in steps)
    return {
        key[1:]
        for key in checked
        if check_standing.point_standing(lines, check_identity.BOARD, *key[1:])
        is check_standing.Standing.VERIFIED
    }


def _left_out_reason(numbers, held, verified):
    problem = timings_tool.measurement_problem(held)
    if problem is not None:
        return _REASON_OF[problem]
    if held.entering[0][1]["outcome"] != "converged":
        return "not_converged"
    return None if numbers in verified else "not_verified"


def _imprecise_line(run_id, lines):
    try:
        return timing_finding.run_found_at(lines)
    except (TypeError, ValueError) as e:
        file = run_files.relative(run_id, checks_tool.LOG)
        raise tools.ToolFailure(
            timings_tool.KIND_TIMING_RESULT_INVALID, f"{file}: {e}"
        ) from e


def _record(data_root, run_id, round):
    document = hypotheses_tool.read(data_root, run_id, round)
    if document["run_id"] != run_id or document["round"] != round:
        file = layout.hypothesis_record(data_root, run_id, round)
        raise tools.ToolFailure(
            hypotheses_tool.KIND_HYPOTHESES_INVALID,
            f"{file.relative_to(data_root).as_posix()}: names another run or round",
        )
    return document


def _records(data_root, run_id):
    rounds = layout.run_dir(data_root, run_id) / "rounds"
    try:
        names = [entry.name for entry in rounds.iterdir()]
    except run_files.NOT_THERE:
        names = []
    except OSError as e:
        raise tools.ToolFailure(
            hypotheses_tool.KIND_HYPOTHESES_UNREADABLE, f"{rounds}: {e}"
        ) from e
    found = {}
    for number in sorted(int(name) for name in names if _ROUND_NAME.fullmatch(name)):
        if not 1 <= number <= keys.MAX_INTEGER:
            continue
        try:
            found[number] = _record(data_root, run_id, number)
        except tools.ToolFailure as e:
            if e.kind != hypotheses_tool.KIND_HYPOTHESES_MISSING:
                raise
    return found


@contextlib.contextmanager
def _reading(run_id):
    try:
        yield
    except tools.ToolFailure as e:
        raise _Unread(run_id, e.kind, e.message) from e


def _read_run(data_root, run_id):
    with _reading(run_id):
        lines = _lines(data_root, run_id)
        timing = timings_tool.timing_lines(
            run_id, lines, check_identity.BOARD, lambda numbers: True
        )
        verified = _verified_attempts(run_id, lines)
        qualifying, left_out = {}, {}
        for numbers, held in timing.items():
            reason = _left_out_reason(numbers, held, verified)
            if reason is None:
                qualifying[numbers] = held.entering[0][1]
            else:
                left_out[numbers] = reason
        return _Run(
            run_id=run_id,
            timing=timing,
            qualifying=qualifying,
            left_out=left_out,
            last_round=max((e["round"] for e in lines if "round" in e), default=None),
            first_verified_round=min((n[0] for n in verified), default=None),
            records=_records(data_root, run_id),
            imprecise_line=_imprecise_line(run_id, lines),
        )


def _ref(numbers):
    return dict(zip(("round", "candidate", "attempt"), numbers))


def _best_of(run):
    means, unordered = {}, []
    for numbers, result in sorted(run.qualifying.items()):
        try:
            means[numbers] = measurement.trimmed_mean(result["intervals"])
        except measurement.InvalidSamplesError:
            unordered.append(
                _ref(numbers) | {"reason": timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN}
            )
    best = min(means, key=lambda numbers: (means[numbers], numbers), default=None)
    return best, unordered


def _reaching_of(run, best_result, skipped=None):
    file = run_files.relative(run.run_id, checks_tool.LOG)
    reaching, out = [], []
    for numbers, result in sorted(run.qualifying.items()):
        if numbers == skipped:
            continue
        try:
            difference = timings_tool.difference_of(file, result, best_result)
        except tools.ToolFailure as e:
            if e.kind not in _OUT_OF_REACH:
                raise
            out.append(_ref(numbers) | {"reason": e.kind})
            continue
        if difference in ("not_different", "lower"):
            reaching.append(numbers)
    return reaching, out


def _case_entries(second, first_run, second_round):
    if second_round is None:
        return []
    return [
        {"round": round, "hypothesis": hypothesis["id"], "case": basis["case"]}
        for round, document in sorted(second.records.items())
        if round <= second_round
        for hypothesis in document["hypotheses"]
        for basis in hypothesis["basis"]
        if basis["kind"] == "case" and basis["case"]["run_id"] == first_run
    ]


def _decided(best, first_round, second_round):
    if best is None:
        return NOT_APPLICABLE, "(i)"
    if first_round <= 1:
        return NOT_APPLICABLE, "(ii)"
    if second_round == 0:
        return NOT_APPLICABLE, "(iii)"
    if second_round is None:
        return NOT_MET, "not_reached"
    if second_round >= first_round:
        return NOT_MET, "not_fewer_rounds"
    return None, None


def _each_reason(reasons):
    counts = dict.fromkeys(LEFT_OUT_REASONS, 0)
    for reason in reasons:
        counts[reason] += 1
    return counts


def _run_report(run, count_round, did_not_reach):
    limit = run.last_round if count_round is None else count_round
    count = sum(
        len(held.entering) + len(held.broken)
        for numbers, held in run.timing.items()
        if numbers[0] <= limit
    )
    near = [reason for numbers, reason in run.left_out.items() if numbers[0] <= limit]
    named = {
        entry["run_id"]
        for document in run.records.values()
        for entry in document.get("cases_read", ())
    }
    return {
        "board_measurements": {"up_to_round": limit, "count": count},
        "left_out": {
            "up_to_count": _each_reason(near),
            "in_all": _each_reason(run.left_out.values()),
            "did_not_reach": did_not_reach,
        },
        "first_verified_round": run.first_verified_round,
        "cases_read_runs": sorted(named),
        "imprecise": {
            "found": run.imprecise_line is not None,
            "line": run.imprecise_line,
        },
    }


def _verdict(data_root, runs, stated):
    first_run, second_run = runs
    first, second = (_read_run(data_root, run_id) for run_id in runs)
    best, first_out = _best_of(first)
    first_round = second_round = attempt = None
    second_out = []
    if best is not None:
        reaching, out = _reaching_of(first, first.qualifying[best], best)
        first_out = out
        first_round = min([best[0], *(numbers[0] for numbers in reaching)])
        reaching, second_out = _reaching_of(second, first.qualifying[best])
        if reaching:
            attempt = reaching[0]
            second_round = attempt[0]
    verdict, reason = _decided(best, first_round, second_round)
    entries = _case_entries(second, first_run, second_round)
    if verdict is None:
        with _reading(second_run):
            for round in range(1, second_round + 1):
                if round not in second.records:
                    _record(data_root, second_run, round)
        verdict, reason = (MET, None) if entries else (NOT_MET, "no_case_entry")
    return {
        "outcome": VERDICT,
        "verdict": verdict,
        "reason": reason,
        "first_run_id": first_run,
        "second_run_id": second_run,
        "first_run_best": None if best is None else _ref(best),
        "first_run_round": first_round,
        "second_run_round": "not reached" if second_round is None else second_round,
        "reaching_attempt": None if attempt is None else _ref(attempt),
        "case_entries": entries,
        "first_run": _run_report(first, first_round, first_out),
        "second_run": _run_report(second, second_round, second_out),
        "token_spend": "not available",
        "same_source_commit": stated[0].source_commit == stated[1].source_commit,
        "same_draws": stated[0].draws == stated[1].draws,
    }


def judge(data_root, first_run, second_run):
    """Return the outcome of the metric for the ordered pair (``first_run``, ``second_run``) below ``data_root``.

    @param data_root the data root, a path; nothing below it is written.
    @param first_run the ``run_id`` of the first run of the pair.
    @param second_run the ``run_id`` of the second run; the order is the caller's.
    @return a new ``dict`` that :func:`hilclaw.tools.encode` can write, whose
        ``outcome`` is :data:`VERDICT`, :data:`NOT_A_PAIR`,
        :data:`OUTSIDE_METRIC` or :data:`READ_FAILURE`, with the members of the
        module docstring.
    @throws hilclaw.layout.InvalidPathValueError for an id that is no ``run_id``.
    @throws ValueError for two equal ids.
    """
    _check_ids(first_run, second_run)
    runs = (first_run, second_run)
    try:
        stated = tuple(_stated(data_root, run_id) for run_id in runs)
        return _no_verdict(runs, stated) or _verdict(data_root, runs, stated)
    except _Unread as e:
        return {
            "outcome": READ_FAILURE,
            "kind": e.kind,
            "run_id": e.run_id,
            "reason": e.reason,
        }


def _judged(args, source):
    if len(args) != 2:
        reason = f"usage: expected two run ids, got {len(args)} arguments"
        return {"outcome": BAD_USAGE, "reason": reason}
    try:
        _check_ids(*args)
    except ValueError as e:
        return {"outcome": BAD_USAGE, "reason": str(e)}
    try:
        return judge(data_root_source.obtain(source), *args)
    except tools.ToolFailure as e:
        return {"outcome": NO_DATA_ROOT, "reason": e.message}
    except Exception as e:  # noqa: BLE001
        return {"outcome": FAULT, "fault": type(e).__name__}


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _say(stderr, text):
    with contextlib.suppress(Exception):
        if stderr is not None:
            stderr.write(f"hilclaw.s6_metric: {text}\n".encode("ascii", "replace"))
            stderr.flush()


def main(argv=None, *, source=data_root_source.configured, stdout=None, stderr=None):
    """Judge the pair named by the two arguments; return the exit status.

    ``argv`` defaults to ``sys.argv[1:]``. ``source`` is the data-root source
    (:mod:`hilclaw.data_root_source`), asked once, after the arguments were
    checked. ``stdout`` and ``stderr`` are binary streams and default to the
    standard ones. Returns the status of the module docstring's table; no
    :class:`Exception` leaves the call.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if stdout is None:
        _say(stderr, "fault: there is no standard output; nothing was judged")
        return EXIT_STATUS[FAULT]
    told = _judged(args, source)
    try:
        line = tools.encode(told)
        if stdout.write(line) != len(line):
            raise OSError("it took a part of the line")
        stdout.flush()
    except Exception as e:  # noqa: BLE001
        _say(stderr, f"cannot write standard output: {type(e).__name__}")
        return EXIT_STATUS[FAULT]
    return EXIT_STATUS[told["outcome"]]


if __name__ == "__main__":
    raise SystemExit(main())
