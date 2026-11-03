import json
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import (
    clang_build,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.clang_build import BuildResult
from hilclaw.harness import bf16_timing_build, bf16_verification_build, timing_build
from hilclaw.harness.bf16_program_generator import GENERATED_KINDS, timing_source
from hilclaw.harness.bf16_timing import KINDS, run_bf16_timing
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
    "rope": rope_bf16_contract,
    "sdpa_kv_cache": sdpa_kv_cache_bf16_contract,
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
def scratch(tmp_path, monkeypatch):
    directory = tmp_path / "scratch"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


def assert_program(kind, path):
    if kind not in GENERATED_KINDS:
        assert path is PROGRAM_SOURCES[kind] or path == str(PROGRAM_SOURCES[kind])
        return
    path = Path(path)
    assert path.is_absolute()
    assert path.name == PROGRAM_SOURCES[kind].name
    assert path.parent != DIRECTORY
    assert not path.parent.exists()


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
        assert path.is_file() is (kind not in GENERATED_KINDS)
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
        PROGRAM_SOURCES["other"] = Path("other.c")
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
    assert sources[1:] == (first, "l.c")
    assert_program(kind, sources[0])
    assert handed is output
    assert keywords.keys() == given.keys()
    assert all(keywords[name] is given[name] for name in given)


@pytest.mark.parametrize("kind", KINDS)
def test_defaults_are_those_of_clang_build(monkeypatch, kind):
    calls = []
    monkeypatch.setattr(clang_build, "build", lambda *a, **k: calls.append((a, k)))
    assert build_bf16_timing_executable(kind, "k.c", "exe", timeout_s=3) is None
    assert_program(kind, calls[0][0][0][0])
    assert calls == [
        (
            ((calls[0][0][0][0], "k.c"), "exe"),
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
    assert_program(kind, stub.sources()[len(flags)])
    assert stub.sources() == [
        *flags,
        stub.sources()[len(flags)],
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
    assert_program("rmsnorm", stub.sources()[0])
    assert stub.sources()[1:] == [*map(str, expected)]


def test_a_failed_build_is_a_result(stub, kernel, out):
    result = build_bf16_timing_executable(
        "gemm", kernel(), out, timeout_s=TIMEOUT, compiler=stub(FAIL)
    )
    assert result.ok is False
    assert result.returncode == 1
    assert "stub says no" in result.log


@pytest.mark.parametrize(
    "kind",
    ["fp16", "GEMM", "", "gemm ", b"gemm", None, 1, Count("gemm")],
)
def test_an_unknown_kind_is_refused_before_anything_starts(no_build, kind):
    with pytest.raises(ValueError, match="kind must be one of") as caught:
        build_bf16_timing_executable(kind, "k.c", "exe", timeout_s=TIMEOUT)
    assert caught.value.parameter == "kind"


def test_the_kind_is_tested_before_the_kernel_sources(no_build):
    with pytest.raises(ValueError) as caught:
        build_bf16_timing_executable("fp16", (), "exe", timeout_s=TIMEOUT)
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


# The generated programs (ADR-0193 decision 6)


def test_the_generated_kinds_keep_the_file_names_of_their_programs():
    for kind in GENERATED_KINDS:
        assert PROGRAM_SOURCES[kind].name == f"bf16_timing_{kind}.c"
    assert set(GENERATED_KINDS) < set(PROGRAM_SOURCES)


@pytest.mark.parametrize("kind", KINDS)
def test_the_build_compiles_the_generated_text_beside_both_headers(
    monkeypatch, scratch, kind
):
    seen = {}

    def fake(sources, output, **keywords):
        program = Path(sources[0])
        seen["text"] = program.read_text(encoding="ascii")
        seen["entries"] = sorted(os.listdir(program.parent))
        seen["headers"] = [
            (program.parent / name).read_bytes()
            for name in ("bf16_timing.h", "bf16_verification.h")
        ]
        seen["parent"] = program.parent
        return "built"

    monkeypatch.setattr(clang_build, "build", fake)
    assert build_bf16_timing_executable(kind, "k.c", "exe", timeout_s=3) == "built"
    if kind in GENERATED_KINDS:
        assert seen["text"] == timing_source(kind)
        assert seen["entries"] == sorted(
            ["bf16_timing.h", "bf16_verification.h", PROGRAM_SOURCES[kind].name]
        )
        assert seen["headers"] == [
            (DIRECTORY / name).read_bytes()
            for name in ("bf16_timing.h", "bf16_verification.h")
        ]
        assert seen["parent"].parent == scratch
    else:
        assert seen["text"] == PROGRAM_SOURCES[kind].read_text(encoding="ascii")
        assert seen["parent"] == DIRECTORY
    assert os.listdir(scratch) == []


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_a_generated_kind_reads_no_program_file(stub, kernel, out, monkeypatch, kind):
    sources = {**PROGRAM_SOURCES, kind: kernel().with_name(f"bf16_timing_{kind}.c")}
    monkeypatch.setattr(
        bf16_timing_build, "PROGRAM_SOURCES", types.MappingProxyType(sources)
    )
    result = build_bf16_timing_executable(
        kind, kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    )
    assert result.ok
    assert_program(kind, stub.sources()[0])


def test_a_handwritten_program_that_is_missing_raises(stub, kernel, out, monkeypatch):
    sources = {**PROGRAM_SOURCES, "rope": kernel().with_name("bf16_timing_rope.c")}
    monkeypatch.setattr(
        bf16_timing_build, "PROGRAM_SOURCES", types.MappingProxyType(sources)
    )
    with pytest.raises(FileNotFoundError, match="bf16_timing_rope.c"):
        build_bf16_timing_executable(
            "rope", kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started


def test_the_directory_is_removed_after_a_failed_build(stub, kernel, out, scratch):
    result = build_bf16_timing_executable(
        "elementwise_add", kernel(), out, timeout_s=TIMEOUT, compiler=stub(FAIL)
    )
    assert result.ok is False
    assert_program("elementwise_add", stub.sources()[0])
    assert os.listdir(scratch) == []


@pytest.mark.parametrize(
    "keywords",
    [{"trailing_flags": ("-o", "x")}, {"timeout_s": -1}, {"compiler": ()}],
    ids=["trailing", "timeout", "compiler"],
)
def test_the_directory_is_removed_after_a_raise(kernel, out, scratch, keywords):
    with pytest.raises((TypeError, ValueError)):
        build_bf16_timing_executable(
            "gemm", kernel(), out, **{"timeout_s": TIMEOUT, **keywords}
        )
    assert os.listdir(scratch) == []
    assert not out.exists()


@pytest.mark.parametrize("index", [0, 1])
def test_a_missing_header_raises_before_the_compiler(
    stub, kernel, out, scratch, monkeypatch, tmp_path, index
):
    headers = list(bf16_timing_build._HEADERS)
    headers[index] = tmp_path / "gone.h"
    monkeypatch.setattr(bf16_timing_build, "_HEADERS", tuple(headers))
    with pytest.raises(FileNotFoundError):
        build_bf16_timing_executable(
            "swiglu", kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started
    assert os.listdir(scratch) == []


@pytest.mark.parametrize("kind", ["fp16", "GEMM", None, Count("gemm")], ids=repr)
def test_a_refused_kind_makes_no_directory(no_build, scratch, kind):
    with pytest.raises(ValueError):
        build_bf16_timing_executable(kind, "k.c", "exe", timeout_s=3)
    assert os.listdir(scratch) == []


@pytest.mark.parametrize("sources", [(), 7], ids=repr)
def test_refused_kernel_sources_make_no_directory(no_build, scratch, sources):
    with pytest.raises((TypeError, ValueError)):
        build_bf16_timing_executable("rmsnorm", sources, "exe", timeout_s=3)
    assert os.listdir(scratch) == []


def busy_kernel(kind):
    return empty_kernel(kind).replace(
        "\n}\n",
        "\n    volatile unsigned spin = 0;\n"
        "    for (unsigned i = 0; i < 20000; i++)\n"
        "        spin += i;\n"
        "    (void)spin;\n}\n",
    )


@pytest.mark.parametrize("kind", GENERATED_KINDS)
def test_real_clang_builds_the_generated_program_whose_report_is_accepted(
    clang, kernel, out, kind
):
    source = kernel(text=busy_kernel(kind))
    result = build_bf16_timing_executable(
        kind, source, out, timeout_s=TIMEOUT, flags=STRICT
    )
    assert result.ok, result.log
    dims = (3, 4, 5) if kind == "gemm" else (3, 5)
    timed = run_bf16_timing(
        out,
        kind,
        dims,
        sample_form="interval",
        seed=20261103,
        timeout_s=TIMEOUT,
        n_max=10,
    )
    assert timed.broken is None, timed.run
    assert timed.intervals_ns
