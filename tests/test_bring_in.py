import errno
import os
import stat
from pathlib import Path

import pytest

from hilclaw.bring_in import (
    ATTEMPT_DIRECTORY_UNLISTABLE,
    BRING_IN_FAILURES,
    CANDIDATE_UNREADABLE,
    ENTRY_KIND_UNDETERMINED,
    MAX_FILE_BYTES,
    MAX_FILES,
    PLACE_UNLISTABLE,
    SCRATCH_ROOT_UNLISTABLE,
    BringInError,
    InvalidBringInArgumentError,
    OutputExistsError,
    bring_in,
)
from hilclaw.kernel_source import read_compiled_set
from hilclaw.layout import attempt_artefact


@pytest.fixture
def scratch(tmp_path):
    directory = tmp_path / "scratch"
    directory.mkdir()
    return directory


@pytest.fixture
def place(scratch):
    directory = scratch / "output"
    directory.mkdir()
    return directory


@pytest.fixture
def output(tmp_path):
    return attempt_artefact(tmp_path / "data", "run-1", 1, 1, 1, "output")


def symlink(link, target, *, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError):
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise
        pytest.skip("this machine refuses to create a symbolic link")


def write(directory, name, data=None):
    path = directory / name
    path.write_bytes(f"/* {name} */\n".encode() if data is None else data)
    return path


def snapshot(root):
    """Every entry below ``root`` with its kind and, for a regular file, its bytes."""
    found = {}
    for directory, dirs, files in os.walk(root):
        for name in dirs + files:
            path = Path(directory, name)
            mode = os.lstat(path).st_mode
            key = path.relative_to(root).as_posix()
            if stat.S_ISREG(mode):
                found[key] = ("file", path.read_bytes(), stat.S_IMODE(mode))
            elif stat.S_ISLNK(mode):
                found[key] = ("link", os.readlink(path))
            else:
                found[key] = ("dir",)
    return found


def recording_listdir(monkeypatch):
    seen = []
    real = os.listdir

    def listdir(path):
        seen.append(os.fspath(path))
        return real(path)

    monkeypatch.setattr(os, "listdir", listdir)
    return seen


def failing(monkeypatch, name, when):
    real = getattr(os, name)

    def call(path, *args, **kwargs):
        if when(Path(path)):
            raise PermissionError(errno.EACCES, "denied", os.fspath(path))
        return real(path, *args, **kwargs)

    monkeypatch.setattr(os, name, call)


def test_the_public_names():
    assert MAX_FILES == 16
    assert MAX_FILE_BYTES == 262_144
    assert BRING_IN_FAILURES == (
        "attempt_directory_unlistable",
        "scratch_root_unlistable",
        "place_unlistable",
        "entry_kind_undetermined",
        "candidate_unreadable",
    )
    assert issubclass(InvalidBringInArgumentError, ValueError)
    assert not issubclass(OutputExistsError, OSError)
    assert not issubclass(BringInError, OSError)


def test_walk_through_step_1_takes_the_place_only(scratch, place, output):
    for name in ("pack.h", "pack.c", "gemm.c"):
        write(place, name)
    (scratch / "try").mkdir()
    write(scratch / "try", "test_main.c")
    write(scratch, "a.out", b"\x7fELF")
    before = snapshot(scratch)

    taken = bring_in(scratch, output)

    assert taken == ("gemm.c", "pack.c", "pack.h")
    assert sorted(os.listdir(output)) == ["gemm.c", "pack.c", "pack.h"]
    for name in taken:
        assert (output / name).read_bytes() == (place / name).read_bytes()
        assert stat.S_ISREG(os.lstat(output / name).st_mode)
    assert [path.name for path in read_compiled_set(output).compiled_set] == [
        "gemm.c",
        "pack.c",
    ]
    assert snapshot(scratch) == before


def test_bytes_are_copied_exactly(scratch, place, output):
    data = bytes(range(256)) * 3 + b"\r\n\0end"
    write(place, "k.c", data)
    assert bring_in(os.fspath(scratch), os.fspath(output)) == ("k.c",)
    assert (output / "k.c").read_bytes() == data


def test_an_empty_file_is_taken(scratch, place, output):
    write(place, "empty.c", b"")
    assert bring_in(scratch, output) == ("empty.c",)
    assert (output / "empty.c").read_bytes() == b""


def test_walk_through_step_2_takes_none_and_renames_none(scratch, place, output):
    write(place, "Notes.md")
    write(place, "Fast.c")
    (place / "old").mkdir()
    write(place / "old", "old.c")
    (place / "dir.c").mkdir()
    write(scratch, "elsewhere.c")
    symlink(place / "ref.c", scratch / "elsewhere.c")
    before = snapshot(scratch)

    assert bring_in(scratch, output) == ()
    assert not output.parent.exists()
    assert snapshot(scratch) == before


def test_entries_not_taken_leave_their_neighbours_taken(scratch, place, output):
    write(place, "gemm.c")
    write(place, "Notes.md")
    write(place, "Fast.c")
    (place / "old").mkdir()
    write(place / "old", "old.c")
    assert bring_in(scratch, output) == ("gemm.c",)
    assert os.listdir(output) == ["gemm.c"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs os.mkfifo")
def test_a_fifo_is_not_taken(scratch, place, output):
    os.mkfifo(place / "fifo.c")
    write(place, "gemm.c")
    assert bring_in(scratch, output) == ("gemm.c",)


def test_no_place(scratch, output):
    write(scratch, "gemm.c")
    assert bring_in(scratch, output) == ()
    assert not output.parent.exists()


def test_an_empty_place(scratch, place, output):
    assert bring_in(scratch, output) == ()
    assert not output.parent.exists()


def test_a_place_that_is_a_regular_file(scratch, output):
    write(scratch, "output")
    assert bring_in(scratch, output) == ()
    assert not output.parent.exists()


def test_a_place_that_is_a_link_to_a_directory(scratch, tmp_path, output):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    write(elsewhere, "gemm.c")
    symlink(scratch / "output", elsewhere, directory=True)
    assert bring_in(scratch, output) == ()
    assert not output.parent.exists()


def test_a_place_listed_as_upper_case_is_not_the_place(scratch, output, monkeypatch):
    other = scratch / "Output"
    other.mkdir()
    write(other, "gemm.c")
    seen = recording_listdir(monkeypatch)
    assert bring_in(scratch, output) == ()
    assert not output.parent.exists()
    assert os.fspath(other) not in seen


def test_a_scratch_root_that_is_a_link_to_a_directory(tmp_path, place, output):
    linked = tmp_path / "linked"
    symlink(linked, place.parent, directory=True)
    write(place, "gemm.c")
    assert bring_in(linked, output) == ("gemm.c",)


def test_exactly_the_bound_of_files_is_taken(scratch, place, output):
    names = [f"k{number:02d}.c" for number in range(MAX_FILES)]
    for name in names:
        write(place, name)
    write(place, "Notes.md")
    assert bring_in(scratch, output) == tuple(names)


def test_one_file_above_the_bound_takes_nothing(scratch, place, output, monkeypatch):
    for number in range(MAX_FILES + 1):
        write(place, f"k{number:02d}.h")
    opened = []
    real_open = os.open
    monkeypatch.setattr(
        os, "open", lambda path, *a: opened.append(path) or real_open(path, *a)
    )
    assert bring_in(scratch, output) == ()
    assert opened == []
    assert not output.parent.exists()


def test_files_not_admitted_do_not_count_to_the_bound(scratch, place, output):
    for number in range(MAX_FILES):
        write(place, f"k{number:02d}.c")
    for number in range(MAX_FILES):
        write(place, f"K{number:02d}.c")
    assert len(bring_in(scratch, output)) == MAX_FILES


def test_the_size_bound(scratch, place, output):
    write(place, "fits.c", b"a" * MAX_FILE_BYTES)
    write(place, "large.c", b"a" * (MAX_FILE_BYTES + 1))
    write(place, "small.h")
    assert bring_in(scratch, output) == ("fits.c", "small.h")
    assert (output / "fits.c").stat().st_size == MAX_FILE_BYTES
    assert not (output / "large.c").exists()


def test_files_above_the_size_bound_do_not_count_to_the_number(scratch, place, output):
    for number in range(MAX_FILES):
        write(place, f"k{number:02d}.c")
    write(place, "large.c", b"a" * (MAX_FILE_BYTES + 1))
    assert len(bring_in(scratch, output)) == MAX_FILES


@pytest.mark.parametrize(
    "name",
    [
        "con.c",
        "nul.h",
        "com1.c",
        "lpt9.h",
        "A.c",
        "_a.c",
        "-a.c",
        "a.cc",
        "a.c.c",
        "a.txt",
        ".hidden.c",
        "a" * 63 + ".c",
    ],
)
def test_names_that_are_not_admitted_are_not_taken(scratch, place, output, name):
    write(place, name)
    write(place, "gemm.c")
    assert bring_in(scratch, output) == ("gemm.c",)
    assert sorted(os.listdir(place)) == sorted([name, "gemm.c"])


def test_the_longest_admitted_name_is_taken(scratch, place, output):
    name = "a" * 62 + ".c"
    write(place, name)
    assert bring_in(scratch, output) == (name,)


@pytest.mark.skipif(os.name != "posix", reason="mode bits are POSIX")
def test_no_mode_bit_is_carried_over(scratch, place, output):
    source = write(place, "gemm.c")
    os.chmod(source, 0o4777)
    bring_in(scratch, output)
    mode = stat.S_IMODE(os.lstat(output / "gemm.c").st_mode)
    umask = os.umask(0)
    os.umask(umask)
    assert mode == 0o666 & ~umask
    assert mode & 0o7111 == 0


@pytest.mark.parametrize("kind", ["directory", "file", "dangling link"])
def test_an_existing_output_is_refused(scratch, place, output, kind, monkeypatch):
    output.parent.mkdir(parents=True)
    if kind == "directory":
        output.mkdir()
    elif kind == "file":
        output.write_bytes(b"x")
    else:
        symlink(output, output.parent / "missing", directory=True)
    write(place, "gemm.c")
    before = snapshot(output.parent)
    seen = recording_listdir(monkeypatch)

    with pytest.raises(OutputExistsError):
        bring_in(scratch, output)

    assert os.fspath(scratch) not in seen
    assert os.fspath(place) not in seen
    assert snapshot(output.parent) == before


def test_an_output_created_after_the_check_is_refused(
    scratch, place, output, monkeypatch
):
    write(place, "gemm.c")
    output.mkdir(parents=True)
    real = os.listdir
    monkeypatch.setattr(
        os,
        "listdir",
        lambda path: [] if Path(path) == output.parent else real(path),
    )
    with pytest.raises(OutputExistsError) as caught:
        bring_in(scratch, output)
    assert isinstance(caught.value.__cause__, FileExistsError)
    assert os.listdir(output) == []


@pytest.mark.parametrize("value", [None, 1, b"/tmp/output", 2.5, ["output"]])
@pytest.mark.parametrize("argument", ["scratch_root", "output_path"])
def test_arguments_of_the_wrong_type(scratch, output, argument, value):
    arguments = {"scratch_root": scratch, "output_path": output, argument: value}
    with pytest.raises(InvalidBringInArgumentError, match=argument):
        bring_in(**arguments)


@pytest.mark.parametrize("argument", ["scratch_root", "output_path"])
def test_a_nul_character(scratch, output, argument):
    arguments = {"scratch_root": scratch, "output_path": output}
    arguments[argument] = os.fspath(arguments[argument]) + "\0"
    with pytest.raises(InvalidBringInArgumentError, match=argument):
        bring_in(**arguments)


@pytest.mark.parametrize("last", ["Output", "out", "output.c", "outputs"])
def test_an_output_path_whose_last_component_is_not_output(scratch, tmp_path, last):
    with pytest.raises(InvalidBringInArgumentError, match="last component"):
        bring_in(scratch, tmp_path / "attempt" / last)


def test_the_paths_are_checked_before_anything_is_looked_at(monkeypatch, tmp_path):
    seen = recording_listdir(monkeypatch)
    with pytest.raises(InvalidBringInArgumentError):
        bring_in(tmp_path, tmp_path / "x")
    assert seen == []


def test_a_scratch_inside_the_attempt_tree(output, place):
    write(place, "gemm.c")
    with pytest.raises(InvalidBringInArgumentError, match="inside"):
        bring_in(output / "scratch", output)
    with pytest.raises(InvalidBringInArgumentError, match="inside"):
        bring_in(output, output)


def test_an_attempt_tree_inside_the_scratch(place):
    write(place, "gemm.c")
    with pytest.raises(InvalidBringInArgumentError, match="inside"):
        bring_in(place.parent, place)
    with pytest.raises(InvalidBringInArgumentError, match="inside"):
        bring_in(place.parent, place.parent / "attempts" / "01" / "output")
    assert not (place.parent / "attempts").exists()


def test_a_link_that_puts_the_attempt_inside_the_scratch(scratch, place, tmp_path):
    write(place, "gemm.c")
    linked = tmp_path / "linked"
    symlink(linked, scratch, directory=True)
    with pytest.raises(InvalidBringInArgumentError, match="inside"):
        bring_in(scratch, linked / "attempt" / "output")


def test_a_scratch_beside_the_attempt_is_accepted(tmp_path):
    scratch = tmp_path / "out"
    (scratch / "output").mkdir(parents=True)
    write(scratch / "output", "gemm.c")
    output = tmp_path / "outer" / "output"
    assert bring_in(scratch, output) == ("gemm.c",)


def test_a_missing_scratch_root_is_a_failure(tmp_path, output):
    with pytest.raises(BringInError) as caught:
        bring_in(tmp_path / "missing", output)
    assert caught.value.failure == SCRATCH_ROOT_UNLISTABLE
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert str(caught.value) == SCRATCH_ROOT_UNLISTABLE


def test_a_scratch_root_that_is_a_file_is_a_failure(tmp_path, output):
    write(tmp_path, "scratch")
    with pytest.raises(BringInError) as caught:
        bring_in(tmp_path / "scratch", output)
    assert caught.value.failure == SCRATCH_ROOT_UNLISTABLE


def assert_failure(caught, failure, output):
    assert caught.value.failure == failure
    assert failure in BRING_IN_FAILURES
    assert isinstance(caught.value.__cause__, PermissionError)
    assert str(caught.value) == failure
    assert "denied" not in str(caught.value)
    assert not output.parent.exists()


def test_an_unlistable_scratch_root(scratch, place, output, monkeypatch):
    write(place, "gemm.c")
    failing(monkeypatch, "listdir", lambda path: path == scratch)
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert_failure(caught, SCRATCH_ROOT_UNLISTABLE, output)


def test_an_unlistable_place(scratch, place, output, monkeypatch):
    write(place, "gemm.c")
    failing(monkeypatch, "listdir", lambda path: path == place)
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert_failure(caught, PLACE_UNLISTABLE, output)


def test_an_unlistable_attempt_directory(scratch, place, output, monkeypatch):
    write(place, "gemm.c")
    output.parent.mkdir(parents=True)
    failing(monkeypatch, "listdir", lambda path: path == output.parent)
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert caught.value.failure == ATTEMPT_DIRECTORY_UNLISTABLE
    assert isinstance(caught.value.__cause__, PermissionError)
    monkeypatch.undo()
    assert os.listdir(output.parent) == []


def test_the_kind_of_the_place_undetermined(scratch, place, output, monkeypatch):
    write(place, "gemm.c")
    failing(monkeypatch, "lstat", lambda path: path == place)
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert_failure(caught, ENTRY_KIND_UNDETERMINED, output)


def test_the_kind_of_an_admitted_entry_undetermined(
    scratch, place, output, monkeypatch
):
    write(place, "gemm.c")
    write(place, "pack.c")
    failing(monkeypatch, "lstat", lambda path: path.name == "pack.c")
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert_failure(caught, ENTRY_KIND_UNDETERMINED, output)


def test_the_kind_of_a_name_not_admitted_is_not_asked(
    scratch, place, output, monkeypatch
):
    write(place, "gemm.c")
    write(place, "Notes.md")
    failing(monkeypatch, "lstat", lambda path: path.name == "Notes.md")
    assert bring_in(scratch, output) == ("gemm.c",)


def test_an_unreadable_candidate(scratch, place, output, monkeypatch):
    write(place, "gemm.c")
    write(place, "pack.c")
    failing(monkeypatch, "open", lambda path: path.name == "pack.c")
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert_failure(caught, CANDIDATE_UNREADABLE, output)


def test_a_read_error_of_a_candidate(scratch, place, output, monkeypatch):
    write(place, "gemm.c")

    def read(descriptor, size):
        raise PermissionError(errno.EACCES, "denied")

    monkeypatch.setattr(os, "read", read)
    with pytest.raises(BringInError) as caught:
        bring_in(scratch, output)
    assert_failure(caught, CANDIDATE_UNREADABLE, output)


@pytest.mark.parametrize("number", [errno.ELOOP, errno.EMLINK])
def test_a_link_met_at_the_open_is_not_taken(
    scratch, place, output, monkeypatch, number
):
    write(place, "gemm.c")
    write(place, "pack.c")

    real = os.open

    def open_(path, *args):
        if Path(path).name == "pack.c":
            raise OSError(number, "a symbolic link")
        return real(path, *args)

    monkeypatch.setattr(os, "open", open_)
    assert bring_in(scratch, output) == ("gemm.c",)


def test_a_link_swapped_in_after_the_examination_is_not_taken(
    scratch, place, output, monkeypatch
):
    write(place, "gemm.c")
    write(scratch, "secret.c", b"secret")
    symlink(place / "ref.c", scratch / "secret.c")
    real = os.lstat
    regular = real(place / "gemm.c")
    monkeypatch.setattr(
        os,
        "lstat",
        lambda path: regular if Path(path).name == "ref.c" else real(path),
    )
    assert bring_in(scratch, output) == ("gemm.c",)
    assert not (output / "ref.c").exists()


@pytest.mark.parametrize("change", ["st_ino", "st_dev", "st_mode"])
def test_an_identity_mismatch_is_not_taken(scratch, place, output, monkeypatch, change):
    write(place, "gemm.c")
    write(place, "pack.c")
    opened = {}
    real_open, real_fstat = os.open, os.fstat

    def open_(path, *args):
        descriptor = real_open(path, *args)
        opened[descriptor] = Path(path).name
        return descriptor

    def fstat(descriptor):
        result = real_fstat(descriptor)
        if opened.get(descriptor) != "pack.c":
            return result
        fields = list(result)
        index = {"st_mode": 0, "st_ino": 1, "st_dev": 2}[change]
        fields[index] = (
            stat.S_IFIFO | 0o644 if change == "st_mode" else fields[index] + 1
        )
        return os.stat_result(fields)

    monkeypatch.setattr(os, "open", open_)
    monkeypatch.setattr(os, "fstat", fstat)
    assert bring_in(scratch, output) == ("gemm.c",)


def test_a_file_that_grew_above_the_bound_is_not_taken(
    scratch, place, output, monkeypatch
):
    write(place, "gemm.c")
    write(place, "pack.c")
    opened = {}
    real_open, real_read = os.open, os.read

    def open_(path, *args):
        descriptor = real_open(path, *args)
        opened[descriptor] = Path(path).name
        return descriptor

    def read(descriptor, size):
        if opened.get(descriptor) == "pack.c":
            return b"a" * size
        return real_read(descriptor, size)

    monkeypatch.setattr(os, "open", open_)
    monkeypatch.setattr(os, "read", read)
    assert bring_in(scratch, output) == ("gemm.c",)
    assert sorted(os.listdir(output)) == ["gemm.c"]


def test_reads_in_pieces_are_joined(scratch, place, output, monkeypatch):
    data = b"0123456789" * 10
    write(place, "gemm.c", data)
    real = os.read
    monkeypatch.setattr(os, "read", lambda descriptor, size: real(descriptor, 7))
    assert bring_in(scratch, output) == ("gemm.c",)
    assert (output / "gemm.c").read_bytes() == data


def test_writes_in_pieces_are_completed(scratch, place, output, monkeypatch):
    data = b"0123456789" * 10
    write(place, "gemm.c", data)
    real = os.write
    monkeypatch.setattr(
        os, "write", lambda descriptor, view: real(descriptor, view[:3])
    )
    bring_in(scratch, output)
    assert (output / "gemm.c").read_bytes() == data


def test_a_write_error_is_raised_and_earlier_files_stay(
    scratch, place, output, monkeypatch
):
    write(place, "gemm.c")
    write(place, "pack.c")
    real = os.open

    def open_(path, flags, *args):
        if Path(path).name == "pack.c" and flags & os.O_CREAT:
            raise OSError(errno.ENOSPC, "no space left")
        return real(path, flags, *args)

    monkeypatch.setattr(os, "open", open_)
    with pytest.raises(OSError) as caught:
        bring_in(scratch, output)
    assert caught.value.errno == errno.ENOSPC
    assert not isinstance(caught.value, BringInError)
    assert os.listdir(output) == ["gemm.c"]


def test_an_attempt_directory_that_is_a_file(scratch, place, output):
    write(place, "gemm.c")
    output.parent.parent.mkdir(parents=True)
    write(output.parent.parent, output.parent.name)
    with pytest.raises(OSError) as caught:
        bring_in(scratch, output)
    assert not isinstance(caught.value, OutputExistsError)


def test_an_existing_attempt_directory_is_used(scratch, place, output):
    write(place, "gemm.c")
    output.parent.mkdir(parents=True)
    write(output.parent, "spec.json", b"{}")
    assert bring_in(scratch, output) == ("gemm.c",)
    assert sorted(os.listdir(output.parent)) == ["output", "spec.json"]


def test_the_order_does_not_depend_on_the_listing(scratch, place, output, monkeypatch):
    names = ["a.c", "b-1.c", "b.c", "b_1.c", "z.h", "0.c"]
    for name in names:
        write(place, name)
    real = os.listdir
    monkeypatch.setattr(os, "listdir", lambda path: list(reversed(real(path))))
    assert bring_in(scratch, output) == tuple(sorted(names))


def test_paths_without_a_common_path_are_apart(scratch, place, output, monkeypatch):
    write(place, "gemm.c")

    def commonpath(paths):
        raise ValueError("Paths don't have the same drive")

    monkeypatch.setattr(os.path, "commonpath", commonpath)
    assert bring_in(scratch, output) == ("gemm.c",)
