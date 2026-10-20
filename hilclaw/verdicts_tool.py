"""The tool ``verdicts.write``, which writes a round's ``eval/verdicts.json`` for the evaluator (ADR-0128 decision 6).

For the runs of ADR-0120 decision 1 the ``evaluator`` sub-agent has no
file-writing means (ADR-0128 decision 3); it composes the verdicts of a round
and this tool writes them by :func:`hilclaw.verdicts_file.write`, so by the
steps of ADR-0071 decision 1 unchanged. It is a tool of the registry beside
the FR-10 tools, not an FR-10 tool: it is not journaled, appends no line to
``events.ndjson`` and selects no backend (ADR-0128 decision 6, as for
``state.write``, ADR-0124 decision 3).

The request is exactly ``{"run_id": ..., "record": ...}``: ``record`` is the
whole content of the file as one JSON object. The data root comes from the
data-root source, asked at each call after the record was checked, and never
from the request (ADR-0015 decision 3). The result is ``{}``.

``record`` is encoded into the bytes the write takes by one fixed rule:
``json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)``, the
members in the order given, followed by one line feed, encoded in UTF-8
without a byte order mark. ``json.dumps`` escapes every control character of
a string, so the bytes hold no carriage return; a string that UTF-8 cannot
encode (a lone surrogate) is refused with ``invalid_request``.

The checks, in this order, each with its kind (ADR-0128 decision 6, table):
the request (``invalid_request``); the bytes by
:func:`hilclaw.verdicts_file.parse`, a round-0 record and another
``schema_version`` among its refusals, and the record's ``run_id`` against the
request's (``invalid_request``); the data root (``no_data_root``); the read of
the round's ``decision/hypotheses.json`` by
:func:`hilclaw.hypotheses_tool.read` (the four ``hypotheses_*`` kinds); the
rules of :func:`hilclaw.verdicts_hypotheses.check` (``verdicts_mismatch``);
no evidence entry of ``kind`` ``comparison`` (``comparison_not_given``, until
a tool gives a comparison); the write (``verdicts_exist`` for a taken name,
``verdicts_not_written`` for any other failure of the file system).

Nothing is created before the write; a refused record can be corrected and
sent again. The only file read is ``hypotheses.json``. Nothing is kept
between calls. The kinds are names of the tool layer and none is reserved.
"""

import json

from hilclaw import (
    data_root_source,
    hypotheses_tool,
    layout,
    run_files,
    tools,
    verdicts_file,
    verdicts_hypotheses,
)

#: The kinds of the read of the round's ``decision/hypotheses.json``, those of :mod:`hilclaw.hypotheses_tool`.
KIND_HYPOTHESES_MISSING = hypotheses_tool.KIND_HYPOTHESES_MISSING
KIND_HYPOTHESES_INVALID = hypotheses_tool.KIND_HYPOTHESES_INVALID
KIND_HYPOTHESES_UNSUPPORTED = hypotheses_tool.KIND_HYPOTHESES_UNSUPPORTED
KIND_HYPOTHESES_UNREADABLE = hypotheses_tool.KIND_HYPOTHESES_UNREADABLE
#: The record breaks a rule between it and the round's hypothesis record; nothing was written.
KIND_VERDICTS_MISMATCH = "verdicts_mismatch"
#: The record holds an evidence entry of kind comparison, which no tool gives yet; nothing was written.
KIND_COMPARISON_NOT_GIVEN = "comparison_not_given"
#: The round's ``eval/verdicts.json`` is already there; nothing was replaced.
KIND_VERDICTS_EXIST = "verdicts_exist"
#: A step of the write failed in the file system; nothing was put under the final name.
KIND_VERDICTS_NOT_WRITTEN = "verdicts_not_written"

NAME = "verdicts.write"

_DESCRIPTION = (
    "Write the verdicts of one round of the run run_id: record is the whole "
    "content of rounds/<RRRR>/eval/verdicts.json as one JSON object "
    "(schema_version 1, run_id, round of at least 1, one verdict per hypothesis "
    "of the round's decision/hypotheses.json). The file is written once and "
    "never replaced. The result is {}. The data root is never part of the "
    "request; the tool knows it. A refused record leaves nothing written and "
    "can be corrected and sent again. It fails with invalid_request for a "
    "record that is not valid, of round 0 or of another schema_version, or "
    "whose run_id is not run_id; no_data_root when the data root cannot be "
    "obtained; hypotheses_missing, hypotheses_invalid, "
    "hypotheses_unsupported or hypotheses_unreadable when the round's "
    "hypotheses.json is not there, is invalid or no regular file, has another "
    "schema_version or cannot be read; verdicts_mismatch when the record "
    "breaks a rule against it (a verdict for each hypothesis id and none for "
    "another, measured within tested_by, each verdict value by its rule); "
    "comparison_not_given for any evidence entry of kind comparison, which is "
    "refused for now: write check entries only; verdicts_exist when the "
    "round's verdicts.json is already there; and verdicts_not_written when "
    "a step of the write fails."
)
_MEMBERS = ("run_id", "record")


def definition(source):
    """Return the tool definition of ``verdicts.write``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked at each call,
    after the request and the record were checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` and
    ``record``, whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses,
    whose ``record`` is no object, cannot be encoded, is refused by
    :func:`hilclaw.verdicts_file.parse` or names another ``run_id``;
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does; and the
    kinds of this module, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def write(request):
        return _write(source, request)

    return tools.ToolDefinition(NAME, write, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "record": {"type": "object"},
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
    record = request["record"]
    if type(record) is not dict:
        raise _invalid(f"record: must be an object, got {type(record).__name__}")
    try:
        text = json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)
        content = (text + "\n").encode("utf-8")
    except (ValueError, RecursionError) as e:
        raise _invalid(f"record: cannot be encoded as UTF-8 JSON text: {e}") from e
    try:
        document = verdicts_file.parse(content)
    except (
        verdicts_file.InvalidVerdictFileError,
        verdicts_file.UnsupportedVersionError,
    ) as e:
        raise _invalid(f"record: {e}") from e
    if document["run_id"] != run_id:
        raise _invalid(
            f"record.run_id: must be the request's run_id {run_id!r}, "
            f"got {document['run_id']!r}"
        )
    return run_id, document, content


def _write(source, request):
    run_id, document, content = _checked(request)
    data_root = data_root_source.obtain(source)
    hypotheses = hypotheses_tool.read(data_root, run_id, document["round"])
    try:
        verdicts_hypotheses.check(document, hypotheses)
    except verdicts_hypotheses.MismatchError as e:
        raise tools.ToolFailure(KIND_VERDICTS_MISMATCH, f"record: {e}") from e
    for index, verdict in enumerate(document["verdicts"]):
        for at, entry in enumerate(verdict["evidence"]):
            if entry["kind"] == "comparison":
                raise tools.ToolFailure(
                    KIND_COMPARISON_NOT_GIVEN,
                    f"record.verdicts[{index}].evidence[{at}]: a comparison is "
                    "refused until a tool gives it; write check entries only",
                )
    path = layout.verdict_record(data_root, run_id, document["round"])
    file = path.relative_to(data_root).as_posix()
    try:
        verdicts_file.write(data_root, content)
    except verdicts_file.NameTakenError as e:
        raise tools.ToolFailure(
            KIND_VERDICTS_EXIST,
            f"{file}: is already there; nothing was replaced",
        ) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_VERDICTS_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root)}",
        ) from e
    return {}


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
