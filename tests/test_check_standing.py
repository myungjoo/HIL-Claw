import copy
import itertools

import pytest

from hilclaw import (
    check_failure,
    check_operation,
    check_standing,
    events,
    journal,
    keys,
)
from hilclaw.check_identity import STEP_BOARD, STEP_SIM, STEPS
from hilclaw.check_result import BROKEN, CONDITIONS, FAIL, PASS
from hilclaw.check_standing import UNSTARTED_KINDS, Standing, standing
from hilclaw.journal import STEP_ENDED, STEP_STARTED, JournalError

# Synthetic lines only: no file, no tool call, no process.
TIME = "2026-01-01T00:00:00Z"
TARGET = {"round": 3, "candidate": 2, "attempt": 1}
ARGS = (3, 2, 1)

NOT_VERIFIED, VERIFIED, UNDETERMINED = (
    Standing.NOT_VERIFIED,
    Standing.VERIFIED,
    Standing.UNDETERMINED,
)

CLASS_II = (
    "build_log_unwritable",
    check_operation.KIND_OPERATION_ANSWER_INVALID,
    check_failure.KIND_OPERATION_FAILURE_INVALID,
    check_failure.KIND_SETTINGS_REFUSED,
    "example_unknown_kind",
)
CLASS_I = (
    "no_kernel_source",
    "kernel_source_unreadable",
    "build_directory_unusable",
    "build_input_missing",
    "compiler_unavailable",
    "build_output_missing",
    "executable_unstartable",
)


def ev(kind, data, numbers=TARGET):
    return {"schema_version": 1, "time": TIME, "kind": kind, **numbers, "data": data}


def start(execution=1, step=STEP_SIM, numbers=TARGET):
    return ev(STEP_STARTED, {"step": step, "execution": execution}, numbers)


def end(
    execution=1, outcome=PASS, step=STEP_SIM, numbers=TARGET, failure=None, result=None
):
    data = {"step": step, "execution": execution, "spend": {}}
    if failure is not None:
        data["failure"] = {"kind": failure, "message": "no outcome"}
    elif result is not None:
        data["result"] = result
    else:
        data["result"] = {"outcome": outcome} | (
            {"condition": "exit_status"} if outcome == BROKEN else {}
        )
    return ev(STEP_ENDED, data, numbers)


def ended(execution=1, outcome=PASS, **kwargs):
    return [start(execution, **kwargs), end(execution, outcome, **kwargs)]


def broken(execution, condition, **kwargs):
    result = {"outcome": BROKEN, "condition": condition}
    return [start(execution, **kwargs), end(execution, result=result, **kwargs)]


def failed(execution, kind, **kwargs):
    return [start(execution, **kwargs), end(execution, failure=kind, **kwargs)]


def at(lines, step=STEP_SIM, numbers=ARGS):
    return standing(lines, step, *numbers)


def every_order(lines):
    results = {at(list(order)) for order in itertools.permutations(lines)}
    assert len(results) == 1
    return results.pop()


WALK_THROUGH = [
    ([], UNDETERMINED),
    (ended(1, PASS), VERIFIED),
    (ended(1, FAIL) + ended(2, PASS), NOT_VERIFIED),
    (ended(1, PASS) + ended(2, FAIL), NOT_VERIFIED),
    (broken(1, "exit_status") + ended(2, PASS), NOT_VERIFIED),
    (failed(1, "operation_failure_invalid"), UNDETERMINED),
    (failed(1, "compiler_unavailable") + ended(2, PASS), VERIFIED),
    (failed(1, "build_log_unwritable") + ended(2, PASS), UNDETERMINED),
    (broken(1, "build_exit_status") + ended(2, PASS), NOT_VERIFIED),
    (ended(1, PASS) + [start(2)], UNDETERMINED),
    ([start(1)] + ended(2, FAIL), NOT_VERIFIED),
]


@pytest.mark.parametrize(("lines", "expected"), WALK_THROUGH)
def test_walk_through_rows_in_every_order(lines, expected):
    assert every_order(lines) is expected


def test_walk_through_two_points():
    sim = ended(1, PASS)
    board = ended(1, FAIL, step=STEP_BOARD)
    lines = sim + board
    assert at(lines, STEP_SIM) is VERIFIED
    assert at(lines, STEP_BOARD) is NOT_VERIFIED
    assert at(sim, STEP_SIM) is at(lines, STEP_SIM)
    assert at(board, STEP_BOARD) is at(lines, STEP_BOARD)
    assert at(sim + [start(2, step=STEP_BOARD)], STEP_SIM) is VERIFIED
    assert at(ended(1, FAIL) + ended(1, PASS, step=STEP_BOARD), STEP_BOARD) is VERIFIED


def test_walk_through_repaired_attempt():
    repaired = {"round": 3, "candidate": 2, "attempt": 2}
    lines = ended(1, FAIL) + ended(1, PASS, numbers=repaired)
    assert at(lines, numbers=(3, 2, 1)) is NOT_VERIFIED
    assert at(lines, numbers=(3, 2, 2)) is VERIFIED


@pytest.mark.parametrize("kind", CLASS_II)
def test_class_ii_kind_blocks_verified_and_not_a_fail(kind):
    assert kind not in UNSTARTED_KINDS
    assert at(failed(1, kind) + ended(2, PASS)) is UNDETERMINED
    assert at(failed(1, kind) + ended(2, FAIL)) is NOT_VERIFIED
    assert at(failed(1, kind)) is UNDETERMINED


@pytest.mark.parametrize("kind", CLASS_I)
def test_class_i_kind_counts_neither_way(kind):
    assert kind in UNSTARTED_KINDS
    assert at(failed(1, kind) + ended(2, PASS)) is VERIFIED
    assert at(failed(1, kind)) is UNDETERMINED
    assert at(failed(1, kind) + ended(2, FAIL)) is NOT_VERIFIED


def test_only_failures_are_undetermined():
    assert at(failed(1, CLASS_I[0]) + failed(2, CLASS_I[1])) is UNDETERMINED


@pytest.mark.parametrize("condition", CONDITIONS)
def test_every_condition_is_not_verified(condition):
    assert at(broken(1, condition)) is NOT_VERIFIED
    assert at(broken(1, condition) + ended(2, PASS)) is NOT_VERIFIED
    assert at(ended(1, PASS) + broken(2, condition)) is NOT_VERIFIED


def test_fail_stands_beside_open_identity_and_class_ii_failure():
    lines = [start(1), end(2, failure=CLASS_II[0]), end(3, PASS), end(4, FAIL)]
    assert every_order(lines) is NOT_VERIFIED


def test_end_line_without_start_line_counts():
    assert at([end(1, PASS)]) is VERIFIED
    assert at([end(1, FAIL)]) is NOT_VERIFIED
    assert at(ended(1, PASS) + [end(2, BROKEN)]) is NOT_VERIFIED
    assert at([end(1, failure=CLASS_II[0]), end(2, PASS)]) is UNDETERMINED


def test_doubled_end_line_both_count():
    assert every_order([start(1), end(1, PASS), end(1, FAIL)]) is NOT_VERIFIED
    assert at([start(1), end(1, PASS), end(1, PASS)]) is VERIFIED


def test_start_after_end_of_same_identity_is_not_open():
    assert at([end(1, PASS), start(1)]) is VERIFIED


def test_open_identity_only_is_undetermined():
    assert at([start(1)]) is UNDETERMINED
    assert at([start(1), start(2)] + [end(1, PASS)]) is UNDETERMINED


def test_lines_that_do_not_match_are_ignored():
    other_kind = ev("example_kind", {"step": STEP_SIM, "outcome": FAIL})
    unnumbered = {
        "schema_version": 1,
        "time": TIME,
        "kind": STEP_ENDED,
        "data": end(1, FAIL)["data"],
    }
    no_attempt = ev(STEP_ENDED, end(1, FAIL)["data"], {"round": 3, "candidate": 2})
    lines = [
        other_kind,
        unnumbered,
        no_attempt,
        ev(STEP_STARTED, start(2)["data"], {"round": 3, "candidate": 2}),
        *ended(1, FAIL, step="example_step"),
        *ended(1, FAIL, step=STEP_BOARD),
        *ended(1, FAIL, numbers={"round": 4, "candidate": 2, "attempt": 1}),
        *ended(1, FAIL, numbers={"round": 3, "candidate": 1, "attempt": 1}),
        *ended(1, FAIL, numbers={"round": 3, "candidate": 2, "attempt": 2}),
        start(3, step=STEP_BOARD),
    ]
    assert at(lines) is UNDETERMINED
    assert at(lines + ended(2, PASS)) is VERIFIED


def test_unmatched_end_line_result_is_not_read():
    lines = [end(1, result={"example_member": 1}, step=STEP_BOARD)] + ended(2, PASS)
    assert at(lines) is VERIFIED


def test_generator_is_accepted_and_read_once():
    consumed = []

    def lines():
        for line in ended(1, PASS):
            consumed.append(line)
            yield line

    assert at(lines()) is VERIFIED
    assert len(consumed) == 2


def test_arguments_are_not_modified():
    lines = [start(1)] + ended(2, PASS) + failed(3, CLASS_I[0]) + [end(1, FAIL)]
    before = copy.deepcopy(lines)
    assert at(lines) is NOT_VERIFIED
    assert lines == before


def test_lines_of_read_are_accepted(tmp_path):
    run_id = "example_run"
    for line in ended(1, PASS) + [start(2)]:
        events.append(tmp_path, run_id, line["kind"], line["data"], **TARGET)
    log = events.read(tmp_path, run_id)
    assert at(log.events) is UNDETERMINED
    assert at(log.events[:2]) is VERIFIED


@pytest.mark.parametrize("step", STEPS)
def test_each_step_is_accepted(step):
    assert at(ended(1, PASS, step=step), step) is VERIFIED


class Text(str):
    pass


@pytest.mark.parametrize(
    "step", ["sim_run", None, Text(STEP_SIM), "correctness_check", 1, [STEP_SIM]]
)
def test_step_outside_steps_is_refused(step):
    with pytest.raises(
        JournalError, match=r"^step: must be one of correctness_check_sim"
    ):
        standing([], step, *ARGS)


def test_step_is_checked_before_lines():
    def lines():
        raise AssertionError("read")
        yield

    with pytest.raises(JournalError, match="^step:"):
        standing(lines(), "sim_run", *ARGS)


@pytest.mark.parametrize(
    ("numbers", "place"),
    [
        ((None, 2, 1), "round"),
        ((3, None, 1), "candidate"),
        ((3, 2, None), "attempt"),
    ],
)
def test_missing_number_is_refused(numbers, place):
    with pytest.raises(JournalError, match=f"^{place}: is required"):
        at([], numbers=numbers)


@pytest.mark.parametrize(
    ("numbers", "place"),
    [
        ((True, 2, 1), "round"),
        ((3, False, 1), "candidate"),
        ((3, 2, True), "attempt"),
        ((-1, 2, 1), "round"),
        ((3, 0, 1), "candidate"),
        ((3, 2, 0), "attempt"),
        ((keys.MAX_INTEGER + 1, 2, 1), "round"),
        ((3, keys.MAX_INTEGER + 1, 1), "candidate"),
        ((3, 2, keys.MAX_INTEGER + 1), "attempt"),
        ((3.0, 2, 1), "round"),
        ((3, "2", 1), "candidate"),
    ],
)
def test_invalid_number_is_refused(numbers, place):
    with pytest.raises(events.InvalidEventError, match=f"^{place}:"):
        at([], numbers=numbers)


def test_numbers_at_their_bounds_are_accepted():
    top = keys.MAX_INTEGER
    numbers = {"round": 0, "candidate": top, "attempt": top}
    assert at(ended(1, PASS, numbers=numbers), numbers=(0, top, top)) is VERIFIED


BAD_LINES = [
    ("not a dict", events.InvalidEventError),
    (
        {"schema_version": 1, "time": TIME, "kind": "example_kind"},
        events.InvalidEventError,
    ),
    (
        {"schema_version": 2, "time": TIME, "kind": "example_kind", "data": {}},
        events.UnsupportedVersionError,
    ),
    (ev(STEP_STARTED, {"step": STEP_SIM}), JournalError),
    (ev(STEP_STARTED, {"step": STEP_SIM, "execution": 0}), JournalError),
    (ev(STEP_ENDED, {"step": STEP_SIM, "execution": 1, "spend": {}}), JournalError),
    (
        ev(STEP_ENDED, {"step": STEP_SIM, "execution": 1, "spend": {}, "result": []}),
        JournalError,
    ),
    (
        ev(
            STEP_ENDED,
            {"step": STEP_SIM, "execution": 1, "spend": {}, "failure": {"kind": "X"}},
        ),
        JournalError,
    ),
    (end(1, FAIL, step=STEP_BOARD) | {"extra": 1}, events.InvalidEventError),
]


@pytest.mark.parametrize(("bad", "error"), BAD_LINES)
@pytest.mark.parametrize("position", [1, 3])
def test_malformed_line_is_refused_with_its_number(bad, error, position):
    lines = ended(1, FAIL) + [start(2)]
    lines.insert(position - 1, bad)
    with pytest.raises(error, match=f"^line {position}: "):
        at(lines)


def test_first_malformed_line_is_reported():
    lines = [start(1), ev(STEP_STARTED, {}), "not a dict"]
    with pytest.raises(JournalError, match="^line 2: "):
        at(lines)


@pytest.mark.parametrize(
    ("result", "match"),
    [
        ({}, "data.result: lacks the member outcome"),
        ({"condition": "exit_status"}, "data.result: lacks the member outcome"),
        (
            {"outcome": "passed"},
            "data.result.outcome: must be one of pass, fail, broken, got str 'passed'",
        ),
        ({"outcome": "PASS"}, "data.result.outcome: must be one of pass, fail, broken"),
        (
            {"outcome": 1},
            "data.result.outcome: must be one of pass, fail, broken, got int 1",
        ),
        (
            {"outcome": None},
            "data.result.outcome: must be one of pass, fail, broken, got NoneType",
        ),
        (
            {"outcome": [PASS]},
            "data.result.outcome: must be one of pass, fail, broken, got list",
        ),
        (
            {"outcome": Text(PASS)},
            "data.result.outcome: must be one of pass, fail, broken, got Text",
        ),
    ],
)
def test_result_without_admitted_outcome_is_refused(result, match):
    lines = ended(1, FAIL) + [start(2), end(2, result=result)]
    with pytest.raises(JournalError, match=f"^line 4: {match}"):
        at(lines)


def test_unknown_outcome_beside_fail_is_still_refused():
    with pytest.raises(JournalError, match="^line 1: "):
        at([end(1, result={"outcome": "unknown"})] + ended(2, FAIL))


def test_outcome_too_long_to_show(monkeypatch):
    def refuse(value):
        raise ValueError("too long")

    monkeypatch.setattr(check_standing.reprlib, "repr", refuse)
    with pytest.raises(
        JournalError,
        match="^line 1: data.result.outcome: .* got int a value too long to show$",
    ):
        at([end(1, result={"outcome": 7})])
    with pytest.raises(
        JournalError, match="^step: .* got str a value too long to show$"
    ):
        standing([], "sim_run", *ARGS)


def test_unstarted_kinds_are_the_seven_constants():
    assert type(UNSTARTED_KINDS) is frozenset
    assert UNSTARTED_KINDS == {
        check_failure.KIND_NO_KERNEL_SOURCE,
        check_failure.KIND_KERNEL_SOURCE_UNREADABLE,
        check_failure.KIND_BUILD_DIRECTORY_UNUSABLE,
        check_failure.KIND_BUILD_INPUT_MISSING,
        check_failure.KIND_COMPILER_UNAVAILABLE,
        check_failure.KIND_BUILD_OUTPUT_MISSING,
        check_failure.KIND_EXECUTABLE_UNSTARTABLE,
    }
    assert UNSTARTED_KINDS == set(CLASS_I)
    assert UNSTARTED_KINDS < check_failure.BACKEND_KINDS
    assert check_failure.BACKEND_KINDS - UNSTARTED_KINDS == {
        check_failure.KIND_SETTINGS_REFUSED
    }


def test_standing_has_exactly_three_members():
    assert [member.name for member in Standing] == [
        "NOT_VERIFIED",
        "VERIFIED",
        "UNDETERMINED",
    ]


def test_public_names():
    public = {name for name in vars(check_standing) if not name.startswith("_")}
    imported = {
        "enum",
        "reprlib",
        "check_failure",
        "check_identity",
        "check_result",
        "events",
        "journal",
    }
    assert public - imported == {
        "STEPS_OF",
        "Standing",
        "UNSTARTED_KINDS",
        "point_standing",
        "standing",
    }
    assert journal.JournalError.__mro__[1] is ValueError


# point_standing: the lines of the one v2 value of a point (ADR-0183 decision 8)

RETIRED = (
    "correctness_check_sim",
    "correctness_check_board",
    "correctness_check_bf16_sim",
    "correctness_check_bf16_board",
)
RETIRED_SIM = "correctness_check_bf16_sim"
RETIRED_BOARD = "correctness_check_bf16_board"


def at_point(lines, point="sim", numbers=ARGS):
    return check_standing.point_standing(lines, point, *numbers)


def test_steps_of_names_the_one_v2_value_of_each_point():
    assert check_standing.STEPS_OF == {
        "sim": ("correctness_check_sim_v2",),
        "board": ("correctness_check_board_v2",),
    }
    assert check_standing.STEPS_OF == {"sim": (STEP_SIM,), "board": (STEP_BOARD,)}
    assert {
        step for steps in check_standing.STEPS_OF.values() for step in steps
    } == set(STEPS)


@pytest.mark.parametrize(("lines", "expected"), WALK_THROUGH)
@pytest.mark.parametrize(("point", "step"), [("sim", STEP_SIM), ("board", STEP_BOARD)])
def test_point_standing_is_the_standing_of_its_v2_value(lines, expected, point, step):
    moved = [copy.deepcopy(event) for event in lines]
    for event in moved:
        event["data"]["step"] = step
    assert at_point(moved, point) is expected
    assert at_point(moved, point) is at(moved, step)


@pytest.mark.parametrize(
    ("lines", "expected"),
    [
        (ended(1, PASS) + ended(1, FAIL, step=RETIRED_SIM), VERIFIED),
        (ended(1, FAIL) + ended(2, PASS, step="correctness_check_sim"), NOT_VERIFIED),
        (ended(1, PASS) + [start(1, step=RETIRED_SIM)], VERIFIED),
        (
            failed(1, "build_log_unwritable", step=RETIRED_SIM) + ended(1, PASS),
            VERIFIED,
        ),
        (broken(1, "exit_status") + ended(2, PASS, step=RETIRED_SIM), NOT_VERIFIED),
    ],
)
def test_point_standing_passes_over_the_lines_of_a_retired_value(lines, expected):
    assert at_point(lines) is expected


@pytest.mark.parametrize("step", RETIRED)
@pytest.mark.parametrize("point", ["sim", "board"])
def test_a_log_of_retired_lines_only_is_neither_read_nor_refused(step, point):
    lines = (
        ended(1, PASS, step=step)
        + ended(2, FAIL, step=step)
        + [end(3, step=step, result={"max_abs_error": 0.0})]
        + [start(4, step=step)]
    )
    assert at_point(lines, point) is UNDETERMINED
    with pytest.raises(JournalError, match="^step: "):
        standing(lines, step, *ARGS)


def test_point_standing_ignores_the_other_point():
    lines = ended(1, FAIL, step=STEP_BOARD) + ended(1, PASS, step=STEP_SIM)
    assert at_point(lines, "sim") is VERIFIED
    assert at_point(lines, "board") is NOT_VERIFIED
    assert at_point(ended(1, PASS, step=STEP_BOARD), "sim") is UNDETERMINED


@pytest.mark.parametrize(
    "point", [STEP_SIM, RETIRED_SIM, "SIM", None, Text("sim"), 1, ["sim"]]
)
def test_point_outside_the_two_is_refused(point):
    def lines():
        raise AssertionError("read")
        yield

    with pytest.raises(JournalError, match=r"^point: must be one of sim, board, got "):
        check_standing.point_standing(lines(), point, *ARGS)


def test_point_standing_refuses_what_standing_refuses():
    with pytest.raises(JournalError, match="^attempt: is required"):
        at_point([], numbers=(3, 2, None))
    with pytest.raises(events.InvalidEventError, match="^round:"):
        at_point([], numbers=(True, 2, 1))
    bad = [end(1, step=STEP_SIM, result={"max_abs_error": 0.0})]
    with pytest.raises(
        JournalError, match="^line 1: data.result: lacks the member outcome$"
    ):
        at_point(bad)
    assert at_point(bad, "board") is UNDETERMINED
    with pytest.raises(ValueError, match="^line 2: "):
        at_point(ended(1, PASS, step=STEP_BOARD)[:1] + [{"kind": "x"}], "board")
    with pytest.raises(ValueError, match="^line 2: "):
        at_point(ended(1, PASS, step=RETIRED_BOARD)[:1] + [{"kind": "x"}], "sim")
