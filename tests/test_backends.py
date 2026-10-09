import copy
import io
import json
from types import MappingProxyType

import pytest

from hilclaw import __main__ as command_line
from hilclaw import backends, mcp_front, tools
from hilclaw.backends import HW_TOOLS, Backend, BackendTable, select
from hilclaw.keys import InvalidRecordError
from hilclaw.tools import Registry, ToolFailure

DESCRIPTION = "A tool of the tests."
SCHEMA = {"type": "object"}
REMOVE = object()


class Operation:
    def __init__(self, label="op"):
        self.label = label
        self.calls = 0

    def __call__(self, request):
        self.calls += 1
        return {"answered_by": self.label}


class Text(str):
    pass


def record(accelerator="acc_a", **changes):
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


def all_four(label="op"):
    return {tool: Operation(f"{label}:{tool}") for tool in HW_TOOLS}


def calls_of(*mappings):
    return sum(
        operation.calls for mapping in mappings for operation in mapping.values()
    )


def failure_of(table, hw_profile, tool):
    with pytest.raises(ToolFailure) as raised:
        select(table, hw_profile, tool)
    return raised.value


INVALID_RECORDS = [
    pytest.param(None, id="None"),
    pytest.param([("accelerator", "acc_a")], id="a list"),
    pytest.param("acc_a", id="a str"),
    pytest.param(record(accelerator=REMOVE), id="accelerator missing"),
    pytest.param(record("Acc_a"), id="accelerator in upper case"),
    pytest.param(record(""), id="accelerator empty"),
    pytest.param(record(7), id="accelerator an int"),
    pytest.param(record("a" * 33), id="accelerator of 33 characters"),
    pytest.param(record(Text("acc_a")), id="accelerator a str subclass"),
    pytest.param(record(example_unknown="x"), id="unknown field"),
    pytest.param(record(hw_source=REMOVE), id="hw_source missing"),
    pytest.param(record(schema_version=2), id="wrong schema_version"),
    pytest.param(record(toolchain={}), id="empty toolchain"),
    pytest.param(record(host={"cpu": "cpu x"}), id="host without os"),
]

BAD_NAMES = [
    pytest.param("Acc_a", ValueError, id="upper case"),
    pytest.param("", ValueError, id="empty"),
    pytest.param("a" * 33, ValueError, id="33 characters"),
    pytest.param("1acc", ValueError, id="starts with a digit"),
    pytest.param("acc-a", ValueError, id="hyphen"),
    pytest.param("acc_a\n", ValueError, id="trailing line feed"),
    pytest.param(7, TypeError, id="an int"),
    pytest.param(None, TypeError, id="None"),
    pytest.param(b"acc_a", TypeError, id="bytes"),
    pytest.param(Text("acc_a"), TypeError, id="a str subclass"),
]


# The HW tools


def test_the_hw_tools_are_the_four_of_fr_10():
    assert HW_TOOLS == ("sim.run", "board.run", "profiler.collect", "correctness.check")
    assert type(HW_TOOLS) is tuple


@pytest.mark.parametrize("tool", HW_TOOLS)
def test_check_hw_tool_returns_the_name_of_a_hw_tool_as_the_same_object(tool):
    assert backends.check_hw_tool(tool) is tool


@pytest.mark.parametrize("tool", ["blob.push", "sim_run", "SIM.RUN", "sim.run ", ""])
def test_check_hw_tool_refuses_a_name_that_is_no_hw_tool(tool):
    with pytest.raises(ValueError, match="no HW tool"):
        backends.check_hw_tool(tool)


@pytest.mark.parametrize("tool", [7, None, ("sim.run",), Text("sim.run")])
def test_check_hw_tool_refuses_what_is_no_str(tool):
    with pytest.raises(TypeError, match="must be a str"):
        backends.check_hw_tool(tool)


# A backend


@pytest.mark.parametrize("count", [0, 1, 2, 4])
def test_a_backend_offers_the_operations_it_was_built_with(count):
    operations = {tool: Operation() for tool in HW_TOOLS[:count]}
    backend = Backend("acc_a", operations)
    assert backend.name == "acc_a"
    assert backend.offered() == tuple(sorted(HW_TOOLS[:count]))
    assert calls_of(operations) == 0


def test_a_backend_name_may_be_the_longest_name():
    assert Backend("a" * 32, {}).name == "a" * 32
    assert Backend("a1_", {}).name == "a1_"


def test_a_backend_takes_any_mapping_and_any_callable():
    backend = Backend("acc_a", MappingProxyType({"sim.run": len}))
    assert backend.offered() == ("sim.run",)
    assert select(BackendTable([backend]), record(), "sim.run") is len


@pytest.mark.parametrize("name, error", BAD_NAMES)
def test_a_backend_name_that_is_no_name_is_refused(name, error):
    operations = all_four()
    with pytest.raises(error):
        Backend(name, operations)
    assert calls_of(operations) == 0


@pytest.mark.parametrize(
    "operations",
    [None, [("sim.run", len)], "sim.run", 7, {"sim.run"}],
    ids=["None", "a list of pairs", "a str", "an int", "a set"],
)
def test_operations_that_are_no_mapping_are_refused(operations):
    with pytest.raises(TypeError, match="mapping"):
        Backend("acc_a", operations)


@pytest.mark.parametrize("operation", [None, "sim.run", 7, {"result": 1}])
def test_an_operation_that_is_not_callable_is_refused(operation):
    with pytest.raises(TypeError, match="not callable"):
        Backend("acc_a", {"sim.run": operation})


@pytest.mark.parametrize(
    "tool",
    [
        "blob.push",
        "blob.fetch",
        "test.tool",
        "sim_run",
        "SIM.RUN",
        "sim.run ",
        "",
    ],
)
def test_an_operation_under_no_hw_tool_name_is_refused(tool):
    operations = {"board.run": Operation(), tool: Operation()}
    with pytest.raises(ValueError, match="no HW tool"):
        Backend("acc_a", operations)
    assert calls_of(operations) == 0


@pytest.mark.parametrize("tool", [7, None, ("sim.run",), Text("sim.run")])
def test_an_operation_under_what_is_no_str_is_refused(tool):
    operations = {"board.run": Operation(), tool: Operation()}
    with pytest.raises(TypeError, match="must be a str"):
        Backend("acc_a", operations)
    assert calls_of(operations) == 0


def test_a_backend_keeps_its_own_copy_of_the_operations():
    first, later = Operation("first"), Operation("later")
    operations = {"sim.run": first}
    backend = Backend("acc_a", operations)
    table = BackendTable([backend])
    operations["sim.run"] = later
    operations["board.run"] = later
    assert backend.offered() == ("sim.run",)
    assert select(table, record(), "sim.run") is first
    assert failure_of(table, record(), "board.run").kind == "not_offered"
    operations.clear()
    assert select(table, record(), "sim.run") is first


def test_a_backend_has_no_public_way_to_change():
    backend = Backend("acc_a", {"sim.run": Operation()})
    public = sorted(name for name in dir(backend) if not name.startswith("_"))
    assert public == ["name", "offered"]
    with pytest.raises(AttributeError):
        backend.name = "acc_b"
    with pytest.raises(AttributeError):
        backend.operations = {}
    assert backend.offered() == ("sim.run",)
    assert backend.name == "acc_a"


def test_two_backends_are_equal_only_as_the_same_object():
    operations = all_four()
    one, other = Backend("acc_a", operations), Backend("acc_a", operations)
    assert one != other
    assert len({one, other, one}) == 2


def test_the_repr_of_a_backend_shows_its_name_and_what_it_offers():
    backend = Backend("acc_a", {"sim.run": len, "board.run": len})
    assert repr(backend) == "Backend('acc_a', offered=('board.run', 'sim.run'))"
    assert repr(Backend("acc_b", {})) == "Backend('acc_b', offered=())"


# The backend table


def test_a_table_of_none_one_and_several_backends_has_sorted_names():
    assert BackendTable([]).names() == ()
    assert BackendTable(()).names() == ()
    assert BackendTable([Backend("acc_a", {})]).names() == ("acc_a",)
    several = (Backend(name, {}) for name in ("acc_c", "acc_a", "acc_b"))
    names = BackendTable(several).names()
    assert names == ("acc_a", "acc_b", "acc_c")
    assert type(names) is tuple


def test_a_name_given_twice_is_refused():
    operations = all_four()
    with pytest.raises(ValueError, match="acc_a is given twice"):
        BackendTable(
            [Backend("acc_a", operations), Backend("acc_b", {}), Backend("acc_a", {})]
        )
    backend = Backend("acc_a", operations)
    with pytest.raises(ValueError, match="twice"):
        BackendTable([backend, backend])
    assert calls_of(operations) == 0


@pytest.mark.parametrize(
    "entry",
    [None, "acc_a", ("acc_a", {}), {"acc_a": {}}, Backend, len],
    ids=["None", "a name", "a pair", "a dict", "the class", "a callable"],
)
def test_a_table_entry_that_is_no_backend_is_refused(entry):
    with pytest.raises(TypeError, match="must be a Backend"):
        BackendTable([Backend("acc_b", {}), entry])


@pytest.mark.parametrize("entries", [None, 7, Backend("acc_a", {})])
def test_a_table_of_what_is_not_iterable_is_refused(entries):
    with pytest.raises(TypeError):
        BackendTable(entries)


def test_a_mapping_of_names_is_no_list_of_backends():
    with pytest.raises(TypeError, match="must be a Backend"):
        BackendTable({"acc_a": Backend("acc_a", {})})


def test_a_table_files_a_backend_under_the_name_it_was_built_with():
    class Renamed(Backend):
        @property
        def name(self):
            return "Not A Name"

    operation = Operation()
    table = BackendTable([Renamed("acc_a", {"sim.run": operation})])
    assert table.names() == ("acc_a",)
    assert select(table, record(), "sim.run") is operation
    assert "the backend acc_a" in failure_of(table, record(), "board.run").message
    with pytest.raises(ValueError, match="acc_a is given twice"):
        BackendTable([Renamed("acc_a", {}), Backend("acc_a", {})])


def test_a_table_keeps_its_own_copy_of_the_entries():
    first = Operation("first")
    entries = [Backend("acc_a", {"sim.run": first})]
    table = BackendTable(entries)
    entries.append(Backend("acc_b", all_four()))
    entries[0] = Backend("acc_a", {})
    assert table.names() == ("acc_a",)
    assert select(table, record(), "sim.run") is first
    assert failure_of(table, record("acc_b"), "sim.run").kind == "no_backend"


def test_a_table_has_no_public_way_to_change():
    table = BackendTable([Backend("acc_a", {})])
    public = sorted(name for name in dir(table) if not name.startswith("_"))
    assert public == ["names"]
    with pytest.raises(AttributeError):
        table.backends = {}
    with pytest.raises(AttributeError):
        table.register = len
    assert table.names() == ("acc_a",)


def test_two_tables_are_equal_only_as_the_same_object():
    backend = Backend("acc_a", {})
    one, other = BackendTable([backend]), BackendTable([backend])
    assert one != other
    assert len({one, other}) == 2


def test_the_repr_of_a_table_shows_its_names():
    table = BackendTable([Backend("acc_b", {}), Backend("acc_a", {})])
    assert repr(table) == "BackendTable(('acc_a', 'acc_b'))"


def test_the_module_holds_no_table_and_no_backend():
    held = [
        name
        for name, value in vars(backends).items()
        if isinstance(value, (Backend, BackendTable))
    ]
    assert held == []


# The selection: happy


@pytest.mark.parametrize("tool", HW_TOOLS)
def test_select_returns_the_very_operation_of_each_offered_tool(tool):
    operations = all_four()
    table = BackendTable(
        [Backend("acc_b", all_four("b")), Backend("acc_a", operations)]
    )
    assert select(table, record(), tool) is operations[tool]
    assert calls_of(operations) == 0


def test_two_records_that_differ_in_accelerator_select_two_backends():
    a, b = all_four("a"), all_four("b")
    table = BackendTable([Backend("acc_a", a), Backend("acc_b", b)])
    assert select(table, record("acc_a"), "board.run") is a["board.run"]
    assert select(table, record("acc_b"), "board.run") is b["board.run"]
    assert calls_of(a, b) == 0


def test_two_tables_of_one_process_stay_apart():
    a, other_a = all_four("one"), all_four("other")
    one = BackendTable([Backend("acc_a", a)])
    other = BackendTable([Backend("acc_a", other_a), Backend("acc_b", {})])
    assert select(one, record(), "sim.run") is a["sim.run"]
    assert select(other, record(), "sim.run") is other_a["sim.run"]
    assert one.names() == ("acc_a",)
    assert other.names() == ("acc_a", "acc_b")
    assert failure_of(one, record("acc_b"), "sim.run").kind == "no_backend"


# The selection: only accelerator selects


@pytest.mark.parametrize(
    "changes",
    [
        {"revision": "rev 2"},
        {"toolchain": {"cc": "2.0"}},
        {"toolchain": {"cc": "1.0", "ld": "3"}},
        {"host": {"cpu": "another cpu", "os": "os y"}},
        {"host": {"cpu": "cpu x", "os": "os y", "ram_gb": 64}},
        {"ext": {"example_member": 1}},
        {"hw_source": "in_house"},
        {"label": "a label of the tests"},
    ],
    ids=[
        "revision",
        "toolchain value",
        "toolchain member",
        "host value",
        "host member",
        "ext",
        "hw_source",
        "label",
    ],
)
def test_no_field_but_accelerator_selects(changes):
    operations = all_four()
    table = BackendTable([Backend("acc_a", operations), Backend("acc_b", all_four())])
    assert record(**changes) != record()
    for tool in HW_TOOLS:
        assert select(table, record(**changes), tool) is operations[tool]
        assert select(table, record(), tool) is operations[tool]


def test_a_record_may_be_any_mapping():
    operations = all_four()
    table = BackendTable([Backend("acc_a", operations)])
    assert select(table, MappingProxyType(record()), "sim.run") is operations["sim.run"]


# The selection: no_backend


@pytest.mark.parametrize(
    "names, accelerator",
    [
        pytest.param((), "acc_a", id="empty table"),
        pytest.param(("acc_b", "acc_c"), "acc_a", id="no such entry"),
        pytest.param(("acc_a",), "acc_b", id="one character differs"),
        pytest.param(("acc_a",), "acc_a1", id="one character more"),
        pytest.param(("acc_a",), "acc_", id="one character less"),
    ],
)
def test_a_table_without_the_entry_is_no_backend(names, accelerator):
    held = {name: all_four(name) for name in names}
    table = BackendTable(Backend(name, held[name]) for name in names)
    for tool in HW_TOOLS:
        failure = failure_of(table, record(accelerator), tool)
        assert failure.kind == tools.KIND_NO_BACKEND == "no_backend"
        assert f"the accelerator {accelerator}" in failure.message
        assert failure.__cause__ is None
    assert calls_of(*held.values()) == 0


def test_an_unknown_accelerator_is_no_backend_before_not_offered():
    table = BackendTable([Backend("acc_a", {}), Backend("acc_b", {})])
    assert failure_of(table, record("acc_c"), "sim.run").kind == "no_backend"


# The selection: not_offered


@pytest.mark.parametrize("tool", HW_TOOLS)
def test_a_backend_without_the_operation_is_not_offered(tool):
    operations = all_four()
    del operations[tool]
    table = BackendTable([Backend("acc_a", operations), Backend("acc_b", all_four())])
    failure = failure_of(table, record(), tool)
    assert failure.kind == tools.KIND_NOT_OFFERED == "not_offered"
    assert "the backend acc_a" in failure.message
    assert tool in failure.message
    assert failure.__cause__ is None
    for other in operations:
        assert select(table, record(), other) is operations[other]
    assert calls_of(operations) == 0


@pytest.mark.parametrize("tool", HW_TOOLS)
def test_a_backend_with_no_operation_offers_no_tool(tool):
    table = BackendTable([Backend("acc_a", {})])
    failure = failure_of(table, record(), tool)
    assert failure.kind == "not_offered"
    assert "acc_a" in failure.message and tool in failure.message


# The selection: a record that is no valid record


@pytest.mark.parametrize("hw_profile", INVALID_RECORDS)
@pytest.mark.parametrize("names", [(), ("acc_a",)], ids=["empty table", "with acc_a"])
def test_an_invalid_record_passes_through_as_it_is(hw_profile, names):
    held = {name: all_four(name) for name in names}
    table = BackendTable(Backend(name, held[name]) for name in names)
    with pytest.raises(InvalidRecordError) as raised:
        select(table, hw_profile, "sim.run")
    assert type(raised.value) is InvalidRecordError
    assert not isinstance(raised.value, ToolFailure)
    assert raised.value.__cause__ is None
    assert calls_of(*held.values()) == 0


def test_an_invalid_record_is_not_no_backend_when_the_table_lacks_the_entry():
    table = BackendTable([Backend("acc_b", all_four())])
    assert failure_of(table, record("acc_a"), "sim.run").kind == "no_backend"
    with pytest.raises(InvalidRecordError, match="hw_source"):
        select(table, record("acc_a", hw_source=REMOVE), "sim.run")
    with pytest.raises(InvalidRecordError, match="unknown field"):
        select(table, record("acc_a", example_unknown=1), "sim.run")


def test_an_invalid_record_is_not_not_offered_when_the_backend_lacks_the_tool():
    table = BackendTable([Backend("acc_a", {})])
    with pytest.raises(InvalidRecordError, match="revision"):
        select(table, record(revision=""), "sim.run")


# The selection: defects of the caller


@pytest.mark.parametrize(
    "tool",
    ["blob.push", "blob.fetch", "test.tool", "sim_run", "SIM.RUN", "sim.run ", ""],
)
def test_select_refuses_a_tool_that_is_no_hw_tool(tool):
    operations = all_four()
    table = BackendTable([Backend("acc_a", operations)])
    with pytest.raises(ValueError, match="no HW tool") as raised:
        select(table, record(), tool)
    assert not isinstance(raised.value, InvalidRecordError)
    assert calls_of(operations) == 0


@pytest.mark.parametrize("tool", [7, None, ["sim.run"], Text("sim.run")])
def test_select_refuses_a_tool_name_that_is_no_str(tool):
    operations = all_four()
    table = BackendTable([Backend("acc_a", operations)])
    with pytest.raises(TypeError, match="must be a str"):
        select(table, record(), tool)
    assert calls_of(operations) == 0


@pytest.mark.parametrize(
    "table",
    [None, {}, [Backend("acc_a", {})], Backend("acc_a", {}), BackendTable],
    ids=["None", "a dict", "a list of backends", "a backend", "the class"],
)
def test_select_refuses_what_is_no_table(table):
    with pytest.raises(TypeError, match="BackendTable"):
        select(table, record(), "sim.run")


def test_a_defect_of_the_caller_comes_before_the_record():
    table = BackendTable([])
    with pytest.raises(ValueError, match="no HW tool") as raised:
        select(table, None, "blob.push")
    assert not isinstance(raised.value, InvalidRecordError)
    with pytest.raises(TypeError):
        select(None, None, "sim.run")


# The selection: nothing is kept and nothing is changed


def test_select_gives_the_same_answer_twice_and_leaves_the_record_as_it_is():
    operations = all_four()
    table = BackendTable([Backend("acc_a", operations)])
    hw_profile = record(ext={"example_member": 1}, label="a label of the tests")
    before = copy.deepcopy(hw_profile)
    first = select(table, hw_profile, "profiler.collect")
    second = select(table, hw_profile, "profiler.collect")
    assert first is second is operations["profiler.collect"]
    assert hw_profile == before
    again = (
        failure_of(table, record("acc_b"), "sim.run"),
        failure_of(table, record("acc_b"), "sim.run"),
    )
    assert again[0].error_object() == again[1].error_object()
    assert table.names() == ("acc_a",)
    assert calls_of(operations) == 0


def test_a_failed_selection_adds_no_entry():
    table = BackendTable([Backend("acc_a", {})])
    for _ in range(2):
        assert failure_of(table, record("acc_b"), "sim.run").kind == "no_backend"
        assert failure_of(table, record("acc_a"), "sim.run").kind == "not_offered"
    assert table.names() == ("acc_a",)


# Through tools.call and both fronts


def registry_over(table, hw_profile):
    def tool(request):
        return select(table, hw_profile, "sim.run")(request)

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


def test_the_result_of_the_operation_is_the_same_through_both_fronts():
    operation = Operation("acc_a")
    registry = registry_over(
        BackendTable([Backend("acc_a", {"sim.run": operation})]), record()
    )
    expected = {"answered_by": "acc_a"}
    assert tools.call(registry, "sim.run", {}) == expected
    assert through_command_line(registry, "sim.run", {}) == (0, expected)
    assert through_mcp(registry, "sim_run", {}) == (False, expected)
    assert operation.calls == 3


@pytest.mark.parametrize(
    "operations, accelerator, kind",
    [
        pytest.param(all_four(), "acc_b", "no_backend", id="no_backend"),
        pytest.param(
            {"board.run": Operation()}, "acc_a", "not_offered", id="not_offered"
        ),
    ],
)
def test_the_two_kinds_are_the_same_through_both_fronts(operations, accelerator, kind):
    registry = registry_over(
        BackendTable([Backend("acc_a", operations)]), record(accelerator)
    )
    with pytest.raises(ToolFailure) as raised:
        tools.call(registry, "sim.run", {})
    assert raised.value.kind == kind
    expected = raised.value.error_object()
    assert expected == {"error": {"kind": kind, "message": raised.value.message}}
    assert through_command_line(registry, "sim.run", {}) == (3, expected)
    assert through_mcp(registry, "sim_run", {}) == (True, expected)
    assert calls_of(operations) == 0


def test_an_invalid_record_is_one_tool_failure_through_both_fronts():
    operations = all_four()
    registry = registry_over(
        BackendTable([Backend("acc_a", operations)]), record(hw_source=REMOVE)
    )
    with pytest.raises(ToolFailure) as raised:
        tools.call(registry, "sim.run", {})
    assert raised.value.kind not in ("no_backend", "not_offered", "invalid_request")
    assert isinstance(raised.value.__cause__, InvalidRecordError)
    status, by_command_line = through_command_line(registry, "sim.run", {})
    failed, by_mcp = through_mcp(registry, "sim_run", {})
    assert (status, failed) == (3, True)
    assert by_command_line == by_mcp == raised.value.error_object()
    assert calls_of(operations) == 0
