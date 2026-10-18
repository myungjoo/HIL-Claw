import copy
from pathlib import Path

import pytest

from hilclaw import check_build, check_failure, check_result, clang_build
from hilclaw.check_build import BUILT, place_error, read_build
from hilclaw.check_failure import (
    KIND_BUILD_DIRECTORY_UNUSABLE,
    KIND_BUILD_INPUT_MISSING,
    KIND_BUILD_OUTPUT_MISSING,
    KIND_COMPILER_UNAVAILABLE,
    KIND_SETTINGS_REFUSED,
)

S7 = "build_exit_status"
S8 = "build_time_limit"
MARKER = "zq7-marker-zq7"
KINDS = {
    value
    for name, value in vars(check_failure).items()
    if name.startswith("KIND_") and isinstance(value, str)
}


def build_result(ok=False, returncode=1, timed_out=False):
    return clang_build.BuildResult(
        ok=ok,
        returncode=returncode,
        timed_out=timed_out,
        output=Path("out", "verify"),
        log="compiler output",
        command=("clang", "-o", "verify"),
        duration_s=0.5,
    )


OK = build_result(ok=True, returncode=0)
TIMED_OUT = build_result(returncode=None, timed_out=True)
FAILED = build_result(returncode=1)
SIGNALLED = build_result(returncode=-9)
NO_ARTEFACT = build_result(returncode=0)
NO_STATUS = build_result(returncode=None)

BUILDS = [
    (OK, BUILT),
    (TIMED_OUT, S8),
    (FAILED, S7),
    (SIGNALLED, S7),
    (NO_ARTEFACT, KIND_BUILD_OUTPUT_MISSING),
    (NO_STATUS, None),
]


def os_error():
    return OSError(5, "Input/output error", "tmp-file")


def removal():
    return PermissionError(13, "Permission denied", "tmp-file")


def with_attribute(error, name, value):
    setattr(error, name, value)
    return error


def named(cls, parameter, *args):
    return with_attribute(cls(*args or ("refused",)), "parameter", parameter)


def unicode_error(parameter):
    error = UnicodeEncodeError("utf-8", "\udcff", 0, 1, "surrogates not allowed")
    return with_attribute(error, "parameter", parameter)


def run_error(removal_error=None, **members):
    return clang_build.CompilerRunError(os_error(), removal_error, **members)


@pytest.mark.parametrize(("result", "expected"), BUILDS)
def test_read_build_applies_the_reading_of_adr_0060(result, expected):
    assert read_build(result) == expected


def test_read_build_ok_wins_over_the_other_fields():
    assert read_build(build_result(ok=True, returncode=3, timed_out=True)) is BUILT


def test_read_build_time_limit_wins_over_a_status():
    assert read_build(build_result(returncode=2, timed_out=True)) == S8


def test_read_build_status_that_is_no_exact_int_is_not_placed():
    assert read_build(build_result(returncode=True)) is None
    assert read_build(build_result(returncode="1")) is None


@pytest.mark.parametrize(
    "value",
    [
        tuple(FAILED),
        None,
        MARKER,
        clang_build.CompilerRunError(os_error()),
    ],
    ids=["tuple", "none", "str", "error"],
)
def test_read_build_refuses_a_value_that_is_no_build_result(value):
    with pytest.raises(TypeError) as caught:
        read_build(value)
    message = str(caught.value)
    assert type(value).__name__ in message
    assert MARKER not in message
    assert "compiler output" not in message


def test_read_build_refuses_a_subclass_of_build_result():
    class Other(clang_build.BuildResult):
        pass

    with pytest.raises(TypeError, match="Other"):
        read_build(Other(*FAILED))


@pytest.mark.parametrize(("result", "expected"), BUILDS)
def test_temporary_not_removed_answers_by_its_carried_build(result, expected):
    error = clang_build.TemporaryNotRemovedError(os_error(), result)
    answer = place_error(error)
    assert answer == expected


@pytest.mark.parametrize("result", [tuple(OK), None, MARKER])
def test_temporary_not_removed_with_no_build_result_raises(result):
    error = clang_build.TemporaryNotRemovedError(os_error(), result)
    with pytest.raises(TypeError) as caught:
        place_error(error)
    assert MARKER not in str(caught.value)


@pytest.mark.parametrize(
    "cls", [clang_build.ArtefactNotPlacedError, clang_build.ArtefactNotCheckedError]
)
@pytest.mark.parametrize("removal_error", [None, removal()])
@pytest.mark.parametrize("result", [NO_ARTEFACT, OK, FAILED])
def test_artefact_errors_are_s9(cls, removal_error, result):
    assert place_error(cls(os_error(), result, removal_error)) == (
        KIND_BUILD_OUTPUT_MISSING
    )


@pytest.mark.parametrize("removal_error", [None, removal()])
def test_compiler_not_started_is_s6(removal_error):
    error = clang_build.CompilerNotStartedError(
        FileNotFoundError(2, "No such file or directory", "clang"), removal_error
    )
    assert place_error(error) == KIND_COMPILER_UNAVAILABLE


@pytest.mark.parametrize("removal_error", [None, removal()])
@pytest.mark.parametrize(
    ("members", "expected"),
    [
        ({"timed_out": True}, S8),
        ({"timed_out": True, "log": "partial"}, S8),
        ({"timed_out": True, "returncode": 1}, S8),
        ({"timed_out": True, "returncode": 0}, S8),
        ({}, None),
        ({"log": "all of it"}, None),
        ({"returncode": 0}, KIND_BUILD_OUTPUT_MISSING),
        ({"returncode": 1}, S7),
        ({"returncode": -11}, S7),
        ({"returncode": True}, None),
    ],
)
def test_compiler_run_error_rows(removal_error, members, expected):
    assert place_error(run_error(removal_error, **members)) == expected


def test_compiler_not_found_is_s6():
    assert place_error(clang_build.CompilerNotFoundError("clang")) == (
        KIND_COMPILER_UNAVAILABLE
    )


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            with_attribute(FileNotFoundError(2, "missing"), "path_role", "source"),
            KIND_BUILD_INPUT_MISSING,
        ),
        (
            with_attribute(IsADirectoryError(21, "dir"), "path_role", "source"),
            KIND_BUILD_INPUT_MISSING,
        ),
        (
            with_attribute(PermissionError(13, "denied"), "path_role", "source"),
            KIND_BUILD_INPUT_MISSING,
        ),
        (
            with_attribute(NotADirectoryError(20, "not dir"), "path_role", "source"),
            KIND_BUILD_INPUT_MISSING,
        ),
        (
            with_attribute(FileNotFoundError(2, "missing"), "path_role", "output"),
            KIND_BUILD_DIRECTORY_UNUSABLE,
        ),
        (
            with_attribute(IsADirectoryError(21, "dir"), "path_role", "output"),
            KIND_BUILD_DIRECTORY_UNUSABLE,
        ),
        (
            with_attribute(NotADirectoryError(20, "not dir"), "path_role", "output"),
            KIND_BUILD_DIRECTORY_UNUSABLE,
        ),
        (
            with_attribute(OSError(5, "io"), "path_role", "output"),
            KIND_BUILD_DIRECTORY_UNUSABLE,
        ),
        (NotADirectoryError(20, "not dir"), KIND_BUILD_DIRECTORY_UNUSABLE),
        (OSError(5, "io"), None),
        (FileNotFoundError(2, "missing"), None),
        (with_attribute(PermissionError(13, "denied"), "path_role", "cwd"), None),
        (with_attribute(NotADirectoryError(20, "not dir"), "path_role", "cwd"), None),
        (with_attribute(OSError(5, "io"), "path_role", None), None),
    ],
)
def test_plain_os_error_rows(error, expected):
    assert place_error(error) == expected


@pytest.mark.parametrize("parameter", check_build._SETTINGS)
@pytest.mark.parametrize("cls", [TypeError, ValueError])
def test_named_setting_is_s4(cls, parameter):
    assert place_error(named(cls, parameter)) == KIND_SETTINGS_REFUSED


def test_the_settings_are_the_five_of_the_records():
    assert set(check_build._SETTINGS) == {
        "timeout_s",
        "flags",
        "trailing_flags",
        "compiler",
        "env",
    }


@pytest.mark.parametrize("parameter", ["flags", "compiler", "env"])
def test_unicode_encode_error_of_a_setting_is_s4(parameter):
    assert place_error(unicode_error(parameter)) == KIND_SETTINGS_REFUSED


@pytest.mark.parametrize(
    "parameter", ["sources", "output", "cwd", "kernel_sources", "bogus", None]
)
@pytest.mark.parametrize("cls", [TypeError, ValueError])
def test_named_argument_is_not_placed(cls, parameter):
    assert place_error(named(cls, parameter)) is None


@pytest.mark.parametrize(
    "error",
    [
        TypeError("unnamed"),
        ValueError("unnamed"),
        unicode_error("output"),
        RuntimeError("other"),
        LookupError("other"),
        named(LookupError, "flags"),
        named(RuntimeError, "env"),
        KeyboardInterrupt(),
        SystemExit(1),
        GeneratorExit(),
    ],
    ids=lambda error: type(error).__name__,
)
def test_errors_without_a_row_are_not_placed(error):
    assert place_error(error) is None


def test_a_request_to_end_is_not_placed_even_with_members():
    interrupt = with_attribute(KeyboardInterrupt(), "parameter", "flags")
    interrupt.path_role = "source"
    assert place_error(interrupt) is None


@pytest.mark.parametrize(
    "error",
    [
        clang_build.TemporaryNotRemovedError(os_error(), FAILED),
        clang_build.ArtefactNotPlacedError(os_error(), NO_ARTEFACT),
        clang_build.ArtefactNotCheckedError(os_error(), NO_ARTEFACT),
        clang_build.CompilerNotStartedError(os_error()),
        run_error(returncode=1),
    ],
    ids=lambda error: type(error).__name__,
)
@pytest.mark.parametrize("role", ["source", "output", "cwd"])
def test_the_five_classes_ignore_a_path_role(error, role):
    expected = place_error(error)
    error.path_role = role
    assert place_error(error) == expected
    assert expected not in (KIND_BUILD_INPUT_MISSING, KIND_BUILD_DIRECTORY_UNUSABLE)


def test_compiler_run_error_ignores_a_parameter():
    assert place_error(with_attribute(run_error(timed_out=True), "parameter", "x")) == (
        S8
    )


PURITY_CASES = [
    clang_build.TemporaryNotRemovedError(os_error(), OK),
    clang_build.ArtefactNotPlacedError(os_error(), NO_ARTEFACT, removal()),
    clang_build.ArtefactNotCheckedError(os_error(), NO_ARTEFACT, removal()),
    clang_build.CompilerNotStartedError(os_error(), removal()),
    run_error(removal(), timed_out=False, log="text", returncode=0),
    clang_build.CompilerNotFoundError("clang"),
    with_attribute(FileNotFoundError(2, "missing"), "path_role", "source"),
    NotADirectoryError(20, "not dir"),
    named(TypeError, "flags"),
    unicode_error("output"),
    KeyboardInterrupt(),
]


@pytest.mark.parametrize("error", PURITY_CASES, ids=lambda e: type(e).__name__)
def test_place_error_changes_nothing_of_the_object(error):
    members = copy.copy(vars(error))
    args = error.args
    place_error(error)
    assert vars(error) == members
    assert error.args == args


def test_read_build_changes_nothing_of_the_result():
    before = tuple(FAILED)
    read_build(FAILED)
    assert tuple(FAILED) == before


def test_every_answer_is_a_known_value():
    allowed_strings = set(check_result.CONDITIONS[:2]) | KINDS
    answers = [read_build(result) for result, _ in BUILDS]
    answers += [place_error(error) for error in PURITY_CASES]
    answers += [
        place_error(run_error(timed_out=True)),
        place_error(run_error(returncode=4)),
        place_error(clang_build.TemporaryNotRemovedError(os_error(), TIMED_OUT)),
    ]
    for answer in answers:
        assert answer is None or answer is BUILT or answer in allowed_strings
    assert {S7, S8} <= set(answers)


def test_built_is_no_other_value():
    assert BUILT is not None
    assert BUILT not in check_result.CONDITIONS
    assert BUILT not in KINDS
    assert BUILT not in check_failure.BACKEND_KINDS
    assert set(check_result.CONDITIONS[:2]) == {S7, S8}
