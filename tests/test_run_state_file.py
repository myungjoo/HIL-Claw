import inspect
import os
import re
import secrets
import sys
from pathlib import Path

import pytest

from hilclaw import keys, layout, run_state, run_state_file
from hilclaw.journal import EMPTY, Identity, SpendView
from hilclaw.run_journal import MissingStateError, read_state
from hilclaw.run_state_file import replace

# Synthetic values only: no step name, axis or member of a real run.
RUN = "run-a"
OTHER_RUN = "run-b"
STATE = f"runs/{RUN}/STATE.json"
STEP = "example_step"
AXIS = "example_axis"
MAX = keys.MAX_INTEGER
TEMPORARY = re.compile(r"STATE\.json\.[a-z0-9-]{1,64}\.tmp")
LEFTOVER = f"runs/{RUN}/STATE.json.4242-0123456789abcdef.tmp"

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
AFTER_VIEW = SpendView({AXIS: 7}, 3, frozenset({OPEN}))
NEW = run_state.dump(4, AFTER_VIEW)

STEPS = ("creation", "write", "flush", "move")
PREVIOUS = {"first": None, "existing": START}
REFUSED_ROUNDS = [-1, MAX + 1, True, 1.0, "1", None]
REFUSED_VIEWS = [
    None,
    (),
    SpendView({AXIS: -1}, 0, frozenset()),
    SpendView({"Bad Axis": 1}, 0, frozenset()),
    SpendView({}, MAX + 1, frozenset()),
    SpendView({}, 0, frozenset({("x",)})),
    SpendView({}, 0, []),
]
REFUSED_OTHERS = [
    {"schema_version": 1},
    {"round": 1},
    {"budget_spent": {}},
    {"example_member": float("nan")},
    {"example_member": {1}},
    {1: 2},
    [1],
]
REFUSED_VALUES = (
    [(value, EMPTY, None) for value in REFUSED_ROUNDS]
    + [(0, value, None) for value in REFUSED_VIEWS]
    + [(0, EMPTY, value) for value in REFUSED_OTHERS]
)


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


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): (
            path.read_bytes() if path.is_file() else None
        )
        for path in directory.rglob("*")
    }


def temporaries(directory):
    return [
        name for name in snapshot(directory) if TEMPORARY.fullmatch(Path(name).name)
    ]


def link(path, target):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


def held(root):
    path = root / STATE
    return path.read_bytes() if path.is_file() else None


@pytest.fixture
def watch(monkeypatch, root):
    seen = []
    flush, move = os.fsync, os.replace

    def fsync(descriptor):
        found = {name: content for name, content in snapshot(root).items() if content}
        seen.append({"step": "flush", "held": found.pop(STATE, None), "files": found})
        status = os.fstat(descriptor)
        same = [
            name for name in found if os.path.samestat(status, os.stat(root / name))
        ]
        seen[-1].update(descriptor=descriptor, flushed=same)
        return flush(descriptor)

    def replacing(source, target):
        with pytest.raises(OSError):
            os.fstat(seen[-1]["descriptor"])
        content = Path(source).read_bytes()
        seen.append({"step": "move", "held": held(root), "content": content})
        seen[-1].update(source=Path(source), target=Path(target))
        return move(source, target)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "replace", replacing)
    return seen


class Partial:
    def __init__(self, file, error):
        self.file = file
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return self.file.__exit__(*exception)

    def write(self, content):
        self.file.write(content[:7])
        raise self.error


def break_step(monkeypatch, step, error):
    real = open

    def refuse(*arguments, **named):
        raise error

    def creation(file, mode="r", *arguments, **named):
        if "x" not in mode:
            return real(file, mode, *arguments, **named)
        if step == "creation":
            raise error
        return Partial(real(file, mode, *arguments, **named), error)

    if step in ("creation", "write"):
        monkeypatch.setattr("builtins.open", creation)
    else:
        name = {"flush": "fsync", "move": "replace", "unlink": "unlink"}[step]
        monkeypatch.setattr(os, name, refuse)


# --- happy ---


def test_signature_and_public_names():
    names = ["data_root", "run_id", "round", "view", "others"]
    assert list(inspect.signature(replace).parameters) == names
    assert inspect.signature(replace).parameters["others"].default is None
    own = [
        name
        for name, value in vars(run_state_file).items()
        if getattr(value, "__module__", None) == run_state_file.__name__
    ]
    assert own == ["replace"]


@pytest.mark.parametrize("present", ["nothing", "runs", "another file"])
def test_the_first_file_of_a_run(root, present):
    if present == "runs":
        (root / "runs").mkdir()
    if present == "another file":
        place(root, b"", f"runs/{RUN}/events.ndjson")
    before = snapshot(root)

    assert replace(root, RUN, 0, EMPTY) is None

    created = {"runs": None, f"runs/{RUN}": None, STATE: run_state.dump(0, EMPTY)}
    assert snapshot(root) == before | created
    assert read_state(root, RUN) == run_state.RunState(0, EMPTY, {})


def test_an_existing_file_is_replaced_by_the_example_of_adr_0012(root):
    place(root, START)

    assert replace(root, RUN, 4, AFTER_VIEW) is None

    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None, STATE: NEW}
    assert read_state(root, RUN) == run_state.parse(AFTER)
    assert read_state(root, RUN) == run_state.RunState(4, AFTER_VIEW, {})


def test_others_are_written_and_read_back(root):
    others = {"example_member": {"b": [1, None, "x"], "a": 2.5}, "another": True}

    replace(root, RUN, 1, AFTER_VIEW, others)

    assert held(root) == run_state.dump(1, AFTER_VIEW, others)
    assert read_state(root, RUN) == run_state.RunState(1, AFTER_VIEW, others)


def test_a_second_run_is_untouched(root):
    replace(root, OTHER_RUN, 2, AFTER_VIEW, {"example_member": 1})
    other = snapshot(root)

    replace(root, RUN, 0, EMPTY)
    replace(root, RUN, 1, EMPTY)

    kept = {
        name: content for name, content in snapshot(root).items() if RUN not in name
    }
    assert kept == other
    assert read_state(root, OTHER_RUN).round == 2
    assert read_state(root, RUN).round == 1


def test_data_root_as_str_and_as_a_relative_path(root, monkeypatch):
    replace(str(root), RUN, 0, EMPTY)
    monkeypatch.chdir(root.parent)
    replace("data", RUN, 4, AFTER_VIEW)
    replace(Path("data"), OTHER_RUN, 0, EMPTY)

    assert held(root) == NEW
    assert snapshot(root)[f"runs/{OTHER_RUN}/STATE.json"] == run_state.dump(0, EMPTY)
    assert temporaries(root) == []


# --- the steps ---


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
def test_the_final_name_holds_the_previous_content_until_the_move(
    root, watch, previous
):
    if previous is not None:
        place(root, previous)

    replace(root, RUN, 4, AFTER_VIEW)

    flush, move = watch
    assert (flush["step"], move["step"]) == ("flush", "move")
    assert flush["held"] == move["held"] == previous
    assert held(root) == NEW


def test_the_temporary_file_is_whole_and_beside_the_final_one(root, watch):
    place(root, START)

    replace(root, RUN, 4, AFTER_VIEW)

    flush, move = watch
    source = move["source"]
    assert source.parent == root / "runs" / RUN
    assert move["target"] == layout.run_file(root, RUN, "STATE.json")
    assert TEMPORARY.fullmatch(source.name)
    assert source.name not in layout.RUN_FILES
    assert source.name.startswith(f"STATE.json.{os.getpid()}-")
    assert move["content"] == NEW
    assert flush["files"] == {source.relative_to(root).as_posix(): NEW}
    assert flush["flushed"] == list(flush["files"])
    assert temporaries(root) == []


def test_two_replacements_use_two_temporary_names(root, watch):
    replace(root, RUN, 0, EMPTY)
    replace(root, RUN, 0, EMPTY)
    replace(root, OTHER_RUN, 0, EMPTY)

    sources = [entry["source"].name for entry in watch if entry["step"] == "move"]
    assert len(set(sources)) == 3
    assert all(TEMPORARY.fullmatch(name) for name in sources)


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
def test_only_a_new_file_of_the_temporary_name_is_opened(root, monkeypatch, previous):
    if previous is not None:
        place(root, previous)
    real = open
    opened = []

    def spy(file, mode="r", *arguments, **named):
        opened.append((Path(file), mode))
        return real(file, mode, *arguments, **named)

    monkeypatch.setattr("builtins.open", spy)
    replace(root, RUN, 4, AFTER_VIEW)
    monkeypatch.undo()

    ((path, mode),) = opened
    assert mode == "xb"
    assert path.parent == root / "runs" / RUN
    assert TEMPORARY.fullmatch(path.name)


@pytest.mark.skipif(sys.platform == "win32", reason="a read-only file is not replaced")
def test_a_final_file_that_cannot_be_written_is_still_replaced(root):
    place(root, START).chmod(0o444)

    replace(root, RUN, 4, AFTER_VIEW)

    assert held(root) == NEW


# --- branch ---


@pytest.mark.parametrize(
    "previous",
    [
        b"",
        b'{"schema_version": 1, "round": ',
        b'{"schema_version": 2, "example_member": 1}\n',
        run_state.dump(9, AFTER_VIEW, {"example_member": 5, "another": [1]}),
    ],
    ids=["empty", "invalid", "another version", "further members"],
)
def test_the_previous_file_is_not_read_and_nothing_is_carried_over(root, previous):
    place(root, previous)

    replace(root, RUN, 1, EMPTY)

    assert held(root) == run_state.dump(1, EMPTY)
    assert read_state(root, RUN) == run_state.RunState(1, EMPTY, {})
    assert b"example_member" not in held(root)


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("leftover", [NEW[:9], NEW], ids=["partial", "whole"])
def test_a_leftover_is_neither_read_nor_moved_nor_removed(root, previous, leftover):
    place(root, leftover, LEFTOVER)
    if previous is None:
        with pytest.raises(MissingStateError):
            read_state(root, RUN)
    else:
        place(root, previous)
        assert read_state(root, RUN) == run_state.parse(previous)
    before = snapshot(root)

    replace(root, RUN, 2, EMPTY, {"example_member": 1})

    written = run_state.dump(2, EMPTY, {"example_member": 1})
    assert snapshot(root) == before | {STATE: written}
    assert temporaries(root) == [LEFTOVER]
    assert read_state(root, RUN).round == 2


@pytest.mark.parametrize("dangling", [False, True])
def test_a_symbolic_link_under_the_final_name_is_replaced_not_followed(root, dangling):
    target = root.parent / "target.json"
    if not dangling:
        target.write_bytes(AFTER)
    link(root / STATE, target)

    replace(root, RUN, 0, EMPTY)

    assert not (root / STATE).is_symlink()
    assert held(root) == run_state.dump(0, EMPTY)
    assert read_state(root, RUN).round == 0
    assert target.exists() is not dangling
    assert dangling or target.read_bytes() == AFTER


# --- error / negative ---


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS)
def test_a_failed_step_leaves_the_final_name_and_no_temporary_file(
    root, monkeypatch, step, previous
):
    if previous is not None:
        place(root, previous)
    error = OSError(f"{step} refused")
    break_step(monkeypatch, step, error)

    with pytest.raises(OSError) as caught:
        replace(root, RUN, 4, AFTER_VIEW)
    monkeypatch.undo()

    assert caught.value is error
    assert held(root) == previous
    assert temporaries(root) == []
    expected = {"runs": None, f"runs/{RUN}": None}
    assert snapshot(root) == expected | ({} if previous is None else {STATE: previous})


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS[1:])
def test_an_interrupt_removes_the_temporary_file_too(root, monkeypatch, step, previous):
    if previous is not None:
        place(root, previous)
    break_step(monkeypatch, step, KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        replace(root, RUN, 4, AFTER_VIEW)
    monkeypatch.undo()

    assert held(root) == previous
    assert temporaries(root) == []


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
def test_a_temporary_name_in_use_is_an_error_and_that_file_stays(
    root, monkeypatch, previous
):
    if previous is not None:
        place(root, previous)
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * 2 * size)
    name = f"runs/{RUN}/STATE.json.{os.getpid()}-{'0' * 16}.tmp"
    place(root, b"of another writer", name)
    before = snapshot(root)

    with pytest.raises(FileExistsError):
        replace(root, RUN, 4, AFTER_VIEW)

    assert snapshot(root) == before
    assert held(root) == previous


def test_a_removal_that_fails_does_not_hide_the_failure_of_the_step(root, monkeypatch):
    place(root, START)
    error = OSError("move refused")
    break_step(monkeypatch, "move", error)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    with pytest.raises(OSError) as caught:
        replace(root, RUN, 4, AFTER_VIEW)
    monkeypatch.undo()

    assert caught.value is error
    assert held(root) == START
    (leftover,) = temporaries(root)
    assert snapshot(root)[leftover] == NEW


def test_a_temporary_file_removed_by_another_fails_the_move_and_changes_nothing(
    root, monkeypatch
):
    place(root, START)
    move = os.replace

    def removed_first(source, target):
        Path(source).unlink()
        return move(source, target)

    monkeypatch.setattr(os, "replace", removed_first)

    with pytest.raises(FileNotFoundError):
        replace(root, RUN, 4, AFTER_VIEW)

    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None, STATE: START}


@pytest.mark.parametrize("content", [None, b"inner"], ids=["empty", "with a file"])
def test_a_directory_in_the_place_of_the_final_name(root, content):
    (root / STATE).mkdir(parents=True)
    if content is not None:
        place(root, content, f"{STATE}/inner.txt")
    before = snapshot(root)

    with pytest.raises(OSError):
        replace(root, RUN, 0, EMPTY)

    assert snapshot(root) == before
    assert (root / STATE).is_dir()


@pytest.mark.parametrize("name", ["runs", f"runs/{RUN}"])
def test_a_file_in_the_place_of_a_directory_above_the_final_name(root, name):
    place(root, b"a file", name)
    before = snapshot(root)

    with pytest.raises(OSError):
        replace(root, RUN, 0, EMPTY)

    assert snapshot(root) == before


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_missing_data_root_is_not_created(tmp_path, as_type):
    with pytest.raises(FileNotFoundError, match="data root"):
        replace(as_type(tmp_path / "absent"), RUN, 0, EMPTY)

    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_file_in_the_place_of_the_data_root(tmp_path, as_type):
    place(tmp_path, b"a file", "data")

    with pytest.raises(NotADirectoryError, match="data root"):
        replace(as_type(tmp_path / "data"), RUN, 0, EMPTY)

    assert snapshot(tmp_path) == {"data": b"a file"}


@pytest.mark.parametrize("run_id", ["", "Run", "a/b", "..", "a" * 65, 7, None])
def test_an_invalid_run_id_creates_nothing(root, run_id):
    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        replace(root, run_id, 0, EMPTY)

    assert snapshot(root) == {}


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("values", REFUSED_VALUES)
def test_values_that_dump_refuses_create_and_change_nothing(root, values, previous):
    if previous is not None:
        place(root, previous)
    before = snapshot(root)
    with pytest.raises(run_state.InvalidStateError):
        run_state.dump(*values)

    with pytest.raises(run_state.InvalidStateError):
        replace(root, RUN, *values)

    assert snapshot(root) == before


def test_the_order_of_the_checks(tmp_path):
    absent = tmp_path / "absent"
    file = place(tmp_path, b"a file", "file")

    with pytest.raises(layout.InvalidPathValueError):
        replace(absent, "Run", -1, None)
    with pytest.raises(run_state.InvalidStateError):
        replace(absent, RUN, -1, EMPTY)
    with pytest.raises(run_state.InvalidStateError):
        replace(file, RUN, 0, EMPTY, {"round": 1})
    with pytest.raises(FileNotFoundError):
        replace(absent, RUN, 0, EMPTY)
    with pytest.raises(NotADirectoryError):
        replace(file, RUN, 0, EMPTY)

    assert snapshot(tmp_path) == {"file": b"a file"}
