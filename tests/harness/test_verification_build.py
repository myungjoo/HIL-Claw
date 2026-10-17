import json
import os
import pickle
import shutil
import sys
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import clang_build
from hilclaw.clang_build import BuildResult, CompilerNotFoundError
from hilclaw.harness import timing_build, verification, verification_build
from hilclaw.harness.verification_build import (
    PROGRAM_SOURCE,
    build_verification_executable,
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

# ADR-0008 decision 4.
PROTOTYPE = "void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)"
GEMM_C = f"""\
#include <stddef.h>

{PROTOTYPE}
{{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {{
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }}
}}
"""
DOT_DECLARATION = "float hilclaw_test_dot(size_t k, size_t n, const float *row, const float *b, size_t j)"
ENTRY_C = f"""\
#include <stddef.h>

{DOT_DECLARATION};

{PROTOTYPE}
{{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++)
            c[i * n + j] = hilclaw_test_dot(k, n, a + i * k, b, j);
}}
"""
DOT_C = f"""\
#include <stddef.h>

{DOT_DECLARATION};

{DOT_DECLARATION}
{{
    float sum = 0.0f;
    for (size_t p = 0; p < k; p++)
        sum += row[p] * b[p * n + j];
    return sum;
}}
"""
NO_GEMM_C = "int unrelated(void)\n{\n    return 0;\n}\n"
STRICT = ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2")
RUN = {
    "m": 3,
    "k": 5,
    "n": 4,
    "draws": 2,
    "seed": 20261008,
    "rtol": 1e-5,
    "atol": 1e-3,
    "timeout_s": TIMEOUT,
}


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

    def write(name="kernel.c", text=GEMM_C):
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


def test_program_source_is_the_c_file_next_to_the_package():
    assert PROGRAM_SOURCE.is_absolute()
    assert PROGRAM_SOURCE.is_file()
    assert PROGRAM_SOURCE.name == "verification_program.c"
    assert PROGRAM_SOURCE.parent == Path(hilclaw.harness.__file__).parent
    assert (PROGRAM_SOURCE.parent / "__init__.py").is_file()
    assert PROGRAM_SOURCE != timing_build.DRIVER_SOURCE


def test_stub_build_succeeds_and_adds_nothing(stub, kernel, out):
    source = kernel()
    result = build_verification_executable(
        source, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    )
    assert isinstance(result, BuildResult)
    assert result.ok is True
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.output == out
    assert result.log == ""
    assert out.read_bytes() == b"artefact"
    argv = stub.call()["argv"]
    assert argv[:3] == [str(PROGRAM_SOURCE), str(source), "-o"]
    assert len(argv) == 4
    temporary = Path(argv[3])
    assert temporary.parent == out.parent
    assert temporary != out
    assert result.command[2:] == tuple(argv)
    assert sorted(p.name for p in out.parent.iterdir()) == ["verification"]


def test_flags_surround_the_sources_in_the_order_given(stub, kernel, out):
    first, second = kernel("a.c"), kernel("b.c")
    flags = ("-O3", "-fopenmp", "-DX=1", "-O0")
    trailing = ("-lm", "-lomp", "-lm")
    result = build_verification_executable(
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
        str(PROGRAM_SOURCE),
        str(first),
        str(second),
        *trailing,
    ]


def test_cwd_and_env_reach_the_compiler(stub, kernel, out, tmp_path):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "from the caller"}
    result = build_verification_executable(
        kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE), cwd=cwd, env=env
    )
    assert result.ok
    call = stub.call()
    assert Path(call["cwd"]).resolve() == cwd.resolve()
    assert call["mark"] == "from the caller"


def test_environment_is_inherited_by_default(stub, kernel, out, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    assert build_verification_executable(
        kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
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
    result = build_verification_executable(
        given, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    )
    assert result.ok
    assert stub.sources() == [str(PROGRAM_SOURCE), *map(str, expected)]


def test_relative_kernel_source_is_taken_from_the_callers_directory(
    stub, kernel, out, monkeypatch
):
    source = kernel()
    monkeypatch.chdir(source.parent)
    assert build_verification_executable(
        source.name, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    ).ok
    assert stub.sources() == [str(PROGRAM_SOURCE), os.path.abspath(source.name)]


def test_compiler_as_a_prefix_sequence(stub, kernel, out):
    interpreter, script = stub(WRITE)
    result = build_verification_executable(
        kernel(), out, timeout_s=TIMEOUT, compiler=[interpreter, "-B", script]
    )
    assert result.ok
    assert result.command[1:3] == ("-B", script)
    assert result.command[3] == str(PROGRAM_SOURCE)


def test_duplicate_sources_are_not_checked(stub, kernel, out):
    source = kernel()
    assert build_verification_executable(
        (source, PROGRAM_SOURCE, source), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
    ).ok
    assert stub.sources() == [
        str(PROGRAM_SOURCE),
        str(source),
        str(PROGRAM_SOURCE),
        str(source),
    ]


def test_arguments_are_handed_over_unchanged_in_one_call(monkeypatch):
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
    assert build_verification_executable(["k.c", "l.c"], output, **given) is outcome
    assert len(calls) == 1
    sources, handed, keywords = calls[0]
    assert sources == (PROGRAM_SOURCE, "k.c", "l.c")
    assert handed is output
    assert keywords.keys() == given.keys()
    assert all(keywords[name] is given[name] for name in given)


def test_defaults_are_those_of_clang_build(monkeypatch):
    calls = []
    monkeypatch.setattr(clang_build, "build", lambda *a, **k: calls.append((a, k)))
    build_verification_executable("k.c", "exe", timeout_s=3)
    assert calls == [
        (
            ((PROGRAM_SOURCE, "k.c"), "exe"),
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


def test_failed_build_is_a_result_with_the_log(stub, kernel, out):
    result = build_verification_executable(
        kernel(), out, timeout_s=TIMEOUT, compiler=stub(FAIL)
    )
    assert result.ok is False
    assert result.returncode == 1
    assert result.timed_out is False
    assert result.log.strip() == "kernel.c:1:1: error: stub says no"
    assert not out.exists()
    assert list(out.parent.iterdir()) == []


def test_timeout_is_a_result(stub, kernel, out):
    result = build_verification_executable(
        kernel(), out, timeout_s=5, compiler=stub(SLEEP)
    )
    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode is None
    assert "before sleep" in result.log
    assert not out.exists()


@pytest.mark.parametrize("empty", [(), [], "generator", b""], ids=repr)
def test_no_kernel_source_is_refused_before_anything_starts(stub, out, empty):
    if empty == "generator":
        empty = (path for path in ())
    with pytest.raises(ValueError, match="no kernel source"):
        build_verification_executable(
            empty, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started
    assert not out.exists()


def test_no_kernel_source_is_tested_before_the_other_arguments(stub, out):
    with pytest.raises(ValueError, match="no kernel source"):
        build_verification_executable((), out, timeout_s="soon", compiler=stub(WRITE))
    assert not stub.started


@pytest.mark.parametrize("value", [None, 7, 1.5], ids=repr)
def test_kernel_sources_that_cannot_be_iterated(stub, out, value):
    with pytest.raises(TypeError):
        build_verification_executable(
            value, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started


@pytest.mark.parametrize("as_list", [False, True])
def test_bytes_path_is_refused(stub, kernel, out, as_list):
    path = os.fsencode(kernel())
    with pytest.raises(TypeError, match="str or os.PathLike"):
        build_verification_executable(
            [path] if as_list else path,
            out,
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert not stub.started


@pytest.fixture
def no_build(monkeypatch):
    calls = []
    monkeypatch.setattr(clang_build, "build", lambda *a, **k: calls.append(a))
    return calls


@pytest.mark.parametrize("value", [None, 7, 1.5], ids=repr)
def test_kernel_sources_that_cannot_be_iterated_name_the_parameter(
    stub, out, no_build, value
):
    with pytest.raises(TypeError) as caught:
        build_verification_executable(
            value, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value.parameter == "kernel_sources"
    assert no_build == []
    assert not stub.started
    assert list(out.parent.iterdir()) == []


def test_a_type_error_from_the_iteration_is_the_same_object(
    stub, kernel, out, no_build
):
    raised = TypeError("x")

    def sources():
        yield kernel()
        raise raised

    with pytest.raises(TypeError) as caught:
        build_verification_executable(
            sources(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value is raised
    assert caught.value.args == ("x",)
    assert caught.value.parameter == "kernel_sources"
    assert no_build == []
    assert not stub.started
    assert list(out.parent.iterdir()) == []


class KernelValueError(ValueError):
    pass


@pytest.mark.parametrize("kind", [ValueError, KernelValueError, UnicodeError])
def test_a_value_error_from_the_iteration_names_the_kernel_sources(
    stub, kernel, out, no_build, kind
):
    raised = kind("x")

    def sources():
        yield kernel()
        raise raised

    with pytest.raises(kind) as caught:
        build_verification_executable(
            sources(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value is raised
    assert type(caught.value) is kind
    assert caught.value.args == ("x",)
    assert caught.value.parameter == "kernel_sources"
    assert no_build == []
    assert not stub.started
    assert list(out.parent.iterdir()) == []


def test_a_value_error_from_the_iteration_keeps_its_parameter_through_pickling(
    stub, out
):
    def sources():
        raise ValueError("x")
        yield

    with pytest.raises(ValueError) as caught:
        build_verification_executable(
            sources(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    copy = pickle.loads(pickle.dumps(caught.value))
    assert type(copy) is ValueError
    assert copy.args == ("x",)
    assert copy.parameter == "kernel_sources"


class FailingPath:
    def __init__(self, error):
        self.error = error

    def __fspath__(self):
        raise self.error


@pytest.mark.parametrize("as_list", [False, True])
def test_a_value_error_from_a_kernel_path_object_keeps_the_parameter_of_build(
    stub, kernel, out, as_list
):
    raised = ValueError("no path")
    source = FailingPath(raised)
    with pytest.raises(ValueError) as caught:
        build_verification_executable(
            [kernel(), source] if as_list else source,
            out,
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert caught.value is raised
    assert caught.value.parameter == "sources"
    assert not stub.started
    assert list(out.parent.iterdir()) == []


def test_other_errors_from_the_iteration_pass_unchanged(stub, kernel, out, no_build):
    raised = RuntimeError("x")

    def sources():
        yield kernel()
        raise raised

    with pytest.raises(RuntimeError) as caught:
        build_verification_executable(
            sources(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert caught.value is raised
    assert not hasattr(caught.value, "parameter")
    assert no_build == []


def test_the_kernel_sources_parameter_survives_pickling(stub, out):
    with pytest.raises(TypeError) as caught:
        build_verification_executable(
            None, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    copy = pickle.loads(pickle.dumps(caught.value))
    assert type(copy) is TypeError
    assert copy.args == caught.value.args
    assert copy.parameter == "kernel_sources"


@pytest.mark.parametrize("empty", [(), [], "generator"], ids=repr)
def test_no_kernel_source_carries_no_parameter(stub, out, empty):
    if empty == "generator":
        empty = (path for path in ())
    with pytest.raises(ValueError) as caught:
        build_verification_executable(
            empty, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not hasattr(caught.value, "parameter")


@pytest.mark.parametrize("as_list", [False, True])
def test_bytes_path_keeps_the_parameter_of_build(stub, kernel, out, as_list):
    path = os.fsencode(kernel())
    with pytest.raises(TypeError) as caught:
        build_verification_executable(
            [path] if as_list else path,
            out,
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert caught.value.parameter == "sources"
    assert not stub.started


@pytest.mark.parametrize(
    ("settings", "parameter"),
    [
        ({"timeout_s": "soon"}, "timeout_s"),
        ({"flags": 7}, "flags"),
        ({"flags": [7]}, "flags"),
        ({"trailing_flags": 7}, "trailing_flags"),
        ({"compiler": 7}, "compiler"),
        ({"compiler": [b"cc"]}, "compiler"),
    ],
    ids=repr,
)
def test_settings_keep_the_parameter_of_build(stub, kernel, out, settings, parameter):
    arguments = {"timeout_s": TIMEOUT, "compiler": stub(WRITE), **settings}
    with pytest.raises(TypeError) as caught:
        build_verification_executable(kernel(), out, **arguments)
    assert caught.value.parameter == parameter
    assert not stub.started


def test_a_missing_timeout_carries_no_parameter(kernel, out):
    with pytest.raises(TypeError) as caught:
        build_verification_executable(kernel(), out)
    assert not hasattr(caught.value, "parameter")


def test_missing_kernel_source(stub, kernel, out):
    missing = kernel().with_name("absent.c")
    with pytest.raises(FileNotFoundError, match="absent.c"):
        build_verification_executable(
            [kernel(), missing], out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started


def test_kernel_source_that_is_a_directory(stub, kernel, out):
    with pytest.raises(IsADirectoryError):
        build_verification_executable(
            kernel().parent, out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started


def test_missing_program_source(stub, kernel, out, monkeypatch):
    absent = kernel().with_name("verification_program.c")
    monkeypatch.setattr(verification_build, "PROGRAM_SOURCE", absent)
    with pytest.raises(FileNotFoundError, match="verification_program.c"):
        build_verification_executable(
            kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started


@pytest.mark.parametrize("name", ["flags", "trailing_flags"])
@pytest.mark.parametrize("flag", [("-o", "x"), ("-ox",), ("--output=x",)])
def test_flag_that_sets_the_output(stub, kernel, out, name, flag):
    with pytest.raises(ValueError, match="must not set the output"):
        build_verification_executable(
            kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE), **{name: flag}
        )
    assert not stub.started


@pytest.mark.parametrize("name", ["flags", "trailing_flags"])
def test_bare_str_as_flags(stub, kernel, out, name):
    with pytest.raises(TypeError, match="sequence of str"):
        build_verification_executable(
            kernel(), out, timeout_s=TIMEOUT, compiler=stub(WRITE), **{name: "-O2"}
        )
    assert not stub.started


def test_timeout_has_no_default(stub, kernel, out):
    with pytest.raises(TypeError, match="timeout_s"):
        build_verification_executable(kernel(), out, compiler=stub(WRITE))
    assert not stub.started


def test_output_has_no_default(stub, kernel):
    with pytest.raises(TypeError, match="output"):
        build_verification_executable(kernel(), timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert not stub.started


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")], ids=repr)
def test_timeout_that_is_not_positive_and_finite(stub, kernel, out, value):
    with pytest.raises(ValueError, match="timeout_s"):
        build_verification_executable(
            kernel(), out, timeout_s=value, compiler=stub(WRITE)
        )
    assert not stub.started


@pytest.mark.parametrize("value", [None, True, "10"], ids=repr)
def test_timeout_of_the_wrong_type(stub, kernel, out, value):
    with pytest.raises(TypeError, match="timeout_s"):
        build_verification_executable(
            kernel(), out, timeout_s=value, compiler=stub(WRITE)
        )
    assert not stub.started


@pytest.mark.parametrize(
    "compiler", ["hilclaw-no-such-compiler", ("hilclaw-no-such-compiler", "clang")]
)
def test_compiler_that_does_not_exist(kernel, out, compiler):
    with pytest.raises(CompilerNotFoundError):
        build_verification_executable(
            kernel(), out, timeout_s=TIMEOUT, compiler=compiler
        )
    assert not out.exists()


def test_empty_compiler_prefix(kernel, out):
    with pytest.raises(ValueError, match="prefix is empty"):
        build_verification_executable(kernel(), out, timeout_s=TIMEOUT, compiler=())
    assert not out.exists()


def test_output_directory_that_does_not_exist(stub, kernel, out):
    with pytest.raises(FileNotFoundError, match="output directory"):
        build_verification_executable(
            kernel(),
            out.parent / "absent" / "verification",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert not stub.started


def test_output_that_is_a_directory(stub, kernel, out):
    with pytest.raises(IsADirectoryError):
        build_verification_executable(
            kernel(), out.parent, timeout_s=TIMEOUT, compiler=stub(WRITE)
        )
    assert not stub.started


def test_real_clang_builds_an_executable_that_passes_a_verification_run(
    clang, kernel, out
):
    source = kernel()
    result = build_verification_executable(source, out, timeout_s=120, flags=STRICT)
    assert result.ok, result.log
    assert result.command[1:-2] == (*STRICT, str(PROGRAM_SOURCE), str(source))
    run = verification.run_verification(out, **RUN)
    assert run.broken is None, run.run
    assert run.verdict is verification.Verdict.PASS, run.counts
    assert run.run.command[0] == str(out)


def test_real_clang_builds_all_source_files_of_one_kernel(clang, kernel, out):
    sources = (kernel("entry.c", ENTRY_C), kernel("dot.c", DOT_C))
    result = build_verification_executable(sources, out, timeout_s=120, flags=STRICT)
    assert result.ok, result.log
    run = verification.run_verification(out, **RUN)
    assert run.broken is None, run.run
    assert run.verdict is verification.Verdict.PASS, run.counts


def test_real_clang_fails_to_link_a_kernel_without_the_entry_point(clang, kernel, out):
    result = build_verification_executable(
        kernel("other.c", NO_GEMM_C), out, timeout_s=120, flags=STRICT
    )
    assert result.ok is False
    assert result.timed_out is False
    assert result.returncode not in (0, None)
    assert "hilclaw_gemm" in result.log
    assert not out.exists()
