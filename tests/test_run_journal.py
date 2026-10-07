import inspect
import json
from pathlib import Path

import pytest

from hilclaw import events, journal, keys, layout, run_state
from hilclaw.journal import (
    EMPTY,
    Identity,
    Problem,
    Report,
    SpendView,
    State,
    StepState,
)
from hilclaw.run_journal import (
    Current,
    MissingStateError,
    current,
    read_state,
    step_state,
)

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

# The Example of ADR-0012, as written in the record.
START = (
    b'{"schema_version": 1, "round": 0, "budget_spent":'
    b' {"totals": {}, "position": 0, "open_steps": []}}\n'
)
AFTER = (
    b'{"schema_version": 1, "round": 4, "budget_spent": {"totals": {"example_axis": 7},'
    b' "position": 3, "open_steps": [{"round": 3, "candidate": 1, "attempt": 1,'
    b' "step": "example_step", "execution": 1}]}}\n'
)
OPEN = Identity(STEP, 1, 3, 1, 1)
DONE = Identity(STEP, 1, 3, 2, 1)
AFTER_VIEW = SpendView({AXIS: 7}, 3, frozenset({OPEN}))

# The log that Example describes: the two lines of the Example of ADR-0011 and one start line.
EXAMPLE_LOG = (
    b'{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "step_started",'
    b' "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:04:10Z", "kind": "step_ended",'
    b' "round": 3, "candidate": 2, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1,'
    b' "spend": {"example_axis": 7}, "result": {"example_member": 1}}}\n'
    b'{"schema_version": 1, "time": "2026-01-01T00:05:00Z", "kind": "step_started",'
    b' "round": 3, "candidate": 1, "attempt": 1,'
    b' "data": {"step": "example_step", "execution": 1}}\n'
)

FAILURE = {"kind": "example_failure", "message": "no outcome"}
CALLS = {
    "read_state": read_state,
    "current": current,
    "step_state": lambda root, run: step_state(root, run, OPEN),
}
BOTH_FILES = {name: CALLS[name] for name in ("current", "step_state")}


def event(kind, data, identity=None):
    numbers = {} if identity is None else identity._asdict()
    numbers = {name: numbers[name] for name in NUMBERS if numbers.get(name) is not None}
    return {"schema_version": 1, "time": TIME, "kind": kind, **numbers, "data": data}


def started(identity):
    return event(
        "step_started",
        {"step": identity.step, "execution": identity.execution},
        identity,
    )


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
    return path


def place(root, content, relative=STATE):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def store(root, view=EMPTY, round=0, others=None, run=RUN):
    return place(root, run_state.dump(round, view, others), f"runs/{run}/STATE.json")


def at(position):
    return SpendView({}, position, frozenset())


def snapshot(tmp_path):
    return {
        path.relative_to(tmp_path).as_posix(): (
            (path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else None
        )
        for path in tmp_path.rglob("*")
    }


def link(path, target):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


# A log of several steps: lines of another kind, a failure, an end without a start, an open step.
STEPS = [
    other(),
    started(Identity(STEP, 1, 0)),
    ended(Identity(STEP, 1, 0), 5),
    started(Identity(STEP, 1, 1, 1, 1)),
    other(1),
    started(Identity(STEP, 1, 1, 2, 1)),
    ended(Identity(STEP, 1, 1, 1, 1), 2, failure=FAILURE),
    ended(Identity("other_step", 1), 11),
    started(Identity(STEP, 2, 1, 2, 1)),
    ended(Identity(STEP, 1, 1, 2, 1), 0),
]


# --- happy ---


def test_signatures_and_types():
    assert list(inspect.signature(read_state).parameters) == ["data_root", "run_id"]
    assert list(inspect.signature(current).parameters) == ["data_root", "run_id"]
    assert list(inspect.signature(step_state).parameters) == [
        "data_root",
        "run_id",
        "identity",
    ]
    assert Current._fields == ("state", "view", "reports", "torn_tail")
    assert not issubclass(MissingStateError, run_state.InvalidStateError)
    assert not issubclass(MissingStateError, OSError)


def test_read_state_gives_the_example_of_adr_0012(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)

    state = read_state(root, RUN)

    assert type(state) is run_state.RunState
    assert state == run_state.RunState(4, AFTER_VIEW, {})
    assert state == run_state.parse(AFTER)


def test_read_state_at_the_start_of_a_run(root):
    place(root, START)

    assert read_state(root, RUN) == run_state.RunState(0, EMPTY, {})


def test_current_from_the_start_state_equals_the_fold_of_the_whole_log(root):
    place(root, START)
    place(root, EXAMPLE_LOG, LOG)

    result = current(root, RUN)

    assert type(result) is Current
    assert result.state == run_state.RunState(0, EMPTY, {})
    assert result.view == AFTER_VIEW
    assert result.view == journal.fold(events.read(root, RUN).events)[0]
    assert result.reports == ()
    assert result.torn_tail == 0


def test_current_at_the_stored_position_gives_the_stored_view(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)

    result = current(root, RUN)

    assert result == Current(run_state.RunState(4, AFTER_VIEW, {}), AFTER_VIEW, (), 0)
    assert type(result.view) is SpendView


def test_lines_appended_after_the_stored_position_are_folded(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)
    numbers = {"round": 3, "candidate": 2, "attempt": 1}
    events.append(root, RUN, "example_kind", {})
    events.append(root, RUN, "step_started", {"step": STEP, "execution": 2}, **numbers)
    data = {
        "step": STEP,
        "execution": 2,
        "spend": {AXIS: 4, "other_axis": 0},
        "result": {},
    }
    events.append(root, RUN, "step_ended", data, **numbers)

    result = current(root, RUN)

    assert result.state.budget_spent == AFTER_VIEW
    assert result.view == SpendView({AXIS: 11, "other_axis": 0}, 6, frozenset({OPEN}))
    assert result.reports == ()


@pytest.mark.parametrize("prefix", range(len(STEPS) + 1))
def test_replay_from_every_prefix_gives_the_view_of_the_whole_log(root, prefix):
    whole, _ = journal.fold(STEPS)
    stored, _ = journal.fold(STEPS[:prefix])
    store(root, stored, round=prefix)
    place(root, raw(*STEPS), LOG)

    result = current(root, RUN)

    assert result.view == whole
    assert result.view.position == len(STEPS)
    assert result.state.budget_spent == stored
    assert result.state.round == prefix


def test_an_open_step_of_the_stored_view_ends_in_the_tail(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG + raw(ended(OPEN, 5, result={"example_member": 2})), LOG)

    result = current(root, RUN)

    assert result.view == SpendView({AXIS: 12}, 4, frozenset())
    assert result.reports == ()
    assert step_state(root, RUN, OPEN) == StepState(
        State.ENDED, {"example_member": 2}, None, {AXIS: 5}
    )


# --- step_state ---


def test_step_state_no_line(root):
    place(root, START)
    place(root, EXAMPLE_LOG, LOG)

    assert step_state(root, RUN, Identity(STEP, 2, 3, 2, 1)) == StepState(State.NO_LINE)
    assert step_state(root, RUN, Identity("other_step", 1)) == StepState(State.NO_LINE)


def test_step_state_open_by_a_start_line_in_the_tail(root):
    place(root, START)
    place(root, EXAMPLE_LOG, LOG)

    assert step_state(root, RUN, OPEN) == StepState(State.OPEN)


def test_step_state_open_in_the_stored_view_with_nothing_in_the_tail(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)

    assert step_state(root, RUN, OPEN) == StepState(State.OPEN)


def test_step_state_ended_with_a_result(root):
    place(root, START)
    place(root, EXAMPLE_LOG, LOG)

    answer = step_state(root, RUN, DONE)

    assert type(answer) is StepState
    assert answer == StepState(State.ENDED, {"example_member": 1}, None, {AXIS: 7})


def test_step_state_ended_with_a_failure(root):
    store(root, at(1))
    place(root, raw(other(), started(DONE), ended(DONE, 3, failure=FAILURE)), LOG)

    assert step_state(root, RUN, DONE) == StepState(
        State.ENDED, None, FAILURE, {AXIS: 3}
    )


def test_step_state_does_not_see_a_step_that_ended_before_the_position(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)

    assert step_state(root, RUN, DONE) == StepState(State.NO_LINE)
    assert journal.step_state(DONE, events.read(root, RUN).events).state is State.ENDED


def test_step_state_answers_from_the_first_end_line_of_the_tail(root):
    store(root, at(1))
    lines = [other(), started(DONE), ended(DONE, 3), ended(DONE, 9, failure=FAILURE)]
    place(root, raw(*lines), LOG)

    assert step_state(root, RUN, DONE) == StepState(State.ENDED, {}, None, {AXIS: 3})


# --- branch ---


def test_reports_of_the_fold_carry_the_line_numbers_of_the_file(root):
    store(root, at(2))
    lines = [other(), other(), ended(DONE, 3), started(OPEN), other(), started(OPEN)]
    place(root, raw(*lines), LOG)

    result = current(root, RUN)

    assert result.reports == (
        Report(3, DONE, Problem.END_NOT_OPEN),
        Report(6, OPEN, Problem.START_REPEATED),
    )
    assert result.view == SpendView({AXIS: 3}, 6, frozenset({OPEN}))


@pytest.mark.parametrize("stored", [START, AFTER], ids=["position 0", "position 3"])
def test_a_torn_tail_is_reported_and_left_in_the_file(tmp_path, root, stored):
    place(root, stored)
    place(root, EXAMPLE_LOG + b'{"schema_version": 1, "ti', LOG)
    before = snapshot(tmp_path)

    result = current(root, RUN)
    answer = step_state(root, RUN, OPEN)

    assert result.torn_tail == 25
    assert result.view == AFTER_VIEW
    assert answer == StepState(State.OPEN)
    assert snapshot(tmp_path) == before


def test_a_torn_tail_that_parses_is_not_folded(root):
    place(root, START)
    place(root, raw(started(DONE)) + raw(ended(DONE, 3))[:-1], LOG)

    result = current(root, RUN)

    assert result.view == SpendView({}, 1, frozenset({DONE}))
    assert result.torn_tail > 0
    assert step_state(root, RUN, DONE) == StepState(State.OPEN)


def test_others_are_returned_as_parsed(root):
    others = {
        "next_action": {"example_member": [1, None, "x"]},
        "phase": "example_phase",
    }
    store(root, AFTER_VIEW, 4, others)
    place(root, EXAMPLE_LOG, LOG)

    assert read_state(root, RUN).others == others
    assert current(root, RUN).state == run_state.RunState(4, AFTER_VIEW, others)
    assert current(root, RUN).view == AFTER_VIEW


def test_any_order_of_members_and_white_space(root):
    content = (
        b'\r\n{\t"budget_spent" : {"open_steps": [], "position": 1,\n "totals": {"example_axis": 2}},'
        b' "example_member": true, "round": 1,\n\n "schema_version": 1}  '
    )
    place(root, content)
    place(root, raw(other(), started(DONE), ended(DONE, 3)), LOG)

    result = current(root, RUN)

    assert result.state == run_state.RunState(
        1, SpendView({AXIS: 2}, 1, frozenset()), {"example_member": True}
    )
    assert result.view == SpendView({AXIS: 5}, 3, frozenset())


def test_a_total_above_the_integer_range(root):
    store(root, SpendView({AXIS: MAX + 5}, 1, frozenset({DONE})))
    place(root, raw(started(DONE), ended(DONE, 7)), LOG)

    result = current(root, RUN)

    assert result.state.budget_spent.totals[AXIS] == MAX + 5
    assert result.view == SpendView({AXIS: MAX + 12}, 2, frozenset())
    assert type(result.view.totals[AXIS]) is int


def test_lines_of_other_kinds_in_the_tail_count_in_the_position(root):
    store(root, at(1))
    place(root, raw(other(), other(1), other(2), started(DONE), other(3)), LOG)

    result = current(root, RUN)

    assert result.view == SpendView({}, 5, frozenset({DONE}))
    assert result.reports == ()


@pytest.mark.parametrize("log", [None, b""], ids=["missing", "empty"])
def test_no_log_and_a_stored_position_0(root, log):
    place(root, START)
    if log is not None:
        place(root, log, LOG)

    assert current(root, RUN) == Current(run_state.RunState(0, EMPTY, {}), EMPTY, (), 0)
    assert step_state(root, RUN, OPEN) == StepState(State.NO_LINE)


def test_a_torn_tail_only_and_a_stored_position_0(root):
    place(root, START)
    place(root, b"torn", LOG)

    assert current(root, RUN) == Current(run_state.RunState(0, EMPTY, {}), EMPTY, (), 4)


def test_data_root_as_str(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)

    assert read_state(str(root), RUN) == read_state(root, RUN)
    assert current(str(root), RUN) == current(root, RUN)
    assert step_state(str(root), RUN, OPEN) == StepState(State.OPEN)


def test_a_relative_data_root_is_not_resolved(root, monkeypatch):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)
    monkeypatch.chdir(root.parent)

    assert current("data", RUN).view == AFTER_VIEW
    with pytest.raises(
        MissingStateError, match=f"^runs/{OTHER_RUN}/STATE.json: is missing$"
    ):
        current(Path("data"), OTHER_RUN)


def test_two_runs_have_two_pairs_of_files(root):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)
    store(root, at(1), round=1, run=OTHER_RUN)
    place(root, raw(other(), started(DONE)), f"runs/{OTHER_RUN}/events.ndjson")

    assert current(root, RUN).view == AFTER_VIEW
    assert current(root, OTHER_RUN).view == SpendView({}, 2, frozenset({DONE}))
    assert step_state(root, RUN, DONE) == StepState(State.NO_LINE)
    assert step_state(root, OTHER_RUN, DONE) == StepState(State.OPEN)
    assert read_state(root, OTHER_RUN).round == 1


@pytest.mark.parametrize("call", CALLS)
def test_nothing_is_created_or_changed(tmp_path, root, call):
    place(root, START)
    place(root, EXAMPLE_LOG, LOG)
    before = snapshot(tmp_path)

    CALLS[call](root, RUN)
    with pytest.raises(MissingStateError):
        CALLS[call](root, OTHER_RUN)

    assert snapshot(tmp_path) == before


def test_results_share_no_state_between_calls(root):
    store(root, AFTER_VIEW, 4, {"example_member": [1]})
    place(root, EXAMPLE_LOG + raw(ended(OPEN, 1, result={"example_member": [2]})), LOG)

    first = current(root, RUN)
    first.state.others["example_member"].append(9)
    answer = step_state(root, RUN, OPEN)
    answer.result["example_member"].append(9)
    answer.spend[AXIS] = 99

    assert current(root, RUN).state.others == {"example_member": [1]}
    assert step_state(root, RUN, OPEN) == StepState(
        State.ENDED, {"example_member": [2]}, None, {AXIS: 1}
    )
    with pytest.raises(TypeError):
        first.view.totals[AXIS] = 0


# --- error / negative: STATE.json ---


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize(
    "present",
    [
        (),
        ("runs/keep",),
        (f"runs/{RUN}/instance.json",),
        (LOG,),
        ("runs",),
        (f"runs/{RUN}",),
    ],
    ids=[
        "no runs",
        "no run directory",
        "another file",
        "a log",
        "runs is a file",
        "run is a file",
    ],
)
def test_a_missing_state_file(tmp_path, root, call, present):
    for relative in present:
        place(root, EXAMPLE_LOG, relative)
    before = snapshot(tmp_path)

    with pytest.raises(MissingStateError, match=f"^{STATE}: is missing$"):
        CALLS[call](root, RUN)

    assert snapshot(tmp_path) == before


INVALID = {
    "empty": b"",
    "not UTF-8": b'{"schema_version": 1, "round": 0, "example_member": "\xff"}',
    "a byte order mark": b"\xef\xbb\xbf" + START,
    "not JSON": b"{",
    "two texts": START + START,
    "not an object": b"[]",
    "a member name twice": START[:-2] + b', "round": 1}\n',
    "no schema_version": b'{"round": 0}',
    "no round": START.replace(b'"round": 0, ', b""),
    "no budget_spent": b'{"schema_version": 1, "round": 0}',
    "a member inside budget_spent": START.replace(
        b'"totals"', b'"offset": 0, "totals"'
    ),
    "a negative position": START.replace(b'"position": 0', b'"position": -1'),
}


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("content", INVALID)
def test_an_invalid_state_file(tmp_path, root, call, content):
    place(root, INVALID[content])
    place(root, EXAMPLE_LOG, LOG)
    before = snapshot(tmp_path)

    with pytest.raises(run_state.InvalidStateError, match=f"^{STATE}: ") as excinfo:
        CALLS[call](root, RUN)

    with pytest.raises(run_state.InvalidStateError) as parsed:
        run_state.parse(INVALID[content])
    assert str(excinfo.value) == f"{STATE}: {parsed.value}"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("version", [0, 2])
def test_a_state_file_of_another_version(root, call, version):
    place(
        root, START.replace(b'"schema_version": 1', b'"schema_version": %d' % version)
    )
    place(root, EXAMPLE_LOG, LOG)

    with pytest.raises(run_state.UnsupportedVersionError) as excinfo:
        CALLS[call](root, RUN)

    assert str(excinfo.value) == f"{STATE}: schema_version: {version} is not supported"
    assert not isinstance(excinfo.value, events.UnsupportedVersionError)
    assert not isinstance(excinfo.value, run_state.InvalidStateError)


@pytest.mark.parametrize("call", CALLS)
def test_a_directory_in_the_place_of_the_state_file(tmp_path, root, call):
    (root / STATE).mkdir(parents=True)
    place(root, EXAMPLE_LOG, LOG)
    before = snapshot(tmp_path)

    with pytest.raises(
        run_state.InvalidStateError, match=f"^{STATE}: is not a regular file$"
    ):
        CALLS[call](root, RUN)

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize("target", ["a file", "nothing"])
def test_a_symbolic_link_in_the_place_of_the_state_file(tmp_path, root, call, target):
    elsewhere = tmp_path / "elsewhere.json"
    if target == "a file":
        elsewhere.write_bytes(START)
    link(root / STATE, elsewhere)

    with pytest.raises(
        run_state.InvalidStateError, match=f"^{STATE}: is not a regular file$"
    ):
        CALLS[call](root, RUN)

    assert elsewhere.exists() == (target == "a file")


@pytest.mark.parametrize("call", CALLS)
def test_an_os_error_while_the_state_file_is_read_passes_through(
    root, call, monkeypatch
):
    place(root, START)

    def fail(path):
        raise PermissionError(f"denied: {path.name}")

    monkeypatch.setattr(Path, "read_bytes", fail)

    with pytest.raises(PermissionError, match="denied: STATE.json"):
        CALLS[call](root, RUN)


# --- error / negative: the log ---


@pytest.mark.parametrize("call", BOTH_FILES)
@pytest.mark.parametrize(
    ("log", "lines"),
    [
        (None, 0),
        (b"", 0),
        (EXAMPLE_LOG[: EXAMPLE_LOG.index(b"\n", EXAMPLE_LOG.index(b"\n") + 1) + 1], 2),
        (EXAMPLE_LOG[:-1], 2),
        (b"torn", 0),
    ],
    ids=[
        "missing",
        "empty",
        "one line short",
        "the third line torn",
        "a torn tail only",
    ],
)
def test_a_stored_position_beyond_the_log(tmp_path, root, call, log, lines):
    place(root, AFTER)
    if log is not None:
        place(root, log, LOG)
    before = snapshot(tmp_path)

    with pytest.raises(events.PositionBeyondLogError) as excinfo:
        BOTH_FILES[call](root, RUN)

    assert str(excinfo.value) == (
        f"{LOG}: position 3 is beyond the end of the log, complete lines: {lines}"
    )
    assert isinstance(excinfo.value, events.CorruptEventsError)
    assert snapshot(tmp_path) == before
    assert read_state(root, RUN).budget_spent == AFTER_VIEW


@pytest.mark.parametrize("call", BOTH_FILES)
@pytest.mark.parametrize(
    "damaged",
    [b"{\n", b"\xff\n", b"\n", b'{"schema_version": 1}\n'],
    ids=["not JSON", "not UTF-8", "blank", "no kind"],
)
def test_a_damaged_line_in_the_tail_is_reported(root, call, damaged):
    store(root, at(1))
    place(root, raw(other()) + damaged + raw(started(DONE)), LOG)

    with pytest.raises(
        events.CorruptEventsError, match=f"^{LOG}: line 2: is damaged"
    ) as excinfo:
        BOTH_FILES[call](root, RUN)

    assert not isinstance(excinfo.value, events.PositionBeyondLogError)


@pytest.mark.parametrize("call", BOTH_FILES)
def test_a_line_of_another_version_in_the_tail_is_reported(root, call):
    store(root, at(1))
    place(root, raw(other(), other() | {"schema_version": 2}), LOG)

    with pytest.raises(
        events.UnsupportedVersionError, match=f"^{LOG}: line 2: "
    ) as excinfo:
        BOTH_FILES[call](root, RUN)

    assert not isinstance(excinfo.value, run_state.UnsupportedVersionError)


@pytest.mark.parametrize(
    "before",
    [
        b"{\n",
        b"\xff\n",
        raw(other() | {"schema_version": 2}),
        raw(started(DONE))[:-2] + b"\n",
    ],
    ids=["not JSON", "not UTF-8", "another version", "a cut line"],
)
def test_damage_before_the_stored_position_is_not_seen(root, before):
    store(root, at(1))
    place(root, before + raw(started(DONE), ended(DONE, 3)), LOG)

    assert current(root, RUN).view == SpendView({AXIS: 3}, 3, frozenset())
    assert step_state(root, RUN, DONE).state is State.ENDED


@pytest.mark.parametrize("call", BOTH_FILES)
@pytest.mark.parametrize(
    "data",
    [
        {"step": STEP},
        {"step": STEP, "execution": 0},
        {"step": STEP, "execution": 1, "example_member": 1},
    ],
    ids=["no execution", "execution 0", "an unknown member"],
)
def test_a_malformed_step_line_in_the_tail_is_refused(root, call, data):
    store(root, at(2))
    place(root, raw(other(), other(), started(DONE), event("step_started", data)), LOG)

    with pytest.raises(journal.JournalError, match="^line 4: data") as excinfo:
        BOTH_FILES[call](root, RUN)

    assert not isinstance(excinfo.value, events.InvalidEventError)


def test_a_malformed_end_line_in_the_tail_is_refused(root):
    place(root, START)
    line = ended(DONE, 1)
    line["data"]["failure"] = FAILURE
    place(root, raw(started(DONE), line), LOG)

    with pytest.raises(
        journal.JournalError, match="^line 2: data: must hold exactly one"
    ):
        current(root, RUN)


@pytest.mark.parametrize("call", BOTH_FILES)
def test_a_path_that_is_not_a_regular_file_in_the_place_of_the_log(root, call):
    place(root, START)
    (root / LOG).mkdir()

    with pytest.raises(
        events.CorruptEventsError, match=f"^{LOG}: is not a regular file$"
    ):
        BOTH_FILES[call](root, RUN)

    assert read_state(root, RUN) == run_state.RunState(0, EMPTY, {})


# --- error / negative: arguments ---


@pytest.mark.parametrize("call", CALLS)
@pytest.mark.parametrize(
    "run_id", ["", "Run-A", "../run-a", "a/b", ".", "a" * 65, None, 1, b"run-a"]
)
def test_an_invalid_run_id(tmp_path, root, call, run_id):
    place(root, START)

    with pytest.raises(layout.InvalidPathValueError, match="^run_id: must be"):
        CALLS[call](root, run_id)
    with pytest.raises(layout.InvalidPathValueError, match="^run_id: must be"):
        CALLS[call](tmp_path / "absent", run_id)


@pytest.mark.parametrize("call", CALLS)
def test_a_missing_data_root(tmp_path, call):
    with pytest.raises(
        FileNotFoundError, match="data root is not an existing directory"
    ):
        CALLS[call](tmp_path / "absent", RUN)
    with pytest.raises(
        FileNotFoundError, match="data root is not an existing directory"
    ):
        CALLS[call](str(tmp_path / "absent"), RUN)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("call", CALLS)
def test_a_file_in_the_place_of_the_data_root(tmp_path, call):
    (tmp_path / "data").write_bytes(b"")

    with pytest.raises(
        NotADirectoryError, match="data root is not an existing directory"
    ):
        CALLS[call](tmp_path / "data", RUN)


@pytest.mark.parametrize(
    "identity",
    [
        None,
        STEP,
        (STEP, 1),
        (STEP, 1, None, None, None),
        [STEP, 1],
        {"step": STEP, "execution": 1},
    ],
    ids=repr,
)
def test_step_state_refuses_an_identity_of_another_type_before_any_read(
    tmp_path, root, identity
):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)

    with pytest.raises(journal.JournalError, match="^identity: must be an Identity"):
        step_state(root, RUN, identity)
    with pytest.raises(journal.JournalError, match="^identity: must be an Identity"):
        step_state(tmp_path / "absent", RUN, identity)


@pytest.mark.parametrize(
    ("identity", "error"),
    [
        (Identity("Bad-Step", 1), journal.JournalError),
        (Identity(STEP, 0), journal.JournalError),
        (Identity(STEP, True), journal.JournalError),
        (Identity(STEP, 1, -1), events.InvalidEventError),
        (Identity(STEP, 1, None, 1), events.InvalidEventError),
        (Identity(STEP, 1, 3, None, 1), events.InvalidEventError),
        (Identity(STEP, 1, 3, 0), events.InvalidEventError),
        (Identity(STEP, 1, MAX + 1), events.InvalidEventError),
    ],
    ids=repr,
)
def test_step_state_refuses_invalid_identity_values_before_any_read(
    tmp_path, root, monkeypatch, identity, error
):
    place(root, AFTER)
    place(root, EXAMPLE_LOG, LOG)
    with pytest.raises(error):
        step_state(tmp_path / "absent", RUN, identity)

    def fail(path):
        raise AssertionError(f"read: {path}")

    monkeypatch.setattr(Path, "read_bytes", fail)

    with pytest.raises(error):
        step_state(root, RUN, identity)


def test_step_state_checks_the_run_id_before_the_identity(root):
    with pytest.raises(layout.InvalidPathValueError, match="^run_id: must be"):
        step_state(root, "Run-A", None)


def test_step_state_checks_the_identity_before_a_missing_state_file(root):
    with pytest.raises(journal.JournalError, match="^identity: must be an Identity"):
        step_state(root, RUN, (STEP, 1))
    with pytest.raises(MissingStateError):
        step_state(root, RUN, Identity(STEP, 1))
