import os

import pytest
import test_cuda_check as checks

from hilclaw import (
    backends,
    build_log,
    check_failure,
    cuda_run,
    local_run,
    run_operation,
    standin_run,
    standin_settings,
    targets,
)
from hilclaw.harness import cuda_programs, timing
from hilclaw.run_parameters import Bf16TimingParameters, TimingParameters

PARAMETERS = TimingParameters(m=5, k=33, n=7, n_max=20, sample_form="interval", seed=99)
RUN_TOOLS = ("sim.run", "board.run")
INSIDE = checks.INSIDE
IMAGE = checks.IMAGE
REPORT = b"resolution_ns 1\ninterval_ns 5"
client = checks.client
build_root = checks.build_root
kernel = checks.kernel
gpu = checks.gpu
ended = checks.ended
timed_out = checks.timed_out
raises = checks.raises
probed = checks.probed
inner = checks.inner


def timing_built(**kwargs):
    return checks.built(cuda_run.TIMING_EXECUTABLE_NAME, **kwargs)


def waiter_built(**kwargs):
    return checks.built(cuda_run.WAITER_EXECUTABLE_NAME, **kwargs)


def waited(report=REPORT, line=b"waiter_max_rss_kib 300", status=0):
    return ended(status, stdout=report + b"\n" + line + b"\n", stderr=b"proc")


def happy():
    return [probed(), timing_built(), waiter_built(), waited()]


def operation(kernel, target=None):
    return cuda_run.operation_for(
        checks.the_target() if target is None else target,
        sources=lambda output_path: (kernel,),
    )


def call(op, parameters=PARAMETERS, keeper=None):
    keeper = build_log.LogKeeper() if keeper is None else keeper
    return op("request", "hw_profile", parameters, "output-path", keeper)


def failure_of(op, kind, **kwargs):
    with pytest.raises(checks.tools.ToolFailure) as raised:
        call(op, **kwargs)
    assert raised.value.kind == kind
    assert IMAGE not in raised.value.message
    return raised.value


# The module


def test_the_public_names_of_the_module():
    public = {name for name in vars(cuda_run) if not name.startswith("_")}
    imported = {
        "monotonic",
        "cuda_check",
        "run_failure",
        "run_parameters",
        "standin_answer",
        "standin_check",
        "standin_run",
        "standin_settings",
        "standin_waiter_line",
        "cuda_programs",
        "timing",
    }
    assert public - imported == {
        "TIMING_EXECUTABLE_NAME",
        "WAITER_EXECUTABLE_NAME",
        "BUILD_DIR_PREFIX",
        "operation_for",
    }


def test_the_module_reads_no_attempt_file_name_and_runs_nothing_on_the_host():
    assert not {"kernel_source", "attempt_kernel"} & set(vars(cuda_run))
    assert not {"local_run", "cuda_adapter", "memory_ceiling"} & set(vars(cuda_run))
    assert "HQ-0104" in cuda_run.__doc__ and "in containers" in cuda_run.__doc__
    assert "test-only" not in cuda_run.__doc__


# operation_for


def test_operation_for_refuses_what_cuda_check_refuses(kernel):
    with pytest.raises(TypeError, match="target must be a Target"):
        cuda_run.operation_for("cuda_gpu", sources=lambda path: (kernel,))
    with pytest.raises(TypeError, match="sources must be a callable"):
        cuda_run.operation_for(checks.the_target(), sources=None)
    with pytest.raises(TypeError):
        cuda_run.operation_for(checks.the_target())


@pytest.mark.parametrize(
    ("parameters", "keeper", "error"),
    [
        (Bf16TimingParameters("gemm", "bf16", {}, 20, "interval", 1), None, TypeError),
        (tuple(PARAMETERS), None, TypeError),
        (PARAMETERS, object(), TypeError),
        (PARAMETERS._replace(m=0), None, ValueError),
        (PARAMETERS._replace(n_max=1), None, ValueError),
        (PARAMETERS._replace(sample_form="some"), None, ValueError),
        (PARAMETERS._replace(seed=-1), None, ValueError),
    ],
)
def test_refused_arguments_start_nothing(
    client, build_root, kernel, parameters, keeper, error
):
    with pytest.raises(error):
        operation(kernel)(
            "r",
            "h",
            parameters,
            "out",
            build_log.LogKeeper() if keeper is None else keeper,
        )
    assert client.calls == []
    assert list(build_root.iterdir()) == []


def test_no_image_is_compiler_unavailable_before_anything(
    monkeypatch, client, build_root, kernel
):
    monkeypatch.delenv(checks.cuda_image.ENV_IMAGE)
    failure_of(operation(kernel), check_failure.KIND_COMPILER_UNAVAILABLE)
    assert client.calls == []
    assert list(build_root.iterdir()) == []


# With the stub client


@pytest.mark.parametrize("answer", [ended(6), ended(125), timed_out()])
def test_no_usable_device_is_device_unavailable_before_any_build(
    client, build_root, kernel, answer
):
    client.script = [answer]
    keeper = build_log.LogKeeper()
    failure_of(operation(kernel), check_failure.KIND_DEVICE_UNAVAILABLE, keeper=keeper)
    assert len(client.runs()) == 1 and keeper.held() is None
    assert list(build_root.iterdir()) == []


def test_the_timing_process_runs_under_the_waiter_in_gpu_containers(
    client, build_root, kernel
):
    seen = {}
    client.script = [probed(), timing_built(seen=seen), waiter_built(), waited()]
    keeper = build_log.LogKeeper()
    assert call(operation(kernel), keeper=keeper) == (REPORT, 300 * 1024)
    assert keeper.held() == (checks.BUILD_STDOUT + checks.BUILD_STDERR).decode()
    probe, build, waiter, process = client.runs()
    checks.assert_gpu_containers(client)
    assert inner(probe)[0] == "nvidia-smi"
    target = checks.the_target()
    assert inner(build) == [
        "nvcc",
        *target.flags,
        f"{INSIDE}/{cuda_programs.TIMING_DRIVER_SOURCE.name}",
        f"{INSIDE}/kernel/kernel.cu",
        *target.trailing_flags,
        "-o",
        f"{INSIDE}/timing",
    ]
    assert inner(waiter) == [
        "nvcc",
        *target.waiter_flags,
        f"{INSIDE}/timing_waiter.c",
        "-o",
        f"{INSIDE}/waiter",
    ]
    assert inner(process) == [
        f"{INSIDE}/waiter",
        f"{INSIDE}/timing",
        *timing.driver_arguments(**PARAMETERS._asdict()),
    ]
    assert seen["timing_waiter.c"] == standin_run.WAITER_SOURCE.read_bytes()
    assert "--memory" not in process
    options = client.options()
    assert options[0]["timeout_s"] == checks.cuda_check.DEVICE_QUERY_TIMEOUT_S
    assert options[1]["timeout_s"] == target.build_time_limit_s
    assert 0 < options[2]["timeout_s"] <= target.build_time_limit_s
    assert options[3]["timeout_s"] == standin_settings.timing_process_time_limit_s(
        5, 33, 7, 20, target.process_time_limit_cap_s
    )
    assert os.path.basename(checks.mount_source(build)).startswith(
        cuda_run.BUILD_DIR_PREFIX
    )
    assert list(build_root.iterdir()) == []


def test_the_answer_is_the_form_a_of_run_operation(
    client, build_root, kernel, tmp_path
):
    client.script = happy()
    answer = run_operation.ask(
        operation(kernel),
        "r",
        "h",
        PARAMETERS,
        "out",
        build_log.LogKeeper(),
        log_path=tmp_path / "log.txt",
    )
    assert type(answer) is run_operation.Reported
    assert (answer.report, answer.memory_bytes) == (REPORT, 300 * 1024)
    assert (tmp_path / "log.txt").is_file()


def test_the_none_line_gives_no_figure(client, build_root, kernel):
    client.script = [*happy()[:3], waited(line=b"waiter_max_rss none")]
    assert call(operation(kernel)) == (REPORT, None)


def test_a_memory_limit_of_the_target_bounds_only_the_timing_process(
    client, build_root, kernel
):
    client.script = happy()
    call(operation(kernel, checks.the_target(memory_limit_bytes=2**30)))
    *others, process = client.runs()
    assert all("--memory" not in command for command in others)
    assert process[process.index("--memory") + 1] == str(2**30)


@pytest.mark.parametrize(
    ("answer", "condition"),
    [(ended(1), "build_exit_status"), (timed_out(), "build_time_limit")],
)
def test_a_timing_build_that_fails_is_its_condition_with_no_waiter_build(
    client, build_root, kernel, answer, condition
):
    client.script = [probed(), answer]
    keeper = build_log.LogKeeper()
    assert call(operation(kernel), keeper=keeper) == condition
    assert type(keeper.held()) is str and len(client.runs()) == 2
    assert list(build_root.iterdir()) == []


def test_a_timing_build_with_no_executable_is_build_output_missing(
    client, build_root, kernel
):
    client.script = [probed(), timing_built(executable=False)]
    failure = failure_of(operation(kernel), check_failure.KIND_BUILD_OUTPUT_MISSING)
    assert "timing" in failure.message
    assert list(build_root.iterdir()) == []


@pytest.mark.parametrize(
    ("answer", "condition"),
    [
        (ended(1, stderr=b"waiter error"), "build_exit_status"),
        (timed_out(), "build_time_limit"),
    ],
)
def test_a_waiter_build_that_fails_is_its_condition_and_its_log_is_not_kept(
    client, build_root, kernel, answer, condition
):
    client.script = [probed(), timing_built(), answer]
    keeper = build_log.LogKeeper()
    assert call(operation(kernel), keeper=keeper) == condition
    assert "waiter error" not in keeper.held()
    assert len(client.runs()) == 3
    assert list(build_root.iterdir()) == []


def test_a_waiter_build_with_no_executable_is_build_output_missing(
    client, build_root, kernel
):
    client.script = [probed(), timing_built(), waiter_built(executable=False)]
    failure = failure_of(operation(kernel), check_failure.KIND_BUILD_OUTPUT_MISSING)
    assert "waiter" in failure.message
    assert list(build_root.iterdir()) == []


def test_no_build_time_left_for_the_waiter_starts_no_container(
    monkeypatch, client, build_root, kernel
):
    ticks = iter((0.0, 1000.0))
    monkeypatch.setattr(cuda_run, "monotonic", lambda: next(ticks))
    client.script = [probed(), timing_built()]
    assert call(operation(kernel)) == "build_time_limit"
    assert len(client.runs()) == 2
    assert list(build_root.iterdir()) == []


@pytest.mark.parametrize(
    ("answer", "condition"),
    [
        (waited(status=1), "exit_status"),
        (waited(status=125), "exit_status"),
        (ended(127), "exit_status"),
        (timed_out(), "time_limit"),
    ],
)
def test_a_timing_process_that_fails_is_broken(
    client, build_root, kernel, answer, condition
):
    client.script = [*happy()[:3], answer]
    assert call(operation(kernel)) == condition
    assert list(build_root.iterdir()) == []


def test_a_timing_stream_with_status_0_and_no_waiter_line_is_not_placed(
    client, build_root, kernel
):
    client.script = [*happy()[:3], ended(0, stdout=REPORT)]
    with pytest.raises(RuntimeError, match="no row places"):
        call(operation(kernel))
    assert list(build_root.iterdir()) == []


def test_no_client_at_the_timing_process_is_executable_unstartable(
    client, build_root, kernel
):
    client.script = [*happy()[:3], raises(local_run.ProgramNotFoundError("docker"))]
    failure_of(operation(kernel), check_failure.KIND_EXECUTABLE_UNSTARTABLE)
    assert list(build_root.iterdir()) == []


def test_a_failed_selection_starts_no_build(client, build_root):
    client.script = [probed()]
    op = cuda_run.operation_for(checks.the_target(), sources=lambda path: ())
    failure_of(op, check_failure.KIND_NO_KERNEL_SOURCE)
    assert len(client.runs()) == 1
    assert list(build_root.iterdir()) == []


# On the real GPU (FR-19 (5))


def timed_on_the_gpu(tmp_path, fixture, tool):
    keeper = build_log.LogKeeper()
    op = backends.select(checks.a_table(fixture), checks.HW_PROFILE, tool)
    return run_operation.ask(
        op,
        {"run_id": "test"},
        checks.HW_PROFILE,
        PARAMETERS,
        str(checks.placed(tmp_path, fixture)),
        keeper,
        log_path=tmp_path / f"{tool}-log.txt",
    )


@pytest.mark.parametrize("tool", RUN_TOOLS)
def test_a_correct_kernel_is_timed_on_the_gpu(gpu, tmp_path, tool):
    answer = timed_on_the_gpu(tmp_path, "gemm.cu", tool)
    assert type(answer) is run_operation.Reported
    judged = timing.judge_report(
        answer.report, sample_form=PARAMETERS.sample_form, n_max=PARAMETERS.n_max
    )
    assert judged.broken is None
    assert timing.parse_report(answer.report) is not None
    assert type(answer.memory_bytes) is int and answer.memory_bytes > 0
    assert (tmp_path / f"{tool}-log.txt").is_file()


def test_both_run_tools_are_one_operation():
    table = checks.a_table("gemm.cu")
    sim = backends.select(table, checks.HW_PROFILE, "sim.run")
    assert backends.select(table, checks.HW_PROFILE, "board.run") is sim
    target = targets.target(targets.CUDA_GPU)
    assert (target.unit, target.units_per_ns) == ("ns", 1)


@pytest.mark.parametrize(
    ("fixture", "answer"),
    [("broken.cu", "build_exit_status"), ("gemm_exit.cu", "exit_status")],
)
def test_a_kernel_that_does_not_build_or_exits_is_broken_on_the_gpu(
    gpu,
    tmp_path,
    fixture,
    answer,
):
    assert timed_on_the_gpu(tmp_path, fixture, "board.run") == answer
