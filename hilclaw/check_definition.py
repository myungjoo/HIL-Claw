"""The input schema and the description of ``correctness.check``; bound to no registry.

``ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md``
is the rule; a decision cited by its number alone is one of that record.

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

Choices that are this module's own and no rule of a record: the names, the
text of :data:`DESCRIPTION`, and that the schema is returned by a function,
a fresh object at each call, so that a caller that changes one does not
change the next.

What the module does not do: it registers nothing, builds no
:class:`hilclaw.tools.ToolDefinition` and binds no tool function. The schema
is a statement to the caller and checks nothing (ADR-0015 decision 2): the
tool function checks its own request (:func:`hilclaw.check_identity.check`
and the frame). Whether Claude Code accepts the keywords of the schema is not
verified (OD-18 sub-question ⑤), and no reduced schema is given. It reads no
file and keeps nothing between calls. It imports :mod:`hilclaw.check_identity`
and :mod:`hilclaw.keys` and nothing else.
"""

from hilclaw import check_identity, keys

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
