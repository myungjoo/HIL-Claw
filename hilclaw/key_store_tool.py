"""The tool ``key.store``, which stores the two key record files of a run for the Round-Manager (ADR-0134 decision 3).

For the runs of ADR-0120 decision 1 the Round-Manager stores the hw_profile
and the op_signature record its run's ``instance.json`` states, each in its
key record file of ``db/`` (ADR-0004 decision 5), through this tool only, as
the first round step of every turn that carries a round (ADR-0134 decisions 2
and 5). It is a tool of the registry beside the FR-10 tools, not an FR-10
tool: it is not journaled, appends no line to ``events.ndjson``, selects no
backend and keeps nothing between calls (ADR-0134 decision 3).

The request is exactly ``{"run_id": ...}``. The data root comes from the
data-root source, asked at each call after the request was checked, and never
from the request (ADR-0015 decision 3). The result is
``{"hw_profile_created": bool, "op_signature_created": bool}``: the
``created`` flag of the :class:`hilclaw.key_records.Stored` of each store, so
true exactly when this call created that file.

The checks, in this order, each with its kind; the first that fails decides
and nothing is created before 5 (ADR-0134 decision 3, table):

1. the request (``invalid_request``);
2. the data root (``no_data_root``);
3. the run's ``instance.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``instance.read`` answers
   them);
4. an ``op_signature`` stated (:data:`KIND_OP_SIGNATURE_NOT_STATED`); without
   one nothing is stored, not the hw_profile alone (ADR-0134 decision 4);
5. :func:`hilclaw.key_records.store_hw_profile` of ``hw_profile.record``: a
   collision or an invalid stored record (:data:`KIND_KEY_RECORD_INVALID`);
   any :class:`OSError`, a failing read of the stored record, a data root gone
   since 2 and a name taken during the write and free again when re-read
   among them (:data:`KIND_KEY_NOT_WRITTEN`);
6. :func:`hilclaw.key_records.store_op_signature` of ``op_signature.record``
   below ``hw_profile.key``: the same two kinds, a hw_profile record gone since
   5 being :data:`KIND_KEY_NOT_WRITTEN` too. A refusal here keeps the file 5
   created (ADR-0014 decision 6).

Each message starts with the path of the file concerned relative to the data
root, where there is one. An :class:`OSError` is reported by its class and
the text of the system, without the absolute path, and says so when the data
root is gone.

A stored record whose attributes (``hw_source``, ``label``) differ from the
instance's is kept as it is and the call succeeds; the difference is neither
compared nor reported (ADR-0134 decision 6). An error of :mod:`hilclaw.keys`
or :mod:`hilclaw.layout` from a store, which a valid parsed ``instance.json``
does not leave room for (ADR-0134 decision 4), is mapped to no kind: it passes
out of the tool function and :func:`hilclaw.tools.call` answers it with
``tool_crashed``.

The only files read are ``instance.json`` and, through
:mod:`hilclaw.key_records`, the two key record files; ``STATE.json`` is not
read, and neither the round nor the scope is checked. The only files written
are the two record files, through :func:`hilclaw.key_records.store_hw_profile`
and :func:`hilclaw.key_records.store_op_signature`. The kinds of this module
are names of the tool layer and none is reserved; the four ``run_file_*``
kinds are the reserved ones of ADR-0019, widened to this read by ADR-0134
decision 3.
"""

import contextlib

from hilclaw import (
    case_tool,
    data_root_source,
    key_records,
    layout,
    run_admission,
    run_file_tools,
    run_files,
    tools,
)

#: ``instance.json`` states no op_signature, so the run has no key; nothing was stored (ADR-0041 decision 4).
KIND_OP_SIGNATURE_NOT_STATED = run_admission.KIND_OP_SIGNATURE_NOT_STATED
#: A stored key record file is invalid or collides with the instance's record; nothing was written for it.
KIND_KEY_RECORD_INVALID = case_tool.KIND_KEY_RECORD_INVALID
#: A step of a store failed in the file system; that record file was not written.
KIND_KEY_NOT_WRITTEN = "key_not_written"

NAME = "key.store"

_DESCRIPTION = (
    "Store the two key records of the run run_id in the knowledge tree: the "
    "hw_profile record and the op_signature record its instance.json states, "
    "each written once in its key record file and never replaced. Call it as "
    "the first step of every turn that carries a round; a key already stored "
    "is left as it is. The result is "
    '{"hw_profile_created": true or false, "op_signature_created": true or '
    "false}: whether this call created each file. The data root is never part "
    "of the request; the tool knows it. It fails, checked in this order, with "
    "invalid_request for a request that is not exactly run_id; no_data_root "
    "when the data root cannot be obtained; run_file_missing, "
    "run_file_invalid, run_file_unsupported or run_file_unreadable when the "
    "run's instance.json is not there, is invalid or no regular file, has "
    "another schema_version or cannot be read; op_signature_not_stated when "
    "instance.json states no op_signature, nothing being stored; then, for "
    "hw_profile.json and after it op_signature.json, key_record_invalid when "
    "the stored record is invalid or collides, and key_not_written when a "
    "step of the store fails. A failure at op_signature.json keeps the "
    "hw_profile.json this call created."
)
_MEMBERS = ("run_id",)
_OP_RECORD = "op_signature.json"


def definition(source):
    """Return the tool definition of ``key.store``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` or whose
    ``run_id`` :func:`hilclaw.layout.check_run_id` refuses; ``no_data_root``
    as :func:`hilclaw.data_root_source.obtain` does; the four ``run_file_*``
    kinds as :func:`hilclaw.run_file_tools.read` raises them; and the kinds of
    this module, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def store_key(request):
        return _store(source, request)

    return tools.ToolDefinition(NAME, store_key, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
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
            f"the request takes the member run_id only, not {', '.join(map(repr, others))}"
        )
    if "run_id" not in request:
        raise _invalid("the request lacks the member run_id")
    try:
        return layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise _invalid(f"the request's {e}") from e


def _store(source, request):
    run_id = _checked(request)
    data_root = data_root_source.obtain(source)
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    if stated.op_signature is None:
        file = run_files.relative(run_id, "instance.json")
        raise tools.ToolFailure(
            KIND_OP_SIGNATURE_NOT_STATED,
            f"{file}: states no op_signature, so the run has no key; nothing "
            "was stored",
        )
    hw_key = stated.hw_profile_key
    hw_path = layout.hw_profile_record(data_root, hw_key)
    op_path = layout.op_signature_file(
        data_root, hw_key, stated.op_signature.key, _OP_RECORD
    )
    with _mapped(data_root, hw_path):
        hw = key_records.store_hw_profile(data_root, stated.hw_profile)
    with _mapped(data_root, op_path):
        op = key_records.store_op_signature(
            data_root, hw_key, stated.op_signature.record
        )
    return {"hw_profile_created": hw.created, "op_signature_created": op.created}


@contextlib.contextmanager
def _mapped(data_root, path):
    file = _relative(path, data_root)
    try:
        yield
    except (key_records.KeyCollisionError, key_records.CorruptKeyRecordError) as e:
        raise tools.ToolFailure(KIND_KEY_RECORD_INVALID, str(e)) from e
    except key_records.KeyRecordNotFoundError as e:
        raise tools.ToolFailure(
            KIND_KEY_NOT_WRITTEN, f"{file}: was not written: {e}"
        ) from e
    except OSError as e:
        raise tools.ToolFailure(
            KIND_KEY_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root)}",
        ) from e


def _relative(path, data_root):
    return path.relative_to(data_root).as_posix()


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
