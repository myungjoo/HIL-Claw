import functools
import os
import shutil
import signal
import struct
import zlib
from pathlib import Path

import numpy as np
import pytest

import hilclaw.harness
from hilclaw import clang_build, local_run, rope_bf16_contract, rope_table
from hilclaw.harness.bf16_verification_arrays import draw_inputs, widen

DIRECTORY = Path(hilclaw.harness.__file__).parent
PROGRAM = DIRECTORY / "bf16_verification_rope.c"
PREFIX = b"bf16_verification_rope: "

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
O0 = (*STRICT, "-O0")
O2 = (*STRICT, "-O2")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses, end mark and fill of the program.
COMMAND_LINE, MEMORY, INPUT = 2, 3, 5
END = b"end\n"
FILL = 0x7FC0

SEEDS = [0, 1, 2**63, 2**64 - 1]
SHAPE = (3, 2, 4)
SHAPES = [(1, 1, 2), (1, 2, 4), (3, 2, 4), (2, 3, 6), (4, 1, 2)]
WIDE_SHAPES = [shape for shape in SHAPES if shape[1] >= 2]

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
    (void)m;
    (void)h;
    (void)d;
    (void)x;
    (void)freqs_cis;
    (void)out;
@BODY@}
"""

COPY_X = """\
    for (size_t i = 0; i < m * h * d; i++)
        out[i] = x[i];
"""

COPY_ROWS = """\
    for (size_t i = 0; i < m * h * d; i++)
        out[i] = 0;
    for (size_t i = 0; i < m; i++)
        for (size_t c = 0; c < d; c++)
            memcpy(&out[i * h * d + 2 * c], &freqs_cis[i * d + c], 2 * sizeof(uint16_t));
"""

OVERWRITE = """\
    memset((void *)freqs_cis, 0xAB, m * d * sizeof(float));
    memset((void *)x, 0xCD, m * h * d * sizeof(uint16_t));
"""

HELPERS = """\
static float widened(uint16_t pattern)
{
    uint32_t bits = (uint32_t)pattern << 16;
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

static uint16_t rounded(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return (uint16_t)((bits + UINT32_C(0x7FFF) + ((bits >> 16) & 1)) >> 16);
}
"""

PLAIN = """\
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++)
            for (size_t p = 0; p < d / 2; p++) {
                size_t e = (i * h + j) * d + 2 * p;
                float c = freqs_cis[i * d + 2 * p], s = freqs_cis[i * d + 2 * p + 1];
                float x0 = widened(x[e]), x1 = widened(x[e + 1]);
                out[e] = rounded(x0 * c - x1 * s);
                out[e + 1] = rounded(x0 * s + x1 * c);
            }
"""

FIRST_TOKEN = """\
    for (size_t i = 0; i < h * d; i++)
        out[i] = x[i];
"""

DIMENSIONS = """\
    for (size_t i = 0; i < m * h * d; i++)
        out[i] = 0;
    out[0] = (uint16_t)m;
    out[1] = (uint16_t)h;
    out[2] = (uint16_t)d;
"""

# External names a kernel may define; each is the name of a static of the program.
COLLIDING = """\
int fail, digits, byte_size, mix, draw_base, draw_patterns, fill_output;
int check_value, report_open, emit, read_rows;
"""

# name: (file-scope text, body of the kernel)
STUBS = {
    "copy-x": ("", COPY_X),
    "copy-rows": ("", COPY_ROWS),
    "overwriting": ("", COPY_ROWS + OVERWRITE),
    "plain": (HELPERS, PLAIN),
    "counting": ("", '    fputs("call\\n", stderr);\n' + COPY_X),
    "printing": ("", '    puts("kernel says hello");\n' + COPY_X),
    "dimensions": ("", DIMENSIONS),
    "silent": ("", ""),
    "first-token": ("", FIRST_TOKEN),
    "colliding": (COLLIDING, COPY_X),
    "hanging": ("", "    for (;;)\n        sleep(1);\n"),
    "aborting": (
        "static int calls;",
        "    if (++calls == 2)\n        abort();\n" + COPY_X,
    ),
}

TABLE = {
    "theta": 500000.0,
    "scale_factor": 8.0,
    "low_freq_factor": 1.0,
    "high_freq_factor": 4.0,
    "old_context_len": 8192,
}

# Patterns a binary32 interpretation would alter: NaNs with payloads, -0, infinities, subnormals.
SPECIAL = (0x7FC00001, 0xFFC12345, 0x7F800001, 0x80000000, 0xFF800000, 0x00000001)


@functools.cache
def _table(d, positions):
    return rope_table.build(head_dim=d, positions=positions, **TABLE)


def table_rows(m, d, start):
    """Rows ``start`` .. ``start + m - 1`` of the table, as ``uint32`` patterns."""
    return _table(d, start + m)[start:].view(np.uint32).copy()


def arbitrary_rows(m, d):
    rows = (np.arange(1, m * d + 1, dtype=np.uint64) * 0x9E3779B1) % 2**32
    rows = rows.astype(np.uint32)
    count = min(len(SPECIAL), m * d)
    rows[:count] = SPECIAL[:count]
    return rows.reshape(m, d)


def expected_x(m, h, d, seed, draw):
    # The same generator sequence: indices 0 .. m*h*d - 1, bits = 8, in memory order.
    first, _ = draw_inputs("elementwise_add", (m * h, d), seed=seed, draw=draw)
    return first.reshape(m, h, d)


def packed_check(x, rows):
    return struct.pack("=I", zlib.crc32(x.tobytes() + rows.tobytes()))


def copied_x(x, rows):
    return x.copy()


def copied_rows(x, rows):
    m, h, d = x.shape
    output = np.zeros((m, h * d), np.uint16)
    output[:, : 2 * d] = rows.view(np.uint16)
    return output.reshape(m, h, d)


def unwritten(x, rows):
    return np.full(x.shape, FILL, np.uint16)


def first_token(x, rows):
    output = unwritten(x, rows)
    output[0] = x[0]
    return output


def expected_blocks(output, shape, draws, seed, rows):
    blocks = []
    for draw in range(draws):
        x = expected_x(*shape, seed, draw)
        blocks.append((packed_check(x, rows), output(x, rows).tobytes()))
    return blocks


def expected_report(output, shape, draws, seed, rows):
    blocks = expected_blocks(output, shape, draws, seed, rows)
    return b"".join(check + block for check, block in blocks) + END


def split(report, m, h, d, draws):
    """Cut a complete report by lengths that follow from the dimensions and ``draws``."""
    size = 4 + 2 * m * h * d
    assert len(report) == draws * size + len(END)
    assert report[draws * size :] == END
    blocks = [report[draw * size : (draw + 1) * size] for draw in range(draws)]
    return [
        (block[:4], np.frombuffer(block[4:], np.uint16).reshape(m, h, d))
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
    directory = tmp_path_factory.mktemp("bf16_verification_rope")
    built = {}

    def build(name, flags=O2):
        if (name, flags) not in built:
            file_scope, body = STUBS[name]
            text = KERNEL.replace("@GLOBALS@", file_scope).replace("@BODY@", body)
            signature = rope_bf16_contract.PROTOTYPE.removesuffix(";")
            text = text.replace("@SIGNATURE@", signature)
            stem = f"{name}-{len(built)}"
            source = directory / f"{stem}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            path = directory / stem
            result = clang_build.build(
                (PROGRAM, source),
                path,
                timeout_s=BUILD_TIMEOUT,
                flags=flags,
                trailing_flags=("-lm",),
            )
            assert result.ok, result.log
            built[name, flags] = path
        return built[name, flags]

    return build


def verify(path, shape, draws, seed, rows, timeout_s=RUN_TIMEOUT):
    arguments = [str(value) for value in (*shape, draws, seed)]
    stdin_data = rows if rows is None or isinstance(rows, bytes) else rows.tobytes()
    return local_run.run((path, *arguments), timeout_s=timeout_s, stdin_data=stdin_data)


def assert_report(run, expected):
    assert run.timed_out is False
    assert run.returncode == 0, run
    assert run.stdout == expected


def assert_refused(run, status, subject=b""):
    assert run.timed_out is False
    assert run.returncode == status, run
    assert run.stdout == b""
    assert run.stderr.startswith(PREFIX + subject)
    assert run.stderr.endswith(b"\n")
    assert run.stderr.count(b"\n") == 1


def test_program_is_ascii_and_declares_the_contract_prototype():
    lines = PROGRAM.read_bytes().decode("ascii").splitlines()
    assert rope_bf16_contract.PROTOTYPE in lines
    assert '#define PROGRAM "bf16_verification_rope"' in lines
    assert lines.index("#define _POSIX_C_SOURCE 200809L") < lines.index(
        '#include "bf16_verification.h"'
    )
    assert "enum { STATUS_INPUT = 5 };" in lines
    assert not any("math.h" in line for line in lines)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("source", ["table", "arbitrary"])
def test_check_values_and_x_agree_with_the_generator(executable, source, shape, seed):
    m, _, d = shape
    rows = table_rows(m, d, 0) if source == "table" else arbitrary_rows(m, d)
    run = verify(executable("copy-x"), shape, 2, seed, rows)
    assert_report(run, expected_report(copied_x, shape, 2, seed, rows))
    for draw, (check, block) in enumerate(split(run.stdout, *shape, 2)):
        x = expected_x(*shape, seed, draw)
        assert check == packed_check(x, rows)
        assert block.flat[0] == x.flat[0]
        assert block.flat[-1] == x.flat[-1]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("shape", WIDE_SHAPES)
@pytest.mark.parametrize("source", ["table", "arbitrary"])
def test_rows_reach_the_kernel_uninterpreted(executable, source, shape, seed):
    m, h, d = shape
    rows = table_rows(m, d, 0) if source == "table" else arbitrary_rows(m, d)
    run = verify(executable("copy-rows"), shape, 2, seed, rows)
    assert_report(run, expected_report(copied_rows, shape, 2, seed, rows))
    for _, block in split(run.stdout, *shape, 2):
        sent = block.reshape(m, h * d)[:, : 2 * d].copy().view(np.uint32)
        np.testing.assert_array_equal(sent, rows)


@pytest.mark.parametrize("name", ["copy-x", "copy-rows"])
def test_rows_of_a_later_position_agree(executable, name):
    shape = (1, 2, 64)
    rows = table_rows(1, 64, 127)
    assert rows[0, 0] != table_rows(1, 64, 0)[0, 0]
    output = copied_x if name == "copy-x" else copied_rows
    run = verify(executable(name), shape, 3, 2**63, rows)
    assert_report(run, expected_report(output, shape, 3, 2**63, rows))


def test_special_patterns_are_passed_through(executable):
    shape = (1, 2, 6)
    rows = np.array([SPECIAL], dtype=np.uint32)
    run = verify(executable("copy-rows"), shape, 2, 5, rows)
    assert_report(run, expected_report(copied_rows, shape, 2, 5, rows))


def test_rows_are_restored_before_every_call(executable):
    m, _, d = shape = SHAPE
    rows = table_rows(m, d, 0)
    run = verify(executable("overwriting"), shape, 3, 7, rows)
    assert_report(run, expected_report(copied_rows, shape, 3, 7, rows))


def test_report_depends_on_the_seed_and_the_rows(executable):
    m, _, d = SHAPE

    def report(seed, rows):
        run = verify(executable("copy-x"), SHAPE, 2, seed, rows)
        assert run.returncode == 0, run
        return run.stdout

    table, other = table_rows(m, d, 0), arbitrary_rows(m, d)
    assert report(7, table) == report(7, table)
    reports = {report(seed, rows) for seed in (*SEEDS, 7) for rows in (table, other)}
    assert len(reports) == 2 * (len(SEEDS) + 1)


def test_drawn_patterns_lie_in_the_value_set(executable):
    shape = (16, 4, 64)
    rows = table_rows(16, 64, 0)
    run = verify(executable("copy-x"), shape, 2, 11, rows)
    reported = set()
    for _, block in split(run.stdout, *shape, 2):
        reported.update(block.ravel().tolist())
    assert reported == set(rope_bf16_contract.X_PATTERNS)


@pytest.mark.parametrize("flags", [O0, O2], ids=["O0", "O2"])
@pytest.mark.parametrize("start", [0, 5])
def test_output_of_a_plain_bf16_kernel_meets_a_float64_rotation(
    executable, flags, start
):
    m, h, d = shape = (4, 3, 8)
    draws, seed = 3, 12345
    rows = table_rows(m, d, start)
    table = rows.view(np.float32).astype(np.float64)
    c, s = table[:, None, 0::2], table[:, None, 1::2]
    run = verify(executable("plain", flags), shape, draws, seed, rows)
    assert run.returncode == 0, run
    for draw, (check, block) in enumerate(split(run.stdout, *shape, draws)):
        x = expected_x(*shape, seed, draw)
        assert check == packed_check(x, rows)
        wide = widen(x.reshape(m * h, d)).reshape(m, h, d)
        expected = np.empty_like(wide)
        expected[..., 0::2] = wide[..., 0::2] * c - wide[..., 1::2] * s
        expected[..., 1::2] = wide[..., 0::2] * s + wide[..., 1::2] * c
        output = widen(block.reshape(m * h, d).copy()).reshape(m, h, d)
        # A loose margin of this test (bf16 rounding of float results), not a tolerance.
        np.testing.assert_allclose(output, expected, rtol=0, atol=2**-7)


def test_one_kernel_call_per_draw(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("counting"), SHAPE, 4, 7, rows)
    assert_report(run, expected_report(copied_x, SHAPE, 4, 7, rows))
    assert run.stderr.count(b"call\n") == 4


def test_kernel_output_arrives_on_standard_error(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("printing"), SHAPE, 2, 7, rows)
    assert_report(run, expected_report(copied_x, SHAPE, 2, 7, rows))
    assert run.stderr.count(b"kernel says hello\n") == 2
    assert b"hello" not in run.stdout


@pytest.mark.parametrize("shape", [(3, 2, 4), (1, 1, 4), (1, 3, 2), (5, 7, 6)])
def test_dimensions_reach_the_kernel(executable, shape):
    m, h, d = shape
    run = verify(executable("dimensions"), shape, 2, 7, arbitrary_rows(m, d))
    assert run.returncode == 0, run
    expected = [m, h, d] + [0] * (m * h * d - 3)
    for _, block in split(run.stdout, *shape, 2):
        assert block.ravel().tolist() == expected


def test_unwritten_output_is_reported_as_the_fill(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("silent"), SHAPE, 2, 7, rows)
    assert_report(run, expected_report(unwritten, SHAPE, 2, 7, rows))
    for _, block in split(run.stdout, *SHAPE, 2):
        assert (block == FILL).all()


def test_partly_written_output_holds_no_stale_element(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("first-token"), SHAPE, 2, 7, rows)
    assert_report(run, expected_report(first_token, SHAPE, 2, 7, rows))
    _, second = split(run.stdout, *SHAPE, 2)[1]
    assert (second[1:] == FILL).all()


def test_kernel_may_define_the_names_of_the_program(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("colliding"), SHAPE, 2, 7, rows)
    assert_report(run, expected_report(copied_x, SHAPE, 2, 7, rows))


def test_report_length_follows_from_the_dimensions_and_draws(executable):
    m, h, d = shape = (3, 5, 6)
    for draws in (1, 2, 5):
        run = verify(executable("copy-rows"), shape, draws, 9, arbitrary_rows(m, d))
        assert run.returncode == 0, run
        assert len(run.stdout) == draws * (4 + 2 * m * h * d) + 4
        assert run.stdout.endswith(END)


def test_kernel_that_never_returns_leaves_the_first_check_value(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("hanging"), SHAPE, 2, 7, rows, timeout_s=2)
    assert run.timed_out is True
    assert run.returncode is None
    assert run.stdout == packed_check(expected_x(*SHAPE, 7, 0), rows)


def test_kernel_that_aborts_leaves_the_report_written_so_far(executable):
    rows = table_rows(SHAPE[0], SHAPE[2], 0)
    run = verify(executable("aborting"), SHAPE, 3, 7, rows)
    assert run.timed_out is False
    assert run.returncode == -signal.SIGABRT
    first, second = expected_blocks(copied_x, SHAPE, 2, 7, rows)
    assert run.stdout == first[0] + first[1] + second[0]


ROW_BYTES = 4 * SHAPE[0] * SHAPE[2]
BAD_INPUTS = {
    "null-device": None,
    "empty": b"",
    "one-byte-short": bytes(ROW_BYTES - 1),
    "one-byte-too-many": bytes(ROW_BYTES + 1),
    "twice": bytes(2 * ROW_BYTES),
}


@pytest.mark.parametrize("data", BAD_INPUTS.values(), ids=BAD_INPUTS.keys())
def test_standard_input_of_another_length_is_refused(executable, data):
    run = verify(executable("counting"), SHAPE, 2, 7, data)
    assert_refused(run, INPUT, b"standard input: ")
    assert b"call" not in run.stderr


def test_large_standard_input_past_the_rows_is_refused(executable):
    run = verify(executable("counting"), SHAPE, 2, 7, bytes(ROW_BYTES + 2**20))
    assert_refused(run, INPUT, b"standard input: ")
    assert b"call" not in run.stderr


GOOD = ("3", "2", "4", "2", "7")
ARGUMENT = {"m": 0, "h": 1, "d": 2, "draws": 3, "seed": 4}

BAD_VALUES = (
    [(name, value) for name in "mhd" for value in ["0", "", "-2", "+2", "2x", " 2"]]
    + [(name, value) for name in "mhd" for value in ["2 ", "02", "00", "2" * 30]]
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
    "four-of-the-other-kinds": ("5", "6", "2", "7"),
    "six": (*GOOD, "1"),
}

# Dimensions that pass the command line and cannot be held or allocated, with the subject.
TOO_LARGE = {
    "tokens-heads-overflow": ((2**40, 2**40, 2), b"sizes"),
    "x-bytes-overflow": ((2**62, 1, 2), b"sizes"),
    "elements-overflow": ((1, 2**63, 2), b"sizes"),
    "row-bytes-overflow": ((2**61, 1, 2), b"sizes"),
    "not-allocatable": ((2**28, 2, 2**29), b"malloc"),
}


@pytest.mark.parametrize("data", [b"", bytes(ROW_BYTES)], ids=["empty", "some"])
@pytest.mark.parametrize(("shape", "subject"), TOO_LARGE.values(), ids=TOO_LARGE.keys())
def test_arrays_that_cannot_be_held_are_refused_before_the_input(
    executable, shape, subject, data
):
    run = verify(executable("counting"), shape, 1, 0, data)
    assert_refused(run, MEMORY, subject + b": ")


@pytest.mark.parametrize("arguments", BAD_COUNTS.values(), ids=BAD_COUNTS.keys())
def test_wrong_number_of_arguments_is_refused(executable, arguments):
    run = local_run.run(
        (executable("counting"), *arguments),
        timeout_s=RUN_TIMEOUT,
        stdin_data=bytes(ROW_BYTES),
    )
    assert_refused(run, COMMAND_LINE, b"usage: ")
    assert b"<m> <h> <d> <draws> <seed>" in run.stderr


@pytest.mark.parametrize(("name", "value"), BAD_VALUES, ids=BAD_VALUE_IDS)
def test_malformed_argument_is_refused(executable, name, value):
    arguments = list(GOOD)
    arguments[ARGUMENT[name]] = value
    run = local_run.run(
        (executable("counting"), *arguments),
        timeout_s=RUN_TIMEOUT,
        stdin_data=bytes(ROW_BYTES),
    )
    assert_refused(run, COMMAND_LINE, name.encode("ascii") + b": ")


@pytest.mark.parametrize("d", [1, 63, 2**64 - 1])
def test_odd_d_is_refused(executable, d):
    run = verify(executable("counting"), (1, 1, d), 1, 0, bytes(4 * min(d, 63)))
    assert_refused(run, COMMAND_LINE, b"d: ")


def test_good_command_line_of_the_refusal_tests_is_accepted(executable):
    rows = arbitrary_rows(3, 4)
    run = local_run.run(
        (executable("counting"), *GOOD),
        timeout_s=RUN_TIMEOUT,
        stdin_data=rows.tobytes(),
    )
    assert_report(run, expected_report(copied_x, SHAPE, 2, 7, rows))
