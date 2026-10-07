"""MCP front of the tool registry: a stdio server (ADR-0010 decision 4).

Command line: ``python -m hilclaw.mcp_front``, without arguments. The server
reads JSON-RPC 2.0 messages from standard input, one per line in UTF-8, and
writes each response to standard output as one line of ASCII JSON text ended
by one LF, flushed when it is written. It serves until the end of standard
input. Standard output gets nothing but responses; standard error gets one
line of free text when the server gives up.

Methods: ``initialize``, ``ping``, ``tools/list`` and ``tools/call``. The
server is named ``hilclaw`` and a tool is listed and called by its registry
name with each ``.`` replaced by ``_``. The request of a call is the
``arguments`` object (``{}`` when absent). The answer of a call that reached a
tool function is one text block: the result as JSON text with ``isError``
false, or ``{"error": {"kind": ..., "message": ...}}`` with ``isError`` true
for a tool failure, in the characters the command-line front writes.

What reaches no tool function is a JSON-RPC error: -32700 for a line that is
not JSON or is nested too deeply to read, -32600 for JSON that is not a
message (also a member name given twice anywhere in it, an ``id`` that is not
a string or an integer), -32601 for an unknown method, -32602 for ``params``
that is not an object, an unknown tool and ``arguments`` that is not an
object. The ``id`` of an error is ``null`` when the message gave no usable
one. A notification, a response and a blank line get no answer.

The server keeps no state: every request is served alike before and after
``initialize``. Messages are handled one at a time in the order read, so
standard input must be a blocking stream. Exit status 0 is the end of
standard input; 4 means an argument was given or a standard stream is closed
or failed when it was needed.
"""

import contextlib
import json
import sys

from hilclaw import __version__, tools

SERVER_NAME = "hilclaw"
PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
EXIT_END_OF_INPUT = 0
EXIT_FRONT_FAILURE = 4
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602


class _Refused(Exception):
    def __init__(self, code, text):
        super().__init__(code, text)
        self.code = code
        self.text = text


def mcp_name(name):
    """Return the MCP name of the tool with the registry name ``name`` (``sim.run`` → ``sim_run``)."""
    return name.replace(".", "_")


def mcp_names(registry):
    """Return the table from MCP name to registry name for every tool of ``registry``."""
    return {mcp_name(name): name for name in registry.names()}


def _initialize(registry, params):
    asked = params.get("protocolVersion")
    version = asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0]
    return {
        "protocolVersion": version,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": __version__},
    }


def _ping(registry, params):
    return {}


def _list(registry, params):
    names = mcp_names(registry)
    return {"tools": [{"name": n, "inputSchema": {"type": "object"}} for n in names]}


def _call(registry, params):
    name = params.get("name")
    known = mcp_names(registry).get(name) if type(name) is str else None
    arguments = params.get("arguments", {})
    try:
        outcome, failed = tools.call(registry, known, arguments), False
    except tools.UnknownToolError:
        raise _Refused(INVALID_PARAMS, f"unknown tool {name!r}") from None
    except tools.InvalidRequestError as e:
        raise _Refused(INVALID_PARAMS, str(e)) from e
    except tools.ToolFailure as e:
        outcome, failed = e.error_object(), True
    text = tools.encode(outcome)[:-1].decode("ascii")
    return {"content": [{"type": "text", "text": text}], "isError": failed}


_METHODS = {
    "initialize": _initialize,
    "ping": _ping,
    "tools/list": _list,
    "tools/call": _call,
}


def _result(registry, message, usable_id):
    if message.get("jsonrpc") != "2.0":
        raise _Refused(INVALID_REQUEST, 'the member "jsonrpc" must be "2.0"')
    if "method" not in message and ("result" in message or "error" in message):
        return None
    method = message.get("method")
    if type(method) is not str:
        raise _Refused(INVALID_REQUEST, "the method must be a string")
    if "id" not in message:
        return None
    if not usable_id:
        raise _Refused(INVALID_REQUEST, "the id must be a string or an integer")
    if method not in _METHODS:
        raise _Refused(METHOD_NOT_FOUND, f"unknown method {method!r}")
    params = message.get("params", {})
    if type(params) is not dict:
        raise _Refused(INVALID_PARAMS, "the params must be an object")
    return _METHODS[method](registry, params)


def _is_json(line):
    def refuse(constant):
        raise ValueError(constant)

    try:
        json.loads(line.decode("utf-8"), parse_constant=refuse)
    except (ValueError, RecursionError):
        return False
    return True


def _answer(registry, line):
    if not line.strip():
        return None
    try:
        message = tools.decode_request(line)
    except tools.InvalidRequestError as e:
        code = INVALID_REQUEST if _is_json(line) else PARSE_ERROR
        reason = e.__cause__ or "nested too deeply"
        return _error(None, code, f"not a message: {reason}")
    request_id = message.get("id")
    if type(request_id) not in (str, int):
        request_id = None
    try:
        result = _result(registry, message, request_id is not None)
    except _Refused as e:
        return _error(request_id, e.code, e.text)
    if result is None:
        return None
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code, text):
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": text},
    }


def _standard(name):
    return getattr(getattr(sys, name), "buffer", None)


def _give_up(stderr, text):
    with contextlib.suppress(OSError, ValueError):
        if stderr is not None:
            stderr.write(
                f"hilclaw.mcp_front: {text}\n".encode("utf-8", "backslashreplace")
            )
            stderr.flush()
    return EXIT_FRONT_FAILURE


def main(argv=None, *, registry=None, stdin=None, stdout=None, stderr=None):
    """Serve the registry over standard input and output and return the exit status (0 or 4).

    ``argv`` defaults to ``sys.argv[1:]`` and must be empty; ``registry``
    defaults to :func:`hilclaw.tools.default_registry`. ``stdin``, ``stdout``
    and ``stderr`` are binary streams and default to the standard ones; a
    standard stream that is closed or has no binary layer counts as closed.
    A ``KeyboardInterrupt`` or ``SystemExit`` of a tool function is not caught.
    """
    args = sys.argv[1:] if argv is None else list(argv)
    registry = tools.default_registry() if registry is None else registry
    stdin = _standard("stdin") if stdin is None else stdin
    stdout = _standard("stdout") if stdout is None else stdout
    stderr = _standard("stderr") if stderr is None else stderr
    if args:
        return _give_up(stderr, f"expected no argument, got {len(args)}")
    while True:
        try:
            if stdin is None:
                raise OSError("it is closed")
            line = stdin.readline()
        except (OSError, ValueError) as e:
            return _give_up(stderr, f"cannot read standard input: {e}")
        if not line:
            return EXIT_END_OF_INPUT
        answer = _answer(registry, line)
        if answer is None:
            continue
        data = tools.encode(answer)
        try:
            if stdout is None:
                raise OSError("it is closed")
            stdout.write(data)
            stdout.flush()
        except (OSError, ValueError) as e:
            return _give_up(stderr, f"cannot write standard output: {e}")


if __name__ == "__main__":
    raise SystemExit(main())
