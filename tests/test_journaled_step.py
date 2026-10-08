import inspect
import json
import os
import re
from pathlib import Path

import pytest

from hilclaw import (
    events,
    journal,
    journaled_step,
    keys,
    layout,
    run_journal,
    run_state,
    tools,
)
from hilclaw.journal import EMPTY, Identity, SpendView, State
from hilclaw.journaled_step import KIND_STEP_OPEN, InvalidOutcomeError, StepFailed, run

# Synthetic values only: no step name, axis or member of a real run.
RUN = "run-a"
OTHER_RUN = "run-b"
STATE = f"runs/{RUN}/STATE.json"
LOG = f"runs/{RUN}/events.ndjson"
STEP = "example_step"
AXIS = "example_axis"
TIME = "2026-01-01T00:00:00Z"
MAX = keys.MAX_INTEGER
NUMBERS = ("round", "candidate", "attempt")

# The identity, the amounts and the result of the Example of ADR-0011; the run stands in round 3.
ROUND = 3
ID = Identity(STEP, 1, ROUND, 2, 1)
SPEND = {AXIS: 7}
RESULT = {"example_member": 1}
EXAMPLE_LOG = (
    b'{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "step_started",'
    b' "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:04:10Z", "kind": "step_ended",'
    b' "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1,'
    b' "spend": {"example_axis": 7}, "result": {"example_member": 1}}}\n'
)
EARLIER = Identity(STEP, 1, 1, 1, 1)
LATER = Identity(STEP, 1, 5)
NO_ROUND = Identity(STEP, 1)
FAILURE = {"kind": "example_failure", "message": "no outcome"}
OPEN_MESSAGE = "the step example_step execution 1 round 3 candidate 2 attempt 1 is open"
MISSING = tools.KIND_RUN_FILE_MISSING
UNREADABLE = tools.KIND_RUN_FILE_UNREADABLE
INVALID = tools.KIND_RUN_FILE_INVALID
UNSUPPORTED = tools.KIND_RUN_FILE_UNSUPPORTED


class Step:
    """A step that counts its calls, records the log it sees and gives ``outcome``."""

    def __init__(self, outcome=(SPEND, RESULT), root=None):
        self.outcome, self.root = outcome, root
        self.calls, self.seen = 0, None

    def __call__(self):
        self.calls += 1
        if self.root is not None:
            self.seen = (self.root / LOG).read_bytes()
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


def failed(spend=None, kind=FAILURE["kind"], message=FAILURE["message"]):
    return Step(StepFailed({} if spend is None else spend, kind, message))


def event(kind, data, identity=None):
    numbers = {} if identity is None else identity._asdict()
    numbers = {name: numbers[name] for name in NUMBERS if numbers.get(name) is not None}
    return {"schema_version": 1, "time": TIME, "kind": kind, **numbers, "data": data}


def started(identity):
    data = {"step": identity.step, "execution": identity.execution}
    return event("step_started", data, identity)


def ended(identity, amount=None, **outcome):
    data = {"step": identity.step, "execution": identity.execution}
    data["spend"] = {} if amount is None else {AXIS: amount}
    return event("step_ended", data | (outcome or {"result": {}}), identity)


def other(member=0):
    return event("example_kind", {"example_member": member})


def raw(*lines):
    return b"".join(json.dumps(line).encode() + b"\n" for line in lines)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    store(path)
    return path


def place(root, content, relative=LOG):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def store(root, view=EMPTY, round=ROUND, run=RUN):
    return place(root, run_state.dump(round, view), f"runs/{run}/STATE.json")


def at(position):
    return SpendView({}, position, frozenset())


def lines(root, run=RUN):
    return events.read(root, run).events


def snapshot(path):
    return {
        item.relative_to(path).as_posix(): item.read_bytes() if item.is_file() else None
        for item in path.rglob("*")
    }


def without_time(line):
    return {name: value for name, value in line.items() if name != "time"}


def assert_open_and_not_run(root, identity=ID):
    before = snapshot(root)
    step = Step()
    with pytest.raises(tools.ToolFailure) as caught:
        run(root, RUN, identity, step)
    assert caught.value.kind == KIND_STEP_OPEN
    assert step.calls == 0
    assert snapshot(root) == before


# --- happy ---


def test_signature_and_types():
    assert list(inspect.signature(run).parameters) == [
        "data_root",
        "run_id",
        "identity",
        "step",
    ]
    assert KIND_STEP_OPEN is tools.KIND_STEP_OPEN == "step_open"
    assert issubclass(InvalidOutcomeError, ValueError)
    assert not issubclass(InvalidOutcomeError, journal.JournalError)
    assert not issubclass(StepFailed, tools.ToolFailure)
    error = StepFailed(SPEND, "example_failure", "no outcome")
    assert (error.spend, error.kind, error.message) == (
        SPEND,
        "example_failure",
        "no outcome",
    )


def test_no_line_writes_the_two_lines_of_the_example(root):
    step = Step()
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 1
    written = lines(root)
    expected = [json.loads(line) for line in EXAMPLE_LOG.splitlines()]
    assert list(map(without_time, written)) == list(map(without_time, expected))
    assert [list(line) for line in written] == [list(line) for line in expected]
    for line in written:
        journal.check_step(line)
    assert (root / LOG).read_bytes().endswith(b"\n")
    now = run_journal.current(root, RUN)
    assert dict(now.view.totals) == SPEND
    assert now.view.open_steps == frozenset()
    assert now.view.position == 2
    assert now.reports == ()


def test_a_step_without_an_outcome_leaves_an_end_line_with_failure_and_spend(root):
    step = failed({AXIS: 2})
    with pytest.raises(tools.ToolFailure) as caught:
        run(root, RUN, ID, step)
    assert (caught.value.kind, caught.value.message) == tuple(FAILURE.values())
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert step.calls == 1
    start, end = lines(root)
    assert without_time(start) == without_time(started(ID))
    assert without_time(end) == without_time(ended(ID, 2, failure=FAILURE))
    journal.check_step(end)
    now = run_journal.current(root, RUN)
    assert dict(now.view.totals) == {AXIS: 2}
    assert now.view.open_steps == frozenset()


@pytest.mark.parametrize(
    "identity",
    [
        ID,
        Identity(STEP, 1, ROUND, 2),
        Identity(STEP, 1, ROUND),
        Identity(STEP, 1, 0),
        NO_ROUND,
    ],
)
def test_the_envelope_numbers_are_those_of_the_identity(root, identity):
    assert run(root, RUN, identity, Step()) == RESULT
    start, end = lines(root)
    assert without_time(start) == without_time(started(identity))
    assert without_time(end) == without_time(ended(identity, 7, result=RESULT))
    assert journal.identity_of(start) == journal.identity_of(end) == identity


@pytest.mark.parametrize("step", [Step(({}, {})), failed()])
def test_an_empty_spend_is_written_as_stated(root, step):
    if isinstance(step.outcome, StepFailed):
        with pytest.raises(tools.ToolFailure):
            run(root, RUN, ID, step)
    else:
        assert run(root, RUN, ID, step) == {}
    assert lines(root)[1]["data"]["spend"] == {}
    assert dict(run_journal.current(root, RUN).view.totals) == {}


def test_the_data_root_may_be_a_str(root):
    assert run(str(root), RUN, ID, Step()) == RESULT
    assert run(str(root), RUN, ID, Step()) == RESULT
    assert len(lines(root)) == 2


def test_a_second_run_is_untouched_and_has_its_own_identities(root):
    store(root, run=OTHER_RUN)
    before = snapshot(root / "runs" / OTHER_RUN)
    assert run(root, RUN, ID, Step()) == RESULT
    assert snapshot(root / "runs" / OTHER_RUN) == before
    step = Step(({}, {"example_member": 2}))
    assert run(root, OTHER_RUN, ID, step) == {"example_member": 2}
    assert step.calls == 1
    assert len(lines(root)) == len(lines(root, OTHER_RUN)) == 2


def test_the_result_returned_is_a_copy_and_a_nested_value_is_kept(root):
    result = {"example_member": [1, 2.5, "x", None, True, {"inner": []}]}
    spend = {AXIS: 0, "other_axis": MAX}
    returned = run(root, RUN, ID, Step((spend, result)))
    assert returned == result
    assert returned is not result
    returned["example_member"].append("changed")
    again = run(root, RUN, ID, Step())
    assert again == result
    assert lines(root)[1]["data"]["spend"] == spend


def test_a_nested_result_is_answered_equal_by_a_repeated_call(root):
    nested = []
    for _ in range(50):
        nested = [{"example_member": nested}]
    assert run(root, RUN, ID, Step((SPEND, {"example_member": nested}))) == {
        "example_member": nested
    }
    assert run(root, RUN, ID, Step()) == {"example_member": nested}


# --- the three states (decision 4) ---


def test_ended_with_a_result_is_answered_from_the_line_and_not_run(root):
    first = run(root, RUN, ID, Step())
    before = snapshot(root)
    step = Step(({AXIS: 99}, {"example_member": 2}))
    assert run(root, RUN, ID, step) == first == RESULT
    assert step.calls == 0
    assert snapshot(root) == before
    assert dict(run_journal.current(root, RUN).view.totals) == SPEND


def test_ended_with_a_failure_raises_the_same_failure_and_is_not_run(root):
    with pytest.raises(tools.ToolFailure) as first:
        run(root, RUN, ID, failed({AXIS: 2}))
    before = snapshot(root)
    step = Step()
    with pytest.raises(tools.ToolFailure) as second:
        run(root, RUN, ID, step)
    assert (second.value.kind, second.value.message) == (
        first.value.kind,
        first.value.message,
    )
    assert second.value.error_object() == first.value.error_object()
    assert second.value.__cause__ is None
    assert step.calls == 0
    assert snapshot(root) == before


def test_open_is_a_tool_failure_that_names_the_identity_and_is_not_run(root):
    place(root, raw(started(ID)))
    step = Step()
    with pytest.raises(tools.ToolFailure) as caught:
        run(root, RUN, ID, step)
    assert caught.value.kind == "step_open"
    assert caught.value.message == OPEN_MESSAGE
    assert step.calls == 0
    assert (root / LOG).read_bytes() == raw(started(ID))
    assert_open_and_not_run(root)


def test_the_message_of_an_open_step_names_only_the_numbers_given(root):
    place(root, raw(started(NO_ROUND), started(Identity(STEP, 2, ROUND))))
    with pytest.raises(tools.ToolFailure) as caught:
        run(root, RUN, NO_ROUND, Step())
    assert caught.value.message == "the step example_step execution 1 is open"
    with pytest.raises(tools.ToolFailure) as caught:
        run(root, RUN, Identity(STEP, 2, ROUND), Step())
    assert caught.value.message == "the step example_step execution 2 round 3 is open"


def test_an_identity_open_in_the_stored_view_is_open(root):
    place(root, raw(started(ID)))
    store(root, SpendView({}, 1, frozenset({ID})))
    assert_open_and_not_run(root)


def test_a_higher_execution_is_another_identity_and_runs(root):
    place(root, raw(started(ID)))
    again = ID._replace(execution=2)
    step = Step()
    assert run(root, RUN, again, step) == RESULT
    assert step.calls == 1
    assert [journal.identity_of(line) for line in lines(root)] == [ID, again, again]
    assert run_journal.current(root, RUN).view.open_steps == frozenset({ID})
    assert_open_and_not_run(root)


@pytest.mark.parametrize(
    "different",
    [ID._replace(step="other_step"), ID._replace(candidate=1), ID._replace(attempt=2)],
)
def test_another_step_or_target_is_another_identity(root, different):
    place(root, raw(started(ID)))
    assert run(root, RUN, different, Step()) == RESULT


def test_the_first_end_line_answers_when_the_log_holds_two(root):
    first = ended(ID, 1, result={"example_member": 1})
    second = ended(ID, 1, failure=FAILURE)
    place(root, raw(started(ID), first, second))
    step = Step()
    assert run(root, RUN, ID, step) == {"example_member": 1}
    assert step.calls == 0


def test_an_ended_step_is_answered_with_a_torn_tail_left_in_place(root):
    content = (
        raw(started(ID), ended(ID, 7, result=RESULT)) + b'{"schema_version": 1, "ti'
    )
    place(root, content)
    step = Step()
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 0
    assert (root / LOG).read_bytes() == content


# --- the three death points ---


def fail_append(monkeypatch, kind, after=False):
    real = events.append

    def append(data_root, run_id, line_kind, data, **numbers):
        if line_kind != kind:
            return real(data_root, run_id, line_kind, data, **numbers)
        if after:
            real(data_root, run_id, line_kind, data, **numbers)
        raise OSError("example failure of the append")

    monkeypatch.setattr(events, "append", append)


def test_death_before_the_start_line_is_complete_the_next_call_runs(root, monkeypatch):
    with monkeypatch.context() as patch:
        fail_append(patch, "step_started")
        step = Step()
        with pytest.raises(OSError, match="example failure"):
            run(root, RUN, ID, step)
        assert step.calls == 0
    assert not (root / LOG).exists()
    step = Step()
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 1
    assert dict(run_journal.current(root, RUN).view.totals) == SPEND


def test_death_after_the_start_line_and_before_the_step_leaves_it_open(
    root, monkeypatch
):
    with monkeypatch.context() as patch:
        fail_append(patch, "step_started", after=True)
        step = Step()
        with pytest.raises(OSError, match="example failure"):
            run(root, RUN, ID, step)
        assert step.calls == 0
    assert list(map(without_time, lines(root))) == [without_time(started(ID))]
    assert_open_and_not_run(root)


def test_a_step_that_fails_with_the_kind_of_an_open_step_is_ended(root):
    with pytest.raises(tools.ToolFailure) as first:
        run(root, RUN, ID, failed({AXIS: 2}, KIND_STEP_OPEN, "stated by the step"))
    step = Step()
    with pytest.raises(tools.ToolFailure) as second:
        run(root, RUN, ID, step)
    assert (
        first.value.args == second.value.args == (KIND_STEP_OPEN, "stated by the step")
    )
    assert step.calls == 0
    assert run_journal.step_state(root, RUN, ID).state is State.ENDED


def test_a_torn_start_line_is_no_line_the_next_call_runs(root):
    place(root, raw(started(ID))[:-1])
    step = Step()
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 1
    assert list(map(without_time, lines(root))) == [
        without_time(started(ID)),
        without_time(ended(ID, 7, result=RESULT)),
    ]
    assert events.read(root, RUN).torn_tail == 0


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("died"),
        tools.ToolFailure("example_failure", "no amounts"),
        KeyboardInterrupt(),
    ],
)
def test_death_during_the_step_leaves_it_open(root, error):
    step = Step(error)
    with pytest.raises(type(error)) as caught:
        run(root, RUN, ID, step)
    assert caught.value is error
    assert step.calls == 1
    assert list(map(without_time, lines(root))) == [without_time(started(ID))]
    now = run_journal.current(root, RUN)
    assert now.view.open_steps == frozenset({ID})
    assert dict(now.view.totals) == {}
    assert_open_and_not_run(root)


@pytest.mark.parametrize("step", [Step(), failed({AXIS: 2})])
def test_death_between_the_outcome_and_the_end_line_leaves_it_open(
    root, monkeypatch, step
):
    with monkeypatch.context() as patch:
        fail_append(patch, "step_ended")
        with pytest.raises(OSError, match="example failure"):
            run(root, RUN, ID, step)
    assert step.calls == 1
    assert [line["kind"] for line in lines(root)] == ["step_started"]
    assert dict(run_journal.current(root, RUN).view.totals) == {}
    assert_open_and_not_run(root)


def test_death_after_the_end_line_the_next_call_answers_and_counts_once(
    root, monkeypatch
):
    with monkeypatch.context() as patch:
        fail_append(patch, "step_ended", after=True)
        with pytest.raises(OSError, match="example failure"):
            run(root, RUN, ID, Step())
    before = snapshot(root)
    step = Step(({AXIS: 99}, {}))
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 0
    assert snapshot(root) == before
    now = run_journal.current(root, RUN)
    assert dict(now.view.totals) == SPEND
    assert now.view.open_steps == frozenset()
    assert now.reports == ()


# --- order ---


def test_the_start_line_is_complete_when_the_step_is_called(root):
    step = Step(root=root)
    run(root, RUN, ID, step)
    assert step.seen.endswith(b"\n")
    seen = [json.loads(line) for line in step.seen.splitlines()]
    assert list(map(without_time, seen)) == [without_time(started(ID))]
    after = (root / LOG).read_bytes()
    assert after.startswith(step.seen)
    assert len(after.splitlines()) == 2


def test_the_state_is_established_before_anything_is_appended_or_run(root, monkeypatch):
    order = []

    def recorded(module, name):
        real = getattr(module, name)

        def function(*args, **kwargs):
            order.append((name, args[2]) if name == "append" else name)
            return real(*args, **kwargs)

        monkeypatch.setattr(module, name, function)

    recorded(run_journal, "read_state")
    recorded(events, "read")
    recorded(journal, "step_state")
    recorded(events, "append")

    def step():
        order.append("step")
        return SPEND, RESULT

    run(root, RUN, ID, step)
    assert order == [
        "step_state",
        "read_state",
        "read",
        "step_state",
        ("append", "step_started"),
        "step",
        "step_state",
        ("append", "step_ended"),
    ]
    del order[:]
    run(root, RUN, ID, step)
    assert order == ["step_state", "read_state", "read", "step_state"]


# --- branch: where the lookup reads ---


def test_an_identity_of_the_stored_round_is_decided_by_the_tail(root):
    place(root, raw(other(), other(1), started(ID), ended(ID, 7, result=RESULT)))
    store(root, at(2))
    step = Step()
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 0
    again = ID._replace(candidate=3)
    assert run(root, RUN, again, step) == RESULT
    assert step.calls == 1
    assert len(lines(root)) == 6


@pytest.mark.parametrize("identity", [EARLIER, NO_ROUND, LATER])
def test_an_identity_of_another_round_that_ended_before_the_position_is_not_run(
    root, identity
):
    place(root, raw(started(identity), ended(identity, 4, result=RESULT), other()))
    store(root, SpendView({AXIS: 4}, 2, frozenset()), round=4)
    assert run_journal.step_state(root, RUN, identity).state is State.NO_LINE
    before = snapshot(root)
    step = Step(({AXIS: 99}, {}))
    assert run(root, RUN, identity, step) == RESULT
    assert step.calls == 0
    assert snapshot(root) == before


def test_an_identity_of_an_earlier_round_that_failed_before_the_position_fails_again(
    root,
):
    place(root, raw(started(EARLIER), ended(EARLIER, 4, failure=FAILURE)))
    store(root, SpendView({AXIS: 4}, 2, frozenset()), round=4)
    step = Step()
    with pytest.raises(tools.ToolFailure) as caught:
        run(root, RUN, EARLIER, step)
    assert (caught.value.kind, caught.value.message) == tuple(FAILURE.values())
    assert step.calls == 0


@pytest.mark.parametrize("identity", [EARLIER, NO_ROUND])
def test_an_identity_of_another_round_open_before_the_position_is_open(root, identity):
    place(root, raw(started(identity), other()))
    store(root, SpendView({}, 2, frozenset({identity})), round=4)
    assert_open_and_not_run(root, identity)


@pytest.mark.parametrize("identity", [EARLIER, NO_ROUND, LATER])
def test_an_identity_of_another_round_with_no_line_anywhere_runs(root, identity):
    place(root, raw(other(), started(ID), ended(ID, 1, result={})))
    store(root, SpendView({AXIS: 1}, 3, frozenset()), round=4)
    step = Step()
    assert run(root, RUN, identity, step) == RESULT
    assert step.calls == 1
    assert [journal.identity_of(line) for line in lines(root)[3:]] == [
        identity,
        identity,
    ]
    assert dict(run_journal.current(root, RUN).view.totals) == {AXIS: 8}


def test_lines_before_the_position_are_interpreted_on_the_first_line_path_only(root):
    damaged = b"not a line\n" + raw(other())
    place(root, damaged)
    store(root, at(2))
    step = Step()
    assert_answered(root, INVALID, events.CorruptEventsError, EARLIER, LOG, "line 1")
    assert_answered(root, INVALID, events.CorruptEventsError, NO_ROUND, LOG, "line 1")
    assert (root / LOG).read_bytes() == damaged
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 1
    assert (root / LOG).read_bytes().startswith(damaged)
    assert run(root, RUN, ID, step) == RESULT
    assert step.calls == 1


@pytest.mark.parametrize("identity", [ID, EARLIER, NO_ROUND, LATER])
@pytest.mark.parametrize("content", [None, b"", raw(other()), raw(other())[:-1]])
def test_a_position_beyond_the_log_is_invalid_on_both_paths(root, identity, content):
    if content is not None:
        place(root, content)
    store(root, at(2))
    with pytest.raises(events.PositionBeyondLogError) as expected:
        run_journal.current(root, RUN)
    failure = assert_answered(
        root, INVALID, events.PositionBeyondLogError, identity, LOG
    )
    assert failure.message == str(expected.value)


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_position_at_the_end_of_the_log_is_not_beyond_it(root, identity):
    place(root, raw(other(), other(1)))
    store(root, at(2))
    assert run(root, RUN, identity, Step()) == RESULT


# --- error / negative ---


def assert_refused(root, error, identity=ID, match=None):
    before = snapshot(root)
    step = Step()
    with pytest.raises(error, match=match) as caught:
        run(root, RUN, identity, step)
    assert type(caught.value) is error
    assert step.calls == 0
    assert snapshot(root) == before


def answered(root, kind, cause, identity=ID, file=STATE, match=None, once=False):
    """The lookup answers with ``kind`` through both entries; nothing else is called."""
    step, before = Step(), Before(Path(root))
    for call in (
        lambda: prepared(root, step, before, identity),
        lambda: run(root, RUN, identity, step),
    )[: 1 if once else 2]:
        with pytest.raises(tools.ToolFailure) as caught:
            call()
        assert type(caught.value) is tools.ToolFailure
        assert caught.value.kind == kind
        assert type(caught.value.__cause__) is cause
        assert caught.value.message.startswith(f"{file}: ")
        assert match is None or re.search(match, caught.value.message)
    assert (step.calls, before.calls) == (0, 0)
    return caught.value


def assert_answered(root, kind, cause, identity=ID, file=STATE, match=None):
    before = snapshot(Path(root))
    failure = answered(root, kind, cause, identity, file, match)
    assert snapshot(Path(root)) == before
    return failure


@pytest.mark.parametrize("identity", [ID, EARLIER, NO_ROUND])
def test_a_missing_state_file_is_missing_and_nothing_is_created(tmp_path, identity):
    failure = assert_answered(
        tmp_path, MISSING, run_journal.MissingStateError, identity
    )
    assert failure.message == f"{STATE}: is missing"
    place(tmp_path, raw(started(identity), ended(identity)))
    assert_answered(tmp_path, MISSING, run_journal.MissingStateError, identity)


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_file_in_the_place_of_the_run_directory_is_missing(tmp_path, identity):
    place(tmp_path, b"x", f"runs/{RUN}")
    assert_answered(tmp_path, MISSING, run_journal.MissingStateError, identity)


@pytest.mark.parametrize(
    ("content", "kind", "error"),
    [
        (b"", INVALID, run_state.InvalidStateError),
        (b"{}\n", INVALID, run_state.InvalidStateError),
        (
            b'{"schema_version": 1, "round": -1, "budget_spent": {}}\n',
            INVALID,
            run_state.InvalidStateError,
        ),
        (
            run_state.dump(ROUND, EMPTY).replace(
                b'"schema_version": 1', b'"schema_version": 2'
            ),
            UNSUPPORTED,
            run_state.UnsupportedVersionError,
        ),
    ],
)
@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_an_invalid_and_an_other_version_state_file_have_their_kinds(
    root, identity, content, kind, error
):
    place(root, content, STATE)
    assert_answered(root, kind, error, identity)


def test_a_state_file_that_is_a_directory_is_invalid(tmp_path):
    (tmp_path / STATE).mkdir(parents=True)
    assert_answered(tmp_path, INVALID, run_state.InvalidStateError)
    assert_answered(tmp_path, INVALID, run_state.InvalidStateError, EARLIER)


@pytest.mark.parametrize(
    ("identity", "position"), [(ID, 0), (ID, 1), (EARLIER, 0), (EARLIER, 2)]
)
def test_a_damaged_line_in_the_lines_read_is_invalid(root, identity, position):
    place(root, raw(other()) + b'{"schema_version": 1}\n')
    store(root, at(position))
    assert_answered(
        root, INVALID, events.CorruptEventsError, identity, LOG, "line 2: is damaged"
    )


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_line_of_another_version_in_the_lines_read_is_unsupported(root, identity):
    place(root, raw(other() | {"schema_version": 2}))
    assert_answered(
        root, UNSUPPORTED, events.UnsupportedVersionError, identity, LOG, "line 1"
    )


MALFORMED = [
    event("step_started", {"step": STEP}),
    event("step_started", {"step": STEP, "execution": 0}),
    event("step_ended", {"step": STEP, "execution": 1, "spend": {}}),
    event(
        "step_ended", {"step": STEP, "execution": 1, "spend": {AXIS: -1}, "result": {}}
    ),
]


@pytest.mark.parametrize("line", MALFORMED)
@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_malformed_step_line_in_the_lines_read_is_invalid(root, identity, line):
    place(root, raw(other(), line))
    with pytest.raises(journal.JournalError) as expected:
        run_journal.step_state(root, RUN, identity)
    failure = assert_answered(root, INVALID, journal.JournalError, identity, LOG)
    assert failure.message == f"{LOG}: {expected.value}"
    assert failure.message.startswith(f"{LOG}: line 2: ")


def test_a_malformed_step_line_is_named_by_its_line_number_in_the_file(root):
    place(root, raw(other(), other(1), MALFORMED[0]))
    store(root, at(2))
    assert_answered(root, INVALID, journal.JournalError, ID, LOG, "^[^:]+: line 3: ")
    assert_answered(root, INVALID, journal.JournalError, EARLIER, LOG, ": line 3: ")


def test_a_malformed_step_line_before_the_position_is_not_found_by_the_tail(root):
    place(root, raw(MALFORMED[0], other()))
    store(root, at(1))
    assert_answered(root, INVALID, journal.JournalError, NO_ROUND, LOG, ": line 1: ")
    assert run(root, RUN, ID, Step()) == RESULT


def test_a_log_that_is_a_directory_is_invalid(root):
    (root / LOG).mkdir()
    for identity in (ID, EARLIER):
        failure = assert_answered(
            root, INVALID, events.CorruptEventsError, identity, LOG
        )
        assert failure.message == f"{LOG}: is not a regular file"


def test_the_situation_found_first_is_answered(root):
    place(root, b"not a line\n")
    place(root, b"{", STATE)
    assert_answered(root, INVALID, run_state.InvalidStateError, ID, STATE)
    (root / STATE).unlink()
    assert_answered(root, MISSING, run_journal.MissingStateError, ID, STATE)
    store(root, at(3))
    assert_answered(root, INVALID, events.PositionBeyondLogError, ID, LOG)
    assert_answered(root, INVALID, events.CorruptEventsError, EARLIER, LOG, "line 1")


def test_a_missing_data_root_is_missing_and_is_not_created(tmp_path):
    missing = tmp_path / "missing"
    for root, identity in ((missing, ID), (str(missing), NO_ROUND)):
        failure = assert_answered(root, MISSING, FileNotFoundError, identity)
        assert failure.message == (
            f"{STATE}: is missing: the data root is not an existing directory"
        )
        assert str(missing) not in failure.message
    assert not missing.exists()


def test_a_file_in_the_place_of_the_data_root_is_missing(tmp_path):
    file = tmp_path / "file"
    file.write_bytes(b"x")
    assert_answered(file, MISSING, NotADirectoryError, ID, STATE, "the data root")
    assert file.read_bytes() == b"x"


# --- the file system at the reads (ADR-0019 decision 4) ---


def fail_read(monkeypatch, target, name, error):
    """Make ``os.lstat`` or ``Path.read_bytes`` raise ``error`` for the file ``name``."""
    owner, attribute = (os, "lstat") if target == "lstat" else (Path, "read_bytes")
    real = getattr(owner, attribute)

    def failing(path, *arguments, **options):
        if Path(path).name == name:
            raise error
        return real(path, *arguments, **options)

    monkeypatch.setattr(owner, attribute, failing)


def before_read(monkeypatch, name, action):
    """Run ``action`` once, just before the bytes of the file ``name`` are read."""
    real, done = Path.read_bytes, []

    def read_bytes(path):
        if path.name == name and not done:
            done.append(action())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)


def after_read(monkeypatch, name, action):
    """Run ``action`` once, just after the bytes of the file ``name`` were read."""
    real, done = Path.read_bytes, []

    def read_bytes(path):
        content = real(path)
        if path.name == name and not done:
            done.append(action())
        return content

    monkeypatch.setattr(Path, "read_bytes", read_bytes)


@pytest.mark.parametrize("identity", [ID, EARLIER])
@pytest.mark.parametrize("target", ["lstat", "read_bytes"])
@pytest.mark.parametrize(("name", "file"), [("STATE.json", STATE), (LOG[-13:], LOG)])
def test_a_read_the_file_system_fails_is_unreadable(
    root, monkeypatch, identity, target, name, file
):
    place(root, raw(other()))
    before = snapshot(root)
    error = PermissionError(13, "Permission denied", str(root / file))
    with monkeypatch.context() as patch:
        fail_read(patch, target, name, error)
        failure = answered(root, UNREADABLE, PermissionError, identity, file)
        assert failure.__cause__ is error
    assert (
        failure.message
        == f"{file}: could not be read: PermissionError: Permission denied"
    )
    assert snapshot(root) == before
    assert run(root, RUN, identity, Step()) == RESULT


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_state_file_that_goes_between_the_check_and_the_read_is_missing(
    root, monkeypatch, identity
):
    with monkeypatch.context() as patch:
        before_read(patch, "STATE.json", (root / STATE).unlink)
        failure = answered(root, MISSING, FileNotFoundError, identity, once=True)
    assert failure.message == f"{STATE}: is missing"
    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None}


@pytest.mark.parametrize("identity", [ID, EARLIER])
@pytest.mark.parametrize(
    ("name", "file", "moment"),
    [
        ("STATE.json", STATE, before_read),
        ("STATE.json", LOG, after_read),
        ("events.ndjson", LOG, before_read),
    ],
    ids=["at-the-state-read", "before-the-log", "at-the-log-read"],
)
def test_a_data_root_that_goes_during_the_lookup_is_missing(
    root, monkeypatch, identity, name, file, moment
):
    place(root, raw(other()))
    before, gone = snapshot(root), root.with_name("gone")
    with monkeypatch.context() as patch:
        moment(patch, name, lambda: root.rename(gone))
        failure = answered(root, MISSING, FileNotFoundError, identity, file, once=True)
    assert failure.message == (
        f"{file}: is missing: the data root is not an existing directory"
    )
    assert not root.exists() and snapshot(gone) == before


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_log_that_goes_during_the_read_is_a_log_that_is_not_there(
    root, monkeypatch, identity
):
    place(root, raw(other()))
    step = Step()
    with monkeypatch.context() as patch:
        before_read(patch, "events.ndjson", (root / LOG).unlink)
        assert run(root, RUN, identity, step) == RESULT
    assert step.calls == 1
    assert [journal.identity_of(line) for line in lines(root)] == [identity, identity]


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_log_that_goes_during_the_read_leaves_a_stored_position_beyond_it(
    root, monkeypatch, identity
):
    place(root, raw(other()))
    store(root, at(1))
    before = snapshot(root)
    with monkeypatch.context() as patch:
        before_read(patch, "events.ndjson", (root / LOG).unlink)
        failure = answered(
            root, INVALID, events.PositionBeyondLogError, identity, LOG, once=True
        )
    assert failure.message == (
        f"{LOG}: position 1 is beyond the end of the log, complete lines: 0"
    )
    del before[LOG]
    assert snapshot(root) == before


def log_gone(root):
    return FileNotFoundError(2, "No such file or directory", str(root / LOG))


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_log_that_goes_in_both_reads_of_one_call_is_a_log_that_is_not_there(
    root, monkeypatch, identity
):
    place(root, raw(started(identity), ended(identity, 1, result={})))
    step = Step()
    with monkeypatch.context() as patch:
        fail_read(patch, "read_bytes", "events.ndjson", log_gone(root))
        assert run(root, RUN, identity, step) == RESULT
    assert step.calls == 1
    assert len(lines(root)) == 4


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_log_that_goes_in_both_reads_leaves_a_stored_position_beyond_it(
    root, monkeypatch, identity
):
    place(root, raw(other()))
    store(root, at(1))
    before = snapshot(root)
    with monkeypatch.context() as patch:
        fail_read(patch, "read_bytes", "events.ndjson", log_gone(root))
        failure = answered(root, INVALID, events.PositionBeyondLogError, identity, LOG)
    assert failure.message == (
        f"{LOG}: position 1 is beyond the end of the log, complete lines: 0"
    )
    assert snapshot(root) == before


@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_data_root_that_was_gone_at_the_first_read_only_is_read_again(
    root, monkeypatch, identity
):
    place(
        root, raw(started(identity), ended(identity, 1, result={"example_member": 2}))
    )
    real, calls = events.read, []

    def read(data_root, run_id, position=0):
        calls.append(position)
        if len(calls) == 1:
            raise FileNotFoundError(f"data root is not an existing directory: {root}")
        return real(data_root, run_id, position)

    step = Step()
    with monkeypatch.context() as patch:
        patch.setattr(events, "read", read)
        assert run(root, RUN, identity, step) == {"example_member": 2}
    assert (step.calls, calls) == (0, [0, 0])


# --- no situation: what the lookup does not answer with one of the four kinds ---


@pytest.mark.parametrize("identity", [ID, EARLIER, NO_ROUND])
@pytest.mark.parametrize("content", [None, b"", raw(other())[:-1], b"\xff torn"])
def test_a_missing_an_empty_and_a_torn_log_are_no_situation(root, identity, content):
    if content is not None:
        place(root, content)
    step = Step()
    assert run(root, RUN, identity, step) == RESULT
    assert step.calls == 1
    assert len(lines(root)) == 2


CLASSES_OF_THE_ROWS = [
    OSError("example"),
    FileNotFoundError(2, "No such file or directory"),
    NotADirectoryError(20, "Not a directory"),
    PermissionError(13, "Permission denied"),
    run_journal.MissingStateError(f"{STATE}: is missing"),
    run_state.InvalidStateError(f"{STATE}: example"),
    run_state.UnsupportedVersionError(f"{STATE}: example"),
    events.CorruptEventsError(f"{LOG}: line 1: is damaged"),
    events.PositionBeyondLogError(f"{LOG}: position 1 is beyond"),
    events.UnsupportedVersionError(f"{LOG}: line 1: example"),
    journal.JournalError("line 1: example"),
]
of_each_row = pytest.mark.parametrize(
    "error", CLASSES_OF_THE_ROWS, ids=lambda error: type(error).__qualname__
)


@of_each_row
@pytest.mark.parametrize("identity", [ID, EARLIER])
def test_a_class_of_a_row_out_of_the_step_passes_through_and_leaves_it_open(
    root, error, identity
):
    step = Step(error)
    with pytest.raises(type(error)) as caught:
        run(root, RUN, identity, step)
    assert caught.value is error
    assert step.calls == 1
    assert list(map(without_time, lines(root))) == [without_time(started(identity))]
    assert_open_and_not_run(root, identity)


@of_each_row
def test_a_class_of_a_row_out_of_before_start_passes_through(root, error):
    snap = snapshot(root)
    before, step = Before(root, error), Step()
    with pytest.raises(type(error)) as caught:
        prepared(root, step, before)
    assert caught.value is error
    assert (before.calls, step.calls) == (1, 0)
    assert snapshot(root) == snap


@of_each_row
@pytest.mark.parametrize("kind", ["step_started", "step_ended"])
def test_a_class_of_a_row_out_of_an_append_passes_through(
    root, monkeypatch, error, kind
):
    real = events.append

    def append(data_root, run_id, line_kind, data, **numbers):
        if line_kind == kind:
            raise error
        return real(data_root, run_id, line_kind, data, **numbers)

    step = Step()
    with monkeypatch.context() as patch:
        patch.setattr(events, "append", append)
        with pytest.raises(type(error)) as caught:
            run(root, RUN, ID, step)
    assert caught.value is error
    assert step.calls == (kind == "step_ended")


# --- the same request again (ADR-0019 decision 3) ---


def write_the_state(root):
    store(root)


def drop_the_damaged_line(root):
    place(root, raw(other()))


def write_the_missing_lines(root):
    place(root, raw(other(), other(1)))


AGAIN = {
    "no-state": (lambda root: (root / STATE).unlink(), MISSING, write_the_state),
    "invalid-state": (lambda root: place(root, b"{", STATE), INVALID, write_the_state),
    "damaged-line": (
        lambda root: place(root, raw(other()) + b"not a line\n"),
        INVALID,
        drop_the_damaged_line,
    ),
    "position-beyond-the-log": (
        lambda root: store(root, at(2)),
        INVALID,
        write_the_missing_lines,
    ),
}


@pytest.mark.parametrize("identity", [ID, EARLIER])
@pytest.mark.parametrize("case", list(AGAIN))
def test_the_same_request_again_runs_once_the_situation_holds_no_longer(
    root, identity, case
):
    damage, kind, remove = AGAIN[case]
    damage(root)
    step = Step()
    for _ in range(2):
        with pytest.raises(tools.ToolFailure) as caught:
            run(root, RUN, identity, step)
        assert caught.value.kind == kind
    assert step.calls == 0
    remove(root)
    held = len(lines(root))
    assert run(root, RUN, identity, step) == RESULT
    assert run(root, RUN, identity, step) == RESULT
    assert step.calls == 1
    assert [journal.identity_of(line) for line in lines(root)[held:]] == [
        identity,
        identity,
    ]


@pytest.mark.parametrize(
    "run_id", ["", "Run", "a/b", "..", "a" * 65, None, 1, b"run-a"]
)
def test_an_invalid_run_id_is_refused(root, run_id):
    before = snapshot(root)
    step = Step()
    with pytest.raises(layout.InvalidPathValueError):
        run(root, run_id, ID, step)
    assert step.calls == 0
    assert snapshot(root) == before


@pytest.mark.parametrize(
    ("identity", "error"),
    [
        (None, journal.JournalError),
        (tuple(ID), journal.JournalError),
        ((STEP, 1), journal.JournalError),
        (Identity("Bad Step", 1), journal.JournalError),
        (Identity(STEP, 0), journal.JournalError),
        (Identity(STEP, True), journal.JournalError),
        (Identity(STEP, MAX + 1), journal.JournalError),
        (Identity(STEP, 1, -1), events.InvalidEventError),
        (Identity(STEP, 1, None, 1), events.InvalidEventError),
        (Identity(STEP, 1, 0, None, 1), events.InvalidEventError),
        (Identity(STEP, 1, 0, 0), events.InvalidEventError),
    ],
)
def test_an_invalid_identity_is_refused(root, identity, error):
    assert_refused(root, error, identity)


@pytest.mark.parametrize("step", [None, (SPEND, RESULT), "step", 1])
def test_a_step_that_is_not_callable_is_refused(root, step):
    before = snapshot(root)
    with pytest.raises(TypeError, match="step must be callable"):
        run(root, RUN, ID, step)
    assert snapshot(root) == before


class Pair(tuple):
    pass


class Spend(dict):
    pass


DEEP = []
for _ in range(600):
    DEEP = [DEEP]
CYCLE = {}
CYCLE["example_member"] = CYCLE
UNHOLDABLE = {
    "nothing returned": None,
    "a list": [SPEND, RESULT],
    "a tuple of three": (SPEND, RESULT, None),
    "a tuple of one": (RESULT,),
    "a subclass of tuple": Pair((SPEND, RESULT)),
    "a result alone": RESULT,
    "no spend": (None, RESULT),
    "a spend that is a list": ([], RESULT),
    "a spend of a subclass": (Spend(SPEND), RESULT),
    "a negative amount": ({AXIS: -1}, RESULT),
    "a fractional amount": ({AXIS: 1.0}, RESULT),
    "a bool amount": ({AXIS: True}, RESULT),
    "an amount too large": ({AXIS: MAX + 1}, RESULT),
    "an axis that is no name": ({"Bad Axis": 1}, RESULT),
    "an axis that is no str": ({1: 1}, RESULT),
    "no result": (SPEND, None),
    "a result that is a list": (SPEND, [RESULT]),
    "a result with NaN": (SPEND, {"example_member": float("nan")}),
    "a result with an infinity": (SPEND, {"example_member": [float("inf")]}),
    "a result with a set": (SPEND, {"example_member": {1}}),
    "a result with a tuple": (SPEND, {"example_member": (1, 2)}),
    "a result with a member name that is no str": (SPEND, {1: 2}),
    "a result that holds itself": (SPEND, CYCLE),
    "a result nested too deeply to copy": (SPEND, {"example_member": DEEP}),
    "a failure kind that is no name": StepFailed(SPEND, "Bad Kind", "no outcome"),
    "a failure kind that is no str": StepFailed(SPEND, None, "no outcome"),
    "a failure message that is no str": StepFailed(SPEND, "example_failure", 5),
    "a failure without spend": StepFailed(None, "example_failure", "no outcome"),
    "a failure with a negative amount": StepFailed(
        {AXIS: -1}, "example_failure", "no outcome"
    ),
}


@pytest.mark.parametrize("outcome", UNHOLDABLE.values(), ids=UNHOLDABLE.keys())
def test_an_outcome_the_end_line_cannot_hold_appends_no_line_and_leaves_the_step_open(
    root, outcome
):
    step = Step(outcome)
    with pytest.raises(InvalidOutcomeError) as caught:
        run(root, RUN, ID, step)
    assert type(caught.value) is InvalidOutcomeError
    assert caught.value.__cause__ is None
    assert step.calls == 1
    assert list(map(without_time, lines(root))) == [without_time(started(ID))]
    assert events.read(root, RUN).torn_tail == 0
    run_journal.current(root, RUN)
    assert_open_and_not_run(root)


@pytest.mark.parametrize("depth", range(440, 520))
def test_a_result_is_refused_or_answered_equal_whatever_its_depth(root, depth):
    nested = []
    for _ in range(depth):
        nested = [nested]
    try:
        first = run(root, RUN, ID, Step((SPEND, {"example_member": nested})))
    except InvalidOutcomeError:
        assert_open_and_not_run(root)
        return
    step = Step()
    assert run(root, RUN, ID, step) == first
    assert step.calls == 0


def test_the_message_of_an_invalid_outcome_names_the_member(root):
    with pytest.raises(InvalidOutcomeError, match=r"data\.spend\.example_axis"):
        run(root, RUN, ID, Step(({AXIS: -1}, RESULT)))
    with pytest.raises(InvalidOutcomeError, match=r"data\.failure\.kind"):
        run(root, RUN, EARLIER, failed(kind="Bad Kind"))
    with pytest.raises(
        InvalidOutcomeError, match=r"pair \(spend, result\), got NoneType"
    ):
        run(root, RUN, NO_ROUND, Step(None))
    with pytest.raises(InvalidOutcomeError, match="nested too deeply to copy"):
        run(root, RUN, LATER, Step((SPEND, {"example_member": DEEP})))


def test_the_checks_come_in_the_order_run_id_identity_step_data_root(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(layout.InvalidPathValueError):
        run(missing, "Bad Run", None, None)
    with pytest.raises(journal.JournalError):
        run(missing, RUN, None, None)
    with pytest.raises(TypeError):
        run(missing, RUN, ID, None)
    with pytest.raises(tools.ToolFailure) as caught:
        run(missing, RUN, ID, Step())
    assert caught.value.kind == MISSING
    assert type(caught.value.__cause__) is FileNotFoundError
    with pytest.raises(tools.ToolFailure) as caught:
        run(tmp_path, RUN, ID, Step())
    assert caught.value.kind == MISSING
    assert type(caught.value.__cause__) is run_journal.MissingStateError
    assert snapshot(tmp_path) == {}


def test_no_state_is_kept_between_calls(root):
    assert journaled_step.run(root, RUN, ID, Step()) == RESULT
    (root / LOG).unlink()
    step = Step(({}, {"example_member": 2}))
    assert journaled_step.run(root, RUN, ID, step) == {"example_member": 2}
    assert step.calls == 1


# --- run_prepared: the place between the lookup and the start line (ADR-0016 decision 2) ---


class Before:
    """What is called before the start line: it counts and records the log it sees."""

    def __init__(self, root, error=None):
        self.root, self.error = root, error
        self.calls, self.seen = 0, None

    def __call__(self):
        self.calls += 1
        log = self.root / LOG
        self.seen = log.read_bytes() if log.exists() else None
        if self.error is not None:
            raise self.error
        return "not used"


def prepared(root, step, before, identity=ID):
    return journaled_step.run_prepared(root, RUN, identity, step, before_start=before)


def test_the_signature_of_run_prepared():
    parameters = inspect.signature(journaled_step.run_prepared).parameters
    assert list(parameters) == [*inspect.signature(run).parameters, "before_start"]
    assert parameters["before_start"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["before_start"].default is inspect.Parameter.empty


def test_before_start_is_called_once_before_the_start_line_exists(root):
    before, step = Before(root), Step(root=root)
    assert prepared(root, step, before) == RESULT
    assert (before.calls, step.calls) == (1, 1)
    assert before.seen is None
    seen = [json.loads(line) for line in step.seen.splitlines()]
    assert list(map(without_time, seen)) == [without_time(started(ID))]
    assert list(map(without_time, lines(root))) == [
        without_time(started(ID)),
        without_time(ended(ID, 7, result=RESULT)),
    ]


def test_run_prepared_writes_the_lines_run_writes(tmp_path):
    logs = []
    for name in ("plain", "prepared"):
        path = tmp_path / name
        store(path)
        place(path, raw(other()))
        before = Before(path)
        if name == "plain":
            assert run(path, RUN, ID, Step()) == RESULT
        else:
            assert prepared(path, Step(), before) == RESULT
            assert before.seen == raw(other())
        logs.append(list(map(without_time, lines(path))))
    assert logs[0] == logs[1]
    assert len(logs[0]) == 3


def test_before_start_comes_after_the_lookup_and_before_the_append(root, monkeypatch):
    order = []
    real_state, real_append = journal.step_state, events.append

    def step_state(*args):
        order.append("step_state")
        return real_state(*args)

    def append(data_root, run_id, kind, data, **numbers):
        order.append(kind)
        return real_append(data_root, run_id, kind, data, **numbers)

    monkeypatch.setattr(journal, "step_state", step_state)
    monkeypatch.setattr(events, "append", append)

    def step():
        order.append("step")
        return SPEND, RESULT

    def before():
        order.append("before_start")

    assert prepared(root, step, before) == RESULT
    assert order == [
        "step_state",
        "step_state",
        "before_start",
        "step_started",
        "step",
        "step_state",
        "step_ended",
    ]
    del order[:]
    assert prepared(root, step, before) == RESULT
    assert order == ["step_state", "step_state"]


@pytest.mark.parametrize(
    "content,expected",
    [
        (raw(started(ID), ended(ID, 7, result=RESULT)), None),
        (raw(started(ID), ended(ID, 2, failure=FAILURE)), FAILURE["kind"]),
        (raw(started(ID)), KIND_STEP_OPEN),
    ],
    ids=["ended-result", "ended-failure", "open"],
)
def test_before_start_is_not_called_for_an_ended_or_an_open_identity(
    root, content, expected
):
    place(root, content)
    snap = snapshot(root)
    before, step = Before(root, RuntimeError("must not be called")), Step()
    if expected is None:
        assert prepared(root, step, before) == RESULT
    else:
        with pytest.raises(tools.ToolFailure) as caught:
            prepared(root, step, before)
        assert caught.value.kind == expected
    assert (before.calls, step.calls) == (0, 0)
    assert snapshot(root) == snap


@pytest.mark.parametrize(
    "error",
    [
        tools.ToolFailure("example_failure", "not prepared"),
        tools.ToolFailure(KIND_STEP_OPEN, "a reserved kind"),
        RuntimeError("died"),
        KeyboardInterrupt(),
        SystemExit(9),
    ],
    ids=["tool-failure", "reserved-kind", "exception", "interrupt", "exit"],
)
def test_what_before_start_raises_passes_through_and_leaves_no_line(root, error):
    snap = snapshot(root)
    before, step = Before(root, error), Step()
    with pytest.raises(type(error)) as caught:
        prepared(root, step, before)
    assert caught.value is error
    assert (before.calls, step.calls) == (1, 0)
    assert snapshot(root) == snap
    again = Before(root)
    assert prepared(root, step, again) == RESULT
    assert (again.calls, step.calls) == (1, 1)
    assert len(lines(root)) == 2


@pytest.mark.parametrize("before", [None, "before", 1, (SPEND, RESULT)])
def test_a_before_start_that_is_not_callable_is_refused_before_any_file_is_read(
    tmp_path, before
):
    missing = tmp_path / "missing"
    with pytest.raises(TypeError, match="before_start must be callable"):
        prepared(missing, Step(), before)
    with pytest.raises(TypeError, match="step must be callable"):
        prepared(missing, None, before)
    with pytest.raises(journal.JournalError):
        prepared(missing, None, before, identity=None)
    with pytest.raises(layout.InvalidPathValueError):
        journaled_step.run_prepared(missing, "Bad Run", None, None, before_start=before)
    with pytest.raises(TypeError):
        journaled_step.run_prepared(missing, RUN, ID, Step())
    with pytest.raises(TypeError):
        journaled_step.run_prepared(missing, RUN, ID, Step(), Before(missing))
    assert snapshot(tmp_path) == {}


def test_an_answer_of_the_lookup_comes_before_before_start_is_called(tmp_path, root):
    for path, error in (
        (tmp_path / "missing", FileNotFoundError),
        (tmp_path, run_journal.MissingStateError),
    ):
        before, step = Before(path), Step()
        with pytest.raises(tools.ToolFailure) as caught:
            prepared(path, step, before)
        assert caught.value.kind == MISSING
        assert type(caught.value.__cause__) is error
        assert (before.calls, step.calls) == (0, 0)
    place(root, b"not a line\n")
    before = Before(root)
    with pytest.raises(tools.ToolFailure) as caught:
        prepared(root, Step(), before)
    assert caught.value.kind == INVALID
    assert before.calls == 0


def test_a_failed_start_line_after_before_start_does_not_call_the_step(
    root, monkeypatch
):
    def append(*args, **numbers):
        raise OSError("example failure of the append")

    before, step = Before(root), Step()
    with monkeypatch.context() as patch:
        patch.setattr(events, "append", append)
        with pytest.raises(OSError, match="example failure"):
            prepared(root, step, before)
    assert (before.calls, step.calls) == (1, 0)
    assert prepared(root, step, before) == RESULT
    assert (before.calls, step.calls) == (2, 1)
