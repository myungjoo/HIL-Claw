import copy
from fractions import Fraction

import pytest

from hilclaw import check_identity, events, journal, run_result
from hilclaw.harness.timing_finding import (
    RESOLUTION_SHARE_MAX,
    line_finding,
    measurement_found,
    run_found_at,
)
from hilclaw.run_identity import STEP_BOARD_RUN, STEP_SIM_RUN

INTERVALS = [104200311, 99870122, 101004517, 100310960, 102118803]
SMALLEST = min(INTERVALS)


def converged(resolution, intervals=INTERVALS):
    return {
        "outcome": "converged",
        "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
        "shape": {"m": 1, "k": 2048, "n": 8192},
        "n_max": 10,
        "sample_form": "interval",
        "unit": "ns",
        "resolution": resolution,
        "intervals": list(intervals),
        "ceiling": "not_stated",
    }


def not_converged(resolution=1, intervals=INTERVALS * 2):
    return converged(resolution, intervals) | {"outcome": "not_converged"}


BROKEN = {
    "outcome": "broken",
    "condition": "exit_status",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "n_max": 10,
    "sample_form": "interval",
    "ceiling": "not_stated",
}
CLEAN = converged(1)
COARSE = converged(SMALLEST // 100 + 1)


def line(kind, data, attempt=1):
    return {
        "schema_version": events.SCHEMA_VERSION,
        "time": "2026-10-18T00:00:00Z",
        "kind": kind,
        "round": 1,
        "candidate": 1,
        "attempt": attempt,
        "data": data,
    }


def started(step=STEP_SIM_RUN, attempt=1):
    return line("step_started", {"step": step, "execution": 1}, attempt)


def ended(result, step=STEP_SIM_RUN, attempt=1):
    data = {"step": step, "execution": 1, "spend": {}, "result": result}
    return line("step_ended", data, attempt)


def failed(step=STEP_SIM_RUN):
    failure = {"kind": "backend_unavailable", "message": "no backend"}
    return line(
        "step_ended", {"step": step, "execution": 1, "spend": {}, "failure": failure}
    )


def test_constant_is_one_percent_exactly():
    assert RESOLUTION_SHARE_MAX == Fraction(1, 100)
    assert type(RESOLUTION_SHARE_MAX) is Fraction


def test_outcomes_are_those_of_the_result_module():
    assert measurement_found({"outcome": run_result.BROKEN}) is False
    assert measurement_found(not_converged() | {"outcome": run_result.NOT_CONVERGED})
    assert not measurement_found(CLEAN | {"outcome": run_result.CONVERGED})


def test_not_converged_with_a_fine_clock_is_found():
    assert measurement_found(not_converged(1)) is True


def test_not_converged_with_empty_intervals_is_found():
    assert measurement_found(not_converged(0, [])) is True


def test_converged_at_exactly_one_percent_is_not_found():
    assert measurement_found(converged(1, [100, 200])) is False
    assert measurement_found(converged(2, [300, 200, 250])) is False


def test_converged_one_nanosecond_beyond_one_percent_is_found():
    assert measurement_found(converged(2, [100, 200])) is True
    assert measurement_found(converged(3, [300, 200, 250])) is True


def test_converged_with_a_fine_clock_is_not_found():
    assert measurement_found(CLEAN) is False


def test_smallest_interval_decides_not_the_others():
    assert measurement_found(converged(2, [1000, 150, 1000])) is True
    assert measurement_found(converged(2, [1000, 200, 1000])) is False


def test_resolution_zero_is_never_found():
    assert measurement_found(converged(0, [1])) is False
    assert measurement_found(converged(0, INTERVALS)) is False


def test_large_integers_are_compared_exactly():
    resolution = 10**20
    smallest = 100 * resolution - 1
    assert not resolution / smallest > 0.01
    assert measurement_found(converged(resolution, [smallest, smallest + 5])) is True
    equal = converged(10**28, [10**30])
    assert measurement_found(equal) is False


def test_tuple_intervals_are_accepted():
    assert measurement_found(converged(2, (100, 200))) is True


def test_broken_is_not_found():
    assert measurement_found(BROKEN) is False


def test_broken_with_stray_members_is_not_found():
    stray = BROKEN | {"resolution": "x", "intervals": None, "extra": [1]}
    assert measurement_found(stray) is False
    assert measurement_found({"outcome": "broken"}) is False


def test_other_members_are_not_checked():
    assert (
        measurement_found(
            {"outcome": "converged", "resolution": 1, "intervals": [1000]}
        )
        is False
    )


@pytest.mark.parametrize("result", [None, [], "converged", (("outcome", "broken"),)])
def test_a_result_that_is_not_a_dict_is_refused(result):
    with pytest.raises(TypeError, match="^result: "):
        measurement_found(result)


def test_a_dict_subclass_is_refused():
    class Result(dict):
        pass

    with pytest.raises(TypeError, match="^result: "):
        measurement_found(Result(BROKEN))


def test_absent_outcome_is_refused():
    with pytest.raises(ValueError, match="^outcome: is absent"):
        measurement_found({})


@pytest.mark.parametrize("outcome", [None, 1, True, b"broken", ["broken"]])
def test_outcome_of_another_type_is_refused(outcome):
    with pytest.raises(TypeError, match="^outcome: "):
        measurement_found(BROKEN | {"outcome": outcome})


def test_outcome_of_a_str_subclass_is_refused_without_calling_it():
    class Name(str):
        def __eq__(self, other):
            raise AssertionError("called")

        __hash__ = str.__hash__

    with pytest.raises(TypeError, match="^outcome: "):
        measurement_found(BROKEN | {"outcome": Name("broken")})


@pytest.mark.parametrize(
    "outcome", ["", "Converged", "not converged", "completed", "broken "]
)
def test_unknown_outcome_is_refused(outcome):
    with pytest.raises(ValueError, match="^outcome: must be"):
        measurement_found(BROKEN | {"outcome": outcome})


@pytest.mark.parametrize("make", [converged, not_converged])
@pytest.mark.parametrize("name", ["resolution", "intervals"])
def test_absent_measurement_member_is_refused(make, name):
    result = make(1)
    del result[name]
    with pytest.raises(ValueError, match=f"^{name}: is absent"):
        measurement_found(result)


@pytest.mark.parametrize("make", [converged, not_converged])
@pytest.mark.parametrize("resolution", [True, False, 1.0, 0.0, "1", None])
def test_resolution_of_another_type_is_refused(make, resolution):
    with pytest.raises(TypeError, match="^resolution: "):
        measurement_found(make(resolution))


@pytest.mark.parametrize("make", [converged, not_converged])
def test_negative_resolution_is_refused(make):
    with pytest.raises(ValueError, match="^resolution: must be at least 0"):
        measurement_found(make(-1))


@pytest.mark.parametrize("intervals", [None, "100", {100: 1}, {100}, range(1, 5), 100])
def test_intervals_of_another_type_are_refused(intervals):
    result = converged(1) | {"intervals": intervals}
    with pytest.raises(TypeError, match="^intervals: must be exactly a list"):
        measurement_found(result)


@pytest.mark.parametrize("entry", [True, 100.0, "100", None])
def test_interval_entry_of_another_type_is_refused(entry):
    with pytest.raises(TypeError, match="^intervals: every entry"):
        measurement_found(converged(1, [100, entry]))
    with pytest.raises(TypeError, match="^intervals: every entry"):
        measurement_found(not_converged(1, [entry]))


@pytest.mark.parametrize("entry", [0, -1])
def test_interval_below_one_is_refused(entry):
    with pytest.raises(ValueError, match="^intervals: every entry must be at least 1"):
        measurement_found(converged(1, [100, entry]))
    with pytest.raises(ValueError, match="^intervals: every entry must be at least 1"):
        measurement_found(not_converged(1, [entry]))


def test_empty_intervals_when_converged_are_refused():
    with pytest.raises(ValueError, match="^intervals: must not be empty"):
        measurement_found(converged(1, []))


@pytest.mark.parametrize(
    "result", [CLEAN, COARSE, not_converged(), BROKEN, converged(-1), converged(1, [0])]
)
def test_result_is_not_modified(result):
    before = copy.deepcopy(result)
    try:
        measurement_found(result)
    except ValueError:
        pass
    assert result == before


def test_line_of_another_kind_gives_none():
    assert line_finding(line("run_started", {"step": STEP_SIM_RUN})) is None


def test_start_line_of_a_run_tool_gives_none():
    assert line_finding(started()) is None
    assert line_finding(started(STEP_BOARD_RUN)) is None


@pytest.mark.parametrize(
    "step", [check_identity.STEP_SIM, check_identity.STEP_BOARD, "made_up_step"]
)
def test_end_line_under_another_step_gives_none(step):
    assert line_finding(ended(COARSE, step)) is None
    assert line_finding(ended({"outcome": "unknown"}, step)) is None


def test_end_line_without_a_step_gives_none():
    assert line_finding(line("step_ended", {})) is None


def test_failure_end_line_gives_false():
    assert line_finding(failed()) is False
    assert line_finding(failed(STEP_BOARD_RUN)) is False


@pytest.mark.parametrize("step", [STEP_SIM_RUN, STEP_BOARD_RUN])
def test_end_line_of_a_run_tool_gives_the_finding_of_its_result(step):
    assert line_finding(ended(CLEAN, step)) is False
    assert line_finding(ended(COARSE, step)) is True
    assert line_finding(ended(not_converged(), step)) is True
    assert line_finding(ended(BROKEN, step)) is False


def test_end_line_with_both_result_and_failure_is_refused():
    event = ended(CLEAN)
    event["data"]["failure"] = {"kind": "backend_unavailable", "message": "no backend"}
    with pytest.raises(journal.JournalError, match="exactly one of result and failure"):
        line_finding(event)


def test_end_line_without_spend_is_refused():
    event = ended(CLEAN)
    del event["data"]["spend"]
    with pytest.raises(journal.JournalError, match="lacks the member spend"):
        line_finding(event)


def test_end_line_with_a_result_that_is_not_an_object_is_refused():
    with pytest.raises(journal.JournalError, match="data.result"):
        line_finding(ended([1, 2]))


def test_end_line_with_a_refused_result_raises_its_error():
    with pytest.raises(ValueError, match="^outcome: must be"):
        line_finding(ended({"outcome": "unknown"}))


@pytest.mark.parametrize("event", [None, [], {"kind": "step_ended"}])
def test_line_with_a_broken_envelope_is_refused(event):
    with pytest.raises(events.InvalidEventError):
        line_finding(event)


def test_line_of_another_version_is_refused():
    event = ended(CLEAN) | {"schema_version": 2}
    with pytest.raises(events.UnsupportedVersionError):
        line_finding(event)


def test_line_is_not_modified():
    event = ended(COARSE)
    before = copy.deepcopy(event)
    line_finding(event)
    assert event == before


def test_empty_log_gives_none():
    assert run_found_at([]) is None
    assert run_found_at(iter(())) is None


def test_log_with_only_clean_results_gives_none():
    log = [
        line("run_started", {}),
        started(),
        ended(CLEAN),
        started(STEP_BOARD_RUN),
        ended(CLEAN, STEP_BOARD_RUN),
        failed(),
        ended(BROKEN, attempt=2),
        ended(COARSE, check_identity.STEP_SIM, attempt=3),
    ]
    assert run_found_at(log) is None


def test_first_found_board_line_after_clean_sim_lines_gives_its_number():
    log = [
        started(),
        ended(CLEAN),
        started(attempt=2),
        ended(CLEAN, attempt=2),
        started(STEP_BOARD_RUN),
        ended(COARSE, STEP_BOARD_RUN),
        ended(not_converged(), attempt=3),
    ]
    assert run_found_at(log) == 6


def test_end_line_without_a_start_line_counts():
    assert run_found_at([ended(CLEAN), ended(not_converged(), attempt=2)]) == 2


def test_second_end_line_of_one_identity_counts():
    assert run_found_at([started(), ended(CLEAN), ended(COARSE)]) == 3


def test_prefix_of_the_log_gives_the_finding_at_that_moment():
    log = [
        started(),
        ended(CLEAN),
        started(STEP_BOARD_RUN),
        ended(COARSE, STEP_BOARD_RUN),
    ]
    assert run_found_at(log[:2]) is None
    assert run_found_at(log) == 4


def test_generator_is_read_once():
    read = []

    def lines():
        for event in [started(), ended(COARSE), ended(CLEAN, attempt=2)]:
            read.append(event)
            yield event

    assert run_found_at(lines()) == 2
    assert len(read) == 3


def test_damaged_line_before_a_finding_raises_with_its_number():
    damaged = ended(CLEAN)
    del damaged["data"]["spend"]
    with pytest.raises(
        journal.JournalError, match="^line 2: data: lacks the member spend"
    ):
        run_found_at([started(), damaged, ended(COARSE, attempt=2)])


def test_damaged_line_after_a_finding_is_still_checked():
    with pytest.raises(events.InvalidEventError, match="^line 3: "):
        run_found_at([started(), ended(COARSE), {"kind": "step_ended"}])


def test_start_line_under_another_step_is_checked():
    bad = line("step_started", {"step": check_identity.STEP_SIM, "execution": 0})
    with pytest.raises(journal.JournalError, match="^line 1: data.execution"):
        run_found_at([bad, ended(COARSE)])


def test_end_line_under_another_step_is_checked():
    bad = ended(CLEAN, check_identity.STEP_SIM)
    del bad["data"]["spend"]
    with pytest.raises(journal.JournalError, match="^line 1: "):
        run_found_at([bad])


def test_refused_result_raises_with_its_line_number():
    with pytest.raises(TypeError, match="^line 2: resolution: "):
        run_found_at([ended(CLEAN), ended(converged(1.0), attempt=2)])


def test_line_of_another_version_raises_with_its_number():
    with pytest.raises(events.UnsupportedVersionError, match="^line 1: "):
        run_found_at([ended(CLEAN) | {"schema_version": 2}])


def test_lines_are_not_modified():
    log = [started(), ended(COARSE), failed()]
    before = copy.deepcopy(log)
    run_found_at(log)
    assert log == before


@pytest.mark.parametrize("unit", ["ns", "ms", None])
def test_the_unit_is_not_read(unit):
    for result in (CLEAN, COARSE, not_converged()):
        changed = copy.deepcopy(result)
        if unit is None:
            del changed["unit"]
        else:
            changed["unit"] = unit
        assert measurement_found(changed) is measurement_found(result)


@pytest.mark.parametrize("name", ["resolution_ns", "intervals_ns"])
def test_the_members_of_the_retired_definition_are_not_read(name):
    result = copy.deepcopy(CLEAN)
    result[name] = result.pop(name.removesuffix("_ns"))
    with pytest.raises(ValueError, match=f"^{name.removesuffix('_ns')}: is absent"):
        measurement_found(result)


@pytest.mark.parametrize("retired", ["sim_run_timing", "board_run_timing"])
def test_an_end_line_under_a_retired_run_value_gives_no_finding(retired):
    assert line_finding(ended(COARSE, step=retired)) is None
    assert run_found_at([started(retired), ended(COARSE, step=retired)]) is None
