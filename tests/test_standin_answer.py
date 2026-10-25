import errno

import pytest

from hilclaw import (
    check_failure,
    check_result,
    kernel_source,
    local_run,
    run_failure,
    run_result,
    standin_answer,
    standin_container,
    standin_copies,
    standin_image,
    standin_waiter_line,
)
from hilclaw.standin_answer import (
    BUILD,
    COPIES,
    GO_ON,
    IMAGE,
    PROCESS,
    STEPS,
    Failure,
    build_dir_removable,
    place_error,
    read_build,
    read_copies,
    read_image_value,
    read_process,
    read_timing_process,
)

BUILD_TIME_LIMIT = "build_time_limit"
BUILD_EXIT_STATUS = "build_exit_status"
TIME_LIMIT = "time_limit"
EXIT_STATUS = "exit_status"
SECRET = "zq7-/home/user/image:tag-zq7"
WAITER_LINE = b"waiter_max_rss_kib 2048\n"
REPORT = b"resolution_ns 1\ninterval_ns 5\nstop\n"


def removal(returncode=0, timed_out=False):
    return standin_container.Removal(
        returncode=returncode,
        timed_out=timed_out,
        stdout=b"",
        stderr=b"",
        command=("docker", "rm", "--force", "hilclaw-standin-x"),
        duration_s=0.1,
    )


def container(returncode=0, timed_out=False, stdout=b"", stderr=b"", gone=None):
    return standin_container.ContainerResult(
        returncode=None if timed_out else returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        command=("docker", "run"),
        duration_s=1.0,
        name="hilclaw-standin-" + "0" * 32,
        removal=gone,
    )


def failure(kind):
    def check(answer):
        assert type(answer) is Failure
        assert answer.kind == kind
        assert type(answer.message) is str and answer.message
        assert SECRET not in answer.message
        return True

    return check


def with_attributes(error, **attributes):
    for name, value in attributes.items():
        setattr(error, name, value)
    return error


def test_conditions_are_values_of_both_contracts():
    for value in (BUILD_TIME_LIMIT, BUILD_EXIT_STATUS, TIME_LIMIT, EXIT_STATUS):
        assert value in check_result.CONDITIONS
        assert value in run_result.CONDITIONS


def test_every_kind_is_a_backend_kind_of_both_contracts():
    answers = [
        read_image_value(None),
        read_copies(standin_copies.Copies((), (), None, "no_compiled_file")),
        read_build(container(125)),
        place_error(standin_image.ImageRefusedError("x"), IMAGE),
        place_error(standin_copies.CopyError("copy_unwritable"), COPIES),
        place_error(standin_copies.CopyError("kernel_file_changed"), COPIES),
        place_error(kernel_source.KernelSourceReadError("x"), COPIES),
        place_error(local_run.ProgramNotFoundError("x"), PROCESS),
        place_error(with_attributes(ValueError(), parameter="timeout_s"), BUILD),
    ]
    for answer in answers:
        assert type(answer) is Failure
        assert answer.kind in check_failure.BACKEND_KINDS
        assert answer.kind in run_failure.BACKEND_KINDS


# Happy paths


def test_ok_build_container_goes_on():
    assert read_build(container(0)) is GO_ON


def test_ok_process_container_goes_on():
    assert read_process(container(0, stdout=REPORT)) is GO_ON


def test_timing_container_with_value_line_gives_report_and_figure():
    answer = read_timing_process(container(0, stdout=REPORT + b"\n" + WAITER_LINE))
    assert answer == standin_waiter_line.WaiterRead(REPORT, 2048 * 1024)


def test_timing_container_with_none_line_gives_report_without_figure():
    stdout = REPORT + b"\n" + standin_waiter_line.NONE_LINE + b"\n"
    assert read_timing_process(container(0, stdout=stdout)) == (
        standin_waiter_line.WaiterRead(REPORT, None)
    )


# C1, C2: the image


def test_no_image_named_is_compiler_unavailable():
    assert failure(check_failure.KIND_COMPILER_UNAVAILABLE)(read_image_value(None))


def test_named_image_goes_on():
    assert read_image_value("registry/clang:18") is GO_ON


def test_refused_image_is_compiler_unavailable():
    error = standin_image.ImageRefusedError(SECRET)
    assert failure(check_failure.KIND_COMPILER_UNAVAILABLE)(place_error(error, IMAGE))


def test_other_error_of_the_image_read_is_not_placed():
    assert place_error(TypeError("environ must be a mapping"), IMAGE) is None
    assert place_error(ValueError(SECRET), IMAGE) is None


@pytest.mark.parametrize(
    ("step", "kind"),
    [
        (BUILD, check_failure.KIND_COMPILER_UNAVAILABLE),
        (PROCESS, check_failure.KIND_EXECUTABLE_UNSTARTABLE),
    ],
)
@pytest.mark.parametrize("cls", [TypeError, ValueError])
def test_image_refused_by_the_container_start(step, kind, cls):
    error = with_attributes(cls(SECRET), parameter="image")
    assert failure(kind)(place_error(error, step))


# C3, C4: no client, no numeric user


@pytest.mark.parametrize(
    ("step", "kind"),
    [
        (BUILD, check_failure.KIND_COMPILER_UNAVAILABLE),
        (PROCESS, check_failure.KIND_EXECUTABLE_UNSTARTABLE),
    ],
)
def test_client_not_found(step, kind):
    error = local_run.ProgramNotFoundError(SECRET)
    assert failure(kind)(place_error(error, step))


@pytest.mark.parametrize(
    ("step", "kind"),
    [
        (BUILD, check_failure.KIND_COMPILER_UNAVAILABLE),
        (PROCESS, check_failure.KIND_EXECUTABLE_UNSTARTABLE),
    ],
)
def test_no_numeric_user(step, kind):
    error = standin_container.NoNumericUserError(SECRET)
    assert failure(kind)(place_error(error, step))


# C5 to C8: statuses


@pytest.mark.parametrize("status", [125, 126, 127])
def test_runtime_status_of_a_build_is_compiler_unavailable(status):
    answer = read_build(container(status, stderr=SECRET.encode()))
    assert failure(check_failure.KIND_COMPILER_UNAVAILABLE)(answer)


@pytest.mark.parametrize("status", [1, 2, 124, 128, 137, 255, -9])
def test_other_non_zero_status_of_a_build_is_build_exit_status(status):
    assert read_build(container(status)) == BUILD_EXIT_STATUS


@pytest.mark.parametrize("status", [125, 126, 127, 1, 137, -9])
def test_non_zero_status_of_a_verification_process_is_exit_status(status):
    stderr = b"docker: Error response from daemon: Container command not found"
    assert read_process(container(status, stderr=stderr)) == EXIT_STATUS


@pytest.mark.parametrize("status", [None, True, 0.0, "0"])
def test_status_that_is_not_exactly_an_int_is_not_placed(status):
    result = container(status)
    assert read_build(result) is None
    assert read_process(result) is None
    assert read_timing_process(result) is None


# Decision 4: the timing process


@pytest.mark.parametrize("status", [125, 126, 127, 1, -9])
def test_timing_process_with_waiter_line_and_non_zero_status(status):
    result = container(status, stdout=REPORT + b"\n" + WAITER_LINE)
    assert read_timing_process(result) == EXIT_STATUS


@pytest.mark.parametrize("status", [125, 126, 127, 1, 137, -9])
def test_timing_process_without_waiter_line_and_non_zero_status(status):
    result = container(status, stdout=REPORT)
    assert read_timing_process(result) == EXIT_STATUS


def test_timing_process_without_waiter_line_and_status_zero_is_open():
    assert read_timing_process(container(0, stdout=REPORT)) is None
    assert read_timing_process(container(0, stdout=b"")) is None


def test_waiter_line_not_last_gives_no_figure():
    stdout = REPORT + b"\n" + WAITER_LINE + b"stop\n"
    assert read_timing_process(container(0, stdout=stdout)) is None
    assert read_timing_process(container(1, stdout=stdout)) == EXIT_STATUS


def test_check_and_run_tools_differ_only_for_the_process_stream():
    plain = container(0, stdout=REPORT)
    assert read_process(plain) is GO_ON
    assert read_timing_process(plain) is None
    measured = container(0, stdout=REPORT + b"\n" + WAITER_LINE)
    assert read_process(measured) is GO_ON
    assert isinstance(read_timing_process(measured), standin_waiter_line.WaiterRead)


def test_timing_process_refuses_stdout_that_is_not_bytes():
    with pytest.raises(TypeError):
        read_timing_process(container(0, stdout=bytearray(REPORT)))


# C10: time limits, whatever the removal gave


@pytest.mark.parametrize(
    "gone",
    [removal(0), removal(1), removal(None, timed_out=True), None],
)
def test_time_limit_whatever_the_removal(gone):
    result = container(timed_out=True, gone=gone)
    assert read_build(result) == BUILD_TIME_LIMIT
    assert read_process(result) == TIME_LIMIT
    assert read_timing_process(result) == TIME_LIMIT


def test_timed_out_timing_process_with_waiter_line_is_time_limit():
    result = container(timed_out=True, stdout=REPORT + b"\n" + WAITER_LINE)
    assert read_timing_process(result) == TIME_LIMIT


@pytest.mark.parametrize(
    ("step", "condition"), [(BUILD, BUILD_TIME_LIMIT), (PROCESS, TIME_LIMIT)]
)
@pytest.mark.parametrize("cls", [OSError, LookupError, ArithmeticError, RuntimeError])
def test_forced_removal_that_raised_after_timeout(step, condition, cls):
    error = with_attributes(cls(SECRET), container_name="hilclaw-standin-x")
    assert place_error(error, step) == condition


# C11: an exception of the client run after the start


@pytest.mark.parametrize("step", [BUILD, PROCESS])
@pytest.mark.parametrize("gone", [removal(0), None])
def test_overflow_after_start_is_settings_refused(step, gone):
    error = with_attributes(
        OverflowError(SECRET), container_name="hilclaw-standin-x", removal=gone
    )
    assert failure(check_failure.KIND_SETTINGS_REFUSED)(place_error(error, step))


@pytest.mark.parametrize("step", [BUILD, PROCESS])
def test_other_error_after_start_is_not_placed(step):
    error = with_attributes(
        RuntimeError(SECRET), container_name="hilclaw-standin-x", removal=removal(0)
    )
    assert place_error(error, step) is None


# C12, C13, C15, C16: the copies


@pytest.mark.parametrize(
    "value",
    [
        standin_copies.KERNEL_FILE_UNREADABLE,
        standin_copies.KERNEL_FILE_CHANGED,
        standin_copies.HARNESS_UNREADABLE,
        standin_copies.HARNESS_NOT_REGULAR_FILE,
        standin_copies.HARNESS_CHANGED,
    ],
)
def test_copy_reading_failure_is_build_input_missing(value):
    error = standin_copies.CopyError(value)
    assert failure(check_failure.KIND_BUILD_INPUT_MISSING)(place_error(error, COPIES))


@pytest.mark.parametrize(
    "value", [standin_copies.ENTRY_EXISTS, standin_copies.COPY_UNWRITABLE]
)
def test_copy_writing_failure_is_build_directory_unusable(value):
    error = standin_copies.CopyError(value)
    answer = place_error(error, COPIES)
    assert failure(check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)(answer)


def test_every_copy_failure_is_placed():
    for value in standin_copies.COPY_FAILURES:
        assert place_error(standin_copies.CopyError(value), COPIES) is not None


def test_copy_error_of_an_unknown_failure_is_not_placed():
    assert place_error(standin_copies.CopyError("example_failure"), COPIES) is None


def test_not_a_directory_of_the_copies_is_build_directory_unusable():
    error = NotADirectoryError(errno.ENOTDIR, "not a directory")
    answer = place_error(error, COPIES)
    assert failure(check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)(answer)


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(errno.EACCES, "denied", SECRET),
        FileNotFoundError(errno.ENOENT, "missing", SECRET),
        OSError(errno.EIO, "io"),
    ],
)
def test_other_os_error_of_the_copies_is_open(error):
    assert place_error(error, COPIES) is None


def test_reader_failure_is_kernel_source_unreadable():
    error = kernel_source.KernelSourceReadError("attempt_directory_unlistable")
    answer = place_error(error, COPIES)
    assert failure(check_failure.KIND_KERNEL_SOURCE_UNREADABLE)(answer)


def test_no_kernel_source():
    copies = standin_copies.Copies((), (), None, kernel_source.NO_COMPILED_FILE)
    assert failure(check_failure.KIND_NO_KERNEL_SOURCE)(read_copies(copies))


def test_copies_placed_go_on():
    copies = standin_copies.Copies(
        ("kernel/gemm.c",), (), "verification_program.c", None
    )
    assert read_copies(copies) is GO_ON


@pytest.mark.parametrize(
    "error",
    [
        kernel_source.InvalidOutputPathError(SECRET),
        with_attributes(TypeError(), parameter="harness_program"),
        with_attributes(ValueError(), parameter="build_dir"),
        RuntimeError(SECRET),
    ],
)
def test_own_argument_errors_of_the_copies_are_not_placed(error):
    assert place_error(error, COPIES) is None


# C13, C14, C16, C17: errors of the container start


@pytest.mark.parametrize("step", [BUILD, PROCESS])
def test_build_dir_value_error_is_build_directory_unusable(step):
    error = with_attributes(ValueError(SECRET), parameter="build_dir")
    answer = place_error(error, step)
    assert failure(check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)(answer)


@pytest.mark.parametrize("step", [BUILD, PROCESS])
def test_not_a_directory_is_build_directory_unusable(step):
    error = NotADirectoryError(errno.ENOTDIR, "not a directory", SECRET)
    answer = place_error(error, step)
    assert failure(check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)(answer)


@pytest.mark.parametrize("step", [BUILD, PROCESS])
@pytest.mark.parametrize(
    "error",
    [
        PermissionError(errno.EACCES, "denied", SECRET),
        FileNotFoundError(errno.ENOENT, "missing", SECRET),
        OSError(errno.EIO, "io"),
    ],
)
def test_other_os_error_of_the_start_is_open(step, error):
    assert place_error(error, step) is None


@pytest.mark.parametrize("step", [BUILD, PROCESS])
@pytest.mark.parametrize("parameter", ["timeout_s", "removal_timeout_s"])
@pytest.mark.parametrize("cls", [TypeError, ValueError])
def test_time_limit_setting_refused(step, parameter, cls):
    error = with_attributes(cls(SECRET), parameter=parameter)
    assert failure(check_failure.KIND_SETTINGS_REFUSED)(place_error(error, step))


@pytest.mark.parametrize("step", [BUILD, PROCESS])
@pytest.mark.parametrize(
    "error",
    [
        with_attributes(TypeError(), parameter="build_dir"),
        with_attributes(ValueError(), parameter="program"),
        with_attributes(TypeError(), parameter="arguments"),
        with_attributes(ValueError(), parameter="client"),
        TypeError(SECRET),
        ValueError(SECRET),
        RuntimeError(SECRET),
    ],
)
def test_own_argument_errors_of_the_start_are_not_placed(step, error):
    assert place_error(error, step) is None


# C18 and negative cases


@pytest.mark.parametrize("step", STEPS)
@pytest.mark.parametrize(
    "error",
    [
        KeyboardInterrupt(),
        SystemExit(1),
        with_attributes(KeyboardInterrupt(), container_name="hilclaw-standin-x"),
        with_attributes(
            KeyboardInterrupt(), container_name="hilclaw-standin-x", removal=None
        ),
    ],
)
def test_request_to_end_is_not_placed(step, error):
    assert place_error(error, step) is None


@pytest.mark.parametrize("step", STEPS)
def test_value_that_is_no_exception_is_not_placed(step):
    assert place_error("not an exception", step) is None
    assert place_error(None, step) is None


def test_place_error_refuses_a_step():
    with pytest.raises(TypeError, match="step"):
        place_error(OSError(), 1)
    with pytest.raises(ValueError, match="step"):
        place_error(OSError(), "timing")


def test_place_error_does_not_change_the_error():
    error = with_attributes(OverflowError(SECRET), container_name="n", removal=None)
    before = (error.args, dict(vars(error)))
    place_error(error, BUILD)
    assert (error.args, dict(vars(error))) == before


@pytest.mark.parametrize("value", [b"image", 1, ["image"]])
def test_read_image_value_refuses_other_types(value):
    with pytest.raises(TypeError, match=type(value).__name__):
        read_image_value(value)


@pytest.mark.parametrize(
    "value",
    [None, ("kernel/gemm.c",), standin_copies.Copies((), (), None, None)._asdict()],
)
def test_read_copies_refuses_other_types(value):
    with pytest.raises(TypeError):
        read_copies(value)


@pytest.mark.parametrize("function", [read_build, read_process, read_timing_process])
@pytest.mark.parametrize("value", [None, 0, tuple(container(0)), removal(0)])
def test_container_readers_refuse_other_types(function, value):
    with pytest.raises(TypeError, match="ContainerResult"):
        function(value)


# build_dir_removable


def test_build_dir_removable_after_a_normal_end():
    assert build_dir_removable(container(0)) is True
    assert build_dir_removable(container(125)) is True


@pytest.mark.parametrize(
    ("gone", "removable"),
    [
        (removal(0), True),
        (removal(1), False),
        (removal(None, timed_out=True), False),
        (removal(True), False),
        (None, False),
    ],
)
def test_build_dir_removable_after_a_timeout(gone, removable):
    assert build_dir_removable(container(timed_out=True, gone=gone)) is removable


@pytest.mark.parametrize(
    ("error", "removable"),
    [
        (local_run.ProgramNotFoundError("x"), True),
        (standin_container.NoNumericUserError("x"), True),
        (KeyboardInterrupt(), True),
        (with_attributes(ValueError(), parameter="image"), True),
        (OSError(errno.EIO, "io"), False),
        (PermissionError(errno.EACCES, "denied"), False),
        (with_attributes(OSError(), container_name="n"), False),
        (with_attributes(OverflowError(), container_name="n", removal=None), False),
        (
            with_attributes(OverflowError(), container_name="n", removal=removal(0)),
            True,
        ),
        (
            with_attributes(
                KeyboardInterrupt(), container_name="n", removal=removal(2)
            ),
            False,
        ),
    ],
)
def test_build_dir_removable_after_an_exception(error, removable):
    assert build_dir_removable(error) is removable


@pytest.mark.parametrize("value", [None, "result", tuple(container(0)), removal(0)])
def test_build_dir_removable_refuses_other_types(value):
    with pytest.raises(TypeError, match="outcome"):
        build_dir_removable(value)


def test_steps_are_four_strings():
    assert STEPS == ("image", "copies", "build", "process")
    assert standin_answer.GO_ON is GO_ON
