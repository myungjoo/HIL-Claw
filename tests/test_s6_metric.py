import io
import json
import pathlib
import subprocess
import sys

import pytest

from hilclaw import (
    contract_table,
    events,
    journal,
    keys,
    layout,
    mock_backend,
    run_result,
    s6_metric,
    standin_profile,
    timings_tool,
    tools,
)
from hilclaw.harness import measurement

FIRST = "20261009t012331z-9f3a6c1e0b7d4a52"
SECOND = "20261020t093000z-0f1e2d3c4b5a6978"
OTHER = "20261001t000000z-aaaaaaaaaaaaaaaa"
TIMING = "board_run_timing_v2"
CHECK = "correctness_check_board_v2"
BOARD_FAILURE = {"kind": "operation_answer_invalid", "message": "no answer"}

A = [104, 99, 101, 100, 102]
C = [130, 100, 96, 104, 98, 101, 97, 103, 99, 102]
D = [100, 97, 99, 101, 98]
FAR = [135, 129, 131, 130, 133]
MID = [125, 119, 121, 120, 122]
BIG = [10**320] * 5

GEMM = next(e for e in contract_table.TABLE.values() if e.contract.KIND == "gemm")
RMSNORM = next(e for e in contract_table.TABLE.values() if e.contract.KIND == "rmsnorm")
PROFILE = {
    "schema_version": 1,
    "accelerator": standin_profile.ACCELERATOR,
    "revision": "synthetic-revision",
    "toolchain": {"clang": "synthetic"},
    "host": {"cpu": "synthetic", "os": "synthetic"},
    "label": "synthetic",
    "hw_source": "external",
}
OP = GEMM.contract.op_signature_record(4, 4, 4)
LATENCY = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
ZERO = dict.fromkeys(s6_metric.LEFT_OUT_REASONS, 0)
COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40


@pytest.fixture
def root(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    return data_root


def hw(profile=PROFILE):
    return {"key": keys.hw_profile_key(profile).name, "record": profile}


def op_member(record=OP):
    return {"key": keys.op_signature_key(record).name, "record": record}


def write_instance(root, run_id, **changes):
    made = {
        "schema_version": 1,
        "hw_profile": hw(),
        "op_signature": op_member(),
        "objective": LATENCY,
        "tolerance": {"rtol": 0.001, "atol": 0.001},
        "candidates_per_round": 1,
        "round_budget": 5,
        "wall_clock_budget_s": 3600,
        "n_max": 10,
        "coder_model": "claude-synthetic-1",
        "source_commit": COMMIT,
        "draws": 2,
    }
    made.update(changes)
    made = {name: value for name, value in made.items() if value is not None}
    path = layout.run_file(root, run_id, "instance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(made), encoding="utf-8")


def pair(root, first=None, second=None):
    write_instance(root, FIRST, **(first or {}))
    write_instance(root, SECOND, **(second or {}))
    touch_log(root, FIRST)
    touch_log(root, SECOND)


def touch_log(root, run_id):
    path = layout.run_file(root, run_id, "events.ndjson")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def timing(intervals, outcome="converged", entry=GEMM, dims=(4, 4, 4)):
    return run_result.completed(
        outcome,
        entry,
        dims,
        unit="ns",
        resolution=0,
        intervals=intervals,
        memory_bytes=None,
        n_max=10,
        sample_form="interval",
        bound=None,
    )


def broken():
    return run_result.broken(
        "time_limit", GEMM, (4, 4, 4), n_max=10, sample_form="interval", bound=None
    )


def lines(root, run_id, step, round, candidate, attempt, execution=1, **outcome):
    numbers = {"round": round, "candidate": candidate, "attempt": attempt}
    started = {"step": step, "execution": execution}
    events.append(root, run_id, journal.STEP_STARTED, started, **numbers)
    if outcome:
        ended = started | {"spend": {}} | outcome
        events.append(root, run_id, journal.STEP_ENDED, ended, **numbers)


def check(root, run_id, round, candidate=1, attempt=1, outcome="pass", execution=1):
    lines(
        root,
        run_id,
        CHECK,
        round,
        candidate,
        attempt,
        execution,
        result={"outcome": outcome},
    )


def measured(root, run_id, round, samples, candidate=1, attempt=1, **changes):
    check(root, run_id, round, candidate, attempt)
    result = timing(samples, **changes)
    lines(root, run_id, TIMING, round, candidate, attempt, result=result)


def hypotheses(root, run_id, round, basis=None, cases_read=None):
    external = {"kind": "external", "source": "s", "version": "v", "text": "synthetic"}
    document = {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "candidates": 1,
        "hypotheses": [
            {
                "id": "h1",
                "statement": "synthetic",
                "basis": basis or [external],
                "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
                "origin": "system",
                "tested_by": [1],
            }
        ],
    }
    if cases_read is not None:
        document["cases_read"] = cases_read
    path = layout.hypothesis_record(root, run_id, round)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def case_entry(run_id=FIRST, round=1, hypothesis="h1"):
    return {
        "kind": "case",
        "case": {"run_id": run_id, "round": round, "hypothesis": hypothesis},
        "text": "synthetic",
    }


def read_of(run_id=FIRST, round=1):
    return {"run_id": run_id, "round": round}


def with_case(root, round=1, run_id=FIRST, other_rounds=()):
    hypotheses(root, SECOND, round, [case_entry(run_id)], [read_of(run_id)])
    for number in other_rounds:
        hypotheses(root, SECOND, number)


def worked_example(root):
    pair(root)
    for round, samples in enumerate((FAR, MID)):
        measured(root, FIRST, round, samples)
    measured(root, FIRST, 2, C, outcome="not_converged")
    measured(root, FIRST, 3, A)
    for round, samples in enumerate((FAR, MID, D)):
        measured(root, SECOND, round, samples)
    with_case(root, 2, other_rounds=(1,))


def judged(root):
    return s6_metric.judge(root, FIRST, SECOND)


def verdict_of(root):
    told = judged(root)
    assert told["outcome"] == s6_metric.VERDICT, told
    return told["verdict"], told["reason"]


def only(reason, count=1):
    return ZERO | {reason: count}


def test_the_worked_example_is_met(root):
    worked_example(root)
    told = judged(root)
    assert told["outcome"] == "verdict"
    assert told["verdict"] == "met"
    assert told["reason"] is None
    assert told["first_run_id"] == FIRST
    assert told["second_run_id"] == SECOND
    assert told["first_run_best"] == {"round": 3, "candidate": 1, "attempt": 1}
    assert told["first_run_round"] == 3
    assert told["second_run_round"] == 2
    assert told["reaching_attempt"] == {"round": 2, "candidate": 1, "attempt": 1}
    assert told["case_entries"] == [
        {
            "round": 2,
            "hypothesis": "h1",
            "case": {"run_id": FIRST, "round": 1, "hypothesis": "h1"},
        }
    ]
    assert told["first_run"]["board_measurements"] == {"up_to_round": 3, "count": 4}
    assert told["second_run"]["board_measurements"] == {"up_to_round": 2, "count": 3}
    left_out = told["first_run"]["left_out"]
    assert left_out["up_to_count"] == only("not_converged")
    assert left_out["in_all"] == only("not_converged")
    assert left_out["did_not_reach"] == []
    assert told["second_run"]["left_out"]["in_all"] == ZERO
    assert told["first_run"]["first_verified_round"] == 0
    assert told["second_run"]["first_verified_round"] == 0
    assert told["first_run"]["cases_read_runs"] == []
    assert told["second_run"]["cases_read_runs"] == [FIRST]
    assert told["token_spend"] == "not available"
    assert told["first_run"]["imprecise"]["found"] is True
    assert type(told["first_run"]["imprecise"]["line"]) is int
    assert told["second_run"]["imprecise"] == {"found": False, "line": None}
    assert told["same_source_commit"] is True
    assert told["same_draws"] is True
    assert tools.encode(told)


def test_the_constants_of_the_scope_are_those_of_the_backends():
    assert standin_profile.ACCELERATOR in s6_metric._ACCELERATORS
    assert mock_backend.NAME in s6_metric._ACCELERATORS
    assert len(s6_metric._ACCELERATORS) == 2


def test_the_records_boundary_case_with_first_run_round_one(root):
    pair(root)
    measured(root, FIRST, 0, FAR)
    measured(root, FIRST, 1, A)
    measured(root, FIRST, 2, FAR)
    measured(root, FIRST, 3, FAR)
    measured(root, SECOND, 0, FAR)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not applicable", "(ii)")
    assert told["first_run_round"] == 1
    assert told["second_run_round"] == "not reached"


def test_a_first_run_round_of_zero_is_not_applicable(root):
    pair(root)
    measured(root, FIRST, 0, A)
    measured(root, SECOND, 0, A)
    assert verdict_of(root) == ("not applicable", "(ii)")


def test_no_qualifying_attempt_in_the_first_run_is_not_applicable(root):
    pair(root)
    measured(root, FIRST, 0, C, outcome="not_converged")
    measured(root, SECOND, 0, A)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not applicable", "(i)")
    assert told["first_run_best"] is None
    assert told["first_run_round"] is None
    assert told["second_run_round"] == "not reached"
    assert told["reaching_attempt"] is None
    assert told["first_run"]["board_measurements"] == {"up_to_round": 0, "count": 1}


def test_a_second_run_round_of_zero_is_not_applicable(root):
    pair(root)
    measured(root, FIRST, 0, FAR)
    measured(root, FIRST, 1, MID)
    measured(root, FIRST, 2, A)
    measured(root, SECOND, 0, D)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not applicable", "(iii)")
    assert told["second_run_round"] == 0


def three_rounds_first(root):
    pair(root)
    measured(root, FIRST, 0, FAR)
    measured(root, FIRST, 1, MID)
    measured(root, FIRST, 2, A)


def test_a_second_run_round_equal_to_the_first_run_round_is_not_met(root):
    three_rounds_first(root)
    measured(root, SECOND, 0, FAR)
    measured(root, SECOND, 2, D)
    with_case(root, 1)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not met", "not_fewer_rounds")
    assert told["second_run_round"] == 2
    assert [entry["round"] for entry in told["case_entries"]] == [1]


def test_a_second_run_that_never_reaches_is_not_met(root):
    three_rounds_first(root)
    measured(root, SECOND, 0, FAR)
    measured(root, SECOND, 3, MID)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not met", "not_reached")
    assert told["second_run_round"] == "not reached"
    assert told["second_run"]["board_measurements"] == {"up_to_round": 3, "count": 2}
    assert told["case_entries"] == []


def test_a_faster_second_run_with_only_cases_read_is_not_met(root):
    three_rounds_first(root)
    measured(root, SECOND, 0, FAR)
    measured(root, SECOND, 1, D)
    hypotheses(root, SECOND, 1, cases_read=[read_of()])
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not met", "no_case_entry")
    assert told["second_run"]["cases_read_runs"] == [FIRST]


def test_a_case_entry_only_after_the_second_run_round_is_not_met(root):
    three_rounds_first(root)
    measured(root, SECOND, 0, FAR)
    measured(root, SECOND, 1, D)
    hypotheses(root, SECOND, 1)
    with_case(root, 2)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not met", "no_case_entry")
    assert told["case_entries"] == []


def test_a_case_entry_naming_another_run_is_not_met(root):
    three_rounds_first(root)
    measured(root, SECOND, 0, FAR)
    measured(root, SECOND, 1, D)
    with_case(root, 1, run_id=OTHER)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not met", "no_case_entry")
    assert told["second_run"]["cases_read_runs"] == [OTHER]


def test_the_case_entry_may_stand_before_the_second_run_round(root):
    pair(root)
    for round, samples in enumerate((FAR, MID, MID, A)):
        measured(root, FIRST, round, samples)
    measured(root, SECOND, 2, D)
    with_case(root, 1, other_rounds=(2,))
    told = judged(root)
    assert told["verdict"] == "met"
    assert (told["first_run_round"], told["second_run_round"]) == (3, 2)


@pytest.mark.parametrize(
    "ties, best",
    [
        (((3, 1, 1), (2, 1, 1)), (2, 1, 1)),
        (((2, 2, 1), (2, 1, 1)), (2, 1, 1)),
        (((2, 1, 2), (2, 1, 1)), (2, 1, 1)),
    ],
)
def test_ties_go_to_round_then_candidate_then_attempt(root, ties, best):
    pair(root)
    for numbers in ties:
        round, candidate, attempt = numbers
        measured(root, FIRST, round, A, candidate=candidate, attempt=attempt)
    told = judged(root)
    assert told["first_run_best"] == dict(zip(("round", "candidate", "attempt"), best))


def test_an_earlier_attempt_that_reaches_lowers_the_first_run_round(root):
    pair(root)
    measured(root, FIRST, 0, FAR)
    measured(root, FIRST, 2, A)
    measured(root, FIRST, 4, D)
    measured(root, SECOND, 0, FAR)
    told = judged(root)
    assert told["first_run_best"]["round"] == 4
    assert told["first_run_round"] == 2
    assert told["first_run"]["board_measurements"] == {"up_to_round": 2, "count": 2}


def test_a_lower_second_run_attempt_reaches(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, [50, 51, 49, 50, 52])
    with_case(root, 1)
    told = judged(root)
    assert told["verdict"] == "met"
    assert told["second_run_round"] == 1


def test_the_reaching_attempt_is_the_lowest_of_its_round(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, FAR, candidate=1)
    measured(root, SECOND, 1, D, candidate=2, attempt=2)
    measured(root, SECOND, 1, D, candidate=3)
    with_case(root, 1)
    told = judged(root)
    assert told["reaching_attempt"] == {"round": 1, "candidate": 2, "attempt": 2}


def left_out_of(root, run=FIRST):
    return judged(root)["first_run" if run == FIRST else "second_run"]["left_out"]


def one_attempt_left(root, write):
    pair(root)
    write(root)
    measured(root, FIRST, 2, A)
    measured(root, SECOND, 0, FAR)


def test_a_not_converged_attempt_is_left_out(root):
    one_attempt_left(root, lambda r: measured(r, FIRST, 1, C, outcome="not_converged"))
    assert left_out_of(root)["in_all"] == only("not_converged")


def test_an_attempt_with_only_broken_results_is_left_out(root):
    def write(r):
        check(r, FIRST, 1)
        lines(r, FIRST, TIMING, 1, 1, 1, result=broken())

    one_attempt_left(root, write)
    told = judged(root)
    assert told["first_run"]["left_out"]["in_all"] == only("only_broken")
    assert told["first_run"]["board_measurements"]["count"] == 2


def test_a_broken_line_beside_one_measurement_still_qualifies(root):
    pair(root)
    measured(root, FIRST, 0, FAR)
    lines(root, FIRST, TIMING, 0, 1, 1, 2, result=broken())
    told = judged(root)
    assert told["first_run_best"]["round"] == 0
    assert told["first_run"]["board_measurements"]["count"] == 2


def test_an_attempt_with_several_completed_results_is_left_out(root):
    def write(r):
        measured(r, FIRST, 1, D)
        lines(r, FIRST, TIMING, 1, 1, 1, 2, result=timing(D))

    one_attempt_left(root, write)
    assert left_out_of(root)["in_all"] == only("several_completed")


def test_an_attempt_with_a_failure_end_line_is_left_out(root):
    def write(r):
        measured(r, FIRST, 1, D)
        lines(r, FIRST, TIMING, 1, 1, 1, 2, failure=BOARD_FAILURE)

    one_attempt_left(root, write)
    assert left_out_of(root)["in_all"] == only("failure_or_open")


def test_an_attempt_with_an_open_identity_is_left_out(root):
    def write(r):
        measured(r, FIRST, 1, D)
        lines(r, FIRST, TIMING, 1, 1, 1, 2)

    one_attempt_left(root, write)
    told = judged(root)
    assert told["first_run"]["left_out"]["in_all"] == only("failure_or_open")
    assert told["first_run"]["board_measurements"]["count"] == 2


def test_an_open_step_counts_for_no_measurement(root):
    pair(root)
    lines(root, FIRST, TIMING, 0, 1, 1)
    told = judged(root)
    assert told["first_run"]["board_measurements"] == {"up_to_round": 0, "count": 0}


@pytest.mark.parametrize("outcome", ["fail", "broken"])
def test_an_attempt_not_verified_is_left_out(root, outcome):
    def write(r):
        check(r, FIRST, 1, outcome=outcome)
        lines(r, FIRST, TIMING, 1, 1, 1, result=timing(D))

    one_attempt_left(root, write)
    assert left_out_of(root)["in_all"] == only("not_verified")


def test_an_attempt_without_a_check_is_left_out_as_not_verified(root):
    one_attempt_left(root, lambda r: lines(r, FIRST, TIMING, 1, 1, 1, result=timing(D)))
    assert left_out_of(root)["in_all"] == only("not_verified")


def test_left_out_counts_stop_at_the_count_but_not_in_all(root):
    pair(root)
    measured(root, FIRST, 0, FAR)
    measured(root, FIRST, 1, A)
    measured(root, FIRST, 2, C, outcome="not_converged")
    measured(root, SECOND, 0, FAR)
    left_out = left_out_of(root)
    assert left_out["up_to_count"] == ZERO
    assert left_out["in_all"] == only("not_converged")


def test_several_goes_before_a_failure_in_the_count(root):
    def write(r):
        measured(r, FIRST, 1, D)
        lines(r, FIRST, TIMING, 1, 1, 1, 2, result=timing(D))
        lines(r, FIRST, TIMING, 1, 1, 1, 3, failure=BOARD_FAILURE)

    one_attempt_left(root, write)
    assert left_out_of(root)["in_all"] == only("several_completed")


def test_the_first_verified_round_is_of_any_attempt_with_a_board_check(root):
    pair(root)
    check(root, FIRST, 0, outcome="fail")
    check(root, FIRST, 1)
    measured(root, FIRST, 2, A)
    told = judged(root)
    assert told["first_run"]["first_verified_round"] == 1
    assert told["second_run"]["first_verified_round"] is None


def test_a_different_contract_does_not_reach_and_is_reported(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, D, entry=RMSNORM, dims=(4, 4))
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not met", "not_reached")
    assert told["second_run"]["left_out"]["did_not_reach"] == [
        {"round": 1, "candidate": 1, "attempt": 1, "reason": "shapes_differ"}
    ]


def test_a_different_shape_does_not_reach_and_is_reported(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, D, dims=(8, 8, 8))
    told = judged(root)
    assert told["second_run_round"] == "not reached"
    assert told["second_run"]["left_out"]["did_not_reach"] == [
        {"round": 1, "candidate": 1, "attempt": 1, "reason": "shapes_differ"}
    ]


def test_samples_outside_the_domain_do_not_reach_and_are_reported(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, BIG)
    told = judged(root)
    assert told["second_run_round"] == "not reached"
    assert told["second_run"]["left_out"]["did_not_reach"] == [
        {"round": 1, "candidate": 1, "attempt": 1, "reason": "samples_out_of_domain"}
    ]


def test_a_first_run_attempt_outside_the_domain_is_no_best_and_is_reported(root):
    three_rounds_first(root)
    measured(root, FIRST, 3, BIG)
    told = judged(root)
    assert told["first_run_best"]["round"] == 2
    assert told["first_run"]["left_out"]["did_not_reach"] == [
        {"round": 3, "candidate": 1, "attempt": 1, "reason": "samples_out_of_domain"}
    ]


def test_a_first_run_only_outside_the_domain_has_no_best(root):
    pair(root)
    measured(root, FIRST, 0, BIG)
    told = judged(root)
    assert (told["verdict"], told["reason"]) == ("not applicable", "(i)")
    assert told["first_run"]["left_out"]["did_not_reach"] == [
        {"round": 0, "candidate": 1, "attempt": 1, "reason": "samples_out_of_domain"}
    ]


def test_the_module_keeps_no_constant_of_the_policy():
    assert not hasattr(s6_metric, "DELTA")
    assert measurement.DELTA == 0.02


OTHER_PROFILE = PROFILE | {"revision": "another"}
OTHER_OP = GEMM.contract.op_signature_record(8, 8, 8)


@pytest.mark.parametrize(
    "member, change",
    [
        ("hw_profile", {"hw_profile": hw(OTHER_PROFILE)}),
        ("op_signature", {"op_signature": op_member(OTHER_OP)}),
        ("objective", {"objective": None}),
        ("tolerance", {"tolerance": {"rtol": 0.5, "atol": 0.001}}),
        ("candidates_per_round", {"candidates_per_round": 2}),
        ("round_budget", {"round_budget": 6}),
        ("wall_clock_budget_s", {"wall_clock_budget_s": 7200}),
        ("n_max", {"n_max": 20}),
        ("coder_model", {"coder_model": "claude-synthetic-2"}),
        (
            "injections",
            {"injections": [{"id": "i1", "kind": "material", "source": "s"}]},
        ),
    ],
)
def test_a_differing_member_is_not_a_pair(root, member, change):
    pair(root, second=change)
    assert judged(root) == {"outcome": "not_a_pair", "members": [member]}


def test_every_differing_member_is_named(root):
    pair(root, second={"n_max": 20, "round_budget": 6})
    assert judged(root)["members"] == ["round_budget", "n_max"]


@pytest.mark.parametrize(
    "member",
    [
        "tolerance",
        "candidates_per_round",
        "round_budget",
        "wall_clock_budget_s",
        "n_max",
        "coder_model",
        "injections",
    ],
)
def test_a_member_both_leave_out_is_equal(root, member):
    pair(root, first={member: None}, second={member: None})
    measured(root, FIRST, 0, A)
    assert judged(root)["outcome"] == "verdict"


def test_a_member_one_leaves_out_differs(root):
    pair(root, second={"n_max": None})
    assert judged(root)["members"] == ["n_max"]


def test_the_attributes_still_form_a_pair_and_two_are_reported(root):
    labelled = PROFILE | {"label": "another", "hw_source": "in_house"}
    pair(
        root,
        second={
            "hw_profile": hw(labelled),
            "source_commit": OTHER_COMMIT,
            "draws": 3,
            "owner": "someone",
            "project": "something",
        },
    )
    assert keys.hw_profile_key(labelled).name == keys.hw_profile_key(PROFILE).name
    measured(root, FIRST, 0, A)
    told = judged(root)
    assert told["outcome"] == "verdict"
    assert told["same_source_commit"] is False
    assert told["same_draws"] is False


def test_both_leaving_out_source_commit_and_draws_is_the_same(root):
    absent = {"source_commit": None, "draws": None}
    pair(root, first=absent, second=absent)
    measured(root, FIRST, 0, A)
    told = judged(root)
    assert told["same_source_commit"] is True
    assert told["same_draws"] is True


@pytest.mark.parametrize("which", [FIRST, SECOND])
def test_a_run_without_an_op_signature_forms_no_pair(root, which):
    change = {"op_signature": None}
    pair(
        root,
        first=change if which == FIRST else None,
        second=change if which == SECOND else None,
    )
    assert judged(root) == {
        "outcome": "outside_metric",
        "reason": "no_op_signature",
        "run_id": which,
    }


def test_another_accelerator_is_outside_the_metric(root):
    other = hw(PROFILE | {"accelerator": "another_npu"})
    pair(root, first={"hw_profile": other}, second={"hw_profile": other})
    assert judged(root) == {
        "outcome": "outside_metric",
        "reason": "accelerator",
        "run_id": FIRST,
    }


def test_the_mock_is_inside_the_metric(root):
    mocked = hw(PROFILE | {"accelerator": mock_backend.NAME})
    pair(root, first={"hw_profile": mocked}, second={"hw_profile": mocked})
    assert judged(root)["outcome"] == "verdict"


def test_a_contract_the_start_does_not_cover_is_outside_the_metric(root, monkeypatch):
    pair(root)
    monkeypatch.setattr(contract_table, "start_covers", lambda record: False)
    assert judged(root) == {
        "outcome": "outside_metric",
        "reason": "contract",
        "run_id": FIRST,
    }


def test_no_objective_is_outside_the_metric(root):
    pair(root, first={"objective": None}, second={"objective": None})
    assert judged(root) == {
        "outcome": "outside_metric",
        "reason": "objective",
        "run_id": FIRST,
    }


def test_another_objective_is_outside_the_metric(root, monkeypatch):
    pair(root)
    read = s6_metric.instance.read
    throughput = {"objectives": [{"type": "throughput"}], "constraints": []}
    monkeypatch.setattr(
        s6_metric.instance,
        "read",
        lambda *a: read(*a)._replace(objective=throughput),
    )
    assert judged(root)["reason"] == "objective"


def test_a_stated_constraint_is_outside_the_metric(root, monkeypatch):
    pair(root)
    read = s6_metric.instance.read
    bounded = LATENCY | {"constraints": [{"type": "memory_ceiling"}]}
    monkeypatch.setattr(
        s6_metric.instance, "read", lambda *a: read(*a)._replace(objective=bounded)
    )
    assert judged(root)["reason"] == "objective"


def failure_of(root):
    told = judged(root)
    assert told["outcome"] == "read_failure", told
    assert set(told) == {"outcome", "kind", "run_id", "reason"}
    return told["kind"], told["run_id"]


def test_a_missing_run_is_a_read_failure(root):
    write_instance(root, FIRST)
    assert failure_of(root) == ("instance_missing", SECOND)


def test_a_missing_data_root_is_a_read_failure(tmp_path):
    told = s6_metric.judge(tmp_path / "gone", FIRST, SECOND)
    assert (told["outcome"], told["kind"]) == ("read_failure", "instance_missing")


@pytest.mark.parametrize(
    "content, kind",
    [
        (b"{", "instance_invalid"),
        (b'{"schema_version": 2}', "instance_unsupported"),
    ],
)
def test_a_damaged_instance_is_a_read_failure(root, content, kind):
    pair(root)
    layout.run_file(root, FIRST, "instance.json").write_bytes(content)
    assert failure_of(root) == (kind, FIRST)


def test_an_unreadable_instance_is_a_read_failure(root, monkeypatch):
    pair(root)

    def denied(*_):
        raise PermissionError("denied")

    monkeypatch.setattr(s6_metric.instance, "read", denied)
    assert failure_of(root) == ("instance_unreadable", FIRST)


def test_a_missing_log_is_a_read_failure(root):
    pair(root)
    layout.run_file(root, SECOND, "events.ndjson").unlink()
    assert failure_of(root) == ("run_file_missing", SECOND)


def test_a_damaged_log_line_is_a_read_failure(root):
    pair(root)
    layout.run_file(root, FIRST, "events.ndjson").write_bytes(b"{damaged\n")
    assert failure_of(root) == ("run_file_invalid", FIRST)


def test_a_log_of_another_version_is_a_read_failure(root):
    pair(root)
    line = {
        "schema_version": 9,
        "time": "2026-10-31T00:00:00Z",
        "kind": "x",
        "data": {},
    }
    layout.run_file(root, SECOND, "events.ndjson").write_text(
        json.dumps(line) + "\n", encoding="utf-8"
    )
    assert failure_of(root) == ("run_file_unsupported", SECOND)


def test_a_malformed_timing_result_is_a_read_failure(root):
    pair(root)
    lines(root, FIRST, TIMING, 0, 1, 1, result={"outcome": "nonsense"})
    assert failure_of(root) == ("timing_result_invalid", FIRST)


def test_a_result_the_imprecise_finding_refuses_is_a_read_failure(root):
    pair(root)
    result = timing(A)
    del result["resolution"]
    lines(root, SECOND, TIMING, 0, 1, 1, result=result)
    assert failure_of(root) == ("timing_result_invalid", SECOND)


def test_a_malformed_check_result_is_a_read_failure(root):
    pair(root)
    lines(root, FIRST, CHECK, 0, 1, 1, result={"outcome": "nonsense"})
    assert failure_of(root) == ("check_result_invalid", FIRST)


def test_a_damaged_hypotheses_file_is_a_read_failure(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, D)
    hypotheses(root, SECOND, 1).write_bytes(b"{")
    assert failure_of(root) == ("hypotheses_invalid", SECOND)


def test_a_damaged_hypotheses_file_of_any_round_is_a_read_failure(root):
    three_rounds_first(root)
    hypotheses(root, FIRST, 2).write_bytes(b"{")
    assert failure_of(root) == ("hypotheses_invalid", FIRST)


def test_a_hypotheses_file_of_another_version_is_a_read_failure(root):
    three_rounds_first(root)
    hypotheses(root, SECOND, 1).write_bytes(b'{"schema_version": 2}\n')
    assert failure_of(root) == ("hypotheses_unsupported", SECOND)


def test_a_hypotheses_file_naming_another_round_is_a_read_failure(root):
    three_rounds_first(root)
    moved = hypotheses(root, SECOND, 1)
    target = layout.hypothesis_record(root, SECOND, 2)
    target.parent.mkdir(parents=True)
    moved.rename(target)
    assert failure_of(root) == ("hypotheses_invalid", SECOND)


def test_a_missing_file_the_case_condition_reads_is_a_read_failure(root):
    three_rounds_first(root)
    measured(root, SECOND, 1, D)
    assert failure_of(root) == ("hypotheses_missing", SECOND)


def test_a_missing_file_the_case_condition_does_not_read_is_no_failure(root):
    three_rounds_first(root)
    measured(root, SECOND, 3, D)
    assert verdict_of(root) == ("not met", "not_fewer_rounds")


def test_other_entries_of_the_rounds_directory_are_passed_over(root):
    three_rounds_first(root)
    measured(root, SECOND, 3, D)
    rounds = layout.run_dir(root, SECOND) / "rounds"
    rounds.mkdir()
    (rounds / "not-a-round").mkdir()
    (rounds / "0000").mkdir()
    assert verdict_of(root) == ("not met", "not_fewer_rounds")


def test_a_failing_listing_is_a_read_failure(root, monkeypatch):
    three_rounds_first(root)
    (layout.run_dir(root, FIRST) / "rounds").mkdir()

    def denied(self):
        raise PermissionError("denied")

    monkeypatch.setattr(pathlib.Path, "iterdir", denied)
    assert failure_of(root) == ("hypotheses_unreadable", FIRST)


@pytest.mark.parametrize(
    "first, second, error",
    [
        ("Not An Id", SECOND, layout.InvalidPathValueError),
        (FIRST, "../up", layout.InvalidPathValueError),
        (FIRST, FIRST, ValueError),
    ],
)
def test_ids_that_name_no_two_runs_are_refused(root, first, second, error):
    with pytest.raises(error):
        s6_metric.judge(root, first, second)


def tree(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def test_the_files_of_the_data_root_are_byte_identical_after_a_call(root):
    worked_example(root)
    before = tree(root)
    judged(root)
    assert tree(root) == before
    assert not list(root.rglob("best.json"))


def test_the_module_is_no_registered_tool():
    names = tools.default_registry(lambda: "unused").names()
    assert not any("s6" in name for name in names)


def test_the_result_never_uses_the_file_value_forms():
    words = (s6_metric.MET, s6_metric.NOT_MET, s6_metric.NOT_APPLICABLE)
    assert words == ("met", "not met", "not applicable")


def call(*args, source=None):
    out, err = io.BytesIO(), io.BytesIO()
    status = s6_metric.main(list(args), source=source, stdout=out, stderr=err)
    return status, out.getvalue(), err.getvalue()


def told_by(root, *args):
    status, out, err = call(*args, source=lambda: root)
    assert err == b""
    assert out.endswith(b"\n") and out.count(b"\n") == 1
    return status, json.loads(out)


def test_the_entry_gives_status_zero_for_met(root):
    worked_example(root)
    status, told = told_by(root, FIRST, SECOND)
    assert (status, told["verdict"]) == (0, "met")
    assert tools.encode(told) == call(FIRST, SECOND, source=lambda: root)[1]


def test_the_entry_gives_status_zero_for_not_met(root):
    three_rounds_first(root)
    status, told = told_by(root, FIRST, SECOND)
    assert (status, told["verdict"]) == (0, "not met")


def test_the_entry_gives_status_zero_for_not_applicable(root):
    pair(root)
    status, told = told_by(root, FIRST, SECOND)
    assert (status, told["verdict"]) == (0, "not applicable")


def test_the_order_of_the_ids_decides_the_verdict(root):
    worked_example(root)
    told = s6_metric.judge(root, SECOND, FIRST)
    assert told["first_run_best"] == {"round": 2, "candidate": 1, "attempt": 1}
    assert (told["verdict"], told["reason"]) == ("not met", "not_fewer_rounds")


def test_the_entry_gives_status_ten_for_not_a_pair(root):
    pair(root, second={"n_max": 20})
    status, told = told_by(root, FIRST, SECOND)
    assert (status, told["outcome"]) == (10, "not_a_pair")


def test_the_entry_gives_status_eleven_for_outside_the_metric(root):
    pair(root, first={"op_signature": None})
    status, told = told_by(root, FIRST, SECOND)
    assert (status, told["outcome"]) == (11, "outside_metric")


def test_the_entry_gives_status_twelve_for_a_read_failure(root):
    status, told = told_by(root, FIRST, SECOND)
    assert (status, told["outcome"]) == (12, "read_failure")


@pytest.mark.parametrize(
    "args",
    [
        (),
        (FIRST,),
        (FIRST, SECOND, OTHER),
        ("Not An Id", SECOND),
        (FIRST, FIRST),
    ],
)
def test_the_entry_gives_status_twenty_for_bad_usage(root, args):
    asked = []
    status, out, _ = call(*args, source=lambda: asked.append(1) or root)
    assert (status, json.loads(out)["outcome"]) == (20, "bad_usage")
    assert asked == []


def test_the_entry_gives_status_twentyone_for_no_data_root(tmp_path):
    status, out, _ = call(FIRST, SECOND, source=lambda: tmp_path / "gone")
    assert (status, json.loads(out)["outcome"]) == (21, "no_data_root")


def test_the_entry_gives_a_fault_for_an_obtain_that_raises_oddly(monkeypatch, root):
    def odd(source):
        raise RuntimeError("odd")

    monkeypatch.setattr(s6_metric.data_root_source, "obtain", odd)
    status, out, _ = call(FIRST, SECOND, source=lambda: root)
    assert (status, json.loads(out)) == (
        22,
        {"outcome": "fault", "fault": "RuntimeError"},
    )


def test_the_entry_gives_a_fault_for_a_judgement_that_raises(monkeypatch, root):
    def odd(*_):
        raise RuntimeError("odd")

    monkeypatch.setattr(s6_metric, "judge", odd)
    status, out, _ = call(FIRST, SECOND, source=lambda: root)
    assert (status, json.loads(out)["outcome"]) == (22, "fault")


def test_the_statuses_are_distinct_and_none_is_one_or_two():
    statuses = list(s6_metric.EXIT_STATUS.values())
    assert len(set(statuses)) == len(statuses)
    assert not {1, 2} & set(statuses)
    assert s6_metric.EXIT_STATUS[s6_metric.VERDICT] == 0


class Refusing(io.BytesIO):
    def write(self, content):
        raise OSError("full")


class Partial(io.BytesIO):
    def write(self, content):
        return 1


@pytest.mark.parametrize("stream", [Refusing, Partial])
def test_an_unwritable_standard_output_is_said_on_standard_error(root, stream):
    err = io.BytesIO()
    status = s6_metric.main(
        [FIRST, SECOND], source=lambda: root, stdout=stream(), stderr=err
    )
    assert status == 22
    assert err.getvalue().startswith(b"hilclaw.s6_metric: cannot write standard output")


def test_a_process_without_standard_output_is_a_fault(root, monkeypatch):
    err = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", None)
    status = s6_metric.main([FIRST, SECOND], source=lambda: root, stderr=err)
    assert status == 22
    assert b"no standard output" in err.getvalue()


def test_the_default_arguments_come_from_the_process(root, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["s6_metric"])
    out = io.BytesIO()
    assert s6_metric.main(source=lambda: root, stdout=out) == 20


def test_the_module_runs_as_a_command_line_entry():
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.s6_metric"], capture_output=True, check=False
    )
    assert done.returncode == 20
    assert json.loads(done.stdout)["outcome"] == "bad_usage"


def test_the_helpers_are_those_of_the_timing_tool(monkeypatch, root):
    three_rounds_first(root)
    measured(root, SECOND, 1, D)
    with_case(root, 1)
    seen = []
    given = timings_tool.difference_of

    def recording(file, measured_result, against):
        seen.append(file)
        return given(file, measured_result, against)

    monkeypatch.setattr(timings_tool, "difference_of", recording)
    assert judged(root)["verdict"] == "met"
    assert seen
