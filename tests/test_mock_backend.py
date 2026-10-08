import copy
import io
import json
import re
from types import MappingProxyType

import pytest

from hilclaw import __main__ as command_line
from hilclaw import mcp_front, mock_backend, tools
from hilclaw.backends import HW_TOOLS, Backend, BackendTable, select
from hilclaw.mock_backend import NAME, backend
from hilclaw.tools import Registry, ToolFailure

DESCRIPTION = "A tool of the tests."
SCHEMA = {"type": "object"}


class Asked:
    def __init__(self, answer=None):
        self.answer = answer
        self.calls = []

    def __call__(self, tool, request, hw_profile):
        self.calls.append((tool, request, hw_profile))
        return self.answer


class Text(str):
    pass


def record(accelerator=NAME):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }


def raising(error):
    def script(tool, request, hw_profile):
        raise error

    return script


def fails_first(tool, request, hw_profile):
    if request["execution"] == 1:
        raise ToolFailure("example_fault", "the first execution fails")
    return {"example_member": request["execution"]}


def operation_of(script, tool="sim.run", offered=HW_TOOLS):
    return select(BackendTable([backend(script, offered)]), record(), tool)


def failure_of(table, hw_profile, tool):
    with pytest.raises(ToolFailure) as raised:
        select(table, hw_profile, tool)
    return raised.value


# The reserved name and the backend


def test_the_reserved_name_is_a_name():
    assert type(NAME) is str
    assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", NAME)
    assert mock_backend.NAME is NAME


@pytest.mark.parametrize("count", [0, 1, 2, 4])
def test_a_mock_is_a_backend_of_the_reserved_name_offering_its_tools(count):
    script = Asked()
    made = backend(script, HW_TOOLS[:count])
    assert type(made) is Backend
    assert made.name == NAME
    assert made.offered() == tuple(sorted(HW_TOOLS[:count]))
    assert BackendTable([made]).names() == (NAME,)
    assert script.calls == []


def test_the_tools_may_be_any_iterable_of_names():
    for offered in (
        ["board.run", "sim.run"],
        {"board.run", "sim.run"},
        frozenset({"board.run", "sim.run"}),
        (tool for tool in ("sim.run", "board.run")),
    ):
        assert backend(Asked(), offered).offered() == ("board.run", "sim.run")


def test_a_script_may_be_any_callable():
    assert operation_of(lambda tool, request, hw_profile: tool)({}, record()) == (
        "sim.run"
    )
    assert operation_of(Asked({"example_member": 1}))({}, record()) == {
        "example_member": 1
    }


def test_the_operation_returns_the_very_object_the_script_returned():
    for answer in ({"example_member": 1}, ["no", "result"], None, object()):
        assert operation_of(Asked(answer))({}, record()) is answer


# What the script is asked with, and when


@pytest.mark.parametrize("tool", HW_TOOLS)
def test_the_script_is_asked_once_with_the_tool_the_request_and_the_hw_profile(tool):
    script = Asked({"example_member": 1})
    request, hw_profile = {"example_argument": [1, 2]}, record()
    operation_of(script, tool)(request, hw_profile)
    ((asked_tool, asked_request, asked_hw_profile),) = script.calls
    assert asked_tool == tool
    assert asked_request is request
    assert asked_hw_profile is hw_profile


def test_building_and_selecting_ask_the_script_nothing():
    script = Asked()
    table = BackendTable([backend(script, HW_TOOLS)])
    operations = [select(table, record(), tool) for tool in HW_TOOLS]
    assert script.calls == []
    operations[0]({}, record())
    operations[0]({}, record())
    assert len(script.calls) == 2


def test_each_tool_has_an_operation_of_its_own():
    table = BackendTable([backend(Asked(), HW_TOOLS)])
    operations = [select(table, record(), tool) for tool in HW_TOOLS]
    assert len({id(operation) for operation in operations}) == 4
    assert select(table, record(), "sim.run") is operations[0]
    assert repr(operations[0]) == "<operation of the mock backend for 'sim.run'>"
    assert "board.run" in repr(operations[1])


@pytest.mark.parametrize(
    "call",
    [
        lambda operation: operation({}),
        lambda operation: operation(),
        lambda operation: operation({}, record(), "more"),
        lambda operation: operation({}, hw_profile=record()),
        lambda operation: operation(request={}, hw_profile=record()),
        lambda operation: operation({}, record(), data_root="x"),
    ],
    ids=[
        "the request alone",
        "nothing",
        "a third argument",
        "the hw_profile by keyword",
        "both by keyword",
        "a further keyword",
    ],
)
def test_an_operation_takes_the_request_and_the_hw_profile_and_nothing_else(call):
    script = Asked()
    with pytest.raises(TypeError):
        call(operation_of(script))
    assert script.calls == []


# What a script can express


def test_a_script_expresses_a_result_and_a_result_of_a_failed_experiment():
    worked = {"example_member": 1}
    failed = {"example_failed": True, "example_reason": "a reason of the tests"}

    def script(tool, request, hw_profile):
        return failed if request["example_fail"] else worked

    operation = operation_of(script)
    assert operation({"example_fail": False}, record()) is worked
    assert operation({"example_fail": True}, record()) is failed


@pytest.mark.parametrize(
    "kind", ["example_fault", "invalid_request", "tool_crashed", "no_backend"]
)
def test_a_tool_failure_of_the_script_passes_through_as_the_same_object(kind):
    failure = ToolFailure(kind, "a message of the tests")
    with pytest.raises(ToolFailure) as raised:
        operation_of(raising(failure))({}, record())
    assert raised.value is failure
    assert raised.value.__cause__ is None


def test_fails_first_then_works_is_written_over_execution_and_not_counted():
    operation = operation_of(fails_first)
    for _ in range(2):
        with pytest.raises(ToolFailure) as raised:
            operation({"execution": 1}, record())
        assert raised.value.error_object() == {
            "error": {"kind": "example_fault", "message": "the first execution fails"}
        }
    for _ in range(2):
        assert operation({"execution": 2}, record()) == {"example_member": 2}
    with pytest.raises(ToolFailure):
        operation({"execution": 1}, record())


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("a fault of the tests"),
        KeyError("example_member"),
        SystemExit(3),
        KeyboardInterrupt(),
    ],
    ids=["RuntimeError", "KeyError", "SystemExit", "KeyboardInterrupt"],
)
def test_what_is_no_tool_failure_passes_through_as_the_same_object(error):
    with pytest.raises(BaseException) as raised:
        operation_of(raising(error))({}, record())
    assert raised.value is error
    assert raised.value.__cause__ is None


# Two mocks


def test_two_mocks_bound_to_two_scripts_stay_apart():
    a, b = Asked({"answered_by": "a"}), Asked({"answered_by": "b"})
    one = BackendTable([backend(a, HW_TOOLS)])
    other = BackendTable([backend(b, ["sim.run"])])
    assert select(one, record(), "sim.run")({}, record()) == {"answered_by": "a"}
    assert select(other, record(), "sim.run")({}, record()) == {"answered_by": "b"}
    assert (len(a.calls), len(b.calls)) == (1, 1)
    assert failure_of(other, record(), "board.run").kind == "not_offered"
    assert select(one, record(), "board.run")({}, record()) == {"answered_by": "a"}
    assert (len(a.calls), len(b.calls)) == (2, 1)


def test_one_script_bound_to_two_mocks_is_asked_by_both():
    script = Asked()
    one = BackendTable([backend(script, ["sim.run"])])
    other = BackendTable([backend(script, ["board.run"])])
    select(one, record(), "sim.run")({"example_from": 1}, record())
    select(other, record(), "board.run")({"example_from": 2}, record())
    assert [(tool, request) for tool, request, _ in script.calls] == [
        ("sim.run", {"example_from": 1}),
        ("board.run", {"example_from": 2}),
    ]


# Building: what is refused


@pytest.mark.parametrize("script", [None, "script", {"sim.run": 1}, 7])
@pytest.mark.parametrize("offered", [(), HW_TOOLS], ids=["no tools", "all four"])
def test_a_script_that_is_not_callable_is_refused(script, offered):
    with pytest.raises(TypeError, match="must be callable"):
        backend(script, offered)


@pytest.mark.parametrize(
    "tool", ["blob.push", "blob.fetch", "example.tool", "sim_run", "SIM.RUN", ""]
)
def test_a_tool_that_is_no_hw_tool_is_refused(tool):
    script = Asked()
    with pytest.raises(ValueError, match="no HW tool"):
        backend(script, ["board.run", tool])
    assert script.calls == []


@pytest.mark.parametrize("tool", [7, None, ("sim.run",), Text("sim.run"), ["sim.run"]])
def test_a_tool_that_is_no_str_is_refused(tool):
    script = Asked()
    with pytest.raises(TypeError):
        backend(script, ["board.run", tool])
    assert script.calls == []


@pytest.mark.parametrize("offered", [None, 7, len])
def test_tools_that_are_not_iterable_are_refused(offered):
    script = Asked()
    with pytest.raises(TypeError):
        backend(script, offered)
    assert script.calls == []


@pytest.mark.parametrize("offered", ["sim.run", "", Text("sim.run")])
def test_a_str_in_place_of_the_tools_is_refused(offered):
    script = Asked()
    with pytest.raises(TypeError, match="not a "):
        backend(script, offered)
    assert script.calls == []


@pytest.mark.parametrize(
    "offered",
    [{"sim.run": len}, {}, MappingProxyType({"sim.run": None})],
    ids=["a dict of operations", "an empty dict", "a mapping proxy"],
)
def test_a_mapping_in_place_of_the_tools_is_refused(offered):
    script = Asked()
    with pytest.raises(TypeError, match="iterable of names"):
        backend(script, offered)
    assert script.calls == []


def test_bytes_in_place_of_the_tools_are_refused():
    with pytest.raises(TypeError):
        backend(Asked(), b"sim.run")


@pytest.mark.parametrize(
    "offered",
    [
        ["sim.run", "sim.run"],
        ["sim.run", "board.run", "sim.run"],
        HW_TOOLS + HW_TOOLS,
    ],
)
def test_a_tool_given_twice_is_refused(offered):
    script = Asked()
    with pytest.raises(ValueError, match="given twice"):
        backend(script, offered)
    assert script.calls == []


def test_a_tool_that_is_no_hw_tool_is_refused_before_one_given_twice():
    with pytest.raises(ValueError, match="no HW tool"):
        backend(Asked(), ["sim.run", "sim.run", "blob.push"])


# The two kinds are no matter of a script


def test_a_table_without_the_mock_is_no_backend():
    script = Asked()
    backend(script, HW_TOOLS)
    table = BackendTable([Backend("acc_a", {})])
    for tool in HW_TOOLS:
        assert failure_of(table, record(), tool).kind == "no_backend"
    assert failure_of(BackendTable([]), record(), "sim.run").kind == "no_backend"
    assert script.calls == []


@pytest.mark.parametrize("tool", HW_TOOLS)
def test_a_mock_built_without_the_operation_of_the_tool_is_not_offered(tool):
    script = Asked()
    others = [other for other in HW_TOOLS if other != tool]
    table = BackendTable([backend(script, others)])
    assert failure_of(table, record(), tool).kind == "not_offered"
    assert failure_of(BackendTable([backend(script, ())]), record(), tool).kind == (
        "not_offered"
    )
    assert script.calls == []


def test_a_record_of_another_accelerator_does_not_reach_the_mock():
    script = Asked()
    table = BackendTable([backend(script, HW_TOOLS)])
    for accelerator in ("acc_a", NAME + "_", NAME[:-1], "a" + NAME):
        failure = failure_of(table, record(accelerator), "sim.run")
        assert failure.kind == "no_backend"
    assert script.calls == []


# The reserved name has one backend


def test_a_table_takes_one_backend_of_the_reserved_name():
    script = Asked()
    with pytest.raises(ValueError, match=f"{NAME} is given twice"):
        BackendTable([backend(script, HW_TOOLS), backend(script, ())])
    with pytest.raises(ValueError, match=f"{NAME} is given twice"):
        BackendTable([backend(script, HW_TOOLS), Backend(NAME, {})])
    with pytest.raises(ValueError, match=f"{NAME} is given twice"):
        BackendTable([Backend(NAME, {"sim.run": len}), backend(script, HW_TOOLS)])
    assert script.calls == []


# Nothing is kept and nothing is changed


def test_a_call_leaves_the_request_and_the_record_as_they_are():
    request = {"execution": 2, "example_argument": {"nested": [1, 2]}}
    hw_profile = record()
    before = copy.deepcopy(request), copy.deepcopy(hw_profile)
    operation = operation_of(fails_first)
    assert operation(request, hw_profile) == operation(request, hw_profile)
    request["execution"] = 1
    with pytest.raises(ToolFailure):
        operation(request, hw_profile)
    request["execution"] = 2
    assert (request, hw_profile) == before


def test_a_later_change_of_the_tools_changes_nothing():
    script = Asked({"example_member": 1})
    offered = ["sim.run"]
    made = backend(script, offered)
    table = BackendTable([made])
    offered.append("board.run")
    offered.remove("sim.run")
    assert made.offered() == ("sim.run",)
    assert select(table, record(), "sim.run")({}, record()) == {"example_member": 1}
    assert failure_of(table, record(), "board.run").kind == "not_offered"


def test_the_module_has_the_name_and_the_builder_and_holds_nothing_else():
    public = {name for name in dir(mock_backend) if not name.startswith("_")}
    assert public == {"NAME", "backend", "backends", "Mapping"}
    held = {name for name in vars(mock_backend) if not name.startswith("__")}
    assert held == public | {"_Operation"}
    assert type(mock_backend._Operation) is type


# Through tools.call and both fronts


def registry_over(script, offered=HW_TOOLS):
    table = BackendTable([backend(script, offered)])
    hw_profile = record()

    def tool(request):
        return select(table, hw_profile, "sim.run")(request, hw_profile)

    registry = Registry()
    registry.register("sim.run", tool, DESCRIPTION, SCHEMA)
    return registry


def through_command_line(registry, name, request):
    stdin = io.BytesIO(json.dumps(request).encode())
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        [name], registry=registry, stdin=stdin, stdout=stdout, stderr=stderr
    )
    return status, json.loads(stdout.getvalue())


def through_mcp(registry, name, request):
    document = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": request},
    }
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=registry,
        stdin=io.BytesIO(json.dumps(document).encode() + b"\n"),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    (answer,) = (json.loads(line) for line in stdout.getvalue().splitlines())
    (block,) = answer["result"]["content"]
    return answer["result"]["isError"], json.loads(block["text"])


def test_the_result_of_the_script_is_the_same_through_both_fronts():
    script = Asked({"example_member": [1, "two"]})
    registry = registry_over(script)
    request = {"example_argument": 1}
    expected = {"example_member": [1, "two"]}
    assert tools.call(registry, "sim.run", request) == expected
    assert through_command_line(registry, "sim.run", request) == (0, expected)
    assert through_mcp(registry, "sim_run", request) == (False, expected)
    assert [(tool, asked) for tool, asked, _ in script.calls] == [
        ("sim.run", request)
    ] * 3
    assert all(hw_profile == record() for _, _, hw_profile in script.calls)


@pytest.mark.parametrize(
    "request_, expected_status, expected",
    [
        (
            {"execution": 1},
            3,
            {
                "error": {
                    "kind": "example_fault",
                    "message": "the first execution fails",
                }
            },
        ),
        ({"execution": 2}, 0, {"example_member": 2}),
    ],
    ids=["a tool failure", "a result"],
)
def test_a_script_over_execution_is_the_same_through_both_fronts(
    request_, expected_status, expected
):
    registry = registry_over(fails_first)
    if expected_status:
        with pytest.raises(ToolFailure) as raised:
            tools.call(registry, "sim.run", request_)
        assert raised.value.error_object() == expected
    else:
        assert tools.call(registry, "sim.run", request_) == expected
    assert through_command_line(registry, "sim.run", request_) == (
        expected_status,
        expected,
    )
    assert through_mcp(registry, "sim_run", request_) == (
        bool(expected_status),
        expected,
    )


@pytest.mark.parametrize(
    "script, kind, cause",
    [
        (raising(RuntimeError("a fault of the tests")), "tool_crashed", RuntimeError),
        (raising(KeyError("example_member")), "tool_crashed", KeyError),
        (Asked(["no", "object"]), "bad_result", ValueError),
        (Asked(None), "bad_result", ValueError),
    ],
    ids=["RuntimeError", "KeyError", "a list returned", "None returned"],
)
def test_what_tools_call_makes_of_a_script_is_the_same_through_both_fronts(
    script, kind, cause
):
    registry = registry_over(script)
    with pytest.raises(ToolFailure) as raised:
        tools.call(registry, "sim.run", {})
    assert raised.value.kind == kind
    assert isinstance(raised.value.__cause__, cause)
    expected = raised.value.error_object()
    assert through_command_line(registry, "sim.run", {}) == (3, expected)
    assert through_mcp(registry, "sim_run", {}) == (True, expected)


def test_not_offered_through_both_fronts_asks_the_script_nothing():
    script = Asked({"example_member": 1})
    registry = registry_over(script, offered=["board.run"])
    with pytest.raises(ToolFailure) as raised:
        tools.call(registry, "sim.run", {})
    assert raised.value.kind == "not_offered"
    expected = raised.value.error_object()
    assert through_command_line(registry, "sim.run", {}) == (3, expected)
    assert through_mcp(registry, "sim_run", {}) == (True, expected)
    assert script.calls == []
