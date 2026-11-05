import builtins
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hilclaw import clang_adapter, local_run, standin_container, targets, vendor_adapter
from hilclaw.harness import timing
from hilclaw.harness.measurement import N_MIN
from hilclaw.qnn_adapter import (
    BUILD_PROGRAM,
    VERSION_PROGRAM,
    assemble_build,
    assemble_probe,
    assemble_run,
    assemble_timing,
    build,
    interpret_container_probe,
    interpret_probe,
    measure,
    probe,
    run,
)
from hilclaw.run_parameters import Bf16TimingParameters, TimingParameters
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

# Kept as *.c.in, outside the CI C gate (no SDK headers there); copied to *.c.
FIXTURES = Path(__file__).resolve().parent / "qnn_fixtures"
FIXTURE = FIXTURES / "add.c.in"
MISSING = "hilclaw-no-such-program"
EXE = ".exe" if os.name == "nt" else ""
LIMIT = 300
VERSION = b"QNN SDK v2.37.0.250724175447_124859"
PID_LINE = b"qnn-net-run pid:4242\r\n"
PARAMETERS = TimingParameters(2, 3, 4, 10, "interval", 42)
DRIVER_ARGUMENTS = ("2", "3", "4", "5", "10", "0.05", "interval", "42")
REPORT = b"resolution_ns 100\n" + b"interval_ns 5000\n" * N_MIN + b"stop converged\n"

# Fault-injection scripts (ADR-0194 decision 6), each run by this interpreter
# from the test's own temporary directory and passed only as ``program`` or
# as the run's executable argument.
HANG = "import threading\nthreading.Event().wait()\n"
SILENT_STATUS = "import sys\nsys.exit(70)\n"
SIGNAL = "import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)\n"
NO_ARTEFACT = "pass\n"
ALLOCATION_FAILURE = (
    "import sys\nsys.stderr.write('QnnGraph_create failed: 1002\\n')\nsys.exit(1)\n"
)


class BytesPath:
    def __fspath__(self):
        return b"QnnHtp.dll"


def make_target(**changes):
    values = {
        "flags": (),
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
def qnn_sdk():
    runner = shutil.which(VERSION_PROGRAM)
    if runner is None:
        pytest.skip(
            "qnn-net-run is not on PATH (FR-19 (5): a vendor tool's execution test)"
        )
    return Path(runner).resolve().parents[2]


@pytest.fixture
def qnn(qnn_sdk):
    root = qnn_sdk
    compiler = shutil.which("clang") or (os.name == "nt" and shutil.which("gcc"))
    if not compiler:
        pytest.skip("no C compiler (clang, or gcc on Windows) is on PATH")
    host = "x86_64-windows-msvc" if os.name == "nt" else "x86_64-linux-clang"
    library = root / "lib" / host
    search = "PATH" if os.name == "nt" else "LD_LIBRARY_PATH"
    env = dict(os.environ)
    env[search] = os.pathsep.join(filter(None, (str(library), env.get(search))))
    target = make_target(
        flags=("-I" + str(root / "include" / "QNN"),),
        trailing_flags=() if os.name == "nt" else ("-ldl",),
        env=env,
    )
    backend = library / ("QnnHtp.dll" if os.name == "nt" else "libQnnHtp.so")
    return target, compiler, str(backend)


@pytest.fixture
def script(tmp_path):
    directory = tmp_path / "fault"
    directory.mkdir()

    def write(body):
        path = directory / "tool.py"
        path.write_text(body, encoding="utf-8")
        return (sys.executable, str(path))

    return write


def source(tmp_path, name):
    path = tmp_path / (name + ".c")
    shutil.copyfile(FIXTURES / (name + ".c.in"), path)
    return path


def assert_form(outcome, form, condition=None, kind=None):
    assert type(outcome) is vendor_adapter.Outcome
    assert (outcome.form, outcome.condition, outcome.kind) == (form, condition, kind)


def recorded(returncode=0, stdout=b"", stderr=b"", timed_out=False):
    return local_run.RunResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        command=("tool",),
        duration_s=0.1,
    )


def contained(returncode=0, stdout=b"", stderr=b"", timed_out=False):
    return standin_container.ContainerResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
        command=("docker", "run"),
        duration_s=0.1,
        name="hilclaw-standin-" + "0" * 32,
        removal=None,
    )


def test_program_constants():
    assert (BUILD_PROGRAM, VERSION_PROGRAM) == ("clang", "qnn-net-run")


def test_assemble_build_takes_the_target_values_and_adds_no_flag():
    target = make_target(
        flags=("-O2", "-Isdk/include/QNN"),
        trailing_flags=("-ldl",),
        env={"A": "1"},
        build_time_limit_s=7,
    )
    call = assemble_build(target, ["a.c", Path("b.c")], "out")
    assert call == BuildCall(
        compiler=("clang",),
        flags=("-O2", "-Isdk/include/QNN"),
        sources=("a.c", Path("b.c")),
        trailing_flags=("-ldl",),
        output="out",
        env=target.env,
        timeout_s=7,
        files=(),
    )
    bare = assemble_build(make_target(), "a.c", "o", program=("ccache", "gcc"))
    assert (bare.compiler, bare.flags, bare.trailing_flags) == (
        ("ccache", "gcc"),
        (),
        (),
    )


def test_assemble_run_caps_the_time_limit_and_takes_the_env():
    target = make_target(process_time_limit_cap_s=5, env={"LD_LIBRARY_PATH": "lib"})
    assert assemble_run(target, Path("p"), ["libQnnHtp.so"], timeout_s=9) == RunCall(
        command=("p", "libQnnHtp.so"), env=target.env, timeout_s=5, files=()
    )
    assert assemble_run(target, "p", timeout_s=2.5).timeout_s == 2.5


def test_assemble_probe_is_the_version_query():
    assert assemble_probe(timeout_s=3) == RunCall(
        command=("qnn-net-run", "--version"), env=None, timeout_s=3, files=()
    )
    assert assemble_probe(timeout_s=3, program=Path("bin") / "net-run").command == (
        os.fspath(Path("bin") / "net-run"),
        "--version",
    )
    assert assemble_probe(timeout_s=3, program=("py", "t.py")).command == (
        "py",
        "t.py",
        "--version",
    )


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
    assert assemble_probe(timeout_s=1).command == ("qnn-net-run", "--version")
    assert assemble_timing(target, "p", "b.so", PARAMETERS, timeout_s=1).command == (
        "p",
        "b.so",
        *DRIVER_ARGUMENTS,
    )


@pytest.mark.parametrize(
    ("call", "error", "parameter"),
    [
        (lambda: assemble_build(None, "a.c", "o"), TypeError, "target"),
        (lambda: assemble_build(make_target(), 3, "o"), TypeError, "sources"),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=b"clang"),
            TypeError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=()),
            ValueError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.c", "o", program=("cc", "")),
            ValueError,
            "program",
        ),
        (lambda: assemble_run("t", "p", timeout_s=1), TypeError, "target"),
        (
            lambda: assemble_run(make_target(), "", timeout_s=1),
            ValueError,
            "executable",
        ),
        (
            lambda: assemble_run(make_target(), b"p", timeout_s=1),
            TypeError,
            "executable",
        ),
        (
            lambda: assemble_run(make_target(), "p", "libQnnHtp.so", timeout_s=1),
            TypeError,
            "arguments",
        ),
        (
            lambda: assemble_run(make_target(), "p", [Path("lib")], timeout_s=1),
            TypeError,
            "arguments",
        ),
        (
            lambda: assemble_run(make_target(), "p", timeout_s=0),
            ValueError,
            "timeout_s",
        ),
        (lambda: assemble_probe(timeout_s=None), TypeError, "timeout_s"),
        (lambda: assemble_probe(timeout_s=True), TypeError, "timeout_s"),
        (
            lambda: assemble_probe(timeout_s=float("inf")),
            ValueError,
            "timeout_s",
        ),
        (lambda: assemble_probe(timeout_s=1, program=""), ValueError, "program"),
        (lambda: assemble_probe(timeout_s=1, program=None), TypeError, "program"),
        (
            lambda: assemble_probe(timeout_s=1, program=("net-run", 2)),
            TypeError,
            "program",
        ),
    ],
)
def test_assemble_parts_refuse_bad_arguments(call, error, parameter):
    with pytest.raises(error) as caught:
        call()
    assert caught.value.parameter == parameter


def test_execute_parts_refuse_before_anything_starts(tmp_path, monkeypatch):
    def refused(*args, **kwargs):
        raise AssertionError("an executor was called")

    monkeypatch.setattr(clang_adapter.clang_build, "build", refused)
    monkeypatch.setattr(local_run, "run", refused)
    with pytest.raises(TypeError) as caught:
        build("t", "a.c", tmp_path / "o")
    assert caught.value.parameter == "target"
    with pytest.raises(ValueError) as caught:
        build(make_target(), "a.c", tmp_path / "o", program=())
    assert caught.value.parameter == "program"
    with pytest.raises(TypeError) as caught:
        run(None, "p", timeout_s=1)
    assert caught.value.parameter == "target"
    with pytest.raises(ValueError) as caught:
        run(make_target(), "p", timeout_s=-1)
    assert caught.value.parameter == "timeout_s"
    with pytest.raises(ValueError) as caught:
        probe(timeout_s=-1)
    assert caught.value.parameter == "timeout_s"
    with pytest.raises(TypeError) as caught:
        probe(timeout_s=1, program=3)
    assert caught.value.parameter == "program"


def test_execute_parts_hand_the_assembled_values(tmp_path, monkeypatch):
    seen = {}

    def fake_run(command, *, timeout_s, env=None):
        seen["run"] = (command, timeout_s, env)
        if command[0] == "qnn-net-run":
            return recorded(stdout=PID_LINE, stderr=VERSION + b"\r\n")
        return recorded(stdout=b"11 22 33 44\n")

    def fake_build(sources, output, **kwargs):
        seen["build"] = (sources, output, kwargs)
        raise clang_adapter.clang_build.CompilerNotFoundError("clang")

    monkeypatch.setattr(local_run, "run", fake_run)
    monkeypatch.setattr(clang_adapter.clang_build, "build", fake_build)
    target = make_target(
        env={"LD_LIBRARY_PATH": "lib"}, process_time_limit_cap_s=4, flags=("-Iq",)
    )
    assert run(target, "p", ["b.so"], timeout_s=9).carried == b"11 22 33 44\n"
    assert seen["run"] == (("p", "b.so"), 4, target.env)
    assert probe(timeout_s=2).version == VERSION.decode()
    assert seen["run"] == (("qnn-net-run", "--version"), 2, None)
    assert_form(build(target, "a.c", "o"), TOOL_FAILURE, kind="compiler_unavailable")
    assert seen["build"] == (
        ("a.c",),
        "o",
        {
            "timeout_s": target.build_time_limit_s,
            "flags": ("-Iq",),
            "trailing_flags": (),
            "compiler": ("clang",),
            "env": target.env,
        },
    )


def test_execute_parts_raise_unplaced_errors_unchanged(tmp_path, monkeypatch):
    error = OSError(5, "I/O after start")
    built_error = RuntimeError("build")

    def raising_run(*args, **kwargs):
        raise error

    def raising_build(*args, **kwargs):
        raise built_error

    monkeypatch.setattr(local_run, "run", raising_run)
    monkeypatch.setattr(clang_adapter.clang_build, "build", raising_build)
    for call in (
        lambda: run(make_target(), "p", timeout_s=1),
        lambda: probe(timeout_s=1),
    ):
        with pytest.raises(OSError) as caught:
            call()
        assert caught.value is error
    with pytest.raises(RuntimeError) as caught:
        build(make_target(), "a.c", tmp_path / "o")
    assert caught.value is built_error


def test_probe_places_a_missing_program_from_the_executor(monkeypatch):
    def not_found(command, *, timeout_s, env=None):
        raise local_run.ProgramNotFoundError(command[0])

    monkeypatch.setattr(local_run, "run", not_found)
    found = probe(timeout_s=1)
    assert (found.state, found.version) == (ABSENT, None)


@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (recorded(stdout=PID_LINE, stderr=VERSION + b"\r\n"), PRESENT, VERSION),
        (recorded(stdout=VERSION + b"\n"), PRESENT, VERSION),
        (
            recorded(stdout=b"  " + VERSION + b"  \n", stderr=b"QNN SDK v9\n"),
            PRESENT,
            VERSION,
        ),
        (
            recorded(stdout=PID_LINE, stderr=b"\nnote\n  " + VERSION + b"\n"),
            PRESENT,
            VERSION,
        ),
        (recorded(stdout=PID_LINE), UNREADABLE, None),
        (recorded(stdout=PID_LINE, stderr=b"qnn sdk v2.37.0\n"), UNREADABLE, None),
        (recorded(stdout=PID_LINE, stderr=b"SDK v2.37.0\n"), UNREADABLE, None),
        (recorded(), UNREADABLE, None),
        (recorded(returncode=1, stderr=VERSION), UNREADABLE, None),
        (
            recorded(returncode=127, stderr=b"libc++.so.1: cannot open"),
            UNREADABLE,
            None,
        ),
        (recorded(returncode=-11), UNREADABLE, None),
        (recorded(returncode=None, timed_out=True, stderr=VERSION), UNREADABLE, None),
        (local_run.ProgramNotFoundError("qnn-net-run"), ABSENT, None),
        (OSError(13, "Permission denied", "/opt/qairt/bin/qnn-net-run"), ABSENT, None),
    ],
)
def test_interpret_probe_on_recorded_answers(answer, state, version):
    found = interpret_probe(answer, "qnn-net-run")
    assert type(found) is Probe
    expected = version.decode() if version is not None else None
    assert (found.state, found.version) == (state, expected)
    assert type(found.message) is str and found.message


@pytest.mark.parametrize(
    "error", [OSError(5, "I/O"), KeyboardInterrupt(), ValueError()]
)
def test_interpret_probe_leaves_other_errors(error):
    assert interpret_probe(error, "qnn-net-run") is None


def test_interpret_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_probe(VERSION, "qnn-net-run")
    assert caught.value.parameter == "answer"
    with pytest.raises(TypeError) as caught:
        interpret_probe(recorded(), 3)
    assert caught.value.parameter == "program"
    with pytest.raises(ValueError) as caught:
        interpret_probe(recorded(), "")
    assert caught.value.parameter == "program"
    with pytest.raises(ValueError):
        interpret_probe(recorded(returncode=None), "qnn-net-run")


@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (contained(stdout=PID_LINE, stderr=VERSION + b"\n"), PRESENT, VERSION),
        (contained(stdout=b"\n" + VERSION + b"\n"), PRESENT, VERSION),
        (contained(stdout=PID_LINE), UNREADABLE, None),
        (contained(returncode=1, stderr=VERSION), UNREADABLE, None),
        (contained(returncode=126), ABSENT, None),
        (contained(returncode=127), ABSENT, None),
        (contained(returncode=None, timed_out=True), UNREADABLE, None),
    ],
)
def test_interpret_container_probe_on_recorded_answers(answer, state, version):
    found = interpret_container_probe(answer)
    assert type(found) is Probe
    expected = version.decode() if version is not None else None
    assert (found.state, found.version) == (state, expected)
    assert type(found.message) is str and found.message


@pytest.mark.parametrize(
    "answer",
    [
        contained(returncode=125),
        local_run.ProgramNotFoundError("docker"),
        OSError(),
    ],
)
def test_interpret_container_probe_leaves_an_unused_container(answer):
    assert interpret_container_probe(answer) is None


def test_interpret_container_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_container_probe(recorded())
    assert caught.value.parameter == "answer"
    with pytest.raises(ValueError):
        interpret_container_probe(contained(returncode=None))


def test_real_qnn_program_builds_and_runs_on_the_htp_emulator(qnn, tmp_path):
    target, compiler, backend = qnn
    out = tmp_path / ("add" + EXE)
    outcome = build(target, source(tmp_path, "add"), out, program=compiler)
    assert_form(outcome, GO_ON)
    assert outcome.carried == out
    assert out.is_file()
    outcome = run(target, out, [backend], timeout_s=LIMIT)
    assert_form(outcome, GO_ON)
    last = outcome.carried.splitlines()[-1]
    assert last.split() == [b"sum", b"11", b"22", b"33", b"44"]


def test_real_qnn_compile_failure_is_build_exit_status(qnn, tmp_path):
    target, compiler, _ = qnn
    out = tmp_path / ("broken" + EXE)
    outcome = build(target, source(tmp_path, "broken"), out, program=compiler)
    assert_form(outcome, BROKEN, condition="build_exit_status")
    assert not out.exists()


def test_real_qnn_probe_reports_present_with_the_sdk_version(qnn_sdk):
    found = probe(timeout_s=LIMIT)
    assert found.state == PRESENT
    assert found.version.startswith("QNN SDK v")
    assert found.version == found.version.strip()


def test_missing_programs_are_absent_or_unavailable(tmp_path):
    assert_form(
        build(make_target(), FIXTURE, tmp_path / "o", program=MISSING),
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


def test_fault_emulator_run_with_an_allocation_failure_is_exit_status(script):
    # Stands for a QNN program whose QnnGraph_create returns
    # QNN_GRAPH_ERROR_MEM_ALLOC (1002, "create failed due to memory/resource
    # allocation", include/QNN/QnnGraph.h and QnnCommon.h of QNN SDK 2.37.0) on
    # the HTP emulator and that reports it by a non-zero status (ADR-0194
    # decision 3, the "Run failure" row).
    interpreter, path = script(ALLOCATION_FAILURE)
    outcome = run(make_target(), interpreter, [path], timeout_s=LIMIT)
    assert_form(outcome, BROKEN, condition="exit_status")


def test_fault_emulator_run_that_hangs_is_time_limit(script):
    # Stands for a run on the HTP emulator that never ends (ADR-0194 decision 6:
    # the runner's or emulator's own hang; ADR-0042 decision 3).
    interpreter, path = script(HANG)
    outcome = run(make_target(), interpreter, [path], timeout_s=0.5)
    assert_form(outcome, BROKEN, condition="time_limit")


def test_fault_build_tool_that_hangs_is_build_time_limit(script, tmp_path):
    # Stands for a compiler that never ends (ADR-0194 decision 6: the tool's own hang).
    outcome = build(
        make_target(build_time_limit_s=0.5),
        FIXTURE,
        tmp_path / "o",
        program=script(HANG),
    )
    assert_form(outcome, BROKEN, condition="build_time_limit")


def test_fault_build_tool_with_a_silent_status_is_build_exit_status(script, tmp_path):
    # Stands for a compiler that crashes with a non-zero status and no
    # diagnostic (ADR-0194 decision 6; ADR-0060 decision 4, S7).
    outcome = build(
        make_target(), FIXTURE, tmp_path / "o", program=script(SILENT_STATUS)
    )
    assert_form(outcome, BROKEN, condition="build_exit_status")


@posix_only
def test_fault_build_tool_ended_by_a_signal_is_build_exit_status(script, tmp_path):
    # Stands for a compiler that crashes by a signal (ADR-0194 decision 6;
    # ADR-0060 decision 4 reads a signal as S7).
    outcome = build(make_target(), FIXTURE, tmp_path / "o", program=script(SIGNAL))
    assert_form(outcome, BROKEN, condition="build_exit_status")


def test_fault_build_tool_without_artefact_is_build_output_missing(script, tmp_path):
    # Stands for a compiler that exits 0 and leaves no artefact (ADR-0060
    # decision 4, S9).
    out = tmp_path / "o"
    outcome = build(make_target(), FIXTURE, out, program=script(NO_ARTEFACT))
    assert_form(outcome, TOOL_FAILURE, kind="build_output_missing")
    assert not out.exists()


def test_fault_version_query_that_hangs_is_unreadable(script):
    # Stands for a qnn-net-run version query that never ends (ADR-0194
    # decisions 6 and 7).
    found = probe(timeout_s=0.5, program=script(HANG))
    assert (found.state, found.version) == (UNREADABLE, None)


def test_assemble_timing_puts_the_backend_before_the_driver_arguments():
    target = make_target(process_time_limit_cap_s=5, env={"PATH": "lib"})
    call = assemble_timing(target, Path("t"), "QnnHtp.dll", PARAMETERS, timeout_s=9)
    assert call == RunCall(
        command=("t", "QnnHtp.dll", *DRIVER_ARGUMENTS),
        env=target.env,
        timeout_s=5,
        files=(),
    )
    reciprocal = PARAMETERS._replace(sample_form="reciprocal", seed=0)
    call = assemble_timing(
        target, "t", Path("lib") / "libQnnCpu.so", reciprocal, timeout_s=2
    )
    assert call.command == (
        "t",
        os.fspath(Path("lib") / "libQnnCpu.so"),
        *timing.driver_arguments(**reciprocal._asdict()),
    )
    assert call.command[-2:] == ("reciprocal", "0")
    assert call.timeout_s == 2


@pytest.mark.parametrize(
    ("changes", "error", "parameter"),
    [
        ({"target": None}, TypeError, "target"),
        ({"executable": ""}, ValueError, "executable"),
        ({"executable": b"t"}, TypeError, "executable"),
        ({"backend": None}, TypeError, "backend"),
        ({"backend": b"QnnHtp.dll"}, TypeError, "backend"),
        ({"backend": ""}, ValueError, "backend"),
        ({"backend": BytesPath()}, TypeError, "backend"),
        ({"parameters": tuple(PARAMETERS)}, TypeError, "parameters"),
        (
            {
                "parameters": Bf16TimingParameters(
                    "gemm", "bf16", (2, 3, 4), 10, "interval", 1
                )
            },
            TypeError,
            "parameters",
        ),
        (
            {"parameters": PARAMETERS._replace(n_max=N_MIN - 1)},
            ValueError,
            "parameters",
        ),
        ({"parameters": PARAMETERS._replace(m=0)}, ValueError, "parameters"),
        ({"parameters": PARAMETERS._replace(k=True)}, ValueError, "parameters"),
        (
            {"parameters": PARAMETERS._replace(sample_form="both")},
            ValueError,
            "parameters",
        ),
        ({"parameters": PARAMETERS._replace(seed=-1)}, ValueError, "parameters"),
        ({"parameters": PARAMETERS._replace(seed=2**64)}, ValueError, "parameters"),
        ({"timeout_s": 0}, ValueError, "timeout_s"),
        ({"timeout_s": "1"}, TypeError, "timeout_s"),
    ],
)
def test_assemble_timing_and_measure_refuse_bad_arguments(
    changes, error, parameter, monkeypatch
):
    def refused(*args, **kwargs):
        raise AssertionError("an executor was called")

    values = {
        "target": make_target(),
        "executable": "t",
        "backend": "QnnHtp.dll",
        "parameters": PARAMETERS,
        "timeout_s": 1,
    }
    values.update(changes)
    monkeypatch.setattr(local_run, "run", refused)
    for call in (assemble_timing, measure):
        with pytest.raises(error) as caught:
            call(**values)
        assert caught.value.parameter == parameter


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        (recorded(stdout=REPORT), (REPORT, None)),
        (recorded(stdout=b""), (b"", None)),
        (recorded(returncode=1, stdout=b"resolution_ns 100\n"), "exit_status"),
        (recorded(returncode=-11), "exit_status"),
        (recorded(returncode=None, timed_out=True), "time_limit"),
    ],
)
def test_measure_hands_the_ended_process_to_the_vendor_measure(
    answer, expected, monkeypatch
):
    seen = []

    def fake_run(command, *, timeout_s, env=None):
        seen.append((command, timeout_s, env))
        return answer

    monkeypatch.setattr(local_run, "run", fake_run)
    target = make_target(env={"PATH": "lib"}, process_time_limit_cap_s=4)
    assert measure(target, "t", "QnnHtp.dll", PARAMETERS, timeout_s=9) == expected
    assert seen == [(("t", "QnnHtp.dll", *DRIVER_ARGUMENTS), 4, target.env)]


@pytest.mark.parametrize(
    "error",
    [local_run.ProgramNotFoundError("t"), OSError(5, "I/O after start")],
)
def test_measure_raises_the_executor_errors_unchanged(error, monkeypatch):
    def raising(*args, **kwargs):
        raise error

    monkeypatch.setattr(local_run, "run", raising)
    with pytest.raises(type(error)) as caught:
        measure(make_target(), "t", "QnnHtp.dll", PARAMETERS, timeout_s=1)
    assert caught.value is error


def test_measure_of_a_missing_program_raises_and_is_placed_by_interpret_run(tmp_path):
    missing = tmp_path / MISSING
    with pytest.raises((local_run.ProgramNotFoundError, OSError)) as caught:
        measure(make_target(), missing, "QnnHtp.dll", PARAMETERS, timeout_s=LIMIT)
    outcome = vendor_adapter.interpret_run(caught.value, str(missing))
    assert_form(outcome, TOOL_FAILURE, kind="executable_unstartable")


def test_measure_refuses_an_answer_no_row_holds(monkeypatch):
    monkeypatch.setattr(
        local_run, "run", lambda *args, **kwargs: recorded(returncode=None)
    )
    with pytest.raises(ValueError):
        measure(make_target(), "t", "QnnHtp.dll", PARAMETERS, timeout_s=1)


def test_fault_timing_run_that_hangs_is_time_limit(script):
    # Stands for a timing run on the HTP emulator that never ends (ADR-0194
    # decision 6: the runner's or emulator's own hang; ADR-0042 decision 3).
    # The script takes the backend library's place in the command.
    interpreter, path = script(HANG)
    assert measure(make_target(), interpreter, path, PARAMETERS, timeout_s=0.5) == (
        "time_limit"
    )


def test_fault_timing_run_with_an_allocation_failure_is_exit_status(script):
    # Stands for the timing fixture whose QnnGraph_create returns
    # QNN_GRAPH_ERROR_MEM_ALLOC (1002, "create failed due to memory/resource
    # allocation", include/QNN/QnnGraph.h and QnnCommon.h of QNN SDK 2.37.0)
    # and that reports it by a non-zero status (ADR-0194 decision 3).
    interpreter, path = script(ALLOCATION_FAILURE)
    assert measure(make_target(), interpreter, path, PARAMETERS, timeout_s=LIMIT) == (
        "exit_status"
    )


def built_timing(qnn, tmp_path):
    target, compiler, _ = qnn
    out = tmp_path / ("timing" + EXE)
    outcome = build(target, source(tmp_path, "timing"), out, program=compiler)
    assert_form(outcome, GO_ON)
    assert outcome.carried == out
    return out


@pytest.mark.parametrize("sample_form", timing.SAMPLE_FORMS)
def test_real_qnn_timing_fixture_reports_at_the_htp_emulator_point(
    qnn, tmp_path, sample_form
):
    # The intervals are times of the emulation on the host, no device figure
    # (FR-19 (4); ADR-0194 decision 4).
    target, _, backend = qnn
    executable = built_timing(qnn, tmp_path)
    parameters = TimingParameters(2, 3, 4, 50, sample_form, 7)
    answer = measure(target, executable, backend, parameters, timeout_s=LIMIT)
    assert type(answer) is tuple
    report, figure = answer
    assert figure is None
    judgement = timing.judge_report(report, sample_form=sample_form, n_max=50)
    assert judgement.broken is None
    assert judgement.state in (
        timing.measurement.State.CONVERGED,
        timing.measurement.State.NOT_CONVERGED,
    )
    assert judgement.resolution_ns > 0
    assert N_MIN <= len(judgement.intervals_ns) <= 50
    assert all(interval > 0 for interval in judgement.intervals_ns)
    assert report.startswith(b"resolution_ns ")


def test_real_qnn_timing_fixture_without_its_backend_is_exit_status(qnn, tmp_path):
    target, _, backend = qnn
    executable = built_timing(qnn, tmp_path)
    missing = str(Path(backend).with_name("hilclaw-no-such-backend.dll"))
    assert measure(target, executable, missing, PARAMETERS, timeout_s=LIMIT) == (
        "exit_status"
    )
    call = assemble_timing(target, executable, missing, PARAMETERS, timeout_s=LIMIT)
    ended = local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)
    assert ended.returncode == 1
    assert b"stop" not in ended.stdout
    assert len(ended.stderr.decode("utf-8", "replace").strip().splitlines()) == 1
