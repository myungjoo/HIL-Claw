import os
import re
import shutil
import signal
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
import pytest

import hilclaw.harness
from hilclaw import local_run, rope_bf16_contract, sdpa_kv_cache_bf16_contract
from hilclaw.harness import bf16_rope_arrays, bf16_sdpa_kv_cache_arrays
from hilclaw.harness.bf16_timing import run_bf16_timing
from hilclaw.harness.bf16_timing_build import (
    PROGRAM_SOURCES,
    build_bf16_timing_executable,
)
from hilclaw.harness.measurement import State
from hilclaw.harness.timing import Broken

DIRECTORY = Path(hilclaw.harness.__file__).parent

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

COMMAND_LINE, MEMORY, SYSTEM, ZERO_INTERVAL, INPUT = 2, 3, 4, 5, 6

KINDS = ("rope", "sdpa_kv_cache")
CONTRACTS = {"rope": rope_bf16_contract, "sdpa_kv_cache": sdpa_kv_cache_bf16_contract}
DIMS = {"rope": (3, 2, 4), "sdpa_kv_cache": (2, 5, 4, 2, 3)}
NAMES = {"rope": ["m", "h", "d"], "sdpa_kv_cache": ["m", "l", "h", "h_kv", "d"]}
TIMING_NAMES = ["n_min", "n_max", "cv_max", "sample_form", "seed"]

PRELUDE = """\
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

"""

CLOCK = "int clock_gettime(clockid_t id, struct timespec *t)\n{\n    (void)id;\n"
SCOPES = {
    "plain": ("", ""),
    "aborting": ("", "    if (calls == 3)\n        abort();\n"),
    "hanging": ("", "    while (calls > 0)\n        sleep(1);\n"),
    "frozen-clock": (
        CLOCK + "    t->tv_sec = 1;\n    t->tv_nsec = 0;\n    return 0;\n}\n",
        "",
    ),
    "failing-clock": (CLOCK + "    (void)t;\n    return -1;\n}\n", ""),
}

# The stub also changes a row, which the contract forbids, to show that the
# program puts nothing back in the rows between repeats.
ROPE_BODY = """\
    uint32_t check = crc(crc(0, x, m * h * d * 2), freqs_cis, m * d * 4);
    size_t i;

    printf("call %zu %zu %zu %08lx\\n", m, h, d, (unsigned long)check);
    fflush(stdout);
    if (calls == 1)
        *(float *)(uintptr_t)freqs_cis = -*freqs_cis;
    for (i = 0; i < m * h * d; i++)
        out[i] = 0;
"""

# Rows P .. l - 1 hold, from the second call on, the number of the call before.
SDPA_BODY = """\
    size_t row = h_kv * d, cached = (l - m) * row, i;
    uint32_t inputs = crc(crc(crc(0, q, m * h * d * 2), k_new, m * row * 2), v_new, m * row * 2);
    uint32_t rows = crc(crc(0, cache_k, cached * 2), cache_v, cached * 2);
    int kept = 1;

    if (calls > 1)
        for (i = cached; i < l * row; i++)
            kept = kept && cache_k[i] == (uint16_t)(calls - 1) && cache_v[i] == (uint16_t)(calls - 1);
    printf("call %zu %zu %zu %zu %zu %08lx %08lx %d\\n", m, l, h, h_kv, d, (unsigned long)inputs,
           (unsigned long)rows, kept);
    fflush(stdout);
    for (i = cached; i < l * row; i++) {
        cache_k[i] = (uint16_t)calls;
        cache_v[i] = (uint16_t)calls;
    }
    for (i = 0; i < m * h * d; i++)
        out[i] = 0;
"""

# Linked with --wrap=malloc: reports whether the pointer the kernel gets is the
# start of one allocation of exactly l rows.
ALLOCATIONS = """\
void *__real_malloc(size_t bytes);
void *__wrap_malloc(size_t bytes);

static void *starts[32];
static size_t sizes[32];
static int allocated;

void *__wrap_malloc(size_t bytes)
{
    void *pointer = __real_malloc(bytes);

    if (allocated < 32) {
        starts[allocated] = pointer;
        sizes[allocated++] = bytes;
    }
    return pointer;
}

static size_t allocation_of(const void *pointer)
{
    int i;

    for (i = 0; i < allocated; i++)
        if (starts[i] == pointer)
            return sizes[i];
    return 0;
}
"""
ALLOCATIONS_BODY = """\
    printf("allocated %zu %zu\\n", allocation_of(cache_k), allocation_of(cache_v));
"""

RUNNING = {
    "rope": ROPE_BODY,
    "sdpa_kv_cache": SDPA_BODY,
}


def kernel_source(kind, name="plain", extra_scope="", extra_body=""):
    prototype = CONTRACTS[kind].PROTOTYPE
    scope, body = SCOPES[name]
    return (
        f"{PRELUDE}{scope}{extra_scope}{prototype}\n\n"
        f"{prototype.removesuffix(';')}\n{{\n    ++calls;\n{{\n{body}{extra_body}"
        f"{RUNNING[kind]}}}\n}}\n"
    )


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a timing executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_timing_rope_sdpa")
    built = {}

    def build(kind, name="plain", *, extra_scope="", extra_body="", flags=()):
        key = (kind, name, extra_scope, extra_body, flags)
        if key not in built:
            stem = f"{kind}-{name}-{len(built)}"
            source = directory / f"{stem}.c"
            text = kernel_source(kind, name, extra_scope, extra_body)
            source.write_text(text, encoding="ascii", newline="\n")
            output = directory / stem
            result = build_bf16_timing_executable(
                kind,
                source,
                output,
                timeout_s=BUILD_TIMEOUT,
                flags=(*STRICT, *flags),
            )
            assert result.ok, result.log
            built[key] = output
        return built[key]

    return build


def arguments(kind, *, dims=None, n_min="5", n_max="10", cv_max="0.05", seed="7"):
    return (
        *map(str, dims or DIMS[kind]),
        n_min,
        n_max,
        cv_max,
        "interval",
        seed,
    )


def rope_bytes(dims=DIMS["rope"], start=0):
    return bf16_rope_arrays.table_rows(dims, start=start).tobytes()


def started(kind, path, *argv, stdin=None):
    if kind == "rope" and stdin is None:
        stdin = rope_bytes()
    return local_run.run((path, *argv), timeout_s=RUN_TIMEOUT, stdin_data=stdin)


def timed(kind, path, dims=None, seed=7, timeout_s=RUN_TIMEOUT):
    return run_bf16_timing(
        path,
        kind,
        dims or DIMS[kind],
        sample_form="interval",
        seed=seed,
        timeout_s=timeout_s,
    )


def lines_of(stderr, word):
    return [
        line.decode("ascii").split()[1:]
        for line in stderr.splitlines()
        if line.startswith(word + b" ")
    ]


def calls_of(stderr):
    return lines_of(stderr, b"call")


@pytest.mark.parametrize("kind", KINDS)
def test_each_program_declares_its_prototype_byte_for_byte_and_calls_it_once(kind):
    prototype = CONTRACTS[kind].PROTOTYPE
    text = PROGRAM_SOURCES[kind].read_text(encoding="ascii")
    verification = (DIRECTORY / f"bf16_verification_{kind}.c").read_text(
        encoding="ascii"
    )
    assert prototype + "\n" in text
    assert prototype + "\n" in verification
    symbol = f"hilclaw_{kind}_bf16"
    assert text.count(symbol) == 2
    assert f"static kernel_function *volatile kernel = {symbol};" in text
    assert text.count("call(") == 1
    assert '#include "bf16_timing.h"' in text
    assert "<math.h>" not in text


def test_the_rope_input_status_is_documented_and_differs_from_the_others():
    text = PROGRAM_SOURCES["rope"].read_text(encoding="ascii")
    assert f"enum {{ STATUS_INPUT = {INPUT} }};" in text
    assert f" *   {INPUT}  standard input" in text
    assert INPUT not in (COMMAND_LINE, MEMORY, SYSTEM, ZERO_INTERVAL)


@pytest.mark.parametrize(
    "dims, seed, start",
    [
        ((1, 2, 4), 6, 127),
        ((1, 2, 4), 7, 2047),
        ((3, 2, 4), 6, 0),
        ((3, 2, 4), 7, 0),
    ],
)
def test_the_rope_kernel_gets_the_rows_of_the_seed_and_the_drawn_x(
    executable, dims, seed, start
):
    result = timed("rope", executable("rope"), dims=dims, seed=seed)
    assert result.broken is None, result.run
    assert result.state in (State.CONVERGED, State.NOT_CONVERGED)
    x = bf16_rope_arrays.draw_x(dims, seed=seed, draw=0)
    rows = bf16_rope_arrays.table_rows(dims, start=start)
    wanted = f"{bf16_rope_arrays.check_value(x, rows):08x}"
    calls = calls_of(result.run.stderr)
    assert len(calls) == 1 + len(result.intervals_ns)
    assert calls[0] == [*map(str, dims), wanted]


def test_the_rope_rows_are_copied_once(executable):
    run = started("rope", executable("rope"), *arguments("rope"))
    assert run.returncode == 0, run.stderr
    checks = [call[-1] for call in calls_of(run.stderr)]
    assert len(checks) >= 3
    assert len(set(checks[1:])) == 1
    assert checks[1] != checks[0]


@pytest.mark.parametrize("name", ["empty", "short", "longer"])
def test_wrong_rope_input_ends_with_its_own_status(executable, name):
    rows = rope_bytes()
    stdin = {"empty": b"", "short": rows[:-1], "longer": rows + b"\0"}[name]
    run = started("rope", executable("rope"), *arguments("rope"), stdin=stdin)
    assert run.returncode == INPUT
    assert run.stdout == b""
    assert b"bf16_timing_rope: standard input:" in run.stderr
    assert not calls_of(run.stderr)


def test_no_rope_input_at_all_ends_with_its_own_status(executable):
    run = local_run.run((executable("rope"), *arguments("rope")), timeout_s=RUN_TIMEOUT)
    assert run.returncode == INPUT
    assert not calls_of(run.stderr)


def test_unreadable_rope_input_ends_with_its_own_status(executable, tmp_path):
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        run = subprocess.run(
            [executable("rope"), *arguments("rope")],
            stdin=descriptor,
            capture_output=True,
            timeout=RUN_TIMEOUT,
            check=False,
        )
    finally:
        os.close(descriptor)
    assert run.returncode == INPUT
    assert run.stdout == b""
    assert b"standard input: cannot be read" in run.stderr


def test_wrong_rows_of_the_python_side_are_an_exit_status(executable, monkeypatch):
    def short(dims, *, start):
        return np.zeros((dims[0], dims[2] - 2), dtype=np.float32)

    monkeypatch.setattr(bf16_rope_arrays, "table_rows", short)
    result = timed("rope", executable("rope"))
    assert result.broken is Broken.EXIT_STATUS
    assert result.run.returncode == INPUT


def test_an_odd_d_is_a_command_line_status_before_the_input_is_read(executable):
    run = local_run.run(
        (executable("rope"), *arguments("rope", dims=(3, 2, 5))),
        timeout_s=RUN_TIMEOUT,
    )
    assert run.returncode == COMMAND_LINE
    assert run.stdout == b""
    assert b"bf16_timing_rope: d: must be even" in run.stderr


@pytest.mark.parametrize(
    "dims",
    [(2, 5, 4, 2, 3), (2, 2, 4, 2, 3), (1, 7, 2, 1, 4), (3, 3, 2, 2, 1)],
    ids=lambda dims: "-".join(map(str, dims)),
)
@pytest.mark.parametrize("seed", [0, 7, 2**64 - 1])
def test_the_cache_kernel_sees_the_drawn_rows_at_every_call_and_its_writes_persist(
    executable, dims, seed
):
    result = timed("sdpa_kv_cache", executable("sdpa_kv_cache"), dims=dims, seed=seed)
    assert result.broken is None, result.run
    assert result.state in (State.CONVERGED, State.NOT_CONVERGED)
    drawn = bf16_sdpa_kv_cache_arrays.draw_inputs(dims, seed=seed, draw=0)
    crc = 0
    for array in (drawn.q, drawn.k_new, drawn.v_new):
        crc = zlib.crc32(array, crc)
    inputs = f"{crc:08x}"
    rows = f"{zlib.crc32(drawn.cached_v, zlib.crc32(drawn.cached_k)):08x}"
    calls = calls_of(result.run.stderr)
    assert len(calls) == 1 + len(result.intervals_ns) >= 3
    for call in calls:
        assert call == [*map(str, dims), inputs, rows, "1"]


@pytest.mark.skipif(
    sys.platform != "linux", reason="--wrap is a flag of the GNU linker"
)
@pytest.mark.parametrize(
    "dims",
    [(2, 5, 4, 2, 3), (2, 2, 4, 2, 3)],
    ids=lambda dims: "-".join(map(str, dims)),
)
def test_each_cache_is_one_allocation_of_exactly_l_rows(executable, dims):
    path = executable(
        "sdpa_kv_cache",
        "plain",
        extra_scope=ALLOCATIONS,
        extra_body=ALLOCATIONS_BODY,
        flags=("-Wl,--wrap=malloc",),
    )
    run = started("sdpa_kv_cache", path, *arguments("sdpa_kv_cache", dims=dims))
    assert run.returncode == 0, run.stderr
    _, l, _, h_kv, d = dims
    bytes_of_a_cache = str(2 * l * h_kv * d)
    seen = lines_of(run.stderr, b"allocated")
    assert seen
    assert all(line == [bytes_of_a_cache, bytes_of_a_cache] for line in seen)


@pytest.mark.parametrize("kind", KINDS)
def test_a_report_of_the_program_is_judged_completed_and_does_not_hold_the_calls(
    executable, kind
):
    result = timed(kind, executable(kind))
    assert result.broken is None
    assert result.run.stdout.startswith(b"resolution_ns ")
    assert b"call" not in result.run.stdout
    assert re.search(rb"stop (converged|not_converged)\n$", result.run.stdout)


FORCED = [
    ("2", "7", "1e9", "converged", 2),
    ("3", "4", "1e-300", "not_converged", 4),
]


@pytest.mark.parametrize("n_min, n_max, cv_max, stop, count", FORCED)
@pytest.mark.parametrize("kind", KINDS)
def test_the_loop_stops_where_the_rule_says(
    executable, kind, n_min, n_max, cv_max, stop, count
):
    run = started(
        kind,
        executable(kind),
        *arguments(kind, n_min=n_min, n_max=n_max, cv_max=cv_max),
    )
    assert run.returncode == 0, run.stderr
    lines = run.stdout.decode("ascii").splitlines()
    assert len(lines) == count + 2
    assert lines[-1] == f"stop {stop}"
    assert len(calls_of(run.stderr)) == count + 1


@pytest.mark.parametrize("kind", KINDS)
def test_an_aborting_kernel_is_an_exit_status(executable, kind):
    result = timed(kind, executable(kind, "aborting"))
    assert result.broken is Broken.EXIT_STATUS
    assert result.run.returncode == -signal.SIGABRT


@pytest.mark.parametrize("kind", KINDS)
def test_a_hanging_kernel_is_a_timeout(executable, kind):
    result = timed(kind, executable(kind, "hanging"), timeout_s=2)
    assert result.broken is Broken.TIMEOUT


@pytest.mark.parametrize("kind", KINDS)
def test_a_zero_interval_ends_with_its_status(executable, kind):
    run = started(kind, executable(kind, "frozen-clock"), *arguments(kind))
    assert run.returncode == ZERO_INTERVAL
    assert run.stdout.endswith(b"interval_ns 0\n")
    assert b"stop" not in run.stdout


@pytest.mark.parametrize("kind", KINDS)
def test_a_failing_clock_is_a_system_status(executable, kind):
    run = started(kind, executable(kind, "failing-clock"), *arguments(kind))
    assert run.returncode == SYSTEM
    assert b"stop" not in run.stdout


def bad_values(kind):
    values = [
        (name, value)
        for name in NAMES[kind]
        for value in ["0", "01", "-1", "+1", "1x", ""]
    ]
    values += [("n_min", value) for value in ["1", "05"]]
    values += [("n_max", value) for value in ["4", "010"]]
    values += [("cv_max", value) for value in ["0", "nan", "inf", "0.05x", ""]]
    values += [("sample_form", value) for value in ["time", "Interval", ""]]
    values += [("seed", value) for value in ["18446744073709551616", "07", "-1"]]
    return values


BAD = [(kind, name, value) for kind in KINDS for name, value in bad_values(kind)]


@pytest.mark.parametrize(
    "kind, name, value", BAD, ids=[f"{k}-{n}-{i}" for i, (k, n, _) in enumerate(BAD)]
)
def test_a_bad_spelling_is_a_command_line_status(executable, kind, name, value):
    names = NAMES[kind] + TIMING_NAMES
    argv = list(arguments(kind))
    argv[names.index(name)] = value
    run = local_run.run((executable(kind), *argv), timeout_s=RUN_TIMEOUT)
    assert run.returncode == COMMAND_LINE
    assert run.stdout == b""
    assert f"bf16_timing_{kind}: {name}:".encode() in run.stderr
    assert not calls_of(run.stderr)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("change", ["none", "one-less", "one-more"])
def test_a_wrong_argument_count_is_a_command_line_status(executable, kind, change):
    argv = list(arguments(kind))
    argv = {"none": [], "one-less": argv[:-1], "one-more": [*argv, "7"]}[change]
    run = local_run.run((executable(kind), *argv), timeout_s=RUN_TIMEOUT)
    assert run.returncode == COMMAND_LINE
    assert run.stdout == b""
    assert f"bf16_timing_{kind}: usage:".encode() in run.stderr


@pytest.mark.parametrize(
    "dims, name",
    [((3, 2, 4, 2, 3), "l"), ((2, 5, 3, 2, 3), "h"), ((2, 5, 2, 4, 3), "h")],
)
def test_a_broken_rule_between_cache_dimensions_is_a_command_line_status(
    executable, dims, name
):
    run = started(
        "sdpa_kv_cache",
        executable("sdpa_kv_cache"),
        *arguments("sdpa_kv_cache", dims=dims),
    )
    assert run.returncode == COMMAND_LINE
    assert run.stdout == b""
    assert f"bf16_timing_sdpa_kv_cache: {name}:".encode() in run.stderr


TOO_LARGE = {
    "rope": [(2**40, 2**40, 2**40), (2**62, 1, 2), (1, 2**62, 2)],
    "sdpa_kv_cache": [
        (2**40, 2**40, 2**40, 1, 2**40),
        (1, 2**62, 1, 1, 1),
        (2**62, 2**62, 1, 1, 1),
        (1, 2**61, 2, 2, 1),
        (1, 2, 2**62, 1, 1),
    ],
}
FLOOR = [(kind, dims) for kind in KINDS for dims in TOO_LARGE[kind]]


@pytest.mark.parametrize("kind, dims", FLOOR, ids=lambda value: str(value))
def test_dimensions_that_cannot_be_held_are_a_memory_status(executable, kind, dims):
    run = local_run.run(
        (executable(kind), *arguments(kind, dims=dims)), timeout_s=RUN_TIMEOUT
    )
    assert run.returncode == MEMORY
    assert run.stdout == b""
    assert not calls_of(run.stderr)


def test_elements_of_a_draw_that_cannot_be_counted_are_a_memory_status(executable):
    dims = (2**62, 2**63 - 1, 1, 1, 1)
    run = local_run.run(
        (executable("sdpa_kv_cache"), *arguments("sdpa_kv_cache", dims=dims)),
        timeout_s=RUN_TIMEOUT,
    )
    assert run.returncode == MEMORY
    assert b"sizes:" in run.stderr


@pytest.mark.parametrize("kind", KINDS)
def test_samples_that_cannot_be_held_are_a_memory_status(executable, kind):
    run = started(kind, executable(kind), *arguments(kind, n_max=str(2**61)))
    assert run.returncode == MEMORY
    assert run.stdout == b""
    assert not calls_of(run.stderr)
