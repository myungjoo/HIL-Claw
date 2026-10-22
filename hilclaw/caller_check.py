"""The caller check hook of a first-case turn session (ADR-0146).

:func:`main` is a ``PreToolUse`` command hook program. It reads one hook
input from standard input, tells the calling agent, takes that caller's
holder list from the session directory with
:func:`hilclaw.turn_permissions.holder_lists`, and returns the exit status:
:data:`EXIT_PASS` with nothing printed when the tool is on the list, else
:data:`EXIT_REFUSE` with one fixed line on standard error. It writes no file,
starts no process, calls no model and contacts no server. This is runtime
code: it is built and tested against fixture inputs and fixture agent files
only, never against a real session (D16).

**Decided by ADR-0146** and only applied here:

- a pass gives no decision: exit 0 and no output, never ``"allow"`` and
  nothing on standard output (decision 2);
- the main session's list is :data:`hilclaw.turn_permissions.ROUND_MANAGER_TOOLS`,
  a sub-agent's list the ``mcp__hilclaw__`` entries of the agent file whose
  ``name`` equals its ``agent_type``, both read at each call (decision 3);
- a call with neither ``agent_id`` nor ``agent_type`` is the main session's,
  one with both is the named sub-agent's, any other is refused (decision 3);
- the session directory is :data:`ENV_PROJECT_DIR` of the environment, never
  the input's ``cwd`` (decision 3);
- the whole body is guarded: any :class:`Exception` refuses (decision 5);
- the refusals and the one line of decision 6.

**Chosen here** (left to the code slice by ADR-0146): ``agent_id`` counts
only when it is a non-empty ``str``; ``mcp_server`` is not read, the prefix
``mcp__hilclaw__`` is relied on (decision 2); an input object with a
repeated key is refused; the line names the tool only when ``tool_name`` has
the form the shared reader admits for a ``tools`` entry; :data:`START` is
the start text for the turn loop's settings.

The settings that name this program are written by :mod:`hilclaw.turn_loop`.

Runtime acceptance items it depends on (ADR-0146 Consequences):

- (lvi) the hook of the written settings runs for every ``hilclaw`` call,
  with ``CLAUDE_PROJECT_DIR`` the session directory;
- (lvii) a main-session call carries neither agent field, a sub-agent's both;
- (lviii) exit 2 stops the call and exit 0 leaves it to ``dontAsk``;
- (lix) ``onFailure: "block"`` and the exec form are honoured on every platform;
- (lx) no managed setting or mod undoes the hook.
"""

import contextlib
import json
import os
import re
import sys

from hilclaw import mcp_front, turn_permissions

EXIT_PASS = 0
EXIT_REFUSE = 2
EVENT = "PreToolUse"
ENV_PROJECT_DIR = "CLAUDE_PROJECT_DIR"
TOOL_PREFIX = f"mcp__{mcp_front.SERVER_NAME}__"
START = (
    "import sys; sys.path.insert(0, sys.argv.pop(1)); "
    "from hilclaw.caller_check import main; raise SystemExit(main())"
)
_NAMED = re.compile(rf"{re.escape(TOOL_PREFIX)}[a-z][a-z0-9_]*")
REFUSAL = (
    "caller check: the call{} was refused because the calling agent "
    "does not hold the tool or could not be checked"
)


class _Refused(Exception):
    pass


def _unique(pairs):
    found = dict(pairs)
    if len(found) != len(pairs):
        raise _Refused
    return found


def _holders(payload, environ):
    has_id = "agent_id" in payload
    has_type = "agent_type" in payload
    if has_id != has_type:
        raise _Refused
    session = environ.get(ENV_PROJECT_DIR)
    if not isinstance(session, str) or not session or not os.path.isdir(session):
        raise _Refused
    main_list, agents = turn_permissions.holder_lists(session)
    if not has_id:
        return main_list
    agent_id = payload["agent_id"]
    agent_type = payload["agent_type"]
    if not isinstance(agent_id, str) or not agent_id:
        raise _Refused
    if not isinstance(agent_type, str) or agent_type not in agents:
        raise _Refused
    return agents[agent_type]


def _decide(data, environ):
    payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique)
    if not isinstance(payload, dict) or payload.get("hook_event_name") != EVENT:
        raise _Refused
    tool = payload.get("tool_name")
    if not isinstance(tool, str) or not tool.startswith(TOOL_PREFIX):
        raise _Refused
    if tool not in _holders(payload, environ):
        raise _Refused


def _line(data):
    with contextlib.suppress(Exception):
        payload = json.loads(data.decode("utf-8"), object_pairs_hook=_unique)
        tool = payload.get("tool_name")
        if isinstance(tool, str) and _NAMED.fullmatch(tool):
            return REFUSAL.format(f" of {tool}")
    return REFUSAL.format("")


def main(data=None, stderr=None, environ=None):
    """Check the caller of one ``PreToolUse`` call and return the exit status.

    ``data`` is the hook input as ``bytes`` (default: all of the process's
    standard input), ``stderr`` the text stream the refusal line is written
    to (default :data:`sys.stderr`) and ``environ`` the mapping
    :data:`ENV_PROJECT_DIR` is read from (default :data:`os.environ`).
    Returns :data:`EXIT_PASS` and prints nothing when the calling agent holds
    the tool; otherwise writes :data:`REFUSAL` as one line to ``stderr`` and
    returns :data:`EXIT_REFUSE`. Every :class:`Exception` raised while
    reading or deciding refuses; nothing is ever written to standard output.
    """
    with contextlib.suppress(Exception):
        if data is None:
            data = sys.stdin.buffer.read()
        _decide(data, os.environ if environ is None else environ)
        return EXIT_PASS
    with contextlib.suppress(Exception):
        print(_line(data), file=sys.stderr if stderr is None else stderr)
    return EXIT_REFUSE
