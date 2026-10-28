import copy
import errno
import io
import json
import os
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    check_result,
    checks_tool,
    events,
    hypotheses_file,
    journal,
    layout,
    mcp_front,
    once_write,
    run_result,
    timings_tool,
    tools,
    verdicts_file,
    verdicts_tool,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
HYPOTHESES = {
    "schema_version": 1,
    "run_id": RUN,
    "round": 1,
    "candidates": 2,
    "hypotheses": [
        {
            "id": "h1",
            "statement": "unrolling lowers latency",
            "basis": [
                {
                    "kind": "attempt",
                    "ref": {"round": 0, "candidate": 1, "attempt": 1},
                    "text": "the baseline",
                }
            ],
            "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
            "origin": "system",
            "tested_by": [1],
        },
        {
            "id": "h2",
            "statement": "tiling lowers latency",
            "basis": [
                {
                    "kind": "attempt",
                    "ref": {"round": 0, "candidate": 1, "attempt": 1},
                    "text": "the baseline",
                }
            ],
            "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
            "origin": "system",
            "tested_by": [2],
        },
    ],
}
HYPOTHESES_PATH = f"runs/{RUN}/rounds/0001/decision/hypotheses.json"
VERDICTS_PATH = f"runs/{RUN}/rounds/0001/eval/verdicts.json"
LOG = f"runs/{RUN}/events.ndjson"
SIM = "correctness_check_sim"
BOARD = "correctness_check_board"
PASS = {"outcome": "pass", "max_abs_error": 0.0}
FAIL = {"outcome": "fail", "max_abs_error": 2.5}
BROKEN = {"outcome": "broken"}
UNSTARTED = {"kind": "compiler_unavailable", "message": "no cc"}
KINDS = (
    "invalid_request",
    "no_data_root",
    "hypotheses_missing",
    "hypotheses_invalid",
    "hypotheses_unsupported",
    "hypotheses_unreadable",
    "verdicts_mismatch",
    "check_result_invalid",
    "timing_result_invalid",
    "check_unfounded",
    "comparison_unfounded",
    "comparison_unverified",
    "verdicts_exist",
    "verdicts_not_written",
)
RUN_FILE_KINDS = (
    "run_file_missing",
    "run_file_unreadable",
    "run_file_invalid",
    "run_file_unsupported",
)


def ref(round=1, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


def check_entry(at=(1, 1, 1), point="board", outcome="pass"):
    return {"kind": "check", "ref": ref(*at), "point": point, "outcome": outcome}


def comparison(point="board", difference="lower"):
    return {
        "kind": "comparison",
        "metric": "latency_minimisation",
        "point": point,
        "measured": ref(1, 1, 1),
        "against": ref(0, 1, 1),
        "difference": difference,
    }


def verdict(hypothesis, evidence, value="inconclusive", cause="no comparison yet"):
    return {
        "hypothesis": hypothesis,
        "verdict": value,
        "cause": cause,
        "evidence": evidence,
    }


def record(*entries, **top):
    if not entries:
        entries = (
            verdict("h1", [check_entry()]),
            verdict("h2", [check_entry((1, 2, 1), point="sim", outcome="fail")]),
        )
    return {
        "schema_version": 1,
        "run_id": RUN,
        "round": 1,
        "verdicts": list(entries),
    } | top


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


def start(root, execution=1, at=(1, 1, 1), step=BOARD):
    data = {"step": step, "execution": execution}
    events.append(root, RUN, journal.STEP_STARTED, data, **numbers(*at))


def end(root, execution=1, at=(1, 1, 1), step=BOARD, **outcome):
    data = {"step": step, "execution": execution, "spend": {}, **outcome}
    events.append(root, RUN, journal.STEP_ENDED, data, **numbers(*at))


def check(root, execution=1, at=(1, 1, 1), step=BOARD, **outcome):
    start(root, execution, at, step)
    end(root, execution, at, step, **outcome)


def raw(root, content):
    path = layout.run_file(root, RUN, "events.ndjson")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "ab") as f:
        f.write(content)


def line(data, kind=journal.STEP_ENDED, version=1, at=(1, 1, 1)):
    event = {"schema_version": version, "time": "2026-10-20T00:00:00Z", "kind": kind}
    return (json.dumps(event | numbers(*at) | {"data": data}) + "\n").encode()


def founding(root):
    check(root, result=PASS)
    check(root, at=(1, 2, 1), step=SIM, result=FAIL)
    check(root, at=(1, 2, 1), result=PASS)


def with_hypotheses(root, document=HYPOTHESES, log=True):
    content = (json.dumps(document, indent=2) + "\n").encode()
    hypotheses_file.write(root, content)
    if log:
        founding(root)


def eval_dir(root):
    return root / "runs" / RUN / "rounds" / "0001" / "eval"


def verdicts_path(root):
    return layout.verdict_record(root, RUN, 1)


def write(source, request):
    return verdicts_tool.definition(source).function(request)


def failure(source, request):
    with pytest.raises(ToolFailure) as refused:
        write(source, request)
    return refused.value


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = verdicts_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == verdicts_tool.NAME == "verdicts.write"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "record": {"type": "object"},
        },
        "required": ["run_id", "record"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert verdicts_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError):
        verdicts_tool.definition(source)


def test_the_description_names_every_kind_and_what_it_tells():
    description = verdicts_tool.definition(lambda: None).description
    for kind in KINDS + RUN_FILE_KINDS:
        assert kind in description
    assert "eval/verdicts.json" in description
    assert "events.ndjson is read for every record" in description
    assert 'outcome is "pass" only when every recorded result' in description
    assert "can have no check entry" in description
    assert "never part of the request" in description
    assert "corrected and sent again" in description
    assert "recomputed from the log as timings.compare computes it" in description
    assert "both attempts must be verified at board" in description
    assert "a comparison that does not count is still written" in description
    assert "refused for now" not in description


def test_no_kind_of_the_module_is_reserved():
    kinds = {
        value for name, value in vars(verdicts_tool).items() if name.startswith("KIND_")
    }
    assert kinds == set(KINDS[2:])
    assert not kinds & tools.RESERVED_KINDS
    assert verdicts_tool.KIND_CHECK_RESULT_INVALID == (
        checks_tool.KIND_CHECK_RESULT_INVALID
    )
    assert verdicts_tool.KIND_CHECK_UNFOUNDED == "check_unfounded"
    assert verdicts_tool.KIND_TIMING_RESULT_INVALID == (
        timings_tool.KIND_TIMING_RESULT_INVALID
    )


def test_a_valid_record_is_written_and_parses_back(root):
    with_hypotheses(root)
    source = Source(root)
    given = record()
    sent = copy.deepcopy(given)
    assert not eval_dir(root).exists()
    assert write(source, {"run_id": RUN, "record": sent}) == {}
    assert source.calls == 1
    assert sent == given
    content = verdicts_path(root).read_bytes()
    assert verdicts_file.parse(content) == given
    assert list(eval_dir(root).iterdir()) == [verdicts_path(root)]


def test_the_written_bytes_end_with_one_line_feed_and_hold_no_carriage_return(root):
    with_hypotheses(root)
    given = record(
        verdict("h1", [check_entry()], cause="line one\r\nline two\rend\n"),
        verdict("h2", [check_entry((1, 2, 1))]),
    )
    write(Source(root), {"run_id": RUN, "record": given})
    content = verdicts_path(root).read_bytes()
    assert content.endswith(b"}\n")
    assert not content.endswith(b"\n\n")
    assert b"\r" not in content
    assert not content.startswith(b"\xef\xbb\xbf")
    assert verdicts_file.parse(content) == given


def test_non_ascii_text_is_written_as_utf_8_and_round_trips(root):
    with_hypotheses(root)
    cause = "지연이 줄지 않았다 — é \U0001f600"
    given = record(
        verdict("h1", [check_entry()], cause=cause),
        verdict("h2", [check_entry((1, 2, 1))]),
        note={"키": "값"},
    )
    write(Source(root), {"run_id": RUN, "record": given})
    content = verdicts_path(root).read_bytes()
    assert cause.encode("utf-8") in content
    assert json.loads(content.decode("utf-8")) == given


def test_the_members_are_written_in_the_order_given(root):
    with_hypotheses(root)
    given = record()
    reordered = dict(reversed(list(given.items())))
    write(Source(root), {"run_id": RUN, "record": reordered})
    text = verdicts_path(root).read_text(encoding="utf-8")
    assert list(json.loads(text)) == list(reordered)
    assert text.index('"verdicts"') < text.index('"schema_version"')


def bad_record_cases():
    empty = record()
    empty["verdicts"] = []
    unknown_member = record()
    unknown_member["verdicts"][0]["note"] = "x"
    no_version = record()
    del no_version["schema_version"]
    return [
        ("extra member", {"run_id": RUN, "record": record(), "data_root": "/x"}),
        ("missing run_id", {"record": record()}),
        ("missing record", {"run_id": RUN}),
        ("empty request", {}),
        ("bad run_id", {"run_id": "Run A", "record": record()}),
        ("run_id not a string", {"run_id": 3, "record": record()}),
        ("record a list", {"run_id": RUN, "record": [record()]}),
        ("record a string", {"run_id": RUN, "record": "{}"}),
        ("record null", {"run_id": RUN, "record": None}),
        ("no verdict", {"run_id": RUN, "record": empty}),
        ("unknown verdict member", {"run_id": RUN, "record": unknown_member}),
        ("no schema_version", {"run_id": RUN, "record": no_version}),
        ("round 0", {"run_id": RUN, "record": record(round=0)}),
        ("other schema_version", {"run_id": RUN, "record": record(schema_version=2)}),
        ("run_id mismatch", {"run_id": RUN, "record": record(run_id="run-b")}),
        ("lone surrogate", {"run_id": RUN, "record": record(note="\ud800")}),
        ("not a number", {"run_id": RUN, "record": record(note=float("nan"))}),
    ]


@pytest.mark.parametrize(
    "request_",
    [case for _, case in bad_record_cases()],
    ids=[label for label, _ in bad_record_cases()],
)
def test_a_refused_request_or_record_asks_no_source_and_creates_nothing(root, request_):
    with_hypotheses(root)
    source = Source(root)
    refused = failure(source, request_)
    assert refused.kind == tools.KIND_INVALID_REQUEST
    assert source.calls == 0
    assert not eval_dir(root).exists()


def test_the_messages_of_invalid_request_name_the_member(root):
    source = Source(root)
    other = failure(source, {"run_id": RUN, "record": record(schema_version=2)})
    assert other.message == "record: schema_version: is 2, not 1"
    mismatch = failure(source, {"run_id": RUN, "record": record(run_id="run-b")})
    assert mismatch.message == (
        "record.run_id: must be the request's run_id 'run-a', got 'run-b'"
    )
    extra = failure(source, {"run_id": RUN, "record": record(), "x": 1})
    assert extra.message == "the request takes the members run_id, record only, not 'x'"
    lacking = failure(source, {"run_id": RUN})
    assert lacking.message == "the request lacks the member record"
    listed = failure(source, {"run_id": RUN, "record": []})
    assert listed.message == "record: must be an object, got list"
    assert source.calls == 0


def test_a_failing_source_is_no_data_root(root):
    with_hypotheses(root)
    source = FailingSource()
    refused = failure(source, {"run_id": RUN, "record": record()})
    assert refused.kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1
    assert not eval_dir(root).exists()


def test_missing_hypotheses_are_hypotheses_missing(root):
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_MISSING
    assert refused.message == f"{HYPOTHESES_PATH}: is missing"
    assert not (root / "runs").exists()


def test_hypotheses_missing_with_a_vanished_data_root_say_so(root, monkeypatch):
    with_hypotheses(root)
    real = layout.hypothesis_record

    def vanishing(data_root, run_id, round):
        os.rename(root, root.with_name("gone"))
        return real(data_root, run_id, round)

    monkeypatch.setattr(layout, "hypothesis_record", vanishing)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_MISSING
    assert refused.message == (
        f"{HYPOTHESES_PATH}: is missing: the data root is not an existing directory"
    )


def test_a_file_in_place_of_a_directory_is_hypotheses_missing(root):
    (root / "runs").mkdir()
    (root / "runs" / RUN).write_bytes(b"")
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_MISSING


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", verdicts_tool.KIND_HYPOTHESES_INVALID),
        (b"{not json}\n", verdicts_tool.KIND_HYPOTHESES_INVALID),
        (b'{"schema_version": 1}\n', verdicts_tool.KIND_HYPOTHESES_INVALID),
        (b'{"schema_version": 2}\n', verdicts_tool.KIND_HYPOTHESES_UNSUPPORTED),
    ],
)
def test_unusable_hypotheses_are_refused_by_kind(root, content, kind):
    path = layout.hypothesis_record(root, RUN, 1)
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == kind
    assert refused.message.startswith(f"{HYPOTHESES_PATH}: ")
    assert not eval_dir(root).exists()
    assert path.read_bytes() == content


def test_a_directory_at_the_place_of_the_hypotheses_is_hypotheses_invalid(root):
    layout.hypothesis_record(root, RUN, 1).mkdir(parents=True)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_INVALID
    assert refused.message == f"{HYPOTHESES_PATH}: is not a regular file"
    assert not eval_dir(root).exists()


def test_a_failed_read_of_the_hypotheses_is_hypotheses_unreadable(root, monkeypatch):
    with_hypotheses(root)

    def denied(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(Path, "read_bytes", denied)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_UNREADABLE
    assert refused.message == (
        f"{HYPOTHESES_PATH}: could not be read: PermissionError: Permission denied"
    )
    assert str(root) not in refused.message
    assert not eval_dir(root).exists()


@pytest.mark.parametrize(
    "given",
    [
        record(verdict("h1", [check_entry()])),
        record(*record()["verdicts"], verdict("h3", [check_entry()])),
        record(
            verdict("h1", [check_entry(), check_entry((0, 1, 1)), comparison()]),
            verdict("h2", [check_entry((1, 2, 1))]),
        ),
        record(
            verdict(
                "h1",
                [check_entry(), check_entry((0, 1, 1)), comparison()],
                value="refuted",
            ),
            verdict("h2", [check_entry((1, 2, 1))]),
        ),
    ],
    ids=["missing verdict", "unknown id", "inconclusive by rule supported", "refuted"],
)
def test_a_record_against_the_hypotheses_is_verdicts_mismatch(root, given):
    with_hypotheses(root)
    refused = failure(Source(root), {"run_id": RUN, "record": given})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_MISMATCH
    assert refused.message.startswith("record: verdicts")
    assert not eval_dir(root).exists()


def test_the_mismatch_message_names_the_broken_rule(root):
    with_hypotheses(root)
    refused = failure(
        Source(root), {"run_id": RUN, "record": record(verdict("h1", [check_entry()]))}
    )
    assert refused.message == (
        "record: verdicts: must hold a verdict for hypothesis 'h2' "
        "(hypotheses[1].id of the hypothesis record)"
    )


def test_hypotheses_of_another_run_id_are_verdicts_mismatch(root):
    path = layout.hypothesis_record(root, RUN, 1)
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps(HYPOTHESES | {"run_id": "run-b"}).encode())
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_MISMATCH
    assert refused.message.startswith("record: run_id: ")
    assert not eval_dir(root).exists()


def test_a_taken_name_is_verdicts_exist_and_the_file_is_unchanged(root):
    with_hypotheses(root)
    source = Source(root)
    write(source, {"run_id": RUN, "record": record()})
    before = verdicts_path(root).read_bytes()
    other = record(
        verdict("h1", [check_entry()], cause="another cause"),
        verdict("h2", [check_entry((1, 2, 1))]),
    )
    refused = failure(source, {"run_id": RUN, "record": other})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_EXIST
    assert refused.message == f"{VERDICTS_PATH}: is already there; nothing was replaced"
    assert verdicts_path(root).read_bytes() == before
    assert list(eval_dir(root).iterdir()) == [verdicts_path(root)]


def test_a_failed_write_is_verdicts_not_written(root, monkeypatch):
    with_hypotheses(root)

    def full(path, content):
        raise OSError(errno.ENOSPC, "No space left on device", str(path))

    monkeypatch.setattr(once_write, "write_once", full)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_NOT_WRITTEN
    assert refused.message == (
        f"{VERDICTS_PATH}: was not written: OSError: No space left on device"
    )
    assert str(root) not in refused.message
    assert not verdicts_path(root).exists()


def test_a_vanished_data_root_is_named_without_its_path(root, monkeypatch):
    with_hypotheses(root)
    real = verdicts_file.write

    def vanishing(data_root, content):
        os.rename(root, root.with_name("gone"))
        return real(data_root, content)

    monkeypatch.setattr(verdicts_file, "write", vanishing)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_NOT_WRITTEN
    assert refused.message == (
        f"{VERDICTS_PATH}: was not written: FileNotFoundError: "
        "the data root is not an existing directory"
    )


# The log check of ADR-0131 decision 5


def log_path(root):
    return layout.run_file(root, RUN, "events.ndjson")


def pair(first=(), second=()):
    return record(verdict("h1", list(first)), verdict("h2", list(second)))


def written(root, given):
    assert write(Source(root), {"run_id": RUN, "record": given}) == {}
    assert verdicts_file.parse(verdicts_path(root).read_bytes()) == given


def refused(root, given):
    log = log_path(root)
    before = log.read_bytes() if log.is_file() else None
    error = failure(Source(root), {"run_id": RUN, "record": given})
    assert not eval_dir(root).exists()
    if before is not None:
        assert log.read_bytes() == before
    return error


def unspent(root, at):
    data = {"step": BOARD, "execution": 1}
    events.append(root, RUN, journal.STEP_ENDED, data, **numbers(*at))


@pytest.mark.parametrize(
    ("results", "outcome"),
    [
        ([PASS], "pass"),
        ([PASS, PASS], "pass"),
        ([FAIL, PASS], "fail"),
        ([PASS, BROKEN], "broken"),
        ([FAIL, BROKEN], "fail"),
        ([FAIL, BROKEN], "broken"),
    ],
    ids=["one pass", "two passes", "fail then pass", "broken", "fail", "broken of two"],
)
def test_a_founded_check_entry_is_written(root, results, outcome):
    with_hypotheses(root, log=False)
    for execution, result in enumerate(results, 1):
        check(root, execution, result=result)
    written(root, pair([check_entry(outcome=outcome)]))


def test_a_pass_beside_an_open_identity_is_founded(root):
    with_hypotheses(root, log=False)
    check(root, 1, result=PASS)
    start(root, 2)
    written(root, pair([check_entry()]))


def test_two_end_lines_of_one_execution_both_passing_found_a_pass(root):
    with_hypotheses(root, log=False)
    start(root)
    end(root, result=PASS)
    end(root, result=PASS)
    written(root, pair([check_entry()]))


def test_a_failure_end_line_beside_a_pass_does_not_count(root):
    with_hypotheses(root, log=False)
    check(root, 1, failure=UNSTARTED)
    check(root, 2, result=PASS)
    written(root, pair([check_entry()]))


def test_a_record_without_a_check_entry_and_without_a_log_is_written(root):
    with_hypotheses(root, log=False)
    written(root, pair())
    assert not log_path(root).exists()


def test_entries_of_an_earlier_round_are_founded_on_its_lines(root):
    with_hypotheses(root, log=False)
    check(root, at=(0, 1, 1), result=PASS)
    check(root, at=(0, 1, 1), step=SIM, result=BROKEN)
    written(
        root,
        pair([check_entry((0, 1, 1)), check_entry((0, 1, 1), "sim", "broken")]),
    )


def test_a_torn_tail_is_no_line(root):
    with_hypotheses(root)
    raw(root, line({"step": BOARD, "execution": 2, "spend": {}, "result": FAIL})[:-1])
    written(root, record())


def test_a_pass_against_a_recorded_fail_is_check_unfounded(root):
    with_hypotheses(root, log=False)
    check(root, 1, result=FAIL)
    check(root, 2, result=PASS)
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message == (
        f"record.verdicts[0].evidence[0]: outcome pass is not founded: {LOG} holds "
        "the outcomes fail, pass of round 1, candidate 1, attempt 1 at board, "
        "and pass needs every result to pass"
    )


@pytest.mark.parametrize(
    ("results", "outcome"),
    [([FAIL], "broken"), ([PASS], "fail"), ([PASS, PASS], "broken")],
)
def test_an_outcome_the_log_does_not_hold_is_check_unfounded(root, results, outcome):
    with_hypotheses(root, log=False)
    for execution, result in enumerate(results, 1):
        check(root, execution, result=result)
    error = refused(root, pair([check_entry(outcome=outcome)]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    held = results[0]["outcome"]
    assert error.message == (
        f"record.verdicts[0].evidence[0]: outcome {outcome} is not founded: "
        f"{LOG} holds only the outcomes {held} of round 1, candidate 1, "
        "attempt 1 at board"
    )


def no_line(root):
    pass


def only_a_failure(root):
    check(root, failure=UNSTARTED)


def only_open(root):
    start(root)
    start(root, 2)


def other_point(root):
    check(root, step=SIM, result=PASS)


def other_candidate(root):
    check(root, at=(1, 2, 1), result=PASS)


def other_attempt(root):
    check(root, at=(1, 1, 2), result=PASS)


def other_round(root):
    check(root, at=(0, 1, 1), result=PASS)


@pytest.mark.parametrize(
    "lines",
    [
        no_line,
        only_a_failure,
        only_open,
        other_point,
        other_candidate,
        other_attempt,
        other_round,
    ],
)
@pytest.mark.parametrize("outcome", ["pass", "fail"])
def test_an_attempt_and_point_without_a_result_is_check_unfounded(root, lines, outcome):
    with_hypotheses(root, log=False)
    lines(root)
    error = refused(root, pair([check_entry(outcome=outcome)]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message == (
        f"record.verdicts[0].evidence[0]: {LOG} holds no result of round 1, "
        "candidate 1, attempt 1 at board, so it can have no check entry"
    )


def test_a_check_entry_with_a_missing_log_is_check_unfounded(root):
    with_hypotheses(root, log=False)
    error = refused(root, pair([], [check_entry((1, 2, 1), "sim")]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message.startswith("record.verdicts[1].evidence[0]: ")
    assert not log_path(root).exists()


def test_the_first_unfounded_entry_in_record_order_decides(root):
    with_hypotheses(root, log=False)
    check(root, result=PASS)
    given = pair(
        [check_entry(), check_entry(point="sim"), check_entry((1, 1, 2))],
        [check_entry((1, 2, 1))],
    )
    error = refused(root, given)
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message.startswith("record.verdicts[0].evidence[1]: ")
    later = pair([check_entry()], [check_entry((1, 2, 1)), check_entry(point="sim")])
    assert refused(root, later).message.startswith("record.verdicts[1].evidence[0]: ")


def test_a_refused_record_corrected_is_then_written(root):
    with_hypotheses(root, log=False)
    check(root, 1, result=FAIL)
    check(root, 2, result=PASS)
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    written(root, pair([check_entry(outcome="fail")]))


@pytest.mark.parametrize(
    "at",
    [(1, 1, 2), (1, 3, 1), (0, 1, 1)],
    ids=["other attempt", "other candidate", "other round"],
)
def test_a_bad_result_out_of_scope_is_no_failure(root, at):
    with_hypotheses(root)
    check(root, at=at, result={"no": "outcome"})
    check(root, at=at, step=SIM, result={"outcome": "PASS"})
    written(root, record())


@pytest.mark.parametrize(
    ("result", "problem"),
    [
        ({"no": "outcome"}, "data.result: lacks the member outcome"),
        (
            {"outcome": "PASS"},
            "data.result.outcome: must be one of pass, fail, broken, got str 'PASS'",
        ),
    ],
)
def test_a_bad_result_of_a_named_attempt_is_check_result_invalid(root, result, problem):
    with_hypotheses(root)
    check(root, 2, at=(1, 2, 1), step=SIM, result=result)
    error = refused(root, record())
    assert error.kind == verdicts_tool.KIND_CHECK_RESULT_INVALID
    assert error.message == f"{LOG}: line 8: {problem}"


def test_a_bad_result_beside_founding_lines_is_check_result_invalid(root):
    with_hypotheses(root, log=False)
    check(root, 1, result={"outcome": None})
    check(root, 2, result=PASS)
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_RESULT_INVALID
    assert error.message.startswith(f"{LOG}: line 2: ")


def test_a_broken_step_line_before_a_named_bad_result_decides(root):
    with_hypotheses(root)
    unspent(root, (1, 1, 3))
    check(root, at=(1, 2, 1), step=SIM, result={"no": "outcome"})
    error = refused(root, record())
    assert error.kind == tools.KIND_RUN_FILE_INVALID
    assert error.message == f"{LOG}: line 7: data: lacks the member spend"


def test_a_named_bad_result_before_a_broken_step_line_decides(root):
    with_hypotheses(root)
    check(root, at=(1, 2, 1), step=SIM, result={"no": "outcome"})
    unspent(root, (1, 1, 3))
    error = refused(root, record())
    assert error.kind == verdicts_tool.KIND_CHECK_RESULT_INVALID
    assert error.message == f"{LOG}: line 8: data.result: lacks the member outcome"


@pytest.mark.parametrize("given", [record(), pair()], ids=["checks", "no check"])
def test_a_broken_step_line_of_an_attempt_no_entry_names_is_run_file_invalid(
    root, given
):
    with_hypotheses(root)
    unspent(root, (1, 1, 3))
    error = refused(root, given)
    assert error.kind == tools.KIND_RUN_FILE_INVALID
    assert error.message == f"{LOG}: line 7: data: lacks the member spend"


@pytest.mark.parametrize("where", ["first", "last"])
@pytest.mark.parametrize("given", [record(), pair()], ids=["checks", "no check"])
def test_a_damaged_line_anywhere_is_run_file_invalid(root, where, given):
    with_hypotheses(root, log=False)
    if where == "first":
        raw(root, b"{not json}\n")
    founding(root)
    if where == "last":
        raw(root, b"\xff\n")
    error = refused(root, given)
    assert error.kind == tools.KIND_RUN_FILE_INVALID
    number = 1 if where == "first" else 7
    assert error.message.startswith(f"{LOG}: line {number}: is damaged")


def test_a_directory_at_the_place_of_the_log_is_run_file_invalid(root):
    with_hypotheses(root, log=False)
    log_path(root).mkdir()
    error = refused(root, pair())
    assert error.kind == tools.KIND_RUN_FILE_INVALID
    assert error.message == f"{LOG}: is not a regular file"


def test_a_line_of_another_version_is_run_file_unsupported(root):
    with_hypotheses(root)
    raw(root, line({"anything": 1}, version=2))
    error = refused(root, record())
    assert error.kind == tools.KIND_RUN_FILE_UNSUPPORTED
    assert error.message.startswith(f"{LOG}: line 7: ")


def test_a_data_root_gone_since_the_source_is_run_file_missing(root, monkeypatch):
    with_hypotheses(root)
    real = events.read

    def removing(data_root, run_id, position=0):
        shutil.rmtree(root)
        return real(data_root, run_id, position)

    monkeypatch.setattr(events, "read", removing)
    error = failure(Source(root), {"run_id": RUN, "record": record()})
    assert error.kind == tools.KIND_RUN_FILE_MISSING
    assert error.message == (
        f"{LOG}: is missing: the data root is not an existing directory"
    )
    assert not root.exists()


def test_a_failed_read_of_the_log_is_run_file_unreadable(root, monkeypatch):
    with_hypotheses(root)

    def denied(data_root, run_id, position=0):
        raise PermissionError(errno.EACCES, "Permission denied", "secret/path")

    monkeypatch.setattr(events, "read", denied)
    error = refused(root, pair())
    assert error.kind == tools.KIND_RUN_FILE_UNREADABLE
    assert error.message == (
        f"{LOG}: could not be read: PermissionError: Permission denied"
    )


def test_the_tool_appends_nothing_to_the_log(root, monkeypatch):
    with_hypotheses(root)
    before = log_path(root).read_bytes()
    monkeypatch.setattr(events, "append", None)
    written(root, record())
    assert log_path(root).read_bytes() == before


def damaged(root):
    raw(root, b"{not json}\n")


@pytest.mark.parametrize(
    ("given", "kind"),
    [
        (record(schema_version=2), tools.KIND_INVALID_REQUEST),
        (record(verdict("h1", [check_entry()])), verdicts_tool.KIND_VERDICTS_MISMATCH),
        (
            record(verdict("h1", [check_entry(), comparison(point="sim")])),
            verdicts_tool.KIND_VERDICTS_MISMATCH,
        ),
    ],
    ids=["invalid_request", "verdicts_mismatch", "verdicts_mismatch with comparison"],
)
def test_an_earlier_check_wins_over_a_damaged_log(root, given, kind):
    with_hypotheses(root)
    damaged(root)
    assert refused(root, given).kind == kind


def test_missing_hypotheses_win_over_a_damaged_log(root):
    damaged(root)
    error = refused(root, record())
    assert error.kind == verdicts_tool.KIND_HYPOTHESES_MISSING


def test_the_default_registry_holds_verdicts_write(root):
    registry = default_registry(lambda: root)
    assert "verdicts.write" in registry.names()
    with_hypotheses(root)
    assert (
        tools.call(registry, "verdicts.write", {"run_id": RUN, "record": record()})
        == {}
    )
    assert verdicts_path(root).is_file()


def _mcp(request_id, method, params):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return json.dumps(document).encode() + b"\n"


def test_the_mcp_front_lists_and_serves_verdicts_write(root):
    with_hypotheses(root)
    data = b"".join(
        [
            _mcp(1, "tools/list", {}),
            _mcp(
                2,
                "tools/call",
                {
                    "name": "verdicts_write",
                    "arguments": {"run_id": RUN, "record": record()},
                },
            ),
            _mcp(
                3,
                "tools/call",
                {
                    "name": "verdicts_write",
                    "arguments": {"run_id": RUN, "record": record()},
                },
            ),
        ]
    )
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(lambda: root),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    listed, written, taken = (
        json.loads(line) for line in stdout.getvalue().splitlines()
    )
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert "verdicts_write" in names
    assert mcp_front.mcp_name("verdicts.write") == "verdicts_write"
    assert written["result"]["isError"] is False
    assert json.loads(written["result"]["content"][0]["text"]) == {}
    assert taken["result"]["isError"] is True
    error = json.loads(taken["result"]["content"][0]["text"])["error"]
    assert error["kind"] == "verdicts_exist"


# The comparison checks of ADR-0140 decision 5

T_SIM = "sim_run_timing"
T_BOARD = "board_run_timing"
SLOW = [1000, 1001, 999, 1000, 1002]
FAST = [500, 501, 499, 500, 502]
CLOSE = [1000, 1002, 1001, 999, 1000]
CLASS_II = {"kind": "operation_failure_invalid", "message": "no answer"}
MEASURED = (1, 1, 1)
AGAINST = (0, 1, 1)


def timing(outcome="converged", intervals=SLOW, m=4, k=4, n=4):
    return run_result.completed(
        outcome,
        intervals_ns=intervals,
        resolution_ns=1,
        memory_bytes=None,
        m=m,
        k=k,
        n=n,
        n_max=10,
        sample_form="interval",
        bound=None,
    )


def broken_timing():
    return run_result.broken(
        "time_limit", m=4, k=4, n=4, n_max=10, sample_form="interval", bound=None
    )


def timed(root, measured=FAST, against=SLOW, step=T_BOARD):
    check(root, at=MEASURED, step=step, result=timing(intervals=measured))
    check(root, at=AGAINST, step=step, result=timing(intervals=against))


def counted_log(root, measured=FAST, against=SLOW):
    with_hypotheses(root)
    check(root, at=AGAINST, result=PASS)
    timed(root, measured, against)


def counted(difference="lower", value="supported", extra=()):
    return record(
        verdict(
            "h1",
            [check_entry(), check_entry(AGAINST), comparison(difference=difference)]
            + list(extra),
            value=value,
            cause="the comparison at board",
        ),
        verdict("h2", [check_entry((1, 2, 1))]),
    )


def encoded(given):
    return (json.dumps(given, ensure_ascii=False, indent=2) + "\n").encode()


def test_a_counted_lower_comparison_is_written_as_supported(root):
    counted_log(root)
    given = counted()
    written(root, given)
    assert verdicts_path(root).read_bytes() == encoded(given)


def test_a_not_converged_against_enters_and_counts(root):
    with_hypotheses(root)
    check(root, at=AGAINST, result=PASS)
    check(root, at=MEASURED, step=T_BOARD, result=timing(intervals=FAST))
    check(root, at=AGAINST, step=T_BOARD, result=timing("not_converged", SLOW))
    written(root, counted())


def test_a_counted_higher_comparison_is_written_as_refuted(root):
    counted_log(root, measured=SLOW, against=FAST)
    written(root, counted("higher", "refuted"))


def test_a_counted_not_different_comparison_is_written_as_inconclusive(root):
    counted_log(root, measured=CLOSE, against=SLOW)
    written(root, counted("not_different", "inconclusive"))


def test_a_sim_comparison_without_a_check_entry_is_written_uncounted(root):
    with_hypotheses(root)
    timed(root, step=T_SIM)
    written(root, pair([comparison(point="sim")]))


@pytest.mark.parametrize("entries", [[], [check_entry()]], ids=["none", "one"])
def test_a_board_comparison_without_both_pass_entries_is_written_unverified(
    root, entries
):
    with_hypotheses(root)
    start(root, 2)
    check(root, at=AGAINST, result=FAIL)
    timed(root)
    written(root, pair([*entries, comparison()]))


def test_a_comparison_of_the_second_hypothesis_is_founded(root):
    with_hypotheses(root)
    check(root, at=(1, 2, 1), step=T_BOARD, result=timing(intervals=FAST))
    check(root, at=AGAINST, step=T_BOARD, result=timing(intervals=SLOW))
    entry = comparison() | {"measured": ref(1, 2, 1)}
    written(root, pair([], [entry]))


def several(root):
    timed(root)
    check(root, 2, at=MEASURED, step=T_BOARD, result=timing(intervals=FAST))


def open_identity(root):
    timed(root)
    start(root, 2, at=AGAINST, step=T_BOARD)


def a_failure(root):
    timed(root)
    check(root, 2, at=AGAINST, step=T_BOARD, failure=CLASS_II)


def only_against(root):
    check(root, at=AGAINST, step=T_BOARD, result=timing())


def only_broken(root):
    check(root, at=MEASURED, step=T_BOARD, result=broken_timing())
    check(root, at=AGAINST, step=T_BOARD, result=timing())


def other_shape(root):
    check(root, at=MEASURED, step=T_BOARD, result=timing(intervals=FAST, m=8))
    check(root, at=AGAINST, step=T_BOARD, result=timing())


def out_of_domain(root):
    check(root, at=MEASURED, step=T_BOARD, result=timing(intervals=[10**310] * 5))
    check(root, at=AGAINST, step=T_BOARD, result=timing())


@pytest.mark.parametrize(
    ("lines", "kind"),
    [
        (several, timings_tool.KIND_MEASUREMENT_SEVERAL),
        (open_identity, timings_tool.KIND_MEASUREMENT_UNKNOWN),
        (a_failure, timings_tool.KIND_MEASUREMENT_UNKNOWN),
        (only_against, timings_tool.KIND_MEASUREMENT_MISSING),
        (only_broken, timings_tool.KIND_MEASUREMENT_MISSING),
        (other_shape, timings_tool.KIND_SHAPES_DIFFER),
        (out_of_domain, timings_tool.KIND_SAMPLES_OUT_OF_DOMAIN),
    ],
)
def test_every_kind_of_compare_is_comparison_unfounded(root, lines, kind):
    with_hypotheses(root)
    lines(root)
    error = refused(root, pair([comparison()]))
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNFOUNDED
    assert error.message.startswith(f"record.verdicts[0].evidence[0]: {kind}: {LOG}: ")
    assert isinstance(error.__cause__, ToolFailure)
    assert error.__cause__.kind == kind


def test_a_comparison_with_a_missing_log_is_comparison_unfounded(root):
    with_hypotheses(root, log=False)
    error = refused(root, pair([comparison(point="sim")]))
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNFOUNDED
    assert error.message == (
        "record.verdicts[0].evidence[0]: measurement_missing: "
        f"{LOG}: measured (round 1, candidate 1, attempt 1) at sim_run_timing: "
        "has no measurement"
    )
    assert not log_path(root).exists()


def test_another_difference_than_the_log_gives_is_comparison_unfounded(root):
    with_hypotheses(root)
    timed(root)
    error = refused(root, pair([comparison(difference="higher")]))
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNFOUNDED
    assert error.message == (
        "record.verdicts[0].evidence[0]: difference higher is not founded: "
        f"{LOG} gives lower"
    )


def test_lines_of_other_kinds_are_not_held_to_the_timing_rule(root):
    with_hypotheses(root)
    data = {"step": T_BOARD, "result": {"outcome": "x"}}
    events.append(root, RUN, "round_started", data, **numbers(*MEASURED))
    timed(root)
    written(root, pair([comparison()]))


@pytest.mark.parametrize(
    "kind", [tools.KIND_RUN_FILE_INVALID, verdicts_tool.KIND_TIMING_RESULT_INVALID]
)
def test_another_kind_of_compare_propagates_as_it_is(root, monkeypatch, kind):
    with_hypotheses(root)
    timed(root)

    def failing(*arguments):
        raise ToolFailure(kind, "from compare")

    monkeypatch.setattr(timings_tool, "compare", failing)
    error = refused(root, pair([comparison()]))
    assert (error.kind, error.message) == (kind, "from compare")


def test_a_refused_comparison_corrected_is_then_written(root):
    with_hypotheses(root)
    timed(root)
    refused(root, pair([comparison(difference="not_different")]))
    written(root, pair([comparison()]))


def test_a_broken_timing_line_beside_a_converged_one_is_founded(root):
    counted_log(root)
    check(root, 2, at=MEASURED, step=T_BOARD, result=broken_timing())
    written(root, counted())


def test_the_first_unfounded_comparison_in_record_order_decides(root):
    with_hypotheses(root)
    timed(root)
    missing = comparison() | {"measured": ref(1, 2, 1)}
    given = pair([comparison(), comparison(point="sim")], [missing])
    error = refused(root, given)
    assert error.message.startswith("record.verdicts[0].evidence[1]: ")
    later = pair([comparison()], [missing, missing | {"point": "sim"}])
    error = refused(root, later)
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNFOUNDED
    assert error.message.startswith("record.verdicts[1].evidence[0]: ")


def test_an_unfounded_check_entry_wins_over_an_earlier_unfounded_comparison(root):
    with_hypotheses(root)
    given = pair([comparison(difference="higher"), check_entry((1, 1, 2))])
    error = refused(root, given)
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message.startswith("record.verdicts[0].evidence[1]: ")


def test_an_unfounded_comparison_wins_over_an_earlier_unverified_one(root):
    counted_log(root)
    start(root, 2)
    error = refused(root, counted(extra=[comparison(point="sim")]))
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNFOUNDED
    assert error.message.startswith("record.verdicts[0].evidence[3]: ")


def test_a_measured_with_an_open_board_check_is_comparison_unverified(root):
    counted_log(root)
    start(root, 2)
    error = refused(root, counted())
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert error.message == (
        "record.verdicts[0].evidence[2]: the comparison counts, but its measured "
        "(round 1, candidate 1, attempt 1) is undetermined at board, where both "
        "must be verified"
    )


def test_an_against_with_a_class_ii_failure_is_comparison_unverified(root):
    counted_log(root)
    check(root, 2, at=AGAINST, failure=CLASS_II)
    error = refused(root, counted())
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert error.message == (
        "record.verdicts[0].evidence[2]: the comparison counts, but its against "
        "(round 0, candidate 1, attempt 1) is undetermined at board, where both "
        "must be verified"
    )


def test_an_against_with_a_class_i_failure_beside_a_pass_is_verified(root):
    counted_log(root)
    check(root, 2, at=AGAINST, failure=UNSTARTED)
    written(root, counted())


def test_measured_is_reported_before_against(root):
    counted_log(root)
    start(root, 2)
    start(root, 2, at=AGAINST)
    error = refused(root, counted())
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert "its measured (round 1, candidate 1, attempt 1)" in error.message


def unverified_pair(root, first_counted):
    counted_log(root)
    start(root, 2, at=AGAINST)
    check(root, at=(1, 2, 1), step=T_BOARD, result=timing(intervals=FAST))
    second = comparison() | {"measured": ref(1, 2, 1)}
    first = [check_entry(), comparison()]
    if first_counted:
        first.insert(1, check_entry(AGAINST))
    return record(
        verdict("h1", first, value="supported" if first_counted else "inconclusive"),
        verdict(
            "h2",
            [check_entry((1, 2, 1)), check_entry(AGAINST), second],
            value="supported",
        ),
    )


def test_the_first_unverified_comparison_in_record_order_decides(root):
    error = refused(root, unverified_pair(root, first_counted=True))
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert error.message.startswith("record.verdicts[0].evidence[2]: ")


def test_a_comparison_that_does_not_count_is_not_held_to_the_standing(root):
    error = refused(root, unverified_pair(root, first_counted=False))
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert error.message.startswith("record.verdicts[1].evidence[2]: ")


SHAPE = {"m": 4, "k": 4, "n": 4}
INVALID_TIMINGS = [
    (
        {"outcome": "pass", "shape": SHAPE, "intervals_ns": SLOW},
        "data.result.outcome: must be one of converged, not_converged, broken",
    ),
    ({"no": "outcome"}, "data.result: lacks the member outcome"),
    (
        {"outcome": "converged", "shape": SHAPE, "intervals_ns": SLOW[:4]},
        "data.result.intervals_ns: must be a list of at least 5 ints",
    ),
    (
        {"outcome": "not_converged", "shape": SHAPE | {"k": 0}, "intervals_ns": SLOW},
        "data.result.shape: must be an object of exactly m, k and n",
    ),
]


@pytest.mark.parametrize(("result", "problem"), INVALID_TIMINGS)
@pytest.mark.parametrize("side", [MEASURED, AGAINST], ids=["measured", "against"])
def test_an_invalid_timing_result_of_a_named_side_is_timing_result_invalid(
    root, result, problem, side
):
    with_hypotheses(root)
    timed(root)
    end(root, 2, at=side, step=T_BOARD, result=result)
    error = refused(root, pair([comparison()]))
    assert error.kind == verdicts_tool.KIND_TIMING_RESULT_INVALID
    assert error.message.startswith(f"{LOG}: line 11: {problem}")


def test_an_invalid_timing_result_at_the_sim_point_is_timing_result_invalid(root):
    with_hypotheses(root)
    timed(root, step=T_SIM)
    end(root, 2, at=MEASURED, step=T_SIM, result={"outcome": "converged"})
    error = refused(root, pair([comparison(point="sim")]))
    assert error.kind == verdicts_tool.KIND_TIMING_RESULT_INVALID
    assert (
        error.message == f"{LOG}: line 11: data.result: lacks the member intervals_ns"
    )


@pytest.mark.parametrize(
    ("at", "step"),
    [((1, 1, 2), T_BOARD), ((1, 2, 1), T_BOARD), (MEASURED, T_SIM)],
    ids=["other attempt", "other candidate", "other point"],
)
def test_an_invalid_timing_result_no_comparison_names_is_no_failure(root, at, step):
    with_hypotheses(root)
    timed(root)
    check(root, at=at, step=step, result={"outcome": "converged", "intervals_ns": [1]})
    written(root, pair([comparison()]))


def test_a_check_line_of_a_compared_attempt_is_not_held_to_the_timing_rule(root):
    with_hypotheses(root)
    timed(root)
    written(root, pair([comparison()]))


def test_a_timing_line_of_a_checked_attempt_is_not_held_to_the_check_rule(root):
    with_hypotheses(root)
    timed(root)
    written(root, pair([check_entry()]))


def bad_check(root):
    end(root, 2, at=MEASURED, result={"no": "outcome"})


def bad_timing(root):
    end(root, 2, at=MEASURED, step=T_BOARD, result={"outcome": "converged"})


def bad_step(root):
    unspent(root, (1, 1, 3))


@pytest.mark.parametrize(
    ("first", "second", "kind"),
    [
        (bad_timing, bad_check, verdicts_tool.KIND_TIMING_RESULT_INVALID),
        (bad_check, bad_timing, verdicts_tool.KIND_CHECK_RESULT_INVALID),
        (bad_step, bad_timing, tools.KIND_RUN_FILE_INVALID),
        (bad_step, bad_check, tools.KIND_RUN_FILE_INVALID),
        (bad_timing, bad_step, verdicts_tool.KIND_TIMING_RESULT_INVALID),
    ],
    ids=[
        "timing then check",
        "check then timing",
        "step then timing",
        "step then check",
        "timing then step",
    ],
)
def test_the_first_failing_step_line_decides(root, first, second, kind):
    with_hypotheses(root)
    timed(root)
    first(root)
    second(root)
    error = refused(root, pair([check_entry(), comparison()]))
    assert error.kind == kind
    assert error.message.startswith(f"{LOG}: line 11: ")


def test_an_invalid_timing_result_wins_over_an_unfounded_check_entry(root):
    with_hypotheses(root)
    timed(root)
    bad_timing(root)
    error = refused(root, pair([check_entry((1, 1, 2)), comparison()]))
    assert error.kind == verdicts_tool.KIND_TIMING_RESULT_INVALID


@pytest.mark.parametrize(
    ("given", "kind"),
    [
        (
            record(verdict("h1", [comparison()])),
            verdicts_tool.KIND_VERDICTS_MISMATCH,
        ),
        (record(schema_version=2), tools.KIND_INVALID_REQUEST),
    ],
    ids=["verdicts_mismatch", "invalid_request"],
)
def test_an_earlier_check_wins_over_an_invalid_timing_result(root, given, kind):
    with_hypotheses(root)
    timed(root)
    bad_timing(root)
    assert refused(root, given).kind == kind


def test_missing_hypotheses_win_over_an_invalid_timing_result(root):
    timed(root)
    bad_timing(root)
    error = refused(root, pair([comparison()]))
    assert error.kind == verdicts_tool.KIND_HYPOTHESES_MISSING


@pytest.mark.parametrize("where", ["first", "last"])
def test_a_damaged_log_with_a_comparison_is_run_file_invalid(root, where):
    with_hypotheses(root, log=False)
    if where == "first":
        damaged(root)
    founding(root)
    timed(root)
    if where == "last":
        damaged(root)
    error = refused(root, pair([comparison()]))
    assert error.kind == tools.KIND_RUN_FILE_INVALID
    number = 1 if where == "first" else 11
    assert error.message.startswith(f"{LOG}: line {number}: is damaged")


def test_the_default_registry_writes_a_counted_comparison(root):
    counted_log(root)
    registry = default_registry(lambda: root)
    given = counted()
    request = {"run_id": RUN, "record": given}
    assert tools.call(registry, "verdicts.write", request) == {}
    assert verdicts_path(root).read_bytes() == encoded(given)


def test_the_mcp_front_writes_a_counted_comparison(root):
    counted_log(root)
    given = counted()
    arguments = {"run_id": RUN, "record": given}
    data = _mcp(1, "tools/call", {"name": "verdicts_write", "arguments": arguments})
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(lambda: root),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    answer = json.loads(stdout.getvalue())
    assert answer["result"]["isError"] is False
    assert verdicts_path(root).read_bytes() == encoded(given)


# The lines of a bf16 check (ADR-0178 decision 1)

BF16_SIM = "correctness_check_bf16_sim"
BF16_BOARD = "correctness_check_bf16_board"


def bf16(failed=0, kind="rmsnorm"):
    dims = {"gemm": (4, 2, 8), "rope": (2, 3, 8), "sdpa_kv_cache": (2, 3, 4, 2, 8)}.get(
        kind, (2, 8)
    )
    entry = (failed, 0, 0) if kind == "sdpa_kv_cache" else (failed, 0)
    return check_result.bf16_completed(
        kind, dims, draws=1, rtol=0.01, atol=0.001, counts=[entry]
    )


def bf16_founding(root):
    check(root, step=BF16_BOARD, result=bf16())
    check(root, at=(1, 2, 1), step=BF16_SIM, result=bf16(1))
    check(root, at=(1, 2, 1), step=BF16_BOARD, result=bf16())


@pytest.mark.parametrize("kind", check_result.BF16_KINDS)
def test_check_entries_of_a_bf16_run_are_founded_at_both_points(root, kind):
    with_hypotheses(root, log=False)
    check(root, step=BF16_BOARD, result=bf16(kind=kind))
    check(root, at=(1, 2, 1), step=BF16_SIM, result=bf16(1, kind))
    written(root, record())


def test_a_bf16_pass_against_a_bf16_fail_is_check_unfounded(root):
    with_hypotheses(root, log=False)
    check(root, 1, step=BF16_BOARD, result=bf16(1))
    check(root, 2, step=BF16_BOARD, result=bf16())
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message == (
        f"record.verdicts[0].evidence[0]: outcome pass is not founded: {LOG} holds "
        "the outcomes fail, pass of round 1, candidate 1, attempt 1 at board, "
        "and pass needs every result to pass"
    )


def test_a_bf16_line_of_the_other_point_founds_nothing(root):
    with_hypotheses(root, log=False)
    check(root, step=BF16_SIM, result=bf16())
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert error.message.endswith(
        "holds no result of round 1, candidate 1, attempt 1 at board, so it can "
        "have no check entry"
    )


def test_the_results_of_both_values_of_a_point_found_an_entry_together(root):
    with_hypotheses(root, log=False)
    check(root, 1, result=PASS)
    check(root, 1, step=BF16_BOARD, result=bf16(1))
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED
    assert "holds the outcomes pass, fail of round 1" in error.message
    written(root, pair([check_entry(outcome="fail")]))


def test_both_values_passing_found_a_pass(root):
    with_hypotheses(root, log=False)
    check(root, 1, result=PASS)
    check(root, 1, step=BF16_BOARD, result=bf16())
    written(root, pair([check_entry()]))


def bf16_counted_log(root):
    with_hypotheses(root, log=False)
    bf16_founding(root)
    check(root, at=AGAINST, step=BF16_BOARD, result=bf16())
    timed(root)


def test_a_counted_comparison_over_bf16_board_checks_is_written(root):
    bf16_counted_log(root)
    given = counted()
    written(root, given)
    assert verdicts_path(root).read_bytes() == encoded(given)


def test_an_open_bf16_board_check_makes_a_counted_comparison_unverified(root):
    bf16_counted_log(root)
    start(root, 2, step=BF16_BOARD)
    error = refused(root, counted())
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert error.message == (
        "record.verdicts[0].evidence[2]: the comparison counts, but its measured "
        "(round 1, candidate 1, attempt 1) is undetermined at board, where both "
        "must be verified"
    )


def test_a_failure_under_the_other_value_makes_a_comparison_unverified(root):
    bf16_counted_log(root)
    check(root, 2, at=AGAINST, step=BOARD, failure=CLASS_II)
    error = refused(root, counted())
    assert error.kind == verdicts_tool.KIND_COMPARISON_UNVERIFIED
    assert error.message == (
        "record.verdicts[0].evidence[2]: the comparison counts, but its against "
        "(round 0, candidate 1, attempt 1) is undetermined at board, where both "
        "must be verified"
    )


def test_a_fail_under_the_other_value_makes_a_pass_entry_unfounded(root):
    bf16_counted_log(root)
    check(root, 2, at=AGAINST, step=BOARD, result=FAIL)
    error = refused(root, counted())
    assert error.kind == verdicts_tool.KIND_CHECK_UNFOUNDED


def test_a_bf16_result_without_an_outcome_is_check_result_invalid(root):
    with_hypotheses(root, log=False)
    check(root, step=BF16_BOARD, result=bf16() | {"outcome": None})
    error = refused(root, pair([check_entry()]))
    assert error.kind == verdicts_tool.KIND_CHECK_RESULT_INVALID
    assert error.message == (
        f"{LOG}: line 2: data.result.outcome: must be one of pass, fail, broken, "
        "got NoneType None"
    )


def test_a_damaged_bf16_end_line_is_run_file_invalid(root):
    with_hypotheses(root, log=False)
    check(root, step=BF16_BOARD, result=bf16())
    raw(root, line({"step": BF16_BOARD, "execution": 2, "result": bf16()}))
    error = refused(root, pair([check_entry()]))
    assert error.kind == tools.KIND_RUN_FILE_INVALID
    assert error.message == f"{LOG}: line 3: data: lacks the member spend"


@pytest.mark.parametrize("point", [BF16_BOARD, "bf16"])
def test_a_check_entry_at_a_point_of_neither_value_is_invalid_request(root, point):
    with_hypotheses(root, log=False)
    check(root, step=BF16_BOARD, result=bf16())
    entry = check_entry() | {"point": point}
    error = refused(root, pair([entry]))
    assert error.kind == tools.KIND_INVALID_REQUEST
