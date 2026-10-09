import copy
import inspect
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import __main__ as command_line
from hilclaw import (
    config,
    events,
    journaled_step,
    journaled_tool,
    keys,
    mcp_front,
    run_state,
    tools,
)
from hilclaw.journal import EMPTY, Identity, SpendView
from hilclaw.journaled_step import InvalidOutcomeError, StepFailed
from hilclaw.journaled_tool import tool_function
from hilclaw.tools import Registry, ToolFailure

# Synthetic values only: no tool, step name, axis or member of a real run.
REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = "test.journaled"
MCP_TOOL = "test_journaled"
DESCRIPTION = "A journaled tool of the tests."
SCHEMA = {"type": "object"}
RUN = "run-a"
LOG = f"runs/{RUN}/events.ndjson"
STEP = "example_step"
AXIS = "example_axis"
SPEND = {AXIS: 7}
ROUND = 3
NUMBERS = ("round", "candidate", "attempt")
REQUEST = {"run_id": RUN, "round": ROUND, "candidate": 2, "attempt": 1, "execution": 1}
ID = Identity(STEP, 1, ROUND, 2, 1)
MAX = keys.MAX_INTEGER
INVALID = tools.KIND_INVALID_REQUEST
FAILURE = {"error": {"kind": "example_failure", "message": "no outcome"}}

HELPER_SCRIPT = """\
import os
import sys

sys.path.insert(0, {root!r})

from hilclaw import __main__, data_root_source, journaled_tool, mcp_front
from hilclaw.tools import Registry


def perform(data_root, request):
    if "example_exit" in request:
        os._exit(9)
    return {{"example_axis": 7}}, {{"example_member": os.getpid()}}


function = journaled_tool.tool_function(
    step="example_step",
    numbers=("round", "candidate", "attempt"),
    source=data_root_source.configured,
    check=lambda request: None,
    perform=perform,
)
registry = Registry()
registry.register(
    "test.journaled", function, "A journaled tool of the tests.", {{"type": "object"}}
)
front = mcp_front if sys.argv[1] == "mcp" else __main__
raise SystemExit(front.main(sys.argv[2:], registry=registry))
"""


class Source:
    def __init__(self, *answers, order=None):
        self.answers = answers
        self.calls = 0
        self.order = [] if order is None else order

    def __call__(self):
        self.calls += 1
        self.order.append("source")
        answer = self.answers[min(self.calls, len(self.answers)) - 1]
        if isinstance(answer, BaseException):
            raise answer
        return answer


class Tool:
    """The test-only journaled tool: it counts, refuses a marker and fails when told to."""

    def __init__(self, *answers, numbers=NUMBERS, check=None, outcome=None):
        self.order, self.seen = [], []
        self.checked = self.performed = 0
        self.refusal, self.outcome = check, outcome
        self.source = Source(*answers, order=self.order)
        self.function = tool_function(
            step=STEP,
            numbers=numbers,
            source=self.source,
            check=self.check,
            perform=self.perform,
        )
        self.registry = Registry()
        self.registry.register(TOOL, self.function, DESCRIPTION, SCHEMA)

    def check(self, request):
        self.checked += 1
        self.order.append("check")
        if self.refusal is not None:
            raise self.refusal
        if "example_marker" in request:
            raise ToolFailure(INVALID, "example_marker: is no member")

    def perform(self, data_root, request):
        self.performed += 1
        self.order.append("perform")
        self.seen.append((data_root, request))
        if self.outcome is not None:
            if isinstance(self.outcome, BaseException):
                raise self.outcome
            return self.outcome
        if "example_fail" in request:
            raise StepFailed(SPEND, request["example_fail"], "no outcome")
        return SPEND, {"example_member": self.performed}


def request(**changes):
    return {**REQUEST, **changes}


def without(*names):
    return {name: value for name, value in REQUEST.items() if name not in names}


def by_call(tool, asked):
    try:
        return False, tools.call(tool.registry, TOOL, asked)
    except ToolFailure as failure:
        return True, failure.error_object()


def by_command_line(tool, asked):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        [TOOL],
        registry=tool.registry,
        stdin=io.BytesIO(json.dumps(asked).encode()),
        stdout=stdout,
        stderr=stderr,
    )
    assert status in (0, 3)
    return status == 3, json.loads(stdout.getvalue())


def mcp_line(asked):
    params = {"name": MCP_TOOL, "arguments": asked}
    document = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    return json.dumps(document).encode() + b"\n"


def outcome_of(document):
    (block,) = document["result"]["content"]
    return document["result"]["isError"], json.loads(block["text"])


def by_mcp(tool, asked):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=tool.registry,
        stdin=io.BytesIO(mcp_line(asked)),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    return outcome_of(json.loads(stdout.getvalue()))


FRONTS = {"cli": by_command_line, "mcp": by_mcp}
WAYS = {"call": by_call, **FRONTS}
PAIRS = [("cli", "mcp"), ("mcp", "cli")]
one_then_the_other = pytest.mark.parametrize("first,second", PAIRS)
each_front = pytest.mark.parametrize("front", list(FRONTS))


def event(kind, data, identity):
    numbers = {name: identity._asdict()[name] for name in NUMBERS}
    numbers = {name: value for name, value in numbers.items() if value is not None}
    return {"schema_version": 1, "kind": kind, **numbers, "data": data}


def started(identity=ID):
    data = {"step": identity.step, "execution": identity.execution}
    return event("step_started", data, identity)


def ended(identity=ID, **outcome):
    data = {"step": identity.step, "execution": identity.execution, "spend": SPEND}
    return event("step_ended", data | outcome, identity)


def raw(*lines):
    timed = [{"time": "2026-01-01T00:00:00Z", **line} for line in lines]
    return b"".join(json.dumps(line).encode() + b"\n" for line in timed)


def place(root, content, relative=LOG):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def store(root, view=EMPTY, round=ROUND, run=RUN):
    return place(root, run_state.dump(round, view), f"runs/{run}/STATE.json")


def new_root(tmp_path, name="data"):
    path = tmp_path / name
    path.mkdir()
    store(path)
    return path


@pytest.fixture
def root(tmp_path):
    return new_root(tmp_path)


def lines(root, run=RUN):
    found = events.read(root, run).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def snapshot(path):
    return {
        item.relative_to(path).as_posix(): item.read_bytes() if item.is_file() else None
        for item in path.rglob("*")
    }


class Died(BaseException):
    """Stands for the death of the process: no kind answers it and no front catches it."""


def die_in_append(monkeypatch, kind, after=False):
    real = events.append

    def append(data_root, run_id, line_kind, data, **numbers):
        if line_kind != kind:
            return real(data_root, run_id, line_kind, data, **numbers)
        if after:
            real(data_root, run_id, line_kind, data, **numbers)
        raise Died()

    monkeypatch.setattr(events, "append", append)


def break_append(monkeypatch, kind, error):
    real = events.append

    def append(data_root, run_id, line_kind, data, **numbers):
        if line_kind != kind:
            return real(data_root, run_id, line_kind, data, **numbers)
        raise error

    monkeypatch.setattr(events, "append", append)


def refused(tool, asked, member):
    with pytest.raises(ToolFailure) as caught:
        tool.function(asked)
    assert caught.value.kind == INVALID == "invalid_request"
    assert member in caught.value.message
    assert (tool.source.calls, tool.performed) == (0, 0)
    return caught.value


def assert_open_and_not_run(tool, root, way, asked=REQUEST):
    before, performed = snapshot(root), tool.performed
    failed, answer = WAYS[way](tool, asked)
    assert failed is True
    assert answer["error"]["kind"] == tools.KIND_STEP_OPEN == "step_open"
    assert tool.performed == performed
    assert snapshot(root) == before


# --- happy ---


def test_the_public_names_and_the_signature():
    public = [name for name in vars(journaled_tool) if not name.startswith("_")]
    assert [
        name for name in public if not inspect.ismodule(vars(journaled_tool)[name])
    ] == ["tool_function", "checked_function"]
    parameters = inspect.signature(tool_function).parameters
    assert list(parameters) == ["step", "numbers", "source", "check", "perform"]
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty


def test_a_first_call_appends_the_two_lines_and_returns_the_result(root):
    tool = Tool(root)
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert lines(root) == [started(), ended(result={"example_member": 1})]
    assert tool.order == ["check", "source", "perform"]
    assert (tool.checked, tool.source.calls, tool.performed) == (1, 1, 1)


@pytest.mark.parametrize(
    "numbers,asked,identity",
    [
        ((), without(*NUMBERS), Identity(STEP, 1)),
        (("round",), without("candidate", "attempt"), Identity(STEP, 1, ROUND)),
        (("round", "candidate"), without("attempt"), Identity(STEP, 1, ROUND, 2)),
        (("round",), {"run_id": RUN, "execution": 1, "round": 9}, Identity(STEP, 1, 9)),
        (("round",), {"run_id": RUN, "execution": 1, "round": 0}, Identity(STEP, 1, 0)),
    ],
)
def test_a_tool_that_requires_fewer_numbers(root, numbers, asked, identity):
    tool = Tool(root, numbers=numbers)
    assert tool.function(asked) == {"example_member": 1}
    assert lines(root) == [
        started(identity),
        ended(identity, result={"example_member": 1}),
    ]
    assert tool.function(asked) == {"example_member": 1}
    assert tool.performed == 1


def test_a_failed_step_gives_an_end_line_with_failure_and_spend(root):
    tool = Tool(root)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request(example_fail="example_failure"))
    assert caught.value.error_object() == FAILURE
    assert lines(root) == [started(), ended(failure=FAILURE["error"])]
    assert tool.performed == 1


def test_a_further_execution_is_another_identity_and_runs(root):
    tool = Tool(root)
    assert tool.function(request()) == {"example_member": 1}
    assert tool.function(request(execution=2)) == {"example_member": 2}
    assert tool.function(request(execution=MAX)) == {"example_member": 3}
    assert tool.function(request()) == {"example_member": 1}
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1, 2, 2, MAX, MAX]


def test_perform_gets_the_data_root_and_the_request_as_given(root):
    tool = Tool(str(root))
    asked = request(example_other={"nested": [1, 2]})
    before = copy.deepcopy(asked)
    tool.function(asked)
    ((data_root, seen),) = tool.seen
    assert data_root == root and type(data_root) is type(root)
    assert seen is asked
    assert asked == before


@pytest.mark.parametrize(
    "asked", [request(), request(example_fail="example_failure")], ids=["ok", "failed"]
)
def test_one_request_gives_the_same_outcome_in_every_way(tmp_path, asked):
    outcomes, logs = [], []
    for way, through in WAYS.items():
        tool = Tool(new_root(tmp_path, way))
        outcomes.append(through(tool, asked))
        logs.append(lines(tmp_path / way))
        assert tool.performed == 1
    assert outcomes[0] == outcomes[1] == outcomes[2]
    assert logs[0] == logs[1] == logs[2]
    assert len(logs[0]) == 2
    expected = (
        (True, FAILURE) if "example_fail" in asked else (False, {"example_member": 1})
    )
    assert outcomes[0] == expected


# --- the three states, the first call through one front and the repeated one through the other ---


@one_then_the_other
def test_no_line_runs_once_and_an_ended_step_answers_its_result(root, first, second):
    tool = Tool(root)
    assert FRONTS[first](tool, REQUEST) == (False, {"example_member": 1})
    assert tool.performed == 1
    before = snapshot(root)
    assert FRONTS[second](tool, REQUEST) == (False, {"example_member": 1})
    assert FRONTS[first](tool, REQUEST) == (False, {"example_member": 1})
    assert tool.performed == 1
    assert snapshot(root) == before


@one_then_the_other
def test_an_ended_step_with_a_failure_fails_again_and_is_not_run(root, first, second):
    tool = Tool(root)
    asked = request(example_fail="example_failure")
    assert FRONTS[first](tool, asked) == (True, FAILURE)
    before = snapshot(root)
    assert FRONTS[second](tool, asked) == (True, FAILURE)
    assert FRONTS[second](tool, REQUEST) == (True, FAILURE)
    assert tool.performed == 1
    assert snapshot(root) == before


@each_front
def test_an_open_step_is_step_open_and_not_run(root, front):
    place(root, raw(started()))
    tool = Tool(root)
    assert_open_and_not_run(tool, root, front)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request())
    assert caught.value.kind == "step_open"
    assert tool.performed == 0


def test_a_step_that_states_a_reserved_kind_is_not_detected(root):
    tool = Tool(root)
    for _ in range(2):
        failed, answer = by_call(tool, request(example_fail="step_open"))
        assert (failed, answer["error"]) == (
            True,
            {"kind": "step_open", "message": "no outcome"},
        )
    assert tool.performed == 1
    assert [line["kind"] for line in lines(root)] == ["step_started", "step_ended"]


# --- the three death points, the repeated call through the other front ---


@one_then_the_other
def test_death_before_the_start_line_the_next_call_runs(
    root, monkeypatch, first, second
):
    tool = Tool(root)
    with monkeypatch.context() as patch:
        die_in_append(patch, "step_started")
        with pytest.raises(Died):
            FRONTS[first](tool, REQUEST)
    assert tool.performed == 0
    assert not (root / LOG).exists()
    assert FRONTS[second](tool, REQUEST) == (False, {"example_member": 1})
    assert tool.performed == 1


@each_front
def test_a_torn_start_line_is_no_line_the_next_call_runs(root, front):
    place(root, raw(started())[:-1])
    tool = Tool(root)
    assert FRONTS[front](tool, REQUEST) == (False, {"example_member": 1})
    assert tool.performed == 1
    assert lines(root) == [started(), ended(result={"example_member": 1})]


@one_then_the_other
def test_death_after_the_start_line_before_the_step_leaves_it_open(
    root, monkeypatch, first, second
):
    tool = Tool(root)
    with monkeypatch.context() as patch:
        die_in_append(patch, "step_started", after=True)
        with pytest.raises(Died):
            FRONTS[first](tool, REQUEST)
    assert tool.performed == 0
    assert lines(root) == [started()]
    assert_open_and_not_run(tool, root, second)


@one_then_the_other
@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("died"),
        ToolFailure("example_failure", "no amounts"),
        KeyboardInterrupt(),
        "no pair",
    ],
    ids=["exception", "plain-tool-failure", "interrupt", "no-pair"],
)
def test_death_during_the_step_leaves_it_open(root, first, second, error):
    tool = Tool(root, outcome=error)
    if isinstance(error, KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            FRONTS[first](tool, REQUEST)
    else:
        failed, answer = FRONTS[first](tool, REQUEST)
        assert failed is True
        assert answer["error"]["kind"] != "step_open"
    assert tool.performed == 1
    assert lines(root) == [started()]
    assert_open_and_not_run(tool, root, second)


def test_what_perform_raises_passes_through_unchanged(root):
    for execution, error in enumerate(
        [RuntimeError("died"), ToolFailure("example_failure", "no amounts")], 1
    ):
        tool = Tool(root, outcome=error)
        with pytest.raises(type(error)) as caught:
            tool.function(request(execution=execution))
        assert caught.value is error
    with pytest.raises(InvalidOutcomeError):
        Tool(root, outcome="no pair").function(request(execution=3))
    assert [line["kind"] for line in lines(root)] == ["step_started"] * 3


@one_then_the_other
@pytest.mark.parametrize(
    "asked", [request(), request(example_fail="example_failure")], ids=["ok", "failed"]
)
def test_death_between_the_outcome_and_the_end_line_leaves_it_open(
    root, monkeypatch, first, second, asked
):
    tool = Tool(root)
    with monkeypatch.context() as patch:
        die_in_append(patch, "step_ended")
        with pytest.raises(Died):
            FRONTS[first](tool, asked)
    assert tool.performed == 1
    assert lines(root) == [started()]
    assert_open_and_not_run(tool, root, second, asked)


@one_then_the_other
@pytest.mark.parametrize(
    "asked,stored",
    [
        (request(), (False, {"example_member": 1})),
        (request(example_fail="example_failure"), (True, FAILURE)),
    ],
    ids=["ok", "failed"],
)
def test_death_after_the_end_line_the_next_call_answers_what_it_holds(
    root, monkeypatch, first, second, asked, stored
):
    tool = Tool(root)
    with monkeypatch.context() as patch:
        die_in_append(patch, "step_ended", after=True)
        with pytest.raises(Died):
            FRONTS[first](tool, asked)
    before = snapshot(root)
    assert FRONTS[second](tool, asked) == stored
    assert tool.performed == 1
    assert snapshot(root) == before


# --- a failed append of a step line (ADR-0026) ---


@pytest.mark.parametrize(
    "line,kind,performed",
    [("step_started", "start_line_failed", 0), ("step_ended", "end_line_failed", 1)],
)
@pytest.mark.parametrize(
    "error",
    [
        OSError(28, "No space left on device", "/elsewhere/events.ndjson"),
        events.CorruptEventsError(f"{LOG}: is not a regular file"),
    ],
    ids=["OSError", "CorruptEventsError"],
)
@pytest.mark.parametrize(
    "asked", [request(), request(example_fail="example_failure")], ids=["ok", "failed"]
)
def test_a_failed_append_is_the_kind_of_its_line_in_every_way(
    tmp_path, monkeypatch, line, kind, performed, error, asked
):
    outcomes = []
    for way, through in WAYS.items():
        tool = Tool(new_root(tmp_path, way))
        with monkeypatch.context() as patch:
            break_append(patch, line, error)
            outcomes.append(through(tool, asked))
        assert tool.performed == performed
        assert lines(tmp_path / way) == [started()] * performed
    assert outcomes[0] == outcomes[1] == outcomes[2]
    failed, answer = outcomes[0]
    assert failed is True
    assert set(answer["error"]) == {"kind", "message"}
    assert answer["error"]["kind"] == kind
    message = answer["error"]["message"]
    assert message.startswith(f"{LOG}: ")
    for text in ("elsewhere", AXIS, "example_member", "example_failure", "no outcome"):
        assert text not in message


@one_then_the_other
def test_after_a_failed_start_line_the_same_request_runs_the_step(
    root, monkeypatch, first, second
):
    tool = Tool(root)
    with monkeypatch.context() as patch:
        break_append(patch, "step_started", OSError(28, "No space left on device"))
        failed, answer = FRONTS[first](tool, REQUEST)
    assert (failed, answer["error"]["kind"]) == (True, "start_line_failed")
    assert tool.performed == 0
    assert FRONTS[second](tool, REQUEST) == (False, {"example_member": 1})
    assert tool.performed == 1


@one_then_the_other
def test_after_a_failed_end_line_the_same_request_is_step_open(
    root, monkeypatch, first, second
):
    tool = Tool(root)
    with monkeypatch.context() as patch:
        break_append(patch, "step_ended", OSError(28, "No space left on device"))
        failed, answer = FRONTS[first](tool, REQUEST)
    assert (failed, answer["error"]["kind"]) == (True, "end_line_failed")
    assert tool.performed == 1
    assert_open_and_not_run(tool, root, second)


# --- the order of a call ---


def test_a_refused_request_asks_no_source_and_runs_nothing(tmp_path):
    tool = Tool(RuntimeError("the source must not be asked"))
    for asked in (without("run_id"), request(execution=0), without("candidate")):
        refused(tool, asked, "")
    assert tool.order == []
    refused(tool, request(example_marker=1), "example_marker")
    assert tool.order == ["check"]
    assert list(tmp_path.iterdir()) == []


def test_the_own_check_runs_after_the_five_members_and_before_the_source(root):
    tool = Tool(root)
    refused(tool, request(example_marker=1, execution=0), "execution")
    assert tool.checked == 0
    refused(tool, request(example_marker=1), "example_marker")
    assert tool.order == ["check"]
    tool.function(request())
    assert tool.order == ["check", "check", "source", "perform"]


@pytest.mark.parametrize(
    "error",
    [ToolFailure("example_refusal", "of the tool"), RuntimeError("a defect")],
    ids=["another-kind", "exception"],
)
def test_what_the_own_check_raises_passes_through_unchanged(root, error):
    before = snapshot(root)
    tool = Tool(root, check=error)
    with pytest.raises(type(error)) as caught:
        tool.function(request())
    assert caught.value is error
    assert (tool.source.calls, tool.performed) == (0, 0)
    failed, answer = by_call(tool, request())
    expected = "example_refusal" if isinstance(error, ToolFailure) else "tool_crashed"
    assert (failed, answer["error"]["kind"]) == (True, expected)
    assert snapshot(root) == before


@pytest.mark.parametrize("way", list(WAYS))
def test_a_failing_source_is_no_data_root_and_nothing_runs(tmp_path, way):
    missing = tmp_path / "missing"
    for tool in (Tool(missing), Tool(RuntimeError("no configuration"))):
        failed, answer = WAYS[way](tool, REQUEST)
        assert (failed, answer["error"]["kind"]) == (True, "no_data_root")
        assert (tool.checked, tool.source.calls, tool.performed) == (1, 1, 0)
    assert list(tmp_path.iterdir()) == []


def test_the_source_is_asked_once_at_each_call_and_nothing_is_kept(tmp_path):
    one, other = new_root(tmp_path, "one"), new_root(tmp_path, "other")
    tool = Tool(one, other)
    assert tool.function(request()) == {"example_member": 1}
    assert tool.source.calls == 1
    assert tool.function(request()) == {"example_member": 2}
    assert tool.source.calls == 2
    assert [data_root for data_root, _ in tool.seen] == [one, other]
    assert lines(one) == [started(), ended(result={"example_member": 1})]
    assert lines(other) == [started(), ended(result={"example_member": 2})]
    assert tool.function(request()) == {"example_member": 2}
    assert (tool.source.calls, tool.performed) == (3, 2)


def test_a_change_of_the_run_between_two_calls_is_seen(root):
    tool = Tool(root)
    assert tool.function(request()) == {"example_member": 1}
    place(root, b"")
    assert tool.function(request()) == {"example_member": 2}


def test_the_run_and_the_identity_are_those_checked_before_the_own_check(root):
    store(root, run="run-b")
    function, _ = build(
        source=lambda: root,
        check=lambda request: request.update(run_id="run-b", round=9, execution=2),
        perform=lambda data_root, request: (SPEND, {}),
    )
    assert function(request()) == {}
    assert lines(root) == [started(), ended(result={})]
    assert lines(root, "run-b") == []


# --- a refused request ---

REFUSED = [
    (without("run_id"), "run_id"),
    (request(run_id=7), "run_id"),
    (request(run_id=None), "run_id"),
    (request(run_id=""), "run_id"),
    (request(run_id="a/b"), "run_id"),
    (request(run_id=".."), "run_id"),
    (request(run_id="Run-a"), "run_id"),
    (request(run_id=[RUN]), "run_id"),
    (without("execution"), "execution"),
    (request(execution=0), "execution"),
    (request(execution=-1), "execution"),
    (request(execution=True), "execution"),
    (request(execution=1.0), "execution"),
    (request(execution="1"), "execution"),
    (request(execution=None), "execution"),
    (request(execution=MAX + 1), "execution"),
    (without("round"), "round"),
    (without("candidate"), "candidate"),
    (without("attempt"), "attempt"),
    (without("round", "candidate"), "round"),
    (request(round=-1), "round"),
    (request(round=True), "round"),
    (request(round=3.0), "round"),
    (request(round="3"), "round"),
    (request(round=None), "round"),
    (request(round=MAX + 1), "round"),
    (request(candidate=0), "candidate"),
    (request(candidate=False), "candidate"),
    (request(candidate=None), "candidate"),
    (request(attempt=0), "attempt"),
    (request(attempt=1.5), "attempt"),
    (request(attempt="1"), "attempt"),
    (request(attempt=None), "attempt"),
    (request(attempt=[1]), "attempt"),
    (request(example_marker=True), "example_marker"),
]


@pytest.mark.parametrize("asked,member", REFUSED)
def test_a_refused_request_names_the_member_and_leaves_no_trace(root, asked, member):
    before, given = snapshot(root), copy.deepcopy(asked)
    tool = Tool(root)
    error = refused(tool, asked, member)
    assert error.message.startswith(f"{member}: ")
    assert asked == given
    assert snapshot(root) == before
    assert [entry.name for entry in (root / "runs").iterdir()] == [RUN]


@pytest.mark.parametrize(
    "error",
    [ValueError, TypeError],
    ids=["a-rule-of-the-run-or-the-identity", "no-object"],
)
def test_a_refusal_is_chained_to_the_error_of_the_reused_check(root, error):
    tool = Tool(root)
    if error is TypeError:
        for asked in (None, [REQUEST], "run-a", 1):
            assert (
                refused(tool, asked, "the request must be an object").__cause__ is None
            )
        return
    for asked in (request(run_id="A"), request(execution=0), request(round=-1)):
        assert isinstance(refused(tool, asked, "").__cause__, ValueError)
    assert refused(tool, without("run_id"), "run_id").__cause__ is None


@pytest.mark.parametrize(
    "numbers,asked,member",
    [
        ((), {"run_id": RUN, "execution": 1, "round": ROUND}, "round"),
        ((), {"run_id": RUN, "execution": 1, "attempt": 1}, "attempt"),
        (("round",), without("attempt"), "candidate"),
        (("round",), without("candidate"), "attempt"),
        (("round",), without("attempt") | {"candidate": None}, "candidate"),
        (("round", "candidate"), request(), "attempt"),
        (("round", "candidate"), request(attempt=None), "attempt"),
        (("round", "candidate"), without("candidate"), "candidate"),
    ],
)
def test_a_number_the_contract_does_not_require_is_refused(
    root, numbers, asked, member
):
    before = snapshot(root)
    tool = Tool(root, numbers=numbers)
    assert refused(tool, asked, member).message.startswith(f"{member}: ")
    assert snapshot(root) == before


def test_a_request_never_names_the_step(root):
    tool = Tool(root)
    asked = request(step="example_other", kind="step_ended", data={"step": "x"})
    assert tool.function(asked) == {"example_member": 1}
    assert lines(root) == [started(), ended(result={"example_member": 1})]
    assert tool.function(request()) == {"example_member": 1}
    assert tool.performed == 1


@pytest.mark.parametrize(
    "asked,member",
    [
        (without("run_id"), "run_id"),
        (request(execution=0), "execution"),
        (without("candidate"), "candidate"),
        (request(round=None), "round"),
        (request(example_marker=1), "example_marker"),
    ],
)
def test_both_fronts_report_a_refused_request_alike(root, asked, member):
    before = snapshot(root)
    tool = Tool(root)
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        [TOOL],
        registry=tool.registry,
        stdin=io.BytesIO(json.dumps(asked).encode()),
        stdout=stdout,
        stderr=stderr,
    )
    assert status == command_line.EXIT_TOOL_FAILURE == 3
    answer = json.loads(stdout.getvalue())
    assert list(answer) == ["error"]
    assert answer["error"]["kind"] == "invalid_request"
    assert member in answer["error"]["message"]
    assert by_mcp(tool, asked) == (True, answer) == by_call(tool, asked)
    assert (tool.source.calls, tool.performed) == (0, 0)
    assert snapshot(root) == before


# --- a run that cannot be used: a tool failure of one of the four kinds of ADR-0019 ---


def no_run_directory(root):
    (root / "runs" / RUN / "STATE.json").unlink()
    (root / "runs" / RUN).rmdir()


def no_state(root):
    (root / "runs" / RUN / "STATE.json").unlink()


STATE = f"runs/{RUN}/STATE.json"


def other_version_state(root):
    content = run_state.dump(ROUND, EMPTY)
    changed = content.replace(b'"schema_version": 1', b'"schema_version": 2')
    assert changed != content
    place(root, changed, STATE)


def line_of_another_version(root):
    place(root, raw({"schema_version": 2, "kind": "example_kind", "data": {}}))


def step_line_that_breaks_the_journal(root):
    place(root, raw(event("step_started", {"step": STEP}, ID)))


UNUSABLE = {
    "no-run-directory": (no_run_directory, "run_file_missing", STATE),
    "no-state": (no_state, "run_file_missing", STATE),
    "invalid-state": (
        lambda root: place(root, b"{", STATE),
        "run_file_invalid",
        STATE,
    ),
    "empty-state": (lambda root: place(root, b"", STATE), "run_file_invalid", STATE),
    "other-version-state": (other_version_state, "run_file_unsupported", STATE),
    "damaged-log": (
        lambda root: place(root, b"not a line\n"),
        "run_file_invalid",
        LOG,
    ),
    "line-of-another-version": (line_of_another_version, "run_file_unsupported", LOG),
    "step-line-that-breaks-the-journal": (
        step_line_that_breaks_the_journal,
        "run_file_invalid",
        LOG,
    ),
    "position-beyond-the-log": (
        lambda root: store(root, SpendView({}, 5, frozenset())),
        "run_file_invalid",
        LOG,
    ),
}


@pytest.mark.parametrize("damage", list(UNUSABLE))
def test_an_unusable_run_is_a_tool_failure_of_its_run_file_kind(root, damage):
    change, kind, file = UNUSABLE[damage]
    change(root)
    before = snapshot(root)
    with pytest.raises(ToolFailure) as expected:
        journaled_step.run(root, RUN, ID, lambda: (SPEND, {}))
    assert expected.value.kind == kind
    tool = Tool(root)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request())
    assert type(caught.value) is ToolFailure
    assert caught.value.args == expected.value.args
    assert caught.value.__cause__ is not None
    assert caught.value.message.startswith(f"{file}: ")
    answers = {way: WAYS[way](tool, request()) for way in WAYS}
    assert answers["cli"] == answers["mcp"] == answers["call"]
    assert answers["cli"] == (True, caught.value.error_object())
    assert answers["cli"][1]["error"]["kind"] == kind
    assert kind in tools.RESERVED_KINDS
    assert tool.performed == 0
    assert snapshot(root) == before


@pytest.mark.parametrize("way", list(WAYS))
def test_a_well_formed_run_id_that_names_no_run_is_missing_not_a_refused_request(
    root, way
):
    before = snapshot(root)
    tool = Tool(root)
    failed, answer = WAYS[way](tool, request(run_id="run-b"))
    assert failed is True
    assert answer["error"]["kind"] == "run_file_missing" != INVALID
    assert answer["error"]["message"] == "runs/run-b/STATE.json: is missing"
    assert (tool.source.calls, tool.performed) == (1, 0)
    assert snapshot(root) == before


@pytest.mark.parametrize("way", list(WAYS))
def test_what_the_step_raises_in_a_class_of_a_row_is_still_a_crashed_tool(root, way):
    tool = Tool(root, outcome=FileNotFoundError(2, "No such file or directory"))
    failed, answer = WAYS[way](tool, request())
    assert (failed, answer["error"]["kind"]) == (True, "tool_crashed")
    assert tool.performed == 1
    failed, answer = WAYS[way](tool, request())
    assert (failed, answer["error"]["kind"]) == (True, "step_open")


@pytest.mark.parametrize("way", list(WAYS))
def test_the_same_request_is_answered_once_the_state_is_written(root, way):
    no_state(root)
    tool = Tool(root)
    failed, answer = WAYS[way](tool, request())
    assert (failed, answer["error"]["kind"]) == (True, "run_file_missing")
    store(root)
    assert WAYS[way](tool, request()) == (False, {"example_member": 1})
    assert WAYS[way](tool, request()) == (False, {"example_member": 1})
    assert tool.performed == 1


# --- the builder ---


def build(**changes):
    called = []
    arguments = {
        "step": STEP,
        "numbers": NUMBERS,
        "source": lambda: called.append("source"),
        "check": lambda request: called.append("check"),
        "perform": lambda data_root, request: called.append("perform"),
    }
    return tool_function(**arguments | changes), called


def test_building_calls_nothing_and_gives_a_new_function_each_time():
    (one, called), (other, _) = build(), build()
    assert callable(one) and one is not other
    assert called == []
    assert list(inspect.signature(one).parameters) == ["request"]


@pytest.mark.parametrize(
    "step", ["", "Example", "example-step", "1step", "a" * 33, 7, None, ["example"]]
)
def test_a_step_that_is_no_name_is_refused_when_built(step):
    with pytest.raises(ValueError, match="step"):
        build(step=step)


@pytest.mark.parametrize(
    "numbers,error",
    [
        (("candidate",), ValueError),
        (("round", "attempt"), ValueError),
        (("round", "round"), ValueError),
        (("example",), ValueError),
        (("round", "candidate", "attempt", "round"), ValueError),
        (("attempt", "candidate", "round"), ValueError),
        (["round"], TypeError),
        ("round", TypeError),
        (None, TypeError),
        ({"round"}, TypeError),
    ],
)
def test_numbers_of_another_form_are_refused_when_built(numbers, error):
    with pytest.raises(error, match="numbers"):
        build(numbers=numbers)


@pytest.mark.parametrize("name", ["source", "check", "perform"])
@pytest.mark.parametrize("value", [None, "example", 1])
def test_a_part_that_is_not_callable_is_refused_when_built(name, value):
    with pytest.raises(TypeError, match=name):
        build(**{name: value})


def test_the_five_are_given_by_name_and_all_are_required():
    with pytest.raises(TypeError):
        tool_function(STEP, NUMBERS, lambda: None, lambda r: None, lambda d, r: None)
    for name in ("step", "numbers", "source", "check", "perform"):
        arguments = {
            "step": STEP,
            "numbers": (),
            "source": lambda: None,
            "check": lambda request: None,
            "perform": lambda data_root, request: None,
        }
        del arguments[name]
        with pytest.raises(TypeError, match=name):
            tool_function(**arguments)


# --- through a real process ---


def run_front(tmp_path, front, local_path, asked):
    script = tmp_path / "fronts_with_a_journaled_tool.py"
    script.write_text(HELPER_SCRIPT.format(root=str(REPO_ROOT)), encoding="utf-8")
    environ = dict(os.environ)
    environ.pop(config.ENV_URL, None)
    environ[config.ENV_LOCAL_PATH] = str(local_path)
    data, args = json.dumps(asked).encode(), [TOOL]
    if front == "mcp":
        data, args = mcp_line(asked), []
    done = subprocess.run(
        [sys.executable, str(script), front, *args],
        input=data,
        capture_output=True,
        cwd=tmp_path,
        env=environ,
        timeout=60,
        check=False,
    )
    return done.returncode, done.stdout


def process_outcome(tmp_path, front, local_path, asked):
    status, output = run_front(tmp_path, front, local_path, asked)
    if front == "mcp":
        assert status == 0
        return outcome_of(json.loads(output))
    assert status in (0, 3)
    return status == 3, json.loads(output)


@one_then_the_other
def test_process_the_repeated_call_through_the_other_front_returns_the_line(
    root, tmp_path, first, second
):
    failed, result = process_outcome(tmp_path, first, root, REQUEST)
    assert failed is False
    assert (
        list(result) == ["example_member"] and result["example_member"] != os.getpid()
    )
    assert lines(root) == [started(), ended(result=result)]
    before = snapshot(root)
    assert process_outcome(tmp_path, second, root, REQUEST) == (False, result)
    assert snapshot(root) == before


@one_then_the_other
def test_process_a_death_during_the_step_leaves_it_open(root, tmp_path, first, second):
    asked = request(example_exit=True)
    status, output = run_front(tmp_path, first, root, asked)
    assert (status, output) == (9, b"")
    assert lines(root) == [started()]
    before = snapshot(root)
    failed, answer = process_outcome(tmp_path, second, root, REQUEST)
    assert (failed, answer["error"]["kind"]) == (True, "step_open")
    assert snapshot(root) == before


def test_process_a_refused_request_and_a_missing_data_root(tmp_path):
    missing = tmp_path / "missing"
    for front in FRONTS:
        failed, answer = process_outcome(tmp_path, front, missing, without("run_id"))
        assert (failed, answer["error"]["kind"]) == (True, "invalid_request")
        failed, answer = process_outcome(tmp_path, front, missing, REQUEST)
        assert (failed, answer["error"]["kind"]) == (True, "no_data_root")
    assert not missing.exists()


# --- the part the two builders share ---

checked_function = journaled_tool.checked_function


class Shared:
    def __init__(self, *answers, numbers=NUMBERS, refusal=None, outcome=None, **others):
        self.order, self.seen = [], []
        self.refusal, self.outcome = refusal, outcome
        self.source = Source(*answers, order=self.order)
        self.function = checked_function(
            step=STEP,
            numbers=numbers,
            carry_out=self.carry_out,
            source=self.source,
            check=self.check,
            **others,
        )

    def check(self, request):
        self.order.append("check")
        if self.refusal is not None:
            raise self.refusal

    def carry_out(self, *arguments):
        self.order.append("carry_out")
        self.seen.append(arguments)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def shared_parts(**changes):
    called = []
    arguments = {
        "step": STEP,
        "numbers": NUMBERS,
        "carry_out": lambda *arguments: called.append("carry_out"),
        "source": lambda: called.append("source"),
        "check": lambda request: called.append("check"),
    }
    return arguments | changes, called


def test_the_signature_of_checked_function():
    parameters = inspect.signature(checked_function).parameters
    named = ["step", "numbers", "carry_out", "source", "check"]
    assert list(parameters) == [*named, "others"]
    for name in named:
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
        assert parameters[name].default is inspect.Parameter.empty
    assert parameters["others"].kind is inspect.Parameter.VAR_KEYWORD


def test_checked_function_hands_a_checked_request_to_carry_out_once(root):
    outcome = {"example_member": 1}
    shared = Shared(str(root), outcome=outcome)
    asked = request(example_other={"nested": [1, 2]})
    given, before = copy.deepcopy(asked), snapshot(root)
    assert shared.function(asked) is outcome
    assert shared.order == ["check", "source", "carry_out"]
    assert shared.source.calls == 1
    ((data_root, run_id, identity, handed),) = shared.seen
    assert isinstance(data_root, Path) and data_root == root
    assert (run_id, identity) == (RUN, ID)
    assert handed is asked and asked == given
    assert snapshot(root) == before


def test_checked_function_asks_the_source_at_each_call(root, tmp_path):
    other = new_root(tmp_path, "other")
    shared = Shared(str(root), str(other))
    shared.function(dict(REQUEST))
    shared.function(dict(REQUEST))
    assert [seen[0] for seen in shared.seen] == [root, other]
    assert shared.order == ["check", "source", "carry_out"] * 2


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_checked_function_forms_the_identity_of_each_prefix_of_the_numbers(root, count):
    numbers = NUMBERS[:count]
    shared = Shared(str(root), numbers=numbers)
    asked = without(*NUMBERS[count:])
    assert shared.function(asked) is None
    values = [REQUEST[name] for name in numbers] + [None] * (3 - count)
    assert shared.seen == [(root, RUN, Identity(STEP, 1, *values), asked)]


def test_checked_function_gives_a_new_function_each_time_and_calls_nothing():
    given, called = shared_parts(perform=lambda: called.append("perform"))
    one, other = checked_function(**given), checked_function(**given)
    assert callable(one) and one is not other
    assert list(inspect.signature(one).parameters) == ["request"]
    assert called == []


def test_checked_function_does_not_call_a_further_callable(root):
    called = []
    shared = Shared(
        str(root),
        hw_profile_of=lambda *arguments: called.append("hw_profile_of"),
        perform=lambda *arguments: called.append("perform"),
    )
    shared.function(dict(REQUEST))
    assert called == [] and shared.order == ["check", "source", "carry_out"]


@pytest.mark.parametrize(
    "step", ["", "Example", "example-step", "1step", "a" * 33, 7, None, ["example"]]
)
def test_checked_function_refuses_a_step_that_is_no_name(step):
    given, called = shared_parts(step=step)
    with pytest.raises(ValueError, match="step"):
        checked_function(**given)
    assert called == []


@pytest.mark.parametrize(
    "numbers,error,message",
    [
        (("candidate",), ValueError, "numbers must be a prefix"),
        (("round", "attempt"), ValueError, "numbers must be a prefix"),
        (("round", "candidate", "attempt", "round"), ValueError, "must be a prefix"),
        (("example",), ValueError, "numbers must be a prefix"),
        (["round"], TypeError, "numbers must be a tuple, got list"),
        ("round", TypeError, "numbers must be a tuple, got str"),
        (None, TypeError, "numbers must be a tuple, got NoneType"),
    ],
)
def test_checked_function_refuses_numbers_of_another_form(numbers, error, message):
    given, called = shared_parts(numbers=numbers)
    with pytest.raises(error, match=message):
        checked_function(**given)
    assert called == []


@pytest.mark.parametrize(
    "name", ["carry_out", "source", "check", "perform", "hw_profile_of"]
)
@pytest.mark.parametrize("value", [None, "example", 1])
def test_checked_function_refuses_a_part_that_is_not_callable(name, value):
    given, called = shared_parts(perform=len, hw_profile_of=len)
    with pytest.raises(TypeError, match=f"^{name} must be callable, got "):
        checked_function(**(given | {name: value}))
    assert called == []


def test_checked_function_checks_in_the_order_of_its_docstring():
    given, _ = shared_parts(
        step=None, numbers=None, carry_out=None, source=None, check=None
    )
    given |= {"hw_profile_of": None, "perform": None}
    with pytest.raises(ValueError, match="step"):
        checked_function(**given)
    given["step"] = STEP
    with pytest.raises(TypeError, match="numbers must be a tuple"):
        checked_function(**given)
    given["numbers"] = ("attempt",)
    with pytest.raises(ValueError, match="numbers must be a prefix"):
        checked_function(**given)
    given["numbers"] = ()
    for name in ("carry_out", "source", "check", "hw_profile_of", "perform"):
        with pytest.raises(TypeError, match=f"^{name} must be callable"):
            checked_function(**given)
        given[name] = len
    assert callable(checked_function(**given))


def test_the_parts_of_checked_function_are_given_by_name_and_all_are_required():
    given, _ = shared_parts()
    with pytest.raises(TypeError):
        checked_function(*given.values())
    for name in given:
        with pytest.raises(TypeError, match=name):
            checked_function(
                **{other: value for other, value in given.items() if other != name}
            )


@pytest.mark.parametrize(
    "numbers,asked,member",
    [
        (NUMBERS, None, "the request must be an object, got NoneType"),
        (NUMBERS, [REQUEST], "the request must be an object, got list"),
        (NUMBERS, without("run_id"), "run_id: is required"),
        (NUMBERS, without("execution"), "execution: is required"),
        (NUMBERS, without("attempt"), "attempt: is required"),
        ((), without("candidate", "attempt"), "round: is no member"),
        (("round",), without("attempt"), "candidate: is no member"),
        (NUMBERS, request(round=None), "round: must be an integer, got null"),
        (NUMBERS, request(run_id="Run A"), "run_id"),
        (NUMBERS, request(run_id=7), "run_id"),
        (NUMBERS, request(execution=0), "execution"),
    ],
)
def test_checked_function_refuses_a_request_before_anything_is_called(
    root, numbers, asked, member
):
    shared = Shared(str(root), numbers=numbers)
    before = snapshot(root)
    with pytest.raises(ToolFailure) as caught:
        shared.function(asked)
    assert caught.value.kind == INVALID == "invalid_request"
    assert member in caught.value.message
    assert shared.order == [] and shared.source.calls == 0
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "refusal",
    [ToolFailure(INVALID, "example_marker: is no member"), KeyError("example"), Died()],
    ids=["a refusal", "another exception", "a death"],
)
def test_checked_function_lets_what_check_raises_pass_through(root, refusal):
    shared = Shared(str(root), refusal=refusal)
    with pytest.raises(type(refusal)) as caught:
        shared.function(dict(REQUEST))
    assert caught.value is refusal
    assert shared.order == ["check"] and shared.source.calls == 0


def test_checked_function_lets_no_data_root_pass_through(tmp_path):
    missing = tmp_path / "missing"
    for answer in (str(missing), OSError("no configuration"), 7):
        shared = Shared(answer)
        with pytest.raises(ToolFailure) as caught:
            shared.function(dict(REQUEST))
        assert caught.value.kind == tools.KIND_NO_DATA_ROOT == "no_data_root"
        assert shared.order == ["check", "source"]
    assert not missing.exists()


@pytest.mark.parametrize(
    "outcome",
    [
        ToolFailure(tools.KIND_STEP_OPEN, "example"),
        StepFailed(SPEND, "example_failure", "no outcome"),
        KeyError("example"),
        Died(),
    ],
    ids=["a tool failure", "a failed step", "another exception", "a death"],
)
def test_checked_function_lets_what_carry_out_raises_pass_through(root, outcome):
    shared = Shared(str(root), outcome=outcome)
    before = snapshot(root)
    with pytest.raises(type(outcome)) as caught:
        shared.function(dict(REQUEST))
    assert caught.value is outcome
    assert shared.order == ["check", "source", "carry_out"]
    assert snapshot(root) == before
