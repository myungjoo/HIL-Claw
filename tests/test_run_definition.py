import ast
import copy
import inspect
import json
import math
import re
from pathlib import Path

import pytest

from hilclaw import (
    events,
    journaled_tool,
    keys,
    layout,
    run_definition,
    run_identity,
    run_state,
    tools,
)
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
        "hilclaw.keys",
        "hilclaw.run_identity",
        "hilclaw.tools",
    }
    public = {
        name
        for name, value in vars(run_definition).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "MEMBERS",
        "check",
        "input_schema",
        "SIM_DESCRIPTION",
        "BOARD_DESCRIPTION",
    }
    code = own.read_text(encoding="utf-8").split('"""', 2)[2]
    for word in ("register(", "default_registry", "open(", "__main__", "environ"):
        assert word not in code


def test_the_default_registry_holds_neither_run_tool():
    names = tools.default_registry(lambda: None).names()
    assert "sim.run" not in names
    assert "board.run" not in names


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert input_schema() == SCHEMA
    assert check(dict(REQUEST)) is None
    refusal(REQUEST | {"seed": 7}, "seed")
    assert list(tmp_path.iterdir()) == []
