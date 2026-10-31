"""The round-budget check hook of a first-case turn session (ADR-0147).

:func:`main` is a ``PreToolUse`` command hook program for the tools that
spend, :data:`SPENDING_TOOLS`. It reads one hook input from standard input,
takes the run that the request's ``run_id`` names below the data root given
as its one argument, and returns the exit status: :data:`EXIT_PASS` with
nothing printed when that run holds no ``run_status`` and is not at its
round budget, else :data:`EXIT_REFUSE` with one fixed line on standard
error. It writes no file, starts no process, calls no model and contacts no
server. This is runtime code: it is built and tested against fixture inputs
and fixture run directories only, never against a real session (D16).

**Decided by ADR-0147** and only applied here:

- the spending tools are ``coder.run`` and ``correctness.check`` (decision 2),
  and ``sim.run`` and ``board.run``, which the slice that registers them adds
  (decision 2; ADR-0167 decision 5);
- a pass gives no decision: exit 0 and no output, never ``"allow"``, nothing
  on standard output and so no ``updatedInput`` (decision 3);
- the run is the ``run_id`` of ``tool_input``, not compared with the
  session's run; the data root is the hook's argument, never the environment
  or a configured source (decision 4);
- ``STATE.json`` and then, when it holds no ``run_status``, ``instance.json``
  are read by :func:`hilclaw.run_file_tools.read`; only ``run_status``,
  ``round`` and ``round_budget`` are interpreted, and ``round`` at or beyond
  ``round_budget`` refuses (decisions 4, 5);
- a run that states no ``round_budget`` gets no decision (decision 5);
- the whole body is guarded: any :class:`Exception` refuses (decision 4);
- the refusals of decision 5's table and its one line.

**Chosen here** (left to the code slice by ADR-0147): the names
:data:`SPENDING_TOOLS`, :data:`START` and :data:`REFUSAL`; an argument list
of other than exactly one element is refused; a relative data root is used
as given, with no refusal beyond the table; an input object with a repeated
key or a ``NaN`` or ``Infinity`` constant is refused; the line names the
tool only when it is a spending tool. What :data:`START` raises before
:func:`main` runs (no package argument, a failed import) ends through an
``excepthook`` in exit status 2 with one fixed line on standard error, so such
a fault refuses without relying on ``onFailure``; a :class:`SystemExit` does
not reach that hook, so :func:`main`'s status is kept.

:mod:`hilclaw.turn_loop` writes the second ``PreToolUse`` entry that names
this program, its matcher built from :data:`SPENDING_TOOLS` and the data root
as its last argument.

Runtime acceptance items it depends on (ADR-0147 Consequences):

- (lxi) the hook's ``tool_input`` is the arguments object the server receives;
- (lxii) both ``PreToolUse`` entries run, and one exit 2 stops the call;
- ADR-0146 (lvi) the hook of the written settings runs for every matched call;
- ADR-0146 (lviii) exit 2 stops the call and exit 0 leaves it to ``dontAsk``;
- ADR-0146 (lix) ``onFailure`` and the exec form, its arguments as written;
- ADR-0146 (lx) no managed setting or mod undoes the hook.
"""

import contextlib
import json
import os
import sys

from hilclaw import layout, run_file_tools
from hilclaw.caller_check import EVENT, TOOL_PREFIX

EXIT_PASS = 0
EXIT_REFUSE = 2
RUN_STATUS = "run_status"
SPENDING_TOOLS = (
    f"{TOOL_PREFIX}coder_run",
    f"{TOOL_PREFIX}correctness_check",
    f"{TOOL_PREFIX}sim_run",
    f"{TOOL_PREFIX}board_run",
)
START = (
    "import os, sys; sys.excepthook = lambda *_: (sys.stderr.write("
    "'budget check: the hook could not start\\n'), sys.stderr.flush(), os._exit(2)); "
    "sys.path.insert(0, sys.argv.pop(1)); "
    "from hilclaw.budget_check import main; raise SystemExit(main(args=sys.argv[1:]))"
)
REFUSAL = (
    "budget check: the call{} was refused because the run is over, "
    "is at its round budget, or could not be checked"
)


class _Refused(Exception):
    pass


def _unique(pairs):
    found = dict(pairs)
    if len(found) != len(pairs):
        raise _Refused
    return found


def _constant(_):
    raise _Refused


def _payload(data):
    text = data.decode("utf-8")
    payload = json.loads(text, object_pairs_hook=_unique, parse_constant=_constant)
    if not isinstance(payload, dict):
        raise _Refused
    return payload


def _decide(data, args):
    payload = _payload(data)
    if payload.get("hook_event_name") != EVENT:
        raise _Refused
    if payload.get("tool_name") not in SPENDING_TOOLS:
        raise _Refused
    request = payload.get("tool_input")
    if not isinstance(request, dict):
        raise _Refused
    run_id = layout.check_run_id(request.get("run_id"))
    if len(args) != 1 or not isinstance(args[0], str) or not os.path.isdir(args[0]):
        raise _Refused
    data_root = args[0]
    state, _ = run_file_tools.read(data_root, run_id, "STATE.json")
    if RUN_STATUS in state.others:
        raise _Refused
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    if stated.round_budget is not None and state.round >= stated.round_budget:
        raise _Refused


def _line(data):
    with contextlib.suppress(Exception):
        tool = _payload(data).get("tool_name")
        if tool in SPENDING_TOOLS:
            return REFUSAL.format(f" of {tool}")
    return REFUSAL.format("")


def main(data=None, stderr=None, args=None):
    """Check the run of one spending ``PreToolUse`` call and return the exit status.

    ``data`` is the hook input as ``bytes`` (default: all of the process's
    standard input), ``stderr`` the text stream the refusal line is written
    to (default :data:`sys.stderr`) and ``args`` the list of the program's
    arguments after the package directory, whose one element is the data
    root (default ``sys.argv[1:]``). Returns :data:`EXIT_PASS` and prints
    nothing when the call is to a tool of :data:`SPENDING_TOOLS` and its
    run holds no ``run_status`` and either states no ``round_budget`` or has
    a ``round`` below it; otherwise writes :data:`REFUSAL` as one line to
    ``stderr`` and returns :data:`EXIT_REFUSE`. Every :class:`Exception`
    raised while reading or deciding refuses; nothing is ever written to
    standard output.
    """
    with contextlib.suppress(Exception):
        if data is None:
            data = sys.stdin.buffer.read()
        _decide(data, sys.argv[1:] if args is None else args)
        return EXIT_PASS
    with contextlib.suppress(Exception):
        print(_line(data), file=sys.stderr if stderr is None else stderr)
    return EXIT_REFUSE
