import json

import pytest

from hilclaw import journaled_step, tools
from hilclaw.tools import (
    InvalidRequestError,
    Registry,
    ToolDefinition,
    ToolFailure,
    UnknownToolError,
    call,
    check_json_object,
    decode_request,
    default_registry,
    encode,
)

EVERY_JSON_TYPE = {
    "object": {"nested": {"deeper": {}}},
    "array": [1, [2, [3]], {"a": None}],
    "null": None,
    "true": True,
    "false": False,
    "integer": -(2**70),
    "float": 0.5,
    "text": "héllo 한글 \U0001f600",
    "": "an empty member name",
}


class Custom(Exception):
    pass


class Text(str):
    pass


class Number(int):
    pass


class Mapping(dict):
    pass


ECHO = object()
DESCRIPTION = "A tool of the tests."
SCHEMA = {"type": "object"}
RICH_SCHEMA = {
    "type": "object",
    "properties": {
        "example_text": {"type": "string", "description": "héllo 한글"},
        "example_list": {"type": "array", "items": {"type": ["integer", "null"]}},
        "example_object": {
            "type": "object",
            "properties": {"example_number": {"type": "number", "minimum": 0.5}},
            "required": ["example_number"],
        },
    },
    "required": ["example_text"],
    "additionalProperties": False,
}


class Recorder:
    def __init__(self, outcome=ECHO):
        self.requests = []
        self.outcome = outcome

    def __call__(self, request):
        self.requests.append(request)
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return request if self.outcome is ECHO else self.outcome


def registry_of(**functions):
    registry = Registry()
    for name, function in functions.items():
        registry.register(name.replace("_", "."), function, DESCRIPTION, SCHEMA)
    return registry


def cyclic():
    value = {}
    value["self"] = value
    return value


def nested(depth):
    value = {}
    for _ in range(depth):
        value = {"a": [value]}
    return value


NOT_OBJECTS = [
    pytest.param([], id="list"),
    pytest.param("text", id="str"),
    pytest.param(None, id="none"),
    pytest.param(3, id="int"),
    pytest.param(("a",), id="tuple"),
    pytest.param(Mapping(), id="dict subclass"),
    pytest.param({"a": float("nan")}, id="nan"),
    pytest.param({"a": [float("inf")]}, id="inf"),
    pytest.param({"a": {"b": float("-inf")}}, id="minus inf"),
    pytest.param({1: "a"}, id="int member name"),
    pytest.param({"a": {None: 1}}, id="none member name at depth"),
    pytest.param({Text("a"): 1}, id="str subclass member name"),
    pytest.param({"a": b"bytes"}, id="bytes"),
    pytest.param({"a": [{"b": {1, 2}}]}, id="set at depth"),
    pytest.param({"a": (1, 2)}, id="tuple at depth"),
    pytest.param({"a": Text("x")}, id="str subclass"),
    pytest.param({"a": Number(1)}, id="int subclass"),
    pytest.param({"a": [Mapping()]}, id="dict subclass at depth"),
    pytest.param({"a": object()}, id="object"),
    pytest.param(cyclic(), id="cyclic"),
    pytest.param(nested(100_000), id="too deep"),
]


# ToolFailure


def test_tool_failure_carries_kind_and_message():
    failure = ToolFailure("backend_down", "no answer from the board")
    assert failure.kind == "backend_down"
    assert failure.message == "no answer from the board"
    assert isinstance(failure, Exception)


def test_error_object_has_exactly_the_two_members():
    failure = ToolFailure("refused", "")
    assert failure.error_object() == {"error": {"kind": "refused", "message": ""}}
    assert list(failure.error_object()) == ["error"]
    assert list(failure.error_object()["error"]) == ["kind", "message"]
    check_json_object(failure.error_object())


@pytest.mark.parametrize("kind", ["a", "a1_b", "a" * 32])
def test_tool_failure_accepts_a_name(kind):
    assert ToolFailure(kind, "m").kind == kind


@pytest.mark.parametrize("kind", ["", "Bad", "a.b", "1a", "_a", "a b", "a\n", "a" * 33])
def test_tool_failure_refuses_a_kind_that_is_not_a_name(kind):
    with pytest.raises(ValueError, match="not a name"):
        ToolFailure(kind, "m")


@pytest.mark.parametrize(
    ("kind", "message"),
    [(None, "m"), (1, "m"), (b"a", "m"), (Text("a"), "m")]
    + [("a", None), ("a", 1), ("a", b"m"), ("a", Text("m")), ("a", ValueError("m"))],
)
def test_tool_failure_refuses_other_types(kind, message):
    with pytest.raises(TypeError, match="must be str"):
        ToolFailure(kind, message)


# Registry


def test_register_get_and_names():
    def first(request):
        return request

    def second(request):
        return request

    registry = Registry()
    assert registry.names() == ()
    registry.register("sim.run", first, DESCRIPTION, SCHEMA)
    registry.register("blob.push", second, "Another tool.", RICH_SCHEMA)
    assert registry.get("sim.run") is first
    assert registry.get("blob.push") is second
    assert registry.names() == ("blob.push", "sim.run")


@pytest.mark.parametrize("name", ["a", "sim.run", "a1.b2.c3", "profiler.collect"])
def test_register_accepts_dotted_lowercase_words(name):
    registry = Registry()
    registry.register(name, dict, DESCRIPTION, SCHEMA)
    assert registry.names() == (name,)


@pytest.mark.parametrize(
    "name",
    ["", "Sim.run", "sim.Run", "sim_run", "sim run", ".sim", "sim.", "sim..run"]
    + ["1sim", "sim.1", "sim-run", "sim.run\n", "--help", "sím.run"],
)
def test_register_refuses_a_name_that_breaks_the_rule(name):
    registry = Registry()
    with pytest.raises(ValueError, match="not a tool name"):
        registry.register(name, dict, DESCRIPTION, SCHEMA)
    assert registry.names() == ()


@pytest.mark.parametrize("name", [None, 1, b"sim.run", ("sim", "run"), Text("sim.run")])
def test_register_refuses_a_name_that_is_not_a_str(name):
    registry = Registry()
    with pytest.raises(TypeError, match="must be a str"):
        registry.register(name, dict, DESCRIPTION, SCHEMA)
    assert registry.names() == ()


@pytest.mark.parametrize("function", [None, "sim.run", 1, {}])
def test_register_refuses_a_function_that_is_not_callable(function):
    registry = Registry()
    with pytest.raises(TypeError, match="not callable"):
        registry.register("sim.run", function, DESCRIPTION, SCHEMA)
    assert registry.names() == ()


def test_register_refuses_a_second_function_for_one_name():
    first = Recorder()
    registry = registry_of(sim_run=first)
    with pytest.raises(ValueError, match="registered already"):
        registry.register("sim.run", Recorder(), "Another tool.", RICH_SCHEMA)
    with pytest.raises(ValueError, match="registered already"):
        registry.register("sim.run", Recorder(), "", None)
    assert registry.get("sim.run") is first
    assert registry.definition("sim.run") == ("sim.run", first, DESCRIPTION, SCHEMA)
    assert registry.names() == ("sim.run",)


@pytest.mark.parametrize("name", ["board.run", "sim", "sim.run.x", "", None, 1, []])
def test_get_raises_its_own_lookup_error(name):
    registry = registry_of(sim_run=Recorder())
    with pytest.raises(UnknownToolError, match="unknown tool") as caught:
        registry.get(name)
    assert isinstance(caught.value, LookupError)
    assert not isinstance(caught.value, ToolFailure)


# The tool definition


def assert_refused(error, said, *definition):
    registry = registry_of(board_run=Recorder())
    with pytest.raises(error, match=said):
        registry.register("sim.run", *definition)
    assert registry.names() == ("board.run",)
    with pytest.raises(UnknownToolError):
        registry.definition("sim.run")
    registry.register("sim.run", Recorder(), DESCRIPTION, SCHEMA)
    assert registry.names() == ("board.run", "sim.run")


def test_a_definition_is_read_back_with_its_four_parts():
    tool = Recorder()
    registry = Registry()
    registry.register("sim.run", tool, "Runs a thing. 한글 \U0001f600", RICH_SCHEMA)
    held = registry.definition("sim.run")
    assert isinstance(held, ToolDefinition)
    assert held._fields == ("name", "function", "description", "input_schema")
    assert held.name == "sim.run"
    assert held.function is tool is registry.get("sim.run")
    assert held.description == "Runs a thing. 한글 \U0001f600"
    assert held.input_schema == RICH_SCHEMA
    assert registry.names() == ("sim.run",)
    with pytest.raises(AttributeError):
        held.description = "another"


def test_two_tools_keep_two_definitions_apart():
    first, second = Recorder(), Recorder()
    registry = Registry()
    registry.register("sim.run", first, "The first.", SCHEMA)
    registry.register("board.run", second, "The second.", RICH_SCHEMA)
    assert registry.definition("sim.run") == ("sim.run", first, "The first.", SCHEMA)
    assert registry.definition("board.run") == (
        "board.run",
        second,
        "The second.",
        RICH_SCHEMA,
    )


@pytest.mark.parametrize(
    "schema",
    [
        pytest.param({"type": "object"}, id="type only"),
        pytest.param(RICH_SCHEMA, id="further keywords"),
        pytest.param({"type": "object", "example_keyword": [1, None]}, id="unknown"),
        pytest.param({"type": "object", "properties": nested(20)}, id="nested"),
    ],
)
def test_register_checks_nothing_of_a_schema_but_its_type(schema):
    registry = Registry()
    registry.register("sim.run", Recorder(), DESCRIPTION, schema)
    assert registry.definition("sim.run").input_schema == schema


def test_register_takes_a_description_of_any_length_with_whitespace_around_it():
    text = "  " + "long " * 20_000 + "\n"
    registry = Registry()
    registry.register("sim.run", Recorder(), text, SCHEMA)
    assert registry.definition("sim.run").description == text


def test_the_registry_keeps_its_own_copy_of_a_schema():
    schema = {"type": "object", "properties": {"example_member": {"type": "string"}}}
    registry = Registry()
    registry.register("sim.run", Recorder(), DESCRIPTION, schema)
    schema["properties"]["example_member"]["type"] = "integer"
    schema["type"] = "array"
    assert registry.definition("sim.run").input_schema == {
        "type": "object",
        "properties": {"example_member": {"type": "string"}},
    }


def test_a_reader_gets_a_copy_of_a_schema_at_each_reading():
    registry = Registry()
    registry.register("sim.run", Recorder(), DESCRIPTION, RICH_SCHEMA)
    first = registry.definition("sim.run")
    assert first.input_schema is not RICH_SCHEMA
    first.input_schema["properties"]["example_text"]["type"] = "integer"
    first.input_schema.clear()
    second = registry.definition("sim.run")
    assert second.input_schema == RICH_SCHEMA
    assert second.input_schema is not first.input_schema
    assert second == registry.definition("sim.run")


@pytest.mark.parametrize("name", ["board.run", "sim", "sim.run.x", "", None, 1, []])
def test_definition_raises_the_lookup_error_of_get(name):
    registry = registry_of(sim_run=Recorder())
    with pytest.raises(UnknownToolError, match="unknown tool") as caught:
        registry.definition(name)
    assert not isinstance(caught.value, ToolFailure)


@pytest.mark.parametrize("description", [None, b"text", 3, ["text"], Text("text")])
def test_register_refuses_a_description_that_is_not_a_str(description):
    said = "description of sim.run must be a str"
    assert_refused(TypeError, said, Recorder(), description, SCHEMA)


@pytest.mark.parametrize("description", ["", " ", "\n\t ", "　 "])
def test_register_refuses_an_empty_or_blank_description(description):
    assert_refused(
        ValueError, "description of sim.run is empty", Recorder(), description, SCHEMA
    )


@pytest.mark.parametrize(
    "schema",
    [None, [], [SCHEMA], '{"type": "object"}', 3, ("type", "object"), Mapping(SCHEMA)],
)
def test_register_refuses_a_schema_that_is_not_a_dict(schema):
    assert_refused(
        TypeError, "schema of sim.run must be a dict", Recorder(), DESCRIPTION, schema
    )


@pytest.mark.parametrize(
    "member",
    [
        pytest.param({1: "a"}, id="int member name"),
        pytest.param({Text("a"): 1}, id="str subclass member name"),
        pytest.param({"a": float("nan")}, id="nan"),
        pytest.param({"a": [float("inf")]}, id="inf at depth"),
        pytest.param({"a": (1, 2)}, id="tuple"),
        pytest.param({"a": [{"b": {1, 2}}]}, id="set at depth"),
        pytest.param({"a": b"bytes"}, id="bytes"),
        pytest.param({"a": Mapping()}, id="dict subclass"),
        pytest.param({"a": cyclic()}, id="cyclic"),
        pytest.param({"a": nested(100_000)}, id="too deep"),
    ],
)
def test_register_refuses_a_schema_that_is_no_json_object(member):
    said = "schema of sim.run is not JSON: "
    schema = {"type": "object"} | member
    assert_refused(ValueError, said, Recorder(), DESCRIPTION, schema)


def test_register_refuses_a_schema_that_holds_itself():
    schema = {"type": "object"}
    schema["properties"] = {"example_member": schema}
    assert_refused(ValueError, "is not JSON: ", Recorder(), DESCRIPTION, schema)


@pytest.mark.parametrize(
    "schema",
    [
        pytest.param({}, id="no type"),
        pytest.param({"properties": {"type": "object"}}, id="type at depth only"),
        pytest.param({"type": "string"}, id="string"),
        pytest.param({"type": ["object"]}, id="list"),
        pytest.param({"type": ["object", "null"]}, id="longer list"),
        pytest.param({"type": None}, id="null"),
        pytest.param({"type": "Object"}, id="capital"),
        pytest.param({"type": "object "}, id="trailing blank"),
        pytest.param({"type": {"type": "object"}}, id="object"),
        pytest.param({"Type": "object"}, id="capital member name"),
    ],
)
def test_register_refuses_a_schema_whose_type_is_not_object(schema):
    assert_refused(
        ValueError, 'must have the type "object"', Recorder(), DESCRIPTION, schema
    )


@pytest.mark.parametrize(
    "arguments",
    [(), (DESCRIPTION,), (SCHEMA,)],
)
def test_register_has_no_default_for_the_description_or_the_schema(arguments):
    assert_refused(TypeError, "missing", Recorder(), *arguments)


def test_register_checks_the_description_before_the_schema():
    assert_refused(TypeError, "description", Recorder(), None, None)
    assert_refused(TypeError, "not callable", None, None, None)


# The reserved kinds


def test_the_reserved_kinds_are_the_five_of_the_record():
    assert tools.KIND_INVALID_REQUEST == "invalid_request"
    assert tools.KIND_NO_DATA_ROOT == "no_data_root"
    assert tools.KIND_STEP_OPEN == "step_open"
    assert tools.KIND_TOOL_CRASHED == "tool_crashed"
    assert tools.KIND_BAD_RESULT == "bad_result"
    assert type(tools.RESERVED_KINDS) is frozenset
    assert tools.RESERVED_KINDS == {
        "invalid_request",
        "no_data_root",
        "step_open",
        "tool_crashed",
        "bad_result",
    }
    assert journaled_step.KIND_STEP_OPEN is tools.KIND_STEP_OPEN


@pytest.mark.parametrize("kind", sorted(tools.RESERVED_KINDS))
def test_a_tool_failure_takes_a_reserved_kind_from_anyone(kind):
    assert ToolFailure(kind, "stated by a tool").kind == kind


def test_default_registry_is_empty_and_not_shared():
    first = default_registry()
    assert isinstance(first, Registry)
    assert first.names() == ()
    first.register("sim.run", Recorder(), DESCRIPTION, SCHEMA)
    assert default_registry().names() == ()


# check_json_object


@pytest.mark.parametrize("value", [{}, EVERY_JSON_TYPE, nested(20)])
def test_check_json_object_accepts_strict_json(value):
    assert check_json_object(value) is None


@pytest.mark.parametrize("value", NOT_OBJECTS)
def test_check_json_object_refuses_everything_else(value):
    with pytest.raises(ValueError):
        check_json_object(value)


def test_check_json_object_says_where():
    with pytest.raises(ValueError, match=r"\$\.a\[1\]\.b: set is not a JSON type"):
        check_json_object({"a": [0, {"b": set()}]})


# decode_request


def test_decode_request_returns_the_object():
    data = json.dumps(EVERY_JSON_TYPE, ensure_ascii=False).encode("utf-8")
    assert decode_request(data) == EVERY_JSON_TYPE
    assert decode_request(bytearray(b"{}")) == {}


@pytest.mark.parametrize("data", [b" {}", b"{}\n", b"\r\n\t {} \r\n", b'{"a":\n1}'])
def test_decode_request_accepts_whitespace_around_the_object(data):
    assert decode_request(data) in ({}, {"a": 1})


def test_decode_request_keeps_an_escaped_lone_surrogate():
    assert decode_request(b'{"a": "\\ud800"}') == {"a": "\ud800"}


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b"  \n", id="whitespace only"),
        pytest.param(b'{"a": "\xff"}', id="not utf-8"),
        pytest.param(b"\xef\xbb\xbf{}", id="byte order mark"),
        pytest.param("{}".encode("utf-16"), id="utf-16"),
        pytest.param(b"{", id="truncated"),
        pytest.param(b"{'a': 1}", id="single quotes"),
        pytest.param(b'{"a": 1,}', id="trailing comma"),
        pytest.param(b"[]", id="array"),
        pytest.param(b'"text"', id="string"),
        pytest.param(b"3", id="number"),
        pytest.param(b"null", id="null"),
        pytest.param(b"true", id="true"),
        pytest.param(b'{"a": NaN}', id="NaN"),
        pytest.param(b'{"a": [Infinity]}', id="Infinity"),
        pytest.param(b'{"a": -Infinity}', id="-Infinity"),
        pytest.param(b'{"a": 1e999}', id="float overflow"),
        pytest.param(b'{"a": 1, "a": 2}', id="duplicate member"),
        pytest.param(b'{"b": {"a": 1, "a": 1}}', id="duplicate member at depth"),
        pytest.param(b"{} {}", id="second object"),
        pytest.param(b"{}\n[]", id="second value"),
        pytest.param(b"{} x", id="trailing text"),
        pytest.param(b'{"a":' * 100_000 + b"1" + b"}" * 100_000, id="too deep"),
    ],
)
def test_decode_request_refuses_what_is_not_one_json_object(data):
    with pytest.raises(InvalidRequestError, match="not a request") as caught:
        decode_request(data)
    assert isinstance(caught.value, ValueError)
    assert not isinstance(caught.value, ToolFailure)


def test_decode_request_lists_the_members_of_the_object_with_a_duplicate():
    with pytest.raises(InvalidRequestError, match=r"given twice among \['a', 'b'\]"):
        decode_request(b'{"a": 1, "b": 2, "a": 3}')


@pytest.mark.parametrize("data", ["{}", None, 5, [b"{}"]])
def test_decode_request_refuses_what_is_not_bytes(data):
    with pytest.raises(TypeError, match="must be bytes"):
        decode_request(data)


# encode


def test_encode_is_one_compact_ascii_line_in_member_order():
    assert encode({"b": [1, 2.5, None], "a": {"c": True}}) == (
        b'{"b":[1,2.5,null],"a":{"c":true}}\n'
    )
    assert encode({}) == b"{}\n"


def test_encode_escapes_non_ascii_and_round_trips():
    line = encode(EVERY_JSON_TYPE)
    assert line.isascii()
    assert line.endswith(b"\n") and line.count(b"\n") == 1 and b"\r" not in line
    assert decode_request(line) == EVERY_JSON_TYPE
    assert encode({"a": "\ud800"}) == b'{"a":"\\ud800"}\n'


def test_encode_takes_an_error_object():
    line = encode(ToolFailure("refused", 'said "no"\n').error_object())
    assert line == b'{"error":{"kind":"refused","message":"said \\"no\\"\\n"}}\n'


def test_encode_refuses_a_non_finite_number():
    with pytest.raises(ValueError):
        encode({"a": float("nan")})


# call


def test_call_hands_the_request_over_and_returns_the_result():
    result = {"ok": True, "n": 3}
    tool = Recorder(result)
    request = {"spec": "gemm", "sizes": [1, 2]}
    assert call(registry_of(sim_run=tool), "sim.run", request) is result
    assert tool.requests == [request]
    assert tool.requests[0] is request


def test_call_passes_every_json_type_in_both_directions():
    tool = Recorder()
    assert (
        call(registry_of(sim_run=tool), "sim.run", EVERY_JSON_TYPE) is EVERY_JSON_TYPE
    )
    assert tool.requests == [EVERY_JSON_TYPE]


def test_call_accepts_an_empty_request_and_an_empty_result():
    tool = Recorder({})
    assert call(registry_of(sim_run=tool), "sim.run", {}) == {}
    assert tool.requests == [{}]


def test_call_reaches_only_the_named_tool():
    first, second = Recorder({"tool": 1}), Recorder({"tool": 2})
    registry = registry_of(sim_run=first, board_run=second)
    assert call(registry, "board.run", {}) == {"tool": 2}
    assert first.requests == []


def test_call_keeps_no_state_between_calls():
    tool = Recorder()
    registry = registry_of(sim_run=tool)
    assert call(registry, "sim.run", {"n": 1}) == {"n": 1}
    assert call(registry, "sim.run", {"n": 2}) == {"n": 2}
    assert registry.names() == ("sim.run",)


@pytest.mark.parametrize("name", ["board.run", "", "sim.run ", None])
def test_call_raises_the_lookup_error_for_an_unknown_name(name):
    tool = Recorder()
    with pytest.raises(UnknownToolError):
        call(registry_of(sim_run=tool), name, {})
    assert tool.requests == []


@pytest.mark.parametrize("request_value", NOT_OBJECTS)
def test_call_refuses_what_is_not_a_request_before_the_tool(request_value):
    tool = Recorder()
    with pytest.raises(InvalidRequestError, match="not a request") as caught:
        call(registry_of(sim_run=tool), "sim.run", request_value)
    assert isinstance(caught.value.__cause__, ValueError)
    assert tool.requests == []


def test_call_reports_an_unknown_name_before_a_bad_request():
    with pytest.raises(UnknownToolError):
        call(Registry(), "sim.run", None)


def test_call_lets_a_tool_failure_through_unchanged():
    failure = ToolFailure("backend_down", "no answer")
    with pytest.raises(ToolFailure) as caught:
        call(registry_of(sim_run=Recorder(failure)), "sim.run", {})
    assert caught.value is failure
    assert (caught.value.kind, caught.value.message) == ("backend_down", "no answer")


@pytest.mark.parametrize(
    "raised",
    [ValueError("bad value"), OSError(5, "disk gone"), Custom("mine"), KeyError("k")]
    + [UnknownToolError("inner"), InvalidRequestError("inner"), RecursionError()],
)
def test_call_turns_any_other_exception_into_a_tool_failure(raised):
    with pytest.raises(ToolFailure) as caught:
        call(registry_of(sim_run=Recorder(raised)), "sim.run", {})
    assert caught.value.kind == tools.KIND_TOOL_CRASHED == "tool_crashed"
    assert caught.value.message == f"{type(raised).__name__}: {raised}"
    assert caught.value.__cause__ is raised


@pytest.mark.parametrize("raised", [KeyboardInterrupt(), SystemExit(7)])
def test_call_does_not_catch_an_interrupt_or_an_exit(raised):
    with pytest.raises(type(raised)) as caught:
        call(registry_of(sim_run=Recorder(raised)), "sim.run", {})
    assert caught.value is raised


@pytest.mark.parametrize("result", NOT_OBJECTS)
def test_call_turns_what_is_not_a_result_into_a_tool_failure(result):
    tool = Recorder(result)
    with pytest.raises(ToolFailure, match="not a result") as caught:
        call(registry_of(sim_run=tool), "sim.run", {})
    assert caught.value.kind == tools.KIND_BAD_RESULT == "bad_result"
    assert isinstance(caught.value.__cause__, ValueError)
    assert tool.requests == [{}]


def test_call_turns_a_missing_return_value_into_a_tool_failure():
    with pytest.raises(ToolFailure, match="expected an object, got NoneType"):
        call(registry_of(sim_run=lambda request: None), "sim.run", {})


@pytest.mark.parametrize(
    "request_value",
    [
        pytest.param({}, id="required member absent"),
        pytest.param({"example_text": 3}, id="wrong type"),
        pytest.param({"example_text": "a", "example_other": None}, id="further member"),
    ],
)
def test_call_compares_no_request_with_the_schema(request_value):
    tool = Recorder()
    registry = Registry()
    registry.register("sim.run", tool, DESCRIPTION, RICH_SCHEMA)
    assert call(registry, "sim.run", request_value) is request_value
    assert tool.requests == [request_value]
    assert tool.requests[0] is request_value


@pytest.mark.parametrize("kind", sorted(tools.RESERVED_KINDS))
def test_call_lets_a_tool_failure_of_a_reserved_kind_through_unchanged(kind):
    failure = ToolFailure(kind, "stated by the tool function")
    with pytest.raises(ToolFailure) as caught:
        call(registry_of(sim_run=Recorder(failure)), "sim.run", {})
    assert caught.value is failure
    assert caught.value.__cause__ is None
    assert caught.value.error_object() == {
        "error": {"kind": kind, "message": "stated by the tool function"}
    }
