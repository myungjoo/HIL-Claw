import json

import pytest

from hilclaw import tools
from hilclaw.tools import (
    InvalidRequestError,
    Registry,
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
        registry.register(name.replace("_", "."), function)
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
    registry.register("sim.run", first)
    registry.register("blob.push", second)
    assert registry.get("sim.run") is first
    assert registry.get("blob.push") is second
    assert registry.names() == ("blob.push", "sim.run")


@pytest.mark.parametrize("name", ["a", "sim.run", "a1.b2.c3", "profiler.collect"])
def test_register_accepts_dotted_lowercase_words(name):
    registry = Registry()
    registry.register(name, dict)
    assert registry.names() == (name,)


@pytest.mark.parametrize(
    "name",
    ["", "Sim.run", "sim.Run", "sim_run", "sim run", ".sim", "sim.", "sim..run"]
    + ["1sim", "sim.1", "sim-run", "sim.run\n", "--help", "sím.run"],
)
def test_register_refuses_a_name_that_breaks_the_rule(name):
    registry = Registry()
    with pytest.raises(ValueError, match="not a tool name"):
        registry.register(name, dict)
    assert registry.names() == ()


@pytest.mark.parametrize("name", [None, 1, b"sim.run", ("sim", "run"), Text("sim.run")])
def test_register_refuses_a_name_that_is_not_a_str(name):
    registry = Registry()
    with pytest.raises(TypeError, match="must be a str"):
        registry.register(name, dict)
    assert registry.names() == ()


@pytest.mark.parametrize("function", [None, "sim.run", 1, {}])
def test_register_refuses_a_function_that_is_not_callable(function):
    registry = Registry()
    with pytest.raises(TypeError, match="not callable"):
        registry.register("sim.run", function)
    assert registry.names() == ()


def test_register_refuses_a_second_function_for_one_name():
    first = Recorder()
    registry = registry_of(sim_run=first)
    with pytest.raises(ValueError, match="registered already"):
        registry.register("sim.run", Recorder())
    assert registry.get("sim.run") is first


@pytest.mark.parametrize("name", ["board.run", "sim", "sim.run.x", "", None, 1, []])
def test_get_raises_its_own_lookup_error(name):
    registry = registry_of(sim_run=Recorder())
    with pytest.raises(UnknownToolError, match="unknown tool") as caught:
        registry.get(name)
    assert isinstance(caught.value, LookupError)
    assert not isinstance(caught.value, ToolFailure)


def test_default_registry_is_empty_and_not_shared():
    first = default_registry()
    assert isinstance(first, Registry)
    assert first.names() == ()
    first.register("sim.run", Recorder())
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
