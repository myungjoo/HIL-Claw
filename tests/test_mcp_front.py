import io
import json
import queue
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from hilclaw import __main__ as command_line
from hilclaw import __version__, config, data_root_source, mcp_front, tools
from hilclaw.mcp_front import main, mcp_name, mcp_names
from hilclaw.tools import Registry, ToolFailure, default_registry

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXED_NAMES = {
    "sim.run": "sim_run",
    "board.run": "board_run",
    "profiler.collect": "profiler_collect",
    "correctness.check": "correctness_check",
    "blob.push": "blob_push",
    "blob.fetch": "blob_fetch",
    "state.read": "state_read",
    "instance.read": "instance_read",
    "run.fresh": "run_fresh",
    "state.write": "state_write",
    "verdicts.write": "verdicts_write",
    "run.commit": "run_commit",
}
NON_ASCII = {"text": "héllo 한글 \U0001f600", "키": [1, 2.5, None, True, {"a": {}}]}
INITIALIZE = {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "test client", "version": "0"},
}
SERVER = {
    "protocolVersion": "2025-06-18",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "hilclaw", "version": __version__},
}

HELPER_SCRIPT = """\
import sys

sys.path.insert(0, {root!r})

from hilclaw.mcp_front import main
from hilclaw.tools import Registry

registry = Registry()
registry.register(
    "test.echo", lambda request: {{"echo": request}}, {description!a}, {schema!r}
)
registry.register("test.also", lambda request: {{}}, "Another tool.", {{"type": "object"}})
raise SystemExit(main(registry=registry))
"""

DESCRIPTION = "A tool of the tests."
SCHEMA = {"type": "object"}
NON_ASCII_DESCRIPTION = "Echoes the request. héllo 한글 \U0001f600"
NESTED_SCHEMA = {
    "type": "object",
    "properties": {
        "example_list": {"type": "array", "items": {"type": ["string", "null"]}},
        "example_object": {
            "type": "object",
            "properties": {"example_number": {"type": "number", "minimum": 0.5}},
            "additionalProperties": False,
        },
    },
    "required": ["example_list"],
}


class Calls:
    def __init__(self):
        self.requests = []

    def echo(self, request):
        self.requests.append(request)
        return {"echo": request}


class BrokenStream(io.BytesIO):
    def write(self, data):
        raise BrokenPipeError(32, "Broken pipe")


class UnreadableStream(io.BytesIO):
    def readline(self, *args):
        raise OSError(5, "Input/output error")


def raising(error):
    def tool(request):
        raise error

    return tool


def registry_with(**functions):
    registry = Registry()
    for name, function in functions.items():
        registry.register(name.replace("_", "."), function, DESCRIPTION, SCHEMA)
    return registry


def message(method, request_id=None, params=None):
    document = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        document["id"] = request_id
    if params is not None:
        document["params"] = params
    return json.dumps(document, ensure_ascii=False).encode("utf-8") + b"\n"


def call(request_id, name, arguments=None):
    params = {"name": name}
    if arguments is not None:
        params["arguments"] = arguments
    return message("tools/call", request_id, params)


def serve(data, registry=None, stdout=None, stderr=None, stdin=None):
    stdin = io.BytesIO(data) if stdin is None else stdin
    stdout = io.BytesIO() if stdout is None else stdout
    stderr = io.BytesIO() if stderr is None else stderr
    registry = Registry() if registry is None else registry
    status = main([], registry=registry, stdin=stdin, stdout=stdout, stderr=stderr)
    return status, stdout.getvalue(), stderr.getvalue()


def responses(out):
    assert b"\r" not in out
    assert out == b"" or out.endswith(b"\n")
    lines = out.split(b"\n")[:-1]
    assert all(line.isascii() and line for line in lines)
    documents = [json.loads(line) for line in lines]
    for document in documents:
        assert document["jsonrpc"] == "2.0"
        assert list(document) in (
            ["jsonrpc", "id", "result"],
            ["jsonrpc", "id", "error"],
        )
    return documents


def served(data, registry=None):
    status, out, err = serve(data, registry)
    assert (status, err) == (0, b"")
    return responses(out)


def error_of(document, code, request_id=None):
    assert document["id"] == request_id and type(document["id"]) is type(request_id)
    assert list(document["error"]) == ["code", "message"]
    assert document["error"]["code"] == code
    assert isinstance(document["error"]["message"], str)
    return document["error"]["message"]


def outcome_of(document, is_error=False):
    result = document["result"]
    assert list(result) == ["content", "isError"]
    assert result["isError"] is is_error
    (block,) = result["content"]
    assert list(block) == ["type", "text"] and block["type"] == "text"
    return json.loads(block["text"])


# Names


@pytest.mark.parametrize(("name", "expected"), FIXED_NAMES.items())
def test_mcp_name_replaces_each_dot(name, expected):
    assert mcp_name(name) == expected


def test_mcp_name_of_a_longer_name():
    assert mcp_name("a.b.c") == "a_b_c"
    assert mcp_name("plain") == "plain"


def test_mcp_names_is_the_table_of_the_registry():
    registry = registry_with(test_echo=Calls().echo, a_b=lambda r: {})
    assert mcp_names(registry) == {"a_b": "a.b", "test_echo": "test.echo"}
    assert list(mcp_names(registry)) == ["a_b", "test_echo"]
    assert mcp_names(Registry()) == {}


# The handshake and a call


def test_handshake_list_and_call():
    calls = Calls()
    data = (
        message("initialize", 1, INITIALIZE)
        + message("notifications/initialized")
        + message("tools/list", 2)
        + call(3, "test_echo", {"n": 1})
    )
    first, listed, called = served(data, registry_with(test_echo=calls.echo))
    assert first == {"jsonrpc": "2.0", "id": 1, "result": SERVER}
    assert mcp_front.SERVER_NAME == "hilclaw"
    assert listed == {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {
            "tools": [
                {
                    "name": "test_echo",
                    "description": DESCRIPTION,
                    "inputSchema": SCHEMA,
                }
            ]
        },
    }
    assert list(listed["result"]["tools"][0]) == ["name", "description", "inputSchema"]
    assert called["id"] == 3
    assert outcome_of(called) == {"echo": {"n": 1}}
    assert calls.requests == [{"n": 1}]


def test_a_call_is_exact_bytes():
    status, out, err = serve(
        call(1, "test_echo", {"n": 1}), registry_with(test_echo=Calls().echo)
    )
    assert (status, err) == (mcp_front.EXIT_END_OF_INPUT, b"")
    assert out == (
        b'{"jsonrpc":"2.0","id":1,"result":{"content":[{"type":"text",'
        b'"text":"{\\"echo\\":{\\"n\\":1}}"}],"isError":false}}\n'
    )


def test_a_non_ascii_request_round_trips():
    calls = Calls()
    (called,) = served(
        call("한글", "test_echo", NON_ASCII), registry_with(test_echo=calls.echo)
    )
    assert called["id"] == "한글"
    assert outcome_of(called) == {"echo": NON_ASCII}
    assert calls.requests == [NON_ASCII]


@pytest.mark.parametrize("request_id", [0, 7, -3, 2**70, "7", "", "a b"])
def test_an_id_is_echoed_with_its_type(request_id):
    (document,) = served(message("ping", request_id))
    assert document == {"jsonrpc": "2.0", "id": request_id, "result": {}}
    assert type(document["id"]) is type(request_id)


def test_several_calls_are_answered_in_order():
    registry = registry_with(test_echo=Calls().echo)
    data = b"".join(call(i, "test_echo", {"i": i}) for i in range(20))
    documents = served(data, registry)
    assert [d["id"] for d in documents] == list(range(20))
    assert [outcome_of(d) for d in documents] == [{"echo": {"i": i}} for i in range(20)]


def test_list_is_sorted_by_name_on_one_page():
    registry = registry_with(b_two=lambda r: {}, a_one=lambda r: {}, c=lambda r: {})
    (listed,) = served(message("tools/list", 1, {"_meta": {}}), registry)
    assert [tool["name"] for tool in listed["result"]["tools"]] == [
        "a_one",
        "b_two",
        "c",
    ]
    assert list(listed["result"]) == ["tools"]


def test_list_shows_the_description_and_the_schema_of_each_tool():
    registry = Registry()
    registry.register("b.two", lambda r: {}, NON_ASCII_DESCRIPTION, NESTED_SCHEMA)
    registry.register("a.one", lambda r: {}, "The first.", SCHEMA)
    registry.register(
        "c", lambda r: {}, "  kept as it is\n", {"type": "object", "x": 1}
    )
    (listed,) = served(message("tools/list", 1), registry)
    assert listed["result"] == {
        "tools": [
            {"name": "a_one", "description": "The first.", "inputSchema": SCHEMA},
            {
                "name": "b_two",
                "description": NON_ASCII_DESCRIPTION,
                "inputSchema": NESTED_SCHEMA,
            },
            {
                "name": "c",
                "description": "  kept as it is\n",
                "inputSchema": {"type": "object", "x": 1},
            },
        ]
    }
    for tool in listed["result"]["tools"]:
        assert list(tool) == ["name", "description", "inputSchema"]
    assert list(listed["result"]["tools"][1]["inputSchema"]) == list(NESTED_SCHEMA)


def test_list_of_an_empty_registry_has_no_tool():
    (listed,) = served(message("tools/list", 1), Registry())
    assert listed == {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}


def test_two_lists_of_one_session_are_equal():
    registry = Registry()
    registry.register("test.echo", Calls().echo, NON_ASCII_DESCRIPTION, NESTED_SCHEMA)
    data = (
        message("tools/list", 1)
        + call(2, "test_echo", {"n": 1})
        + message("tools/list", 1)
    )
    status, out, err = serve(data, registry)
    assert (status, err) == (0, b"")
    first, _, second = out.split(b"\n")[:-1]
    assert first == second
    assert registry.definition("test.echo").input_schema == NESTED_SCHEMA


@pytest.mark.parametrize(
    "arguments",
    [
        pytest.param({}, id="required member absent"),
        pytest.param({"example_list": 3}, id="wrong type"),
        pytest.param({"example_object": {"example_other": None}}, id="further member"),
    ],
)
def test_a_call_is_not_compared_with_the_schema(arguments):
    calls = Calls()
    registry = Registry()
    registry.register("test.echo", calls.echo, DESCRIPTION, NESTED_SCHEMA)
    (called,) = served(call(1, "test_echo", arguments), registry)
    assert outcome_of(called) == {"echo": arguments}
    assert calls.requests == [arguments]


@pytest.mark.parametrize("cursor", ["x", "", 0, 3, {}, []])
def test_a_cursor_is_refused_because_no_page_follows(cursor):
    registry = registry_with(test_echo=Calls().echo)
    data = message("tools/list", 1, {"cursor": cursor}) + message("tools/list", 2)
    refused, listed = served(data, registry)
    assert error_of(refused, -32602, 1) == "unknown cursor"
    assert [tool["name"] for tool in listed["result"]["tools"]] == ["test_echo"]


def test_arguments_may_be_absent():
    calls = Calls()
    (called,) = served(call(1, "test_echo"), registry_with(test_echo=calls.echo))
    assert outcome_of(called) == {"echo": {}}
    assert calls.requests == [{}]


def test_a_progress_token_gets_no_progress():
    params = {"name": "test_echo", "arguments": {}, "_meta": {"progressToken": "p"}}
    registry = registry_with(test_echo=Calls().echo)
    (called,) = served(message("tools/call", 1, params), registry)
    assert outcome_of(called) == {"echo": {}}


def test_a_long_line_is_served():
    text = "x" * 2_000_000
    (called,) = served(
        call(1, "test_echo", {"t": text}), registry_with(test_echo=Calls().echo)
    )
    assert outcome_of(called) == {"echo": {"t": text}}


def test_crlf_from_the_client_is_accepted_and_never_written():
    data = message("ping", 1).replace(b"\n", b"\r\n") * 2
    status, out, _ = serve(data)
    assert status == 0
    assert out == b'{"jsonrpc":"2.0","id":1,"result":{}}\n' * 2


# The text block is what the command-line front writes


@pytest.mark.parametrize(
    "tool",
    [
        lambda request: {"echo": request, "키": "값"},
        raising(ToolFailure("backend_down", "no answer from the board")),
        raising(ValueError("bad value")),
        lambda request: None,
    ],
)
def test_the_text_block_equals_the_line_of_the_command_line_front(tool):
    registry = registry_with(test_tool=tool)
    (called,) = served(call(1, "test_tool", NON_ASCII), registry)
    (block,) = called["result"]["content"]
    stdout = io.BytesIO()
    status = command_line.main(
        ["test.tool"],
        registry=registry,
        stdin=io.BytesIO(json.dumps(NON_ASCII).encode()),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert block["text"].encode("ascii") + b"\n" == stdout.getvalue()
    assert called["result"]["isError"] is (status != 0)


# Tool failures


def test_a_tool_failure_is_the_error_object_with_is_error():
    failure = ToolFailure("backend_down", "no answer from the board")
    (called,) = served(call(1, "test_fail"), registry_with(test_fail=raising(failure)))
    assert outcome_of(called, is_error=True) == {
        "error": {"kind": "backend_down", "message": "no answer from the board"}
    }


def test_a_tool_that_raises_anything_else_is_tool_crashed():
    registry = registry_with(test_crash=raising(ValueError("bad value")))
    (called,) = served(call(1, "test_crash"), registry)
    assert outcome_of(called, is_error=True) == {
        "error": {"kind": "tool_crashed", "message": "ValueError: bad value"}
    }


@pytest.mark.parametrize("result", [None, [], "text", {"a": float("nan")}, {1: 2}])
def test_a_tool_that_returns_no_result_is_bad_result(result):
    registry = registry_with(test_odd=lambda request: result)
    (called,) = served(call(1, "test_odd"), registry)
    error = outcome_of(called, is_error=True)["error"]
    assert error["kind"] == "bad_result"
    assert "not a result" in error["message"]


def test_a_result_may_look_like_an_error_object():
    result = {"error": {"kind": "none", "message": "a result of the tool"}}
    (called,) = served(call(1, "test_odd"), registry_with(test_odd=lambda r: result))
    assert outcome_of(called, is_error=False) == result


def test_the_server_serves_on_after_a_tool_failure():
    registry = registry_with(
        test_crash=raising(OSError("gone")), test_echo=Calls().echo
    )
    failed, called = served(call(1, "test_crash") + call(2, "test_echo"), registry)
    assert outcome_of(failed, is_error=True)["error"]["kind"] == "tool_crashed"
    assert outcome_of(called) == {"echo": {}}


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(9)])
def test_an_interrupt_of_a_tool_is_not_answered(error):
    registry = registry_with(test_stop=raising(error))
    stdout = io.BytesIO()
    with pytest.raises(type(error)):
        serve(message("ping", 1) + call(2, "test_stop"), registry, stdout=stdout)
    assert stdout.getvalue() == b'{"jsonrpc":"2.0","id":1,"result":{}}\n'


# The fixed tool set


def test_the_fixed_tool_set_is_the_blob_tools_correctness_check_and_run_file_tools():
    """The C-3 pair (ADR-0039), correctness.check (ADR-0070), the run-file tools (ADR-0124), run.commit (ADR-0127) and verdicts.write (ADR-0128)."""
    held = {
        "blob_fetch": "blob.fetch",
        "blob_push": "blob.push",
        "correctness_check": "correctness.check",
        "instance_read": "instance.read",
        "run_commit": "run.commit",
        "run_fresh": "run.fresh",
        "state_read": "state.read",
        "state_write": "state.write",
        "verdicts_write": "verdicts.write",
    }
    assert mcp_names(default_registry(lambda: REPO_ROOT)) == held
    unknown = [name for name in FIXED_NAMES.values() if name not in held]
    data = message("tools/list", 0) + b"".join(
        call(i, name) for i, name in enumerate(unknown, 1)
    )
    stdout = io.BytesIO()
    status = main([], stdin=io.BytesIO(data), stdout=stdout, stderr=io.BytesIO())
    assert status == 0
    listed, *refused = responses(stdout.getvalue())
    assert [tool["name"] for tool in listed["result"]["tools"]] == list(held)
    assert len(refused) == 3
    for i, (name, document) in enumerate(zip(unknown, refused), 1):
        assert error_of(document, -32602, i) == f"unknown tool {name!r}"


def test_the_default_registry_is_bound_to_the_configured_source(monkeypatch):
    bound = []
    monkeypatch.setattr(
        tools, "default_registry", lambda source: bound.append(source) or Registry()
    )
    main([], stdin=io.BytesIO(b""), stdout=io.BytesIO(), stderr=io.BytesIO())
    assert bound == [data_root_source.configured]
    main([], registry=Registry(), stdin=io.BytesIO(b""), stdout=io.BytesIO())
    assert len(bound) == 1


def test_the_default_registry_asks_no_source_to_list_or_to_refuse(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", tmp_path / "missing.json")
    with pytest.raises(config.ConfigError):
        config.load_data_repo()
    data = message("tools/list", 1) + call(2, "sim_run", {})
    stdout, stderr = io.BytesIO(), io.BytesIO()
    assert main([], stdin=io.BytesIO(data), stdout=stdout, stderr=stderr) == 0
    listed, refused = responses(stdout.getvalue())
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert names == [
        "blob_fetch",
        "blob_push",
        "correctness_check",
        "instance_read",
        "run_commit",
        "run_fresh",
        "state_read",
        "state_write",
        "verdicts_write",
    ]
    assert error_of(refused, -32602, 2) == "unknown tool 'sim_run'"
    assert stderr.getvalue() == b""


# Protocol revisions and the connection state


def test_the_implemented_revision_is_answered_as_requested():
    assert mcp_front.PROTOCOL_VERSIONS == ("2025-06-18",)
    (document,) = served(message("initialize", 1, INITIALIZE))
    assert document["result"] == SERVER


@pytest.mark.parametrize(
    "revision",
    ["2025-03-26", "2024-11-05", "1999-01-01", "2099-01-01", "", 3, None, ["x"]],
)
def test_another_revision_is_answered_with_the_implemented_one(revision):
    (document,) = served(
        message("initialize", 1, INITIALIZE | {"protocolVersion": revision})
    )
    assert document["result"] == SERVER


def test_initialize_without_params_is_answered_with_the_implemented_revision():
    (document,) = served(message("initialize", 1))
    assert document["result"] == SERVER


def test_requests_are_served_before_and_after_initialize():
    calls = Calls()
    one = call("c", "test_echo", {"n": 1})
    data = (
        one
        + message("tools/list", "l")
        + message("initialize", 1, INITIALIZE)
        + message("notifications/initialized")
        + message("initialize", 2, INITIALIZE)
        + one
        + message("tools/list", "l")
        + call(3, "test_fail")
        + one
    )
    registry = registry_with(test_echo=calls.echo, test_fail=raising(OSError("x")))
    documents = served(data, registry)
    assert len(documents) == 8
    assert documents[0] == documents[4] == documents[7]
    assert documents[1] == documents[5]
    assert documents[2]["result"] == documents[3]["result"] == SERVER
    assert calls.requests == [{"n": 1}] * 3


# What reaches no tool function


@pytest.mark.parametrize(
    "name",
    ["test_other", "test.echo", "TEST_ECHO", "test", "", "mcp__hilclaw__test_echo"],
)
def test_an_unknown_tool_is_a_json_rpc_error(name):
    calls = Calls()
    refused, pinged = served(
        call(1, name, {}) + message("ping", 2), registry_with(test_echo=calls.echo)
    )
    assert error_of(refused, mcp_front.INVALID_PARAMS, 1) == f"unknown tool {name!r}"
    assert pinged == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert calls.requests == []


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({}, id="no name"),
        pytest.param({"arguments": {}}, id="arguments only"),
        pytest.param({"name": 3}, id="number"),
        pytest.param({"name": None}, id="null"),
        pytest.param({"name": ["test_echo"]}, id="list"),
        pytest.param({"name": {"test_echo": 1}}, id="object"),
    ],
)
def test_a_call_without_a_tool_name_is_a_json_rpc_error(params):
    calls = Calls()
    refused, pinged = served(
        message("tools/call", 1, params) + message("ping", 2),
        registry_with(test_echo=calls.echo),
    )
    assert "unknown tool" in error_of(refused, -32602, 1)
    assert pinged["result"] == {}
    assert calls.requests == []


@pytest.mark.parametrize("arguments", [[], [{}], "text", 3, 2.5, True])
def test_arguments_that_are_no_request_are_a_json_rpc_error(arguments):
    calls = Calls()
    refused, pinged = served(
        call(1, "test_echo", arguments) + message("ping", 2),
        registry_with(test_echo=calls.echo),
    )
    assert "not a request" in error_of(refused, -32602, 1)
    assert pinged["result"] == {}
    assert calls.requests == []


def test_null_arguments_are_no_request():
    calls = Calls()
    line = b'{"jsonrpc":"2.0","id":1,"method":"tools/call",'
    line += b'"params":{"name":"test_echo","arguments":null}}\n'
    (refused,) = served(line, registry_with(test_echo=calls.echo))
    assert "not a request" in error_of(refused, -32602, 1)
    assert calls.requests == []


@pytest.mark.parametrize(
    "method",
    ["resources/list", "prompts/list", "tools", "tools/call/", "PING", "", "shutdown"],
)
def test_an_unknown_method(method):
    refused, pinged = served(message(method, 1) + message("ping", 2))
    assert error_of(refused, mcp_front.METHOD_NOT_FOUND, 1) == (
        f"unknown method {method!r}"
    )
    assert mcp_front.METHOD_NOT_FOUND == -32601
    assert pinged["result"] == {}


@pytest.mark.parametrize("params", ["[]", "[1]", '"text"', "3", "null", "true"])
@pytest.mark.parametrize("method", ["ping", "initialize", "tools/list", "tools/call"])
def test_params_that_are_no_object(method, params):
    line = f'{{"jsonrpc":"2.0","id":1,"method":"{method}","params":{params}}}\n'
    calls = Calls()
    refused, pinged = served(
        line.encode() + message("ping", 2), registry_with(test_echo=calls.echo)
    )
    assert error_of(refused, -32602, 1) == "the params must be an object"
    assert pinged["result"] == {}
    assert calls.requests == []


@pytest.mark.parametrize(
    "line",
    [
        pytest.param(b"{", id="not json"),
        pytest.param(b"ping", id="a word"),
        pytest.param(b'{"jsonrpc":"2.0","id":1,"method":"ping"', id="cut off"),
        pytest.param(b'{"jsonrpc":"2.0","id":1,"method":"\xff"}', id="not utf-8"),
        pytest.param(
            b'\xef\xbb\xbf{"jsonrpc":"2.0","id":1,"method":"ping"}',
            id="byte order mark",
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":'
            b'{"name":"test_echo","arguments":{"a":NaN}}}',
            id="NaN",
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"a":-Infinity}}',
            id="-Infinity",
        ),
        pytest.param(b'{"jsonrpc":"2.0","id":1,"method":"ping"} {}', id="two objects"),
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"method":"ping","params":{"a":'
            + b"1" * 5_000
            + b"}}",
            id="an integer longer than the interpreter converts",
        ),
    ],
)
def test_a_line_that_is_not_json_is_a_parse_error(line):
    calls = Calls()
    refused, pinged = served(
        line + b"\n" + message("ping", 2), registry_with(test_echo=calls.echo)
    )
    assert "not JSON" in error_of(refused, mcp_front.PARSE_ERROR, None)
    assert mcp_front.PARSE_ERROR == -32700
    assert pinged == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert calls.requests == []


@pytest.mark.parametrize(
    "line",
    [
        pytest.param(b"[]", id="empty array"),
        pytest.param(b'[{"jsonrpc":"2.0","id":1,"method":"ping"}]', id="batch"),
        pytest.param(b'"text"', id="string"),
        pytest.param(b"3", id="number"),
        pytest.param(b"null", id="null"),
        pytest.param(b"true", id="boolean"),
    ],
)
def test_json_that_is_no_object_is_an_invalid_request(line):
    refused, pinged = served(line + b"\n" + message("ping", 2))
    assert "not a message" in error_of(refused, mcp_front.INVALID_REQUEST, None)
    assert mcp_front.INVALID_REQUEST == -32600
    assert pinged["result"] == {}


@pytest.mark.parametrize(
    ("line", "request_id"),
    [
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"method":"ping","method":"ping"}',
            1,
            id="duplicate member",
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","id":"a","method":"tools/call","params":'
            b'{"name":"test_echo","arguments":{"a":1,"a":2}}}',
            "a",
            id="duplicate member in arguments",
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":'
            b'{"name":"test_echo","arguments":{"a":1e999}}}',
            1,
            id="number beyond a float",
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"method":"ping","id":2}', 2, id="the last id"
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","method":"ping","params":{},"params":{}}',
            None,
            id="no id",
        ),
        pytest.param(
            b'{"jsonrpc":"2.0","id":null,"method":"ping","a":1,"a":2}',
            None,
            id="no usable id",
        ),
    ],
)
def test_a_message_the_strict_reading_refuses_is_answered_with_its_id(line, request_id):
    calls = Calls()
    refused, pinged = served(
        line + b"\n" + message("ping", 2), registry_with(test_echo=calls.echo)
    )
    assert "not a message" in error_of(refused, -32600, request_id)
    assert pinged["result"] == {}
    assert calls.requests == []


@pytest.mark.parametrize("depth", [600, 2_000, 20_000, 100_000])
def test_a_message_nested_too_deeply_is_an_invalid_request(depth):
    """The id is given back only where the interpreter can read that deep."""
    calls = Calls()
    line = b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":'
    line += b'{"name":"test_echo","arguments":' + b'{"a":' * depth + b"1"
    line += b"}" * (depth + 2)
    refused, pinged = served(
        line + b"\n" + message("ping", 2), registry_with(test_echo=calls.echo)
    )
    assert refused["error"]["code"] == -32600
    assert "not a message" in refused["error"]["message"]
    assert refused["id"] in (None, 1)
    assert pinged == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert calls.requests == []


def test_a_line_that_only_opens_arrays_is_refused():
    """Not JSON where the interpreter reads it to its end, too deep where it cannot."""
    refused, pinged = served(b"[" * 100_000 + b"\n" + message("ping", 2))
    assert refused["id"] is None
    assert refused["error"]["code"] in (-32700, -32600)
    assert pinged["result"] == {}


@pytest.mark.parametrize(
    ("line", "request_id", "said"),
    [
        ('{"id":7,"method":"ping"}', 7, 'the member "jsonrpc" must be "2.0"'),
        ('{"jsonrpc":"1.0","id":"a","method":"ping"}', "a", 'the member "jsonrpc"'),
        ('{"jsonrpc":2.0,"id":7,"method":"ping"}', 7, 'the member "jsonrpc"'),
        ('{"method":"notifications/initialized"}', None, 'the member "jsonrpc"'),
        ('{"id":7,"result":{}}', 7, 'the member "jsonrpc"'),
        ("{}", None, 'the member "jsonrpc"'),
        ('{"jsonrpc":"2.0","id":5,"method":3}', 5, "the method must be a string"),
        ('{"jsonrpc":"2.0","id":5,"method":null}', 5, "the method must be a string"),
        ('{"jsonrpc":"2.0","id":5,"method":["ping"]}', 5, "the method must be"),
        ('{"jsonrpc":"2.0","method":{}}', None, "the method must be a string"),
        ('{"jsonrpc":"2.0","id":5}', 5, "the method must be a string"),
        ('{"jsonrpc":"2.0"}', None, "the method must be a string"),
        ('{"jsonrpc":"2.0","id":null,"method":"ping"}', None, "the id must be"),
        ('{"jsonrpc":"2.0","id":true,"method":"ping"}', None, "the id must be"),
        ('{"jsonrpc":"2.0","id":1.0,"method":"ping"}', None, "the id must be"),
        ('{"jsonrpc":"2.0","id":{},"method":"ping"}', None, "the id must be"),
        ('{"jsonrpc":"2.0","id":[1],"method":"tools/call"}', None, "the id must be"),
        ('{"jsonrpc":"2.0","id":null,"method":"no/such"}', None, "the id must be"),
    ],
)
def test_an_object_that_is_no_message_is_an_invalid_request(line, request_id, said):
    calls = Calls()
    refused, pinged = served(
        line.encode() + b"\n" + message("ping", 2), registry_with(test_echo=calls.echo)
    )
    assert said in error_of(refused, -32600, request_id)
    assert pinged["result"] == {}
    assert calls.requests == []


@pytest.mark.parametrize(
    "line",
    [
        pytest.param(message("notifications/initialized"), id="initialized"),
        pytest.param(
            message("notifications/cancelled", params={"requestId": 1}), id="cancelled"
        ),
        pytest.param(message("notifications/no/such"), id="unknown notification"),
        pytest.param(message("ping"), id="a request method without an id"),
        pytest.param(
            call(None, "test_echo", {}), id="a call without an id calls no tool"
        ),
        pytest.param(b'{"jsonrpc":"2.0","method":"x","params":[1]}\n', id="odd params"),
        pytest.param(b'{"jsonrpc":"2.0","id":1,"result":{}}\n', id="a response"),
        pytest.param(
            b'{"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"m"}}\n',
            id="an error response",
        ),
        pytest.param(b'{"jsonrpc":"2.0","id":null,"result":{}}\n', id="odd response"),
        pytest.param(b"\n", id="empty line"),
        pytest.param(b"\r\n", id="empty line with CR"),
        pytest.param(b" \t \n", id="blank line"),
    ],
)
def test_what_gets_no_answer(line):
    calls = Calls()
    data = line + message("ping", 2) + line
    (pinged,) = served(data, registry_with(test_echo=calls.echo))
    assert pinged == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert calls.requests == []


# The end of input


def test_no_input_is_a_clean_end():
    assert serve(b"") == (0, b"", b"")


def test_a_last_line_without_lf_is_served():
    status, out, err = serve(message("ping", 1) + message("ping", 2)[:-1])
    assert (status, err) == (0, b"")
    assert [d["id"] for d in responses(out)] == [1, 2]


def test_input_that_ends_inside_a_message():
    status, out, err = serve(message("ping", 1) + message("ping", 2)[:-9])
    assert (status, err) == (0, b"")
    pinged, refused = responses(out)
    assert pinged["id"] == 1
    error_of(refused, -32700, None)


# Streams that fail


def closed():
    stream = io.BytesIO(b"")
    stream.close()
    return stream


@pytest.mark.parametrize("stdin", [UnreadableStream(), closed()])
def test_an_input_that_cannot_be_read(stdin):
    status, out, err = serve(b"", stdin=stdin)
    assert status == mcp_front.EXIT_FRONT_FAILURE == command_line.EXIT_FRONT_FAILURE
    assert out == b""
    assert err.startswith(b"hilclaw.mcp_front: cannot read standard input: ")
    assert err.endswith(b"\n") and err.count(b"\n") == 1


@pytest.mark.parametrize("stdout", [BrokenStream(), closed()])
def test_an_output_that_cannot_be_written(stdout):
    calls = Calls()
    data = message("notifications/initialized") + call(1, "test_echo") * 3
    stderr = io.BytesIO()
    status = main(
        [],
        registry=registry_with(test_echo=calls.echo),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=stderr,
    )
    assert status == mcp_front.EXIT_FRONT_FAILURE == 4
    assert stderr.getvalue().startswith(
        b"hilclaw.mcp_front: cannot write standard output: "
    )
    assert calls.requests == [{}]


@pytest.mark.parametrize("stderr", [BrokenStream(), closed()])
def test_a_standard_error_that_cannot_be_written_changes_nothing(stderr):
    data = message("ping", 1)
    status = main([], stdin=io.BytesIO(data), stdout=BrokenStream(), stderr=stderr)
    assert status == 4
    stdout = io.BytesIO()
    status = main(
        [], stdin=io.BytesIO(message("ping", 1)), stdout=stdout, stderr=stderr
    )
    assert status == 0
    assert stdout.getvalue() == b'{"jsonrpc":"2.0","id":1,"result":{}}\n'


@pytest.mark.parametrize("args", [["sim_run"], ["--help"], ("a", "b")])
def test_an_argument_is_refused_before_anything_is_read(args):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = main(args, stdin=UnreadableStream(), stdout=stdout, stderr=stderr)
    assert status == mcp_front.EXIT_FRONT_FAILURE
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == (
        f"hilclaw.mcp_front: expected no argument, got {len(args)}\n".encode()
    )


# Defaults


class Standard:
    def __init__(self, data=b""):
        self.buffer = io.BytesIO(data)


def test_main_defaults_to_the_process_arguments_and_streams(monkeypatch):
    stdout, stderr = Standard(), Standard()
    monkeypatch.setattr(sys, "argv", ["python -m hilclaw.mcp_front"])
    monkeypatch.setattr(sys, "stdin", Standard(message("tools/list", 1)))
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    assert main() == 0
    (listed,) = responses(stdout.buffer.getvalue())
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert (listed["id"], names) == (
        1,
        [
            "blob_fetch",
            "blob_push",
            "correctness_check",
            "instance_read",
            "run_commit",
            "run_fresh",
            "state_read",
            "state_write",
            "verdicts_write",
        ],
    )
    assert stderr.buffer.getvalue() == b""
    monkeypatch.setattr(sys, "argv", ["python -m hilclaw.mcp_front", "sim_run"])
    assert main() == 4
    assert stderr.buffer.getvalue() == (
        b"hilclaw.mcp_front: expected no argument, got 1\n"
    )


@pytest.mark.parametrize("stream", [None, io.StringIO("{}")])
def test_a_closed_standard_input_is_status_4(monkeypatch, stream):
    monkeypatch.setattr(sys, "stdin", stream)
    stdout, stderr = io.BytesIO(), io.BytesIO()
    assert main([], stdout=stdout, stderr=stderr) == 4
    assert stdout.getvalue() == b""
    assert stderr.getvalue() == (
        b"hilclaw.mcp_front: cannot read standard input: it is closed\n"
    )


@pytest.mark.parametrize("stream", [None, io.StringIO()])
def test_a_closed_standard_output_is_status_4_when_an_answer_is_due(
    monkeypatch, stream
):
    monkeypatch.setattr(sys, "stdout", stream)
    stderr = io.BytesIO()
    data = message("notifications/initialized")
    assert main([], stdin=io.BytesIO(data), stderr=stderr) == 0
    assert stderr.getvalue() == b""
    data += message("ping", 1)
    assert main([], stdin=io.BytesIO(data), stderr=stderr) == 4
    assert stderr.getvalue() == (
        b"hilclaw.mcp_front: cannot write standard output: it is closed\n"
    )


@pytest.mark.parametrize("stream", [None, io.StringIO()])
def test_a_closed_standard_error_loses_no_answer(monkeypatch, stream):
    monkeypatch.setattr(sys, "stderr", stream)
    stdout = io.BytesIO()
    assert main([], stdin=io.BytesIO(message("ping", 1)), stdout=stdout) == 0
    assert stdout.getvalue() == b'{"jsonrpc":"2.0","id":1,"result":{}}\n'
    assert main(["x"], stdin=io.BytesIO(b""), stdout=stdout) == 4
    assert main([], stdin=closed(), stdout=stdout) == 4


# Through a real process


def run_module(data, args=()):
    return subprocess.run(
        [sys.executable, "-m", "hilclaw.mcp_front", *args],
        input=data,
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )


def helper(tmp_path):
    script = tmp_path / "mcp_front_with_test_tools.py"
    text = HELPER_SCRIPT.format(
        root=str(REPO_ROOT), description=NON_ASCII_DESCRIPTION, schema=NESTED_SCHEMA
    )
    script.write_text(text, encoding="utf-8")
    return [sys.executable, str(script)]


def test_process_handshake_and_tool_list():
    data = (
        message("initialize", 1, INITIALIZE)
        + message("notifications/initialized")
        + message("tools/list", 2)
    )
    done = run_module(data)
    assert done.returncode == 0
    first, second = done.stdout.splitlines(keepends=True)
    assert first == (
        b'{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-06-18",'
        b'"capabilities":{"tools":{}},"serverInfo":{"name":"hilclaw","version":"'
        + __version__.encode()
        + b'"}}}\n'
    )
    (listed,) = responses(second)
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert (listed["id"], names) == (
        2,
        [
            "blob_fetch",
            "blob_push",
            "correctness_check",
            "instance_read",
            "run_commit",
            "run_fresh",
            "state_read",
            "state_write",
            "verdicts_write",
        ],
    )
    assert done.stderr == b""


def test_process_malformed_line_and_unknown_tool():
    done = run_module(b"{\r\n" + call(1, "sim_run", {}) + message("ping", "p"))
    assert done.returncode == 0
    assert b"\r" not in done.stdout and done.stdout.endswith(b"\n")
    parse_error, refused, pinged = responses(done.stdout)
    error_of(parse_error, -32700, None)
    assert error_of(refused, -32602, 1) == "unknown tool 'sim_run'"
    assert pinged == {"jsonrpc": "2.0", "id": "p", "result": {}}
    assert done.stderr == b""


def test_process_argument_is_refused():
    done = run_module(message("ping", 1), ["sim_run"])
    assert done.returncode == 4
    assert done.stdout == b""
    assert done.stderr.strip() == b"hilclaw.mcp_front: expected no argument, got 1"


def test_process_call_is_exact_bytes_with_lf(tmp_path):
    data = message("tools/list", 1) + call(2, "test_echo", NON_ASCII)
    done = subprocess.run(
        helper(tmp_path),
        input=data.replace(b"\n", b"\r\n"),
        capture_output=True,
        cwd=tmp_path,
        timeout=60,
        check=False,
    )
    assert done.returncode == 0
    text = json.dumps({"echo": NON_ASCII}, ensure_ascii=True, separators=(",", ":"))
    called = {
        "jsonrpc": "2.0",
        "id": 2,
        "result": {"content": [{"type": "text", "text": text}], "isError": False},
    }
    tool = {
        "name": "test_echo",
        "description": NON_ASCII_DESCRIPTION,
        "inputSchema": NESTED_SCHEMA,
    }
    also = {"name": "test_also", "description": "Another tool.", "inputSchema": SCHEMA}
    listed = {"jsonrpc": "2.0", "id": 1, "result": {"tools": [also, tool]}}
    assert done.stdout == b"".join(
        json.dumps(answer, ensure_ascii=True, separators=(",", ":")).encode("ascii")
        + b"\n"
        for answer in (listed, called)
    )
    assert b'"description":"Echoes the request. h\\u00e9llo ' in done.stdout
    assert (
        b'"inputSchema":{"type":"object","properties":{"example_list":' in done.stdout
    )
    assert b"\r" not in done.stdout
    assert done.stderr == b""


def test_process_answers_each_request_before_the_next_is_sent(tmp_path):
    server = subprocess.Popen(
        helper(tmp_path),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=tmp_path,
    )
    lines = queue.Queue()

    def read():
        for line in server.stdout:
            lines.put(line)

    reader = threading.Thread(target=read, daemon=True)
    reader.start()
    try:
        for i in range(3):
            server.stdin.write(call(i, "test_echo", {"i": i}))
            server.stdin.flush()
            (document,) = responses(lines.get(timeout=60))
            assert document["id"] == i
            assert outcome_of(document) == {"echo": {"i": i}}
            assert server.poll() is None
        server.stdin.close()
        assert server.wait(timeout=60) == 0
        reader.join(timeout=60)
        assert lines.empty()
        assert server.stderr.read() == b""
    finally:
        server.kill()
        server.wait()
        server.stdout.close()
        server.stderr.close()
