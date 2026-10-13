"""The wire copy of the runtime self-check, read as named facts (ADR-0054 decisions 6 and 7).

Renders, of decision 6, the rows of "what is read from where" that are read
from the wire copy, condition (a) and the wire half of condition (b) of
``front_refused`` and the wire conditions of ``passed``; of decision 7, the
wire-side members and "Strings the client supplied are bounded".

:func:`read` takes the ``lines`` of a :class:`hilclaw.selfcheck_server.WireCopy`
and returns one :class:`WireFacts`. It is pure: the same lines give the same
value, and it reads no file, environment, clock or configuration, starts no
process, keeps no state and prints nothing.

**The members.** "Request" and "answer" are defined below; a count is over the
whole copy unless a member says otherwise.

- ``reached``: the copy holds an ``initialize`` request. ``client_version``,
  ``revision_asked``: ``params.clientInfo.version`` and
  ``params.protocolVersion`` of the first one. ``initialize_answered``: that
  first request was answered with a result; ``revision_answered``: the
  ``protocolVersion`` of that result.
- ``probe_seen``: the copy holds a ``server/discover`` request. Of the first
  one: ``probe_before_initialize`` (no ``initialize`` request stands before
  it), ``probe_revision`` and ``probe_error``, the code of the error answered
  to it (``None`` when no error was copied). No probe is no fault.
- ``list_requested``: a ``tools/list`` request; ``list_after_initialize``: one
  that stands after the first ``initialize`` request; ``list_answered``: one
  answered with a result whose ``tools`` is an array; ``list_both_tools``: in
  such an array both :data:`TOKEN_TOOL_NAME` and :data:`FAIL_TOOL_NAME` occur
  as the ``name`` of an object, whatever else it lists.
- ``token_call_requested``, ``fail_call_requested``: a ``tools/call`` request
  whose ``params.name`` is that tool. ``token_call_answered``: at least one
  such call was answered with a result whose ``isError`` is the JSON ``false``;
  ``fail_call_answered``: ``true``. Nothing of ``content`` is read.
- ``errors``: the errors condition (a) names, in the order of the copy, each
  as ``(code, method)``: every error answer except a -32601. ``method`` is one
  of :data:`SERVED_METHODS` when the error answered a request of it, else
  ``None`` (a line the front could not read as a message). At most
  :data:`MAX_LISTED` are kept, the first ones; ``errors_dropped`` says that
  there were more.
- ``unforeseen``: the distinct method names outside :data:`FORESEEN_METHODS`,
  bounded, in the order first seen, of every client line that is one JSON
  object with a string ``method`` - a notification as well as a request. At
  most :data:`MAX_LISTED` are kept; ``unforeseen_dropped`` says that a further
  one was seen. An unforeseen method changes no other member.
- ``unplaceable``: the copy holds a line the front could not have written
  where it stands (below).

**How a client line is read**: as the front reads it,
:func:`hilclaw.tools.decode_request`. A line is a *request* of a method when
it is one JSON object with a string ``method`` and an ``id`` member - the
lines the front always answers. Any other line (blank, not JSON, a
notification, a response) is a request of nothing; its unreadable members
establish nothing. ``params`` and the members named above are read only when
they are objects; a missing or mistyped one is absent, never an error.

**Pairing is by position**: a server line answers the client line that stands
immediately before it. The front reads one line, writes at most one line and
only then reads the next, a client line is copied before the front gets it
and a server line after it was sent, so no other order can stand in a copy the
entry wrote. The ``id`` is not used: the client supplies it and may repeat it.
A request with no server line after it is not answered - also the last one of
a copy whose last answer was sent and not copied.

**How a server line is read**: it is an *answer* when it follows a client
line directly, is one JSON object with exactly one of ``result`` and ``error``
and is what the front can write to that line. To a request with
``"jsonrpc": "2.0"`` and a string or integer ``id``: a ``result`` object or
-32602 for a served method (-32602 alone when ``params`` is no object) and
-32601 for another method. -32600 or -32700 to a line that is not JSON text
of one object; -32600 to any other object the front refuses as a message;
nothing to a blank line, a notification or a response.
Every other server line, and a line whose direction is neither constant of
:mod:`hilclaw.selfcheck_server`, is **unplaceable**: it sets ``unplaceable``,
is never an answer and never an error of condition (a), and the client line
before it stays unanswered. Hence an error code outside the four of
:mod:`hilclaw.mcp_front` never leaves the module.

**Bounded strings.** The version, the three revisions and a method name leave
the module only when they are 1 to :data:`MAX_STRING` characters of ASCII
letters, digits, ``.``, ``_`` and ``-`` (a method name also ``/``); any other
string, the empty one included, is :data:`OTHER`, and a value that is absent
or no string is ``None``. The record names the version and the method name;
the revisions are the client's too. A client's own ``other`` reads the same.

**The revision of the probe** is read from
``params._meta["io.modelcontextprotocol/protocolVersion"]`` and nowhere else.
That place was observed once (K15, T-0106) and is on no page.

**What leaves the module**: booleans, the bounded strings, names of
:data:`SERVED_METHODS` and the four error codes. No line or fragment of one,
no error ``message``, no ``content``, no ``id`` and no ``clientInfo.name`` is in
the value or in an exception. :func:`read` raises :class:`TypeError`, with a
fixed text, for an argument of another form and never for the bytes of a line.

Not done here: no file, no process, no ``claude``, no token, no session-side
or model-side evidence, no word for how a check ended, no report. ``torn`` of
the wire copy and the errors of its reader are not this module's.

Known limits. Whoever can write the wire copy decides what is read (ADR-0054
L6). The facts say what the front wrote, not what the model was given. A -32602
answered to a call of an unknown tool is among ``errors``, as the record is
written. A client line is read again here, in another process than the
front's: a line nested within a few levels of the interpreter's limit, or an
integer near its digit limit, can read differently, and the answer the front
wrote is then unplaceable. Nothing calls the module yet.
"""

import re
from typing import NamedTuple

from hilclaw import mcp_front, selfcheck_server, tools

OTHER = "other"
MAX_STRING = 64
MAX_LISTED = 16
SERVED_METHODS = ("initialize", "ping", "tools/list", "tools/call")
FORESEEN_METHODS = (
    "server/discover",
    "initialize",
    "notifications/initialized",
    "ping",
    "tools/list",
    "tools/call",
)
TOKEN_TOOL_NAME = mcp_front.mcp_name(selfcheck_server.TOKEN_TOOL)
FAIL_TOOL_NAME = mcp_front.mcp_name(selfcheck_server.FAIL_TOOL)

_PROBE = "server/discover"
_PROBE_REVISION = "io.modelcontextprotocol/protocolVersion"
_WORD = re.compile(rf"[A-Za-z0-9._-]{{1,{MAX_STRING}}}")
_METHOD = re.compile(rf"[A-Za-z0-9._/-]{{1,{MAX_STRING}}}")
_UNREAD = (mcp_front.PARSE_ERROR, mcp_front.INVALID_REQUEST)
_CALLS = ((TOKEN_TOOL_NAME, False, "token"), (FAIL_TOOL_NAME, True, "fail"))


class WireFacts(NamedTuple):
    """What :func:`read` found; the module docstring says what each member means.

    Every member is immutable: ``errors`` is a tuple of ``(int, str | None)``
    pairs and ``unforeseen`` a tuple of ``str``.
    """

    reached: bool = False
    client_version: str | None = None
    revision_asked: str | None = None
    initialize_answered: bool = False
    revision_answered: str | None = None
    probe_seen: bool = False
    probe_before_initialize: bool = False
    probe_revision: str | None = None
    probe_error: int | None = None
    list_requested: bool = False
    list_after_initialize: bool = False
    list_answered: bool = False
    list_both_tools: bool = False
    token_call_requested: bool = False
    token_call_answered: bool = False
    fail_call_requested: bool = False
    fail_call_answered: bool = False
    errors: tuple = ()
    errors_dropped: bool = False
    unforeseen: tuple = ()
    unforeseen_dropped: bool = False
    unplaceable: bool = False


def _bounded(value, form):
    if type(value) is not str:
        return None
    return value if form.fullmatch(value) else OTHER


def _object(value):
    return value if type(value) is dict else {}


def _keep(found, name, value):
    if len(found[name]) < MAX_LISTED:
        found[name].append(value)
    else:
        found[name + "_dropped"] = True


def _client(found, line):
    if not line.strip():
        return None, (), False, {}
    try:
        message = tools.decode_request(line)
    except tools.InvalidRequestError:
        return None, _UNREAD, False, {}
    method, params = message.get("method"), message.get("params", {})
    named = type(method) is str
    codes, may_result = (mcp_front.INVALID_REQUEST,), False
    if message.get("jsonrpc") == "2.0":
        if not named:
            if "method" not in message and ("result" in message or "error" in message):
                codes = ()
        elif "id" not in message:
            codes = ()
        elif type(message["id"]) in (str, int):
            if method in SERVED_METHODS:
                codes, may_result = (mcp_front.INVALID_PARAMS,), type(params) is dict
            else:
                codes = (mcp_front.METHOD_NOT_FOUND,)
    if named and method not in FORESEEN_METHODS:
        name = _bounded(method, _METHOD)
        if name not in found["unforeseen"]:
            _keep(found, "unforeseen", name)
    asked = method if named and "id" in message else None
    return asked, codes, may_result, _object(params)


def _answer(line, codes, may_result):
    try:
        message = tools.decode_request(line)
    except tools.InvalidRequestError:
        return None
    if ("result" in message) == ("error" in message):
        return None
    if "result" in message:
        return (
            message["result"]
            if may_result and type(message["result"]) is dict
            else None
        )
    code = _object(message["error"]).get("code")
    return code if type(code) is int and code in codes else None


def _settle(found, method, params, answer):
    if type(answer) is int and answer != mcp_front.METHOD_NOT_FOUND:
        _keep(found, "errors", (answer, method if method in SERVED_METHODS else None))
    result = _object(answer)
    if method == _PROBE and not found["probe_seen"]:
        found["probe_seen"] = True
        found["probe_before_initialize"] = not found["reached"]
        revision = _object(params.get("_meta")).get(_PROBE_REVISION)
        found["probe_revision"] = _bounded(revision, _WORD)
        found["probe_error"] = answer if type(answer) is int else None
    elif method == "initialize" and not found["reached"]:
        found["reached"] = True
        version = _object(params.get("clientInfo")).get("version")
        found["client_version"] = _bounded(version, _WORD)
        found["revision_asked"] = _bounded(params.get("protocolVersion"), _WORD)
        found["initialize_answered"] = type(answer) is dict
        found["revision_answered"] = _bounded(result.get("protocolVersion"), _WORD)
    elif method == "tools/list":
        found["list_requested"] = True
        found["list_after_initialize"] |= found["reached"]
        listed = result.get("tools")
        if type(listed) is list:
            names = [tool.get("name") for tool in listed if type(tool) is dict]
            found["list_answered"] = True
            found["list_both_tools"] |= (
                TOKEN_TOOL_NAME in names and FAIL_TOOL_NAME in names
            )
    elif method == "tools/call":
        for tool, failed, member in _CALLS:
            if params.get("name") == tool:
                found[member + "_call_requested"] = True
                found[member + "_call_answered"] |= result.get("isError") is failed


def read(lines):
    """Return the :class:`WireFacts` of the copied ``lines``.

    ``lines`` is a tuple or a list of ``(direction, line)`` pairs as
    :func:`hilclaw.selfcheck_server.read_wire_copy` returns them in ``lines``:
    the line is ``bytes``, the direction one of the two constants of that
    module (any other value makes the line unplaceable). An empty ``lines``
    gives ``WireFacts()``. Raises :class:`TypeError` when ``lines`` or one of
    its items has another form; the message holds nothing of the content. The
    bytes of a line never raise.
    """
    if type(lines) not in (tuple, list):
        raise TypeError("the lines must be a tuple or a list")
    found = WireFacts(errors=[], unforeseen=[])._asdict()
    waiting = None
    for item in lines:
        if type(item) not in (tuple, list) or len(item) != 2:
            raise TypeError("a copied line must be a pair of a direction and a line")
        direction, line = item
        if type(line) is not bytes:
            raise TypeError("a copied line must be bytes")
        direction = direction if type(direction) is str else None
        from_client = direction == selfcheck_server.FROM_CLIENT
        answer = None
        if not from_client:
            if waiting is not None and direction == selfcheck_server.FROM_SERVER:
                answer = _answer(line, *waiting[1:3])
            found["unplaceable"] |= answer is None
        if waiting is not None:
            _settle(found, waiting[0], waiting[3], answer)
        waiting = _client(found, line) if from_client else None
    if waiting is not None:
        _settle(found, waiting[0], waiting[3], None)
    found["errors"], found["unforeseen"] = (
        tuple(found["errors"]),
        tuple(found["unforeseen"]),
    )
    return WireFacts(**found)
