"""The tool ``verdicts.read``, which reads a round's ``eval/verdicts.json`` for the technique-selector (ADR-0174 decision 2).

For the runs of ADR-0120 decision 1 the ``technique-selector`` sub-agent
takes the verdicts of the earlier rounds of its run as input through this
tool, one call per round, before it writes the round's hypothesis record
(ADR-0174 decision 6). It is a tool of the registry beside the FR-10 tools,
not an FR-10 tool: it is not journaled, appends no line to ``events.ndjson``,
selects no backend and keeps nothing between calls (ADR-0174 decision 3).

The request is exactly ``{"run_id": ..., "round": ...}``: ``round`` is an
``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`, a ``bool`` being none.
The data root comes from the data-root source, asked at each call after the
request was checked, and never from the request (ADR-0015 decision 3). The
result is ``{"record": ...}``: the document :func:`hilclaw.verdicts_file.parse`
returned for the file, members as stored, unknown top-level members included.

The checks, in this order, each with its kind (ADR-0174 decisions 2 and 3):

1. the request, round 0 among its refusals (``invalid_request``);
2. the data root (``no_data_root``);
3. the read of the round's file: no file there
   (:data:`KIND_VERDICTS_MISSING`, the message saying so when the data root
   is not an existing directory either), a place holding no regular file or
   bytes :func:`hilclaw.verdicts_file.parse` refuses
   (:data:`KIND_VERDICTS_INVALID`), another ``schema_version``
   (:data:`KIND_VERDICTS_UNSUPPORTED`), any other failing read
   (:data:`KIND_VERDICTS_UNREADABLE`);
4. the document's ``run_id``, then its ``round``, against the request's
   (:data:`KIND_VERDICTS_INVALID`).

The last three kinds are those ``case.write`` gives the same failures of the
same file (:mod:`hilclaw.case_tool`); :data:`KIND_VERDICTS_MISSING` is this
tool's own, since ``case.write`` takes a missing file as none. A number
beyond the float range in a top-level member no record defines is read as an
infinity, which no result can hold: the call then fails with ``bad_result``,
as ``hypotheses.read`` does. Nothing of the file is returned then.

The only file read is the round's ``verdicts.json``; no ``STATE.json`` is
read, so a round above the run's stored round is read like any other.
Nothing is created. The kinds are names of the tool layer and none is
reserved.
"""

import os
import stat

from hilclaw import (
    case_tool,
    data_root_source,
    keys,
    layout,
    run_files,
    tools,
    verdicts_file,
)

#: The round's ``eval/verdicts.json`` is not there; that says nothing more of the round.
KIND_VERDICTS_MISSING = "verdicts_missing"
#: The kinds of :mod:`hilclaw.case_tool` for the same file, with their meanings.
KIND_VERDICTS_INVALID = case_tool.KIND_VERDICTS_INVALID
KIND_VERDICTS_UNSUPPORTED = case_tool.KIND_VERDICTS_UNSUPPORTED
KIND_VERDICTS_UNREADABLE = case_tool.KIND_VERDICTS_UNREADABLE

NAME = "verdicts.read"

_DESCRIPTION = (
    "Read the verdicts of round round of the run run_id: the file "
    "rounds/<RRRR>/eval/verdicts.json, which holds for each hypothesis of "
    "that round its verdict (supported, refuted or inconclusive), its cause "
    'and its evidence. The result is {"record": the content of the file as '
    "one JSON object, its members as stored, unknown members included}. An "
    "earlier verdict is a hint, not a target. The data root is never part of "
    "the request; the tool knows it. round is at least 1: round 0 has no "
    "verdicts and is refused. Nothing is written. It fails, checked in this "
    "order, with invalid_request for a request that is not exactly run_id and "
    "round, or with round 0; no_data_root when the data root cannot be "
    "obtained; verdicts_missing when the file is not there, which says "
    "nothing more of the round; verdicts_invalid when it is invalid, no "
    "regular file, or names another run_id or round; verdicts_unsupported "
    "when it has another schema_version; verdicts_unreadable when it cannot "
    "be read; and bad_result when it holds a number too large to be returned."
)
_MEMBERS = ("run_id", "round")


def definition(source):
    """Return the tool definition of ``verdicts.read``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked at each call,
    after the request was checked, and not here. Raises :class:`TypeError`
    when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` and
    ``round``, whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses or
    whose ``round`` is no ``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`;
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does; and the
    four ``verdicts_*`` kinds of this module as the module docstring orders
    them. Each message of those starts with the file's path relative to the
    data root.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def read_verdicts(request):
        return _read(source, request)

    return tools.ToolDefinition(NAME, read_verdicts, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 1, "maximum": keys.MAX_INTEGER},
        },
        "required": list(_MEMBERS),
        "additionalProperties": False,
    }


def _invalid(message):
    return tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def _checked(request):
    others = sorted(name for name in request if name not in _MEMBERS)
    if others:
        raise _invalid(
            f"the request takes the members {', '.join(_MEMBERS)} only, "
            f"not {', '.join(map(repr, others))}"
        )
    for name in _MEMBERS:
        if name not in request:
            raise _invalid(f"the request lacks the member {name}")
    try:
        run_id = layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise _invalid(f"the request's {e}") from e
    round = request["round"]
    if type(round) is not int or not 1 <= round <= keys.MAX_INTEGER:
        raise _invalid(
            f"round: must be an int from 1 to {keys.MAX_INTEGER} "
            f"(round 0 has no verdicts), got {round!r}"
        )
    return run_id, round


def _read(source, request):
    run_id, round = _checked(request)
    data_root = data_root_source.obtain(source)
    path = layout.verdict_record(data_root, run_id, round)
    file = path.relative_to(data_root).as_posix()
    document = _parsed(data_root, path, file)
    for name, wanted in (("run_id", run_id), ("round", round)):
        if document[name] != wanted:
            raise tools.ToolFailure(
                KIND_VERDICTS_INVALID,
                f"{file}: {name}: must be the request's {name} {wanted!r}, "
                f"got {document[name]!r}",
            )
    return {"record": document}


def _parsed(data_root, path, file):
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise tools.ToolFailure(
                KIND_VERDICTS_INVALID, f"{file}: is not a regular file"
            )
        content = path.read_bytes()
    except run_files.NOT_THERE as e:
        found = "is missing"
        if not run_files.data_root_is_there(data_root):
            found += ": the data root is not an existing directory"
        raise tools.ToolFailure(KIND_VERDICTS_MISSING, f"{file}: {found}") from e
    except OSError as e:
        reported = ": ".join(filter(None, (type(e).__name__, e.strerror)))
        raise tools.ToolFailure(
            KIND_VERDICTS_UNREADABLE, f"{file}: could not be read: {reported}"
        ) from e
    try:
        return verdicts_file.parse(content)
    except verdicts_file.InvalidVerdictFileError as e:
        raise tools.ToolFailure(KIND_VERDICTS_INVALID, f"{file}: {e}") from e
    except verdicts_file.UnsupportedVersionError as e:
        raise tools.ToolFailure(KIND_VERDICTS_UNSUPPORTED, f"{file}: {e}") from e
