"""The tool ``hypotheses.read``, which reads a round's ``decision/hypotheses.json`` for the evaluator (ADR-0129 decision 3).

For the runs of ADR-0120 decision 1 the ``evaluator`` sub-agent gets the
hypothesis record of a round through this tool (ADR-0129 decisions 2 and 4).
It is a tool of the registry beside the FR-10 tools, not an FR-10 tool: it is
not journaled, appends no line to ``events.ndjson`` and selects no backend
(ADR-0129 decision 3).

The request is exactly ``{"run_id": ..., "round": ...}``: ``round`` is an
``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`, a ``bool`` being none.
The data root comes from the data-root source, asked at each call after the
request was checked, and never from the request (ADR-0015 decision 3). The
result is ``{"record": ...}``: the document :func:`hilclaw.hypotheses_file.parse`
returned for the file, members as stored, unknown top-level members included.

The checks, in this order, each with its kind (ADR-0129 decision 3, table):
the request, round 0 among its refusals (``invalid_request``); the data root
(``no_data_root``); the read of the round's file by :func:`read` (a place
holding no regular file ``hypotheses_invalid``, no file
``hypotheses_missing``, any other failing read ``hypotheses_unreadable``,
bytes :func:`hilclaw.hypotheses_file.parse` refuses ``hypotheses_invalid``,
another ``schema_version`` ``hypotheses_unsupported``); the document's
``run_id``, then its ``round``, against the request's
(``hypotheses_invalid``). :func:`read` is also the read of
``verdicts.write`` (:mod:`hilclaw.verdicts_tool`), so both tools name the
same failures of the same file alike.

A number beyond the float range in a top-level member no record defines is
read by :func:`hilclaw.hypotheses_file.parse` as an infinity, which no result
can hold: the call then fails with ``bad_result``, as ``state.read`` does
(:mod:`hilclaw.run_file_tools`). Nothing of the file is returned then.

The only file read is the round's ``hypotheses.json``; no ``STATE.json`` is
read, so a round above the run's stored round is read like any other.
Nothing is created and nothing is kept between calls. The kinds are names of
the tool layer and none is reserved.
"""

import os
import stat

from hilclaw import data_root_source, hypotheses_file, keys, layout, run_files, tools

#: The round's ``decision/hypotheses.json`` is not there.
KIND_HYPOTHESES_MISSING = "hypotheses_missing"
#: The round's ``decision/hypotheses.json`` is invalid, or its place holds no regular file.
KIND_HYPOTHESES_INVALID = "hypotheses_invalid"
#: The round's ``decision/hypotheses.json`` has another schema_version; nothing of it was interpreted.
KIND_HYPOTHESES_UNSUPPORTED = "hypotheses_unsupported"
#: The read of the round's ``decision/hypotheses.json`` failed for a reason other than its not being there.
KIND_HYPOTHESES_UNREADABLE = "hypotheses_unreadable"

NAME = "hypotheses.read"

_DESCRIPTION = (
    "Read the hypothesis record of round round of the run run_id: the file "
    "rounds/<RRRR>/decision/hypotheses.json, which names the round's "
    "hypotheses, the candidates that test each and the direction each "
    'expects. The result is {"record": the content of the file as one JSON '
    "object, its members as stored, unknown members included}. The data root "
    "is never part of the request; the tool knows it. round is at least 1: "
    "round 0 has no hypothesis record and is refused. It fails with "
    "invalid_request for a request that is not exactly run_id and round, or "
    "with round 0; no_data_root when the data root cannot be obtained; "
    "hypotheses_missing when the file is not there; hypotheses_invalid when it "
    "is invalid, no regular file, or names another run_id or round; "
    "hypotheses_unsupported when it has another schema_version; "
    "hypotheses_unreadable when it cannot be read; and bad_result when it "
    "holds a number too large to be returned."
)
_MEMBERS = ("run_id", "round")
_KINDS = {
    hypotheses_file.InvalidHypothesisFileError: KIND_HYPOTHESES_INVALID,
    hypotheses_file.UnsupportedVersionError: KIND_HYPOTHESES_UNSUPPORTED,
}


def definition(source):
    """Return the tool definition of ``hypotheses.read``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked at each call,
    after the request was checked, and not here. Raises :class:`TypeError`
    when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` and
    ``round``, whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses or
    whose ``round`` is no ``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`;
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does; the
    kinds of :func:`read`; and :data:`KIND_HYPOTHESES_INVALID` for a document
    whose ``run_id`` or ``round`` is not the request's.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def read_hypotheses(request):
        return _read(source, request)

    return tools.ToolDefinition(NAME, read_hypotheses, _DESCRIPTION, _input_schema())


def read(data_root, run_id, round):
    """Return the document of the round's ``decision/hypotheses.json`` below ``data_root``.

    ``data_root`` is a path; ``run_id`` and ``round`` are those
    :func:`hilclaw.layout.hypothesis_record` takes, which raises
    :class:`hilclaw.layout.InvalidPathValueError` for others. The file is
    read once and parsed by :func:`hilclaw.hypotheses_file.parse`; its
    ``run_id`` and ``round`` are not compared with the arguments.

    Raises :class:`hilclaw.tools.ToolFailure` of kind
    :data:`KIND_HYPOTHESES_INVALID` when the place holds no regular file,
    :data:`KIND_HYPOTHESES_MISSING` when nothing is there (the message says so
    when the data root is not an existing directory either),
    :data:`KIND_HYPOTHESES_UNREADABLE` for any other :class:`OSError`, and
    :data:`KIND_HYPOTHESES_INVALID` or :data:`KIND_HYPOTHESES_UNSUPPORTED`
    for the refusals of :func:`hilclaw.hypotheses_file.parse`. Each message
    starts with the file's path relative to ``data_root``.
    """
    path = layout.hypothesis_record(data_root, run_id, round)
    return _parsed(data_root, path, path.relative_to(data_root).as_posix())


def _parsed(data_root, path, file):
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise tools.ToolFailure(
                KIND_HYPOTHESES_INVALID, f"{file}: is not a regular file"
            )
        content = path.read_bytes()
    except run_files.NOT_THERE as e:
        found = "is missing"
        if not run_files.data_root_is_there(data_root):
            found += ": the data root is not an existing directory"
        raise tools.ToolFailure(KIND_HYPOTHESES_MISSING, f"{file}: {found}") from e
    except OSError as e:
        reported = ": ".join(filter(None, (type(e).__name__, e.strerror)))
        raise tools.ToolFailure(
            KIND_HYPOTHESES_UNREADABLE, f"{file}: could not be read: {reported}"
        ) from e
    try:
        return hypotheses_file.parse(content)
    except tuple(_KINDS) as e:
        kind = next(_KINDS[k] for k in _KINDS if isinstance(e, k))
        raise tools.ToolFailure(kind, f"{file}: {e}") from e


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
            f"(round 0 has no hypothesis record), got {round!r}"
        )
    return run_id, round


def _read(source, request):
    run_id, round = _checked(request)
    data_root = data_root_source.obtain(source)
    path = layout.hypothesis_record(data_root, run_id, round)
    file = path.relative_to(data_root).as_posix()
    document = _parsed(data_root, path, file)
    for name, wanted in (("run_id", run_id), ("round", round)):
        if document[name] != wanted:
            raise tools.ToolFailure(
                KIND_HYPOTHESES_INVALID,
                f"{file}: {name}: must be the request's {name} {wanted!r}, "
                f"got {document[name]!r}",
            )
    return {"record": document}
