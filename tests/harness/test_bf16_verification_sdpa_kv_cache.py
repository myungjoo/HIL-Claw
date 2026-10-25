import math
import os
import re
import shutil
import signal
import struct
import zlib
from pathlib import Path
from typing import NamedTuple

import numpy as np
import pytest

import hilclaw.harness
from hilclaw import clang_build, local_run, sdpa_kv_cache_bf16_contract
from hilclaw.harness.bf16_verification_arrays import draw_inputs, widen

DIRECTORY = Path(hilclaw.harness.__file__).parent
PROGRAM = DIRECTORY / "bf16_verification_sdpa_kv_cache.c"
PREFIX = b"bf16_verification_sdpa_kv_cache: "

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
O0 = (*STRICT, "-O0")
O2 = (*STRICT, "-O2")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses, end mark and fill of the program.
COMMAND_LINE, MEMORY = 2, 3
END = b"end\n"
FILL = 0x7FC0
MARK = 0x1234
SCRIBBLE = 0xABAB

SEEDS = [0, 1, 2**63, 2**64 - 1]
SHAPE = (2, 5, 4, 2, 3)
# (m, l, h, h_kv, d): m = l = 1 with d = 1; P = 0 with h = h_kv; decode-like P = 3
# with h = 4*h_kv; P = 3 with m = 2; d = 1 with h = 4*h_kv and P = 1; P = 0 with h = 4*h_kv.
SHAPES = [
    (1, 1, 1, 1, 1),
    (2, 2, 2, 2, 3),
    (1, 4, 4, 1, 2),
    (2, 5, 4, 2, 3),
    (3, 4, 8, 2, 1),
    (3, 3, 4, 1, 2),
]

KERNEL = """\
#define _POSIX_C_SOURCE 200809L
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

@GLOBALS@
@SIGNATURE@
{
    (void)m;
    (void)l;
    (void)h;
    (void)h_kv;
    (void)d;
    (void)q;
    (void)k_new;
    (void)v_new;
    (void)cache_k;
    (void)cache_v;
    (void)out;
@BODY@}
"""

COPY = """\
    memcpy(out, q, m * h * d * sizeof(uint16_t));
    memcpy(cache_k + (l - m) * h_kv * d, k_new, m * h_kv * d * sizeof(uint16_t));
    memcpy(cache_v + (l - m) * h_kv * d, v_new, m * h_kv * d * sizeof(uint16_t));
"""

MARKS = {
    "k-leading": "cache_k - h_kv * d",
    "k-trailing": "cache_k + l * h_kv * d",
    "v-leading": "cache_v - h_kv * d",
    "v-trailing": "cache_v + l * h_kv * d",
}

MARKING = """\
    for (size_t i = 0; i < h_kv * d; i++)
        (@ROW@)[i] = 0x1234;
"""

SCRIBBLING = """\
    if (++calls == 1) {
        size_t row = h_kv * d, rows = m * row;
        memset((void *)q, 0xAB, m * h * d * sizeof(uint16_t));
        memset((void *)k_new, 0xAB, rows * sizeof(uint16_t));
        memset((void *)v_new, 0xAB, rows * sizeof(uint16_t));
        memset(cache_k - rows, 0xAB, (rows + (l - m) * row) * sizeof(uint16_t));
        memset(cache_v - rows, 0xAB, (rows + (l - m) * row) * sizeof(uint16_t));
        memset(cache_k + l * row, 0xAB, rows * sizeof(uint16_t));
        memset(cache_v + l * row, 0xAB, rows * sizeof(uint16_t));
    }
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

PLAIN = (
    COPY
    + """\
    size_t cached = l - m, group = h / h_kv;
    float scale = 1.0f / sqrtf((float)d), *w = malloc(l * sizeof *w);
    if (w == NULL)
        abort();
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++) {
            size_t g = j / group, n = cached + i + 1;
            const uint16_t *qr = &q[(i * h + j) * d];
            float top = -INFINITY, sum = 0.0f;
            for (size_t t = 0; t < n; t++) {
                float dot = 0.0f;
                for (size_t e = 0; e < d; e++)
                    dot += widened(qr[e]) * widened(cache_k[(t * h_kv + g) * d + e]);
                w[t] = dot * scale;
                top = w[t] > top ? w[t] : top;
            }
            for (size_t t = 0; t < n; t++) {
                w[t] = expf(w[t] - top);
                sum += w[t];
            }
            for (size_t e = 0; e < d; e++) {
                float acc = 0.0f;
                for (size_t t = 0; t < n; t++)
                    acc += w[t] * widened(cache_v[(t * h_kv + g) * d + e]);
                out[(i * h + j) * d + e] = rounded(acc / sum);
            }
        }
    free(w);
"""
)

DIMENSIONS = """\
    memset(out, 0, m * h * d * sizeof(uint16_t));
    out[0] = (uint16_t)m;
    out[1] = (uint16_t)l;
    out[2] = (uint16_t)h;
    out[3] = (uint16_t)h_kv;
    out[4] = (uint16_t)d;
"""

# External names a kernel may define; each is the name of a static of the program.
COLLIDING = """\
int fail, digits, byte_size, mix, draw_base, draw_patterns, fill_output;
int check_value, report_open, emit, check_ranges, times;
"""

# name: (file-scope text, body of the kernel)
STUBS = {
    "copy": ("", COPY),
    "silent": ("", ""),
    "scribbling": ("static int calls;", COPY + SCRIBBLING),
    "plain": (HELPERS, PLAIN),
    "counting": ("", '    fputs("call\\n", stderr);\n' + COPY),
    "printing": ("", '    puts("kernel says hello");\n' + COPY),
    "dimensions": ("", DIMENSIONS),
    "colliding": (COLLIDING, COPY),
    "hanging": ("", "    for (;;)\n        sleep(1);\n"),
    "aborting": (
        "static int calls;",
        "    if (++calls == 2)\n        abort();\n" + COPY,
    ),
    **{name: ("", MARKING.replace("@ROW@", row)) for name, row in MARKS.items()},
}

# Compares the program's check function with the header's over two ranges, and prints
# its value over five ranges of one buffer.
CRC_DRIVER = """\
#define main program_main
#include "@PROGRAM@"
#undef main

@PROTOTYPE_BODY@

int main(void)
{
    unsigned char bytes[300];
    struct byte_range parts[5];
    size_t a, b;

    for (a = 0; a < sizeof bytes; a++)
        bytes[a] = (unsigned char)(a * 37 + 11);
    for (a = 0; a <= 64; a++)
        for (b = 0; a + b <= sizeof bytes; b += 1 + b / 3) {
            parts[0].data = bytes;
            parts[0].bytes = a;
            parts[1].data = bytes + a;
            parts[1].bytes = b;
            if (check_ranges(parts, 2) != check_value(bytes, a, bytes + a, b))
                return 1;
        }
    for (a = 0; a < 5; a++) {
        parts[a].data = bytes + 60 * a;
        parts[a].bytes = 60 - 7 * a;
    }
    printf("%lu\\n", (unsigned long)check_ranges(parts, 5));
    return 0;
}
"""


class Inputs(NamedTuple):
    q: np.ndarray
    k_new: np.ndarray
    v_new: np.ndarray
    cached_k: np.ndarray
    cached_v: np.ndarray


def expected_inputs(shape, seed, draw):
    m, l, h, h_kv, d = shape
    cached = l - m
    sizes = [
        m * h * d,
        m * h_kv * d,
        m * h_kv * d,
        cached * h_kv * d,
        cached * h_kv * d,
    ]
    # The same generator sequence: indices 0 .. N - 1 of the draw, bits = 8.
    sequence = draw_inputs("elementwise_add", (1, sum(sizes)), seed=seed, draw=draw)[0]
    parts = np.split(sequence.ravel(), np.cumsum(sizes)[:-1])
    return Inputs(
        parts[0].reshape(m, h, d),
        parts[1].reshape(m, h_kv, d),
        parts[2].reshape(m, h_kv, d),
        parts[3].reshape(cached, h_kv, d),
        parts[4].reshape(cached, h_kv, d),
    )


def allocation(shape, cached_rows):
    m, l, _, h_kv, d = shape
    rows = np.full((l + 2 * m, h_kv, d), FILL, np.uint16)
    rows[m : m + l - m] = cached_rows
    return rows


def packed_check(shape, inputs):
    data = b"".join(
        array.tobytes()
        for array in (
            inputs.q,
            inputs.k_new,
            inputs.v_new,
            allocation(shape, inputs.cached_k),
            allocation(shape, inputs.cached_v),
        )
    )
    return struct.pack("=I", zlib.crc32(data))


def unwritten(shape, inputs):
    out = np.full(inputs.q.shape, FILL, np.uint16)
    return out, allocation(shape, inputs.cached_k), allocation(shape, inputs.cached_v)


def copied(shape, inputs):
    m, l = shape[:2]
    _, cache_k, cache_v = unwritten(shape, inputs)
    cache_k[l : l + m] = inputs.k_new
    cache_v[l : l + m] = inputs.v_new
    return inputs.q.copy(), cache_k, cache_v


def marked(name):
    def output(shape, inputs):
        m, l = shape[:2]
        result = unwritten(shape, inputs)
        row = m - 1 if name.endswith("leading") else m + l
        result[1 if name.startswith("k") else 2][row] = MARK
        return result

    return output


def scribbled(shape, inputs):
    m, l = shape[:2]
    out, cache_k, cache_v = copied(shape, inputs)
    for cache in (cache_k, cache_v):
        cache[:l] = SCRIBBLE
        cache[l + m :] = SCRIBBLE
    return out, cache_k, cache_v


def expected_blocks(output, shape, draws, seed):
    blocks = []
    for draw in range(draws):
        inputs = expected_inputs(shape, seed, draw)
        arrays = output(shape, inputs)
        blocks.append(
            (packed_check(shape, inputs), b"".join(a.tobytes() for a in arrays))
        )
    return blocks


def expected_report(output, shape, draws, seed):
    blocks = expected_blocks(output, shape, draws, seed)
    return b"".join(check + block for check, block in blocks) + END


def report_length(shape, draws):
    m, l, h, h_kv, d = shape
    return draws * (4 + 2 * m * h * d + 4 * (l + 2 * m) * h_kv * d) + 4


def split(report, shape, draws):
    """Cut a complete report by lengths that follow from the dimensions and ``draws``."""
    m, l, h, h_kv, d = shape
    assert len(report) == report_length(shape, draws)
    assert report.endswith(END)
    size = (len(report) - len(END)) // draws
    out_end = 4 + 2 * m * h * d
    cache_bytes = 2 * (l + 2 * m) * h_kv * d
    blocks = []
    for draw in range(draws):
        block = report[draw * size : (draw + 1) * size]
        arrays = (
            block[4:out_end],
            block[out_end : out_end + cache_bytes],
            block[out_end + cache_bytes :],
        )
        out, cache_k, cache_v = (np.frombuffer(a, np.uint16) for a in arrays)
        blocks.append(
            (
                block[:4],
                out.reshape(m, h, d),
                cache_k.reshape(l + 2 * m, h_kv, d),
                cache_v.reshape(l + 2 * m, h_kv, d),
            )
        )
    return blocks


def compile_stub(directory, stem, text, flags):
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
    return path


@pytest.fixture(scope="session")
def toolchain(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    return tmp_path_factory.mktemp("bf16_verification_sdpa_kv_cache")


@pytest.fixture(scope="session")
def executable(toolchain):
    built = {}

    def build(name, flags=O2):
        if (name, flags) not in built:
            file_scope, body = STUBS[name]
            text = KERNEL.replace("@GLOBALS@", file_scope).replace("@BODY@", body)
            signature = sdpa_kv_cache_bf16_contract.PROTOTYPE.removesuffix(";")
            text = text.replace("@SIGNATURE@", signature)
            stem = f"{name}-{len(built)}"
            built[name, flags] = compile_stub(toolchain, stem, text, flags)
        return built[name, flags]

    return build


def verify(path, shape, draws, seed, timeout_s=RUN_TIMEOUT, stdin_data=None):
    arguments = [str(value) for value in (*shape, draws, seed)]
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
    text = PROGRAM.read_bytes().decode("ascii")
    lines = text.splitlines()
    assert sdpa_kv_cache_bf16_contract.PROTOTYPE in lines
    assert '#define PROGRAM "bf16_verification_sdpa_kv_cache"' in lines
    assert lines.index("#define _POSIX_C_SOURCE 200809L") < lines.index(
        '#include "bf16_verification.h"'
    )
    assert "math.h" not in text
    assert re.search(r"\bfloat\b", text) is None
    assert "-lm" not in text
    assert "stdin" not in text and "getenv" not in text and "fopen" not in text


def test_check_function_agrees_with_the_header_and_with_zlib(toolchain):
    signature = sdpa_kv_cache_bf16_contract.PROTOTYPE.removesuffix(";")
    text = CRC_DRIVER.replace("@PROGRAM@", PROGRAM.as_posix())
    text = text.replace("@PROTOTYPE_BODY@", signature + "\n{\n}\n")
    source = toolchain / "crc_driver.c"
    source.write_text(text, encoding="ascii", newline="\n")
    path = toolchain / "crc_driver"
    result = clang_build.build(
        (source,), path, timeout_s=BUILD_TIMEOUT, flags=("-std=c99", "-O2")
    )
    assert result.ok, result.log
    run = local_run.run((path,), timeout_s=RUN_TIMEOUT)
    assert run.returncode == 0, run
    data = bytes((a * 37 + 11) % 256 for a in range(300))
    five = b"".join(data[60 * a : 60 * a + 60 - 7 * a] for a in range(5))
    assert run.stdout == f"{zlib.crc32(five)}\n".encode("ascii")


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("shape", SHAPES)
def test_check_values_and_fills_agree_with_the_generator(executable, shape, seed):
    m, l = shape[:2]
    run = verify(executable("silent"), shape, 2, seed)
    assert_report(run, expected_report(unwritten, shape, 2, seed))
    for draw, (check, out, cache_k, cache_v) in enumerate(split(run.stdout, shape, 2)):
        inputs = expected_inputs(shape, seed, draw)
        assert check == packed_check(shape, inputs)
        assert (out == FILL).all()
        for cache, cached in ((cache_k, inputs.cached_k), (cache_v, inputs.cached_v)):
            assert (cache[:m] == FILL).all()
            np.testing.assert_array_equal(cache[m : m + l - m], cached)
            assert (cache[l:] == FILL).all()


@pytest.mark.parametrize("seed", [0, 2**64 - 1])
@pytest.mark.parametrize("shape", SHAPES)
def test_conforming_cache_write_lands_at_rows_p_onwards(executable, shape, seed):
    m, l = shape[:2]
    run = verify(executable("copy"), shape, 3, seed)
    assert_report(run, expected_report(copied, shape, 3, seed))
    for draw, (_, out, cache_k, cache_v) in enumerate(split(run.stdout, shape, 3)):
        inputs = expected_inputs(shape, seed, draw)
        np.testing.assert_array_equal(out, inputs.q)
        np.testing.assert_array_equal(cache_k[l : l + m], inputs.k_new)
        np.testing.assert_array_equal(cache_v[l : l + m], inputs.v_new)
        np.testing.assert_array_equal(cache_k[m:l], inputs.cached_k)
        np.testing.assert_array_equal(cache_v[m:l], inputs.cached_v)
        for cache in (cache_k, cache_v):
            assert (cache[:m] == FILL).all()
            assert (cache[l + m :] == FILL).all()


@pytest.mark.parametrize("name", MARKS)
@pytest.mark.parametrize("shape", [(1, 1, 1, 1, 1), (1, 4, 4, 1, 2), (2, 5, 4, 2, 3)])
def test_guard_rows_are_reported_at_their_offsets(executable, name, shape):
    run = verify(executable(name), shape, 2, 7)
    assert_report(run, expected_report(marked(name), shape, 2, 7))
    for _, _, cache_k, cache_v in split(run.stdout, shape, 2):
        reported = np.concatenate([cache_k.ravel(), cache_v.ravel()])
        assert (reported == MARK).sum() == shape[3] * shape[4]


@pytest.mark.parametrize("shape", [(2, 5, 4, 2, 3), (3, 3, 4, 1, 2), (1, 4, 4, 1, 2)])
def test_inputs_and_fills_are_restored_before_every_call(executable, shape):
    run = verify(executable("scribbling"), shape, 3, 11)
    first = expected_blocks(scribbled, shape, 1, 11)
    later = expected_blocks(copied, shape, 3, 11)[1:]
    expected = b"".join(check + block for check, block in first + later) + END
    assert_report(run, expected)
    second = split(run.stdout, shape, 3)[1]
    assert second[0] == packed_check(shape, expected_inputs(shape, 11, 1))
    m, l = shape[:2]
    for cache in second[2:]:
        assert (cache[:m] == FILL).all()
        assert (cache[l + m :] == FILL).all()


def reference(shape, inputs):
    m, l, h, h_kv, d = shape
    cached = l - m

    def wide(array, rows):
        return widen(array.ravel().copy()).reshape(rows, -1, d)

    q = wide(inputs.q, m)
    k = wide(np.concatenate([inputs.cached_k, inputs.k_new]), l)
    v = wide(np.concatenate([inputs.cached_v, inputs.v_new]), l)
    mask = np.arange(l)[None, :] > (cached + np.arange(m))[:, None]
    result = np.empty((m, h, d))
    for j in range(h):
        g = j // (h // h_kv)
        scores = q[:, j, :] @ k[:, g, :].T / math.sqrt(d)
        scores[mask] = -np.inf
        weights = np.exp(scores - scores.max(axis=1, keepdims=True))
        weights /= weights.sum(axis=1, keepdims=True)
        result[:, j, :] = weights @ v[:, g, :]
    return result


@pytest.mark.parametrize("flags", [O0, O2], ids=["O0", "O2"])
@pytest.mark.parametrize("shape", [(3, 7, 4, 2, 8), (1, 9, 8, 2, 16), (4, 4, 4, 4, 8)])
def test_output_of_a_plain_bf16_kernel_meets_a_float64_evaluation(
    executable, flags, shape
):
    draws, seed = 2, 12345
    run = verify(executable("plain", flags), shape, draws, seed)
    assert run.returncode == 0, run
    for draw, (check, out, cache_k, cache_v) in enumerate(
        split(run.stdout, shape, draws)
    ):
        inputs = expected_inputs(shape, seed, draw)
        assert check == packed_check(shape, inputs)
        _, expected_k, expected_v = copied(shape, inputs)
        np.testing.assert_array_equal(cache_k, expected_k)
        np.testing.assert_array_equal(cache_v, expected_v)
        output = widen(out.ravel().copy()).reshape(out.shape)
        # A loose margin of this test (bf16 rounding of float results), not a tolerance.
        np.testing.assert_allclose(output, reference(shape, inputs), rtol=0, atol=2**-6)


def test_one_kernel_call_per_draw(executable):
    run = verify(executable("counting"), SHAPE, 4, 7)
    assert_report(run, expected_report(copied, SHAPE, 4, 7))
    assert run.stderr.count(b"call\n") == 4


def test_kernel_output_arrives_on_standard_error(executable):
    run = verify(executable("printing"), SHAPE, 2, 7)
    assert_report(run, expected_report(copied, SHAPE, 2, 7))
    assert run.stderr.count(b"kernel says hello\n") == 2
    assert b"hello" not in run.stdout


@pytest.mark.parametrize("shape", [(2, 5, 4, 2, 3), (1, 1, 5, 5, 1), (3, 9, 6, 3, 2)])
def test_dimensions_reach_the_kernel(executable, shape):
    m, l, h, h_kv, d = shape
    run = verify(executable("dimensions"), shape, 2, 7)
    assert run.returncode == 0, run
    expected = [m, l, h, h_kv, d] + [0] * (m * h * d - 5)
    for _, out, _, _ in split(run.stdout, shape, 2):
        assert out.ravel().tolist() == expected


def test_kernel_may_define_the_names_of_the_program(executable):
    run = verify(executable("colliding"), SHAPE, 2, 7)
    assert_report(run, expected_report(copied, SHAPE, 2, 7))


def test_standard_input_is_not_read(executable):
    quiet = verify(executable("copy"), SHAPE, 2, 7)
    fed = verify(executable("copy"), SHAPE, 2, 7, stdin_data=b"junk")
    assert_report(quiet, expected_report(copied, SHAPE, 2, 7))
    assert_report(fed, quiet.stdout)


@pytest.mark.parametrize("shape", [(3, 5, 6, 3, 2), (1, 1, 1, 1, 1), (2, 7, 4, 1, 3)])
def test_report_length_follows_from_the_dimensions_and_draws(executable, shape):
    for draws in (1, 2, 5):
        run = verify(executable("copy"), shape, draws, 9)
        assert run.returncode == 0, run
        assert len(run.stdout) == report_length(shape, draws)
        assert run.stdout.endswith(END)


def test_kernel_that_never_returns_leaves_the_first_check_value(executable):
    run = verify(executable("hanging"), SHAPE, 2, 7, timeout_s=2)
    assert run.timed_out is True
    assert run.returncode is None
    assert run.stdout == packed_check(SHAPE, expected_inputs(SHAPE, 7, 0))


def test_kernel_that_aborts_leaves_the_report_written_so_far(executable):
    run = verify(executable("aborting"), SHAPE, 3, 7)
    assert run.timed_out is False
    assert run.returncode == -signal.SIGABRT
    first, second = expected_blocks(copied, SHAPE, 2, 7)
    assert run.stdout == first[0] + first[1] + second[0]


GOOD = ("2", "5", "4", "2", "3", "2", "7")
ARGUMENT = {"m": 0, "l": 1, "h": 2, "h_kv": 3, "d": 4, "draws": 5, "seed": 6}
DIMENSION_NAMES = ("m", "l", "h", "h_kv", "d")

BAD_VALUES = (
    [(name, v) for name in DIMENSION_NAMES for v in ["0", "", "-2", "+2", "2x", " 2"]]
    + [(name, v) for name in DIMENSION_NAMES for v in ["2 ", "02", "00", "2" * 30]]
    + [(name, "18446744073709551616") for name in DIMENSION_NAMES]
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
    "four-of-the-two-operand-kinds": ("5", "6", "2", "7"),
    "five-of-gemm-and-rope": ("3", "2", "4", "2", "7"),
    "six": GOOD[:6],
    "eight": (*GOOD, "1"),
}

# (m, l, h, h_kv, d) that pass the argument rules and break a rule between dimensions.
CROSS = {
    "l-below-m": ((3, 2, 4, 2, 3), b"l: "),
    "l-one-below-m-two": ((2, 1, 1, 1, 1), b"l: "),
    "h-3-of-h_kv-2": ((2, 5, 3, 2, 3), b"h: "),
    "h-1-of-h_kv-2": ((2, 5, 1, 2, 3), b"h: "),
    "h-6-of-h_kv-4": ((1, 1, 6, 4, 1), b"h: "),
}

# Dimensions that pass the command line and cannot be held or allocated, with the subject.
TOO_LARGE = {
    "q-elements": ((2**33, 2**33, 2**32, 1, 1), b"sizes"),
    "q-bytes": ((2**63, 2**63, 1, 1, 1), b"sizes"),
    "rows": ((2**62, 2**63, 1, 1, 1), b"sizes"),
    "cache-elements": ((1, 2**40, 1, 1, 2**30), b"sizes"),
    "cache-bytes": ((1, 2**63, 1, 1, 1), b"sizes"),
    "draw-elements": ((1, 2**62 + 1, 2**63 - 1, 1, 1), b"sizes"),
    "q-not-allocatable": ((1, 1, 2**40, 1, 2**16), b"malloc"),
    "cache-not-allocatable": ((1, 2**56, 1, 1, 1), b"malloc"),
}


@pytest.mark.parametrize(("shape", "subject"), TOO_LARGE.values(), ids=TOO_LARGE.keys())
def test_arrays_that_cannot_be_held_are_refused(executable, shape, subject):
    run = verify(executable("counting"), shape, 1, 0)
    assert_refused(run, MEMORY, subject + b": ")


@pytest.mark.parametrize(("shape", "subject"), CROSS.values(), ids=CROSS.keys())
def test_dimensions_that_break_a_rule_between_them_are_refused(
    executable, shape, subject
):
    run = verify(executable("counting"), shape, 1, 0)
    assert_refused(run, COMMAND_LINE, subject)


@pytest.mark.parametrize("arguments", BAD_COUNTS.values(), ids=BAD_COUNTS.keys())
def test_wrong_number_of_arguments_is_refused(executable, arguments):
    run = local_run.run((executable("counting"), *arguments), timeout_s=RUN_TIMEOUT)
    assert_refused(run, COMMAND_LINE, b"usage: ")
    assert b"<m> <l> <h> <h_kv> <d> <draws> <seed>" in run.stderr


@pytest.mark.parametrize(("name", "value"), BAD_VALUES, ids=BAD_VALUE_IDS)
def test_malformed_argument_is_refused(executable, name, value):
    arguments = list(GOOD)
    arguments[ARGUMENT[name]] = value
    run = local_run.run((executable("counting"), *arguments), timeout_s=RUN_TIMEOUT)
    assert_refused(run, COMMAND_LINE, name.encode("ascii") + b": ")


def test_good_command_line_of_the_refusal_tests_is_accepted(executable):
    run = local_run.run((executable("counting"), *GOOD), timeout_s=RUN_TIMEOUT)
    assert_report(run, expected_report(copied, SHAPE, 2, 7))
