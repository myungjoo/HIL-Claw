import copy
import inspect
import io
import json

import pytest

from hilclaw import __main__ as command_line
from hilclaw import (
    backends,
    events,
    hw_tool,
    instance,
    journal,
    mcp_front,
    mock_backend,
    run_journal,
    run_state,
    tools,
)
from hilclaw.backends import HW_TOOLS, Backend, BackendTable
from hilclaw.hw_tool import tool_function
from hilclaw.journal import EMPTY, Identity
from hilclaw.journaled_step import StepFailed
from hilclaw.keys import InvalidRecordError
from hilclaw.tools import Registry, ToolFailure

# Synthetic values only: no step name, axis, member or record of a real tool or run.
TOOL = "sim.run"
DESCRIPTION = "A journaled HW tool of the tests."
SCHEMA = {"type": "object"}
RUN = "run-a"
OTHER_RUN = "run-b"
LOG = f"runs/{RUN}/events.ndjson"
FILE = f"runs/{RUN}/instance.json"
STEP = "example_step"
SPEND = {"example_axis": 7}
ROUND = 3
NUMBERS = ("round", "candidate", "attempt")
REQUEST = {"run_id": RUN, "round": ROUND, "candidate": 2, "attempt": 1, "execution": 1}
ID = Identity(STEP, 1, ROUND, 2, 1)
OTHER = "acc_b"
FAILURE = {"error": {"kind": "example_failure", "message": "no outcome"}}
REMOVE = object()


class Text(str):
    pass


def record(accelerator=mock_backend.NAME, **changes):
    made = {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }
    for name, value in changes.items():
        if value is REMOVE:
            del made[name]
        else:
            made[name] = value
    return made


class Source:
    def __init__(self, answer, order):
        self.answer, self.order, self.calls = answer, order, 0

    def __call__(self):
        self.calls += 1
        self.order.append("source")
        if isinstance(self.answer, BaseException):
            raise self.answer
        return self.answer


class Tool:
    """The test-only journaled HW tool over a table that holds the mock and one other backend."""

    def __init__(
        self,
        answer,
        *,
        name=TOOL,
        offered=HW_TOOLS,
        table=None,
        profile=None,
        script=None,
        outcome=None,
        numbers=NUMBERS,
    ):
        self.name, self.outcome, self.script_outcome = name, outcome, script
        self.profile = record() if profile is None else profile
        self.by_run = {}
        self.order, self.read, self.asked, self.seen, self.elsewhere = (
            [],
            [],
            [],
            [],
            [],
        )
        self.log_at_reader = self.log_at_script = self.data_root = None
        self.source = Source(answer, self.order)
        self.mock = mock_backend.backend(self.script, offered)
        self.other = Backend(OTHER, {tool: self.other_operation for tool in HW_TOOLS})
        held = [self.mock, self.other] if table is None else table
        self.table = BackendTable(held)
        self.function = tool_function(
            tool=name,
            step=STEP,
            numbers=numbers,
            source=self.source,
            table=self.table,
            hw_profile_of=self.reader,
            check=self.check,
            perform=self.perform,
        )
        self.registry = Registry()
        self.registry.register(name, self.function, DESCRIPTION, SCHEMA)

    @property
    def performed(self):
        return len(self.seen)

    def check(self, request):
        self.order.append("check")
        if "example_marker" in request:
            raise ToolFailure(
                tools.KIND_INVALID_REQUEST, "example_marker: is no member"
            )

    def reader(self, data_root, run_id):
        self.order.append("reader")
        self.read.append((data_root, run_id))
        self.log_at_reader = lines(data_root, run_id)
        profile = self.by_run.get(run_id, self.profile)
        if isinstance(profile, BaseException):
            raise profile
        return profile

    def perform(self, data_root, request, hw_profile, operation):
        self.order.append("perform")
        self.seen.append((data_root, request, hw_profile, operation))
        self.data_root = data_root
        if self.outcome is not None:
            raise self.outcome
        answer = operation(request, hw_profile)
        if "failed" in answer:
            raise StepFailed(SPEND, answer["failed"], "no outcome")
        return SPEND, answer

    def script(self, tool, request, hw_profile):
        self.order.append("script")
        self.asked.append((tool, request, hw_profile))
        self.log_at_script = lines(self.data_root, request["run_id"])
        if self.script_outcome is not None:
            raise self.script_outcome
        if request["execution"] < request.get("example_works_from", 1):
            return {"failed": "example_failure"}
        return {"example_member": request["execution"]}

    def other_operation(self, request, hw_profile):
        self.elsewhere.append((request, hw_profile))
        return {"example_member": "elsewhere"}

    def untouched(self):
        return (self.read, self.asked, self.seen, self.elsewhere) == ([], [], [], [])


def dead(root, **options):
    """A tool whose reader fails and whose table is empty: neither may be asked."""
    profile = RuntimeError("the reader must not be asked")
    return Tool(root, table=[], profile=profile, **options)


def request(**changes):
    return {**REQUEST, **changes}


def without(*names):
    return {name: value for name, value in REQUEST.items() if name not in names}


def by_function(tool, asked):
    try:
        return False, tool.function(asked)
    except ToolFailure as failure:
        return True, failure.error_object()


def by_call(tool, asked):
    try:
        return False, tools.call(tool.registry, tool.name, asked)
    except ToolFailure as failure:
        return True, failure.error_object()


def by_command_line(tool, asked):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        [tool.name],
        registry=tool.registry,
        stdin=io.BytesIO(json.dumps(asked).encode()),
        stdout=stdout,
        stderr=stderr,
    )
    assert status in (0, 3)
    return status == 3, json.loads(stdout.getvalue())


def by_mcp(tool, asked):
    params = {"name": tool.name.replace(".", "_"), "arguments": asked}
    document = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=tool.registry,
        stdin=io.BytesIO(json.dumps(document).encode() + b"\n"),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    answer = json.loads(stdout.getvalue())
    (block,) = answer["result"]["content"]
    return answer["result"]["isError"], json.loads(block["text"])


THROUGH_CALL = {"call": by_call, "cli": by_command_line, "mcp": by_mcp}
WAYS = {"function": by_function, **THROUGH_CALL}
PAIRS = [("function", "cli"), ("cli", "mcp"), ("mcp", "call"), ("call", "function")]
one_then_another = pytest.mark.parametrize("first,second", PAIRS)
each_way = pytest.mark.parametrize("way", list(WAYS))


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


def store(root, run=RUN):
    return place(root, run_state.dump(ROUND, EMPTY), f"runs/{run}/STATE.json")


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    store(path)
    return path


def lines(root, run=RUN):
    found = events.read(root, run).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def snapshot(path):
    return {
        item.relative_to(path).as_posix(): item.read_bytes() if item.is_file() else None
        for item in path.rglob("*")
    }


def selections(monkeypatch, order=None):
    made, real = [] if order is None else order, backends.select

    def select(table, hw_profile, tool):
        made.append("select")
        return real(table, hw_profile, tool)

    monkeypatch.setattr(backends, "select", select)
    return made


# --- happy ---


def test_the_public_names_and_the_signature():
    public = [name for name in vars(hw_tool) if not name.startswith("_")]
    assert [name for name in public if not inspect.ismodule(vars(hw_tool)[name])] == [
        "tool_function"
    ]
    parameters = inspect.signature(tool_function).parameters
    assert list(parameters) == [
        "tool",
        "step",
        "numbers",
        "source",
        "table",
        "hw_profile_of",
        "check",
        "perform",
    ]
    for parameter in parameters.values():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is inspect.Parameter.empty


def test_a_first_call_appends_the_two_lines_and_returns_the_result(root):
    tool = Tool(str(root))
    asked = request(example_other={"nested": [1, 2]})
    assert tool.function(asked) == {"example_member": 1}
    assert lines(root) == [started(), ended(result={"example_member": 1})]
    assert tool.read == [(root, RUN)]
    assert type(tool.read[0][0]) is type(root)
    ((data_root, seen, hw_profile, operation),) = tool.seen
    assert data_root == root and type(data_root) is type(root)
    assert seen is asked and hw_profile is tool.profile
    assert operation is backends.select(tool.table, tool.profile, TOOL)
    ((called, script_request, script_profile),) = tool.asked
    assert called == TOOL
    assert script_request is asked and script_profile is tool.profile
    assert tool.elsewhere == []


@pytest.mark.parametrize("name", HW_TOOLS)
def test_the_operation_handed_over_is_that_of_the_called_tool(root, name):
    tool = Tool(root, name=name)
    assert tool.function(request()) == {"example_member": 1}
    assert tool.seen[0][3] is backends.select(tool.table, record(), name)
    assert [called for called, _, _ in tool.asked] == [name]
    for way in THROUGH_CALL.values():
        assert way(tool, request()) == (False, {"example_member": 1})
    assert tool.performed == 1


def test_the_order_of_a_call(root, monkeypatch):
    tool = Tool(root)
    order = tool.order
    selections(monkeypatch, order)
    real_state, real_append = run_journal.read_state, events.append

    def read_state(*args):
        order.append("lookup")
        return real_state(*args)

    def append(data_root, run_id, kind, data, **numbers):
        order.append(kind)
        return real_append(data_root, run_id, kind, data, **numbers)

    monkeypatch.setattr(run_journal, "read_state", read_state)
    monkeypatch.setattr(events, "append", append)
    assert tool.function(request()) == {"example_member": 1}
    assert order == [
        "check",
        "source",
        "lookup",
        "reader",
        "select",
        "step_started",
        "perform",
        "script",
        "step_ended",
    ]
    assert tool.log_at_reader == []
    assert tool.log_at_script == [started()]
    del order[:]
    assert tool.function(request()) == {"example_member": 1}
    assert order == ["check", "source", "lookup"]


@pytest.mark.parametrize(
    "numbers,asked,identity",
    [
        ((), without(*NUMBERS), Identity(STEP, 1)),
        (("round",), without("candidate", "attempt"), Identity(STEP, 1, ROUND)),
    ],
)
def test_a_tool_that_requires_fewer_numbers(root, numbers, asked, identity):
    tool = Tool(root, numbers=numbers)
    assert tool.function(asked) == {"example_member": 1}
    assert lines(root) == [
        started(identity),
        ended(identity, result={"example_member": 1}),
    ]


@pytest.mark.parametrize(
    "asked,expected",
    [
        (request(), (False, {"example_member": 1})),
        (request(example_works_from=2), (True, FAILURE)),
    ],
    ids=["ok", "failed"],
)
def test_one_request_gives_the_same_outcome_in_every_way(tmp_path, asked, expected):
    logs = []
    for way, through in WAYS.items():
        path = tmp_path / way
        path.mkdir()
        store(path)
        tool = Tool(path)
        assert through(tool, asked) == expected
        assert (len(tool.read), len(tool.asked), tool.performed) == (1, 1, 1)
        logs.append(lines(path))
    assert logs[0] == logs[1] == logs[2] == logs[3]
    assert len(logs[0]) == 2


# --- the three states: nothing is read, selected or called ---


@one_then_another
def test_an_ended_step_is_answered_from_the_log_without_a_backend(root, first, second):
    tool = Tool(root)
    assert WAYS[first](tool, request()) == (False, {"example_member": 1})
    before = snapshot(root)
    gone = dead(root)
    assert WAYS[second](gone, request()) == (False, {"example_member": 1})
    assert WAYS[first](gone, request()) == (False, {"example_member": 1})
    assert WAYS[second](tool, request()) == (False, {"example_member": 1})
    assert gone.untouched()
    assert (len(tool.read), len(tool.asked), tool.performed) == (1, 1, 1)
    assert snapshot(root) == before


@one_then_another
def test_an_ended_step_with_a_failure_fails_again_without_a_backend(
    root, first, second
):
    tool = Tool(root)
    asked = request(example_works_from=2)
    assert WAYS[first](tool, asked) == (True, FAILURE)
    assert lines(root) == [started(), ended(failure=FAILURE["error"])]
    before = snapshot(root)
    gone = dead(root)
    assert WAYS[second](gone, asked) == (True, FAILURE)
    assert WAYS[second](gone, request()) == (True, FAILURE)
    assert gone.untouched()
    assert snapshot(root) == before


@each_way
def test_an_open_step_is_step_open_without_a_backend(root, monkeypatch, way):
    place(root, raw(started()))
    before = snapshot(root)
    made = selections(monkeypatch)
    for tool in (Tool(root), dead(root)):
        failed, answer = WAYS[way](tool, request())
        assert (failed, answer["error"]["kind"]) == (True, "step_open")
        assert tool.untouched()
    assert made == []
    assert snapshot(root) == before


def test_no_backend_is_selected_for_an_ended_step(root, monkeypatch):
    tool = Tool(root)
    made = selections(monkeypatch)
    tool.function(request())
    assert made == ["select"]
    tool.function(request())
    assert made == ["select"]


def test_a_further_execution_is_another_identity_and_reaches_the_backend(root):
    tool = Tool(root)
    assert tool.function(request()) == {"example_member": 1}
    assert tool.function(request(execution=2)) == {"example_member": 2}
    assert tool.function(request()) == {"example_member": 1}
    assert [asked["execution"] for _, asked, _ in tool.asked] == [1, 2]
    assert len(tool.read) == 2
    assert [line["data"]["execution"] for line in lines(root)] == [1, 1, 2, 2]


def test_fails_first_then_works_is_written_over_execution(root):
    tool = Tool(root)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request(example_works_from=2))
    assert caught.value.error_object() == FAILURE
    with pytest.raises(ToolFailure):
        tool.function(request(example_works_from=2))
    assert tool.performed == 1
    again = request(execution=2, example_works_from=2)
    assert tool.function(again) == {"example_member": 2}
    assert tool.performed == 2
    assert [line["kind"] for line in lines(root)] == ["step_started", "step_ended"] * 2


# --- the selection fails: no line, nothing called, repeatable ---

NOT_SELECTED = [
    pytest.param({"table": []}, "no_backend", id="no_backend"),
    pytest.param({"offered": ["board.run"]}, "not_offered", id="not_offered"),
    pytest.param({"offered": []}, "not_offered", id="offers-nothing"),
]


@pytest.mark.parametrize("options,kind", NOT_SELECTED)
def test_a_failed_selection_leaves_no_line_and_can_be_repeated(root, options, kind):
    before = snapshot(root)
    tool = Tool(root, **options)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request())
    assert caught.value.kind == kind
    outcomes = [through(tool, request()) for through in THROUGH_CALL.values()]
    assert outcomes == [(True, caught.value.error_object())] * 3
    assert outcomes[0][1]["error"]["kind"] == kind
    assert len(tool.read) == 4
    assert (tool.asked, tool.seen, tool.elsewhere) == ([], [], [])
    assert snapshot(root) == before
    for through in WAYS.values():
        corrected = Tool(root)
        assert through(corrected, request()) == (False, {"example_member": 1})
    assert lines(root) == [started(), ended(result={"example_member": 1})]


def test_no_backend_names_the_accelerator_of_the_run(root):
    tool = Tool(root, profile=record("acc_c"))
    with pytest.raises(ToolFailure) as caught:
        tool.function(request())
    assert caught.value.kind == tools.KIND_NO_BACKEND == "no_backend"
    assert "acc_c" in caught.value.message
    assert (tool.asked, tool.seen, tool.elsewhere) == ([], [], [])
    assert lines(root) == []


# --- before the selection ---


@pytest.mark.parametrize(
    "numbers,asked,member",
    [
        (NUMBERS, without("run_id"), "run_id"),
        (NUMBERS, without("execution"), "execution"),
        (NUMBERS, request(execution=0), "execution"),
        (NUMBERS, without("attempt"), "attempt"),
        (("round",), without("attempt"), "candidate"),
        (NUMBERS, request(example_marker=1), "example_marker"),
        (NUMBERS, [REQUEST], "the request must be an object"),
    ],
)
def test_a_refused_request_asks_no_source_no_reader_and_no_table(
    root, monkeypatch, numbers, asked, member
):
    before, given = snapshot(root), copy.deepcopy(asked)
    made = selections(monkeypatch)
    tool = Tool(root, numbers=numbers)
    with pytest.raises(ToolFailure) as caught:
        tool.function(asked)
    assert caught.value.kind == "invalid_request"
    assert member in caught.value.message
    assert tool.source.calls == 0 and tool.untouched() and made == []
    assert asked == given
    assert snapshot(root) == before


@each_way
def test_a_failing_source_is_no_data_root_and_asks_no_reader(
    tmp_path, monkeypatch, way
):
    made = selections(monkeypatch)
    for answer in (tmp_path / "missing", RuntimeError("no configuration")):
        tool = Tool(answer)
        failed, outcome = WAYS[way](tool, request())
        assert (failed, outcome["error"]["kind"]) == (True, "no_data_root")
        assert tool.source.calls == 1 and tool.untouched()
    assert made == []
    assert list(tmp_path.iterdir()) == []


def test_a_run_that_cannot_be_read_is_found_before_the_reader_is_asked(tmp_path):
    tool = Tool(tmp_path)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request())
    assert caught.value.kind == tools.KIND_RUN_FILE_MISSING == "run_file_missing"
    assert type(caught.value.__cause__) is run_journal.MissingStateError
    assert tool.source.calls == 1 and tool.untouched()
    assert snapshot(tmp_path) == {}


# --- the reader ---

MAPPED = [
    pytest.param(
        instance.MissingInstanceError(f"{FILE}: is missing: of the tests"),
        "run_file_missing",
        id="MissingInstanceError",
    ),
    pytest.param(
        instance.InvalidInstanceError(f"{FILE}: content: of the tests"),
        "run_file_invalid",
        id="InvalidInstanceError",
    ),
    pytest.param(
        instance.UnsupportedVersionError(f"{FILE}: schema_version: of the tests"),
        "run_file_unsupported",
        id="UnsupportedVersionError",
    ),
    pytest.param(
        instance.InvalidInstanceError("the text of another reader"),
        "run_file_invalid",
        id="another-message",
    ),
    pytest.param(
        FileNotFoundError(2, "No such file", "/elsewhere/instance.json"),
        "run_file_missing",
        id="FileNotFoundError",
    ),
    pytest.param(
        NotADirectoryError(20, "Not a directory", "/elsewhere/instance.json"),
        "run_file_missing",
        id="NotADirectoryError",
    ),
    pytest.param(
        OSError(5, "Input/output error", "/elsewhere/instance.json"),
        "run_file_unreadable",
        id="OSError",
    ),
    pytest.param(
        PermissionError(13, "Permission denied", "/elsewhere/instance.json"),
        "run_file_unreadable",
        id="PermissionError",
    ),
    pytest.param(OSError("no errno"), "run_file_unreadable", id="OSError-bare"),
]
by_class = pytest.mark.parametrize(
    "error", [case.values[0] for case in MAPPED], ids=[case.id for case in MAPPED]
)
PASSED = {
    "KeyError": (KeyError("example_run"), "tool_crashed"),
    "RuntimeError": (RuntimeError("of the tests"), "tool_crashed"),
    "a kind of the tests": (
        ToolFailure("example_unreadable", "of the tests"),
        "example_unreadable",
    ),
    "tool_crashed": (ToolFailure("tool_crashed", "of the tests"), "tool_crashed"),
}
ENDS_THE_PROCESS = {"exit": SystemExit(9), "interrupt": KeyboardInterrupt()}
NO_RECORD = [record(accelerator=REMOVE), record(revision=7), {}, "text", None, 7]


def assert_nothing_followed(tool, root, before):
    assert (tool.asked, tool.seen, tool.elsewhere) == ([], [], [])
    assert snapshot(root) == before


def expected_message(error):
    if not isinstance(error, OSError):
        return str(error)
    if isinstance(error, (FileNotFoundError, NotADirectoryError)):
        return f"{FILE}: is missing"
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    return f"{FILE}: could not be read: {reported}"


@pytest.mark.parametrize("error,kind", MAPPED)
def test_what_the_reader_raises_for_the_file_is_answered_with_its_kind(
    root, monkeypatch, error, kind
):
    before = snapshot(root)
    made = selections(monkeypatch)
    tool = Tool(root, profile=error)
    with pytest.raises(ToolFailure) as caught:
        tool.function(request())
    assert caught.value.kind == kind
    assert caught.value.__cause__ is error
    assert caught.value.message == expected_message(error)
    assert "elsewhere" not in caught.value.message
    assert tool.read == [(root, RUN)] and made == []
    assert_nothing_followed(tool, root, before)


@pytest.mark.parametrize("error,kind", MAPPED)
def test_such_a_run_is_answered_alike_in_every_way_and_can_be_repeated(
    root, monkeypatch, error, kind
):
    before = snapshot(root)
    made = selections(monkeypatch)
    tool = Tool(root, profile=error)
    outcomes = [through(tool, request()) for through in WAYS.values()]
    answer = {"error": {"kind": kind, "message": expected_message(error)}}
    assert outcomes == [(True, answer)] * 4
    assert len(tool.read) == 4 and made == []
    assert_nothing_followed(tool, root, before)
    tool.profile = record()
    for through in WAYS.values():
        assert through(tool, request()) == (False, {"example_member": 1})
    assert (len(tool.read), tool.performed, made) == (5, 1, ["select"])
    assert lines(root) == [started(), ended(result={"example_member": 1})]


def test_a_data_root_gone_at_the_read_is_said_in_the_message(root):
    tool = Tool(root)

    def reader(data_root, run_id):
        (root / f"runs/{RUN}/STATE.json").unlink()
        (root / f"runs/{RUN}").rmdir()
        (root / "runs").rmdir()
        root.rmdir()
        raise FileNotFoundError(f"data root is not an existing directory: {root}")

    function = tool_function(
        tool=TOOL,
        step=STEP,
        numbers=NUMBERS,
        source=lambda: root,
        table=tool.table,
        hw_profile_of=reader,
        check=tool.check,
        perform=tool.perform,
    )
    with pytest.raises(ToolFailure) as caught:
        function(request())
    gone = f"{FILE}: is missing: the data root is not an existing directory"
    assert (caught.value.kind, caught.value.message) == ("run_file_missing", gone)
    assert tool.untouched() and not root.exists()
    with pytest.raises(ToolFailure) as caught:
        function(request())
    assert caught.value.kind == "no_data_root"


@pytest.mark.parametrize(
    "error",
    [*(error for error, _ in PASSED.values()), *ENDS_THE_PROCESS.values()],
    ids=[*PASSED, *ENDS_THE_PROCESS],
)
def test_what_else_the_reader_raises_passes_through_as_the_same_object(
    root, monkeypatch, error
):
    before = snapshot(root)
    made = selections(monkeypatch)
    tool = Tool(root, profile=error)
    with pytest.raises(type(error)) as caught:
        tool.function(request())
    assert caught.value is error
    assert error.__cause__ is None
    assert tool.read == [(root, RUN)] and made == []
    assert_nothing_followed(tool, root, before)


@pytest.mark.parametrize("profile", NO_RECORD, ids=repr)
def test_what_is_no_valid_record_is_refused_by_the_selection(root, profile):
    before = snapshot(root)
    tool = Tool(root)
    tool.profile = profile
    with pytest.raises(InvalidRecordError) as caught:
        tool.function(request())
    assert not isinstance(caught.value, ToolFailure)
    assert_nothing_followed(tool, root, before)


@by_class
def test_the_same_class_out_of_the_selection_is_not_answered_with_a_kind(
    root, monkeypatch, error
):
    before = snapshot(root)

    def select(table, hw_profile, tool):
        raise error

    monkeypatch.setattr(backends, "select", select)
    tool = Tool(root)
    with pytest.raises(type(error)) as caught:
        tool.function(request())
    assert caught.value is error
    for through in THROUGH_CALL.values():
        failed, answer = through(tool, request())
        assert (failed, answer["error"]["kind"]) == (True, "tool_crashed")
    assert len(tool.read) == 4
    assert_nothing_followed(tool, root, before)


@pytest.mark.parametrize(
    "profile,kind",
    [*((profile, "tool_crashed") for profile in NO_RECORD), *PASSED.values()],
    ids=[*map(repr, NO_RECORD), *PASSED],
)
def test_what_is_no_situation_of_the_file_keeps_its_answer_and_can_be_repeated(
    root, profile, kind
):
    before = snapshot(root)
    tool = Tool(root)
    tool.profile = profile
    outcomes = [through(tool, request()) for through in THROUGH_CALL.values()]
    assert outcomes[0] == outcomes[1] == outcomes[2]
    failed, answer = outcomes[0]
    assert (failed, answer["error"]["kind"]) == (True, kind)
    assert len(tool.read) == 3
    assert_nothing_followed(tool, root, before)
    tool.profile = record()
    assert tool.function(request()) == {"example_member": 1}
    assert tool.performed == 1


@by_class
def test_an_ended_and_an_open_identity_are_answered_without_the_reader(root, error):
    assert Tool(root).function(request()) == {"example_member": 1}
    store(root, OTHER_RUN)
    place(root, raw(started()), f"runs/{OTHER_RUN}/events.ndjson")
    before = snapshot(root)
    tool = Tool(root, table=[], profile=error)
    for through in WAYS.values():
        assert through(tool, request()) == (False, {"example_member": 1})
        failed, answer = through(tool, request(run_id=OTHER_RUN))
        assert (failed, answer["error"]["kind"]) == (True, "step_open")
    assert tool.untouched()
    assert snapshot(root) == before


@by_class
@pytest.mark.parametrize("line", ["step_started", "step_ended"])
def test_the_same_class_out_of_an_append_is_not_answered_with_a_kind(
    root, monkeypatch, line, error
):
    real = events.append

    def append(data_root, run_id, kind, data, **numbers):
        if kind == line:
            raise error
        return real(data_root, run_id, kind, data, **numbers)

    monkeypatch.setattr(events, "append", append)
    tool = Tool(root)
    with pytest.raises(type(error)) as caught:
        tool.function(request())
    assert caught.value is error
    assert (len(tool.read), tool.performed) == (1, line == "step_ended")
    failed, answer = by_call(tool, request(execution=2))
    assert (failed, answer["error"]["kind"]) == (True, "tool_crashed")


@by_class
@pytest.mark.parametrize("where", ["script", "outcome"])
def test_the_same_class_out_of_the_step_is_not_answered_and_leaves_it_open(
    root, where, error
):
    tool = Tool(root, **{where: error})
    with pytest.raises(type(error)) as caught:
        tool.function(request())
    assert caught.value is error
    assert tool.performed == 1
    assert lines(root) == [started()]
    for execution, through in enumerate(THROUGH_CALL.values(), start=2):
        failed, answer = through(tool, request(execution=execution))
        assert (failed, answer["error"]["kind"]) == (True, "tool_crashed")
        failed, answer = through(dead(root), request(execution=execution))
        assert (failed, answer["error"]["kind"]) == (True, "step_open")
    assert tool.performed == 4
    assert [line["kind"] for line in lines(root)] == ["step_started"] * 4


# --- the death point a backend can cause ---


@one_then_another
@pytest.mark.parametrize(
    "error", [SystemExit(9), KeyboardInterrupt()], ids=["exit", "interrupt"]
)
def test_a_script_that_ends_the_process_leaves_the_step_open(
    root, first, second, error
):
    tool = Tool(root, script=error)
    with pytest.raises(type(error)) as caught:
        tool.function(request())
    assert caught.value is error
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert lines(root) == [started()]
    before = snapshot(root)
    for way in (first, second):
        gone = dead(root)
        failed, answer = WAYS[way](gone, request())
        assert (failed, answer["error"]["kind"]) == (True, "step_open")
        assert gone.untouched()
    assert snapshot(root) == before


@one_then_another
@pytest.mark.parametrize("where", ["script", "outcome"])
def test_a_crash_inside_the_step_leaves_it_open(root, first, second, where):
    error = RuntimeError("died")
    tool = Tool(root, **{where: error})
    if first == "function":
        with pytest.raises(RuntimeError) as caught:
            tool.function(request())
        assert caught.value is error
    else:
        failed, answer = WAYS[first](tool, request())
        assert failed is True
        assert answer["error"]["kind"] == "tool_crashed"
    assert tool.performed == 1
    assert len(tool.asked) == (1 if where == "script" else 0)
    assert lines(root) == [started()]
    before = snapshot(root)
    gone = dead(root)
    failed, answer = WAYS[second](gone, request())
    assert (failed, answer["error"]["kind"]) == (True, "step_open")
    assert gone.untouched()
    assert snapshot(root) == before


def test_a_step_that_raises_step_failed_gives_an_end_line_with_the_failure(root):
    tool = Tool(root, outcome=StepFailed(SPEND, "example_failure", "no outcome"))
    assert by_function(tool, request()) == (True, FAILURE)
    assert lines(root) == [started(), ended(failure=FAILURE["error"])]
    assert tool.asked == []
    assert by_call(dead(root), request()) == (True, FAILURE)


# --- nothing is kept between calls ---


def test_two_runs_of_two_accelerators_reach_two_backends_of_one_table(root):
    store(root, OTHER_RUN)
    tool = Tool(root)
    there = record(OTHER)
    tool.by_run = {OTHER_RUN: there}
    assert tool.function(request()) == {"example_member": 1}
    assert tool.function(request(run_id=OTHER_RUN)) == {"example_member": "elsewhere"}
    assert tool.function(request(execution=2)) == {"example_member": 2}
    assert tool.read == [(root, RUN), (root, OTHER_RUN), (root, RUN)]
    assert [asked["run_id"] for _, asked, _ in tool.asked] == [RUN, RUN]
    assert [asked["run_id"] for asked, _ in tool.elsewhere] == [OTHER_RUN]
    assert tool.elsewhere[0][1] is there
    assert [seen[3] for seen in tool.seen] == [
        backends.select(tool.table, record(), TOOL),
        tool.other_operation,
        backends.select(tool.table, record(), TOOL),
    ]
    assert len(lines(root)) == 4 and len(lines(root, OTHER_RUN)) == 2


def test_a_change_of_what_the_reader_returns_is_seen_at_the_next_identity(root):
    tool = Tool(root)
    assert tool.function(request()) == {"example_member": 1}
    tool.profile = record(OTHER)
    assert tool.function(request()) == {"example_member": 1}
    assert tool.function(request(execution=2)) == {"example_member": "elsewhere"}
    tool.profile = record("acc_c")
    with pytest.raises(ToolFailure) as caught:
        tool.function(request(execution=3))
    assert caught.value.kind == "no_backend"
    assert len(tool.read) == 3
    assert len(lines(root)) == 4


def test_the_request_and_the_record_are_not_modified(root):
    tool = Tool(root)
    asked = request(example_other={"nested": [1, 2]})
    given, profile = copy.deepcopy(asked), copy.deepcopy(tool.profile)
    tool.function(asked)
    tool.function(asked)
    assert asked == given
    assert tool.profile == profile


def test_the_run_and_the_identity_are_those_checked_before_the_own_check(root):
    store(root, OTHER_RUN)
    read = []

    def reader(data_root, run_id):
        read.append(run_id)
        return record()

    function = tool_function(
        tool=TOOL,
        step=STEP,
        numbers=NUMBERS,
        source=lambda: root,
        table=BackendTable([mock_backend.backend(lambda *call: {}, [TOOL])]),
        hw_profile_of=reader,
        check=lambda asked: asked.update(run_id=OTHER_RUN, round=9, execution=2),
        perform=lambda data_root, asked, hw_profile, operation: (SPEND, {}),
    )
    assert function(request()) == {}
    assert read == [RUN]
    assert lines(root) == [started(), ended(result={})]
    assert lines(root, OTHER_RUN) == []


# --- building ---

TABLE = BackendTable([])
PARTS = ("source", "hw_profile_of", "check", "perform")


def build(**changes):
    called = []

    def part(name):
        return lambda *args: called.append(name)

    given = {
        "tool": TOOL,
        "step": STEP,
        "numbers": NUMBERS,
        "table": TABLE,
        **{name: part(name) for name in PARTS},
    }
    given.update(changes)
    return given, called


def test_building_calls_nothing_and_asks_the_table_nothing(monkeypatch):
    made = selections(monkeypatch)
    given, called = build()
    assert callable(tool_function(**given))
    assert called == [] and made == []


@pytest.mark.parametrize(
    "changes,error,message",
    [
        ({"tool": "blob.push"}, ValueError, "is no HW tool"),
        ({"tool": "sim"}, ValueError, "is no HW tool"),
        ({"tool": ""}, ValueError, "is no HW tool"),
        ({"tool": 7}, TypeError, "must be a str"),
        ({"tool": None}, TypeError, "must be a str"),
        ({"tool": Text(TOOL)}, TypeError, "must be a str"),
        ({"tool": [TOOL]}, TypeError, "must be a str"),
        ({"table": None}, TypeError, "table must be a BackendTable, got NoneType"),
        ({"table": {}}, TypeError, "table must be a BackendTable, got dict"),
        ({"table": []}, TypeError, "table must be a BackendTable, got list"),
        ({"table": Backend("acc_a", {})}, TypeError, "got Backend"),
        ({"table": BackendTable}, TypeError, "got type"),
        ({"step": "Bad Step"}, ValueError, "step"),
        ({"step": None}, ValueError, "step"),
        ({"numbers": ("candidate",)}, ValueError, "numbers must be a prefix"),
        ({"numbers": list(NUMBERS)}, TypeError, "numbers must be a tuple"),
        *(
            ({name: value}, TypeError, f"{name} must be callable")
            for name in PARTS
            for value in (None, "text")
        ),
    ],
)
def test_what_cannot_be_built_is_refused_and_nothing_is_called(
    monkeypatch, changes, error, message
):
    made = selections(monkeypatch)
    given, called = build(**changes)
    with pytest.raises(error, match=message):
        tool_function(**given)
    assert called == [] and made == []


def test_the_checks_come_in_the_order_tool_table_then_the_journaled_parts():
    given, _ = build(tool="sim", table=None, step=None, source=None)
    with pytest.raises(ValueError, match="is no HW tool"):
        tool_function(**given)
    with pytest.raises(TypeError, match="table must be a BackendTable"):
        tool_function(**(given | {"tool": TOOL}))
    with pytest.raises(journal.JournalError):
        tool_function(**(given | {"tool": TOOL, "table": TABLE}))
    with pytest.raises(TypeError, match="source must be callable"):
        tool_function(**(given | {"tool": TOOL, "table": TABLE, "step": STEP}))


def test_a_parameter_cannot_be_given_by_position_or_left_out():
    given, _ = build()
    with pytest.raises(TypeError):
        tool_function(*given.values())
    for name in given:
        with pytest.raises(TypeError):
            tool_function(
                **{other: value for other, value in given.items() if other != name}
            )
