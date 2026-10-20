import errno
import io
import json
import os
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    case_tool,
    data_root_source,
    events,
    journal,
    keys,
    layout,
    mcp_front,
    round_end_tool,
    run_file_tools,
    run_journal,
    run_state,
    run_state_file,
    tools,
)
from hilclaw.journal import EMPTY, Identity, SpendView
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

# Synthetic values only: no step name, axis or member of a real run.
RUN = "run-a"
STATE_PATH = f"runs/{RUN}/STATE.json"
LOG_PATH = f"runs/{RUN}/events.ndjson"
INSTANCE_PATH = f"runs/{RUN}/instance.json"
STEP = "example_step"
AXIS = "example_axis"
OTHER_AXIS = "other_axis"
TIME = "2026-01-01T00:00:00Z"
MAX = keys.MAX_INTEGER
GONE = "the data root is not an existing directory"


def hw():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_hw",
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }


def instance_document(round_budget=6):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(hw()).name, "record": hw()},
    }
    if round_budget is not None:
        document["round_budget"] = round_budget
    return document


def encoded(document):
    return (json.dumps(document, indent=2) + "\n").encode()


def line(kind, data, round=None, version=1):
    event = {"schema_version": version, "time": TIME, "kind": kind}
    if round is not None:
        event["round"] = round
    return (json.dumps(event | {"data": data}) + "\n").encode()


def started(execution=1, round=0, step=STEP):
    return line(journal.STEP_STARTED, {"step": step, "execution": execution}, round)


def ended(execution=1, round=0, step=STEP, **spend):
    data = {"step": step, "execution": execution, "spend": spend, "result": {}}
    return line(journal.STEP_ENDED, data, round)


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


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
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def state_path(root):
    return layout.run_file(root, RUN, "STATE.json")


def log_path(root):
    return layout.run_file(root, RUN, "events.ndjson")


def instance_path(root):
    return layout.run_file(root, RUN, "instance.json")


def run(root, round=0, view=EMPTY, others=None, log=b"", round_budget=6):
    """Place the three frame files of a run whose STATE.json names ``round``."""
    place(state_path(root), run_state.dump(round, view, others))
    place(log_path(root), log)
    place(instance_path(root), encoded(instance_document(round_budget)))


def request(**changes):
    return {"run_id": RUN, "round": 0} | changes


def end(source, body=None):
    return round_end_tool.definition(source).function(
        request() if body is None else body
    )


def written(root):
    return run_state.parse(state_path(root).read_bytes())


def tree(root):
    found = {}
    for directory, _, files in os.walk(root):
        here = Path(directory)
        found[here.relative_to(root).as_posix()] = None
        for name in files:
            path = here / name
            with open(path, "rb") as file:
                found[path.relative_to(root).as_posix()] = file.read()
    return found


def refused(root, body=None, source=None):
    before = tree(root)
    with pytest.raises(ToolFailure) as failure:
        end(source or Source(root), body)
    assert tree(root) == before
    return failure.value


def failed(root, body=None, source=None):
    with pytest.raises(ToolFailure) as failure:
        end(source or Source(root), body)
    return failure.value


ROUND_0 = (
    started(1)
    + ended(1, **{AXIS: 3})
    + started(1, step="other_step")
    + ended(1, step="other_step", **{AXIS: 2, OTHER_AXIS: 1})
)


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = round_end_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == round_end_tool.NAME == "round.end"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 0, "maximum": 2**53 - 2},
        },
        "required": ["run_id", "round"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert round_end_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="callable"):
        round_end_tool.definition(source)


KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_invalid",
    "run_file_unsupported",
    "run_file_unreadable",
    "round_not_current",
    "state_member_extra",
    "events.ndjson",
    "instance.json",
    "state_not_written",
)


def test_the_description_names_every_kind_in_order_and_what_to_do():
    description = round_end_tool.definition(lambda: None).description
    places = [description.index(kind) for kind in KINDS]
    assert places == sorted(places)
    assert '"reported_lines"' in description
    assert "report it in one line and go on" in description
    assert "report the kind in one line and end the session" in description
    assert "never part of the request" in description


def test_the_kinds_are_those_of_the_record():
    assert round_end_tool.KIND_STATE_MEMBER_EXTRA == "state_member_extra"
    assert round_end_tool.KIND_ROUND_NOT_CURRENT is case_tool.KIND_ROUND_NOT_CURRENT
    assert (
        round_end_tool.KIND_STATE_NOT_WRITTEN is run_file_tools.KIND_STATE_NOT_WRITTEN
    )
    assert "state_member_extra" not in tools.RESERVED_KINDS


# Happy paths (ADR-0135 Walk-through)


def test_the_end_of_round_0_writes_round_1_and_the_folded_view(root):
    run(root, log=ROUND_0, round_budget=6)
    assert end(Source(root)) == {"round": 1, "over": False, "reported_lines": []}
    from_first, _ = journal.fold(events.read(root, RUN).events)
    assert from_first == SpendView({AXIS: 5, OTHER_AXIS: 1}, 4, frozenset())
    state = written(root)
    assert state == run_state.RunState(1, from_first, {})
    assert state_path(root).read_bytes() == run_state.dump(1, from_first)
    assert log_path(root).read_bytes() == ROUND_0


@pytest.mark.parametrize(
    ("round", "budget", "over"),
    [(4, 5, True), (5, 6, True), (4, 3, True), (0, 1, True), (3, 5, False)],
)
def test_the_round_is_compared_with_the_round_budget(root, round, budget, over):
    run(root, round=round, log=ended(1, round, **{AXIS: 1}), round_budget=budget)
    result = end(Source(root), request(round=round))
    assert result == {"round": round + 1, "over": over, "reported_lines": [1]}
    state = written(root)
    assert state.round == round + 1
    assert state.others == ({"run_status": "over"} if over else {})


def test_no_round_budget_writes_no_run_status(root):
    run(root, round=4, log=ROUND_0, round_budget=None)
    assert end(Source(root), request(round=4))["over"] is False
    assert written(root).others == {}
    assert b"run_status" not in state_path(root).read_bytes()


def test_only_the_tail_after_the_stored_position_is_folded(root):
    before = b"not json, before the position\n" + ended(1, **{AXIS: 100})
    stored = SpendView({AXIS: 10}, 2, frozenset())
    run(root, round=2, view=stored, log=before + ROUND_0)
    assert end(Source(root), request(round=2))["reported_lines"] == []
    assert written(root).budget_spent == SpendView(
        {AXIS: 15, OTHER_AXIS: 1}, 6, frozenset()
    )


def test_a_torn_tail_is_not_counted_folded_or_removed(root):
    log = ROUND_0 + ended(9, **{AXIS: 50})[:-1]
    run(root, log=log)
    end(Source(root))
    assert written(root).budget_spent == SpendView(
        {AXIS: 5, OTHER_AXIS: 1}, 4, frozenset()
    )
    assert log_path(root).read_bytes() == log


def test_an_open_step_at_the_end_is_written(root):
    run(root, log=ROUND_0 + started(2))
    end(Source(root))
    assert written(root).budget_spent.open_steps == {Identity(STEP, 2, 0)}
    stored = json.loads(state_path(root).read_bytes())["budget_spent"]
    assert stored["open_steps"] == [{"round": 0, "step": STEP, "execution": 2}]


def test_the_reported_lines_are_numbered_from_the_first_line_of_the_file(root):
    stored = SpendView({}, 1, frozenset())
    log = started(1) + ended(7, **{AXIS: 4}) + started(2) + started(2)
    run(root, view=stored, log=log)
    result = end(Source(root))
    assert result == {"round": 1, "over": False, "reported_lines": [2, 4]}
    assert written(root).budget_spent == SpendView(
        {AXIS: 4}, 4, frozenset({Identity(STEP, 2, 0)})
    )


def test_a_total_above_the_largest_integer_is_written_exactly(root):
    stored = SpendView({AXIS: MAX}, 0, frozenset())
    run(root, view=stored, log=ended(1, **{AXIS: MAX}))
    end(Source(root))
    assert written(root).budget_spent.totals == {AXIS: 2 * MAX}
    assert str(2 * MAX).encode() in state_path(root).read_bytes()


def test_a_second_call_for_the_same_round_is_round_not_current(root):
    run(root, log=ROUND_0)
    end(Source(root))
    failure = refused(root)
    assert failure.kind == "round_not_current"
    assert failure.message == (
        f"{STATE_PATH}: names round 1 as in progress, not the request's round 0"
    )


def test_two_rounds_end_one_after_the_other(root):
    run(root, log=ROUND_0)
    definition = round_end_tool.definition(Source(root))
    definition.function(request())
    with open(log_path(root), "ab") as log:
        log.write(started(1, 1) + ended(1, 1, **{AXIS: 7}))
    assert definition.function(request(round=1)) == {
        "round": 2,
        "over": False,
        "reported_lines": [],
    }
    from_first, _ = journal.fold(events.read(root, RUN).events)
    assert written(root) == run_state.RunState(2, from_first, {})
    assert from_first.totals == {AXIS: 12, OTHER_AXIS: 1}


def test_the_written_file_is_read_by_the_readers_of_the_state(root):
    run(root, log=ROUND_0 + started(2))
    end(Source(root))
    state = run_journal.read_state(root, RUN)
    assert state == written(root)
    current = run_journal.current(root, RUN)
    assert current.view == state.budget_spent
    assert current.reports == ()
    assert run_file_tools.read(root, RUN, "STATE.json")[0] == state


def test_the_tool_answers_through_the_registry(root):
    run(root, log=ROUND_0)
    registry = default_registry(Source(root))
    assert tools.call(registry, "round.end", request()) == {
        "round": 1,
        "over": False,
        "reported_lines": [],
    }
    assert mcp_front.mcp_names(registry)["round_end"] == "round.end"


def test_the_tool_answers_by_its_mcp_name(root):
    run(root, round=4, log=ROUND_0, round_budget=5)
    params = {"name": "round_end", "arguments": request(round=4)}
    data = (
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
        )
        + "\n"
    ).encode()
    stdout = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(Source(root)),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0
    result = json.loads(stdout.getvalue())["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {
        "round": 5,
        "over": True,
        "reported_lines": [],
    }
    assert written(root).others == {"run_status": "over"}


# Negative requests


@pytest.mark.parametrize(
    "body",
    [
        request(extra=1),
        {},
        {"round": 0},
        {"run_id": RUN},
        request(run_id="Bad Run"),
        request(run_id=""),
        request(run_id="../x"),
        request(run_id=3),
        request(run_id=None),
        request(round=True),
        request(round=False),
        request(round=0.0),
        request(round=1.5),
        request(round=-1),
        request(round=MAX),
        request(round="0"),
        request(round=None),
    ],
)
def test_a_request_that_is_not_exactly_run_id_and_round_is_invalid(root, body):
    run(root, log=ROUND_0)
    source = Source(root)
    failure = refused(root, body, source)
    assert failure.kind == "invalid_request"
    assert source.calls == 0


def test_the_largest_round_is_accepted_up_to_the_check_of_the_state(root):
    run(root, log=ROUND_0)
    failure = refused(root, request(round=MAX - 1))
    assert failure.kind == "round_not_current"


def test_the_request_messages_name_what_is_wrong(root):
    assert "not 'alpha', 'zeta'" in refused(root, request(zeta=1, alpha=2)).message
    assert "lacks the member run_id" in refused(root, {"round": 0}).message
    assert "lacks the member round" in refused(root, {"run_id": RUN}).message
    message = refused(root, request(round=MAX)).message
    assert message == f"round: must be an int from 0 to {MAX - 1}, got {MAX}"


# Every kind, in order


def test_no_data_root(root):
    run(root, log=ROUND_0)
    source = FailingSource()
    failure = refused(root, source=source)
    assert failure.kind == "no_data_root"
    assert source.calls == 1


def test_a_missing_state_is_run_file_missing(root):
    place(log_path(root), ROUND_0)
    place(instance_path(root), encoded(instance_document()))
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message == f"{STATE_PATH}: is missing"


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{", "run_file_invalid"),
        (b"", "run_file_invalid"),
        (encoded({"schema_version": 1, "round": 0}), "run_file_invalid"),
        (encoded({"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_a_state_that_cannot_be_used_is_its_kind(root, content, kind):
    run(root, log=ROUND_0)
    place(state_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(STATE_PATH)


def test_a_directory_in_the_place_of_the_state_is_run_file_invalid(root):
    run(root, log=ROUND_0)
    state_path(root).unlink()
    state_path(root).mkdir()
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message == f"{STATE_PATH}: is not a regular file"


def failing_read(monkeypatch, name, error=None):
    original = Path.read_bytes

    def read_bytes(self):
        if self.name == name:
            raise error or PermissionError(errno.EACCES, "denied", str(self))
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)


@pytest.mark.parametrize(
    ("name", "path"),
    [
        ("STATE.json", STATE_PATH),
        ("events.ndjson", LOG_PATH),
        ("instance.json", INSTANCE_PATH),
    ],
)
def test_an_unreadable_frame_file_is_run_file_unreadable(root, monkeypatch, name, path):
    run(root, log=ROUND_0)
    failing_read(monkeypatch, name)
    failure = refused(root)
    assert failure.kind == "run_file_unreadable"
    assert failure.message == f"{path}: could not be read: PermissionError: denied"


def test_a_state_of_another_round_is_round_not_current(root):
    run(root, round=3, log=ROUND_0)
    failure = refused(root, request(round=2))
    assert failure.kind == "round_not_current"
    assert failure.message == (
        f"{STATE_PATH}: names round 3 as in progress, not the request's round 2"
    )


@pytest.mark.parametrize(
    ("others", "named"),
    [
        ({"run_status": "over"}, "'run_status'"),
        ({"run_status": "running"}, "'run_status'"),
        ({"zeta": 1, "alpha": {"x": []}}, "'alpha', 'zeta'"),
    ],
)
def test_a_state_with_another_member_is_state_member_extra(root, others, named):
    run(root, others=others, log=ROUND_0)
    failure = refused(root)
    assert failure.kind == "state_member_extra"
    assert failure.message.startswith(f"{STATE_PATH}: holds the members {named} ")


@pytest.mark.parametrize(
    ("log", "where"),
    [
        (ROUND_0 + b"not json\n", "line 5: is damaged"),
        (started(1) + b"\xff\n", "line 2: is damaged"),
        (ROUND_0 + line("note", {}, 0)[:-2] + b",\n", "line 5: is damaged"),
        (
            started(1)
            + line(journal.STEP_ENDED, {"step": STEP, "execution": 1, "result": {}}, 0),
            "line 2: data: lacks the member spend",
        ),
        (
            started(1) + ended(1, **{AXIS: -1}),
            "line 2: data.spend.example_axis: must be an int from 0",
        ),
    ],
)
def test_a_damaged_log_line_is_run_file_invalid(root, log, where):
    run(root, log=log)
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message.startswith(f"{LOG_PATH}: {where}")


def test_a_position_beyond_the_log_is_run_file_invalid(root):
    run(root, view=SpendView({}, 5, frozenset()), log=ROUND_0)
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message == (
        f"{LOG_PATH}: position 5 is beyond the end of the log, complete lines: 4"
    )


def test_a_missing_log_beyond_the_position_is_run_file_invalid(root):
    run(root, view=SpendView({}, 1, frozenset()))
    log_path(root).unlink()
    assert refused(root).kind == "run_file_invalid"


def test_a_missing_log_at_position_0_is_an_empty_tail(root):
    run(root)
    log_path(root).unlink()
    assert end(Source(root)) == {"round": 1, "over": False, "reported_lines": []}
    assert written(root).budget_spent == EMPTY
    assert not log_path(root).exists()


def test_a_log_line_of_another_version_is_run_file_unsupported(root):
    run(root, log=ROUND_0 + line("note", {}, version=2))
    failure = refused(root)
    assert failure.kind == "run_file_unsupported"
    assert failure.message == f"{LOG_PATH}: line 5: schema_version: 2 is not supported"


def test_a_directory_in_the_place_of_the_log_is_run_file_invalid(root):
    run(root)
    log_path(root).unlink()
    log_path(root).mkdir()
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message == f"{LOG_PATH}: is not a regular file"


def test_a_missing_instance_is_run_file_missing(root):
    run(root, log=ROUND_0)
    instance_path(root).unlink()
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message == f"{INSTANCE_PATH}: is missing"


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{", "run_file_invalid"),
        (encoded(instance_document(round_budget=0)), "run_file_invalid"),
        (encoded({"schema_version": 1}), "run_file_invalid"),
        (encoded(instance_document() | {"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_an_instance_that_cannot_be_used_is_its_kind(root, content, kind):
    run(root, log=ROUND_0)
    place(instance_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(INSTANCE_PATH)


def failing_replace(monkeypatch):
    def replace(source, target):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(os, "replace", replace)


def test_a_failing_replacement_is_state_not_written(root, monkeypatch):
    run(root, log=ROUND_0)
    failing_replace(monkeypatch)
    failure = refused(root)
    assert failure.kind == "state_not_written"
    assert failure.message == (
        f"{STATE_PATH}: was not written: OSError: Input/output error"
    )


def test_a_failing_write_of_the_state_is_state_not_written(root, monkeypatch):
    run(root, log=ROUND_0)

    def replace(*arguments):
        raise PermissionError(errno.EACCES, "denied", "/absolute/STATE.json")

    monkeypatch.setattr(run_state_file, "replace", replace)
    failure = refused(root)
    assert failure.kind == "state_not_written"
    assert failure.message == f"{STATE_PATH}: was not written: PermissionError: denied"
    assert isinstance(failure.__cause__, PermissionError)


# A data root removed after it was obtained


def removing_after(monkeypatch, module, name, when=lambda *arguments: True):
    original = getattr(module, name)

    def removing(*arguments):
        found = original(*arguments)
        if when(*arguments):
            shutil.rmtree(arguments[0])
        return found

    monkeypatch.setattr(module, name, removing)


def test_a_data_root_gone_before_the_state_is_read_is_run_file_missing(
    root, monkeypatch
):
    run(root, log=ROUND_0)
    original = data_root_source.obtain

    def obtain(source):
        found = original(source)
        shutil.rmtree(found)
        return found

    monkeypatch.setattr(data_root_source, "obtain", obtain)
    failure = failed(root)
    assert failure.kind == "run_file_missing"
    assert failure.message == f"{STATE_PATH}: is missing: {GONE}"


@pytest.mark.parametrize("position", [0, 2])
def test_a_data_root_gone_before_the_log_is_read_is_run_file_missing(
    root, monkeypatch, position
):
    run(root, view=SpendView({}, position, frozenset()), log=ROUND_0)
    removing_after(monkeypatch, run_file_tools, "read")
    failure = failed(root)
    assert failure.kind == "run_file_missing"
    assert failure.message == f"{LOG_PATH}: is missing: {GONE}"


def test_a_data_root_gone_before_the_instance_is_read_is_run_file_missing(
    root, monkeypatch
):
    run(root, log=ROUND_0)
    removing_after(monkeypatch, events, "read")
    failure = failed(root)
    assert failure.kind == "run_file_missing"
    assert failure.message == f"{INSTANCE_PATH}: is missing: {GONE}"


def test_a_data_root_gone_before_the_write_is_state_not_written(root, monkeypatch):
    run(root, log=ROUND_0)
    removing_after(
        monkeypatch,
        run_file_tools,
        "read",
        lambda root, run, name: name != "STATE.json",
    )
    failure = failed(root)
    assert failure.kind == "state_not_written"
    assert failure.message == (
        f"{STATE_PATH}: was not written: FileNotFoundError: {GONE}"
    )
    assert not root.exists()


# Order


def test_invalid_request_comes_before_no_data_root(root):
    source = FailingSource()
    assert refused(root, request(extra=1), source).kind == "invalid_request"
    assert source.calls == 0


def test_no_data_root_comes_before_run_file_missing(root, tmp_path):
    assert refused(root, source=Source(tmp_path / "missing")).kind == "no_data_root"


def test_round_not_current_comes_before_state_member_extra(root):
    run(root, round=2, others={"run_status": "over"}, log=ROUND_0)
    assert refused(root).kind == "round_not_current"


def test_state_member_extra_comes_before_a_damaged_log_line(root):
    run(root, others={"run_status": "over"}, log=b"not json\n")
    assert refused(root).kind == "state_member_extra"


def test_a_damaged_log_line_comes_before_an_invalid_instance(root):
    run(root, log=b"not json\n")
    place(instance_path(root), b"{")
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message.startswith(LOG_PATH)


def test_a_state_kind_comes_before_a_missing_instance_and_log(root):
    place(state_path(root), b"{")
    assert refused(root).kind == "run_file_invalid"


# What is not mapped, and what is not done


def test_an_invalid_state_error_of_the_dump_is_not_mapped(root, monkeypatch):
    run(root, log=ROUND_0)
    original = journal.fold

    def fold(lines, view):
        folded, reports = original(lines, view)
        return folded._replace(position=MAX + 1), reports

    monkeypatch.setattr(journal, "fold", fold)
    before = tree(root)
    with pytest.raises(run_state.InvalidStateError):
        end(Source(root))
    with pytest.raises(ToolFailure) as failure:
        tools.call(default_registry(Source(root)), "round.end", request())
    assert failure.value.kind == "tool_crashed"
    assert tree(root) == before


def test_each_call_asks_the_source_once_and_reads_only_the_frame_files(
    root, monkeypatch
):
    run(root, log=ROUND_0)
    names, positions = [], []
    original_read, original_events = run_file_tools.read, events.read

    def read(data_root, run_id, name):
        names.append(name)
        return original_read(data_root, run_id, name)

    def read_events(data_root, run_id, position=0):
        positions.append(position)
        return original_events(data_root, run_id, position)

    monkeypatch.setattr(run_file_tools, "read", read)
    monkeypatch.setattr(events, "read", read_events)
    source = Source(root)
    definition = round_end_tool.definition(source)
    definition.function(request())
    with open(log_path(root), "ab") as log:
        log.write(started(1, 1))
    definition.function(request(round=1))
    assert source.calls == 2
    assert names == ["STATE.json", "instance.json"] * 2
    assert positions == [0, 4]
    assert set(tree(root)) == {
        ".",
        "runs",
        f"runs/{RUN}",
        INSTANCE_PATH,
        STATE_PATH,
        LOG_PATH,
    }
