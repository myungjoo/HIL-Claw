"""The session's output of the runtime self-check, read as named facts (ADR-0054 decision 6).

Renders the session side and the model side of decision 6. :func:`read` takes
the bytes the session wrote on its standard output and the two tokens and
returns one :class:`StreamFacts`; :func:`evidence` takes those facts and how
the process ended and returns the
:class:`hilclaw.selfcheck_outcome.SessionEvidence` of a started session. Both
are pure: the same arguments give the same value, and they read no file,
environment, clock or configuration, start no process, keep no state and
print nothing.

**Where each member is read from.** The session side is read from the
``system/init`` event and from nowhere else: ``server_status`` from
:data:`SERVERS_KEY`, ``server_in_errors`` and ``any_config_error`` from
:data:`SERVER_ERRORS_KEY`, the two ``..._tool_listed`` and ``session_tools``
from :data:`TOOLS_KEY`. The model side is read from the reply text of the
``result`` message and from nowhere else: ``token_in_reply`` and
``fail_token_in_reply``. No other event and no other member is read.

**The names read from the output**, each one constant of this module. The
standing is the record's: *verified* = on a documentation page (K8), never
tried; *observed once* = one session that never reached the model (K9,
T-0106); *not verified* = on no page read.

- :data:`SERVERS_KEY` ``mcp_servers``, :data:`SERVER_NAME_KEY` ``name``,
  :data:`SERVER_STATUS_KEY` ``status``: verified.
- :data:`SERVER_ERRORS_KEY` ``mcp_server_errors``: verified, as is that the
  key is omitted when there are no errors. The form of an entry: not verified.
- :data:`TOOLS_KEY` ``tools``: observed once. Its form, taken as an array of
  strings: not verified.
- ``selfcheck_outcome.CONNECTED`` as a status word: observed once. The word of
  ``selfcheck_outcome.REFUSED_STATUS_WORDS`` as one: not verified.
- :data:`EVENT_KIND_KEY` ``type``, :data:`EVENT_SUBKIND_KEY` ``subtype``,
  :data:`INIT_KIND` ``system``, :data:`INIT_SUBKIND` ``init``,
  :data:`RESULT_KIND` ``result``, :data:`REPLY_KEY` ``result``: not verified,
  provisional.

Verified too: one JSON value per line, and that the last line is a ``result``
message. The provisional values are this module's guess and say nothing of
what Claude Code writes: how an event says that it is the ``system/init``
event, how a line says that it is the ``result`` message and which member of
it holds the final response text are runtime acceptance item (v) of ADR-0054.
**A wrong one costs a pass, never a false one**: with another name the stream
gives no ``init_read``, no ``result_read``, no listed tool or no token, which
:func:`hilclaw.selfcheck_outcome.decide` never reads as ``passed``. Condition
(b) of ``front_refused`` never holds without ``init_read`` and reads nothing
of the ``result`` message, so a wrong name of that message leaves it as it is.

**Conventions of this module** (the record leaves them to the code):

- *A line* ends with ``\\n``; the bytes after the last one are a line too. A
  line of spaces, tabs and carriage returns only is nothing. Every other line
  is decoded as strict UTF-8 and parsed as strict JSON, with that white space
  allowed around the value. A line that is not one JSON object establishes
  nothing: a byte order mark, invalid UTF-8, another JSON value, ``NaN`` or
  ``Infinity``, nesting too deep to parse, and an object at any depth with a
  member name twice (no single answer). Integers are not converted.
- *The* ``system/init`` *event* is the only line that says so. Two or more are
  an output the check cannot read, so ``init_read`` is false and nothing of
  the session side is read: the record speaks of one, two can contradict each
  other, and taking the first would be a choice between them no fact backs.
- *The* ``result`` *message* is the last line that is not blank, when it says
  so. One that another line follows is not it, and an output cut inside its
  last line has none. The reply text is read only when :data:`REPLY_KEY`
  holds a string.
- *The status word* that is carried is ``CONNECTED``, a word of
  ``REFUSED_STATUS_WORDS``, ``None`` or :data:`OTHER_STATUS`. ``None`` needs
  a ground: :data:`SERVERS_KEY` is an array, each entry an object with a
  string name, and none is named :data:`SERVER_NAME`. One entry of that name
  gives its status word when it is exactly one of the words above. Everything
  else is :data:`OTHER_STATUS`: the member absent or no array, an entry of
  another form, the server named twice, a status that is absent, no string
  or any other string. No string the session chose is carried.
- *The server errors*: :data:`SERVER_ERRORS_KEY` present with any value but
  an empty array sets ``any_config_error`` and, since the configuration file
  of the check names one server and nothing says how an entry names its
  server, ``server_in_errors`` as well. The two always agree here.
- *A tool is listed* when :data:`TOOLS_KEY` is an array that holds its exact
  session-side name as a string. ``session_tools`` holds the strings of that
  array that begin with :data:`TOOL_PREFIX`, each bounded as
  :mod:`hilclaw.selfcheck_wire` bounds a string (1 to ``MAX_STRING``
  characters of ASCII letters, digits, ``.``, ``_`` and ``-``, else ``OTHER``)
  and then each distinct value once, in the order first seen; at most
  ``MAX_LISTED`` are kept and ``session_tools_dropped`` says that a further
  distinct one was seen. It is a tuple of ``str``.
- *A token is looked for* as an exact substring of the reply text: no case
  folding, no trimming, no decoding beyond what JSON did.
- *What is refused*, each with a fixed text that holds nothing of the
  argument. By :func:`read`: an ``output`` that is not ``bytes`` and a token
  that is no ``str`` (:class:`TypeError`); a token that is not 32 lowercase
  hexadecimal characters, and two equal tokens (:class:`ValueError`). By
  :func:`evidence` (:class:`TypeError`): ``facts`` that is no
  :class:`StreamFacts` or holds a yes-or-no member of the evidence that is
  not exactly ``True`` or ``False`` or a status word other than the four
  above, a ``timed_out`` of another type than ``bool`` and an ``exit_status``
  that is neither ``None`` nor an ``int`` (``True`` is none).
  Nothing is raised for the content of the output. No default and no
  exception yields a listed tool, a token in the reply or a connected server.
- *A time limit together with an exit status* is handed on as given.

**What leaves the module**: booleans, the status word under its rule and the
bounded tool names. No line or fragment of one, no reply text, no token, no
model name and no path is in a value or in an exception.

Not done here: no process, no ``claude``, no file, no wire copy, no outcome,
no report, no exit status of the check. "No session was started" is
``SessionEvidence()``, which the caller makes.

Known limits. Whoever writes the output decides what is read (ADR-0054 L6). A
pass is one observation (L2). The tokens are found in whatever text the one
member holds: that it holds the model's own text and no tool result is not
shown here. How deep a line may nest before it is nothing is the
interpreter's limit. Nothing calls the module yet.
"""

import json
import re
from typing import NamedTuple

from hilclaw import selfcheck_outcome, selfcheck_wire

SERVER_NAME = "hilclaw"
TOOL_PREFIX = f"mcp__{SERVER_NAME}__"
TOKEN_TOOL_SESSION_NAME = TOOL_PREFIX + selfcheck_wire.TOKEN_TOOL_NAME
FAIL_TOOL_SESSION_NAME = TOOL_PREFIX + selfcheck_wire.FAIL_TOOL_NAME
OTHER_STATUS = selfcheck_wire.OTHER

SERVERS_KEY = "mcp_servers"
SERVER_NAME_KEY = "name"
SERVER_STATUS_KEY = "status"
SERVER_ERRORS_KEY = "mcp_server_errors"
TOOLS_KEY = "tools"
EVENT_KIND_KEY = "type"
EVENT_SUBKIND_KEY = "subtype"
INIT_KIND = "system"
INIT_SUBKIND = "init"
RESULT_KIND = "result"
REPLY_KEY = "result"

_TOKEN = re.compile(r"[0-9a-f]{32}")
_WORD = re.compile(rf"[A-Za-z0-9._-]{{1,{selfcheck_wire.MAX_STRING}}}")
_BLANK = b" \t\r\n"
_CARRIED = (selfcheck_outcome.CONNECTED, *selfcheck_outcome.REFUSED_STATUS_WORDS)
_INIT = (INIT_KIND, INIT_SUBKIND)
_WORDS = (*_CARRIED, OTHER_STATUS)


class StreamFacts(NamedTuple):
    """What :func:`read` found; the module docstring says what each member means."""

    init_read: bool = False
    server_status: str | None = None
    server_in_errors: bool = False
    any_config_error: bool = False
    token_tool_listed: bool = False
    fail_tool_listed: bool = False
    result_read: bool = False
    token_in_reply: bool = False
    fail_token_in_reply: bool = False
    session_tools: tuple = ()
    session_tools_dropped: bool = False


_SHARED = StreamFacts._fields[:9]


def _pairs(pairs):
    members = dict(pairs)
    if len(members) != len(pairs):
        raise ValueError("a member name given twice")
    return members


def _not_json(constant):
    raise ValueError(constant)


def _event(line):
    try:
        value = json.loads(
            line.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_not_json,
            parse_int=lambda _digits: 0,
        )
    except (ValueError, RecursionError):
        return {}
    return value if type(value) is dict else {}


def _status(servers):
    if type(servers) is not list:
        return OTHER_STATUS
    words = []
    for entry in servers:
        if type(entry) is not dict or type(entry.get(SERVER_NAME_KEY)) is not str:
            return OTHER_STATUS
        if entry[SERVER_NAME_KEY] == SERVER_NAME:
            words.append(entry.get(SERVER_STATUS_KEY))
    if not words:
        return None
    if len(words) == 1 and type(words[0]) is str and words[0] in _CARRIED:
        return words[0]
    return OTHER_STATUS


def _tools(names):
    listed = [name for name in names if type(name) is str]
    kept = []
    for name in listed:
        if not name.startswith(TOOL_PREFIX):
            continue
        word = name if _WORD.fullmatch(name) else selfcheck_wire.OTHER
        if word in kept:
            continue
        if len(kept) == selfcheck_wire.MAX_LISTED:
            return listed, tuple(kept), True
        kept.append(word)
    return listed, tuple(kept), False


def read(output, *, token, fail_token):
    """Return the :class:`StreamFacts` of the standard output of one session.

    ``output`` is the bytes the session wrote, whole or cut by the time
    limit. ``token`` and ``fail_token`` are the two tokens of the check, of
    the form :mod:`hilclaw.selfcheck_server` accepts. Every ``output`` gives a
    value. Raises :class:`TypeError` or :class:`ValueError`, with a fixed
    text, for an argument of another form, as the module docstring lists.
    """
    if type(output) is not bytes:
        raise TypeError("the output must be bytes")
    for value in (token, fail_token):
        if type(value) is not str:
            raise TypeError("a token must be a str")
        if not _TOKEN.fullmatch(value):
            raise ValueError("a token must be 32 lowercase hexadecimal characters")
    if token == fail_token:
        raise ValueError("the two tokens must differ")
    events = [_event(line) for line in output.split(b"\n") if line.strip(_BLANK)]
    facts = StreamFacts()
    inits = [
        event
        for event in events
        if (event.get(EVENT_KIND_KEY), event.get(EVENT_SUBKIND_KEY)) == _INIT
    ]
    if len(inits) == 1:
        init = inits[0]
        names = init.get(TOOLS_KEY)
        listed, kept, dropped = _tools(names if type(names) is list else [])
        in_errors = SERVER_ERRORS_KEY in init and init[SERVER_ERRORS_KEY] != []
        facts = facts._replace(
            init_read=True,
            server_status=_status(init.get(SERVERS_KEY)),
            server_in_errors=in_errors,
            any_config_error=in_errors,
            token_tool_listed=TOKEN_TOOL_SESSION_NAME in listed,
            fail_tool_listed=FAIL_TOOL_SESSION_NAME in listed,
            session_tools=kept,
            session_tools_dropped=dropped,
        )
    last = events[-1] if events else {}
    if last.get(EVENT_KIND_KEY) == RESULT_KIND:
        reply = last.get(REPLY_KEY)
        text = reply if type(reply) is str else ""
        facts = facts._replace(
            result_read=True,
            token_in_reply=token in text,
            fail_token_in_reply=fail_token in text,
        )
    return facts


def evidence(facts, *, timed_out, exit_status):
    """Return the ``SessionEvidence`` of a session that was started.

    ``facts`` is the :class:`StreamFacts` of its output, ``timed_out`` whether
    the time limit ended it and ``exit_status`` its exit status or ``None``
    when it has none. Raises :class:`TypeError` for an argument of another
    form, as the module docstring lists; the message holds nothing of the
    argument.
    """
    if type(facts) is not StreamFacts:
        raise TypeError("the facts must be a StreamFacts")
    flags = [getattr(facts, name) for name in _SHARED if name != "server_status"]
    if any(type(flag) is not bool for flag in flags):
        raise TypeError("a yes-or-no value must be True or False")
    word = facts.server_status
    if word is not None and (type(word) is not str or word not in _WORDS):
        raise TypeError("the status word must be None or a word this module carries")
    if type(timed_out) is not bool:
        raise TypeError("timed_out must be True or False")
    if exit_status is not None and type(exit_status) is not int:
        raise TypeError("the exit status must be None or an integer")
    return selfcheck_outcome.SessionEvidence(
        started=True,
        timed_out=timed_out,
        exit_status=exit_status,
        **{name: getattr(facts, name) for name in _SHARED},
    )
