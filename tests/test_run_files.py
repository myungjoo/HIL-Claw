import inspect

import pytest

from hilclaw import run_files, tools
from hilclaw.tools import ToolFailure

# Synthetic values only: no run, file content or reader class of a real run.
RUN = "run-a"
NAME = "STATE.json"
FILE = f"runs/{RUN}/{NAME}"
MISSING = tools.KIND_RUN_FILE_MISSING
UNREADABLE = tools.KIND_RUN_FILE_UNREADABLE
INVALID = tools.KIND_RUN_FILE_INVALID
UNSUPPORTED = tools.KIND_RUN_FILE_UNSUPPORTED
ROOT_GONE = f"{FILE}: is missing: the data root is not an existing directory"


class Invalid(ValueError):
    pass


class Beyond(Invalid):
    pass


class Unsupported(Exception):
    pass


KINDS = {Invalid: INVALID, Unsupported: UNSUPPORTED}


def raised_in(data_root, error, kinds=KINDS):
    reading = run_files.reading(data_root, RUN, NAME, kinds)
    with pytest.raises(BaseException) as caught, reading:
        raise error
    return caught.value


def test_the_public_names():
    public = sorted(
        name
        for name, value in vars(run_files).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    )
    assert public == [
        "NOT_THERE",
        "data_root_is_there",
        "read_failure",
        "reading",
        "relative",
    ]
    assert run_files.NOT_THERE == (FileNotFoundError, NotADirectoryError)
    assert list(inspect.signature(run_files.reading).parameters) == [
        "data_root",
        "run_id",
        "name",
        "kinds",
    ]
    assert list(inspect.signature(run_files.read_failure).parameters) == [
        "data_root",
        "run_id",
        "name",
        "error",
    ]


# --- relative ---


@pytest.mark.parametrize("name", ["STATE.json", "events.ndjson", "instance.json"])
def test_relative_is_the_path_below_the_data_root(name):
    assert run_files.relative(RUN, name) == f"runs/{RUN}/{name}"


def test_relative_checks_nothing():
    assert run_files.relative("Bad Run", "") == "runs/Bad Run/"


# --- data_root_is_there ---


def test_an_existing_directory_is_there(tmp_path):
    assert run_files.data_root_is_there(tmp_path) is True
    assert run_files.data_root_is_there(str(tmp_path)) is True


def test_a_missing_path_and_a_file_are_not_there(tmp_path):
    file = tmp_path / "file"
    file.write_bytes(b"x")
    assert run_files.data_root_is_there(tmp_path / "missing") is False
    assert run_files.data_root_is_there(file) is False
    assert run_files.data_root_is_there(file / "below") is False
    assert sorted(item.name for item in tmp_path.iterdir()) == ["file"]


# --- read_failure ---


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(2, "No such file or directory", "/example/absolute"),
        NotADirectoryError(20, "Not a directory"),
        FileNotFoundError("data root is not an existing directory: /example"),
    ],
)
def test_not_there_is_missing_and_says_whether_the_data_root_is_there(tmp_path, error):
    failure = run_files.read_failure(tmp_path, RUN, NAME, error)
    assert type(failure) is ToolFailure
    assert (failure.kind, failure.message) == (MISSING, f"{FILE}: is missing")
    assert failure.__cause__ is None
    for gone in (tmp_path / "missing", str(tmp_path / "missing")):
        failure = run_files.read_failure(gone, RUN, NAME, error)
        assert (failure.kind, failure.message) == (MISSING, ROOT_GONE)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("error", "reported"),
    [
        (
            PermissionError(13, "Permission denied", "/example/absolute"),
            "PermissionError: Permission denied",
        ),
        (IsADirectoryError(21, "Is a directory"), "IsADirectoryError: Is a directory"),
        (OSError(5, "Input/output error"), "OSError: Input/output error"),
        (OSError("example failure of the read"), "OSError"),
        (OSError(), "OSError"),
        (TimeoutError(), "TimeoutError"),
    ],
)
def test_every_other_failure_of_the_file_system_is_unreadable(
    tmp_path, error, reported
):
    for data_root in (tmp_path, tmp_path / "missing"):
        failure = run_files.read_failure(data_root, RUN, NAME, error)
        assert type(failure) is ToolFailure
        assert failure.kind == UNREADABLE
        assert failure.message == f"{FILE}: could not be read: {reported}"
        assert "/example" not in failure.message
        assert failure.__cause__ is None


@pytest.mark.parametrize(
    "error",
    [ValueError("example"), Invalid(f"{FILE}: example"), KeyError("k"), None, "text"],
)
def test_read_failure_answers_for_an_os_error_only(tmp_path, error):
    with pytest.raises(TypeError, match="error must be an OSError"):
        run_files.read_failure(tmp_path, RUN, NAME, error)


# --- reading ---


def test_a_read_that_raises_nothing_is_left_alone(tmp_path):
    with run_files.reading(tmp_path, RUN, NAME, KINDS) as nothing:
        value = "read"
    assert (nothing, value) == (None, "read")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("error", "kind"),
    [
        (Invalid(f"{FILE}: breaks a rule"), INVALID),
        (Beyond(f"{FILE}: position 2 is beyond"), INVALID),
        (Unsupported(f"{FILE}: schema_version: 2 is not supported"), UNSUPPORTED),
    ],
)
def test_a_class_of_the_reader_is_answered_with_its_kind_and_its_message(
    tmp_path, error, kind
):
    failure = raised_in(tmp_path, error)
    assert type(failure) is ToolFailure
    assert (failure.kind, failure.message) == (kind, str(error))
    assert failure.__cause__ is error


def test_the_first_class_of_kinds_that_matches_decides():
    error = Beyond(f"{FILE}: example")
    assert raised_in("unused", error, {Beyond: MISSING, Invalid: INVALID}).kind == (
        MISSING
    )
    assert raised_in("unused", error, {Invalid: INVALID, Beyond: MISSING}).kind == (
        INVALID
    )


def test_a_class_of_kinds_comes_before_the_rule_for_an_os_error(tmp_path):
    error = FileNotFoundError(f"{FILE}: example")
    failure = raised_in(tmp_path / "missing", error, {FileNotFoundError: INVALID})
    assert (failure.kind, failure.message) == (INVALID, f"{FILE}: example")
    assert failure.__cause__ is error


@pytest.mark.parametrize("kinds", [KINDS, {}])
def test_an_os_error_of_the_read_is_missing_or_unreadable(tmp_path, kinds):
    gone = FileNotFoundError(2, "No such file or directory", "/example/absolute")
    failure = raised_in(tmp_path, gone, kinds)
    assert (failure.kind, failure.message) == (MISSING, f"{FILE}: is missing")
    assert failure.__cause__ is gone
    failure = raised_in(tmp_path / "missing", NotADirectoryError(), kinds)
    assert (failure.kind, failure.message) == (MISSING, ROOT_GONE)
    denied = PermissionError(13, "Permission denied", "/example/absolute")
    failure = raised_in(tmp_path, denied, kinds)
    assert failure.kind == UNREADABLE
    assert failure.message == (
        f"{FILE}: could not be read: PermissionError: Permission denied"
    )
    assert failure.__cause__ is denied


@pytest.mark.parametrize(
    "error",
    [
        ValueError("example"),
        KeyError("example"),
        TypeError("example"),
        RecursionError(),
        ToolFailure("example_failure", "of the tests"),
        ToolFailure(tools.KIND_STEP_OPEN, "a reserved kind"),
        KeyboardInterrupt(),
        SystemExit(9),
    ],
    ids=lambda error: type(error).__name__,
)
@pytest.mark.parametrize("kinds", [KINDS, {}])
def test_what_is_no_row_passes_through_unchanged(tmp_path, error, kinds):
    assert raised_in(tmp_path, error, kinds) is error
    assert error.__cause__ is None


def test_the_reader_class_of_another_read_is_no_row_here(tmp_path):
    error = Unsupported(f"{FILE}: example")
    assert raised_in(tmp_path, error, {Invalid: INVALID}) is error
