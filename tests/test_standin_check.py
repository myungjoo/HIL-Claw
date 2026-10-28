import os
import shutil
import subprocess
import tempfile

import pytest

from hilclaw import (
    build_log,
    check_failure,
    check_operation,
    kernel_source,
    local_run,
    standin_check,
    standin_container,
    standin_copies,
    standin_image,
    standin_settings,
    tools,
)
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.harness import (
    bf16_sdpa_kv_cache_verification,
    bf16_verification,
    bf16_verification_build,
    verification_build,
)
from hilclaw.standin_check import operation

IMAGE = "registry.example/hilclaw-clang:1"
SEED = 987654321
PARAMETERS = CheckParameters(seed=SEED, draws=3, m=2, k=5, n=7)
REPORT = b"\x01\x02report\x00"
BUILD_STDOUT = b"compiled\n"
BUILD_STDERR = b"gemm.c:1: warning: unused\n"
PROCESS_STDERR = b"process said something"


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


def built(stdout=BUILD_STDOUT, stderr=BUILD_STDERR, *, executable=True):
    def act(command):
        if executable:
            path = os.path.join(mount_source(command), standin_check.EXECUTABLE_NAME)
            with open(path, "wb") as file:
                file.write(b"\x7fELF")
        return run_result(command, 0, stdout=stdout, stderr=stderr)

    return act


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


def reported(report=REPORT):
    return ended(0, stdout=report, stderr=PROCESS_STDERR)


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


def call(output, keeper, parameters=PARAMETERS):
    return operation(
        {"tool": "correctness.check"}, {"hw": 1}, parameters, output, keeper
    )


def build_dirs(temporary):
    return sorted(os.listdir(temporary))


def failure(output, keeper, kind):
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper)
    assert raised.value.kind == kind
    assert type(raised.value.message) is str
    for shown in (IMAGE, "hilclaw-standin", str(output), "tmp", "warning", "partial"):
        assert shown not in raised.value.message
    return raised.value


def test_constants():
    assert standin_check.REMOVAL_TIMEOUT_S == 60
    assert standin_check.COMPILER == "clang"
    assert standin_check.EXECUTABLE_NAME == "verification"
    assert standin_check.BUILD_DIR_PREFIX.startswith("hilclaw-")
    assert len(standin_check.REMOVE_PAUSES_S) >= 2
    assert all(pause >= 0 for pause in standin_check.REMOVE_PAUSES_S)


def test_happy_returns_the_report_and_keeps_the_log(client, output, keeper, temporary):
    client.script = [built(), reported()]
    assert call(output, keeper) == REPORT
    assert keeper.held() == (BUILD_STDOUT + BUILD_STDERR).decode()
    assert build_dirs(temporary) == []
    build, process = client.runs()
    assert client.removals() == []

    inside = standin_container.CONTAINER_BUILD_DIR
    program = build[build.index(IMAGE) + 1 :]
    flags = list(standin_settings.FLAGS)
    trailing = list(standin_settings.TRAILING_FLAGS)
    assert program[0] == "clang"
    assert program[1 : 1 + len(flags)] == flags
    sources = program[1 + len(flags) : len(program) - len(trailing) - 2]
    assert sources == [
        f"{inside}/{verification_build.PROGRAM_SOURCE.name}",
        f"{inside}/kernel/a_util.c",
        f"{inside}/kernel/gemm.c",
    ]
    assert program[-len(trailing) - 2 : -2] == trailing
    assert program[-2:] == ["-o", f"{inside}/verification"]
    assert str(SEED) not in " ".join(build)

    assert process[process.index(IMAGE) + 1 :] == [
        f"{inside}/verification",
        "2",
        "5",
        "7",
        "3",
        str(SEED),
    ]
    options = [options for _, options in client.calls]
    assert options[0]["timeout_s"] == standin_settings.BUILD_TIME_LIMIT_S
    assert options[1]["timeout_s"] == (
        standin_settings.verification_process_time_limit_s(2, 5, 7, 3)
    )
    assert mount_source(build) == mount_source(process)
    assert os.path.basename(mount_source(build)).startswith(
        standin_check.BUILD_DIR_PREFIX
    )


def test_the_operation_is_answered_by_ask(client, output, keeper, tmp_path):
    client.script = [built(), ended(1)]
    answer = check_operation.ask(
        operation,
        {},
        {},
        PARAMETERS,
        output,
        keeper,
        log_path=tmp_path / "log" / "build-log.txt",
        rtol=1e-3,
        atol=1e-3,
    )
    assert answer["outcome"] == "broken"
    assert (tmp_path / "log" / "build-log.txt").read_bytes() == (
        BUILD_STDOUT + BUILD_STDERR
    )


def test_the_log_is_both_streams_decoded_with_nothing_between(client, output, keeper):
    client.script = [built(stdout=b"a\xff", stderr=b"\xe2\x82b"), reported()]
    assert call(output, keeper) == REPORT
    assert keeper.held() == "a\ufffd\ufffdb"


def test_each_stream_is_decoded_on_its_own(client, output, keeper):
    client.script = [built(stdout=b"x\xe2\x82", stderr=b"\xacy"), reported()]
    assert call(output, keeper) == REPORT
    assert keeper.held() == "x\ufffd\ufffdy"
    assert keeper.held() != (b"x\xe2\x82\xacy").decode()


def test_an_empty_log_is_handed_over(client, output, keeper):
    client.script = [built(stdout=b"", stderr=b""), reported(b"")]
    assert call(output, keeper) == b""
    assert keeper.held() == ""


def test_c1_no_image_named(monkeypatch, client, output, keeper, temporary):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    failure(output, keeper, check_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []
    assert keeper.held() is None


def test_c2_image_refused(monkeypatch, client, output, keeper, temporary):
    monkeypatch.setenv(standin_image.ENV_IMAGE, "-refused")
    failure(output, keeper, check_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("index", "kind"),
    [
        (0, check_failure.KIND_COMPILER_UNAVAILABLE),
        (1, check_failure.KIND_EXECUTABLE_UNSTARTABLE),
    ],
)
def test_c3_no_client(client, output, keeper, temporary, index, kind):
    client.script = [built(), reported()]
    client.script[index] = raises(local_run.ProgramNotFoundError("docker"))
    failure(output, keeper, kind)
    assert build_dirs(temporary) == []
    assert (keeper.held() is not None) == (index == 1)


def test_c4_no_numeric_user(monkeypatch, client, output, keeper, temporary):
    monkeypatch.delattr(os, "getuid", raising=False)
    failure(output, keeper, check_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []
    assert keeper.held() is None


@pytest.mark.parametrize("status", [125, 126, 127])
def test_c5_runtime_status_of_a_build(client, output, keeper, temporary, status):
    client.script = [ended(status, stderr=b"docker: error")]
    failure(output, keeper, check_failure.KIND_COMPILER_UNAVAILABLE)
    assert keeper.held() is None
    assert len(client.runs()) == 1
    assert build_dirs(temporary) == []


@pytest.mark.parametrize("status", [1, 124, 128, 137, -9])
def test_c6_other_status_of_a_build(client, output, keeper, temporary, status):
    client.script = [ended(status, stdout=b"", stderr=b"gemm.c: error")]
    assert call(output, keeper) == "build_exit_status"
    assert keeper.held() == "gemm.c: error"
    assert len(client.runs()) == 1
    assert build_dirs(temporary) == []


def test_c7_status_0_and_no_executable(client, output, keeper, temporary):
    client.script = [built(executable=False)]
    failure(output, keeper, check_failure.KIND_BUILD_OUTPUT_MISSING)
    assert keeper.held() == (BUILD_STDOUT + BUILD_STDERR).decode()
    assert len(client.runs()) == 1
    assert build_dirs(temporary) == []


def test_c7_an_executable_that_is_no_regular_file(client, output, keeper):
    def directory(command):
        os.mkdir(os.path.join(mount_source(command), standin_check.EXECUTABLE_NAME))
        return run_result(command, 0)

    client.script = [directory]
    failure(output, keeper, check_failure.KIND_BUILD_OUTPUT_MISSING)
    assert keeper.held() == ""


@pytest.mark.parametrize("status", [1, 125, 126, 127, 139, -11])
def test_c8_process_status(client, output, keeper, temporary, status):
    client.script = [built(), ended(status, stdout=b"half")]
    assert call(output, keeper) == "exit_status"
    assert keeper.held() == (BUILD_STDOUT + BUILD_STDERR).decode()
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("removal", "removed"),
    [
        (None, True),
        (ended(1, stderr=b"no such container"), False),
        (timed_out(), False),
    ],
)
def test_c10_build_time_limit(client, output, keeper, temporary, removal, removed):
    client.script = [timed_out(), removal]
    assert call(output, keeper) == "build_time_limit"
    assert keeper.held() == "partial output"
    ((command, options),) = client.removals()
    assert command[:3] == ["docker", "rm", "--force"]
    assert options["timeout_s"] == standin_check.REMOVAL_TIMEOUT_S
    assert len(client.runs()) == 1
    assert (build_dirs(temporary) == []) == removed


def test_c10_build_time_limit_removal_raised(client, output, keeper, temporary):
    client.script = [timed_out(), raises(OSError("rm failed"))]
    assert call(output, keeper) == "build_time_limit"
    assert keeper.held() is None
    assert len(build_dirs(temporary)) == 1


@pytest.mark.parametrize(
    ("removal", "removed"),
    [
        (None, True),
        (ended(1), False),
        (timed_out(), False),
    ],
)
def test_c10_process_time_limit(client, output, keeper, temporary, removal, removed):
    client.script = [built(), timed_out(), removal]
    assert call(output, keeper) == "time_limit"
    assert keeper.held() == (BUILD_STDOUT + BUILD_STDERR).decode()
    ((_, options),) = client.removals()
    assert options["timeout_s"] == standin_check.REMOVAL_TIMEOUT_S
    assert (build_dirs(temporary) == []) == removed


def test_c10_process_time_limit_removal_raised(client, output, keeper, temporary):
    client.script = [built(), timed_out(), raises(OSError("rm failed"))]
    assert call(output, keeper) == "time_limit"
    assert len(build_dirs(temporary)) == 1


@pytest.mark.parametrize("index", [0, 1])
def test_c11_overflow_after_the_start(client, output, keeper, temporary, index):
    client.script = [built(), reported()]
    client.script[index] = raises(OverflowError("timeout too large"))
    client.script.insert(index + 1, None)
    failure(output, keeper, check_failure.KIND_SETTINGS_REFUSED)
    assert len(client.removals()) == 1
    assert build_dirs(temporary) == []
    assert (keeper.held() is not None) == (index == 1)


def test_c12_harness_program_missing(
    monkeypatch, client, output, keeper, tmp_path, temporary
):
    monkeypatch.setattr(verification_build, "PROGRAM_SOURCE", tmp_path / "gone.c")
    failure(output, keeper, check_failure.KIND_BUILD_INPUT_MISSING)
    assert client.calls == []
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    "error",
    [
        standin_copies.CopyError(standin_copies.ENTRY_EXISTS),
        standin_copies.CopyError(standin_copies.COPY_UNWRITABLE),
        NotADirectoryError("not a directory"),
    ],
)
def test_c13_copies_cannot_be_written(
    monkeypatch, client, output, keeper, temporary, error
):
    def place(*args):
        raise error

    monkeypatch.setattr(standin_copies, "place_copies", place)
    failure(output, keeper, check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c13_a_build_dir_the_mount_cannot_carry(
    monkeypatch, client, output, keeper, tmp_path
):
    odd = tmp_path / "odd,place"
    odd.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(odd))
    failure(output, keeper, check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []
    assert os.listdir(odd) == []


def test_c15_no_kernel_source(client, tmp_path, keeper, temporary):
    missing = tmp_path / "data" / "attempts" / "02" / "output"
    failure(missing, keeper, check_failure.KIND_NO_KERNEL_SOURCE)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c15_reader_fails(monkeypatch, client, output, keeper, temporary):
    def place(*args):
        raise kernel_source.KernelSourceReadError(
            kernel_source.OUTPUT_DIRECTORY_UNLISTABLE
        )

    monkeypatch.setattr(standin_copies, "place_copies", place)
    failure(output, keeper, check_failure.KIND_KERNEL_SOURCE_UNREADABLE)
    assert build_dirs(temporary) == []


def test_c17_removal_limit_refused(monkeypatch, client, output, keeper, temporary):
    monkeypatch.setattr(standin_check, "REMOVAL_TIMEOUT_S", 0)
    failure(output, keeper, check_failure.KIND_SETTINGS_REFUSED)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_c17_build_limit_refused(monkeypatch, client, output, keeper):
    monkeypatch.setattr(standin_settings, "BUILD_TIME_LIMIT_S", float("inf"))
    failure(output, keeper, check_failure.KIND_SETTINGS_REFUSED)
    assert client.calls == []


def test_s3_build_directory_cannot_be_made(monkeypatch, client, output, keeper):
    def refuse(**options):
        raise PermissionError("denied")

    monkeypatch.setattr(tempfile, "mkdtemp", refuse)
    failure(output, keeper, check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []


def test_s3_build_directory_inside_a_checkout(
    monkeypatch, client, output, keeper, tmp_path
):
    checkout = tmp_path / "checkout"
    (checkout / ".git").mkdir(parents=True)
    below = checkout / "deep" / "tmp"
    below.mkdir(parents=True)
    monkeypatch.setattr(tempfile, "tempdir", str(below))
    failure(output, keeper, check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []
    assert os.listdir(below) == []


def test_s3_build_directory_inside_the_package(monkeypatch, client, output, keeper):
    monkeypatch.setattr(tempfile, "tempdir", os.path.dirname(standin_check.__file__))
    made = []
    real = tempfile.mkdtemp

    def mkdtemp(**options):
        made.append(real(**options))
        return made[-1]

    monkeypatch.setattr(tempfile, "mkdtemp", mkdtemp)
    failure(output, keeper, check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert len(made) == 1
    assert not os.path.lexists(made[0])


def test_c14_plain_oserror_passes_and_leaves_the_directory(
    client, output, keeper, temporary
):
    error = OSError("could not read the client's output")
    client.script = [raises(error)]
    with pytest.raises(OSError) as raised:
        call(output, keeper)
    assert raised.value is error
    assert keeper.held() is None
    assert len(build_dirs(temporary)) == 1


def test_c14_plain_oserror_of_the_copies_passes(
    monkeypatch, client, output, keeper, temporary
):
    error = OSError("close failed")

    def place(*args):
        raise error

    monkeypatch.setattr(standin_copies, "place_copies", place)
    with pytest.raises(OSError) as raised:
        call(output, keeper)
    assert raised.value is error
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("parameters", "error"),
    [
        ((SEED, 3, 2, 5, 7), TypeError),
        (CheckParameters(seed=SEED, draws=0, m=2, k=5, n=7), ValueError),
        (CheckParameters(seed=SEED, draws=3, m=True, k=5, n=7), TypeError),
        (CheckParameters(seed=-1, draws=3, m=2, k=5, n=7), ValueError),
        (CheckParameters(seed=2**64, draws=3, m=2, k=5, n=7), ValueError),
        (CheckParameters(seed=1.0, draws=3, m=2, k=5, n=7), TypeError),
        (CheckParameters(seed=False, draws=3, m=2, k=5, n=7), TypeError),
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


def test_c16_image_read_type_error_passes(monkeypatch, client, output, keeper):
    def read_image():
        raise TypeError("not a mapping")

    monkeypatch.setattr(standin_image, "read_image", read_image)
    with pytest.raises(TypeError):
        call(output, keeper)
    assert client.calls == []


def test_a_status_that_is_no_int_is_not_placed(client, output, keeper, temporary):
    client.script = [lambda command: run_result(command, None)]
    with pytest.raises(RuntimeError):
        call(output, keeper)
    assert keeper.held() is None
    assert build_dirs(temporary) == []


def test_a_process_status_that_is_no_int_is_not_placed(client, output, keeper):
    client.script = [built(), lambda command: run_result(command, None)]
    with pytest.raises(RuntimeError):
        call(output, keeper)


@pytest.mark.parametrize("index", [0, 1])
def test_a_request_to_end_from_a_container_passes(
    client, output, keeper, temporary, index
):
    client.script = [built(), reported()]
    client.script[index] = raises(KeyboardInterrupt())
    client.script.insert(index + 1, None)
    with pytest.raises(KeyboardInterrupt):
        call(output, keeper)
    assert len(client.removals()) == 1
    assert build_dirs(temporary) == []


def test_a_request_to_end_with_a_failed_removal_leaves_the_directory(
    client, output, keeper, temporary
):
    client.script = [raises(KeyboardInterrupt()), ended(1)]
    with pytest.raises(KeyboardInterrupt):
        call(output, keeper)
    assert len(build_dirs(temporary)) == 1


def test_a_request_to_end_during_the_removal_passes(
    monkeypatch, client, output, keeper
):
    def interrupt(path, *args, **kwargs):
        raise KeyboardInterrupt

    client.script = [built(), reported()]
    monkeypatch.setattr(standin_check.shutil, "rmtree", interrupt)
    with pytest.raises(KeyboardInterrupt):
        call(output, keeper)


def test_a_failed_removal_changes_no_answer(
    monkeypatch, client, output, keeper, temporary
):
    calls = []

    def refuse(path, *args, **kwargs):
        calls.append(path)
        raise PermissionError("busy")

    client.script = [built(), reported()]
    monkeypatch.setattr(standin_check.shutil, "rmtree", refuse)
    assert call(output, keeper) == REPORT
    assert len(calls) == len(standin_check.REMOVE_PAUSES_S)
    assert len(build_dirs(temporary)) == 1


def test_a_failed_removal_changes_no_tool_failure(
    monkeypatch, client, output, keeper, temporary
):
    monkeypatch.setattr(standin_check.shutil, "rmtree", lambda *a, **k: None)
    client.script = [ended(126)]
    failure(output, keeper, check_failure.KIND_COMPILER_UNAVAILABLE)
    assert len(build_dirs(temporary)) == 1


def test_a_failed_removal_changes_no_condition(monkeypatch, client, output, keeper):
    monkeypatch.setattr(standin_check.shutil, "rmtree", lambda *a, **k: None)
    client.script = [ended(2)]
    assert call(output, keeper) == "build_exit_status"


def test_a_tool_failure_holds_no_chained_error(client, output, keeper):
    client.script = [raises(local_run.ProgramNotFoundError("docker"))]
    error = failure(output, keeper, check_failure.KIND_COMPILER_UNAVAILABLE)
    assert error.__cause__ is None
    assert error.__context__ is None


def test_a_second_call_makes_a_new_build_directory(client, output, temporary):
    client.script = [built(), reported(), built(), reported()]
    assert call(output, build_log.LogKeeper()) == REPORT
    assert call(output, build_log.LogKeeper()) == REPORT
    first, _, second, _ = client.runs()
    assert mount_source(first) != mount_source(second)
    assert build_dirs(temporary) == []


def test_in_container():
    assert standin_check.in_container("kernel/a.c") == (
        f"{standin_container.CONTAINER_BUILD_DIR}/kernel/a.c"
    )


def test_settled():
    assert standin_check.settled("exit_status") == "exit_status"
    failed = check_failure.KIND_BUILD_OUTPUT_MISSING
    answer = standin_check.standin_answer.Failure(failed, "no executable")
    with pytest.raises(standin_check.Answered) as raised:
        standin_check.settled(answer)
    assert raised.value.answer is answer
    with pytest.raises(RuntimeError):
        standin_check.settled(None)


def test_carry_out_raises_an_answer_as_a_tool_failure(temporary):
    directory = standin_check.make_build_dir("hilclaw-test-")
    answer = standin_check.standin_answer.Failure("some_kind", "said")

    def steps(outcomes):
        assert outcomes == []
        raise standin_check.Answered(answer)

    with pytest.raises(tools.ToolFailure) as raised:
        standin_check.carry_out(directory, steps)
    assert (raised.value.kind, raised.value.message) == ("some_kind", "said")
    assert not os.path.lexists(directory)


def test_carry_out_leaves_the_directory_after_a_plain_oserror(temporary):
    directory = standin_check.make_build_dir("hilclaw-test-")

    def steps(outcomes):
        outcomes.append(OSError("after the start"))
        return "time_limit"

    assert standin_check.carry_out(directory, steps) == "time_limit"
    assert os.path.isdir(directory)


def test_remove_build_dir(temporary):
    directory = standin_check.make_build_dir("hilclaw-test-")
    assert os.path.basename(directory).startswith("hilclaw-test-")
    assert standin_check.remove_build_dir(directory) is True
    assert standin_check.remove_build_dir(directory) is True


def test_run_build_without_a_keeper_hands_over_nothing(client, temporary):
    directory = standin_check.make_build_dir("hilclaw-test-")
    client.script = [built()]
    outcomes = []
    answer = standin_check.run_build(
        outcomes,
        IMAGE,
        directory,
        ("x.c",),
        5,
        keeper=None,
        executable=standin_check.EXECUTABLE_NAME,
        missing=None,
    )
    assert answer is standin_check.standin_answer.GO_ON
    assert len(outcomes) == 1


def test_container_image(monkeypatch):
    assert standin_check.container_image() == IMAGE
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    with pytest.raises(tools.ToolFailure):
        standin_check.container_image()


# A check of a bf16 kind (ADR-0177 decision 3; ADR-0179)

BF16_DIMS = {
    "gemm": (2, 5, 7),
    "rmsnorm": (3, 4),
    "elementwise_add": (3, 4),
    "swiglu": (3, 4),
    "sdpa_kv_cache": (2, 3, 4, 2, 4),
}


def bf16(kind="gemm", dims=None, *, seed=SEED, draws=3, dtype="bf16"):
    dims = BF16_DIMS[kind] if dims is None else dims
    return Bf16CheckParameters(seed, draws, kind, dtype, dims)


def bf16_arguments(kind, dims, draws=3, seed=SEED):
    if kind == "sdpa_kv_cache":
        return bf16_sdpa_kv_cache_verification.program_arguments(
            dims, draws=draws, seed=seed
        )
    return bf16_verification.program_arguments(kind, dims, draws=draws, seed=seed)


def built_beside_the_header(seen):
    make = built()

    def act(command):
        directory = mount_source(command)
        seen["entries"] = sorted(os.listdir(directory))
        with open(os.path.join(directory, "bf16_verification.h"), "rb") as file:
            seen["header"] = file.read()
        return make(command)

    return act


@pytest.mark.parametrize("kind", list(BF16_DIMS))
def test_bf16_happy_builds_the_program_of_the_kind_beside_the_header(
    client, output, keeper, temporary, kind
):
    seen = {}
    client.script = [built_beside_the_header(seen), reported()]
    assert call(output, keeper, bf16(kind)) == REPORT
    assert keeper.held() == (BUILD_STDOUT + BUILD_STDERR).decode()
    assert build_dirs(temporary) == []
    program = bf16_verification_build.PROGRAM_SOURCES[kind]
    assert seen["entries"] == sorted(["bf16_verification.h", program.name, "kernel"])
    assert seen["header"] == standin_check.BF16_HEADER.read_bytes()
    assert standin_check.BF16_HEADER.name == "bf16_verification.h"

    build, process = client.runs()
    inside = standin_container.CONTAINER_BUILD_DIR
    command = build[build.index(IMAGE) + 1 :]
    flags = list(standin_settings.FLAGS)
    trailing = list(standin_settings.TRAILING_FLAGS)
    assert command[: 1 + len(flags)] == ["clang", *flags]
    assert command[1 + len(flags) : -len(trailing) - 2] == [
        f"{inside}/{program.name}",
        f"{inside}/kernel/a_util.c",
        f"{inside}/kernel/gemm.c",
    ]
    assert command[-len(trailing) - 2 :] == [*trailing, "-o", f"{inside}/verification"]
    assert str(SEED) not in " ".join(build)
    assert process[process.index(IMAGE) + 1 :] == [
        f"{inside}/verification",
        *bf16_arguments(kind, BF16_DIMS[kind]),
    ]
    options = [options for _, options in client.calls]
    assert options[0]["timeout_s"] == standin_settings.BUILD_TIME_LIMIT_S
    assert options[1]["timeout_s"] == (
        standin_settings.bf16_verification_process_time_limit_s(
            kind, BF16_DIMS[kind], 3
        )
    )


@pytest.mark.parametrize(
    ("kind", "dims", "capped"),
    [
        ("gemm", (512, 2048, 128256), True),
        ("gemm", (512, 2048, 8192), False),
        ("sdpa_kv_cache", (2048, 2048, 32, 8, 64), True),
        ("swiglu", (512, 8192), False),
    ],
)
def test_bf16_the_largest_shapes_hand_the_capped_limit_or_not(
    client, output, keeper, kind, dims, capped
):
    client.script = [built(), reported()]
    assert call(output, keeper, bf16(kind, dims, draws=9)) == REPORT
    limit = client.calls[1][1]["timeout_s"]
    assert (limit == 1500.0) is capped
    assert limit == standin_settings.bf16_verification_process_time_limit_s(
        kind, dims, 9
    )


def test_bf16_the_process_past_its_limit_is_time_limit(
    client, output, keeper, temporary
):
    client.script = [built(), timed_out(), None]
    assert call(output, keeper, bf16("swiglu")) == "time_limit"
    assert build_dirs(temporary) == []


def test_bf16_the_build_past_its_limit_is_build_time_limit(
    client, output, keeper, temporary
):
    client.script = [timed_out(), None]
    assert call(output, keeper, bf16("sdpa_kv_cache")) == "build_time_limit"
    assert keeper.held() == "partial output"
    assert len(client.runs()) == 1


@pytest.mark.parametrize("status", [1, 2, 3, 139])
def test_bf16_a_process_status_is_exit_status(client, output, keeper, status):
    client.script = [built(), ended(status)]
    assert call(output, keeper, bf16("rmsnorm")) == "exit_status"


def test_bf16_the_header_missing_is_build_input_missing(
    monkeypatch, client, output, keeper, tmp_path, temporary
):
    monkeypatch.setattr(standin_check, "BF16_HEADER", tmp_path / "gone.h")
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper, bf16("elementwise_add"))
    assert raised.value.kind == check_failure.KIND_BUILD_INPUT_MISSING
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_bf16_the_program_missing_is_build_input_missing(
    monkeypatch, client, output, keeper, tmp_path, temporary
):
    sources = dict(bf16_verification_build.PROGRAM_SOURCES)
    sources["gemm"] = tmp_path / "gone.c"
    monkeypatch.setattr(bf16_verification_build, "PROGRAM_SOURCES", sources)
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper, bf16("gemm"))
    assert raised.value.kind == check_failure.KIND_BUILD_INPUT_MISSING
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_bf16_a_header_name_already_taken_is_build_directory_unusable(
    monkeypatch, client, output, keeper, tmp_path, temporary
):
    taken = tmp_path / "header" / verification_build.PROGRAM_SOURCE.name
    taken.parent.mkdir()
    taken.write_bytes(b"/* a header named like the program */\n")
    monkeypatch.setattr(standin_check, "BF16_HEADER", taken)
    sources = dict(bf16_verification_build.PROGRAM_SOURCES)
    sources["gemm"] = verification_build.PROGRAM_SOURCE
    monkeypatch.setattr(bf16_verification_build, "PROGRAM_SOURCES", sources)
    with pytest.raises(tools.ToolFailure) as raised:
        call(output, keeper, bf16("gemm"))
    assert raised.value.kind == check_failure.KIND_BUILD_DIRECTORY_UNUSABLE
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_bf16_no_kernel_source_copies_no_header(
    monkeypatch, client, tmp_path, keeper, temporary
):
    copied = []
    monkeypatch.setattr(
        standin_copies, "place_harness_copy", lambda *args: copied.append(args)
    )
    missing = tmp_path / "data" / "attempts" / "02" / "output"
    with pytest.raises(tools.ToolFailure) as raised:
        call(missing, keeper, bf16("swiglu"))
    assert raised.value.kind == check_failure.KIND_NO_KERNEL_SOURCE
    assert (copied, client.calls, build_dirs(temporary)) == ([], [], [])


def test_bf16_a_plain_oserror_of_the_header_copy_passes(
    monkeypatch, client, output, keeper, temporary
):
    error = OSError("plain")

    def place(*args):
        raise error

    monkeypatch.setattr(standin_copies, "place_harness_copy", place)
    with pytest.raises(OSError) as raised:
        call(output, keeper, bf16("gemm"))
    assert raised.value is error
    assert build_dirs(temporary) == []


@pytest.mark.parametrize(
    ("parameters", "error"),
    [
        (bf16(dtype="fp32"), ValueError),
        (bf16(dtype=None), ValueError),
        (bf16("rope", (1, 2, 4)), ValueError),
        (Bf16CheckParameters(SEED, 3, "softmax", "bf16", (1, 2)), ValueError),
        (bf16("gemm", [2, 5, 7]), TypeError),
        (bf16("gemm", (2, 5)), ValueError),
        (bf16("rmsnorm", (0, 4)), ValueError),
        (bf16("swiglu", (3, True)), TypeError),
        (bf16("sdpa_kv_cache", (3, 2, 4, 2, 4)), ValueError),
        (bf16("sdpa_kv_cache", (2, 3, 4, 3, 4)), ValueError),
        (bf16(draws=0), ValueError),
        (bf16(draws=2**64), ValueError),
        (bf16(seed=-1), ValueError),
        (bf16(seed=2**64), ValueError),
        (bf16(seed=1.0), ValueError),
        (bf16(seed=True), ValueError),
        (tuple(bf16()), TypeError),
    ],
)
def test_bf16_own_arguments_pass(client, output, keeper, temporary, parameters, error):
    with pytest.raises(error):
        call(output, keeper, parameters)
    assert client.calls == []
    assert build_dirs(temporary) == []


def test_bf16_keeper_that_is_no_log_keeper(client, output, temporary):
    with pytest.raises(TypeError):
        call(output, object(), bf16())
    assert (client.calls, build_dirs(temporary)) == ([], [])


@pytest.mark.parametrize("kind", list(BF16_DIMS))
def test_bf16_the_copied_program_compiles_with_the_fixed_set(tmp_path, kind):
    compiler = shutil.which("clang")
    if compiler is None or os.name == "nt":
        pytest.skip("clang on a POSIX system is needed")
    output = tmp_path / "output"
    output.mkdir()
    (output / "kernel.c").write_text("int hilclaw_kernel_placeholder;\n")
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    program = bf16_verification_build.PROGRAM_SOURCES[kind]
    copies = standin_copies.place_copies(output, program, build_dir)
    standin_copies.place_harness_copy(standin_check.BF16_HEADER, build_dir)
    result = subprocess.run(
        [
            compiler,
            *standin_settings.FLAGS,
            "-c",
            str(build_dir / copies.harness),
            "-o",
            str(build_dir / "program.o"),
        ],
        capture_output=True,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
