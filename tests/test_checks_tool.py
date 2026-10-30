import errno
import json
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    check_result,
    check_standing,
    checks_tool,
    contract_table,
    events,
    journal,
    keys,
    layout,
    mcp_front,
    tools,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
LOG = f"runs/{RUN}/events.ndjson"
SIM = "correctness_check_sim_v2"
BOARD = "correctness_check_board_v2"
RETIRED = (
    "correctness_check_sim",
    "correctness_check_board",
    "correctness_check_bf16_sim",
    "correctness_check_bf16_board",
)
RETIRED_SIM = "correctness_check_bf16_sim"
RETIRED_BOARD = "correctness_check_bf16_board"
PASS = {"outcome": "pass", "max_abs_error": 0.0}
FAIL = {"outcome": "fail", "max_abs_error": 2.5}
BROKEN = {"outcome": "broken"}
UNSTARTED = {"kind": "compiler_unavailable", "message": "no cc"}
BLOCKED = {"kind": "executable_failed", "message": "signal 9"}
KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_unreadable",
    "run_file_invalid",
    "run_file_unsupported",
    "check_result_invalid",
    "bad_result",
)
STANDING_NAMES = {
    check_standing.Standing.VERIFIED: "verified",
    check_standing.Standing.NOT_VERIFIED: "not_verified",
    check_standing.Standing.UNDETERMINED: "undetermined",
}


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


def numbers(round, candidate, attempt):
    return {"round": round, "candidate": candidate, "attempt": attempt}


def start(root, execution=1, attempt=1, step=BOARD, round=1, candidate=1):
    data = {"step": step, "execution": execution}
    events.append(
        root, RUN, journal.STEP_STARTED, data, **numbers(round, candidate, attempt)
    )


def end(root, execution=1, attempt=1, step=BOARD, round=1, candidate=1, **outcome):
    data = {"step": step, "execution": execution, "spend": {}, **outcome}
    events.append(
        root, RUN, journal.STEP_ENDED, data, **numbers(round, candidate, attempt)
    )


def check(root, execution=1, attempt=1, step=BOARD, round=1, candidate=1, **outcome):
    start(root, execution, attempt, step, round, candidate)
    end(root, execution, attempt, step, round, candidate, **outcome)


def unspent(root, attempt):
    data = {"step": BOARD, "execution": 1}
    events.append(root, RUN, journal.STEP_ENDED, data, **numbers(1, 1, attempt))


def raw(root, content):
    path = layout.run_file(root, RUN, "events.ndjson")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as f:
        f.write(content)


def line(data, kind=journal.STEP_ENDED, version=1, attempt=1, candidate=1, round=1):
    event = {"schema_version": version, "time": "2026-10-20T00:00:00Z", "kind": kind}
    event |= numbers(round, candidate, attempt)
    return (json.dumps(event | {"data": data}) + "\n").encode()


def request(attempt=None, point="board", round=1, candidate=1, run_id=RUN):
    given = {"run_id": run_id, "round": round, "candidate": candidate, "point": point}
    if attempt is not None:
        given["attempt"] = attempt
    return given


def without(member):
    return {k: v for k, v in request().items() if k != member}


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes() if p.is_file() else None
        for p in root.rglob("*")
    }


def read(root, given):
    before = snapshot(root)
    source = Source(root)
    result = checks_tool.definition(source).function(given)
    assert source.calls == 1
    assert snapshot(root) == before
    return result


def failure(root, given):
    before = snapshot(root) if root.is_dir() else None
    with pytest.raises(ToolFailure) as refused:
        checks_tool.definition(Source(root)).function(given)
    if before is not None:
        assert snapshot(root) == before
    return refused.value


def only(result):
    (entry,) = result["attempts"]
    return entry


def ended(execution=1, **outcome):
    return {"execution": execution, "state": "ended", **outcome}


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = checks_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == checks_tool.NAME == "checks.read"
    assert source.calls == 0
    number = {"type": "integer", "maximum": keys.MAX_INTEGER}
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": number | {"minimum": 0},
            "candidate": number | {"minimum": 1},
            "attempt": number | {"minimum": 1},
            "point": {"type": "string", "enum": ["sim", "board"]},
        },
        "required": ["run_id", "round", "candidate", "point"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert checks_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="must be callable"):
        checks_tool.definition(source)


def test_the_description_names_every_kind_and_what_it_tells():
    description = checks_tool.definition(lambda: None).description
    for kind in KINDS:
        assert kind in description
    for text in (
        "events.ndjson",
        "never part of the request",
        "attempt is optional",
        "without it, every attempt",
        '{"attempts": [{"attempt": n, "standing": s, "checks": [...]}]}',
        '"verified", "not_verified" or "undetermined"',
        '"state": "open"',
    ):
        assert text in description


def test_the_new_kind_is_of_the_tool_layer_and_not_reserved():
    assert checks_tool.KIND_CHECK_RESULT_INVALID == "check_result_invalid"
    assert checks_tool.KIND_CHECK_RESULT_INVALID not in tools.RESERVED_KINDS
    kinds = {name for name in vars(checks_tool) if name.startswith("KIND_")}
    assert kinds == {"KIND_CHECK_RESULT_INVALID"}


# Happy path and the walk-through rows


def test_one_pass_is_verified(root):
    check(root, step=SIM, result=PASS)
    result = read(root, request(1, "sim"))
    assert list(result) == ["attempts"]
    entry = only(result)
    assert list(entry) == ["attempt", "standing", "checks"]
    assert entry == {
        "attempt": 1,
        "standing": "verified",
        "checks": [ended(result=PASS)],
    }


def test_a_result_is_returned_as_stored(root):
    stored = {"outcome": "pass", "note": {"free": [1.5, -2, None, "x"]}, "z": True}
    check(root, result=stored)
    assert only(read(root, request(1)))["checks"] == [ended(result=stored)]


def test_fail_then_pass_is_not_verified(root):
    check(root, 1, result=FAIL)
    check(root, 2, result=PASS)
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "not_verified",
        "checks": [ended(1, result=FAIL), ended(2, result=PASS)],
    }


def test_a_broken_result_is_not_verified(root):
    check(root, result=BROKEN)
    assert only(read(root, request(1)))["standing"] == "not_verified"


def test_pass_and_open_is_undetermined_and_the_open_check_is_listed(root):
    check(root, 1, result=PASS)
    start(root, 2)
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "undetermined",
        "checks": [ended(1, result=PASS), {"execution": 2, "state": "open"}],
    }


def test_an_open_identity_stands_at_its_first_start_line(root):
    start(root, 2)
    check(root, 1, result=PASS)
    start(root, 2)
    assert only(read(root, request(1)))["checks"] == [
        {"execution": 2, "state": "open"},
        ended(1, result=PASS),
    ]


def test_two_end_lines_of_one_execution_give_two_elements(root):
    start(root, 1)
    start(root, 1)
    end(root, 1, result=PASS)
    end(root, 1, result=PASS)
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "verified",
        "checks": [ended(1, result=PASS), ended(1, result=PASS)],
    }


def test_an_end_line_without_a_start_line_gives_one_element(root):
    end(root, 3, result=FAIL)
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "not_verified",
        "checks": [ended(3, result=FAIL)],
    }


def test_an_unstarted_failure_alone_is_undetermined(root):
    check(root, failure=UNSTARTED)
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "undetermined",
        "checks": [ended(failure=UNSTARTED)],
    }


def test_a_failure_of_class_two_beside_a_pass_is_undetermined(root):
    check(root, 1, result=PASS)
    check(root, 2, failure=BLOCKED)
    entry = only(read(root, request(1)))
    assert entry["standing"] == "undetermined"
    assert entry["checks"] == [ended(1, result=PASS), ended(2, failure=BLOCKED)]


def test_without_attempt_every_checked_attempt_comes_in_ascending_order(root):
    check(root, attempt=3, result=FAIL)
    check(root, attempt=1, result=PASS)
    check(root, attempt=2, step=SIM, result=PASS)
    start(root, attempt=5)
    assert read(root, request()) == {
        "attempts": [
            {"attempt": 1, "standing": "verified", "checks": [ended(result=PASS)]},
            {"attempt": 3, "standing": "not_verified", "checks": [ended(result=FAIL)]},
            {
                "attempt": 5,
                "standing": "undetermined",
                "checks": [{"execution": 1, "state": "open"}],
            },
        ]
    }
    assert [e["attempt"] for e in read(root, request(point="sim"))["attempts"]] == [2]


def test_round_zero_is_read(root):
    check(root, round=0, result=PASS)
    check(root, round=1, result=FAIL)
    assert read(root, request(round=0)) == {
        "attempts": [
            {"attempt": 1, "standing": "verified", "checks": [ended(result=PASS)]}
        ]
    }


def test_lines_of_the_other_point_other_candidates_rounds_and_kinds_are_ignored(root):
    check(root, step=SIM, result=FAIL)
    check(root, candidate=2, result=FAIL)
    check(root, round=2, result=FAIL)
    check(root, attempt=2, result=FAIL)
    events.append(root, RUN, "round_started", {"note": 1}, round=1)
    data = {"step": BOARD, "execution": 1}
    events.append(root, RUN, journal.STEP_STARTED, data, round=1, candidate=1)
    check(root, step="other_step", result={"no": "outcome"})
    check(root, result=PASS)
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "verified",
        "checks": [ended(result=PASS)],
    }


def test_with_attempt_and_no_line_of_it_the_entry_is_empty_and_undetermined(root):
    check(root, attempt=2, result=PASS)
    assert read(root, request(1)) == {
        "attempts": [{"attempt": 1, "standing": "undetermined", "checks": []}]
    }


@pytest.mark.parametrize("make", ["nothing", "run directory", "empty log"])
def test_a_missing_log_holds_no_check(root, make):
    if make != "nothing":
        layout.run_dir(root, RUN).mkdir(parents=True)
    if make == "empty log":
        raw(root, b"")
    assert read(root, request()) == {"attempts": []}
    assert read(root, request(4)) == {
        "attempts": [{"attempt": 4, "standing": "undetermined", "checks": []}]
    }
    assert not layout.run_file(root, RUN, "STATE.json").exists()


def test_a_run_id_naming_no_run_is_answered_like_an_empty_log(root):
    check(root, result=PASS)
    assert read(root, request(run_id="other")) == {"attempts": []}


def test_a_log_gone_between_its_look_and_its_read_holds_no_check(root, monkeypatch):
    def vanished(data_root, run_id, position=0):
        raise FileNotFoundError(errno.ENOENT, "gone")

    monkeypatch.setattr(events, "read", vanished)
    assert read(root, request()) == {"attempts": []}


def test_a_torn_tail_is_no_line(root):
    check(root, 1, result=PASS)
    raw(root, line({"step": BOARD, "execution": 2, "spend": {}, "result": FAIL})[:-9])
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "verified",
        "checks": [ended(1, result=PASS)],
    }


def test_each_call_reads_the_log_anew(root):
    definition = checks_tool.definition(Source(root))
    assert definition.function(request()) == {"attempts": []}
    check(root, result=PASS)
    assert definition.function(request()) == {
        "attempts": [
            {"attempt": 1, "standing": "verified", "checks": [ended(result=PASS)]}
        ]
    }


def test_the_tool_appends_nothing_and_selects_no_backend(root, monkeypatch):
    check(root, result=PASS)
    monkeypatch.setattr(events, "append", None)
    assert only(read(root, request(1)))["standing"] == "verified"


SCENARIOS = {
    "pass": [("check", 1, {"result": PASS})],
    "fail then pass": [("check", 1, {"result": FAIL}), ("check", 2, {"result": PASS})],
    "pass and open": [("check", 1, {"result": PASS}), ("start", 2, {})],
    "two end lines": [
        ("start", 1, {}),
        ("end", 1, {"result": PASS}),
        ("end", 1, {"result": PASS}),
    ],
    "unstarted failure": [("check", 1, {"failure": UNSTARTED})],
    "class two failure": [
        ("check", 1, {"result": PASS}),
        ("check", 2, {"failure": BLOCKED}),
    ],
    "broken": [("check", 1, {"result": BROKEN})],
    "open only": [("start", 1, {})],
    "no line": [],
}


@pytest.mark.parametrize("name", sorted(SCENARIOS))
def test_the_standing_agrees_with_check_standing(root, name):
    writers = {"check": check, "start": start, "end": end}
    for writer, execution, outcome in SCENARIOS[name]:
        writers[writer](root, execution, **outcome)
    lines = events.read(root, RUN).events
    expected = check_standing.standing(lines, BOARD, 1, 1, 1)
    assert only(read(root, request(1)))["standing"] == STANDING_NAMES[expected]


def infinite(attempt):
    data = (
        '{"step": "correctness_check_board_v2", "execution": 1, "spend": {}, '
        '"result": {"outcome": "pass", "e": 1e999}}'
    )
    envelope = (
        '{"schema_version": 1, "time": "2026-10-20T00:00:00Z", "kind": "step_ended", '
        f'"round": 1, "candidate": 1, "attempt": {attempt}, "data": '
    )
    return (envelope + data + "}\n").encode()


def test_a_number_beyond_the_float_range_is_bad_result(root):
    raw(root, infinite(1))
    result = read(root, request(1))
    assert only(result)["checks"][0]["result"]["e"] == float("inf")
    registry = default_registry(Source(root))
    with pytest.raises(ToolFailure) as refused:
        tools.call(registry, "checks.read", request(1))
    assert refused.value.kind == tools.KIND_BAD_RESULT


def test_a_number_beyond_the_float_range_outside_the_result_does_nothing(root):
    raw(root, infinite(2))
    check(root, result=PASS)
    registry = default_registry(Source(root))
    assert tools.call(registry, "checks.read", request(1)) == {
        "attempts": [
            {"attempt": 1, "standing": "verified", "checks": [ended(result=PASS)]}
        ]
    }


# Refused requests


@pytest.mark.parametrize(
    ("given", "message"),
    [
        (request() | {"execution": 1}, "not 'execution'"),
        (request() | {"Point": "sim"}, "not 'Point'"),
        (without("run_id"), "lacks the member run_id"),
        (without("round"), "lacks the member round"),
        (without("candidate"), "lacks the member candidate"),
        (without("point"), "lacks the member point"),
        ({"run_id": RUN, "attempt": 1, "round": 1, "point": "sim"}, "candidate"),
        (request(run_id="Run"), "run_id"),
        (request(run_id=""), "run_id"),
        (request(run_id=3), "run_id"),
        (request(round=-1), "round: must be an int from 0"),
        (request(round=keys.MAX_INTEGER + 1), "round"),
        (request(round=True), "round"),
        (request(round=1.0), "round"),
        (request(round="1"), "round"),
        (request(candidate=0), "candidate: must be an int from 1"),
        (request(candidate=-1), "candidate"),
        (request(candidate=keys.MAX_INTEGER + 1), "candidate"),
        (request(candidate=True), "candidate"),
        (request(candidate=1.0), "candidate"),
        (request(candidate="1"), "candidate"),
        (request(attempt=0), "attempt: must be an int from 1"),
        (request(attempt=-1), "attempt"),
        (request(attempt=keys.MAX_INTEGER + 1), "attempt"),
        (request(attempt=True), "attempt"),
        (request(attempt=1.0), "attempt"),
        (request(attempt="1"), "attempt"),
        (request() | {"attempt": None}, "attempt"),
        (request(point="Sim"), "point"),
        (request(point="BOARD"), "point"),
        (request(point="sim "), "point"),
        (request(point="correctness_check_sim"), "point"),
        (request(point=1), "point"),
        (request(point=None), "point"),
    ],
)
def test_a_refused_request_is_invalid_request_and_asks_no_source(root, given, message):
    check(root, result=PASS)
    before = snapshot(root)
    source = Source(root)
    with pytest.raises(ToolFailure) as refused:
        checks_tool.definition(source).function(given)
    assert refused.value.kind == tools.KIND_INVALID_REQUEST
    assert message in refused.value.message
    assert source.calls == 0
    assert snapshot(root) == before


def test_a_huge_int_is_refused_without_showing_it_whole():
    with pytest.raises(ToolFailure) as refused:
        checks_tool.definition(FailingSource()).function(request(round=10**5000))
    assert refused.value.kind == tools.KIND_INVALID_REQUEST
    assert refused.value.message.startswith("round: must be an int from 0")
    assert len(refused.value.message) < 200


def test_the_largest_numbers_are_admitted(root):
    big = keys.MAX_INTEGER
    check(root, attempt=big, round=big, candidate=big, result=PASS)
    assert read(root, request(big, round=big, candidate=big)) == {
        "attempts": [
            {"attempt": big, "standing": "verified", "checks": [ended(result=PASS)]}
        ]
    }


# The data root and the log


def test_a_failing_source_is_no_data_root():
    source = FailingSource()
    with pytest.raises(ToolFailure) as refused:
        checks_tool.definition(source).function(request())
    assert refused.value.kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1


def test_a_data_root_that_is_no_directory_is_no_data_root(tmp_path):
    with pytest.raises(ToolFailure) as refused:
        checks_tool.definition(Source(tmp_path / "missing")).function(request())
    assert refused.value.kind == tools.KIND_NO_DATA_ROOT
    assert not (tmp_path / "missing").exists()


def test_a_data_root_gone_since_the_source_is_run_file_missing(root, monkeypatch):
    check(root, result=PASS)
    real = events.read

    def removing(data_root, run_id, position=0):
        shutil.rmtree(root)
        return real(data_root, run_id, position)

    monkeypatch.setattr(events, "read", removing)
    with pytest.raises(ToolFailure) as refused:
        checks_tool.definition(Source(root)).function(request())
    assert refused.value.kind == tools.KIND_RUN_FILE_MISSING
    assert refused.value.message == (
        f"{LOG}: is missing: the data root is not an existing directory"
    )


def test_a_failed_read_is_run_file_unreadable(root, monkeypatch):
    check(root, result=PASS)

    def denied(data_root, run_id, position=0):
        raise PermissionError(errno.EACCES, "Permission denied", "secret/path")

    monkeypatch.setattr(events, "read", denied)
    refused = failure(root, request())
    assert refused.kind == tools.KIND_RUN_FILE_UNREADABLE
    assert refused.message == (
        f"{LOG}: could not be read: PermissionError: Permission denied"
    )


def test_a_directory_at_the_place_of_the_log_is_run_file_invalid(root):
    layout.run_file(root, RUN, "events.ndjson").mkdir(parents=True)
    refused = failure(root, request())
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message == f"{LOG}: is not a regular file"


@pytest.mark.parametrize("where", ["first", "last"])
def test_a_damaged_line_anywhere_is_run_file_invalid(root, where):
    if where == "first":
        raw(root, b"{not json}\n")
    check(root, result=PASS)
    check(root, candidate=2, result={"no": "outcome"})
    if where == "last":
        raw(root, b"\xff\n")
    refused = failure(root, request(1))
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    number = 1 if where == "first" else 5
    assert refused.message.startswith(f"{LOG}: line {number}: is damaged")


def test_a_damaged_line_after_a_bad_result_in_scope_is_run_file_invalid(root):
    check(root, result={"no": "outcome"})
    raw(root, b"[]\n")
    assert failure(root, request(1)).kind == tools.KIND_RUN_FILE_INVALID


def test_a_line_of_another_version_is_run_file_unsupported(root):
    check(root, result=PASS)
    raw(root, line({"anything": 1}, version=2))
    refused = failure(root, request(1))
    assert refused.kind == tools.KIND_RUN_FILE_UNSUPPORTED
    assert refused.message.startswith(f"{LOG}: line 3: ")


def test_a_broken_step_line_of_another_attempt_is_run_file_invalid(root):
    check(root, result=PASS)
    unspent(root, 2)
    refused = failure(root, request(1))
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message == f"{LOG}: line 3: data: lacks the member spend"


def test_a_broken_step_line_of_another_step_is_run_file_invalid(root):
    events.append(root, RUN, journal.STEP_STARTED, {"step": "Bad"}, round=4)
    assert failure(root, request()).kind == tools.KIND_RUN_FILE_INVALID


@pytest.mark.parametrize(
    ("result", "problem"),
    [
        ({"no": "outcome"}, "data.result: lacks the member outcome"),
        (
            {"outcome": "PASS"},
            "data.result.outcome: must be one of pass, fail, broken, got str 'PASS'",
        ),
        (
            {"outcome": 1},
            "data.result.outcome: must be one of pass, fail, broken, got int 1",
        ),
        (
            {"outcome": None},
            "data.result.outcome: must be one of pass, fail, broken, got NoneType None",
        ),
    ],
)
@pytest.mark.parametrize("attempt", [1, None])
def test_a_bad_result_in_scope_is_check_result_invalid(root, result, problem, attempt):
    check(root, 1, result=PASS)
    check(root, 2, result=result)
    refused = failure(root, request(attempt))
    assert refused.kind == checks_tool.KIND_CHECK_RESULT_INVALID
    assert refused.message == f"{LOG}: line 4: {problem}"


def test_a_bad_result_of_another_attempt_is_in_scope_without_attempt(root):
    check(root, attempt=2, result={"no": "outcome"})
    check(root, attempt=1, result=PASS)
    assert only(read(root, request(1)))["standing"] == "verified"
    assert failure(root, request()).kind == checks_tool.KIND_CHECK_RESULT_INVALID


@pytest.mark.parametrize(
    "where",
    [{"step": SIM}, {"candidate": 2}, {"round": 2}],
)
def test_a_bad_result_out_of_scope_is_no_failure(root, where):
    check(root, result={"no": "outcome"}, **where)
    check(root, result=PASS)
    assert only(read(root, request(1)))["standing"] == "verified"
    assert [e["attempt"] for e in read(root, request())["attempts"]] == [1]


def test_a_broken_step_line_before_a_bad_result_out_of_scope_decides(root):
    unspent(root, 3)
    check(root, attempt=2, result={"no": "outcome"})
    assert failure(root, request(1)).kind == tools.KIND_RUN_FILE_INVALID


def test_the_first_failing_step_line_in_line_order_decides(root):
    check(root, attempt=2, result={"no": "outcome"})
    unspent(root, 3)
    assert failure(root, request()).kind == checks_tool.KIND_CHECK_RESULT_INVALID
    assert failure(root, request(1)).kind == tools.KIND_RUN_FILE_INVALID


# The shared read: log_lines and checks_of


def test_the_shared_names_are_the_log_and_the_steps_of_the_points():
    assert checks_tool.LOG == "events.ndjson"
    assert f"runs/{RUN}/{checks_tool.LOG}" == LOG
    assert check_standing.STEPS_OF == {"sim": (SIM,), "board": (BOARD,)}
    assert not hasattr(checks_tool, "STEP_OF")


def test_log_lines_returns_every_complete_line_in_order(root):
    check(root, result=PASS)
    raw(root, b'{"torn')
    lines = checks_tool.log_lines(root, RUN)
    assert [event["kind"] for event in lines] == [
        journal.STEP_STARTED,
        journal.STEP_ENDED,
    ]
    assert lines == events.read(root, RUN).events


@pytest.mark.parametrize("make", [False, True], ids=["no run", "run directory"])
def test_log_lines_of_a_missing_log_is_empty(root, make):
    if make:
        layout.run_file(root, RUN, "events.ndjson").parent.mkdir(parents=True)
    assert checks_tool.log_lines(root, RUN) == []


def test_log_lines_answers_a_damaged_line_with_run_file_invalid(root):
    check(root, result=PASS)
    raw(root, b"[]\n")
    with pytest.raises(ToolFailure) as refused:
        checks_tool.log_lines(root, RUN)
    assert refused.value.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.value.message.startswith(f"{LOG}: line 3: ")


def test_log_lines_answers_a_vanished_data_root_with_run_file_missing(tmp_path):
    with pytest.raises(ToolFailure) as refused:
        checks_tool.log_lines(tmp_path / "gone", RUN)
    assert refused.value.kind == tools.KIND_RUN_FILE_MISSING


def test_checks_of_groups_the_admitted_checks_by_step_and_attempt(root):
    check(root, 1, result=FAIL)
    start(root, 2)
    check(root, step=SIM, result=PASS)
    check(root, attempt=2, failure=UNSTARTED)
    check(root, candidate=2, result=PASS)
    events.append(root, RUN, journal.STEP_STARTED, {"step": "build", "execution": 1})
    asked = []

    def inside(key):
        asked.append(key)
        return key[2] == 1

    found = checks_tool.checks_of(RUN, checks_tool.log_lines(root, RUN), inside)
    assert found == {
        (BOARD, 1, 1, 1): [ended(1, result=FAIL), {"execution": 2, "state": "open"}],
        (SIM, 1, 1, 1): [ended(1, result=PASS)],
        (BOARD, 1, 1, 2): [ended(1, failure=UNSTARTED)],
    }
    assert (BOARD, 1, 2, 1) in asked
    assert all(key[3] is not None for key in asked)


def test_checks_of_refuses_only_an_admitted_bad_result(root):
    check(root, attempt=2, result={"no": "outcome"})
    check(root, result=PASS)
    lines = checks_tool.log_lines(root, RUN)
    found = checks_tool.checks_of(RUN, lines, lambda key: key[3] == 1)
    assert found == {(BOARD, 1, 1, 1): [ended(result=PASS)]}
    with pytest.raises(ToolFailure) as refused:
        checks_tool.checks_of(RUN, lines, lambda key: True)
    assert refused.value.kind == checks_tool.KIND_CHECK_RESULT_INVALID
    assert refused.value.message == (
        f"{LOG}: line 2: data.result: lacks the member outcome"
    )


def test_checks_of_refuses_a_broken_step_line_whatever_it_admits(root):
    unspent(root, 3)
    lines = checks_tool.log_lines(root, RUN)
    with pytest.raises(ToolFailure) as refused:
        checks_tool.checks_of(RUN, lines, lambda key: False)
    assert refused.value.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.value.message == f"{LOG}: line 1: data: lacks the member spend"


DIMS_OF = {
    "gemm": (4, 2, 8),
    "rope": (2, 3, 8),
    "sdpa_kv_cache": (2, 3, 4, 2, 8),
}
BF16_ENTRIES = {
    key[0]: entry for key, entry in contract_table.TABLE.items() if key[1] == "bf16"
}


def bf16(kind="rmsnorm", failed=0):
    entry = BF16_ENTRIES[kind]
    dims = DIMS_OF.get(kind, (2, 8))
    names = check_result.output_operands(entry, dims)
    exact = check_result.BIT_EXACT.get((kind, "bf16", "row_major"), ())
    counts = {name: [0 if name in exact else (failed, 0)] for name in names}
    if exact:
        counts["out"] = [(failed, 0)]
    return check_result.v2_completed(
        entry, dims, draws=1, rtol=0.01, atol=0.001, counts=counts
    )


def bf16_broken(condition="build_exit_status"):
    return check_result.v2_broken(
        condition, BF16_ENTRIES["swiglu"], (2, 8), draws=1, rtol=0.01, atol=0.001
    )


@pytest.mark.parametrize(("point", "step"), [("sim", SIM), ("board", BOARD)])
@pytest.mark.parametrize("kind", list(BF16_ENTRIES))
def test_a_v2_bf16_run_is_read_as_an_fp32_run_is(root, point, step, kind):
    check(root, 1, step=step, result=bf16(kind, failed=1))
    check(root, 2, step=step, result=bf16(kind))
    check(root, 1, attempt=2, step=step, result=bf16(kind))
    expected = [
        {
            "attempt": 1,
            "standing": "not_verified",
            "checks": [ended(1, result=bf16(kind, 1)), ended(2, result=bf16(kind))],
        },
        {"attempt": 2, "standing": "verified", "checks": [ended(result=bf16(kind))]},
    ]
    assert read(root, request(point=point)) == {"attempts": expected}
    assert read(root, request(2, point)) == {"attempts": expected[1:]}
    other = "board" if point == "sim" else "sim"
    assert read(root, request(point=other)) == {"attempts": []}


def test_v2_lines_pass_fail_and_broken_of_each_point(root):
    check(root, 1, step=SIM, result=bf16())
    check(root, 1, attempt=2, step=SIM, result=bf16(failed=1))
    check(root, 1, attempt=3, step=SIM, result=bf16_broken())
    check(root, 1, step=BOARD, result=bf16())
    assert read(root, request(point="sim")) == {
        "attempts": [
            {"attempt": 1, "standing": "verified", "checks": [ended(result=bf16())]},
            {
                "attempt": 2,
                "standing": "not_verified",
                "checks": [ended(result=bf16(failed=1))],
            },
            {
                "attempt": 3,
                "standing": "not_verified",
                "checks": [ended(result=bf16_broken())],
            },
        ]
    }
    assert only(read(root, request(1)))["standing"] == "verified"


def test_an_fp32_run_is_read_beside_a_bf16_run(root):
    check(root, result=PASS)
    check(root, attempt=2, step=BOARD, result=bf16())
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "verified",
        "checks": [ended(result=PASS)],
    }
    assert [e["attempt"] for e in read(root, request())["attempts"]] == [1, 2]


def test_an_open_bf16_identity_is_listed_and_undetermined(root):
    check(root, 1, step=SIM, result=bf16())
    start(root, 2, step=SIM)
    assert only(read(root, request(1, "sim"))) == {
        "attempt": 1,
        "standing": "undetermined",
        "checks": [ended(1, result=bf16()), {"execution": 2, "state": "open"}],
    }


def test_the_lines_of_a_retired_value_are_neither_read_nor_refused(root):
    check(root, 1, result=PASS)
    start(root, 1, step=RETIRED_BOARD)
    end(root, 1, step=RETIRED_BOARD, result=bf16_broken())
    start(root, 2, step=RETIRED_BOARD)
    check(root, 3, step=RETIRED_BOARD, result={"no": "outcome"})
    check(root, 1, step=RETIRED_SIM, result=bf16(failed=1))
    assert only(read(root, request(1))) == {
        "attempt": 1,
        "standing": "verified",
        "checks": [ended(1, result=PASS)],
    }
    assert read(root, request(point="sim")) == {"attempts": []}


@pytest.mark.parametrize("step", RETIRED)
@pytest.mark.parametrize("point", ["sim", "board"])
def test_a_log_of_retired_lines_only_reads_no_check(root, step, point):
    check(root, 1, step=step, result=PASS)
    check(root, 2, step=step, result=FAIL)
    check(root, 1, attempt=2, step=step, result={"outcome": "passed"})
    start(root, 1, attempt=3, step=step)
    assert read(root, request(point=point)) == {"attempts": []}
    assert only(read(root, request(1, point))) == {
        "attempt": 1,
        "standing": "undetermined",
        "checks": [],
    }


def test_a_damaged_bf16_end_line_is_run_file_invalid(root):
    check(root, step=BOARD, result=bf16())
    raw(root, line({"step": BOARD, "execution": 2, "result": bf16()}))
    refused = failure(root, request(1))
    assert refused.kind == tools.KIND_RUN_FILE_INVALID
    assert refused.message == f"{LOG}: line 3: data: lacks the member spend"


@pytest.mark.parametrize("attempt", [1, None])
def test_a_bf16_result_without_an_outcome_is_check_result_invalid(root, attempt):
    check(root, 1, step=SIM, result=bf16())
    check(root, 2, step=SIM, result=bf16() | {"outcome": "passed"})
    refused = failure(root, request(attempt, "sim"))
    assert refused.kind == checks_tool.KIND_CHECK_RESULT_INVALID
    assert refused.message == (
        f"{LOG}: line 4: data.result.outcome: must be one of pass, fail, broken, "
        "got str 'passed'"
    )
    assert only(read(root, request(1, "board")))["checks"] == []


@pytest.mark.parametrize("point", [SIM, BOARD, *RETIRED, "bf16_sim", "bf16"])
def test_a_point_that_is_a_step_value_is_invalid_request(root, point):
    check(root, step=SIM, result=bf16())
    refused = failure(root, request(1, point))
    assert refused.kind == tools.KIND_INVALID_REQUEST
    assert refused.message == 'point: must be "sim" or "board"'


def test_checks_in_order_keeps_the_order_of_the_lines_across_steps(root):
    check(root, 1, result=PASS)
    start(root, 2, step=RETIRED_BOARD)
    check(root, 1, step=RETIRED_BOARD, result=bf16())
    check(root, 1, step=SIM, result=PASS)
    end(root, 2, step=RETIRED_BOARD, failure=UNSTARTED)
    lines = checks_tool.log_lines(root, RUN)

    def inside(key):
        return key[0] != SIM

    assert checks_tool.checks_in_order(RUN, lines, inside) == [
        ((BOARD, 1, 1, 1), ended(1, result=PASS)),
        ((RETIRED_BOARD, 1, 1, 1), ended(1, result=bf16())),
        ((RETIRED_BOARD, 1, 1, 1), ended(2, failure=UNSTARTED)),
    ]
    grouped = {}
    for key, element in checks_tool.checks_in_order(RUN, lines, lambda key: True):
        grouped.setdefault(key, []).append(element)
    assert grouped == checks_tool.checks_of(RUN, lines, lambda key: True)


def test_checks_in_order_raises_as_checks_of_does(root):
    check(root, step=RETIRED_SIM, result={"no": "outcome"})
    unspent(root, 2)
    lines = checks_tool.log_lines(root, RUN)
    with pytest.raises(ToolFailure) as refused:
        checks_tool.checks_in_order(RUN, lines, lambda key: True)
    assert refused.value.kind == checks_tool.KIND_CHECK_RESULT_INVALID
    with pytest.raises(ToolFailure) as refused:
        checks_tool.checks_in_order(RUN, lines, lambda key: False)
    assert refused.value.kind == tools.KIND_RUN_FILE_INVALID


# The registry


def test_the_default_registry_and_the_mcp_front_hold_the_tool(root):
    check(root, result=PASS)
    registry = default_registry(Source(root))
    assert "checks.read" in registry.names()
    held = registry.definition("checks.read")
    own = checks_tool.definition(Source(root))
    assert (held.description, held.input_schema) == (own.description, own.input_schema)
    assert mcp_front.mcp_names(registry)["checks_read"] == "checks.read"
    assert tools.call(registry, "checks.read", request()) == {
        "attempts": [
            {"attempt": 1, "standing": "verified", "checks": [ended(result=PASS)]}
        ]
    }
