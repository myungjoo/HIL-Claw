"""The request side of the identity of a call of ``sim.run`` and ``board.run``: the ``step`` and the numbers.

``ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`` is the
rule; a decision cited by its number alone is one of that record. The module
renders, ahead of the tool functions, what its decisions 3 and 4 fix of a
call, with the values of ADR-0183 decision 2:

* :data:`STEP_SIM_RUN`, :data:`STEP_BOARD_RUN`, :data:`STEPS`: each tool has
  exactly one ``step`` value, ``sim_run_timing_v2`` for ``sim.run`` and
  ``board_run_timing_v2`` for ``board.run`` (ADR-0183 decision 2, which
  retires the values of decision 3 and keeps its rule), the same for every
  contract.
* :data:`NUMBERS`: "All three numbers are required" (decision 4).
* :func:`step_of`: the ``step`` value "follows from the tool and not from
  anything a request says" (decision 1, as decision 3 fixes it); "the tool
  function of each tool has its one value from the contract" (decision 3).

Choices that are this module's own and no rule of a record:

* :data:`STEPS` is a ``tuple`` in the order sim, board. The order means
  nothing, and it is no list of the values of one tool: each tool has one.
* :func:`step_of` refuses every value but the two tool names, compared as
  they are. That it refuses ``correctness.check``, ``profiler.collect`` and
  every other name is this module's choice: their ``step`` values are not this
  contract's.
* A value whose type is not exactly ``str``, an instance of a subclass of
  ``str`` included, is refused with :class:`TypeError` without calling any
  code of the value: it is not compared, hashed or printed.
* The message of a refusal is one of two texts built when the module is
  imported, at most 100 characters long. It names the two tool names and
  shows nothing of the value that was given, not even its type. Nothing may
  depend on its wording.

What the module does not do: it is no tool and no step and is bound to none.
It holds no tool's own check of a request and looks at no request: the five
members of decision 4 are the frame's, checked in moment ① (decision 6). It
does not close the member list of a request: that the list is closed at those
five and that a member no record names, a member ``point`` among them, is
refused are ADR-0106's (decisions 2 and 3) and live in
:mod:`hilclaw.run_definition`. It builds no identity. It does not say which
builder the tool functions use (ADR-0062 Consequences). It says nothing of who
may raise ``execution`` or which of several executions counts (OD-10, OD-17,
OD-18 sub-question ⑳), except that for the comparisons of a verdict in the
runs of ADR-0120 decision 1, ADR-0140 decision 3 says which result enters:
exactly one, the comparison being refused otherwise
(:mod:`hilclaw.timings_tool`). It gives no rule for the ``step`` values of
another tool: decision 3 "says how these two values were formed and is no
rule for the ``step`` values of another tool". It keeps nothing between
calls, reads no file and imports nothing.
"""

#: The one ``step`` of ``sim.run`` (ADR-0062 decision 3, ADR-0183 decision 2).
STEP_SIM_RUN = "sim_run_timing_v2"
#: The one ``step`` of ``board.run`` (ADR-0062 decision 3, ADR-0183 decision 2).
STEP_BOARD_RUN = "board_run_timing_v2"
#: The ``step`` values of the two tools, each once; the order means nothing.
STEPS = (STEP_SIM_RUN, STEP_BOARD_RUN)

#: The numbers a request of either tool requires (ADR-0062 decision 4), as a builder of :mod:`hilclaw.journaled_tool` takes them.
NUMBERS = ("round", "candidate", "attempt")

_SIM = "sim.run"
_BOARD = "board.run"
_STEP_OF = {_SIM: STEP_SIM_RUN, _BOARD: STEP_BOARD_RUN}
_ACCEPTED = f'tool: must be "{_SIM}" or "{_BOARD}", '
_NO_STRING = _ACCEPTED + "got a value that is not exactly a string"
_OTHER = _ACCEPTED + "got another string"


def step_of(tool):
    """Return the one ``step`` value of the run tool named ``tool`` (ADR-0062 decision 3, ADR-0183 decision 2).

    - ``tool``: the name of the tool, ``"sim.run"`` or ``"board.run"``.

    The parameter has no default. Returns :data:`STEP_SIM_RUN` for exactly
    ``"sim.run"`` and :data:`STEP_BOARD_RUN` for exactly ``"board.run"``, and
    no other value. It is meant for building a tool function, not for
    answering a call: it takes no request and raises no
    :class:`hilclaw.tools.ToolFailure`.

    Raises :class:`TypeError` when ``tool`` is not exactly a ``str``, without
    calling any code of it, and :class:`ValueError` for any other ``str``:
    compared as it is, nothing is normalised. The refusal of the names of the
    other tools is this module's choice (see the module docstring). The
    message names the two tool names and shows nothing of ``tool``.
    """
    if type(tool) is not str:
        raise TypeError(_NO_STRING)
    if tool not in _STEP_OF:
        raise ValueError(_OTHER)
    return _STEP_OF[tool]
