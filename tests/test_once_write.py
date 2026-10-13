import inspect
import os
import secrets

import pytest

from hilclaw import once_write
from hilclaw.once_write import write_once

# Synthetic values only: no content of a real run.
NAME = "final.json"
CONTENT = b'{"synthetic": 1}\n'
OTHER = b"of another writer\n"
FIXED = f"{NAME}.{os.getpid()}-{'0' * 16}.tmp"


def snapshot(directory):
    return {entry.name: entry.read_bytes() for entry in directory.iterdir()}


def failing(error):
    def fail(*arguments, **named):
        raise error

    return fail


@pytest.fixture
def fixed_token(monkeypatch):
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * 2 * size)


class Partial:
    def __init__(self, file, error):
        self.file = file
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return self.file.__exit__(*exception)

    def write(self, content):
        self.file.write(content[:5])
        raise self.error


def break_step(monkeypatch, step, error):
    real = open

    def torn(file, mode="r", *arguments, **named):
        return Partial(real(file, mode, *arguments, **named), error)

    if step == "write":
        monkeypatch.setattr(once_write, "open", torn, raising=False)
    else:
        monkeypatch.setattr(os, step, failing(error))


# --- happy ---


def test_signature_and_public_names():
    assert list(inspect.signature(write_once).parameters) == ["path", "content"]
    own = [
        name
        for name, value in vars(once_write).items()
        if not name.startswith("_")
        and getattr(value, "__module__", "") == once_write.__name__
    ]
    assert own == ["write_once"]


def test_a_free_name_is_given_to_the_whole_content(tmp_path):
    assert write_once(tmp_path / NAME, CONTENT) is None

    assert snapshot(tmp_path) == {NAME: CONTENT}


def test_an_empty_content_is_written_as_it_is(tmp_path):
    assert write_once(tmp_path / NAME, b"") is None

    assert snapshot(tmp_path) == {NAME: b""}


def test_the_temporary_name_form_and_the_order_of_the_steps(
    tmp_path, monkeypatch, fixed_token
):
    seen = []
    flush, give, remove = os.fsync, os.link, os.unlink

    def fsync(descriptor):
        seen.append(("flush", snapshot(tmp_path)))
        return flush(descriptor)

    def link(source, target):
        seen.append(("link", source, target, snapshot(tmp_path)))
        return give(source, target)

    def unlink(path):
        seen.append(("unlink", path, snapshot(tmp_path)))
        return remove(path)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "link", link)
    monkeypatch.setattr(os, "unlink", unlink)
    final, temporary = tmp_path / NAME, tmp_path / FIXED

    assert write_once(final, CONTENT) is None
    monkeypatch.undo()

    assert seen == [
        ("flush", {FIXED: CONTENT}),
        ("link", temporary, final, {FIXED: CONTENT}),
        ("unlink", temporary, {FIXED: CONTENT, NAME: CONTENT}),
    ]
    assert snapshot(tmp_path) == {NAME: CONTENT}


def test_two_writes_use_different_temporary_names(tmp_path, monkeypatch):
    sources = []
    give = os.link

    def link(source, target):
        sources.append(source.name)
        return give(source, target)

    monkeypatch.setattr(os, "link", link)

    write_once(tmp_path / "a.json", CONTENT)
    write_once(tmp_path / "a.json", CONTENT)

    assert len(set(sources)) == 2
    prefix = f"a.json.{os.getpid()}-"
    assert all(name.startswith(prefix) and name.endswith(".tmp") for name in sources)
    assert all(len(name) == len(prefix) + 16 + len(".tmp") for name in sources)


def test_a_removal_that_fails_after_the_name_is_given_is_no_failure(
    tmp_path, monkeypatch, fixed_token
):
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    assert write_once(tmp_path / NAME, CONTENT) is None
    monkeypatch.undo()

    assert snapshot(tmp_path) == {NAME: CONTENT, FIXED: CONTENT}
    assert os.path.samefile(tmp_path / NAME, tmp_path / FIXED)


# --- the final name is taken ---


def test_a_taken_name_returns_the_error_of_the_link_and_replaces_nothing(
    tmp_path, monkeypatch
):
    (tmp_path / NAME).write_bytes(OTHER)
    raised = []
    give = os.link

    def link(source, target):
        try:
            return give(source, target)
        except FileExistsError as error:
            raised.append(error)
            raise

    monkeypatch.setattr(os, "link", link)

    taken = write_once(tmp_path / NAME, CONTENT)

    assert type(taken) is FileExistsError
    assert raised == [taken]
    assert snapshot(tmp_path) == {NAME: OTHER}


def test_equal_bytes_under_a_taken_name_are_reported_as_any_other(tmp_path):
    (tmp_path / NAME).write_bytes(CONTENT)

    assert isinstance(write_once(tmp_path / NAME, CONTENT), FileExistsError)
    assert snapshot(tmp_path) == {NAME: CONTENT}


def test_a_directory_under_the_final_name_is_a_taken_name(tmp_path):
    (tmp_path / NAME).mkdir()

    assert isinstance(write_once(tmp_path / NAME, CONTENT), FileExistsError)
    assert [entry.name for entry in tmp_path.iterdir()] == [NAME]
    assert list((tmp_path / NAME).iterdir()) == []


def test_a_taken_name_is_never_opened(tmp_path, monkeypatch):
    (tmp_path / NAME).write_bytes(OTHER)
    opened = []
    real = open

    def spy(file, mode="r", *arguments, **named):
        opened.append((file.name, mode))
        return real(file, mode, *arguments, **named)

    monkeypatch.setattr(once_write, "open", spy, raising=False)

    write_once(tmp_path / NAME, CONTENT)

    assert [mode for _, mode in opened] == ["xb"]
    assert opened[0][0] != NAME


def test_a_removal_that_fails_does_not_hide_a_taken_name(
    tmp_path, monkeypatch, fixed_token
):
    (tmp_path / NAME).write_bytes(OTHER)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    taken = write_once(tmp_path / NAME, CONTENT)
    monkeypatch.undo()

    assert isinstance(taken, FileExistsError)
    assert snapshot(tmp_path) == {NAME: OTHER, FIXED: CONTENT}


# --- negative and failure paths ---


@pytest.mark.parametrize("previous", [None, OTHER], ids=["free", "taken"])
def test_a_temporary_name_in_use_is_raised_and_that_file_stays(
    tmp_path, fixed_token, previous
):
    if previous is not None:
        (tmp_path / NAME).write_bytes(previous)
    (tmp_path / FIXED).write_bytes(OTHER)
    before = snapshot(tmp_path)

    with pytest.raises(FileExistsError):
        write_once(tmp_path / NAME, CONTENT)

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("step", ["write", "fsync", "link"])
@pytest.mark.parametrize("previous", [None, OTHER], ids=["free", "taken"])
def test_a_failing_step_is_raised_and_leaves_no_temporary_file(
    tmp_path, monkeypatch, step, previous
):
    if previous is not None:
        (tmp_path / NAME).write_bytes(previous)
    before = snapshot(tmp_path)
    error = OSError(f"{step} refused")
    break_step(monkeypatch, step, error)

    with pytest.raises(OSError) as caught:
        write_once(tmp_path / NAME, CONTENT)
    monkeypatch.undo()

    assert caught.value is error
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("step", ["write", "fsync", "link"])
def test_an_interrupt_during_a_step_removes_the_temporary_file_and_passes_through(
    tmp_path, monkeypatch, step
):
    break_step(monkeypatch, step, KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        write_once(tmp_path / NAME, CONTENT)
    monkeypatch.undo()

    assert snapshot(tmp_path) == {}


def test_a_removal_that_fails_does_not_hide_the_failure_of_the_step(
    tmp_path, monkeypatch, fixed_token
):
    error = OSError("link refused")
    break_step(monkeypatch, "link", error)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    with pytest.raises(OSError) as caught:
        write_once(tmp_path / NAME, CONTENT)
    monkeypatch.undo()

    assert caught.value is error
    assert snapshot(tmp_path) == {FIXED: CONTENT}


def test_a_temporary_file_removed_by_another_fails_the_link_and_gives_no_name(
    tmp_path, monkeypatch
):
    give = os.link

    def removed_first(source, target):
        source.unlink()
        return give(source, target)

    monkeypatch.setattr(os, "link", removed_first)

    with pytest.raises(FileNotFoundError):
        write_once(tmp_path / NAME, CONTENT)

    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("content", ["text", None, 7, [b"a"]], ids=repr)
def test_a_content_that_is_not_bytes_is_a_type_error_and_leaves_nothing(
    tmp_path, content
):
    with pytest.raises(TypeError):
        write_once(tmp_path / NAME, content)

    assert snapshot(tmp_path) == {}


def test_a_missing_parent_directory_is_an_error_and_is_not_created(tmp_path):
    with pytest.raises(FileNotFoundError):
        write_once(tmp_path / "absent" / NAME, CONTENT)

    assert snapshot(tmp_path) == {}


def test_a_file_in_the_place_of_the_parent_directory_is_an_error(tmp_path):
    (tmp_path / "file").write_bytes(OTHER)

    with pytest.raises(OSError):
        write_once(tmp_path / "file" / NAME, CONTENT)

    assert snapshot(tmp_path) == {"file": OTHER}


def test_no_replacing_rename_is_called(tmp_path, monkeypatch):
    for name in ("replace", "rename"):
        monkeypatch.setattr(os, name, failing(AssertionError(f"os.{name} was called")))
    (tmp_path / "taken.json").write_bytes(OTHER)

    assert write_once(tmp_path / NAME, CONTENT) is None
    assert isinstance(write_once(tmp_path / "taken.json", CONTENT), FileExistsError)
    monkeypatch.undo()

    assert snapshot(tmp_path) == {NAME: CONTENT, "taken.json": OTHER}
