import os
import tempfile

import pytest

from hilclaw import (
    build_log,
    kernel_source,
    local_run,
    run_failure,
    run_operation,
    standin_check,
    standin_container,
    standin_copies,
    standin_image,
    standin_run,
    standin_settings,
    tools,
)
from hilclaw.harness import (
    bf16_rope_verification,
    bf16_timing,
    bf16_timing_build,
    timing,
    timing_build,
)
from hilclaw.run_parameters import Bf16TimingParameters, TimingParameters
from hilclaw.standin_run import operation

IMAGE = "registry.example/hilclaw-clang:1"
SEED = 987654321987
PARAMETERS = TimingParameters(
    m=2, k=5, n=7, n_max=40, sample_form="interval", seed=SEED
)
REPORT = b"resolution_ns 1\ninterval_ns 5\nstop converged\n"
BUILD_STDOUT = b"compiled\n"
BUILD_STDERR = b"gemm.c:1: warning: unused\n"
WAITER_STDERR = b"timing_waiter.c:1: warning: never kept\n"
INSIDE = standin_container.CONTAINER_BUILD_DIR
TOOLS = ("sim.run", "board.run")


def run_result(command, returncode=0, *, timed_out=False, stdout=b"", stderr=b""):
    return local_run.RunResult(
        returncode=None if timed_out else returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        command=tuple(command),
        duration_s=0.5,
        max_rss=None,
    )


def mount_source(command):
    option = command[command.index("--mount") + 1]
    fields = dict(field.split("=", 1) for field in option.split(","))
    return fields["source"]


def built(name, stdout=b"", stderr=b"", *, executable=True):
    def act(command):
        if executable:
            with open(os.path.join(mount_source(command), name), "wb") as file:
                file.write(b"\x7fELF")
        return run_result(command, 0, stdout=stdout, stderr=stderr)

    return act


def timing_built(stdout=BUILD_STDOUT, stderr=BUILD_STDERR, *, executable=True):
    return built(
        standin_run.TIMING_EXECUTABLE_NAME, stdout, stderr, executable=executable
    )


def waiter_built(stderr=WAITER_STDERR, *, executable=True):
    return built(standin_run.WAITER_EXECUTABLE_NAME, b"", stderr, executable=executable)


def ended(returncode, stdout=b"", stderr=b""):
    return lambda command: run_result(command, returncode, stdout=stdout, stderr=stderr)


def timed_out(stdout=b"partial", stderr=b" output"):
    return lambda command: run_result(
        command, timed_out=True, stdout=stdout, stderr=stderr
    )


def raises(error):
    def act(command):
        raise error

    return act


def waited(report=REPORT, line=b"waiter_max_rss_kib 300", status=0):
    return ended(status, stdout=report + b"\n" + line + b"\n", stderr=b"proc")


def happy():
    return [timing_built(), waiter_built(), waited()]


class Client:
    def __init__(self):
        self.calls = []
        self.script = []

    def __call__(self, command, **options):
        command = list(command)
        self.calls.append((command, options))
        if command[1] == "rm" and (not self.script or self.script[0] is None):
            if self.script:
                self.script.pop(0)
            return run_result(command, 0)
        return self.script.pop(0)(command)

    def runs(self):
        return [command for command, _ in self.calls if command[1] == "run"]

    def run_options(self):
        return [options for command, options in self.calls if command[1] == "run"]

    def removals(self):
        return [
            (command, options) for command, options in self.calls if command[1] == "rm"
        ]


@pytest.fixture(autouse=True)
def client(monkeypatch):
    stub = Client()
    monkeypatch.setattr(local_run, "run", stub)
    return stub


@pytest.fixture(autouse=True)
def user(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)


@pytest.fixture(autouse=True)
def image(monkeypatch):
    monkeypatch.setenv(standin_image.ENV_IMAGE, IMAGE)


@pytest.fixture(autouse=True)
def temporary(monkeypatch, tmp_path):
    directory = tmp_path / "tmp"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    monkeypatch.setattr(standin_check, "REMOVE_PAUSES_S", (0.0, 0.0))
    return directory


@pytest.fixture
def clock(monkeypatch):
    readings = []

    def monotonic():
        return readings.pop(0)

    monkeypatch.setattr(standin_run, "monotonic", monotonic)
    return readings


@pytest.fixture
def output(tmp_path):
    directory = tmp_path / "data" / "attempts" / "01" / "output"
    directory.mkdir(parents=True)
    (directory / "gemm.c").write_bytes(b"void gemm(void) {}\n")
    (directory / "a_util.c").write_bytes(b"int util;\n")
    (directory / "gemm.h").write_bytes(b"void gemm(void);\n")
    return directory


@pytest.fixture
def keeper():
    return build_log.LogKeeper()


def call(output, keeper, parameters=PARAMETERS, tool="sim.run"):
    return operation({"tool": tool}, {"hw": 1}, parameters, output, keeper)


def build_dirs(temporary):
    return sorted(os.listdir(temporary))


def program(command):
    return command[command.index(IMAGE) + 1 :]


def timing_log():
    return (BUILD_STDOUT + BUILD_STDERR).decode()


def failure(output, keeper, kind):
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper)
    assert raised.value.kind == kind
    assert type(raised.value.message) is str
    for shown in (
        IMAGE,
        "hilclaw-standin",
        str(output),
        "tmp",
        "warning",
        "partial",
        INSIDE,
    ):
        assert shown not in raised.value.message
    assert raised.value.__cause__ is None
    return raised.value


def test_constants():
    assert standin_run.TIMING_EXECUTABLE_NAME == "timing"
    assert standin_run.WAITER_EXECUTABLE_NAME == "waiter"
    assert standin_run.BUILD_DIR_PREFIX.startswith("hilclaw-")
    assert standin_run.BUILD_DIR_PREFIX != standin_check.BUILD_DIR_PREFIX
    assert standin_run.WAITER_SOURCE.name == "timing_waiter.c"
    assert standin_run.WAITER_SOURCE.is_file()
    assert standin_run.WAITER_SOURCE.parent == timing_build.DRIVER_SOURCE.parent


@pytest.mark.parametrize("tool", TOOLS)
def test_happy_returns_the_report_and_the_figure(
    client, output, keeper, temporary, tool
):
    client.script = happy()
    answer = call(output, keeper, tool=tool)
    assert answer == (REPORT, 300 * 1024)
    assert type(answer) is tuple
    assert keeper.held() == timing_log()
    assert build_dirs(temporary) == []
    assert client.removals() == []

    timing_build_command, waiter_build, process = client.runs()
    flags = list(standin_settings.FLAGS)
    trailing = list(standin_settings.TRAILING_FLAGS)
    compiled = program(timing_build_command)
    assert compiled[0] == "clang"
    assert compiled[1 : 1 + len(flags)] == flags
    sources = compiled[1 + len(flags) : len(compiled) - len(trailing) - 2]
    assert sources == [
        f"{INSIDE}/{timing_build.DRIVER_SOURCE.name}",
        f"{INSIDE}/kernel/a_util.c",
        f"{INSIDE}/kernel/gemm.c",
    ]
    assert compiled[-len(trailing) - 2 : -2] == trailing
    assert compiled[-2:] == ["-o", f"{INSIDE}/timing"]

    assert program(waiter_build) == [
        "clang",
        *standin_settings.WAITER_FLAGS,
        f"{INSIDE}/timing_waiter.c",
        "-o",
        f"{INSIDE}/waiter",
    ]
    assert "-fopenmp" in flags
    assert "-fopenmp" not in program(waiter_build)

    driver = timing.driver_arguments(
        m=2, k=5, n=7, n_max=40, sample_form="interval", seed=SEED
    )
    assert program(process) == [f"{INSIDE}/waiter", f"{INSIDE}/timing", *driver]
    assert len(driver) == 8
    for command in (timing_build_command, waiter_build):
        assert str(SEED) not in " ".join(command)

    options = client.run_options()
    assert options[0]["timeout_s"] == standin_settings.BUILD_TIME_LIMIT_S
    assert 0 < options[1]["timeout_s"] <= standin_settings.BUILD_TIME_LIMIT_S
    assert options[2]["timeout_s"] == standin_settings.timing_process_time_limit_s(
        2, 5, 7, 40
    )
    sources = {mount_source(command) for command in client.runs()}
    assert len(sources) == 1
    assert os.path.basename(sources.pop()).startswith(standin_run.BUILD_DIR_PREFIX)


def test_the_copies_lie_beside_the_kernel_directory(client, output, keeper):
    seen = []

    def look(command):
        seen.append(sorted(os.listdir(mount_source(command))))
        return timing_built()(command)

    client.script = [look, waiter_built(), waited()]
    call(output, keeper)
    assert seen == [["kernel", "timing_driver.c", "timing_waiter.c"]]


@pytest.mark.parametrize("tool", TOOLS)
def test_the_operation_is_answered_by_ask(client, output, keeper, tmp_path, tool):
    client.script = happy()
    log_path = tmp_path / "log" / "build-log.txt"
    answer = run_operation.ask(
        operation, {}, {}, PARAMETERS, output, keeper, log_path=log_path
    )
    assert answer == run_operation.Reported(REPORT, 300 * 1024)
    assert type(answer) is run_operation.Reported
    assert log_path.read_bytes() == BUILD_STDOUT + BUILD_STDERR


def test_a_condition_is_answered_by_ask(client, output, keeper, tmp_path):
    client.script = [timing_built(), ended(1, stderr=WAITER_STDERR)]
    log_path = tmp_path / "build-log.txt"
    answer = run_operation.ask(
        operation, {}, {}, PARAMETERS, output, keeper, log_path=log_path
    )
    assert answer == "build_exit_status"
    assert log_path.read_bytes() == BUILD_STDOUT + BUILD_STDERR


def test_the_open_stream_is_answered_invalid_by_ask(client, output, keeper, tmp_path):
    client.script = [timing_built(), waiter_built(), ended(0, stdout=REPORT)]
    with pytest.raises(run_operation.OperationAnswerInvalid):
        run_operation.ask(
            operation,
            {},
            {},
            PARAMETERS,
            output,
            keeper,
            log_path=tmp_path / "build-log.txt",
        )
    assert (tmp_path / "build-log.txt").read_bytes() == BUILD_STDOUT + BUILD_STDERR


def test_the_none_line_gives_no_figure(client, output, keeper):
    client.script = [
        timing_built(),
        waiter_built(),
        waited(line=b"waiter_max_rss none"),
    ]
    assert call(output, keeper) == (REPORT, None)


def test_the_timing_log_is_both_streams_decoded(client, output, keeper):
    client.script = [
        timing_built(stdout=b"a\xff", stderr=b"\xe2\x82b"),
        waiter_built(),
        waited(),
    ]
    call(output, keeper)
    assert keeper.held() == "a��b"


def test_the_timing_log_is_handed_over_before_the_waiters_build(client, output, keeper):
    held = []

    def look(command):
        held.append(keeper.held())
        return waiter_built()(command)

    client.script = [timing_built(), look, waited()]
    call(output, keeper)
    assert held == [timing_log()]


def test_c1_no_image_named(monkeypatch, client, output, keeper, temporary):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    failure(output, keeper, run_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []
    assert keeper.held() is None


def test_c2_image_refused(monkeypatch, client, output, keeper, temporary):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "-refused")
    failure(output, keeper, run_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("index", "kind", "log"),
    [
        (0, run_failure.KIND_COMPILER_UNAVAILABLE, False),
        (1, run_failure.KIND_COMPILER_UNAVAILABLE, True),
        (2, run_failure.KIND_EXECUTABLE_UNSTARTABLE, True),
    ],
)
def test_c3_no_client(client, output, keeper, temporary, index, kind, log):
    client.script = happy()
    client.script[index] = raises(local_run.ProgramNotFoundError("docker"))
    failure(output, keeper, kind)
    assert build_dirs(temporary) == []
    assert (keeper.held() is not None) == log


def test_c4_no_numeric_user(monkeypatch, client, output, keeper, temporary):
    monkeypatch.delattr(os, "getuid", raising=False)
    failure(output, keeper, run_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []
    assert keeper.held() is None


@pytest.mark.parametrize("status", [125, 126, 127])
def test_c5_runtime_status_of_the_timing_build(
    client, output, keeper, temporary, status
):
    client.script = [ended(status, stderr=b"docker: error")]
    failure(output, keeper, run_failure.KIND_COMPILER_UNAVAILABLE)
    assert keeper.held() is None
    assert len(client.runs()) == 1
    assert build_dirs(temporary) == []


@pytest.mark.parametrize("status", [125, 126, 127])
def test_c19_runtime_status_of_the_waiters_build(
    client, output, keeper, temporary, status
):
    client.script = [timing_built(), ended(status, stderr=b"docker: error")]
    failure(output, keeper, run_failure.KIND_COMPILER_UNAVAILABLE)
    assert keeper.held() == timing_log()
    assert len(client.runs()) == 2
    assert build_dirs(temporary) == []


@pytest.mark.parametrize("status", [1, 124, 128, 137, -9])
def test_c6_other_status_of_the_timing_build(client, output, keeper, temporary, status):
    client.script = [ended(status, stderr=b"gemm.c: error")]
    assert call(output, keeper) == "build_exit_status"
    assert keeper.held() == "gemm.c: error"
    assert len(client.runs()) == 1
    assert build_dirs(temporary) == []


@pytest.mark.parametrize("status", [1, 128, -9])
def test_c19_the_waiters_build_fails(client, output, keeper, temporary, status):
    client.script = [timing_built(), ended(status, stderr=WAITER_STDERR)]
    assert call(output, keeper) == "build_exit_status"
    assert keeper.held() == timing_log()
    assert len(client.runs()) == 2
    assert build_dirs(temporary) == []


def test_c7_timing_build_status_0_and_no_executable(client, output, keeper, temporary):
    client.script = [timing_built(executable=False)]
    error = failure(output, keeper, run_failure.KIND_BUILD_OUTPUT_MISSING)
    assert "timing build" in error.message
    assert keeper.held() == timing_log()
    assert len(client.runs()) == 1
    assert build_dirs(temporary) == []


def test_c19_waiters_build_status_0_and_no_executable(
    client, output, keeper, temporary
):
    client.script = [timing_built(), waiter_built(executable=False)]
    error = failure(output, keeper, run_failure.KIND_BUILD_OUTPUT_MISSING)
    assert "waiter" in error.message
    assert keeper.held() == timing_log()
    assert len(client.runs()) == 2
    assert build_dirs(temporary) == []


def test_c19_a_waiter_that_is_no_regular_file(client, output, keeper):
    def directory(command):
        os.mkdir(os.path.join(mount_source(command), "waiter"))
        return run_result(command, 0)

    client.script = [timing_built(), directory]
    failure(output, keeper, run_failure.KIND_BUILD_OUTPUT_MISSING)


@pytest.mark.parametrize("status", [1, 125, 126, 127, 137, -11])
def test_c8_c9_a_line_with_a_non_zero_status(client, output, keeper, status):
    client.script = [timing_built(), waiter_built(), waited(status=status)]
    assert call(output, keeper) == "exit_status"
    assert keeper.held() == timing_log()


@pytest.mark.parametrize("status", [1, 3, 125, 127, 137])
def test_c8_c9_no_line_with_a_non_zero_status(client, output, keeper, status):
    client.script = [timing_built(), waiter_built(), ended(status, stdout=REPORT)]
    assert call(output, keeper) == "exit_status"


@pytest.mark.parametrize("stdout", [REPORT, b"", b"\nwaiter_max_rss_kib 300"])
def test_c9_no_line_with_status_0_is_not_placed(
    client, output, keeper, temporary, stdout
):
    client.script = [timing_built(), waiter_built(), ended(0, stdout=stdout)]
    with pytest.raises(RuntimeError):
        call(output, keeper)
    assert keeper.held() == timing_log()
    assert build_dirs(temporary) == []


def test_a_process_status_that_is_no_int_is_not_placed(client, output, keeper):
    client.script = [
        timing_built(),
        waiter_built(),
        lambda command: run_result(
            command, None, stdout=REPORT + b"\nwaiter_max_rss none\n"
        ),
    ]
    with pytest.raises(RuntimeError):
        call(output, keeper)


def test_a_build_status_that_is_no_int_is_not_placed(client, output, keeper):
    client.script = [lambda command: run_result(command, None)]
    with pytest.raises(RuntimeError):
        call(output, keeper)
    assert keeper.held() is None


REMOVALS = [
    (None, True),
    (ended(1, stderr=b"no such container"), False),
    (timed_out(), False),
]


@pytest.mark.parametrize(("removal", "removed"), REMOVALS)
def test_c10_timing_build_time_limit(
    client, output, keeper, temporary, removal, removed
):
    client.script = [timed_out(), removal]
    assert call(output, keeper) == "build_time_limit"
    assert keeper.held() == "partial output"
    ((command, options),) = client.removals()
    assert command[:3] == ["docker", "rm", "--force"]
    assert options["timeout_s"] == standin_check.REMOVAL_TIMEOUT_S
    assert len(client.runs()) == 1
    assert (build_dirs(temporary) == []) == removed


@pytest.mark.parametrize(("removal", "removed"), REMOVALS)
def test_c19_waiters_build_time_limit(
    client, output, keeper, temporary, removal, removed
):
    client.script = [timing_built(), timed_out(), removal]
    assert call(output, keeper) == "build_time_limit"
    assert keeper.held() == timing_log()
    ((_, options),) = client.removals()
    assert options["timeout_s"] == standin_check.REMOVAL_TIMEOUT_S
    assert len(client.runs()) == 2
    assert (build_dirs(temporary) == []) == removed


@pytest.mark.parametrize(("removal", "removed"), REMOVALS)
def test_c10_timing_process_time_limit(
    client, output, keeper, temporary, removal, removed
):
    client.script = [timing_built(), waiter_built(), timed_out(), removal]
    assert call(output, keeper) == "time_limit"
    assert keeper.held() == timing_log()
    ((_, options),) = client.removals()
    assert options["timeout_s"] == standin_check.REMOVAL_TIMEOUT_S
    assert (build_dirs(temporary) == []) == removed


@pytest.mark.parametrize(
    ("script", "answer", "log"),
    [
        ([], "build_time_limit", None),
        ([timing_built()], "build_time_limit", timing_log()),
        ([timing_built(), waiter_built()], "time_limit", timing_log()),
    ],
)
def test_c10_removal_raised(client, output, keeper, temporary, script, answer, log):
    client.script = [*script, timed_out(), raises(OSError("rm failed"))]
    assert call(output, keeper) == answer
    assert keeper.held() == log
    assert len(build_dirs(temporary)) == 1


@pytest.mark.parametrize("index", [0, 1, 2])
def test_c11_overflow_after_the_start(client, output, keeper, temporary, index):
    client.script = happy()
    client.script[index] = raises(OverflowError("timeout too large"))
    client.script.insert(index + 1, None)
    failure(output, keeper, run_failure.KIND_SETTINGS_REFUSED)
    assert len(client.removals()) == 1
    assert build_dirs(temporary) == []
    assert (keeper.held() is not None) == (index > 0)


@pytest.mark.parametrize("which", ["driver", "waiter"])
def test_c12_a_harness_program_missing(
    monkeypatch, client, output, keeper, tmp_path, temporary, which
):
    if which == "driver":
        monkeypatch.setattr(timing_build, "DRIVER_SOURCE", tmp_path / "gone.c")
    else:
        monkeypatch.setattr(standin_run, "WAITER_SOURCE", tmp_path / "gone.c")
    failure(output, keeper, run_failure.KIND_BUILD_INPUT_MISSING)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c12_a_waiter_source_that_is_no_regular_file(
    monkeypatch, client, output, keeper, tmp_path
):
    monkeypatch.setattr(standin_run, "WAITER_SOURCE", tmp_path)
    failure(output, keeper, run_failure.KIND_BUILD_INPUT_MISSING)
    assert client.calls == []


@pytest.mark.parametrize(
    "error",
    [
        standin_copies.CopyError(standin_copies.ENTRY_EXISTS),
        standin_copies.CopyError(standin_copies.COPY_UNWRITABLE),
        NotADirectoryError("not a directory"),
    ],
)
@pytest.mark.parametrize("step", ["place_copies", "place_harness_copy"])
def test_c13_copies_cannot_be_written(
    monkeypatch, client, output, keeper, temporary, error, step
):
    def place(*args):
        raise error

    monkeypatch.setattr(standin_copies, step, place)
    failure(output, keeper, run_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c13_a_waiter_named_like_the_driver(
    monkeypatch, client, output, keeper, tmp_path
):
    other = tmp_path / "elsewhere"
    other.mkdir()
    twin = other / timing_build.DRIVER_SOURCE.name
    twin.write_bytes(b"int main(void) { return 0; }\n")
    monkeypatch.setattr(standin_run, "WAITER_SOURCE", twin)
    failure(output, keeper, run_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []


def test_c13_a_build_dir_the_mount_cannot_carry(
    monkeypatch, client, output, keeper, tmp_path
):
    odd = tmp_path / "odd,place"
    odd.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(odd))
    failure(output, keeper, run_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []
    assert os.listdir(odd) == []


def test_c15_no_kernel_source(client, tmp_path, keeper, temporary):
    missing = tmp_path / "data" / "attempts" / "02" / "output"
    failure(missing, keeper, run_failure.KIND_NO_KERNEL_SOURCE)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c15_no_kernel_source_copies_no_waiter(monkeypatch, client, tmp_path, keeper):
    copied = []
    monkeypatch.setattr(
        standin_copies, "place_harness_copy", lambda *args: copied.append(args)
    )
    missing = tmp_path / "data" / "attempts" / "02" / "output"
    failure(missing, keeper, run_failure.KIND_NO_KERNEL_SOURCE)
    assert copied == []


def test_c15_reader_fails(monkeypatch, client, output, keeper, temporary):
    def place(*args):
        raise kernel_source.KernelSourceReadError(
            kernel_source.OUTPUT_DIRECTORY_UNLISTABLE
        )

    monkeypatch.setattr(standin_copies, "place_copies", place)
    failure(output, keeper, run_failure.KIND_KERNEL_SOURCE_UNREADABLE)
    assert build_dirs(temporary) == []


def test_c17_removal_limit_refused(monkeypatch, client, output, keeper, temporary):
    monkeypatch.setattr(standin_check, "REMOVAL_TIMEOUT_S", 0)
    failure(output, keeper, run_failure.KIND_SETTINGS_REFUSED)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c17_build_limit_refused(monkeypatch, client, output, keeper):
    monkeypatch.setattr(standin_settings, "BUILD_TIME_LIMIT_S", float("inf"))
    failure(output, keeper, run_failure.KIND_SETTINGS_REFUSED)
    assert client.calls == []


def test_the_waiters_limit_is_what_the_timing_build_left(client, clock, output, keeper):
    clock.extend([100.0, 142.5])
    client.script = happy()
    call(output, keeper)
    options = client.run_options()
    assert options[0]["timeout_s"] == standin_settings.BUILD_TIME_LIMIT_S
    assert options[1]["timeout_s"] == pytest.approx(
        standin_settings.BUILD_TIME_LIMIT_S - 42.5
    )


@pytest.mark.parametrize("elapsed", [60.0, 75.0])
def test_c19_the_build_limit_used_up_before_the_waiters_build(
    client, clock, output, keeper, temporary, elapsed
):
    clock.extend([10.0, 10.0 + elapsed])
    client.script = [timing_built()]
    assert call(output, keeper) == "build_time_limit"
    assert len(client.runs()) == 1
    assert keeper.held() == timing_log()
    assert build_dirs(temporary) == []


def test_s3_build_directory_cannot_be_made(monkeypatch, client, output, keeper):
    def refuse(**options):
        raise PermissionError("denied")

    monkeypatch.setattr(tempfile, "mkdtemp", refuse)
    failure(output, keeper, run_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []


def test_s3_build_directory_inside_a_checkout(
    monkeypatch, client, output, keeper, tmp_path
):
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    below = checkout / "tmp"
    below.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(below))
    failure(output, keeper, run_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert os.listdir(below) == []


@pytest.mark.parametrize("index", [0, 1, 2])
def test_c14_plain_oserror_passes_and_leaves_the_directory(
    client, output, keeper, temporary, index
):
    error = OSError("could not read the client's output")
    client.script = happy()
    client.script[index] = raises(error)
    with pytest.raises(OSError) as raised:
        call(output, keeper)
    assert raised.value is error
    assert (keeper.held() is not None) == (index > 0)
    assert len(build_dirs(temporary)) == 1


@pytest.mark.parametrize("step", ["place_copies", "place_harness_copy"])
def test_c14_plain_oserror_of_the_copies_passes(
    monkeypatch, client, output, keeper, temporary, step
):
    error = OSError("close failed")

    def place(*args):
        raise error

    monkeypatch.setattr(standin_copies, step, place)
    with pytest.raises(OSError) as raised:
        call(output, keeper)
    assert raised.value is error
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("parameters", "error"),
    [
        ((2, 5, 7, 40, "interval", SEED), TypeError),
        (PARAMETERS._replace(m=0), timing.TimingArgumentError),
        (PARAMETERS._replace(k=True), timing.TimingArgumentError),
        (PARAMETERS._replace(n_max=1), timing.TimingArgumentError),
        (PARAMETERS._replace(sample_form="median"), timing.TimingArgumentError),
        (PARAMETERS._replace(seed=-1), timing.TimingArgumentError),
        (PARAMETERS._replace(seed=2**64), timing.TimingArgumentError),
        (PARAMETERS._replace(seed=1.0), timing.TimingArgumentError),
    ],
)
def test_c16_own_arguments_pass(client, output, keeper, temporary, parameters, error):
    with pytest.raises(error):
        call(output, keeper, parameters)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c16_keeper_that_is_no_log_keeper(client, output, temporary):
    with pytest.raises(TypeError):
        call(output, object())
    assert build_dirs(temporary) == []


def test_c16_output_path_refused_by_the_reader(client, keeper, temporary):
    with pytest.raises(kernel_source.InvalidOutputPathError):
        call(b"bytes/output", keeper)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c16_a_harness_parameter_error_passes(monkeypatch, client, output, keeper):
    monkeypatch.setattr(standin_run, "WAITER_SOURCE", 42)
    with pytest.raises(TypeError) as raised:
        call(output, keeper)
    assert raised.value.parameter == "harness_program"
    assert client.calls == []


@pytest.mark.parametrize("index", [0, 1, 2])
def test_a_request_to_end_from_a_container_passes(
    client, output, keeper, temporary, index
):
    client.script = happy()
    client.script[index] = raises(KeyboardInterrupt())
    client.script.insert(index + 1, None)
    with pytest.raises(KeyboardInterrupt):
        call(output, keeper)
    assert len(client.removals()) == 1
    assert build_dirs(temporary) == []


def test_a_request_to_end_with_a_failed_removal_leaves_the_directory(
    client, output, keeper, temporary
):
    client.script = [timing_built(), raises(KeyboardInterrupt()), ended(1)]
    with pytest.raises(KeyboardInterrupt):
        call(output, keeper)
    assert len(build_dirs(temporary)) == 1


def test_a_request_to_end_during_the_removal_passes(
    monkeypatch, client, output, keeper
):
    def interrupt(path, *args, **kwargs):
        raise KeyboardInterrupt

    client.script = happy()
    monkeypatch.setattr(standin_check.shutil, "rmtree", interrupt)
    with pytest.raises(KeyboardInterrupt):
        call(output, keeper)


def test_a_failed_removal_changes_no_answer(
    monkeypatch, client, output, keeper, temporary
):
    monkeypatch.setattr(standin_check.shutil, "rmtree", lambda *a, **k: None)
    client.script = happy()
    assert call(output, keeper) == (REPORT, 300 * 1024)
    assert len(build_dirs(temporary)) == 1


def test_a_failed_removal_changes_no_tool_failure(
    monkeypatch, client, output, keeper, temporary
):
    monkeypatch.setattr(standin_check.shutil, "rmtree", lambda *a, **k: None)
    client.script = [timing_built(), ended(126)]
    failure(output, keeper, run_failure.KIND_COMPILER_UNAVAILABLE)
    assert len(build_dirs(temporary)) == 1


def test_a_second_call_makes_a_new_build_directory(client, output, temporary):
    client.script = happy() + happy()
    assert call(output, build_log.LogKeeper()) == (REPORT, 300 * 1024)
    assert call(output, build_log.LogKeeper(), tool="board.run") == (
        REPORT,
        300 * 1024,
    )
    first, _, _, second, _, _ = client.runs()
    assert mount_source(first) != mount_source(second)
    assert build_dirs(temporary) == []


# A bf16 run (ADR-0181 decisions 2, 3, 5 and 6)

BF16_DIMS = {
    "gemm": (2, 3, 4),
    "rmsnorm": (2, 3),
    "elementwise_add": (2, 3),
    "swiglu": (2, 3),
    "rope": (2, 3, 4),
    "sdpa_kv_cache": (2, 5, 12, 3, 8),
}
BF16_KINDS = tuple(BF16_DIMS)


def bf16(
    kind="rmsnorm", dims=None, *, dtype="bf16", n_max=40, form="interval", seed=SEED
):
    dims = BF16_DIMS[kind] if dims is None else dims
    return Bf16TimingParameters(kind, dtype, dims, n_max, form, seed)


def test_the_headers_are_those_the_programs_include():
    assert [path.name for path in standin_run.BF16_HEADERS] == [
        "bf16_timing.h",
        "bf16_verification.h",
    ]
    for path in standin_run.BF16_HEADERS:
        assert path.is_file()
    programs = bf16_timing_build.PROGRAM_SOURCES.values()
    assert {path.parent for path in programs} == {standin_run.BF16_HEADERS[0].parent}


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("kind", BF16_KINDS)
def test_a_bf16_call_builds_twice_and_runs_under_the_waiter(
    client, output, keeper, temporary, kind, tool
):
    seen = []

    def look(command):
        seen.append(sorted(os.listdir(mount_source(command))))
        return timing_built()(command)

    client.script = [look, waiter_built(), waited()]
    parameters = bf16(kind)
    answer = call(output, keeper, parameters, tool)
    assert answer == (REPORT, 300 * 1024)
    assert type(answer) is tuple
    assert keeper.held() == timing_log()
    assert build_dirs(temporary) == []

    source = bf16_timing_build.PROGRAM_SOURCES[kind].name
    assert seen == [
        sorted(
            [
                source,
                "bf16_timing.h",
                "bf16_verification.h",
                "kernel",
                "timing_waiter.c",
            ]
        )
    ]
    timing_build_command, waiter_build, process = client.runs()
    flags = list(standin_settings.FLAGS)
    trailing = list(standin_settings.TRAILING_FLAGS)
    assert program(timing_build_command) == [
        "clang",
        *flags,
        f"{INSIDE}/{source}",
        f"{INSIDE}/kernel/a_util.c",
        f"{INSIDE}/kernel/gemm.c",
        *trailing,
        "-o",
        f"{INSIDE}/timing",
    ]
    assert program(waiter_build) == [
        "clang",
        *standin_settings.WAITER_FLAGS,
        f"{INSIDE}/timing_waiter.c",
        "-o",
        f"{INSIDE}/waiter",
    ]
    assert "-fopenmp" in flags
    assert "-fopenmp" not in program(waiter_build)
    arguments = bf16_timing.program_arguments(
        kind, BF16_DIMS[kind], n_max=40, sample_form="interval", seed=SEED
    )
    assert program(process) == [f"{INSIDE}/waiter", f"{INSIDE}/timing", *arguments]
    assert str(SEED) in arguments
    for command in (timing_build_command, waiter_build):
        assert str(SEED) not in " ".join(command)

    options = client.run_options()
    assert options[0]["timeout_s"] == standin_settings.BUILD_TIME_LIMIT_S
    assert 0 < options[1]["timeout_s"] <= standin_settings.BUILD_TIME_LIMIT_S
    assert options[2]["timeout_s"] == (
        standin_settings.bf16_timing_process_time_limit_s(kind, BF16_DIMS[kind], 40)
    )


@pytest.mark.parametrize(
    ("dims", "seed", "start"),
    [
        ((2, 3, 4), SEED, 0),
        ((3, 2, 6), 11, 0),
        ((1, 2, 4), 10, 127),
        ((1, 2, 4), 11, 2047),
    ],
)
def test_rope_hands_the_rows_of_its_start_position_to_the_process_alone(
    client, output, keeper, dims, seed, start
):
    client.script = happy()
    assert call(output, keeper, bf16("rope", dims, seed=seed)) == (REPORT, 300 * 1024)
    assert bf16_rope_verification.start_position(dims, seed=seed) == start
    first, second, process = client.run_options()
    assert "stdin_data" not in first
    assert "stdin_data" not in second
    assert process["stdin_data"] == bf16_timing.rope_rows(dims, seed)
    assert len(process["stdin_data"]) == 4 * dims[0] * dims[2]
    builds, ran = client.runs()[:2], client.runs()[2]
    assert all("--interactive" not in command for command in builds)
    assert "--interactive" in ran


@pytest.mark.parametrize(
    "parameters",
    [PARAMETERS, *(bf16(kind) for kind in BF16_KINDS if kind != "rope")],
)
def test_no_other_run_hands_a_container_any_input(client, output, keeper, parameters):
    client.script = happy()
    call(output, keeper, parameters)
    assert all("stdin_data" not in options for options in client.run_options())
    assert all("--interactive" not in command for command in client.runs())


@pytest.mark.parametrize(
    ("parameters", "error"),
    [
        (bf16(dtype="fp32"), ValueError),
        (bf16(dtype=None), ValueError),
        (bf16("conv", (2, 3)), timing.TimingArgumentError),
        (bf16(1, (2, 3)), timing.TimingArgumentError),
        (bf16("gemm", (2, 3)), timing.TimingArgumentError),
        (bf16("sdpa_kv_cache", (2, 5, 12, 3)), timing.TimingArgumentError),
        (bf16("rmsnorm", [2, 3]), timing.TimingArgumentError),
        (bf16("rmsnorm", (0, 3)), timing.TimingArgumentError),
        (bf16("rmsnorm", (True, 3)), timing.TimingArgumentError),
        (bf16("rope", (2, 3, 5)), timing.TimingArgumentError),
        (bf16("rope", (1, 1, 2**52), seed=1), timing.TimingArgumentError),
        (bf16("sdpa_kv_cache", (5, 2, 12, 3, 8)), timing.TimingArgumentError),
        (bf16("sdpa_kv_cache", (2, 5, 12, 5, 8)), timing.TimingArgumentError),
        (bf16(n_max=1), timing.TimingArgumentError),
        (bf16(n_max=True), timing.TimingArgumentError),
        (bf16(form="median"), timing.TimingArgumentError),
        (bf16(seed=-1), timing.TimingArgumentError),
        (bf16(seed=2**64), timing.TimingArgumentError),
        (tuple(bf16()), TypeError),
        (None, TypeError),
    ],
)
def test_c16_a_bf16_call_refused_starts_nothing(
    monkeypatch, client, output, keeper, temporary, parameters, error
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    with pytest.raises(error):
        call(output, keeper, parameters)
    assert client.calls == []
    assert build_dirs(temporary) == []
    assert keeper.held() is None


def test_c16_a_keeper_that_is_no_log_keeper_at_a_bf16_call(client, output, temporary):
    with pytest.raises(TypeError):
        call(output, object(), bf16())
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_the_limit_refuses_what_the_arguments_do_not(
    monkeypatch, client, output, keeper, temporary
):
    def limit(*args):
        raise ValueError("refused")

    monkeypatch.setattr(standin_settings, "bf16_timing_process_time_limit_s", limit)
    with pytest.raises(ValueError, match="refused"):
        call(output, keeper, bf16())
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_rope_rows_are_built_before_anything_is_started(
    monkeypatch, client, output, keeper, temporary
):
    def rows(*args):
        raise MemoryError

    monkeypatch.setattr(bf16_timing, "rope_rows", rows)
    with pytest.raises(MemoryError):
        call(output, keeper, bf16("rope"))
    assert client.calls == []
    assert build_dirs(temporary) == []


@pytest.mark.parametrize("kind", ["rmsnorm", "rope"])
@pytest.mark.parametrize(
    ("script", "answer", "log"),
    [
        ([timed_out(), None], "build_time_limit", "partial output"),
        ([ended(1, stderr=b"gemm.c: error")], "build_exit_status", "gemm.c: error"),
        ([timing_built(), ended(1, stderr=WAITER_STDERR)], "build_exit_status", None),
        ([timing_built(), timed_out(), None], "build_time_limit", None),
        ([timing_built(), waiter_built(), timed_out(), None], "time_limit", None),
        ([timing_built(), waiter_built(), waited(status=3)], "exit_status", None),
        ([timing_built(), waiter_built(), ended(5)], "exit_status", None),
    ],
)
def test_a_failure_answer_at_a_bf16_call(
    client, output, keeper, temporary, kind, script, answer, log
):
    client.script = list(script)
    assert call(output, keeper, bf16(kind)) == answer
    assert keeper.held() == (timing_log() if log is None else log)
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("script", "kind", "log"),
    [
        (
            [timing_built(executable=False)],
            run_failure.KIND_BUILD_OUTPUT_MISSING,
            True,
        ),
        (
            [timing_built(), waiter_built(executable=False)],
            run_failure.KIND_BUILD_OUTPUT_MISSING,
            True,
        ),
        ([ended(126)], run_failure.KIND_COMPILER_UNAVAILABLE, False),
    ],
)
def test_a_tool_failure_at_a_bf16_call(
    client, output, keeper, temporary, script, kind, log
):
    client.script = list(script)
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper, bf16())
    assert raised.value.kind == kind
    assert (keeper.held() == timing_log()) == log
    assert build_dirs(temporary) == []


@pytest.mark.parametrize("index", [0, 1])
def test_c12_a_bf16_header_missing(
    monkeypatch, client, output, keeper, tmp_path, temporary, index
):
    headers = list(standin_run.BF16_HEADERS)
    headers[index] = tmp_path / "gone.h"
    monkeypatch.setattr(standin_run, "BF16_HEADERS", tuple(headers))
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper, bf16())
    assert raised.value.kind == run_failure.KIND_BUILD_INPUT_MISSING
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c15_no_kernel_source_at_a_bf16_call_copies_no_header(
    monkeypatch, client, tmp_path, keeper, temporary
):
    copied = []
    monkeypatch.setattr(
        standin_copies, "place_harness_copy", lambda *args: copied.append(args)
    )
    missing = tmp_path / "data" / "attempts" / "02" / "output"
    with pytest.raises(tools.ToolFailure) as raised:
        call(missing, keeper, bf16())
    assert raised.value.kind == run_failure.KIND_NO_KERNEL_SOURCE
    assert copied == []
    assert build_dirs(temporary) == []


def test_a_bf16_call_is_answered_by_ask(client, output, keeper, tmp_path):
    client.script = happy()
    log_path = tmp_path / "build-log.txt"
    answer = run_operation.ask(
        operation, {}, {}, bf16("rope"), output, keeper, log_path=log_path
    )
    assert answer == run_operation.Reported(REPORT, 300 * 1024)
    assert log_path.read_bytes() == BUILD_STDOUT + BUILD_STDERR
