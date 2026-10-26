"""The copy of the definition into a turn session directory (ADR-0118 decisions 4 and 5).

:func:`put` copies the runtime's layer-1 definition from ``orchestration/``
into a session directory, under the names Claude Code reads there. It is the
``put_definition`` that the caller of :func:`hilclaw.turn_loop.run` passes.
It makes no judgement, calls no model, starts no process and writes nothing
outside the session directory.

**Decided by ADR-0118** and only applied here:

- the definition lives in the top-level directory ``orchestration/`` of this
  repository, and its files get the names Claude Code reads only in the
  session directory: a project ``CLAUDE.md``, ``.claude/agents/``,
  ``.claude/skills/`` and ``.claude/settings.json`` (decision 5);
- no entry under ``orchestration/`` is named ``CLAUDE.md``,
  ``CLAUDE.local.md`` or ``AGENTS.md``, and no directory there is named
  ``.claude`` (decision 5, naming rule);
- the copy replaces whatever definition the session directory held before
  (decision 4).

**Choices of this module** (decision 5 leaves them to the definition task):

- *The layout* of ``orchestration/`` is :data:`LAYOUT`, written here and
  nowhere else: ``round-manager.md`` becomes ``CLAUDE.md``, since the
  Round-Manager is the main conversation of the turn session (decision 2);
  the directories ``agents/`` and ``skills/`` become ``.claude/agents/`` and
  ``.claude/skills/``; ``settings.json`` becomes ``.claude/settings.json``.
  Only ``round-manager.md`` is required; the other entries are copied when
  present, and when absent their targets are removed from the session
  directory, so the copy is the definition as it now is. Nothing else in the
  session directory is touched, :data:`hilclaw.turn_loop.CONFIG_FILE`
  included. Content is copied byte for byte; modes and times do not matter.
- *The prompt*: ``orchestration/round-manager.md`` states the turn contract
  of decision 2 and the entry of a turn (first the commit of whatever is
  owed, then the first ``STATE.json``, the over states and the round-budget
  end); every end of the session after a successful entry commit calls
  ``run.commit`` as its last act (ADR-0143 decision 2); a round begins with
  the store of the run's key record files and ends with the case (in a
  round >= 1), the round-end write and the commit; in round 0 a turn
  delegates the coder call to the coder-driver after the key store and,
  when the call brought something in, the sim-point and then the
  board-point check to the evaluator and, when both verified, the board
  measurement to the experiment-runner; on a completed measurement it goes
  to the closing steps, and otherwise it stops. In a round >= 1 a turn
  delegates the selection to the technique-selector after the key store,
  then reads the round's hypothesis record with ``hypotheses.read``, and
  stops: the later steps are not yet defined (ADR-0132 decision 6). The
  stop writes nothing else and ends no round.
- *Refusals*, each a :class:`ValueError` with a fixed text raised before
  anything is written: a top-level entry that is not a key of :data:`LAYOUT`;
  an entry of the wrong kind; a missing ``round-manager.md``; an entry at any
  depth named as in :data:`hilclaw.turn_loop.MARKERS`, compared as that
  module does (folded where the file system ignores case); a symbolic link
  or junction, or an entry that is neither a file nor a directory, at any
  depth; and, in the session directory, a ``.claude`` that is no plain
  directory or a link where a target goes.

**What is raised** besides those: :class:`TypeError` for an argument that is
not a ``str`` or path object; :class:`FileNotFoundError` for a missing
``source`` and :class:`ValueError` for one that is no directory;
:class:`ValueError` for a ``session_dir`` that is no existing directory; and,
unchanged, what reading, removing or copying raises.

The roster: ``orchestration/agents/`` holds the evaluator's definition
(ADR-0128 decision 7), the coder-driver's (ADR-0126 decision 6; ADR-0141
decision 5), the experiment-runner's (ADR-0142 decision 4) and the
technique-selector's (ADR-0132 decision 7), and the rest of the roster
stays open (OD-23).

Not done here: no skills, no settings, hooks or permissions (PLAN P2-4;
ADR-0118 decision 4, "Workspace trust"), no round steps of a round >= 1
between the read of the round's hypothesis record and the closing steps
(later P2-1 slices), no ``--add-dir`` or other way for the session to reach
the run's files (decision 4), no caller and no command-line entry.

Runtime acceptance items it depends on (ADR-0118 Consequences): (i) a
session started in the session directory loads its ``CLAUDE.md``,
``.claude/agents/``, ``.claude/skills/`` and ``.claude/settings.json`` and no
file of this repository; (iii) a sub-agent defined in its ``.claude/agents/``
is found and the main session of a ``-p`` run delegates to it; and
(ADR-0128 Consequences) (xviii) the evaluator gets exactly the tools its
``tools`` list names; and (ADR-0132 Consequences) (xxiii) so does the
technique-selector.
"""

import os
import shutil
import stat
from pathlib import Path

from hilclaw.turn_loop import MARKERS

SOURCE = Path(__file__).resolve().parent.parent / "orchestration"
PROMPT = "round-manager.md"
LAYOUT = {
    PROMPT: ("CLAUDE.md",),
    "agents": (".claude", "agents"),
    "skills": (".claude", "skills"),
    "settings.json": (".claude", "settings.json"),
}
DIRECTORIES = frozenset({"agents", "skills"})

_FILE = "file"
_DIRECTORY = "directory"
_JUNCTION_TAG = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0xA0000003)
_FOLDED_MARKERS = frozenset(os.path.normcase(name) for name in MARKERS)
_UNKNOWN = "the definition holds an entry that is not in the layout"
_WRONG_KIND = "an entry of the definition is of the wrong kind"
_NO_PROMPT = "the definition holds no round-manager.md"
_MARKER = "the definition holds an instruction file or a .claude"
_LINK = "the definition holds a symbolic link or a junction"
_OTHER = "the definition holds an entry that is neither a file nor a directory"
_SESSION_CLAUDE = "the session directory holds a .claude that is no plain directory"
_SESSION_LINK = "the session directory holds a link where the definition goes"


def _text(path, what):
    if isinstance(path, (str, os.PathLike)):
        path = os.fspath(path)
    if type(path) is not str:
        raise TypeError(f"{what} must be a str or a path")
    return path


def _kind(path):
    examined = os.lstat(path)
    if stat.S_ISLNK(examined.st_mode):
        return None
    if getattr(examined, "st_reparse_tag", 0) == _JUNCTION_TAG:
        return None
    if stat.S_ISDIR(examined.st_mode):
        return _DIRECTORY
    if stat.S_ISREG(examined.st_mode):
        return _FILE
    return ""


def _check_entry(path, name):
    if os.path.normcase(name) in _FOLDED_MARKERS:
        raise ValueError(_MARKER)
    kind = _kind(path)
    if kind is None:
        raise ValueError(_LINK)
    if not kind:
        raise ValueError(_OTHER)
    if kind == _DIRECTORY:
        for entry in os.scandir(path):
            _check_entry(entry.path, entry.name)
    return kind


def _check_source(source):
    present = {}
    for entry in os.scandir(source):
        kind = _check_entry(entry.path, entry.name)
        present[entry.name] = kind
    for name, kind in present.items():
        if name not in LAYOUT:
            raise ValueError(_UNKNOWN)
        if (kind == _DIRECTORY) != (name in DIRECTORIES):
            raise ValueError(_WRONG_KIND)
    if PROMPT not in present:
        raise ValueError(_NO_PROMPT)
    return present


def _check_session(session):
    claude = os.path.join(session, ".claude")
    if os.path.lexists(claude) and _kind(claude) != _DIRECTORY:
        raise ValueError(_SESSION_CLAUDE)
    for parts in LAYOUT.values():
        target = os.path.join(session, *parts)
        if os.path.lexists(target) and _kind(target) is None:
            raise ValueError(_SESSION_LINK)


def _remove(target):
    if not os.path.lexists(target):
        return
    if _kind(target) == _DIRECTORY:
        shutil.rmtree(target)
    else:
        os.unlink(target)


def put(session_dir, *, source=None):
    """Copy the definition in ``source`` into ``session_dir`` under the names of :data:`LAYOUT`.

    ``session_dir`` (a ``str`` or path object) names an existing directory;
    it is the one argument :func:`hilclaw.turn_loop.run` passes to its
    ``put_definition``. ``source`` (a ``str`` or path object; ``None``:
    :data:`SOURCE`) names the existing directory that holds the definition.
    Every check of the module docstring is made before anything is written;
    then the target of each entry of :data:`LAYOUT` is removed from
    ``session_dir`` if it exists, and the entry, if present in ``source``, is
    copied there, ``.claude`` being made when needed. Returns ``None``.
    Raises as the module docstring lists.
    """
    session = _text(session_dir, "session_dir")
    origin = _text(SOURCE if source is None else source, "source")
    if not os.path.exists(origin):
        raise FileNotFoundError(f"source does not exist: {origin!r}")
    if not os.path.isdir(origin):
        raise ValueError("source must name a directory")
    if not os.path.isdir(session):
        raise ValueError("session_dir must name an existing directory")
    present = _check_source(origin)
    _check_session(session)
    for name, parts in LAYOUT.items():
        target = os.path.join(session, *parts)
        _remove(target)
        if name not in present:
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if name in DIRECTORIES:
            shutil.copytree(
                os.path.join(origin, name), target, copy_function=shutil.copyfile
            )
        else:
            shutil.copyfile(os.path.join(origin, name), target)
