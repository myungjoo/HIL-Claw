import copy
import json
from types import MappingProxyType

import pytest

from hilclaw import events, journal, keys
from hilclaw.journal import (
    EMPTY,
    STEP_ENDED,
    STEP_STARTED,
    Identity,
    JournalError,
    Problem,
    Report,
    SpendView,
    State,
    StepState,
    check_step,
    fold,
    identity_of,
    step_identity,
    step_state,
)

# Synthetic values only: no step name, axis or result member of a real run.
TIME = "2026-01-01T00:00:00Z"
STEP = "example_step"
AXIS = "example_axis"
OTHER_AXIS = "other_example_axis"
RESULT = {"example_member": 1}
FAILURE = {"kind": "example_failure", "message": "no outcome"}
TARGET = {"round": 3, "candidate": 2, "attempt": 1}

# The Example of ADR-0011, as written in the record.
EXAMPLE = [
    json.loads(text)
    for text in (
        (
            '{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "step_started",'
            ' "round": 3, "candidate": 2, "attempt": 1,'
            ' "data": {"step": "example_step", "execution": 1}}'
        ),
        (
            '{"schema_version": 1, "time": "2026-01-01T00:04:10Z", "kind": "step_ended",'
            ' "round": 3, "candidate": 2, "attempt": 1,'
            ' "data": {"step": "example_step", "execution": 1,'
            ' "spend": {"example_axis": 7}, "result": {"example_member": 1}}}'
        ),
    )
]
EXAMPLE_ID = Identity(STEP, 1, 3, 2, 1)


def ev(kind, data, **numbers):
    return {"schema_version": 1, "time": TIME, "kind": kind, **numbers, "data": data}


def start(step=STEP, execution=1, **numbers):
    return ev(STEP_STARTED, {"step": step, "execution": execution}, **numbers)


def end(step=STEP, execution=1, spend=None, failure=None, **numbers):
    data = {"step": step, "execution": execution, "spend": spend or {}}
    data |= {"failure": failure} if failure else {"result": dict(RESULT)}
    return ev(STEP_ENDED, data, **numbers)


def other(**numbers):
    return ev("example_kind", {"spend": {AXIS: 100}, "step": 5}, **numbers)


def with_data(kind, **changes):
    line = start() if kind == STEP_STARTED else end(spend={AXIS: 1})
    for name, value in changes.items():
        if value is ...:
            del line["data"][name]
        else:
            line["data"][name] = value
    return line


def view_of(lines, view=EMPTY):
    return fold(lines, view)[0]


def test_example_of_the_record():
    for line in EXAMPLE:
        assert events.validate(line) is None
        assert check_step(line) is None
    assert identity_of(EXAMPLE[0]) == identity_of(EXAMPLE[1]) == EXAMPLE_ID
    view, reports = fold(EXAMPLE)
    assert view == SpendView({AXIS: 7}, 2, frozenset())
    assert reports == ()
    assert step_state(EXAMPLE_ID, EXAMPLE) == StepState(
        State.ENDED, {"example_member": 1}, None, {AXIS: 7}
    )


def test_start_line_alone_is_open():
    view, reports = fold(EXAMPLE[:1])
    assert view == SpendView({}, 1, frozenset({EXAMPLE_ID}))
    assert reports == ()
    assert step_state(EXAMPLE_ID, EXAMPLE[:1]) == StepState(
        State.OPEN, None, None, None
    )


def test_no_line():
    assert fold([]) == (EMPTY, ())
    assert EMPTY == SpendView({}, 0, frozenset())
    assert step_state(EXAMPLE_ID, []) == StepState(State.NO_LINE)
    assert (
        step_state(EXAMPLE_ID, [other(), start(execution=2, **TARGET)]).state
        is State.NO_LINE
    )


def test_identities_of_every_level_are_distinct():
    levels = [{}, {"round": 0}, {"round": 0, "candidate": 1}, TARGET | {"round": 0}]
    lines = [start(**numbers) for numbers in levels]
    lines += [start(step="other_step"), start(execution=2), start(round=1)]
    identities = [identity_of(line) for line in lines]
    assert len(set(identities)) == len(lines)
    assert identities[0] == Identity(STEP, 1, None, None, None)
    assert identities[2] == Identity(STEP, 1, 0, 1, None)
    assert view_of(lines).open_steps == frozenset(identities)
    for identity in identities:
        assert step_state(identity, lines).state is State.OPEN


def test_step_identity_names_the_identity_of_a_line():
    assert step_identity(STEP, 1, **TARGET) == EXAMPLE_ID
    assert step_identity(STEP, 1, 3, 2, 1) == EXAMPLE_ID
    assert step_identity(STEP, 2) == identity_of(start(execution=2))
    assert step_identity(STEP, keys.MAX_INTEGER, round=0) == Identity(
        STEP, keys.MAX_INTEGER, 0
    )
    assert identity_of(end(**TARGET)) == EXAMPLE_ID
    assert hash(step_identity(STEP, 1)) == hash(Identity(STEP, 1))


def test_end_line_with_failure_is_ended_and_counted():
    lines = [start(), end(spend={AXIS: 4}, failure=FAILURE)]
    assert check_step(lines[1]) is None
    assert view_of(lines) == SpendView({AXIS: 4}, 2, frozenset())
    assert step_state(Identity(STEP, 1), lines) == StepState(
        State.ENDED, None, FAILURE, {AXIS: 4}
    )


def test_spend_empty_several_axes_and_several_lines():
    lines = [
        start(),
        end(),
        start(execution=2),
        end(execution=2, spend={AXIS: 3, OTHER_AXIS: 10}),
        start(execution=3),
        end(execution=3, spend={AXIS: 5, "zero_axis": 0}),
    ]
    assert view_of(lines[:2]) == SpendView({}, 2, frozenset())
    assert view_of(lines).totals == {AXIS: 8, OTHER_AXIS: 10, "zero_axis": 0}
    assert step_state(Identity(STEP, 1), lines).spend == {}


def test_a_total_is_the_exact_sum_beyond_the_largest_integer():
    lines = [end(execution=n, spend={AXIS: keys.MAX_INTEGER}) for n in (1, 2, 3)]
    view = view_of(lines)
    assert view.totals == {AXIS: 3 * keys.MAX_INTEGER}
    assert view_of([end(execution=4, spend={AXIS: 1})], view).totals[AXIS] == (
        3 * keys.MAX_INTEGER + 1
    )


def test_lines_of_other_kinds_count_in_the_position_only():
    lines = [other(), EXAMPLE[0], other(**TARGET), other(round=3), EXAMPLE[1], other()]
    assert fold(lines) == (SpendView({AXIS: 7}, 6, frozenset()), ())
    assert step_state(EXAMPLE_ID, lines).state is State.ENDED
    assert view_of([other(), other()]) == SpendView({}, 2, frozenset())


@pytest.mark.parametrize(
    ("cut", "state", "totals", "open_steps"),
    [
        (1, State.NO_LINE, {}, frozenset()),
        (2, State.OPEN, {}, frozenset({EXAMPLE_ID})),
        (3, State.ENDED, {AXIS: 7}, frozenset()),
    ],
)
def test_three_death_points(cut, state, totals, open_steps):
    log = [other(), *EXAMPLE][:cut]
    assert step_state(EXAMPLE_ID, log).state is state
    assert fold(log) == (SpendView(totals, cut, open_steps), ())
    assert fold(log + log[cut:]) == fold(log)


def test_an_end_line_appended_later_ends_an_open_step():
    stored = view_of([EXAMPLE[0], other()])
    assert stored == SpendView({}, 2, frozenset({EXAMPLE_ID}))
    assert step_state(EXAMPLE_ID, [], stored) == StepState(State.OPEN)
    assert step_state(EXAMPLE_ID, [other()], stored).state is State.OPEN
    tail = [other(), EXAMPLE[1]]
    assert fold(tail, stored) == (SpendView({AXIS: 7}, 4, frozenset()), ())
    assert step_state(EXAMPLE_ID, tail, stored) == StepState(
        State.ENDED, dict(RESULT), None, {AXIS: 7}
    )


def test_second_end_line_is_counted_and_reported_and_the_first_is_returned():
    identity = Identity(STEP, 1)
    lines = [start(), end(spend={AXIS: 2}), end(spend={AXIS: 5}, failure=FAILURE)]
    view, reports = fold(lines)
    assert view == SpendView({AXIS: 7}, 3, frozenset())
    assert reports == (Report(3, identity, Problem.END_NOT_OPEN),)
    assert step_state(identity, lines) == StepState(
        State.ENDED, dict(RESULT), None, {AXIS: 2}
    )
    assert step_state(identity, lines[:2]) == step_state(identity, lines)


def test_end_line_without_a_start_line_is_counted_and_reported():
    lines = [other(), end(spend={AXIS: 2}, **TARGET)]
    assert fold(lines) == (
        SpendView({AXIS: 2}, 2, frozenset()),
        (Report(2, EXAMPLE_ID, Problem.END_NOT_OPEN),),
    )
    assert step_state(EXAMPLE_ID, lines).state is State.ENDED


def test_second_start_line_of_an_open_identity_is_reported_and_stays_open():
    identity = Identity(STEP, 1)
    view, reports = fold([start(), other(), start()])
    assert view == SpendView({}, 3, frozenset({identity}))
    assert reports == (Report(3, identity, Problem.START_REPEATED),)
    assert step_state(identity, [start(), start()]).state is State.OPEN
    assert fold([start()], view) == (
        SpendView({}, 4, frozenset({identity})),
        (Report(4, identity, Problem.START_REPEATED),),
    )


def test_start_line_of_an_identity_that_ended():
    identity = Identity(STEP, 1)
    lines = [start(), end(spend={AXIS: 2}), start()]
    view, reports = fold(lines)
    assert view == SpendView({AXIS: 2}, 3, frozenset({identity}))
    assert reports == (Report(3, identity, Problem.START_REPEATED),)
    assert step_state(identity, lines) == StepState(
        State.ENDED, dict(RESULT), None, {AXIS: 2}
    )
    # A view holds no ended identity: from the tail the same line is not reported.
    assert fold(lines[2:], view_of(lines[:2])) == (view, ())
    assert step_state(identity, lines[2:], view_of(lines[:2])).state is State.OPEN
    again = [*lines, end(spend={AXIS: 1})]
    assert fold(again) == (SpendView({AXIS: 3}, 4, frozenset()), reports)


MIXED = [
    other(),
    start(**TARGET),
    start(),
    other(round=1),
    end(spend={AXIS: 7, OTHER_AXIS: 1}, **TARGET),
    start(execution=2, round=1),
    end(spend={AXIS: 2}, failure=FAILURE),
    end(spend={AXIS: 3}),
    start(),
    end(step="other_step", spend={"zero_axis": 0}, round=0, candidate=1),
    start(execution=2, round=1),
    end(spend={OTHER_AXIS: 4}, **TARGET),
    other(),
]


def test_reports_of_the_mixed_sequence():
    view, reports = fold(MIXED)
    assert view == SpendView(
        {AXIS: 12, OTHER_AXIS: 5, "zero_axis": 0},
        13,
        frozenset({Identity(STEP, 1), Identity(STEP, 2, 1)}),
    )
    assert reports == (
        Report(8, Identity(STEP, 1), Problem.END_NOT_OPEN),
        Report(9, Identity(STEP, 1), Problem.START_REPEATED),
        Report(10, Identity("other_step", 1, 0, 1), Problem.END_NOT_OPEN),
        Report(11, Identity(STEP, 2, 1), Problem.START_REPEATED),
        Report(12, EXAMPLE_ID, Problem.END_NOT_OPEN),
    )


@pytest.mark.parametrize("cut", range(len(MIXED) + 1))
def test_folding_a_tail_from_the_view_of_its_prefix_gives_the_whole(cut):
    whole, reports = fold(MIXED)
    prefix, before = fold(MIXED[:cut])
    assert prefix.position == cut
    view, after = fold(MIXED[cut:], prefix)
    assert view == whole
    assert (view.totals, view.position, view.open_steps) == tuple(whole)
    assert {report.line for report in before + after} <= {
        report.line for report in reports
    }
    assert all(report.line > cut for report in after)


@pytest.mark.parametrize("cut", range(len(MIXED) + 1))
def test_state_of_the_step_in_progress_is_the_same_from_the_tail(cut):
    log = [*MIXED, start(step="late_step"), end(step="late_step", spend={AXIS: 1})]
    identity = Identity("late_step", 1)
    stored = view_of(log[:cut])
    assert step_state(identity, log[cut:], stored) == step_state(identity, log)
    assert step_state(identity, log[cut:-1], stored).state is State.OPEN


def test_arguments_are_not_modified_and_nothing_is_shared():
    lines = copy.deepcopy(MIXED)
    totals = {AXIS: 1}
    stored = SpendView(totals, 5, {Identity(STEP, 1)})
    view, _ = fold(lines, stored)
    state = step_state(EXAMPLE_ID, lines, stored)
    assert lines == MIXED
    assert stored == SpendView({AXIS: 1}, 5, {Identity(STEP, 1)})
    totals[AXIS] = 99
    assert view.totals[AXIS] == 13
    assert type(view.totals) is MappingProxyType
    assert type(view.open_steps) is frozenset
    with pytest.raises(TypeError):
        view.totals[AXIS] = 0
    state.result["example_member"] = 2
    state.spend[AXIS] = 0
    assert lines == MIXED
    assert EMPTY == SpendView({}, 0, frozenset())


def test_a_view_given_with_plain_types_is_accepted():
    stored = SpendView({AXIS: 1}, 5, {Identity(STEP, 1)})
    assert fold([end(spend={AXIS: 1})], stored) == (
        SpendView({AXIS: 2}, 6, frozenset()),
        (),
    )
    assert fold([], stored)[0] == stored


def test_lines_may_be_any_iterable_read_once():
    assert fold(iter(MIXED)) == fold(MIXED) == fold(tuple(MIXED))
    generator = (line for line in EXAMPLE)
    assert step_state(EXAMPLE_ID, generator).state is State.ENDED
    assert list(generator) == []


BAD_DATA = [
    (with_data(STEP_STARTED, step=...), "data: lacks the member step"),
    (with_data(STEP_STARTED, execution=...), "data: lacks the member execution"),
    (with_data(STEP_STARTED, step="Example"), "data.step: must be a name"),
    (with_data(STEP_STARTED, step=""), "data.step"),
    (with_data(STEP_STARTED, step="a" * 33), "data.step"),
    (with_data(STEP_STARTED, step=5), "data.step"),
    (with_data(STEP_STARTED, step=None), "data.step"),
    (with_data(STEP_STARTED, step=[STEP]), "data.step"),
    (with_data(STEP_STARTED, execution=0), "data.execution: must be an int from 1"),
    (with_data(STEP_STARTED, execution=-1), "data.execution"),
    (with_data(STEP_STARTED, execution=True), "data.execution"),
    (with_data(STEP_STARTED, execution=1.0), "data.execution"),
    (with_data(STEP_STARTED, execution="1"), "data.execution"),
    (with_data(STEP_STARTED, execution=None), "data.execution"),
    (with_data(STEP_STARTED, execution=keys.MAX_INTEGER + 1), "data.execution"),
    (with_data(STEP_STARTED, execution=10**5000), "data.execution"),
    (
        with_data(STEP_STARTED, spend={}),
        "step_started line, without the member, got str 'spend'",
    ),
    (with_data(STEP_STARTED, result={}), "without the member, got str 'result'"),
    (
        with_data(STEP_STARTED, example_member=1),
        "without the member, got str 'example_member'",
    ),
    (with_data(STEP_ENDED, example_member=1), "step_ended line, without the member"),
    (with_data(STEP_ENDED, round=3), "without the member, got str 'round'"),
    (with_data(STEP_ENDED, step=...), "data: lacks the member step"),
    (with_data(STEP_ENDED, execution=...), "data: lacks the member execution"),
    (with_data(STEP_ENDED, spend=...), "data: lacks the member spend"),
    (with_data(STEP_ENDED, execution=0), "data.execution"),
    (
        with_data(STEP_ENDED, failure=FAILURE),
        "data: must hold exactly one of result and failure",
    ),
    (
        with_data(STEP_ENDED, result=...),
        "data: must hold exactly one of result and failure",
    ),
    (with_data(STEP_ENDED, spend=None), "data.spend: must be an object"),
    (with_data(STEP_ENDED, spend=[]), "data.spend: must be an object"),
    (with_data(STEP_ENDED, spend=7), "data.spend: must be an object"),
    (
        with_data(STEP_ENDED, spend={AXIS: True}),
        f"data.spend.{AXIS}: must be an int from 0",
    ),
    (with_data(STEP_ENDED, spend={AXIS: 1.0}), f"data.spend.{AXIS}"),
    (with_data(STEP_ENDED, spend={AXIS: -1}), f"data.spend.{AXIS}"),
    (with_data(STEP_ENDED, spend={AXIS: None}), f"data.spend.{AXIS}"),
    (with_data(STEP_ENDED, spend={AXIS: "1"}), f"data.spend.{AXIS}"),
    (with_data(STEP_ENDED, spend={AXIS: {OTHER_AXIS: 1}}), f"data.spend.{AXIS}"),
    (with_data(STEP_ENDED, spend={AXIS: keys.MAX_INTEGER + 1}), f"data.spend.{AXIS}"),
    (
        with_data(STEP_ENDED, spend={"Axis": 1}),
        "data.spend: member name: must be a name",
    ),
    (with_data(STEP_ENDED, spend={"": 1}), "data.spend: member name"),
    (with_data(STEP_ENDED, spend={AXIS: 1, 5: 1}), "data.spend: member name"),
    (with_data(STEP_ENDED, result=None), "data.result: must be an object"),
    (with_data(STEP_ENDED, result=[]), "data.result: must be an object"),
    (with_data(STEP_ENDED, result="done"), "data.result: must be an object"),
    (
        with_data(STEP_ENDED, result=..., failure="broken"),
        "data.failure: must be an object",
    ),
    (
        with_data(STEP_ENDED, result=..., failure=None),
        "data.failure: must be an object",
    ),
    (with_data(STEP_ENDED, result=..., failure={}), "data.failure: must be an object"),
    (
        with_data(STEP_ENDED, result=..., failure={"kind": "example_failure"}),
        "data.failure",
    ),
    (
        with_data(STEP_ENDED, result=..., failure=FAILURE | {"example_member": 1}),
        "data.failure: must be an object with exactly kind and message",
    ),
    (
        with_data(STEP_ENDED, result=..., failure=FAILURE | {"kind": "Not a name"}),
        "data.failure.kind: must be a name",
    ),
    (
        with_data(STEP_ENDED, result=..., failure=FAILURE | {"message": 5}),
        "data.failure.message: must be a str",
    ),
]


@pytest.mark.parametrize(("line", "message"), BAD_DATA)
def test_data_that_breaks_the_table_is_refused_everywhere(line, message):
    assert events.validate(line) is None
    kept = copy.deepcopy(line)
    for check in (check_step, identity_of):
        with pytest.raises(JournalError) as error:
            check(line)
        assert message in str(error.value)
        assert not str(error.value).startswith("line ")
    for use in (fold, lambda lines: step_state(EXAMPLE_ID, lines)):
        with pytest.raises(JournalError) as error:
            use([start(), other(), line, end()])
        assert str(error.value).startswith("line 3: ")
        assert message in str(error.value)
    assert line == kept


def test_values_at_the_limits_are_accepted():
    line = end(execution=keys.MAX_INTEGER, spend={"a" * 32: keys.MAX_INTEGER, "a": 0})
    line["data"]["result"] = {"anything": [None, 1.5, {"Not a name": True}]}
    assert check_step(line) is None
    assert check_step(end(failure={"kind": "a", "message": ""})) is None


@pytest.mark.parametrize("kind", ["example_kind", "step_start", "step_ended_"])
def test_a_line_of_another_kind_is_not_a_step_line(kind):
    line = ev(kind, {"step": STEP, "execution": 1})
    for check in (check_step, identity_of):
        with pytest.raises(
            JournalError, match="kind: must be step_started or step_ended"
        ):
            check(line)


@pytest.mark.parametrize(
    ("event", "error", "message"),
    [
        (None, events.InvalidEventError, "event: must be an object"),
        ([], events.InvalidEventError, "event: must be an object"),
        (start() | {"example_member": 1}, events.InvalidEventError, "unknown member"),
        (start(candidate=1), events.InvalidEventError, "candidate: is given only"),
        (start(round=True), events.InvalidEventError, "round"),
        (start() | {"data": []}, events.InvalidEventError, "data"),
        (
            start() | {"schema_version": 2},
            events.UnsupportedVersionError,
            "schema_version",
        ),
    ],
)
def test_an_envelope_error_passes_through_and_names_the_line(event, error, message):
    for check in (check_step, identity_of):
        with pytest.raises(error, match=message) as raised:
            check(event)
        assert type(raised.value) is error
    for use in (fold, lambda lines: step_state(EXAMPLE_ID, lines)):
        with pytest.raises(error, match=f"line 2: .*{message}") as raised:
            use([other(), event])
        assert type(raised.value) is error


def test_a_line_number_continues_the_position_of_the_view():
    stored = SpendView({}, 40, frozenset())
    bad = with_data(STEP_ENDED, spend=None)
    with pytest.raises(JournalError, match="^line 42: data.spend"):
        fold([other(), bad], stored)
    with pytest.raises(JournalError, match="^line 42: data.spend"):
        step_state(EXAMPLE_ID, [other(), bad], stored)
    assert fold([other(), end()], stored)[1] == (
        Report(42, Identity(STEP, 1), Problem.END_NOT_OPEN),
    )


def test_a_malformed_line_is_never_counted_in_part():
    bad = with_data(STEP_ENDED, spend={AXIS: 5, OTHER_AXIS: -1})
    with pytest.raises(JournalError, match="line 2: data.spend.other_example_axis"):
        fold([start(), bad])
    with pytest.raises(JournalError, match="line 3: "):
        step_state(Identity(STEP, 1), [start(), end(), bad])


@pytest.mark.parametrize("lines", [None, 5, object()])
def test_lines_that_cannot_be_iterated(lines):
    with pytest.raises(TypeError):
        fold(lines)
    with pytest.raises(TypeError):
        step_state(EXAMPLE_ID, lines)


BAD_VIEWS = [
    (None, "view: must be a SpendView"),
    (({}, 0, frozenset()), "view: must be a SpendView"),
    ({"totals": {}, "position": 0, "open_steps": []}, "view: must be a SpendView"),
    (SpendView({}, -1, frozenset()), "view.position: must be an int from 0"),
    (SpendView({}, True, frozenset()), "view.position"),
    (SpendView({}, 1.0, frozenset()), "view.position"),
    (SpendView({}, None, frozenset()), "view.position"),
    (SpendView(None, 0, frozenset()), "view.totals: must be a mapping"),
    (SpendView([(AXIS, 1)], 0, frozenset()), "view.totals: must be a mapping"),
    (
        SpendView({AXIS: -1}, 0, frozenset()),
        f"view.totals.{AXIS}: must be an int from 0",
    ),
    (SpendView({AXIS: True}, 0, frozenset()), f"view.totals.{AXIS}"),
    (SpendView({AXIS: 1.0}, 0, frozenset()), f"view.totals.{AXIS}"),
    (SpendView({AXIS: None}, 0, frozenset()), f"view.totals.{AXIS}"),
    (
        SpendView({"Axis": 1}, 0, frozenset()),
        "view.totals: member name: must be a name",
    ),
    (SpendView({5: 1}, 0, frozenset()), "view.totals: member name"),
    (SpendView({}, 0, None), "view.open_steps: must be a frozenset or a set"),
    (
        SpendView({}, 0, [Identity(STEP, 1)]),
        "view.open_steps: must be a frozenset or a set",
    ),
    (
        SpendView({}, 0, {(STEP, 1, None, None, None)}),
        "view.open_steps: member: must be an",
    ),
    (SpendView({}, 0, {STEP}), "view.open_steps: member: must be an Identity"),
    (SpendView({}, 0, {Identity(STEP, 0)}), "view.open_steps: data.execution"),
    (SpendView({}, 0, {Identity("Step", 1)}), "view.open_steps: data.step"),
    (SpendView({}, 0, {Identity(STEP, 1, None, 1)}), "view.open_steps: candidate"),
    (SpendView({}, 0, {Identity(STEP, 1, True)}), "view.open_steps: round"),
]


@pytest.mark.parametrize(("view", "message"), BAD_VIEWS)
def test_a_malformed_view_is_refused_before_any_line_is_read(view, message):
    for use in (fold, lambda lines, view: step_state(EXAMPLE_ID, lines, view)):
        lines = iter(EXAMPLE)
        with pytest.raises(JournalError) as error:
            use(lines, view)
        assert message in str(error.value)
        assert type(error.value) is JournalError
        assert list(lines) == EXAMPLE


BAD_IDENTITIES = [
    ((STEP, 0), {}, JournalError, "data.execution: must be an int from 1"),
    ((STEP, True), {}, JournalError, "data.execution"),
    ((STEP, 1.0), {}, JournalError, "data.execution"),
    ((STEP, None), {}, JournalError, "data.execution"),
    (("Example Step", 1), {}, JournalError, "data.step: must be a name"),
    ((None, 1), {}, JournalError, "data.step"),
    (([STEP], 1), {}, JournalError, "data.step"),
    ((STEP, 1), {"candidate": 1}, events.InvalidEventError, "candidate: is given only"),
    ((STEP, 1), {"attempt": 1}, events.InvalidEventError, "attempt: is given only"),
    (
        (STEP, 1),
        {"round": 0, "attempt": 1},
        events.InvalidEventError,
        "attempt: is given only",
    ),
    ((STEP, 1), {"round": -1}, events.InvalidEventError, "round"),
    ((STEP, 1), {"round": True}, events.InvalidEventError, "round"),
    ((STEP, 1), {"round": "3"}, events.InvalidEventError, "round"),
    ((STEP, 1), {"round": 0, "candidate": 0}, events.InvalidEventError, "candidate"),
    ((STEP, 1), TARGET | {"attempt": 0}, events.InvalidEventError, "attempt"),
    ((STEP, 1), TARGET | {"attempt": 1.0}, events.InvalidEventError, "attempt"),
]


@pytest.mark.parametrize(("args", "numbers", "error", "message"), BAD_IDENTITIES)
def test_an_identity_that_breaks_a_rule_is_refused(args, numbers, error, message):
    with pytest.raises(error, match=message):
        step_identity(*args, **numbers)
    lines = iter(EXAMPLE)
    with pytest.raises(error, match=message):
        step_state(Identity(*args, **numbers), lines)
    assert list(lines) == EXAMPLE


@pytest.mark.parametrize(
    "identity", [None, STEP, (STEP, 1, 3, 2, 1), [STEP, 1], EXAMPLE[0]]
)
def test_step_state_takes_an_identity_only(identity):
    with pytest.raises(JournalError, match="identity: must be an Identity"):
        step_state(identity, EXAMPLE)


def test_the_module_keeps_no_state_between_calls():
    first = (fold(MIXED), step_state(EXAMPLE_ID, MIXED))
    assert (fold(MIXED), step_state(EXAMPLE_ID, MIXED)) == first
    assert journal.EMPTY is EMPTY
    assert fold([]) == (EMPTY, ())
