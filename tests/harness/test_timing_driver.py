import os
import re
import shutil
import signal
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import clang_build, local_run
from hilclaw.harness import timing
from hilclaw.harness.measurement import N_MAX_DEFAULT, N_MIN, State
from hilclaw.harness.timing import Broken

DRIVER = Path(hilclaw.harness.__file__).parent / "timing_driver.c"

# ADR-0008 decision 4, byte for byte.
PROTOTYPE = (
    "void hilclaw_gemm(size_t m, size_t k, size_t n, "
    "const float *restrict a, const float *restrict b, float *restrict c);"
)

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses of the driver program.
COMMAND_LINE, MEMORY, SYSTEM, ZERO_INTERVAL = 2, 3, 4, 5

SHAPE = {"m": 48, "k": 80, "n": 32}

KERNEL = """\
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

@GLOBALS@
@SIGNATURE@
{
@BODY@
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""

CALLS = "static int calls;"

CHECKING = """\
    size_t negative = 0, positive = 0;
    if (m != @M@ || k != @K@ || n != @N@)
        abort();
    for (size_t i = 0; i < m * k + k * n; i++) {
        float x = i < m * k ? a[i] : b[i - m * k];
        if (x >= 0.5f && x < 1.0f)
            positive++;
        else if (x <= -0.5f && x > -1.0f)
            negative++;
        else
            abort();
    }
    if (negative == 0 || positive == 0)
        abort();
"""

CHECKSUM = """\
    if (++calls == 1) {
        uint64_t sum = UINT64_C(1469598103934665603);
        for (size_t i = 0; i < m * k + k * n; i++) {
            uint32_t bits;
            memcpy(&bits, i < m * k ? &a[i] : &b[i - m * k], sizeof bits);
            sum = (sum ^ bits) * UINT64_C(1099511628211);
        }
        fprintf(stderr, "checksum %llu\\n", (unsigned long long)sum);
    }
"""

SLEEPING = """\
    struct timespec pause = {.tv_sec = 0, .tv_nsec = 100000000L};
    nanosleep(&pause, NULL);
"""

ALTERNATING = """\
    struct timespec pause = {.tv_sec = 0, .tv_nsec = ++calls % 2 ? 5000000L : 40000000L};
    nanosleep(&pause, NULL);
"""

CLOCK = "int clock_gettime(clockid_t id, struct timespec *t)\n{\n    (void)id;\n"
FROZEN_CLOCK = CLOCK + "    t->tv_sec = 1;\n    t->tv_nsec = 0;\n    return 0;\n}\n"
FAILING_CLOCK = CLOCK + "    (void)t;\n    return -1;\n}\n"
BACKWARD_CLOCK = (
    CLOCK
    + "    static long ticks = 1000;\n"
    + "    t->tv_sec = 0;\n    t->tv_nsec = ticks--;\n    return 0;\n}\n"
)

# name: (file-scope text, text at the start of every call)
KERNELS = {
    "plain": ("", ""),
    "counting": ("", '    fputs("call\\n", stderr);\n'),
    "printing": ("", '    puts("kernel says hello");\n'),
    "checking": ("", CHECKING),
    "checksum": (CALLS, CHECKSUM),
    "sleeping": ("", SLEEPING),
    "alternating": (CALLS, ALTERNATING),
    "hanging": (CALLS, "    while (++calls > 0)\n        sleep(1);\n"),
    "aborting": (CALLS, "    if (++calls == 3)\n        abort();\n"),
    "frozen-clock": (FROZEN_CLOCK, ""),
    "failing-clock": (FAILING_CLOCK, ""),
    "backward-clock": (BACKWARD_CLOCK, ""),
}

GOOD = ("64", "64", "64", "5", "10", "0.05", "interval", "7")
ARGUMENT = {
    name: position
    for position, name in enumerate(
        ("m", "k", "n", "n_min", "n_max", "cv_max", "sample_form", "seed")
    )
}

BAD_VALUES = (
    [(name, value) for name in "mkn" for value in ["0", "", "-1", "+1", "1x", " 1"]]
    + [(name, value) for name in "mkn" for value in ["1 ", "01", "00", "1" * 30]]
    + [("n_min", value) for value in ["0", "1", "", "-5", "05", "5.0", "1" * 30]]
    + [("n_max", value) for value in ["4", "0", "", "-10", "010", "1e1", "1" * 30]]
    + [("seed", value) for value in ["18446744073709551616", "", "-1", "+7", "07"]]
    + [("seed", value) for value in ["0x7", "7 ", "1" * 30]]
    + [("cv_max", value) for value in ["x", "0", "0.0", "-0.05", "nan", "inf"]]
    + [("cv_max", value) for value in ["-inf", "0.05x", "0.05 ", "", "1e999"]]
    + [("sample_form", value) for value in ["time", "", "Interval", "interval "]]
    + [("sample_form", value) for value in ["intervals", "reciprocal,interval"]]
)
BAD_VALUE_IDS = [
    f"{name}-{position}" for position, (name, value) in enumerate(BAD_VALUES)
]

BAD_COUNTS = {
    "none": (),
    "one": GOOD[:1],
    "seven": GOOD[:7],
    "nine": (*GOOD, "7"),
    "sixteen": GOOD * 2,
}

# m, k, n and n_max that pass the command line and cannot be held or allocated.
TOO_LARGE = {
    "product-overflows": {"m": 2**40, "k": 2**40, "n": 2**40},
    "bytes-overflow": {"m": 2**62, "k": 1, "n": 1},
    "output-overflows": {"m": 2**32, "k": 1, "n": 2**32},
    "not-allocatable": {"m": 2**30, "k": 2**30, "n": 2**30},
    "samples-overflow": {"m": 1, "k": 1, "n": 1, "n_max": 2**61},
    "samples-not-allocatable": {"m": 1, "k": 1, "n": 1, "n_max": 2**59},
}

# (n_min, n_max, cv_max): 1e9 is a bound no spread reaches; the square of 1e-300 is 0.0,
# which no spread is below.
FORCED = [
    ("2", "7", "1e9", State.CONVERGED, 2),
    ("4", "6", "1e9", State.CONVERGED, 4),
    ("3", "3", "1e9", State.CONVERGED, 3),
    ("3", "4", "1e-300", State.NOT_CONVERGED, 4),
    ("2", "2", "1e-300", State.NOT_CONVERGED, 2),
]

RESOLUTION_LINE = rb"resolution_ns (0|[1-9][0-9]*)\n"
INTERVAL_LINE = rb"interval_ns [1-9][0-9]*\n"
REPORT = (
    RESOLUTION_LINE + rb"(%s){5,10}stop (converged|not_converged)\n" % INTERVAL_LINE
)


def kernel_source(name):
    file_scope, body = KERNELS[name]
    text = KERNEL.replace("@GLOBALS@", file_scope).replace("@BODY@", body)
    text = text.replace("@SIGNATURE@", PROTOTYPE.removesuffix(";"))
    for dimension, value in SHAPE.items():
        text = text.replace(f"@{dimension.upper()}@", str(value))
    return text


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a timing executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("timing_driver")
    built = {}

    def build(name, optimisation="-O2"):
        if (name, optimisation) not in built:
            source = directory / f"{name}.c"
            source.write_text(kernel_source(name), encoding="ascii", newline="\n")
            output = directory / f"{name}{optimisation}"
            result = clang_build.build(
                (DRIVER, source),
                output,
                timeout_s=BUILD_TIMEOUT,
                flags=(*STRICT, optimisation),
            )
            assert result.ok, result.log
            built[name, optimisation] = output
        return built[name, optimisation]

    return build


def timed(path, **parameters):
    settings = {"m": 64, "k": 64, "n": 64, "sample_form": "interval", "seed": 7}
    settings["timeout_s"] = RUN_TIMEOUT
    return timing.run_timing(path, **(settings | parameters))


def assert_completed(result, n_max=N_MAX_DEFAULT):
    assert result.broken is None, result.run
    assert result.run.returncode == 0
    assert result.state in (State.CONVERGED, State.NOT_CONVERGED)
    assert N_MIN <= len(result.intervals_ns) <= n_max
    if result.state is State.NOT_CONVERGED:
        assert len(result.intervals_ns) == n_max
    assert all(type(value) is int and value > 0 for value in result.intervals_ns)
    assert type(result.resolution_ns) is int


def assert_refused(run, status):
    assert run.timed_out is False
    assert run.returncode == status, run
    assert run.stdout == b""
    assert run.stderr.startswith(b"timing_driver: ")
    assert run.stderr.endswith(b"\n")
    assert run.stderr.count(b"\n") == 1


def test_driver_source_is_ascii_and_declares_the_contract_prototype():
    text = DRIVER.read_bytes().decode("ascii")
    assert PROTOTYPE in text.splitlines()


@pytest.mark.parametrize("optimisation", ["-O0", "-O2"])
@pytest.mark.parametrize("sample_form", timing.SAMPLE_FORMS)
def test_plain_kernel_builds_strictly_and_completes(
    executable, optimisation, sample_form
):
    path = executable("plain", optimisation)
    result = timed(path, sample_form=sample_form)
    assert_completed(result)
    assert re.fullmatch(REPORT, result.run.stdout)
    assert result.run.command[0] == str(path)


def test_one_untimed_call_and_one_call_per_repeat(executable):
    result = timed(executable("counting"))
    assert_completed(result)
    assert result.run.stderr.count(b"call\n") == len(result.intervals_ns) + 1


def test_kernel_output_arrives_on_standard_error(executable):
    result = timed(executable("printing"))
    assert_completed(result)
    assert b"kernel says hello\n" in result.run.stderr


@pytest.mark.parametrize("seed", [0, 1, 7, 2**63, 2**64 - 1])
def test_non_square_arguments_and_operands_are_as_the_contract_says(executable, seed):
    result = timed(executable("checking"), **SHAPE, seed=seed)
    assert_completed(result)


def test_operands_depend_on_the_seed_only(executable):
    def checksum(seed):
        result = timed(executable("checksum"), m=30, k=50, n=70, seed=seed)
        assert_completed(result)
        (value,) = re.findall(rb"checksum ([0-9]+)\n", result.run.stderr)
        return value

    assert checksum(7) == checksum(7)
    assert len({checksum(seed) for seed in (0, 7, 8, 2**64 - 1)}) == 4


@pytest.mark.parametrize("sample_form", timing.SAMPLE_FORMS)
def test_steady_kernel_converges(executable, sample_form):
    result = timed(executable("sleeping"), sample_form=sample_form, n_max=20)
    assert_completed(result, n_max=20)
    assert result.state is State.CONVERGED
    assert min(result.intervals_ns) >= 100_000_000


@pytest.mark.parametrize("n_max", [N_MIN, 7])
def test_unsteady_kernel_stops_at_n_max(executable, n_max):
    result = timed(executable("alternating"), n_max=n_max)
    assert_completed(result, n_max=n_max)
    assert result.state is State.NOT_CONVERGED
    assert len(result.intervals_ns) == n_max
    assert min(result.intervals_ns[0::2]) > max(result.intervals_ns[1::2])


@pytest.mark.parametrize("sample_form", timing.SAMPLE_FORMS)
@pytest.mark.parametrize(("n_min", "n_max", "cv_max", "state", "count"), FORCED)
def test_driver_takes_the_policy_from_its_arguments(
    executable, n_min, n_max, cv_max, state, count, sample_form
):
    arguments = ("64", "64", "64", n_min, n_max, cv_max, sample_form, "7")
    run = local_run.run((executable("plain"), *arguments), timeout_s=RUN_TIMEOUT)
    assert run.returncode == 0, run
    report = timing.parse_report(run.stdout)
    assert report is not None, run.stdout
    assert report.state is state
    assert len(report.intervals_ns) == count


def test_kernel_that_never_returns_leaves_the_resolution_line(executable):
    result = timed(executable("hanging"), timeout_s=2)
    assert result.broken is Broken.TIMEOUT
    assert re.fullmatch(RESOLUTION_LINE, result.run.stdout)


def test_kernel_that_aborts_leaves_the_lines_taken_so_far(executable):
    result = timed(executable("aborting"))
    assert result.broken is Broken.EXIT_STATUS
    assert result.run.returncode == -signal.SIGABRT
    assert re.fullmatch(RESOLUTION_LINE + INTERVAL_LINE, result.run.stdout)


def test_interval_of_zero_is_reported_and_ends_the_run(executable):
    result = timed(executable("frozen-clock"))
    assert result.broken is Broken.EXIT_STATUS
    assert result.run.returncode == ZERO_INTERVAL
    assert re.fullmatch(RESOLUTION_LINE + rb"interval_ns 0\n", result.run.stdout)
    assert result.run.stderr.startswith(b"timing_driver: ")


@pytest.mark.parametrize("name", ["failing-clock", "backward-clock"])
def test_clock_that_cannot_be_read_ends_the_run(executable, name):
    result = timed(executable(name))
    assert result.broken is Broken.EXIT_STATUS
    assert result.run.returncode == SYSTEM
    assert re.fullmatch(RESOLUTION_LINE, result.run.stdout)
    assert result.run.stderr.startswith(b"timing_driver: ")


@pytest.mark.parametrize("sizes", TOO_LARGE.values(), ids=TOO_LARGE.keys())
def test_arrays_that_cannot_be_held_are_refused(executable, sizes):
    result = timed(executable("plain"), **sizes)
    assert result.broken is Broken.EXIT_STATUS
    assert_refused(result.run, MEMORY)


@pytest.mark.parametrize("arguments", BAD_COUNTS.values(), ids=BAD_COUNTS.keys())
def test_wrong_number_of_arguments_is_refused(executable, arguments):
    run = local_run.run((executable("plain"), *arguments), timeout_s=RUN_TIMEOUT)
    assert_refused(run, COMMAND_LINE)


@pytest.mark.parametrize(("name", "value"), BAD_VALUES, ids=BAD_VALUE_IDS)
def test_malformed_argument_is_refused(executable, name, value):
    arguments = list(GOOD)
    arguments[ARGUMENT[name]] = value
    run = local_run.run((executable("plain"), *arguments), timeout_s=RUN_TIMEOUT)
    assert_refused(run, COMMAND_LINE)


def test_good_command_line_of_the_refusal_tests_is_accepted(executable):
    run = local_run.run((executable("plain"), *GOOD), timeout_s=RUN_TIMEOUT)
    assert run.returncode == 0, run
    assert timing.parse_report(run.stdout) is not None
