"""The permission options and holder lists of a first-case turn session (ADR-0139, ADR-0146).

:func:`options` returns the arguments that :mod:`hilclaw.turn_loop` appends
to the command line of a turn after ``--strict-mcp-config``;
:func:`holder_lists` returns the lists the caller check of ADR-0146
(:mod:`hilclaw.caller_check`) reads, from the same files. It reads the
agent files of the definition that was put into the session directory and
joins them with the Round-Manager's fixed list. It makes no judgement, calls
no model, starts no process and writes nothing. This is runtime code: it is
built and tested against fixture files and a stub ``claude`` only, never
against a real session (D16).

**Decided by ADR-0139** and only applied here:

- the mode is :data:`PERMISSION_MODE`, passed explicitly (decision 2);
- the pre-approved list is the union of :data:`ROUND_MANAGER_TOOLS`, an
  ``Agent(<name>)`` for each agent and every entry of each agent's ``tools``
  list, all exact names, with no wildcard; it is sorted, without repeats, and
  passed as one argument joined by :data:`TOOLS_SEPARATOR` (decision 3);
- the built-in set is :data:`DELEGATION_TOOL` when at least one agent was
  read, plus every name of :data:`BUILT_IN_TOOLS` that the agents' ``tools``
  lists hold, sorted and joined the same way; with no agent it is the empty
  string (decision 4);
- the bare names ``Read``, ``Grep`` and ``Glob`` are pre-approved as written
  (decision 6);
- the setting sources are :data:`SETTING_SOURCES` (decision 7).

**The arguments**, in this order: :data:`OPT_SETTING_SOURCES` with
:data:`SETTING_SOURCES`, :data:`OPT_TOOLS` with the built-in set,
:data:`OPT_PERMISSION_MODE` with :data:`PERMISSION_MODE`, and
:data:`OPT_ALLOWED_TOOLS` with the pre-approved list. No model, turn-limit or
bypass option is among them (decision 10).

**The agent files** are the regular files whose names end in ``.md`` at any
depth under ``<session>/.claude/agents/``, read in the sorted order of their
relative paths; when that directory is absent there is no agent. A file must
be UTF-8 text whose first line is ``---`` and which has a later line
``---``; lines may end in ``\\n`` or ``\\r\\n``. Every line between the two is
``key: value``: a key of ASCII letters, digits, ``_`` and ``-`` beginning
with a letter, a ``:``, and a value taken with outer white space stripped;
each key at most once. Only ``name`` and ``tools`` are used. A ``name`` is
lowercase ASCII letters, digits and ``-``, beginning with a letter. ``tools``
is split on ``,`` and each entry stripped; an entry is either exactly
``mcp__hilclaw__<name>`` with ``<name>`` of lowercase ASCII letters, digits
and ``_`` beginning with a letter, or exactly one of :data:`BUILT_IN_TOOLS`.

**What is raised**, each before anything is returned: :class:`TypeError` for
a session directory that is not a ``str`` or path object; and a
:class:`ValueError` with a fixed text for ``.claude/agents`` that is no
directory, an agent file that is not UTF-8, one with no frontmatter or with a
line between the markers that is no ``key: value`` or repeats a key, one with
a missing or malformed ``name``, one with no ``tools`` key or an empty value
(an omitted list inherits every tool, ADR-0139 P8), one with a ``tools``
entry of any other form (a wildcard, ``mcp__hilclaw`` alone, another server's
name, ``Bash``, ``Write``, ``Edit``, ``Agent`` and every other built-in tool
among them) and one with a ``permissionMode`` key; and, added by ADR-0146
decision 3, two or more agent files with the same ``name`` and an agent file
whose ``name`` is ``general-purpose`` (the ``name`` form already excludes
``Explore`` and ``Plan``). Reading errors are raised unchanged.

The coder-driver's entry is derived with no change here (ADR-0141
decision 5; ADR-0139 decision 9, form (T)): its two ``mcp__hilclaw__`` names
are pre-approved beside ``Agent(coder-driver)``, and it adds no built-in
tool; a ``Bash`` entry is still refused.

Not done here: no check of a ``tools`` entry against the registry, only of
its form. The module gives the holder lists that the caller check hook of
ADR-0146 reads; it writes no settings file and sets no deny rule.

Runtime acceptance items it depends on (ADR-0139 Consequences): (xxxiv) the
options take effect in a never-trusted session directory; (xxxv) the
pre-approved ``hilclaw`` tools run without a prompt and others are denied
without a wait; (xxxvi) ``--tools`` accepts these names and leaves the
``hilclaw`` tools reachable; (xxxvii) a sub-agent runs in ``dontAsk`` under
the session's list; (xxxviii) ``Agent(<name>)`` lets the Round-Manager
delegate, and the list reaches Claude Code as written on Windows; (xxxix)
the bare read tools read outside the working directories; (xl) no setting of
the runtime user's ``~/.claude/settings.json`` acts on the session.
"""

import os
import re

from hilclaw import mcp_front

OPT_SETTING_SOURCES = "--setting-sources"
SETTING_SOURCES = "project"
OPT_TOOLS = "--tools"
OPT_PERMISSION_MODE = "--permission-mode"
PERMISSION_MODE = "dontAsk"
OPT_ALLOWED_TOOLS = "--allowedTools"
TOOLS_SEPARATOR = ","
DELEGATION_TOOL = "Agent"
BUILT_IN_TOOLS = ("Glob", "Grep", "Read")
AGENTS_DIRECTORY = (".claude", "agents")
ROUND_MANAGER_TOOLS = (
    "mcp__hilclaw__state_read",
    "mcp__hilclaw__instance_read",
    "mcp__hilclaw__run_fresh",
    "mcp__hilclaw__state_write",
    "mcp__hilclaw__run_commit",
    "mcp__hilclaw__key_store",
    "mcp__hilclaw__case_write",
    "mcp__hilclaw__round_end",
)

_MARKER = "---"
_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_NAME = re.compile(r"[a-z][a-z0-9-]*")
_MCP_TOOL = re.compile(rf"mcp__{re.escape(mcp_front.SERVER_NAME)}__[a-z][a-z0-9_]*")
_NO_DIRECTORY = "the agents entry of the session directory is no directory"
_NOT_UTF8 = "an agent file is not UTF-8"
_NO_FRONTMATTER = "an agent file has no frontmatter"
_NOT_A_KEY = "an agent file has a frontmatter line that is no 'key: value'"
_KEY_TWICE = "an agent file has a frontmatter key twice"
_BAD_NAME = "an agent file has no valid name"
_NO_TOOLS = "an agent file has no tools list"
_BAD_TOOL = "an agent file names a tool that is not admitted"
_PERMISSION_MODE = "an agent file sets permissionMode"
_NAME_TWICE = "two agent files have the same name"
_BUILT_IN_AGENT = "an agent file has the name of a built-in agent"
_BUILT_IN_AGENT_NAME = "general-purpose"


def _frontmatter(data):
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(_NOT_UTF8) from None
    lines = [line.removesuffix("\r") for line in text.split("\n")]
    if lines[0] != _MARKER or _MARKER not in lines[1:]:
        raise ValueError(_NO_FRONTMATTER)
    found = {}
    for line in lines[1 : lines.index(_MARKER, 1)]:
        key, separator, value = line.partition(":")
        if not separator or not _KEY.fullmatch(key):
            raise ValueError(_NOT_A_KEY)
        if key in found:
            raise ValueError(_KEY_TWICE)
        found[key] = value.strip()
    return found


def _agent(data):
    found = _frontmatter(data)
    if "permissionMode" in found:
        raise ValueError(_PERMISSION_MODE)
    name = found.get("name")
    if name is None or not _NAME.fullmatch(name):
        raise ValueError(_BAD_NAME)
    if name == _BUILT_IN_AGENT_NAME:
        raise ValueError(_BUILT_IN_AGENT)
    if not found.get("tools"):
        raise ValueError(_NO_TOOLS)
    tools = [entry.strip() for entry in found["tools"].split(TOOLS_SEPARATOR)]
    for entry in tools:
        if entry not in BUILT_IN_TOOLS and not _MCP_TOOL.fullmatch(entry):
            raise ValueError(_BAD_TOOL)
    return name, tools


def _agent_files(session):
    top = os.path.join(session, *AGENTS_DIRECTORY)
    if not os.path.lexists(top):
        return []
    if not os.path.isdir(top):
        raise ValueError(_NO_DIRECTORY)
    found = []
    for directory, _, names in os.walk(top):
        for name in names:
            path = os.path.join(directory, name)
            if name.endswith(".md") and os.path.isfile(path):
                found.append(os.path.relpath(path, top))
    return [os.path.join(top, relative) for relative in sorted(found)]


def _agents(session_dir):
    if isinstance(session_dir, os.PathLike):
        session_dir = os.fspath(session_dir)
    if type(session_dir) is not str:
        raise TypeError("the session directory must be a str or a path")
    agents = []
    for path in _agent_files(session_dir):
        with open(path, "rb") as file:
            agents.append(_agent(file.read()))
    names = [name for name, _ in agents]
    if len(set(names)) != len(names):
        raise ValueError(_NAME_TWICE)
    return agents


def holder_lists(session_dir):
    """Return the holder lists of the callers of a turn session in ``session_dir``.

    ``session_dir`` (a ``str`` or path object) is the session directory after
    the definition was put into it; its agent files are read at each call,
    with the reader and the refusals of :func:`options` (ADR-0146 decision 3).
    The result is a pair ``(main, agents)``: ``main`` is the main session's
    list, the tuple :data:`ROUND_MANAGER_TOOLS`; ``agents`` is a new ``dict``
    that maps the ``name`` of each agent file to a tuple of the
    ``mcp__hilclaw__`` entries of its ``tools`` list, in the order written;
    built-in entries are left out. Raises as the module docstring lists under
    "What is raised".
    """
    agents = {
        name: tuple(entry for entry in tools if entry not in BUILT_IN_TOOLS)
        for name, tools in _agents(session_dir)
    }
    return ROUND_MANAGER_TOOLS, agents


def options(session_dir):
    """Return the permission options of a turn session in ``session_dir`` as a tuple of ``str``.

    ``session_dir`` (a ``str`` or path object) is the session directory after
    the definition was put into it. The result is the four options and their
    values in the order the module docstring states, to be appended after
    ``--strict-mcp-config``. Raises as the module docstring lists under
    "What is raised".
    """
    agents = _agents(session_dir)
    built_in = set()
    allowed = set(ROUND_MANAGER_TOOLS)
    for name, tools in agents:
        built_in.add(DELEGATION_TOOL)
        built_in.update(entry for entry in tools if entry in BUILT_IN_TOOLS)
        allowed.add(f"{DELEGATION_TOOL}({name})")
        allowed.update(tools)
    return (
        OPT_SETTING_SOURCES,
        SETTING_SOURCES,
        OPT_TOOLS,
        TOOLS_SEPARATOR.join(sorted(built_in)),
        OPT_PERMISSION_MODE,
        PERMISSION_MODE,
        OPT_ALLOWED_TOOLS,
        TOOLS_SEPARATOR.join(sorted(allowed)),
    )
