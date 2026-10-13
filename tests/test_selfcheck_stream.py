import json

import pytest

from hilclaw.selfcheck_outcome import (
    CONNECTED,
    FRONT_REFUSED,
    NO_CALL,
    PASSED,
    REFUSED_STATUS_WORDS,
    SESSION_FAILED,
    SessionEvidence,
    decide,
)
from hilclaw.selfcheck_stream import (
    EVENT_KIND_KEY,
    EVENT_SUBKIND_KEY,
    FAIL_TOOL_SESSION_NAME,
    INIT_KIND,
    INIT_SUBKIND,
    OTHER_STATUS,
    REPLY_KEY,
    RESULT_KIND,
    SERVER_ERRORS_KEY,
    SERVER_NAME,
    SERVER_NAME_KEY,
    SERVER_STATUS_KEY,
    SERVERS_KEY,
    TOKEN_TOOL_SESSION_NAME,
    TOOL_PREFIX,
    TOOLS_KEY,
    StreamFacts,
    evidence,
    read,
)
from hilclaw.selfcheck_wire import (
    FAIL_TOOL_NAME,
    MAX_LISTED,
    MAX_STRING,
    OTHER,
    TOKEN_TOOL_NAME,
    WireFacts,
)

TOKEN = "0123456789abcdef0123456789abcdef"
FAIL_TOKEN = "fedcba9876543210fedcba9876543210"
MARKER = "marker-3f9c"


class Drop:
    def __repr__(self):
        return "DROP"


DROP = Drop()
REPLY = f"{MARKER} first {TOKEN} second {FAIL_TOKEN} end"
BOTH_TOOLS = [TOKEN_TOOL_SESSION_NAME, FAIL_TOOL_SESSION_NAME]
READ_ERROR_TEXTS = (
    "the output must be bytes",
    "a token must be a str",
    "a token must be 32 lowercase hexadecimal characters",
    "the two tokens must differ",
)
EVIDENCE_ERROR_TEXTS = (
    "the facts must be a StreamFacts",
    "a yes-or-no value must be True or False",
    "the status word must be None or a word this module carries",
    "timed_out must be True or False",
    "the exit status must be None or an integer",
)
WIRE = WireFacts(
    reached=True,
    client_version="2.1.280",
    revision_asked="2025-11-25",
    initialize_answered=True,
    revision_answered="2025-06-18",
    list_requested=True,
    list_after_initialize=True,
    list_answered=True,
    list_both_tools=True,
    token_call_requested=True,
    token_call_answered=True,
    fail_call_requested=True,
    fail_call_answered=True,
)
DROPPED_WIRE = WireFacts(
    reached=True,
    client_version="2.1.280",
    revision_asked="2025-11-25",
    initialize_answered=True,
    revision_answered="2025-06-18",
)
PASSING = StreamFacts(
    init_read=True,
    server_status=CONNECTED,
    token_tool_listed=True,
    fail_tool_listed=True,
    result_read=True,
    token_in_reply=True,
    fail_token_in_reply=True,
    session_tools=tuple(BOTH_TOOLS),
)
NO_INIT = PASSING._replace(
    init_read=False,
    server_status=None,
    token_tool_listed=False,
    fail_tool_listed=False,
    session_tools=(),
)
NO_RESULT = PASSING._replace(
    result_read=False, token_in_reply=False, fail_token_in_reply=False
)


def label(value):
    return repr(value)[:40]


def line(value):
    return json.dumps(value).encode() + b"\n"


def changed(members, changes):
    members = {**members, **changes}
    return {key: value for key, value in members.items() if value is not DROP}


def server(status=CONNECTED, name=SERVER_NAME):
    return changed({SERVER_NAME_KEY: name, SERVER_STATUS_KEY: status}, {})


def init(**changes):
    members = {
        EVENT_KIND_KEY: INIT_KIND,
        EVENT_SUBKIND_KEY: INIT_SUBKIND,
        TOOLS_KEY: list(BOTH_TOOLS),
        SERVERS_KEY: [server()],
    }
    return changed(members, changes)


def result(text=REPLY, **changes):
    return changed({EVENT_KIND_KEY: RESULT_KIND, REPLY_KEY: text}, changes)


def other_event(**members):
    return {EVENT_KIND_KEY: "between", **members}


def stream(*values):
    return b"".join(line(value) for value in values)


def facts(output):
    return read(output, token=TOKEN, fail_token=FAIL_TOKEN)


def outcome(output, wire=WIRE, *, exit_status=0, timed_out=False):
    session = evidence(facts(output), timed_out=timed_out, exit_status=exit_status)
    return decide(None, session, wire).outcome


PASSING_STREAM = stream(init(), other_event(note=1), other_event(), result())


def test_the_session_side_names_are_built_from_the_server_and_the_wire_names():
    assert SERVER_NAME == "hilclaw"
    assert TOOL_PREFIX == "mcp__hilclaw__"
    assert TOKEN_TOOL_SESSION_NAME == "mcp__hilclaw__selfcheck_token"
    assert FAIL_TOOL_SESSION_NAME == "mcp__hilclaw__selfcheck_fail"
    assert TOKEN_TOOL_SESSION_NAME == TOOL_PREFIX + TOKEN_TOOL_NAME
    assert FAIL_TOOL_SESSION_NAME == TOOL_PREFIX + FAIL_TOOL_NAME


def test_the_members_the_record_quotes_from_a_page_or_an_observation():
    assert SERVERS_KEY == "mcp_servers"
    assert SERVER_NAME_KEY == "name"
    assert SERVER_STATUS_KEY == "status"
    assert SERVER_ERRORS_KEY == "mcp_server_errors"
    assert TOOLS_KEY == "tools"


def test_the_status_stand_in_is_neither_connected_nor_a_refusing_word():
    assert type(OTHER_STATUS) is str
    assert OTHER_STATUS == OTHER
    assert OTHER_STATUS != CONNECTED
    assert OTHER_STATUS not in REFUSED_STATUS_WORDS


def test_a_passing_stream_gives_every_fact_and_passes():
    assert facts(PASSING_STREAM) == PASSING
    session = evidence(PASSING, timed_out=False, exit_status=0)
    assert session == SessionEvidence(
        started=True,
        timed_out=False,
        exit_status=0,
        init_read=True,
        server_status=CONNECTED,
        server_in_errors=False,
        any_config_error=False,
        token_tool_listed=True,
        fail_tool_listed=True,
        result_read=True,
        token_in_reply=True,
        fail_token_in_reply=True,
    )
    assert decide(None, session, WIRE).outcome == PASSED


def test_an_empty_error_list_and_further_members_do_not_change_a_pass():
    output = stream(
        init(**{SERVER_ERRORS_KEY: [], "note": MARKER, "count": 3, "ratio": 0.5}),
        result(note=None),
    )
    assert facts(output) == PASSING
    assert outcome(output) == PASSED


def test_another_server_beside_the_one_of_the_check_changes_nothing():
    output = stream(
        init(**{SERVERS_KEY: [server("failed", "another"), server()]}), result()
    )
    assert facts(output) == PASSING


def test_walk_through_the_reply_without_the_tokens_is_no_call():
    output = stream(init(), result("I called nothing."))
    found = facts(output)
    assert found == PASSING._replace(token_in_reply=False, fail_token_in_reply=False)
    assert outcome(output) == NO_CALL


@pytest.mark.parametrize(
    "servers",
    [[], [server(name="another")], [server("failed")]],
    ids=label,
)
def test_walk_through_a_dropped_server_is_front_refused_by_b(servers):
    output = stream(init(**{SERVERS_KEY: servers, TOOLS_KEY: []}), result("none"))
    found = facts(output)
    assert found.init_read and found.result_read
    assert found.server_status in (None, *REFUSED_STATUS_WORDS)
    session = evidence(found, timed_out=False, exit_status=0)
    verdict = decide(None, session, DROPPED_WIRE)
    assert (verdict.outcome, verdict.refused_a, verdict.refused_b) == (
        FRONT_REFUSED,
        False,
        True,
    )


@pytest.mark.parametrize("word", ["pending", "dropped", "word-x", MARKER])
def test_walk_through_a_word_outside_the_list_is_session_failed(word):
    output = stream(init(**{SERVERS_KEY: [server(word)]}), result())
    assert facts(output).server_status == OTHER_STATUS
    assert outcome(output) == SESSION_FAILED
    assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


@pytest.mark.parametrize("status", [1, 2, 255, -9, None])
def test_walk_through_a_session_that_did_not_end_well_is_session_failed(status):
    assert outcome(PASSING_STREAM, exit_status=status) == SESSION_FAILED


def test_a_time_limit_is_session_failed_whatever_the_output_holds():
    assert outcome(PASSING_STREAM, exit_status=None, timed_out=True) == SESSION_FAILED


def test_no_init_event():
    output = stream(other_event(), result())
    assert facts(output) == NO_INIT
    assert outcome(output) == SESSION_FAILED
    assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


@pytest.mark.parametrize(
    "second",
    [
        init(),
        init(**{SERVERS_KEY: [server("failed")]}),
        init(**{SERVER_ERRORS_KEY: [{"name": SERVER_NAME}]}),
        init(**{SERVERS_KEY: DROP, TOOLS_KEY: DROP}),
    ],
    ids=label,
)
def test_two_init_events_are_not_read(second):
    for output in (
        stream(init(), second, result()),
        stream(second, init(), result()),
        stream(init(), other_event(), second, other_event(), result()),
    ):
        assert facts(output) == NO_INIT
        assert outcome(output) == SESSION_FAILED
        assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


def test_two_init_events_of_a_dropped_server_are_not_front_refused():
    dropped = init(**{SERVERS_KEY: [], TOOLS_KEY: []})
    output = stream(dropped, dropped, result("none"))
    assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


def test_an_init_event_after_the_result_line_leaves_no_result_message():
    assert facts(stream(result(), init())) == NO_RESULT
    assert facts(stream(init(), result(), init())) == StreamFacts()
    assert outcome(stream(result(), init())) == SESSION_FAILED


@pytest.mark.parametrize(
    "change",
    [
        {EVENT_SUBKIND_KEY: DROP},
        {EVENT_SUBKIND_KEY: None},
        {EVENT_SUBKIND_KEY: [INIT_SUBKIND]},
        {EVENT_SUBKIND_KEY: INIT_SUBKIND.upper()},
        {EVENT_SUBKIND_KEY: INIT_SUBKIND + " "},
        {EVENT_KIND_KEY: DROP},
        {EVENT_KIND_KEY: 0},
        {EVENT_KIND_KEY: [INIT_KIND]},
        {EVENT_KIND_KEY: INIT_KIND.upper()},
        {EVENT_KIND_KEY: f"{INIT_KIND}/{INIT_SUBKIND}"},
    ],
    ids=label,
)
def test_a_line_that_does_not_say_that_it_is_the_init_event_is_not_read(change):
    assert facts(stream(init(**change), result())) == NO_INIT


def test_an_init_event_nested_in_another_line_is_not_read():
    output = stream(other_event(event=init()), [init()], result())
    assert facts(output) == NO_INIT


@pytest.mark.parametrize(
    ("servers", "word"),
    [
        (DROP, OTHER_STATUS),
        (None, OTHER_STATUS),
        (SERVER_NAME, OTHER_STATUS),
        ({SERVER_NAME: {SERVER_STATUS_KEY: CONNECTED}}, OTHER_STATUS),
        ({SERVER_NAME_KEY: SERVER_NAME, SERVER_STATUS_KEY: CONNECTED}, OTHER_STATUS),
        ([SERVER_NAME], OTHER_STATUS),
        ([[server()]], OTHER_STATUS),
        ([server(), 7], OTHER_STATUS),
        ([None], OTHER_STATUS),
        ([server(name=7)], OTHER_STATUS),
        ([server(name=None)], OTHER_STATUS),
        ([server(name=[SERVER_NAME])], OTHER_STATUS),
        ([{SERVER_STATUS_KEY: CONNECTED}], OTHER_STATUS),
        ([server(), {SERVER_STATUS_KEY: "failed"}], OTHER_STATUS),
        ([server(), server()], OTHER_STATUS),
        ([server(), server("failed")], OTHER_STATUS),
        ([server("failed"), server("failed")], OTHER_STATUS),
        ([server("failed"), server(name="another"), server()], OTHER_STATUS),
        ([server(DROP)], OTHER_STATUS),
        ([server(None)], OTHER_STATUS),
        ([server(1)], OTHER_STATUS),
        ([server(True)], OTHER_STATUS),
        ([server([CONNECTED])], OTHER_STATUS),
        ([server({SERVER_STATUS_KEY: CONNECTED})], OTHER_STATUS),
        ([server("Connected")], OTHER_STATUS),
        ([server(" connected")], OTHER_STATUS),
        ([server("connected\n")], OTHER_STATUS),
        ([server("CONNECTED")], OTHER_STATUS),
        ([server("")], OTHER_STATUS),
        ([server("Failed")], OTHER_STATUS),
        ([server("failed ")], OTHER_STATUS),
        ([server(OTHER_STATUS)], OTHER_STATUS),
        ([server(MARKER * 40)], OTHER_STATUS),
        ([], None),
        ([server(name="another")], None),
        ([server(name="Hilclaw")], None),
        ([server(name=" hilclaw")], None),
        ([server(name="hilclaw2")], None),
        ([server(name="")], None),
        ([server("failed")], "failed"),
        ([server("failed"), server(name="another")], "failed"),
        ([server()], CONNECTED),
        ([server(name="another", status="failed"), server()], CONNECTED),
    ],
    ids=label,
)
def test_the_status_word(servers, word):
    found = facts(stream(init(**{SERVERS_KEY: servers}), result()))
    assert found == PASSING._replace(server_status=word)
    if word != CONNECTED:
        assert outcome(stream(init(**{SERVERS_KEY: servers}), result())) != PASSED
    if word == OTHER_STATUS:
        output = stream(init(**{SERVERS_KEY: servers, TOOLS_KEY: []}), result("none"))
        assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


def test_every_refusing_word_of_the_outcome_table_is_carried():
    for word in REFUSED_STATUS_WORDS:
        found = facts(stream(init(**{SERVERS_KEY: [server(word)]}), result()))
        assert found.server_status == word


@pytest.mark.parametrize(
    ("errors", "expected"),
    [
        (DROP, False),
        ([], False),
        ([{SERVER_NAME_KEY: SERVER_NAME}], True),
        ([{SERVER_NAME_KEY: "another"}], True),
        ([{"server": "another", "error": MARKER}], True),
        (["another"], True),
        ([[]], True),
        ([None], True),
        ({}, True),
        ({"another": MARKER}, True),
        (None, True),
        ("", True),
        (MARKER, True),
        (0, True),
        (False, True),
        (True, True),
    ],
    ids=label,
)
def test_the_server_errors(errors, expected):
    output = stream(init(**{SERVER_ERRORS_KEY: errors}), result())
    found = facts(output)
    assert found == PASSING._replace(
        server_in_errors=expected, any_config_error=expected
    )
    assert (outcome(output) == PASSED) is not expected
    dropped = init(**{SERVER_ERRORS_KEY: errors, SERVERS_KEY: [], TOOLS_KEY: []})
    refused = outcome(stream(dropped, result("none")), DROPPED_WIRE) == FRONT_REFUSED
    assert refused is not expected


@pytest.mark.parametrize(
    ("tools", "token_listed", "fail_listed", "kept"),
    [
        (DROP, False, False, ()),
        (None, False, False, ()),
        ({TOKEN_TOOL_SESSION_NAME: 1, FAIL_TOOL_SESSION_NAME: 1}, False, False, ()),
        (" ".join(BOTH_TOOLS), False, False, ()),
        ([], False, False, ()),
        ([TOKEN_TOOL_SESSION_NAME], True, False, (TOKEN_TOOL_SESSION_NAME,)),
        ([FAIL_TOOL_SESSION_NAME], False, True, (FAIL_TOOL_SESSION_NAME,)),
        (BOTH_TOOLS[::-1], True, True, tuple(BOTH_TOOLS[::-1])),
        (BOTH_TOOLS * 3, True, True, tuple(BOTH_TOOLS)),
        ([BOTH_TOOLS], False, False, ()),
        ([{SERVER_NAME_KEY: name} for name in BOTH_TOOLS], False, False, ()),
        ([7, None, True, *BOTH_TOOLS, 0.5], True, True, tuple(BOTH_TOOLS)),
        ([TOKEN_TOOL_NAME, FAIL_TOOL_NAME], False, False, ()),
        (["x" + name for name in BOTH_TOOLS], False, False, ()),
        ([" " + name for name in BOTH_TOOLS], False, False, ()),
        ([name.upper() for name in BOTH_TOOLS], False, False, ()),
        ([" ".join(BOTH_TOOLS)], False, False, (OTHER,)),
        (
            [name + "2" for name in BOTH_TOOLS],
            False,
            False,
            tuple(name + "2" for name in BOTH_TOOLS),
        ),
        ([name + "\n" for name in BOTH_TOOLS], False, False, (OTHER,)),
        (["Read", "mcp__another__selfcheck_token"], False, False, ()),
    ],
    ids=label,
)
def test_the_tool_names(tools, token_listed, fail_listed, kept):
    output = stream(init(**{TOOLS_KEY: tools}), result())
    assert facts(output) == PASSING._replace(
        token_tool_listed=token_listed, fail_tool_listed=fail_listed, session_tools=kept
    )
    if not (token_listed and fail_listed):
        assert outcome(output) == NO_CALL


def test_the_session_tools_are_bounded_and_capped():
    overlong = TOOL_PREFIX + "a" * MAX_STRING
    longest = TOOL_PREFIX + "b" * (MAX_STRING - len(TOOL_PREFIX))
    odd = [TOOL_PREFIX + tail for tail in ("a b", "a/b", "é", MARKER + "\x00", "")]
    found = facts(stream(init(**{TOOLS_KEY: [overlong, longest, *odd]}), result()))
    assert found.session_tools == (OTHER, longest, TOOL_PREFIX)
    assert not found.session_tools_dropped
    assert not found.token_tool_listed and not found.fail_tool_listed
    assert all(len(name) <= MAX_STRING for name in found.session_tools)


def test_more_session_tools_than_the_cap_set_the_flag():
    names = [f"{TOOL_PREFIX}tool_{index}" for index in range(MAX_LISTED + 24)]
    exact = facts(stream(init(**{TOOLS_KEY: names[:MAX_LISTED]}), result()))
    assert exact.session_tools == tuple(names[:MAX_LISTED])
    assert not exact.session_tools_dropped
    repeated = names[:MAX_LISTED] + names[:3]
    assert not facts(
        stream(init(**{TOOLS_KEY: repeated}), result())
    ).session_tools_dropped
    more = facts(stream(init(**{TOOLS_KEY: names + BOTH_TOOLS}), result()))
    assert more.session_tools == tuple(names[:MAX_LISTED])
    assert more.session_tools_dropped
    assert more.token_tool_listed and more.fail_tool_listed


def test_no_result_message():
    output = stream(init(), other_event())
    assert facts(output) == NO_RESULT
    assert outcome(output) == SESSION_FAILED


def test_a_result_message_that_is_not_the_last_line_is_not_read():
    for output in (
        stream(init(), result(), other_event()),
        stream(init(), result(), []),
        stream(init(), result(), {}),
        stream(init(), result()) + b"not json\n",
        stream(init(), result()) + b"7\n",
    ):
        assert facts(output) == NO_RESULT


def test_the_last_of_two_result_messages_is_the_one_read():
    found = facts(stream(init(), result(), result("nothing")))
    assert found == PASSING._replace(token_in_reply=False, fail_token_in_reply=False)
    assert facts(stream(init(), result("nothing"), result())) == PASSING


@pytest.mark.parametrize("cut", [2, 10, len(line(result())) - 1, len(line(result()))])
def test_an_output_cut_in_or_before_its_last_line_has_no_result_message(cut):
    output = PASSING_STREAM[:-cut]
    assert facts(output) == NO_RESULT
    assert outcome(output, exit_status=None, timed_out=True) == SESSION_FAILED


def test_a_whole_last_line_without_its_line_end_is_read():
    assert facts(PASSING_STREAM[:-1]) == PASSING


def test_an_output_cut_inside_the_init_event_reads_nothing():
    assert facts(line(init())[:-9]) == StreamFacts()


@pytest.mark.parametrize(
    "change",
    [
        {EVENT_KIND_KEY: DROP},
        {EVENT_KIND_KEY: None},
        {EVENT_KIND_KEY: [RESULT_KIND]},
        {EVENT_KIND_KEY: RESULT_KIND.upper()},
        {EVENT_KIND_KEY: RESULT_KIND + " "},
    ],
    ids=label,
)
def test_a_last_line_that_does_not_say_that_it_is_the_result_message(change):
    assert facts(stream(init(), result(**change))) == NO_RESULT


@pytest.mark.parametrize(
    "text",
    [
        DROP,
        None,
        "",
        0,
        True,
        [REPLY],
        [TOKEN, FAIL_TOKEN],
        {REPLY_KEY: REPLY},
        {"text": REPLY},
    ],
    ids=label,
)
def test_a_reply_that_is_no_text_holds_no_token(text):
    output = stream(init(), result(text))
    found = facts(output)
    assert found == PASSING._replace(token_in_reply=False, fail_token_in_reply=False)
    assert outcome(output) == NO_CALL


def test_one_token_only_each_way_round():
    first = facts(stream(init(), result(f"only {TOKEN}")))
    assert (first.token_in_reply, first.fail_token_in_reply) == (True, False)
    second = facts(stream(init(), result(f"only {FAIL_TOKEN}")))
    assert (second.token_in_reply, second.fail_token_in_reply) == (False, True)
    for text in (f"only {TOKEN}", f"only {FAIL_TOKEN}"):
        assert outcome(stream(init(), result(text))) == NO_CALL


def test_a_token_is_found_anywhere_in_the_reply_text_and_only_whole():
    glued = facts(stream(init(), result(f"x{TOKEN}{FAIL_TOKEN}y")))
    assert glued.token_in_reply and glued.fail_token_in_reply
    for text in (
        REPLY.upper(),
        f"{TOKEN[:-1]} {FAIL_TOKEN[1:]}",
        f"{TOKEN[:16]} {TOKEN[16:]} {FAIL_TOKEN[:16]}\n{FAIL_TOKEN[16:]}",
        "-".join(TOKEN) + "-".join(FAIL_TOKEN),
    ):
        found = facts(stream(init(), result(text)))
        assert not found.token_in_reply and not found.fail_token_in_reply


def test_the_tokens_are_looked_for_in_the_reply_text_only():
    output = stream(
        init(note=REPLY, **{TOOLS_KEY: [*BOTH_TOOLS, TOKEN, FAIL_TOKEN]}),
        other_event(**{REPLY_KEY: REPLY, "content": [{"text": REPLY}]}),
        {EVENT_KIND_KEY: RESULT_KIND, REPLY_KEY: REPLY, "early": True},
        other_event(note=REPLY),
        result(
            "nothing", note=REPLY, message=REPLY, content=[REPLY], **{TOKEN: FAIL_TOKEN}
        ),
    )
    output = REPLY.encode() + b"\n" + output
    assert TOKEN.encode() in output and FAIL_TOKEN.encode() in output
    found = facts(output)
    assert found.result_read
    assert not found.token_in_reply and not found.fail_token_in_reply
    assert outcome(output) == NO_CALL


def test_the_tokens_after_the_result_message_are_not_found():
    for tail in (REPLY.encode() + b"\n", line(other_event(**{REPLY_KEY: REPLY}))):
        found = facts(stream(init(), result("nothing")) + tail)
        assert not found.token_in_reply and not found.fail_token_in_reply
        assert not found.result_read


def test_each_token_is_looked_for_under_its_own_name():
    found = read(PASSING_STREAM, token=FAIL_TOKEN, fail_token=TOKEN)
    assert found == PASSING
    other = "a" * 32
    found = read(PASSING_STREAM, token=other, fail_token=FAIL_TOKEN)
    assert (found.token_in_reply, found.fail_token_in_reply) == (False, True)
    found = read(PASSING_STREAM, token=TOKEN, fail_token=other)
    assert (found.token_in_reply, found.fail_token_in_reply) == (True, False)


WRONG_NAMES = [
    ({EVENT_KIND_KEY: "kind"}, {"kind_key": "kind"}, StreamFacts(), SESSION_FAILED),
    ({EVENT_SUBKIND_KEY: "sub"}, {}, NO_INIT, SESSION_FAILED),
    ({INIT_KIND: "session"}, {}, NO_INIT, SESSION_FAILED),
    ({INIT_SUBKIND: "start"}, {}, NO_INIT, SESSION_FAILED),
    ({INIT_KIND: "init", INIT_SUBKIND: DROP}, {}, NO_INIT, SESSION_FAILED),
    ({}, {"kind": "final"}, NO_RESULT, SESSION_FAILED),
    (
        {},
        {"reply_key": "text"},
        PASSING._replace(token_in_reply=False, fail_token_in_reply=False),
        NO_CALL,
    ),
]


def renamed(members, names):
    out = {}
    for key, value in members.items():
        key = names.get(key, key)
        if type(value) is str and value in names:
            value = names[value]
        if key is not DROP and value is not DROP:
            out[key] = value
    return out


@pytest.mark.parametrize(
    ("init_names", "result_names", "expected", "word"), WRONG_NAMES, ids=label
)
def test_a_wrong_provisional_name_fails_safe(init_names, result_names, expected, word):
    output = stream(renamed(init(), init_names), renamed_result(result_names))
    assert facts(output) == expected
    assert outcome(output) == word
    assert outcome(output, DROPPED_WIRE) not in (PASSED, FRONT_REFUSED)
    dropped = renamed(init(**{SERVERS_KEY: [], TOOLS_KEY: []}), init_names)
    output = stream(dropped, renamed_result(result_names, "none"))
    assert outcome(output) != PASSED
    if init_names:
        assert outcome(output, DROPPED_WIRE) == SESSION_FAILED
    else:
        rightly_named = stream(dropped, result("none"))
        assert outcome(output, DROPPED_WIRE) == outcome(rightly_named, DROPPED_WIRE)


def renamed_result(names, text=REPLY):
    return {
        names.get("kind_key", EVENT_KIND_KEY): names.get("kind", RESULT_KIND),
        names.get("reply_key", REPLY_KEY): text,
    }


@pytest.mark.parametrize(
    "tools",
    [
        [{"name": name} for name in BOTH_TOOLS],
        {name: {} for name in BOTH_TOOLS},
        ",".join(BOTH_TOOLS),
        [BOTH_TOOLS],
    ],
    ids=label,
)
def test_another_form_of_the_tool_list_fails_safe(tools):
    output = stream(init(**{TOOLS_KEY: tools}), result())
    found = facts(output)
    assert not found.token_tool_listed and not found.fail_tool_listed
    assert outcome(output) == NO_CALL
    assert outcome(output, DROPPED_WIRE) not in (PASSED, FRONT_REFUSED)


@pytest.mark.parametrize("word", ["error", "disconnected", "Failed", "refused"])
def test_another_word_for_a_failed_server_fails_safe(word):
    output = stream(
        init(**{SERVERS_KEY: [server(word)], TOOLS_KEY: []}), result("none")
    )
    assert outcome(output, DROPPED_WIRE) == SESSION_FAILED
    assert outcome(output) == SESSION_FAILED


@pytest.mark.parametrize(
    "output",
    [
        b"",
        b"\n",
        b"\n\n \t\r\n\r\n   ",
        b"\x00",
        b"\xff\xfe\x00\x01\n\x80\x81\n",
        b"not json\n",
        b"[]\n",
        b'"text"\n',
        b"7\n",
        b"null\n",
        b"true\n",
        b"{}\n",
        b"{}{}\n",
        b"{\n}\n",
        b"NaN\n",
        b"9" * 10000 + b"\n",
    ],
    ids=label,
)
def test_an_output_without_an_event_gives_the_empty_facts(output):
    assert facts(output) == StreamFacts()
    assert outcome(output) == SESSION_FAILED
    assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


def test_blank_lines_and_carriage_returns_are_read_as_line_ends():
    output = PASSING_STREAM.replace(b"\n", b"\r\n")
    assert facts(output) == PASSING
    spaced = b"\n \n".join(b"  " + part + b"\t" for part in PASSING_STREAM.split(b"\n"))
    assert facts(spaced + b"\n\n\r\n \n") == PASSING


def test_a_carriage_return_alone_does_not_end_a_line():
    assert facts(PASSING_STREAM.replace(b"\n", b"\r")) == StreamFacts()


def test_invalid_utf8_in_a_line_makes_that_line_nothing():
    broken = line(init()).replace(b"hilclaw", b"hil\xffclaw", 1)
    assert facts(broken + line(result())) == NO_INIT
    broken = line(result()).replace(b"marker", b"mar\xc3ker", 1)
    assert facts(line(init()) + broken) == NO_RESULT
    assert facts(b"\xff\n" + PASSING_STREAM) == PASSING


def test_a_byte_order_mark_makes_the_first_line_nothing():
    assert facts(b"\xef\xbb\xbf" + PASSING_STREAM) == NO_INIT
    assert facts(line(init()) + b"\xef\xbb\xbf" + line(result())) == NO_RESULT


def test_text_as_json_escapes_is_decoded_once():
    escaped = json.dumps(result(), ensure_ascii=True).encode()
    escaped = escaped.replace(b"0123", b"\\u0030123")
    assert TOKEN.encode() not in escaped
    assert facts(line(init()) + escaped + b"\n") == PASSING
    twice = result(REPLY.replace("0123", "\\u0030123"))
    found = facts(stream(init(), twice))
    assert (found.token_in_reply, found.fail_token_in_reply) == (False, True)


def with_member_twice(value, key, first):
    text = json.dumps(value)
    return ("{" + json.dumps(key) + ": " + json.dumps(first) + ", " + text[1:]).encode()


@pytest.mark.parametrize(
    ("key", "first"),
    [
        (EVENT_KIND_KEY, INIT_KIND),
        (EVENT_SUBKIND_KEY, INIT_SUBKIND),
        (SERVERS_KEY, []),
        (SERVER_ERRORS_KEY, [MARKER]),
        (TOOLS_KEY, []),
        ("note", 1),
    ],
    ids=label,
)
def test_a_member_name_twice_in_the_init_event_makes_it_no_event(key, first):
    twice = with_member_twice(init(note=1, **{SERVER_ERRORS_KEY: []}), key, first)
    output = twice + b"\n" + line(result())
    assert facts(output) == NO_INIT
    assert outcome(output) == SESSION_FAILED
    assert outcome(output, DROPPED_WIRE) == SESSION_FAILED


def test_a_member_name_twice_at_a_depth_makes_the_line_no_event():
    nested = line(init()).replace(b'"status"', b'"status": "failed", "status"', 1)
    assert nested != line(init())
    assert facts(nested + line(result())) == NO_INIT


@pytest.mark.parametrize(
    ("key", "first"),
    [(EVENT_KIND_KEY, RESULT_KIND), (REPLY_KEY, REPLY), (REPLY_KEY, ""), ("note", 1)],
    ids=label,
)
def test_a_member_name_twice_in_the_result_line_makes_it_no_message(key, first):
    twice = with_member_twice(result(note=1), key, first)
    assert facts(line(init()) + twice + b"\n") == NO_RESULT


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_a_constant_outside_json_makes_the_line_nothing(constant):
    spoiled = line(init(note=0)).replace(b'"note": 0', f'"note": {constant}'.encode())
    assert constant.encode() in spoiled
    assert facts(spoiled + line(result())) == NO_INIT
    spoiled = line(result(note=0)).replace(b'"note": 0', f'"note": {constant}'.encode())
    assert facts(line(init()) + spoiled) == NO_RESULT


def test_nesting_beyond_the_limit_of_the_interpreter_makes_the_line_nothing():
    deep = b"[" * 200000 + b"]" * 200000
    assert facts(deep + b"\n") == StreamFacts()
    assert facts(line(init()) + b'{"a":' * 200000 + b"\n" + line(result())) == PASSING
    inside = line(init(note=0)).replace(b'"note": 0', b'"note": ' + deep)
    assert facts(inside + line(result())) == NO_INIT


def test_an_integer_too_long_to_convert_is_not_converted():
    digits = b"9" * 10000
    long_init = line(init(note=0)).replace(b'"note": 0', b'"note": -' + digits)
    long_result = line(result(note=0)).replace(b'"note": 0', b'"note": ' + digits)
    assert facts(long_init + long_result) == PASSING


@pytest.mark.parametrize(
    "word",
    [
        "pending",
        "Connected",
        "",
        MARKER,
        1,
        True,
        b"connected",
        [CONNECTED],
        (CONNECTED,),
    ],
    ids=label,
)
def test_facts_with_a_status_word_the_module_does_not_carry_are_refused(word):
    with pytest.raises(TypeError) as caught:
        evidence(PASSING._replace(server_status=word), timed_out=False, exit_status=0)
    assert str(caught.value) == EVIDENCE_ERROR_TEXTS[2]
    assert MARKER not in str(caught.value)


def test_a_very_long_line_is_read():
    filler = "x" * 3_000_000
    output = stream(init(note=filler), other_event(note=filler), result(filler + REPLY))
    assert facts(output) == PASSING


def test_many_lines_are_read():
    output = line(init()) + line(other_event(note=MARKER)) * 20000 + line(result())
    assert facts(output) == PASSING


@pytest.mark.parametrize(
    "output",
    [
        PASSING_STREAM.decode(),
        None,
        PASSING_STREAM.splitlines(),
        tuple(PASSING_STREAM.splitlines()),
        bytearray(PASSING_STREAM),
        memoryview(PASSING_STREAM),
        7,
    ],
    ids=label,
)
def test_an_output_that_is_not_bytes_is_refused(output):
    with pytest.raises(TypeError) as caught:
        read(output, token=TOKEN, fail_token=FAIL_TOKEN)
    assert str(caught.value) == READ_ERROR_TEXTS[0]


@pytest.mark.parametrize(
    "value", [None, 7, TOKEN.encode(), [TOKEN], (TOKEN,), True], ids=label
)
def test_a_token_of_another_type_is_refused(value):
    for tokens in (
        {"token": value, "fail_token": FAIL_TOKEN},
        {"token": TOKEN, "fail_token": value},
    ):
        with pytest.raises(TypeError) as caught:
            read(PASSING_STREAM, **tokens)
        assert str(caught.value) == READ_ERROR_TEXTS[1]


@pytest.mark.parametrize(
    "value",
    [
        "",
        TOKEN[:-1],
        TOKEN + "0",
        TOKEN.upper(),
        TOKEN[:-1] + "g",
        TOKEN[:-1] + "\n",
        TOKEN + "\n",
        " " + TOKEN[1:],
        "０" * 32,
        MARKER,
    ],
    ids=label,
)
def test_a_token_of_another_form_is_refused(value):
    for tokens in (
        {"token": value, "fail_token": FAIL_TOKEN},
        {"token": TOKEN, "fail_token": value},
    ):
        with pytest.raises(ValueError) as caught:
            read(PASSING_STREAM, **tokens)
        assert str(caught.value) == READ_ERROR_TEXTS[2]
        assert MARKER not in str(caught.value)


def test_two_equal_tokens_are_refused():
    with pytest.raises(ValueError) as caught:
        read(PASSING_STREAM, token=TOKEN, fail_token=TOKEN)
    assert str(caught.value) == READ_ERROR_TEXTS[3]
    assert TOKEN not in str(caught.value)


def test_the_tokens_are_named_arguments():
    with pytest.raises(TypeError):
        read(PASSING_STREAM, TOKEN, FAIL_TOKEN)
    with pytest.raises(TypeError):
        read(PASSING_STREAM)
    with pytest.raises(TypeError):
        evidence(PASSING, False, 0)
    with pytest.raises(TypeError):
        evidence(PASSING)


def test_the_arguments_are_checked_before_the_output_is_read():
    with pytest.raises(ValueError):
        read(b"", token=TOKEN, fail_token=TOKEN)


@pytest.mark.parametrize(
    "value",
    [
        tuple(PASSING),
        list(PASSING),
        PASSING._asdict(),
        SessionEvidence(),
        None,
        PASSING_STREAM,
        MARKER,
    ],
    ids=label,
)
def test_facts_of_another_type_are_refused(value):
    with pytest.raises(TypeError) as caught:
        evidence(value, timed_out=False, exit_status=0)
    assert str(caught.value) == EVIDENCE_ERROR_TEXTS[0]


@pytest.mark.parametrize(
    "name",
    [
        name
        for name in SessionEvidence._fields
        if name in StreamFacts._fields and name != "server_status"
    ],
)
@pytest.mark.parametrize("value", [1, 0, None, "true", MARKER, [True], 1.0], ids=label)
def test_facts_with_a_member_that_is_no_boolean_are_refused(name, value):
    with pytest.raises(TypeError) as caught:
        evidence(PASSING._replace(**{name: value}), timed_out=False, exit_status=0)
    assert str(caught.value) == EVIDENCE_ERROR_TEXTS[1]


@pytest.mark.parametrize("value", [1, 0, None, "", "False", MARKER, [False]], ids=label)
def test_a_timed_out_that_is_no_boolean_is_refused(value):
    with pytest.raises(TypeError) as caught:
        evidence(PASSING, timed_out=value, exit_status=0)
    assert str(caught.value) == EVIDENCE_ERROR_TEXTS[3]


@pytest.mark.parametrize(
    "value", [True, False, 0.0, 1.0, "0", b"0", [0], (0,), MARKER], ids=label
)
def test_an_exit_status_of_another_type_is_refused(value):
    with pytest.raises(TypeError) as caught:
        evidence(PASSING, timed_out=False, exit_status=value)
    assert str(caught.value) == EVIDENCE_ERROR_TEXTS[4]
    assert MARKER not in str(caught.value)


def test_the_evidence_of_a_started_session_with_nothing_read():
    session = evidence(StreamFacts(), timed_out=False, exit_status=0)
    assert session == SessionEvidence(started=True, exit_status=0)
    assert decide(None, session, WIRE).outcome == SESSION_FAILED
    assert decide(None, session, None).outcome == SESSION_FAILED


@pytest.mark.parametrize(
    ("timed_out", "status"),
    [(False, 0), (False, 3), (False, -15), (False, None), (True, None), (True, 0)],
)
def test_how_the_process_ended_is_handed_on_as_given(timed_out, status):
    session = evidence(PASSING, timed_out=timed_out, exit_status=status)
    assert session.started is True
    assert session.timed_out is timed_out
    assert session.exit_status == status
    assert type(session) is SessionEvidence
    passed = decide(None, session, WIRE).outcome == PASSED
    assert passed is (not timed_out and status == 0)


def test_the_evidence_carries_each_fact_under_its_own_name():
    for name in StreamFacts._fields[:9]:
        if name == "server_status":
            continue
        only = StreamFacts(**{name: True})
        session = evidence(only, timed_out=False, exit_status=None)
        assert session == SessionEvidence(started=True, **{name: True})
    for word in (None, CONNECTED, OTHER_STATUS, *REFUSED_STATUS_WORDS):
        session = evidence(
            StreamFacts(server_status=word), timed_out=False, exit_status=None
        )
        assert session == SessionEvidence(started=True, server_status=word)
    listed = StreamFacts(session_tools=tuple(BOTH_TOOLS), session_tools_dropped=True)
    assert evidence(listed, timed_out=False, exit_status=None) == SessionEvidence(
        started=True
    )


def test_every_value_read_is_one_decide_accepts():
    outputs = [
        b"",
        PASSING_STREAM,
        stream(init(**{SERVERS_KEY: DROP, TOOLS_KEY: DROP})),
        stream(init(**{SERVER_ERRORS_KEY: None}), result(None)),
        stream(result()),
    ]
    for output in outputs:
        found = facts(output)
        for name in StreamFacts._fields:
            value = getattr(found, name)
            if name == "server_status":
                assert value is None or type(value) is str
            elif name == "session_tools":
                assert type(value) is tuple
            else:
                assert type(value) is bool
        for wire in (WIRE, DROPPED_WIRE, None):
            assert outcome(output, wire) in (PASSED, NO_CALL, SESSION_FAILED)


def test_only_the_passing_stream_shape_passes():
    spoilers = [
        {SERVERS_KEY: []},
        {SERVERS_KEY: [server("pending")]},
        {SERVER_ERRORS_KEY: [MARKER]},
        {TOOLS_KEY: [TOKEN_TOOL_SESSION_NAME]},
        {EVENT_SUBKIND_KEY: MARKER},
    ]
    for spoiler in spoilers:
        assert outcome(stream(init(**spoiler), result())) != PASSED
    for text in ("", TOKEN, FAIL_TOKEN):
        assert outcome(stream(init(), result(text))) != PASSED


def test_nothing_of_the_output_leaks_into_the_values():
    secret = "account-7d41"
    output = stream(
        init(
            note=secret,
            **{
                SERVERS_KEY: [server(secret)],
                TOOLS_KEY: [*BOTH_TOOLS, TOOL_PREFIX + secret + " x", secret],
                SERVER_ERRORS_KEY: [{SERVER_NAME_KEY: secret}],
            },
        ),
        other_event(note=secret),
        result(f"{secret} {REPLY}", note=secret),
    )
    found = facts(output)
    session = evidence(found, timed_out=False, exit_status=0)
    for text in (repr(found), repr(session), str(found), str(tuple(found))):
        assert secret not in text
        assert MARKER not in text
        assert TOKEN not in text and FAIL_TOKEN not in text
    assert found.server_status == OTHER_STATUS
    assert found.session_tools == (*BOTH_TOOLS, OTHER)


def test_the_same_input_gives_equal_values_that_hold_nothing_mutable():
    first, second = facts(PASSING_STREAM), facts(PASSING_STREAM)
    assert first == second
    assert hash(first) == hash(second)
    assert type(first) is StreamFacts
    assert type(first.session_tools) is tuple
    assert all(type(name) is str for name in first.session_tools)
    session = evidence(first, timed_out=False, exit_status=0)
    assert session == evidence(second, timed_out=False, exit_status=0)
    assert hash(session) == hash(evidence(second, timed_out=False, exit_status=0))


def test_the_default_facts_hold_nothing():
    empty = StreamFacts()
    assert empty.server_status is None
    assert empty.session_tools == ()
    assert not any(
        getattr(empty, name)
        for name in StreamFacts._fields
        if name not in ("server_status", "session_tools")
    )
