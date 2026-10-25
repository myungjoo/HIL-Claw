import json
import os
import pickle
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import (
    clang_build,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    local_run,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    swiglu_bf16_contract,
)
from hilclaw.clang_build import BuildResult
from hilclaw.harness import bf16_verification_build, verification_build
from hilclaw.harness.bf16_verification_arrays import KINDS
from hilclaw.harness.bf16_verification_build import (
    PROGRAM_SOURCES,
    build_bf16_verification_executable,
)

PRELUDE = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
argv = sys.argv[1:]
call = {"argv": argv, "cwd": os.getcwd(), "mark": os.environ.get("HILCLAW_TEST_MARK")}
(here / "started.json").write_text(json.dumps(call), encoding="utf-8")
out = Path(argv[argv.index("-o") + 1])
"""
WRITE = "out.write_bytes(b'artefact')"
FAIL = "out.write_bytes(b'partial'); print('kernel.c:1:1: error: stub says no'); sys.exit(1)"
SLEEP = "print('before sleep', flush=True); time.sleep(30)"

TIMEOUT = 60
DIRECTORY = Path(hilclaw.harness.__file__).parent
STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror")
# The array module learns rope with the Python side of ADR-0164 (code slice 3).
PROGRAM_KINDS = (*KINDS, "rope")

# kind: (contract, parameters to void, copy of the first operand to the output)
STUBS = {
    "gemm": (
        gemm_bf16_contract,
        ("b",),
        "c[i * n + j] = a[i * k + j % k];",
    ),
    "rmsnorm": (
        rmsnorm_bf16_contract,
        ("eps", "w"),
        "y[i * n + j] = x[i * n + j];",
    ),
    "elementwise_add": (
        elementwise_add_bf16_contract,
        ("b",),
        "c[i * n + j] = a[i * n + j];",
    ),
    "swiglu": (
        swiglu_bf16_contract,
        ("up",),
        "out[i * n + j] = gate[i * n + j];",
    ),
}
EXPF = "    volatile float e = expf((float)m);\n    (void)e;\n"


def stub_kernel(kind):
    contract, unused, copy = STUBS[kind]
    includes = "#include <stddef.h>\n#include <stdint.h>\n"
    if kind == "swiglu":
        includes += "#include <math.h>\n"
    voids = "".join(f"    (void){name};\n" for name in unused)
    return (
        f"{includes}\n{contract.PROTOTYPE}\n\n"
        f"{contract.PROTOTYPE.removesuffix(';')}\n{{\n{voids}"
        f"{EXPF if kind == 'swiglu' else ''}"
        "    for (size_t i = 0; i < m; i++)\n"
        "        for (size_t j = 0; j < n; j++)\n"
        f"            {copy}\n}}\n"
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
    return directory / "verification"


@pytest.fixture
def clang():
    if os.name != "posix":
        pytest.skip("a verification executable needs a POSIX system")
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
    assert tuple(PROGRAM_SOURCES) == PROGRAM_KINDS
    for kind, path in PROGRAM_SOURCES.items():
        assert isinstance(path, Path)
        assert path.is_absolute()
        assert path.is_file()
        assert path.name == f"bf16_verification_{kind}.c"
        assert path.parent == DIRECTORY
    assert (DIRECTORY / "bf16_verification.h").is_file()
    assert len(set(PROGRAM_SOURCES.values())) == len(PROGRAM_KINDS)
    assert verification_build.PROGRAM_SOURCE not in PROGRAM_SOURCES.values()


def test_program_sources_cannot_be_assigned_to():
    assert isinstance(PROGRAM_SOURCES, types.MappingProxyType)
    with pytest.raises(TypeError):
        PROGRAM_SOURCES["gemm"] = Path("other.c")
    with pytest.raises(TypeError):
        del PROGRAM_SOURCES["gemm"]
    with pytest.raises(TypeError):
        PROGRAM_SOURCES["sdpa"] = Path("sdpa.c")
    assert tuple(PROGRAM_SOURCES) == PROGRAM_KINDS


@pytest.mark.parametrize("kind", PROGRAM_KINDS)
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
    result = build_bf16_verification_executable(kind, [first, "l.c"], output, **given)
    assert result is outcome
    assert len(calls) == 1
    sources, handed, keywords = calls[0]
    assert sources == (PROGRAM_SOURCES[kind], first, "l.c")
    assert sources[0] is PROGRAM_SOURCES[kind]
    assert sources[1] is first
    assert handed is output
    assert keywords.keys() == given.keys()
    assert all(keywords[name] is given[name] for name in given)


@pytest.mark.parametrize("kind", PROGRAM_KINDS)
def test_defaults_are_those_of_clang_build(monkeypatch, kind):
    calls = []
    monkeypatch.setattr(clang_build, "build", lambda *a, **k: calls.append((a, k)))
    assert build_bf16_verification_executable(kind, "k.c", "exe", timeout_s=3) is None
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


@pytest.mark.parametrize("kind", PROGRAM_KINDS)
def test_stub_build_succeeds_and_adds_nothing(stub, kernel, out, kind):
    source = kernel()
    result = build_bf16_verification_executable(
        kind, source, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    )
    assert isinstance(result, BuildResult)
    assert result.ok is True
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.output == out
    assert out.read_bytes() == b"artefact"
    argv = stub.call()["argv"]
    assert argv[:3] == [str(PROGRAM_SOURCES[kind]), str(source), "-o"]
    assert len(argv) == 4
    assert result.command[2:] == tuple(argv)
    assert sorted(p.name for p in out.parent.iterdir()) == ["verification"]


@pytest.mark.parametrize("kind", PROGRAM_KINDS)
def test_flags_surround_the_sources_in_the_order_given(stub, kernel, out, kind):
    first, second = kernel("a.c"), kernel("b.c")
    flags = ("-O3", "-fopenmp", "-DX=1", "-O0")
    trailing = ("-lm", "-lomp", "-lm")
    result = build_bf16_verification_executable(
        kind,
        (first, second),
        out,
        timeout_s=TIMEOUT,
        flags=flags,
        trailing_flags=trailing,
        compiler=stub(WRITE),
    )
    assert result.ok
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
    result = build_bf16_verification_executable(
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


def test_environment_and_directory_are_inherited_by_default(
    stub, kernel, out, monkeypatch
):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    assert build_bf16_verification_executable(
        "gemm", kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    ).ok
    call = stub.call()
    assert call["mark"] == "inherited"
    assert Path(call["cwd"]).resolve() == Path.cwd().resolve()


@pytest.mark.parametrize("form", ["str", "path", "list", "tuple", "generator"])
def test_kernel_sources_in_every_accepted_form(stub, kernel, out, form):
    source, other = kernel(), kernel("other.c")
    given, expected = {
        "str": (str(source), [source]),
        "path": (source, [source]),
        "list": ([source], [source]),
        "tuple": ((str(source), other), [source, other]),
        "generator": ((path for path in [source, other]), [source, other]),
    }[form]
    result = build_bf16_verification_executable(
        "rmsnorm", given, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    )
    assert result.ok
    assert stub.sources() == [str(PROGRAM_SOURCES["rmsnorm"]), *map(str, expected)]


def test_duplicate_sources_are_not_checked(stub, kernel, out):
    source = kernel()
    program = PROGRAM_SOURCES["elementwise_add"]
    assert build_bf16_verification_executable(
        "elementwise_add",
        (source, program, source),
        out,
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
    ).ok
    assert stub.sources() == [str(program), str(source), str(program), str(source)]


def test_failed_build_is_a_result_with_the_log(stub, kernel, out):
    result = build_bf16_verification_executable(
        "gemm", kernel(), out, timeout_s=TIMEOUT, compiler=stub(FAIL)
    )
    assert result.ok is False
    assert result.returncode == 1
    assert result.timed_out is False
    assert result.log.strip() == "kernel.c:1:1: error: stub says no"
    assert not out.exists()
    assert list(out.parent.iterdir()) == []


def test_timeout_is_a_result(stub, kernel, out):
    result = build_bf16_verification_executable(
        "swiglu", kernel(), out, timeout_s=5, compiler=stub(SLEEP)
    )
    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode is None
    assert "before sleep" in result.log
    assert not out.exists()


class Name(str):
    pass


BAD_KINDS = ["sdpa", "GEMM", "", " gemm", Name("gemm"), b"gemm", None, 7, ["gemm"]]


@pytest.mark.parametrize("kind", BAD_KINDS, ids=repr)
def test_kind_that_is_not_a_key_is_refused_before_anything_starts(
    stub, kernel, out, no_build, kind
):
    with pytest.raises(ValueError) as caught:
        build_bf16_verification_executable(
            kind, kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert type(caught.value) is ValueError
    assert caught.value.parameter == "kind"
    for name in PROGRAM_KINDS:
        assert repr(name) in str(caught.value)
    assert not stub.started
    assert list(out.parent.iterdir()) == []


@pytest.mark.parametrize("kernel_sources", [(), None, "generator"], ids=repr)
def test_kind_is_tested_before_every_other_argument(out, no_build, kernel_sources):
    if kernel_sources == "generator":

        def failing():
            raise TypeError("must not be iterated")
            yield

        kernel_sources = failing()
    with pytest.raises(ValueError) as caught:
        build_bf16_verification_executable(
            "GEMM", kernel_sources, out, timeout_s="soon", flags=7, compiler=()
        )
    assert caught.value.parameter == "kind"


def test_the_kind_parameter_survives_pickling(out, no_build):
    with pytest.raises(ValueError) as caught:
        build_bf16_verification_executable(None, "k.c", out, timeout_s=TIMEOUT)
    copy = pickle.loads(pickle.dumps(caught.value))
    assert type(copy) is ValueError
    assert copy.args == caught.value.args
    assert copy.parameter == "kind"


@pytest.mark.parametrize("empty", [(), [], "generator", b""], ids=repr)
def test_no_kernel_source_is_refused_without_a_parameter(stub, out, no_build, empty):
    if empty == "generator":
        empty = (path for path in ())
    with pytest.raises(ValueError, match="no kernel source") as caught:
        build_bf16_verification_executable(
            "gemm", empty, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not hasattr(caught.value, "parameter")
    assert not stub.started
    assert not out.exists()


def test_no_kernel_source_is_tested_before_the_settings(stub, out, no_build):
    with pytest.raises(ValueError, match="no kernel source"):
        build_bf16_verification_executable(
            "swiglu", (), out, timeout_s="soon", compiler=stub(WRITE)
        )
    assert not stub.started


@pytest.mark.parametrize("value", [None, 7, 1.5], ids=repr)
def test_kernel_sources_that_cannot_be_iterated_name_the_parameter(
    stub, out, no_build, value
):
    with pytest.raises(TypeError) as caught:
        build_bf16_verification_executable(
            "gemm", value, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value.parameter == "kernel_sources"
    assert not stub.started
    assert list(out.parent.iterdir()) == []


class KernelValueError(ValueError):
    pass


@pytest.mark.parametrize(
    "error", [TypeError, ValueError, KernelValueError, UnicodeError]
)
def test_an_error_from_the_iteration_names_the_kernel_sources(
    stub, kernel, out, no_build, error
):
    raised = error("x")

    def sources():
        yield kernel()
        raise raised

    with pytest.raises(error) as caught:
        build_bf16_verification_executable(
            "rmsnorm", sources(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value is raised
    assert type(caught.value) is error
    assert caught.value.args == ("x",)
    assert caught.value.parameter == "kernel_sources"
    assert not stub.started


def test_other_errors_from_the_iteration_pass_unchanged(stub, kernel, out, no_build):
    raised = RuntimeError("x")

    def sources():
        yield kernel()
        raise raised

    with pytest.raises(RuntimeError) as caught:
        build_bf16_verification_executable(
            "elementwise_add", sources(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value is raised
    assert not hasattr(caught.value, "parameter")


@pytest.mark.parametrize("as_list", [False, True])
def test_bytes_path_keeps_the_parameter_of_build(stub, kernel, out, as_list):
    path = os.fsencode(kernel())
    with pytest.raises(TypeError, match="str or os.PathLike") as caught:
        build_bf16_verification_executable(
            "gemm",
            [path] if as_list else path,
            out,
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert caught.value.parameter == "sources"
    assert not stub.started


def test_missing_kernel_source(stub, kernel, out):
    missing = kernel().with_name("absent.c")
    with pytest.raises(FileNotFoundError, match="absent.c") as caught:
        build_bf16_verification_executable(
            "swiglu", [kernel(), missing], out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value.path_role == "source"
    assert not stub.started


def test_missing_program_source(stub, kernel, out, monkeypatch):
    absent = kernel().with_name("bf16_verification_rmsnorm.c")
    sources = {**PROGRAM_SOURCES, "rmsnorm": absent}
    monkeypatch.setattr(
        bf16_verification_build, "PROGRAM_SOURCES", types.MappingProxyType(sources)
    )
    with pytest.raises(
        FileNotFoundError, match="bf16_verification_rmsnorm.c"
    ) as caught:
        build_bf16_verification_executable(
            "rmsnorm", kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value.path_role == "source"
    assert not stub.started


@pytest.mark.parametrize("name", ["flags", "trailing_flags"])
@pytest.mark.parametrize("flag", [("-o", "x"), ("-ox",), ("--output=x",)])
def test_flag_that_sets_the_output(stub, kernel, out, name, flag):
    with pytest.raises(ValueError, match="must not set the output") as caught:
        build_bf16_verification_executable(
            "gemm",
            kernel(),
            out,
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            **{name: flag},
        )
    assert caught.value.parameter == name
    assert not stub.started


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")], ids=repr)
def test_timeout_that_is_not_positive_and_finite(stub, kernel, out, value):
    with pytest.raises(ValueError, match="timeout_s") as caught:
        build_bf16_verification_executable(
            "elementwise_add", kernel(), out, timeout_s=value, compiler=stub(WRITE)
        )
    assert caught.value.parameter == "timeout_s"
    assert not stub.started


def test_timeout_has_no_default(stub, kernel, out):
    with pytest.raises(TypeError, match="timeout_s") as caught:
        build_bf16_verification_executable("gemm", kernel(), out, compiler=stub(WRITE))
    assert not hasattr(caught.value, "parameter")
    assert not stub.started


def test_the_module_imports_no_numpy():
    root = Path(__file__).resolve().parents[2]
    code = (
        f"import sys; sys.path.insert(0, {str(root)!r}); "
        "import hilclaw.harness.bf16_verification_build as module; "
        f"assert module.__file__.startswith({str(root)!r}); "
        "print(sorted(name for name in ('numpy', "
        "'hilclaw.harness.bf16_verification_arrays', "
        "'hilclaw.harness.verification_arrays') if name in sys.modules))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "[]"


def report_length(draws, m, n):
    return draws * (4 + 2 * m * n) + 4


@pytest.mark.parametrize("kind", KINDS)
def test_real_clang_builds_an_executable_that_writes_a_complete_report(
    clang, kernel, out, kind
):
    source = kernel(f"{kind}.c", stub_kernel(kind))
    trailing = ("-lm",) if kind == "swiglu" else ()
    result = build_bf16_verification_executable(
        kind, source, out, timeout_s=120, flags=STRICT, trailing_flags=trailing
    )
    assert result.ok, result.log
    assert result.command[1:-2] == (
        *STRICT,
        str(PROGRAM_SOURCES[kind]),
        str(source),
        *trailing,
    )
    m, k, n, draws = 3, 4, 5, 2
    dims = (m, k, n) if kind == "gemm" else (m, n)
    arguments = [str(value) for value in (*dims, draws, 20261025)]
    run = local_run.run((out, *arguments), timeout_s=TIMEOUT)
    assert run.timed_out is False
    assert run.returncode == 0, run
    assert len(run.stdout) == report_length(draws, m, n)
    assert run.stdout.endswith(b"end\n")


ROPE_KERNEL = """#include <stddef.h>
#include <stdint.h>

@PROTOTYPE@

@SIGNATURE@
{
    (void)freqs_cis;
    for (size_t i = 0; i < m * h * d; i++)
        out[i] = x[i];
}
"""


def test_real_clang_builds_a_rope_executable_that_reads_the_rows(clang, kernel, out):
    text = ROPE_KERNEL.replace("@PROTOTYPE@", rope_bf16_contract.PROTOTYPE)
    text = text.replace("@SIGNATURE@", rope_bf16_contract.PROTOTYPE.removesuffix(";"))
    source = kernel("rope.c", text)
    result = build_bf16_verification_executable(
        "rope", source, out, timeout_s=120, flags=STRICT
    )
    assert result.ok, result.log
    assert result.command[1:-2] == (*STRICT, str(PROGRAM_SOURCES["rope"]), str(source))
    m, h, d, draws = 3, 2, 4, 2
    rows = bytes(range(4 * m * d))
    arguments = [str(value) for value in (m, h, d, draws, 20261025)]
    run = local_run.run((out, *arguments), timeout_s=TIMEOUT, stdin_data=rows)
    assert run.timed_out is False
    assert run.returncode == 0, run
    assert len(run.stdout) == draws * (4 + 2 * m * h * d) + 4
    assert run.stdout.endswith(b"end\n")


def test_real_clang_fails_to_link_a_kernel_of_another_kind(clang, kernel, out):
    source = kernel("gemm.c", stub_kernel("gemm"))
    result = build_bf16_verification_executable(
        "rmsnorm", source, out, timeout_s=120, flags=STRICT
    )
    assert result.ok is False
    assert result.timed_out is False
    assert result.returncode not in (0, None)
    assert "hilclaw_rmsnorm_bf16" in result.log
    assert not out.exists()
