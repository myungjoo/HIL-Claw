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
    assemble_timing,
    build,
    check_device,
    check_device_in_container,
    device_outcome,
    device_probe,
    interpret_container_probe,
    interpret_device_container_probe,
    interpret_device_probe,
    interpret_probe,
    measure,
    probe,
    run,
)
from hilclaw.harness import timing
from hilclaw.harness.measurement import N_MIN
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
PARAMETERS = TimingParameters(2, 3, 4, 10, "interval", 42)
DRIVER_ARGUMENTS = ("2", "3", "4", "5", "10", "0.05", "interval", "42")
REPORT = b"resolution_ns 1\n" + b"interval_ns 30000\n" * N_MIN + b"stop converged\n"

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
        "units_per_ns": 1,
        "model_run": False,
        "instance_start": False,
        "coder_loop": False,
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
    assert assemble_timing(target, "p", PARAMETERS, timeout_s=1).command == (
        "p",
        *DRIVER_ARGUMENTS,
    )


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
    assert found.state == PRESENT, (
        f"nvidia-smi is on PATH but reports no usable GPU or driver: {found}"
    )
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


def test_assemble_timing_gives_the_driver_arguments_after_the_executable():
    target = make_target(process_time_limit_cap_s=5, env={"CUDA_VISIBLE_DEVICES": "0"})
    call = assemble_timing(target, Path("t"), PARAMETERS, timeout_s=9)
    assert call == RunCall(
        command=("t", *DRIVER_ARGUMENTS), env=target.env, timeout_s=5, files=()
    )
    reciprocal = PARAMETERS._replace(sample_form="reciprocal", seed=0)
    call = assemble_timing(target, "t", reciprocal, timeout_s=2)
    assert call.command == ("t", *timing.driver_arguments(**reciprocal._asdict()))
    assert call.command[-2:] == ("reciprocal", "0")
    assert call.timeout_s == 2


@pytest.mark.parametrize(
    ("changes", "error", "parameter"),
    [
        ({"target": None}, TypeError, "target"),
        ({"executable": ""}, ValueError, "executable"),
        ({"executable": b"t"}, TypeError, "executable"),
        ({"parameters": tuple(PARAMETERS)}, TypeError, "parameters"),
        ({"parameters": None}, TypeError, "parameters"),
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
        ({"parameters": PARAMETERS._replace(n=2.0)}, ValueError, "parameters"),
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
        (recorded(returncode=1, stdout=b"resolution_ns 1\n"), "exit_status"),
        (recorded(returncode=-9), "exit_status"),
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
    target = make_target(env={"CUDA_VISIBLE_DEVICES": "0"}, process_time_limit_cap_s=4)
    assert measure(target, "t", PARAMETERS, timeout_s=9) == expected
    assert seen == [(("t", *DRIVER_ARGUMENTS), 4, target.env)]


@pytest.mark.parametrize(
    "error",
    [local_run.ProgramNotFoundError("t"), OSError(5, "I/O after start")],
)
def test_measure_raises_the_executor_errors_unchanged(error, monkeypatch):
    def raising(*args, **kwargs):
        raise error

    monkeypatch.setattr(local_run, "run", raising)
    with pytest.raises(type(error)) as caught:
        measure(make_target(), "t", PARAMETERS, timeout_s=1)
    assert caught.value is error


def test_measure_of_a_missing_program_raises_and_is_placed_by_interpret_run(tmp_path):
    missing = tmp_path / MISSING
    with pytest.raises((local_run.ProgramNotFoundError, OSError)) as caught:
        measure(make_target(), missing, PARAMETERS, timeout_s=LIMIT)
    outcome = vendor_adapter.interpret_run(caught.value, str(missing))
    assert_form(outcome, TOOL_FAILURE, kind="executable_unstartable")


def test_measure_refuses_an_answer_no_row_holds(monkeypatch):
    monkeypatch.setattr(
        local_run, "run", lambda *args, **kwargs: recorded(returncode=None)
    )
    with pytest.raises(ValueError):
        measure(make_target(), "t", PARAMETERS, timeout_s=1)


# The held kernel lasts at least HOLD_NS less one %globaltimer step (STEP_NS, a wide bound).
HOLD_NS = 5_000_000
STEP_NS = 100_000
GPU_PARAMETERS = TimingParameters(64, 64, 64, 50, "interval", 7)


@pytest.fixture
def gpu(nvcc, nvidia_smi):
    if os.name != "posix":
        pytest.skip("the timing fixture reads CLOCK_MONOTONIC (POSIX hosts only)")
    found = device_probe(timeout_s=LIMIT)
    if found.state != PRESENT:
        pytest.skip(f"no usable GPU: {found.message}")


def built_timing(tmp_path, name, *flags):
    out = tmp_path / (name + EXE)
    outcome = build(make_target(flags=flags), FIXTURES / "timing.cu", out)
    assert_form(outcome, GO_ON)
    assert outcome.carried == out
    return out


def ended(executable, parameters, timeout_s=LIMIT):
    call = assemble_timing(make_target(), executable, parameters, timeout_s=timeout_s)
    return local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)


def judged(answer, parameters):
    assert type(answer) is tuple
    report, figure = answer
    assert figure is None
    judgement = timing.judge_report(
        report, sample_form=parameters.sample_form, n_max=parameters.n_max
    )
    assert judgement.broken is None
    assert judgement.state in (
        timing.measurement.State.CONVERGED,
        timing.measurement.State.NOT_CONVERGED,
    )
    assert judgement.resolution_ns > 0
    assert N_MIN <= len(judgement.intervals_ns) <= parameters.n_max
    assert all(interval > 0 for interval in judgement.intervals_ns)
    return judgement


def assert_one_error_line(result, text):
    assert result.returncode == 1
    assert b"stop" not in result.stdout
    lines = result.stderr.decode("utf-8", "replace").strip().splitlines()
    assert len(lines) == 1
    assert text in lines[0]


@pytest.mark.parametrize("sample_form", timing.SAMPLE_FORMS)
def test_real_gpu_timing_fixture_reports_a_judged_measurement(
    gpu, tmp_path, sample_form
):
    executable = built_timing(tmp_path, "timing")
    parameters = GPU_PARAMETERS._replace(sample_form=sample_form)
    judged(measure(make_target(), executable, parameters, timeout_s=LIMIT), parameters)


def test_real_gpu_interval_holds_the_completion_of_the_kernel(gpu, tmp_path):
    executable = built_timing(tmp_path, "hold", f"-DTIMING_HOLD_NS={HOLD_NS}")
    parameters = GPU_PARAMETERS._replace(n_max=20)
    answer = measure(make_target(), executable, parameters, timeout_s=LIMIT)
    judgement = judged(answer, parameters)
    bound = HOLD_NS - STEP_NS - judgement.resolution_ns
    assert all(interval >= bound for interval in judgement.intervals_ns)


def test_real_gpu_runs_the_scale_executable_with_status_zero(gpu, tmp_path):
    out = tmp_path / ("scale" + EXE)
    assert_form(build(make_target(), FIXTURES / "scale.cu", out), GO_ON)
    outcome = run(make_target(), out, timeout_s=LIMIT)
    assert_form(outcome, GO_ON)
    assert outcome.carried == b"built\n"


def test_real_gpu_out_of_memory_is_exit_status(gpu, tmp_path):
    executable = built_timing(tmp_path, "oom", "-DTIMING_FAULT=1")
    assert measure(make_target(), executable, PARAMETERS, timeout_s=LIMIT) == (
        "exit_status"
    )
    result = ended(executable, PARAMETERS)
    assert_one_error_line(result, "cudaMalloc: cudaErrorMemoryAllocation")
    assert result.stdout == b""


def test_real_gpu_illegal_address_is_exit_status(gpu, tmp_path):
    executable = built_timing(tmp_path, "fault", "-DTIMING_FAULT=2")
    assert measure(make_target(), executable, PARAMETERS, timeout_s=LIMIT) == (
        "exit_status"
    )
    result = ended(executable, PARAMETERS)
    assert_one_error_line(result, "cudaDeviceSynchronize: cudaErrorIllegalAddress")


def test_real_gpu_hang_is_time_limit_and_leaves_the_gpu_usable(gpu, tmp_path):
    executable = built_timing(tmp_path, "hang", "-DTIMING_FAULT=3")
    assert measure(make_target(), executable, PARAMETERS, timeout_s=1) == "time_limit"
    result = ended(executable, PARAMETERS, timeout_s=1)
    assert result.timed_out
    assert result.stdout.startswith(b"resolution_ns ")
    assert b"interval_ns" not in result.stdout
    after = built_timing(tmp_path, "timing")
    answer = measure(make_target(), after, GPU_PARAMETERS, timeout_s=LIMIT)
    judged(answer, GPU_PARAMETERS)


@pytest.mark.parametrize(
    "answer",
    [
        recorded(returncode=6),
        recorded(returncode=9),
        recorded(returncode=12),
        local_run.ProgramNotFoundError("nvidia-smi"),
        recorded(returncode=2),
        recorded(returncode=None, timed_out=True),
        recorded(stdout=b"No comma here\n"),
    ],
    ids=[
        "no-gpu",
        "no-driver",
        "no-nvml",
        "tool-absent",
        "other-status",
        "time-limit",
        "no-line",
    ],
)
def test_device_outcome_of_every_probe_without_a_usable_device_is_device_unavailable(
    answer,
):
    found = interpret_device_probe(answer, "nvidia-smi")
    outcome = device_outcome(found)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert outcome.message == found.message
    assert outcome.carried is None


def test_device_outcome_of_a_usable_device_goes_on_with_its_version():
    found = interpret_device_probe(
        recorded(stdout=b"NVIDIA GeForce RTX 4070, 617.14\n"), "nvidia-smi"
    )
    outcome = device_outcome(found)
    assert_form(outcome, GO_ON)
    assert outcome.carried == "NVIDIA GeForce RTX 4070 (driver 617.14)"


def test_device_outcome_keeps_the_no_device_message_apart_from_the_absent_tool():
    no_device = device_outcome(Probe(ABSENT, None, NO_DEVICE))
    absent = device_outcome(
        interpret_device_probe(local_run.ProgramNotFoundError("x"), "x")
    )
    assert no_device.message == NO_DEVICE
    assert absent.message != NO_DEVICE
    assert no_device.kind == absent.kind == "device_unavailable"


@pytest.mark.parametrize(
    "value",
    [None, ("present", "v", "m"), "absent", Probe._make, b"absent"],
    ids=["none", "tuple", "str", "callable", "bytes"],
)
def test_device_outcome_refuses_what_is_no_probe(value):
    with pytest.raises(TypeError) as caught:
        device_outcome(value)
    assert caught.value.parameter == "found"


@pytest.mark.parametrize(
    "value",
    [
        Probe("missing", None, "m"),
        Probe(PRESENT, None, "m"),
        Probe(PRESENT, b"GPU", "m"),
        Probe(ABSENT, None, None),
        Probe(UNREADABLE, None, b"m"),
    ],
    ids=[
        "state",
        "present-without-version",
        "bytes-version",
        "no-message",
        "bytes-message",
    ],
)
def test_device_outcome_refuses_a_probe_no_reading_gives(value):
    with pytest.raises(ValueError) as caught:
        device_outcome(value)
    assert caught.value.parameter == "found"


@pytest.mark.parametrize("status", [6, 9, 12])
def test_fault_check_device_without_a_device_or_driver_is_device_unavailable(
    script, status
):
    # Stands for nvidia-smi on a machine with no GPU (6), no loaded driver (9)
    # or no NVML library (12); the status only is read. Source: nvidia-smi
    # documentation, "RETURN VALUE",
    # https://docs.nvidia.com/deploy/nvidia-smi/index.html (read 2026-11-03).
    outcome = check_device(timeout_s=LIMIT, program=script(STATUS % status))
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert outcome.message == NO_DEVICE


def test_fault_check_device_that_hangs_is_device_unavailable(script):
    # Stands for nvidia-smi that never ends (ADR-0194 decision 6: the tool's own hang).
    outcome = check_device(timeout_s=0.5, program=script(HANG))
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert outcome.message != NO_DEVICE


def test_check_device_with_the_query_program_absent_is_device_unavailable():
    outcome = check_device(timeout_s=LIMIT, program=MISSING)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert outcome.message != NO_DEVICE


@pytest.mark.parametrize(
    ("arguments", "parameter"),
    [
        ({"timeout_s": 0}, "timeout_s"),
        ({"timeout_s": "1"}, "timeout_s"),
        ({"timeout_s": LIMIT, "program": ""}, "program"),
        ({"timeout_s": LIMIT, "program": 3}, "program"),
    ],
)
def test_check_device_refuses_its_arguments_before_anything_starts(
    arguments, parameter, monkeypatch
):
    def started(*args, **kwargs):
        raise AssertionError("a process was started")

    monkeypatch.setattr(local_run, "run", started)
    with pytest.raises((TypeError, ValueError)) as caught:
        check_device(**arguments)
    assert caught.value.parameter == parameter


def test_check_device_passes_on_an_error_it_does_not_place(monkeypatch):
    def failed(*args, **kwargs):
        raise OSError(5, "I/O")

    monkeypatch.setattr(local_run, "run", failed)
    with pytest.raises(OSError):
        check_device(timeout_s=LIMIT)


def test_real_check_device_goes_on_with_a_usable_device(nvidia_smi):
    outcome = check_device(timeout_s=LIMIT)
    assert_form(outcome, GO_ON)
    assert "(driver " in outcome.carried


# The device check in a probe container (ADR-0207 decisions 6 and 7)

GPU_LINE = b"NVIDIA GeForce RTX 4070, 617.14\n"
CUDA_IMAGE = os.environ.get("HILCLAW_CUDA_IMAGE") or "cuda:13.1.2"


@pytest.mark.parametrize(
    ("answer", "state", "version", "message"),
    [
        (
            contained(stdout=GPU_LINE),
            PRESENT,
            "NVIDIA GeForce RTX 4070 (driver 617.14)",
            None,
        ),
        (contained(returncode=125), ABSENT, None, None),
        (contained(returncode=126), ABSENT, None, None),
        (contained(returncode=127), ABSENT, None, None),
        (contained(returncode=6), ABSENT, None, NO_DEVICE),
        (contained(returncode=9), ABSENT, None, NO_DEVICE),
        (contained(returncode=12), ABSENT, None, NO_DEVICE),
        (contained(returncode=1, stdout=GPU_LINE), UNREADABLE, None, None),
        (contained(returncode=-11), UNREADABLE, None, None),
        (contained(returncode=None, timed_out=True), UNREADABLE, None, None),
        (contained(stdout=b""), UNREADABLE, None, None),
        (contained(stdout=b"no comma here\n"), UNREADABLE, None, None),
        (local_run.ProgramNotFoundError("docker"), ABSENT, None, None),
        (OSError(2, "gone"), ABSENT, None, None),
        (NotADirectoryError(20, "not a directory"), ABSENT, None, None),
        (standin_container.NoNumericUserError("no uid"), ABSENT, None, None),
    ],
)
def test_interpret_device_container_probe_on_recorded_answers(
    answer, state, version, message
):
    found = interpret_device_container_probe(answer)
    assert type(found) is Probe
    assert (found.state, found.version) == (state, version)
    assert type(found.message) is str and found.message
    if message is not None:
        assert found.message == message
    if state != PRESENT:
        assert "docker" not in found.message
        assert "build" not in found.message


def test_interpret_device_container_probe_tells_the_container_cases_apart():
    messages = {
        interpret_device_container_probe(contained(returncode=status)).message
        for status in (125, 127, 6, 3)
    }
    messages.add(interpret_device_container_probe(OSError()).message)
    timed_out = contained(returncode=None, timed_out=True)
    messages.add(interpret_device_container_probe(timed_out).message)
    assert len(messages) == 6


@pytest.mark.parametrize(
    "answer",
    [KeyboardInterrupt(), OverflowError("limit"), TypeError("x"), ValueError("x")],
)
def test_interpret_device_container_probe_leaves_other_exceptions(answer):
    assert interpret_device_container_probe(answer) is None


def test_interpret_device_container_probe_refuses_other_values():
    with pytest.raises(TypeError) as caught:
        interpret_device_container_probe(recorded())
    assert caught.value.parameter == "answer"
    with pytest.raises(TypeError) as caught:
        interpret_device_container_probe(None)
    assert caught.value.parameter == "answer"
    with pytest.raises(ValueError):
        interpret_device_container_probe(contained(returncode=None))
    with pytest.raises(ValueError):
        interpret_device_container_probe(contained(returncode=True))


class ClientStarts:
    def __init__(self, *answers):
        self.calls = []
        self.answers = list(answers)

    def __call__(self, command, **options):
        self.calls.append((list(command), options))
        answer = self.answers.pop(0) if self.answers else (0, GPU_LINE, False)
        if isinstance(answer, BaseException):
            raise answer
        status, stdout, timed_out = answer
        return local_run.RunResult(
            returncode=None if timed_out else status,
            timed_out=timed_out,
            stdout=stdout,
            stderr=b"",
            command=tuple(command),
            duration_s=0.1,
        )


@pytest.fixture
def client_starts(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)

    def install(*answers):
        stub = ClientStarts(*answers)
        monkeypatch.setattr(local_run, "run", stub)
        return stub

    return install


@pytest.fixture
def probe_dir(tmp_path):
    directory = tmp_path / "build"
    directory.mkdir()
    return directory


def probe_in_container(build_dir, **options):
    options.setdefault("timeout_s", 30)
    options.setdefault("removal_timeout_s", 10)
    return check_device_in_container("cuda:13.1.2", build_dir, **options)


def test_check_device_in_container_goes_on_with_a_gpu_line(client_starts, probe_dir):
    starts = client_starts()
    outcome = probe_in_container(probe_dir)
    assert_form(outcome, GO_ON)
    assert outcome.carried == "NVIDIA GeForce RTX 4070 (driver 617.14)"
    ((command, options),) = starts.calls
    image_at = command.index("cuda:13.1.2")
    assert command[0] == "docker"
    assert command[image_at + 1 :] == [DEVICE_PROGRAM, *DEVICE_QUERY]
    before = command[:image_at]
    assert before[before.index("--gpus") + 1] == "all"
    assert before[before.index("--network") + 1] == "none"
    assert before[before.index("--pull") + 1] == "never"
    assert before[before.index("--mount") + 1] == (
        f"type=bind,source={os.fspath(probe_dir)},target=/build"
    )
    assert options == {"timeout_s": 30, "env": None}


@pytest.mark.parametrize(
    "answer",
    [
        (125, b"", False),
        (126, b"", False),
        (127, b"", False),
        (6, b"", False),
        (1, GPU_LINE, False),
        (0, b"", False),
        (0, b"garbage\n", False),
        (None, b"", True),
    ],
)
def test_check_device_in_container_is_device_unavailable_otherwise(
    client_starts, probe_dir, answer
):
    client_starts(answer, (0, b"", False))
    outcome = probe_in_container(probe_dir)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert type(outcome.message) is str and outcome.message
    assert "cuda:13.1.2" not in outcome.message
    assert os.fspath(probe_dir) not in outcome.message


def test_check_device_in_container_past_the_limit_removes_the_container(
    client_starts, probe_dir
):
    starts = client_starts((None, b"", True), (0, b"", False))
    outcome = probe_in_container(probe_dir, timeout_s=5, removal_timeout_s=2)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    _, (remove, options) = starts.calls
    assert remove[:3] == ["docker", "rm", "--force"]
    assert options == {"timeout_s": 2, "env": None}


@pytest.mark.parametrize(
    "error",
    [local_run.ProgramNotFoundError("docker"), PermissionError(13, "denied")],
)
def test_check_device_in_container_that_cannot_start_is_device_unavailable(
    client_starts, probe_dir, error
):
    client_starts(error)
    outcome = probe_in_container(probe_dir)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert "docker" not in outcome.message


def test_check_device_in_container_without_a_numeric_user_is_device_unavailable(
    client_starts, probe_dir, monkeypatch
):
    starts = client_starts()
    monkeypatch.delattr(os, "getuid", raising=False)
    outcome = probe_in_container(probe_dir)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert starts.calls == []


def test_check_device_in_container_with_a_missing_build_dir_is_device_unavailable(
    client_starts, tmp_path
):
    starts = client_starts()
    outcome = probe_in_container(tmp_path / "absent")
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert "absent" not in outcome.message
    assert starts.calls == []


@pytest.mark.parametrize(
    ("image", "options", "parameter"),
    [
        ("-x", {}, "image"),
        (3, {}, "image"),
        ("cuda:13.1.2", {"timeout_s": 0}, "timeout_s"),
        ("cuda:13.1.2", {"removal_timeout_s": "1"}, "removal_timeout_s"),
        ("cuda:13.1.2", {"client": ""}, "client"),
    ],
)
def test_check_device_in_container_refuses_its_arguments_before_anything_starts(
    client_starts, probe_dir, image, options, parameter
):
    starts = client_starts()
    options.setdefault("timeout_s", 30)
    options.setdefault("removal_timeout_s", 10)
    with pytest.raises((TypeError, ValueError)) as caught:
        check_device_in_container(image, probe_dir, **options)
    assert caught.value.parameter == parameter
    assert starts.calls == []


def test_check_device_in_container_refuses_a_relative_build_dir(client_starts):
    starts = client_starts()
    with pytest.raises(ValueError) as caught:
        probe_in_container("relative")
    assert caught.value.parameter == "build_dir"
    assert starts.calls == []


def test_check_device_in_container_passes_on_what_it_does_not_place(
    client_starts, probe_dir
):
    client_starts(OverflowError("limit"), (0, b"", False))
    with pytest.raises(OverflowError) as caught:
        probe_in_container(probe_dir)
    assert caught.value.container_name.startswith(standin_container.NAME_PREFIX)


STUB_CLIENT = (
    '#!/bin/sh\nprintf "%s" "$HILCLAW_TEST_OUT"\nexit "$HILCLAW_TEST_STATUS"\n'
)


@posix_only
@pytest.mark.parametrize(
    ("status", "output", "form"),
    [
        (0, "NVIDIA GeForce RTX 4070, 617.14\n", GO_ON),
        (125, "", TOOL_FAILURE),
        (127, "", TOOL_FAILURE),
        (3, "", TOOL_FAILURE),
    ],
)
def test_check_device_in_container_with_a_stub_client_on_path(
    tmp_path, probe_dir, monkeypatch, status, output, form
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    client = bin_dir / "docker"
    client.write_text(STUB_CLIENT, encoding="utf-8")
    client.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("HILCLAW_TEST_STATUS", str(status))
    monkeypatch.setenv("HILCLAW_TEST_OUT", output)
    outcome = probe_in_container(probe_dir)
    assert outcome.form == form
    if form == TOOL_FAILURE:
        assert outcome.kind == "device_unavailable"


def test_check_device_in_container_with_no_client_on_path(probe_dir, monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)
    outcome = probe_in_container(probe_dir, client=MISSING)
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")
    assert MISSING not in outcome.message


def _docker(*arguments):
    try:
        return subprocess.run(
            ["docker", *arguments], capture_output=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


@pytest.fixture
def gpu_container():
    if os.name != "posix":
        pytest.skip("the runtime's containers need a POSIX host (C-7 1)")
    if shutil.which("docker") is None:
        pytest.skip("docker is not on PATH (FR-19 (5))")
    found = _docker("image", "inspect", CUDA_IMAGE)
    if found is None or found.returncode != 0:
        pytest.skip(f"the image {CUDA_IMAGE} is not in the store (FR-19 (5))")
    runtimes = _docker("info", "--format", "{{json .Runtimes}}")
    if runtimes is None or b"nvidia" not in runtimes.stdout:
        pytest.skip("Docker has no NVIDIA Container Toolkit runtime (FR-19 (5))")
    if shutil.which("nvidia-smi") is None:
        pytest.skip("nvidia-smi is not on PATH: no usable GPU (FR-19 (5))")
    if device_probe(timeout_s=LIMIT).state != PRESENT:
        pytest.skip("the host reports no usable GPU (FR-19 (5))")
    return CUDA_IMAGE


def test_real_check_device_in_container_goes_on_with_a_usable_device(
    gpu_container, probe_dir
):
    outcome = check_device_in_container(
        gpu_container, probe_dir, timeout_s=LIMIT, removal_timeout_s=60
    )
    assert_form(outcome, GO_ON)
    assert "(driver " in outcome.carried
    assert list(probe_dir.iterdir()) == []


def test_real_check_device_in_container_without_the_image_is_device_unavailable(
    gpu_container, probe_dir
):
    outcome = check_device_in_container(
        "hilclaw-no-such-image:0", probe_dir, timeout_s=LIMIT, removal_timeout_s=60
    )
    assert_form(outcome, TOOL_FAILURE, kind="device_unavailable")


BUILD_AND_RUN = (
    "nvcc -O2 -arch=native -o scale scale.cu && ./scale && "
    "{ command -v nvidia-smi >/dev/null && "
    "nvidia-smi --query-gpu=name --format=csv,noheader || echo no-gpu; }"
)


def _build_and_run(image, build_dir, gpus):
    shutil.copyfile(FIXTURES / "scale.cu", build_dir / "scale.cu")
    return standin_container.run_in_container(
        image,
        build_dir,
        "sh",
        ["-c", BUILD_AND_RUN],
        timeout_s=LIMIT,
        removal_timeout_s=60,
        gpus=gpus,
    )


def test_real_gpu_container_builds_with_arch_native_and_sees_the_gpu(
    gpu_container, probe_dir
):
    done = _build_and_run(gpu_container, probe_dir, True)
    assert done.returncode == 0, done.stderr
    assert done.stdout.decode().splitlines()[0] == "built"
    assert b"no-gpu" not in done.stdout
    assert b"Cannot find valid GPU" not in done.stderr
    assert (probe_dir / "scale").is_file()


def test_real_container_without_gpus_does_not_see_the_gpu(gpu_container, probe_dir):
    done = _build_and_run(gpu_container, probe_dir, False)
    assert done.returncode == 0, done.stderr
    assert done.stdout.decode().split() == ["built", "no-gpu"]
    assert b"Cannot find valid GPU" in done.stderr
