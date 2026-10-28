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
    BF16_CHECK_KINDS,
    BUILD_TIME_LIMIT_S,
    ENV,
    FLAGS,
    PROCESS_TIME_LIMIT_CAP_S,
    TRAILING_FLAGS,
    bf16_verification_process_time_limit_s,
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
        "BF16_CHECK_KINDS",
        "BF16_ELEMENT_WEIGHT",
        "bf16_verification_process_time_limit_s",
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


# The bf16 verification processes (ADR-0179)

BF16_LARGEST = {
    "gemm": (512, 2048, 128256),
    "rmsnorm": (512, 2048),
    "elementwise_add": (512, 2048),
    "swiglu": (512, 8192),
    "rope": (2048, 32, 64),
    "sdpa_kv_cache": (2048, 2048, 32, 8, 64),
}


def bf16_work(kind, dims):
    if kind == "gemm":
        m, k, n = dims
        return 2 * m * k * n + 10 * (m * k + k * n + m * n)
    if kind == "sdpa_kv_cache":
        m, l, h, h_kv, d = dims
        arrays = 2 * m * h * d + 2 * m * h_kv * d + 2 * (l + 2 * m) * h_kv * d
        return 4 * m * l * h * d + 10 * arrays
    if kind == "rope":
        m, h, d = dims
        return 10 * (2 * m * h * d + 2 * m * d)
    m, n = dims
    return 10 * ((2 * m * n + n) if kind == "rmsnorm" else 3 * m * n)


def bf16_expected(kind, dims, draws):
    rule = 10 + draws * (1 + Fraction(bf16_work(kind, dims), 2 * 10**8))
    return float(min(rule, Fraction(1500)))


def test_the_bf16_constants_are_those_of_the_record():
    assert BF16_CHECK_KINDS == (
        "gemm",
        "rmsnorm",
        "elementwise_add",
        "swiglu",
        "rope",
        "sdpa_kv_cache",
    )
    assert type(standin_settings.BF16_ELEMENT_WEIGHT) is int
    assert standin_settings.BF16_ELEMENT_WEIGHT == 10


def bf16_shapes():
    from hilclaw import contract_table

    for key, found in contract_table.TABLE.items():
        if key[0] in BF16_CHECK_KINDS and key[1] == "bf16":
            for dims in found.contract.SHAPES:
                yield key[0], tuple(dims)


@pytest.mark.parametrize(("kind", "dims"), list(bf16_shapes()))
@pytest.mark.parametrize("draws", [1, 2, 8, 9, 100])
def test_the_bf16_rule_is_exact_at_every_shape_of_the_contracts(kind, dims, draws):
    value = bf16_verification_process_time_limit_s(kind, dims, draws)
    assert type(value) is float
    assert value == bf16_expected(kind, dims, draws)
    assert 0 < value <= PROCESS_TIME_LIMIT_CAP_S


def test_the_bf16_figures_of_the_record():
    limit = bf16_verification_process_time_limit_s
    assert limit("gemm", (512, 2048, 128256), 1) == pytest.approx(1372.3, abs=0.05)
    assert limit("gemm", (512, 2048, 128256), 2) == 1500.0
    assert limit("gemm", (1, 2048, 128256), 1) == pytest.approx(26.8, abs=0.05)
    assert limit("gemm", (512, 2048, 8192), 1) == pytest.approx(98.0, abs=0.05)
    assert limit("sdpa_kv_cache", (2048, 2048, 32, 8, 64), 1) == pytest.approx(
        183.6, abs=0.05
    )
    assert limit("swiglu", (512, 8192), 1) == pytest.approx(11.6, abs=0.05)
    assert limit("rmsnorm", (1, 2048), 1) == pytest.approx(11.0, abs=0.05)


@pytest.mark.parametrize(
    ("kind", "under", "capped"),
    [
        ("gemm", 1, 2),
        ("sdpa_kv_cache", 8, 9),
        ("swiglu", 914, 915),
        ("rmsnorm", 1348, 1349),
        ("elementwise_add", 1287, 1288),
        ("rope", 1040, 1041),
    ],
)
def test_the_largest_shape_of_each_kind_reaches_the_cap(kind, under, capped):
    dims = BF16_LARGEST[kind]
    assert bf16_verification_process_time_limit_s(kind, dims, under) < 1500
    assert bf16_verification_process_time_limit_s(kind, dims, capped) == 1500.0


@pytest.mark.parametrize(
    ("dims", "per_draw", "under"),
    [
        ((2048, 32, 64), 1.433, 1040),
        ((2048, 8, 64), 1.118, 1332),
        ((128, 32, 64), 1.027, 1450),
        ((1, 32, 64), 1.000, 1489),
    ],
)
def test_the_rope_figures_of_adr_0180(dims, per_draw, under):
    limit = bf16_verification_process_time_limit_s
    assert limit("rope", dims, 1) - 10 == pytest.approx(per_draw, abs=0.0005)
    assert limit("rope", dims, 1) == pytest.approx(10 + per_draw, abs=0.0005)
    assert limit("rope", dims, under) < 1500
    assert limit("rope", dims, under + 1) == 1500.0


def test_the_rope_measure_has_no_operation_term():
    m, h, d = 3, 5, 8
    elements = 2 * m * h * d + 2 * m * d
    value = bf16_verification_process_time_limit_s("rope", (m, h, d), 7)
    assert value == float(10 + 7 * (1 + Fraction(10 * elements, 2 * 10**8)))


@pytest.mark.parametrize(
    ("dims", "error", "match"),
    [
        ((0, 1, 2), ValueError, "^m must be at least 1"),
        ((1, True, 2), TypeError, "^h must be an int"),
        ((1, 1, 2.0), TypeError, "^d must be an int"),
        ([1, 1, 2], TypeError, "^dims must be a tuple"),
    ],
)
def test_rope_dims_the_bf16_rule_refuses(dims, error, match):
    with pytest.raises(error, match=match):
        bf16_verification_process_time_limit_s("rope", dims, 1)


def test_the_build_limit_is_unchanged_for_rope():
    assert standin_settings.BUILD_TIME_LIMIT_S == 60


def test_the_bf16_gemm_measure_adds_the_element_term_to_the_fp32_one():
    fp32 = verification_process_time_limit_s(32, 2048, 8192, 3)
    bf16 = bf16_verification_process_time_limit_s("gemm", (32, 2048, 8192), 3)
    elements = 32 * 2048 + 2048 * 8192 + 32 * 8192
    assert bf16 - fp32 == pytest.approx(3 * 10 * elements / 2e8)


@pytest.mark.parametrize(
    ("kind", "dims"),
    [
        ("gemm", (HUGE, HUGE, HUGE)),
        ("sdpa_kv_cache", (HUGE, HUGE, HUGE, HUGE, HUGE)),
        ("swiglu", (BIG, BIG)),
    ],
)
def test_the_bf16_rule_never_gives_a_value_the_functions_refuse(kind, dims):
    value = bf16_verification_process_time_limit_s(kind, dims, HUGE)
    assert value == 1500.0
    assert value <= CLANG_BUILD_MAX_TIMEOUT_S


@pytest.mark.parametrize("kind", ["conv", "GEMM", "", None, b"gemm", 1])
def test_a_kind_the_bf16_rule_does_not_serve_is_refused(kind):
    with pytest.raises(ValueError, match="^kind must be one of"):
        bf16_verification_process_time_limit_s(kind, (1, 1), 1)


@pytest.mark.parametrize("dims", [[1, 1, 1], None, (1, 1, 1).__iter__(), "111"])
def test_dims_that_are_no_tuple_are_refused(dims):
    with pytest.raises(TypeError, match="^dims must be a tuple"):
        bf16_verification_process_time_limit_s("gemm", dims, 1)


@pytest.mark.parametrize(
    ("kind", "dims"),
    [
        ("gemm", (1, 1)),
        ("rmsnorm", (1, 1, 1)),
        ("sdpa_kv_cache", (1, 1, 1, 1)),
        ("swiglu", ()),
        ("rope", (1, 1)),
        ("rope", (1, 1, 2, 1)),
    ],
)
def test_dims_of_another_length_are_refused(kind, dims):
    with pytest.raises(ValueError, match=f"^dims of {kind} must be"):
        bf16_verification_process_time_limit_s(kind, dims, 1)


@pytest.mark.parametrize("bad", [True, 1.0, "1", None])
def test_a_bf16_dimension_or_draws_that_is_not_an_int_is_refused(bad):
    with pytest.raises(TypeError, match="^l must be an int"):
        bf16_verification_process_time_limit_s("sdpa_kv_cache", (1, bad, 1, 1, 1), 1)
    with pytest.raises(TypeError, match="^draws must be an int"):
        bf16_verification_process_time_limit_s("rmsnorm", (1, 1), bad)


@pytest.mark.parametrize("bad", [0, -1])
def test_a_bf16_dimension_or_draws_below_one_is_refused(bad):
    with pytest.raises(ValueError, match="^k must be at least 1"):
        bf16_verification_process_time_limit_s("gemm", (1, bad, 1), 1)
    with pytest.raises(ValueError, match="^draws must be at least 1"):
        bf16_verification_process_time_limit_s("swiglu", (1, 1), bad)


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
