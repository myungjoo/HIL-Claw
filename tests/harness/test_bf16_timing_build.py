import json
import os
import shutil
import sys
import types
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import (
    clang_build,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.clang_build import BuildResult
from hilclaw.harness import bf16_verification_build, timing_build
from hilclaw.harness.bf16_timing import KINDS
from hilclaw.harness.bf16_timing_build import (
    PROGRAM_SOURCES,
    build_bf16_timing_executable,
)

PRELUDE = """\
import json, os, sys
from pathlib import Path
here = Path(__file__).parent
argv = sys.argv[1:]
call = {"argv": argv, "cwd": os.getcwd(), "mark": os.environ.get("HILCLAW_TEST_MARK")}
(here / "started.json").write_text(json.dumps(call), encoding="utf-8")
out = Path(argv[argv.index("-o") + 1])
"""
WRITE = "out.write_bytes(b'artefact')"
FAIL = "print('kernel.c:1:1: error: stub says no'); sys.exit(1)"

TIMEOUT = 60
DIRECTORY = Path(hilclaw.harness.__file__).parent
STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")
CONTRACTS = {
    "gemm": gemm_bf16_contract,
    "rmsnorm": rmsnorm_bf16_contract,
    "elementwise_add": elementwise_add_bf16_contract,
    "swiglu": swiglu_bf16_contract,
}


class Count(str):
    pass


def empty_kernel(kind):
    prototype = CONTRACTS[kind].PROTOTYPE
    names = prototype[prototype.index("(") + 1 : prototype.rindex(")")].split(", ")
    voids = "".join(f"    (void){name.split()[-1].lstrip('*')};\n" for name in names)
    return (
        "#include <stddef.h>\n#include <stdint.h>\n\n"
        f"{prototype}\n\n{prototype.removesuffix(';')}\n{{\n{voids}}}\n"
    )


class Stub:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(self, body):
        script = self.directory / "cc.py"
        script.write_text(PRELUDE + body + "\n", encoding="utf-8")
        return (sys.executable, str(script))

    @property
    def started(self):
        return self.record.exists()

    def call(self):
        return json.loads(self.record.read_text(encoding="utf-8"))

    def sources(self):
        argv = self.call()["argv"]
        return argv[: argv.index("-o")]


@pytest.fixture
def stub(tmp_path):
    directory = tmp_path / "stub"
    directory.mkdir()
    return Stub(directory)


@pytest.fixture
def kernel(tmp_path):
    directory = tmp_path / "src"
    directory.mkdir()

    def write(name="kernel.c", text="int unused;\n"):
        path = directory / name
        path.write_text(text, encoding="ascii", newline="\n")
        return path

    return write


@pytest.fixture
def out(tmp_path):
    directory = tmp_path / "out"
    directory.mkdir()
    return directory / "timing"


@pytest.fixture
def clang():
    if os.name != "posix":
        pytest.skip("a timing executable needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


@pytest.fixture
def no_build(monkeypatch):
    def refuse(*arguments, **keywords):
        pytest.fail("clang_build.build was called")

    monkeypatch.setattr(clang_build, "build", refuse)


def test_program_sources_are_the_c_files_of_the_kinds_next_to_the_package():
    assert tuple(PROGRAM_SOURCES) == KINDS
    for kind, path in PROGRAM_SOURCES.items():
        assert isinstance(path, Path)
        assert path.is_absolute()
        assert path.is_file()
        assert path.name == f"bf16_timing_{kind}.c"
        assert path.parent == DIRECTORY
    assert (DIRECTORY / "bf16_timing.h").is_file()
    assert len(set(PROGRAM_SOURCES.values())) == len(KINDS)
    others = {
        timing_build.DRIVER_SOURCE,
        *bf16_verification_build.PROGRAM_SOURCES.values(),
    }
    assert others.isdisjoint(PROGRAM_SOURCES.values())


def test_program_sources_cannot_be_assigned_to():
    assert isinstance(PROGRAM_SOURCES, types.MappingProxyType)
    with pytest.raises(TypeError):
        PROGRAM_SOURCES["gemm"] = Path("other.c")
    with pytest.raises(TypeError):
        del PROGRAM_SOURCES["gemm"]
    with pytest.raises(TypeError):
        PROGRAM_SOURCES["rope"] = Path("rope.c")
    assert tuple(PROGRAM_SOURCES) == KINDS


@pytest.mark.parametrize("kind", KINDS)
def test_arguments_are_handed_over_unchanged_in_one_call(monkeypatch, kind):
    calls = []
    outcome = object()

    def fake(sources, output, **keywords):
        calls.append((sources, output, keywords))
        return outcome

    monkeypatch.setattr(clang_build, "build", fake)
    given = {
        "timeout_s": 12.5,
        "flags": ["-O2"],
        "trailing_flags": ["-lm"],
        "compiler": ("ccache", "clang"),
        "cwd": "somewhere",
        "env": {"OMP_NUM_THREADS": "4"},
    }
    output = Path("exe")
    first = Path("k.c")
    result = build_bf16_timing_executable(kind, [first, "l.c"], output, **given)
    assert result is outcome
    assert len(calls) == 1
    sources, handed, keywords = calls[0]
    assert sources == (PROGRAM_SOURCES[kind], first, "l.c")
    assert sources[0] is PROGRAM_SOURCES[kind]
    assert handed is output
    assert keywords.keys() == given.keys()
    assert all(keywords[name] is given[name] for name in given)


@pytest.mark.parametrize("kind", KINDS)
def test_defaults_are_those_of_clang_build(monkeypatch, kind):
    calls = []
    monkeypatch.setattr(clang_build, "build", lambda *a, **k: calls.append((a, k)))
    assert build_bf16_timing_executable(kind, "k.c", "exe", timeout_s=3) is None
    assert calls == [
        (
            ((PROGRAM_SOURCES[kind], "k.c"), "exe"),
            {
                "timeout_s": 3,
                "flags": (),
                "trailing_flags": (),
                "compiler": None,
                "cwd": None,
                "env": None,
            },
        )
    ]


@pytest.mark.parametrize("kind", KINDS)
def test_stub_build_adds_no_flag_and_puts_the_program_first(stub, kernel, out, kind):
    first, second = kernel("a.c"), kernel("b.c")
    flags = ("-O3", "-DX=1")
    trailing = ("-lm",)
    result = build_bf16_timing_executable(
        kind,
        (first, second),
        out,
        timeout_s=TIMEOUT,
        flags=flags,
        trailing_flags=trailing,
        compiler=stub(WRITE),
    )
    assert isinstance(result, BuildResult)
    assert result.ok is True
    assert out.read_bytes() == b"artefact"
    assert stub.sources() == [
        *flags,
        str(PROGRAM_SOURCES[kind]),
        str(first),
        str(second),
        *trailing,
    ]


def test_cwd_and_env_reach_the_compiler(stub, kernel, out, tmp_path):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "from the caller"}
    result = build_bf16_timing_executable(
        "swiglu",
        kernel(),
        out,
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
        cwd=cwd,
        env=env,
    )
    assert result.ok
    call = stub.call()
    assert Path(call["cwd"]).resolve() == cwd.resolve()
    assert call["mark"] == "from the caller"


@pytest.mark.parametrize("form", ["str", "path", "list", "generator"])
def test_kernel_sources_in_every_accepted_form(stub, kernel, out, form):
    source, other = kernel(), kernel("other.c")
    given, expected = {
        "str": (str(source), [source]),
        "path": (source, [source]),
        "list": ([source], [source]),
        "generator": ((path for path in [source, other]), [source, other]),
    }[form]
    result = build_bf16_timing_executable(
        "rmsnorm", given, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    )
    assert result.ok
    assert stub.sources() == [str(PROGRAM_SOURCES["rmsnorm"]), *map(str, expected)]


def test_a_failed_build_is_a_result(stub, kernel, out):
    result = build_bf16_timing_executable(
        "gemm", kernel(), out, timeout_s=TIMEOUT, compiler=stub(FAIL)
    )
    assert result.ok is False
    assert result.returncode == 1
    assert "stub says no" in result.log


@pytest.mark.parametrize(
    "kind",
    ["rope", "sdpa_kv_cache", "GEMM", "", "gemm ", b"gemm", None, 1, Count("gemm")],
)
def test_an_unknown_kind_is_refused_before_anything_starts(no_build, kind):
    with pytest.raises(ValueError, match="kind must be one of") as caught:
        build_bf16_timing_executable(kind, "k.c", "exe", timeout_s=TIMEOUT)
    assert caught.value.parameter == "kind"


def test_the_kind_is_tested_before_the_kernel_sources(no_build):
    with pytest.raises(ValueError) as caught:
        build_bf16_timing_executable("rope", (), "exe", timeout_s=TIMEOUT)
    assert caught.value.parameter == "kind"


def test_kernel_sources_that_are_not_iterable_are_refused(no_build):
    with pytest.raises(TypeError) as caught:
        build_bf16_timing_executable("gemm", 7, "exe", timeout_s=TIMEOUT)
    assert caught.value.parameter == "kernel_sources"


def test_an_error_while_iterating_the_kernel_sources_is_marked(no_build):
    def sources():
        yield "k.c"
        raise ValueError("broken iterator")

    with pytest.raises(ValueError, match="broken iterator") as caught:
        build_bf16_timing_executable("gemm", sources(), "exe", timeout_s=TIMEOUT)
    assert caught.value.parameter == "kernel_sources"


@pytest.mark.parametrize("empty", [(), [], iter(())])
def test_no_kernel_source_is_refused(no_build, empty):
    with pytest.raises(ValueError, match="no kernel source") as caught:
        build_bf16_timing_executable("swiglu", empty, "exe", timeout_s=TIMEOUT)
    assert getattr(caught.value, "parameter", None) is None


@pytest.mark.parametrize("kind", KINDS)
def test_each_program_links_with_a_kernel_of_its_kind_under_strict_flags(
    clang, kernel, out, kind
):
    source = kernel(text=empty_kernel(kind))
    result = build_bf16_timing_executable(
        kind, source, out, timeout_s=TIMEOUT, flags=STRICT
    )
    assert result.ok, result.log
    assert out.is_file()


def test_a_kernel_of_another_kind_fails_at_the_linker(clang, kernel, out):
    source = kernel(text=empty_kernel("elementwise_add"))
    result = build_bf16_timing_executable(
        "gemm", source, out, timeout_s=TIMEOUT, flags=STRICT
    )
    assert result.ok is False
    assert "hilclaw_gemm_bf16" in result.log
