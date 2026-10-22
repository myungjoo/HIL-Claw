"""The stop check hook of a first-case turn session (ADR-0148).

:func:`main` is a ``Stop`` command hook program. It reads one hook input from
standard input and takes the run id and the data root from its two
arguments. It returns the exit status: :data:`EXIT_REFUSE` with the one line
:data:`REFUSAL` on standard error when the input is the main session's first
stop (``stop_hook_active`` exactly ``false``) and
:func:`hilclaw.run_commit.commit_owed` answers true for that run, else
:data:`EXIT_PASS` with nothing printed. It writes no file, makes no commit,
calls no model and contacts no server. This is runtime code: it is built and
tested against fixture inputs and temporary git repositories only, never
against a real session (D16).

**Unlike the two** ``PreToolUse`` **hooks** (:mod:`hilclaw.caller_check`,
:mod:`hilclaw.budget_check`), this hook lets the stop through on every fault,
and it starts processes: :func:`hilclaw.run_commit.commit_owed` runs the
machine's ``git``, read-only.

**Decided by ADR-0148** and only applied here:

- a refusal is exit 2 with one line on standard error; nothing is ever
  written to standard output: no ``decision``, ``reason`` or
  ``additionalContext`` (decision 3);
- the run id and the data root are the hook's arguments, never the
  environment, the prompt or a configured source; only ``hook_event_name``
  and ``stop_hook_active`` are read from the input, never
  ``transcript_path`` or ``last_assistant_message`` (decision 4);
- ``commit_owed`` is asked once; a stop is refused only when
  ``stop_hook_active`` is exactly ``false`` (decision 4);
- the table of decision 5: every input, argument or answer other than an
  owed commit at a first stop lets the stop through, and the whole body is
  guarded so that any :class:`Exception` lets it through (decision 5);
- what the line says (decision 5).

**Chosen here** (left to the code slice by ADR-0148): the names
:data:`EVENT`, :data:`COMMIT_TOOL`, :data:`START` and :data:`REFUSAL` and the
wording of the line; an input object with a repeated key or a ``NaN`` or
``Infinity`` constant is not JSON and lets the stop through; a relative data
root is used as given, with nothing let through beyond the table; a failure
to write the line lets the stop through.

This module is not registered here. The ``Stop`` entry of the session's
settings, with the run id and the data root as its last two arguments, is
written by :mod:`hilclaw.turn_loop` in ADR-0148's second code slice.

Runtime acceptance items it depends on (ADR-0148 Consequences):

- (lxiii) the ``Stop`` entry runs when the main session ends its reply;
- (lxiv) exit 2 continues the session and the next stop is ``true``;
- (lxv) the hook finds ``git`` and finishes within its timeout;
- (lxvi) a model told the line calls ``run_commit`` once, or ends at once;
- ADR-0146 (lvi) the hook of the written settings runs, here for ``Stop``;
- ADR-0146 (lix) the exec form, its arguments as written;
- ADR-0146 (lx) no managed setting or mod undoes the hook.
"""

import contextlib
import json
import os
import sys

from hilclaw import layout, mcp_front, run_commit
from hilclaw.caller_check import TOOL_PREFIX

EXIT_PASS = 0
EXIT_REFUSE = 2
EVENT = "Stop"
COMMIT_TOOL = TOOL_PREFIX + mcp_front.mcp_name("run.commit")
START = (
    "import sys; sys.path.insert(0, sys.argv.pop(1)); "
    "from hilclaw.stop_check import main; raise SystemExit(main(args=sys.argv[1:]))"
)
REFUSAL = (
    "stop check: this stop was held because a commit of the run is owed; "
    f'call {COMMIT_TOOL} once, as "The end of a session" says, and then end; '
    "if your prompt held no valid run id, or a call of "
    f"{COMMIT_TOOL} has failed in this turn, end at once without calling it"
)


class _NotJson(Exception):
    pass


def _unique(pairs):
    found = dict(pairs)
    if len(found) != len(pairs):
        raise _NotJson
    return found


def _constant(_):
    raise _NotJson


def _owed(data, args):
    payload = json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant
    )
    if not isinstance(payload, dict):
        return False
    if payload.get("hook_event_name") != EVENT:
        return False
    if payload.get("stop_hook_active") is not False:
        return False
    if len(args) != 2:
        return False
    run_id = layout.check_run_id(args[0])
    data_root = args[1]
    if not isinstance(data_root, str) or not os.path.isdir(data_root):
        return False
    return run_commit.commit_owed(data_root, run_id) is True


def main(data=None, stderr=None, args=None):
    """Check one ``Stop`` of a turn session's main session and return the exit status.

    ``data`` is the hook input as ``bytes`` (default: all of the process's
    standard input), ``stderr`` the text stream the refusal line is written
    to (default :data:`sys.stderr`) and ``args`` the list of the program's
    arguments after the package directory: the run id, then the data root
    (default ``sys.argv[1:]``). Writes :data:`REFUSAL` as one line to
    ``stderr`` and returns :data:`EXIT_REFUSE` when the input is one strict
    JSON object whose ``hook_event_name`` is :data:`EVENT` and whose
    ``stop_hook_active`` is exactly ``false``, ``args`` holds exactly a run
    id that :func:`hilclaw.layout.check_run_id` accepts and a data root that
    names a directory, and :func:`hilclaw.run_commit.commit_owed` then
    answers true. Otherwise returns :data:`EXIT_PASS` and prints nothing.
    Every :class:`Exception` raised while reading, deciding or writing the
    line lets the stop through with :data:`EXIT_PASS`; nothing is ever
    written to standard output.
    """
    with contextlib.suppress(Exception):
        if data is None:
            data = sys.stdin.buffer.read()
        if _owed(data, sys.argv[1:] if args is None else args):
            stream = sys.stderr if stderr is None else stderr
            print(REFUSAL, file=stream)
            stream.flush()
            return EXIT_REFUSE
    return EXIT_PASS
