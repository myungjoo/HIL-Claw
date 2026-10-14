import getpass
import inspect
import json
import os
import platform
import re
import socket

import pytest

from hilclaw import (
    selfcheck_login,
    selfcheck_outcome,
    selfcheck_report,
    selfcheck_stream,
)
from hilclaw.selfcheck_login import (
    AUTH_METHODS,
    LOGIN_INSTRUCTION,
    LOGIN_UNREADABLE,
    NO_CLAUDE,
    NOT_LOGGED_IN,
    LoginStatus,
)
from hilclaw.selfcheck_outcome import (
    FRONT_REFUSED,
    NO_CALL,
    OUTCOMES,
    PASSED,
    SESSION_FAILED,
    SessionEvidence,
    Verdict,
    decide,
)
from hilclaw.selfcheck_report import (
    SystemFacts,
    build,
    exit_status,
    line,
    system_facts,
)
from hilclaw.selfcheck_session import SessionRun
from hilclaw.selfcheck_stream import (
    FAIL_TOOL_SESSION_NAME,
    TOKEN_TOOL_SESSION_NAME,
    TOOL_PREFIX,
    StreamFacts,
)
from hilclaw.selfcheck_wire import MAX_LISTED, MAX_STRING, OTHER, WireFacts

TOKEN = "0123456789abcdef0123456789abcdef"
FAIL_TOKEN = "fedcba9876543210fedcba9876543210"
MARKER = "marker-3f9c"
ERROR_TEXTS = (
    "the login must be a LoginStatus",
    "the system facts must be a SystemFacts",
    "the run must be a SessionRun or None",
    "the stream facts must be a StreamFacts or None",
    "a session step goes with a step one that says logged in",
    "a list of names must be a tuple",
    "a yes-or-no value must be True or False",
    "an integer value must be None or an integer",
    "the report must be a dict that build returned",
    "the outcome must be a string",
    "the outcome must be a word of the closed list",
    "the login outcome must be None or a string",
    "the login outcome must be None or a word of step one",
    "the session evidence must be a SessionEvidence",
    "the wire facts must be a WireFacts or None",
    "the errors of the wire facts must be a tuple",
    "the exit status must be None or an integer",
)
SYSTEM = SystemFacts("Linux", "6.8.0-45-generic", "3.14.4")
LOGGED_IN = LoginStatus(None, "claude.ai", 0, False)
NOT_IN = LoginStatus(NOT_LOGGED_IN, "none", 1, False)
SESSION = SessionEvidence(
    started=True,
    timed_out=False,
    exit_status=0,
    init_read=True,
    server_status="connected",
    token_tool_listed=True,
    fail_tool_listed=True,
    result_read=True,
    token_in_reply=True,
    fail_token_in_reply=True,
)
WIRE = WireFacts(
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
STREAM = StreamFacts(
    init_read=True,
    server_status="connected",
    token_tool_listed=True,
    fail_tool_listed=True,
    result_read=True,
    token_in_reply=True,
    fail_token_in_reply=True,
    session_tools=(TOKEN_TOOL_SESSION_NAME, FAIL_TOOL_SESSION_NAME),
)
PASS_RUN = SessionRun(SESSION, WIRE, False, STREAM, True)
DROPPED_WIRE = WireFacts(
    reached=True,
    client_version="2.1.280",
    revision_asked="2025-11-25",
    initialize_answered=True,
    revision_answered="2025-06-18",
)
DROPPED_SESSION = SessionEvidence(
    started=True, exit_status=0, init_read=True, result_read=True
)
QUIET_SESSION = SESSION._replace(token_in_reply=False, fail_token_in_reply=False)
QUIET_WIRE = WIRE._replace(
    token_call_requested=False,
    token_call_answered=False,
    fail_call_requested=False,
    fail_call_answered=False,
)
ERRORS = ((-32602, "tools/list"),)
NOT_STARTED = SessionRun(SessionEvidence(), None, False, None, True)
FAILED = SESSION._replace(exit_status=1, result_read=False, token_in_reply=False)

CASES = {
    "no claude": (LoginStatus(NO_CLAUDE, None, None, False), None, NO_CLAUDE),
    "not logged in": (NOT_IN, None, NOT_LOGGED_IN),
    "unreadable, exit status": (
        LoginStatus(LOGIN_UNREADABLE, "other", 7, False),
        None,
        LOGIN_UNREADABLE,
    ),
    "unreadable, time limit": (
        LoginStatus(LOGIN_UNREADABLE, None, None, True),
        None,
        LOGIN_UNREADABLE,
    ),
    "a pass": (LOGGED_IN, PASS_RUN, PASSED),
    "a pass, directory left": (LOGGED_IN, PASS_RUN._replace(removed=False), PASSED),
    "no call": (
        LOGGED_IN,
        SessionRun(QUIET_SESSION, QUIET_WIRE, False, STREAM, True),
        NO_CALL,
    ),
    "no call, a torn copy": (
        LOGGED_IN,
        SessionRun(QUIET_SESSION, QUIET_WIRE, True, STREAM, True),
        NO_CALL,
    ),
    "refused, b": (
        LOGGED_IN,
        SessionRun(DROPPED_SESSION, DROPPED_WIRE, False, StreamFacts(), True),
        FRONT_REFUSED,
    ),
    "refused, a": (
        LOGGED_IN,
        SessionRun(SESSION, WIRE._replace(errors=ERRORS), False, STREAM, True),
        FRONT_REFUSED,
    ),
    "refused, both": (
        LOGGED_IN,
        SessionRun(
            DROPPED_SESSION,
            DROPPED_WIRE._replace(errors=ERRORS),
            False,
            StreamFacts(),
            True,
        ),
        FRONT_REFUSED,
    ),
    "failed, exit status": (
        LOGGED_IN,
        SessionRun(FAILED, WIRE, False, STREAM, True),
        SESSION_FAILED,
    ),
    "failed, time limit": (
        LOGGED_IN,
        SessionRun(
            SESSION._replace(timed_out=True, exit_status=None),
            WIRE,
            False,
            STREAM,
            True,
        ),
        SESSION_FAILED,
    ),
    "failed, not started": (LOGGED_IN, NOT_STARTED, SESSION_FAILED),
    "failed, no wire copy": (
        LOGGED_IN,
        SessionRun(SESSION, None, False, STREAM, True),
        SESSION_FAILED,
    ),
    "failed, server not reached": (
        LOGGED_IN,
        SessionRun(SESSION, WireFacts(), False, STREAM, True),
        SESSION_FAILED,
    ),
    "failed, a torn copy": (
        LOGGED_IN,
        SessionRun(SESSION, WIRE, True, STREAM, True),
        SESSION_FAILED,
    ),
    "failed, an unplaceable line": (
        LOGGED_IN,
        SessionRun(SESSION, WIRE._replace(unplaceable=True), False, STREAM, True),
        SESSION_FAILED,
    ),
}
PLANTED = [
    "has space",
    'quo"te',
    "line\nend",
    "back\\slash",
    "C:\\Users\\alice\\.claude",
    "alice@example.com",
    "caf\u00e9",
    "x" * (MAX_STRING + 1),
    "",
    "~alice",
]
NOT_STRINGS = [1, True, 1.5, b"2.1.280", ["2.1.280"], ("a",), {"a": 1}]
WORD_MEMBERS = ["client_version", "revision_asked", "revision_answered"]
NOT_BOOLEANS = [1, 0, "true", "", None, [True], MARKER]
NOT_INTEGERS = ["1", True, False, 1.0, [1], MARKER]


def label(value):
    return repr(value)[:24]


def decided(login, run):
    if run is None:
        return decide(login.outcome, SessionEvidence(), None)
    return decide(login.outcome, run.session, run.wire, torn=run.torn)


def no_leak(data, planted=()):
    text = data.decode("ascii")
    assert data.endswith(b"\n") and data.count(b"\n") == 1 and b"\r" not in data
    assert not re.search(r"[0-9A-Fa-f]{32}", text)
    parsed = json.loads(text)
    if "wire" in parsed:
        parsed["wire"]["unforeseen_methods"] = []
    rest = json.dumps(parsed)
    assert "/" not in rest and "\\" not in rest
    machine = (socket.gethostname(), getpass.getuser(), os.path.expanduser("~"))
    for word in (*machine, *planted):
        escaped = json.dumps(word)[1:-1]
        if len(word) >= 4:
            assert word.lower() not in text.lower()
            assert escaped.lower() not in text.lower()


def with_wire(**members):
    return SessionRun(SESSION, WIRE._replace(**members), False, STREAM, True)


def with_stream(**members):
    return SessionRun(SESSION, WIRE, False, STREAM._replace(**members), True)


def test_not_logged_in_walk_through():
    report = build(NOT_IN, None, system=SYSTEM)
    assert report == {
        "outcome": NOT_LOGGED_IN,
        "refused_a": False,
        "refused_b": False,
        "instruction": LOGIN_INSTRUCTION,
        "login": {"auth_method": "none", "exit_status": 1, "timed_out": False},
        "system": {
            "os_name": "Linux",
            "os_release": "6.8.0-45-generic",
            "python_version": "3.14.4",
        },
    }
    assert json.loads(line(report)) == report
    assert exit_status(report["outcome"]) == selfcheck_report.EXIT_NOT_LOGGED_IN != 0


def test_a_pass_walk_through():
    report = build(LOGGED_IN, PASS_RUN, system=SYSTEM)
    assert report == {
        "outcome": PASSED,
        "refused_a": False,
        "refused_b": False,
        "login": {"auth_method": "claude.ai", "exit_status": 0, "timed_out": False},
        "system": {
            "os_name": "Linux",
            "os_release": "6.8.0-45-generic",
            "python_version": "3.14.4",
        },
        "session": {
            "started": True,
            "init_read": True,
            "result_read": True,
            "exit_status": 0,
            "timed_out": False,
            "wire_copy_read": True,
            "tools": [TOKEN_TOOL_SESSION_NAME, FAIL_TOOL_SESSION_NAME],
            "tools_dropped": False,
            "token_tool_listed": True,
            "fail_tool_listed": True,
            "token_in_reply": True,
            "fail_token_in_reply": True,
            "directory_removed": True,
        },
        "wire": {
            "initialize_seen": True,
            "client_version": "2.1.280",
            "revision_asked": "2025-11-25",
            "revision_answered": "2025-06-18",
            "probe_seen": True,
            "probe_before_initialize": True,
            "probe_revision": "2026-07-28",
            "probe_error": -32601,
            "token_call_requested": True,
            "token_call_answered": True,
            "fail_call_requested": True,
            "fail_call_answered": True,
            "unforeseen_methods": [],
            "unforeseen_dropped": False,
        },
    }
    assert json.loads(line(report)) == report
    assert exit_status(report["outcome"]) == 0


def test_the_model_calls_nothing_walk_through():
    login, run, _ = CASES["no call"]
    report = build(login, run, system=SYSTEM)
    assert report["outcome"] == NO_CALL
    session, wire = report["session"], report["wire"]
    assert session["token_tool_listed"] and session["fail_tool_listed"]
    assert session["tools"] == [TOKEN_TOOL_SESSION_NAME, FAIL_TOOL_SESSION_NAME]
    assert not session["token_in_reply"] and not session["fail_token_in_reply"]
    for member in ("token_call", "fail_call"):
        assert wire[member + "_requested"] is False
        assert wire[member + "_answered"] is False
    assert exit_status(report["outcome"]) == selfcheck_report.EXIT_NO_CALL


def test_one_tool_called_and_not_answered_as_the_record_says():
    wire = QUIET_WIRE._replace(token_call_requested=True, fail_call_answered=True)
    session = QUIET_SESSION._replace(token_in_reply=True)
    report = build(
        LOGGED_IN, SessionRun(session, wire, False, STREAM, True), system=SYSTEM
    )
    assert report["outcome"] == NO_CALL
    assert report["wire"]["token_call_requested"] is True
    assert report["wire"]["token_call_answered"] is False
    assert report["wire"]["fail_call_requested"] is False
    assert report["wire"]["fail_call_answered"] is True
    assert report["session"]["token_in_reply"] is True
    assert report["session"]["fail_token_in_reply"] is False


@pytest.mark.parametrize(
    "case, a, b",
    [("refused, b", False, True), ("refused, a", True, False), ("refused, both", 1, 1)],
)
def test_the_client_drops_the_server_walk_through(case, a, b):
    login, run, _ = CASES[case]
    report = build(login, run, system=SYSTEM)
    assert report["outcome"] == FRONT_REFUSED
    assert (report["refused_a"], report["refused_b"]) == (bool(a), bool(b))
    assert exit_status(report["outcome"]) == selfcheck_report.EXIT_FRONT_REFUSED


def test_a_failed_session_walk_through():
    login, run, _ = CASES["failed, exit status"]
    report = build(login, run, system=SYSTEM)
    assert report["outcome"] == SESSION_FAILED
    session = report["session"]
    assert session["started"] and session["init_read"] and session["wire_copy_read"]
    assert report["wire"]["initialize_seen"] is True
    assert session["result_read"] is False
    assert (session["exit_status"], session["timed_out"]) == (1, False)
    assert exit_status(report["outcome"]) == selfcheck_report.EXIT_SESSION_FAILED


@pytest.mark.parametrize("case", CASES)
def test_the_outcome_is_the_one_decide_gives(case):
    login, run, expected = CASES[case]
    report = build(login, run, system=SYSTEM)
    verdict = decided(login, run)
    assert report["outcome"] == verdict.outcome == expected
    assert (report["refused_a"], report["refused_b"]) == verdict[1:]
    assert ("instruction" in report) == (expected == NOT_LOGGED_IN)
    assert report.get("instruction", LOGIN_INSTRUCTION) == LOGIN_INSTRUCTION
    assert ("session" in report) == (run is not None)
    assert ("wire" in report) == (run is not None and run.wire is not None)
    assert (exit_status(report["outcome"]) == 0) == (expected == PASSED)
    data = line(report)
    assert json.loads(data) == report
    assert data == line(build(login, run, system=SYSTEM))
    no_leak(data)


def test_every_outcome_is_reached():
    assert {expected for _, _, expected in CASES.values()} == set(OUTCOMES)


def test_the_member_order_is_the_documented_one():
    report = build(LOGGED_IN, PASS_RUN, system=SYSTEM)
    top = ("outcome", "refused_a", "refused_b", "login", "system", "session", "wire")
    assert tuple(report) == top
    assert tuple(build(NOT_IN, None, system=SYSTEM)) == (
        *top[:3],
        "instruction",
        "login",
        "system",
    )
    assert tuple(report["login"]) == ("auth_method", "exit_status", "timed_out")
    assert tuple(report["system"]) == SystemFacts._fields
    assert tuple(report["system"]) == ("os_name", "os_release", "python_version")
    parsed = json.loads(line(report))
    for group in top[3:]:
        assert tuple(parsed[group]) == tuple(report[group])
    assert line(report).startswith(b'{"outcome":"passed","refused_a":false,')


def test_the_member_names_are_no_schema_names():
    report = build(LOGGED_IN, PASS_RUN, system=SYSTEM)
    names = ["instruction", *report]
    for group in ("login", "system", "session", "wire"):
        names += report[group]
    for name in names:
        assert re.fullmatch(r"[a-z]+(_[a-z]+)*", name)
        assert name != "schema_version"


def test_no_outcome_word_is_written_in_the_module():
    source = inspect.getsource(selfcheck_report)
    for word in OUTCOMES:
        assert f'"{word}"' not in source and f"'{word}'" not in source


def test_step_one_exit_status_and_time_limit():
    login, _, _ = CASES["unreadable, exit status"]
    assert build(login, None, system=SYSTEM)["login"] == {
        "auth_method": "other",
        "exit_status": 7,
        "timed_out": False,
    }
    login, _, _ = CASES["unreadable, time limit"]
    assert build(login, None, system=SYSTEM)["login"] == {
        "auth_method": None,
        "exit_status": None,
        "timed_out": True,
    }
    login, _, _ = CASES["no claude"]
    report = build(login, None, system=SYSTEM)
    assert report["login"]["exit_status"] is None
    assert "session" not in report and "wire" not in report


def test_no_session_was_started():
    report = build(LOGGED_IN, NOT_STARTED, system=SYSTEM)
    assert "wire" not in report
    assert report["session"] == {
        "started": False,
        "init_read": False,
        "result_read": False,
        "exit_status": None,
        "timed_out": False,
        "wire_copy_read": False,
        "tools": [],
        "tools_dropped": False,
        "token_tool_listed": False,
        "fail_tool_listed": False,
        "token_in_reply": False,
        "fail_token_in_reply": False,
        "directory_removed": True,
    }


def test_a_session_without_a_wire_copy():
    login, run, _ = CASES["failed, no wire copy"]
    report = build(login, run, system=SYSTEM)
    assert "wire" not in report and b"client_version" not in line(report)
    assert report["session"]["wire_copy_read"] is False
    assert report["session"]["started"] is True


def test_a_wire_copy_without_the_initialize_request():
    login, run, _ = CASES["failed, server not reached"]
    report = build(login, run, system=SYSTEM)
    assert report["session"]["wire_copy_read"] is True
    wire = report["wire"]
    assert wire["initialize_seen"] is False and wire["probe_seen"] is False
    assert wire["client_version"] is None and wire["probe_error"] is None
    assert wire["revision_asked"] is None and wire["probe_revision"] is None


def test_the_directory_was_not_removed():
    login, run, _ = CASES["a pass, directory left"]
    report = build(login, run, system=SYSTEM)
    assert report["session"]["directory_removed"] is False
    assert report["outcome"] == PASSED


@pytest.mark.parametrize("method", AUTH_METHODS)
def test_each_auth_method_is_carried(method):
    login = LOGGED_IN._replace(auth_method=method)
    assert build(login, PASS_RUN, system=SYSTEM)["login"]["auth_method"] == method


@pytest.mark.parametrize(
    "method", ["other", "CLAUDE.AI", "claude.ai ", *PLANTED, *NOT_STRINGS], ids=label
)
def test_an_auth_method_outside_the_six_is_other(method):
    login = LOGGED_IN._replace(auth_method=method)
    report = build(login, PASS_RUN, system=SYSTEM)
    assert report["login"]["auth_method"] == selfcheck_login.AUTH_METHOD_OTHER
    planted = type(method) is str and method != OTHER
    no_leak(line(report), [method] if planted else [])


def test_no_auth_method_is_null():
    login = LOGGED_IN._replace(auth_method=None)
    assert build(login, PASS_RUN, system=SYSTEM)["login"]["auth_method"] is None


@pytest.mark.parametrize("member", [*WORD_MEMBERS, "probe_revision"])
@pytest.mark.parametrize("value", [*PLANTED, "a/b", *NOT_STRINGS], ids=label)
def test_a_wire_string_outside_the_bound_is_other(member, value):
    report = build(LOGGED_IN, with_wire(**{member: value}), system=SYSTEM)
    assert report["wire"][member] == OTHER
    no_leak(line(report), [value] if type(value) is str else [])


@pytest.mark.parametrize("value", ["a", "x" * MAX_STRING, "2.1.280-beta_1", "other"])
def test_a_wire_string_inside_the_bound_is_carried(value):
    report = build(LOGGED_IN, with_wire(client_version=value), system=SYSTEM)
    assert report["wire"]["client_version"] == value


@pytest.mark.parametrize("value", [*PLANTED, *NOT_STRINGS, None], ids=label)
def test_a_method_name_outside_the_bound_is_other(value):
    run = with_wire(unforeseen=("resources/list", value))
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["wire"]["unforeseen_methods"] == ["resources/list", OTHER]
    assert report["wire"]["unforeseen_dropped"] is False
    no_leak(line(report), [value] if type(value) is str else [])


def test_method_names_are_distinct_and_cut():
    names = tuple(f"x/m{i}" for i in range(MAX_LISTED + 1))
    report = build(LOGGED_IN, with_wire(unforeseen=names), system=SYSTEM)
    assert report["wire"]["unforeseen_methods"] == list(names[:MAX_LISTED])
    assert report["wire"]["unforeseen_dropped"] is True
    run = with_wire(unforeseen=names[:MAX_LISTED] + names[:3] + ("bad name", " "))
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["wire"]["unforeseen_methods"] == list(names[:MAX_LISTED])
    assert report["wire"]["unforeseen_dropped"] is True
    run = with_wire(unforeseen=names[: MAX_LISTED - 1] + ("a b", "c d", names[0]))
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["wire"]["unforeseen_methods"] == [*names[: MAX_LISTED - 1], OTHER]
    assert report["wire"]["unforeseen_dropped"] is False
    run = with_wire(unforeseen=("a/b",), unforeseen_dropped=True)
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["wire"]["unforeseen_methods"] == ["a/b"]
    assert report["wire"]["unforeseen_dropped"] is True


@pytest.mark.parametrize("value", PLANTED, ids=label)
def test_a_tool_name_outside_the_bound_is_other(value):
    run = with_stream(session_tools=(TOKEN_TOOL_SESSION_NAME, TOOL_PREFIX + value))
    report = build(LOGGED_IN, run, system=SYSTEM)
    kept = TOOL_PREFIX + value
    if not re.fullmatch(rf"[A-Za-z0-9._-]{{1,{MAX_STRING}}}", kept):
        kept = OTHER
    assert report["session"]["tools"] == [TOKEN_TOOL_SESSION_NAME, kept]
    no_leak(line(report), [value] if kept == OTHER else [])


@pytest.mark.parametrize(
    "value",
    [*PLANTED, "Bash", "mcp__other__tool", "MCP__HILCLAW__X", *NOT_STRINGS, None],
    ids=label,
)
def test_a_tool_name_without_the_prefix_is_left_out(value):
    run = with_stream(session_tools=(value, FAIL_TOOL_SESSION_NAME, value))
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["session"]["tools"] == [FAIL_TOOL_SESSION_NAME]
    assert report["session"]["tools_dropped"] is False
    no_leak(line(report), [value] if type(value) is str else [])


def test_the_word_the_reader_put_for_a_tool_name_is_kept():
    run = with_stream(session_tools=(OTHER, TOKEN_TOOL_SESSION_NAME, OTHER))
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["session"]["tools"] == [OTHER, TOKEN_TOOL_SESSION_NAME]


def test_tool_names_are_distinct_and_cut():
    names = tuple(f"{TOOL_PREFIX}t{i}" for i in range(MAX_LISTED + 4))
    report = build(LOGGED_IN, with_stream(session_tools=names), system=SYSTEM)
    assert report["session"]["tools"] == list(names[:MAX_LISTED])
    assert report["session"]["tools_dropped"] is True
    run = with_stream(session_tools=names[:MAX_LISTED] + names[:2])
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["session"]["tools"] == list(names[:MAX_LISTED])
    assert report["session"]["tools_dropped"] is False
    run = with_stream(session_tools=names[:1], session_tools_dropped=True)
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["session"]["tools"] == list(names[:1])
    assert report["session"]["tools_dropped"] is True


@pytest.mark.parametrize(
    "facts",
    [
        SystemFacts("Windows", "11", "3.14.4"),
        SystemFacts("Darwin", "23.5.0", "3.11.9"),
        SystemFacts("Linux", "6.1.0-rpi7+rpt-rpi-v8", "3.15.0a1+"),
        SystemFacts("Linux", "5.15.153.1-microsoft-standard-WSL2", "3.12.3"),
    ],
)
def test_the_system_facts_are_carried(facts):
    report = build(NOT_IN, None, system=facts)
    assert tuple(report["system"].values()) == tuple(facts)


@pytest.mark.parametrize("member", SystemFacts._fields)
@pytest.mark.parametrize("value", [*PLANTED, "a/b", *NOT_STRINGS], ids=label)
def test_a_system_fact_outside_the_bound_is_other(member, value):
    report = build(NOT_IN, None, system=SYSTEM._replace(**{member: value}))
    assert report["system"][member] == OTHER
    no_leak(line(report), [value] if type(value) is str else [])


def test_a_system_fact_that_is_none_is_null():
    report = build(NOT_IN, None, system=SYSTEM._replace(os_release=None))
    assert report["system"]["os_release"] is None


def test_system_facts_reads_the_three_values_of_the_interpreter():
    facts = system_facts()
    assert type(facts) is SystemFacts
    assert facts == (
        platform.system(),
        platform.release(),
        platform.python_version(),
    )
    data = line(build(NOT_IN, None, system=facts))
    assert data.endswith(b"\n") and data.count(b"\n") == 1


def test_nothing_of_a_pass_read_from_an_output_with_two_tokens_leaks():
    init = {
        selfcheck_stream.EVENT_KIND_KEY: selfcheck_stream.INIT_KIND,
        selfcheck_stream.EVENT_SUBKIND_KEY: selfcheck_stream.INIT_SUBKIND,
        selfcheck_stream.SERVERS_KEY: [
            {
                selfcheck_stream.SERVER_NAME_KEY: selfcheck_stream.SERVER_NAME,
                selfcheck_stream.SERVER_STATUS_KEY: selfcheck_outcome.CONNECTED,
            }
        ],
        selfcheck_stream.TOOLS_KEY: [
            TOKEN_TOOL_SESSION_NAME,
            FAIL_TOOL_SESSION_NAME,
            TOOL_PREFIX + "/home/alice",
            "Bash",
        ],
        "cwd": "/home/alice/work",
    }
    result = {
        selfcheck_stream.EVENT_KIND_KEY: selfcheck_stream.RESULT_KIND,
        selfcheck_stream.REPLY_KEY: f"first {TOKEN} then {FAIL_TOKEN} {MARKER}",
    }
    output = b"".join(json.dumps(event).encode() + b"\n" for event in (init, result))
    stream = selfcheck_stream.read(output, token=TOKEN, fail_token=FAIL_TOKEN)
    session = selfcheck_stream.evidence(stream, timed_out=False, exit_status=0)
    run = SessionRun(session, WIRE, False, stream, True)
    report = build(LOGGED_IN, run, system=SYSTEM)
    assert report["outcome"] == PASSED
    assert report["session"]["tools"] == [
        TOKEN_TOOL_SESSION_NAME,
        FAIL_TOOL_SESSION_NAME,
        OTHER,
    ]
    no_leak(line(report), [TOKEN, FAIL_TOKEN, MARKER, "alice", "work"])


@pytest.mark.parametrize(
    "login",
    [
        None,
        tuple(LOGGED_IN),
        (None, MARKER, 0, False),
        list(LOGGED_IN),
        SYSTEM,
        Verdict(PASSED),
        MARKER,
    ],
    ids=label,
)
def test_a_login_of_another_form_is_refused(login):
    with pytest.raises(TypeError) as caught:
        build(login, PASS_RUN, system=SYSTEM)
    assert str(caught.value) == "the login must be a LoginStatus"


@pytest.mark.parametrize(
    "run", [tuple(PASS_RUN), list(PASS_RUN), WIRE, SESSION, MARKER, 0, False], ids=label
)
def test_a_run_of_another_form_is_refused(run):
    with pytest.raises(TypeError) as caught:
        build(LOGGED_IN, run, system=SYSTEM)
    assert str(caught.value) == "the run must be a SessionRun or None"


@pytest.mark.parametrize(
    "system", [None, tuple(SYSTEM), (MARKER, MARKER, MARKER), MARKER, LOGGED_IN]
)
def test_system_facts_of_another_form_are_refused(system):
    with pytest.raises(TypeError) as caught:
        build(LOGGED_IN, PASS_RUN, system=system)
    assert str(caught.value) == "the system facts must be a SystemFacts"


@pytest.mark.parametrize(
    "login, run",
    [
        (NOT_IN, PASS_RUN),
        (LoginStatus(NO_CLAUDE, None, None, False), NOT_STARTED),
        (LoginStatus(LOGIN_UNREADABLE, None, 7, False), PASS_RUN),
        (LOGGED_IN, None),
    ],
)
def test_values_that_contradict_each_other_are_refused(login, run):
    with pytest.raises(ValueError) as caught:
        build(login, run, system=SYSTEM)
    assert str(caught.value) == ERROR_TEXTS[4]


@pytest.mark.parametrize(
    "outcome, error", [(MARKER, ValueError), ("passed", ValueError), (5, TypeError)]
)
@pytest.mark.parametrize("run", [None, PASS_RUN])
def test_a_login_outcome_of_another_form_is_refused_as_decide_does(outcome, error, run):
    with pytest.raises(error) as caught:
        build(LOGGED_IN._replace(outcome=outcome), run, system=SYSTEM)
    assert str(caught.value) in ERROR_TEXTS


@pytest.mark.parametrize(
    "run",
    [
        PASS_RUN._replace(session=tuple(SESSION)),
        PASS_RUN._replace(session=None),
        PASS_RUN._replace(session=SESSION._replace(exit_status=MARKER)),
        PASS_RUN._replace(session=SESSION._replace(started=MARKER)),
        PASS_RUN._replace(wire=tuple(WIRE)),
        PASS_RUN._replace(wire=MARKER),
        PASS_RUN._replace(wire=WIRE._replace(errors=[(MARKER, MARKER)])),
        PASS_RUN._replace(wire=WIRE._replace(unforeseen=[MARKER])),
        PASS_RUN._replace(wire=WIRE._replace(unforeseen=MARKER)),
        PASS_RUN._replace(stream=tuple(STREAM)),
        PASS_RUN._replace(stream=MARKER),
        PASS_RUN._replace(stream=SESSION),
        PASS_RUN._replace(stream=STREAM._replace(session_tools=[MARKER])),
        PASS_RUN._replace(stream=STREAM._replace(session_tools=MARKER)),
        PASS_RUN._replace(stream=STREAM._replace(session_tools=None)),
        PASS_RUN._replace(torn=MARKER),
        PASS_RUN._replace(torn=1),
        PASS_RUN._replace(torn=None),
    ],
    ids=label,
)
def test_a_run_whose_member_has_another_form_is_refused(run):
    with pytest.raises(TypeError) as caught:
        build(LOGGED_IN, run, system=SYSTEM)
    assert str(caught.value) in ERROR_TEXTS


@pytest.mark.parametrize("value", NOT_BOOLEANS, ids=label)
@pytest.mark.parametrize(
    "make",
    [
        lambda v: (LOGGED_IN._replace(timed_out=v), PASS_RUN),
        lambda v: (LOGGED_IN, PASS_RUN._replace(removed=v)),
        lambda v: (LOGGED_IN, with_wire(probe_seen=v)),
        lambda v: (LOGGED_IN, with_wire(probe_before_initialize=v)),
        lambda v: (LOGGED_IN, with_wire(token_call_requested=v)),
        lambda v: (LOGGED_IN, with_wire(fail_call_requested=v)),
        lambda v: (LOGGED_IN, with_wire(unforeseen_dropped=v)),
        lambda v: (LOGGED_IN, with_wire(reached=v)),
        lambda v: (LOGGED_IN, with_stream(session_tools_dropped=v)),
        lambda v: (LOGGED_IN, PASS_RUN._replace(session=SESSION._replace(init_read=v))),
    ],
)
def test_a_yes_or_no_value_of_another_form_is_refused(make, value):
    login, run = make(value)
    with pytest.raises(TypeError) as caught:
        build(login, run, system=SYSTEM)
    assert str(caught.value) == "a yes-or-no value must be True or False"


@pytest.mark.parametrize("value", NOT_INTEGERS, ids=label)
@pytest.mark.parametrize(
    "make",
    [
        lambda v: (LOGGED_IN._replace(returncode=v), PASS_RUN),
        lambda v: (LOGGED_IN, with_wire(probe_error=v)),
    ],
)
def test_an_integer_of_another_form_is_refused(make, value):
    login, run = make(value)
    with pytest.raises(TypeError) as caught:
        build(login, run, system=SYSTEM)
    assert str(caught.value) == "an integer value must be None or an integer"


def test_the_exit_statuses():
    assert selfcheck_report.EXIT_PASSED == 0
    values = {
        NO_CLAUDE: selfcheck_report.EXIT_NO_CLAUDE,
        NOT_LOGGED_IN: selfcheck_report.EXIT_NOT_LOGGED_IN,
        LOGIN_UNREADABLE: selfcheck_report.EXIT_LOGIN_UNREADABLE,
        FRONT_REFUSED: selfcheck_report.EXIT_FRONT_REFUSED,
        PASSED: selfcheck_report.EXIT_PASSED,
        NO_CALL: selfcheck_report.EXIT_NO_CALL,
        SESSION_FAILED: selfcheck_report.EXIT_SESSION_FAILED,
    }
    assert set(values) == set(OUTCOMES)
    assert [values[word] for word in OUTCOMES] == [10, 11, 12, 13, 0, 14, 15]
    for word in OUTCOMES:
        status = exit_status(word)
        assert type(status) is int and status == values[word]
        assert (status == 0) == (word == PASSED)
        assert status not in (1, 2, 3, 4, 120) and status < 126


@pytest.mark.parametrize(
    "outcome", ["", "PASSED", " passed", "passed\n", "pass", MARKER], ids=label
)
def test_a_word_that_is_no_outcome_has_no_exit_status(outcome):
    with pytest.raises(ValueError) as caught:
        exit_status(outcome)
    assert str(caught.value) == "the outcome must be a word of the closed list"


@pytest.mark.parametrize(
    "outcome", [None, 0, True, False, b"passed", ["passed"], ("passed",), Verdict]
)
def test_a_value_that_is_no_string_has_no_exit_status(outcome):
    with pytest.raises(TypeError) as caught:
        exit_status(outcome)
    assert str(caught.value) == "the outcome must be a string"


def test_the_line_is_one_ascii_line_whatever_the_dict_holds():
    data = line({"a": "caf\u00e9\r\n\u2028", "b": [1, None, True]})
    assert data == b'{"a":"caf\\u00e9\\r\\n\\u2028","b":[1,null,true]}\n'
    assert line({}) == b"{}\n"


@pytest.mark.parametrize(
    "report",
    [
        None,
        MARKER,
        b"{}",
        [],
        [("outcome", PASSED)],
        (),
        0,
        {"a": {MARKER}},
        {"a": object()},
        {"a": float("nan")},
        {"a": float("inf")},
        {"a": b"bytes"},
        {(MARKER, 1): 1},
    ],
    ids=label,
)
def test_a_report_of_another_form_is_refused(report):
    with pytest.raises(TypeError) as caught:
        line(report)
    assert str(caught.value) == "the report must be a dict that build returned"


def test_a_report_nested_too_deeply_is_refused():
    report = {}
    for _ in range(100000):
        report = {"a": report}
    with pytest.raises(TypeError) as caught:
        line(report)
    assert str(caught.value) == "the report must be a dict that build returned"


def test_no_error_text_holds_a_planted_value():
    assert all(MARKER not in text for text in ERROR_TEXTS)
