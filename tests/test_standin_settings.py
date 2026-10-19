"""Tests of the cpu_standin build settings (ADR-0116 decisions 3 to 6)."""

import os
import shutil
from pathlib import Path

import pytest

from hilclaw import standin_settings
from hilclaw.harness.timing import run_timing
from hilclaw.harness.timing_build import build_timing_executable
from hilclaw.harness.verification import Verdict, run_verification
from hilclaw.harness.verification_build import build_verification_executable
from hilclaw.standin_settings import ENV, FLAGS, TRAILING_FLAGS

KERNELS = Path(__file__).parent / "harness" / "calibration"
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60
SHAPE = {"m": 3, "k": 4, "n": 5}
TOLERANCE = {"rtol": 1e-5, "atol": 1e-3}
SEED = 2026

GEMM_HEAD = """#include <stddef.h>
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a,
                  const float *restrict b, float *restrict c)
{
"""
GEMM_LOOP = """    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""


def test_the_values_are_those_of_the_record():
    assert type(FLAGS) is tuple
    assert FLAGS == ("-std=gnu11", "-O2", "-ffp-contract=off")
    assert type(TRAILING_FLAGS) is tuple
    assert TRAILING_FLAGS == ("-lm",)
    assert all(type(flag) is str for flag in (*FLAGS, *TRAILING_FLAGS))
    assert ENV is None


def test_the_module_exposes_only_the_three_settings():
    public = {name for name in vars(standin_settings) if not name.startswith("_")}
    assert public == {"FLAGS", "TRAILING_FLAGS", "ENV"}


@pytest.mark.parametrize(
    "prefix",
    [
        "-o",
        "--output",
        "-march",
        "-mcpu",
        "-fopenmp",
        "-W",
        "-D",
        "-ffast-math",
        "-flto",
    ],
)
def test_no_flag_is_a_setting_the_record_leaves_out(prefix):
    assert not any(flag.startswith(prefix) for flag in FLAGS)


@pytest.mark.parametrize("runtime", ["-lomp", "-lgomp"])
def test_no_openmp_runtime_is_linked(runtime):
    assert runtime not in TRAILING_FLAGS


@pytest.fixture(scope="module")
def clang():
    if os.name != "posix":
        pytest.skip("a harness executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def build_verification(kernel, output, flags=FLAGS):
    return build_verification_executable(
        kernel,
        output,
        timeout_s=BUILD_TIMEOUT,
        flags=flags,
        trailing_flags=TRAILING_FLAGS,
        env=ENV,
    )


def verify(executable):
    result = run_verification(
        executable,
        **SHAPE,
        draws=1,
        seed=SEED,
        **TOLERANCE,
        timeout_s=RUN_TIMEOUT,
        env=ENV,
    )
    assert result.broken is None, (result.run.returncode, result.run.stderr)
    return result.verdict


def kernel_source(tmp_path, text):
    source = tmp_path / "kernel.c"
    source.write_text(text, encoding="utf-8")
    return source


@pytest.mark.parametrize(
    ("state", "expected"), [("conforming", Verdict.PASS), ("failing", Verdict.FAIL)]
)
def test_the_verification_program_builds_and_keeps_its_verdicts(
    clang, tmp_path, state, expected
):
    executable = tmp_path / "verification"
    result = build_verification(KERNELS / f"gemm_{state}.c", executable)
    assert result.ok, result.log
    assert verify(executable) is expected


def test_the_timing_driver_builds_and_runs(clang, tmp_path):
    executable = tmp_path / "timing"
    result = build_timing_executable(
        KERNELS / "gemm_conforming.c",
        executable,
        timeout_s=BUILD_TIMEOUT,
        flags=FLAGS,
        trailing_flags=TRAILING_FLAGS,
        env=ENV,
    )
    assert result.ok, result.log
    run = run_timing(
        executable,
        m=64,
        k=64,
        n=64,
        sample_form="interval",
        seed=SEED,
        timeout_s=RUN_TIMEOUT,
        env=ENV,
    )
    assert run.broken is None, (run.run.returncode, run.run.stderr)


def test_a_kernel_that_calls_the_math_library_links(clang, tmp_path):
    text = (
        "#include <math.h>\nvolatile float hilclaw_test_sink;\n"
        + GEMM_HEAD
        + "    hilclaw_test_sink = expf(a[0]);\n"
        + GEMM_LOOP
    )
    executable = tmp_path / "verification"
    result = build_verification(kernel_source(tmp_path, text), executable)
    assert result.ok, result.log
    assert verify(executable) is Verdict.PASS


@pytest.mark.parametrize(
    "text",
    [
        "int omp_get_max_threads(void);\nvolatile int hilclaw_test_sink;\n"
        + GEMM_HEAD
        + "    hilclaw_test_sink = omp_get_max_threads();\n"
        + GEMM_LOOP,
        GEMM_HEAD + "    float sum = ;\n" + GEMM_LOOP,
    ],
    ids=["openmp-runtime-call", "syntax-error"],
)
def test_a_kernel_outside_the_set_is_a_failed_build(clang, tmp_path, text):
    result = build_verification(kernel_source(tmp_path, text), tmp_path / "exe")
    assert not result.ok
    assert not (tmp_path / "exe").exists()


def test_a_warning_does_not_fail_the_build(clang, tmp_path):
    source = kernel_source(tmp_path, GEMM_HEAD + "    int unused = 0;\n" + GEMM_LOOP)
    strict = build_verification(
        source, tmp_path / "strict", (*FLAGS, "-Wall", "-Werror")
    )
    assert not strict.ok
    executable = tmp_path / "verification"
    result = build_verification(source, executable)
    assert result.ok, result.log
    assert verify(executable) is Verdict.PASS
