import os
from pathlib import Path

import pytest

from hilclaw import (
    check_failure,
    clang_build,
    local_run,
    run_operation,
    run_result,
    standin_container,
    vendor_adapter,
)
from hilclaw.vendor_adapter import (
    BROKEN,
    GO_ON,
    TOOL_FAILURE,
    Outcome,
    broken,
    check_timeout,
    go_on,
    interpret_build,
    interpret_container_build,
    interpret_container_run,
    interpret_run,
    measure,
    tool_failure,
)

PROGRAM = os.path.join("opt", "tool", "bin", "runner")


def build_result(ok=True, returncode=0, timed_out=False, output=Path("k.o")):
    return clang_build.BuildResult(
        ok=ok,
        returncode=returncode,
        timed_out=timed_out,
        output=output,
        log="",
        command=("clang",),
        duration_s=0.1,
    )


def run_result_of(returncode=0, timed_out=False, stdout=b"out"):
    return local_run.RunResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=b"",
        command=(PROGRAM,),
        duration_s=0.1,
    )


def container_result(returncode=0, timed_out=False, stdout=b"out"):
    return standin_container.ContainerResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=b"",
        command=("docker",),
        duration_s=0.1,
        name="hilclaw-standin-" + "0" * 32,
        removal=None,
    )


def with_attributes(error, **attributes):
    for name, value in attributes.items():
        setattr(error, name, value)
    return error


def assert_outcome(outcome, form, condition=None, kind=None):
    assert type(outcome) is Outcome
    assert outcome.form == form
    assert outcome.condition == condition
    assert outcome.kind == kind
    assert type(outcome.message) is str and outcome.message


def test_spellings_are_the_existing_constants():
    assert vendor_adapter.FORMS == (GO_ON, BROKEN, TOOL_FAILURE)
    assert (
        vendor_adapter.BUILD_TIME_LIMIT,
        vendor_adapter.BUILD_EXIT_STATUS,
        vendor_adapter.TIME_LIMIT,
        vendor_adapter.EXIT_STATUS,
    ) == run_result.CONDITIONS[:4]
    assert set(run_operation.CONDITIONS) == set(run_result.CONDITIONS[:4])
    assert vendor_adapter.KINDS == (
        check_failure.KIND_COMPILER_UNAVAILABLE,
        check_failure.KIND_BUILD_OUTPUT_MISSING,
        check_failure.KIND_EXECUTABLE_UNSTARTABLE,
    )
    assert set(vendor_adapter.KINDS) <= check_failure.BACKEND_KINDS
    assert vendor_adapter.PROBE_STATES == ("present", "absent", "unreadable")


def test_go_on_carries_and_defaults_its_message():
    outcome = go_on(Path("a"))
    assert_outcome(outcome, GO_ON)
    assert outcome.carried == Path("a")
    assert go_on(b"", "said").message == "said"


@pytest.mark.parametrize("condition", run_result.CONDITIONS[:4])
def test_broken_takes_each_condition(condition):
    outcome = broken(condition)
    assert_outcome(outcome, BROKEN, condition=condition)
    assert outcome.carried is None


@pytest.mark.parametrize("kind", vendor_adapter.KINDS)
def test_tool_failure_takes_each_kind(kind):
    assert_outcome(tool_failure(kind, "m"), TOOL_FAILURE, kind=kind)


@pytest.mark.parametrize("value", run_result.CONDITIONS[4:] + ("", "exit"))
def test_broken_refuses_other_conditions(value):
    with pytest.raises(ValueError, match="condition"):
        broken(value)


@pytest.mark.parametrize("value", [None, 1, b"exit_status"])
def test_broken_refuses_other_types(value):
    with pytest.raises(TypeError, match="condition"):
        broken(value)


@pytest.mark.parametrize(
    "value", ["settings_refused", "build_directory_unusable", "device_unavailable"]
)
def test_tool_failure_refuses_other_kinds(value):
    with pytest.raises(ValueError, match="kind"):
        tool_failure(value)


def test_tool_failure_and_messages_refuse_other_types():
    with pytest.raises(TypeError, match="kind"):
        tool_failure(None)
    with pytest.raises(TypeError, match="message"):
        go_on(b"", b"bytes")


def test_build_ok_goes_on_with_the_artefact():
    outcome = interpret_build(build_result(output=Path("x") / "k.o"))
    assert_outcome(outcome, GO_ON)
    assert outcome.carried == Path("x") / "k.o"


@pytest.mark.parametrize("returncode", [1, 2, -11])
def test_build_non_zero_status_is_build_exit_status(returncode):
    outcome = interpret_build(build_result(ok=False, returncode=returncode))
    assert_outcome(outcome, BROKEN, condition="build_exit_status")


def test_build_timeout_is_build_time_limit():
    outcome = interpret_build(build_result(ok=False, returncode=None, timed_out=True))
    assert_outcome(outcome, BROKEN, condition="build_time_limit")


def test_build_status_zero_without_ok_is_output_missing():
    outcome = interpret_build(build_result(ok=False, returncode=0))
    assert_outcome(outcome, TOOL_FAILURE, kind="build_output_missing")


def test_build_without_status_is_no_row():
    with pytest.raises(ValueError, match="no row"):
        interpret_build(build_result(ok=False, returncode=None))


@pytest.mark.parametrize(
    "error",
    [
        clang_build.CompilerNotFoundError("not found"),
        clang_build.CompilerNotStartedError(OSError(8, "Exec format error")),
    ],
)
def test_build_compiler_errors_are_compiler_unavailable(error):
    assert_outcome(interpret_build(error), TOOL_FAILURE, kind="compiler_unavailable")


@pytest.mark.parametrize(
    "error",
    [
        clang_build.CompilerRunError(OSError(5, "I/O"), timed_out=True),
        clang_build.ArtefactNotPlacedError(OSError(13, "denied"), build_result()),
        clang_build.TemporaryNotRemovedError(OSError(13, "denied"), build_result()),
        with_attributes(FileNotFoundError(2, "no"), path_role="source"),
        with_attributes(ValueError("bad"), parameter="flags"),
        RuntimeError("other"),
        KeyboardInterrupt(),
    ],
)
def test_build_other_errors_are_not_placed(error):
    assert interpret_build(error) is None


@pytest.mark.parametrize("value", [None, "k.o", run_result_of(), container_result()])
def test_build_refuses_other_values(value):
    with pytest.raises(TypeError) as caught:
        interpret_build(value)
    assert caught.value.parameter == "answer"


def test_run_status_zero_goes_on_with_its_output():
    outcome = interpret_run(run_result_of(stdout=b"report"), PROGRAM)
    assert_outcome(outcome, GO_ON)
    assert outcome.carried == b"report"


@pytest.mark.parametrize("returncode", [1, 3, 125, 127, -9])
def test_run_non_zero_status_or_signal_is_exit_status(returncode):
    outcome = interpret_run(run_result_of(returncode=returncode), PROGRAM)
    assert_outcome(outcome, BROKEN, condition="exit_status")


def test_run_timeout_is_time_limit():
    outcome = interpret_run(run_result_of(returncode=None, timed_out=True), PROGRAM)
    assert_outcome(outcome, BROKEN, condition="time_limit")


@pytest.mark.parametrize("returncode", [None, 0.0, True])
def test_run_status_of_another_type_is_no_row(returncode):
    with pytest.raises(ValueError, match="no row"):
        interpret_run(run_result_of(returncode=returncode), PROGRAM)


@pytest.mark.parametrize(
    "error",
    [
        local_run.ProgramNotFoundError("not found"),
        OSError(8, "Exec format error", os.path.abspath(PROGRAM)),
        PermissionError(13, "Permission denied", PROGRAM),
    ],
)
def test_run_unstartable_program_is_executable_unstartable(error):
    outcome = interpret_run(error, PROGRAM)
    assert_outcome(outcome, TOOL_FAILURE, kind="executable_unstartable")


def test_run_unstartable_program_given_as_path_object():
    error = OSError(8, "Exec format error", os.path.abspath(PROGRAM))
    outcome = interpret_run(error, Path(PROGRAM))
    assert_outcome(outcome, TOOL_FAILURE, kind="executable_unstartable")


@pytest.mark.parametrize(
    "error",
    [
        OSError(5, "I/O error"),
        OSError(8, "Exec format error", "other-program"),
        OSError(8, "Exec format error", b"runner"),
        OSError(8, "Exec format error", ""),
        with_attributes(NotADirectoryError(20, "no", PROGRAM), path_role="cwd"),
        with_attributes(TypeError("bad"), parameter="command"),
        OverflowError("too long"),
        KeyboardInterrupt(),
    ],
)
def test_run_other_errors_are_not_placed(error):
    assert interpret_run(error, PROGRAM) is None


@pytest.mark.parametrize("value", [None, b"", build_result(), container_result()])
def test_run_refuses_other_values(value):
    with pytest.raises(TypeError) as caught:
        interpret_run(value, PROGRAM)
    assert caught.value.parameter == "answer"


def test_container_build_goes_on_with_a_regular_artefact(tmp_path):
    artefact = tmp_path / "k"
    artefact.write_bytes(b"x")
    outcome = interpret_container_build(container_result(), artefact)
    assert_outcome(outcome, GO_ON)
    assert outcome.carried == artefact


@pytest.mark.parametrize("make", [None, "directory", "parent_is_file"])
def test_container_build_status_zero_without_artefact_is_output_missing(tmp_path, make):
    artefact = tmp_path / "k"
    if make == "directory":
        artefact.mkdir()
    if make == "parent_is_file":
        artefact.write_bytes(b"x")
        artefact = artefact / "k"
    outcome = interpret_container_build(container_result(), artefact)
    assert_outcome(outcome, TOOL_FAILURE, kind="build_output_missing")


@pytest.mark.parametrize("returncode", [125, 126, 127])
def test_container_build_runtime_status_is_compiler_unavailable(tmp_path, returncode):
    outcome = interpret_container_build(container_result(returncode), tmp_path / "k")
    assert_outcome(outcome, TOOL_FAILURE, kind="compiler_unavailable")


@pytest.mark.parametrize("returncode", [1, 124, 128, -9])
def test_container_build_other_status_is_build_exit_status(tmp_path, returncode):
    outcome = interpret_container_build(container_result(returncode), tmp_path / "k")
    assert_outcome(outcome, BROKEN, condition="build_exit_status")


def test_container_build_timeout_is_build_time_limit(tmp_path):
    result = container_result(None, timed_out=True)
    outcome = interpret_container_build(result, tmp_path / "k")
    assert_outcome(outcome, BROKEN, condition="build_time_limit")


def test_container_build_without_status_is_no_row(tmp_path):
    with pytest.raises(ValueError, match="no row"):
        interpret_container_build(container_result(None), tmp_path / "k")


def test_container_build_passes_on_a_stat_error(tmp_path, monkeypatch):
    def refused(path):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(vendor_adapter.os, "stat", refused)
    with pytest.raises(PermissionError):
        interpret_container_build(container_result(), tmp_path / "k")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            local_run.ProgramNotFoundError("client"),
            (TOOL_FAILURE, "compiler_unavailable"),
        ),
        (
            standin_container.NoNumericUserError("user"),
            (TOOL_FAILURE, "compiler_unavailable"),
        ),
        (
            with_attributes(ValueError("image"), parameter="image"),
            (TOOL_FAILURE, "compiler_unavailable"),
        ),
        (
            with_attributes(OSError(5, "rm"), container_name="n"),
            (BROKEN, "build_time_limit"),
        ),
    ],
)
def test_container_build_errors_by_standin_answer(tmp_path, error, expected):
    outcome = interpret_container_build(error, tmp_path / "k")
    form, value = expected
    if form == BROKEN:
        assert_outcome(outcome, BROKEN, condition=value)
    else:
        assert_outcome(outcome, TOOL_FAILURE, kind=value)


@pytest.mark.parametrize(
    "error",
    [
        NotADirectoryError(20, "no"),
        with_attributes(ValueError("t"), parameter="timeout_s"),
        with_attributes(OverflowError("t"), container_name="n", removal=None),
        OSError(5, "after start"),
        KeyboardInterrupt(),
    ],
)
def test_container_errors_outside_the_kinds_are_not_placed(tmp_path, error):
    assert interpret_container_build(error, tmp_path / "k") is None
    assert interpret_container_run(error) is None


def test_container_run_status_zero_goes_on_with_its_output():
    outcome = interpret_container_run(container_result(stdout=b"rep"))
    assert_outcome(outcome, GO_ON)
    assert outcome.carried == b"rep"


@pytest.mark.parametrize("returncode", [125, 126, 127])
def test_container_run_statuses_125_to_127_stay_exit_status(returncode):
    outcome = interpret_container_run(container_result(returncode))
    assert_outcome(outcome, BROKEN, condition="exit_status")


@pytest.mark.parametrize("returncode", [1, 3, -11])
def test_container_run_other_status_is_exit_status(returncode):
    assert_outcome(
        interpret_container_run(container_result(returncode)),
        BROKEN,
        condition="exit_status",
    )


def test_container_run_timeout_and_no_status():
    outcome = interpret_container_run(container_result(None, timed_out=True))
    assert_outcome(outcome, BROKEN, condition="time_limit")
    with pytest.raises(ValueError, match="no row"):
        interpret_container_run(container_result(None))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            local_run.ProgramNotFoundError("client"),
            (TOOL_FAILURE, "executable_unstartable"),
        ),
        (
            standin_container.NoNumericUserError("user"),
            (TOOL_FAILURE, "executable_unstartable"),
        ),
        (with_attributes(OSError(5, "rm"), container_name="n"), (BROKEN, "time_limit")),
    ],
)
def test_container_run_errors_by_standin_answer(error, expected):
    outcome = interpret_container_run(error)
    form, value = expected
    if form == BROKEN:
        assert_outcome(outcome, BROKEN, condition=value)
    else:
        assert_outcome(outcome, TOOL_FAILURE, kind=value)


@pytest.mark.parametrize("value", [None, run_result_of(), build_result()])
def test_container_interprets_refuse_other_values(tmp_path, value):
    with pytest.raises(TypeError) as caught:
        interpret_container_run(value)
    assert caught.value.parameter == "answer"
    with pytest.raises(TypeError) as caught:
        interpret_container_build(value, tmp_path / "k")
    assert caught.value.parameter == "answer"


@pytest.mark.parametrize("make", [run_result_of, container_result])
@pytest.mark.parametrize("figure", [None, 1, 2**70])
def test_measure_status_zero_is_the_pair(make, figure):
    pair = measure(make(stdout=b"report"), figure)
    assert type(pair) is tuple
    assert pair == (b"report", figure)


@pytest.mark.parametrize("make", [run_result_of, container_result])
@pytest.mark.parametrize("returncode", [1, 125, 127, -11])
def test_measure_non_zero_status_is_exit_status(make, returncode):
    assert measure(make(returncode=returncode), 5) == "exit_status"


@pytest.mark.parametrize("make", [run_result_of, container_result])
def test_measure_timeout_is_time_limit(make):
    answer = measure(make(returncode=None, timed_out=True))
    assert answer == "time_limit"
    assert answer in run_operation.CONDITIONS


def test_measure_status_of_another_type_is_no_row():
    with pytest.raises(ValueError, match="no row"):
        measure(run_result_of(returncode=None))


@pytest.mark.parametrize("value", [None, build_result(), (b"r", None), OSError()])
def test_measure_refuses_other_answers(value):
    with pytest.raises(TypeError) as caught:
        measure(value)
    assert caught.value.parameter == "answer"


@pytest.mark.parametrize(
    ("figure", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (True, TypeError),
        (1.0, TypeError),
        ("1", TypeError),
    ],
)
def test_measure_refuses_other_figures(figure, error):
    with pytest.raises(error) as caught:
        measure(run_result_of(), figure)
    assert caught.value.parameter == "figure"


def test_measure_reads_only_its_arguments(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("measure read something")

    monkeypatch.setattr(vendor_adapter.os, "stat", refused)
    monkeypatch.setattr("builtins.open", refused)
    monkeypatch.setattr("time.monotonic", refused)
    monkeypatch.setattr("time.time", refused)
    assert measure(run_result_of(stdout=b"r"), 3) == (b"r", 3)


@pytest.mark.parametrize("value", [1, 0.5, 2**40])
def test_check_timeout_accepts_positive_finite(value):
    assert check_timeout(value) is None


@pytest.mark.parametrize(
    ("value", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (float("inf"), ValueError),
        (float("nan"), ValueError),
        (True, TypeError),
        ("1", TypeError),
        (None, TypeError),
    ],
)
def test_check_timeout_refuses(value, error):
    with pytest.raises(error) as caught:
        check_timeout(value, "limit")
    assert caught.value.parameter == "limit"
