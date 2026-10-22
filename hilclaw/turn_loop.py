"""The turn loop of a first-case run (ADR-0118 decision 3).

:func:`run` starts the turn sessions of one run, one after another. Before
every turn it asks its caller whether a further turn is to run; if so it makes
a session directory, has the caller put the definition into it, writes the
server configuration file and the hook settings file
``.claude/settings.json``, starts exactly one ``claude -p`` there, waits until
that process has ended, removes the directory and asks again. It returns one
:class:`Turn` per session started. This is runtime code: on a runtime machine
each turn starts the real ``claude`` and spends plan usage. It is built and
tested against a stub ``claude`` that the tests write, never against a real
one (D16); that a real session behaves as that stub does is shown by nothing
here.

**Decided by ADR-0118** and only applied here:

- one turn is one Claude Code process of its own, started fresh, and two
  turn sessions of one call are never running at once (decisions 2 and 3);
- the loop makes no judgement, calls no model and is no FR-10 tool
  (decision 3, in the sense of ADR-0115 decisions 2 and 3);
- the session directory lies outside the source checkout and the data
  checkout, and no directory from it up to the root holds a ``CLAUDE.md``,
  ``CLAUDE.local.md``, ``AGENTS.md`` or a ``.claude`` other than the runtime
  user's own configuration directory (decision 4);
- the definition is put into the session directory before each turn
  (decisions 4 and 5);
- the session is given the package's MCP front by a configuration file named
  with ``--mcp-config`` together with ``--strict-mcp-config``, and no
  ``.mcp.json`` is used (decision 6).

**Decided by ADR-0139** and only applied here: every turn session gets the
permission options of decisions 2-4, 6 and 7, built by
:func:`hilclaw.turn_permissions.options` from the session directory after the
definition was put into it.

**Decided by ADR-0141** and only applied here: every turn session gets the
environment of decision 4, in which ``CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT`` is
``0`` and ``CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`` is ``1``, each replacing
any value the caller had, and ``CLAUDE_AUTO_BACKGROUND_TASKS`` is removed.

**Decided by ADR-0146** and only applied here: after the definition is put,
every turn writes the session directory's ``.claude/settings.json`` with one
``hooks`` member and nothing else, no ``permissions`` and no ``env``
(decision 4; ADR-0139 decision 8). The first of its two ``PreToolUse``
entries is one whose matcher is a regular expression anchored to
:data:`hilclaw.caller_check.TOOL_PREFIX` and whose one hook is a ``command``
hook in exec form: ``command`` the absolute path of :data:`sys.executable`,
``args`` ``-I``, ``-c``, :data:`hilclaw.caller_check.START` and the directory
holding this package, ``"onFailure": "block"`` and a ``timeout`` well below
the default. A definition that brings its own ``.claude/settings.json`` is
refused rather than merged or overwritten.

**Decided by ADR-0147** and only applied here: the second ``PreToolUse``
entry, in the same exec form with ``"onFailure": "block"``, has a matcher that
is the exact list of :data:`hilclaw.budget_check.SPENDING_TOOLS` and runs
:data:`hilclaw.budget_check.START` with the directory holding this package and,
as the last ``args`` element, the same real absolute path of ``data_root``
that the server entry's ``env`` holds (decision 4). The settings still hold
no ``env``.

**Decided by ADR-0148** and only applied here: :func:`run` takes the run id
as a required argument, checks it as :func:`hilclaw.layout.check_run_id`
does, reads nothing by it, compares it with nothing and puts it nowhere but
into the ``Stop`` entry (decision 4). That entry, the second member of
``hooks``, is an array of one entry with no ``matcher`` whose one hook is a
``command`` hook in the same exec form: ``args`` ``-I``, ``-c``,
:data:`hilclaw.stop_check.START`, the directory holding this package, the run
id and, last, the same real absolute path of ``data_root`` as the second
``PreToolUse`` entry; a ``timeout`` well below the default and no
``onFailure``, which has no effect on ``Stop``. ADR-0148 so revises ADR-0146
decision 4, as revised by ADR-0147 decision 4, to the two ``PreToolUse``
entries and this one ``Stop`` entry, and nothing else.

**The command line** is :data:`PROGRAM`, :data:`OPT_PRINT` with the caller's
prompt, :data:`OPT_MCP_CONFIG` with :data:`CONFIG_FILE` and
:data:`OPT_STRICT_MCP_CONFIG`, followed by the arguments that
:func:`hilclaw.turn_permissions.options` returns for the session directory.
The program is looked up on the ``PATH`` at every turn. The configuration
file is named by its file name alone, so no path is in an argument. The
options passed besides are ``--setting-sources project``, ``--tools`` with
the built-in set, ``--permission-mode dontAsk`` and ``--allowedTools`` with
the pre-approved list; no model, turn-limit or bypass option is passed
(ADR-0139 decision 10). The session's working directory is the session
directory, its standard input is closed, and it gets the environment of the
calling process as read at that turn, with only the three changes of ADR-0141
decision 4, the calling process's own environment left as it is; its
standard output and standard error are those of the calling process and are
not read here. The wait has no time limit of its own: a limit on a turn is
OD-19's or OD-14's.

**Choices of this module** (ADR-0118 leaves them to the code):

- *A directory per turn*, made by :func:`tempfile.mkdtemp` under ``parent``
  (by default the temporary directory of the system) and removed after the
  turn. Each turn so starts from the definition as it then is, with nothing
  left from an earlier turn, and nothing a run needs lives there (NFR-1). Auto
  memory or agent memory kept there is lost with each turn, which decision 4
  allows; where agent memory is kept is OD-24.
- *The place*: before the first turn and again before each turn, ``parent``
  is refused with a fixed text if, by real path, it is, lies inside or
  contains the directory that holds this package, ``data_root`` or a directory
  of ``keep_out`` (:mod:`hilclaw.checkout_boundary`), or if it or a directory
  above it holds an entry named as in :data:`MARKERS`. The one entry allowed
  is ``Path.home() / ".claude"``, compared by real path. A file placed there
  between two turns stops the next one.
- *The data root and the image reach the server through the environment*:
  the entry's ``env`` holds :data:`hilclaw.config.ENV_LOCAL_PATH` with the
  real absolute path of ``data_root``, so the server names the same data root
  whatever its working directory is, and, only when the calling process's
  environment holds :data:`hilclaw.standin_image.ENV_IMAGE` with a non-empty
  value, that variable with that value unchanged and unchecked (ADR-0144
  decision 5: the process that runs the operation; the server's
  :func:`hilclaw.standin_image.read_image` refuses a bad one). Nothing else
  of the environment is copied there. The value is read once, when
  :func:`run` builds the configuration, so every turn of one loop names the
  same image. That the ``env`` member reaches the server process is what a
  passed self-check of ADR-0054 shows, whose tokens travel the same way.
- *The server entry* is ``command`` :data:`sys.executable`, ``args`` ``-I``,
  ``-c``, a start text that puts the directory holding this package first on
  ``sys.path`` and runs :func:`hilclaw.mcp_front.main`, and that directory;
  so the server finds this package from the session directory.
- *The hook settings*: the matcher is ``^`` followed by
  :data:`hilclaw.caller_check.TOOL_PREFIX`; the ``^`` both anchors it and
  holds it outside the exact-match set, so it is read as a regular
  expression. The second matcher joins the spending tools with ``|``, all of
  whose characters are in the exact-match set. Both ``PreToolUse`` timeouts
  are :data:`HOOK_TIMEOUT_S`, 30 seconds: an interpreter start and a read of
  the agent files or of two run files take well under that, and with
  ``onFailure`` a hook that hangs blocks the call within it. The ``Stop``
  timeout is :data:`STOP_HOOK_TIMEOUT_S`, 60 seconds: that hook runs ``git``
  a few times on the data checkout (ADR-0148 item (lxv)), and one that times
  out only lets the stop through. The members of ``hooks`` are written
  ``PreToolUse`` first, then ``Stop``. A ``data_root`` whose real path holds
  one of the path placeholders that Claude Code substitutes into exec-form
  ``args`` (``${CLAUDE_PROJECT_DIR}``, ``${CLAUDE_PLUGIN_ROOT}``,
  ``${CLAUDE_PLUGIN_DATA}``) is refused, since the hooks would read another
  root than the server's. The text is built once per loop, as the server
  configuration is, and written with exclusive creation in every turn. A
  missing ``.claude`` is made as a plain directory.
- *The prompt* is one line of ASCII letters, digits, spaces, ``.``, ``,``,
  ``_`` and ``-``, not beginning with ``-``: on Windows the ``claude`` found
  may be a command script, whose arguments pass through the command
  interpreter. ``-`` is admitted because a built run id holds it (ADR-0123
  decision 3), and never first, so the prompt cannot read as an option.
- *The removal* is tried whatever happened, an exception included, and is
  tried again a few times within about two seconds (on Windows a process that
  outlives the session can keep a file open); one that still fails is
  carried as ``removed`` false and raises nothing.

**What is raised**, each before the first turn unless said otherwise:
:class:`TypeError` or :class:`ValueError` for a bad argument, among them
:class:`hilclaw.layout.InvalidPathValueError` for a refused ``run_id``,
raised before any other argument but the two callables is checked;
:class:`ValueError` with a fixed text for a refused place, also before a later
turn; :class:`ValueError` with a fixed text for a ``data_root`` holding a path
placeholder; :class:`RuntimeError` when the interpreter does not know its own
path;
:class:`TypeError` for an answer of ``further_turn`` that is not a ``bool``;
:class:`ValueError` when ``put_definition`` made :data:`CONFIG_FILE`;
:class:`ValueError` with a fixed text when the session directory's
``.claude`` is a symbolic link, a junction or no directory, and when
``.claude/settings.json`` exists after ``put_definition``, each before the
settings file is written and the process starts;
:class:`ValueError` with a fixed text when the definition put into the
session directory holds an agent file that
:func:`hilclaw.turn_permissions.options` refuses, before the process starts;
:class:`ClaudeNotFoundError` when no ``claude`` is found at a turn; and,
unchanged, what ``further_turn``, ``put_definition``, making the directory,
writing the files or starting the process raise. Whatever is raised after a
directory was made comes after its removal, and the :class:`Turn` records of
the turns already run are lost to the caller then.

Not done here: no lock against two loops on one run (#4 §2e, OD-17); no
command-line entry, which is :mod:`hilclaw.turn_start`, the caller of this
module; no layout of the definition, which is the caller's
``put_definition``; no round-0 step; no self-check, which
for a first-case run the entry runs before the first turn (ADR-0125); no
policy after a failed turn, only the exit status passed on to
``further_turn`` (for a first-case run that policy is the entry's, by
ADR-0122); no data-plane write.

Runtime acceptance items it depends on (ADR-0118 Consequences): (i) the
session loads the session directory's files and none of this repository;
(iv) ``--mcp-config`` with ``--strict-mcp-config`` gives the ``hilclaw``
server to every turn and the server started from the session directory finds
the package; (v) a ``-p`` turn session exits after its last reply, so the wait
ends; (vi) the exit status tells a session that ended well from a failed one;
(ADR-0139 Consequences) (xxxiv)-(xl), listed in
:mod:`hilclaw.turn_permissions`; (ADR-0141 Consequences) (xli) and
(xlii); (ADR-0146 Consequences) (lvi)-(lx), listed in
:mod:`hilclaw.caller_check`, of which (lvi) and (lviii)-(lx) apply to the
second entry too and (lix) to its data-root argument; and (ADR-0147
Consequences) (lxi) and (lxii), listed in :mod:`hilclaw.budget_check`; and
(ADR-0148 Consequences) (lxiii)-(lxvi), listed in :mod:`hilclaw.stop_check`,
with ADR-0146 (lvi), (lix) and (lx) applying to the ``Stop`` entry too and
(lix) to its run-id and data-root arguments. The stub shows nothing of a real
session's reading of the environment.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import NamedTuple

from hilclaw import (
    budget_check,
    caller_check,
    config,
    layout,
    mcp_front,
    standin_image,
    stop_check,
    turn_permissions,
)
from hilclaw import checkout_boundary as _checkout_boundary

PROGRAM = "claude"
OPT_PRINT = "-p"
OPT_MCP_CONFIG = "--mcp-config"
OPT_STRICT_MCP_CONFIG = "--strict-mcp-config"
SERVERS_MEMBER = "mcpServers"
CONFIG_FILE = "hilclaw-turn.mcp-config.json"
MARKERS = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude")
SETTINGS_DIRECTORY = ".claude"
SETTINGS_FILE = "settings.json"
HOOK_TIMEOUT_S = 30
STOP_HOOK_TIMEOUT_S = 60

_ENV_SET = (
    ("CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT", "0"),
    ("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS", "1"),
)
_ENV_REMOVED = ("CLAUDE_AUTO_BACKGROUND_TASKS",)

_PREFIX = "hilclaw-turn-"
_PROMPT = re.compile(r"[A-Za-z0-9 .,_][A-Za-z0-9 .,_-]*")
_REMOVE_PAUSES_S = (0.0, 0.2, 0.6, 1.2)
_START = (
    "import sys; sys.path.insert(0, sys.argv.pop(1)); "
    "from hilclaw.mcp_front import main; raise SystemExit(main())"
)
_MEETS_CHECKOUT = "the session directory would meet a checkout"
_MARKER_ABOVE = (
    "an instruction file or a foreign .claude lies above the session directory"
)
_CONFIG_TAKEN = "the definition holds the name of the server configuration file"
_SETTINGS_TAKEN = "the definition holds the hook settings file"
_NOT_PLAIN = "the session directory's .claude is no plain directory"
_PLACEHOLDERS = (
    "${CLAUDE_PROJECT_DIR}",
    "${CLAUDE_PLUGIN_ROOT}",
    "${CLAUDE_PLUGIN_DATA}",
)
_PLACEHOLDER_HELD = "data_root holds a hook path placeholder"


class ClaudeNotFoundError(LookupError):
    """No ``claude`` was found on the ``PATH`` at a turn; no session was started."""


class Turn(NamedTuple):
    """One turn session that :func:`run` started.

    - ``exit_status``: the exit status of its process (``int``), as
      :attr:`subprocess.Popen.returncode` gives it: negative on POSIX for a
      process ended by a signal.
    - ``removed``: its session directory is gone.
    """

    exit_status: int
    removed: bool


def _real(path, what):
    if isinstance(path, (str, os.PathLike)):
        path = os.fspath(path)
    if type(path) is not str:
        raise TypeError(f"{what} must be a str or a path")
    return os.path.realpath(path)


def _folded(path):
    return os.path.normcase(os.path.realpath(path))


def _check_prompt(prompt):
    if type(prompt) is not str:
        raise TypeError("the prompt must be a str")
    if not _PROMPT.fullmatch(prompt):
        raise ValueError(
            "the prompt must be one non-empty line of ASCII letters, digits, "
            "spaces, '.', ',', '_' and '-', not beginning with '-'"
        )


def _data_root(data_root):
    root = _real(data_root, "data_root")
    if not os.path.isdir(root):
        raise ValueError("data_root must name an existing directory")
    return root


def _config_text(root):
    if not sys.executable:
        raise RuntimeError("the interpreter does not know its own path")
    entry = {
        "command": sys.executable,
        "args": ["-I", "-c", _START, _checkout_boundary.PACKAGE_DIRECTORY],
        "env": {config.ENV_LOCAL_PATH: root},
    }
    image = os.environ.get(standin_image.ENV_IMAGE)
    if image:
        entry["env"][standin_image.ENV_IMAGE] = image
    return json.dumps({SERVERS_MEMBER: {mcp_front.SERVER_NAME: entry}})


def _hook(timeout, *args):
    return {
        "type": "command",
        "command": os.path.abspath(sys.executable),
        "args": ["-I", "-c", *args],
        "timeout": timeout,
    }


def _entry(matcher, *args):
    hook = _hook(HOOK_TIMEOUT_S, *args)
    hook["onFailure"] = "block"
    return {"matcher": matcher, "hooks": [hook]}


def _settings_text(root, run_id):
    if any(placeholder in root for placeholder in _PLACEHOLDERS):
        raise ValueError(_PLACEHOLDER_HELD)
    package = _checkout_boundary.PACKAGE_DIRECTORY
    entries = [
        _entry("^" + caller_check.TOOL_PREFIX, caller_check.START, package),
        _entry(
            "|".join(budget_check.SPENDING_TOOLS), budget_check.START, package, root
        ),
    ]
    stop = _hook(STOP_HOOK_TIMEOUT_S, stop_check.START, package, run_id, root)
    hooks = {caller_check.EVENT: entries, stop_check.EVENT: [{"hooks": [stop]}]}
    return json.dumps({"hooks": hooks})


def _write_settings(directory, text):
    folder = os.path.join(directory, SETTINGS_DIRECTORY)
    if not os.path.lexists(folder):
        os.mkdir(folder)
    plain = os.path.normcase(
        os.path.join(os.path.realpath(directory), SETTINGS_DIRECTORY)
    )
    if os.path.islink(folder) or not os.path.isdir(folder) or _folded(folder) != plain:
        raise ValueError(_NOT_PLAIN)
    place = os.path.join(folder, SETTINGS_FILE)
    if os.path.lexists(place):
        raise ValueError(_SETTINGS_TAKEN)
    with open(place, "x", encoding="utf-8") as file:
        file.write(text)


def _own_configuration():
    try:
        return _folded(Path.home() / ".claude")
    except RuntimeError:
        return None


def _marker_above(place):
    own = _own_configuration()
    directory = place
    while True:
        for name in MARKERS:
            found = os.path.join(directory, name)
            if os.path.lexists(found) and not (
                name == ".claude" and _folded(found) == own
            ):
                return True
        above = os.path.dirname(directory)
        if above == directory:
            return False
        directory = above


def _check_place(place, roots):
    if _checkout_boundary.meets_checkout(place, roots, containing=True):
        raise ValueError(_MEETS_CHECKOUT)
    if _marker_above(place):
        raise ValueError(_MARKER_ABOVE)


def _remove(directory):
    for pause in _REMOVE_PAUSES_S:
        time.sleep(pause)
        shutil.rmtree(directory, ignore_errors=True)
        if not os.path.lexists(directory):
            return True
    return False


def _environment():
    environment = dict(os.environ)
    environment.update(_ENV_SET)
    for name in _ENV_REMOVED:
        environment.pop(name, None)
    return environment


def _turn(directory, put_definition, prompt, text, settings):
    put_definition(Path(directory))
    place = os.path.join(directory, CONFIG_FILE)
    if os.path.lexists(place):
        raise ValueError(_CONFIG_TAKEN)
    _write_settings(directory, settings)
    with open(place, "x", encoding="utf-8") as file:
        file.write(text)
    permissions = turn_permissions.options(directory)
    found = shutil.which(PROGRAM)
    if found is None:
        raise ClaudeNotFoundError(f"program not found or not executable: {PROGRAM!r}")
    command = (
        os.path.abspath(found),
        OPT_PRINT,
        prompt,
        OPT_MCP_CONFIG,
        CONFIG_FILE,
        OPT_STRICT_MCP_CONFIG,
        *permissions,
    )
    done = subprocess.run(
        command,
        cwd=directory,
        stdin=subprocess.DEVNULL,
        env=_environment(),
        check=False,
    )
    return done.returncode


def run(
    *,
    further_turn,
    put_definition,
    prompt,
    data_root,
    run_id,
    parent=None,
    keep_out=(),
):
    """Run the turns of one run until ``further_turn`` answers ``False``; return their :class:`Turn` records.

    ``further_turn`` is called with ``None`` before the first turn and with
    the exit status of the last turn session after each, and must answer a
    ``bool``. ``put_definition`` is called with the session directory, a
    :class:`pathlib.Path`, before the configuration and settings files are
    written; what it returns is ignored. ``prompt`` is the one-line prompt of
    every turn.
    ``data_root`` (a ``str`` or path object) names the existing directory of
    the data checkout. ``run_id`` is the run's id, checked as
    :func:`hilclaw.layout.check_run_id` does and written only into the
    ``Stop`` entry of the hook settings. ``parent`` is the directory the
    session directories are made in (``None``: the temporary directory of the
    system) and ``keep_out`` a sequence of further directories it must not
    meet. Returns a tuple of :class:`Turn`, one per session started, in
    order. Raises as the module docstring lists under "What is raised".
    """
    for name, value in (
        ("further_turn", further_turn),
        ("put_definition", put_definition),
    ):
        if not callable(value):
            raise TypeError(f"{name} must be callable")
    layout.check_run_id(run_id)
    _check_prompt(prompt)
    root = _data_root(data_root)
    _checkout_boundary.refuse_one_path(keep_out)
    roots = (root, *(_real(path, "a directory of keep_out") for path in keep_out))
    text = _config_text(root)
    settings = _settings_text(root, run_id)
    place = _real(tempfile.gettempdir() if parent is None else parent, "the parent")
    if not os.path.isdir(place):
        raise ValueError("the parent must be an existing directory")
    _check_place(place, roots)
    turns = []
    previous = None
    while True:
        answer = further_turn(previous)
        if type(answer) is not bool:
            raise TypeError("further_turn must answer a bool")
        if not answer:
            return tuple(turns)
        _check_place(place, roots)
        directory = tempfile.mkdtemp(prefix=_PREFIX, dir=place)
        try:
            previous = _turn(directory, put_definition, prompt, text, settings)
        finally:
            removed = _remove(directory)
        turns.append(Turn(previous, removed))
