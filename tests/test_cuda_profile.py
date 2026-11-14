import inspect
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from hilclaw import cuda_adapter, cuda_profile, standin_profile, targets
from hilclaw.cuda_profile import ACCELERATOR, DEVICE_QUERY, local_record
from hilclaw.keys import SCHEMA_VERSION, InvalidRecordError, hw_profile_key
from hilclaw.local_run import RunResult
from hilclaw.standin_profile import UnreadableFactError

NVCC_OUT = (
    b"nvcc: NVIDIA (R) Cuda compiler driver\n"
    b"Copyright (c) 2005-2025 NVIDIA Corporation\n"
    b"Cuda compilation tools, release 13.1, V13.1.115\n"
    b"Build cuda_13.1.r13.1/compiler.37061995_0\n"
)
GCC_OUT = b"gcc (Example 11.4.0-1) 11.4.0\nCopyright (C) 2021 Free Software Foundation, Inc.\n"
SMI_OUT = b"Example GeForce GPU 4070, 8.9, 617.14\n"
IMAGE_NVCC_OUT = NVCC_OUT.replace(b"13.1, V13.1.115", b"13.0, V13.0.88")
IMAGE_GCC_OUT = b"gcc (Image 13.2.0) 13.2.0\n"
IMAGE = "example.invalid/cuda:0"
CPUINFO = b"processor\t: 0\nmodel name\t: Example(R) CPU X-1\n"
OS_RELEASE = b'ID=exampleos\nVERSION_ID="1.0"\n'
TIMEOUT = 60
EXPECTED = {
    "schema_version": SCHEMA_VERSION,
    "accelerator": "cuda_gpu",
    "revision": "Example GeForce GPU 4070 sm_89",
    "toolchain": {
        "nvcc": "Cuda compilation tools, release 13.1, V13.1.115",
        "gcc": "gcc (Example 11.4.0-1) 11.4.0",
        "nvidia_driver": "617.14",
    },
    "host": {"cpu": "Example(R) CPU X-1", "os": "wsl exampleos 1.0"},
    "hw_source": "external",
}
STUB = """#!{python}
import json, pathlib, sys
here = pathlib.Path(__file__).resolve().parent
name = pathlib.Path(sys.argv[0]).name
with open(here / "calls.ndjson", "a", encoding="utf-8") as log:
    log.write(json.dumps([name, *sys.argv[1:]]) + "\\n")
key = "image-" + sys.argv[-2] if name == "docker" else name
sys.stdout.buffer.write((here / (key + ".out")).read_bytes())
status = here / (key + ".status")
sys.exit(int(status.read_text()) if status.exists() else 0)
"""


class Machine:
    def __init__(self, directory):
        self.bin = directory

    def put(self, key, stdout, status=None):
        (self.bin / f"{key}.out").write_bytes(stdout)
        if status is not None:
            (self.bin / f"{key}.status").write_text(str(status))

    def remove(self, program):
        (self.bin / program).unlink()

    def calls(self):
        log = self.bin / "calls.ndjson"
        if not log.exists():
            return []
        return [json.loads(line) for line in log.read_text().splitlines()]


@pytest.fixture
def machine(tmp_path, monkeypatch):
    if os.name != "posix" or not hasattr(os, "getuid"):
        pytest.skip("the stub programs need a POSIX host")
    directory = tmp_path / "bin"
    directory.mkdir()
    for program in ("nvcc", "gcc", "nvidia-smi", "docker"):
        path = directory / program
        path.write_text(STUB.format(python=sys.executable), encoding="utf-8")
        path.chmod(0o755)
    fake = Machine(directory)
    fake.put("nvcc", NVCC_OUT)
    fake.put("gcc", GCC_OUT)
    fake.put("nvidia-smi", SMI_OUT)
    fake.put("image-nvcc", IMAGE_NVCC_OUT)
    fake.put("image-gcc", IMAGE_GCC_OUT)
    files = {"/proc/cpuinfo": CPUINFO, "/etc/os-release": OS_RELEASE}
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.setattr(
        standin_profile, "_kernel", lambda: ("Linux", "6.0-microsoft-standard-WSL2")
    )
    monkeypatch.setattr(standin_profile, "_read", lambda path: files[path])
    return fake


def fails(fact, **arguments):
    with pytest.raises(UnreadableFactError) as caught:
        local_record("external", timeout_s=TIMEOUT, **arguments)
    message = str(caught.value)
    assert message.startswith(fact + ": ")
    return message


def expected(**toolchain):
    record = dict(EXPECTED, toolchain=dict(EXPECTED["toolchain"], **toolchain))
    return record


def test_the_host_record(machine):
    record = local_record("external", timeout_s=TIMEOUT)
    assert record == EXPECTED
    assert list(record) == list(EXPECTED)
    assert hw_profile_key(record).name.startswith("cuda_gpu-")
    assert machine.calls() == [
        ["nvcc", "--version"],
        ["gcc", "--version"],
        ["nvidia-smi", *DEVICE_QUERY],
    ]


@pytest.mark.parametrize("hw_source", ["external", "in_house"])
def test_hw_source_is_the_callers(machine, hw_source):
    assert local_record(hw_source, timeout_s=TIMEOUT)["hw_source"] == hw_source


def test_each_call_returns_a_new_record_read_again(machine):
    first = local_record("external", timeout_s=TIMEOUT)
    machine.put("nvidia-smi", b"Example GeForce GPU 4070, 8.9, 620.01\n")
    second = local_record("external", timeout_s=TIMEOUT)
    assert first is not second
    assert second["toolchain"]["nvidia_driver"] == "620.01"
    assert hw_profile_key(first) != hw_profile_key(second)


def test_the_image_record_reads_nvcc_and_gcc_in_new_containers(machine):
    record = local_record("in_house", timeout_s=TIMEOUT, image=IMAGE)
    assert record["toolchain"] == {
        "nvcc": "Cuda compilation tools, release 13.0, V13.0.88",
        "gcc": "gcc (Image 13.2.0) 13.2.0",
        "nvidia_driver": "617.14",
    }
    assert record["revision"] == EXPECTED["revision"]
    assert record["hw_source"] == "in_house"
    calls = machine.calls()
    assert [call[0] for call in calls] == ["docker", "docker", "nvidia-smi"]
    assert calls[2] == ["nvidia-smi", *DEVICE_QUERY]
    for call, program in zip(calls[:2], ("nvcc", "gcc")):
        assert call[1:3] == ["run", "--rm"]
        assert call[-3:] == [IMAGE, program, "--version"]
        assert "--network" in call and "--pull" in call
    assert (
        calls[0][calls[0].index("--name") + 1] != calls[1][calls[1].index("--name") + 1]
    )


def test_the_image_record_starts_no_host_compiler(machine):
    machine.remove("nvcc")
    machine.remove("gcc")
    assert local_record("external", timeout_s=TIMEOUT, image=IMAGE)["revision"]


def test_the_device_query_is_never_run_in_the_image(machine):
    machine.remove("nvidia-smi")
    message = fails("revision", image=IMAGE)
    assert "was not found" in message


@pytest.mark.parametrize(
    "stdout",
    [
        b"A, 8.9, 1\nB, 8.9, 1\n",
        b"A, 8.9, 1\n\nA, 8.9, 1",
        b"A, 8.9, 1\r\nB, 7.5, 2\r\n",
    ],
)
def test_two_gpu_lines_have_no_record(machine, stdout):
    machine.put("nvidia-smi", stdout)
    assert "more than one GPU" in fails("revision")


@pytest.mark.parametrize("stdout", [b"", b"\n", b" \t \n\n", b"\r\n"])
def test_no_gpu_line_has_no_record(machine, stdout):
    machine.put("nvidia-smi", stdout)
    assert "named no GPU" in fails("revision")


@pytest.mark.parametrize(
    ("program", "fact"),
    [
        ("nvcc", "toolchain.nvcc"),
        ("gcc", "toolchain.gcc"),
        ("nvidia-smi", "revision"),
    ],
)
def test_a_missing_host_program(machine, program, fact):
    machine.remove(program)
    assert "was not found" in fails(fact)


def test_a_missing_container_client(machine):
    machine.remove("docker")
    message = fails("toolchain.nvcc", image=IMAGE)
    assert "`docker run <image> nvcc --version` was not found" in message
    assert IMAGE not in message


@pytest.mark.parametrize(
    ("key", "fact", "arguments"),
    [
        ("nvcc", "toolchain.nvcc", {}),
        ("gcc", "toolchain.gcc", {}),
        ("nvidia-smi", "revision", {}),
        ("image-nvcc", "toolchain.nvcc", {"image": IMAGE}),
        ("image-gcc", "toolchain.gcc", {"image": IMAGE}),
    ],
)
@pytest.mark.parametrize("status", [1, 6, 125])
def test_a_non_zero_status(machine, key, fact, arguments, status):
    machine.put(key, b"", status)
    assert f"ended with status {status}" in fails(fact, **arguments)


@pytest.mark.parametrize(
    "stdout",
    [
        b"nvcc: NVIDIA (R) Cuda compiler driver\n",
        b"",
        b"release 13.1, V13.1.115\n",
        b"Cuda compilation tools\n",
    ],
)
def test_nvcc_without_a_release_line(machine, stdout):
    machine.put("nvcc", stdout)
    assert "no release line" in fails("toolchain.nvcc")


@pytest.mark.parametrize(
    ("stdout", "value"),
    [
        (NVCC_OUT, "Cuda compilation tools, release 13.1, V13.1.115"),
        (
            b"banner\n  Cuda   compilation tools,\trelease 13.1, V13.1.115  \r\n",
            "Cuda compilation tools, release 13.1, V13.1.115",
        ),
        (
            (
                b"Cuda compilation tools, release 1.0, V1\n"
                b"Cuda compilation tools, release 2.0, V2\n"
            ),
            "Cuda compilation tools, release 1.0, V1",
        ),
    ],
)
def test_the_nvcc_release_line_is_spelt(machine, stdout, value):
    machine.put("nvcc", stdout)
    assert local_record("external", timeout_s=TIMEOUT)["toolchain"]["nvcc"] == value


def test_the_nvcc_value_is_the_line_interpret_probe_reads():
    result = RunResult(0, False, NVCC_OUT, b"", ("nvcc", "--version"), 0.0)
    found = cuda_adapter.interpret_probe(result, "nvcc")
    assert found.version == EXPECTED["toolchain"]["nvcc"]


@pytest.mark.parametrize(
    ("stdout", "value"),
    [
        (b"gcc  (Example)\t1.0 \r\nsecond\n", "gcc (Example) 1.0"),
        (b"gcc 1.0", "gcc 1.0"),
    ],
)
def test_the_gcc_line_is_the_first_line_spelt(machine, stdout, value):
    machine.put("gcc", stdout)
    assert local_record("external", timeout_s=TIMEOUT)["toolchain"]["gcc"] == value


@pytest.mark.parametrize(
    ("stdout", "revision", "driver"),
    [
        (b"  Example  GPU ,  8.9 ,\t617.14 \r\n", "Example GPU sm_89", "617.14"),
        (b"Example, GPU, 12.0, 700.1\n", "Example, GPU sm_120", "700.1"),
        (b"\nExample GPU, 7.5, 1\n\n", "Example GPU sm_75", "1"),
    ],
)
def test_the_device_line_is_spelt(machine, stdout, revision, driver):
    machine.put("nvidia-smi", stdout)
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["revision"] == revision
    assert record["toolchain"]["nvidia_driver"] == driver


@pytest.mark.parametrize(
    ("stdout", "fact", "reason"),
    [
        (b"Example GPU, 8.9\n", "revision", "is not a name"),
        (b"Example GPU\n", "revision", "is not a name"),
        (b"Example GPU, 8, 617.14\n", "revision", "not <major>.<minor>"),
        (b"Example GPU, 8.x, 617.14\n", "revision", "not <major>.<minor>"),
        (b"Example GPU, 8.9.1, 617.14\n", "revision", "not <major>.<minor>"),
        (b"Example GPU, [N/A], 617.14\n", "revision", "not <major>.<minor>"),
        (b"Example GPU, , 617.14\n", "revision", "the value is empty"),
        (b" , 8.9, 617.14\n", "revision", "the value is empty"),
        (b"Example GPU, 8.9, \n", "toolchain.nvidia_driver", "the value is empty"),
    ],
)
def test_an_unreadable_device_line(machine, stdout, fact, reason):
    machine.put("nvidia-smi", stdout)
    assert reason in fails(fact)


@pytest.mark.parametrize(
    ("key", "stdout", "fact"),
    [
        ("nvidia-smi", "Examplé GPU, 8.9, 617.14\n".encode(), "revision"),
        ("nvidia-smi", b"Example GPU, 8.9, 617\x0b14\n", "toolchain.nvidia_driver"),
        ("gcc", "gcc (Éxample) 1.0\n".encode(), "toolchain.gcc"),
        ("gcc", b"gcc\x00 1.0\n", "toolchain.gcc"),
        (
            "nvcc",
            "Cuda compilation tools, release 13.1, V13.1.115 –\n".encode(),
            "toolchain.nvcc",
        ),
        ("nvcc", b"Cuda compilation tools, release 13.1\rx\n", "toolchain.nvcc"),
    ],
)
def test_non_ascii_or_control_characters_are_refused(machine, key, stdout, fact):
    machine.put(key, stdout)
    message = fails(fact)
    assert "outside 0x20 to 0x7E" in message
    assert "xample" not in message


def test_an_over_long_revision_is_refused(machine):
    machine.put("nvidia-smi", b"G" * 249 + b", 8.9, 617.14\n")
    assert (
        local_record("external", timeout_s=TIMEOUT)["revision"] == "G" * 249 + " sm_89"
    )
    machine.put("nvidia-smi", b"G" * 250 + b", 8.9, 617.14\n")
    assert "longer than 255" in fails("revision")


@pytest.mark.parametrize(
    ("key", "stdout", "fact"),
    [
        ("gcc", b"g" * 256 + b"\n", "toolchain.gcc"),
        ("nvidia-smi", b"GPU, 8.9, " + b"1" * 256 + b"\n", "toolchain.nvidia_driver"),
        ("nvidia-smi", b"G" * 256 + b", 8.9, 1\n", "revision"),
        (
            "nvcc",
            b"Cuda compilation tools, release " + b"1" * 230 + b"\n",
            "toolchain.nvcc",
        ),
    ],
)
def test_an_over_long_value_is_refused_and_not_cut(machine, key, stdout, fact):
    machine.put(key, stdout)
    assert "longer than 255" in fails(fact)


@pytest.mark.parametrize("hw_source", ["", "External", None, 1, ["external"]])
def test_a_bad_hw_source_is_refused_before_anything_runs(machine, hw_source):
    with pytest.raises(InvalidRecordError):
        local_record(hw_source, timeout_s=TIMEOUT)
    assert machine.calls() == []


@pytest.mark.parametrize(
    ("image", "error"),
    [("", ValueError), ("-x", ValueError), ("a b", ValueError), (7, TypeError)],
)
def test_an_image_the_check_refuses(machine, image, error):
    with pytest.raises(error):
        local_record("external", timeout_s=TIMEOUT, image=image)
    assert machine.calls() == []


@pytest.mark.parametrize("name", ["Windows", "FreeBSD", "linux"])
def test_a_kernel_name_without_a_rule_starts_nothing(machine, monkeypatch, name):
    monkeypatch.setattr(standin_profile, "_kernel", lambda: (name, "1"))
    fails("kernel name")
    assert machine.calls() == []


def test_an_unreadable_host_fact_gives_no_record(machine, monkeypatch):
    def read(path):
        if path == "/etc/os-release":
            raise FileNotFoundError(path)
        return CPUINFO

    monkeypatch.setattr(standin_profile, "_read", read)
    assert "cannot be read (FileNotFoundError)" in fails("host.os")


def test_the_host_members_follow_the_cpu_standin_rules(machine, monkeypatch):
    monkeypatch.setattr(standin_profile, "_kernel", lambda: ("Linux", "6.0-generic"))
    record = local_record("external", timeout_s=TIMEOUT)
    assert record["host"] == {"cpu": "Example(R) CPU X-1", "os": "linux exampleos 1.0"}


@pytest.mark.parametrize("timeout_s", [0, -1, float("nan")])
def test_a_bad_timeout_is_refused(machine, timeout_s):
    with pytest.raises(ValueError):
        local_record("external", timeout_s=timeout_s)


def test_the_constants():
    assert ACCELERATOR == targets.CUDA_GPU == "cuda_gpu"
    assert cuda_profile.GCC == "gcc"
    assert DEVICE_QUERY == (
        "--query-gpu=name,compute_cap,driver_version",
        "--format=csv,noheader",
    )
    assert cuda_profile.UnreadableFactError is standin_profile.UnreadableFactError


def test_the_public_names_and_signature():
    public = {
        name
        for name, value in vars(cuda_profile).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {
        "ACCELERATOR",
        "DEVICE_QUERY",
        "GCC",
        "UnreadableFactError",
        "local_record",
    }
    parameters = inspect.signature(local_record).parameters
    assert list(parameters) == ["hw_source", "timeout_s", "image"]
    assert parameters["timeout_s"].default is inspect.Parameter.empty


def test_the_device_probe_of_the_adapter_is_unchanged():
    assert cuda_adapter._DEVICE_QUERY == (
        "--query-gpu=name,driver_version",
        "--format=csv,noheader",
    )


def _one_gpu():
    smi = shutil.which("nvidia-smi")
    if smi is None:
        return False
    ran = subprocess.run(
        [smi, *DEVICE_QUERY], capture_output=True, check=False, timeout=TIMEOUT
    )
    lines = [line for line in ran.stdout.splitlines() if line.strip()]
    return ran.returncode == 0 and len(lines) == 1


def test_the_host_record_of_this_machine():
    if not hasattr(os, "uname") or sys.platform != "linux":
        pytest.skip("the live case runs on Linux only")
    if shutil.which("nvcc") is None or shutil.which("gcc") is None:
        pytest.skip("nvcc or gcc is not on PATH")
    if not _one_gpu():
        pytest.skip("nvidia-smi with exactly one GPU is not present")
    record = local_record("external", timeout_s=TIMEOUT)
    assert hw_profile_key(record).name.startswith("cuda_gpu-")
    assert record["accelerator"] == "cuda_gpu"
    assert re.fullmatch(r".+ sm_[0-9]+", record["revision"])
    assert list(record["toolchain"]) == ["nvcc", "gcc", "nvidia_driver"]
    assert record["toolchain"]["nvcc"].startswith("Cuda compilation tools, release")
    assert record["toolchain"]["gcc"].startswith("gcc")
    assert record["host"]["os"].split(" ")[0] in ("linux", "wsl")
