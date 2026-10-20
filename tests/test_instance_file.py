import codecs
import inspect
import io
import json
import os
import re
import secrets
from pathlib import Path

import pytest

from hilclaw import instance, instance_file, keys, layout
from hilclaw.instance import (
    InvalidInstanceError,
    MissingInstanceError,
    UnsupportedVersionError,
)
from hilclaw.instance_file import NameTakenError, WrittenFormError, write

# Synthetic values only: no record, key, member or commit of a real run, and no default.
RUN = "run-a"
OTHER_RUN = "run-b"
FILE = f"runs/{RUN}/instance.json"
TEMPORARY = re.compile(r"instance\.json\.[a-z0-9-]{1,64}\.tmp")
LEFTOVER = f"runs/{RUN}/instance.json.4242-0123456789abcdef.tmp"
REMOVE = object()
COMMIT = "0123456789abcdef0123456789abcdef01234567"
STEPS = ("creation", "write", "flush", "link")


def record(accelerator="acc_a"):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }


def doc(profile=None, **changes):
    profile = record() if profile is None else profile
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
    }
    for name, value in changes.items():
        if value is REMOVE:
            del made[name]
        else:
            made[name] = value
    return made


def written(document):
    return json.dumps(document, indent=2).encode() + b"\n"


def text(*members):
    return ("{" + ", ".join(members) + "}\n").encode()


VERSION = '"schema_version": 1'
SECTION = f'"hw_profile": {json.dumps(doc()["hw_profile"])}'
MINIMAL = written(doc())
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 3, "k": 5, "n": 7},
    "dtype": "dtype_a",
    "layout": "layout_a",
    "label": "example",
}
FULL = written(
    doc(
        tolerance={"rtol": 0.25, "atol": 3.0},
        source_commit=COMMIT,
        n_max=7,
        candidates_per_round=3,
        op_signature={"key": keys.op_signature_key(OP).name, "record": OP},
        round_budget=6,
        wall_clock_budget_s=754,
        owner="example-owner",
        project="example-project",
        draws=9,
        objective={"objectives": [{"type": "latency_minimisation"}], "constraints": []},
        coder_model="claude-example-1-2",
        example_member={"b": [1, None, "x"], "a": 2.5},
    )
)
OTHER = written(doc(record("acc_b")))
UNUSUAL = (
    b'\n\t {"example_member": "a\\r\\nb" ,\n\n'
    + SECTION.encode()
    + b',"schema_version"\t:1 }\n\n'
)
CONTENTS = {"required members only": MINIMAL, "every member": FULL}
PREVIOUS = {"free": None, "taken": OTHER}
TAKEN = {
    "other bytes": OTHER,
    "equal bytes": MINIMAL,
    "invalid": MINIMAL[:20],
    "empty": b"",
    "directory": None,
    "link to a file": None,
    "dangling link": None,
}
REFUSED = {
    "str": (MINIMAL.decode(), TypeError),
    "bytearray": (bytearray(MINIMAL), TypeError),
    "dict": (doc(), TypeError),
    "None": (None, TypeError),
    "empty": (b"", InvalidInstanceError),
    "partial": (MINIMAL[:20], InvalidInstanceError),
    "byte order mark": (codecs.BOM_UTF8 + MINIMAL, InvalidInstanceError),
    "member name twice": (text(VERSION, VERSION, SECTION), InvalidInstanceError),
    "version 0": (written(doc(schema_version=0)), UnsupportedVersionError),
    "version 2": (written(doc(schema_version=2)), UnsupportedVersionError),
    "no hw_profile": (written(doc(hw_profile=REMOVE)), InvalidInstanceError),
    "tolerance": (
        written(doc(tolerance={"rtol": -1, "atol": 0})),
        InvalidInstanceError,
    ),
    "source_commit": (written(doc(source_commit="abc")), InvalidInstanceError),
    "n_max": (written(doc(n_max=4)), InvalidInstanceError),
    "candidates_per_round": (
        written(doc(candidates_per_round=0)),
        InvalidInstanceError,
    ),
    "op_signature": (
        written(doc(op_signature={"key": "gemm-0123456789abcdef", "record": OP})),
        InvalidInstanceError,
    ),
    "round_budget": (written(doc(round_budget=0)), InvalidInstanceError),
    "wall_clock_budget_s": (
        written(doc(wall_clock_budget_s=0)),
        InvalidInstanceError,
    ),
    "owner": (written(doc(owner="")), InvalidInstanceError),
    "project": (
        written(doc(owner="example-owner", project="example\nproject")),
        InvalidInstanceError,
    ),
    "draws": (written(doc(draws=0)), InvalidInstanceError),
    "objective": (
        written(doc(objective={"objectives": [], "constraints": []})),
        InvalidInstanceError,
    ),
    "coder_model": (written(doc(coder_model="opus")), InvalidInstanceError),
    "no final line feed": (MINIMAL[:-1], WrittenFormError),
    "CRLF line ends": (MINIMAL.replace(b"\n", b"\r\n"), WrittenFormError),
    "one carriage return": (b"\r" + MINIMAL, WrittenFormError),
}


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


@pytest.fixture(autouse=True)
def no_replacing_step(monkeypatch):
    def refuse(*arguments, **named):
        pytest.fail("a replacing step was called")

    monkeypatch.setattr(os, "replace", refuse)
    monkeypatch.setattr(os, "rename", refuse)


def place(root, content, relative=FILE):
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


def kind(path):
    if path.is_symlink():
        return ("link", os.readlink(path))
    return ("directory" if path.is_dir() else "file", None)


def take(root, how):
    path = root / FILE
    target = root.parent / "target.json"
    if how == "directory":
        path.mkdir(parents=True)
    elif how == "link to a file":
        target.write_bytes(OTHER)
        link(path, target)
    elif how == "dangling link":
        link(path, target)
    else:
        place(root, TAKEN[how])


def found(root):
    try:
        return instance.read(root, RUN)
    except MissingInstanceError:
        return None


def spy(monkeypatch):
    opened = []
    real, low = open, os.open

    def high(file, mode="r", *arguments, **named):
        opened.append((Path(file), mode))
        return real(file, mode, *arguments, **named)

    def descriptor(file, flags, *arguments, **named):
        opened.append((Path(file), flags))
        return low(file, flags, *arguments, **named)

    monkeypatch.setattr("builtins.open", high)
    monkeypatch.setattr(io, "open", high)
    monkeypatch.setattr(os, "open", descriptor)
    return opened


@pytest.fixture
def watch(monkeypatch, root):
    seen = []
    flush, give = os.fsync, os.link

    def fsync(descriptor):
        files = {
            name: content
            for name, content in snapshot(root).items()
            if content is not None
        }
        status = os.fstat(descriptor)
        same = [
            name for name in files if os.path.samestat(status, os.stat(root / name))
        ]
        taken = os.path.lexists(root / FILE)
        seen.append({"step": "flush", "taken": taken, "files": files})
        seen[-1].update(descriptor=descriptor, flushed=same)
        return flush(descriptor)

    def linking(source, target):
        with pytest.raises(OSError):
            os.fstat(seen[-1]["descriptor"])
        content = Path(source).read_bytes()
        taken = os.path.lexists(target)
        seen.append({"step": "link", "taken": taken, "content": content})
        seen[-1].update(source=Path(source), target=Path(target))
        return give(source, target)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "link", linking)
    return seen


class Partial:
    def __init__(self, file, error, observe):
        self.file = file
        self.error = error
        self.observe = observe

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return self.file.__exit__(*exception)

    def write(self, content):
        self.file.write(content[:7])
        self.observe()
        raise self.error


def break_step(monkeypatch, step, error, observe=lambda: None):
    real = open

    def refuse(*arguments, **named):
        observe()
        raise error

    def creation(file, mode="r", *arguments, **named):
        if "x" not in mode:
            return real(file, mode, *arguments, **named)
        if step == "creation":
            raise error
        return Partial(real(file, mode, *arguments, **named), error, observe)

    if step in ("creation", "write"):
        monkeypatch.setattr("builtins.open", creation)
    else:
        name = {"flush": "fsync", "link": "link", "unlink": "unlink"}[step]
        monkeypatch.setattr(os, name, refuse)


# --- happy ---


def test_signature_and_public_names():
    names = ["data_root", "run_id", "content"]
    assert list(inspect.signature(write).parameters) == names
    own = [
        name
        for name, value in vars(instance_file).items()
        if getattr(value, "__module__", None) == instance_file.__name__
    ]
    assert own == ["WrittenFormError", "NameTakenError", "write"]
    assert issubclass(WrittenFormError, ValueError)
    assert not issubclass(WrittenFormError, InvalidInstanceError)
    assert not issubclass(NameTakenError, OSError)


@pytest.mark.parametrize("as_type", [Path, str])
@pytest.mark.parametrize("content", CONTENTS.values(), ids=CONTENTS)
def test_the_bytes_given_are_the_bytes_under_the_final_name(root, content, as_type):
    assert write(as_type(root), RUN, content) is None

    created = {"data": None, "data/runs": None, f"data/runs/{RUN}": None}
    assert snapshot(root.parent) == created | {f"data/{FILE}": content}
    assert instance.read(root, RUN) == instance.parse(content)


def test_data_root_as_a_relative_path(root, monkeypatch):
    monkeypatch.chdir(root.parent)

    write("data", RUN, MINIMAL)
    write(Path("data"), OTHER_RUN, FULL)

    assert snapshot(root)[FILE] == MINIMAL
    assert snapshot(root)[f"runs/{OTHER_RUN}/instance.json"] == FULL
    assert temporaries(root) == []


# --- branch: the run directory ---


@pytest.mark.parametrize(
    "present",
    [
        {},
        {"runs": None},
        {f"runs/{RUN}": None},
        {f"runs/{RUN}/STATE.json": b"a state", f"runs/{RUN}/events.ndjson": b""},
        {LEFTOVER: OTHER[:9]},
        {LEFTOVER: OTHER},
    ],
    ids=["nothing", "runs", "run directory", "other files", "partial", "whole"],
)
def test_the_write_is_the_same_whatever_the_run_directory_holds(root, present):
    for name, content in present.items():
        if content is None:
            (root / name).mkdir(parents=True)
        else:
            place(root, content, name)
    before = snapshot(root)
    assert found(root) is None

    write(root, RUN, MINIMAL)

    created = {"runs": None, f"runs/{RUN}": None, FILE: MINIMAL}
    assert snapshot(root) == before | created
    assert found(root) == instance.parse(MINIMAL)
    assert temporaries(root) == [name for name in present if name == LEFTOVER]


def test_a_second_run_is_untouched(root):
    write(root, OTHER_RUN, FULL)
    place(root, b"a state", f"runs/{OTHER_RUN}/STATE.json")
    other = snapshot(root)

    write(root, RUN, MINIMAL)

    assert {n: c for n, c in snapshot(root).items() if RUN not in n} == other
    assert instance.read(root, OTHER_RUN) == instance.parse(FULL)
    assert instance.read(root, RUN) == instance.parse(MINIMAL)


# --- the steps ---


def test_the_temporary_file_is_whole_and_the_final_name_absent_until_the_link(
    root, watch
):
    write(root, RUN, FULL)

    flush, give = watch
    source = give["source"]
    assert (flush["step"], give["step"]) == ("flush", "link")
    assert (flush["taken"], give["taken"]) == (False, False)
    assert source.parent == root / "runs" / RUN
    assert give["target"] == layout.run_file(root, RUN, "instance.json")
    assert TEMPORARY.fullmatch(source.name)
    assert source.name not in layout.RUN_FILES
    assert source.name.startswith(f"instance.json.{os.getpid()}-")
    assert give["content"] == FULL
    assert flush["files"] == {source.relative_to(root).as_posix(): FULL}
    assert flush["flushed"] == list(flush["files"])
    assert temporaries(root) == []
    assert snapshot(root)[FILE] == FULL


def test_every_write_uses_another_temporary_name(root, watch):
    write(root, RUN, MINIMAL)
    write(root, OTHER_RUN, MINIMAL)
    with pytest.raises(NameTakenError):
        write(root, RUN, MINIMAL)

    sources = [entry["source"].name for entry in watch if entry["step"] == "link"]
    assert len(set(sources)) == 3
    assert all(TEMPORARY.fullmatch(name) for name in sources)


def test_only_a_new_file_of_the_temporary_name_is_opened(root, monkeypatch):
    opened = spy(monkeypatch)
    write(root, RUN, MINIMAL)
    monkeypatch.undo()

    ((path, mode),) = opened
    assert mode == "xb"
    assert path.parent == root / "runs" / RUN
    assert TEMPORARY.fullmatch(path.name)


# --- the death moments of ADR-0025 decision 7 ---


class Stop(BaseException):
    pass


@pytest.mark.parametrize("step", STEPS[1:])
def test_a_stop_before_the_name_is_given_leaves_a_missing_file(root, monkeypatch, step):
    seen = []

    def observe():
        seen.append((found(root), os.path.lexists(root / FILE)))

    break_step(monkeypatch, step, Stop(), observe)

    with pytest.raises(Stop):
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert seen == [(None, False)]
    assert found(root) is None
    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None}


def test_a_stop_after_the_name_is_given_leaves_the_whole_content(root, monkeypatch):
    seen = []
    break_step(monkeypatch, "unlink", Stop(), lambda: seen.append(found(root)))

    with pytest.raises(Stop):
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert seen == [instance.parse(MINIMAL)]
    assert snapshot(root)[FILE] == MINIMAL
    (leftover,) = temporaries(root)
    assert os.path.samefile(root / leftover, root / FILE)


# --- a taken name ---


@pytest.mark.parametrize("how", TAKEN)
def test_a_taken_name_is_reported_and_what_is_there_is_unchanged(
    root, monkeypatch, how
):
    take(root, how)
    before = (snapshot(root.parent), kind(root / FILE))
    opened = spy(monkeypatch)

    with pytest.raises(NameTakenError, match=FILE) as caught:
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert not isinstance(caught.value, OSError)
    assert (snapshot(root.parent), kind(root / FILE)) == before
    assert temporaries(root) == []
    assert all(TEMPORARY.fullmatch(path.name) and mode == "xb" for path, mode in opened)
    assert len(opened) == 1


def test_equal_bytes_are_reported_as_other_bytes(root):
    write(root, RUN, MINIMAL)
    reports = []
    for content in (MINIMAL, OTHER):
        with pytest.raises(NameTakenError) as caught:
            write(root, RUN, content)
        reports.append((type(caught.value), str(caught.value)))

    assert reports[0] == reports[1]
    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None, FILE: MINIMAL}


def test_a_name_freed_by_other_means_is_given_again(root):
    write(root, RUN, MINIMAL)
    with pytest.raises(NameTakenError):
        write(root, RUN, OTHER)
    (root / FILE).unlink()

    write(root, RUN, OTHER)

    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None, FILE: OTHER}


# --- error / negative ---


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("content, error", REFUSED.values(), ids=REFUSED)
def test_a_refused_content_creates_and_changes_nothing(root, content, error, previous):
    if previous is not None:
        place(root, previous)
    before = snapshot(root)

    with pytest.raises(error) as caught:
        write(root, RUN, content)

    assert type(caught.value) is error
    assert snapshot(root) == before


@pytest.mark.parametrize("run_id", ["", "Run", "a/b", "..", "a" * 65, 7, None])
def test_an_invalid_run_id_creates_nothing(root, run_id):
    with pytest.raises(layout.InvalidPathValueError, match="run_id"):
        write(root, run_id, MINIMAL)

    assert snapshot(root) == {}


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_missing_data_root_is_not_created(tmp_path, as_type):
    with pytest.raises(FileNotFoundError, match="data root"):
        write(as_type(tmp_path / "absent"), RUN, MINIMAL)

    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_file_in_the_place_of_the_data_root(tmp_path, as_type):
    place(tmp_path, b"a file", "data")

    with pytest.raises(NotADirectoryError, match="data root"):
        write(as_type(tmp_path / "data"), RUN, MINIMAL)

    assert snapshot(tmp_path) == {"data": b"a file"}


@pytest.mark.parametrize("name", ["runs", f"runs/{RUN}"])
def test_a_file_in_the_place_of_a_directory_above_the_final_name(root, name):
    place(root, b"a file", name)
    before = snapshot(root)

    with pytest.raises(OSError):
        write(root, RUN, MINIMAL)

    assert snapshot(root) == before


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS)
def test_a_failed_step_leaves_the_final_name_and_no_temporary_file(
    root, monkeypatch, step, previous
):
    if previous is not None:
        place(root, previous)
    error = OSError(f"{step} refused: no hard links here")
    break_step(monkeypatch, step, error)

    with pytest.raises(OSError) as caught:
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert caught.value is error
    expected = {"runs": None, f"runs/{RUN}": None}
    assert snapshot(root) == expected | ({} if previous is None else {FILE: previous})


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS[1:])
def test_an_interrupt_removes_the_temporary_file_too(root, monkeypatch, step, previous):
    if previous is not None:
        place(root, previous)
    before = snapshot(root)
    break_step(monkeypatch, step, KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert snapshot(root) == before | {"runs": None, f"runs/{RUN}": None}


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
def test_a_temporary_name_in_use_is_an_error_and_that_file_stays(
    root, monkeypatch, previous
):
    if previous is not None:
        place(root, previous)
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * 2 * size)
    name = f"runs/{RUN}/instance.json.{os.getpid()}-{'0' * 16}.tmp"
    place(root, b"of another writer", name)
    before = snapshot(root)

    with pytest.raises(FileExistsError):
        write(root, RUN, MINIMAL)

    assert snapshot(root) == before


def test_a_removal_that_fails_does_not_hide_the_failure_of_the_step(root, monkeypatch):
    error = OSError("link refused")
    break_step(monkeypatch, "link", error)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    with pytest.raises(OSError) as caught:
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert caught.value is error
    assert found(root) is None
    (leftover,) = temporaries(root)
    assert snapshot(root)[leftover] == MINIMAL


def test_a_removal_that_fails_does_not_hide_a_taken_name(root, monkeypatch):
    place(root, OTHER)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    with pytest.raises(NameTakenError):
        write(root, RUN, MINIMAL)
    monkeypatch.undo()

    assert snapshot(root)[FILE] == OTHER
    assert len(temporaries(root)) == 1


def test_a_removal_that_fails_after_the_name_is_given_is_no_failure(root, monkeypatch):
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    assert write(root, RUN, MINIMAL) is None
    monkeypatch.undo()

    assert snapshot(root)[FILE] == MINIMAL
    assert found(root) == instance.parse(MINIMAL)
    (leftover,) = temporaries(root)
    assert os.path.samefile(root / leftover, root / FILE)


def test_a_temporary_file_removed_by_another_fails_the_link_and_gives_no_name(
    root, monkeypatch
):
    give = os.link

    def removed_first(source, target):
        Path(source).unlink()
        return give(source, target)

    monkeypatch.setattr(os, "link", removed_first)

    with pytest.raises(FileNotFoundError):
        write(root, RUN, MINIMAL)

    assert snapshot(root) == {"runs": None, f"runs/{RUN}": None}


def test_the_order_of_the_checks(tmp_path):
    absent = tmp_path / "absent"
    file = place(tmp_path, b"a file", "file")

    with pytest.raises(layout.InvalidPathValueError):
        write(absent, "Run", None)
    with pytest.raises(TypeError):
        write(absent, RUN, None)
    with pytest.raises(InvalidInstanceError):
        write(absent, RUN, MINIMAL[:20])
    with pytest.raises(WrittenFormError):
        write(absent, RUN, MINIMAL[:-1])
    with pytest.raises(WrittenFormError):
        write(file, RUN, b"\r" + MINIMAL)
    with pytest.raises(FileNotFoundError):
        write(absent, RUN, MINIMAL)
    with pytest.raises(NotADirectoryError):
        write(file, RUN, MINIMAL)

    assert snapshot(tmp_path) == {"file": b"a file"}


# --- nothing added ---


def test_white_space_and_member_order_are_written_as_given(root):
    write(root, RUN, UNUSUAL)

    assert snapshot(root)[FILE] == UNUSUAL
    assert instance.read(root, RUN).others == {"example_member": "a\r\nb"}


def test_absent_members_stay_absent(root):
    write(root, RUN, MINIMAL)

    stated = instance.read(root, RUN)
    assert (stated.tolerance, stated.source_commit, stated.n_max) == (None, None, None)
    assert snapshot(root)[FILE] == MINIMAL


def test_the_module_holds_no_value_of_a_content():
    own = [
        value for name, value in vars(instance_file).items() if not name.startswith("_")
    ]
    assert all(
        inspect.ismodule(value) or inspect.isclass(value) or inspect.isfunction(value)
        for value in own
    )


@pytest.mark.parametrize("model", ["opus", "claude-opus-5-5[1m]", "", None, 5])
def test_a_content_with_an_invalid_coder_model_is_not_written(root, model):
    with pytest.raises(InvalidInstanceError, match="^coder_model: must be"):
        write(root, RUN, written(doc(coder_model=model)))

    assert snapshot(root) == {}
    write(root, RUN, written(doc(coder_model="claude-example-1-2")))
    assert instance.read(root, RUN).coder_model == "claude-example-1-2"
