import errno
import json
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    checks_tool,
    contract_table,
    events,
    journal,
    keys,
    layout,
    mcp_front,
    run_identity,
    run_result,
    timings_tool,
    tools,
)
from hilclaw.harness import measurement
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
LOG = f"runs/{RUN}/events.ndjson"
SIM = "sim_run_timing_v2"
BOARD = "board_run_timing_v2"
GEMM = next(e for e in contract_table.TABLE.values() if e.contract.KIND == "gemm")
RMSNORM = next(e for e in contract_table.TABLE.values() if e.contract.KIND == "rmsnorm")
ADD = next(
    e for e in contract_table.TABLE.values() if e.contract.KIND == "elementwise_add"
)
MEASURED = {"round": 1, "candidate": 1, "attempt": 1}
AGAINST = {"round": 0, "candidate": 1, "attempt": 1}
SLOW = [1000, 1001, 999, 1000, 1002]
FAST = [500, 501, 499, 500, 502]
CLOSE = [1000, 1002, 1001, 999, 1000]
FAILED = {"kind": "operation_answer_invalid", "message": "no answer"}
NEW_KINDS = (
    "timing_result_invalid",
    "measurement_several",
    "measurement_unknown",
    "measurement_missing",
    "shapes_differ",
    "samples_out_of_domain",
)
KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_unreadable",
    "run_file_invalid",
    "run_file_unsupported",
    *NEW_KINDS,
)


class Source:
    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.root


class FailingSource:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise RuntimeError("no data root in this test")


@pytest.fixture
def root(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    return data_root


def timing(outcome="converged", intervals=SLOW, m=4, k=4, n=4, entry=None, dims=None):
    return run_result.completed(
        outcome,
        entry or GEMM,
        dims or (m, k, n),
        unit="ns",
        resolution=1,
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


def start(root, ref, execution=1, step=BOARD):
    data = {"step": step, "execution": execution}
    events.append(root, RUN, journal.STEP_STARTED, data, **ref)


def end(root, ref, execution=1, step=BOARD, **outcome):
    data = {"step": step, "execution": execution, "spend": {}, **outcome}
    events.append(root, RUN, journal.STEP_ENDED, data, **ref)


def run(root, ref, execution=1, step=BOARD, **outcome):
    start(root, ref, execution, step)
    end(root, ref, execution, step, **outcome)


def raw(root, content):
    path = layout.run_file(root, RUN, "events.ndjson")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as f:
        f.write(content)


def line(data, kind=journal.STEP_ENDED, version=1, ref=MEASURED):
    event = {"schema_version": version, "time": "2026-10-21T00:00:00Z", "kind": kind}
    return (json.dumps(event | ref | {"data": data}) + "\n").encode()


def request(**changes):
    given = {
        "run_id": RUN,
        "metric": "latency_minimisation",
        "point": "board",
        "measured": dict(MEASURED),
        "against": dict(AGAINST),
    }
    return given | changes


def without(member):
    return {k: v for k, v in request().items() if k != member}


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes() if p.is_file() else None
        for p in root.rglob("*")
    }


def compared(root, given=None):
    before = snapshot(root)
    source = Source(root)
    result = timings_tool.definition(source).function(given or request())
    assert source.calls == 1
    assert snapshot(root) == before
    return result


def failure(root, given=None):
    before = snapshot(root) if root.is_dir() else None
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(Source(root)).function(given or request())
    if before is not None:
        assert snapshot(root) == before
    return refused.value


def both(root, measured=FAST, against=SLOW):
    run(root, MEASURED, result=timing(intervals=measured))
    run(root, AGAINST, result=timing(intervals=against))


def answer(difference, measured=(1, "converged"), against=(1, "converged")):
    return {
        "difference": difference,
        "measured": {"execution": measured[0], "outcome": measured[1]},
        "against": {"execution": against[0], "outcome": against[1]},
    }


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = timings_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == timings_tool.NAME == "timings.compare"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "metric": {"type": "string", "enum": ["latency_minimisation"]},
            "point": {"type": "string", "enum": ["sim", "board"]},
            "measured": {"type": "object"},
            "against": {"type": "object"},
        },
        "required": ["run_id", "metric", "point", "measured", "against"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert timings_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="must be callable"):
        timings_tool.definition(source)


def test_the_description_names_every_kind_and_what_it_tells():
    description = timings_tool.definition(lambda: None).description
    for kind in KINDS:
        assert kind in description
    for text in (
        "events.ndjson",
        "never part of the request",
        "latency_minimisation",
        "sim or board",
        '{"round": r, "candidate": c, "attempt": a}',
        '"lower"',
        '"higher"',
        '"not_different"',
        "measured against that of the attempt against",
        (
            '{"difference": d, "measured": {"execution": n, "outcome": o}, '
            '"against": {"execution": n, "outcome": o}}'
        ),
        "broken results are ignored",
    ):
        assert text in description


def test_the_new_kinds_are_of_the_tool_layer_and_not_reserved():
    constants = (
        timings_tool.KIND_TIMING_RESULT_INVALID,
        timings_tool.KIND_MEASUREMENT_SEVERAL,
        timings_tool.KIND_MEASUREMENT_UNKNOWN,
        timings_tool.KIND_MEASUREMENT_MISSING,
        timings_tool.KIND_SHAPES_DIFFER,
        timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN,
    )
    assert constants == NEW_KINDS
    assert not set(NEW_KINDS) & tools.RESERVED_KINDS


def test_the_steps_of_the_points_are_those_of_the_run_tools():
    assert timings_tool.STEP_OF == {
        "sim": run_identity.STEP_SIM_RUN,
        "board": run_identity.STEP_BOARD_RUN,
    }
    assert timings_tool.METRIC == "latency_minimisation"
    assert timings_tool._OUTCOMES == (
        run_result.CONVERGED,
        run_result.NOT_CONVERGED,
        run_result.BROKEN,
    )


# Happy cases


def test_a_faster_measured_is_lower(root):
    both(root, FAST, SLOW)
    assert compared(root) == answer("lower")


def test_a_slower_measured_is_higher(root):
    both(root, SLOW, FAST)
    assert compared(root) == answer("higher")


def test_close_samples_are_not_different(root):
    both(root, CLOSE, SLOW)
    assert compared(root) == answer("not_different")


def test_the_sim_point_reads_the_sim_lines(root):
    run(root, MEASURED, step=SIM, result=timing(intervals=FAST))
    run(root, AGAINST, step=SIM, result=timing(intervals=SLOW))
    assert compared(root, request(point="sim")) == answer("lower")
    assert failure(root).kind == timings_tool.KIND_MEASUREMENT_MISSING


@pytest.mark.parametrize(
    ("measured", "against"),
    [(FAST, SLOW), (SLOW, FAST), (CLOSE, SLOW), (SLOW, CLOSE)],
)
def test_the_difference_agrees_with_ratio_interval_in_the_order_against_measured(
    root, measured, against
):
    both(root, measured, against)
    low, high = measurement.ratio_interval(against, measured)
    if high < 1 / (1 + measurement.DELTA):
        expected = "lower"
    elif low > 1 + measurement.DELTA:
        expected = "higher"
    else:
        expected = "not_different"
    assert compared(root)["difference"] == expected
    different = measurement.is_different(against, measured)
    assert (expected != "not_different") is different


# Which results enter (the walk-through of ADR-0140)


@pytest.mark.parametrize("side", ["measured", "against"])
def test_a_not_converged_side_enters(root, side):
    ref = MEASURED if side == "measured" else AGAINST
    other = AGAINST if side == "measured" else MEASURED
    run(root, ref, result=timing("not_converged", FAST if side == "measured" else SLOW))
    run(root, other, result=timing(intervals=SLOW if side == "measured" else FAST))
    result = compared(root)
    assert result["difference"] == "lower"
    assert result[side] == {"execution": 1, "outcome": "not_converged"}


def test_a_broken_line_beside_a_converged_one_gives_the_converged_one(root):
    run(root, MEASURED, 1, result=broken())
    run(root, MEASURED, 2, result=timing(intervals=FAST))
    run(root, AGAINST, 3, result=timing(intervals=SLOW))
    assert compared(root) == answer(
        "lower", measured=(2, "converged"), against=(3, "converged")
    )


def test_two_executions_are_measurement_several(root):
    both(root)
    run(root, MEASURED, 2, result=timing(intervals=FAST))
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_SEVERAL
    assert refused.message == (
        f"{LOG}: measured (round 1, candidate 1, attempt 1) at {BOARD}: "
        "has 2 measurements (executions 1, 2)"
    )


def test_two_end_lines_of_one_identity_are_measurement_several(root):
    run(root, MEASURED, result=timing(intervals=FAST))
    end(root, AGAINST, result=timing("not_converged"))
    start(root, AGAINST)
    end(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_SEVERAL
    assert refused.message.startswith(f"{LOG}: against (round 0, candidate 1")


def test_a_converged_line_beside_an_open_identity_is_measurement_unknown(root):
    both(root)
    start(root, AGAINST, 2)
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_UNKNOWN
    assert refused.message == (
        f"{LOG}: against (round 0, candidate 1, attempt 1) at {BOARD}: "
        "has a failed or unfinished run (execution 2)"
    )


def test_a_converged_line_beside_a_failure_is_measurement_unknown(root):
    both(root)
    run(root, AGAINST, 2, failure=FAILED)
    assert failure(root).kind == timings_tool.KIND_MEASUREMENT_UNKNOWN


def test_only_a_failure_is_measurement_unknown(root):
    run(root, MEASURED, failure=FAILED)
    run(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_UNKNOWN
    assert refused.message.startswith(f"{LOG}: measured ")


def test_a_failure_without_a_start_line_is_measurement_unknown(root):
    run(root, AGAINST, result=timing())
    end(root, MEASURED, failure=FAILED)
    run(root, MEASURED, 2, result=timing(intervals=FAST))
    assert failure(root).kind == timings_tool.KIND_MEASUREMENT_UNKNOWN


def test_an_ended_identity_with_two_start_lines_is_not_open(root):
    start(root, MEASURED)
    run(root, MEASURED, result=timing(intervals=FAST))
    run(root, AGAINST, result=timing())
    assert compared(root) == answer("lower")


def test_several_comes_before_unknown(root):
    both(root)
    run(root, MEASURED, 2, result=timing())
    start(root, MEASURED, 3)
    assert failure(root).kind == timings_tool.KIND_MEASUREMENT_SEVERAL


@pytest.mark.parametrize("lines", ["none", "broken only"])
def test_no_measurement_is_measurement_missing(root, lines):
    if lines == "broken only":
        run(root, MEASURED, result=broken())
    run(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_MISSING
    assert refused.message == (
        f"{LOG}: measured (round 1, candidate 1, attempt 1) at {BOARD}: "
        "has no measurement"
    )


def test_measured_is_judged_before_against(root):
    run(root, AGAINST, 1, result=timing())
    run(root, AGAINST, 2, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_MISSING
    assert refused.message.startswith(f"{LOG}: measured ")


def test_a_missing_against_names_against(root):
    run(root, MEASURED, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_MISSING
    assert refused.message.startswith(f"{LOG}: against ")


def test_round_zero_attempts_are_compared(root):
    zero = {"round": 0, "candidate": 2, "attempt": 3}
    run(root, zero, result=timing(intervals=FAST))
    run(root, AGAINST, result=timing())
    assert compared(root, request(measured=zero))["difference"] == "lower"


@pytest.mark.parametrize(
    "other",
    [
        {"step": SIM},
        {"ref": {"round": 1, "candidate": 1, "attempt": 2}},
        {"ref": {"round": 1, "candidate": 2, "attempt": 1}},
        {"ref": {"round": 2, "candidate": 1, "attempt": 1}},
        {"step": "correctness_check_board"},
    ],
)
def test_lines_of_the_other_point_attempts_and_candidates_are_ignored(root, other):
    ref, step = other.get("ref", MEASURED), other.get("step", BOARD)
    run(root, ref, 1, step, result=timing())
    run(root, ref, 2, step, failure=FAILED)
    start(root, ref, 3, step)
    end(root, ref, 4, step, result={"outcome": "nonsense"})
    both(root)
    assert compared(root) == answer("lower")


def test_lines_of_other_kinds_are_ignored(root):
    events.append(root, RUN, "round_started", {"step": BOARD}, **MEASURED)
    both(root)
    assert compared(root) == answer("lower")


def test_lines_without_an_attempt_are_ignored(root):
    events.append(
        root, RUN, journal.STEP_STARTED, {"step": BOARD, "execution": 1}, round=1
    )
    both(root)
    assert compared(root) == answer("lower")


@pytest.mark.parametrize("make", ["nothing", "run directory", "empty log"])
def test_a_missing_log_is_measurement_missing_for_measured(root, make):
    if make != "nothing":
        layout.run_dir(root, RUN).mkdir(parents=True)
    if make == "empty log":
        raw(root, b"")
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_MISSING
    assert refused.message.startswith(f"{LOG}: measured ")
    assert not layout.run_file(root, RUN, "STATE.json").exists()


def test_a_run_id_naming_no_run_is_measurement_missing(root):
    both(root)
    refused = failure(root, request(run_id="other"))
    assert refused.kind == timings_tool.KIND_MEASUREMENT_MISSING
    assert refused.message.startswith("runs/other/events.ndjson: measured ")


def test_a_torn_tail_is_no_line(root):
    both(root)
    data = {"step": BOARD, "execution": 2, "spend": {}, "result": timing()}
    raw(root, line(data)[:-9])
    assert compared(root) == answer("lower")


def test_each_call_reads_the_log_anew(root):
    definition = timings_tool.definition(Source(root))
    with pytest.raises(ToolFailure):
        definition.function(request())
    both(root)
    assert definition.function(request()) == answer("lower")


def test_the_tool_appends_nothing_and_selects_no_backend(root, monkeypatch):
    both(root)
    monkeypatch.setattr(events, "append", None)
    assert compared(root) == answer("lower")


def test_different_shapes_are_shapes_differ(root):
    run(root, MEASURED, result=timing(intervals=FAST, m=8))
    run(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_SHAPES_DIFFER
    key = "{'kind': 'gemm', 'dtype': 'fp32', 'layout': 'row_major'}"
    assert refused.message == (
        f"{LOG}: measured has the contract {key} and the shape "
        f"{{'m': 8, 'k': 4, 'n': 4}}, against {key} and the shape "
        "{'m': 4, 'k': 4, 'n': 4}"
    )


def test_equal_shapes_of_different_contracts_are_shapes_differ(root):
    run(root, MEASURED, result=timing(intervals=FAST, entry=RMSNORM, dims=(4, 8)))
    run(root, AGAINST, result=timing(entry=ADD, dims=(4, 8)))
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_SHAPES_DIFFER
    assert refused.message == (
        f"{LOG}: measured has the contract {{'kind': 'rmsnorm', 'dtype': 'bf16', "
        "'layout': 'row_major'} and the shape {'m': 4, 'n': 8}, against "
        "{'kind': 'elementwise_add', 'dtype': 'bf16', 'layout': 'row_major'} "
        "and the shape {'m': 4, 'n': 8}"
    )


def test_a_contract_key_differing_in_one_member_is_shapes_differ(root):
    other = timing()
    other["contract_key"]["dtype"] = "bf16"
    run(root, MEASURED, result=timing(intervals=FAST))
    run(root, AGAINST, result=other)
    assert failure(root).kind == timings_tool.KIND_SHAPES_DIFFER


def test_two_results_of_another_kind_with_equal_contract_and_shape_compare(root):
    run(root, MEASURED, result=timing(intervals=FAST, entry=RMSNORM, dims=(4, 8)))
    run(root, AGAINST, result=timing(entry=RMSNORM, dims=(4, 8)))
    assert compared(root) == answer("lower")


@pytest.mark.parametrize("retired", ["board_run_timing", "sim_run_timing"])
def test_lines_under_a_retired_run_value_are_not_read(root, retired):
    run(root, MEASURED, step=retired, result={"outcome": "converged"})
    run(root, AGAINST, step=retired, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_MEASUREMENT_MISSING
    both(root)
    assert compared(root) == answer("lower")


def test_samples_beyond_the_float_range_are_samples_out_of_domain(root):
    run(root, MEASURED, result=timing(intervals=[10**310] * 5))
    run(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN
    assert refused.message.startswith(f"{LOG}: the samples cannot be compared: b: ")


def test_a_refusal_of_the_rule_is_samples_out_of_domain(root, monkeypatch):
    both(root)

    def refusing(a, b):
        assert (a, b) == (SLOW, FAST)
        raise measurement.InvalidSamplesError("a, b: must be within range")

    monkeypatch.setattr(measurement, "ratio_interval", refusing)
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN
    assert refused.message.endswith("a, b: must be within range")


def infinite(member, ref=MEASURED):
    data = (
        '{"step": "board_run_timing_v2", "execution": 1, "spend": {}, "result": '
        '{"outcome": "converged", "contract_key": {"kind": "gemm", "dtype": "fp32", '
        '"layout": "row_major"}, "shape": {"m": 4, "k": 4, "n": 4}, "unit": "ns", '
        f'"intervals": {member["intervals"]}, "memory_bytes": '
        f"{member['memory_bytes']}}}}}"
    )
    envelope = (
        '{"schema_version": 1, "time": "2026-10-21T00:00:00Z", "kind": "step_ended", '
        + "".join(f'"{name}": {value}, ' for name, value in ref.items())
        + '"data": '
    )
    return (envelope + data + "}\n").encode()


def test_a_number_beyond_the_float_range_in_the_samples_is_timing_result_invalid(
    root,
):
    raw(root, infinite({"intervals": "[1, 1, 1, 1, 1e999]", "memory_bytes": 1}))
    run(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_TIMING_RESULT_INVALID
    assert "data.result.intervals" in refused.message


def test_a_number_beyond_the_float_range_in_the_shape_is_timing_result_invalid(root):
    data = line(
        {"step": BOARD, "execution": 1, "spend": {}, "result": timing(intervals=FAST)}
    ).replace(b'"m": 4', b'"m": 1e999')
    raw(root, data)
    run(root, AGAINST, result=timing())
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_TIMING_RESULT_INVALID
    assert refused.message.startswith(f"{LOG}: line 1: data.result.shape: ")


def test_a_number_beyond_the_float_range_elsewhere_changes_nothing(root):
    samples = json.dumps(FAST)
    raw(root, infinite({"intervals": samples, "memory_bytes": "1e999"}))
    run(root, AGAINST, result=timing())
    assert compared(root) == answer("lower")
    registry = default_registry(Source(root))
    assert tools.call(registry, "timings.compare", request()) == answer("lower")


# Refused requests


def changed(side, **members):
    return request(
        **{side: dict(MEASURED if side == "measured" else AGAINST) | members}
    )


REFUSED = [
    (request(extra=1), "not 'extra'"),
    *[
        (without(member), f"lacks the member {member}")
        for member in timings_tool._MEMBERS
    ],
    (request(run_id="Run"), "run_id"),
    (request(run_id=""), "run_id"),
    (request(run_id=3), "run_id"),
    (request(metric="throughput"), "metric"),
    (request(metric="Latency_minimisation"), "metric"),
    (request(metric=None), "metric"),
    (request(point="Board"), "point"),
    (request(point="BOARD"), "point"),
    (request(point="board "), "point"),
    (request(point="board_run_timing"), "point"),
    (request(point=1), "point"),
    (request(point=None), "point"),
    *[
        given
        for side in ("measured", "against")
        for given in [
            (request(**{side: [1, 1, 1]}), f"{side}: must be an object"),
            (request(**{side: None}), f"{side}: must be an object"),
            (changed(side, extra=1), f"{side}: must be an object"),
            (
                request(**{side: {"round": 0, "candidate": 1}}),
                f"{side}: must be an object",
            ),
            (changed(side, round=-1), f"{side}.round"),
            (changed(side, round=keys.MAX_INTEGER + 1), f"{side}.round"),
            (changed(side, round=True), f"{side}.round"),
            (changed(side, candidate=0), f"{side}.candidate"),
            (changed(side, candidate=1.0), f"{side}.candidate"),
            (changed(side, attempt=0), f"{side}.attempt"),
            (changed(side, attempt="1"), f"{side}.attempt"),
            (changed(side, attempt=False), f"{side}.attempt"),
            (changed(side, attempt=None), f"{side}.attempt"),
        ]
    ],
    (request(against=dict(MEASURED)), "two different attempts"),
]


@pytest.mark.parametrize(("given", "message"), REFUSED)
def test_a_refused_request_is_invalid_request_and_asks_no_source(root, given, message):
    both(root)
    before = snapshot(root)
    source = Source(root)
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(source).function(given)
    assert refused.value.kind == tools.KIND_INVALID_REQUEST
    assert message in refused.value.message
    assert source.calls == 0
    assert snapshot(root) == before


def test_a_huge_int_is_refused_without_showing_it_whole():
    given = changed("measured", round=10**5000)
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(FailingSource()).function(given)
    assert refused.value.kind == tools.KIND_INVALID_REQUEST
    assert refused.value.message.startswith("measured.round: must be an int from 0")
    assert len(refused.value.message) < 200


def test_a_value_that_cannot_be_shown_is_named_by_its_type(monkeypatch):
    def failing(value):
        raise ValueError("synthetic")

    monkeypatch.setattr(timings_tool.reprlib, "repr", failing)
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(FailingSource()).function(request(point="Board"))
    assert refused.value.kind == tools.KIND_INVALID_REQUEST
    assert refused.value.message.endswith("got str too long to show")


def test_the_largest_numbers_are_admitted(root):
    big = keys.MAX_INTEGER
    ref = {"round": big, "candidate": big, "attempt": big}
    run(root, ref, result=timing(intervals=FAST))
    run(root, AGAINST, result=timing())
    assert compared(root, request(measured=ref))["difference"] == "lower"


# The data root and the log


def test_a_failing_source_is_no_data_root():
    source = FailingSource()
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(source).function(request())
    assert refused.value.kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1


def test_a_data_root_that_is_no_directory_is_no_data_root(tmp_path):
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(Source(tmp_path / "missing")).function(request())
    assert refused.value.kind == tools.KIND_NO_DATA_ROOT
    assert not (tmp_path / "missing").exists()


def test_a_data_root_gone_since_the_source_is_run_file_missing(root, monkeypatch):
    both(root)
    real = events.read

    def removing(data_root, run_id, position=0):
        shutil.rmtree(root)
        return real(data_root, run_id, position)

    monkeypatch.setattr(events, "read", removing)
    with pytest.raises(ToolFailure) as refused:
        timings_tool.definition(Source(root)).function(request())
    assert refused.value.kind == tools.KIND_RUN_FILE_MISSING
    assert refused.value.message.startswith(f"{LOG}: is missing")


def test_a_failed_read_is_run_file_unreadable(root, monkeypatch):
    both(root)

    def denied(data_root, run_id, position=0):
        raise PermissionError(errno.EACCES, "Permission denied", "secret/path")

    monkeypatch.setattr(events, "read", denied)
    refused = failure(root)
    assert refused.kind == tools.KIND_RUN_FILE_UNREADABLE
    assert refused.message == (
        f"{LOG}: could not be read: PermissionError: Permission denied"
    )


def test_a_directory_at_the_place_of_the_log_is_run_file_invalid(root):
    layout.run_file(root, RUN, "events.ndjson").mkdir(parents=True)
    refused = failure(root)
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message == f"{LOG}: is not a regular file"


def test_a_damaged_line_is_run_file_invalid(root):
    both(root)
    raw(root, b"{not json}\n")
    refused = failure(root)
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message.startswith(f"{LOG}: line 5: is damaged")


def test_a_line_of_another_version_is_run_file_unsupported(root):
    both(root)
    raw(root, line({"anything": 1}, version=2))
    refused = failure(root)
    assert refused.kind == tools.KIND_RUN_FILE_UNSUPPORTED
    assert refused.message.startswith(f"{LOG}: line 5: ")


def test_a_broken_step_line_of_another_attempt_is_run_file_invalid(root):
    both(root)
    other = {"round": 3, "candidate": 3, "attempt": 3}
    events.append(
        root, RUN, journal.STEP_ENDED, {"step": BOARD, "execution": 1}, **other
    )
    refused = failure(root)
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message == f"{LOG}: line 5: data: lacks the member spend"


SHAPE = {"m": 4, "k": 4, "n": 4}
KEY = {"kind": "gemm", "dtype": "fp32", "layout": "row_major"}
V2 = {"intervals": SLOW, "unit": "ns", "shape": SHAPE, "contract_key": KEY}


def without(*names):
    return {
        "outcome": "converged",
        **{name: value for name, value in V2.items() if name not in names},
    }


def with_member(name, value):
    return {"outcome": "converged", **V2, name: value}


INVALID = [
    ({"no": "outcome"}, "data.result: lacks the member outcome"),
    (
        {"outcome": "Converged"},
        (
            "data.result.outcome: must be one of converged, not_converged, broken, "
            "got str 'Converged'"
        ),
    ),
    ({"outcome": None}, "data.result.outcome: must be one of"),
    (without("intervals"), "data.result: lacks the member intervals"),
    (
        {**without("shape"), "outcome": "not_converged"},
        "data.result: lacks the member shape",
    ),
    (without("unit"), "data.result: lacks the member unit"),
    (without("contract_key"), "data.result: lacks the member contract_key"),
    (
        {"outcome": "converged", "shape": SHAPE, "intervals": SLOW},
        "data.result: lacks the member unit",
    ),
    *[
        (with_member("unit", unit), "data.result.unit: ")
        for unit in ("ms", "us", "NS", "", None, 1, ["ns"])
    ],
    *[
        (with_member("contract_key", key), "data.result.contract_key: ")
        for key in (
            KEY | {"language": "c"},
            {"kind": "gemm", "dtype": "fp32"},
            {},
            KEY | {"kind": 1},
            KEY | {"layout": None},
            ["gemm", "fp32", "row_major"],
            "gemm",
        )
    ],
    *[
        (with_member("intervals", samples), "data.result.intervals: ")
        for samples in (
            SLOW[:4],
            [],
            [0, 1, 1, 1, 1],
            [1, 1, 1, 1, 5.0],
            [1, 1, 1, 1, True],
            [1, 1, 1, 1, "1"],
            {"0": 1},
            "11111",
        )
    ],
    *[
        (with_member("shape", shape), "data.result.shape: ")
        for shape in (
            {},
            SHAPE | {"x": 0},
            SHAPE | {"k": 0},
            SHAPE | {"n": 4.0},
            SHAPE | {"m": True},
            [4, 4, 4],
        )
    ],
]


@pytest.mark.parametrize(("result", "problem"), INVALID)
@pytest.mark.parametrize("side", ["measured", "against"])
def test_an_invalid_timing_result_of_a_named_side_is_timing_result_invalid(
    root, result, problem, side
):
    both(root)
    end(root, MEASURED if side == "measured" else AGAINST, 2, result=result)
    refused = failure(root)
    assert refused.kind == timings_tool.KIND_TIMING_RESULT_INVALID
    assert refused.message.startswith(f"{LOG}: line 5: {problem}")


@pytest.mark.parametrize(("result", "problem"), INVALID)
def test_timing_problem_names_what_an_invalid_result_lacks(root, result, problem):
    given = json.loads(json.dumps(result))
    named = timings_tool.timing_problem(given)
    assert named.startswith(problem)
    assert given == result
    both(root)
    end(root, MEASURED, 2, result=result)
    assert failure(root).message == f"{LOG}: line 5: {named}"


@pytest.mark.parametrize(
    "result",
    [
        timing(),
        timing("not_converged", FAST),
        broken(),
        {"outcome": "broken"},
        {"outcome": "converged", **V2, "x": None},
        {"outcome": "converged", **V2, "shape": {"m": 1}},
        {"outcome": "converged", **V2, "shape": SHAPE | {"x": 1}},
        timing(entry=RMSNORM, dims=(4, 8)),
    ],
    ids=[
        "converged",
        "not converged",
        "broken",
        "bare broken",
        "other member",
        "one shape member",
        "other shape member",
        "another kind",
    ],
)
def test_timing_problem_admits_an_admitted_result(result):
    assert timings_tool.timing_problem(result) is None


def test_a_broken_result_needs_no_samples_or_shape(root):
    both(root)
    end(root, MEASURED, 2, result={"outcome": "broken"})
    assert compared(root) == answer("lower")


@pytest.mark.parametrize(
    ("ref", "step"),
    [
        ({"round": 1, "candidate": 1, "attempt": 2}, BOARD),
        (MEASURED, SIM),
    ],
)
def test_an_invalid_result_of_an_unnamed_attempt_or_step_is_no_failure(root, ref, step):
    end(root, ref, step=step, result={"outcome": "converged", "intervals": [1]})
    both(root)
    assert compared(root) == answer("lower")


def test_a_broken_step_line_before_an_invalid_result_decides(root):
    both(root)
    events.append(
        root, RUN, journal.STEP_ENDED, {"step": BOARD, "execution": 9}, round=5
    )
    end(root, MEASURED, 2, result={"no": "outcome"})
    assert failure(root).kind == tools.KIND_RUN_FILE_INVALID


def test_an_invalid_result_before_a_broken_step_line_decides(root):
    both(root)
    end(root, MEASURED, 2, result={"no": "outcome"})
    events.append(
        root, RUN, journal.STEP_ENDED, {"step": BOARD, "execution": 9}, round=5
    )
    assert failure(root).kind == timings_tool.KIND_TIMING_RESULT_INVALID


def test_an_invalid_result_comes_before_the_measurement_rule(root):
    run(root, MEASURED, 1, result=timing())
    run(root, MEASURED, 2, result=timing())
    end(root, AGAINST, result={"outcome": "converged"})
    assert failure(root).kind == timings_tool.KIND_TIMING_RESULT_INVALID


# The shared function


SCENES = {
    "lower": lambda root: both(root),
    "not converged": lambda root: (
        run(root, MEASURED, result=timing("not_converged", FAST)),
        run(root, AGAINST, result=timing()),
    ),
    "several": lambda root: (both(root), run(root, AGAINST, 2, result=timing())),
    "unknown": lambda root: (both(root), start(root, MEASURED, 2)),
    "missing": lambda root: run(root, AGAINST, result=timing()),
    "shapes": lambda root: (
        run(root, MEASURED, result=timing(m=2)),
        run(root, AGAINST, result=timing()),
    ),
    "domain": lambda root: (
        run(root, MEASURED, result=timing(intervals=[10**310] * 5)),
        run(root, AGAINST, result=timing()),
    ),
    "invalid": lambda root: (both(root), end(root, AGAINST, 2, result={})),
    "broken step line": lambda root: (
        both(root),
        events.append(root, RUN, journal.STEP_STARTED, {"step": "B"}, round=1),
    ),
}


@pytest.mark.parametrize("name", sorted(SCENES))
def test_compare_gives_what_the_tool_gives(root, name):
    SCENES[name](root)
    lines = checks_tool.log_lines(root, RUN)
    try:
        expected = compared(root)
    except ToolFailure:
        expected = failure(root)
    try:
        got = timings_tool.compare(
            RUN, lines, "latency_minimisation", "board", MEASURED, AGAINST
        )
    except ToolFailure as e:
        assert (e.kind, e.message) == (expected.kind, expected.message)
    else:
        assert got == expected


def test_compare_over_no_line_is_measurement_missing():
    with pytest.raises(ToolFailure) as refused:
        timings_tool.compare(RUN, [], "latency_minimisation", "sim", MEASURED, AGAINST)
    assert refused.value.kind == timings_tool.KIND_MEASUREMENT_MISSING
    assert refused.value.message.startswith(f"{LOG}: measured ")


@pytest.mark.parametrize(
    ("metric", "point"),
    [("throughput", "board"), ("latency_minimisation", "Board")],
)
def test_compare_refuses_a_metric_or_point_the_request_does_not_admit(metric, point):
    with pytest.raises(ValueError, match="metric or point"):
        timings_tool.compare(RUN, [], metric, point, MEASURED, AGAINST)


# The registry


def test_the_default_registry_and_the_mcp_front_hold_the_tool(root):
    both(root)
    registry = default_registry(Source(root))
    assert "timings.compare" in registry.names()
    held = registry.definition("timings.compare")
    own = timings_tool.definition(Source(root))
    assert (held.description, held.input_schema) == (own.description, own.input_schema)
    assert mcp_front.mcp_names(registry)["timings_compare"] == "timings.compare"
    assert tools.call(registry, "timings.compare", request()) == answer("lower")


def lines_of(root):
    return checks_tool.log_lines(root, RUN)


def test_timing_lines_gives_each_admitted_attempt_its_sets(root):
    run(root, MEASURED, result=timing(intervals=SLOW))
    run(root, MEASURED, execution=2, result=broken())
    run(root, MEASURED, execution=3, failure=FAILED)
    start(root, MEASURED, execution=4)
    run(root, AGAINST, result=timing(intervals=FAST))
    run(root, MEASURED, step=SIM, result=timing(intervals=FAST))
    found = timings_tool.timing_lines(RUN, lines_of(root), "board", lambda n: n[0] == 1)
    assert list(found) == [(1, 1, 1)]
    held = found[(1, 1, 1)]
    assert [execution for execution, _ in held.entering] == [1]
    assert held.broken == [2]
    assert held.unknown == {3, 4}


def test_timing_lines_holds_only_admitted_end_lines_to_the_form(root):
    run(root, AGAINST, result={"outcome": "nonsense"})
    run(root, MEASURED, result=timing(intervals=SLOW))
    lines = lines_of(root)
    found = timings_tool.timing_lines(RUN, lines, "board", lambda n: n[0] == 1)
    assert list(found) == [(1, 1, 1)]
    with pytest.raises(ToolFailure) as e:
        timings_tool.timing_lines(RUN, lines, "board", lambda n: True)
    assert e.value.kind == timings_tool.KIND_TIMING_RESULT_INVALID


def test_timing_lines_refuses_a_damaged_step_line_of_any_attempt(root):
    raw(root, line({"step": BOARD}))
    with pytest.raises(ToolFailure) as e:
        timings_tool.timing_lines(RUN, lines_of(root), "board", lambda n: False)
    assert e.value.kind == "run_file_invalid"


def test_timing_lines_passes_over_a_step_line_that_names_no_attempt(root):
    data = {"step": BOARD, "execution": 1}
    events.append(root, RUN, journal.STEP_STARTED, data)
    assert timings_tool.timing_lines(RUN, lines_of(root), "board", lambda n: True) == {}


def test_timing_lines_refuses_another_point():
    with pytest.raises(KeyError):
        timings_tool.timing_lines(RUN, [], "elsewhere", lambda n: True)


@pytest.mark.parametrize(
    "entering, unknown, kind",
    [
        ([(1, {}), (2, {})], {3}, timings_tool.KIND_MEASUREMENT_SEVERAL),
        ([(1, {})], {3}, timings_tool.KIND_MEASUREMENT_UNKNOWN),
        ([], {3}, timings_tool.KIND_MEASUREMENT_UNKNOWN),
        ([], set(), timings_tool.KIND_MEASUREMENT_MISSING),
        ([(1, {})], set(), None),
    ],
)
def test_measurement_problem_names_the_first_that_holds(entering, unknown, kind):
    held = timings_tool.TimingLines(entering, unknown, [])
    assert timings_tool.measurement_problem(held) == kind


@pytest.mark.parametrize(
    "measured, against, difference",
    [(FAST, SLOW, "lower"), (SLOW, FAST, "higher"), (SLOW, CLOSE, "not_different")],
)
def test_difference_of_gives_the_rule_for_two_results(measured, against, difference):
    given = timings_tool.difference_of(
        "f", timing(intervals=measured), timing(intervals=against)
    )
    assert given == difference


def test_difference_of_refuses_two_shapes():
    with pytest.raises(ToolFailure) as e:
        timings_tool.difference_of("f", timing(m=2), timing(m=4))
    assert e.value.kind == timings_tool.KIND_SHAPES_DIFFER


def test_difference_of_refuses_samples_outside_the_domain():
    with pytest.raises(ToolFailure) as e:
        timings_tool.difference_of("f", timing(intervals=[10**320] * 5), timing())
    assert e.value.kind == timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN
