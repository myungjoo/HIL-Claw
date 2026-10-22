import errno
import os
import stat
from pathlib import Path

import pytest

from hilclaw import kernel_source, standin_copies
from hilclaw.harness import timing_build, verification_build
from hilclaw.kernel_source import (
    NO_ATTEMPT_DIRECTORY,
    NO_COMPILED_FILE,
    NO_KERNEL_SOURCE_CASES,
    NO_OUTPUT_DIRECTORY,
    InvalidOutputPathError,
    KernelSource,
    KernelSourceReadError,
)
from hilclaw.standin_copies import (
    COPY_FAILURES,
    COPY_UNWRITABLE,
    ENTRY_EXISTS,
    HARNESS_CHANGED,
    HARNESS_NOT_REGULAR_FILE,
    HARNESS_UNREADABLE,
    KERNEL_DIR,
    KERNEL_FILE_CHANGED,
    KERNEL_FILE_UNREADABLE,
    Copies,
    CopyError,
    place_copies,
)


@pytest.fixture
def output(tmp_path):
    directory = tmp_path / "attempts" / "01" / "output"
    directory.mkdir(parents=True)
    return directory


@pytest.fixture
def build_dir(tmp_path):
    directory = tmp_path / "build"
    directory.mkdir()
    return directory


@pytest.fixture
def harness(tmp_path):
    path = tmp_path / "harness" / "verification_program.c"
    path.parent.mkdir()
    path.write_bytes(b"int main(void) { return 0; }\n")
    return path


def write(directory, name, data=None):
    (directory / name).write_bytes(
        data if data is not None else f"/* {name} */\n".encode()
    )


def symlink(link, target, *, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError):
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise
        pytest.skip("this machine refuses to create a symbolic link")


def tree(directory):
    found = []
    for root, dirs, files in os.walk(directory):
        for name in dirs + files:
            found.append(Path(root, name).relative_to(directory).as_posix())
    return sorted(found)


def assert_copy(build_dir, relative, source):
    copy = build_dir / relative
    examined = os.lstat(copy)
    assert stat.S_ISREG(examined.st_mode)
    assert not stat.S_ISLNK(examined.st_mode)
    assert copy.read_bytes() == Path(source).read_bytes()
    assert not os.path.samefile(copy, source)


def test_closed_set_of_failures():
    assert KERNEL_DIR == "kernel"
    assert COPY_FAILURES == (
        KERNEL_FILE_UNREADABLE,
        KERNEL_FILE_CHANGED,
        HARNESS_UNREADABLE,
        HARNESS_NOT_REGULAR_FILE,
        HARNESS_CHANGED,
        ENTRY_EXISTS,
        COPY_UNWRITABLE,
    )
    assert len(set(COPY_FAILURES)) == len(COPY_FAILURES)
    assert not set(COPY_FAILURES) & set(NO_KERNEL_SOURCE_CASES)


def test_copy_error_text_is_its_failure():
    error = CopyError(ENTRY_EXISTS)
    assert error.failure == ENTRY_EXISTS
    assert str(error) == ENTRY_EXISTS
    assert error.args == (ENTRY_EXISTS,)


@pytest.mark.parametrize(
    "program", [verification_build.PROGRAM_SOURCE, timing_build.DRIVER_SOURCE]
)
def test_two_sources_and_a_header_with_a_real_harness_program(
    output, build_dir, program
):
    write(output, "pack.c", b'#include "pack.h"\r\nint pack(void) { return 7; }\n')
    write(output, "gemm.c", bytes(range(256)) * 4)
    write(output, "pack.h", b"int pack(void);\n")

    copies = place_copies(output, program, build_dir)

    assert copies == Copies(
        ("kernel/gemm.c", "kernel/pack.c"), ("kernel/pack.h",), program.name, None
    )
    assert tree(build_dir) == sorted(
        ["kernel", "kernel/gemm.c", "kernel/pack.c", "kernel/pack.h", program.name]
    )
    for relative in copies.compiled_set + copies.headers:
        assert_copy(build_dir, relative, output / relative.split("/")[1])
    assert_copy(build_dir, copies.harness, program)


def test_one_source(output, build_dir, harness):
    write(output, "kernel.c")
    copies = place_copies(str(output), str(harness), str(build_dir))
    assert copies == Copies(("kernel/kernel.c",), (), "verification_program.c", None)
    assert tree(build_dir) == ["kernel", "kernel/kernel.c", "verification_program.c"]
    assert all(
        type(path) is str and "\\" not in path
        for path in copies.compiled_set + (copies.harness,)
    )


def test_compiled_set_is_in_the_reader_order(output, build_dir, harness):
    for name in ("a_b.c", "a0.c", "a.c", "a-b.c"):
        write(output, name)
    copies = place_copies(output, harness, build_dir)
    assert copies.compiled_set == (
        "kernel/a-b.c",
        "kernel/a.c",
        "kernel/a0.c",
        "kernel/a_b.c",
    )


def test_the_reader_is_applied_once(monkeypatch, output, build_dir, harness):
    write(output, "a.c")
    calls = []
    real = kernel_source.read_compiled_set

    def counting(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(kernel_source, "read_compiled_set", counting)
    place_copies(output, harness, build_dir)
    assert calls == [output]


def test_a_kernel_file_named_like_the_harness_program(output, build_dir, harness):
    write(output, "verification_program.c", b"/* the kernel's own */\n")
    copies = place_copies(output, harness, build_dir)
    assert copies.compiled_set == ("kernel/verification_program.c",)
    assert copies.harness == "verification_program.c"
    assert_copy(build_dir, copies.compiled_set[0], output / "verification_program.c")
    assert_copy(build_dir, copies.harness, harness)
    assert (build_dir / copies.compiled_set[0]).read_bytes() != (
        build_dir / copies.harness
    ).read_bytes()


def test_nothing_but_kernel_files_is_copied(output, build_dir, harness):
    write(output, "a.c")
    for name in ("Fast.c", "_x.c", "notes.md", "a.o", "a.cc", "Pack.h"):
        write(output, name)
    (output / "old").mkdir()
    write(output / "old", "z.c")
    (output / "dir.h").mkdir()
    copies = place_copies(output, harness, build_dir)
    assert copies == Copies(("kernel/a.c",), (), "verification_program.c", None)
    assert tree(build_dir) == ["kernel", "kernel/a.c", "verification_program.c"]


def test_a_symbolic_link_below_output_is_not_copied(
    output, build_dir, harness, tmp_path
):
    write(output, "a.c")
    write(tmp_path, "real.h")
    symlink(output / "b.h", tmp_path / "real.h")
    copies = place_copies(output, harness, build_dir)
    assert copies.headers == ()
    assert tree(build_dir) == ["kernel", "kernel/a.c", "verification_program.c"]


@pytest.mark.parametrize("missing", NO_KERNEL_SOURCE_CASES)
def test_no_kernel_source_creates_nothing(
    monkeypatch, output, build_dir, harness, missing
):
    monkeypatch.setattr(
        kernel_source, "read_compiled_set", lambda path: KernelSource((), missing)
    )
    assert place_copies(output, harness, build_dir) == Copies((), (), None, missing)
    assert tree(build_dir) == []


@pytest.mark.parametrize(
    ("prepare", "missing"),
    [
        (lambda output: output.rmdir() or output.parent.rmdir(), NO_ATTEMPT_DIRECTORY),
        (lambda output: output.rmdir(), NO_OUTPUT_DIRECTORY),
        (lambda output: write(output, "a.h"), NO_COMPILED_FILE),
    ],
)
def test_no_kernel_source_from_the_real_reader(
    output, build_dir, tmp_path, prepare, missing
):
    prepare(output)
    absent = tmp_path / "no-such-harness.c"
    assert place_copies(output, absent, build_dir) == Copies((), (), None, missing)
    assert tree(build_dir) == []


class Fspath:
    def __init__(self, value):
        self.value = value

    def __fspath__(self):
        return self.value


@pytest.mark.parametrize(
    ("harness_value", "build_value", "parameter", "kind"),
    [
        (None, "B", "harness_program", TypeError),
        (7, "B", "harness_program", TypeError),
        (b"a/h.c", "B", "harness_program", TypeError),
        (Fspath(b"a/h.c"), "B", "harness_program", TypeError),
        ("a/h\0.c", "B", "harness_program", ValueError),
        ("a/", "B", "harness_program", ValueError),
        ("", "B", "harness_program", ValueError),
        ("a/..", "B", "harness_program", ValueError),
        ("a/.", "B", "harness_program", ValueError),
        ("a/kernel", "B", "harness_program", ValueError),
        ("a/Kernel", "B", "harness_program", ValueError),
        ("H", None, "build_dir", TypeError),
        ("H", 3.5, "build_dir", TypeError),
        ("H", b"/build", "build_dir", TypeError),
        ("H", Fspath(b"/build"), "build_dir", TypeError),
        ("H", "/bu\0ild", "build_dir", ValueError),
        ("H", "build", "build_dir", ValueError),
        ("H", "relative/build", "build_dir", ValueError),
    ],
)
def test_refusals_before_anything_is_looked_at(
    monkeypatch, output, build_dir, harness, harness_value, build_value, parameter, kind
):
    write(output, "a.c")
    harness_value = {"H": harness}.get(harness_value, harness_value)
    build_value = {"B": build_dir}.get(build_value, build_value)

    def refuse(*args, **kwargs):
        raise AssertionError("the file system was looked at")

    monkeypatch.setattr(kernel_source, "read_compiled_set", refuse)
    monkeypatch.setattr(standin_copies.os, "lstat", refuse)
    with pytest.raises(kind) as raised:
        place_copies(output, harness_value, build_value)
    assert type(raised.value) is kind
    assert raised.value.parameter == parameter
    assert tree(build_dir) == []


def test_a_build_dir_that_does_not_exist(output, harness, tmp_path):
    write(output, "a.c")
    with pytest.raises(FileNotFoundError):
        place_copies(output, harness, tmp_path / "absent")
    assert not (tmp_path / "absent").exists()


def test_a_build_dir_that_is_a_file(monkeypatch, output, harness, tmp_path):
    write(output, "a.c")
    write(tmp_path, "file")

    def refuse(path):
        raise AssertionError("the reader was applied")

    monkeypatch.setattr(kernel_source, "read_compiled_set", refuse)
    with pytest.raises(NotADirectoryError) as raised:
        place_copies(output, harness, tmp_path / "file")
    assert raised.value.errno == errno.ENOTDIR
    assert str(tmp_path) not in str(raised.value)
    assert (tmp_path / "file").read_bytes() == b"/* file */\n"


def test_a_build_dir_that_is_a_symbolic_link(output, harness, build_dir, tmp_path):
    write(output, "a.c")
    symlink(tmp_path / "link", build_dir, directory=True)
    with pytest.raises(NotADirectoryError):
        place_copies(output, harness, tmp_path / "link")
    assert tree(build_dir) == []


def test_a_build_dir_that_is_a_junction(monkeypatch, output, harness, build_dir):
    write(output, "a.c")
    real = os.lstat

    class Junction:
        def __init__(self, examined):
            self.st_mode = examined.st_mode
            self.st_reparse_tag = standin_copies._JUNCTION_TAG

    def lstat(path):
        examined = real(path)
        return Junction(examined) if os.fspath(path) == str(build_dir) else examined

    monkeypatch.setattr(standin_copies.os, "lstat", lstat)
    with pytest.raises(NotADirectoryError):
        place_copies(output, harness, build_dir)
    assert tree(build_dir) == []


def test_invalid_output_path_is_passed_on(build_dir, harness, tmp_path):
    with pytest.raises(InvalidOutputPathError):
        place_copies(tmp_path / "not-output", harness, build_dir)
    with pytest.raises(InvalidOutputPathError):
        place_copies(None, harness, build_dir)
    assert tree(build_dir) == []


def test_reader_failure_is_passed_on(monkeypatch, output, build_dir, harness):
    error = KernelSourceReadError(kernel_source.OUTPUT_DIRECTORY_UNLISTABLE)

    def fail(path):
        raise error

    monkeypatch.setattr(kernel_source, "read_compiled_set", fail)
    with pytest.raises(KernelSourceReadError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value is error
    assert tree(build_dir) == []


def test_an_existing_entry_at_the_kernel_directory_name(output, build_dir, harness):
    write(output, "a.c")
    (build_dir / KERNEL_DIR).mkdir()
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == ENTRY_EXISTS
    assert isinstance(raised.value.__cause__, FileExistsError)
    assert tree(build_dir) == ["kernel"]


def test_a_file_at_the_kernel_directory_name(output, build_dir, harness):
    write(output, "a.c")
    write(build_dir, KERNEL_DIR, b"old")
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == ENTRY_EXISTS
    assert (build_dir / KERNEL_DIR).read_bytes() == b"old"


def test_an_existing_entry_at_the_harness_copy_name(output, build_dir, harness):
    write(output, "a.c")
    write(build_dir, harness.name, b"old")
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == ENTRY_EXISTS
    assert isinstance(raised.value.__cause__, FileExistsError)
    assert (build_dir / harness.name).read_bytes() == b"old"
    assert (build_dir / "kernel" / "a.c").read_bytes() == (output / "a.c").read_bytes()


def test_a_symbolic_link_at_the_harness_copy_name_is_not_written_through(
    output, build_dir, harness, tmp_path
):
    write(output, "a.c")
    write(tmp_path, "target", b"target")
    symlink(build_dir / harness.name, tmp_path / "target")
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == ENTRY_EXISTS
    assert (tmp_path / "target").read_bytes() == b"target"


def test_a_harness_program_that_is_a_symbolic_link(
    output, build_dir, harness, tmp_path
):
    write(output, "a.c")
    symlink(tmp_path / "link.c", harness)
    with pytest.raises(CopyError) as raised:
        place_copies(output, tmp_path / "link.c", build_dir)
    assert raised.value.failure == HARNESS_NOT_REGULAR_FILE
    assert tree(build_dir) == []


def test_a_harness_program_that_is_a_directory(output, build_dir, tmp_path):
    write(output, "a.c")
    (tmp_path / "program.c").mkdir()
    with pytest.raises(CopyError) as raised:
        place_copies(output, tmp_path / "program.c", build_dir)
    assert raised.value.failure == HARNESS_NOT_REGULAR_FILE
    assert tree(build_dir) == []


def test_a_harness_program_that_does_not_exist(output, build_dir, tmp_path):
    write(output, "a.c")
    with pytest.raises(CopyError) as raised:
        place_copies(output, tmp_path / "absent.c", build_dir)
    assert raised.value.failure == HARNESS_UNREADABLE
    assert isinstance(raised.value.__cause__, FileNotFoundError)
    assert tree(build_dir) == []


def crafted(monkeypatch, output, *names):
    monkeypatch.setattr(
        kernel_source,
        "read_compiled_set",
        lambda path: KernelSource(tuple(output / name for name in names), None),
    )


def test_a_kernel_file_swapped_for_a_link_after_the_listing(
    monkeypatch, output, build_dir, harness, tmp_path
):
    write(tmp_path, "real.c")
    symlink(output / "a.c", tmp_path / "real.c")
    crafted(monkeypatch, output, "a.c")
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == KERNEL_FILE_CHANGED
    assert tree(build_dir) == []


def test_a_kernel_file_gone_after_the_listing(monkeypatch, output, build_dir, harness):
    crafted(monkeypatch, output, "a.c")
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == KERNEL_FILE_UNREADABLE
    assert tree(build_dir) == []


def test_a_kernel_file_whose_identity_changed_at_the_open(
    monkeypatch, output, build_dir, harness, tmp_path
):
    write(output, "a.c")
    write(tmp_path, "other.c")
    real_open = os.open
    kernel = os.fspath(output / "a.c")

    def swapped(path, flags, *mode):
        if os.fspath(path) == kernel:
            return real_open(tmp_path / "other.c", flags, *mode)
        return real_open(path, flags, *mode)

    monkeypatch.setattr(standin_copies.os, "open", swapped)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == KERNEL_FILE_CHANGED
    assert tree(build_dir) == []


def test_a_harness_program_whose_identity_changed_at_the_open(
    monkeypatch, output, build_dir, harness, tmp_path
):
    write(output, "a.c")
    write(tmp_path, "other.c")
    real_open = os.open

    def swapped(path, flags, *mode):
        if os.fspath(path) == os.fspath(harness):
            return real_open(tmp_path / "other.c", flags, *mode)
        return real_open(path, flags, *mode)

    monkeypatch.setattr(standin_copies.os, "open", swapped)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == HARNESS_CHANGED
    assert tree(build_dir) == []


@pytest.mark.parametrize(
    ("which", "link_errno", "failure"),
    [
        ("kernel", errno.ELOOP, KERNEL_FILE_CHANGED),
        ("kernel", errno.EACCES, KERNEL_FILE_UNREADABLE),
        ("harness", errno.EMLINK, HARNESS_CHANGED),
        ("harness", errno.EACCES, HARNESS_UNREADABLE),
    ],
)
def test_an_open_that_fails(
    monkeypatch, output, build_dir, harness, which, link_errno, failure
):
    write(output, "a.c")
    real_open = os.open
    refused = os.fspath(output / "a.c" if which == "kernel" else harness)
    error = OSError(link_errno, os.strerror(link_errno))

    def failing(path, flags, *mode):
        if os.fspath(path) == refused:
            raise error
        return real_open(path, flags, *mode)

    monkeypatch.setattr(standin_copies.os, "open", failing)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == failure
    assert raised.value.__cause__ is error
    assert tree(build_dir) == []


def test_the_open_flags_refuse_links_and_create_new_files():
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    assert standin_copies._READ_FLAGS & nofollow == nofollow
    assert standin_copies._READ_FLAGS & os.O_WRONLY == 0
    for flag in (os.O_WRONLY, os.O_CREAT, os.O_EXCL, nofollow):
        assert standin_copies._WRITE_FLAGS & flag == flag


def test_a_read_error(monkeypatch, output, build_dir, harness):
    write(output, "a.c")
    error = OSError(errno.EIO, "input/output error")

    def failing(descriptor, size):
        raise error

    monkeypatch.setattr(standin_copies.os, "read", failing)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == HARNESS_UNREADABLE
    assert raised.value.__cause__ is error
    assert tree(build_dir) == []


def test_a_read_error_of_a_kernel_file(monkeypatch, output, build_dir, harness):
    write(output, "a.c")
    real_read = os.read
    calls = []
    error = OSError(errno.EIO, "input/output error")

    def failing(descriptor, size):
        calls.append(descriptor)
        if len(calls) == 3:
            raise error
        return real_read(descriptor, size)

    monkeypatch.setattr(standin_copies.os, "read", failing)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == KERNEL_FILE_UNREADABLE
    assert tree(build_dir) == []


def test_a_write_error(monkeypatch, output, build_dir, harness):
    write(output, "a.c")
    error = OSError(errno.ENOSPC, "no space left on device", str(build_dir))

    def failing(descriptor, data):
        raise error

    monkeypatch.setattr(standin_copies.os, "write", failing)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == COPY_UNWRITABLE
    assert raised.value.__cause__ is error
    assert str(raised.value) == COPY_UNWRITABLE
    assert tree(build_dir) == ["kernel", "kernel/a.c"]


def test_short_writes_still_copy_every_byte(monkeypatch, output, build_dir, harness):
    data = bytes(range(256)) * 50
    write(output, "a.c", data)
    real_write = os.write
    monkeypatch.setattr(
        standin_copies.os,
        "write",
        lambda descriptor, view: real_write(descriptor, view[:7]),
    )
    place_copies(output, harness, build_dir)
    assert (build_dir / "kernel" / "a.c").read_bytes() == data


def test_a_mkdir_error_that_is_not_an_existing_entry(
    monkeypatch, output, build_dir, harness
):
    write(output, "a.c")
    error = PermissionError(errno.EACCES, "denied")

    def failing(path, *args, **kwargs):
        raise error

    monkeypatch.setattr(standin_copies.os, "mkdir", failing)
    with pytest.raises(CopyError) as raised:
        place_copies(output, harness, build_dir)
    assert raised.value.failure == COPY_UNWRITABLE
    assert raised.value.__cause__ is error


def test_no_link_or_shutil_copy_is_used(monkeypatch, output, build_dir, harness):
    write(output, "a.c")
    write(output, "a.h")

    def refuse(*args, **kwargs):
        raise AssertionError("a link or a shutil copy was used")

    import shutil

    for name in ("copy", "copy2", "copyfile", "copyfileobj"):
        monkeypatch.setattr(shutil, name, refuse)
    for name in ("link", "symlink", "replace", "rename"):
        monkeypatch.setattr(os, name, refuse)
    place_copies(output, harness, build_dir)
    assert tree(build_dir) == [
        "kernel",
        "kernel/a.c",
        "kernel/a.h",
        "verification_program.c",
    ]
