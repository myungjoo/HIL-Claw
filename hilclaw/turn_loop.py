"""The turn loop of a first-case run (ADR-0118 decision 3).

:func:`run` starts the turn sessions of one run, one after another. Before
every turn it asks its caller whether a further turn is to run; if so it makes
a session directory, has the caller put the definition into it, writes the
server configuration file, starts exactly one ``claude -p`` there, waits until
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

**The command line** is :data:`PROGRAM`, :data:`OPT_PRINT` with the caller's
prompt, :data:`OPT_MCP_CONFIG` with :data:`CONFIG_FILE` and
:data:`OPT_STRICT_MCP_CONFIG`, and nothing else. The program is looked up on
the ``PATH`` at every turn. The configuration file is named by its file name
alone, so no path is in an argument. No permission, model, turn-limit,
setting-source or bypass option is passed: how a turn session is given its
permissions is not decided (ADR-0118 decision 4, "Workspace trust"). The
session's working directory is the session directory, its standard input is
closed, and it gets the environment of the calling process unchanged; its
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
- *The data root reaches the server through the environment*: the entry's
  ``env`` is exactly :data:`hilclaw.config.ENV_LOCAL_PATH` with the real
  absolute path of ``data_root``, so the server names the same data root
  whatever its working directory is.
- *The server entry* is ``command`` :data:`sys.executable`, ``args`` ``-I``,
  ``-c``, a start text that puts the directory holding this package first on
  ``sys.path`` and runs :func:`hilclaw.mcp_front.main`, and that directory;
  so the server finds this package from the session directory.
- *The prompt* is one line of ASCII letters, digits, spaces, ``.``, ``,`` and
  ``_``: on Windows the ``claude`` found may be a command script, whose
  arguments pass through the command interpreter.
- *The removal* is tried whatever happened, an exception included, and is
  tried again a few times within about two seconds (on Windows a process that
  outlives the session can keep a file open); one that still fails is
  carried as ``removed`` false and raises nothing.

**What is raised**, each before the first turn unless said otherwise:
:class:`TypeError` or :class:`ValueError` for a bad argument;
:class:`ValueError` with a fixed text for a refused place, also before a later
turn; :class:`RuntimeError` when the interpreter does not know its own path;
:class:`TypeError` for an answer of ``further_turn`` that is not a ``bool``;
:class:`ValueError` when ``put_definition`` made :data:`CONFIG_FILE`;
:class:`ClaudeNotFoundError` when no ``claude`` is found at a turn; and,
unchanged, what ``further_turn``, ``put_definition``, making the directory,
writing the file or starting the process raise. Whatever is raised after a
directory was made comes after its removal, and the :class:`Turn` records of
the turns already run are lost to the caller then.

Not done here: no lock against two loops on one run (#4 §2e, OD-17); no
command-line entry, which waits on the OD-8 member that says a run is over,
stopped or waiting (until then the caller's predicate stands for it); no
layout of the definition, which is the caller's ``put_definition``; no
permissions; no round-0 step and no self-check before a turn (OD-18 ⑯ (가));
no policy after a failed turn (retry, stop, wait, notify: OD-10, OD-17, OD-19,
OD-27), only the exit status passed on; no data-plane write; no caller.
Nothing calls the module yet.

Runtime acceptance items it depends on (ADR-0118 Consequences): (i) the
session loads the session directory's files and none of this repository;
(iv) ``--mcp-config`` with ``--strict-mcp-config`` gives the ``hilclaw``
server to every turn and the server started from the session directory finds
the package; (v) a ``-p`` turn session exits after its last reply, so the wait
ends; (vi) the exit status tells a session that ended well from a failed one.
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

from hilclaw import checkout_boundary as _checkout_boundary
from hilclaw import config, mcp_front

PROGRAM = "claude"
OPT_PRINT = "-p"
OPT_MCP_CONFIG = "--mcp-config"
OPT_STRICT_MCP_CONFIG = "--strict-mcp-config"
SERVERS_MEMBER = "mcpServers"
CONFIG_FILE = "hilclaw-turn.mcp-config.json"
MARKERS = ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md", ".claude")

_PREFIX = "hilclaw-turn-"
_PROMPT = re.compile(r"[A-Za-z0-9 .,_]+")
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
            "spaces, '.', ',' and '_'"
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
    return json.dumps({SERVERS_MEMBER: {mcp_front.SERVER_NAME: entry}})


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


def _turn(directory, put_definition, prompt, text):
    put_definition(Path(directory))
    place = os.path.join(directory, CONFIG_FILE)
    if os.path.lexists(place):
        raise ValueError(_CONFIG_TAKEN)
    with open(place, "x", encoding="utf-8") as file:
        file.write(text)
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
    )
    done = subprocess.run(command, cwd=directory, stdin=subprocess.DEVNULL, check=False)
    return done.returncode


def run(*, further_turn, put_definition, prompt, data_root, parent=None, keep_out=()):
    """Run the turns of one run until ``further_turn`` answers ``False``; return their :class:`Turn` records.

    ``further_turn`` is called with ``None`` before the first turn and with
    the exit status of the last turn session after each, and must answer a
    ``bool``. ``put_definition`` is called with the session directory, a
    :class:`pathlib.Path`, before the configuration file is written; what it
    returns is ignored. ``prompt`` is the one-line prompt of every turn.
    ``data_root`` (a ``str`` or path object) names the existing directory of
    the data checkout. ``parent`` is the directory the session directories
    are made in (``None``: the temporary directory of the system) and
    ``keep_out`` a sequence of further directories it must not meet. Returns
    a tuple of :class:`Turn`, one per session started, in order. Raises as
    the module docstring lists under "What is raised".
    """
    for name, value in (
        ("further_turn", further_turn),
        ("put_definition", put_definition),
    ):
        if not callable(value):
            raise TypeError(f"{name} must be callable")
    _check_prompt(prompt)
    root = _data_root(data_root)
    _checkout_boundary.refuse_one_path(keep_out)
    roots = (root, *(_real(path, "a directory of keep_out") for path in keep_out))
    text = _config_text(root)
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
            previous = _turn(directory, put_definition, prompt, text)
        finally:
            removed = _remove(directory)
        turns.append(Turn(previous, removed))
