"""Tests of the cpu_standin build settings and time limits (ADR-0116, ADR-0117)."""

import math
import os
import shutil
from fractions import Fraction
from pathlib import Path

import pytest

from hilclaw import standin_settings
from hilclaw.harness.timing import run_timing
from hilclaw.harness.timing_build import build_timing_executable
from hilclaw.harness.verification import Verdict, run_verification
from hilclaw.harness.verification_build import build_verification_executable
from hilclaw.standin_settings import (
    BUILD_TIME_LIMIT_S,
    ENV,
    FLAGS,
    PROCESS_TIME_LIMIT_CAP_S,
    TRAILING_FLAGS,
    timing_process_time_limit_s,
    verification_process_time_limit_s,
)

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


def test_the_module_exposes_only_the_settings_and_the_time_limits():
    public = {name for name in vars(standin_settings) if not name.startswith("_")}
    assert public == {
        "FLAGS",
        "TRAILING_FLAGS",
        "ENV",
        "BUILD_TIME_LIMIT_S",
        "PROCESS_TIME_LIMIT_CAP_S",
        "verification_process_time_limit_s",
        "timing_process_time_limit_s",
    }


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


GATE_UP_512 = {"m": 512, "k": 2048, "n": 8192}
O_1 = {"m": 1, "k": 2048, "n": 2048}
LIMIT_FUNCTIONS = [
    (verification_process_time_limit_s, "draws"),
    (timing_process_time_limit_s, "n_max"),
]
CLANG_BUILD_MAX_TIMEOUT_S = (2**31 - 1) / 1000


def expected(m, k, n, calls):
    rule = 10 + calls * (1 + Fraction(2 * m * k * n, 2 * 10**8))
    return float(min(rule, Fraction(1500)))


def test_the_time_limit_constants_are_those_of_the_record():
    assert type(BUILD_TIME_LIMIT_S) is int
    assert BUILD_TIME_LIMIT_S == 60
    assert type(PROCESS_TIME_LIMIT_CAP_S) is int
    assert PROCESS_TIME_LIMIT_CAP_S == 1500


@pytest.mark.parametrize(
    "shape", [GATE_UP_512, O_1, {"m": 1, "k": 1, "n": 1}, {"m": 3, "k": 4, "n": 5}]
)
@pytest.mark.parametrize("count", [1, 2, 10, 17, 18, 40])
def test_the_rule_is_exact(shape, count):
    verification = verification_process_time_limit_s(**shape, draws=count)
    timing = timing_process_time_limit_s(**shape, n_max=count)
    assert type(verification) is float
    assert type(timing) is float
    assert verification == expected(**shape, calls=count)
    assert timing == expected(**shape, calls=count + 1)


def test_the_figures_of_the_record():
    assert timing_process_time_limit_s(**GATE_UP_512, n_max=10) == pytest.approx(
        966, abs=0.5
    )
    assert timing_process_time_limit_s(**O_1, n_max=10) == pytest.approx(21.5, abs=0.05)
    assert verification_process_time_limit_s(**O_1, draws=1) == pytest.approx(
        11, abs=0.05
    )


def test_the_smallest_inputs_give_just_over_eleven_seconds():
    assert verification_process_time_limit_s(1, 1, 1, 1) == float(
        11 + Fraction(1, 10**8)
    )
    assert timing_process_time_limit_s(1, 1, 1, 1) == float(12 + Fraction(2, 10**8))


@pytest.mark.parametrize("shape", [GATE_UP_512, O_1, {"m": 7, "k": 1, "n": 300}])
@pytest.mark.parametrize("n_max", [1, 5, 10, 16, 17, 1000])
def test_the_timing_run_counts_one_call_more_than_n_max(shape, n_max):
    assert timing_process_time_limit_s(
        **shape, n_max=n_max
    ) == verification_process_time_limit_s(**shape, draws=n_max + 1)


def test_the_cap_at_the_largest_work_of_the_record():
    assert verification_process_time_limit_s(**GATE_UP_512, draws=17) < 1500
    assert verification_process_time_limit_s(**GATE_UP_512, draws=18) == 1500.0
    assert timing_process_time_limit_s(**GATE_UP_512, n_max=16) < 1500
    assert timing_process_time_limit_s(**GATE_UP_512, n_max=17) == 1500.0


BIG = 2**53 - 1
HUGE = 2**4000


@pytest.mark.parametrize(
    ("args", "capped"),
    [
        ((1, 1, 1, 1), False),
        ((BIG, BIG, BIG, BIG), True),
        ((HUGE, HUGE, HUGE, HUGE), True),
        ((1, 1, 1, BIG), True),
        ((1, 1, 1, HUGE), True),
        ((BIG, 1, 1, 1), True),
        ((1, 1, HUGE, 1), True),
    ],
)
@pytest.mark.parametrize(("function", "_"), LIMIT_FUNCTIONS)
def test_the_rule_never_gives_a_value_the_functions_refuse(function, _, args, capped):
    value = function(*args)
    assert type(value) is float
    assert math.isfinite(value)
    assert 0 < value <= PROCESS_TIME_LIMIT_CAP_S
    assert value <= CLANG_BUILD_MAX_TIMEOUT_S
    assert (value == 1500.0) is capped


def test_the_build_limit_is_a_value_the_functions_accept():
    assert math.isfinite(BUILD_TIME_LIMIT_S)
    assert 0 < BUILD_TIME_LIMIT_S <= PROCESS_TIME_LIMIT_CAP_S
    assert BUILD_TIME_LIMIT_S <= CLANG_BUILD_MAX_TIMEOUT_S


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None, Fraction(1)])
@pytest.mark.parametrize("position", ["m", "k", "n", "count"])
@pytest.mark.parametrize(("function", "count_name"), LIMIT_FUNCTIONS)
def test_an_argument_that_is_not_an_int_is_refused(function, count_name, position, bad):
    args = {"m": 1, "k": 1, "n": 1, count_name: 1}
    name = count_name if position == "count" else position
    args[name] = bad
    with pytest.raises(TypeError, match=rf"^{name} must"):
        function(**args)


@pytest.mark.parametrize("bad", [0, -1, -(2**4000)])
@pytest.mark.parametrize("position", ["m", "k", "n", "count"])
@pytest.mark.parametrize(("function", "count_name"), LIMIT_FUNCTIONS)
def test_an_argument_below_one_is_refused(function, count_name, position, bad):
    args = {"m": 1, "k": 1, "n": 1, count_name: 1}
    name = count_name if position == "count" else position
    args[name] = bad
    with pytest.raises(ValueError, match=rf"^{name} must"):
        function(**args)


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
