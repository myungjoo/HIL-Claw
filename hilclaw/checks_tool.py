"""The tool ``checks.read``, which reads the ``correctness.check`` lines of a run for the evaluator (ADR-0131 decision 3).

For the runs of ADR-0120 decision 1 the ``evaluator`` sub-agent gets the
results of an attempt's checks, and the standing of ADR-0110 decision 3,
through this tool (ADR-0131 decisions 2, 3 and 7). It is a tool of the
registry beside the FR-10 tools, not an FR-10 tool: it is not journaled,
appends no line to ``events.ndjson`` and selects no backend.

The request has ``run_id``, ``round``, ``candidate`` and ``point``, required,
and ``attempt``, optional, and no other member. ``round`` is an ``int`` from
0 to :data:`hilclaw.keys.MAX_INTEGER`, ``candidate`` and ``attempt`` are
``int`` values from 1, a ``bool`` being none; ``point`` is exactly
:data:`hilclaw.check_identity.SIM` or :data:`~hilclaw.check_identity.BOARD`,
compared as it is, and names the point whose lines are read: the lines of
both its ``step`` values in :data:`hilclaw.check_standing.STEPS_OF`, that of
ADR-0040 decision 3 and the bf16 one of ADR-0177 decision 3 (ADR-0178
decision 1). The data root comes from the data-root source, asked at each
call after the request was checked, and never from the request (ADR-0015
decision 3).

The result is ``{"attempts": [...]}``, one entry per attempt in ascending
``attempt``, each exactly ``attempt``, ``standing`` and ``checks``. With
``attempt`` in the request there is exactly that entry, also when the log
holds no line of it; without it there is one entry per attempt of the
candidate for which the log holds a line of the point, possibly none.
``checks`` holds, in the order of the lines, one element ``{"execution": n,
"state": "ended", "result" | "failure": ...}`` per end line of the attempt
at the point, the ``result`` or ``failure`` as the line holds it, and one
element ``{"execution": n, "state": "open"}`` per identity with a start line
and no end line, at its first start line. ``standing`` is what
:func:`hilclaw.check_standing.point_standing` computes over the same lines,
as ``"verified"``, ``"not_verified"`` or ``"undetermined"``: names of the
tool layer, stored nowhere.

The checks, in this order, each with its kind (ADR-0131 decision 3, table):
the request (``invalid_request``); the data root (``no_data_root``); the read
of ``runs/<run_id>/events.ndjson`` from its first line by
:func:`hilclaw.events.read`, which parses every complete line in line order
before any step line is looked at (a data root no longer an existing directory
``run_file_missing``, another failing read ``run_file_unreadable``, a path
that is no regular file or a damaged complete line ``run_file_invalid``, a
complete line of another version ``run_file_unsupported``); then the step
lines in line order, the first that fails deciding: a step line about any
attempt that :func:`hilclaw.journal.identity_of` refuses (``run_file_invalid``)
and an end line in the request's scope whose ``result`` has no ``outcome`` of
``"pass"``, ``"fail"`` or ``"broken"`` (:data:`KIND_CHECK_RESULT_INVALID`).
The scope is the named attempt at the point, or every attempt of the
candidate at the point when ``attempt`` is left out. A missing log, or a
missing run directory below an existing data root, holds no line and is no
failure; a torn tail is no line.

Choices left to the code slice (ADR-0131 decision 3), made here:

* The scoped pass over the step lines is this module's own, so that the two
  kinds of its last check are told apart by the check that refuses, and in
  line order across attempts; :func:`hilclaw.check_standing.point_standing`
  is then asked for the standing of each attempt, over lines it no longer
  refuses.
* The read of the log and the scoped pass are public, as :func:`log_lines`,
  :func:`checks_of` and :func:`checks_in_order`, so that ``verdicts.write``
  (ADR-0131 decision 5) raises the same kinds with the same messages for the
  same log.
* A number beyond the float range in a stored ``result`` or ``failure`` is
  read as an infinity, which no result can hold: a call whose result holds
  one fails with ``bad_result``, as ``state.read`` and ``hypotheses.read``
  do. Such a number on a line outside the result does nothing.

The only file read is the run's ``events.ndjson``; no ``STATE.json`` is read,
so a ``run_id`` that names no run is answered like an empty log, and nothing
checks that the run is one of ADR-0120 decision 1. Nothing is created and
nothing is kept between calls. :data:`KIND_CHECK_RESULT_INVALID` is a name of
the tool layer and not reserved.
"""

import reprlib

from hilclaw import (
    check_identity,
    check_result,
    check_standing,
    data_root_source,
    events,
    journal,
    keys,
    layout,
    run_files,
    tools,
)

#: An end line in the request's scope holds a ``result`` without an admitted ``outcome``.
KIND_CHECK_RESULT_INVALID = "check_result_invalid"
#: The name of the run's log, the frame file every read of this module reads.
LOG = "events.ndjson"

NAME = "checks.read"

_DESCRIPTION = (
    "Read every correctness.check of an attempt, or of each attempt of a "
    "candidate, at one point of the run run_id, from the run's events.ndjson, "
    "with the standing those checks give. The data root is never part of the "
    "request; the tool knows it. round (from 0), candidate and point (sim or "
    "board) are required; attempt is optional: with it, the result holds "
    "exactly that attempt, also when nothing was checked; without it, every "
    "attempt of the candidate checked at that point, in ascending order, "
    'possibly none. The result is {"attempts": [{"attempt": n, "standing": '
    's, "checks": [...]}]}, where checks lists, in the order of the log, '
    '{"execution": n, "state": "ended", "result": the result as stored} or '
    '{"execution": n, "state": "ended", "failure": the failure as stored} '
    'for each ended check and {"execution": n, "state": "open"} for each check '
    'started and never ended, and standing is "verified", "not_verified" or '
    '"undetermined". It fails with invalid_request for a request with another '
    "member, without a required one or with a value outside its form; "
    "no_data_root when the data root cannot be obtained; run_file_missing when "
    "the data root is gone; run_file_unreadable when the log cannot be read; "
    "run_file_invalid when the log is no regular file or holds a damaged line "
    "or step line, anywhere; run_file_unsupported when a line has another "
    "schema_version; check_result_invalid when a result of the attempts read "
    "has no outcome pass, fail or broken; and bad_result when a returned "
    "result holds a number too large to be returned. A run without a log, or "
    "no run, holds no check."
)
_MEMBERS = ("run_id", "round", "candidate", "attempt", "point")
_OPTIONAL = ("attempt",)
_LEAST = {"round": 0, "candidate": 1, "attempt": 1}
_POINTS = (check_identity.SIM, check_identity.BOARD)
_OUTCOMES = (check_result.PASS, check_result.FAIL, check_result.BROKEN)
_STANDINGS = {
    check_standing.Standing.VERIFIED: "verified",
    check_standing.Standing.NOT_VERIFIED: "not_verified",
    check_standing.Standing.UNDETERMINED: "undetermined",
}
_LOG_KINDS = {
    events.CorruptEventsError: tools.KIND_RUN_FILE_INVALID,
    events.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
}
_STEP_KINDS = (journal.STEP_STARTED, journal.STEP_ENDED)


def definition(source):
    """Return the tool definition of ``checks.read``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked at each call,
    after the request was checked, and not here. Raises :class:`TypeError`
    when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request with a member other than ``run_id``,
    ``round``, ``candidate``, ``attempt`` and ``point``, without one of them
    but ``attempt``, or with a value outside its form (see the module
    docstring); ``no_data_root`` as :func:`hilclaw.data_root_source.obtain`
    does; the four ``run_file_*`` kinds for the read of the log and its step
    lines; and :data:`KIND_CHECK_RESULT_INVALID` for an end line in the
    request's scope whose ``result`` has no admitted ``outcome``. Each message
    of the last two checks starts with ``runs/<run_id>/events.ndjson``.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def read_checks(request):
        return _read(source, request)

    return tools.ToolDefinition(NAME, read_checks, _DESCRIPTION, _input_schema())


def _input_schema():
    number = {"type": "integer", "maximum": keys.MAX_INTEGER}
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            **{name: number | {"minimum": least} for name, least in _LEAST.items()},
            "point": {"type": "string", "enum": list(_POINTS)},
        },
        "required": [name for name in _MEMBERS if name not in _OPTIONAL],
        "additionalProperties": False,
    }


def _invalid(message):
    return tools.ToolFailure(tools.KIND_INVALID_REQUEST, message)


def _shown(value):
    try:
        return f"{type(value).__name__} {reprlib.repr(value)}"
    except ValueError:
        return f"{type(value).__name__} too long to show"


def _checked(request):
    others = sorted(name for name in request if name not in _MEMBERS)
    if others:
        raise _invalid(
            f"the request takes the members {', '.join(_MEMBERS)} only "
            f"(attempt optional), not {', '.join(map(repr, others))}"
        )
    for name in _MEMBERS:
        if name not in request and name not in _OPTIONAL:
            raise _invalid(f"the request lacks the member {name}")
    try:
        run_id = layout.check_run_id(request["run_id"])
    except layout.InvalidPathValueError as e:
        raise _invalid(f"the request's {e}") from e
    for name, least in _LEAST.items():
        value = request.get(name, least)
        if type(value) is not int or not least <= value <= keys.MAX_INTEGER:
            raise _invalid(
                f"{name}: must be an int from {least} to {keys.MAX_INTEGER}, "
                f"got {_shown(value)}"
            )
    point = request["point"]
    if type(point) is not str or point not in _POINTS:
        raise _invalid(f'point: must be "{_POINTS[0]}" or "{_POINTS[1]}"')
    numbers = (request["round"], request["candidate"], request.get("attempt"))
    return run_id, point, numbers


def log_lines(data_root, run_id):
    """Return the events of ``runs/<run_id>/events.ndjson`` from its first line, read as ADR-0131 decision 3 reads them.

    The read of :func:`hilclaw.events.read`, every complete line parsed in
    line order and a torn tail no line, with its failures answered by the
    kinds of ADR-0019 for the log, the situations of the file first:
    ``run_file_missing`` for a data root no longer an existing directory,
    ``run_file_unreadable`` for another failing read, ``run_file_invalid`` for
    a path that is no regular file or a damaged complete line and
    ``run_file_unsupported`` for a complete line of another version, each a
    :class:`hilclaw.tools.ToolFailure` whose message starts with the relative
    path of the log. A missing log, or a missing run directory below an
    existing data root, holds no line: the result is then empty. Shared by
    ``checks.read`` and ``verdicts.write`` (ADR-0131 decisions 3 and 5).
    """
    with run_files.reading(data_root, run_id, LOG, _LOG_KINDS):
        try:
            return events.read(data_root, run_id).events
        except run_files.NOT_THERE:
            if not run_files.data_root_is_there(data_root):
                raise
            return []


def _outcome(file, number, result):
    if "outcome" not in result:
        problem = "data.result: lacks the member outcome"
    elif type(result["outcome"]) is not str or result["outcome"] not in _OUTCOMES:
        rule = f"must be one of {', '.join(_OUTCOMES)}"
        problem = f"data.result.outcome: {rule}, got {_shown(result['outcome'])}"
    else:
        return
    raise tools.ToolFailure(
        KIND_CHECK_RESULT_INVALID, f"{file}: line {number}: {problem}"
    )


def checks_of(run_id, lines, inside):
    """Return the checks of the attempts and points that ``inside`` admits, by the step-line pass of ADR-0131 decision 3.

    ``lines`` are the events of the run ``run_id`` as :func:`log_lines`
    returns them. ``inside`` is called with the tuple ``(step, round,
    candidate, attempt)`` of a step line whose envelope names an attempt, and
    admits it when it returns true. The step lines are looked at in line
    order, the first that fails deciding: a step line about any attempt that
    :func:`hilclaw.journal.identity_of` refuses is ``run_file_invalid``, and an
    admitted end line whose ``result`` has no ``outcome`` of ``"pass"``,
    ``"fail"`` or ``"broken"`` is :data:`KIND_CHECK_RESULT_INVALID`, each a
    :class:`hilclaw.tools.ToolFailure` whose message starts with
    ``runs/<run_id>/events.ndjson: line <n>``. An end line that ``inside``
    does not admit is not looked at further.

    The result maps each admitted tuple that has a line to its checks, in the
    order of the lines: ``{"execution": n, "state": "ended", "result" |
    "failure": ...}`` per end line, the member as the line holds it, and
    ``{"execution": n, "state": "open"}`` per identity with a start line and
    no end line, at its first start line. Shared by ``checks.read`` and
    ``verdicts.write`` (ADR-0131 decisions 3 and 5).
    """
    found = {}
    for key, element in checks_in_order(run_id, lines, inside):
        found.setdefault(key, []).append(element)
    return found


def checks_in_order(run_id, lines, inside):
    """Return the checks that :func:`checks_of` returns as one list of ``(key, element)`` pairs in the order of the lines.

    The same pass with the same failures as :func:`checks_of`; each element
    is paired with the tuple ``(step, round, candidate, attempt)`` it is
    grouped under there, an open element at its first start line and an
    ended one at its end line. A reader that takes the lines of both
    ``step`` values of a point (ADR-0178 decision 1) keeps their order from
    this list.
    """
    file = run_files.relative(run_id, LOG)
    held, opened, ended = [], set(), set()
    for number, event in enumerate(lines, 1):
        if event["kind"] not in _STEP_KINDS:
            continue
        try:
            identity = journal.identity_of(event)
        except journal.JournalError as e:
            message = f"{file}: line {number}: {e}"
            raise tools.ToolFailure(tools.KIND_RUN_FILE_INVALID, message) from e
        key = (identity.step, *identity[2:5])
        if identity.attempt is None or not inside(key):
            continue
        execution = {"execution": identity.execution}
        if event["kind"] == journal.STEP_STARTED:
            if identity not in opened:
                opened.add(identity)
                held.append((key, identity, execution | {"state": "open"}))
            continue
        data = event["data"]
        if "result" in data:
            _outcome(file, number, data["result"])
        member = "result" if "result" in data else "failure"
        ended.add(identity)
        element = execution | {"state": "ended", member: data[member]}
        held.append((key, None, element))
    return [(key, element) for key, identity, element in held if identity not in ended]


def _read(source, request):
    run_id, point, numbers = _checked(request)
    data_root = data_root_source.obtain(source)
    lines = log_lines(data_root, run_id)
    round, candidate, attempt = numbers
    steps = check_standing.STEPS_OF[point]

    def inside(key):
        return (
            key[0] in steps
            and key[1:3] == (round, candidate)
            and attempt in (None, key[3])
        )

    found = {}
    for key, element in checks_in_order(run_id, lines, inside):
        found.setdefault(key[3], []).append(element)
    entries = []
    for n in sorted(found) if attempt is None else [attempt]:
        standing = check_standing.point_standing(lines, point, round, candidate, n)
        entries.append(
            {"attempt": n, "standing": _STANDINGS[standing], "checks": found.get(n, [])}
        )
    return {"attempts": entries}
