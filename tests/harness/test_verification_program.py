import math
import os
import shutil
import signal
import struct
import zlib
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import clang_build, local_run

PROGRAM = Path(hilclaw.harness.__file__).parent / "verification_program.c"

# ADR-0008 decision 4, byte for byte.
PROTOTYPE = (
    "void hilclaw_gemm(size_t m, size_t k, size_t n, "
    "const float *restrict a, const float *restrict b, float *restrict c);"
)

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
O0 = (*STRICT, "-O0")
O2 = (*STRICT, "-O2")
FAST_MATH = (*STRICT, "-O2", "-ffast-math")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses, end mark and fill of the verification program.
COMMAND_LINE, MEMORY = 2, 3
END = b"end\n"
NAN_BITS = 0x7FC00000

MASK = 2**64 - 1
GOLDEN = 0x9E3779B97F4A7C15
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
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
"""

FIRST_ROW = """\
    (void)m;
    (void)b;
    for (size_t j = 0; j < n; j++)
        c[j] = a[j % k];
"""

UNUSED = "    (void)m;\n    (void)k;\n    (void)n;\n    (void)a;\n    (void)b;\n"

CHECKING = """\
    if (m != @M@ || k != @K@ || n != @N@)
        abort();
    for (size_t i = 0; i < m * n; i++) {
        uint32_t bits;
        memcpy(&bits, &c[i], sizeof bits);
        if (bits != UINT32_C(0x7FC00000))
            abort();
    }
"""

CALLS = "static int calls;"

# name: (file-scope text, body of the kernel)
KERNELS = {
    "copy-a": ("", COPY_A),
    "copy-b": ("", COPY_B),
    "gemm": ("", GEMM),
    "counting": ("", '    fputs("call\\n", stderr);\n' + COPY_A),
    "printing": ("", '    puts("kernel says hello");\n' + COPY_A),
    "checking": ("", CHECKING + COPY_A),
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
    "six-with-a-tolerance": (*GOOD, "1e-6"),
    "seven-with-two-tolerances": (*GOOD, "1e-6", "1e-9"),
}

# m, k, n that pass the command line and cannot be held or allocated.
TOO_LARGE = {
    "product-overflows": (2**40, 2**40, 2**40),
    "bytes-overflow": (2**62, 1, 1),
    "output-overflows": (2**32, 1, 2**32),
    "not-allocatable": (2**30, 2**30, 2**30),
}


def mix(x):
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & MASK
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & MASK
    return x ^ (x >> 31)


def drawn(m, k, n, seed, draw):
    """Bit patterns of ``a`` and of ``b`` of one draw, written from the header comment."""
    base = mix((seed + (draw + 1) * GOLDEN) & MASK)
    bits = []
    for element in range(m * k + k * n):
        word = mix((base + (element + 1) * GOLDEN) & MASK)
        bits.append((word & 1) << 31 | 126 << 23 | word >> 41)
    return bits[: m * k], bits[m * k :]


def pack(bits):
    return struct.pack(f"={len(bits)}I", *bits)


def check_value(a, b):
    return struct.pack("=I", zlib.crc32(pack(a) + pack(b)))


def as_floats(bits):
    return struct.unpack(f"={len(bits)}f", pack(bits))


def copied_a(m, k, n, a, b):
    return [a[i * k + j % k] for i in range(m) for j in range(n)]


def copied_b(m, k, n, a, b):
    return [b[(i % k) * n + j] for i in range(m) for j in range(n)]


def unwritten(m, k, n, a, b):
    return [NAN_BITS] * (m * n)


def first_row(m, k, n, a, b):
    return [a[j % k] for j in range(n)] + [NAN_BITS] * ((m - 1) * n)


def expected_blocks(output, m, k, n, draws, seed):
    blocks = []
    for draw in range(draws):
        a, b = drawn(m, k, n, seed, draw)
        blocks.append((check_value(a, b), pack(output(m, k, n, a, b))))
    return blocks


def expected_report(output, m, k, n, draws, seed):
    blocks = expected_blocks(output, m, k, n, draws, seed)
    return b"".join(check + block for check, block in blocks) + END


def split(report, m, n, draws):
    """Cut a complete report by lengths that follow from ``m``, ``n`` and ``draws``."""
    size = 4 + 4 * m * n
    assert len(report) == draws * size + len(END)
    assert report[draws * size :] == END
    blocks = [report[draw * size : (draw + 1) * size] for draw in range(draws)]
    return [(block[:4], struct.unpack(f"={m * n}I", block[4:])) for block in blocks]


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("verification_program")
    built = {}

    def build(name, flags=O2):
        if (name, flags) not in built:
            file_scope, body = KERNELS[name]
            text = KERNEL.replace("@GLOBALS@", file_scope).replace("@BODY@", body)
            text = text.replace("@SIGNATURE@", PROTOTYPE.removesuffix(";"))
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
    assert run.stderr.startswith(b"verification_program: ")
    assert run.stderr.endswith(b"\n")
    assert run.stderr.count(b"\n") == 1


def test_program_source_is_ascii_and_declares_the_contract_prototype():
    text = PROGRAM.read_bytes().decode("ascii")
    assert PROTOTYPE in text.splitlines()


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize(
    ("name", "output"), [("copy-a", copied_a), ("copy-b", copied_b)]
)
def test_report_holds_check_values_and_outputs_bit_for_bit(
    executable, name, output, draws, seed
):
    run = verify(executable(name), *SHAPE, draws, seed)
    assert_report(run, expected_report(output, *SHAPE, draws, seed))
    m, _, n = SHAPE
    blocks = split(run.stdout, m, n, draws)
    assert len({block for _, block in blocks}) == draws
    values = [value for _, block in blocks for value in as_floats(block)]
    assert all(0.5 <= abs(value) < 1.0 for value in values)
    assert min(values) < 0.0 < max(values)


@pytest.mark.parametrize("name", ["copy-a", "copy-b"])
def test_report_depends_on_the_seed_only(executable, name):
    def report(seed):
        run = verify(executable(name), *SHAPE, 2, seed)
        assert run.returncode == 0, run
        return run.stdout

    assert report(7) == report(7)
    assert len({report(seed) for seed in (*SEEDS, 7, 8)}) == len(SEEDS) + 2


@pytest.mark.parametrize("flags", [O0, O2], ids=["O0", "O2"])
def test_product_of_a_plain_kernel_follows_the_drawn_inputs(executable, flags):
    m, k, n = SHAPE
    draws, seed = 2, 12345
    run = verify(executable("gemm", flags), m, k, n, draws, seed)
    assert run.returncode == 0, run
    for draw, (check, block) in enumerate(split(run.stdout, m, n, draws)):
        a_bits, b_bits = drawn(m, k, n, seed, draw)
        assert check == check_value(a_bits, b_bits)
        a, b, c = as_floats(a_bits), as_floats(b_bits), as_floats(block)
        for i in range(m):
            for j in range(n):
                product = math.fsum(a[i * k + p] * b[p * n + j] for p in range(k))
                # A margin of this test, not a tolerance of the harness.
                assert abs(c[i * n + j] - product) <= 1e-5


def test_one_kernel_call_per_draw(executable):
    run = verify(executable("counting"), *SHAPE, 4, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 4, 7))
    assert run.stderr.count(b"call\n") == 4


def test_kernel_output_arrives_on_standard_error(executable):
    run = verify(executable("printing"), *SHAPE, 2, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 2, 7))
    assert run.stderr.count(b"kernel says hello\n") == 2


def test_arguments_are_passed_and_output_is_nan_before_every_call(executable):
    run = verify(executable("checking"), *SHAPE, 3, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 3, 7))


@pytest.mark.parametrize("flags", [O2, FAST_MATH], ids=["O2", "fast-math"])
def test_unwritten_output_is_reported_as_the_nan_bit_pattern(executable, flags):
    run = verify(executable("silent", flags), *SHAPE, 2, 7)
    assert_report(run, expected_report(unwritten, *SHAPE, 2, 7))


def test_inputs_keep_their_bit_patterns_under_fast_math(executable):
    run = verify(executable("copy-a", FAST_MATH), *SHAPE, 2, 7)
    assert_report(run, expected_report(copied_a, *SHAPE, 2, 7))


def test_partly_written_output_holds_no_stale_element(executable):
    run = verify(executable("first-row"), *SHAPE, 2, 7)
    assert_report(run, expected_report(first_row, *SHAPE, 2, 7))


@pytest.mark.parametrize("shape", [(1, 4, 5), (6, 1, 5), (6, 4, 1), (1, 1, 1)])
@pytest.mark.parametrize(
    ("name", "output"), [("copy-a", copied_a), ("copy-b", copied_b)]
)
def test_one_draw_of_a_shape_with_a_dimension_of_one(executable, name, output, shape):
    run = verify(executable(name), *shape, 1, 7)
    assert_report(run, expected_report(output, *shape, 1, 7))


def test_kernel_that_never_returns_leaves_the_first_check_value(executable):
    run = verify(executable("hanging"), *SHAPE, 2, 7, timeout_s=2)
    assert run.timed_out is True
    assert run.returncode is None
    assert run.stdout == check_value(*drawn(*SHAPE, 7, 0))


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
