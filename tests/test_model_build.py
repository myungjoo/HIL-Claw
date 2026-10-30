import os
import shutil
from pathlib import Path

import pytest

from hilclaw import clang_build, model_build, model_run
from hilclaw.model_build import (
    FORWARD_PROGRAM_SOURCE,
    LIBRARY_FLAGS,
    PROGRAM_DTYPE_FLAGS,
    PROGRAM_SOURCE,
    build_forward_program,
    build_kernel_library,
    build_model_program,
)

TIMEOUT = 120

KERNEL = """\
#include <stddef.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            float sum = 0.0f;

            for (p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""

BROKEN = "void hilclaw_gemm(size_t m, { this is not C\n"


class Recorder:
    def __init__(self, result="built"):
        self.calls = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


@pytest.fixture
def recorder(monkeypatch):
    stand_in = Recorder()
    monkeypatch.setattr(clang_build, "build", stand_in)
    return stand_in


@pytest.fixture
def clang():
    if os.name != "posix":
        pytest.skip("a shared library and dlopen need a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def test_program_source_is_next_to_the_module():
    assert PROGRAM_SOURCE == Path(model_build.__file__).with_name("model_program.c")
    assert PROGRAM_SOURCE.is_file()


def test_forward_program_source_is_next_to_the_module():
    assert FORWARD_PROGRAM_SOURCE == Path(model_build.__file__).with_name(
        "model_forward.c"
    )
    assert FORWARD_PROGRAM_SOURCE.is_file()


def test_library_flags():
    assert LIBRARY_FLAGS == ("-shared", "-fPIC")


def test_program_dtype_flags():
    assert dict(PROGRAM_DTYPE_FLAGS) == {"fp32": (), "bf16": ("-DHILCLAW_MODEL_BF16",)}
    assert tuple(PROGRAM_DTYPE_FLAGS) == model_run.DTYPES


def test_program_dtype_flags_are_read_only():
    with pytest.raises(TypeError):
        PROGRAM_DTYPE_FLAGS["fp16"] = ()
    with pytest.raises(TypeError):
        PROGRAM_DTYPE_FLAGS["fp32"] = ("-O2",)
    with pytest.raises(TypeError):
        del PROGRAM_DTYPE_FLAGS["bf16"]
    assert dict(PROGRAM_DTYPE_FLAGS) == {"fp32": (), "bf16": ("-DHILCLAW_MODEL_BF16",)}


def test_public_names():
    public = {name for name in vars(model_build) if not name.startswith("_")}
    imported = {"os", "Path", "MappingProxyType", "clang_build"}
    assert public - imported == {
        "PROGRAM_SOURCE",
        "FORWARD_PROGRAM_SOURCE",
        "LIBRARY_FLAGS",
        "PROGRAM_DTYPE_FLAGS",
        "build_kernel_library",
        "build_model_program",
        "build_forward_program",
    }


def test_module_text_does_not_name_the_contract_module():
    assert "gemm_contract" not in Path(model_build.__file__).read_text(encoding="utf-8")


def test_kernel_library_hands_every_argument_over(recorder):
    env = {"A": "1"}
    result = build_kernel_library(
        ["k1.c", Path("k2.c")],
        "lib.so",
        timeout_s=7,
        flags=["-O2", "-march=native"],
        trailing_flags=("-lm",),
        compiler=("ccache", "clang"),
        cwd="work",
        env=env,
    )
    assert result == "built"
    assert recorder.calls == [
        (
            (("k1.c", Path("k2.c")), "lib.so"),
            {
                "timeout_s": 7,
                "flags": ("-O2", "-march=native", "-shared", "-fPIC"),
                "trailing_flags": ("-lm",),
                "compiler": ("ccache", "clang"),
                "cwd": "work",
                "env": env,
            },
        )
    ]
    assert recorder.calls[0][1]["env"] is env


def test_kernel_library_defaults_and_one_path(recorder):
    source = Path("kernel.c")
    build_kernel_library(source, "lib.so", timeout_s=1)
    assert recorder.calls == [
        (
            ((source,), "lib.so"),
            {
                "timeout_s": 1,
                "flags": LIBRARY_FLAGS,
                "trailing_flags": (),
                "compiler": None,
                "cwd": None,
                "env": None,
            },
        )
    ]


def test_kernel_library_one_str_path_and_a_generator(recorder):
    build_kernel_library("kernel.c", "a.so", timeout_s=1, flags=("-O3",))
    build_kernel_library((s for s in ("x.c", "y.c")), "b.so", timeout_s=1)
    assert recorder.calls[0][0] == (("kernel.c",), "a.so")
    assert recorder.calls[0][1]["flags"] == ("-O3", "-shared", "-fPIC")
    assert recorder.calls[1][0] == (("x.c", "y.c"), "b.so")


def test_kernel_library_passes_the_result_through(recorder):
    recorder.result = object()
    assert build_kernel_library("k.c", "l.so", timeout_s=1) is recorder.result


@pytest.mark.parametrize(
    "flags", ["-O2", b"-O2", None, ("-O2", 3), ["-O2", b"-c"], {"-O2"}, iter(["-O2"])]
)
def test_kernel_library_refuses_flags_of_the_wrong_type(recorder, flags):
    with pytest.raises(TypeError) as caught:
        build_kernel_library("k.c", "l.so", timeout_s=1, flags=flags)
    assert caught.value.parameter == "flags"
    assert recorder.calls == []


def test_flags_are_checked_before_the_sources(recorder):
    with pytest.raises(TypeError) as caught:
        build_kernel_library((), "l.so", timeout_s=1, flags="-O2")
    assert caught.value.parameter == "flags"


@pytest.mark.parametrize("sources", [(), [], iter(())])
def test_kernel_library_refuses_no_source(recorder, sources):
    with pytest.raises(ValueError, match="no kernel source") as caught:
        build_kernel_library(sources, "l.so", timeout_s=1)
    assert getattr(caught.value, "parameter", None) is None
    assert recorder.calls == []


@pytest.mark.parametrize("sources", [None, 3, 1.5])
def test_kernel_library_refuses_a_non_iterable_source(recorder, sources):
    with pytest.raises(TypeError) as caught:
        build_kernel_library(sources, "l.so", timeout_s=1)
    assert caught.value.parameter == "kernel_sources"
    assert recorder.calls == []


@pytest.mark.parametrize("raised", [TypeError, ValueError, UnicodeError])
def test_kernel_library_marks_an_error_while_iterating_the_sources(recorder, raised):
    def sources():
        yield "k.c"
        raise raised("broken iterator")

    with pytest.raises(raised, match="broken iterator") as caught:
        build_kernel_library(sources(), "l.so", timeout_s=1)
    assert caught.value.parameter == "kernel_sources"
    assert recorder.calls == []


def test_kernel_library_passes_another_iteration_error_unchanged(recorder):
    def sources():
        raise KeyError("other")
        yield "k.c"

    with pytest.raises(KeyError) as caught:
        build_kernel_library(sources(), "l.so", timeout_s=1)
    assert not hasattr(caught.value, "parameter")


def test_kernel_library_passes_on_what_the_build_raises(monkeypatch):
    error = ValueError("from clang_build")
    error.parameter = "timeout_s"

    def raising(*args, **kwargs):
        raise error

    monkeypatch.setattr(clang_build, "build", raising)
    with pytest.raises(ValueError) as caught:
        build_kernel_library("k.c", "l.so", timeout_s=-1)
    assert caught.value is error
    assert caught.value.parameter == "timeout_s"


def test_model_program_hands_every_argument_over(recorder):
    env = {"B": "2"}
    flags = ["-O2"]
    trailing = ["-ldl"]
    result = build_model_program(
        "program",
        timeout_s=9,
        flags=flags,
        trailing_flags=trailing,
        compiler="clang-18",
        cwd="work",
        env=env,
    )
    assert result == "built"
    assert len(recorder.calls) == 1
    args, kwargs = recorder.calls[0]
    assert args == ((PROGRAM_SOURCE,), "program")
    assert kwargs == {
        "timeout_s": 9,
        "flags": ["-O2"],
        "trailing_flags": ["-ldl"],
        "compiler": "clang-18",
        "cwd": "work",
        "env": env,
    }
    assert kwargs["flags"] is flags
    assert kwargs["trailing_flags"] is trailing
    assert kwargs["env"] is env


def test_model_program_defaults_add_no_flag(recorder):
    build_model_program("program", timeout_s=1)
    assert recorder.calls == [
        (
            ((PROGRAM_SOURCE,), "program"),
            {
                "timeout_s": 1,
                "flags": (),
                "trailing_flags": (),
                "compiler": None,
                "cwd": None,
                "env": None,
            },
        )
    ]


def test_model_program_passes_on_what_the_build_raises(monkeypatch):
    error = TypeError("bare str")
    error.parameter = "flags"

    def raising(*args, **kwargs):
        raise error

    monkeypatch.setattr(clang_build, "build", raising)
    with pytest.raises(TypeError) as caught:
        build_model_program("program", timeout_s=1, flags="-O2")
    assert caught.value is error


def test_real_build_errors_reach_the_caller_unchanged(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_kernel_library(tmp_path / "missing.c", tmp_path / "l.so", timeout_s=1)
    with pytest.raises(ValueError) as caught:
        build_model_program(tmp_path / "program", timeout_s=0)
    assert caught.value.parameter == "timeout_s"


def test_clang_builds_a_kernel_into_a_shared_library(clang, tmp_path):
    source = tmp_path / "kernel.c"
    source.write_text(KERNEL, encoding="ascii")
    output = tmp_path / "libkernel.so"
    result = build_kernel_library(source, output, timeout_s=TIMEOUT, flags=("-O2",))
    assert result.ok, result.log
    assert result.command[-6:-3] == ("-O2", "-shared", "-fPIC")
    assert output.read_bytes()[:4] in (b"\x7fELF", b"\xcf\xfa\xed\xfe")


def test_clang_reports_a_kernel_that_does_not_compile(clang, tmp_path):
    source = tmp_path / "kernel.c"
    source.write_text(BROKEN, encoding="ascii")
    output = tmp_path / "libkernel.so"
    result = build_kernel_library(source, output, timeout_s=TIMEOUT)
    assert result.ok is False
    assert result.returncode not in (0, None)
    assert "error" in result.log
    assert not output.exists()


def test_clang_builds_the_program_with_the_callers_flags(clang, tmp_path):
    output = tmp_path / "model_program"
    flags = ("-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
    result = build_model_program(output, timeout_s=TIMEOUT, flags=flags)
    assert result.ok, result.log
    assert result.command[1:7] == flags
    assert os.access(output, os.X_OK)


def test_forward_program_hands_every_argument_over(recorder):
    env = {"C": "3"}
    flags = ["-O2", "-DHILCLAW_MODEL_BF16"]
    trailing = ("-ldl",)
    result = build_forward_program(
        "forward",
        timeout_s=11,
        flags=flags,
        trailing_flags=trailing,
        compiler=("ccache", "clang"),
        cwd="work",
        env=env,
    )
    assert result == "built"
    assert len(recorder.calls) == 1
    args, kwargs = recorder.calls[0]
    assert args == ((FORWARD_PROGRAM_SOURCE,), "forward")
    assert kwargs == {
        "timeout_s": 11,
        "flags": ["-O2", "-DHILCLAW_MODEL_BF16"],
        "trailing_flags": ("-ldl",),
        "compiler": ("ccache", "clang"),
        "cwd": "work",
        "env": env,
    }
    assert kwargs["flags"] is flags
    assert kwargs["trailing_flags"] is trailing
    assert kwargs["env"] is env


def test_forward_program_defaults_add_no_flag(recorder):
    build_forward_program("forward", timeout_s=1)
    assert recorder.calls == [
        (
            ((FORWARD_PROGRAM_SOURCE,), "forward"),
            {
                "timeout_s": 1,
                "flags": (),
                "trailing_flags": (),
                "compiler": None,
                "cwd": None,
                "env": None,
            },
        )
    ]


def test_forward_program_passes_the_result_through(recorder):
    recorder.result = object()
    assert build_forward_program("forward", timeout_s=1) is recorder.result


def test_forward_program_passes_on_what_the_build_raises(monkeypatch, tmp_path):
    error = TypeError("bare str")
    error.parameter = "flags"

    def raising(*args, **kwargs):
        raise error

    monkeypatch.setattr(clang_build, "build", raising)
    with pytest.raises(TypeError) as caught:
        build_forward_program("forward", timeout_s=1, flags="-O2")
    assert caught.value is error
    monkeypatch.undo()
    with pytest.raises(ValueError) as caught:
        build_forward_program(tmp_path / "forward", timeout_s=0)
    assert caught.value.parameter == "timeout_s"


def test_clang_builds_the_forward_program_with_the_callers_flags(clang, tmp_path):
    output = tmp_path / "model_forward"
    flags = ("-std=c99", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
    result = build_forward_program(
        output, timeout_s=TIMEOUT, flags=flags, trailing_flags=("-ldl",)
    )
    assert result.ok, result.log
    assert result.command[1:7] == flags
    assert result.command[7].endswith("model_forward.c")
    assert result.command[8] == "-ldl"
    assert os.access(output, os.X_OK)
