import io
import itertools
import json
import random

import pytest

from hilclaw import selfcheck_login, selfcheck_outcome, selfcheck_server, selfcheck_wire
from hilclaw.selfcheck_outcome import (
    CONNECTED,
    FRONT_REFUSED,
    NO_CALL,
    OUTCOMES,
    PASSED,
    REFUSED_STATUS_WORDS,
    SESSION_FAILED,
    SessionEvidence,
    Verdict,
    decide,
)
from hilclaw.selfcheck_wire import FAIL_TOOL_NAME, TOKEN_TOOL_NAME, WireFacts

TOKEN = "0123456789abcdef0123456789abcdef"
FAIL_TOKEN = "fedcba9876543210fedcba9876543210"
MARKER = "marker-3f9c"
COUNTER = itertools.count()
LOGIN_WORDS = (
    selfcheck_login.NO_CLAUDE,
    selfcheck_login.NOT_LOGGED_IN,
    selfcheck_login.LOGIN_UNREADABLE,
)
ERROR_TEXTS = (
    "the login outcome must be None or a string",
    "the login outcome must be None or a word of step one",
    "the session evidence must be a SessionEvidence",
    "the wire facts must be a WireFacts or None",
    "the errors of the wire facts must be a tuple",
    "a yes-or-no value must be True or False",
    "the exit status must be None or an integer",
)
SESSION = SessionEvidence(
    started=True,
    timed_out=False,
    exit_status=0,
    init_read=True,
    server_status="connected",
    server_in_errors=False,
    any_config_error=False,
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
A_ERRORS = [
    (-32602, "initialize"),
    (-32602, "ping"),
    (-32602, "tools/list"),
    (-32602, "tools/call"),
    (-32603, "tools/call"),
    (-32600, None),
    (-32600, "ping"),
    (-32700, None),
]
SESSION_FLAGS = [
    "started",
    "timed_out",
    "init_read",
    "server_in_errors",
    "any_config_error",
    "token_tool_listed",
    "fail_tool_listed",
    "result_read",
    "token_in_reply",
    "fail_token_in_reply",
]
WIRE_FLAGS = [
    "reached",
    "initialize_answered",
    "list_after_initialize",
    "list_answered",
    "list_both_tools",
    "token_call_answered",
    "fail_call_answered",
    "unplaceable",
]
NOT_BOOLEANS = [1, 0, "true", "", [True], [], None, 1.0, b"\x01", (True,)]
STATUS_VARIANTS = [
    "Connected",
    " connected",
    "connected\n",
    "connected ",
    "CONNECTED",
    b"connected",
    1,
    True,
    0.0,
    ["connected"],
    ("connected",),
    {"status": "connected"},
]
REFUSING_VARIANTS = [
    "Failed",
    " failed",
    "failed\n",
    b"failed",
    0,
    False,
    ["failed"],
    ("failed",),
]


def message(**members):
    return json.dumps({"jsonrpc": "2.0", **members}).encode() + b"\n"


def request(request_id, method, params=None):
    members = {"id": request_id, "method": method}
    if params is not None:
        members["params"] = params
    return message(**members)


INITIALIZE = request(
    1,
    "initialize",
    {"protocolVersion": "2025-11-25", "clientInfo": {"version": "2.1.280"}},
)
PROBE = request(
    "probe",
    "server/discover",
    {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28"}},
)
LIST = request(2, "tools/list")
CALL_TOKEN = request(3, "tools/call", {"name": TOKEN_TOOL_NAME})
CALL_FAIL = request(4, "tools/call", {"name": FAIL_TOOL_NAME})
CALL_UNKNOWN = request(5, "tools/call", {"name": "selfcheck_other"})


def served(tmp_path, *lines):
    """The copy of what the real front answered to ``lines``, in-process."""
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
    return selfcheck_wire.read(copy.lines), copy.torn


def session(**members):
    return SESSION._replace(**members)


def wire(**members):
    return WIRE._replace(**members)


def label(value):
    return ascii(value)[:24]


def by_record(login_outcome, evidence, facts, torn):
    """The row of ADR-0054 decision 6 for these arguments, and (a) and (b)."""
    if login_outcome is not None:
        return login_outcome, False, False
    facts = WireFacts() if facts is None else facts
    status = evidence.exit_status
    by_itself = evidence.started and not evidence.timed_out
    by_itself = by_itself and status is not None and status >= 0
    word = evidence.server_status
    a = b = False
    if evidence.started and facts.reached:
        a = len(facts.errors) > 0
        dropped = facts.initialize_answered and not facts.list_after_initialize
        named = evidence.server_in_errors or word not in (None, "failed")
        b = dropped and by_itself and evidence.init_read and not named
    if a or b:
        return "front_refused", a, b
    clean = by_itself and status == 0
    shown = evidence.init_read and word == "connected"
    names = evidence.token_tool_listed and evidence.fail_tool_listed
    calls = facts.token_call_answered and facts.fail_call_answered
    tokens = evidence.token_in_reply and evidence.fail_token_in_reply
    no_entry = not evidence.any_config_error and not evidence.server_in_errors
    listed = facts.initialize_answered and facts.list_answered
    listed = listed and facts.list_both_tools and facts.reached
    whole = not facts.unplaceable and not torn and not facts.errors
    model = names and calls and tokens
    read = evidence.result_read
    if clean and shown and no_entry and model and listed and read and whole:
        return "passed", False, False
    if clean and read and facts.reached and shown and not model:
        return "no_call", False, False
    return "session_failed", False, False


def test_the_outcomes_are_the_seven_of_the_record_in_its_order():
    assert OUTCOMES == (
        "no_claude",
        "not_logged_in",
        "login_unreadable",
        "front_refused",
        "passed",
        "no_call",
        "session_failed",
    )
    assert OUTCOMES[:3] == LOGIN_WORDS
    assert all(mine is theirs for mine, theirs in zip(OUTCOMES, LOGIN_WORDS))
    assert OUTCOMES[3:] == (FRONT_REFUSED, PASSED, NO_CALL, SESSION_FAILED)


def test_the_status_words():
    assert CONNECTED == "connected"
    assert REFUSED_STATUS_WORDS == ("failed",)
    assert type(REFUSED_STATUS_WORDS) is tuple


def test_no_evidence_is_no_session_started():
    assert SessionEvidence() == SessionEvidence(
        *(False, False, None, False, None, False, False),
        *(False, False, False, False, False),
    )
    assert Verdict(PASSED) == Verdict(PASSED, False, False)
    assert decide(None, SessionEvidence(), None) == Verdict(SESSION_FAILED)
    assert decide(None, SessionEvidence(), WireFacts()) == Verdict(SESSION_FAILED)


def test_the_module_names_no_source_of_the_evidence():
    names = dir(selfcheck_outcome) + list(SessionEvidence._fields)
    names += list(Verdict._fields)
    values = [value for value in vars(selfcheck_outcome).values() if type(value) is str]
    for word in ("mcp__", "mcp_servers", "mcp_server_errors", "is_error", "subtype"):
        assert not any(word in name for name in names)
        assert word not in values


def test_walk_through_2_a_pass(tmp_path):
    facts, torn = served(tmp_path, PROBE, INITIALIZE, LIST, CALL_TOKEN, CALL_FAIL)
    assert facts == WIRE and torn is False
    assert decide(None, SESSION, facts, torn=torn) == Verdict(PASSED, False, False)
    assert decide(None, SESSION, WIRE) == Verdict(PASSED)


def test_walk_through_1_not_logged_in_whatever_else_holds():
    expected = Verdict(selfcheck_login.NOT_LOGGED_IN)
    assert decide(selfcheck_login.NOT_LOGGED_IN, SessionEvidence(), None) == expected
    assert decide(selfcheck_login.NOT_LOGGED_IN, SESSION, WIRE) == expected
    refused = wire(errors=((-32602, "tools/call"),))
    assert decide(selfcheck_login.NOT_LOGGED_IN, SESSION, refused) == expected
    assert decide(selfcheck_login.NOT_LOGGED_IN, SESSION, WIRE, torn=True) == expected


@pytest.mark.parametrize("word", LOGIN_WORDS)
def test_a_word_of_step_one_is_the_outcome_as_it_is(word):
    for evidence, facts in [
        (SESSION, WIRE),
        (SESSION, None),
        (SessionEvidence(), WIRE),
        (DROPPED_SESSION, DROPPED_WIRE),
        (session(exit_status=1), wire(errors=((-32700, None),))),
    ]:
        verdict = decide(word, evidence, facts)
        assert verdict == Verdict(word, False, False)
        assert verdict.outcome is word


def test_walk_through_3_the_model_calls_nothing(tmp_path):
    facts, torn = served(tmp_path, PROBE, INITIALIZE, LIST)
    evidence = session(token_in_reply=False, fail_token_in_reply=False)
    assert decide(None, evidence, facts, torn=torn) == Verdict(NO_CALL)


def test_walk_through_4_the_client_drops_the_server(tmp_path):
    facts, torn = served(tmp_path, PROBE, INITIALIZE)
    assert facts == DROPPED_WIRE._replace(
        probe_seen=True,
        probe_before_initialize=True,
        probe_revision="2026-07-28",
        probe_error=-32601,
    )
    refused = Verdict(FRONT_REFUSED, False, True)
    assert decide(None, DROPPED_SESSION, facts, torn=torn) == refused
    named = DROPPED_SESSION._replace(server_status="failed")
    assert decide(None, named, facts, torn=torn) == refused
    other = DROPPED_SESSION._replace(server_status="disabled")
    assert decide(None, other, facts, torn=torn) == Verdict(SESSION_FAILED)
    never, torn = served(tmp_path, PROBE)
    assert never.reached is False
    assert decide(None, DROPPED_SESSION, never, torn=torn) == Verdict(SESSION_FAILED)
    assert decide(None, named, never, torn=torn) == Verdict(SESSION_FAILED)


def test_walk_through_5_a_non_zero_exit_status():
    assert decide(None, session(exit_status=1), WIRE) == Verdict(SESSION_FAILED)
    assert decide(None, session(exit_status=1), None) == Verdict(SESSION_FAILED)
    refused = wire(errors=((-32602, "initialize"),))
    assert decide(None, session(exit_status=1), refused) == (
        Verdict(FRONT_REFUSED, True, False)
    )


@pytest.mark.parametrize("error", A_ERRORS, ids=label)
def test_condition_a_by_each_error_the_facts_can_carry(error):
    assert decide(None, SESSION, wire(errors=(error,))) == (
        Verdict(FRONT_REFUSED, True, False)
    )


def test_condition_a_by_an_unknown_tool_name_as_the_record_is_written(tmp_path):
    facts, torn = served(
        tmp_path, INITIALIZE, LIST, CALL_TOKEN, CALL_FAIL, CALL_UNKNOWN
    )
    assert facts.errors == ((-32602, "tools/call"),)
    assert facts._replace(errors=()) == wire(
        probe_seen=False,
        probe_before_initialize=False,
        probe_revision=None,
        probe_error=None,
    )
    assert decide(None, SESSION, facts, torn=torn) == Verdict(
        FRONT_REFUSED, True, False
    )


@pytest.mark.parametrize(
    "members",
    [
        {"timed_out": True, "exit_status": None},
        {"exit_status": 1},
        {"exit_status": -9},
        {"exit_status": None},
        {"init_read": False, "server_status": None},
        {"server_status": "pending"},
        {"server_in_errors": True, "any_config_error": True},
        {"result_read": False},
    ],
    ids=label,
)
def test_condition_a_asks_nothing_of_how_the_session_ended(members):
    refused = wire(errors=((-32600, None), (-32602, "tools/list")))
    assert decide(None, session(**members), refused) == (
        Verdict(FRONT_REFUSED, True, False)
    )
    assert decide(None, session(**members), refused, torn=True) == (
        Verdict(FRONT_REFUSED, True, False)
    )
    assert decide(None, session(**members), refused._replace(unplaceable=True)) == (
        Verdict(FRONT_REFUSED, True, False)
    )


def test_conditions_a_and_b_can_both_hold():
    both = DROPPED_WIRE._replace(errors=((-32602, "ping"),))
    assert decide(None, DROPPED_SESSION, both) == Verdict(FRONT_REFUSED, True, True)
    assert decide(None, DROPPED_SESSION, DROPPED_WIRE) == (
        Verdict(FRONT_REFUSED, False, True)
    )
    failed = DROPPED_SESSION._replace(server_status=REFUSED_STATUS_WORDS[0])
    assert decide(None, failed, both) == Verdict(FRONT_REFUSED, True, True)


@pytest.mark.parametrize("status", [0, 1, 2, 137, 255, 3221225786])
def test_condition_b_asks_no_exit_status_of_zero(status):
    evidence = DROPPED_SESSION._replace(exit_status=status)
    assert decide(None, evidence, DROPPED_WIRE) == Verdict(FRONT_REFUSED, False, True)


@pytest.mark.parametrize("torn", [False, True])
@pytest.mark.parametrize("unplaceable", [False, True])
def test_condition_b_stands_in_a_torn_or_unplaceable_copy(torn, unplaceable):
    facts = DROPPED_WIRE._replace(unplaceable=unplaceable)
    assert decide(None, DROPPED_SESSION, facts, torn=torn) == (
        Verdict(FRONT_REFUSED, False, True)
    )


@pytest.mark.parametrize(
    "evidence",
    [
        {"timed_out": True},
        {"timed_out": True, "exit_status": None},
        {"exit_status": None},
        {"exit_status": -1},
        {"exit_status": -15},
        {"init_read": False},
        {"server_status": "pending"},
        {"server_status": "needs-auth"},
        {"server_status": ""},
        {"server_in_errors": True},
        {"server_in_errors": True, "any_config_error": True},
        {"server_status": "failed", "server_in_errors": True},
    ],
    ids=label,
)
def test_condition_b_fails_on_each_session_part(evidence):
    evidence = DROPPED_SESSION._replace(**evidence)
    assert decide(None, evidence, DROPPED_WIRE) == Verdict(SESSION_FAILED)


@pytest.mark.parametrize(
    "facts",
    [
        {"list_after_initialize": True, "list_requested": True},
        {"initialize_answered": False},
        {"reached": False},
    ],
    ids=label,
)
def test_condition_b_fails_on_each_wire_part(facts):
    facts = DROPPED_WIRE._replace(**facts)
    assert decide(None, DROPPED_SESSION, facts) == Verdict(SESSION_FAILED)
    failed = DROPPED_SESSION._replace(server_status="failed")
    assert decide(None, failed, facts) == Verdict(SESSION_FAILED)
    assert decide(None, DROPPED_SESSION, None) == Verdict(SESSION_FAILED)


def test_a_dropped_server_shown_as_connected_is_no_call():
    evidence = DROPPED_SESSION._replace(server_status="connected")
    assert decide(None, evidence, DROPPED_WIRE) == Verdict(NO_CALL)
    assert decide(None, evidence._replace(result_read=False), DROPPED_WIRE) == (
        Verdict(SESSION_FAILED)
    )


def test_a_list_request_before_initialize_only_is_no_list_after_it():
    facts = DROPPED_WIRE._replace(list_requested=True, list_answered=True)
    assert decide(None, DROPPED_SESSION, facts) == Verdict(FRONT_REFUSED, False, True)


def test_an_entry_for_another_server_does_not_undo_condition_b():
    evidence = DROPPED_SESSION._replace(any_config_error=True)
    assert decide(None, evidence, DROPPED_WIRE) == Verdict(FRONT_REFUSED, False, True)


@pytest.mark.parametrize("errors", [((-32602, "tools/call"),), ()])
def test_no_session_started_is_never_front_refused(errors):
    for evidence in [
        SessionEvidence(),
        session(started=False),
        DROPPED_SESSION._replace(started=False),
    ]:
        for facts in [wire(errors=errors), DROPPED_WIRE._replace(errors=errors)]:
            assert decide(None, evidence, facts) == Verdict(SESSION_FAILED)


def test_a_server_not_reached_is_never_front_refused():
    errors = ((-32700, None), (-32600, None))
    for evidence in [SESSION, DROPPED_SESSION, session(exit_status=1)]:
        for facts in [
            WireFacts(errors=errors),
            wire(reached=False, errors=errors),
            DROPPED_WIRE._replace(reached=False),
        ]:
            assert decide(None, evidence, facts) == Verdict(SESSION_FAILED)


@pytest.mark.parametrize(
    ("evidence", "facts", "torn", "outcome"),
    [
        ({"token_in_reply": False}, {}, False, NO_CALL),
        ({"fail_token_in_reply": False}, {}, False, NO_CALL),
        ({"token_tool_listed": False}, {}, False, NO_CALL),
        ({"fail_tool_listed": False}, {}, False, NO_CALL),
        ({}, {"token_call_answered": False}, False, NO_CALL),
        ({}, {"fail_call_answered": False}, False, NO_CALL),
        ({}, {"token_call_answered": False, "token_call_requested": False}, 0, NO_CALL),
        ({"result_read": False}, {}, False, SESSION_FAILED),
        ({"exit_status": 1}, {}, False, SESSION_FAILED),
        ({"exit_status": -9}, {}, False, SESSION_FAILED),
        ({"exit_status": None}, {}, False, SESSION_FAILED),
        ({"timed_out": True}, {}, False, SESSION_FAILED),
        ({"timed_out": True, "exit_status": None}, {}, False, SESSION_FAILED),
        ({"started": False}, {}, False, SESSION_FAILED),
        ({"init_read": False}, {}, False, SESSION_FAILED),
        ({"server_status": "pending"}, {}, False, SESSION_FAILED),
        ({"server_status": "failed"}, {}, False, SESSION_FAILED),
        ({"server_status": None}, {}, False, SESSION_FAILED),
        ({"any_config_error": True}, {}, False, SESSION_FAILED),
        ({"server_in_errors": True}, {}, False, SESSION_FAILED),
        ({"server_in_errors": True, "any_config_error": True}, {}, 0, SESSION_FAILED),
        ({}, {"list_answered": False}, False, SESSION_FAILED),
        ({}, {"list_both_tools": False}, False, SESSION_FAILED),
        ({}, {"initialize_answered": False}, False, SESSION_FAILED),
        ({}, {"reached": False}, False, SESSION_FAILED),
        ({}, {"unplaceable": True}, False, SESSION_FAILED),
        ({}, {}, True, SESSION_FAILED),
        ({}, {"unplaceable": True}, True, SESSION_FAILED),
        ({}, None, False, SESSION_FAILED),
        ({}, None, True, SESSION_FAILED),
        ({}, {"errors": ((-32602, "tools/call"),)}, False, FRONT_REFUSED),
    ],
    ids=label,
)
def test_passed_without_one_condition_falls_to_its_neighbour(
    evidence, facts, torn, outcome
):
    facts = None if facts is None else wire(**facts)
    verdict = decide(None, session(**evidence), facts, torn=bool(torn))
    assert verdict.outcome == outcome
    assert verdict.refused_b is False
    assert verdict.refused_a is (outcome == FRONT_REFUSED)


def test_only_the_members_the_rows_read_decide_a_pass():
    plain = wire(
        client_version=None,
        revision_asked="other",
        revision_answered=None,
        probe_seen=False,
        probe_before_initialize=False,
        probe_revision=None,
        probe_error=None,
        list_requested=False,
        token_call_requested=False,
        fail_call_requested=False,
        errors_dropped=True,
        unforeseen=("sampling/createMessage",),
        unforeseen_dropped=True,
    )
    assert decide(None, SESSION, plain) == Verdict(PASSED)


@pytest.mark.parametrize(
    ("evidence", "facts", "torn"),
    [
        ({"token_in_reply": False}, {}, True),
        ({"token_in_reply": False}, {"unplaceable": True}, False),
        ({}, {"fail_call_answered": False, "unplaceable": True}, True),
        ({"fail_tool_listed": False}, {"list_answered": False}, False),
        ({"fail_tool_listed": False}, {"list_both_tools": False}, False),
        ({"token_in_reply": False}, {"initialize_answered": False}, False),
        ({"token_in_reply": False, "any_config_error": True}, {}, False),
        ({"token_in_reply": False, "server_in_errors": True}, {}, False),
        (
            {"token_tool_listed": False, "fail_tool_listed": False},
            {"token_call_answered": False, "fail_call_answered": False},
            False,
        ),
    ],
    ids=label,
)
def test_no_call_holds_whatever_else_passed_would_miss(evidence, facts, torn):
    verdict = decide(None, session(**evidence), wire(**facts), torn=torn)
    assert verdict == Verdict(NO_CALL)


@pytest.mark.parametrize(
    ("evidence", "facts"),
    [
        ({"result_read": False}, {}),
        ({"exit_status": 1}, {}),
        ({"exit_status": -2}, {}),
        ({"timed_out": True}, {}),
        ({"init_read": False}, {}),
        ({"server_status": "pending"}, {}),
        ({"server_status": None}, {}),
        ({"started": False}, {}),
        ({}, {"reached": False}),
        ({}, None),
    ],
    ids=label,
)
def test_no_call_fails_on_each_of_its_own_parts(evidence, facts):
    evidence = session(token_in_reply=False, **evidence)
    facts = None if facts is None else wire(token_call_answered=False, **facts)
    assert decide(None, evidence, facts) == Verdict(SESSION_FAILED)


def sample(rng, likely):
    def flag(passing):
        return passing if rng.random() < likely else not passing

    evidence = SessionEvidence(
        started=flag(True),
        timed_out=flag(False),
        exit_status=0 if rng.random() < likely else rng.choice([None, 1, -9, 2]),
        init_read=flag(True),
        server_status=(
            "connected"
            if rng.random() < likely
            else rng.choice([None, "failed", "pending", "disabled"])
        ),
        server_in_errors=flag(False),
        any_config_error=flag(False),
        token_tool_listed=flag(True),
        fail_tool_listed=flag(True),
        result_read=flag(True),
        token_in_reply=flag(True),
        fail_token_in_reply=flag(True),
    )
    if rng.random() >= likely:
        return evidence, None, flag(False)
    facts = WireFacts(
        reached=flag(True),
        initialize_answered=flag(True),
        list_after_initialize=flag(True),
        list_answered=flag(True),
        list_both_tools=flag(True),
        token_call_answered=flag(True),
        fail_call_answered=flag(True),
        errors=() if rng.random() < likely else (rng.choice(A_ERRORS),),
        unplaceable=flag(False),
    )
    return evidence, facts, flag(False)


@pytest.mark.parametrize(
    ("likely", "count"), [(0.93, 30000), (0.75, 30000), (0.5, 30000)]
)
def test_nothing_but_every_condition_of_the_row_passes(likely, count):
    rng = random.Random(163)
    seen = dict.fromkeys(OUTCOMES, 0)
    for _ in range(count):
        evidence, facts, torn = sample(rng, likely)
        verdict = decide(None, evidence, facts, torn=torn)
        assert tuple(verdict) == by_record(None, evidence, facts, torn)
        assert verdict.outcome in OUTCOMES[3:]
        seen[verdict.outcome] += 1
        if verdict.outcome == PASSED:
            assert facts is not None and torn is False
            assert evidence[:4] == (True, False, 0, True)
            assert evidence[4:] == (
                "connected",
                False,
                False,
                True,
                True,
                True,
                True,
                True,
            )
            assert facts.errors == () and facts.unplaceable is False
            assert all(
                getattr(facts, name) is True
                for name in WIRE_FLAGS
                if name not in ("list_after_initialize", "unplaceable")
            )
        for word in LOGIN_WORDS:
            assert decide(word, evidence, facts, torn=torn) == Verdict(word)
    assert all(seen[outcome] > 0 for outcome in OUTCOMES[3:] if outcome != PASSED)
    assert seen[PASSED] > 0 or likely < 0.6
    assert sum(seen.values()) == count


def test_every_pair_of_missing_conditions_is_no_pass():
    changes = [("session", name) for name in SESSION_FLAGS]
    changes += [
        ("wire", name) for name in WIRE_FLAGS if name != "list_after_initialize"
    ]
    changes += [("torn", None), ("status", None), ("exit", None), ("errors", None)]
    for picked in itertools.chain(
        itertools.combinations(changes, 1), itertools.combinations(changes, 2)
    ):
        evidence, facts, torn = SESSION, WIRE, False
        for kind, name in picked:
            if kind == "session":
                evidence = evidence._replace(**{name: not getattr(SESSION, name)})
            elif kind == "wire":
                facts = facts._replace(**{name: not getattr(WIRE, name)})
            elif kind == "status":
                evidence = evidence._replace(server_status="pending")
            elif kind == "exit":
                evidence = evidence._replace(exit_status=1)
            elif kind == "errors":
                facts = facts._replace(errors=((-32602, "tools/list"),))
            else:
                torn = True
        verdict = decide(None, evidence, facts, torn=torn)
        assert verdict.outcome != PASSED
        assert tuple(verdict) == by_record(None, evidence, facts, torn)


@pytest.mark.parametrize(
    "login_outcome",
    ["logged_in", "passed", "front_refused", "", "NOT_LOGGED_IN", " no_claude", MARKER],
    ids=label,
)
def test_an_unknown_login_word_is_refused(login_outcome):
    with pytest.raises(ValueError) as caught:
        decide(login_outcome, SESSION, WIRE)
    assert str(caught.value) == ERROR_TEXTS[1]


@pytest.mark.parametrize(
    "login_outcome",
    [True, False, 0, 1, 1.5, b"no_claude", ["no_claude"], ("not_logged_in",), {}],
    ids=label,
)
def test_a_login_outcome_of_another_type_is_refused(login_outcome):
    with pytest.raises(TypeError) as caught:
        decide(login_outcome, SESSION, WIRE)
    assert str(caught.value) == ERROR_TEXTS[0]


def test_a_login_status_is_not_its_outcome():
    status = selfcheck_login.LoginStatus(None, "claude.ai", 0, False)
    with pytest.raises(TypeError) as caught:
        decide(status, SESSION, WIRE)
    assert str(caught.value) == ERROR_TEXTS[0]
    assert decide(status.outcome, SESSION, WIRE) == Verdict(PASSED)


@pytest.mark.parametrize(
    "facts",
    [
        tuple(WIRE),
        list(WIRE),
        WIRE._asdict(),
        selfcheck_server.WireCopy((), False),
        (),
        True,
        MARKER,
        type("Facts", (WireFacts,), {})(*WIRE),
    ],
    ids=label,
)
def test_wire_facts_of_another_type_are_refused(facts):
    for login_outcome in (None, selfcheck_login.NOT_LOGGED_IN):
        with pytest.raises(TypeError) as caught:
            decide(login_outcome, SESSION, facts)
        assert str(caught.value) == ERROR_TEXTS[3]
        assert MARKER not in str(caught.value)


@pytest.mark.parametrize(
    "evidence",
    [
        tuple(SESSION),
        list(SESSION),
        SESSION._asdict(),
        None,
        True,
        MARKER,
        WIRE,
        type("Evidence", (SessionEvidence,), {})(*SESSION),
    ],
    ids=label,
)
def test_session_evidence_of_another_type_is_refused(evidence):
    for login_outcome in (None, selfcheck_login.NO_CLAUDE):
        with pytest.raises(TypeError) as caught:
            decide(login_outcome, evidence, WIRE)
        assert str(caught.value) == ERROR_TEXTS[2]


@pytest.mark.parametrize("value", NOT_BOOLEANS, ids=label)
def test_a_value_that_is_not_a_boolean_never_reads_as_one(value):
    for name in SESSION_FLAGS:
        with pytest.raises(TypeError) as caught:
            decide(None, session(**{name: value}), WIRE)
        assert str(caught.value) == ERROR_TEXTS[5]
    for name in WIRE_FLAGS:
        with pytest.raises(TypeError) as caught:
            decide(None, SESSION, wire(**{name: value}))
        assert str(caught.value) == ERROR_TEXTS[5]
    with pytest.raises(TypeError) as caught:
        decide(None, SESSION, WIRE, torn=value)
    assert str(caught.value) == ERROR_TEXTS[5]
    with pytest.raises(TypeError) as caught:
        decide(selfcheck_login.NOT_LOGGED_IN, SessionEvidence(started=value), None)
    assert str(caught.value) == ERROR_TEXTS[5]


@pytest.mark.parametrize(
    "errors", [[], [(-32602, "ping")], None, False, True, 0, "", MARKER], ids=label
)
def test_errors_that_are_no_tuple_are_refused(errors):
    with pytest.raises(TypeError) as caught:
        decide(None, SESSION, wire(errors=errors))
    assert str(caught.value) == ERROR_TEXTS[4]


@pytest.mark.parametrize(
    "status", [True, False, 0.0, 1.0, "0", b"0", [0], (0,), MARKER], ids=label
)
def test_an_exit_status_that_is_no_integer_is_not_exit_status_0(status):
    for evidence in (session(exit_status=status), SessionEvidence(exit_status=status)):
        with pytest.raises(TypeError) as caught:
            decide(None, evidence, WIRE)
        assert str(caught.value) == ERROR_TEXTS[6]


@pytest.mark.parametrize("word", STATUS_VARIANTS, ids=label)
def test_a_status_word_that_is_not_exactly_connected(word):
    assert decide(None, session(server_status=word), WIRE) == Verdict(SESSION_FAILED)
    missing = session(server_status=word, token_in_reply=False)
    assert decide(None, missing, WIRE) == Verdict(SESSION_FAILED)
    dropped = DROPPED_SESSION._replace(server_status=word)
    assert decide(None, dropped, DROPPED_WIRE) == Verdict(SESSION_FAILED)


@pytest.mark.parametrize("word", REFUSING_VARIANTS, ids=label)
def test_a_status_word_that_is_not_exactly_of_the_list(word):
    dropped = DROPPED_SESSION._replace(server_status=word)
    assert decide(None, dropped, DROPPED_WIRE) == Verdict(SESSION_FAILED)


def test_every_message_is_a_fixed_text():
    refused = [
        (MARKER, SESSION, WIRE, False),
        ([MARKER], SESSION, WIRE, False),
        (None, MARKER, WIRE, False),
        (None, SESSION, MARKER, False),
        (None, SESSION, wire(errors=[MARKER]), False),
        (None, session(started=MARKER), WIRE, False),
        (None, SESSION, wire(reached=MARKER), False),
        (None, SESSION, WIRE, MARKER),
        (None, session(exit_status=MARKER), WIRE, False),
    ]
    texts = set()
    for login_outcome, evidence, facts, torn in refused:
        with pytest.raises((TypeError, ValueError)) as caught:
            decide(login_outcome, evidence, facts, torn=torn)
        assert str(caught.value) in ERROR_TEXTS
        assert MARKER not in repr(caught.value)
        texts.add(str(caught.value))
    assert texts == set(ERROR_TEXTS)


def test_the_same_arguments_give_equal_values():
    for login_outcome, evidence, facts, torn in [
        (None, SESSION, WIRE, False),
        (None, DROPPED_SESSION, DROPPED_WIRE, True),
        (selfcheck_login.LOGIN_UNREADABLE, SessionEvidence(), None, False),
        (None, session(token_in_reply=False), WIRE, False),
        (None, session(exit_status=3), None, False),
    ]:
        first = decide(login_outcome, evidence, facts, torn=torn)
        second = decide(login_outcome, evidence, facts, torn=torn)
        assert first == second and hash(first) == hash(second)
        assert (evidence, facts) == (evidence._replace(), facts and facts._replace())


def test_the_value_holds_an_outcome_and_two_booleans_and_no_status_word():
    cases = [
        (SESSION, WIRE, PASSED),
        (session(token_in_reply=False), WIRE, NO_CALL),
        (DROPPED_SESSION, DROPPED_WIRE, FRONT_REFUSED),
        (session(), wire(list_answered=False), SESSION_FAILED),
    ]
    for evidence, facts, outcome in cases:
        verdict = decide(None, evidence, facts)
        assert verdict.outcome == outcome
        assert Verdict._fields == ("outcome", "refused_a", "refused_b")
        assert [type(member) for member in verdict] == [str, bool, bool]
        hash(verdict)
    for word in (MARKER, "pending", "disabled", [MARKER]):
        for evidence in (session(server_status=word), DROPPED_SESSION):
            verdict = decide(None, evidence._replace(server_status=word), WIRE)
            assert verdict == Verdict(SESSION_FAILED)
            assert "marker" not in repr(verdict) and "pending" not in repr(verdict)
    failed = DROPPED_SESSION._replace(server_status="failed")
    assert repr(decide(None, failed, DROPPED_WIRE)) == (
        "Verdict(outcome='front_refused', refused_a=False, refused_b=True)"
    )
    assert "connected" not in repr(decide(None, SESSION, WIRE))
