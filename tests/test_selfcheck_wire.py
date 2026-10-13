import io
import itertools
import json
import subprocess

import pytest

from hilclaw import mcp_front, selfcheck_server, selfcheck_wire
from hilclaw.selfcheck_server import FROM_CLIENT, FROM_SERVER
from hilclaw.selfcheck_wire import (
    FAIL_TOOL_NAME,
    FORESEEN_METHODS,
    MAX_LISTED,
    MAX_STRING,
    OTHER,
    SERVED_METHODS,
    TOKEN_TOOL_NAME,
    WireFacts,
    read,
)

TOKEN = "0123456789abcdef0123456789abcdef"
FAIL_TOKEN = "fedcba9876543210fedcba9876543210"
MARKER = "marker-3f9c"
PROBE_MEMBER = "io.modelcontextprotocol/protocolVersion"
COUNTER = itertools.count()
OUTCOME_WORDS = (
    "no_claude",
    "not_logged_in",
    "login_unreadable",
    "front_refused",
    "passed",
    "no_call",
    "session_failed",
)
TYPE_ERROR_TEXTS = (
    "the lines must be a tuple or a list",
    "a copied line must be a pair of a direction and a line",
    "a copied line must be bytes",
)


def message(**members):
    return json.dumps({"jsonrpc": "2.0", **members}).encode() + b"\n"


def request(request_id, method, params=None):
    members = {"id": request_id, "method": method}
    if params is not None:
        members["params"] = params
    return message(**members)


def call(request_id, name, arguments=None):
    params = {"name": name}
    if arguments is not None:
        params["arguments"] = arguments
    return request(request_id, "tools/call", params)


def initialize(request_id=1, **params):
    return request(request_id, "initialize", params)


def client(line):
    return (FROM_CLIENT, line)


def server(line):
    return (FROM_SERVER, line)


def result(value, request_id=1):
    return server(message(id=request_id, result=value))


def error(code, request_id=1):
    return server(message(id=request_id, error={"code": code, "message": MARKER}))


PROBE = request(
    "server-discover-probe-1",
    "server/discover",
    {"_meta": {PROBE_MEMBER: "2026-07-28", "clientInfo": {"name": MARKER}}},
)
INITIALIZE = initialize(
    protocolVersion="2025-11-25",
    capabilities={},
    clientInfo={"name": MARKER, "title": MARKER, "version": "2.1.280"},
)
INITIALIZED = message(method="notifications/initialized")
LIST = request(2, "tools/list")
CALL_TOKEN = call(3, TOKEN_TOOL_NAME)
CALL_FAIL = call(4, FAIL_TOOL_NAME)
PING = request(5, "ping")
EXCHANGE = (PROBE, INITIALIZE, INITIALIZED, LIST, CALL_TOKEN, CALL_FAIL)
PASS = WireFacts(
    reached=True,
    client_version="2.1.280",
    revision_asked="2025-11-25",
    initialize_answered=True,
    revision_answered="2025-06-18",
    probe_seen=True,
    probe_before_initialize=True,
    probe_revision="2026-07-28",
    probe_error=-32601,
    list_requested=True,
    list_after_initialize=True,
    list_answered=True,
    list_both_tools=True,
    token_call_requested=True,
    token_call_answered=True,
    fail_call_requested=True,
    fail_call_answered=True,
)
NO_PROBE = PASS._replace(
    probe_seen=False,
    probe_before_initialize=False,
    probe_revision=None,
    probe_error=None,
)
NOT_STRINGS = [7, 1.5, {"a": "b"}, ["2.1"], True, None]
NOT_WORDS = [
    "a" * (MAX_STRING + 1),
    "2.1 280",
    "2.1/280",
    "2.1\\280",
    "2.1é",
    "한",
    "2.1\n",
    "\n2.1",
    "2.1\x00",
    "",
    "a" * 1_000_000,
]
WORDS = ["a" * MAX_STRING, "A-z_0.9", "0", "other"]
STRING_MEMBERS = [
    "client_version",
    "revision_asked",
    "revision_answered",
    "probe_revision",
]


def label(value):
    return ascii(value)[:24]


def copy_of(tmp_path, lines):
    place = tmp_path / f"wire-copy-{next(COUNTER)}"
    status = selfcheck_server.main(
        [],
        environ={
            selfcheck_server.ENV_TOKEN: TOKEN,
            selfcheck_server.ENV_FAIL_TOKEN: FAIL_TOKEN,
            selfcheck_server.ENV_WIRE_COPY: str(place),
        },
        stdin=io.BytesIO(b"".join(lines)),
        stdout=io.BytesIO(),
        stderr=io.BytesIO(),
    )
    assert status == 0
    copy = selfcheck_server.read_wire_copy(place)
    assert copy.torn is False
    return copy.lines


def served(tmp_path, *lines):
    """The facts of what the real front answered to ``lines``."""
    facts = read(copy_of(tmp_path, lines))
    assert facts.unplaceable is False
    return facts


def carried(member, value):
    """What the module gives for a client-supplied ``value`` of ``member``."""
    if member == "client_version":
        lines = [client(initialize(clientInfo={"version": value}))]
    elif member == "revision_asked":
        lines = [client(initialize(protocolVersion=value))]
    elif member == "revision_answered":
        lines = [client(initialize()), result({"protocolVersion": value})]
    else:
        lines = [
            client(request(1, "server/discover", {"_meta": {PROBE_MEMBER: value}}))
        ]
    return getattr(read(lines), member)


def test_the_exchange_of_a_pass_gives_every_fact(tmp_path):
    lines = copy_of(tmp_path, EXCHANGE)
    assert len(lines) == 11
    facts = read(lines)
    assert facts == PASS
    assert facts.errors == () and facts.unforeseen == ()
    assert (facts.errors_dropped, facts.unforeseen_dropped) == (False, False)
    assert facts.unplaceable is False


def test_an_empty_copy_gives_the_all_absent_value():
    assert read(()) == read([]) == WireFacts()
    assert WireFacts() == WireFacts(
        *(False, None, None, False, None, False, False, None, None),
        *(False, False, False, False, False, False, False, False),
        *((), False, (), False, False),
    )


def test_the_constants():
    assert OTHER == "other"
    assert (MAX_STRING, MAX_LISTED) == (64, 16)
    assert SERVED_METHODS == tuple(mcp_front._METHODS)
    assert FORESEEN_METHODS == (
        "server/discover",
        "initialize",
        "notifications/initialized",
        "ping",
        "tools/list",
        "tools/call",
    )
    assert set(SERVED_METHODS) < set(FORESEEN_METHODS)
    assert (TOKEN_TOOL_NAME, FAIL_TOOL_NAME) == ("selfcheck_token", "selfcheck_fail")


def test_the_tool_names_are_those_the_front_lists(tmp_path):
    listing = json.loads(copy_of(tmp_path, [LIST])[1][1])
    listed = sorted(tool["name"] for tool in listing["result"]["tools"])
    assert listed == sorted([TOKEN_TOOL_NAME, FAIL_TOOL_NAME])


def test_no_outcome_word_is_in_the_module():
    names = [name.lower() for name in dir(selfcheck_wire) + list(WireFacts._fields)]
    for word in OUTCOME_WORDS:
        assert not any(word in name for name in names)
        assert word not in repr(PASS)


def test_no_probe_is_no_fault(tmp_path):
    assert served(tmp_path, *EXCHANGE[1:]) == NO_PROBE


def test_a_probe_after_initialize(tmp_path):
    facts = served(tmp_path, INITIALIZE, PROBE, LIST, CALL_TOKEN, CALL_FAIL)
    assert facts == PASS._replace(probe_before_initialize=False)


def test_only_the_first_probe_is_read(tmp_path):
    second = request(9, "server/discover", {"_meta": {PROBE_MEMBER: "1999-01-01"}})
    assert served(tmp_path, PROBE, second, *EXCHANGE[1:]) == PASS
    facts = served(tmp_path, second, INITIALIZE, PROBE)
    assert (facts.probe_revision, facts.probe_before_initialize) == ("1999-01-01", True)


@pytest.mark.parametrize(
    "params",
    [None, {}, {"_meta": {}}, {"_meta": "2026-07-28"}, {PROBE_MEMBER: "2026-07-28"}]
    + [{"_meta": {PROBE_MEMBER: value}} for value in NOT_STRINGS],
)
def test_a_probe_that_names_no_revision_where_it_was_observed(tmp_path, params):
    probe = request(1, "server/discover", params)
    facts = served(tmp_path, probe, *EXCHANGE[1:])
    assert facts == PASS._replace(probe_revision=None)


def test_a_probe_that_was_not_answered():
    facts = read([client(PROBE)])
    assert facts == WireFacts(
        probe_seen=True, probe_before_initialize=True, probe_revision="2026-07-28"
    )


@pytest.mark.parametrize(
    "line",
    [
        request(1, "initialize"),
        initialize(),
        initialize(clientInfo="2.1.280"),
        initialize(clientInfo=["2.1.280"]),
        initialize(clientInfo={"name": MARKER}),
        initialize(clientInfo=None, protocolVersion=None),
    ],
)
def test_an_initialize_without_the_members_read(tmp_path, line):
    assert served(tmp_path, line) == WireFacts(
        reached=True, initialize_answered=True, revision_answered="2025-06-18"
    )


def test_the_first_of_two_initialize_requests_is_read(tmp_path):
    second = initialize(9, protocolVersion="1999-01-01", clientInfo={"version": "9"})
    assert served(tmp_path, *EXCHANGE, second) == PASS
    facts = served(tmp_path, second, INITIALIZE)
    assert (facts.client_version, facts.revision_asked) == ("9", "1999-01-01")


def test_an_initialize_that_was_not_answered():
    facts = read([client(INITIALIZE)])
    assert facts == WireFacts(
        reached=True, client_version="2.1.280", revision_asked="2025-11-25"
    )
    late = read([client(INITIALIZE), client(initialize(2)), result({}, 2)])
    assert late == facts


def test_initialize_answered_and_no_list_after_it(tmp_path):
    facts = served(tmp_path, PROBE, INITIALIZE, INITIALIZED)
    assert facts.initialize_answered and not facts.list_after_initialize
    assert not facts.list_requested and not facts.list_answered


def test_a_list_that_stands_only_before_initialize(tmp_path):
    facts = served(tmp_path, LIST, INITIALIZE)
    assert facts.initialize_answered and not facts.list_after_initialize
    assert facts.list_requested and facts.list_answered and facts.list_both_tools
    after = served(tmp_path, LIST, INITIALIZE, LIST)
    assert after == facts._replace(list_after_initialize=True)


def test_a_list_after_an_initialize_that_was_refused(tmp_path):
    facts = served(tmp_path, request(1, "initialize", [1]), LIST)
    assert facts.reached and not facts.initialize_answered
    assert facts.list_after_initialize and facts.list_answered
    assert facts.errors == ((-32602, "initialize"),)


def test_a_request_the_copy_ends_after_is_not_answered(tmp_path):
    lines = copy_of(tmp_path, EXCHANGE)
    assert read(lines[:-1]) == PASS._replace(fail_call_answered=False)
    assert read(lines[:-3]) == PASS._replace(
        token_call_answered=False, fail_call_requested=False, fail_call_answered=False
    )
    unlisted = read(lines[:6])
    assert unlisted.list_requested and unlisted.list_after_initialize
    assert not unlisted.list_answered and not unlisted.list_both_tools


def test_only_one_tool_called(tmp_path):
    assert served(tmp_path, *EXCHANGE[:5]) == PASS._replace(
        fail_call_requested=False, fail_call_answered=False
    )
    assert served(tmp_path, *EXCHANGE[:4], CALL_FAIL) == PASS._replace(
        token_call_requested=False, token_call_answered=False
    )


def test_calls_given_twice_and_with_arguments(tmp_path):
    again = call(7, TOKEN_TOOL_NAME, {"stray": MARKER})
    assert served(tmp_path, *EXCHANGE, again, CALL_FAIL, again) == PASS


def test_one_answered_call_among_unanswered_ones(tmp_path):
    lines = copy_of(tmp_path, [CALL_TOKEN]) + (client(CALL_TOKEN), client(CALL_FAIL))
    facts = read(lines)
    assert facts.token_call_requested and facts.token_call_answered
    assert facts.fail_call_requested and not facts.fail_call_answered


def test_a_ping_changes_nothing(tmp_path):
    assert served(tmp_path, PING, *EXCHANGE[:3], PING, *EXCHANGE[3:], PING) == PASS


def test_unforeseen_methods_are_named_once_and_change_nothing_else(tmp_path):
    asked = request(8, "resources/list")
    told = message(method="notifications/cancelled", params={"reason": MARKER})
    facts = served(tmp_path, asked, *EXCHANGE, told, asked, told, PING)
    assert facts == PASS._replace(
        unforeseen=("resources/list", "notifications/cancelled")
    )
    assert facts.unforeseen_dropped is False


def test_a_foreseen_notification_is_not_unforeseen(tmp_path):
    facts = served(tmp_path, *(message(method=method) for method in FORESEEN_METHODS))
    assert facts == WireFacts()


@pytest.mark.parametrize(
    ("line", "kept"),
    [
        pytest.param(b"not json\n", (-32700, None), id="not JSON"),
        pytest.param(b"\xff\xfe\n", (-32700, None), id="not UTF-8"),
        pytest.param(b'{"id": 1, "method": NaN}\n', (-32700, None), id="NaN"),
        pytest.param(b"[1]\n", (-32600, None), id="an array"),
        pytest.param(b'"initialize"\n', (-32600, None), id="a string"),
        pytest.param(b'{"jsonrpc":"2.0","id":1,"id":2}\n', (-32600, None), id="twice"),
        pytest.param(message(id=1), (-32600, None), id="no method"),
        pytest.param(message(id=1, method=7), (-32600, None), id="method no string"),
        pytest.param(message(method=["ping"]), (-32600, None), id="notification of 7"),
        pytest.param(b'{"method":"ping"}\n', (-32600, None), id="no jsonrpc, no id"),
        pytest.param(
            message(id=None, method="resources/list"), (-32600, None), id="unserved"
        ),
        pytest.param(b'{"id":1,"method":"ping"}\n', (-32600, "ping"), id="no jsonrpc"),
        pytest.param(
            message(id=1.5, method="initialize"), (-32600, "initialize"), id="id 1.5"
        ),
        pytest.param(
            message(id=True, method="tools/list"), (-32600, "tools/list"), id="id true"
        ),
        pytest.param(
            message(id=None, method="tools/call"), (-32600, "tools/call"), id="id null"
        ),
        pytest.param(call(1, MARKER), (-32602, "tools/call"), id="unknown tool"),
        pytest.param(call(1, 7), (-32602, "tools/call"), id="tool name no string"),
        pytest.param(
            call(1, TOKEN_TOOL_NAME, [MARKER]), (-32602, "tools/call"), id="arguments"
        ),
        pytest.param(
            request(1, "tools/list", {"cursor": MARKER}),
            (-32602, "tools/list"),
            id="cursor",
        ),
    ]
    + [
        pytest.param(request(1, method, [MARKER]), (-32602, method), id=method)
        for method in SERVED_METHODS
    ],
)
def test_an_error_of_condition_a_is_kept(tmp_path, line, kept):
    facts = served(tmp_path, line)
    assert facts.errors == (kept,)
    assert facts.errors_dropped is False
    assert served(tmp_path, *EXCHANGE, line).errors == (kept,)


@pytest.mark.parametrize("method", ["server/discover", "resources/list", "", MARKER])
def test_method_not_found_for_an_unserved_method_is_no_error(tmp_path, method):
    lines = copy_of(tmp_path, [request(1, method), *EXCHANGE])
    assert json.loads(lines[1][1])["error"]["code"] == -32601
    assert read(lines).errors == ()


def test_errors_keep_the_order_of_the_copy(tmp_path):
    lines = [b"}\n", request(1, "ping", 7), PROBE, b"[]\n", call(2, MARKER), LIST]
    assert served(tmp_path, *lines).errors == (
        (-32700, None),
        (-32602, "ping"),
        (-32600, None),
        (-32602, "tools/call"),
    )


def test_errors_are_capped(tmp_path):
    lines = [b"}\n"] + [request(1, "ping", 7)] * (MAX_LISTED - 1)
    full = served(tmp_path, *lines)
    assert full.errors == ((-32700, None),) + ((-32602, "ping"),) * (MAX_LISTED - 1)
    assert full.errors_dropped is False
    over = served(tmp_path, *lines, b"[]\n", *EXCHANGE)
    assert over.errors == full.errors
    assert over == PASS._replace(errors=full.errors, errors_dropped=True)


@pytest.mark.parametrize("member", STRING_MEMBERS)
@pytest.mark.parametrize("value", WORDS, ids=label)
def test_a_short_word_is_carried(member, value):
    assert carried(member, value) == value


@pytest.mark.parametrize("member", STRING_MEMBERS)
@pytest.mark.parametrize("value", NOT_WORDS, ids=label)
def test_another_string_is_other(member, value):
    assert carried(member, value) == OTHER


@pytest.mark.parametrize("member", STRING_MEMBERS)
@pytest.mark.parametrize("value", NOT_STRINGS, ids=label)
def test_a_value_that_is_no_string_is_absent(member, value):
    assert carried(member, value) is None


@pytest.mark.parametrize(
    "method",
    ["a" * MAX_STRING, "resources/list", "a/b.c_d-9", "/", "other"],
    ids=label,
)
def test_a_short_method_name_is_carried(tmp_path, method):
    assert read([client(request(1, method))]).unforeseen == (method,)
    assert served(tmp_path, message(method=method)).unforeseen == (method,)


@pytest.mark.parametrize(
    "method",
    [name for name in NOT_WORDS if "/" not in name] + ["a/" * MAX_STRING],
    ids=label,
)
def test_another_method_name_is_other(tmp_path, method):
    assert read([client(request(1, method))]).unforeseen == (OTHER,)
    facts = served(tmp_path, request(1, method), *EXCHANGE, message(method=method))
    assert facts == PASS._replace(unforeseen=(OTHER,))


@pytest.mark.parametrize("method", NOT_STRINGS, ids=label)
def test_a_method_that_is_no_string_is_no_method(method):
    assert read([client(message(id=1, method=method))]) == WireFacts()


def test_unforeseen_methods_are_capped(tmp_path):
    names = [f"x/{number}" for number in range(MAX_LISTED + 4)]
    asked = [request(1, name) for name in names]
    full = served(tmp_path, *asked[:MAX_LISTED], *asked[:MAX_LISTED])
    assert full.unforeseen == tuple(names[:MAX_LISTED])
    assert full.unforeseen_dropped is False
    over = served(tmp_path, *asked, *EXCHANGE)
    assert over == PASS._replace(unforeseen=full.unforeseen, unforeseen_dropped=True)


def test_a_hostile_copy_gives_a_small_value(tmp_path):
    lines = [request(MARKER * 50, f"{'m' * 60}/{number}") for number in range(2000)]
    lines += [request(number, "ping", MARKER) for number in range(2000)]
    lines += [initialize(clientInfo={"version": "v" * 100_000})]
    facts = served(tmp_path, *lines)
    assert len(facts.unforeseen) == len(facts.errors) == MAX_LISTED
    assert facts.unforeseen_dropped and facts.errors_dropped
    assert facts.client_version == OTHER
    assert len(repr(facts)) < 3000


def test_nothing_of_the_client_or_of_a_token_is_in_the_value(tmp_path):
    lines = [
        *EXCHANGE,
        request(MARKER, MARKER + "x" * MAX_STRING),
        request(MARKER, "tools/call", {"name": MARKER, "arguments": {MARKER: MARKER}}),
        call(MARKER, TOKEN_TOOL_NAME, {"stray": MARKER}),
        message(method=MARKER + " " + MARKER, params={MARKER: MARKER}),
        MARKER.encode() + b"\n",
        message(id=MARKER, result=MARKER),
    ]
    copied = copy_of(tmp_path, lines)
    seen = b"".join(line for _, line in copied)
    assert TOKEN.encode() in seen and FAIL_TOKEN.encode() in seen
    assert seen.count(MARKER.encode()) > 10
    facts = read(copied)
    assert facts == PASS._replace(
        unforeseen=(OTHER,), errors=((-32602, "tools/call"), (-32700, None))
    )
    for secret in (MARKER, TOKEN, FAIL_TOKEN, "marker", "self-check", "unknown"):
        assert secret not in repr(facts)
        assert secret not in str(facts._asdict())


def test_a_server_line_first_is_unplaceable():
    assert read([result({})]) == WireFacts(unplaceable=True)
    assert read([error(-32700), client(INITIALIZE)]) == WireFacts(
        reached=True,
        client_version="2.1.280",
        revision_asked="2025-11-25",
        unplaceable=True,
    )


def test_a_second_server_line_is_unplaceable():
    lines = [client(INITIALIZE), result({"protocolVersion": "2025-06-18"})]
    answered = read(lines)
    assert answered.initialize_answered and not answered.unplaceable
    for second in (error(-32602), result({"protocolVersion": "1999-01-01"})):
        assert read([*lines, second]) == answered._replace(unplaceable=True)


ANSWERS_THE_FRONT_CANNOT_WRITE = [
    pytest.param(INITIALIZE, server(b"not json\n"), id="not JSON"),
    pytest.param(INITIALIZE, server(b""), id="empty"),
    pytest.param(INITIALIZE, server(b"\xff\n"), id="not UTF-8"),
    pytest.param(INITIALIZE, server(b"[" * 100_000), id="deep"),
    pytest.param(INITIALIZE, server(b'[{"result": {}}]\n'), id="an array"),
    pytest.param(INITIALIZE, server(message(id=1)), id="neither"),
    pytest.param(
        INITIALIZE,
        server(message(id=1, result={}, error={"code": -32602})),
        id="both",
    ),
    pytest.param(INITIALIZE, result([]), id="result an array"),
    pytest.param(INITIALIZE, result(None), id="result null"),
    pytest.param(INITIALIZE, result("2025-06-18"), id="result a string"),
    pytest.param(INITIALIZE, server(message(id=1, error=-32602)), id="error a number"),
    pytest.param(INITIALIZE, server(message(id=1, error={})), id="no code"),
    pytest.param(INITIALIZE, error("-32602"), id="code a string"),
    pytest.param(INITIALIZE, error(-32602.0), id="code a float"),
    pytest.param(INITIALIZE, error(True), id="code true"),
    pytest.param(INITIALIZE, error([-32602]), id="code an array"),
    pytest.param(INITIALIZE, error(-32000), id="code of none of the four"),
    pytest.param(INITIALIZE, error(0), id="code 0"),
    pytest.param(INITIALIZE, error(-32601), id="-32601 to a served method"),
    pytest.param(INITIALIZE, error(-32700), id="-32700 to a readable request"),
    pytest.param(INITIALIZE, error(-32600), id="-32600 to a served request"),
    pytest.param(request(1, "ping", [1]), result({}), id="result to refused params"),
    pytest.param(PROBE, result({}), id="result to an unserved method"),
    pytest.param(PROBE, error(-32602), id="-32602 to an unserved method"),
    pytest.param(PROBE, error(-32600), id="-32600 to an unserved method"),
    pytest.param(INITIALIZED, error(-32601), id="error to a notification"),
    pytest.param(INITIALIZED, result({}), id="result to a notification"),
    pytest.param(message(method="tools/list"), result({"tools": []}), id="no id"),
    pytest.param(b"\n", error(-32700), id="error to a blank line"),
    pytest.param(b" \t\r\n", result({}), id="result to a blank line"),
    pytest.param(message(id=1, result={}), error(-32600), id="error to a response"),
    pytest.param(message(id=1, error={}), result({}), id="result to a response"),
    pytest.param(b"not json\n", result({}), id="result to what is not JSON"),
    pytest.param(b"not json\n", error(-32602), id="-32602 to what is not JSON"),
    pytest.param(b"[1]\n", error(-32601), id="-32601 to an array"),
    pytest.param(message(id=1.5, method="ping"), result({}), id="result to id 1.5"),
    pytest.param(message(id=1.5, method="ping"), error(-32602), id="-32602 to id 1.5"),
    pytest.param(message(id=None, method="x"), error(-32601), id="-32601 to id null"),
    pytest.param(
        b'{"id":1,"method":"initialize"}\n', result({}), id="result to no jsonrpc"
    ),
    pytest.param(b'{"id":1,"method":"x"}\n', error(-32601), id="-32601 to no jsonrpc"),
]


@pytest.mark.parametrize(("asked", "written"), ANSWERS_THE_FRONT_CANNOT_WRITE)
def test_an_answer_the_front_cannot_write_is_unplaceable(asked, written):
    alone = read([client(asked)])
    assert alone.unplaceable is False and alone.errors == ()
    facts = read([client(asked), written])
    assert facts == alone._replace(unplaceable=True)
    assert not facts.initialize_answered and facts.probe_error is None
    after = read([client(asked), written, client(LIST), result({"tools": []}, 2)])
    assert after.list_answered and after.errors == () and after.unplaceable


@pytest.mark.parametrize(
    "direction",
    ["middle", "", "Client", "SERVER", "C", None, 0, True, b"client", ("client",)],
)
def test_a_direction_that_is_neither_constant_is_unplaceable(direction):
    assert read([(direction, INITIALIZE)]) == WireFacts(unplaceable=True)
    assert read([[direction, message(id=1, result={})]]) == WireFacts(unplaceable=True)
    between = read([client(INITIALIZE), (direction, b"\n"), result({})])
    assert between.reached and not between.initialize_answered
    assert between.unplaceable


@pytest.mark.parametrize(
    "tools",
    [
        None,
        {},
        "selfcheck_token selfcheck_fail",
        {TOKEN_TOOL_NAME: {}, FAIL_TOOL_NAME: {}},
        7,
    ],
)
def test_a_list_result_without_an_array_is_no_answer_to_the_list(tools):
    value = {} if tools is None else {"tools": tools}
    facts = read([client(LIST), result(value)])
    assert facts == WireFacts(list_requested=True)


@pytest.mark.parametrize(
    "tools",
    [
        [],
        [TOKEN_TOOL_NAME, FAIL_TOOL_NAME],
        [[TOKEN_TOOL_NAME], [FAIL_TOOL_NAME], None, 7],
        [{"name": TOKEN_TOOL_NAME}],
        [{"name": FAIL_TOOL_NAME}, {"name": FAIL_TOOL_NAME}],
        [{"name": [TOKEN_TOOL_NAME]}, {"name": {FAIL_TOOL_NAME: 1}}],
        [{"name": TOKEN_TOOL_NAME}, {"title": FAIL_TOOL_NAME}],
        [{"name": TOKEN_TOOL_NAME.upper()}, {"name": FAIL_TOOL_NAME}],
    ],
)
def test_a_list_that_does_not_name_both_tools(tools):
    facts = read([client(LIST), result({"tools": tools})])
    assert facts == WireFacts(list_requested=True, list_answered=True)


def test_a_list_that_names_both_tools_among_others():
    tools = [7, {"name": MARKER}, {"name": FAIL_TOOL_NAME}, {"name": TOKEN_TOOL_NAME}]
    facts = read([client(LIST), result({"tools": tools})])
    assert facts.list_answered and facts.list_both_tools
    assert MARKER not in repr(facts)


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"isError": 0},
        {"isError": 1},
        {"isError": "false"},
        {"isError": "true"},
        {"isError": None},
        {"isError": []},
        {"content": [{"type": "text", "text": TOKEN}]},
    ],
)
def test_a_call_result_without_the_expected_is_error(value):
    lines = [client(CALL_TOKEN), result(value), client(CALL_FAIL), result(value)]
    facts = read(lines)
    assert facts == WireFacts(token_call_requested=True, fail_call_requested=True)
    assert TOKEN not in repr(facts)


def test_a_call_answered_the_other_way_round():
    lines = [
        client(CALL_TOKEN),
        result({"isError": True}),
        client(CALL_FAIL),
        result({"isError": False}),
    ]
    assert read(lines) == WireFacts(token_call_requested=True, fail_call_requested=True)


@pytest.mark.parametrize(
    "params",
    [None, [TOKEN_TOOL_NAME], {"name": [TOKEN_TOOL_NAME]}, {"name": "selfcheck.token"}],
)
def test_a_call_of_no_tool_of_the_check(params):
    facts = read([client(request(1, "tools/call", params))])
    assert facts == WireFacts()


HOSTILE_LINES = [
    pytest.param(b"\xff\xfe\xfd\n", id="not UTF-8"),
    pytest.param(b"\xef\xbb\xbf" + PING, id="byte order mark"),
    pytest.param(b"[" * 5000 + b"\n", id="arrays 5000 deep"),
    pytest.param(b'{"a":' * 5000 + b"\n", id="objects 5000 deep"),
    pytest.param(b"[" * 100_000 + b"\n", id="arrays 100000 deep"),
    pytest.param(
        b'{"jsonrpc":"2.0","id":1,"method":"ping","params":'
        + b"[" * 3000
        + b"]" * 3000
        + b"}\n",
        id="deep params",
    ),
    pytest.param(message(id=int("9" * 400), method="ping"), id="400 digits"),
    pytest.param(b'{"id":' + b"9" * 5000 + b"}\n", id="5000 digits"),
    pytest.param(b'{"id":1e999,"method":"ping"}\n', id="a float too large"),
    pytest.param(b'{"method":"ping","method":"ping","id":1}\n', id="a member twice"),
    pytest.param(message(id=1, method="m" * 1_000_000), id="a megabyte method"),
    pytest.param(b"x" * 1_000_000 + b"\n", id="a megabyte of text"),
    pytest.param(b"\n", id="a blank line"),
    pytest.param(b"\x00\n", id="NUL"),
    pytest.param(b"null\n", id="null"),
    pytest.param(b"{}\n", id="an empty object"),
    pytest.param(PING.rstrip(b"\n"), id="no line feed"),
]


@pytest.mark.parametrize("line", HOSTILE_LINES)
def test_any_bytes_of_a_client_line_are_read_as_the_front_reads_them(tmp_path, line):
    lines = copy_of(tmp_path, [*EXCHANGE, line])
    facts = read(lines)
    assert facts.unplaceable is False
    assert lines[11] == client(line)
    answers = [json.loads(answer) for _, answer in lines[12:]]
    assert len(answers) <= 1
    codes = [answer["error"]["code"] for answer in answers if "error" in answer]
    codes = [code for code in codes if code != -32601]
    assert [code for code, _ in facts.errors] == codes
    assert facts._replace(errors=(), unforeseen=()) == PASS
    assert read([client(line)]) == read([(FROM_CLIENT, line)])


@pytest.mark.parametrize("line", HOSTILE_LINES)
def test_any_bytes_of_a_server_line_are_unplaceable(line):
    assert read([server(line)]) == WireFacts(unplaceable=True)
    facts = read([client(INITIALIZE), server(line)])
    assert facts.reached and not facts.initialize_answered and facts.unplaceable


def test_an_empty_line_is_read():
    assert read([client(b"")]) == WireFacts()
    assert read([client(b""), server(b"")]) == WireFacts(unplaceable=True)


@pytest.mark.parametrize(
    "lines",
    [
        None,
        MARKER,
        MARKER.encode(),
        {client(INITIALIZE): 1},
        iter([client(INITIALIZE)]),
        7,
        selfcheck_server.WireCopy((client(INITIALIZE), result({})), False),
        selfcheck_server.WireCopy((client(INITIALIZE),), False),
        [None],
        [MARKER],
        [(FROM_CLIENT,)],
        [(FROM_CLIENT, INITIALIZE, MARKER)],
        [(FROM_CLIENT, MARKER)],
        [(FROM_CLIENT, bytearray(INITIALIZE))],
        [(FROM_CLIENT, memoryview(INITIALIZE))],
        [(FROM_CLIENT, None)],
        [client(INITIALIZE), (FROM_SERVER, [MARKER])],
        [{FROM_CLIENT: INITIALIZE}],
        [(MARKER, MARKER)],
    ],
)
def test_an_argument_of_another_form_is_a_type_error(lines):
    with pytest.raises(TypeError) as raised:
        read(lines)
    assert str(raised.value) in TYPE_ERROR_TEXTS
    assert raised.value.__cause__ is None and raised.value.__context__ is None


def test_the_same_lines_give_the_same_hashable_value(tmp_path):
    lines = list(copy_of(tmp_path, [*EXCHANGE, request(1, "x/y"), b"}\n"]))
    before = list(lines)
    first, second = read(lines), read(tuple(lines))
    assert first == second and hash(first) == hash(second)
    assert lines == before
    assert type(first.errors) is tuple and type(first.unforeseen) is tuple
    assert all(type(pair) is tuple for pair in first.errors)
    assert read(lines) is not first and read(lines) == first


def test_it_reads_nothing_but_its_argument(tmp_path, monkeypatch):
    lines = copy_of(tmp_path, [*EXCHANGE, request(1, "x/y"), b"}\n"])
    expected = read(lines)

    def refuse(*args, **kwargs):
        raise AssertionError("the module reached outside its argument")

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    monkeypatch.setenv("PATH", "")
    for name in list(selfcheck_server.__dict__):
        if name.startswith("ENV_"):
            monkeypatch.setenv(getattr(selfcheck_server, name), MARKER)
    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr("builtins.print", refuse)
    monkeypatch.setattr("os.open", refuse)
    monkeypatch.setattr("os.getenv", refuse)
    monkeypatch.setattr("time.time", refuse)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    assert read(lines) == expected
    assert list(empty.iterdir()) == []
