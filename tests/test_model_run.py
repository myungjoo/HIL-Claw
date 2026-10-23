import os
import shutil
from pathlib import Path, PurePosixPath

import numpy as np
import pytest

from hilclaw import local_run, model_run
from hilclaw.local_run import RunResult
from hilclaw.model_build import build_kernel_library, build_model_program
from hilclaw.model_run import (
    END_MARK,
    ModelProgramResult,
    RunFailed,
    encode_input,
    output_shapes,
    parse_report,
    run_model_program,
)

BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60


def matrices(m, k, n, seed):
    generator = np.random.default_rng(seed)
    a = generator.integers(-4, 5, size=(m, k)).astype(np.float32)
    b = generator.integers(-4, 5, size=(k, n)).astype(np.float32)
    return a, b


def call_bytes(index, a, b):
    m, k = a.shape
    n = b.shape[1]
    header = np.array([index, m, k, n], dtype=np.uint64).tobytes()
    return (
        header + np.ascontiguousarray(a).tobytes() + np.ascontiguousarray(b).tobytes()
    )


def input_bytes(calls):
    body = b"".join(call_bytes(index, a, b) for index, a, b in calls)
    return np.array([len(calls)], dtype=np.uint64).tobytes() + body


def report_of(*arrays):
    return (
        b"".join(np.asarray(x, dtype=np.float32).tobytes() for x in arrays) + END_MARK
    )


def good_call(index=0):
    a, b = matrices(2, 3, 4, index)
    return (index, a, b)


def test_encode_input_matches_hand_made_bytes_for_several_calls():
    a0, b0 = matrices(2, 3, 4, 1)
    a1, b1 = matrices(1, 1, 1, 2)
    a2, b2 = matrices(5, 2, 3, 3)
    fortran = np.asfortranarray(a2)
    assert not fortran.flags.c_contiguous
    calls = [(0, a0, b0), [3, a1, b1], (2**64 - 1, fortran, b2)]
    data = encode_input(calls)
    assert type(data) is bytes
    assert data == input_bytes([(0, a0, b0), (3, a1, b1), (2**64 - 1, a2, b2)])


def test_encode_input_single_call_layout():
    a = np.array([[1, 2]], dtype=np.float32)
    b = np.array([[3], [4]], dtype=np.float32)
    data = encode_input(((7, a, b),))
    words = np.frombuffer(data[:40], dtype=np.uint64).tolist()
    assert words == [1, 7, 1, 2, 1]
    assert np.frombuffer(data[40:], dtype=np.float32).tolist() == [1, 2, 3, 4]


def test_output_shapes():
    calls = [good_call(0), (1, *matrices(3, 5, 1, 4)), (0, *matrices(1, 1, 7, 5))]
    assert output_shapes(calls) == ((2, 4), (3, 1), (1, 7))


def bad_calls():
    a, b = matrices(2, 3, 4, 0)
    return [
        ("text", TypeError, "calls"),
        (b"bytes", TypeError, "calls"),
        (iter([(0, a, b)]), TypeError, "calls"),
        ({0: (0, a, b)}, TypeError, "calls"),
        ([], ValueError, "calls"),
        ([(0, a, b), (0, a)], TypeError, "calls[1]"),
        ([(0, a, b, 1)], TypeError, "calls[0]"),
        ([{"index": 0}], TypeError, "calls[0]"),
        ([(True, a, b)], TypeError, "calls[0]"),
        ([(1.0, a, b)], TypeError, "calls[0]"),
        ([(np.uint64(0), a, b)], TypeError, "calls[0]"),
        ([(0, a, b), (-1, a, b)], ValueError, "calls[1]"),
        ([(2**64, a, b)], ValueError, "calls[0]"),
        ([(0, a.tolist(), b)], TypeError, "calls[0]: a"),
        ([(0, a, b.tolist())], TypeError, "calls[0]: b"),
        ([(0, a.astype(np.float64), b)], ValueError, "calls[0]: a"),
        ([(0, a, b.astype(np.float16))], ValueError, "calls[0]: b"),
        ([(0, a.astype(">f4" if np.little_endian else "<f4"), b)], ValueError, "a"),
        ([(0, a.reshape(-1), b)], ValueError, "calls[0]: a"),
        ([(0, a, b.reshape(1, 3, 4))], ValueError, "calls[0]: b"),
        ([(0, np.zeros((0, 3), np.float32), b)], ValueError, "calls[0]: a"),
        (
            [(0, np.zeros((2, 0), np.float32), np.zeros((0, 4), np.float32))],
            ValueError,
            "a",
        ),
        ([(0, a, np.zeros((3, 0), np.float32))], ValueError, "calls[0]: b"),
        ([(0, a, b), (0, a, a)], ValueError, "calls[1]: inner"),
    ]


@pytest.mark.parametrize("function", [encode_input, output_shapes])
@pytest.mark.parametrize(("calls", "error", "text"), bad_calls())
def test_calls_are_refused(function, calls, error, text):
    with pytest.raises(error) as caught:
        function(calls)
    assert type(caught.value) is error
    assert text in str(caught.value)


def bad_shapes():
    return [
        ("ab", TypeError),
        (b"ab", TypeError),
        (None, TypeError),
        (iter([(1, 1)]), TypeError),
        ((), ValueError),
        ([(1, 1), (1,)], TypeError),
        ([(1, 1, 1)], TypeError),
        ([{1, 2}], TypeError),
        ([(True, 1)], TypeError),
        ([(1, False)], TypeError),
        ([(1.0, 1)], TypeError),
        ([(0, 1)], ValueError),
        ([(1, -2)], ValueError),
    ]


@pytest.mark.parametrize(("shapes", "error"), bad_shapes())
def test_parse_report_refuses_shapes(shapes, error):
    with pytest.raises(error) as caught:
        parse_report(END_MARK, shapes)
    assert type(caught.value) is error
    assert "shapes" in str(caught.value)


class SubBytes(bytes):
    pass


@pytest.mark.parametrize(
    "report",
    [bytearray(END_MARK), memoryview(END_MARK), SubBytes(END_MARK), "end\n", None],
)
def test_parse_report_refuses_non_bytes(report):
    with pytest.raises(TypeError, match="report"):
        parse_report(report, [(1, 1)])


def test_parse_report_complete():
    first = np.arange(6, dtype=np.float32).reshape(2, 3)
    second = np.array([[-1.5]], dtype=np.float32)
    report = report_of(first, second)
    outputs = parse_report(report, [(2, 3), [1, 1]])
    assert len(outputs) == 2
    for output, expected in zip(outputs, (first, second), strict=True):
        assert output.dtype == np.float32
        assert output.shape == expected.shape
        assert np.array_equal(output, expected)
        assert output.flags.owndata
        assert output.flags.writeable


@pytest.mark.parametrize(
    "report",
    [
        report_of(np.zeros((2, 2)))[1:],
        report_of(np.zeros((2, 2))) + b"\0",
        report_of(np.zeros((2, 2)))[:-4] + b"END\n",
        np.zeros((2, 2), np.float32).tobytes() + b"\0" * 4,
        np.zeros((2, 2), np.float32).tobytes(),
        np.zeros((3, 2), np.float32).tobytes(),
        b"",
        END_MARK,
    ],
)
def test_parse_report_incomplete(report):
    assert parse_report(report, [(2, 2)]) is None


def test_parse_report_passes_nan_through():
    values = np.array([[np.nan, 1.0]], dtype=np.float32)
    nan_bits = np.array([0x7FC00001], dtype=np.uint32).view(np.float32)
    values[0, 0] = nan_bits[0]
    (output,) = parse_report(report_of(values), [(1, 2)])
    assert output.view(np.uint32)[0, 0] == 0x7FC00001
    assert output[0, 1] == 1.0


def test_parse_report_does_not_allocate_from_huge_shapes():
    assert parse_report(END_MARK, [(2**40, 2**40)]) is None


class Recorder:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def __call__(self, command, *, timeout_s, cwd=None, env=None):
        self.calls.append((command, timeout_s, cwd, env))
        return self.result


def runner_result(returncode=0, timed_out=False, stdout=b"", stderr=b"err"):
    return RunResult(returncode, timed_out, stdout, stderr, ("x",), 0.25, 42)


@pytest.fixture
def recorder(monkeypatch):
    def install(result):
        recording = Recorder(result)
        monkeypatch.setattr(local_run, "run", recording)
        return recording

    return install


def test_run_with_a_path_program(recorder, tmp_path):
    first = np.array([[1, 2]], dtype=np.float32)
    second = np.array([[3], [4], [5]], dtype=np.float32)
    report = report_of(first, second)
    recording = recorder(runner_result(stdout=report))
    environment = {"A": "1"}
    result = run_model_program(
        Path("bin") / "model",
        tmp_path / "input.bin",
        ["libk0.so", PurePosixPath("dir/libk1.so")],
        shapes=((1, 2), (3, 1)),
        timeout_s=7.5,
        cwd=tmp_path,
        env=environment,
    )
    assert recording.calls == [
        (
            (
                os.fspath(Path("bin") / "model"),
                os.fspath(tmp_path / "input.bin"),
                "libk0.so",
                os.fspath(PurePosixPath("dir/libk1.so")),
            ),
            7.5,
            tmp_path,
            environment,
        )
    ]
    command = recording.calls[0][0]
    assert all(type(part) is str for part in command)
    assert recording.calls[0][2] is tmp_path
    assert recording.calls[0][3] is environment
    assert isinstance(result, ModelProgramResult)
    assert result.failed is None
    assert np.array_equal(result.outputs[0], first)
    assert np.array_equal(result.outputs[1], second)
    for output in result.outputs:
        assert output.flags.owndata
        assert output.base is None
        assert not np.shares_memory(output, np.frombuffer(report, np.uint8))
    assert result.run == runner_result(stdout=b"")


def test_run_with_a_command_prefix(recorder):
    recording = recorder(runner_result(stdout=report_of(np.zeros((1, 1)))))
    result = run_model_program(
        ["sh", Path("wrap.sh"), "--"],
        "in.bin",
        ("lib.so",),
        shapes=[(1, 1)],
        timeout_s=3,
    )
    assert recording.calls == [
        (("sh", os.fspath(Path("wrap.sh")), "--", "in.bin", "lib.so"), 3, None, None)
    ]
    assert result.failed is None


@pytest.mark.parametrize(
    ("returned", "failed"),
    [
        (runner_result(returncode=None, timed_out=True), RunFailed.TIMEOUT),
        (runner_result(returncode=0, timed_out=True), RunFailed.TIMEOUT),
        (runner_result(returncode=1), RunFailed.EXIT_STATUS),
        (runner_result(returncode=-9), RunFailed.EXIT_STATUS),
        (runner_result(returncode=0, stdout=b"short"), RunFailed.REPORT_FORM),
        (runner_result(returncode=0, stdout=b""), RunFailed.REPORT_FORM),
    ],
)
def test_run_failed_outcomes(recorder, returned, failed):
    recorder(returned)
    result = run_model_program("prog", "in", ["lib"], shapes=[(1, 1)], timeout_s=1)
    assert result.failed is failed
    assert result.outputs is None
    assert result.run.stdout == b""
    assert result.run == returned._replace(stdout=b"")


@pytest.mark.parametrize(
    "returned",
    [
        runner_result(returncode=None, timed_out=True, stdout=report_of([[1.0]])),
        runner_result(returncode=5, stdout=report_of([[1.0]])),
    ],
)
def test_complete_report_of_a_failed_run_gives_no_outputs(recorder, returned):
    recorder(returned)
    result = run_model_program("prog", "in", ["lib"], shapes=[(1, 1)], timeout_s=1)
    assert result.failed in (RunFailed.TIMEOUT, RunFailed.EXIT_STATUS)
    assert result.outputs is None
    assert result.run.stdout == b""


class BytesPath:
    def __fspath__(self):
        return b"bytes/path"


def bad_run_arguments():
    good = {"program": "prog", "input_file": "in", "libraries": ["lib"]}
    cases = [
        ({"program": b"prog"}, TypeError, "program"),
        ({"program": BytesPath()}, TypeError, "program"),
        ({"program": 5}, TypeError, "program"),
        ({"program": iter(["prog"])}, TypeError, "program"),
        ({"program": []}, ValueError, "program"),
        ({"program": ["sh", b"x"]}, TypeError, "program[1]"),
        ({"program": ["sh", 1]}, TypeError, "program[1]"),
        ({"input_file": b"in"}, TypeError, "input_file"),
        ({"input_file": BytesPath()}, TypeError, "input_file"),
        ({"input_file": None}, TypeError, "input_file"),
        ({"libraries": "lib.so"}, TypeError, "libraries"),
        ({"libraries": b"lib.so"}, TypeError, "libraries"),
        ({"libraries": Path("lib.so")}, TypeError, "libraries"),
        ({"libraries": iter(["lib"])}, TypeError, "libraries"),
        ({"libraries": []}, ValueError, "libraries"),
        ({"libraries": ["a", b"b"]}, TypeError, "libraries[1]"),
        ({"libraries": ["a", BytesPath()]}, TypeError, "libraries[1]"),
        ({"libraries": [None]}, TypeError, "libraries[0]"),
    ]
    return [({**good, **change}, error, text) for change, error, text in cases]


@pytest.mark.parametrize(("arguments", "error", "text"), bad_run_arguments())
def test_run_refuses_arguments_before_the_start(recorder, arguments, error, text):
    recording = recorder(runner_result())
    with pytest.raises(error) as caught:
        run_model_program(**arguments, shapes=[(1, 1)], timeout_s=1)
    assert type(caught.value) is error
    assert text in str(caught.value)
    assert recording.calls == []


@pytest.mark.parametrize(("shapes", "error"), bad_shapes())
def test_run_refuses_shapes_before_the_start(recorder, shapes, error):
    recording = recorder(runner_result())
    with pytest.raises(error, match="shapes"):
        run_model_program("prog", "in", ["lib"], shapes=shapes, timeout_s=1)
    assert recording.calls == []


def test_run_passes_on_what_local_run_raises(tmp_path):
    with pytest.raises(local_run.ProgramNotFoundError):
        run_model_program(
            str(tmp_path / "missing"), "in", ["lib"], shapes=[(1, 1)], timeout_s=1
        )
    with pytest.raises(ValueError):
        run_model_program("prog", "in", ["lib"], shapes=[(1, 1)], timeout_s=0)


def test_public_names():
    assert {name for name in vars(model_run) if not name.startswith("_")} >= {
        "END_MARK",
        "RunFailed",
        "ModelProgramResult",
        "encode_input",
        "output_shapes",
        "parse_report",
        "run_model_program",
    }
    assert [member.name for member in RunFailed] == [
        "TIMEOUT",
        "EXIT_STATUS",
        "REPORT_FORM",
    ]
    assert ModelProgramResult._fields == ("failed", "outputs", "run")


PRODUCT = """\
#include <stddef.h>
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            float sum = @START@;

            for (p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""

NEVER_RETURNS = """\
#include <stddef.h>
#include <unistd.h>
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    (void)m; (void)k; (void)n; (void)a; (void)b; (void)c;
    for (;;)
        sleep(1);
}
"""

SOURCES = {
    "plain": PRODUCT.replace("@START@", "0.0f"),
    "plus_one": PRODUCT.replace("@START@", "1.0f"),
    "never_returns": NEVER_RETURNS,
    "no_entry": "int other_entry(int x)\n{\n    return x + 1;\n}\n",
}


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the model program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("model_run")
    program = directory / "model_program"
    result = build_model_program(program, timeout_s=BUILD_TIMEOUT, flags=("-O2",))
    assert result.ok, result.log
    libraries = {}
    for name, text in SOURCES.items():
        source = directory / f"{name}.c"
        source.write_text(text, encoding="ascii", newline="\n")
        output = directory / f"lib{name}.so"
        result = build_kernel_library(
            source, output, timeout_s=BUILD_TIMEOUT, flags=("-O2",)
        )
        assert result.ok, result.log
        libraries[name] = output
    return program, libraries


def run_calls(built, tmp_path, calls, names, timeout_s=RUN_TIMEOUT):
    program, libraries = built
    path = tmp_path / "input.bin"
    path.write_bytes(encode_input(calls))
    return run_model_program(
        program,
        path,
        [libraries[name] for name in names],
        shapes=output_shapes(calls),
        timeout_s=timeout_s,
    )


def test_real_run_two_kernels_several_shapes(built, tmp_path):
    shapes = [(2, 3, 4), (1, 1, 1), (5, 7, 3), (3, 2, 6)]
    calls = [
        (position % 2, *matrices(m, k, n, 10 + position))
        for position, (m, k, n) in enumerate(shapes)
    ]
    result = run_calls(built, tmp_path, calls, ["plain", "plus_one"])
    assert result.failed is None, result.run.stderr
    assert result.run.returncode == 0
    assert result.run.stdout == b""
    assert len(result.outputs) == len(calls)
    for (index, a, b), output in zip(calls, result.outputs, strict=True):
        expected = a @ b + np.float32(index)
        assert output.dtype == np.float32
        assert np.array_equal(output, expected)


def test_real_run_index_out_of_range(built, tmp_path):
    result = run_calls(
        built, tmp_path, [(2, *matrices(2, 2, 2, 1))], ["plain", "plus_one"]
    )
    assert result.failed is RunFailed.EXIT_STATUS
    assert result.run.returncode == 5
    assert result.outputs is None


def test_real_run_library_without_entry(built, tmp_path):
    result = run_calls(
        built, tmp_path, [(0, *matrices(2, 2, 2, 1))], ["plain", "no_entry"]
    )
    assert result.failed is RunFailed.EXIT_STATUS
    assert result.run.returncode == 6
    assert result.outputs is None


def test_real_run_timeout(built, tmp_path):
    result = run_calls(
        built, tmp_path, [(0, *matrices(1, 1, 1, 1))], ["never_returns"], timeout_s=1
    )
    assert result.failed is RunFailed.TIMEOUT
    assert result.run.timed_out
    assert result.outputs is None
