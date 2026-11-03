import builtins
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hilclaw import clang_adapter, local_run, standin_container, targets, vendor_adapter
from hilclaw.cuda_adapter import (
    DEVICE_PROGRAM,
    NO_DEVICE,
    PROGRAM,
    assemble_build,
    assemble_device_probe,
    assemble_probe,
    assemble_run,
    build,
    device_probe,
    interpret_container_probe,
    interpret_device_probe,
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

FIXTURES = Path(__file__).resolve().parent / "cuda_fixtures"
MISSING = "hilclaw-no-such-program"
EXE = ".exe" if os.name == "nt" else ""
LIMIT = 300
DEVICE_QUERY = ("--query-gpu=name,driver_version", "--format=csv,noheader")
RELEASE = b"Cuda compilation tools, release 13.1, V13.1.115"
NVCC_OUTPUT = (
    b"nvcc: NVIDIA (R) Cuda compiler driver\n"
    b"Copyright (c) 2005-2025 NVIDIA Corporation\n"
    b"Built on Tue_Dec_16_07:23:41_PM_PST_2025\n" + RELEASE + b"\n"
    b"Build cuda_13.1.r13.1/compiler.37061995_0\n"
)

# Fault-injection scripts (ADR-0194 decision 6), each run by this interpreter
# from the test's own temporary directory and passed only as ``program`` or
# as the run's executable argument.
HANG = "import threading\nthreading.Event().wait()\n"
SILENT_STATUS = "import sys\nsys.exit(70)\n"
SIGNAL = "import os, signal\nos.kill(os.getpid(), signal.SIGSEGV)\n"
NO_ARTEFACT = "pass\n"
STATUS = "import sys\nsys.exit(%d)\n"
OUT_OF_MEMORY = (
    "import sys\nsys.stderr.write('CUDA error: out of memory\\n')\nsys.exit(1)\n"
)


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
        "model_run": False,
        "instance_start": False,
    }
    values.update(changes)
    return targets.Target(**values)


@pytest.fixture
def nvcc():
    if shutil.which("nvcc") is None:
        pytest.skip("nvcc is not on PATH (FR-19 (5): a vendor tool's execution test)")
    host = "cl" if os.name == "nt" else "g++"
    if shutil.which(host) is None:
        pytest.skip(f"nvcc needs the host compiler {host}, which is not on PATH")


@pytest.fixture
def nvidia_smi():
    if shutil.which("nvidia-smi") is None:
        pytest.skip(
            "nvidia-smi is not on PATH (FR-19 (5): a vendor tool's execution test)"
        )


@pytest.fixture
def script(tmp_path):
    directory = tmp_path / "fault"
    directory.mkdir()

    def write(body):
        path = directory / "tool.py"
        path.write_text(body, encoding="utf-8")
        return (sys.executable, str(path))

    return write


def assert_form(outcome, form, condition=None, kind=None):
    assert type(outcome) is vendor_adapter.Outcome
    assert (outcome.form, outcome.condition, outcome.kind) == (form, condition, kind)


def recorded(returncode=0, stdout=b"", timed_out=False):
    return local_run.RunResult(
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=b"",
        command=("tool",),
        duration_s=0.1,
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


def test_program_constants():
    assert (PROGRAM, DEVICE_PROGRAM) == ("nvcc", "nvidia-smi")
    assert type(NO_DEVICE) is str and NO_DEVICE


def test_assemble_build_takes_the_target_values_and_adds_no_flag():
    target = make_target(
        flags=("-O3", "-arch=sm_89"),
        trailing_flags=("-lcublas",),
        env={"A": "1"},
        build_time_limit_s=7,
    )
    call = assemble_build(target, ["a.cu", Path("b.cu")], "out")
    assert call == BuildCall(
        compiler=("nvcc",),
        flags=("-O3", "-arch=sm_89"),
        sources=("a.cu", Path("b.cu")),
        trailing_flags=("-lcublas",),
        output="out",
        env=target.env,
        timeout_s=7,
        files=(),
    )
    bare = assemble_build(make_target(), "a.cu", "o", program=("ccache", "nvcc"))
    assert (bare.compiler, bare.flags, bare.trailing_flags) == (
        ("ccache", "nvcc"),
        (),
        (),
    )


def test_assemble_run_caps_the_time_limit_and_takes_the_env():
    target = make_target(process_time_limit_cap_s=5, env={"B": "2"})
    assert assemble_run(target, Path("p"), ["x"], timeout_s=9) == RunCall(
        command=("p", "x"), env=target.env, timeout_s=5, files=()
    )
    assert assemble_run(target, "p", timeout_s=2.5).timeout_s == 2.5


def test_assemble_probe_is_the_version_query():
    assert assemble_probe(timeout_s=3) == RunCall(
        command=("nvcc", "--version"), env=None, timeout_s=3, files=()
    )
    assert assemble_probe(timeout_s=3, program=("py", "t.py")).command == (
        "py",
        "t.py",
        "--version",
    )


def test_assemble_device_probe_is_the_csv_gpu_query():
    assert assemble_device_probe(timeout_s=4) == RunCall(
        command=("nvidia-smi", *DEVICE_QUERY), env=None, timeout_s=4, files=()
    )
    call = assemble_device_probe(timeout_s=4, program=Path("bin") / "smi")
    assert call.command == (os.fspath(Path("bin") / "smi"), *DEVICE_QUERY)
    call = assemble_device_probe(timeout_s=4, program=("py", "t.py"))
    assert call.command == ("py", "t.py", *DEVICE_QUERY)


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
    assert assemble_build(target, ["a.cu"], "o").env == target.env
    assert assemble_run(target, "p", ["a"], timeout_s=1).command == ("p", "a")
    assert assemble_probe(timeout_s=1).command == ("nvcc", "--version")
    assert assemble_device_probe(timeout_s=1).command[0] == "nvidia-smi"


@pytest.mark.parametrize(
    ("call", "error", "parameter"),
    [
        (lambda: assemble_build(None, "a.cu", "o"), TypeError, "target"),
        (lambda: assemble_build(make_target(), 3, "o"), TypeError, "sources"),
        (
            lambda: assemble_build(make_target(), "a.cu", "o", program=b"nvcc"),
            TypeError,
            "program",
        ),
        (
            lambda: assemble_build(make_target(), "a.cu", "o", program=()),
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
            lambda: assemble_run(make_target(), "p", "a", timeout_s=1),
            TypeError,
            "arguments",
        ),
        (
            lambda: assemble_run(make_target(), "p", timeout_s=0),
            ValueError,
            "timeout_s",
        ),
        (lambda: assemble_probe(timeout_s=None), TypeError, "timeout_s"),
        (lambda: assemble_probe(timeout_s=1, program=""), ValueError, "program"),
        (
            lambda: assemble_device_probe(timeout_s=float("nan")),
            ValueError,
            "timeout_s",
        ),
        (lambda: assemble_device_probe(timeout_s=True), TypeError, "timeout_s"),
        (
            lambda: assemble_device_probe(timeout_s=1, program=None),
            TypeError,
            "program",
        ),
        (
            lambda: assemble_device_probe(timeout_s=1, program=("smi", 2)),
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
        build("t", "a.cu", tmp_path / "o")
    assert caught.value.parameter == "target"
    with pytest.raises(TypeError) as caught:
        run(None, "p", timeout_s=1)
    assert caught.value.parameter == "target"
    with pytest.raises(ValueError) as caught:
        probe(timeout_s=-1)
    assert caught.value.parameter == "timeout_s"
    with pytest.raises(TypeError) as caught:
        device_probe(timeout_s=1, program=3)
    assert caught.value.parameter == "program"


def test_execute_parts_hand_the_assembled_values(tmp_path, monkeypatch):
    seen = {}

    def fake_run(command, *, timeout_s, env=None):
        seen["run"] = (command, timeout_s, env)
        if command[0] == "nvcc":
            return recorded(stdout=NVCC_OUTPUT)
        if command[0] == "nvidia-smi":
            return recorded(stdout=b"GPU A, 1.0\n")
        return recorded(stdout=b"ran\n")

    def fake_build(sources, output, **kwargs):
        seen["build"] = (sources, output, kwargs)
        raise clang_adapter.clang_build.CompilerNotFoundError("nvcc")

    monkeypatch.setattr(local_run, "run", fake_run)
    monkeypatch.setattr(clang_adapter.clang_build, "build", fake_build)
    target = make_target(env={"E": "1"}, process_time_limit_cap_s=4, flags=("-G",))
    assert run(target, "p", ["a"], timeout_s=9).carried == b"ran\n"
    assert seen["run"] == (("p", "a"), 4, target.env)
    assert probe(timeout_s=2).version == RELEASE.decode()
    assert seen["run"] == (("nvcc", "--version"), 2, None)
    assert device_probe(timeout_s=3).version == "GPU A (driver 1.0)"
    assert seen["run"] == (("nvidia-smi", *DEVICE_QUERY), 3, None)
    assert_form(build(target, "a.cu", "o"), TOOL_FAILURE, kind="compiler_unavailable")
    assert seen["build"] == (
        ("a.cu",),
        "o",
        {
            "timeout_s": target.build_time_limit_s,
            "flags": ("-G",),
            "trailing_flags": (),
            "compiler": ("nvcc",),
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
        lambda: device_probe(timeout_s=1),
    ):
        with pytest.raises(OSError) as caught:
            call()
        assert caught.value is error
    with pytest.raises(RuntimeError) as caught:
        build(make_target(), "a.cu", tmp_path / "o")
    assert caught.value is built_error


@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (recorded(stdout=NVCC_OUTPUT), PRESENT, RELEASE.decode()),
        (
            recorded(stdout=b"\n  " + RELEASE + b"  \r\n" + RELEASE + b"9\n"),
            PRESENT,
            RELEASE.decode(),
        ),
        (recorded(stdout=b"nvcc: NVIDIA (R) Cuda compiler driver\n"), UNREADABLE, None),
        (recorded(stdout=b"cuda compilation tools, release 1\n"), UNREADABLE, None),
        (recorded(stdout=b""), UNREADABLE, None),
        (recorded(returncode=1, stdout=NVCC_OUTPUT), UNREADABLE, None),
        (recorded(returncode=-11), UNREADABLE, None),
        (recorded(returncode=None, timed_out=True), UNREADABLE, None),
        (local_run.ProgramNotFoundError("nvcc"), ABSENT, None),
        (OSError(13, "Permission denied", "/usr/local/cuda/bin/nvcc"), ABSENT, None),
    ],
)
def test_interpret_probe_on_recorded_answers(answer, state, version):
    found = interpret_probe(answer, "nvcc")
    assert type(found) is Probe
    assert (found.state, found.version) == (state, version)
    assert type(found.message) is str and found.message


@pytest.mark.parametrize(
    "error", [OSError(5, "I/O"), KeyboardInterrupt(), ValueError()]
)
def test_interpret_probe_leaves_other_errors(error):
    assert interpret_probe(error, "nvcc") is None


def test_interpret_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_probe(NVCC_OUTPUT, "nvcc")
    assert caught.value.parameter == "answer"
    with pytest.raises(TypeError) as caught:
        interpret_probe(recorded(), 3)
    assert caught.value.parameter == "program"
    with pytest.raises(ValueError):
        interpret_probe(recorded(returncode=None), "nvcc")


@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (contained(stdout=NVCC_OUTPUT), PRESENT, RELEASE.decode()),
        (contained(stdout=b"\n" + RELEASE + b"\n"), PRESENT, RELEASE.decode()),
        (contained(stdout=b"nvcc: banner only\n"), UNREADABLE, None),
        (contained(returncode=1, stdout=NVCC_OUTPUT), UNREADABLE, None),
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
    [contained(returncode=125), local_run.ProgramNotFoundError("docker"), OSError()],
)
def test_interpret_container_probe_leaves_an_unused_container(answer):
    assert interpret_container_probe(answer) is None


def test_interpret_container_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_container_probe(recorded())
    assert caught.value.parameter == "answer"
    with pytest.raises(ValueError):
        interpret_container_probe(contained(returncode=None))


@pytest.mark.parametrize(
    ("answer", "state", "version", "message"),
    [
        (
            recorded(stdout=b"NVIDIA GeForce RTX 4070, 617.14\n"),
            PRESENT,
            "NVIDIA GeForce RTX 4070 (driver 617.14)",
            None,
        ),
        (
            recorded(stdout=b"\nGPU, A , 1.0 \r\n  B,1.0\n\n"),
            PRESENT,
            "GPU, A (driver 1.0); B (driver 1.0)",
            None,
        ),
        (recorded(returncode=6), ABSENT, None, NO_DEVICE),
        (recorded(returncode=9, stdout=b"any text\n"), ABSENT, None, NO_DEVICE),
        (recorded(returncode=12), ABSENT, None, NO_DEVICE),
        (local_run.ProgramNotFoundError("nvidia-smi"), ABSENT, None, None),
        (OSError(8, "Exec format error", "/usr/bin/nvidia-smi"), ABSENT, None, None),
        (recorded(returncode=2), UNREADABLE, None, None),
        (recorded(returncode=15), UNREADABLE, None, None),
        (recorded(returncode=255), UNREADABLE, None, None),
        (recorded(returncode=-6), UNREADABLE, None, None),
        (recorded(returncode=None, timed_out=True), UNREADABLE, None, None),
        (recorded(stdout=b""), UNREADABLE, None, None),
        (recorded(stdout=b" \n\n"), UNREADABLE, None, None),
        (recorded(stdout=b"No comma here\n"), UNREADABLE, None, None),
        (recorded(stdout=b"GPU A, 1.0\nGPU B,\n"), UNREADABLE, None, None),
        (recorded(stdout=b", 1.0\n"), UNREADABLE, None, None),
    ],
)
def test_interpret_device_probe_on_recorded_answers(answer, state, version, message):
    found = interpret_device_probe(answer, "nvidia-smi")
    assert type(found) is Probe
    assert (found.state, found.version) == (state, version)
    assert type(found.message) is str and found.message
    if message is not None:
        assert found.message == message
    elif state != PRESENT:
        assert found.message != NO_DEVICE


@pytest.mark.parametrize(
    "error", [OSError(5, "I/O"), KeyboardInterrupt(), ValueError()]
)
def test_interpret_device_probe_leaves_other_errors(error):
    assert interpret_device_probe(error, "nvidia-smi") is None


def test_interpret_device_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_device_probe(b"GPU, 1", "nvidia-smi")
    assert caught.value.parameter == "answer"
    with pytest.raises(ValueError) as caught:
        interpret_device_probe(recorded(), "")
    assert caught.value.parameter == "program"
    with pytest.raises(ValueError):
        interpret_device_probe(recorded(returncode=None), "nvidia-smi")


def test_real_nvcc_builds_a_fixture_into_an_executable(nvcc, tmp_path):
    out = tmp_path / ("scale" + EXE)
    outcome = build(make_target(), FIXTURES / "scale.cu", out)
    assert_form(outcome, GO_ON)
    assert outcome.carried == out
    assert out.is_file()


def test_real_nvcc_compile_failure_is_build_exit_status(nvcc, tmp_path):
    out = tmp_path / ("broken" + EXE)
    outcome = build(make_target(), FIXTURES / "broken.cu", out)
    assert_form(outcome, BROKEN, condition="build_exit_status")
    assert not out.exists()


def test_real_nvcc_probe_reports_present_with_the_release_line(nvcc):
    found = probe(timeout_s=LIMIT)
    assert found.state == PRESENT
    assert found.version.startswith("Cuda compilation tools, release ")
    assert found.version == found.version.strip()


def test_real_nvidia_smi_reports_a_usable_device(nvidia_smi):
    found = device_probe(timeout_s=LIMIT)
    assert found.state == PRESENT, found
    assert "(driver " in found.version


def test_missing_programs_are_absent_or_unavailable(tmp_path):
    assert_form(
        build(make_target(), FIXTURES / "scale.cu", tmp_path / "o", program=MISSING),
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
    found = device_probe(timeout_s=LIMIT, program=MISSING)
    assert (found.state, found.version) == (ABSENT, None)
    assert found.message != NO_DEVICE


@pytest.mark.parametrize("status", [6, 9, 12])
def test_fault_nvidia_smi_without_a_device_or_driver_is_no_device(script, status):
    # Stands for nvidia-smi on a machine with no GPU (6, "A query to find an
    # object was unsuccessful"), no loaded driver (9) or no NVML library (12);
    # the status only is read. Source: nvidia-smi documentation, "RETURN VALUE",
    # https://docs.nvidia.com/deploy/nvidia-smi/index.html (read 2026-11-03).
    found = device_probe(timeout_s=LIMIT, program=script(STATUS % status))
    assert found == Probe(ABSENT, None, NO_DEVICE)


def test_fault_nvidia_smi_that_hangs_is_unreadable(script):
    # Stands for nvidia-smi that never ends (ADR-0194 decision 6: the tool's own hang).
    found = device_probe(timeout_s=0.5, program=script(HANG))
    assert (found.state, found.version) == (UNREADABLE, None)
    assert found.message != NO_DEVICE


def test_fault_cuda_program_out_of_memory_is_exit_status(script):
    # Stands for a CUDA program whose allocation fails with cudaErrorMemoryAllocation
    # ("out of memory", CUDA Runtime API, enum cudaError) and that reports it by
    # a non-zero status (ADR-0194 decision 3, the "Run failure" row).
    interpreter, path = script(OUT_OF_MEMORY)
    outcome = run(make_target(), interpreter, [path], timeout_s=LIMIT)
    assert_form(outcome, BROKEN, condition="exit_status")


def test_fault_nvcc_that_hangs_is_build_time_limit(script, tmp_path):
    # Stands for an nvcc that never ends (ADR-0194 decision 6: the tool's own hang).
    outcome = build(
        make_target(build_time_limit_s=0.5),
        FIXTURES / "scale.cu",
        tmp_path / "o",
        program=script(HANG),
    )
    assert_form(outcome, BROKEN, condition="build_time_limit")


def test_fault_nvcc_with_a_silent_status_is_build_exit_status(script, tmp_path):
    # Stands for an nvcc that crashes with a non-zero status and no diagnostic
    # (ADR-0194 decision 6; ADR-0060 decision 4, S7).
    outcome = build(
        make_target(),
        FIXTURES / "scale.cu",
        tmp_path / "o",
        program=script(SILENT_STATUS),
    )
    assert_form(outcome, BROKEN, condition="build_exit_status")


@posix_only
def test_fault_nvcc_ended_by_a_signal_is_build_exit_status(script, tmp_path):
    # Stands for an nvcc that crashes by a signal (ADR-0194 decision 6;
    # ADR-0060 decision 4 reads a signal as S7).
    outcome = build(
        make_target(), FIXTURES / "scale.cu", tmp_path / "o", program=script(SIGNAL)
    )
    assert_form(outcome, BROKEN, condition="build_exit_status")


def test_fault_nvcc_without_artefact_is_build_output_missing(script, tmp_path):
    # Stands for an nvcc that exits 0 and leaves no artefact (ADR-0060 decision 4, S9).
    out = tmp_path / "o"
    outcome = build(
        make_target(), FIXTURES / "scale.cu", out, program=script(NO_ARTEFACT)
    )
    assert_form(outcome, TOOL_FAILURE, kind="build_output_missing")
    assert not out.exists()


def test_fault_nvcc_version_query_that_hangs_is_unreadable(script):
    # Stands for an nvcc version query that never ends (ADR-0194 decisions 6 and 7).
    found = probe(timeout_s=0.5, program=script(HANG))
    assert (found.state, found.version) == (UNREADABLE, None)
