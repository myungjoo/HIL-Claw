import dataclasses
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from hilclaw import (
    backends,
    build_log,
    check_definition,
    check_failure,
    check_operation,
    cuda_adapter,
    cuda_check,
    cuda_image,
    cuda_run,
    local_run,
    standin_answer,
    standin_check,
    standin_container,
    standin_copies,
    standin_settings,
    targets,
    tools,
    vendor_adapter,
)
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.harness import cuda_programs
from hilclaw.keys import SCHEMA_VERSION

FIXTURES = Path(__file__).resolve().parent / "cuda_fixtures"
TOOL = "correctness.check"
IMAGE = "registry.example/cuda:1"
REAL_IMAGE = "cuda:13.1.2"
PARAMETERS = CheckParameters(seed=987654321, draws=2, m=5, k=33, n=7)
TOLERANCE = {"rtol": 1e-4, "atol": 1e-4}
REPORT = b"a report of the stub program\n"
BUILD_STDOUT = b"compiled\n"
BUILD_STDERR = b"kernel.cu(1): warning: unused\n"
DEVICE_LINE = b"Stub GPU, 1.0\n"
INSIDE = standin_container.CONTAINER_BUILD_DIR
ISOLATION = [
    "--network",
    "none",
    "--pull",
    "never",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges=true",
    "--entrypoint=",
]
LIMIT = 300


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


def inner(command):
    return command[command.index(IMAGE) + 1 :]


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


def probed(stdout=DEVICE_LINE):
    return ended(0, stdout=stdout)


def built(name=cuda_check.EXECUTABLE_NAME, *, executable=True, seen=None):
    def act(command):
        directory = mount_source(command)
        if seen is not None:
            for root, _, files in os.walk(directory):
                for file in files:
                    path = os.path.join(root, file)
                    with open(path, "rb") as opened:
                        seen[os.path.relpath(path, directory)] = opened.read()
        if executable:
            with open(os.path.join(directory, name), "wb") as file:
                file.write(b"\x7fELF")
        return run_result(command, 0, stdout=BUILD_STDOUT, stderr=BUILD_STDERR)

    return act


def reported(report=REPORT):
    return ended(0, stdout=report, stderr=b"process said something")


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

    def options(self):
        return [options for command, options in self.calls if command[1] == "run"]


@pytest.fixture(autouse=True)
def client(request, monkeypatch, tmp_path):
    if "gpu" in request.fixturenames:
        return None
    stub = Client()
    monkeypatch.setattr(local_run, "run", stub)
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)
    monkeypatch.setenv(cuda_image.ENV_IMAGE, IMAGE)
    return stub


@pytest.fixture
def build_root(tmp_path, monkeypatch):
    root = tmp_path / "temporary"
    root.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(root))
    monkeypatch.setattr(standin_check, "REMOVE_PAUSES_S", (0.0, 0.0))
    return root


@pytest.fixture
def kernel(tmp_path):
    path = tmp_path / "output" / "kernel.cu"
    path.parent.mkdir()
    path.write_text("// a kernel\n", encoding="utf-8")
    return path


def the_target(**changes):
    return dataclasses.replace(targets.target(targets.CUDA_GPU), **changes)


def operation(kernel, target=None, **kwargs):
    selection = kwargs.pop("sources", lambda output_path: (kernel,))
    return cuda_check.operation_for(
        the_target() if target is None else target, sources=selection
    )


def call(op, parameters=PARAMETERS, keeper=None, output_path="output-path"):
    keeper = build_log.LogKeeper() if keeper is None else keeper
    return op("request", "hw_profile", parameters, output_path, keeper)


def failure_of(op, kind, **kwargs):
    with pytest.raises(tools.ToolFailure) as raised:
        call(op, **kwargs)
    assert raised.value.kind == kind
    assert type(raised.value.message) is str and raised.value.message
    for shown in (IMAGE, "hilclaw-cuda", "warning", "partial", "Stub GPU"):
        assert shown not in raised.value.message
    return raised.value


def assert_gpu_containers(client):
    for command in client.runs():
        assert command[command.index(IMAGE) - 3 : command.index(IMAGE) - 1] == [
            "--gpus",
            "all",
        ]
        for option in ISOLATION:
            assert option in command
        assert command[command.index("--workdir") + 1] == INSIDE
        assert command[command.index("--user") + 1] == "1234:567"
        assert "--privileged" not in command and "--env" not in command
        assert command.count("--mount") == 1


# The module


def test_the_public_names_of_the_module():
    public = {name for name in vars(cuda_check) if not name.startswith("_")}
    imported = {
        "os",
        "stat",
        "build_log",
        "check_failure",
        "check_parameters",
        "cuda_adapter",
        "cuda_image",
        "standin_answer",
        "standin_check",
        "standin_copies",
        "standin_settings",
        "targets",
        "tools",
        "vendor_adapter",
        "cuda_programs",
    }
    assert public - imported == {
        "DEVICE_QUERY_TIMEOUT_S",
        "EXECUTABLE_NAME",
        "BUILD_DIR_PREFIX",
        "operation_for",
        "check_target",
        "check_sources",
        "check_keeper",
        "container_image",
        "confirm_device",
        "select_sources",
        "place_sources",
        "build_in_container",
        "run_process",
    }


def test_the_module_reads_no_attempt_file_name_and_runs_nothing_on_the_host():
    assert not {"kernel_source", "attempt_kernel"} & set(vars(cuda_check))
    assert not {"clang_build", "local_run"} & set(vars(cuda_check))
    assert "HQ-0104" in cuda_check.__doc__
    assert "in containers" in cuda_check.__doc__
    assert "test-only" not in cuda_check.__doc__


def test_the_default_table_has_no_cuda_gpu_entry():
    table = check_definition.default_table()
    assert targets.CUDA_GPU not in table.names()
    record = {
        "schema_version": SCHEMA_VERSION,
        "accelerator": targets.CUDA_GPU,
        "revision": "Example GPU sm_89",
        "toolchain": {"nvcc": "x", "gcc": "y", "nvidia_driver": "1"},
        "host": {"cpu": "c", "os": "o"},
        "hw_source": "external",
    }
    for tool in backends.HW_TOOLS:
        with pytest.raises(tools.ToolFailure) as raised:
            backends.select(table, record, tool)
        assert raised.value.kind == tools.KIND_NO_BACKEND


# operation_for and its argument checks


def test_operation_for_refuses_a_target_that_is_no_target(kernel):
    with pytest.raises(TypeError, match="target must be a Target"):
        cuda_check.operation_for("cuda_gpu", sources=lambda path: (kernel,))


@pytest.mark.parametrize("sources", [None, (), "kernel.cu"])
def test_operation_for_refuses_a_selection_that_is_not_callable(sources):
    with pytest.raises(TypeError, match="sources must be a callable"):
        cuda_check.operation_for(the_target(), sources=sources)


def test_operation_for_needs_the_selection_by_name():
    with pytest.raises(TypeError):
        cuda_check.operation_for(the_target())
    with pytest.raises(TypeError):
        cuda_check.operation_for(the_target(), lambda path: ())


def test_check_target_check_sources_and_check_keeper_pass_good_values():
    assert cuda_check.check_target(the_target()) is None
    assert cuda_check.check_sources(len) is None
    assert cuda_check.check_keeper(build_log.LogKeeper()) is None
    with pytest.raises(TypeError, match="keeper must be a LogKeeper"):
        cuda_check.check_keeper(object())


@pytest.mark.parametrize(
    ("parameters", "keeper", "error"),
    [
        (Bf16CheckParameters(1, 1, "gemm", "bf16", {}), None, TypeError),
        (tuple(PARAMETERS), None, TypeError),
        (PARAMETERS, object(), TypeError),
        (PARAMETERS._replace(seed=True), None, TypeError),
        (PARAMETERS._replace(seed="1"), None, TypeError),
        (PARAMETERS._replace(seed=-1), None, ValueError),
        (PARAMETERS._replace(seed=2**64), None, ValueError),
        (PARAMETERS._replace(m=0), None, ValueError),
        (PARAMETERS._replace(draws=1.5), None, TypeError),
    ],
)
def test_refused_arguments_start_nothing(
    client, build_root, kernel, parameters, keeper, error
):
    selected = []
    op = cuda_check.operation_for(
        the_target(), sources=lambda path: selected.append(path) or (kernel,)
    )
    with pytest.raises(error):
        op(
            "r",
            "h",
            parameters,
            "out",
            build_log.LogKeeper() if keeper is None else keeper,
        )
    assert client.calls == [] and selected == []
    assert list(build_root.iterdir()) == []


# The image (C1, C2)


def test_container_image_returns_the_named_image():
    assert cuda_check.container_image() == IMAGE


@pytest.mark.parametrize("value", [None, "", "-refused", "two words"])
def test_no_image_or_a_refused_one_is_compiler_unavailable_before_anything(
    monkeypatch, client, build_root, kernel, value
):
    if value is None:
        monkeypatch.delenv(cuda_image.ENV_IMAGE)
    else:
        monkeypatch.setenv(cuda_image.ENV_IMAGE, value)
    keeper = build_log.LogKeeper()
    failure_of(
        operation(kernel), check_failure.KIND_COMPILER_UNAVAILABLE, keeper=keeper
    )
    assert client.calls == [] and keeper.held() is None
    assert list(build_root.iterdir()) == []


def test_the_standin_image_variable_is_not_read(
    monkeypatch, client, build_root, kernel
):
    monkeypatch.delenv(cuda_image.ENV_IMAGE)
    monkeypatch.setenv("HILCLAW_STANDIN_IMAGE", IMAGE)
    failure_of(operation(kernel), check_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []


def test_container_image_lets_pass_what_it_does_not_place(monkeypatch):
    def read_image():
        raise LookupError("not placed")

    monkeypatch.setattr(cuda_image, "read_image", read_image)
    with pytest.raises(LookupError):
        cuda_check.container_image()


# The whole call with the stub client


def test_a_built_program_is_run_in_three_gpu_containers(client, build_root, kernel):
    client.script = [probed(), built(), reported()]
    keeper = build_log.LogKeeper()
    assert call(operation(kernel), keeper=keeper) == REPORT
    assert keeper.held() == (BUILD_STDOUT + BUILD_STDERR).decode()
    probe, build, process = client.runs()
    assert_gpu_containers(client)
    assert inner(probe) == [
        "nvidia-smi",
        *cuda_adapter.assemble_device_probe(timeout_s=1).command[1:],
    ]
    target = the_target()
    assert inner(build) == [
        "nvcc",
        *target.flags,
        f"{INSIDE}/{cuda_programs.VERIFICATION_PROGRAM_SOURCE.name}",
        f"{INSIDE}/kernel/kernel.cu",
        *target.trailing_flags,
        "-o",
        f"{INSIDE}/verification",
    ]
    assert inner(process) == [
        f"{INSIDE}/verification",
        "5",
        "33",
        "7",
        "2",
        "987654321",
    ]
    assert "--memory" not in process
    assert [options["timeout_s"] for options in client.options()] == [
        cuda_check.DEVICE_QUERY_TIMEOUT_S,
        target.build_time_limit_s,
        standin_settings.verification_process_time_limit_s(
            5, 33, 7, 2, target.process_time_limit_cap_s
        ),
    ]
    assert len({mount_source(command) for command in client.runs()}) == 1
    assert os.path.basename(mount_source(build)).startswith(cuda_check.BUILD_DIR_PREFIX)
    assert list(build_root.iterdir()) == []


def test_the_selected_files_are_copied_in_the_selection_s_order(
    client, build_root, tmp_path
):
    first = tmp_path / "b_first.cu"
    second = tmp_path / "a_second.cu"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    seen = {}
    client.script = [probed(), built(seen=seen), reported()]
    op = cuda_check.operation_for(
        the_target(), sources=lambda path: [str(first), second]
    )
    assert call(op) == REPORT
    build = client.runs()[1]
    assert inner(build)[-5:-2] == [
        f"{INSIDE}/{cuda_programs.VERIFICATION_PROGRAM_SOURCE.name}",
        f"{INSIDE}/kernel/b_first.cu",
        f"{INSIDE}/kernel/a_second.cu",
    ]
    assert seen == {
        os.path.join("kernel", "b_first.cu"): b"first",
        os.path.join("kernel", "a_second.cu"): b"second",
        cuda_programs.VERIFICATION_PROGRAM_SOURCE.name: (
            cuda_programs.VERIFICATION_PROGRAM_SOURCE.read_bytes()
        ),
    }


def test_the_selection_is_asked_with_the_output_path_after_the_probe(
    client, build_root, kernel
):
    asked = []

    def selection(path):
        asked.append((path, len(client.runs())))
        return (kernel,)

    client.script = [probed(), built(), reported()]
    call(cuda_check.operation_for(the_target(), sources=selection), output_path="o/p")
    assert asked == [("o/p", 1)]


def test_the_operation_is_answered_by_ask(client, build_root, kernel, tmp_path):
    client.script = [probed(), built(), ended(1)]
    answer = check_operation.ask(
        operation(kernel),
        {},
        {},
        PARAMETERS,
        "out",
        build_log.LogKeeper(),
        log_path=tmp_path / "log" / "build-log.txt",
        **TOLERANCE,
    )
    assert (answer["outcome"], answer["condition"]) == ("broken", "exit_status")
    assert (tmp_path / "log" / "build-log.txt").read_bytes() == (
        BUILD_STDOUT + BUILD_STDERR
    )


def test_a_memory_limit_of_the_target_bounds_only_the_process(
    client, build_root, kernel
):
    client.script = [probed(), built(), reported()]
    call(operation(kernel, the_target(memory_limit_bytes=2**30)))
    probe, build, process = client.runs()
    assert "--memory" not in probe and "--memory" not in build
    assert process[process.index("--memory") + 1] == str(2**30)


# The device check (ADR-0207 decision 6)


@pytest.mark.parametrize(
    "answer",
    [
        ended(6, stderr=b"No devices were found\n"),
        ended(9),
        ended(12),
        ended(125, stderr=b"could not select device driver"),
        ended(126),
        ended(127),
        ended(4),
        probed(b"no line it reads\n"),
        timed_out(),
        raises(local_run.ProgramNotFoundError("docker")),
    ],
    ids=[
        "no-device",
        "no-driver",
        "no-nvml",
        "no-gpu-for-the-container",
        "not-invokable",
        "not-in-image",
        "other-status",
        "unreadable",
        "time-limit",
        "no-client",
    ],
)
def test_no_usable_device_is_device_unavailable_before_any_build_or_process(
    client, build_root, kernel, answer
):
    client.script = [answer]
    selected = []
    op = cuda_check.operation_for(
        the_target(), sources=lambda path: selected.append(path) or (kernel,)
    )
    keeper = build_log.LogKeeper()
    failure_of(op, check_failure.KIND_DEVICE_UNAVAILABLE, keeper=keeper)
    (probe,) = client.runs()
    assert inner(probe)[0] == cuda_adapter.DEVICE_PROGRAM
    assert_gpu_containers(client)
    assert selected == [] and keeper.held() is None
    assert list(build_root.iterdir()) == []


def test_no_numeric_user_is_device_unavailable_with_nothing_started(
    monkeypatch, client, build_root, kernel
):
    monkeypatch.delattr(os, "getuid", raising=False)
    failure_of(operation(kernel), check_failure.KIND_DEVICE_UNAVAILABLE)
    assert client.calls == []
    assert list(build_root.iterdir()) == []


def test_a_probe_that_may_still_run_leaves_the_build_directory(
    client, build_root, kernel
):
    client.script = [timed_out(), ended(1)]
    failure_of(operation(kernel), check_failure.KIND_DEVICE_UNAVAILABLE)
    assert len(client.runs()) == 1
    assert len(list(build_root.iterdir())) == 1


def test_confirm_device_goes_on_and_records_the_probe(client, tmp_path):
    client.script = [probed()]
    outcomes = []
    assert cuda_check.confirm_device(IMAGE, str(tmp_path), outcomes) is None
    (outcome,) = outcomes
    assert type(outcome) is standin_container.ContainerResult
    assert client.options()[0]["timeout_s"] == cuda_check.DEVICE_QUERY_TIMEOUT_S


def test_confirm_device_raises_the_failure_of_the_probe(client, tmp_path):
    client.script = [ended(6)]
    outcomes = []
    with pytest.raises(standin_check.Answered) as raised:
        cuda_check.confirm_device(IMAGE, str(tmp_path), outcomes)
    assert raised.value.answer.kind == check_failure.KIND_DEVICE_UNAVAILABLE
    assert raised.value.answer.message == cuda_adapter.NO_DEVICE
    assert len(outcomes) == 1


def test_confirm_device_gives_the_forced_removal_its_limit(client, tmp_path):
    client.script = [timed_out(), None]
    with pytest.raises(standin_check.Answered):
        cuda_check.confirm_device(IMAGE, str(tmp_path), [])
    removal = [options for command, options in client.calls if command[1] == "rm"]
    assert removal[0]["timeout_s"] == standin_check.REMOVAL_TIMEOUT_S


def test_confirm_device_lets_pass_what_the_probe_lets_pass(client, tmp_path):
    client.script = [raises(KeyboardInterrupt())]
    outcomes = []
    with pytest.raises(KeyboardInterrupt):
        cuda_check.confirm_device(IMAGE, str(tmp_path), outcomes)
    assert isinstance(outcomes[0], KeyboardInterrupt)


# The selection


def test_select_sources_returns_the_selected_paths_as_a_tuple(kernel):
    assert cuda_check.select_sources(lambda path: [kernel], "o") == (kernel,)
    assert cuda_check.select_sources(lambda path: (str(kernel),), "o") == (str(kernel),)


@pytest.mark.parametrize(
    ("selection", "kind"),
    [
        (lambda path: (), check_failure.KIND_NO_KERNEL_SOURCE),
        (lambda path: [], check_failure.KIND_NO_KERNEL_SOURCE),
        (lambda path: 1 / 0, check_failure.KIND_KERNEL_SOURCE_UNREADABLE),
    ],
)
def test_select_sources_answers_a_selection_that_fails(selection, kind):
    with pytest.raises(tools.ToolFailure) as raised:
        cuda_check.select_sources(selection, "o")
    assert raised.value.kind == kind


def test_select_sources_answers_a_path_that_is_no_regular_file(tmp_path):
    for path in (tmp_path / "absent.cu", tmp_path, "bad\0path"):
        with pytest.raises(tools.ToolFailure) as raised:
            cuda_check.select_sources(lambda output, path=path: (path,), "o")
        assert raised.value.kind == check_failure.KIND_BUILD_INPUT_MISSING


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="no symbolic links")
def test_select_sources_answers_a_link_as_no_regular_file(tmp_path, kernel):
    link = tmp_path / "link.cu"
    try:
        link.symlink_to(kernel)
    except OSError:
        pytest.skip("symbolic links cannot be made here")
    with pytest.raises(tools.ToolFailure) as raised:
        cuda_check.select_sources(lambda path: (link,), "o")
    assert raised.value.kind == check_failure.KIND_BUILD_INPUT_MISSING


@pytest.mark.parametrize(
    "selection",
    [lambda path: "kernel.cu", lambda path: None, lambda path: (b"kernel.cu",)],
)
def test_select_sources_refuses_a_value_of_another_type(selection):
    with pytest.raises(TypeError):
        cuda_check.select_sources(selection, "o")


def test_select_sources_lets_a_request_to_end_pass():
    def selection(path):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        cuda_check.select_sources(selection, "o")


@pytest.mark.parametrize(
    ("selection", "kind"),
    [
        (lambda path: (), check_failure.KIND_NO_KERNEL_SOURCE),
        (lambda path: 1 / 0, check_failure.KIND_KERNEL_SOURCE_UNREADABLE),
        (lambda path: ("/no/such/kernel.cu",), check_failure.KIND_BUILD_INPUT_MISSING),
    ],
)
def test_a_failed_selection_starts_no_build_and_removes_the_directory(
    client, build_root, selection, kind
):
    client.script = [probed()]
    failure_of(cuda_check.operation_for(the_target(), sources=selection), kind)
    assert len(client.runs()) == 1
    assert list(build_root.iterdir()) == []


# The copies


def test_place_sources_copies_the_program_the_files_and_further_harnesses(
    tmp_path, kernel
):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    further = tmp_path / "waiter.c"
    further.write_bytes(b"waiter")
    copies = cuda_check.place_sources(
        lambda path: (kernel,),
        "o",
        cuda_programs.TIMING_DRIVER_SOURCE,
        str(build_dir),
        (further,),
    )
    assert copies == standin_copies.Copies(
        ("kernel/kernel.cu",), (), cuda_programs.TIMING_DRIVER_SOURCE.name, None
    )
    assert (build_dir / "waiter.c").read_bytes() == b"waiter"
    assert (build_dir / "kernel" / "kernel.cu").read_bytes() == kernel.read_bytes()


def test_place_sources_answers_a_failed_copy(tmp_path, kernel):
    build_dir = tmp_path / "build"
    build_dir.mkdir()
    with pytest.raises(standin_check.Answered) as raised:
        cuda_check.place_sources(
            lambda path: (kernel,), "o", tmp_path / "absent.c", str(build_dir)
        )
    assert raised.value.answer.kind == check_failure.KIND_BUILD_INPUT_MISSING


def test_two_files_of_one_name_are_build_directory_unusable(
    client, build_root, tmp_path
):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "k.cu").write_bytes(b"1")
    (tmp_path / "b" / "k.cu").write_bytes(b"2")
    client.script = [probed()]
    op = cuda_check.operation_for(
        the_target(),
        sources=lambda path: (tmp_path / "a" / "k.cu", tmp_path / "b" / "k.cu"),
    )
    failure_of(op, check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert len(client.runs()) == 1
    assert list(build_root.iterdir()) == []


def test_a_copy_error_no_row_places_passes(monkeypatch, client, build_root, kernel):
    def place(*args):
        raise PermissionError("not placed")

    monkeypatch.setattr(standin_copies, "place_selected_copies", place)
    client.script = [probed()]
    with pytest.raises(PermissionError):
        call(operation(kernel))
    assert list(build_root.iterdir()) == []


# The build


@pytest.mark.parametrize("status", [125, 126, 127])
def test_a_runtime_status_of_the_build_is_compiler_unavailable(
    client, build_root, kernel, status
):
    client.script = [probed(), ended(status, stderr=b"docker: error")]
    keeper = build_log.LogKeeper()
    failure_of(
        operation(kernel), check_failure.KIND_COMPILER_UNAVAILABLE, keeper=keeper
    )
    assert keeper.held() is None and len(client.runs()) == 2
    assert list(build_root.iterdir()) == []


@pytest.mark.parametrize(
    ("answer", "condition"),
    [
        (ended(1, stderr=b"kernel.cu: error"), "build_exit_status"),
        (ended(-9, stderr=b"kernel.cu: error"), "build_exit_status"),
        (timed_out(stderr=b"kernel.cu: error"), "build_time_limit"),
    ],
)
def test_a_build_that_fails_is_its_condition_with_the_log_kept(
    client, build_root, kernel, answer, condition
):
    client.script = [probed(), answer]
    keeper = build_log.LogKeeper()
    assert call(operation(kernel), keeper=keeper) == condition
    assert "kernel.cu: error" in keeper.held()
    assert len(client.runs()) == 2
    assert list(build_root.iterdir()) == []


def test_a_build_with_status_0_and_no_executable_is_build_output_missing(
    client, build_root, kernel
):
    client.script = [probed(), built(executable=False)]
    keeper = build_log.LogKeeper()
    failure_of(
        operation(kernel), check_failure.KIND_BUILD_OUTPUT_MISSING, keeper=keeper
    )
    assert keeper.held() is not None and len(client.runs()) == 2
    assert list(build_root.iterdir()) == []


def test_no_client_at_the_build_is_compiler_unavailable(client, build_root, kernel):
    client.script = [probed(), raises(local_run.ProgramNotFoundError("docker"))]
    failure_of(operation(kernel), check_failure.KIND_COMPILER_UNAVAILABLE)
    assert list(build_root.iterdir()) == []


def test_build_in_container_runs_nvcc_with_the_gpus(client, tmp_path):
    client.script = [built("exe")]
    outcomes = []
    keeper = build_log.LogKeeper()
    answer = cuda_check.build_in_container(
        outcomes,
        IMAGE,
        str(tmp_path),
        ("-O2", "x.cu", "-o", f"{INSIDE}/exe"),
        7,
        keeper=keeper,
        executable="exe",
        missing=standin_answer.Failure("k", "m"),
    )
    assert answer is standin_answer.GO_ON and len(outcomes) == 1
    assert inner(client.runs()[0]) == ["nvcc", "-O2", "x.cu", "-o", f"{INSIDE}/exe"]
    assert_gpu_containers(client)
    assert client.options()[0]["timeout_s"] == 7
    assert keeper.held() is not None


def test_build_in_container_raises_the_missing_failure(client, tmp_path):
    client.script = [built("exe", executable=False)]
    missing = standin_answer.Failure("k", "m")
    with pytest.raises(standin_check.Answered) as raised:
        cuda_check.build_in_container(
            [],
            IMAGE,
            str(tmp_path),
            ("x.cu",),
            7,
            keeper=None,
            executable="exe",
            missing=missing,
        )
    assert raised.value.answer is missing


# The process


@pytest.mark.parametrize("status", [1, 3, 125, 126, 127, -9])
def test_a_process_that_fails_is_broken_and_never_a_tool_failure(
    client, build_root, kernel, status
):
    client.script = [probed(), built(), ended(status, stdout=b"part")]
    assert call(operation(kernel)) == "exit_status"
    assert list(build_root.iterdir()) == []


def test_a_process_past_its_limit_is_time_limit(client, build_root, kernel):
    client.script = [probed(), built(), timed_out()]
    assert call(operation(kernel)) == "time_limit"
    assert list(build_root.iterdir()) == []


def test_a_process_whose_forced_removal_fails_leaves_the_directory(
    client, build_root, kernel
):
    client.script = [probed(), built(), timed_out(), ended(1)]
    assert call(operation(kernel)) == "time_limit"
    assert len(list(build_root.iterdir())) == 1


def test_an_incomplete_report_with_status_0_is_returned_for_the_judging(
    client, build_root, kernel, tmp_path
):
    client.script = [probed(), built(), reported(b"seed 1\n")]
    answer = check_operation.ask(
        operation(kernel),
        {},
        {},
        PARAMETERS,
        "out",
        build_log.LogKeeper(),
        log_path=tmp_path / "log.txt",
        **TOLERANCE,
    )
    assert answer["outcome"] == "broken"


def test_no_client_at_the_process_is_executable_unstartable(client, build_root, kernel):
    client.script = [probed(), built(), raises(local_run.ProgramNotFoundError("d"))]
    failure_of(operation(kernel), check_failure.KIND_EXECUTABLE_UNSTARTABLE)
    assert list(build_root.iterdir()) == []


def test_a_request_to_end_in_the_process_still_removes_the_build_directory(
    client, build_root, kernel
):
    client.script = [probed(), built(), raises(KeyboardInterrupt()), None]
    with pytest.raises(KeyboardInterrupt):
        call(operation(kernel))
    assert list(build_root.iterdir()) == []


def test_run_process_runs_the_program_with_the_gpus_and_the_bound(client, tmp_path):
    client.script = [reported()]
    outcomes = []
    ran = cuda_check.run_process(
        outcomes, IMAGE, str(tmp_path), "/build/x", ("1", "2"), 9, 2**20
    )
    assert ran.stdout == REPORT and outcomes == [ran]
    (command,) = client.runs()
    assert inner(command) == ["/build/x", "1", "2"]
    assert command[command.index("--memory") + 1] == str(2**20)
    assert_gpu_containers(client)


def test_run_process_answers_a_time_limit_raised_by_the_removal(client, tmp_path):
    client.script = [timed_out(), raises(OSError("removal"))]
    assert (
        cuda_check.run_process([], IMAGE, str(tmp_path), "/build/x", (), 9, None)
        == "time_limit"
    )


def test_an_unusable_build_directory_starts_nothing(
    monkeypatch, client, build_root, kernel
):
    def refused(prefix):
        raise tools.ToolFailure(check_failure.KIND_BUILD_DIRECTORY_UNUSABLE, "m")

    monkeypatch.setattr(standin_check, "make_build_dir", refused)
    failure_of(operation(kernel), check_failure.KIND_BUILD_DIRECTORY_UNUSABLE)
    assert client.calls == []


# On the real GPU (FR-19 (5))


def real_image():
    return os.environ.get(cuda_image.ENV_IMAGE) or REAL_IMAGE


@pytest.fixture
def gpu(monkeypatch, tmp_path):
    if os.name != "posix" or not hasattr(os, "getuid"):
        pytest.skip("the containers need a POSIX host with a numeric user")
    if shutil.which("docker") is None:
        pytest.skip("docker is not on PATH (FR-19 (5): a vendor tool's execution test)")
    image = real_image()
    found = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        check=False,
        timeout=LIMIT,
    )
    if found.returncode != 0:
        pytest.skip(f"the image {image} is not in the local store")
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    outcome = cuda_adapter.check_device_in_container(
        image, str(probe_dir), timeout_s=LIMIT, removal_timeout_s=60
    )
    if outcome.form != vendor_adapter.GO_ON:
        pytest.skip(f"no usable GPU in a container of {image}: {outcome.message}")
    monkeypatch.setenv(cuda_image.ENV_IMAGE, image)


HW_PROFILE = {
    "schema_version": SCHEMA_VERSION,
    "accelerator": targets.CUDA_GPU,
    "revision": "A GPU of the test sm_89",
    "toolchain": {"nvcc": "n", "gcc": "g", "nvidia_driver": "d"},
    "host": {"cpu": "c", "os": "o"},
    "hw_source": "external",
}


def placed(tmp_path, fixture):
    output = tmp_path / "output"
    output.mkdir(exist_ok=True)
    text = (FIXTURES / fixture).read_text(encoding="utf-8")
    if fixture == "gemm_wrong.cu":
        text = "#define GEMM_WRONG 1\n" + (FIXTURES / "gemm.cu").read_text(
            encoding="utf-8"
        )
    (output / fixture).write_text(text, encoding="utf-8")
    return output


def a_table(fixture):
    target = targets.target(targets.CUDA_GPU)

    def selection(output_path):
        return (Path(output_path) / fixture,)

    run = cuda_run.operation_for(target, sources=selection)
    return backends.BackendTable(
        [
            backends.Backend(
                targets.CUDA_GPU,
                {
                    TOOL: cuda_check.operation_for(target, sources=selection),
                    "sim.run": run,
                    "board.run": run,
                },
            )
        ]
    )


def checked_on_the_gpu(tmp_path, fixture, parameters=PARAMETERS):
    log_path = tmp_path / "build-log.txt"
    keeper = build_log.LogKeeper()
    op = backends.select(a_table(fixture), HW_PROFILE, TOOL)
    result = check_operation.ask(
        op,
        {"run_id": "test"},
        HW_PROFILE,
        parameters,
        str(placed(tmp_path, fixture)),
        keeper,
        log_path=log_path,
        **TOLERANCE,
    )
    return result, log_path


@pytest.mark.parametrize(
    "parameters",
    [PARAMETERS, CheckParameters(seed=7, draws=3, m=8, k=8, n=8)],
    ids=["5x33x7", "8x8x8"],
)
def test_a_correct_kernel_passes_on_the_gpu(gpu, tmp_path, parameters):
    result, log_path = checked_on_the_gpu(tmp_path, "gemm.cu", parameters)
    assert result["outcome"] == "pass"
    assert log_path.is_file()


def test_a_wrong_kernel_fails_on_the_gpu(gpu, tmp_path):
    result, _ = checked_on_the_gpu(tmp_path, "gemm_wrong.cu")
    assert result["outcome"] == "fail"


def test_a_kernel_that_does_not_compile_is_built_broken_with_its_log(gpu, tmp_path):
    result, log_path = checked_on_the_gpu(tmp_path, "broken.cu")
    assert (result["outcome"], result["condition"]) == ("broken", "build_exit_status")
    assert "broken.cu" in log_path.read_text(encoding="utf-8")


def test_a_kernel_that_exits_non_zero_is_broken(gpu, tmp_path):
    result, _ = checked_on_the_gpu(tmp_path, "gemm_exit.cu")
    assert (result["outcome"], result["condition"]) == ("broken", "exit_status")


def test_a_device_lost_after_the_probe_is_a_run_failure(gpu, tmp_path, monkeypatch):
    def without_the_gpus(outcomes, image, build_dir, program, arguments, limit, bound):
        return standin_check.run_container(
            outcomes,
            standin_answer.PROCESS,
            image,
            build_dir,
            program,
            arguments,
            limit,
            memory_limit_bytes=bound,
        )

    monkeypatch.setattr(cuda_check, "run_process", without_the_gpus)
    result, _ = checked_on_the_gpu(tmp_path, "gemm.cu")
    assert (result["outcome"], result["condition"]) == ("broken", "exit_status")
