"""The tool ``timings.compare``, which gives the evaluator the ``difference`` of two attempts at one point (ADR-0140 decisions 3 and 4).

For the runs of ADR-0120 decision 1 the ``evaluator`` sub-agent gets the
``difference`` of a ``comparison`` entry of ``verdicts.json`` from this tool
and copies it (ADR-0140 decision 2). It is a tool of the registry beside the
FR-10 tools, not an FR-10 tool: it is not journaled, appends no line to
``events.ndjson`` and selects no backend.

The request has exactly ``run_id``, ``metric``, ``point``, ``measured`` and
``against``, all required. ``metric`` is exactly ``"latency_minimisation"``;
``point`` is exactly ``"sim"`` or ``"board"``, compared as it is, and names
the ``step`` read, :data:`hilclaw.run_identity.STEP_SIM_RUN` or
:data:`~hilclaw.run_identity.STEP_BOARD_RUN`; ``measured`` and ``against``
are each a ``dict`` of exactly ``round`` (an ``int`` from 0), ``candidate``
and ``attempt`` (``int`` values from 1), each at most
:data:`hilclaw.keys.MAX_INTEGER`, a ``bool`` being none, and they are not
equal. The data root comes from the data-root source, asked at each call
after the request was checked, and never from the request.

The result is ``{"difference": d, "measured": {"execution": n, "outcome":
o}, "against": {"execution": n, "outcome": o}}``, each side naming the end
line whose measurement entered and that result's ``outcome``.

The checks, in this order, each with its kind (ADR-0140 decision 3, table):
the request (``invalid_request``); the data root (``no_data_root``); the read
of ``runs/<run_id>/events.ndjson`` from its first line by
:func:`hilclaw.checks_tool.log_lines`, with its four ``run_file_*`` kinds;
then the step lines in line order, the first that fails deciding: a step line
about any attempt that :func:`hilclaw.journal.identity_of` refuses
(``run_file_invalid``) and an end line of ``measured`` or ``against`` at the
``step`` whose ``result`` is not an admitted timing result
(:data:`KIND_TIMING_RESULT_INVALID`); then ``measured`` and after it
``against`` by the measurement rule (:data:`KIND_MEASUREMENT_SEVERAL`,
:data:`KIND_MEASUREMENT_UNKNOWN`, :data:`KIND_MEASUREMENT_MISSING`, in this
order); the two results' ``shape`` (:data:`KIND_SHAPES_DIFFER`); the domain
of :func:`hilclaw.harness.measurement.ratio_interval`
(:data:`KIND_SAMPLES_OUT_OF_DOMAIN`). An admitted timing result has
``outcome`` ``"converged"``, ``"not_converged"`` or ``"broken"`` and, for
the first two, ``intervals_ns``, a list of at least ``N_MIN`` ``int`` values
of at least 1, and ``shape``, an object of exactly ``m``, ``k`` and ``n``,
each an ``int`` of at least 1; its other members are not looked at.

The measurement of one attempt at the point: M is its end lines at the
``step``, every ``execution`` together, whose ``result`` has ``outcome``
``"converged"`` or ``"not_converged"``; U is its end lines that hold a
``failure`` together with its identities that have a start line and no end
line. It has a measurement exactly when M holds one line and U is empty:
that result's ``intervals_ns``. Otherwise ``measurement_several`` when M
holds more than one line, else ``measurement_unknown`` when U is not empty,
else ``measurement_missing``. A ``"broken"`` result neither enters nor
refuses; a ``"not_converged"`` one enters like a ``"converged"`` one.

The rule (ADR-0140 decision 4, after ADR-0007 decision 7): with x the
samples of ``against`` and y those of ``measured``, the interval is
``ratio_interval(x, y)``; ``d`` is ``"lower"`` when it lies wholly and
strictly below ``1 / (1 + DELTA)``, ``"higher"`` when it lies wholly and
strictly above ``1 + DELTA``, and ``"not_different"`` otherwise. The pair is
never exchanged and no parameter is added.

Choices left to the code slice (ADR-0140 decision 3), made here:

* The read of the log is :func:`hilclaw.checks_tool.log_lines`; the work
  after it is public, as :func:`compare`, so that ``verdicts.write``
  (ADR-0140 decision 5) gives the same ``difference`` and kinds for the same
  lines.
* The three ``outcome`` values are written here as ADR-0063 decision 2
  names them: :mod:`hilclaw.run_result` holds the same values and is imported
  by no other module of the package.
* A number beyond the float range in a stored result is read as an infinity,
  a ``float``: in ``intervals_ns`` or ``shape`` it is no ``int``, so
  ``timing_result_invalid``; in any other member it is not looked at and
  changes nothing, since the result returns no stored member. An ``int`` too
  large for the rule's float range in ``intervals_ns`` is admitted and then
  ``samples_out_of_domain``.

The only file read is the run's ``events.ndjson``; no ``STATE.json`` or
instance record is read, so a ``run_id`` that names no run, or a missing log,
holds no line and is answered ``measurement_missing`` for ``measured``.
Nothing checks that the run is one of ADR-0120 decision 1, that the two
rounds stand in any order or that either attempt passed a check; neither
``sample_form`` nor ``n_max`` is compared and ``ceiling`` is not read.
Nothing is created and nothing is kept between calls. The six kinds below are
names of the tool layer and not reserved.
"""

import reprlib

from hilclaw import (
    check_identity,
    checks_tool,
    data_root_source,
    journal,
    keys,
    layout,
    run_files,
    run_identity,
    tools,
)
from hilclaw.harness import measurement

#: An end line of a named attempt at the ``step`` holds a ``result`` that is no admitted timing result.
KIND_TIMING_RESULT_INVALID = "timing_result_invalid"
#: A side has more than one measurement at the point.
KIND_MEASUREMENT_SEVERAL = "measurement_several"
#: A side has a ``failure`` end line or an open identity at the point, so its measurement is not known.
KIND_MEASUREMENT_UNKNOWN = "measurement_unknown"
#: A side has no measurement at the point.
KIND_MEASUREMENT_MISSING = "measurement_missing"
#: The two measurements are of different shapes.
KIND_SHAPES_DIFFER = "shapes_differ"
#: The rule's functions refuse the two sample sets.
KIND_SAMPLES_OUT_OF_DOMAIN = "samples_out_of_domain"
#: The one admitted metric (ADR-0059 decision 3).
METRIC = "latency_minimisation"
#: The ``step`` read at each ``point`` (ADR-0062 decision 3).
STEP_OF = {
    check_identity.SIM: run_identity.STEP_SIM_RUN,
    check_identity.BOARD: run_identity.STEP_BOARD_RUN,
}

NAME = "timings.compare"

_DESCRIPTION = (
    "Compare the timing measurement of the attempt measured against that of "
    "the attempt against at one point of the run run_id, by the package's "
    "difference rule, from the sim.run or board.run lines of the run's "
    "events.ndjson. The data root is never part of the request; the tool "
    "knows it. All members are required: metric is latency_minimisation; "
    "point is sim or board; measured and against are each "
    '{"round": r, "candidate": c, "attempt": a} with round from 0 and '
    "candidate and attempt from 1, and the two differ. Each side must have "
    "exactly one converged or not_converged timing result at the point and "
    "no failed or unfinished run there; broken results are ignored. The "
    'result is {"difference": d, "measured": {"execution": n, "outcome": o}, '
    '"against": {"execution": n, "outcome": o}}, where d is "lower" when '
    "the interval of the ratio of the times of measured to those of against "
    'lies wholly below 1 / (1 + delta), "higher" when it lies wholly above '
    '1 + delta, and "not_different" otherwise; execution and outcome name '
    "the result that entered. Copy d into the comparison entry with the same "
    "metric, point, measured and against. It fails with invalid_request for "
    "a request with another member, without one or with a value outside its "
    "form; no_data_root when the data root cannot be obtained; "
    "run_file_missing when the data root is gone; run_file_unreadable when "
    "the log cannot be read; run_file_invalid when the log is no regular file "
    "or holds a damaged line or step line, anywhere; run_file_unsupported "
    "when a line has another schema_version; timing_result_invalid when a "
    "timing result of either attempt at the point is malformed; "
    "measurement_several when a side has more than one such result; "
    "measurement_unknown when a side has a failed or unfinished run; "
    "measurement_missing when a side has no result, also when the run has no "
    "log or does not exist; shapes_differ when the two results are of "
    "different shapes; and samples_out_of_domain when the samples are too "
    "large to compare."
)
_MEMBERS = ("run_id", "metric", "point", "measured", "against")
_SIDES = ("measured", "against")
_LEAST = {"round": 0, "candidate": 1, "attempt": 1}
_BROKEN = "broken"
_ENTERING = ("converged", "not_converged")
_OUTCOMES = (*_ENTERING, _BROKEN)
_SHAPE = ("m", "k", "n")
_STEP_KINDS = (journal.STEP_STARTED, journal.STEP_ENDED)


def definition(source):
    """Return the tool definition of ``timings.compare``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked at each call,
    after the request was checked, and not here. Raises :class:`TypeError`
    when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request outside the forms of the module
    docstring, ``no_data_root`` as :func:`hilclaw.data_root_source.obtain`
    does, the kinds of :func:`hilclaw.checks_tool.log_lines` for the read of
    the log, and the kinds of :func:`compare` after it.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def compare_timings(request):
        run_id, metric, point, measured, against = _checked(request)
        lines = checks_tool.log_lines(data_root_source.obtain(source), run_id)
        return compare(run_id, lines, metric, point, measured, against)

    return tools.ToolDefinition(NAME, compare_timings, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "metric": {"type": "string", "enum": [METRIC]},
            "point": {"type": "string", "enum": list(STEP_OF)},
            "measured": {"type": "object"},
            "against": {"type": "object"},
        },
        "required": list(_MEMBERS),
        "additionalProperties": False,
    }


def _invalid(message):
    return tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def _shown(value):
    try:
        return f"{type(value).__name__} {reprlib.repr(value)}"
    except ValueError:
        return f"{type(value).__name__} too long to show"


def _ref(name, value):
    if type(value) is not dict or set(value) != set(_LEAST):
        raise _invalid(
            f"{name}: must be an object of exactly round, candidate and attempt, "
            f"got {_shown(value)}"
        )
    for member, least in _LEAST.items():
        number = value[member]
        if type(number) is not int or not least <= number <= keys.MAX_INTEGER:
            raise _invalid(
                f"{name}.{member}: must be an int from {least} to "
                f"{keys.MAX_INTEGER}, got {_shown(number)}"
            )
    return value


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
    metric, point = request["metric"], request["point"]
    if type(metric) is not str or metric != METRIC:
        raise _invalid(f'metric: must be "{METRIC}", got {_shown(metric)}')
    if type(point) is not str or point not in STEP_OF:
        raise _invalid(f'point: must be "sim" or "board", got {_shown(point)}')
    measured, against = (_ref(name, request[name]) for name in _SIDES)
    if measured == against:
        raise _invalid("measured and against must name two different attempts")
    return run_id, metric, point, measured, against


def _problem(result):
    if "outcome" not in result:
        return ": lacks the member outcome"
    outcome = result["outcome"]
    if type(outcome) is not str or outcome not in _OUTCOMES:
        return f".outcome: must be one of {', '.join(_OUTCOMES)}, got {_shown(outcome)}"
    if outcome == _BROKEN:
        return None
    for name in ("intervals_ns", "shape"):
        if name not in result:
            return f": lacks the member {name}"
    samples = result["intervals_ns"]
    if (
        type(samples) is not list
        or len(samples) < measurement.N_MIN
        or any(type(s) is not int or s < 1 for s in samples)
    ):
        return (
            f".intervals_ns: must be a list of at least {measurement.N_MIN} ints "
            "of at least 1"
        )
    shape = result["shape"]
    if (
        type(shape) is not dict
        or set(shape) != set(_SHAPE)
        or any(type(shape[d]) is not int or shape[d] < 1 for d in _SHAPE)
    ):
        return ".shape: must be an object of exactly m, k and n, each an int from 1"
    return None


def _numbers(ref):
    return ref["round"], ref["candidate"], ref["attempt"]


def _measurement(file, side, ref, step, found):
    entering, unknown = found
    named = "round {}, candidate {}, attempt {}".format(*_numbers(ref))
    where = f"{file}: {side} ({named}) at {step}"
    if len(entering) > 1:
        executions = ", ".join(str(execution) for execution, _ in entering)
        raise tools.ToolFailure(
            KIND_MEASUREMENT_SEVERAL,
            f"{where}: has {len(entering)} measurements (executions {executions})",
        )
    if unknown:
        raise tools.ToolFailure(
            KIND_MEASUREMENT_UNKNOWN,
            f"{where}: has a failed or unfinished run (execution {min(unknown)})",
        )
    if not entering:
        raise tools.ToolFailure(
            KIND_MEASUREMENT_MISSING, f"{where}: has no measurement"
        )
    return entering[0]


def compare(run_id, lines, metric, point, measured, against):
    """Return the result of ``timings.compare`` for the entry ``metric``, ``point``, ``measured``, ``against`` over ``lines`` (ADR-0140 decisions 3 and 4).

    ``lines`` are the events of the run ``run_id`` as
    :func:`hilclaw.checks_tool.log_lines` returns them. ``metric`` and
    ``point`` are as the request names them, and ``measured`` and ``against``
    are each a mapping of ``round``, ``candidate`` and ``attempt`` in the
    request's forms, naming two different attempts. Nothing of them is
    checked but that ``metric`` is :data:`METRIC` and ``point`` a key of
    :data:`STEP_OF`, a :class:`ValueError` otherwise. Shared by
    ``timings.compare`` and ``verdicts.write`` (ADR-0140 decision 5).

    Returns ``{"difference": d, "measured": {"execution": n, "outcome": o},
    "against": {"execution": n, "outcome": o}}``, a new ``dict``. Raises
    :class:`hilclaw.tools.ToolFailure` by the checks after the read of the
    module docstring, in their order: ``run_file_invalid`` and
    :data:`KIND_TIMING_RESULT_INVALID` for the first step line that fails, in
    line order, each message starting with ``runs/<run_id>/events.ndjson:
    line <n>``; then :data:`KIND_MEASUREMENT_SEVERAL`,
    :data:`KIND_MEASUREMENT_UNKNOWN` and :data:`KIND_MEASUREMENT_MISSING` for
    ``measured`` and then for ``against``, the message naming the side;
    :data:`KIND_SHAPES_DIFFER`; :data:`KIND_SAMPLES_OUT_OF_DOMAIN`.
    """
    if metric != METRIC or point not in STEP_OF:
        raise ValueError("metric or point is not one the request admits")
    step = STEP_OF[point]
    file = run_files.relative(run_id, checks_tool.LOG)
    sides = {_numbers(measured): "measured", _numbers(against): "against"}
    found = {side: ([], set()) for side in _SIDES}
    started, ended = {}, set()
    for number, event in enumerate(lines, 1):
        if event["kind"] not in _STEP_KINDS:
            continue
        try:
            identity = journal.identity_of(event)
        except journal.JournalError as e:
            message = f"{file}: line {number}: {e}"
            raise tools.ToolFailure(tools.KIND_RUN_FILE_INVALID, message) from e
        side = sides.get(tuple(identity[2:5]))
        if identity.step != step or side is None:
            continue
        if event["kind"] == journal.STEP_STARTED:
            started.setdefault(identity, side)
            continue
        ended.add(identity)
        data = event["data"]
        entering, unknown = found[side]
        if "failure" in data:
            unknown.add(identity.execution)
            continue
        problem = _problem(data["result"])
        if problem is not None:
            raise tools.ToolFailure(
                KIND_TIMING_RESULT_INVALID,
                f"{file}: line {number}: data.result{problem}",
            )
        if data["result"]["outcome"] in _ENTERING:
            entering.append((identity.execution, data["result"]))
    for identity, side in started.items():
        if identity not in ended:
            found[side][1].add(identity.execution)
    chosen = {
        side: _measurement(file, side, ref, step, found[side])
        for side, ref in zip(_SIDES, (measured, against))
    }
    (_, y), (_, x) = chosen["measured"], chosen["against"]
    if y["shape"] != x["shape"]:
        raise tools.ToolFailure(
            KIND_SHAPES_DIFFER,
            f"{file}: measured has the shape {y['shape']}, against {x['shape']}",
        )
    try:
        low, high = measurement.ratio_interval(x["intervals_ns"], y["intervals_ns"])
    except measurement.InvalidSamplesError as e:
        raise tools.ToolFailure(
            KIND_SAMPLES_OUT_OF_DOMAIN, f"{file}: the samples cannot be compared: {e}"
        ) from e
    if high < 1 / (1 + measurement.DELTA):
        difference = "lower"
    elif low > 1 + measurement.DELTA:
        difference = "higher"
    else:
        difference = "not_different"
    result = {"difference": difference}
    for side in _SIDES:
        execution, chosen_result = chosen[side]
        result[side] = {"execution": execution, "outcome": chosen_result["outcome"]}
    return result
