"""The report of the runtime self-check (ADR-0054 decision 7).

:func:`build` takes the values the landed steps return - the
:class:`hilclaw.selfcheck_login.LoginStatus` of step one, the
:class:`hilclaw.selfcheck_session.SessionRun` of step two or ``None`` when no
session step was run, and a :class:`SystemFacts` - and returns the report as a
``dict``. :func:`line` turns a report into one JSON object on one line ended
by one LF, as :func:`hilclaw.tools.encode` writes a result. :func:`exit_status`
gives the exit status of the check for an outcome word. The three are pure:
they start no process, read no file, environment variable or clock, keep no
state and print nothing. :func:`system_facts` is the one function that reads
anything: three values of :mod:`platform`.

**The outcome** is the one :func:`hilclaw.selfcheck_outcome.decide` gives for
the same values, and no other way to an outcome exists here.

**The members**, in the order written. The names are those of a process
output, **not of a data-plane schema**: the report is no record of
``STATE.json``, ``instance.json`` or ``events.ndjson`` and carries no version.

- At the top: ``outcome``; ``refused_a``, ``refused_b`` (which condition of
  ``front_refused`` held; false for every other outcome); ``instruction``
  (``selfcheck_login.LOGIN_INSTRUCTION``, only when the outcome is
  ``not_logged_in``); and the four groups below.
- ``login``, of the ``LoginStatus``: ``auth_method``, ``exit_status``
  (``returncode``), ``timed_out``.
- ``system``, of the ``SystemFacts``: ``os_name``, ``os_release``,
  ``python_version``.
- ``session``, of ``run.session`` unless said: ``started``, ``init_read``,
  ``result_read``, ``exit_status``, ``timed_out``, ``wire_copy_read``
  (``run.wire is not None``), ``tools`` and ``tools_dropped``
  (``run.stream.session_tools`` and its ``..._dropped``),
  ``token_tool_listed``, ``fail_tool_listed``, ``token_in_reply``,
  ``fail_token_in_reply``, ``directory_removed`` (``run.removed``).
- ``wire``, of ``run.wire``: ``initialize_seen`` (``reached``),
  ``client_version``, ``revision_asked``, ``revision_answered``,
  ``probe_seen``, ``probe_before_initialize``, ``probe_revision``,
  ``probe_error``, ``token_call_requested``, ``token_call_answered``,
  ``fail_call_requested``, ``fail_call_answered``, ``unforeseen_methods``
  (``unforeseen``), ``unforeseen_dropped``.

"The server started" of the record is ``wire_copy_read`` and
``initialize_seen``. The record does not list ``directory_removed``.

**Conventions of this module** (the record leaves them to the code):

- *Absent or null.* A group is left out when its source does not exist:
  ``session`` when ``run`` is ``None``, ``wire`` when ``run.wire`` is ``None``.
  A member of a group that exists is always written, and is ``null`` when its
  value is ``None``. ``instruction`` is left out, never ``null``. With
  ``run.stream`` ``None`` (no session was started) ``tools`` is empty.
- *The gate.* Whatever the caller hands in, a string is written only as
  follows; the readers bound already, and nothing is believed here. The
  client version, the three revisions and a tool name: 1 to
  ``selfcheck_wire.MAX_STRING`` characters of ASCII letters, digits, ``.``,
  ``_`` and ``-``; a method name also ``/``; any other value but ``None``, a
  non-string included, is ``selfcheck_wire.OTHER`` (in a list ``None`` too).
  ``auth_method``: one of ``selfcheck_login.AUTH_METHODS``, else
  ``AUTH_METHOD_OTHER``. Of the tool names only the strings that begin with
  ``selfcheck_stream.TOOL_PREFIX``, and the reader's own ``OTHER``, are
  written. Each list holds every distinct value once and at most
  ``selfcheck_wire.MAX_LISTED``; ``..._dropped`` is true when the source said
  so or one was cut here.
- *The system facts* are ``platform.system()``, ``platform.release()`` and
  ``platform.python_version()`` and nothing else of the machine: no host
  name. The record sets no bound for them; the gate is applied all the same,
  with ``+`` allowed (a Python build or a kernel release can end in it), so
  that the line stays short whatever a platform states.
- *The exit statuses*: :data:`EXIT_PASSED` 0 and one distinct value for each
  other outcome, 10 to 15 in the order of ``selfcheck_outcome.OUTCOMES``.
  None is 1 or 2 (the interpreter's), 3 or 4 (``python -m hilclaw``), 120, or
  126 and above (the shell's). A fault of the check itself has none here.
- *Values that contradict each other.* A ``login.outcome`` that is not
  ``None`` with a ``SessionRun``, and one that is ``None`` without, are
  refused (:class:`ValueError`). Nothing else is cross-checked.
- *What is refused*, each with a fixed text that holds nothing of the
  argument (:class:`TypeError`): a ``login`` that is no ``LoginStatus``, a
  ``run`` that is neither ``None`` nor a ``SessionRun``, a ``system`` that is
  no ``SystemFacts``, a ``stream`` that is neither ``None`` nor a
  ``StreamFacts``, a list of names that is no tuple, a yes-or-no value that
  is not ``True`` or ``False``, an integer value that is neither ``None`` nor
  an ``int`` below 2**32 in size (``True`` is none). ``decide``'s pass on. By
  :func:`exit_status`: no string (:class:`TypeError`), no outcome word
  (:class:`ValueError`). By :func:`line`: a value that is no ``dict`` or
  cannot be written as JSON (:class:`TypeError`).

**What a report holds**: booleans, integers, ``null``, the strings of the
gate, the fixed instruction text and outcome words, and lists and objects of
those. Nothing is copied whole or in part from an output, the wire copy, a
reply, the environment or an exception, and nothing names the host or the user.

Known limits. A pass is one observation (ADR-0054 L2). The yes-or-no values
and the integers of that size are believed as given (L6). A string inside the
bound is written whatever it means: a method name may look like a path. A
``session_failed`` report says how far the session got and not why. The
record lists no member for the error codes of condition (a), the status word
of the server, a torn copy or an unplaceable line, so the report does not say
them. :func:`line` writes the ``dict`` it is given: the gate is :func:`build`.
What :mod:`platform` does to learn its three values is the interpreter's.
Where the report is kept and what the instance's log is are not this module's
(O7). No step is called, no stream is written and no command of the package
exists here. Nothing calls the module yet.
"""

import platform
import re
from typing import NamedTuple

from hilclaw import selfcheck_login, selfcheck_outcome, tools
from hilclaw.selfcheck_login import AUTH_METHOD_OTHER, AUTH_METHODS
from hilclaw.selfcheck_session import SessionRun
from hilclaw.selfcheck_stream import TOOL_PREFIX, StreamFacts
from hilclaw.selfcheck_wire import MAX_LISTED, MAX_STRING, OTHER

EXIT_PASSED = 0
EXIT_NO_CLAUDE = 10
EXIT_NOT_LOGGED_IN = 11
EXIT_LOGIN_UNREADABLE = 12
EXIT_FRONT_REFUSED = 13
EXIT_NO_CALL = 14
EXIT_SESSION_FAILED = 15
_EXIT = {
    selfcheck_login.NO_CLAUDE: EXIT_NO_CLAUDE,
    selfcheck_login.NOT_LOGGED_IN: EXIT_NOT_LOGGED_IN,
    selfcheck_login.LOGIN_UNREADABLE: EXIT_LOGIN_UNREADABLE,
    selfcheck_outcome.FRONT_REFUSED: EXIT_FRONT_REFUSED,
    selfcheck_outcome.PASSED: EXIT_PASSED,
    selfcheck_outcome.NO_CALL: EXIT_NO_CALL,
    selfcheck_outcome.SESSION_FAILED: EXIT_SESSION_FAILED,
}
_WORD = re.compile(rf"[A-Za-z0-9._-]{{1,{MAX_STRING}}}")
_METHOD = re.compile(rf"[A-Za-z0-9._/-]{{1,{MAX_STRING}}}")
_SYSTEM = re.compile(rf"[A-Za-z0-9._+-]{{1,{MAX_STRING}}}")


class SystemFacts(NamedTuple):
    """The operating system's name and release and the Python version."""

    os_name: str
    os_release: str
    python_version: str


def system_facts():
    """Return the :class:`SystemFacts` of this interpreter, as it states them."""
    return SystemFacts(platform.system(), platform.release(), platform.python_version())


def _flag(value):
    if type(value) is not bool:
        raise TypeError("a yes-or-no value must be True or False")
    return value


def _integer(value):
    if value is not None and (type(value) is not int or abs(value) >> 32):
        raise TypeError("an integer value must be None or an integer of 32 bits")
    return value


def _bounded(value, form):
    if value is None:
        return None
    return value if type(value) is str and form.fullmatch(value) else OTHER


def _listed(source, member, form, prefix=""):
    values = getattr(source, member)
    if type(values) is not tuple:
        raise TypeError("a list of names must be a tuple")
    kept, cut = [], _flag(getattr(source, member + "_dropped"))
    for value in values:
        named = type(value) is str and (value == OTHER or value.startswith(prefix))
        if prefix and not named:
            continue
        word = _bounded(value, form) or OTHER
        if word in kept:
            continue
        if len(kept) == MAX_LISTED:
            return kept, True
        kept.append(word)
    return kept, cut


def _session(run):
    stream = StreamFacts() if run.stream is None else run.stream
    if type(stream) is not StreamFacts:
        raise TypeError("the stream facts must be a StreamFacts or None")
    names, dropped = _listed(stream, "session_tools", _WORD, TOOL_PREFIX)
    session = run.session
    return {
        "started": _flag(session.started),
        "init_read": _flag(session.init_read),
        "result_read": _flag(session.result_read),
        "exit_status": _integer(session.exit_status),
        "timed_out": _flag(session.timed_out),
        "wire_copy_read": run.wire is not None,
        "tools": names,
        "tools_dropped": dropped,
        "token_tool_listed": _flag(session.token_tool_listed),
        "fail_tool_listed": _flag(session.fail_tool_listed),
        "token_in_reply": _flag(session.token_in_reply),
        "fail_token_in_reply": _flag(session.fail_token_in_reply),
        "directory_removed": _flag(run.removed),
    }


def _wire(wire):
    methods, dropped = _listed(wire, "unforeseen", _METHOD)
    return {
        "initialize_seen": _flag(wire.reached),
        "client_version": _bounded(wire.client_version, _WORD),
        "revision_asked": _bounded(wire.revision_asked, _WORD),
        "revision_answered": _bounded(wire.revision_answered, _WORD),
        "probe_seen": _flag(wire.probe_seen),
        "probe_before_initialize": _flag(wire.probe_before_initialize),
        "probe_revision": _bounded(wire.probe_revision, _WORD),
        "probe_error": _integer(wire.probe_error),
        "token_call_requested": _flag(wire.token_call_requested),
        "token_call_answered": _flag(wire.token_call_answered),
        "fail_call_requested": _flag(wire.fail_call_requested),
        "fail_call_answered": _flag(wire.fail_call_answered),
        "unforeseen_methods": methods,
        "unforeseen_dropped": dropped,
    }


def build(login, run, *, system):
    """Return the report of one check as a ``dict`` of the members above.

    ``login`` is the ``LoginStatus`` of step one, ``run`` the ``SessionRun``
    of step two or ``None`` when no session step was run, ``system`` a
    :class:`SystemFacts`. Raises :class:`TypeError` or :class:`ValueError`
    for values of another form or that contradict each other, as the module
    docstring lists; the message holds nothing of the argument.
    """
    if type(login) is not selfcheck_login.LoginStatus:
        raise TypeError("the login must be a LoginStatus")
    if type(system) is not SystemFacts:
        raise TypeError("the system facts must be a SystemFacts")
    if run is None:
        evidence, wire, torn = selfcheck_outcome.SessionEvidence(), None, False
    elif type(run) is SessionRun:
        evidence, wire, torn = run.session, run.wire, run.torn
    else:
        raise TypeError("the run must be a SessionRun or None")
    verdict = selfcheck_outcome.decide(login.outcome, evidence, wire, torn=torn)
    if (login.outcome is None) == (run is None):
        raise ValueError("a session step goes with a step one that says logged in")
    report = {
        "outcome": verdict.outcome,
        "refused_a": _flag(verdict.refused_a),
        "refused_b": _flag(verdict.refused_b),
    }
    if verdict.outcome == selfcheck_login.NOT_LOGGED_IN:
        report["instruction"] = selfcheck_login.LOGIN_INSTRUCTION
    method = login.auth_method
    if not (method is None or type(method) is str and method in AUTH_METHODS):
        method = AUTH_METHOD_OTHER
    report["login"] = {
        "auth_method": method,
        "exit_status": _integer(login.returncode),
        "timed_out": _flag(login.timed_out),
    }
    report["system"] = {
        name: _bounded(value, _SYSTEM) for name, value in system._asdict().items()
    }
    if run is not None:
        report["session"] = _session(run)
    if wire is not None:
        report["wire"] = _wire(wire)
    return report


def line(report):
    """Return ``report`` as one line of compact JSON in ASCII bytes, ended by one LF.

    ``report`` is a ``dict`` that :func:`build` returned; the same report gives
    the same bytes, in its member order. Raises :class:`TypeError`, with a
    fixed text, for a value that is no ``dict`` or cannot be written as JSON.
    """
    try:
        if type(report) is dict:
            return tools.encode(report)
    except (TypeError, ValueError, RecursionError):
        pass
    raise TypeError("the report must be a dict that build returned")


def exit_status(outcome):
    """Return the exit status of a check that ended in ``outcome``.

    0 for ``passed`` and for nothing else; never 1 or 2. Raises :class:`TypeError`
    for no string, :class:`ValueError` for no word of ``selfcheck_outcome.OUTCOMES``.
    """
    if type(outcome) is not str:
        raise TypeError("the outcome must be a string")
    if outcome not in _EXIT:
        raise ValueError("the outcome must be a word of the closed list")
    return _EXIT[outcome]
