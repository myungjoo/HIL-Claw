"""Step two of the runtime self-check: the session (ADR-0054 decision 4).

:func:`run` makes the directory of the check, two tokens and the configuration
file, starts exactly one ``claude -p`` through :func:`hilclaw.local_run.run`,
reads the session's output and the wire copy with the modules of the check,
removes the directory and returns one :class:`SessionRun`. This is runtime
code: on a runtime machine it starts the real ``claude`` and spends one
session of plan usage. It is built and tested against a stub ``claude`` that
the tests write, never against a real one (D16); that a real session behaves
as that stub does is shown by nothing here.

**The command line** is :data:`COMMAND`, the same for every call: :data:`PROGRAM`,
:data:`OPT_PRINT` with :data:`PROMPT`, :data:`OPT_MCP_CONFIG` with
:data:`CONFIG_FILE`, :data:`OPT_STRICT_MCP_CONFIG`, :data:`OPT_SETTING_SOURCES`
with :data:`SETTING_SOURCES`, :data:`OPT_TOOLS` with :data:`NO_TOOLS`,
:data:`OPT_PERMISSION_MODE` with :data:`PERMISSION_MODE`,
:data:`OPT_ALLOWED_TOOLS` with :data:`ALLOWED_TOOLS`,
:data:`OPT_NO_SESSION_PERSISTENCE`, :data:`OPT_OUTPUT_FORMAT` with
:data:`OUTPUT_FORMAT`, and :data:`OPT_VERBOSE`. No bypass flag, no model, no
turn limit and no other option is passed, and no environment variable is set:
the session gets the environment of the calling process unchanged.

**The standing of each name**, in the record's words: *verified* = on a
documentation page read for the record, never tried; *observed once* = the one
command line of T-0106, in a session that never reached the model; *not
verified* = in no record of the repository.

- ``--mcp-config``, ``--strict-mcp-config`` (K4), ``--permission-mode`` with
  ``dontAsk`` (K5), ``--allowedTools``, ``--tools`` with ``""`` (K6),
  ``--no-session-persistence``, ``--setting-sources`` with ``project`` (K7),
  ``--output-format`` with ``stream-json`` (K8), and that a stdio server entry
  is ``command``, ``args``, ``env`` (ADR-0010 F1): verified.
- That those options except ``--allowedTools``, with ``-p`` taking the prompt
  as its argument and with ``--verbose``, were accepted on one command line in
  the order kept here, and that a file named by ``--mcp-config`` relative to
  the working directory connected the server ``hilclaw``: observed once.
- :data:`SERVERS_MEMBER` ``mcpServers``, the member of the configuration file
  that wraps the server entries; :data:`ALLOWED_TOOLS_SEPARATOR` ``,``, that
  ``--allowedTools`` takes both names as one argument joined by a comma; that
  an entry needs no member beyond those three: not verified.

The values not verified are provisional: this module's guess, a runtime
acceptance item of ADR-0054 (HQ-0016), and no statement of what Claude Code
does. **A wrong one costs a pass, never a false one**: the server does not
connect or the calls are denied, the evidence then lacks the wire copy, the
calls or the tokens, and :func:`hilclaw.selfcheck_outcome.decide` reads that
as ``session_failed`` or ``no_call``.

**The tokens** are made here with ``selfcheck_server.new_token``, new for
every call, and are written into the configuration file only: they are in no
argument, not in the prompt, not in the returned value and in no exception.

**Conventions of this module** (the record leaves them to the code):

- *The time limit* has no default; its value belongs to the code that
  composes the check. A bad ``timeout_s`` is refused as
  :func:`hilclaw.local_run.run` refuses it: nothing is started and the
  directory, already made, is removed.
- *The directory* is made by :func:`tempfile.mkdtemp`, with the permissions
  it gives, under ``parent`` - by default the temporary directory of the system.
  "Outside both checkouts" is checked before anything is made, on real paths:
  a ``parent`` that is, or lies inside, the directory that holds this package
  or a directory of ``keep_out`` is refused with a fixed text. The module
  knows no other checkout: the caller names the data root in ``keep_out``.
  Names are compared as :func:`os.path.normcase` folds them: on a file
  system that ignores case where the system's path rules do not, a name
  that differs in case only is not recognised.
- *The two files* are :data:`CONFIG_FILE` and :data:`WIRE_COPY_FILE` in that
  directory. The configuration file is written, created exclusively, before
  anything is started: one JSON object holding, under :data:`SERVERS_MEMBER`
  and ``selfcheck_stream.SERVER_NAME``, exactly what
  ``selfcheck_server.server_entry`` returns. The place of the wire copy is
  left for the server to create. Nothing is written anywhere else.
- *The configuration file is named to the session by its file name alone*, as
  on the observed command line, so no path is in an argument.
- *No session was started* - no ``claude`` found, or an :class:`OSError` of
  the start - is ``SessionEvidence()`` with ``stream`` and ``wire`` ``None``;
  nothing is read.
- *No readable wire copy* - no file, or what is there is no wire copy - is
  ``wire`` ``None`` with ``torn`` false.
- *The removal* is tried whatever happened, an exception included, which
  still arrives afterwards. A removal that fails is tried again a few times
  within about two seconds (on Windows a process that outlives the session
  can keep a file open), then carried as ``removed`` false: it raises
  nothing, and the evidence is not lost for it.
- *What is raised*: :class:`TypeError` and :class:`ValueError` for a bad
  ``timeout_s``, ``parent`` or ``keep_out``; :class:`OverflowError` of
  :func:`hilclaw.local_run.run`, after the child was started and killed;
  :class:`RuntimeError` of ``server_entry``; and the :class:`OSError` of
  making the directory or writing the configuration file, with the system's
  own text, which may name the path. The last is raised and not read as "no
  session was started": that row of the record speaks of the session, and a
  disk that refuses the check's own files is a fault of the check that
  ``session_failed`` would hide. No exception holds a token.
- *What leaves the module*: the named facts of the readers. No line of the
  output or of the wire copy, no reply text, no token, no path and no command
  line; the child's standard error is dropped. The module prints nothing.

Not done here: no step one, no outcome, no report, no exit status of the
check, no retry and no second process. No data-plane file is written.

Known limits. A pass is one observation (ADR-0054 L2). Every call spends one
session of plan usage; when to call is the caller's (L5). Whoever controls the
``PATH`` or the environment decides what is seen, and a credential in the
environment reaches the session unchanged (L6). On Windows the ``claude`` found
may be a command script, whose arguments pass through the command interpreter:
the prompt is therefore one line of ASCII letters, digits, spaces, ``.``,
``,`` and ``_``, but the empty argument of ``--tools`` and the comma of
``--allowedTools`` are not under the module's control. From
:mod:`hilclaw.local_run`: on a timeout only the started process is killed, so
a surviving child can make the call outlast the limit and keep the directory
in use; the output is held in memory. A killed process of the check leaves the
directory behind. Nothing calls the module yet.
"""

import json
import os
import shutil
import tempfile
import time
from typing import NamedTuple

from hilclaw import (
    local_run,
    selfcheck_outcome,
    selfcheck_server,
    selfcheck_stream,
    selfcheck_wire,
)

PROGRAM = "claude"
OPT_PRINT = "-p"
OPT_MCP_CONFIG = "--mcp-config"
OPT_STRICT_MCP_CONFIG = "--strict-mcp-config"
OPT_SETTING_SOURCES = "--setting-sources"
SETTING_SOURCES = "project"
OPT_TOOLS = "--tools"
NO_TOOLS = ""
OPT_PERMISSION_MODE = "--permission-mode"
PERMISSION_MODE = "dontAsk"
OPT_ALLOWED_TOOLS = "--allowedTools"
ALLOWED_TOOLS_SEPARATOR = ","
ALLOWED_TOOLS = ALLOWED_TOOLS_SEPARATOR.join(
    (
        selfcheck_stream.TOKEN_TOOL_SESSION_NAME,
        selfcheck_stream.FAIL_TOOL_SESSION_NAME,
    )
)
OPT_NO_SESSION_PERSISTENCE = "--no-session-persistence"
OPT_OUTPUT_FORMAT = "--output-format"
OUTPUT_FORMAT = "stream-json"
OPT_VERBOSE = "--verbose"
SERVERS_MEMBER = "mcpServers"
CONFIG_FILE = "selfcheck.mcp.json"
WIRE_COPY_FILE = "selfcheck.wire"
PROMPT = (
    f"Call the tool {selfcheck_stream.TOKEN_TOOL_SESSION_NAME} once and the tool "
    f"{selfcheck_stream.FAIL_TOOL_SESSION_NAME} once, each without arguments. "
    "The second one answers with a failure, which is expected. Then reply with "
    "the exact text that each of the two returned, the failure message included."
)
COMMAND = (
    PROGRAM,
    OPT_PRINT,
    PROMPT,
    OPT_MCP_CONFIG,
    CONFIG_FILE,
    OPT_STRICT_MCP_CONFIG,
    OPT_SETTING_SOURCES,
    SETTING_SOURCES,
    OPT_TOOLS,
    NO_TOOLS,
    OPT_PERMISSION_MODE,
    PERMISSION_MODE,
    OPT_ALLOWED_TOOLS,
    ALLOWED_TOOLS,
    OPT_NO_SESSION_PERSISTENCE,
    OPT_OUTPUT_FORMAT,
    OUTPUT_FORMAT,
    OPT_VERBOSE,
)

_PACKAGE_DIRECTORY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PREFIX = "hilclaw-selfcheck-"
_REMOVE_PAUSES_S = (0.0, 0.2, 0.6, 1.2)


class SessionRun(NamedTuple):
    """What one :func:`run` call found.

    - ``session``: the ``SessionEvidence`` of the session; ``SessionEvidence()``
      when none was started.
    - ``wire``: the ``WireFacts`` of the wire copy; ``None`` when no readable
      copy exists.
    - ``torn``: the ``torn`` of that copy; false when there is none.
    - ``stream``: the ``StreamFacts`` of the session's standard output;
      ``None`` when no session was started.
    - ``removed``: the directory of the check is gone.
    """

    session: selfcheck_outcome.SessionEvidence
    wire: selfcheck_wire.WireFacts | None
    torn: bool
    stream: selfcheck_stream.StreamFacts | None
    removed: bool


def _real(path, what):
    path = os.fspath(path)
    if type(path) is not str:
        raise TypeError(f"{what} must be a str or a path")
    return os.path.realpath(path)


def _refuse_inside(parent, keep_out):
    if isinstance(keep_out, (str, bytes, os.PathLike)):
        raise TypeError("keep_out must be a sequence of paths, not one path")
    place = _real(parent, "the parent")
    inside = os.path.normcase(place) + os.sep
    for root in (_PACKAGE_DIRECTORY, *keep_out):
        root = os.path.normcase(_real(root, "a directory of keep_out"))
        if inside.startswith(root.rstrip(os.sep) + os.sep):
            raise ValueError("the directory of the check would lie inside a checkout")
    return place


def _remove(directory):
    for pause in _REMOVE_PAUSES_S:
        time.sleep(pause)
        shutil.rmtree(directory, ignore_errors=True)
        if not os.path.lexists(directory):
            return True
    return False


def _session(directory, timeout_s):
    token, fail_token = selfcheck_server.new_token(), selfcheck_server.new_token()
    place = os.path.join(directory, WIRE_COPY_FILE)
    entry = selfcheck_server.server_entry(
        token=token, fail_token=fail_token, wire_copy=place
    )
    config = {SERVERS_MEMBER: {selfcheck_stream.SERVER_NAME: entry}}
    with open(os.path.join(directory, CONFIG_FILE), "x", encoding="utf-8") as file:
        json.dump(config, file)
    try:
        done = local_run.run(COMMAND, timeout_s=timeout_s, cwd=directory)
    except (local_run.ProgramNotFoundError, OSError):
        return selfcheck_outcome.SessionEvidence(), None, False, None
    stream = selfcheck_stream.read(done.stdout, token=token, fail_token=fail_token)
    session = selfcheck_stream.evidence(
        stream, timed_out=done.timed_out, exit_status=done.returncode
    )
    try:
        copy = selfcheck_server.read_wire_copy(place)
    except (selfcheck_server.WireCopyError, OSError):
        return session, None, False, stream
    return session, selfcheck_wire.read(copy.lines), copy.torn, stream


def run(*, timeout_s, parent=None, keep_out=()):
    """Run step two of the self-check once and return a :class:`SessionRun`.

    ``timeout_s`` is the limit of the session in seconds. ``parent`` is the
    existing directory the directory of the check is made in (``None``: the
    temporary directory of the system) and ``keep_out`` a sequence of
    directories it must not lie inside, beside the one that holds this
    package. Every way a session can end, one that could not be started
    included, is a result. Raises as the module docstring lists under "What
    is raised"; the directory is gone then too, unless its removal failed.
    """
    place = _refuse_inside(
        tempfile.gettempdir() if parent is None else parent, keep_out
    )
    directory = tempfile.mkdtemp(prefix=_PREFIX, dir=place)
    try:
        found = _session(directory, timeout_s)
    finally:
        removed = _remove(directory)
    return SessionRun(*found, removed)
