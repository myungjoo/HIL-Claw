import dataclasses
import os
import re
import shutil
from pathlib import Path

import pytest

from hilclaw import cuda_adapter, gemm_cuda_contract, local_run, targets
from hilclaw.harness import cuda_programs, timing, verification
from hilclaw.harness.cuda_programs import (
    TIMING_DRIVER_SOURCE,
    VERIFICATION_PROGRAM_SOURCE,
)
from hilclaw.harness.verification import Broken, Verdict
from hilclaw.vendor_adapter import GO_ON, PRESENT

FIXTURES = Path(__file__).resolve().parent.parent / "cuda_fixtures"
SOURCES = (VERIFICATION_PROGRAM_SOURCE, TIMING_DRIVER_SOURCE)
LIMIT = 300
TOLERANCE = {"rtol": 1e-4, "atol": 1e-4}
SHAPES = [(8, 8, 8), (5, 33, 7)]


# The module, everywhere


def test_the_two_sources_sit_beside_the_module():
    here = Path(cuda_programs.__file__).parent
    assert VERIFICATION_PROGRAM_SOURCE == here / "cuda_verification_program.c"
    assert TIMING_DRIVER_SOURCE == here / "cuda_timing_driver.c"
    for source in SOURCES:
        assert source.is_file()


def test_the_public_names_of_the_module():
    public = {name for name in vars(cuda_programs) if not name.startswith("_")}
    assert public - {"Path"} == {"VERIFICATION_PROGRAM_SOURCE", "TIMING_DRIVER_SOURCE"}


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.stem)
def test_each_program_is_c_against_the_cuda_runtime_api(source):
    text = source.read_text(encoding="utf-8")
    assert "#include <cuda_runtime_api.h>" in text
    assert "#include <cuda_runtime.h>" not in text
    assert "__global__" not in text and "<<<" not in text
    assert "int main(int argc, char **argv)" in text


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.stem)
def test_each_program_declares_the_contract_s_entry_point_with_c_linkage(source):
    declared = gemm_cuda_contract.PROTOTYPE.removeprefix('extern "C" ')
    assert gemm_cuda_contract.PROTOTYPE.startswith('extern "C" ')
    assert declared in source.read_text(encoding="utf-8")


@pytest.mark.parametrize("source", SOURCES, ids=lambda path: path.stem)
def test_each_program_waits_and_checks_after_the_kernel(source):
    text = source.read_text(encoding="utf-8")
    for call in ("cudaFree(NULL)", "cudaMalloc", "cudaMemcpy", "cudaDeviceSynchronize"):
        assert call in text
    assert re.search(r"cudaGetLastError\(\), \"hilclaw_gemm launch\"", text)


# Built with nvcc


@pytest.fixture
def nvcc():
    if os.name != "posix":
        pytest.skip("the programs use POSIX descriptors and CLOCK_MONOTONIC")
    if shutil.which("nvcc") is None:
        pytest.skip("nvcc is not on PATH (FR-19 (5): a vendor tool's execution test)")
    if shutil.which("g++") is None:
        pytest.skip("nvcc needs the host compiler g++, which is not on PATH")


@pytest.fixture
def gpu(nvcc):
    if shutil.which("nvidia-smi") is None:
        pytest.skip(
            "nvidia-smi is not on PATH (FR-19 (5): a vendor tool's execution test)"
        )
    found = cuda_adapter.device_probe(timeout_s=LIMIT)
    if found.state != PRESENT:
        pytest.skip(f"no usable GPU: {found.message}")


def built(tmp_path, program, kernel="gemm.cu", target=None):
    held = targets.target(targets.CUDA_GPU) if target is None else target
    out = tmp_path / f"{program.stem}-{Path(kernel).stem}"
    outcome = cuda_adapter.build(held, (program, FIXTURES / kernel), out)
    assert (outcome.form, outcome.carried) == (GO_ON, out)
    return out


def built_without_a_device(tmp_path, program):
    held = targets.target(targets.CUDA_GPU)
    return built(tmp_path, program, target=dataclasses.replace(held, flags=("-O2",)))


def assert_refused(result, status, stem, stdout_mark):
    assert result.returncode == status
    assert stdout_mark not in result.stdout
    lines = result.stderr.decode("utf-8", "replace").strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith(f"{stem}: ")


VERIFICATION_REFUSED = {
    "too_few": ("8", "8", "8", "1"),
    "too_many": ("8", "8", "8", "1", "7", "0"),
    "leading_zero": ("08", "8", "8", "1", "7"),
    "zero_dimension": ("8", "0", "8", "1", "7"),
    "zero_draws": ("8", "8", "8", "0", "7"),
    "signed": ("8", "8", "+8", "1", "7"),
}


@pytest.mark.parametrize(
    "arguments", VERIFICATION_REFUSED.values(), ids=list(VERIFICATION_REFUSED)
)
def test_the_verification_program_refuses_a_command_line(nvcc, tmp_path, arguments):
    executable = built_without_a_device(tmp_path, VERIFICATION_PROGRAM_SOURCE)
    result = local_run.run((executable, *arguments), timeout_s=LIMIT)
    assert_refused(result, 2, "cuda_verification_program", b"end\n")
    assert result.stdout == b""


TIMING_REFUSED = {
    "too_few": ("8", "8", "8", "5", "10", "0.01", "interval"),
    "leading_zero": ("8", "08", "8", "5", "10", "0.01", "interval", "7"),
    "zero_dimension": ("0", "8", "8", "5", "10", "0.01", "interval", "7"),
    "n_max_below_n_min": ("8", "8", "8", "5", "4", "0.01", "interval", "7"),
    "cv_max": ("8", "8", "8", "5", "10", "-1", "interval", "7"),
    "sample_form": ("8", "8", "8", "5", "10", "0.01", "median", "7"),
}


@pytest.mark.parametrize("arguments", TIMING_REFUSED.values(), ids=list(TIMING_REFUSED))
def test_the_timing_driver_refuses_a_command_line(nvcc, tmp_path, arguments):
    executable = built_without_a_device(tmp_path, TIMING_DRIVER_SOURCE)
    result = local_run.run((executable, *arguments), timeout_s=LIMIT)
    assert_refused(result, 2, "cuda_timing_driver", b"stop")
    assert result.stdout == b""


# On the GPU (FR-19 (5))


@pytest.mark.parametrize("shape", SHAPES, ids=["square", "non_square"])
def test_real_gpu_a_correct_kernel_passes(gpu, tmp_path, shape):
    m, k, n = shape
    executable = built(tmp_path, VERIFICATION_PROGRAM_SOURCE)
    result = verification.run_verification(
        executable, m=m, k=k, n=n, draws=3, seed=7, timeout_s=LIMIT, **TOLERANCE
    )
    assert (result.broken, result.verdict) == (None, Verdict.PASS)
    assert [count.failed for count in result.counts] == [0, 0, 0]
    assert result.run.returncode == 0


def test_real_gpu_a_wrong_kernel_fails(gpu, tmp_path):
    m, k, n = SHAPES[1]
    executable = built(tmp_path, VERIFICATION_PROGRAM_SOURCE, "gemm_wrong.cu")
    result = verification.run_verification(
        executable, m=m, k=k, n=n, draws=2, seed=7, timeout_s=LIMIT, **TOLERANCE
    )
    assert (result.broken, result.verdict) == (None, Verdict.FAIL)
    assert [count.failed for count in result.counts] == [m * n, m * n]
    assert [count.non_finite for count in result.counts] == [0, 0]


def test_real_gpu_the_report_is_judged_by_the_unchanged_judge(gpu, tmp_path):
    m, k, n = SHAPES[1]
    executable = built(tmp_path, VERIFICATION_PROGRAM_SOURCE)
    arguments = verification.program_arguments(m=m, k=k, n=n, draws=2, seed=11)
    result = local_run.run((executable, *arguments), timeout_s=LIMIT)
    assert len(result.stdout) == 2 * (4 + 4 * m * n) + 4
    judged = verification.judge_report(
        result.stdout, m=m, k=k, n=n, draws=2, seed=11, **TOLERANCE
    )
    assert (judged.broken, judged.verdict) == (None, Verdict.PASS)
    wrong_seed = verification.judge_report(
        result.stdout, m=m, k=k, n=n, draws=2, seed=12, **TOLERANCE
    )
    assert wrong_seed.broken is Broken.CHECK_VALUE


@pytest.mark.parametrize("sample_form", timing.SAMPLE_FORMS)
def test_real_gpu_the_timing_report_is_accepted(gpu, tmp_path, sample_form):
    m, k, n = SHAPES[1]
    executable = built(tmp_path, TIMING_DRIVER_SOURCE)
    result = timing.run_timing(
        executable,
        m=m,
        k=k,
        n=n,
        sample_form=sample_form,
        seed=7,
        n_max=40,
        timeout_s=LIMIT,
    )
    assert result.broken is None
    assert result.state in (
        timing.measurement.State.CONVERGED,
        timing.measurement.State.NOT_CONVERGED,
    )
    assert result.resolution_ns > 0
    assert all(interval > 0 for interval in result.intervals_ns)
    assert timing.parse_report(result.run.stdout) is not None


@pytest.mark.parametrize(
    ("source", "arguments", "mark"),
    [
        (VERIFICATION_PROGRAM_SOURCE, ("8", "8", "8", "1", "7"), b"end\n"),
        (
            TIMING_DRIVER_SOURCE,
            ("8", "8", "8", "5", "10", "0.01", "interval", "7"),
            b"stop",
        ),
    ],
    ids=["verification", "timing"],
)
def test_real_gpu_a_cuda_runtime_error_ends_without_a_complete_report(
    gpu, tmp_path, source, arguments, mark
):
    executable = built(tmp_path, source)
    hidden = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    result = local_run.run((executable, *arguments), timeout_s=LIMIT, env=hidden)
    assert result.returncode == 1
    assert mark not in result.stdout
    lines = result.stderr.decode("utf-8", "replace").strip().splitlines()
    assert len(lines) == 1
    assert "cudaFree: cudaErrorNoDevice" in lines[0]


def test_real_gpu_a_hidden_device_is_a_broken_verification(gpu, tmp_path):
    executable = built(tmp_path, VERIFICATION_PROGRAM_SOURCE)
    hidden = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    result = verification.run_verification(
        executable,
        m=4,
        k=4,
        n=4,
        draws=1,
        seed=7,
        timeout_s=LIMIT,
        env=hidden,
        **TOLERANCE,
    )
    assert (result.broken, result.verdict, result.counts) == (
        Broken.EXIT_STATUS,
        None,
        None,
    )
