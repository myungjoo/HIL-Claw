"""The tool ``round.end``, which makes the write that ends a round for the Round-Manager (ADR-0135 decision 2).

For the runs of ADR-0120 decision 1 the Round-Manager makes the write that
ends its round only through this tool: the tool folds the stored spend view
over the tail of the log, compares the next round with the run's
``round_budget`` and replaces ``STATE.json`` itself, so the model supplies no
total, position, open step, next round or run status (ADR-0135 decisions 2
to 4). It is a tool of the registry beside the FR-10 tools, not an FR-10
tool: it is not journaled, appends no line to ``events.ndjson``, selects no
backend and keeps nothing between calls (ADR-0135 decision 2).

The request is exactly ``{"run_id": ..., "round": ...}``: ``round`` is the
round being ended, an ``int`` from 0 to :data:`hilclaw.keys.MAX_INTEGER`
minus 1, a ``bool`` being none, so that the next round is an integer of
ADR-0001. The data root comes from the data-root source, asked at each call
after the request was checked, and never from the request (ADR-0015
decision 3). The result is ``{"round": k + 1, "over": bool,
"reported_lines": [...]}``: the round written, whether ``run_status``
``"over"`` was written, and the line numbers of the
:class:`hilclaw.journal.Report` of the fold, ascending and possibly none.
:func:`hilclaw.journal.fold` numbers a line from the stored position, so
:attr:`hilclaw.journal.Report.line` already counts from the first line of the
file, from 1.

The checks, in this order, each with its kind; the first that fails decides
and nothing is written before 6 (ADR-0135 decision 2, table):

1. the request (``invalid_request``);
2. the data root (``no_data_root``);
3. the run's ``STATE.json`` read once by :func:`hilclaw.run_file_tools.read`
   (the four ``run_file_*`` kinds of ADR-0019, as ``state.read`` answers
   them); its ``round`` equal to the request's
   (:data:`KIND_ROUND_NOT_CURRENT`); then no top-level member beside
   ``schema_version``, ``round`` and ``budget_spent``
   (:data:`KIND_STATE_MEMBER_EXTRA`), ``run_status`` of any value included;
4. the tail of ``events.ndjson`` after the position of that same
   ``STATE.json``, read by :func:`hilclaw.events.read` and folded by
   :func:`hilclaw.journal.fold` into the view of 3, as ADR-0019 decision 3's
   table maps the log: a damaged complete line, a position beyond the log and
   a step line that breaks ADR-0011 ``run_file_invalid``, a line of another
   version ``run_file_unsupported``, an :class:`OSError` as
   :func:`hilclaw.run_files.read_failure` answers it;
5. the run's ``instance.json`` read once the same way (the same four kinds),
   for its ``round_budget``, ``None`` when it states none;
6. :func:`hilclaw.run_state_file.replace` with the round *k* + 1, the folded
   view and ``{"run_status": "over"}`` when a ``round_budget`` is stated and
   *k* + 1 is at least that budget, else nothing more: any :class:`OSError`
   is :data:`KIND_STATE_NOT_WRITTEN` and ``STATE.json`` holds what it held.

A data root gone since 2 is ``run_file_missing`` at 3, 4 and 5 (ADR-0019
decision 4) and :data:`KIND_STATE_NOT_WRITTEN` at 6. At 4 that holds for the
stored position 0 too: :func:`hilclaw.events.read` asks for the data root
before the log, so a gone root is never read as an empty tail. Each message
starts with the path of the file concerned relative to the data root. An
:class:`OSError` is reported by its class and the text of the system,
without the absolute path, and says so when the data root is gone.

What is written is exactly ``schema_version`` 1, ``round`` *k* + 1,
``budget_spent`` the folded view and, under the condition of 6, ``run_status``
``"over"`` (ADR-0135 decision 4). The position written is the stored one
plus the number of complete lines after it; a torn tail is not counted, not
folded and not removed, so the log's bytes are unchanged. Open steps are
written as the fold lists them. A total above :data:`hilclaw.keys.MAX_INTEGER`
needs no conversion: :func:`hilclaw.run_state.dump` writes it exactly and
:func:`hilclaw.run_state.parse` reads it back equal. A
:class:`hilclaw.run_state.InvalidStateError` of that dump at 6 (a total too
long for this interpreter to write, a position above
:data:`hilclaw.keys.MAX_INTEGER`) has no kind in ADR-0135: it passes out of
the tool function and :func:`hilclaw.tools.call` answers it with
``tool_crashed``, nothing being written.

The only files read are ``STATE.json``, ``events.ndjson`` and
``instance.json``; the only write is that of 6. No line before the stored
position is interpreted, no fold from the first line is made and none is
compared, and no commit, case or removal of a torn tail is made. The kind
``state_member_extra`` is a name of the tool layer and is not reserved; the
four ``run_file_*`` kinds are the reserved ones of ADR-0019, widened to these
reads by ADR-0135 decision 2.
"""

from hilclaw import (
    case_tool,
    data_root_source,
    events,
    journal,
    keys,
    layout,
    run_file_tools,
    run_files,
    run_state_file,
    tools,
)

#: The request's round is not the round ``STATE.json`` names as in progress; nothing was written.
KIND_ROUND_NOT_CURRENT = case_tool.KIND_ROUND_NOT_CURRENT
#: ``STATE.json`` holds a top-level member beside the three of ADR-0012, ``run_status`` included; nothing was written.
KIND_STATE_MEMBER_EXTRA = "state_member_extra"
#: A step of the replacement failed in the file system; ``STATE.json`` holds what it held.
KIND_STATE_NOT_WRITTEN = run_file_tools.KIND_STATE_NOT_WRITTEN

NAME = "round.end"

_DESCRIPTION = (
    "End round round of the run run_id, the round in progress: fold the "
    "stored spend view over the lines the log gained since it was stored, "
    "compare the next round with the run's round_budget and replace "
    "STATE.json with the next round, that view and, when the run is over, "
    'run_status "over". Call it once per round as the round\'s last write, '
    "then run.commit; you supply no number but the round. The result is "
    '{"round": the round written, "over": true or false, "reported_lines": '
    "[line numbers]}: over is true when the run is over; reported_lines are "
    "log lines the fold counted and reports, so when it is not empty report "
    "it in one line and go on. The data root is never part of the request; "
    "the tool knows it. Nothing is written when it fails; then report the "
    "kind in one line and end the session without another write, neither "
    "run.commit nor STATE.json in another way. It fails, checked in this "
    "order, with invalid_request for a request that is not exactly run_id "
    "and round; no_data_root when the data root cannot be obtained; "
    "run_file_missing, run_file_invalid, run_file_unsupported or "
    "run_file_unreadable when the run's STATE.json is not there, is invalid "
    "or no regular file, has another schema_version or cannot be read; "
    "round_not_current when round is not the round STATE.json names; "
    "state_member_extra when STATE.json holds a member beside "
    "schema_version, round and budget_spent, run_status included; the same "
    "four run_file kinds for the run's events.ndjson, run_file_invalid "
    "covering a damaged line, a step line breaking the journal rules and a "
    "stored position beyond the log; the same four for the run's "
    "instance.json; and state_not_written when a step of the write fails."
)
_MEMBERS = ("run_id", "round")
_LOG = "events.ndjson"
_LOG_KINDS = {
    events.CorruptEventsError: tools.KIND_RUN_FILE_INVALID,
    events.UnsupportedVersionError: tools.KIND_RUN_FILE_UNSUPPORTED,
}
_LAST = keys.MAX_INTEGER - 1


def definition(source):
    """Return the tool definition of ``round.end``, bound to the data-root source ``source``.

    The result is one :class:`hilclaw.tools.ToolDefinition`. ``source`` is
    the data-root source of ADR-0015 decision 3; it is asked once at each
    call, after the request was checked, and not here. Raises
    :class:`TypeError` when it is not callable.

    The tool function raises :class:`hilclaw.tools.ToolFailure` of kind
    ``invalid_request`` for a request that is not exactly ``run_id`` and
    ``round``, whose ``run_id`` :func:`hilclaw.layout.check_run_id` refuses or
    whose ``round`` is no ``int`` from 0 to :data:`hilclaw.keys.MAX_INTEGER`
    minus 1; ``no_data_root`` as :func:`hilclaw.data_root_source.obtain`
    does; the four ``run_file_*`` kinds for ``STATE.json``, the log and
    ``instance.json``; and the kinds of this module, in the order of the
    module docstring.
    """
    if not callable(source):
        raise TypeError("the data-root source must be callable")

    def end_round(request):
        return _end(source, request)

    return tools.ToolDefinition(NAME, end_round, _DESCRIPTION, _input_schema())


def _input_schema():
    return {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 0, "maximum": _LAST},
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
    round = request["round"]
    if type(round) is not int or not 0 <= round <= _LAST:
        raise _invalid(f"round: must be an int from 0 to {_LAST}, got {round!r}")
    return run_id, round


def _end(source, request):
    run_id, round = _checked(request)
    data_root = data_root_source.obtain(source)
    state, _ = run_file_tools.read(data_root, run_id, "STATE.json")
    file = run_files.relative(run_id, "STATE.json")
    if state.round != round:
        raise tools.ToolFailure(
            KIND_ROUND_NOT_CURRENT,
            f"{file}: names round {state.round} as in progress, not the "
            f"request's round {round}",
        )
    if state.others:
        raise tools.ToolFailure(
            KIND_STATE_MEMBER_EXTRA,
            f"{file}: holds the members {', '.join(map(repr, sorted(state.others)))} "
            "beside schema_version, round and budget_spent, which this write "
            "would have to drop or carry",
        )
    view, reports = _folded(data_root, run_id, state.budget_spent)
    stated, _ = run_file_tools.read(data_root, run_id, "instance.json")
    budget = stated.round_budget
    over = budget is not None and round + 1 >= budget
    others = {"run_status": "over"} if over else {}
    try:
        run_state_file.replace(data_root, run_id, round + 1, view, others)
    except OSError as e:
        raise tools.ToolFailure(
            KIND_STATE_NOT_WRITTEN,
            f"{file}: was not written: {_reported(e, data_root)}",
        ) from e
    return {
        "round": round + 1,
        "over": over,
        "reported_lines": [report.line for report in reports],
    }


def _folded(data_root, run_id, stored):
    with run_files.reading(data_root, run_id, _LOG, _LOG_KINDS):
        log = events.read(data_root, run_id, stored.position)
    try:
        return journal.fold(log.events, stored)
    except ValueError as e:
        raise tools.ToolFailure(
            tools.KIND_RUN_FILE_INVALID, f"{run_files.relative(run_id, _LOG)}: {e}"
        ) from e


def _reported(error, data_root):
    reported = ": ".join(filter(None, (type(error).__name__, error.strerror)))
    if isinstance(error, run_files.NOT_THERE) and not run_files.data_root_is_there(
        data_root
    ):
        reported += ": the data root is not an existing directory"
    return reported
