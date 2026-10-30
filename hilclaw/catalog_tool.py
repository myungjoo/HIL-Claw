"""The tool ``catalog.read``, which gives the technique-selector the selection criteria of its run's catalog (ADR-0171 decision 3).

For the runs of ADR-0120 decision 1 the ``technique-selector`` sub-agent
chooses the technique ids of the spec of a round >= 1 (ADR-0171 decision 2)
and reaches the ``## When`` sections of the catalog through this tool, since
its turn session holds no path to ``catalog/``. It is a tool of the registry
beside the FR-10 tools, not an FR-10 tool: it is not journaled, appends no
line to ``events.ndjson``, selects no backend and keeps nothing between
calls.

The request is exactly ``{"run_id": ...}``. The data root comes from the
data-root source, asked at each call after the request was checked, and never
from the request (ADR-0015 decision 3). The result is ``{"entries": [{"id":
..., "when": ...}, ...]}``: one element per entry of the catalog directory of
the run's accelerator that applies to the run, in ascending id order, ``when``
being what :func:`hilclaw.catalog.criteria` returns for it. An entry applies
when :func:`hilclaw.catalog.applies` answers ``True`` for the ``kind``,
``dtype`` and ``layout`` of the run's stated op_signature record and the
``language`` of the contract that covers it (ADR-0190 decision 2), so that
``spec.write`` refuses no id it returns with ``technique_not_applicable``. An
instance that states no op_signature, or one no contract of
:mod:`hilclaw.contract_table` covers, gets no entry and no failure: it is
``spec.write``'s check 5 that names those (ADR-0190 decision 3).

The checks, in this order, each with its kind (ADR-0171 decision 3, table):

1. the request (``invalid_request``): a member other than ``run_id``, or
   ``run_id`` missing or refused by :func:`hilclaw.layout.check_run_id`;
2. the data root (``no_data_root``);
3. the run's ``instance.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``instance.read`` answers
   them);
4. the directory of the instance's ``hw_profile`` ``accelerator`` below
   :data:`hilclaw.catalog.SOURCE` read by :func:`hilclaw.catalog.criteria`:
   a directory that is missing, is refused by the catalog's rules or cannot
   be read (:data:`KIND_CATALOG_UNUSABLE`, the kind of ``spec.write``), for a
   run with no applicable entry as for any other.

Each message of 4 starts with the catalog directory as
``catalog/<accelerator>``; an :class:`OSError` is reported by its class and
the text of the system. The files read are ``instance.json`` and the catalog
directory; nothing is created. No kind is new.
"""

from hilclaw import (
    catalog,
    contract_table,
    data_root_source,
    layout,
    run_file_tools,
    spec_tool,
    tools,
)

#: The accelerator's catalog directory is missing, refused or unreadable; re-exported from :mod:`hilclaw.spec_tool`.
KIND_CATALOG_UNUSABLE = spec_tool.KIND_CATALOG_UNUSABLE

NAME = "catalog.read"

_DESCRIPTION = (
    "Read the selection criteria of the technique catalog of the run run_id: "
    "for each entry of the catalog of the run's accelerator that applies to "
    "the run's op_signature, its technique id and the text of its When "
    "section, which says when the technique is worth trying. The result is "
    '{"entries": [{"id": ..., "when": ...}, ...]} in ascending id order, with '
    "no element when no entry applies; an id is what spec.write takes in "
    "techniques. The "
    "request is exactly run_id. The data root is never part of the request; "
    "the tool knows it. Nothing is written. It fails, checked in this order, "
    "with invalid_request for a request that is not exactly run_id; "
    "no_data_root when the data root cannot be obtained; run_file_missing, "
    "run_file_invalid, run_file_unsupported or run_file_unreadable when the "
    "run's instance.json is not there, is invalid or no regular file, has "
    "another schema_version or cannot be read; and catalog_unusable when the "
    "catalog of the run's accelerator is missing, invalid or cannot be read."
)
_MEMBERS = ("run_id",)


def definition(source):
    """Return the tool definition of ``catalog.read``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` or whose
    ``run_id`` :func:`hilclaw.layout.check_run_id` refuses; ``no_data_root``
    as :func:`hilclaw.data_root_source.obtain` does; the four ``run_file_*``
    kinds as :func:`hilclaw.run_file_tools.read` raises them; and
    :data:`KIND_CATALOG_UNUSABLE`, in the order of the module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def read_catalog(request):
        return _read(source, request)

    return tools.ToolDefinition(NAME, read_catalog, _DESCRIPTION, _input_schema())


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


def _read(source, request):
    run_id = _checked(request)
    data_root = data_root_source.obtain(source)
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    accelerator = stated.hw_profile["accelerator"]
    directory = f"catalog/{accelerator}"
    try:
        found = catalog.criteria(accelerator)
    except FileNotFoundError as e:
        raise _unusable(directory, "is not there") from e
    except catalog.InvalidCatalogError as e:
        raise _unusable(directory, f"is refused: {e}") from e
    except OSError as e:
        reported = ": ".join(filter(None, (type(e).__name__, e.strerror)))
        raise _unusable(directory, f"cannot be read: {reported}") from e
    if not _applicable(stated):
        return {"entries": []}
    return {
        "entries": [{"id": entry_id, "when": when} for entry_id, when in found.items()]
    }


def _applicable(stated):
    if stated.op_signature is None:
        return False
    record = stated.op_signature.record
    covering = contract_table.entry(record)
    if covering is None:
        return False
    return catalog.applies(
        record["kind"], record["dtype"], record["layout"], covering.contract.LANGUAGE
    )


def _unusable(directory, problem):
    return tools.ToolFailure(
        KIND_CATALOG_UNUSABLE, f"{directory}: the catalog directory {problem}"
    )
