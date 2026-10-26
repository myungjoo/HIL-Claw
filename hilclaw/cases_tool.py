"""The tool ``cases.lookup``, which gives the technique-selector the lookup of the stored cases of its run's key (ADR-0173 decision 2).

For the runs of ADR-0120 decision 1 the ``technique-selector`` sub-agent
takes the output of the exact-match lookup of ADR-0073 decision 1 through
this tool before it writes the round's hypothesis record (ADR-0173 decision
5). The tool is that lookup, :func:`hilclaw.case_lookup.find` for the records
the run's ``instance.json`` states, and no second one. It is a tool of the
registry beside the FR-10 tools, not an FR-10 tool: it is not journaled,
appends no line to ``events.ndjson``, selects no backend and keeps nothing
between calls.

The request is exactly ``{"run_id": ...}``. The data root comes from the
data-root source, asked at each call after the request was checked, and never
from the request (ADR-0015 decision 3). The result is
``{"key": ..., "cases": [...], "cases_read": [...], "reports": [...]}``:

- ``key`` is ``{"hw_profile": ..., "op_signature": ...}``, the two key
  directory names, on a hit, and ``None`` for a miss, a run that states no
  op_signature and a stored key record that collides or is not valid;
- ``cases`` is every case the lookup gives, each the parsed document whole,
  in the lookup's order;
- ``cases_read`` is :func:`hilclaw.case_lookup.cases_read` of the lookup, the
  value a record of the selection carries (ADR-0073 decision 3);
- ``reports`` is one ``{"path": ..., "kind": ..., "reason": ...}`` per
  :class:`hilclaw.case_lookup.Report`, unchanged and in its order. A report is
  part of the result, not a failure (ADR-0173 decision 3).

The checks, in this order, each with its kind (ADR-0173 decision 2, table):

1. the request (``invalid_request``): a member other than ``run_id``, or
   ``run_id`` missing or refused by :func:`hilclaw.layout.check_run_id`;
2. the data root (``no_data_root``);
3. the run's ``instance.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``instance.read`` answers
   them);
4. the lookup: any :class:`OSError` of :func:`hilclaw.case_lookup.find`
   (:data:`KIND_CASES_UNREADABLE`, the kind of ``hypotheses.write``).

The message of 4 starts with the key directory relative to the data root, or
``instance.json`` for a run that states no op_signature; the
:class:`OSError` is reported by its class and the text of the system, and
the message says so when the data root is gone. The files read are
``instance.json`` and what :func:`hilclaw.case_lookup.find` reads; nothing is
created. No kind is new.
"""

from hilclaw import (
    case_lookup,
    data_root_source,
    hypotheses_write_tool,
    layout,
    run_file_tools,
    run_files,
    tools,
)

#: The lookup of the cases of the run's key failed in the file system; re-exported from :mod:`hilclaw.hypotheses_write_tool`.
KIND_CASES_UNREADABLE = hypotheses_write_tool.KIND_CASES_UNREADABLE

NAME = "cases.lookup"

_DESCRIPTION = (
    "Look up the stored cases of the key of the run run_id: the exact-match "
    "lookup of the run's hw_profile and op_signature in db/, giving every "
    "valid case of the key directory except those of the run itself, each "
    "whole, in ascending order of their file names, which claims no meaning. "
    'The result is {"key": {"hw_profile": ..., "op_signature": ...} or null, '
    '"cases": [...], "cases_read": [{"run_id": ..., "round": ...}, ...], '
    '"reports": [{"path": ..., "kind": ..., "reason": ...}, ...]}: key is null '
    "when the key is not stored, the run states no op_signature or a stored "
    "key record is reported; cases_read is the value the round's hypothesis "
    "record carries; a report (key_record, invalid, set_apart, unreadable) "
    "names a file that is no case and is not a failure. A case is a hint, "
    "not a target. The request is exactly run_id. The data root is never part "
    "of the request; the tool knows it. Nothing is written. It fails, checked "
    "in this order, with invalid_request for a request that is not exactly "
    "run_id; no_data_root when the data root cannot be obtained; "
    "run_file_missing, run_file_invalid, run_file_unsupported or "
    "run_file_unreadable when the run's instance.json is not there, is "
    "invalid or no regular file, has another schema_version or cannot be "
    "read; and cases_unreadable when the cases of the run's key cannot be "
    "looked up."
)
_MEMBERS = ("run_id",)


def definition(source):
    """Return the tool definition of ``cases.lookup``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function returns the result of the module docstring and raises
    :class:`hilclaw.tools.ToolFailure` of kind ``invalid_request`` for a
    request that is not exactly ``run_id`` or whose ``run_id``
    :func:`hilclaw.layout.check_run_id` refuses; ``no_data_root`` as
    :func:`hilclaw.data_root_source.obtain` does; the four ``run_file_*``
    kinds as :func:`hilclaw.run_file_tools.read` raises them; and
    :data:`KIND_CASES_UNREADABLE`, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def look_up(request):
        return _look_up(source, request)

    return tools.ToolDefinition(NAME, look_up, _DESCRIPTION, _input_schema())


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


def _look_up(source, request):
    run_id = _checked(request)
    data_root = data_root_source.obtain(source)
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
    key = None
    if found.key is not None:
        hw, op = found.key
        key = {"hw_profile": hw.name, "op_signature": op.name}
    return {
        "key": key,
        "cases": list(found.cases),
        "cases_read": case_lookup.cases_read(found),
        "reports": [report._asdict() for report in found.reports],
    }


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
