import copy
import json
import os
import time

import pytest

from hilclaw import (
    check_result,
    checks_tool,
    events,
    journal,
    keys,
    layout,
    spec,
    spec_feedback,
)
from hilclaw.spec_feedback import KIND_FEEDBACK_UNREADABLE, attempts
from hilclaw.tools import ToolFailure

RUN = "run-a"
SIM = "correctness_check_sim"
BOARD = "correctness_check_board"
SECRET = 987654.321
PASS = {"outcome": "pass", "max_abs_error": 0.0}
FAIL = {
    "outcome": "fail",
    "shape": {"m": 31, "k": 37, "n": 41},
    "draws": 43,
    "tolerance": {"rtol": SECRET, "atol": SECRET},
    "counts": [{"failed": 4747, "non_finite": 5353}],
    "max_abs_error": SECRET,
}
UNSTARTED = {"kind": "compiler_unavailable", "message": "no cc"}


def broken(condition, **more):
    return {"outcome": "broken", "condition": condition, **more}


def sentence(stage, point, outcome, phrase=None):
    text = f"Stage {stage}: the correctness check at the {point} point ended with "
    text += f"the outcome {outcome}"
    return text + (f": {phrase}." if phrase else ".")


BUILD_EXIT = "the compiler or the linker ended with a failure status"
BUILD_TIME = "the build of the verification executable passed its time limit"


@pytest.fixture
def root(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    return data_root


def document(round=1, attempt=1, techniques=(), run_id=RUN, candidate=1):
    hw = {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    op = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 3, "k": 5, "n": 7},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }
    operand = {"name": "a", "role": "input", "dtype": "synthetic_dtype", "shape": [3]}
    made = {
        "schema_version": 2,
        "id": {
            "run_id": run_id,
            "round": round,
            "candidate": candidate,
            "attempt": attempt,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": {"key": keys.hw_profile_key(hw).name, "record": hw},
        "task": {
            "op_signature": {"key": keys.op_signature_key(op).name, "record": op},
            "contract": {
                "language": "synthetic_lang",
                "prototype": "synthetic prototype text",
                "operands": [operand],
            },
            "objective": {
                "objectives": [{"type": "latency_minimisation"}],
                "constraints": [],
            },
        },
        "guidance": {"techniques": [{"id": t, "text": f"use {t}"} for t in techniques]},
        "feedback": {"attempts": []},
    }
    if attempt > 1:
        failure = {"attempt": attempt - 1, "stage": "compile", "report": "r"}
        made["repair"] = {"failures": [failure]}
    return made


def spec_path(root, round, attempt=1):
    return layout.attempt_artefact(root, RUN, round, 1, attempt, "spec.json")


def put_spec(root, round, attempt=1, techniques=(), content=None, **ident):
    path = spec_path(root, round, attempt)
    path.parent.mkdir(parents=True, exist_ok=True)
    if content is None:
        made = document(round, attempt, techniques, **ident)
        content = json.dumps(made).encode()
    path.write_bytes(content)
    return path


def check(root, round, step=SIM, attempt=1, execution=1, **outcome):
    numbers = {"round": round, "candidate": 1, "attempt": attempt}
    data = {"step": step, "execution": execution}
    events.append(root, RUN, journal.STEP_STARTED, data, **numbers)
    data = data | {"spend": {}, **outcome}
    events.append(root, RUN, journal.STEP_ENDED, data, **numbers)


def passed(root, round, attempt=1):
    check(root, round, SIM, attempt, result=PASS)
    check(root, round, BOARD, attempt, result=PASS)


def build_log(root, round, step=SIM, execution=1, attempt=1, content=b"x.c:1: error"):
    directory = layout.attempt_dir(root, RUN, round, "measure", 1, attempt)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"build-log-{step}-{execution:02d}.txt"
    path.write_bytes(content)
    return path


def valid_in_a_spec(entries, round):
    made = document(round)
    made["feedback"]["attempts"] = copy.deepcopy(entries)
    spec.validate(made)


def refused(root, kind, round=1, place=None):
    with pytest.raises(ToolFailure) as caught:
        attempts(root, RUN, round)
    assert caught.value.kind == kind
    message = caught.value.message
    assert str(root) not in message
    assert str(root.as_posix()) not in message
    if place is not None:
        assert message.startswith(place)
    return message


def compiled(report, techniques=()):
    failure = {"stage": "compile", "report": report}
    entry = {"round": 0, "candidate": 1, "attempt": 1, "techniques": list(techniques)}
    return [entry | {"failure": failure}]


def tree(root):
    return sorted(
        (path.relative_to(root).as_posix(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
    )


def test_the_kind_is_a_name_of_the_tool_layer():
    assert KIND_FEEDBACK_UNREADABLE == "feedback_unreadable"


def test_a_round_0_attempt_that_passed_both_points_is_shown_without_failure(root):
    put_spec(root, 0)
    passed(root, 0)
    got = attempts(root, RUN, 1)
    assert got == [{"round": 0, "candidate": 1, "attempt": 1, "techniques": []}]
    valid_in_a_spec(got, 1)


def test_a_build_failure_shows_the_sentence_and_the_compiler_log(root):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    build_log(root, 0, content="x.c:3: error: é\n".encode())
    got = attempts(root, RUN, 1)
    report = sentence("compile", "sim", "broken", BUILD_EXIT)
    report += "\nCompiler log:\nx.c:3: error: é\n"
    failure = {"stage": "compile", "report": report}
    assert got == [
        {"round": 0, "candidate": 1, "attempt": 1, "techniques": [], "failure": failure}
    ]
    assert got[0]["failure"]["report"].startswith(
        sentence("compile", "sim", "broken", BUILD_EXIT)
    )
    valid_in_a_spec(got, 1)


@pytest.mark.parametrize("content", [None, b""])
def test_a_build_failure_without_a_log_or_with_an_empty_one_is_the_sentence(
    root, content
):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    if content is not None:
        build_log(root, 0, content=content)
    got = attempts(root, RUN, 1)
    assert got == compiled(sentence("compile", "sim", "broken", BUILD_EXIT))
    valid_in_a_spec(got, 1)


def test_round_4_of_the_walk_through(root):
    put_spec(root, 0)
    passed(root, 0)
    put_spec(root, 1, techniques=["a", "b"])
    check(root, 1, result=FAIL)
    put_spec(root, 2, techniques=["c"])
    check(root, 2, failure=UNSTARTED)
    put_spec(root, 3, techniques=["d"])
    check(root, 3, result=PASS)
    got = attempts(root, RUN, 4)
    assert got == [
        {"round": 0, "candidate": 1, "attempt": 1, "techniques": []},
        {
            "round": 1,
            "candidate": 1,
            "attempt": 1,
            "techniques": ["a", "b"],
            "failure": {"stage": "sim", "report": sentence("sim", "sim", "fail")},
        },
        {"round": 3, "candidate": 1, "attempt": 1, "techniques": ["d"]},
    ]
    valid_in_a_spec(got, 4)


def test_a_board_failure_after_a_sim_pass_is_stage_board(root):
    put_spec(root, 0)
    check(root, 0, SIM, result=PASS)
    check(root, 0, BOARD, result=FAIL)
    got = attempts(root, RUN, 1)
    failure = {"stage": "board", "report": sentence("board", "board", "fail")}
    entry = {"round": 0, "candidate": 1, "attempt": 1, "techniques": []}
    assert got == [entry | {"failure": failure}]
    valid_in_a_spec(got, 1)


def test_a_board_build_past_its_limit_reads_the_board_log(root):
    put_spec(root, 0)
    check(root, 0, SIM, result=PASS)
    check(root, 0, BOARD, execution=3, result=broken("build_time_limit"))
    build_log(root, 0, SIM, 1, content=b"not this one")
    build_log(root, 0, BOARD, 3, content=b"killed")
    got = attempts(root, RUN, 1)
    report = (
        sentence("compile", "board", "broken", BUILD_TIME) + "\nCompiler log:\nkilled"
    )
    assert got == compiled(report)
    valid_in_a_spec(got, 1)


def test_the_first_failing_line_decides_and_names_the_log(root):
    put_spec(root, 0)
    check(root, 0, SIM, execution=1, result=PASS)
    check(root, 0, SIM, execution=2, failure=UNSTARTED)
    check(root, 0, SIM, execution=7, result=broken("build_exit_status"))
    check(root, 0, SIM, execution=4, result=FAIL)
    build_log(root, 0, SIM, 4, content=b"wrong")
    build_log(root, 0, SIM, 7, content=b"right")
    got = attempts(root, RUN, 1)
    report = sentence("compile", "sim", "broken", BUILD_EXIT)
    assert got == compiled(report + "\nCompiler log:\nright")
    valid_in_a_spec(got, 1)


def test_an_execution_of_three_digits_is_written_in_full(root):
    put_spec(root, 0)
    check(root, 0, SIM, execution=123, result=broken("build_exit_status"))
    assert build_log(root, 0, SIM, 123, content=b"long").name.endswith("-123.txt")
    got = attempts(root, RUN, 1)
    report = sentence("compile", "sim", "broken", BUILD_EXIT)
    assert got == compiled(report + "\nCompiler log:\nlong")
    valid_in_a_spec(got, 1)


def test_several_attempts_of_a_round_are_in_ascending_order(root):
    for attempt in (10, 2, 1):
        put_spec(root, 0, attempt, techniques=[f"t{attempt}"])
        check(root, 0, SIM, attempt, result=FAIL)
    put_spec(root, 1, 1)
    check(root, 1, SIM, 1, result=FAIL)
    got = attempts(root, RUN, 2)
    failure = {"stage": "sim", "report": sentence("sim", "sim", "fail")}
    assert got == [
        {
            "round": round,
            "candidate": 1,
            "attempt": attempt,
            "techniques": techniques,
            "failure": failure,
        }
        for round, attempt, techniques in (
            (0, 1, ["t1"]),
            (0, 2, ["t2"]),
            (0, 10, ["t10"]),
            (1, 1, []),
        )
    ]
    valid_in_a_spec(got, 2)


@pytest.mark.parametrize("condition", check_result.CONDITIONS)
def test_each_condition_has_its_own_phrase(root, condition):
    put_spec(root, 0)
    check(root, 0, result=broken(condition))
    report = attempts(root, RUN, 1)[0]["failure"]["report"]
    assert report.startswith("Stage ")
    assert "a condition this report does not name" not in report
    assert condition not in report


def test_the_phrases_are_distinct():
    phrases = set()
    for condition in check_result.CONDITIONS:
        phrases.add(spec_feedback._PHRASES[condition])
    assert len(phrases) == len(check_result.CONDITIONS)


@pytest.mark.parametrize(
    "result",
    [
        {"outcome": "broken", "condition": "a_new_condition\nwith text"},
        {"outcome": "broken", "condition": ["build_exit_status"]},
        {"outcome": "broken", "condition": {"x": 1}},
        {"outcome": "broken"},
    ],
)
def test_an_unknown_condition_gets_the_generic_phrase_and_is_not_echoed(root, result):
    put_spec(root, 0)
    check(root, 0, result=result)
    failure = attempts(root, RUN, 1)[0]["failure"]
    phrase = "a condition this report does not name"
    assert failure == {
        "stage": "sim",
        "report": sentence("sim", "sim", "broken", phrase),
    }


def test_no_report_carries_a_member_of_the_result_beyond_outcome_and_condition(root):
    put_spec(root, 0)
    check(root, 0, SIM, result=FAIL)
    put_spec(root, 1)
    check(
        root,
        1,
        SIM,
        result=broken(
            "build_exit_status", **{k: FAIL[k] for k in FAIL if k != "outcome"}
        ),
    )
    put_spec(root, 2)
    check(
        root,
        2,
        SIM,
        result=broken("check_value", **{k: FAIL[k] for k in FAIL if k != "outcome"}),
    )
    got = attempts(root, RUN, 3)
    text = json.dumps(got)
    for value in ("987654", "4747", "5353", "31", "37", "41", "43"):
        assert value not in text
    for member in ("counts", "draws", "tolerance", "shape", "max_abs_error", "rtol"):
        assert member not in text
    assert all(
        set(e) <= {"round", "candidate", "attempt", "techniques", "failure"}
        for e in got
    )


def test_no_run_directory_gives_no_attempt(root):
    assert attempts(root, RUN, 1) == []


def test_a_rounds_directory_without_attempts_gives_none(root):
    (layout.run_dir(root, RUN) / "rounds" / "0000" / "coder").mkdir(parents=True)
    (layout.run_dir(root, RUN) / "rounds" / "0001").mkdir(parents=True)
    assert attempts(root, RUN, 2) == []


def test_attempts_without_a_log_are_undetermined_and_not_shown(root):
    put_spec(root, 0)
    put_spec(root, 1)
    assert attempts(root, RUN, 2) == []


def test_rounds_at_or_above_the_requested_one_are_ignored(root):
    put_spec(root, 0)
    passed(root, 0)
    for round in (1, 2):
        put_spec(root, round, content=b"not json")
    assert [e["round"] for e in attempts(root, RUN, 1)] == [0]


def test_names_that_are_not_the_layout_form_are_ignored(root):
    put_spec(root, 0)
    passed(root, 0)
    rounds = layout.run_dir(root, RUN) / "rounds"
    attempts_dir = spec_path(root, 0).parent.parent
    for directory in (rounds, attempts_dir):
        for name in ("tmp", "1", "001", "00000", "+1", "١", "0a"):
            (directory / name).mkdir()
            (directory / name / "spec.json").write_bytes(b"not json")
    (attempts_dir / "00").mkdir()
    (attempts_dir / "00" / "spec.json").write_bytes(b"not json")
    (rounds / "a-file").write_bytes(b"")
    assert attempts(root, RUN, 1) == [
        {"round": 0, "candidate": 1, "attempt": 1, "techniques": []}
    ]


def test_an_attempt_directory_without_a_spec_is_ignored(root):
    put_spec(root, 0)
    passed(root, 0)
    (spec_path(root, 0, 2).parent).mkdir(parents=True)
    check(root, 0, SIM, 2, result=FAIL)
    assert [e["attempt"] for e in attempts(root, RUN, 1)] == [1]


def test_a_file_in_place_of_a_directory_is_not_there(root):
    run_dir = layout.run_dir(root, RUN)
    run_dir.mkdir(parents=True)
    (run_dir / "rounds").write_bytes(b"")
    assert attempts(root, RUN, 1) == []


def test_a_huge_round_returns_promptly(root):
    put_spec(root, 0)
    passed(root, 0)
    started = time.monotonic()
    got = attempts(root, RUN, keys.MAX_INTEGER)
    assert time.monotonic() - started < 5
    assert [e["round"] for e in got] == [0]


def test_a_class_i_failure_alone_at_sim_is_undetermined(root):
    put_spec(root, 0)
    check(root, 0, SIM, failure=UNSTARTED)
    check(root, 0, BOARD, result=FAIL)
    assert attempts(root, RUN, 1) == []


def test_an_attempt_verified_at_sim_and_undetermined_at_board_has_no_failure(root):
    put_spec(root, 0)
    check(root, 0, SIM, result=PASS)
    check(root, 0, BOARD, failure=UNSTARTED)
    assert attempts(root, RUN, 1) == [
        {"round": 0, "candidate": 1, "attempt": 1, "techniques": []}
    ]


def test_lines_of_other_candidates_and_steps_are_not_counted(root):
    put_spec(root, 0)
    check(root, 0, SIM, result=PASS)
    events.append(
        root,
        RUN,
        journal.STEP_ENDED,
        {"step": SIM, "execution": 1, "spend": {}, "result": {"no": "outcome"}},
        round=0,
        candidate=2,
        attempt=1,
    )
    assert attempts(root, RUN, 1) == [
        {"round": 0, "candidate": 1, "attempt": 1, "techniques": []}
    ]


@pytest.mark.parametrize(
    "content",
    [
        b"not json",
        b"",
        json.dumps({**document(0), "schema_version": 1}).encode(),
        json.dumps(document(0, attempt=2)).encode(),
        json.dumps(document(1)).encode(),
        json.dumps(document(0, run_id="run-b")).encode(),
        json.dumps(document(0, run_id="Run A")).encode(),
        json.dumps(document(0, candidate=2)).encode(),
    ],
)
def test_a_bad_spec_is_feedback_unreadable(root, content):
    put_spec(root, 0, content=content)
    place = f"runs/{RUN}/rounds/0000/coder/candidates/01/attempts/01/spec.json: "
    refused(root, KIND_FEEDBACK_UNREADABLE, place=place)


def test_a_spec_that_is_a_directory_is_feedback_unreadable(root):
    spec_path(root, 0).mkdir(parents=True)
    message = refused(root, KIND_FEEDBACK_UNREADABLE)
    assert message.endswith("spec.json: is no regular file")


def test_the_first_bad_spec_in_order_decides(root):
    put_spec(root, 0, 2, content=b"second")
    put_spec(root, 1, 1, content=b"third")
    put_spec(root, 0, 10, content=b"[]")
    refused(
        root,
        KIND_FEEDBACK_UNREADABLE,
        2,
        f"runs/{RUN}/rounds/0000/coder/candidates/01/attempts/02/",
    )


def test_a_listing_that_fails_is_feedback_unreadable(root, monkeypatch):
    put_spec(root, 0)
    real = os.listdir

    def fake(path):
        if str(path).endswith("attempts"):
            raise PermissionError(13, "Permission denied", str(path))
        return real(path)

    monkeypatch.setattr(spec_feedback.os, "listdir", fake)
    message = refused(root, KIND_FEEDBACK_UNREADABLE)
    assert message == (
        f"runs/{RUN}/rounds/0000/coder/candidates/01/attempts: "
        "could not be listed: PermissionError: Permission denied"
    )


def test_a_rounds_listing_that_fails_is_feedback_unreadable(root, monkeypatch):
    put_spec(root, 0)
    real = os.listdir

    def fake(path):
        if str(path).endswith("rounds"):
            raise OSError(5, "Input/output error", str(path))
        return real(path)

    monkeypatch.setattr(spec_feedback.os, "listdir", fake)
    refused(
        root, KIND_FEEDBACK_UNREADABLE, place=f"runs/{RUN}/rounds: could not be listed"
    )


@pytest.mark.parametrize("target", ["spec.json", ".txt"])
def test_a_failing_lstat_is_feedback_unreadable(root, monkeypatch, target):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    build_log(root, 0)
    real = os.lstat

    def fake(path, *args, **kwargs):
        if str(path).endswith(target):
            raise PermissionError(13, "Permission denied", str(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(spec_feedback.os, "lstat", fake)
    message = refused(root, KIND_FEEDBACK_UNREADABLE)
    assert message.endswith(": could not be read: PermissionError: Permission denied")
    assert target in message.split(":")[0]


@pytest.mark.parametrize("target", ["spec.json", ".txt"])
def test_a_failing_read_is_feedback_unreadable(root, monkeypatch, target):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    build_log(root, 0)
    real = spec_feedback.Path.read_bytes

    def fake(path):
        if str(path).endswith(target):
            raise OSError(5, "Input/output error", str(path))
        return real(path)

    monkeypatch.setattr(spec_feedback.Path, "read_bytes", fake)
    message = refused(root, KIND_FEEDBACK_UNREADABLE)
    assert message.endswith(": could not be read: OSError: Input/output error")
    assert target in message.split(":")[0]


def test_a_damaged_log_line_is_run_file_invalid(root):
    put_spec(root, 0)
    path = layout.run_file(root, RUN, "events.ndjson")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"{not json}\n")
    refused(root, "run_file_invalid", place=f"runs/{RUN}/events.ndjson")


def test_a_bad_step_line_is_run_file_invalid(root):
    put_spec(root, 0)
    events.append(
        root,
        RUN,
        journal.STEP_ENDED,
        {"step": SIM, "spend": {}, "result": PASS},
        round=0,
        candidate=1,
        attempt=1,
    )
    refused(root, "run_file_invalid", place=f"runs/{RUN}/events.ndjson: line 1")


def test_a_log_line_of_another_version_is_run_file_unsupported(root):
    put_spec(root, 0)
    path = layout.run_file(root, RUN, "events.ndjson")
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "schema_version": 9,
        "time": "2026-10-20T00:00:00Z",
        "kind": "x",
        "data": {},
    }
    path.write_bytes(json.dumps(line).encode() + b"\n")
    refused(root, "run_file_unsupported", place=f"runs/{RUN}/events.ndjson")


def test_a_log_that_is_a_directory_is_run_file_invalid(root):
    put_spec(root, 0)
    layout.run_file(root, RUN, "events.ndjson").mkdir()
    refused(root, "run_file_invalid", place=f"runs/{RUN}/events.ndjson")


def test_a_result_without_outcome_is_check_result_invalid(root):
    put_spec(root, 0)
    check(root, 0, BOARD, result={"max_abs_error": 1.0})
    refused(
        root,
        checks_tool.KIND_CHECK_RESULT_INVALID,
        place=f"runs/{RUN}/events.ndjson: line 2",
    )


def test_a_result_without_outcome_of_another_attempt_is_not_looked_at(root):
    put_spec(root, 0)
    passed(root, 0)
    check(root, 0, SIM, 5, result={"max_abs_error": 1.0})
    assert len(attempts(root, RUN, 1)) == 1


@pytest.mark.parametrize(
    ("content", "problem"),
    [
        (b"\xef\xbb\xbfx.c: error", "starts with a byte order mark"),
        (b"x.c: \xff error", "is no UTF-8 at byte 5"),
    ],
)
def test_a_compiler_log_that_is_no_utf_8_is_feedback_unreadable(root, content, problem):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    build_log(root, 0, content=content)
    message = refused(root, KIND_FEEDBACK_UNREADABLE)
    place = f"runs/{RUN}/rounds/0000/measure/candidates/01/attempts/01/"
    assert message == f"{place}build-log-{SIM}-01.txt: {problem}"


def test_a_compiler_log_that_is_a_directory_is_feedback_unreadable(root):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    directory = layout.attempt_dir(root, RUN, 0, "measure", 1, 1)
    (directory / f"build-log-{SIM}-01.txt").mkdir(parents=True)
    message = refused(root, KIND_FEEDBACK_UNREADABLE)
    assert message.endswith(".txt: is no regular file")


def test_a_compiler_log_is_not_read_for_a_failure_of_another_stage(root):
    put_spec(root, 0)
    check(root, 0, result=broken("exit_status"))
    build_log(root, 0, content=b"\xff")
    assert attempts(root, RUN, 1)[0]["failure"]["stage"] == "sim"


def test_a_bad_spec_is_reported_before_a_damaged_log(root):
    put_spec(root, 0)
    put_spec(root, 1, content=b"bad")
    layout.run_file(root, RUN, "events.ndjson").write_bytes(b"{bad\n")
    refused(root, KIND_FEEDBACK_UNREADABLE, 2)


def test_a_damaged_log_is_reported_before_a_bad_compiler_log(root):
    put_spec(root, 0)
    check(root, 0, result=broken("build_exit_status"))
    build_log(root, 0, content=b"\xff")
    put_spec(root, 1)
    check(root, 1, BOARD, result={"no": "outcome"})
    refused(root, checks_tool.KIND_CHECK_RESULT_INVALID, 2)


def test_nothing_is_created_or_changed_below_the_data_root(root):
    put_spec(root, 0, techniques=["a"])
    check(root, 0, result=broken("build_exit_status"))
    build_log(root, 0)
    put_spec(root, 1)
    before = tree(root)
    attempts(root, RUN, 5)
    attempts(root, RUN, 1)
    assert tree(root) == before


def test_no_other_run_file_is_read(root):
    put_spec(root, 0)
    passed(root, 0)
    for name in ("STATE.json", "instance.json"):
        layout.run_file(root, RUN, name).mkdir()
    decision = layout.role_dir(root, RUN, 0, "decision")
    decision.mkdir(parents=True)
    (decision / "hypotheses.json").mkdir()
    (decision / "decision.md").mkdir()
    assert len(attempts(root, RUN, 1)) == 1


def test_each_call_returns_new_entries(root):
    put_spec(root, 0, techniques=["a"])
    check(root, 0, result=FAIL)
    first = attempts(root, RUN, 1)
    first[0]["techniques"].append("z")
    first[0]["failure"]["report"] = "changed"
    second = attempts(root, RUN, 1)
    assert second[0]["techniques"] == ["a"]
    assert second[0]["failure"]["report"] == sentence("sim", "sim", "fail")


def test_a_data_root_as_a_str_is_accepted(root):
    put_spec(root, 0)
    passed(root, 0)
    assert len(attempts(str(root), RUN, 1)) == 1


@pytest.mark.parametrize(
    ("round", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (keys.MAX_INTEGER + 1, ValueError),
        (True, TypeError),
        ("1", TypeError),
        (1.0, TypeError),
        (None, TypeError),
    ],
)
def test_a_bad_round_is_refused_by_the_caller_check(root, round, error):
    with pytest.raises(error, match="^round: "):
        attempts(root, RUN, round)


@pytest.mark.parametrize("run_id", ["Run-A", "", "../x", None, 3, "a" * 65])
def test_a_bad_run_id_is_refused_by_the_layout(root, run_id):
    with pytest.raises(layout.InvalidPathValueError):
        attempts(root, run_id, 1)


# The lines of a bf16 check (ADR-0178 decision 1)

BF16_SIM = "correctness_check_bf16_sim"
BF16_BOARD = "correctness_check_bf16_board"


def bf16(failed=0, kind="swiglu"):
    dims = {"gemm": (4, 2, 8), "sdpa_kv_cache": (2, 3, 4, 2, 8)}.get(kind, (2, 8))
    entry = (failed, 0, 0) if kind == "sdpa_kv_cache" else (failed, 0)
    return check_result.bf16_completed(
        kind, dims, draws=1, rtol=0.01, atol=0.001, counts=[entry]
    )


def bf16_broken(condition):
    return check_result.bf16_broken(
        condition, "swiglu", (2, 8), draws=1, rtol=0.01, atol=0.001
    )


def entry(failure=None, round=0, attempt=1):
    made = {"round": round, "candidate": 1, "attempt": attempt, "techniques": []}
    return made if failure is None else made | {"failure": failure}


@pytest.mark.parametrize("kind", check_result.BF16_KINDS)
def test_a_bf16_round_0_attempt_is_read_as_an_fp32_one(root, kind):
    put_spec(root, 0, 1)
    put_spec(root, 0, 2)
    put_spec(root, 0, 3)
    check(root, 0, BF16_SIM, 1, result=bf16(kind=kind))
    check(root, 0, BF16_BOARD, 1, result=bf16(kind=kind))
    check(root, 0, BF16_SIM, 2, result=bf16(1, kind))
    check(root, 0, BF16_SIM, 3, result=bf16(kind=kind))
    check(root, 0, BF16_BOARD, 3, result=bf16(2, kind))
    got = attempts(root, RUN, 1)
    assert got == [
        entry(),
        entry({"stage": "sim", "report": sentence("sim", "sim", "fail")}, attempt=2),
        entry({"stage": "board", "report": sentence("board", "board", "fail")}, 0, 3),
    ]
    valid_in_a_spec(got, 1)


def test_a_bf16_build_failure_shows_the_compiler_log_of_its_step(root):
    put_spec(root, 0)
    check(root, 0, BF16_SIM, result=bf16_broken("build_time_limit"))
    build_log(root, 0, SIM, content=b"not this one")
    build_log(root, 0, BF16_SIM, content=b"x.c:9: slow")
    report = sentence("compile", "sim", "broken", BUILD_TIME)
    report += "\nCompiler log:\nx.c:9: slow"
    assert attempts(root, RUN, 1) == [entry({"stage": "compile", "report": report})]


def test_an_open_bf16_sim_check_is_not_shown(root):
    put_spec(root, 0)
    check(root, 0, BF16_SIM, result=bf16())
    events.append(
        root,
        RUN,
        journal.STEP_STARTED,
        {"step": BF16_SIM, "execution": 2},
        round=0,
        candidate=1,
        attempt=1,
    )
    assert attempts(root, RUN, 1) == []


def test_the_deciding_check_is_the_first_failed_line_under_either_value(root):
    put_spec(root, 0)
    put_spec(root, 0, 2)
    check(root, 0, BF16_SIM, result=bf16_broken("build_exit_status"))
    check(root, 0, SIM, execution=1, result=FAIL)
    build_log(root, 0, BF16_SIM, content=b"bf16 log")
    build_log(root, 0, SIM, content=b"fp32 log")
    check(root, 0, SIM, 2, result=FAIL)
    check(root, 0, BF16_SIM, 2, result=bf16_broken("build_exit_status"))
    report = sentence("compile", "sim", "broken", BUILD_EXIT)
    assert attempts(root, RUN, 1) == [
        entry({"stage": "compile", "report": report + "\nCompiler log:\nbf16 log"}),
        entry({"stage": "sim", "report": sentence("sim", "sim", "fail")}, attempt=2),
    ]


def test_a_pass_under_each_value_of_both_points_shows_no_failure(root):
    put_spec(root, 0)
    passed(root, 0)
    check(root, 0, BF16_SIM, result=bf16())
    check(root, 0, BF16_BOARD, result=bf16())
    assert attempts(root, RUN, 1) == [entry()]


def test_a_bf16_board_fail_beside_an_fp32_board_pass_is_a_board_failure(root):
    put_spec(root, 0)
    passed(root, 0)
    check(root, 0, BF16_BOARD, result=bf16(3))
    report = sentence("board", "board", "fail")
    assert attempts(root, RUN, 1) == [entry({"stage": "board", "report": report})]


def test_a_damaged_bf16_end_line_is_run_file_invalid(root):
    put_spec(root, 0)
    numbers = {"round": 0, "candidate": 1, "attempt": 1}
    data = {"step": BF16_SIM, "execution": 1, "result": bf16()}
    events.append(root, RUN, journal.STEP_ENDED, data, **numbers)
    message = refused(root, "run_file_invalid")
    assert message == f"runs/{RUN}/events.ndjson: line 1: data: lacks the member spend"


def test_a_bf16_result_without_an_outcome_is_check_result_invalid(root):
    put_spec(root, 0)
    result = bf16()
    del result["outcome"]
    check(root, 0, BF16_BOARD, result=result)
    message = refused(root, "check_result_invalid")
    assert message == (
        f"runs/{RUN}/events.ndjson: line 2: data.result: lacks the member outcome"
    )
