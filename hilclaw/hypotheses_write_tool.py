"""The tool ``hypotheses.write``, which writes a round's ``decision/hypotheses.json`` for the technique-selector (ADR-0132 decision 4).

For the runs of ADR-0120 decision 1 the ``technique-selector`` sub-agent has
no file-writing means (ADR-0132 decision 3); it composes the hypothesis record
of a round of at least 1 and this tool writes it by
:func:`hilclaw.hypotheses_file.write`, so by the steps of ADR-0059 decision 1
unchanged. It is a tool of the registry beside the FR-10 tools, not an FR-10
tool: it is not journaled, appends no line to ``events.ndjson``, selects no
backend and takes no lock (ADR-0132 decision 4, as for ``verdicts.write``,
ADR-0128 decision 6).

The request is exactly ``{"run_id": ..., "record": ...}``: ``record`` is the
whole content of the file as one JSON object. The data root comes from the
data-root source, asked at each call after the record was checked, and never
from the request (ADR-0015 decision 3). The result is ``{}``.

``record`` is encoded into the bytes the write takes by the fixed rule of
:mod:`hilclaw.verdicts_tool`:
``json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)``, the
members in the order given, followed by one line feed, encoded in UTF-8
without a byte order mark. ``json.dumps`` escapes every control character of
a string, so the bytes hold no carriage return; a value it refuses (a number
that is not finite) and a string that UTF-8 cannot encode (a lone surrogate)
are refused with ``invalid_request``.

The checks, in this order, each with its kind (ADR-0132 decision 4, table);
the first that fails decides:

1. the request, then the bytes by :func:`hilclaw.hypotheses_file.parse`, a
   round-0 record and another ``schema_version`` among its refusals, then
   the record's ``run_id`` against the request's (``invalid_request``);
2. the data root (``no_data_root``);
3. the run's ``STATE.json`` read by :func:`hilclaw.run_file_tools.read` (the
   four ``run_file_*`` kinds), and its ``round`` equal to the record's
   (``round_not_current``, the kind of :mod:`hilclaw.case_tool`): the record
   is that of the round in progress, a precondition of the call held as
   ``case.write`` holds it (ADR-0133 decision 3);
4. only when the record's ``cases_read`` holds at least one entry, the rules
   between the record and the cases of its key, by the steps of
   :func:`hilclaw.hypotheses_cases.check_run` taken one by one: the run's
   ``instance.json`` read the same way (the four ``run_file_*`` kinds);
   :func:`hilclaw.case_lookup.find` for the records it states and the run
   id, any :class:`OSError` of it (:data:`KIND_CASES_UNREADABLE`);
   :func:`hilclaw.hypotheses_cases.check` (:data:`KIND_CASES_MISMATCH`). The
   reports of the lookup are not judged. A record with no ``cases_read``, or
   an empty one, holds no ``case`` entry (ADR-0073 decision 2), so nothing of
   the key is read for it;
5. the write by :func:`hilclaw.hypotheses_file.write`: a taken final name
   (:data:`KIND_HYPOTHESES_EXIST`; nothing replaced, the file under the name
   not read), any other :class:`OSError` (:data:`KIND_HYPOTHESES_NOT_WRITTEN`).

It admits exactly what those validators admit: an ``injected`` entry with its
``injection`` as :mod:`hilclaw.hypotheses` admits it. It holds no rule of
conduct of ADR-0112, no rule between files of ADR-0075 decision 3, no
``candidates`` against ``instance.json`` or the round's specs and no ``ref``
against the tree (ADR-0132 decision 4; ADR-0059 Boundaries).

Each message starts with the path of the file concerned relative to the data
root, where there is one; for a failing lookup it is the key directory, or
``instance.json`` for a run that states no op_signature. An :class:`OSError`
is reported by its class and the text of the system, without the absolute
path, and says so when the data root is gone.

Nothing is created before the write; a refused record can be corrected and
sent again. The only files read are ``STATE.json`` and, in check 4,
``instance.json`` and what :func:`hilclaw.case_lookup.find` reads. Nothing is
kept between calls. The kinds of this module are names of the tool layer and
none is reserved; no ``hypotheses_*`` kind of :mod:`hilclaw.hypotheses_tool`
is reused, and the four ``run_file_*`` kinds are the reserved ones of
ADR-0019, widened to these two reads by ADR-0132 decision 4.
"""

import json

from hilclaw import (
    case_lookup,
    case_tool,
    data_root_source,
    hypotheses_cases,
    hypotheses_file,
    layout,
    run_file_tools,
    run_files,
    tools,
)

#: The record's round is not the round ``STATE.json`` names as in progress, as in :mod:`hilclaw.case_tool`; nothing was written.
KIND_ROUND_NOT_CURRENT = case_tool.KIND_ROUND_NOT_CURRENT
#: The lookup of the cases of the run's key failed in the file system; nothing was written.
KIND_CASES_UNREADABLE = "cases_unreadable"
#: The record breaks a rule between it and the cases of the run's key (ADR-0073 decisions 2 and 3); nothing was written.
KIND_CASES_MISMATCH = "cases_mismatch"
#: The round's ``decision/hypotheses.json`` is already there; nothing was replaced.
KIND_HYPOTHESES_EXIST = "hypotheses_exist"
#: A step of the write failed in the file system; nothing was put under the final name.
KIND_HYPOTHESES_NOT_WRITTEN = "hypotheses_not_written"

NAME = "hypotheses.write"

_DESCRIPTION = (
    "Write the hypothesis record of the round in progress of the run run_id: "
    "record is the whole content of rounds/<RRRR>/decision/hypotheses.json as "
    "one JSON object (schema_version 1, run_id, round of at least 1, "
    "candidates, hypotheses, and cases_read when the record names cases). "
    "The file is written once and never replaced. The result is {}. The data "
    "root is never part of the request; the tool knows it. A refused record "
    "leaves nothing written and can be corrected and sent again. It fails, "
    "checked in this order, with invalid_request for a request that is not "
    "exactly run_id and record, or a record that is not valid, of round 0 or "
    "of another schema_version, or whose run_id is not run_id; no_data_root "
    "when the data root cannot be obtained; run_file_missing, "
    "run_file_invalid, run_file_unsupported or run_file_unreadable when the "
    "run's STATE.json is not there, is invalid or no regular file, has "
    "another schema_version or cannot be read; round_not_current when the "
    "record's round is not the round STATE.json names. Only for a record "
    "whose cases_read holds an entry: the same four run_file kinds for the "
    "run's instance.json; cases_unreadable when the cases of the run's key "
    "cannot be looked up; cases_mismatch when a cases_read entry names no "
    "stored case of the key or a case basis entry names a hypothesis id the "
    "named case does not hold. Then hypotheses_exist when the round's "
    "hypotheses.json is already there, and hypotheses_not_written when a "
    "step of the write fails."
)
_MEMBERS = ("run_id", "record")


def definition(source):
    """Return the tool definition of ``hypotheses.write``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request and the record were checked, and not here.
    Raises :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` and
    ``record``, whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses,
    whose ``record`` is no object, cannot be encoded, is refused by
    :func:`hilclaw.hypotheses_file.parse` or names another ``run_id``;
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does; the
    four ``run_file_*`` kinds as :func:`hilclaw.run_file_tools.read` raises
    them; and the kinds of this module, in the order of the module
    docstring.
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
        document = hypotheses_file.parse(content)
    except (
        hypotheses_file.InvalidHypothesisFileError,
        hypotheses_file.UnsupportedVersionError,
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
    round = document["round"]
    state, _ = run_file_tools.read(data_root, run_id, "STATE.json")
    if state.round != round:
        file = run_files.relative(run_id, "STATE.json")
        raise tools.ToolFailure(
            KIND_ROUND_NOT_CURRENT,
            f"{file}: names round {state.round} as in progress, not the "
            f"record's round {round}",
        )
    if document.get("cases_read"):
        _cases(data_root, run_id, document)
    path = layout.hypothesis_record(data_root, run_id, round)
    file = path.relative_to(data_root).as_posix()
    try:
        hypotheses_file.write(data_root, content)
    except hypotheses_file.NameTakenError as e:
        raise tools.ToolFailure(
            KIND_HYPOTHESES_EXIST,
            f"{file}: is already there; nothing was replaced",
        ) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_HYPOTHESES_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root)}",
        ) from e
    return {}


def _cases(data_root, run_id, document):
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    op_signature = stated.op_signature
    if op_signature is None:
        where = run_files.relative(run_id, "instance.json")
    else:
        key_dir = layout.op_signature_dir(
            data_root, stated.hw_profile_key, op_signature.key
        )
        where = key_dir.relative_to(data_root).as_posix()
    try:
        found = case_lookup.find(
            data_root,
            stated.hw_profile,
            op_signature.record if op_signature else None,
            run_id,
        )
    except OSError as e:
        raise tools.ToolFailure(
            KIND_CASES_UNREADABLE,
            f"{where}: the cases of the run's key could not be read: "
            f"{_reported(e, data_root)}",
        ) from e
    try:
        hypotheses_cases.check(document, found)
    except hypotheses_cases.MismatchError as e:
        raise tools.ToolFailure(KIND_CASES_MISMATCH, f"record: {e}") from e


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
