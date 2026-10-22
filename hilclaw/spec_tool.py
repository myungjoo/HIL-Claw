"""The tool ``spec.write``, which composes and writes the spec of the first coder call of a round of a first-case run (ADR-0138 decision 3, ADR-0151 decision 3).

For the runs of ADR-0120 decision 1 whose ``instance.json`` states
``candidates_per_round`` 1, the ``coder-driver`` has the spec of the first
coder call of a round (``candidate`` 1, ``attempt`` 1) written through this
tool before it requests that call: the bring-up call of round 0 (ADR-0138
decisions 1 and 3) and the first call of a round >= 1 (ADR-0151 decisions 1
and 3). It is a tool of the registry beside the FR-10 tools, not an FR-10
tool: it is not journaled, appends no line to ``events.ndjson``, selects no
backend and keeps nothing between calls.

The request is ``{"run_id": ..., "round": ..., "candidate": 1, "attempt":
1}`` and, exactly when ``round`` >= 1, ``"techniques"``: an array of
*names* of ADR-0001 decision 1, none twice, possibly empty, with no length
bound. The numbers are in the form of ADR-0015 decision 4: ``int`` values, a
``bool`` being none, ``round`` from 0 to :data:`hilclaw.keys.MAX_INTEGER`.
The data root comes from the data-root source, asked at each call after the
request was checked, and never from the request (ADR-0015 decision 3). The
result is the empty object ``{}``. ``id.round`` is not held against
``STATE.json`` (ADR-0151 decision 3).

The checks, in this order, each with its kind; the first that fails decides
and nothing is created before 12 (ADR-0151 decision 3, table):

1. the request (``invalid_request``): a member other than those above, one
   missing, a value outside its form, ``candidate`` or ``attempt`` other
   than 1, ``techniques`` with ``round`` 0 or absent with ``round`` >= 1, or
   an element of it that is no *name* or occurs twice;
2. the data root (``no_data_root``);
3. the run's ``instance.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``instance.read`` answers
   them);
4. ``candidates_per_round`` stated (:data:`KIND_CANDIDATES_PER_ROUND_NOT_STATED`)
   and equal to 1 (:data:`KIND_CANDIDATES_PER_ROUND_NOT_COVERED`);
5. ``op_signature`` stated (:data:`KIND_OP_SIGNATURE_NOT_STATED`) and covered
   by :func:`hilclaw.gemm_contract.covers` (:data:`KIND_OP_SIGNATURE_NOT_COVERED`);
6. ``objective`` stated (:data:`KIND_OBJECTIVE_NOT_STATED`);
7. for ``round`` >= 1 and a non-empty ``techniques`` only, each id in the
   request's order looked up by :func:`hilclaw.catalog.technique` in the
   directory of the instance's ``hw_profile`` ``accelerator`` below
   :data:`hilclaw.catalog.SOURCE`: a directory that is missing, is refused
   by the catalog's rules or cannot be read (:data:`KIND_CATALOG_UNUSABLE`),
   an id that names no entry (:data:`KIND_TECHNIQUE_UNKNOWN`), and an entry
   whose :data:`hilclaw.catalog.APPLIES_TO` values differ from the composed
   spec's ``task.op_signature.record`` ``kind``, ``dtype`` and ``layout`` or
   its ``task.contract.language`` (:data:`KIND_TECHNIQUE_NOT_APPLICABLE`,
   which no valid ``instance.json`` makes refuse today); the first id that
   fails decides;
8. to 10. for ``round`` >= 1, :func:`hilclaw.spec_feedback.attempts`, whose
   kinds pass out unchanged: :data:`KIND_FEEDBACK_UNREADABLE`, the four
   ``run_file_*`` kinds for the run's ``events.ndjson`` and
   ``check_result_invalid``;
11. the composed document encoded into the written form of ADR-0029 decision
    2, accepted by :func:`hilclaw.spec_file.parse` and given its final name
    by :func:`hilclaw.spec_file.final_name` (:data:`KIND_SPEC_INVALID`, a
    document that cannot be so encoded among them); no valid
    ``instance.json`` makes this check refuse today;
12. the write by :func:`hilclaw.spec_file.write`: a taken final name
    (:data:`KIND_SPEC_EXISTS`; nothing is written, and the file under the name
    is not read or compared), any :class:`OSError`, a data root gone since 2
    among them (:data:`KIND_SPEC_NOT_WRITTEN`).

The document of round 0 holds ``schema_version`` 2; ``id`` with the
request's ``run_id``, ``round`` 0, ``candidate`` 1, ``attempt`` 1,
``candidates`` 1 and ``relation`` ``single``, and no ``variant``;
``hw_profile`` with the ``key`` and ``record`` of the instance's member
``hw_profile``; ``task`` with ``op_signature``, the ``key`` and the whole
``record`` of the instance's member, ``contract``,
:func:`hilclaw.gemm_contract.task_contract` of that record's shape, and
``objective``, the instance's member; ``guidance`` with an empty
``techniques``; and ``feedback`` with an empty ``attempts`` (ADR-0138
decision 2). The document of a round ``r`` >= 1 is that document with
``id.round`` ``r``, ``guidance.techniques`` the ``{id, text}`` entries of 7
in the request's order, and ``feedback.attempts`` the list of 8 to 10
(ADR-0151 decision 2). No document has ``task.build``, ``feedback.base``,
``profile``, ``repair`` or ``ext``. The document is encoded by the rule of
``verdicts.write``: ``json.dumps(document, ensure_ascii=False, indent=2,
allow_nan=False)`` followed by one line feed, in UTF-8 without a byte order
mark.

Each message starts with the path of the file concerned relative to the data
root, or, for 7, the catalog directory as ``catalog/<accelerator>``. An
:class:`OSError` is reported by its class and the text of the system,
without the absolute path, and says so when the data root is gone. What
:func:`hilclaw.gemm_contract.covers` or a refusal of
:func:`hilclaw.spec_file.write` other than those of 12 raises, which a valid
``instance.json`` and check 11 do not leave room for, is mapped to no kind: it
passes out of the tool function and :func:`hilclaw.tools.call` answers it with
``tool_crashed``.

The files read are ``instance.json``, for a non-empty ``techniques`` the
catalog directory, and for ``round`` >= 1 what
:func:`hilclaw.spec_feedback.attempts` reads (the earlier attempts'
directories and specs, ``events.ndjson`` and the compiler logs).
``STATE.json``, ``decision/hypotheses.json``, ``decision.md`` and the stored
key records below ``db/`` are not. The only file written is the spec, through
:func:`hilclaw.spec_file.write`. The new kinds are names of the tool layer and
none is reserved; the four ``run_file_*`` kinds are the reserved ones of
ADR-0019, widened to these reads by ADR-0138 decision 3 and ADR-0151
decision 3.
"""

import json
import re

from hilclaw import (
    catalog,
    coder_call,
    data_root_source,
    gemm_contract,
    keys,
    layout,
    run_admission,
    run_file_tools,
    run_files,
    run_objective,
    spec_feedback,
    spec_file,
    tools,
)

#: ``instance.json`` states no candidates_per_round; nothing was written.
KIND_CANDIDATES_PER_ROUND_NOT_STATED = "candidates_per_round_not_stated"
#: ``instance.json`` states a candidates_per_round other than 1; nothing was written.
KIND_CANDIDATES_PER_ROUND_NOT_COVERED = "candidates_per_round_not_covered"
#: ``instance.json`` states no op_signature; nothing was written (ADR-0041 decision 4).
KIND_OP_SIGNATURE_NOT_STATED = run_admission.KIND_OP_SIGNATURE_NOT_STATED
#: The stated op_signature is not covered by the contract of ADR-0041 decision 5; nothing was written.
KIND_OP_SIGNATURE_NOT_COVERED = run_admission.KIND_OP_SIGNATURE_NOT_COVERED
#: ``instance.json`` states no objective; nothing was written (ADR-0061 decision 4).
KIND_OBJECTIVE_NOT_STATED = run_objective.KIND_OBJECTIVE_NOT_STATED
#: The accelerator's catalog directory is missing, refused or unreadable; nothing was written (ADR-0151 decision 2 (b)).
KIND_CATALOG_UNUSABLE = "catalog_unusable"
#: A requested id names no entry of the accelerator's catalog; nothing was written (ADR-0151 decision 2 (b)).
KIND_TECHNIQUE_UNKNOWN = "technique_unknown"
#: A requested entry applies to another kind, dtype, layout or language than the spec's; nothing was written (ADR-0151 decision 2 (b)).
KIND_TECHNIQUE_NOT_APPLICABLE = "technique_not_applicable"
#: An earlier attempt's spec, a listing or a compiler log cannot be used; re-exported from :mod:`hilclaw.spec_feedback`.
KIND_FEEDBACK_UNREADABLE = spec_feedback.KIND_FEEDBACK_UNREADABLE
#: The composed content is refused as a spec or has no final name; nothing was written (ADR-0126 decision 3).
KIND_SPEC_INVALID = coder_call.KIND_SPEC_INVALID
#: The spec's final name is taken; nothing was written, read or compared.
KIND_SPEC_EXISTS = "spec_exists"
#: A step of the write failed in the file system; nothing was put under the final name.
KIND_SPEC_NOT_WRITTEN = "spec_not_written"

NAME = "spec.write"

_DESCRIPTION = (
    "Compose and write the spec of the first coder call of a round of the run "
    "run_id, the call with candidate 1 and attempt 1, from the run's "
    "instance.json: its hw_profile, its op_signature with the contract that "
    "covers it, and its objective. For round 0, the bring-up call, the spec "
    "has no technique and no feedback. For a round of 1 or more, the spec "
    "also carries the catalog entry of each technique id you name in "
    "techniques, in your order, and every earlier attempt of the run whose "
    "check at the sim point is settled, with its technique ids and its "
    "failure. The spec is written once to "
    "runs/<run_id>/rounds/<RRRR>/coder/candidates/01/attempts/01/spec.json "
    "and never replaced. Call it before you request that coder call; request "
    "no call when it fails with a kind other than spec_exists, and report the "
    "kind in every case. The request is run_id, round, candidate 1 and "
    "attempt 1, and, exactly when round is 1 or more, techniques: an array "
    "of technique ids, each a name, none twice, possibly empty. The result "
    "is {}. The data root is never part of the request; the tool knows it. "
    "Nothing is written when it fails. It fails, checked in this order, with "
    "invalid_request for a request with another member, a member missing, "
    "a value outside its form, a candidate or attempt other than 1, "
    "techniques with round 0 or without it for a round of 1 or more, or an "
    "id that is no name or is given twice; no_data_root when the data root "
    "cannot be obtained; run_file_missing, run_file_invalid, "
    "run_file_unsupported or run_file_unreadable when the run's "
    "instance.json is not there, is invalid or no regular file, has another "
    "schema_version or cannot be read; candidates_per_round_not_stated when "
    "instance.json states no candidates_per_round; "
    "candidates_per_round_not_covered when it states one other than 1; "
    "op_signature_not_stated when it states no op_signature; "
    "op_signature_not_covered when the op_signature is not covered by the "
    "contract of the run tools; objective_not_stated when it states no "
    "objective; for a round of 1 or more with ids only, catalog_unusable "
    "when the catalog of the run's accelerator is missing, invalid or cannot "
    "be read, technique_unknown when an id names no entry of it, and "
    "technique_not_applicable when an entry applies to another task than "
    "the spec's; for a round of 1 or more, feedback_unreadable when an "
    "earlier attempt's spec, a listing or a compiler log cannot be used, "
    "run_file_missing, run_file_invalid, run_file_unsupported or "
    "run_file_unreadable for the run's events.ndjson, and "
    "check_result_invalid when a check result of an earlier attempt has no "
    "admitted outcome; spec_invalid when the composed spec is refused; "
    "spec_exists when the spec is already there, which is not read or "
    "compared; and spec_not_written when a step of the write fails."
)
_MEMBERS = ("run_id", "round", "candidate", "attempt")
_TECHNIQUES = "techniques"
_TUPLE = {"round": 0, "candidate": 1, "attempt": 1}
_NAME = re.compile(r"[a-z][a-z0-9_]{0,31}")


def definition(source):
    """Return the tool definition of ``spec.write``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not ``run_id``, ``round``,
    ``candidate`` and ``attempt`` with, exactly when ``round`` >= 1,
    ``techniques``; whose ``run_id`` :func:`hilclaw.layout.check_run_id`
    refuses; whose numbers are not ``int`` values in the form of ADR-0015
    decision 4, ``round`` from 0 to :data:`hilclaw.keys.MAX_INTEGER` and
    ``candidate`` and ``attempt`` 1; or whose ``techniques`` is no ``list``
    of distinct *names*; ``no_data_root`` as
    :func:`hilclaw.data_root_source.obtain` does; the four ``run_file_*``
    kinds as :func:`hilclaw.run_file_tools.read` raises them; what
    :func:`hilclaw.spec_feedback.attempts` raises; and the kinds of this
    module, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def write_spec(request):
        return _write(source, request)

    return tools.ToolDefinition(NAME, write_spec, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 0, "maximum": keys.MAX_INTEGER},
            "candidate": {"type": "integer", "minimum": 1, "maximum": 1},
            "attempt": {"type": "integer", "minimum": 1, "maximum": 1},
            _TECHNIQUES: {"type": "array"},
        },
        "required": list(_MEMBERS),
        "additionalProperties": False,
    }


def _invalid(message):
    return tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def _checked(request):
    value = request.get("round")
    later = type(value) is int and value >= 1
    taken = (*_MEMBERS, _TECHNIQUES) if later else _MEMBERS
    others = sorted(name for name in request if name not in (*_MEMBERS, _TECHNIQUES))
    if others:
        raise _invalid(
            f"the request takes the members {', '.join(taken)} only, "
            f"not {', '.join(map(repr, others))}"
        )
    for name in _MEMBERS:
        if name not in request:
            raise _invalid(f"the request lacks the member {name}")
    try:
        run_id = layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise _invalid(f"the request's {e}") from e
    for name in _MEMBERS[1:]:
        value = request[name]
        if type(value) is not int:
            raise _invalid(f"{name}: must be an int, got {type(value).__name__}")
        if name == "round" and not 0 <= value <= keys.MAX_INTEGER:
            raise _invalid(f"round: must be from 0 to {keys.MAX_INTEGER}, got {value}")
        if name != "round" and value != 1:
            raise _invalid(
                f"{name}: must be 1: this tool writes only the spec of "
                f"candidate 1, attempt 1 of a round, got {value}"
            )
    if not later:
        if _TECHNIQUES in request:
            raise _invalid("techniques: is taken only with a round of 1 or more")
        return run_id, 0, []
    if _TECHNIQUES not in request:
        raise _invalid(
            "the request lacks the member techniques, which a round of 1 or "
            "more requires"
        )
    return run_id, request["round"], _ids(request[_TECHNIQUES])


def _ids(value):
    if type(value) is not list:
        raise _invalid(f"techniques: must be an array, got {type(value).__name__}")
    seen = set()
    for index, entry_id in enumerate(value):
        if type(entry_id) is not str:
            raise _invalid(
                f"techniques[{index}]: must be a str, got {type(entry_id).__name__}"
            )
        if not _NAME.fullmatch(entry_id):
            raise _invalid(
                f"techniques[{index}]: must be a name matching {_NAME.pattern}"
            )
        if entry_id in seen:
            raise _invalid(f"techniques[{index}]: {entry_id!r} is given twice")
        seen.add(entry_id)
    return value


def _write(source, request):
    run_id, round, ids = _checked(request)
    data_root = data_root_source.obtain(source)
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    _admitted(run_id, stated)
    document = _compose(run_id, stated)
    if round:
        document["id"]["round"] = round
        document["guidance"]["techniques"] = _techniques(stated, document, ids)
        document["feedback"]["attempts"] = spec_feedback.attempts(
            data_root, run_id, round
        )
    content, path = _content(data_root, run_id, round, document)
    file = _relative(path, data_root)
    try:
        spec_file.write(data_root, content)
    except spec_file.NameTakenError as e:
        raise tools.ToolFailure(
            KIND_SPEC_EXISTS,
            f"{file}: is already there; nothing was written, read or compared",
        ) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_SPEC_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root)}",
        ) from e
    return {}


def _admitted(run_id, stated):
    file = run_files.relative(run_id, "instance.json")
    count = stated.candidates_per_round
    if count is None:
        raise tools.ToolFailure(
            KIND_CANDIDATES_PER_ROUND_NOT_STATED,
            f"{file}: states no candidates_per_round; nothing was written",
        )
    if count != 1:
        raise tools.ToolFailure(
            KIND_CANDIDATES_PER_ROUND_NOT_COVERED,
            f"{file}: states candidates_per_round {count}; only a run with 1 "
            "gets its spec from this tool; nothing was written",
        )
    if stated.op_signature is None:
        raise tools.ToolFailure(
            KIND_OP_SIGNATURE_NOT_STATED,
            f"{file}: states no op_signature; nothing was written",
        )
    if not gemm_contract.covers(stated.op_signature.record):
        raise tools.ToolFailure(
            KIND_OP_SIGNATURE_NOT_COVERED,
            f"{file}: op_signature: the stated record is not covered by the "
            "contract of the run tools; nothing was written",
        )
    if stated.objective is None:
        raise tools.ToolFailure(
            KIND_OBJECTIVE_NOT_STATED,
            f"{file}: states no objective; nothing was written",
        )


def _compose(run_id, stated):
    record = stated.op_signature.record
    shape = record["shape"]
    return {
        "schema_version": 2,
        "id": {
            "run_id": run_id,
            **_TUPLE,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": {"key": stated.hw_profile_key, "record": stated.hw_profile},
        "task": {
            "op_signature": {"key": stated.op_signature.key, "record": record},
            "contract": gemm_contract.task_contract(shape["m"], shape["k"], shape["n"]),
            "objective": stated.objective,
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }


def _techniques(stated, document, ids):
    if not ids:
        return []
    accelerator = stated.hw_profile["accelerator"]
    directory = f"catalog/{accelerator}"
    record = document["task"]["op_signature"]["record"]
    composed = {name: record[name] for name in ("kind", "dtype", "layout")}
    composed["language"] = document["task"]["contract"]["language"]
    applies = [line.removeprefix("- ").split(": ", 1) for line in catalog.APPLIES_TO]
    entries = []
    for entry_id in ids:
        try:
            entry = catalog.technique(accelerator, entry_id)
        except KeyError as e:
            raise tools.ToolFailure(
                KIND_TECHNIQUE_UNKNOWN,
                f"{directory}: holds no entry {entry_id}: the accelerator "
                f"{accelerator} has no such technique; nothing was written",
            ) from e
        except FileNotFoundError as e:
            raise _unusable(directory, "is not there") from e
        except catalog.InvalidCatalogError as e:
            raise _unusable(directory, f"is refused: {e}") from e
        except OSError as e:
            raise _unusable(directory, f"cannot be read: {_described(e)}") from e
        for name, value in applies:
            if composed[name] != value:
                raise tools.ToolFailure(
                    KIND_TECHNIQUE_NOT_APPLICABLE,
                    f"{directory}/{entry_id}.md: applies to the {name} {value}, "
                    f"not the spec's {composed[name]}; nothing was written",
                )
        entries.append(entry)
    return entries


def _unusable(directory, problem):
    return tools.ToolFailure(
        KIND_CATALOG_UNUSABLE,
        f"{directory}: the catalog directory {problem}; nothing was written",
    )


def _content(data_root, run_id, round, document):
    place = layout.attempt_artefact(data_root, run_id, round, 1, 1, "spec.json")
    file = _relative(place, data_root)
    try:
        content = _encoded(document)
        if not content.endswith(b"\n") or b"\r" in content:
            raise ValueError("it is not in the written form of ADR-0029 decision 2")
        path = spec_file.final_name(data_root, spec_file.parse(content))
    except (ValueError, spec_file.UnsupportedVersionError) as e:
        raise tools.ToolFailure(
            KIND_SPEC_INVALID,
            f"{file}: the composed spec is refused, nothing was written: {e}",
        ) from e
    return content, path


def _encoded(document):
    text = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    return (text + "\n").encode("utf-8")


def _relative(path, data_root):
    return path.relative_to(data_root).as_posix()


def _described(error):
    return ": ".join(filter(None, (type(error).__name__, error.strerror)))


def _reported(error, data_root):
    reported = _described(error)
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
