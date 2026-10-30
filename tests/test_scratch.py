import errno
import os
import shutil
import stat
import tempfile
from pathlib import Path

import pytest

from hilclaw import scratch as scratch_module
from hilclaw.bring_in import bring_in
from hilclaw.kernel_source import OUTPUT_NAME
from hilclaw.scratch import (
    BASE_COPY_NAME,
    BASE_UNREADABLE,
    PREFIX,
    SCRATCH_FAILURES,
    SPEC_CHANGED,
    SPEC_COPY_NAME,
    SPEC_NOT_REGULAR_FILE,
    SPEC_UNREADABLE,
    InvalidScratchArgumentError,
    ScratchError,
    create,
    remove,
)

REPOSITORY = Path(scratch_module.__file__).resolve().parent.parent
SPEC_BYTES = b'{"schema_version": 2}\n'
POSIX_ONLY = pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt", reason="Windows junctions")


@pytest.fixture
def parent(tmp_path):
    directory = tmp_path / "parent"
    directory.mkdir()
    return directory


@pytest.fixture
def data_root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


@pytest.fixture
def spec(tmp_path):
    path = tmp_path / "spec.json"
    path.write_bytes(SPEC_BYTES)
    return path


@pytest.fixture
def no_pause(monkeypatch):
    monkeypatch.setattr(scratch_module.time, "sleep", lambda _: None)


@pytest.fixture
def no_rmtree(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("rmtree must not be reached")

    monkeypatch.setattr(shutil, "rmtree", refuse)


def symlink(link, target, *, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError):
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise
        pytest.skip("this machine refuses to create a symbolic link")


def junction(link, target):
    import _winapi

    _winapi.CreateJunction(str(target), str(link))


def assert_no_path(error, *paths):
    for path in paths:
        assert str(path) not in str(error)
    assert "/" not in str(error)
    assert "\\" not in str(error)


def made(parent):
    return sorted(os.listdir(parent))


# --- create: happy paths ---


def test_create_places_exactly_one_copy_of_the_bytes(spec, parent, data_root):
    directory = create(spec, parent=parent, keep_out=[data_root])
    assert isinstance(directory, str)
    assert Path(directory).parent.resolve() == parent.resolve()
    assert Path(directory).name.startswith(PREFIX)
    assert os.listdir(directory) == [SPEC_COPY_NAME]
    assert Path(directory, SPEC_COPY_NAME).read_bytes() == SPEC_BYTES
    assert remove(directory, keep_out=[data_root]) is True
    assert not os.path.lexists(directory)
    assert made(parent) == []


def test_create_copies_bytes_that_are_neither_json_nor_utf8(tmp_path, parent):
    data = b"\xff\xfe not json \x00\r\n" + bytes(range(256)) * 300
    source = tmp_path / "raw"
    source.write_bytes(data)
    directory = create(str(source), parent=str(parent))
    assert Path(directory, SPEC_COPY_NAME).read_bytes() == data


def test_create_copies_an_empty_file(tmp_path, parent):
    source = tmp_path / "empty"
    source.write_bytes(b"")
    directory = create(source, parent=parent)
    assert Path(directory, SPEC_COPY_NAME).read_bytes() == b""


def test_two_calls_give_two_directories(spec, parent):
    first = create(spec, parent=parent)
    second = create(spec, parent=parent)
    assert first != second
    assert len(made(parent)) == 2


def test_create_defaults_to_the_temporary_directory(spec):
    directory = create(spec)
    try:
        assert os.path.normcase(os.path.dirname(directory)) == os.path.normcase(
            os.path.realpath(tempfile.gettempdir())
        )
    finally:
        assert remove(directory) is True


def test_the_copy_is_not_in_the_place(spec, parent, tmp_path):
    assert SPEC_COPY_NAME != OUTPUT_NAME
    directory = create(spec, parent=parent)
    output = tmp_path / "attempt" / OUTPUT_NAME
    assert bring_in(directory, output) == ()
    assert not output.exists()


def test_the_copy_is_a_new_file(spec, parent):
    directory = create(spec, parent=parent)
    copied = os.lstat(os.path.join(directory, SPEC_COPY_NAME))
    source = os.lstat(spec)
    assert stat.S_ISREG(copied.st_mode)
    assert copied.st_nlink == 1
    assert (copied.st_dev, copied.st_ino) != (source.st_dev, source.st_ino)


@POSIX_ONLY
def test_the_copy_carries_no_mode_bit_of_the_source(spec, parent):
    os.chmod(spec, 0o755)
    directory = create(spec, parent=parent)
    mode = stat.S_IMODE(os.lstat(os.path.join(directory, SPEC_COPY_NAME)).st_mode)
    assert mode & 0o111 == 0


# --- create: refusals ---


@pytest.mark.parametrize("where", ["equal", "inside"])
def test_create_refuses_a_parent_in_keep_out(spec, parent, where):
    place = parent if where == "equal" else parent / "below"
    place.mkdir(exist_ok=True)
    with pytest.raises(InvalidScratchArgumentError) as caught:
        create(spec, parent=place, keep_out=(parent,))
    assert_no_path(caught.value, parent)
    assert made(place) == []


def test_create_refuses_a_parent_inside_the_package_checkout(spec):
    before = made(REPOSITORY)
    for place in (REPOSITORY, REPOSITORY / "hilclaw", REPOSITORY / "absent"):
        with pytest.raises(InvalidScratchArgumentError) as caught:
            create(spec, parent=place)
        assert "checkout" in str(caught.value)
        assert_no_path(caught.value, REPOSITORY)
    assert made(REPOSITORY) == before


@pytest.mark.parametrize("keep_out", ["data", b"data", Path("data")])
def test_create_refuses_one_path_as_keep_out(spec, parent, keep_out):
    with pytest.raises(TypeError):
        create(spec, parent=parent, keep_out=keep_out)
    assert made(parent) == []


@pytest.mark.parametrize("value", [None, 7, b"spec.json", "spec\0.json"])
def test_create_refuses_a_bad_spec_path(parent, value):
    with pytest.raises(InvalidScratchArgumentError) as caught:
        create(value, parent=parent)
    assert "spec_path" in str(caught.value)
    assert made(parent) == []


@pytest.mark.parametrize("value", [7, b"parent", "par\0ent"])
def test_create_refuses_a_bad_parent(spec, value):
    with pytest.raises(InvalidScratchArgumentError) as caught:
        create(spec, parent=value)
    assert "parent" in str(caught.value)


@pytest.mark.parametrize("value", [7, b"data", "da\0ta"])
def test_create_refuses_a_bad_keep_out_entry(spec, parent, value):
    with pytest.raises(InvalidScratchArgumentError) as caught:
        create(spec, parent=parent, keep_out=[value])
    assert "keep_out" in str(caught.value)
    assert made(parent) == []


def test_create_refuses_a_missing_source(tmp_path, parent):
    missing = tmp_path / "missing.json"
    with pytest.raises(ScratchError) as caught:
        create(missing, parent=parent)
    assert caught.value.failure == SPEC_UNREADABLE
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert_no_path(caught.value, missing)
    assert made(parent) == []


def test_create_refuses_a_directory_as_source(tmp_path, parent):
    with pytest.raises(ScratchError) as caught:
        create(tmp_path, parent=parent)
    assert caught.value.failure == SPEC_NOT_REGULAR_FILE
    assert str(caught.value) == SPEC_NOT_REGULAR_FILE
    assert made(parent) == []


def test_create_refuses_a_symbolic_link_as_source(spec, tmp_path, parent):
    link = tmp_path / "link.json"
    symlink(link, spec)
    with pytest.raises(ScratchError) as caught:
        create(link, parent=parent)
    assert caught.value.failure == SPEC_NOT_REGULAR_FILE
    assert made(parent) == []


def test_create_refuses_a_source_that_cannot_be_opened(spec, parent, monkeypatch):
    def refuse(path, flags, *args):
        raise PermissionError(errno.EACCES, "denied", str(path))

    monkeypatch.setattr(scratch_module.os, "open", refuse)
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent)
    assert caught.value.failure == SPEC_UNREADABLE
    assert isinstance(caught.value.__cause__, PermissionError)
    assert made(parent) == []


def test_create_refuses_a_source_swapped_for_a_link_before_the_open(
    spec, parent, monkeypatch
):
    def refuse(path, flags, *args):
        raise OSError(errno.ELOOP, "loop", str(path))

    monkeypatch.setattr(scratch_module.os, "open", refuse)
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent)
    assert caught.value.failure == SPEC_CHANGED
    assert made(parent) == []


@pytest.mark.parametrize("change", ["inode", "device", "kind"])
def test_create_refuses_an_opened_file_that_is_not_the_one_examined(
    spec, parent, monkeypatch, change
):
    real = os.fstat

    def other(descriptor):
        found = list(real(descriptor))
        if change == "inode":
            found[stat.ST_INO] += 1
        elif change == "device":
            found[stat.ST_DEV] += 1
        else:
            found[stat.ST_MODE] = stat.S_IFDIR | 0o755
        return os.stat_result(found)

    monkeypatch.setattr(scratch_module.os, "fstat", other)
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent)
    assert caught.value.failure == SPEC_CHANGED
    assert made(parent) == []


def test_create_refuses_a_source_that_fails_while_read(spec, parent, monkeypatch):
    def fail(descriptor, size):
        raise OSError(errno.EIO, "io")

    monkeypatch.setattr(scratch_module.os, "read", fail)
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent)
    assert caught.value.failure == SPEC_UNREADABLE
    assert caught.value.__cause__.errno == errno.EIO
    assert made(parent) == []


# --- create: all or nothing ---


def test_a_failed_write_leaves_no_scratch(spec, parent, monkeypatch):
    original = OSError(errno.ENOSPC, "no space")

    def fail(descriptor, data):
        raise original

    monkeypatch.setattr(scratch_module.os, "write", fail)
    with pytest.raises(OSError) as caught:
        create(spec, parent=parent)
    assert caught.value is original
    assert made(parent) == []


def test_a_failed_creation_of_the_copy_leaves_no_scratch(spec, parent, monkeypatch):
    real = os.open
    original = PermissionError(errno.EACCES, "denied")

    def fail_on_write(path, flags, *args, **kwargs):
        if flags & os.O_CREAT:
            raise original
        return real(path, flags, *args, **kwargs)

    monkeypatch.setattr(scratch_module.os, "open", fail_on_write)
    with pytest.raises(PermissionError) as caught:
        create(spec, parent=parent)
    assert caught.value is original
    assert made(parent) == []


def test_a_failure_in_mkdtemp_is_raised_as_it_is(spec, parent, monkeypatch):
    original = OSError(errno.ENOSPC, "no space")

    def fail(**kwargs):
        raise original

    monkeypatch.setattr(scratch_module.tempfile, "mkdtemp", fail)
    with pytest.raises(OSError) as caught:
        create(spec, parent=parent)
    assert caught.value is original


# --- remove ---


def test_remove_removes_nested_entries(tmp_path):
    root = tmp_path / "scratch"
    (root / "a" / "b").mkdir(parents=True)
    (root / "a" / "b" / "c.txt").write_bytes(b"c")
    (root / "top.c").write_bytes(b"int x;\n")
    assert remove(root) is True
    assert not root.exists()


def test_remove_does_not_follow_a_link_to_a_directory(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_bytes(b"keep")
    root = tmp_path / "scratch"
    root.mkdir()
    symlink(root / "link", outside, directory=True)
    assert remove(root) is True
    assert not os.path.lexists(root)
    assert (outside / "keep.txt").read_bytes() == b"keep"


def test_remove_does_not_follow_a_link_to_a_file(tmp_path):
    outside = tmp_path / "keep.txt"
    outside.write_bytes(b"keep")
    root = tmp_path / "scratch"
    root.mkdir()
    symlink(root / "link", outside)
    assert remove(root) is True
    assert outside.read_bytes() == b"keep"


def test_remove_removes_a_dangling_link(tmp_path):
    root = tmp_path / "scratch"
    root.mkdir()
    symlink(root / "dangling", tmp_path / "nowhere")
    assert remove(root) is True
    assert not os.path.lexists(root)


@WINDOWS_ONLY
def test_remove_does_not_descend_into_a_junction(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_bytes(b"keep")
    root = tmp_path / "scratch"
    root.mkdir()
    junction(root / "junction", outside)
    assert remove(root) is True
    assert (outside / "keep.txt").read_bytes() == b"keep"


@WINDOWS_ONLY
def test_remove_refuses_a_junction_as_scratch(tmp_path, no_rmtree):
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_bytes(b"keep")
    link = tmp_path / "junction"
    junction(link, target)
    with pytest.raises(InvalidScratchArgumentError):
        remove(link)
    assert (target / "keep.txt").read_bytes() == b"keep"


@POSIX_ONLY
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores permissions"
)
def test_remove_makes_a_protected_directory_writable(tmp_path, no_pause):
    root = tmp_path / "scratch"
    locked = root / "locked"
    (locked / "inner").mkdir(parents=True)
    (locked / "inner" / "file").write_bytes(b"x")
    os.chmod(locked / "inner", 0o500)
    os.chmod(locked, 0o000)
    assert remove(root) is True
    assert not root.exists()


@POSIX_ONLY
@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores permissions"
)
def test_making_writable_does_not_follow_a_link(tmp_path, no_pause, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    os.chmod(outside, 0o500)
    root = tmp_path / "scratch"
    (root / "locked").mkdir(parents=True)
    (root / "locked" / "file").write_bytes(b"x")
    os.chmod(root / "locked", 0o500)
    symlink(root / "link", outside, directory=True)
    real = shutil.rmtree
    calls = []

    def first_fails(path, ignore_errors=False):
        calls.append(path)
        if len(calls) > 1:
            real(path, ignore_errors=ignore_errors)

    monkeypatch.setattr(shutil, "rmtree", first_fails)
    try:
        assert remove(root) is True
        assert stat.S_IMODE(os.lstat(outside).st_mode) == 0o500
    finally:
        os.chmod(outside, 0o700)


def test_remove_tolerates_entries_that_vanish_while_made_writable(tmp_path):
    root = tmp_path / "scratch"
    (root / "a").mkdir(parents=True)
    real_lstat = os.lstat

    def gone(path, *args, **kwargs):
        if os.path.basename(path) == "a":
            raise FileNotFoundError(errno.ENOENT, "gone")
        return real_lstat(path, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(scratch_module.os, "lstat", gone)
        scratch_module._make_writable(str(root))
        scratch_module._make_writable(str(tmp_path / "absent"))
    symlink(root / "link", root / "a", directory=True)
    scratch_module._make_writable(str(root / "link"))
    assert remove(root) is True


def test_a_removal_that_cannot_finish_returns_false(tmp_path, no_pause, monkeypatch):
    root = tmp_path / "scratch"
    root.mkdir()
    (root / "file").write_bytes(b"x")
    calls = []
    monkeypatch.setattr(shutil, "rmtree", lambda *a, **k: calls.append(a))
    assert remove(root) is False
    assert len(calls) == len(scratch_module._REMOVE_PAUSES_S)
    assert (root / "file").exists()


def test_remove_refuses_a_missing_path(tmp_path, no_rmtree):
    missing = tmp_path / "missing"
    with pytest.raises(InvalidScratchArgumentError) as caught:
        remove(missing)
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert_no_path(caught.value, missing)


def test_remove_refuses_a_path_that_cannot_be_examined(
    tmp_path, no_rmtree, monkeypatch
):
    def fail(path, *args, **kwargs):
        raise PermissionError(errno.EACCES, "denied")

    monkeypatch.setattr(scratch_module.os, "lstat", fail)
    with pytest.raises(InvalidScratchArgumentError) as caught:
        remove(tmp_path)
    assert isinstance(caught.value.__cause__, PermissionError)


def test_remove_refuses_a_regular_file(spec, no_rmtree):
    with pytest.raises(InvalidScratchArgumentError):
        remove(spec)
    assert spec.read_bytes() == SPEC_BYTES


def test_remove_refuses_a_link_to_a_directory(tmp_path, no_rmtree):
    target = tmp_path / "target"
    target.mkdir()
    (target / "keep.txt").write_bytes(b"keep")
    link = tmp_path / "link"
    symlink(link, target, directory=True)
    with pytest.raises(InvalidScratchArgumentError):
        remove(link)
    assert os.path.islink(link)
    assert (target / "keep.txt").read_bytes() == b"keep"


def test_remove_refuses_a_dangling_link(tmp_path, no_rmtree):
    link = tmp_path / "link"
    symlink(link, tmp_path / "nowhere", directory=True)
    with pytest.raises(InvalidScratchArgumentError):
        remove(link)
    assert os.path.lexists(link)


@pytest.mark.parametrize("where", ["equal", "inside", "containing"])
def test_remove_refuses_a_path_that_meets_keep_out(tmp_path, no_rmtree, where):
    data = tmp_path / "outer" / "data"
    (data / "inner").mkdir(parents=True)
    target = {
        "equal": data,
        "inside": data / "inner",
        "containing": tmp_path / "outer",
    }[where]
    with pytest.raises(InvalidScratchArgumentError) as caught:
        remove(target, keep_out=[data])
    assert_no_path(caught.value, data)
    assert (data / "inner").is_dir()


@pytest.mark.parametrize("target", [REPOSITORY, REPOSITORY / "hilclaw"])
def test_remove_refuses_the_package_checkout(target, no_rmtree):
    with pytest.raises(InvalidScratchArgumentError) as caught:
        remove(target)
    assert_no_path(caught.value, REPOSITORY)
    assert target.is_dir()


def test_remove_refuses_a_directory_containing_the_package_checkout(no_rmtree):
    with pytest.raises(InvalidScratchArgumentError):
        remove(REPOSITORY.parent)


def test_remove_refuses_one_path_as_keep_out(tmp_path, no_rmtree):
    with pytest.raises(TypeError):
        remove(tmp_path, keep_out=str(tmp_path / "data"))


@pytest.mark.parametrize("value", [None, 7, b"scratch", "scr\0atch"])
def test_remove_refuses_a_bad_scratch(value, no_rmtree):
    with pytest.raises(InvalidScratchArgumentError) as caught:
        remove(value)
    assert "scratch" in str(caught.value)


def test_the_failures_are_distinct_and_texts_hold_no_path():
    assert len(set(SCRATCH_FAILURES)) == len(SCRATCH_FAILURES) == 4
    for failure in SCRATCH_FAILURES:
        assert str(ScratchError(failure)) == failure
        assert os.sep not in failure
    assert issubclass(InvalidScratchArgumentError, ValueError)


@pytest.fixture
def base(tmp_path):
    directory = tmp_path / "base"
    directory.mkdir()
    (directory / "kernel.c").write_bytes(b"int k;\n")
    (directory / "kernel.h").write_bytes(b"")
    return directory


def test_create_copies_each_file_of_base(spec, parent, base):
    scratch = Path(create(spec, parent=parent, base=base))
    try:
        assert sorted(os.listdir(scratch)) == [BASE_COPY_NAME, SPEC_COPY_NAME]
        copied = scratch / BASE_COPY_NAME
        assert sorted(os.listdir(copied)) == ["kernel.c", "kernel.h"]
        assert (copied / "kernel.c").read_bytes() == b"int k;\n"
        assert (copied / "kernel.h").read_bytes() == b""
    finally:
        remove(scratch)


def test_create_copies_an_empty_base(spec, parent, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    scratch = Path(create(spec, parent=parent, base=empty))
    try:
        assert os.listdir(scratch / BASE_COPY_NAME) == []
    finally:
        remove(scratch)


def test_create_refuses_a_missing_base(spec, parent, tmp_path):
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent, base=tmp_path / "absent")
    assert caught.value.failure == BASE_UNREADABLE
    assert os.listdir(parent) == []


def test_create_refuses_a_base_holding_a_directory(spec, parent, base):
    (base / "nested").mkdir()
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent, base=base)
    assert caught.value.failure == BASE_UNREADABLE
    assert os.listdir(parent) == []


def test_create_refuses_a_bad_base_path(spec, parent):
    with pytest.raises(InvalidScratchArgumentError):
        create(spec, parent=parent, base="a\0b")


def test_create_refuses_a_base_that_is_a_symbolic_link(spec, parent, base, tmp_path):
    link = tmp_path / "linked"
    try:
        os.symlink(base, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise
        pytest.skip("this machine refuses to create a symbolic link")
    with pytest.raises(ScratchError) as caught:
        create(spec, parent=parent, base=link)
    assert caught.value.failure == BASE_UNREADABLE
    assert os.listdir(parent) == []
