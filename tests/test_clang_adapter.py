import builtins
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hilclaw import clang_adapter, local_run, standin_container, targets, vendor_adapter
from hilclaw.clang_adapter import (
    PROGRAM,
    assemble_build,
    assemble_probe,
    assemble_run,
    build,
    interpret_container_probe,
    interpret_probe,
    probe,
    run,
)
from hilclaw.vendor_adapter import (
    ABSENT,
    BROKEN,
    GO_ON,
    PRESENT,
    TOOL_FAILURE,
    UNREADABLE,
    BuildCall,
    Probe,
    RunCall,
)

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")

MISSING = "hilclaw-no-such-program"
EXE = ".exe" if os.name == "nt" else ""
LIMIT = 60

GOOD_C = "double scale(double x) { return 2.0 * x; }\n"
BAD_C = "int broken( {\n"
EXIT_C = '#include <stdio.h>\nint main(void) { puts("ran"); return %d; }\n'
LOOP_C = "int main(void) { volatile unsigned long n = 0; for (;;) n++; }\n"

# Fault-injection scripts (ADR-0194 decision 6), each run by this interpreter
# from the test's own temporary directory and passed only as ``program``.
HANG = "import threading\nthreading.Event().wait()\n"
SILENT_STATUS = "import sys\nsys.exit(70)\n"
SIGNAL = "import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)\n"
NO_ARTEFACT = "pass\n"
NO_LINE = "pass\n"


class BytesPath:
    def __fspath__(self):
        return b"p"


def make_target(**changes):
    values = {
        "flags": ("-O2",),
        "trailing_flags": (),
        "waiter_flags": (),
        "env": None,
        "build_time_limit_s": LIMIT,
        "process_time_limit_cap_s": LIMIT,
        "contracts": (),
        "memory_limit_bytes": None,
        "unit": "ns",
        "units_per_ns": 1,
        "model_run": False,
        "instance_start": False,
    }
    values.update(changes)
    return targets.Target(**values)


@pytest.fixture
def clang():
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


@pytest.fixture
def script(tmp_path):
    directory = tmp_path / "fault"
    directory.mkdir()

    def write(body):
        path = directory / "tool.py"
        path.write_text(body, encoding="utf-8")
        return (sys.executable, str(path))

    return write


def source(tmp_path, text, name="k.c"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def built(tmp_path, text):
    out = tmp_path / ("prog" + EXE)
    outcome = build(make_target(flags=("-O0",)), source(tmp_path, text), out)
    assert outcome.form == GO_ON, outcome
    return out


def assert_form(outcome, form, condition=None, kind=None):
    assert type(outcome) is vendor_adapter.Outcome
    assert (outcome.form, outcome.condition, outcome.kind) == (form, condition, kind)


def test_program_constant_is_clang():
    assert PROGRAM == "clang"


def test_assemble_build_takes_the_target_values():
    target = make_target(
        flags=("-O3", "-c"),
        trailing_flags=("-lm",),
        env={"A": "1"},
        build_time_limit_s=7,
    )
    call = assemble_build(target, ["a.c", Path("b.c")], "out.o")
    assert call == BuildCall(
        compiler=("clang",),
        flags=("-O3", "-c"),
        sources=("a.c", Path("b.c")),
        trailing_flags=("-lm",),
        output="out.o",
        env=target.env,
        timeout_s=7,
        files=(),
    )


def test_assemble_build_takes_one_source_and_a_program_prefix():
    call = assemble_build(make_target(), Path("a.c"), "o", program=["ccache", "clang"])
    assert call.sources == (Path("a.c"),)
    assert call.compiler == ("ccache", "clang")
    call = assemble_build(make_target(), "a.c", "o", program=Path("bin") / "cc")
    assert call.compiler == (os.fspath(Path("bin") / "cc"),)


def test_assemble_run_caps_the_time_limit_and_takes_the_env():
    target = make_target(process_time_limit_cap_s=5, env={"B": "2"})
    call = assemble_run(target, Path("p"), ["x", "y"], timeout_s=9)
    assert call == RunCall(
        command=("p", "x", "y"), env=target.env, timeout_s=5, files=()
    )
    assert assemble_run(target, "p", timeout_s=2.5).timeout_s == 2.5


def test_assemble_probe_is_the_version_query():
    assert assemble_probe(timeout_s=3) == RunCall(
        command=("clang", "--version"), env=None, timeout_s=3, files=()
    )
    call = assemble_probe(timeout_s=3, program=("py", "tool.py"))
    assert call.command == ("py", "tool.py", "--version")


def test_assemble_parts_are_pure(monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("an assemble part reached outside")

    class NoEnviron(dict):
        def __getitem__(self, key):
            refused()

        get = __getitem__

    target = make_target(env={"A": "1"})
    monkeypatch.setattr(subprocess, "Popen", refused)
    monkeypatch.setattr(subprocess, "run", refused)
    monkeypatch.setattr(os, "environ", NoEnviron())
    monkeypatch.setattr(os, "stat", refused)
    monkeypatch.setattr(os, "getcwd", refused)
    monkeypatch.setattr(time, "time", refused)
    monkeypatch.setattr(time, "monotonic", refused)
    monkeypatch.setattr(builtins, "open", refused)
    assert assemble_build(target, ["a.c"], "o").env == target.env
    assert assemble_run(target, "p", ["a"], timeout_s=1).command == ("p", "a")
    assert assemble_probe(timeout_s=1).command == ("clang", "--version")


@pytest.mark.parametrize(
    ("call", "error", "parameter"),
    [
        (lambda: assemble_build(None, "a.c", "o"), TypeError, "target"),
        (lambda: assemble_build(make_target(), 3, "o"), TypeError, "sources"),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=3),
            TypeError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=b"cc"),
            TypeError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=""),
            ValueError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=()),
            ValueError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=("cc", 1)),
            TypeError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=("cc", "")),
            ValueError,
            "program",
        ),
        (lambda: assemble_run("t", "p", timeout_s=1), TypeError, "target"),
        (lambda: assemble_run(make_target(), 3, timeout_s=1), TypeError, "executable"),
        (
            lambda: assemble_run(make_target(), b"p", timeout_s=1),
            TypeError,
            "executable",
        ),
        (
            lambda: assemble_run(make_target(), BytesPath(), timeout_s=1),
            TypeError,
            "executable",
        ),
        (
            lambda: assemble_run(make_target(), "", timeout_s=1),
            ValueError,
            "executable",
        ),
        (
            lambda: assemble_run(make_target(), "p", "a", timeout_s=1),
            TypeError,
            "arguments",
        ),
        (
            lambda: assemble_run(make_target(), "p", 3, timeout_s=1),
            TypeError,
            "arguments",
        ),
        (
            lambda: assemble_run(make_target(), "p", [b"a"], timeout_s=1),
            TypeError,
            "arguments",
        ),
        (
            lambda: assemble_run(make_target(), "p", timeout_s=0),
            ValueError,
            "timeout_s",
        ),
        (
            lambda: assemble_run(make_target(), "p", timeout_s="1"),
            TypeError,
            "timeout_s",
        ),
        (lambda: assemble_probe(timeout_s=float("inf")), ValueError, "timeout_s"),
        (lambda: assemble_probe(timeout_s=None), TypeError, "timeout_s"),
        (lambda: assemble_probe(timeout_s=1, program=None), TypeError, "program"),
    ],
)
def test_assemble_parts_refuse_bad_arguments(call, error, parameter):
    with pytest.raises(error) as caught:
        call()
    assert caught.value.parameter == parameter


@pytest.mark.parametrize("bad", [None, "t"])
def test_execute_parts_refuse_before_anything_starts(tmp_path, monkeypatch, bad):
    def refused(*args, **kwargs):
        raise AssertionError("an executor was called")

    monkeypatch.setattr(clang_adapter.clang_build, "build", refused)
    monkeypatch.setattr(clang_adapter.local_run, "run", refused)
    with pytest.raises(TypeError) as caught:
        build(bad, "a.c", tmp_path / "o")
    assert caught.value.parameter == "target"
    with pytest.raises(TypeError) as caught:
        run(bad, "p", timeout_s=1)
    assert caught.value.parameter == "target"
    with pytest.raises(ValueError) as caught:
        probe(timeout_s=-1)
    assert caught.value.parameter == "timeout_s"


def test_real_clang_builds_to_go_on(clang, tmp_path):
    out = tmp_path / "k.o"
    outcome = build(make_target(flags=("-O2", "-c")), source(tmp_path, GOOD_C), out)
    assert_form(outcome, GO_ON)
    assert outcome.carried == out
    assert out.is_file()


def test_real_clang_compile_failure_is_build_exit_status(clang, tmp_path):
    out = tmp_path / "k.o"
    outcome = build(make_target(flags=("-c",)), source(tmp_path, BAD_C), out)
    assert_form(outcome, BROKEN, condition="build_exit_status")
    assert not out.exists()


def test_real_clang_executable_exit_0_goes_on(clang, tmp_path):
    program = built(tmp_path, EXIT_C % 0)
    outcome = run(make_target(), program, timeout_s=LIMIT)
    assert_form(outcome, GO_ON)
    assert outcome.carried.strip() == b"ran"


def test_real_clang_executable_exit_3_is_exit_status(clang, tmp_path):
    program = built(tmp_path, EXIT_C % 3)
    assert_form(
        run(make_target(), program, timeout_s=LIMIT), BROKEN, condition="exit_status"
    )


def test_real_clang_executable_past_the_limit_is_time_limit(clang, tmp_path):
    program = built(tmp_path, LOOP_C)
    outcome = run(make_target(process_time_limit_cap_s=0.5), program, timeout_s=LIMIT)
    assert_form(outcome, BROKEN, condition="time_limit")


def test_real_clang_probe_reports_present_with_a_version(clang):
    found = probe(timeout_s=LIMIT)
    assert type(found) is Probe
    assert found.state == PRESENT
    assert "clang version" in found.version
    assert found.version == found.version.strip()


def test_missing_program_is_reported_by_each_job(tmp_path):
    src = source(tmp_path, GOOD_C)
    assert_form(
        build(make_target(), src, tmp_path / "k.o", program=MISSING),
        TOOL_FAILURE,
        kind="compiler_unavailable",
    )
    assert_form(
        run(make_target(), tmp_path / MISSING, timeout_s=LIMIT),
        TOOL_FAILURE,
        kind="executable_unstartable",
    )
    found = probe(timeout_s=LIMIT, program=MISSING)
    assert (found.state, found.version) == (ABSENT, None)


@posix_only
def test_file_that_cannot_start_is_executable_unstartable(tmp_path):
    program = tmp_path / "not-a-program"
    program.write_bytes(b"\x00\x01\x02 not an executable\n")
    program.chmod(0o755)
    assert_form(
        run(make_target(), program, timeout_s=LIMIT),
        TOOL_FAILURE,
        kind="executable_unstartable",
    )
    found = probe(timeout_s=LIMIT, program=program)
    assert found.state == ABSENT
    assert_form(
        build(
            make_target(), source(tmp_path, GOOD_C), tmp_path / "k.o", program=program
        ),
        TOOL_FAILURE,
        kind="compiler_unavailable",
    )


def test_fault_compiler_that_hangs_is_build_time_limit(script, tmp_path):
    # Stands for a compiler that never ends (ADR-0194 decision 6: the tool's own hang).
    outcome = build(
        make_target(build_time_limit_s=0.5),
        source(tmp_path, GOOD_C),
        tmp_path / "k.o",
        program=script(HANG),
    )
    assert_form(outcome, BROKEN, condition="build_time_limit")


def test_fault_compiler_with_a_silent_status_is_build_exit_status(script, tmp_path):
    # Stands for a compiler that ends with a non-zero status and no diagnostic
    # (ADR-0194 decision 6: the tool's own crash; ADR-0060 decision 4, S7).
    outcome = build(
        make_target(),
        source(tmp_path, GOOD_C),
        tmp_path / "k.o",
        program=script(SILENT_STATUS),
    )
    assert_form(outcome, BROKEN, condition="build_exit_status")


@posix_only
def test_fault_compiler_ended_by_a_signal_is_build_exit_status(script, tmp_path):
    # Stands for a compiler that crashes by a signal (ADR-0194 decision 6;
    # ADR-0060 decision 4 reads a signal as S7).
    outcome = build(
        make_target(),
        source(tmp_path, GOOD_C),
        tmp_path / "k.o",
        program=script(SIGNAL),
    )
    assert_form(outcome, BROKEN, condition="build_exit_status")


def test_fault_compiler_without_artefact_is_build_output_missing(script, tmp_path):
    # Stands for a compiler that exits 0 and leaves no artefact (ADR-0060 decision 4, S9).
    out = tmp_path / "k.o"
    outcome = build(
        make_target(), source(tmp_path, GOOD_C), out, program=script(NO_ARTEFACT)
    )
    assert_form(outcome, TOOL_FAILURE, kind="build_output_missing")
    assert not out.exists()


def test_fault_version_query_that_hangs_is_unreadable(script):
    # Stands for a version query that never ends (ADR-0194 decisions 6 and 7).
    found = probe(timeout_s=0.5, program=script(HANG))
    assert (found.state, found.version) == (UNREADABLE, None)


def test_fault_version_query_without_a_line_is_unreadable(script):
    # Stands for a version query that prints no line (ADR-0194 decisions 6 and 7;
    # clang_build.compiler_version refuses the same).
    found = probe(timeout_s=LIMIT, program=script(NO_LINE))
    assert (found.state, found.version) == (UNREADABLE, None)


def recorded(returncode=0, stdout=b"", timed_out=False):
    return local_run.RunResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=b"",
        command=("clang", "--version"),
        duration_s=0.1,
    )


@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (
            recorded(stdout=b"  clang version 9.9.9 (x)  \nTarget: y\n"),
            PRESENT,
            "clang version 9.9.9 (x)",
        ),
        (recorded(stdout=b"caf\xe9 1\n"), PRESENT, "caf� 1"),
        (recorded(stdout=b""), UNREADABLE, None),
        (recorded(stdout=b"   \nclang version 1\n"), UNREADABLE, None),
        (recorded(returncode=1, stdout=b"clang version 1\n"), UNREADABLE, None),
        (recorded(returncode=-9), UNREADABLE, None),
        (recorded(returncode=None, timed_out=True), UNREADABLE, None),
        (local_run.ProgramNotFoundError("x"), ABSENT, None),
        (OSError(13, "Permission denied", "/usr/bin/clang"), ABSENT, None),
    ],
)
def test_interpret_probe_on_recorded_answers(answer, state, version):
    found = interpret_probe(answer, "clang")
    assert type(found) is Probe
    assert (found.state, found.version) == (state, version)
    assert type(found.message) is str and found.message


@pytest.mark.parametrize(
    "error", [OSError(5, "I/O"), KeyboardInterrupt(), ValueError("v")]
)
def test_interpret_probe_leaves_other_errors(error):
    assert interpret_probe(error, "clang") is None


def test_interpret_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_probe(b"clang version", "clang")
    assert caught.value.parameter == "answer"
    with pytest.raises(TypeError) as caught:
        interpret_probe(recorded(), 3)
    assert caught.value.parameter == "program"


def test_execute_parts_raise_unplaced_errors_unchanged(tmp_path, monkeypatch):
    error = OSError(5, "I/O after start")
    built_error = RuntimeError("build")

    def raising_run(*args, **kwargs):
        raise error

    def raising_build(*args, **kwargs):
        raise built_error

    monkeypatch.setattr(clang_adapter.local_run, "run", raising_run)
    monkeypatch.setattr(clang_adapter.clang_build, "build", raising_build)
    with pytest.raises(OSError) as caught:
        run(make_target(), "p", timeout_s=1)
    assert caught.value is error
    with pytest.raises(OSError) as caught:
        probe(timeout_s=1)
    assert caught.value is error
    with pytest.raises(RuntimeError) as caught:
        build(make_target(), "a.c", tmp_path / "o")
    assert caught.value is built_error


def test_execute_parts_hand_the_assembled_values(tmp_path, monkeypatch):
    seen = {}

    def fake_run(command, *, timeout_s, env=None):
        seen["run"] = (command, timeout_s, env)
        return recorded(stdout=b"v 1\n")

    def fake_build(sources, output, **kwargs):
        seen["build"] = (sources, output, kwargs)
        raise vendor_adapter.clang_build.CompilerNotFoundError("x")

    monkeypatch.setattr(clang_adapter.local_run, "run", fake_run)
    monkeypatch.setattr(clang_adapter.clang_build, "build", fake_build)
    target = make_target(
        env={"E": "1"}, process_time_limit_cap_s=4, trailing_flags=("-lm",)
    )
    assert run(target, "p", ["a"], timeout_s=9).carried == b"v 1\n"
    assert seen["run"] == (("p", "a"), 4, target.env)
    assert probe(timeout_s=2).version == "v 1"
    assert seen["run"] == (("clang", "--version"), 2, None)
    outcome = build(target, "a.c", "o")
    assert outcome.kind == "compiler_unavailable"
    assert seen["build"] == (
        ("a.c",),
        "o",
        {
            "timeout_s": target.build_time_limit_s,
            "flags": target.flags,
            "trailing_flags": ("-lm",),
            "compiler": ("clang",),
            "env": target.env,
        },
    )


def contained(returncode=0, stdout=b"", timed_out=False):
    return standin_container.ContainerResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=b"",
        command=("docker", "run"),
        duration_s=0.1,
        name="hilclaw-standin-" + "0" * 32,
        removal=None,
    )


@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (
            contained(stdout=b" clang version 9.9.9 \nTarget: y\n"),
            PRESENT,
            "clang version 9.9.9",
        ),
        (contained(stdout=b""), UNREADABLE, None),
        (contained(stdout=b"\nclang version 1\n"), UNREADABLE, None),
        (contained(returncode=1, stdout=b"clang version 1\n"), UNREADABLE, None),
        (contained(returncode=-9), UNREADABLE, None),
        (contained(returncode=124), UNREADABLE, None),
        (contained(returncode=126), ABSENT, None),
        (contained(returncode=127), ABSENT, None),
        (contained(returncode=None, timed_out=True), UNREADABLE, None),
    ],
)
def test_interpret_container_probe_on_recorded_answers(answer, state, version):
    found = interpret_container_probe(answer)
    assert type(found) is Probe
    assert (found.state, found.version) == (state, version)
    assert type(found.message) is str and found.message


@pytest.mark.parametrize(
    "answer",
    [
        contained(returncode=125),
        local_run.ProgramNotFoundError("docker"),
        standin_container.NoNumericUserError("no uid"),
        OSError(5, "I/O"),
        KeyboardInterrupt(),
    ],
)
def test_interpret_container_probe_leaves_an_unused_container_to_the_caller(answer):
    assert interpret_container_probe(answer) is None


def test_interpret_container_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_container_probe(recorded())
    assert caught.value.parameter == "answer"
    with pytest.raises(ValueError):
        interpret_container_probe(contained(returncode=None))
    with pytest.raises(ValueError):
        interpret_container_probe(contained(returncode=True))
