import os
import shutil
import signal
import struct
from pathlib import Path

import numpy as np
import pytest

import hilclaw.harness
from hilclaw import clang_build, gemm_bf16_contract, local_run
from hilclaw.harness.bf16_verification_arrays import (
    check_value,
    count_failures,
    draw_inputs,
    reference,
    widen,
)

DIRECTORY = Path(hilclaw.harness.__file__).parent
PROGRAM = DIRECTORY / "bf16_verification_gemm.c"
HEADER = DIRECTORY / "bf16_verification.h"

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
O0 = (*STRICT, "-O0")
O2 = (*STRICT, "-O2")
FAST_MATH = (*STRICT, "-O2", "-ffast-math")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses, end mark, fill and stderr prefix of the program.
COMMAND_LINE, MEMORY = 2, 3
END = b"end\n"
FILL = 0x7FC0
PREFIX = b"bf16_verification_gemm: "

SEEDS = [0, 1, 2**63, 2**64 - 1]
SHAPE = (6, 4, 5)

KERNEL = """\
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

@GLOBALS@
@SIGNATURE@
{
@BODY@}
"""

COPY_A = """\
    (void)b;
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++)
            c[i * n + j] = a[i * k + j % k];
"""

COPY_B = """\
    (void)a;
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++)
            c[i * n + j] = b[(i % k) * n + j];
"""

GEMM = """\
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += widened(a[i * k + p]) * widened(b[p * n + j]);
            uint32_t bits;
            memcpy(&bits, &sum, sizeof bits);
            c[i * n + j] = (uint16_t)((bits + UINT32_C(0x7FFF) + ((bits >> 16) & 1)) >> 16);
        }
"""

WIDENED = """\
static float widened(uint16_t pattern)
{
    uint32_t bits = (uint32_t)pattern << 16;
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}
"""

FIRST_ROW = """\
    (void)m;
    (void)b;
    for (size_t j = 0; j < n; j++)
        c[j] = a[j % k];
"""

DIMENSIONS = """\
    (void)a;
    (void)b;
    for (size_t i = 0; i < m * n; i++)
        c[i] = 0;
    c[0] = (uint16_t)m;
    c[1] = (uint16_t)k;
    c[2] = (uint16_t)n;
"""

UNUSED = "    (void)m;\n    (void)k;\n    (void)n;\n    (void)a;\n    (void)b;\n"

CHECKING = """\
    if (m != @M@ || k != @K@ || n != @N@)
        abort();
    for (size_t i = 0; i < m * n; i++)
        if (c[i] != UINT16_C(0x7FC0))
            abort();
"""

CALLS = "static int calls;"

# name: (file-scope text, body of the kernel)
KERNELS = {
    "copy-a": ("", COPY_A),
    "copy-b": ("", COPY_B),
    "gemm": (WIDENED, GEMM),
    "counting": ("", '    fputs("call\\n", stderr);\n' + COPY_A),
    "printing": ("", '    puts("kernel says hello");\n' + COPY_A),
    "checking": ("", CHECKING + COPY_A),
    "dimensions": ("", DIMENSIONS),
    "silent": ("", UNUSED + "    (void)c;\n"),
    "first-row": ("", FIRST_ROW),
    "hanging": ("", UNUSED + "    (void)c;\n    for (;;)\n        sleep(1);\n"),
    "aborting": (CALLS, "    if (++calls == 2)\n        abort();\n" + COPY_A),
}

GOOD = ("6", "4", "5", "2", "7")
ARGUMENT = {"m": 0, "k": 1, "n": 2, "draws": 3, "seed": 4}

BAD_VALUES = (
    [(name, value) for name in "mkn" for value in ["0", "", "-1", "+1", "1x", " 1"]]
    + [(name, value) for name in "mkn" for value in ["1 ", "01", "00", "1" * 30]]
    + [("draws", value) for value in ["0", "", "-1", "+2", "02", "2.0", "1" * 30]]
    + [("draws", "18446744073709551616")]
    + [("seed", value) for value in ["18446744073709551616", "", "-1", "+7", "07"]]
    + [("seed", value) for value in ["0x7", "7 ", "1" * 30]]
)
BAD_VALUE_IDS = [
    f"{name}-{position}" for position, (name, value) in enumerate(BAD_VALUES)
]

BAD_COUNTS = {
    "none": (),
    "one": GOOD[:1],
    "four": GOOD[:4],
    "six": (*GOOD, "1"),
}

# m, k, n that pass the command line and cannot be held or allocated.
TOO_LARGE = {
    "product-overflows": (2**40, 2**40, 2**40),
    "bytes-overflow": (2**63, 1, 1),
    "output-overflows": (2**32, 1, 2**32),
    "not-allocatable": (2**30, 2**30, 2**30),
}


def copied_a(a, b):
    m, k = a.shape
    n = b.shape[1]
    return np.array([[a[i, j % k] for j in range(n)] for i in range(m)], np.uint16)


def copied_b(a, b):
    m, k = a.shape
    return b[np.arange(m) % k, :]


def unwritten(a, b):
    return np.full((a.shape[0], b.shape[1]), FILL, np.uint16)


def first_row(a, b):
    c = unwritten(a, b)
    c[0, :] = copied_a(a, b)[0, :]
    return c


def inputs(m, k, n, seed, draw):
    return draw_inputs("gemm", (m, k, n), seed=seed, draw=draw)


def packed_check(a, b):
    return struct.pack("=I", check_value(a, b))


def expected_blocks(output, m, k, n, draws, seed):
    blocks = []
    for draw in range(draws):
        a, b = inputs(m, k, n, seed, draw)
        blocks.append((packed_check(a, b), output(a, b).tobytes()))
    return blocks


def expected_report(output, m, k, n, draws, seed):
    blocks = expected_blocks(output, m, k, n, draws, seed)
    return b"".join(check + block for check, block in blocks) + END


def split(report, m, n, draws):
    """Cut a complete report by lengths that follow from ``m``, ``n`` and ``draws``."""
    size = 4 + 2 * m * n
    assert len(report) == draws * size + len(END)
    assert report[draws * size :] == END
    blocks = [report[draw * size : (draw + 1) * size] for draw in range(draws)]
    return [
        (struct.unpack("=I", block[:4])[0], np.frombuffer(block[4:], np.uint16))
        for block in blocks
    ]


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_verification_gemm")
    built = {}

    def build(name, flags=O2):
        if (name, flags) not in built:
            file_scope, body = KERNELS[name]
            text = KERNEL.replace("@GLOBALS@", file_scope).replace("@BODY@", body)
            signature = gemm_bf16_contract.PROTOTYPE.removesuffix(";")
            text = text.replace("@SIGNATURE@", signature)
            for dimension, value in zip("MKN", SHAPE, strict=True):
                text = text.replace(f"@{dimension}@", str(value))
            stem = f"{name}-{len(built)}"
            source = directory / f"{stem}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            output = directory / stem
            result = clang_build.build(
                (PROGRAM, source), output, timeout_s=BUILD_TIMEOUT, flags=flags
            )
            assert result.ok, result.log
            built[name, flags] = output
        return built[name, flags]

    return build


def verify(path, m, k, n, draws, seed, timeout_s=RUN_TIMEOUT):
    arguments = [str(value) for value in (m, k, n, draws, seed)]
    return local_run.run((path, *arguments), timeout_s=timeout_s)


def assert_report(run, expected):
    assert run.timed_out is False
    assert run.returncode == 0, run
    assert run.stdout == expected


def assert_refused(run, status):
    assert run.timed_out is False
    assert run.returncode == status, run
    assert run.stdout == b""
    assert run.stderr.startswith(PREFIX)
    assert run.stderr.endswith(b"\n")
    assert run.stderr.count(b"\n") == 1


def test_sources_are_ascii_and_program_declares_the_contract_prototype():
    HEADER.read_bytes().decode("ascii")
    text = PROGRAM.read_bytes().decode("ascii")
    assert gemm_bf16_contract.PROTOTYPE in text.splitlines()
    assert '#include "bf16_verification.h"' in text.splitlines()


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize(
    ("name", "output"), [("copy-a", copied_a), ("copy-b", copied_b)]
)
def test_check_values_and_outputs_agree_with_the_array_module(
    executable, name, output, draws, seed
):
    m, k, n = SHAPE
    run = verify(executable(name), m, k, n, draws, seed)
    assert_report(run, expected_report(output, m, k, n, draws, seed))
    for draw, (check, block) in enumerate(split(run.stdout, m, n, draws)):
        a, b = inputs(m, k, n, seed, draw)
        assert check == check_value(a, b)
        operand = a if name == "copy-a" else b
        assert operand.flat[0] in block
        assert operand.flat[-1] in block
        np.testing.assert_array_equal(block.reshape(m, n), output(a, b))


@pytest.mark.parametrize(
    "shape", [(1, 4, 5), (6, 1, 5), (6, 4, 1), (1, 1, 1), (3, 7, 2), (2, 3, 9)]
)
@pytest.mark.parametrize(
    ("name", "output"), [("copy-a", copied_a), ("copy-b", copied_b)]
)
@pytest.mark.parametrize("seed", [0, 2**63, 2**64 - 1])
def test_shapes_with_small_dimensions_agree_with_the_array_module(
    executable, name, output, shape, seed
):
    run = verify(executable(name), *shape, 2, seed)
    assert_report(run, expected_report(output, *shape, 2, seed))


def test_reported_inputs_cover_both_ends_of_each_operand(executable):
    m, k, n = SHAPE
    run_a = verify(executable("copy-a"), m, k, n, 1, 3)
    run_b = verify(executable("copy-b"), m, k, n, 1, 3)
    a, b = inputs(m, k, n, 3, 0)
    [(_, block_a)] = split(run_a.stdout, m, n, 1)
    [(_, block_b)] = split(run_b.stdout, m, n, 1)
    assert block_a[0] == a[0, 0] and block_a[-1] == a[m - 1, (n - 1) % k]
    assert a[m - 1, k - 1] == block_a.reshape(m, n)[m - 1, k - 1]
    assert block_b[0] == b[0, 0] and block_b[-1] == b[(m - 1) % k, n - 1]
    assert b[k - 1, n - 1] == block_b.reshape(m, n)[k - 1, n - 1]


@pytest.mark.parametrize("name", ["copy-a", "copy-b"])
def test_report_depends_on_the_seed_only(executable, name):
    def report(seed):
        run = verify(executable(name), *SHAPE, 2, seed)
        assert run.returncode == 0, run
        return run.stdout

    assert report(7) == report(7)
    assert len({report(seed) for seed in (*SEEDS, 7, 8)}) == len(SEEDS) + 2


@pytest.mark.parametrize("flags", [O0, O2], ids=["O0", "O2"])
def test_output_of_a_plain_bf16_kernel_meets_the_float64_reference(executable, flags):
    m, k, n = SHAPE
    draws, seed = 3, 12345
    run = verify(executable("gemm", flags), m, k, n, draws, seed)
    assert run.returncode == 0, run
    for draw, (check, block) in enumerate(split(run.stdout, m, n, draws)):
        a, b = inputs(m, k, n, seed, draw)
        assert check == check_value(a, b)
        output = block.reshape(m, n).copy()
        assert np.isfinite(widen(output)).all()
        # A loose margin of this test (bf16 rounding of results below 4), not a tolerance.
        counts = count_failures(output, reference("gemm", a, b), rtol=2**-7, atol=2**-7)
        assert counts == (0, 0)


def test_one_kernel_call_per_draw(executable):
    run = verify(executable("counting"), *SHAPE, 4, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 4, 7))
    assert run.stderr.count(b"call\n") == 4


def test_kernel_output_arrives_on_standard_error(executable):
    run = verify(executable("printing"), *SHAPE, 2, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 2, 7))
    assert run.stderr.count(b"kernel says hello\n") == 2
    assert b"hello" not in run.stdout


def test_arguments_are_passed_and_output_is_filled_before_every_call(executable):
    run = verify(executable("checking"), *SHAPE, 3, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 3, 7))


@pytest.mark.parametrize("shape", [(6, 4, 5), (3, 7, 2), (2, 9, 3)])
def test_dimensions_reach_the_kernel(executable, shape):
    m, k, n = shape
    run = verify(executable("dimensions"), m, k, n, 2, 7)
    assert run.timed_out is False
    assert run.returncode == 0, run
    expected = [m, k, n] + [0] * (m * n - 3)
    for _, block in split(run.stdout, m, n, 2):
        assert block.tolist() == expected


@pytest.mark.parametrize("flags", [O2, FAST_MATH], ids=["O2", "fast-math"])
def test_unwritten_output_is_reported_as_the_fill(executable, flags):
    run = verify(executable("silent", flags), *SHAPE, 2, 7)
    assert_report(run, expected_report(unwritten, *SHAPE, 2, 7))
    for _, block in split(run.stdout, SHAPE[0], SHAPE[2], 2):
        assert (block == FILL).all()


def test_inputs_keep_their_bit_patterns_under_fast_math(executable):
    run = verify(executable("copy-a", FAST_MATH), *SHAPE, 2, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 2, 7))


def test_partly_written_output_holds_no_stale_element(executable):
    run = verify(executable("first-row"), *SHAPE, 2, 7)
    assert_report(run, expected_report(first_row, *SHAPE, 2, 7))
    m, _, n = SHAPE
    _, second = split(run.stdout, m, n, 2)[1]
    assert (second[n:] == FILL).all()


def test_report_length_follows_from_the_dimensions_and_draws(executable):
    m, k, n = (3, 7, 2)
    for draws in (1, 2, 5):
        run = verify(executable("copy-b"), m, k, n, draws, 9)
        assert run.returncode == 0, run
        assert len(run.stdout) == draws * (4 + 2 * m * n) + 4
        assert run.stdout.endswith(END)


def test_kernel_that_never_returns_leaves_the_first_check_value(executable):
    run = verify(executable("hanging"), *SHAPE, 2, 7, timeout_s=2)
    assert run.timed_out is True
    assert run.returncode is None
    assert run.stdout == packed_check(*inputs(*SHAPE, 7, 0))


def test_kernel_that_aborts_leaves_the_report_written_so_far(executable):
    run = verify(executable("aborting"), *SHAPE, 3, 7)
    assert run.timed_out is False
    assert run.returncode == -signal.SIGABRT
    first, second = expected_blocks(copied_a, *SHAPE, 2, 7)
    assert run.stdout == first[0] + first[1] + second[0]


@pytest.mark.parametrize("shape", TOO_LARGE.values(), ids=TOO_LARGE.keys())
def test_arrays_that_cannot_be_held_are_refused(executable, shape):
    assert_refused(verify(executable("copy-a"), *shape, 1, 0), MEMORY)


@pytest.mark.parametrize("arguments", BAD_COUNTS.values(), ids=BAD_COUNTS.keys())
def test_wrong_number_of_arguments_is_refused(executable, arguments):
    run = local_run.run((executable("copy-a"), *arguments), timeout_s=RUN_TIMEOUT)
    assert_refused(run, COMMAND_LINE)


@pytest.mark.parametrize(("name", "value"), BAD_VALUES, ids=BAD_VALUE_IDS)
def test_malformed_argument_is_refused(executable, name, value):
    arguments = list(GOOD)
    arguments[ARGUMENT[name]] = value
    run = local_run.run((executable("copy-a"), *arguments), timeout_s=RUN_TIMEOUT)
    assert_refused(run, COMMAND_LINE)


def test_good_command_line_of_the_refusal_tests_is_accepted(executable):
    run = local_run.run((executable("copy-a"), *GOOD), timeout_s=RUN_TIMEOUT)
    assert_report(run, expected_report(copied_a, 6, 4, 5, 2, 7))
