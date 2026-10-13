import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from hilclaw import clang_build, kernel_source
from hilclaw.kernel_source import (
    ATTEMPT_DIRECTORY_UNLISTABLE,
    ENTRY_KIND_UNDETERMINED,
    NO_ATTEMPT_DIRECTORY,
    NO_COMPILED_FILE,
    NO_KERNEL_SOURCE_CASES,
    NO_OUTPUT_DIRECTORY,
    OUTPUT_DIRECTORY_UNLISTABLE,
    OUTPUT_NAME,
    READER_FAILURES,
    InvalidOutputPathError,
    KernelSource,
    KernelSourceReadError,
    is_admitted_name,
    read_compiled_set,
)

# ADR-0055 decision 5, N2.
RESERVED_STEMS = (
    ["con", "prn", "aux", "nul"]
    + [f"com{n}" for n in range(1, 10)]
    + [f"lpt{n}" for n in range(1, 10)]
)


@pytest.fixture
def attempt(tmp_path):
    directory = tmp_path / "attempts" / "01"
    directory.mkdir(parents=True)
    return directory


@pytest.fixture
def output(attempt):
    directory = attempt / "output"
    directory.mkdir()
    return directory


@pytest.fixture
def clang():
    if os.name != "posix":
        pytest.skip("the executable of this test needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def write(directory, *names):
    for name in names:
        (directory / name).write_text("int x;\n", encoding="ascii", newline="\n")


def symlink(link, target, *, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError):
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise
        pytest.skip("this machine refuses to create a symbolic link")


def fake_listing(monkeypatch, listings, kinds=None):
    """Answer listings and kinds from tables keyed by path text; other paths go to the system."""
    listings = {os.fspath(key): value for key, value in listings.items()}
    kinds = {os.fspath(key): value for key, value in (kinds or {}).items()}
    real_listdir, real_lstat = os.listdir, os.lstat

    def answer(table, real, path):
        value = table.get(os.fspath(path), real)
        if value is real:
            return real(path)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(
        kernel_source.os, "listdir", lambda path: answer(listings, real_listdir, path)
    )
    monkeypatch.setattr(
        kernel_source.os, "lstat", lambda path: answer(kinds, real_lstat, path)
    )


REGULAR = os.stat_result((stat.S_IFREG | 0o644, 0, 0, 1, 0, 0, 0, 0, 0, 0))
DIRECTORY = os.stat_result((stat.S_IFDIR | 0o755, 0, 0, 1, 0, 0, 0, 0, 0, 0))


def names_of(answer):
    return [path.name for path in answer.compiled_set]


def test_closed_sets_of_constants():
    assert OUTPUT_NAME == "output"
    assert NO_KERNEL_SOURCE_CASES == (
        NO_ATTEMPT_DIRECTORY,
        NO_OUTPUT_DIRECTORY,
        NO_COMPILED_FILE,
    )
    assert READER_FAILURES == (
        ATTEMPT_DIRECTORY_UNLISTABLE,
        OUTPUT_DIRECTORY_UNLISTABLE,
        ENTRY_KIND_UNDETERMINED,
    )
    every = NO_KERNEL_SOURCE_CASES + READER_FAILURES
    assert len(set(every)) == 6
    assert all(type(value) is str for value in every)


@pytest.mark.parametrize(
    "name",
    [
        "a.c",
        "a.h",
        "gemm.c",
        "0.c",
        "a_b-c9.h",
        "a" * 62 + ".c",
        "a" + "_" * 61 + ".h",
        "com0.c",
        "lpt0.h",
        "cons.c",
        "nul1.c",
        "com10.c",
        "c.c",
    ],
)
def test_admitted_names(name):
    assert is_admitted_name(name) is True


@pytest.mark.parametrize(
    "name",
    [
        "",
        "a.c\n",
        "\na.c",
        "a" * 63 + ".c",
        "A.c",
        "a.C",
        "aB.c",
        "_a.c",
        "-a.c",
        ".a.c",
        ".c",
        "a.b.c",
        "a.cc",
        "a.o",
        "a",
        "a.",
        "a.c.",
        "a .c",
        "a.c ",
        " a.c",
        "a/b.c",
        "a\\b.c",
        "..",
        ".",
        "../a.c",
        "é.c",
        "aé.c",
        "１.c",
        "a１.c",
        "a\x00.c",
        "a.c\x00",
        "CON.c",
    ],
)
def test_names_that_are_not_admitted(name):
    assert is_admitted_name(name) is False


@pytest.mark.parametrize("stem", RESERVED_STEMS)
def test_reserved_stems_are_not_admitted(stem):
    assert is_admitted_name(stem + ".c") is False


def test_reserved_stems_are_22_and_hold_for_a_header():
    assert len(RESERVED_STEMS) == 22
    assert is_admitted_name("aux.h") is False
    assert is_admitted_name("lpt9.h") is False


class StrSubclass(str):
    pass


@pytest.mark.parametrize(
    "value", [None, b"a.c", 1, ["a.c"], Path("a.c"), StrSubclass("a.c")]
)
def test_a_value_that_is_not_exactly_a_str_is_not_admitted(value):
    assert is_admitted_name(value) is False


def test_the_walk_through_of_the_record(output):
    write(output, "pack.h", "pack.c", "gemm.c")
    answer = read_compiled_set(output)
    assert answer == KernelSource((output / "gemm.c", output / "pack.c"), None)
    assert all(type(path) is type(output) for path in answer.compiled_set)


def test_one_file(output):
    write(output, "kernel.c")
    assert read_compiled_set(output) == KernelSource((output / "kernel.c",), None)


@pytest.mark.parametrize(
    "listed",
    [
        ["a.c", "a_b.c", "a0.c", "a-b.c"],
        ["a_b.c", "a0.c", "a.c", "a-b.c"],
        ["a0.c", "a-b.c", "a_b.c", "a.c"],
    ],
)
def test_order_is_byte_order_of_the_names_whatever_the_listing(
    monkeypatch, output, listed
):
    write(output, *listed)
    fake_listing(monkeypatch, {output: listed})
    answer = read_compiled_set(output)
    assert names_of(answer) == ["a-b.c", "a.c", "a0.c", "a_b.c"]
    assert answer.missing is None


def test_neither_number_nor_size_is_a_bound(output):
    names = [f"k{n:02d}.c" for n in range(17)]
    write(output, *names)
    (output / "big.c").write_bytes(b"/" * 262_145)
    assert names_of(read_compiled_set(output)) == ["big.c", *names]


def test_a_thousand_files(monkeypatch, output):
    names = [f"k{n:04d}.c" for n in range(1000)]
    kinds = {output / name: REGULAR for name in names}
    fake_listing(monkeypatch, {output: list(reversed(names))}, kinds)
    assert names_of(read_compiled_set(output)) == names


def test_str_and_path_give_the_same_answer_below_the_given_path(output, monkeypatch):
    write(output, "a.c")
    assert read_compiled_set(str(output)) == read_compiled_set(output)
    monkeypatch.chdir(output.parent)
    relative = read_compiled_set("output")
    assert relative == KernelSource((Path("output") / "a.c",), None)
    assert not relative.compiled_set[0].is_absolute()


def test_no_attempt_directory(tmp_path):
    answer = read_compiled_set(tmp_path / "attempts" / "01" / "output")
    assert answer == KernelSource((), NO_ATTEMPT_DIRECTORY)


def test_attempt_path_is_a_regular_file(tmp_path):
    (tmp_path / "01").write_text("", encoding="ascii")
    answer = read_compiled_set(tmp_path / "01" / "output")
    assert answer == KernelSource((), NO_ATTEMPT_DIRECTORY)


def test_attempt_directory_without_output(attempt):
    write(attempt, "spec.json", "a.c")
    assert read_compiled_set(attempt / "output") == KernelSource(
        (), NO_OUTPUT_DIRECTORY
    )


def test_output_is_a_regular_file(attempt):
    write(attempt, "output")
    assert read_compiled_set(attempt / "output") == KernelSource(
        (), NO_OUTPUT_DIRECTORY
    )


def test_output_is_a_symbolic_link_to_a_directory(attempt, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    write(elsewhere, "a.c")
    symlink(attempt / "output", elsewhere, directory=True)
    assert read_compiled_set(attempt / "output") == KernelSource(
        (), NO_OUTPUT_DIRECTORY
    )


def test_an_entry_listed_as_Output_is_not_the_output(attempt):
    (attempt / "Output").mkdir()
    write(attempt / "Output", "a.c")
    assert read_compiled_set(attempt / "output") == KernelSource(
        (), NO_OUTPUT_DIRECTORY
    )


def test_Output_is_not_the_output_where_a_lookup_of_the_path_finds_it(
    monkeypatch, attempt
):
    listing = {attempt: ["Output"], attempt / "output": ["a.c"]}
    kinds = {
        attempt / "Output": DIRECTORY,
        attempt / "output": DIRECTORY,
        attempt / "output" / "a.c": REGULAR,
    }
    fake_listing(monkeypatch, listing, kinds)
    assert read_compiled_set(attempt / "output") == KernelSource(
        (), NO_OUTPUT_DIRECTORY
    )


def test_empty_output(output):
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_only_a_header(output):
    write(output, "a.h")
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_only_names_that_are_not_admitted(output):
    write(output, "Fast.c", "Notes.md", "_a.c", "a.cc")
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_only_regular_files_under_reserved_stems(monkeypatch, output):
    names = ["con.c", "nul.c", "com1.c", "lpt9.c", "aux.h"]
    kinds = {output / name: REGULAR for name in names}
    fake_listing(monkeypatch, {output: names}, kinds)
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_nothing_below_a_sub_directory_is_looked_at(output):
    (output / "old").mkdir()
    write(output / "old", "a.c")
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_a_symbolic_link_to_a_regular_file_is_no_kernel_file(output, tmp_path):
    write(tmp_path, "real.c")
    symlink(output / "a.c", tmp_path / "real.c")
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_a_directory_under_an_admitted_name_is_no_kernel_file(output):
    (output / "a.c").mkdir()
    assert read_compiled_set(output) == KernelSource((), NO_COMPILED_FILE)


def test_two_names_differing_only_in_case(monkeypatch, output):
    kinds = {os.path.join(output, name): REGULAR for name in ("a.c", "A.c")}
    fake_listing(monkeypatch, {output: ["A.c", "a.c"]}, kinds)
    assert names_of(read_compiled_set(output)) == ["a.c"]


def test_mixed_entries_and_nothing_is_opened(monkeypatch, output):
    write(output, "gemm.c", "pack.c", "pack.h", "Notes.md", "Fast.c", "-x.c", "a.o")
    (output / "old").mkdir()
    write(output / "old", "z.c")
    (output / "dir.c").mkdir()

    def refuse(*args, **kwargs):
        raise AssertionError("the reader opened something")

    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", refuse)
        patch.setattr("io.open", refuse)
        patch.setattr(os, "open", refuse)
        patch.setattr(os, "stat", refuse)
        patch.setattr(os, "scandir", refuse)
        answer = read_compiled_set(output)
    assert answer == KernelSource((output / "gemm.c", output / "pack.c"), None)


def test_an_attempt_directory_that_is_a_symbolic_link_counts(tmp_path):
    real = tmp_path / "real"
    (real / "output").mkdir(parents=True)
    write(real / "output", "a.c")
    symlink(tmp_path / "01", real, directory=True)
    path = tmp_path / "01" / "output"
    assert read_compiled_set(path) == KernelSource((path / "a.c",), None)


@pytest.mark.parametrize(
    "error", [PermissionError(13, "denied"), OSError(5, "input/output error")]
)
def test_attempt_directory_that_cannot_be_listed(monkeypatch, output, error):
    write(output, "a.c")
    fake_listing(monkeypatch, {output.parent: error})
    with pytest.raises(KernelSourceReadError) as raised:
        read_compiled_set(output)
    assert raised.value.failure == ATTEMPT_DIRECTORY_UNLISTABLE
    assert raised.value.__cause__ is error


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(13, "denied"),
        OSError(5, "input/output error"),
        FileNotFoundError(2, "gone since the listing of the attempt directory"),
        NotADirectoryError(20, "replaced since the listing"),
    ],
)
def test_output_that_cannot_be_listed(monkeypatch, output, error):
    write(output, "a.c")
    fake_listing(monkeypatch, {output: error})
    with pytest.raises(KernelSourceReadError) as raised:
        read_compiled_set(output)
    assert raised.value.failure == OUTPUT_DIRECTORY_UNLISTABLE
    assert raised.value.__cause__ is error


@pytest.mark.parametrize(
    "error", [PermissionError(13, "denied"), FileNotFoundError(2, "gone")]
)
@pytest.mark.parametrize("with_output", [True, False])
def test_kind_of_an_entry_of_the_attempt_directory(
    monkeypatch, attempt, error, with_output
):
    if with_output:
        (attempt / "output").mkdir()
        write(attempt / "output", "a.c")
    write(attempt, "spec.json")
    fake_listing(monkeypatch, {}, {attempt / "spec.json": error})
    with pytest.raises(KernelSourceReadError) as raised:
        read_compiled_set(attempt / "output")
    assert raised.value.failure == ENTRY_KIND_UNDETERMINED
    assert raised.value.__cause__ is error


def test_kind_of_the_entry_output_itself(monkeypatch, output):
    error = PermissionError(13, "denied")
    fake_listing(monkeypatch, {}, {output: error})
    with pytest.raises(KernelSourceReadError) as raised:
        read_compiled_set(output)
    assert raised.value.failure == ENTRY_KIND_UNDETERMINED


@pytest.mark.parametrize("name", ["b.c", "b.h", "Notes.md", "Fast.c", "con.c", "old"])
def test_kind_of_an_entry_of_output_is_not_passed_over(monkeypatch, output, name):
    write(output, "a.c")
    error = PermissionError(13, "denied")
    fake_listing(monkeypatch, {output: ["a.c", name]}, {output / name: error})
    with pytest.raises(KernelSourceReadError) as raised:
        read_compiled_set(output)
    assert raised.value.failure == ENTRY_KIND_UNDETERMINED
    assert raised.value.__cause__ is error


def test_a_failure_shows_its_member_and_nothing_of_the_system(monkeypatch, output):
    error = PermissionError(13, "denied", str(output))
    fake_listing(monkeypatch, {output: error})
    with pytest.raises(KernelSourceReadError) as raised:
        read_compiled_set(output)
    assert str(raised.value) == OUTPUT_DIRECTORY_UNLISTABLE
    assert raised.value.args == (OUTPUT_DIRECTORY_UNLISTABLE,)
    assert not isinstance(raised.value, OSError)


@pytest.mark.parametrize(
    "tail", ["Output", "OUTPUT", "outputs", "output.d", "01", "..", "output/a.c"]
)
def test_a_path_whose_last_component_is_not_output(output, tail):
    write(output, "a.c")
    with pytest.raises(InvalidOutputPathError):
        read_compiled_set(output.parent / tail)


@pytest.mark.parametrize("value", ["", ".", "/"])
def test_a_path_without_a_last_component(value):
    with pytest.raises(InvalidOutputPathError):
        read_compiled_set(value)


@pytest.mark.parametrize("value", [None, b"attempt/output", 7, ["output"], object()])
def test_a_value_that_is_no_path(value):
    with pytest.raises(InvalidOutputPathError):
        read_compiled_set(value)


def test_an_invalid_path_is_looked_at_by_nothing(monkeypatch, attempt):
    def refuse(path):
        raise AssertionError("the reader looked at the file system")

    monkeypatch.setattr(kernel_source.os, "listdir", refuse)
    monkeypatch.setattr(kernel_source.os, "lstat", refuse)
    with pytest.raises(InvalidOutputPathError):
        read_compiled_set(attempt)
    with pytest.raises(InvalidOutputPathError):
        read_compiled_set(None)


def test_invalid_output_path_error_is_a_value_error():
    assert issubclass(InvalidOutputPathError, ValueError)


def test_compiled_set_builds_with_clang_and_no_include_path(clang, output, tmp_path):
    files = {
        "a.c": '#include "pack.h"\nint main(void) { return pack() == 7 ? 0 : 1; }\n',
        "pack.c": '#include "pack.h"\nint pack(void) { return 7; }\n',
        "pack.h": "int pack(void);\n",
    }
    for name, text in files.items():
        (output / name).write_text(text, encoding="ascii", newline="\n")
    elsewhere = tmp_path / "build"
    elsewhere.mkdir()

    answer = read_compiled_set(output)
    assert names_of(answer) == ["a.c", "pack.c"]
    built = clang_build.build(
        answer.compiled_set, elsewhere / "program", timeout_s=120, cwd=elsewhere
    )

    assert built.ok, built.log
    assert not any(flag.startswith("-I") for flag in built.command)
    run = subprocess.run(
        [str(elsewhere / "program")], cwd=elsewhere, timeout=60, check=False
    )
    assert run.returncode == 0
