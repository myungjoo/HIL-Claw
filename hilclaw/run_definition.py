"""The member list, the input schema and the descriptions of ``sim.run`` and ``board.run`` (ADR-0106).

``ARCHITECTURE/decisions/ADR-0106-od18-run-tools-request-schema.md`` is the
rule; a decision cited by its number alone is one of that record. The module
renders, ahead of the tool functions, what its decisions 2 to 5 fix:

* :data:`MEMBERS`: "A request of either tool has exactly the five members
  ``run_id``, ``round``, ``candidate``, ``attempt`` and ``execution`` [...]
  and no other" (decision 2), built from :data:`hilclaw.run_identity.NUMBERS`.
* :func:`check`: "A request of either tool with a member no record names is
  a refused request: the tool failure of the reserved kind
  ``invalid_request``", for every such name and every value it carries,
  ``null`` included, in moment ① (decision 3).
* :func:`input_schema`: the one schema of decision 4 for both tools, as a
  Python value. The bound of the numbers is :data:`hilclaw.keys.MAX_INTEGER`
  (ADR-0001 decision 1) and the required members are :data:`MEMBERS`, in
  that order.
* :data:`SIM_DESCRIPTION`, :data:`BOARD_DESCRIPTION`: texts that tell the
  caller what decision 5 says each must tell at least: the point the tool
  times and that no member states it; that the tool is journaled, with the
  stored outcome, ``step_open`` and a higher ``execution``; that the run's
  own ``instance.json`` supplies the dimensions, ``n_max``, the objective and
  the bound, and that the seed and the settings are no members; that the
  request has exactly the five members and any other, ``point`` among them,
  is refused; and that a number written with a fraction or an exponent is
  refused although the schema admits it (decision 4). They differ in the
  point and state no dimension, ``n_max``, bound, seed or setting as a value
  and no rule of who may raise ``execution`` or which execution counts.

Choices that are this module's own and no rule of a record:

* The names, the texts of the descriptions, and that the schema is returned
  by a function, a fresh object at each call, so that a caller that changes
  one does not change the next. Both tools are given the same schema by the
  same function; whether code holds one object or two is the code task's
  (decision 4).
* :data:`MEMBERS` is a ``tuple`` in the order of ADR-0062 decision 4; the
  order means nothing.
* A ``request`` whose type is not exactly ``dict`` is refused with the same
  kind. In a tool function the check of the frame refuses it first; the
  choice keeps the function total.
* A key whose type is not exactly ``str``, an instance of a subclass of
  ``str`` included, is a member no record names. It is refused without
  calling any code of it: it is not compared, hashed or printed.
* Of several members no record names, the first in the order of the request
  is the one refused.
* The message of the refusal starts with the name the request gave the
  member when that name is 1 to 32 characters of ``A-Z``, ``a-z``, ``0-9``,
  ``_``, ``.`` and ``-``, and with the fixed text ``(a name not shown)``
  otherwise, so that it shows no control character and no long name. It goes
  on to name the five members of :data:`MEMBERS`, is at most 160 characters
  long and shows nothing of the value of the member, not even its type.
  Nothing may depend on its wording beyond the name at its start.

What the module does not do: it is no tool and no step and is bound to none.
It registers nothing, builds no tool definition and binds no backend, source
of seeds or tool function; registration is open (ADR-0106 Boundaries). It
checks none of the values of the five members: the frame does
(:mod:`hilclaw.journaled_tool`). The schema is a statement to the caller and
checks nothing (ADR-0015 decision 2). Whether Claude Code accepts its
keywords is not verified (OD-18 sub-question ⑤), and no reduced schema is
given. It reads no file and keeps nothing between calls. It imports
:mod:`re` and :mod:`hilclaw.keys`, :mod:`hilclaw.run_identity` and
:mod:`hilclaw.tools` and nothing else.
"""

import re

from hilclaw import keys, run_identity, tools

#: The members of a request of ``sim.run`` and ``board.run``; no other is taken (ADR-0106 decision 2).
MEMBERS = ("run_id", *run_identity.NUMBERS, "execution")

_SHOWN = re.compile(r"[A-Za-z0-9_.-]{1,32}")
_NOT_SHOWN = "(a name not shown)"
_NO_OBJECT = "the request is no object"
_UNNAMED = (
    ": is no member of a request of this tool, which takes "
    f"{', '.join(MEMBERS[:-1])} and {MEMBERS[-1]} only"
)

_COMMON = (
    "The request names the attempt by run_id, round, candidate and attempt; "
    "no member states the point. The tool is journaled under the identity of "
    "the call, which includes execution: a call with the identity of a timing "
    "run that has ended is answered with the stored outcome and makes no new "
    "run, a call with the identity of one that is still open is refused with "
    "step_open, and a new timing run of the same attempt at the same point is "
    "a call with a higher execution. The run's own instance.json supplies the "
    "dimensions, n_max, the objective and the bound; the seed and the "
    "settings are no members of the request. The request has exactly the "
    "five members run_id, round, candidate, attempt and execution; a request "
    "with any other member, point among them, is refused as invalid_request. "
    "Beyond the input schema, a number of round, candidate, attempt or "
    "execution written with a fraction or an exponent, such as 1.0 or 1e0, "
    "is refused."
)

#: What a caller of ``sim.run`` is told of the tool (ADR-0106 decision 5).
SIM_DESCRIPTION = "Time the kernel of one attempt of a run at the sim point. " + _COMMON
#: What a caller of ``board.run`` is told of the tool (ADR-0106 decision 5).
BOARD_DESCRIPTION = (
    "Time the kernel of one attempt of a run at the board point. " + _COMMON
)


def check(request):
    """Refuse a request of ``sim.run`` or ``board.run`` with a member no record names.

    - ``request``: the request of a call of either tool.

    The parameter has no default. This is the convention of the ``check`` of
    :func:`hilclaw.journaled_tool.tool_function`, which calls it in moment ①
    after the frame checked the five members and before the data root is
    asked. Returns ``None`` when every key of ``request`` is exactly one of
    :data:`MEMBERS`.

    Raises :class:`hilclaw.tools.ToolFailure` of kind
    :data:`hilclaw.tools.KIND_INVALID_REQUEST` (ADR-0106 decision 3) when

    1. the request has a key that is not exactly one of :data:`MEMBERS`,
       compared as it is, case-sensitive, whatever its value, ``None``
       included; of several, the first in the order of the request is named;
    2. a key is not exactly a ``str``, or ``request`` is not exactly a
       ``dict`` (the module's own choice; see the module docstring).

    No value is looked at, the request is not modified, no code of a key or
    a value is called, and no file is read or written.
    """
    if type(request) is not dict:
        raise tools.ToolFailure(tools.KIND_INVALID_REQUEST, _NO_OBJECT)
    for key in request:
        if type(key) is not str or key not in MEMBERS:
            shown = type(key) is str and _SHOWN.fullmatch(key)
            message = (key if shown else _NOT_SHOWN) + _UNNAMED
            raise tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def input_schema():
    """Return the input schema of ``sim.run`` and ``board.run`` (ADR-0106 decision 4).

    The result is a new ``dict`` at each call, one JSON object in the strict
    sense of :mod:`hilclaw.tools`; changing it changes no later result. It
    uses the keywords ``type``, ``properties``, ``required``,
    ``additionalProperties``, ``pattern``, ``minimum`` and ``maximum`` only.
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
        },
        "required": list(MEMBERS),
        "additionalProperties": False,
    }
