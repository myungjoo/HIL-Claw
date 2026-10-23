import os
import shutil

import numpy as np
import pytest

from hilclaw.local_run import run
from hilclaw.model_build import build_kernel_library, build_model_program

BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60
END = b"end\n"
NAN_BITS = 0x7FC00000

PRODUCT = """\
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            float sum = @START@;

            for (p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
"""

KERNEL = """\
#include <stddef.h>
#include <stdio.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
@BODY@}
"""

KERNELS = {
    "plain": PRODUCT.replace("@START@", "0.0f"),
    "plus_one": PRODUCT.replace("@START@", "1.0f"),
    "printing": '    puts("kernel says hello");\n    fflush(stdout);\n'
    + PRODUCT.replace("@START@", "0.0f"),
    "unwritten": "    (void)m; (void)k; (void)n; (void)a; (void)b; (void)c;\n",
}

NO_ENTRY = "int hilclaw_other(int x)\n{\n    return x + 1;\n}\n"


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the model program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("model")
    program = directory / "model_program"
    result = build_model_program(program, timeout_s=BUILD_TIMEOUT, flags=("-O2",))
    assert result.ok, result.log
    libraries = {}

    def library(name):
        if name not in libraries:
            text = (
                NO_ENTRY
                if name == "no_entry"
                else KERNEL.replace("@BODY@", KERNELS[name])
            )
            source = directory / f"{name}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            output = directory / f"lib{name}.so"
            result = build_kernel_library(
                source, output, timeout_s=BUILD_TIMEOUT, flags=("-O2",)
            )
            assert result.ok, result.log
            libraries[name] = str(output)
        return libraries[name]

    return program, library


def matrices(m, k, n, seed):
    generator = np.random.default_rng(seed)
    a = generator.integers(-4, 5, size=(m, k)).astype(np.float32)
    b = generator.integers(-4, 5, size=(k, n)).astype(np.float32)
    return a, b


def call_bytes(index, a, b):
    m, k = a.shape
    n = b.shape[1]
    header = np.array([index, m, k, n], dtype=np.uint64).tobytes()
    return header + a.astype(np.float32).tobytes() + b.astype(np.float32).tobytes()


def input_bytes(calls):
    body = b"".join(call_bytes(index, a, b) for index, a, b in calls)
    return np.array([len(calls)], dtype=np.uint64).tobytes() + body


def start(built, tmp_path, data, names):
    program, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(data)
    return run(
        [program, str(path), *(library(name) for name in names)], timeout_s=RUN_TIMEOUT
    )


def expected(*outputs):
    return b"".join(np.asarray(c, dtype=np.float32).tobytes() for c in outputs) + END


def assert_failed(result, status, text):
    assert result.returncode == status, result.stderr
    assert not result.stdout.endswith(END)
    assert result.stdout == b""
    assert result.stderr.startswith(b"model_program: ")
    assert result.stderr.count(b"\n") == 1 and result.stderr.endswith(b"\n")
    assert text in result.stderr


def test_one_kernel_one_call(built, tmp_path):
    a, b = matrices(3, 4, 5, 1)
    result = start(built, tmp_path, input_bytes([(0, a, b)]), ["plain"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected(a @ b)
    assert result.stderr == b""


def test_two_kernels_of_one_symbol_stay_apart(built, tmp_path):
    a, b = matrices(2, 3, 4, 2)
    data = input_bytes([(0, a, b), (1, a, b)])
    result = start(built, tmp_path, data, ["plain", "plus_one"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected(a @ b, a @ b + 1)
    swapped = start(built, tmp_path, data, ["plus_one", "plain"])
    assert swapped.stdout == expected(a @ b + 1, a @ b)


def test_several_calls_of_different_shapes_in_order(built, tmp_path):
    shapes = [(1, 1, 1), (1, 7, 3), (5, 2, 1), (4, 6, 8)]
    calls = [(i % 2, *matrices(*shape, 10 + i)) for i, shape in enumerate(shapes)]
    result = start(built, tmp_path, input_bytes(calls), ["plain", "plus_one"])
    assert result.returncode == 0, result.stderr
    outputs = [a @ b + index for index, a, b in calls]
    assert result.stdout == expected(*outputs)
    assert (
        len(result.stdout) == sum(4 * a.shape[0] * b.shape[1] for _, a, b in calls) + 4
    )


def test_a_library_index_used_twice(built, tmp_path):
    first = matrices(2, 2, 2, 3)
    second = matrices(3, 1, 2, 4)
    data = input_bytes([(1, *first), (0, *second), (1, *second)])
    result = start(built, tmp_path, data, ["plain", "plus_one"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected(
        first[0] @ first[1] + 1, second[0] @ second[1], second[0] @ second[1] + 1
    )


def test_what_a_kernel_prints_is_not_part_of_the_report(built, tmp_path):
    a, b = matrices(2, 3, 2, 5)
    result = start(built, tmp_path, input_bytes([(0, a, b), (0, a, b)]), ["printing"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected(a @ b, a @ b)
    assert result.stderr == b"kernel says hello\n" * 2


def test_an_unwritten_output_shows_the_nan_fill(built, tmp_path):
    a, b = matrices(2, 3, 4, 6)
    result = start(built, tmp_path, input_bytes([(0, a, b)]), ["unwritten"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == np.full(8, NAN_BITS, dtype=np.uint32).tobytes() + END


@pytest.mark.parametrize("arguments", [[], ["input.bin"]])
def test_command_line_without_a_library(built, tmp_path, arguments):
    program, _ = built
    (tmp_path / "input.bin").write_bytes(input_bytes([(0, *matrices(1, 1, 1, 0))]))
    result = run(
        [program, *(str(tmp_path / argument) for argument in arguments)],
        timeout_s=RUN_TIMEOUT,
    )
    assert_failed(result, 2, b"usage")


def test_missing_input_file(built, tmp_path):
    program, library = built
    result = run(
        [program, str(tmp_path / "absent.bin"), library("plain")], timeout_s=RUN_TIMEOUT
    )
    assert_failed(result, 5, b"cannot be opened")


def test_input_file_that_is_a_directory(built, tmp_path):
    program, library = built
    result = run([program, str(tmp_path), library("plain")], timeout_s=RUN_TIMEOUT)
    assert result.returncode == 5, result.stderr
    assert result.stdout == b""
    assert result.stderr.count(b"\n") == 1


def test_number_of_calls_zero(built, tmp_path):
    data = np.array([0], dtype=np.uint64).tobytes()
    assert_failed(start(built, tmp_path, data, ["plain"]), 5, b"number of calls is 0")


@pytest.mark.parametrize("cut", [0, 1, 7, 8, 9, 39, 40, 41, 8 + 32 + 4 * 6 - 1])
def test_short_file(built, tmp_path, cut):
    a, b = matrices(2, 2, 1, 7)
    data = input_bytes([(0, a, b)])
    assert len(data) == 8 + 32 + 4 * 6
    assert_failed(start(built, tmp_path, data[:cut], ["plain"]), 5, b"too short")


def test_short_file_after_a_complete_call_runs_nothing(built, tmp_path):
    a, b = matrices(2, 2, 2, 8)
    data = np.array([2], dtype=np.uint64).tobytes() + call_bytes(0, a, b)
    assert_failed(start(built, tmp_path, data, ["plain"]), 5, b"too short for a call")


@pytest.mark.parametrize(
    "extra", [b"\x00", b"\x00" * 8, call_bytes(0, *matrices(1, 1, 1, 9))]
)
def test_trailing_bytes(built, tmp_path, extra):
    data = input_bytes([(0, *matrices(1, 2, 1, 9))]) + extra
    assert_failed(
        start(built, tmp_path, data, ["plain"]), 5, b"bytes follow the last call"
    )


@pytest.mark.parametrize("index", [2, 3, 2**64 - 1])
def test_index_out_of_range(built, tmp_path, index):
    a, b = matrices(1, 1, 1, 10)
    data = input_bytes([(0, a, b), (index, a, b)])
    assert_failed(
        start(built, tmp_path, data, ["plain", "plus_one"]), 5, b"out of range"
    )


@pytest.mark.parametrize("position", [1, 2, 3])
def test_zero_dimension(built, tmp_path, position):
    header = [0, 1, 1, 1]
    header[position] = 0
    data = (
        np.array([1], dtype=np.uint64).tobytes()
        + np.array(header, dtype=np.uint64).tobytes()
        + np.ones(4, dtype=np.float32).tobytes()
    )
    assert_failed(start(built, tmp_path, data, ["plain"]), 5, b"a dimension is 0")


@pytest.mark.parametrize(
    "shape",
    [(2**62, 1, 1), (1, 2**62, 1), (1, 1, 2**62), (2**40, 2**40, 1), (2**31, 1, 1)],
)
def test_size_that_cannot_be_in_the_file(built, tmp_path, shape):
    data = (
        np.array([1], dtype=np.uint64).tobytes()
        + np.array([0, *shape], dtype=np.uint64).tobytes()
        + np.ones(4, dtype=np.float32).tobytes()
    )
    assert_failed(
        start(built, tmp_path, data, ["plain"]), 5, b"too short for the matrices"
    )


def test_library_path_that_does_not_exist(built, tmp_path):
    program, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(input_bytes([(0, *matrices(1, 1, 1, 11))]))
    result = run(
        [program, str(path), library("plain"), str(tmp_path / "libabsent.so")],
        timeout_s=RUN_TIMEOUT,
    )
    assert_failed(result, 6, b"library 1: cannot be loaded")


def test_library_is_loaded_before_the_input_file_is_read(built, tmp_path):
    program, _ = built
    result = run(
        [program, str(tmp_path / "absent.bin"), str(tmp_path / "libabsent.so")],
        timeout_s=RUN_TIMEOUT,
    )
    assert_failed(result, 6, b"library 0: cannot be loaded")


def test_file_that_is_not_a_library(built, tmp_path):
    program, _ = built
    fake = tmp_path / "libfake.so"
    fake.write_bytes(b"not a shared library\n")
    path = tmp_path / "input.bin"
    path.write_bytes(input_bytes([(0, *matrices(1, 1, 1, 12))]))
    result = run([program, str(path), str(fake)], timeout_s=RUN_TIMEOUT)
    assert_failed(result, 6, b"library 0: cannot be loaded")


def test_library_without_the_entry_point(built, tmp_path):
    data = input_bytes([(0, *matrices(1, 1, 1, 13))])
    result = start(built, tmp_path, data, ["plain", "no_entry"])
    assert_failed(result, 6, b"library 1: has no hilclaw_gemm")


def shell(built, tmp_path, script, data):
    program, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(data)
    return run(
        ["sh", "-c", script, "sh", str(program), str(path), library("plain")],
        timeout_s=RUN_TIMEOUT,
    )


def test_output_array_that_cannot_be_allocated(built, tmp_path):
    side = 2**15
    a = np.ones((side, 1), dtype=np.float32)
    b = np.ones((1, side), dtype=np.float32)
    script = 'ulimit -v 262144 && exec "$1" "$2" "$3"'
    result = shell(built, tmp_path, script, input_bytes([(0, a, b)]))
    assert_failed(result, 3, b"cannot allocate the operands")


def test_closed_standard_output(built, tmp_path):
    data = input_bytes([(0, *matrices(1, 1, 1, 14))])
    result = shell(built, tmp_path, 'exec "$1" "$2" "$3" >&-', data)
    assert_failed(result, 4, b"descriptors")


@pytest.mark.skipif(not os.path.exists("/dev/full"), reason="no /dev/full")
def test_report_that_cannot_be_written(built, tmp_path):
    data = input_bytes([(0, *matrices(1, 1, 1, 15))])
    result = shell(built, tmp_path, 'exec "$1" "$2" "$3" > /dev/full', data)
    assert_failed(result, 4, b"cannot write to the standard output")
