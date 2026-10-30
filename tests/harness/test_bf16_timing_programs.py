import os
import re
import shutil
import signal
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import (
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    local_run,
    rmsnorm_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.harness.bf16_timing import KINDS, run_bf16_timing
from hilclaw.harness.bf16_timing_build import (
    PROGRAM_SOURCES,
    build_bf16_timing_executable,
)
from hilclaw.harness.bf16_verification_arrays import EPS_BITS, check_value, draw_inputs
from hilclaw.harness.measurement import State
from hilclaw.harness.timing import Broken

DIRECTORY = Path(hilclaw.harness.__file__).parent
HEADER = DIRECTORY / "bf16_timing.h"

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses of the programs (those of timing_driver.c).
COMMAND_LINE, MEMORY, SYSTEM, ZERO_INTERVAL = 2, 3, 4, 5

# kind: (contract, first operand, second operand, output, bytes of the second)
KINDS_OF = {
    "gemm": (gemm_bf16_contract, "a", "b", "c", "k * n"),
    "rmsnorm": (rmsnorm_bf16_contract, "x", "w", "y", "n"),
    "elementwise_add": (elementwise_add_bf16_contract, "a", "b", "c", "m * n"),
    "swiglu": (swiglu_bf16_contract, "gate", "up", "out", "m * n"),
}
DIMS = {
    "gemm": (3, 4, 5),
    "rmsnorm": (3, 5),
    "elementwise_add": (3, 5),
    "swiglu": (3, 5),
}

KERNEL = """\
#define _POSIX_C_SOURCE 200809L
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

static int calls;

static uint32_t crc(uint32_t value, const void *data, size_t bytes)
{
    const unsigned char *p = data;
    int bit;

    value = ~value;
    while (bytes-- > 0) {
        value ^= *p++;
        for (bit = 0; bit < 8; bit++)
            value = (value >> 1) ^ ((value & 1) != 0 ? UINT32_C(0xEDB88320) : 0);
    }
    return ~value;
}

@GLOBALS@
@PROTOTYPE@

@SIGNATURE@
{
    uint32_t check = crc(crc(0, @FIRST@, @FIRST_BYTES@ * 2), @SECOND@, @SECOND_BYTES@ * 2);
    size_t i;

    ++calls;
@BODY@
    printf("call @DIMS@ %08lx @EPS@\\n", @DIM_ARGS@, (unsigned long)check, @EPS_ARG@);
    fflush(stdout);
    for (i = 0; i < m * n; i++)
        @OUTPUT@[i] = 0;
}
"""

CLOCK = "int clock_gettime(clockid_t id, struct timespec *t)\n{\n    (void)id;\n"
FROZEN_CLOCK = CLOCK + "    t->tv_sec = 1;\n    t->tv_nsec = 0;\n    return 0;\n}\n"
FAILING_CLOCK = CLOCK + "    (void)t;\n    return -1;\n}\n"

# name: (file-scope text, text at the start of every call after the count)
STUBS = {
    "plain": ("", ""),
    "aborting": ("", "    if (calls == 3)\n        abort();\n"),
    "hanging": ("", "    while (calls > 0)\n        sleep(1);\n"),
    "frozen-clock": (FROZEN_CLOCK, ""),
    "failing-clock": (FAILING_CLOCK, ""),
}

CALL_LINE = re.compile(rb"call ([0-9 ]+) ([0-9a-f]{8}) ([0-9a-f]{8})")
INTERVAL = re.compile(rb"interval_ns [1-9][0-9]*\n")
REPORT = re.compile(
    rb"resolution_ns (0|[1-9][0-9]*)\n(interval_ns [1-9][0-9]*\n)+stop (converged|not_converged)\n"
)


def kernel_source(kind, name):
    contract, first, second, output, second_count = KINDS_OF[kind]
    file_scope, body = STUBS[name]
    gemm = kind == "gemm"
    rmsnorm = kind == "rmsnorm"
    eps = (
        "uint32_t e; memcpy(&e, &eps, sizeof e); return e;" if rmsnorm else "return 0;"
    )
    replacements = {
        "@GLOBALS@": file_scope
        + ("static unsigned long eps_bits(float eps)\n{\n    " if rmsnorm else "")
        + (eps + "\n}\n" if rmsnorm else ""),
        "@PROTOTYPE@": contract.PROTOTYPE,
        "@SIGNATURE@": contract.PROTOTYPE.removesuffix(";"),
        "@BODY@": body,
        "@FIRST@": first,
        "@SECOND@": second,
        "@FIRST_BYTES@": "(m * k)" if gemm else "(m * n)",
        "@SECOND_BYTES@": f"({second_count})",
        "@DIMS@": "%zu %zu %zu" if gemm else "%zu %zu",
        "@DIM_ARGS@": "m, k, n" if gemm else "m, n",
        "@EPS@": "%08lx",
        "@EPS_ARG@": "eps_bits(eps)" if rmsnorm else "0UL",
        "@OUTPUT@": output,
    }
    text = KERNEL
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a timing executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_timing")
    built = {}

    def build(kind, name="plain", optimisation="-O2"):
        key = (kind, name, optimisation)
        if key not in built:
            stem = f"{kind}-{name}{optimisation}"
            source = directory / f"{stem}.c"
            source.write_text(kernel_source(kind, name), encoding="ascii", newline="\n")
            output = directory / stem
            result = build_bf16_timing_executable(
                kind,
                source,
                output,
                timeout_s=BUILD_TIMEOUT,
                flags=(*STRICT, optimisation),
            )
            assert result.ok, result.log
            built[key] = output
        return built[key]

    return build


def arguments(kind, *, n_min="5", n_max="10", cv_max="0.05", form="interval", seed="7"):
    return (*map(str, DIMS[kind]), n_min, n_max, cv_max, form, seed)


def started(path, *argv, timeout_s=RUN_TIMEOUT):
    return local_run.run((path, *argv), timeout_s=timeout_s)


def calls_of(stderr):
    return [
        CALL_LINE.fullmatch(line)
        for line in stderr.splitlines()
        if line.startswith(b"call ")
    ]


def expected_check(kind, dims, seed):
    return check_value(*draw_inputs(kind, dims, seed=seed, draw=0))


@pytest.mark.parametrize("kind", KINDS)
def test_each_program_declares_its_prototype_byte_for_byte_and_calls_it_once(kind):
    contract = KINDS_OF[kind][0]
    text = PROGRAM_SOURCES[kind].read_text(encoding="ascii")
    verification = (DIRECTORY / f"bf16_verification_{kind}.c").read_text(
        encoding="ascii"
    )
    assert contract.PROTOTYPE + "\n" in text
    assert contract.PROTOTYPE + "\n" in verification
    symbol = f"hilclaw_{kind}_bf16"
    assert text.count(symbol) == 2
    assert f"static kernel_function *volatile kernel = {symbol};" in text
    assert text.count("call(") == 1
    assert '#include "bf16_timing.h"' in text
    assert "<math.h>" not in text
    for other in KINDS:
        if other != kind:
            assert f"hilclaw_{other}_bf16" not in text


def test_the_header_includes_the_verification_header_and_no_math():
    text = HEADER.read_text(encoding="ascii")
    assert '#include "bf16_verification.h"' in text
    assert "<math.h>" not in text
    assert "CLOCK_MONOTONIC" in text


def test_rmsnorm_compiles_in_the_contracts_eps():
    text = PROGRAM_SOURCES["rmsnorm"].read_text(encoding="ascii")
    assert f"UINT32_C(0x{EPS_BITS:08X})" in text


@pytest.mark.parametrize("optimisation", ["-O0", "-O2"])
@pytest.mark.parametrize("sample_form", ["interval", "reciprocal"])
@pytest.mark.parametrize("seed", [0, 7, 2**64 - 1])
@pytest.mark.parametrize("kind", KINDS)
def test_a_run_is_judged_and_the_kernel_gets_the_verification_draw(
    executable, kind, seed, sample_form, optimisation
):
    dims = DIMS[kind]
    result = run_bf16_timing(
        executable(kind, optimisation=optimisation),
        kind,
        dims,
        sample_form=sample_form,
        seed=seed,
        timeout_s=RUN_TIMEOUT,
    )
    assert result.broken is None, result.run
    assert result.state in (State.CONVERGED, State.NOT_CONVERGED)
    assert REPORT.fullmatch(result.run.stdout)
    assert b"call" not in result.run.stdout
    calls = calls_of(result.run.stderr)
    assert len(calls) == 1 + len(result.intervals_ns)
    assert len(INTERVAL.findall(result.run.stdout)) == len(result.intervals_ns)
    wanted = f"{expected_check(kind, dims, seed):08x}".encode()
    eps = f"{EPS_BITS if kind == 'rmsnorm' else 0:08x}".encode()
    for call in calls:
        assert call is not None
        assert call.group(1) == " ".join(map(str, dims)).encode()
        assert call.group(2) == wanted
        assert call.group(3) == eps


@pytest.mark.parametrize("kind", KINDS)
def test_different_seeds_draw_different_inputs(executable, kind):
    path = executable(kind)
    seen = set()
    for seed in ("1", "2"):
        run = started(path, *arguments(kind, seed=seed))
        assert run.returncode == 0
        seen.add(calls_of(run.stderr)[0].group(2))
    assert len(seen) == 2


FORCED = [
    ("2", "7", "1e9", "converged", 2),
    ("4", "6", "1e9", "converged", 4),
    ("3", "3", "1e9", "converged", 3),
    ("3", "4", "1e-300", "not_converged", 4),
    ("2", "2", "1e-300", "not_converged", 2),
]


@pytest.mark.parametrize("n_min, n_max, cv_max, stop, count", FORCED)
@pytest.mark.parametrize("kind", KINDS)
def test_the_loop_stops_where_the_rule_says(
    executable, kind, n_min, n_max, cv_max, stop, count
):
    run = started(
        executable(kind), *arguments(kind, n_min=n_min, n_max=n_max, cv_max=cv_max)
    )
    assert run.returncode == 0, run.stderr
    lines = run.stdout.decode("ascii").splitlines()
    assert lines[0].startswith("resolution_ns ")
    assert len(lines) == count + 2
    assert lines[-1] == f"stop {stop}"
    assert len(calls_of(run.stderr)) == count + 1


@pytest.mark.parametrize("kind", KINDS)
def test_an_aborting_kernel_is_an_exit_status(executable, kind):
    result = run_bf16_timing(
        executable(kind, "aborting"),
        kind,
        DIMS[kind],
        sample_form="interval",
        seed=7,
        timeout_s=RUN_TIMEOUT,
    )
    assert result.broken is Broken.EXIT_STATUS
    assert result.run.returncode == -signal.SIGABRT
    assert result.run.stdout.count(b"interval_ns") == 1


@pytest.mark.parametrize("kind", KINDS)
def test_a_hanging_kernel_is_a_timeout(executable, kind):
    result = run_bf16_timing(
        executable(kind, "hanging"),
        kind,
        DIMS[kind],
        sample_form="interval",
        seed=7,
        timeout_s=2,
    )
    assert result.broken is Broken.TIMEOUT
    assert result.run.timed_out is True


@pytest.mark.parametrize("kind", KINDS)
def test_a_zero_interval_ends_with_its_status(executable, kind):
    run = started(executable(kind, "frozen-clock"), *arguments(kind))
    assert run.returncode == ZERO_INTERVAL
    assert run.stdout.endswith(b"interval_ns 0\n")
    assert b"stop" not in run.stdout
    assert f"bf16_timing_{kind}: interval:".encode() in run.stderr
    result = run_bf16_timing(
        executable(kind, "frozen-clock"),
        kind,
        DIMS[kind],
        sample_form="interval",
        seed=7,
        timeout_s=RUN_TIMEOUT,
    )
    assert result.broken is Broken.EXIT_STATUS


@pytest.mark.parametrize("kind", KINDS)
def test_a_failing_clock_is_a_system_status(executable, kind):
    run = started(executable(kind, "failing-clock"), *arguments(kind))
    assert run.returncode == SYSTEM
    assert b"stop" not in run.stdout
    assert f"bf16_timing_{kind}: clock_gettime:".encode() in run.stderr


def bad_values(kind):
    names = ["m", "k", "n"] if kind == "gemm" else ["m", "n"]
    values = [
        (name, value) for name in names for value in ["0", "01", "-1", "+1", "1x", ""]
    ]
    values += [("n_min", value) for value in ["1", "05", "-5"]]
    values += [("n_max", value) for value in ["4", "010", "1e1"]]
    values += [("cv_max", value) for value in ["0", "-0.05", "nan", "inf", "0.05x", ""]]
    values += [("sample_form", value) for value in ["time", "Interval", ""]]
    values += [("seed", value) for value in ["18446744073709551616", "07", "-1"]]
    return values


BAD = [(kind, name, value) for kind in KINDS for name, value in bad_values(kind)]


@pytest.mark.parametrize(
    "kind, name, value", BAD, ids=[f"{k}-{n}-{i}" for i, (k, n, _) in enumerate(BAD)]
)
def test_a_bad_spelling_is_a_command_line_status(executable, kind, name, value):
    names = (["m", "k", "n"] if kind == "gemm" else ["m", "n"]) + [
        "n_min",
        "n_max",
        "cv_max",
        "sample_form",
        "seed",
    ]
    argv = list(arguments(kind))
    argv[names.index(name)] = value
    run = started(executable(kind), *argv)
    assert run.returncode == COMMAND_LINE
    assert run.stdout == b""
    assert f"bf16_timing_{kind}: {name}:".encode() in run.stderr
    assert not calls_of(run.stderr)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("change", ["none", "one-less", "one-more"])
def test_a_wrong_argument_count_is_a_command_line_status(executable, kind, change):
    argv = list(arguments(kind))
    argv = {"none": [], "one-less": argv[:-1], "one-more": [*argv, "7"]}[change]
    run = started(executable(kind), *argv)
    assert run.returncode == COMMAND_LINE
    assert run.stdout == b""
    assert f"bf16_timing_{kind}: usage:".encode() in run.stderr


TOO_LARGE = {
    "gemm": [(2**40, 2**40, 2**40), (2**62, 1, 1)],
    "rmsnorm": [(2**40, 2**40), (2**62, 1)],
    "elementwise_add": [(2**40, 2**40), (2**62, 1)],
    "swiglu": [(2**40, 2**40), (2**62, 1)],
}


@pytest.mark.parametrize("kind", KINDS)
def test_dimensions_that_cannot_be_held_are_a_memory_status(executable, kind):
    for dims in TOO_LARGE[kind]:
        argv = (*map(str, dims), *arguments(kind)[len(dims) :])
        run = started(executable(kind), *argv)
        assert run.returncode == MEMORY
        assert run.stdout == b""
        assert not calls_of(run.stderr)


@pytest.mark.parametrize("kind", KINDS)
def test_samples_that_cannot_be_held_are_a_memory_status(executable, kind):
    run = started(executable(kind), *arguments(kind, n_max=str(2**61)))
    assert run.returncode == MEMORY
    assert run.stdout == b""
    assert not calls_of(run.stderr)
