"""The tool ``case.write``, which stores the hypothesis-outcome case of a round for the Round-Manager (ADR-0133 decision 3).

For the runs of ADR-0120 decision 1 the Round-Manager holds the promotion
step of a round of at least 1 itself and writes the round's case (ADR-0072)
through this tool only, right before the write that ends the round (ADR-0133
decisions 2 and 5). It is a tool of the registry beside the FR-10 tools, not
an FR-10 tool: it is not journaled, appends no line to ``events.ndjson``,
selects no backend and keeps nothing between calls (ADR-0133 decision 3, as
ADR-0124 decision 3 reads ``state.write``).

The request is exactly ``{"run_id": ..., "round": ...}``: ``round`` is an
``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`, a ``bool`` being none.
The data root comes from the data-root source, asked at each call after the
request was checked, and never from the request (ADR-0015 decision 3). The
result is ``{"with_verdicts": bool}``: true exactly when the stored case holds
``verdict_record``.

The checks, in this order, each with its kind; the first that fails decides
and every check before the write creates nothing (ADR-0133 decision 3, table):

1. the request (``invalid_request``);
2. the data root (``no_data_root``);
3. the run's ``STATE.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``state.read`` answers
   them), and its ``round`` equal to the request's
   (:data:`KIND_ROUND_NOT_CURRENT`);
4. the run's ``instance.json`` read the same way (the same four kinds);
5. the key: an instance stating no ``op_signature``, or
   :func:`hilclaw.key_records.lookup` of its two records finding no record
   file (:data:`KIND_KEY_NOT_STORED`); a collision or an invalid stored record
   (:data:`KIND_KEY_RECORD_INVALID`); any :class:`OSError` of the lookup, a
   data root gone since 2 among them (:data:`KIND_KEY_RECORD_UNREADABLE`);
6. the round's ``decision/hypotheses.json`` by
   :func:`hilclaw.hypotheses_tool.read` (the four ``hypotheses_*`` kinds),
   then its ``run_id`` and its ``round`` against the request's
   (``hypotheses_invalid``, worded as ``hypotheses.read`` words it);
7. the round's ``eval/verdicts.json``: nothing there is no failure and gives
   a case without verdicts; a place holding no regular file, bytes
   :func:`hilclaw.verdicts_file.parse` refuses or a ``run_id`` or ``round``
   other than the request's (:data:`KIND_VERDICTS_INVALID`); another
   ``schema_version`` (:data:`KIND_VERDICTS_UNSUPPORTED`); any other failing
   read (:data:`KIND_VERDICTS_UNREADABLE`);
8. with verdicts, :func:`hilclaw.verdicts_hypotheses.check` of the pair
   (``verdicts_mismatch``); then :func:`hilclaw.cases.build`;
9. the write by :func:`hilclaw.cases_file.write` into the key directory of 5:
   a taken name (:data:`KIND_CASE_EXISTS`, nothing replaced), any
   :class:`OSError`, a key directory gone since 5 among them
   (:data:`KIND_CASE_NOT_WRITTEN`).

Each message starts with the path of the file concerned relative to the data
root, where there is one; for a refusal of the key it is the key directory.
An :class:`OSError` is reported by its class and the text of the system,
without the absolute path, and says so when the data root is gone, or for
the write when the key directory is.

The case is encoded into the bytes the write takes by one fixed rule, that of
``verdicts.write``: ``json.dumps(case, ensure_ascii=False, indent=2,
allow_nan=False)``, the members in the order :func:`hilclaw.cases.build`
gives, followed by one line feed, encoded in UTF-8 without a byte order mark.
A hypothesis or verdicts file whose top-level member that no record defines
holds a number beyond the float range (read as an infinity) or a lone
surrogate cannot be so encoded; no record decides that case, so the
:class:`ValueError` passes out of the tool function and
:func:`hilclaw.tools.call` answers it with ``tool_crashed``, nothing being
written. So are an :class:`hilclaw.cases.InvalidCaseError` of the build and a
refusal of :func:`hilclaw.cases_file.write` other than those of 9, which a
successful build does not leave room for.

The only files read are ``STATE.json``, ``instance.json``, the two key record
files, ``hypotheses.json`` and ``verdicts.json``; the only file written is the
case, through :func:`hilclaw.cases_file.write`, and no directory is created.
The kinds of this module are names of the tool layer and none is reserved; the
four ``run_file_*`` kinds are the reserved ones of ADR-0019, widened to these
two reads by ADR-0133 decision 3.
"""

import json
import os
import stat

from hilclaw import (
    cases,
    cases_file,
    data_root_source,
    hypotheses_tool,
    key_records,
    keys,
    layout,
    run_file_tools,
    run_files,
    tools,
    verdicts_file,
    verdicts_hypotheses,
    verdicts_tool,
)

#: The request's round is not the round ``STATE.json`` names as in progress; nothing was written.
KIND_ROUND_NOT_CURRENT = "round_not_current"
#: ``instance.json`` states no op_signature, or a record file of its key is not stored; nothing was created.
KIND_KEY_NOT_STORED = "key_not_stored"
#: A stored key record file is invalid or collides with the instance's record; nothing was written.
KIND_KEY_RECORD_INVALID = "key_record_invalid"
#: The read of a key record file failed in the file system; nothing was written.
KIND_KEY_RECORD_UNREADABLE = "key_record_unreadable"
#: The kinds of the read of the round's ``decision/hypotheses.json``, those of :mod:`hilclaw.hypotheses_tool`.
KIND_HYPOTHESES_MISSING = hypotheses_tool.KIND_HYPOTHESES_MISSING
KIND_HYPOTHESES_INVALID = hypotheses_tool.KIND_HYPOTHESES_INVALID
KIND_HYPOTHESES_UNSUPPORTED = hypotheses_tool.KIND_HYPOTHESES_UNSUPPORTED
KIND_HYPOTHESES_UNREADABLE = hypotheses_tool.KIND_HYPOTHESES_UNREADABLE
#: The round's ``eval/verdicts.json`` is invalid, names another run or round, or its place holds no regular file.
KIND_VERDICTS_INVALID = "verdicts_invalid"
#: The round's ``eval/verdicts.json`` has another schema_version; nothing of it was interpreted.
KIND_VERDICTS_UNSUPPORTED = "verdicts_unsupported"
#: The read of the round's ``eval/verdicts.json`` failed for a reason other than its not being there.
KIND_VERDICTS_UNREADABLE = "verdicts_unreadable"
#: The round's verdicts break a rule between them and its hypothesis record, as in :mod:`hilclaw.verdicts_tool`.
KIND_VERDICTS_MISMATCH = verdicts_tool.KIND_VERDICTS_MISMATCH
#: The round's case is already stored; nothing was replaced.
KIND_CASE_EXISTS = "case_exists"
#: A step of the write failed in the file system; nothing was put under the final name.
KIND_CASE_NOT_WRITTEN = "case_not_written"

NAME = "case.write"

_DESCRIPTION = (
    "Store the hypothesis-outcome case of round round of the run run_id, the "
    "round in progress, in the knowledge tree: a copy of the round's "
    "decision/hypotheses.json and, when it is there, of its eval/verdicts.json, "
    "written once below the key of the run's instance.json and never replaced. "
    "Call it once per round of at least 1, right before the write that ends "
    'the round. The result is {"with_verdicts": true or false}: whether the '
    "stored case holds the round's verdicts; a round without verdicts.json is "
    "stored without them. The data root is never part of the request; the "
    "tool knows it. Nothing is written when it fails. It fails, checked in "
    "this order, with invalid_request for a request that is not exactly "
    "run_id and round, or with round 0; no_data_root when the data root "
    "cannot be obtained; run_file_missing, run_file_invalid, "
    "run_file_unsupported or run_file_unreadable when the run's STATE.json is "
    "not there, is invalid or no regular file, has another schema_version or "
    "cannot be read; round_not_current when round is not the round STATE.json "
    "names; the same four run_file kinds for the run's instance.json; "
    "key_not_stored when instance.json states no op_signature or the key's "
    "hw_profile.json or op_signature.json is not stored; key_record_invalid "
    "when a stored key record is invalid or collides; key_record_unreadable "
    "when a key record cannot be read; hypotheses_missing, "
    "hypotheses_invalid, hypotheses_unsupported or hypotheses_unreadable when "
    "the round's hypotheses.json is not there, is invalid or no regular file "
    "or names another run_id or round, has another schema_version or cannot "
    "be read; verdicts_invalid when the round's verdicts.json is invalid, no "
    "regular file or names another run_id or round; verdicts_unsupported when "
    "it has another schema_version; verdicts_unreadable when it cannot be "
    "read; verdicts_mismatch when it breaks a rule against hypotheses.json; "
    "case_exists when the round's case is already stored; and "
    "case_not_written when a step of the write fails."
)
_MEMBERS = ("run_id", "round")


def definition(source):
    """Return the tool definition of ``case.write``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` and
    ``round``, whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses or
    whose ``round`` is no ``int`` from 1 to :data:`hilclaw.keys.MAX_INTEGER`;
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does; the four
    ``run_file_*`` kinds as :func:`hilclaw.run_file_tools.read` raises them;
    the kinds of :func:`hilclaw.hypotheses_tool.read`; and the kinds of this
    module, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def write_case(request):
        return _write(source, request)

    return tools.ToolDefinition(NAME, write_case, _DESCRIPTION, _input_schema())


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
            f"(round 0 has no case), got {round!r}"
        )
    return run_id, round


def _write(source, request):
    run_id, round = _checked(request)
    data_root = data_root_source.obtain(source)
    state, _ = run_file_tools.read(data_root, run_id, "STATE.json")
    if state.round != round:
        file = run_files.relative(run_id, "STATE.json")
        raise tools.ToolFailure(
            KIND_ROUND_NOT_CURRENT,
            f"{file}: names round {state.round} as in progress, not the "
            f"request's round {round}",
        )
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    hw, op = _key(data_root, run_id, stated)
    hypotheses = hypotheses_tool.read(data_root, run_id, round)
    path = layout.hypothesis_record(data_root, run_id, round)
    _same(
        KIND_HYPOTHESES_INVALID, _relative(path, data_root), hypotheses, run_id, round
    )
    verdicts = _verdicts(data_root, run_id, round)
    if verdicts is not None:
        try:
            verdicts_hypotheses.check(verdicts, hypotheses)
        except verdicts_hypotheses.MismatchError as e:
            file = _relative(layout.verdict_record(data_root, run_id, round), data_root)
            raise tools.ToolFailure(KIND_VERDICTS_MISMATCH, f"{file}: {e}") from e
    case = cases.build(hypotheses, verdicts)
    text = json.dumps(case, ensure_ascii=False, indent=2, allow_nan=False)
    content = (text + "\n").encode("utf-8")
    path = layout.case_record(data_root, hw.name, op.name, run_id, round)
    file = _relative(path, data_root)
    try:
        cases_file.write(data_root, hw.name, op.name, content)
    except cases_file.NameTakenError as e:
        raise tools.ToolFailure(
            KIND_CASE_EXISTS, f"{file}: is already there; nothing was replaced"
        ) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_CASE_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root, path.parent)}",
        ) from e
    return {"with_verdicts": verdicts is not None}


def _key(data_root, run_id, stated):
    if stated.op_signature is None:
        file = run_files.relative(run_id, "instance.json")
        raise tools.ToolFailure(
            KIND_KEY_NOT_STORED,
            f"{file}: states no op_signature, so the run has no key to store "
            "a case below",
        )
    key_dir = layout.op_signature_dir(
        data_root, stated.hw_profile_key, stated.op_signature.key
    )
    where = _relative(key_dir, data_root)
    try:
        found = key_records.lookup(
            data_root, stated.hw_profile, stated.op_signature.record
        )
    except (key_records.KeyCollisionError, key_records.CorruptKeyRecordError) as e:
        raise tools.ToolFailure(KIND_KEY_RECORD_INVALID, str(e)) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_KEY_RECORD_UNREADABLE,
            f"{where}: the key records could not be read: {_reported(e, data_root)}",
        ) from e
    if found is None:
        raise tools.ToolFailure(
            KIND_KEY_NOT_STORED,
            f"{where}: the key is not stored: hw_profile.json or "
            "op_signature.json is missing",
        )
    return found


def _verdicts(data_root, run_id, round):
    path = layout.verdict_record(data_root, run_id, round)
    file = _relative(path, data_root)
    try:
        mode = os.lstat(path).st_mode
    except run_files.NOT_THERE:
        return None
    except OSError as e:
        raise _unreadable(file, e) from e
    if not stat.S_ISREG(mode):
        raise tools.ToolFailure(KIND_VERDICTS_INVALID, f"{file}: is not a regular file")
    try:
        content = path.read_bytes()
    except OSError as e:
        raise _unreadable(file, e) from e
    try:
        document = verdicts_file.parse(content)
    except verdicts_file.InvalidVerdictFileError as e:
        raise tools.ToolFailure(KIND_VERDICTS_INVALID, f"{file}: {e}") from e
    except verdicts_file.UnsupportedVersionError as e:
        raise tools.ToolFailure(KIND_VERDICTS_UNSUPPORTED, f"{file}: {e}") from e
    _same(KIND_VERDICTS_INVALID, file, document, run_id, round)
    return document


def _same(kind, file, document, run_id, round):
    for name, wanted in (("run_id", run_id), ("round", round)):
        if document[name] != wanted:
            raise tools.ToolFailure(
                kind,
                f"{file}: {name}: must be the request's {name} {wanted!r}, "
                f"got {document[name]!r}",
            )


def _unreadable(file, error):
    return tools.ToolFailure(
        KIND_VERDICTS_UNREADABLE, f"{file}: could not be read: {_system(error)}"
    )


def _relative(path, data_root):
    return path.relative_to(data_root).as_posix()


def _system(error):
    return ": ".join(filter(None, (type(error).__name__, error.strerror)))


def _reported(error, data_root, key_dir=None):
    reported = _system(error)
    if isinstance(error, run_files.NOT_THERE):
        if not run_files.data_root_is_there(data_root):
            reported += ": the data root is not an existing directory"
        elif key_dir is not None and not key_dir.is_dir():
            reported += ": the key directory is not an existing directory"
    return reported
