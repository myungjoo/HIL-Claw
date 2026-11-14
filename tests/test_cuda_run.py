import sys
from pathlib import Path

import pytest
import test_cuda_check as checks

from hilclaw import (
    backends,
    build_log,
    check_failure,
    cuda_run,
    local_run,
    run_operation,
    standin_settings,
    targets,
    tools,
)
from hilclaw.harness import cuda_programs, memory_ceiling, timing
from hilclaw.run_parameters import Bf16TimingParameters, TimingParameters

PARAMETERS = TimingParameters(m=5, k=33, n=7, n_max=20, sample_form="interval", seed=99)
RUN_TOOLS = ("sim.run", "board.run")
posix_only = checks.posix_only
stubs = checks.stubs
build_root = checks.build_root
kernel = checks.kernel
gpu = checks.gpu


def operation(kernel, target=None):
    return cuda_run.operation_for(
        checks.the_target() if target is None else target,
        sources=lambda output_path: (kernel,),
    )


def call(op, parameters=PARAMETERS, keeper=None):
    keeper = build_log.LogKeeper() if keeper is None else keeper
    return op("request", "hw_profile", parameters, "output-path", keeper)


def failure_of(op, kind, **kwargs):
    with pytest.raises(tools.ToolFailure) as raised:
        call(op, **kwargs)
    assert raised.value.kind == kind
    return raised.value


# The module


def test_the_public_names_of_the_module():
    public = {name for name in vars(cuda_run) if not name.startswith("_")}
    imported = {
        "sys",
        "cuda_adapter",
        "cuda_check",
        "local_run",
        "run_parameters",
        "standin_settings",
        "tools",
        "vendor_adapter",
        "cuda_programs",
        "memory_ceiling",
        "timing",
    }
    assert public - imported == {
        "TIMING_EXECUTABLE_NAME",
        "BUILD_DIR_PREFIX",
        "operation_for",
    }


def test_the_module_reads_no_attempt_file_name():
    assert not {"kernel_source", "attempt_kernel"} & set(vars(cuda_run))
    assert "HQ-0104" in cuda_run.__doc__ and "test-only" in cuda_run.__doc__


# operation_for


def test_operation_for_refuses_what_cuda_check_refuses(kernel):
    with pytest.raises(TypeError, match="target must be a Target"):
        cuda_run.operation_for("cuda_gpu", sources=lambda path: (kernel,))
    with pytest.raises(TypeError, match="sources must be a callable"):
        cuda_run.operation_for(checks.the_target(), sources=None)
    with pytest.raises(TypeError):
        cuda_run.operation_for(checks.the_target())


@posix_only
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
    stubs, build_root, kernel, parameters, keeper, error
):
    with pytest.raises(error):
        operation(kernel)(
            "r",
            "h",
            parameters,
            "out",
            build_log.LogKeeper() if keeper is None else keeper,
        )
    assert stubs.calls() == []
    assert list(build_root.iterdir()) == []


# With stub programs


@posix_only
def test_no_usable_device_is_device_unavailable_before_anything_else(
    stubs, build_root, kernel
):
    stubs.set("nvidia-smi", status=6)
    keeper = build_log.LogKeeper()
    failure_of(operation(kernel), check_failure.KIND_DEVICE_UNAVAILABLE, keeper=keeper)
    assert stubs.names() == ["nvidia-smi"] and keeper.held() is None
    assert list(build_root.iterdir()) == []


@posix_only
def test_a_built_timing_driver_is_run_and_its_report_and_host_figure_returned(
    stubs, build_root, kernel
):
    stubs.set("nvcc", program=checks.program(), stderr="a warning\n")
    keeper = build_log.LogKeeper()
    report, figure = call(operation(kernel), keeper=keeper)
    assert report == checks.REPORT.encode()
    assert figure is None or (type(figure) is int and figure >= 1)
    _, build, run = stubs.calls()
    target = checks.the_target()
    sources = build[1 + len(target.flags) : -2]
    assert sources == [str(cuda_programs.TIMING_DRIVER_SOURCE), str(kernel)]
    assert Path(run[1]).name == cuda_run.TIMING_EXECUTABLE_NAME
    assert Path(run[1]).parent.name.startswith(cuda_run.BUILD_DIR_PREFIX)
    assert tuple(run[2:]) == timing.driver_arguments(**PARAMETERS._asdict())
    assert "a warning" in keeper.held()
    assert list(build_root.iterdir()) == []


@posix_only
def test_the_answer_is_the_form_a_of_run_operation(stubs, build_root, kernel, tmp_path):
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
    assert answer.report == checks.REPORT.encode()
    assert (tmp_path / "log.txt").is_file()


@posix_only
@pytest.mark.parametrize(
    ("conf", "answer"),
    [({"status": 1}, "build_exit_status"), ({"sleep": 5}, "build_time_limit")],
)
def test_a_build_that_fails_is_its_condition(stubs, build_root, kernel, conf, answer):
    stubs.set("nvcc", **conf)
    keeper = build_log.LogKeeper()
    op = operation(kernel, checks.the_target(build_time_limit_s=1))
    assert call(op, keeper=keeper) == answer
    assert type(keeper.held()) is str
    assert list(build_root.iterdir()) == []


@posix_only
@pytest.mark.parametrize(
    ("conf", "answer"),
    [({"status": 1}, "exit_status"), ({"sleep": 5}, "time_limit")],
)
def test_a_timing_process_that_fails_is_broken(stubs, build_root, kernel, conf, answer):
    stubs.set("nvcc", program=checks.program(stdout="part", **conf))
    op = operation(kernel, checks.the_target(process_time_limit_cap_s=1))
    assert call(op) == answer
    assert list(build_root.iterdir()) == []


@posix_only
def test_a_timing_driver_that_cannot_start_is_executable_unstartable(
    stubs, build_root, kernel
):
    stubs.set("nvcc", program=checks.program(), mode=0o644)
    failure_of(operation(kernel), check_failure.KIND_EXECUTABLE_UNSTARTABLE)
    assert list(build_root.iterdir()) == []


@posix_only
def test_an_error_of_the_run_no_row_places_passes(
    stubs, build_root, kernel, monkeypatch
):
    def run(*args, **kwargs):
        raise PermissionError("not placed")

    monkeypatch.setattr(local_run, "run", run)
    monkeypatch.setattr(cuda_run.cuda_check, "confirm_device", lambda: None)
    with pytest.raises(PermissionError):
        call(operation(kernel))
    assert list(build_root.iterdir()) == []


def test_the_figure_is_the_host_process_s(monkeypatch, tmp_path):
    result = local_run.RunResult(0, False, b"r", b"", ("t",), 0.1, max_rss=2048)
    monkeypatch.setattr(local_run, "run", lambda command, **kwargs: result)
    target = checks.the_target()
    answer = cuda_run._time(target, tmp_path / "timing", PARAMETERS, 10)
    assert answer == (b"r", memory_ceiling.figure(2048, sys.platform))


def test_the_time_limit_is_the_timing_limit_of_the_target_s_cap(monkeypatch, tmp_path):
    seen = {}

    def run(command, *, timeout_s, env):
        seen["timeout_s"] = timeout_s
        return local_run.RunResult(0, False, b"r", b"", tuple(command), 0.1)

    monkeypatch.setattr(local_run, "run", run)
    target = checks.the_target()
    limit = cuda_run._checked(
        PARAMETERS, build_log.LogKeeper(), target.process_time_limit_cap_s
    )
    assert limit == standin_settings.timing_process_time_limit_s(
        5, 33, 7, 20, target.process_time_limit_cap_s
    )
    cuda_run._time(target, tmp_path / "timing", PARAMETERS, limit)
    assert seen["timeout_s"] == min(limit, target.process_time_limit_cap_s)


# On the real GPU (FR-19 (5))


def timed_on_the_gpu(tmp_path, fixture, tool):
    keeper = build_log.LogKeeper()
    op = backends.select(checks.a_table(fixture), checks.HW_PROFILE, tool)
    return run_operation.ask(
        op,
        {"run_id": "test"},
        checks.HW_PROFILE,
        PARAMETERS,
        str(checks.FIXTURES),
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
    assert answer.memory_bytes is None or answer.memory_bytes >= 1
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
