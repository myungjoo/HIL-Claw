"""The tool ``spec.write``, which composes and writes the spec of the first round-0 coder call of a first-case run (ADR-0138 decision 3).

For the runs of ADR-0120 decision 1 whose ``instance.json`` states
``candidates_per_round`` 1, the ``coder-driver`` has the spec of the bring-up
call of round 0 (``round`` 0, ``candidate`` 1, ``attempt`` 1) written through
this tool before it requests that call (ADR-0138 decisions 1 and 3). It is a
tool of the registry beside the FR-10 tools, not an FR-10 tool: it is not
journaled, appends no line to ``events.ndjson``, selects no backend and keeps
nothing between calls (ADR-0138 decision 3).

The request is exactly ``{"run_id": ..., "round": 0, "candidate": 1,
"attempt": 1}``, the numbers in the form of ADR-0015 decision 4: ``int``
values, a ``bool`` being none. The data root comes from the data-root source,
asked at each call after the request was checked, and never from the request
(ADR-0015 decision 3). The result is the empty object ``{}``.

The checks, in this order, each with its kind; the first that fails decides
and nothing is created before 8 (ADR-0138 decision 3, table):

1. the request (``invalid_request``): a member other than the four, one
   missing, a value outside its form or a tuple other than 0, 1, 1;
2. the data root (``no_data_root``);
3. the run's ``instance.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``instance.read`` answers
   them);
4. ``candidates_per_round`` stated (:data:`KIND_CANDIDATES_PER_ROUND_NOT_STATED`)
   and equal to 1 (:data:`KIND_CANDIDATES_PER_ROUND_NOT_COVERED`);
5. ``op_signature`` stated (:data:`KIND_OP_SIGNATURE_NOT_STATED`) and covered
   by :func:`hilclaw.gemm_contract.covers` (:data:`KIND_OP_SIGNATURE_NOT_COVERED`);
6. ``objective`` stated (:data:`KIND_OBJECTIVE_NOT_STATED`);
7. the document of ADR-0138 decision 2 composed and encoded into the written
   form of ADR-0029 decision 2, accepted by :func:`hilclaw.spec_file.parse`
   and given its final name by :func:`hilclaw.spec_file.final_name`
   (:data:`KIND_SPEC_INVALID`, a document that cannot be so encoded among
   them); no valid ``instance.json`` makes this check refuse today;
8. the write by :func:`hilclaw.spec_file.write`: a taken final name
   (:data:`KIND_SPEC_EXISTS`; nothing is written, and the file under the name
   is not read or compared), any :class:`OSError`, a data root gone since 2
   among them (:data:`KIND_SPEC_NOT_WRITTEN`).

The document holds ``schema_version`` 2; ``id`` with the request's
``run_id``, ``round`` 0, ``candidate`` 1, ``attempt`` 1, ``candidates`` 1 and
``relation`` ``single``, and no ``variant``; ``hw_profile`` with the ``key``
and ``record`` of the instance's member ``hw_profile``; ``task`` with
``op_signature``, the ``key`` and the whole ``record`` of the instance's
member, ``contract``, :func:`hilclaw.gemm_contract.task_contract` of that
record's shape, and ``objective``, the instance's member; ``guidance`` with an
empty ``techniques``; and ``feedback`` with an empty ``attempts``. There is no
``task.build``, ``feedback.base``, ``repair`` or ``ext`` (ADR-0138 decision
2). The document is encoded by the rule of ``verdicts.write``:
``json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)``
followed by one line feed, in UTF-8 without a byte order mark.

Each message starts with the path of the file concerned relative to the data
root. An :class:`OSError` is reported by its class and the text of the
system, without the absolute path, and says so when the data root is gone.
What :func:`hilclaw.gemm_contract.covers` or a refusal of
:func:`hilclaw.spec_file.write` other than those of 8 raises, which a valid
``instance.json`` and check 7 do not leave room for, is mapped to no kind: it
passes out of the tool function and :func:`hilclaw.tools.call` answers it with
``tool_crashed``.

The only file read is ``instance.json``; ``STATE.json`` and the stored key
records below ``db/`` are not. The only file written is the spec, through
:func:`hilclaw.spec_file.write`. The four new kinds are names of the tool
layer and none is reserved; the four ``run_file_*`` kinds are the reserved
ones of ADR-0019, widened to this read by ADR-0138 decision 3.
"""

import json

from hilclaw import (
    coder_call,
    data_root_source,
    gemm_contract,
    layout,
    run_admission,
    run_file_tools,
    run_files,
    run_objective,
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
#: The composed content is refused as a spec or has no final name; nothing was written (ADR-0126 decision 3).
KIND_SPEC_INVALID = coder_call.KIND_SPEC_INVALID
#: The spec's final name is taken; nothing was written, read or compared.
KIND_SPEC_EXISTS = "spec_exists"
#: A step of the write failed in the file system; nothing was put under the final name.
KIND_SPEC_NOT_WRITTEN = "spec_not_written"

NAME = "spec.write"

_DESCRIPTION = (
    "Compose and write the spec of the first coder call of round 0 of the run "
    "run_id, the bring-up call with round 0, candidate 1 and attempt 1, from "
    "the run's instance.json: its hw_profile, its op_signature with the "
    "contract that covers it, and its objective, with no technique and no "
    "feedback. The spec is written once to "
    "runs/<run_id>/rounds/0000/coder/candidates/01/attempts/01/spec.json and "
    "never replaced. Call it before you request that coder call; request no "
    "call when it fails with a kind other than spec_exists, and report the "
    "kind in every case. The request is exactly run_id, round 0, candidate 1 "
    "and attempt 1. The result is {}. The data root is never part of the "
    "request; the tool knows it. Nothing is written when it fails. It fails, "
    "checked in this order, with invalid_request for a request that is not "
    "exactly run_id, round, candidate and attempt, or whose round, candidate "
    "and attempt are not 0, 1 and 1; no_data_root when the data root cannot "
    "be obtained; run_file_missing, run_file_invalid, run_file_unsupported or "
    "run_file_unreadable when the run's instance.json is not there, is "
    "invalid or no regular file, has another schema_version or cannot be "
    "read; candidates_per_round_not_stated when instance.json states no "
    "candidates_per_round; candidates_per_round_not_covered when it states "
    "one other than 1; op_signature_not_stated when it states no "
    "op_signature; op_signature_not_covered when the op_signature is not "
    "covered by the contract of the run tools; objective_not_stated when it "
    "states no objective; spec_invalid when the composed spec is refused; "
    "spec_exists when the spec is already there, which is not read or "
    "compared; and spec_not_written when a step of the write fails."
)
_MEMBERS = ("run_id", "round", "candidate", "attempt")
_TUPLE = {"round": 0, "candidate": 1, "attempt": 1}


def definition(source):
    """Return the tool definition of ``spec.write``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id``,
    ``round``, ``candidate`` and ``attempt``, whose ``run_id``
    :func:`hilclaw.layout.check_run_id` refuses, whose numbers are not ``int``
    values in the form of ADR-0015 decision 4 or are not 0, 1 and 1;
    ``no_data_root`` as :func:`hilclaw.data_root_source.obtain` does; the four
    ``run_file_*`` kinds as :func:`hilclaw.run_file_tools.read` raises them;
    and the kinds of this module, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def write_spec(request):
        return _write(source, request)

    return tools.ToolDefinition(NAME, write_spec, _DESCRIPTION, _input_schema())


def _input_schema():
    numbers = {
        name: {"type": "integer", "minimum": value, "maximum": value}
        for name, value in _TUPLE.items()
    }
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            **numbers,
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
    for name, wanted in _TUPLE.items():
        value = request[name]
        if type(value) is not int:
            raise _invalid(f"{name}: must be an int, got {type(value).__name__}")
        if value != wanted:
            raise _invalid(
                f"{name}: must be {wanted}: this tool writes only the spec of "
                f"round 0, candidate 1, attempt 1, got {value}"
            )
    return run_id


def _write(source, request):
    run_id = _checked(request)
    data_root = data_root_source.obtain(source)
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    _admitted(run_id, stated)
    content, path = _content(data_root, run_id, _compose(run_id, stated))
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


def _content(data_root, run_id, document):
    place = layout.attempt_artefact(data_root, run_id, *_TUPLE.values(), "spec.json")
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


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
