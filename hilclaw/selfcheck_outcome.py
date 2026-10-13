"""The outcome table of the runtime self-check (ADR-0054 decision 6).

Renders "The outcomes - a closed list of seven; a check ends in exactly one".
:func:`decide` takes values that somebody else already read - the outcome of
step one, a :class:`SessionEvidence`, the :class:`hilclaw.selfcheck_wire.WireFacts`
of the wire copy and whether that copy was torn - and returns one
:class:`Verdict`. It is pure: the same arguments give the same value, and it
reads no file, environment, clock or configuration, starts no process, keeps
no state and prints nothing.

**The rows**, in the order of :data:`OUTCOMES`. The first row whose condition
holds, read from the top, is the outcome; the last one holds for everything.
``s`` is the session evidence, ``w`` the wire facts.

1. to 3. :data:`hilclaw.selfcheck_login.NO_CLAUDE`, ``NOT_LOGGED_IN``,
   ``LOGIN_UNREADABLE``: ``login_outcome`` is that word. It is returned as it
   is, whatever the other arguments hold.
4. :data:`FRONT_REFUSED`: ``s.started and w.reached`` and one of

   - (a) ``w.errors`` is not empty;
   - (b) ``w.initialize_answered and not w.list_after_initialize``, the session
     *ended by itself*, ``s.init_read``, ``not s.server_in_errors`` and
     ``s.server_status`` is ``None`` or a word of
     :data:`REFUSED_STATUS_WORDS`.

   (a) asks nothing of how the session ended.
5. :data:`PASSED`: the session ended by itself with ``s.exit_status == 0``;
   ``s.init_read`` and ``s.server_status`` is :data:`CONNECTED`; neither
   ``s.any_config_error`` nor ``s.server_in_errors``; *the model's part* (next
   row); ``s.result_read``; ``w.reached``, ``w.initialize_answered``,
   ``w.list_answered``, ``w.list_both_tools`` and no ``w.errors``; neither
   ``w.unplaceable`` nor ``torn``.
6. :data:`NO_CALL`: the session ended by itself with ``s.exit_status == 0``;
   ``s.init_read`` and ``s.server_status`` is :data:`CONNECTED`;
   ``s.result_read``; ``w.reached``; and the model's part does not hold. The
   model's part is all of ``s.token_tool_listed``, ``s.fail_tool_listed``,
   ``w.token_call_answered``, ``w.fail_call_answered``, ``s.token_in_reply``
   and ``s.fail_token_in_reply`` - the tool names, the calls and the tokens.
7. :data:`SESSION_FAILED`: every other case.

**The list of refusing status words** holds one word, ``failed``. A word enters
it only by a change of the record that names its page or its observation.

**Conventions of this module** (the record leaves them to the code):

- *Ended by itself*: ``s.started``, not ``s.timed_out`` and an exit status that
  is an integer of zero or more. A negative status is a signal on POSIX:
  something else ended the session. On Windows a kill has no sign, so a
  session another process ended reads there as ended by itself; whoever ends
  it for the time limit says so in ``timed_out``.
- *No wire copy*: ``wire`` is ``None`` when no readable copy exists - no file,
  or an error of its reader, which the caller catches. It is read as a copy
  that holds nothing, so rows 4 to 6 cannot hold; ``torn`` then says nothing.
- *A torn copy or one with an unplaceable line* is never :data:`PASSED`. What
  such a copy does establish stands: an error of condition (a) in it is still
  :data:`FRONT_REFUSED` and :data:`NO_CALL` can still hold. A session that
  lacks nothing else is :data:`SESSION_FAILED`: nothing of the names, the
  calls or the tokens is missing. The other reading, that such a copy
  establishes nothing, was not taken: the whole records before a cut are the
  entry's own, and an unplaceable line is never read as an answer or an error.
  An unplaceable line leaves the request before it unanswered, so a call that
  was made can read as missing.
- *The server named with a refusing word and also among the errors*: the entry
  among the errors wins, so not (b). An entry for another server
  (``s.any_config_error`` alone) does not undo (b): the row and row 7 speak of
  an entry that names the server of the check.
- *No server error entry* of row 5 is no entry at all, for any server. Row 6
  does not ask it: an entry does not keep a session from :data:`NO_CALL` when
  the condition of that row holds.
- *The errors of the wire facts* are counted, not read: any item of
  ``w.errors`` is an error of condition (a).
- *The reply* is the text of the ``result`` message, so row 5 needs
  ``s.result_read`` as well as both token facts.
- *Arguments that contradict each other* are not cross-checked: the table is
  applied as it stands. Row 5 asks ``w.reached`` beside
  ``w.initialize_answered``, which facts read from a copy always give together.
- *The status word is compared exactly*: only a ``str`` equal to
  :data:`CONNECTED` is connected and only one equal to a word of the list
  refuses. Any other value but ``None``, a non-string included, is a word
  outside both. It is compared and never returned.
- *What is refused*, before any row is read, each with a fixed text that holds
  nothing of the argument: a ``login_outcome`` that is no string and not
  ``None`` (:class:`TypeError`) or another string (:class:`ValueError`); a
  ``session`` that is no :class:`SessionEvidence`; a ``wire`` that is neither
  ``None`` nor a ``WireFacts``; a yes-or-no member of either, or ``torn``, that
  is not exactly ``True`` or ``False``; ``w.errors`` that is no tuple; an exit
  status that is neither ``None`` nor an ``int`` (``True`` is none). Of the
  wire facts only the members the rows read are looked at. No default and no
  exception yields :data:`PASSED`.

Not done here: no process, no ``claude``, no file, no token, no reading of any
output, no report, no exit status of the check, and nothing about what round 0
does after an outcome.

Known limits. A pass is one observation (ADR-0054 L2). The function believes
its arguments, so whoever builds them decides the outcome (L6). A -32602
answered to a call of an unknown tool name, which the model may cause, is an
error of condition (a) and ends in :data:`FRONT_REFUSED`, as the record is
written. Nothing calls the module yet.
"""

from typing import NamedTuple

from hilclaw import selfcheck_login
from hilclaw.selfcheck_wire import WireFacts

FRONT_REFUSED = "front_refused"
PASSED = "passed"
NO_CALL = "no_call"
SESSION_FAILED = "session_failed"
OUTCOMES = (
    selfcheck_login.NO_CLAUDE,
    selfcheck_login.NOT_LOGGED_IN,
    selfcheck_login.LOGIN_UNREADABLE,
    FRONT_REFUSED,
    PASSED,
    NO_CALL,
    SESSION_FAILED,
)
CONNECTED = "connected"
REFUSED_STATUS_WORDS = ("failed",)

_WIRE_FLAGS = (
    "reached",
    "initialize_answered",
    "list_after_initialize",
    "list_answered",
    "list_both_tools",
    "token_call_answered",
    "fail_call_answered",
    "unplaceable",
)


class SessionEvidence(NamedTuple):
    """The session-side and model-side evidence of one check, as already read.

    ``SessionEvidence()`` is "no session was started".

    - ``started``: a session was started.
    - ``timed_out``: the time limit ended it.
    - ``exit_status``: its exit status, negative when a signal ended it on
      POSIX; ``None`` when it has none.
    - ``init_read``: its ``system/init`` event was read.
    - ``server_status``: the status word that event gives the server of the
      check among its servers; ``None`` when it does not name it there.
    - ``server_in_errors``: that event names the server of the check among its
      server errors.
    - ``any_config_error``: that event holds a server error, for any server.
    - ``token_tool_listed``, ``fail_tool_listed``: that event holds the name
      of that tool.
    - ``result_read``: the ``result`` message was read.
    - ``token_in_reply``, ``fail_token_in_reply``: the text the model wrote
      holds that token.
    """

    started: bool = False
    timed_out: bool = False
    exit_status: int | None = None
    init_read: bool = False
    server_status: str | None = None
    server_in_errors: bool = False
    any_config_error: bool = False
    token_tool_listed: bool = False
    fail_tool_listed: bool = False
    result_read: bool = False
    token_in_reply: bool = False
    fail_token_in_reply: bool = False


class Verdict(NamedTuple):
    """What :func:`decide` found.

    ``outcome`` is one of :data:`OUTCOMES`. ``refused_a`` and ``refused_b``
    say which of the two conditions of :data:`FRONT_REFUSED` held - both can -
    and are false for every other outcome.
    """

    outcome: str
    refused_a: bool = False
    refused_b: bool = False


_SESSION_FLAGS = tuple(
    name
    for name in SessionEvidence._fields
    if name not in ("exit_status", "server_status")
)


def _check(login_outcome, session, wire, torn):
    if login_outcome is not None:
        if type(login_outcome) is not str:
            raise TypeError("the login outcome must be None or a string")
        if login_outcome not in OUTCOMES[:3]:
            raise ValueError("the login outcome must be None or a word of step one")
    if type(session) is not SessionEvidence:
        raise TypeError("the session evidence must be a SessionEvidence")
    if wire is not None and type(wire) is not WireFacts:
        raise TypeError("the wire facts must be a WireFacts or None")
    flags = [torn] + [getattr(session, name) for name in _SESSION_FLAGS]
    if wire is not None:
        flags += [getattr(wire, name) for name in _WIRE_FLAGS]
        if type(wire.errors) is not tuple:
            raise TypeError("the errors of the wire facts must be a tuple")
    if any(type(flag) is not bool for flag in flags):
        raise TypeError("a yes-or-no value must be True or False")
    if session.exit_status is not None and type(session.exit_status) is not int:
        raise TypeError("the exit status must be None or an integer")


def decide(login_outcome, session, wire, *, torn=False):
    """Return the :class:`Verdict` of one check.

    ``login_outcome`` is the ``outcome`` of a
    :class:`hilclaw.selfcheck_login.LoginStatus`: ``None`` for "logged in",
    else one of the three words of step one. ``session`` is a
    :class:`SessionEvidence`. ``wire`` is the
    :class:`hilclaw.selfcheck_wire.WireFacts` of the wire copy, or ``None``
    when no readable copy exists. ``torn`` is the ``torn`` of that copy.

    Every argument of that form gives exactly one outcome. Raises
    :class:`TypeError` or :class:`ValueError` for an argument of another form,
    as the module docstring lists; the message holds nothing of the argument.
    """
    _check(login_outcome, session, wire, torn)
    if login_outcome is not None:
        return Verdict(login_outcome)
    facts = WireFacts() if wire is None else wire
    word = session.server_status
    known = type(word) is str
    status = session.exit_status
    ended = (
        session.started and not session.timed_out and status is not None and status >= 0
    )
    reached = session.started and facts.reached
    refused_a = reached and bool(facts.errors)
    refused_b = (
        reached
        and facts.initialize_answered
        and not facts.list_after_initialize
        and ended
        and session.init_read
        and not session.server_in_errors
        and (word is None or (known and word in REFUSED_STATUS_WORDS))
    )
    if refused_a or refused_b:
        return Verdict(FRONT_REFUSED, refused_a, refused_b)
    connected = (
        ended
        and status == 0
        and session.init_read
        and known
        and word == CONNECTED
        and session.result_read
        and facts.reached
    )
    model = (
        session.token_tool_listed
        and session.fail_tool_listed
        and facts.token_call_answered
        and facts.fail_call_answered
        and session.token_in_reply
        and session.fail_token_in_reply
    )
    if (
        connected
        and model
        and not session.any_config_error
        and not session.server_in_errors
        and facts.initialize_answered
        and facts.list_answered
        and facts.list_both_tools
        and not facts.errors
        and not facts.unplaceable
        and not torn
    ):
        return Verdict(PASSED)
    if connected and not model:
        return Verdict(NO_CALL)
    return Verdict(SESSION_FAILED)
