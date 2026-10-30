import os
import shutil
import signal
import struct
from pathlib import Path

import numpy as np
import pytest

import hilclaw.harness
from hilclaw import (
    clang_build,
    elementwise_add_bf16_contract,
    local_run,
    rmsnorm_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.harness.bf16_verification_arrays import (
    EPS_BITS,
    check_value,
    count_failures,
    draw_inputs,
    reference,
    widen,
)

DIRECTORY = Path(hilclaw.harness.__file__).parent
HEADER = DIRECTORY / "bf16_verification.h"

STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
O0 = (*STRICT, "-O0")
O2 = (*STRICT, "-O2")
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60

# Documented exit statuses, end mark and fill of the programs.
COMMAND_LINE, MEMORY = 2, 3
END = b"end\n"
FILL = 0x7FC0

# kind: (contract module, first operand, second operand, output, index of the second)
KINDS = {
    "rmsnorm": (rmsnorm_bf16_contract, "x", "w", "y", "j"),
    "elementwise_add": (elementwise_add_bf16_contract, "a", "b", "c", "i * n + j"),
    "swiglu": (swiglu_bf16_contract, "gate", "up", "out", "i * n + j"),
}

SEEDS = [0, 1, 2**63, 2**64 - 1]
SHAPE = (5, 6)
SMALL_SHAPES = [(1, 6), (5, 1), (1, 1), (3, 7)]

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
    (void)n;
    (void)@A@;
    (void)@B@;
    (void)@C@;
@EPS@@BODY@}
"""

COPY_FIRST = """\
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++)
            @C@[i * n + j] = @A@[i * n + j];
"""

COPY_SECOND = """\
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++)
            @C@[i * n + j] = @B@[@SECOND@];
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

PLAIN = {
    "rmsnorm": """\
    for (size_t i = 0; i < m; i++) {
        float sum = 0.0f;
        for (size_t j = 0; j < n; j++)
            sum += widened(@A@[i * n + j]) * widened(@A@[i * n + j]);
        float scale = 1.0f / sqrtf(sum / (float)n + eps);
        for (size_t j = 0; j < n; j++)
            @C@[i * n + j] = rounded(widened(@A@[i * n + j]) * widened(@B@[j]) * scale);
    }
""",
    "elementwise_add": """\
    for (size_t i = 0; i < m * n; i++)
        @C@[i] = rounded(widened(@A@[i]) + widened(@B@[i]));
""",
    "swiglu": """\
    for (size_t i = 0; i < m * n; i++) {
        float g = widened(@A@[i]);
        @C@[i] = rounded(g / (1.0f + expf(-g)) * widened(@B@[i]));
    }
""",
}

FIRST_ROW = """\
    for (size_t j = 0; j < n; j++)
        @C@[j] = @A@[j];
"""

DIMENSIONS = """\
    for (size_t i = 0; i < m * n; i++)
        @C@[i] = 0;
    @C@[0] = (uint16_t)m;
    @C@[1] = (uint16_t)n;
"""

EPS_PATTERN = """\
    uint16_t halves[2];
    memcpy(halves, &eps, sizeof halves);
    for (size_t i = 0; i < m * n; i++)
        @C@[i] = 0;
    @C@[0] = halves[0];
    @C@[1] = halves[1];
"""

CHECKING = (
    """\
    if (m != @M@ || n != @N@)
        abort();
    for (size_t i = 0; i < m * n; i++)
        if (@C@[i] != UINT16_C(0x7FC0))
            abort();
"""
    + COPY_FIRST
)

# External names a kernel may define; each is the name of a static of the header.
COLLIDING = """\
int fail, digits, byte_size, mix, draw_base, draw_patterns, fill_output;
int check_value, report_open, emit;
"""

CALLS = "static int calls;"

# name: (file-scope text, body of the kernel)
STUBS = {
    "copy-first": ("", COPY_FIRST),
    "copy-second": ("", COPY_SECOND),
    "plain": (HELPERS, None),
    "counting": ("", '    fputs("call\\n", stderr);\n' + COPY_FIRST),
    "printing": ("", '    puts("kernel says hello");\n' + COPY_FIRST),
    "checking": ("", CHECKING),
    "dimensions": ("", DIMENSIONS),
    "eps": ("", EPS_PATTERN),
    "silent": ("", ""),
    "first-row": ("", FIRST_ROW),
    "colliding": (COLLIDING, COPY_FIRST),
    "hanging": ("", "    for (;;)\n        sleep(1);\n"),
    "aborting": (CALLS, "    if (++calls == 2)\n        abort();\n" + COPY_FIRST),
}

GOOD = ("5", "6", "2", "7")
ARGUMENT = {"m": 0, "n": 1, "draws": 2, "seed": 3}

BAD_VALUES = (
    [(name, value) for name in "mn" for value in ["0", "", "-1", "+1", "1x", " 1"]]
    + [(name, value) for name in "mn" for value in ["1 ", "01", "00", "1" * 30]]
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
    "three": GOOD[:3],
    "five-of-gemm": ("5", "4", "6", "2", "7"),
    "six": (*GOOD, "1", "1"),
}

# m, n that pass the command line and cannot be held or allocated, with the subject.
TOO_LARGE = {
    "product-overflows": ((2**40, 2**40), b"sizes"),
    "bytes-overflow": ((2**63, 1), b"sizes"),
    "operands-overflow": ((1, 2**63 - 1), b"sizes"),
    "not-allocatable": ((2**29, 2**29), b"malloc"),
}


def inputs(kind, m, n, seed, draw):
    return draw_inputs(kind, (m, n), seed=seed, draw=draw)


def copied_first(kind, first, second):
    return first.copy()


def copied_second(kind, first, second):
    if kind == "rmsnorm":
        return np.tile(second, (first.shape[0], 1))
    return second.copy()


def unwritten(kind, first, second):
    return np.full(first.shape, FILL, np.uint16)


def first_row(kind, first, second):
    output = unwritten(kind, first, second)
    output[0, :] = first[0, :]
    return output


def packed_check(first, second):
    return struct.pack("=I", check_value(first, second))


def expected_blocks(kind, output, m, n, draws, seed):
    blocks = []
    for draw in range(draws):
        first, second = inputs(kind, m, n, seed, draw)
        blocks.append(
            (packed_check(first, second), output(kind, first, second).tobytes())
        )
    return blocks


def expected_report(kind, output, m, n, draws, seed):
    blocks = expected_blocks(kind, output, m, n, draws, seed)
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


def program(kind):
    return DIRECTORY / f"bf16_verification_{kind}.c"


def prefix(kind):
    return f"bf16_verification_{kind}: ".encode("ascii")


@pytest.fixture(scope="session")
def executable(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("bf16_verification_programs")
    built = {}

    def build(kind, name, flags=O2):
        if (kind, name, flags) not in built:
            contract, first, second, output, index = KINDS[kind]
            file_scope, body = STUBS[name]
            if body is None:
                body = PLAIN[kind]
            eps = "    (void)eps;\n" if kind == "rmsnorm" else ""
            text = KERNEL.replace("@GLOBALS@", file_scope).replace("@EPS@", eps)
            text = text.replace("@BODY@", body).replace("@SECOND@", index)
            text = text.replace("@SIGNATURE@", contract.PROTOTYPE.removesuffix(";"))
            for placeholder, value in zip("ABC", (first, second, output), strict=True):
                text = text.replace(f"@{placeholder}@", value)
            text = text.replace("@M@", str(SHAPE[0])).replace("@N@", str(SHAPE[1]))
            stem = f"{kind}-{name}-{len(built)}"
            source = directory / f"{stem}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            path = directory / stem
            result = clang_build.build(
                (program(kind), source),
                path,
                timeout_s=BUILD_TIMEOUT,
                flags=flags,
                trailing_flags=("-lm",),
            )
            assert result.ok, result.log
            built[kind, name, flags] = path
        return built[kind, name, flags]

    return build


def verify(path, m, n, draws, seed, timeout_s=RUN_TIMEOUT):
    arguments = [str(value) for value in (m, n, draws, seed)]
    return local_run.run((path, *arguments), timeout_s=timeout_s)


def assert_report(run, expected):
    assert run.timed_out is False
    assert run.returncode == 0, run
    assert run.stdout == expected


def assert_refused(run, kind, status):
    assert run.timed_out is False
    assert run.returncode == status, run
    assert run.stdout == b""
    assert run.stderr.startswith(prefix(kind))
    assert run.stderr.endswith(b"\n")
    assert run.stderr.count(b"\n") == 1


@pytest.mark.parametrize("kind", KINDS)
def test_program_is_ascii_and_declares_the_contract_prototype(kind):
    HEADER.read_bytes().decode("ascii")
    lines = program(kind).read_bytes().decode("ascii").splitlines()
    assert KINDS[kind][0].PROTOTYPE in lines
    assert f'#define PROGRAM "bf16_verification_{kind}"' in lines
    assert lines.index("#define _POSIX_C_SOURCE 200809L") < lines.index(
        '#include "bf16_verification.h"'
    )
    assert not any("math.h" in line for line in lines)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("draws", [1, 3])
@pytest.mark.parametrize(
    ("name", "output"), [("copy-first", copied_first), ("copy-second", copied_second)]
)
@pytest.mark.parametrize("kind", KINDS)
def test_check_values_and_outputs_agree_with_the_array_module(
    executable, kind, name, output, draws, seed
):
    m, n = SHAPE
    run = verify(executable(kind, name), m, n, draws, seed)
    assert_report(run, expected_report(kind, output, m, n, draws, seed))
    for draw, (check, block) in enumerate(split(run.stdout, m, n, draws)):
        first, second = inputs(kind, m, n, seed, draw)
        assert check == check_value(first, second)
        operand = first if name == "copy-first" else second
        assert block[0] == operand.flat[0]
        assert block[-1] == operand.flat[-1]
        np.testing.assert_array_equal(block.reshape(m, n), output(kind, first, second))


@pytest.mark.parametrize("shape", SMALL_SHAPES)
@pytest.mark.parametrize("seed", [0, 2**63, 2**64 - 1])
@pytest.mark.parametrize(
    ("name", "output"), [("copy-first", copied_first), ("copy-second", copied_second)]
)
@pytest.mark.parametrize("kind", KINDS)
def test_shapes_with_small_dimensions_agree_with_the_array_module(
    executable, kind, name, output, seed, shape
):
    run = verify(executable(kind, name), *shape, 2, seed)
    assert_report(run, expected_report(kind, output, *shape, 2, seed))


@pytest.mark.parametrize("kind", KINDS)
def test_report_depends_on_the_seed_only(executable, kind):
    def report(seed):
        run = verify(executable(kind, "copy-first"), *SHAPE, 2, seed)
        assert run.returncode == 0, run
        return run.stdout

    assert report(7) == report(7)
    assert len({report(seed) for seed in (*SEEDS, 7, 8)}) == len(SEEDS) + 2


@pytest.mark.parametrize("kind", KINDS)
def test_reported_patterns_lie_in_the_value_sets(executable, kind):
    m, n = 16, 64
    contract = KINDS[kind][0]
    if kind == "swiglu":
        sets = {
            "copy-first": contract.GATE_PATTERNS,
            "copy-second": contract.UP_PATTERNS,
        }
    else:
        sets = {
            "copy-first": contract.INPUT_PATTERNS,
            "copy-second": contract.INPUT_PATTERNS,
        }
    for name, allowed in sets.items():
        run = verify(executable(kind, name), m, n, 2, 11)
        reported = set()
        for _, block in split(run.stdout, m, n, 2):
            reported.update(block.tolist())
        assert reported <= set(allowed)
        large = {pattern for pattern in reported if pattern & 0x7FFF >= 0x3F80}
        if kind == "swiglu" and name == "copy-first":
            assert large
            assert len(reported) > 256
        else:
            assert not large


def test_rmsnorm_passes_the_eps_of_the_record(executable):
    run = verify(executable("rmsnorm", "eps"), *SHAPE, 2, 7)
    assert run.returncode == 0, run
    for _, block in split(run.stdout, *SHAPE, 2):
        assert block[:2].tobytes() == struct.pack("=I", EPS_BITS)
        assert (block[2:] == 0).all()
    eps = struct.unpack("=f", struct.pack("=I", EPS_BITS))[0]
    assert eps == rmsnorm_bf16_contract.EPS
    assert EPS_BITS == 0x3727C5AC


@pytest.mark.parametrize("flags", [O0, O2], ids=["O0", "O2"])
@pytest.mark.parametrize("kind", KINDS)
def test_output_of_a_plain_bf16_kernel_meets_the_float64_reference(
    executable, kind, flags
):
    m, n = SHAPE
    draws, seed = 3, 12345
    run = verify(executable(kind, "plain", flags), m, n, draws, seed)
    assert run.returncode == 0, run
    for draw, (check, block) in enumerate(split(run.stdout, m, n, draws)):
        first, second = inputs(kind, m, n, seed, draw)
        assert check == check_value(first, second)
        output = block.reshape(m, n).copy()
        assert np.isfinite(widen(output)).all()
        # A loose margin of this test (bf16 rounding of float results), not a tolerance.
        expected = reference(kind, first, second)
        assert count_failures(output, expected, rtol=2**-6, atol=2**-7) == (0, 0)


@pytest.mark.parametrize("kind", KINDS)
def test_one_kernel_call_per_draw(executable, kind):
    run = verify(executable(kind, "counting"), *SHAPE, 4, 7)
    assert_report(run, expected_report(kind, copied_first, *SHAPE, 4, 7))
    assert run.stderr.count(b"call\n") == 4


@pytest.mark.parametrize("kind", KINDS)
def test_kernel_output_arrives_on_standard_error(executable, kind):
    run = verify(executable(kind, "printing"), *SHAPE, 2, 7)
    assert_report(run, expected_report(kind, copied_first, *SHAPE, 2, 7))
    assert run.stderr.count(b"kernel says hello\n") == 2
    assert b"hello" not in run.stdout


@pytest.mark.parametrize("kind", KINDS)
def test_arguments_are_passed_and_output_is_filled_before_every_call(executable, kind):
    run = verify(executable(kind, "checking"), *SHAPE, 3, 7)
    assert_report(run, expected_report(kind, copied_first, *SHAPE, 3, 7))


@pytest.mark.parametrize("shape", [(5, 6), (3, 7), (2, 1), (1, 2)])
@pytest.mark.parametrize("kind", KINDS)
def test_dimensions_reach_the_kernel(executable, kind, shape):
    m, n = shape
    run = verify(executable(kind, "dimensions"), m, n, 2, 7)
    assert run.timed_out is False
    assert run.returncode == 0, run
    expected = [m, n] + [0] * (m * n - 2)
    for _, block in split(run.stdout, m, n, 2):
        assert block.tolist() == expected


@pytest.mark.parametrize("kind", KINDS)
def test_unwritten_output_is_reported_as_the_fill(executable, kind):
    run = verify(executable(kind, "silent"), *SHAPE, 2, 7)
    assert_report(run, expected_report(kind, unwritten, *SHAPE, 2, 7))
    for _, block in split(run.stdout, *SHAPE, 2):
        assert (block == FILL).all()


@pytest.mark.parametrize("kind", KINDS)
def test_partly_written_output_holds_no_stale_element(executable, kind):
    run = verify(executable(kind, "first-row"), *SHAPE, 2, 7)
    assert_report(run, expected_report(kind, first_row, *SHAPE, 2, 7))
    m, n = SHAPE
    _, second = split(run.stdout, m, n, 2)[1]
    assert (second[n:] == FILL).all()


@pytest.mark.parametrize("kind", KINDS)
def test_kernel_may_define_the_names_of_the_header(executable, kind):
    run = verify(executable(kind, "colliding"), *SHAPE, 2, 7)
    assert_report(run, expected_report(kind, copied_first, *SHAPE, 2, 7))


@pytest.mark.parametrize("kind", KINDS)
def test_report_length_follows_from_the_dimensions_and_draws(executable, kind):
    m, n = (3, 7)
    for draws in (1, 2, 5):
        run = verify(executable(kind, "copy-second"), m, n, draws, 9)
        assert run.returncode == 0, run
        assert len(run.stdout) == draws * (4 + 2 * m * n) + 4
        assert run.stdout.endswith(END)


@pytest.mark.parametrize("kind", KINDS)
def test_kernel_that_never_returns_leaves_the_first_check_value(executable, kind):
    run = verify(executable(kind, "hanging"), *SHAPE, 2, 7, timeout_s=2)
    assert run.timed_out is True
    assert run.returncode is None
    assert run.stdout == packed_check(*inputs(kind, *SHAPE, 7, 0))


@pytest.mark.parametrize("kind", KINDS)
def test_kernel_that_aborts_leaves_the_report_written_so_far(executable, kind):
    run = verify(executable(kind, "aborting"), *SHAPE, 3, 7)
    assert run.timed_out is False
    assert run.returncode == -signal.SIGABRT
    first, second = expected_blocks(kind, copied_first, *SHAPE, 2, 7)
    assert run.stdout == first[0] + first[1] + second[0]


@pytest.mark.parametrize(("shape", "subject"), TOO_LARGE.values(), ids=TOO_LARGE.keys())
@pytest.mark.parametrize("kind", KINDS)
def test_arrays_that_cannot_be_held_are_refused(executable, kind, shape, subject):
    run = verify(executable(kind, "copy-first"), *shape, 1, 0)
    assert_refused(run, kind, MEMORY)
    assert run.stderr.startswith(prefix(kind) + subject + b": ")


@pytest.mark.parametrize("arguments", BAD_COUNTS.values(), ids=BAD_COUNTS.keys())
@pytest.mark.parametrize("kind", KINDS)
def test_wrong_number_of_arguments_is_refused(executable, kind, arguments):
    run = local_run.run(
        (executable(kind, "copy-first"), *arguments), timeout_s=RUN_TIMEOUT
    )
    assert_refused(run, kind, COMMAND_LINE)
    assert b"<m> <n> <draws> <seed>" in run.stderr


@pytest.mark.parametrize(("name", "value"), BAD_VALUES, ids=BAD_VALUE_IDS)
@pytest.mark.parametrize("kind", KINDS)
def test_malformed_argument_is_refused(executable, kind, name, value):
    arguments = list(GOOD)
    arguments[ARGUMENT[name]] = value
    run = local_run.run(
        (executable(kind, "copy-first"), *arguments), timeout_s=RUN_TIMEOUT
    )
    assert_refused(run, kind, COMMAND_LINE)
    assert run.stderr.startswith(prefix(kind) + name.encode("ascii") + b": ")


@pytest.mark.parametrize("kind", KINDS)
def test_good_command_line_of_the_refusal_tests_is_accepted(executable, kind):
    run = local_run.run((executable(kind, "copy-first"), *GOOD), timeout_s=RUN_TIMEOUT)
    assert_report(run, expected_report(kind, copied_first, 5, 6, 2, 7))
