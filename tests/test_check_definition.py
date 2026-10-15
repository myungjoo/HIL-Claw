import ast
import copy
import inspect
import re
from pathlib import Path

import pytest

from hilclaw import check_definition, check_identity, keys, layout, tools
from hilclaw.check_definition import DESCRIPTION, input_schema

TOOL = "correctness.check"
# ADR-0069 decision 4, written out.
SCHEMA = {
    "type": "object",
    "properties": {
        "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
        "round": {"type": "integer", "minimum": 0, "maximum": 9007199254740991},
        "candidate": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "attempt": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "execution": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "point": {"type": "string", "enum": ["sim", "board"]},
    },
    "required": ["run_id", "round", "candidate", "attempt", "execution", "point"],
    "additionalProperties": False,
}


def stub(request):
    raise AssertionError("the stub was called")


def test_the_schema_is_that_of_the_record():
    schema = input_schema()
    assert schema == SCHEMA
    assert type(schema["additionalProperties"]) is bool
    assert keys.MAX_INTEGER == 9007199254740991
    tools.check_json_object(schema)


def test_the_required_members_and_the_properties_are_the_members_of_a_request():
    schema = input_schema()
    assert schema["required"] == list(check_identity.MEMBERS)
    assert tuple(schema["properties"]) == check_identity.MEMBERS
    assert schema["properties"]["point"]["enum"] == [
        check_identity.SIM,
        check_identity.BOARD,
    ]


@pytest.mark.parametrize(
    "run_id",
    ["r1", "0", "a" * 64, "a" * 65, "", "R1", "-a", "_a", "a-b_c", "a.b", "a\n", "a b"],
)
def test_the_pattern_states_the_run_id_the_layout_accepts(run_id):
    pattern = input_schema()["properties"]["run_id"]["pattern"]
    # An ECMA-262 "$" ends the input only, as Python's "\Z" does.
    pattern = pattern.removesuffix("$") + r"\Z"
    try:
        layout.check_run_id(run_id)
        accepted = True
    except ValueError:
        accepted = False
    assert bool(re.search(pattern, run_id)) is accepted


def test_a_changed_schema_does_not_change_the_next():
    first = input_schema()
    kept = copy.deepcopy(first)
    first["required"].append("draws")
    first["properties"]["point"]["enum"].append("other")
    first["properties"]["candidate"]["minimum"] = 0
    first["properties"]["draws"] = {"type": "integer"}
    first["additionalProperties"] = True
    second = input_schema()
    assert second == kept == SCHEMA
    assert second is not first
    count = second["properties"]
    assert count["candidate"] is not count["attempt"] is not count["execution"]


def test_a_registry_accepts_the_description_and_the_schema():
    registry = tools.Registry()
    registry.register(TOOL, stub, DESCRIPTION, input_schema())
    held = registry.definition(TOOL)
    assert (held.description, held.input_schema) == (DESCRIPTION, SCHEMA)
    assert registry.names() == (TOOL,)


def test_the_default_registry_holds_no_definition_of_the_tool():
    assert TOOL not in tools.default_registry(lambda: None).names()


def test_the_description_tells_what_the_record_asks():
    assert type(DESCRIPTION) is str
    assert DESCRIPTION.strip()
    for member in check_identity.MEMBERS:
        assert member in DESCRIPTION
    for term in ("execution", "step_open", "fraction", "exponent"):
        assert term in DESCRIPTION
    assert re.findall(r"[\w.]*\d[\w.]*", DESCRIPTION) == ["1.0", "1e0"]


@pytest.mark.parametrize("value", [None, 1, "x", {}])
def test_input_schema_takes_no_argument(value):
    assert list(inspect.signature(input_schema).parameters) == []
    with pytest.raises(TypeError):
        input_schema(value)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert input_schema() == SCHEMA
    assert list(tmp_path.iterdir()) == []


def test_the_module_imports_what_it_names_and_has_its_public_names_only():
    own = Path(check_definition.__file__)
    text = own.read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(text)):
        assert not isinstance(node, ast.Import)
        if isinstance(node, ast.ImportFrom):
            assert node.module == "hilclaw"
            imported.update(alias.name for alias in node.names)
    assert imported == {"check_identity", "keys"}
    public = {
        name
        for name, value in vars(check_definition).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"DESCRIPTION", "input_schema"}
    for word in ("register(", "ToolDefinition(", "default_registry", "__main__"):
        assert word not in text.split('"""', 2)[2]
