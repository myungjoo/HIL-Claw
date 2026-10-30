"""The registry tool ``coder.run``, which performs the coder call of a first-case turn (ADR-0141 decisions 2 and 3).

``ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md``
decision 2 fixes that the coder-driver reaches :func:`hilclaw.coder_call.call`
as the registry tool ``coder.run`` through the MCP front (form (T)). The tool
function performs that function with the request it was given, the data-root
source the registry was built with and a runtime, and returns what it
returns. It adds nothing to the call's contract: the request, the result and
the kinds in their order are those of :func:`hilclaw.coder_call.call` and
:data:`hilclaw.coder_call.FAILURE_KINDS`, and every exception the function
propagates passes out of the tool function unchanged. The tool is not
journaled (ADR-0126 decision 7): it appends no line to ``events.ndjson``.

Decision 3 held while slice (d) was absent: the registry bound the tool to
:class:`NoContainerRuntime`, whose ``available()`` returns false. ADR-0137
code slice 2 replaced that binding with
:class:`hilclaw.coder_runtime.DockerRuntime` in
:func:`hilclaw.tools.default_registry`; :class:`NoContainerRuntime` stays as a
runtime that starts nothing.

The choices ADR-0141 decision 2 leaves to the code slice, as made here: the
module is this one; the description and the input schema are
:data:`_DESCRIPTION` and :func:`_input_schema`, the latter stating the forms
:func:`hilclaw.layout.attempt_artefact` checks; the tool has no message text
of its own; :func:`definition` refuses a runtime without a callable
``available`` and ``run`` with :class:`TypeError`; and
:meth:`NoContainerRuntime.run` raises
:class:`hilclaw.coder_call.CoderNotStartedError`.
"""

from hilclaw import coder_call, keys, tools

NAME = "coder.run"

_DESCRIPTION = (
    "Perform the coder call for one attempt of the run run_id: the coder "
    "writes a kernel from the spec of that attempt, and the admitted files it "
    "wrote are brought in below the attempt's output directory, "
    "runs/<run_id>/rounds/<round>/coder/candidates/<candidate>/attempts/"
    "<attempt>/output. The spec of that attempt must already be written by "
    "spec.write. The request is exactly run_id, a string of lowercase "
    "letters, digits, _ and - that starts with a letter or a digit and has at "
    "most 64 characters; round, an integer of 0 or more; and candidate and "
    "attempt, integers of 1 or more. The data root is never part of the "
    'request; the tool knows it. The result is {"taken": [...], '
    '"scratch_removed": true or false}: the names of the files brought in, '
    "possibly none, and whether the coder's scratch directory was removed. "
    "When it fails with a kind up to no_container_runtime, nothing was "
    "created. It fails, checked in this order, with invalid_request for a "
    "request that is not exactly those four members in those forms; "
    "no_data_root when the data root cannot be obtained; run_file_missing, "
    "run_file_unreadable, run_file_invalid or run_file_unsupported when the "
    "run's instance.json is not there, cannot be read, is invalid (a "
    "coder_model that is no full model name included) or has another "
    "schema_version; coder_model_not_stated when instance.json states no "
    "coder_model; output_exists when the attempt already has an entry output, "
    "or one was made during the call; spec_unreadable when the spec cannot be "
    "read, a missing spec included; spec_not_regular_file when it is no "
    "regular file; spec_invalid when it is refused as a spec or its id is not "
    "the tuple of the request; spec_unsupported when it has another "
    "schema_version; no_container_runtime when the package can start no "
    "container for the coder, which is the answer while it has none it can "
    "use; spec_changed when the spec changed while it was copied for the "
    "coder; base_unreadable when the source of the spec's feedback.base "
    "cannot be copied for the coder; coder_not_started when the coder could not be started; "
    "coder_not_ended when the coder process ended with a status other than 0, "
    "and nothing was brought in; attempt_directory_unlistable, "
    "scratch_root_unlistable, place_unlistable, entry_kind_undetermined or "
    "candidate_unreadable when the bring-in could not see what it has to see; "
    "and output_not_written when output could not be written. Report the kind "
    "in every case."
)
_MEMBERS = ("run_id", "round", "candidate", "attempt")


class NoContainerRuntime:
    """A runtime that starts nothing (ADR-0141 decision 3).

    It starts no process and no container, reads no environment variable and
    takes no option. It was the package's binding while slice (d) was absent;
    ADR-0137 code slice 2 replaced it with
    :class:`hilclaw.coder_runtime.DockerRuntime` in the source of
    :func:`hilclaw.tools.default_registry`.
    """

    def available(self):
        """Return ``False``: the package has no container runtime it can use."""
        return False

    def run(self, scratch_root, *, coder_model):
        """Start nothing and raise :class:`hilclaw.coder_call.CoderNotStartedError`."""
        raise coder_call.CoderNotStartedError("the package starts no container")


def definition(source, runtime):
    """Return the tool definition of ``coder.run``, bound to ``source`` and ``runtime``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3 and ``runtime`` the seam of
    :mod:`hilclaw.coder_call`; neither is called here. Raises
    :class:`TypeError` when ``source`` is not callable or ``runtime`` has no
    callable ``available`` or ``run``.

    The tool function returns ``hilclaw.coder_call.call(request,
    source=source, runtime=runtime)``; its failures and exceptions are that
    function's, unchanged.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")
    for method in ("available", "run"):
        if not callable(getattr(runtime, method, None)):
            raise TypeError(f"the runtime must have a callable {method}")

    def run_coder(request):
        return coder_call.call(request, source=source, runtime=runtime)

    return tools.ToolDefinition(NAME, run_coder, _DESCRIPTION, _input_schema())


def _input_schema():
    def number(minimum):
        return {"type": "integer", "minimum": minimum, "maximum": keys.MAX_INTEGER}

    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": number(0),
            "candidate": number(1),
            "attempt": number(1),
        },
        "required": list(_MEMBERS),
        "additionalProperties": False,
    }
