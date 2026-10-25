"""The tool definition of ``correctness.check`` in the default registry (ADR-0069, ADR-0070).

``ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md``
is the rule; a decision cited by its number alone is one of that record.
``ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md``
is the rule of :func:`default_table` and :func:`definition`, with
``ARCHITECTURE/decisions/ADR-0167-od18-run-tools-registration.md`` for the
run tools' operations of the table.

* :func:`input_schema`: the schema of decision 4, as a Python value. The
  bound of the numbers is :data:`hilclaw.keys.MAX_INTEGER` (ADR-0001
  decision 1), the values of ``point`` are :data:`hilclaw.check_identity.SIM`
  and :data:`hilclaw.check_identity.BOARD`, and the required members are
  :data:`hilclaw.check_identity.MEMBERS`, in that order.
* :data:`DESCRIPTION`: a text that tells the caller what decision 5 says it
  must tell at least: what a call checks; that the tool is journaled, with
  the stored outcome, ``step_open`` and a higher ``execution``; that the
  request has exactly the six members and any other is refused; and that a
  number written with a fraction or an exponent is refused although the
  schema admits it (decision 4). It states no tolerance, number of draws,
  dimension or setting as a value and no rule of who may raise
  ``execution`` or when.
* :func:`default_table`: the backend table of the default registry, whose
  one entry is the mock under :data:`hilclaw.mock_backend.NAME` offering
  this tool with its default script (ADR-0070 decision 3) and ``sim.run``
  and ``board.run`` with theirs (ADR-0167 decision 3: one table for the
  three HW tools of the registry).
* :func:`definition`: the tool definition :func:`hilclaw.tools.default_registry`
  registers, the tool function bound to that table, to
  :func:`hilclaw.harness.seed_source.system` and to
  :func:`hilclaw.gemm_contract.covers` (ADR-0070 decisions 4 and 5).

Choices that are this module's own and no rule of a record: the names, the
text of :data:`DESCRIPTION`, and that the schema is returned by a function,
a fresh object at each call, so that a caller that changes one does not
change the next.

When the modules are imported is this module's own choice too: it imports
:mod:`hilclaw.check_tool` and :mod:`hilclaw.mock_check`, and through them
NumPy, only inside functions, so that importing it or building a definition
imports neither. :func:`default_table` imports :mod:`hilclaw.mock_check` and
:mod:`hilclaw.mock_run` when it is called; the tool function of a definition imports
:mod:`hilclaw.check_tool`, builds the table and binds the tool function at
its first call, and keeps that one bound function for its later calls. A
first call whose import or binding raises keeps nothing, and the next call
binds again; what it raises reaches the front as anything a tool function
raises does.

What the module does not do: it registers nothing; the registration is
:func:`hilclaw.tools.default_registry`'s. No request, option or environment
variable chooses the table, the source of seeds or the predicate. The schema
is a statement to the caller and checks nothing (ADR-0015 decision 2): the
tool function checks its own request (:func:`hilclaw.check_identity.check`
and the frame). Whether Claude Code accepts the keywords of the schema is not
verified (OD-18 sub-question ⑤), and no reduced schema is given. It reads no
file and keeps nothing between calls but the bound function of a definition;
building a definition calls neither the data-root source, the source of
seeds, the predicate, the script nor :func:`default_table`.
"""

from hilclaw import backends, check_identity, gemm_contract, keys, mock_backend, tools
from hilclaw.harness import seed_source

_TOOL = "correctness.check"
_RUN_TOOLS = ("sim.run", "board.run")

#: What a caller of ``correctness.check`` is told of the tool (ADR-0069 decision 5).
DESCRIPTION = (
    "Check the kernel of one attempt of a run at one execution point: the "
    "attempt that run_id, round, candidate and attempt name, at the point that "
    'point states, "sim" or "board". The tool is journaled under the identity '
    "of the call, which includes the point and execution: a call with the "
    "identity of a check that has ended is answered with the stored outcome "
    "and makes no new check, a call with the identity of a check that is "
    "still open is refused with step_open, and a new check of the same "
    "attempt at the same point is a call with a higher execution. The request "
    "has exactly the six members run_id, round, candidate, attempt, execution "
    "and point; a request with any other member is refused as "
    "invalid_request. The inputs of the check, among them the shape, the "
    "number of draws, the tolerance and the seed, are the run's and the "
    "backend's and are no members of the request. Beyond the input schema, "
    "a number of round, candidate, attempt or execution written with a "
    "fraction or an exponent, such as 1.0 or 1e0, is refused."
)


def input_schema():
    """Return the input schema of ``correctness.check`` (ADR-0069 decision 4).

    The result is a new ``dict`` at each call, one JSON object in the strict
    sense of :mod:`hilclaw.tools`; changing it changes no later result.
    """
    count = {"type": "integer", "minimum": 1, "maximum": keys.MAX_INTEGER}
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 0, "maximum": keys.MAX_INTEGER},
            "candidate": dict(count),
            "attempt": dict(count),
            "execution": dict(count),
            "point": {
                "type": "string",
                "enum": [check_identity.SIM, check_identity.BOARD],
            },
        },
        "required": list(check_identity.MEMBERS),
        "additionalProperties": False,
    }


def default_table():
    """Return a new backend table of the default registry (ADR-0070 decision 3, ADR-0167 decision 3).

    It holds one :class:`hilclaw.backends.Backend` named
    :data:`hilclaw.mock_backend.NAME` that offers the three HW tools of the
    default registry: ``correctness.check``, with
    :func:`hilclaw.mock_check.operation` bound to
    :func:`hilclaw.mock_check.default_script`, and ``sim.run`` and
    ``board.run``, each with :func:`hilclaw.mock_run.operation` of that tool
    bound to :func:`hilclaw.mock_run.default_script`. Each operation takes
    five arguments, the log keeper (ADR-0078 decision 6, ADR-0108
    decision 5) the last, and neither default script hands it a log, so a
    call answered by one leaves no file of a compiler's log. It holds no
    ``cpu_standin`` entry, so a call about any other ``accelerator`` is
    ``no_backend``. It imports :mod:`hilclaw.mock_check`, and so NumPy, and
    :mod:`hilclaw.mock_run`.
    """
    from hilclaw import mock_check, mock_run

    operations = {_TOOL: mock_check.operation(mock_check.default_script)}
    for tool in _RUN_TOOLS:
        operations[tool] = mock_run.operation(tool, mock_run.default_script)
    return backends.BackendTable([backends.Backend(mock_backend.NAME, operations)])


def definition(source):
    """Return the :class:`hilclaw.tools.ToolDefinition` of ``correctness.check`` bound to ``source``.

    ``source`` is the data-root source (ADR-0015 decision 3), asked at each
    call and not here. The tool function is
    :func:`hilclaw.check_tool.tool_function` bound to a new
    :func:`default_table`, to :func:`hilclaw.harness.seed_source.system` and
    to :func:`hilclaw.gemm_contract.covers` (ADR-0070 decisions 3 and 4); the
    binding is made at the first call of the definition's function, which
    then imports :mod:`hilclaw.check_tool` and builds the table, and is kept
    for its later calls. The description is :data:`DESCRIPTION` and the
    schema a new :func:`input_schema`. Raises :class:`TypeError` when
    ``source`` is not callable.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")
    bound = []

    def function(request):
        if not bound:
            from hilclaw import check_tool

            bound.append(
                check_tool.tool_function(
                    source=source,
                    table=default_table(),
                    seeds=seed_source.system,
                    covers=gemm_contract.covers,
                )
            )
        return bound[0](request)

    return tools.ToolDefinition(_TOOL, function, DESCRIPTION, input_schema())
