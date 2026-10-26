import ast
import copy
import inspect
import io
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    __main__,
    check_definition,
    data_root_source,
    events,
    gemm_contract,
    journaled_tool,
    keys,
    layout,
    local_run,
    mcp_front,
    mock_backend,
    mock_run,
    run_definition,
    run_identity,
    run_state,
    run_tool,
    standin_image,
    standin_run,
    tools,
)
from hilclaw.harness import seed_source
from hilclaw.harness.measurement import N_MIN
from hilclaw.journal import EMPTY
from hilclaw.run_definition import (
    BOARD_DESCRIPTION,
    MEMBERS,
    SIM_DESCRIPTION,
    check,
    input_schema,
)

MARKER = "zq7-marker-zq7"
UNNAMED_LIMIT = 160
NOT_SHOWN = "(a name not shown)"
REQUEST = {"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1}
# ADR-0106 decision 4, written out.
SCHEMA = {
    "type": "object",
    "properties": {
        "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
        "round": {"type": "integer", "minimum": 0, "maximum": 9007199254740991},
        "candidate": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "attempt": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "execution": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
    },
    "required": ["run_id", "round", "candidate", "attempt", "execution"],
    "additionalProperties": False,
}
# ADR-0077 decision 4.
KEYWORDS = {
    "type",
    "properties",
    "required",
    "additionalProperties",
    "enum",
    "minimum",
    "maximum",
    "pattern",
}
UNNAMED = [
    "point",
    "seed",
    "n_max",
    "bound",
    "objective",
    "sample_form",
    "m",
    "k",
    "n",
    "shape",
    "op_signature",
    "step",
    "hw_profile",
    "data_root",
    "Execution",
    "run-id",
    "flags",
    "time_limit",
    "a" * 32,
]
POINT_VALUES = ["sim", "board", "Sim", "", None, 0, True, ["sim"], {"sim": 1}]
UNNAMED_VALUES = [None, 0, 7, 1000, 1.5, True, "sim", MARKER, [MARKER], {MARKER: 1}]
NOT_SHOWABLE = [
    "",
    "seed ",
    " seed",
    "se\ned",
    "seed\n",
    "\x00",
    "\x1b[31m",
    "a b",
    "seed'",
    "p\u00f6int",
    "\u202epoint",
    "a" * 33,
    MARKER * 5000,
]
NO_OBJECT = [None, [], [("run_id", "r1")], "r1", json.dumps(REQUEST), 0, 1.0]
TOOLS = {
    "sim.run": (run_identity.STEP_SIM_RUN, SIM_DESCRIPTION),
    "board.run": (run_identity.STEP_BOARD_RUN, BOARD_DESCRIPTION),
}
each_tool = pytest.mark.parametrize("tool", list(TOOLS))


class Called(Exception):
    pass


class Hostile:
    def __eq__(self, other):
        raise Called("__eq__")

    def __hash__(self):
        raise Called("__hash__")

    def __str__(self):
        raise Called("__str__")

    def __repr__(self):
        raise Called("__repr__")


class HostileKey(Hostile):
    def __hash__(self):
        return hash("run_id")


class Text(str):
    pass


class HostileTextKey(str):
    def __eq__(self, other):
        raise Called("__eq__")

    def __hash__(self):
        return hash("run_id")

    def __str__(self):
        raise Called("__str__")

    def __repr__(self):
        raise Called("__repr__")


def refusal(request, start=NOT_SHOWN):
    with pytest.raises(tools.ToolFailure) as caught:
        check(request)
    error = caught.value
    assert type(error) is tools.ToolFailure
    assert error.kind == tools.KIND_INVALID_REQUEST == "invalid_request"
    message = error.message
    assert type(message) is str
    assert 0 < len(message) <= UNNAMED_LIMIT
    assert message.isascii() and message.isprintable()
    assert MARKER not in message
    assert message.startswith(start + ": ")
    for member in MEMBERS:
        assert member in message
    return message


def test_the_members_are_the_five_of_the_record():
    assert type(MEMBERS) is tuple
    assert MEMBERS == ("run_id", "round", "candidate", "attempt", "execution")
    assert all(type(member) is str for member in MEMBERS)
    assert MEMBERS[1:4] == run_identity.NUMBERS
    assert "point" not in MEMBERS


def test_the_request_of_the_walk_through_is_accepted_and_not_changed():
    request = dict(REQUEST)
    assert check(request) is None
    assert request == REQUEST
    assert list(request) == list(REQUEST)


def test_no_value_is_looked_at():
    request = {"run_id": Hostile(), "execution": Text("1"), "round": None}
    assert check(request) is None
    assert check({}) is None


@pytest.mark.parametrize("name", UNNAMED)
@pytest.mark.parametrize("value", UNNAMED_VALUES, ids=repr)
def test_a_member_no_record_names_is_refused_whatever_its_value(name, value):
    request = REQUEST | {name: value}
    before = copy.deepcopy(request)
    refusal(request, name)
    assert request == before


@pytest.mark.parametrize("value", POINT_VALUES, ids=repr)
def test_point_is_refused_with_any_value(value):
    refusal(REQUEST | {"point": value}, "point")
    refusal({"point": value}, "point")


@pytest.mark.parametrize("name", NOT_SHOWABLE, ids=lambda name: ascii(name)[:40])
def test_a_name_that_is_not_shown(name):
    message = refusal(REQUEST | {name: MARKER}, NOT_SHOWN)
    if name:
        assert name not in message


def test_the_message_shows_nothing_of_the_value():
    for value in (MARKER, [MARKER] * 100, {MARKER: MARKER}, 1.5, None, b"x"):
        message = refusal(REQUEST | {"seed": value}, "seed")
        for shown in ("str", "list", "dict", "float", "None", "bytes", "1.5"):
            assert shown not in message


def test_the_first_unnamed_member_in_order_is_named():
    refusal({"seed": 1, "point": "sim", **REQUEST}, "seed")
    refusal({**REQUEST, "point": "sim", "seed": 1}, "point")
    refusal({"Execution": 1, "run-id": "r1"}, "Execution")
    refusal({"a\nb": 1, "seed": 1}, NOT_SHOWN)


@pytest.mark.parametrize("request_", NO_OBJECT, ids=repr)
def test_a_request_that_is_no_dict_is_refused(request_):
    with pytest.raises(tools.ToolFailure) as caught:
        check(request_)
    assert caught.value.kind == tools.KIND_INVALID_REQUEST
    assert len(caught.value.message) <= UNNAMED_LIMIT


def test_a_dict_subclass_is_refused():
    class Mapping(dict):
        pass

    with pytest.raises(tools.ToolFailure) as caught:
        check(Mapping(REQUEST))
    assert caught.value.kind == tools.KIND_INVALID_REQUEST


@pytest.mark.parametrize(
    "key",
    [1, None, 1.5, (), b"run_id", True],
    ids=repr,
)
def test_a_key_that_is_no_str_is_refused(key):
    refusal(REQUEST | {key: 1}, NOT_SHOWN)


def test_a_str_subclass_key_is_refused_without_calling_its_code():
    refusal({Text("run_id"): "r1"}, NOT_SHOWN)
    for key in (HostileTextKey("run_id"), HostileKey()):
        request = {}
        dict.__setitem__(request, key, Hostile())
        refusal(request, NOT_SHOWN)


def test_a_missing_or_surplus_argument_is_a_type_error():
    with pytest.raises(TypeError):
        check()
    with pytest.raises(TypeError):
        check(REQUEST, REQUEST)
    parameters = list(inspect.signature(check).parameters.values())
    assert [parameter.name for parameter in parameters] == ["request"]
    assert parameters[0].default is inspect.Parameter.empty


# The input schema (decision 4).


def test_the_schema_is_that_of_the_record():
    schema = input_schema()
    assert schema == SCHEMA
    assert keys.MAX_INTEGER == 9007199254740991
    assert schema["required"] == list(MEMBERS)
    assert tuple(schema["properties"]) == MEMBERS
    assert schema["additionalProperties"] is False
    tools.check_json_object(schema)


def used_keywords(schema):
    found = set(schema)
    for value in schema.get("properties", {}).values():
        found |= used_keywords(value)
    return found


def test_the_schema_uses_keywords_of_adr_0077_only():
    used = used_keywords(input_schema())
    assert used <= KEYWORDS
    assert used == KEYWORDS - {"enum"}


def test_a_changed_schema_does_not_change_the_next():
    first = input_schema()
    first["required"].append("point")
    first["properties"]["candidate"]["minimum"] = 0
    first["properties"]["point"] = {"type": "string"}
    first["additionalProperties"] = True
    second = input_schema()
    assert second == SCHEMA
    assert second is not first
    counts = [
        second["properties"][name] for name in ("candidate", "attempt", "execution")
    ]
    assert len({id(count) for count in counts}) == 3


def test_input_schema_takes_no_argument():
    assert list(inspect.signature(input_schema).parameters) == []
    with pytest.raises(TypeError):
        input_schema(None)


@pytest.mark.parametrize(
    "run_id",
    ["r1", "0", "a" * 64, "a" * 65, "", "R1", "-a", "_a", "a-b_c", "a.b", "a\n"],
)
def test_the_pattern_states_the_run_id_the_layout_accepts(run_id):
    try:
        layout.check_run_id(run_id)
        accepted = True
    except ValueError:
        accepted = False
    assert admits({**REQUEST, "run_id": run_id}) is accepted


@each_tool
def test_a_registry_accepts_the_description_and_the_schema(tool):
    _, description = TOOLS[tool]
    registry = tools.Registry()
    registry.register(tool, lambda request: {}, description, input_schema())
    held = registry.definition(tool)
    assert (held.description, held.input_schema) == (description, SCHEMA)
    assert registry.names() == (tool,)


# The descriptions (decision 5).


@each_tool
def test_a_description_tells_what_the_record_asks(tool):
    _, description = TOOLS[tool]
    assert type(description) is str and description.strip()
    point = tool.split(".")[0]
    assert f"at the {point} point" in description
    for term in (
        "no member states the point",
        "journaled",
        "stored outcome",
        "step_open",
        "higher execution",
        "instance.json",
        "dimensions",
        "n_max",
        "objective",
        "bound",
        "seed",
        "settings",
        "point",
        "invalid_request",
        "fraction",
        "exponent",
        "1.0",
        "1e0",
        *MEMBERS,
    ):
        assert term in description, term


def test_the_descriptions_differ_in_the_point_only():
    assert SIM_DESCRIPTION != BOARD_DESCRIPTION
    assert "board point" not in SIM_DESCRIPTION
    assert "sim point" not in BOARD_DESCRIPTION
    assert SIM_DESCRIPTION.replace("sim point", "board point") == BOARD_DESCRIPTION


@each_tool
def test_a_description_states_no_value(tool):
    _, description = TOOLS[tool]
    numbers = set(re.findall(r"\d+(?:\.\d+)?(?:e\d+)?", description))
    assert numbers == {"1.0", "1e0"}
    for kept_out in ("who may", "counts", "sim.run", "board.run"):
        assert kept_out not in description


# A small evaluator of the seven keywords the schema uses.


def of_type(value, name):
    if name == "object":
        return type(value) is dict
    if name == "string":
        return type(value) is str
    if name == "integer":
        number = type(value) in (int, float) and math.isfinite(value)
        return number and float(value).is_integer()
    raise AssertionError(f"type {name} is not read here")


def admits_value(schema, value):
    for keyword in schema:
        assert keyword in KEYWORDS - {"enum"}, keyword
    if not of_type(value, schema["type"]):
        return False
    if "pattern" in schema:
        pattern = schema["pattern"].removesuffix("$") + r"\Z"
        if not re.search(pattern, value):
            return False
    if "minimum" in schema and value < schema["minimum"]:
        return False
    if "maximum" in schema and value > schema["maximum"]:
        return False
    if "properties" in schema:
        if any(name not in value for name in schema["required"]):
            return False
        for name, member in value.items():
            if name in schema["properties"]:
                if not admits_value(schema["properties"][name], member):
                    return False
            elif schema["additionalProperties"] is False:
                return False
    return True


def admits(request):
    return admits_value(input_schema(), request)


# The Walk-through of ADR-0106, at both tools.

EXECUTION_RENAMED = {
    **{name: value for name, value in REQUEST.items() if name != "execution"},
    "Execution": 1,
}
REFUSED_ROWS = {
    "point-sim": REQUEST | {"point": "sim"},
    "point-board": REQUEST | {"point": "board"},
    "seed": REQUEST | {"seed": 7},
    "n_max": REQUEST | {"n_max": 1000},
    "bound": REQUEST | {"bound": 1024},
    "objective": REQUEST | {"objective": {}},
    "m": REQUEST | {"m": 1},
    "Execution": EXECUTION_RENAMED,
}
ROWS = {
    "request": (REQUEST, True, True),
    **{name: (asked, False, False) for name, asked in REFUSED_ROWS.items()},
    "execution-1.0": (REQUEST | {"execution": 1.0}, True, False),
}


class CountingSource:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise Called("the source was asked")


def counted(tool):
    step, _ = TOOLS[tool]
    source = CountingSource()
    performed = []

    def perform(data_root, request):
        performed.append(request)
        raise AssertionError("perform was called")

    function = journaled_tool.tool_function(
        step=step,
        numbers=run_identity.NUMBERS,
        source=source,
        check=run_definition.check,
        perform=perform,
    )
    return function, source, performed


@each_tool
@pytest.mark.parametrize("row", list(ROWS))
def test_each_row_of_the_walk_through(tool, row):
    asked, schema_admits, passes = ROWS[row]
    assert admits(asked) is schema_admits
    function, source, performed = counted(tool)
    before = copy.deepcopy(asked)
    with pytest.raises(tools.ToolFailure) as caught:
        function(asked)
    if passes:
        assert caught.value.kind == tools.KIND_NO_DATA_ROOT
        assert source.calls == 1
    else:
        assert caught.value.kind == tools.KIND_INVALID_REQUEST
        assert source.calls == 0
    assert performed == []
    assert asked == before


@each_tool
@pytest.mark.parametrize("row", list(REFUSED_ROWS))
def test_a_refused_row_names_the_member(tool, row):
    function, _, _ = counted(tool)
    with pytest.raises(tools.ToolFailure) as caught:
        function(REFUSED_ROWS[row])
    message = caught.value.message
    if row == "Execution":
        assert message.startswith("execution: ")
    else:
        assert message.startswith(next(iter(REFUSED_ROWS[row].keys() - MEMBERS)))


# The rows "again after the first call ended", over a real data root.

PROFILE = {
    "schema_version": 1,
    "accelerator": "acc_a",
    "revision": "rev 1",
    "toolchain": {"cc": "1.0"},
    "host": {"cpu": "cpu x", "os": "os y"},
    "hw_source": "external",
}


def new_root(tmp_path):
    run = tmp_path / "data" / "runs" / REQUEST["run_id"]
    run.mkdir(parents=True)
    section = {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE}
    document = {"schema_version": 1, "hw_profile": section}
    (run / "instance.json").write_text(json.dumps(document), encoding="utf-8")
    (run / "STATE.json").write_bytes(run_state.dump(REQUEST["round"], EMPTY))
    return tmp_path / "data"


def lines(root):
    return events.read(root, REQUEST["run_id"]).events


@each_tool
def test_again_after_the_first_call_ended(tmp_path, tool):
    step, _ = TOOLS[tool]
    root = new_root(tmp_path)
    asked = []
    performed = []

    def source():
        asked.append(1)
        return root

    def perform(data_root, request):
        performed.append(request)
        return {"example_axis": 1}, {"example_member": len(performed)}

    function = journaled_tool.tool_function(
        step=step,
        numbers=run_identity.NUMBERS,
        source=source,
        check=run_definition.check,
        perform=perform,
    )
    assert function(dict(REQUEST)) == {"example_member": 1}
    kept = lines(root)
    assert len(kept) == 2
    assert {line["data"]["step"] for line in kept} == {step}
    assert function(dict(REQUEST)) == {"example_member": 1}
    assert len(performed) == 1
    assert asked == [1, 1]
    seeded = REQUEST | {"seed": 7}
    assert admits(seeded) is False
    with pytest.raises(tools.ToolFailure) as caught:
        function(seeded)
    assert caught.value.kind == tools.KIND_INVALID_REQUEST
    assert caught.value.message.startswith("seed: ")
    assert asked == [1, 1]
    assert len(performed) == 1
    assert lines(root) == kept


# The module.


def imports_of(path):
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def test_the_module_imports_what_it_names_and_has_its_public_names_only():
    own = Path(run_definition.__file__)
    assert imports_of(own) == {
        "re",
        "hilclaw.gemm_contract",
        "hilclaw.keys",
        "hilclaw.run_identity",
        "hilclaw.tools",
        "hilclaw.harness.seed_source",
        "hilclaw.check_definition",
        "hilclaw.run_tool",
    }
    public = {
        name
        for name, value in vars(run_definition).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "MEMBERS",
        "check",
        "definitions",
        "input_schema",
        "SIM_DESCRIPTION",
        "BOARD_DESCRIPTION",
    }
    code = own.read_text(encoding="utf-8").split('"""', 2)[2]
    for word in ("register(", "default_registry", "open(", "__main__", "environ"):
        assert word not in code


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert input_schema() == SCHEMA
    assert check(dict(REQUEST)) is None
    refusal(REQUEST | {"seed": 7}, "seed")
    assert list(tmp_path.iterdir()) == []


# The two definitions and the default registry (ADR-0167); test values only.

RUN = "run-a"
ROUND = 3
SHAPE = {"m": 2, "k": 3, "n": 4}
N_MAX = 10
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": SHAPE,
    "dtype": "fp32",
    "layout": "row_major",
}
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
DRAWS = 2
TOLERANCE = {"rtol": 0.25, "atol": 3.0}
CALL = {"run_id": RUN, "round": ROUND, "candidate": 2, "attempt": 1, "execution": 1}
NUMBERS = {"round": ROUND, "candidate": 2, "attempt": 1}
CONVERGED = {
    "outcome": "converged",
    "shape": SHAPE,
    "n_max": N_MAX,
    "sample_form": "interval",
    "resolution_ns": 1,
    "intervals_ns": [1000000] * N_MIN,
    "ceiling": "not_stated",
}
REPO_ROOT = Path(__file__).resolve().parent.parent


def hw_profile(accelerator):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"cc": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }


def a_run(root, run_id=RUN, accelerator=mock_backend.NAME):
    record = hw_profile(accelerator)
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "n_max": N_MAX,
        "objective": OBJECTIVE,
        "draws": DRAWS,
        "tolerance": TOLERANCE,
    }
    run = root / "runs" / run_id
    run.mkdir(parents=True)
    (run / "instance.json").write_text(json.dumps(document), encoding="utf-8")
    (run / "STATE.json").write_bytes(run_state.dump(ROUND, EMPTY))
    return root


def step_lines(root, run_id=RUN):
    found = events.read(root, run_id).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def no_log(root, run_id=RUN):
    return not (root / "runs" / run_id / "events.ndjson").exists()


class Recorder:
    def __init__(self, real):
        self.real, self.calls, self.answers = real, [], []

    def __call__(self, *args):
        self.calls.append(args)
        self.answers.append(self.real(*args))
        return self.answers[-1]


class AnsweringSource:
    def __init__(self, root=None):
        self.root, self.calls = root, 0

    def __call__(self):
        self.calls += 1
        return self.root


@pytest.fixture
def data(tmp_path):
    return a_run(tmp_path / "data")


@pytest.fixture
def parties(monkeypatch):
    """Record the source of seeds, the predicate, the run script and the table the source binds."""
    recorded = {
        "seeds": Recorder(seed_source.system),
        "covers": Recorder(gemm_contract.covers),
        "script": Recorder(mock_run.default_script),
        "table": Recorder(check_definition.default_table),
    }
    monkeypatch.setattr(seed_source, "system", recorded["seeds"])
    monkeypatch.setattr(gemm_contract, "covers", recorded["covers"])
    monkeypatch.setattr(mock_run, "default_script", recorded["script"])
    monkeypatch.setattr(check_definition, "default_table", recorded["table"])
    return recorded


def counts(parties):
    return tuple(len(parties[name].calls) for name in ("seeds", "covers", "script"))


def refused_call(registry, tool, request, kind):
    with pytest.raises(tools.ToolFailure) as caught:
        tools.call(registry, tool, request)
    assert caught.value.kind == kind
    return caught.value


def timed(tool, result=CONVERGED):
    step = {"step": TOOLS[tool][0], "execution": 1}
    return [
        {"schema_version": 1, "kind": "step_started", **NUMBERS, "data": step},
        {
            "schema_version": 1,
            "kind": "step_ended",
            **NUMBERS,
            "data": {**step, "spend": {}, "result": result},
        },
    ]


def test_definitions_are_the_two_tools_of_the_record(parties):
    source = AnsweringSource()
    held = run_definition.definitions(source)
    assert type(held) is tuple
    assert [(one.name, one.description) for one in held] == [
        ("sim.run", SIM_DESCRIPTION),
        ("board.run", BOARD_DESCRIPTION),
    ]
    for one in held:
        assert type(one) is tools.ToolDefinition
        assert one.input_schema == SCHEMA
        assert callable(one.function)
    assert held[0].input_schema is not held[1].input_schema
    assert (source.calls, *counts(parties)) == (0, 0, 0, 0)
    assert parties["table"].calls == []


@pytest.mark.parametrize("source", [None, "data", 3, {}, Path(".")])
def test_definitions_refuse_a_source_that_is_not_callable(source):
    with pytest.raises(TypeError, match="callable"):
        run_definition.definitions(source)


def test_the_default_registry_holds_both_run_tools(parties):
    source = AnsweringSource()
    registry = tools.default_registry(source)
    for tool, (_, description) in TOOLS.items():
        held = registry.definition(tool)
        assert (held.name, held.description, held.input_schema) == (
            tool,
            description,
            SCHEMA,
        )
    assert "profiler.collect" not in registry.names()
    assert (source.calls, *counts(parties)) == (0, 0, 0, 0)
    assert parties["table"].calls == []


@pytest.mark.parametrize("source", [None, "data", 3])
def test_the_default_registry_refuses_a_source_that_is_not_callable(source, parties):
    with pytest.raises(TypeError, match="must be callable"):
        tools.default_registry(source)
    assert (*counts(parties), len(parties["table"].calls)) == (0, 0, 0, 0)


@each_tool
def test_a_call_about_a_run_at_the_mock_is_completed(tool, data, parties):
    registry = tools.default_registry(lambda: data)
    assert tools.call(registry, tool, dict(CALL)) == CONVERGED
    assert step_lines(data) == timed(tool)
    assert counts(parties) == (1, 1, 1)
    ((called, asked, _, parameters, _, _),) = parties["script"].calls
    assert (called, asked) == (tool, CALL)
    assert parameters.seed == parties["seeds"].answers[0]


@each_tool
def test_the_same_request_again_returns_the_stored_result(tool, data, parties):
    first = tools.call(tools.default_registry(lambda: data), tool, dict(CALL))
    again = tools.call(tools.default_registry(lambda: data), tool, dict(CALL))
    assert again == first == CONVERGED
    assert counts(parties) == (1, 1, 1)
    assert len(step_lines(data)) == 2


@each_tool
def test_a_run_at_another_accelerator_is_no_backend(tool, tmp_path, parties):
    root = a_run(tmp_path / "data", accelerator="acc_b")
    registry = tools.default_registry(lambda: root)
    refused_call(registry, tool, dict(CALL), tools.KIND_NO_BACKEND)
    refused_call(registry, tool, dict(CALL), tools.KIND_NO_BACKEND)
    assert no_log(root)
    assert counts(parties) == (0, 0, 0)


@each_tool
def test_a_run_at_cpu_standin_reaches_its_operation(
    tool, tmp_path, parties, monkeypatch
):
    started = []
    reached = Recorder(standin_run.operation)
    monkeypatch.delenv(standin_image.ENV_IMAGE, raising=False)
    monkeypatch.setattr(local_run, "run", lambda command, **_: started.append(command))
    monkeypatch.setattr(standin_run, "operation", reached)
    root = a_run(tmp_path / "data", accelerator="cpu_standin")
    registry = tools.default_registry(lambda: root)
    failure = refused_call(registry, tool, dict(CALL), "compiler_unavailable")
    again = refused_call(registry, tool, dict(CALL), "compiler_unavailable")
    assert again.message == failure.message
    assert (len(reached.calls), started) == (1, [])
    assert counts(parties) == (1, 1, 0)
    ended = {"kind": "compiler_unavailable", "message": failure.message}
    assert [line["data"].get("failure") for line in step_lines(root)] == [None, ended]


@each_tool
@pytest.mark.parametrize(
    "asked",
    [
        CALL | {"point": "sim"},
        CALL | {"seed": 7},
        CALL | {"n_max": 1000},
        {name: CALL[name] for name in CALL if name != "execution"},
    ],
)
def test_a_request_the_record_refuses_is_invalid_request(tool, data, parties, asked):
    registry = tools.default_registry(lambda: data)
    refused_call(registry, tool, asked, tools.KIND_INVALID_REQUEST)
    assert no_log(data)
    assert counts(parties) == (0, 0, 0)


def test_correctness_check_still_answers_through_the_same_registry(data, parties):
    registry = tools.default_registry(lambda: data)
    asked = CALL | {"point": "sim"}
    checked = tools.call(registry, "correctness.check", asked)
    assert checked["outcome"] == "pass"
    assert tools.call(registry, "sim.run", dict(CALL)) == CONVERGED
    assert tools.call(registry, "correctness.check", asked) == checked
    assert counts(parties) == (2, 2, 1)
    assert len(parties["table"].calls) == 2


def test_no_environment_variable_chooses_the_table_or_the_seeds(
    tmp_path, parties, monkeypatch
):
    monkeypatch.setenv("HILCLAW_BACKEND", "cpu_standin")
    monkeypatch.setenv("HILCLAW_SEED", "7")
    root = a_run(a_run(tmp_path / "data"), "run-b", accelerator="acc_b")
    registry = tools.default_registry(lambda: root)
    assert tools.call(registry, "board.run", dict(CALL)) == CONVERGED
    refused_call(
        registry, "board.run", CALL | {"run_id": "run-b"}, tools.KIND_NO_BACKEND
    )
    assert parties["script"].calls[0][3].seed == parties["seeds"].answers[0]


def test_the_first_call_binds_the_tool_function_of_the_record(
    data, parties, monkeypatch
):
    bound = []
    real = run_tool.tool_function

    def binding(tool, **parts):
        bound.append((tool, parts))
        return real(tool, **parts)

    monkeypatch.setattr(run_tool, "tool_function", binding)
    source = AnsweringSource(data)
    registry = tools.default_registry(source)
    assert bound == []
    assert tools.call(registry, "sim.run", dict(CALL)) == CONVERGED
    assert tools.call(registry, "sim.run", CALL | {"execution": 2}) == CONVERGED
    assert bound == [
        (
            "sim.run",
            {
                "source": source,
                "table": parties["table"].answers[0],
                "seeds": parties["seeds"],
                "covers": parties["covers"],
            },
        )
    ]
    assert len(parties["table"].calls) == 1


def test_a_first_call_whose_binding_fails_keeps_nothing(data, parties, monkeypatch):
    broken = RuntimeError("no table")
    failures = [broken]

    def fails_once():
        if failures:
            raise failures.pop()
        return parties["table"]()

    monkeypatch.setattr(check_definition, "default_table", fails_once)
    registry = tools.default_registry(lambda: data)
    failure = refused_call(registry, "board.run", dict(CALL), tools.KIND_TOOL_CRASHED)
    assert failure.__cause__ is broken
    assert no_log(data)
    assert tools.call(registry, "board.run", dict(CALL)) == CONVERGED
    assert tools.call(registry, "board.run", dict(CALL)) == CONVERGED
    assert len(parties["table"].calls) == 1
    assert counts(parties) == (1, 1, 1)


@pytest.fixture
def configured(tmp_path, monkeypatch):
    """A data root with a run at the mock and one at acc_b, as the fronts' source."""
    root = a_run(a_run(tmp_path / "data"), "run-b", accelerator="acc_b")
    monkeypatch.setattr(data_root_source, "configured", lambda: root)
    return root


def mcp_exchange(document):
    stdin = io.BytesIO(json.dumps(document).encode() + b"\n")
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main([], stdin=stdin, stdout=stdout, stderr=stderr)
    assert (status, stderr.getvalue()) == (0, b"")
    return json.loads(stdout.getvalue())


def mcp_tool_call(name, arguments):
    params = {"name": name, "arguments": arguments}
    answer = mcp_exchange(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    )
    result = answer["result"]
    return result["isError"], json.loads(result["content"][0]["text"])


def test_tools_list_of_the_mcp_front_lists_both_run_tools(configured):
    answer = mcp_exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    listed = {tool["name"]: tool for tool in answer["result"]["tools"]}
    for name, description in (
        ("sim_run", SIM_DESCRIPTION),
        ("board_run", BOARD_DESCRIPTION),
    ):
        assert listed[name]["description"] == description
        assert listed[name]["inputSchema"] == SCHEMA
    assert "profiler_collect" not in listed


@pytest.mark.parametrize(
    ("tool", "name"), [("sim.run", "sim_run"), ("board.run", "board_run")]
)
def test_the_mcp_front_serves_both_run_tools(configured, parties, tool, name):
    assert mcp_tool_call(name, CALL) == (False, CONVERGED)
    assert mcp_tool_call(name, CALL) == (False, CONVERGED)
    assert step_lines(configured) == timed(tool)
    failed, answer = mcp_tool_call(name, CALL | {"run_id": "run-b"})
    assert failed is True
    assert answer["error"]["kind"] == tools.KIND_NO_BACKEND
    assert no_log(configured, "run-b")
    failed, answer = mcp_tool_call(name, CALL | {"point": "board"})
    assert failed is True
    assert answer["error"]["kind"] == tools.KIND_INVALID_REQUEST
    assert counts(parties) == (1, 1, 1)


def test_the_command_line_front_serves_a_run_tool(configured, parties):
    stdout = io.BytesIO()
    status = __main__.main(
        ["board.run"],
        stdin=io.BytesIO(json.dumps(CALL).encode()),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert (status, json.loads(stdout.getvalue())) == (__main__.EXIT_RESULT, CONVERGED)
    assert counts(parties) == (1, 1, 1)


HEAVY = (
    "numpy",
    "hilclaw.run_tool",
    "hilclaw.mock_check",
    "hilclaw.mock_run",
    "hilclaw.standin_check",
    "hilclaw.standin_run",
)
BUILD_CHILD = """
import sys
from hilclaw import run_definition, tools
calls = []
def source():
    calls.append(1)
run_definition.definitions(source)
tools.default_registry(source)
print(len(calls), ",".join(name for name in {heavy!r} if name in sys.modules))
"""


def test_building_the_definitions_and_the_registry_imports_no_numpy():
    done = subprocess.run(
        [sys.executable, "-c", BUILD_CHILD.format(heavy=HEAVY)],
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, b"")
    assert done.stdout.decode().split() == ["0"]
