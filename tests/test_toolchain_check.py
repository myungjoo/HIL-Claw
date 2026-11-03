import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    clang_adapter,
    clang_build,
    cuda_adapter,
    local_run,
    qnn_adapter,
    standin_container,
    toolchain_check,
)
from hilclaw.toolchain_check import (
    CLIENT,
    COMPONENTS,
    EXIT_FAULT,
    EXIT_READ,
    EXIT_UNREADABLE,
    EXIT_USAGE,
    HOST_TIME_LIMIT_S,
    IMAGE_TIME_LIMIT_S,
    REMOVAL_TIME_LIMIT_S,
    Component,
    check,
    exit_status,
    main,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")
IMAGE = "example/tools:1"
USAGE_LINE = (
    b"hilclaw.toolchain_check: usage: python -m hilclaw.toolchain_check [<image> ...]\n"
)

# Fault-injection scripts (ADR-0194 decision 6), run by this interpreter from
# the test's own temporary directory and passed only as a table's program.
HANG = "import threading\nthreading.Event().wait()\n"
NO_LINE = "pass\n"
NO_GPU = "import sys\nsys.exit(6)\n"

# A stub container client: it records its arguments and answers as told by
# the files beside it. It stands for the container runtime, not for a tool.
CLIENT_STUB = """#!{python}
import json, os, sys, threading
here = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
if sys.argv[1] == "rm":
    sys.exit(0)
with open(os.path.join(here, "answer.json"), encoding="utf-8") as answer:
    answer = json.load(answer)
if answer.get("hang"):
    threading.Event().wait()
sys.stdout.write(answer.get("stdout", ""))
sys.exit(answer.get("status", 0))
"""


def component(program, **changes):
    values = {
        "assemble": clang_adapter.assemble_probe,
        "interpret": clang_adapter.interpret_probe,
        "interpret_container": clang_adapter.interpret_container_probe,
        "program": program,
    }
    values.update(changes)
    return Component(**values)


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

    def write(body, name="tool.py"):
        path = directory / name
        path.write_text(body, encoding="utf-8")
        return (sys.executable, str(path))

    return write


@pytest.fixture
def missing(tmp_path):
    return str(tmp_path / "no-such-program")


@pytest.fixture
def stub_client(tmp_path):
    directory = tmp_path / "client"
    directory.mkdir()
    path = directory / "docker"
    path.write_text(CLIENT_STUB.format(python=sys.executable), encoding="utf-8")
    path.chmod(0o755)

    class Client:
        program = str(path)

        def answer(self, **values):
            (directory / "answer.json").write_text(json.dumps(values), encoding="utf-8")

        def calls(self):
            log = directory / "calls.jsonl"
            if not log.exists():
                return []
            return [json.loads(line) for line in log.read_text().splitlines()]

    return Client()


class Stream:
    def __init__(self, take=None, fail=None):
        self.data = b""
        self.take = take
        self.fail = fail

    def write(self, data):
        if self.fail is not None:
            raise self.fail
        taken = data if self.take is None else data[: self.take]
        self.data += taken
        return len(taken)

    def flush(self):
        pass


def run_main(argv, **options):
    out, err = io.BytesIO(), io.BytesIO()
    status = main(argv, stdout=out, stderr=err, **options)
    return status, out.getvalue(), err.getvalue()


def test_constants():
    assert (EXIT_READ, EXIT_UNREADABLE, EXIT_USAGE, EXIT_FAULT) == (0, 10, 20, 21)
    assert (HOST_TIME_LIMIT_S, IMAGE_TIME_LIMIT_S, REMOVAL_TIME_LIMIT_S) == (
        30,
        120,
        30,
    )
    assert CLIENT == "docker"


def test_the_table_holds_the_clang_adapter_probe_pair():
    assert list(COMPONENTS) == ["clang", "nvcc", "nvidia-smi", "qnn-net-run"]
    assert COMPONENTS["clang"] == Component(
        assemble=clang_adapter.assemble_probe,
        interpret=clang_adapter.interpret_probe,
        interpret_container=clang_adapter.interpret_container_probe,
        program=clang_adapter.PROGRAM,
        host_only=False,
    )


def test_the_table_holds_the_cuda_adapter_probe_pairs():
    assert COMPONENTS["nvcc"] == Component(
        assemble=cuda_adapter.assemble_probe,
        interpret=cuda_adapter.interpret_probe,
        interpret_container=cuda_adapter.interpret_container_probe,
        program=cuda_adapter.PROGRAM,
        host_only=False,
    )
    assert COMPONENTS["nvidia-smi"] == Component(
        assemble=cuda_adapter.assemble_device_probe,
        interpret=cuda_adapter.interpret_device_probe,
        interpret_container=None,
        program=cuda_adapter.DEVICE_PROGRAM,
        host_only=True,
    )


def test_the_table_holds_the_qnn_adapter_probe_pair():
    assert COMPONENTS["qnn-net-run"] == Component(
        assemble=qnn_adapter.assemble_probe,
        interpret=qnn_adapter.interpret_probe,
        interpret_container=qnn_adapter.interpret_container_probe,
        program=qnn_adapter.VERSION_PROGRAM,
        host_only=False,
    )


def test_real_clang_on_the_host_is_present_with_the_compiler_version(clang):
    report = check()
    expected = clang_build.compiler_version(timeout_s=HOST_TIME_LIMIT_S)
    assert list(report["host"]) == list(COMPONENTS)
    assert report["host"]["clang"] == {
        "state": "present",
        "version": expected,
        "message": None,
    }
    assert report["images"] == {}
    assert exit_status(report) == EXIT_READ


def test_a_program_that_does_not_exist_is_absent(missing):
    report = check(components={"x": component(missing)})
    entry = report["host"]["x"]
    assert (entry["state"], entry["version"]) == ("absent", None)
    assert entry["message"]
    assert exit_status(report) == EXIT_READ


def test_fault_query_that_hangs_is_unreadable(script, monkeypatch):
    # Stands for a version query that never ends (ADR-0194 decisions 6 and 7).
    monkeypatch.setattr(toolchain_check, "HOST_TIME_LIMIT_S", 0.5)
    report = check(components={"x": component(script(HANG))})
    assert report["host"]["x"]["state"] == "unreadable"
    assert exit_status(report) == EXIT_UNREADABLE


def test_fault_query_that_prints_no_line_is_unreadable(script):
    # Stands for a version query that prints no line (ADR-0194 decisions 6 and 7).
    report = check(components={"x": component(script(NO_LINE))})
    entry = report["host"]["x"]
    assert (entry["state"], entry["version"]) == ("unreadable", None)
    assert entry["message"]


def test_an_error_the_adapter_does_not_read_is_unreadable_on_the_host(monkeypatch):
    def failing(*args, **kwargs):
        raise OSError(5, "I/O")

    monkeypatch.setattr(local_run, "run", failing)
    report = check(components={"x": component("clang")})
    assert report["host"]["x"] == {
        "state": "unreadable",
        "version": None,
        "message": "the query could not be run",
    }


def test_the_host_query_is_assembled_by_the_adapter(monkeypatch):
    seen = []

    def fake_run(command, *, timeout_s, env=None):
        seen.append((tuple(command), timeout_s, env))
        return local_run.RunResult(0, False, b"v 1\n", b"", tuple(command), 0.1)

    monkeypatch.setattr(local_run, "run", fake_run)
    report = check(components={"x": component(("prefix", "tool"))})
    assert seen == [(("prefix", "tool", "--version"), HOST_TIME_LIMIT_S, None)]
    assert report["host"]["x"]["version"] == "v 1"


@posix_only
@pytest.mark.parametrize(
    ("answer", "state", "version"),
    [
        (
            {"stdout": "clang version 77.0.1 (stub)\nTarget: x\n"},
            "present",
            "clang version 77.0.1 (stub)",
        ),
        ({"status": 127}, "absent", None),
        ({"status": 126}, "absent", None),
        ({"status": 1, "stdout": "clang version 1\n"}, "unreadable", None),
        ({"stdout": ""}, "unreadable", None),
    ],
)
def test_image_component_cases_through_a_stub_client(
    stub_client, missing, answer, state, version
):
    stub_client.answer(**answer)
    report = check(
        [IMAGE], components={"clang": component("clang")}, client=stub_client.program
    )
    image = report["images"][IMAGE]
    assert (image["state"], image["message"]) == ("read", None)
    entry = image["components"]["clang"]
    assert (entry["state"], entry["version"]) == (state, version)
    expected = EXIT_UNREADABLE if state == "unreadable" else EXIT_READ
    assert exit_status(report) == expected


@posix_only
def test_image_container_carries_no_network_and_no_pull_and_a_removed_empty_dir(
    stub_client, monkeypatch
):
    monkeypatch.setattr(local_run, "run", local_run.run)
    stub_client.answer(stdout="clang version 1\n")
    report = check(
        [IMAGE], components={"c": component("clang")}, client=stub_client.program
    )
    assert report["images"][IMAGE]["components"]["c"]["state"] == "present"
    [arguments] = stub_client.calls()
    assert arguments[0] == "run"
    image_at = arguments.index(IMAGE)
    options = arguments[:image_at]
    assert options[options.index("--network") + 1] == "none"
    assert options[options.index("--pull") + 1] == "never"
    assert "--entrypoint=" in options
    assert arguments[image_at + 1 :] == ["clang", "--version"]
    mount = options[options.index("--mount") + 1]
    source = mount.split("source=", 1)[1].split(",", 1)[0]
    assert os.path.basename(source).startswith("hilclaw-toolchain-check-")
    assert not os.path.exists(source)


@posix_only
def test_image_query_that_hangs_is_unreadable_and_the_container_removed(
    stub_client, monkeypatch
):
    monkeypatch.setattr(toolchain_check, "IMAGE_TIME_LIMIT_S", 0.5)
    stub_client.answer(hang=True)
    report = check(
        [IMAGE], components={"c": component("clang")}, client=stub_client.program
    )
    assert report["images"][IMAGE]["components"]["c"]["state"] == "unreadable"
    calls = stub_client.calls()
    assert [call[0] for call in calls] == ["run", "rm"]


@posix_only
def test_a_client_failure_makes_the_image_unreadable(stub_client):
    stub_client.answer(status=125)
    report = check(
        [IMAGE], components={"c": component("clang")}, client=stub_client.program
    )
    assert report["images"][IMAGE] == {
        "state": "unreadable",
        "message": "no container of the image could be used",
        "components": {},
    }
    assert exit_status(report) == EXIT_UNREADABLE


def test_a_client_that_cannot_be_found_makes_the_image_unreadable(missing, monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 1000, raising=False)
    report = check([IMAGE], components={"c": component("clang")}, client=missing)
    assert report["images"][IMAGE]["state"] == "unreadable"
    assert report["images"][IMAGE]["components"] == {}


def test_a_platform_without_numeric_user_makes_the_image_unreadable(monkeypatch):
    monkeypatch.delattr(os, "getuid", raising=False)
    started = []

    def not_found(command, **options):
        started.append(command)
        raise local_run.ProgramNotFoundError(command[0])

    monkeypatch.setattr(local_run, "run", not_found)
    report = check([IMAGE], components={"c": component(("absent-tool",))})
    assert report["images"][IMAGE]["state"] == "unreadable"
    assert len(started) == 1


def test_the_temporary_directory_is_removed_when_the_container_call_raises(monkeypatch):
    seen = []

    def failing(image, build_dir, *args, **kwargs):
        seen.append(build_dir)
        assert os.path.isdir(build_dir) and not os.listdir(build_dir)
        raise RuntimeError("boom")

    monkeypatch.setattr(standin_container, "run_in_container", failing)
    report = check([IMAGE, IMAGE], components={"c": component(("absent-tool",))})
    assert list(report["images"]) == [IMAGE]
    assert report["images"][IMAGE]["state"] == "unreadable"
    assert len(seen) == 1 and not os.path.exists(seen[0])


def test_host_only_components_are_not_read_in_an_image(monkeypatch, missing):
    started = []

    def fake_container(image, build_dir, program, arguments, **options):
        started.append((program, tuple(arguments), options))
        return standin_container.ContainerResult(
            0, False, b"v 2\n", b"", ("docker",), 0.1, "n", None
        )

    monkeypatch.setattr(standin_container, "run_in_container", fake_container)
    table = {
        "device": component(missing, host_only=True),
        "tool": component(("pre", "tool")),
    }
    report = check([IMAGE], components=table, client="podman")
    assert list(report["host"]) == ["device", "tool"]
    assert report["images"][IMAGE]["components"] == {
        "tool": {"state": "present", "version": "v 2", "message": None}
    }
    assert started == [
        (
            "pre",
            ("tool", "--version"),
            {
                "timeout_s": IMAGE_TIME_LIMIT_S,
                "removal_timeout_s": REMOVAL_TIME_LIMIT_S,
                "client": "podman",
            },
        )
    ]


@pytest.mark.parametrize(
    ("images", "error"),
    [
        ("img", TypeError),
        (b"img", TypeError),
        (["-x"], ValueError),
        ([""], ValueError),
        (["a b"], ValueError),
        ([3], TypeError),
    ],
)
def test_check_refuses_images_before_anything_starts(images, error, monkeypatch):
    monkeypatch.setattr(local_run, "run", lambda *a, **k: pytest.fail("started"))
    with pytest.raises(error):
        check(images)


def test_check_passes_on_an_error_of_an_assemble_part():
    with pytest.raises(TypeError) as caught:
        check(components={"x": component(3)})
    assert caught.value.parameter == "program"


@pytest.mark.parametrize(
    ("report", "status"),
    [
        ({"host": {}, "images": {}}, EXIT_READ),
        ({"host": {"a": {"state": "absent"}}, "images": {}}, EXIT_READ),
        ({"host": {"a": {"state": "unreadable"}}, "images": {}}, EXIT_UNREADABLE),
        (
            {"host": {}, "images": {"i": {"state": "unreadable", "components": {}}}},
            EXIT_UNREADABLE,
        ),
        (
            {
                "host": {"a": {"state": "present"}},
                "images": {
                    "i": {"state": "read", "components": {"a": {"state": "unreadable"}}}
                },
            },
            EXIT_UNREADABLE,
        ),
        (
            {
                "host": {"a": {"state": "present"}},
                "images": {
                    "i": {"state": "read", "components": {"a": {"state": "absent"}}}
                },
            },
            EXIT_READ,
        ),
    ],
)
def test_exit_status(report, status):
    assert exit_status(report) == status


def test_exit_status_refuses_a_value_that_is_no_report():
    with pytest.raises((KeyError, TypeError)):
        exit_status({"host": {}})


def test_main_writes_one_document_and_returns_read(missing):
    status, out, err = run_main([], components={"x": component(missing)})
    assert status == EXIT_READ and err == b""
    assert out.endswith(b"\n") and out.count(b"\n") == 1
    report = json.loads(out)
    assert report["host"]["x"]["state"] == "absent"
    assert report["images"] == {}
    assert missing.encode() not in out


def test_main_returns_unreadable_with_a_report(script):
    status, out, err = run_main([], components={"x": component(script(NO_LINE))})
    assert status == EXIT_UNREADABLE and err == b""
    assert json.loads(out)["host"]["x"]["state"] == "unreadable"


@pytest.mark.parametrize("argv", [["--help"], [""], ["a b"], [IMAGE, "-x"], ["a\0b"]])
def test_main_refuses_a_bad_argument_before_anything_starts(argv, monkeypatch):
    monkeypatch.setattr(local_run, "run", lambda *a, **k: pytest.fail("started"))
    status, out, err = run_main(argv)
    assert (status, out, err) == (EXIT_USAGE, b"", USAGE_LINE)


@pytest.mark.parametrize(
    "stdout",
    [
        Stream(take=3),
        Stream(fail=OSError("closed")),
        Stream(fail=ValueError("closed file")),
    ],
)
def test_main_faults_on_a_standard_output_it_cannot_write(stdout, missing):
    err = io.BytesIO()
    status = main([], stdout=stdout, stderr=err, components={"x": component(missing)})
    assert status == EXIT_FAULT
    assert err.getvalue() == b"hilclaw.toolchain_check: fault: %s\n" % (
        b"OSError" if stdout.fail is None else type(stdout.fail).__name__.encode()
    )


def test_main_faults_without_a_standard_output(monkeypatch, missing):
    monkeypatch.setattr(sys, "stdout", object())
    monkeypatch.setattr(local_run, "run", lambda *a, **k: pytest.fail("started"))
    err = io.BytesIO()
    status = main([], stderr=err, components={"x": component(missing)})
    assert status == EXIT_FAULT
    assert err.getvalue() == b"hilclaw.toolchain_check: fault: OSError\n"


def test_main_faults_on_its_own_error_and_writes_no_report():
    status, out, err = run_main(
        [], components={"x": component("clang", assemble=lambda **k: None)}
    )
    assert (status, out) == (EXIT_FAULT, b"")
    assert err == b"hilclaw.toolchain_check: fault: AttributeError\n"


def test_main_keeps_its_status_when_standard_error_cannot_be_written(monkeypatch):
    monkeypatch.setattr(sys, "stderr", object())
    assert main(["--help"], stdout=io.BytesIO()) == EXIT_USAGE
    assert (
        main(["--help"], stdout=io.BytesIO(), stderr=Stream(fail=OSError()))
        == EXIT_USAGE
    )


def test_main_reads_the_process_arguments_and_streams(
    monkeypatch, missing, capfdbinary
):
    monkeypatch.setattr(sys, "argv", ["toolchain_check", "-bad"])
    assert main() == EXIT_USAGE
    assert capfdbinary.readouterr().err == USAGE_LINE
    monkeypatch.setattr(sys, "argv", ["toolchain_check"])
    assert main(components={"x": component(missing)}) == EXIT_READ
    captured = capfdbinary.readouterr()
    assert json.loads(captured.out)["host"]["x"]["state"] == "absent"
    assert captured.err == b""


def test_running_the_module_calls_main():
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.toolchain_check", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert (done.returncode, done.stdout, done.stderr) == (EXIT_USAGE, b"", USAGE_LINE)


def test_running_the_module_reports_the_host(clang):
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.toolchain_check"],
        cwd=REPO_ROOT,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert (done.returncode, done.stderr) == (EXIT_READ, b"")
    assert json.loads(done.stdout)["host"]["clang"]["state"] == "present"


def test_fault_device_query_without_a_gpu_is_absent_with_no_device(script):
    # Stands for nvidia-smi on a machine with no GPU: status 6, "A query to find
    # an object was unsuccessful" (nvidia-smi documentation, "RETURN VALUE",
    # https://docs.nvidia.com/deploy/nvidia-smi/index.html, read 2026-11-03).
    table = {"nvidia-smi": COMPONENTS["nvidia-smi"]._replace(program=script(NO_GPU))}
    report = check(components=table)
    assert report["host"]["nvidia-smi"] == {
        "state": "absent",
        "version": None,
        "message": cuda_adapter.NO_DEVICE,
    }
    assert exit_status(report) == EXIT_READ


def test_the_device_query_is_not_read_in_an_image(monkeypatch):
    started = []

    def fake_container(image, build_dir, program, arguments, **options):
        started.append((program, tuple(arguments)))
        return standin_container.ContainerResult(
            127, False, b"", b"", ("docker",), 0.1, "n", None
        )

    def fake_run(command, *, timeout_s, env=None):
        raise local_run.ProgramNotFoundError(command[0])

    monkeypatch.setattr(standin_container, "run_in_container", fake_container)
    monkeypatch.setattr(local_run, "run", fake_run)
    report = check([IMAGE])
    assert started == [
        ("clang", ("--version",)),
        ("nvcc", ("--version",)),
        ("qnn-net-run", ("--version",)),
    ]
    assert list(report["host"]) == ["clang", "nvcc", "nvidia-smi", "qnn-net-run"]
    assert report["host"]["nvidia-smi"]["state"] == "absent"
    assert report["host"]["nvidia-smi"]["message"] != cuda_adapter.NO_DEVICE
    assert list(report["images"][IMAGE]["components"]) == [
        "clang",
        "nvcc",
        "qnn-net-run",
    ]


def test_real_cuda_tools_on_the_host_are_read_by_the_cuda_adapter():
    report = check()
    for name, found in (
        ("nvcc", cuda_adapter.probe(timeout_s=HOST_TIME_LIMIT_S)),
        ("nvidia-smi", cuda_adapter.device_probe(timeout_s=HOST_TIME_LIMIT_S)),
    ):
        entry = report["host"][name]
        assert (entry["state"], entry["version"]) == (found.state, found.version)


def test_real_qnn_sdk_on_the_host_is_read_by_the_qnn_adapter():
    report = check()
    found = qnn_adapter.probe(timeout_s=HOST_TIME_LIMIT_S)
    entry = report["host"]["qnn-net-run"]
    assert (entry["state"], entry["version"]) == (found.state, found.version)


def test_image_entry_reads_one_image_and_not_the_host(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1000, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 1000, raising=False)
    started = []

    def answering(command, **options):
        started.append(list(command))
        return local_run.RunResult(
            0, False, b"clang version 9\n", b"", tuple(command), 0.0
        )

    monkeypatch.setattr(local_run, "run", answering)
    entry = toolchain_check.image_entry(IMAGE, components={"c": component("clang")})
    assert entry == {
        "state": "read",
        "message": None,
        "components": {
            "c": {"state": "present", "version": "clang version 9", "message": None}
        },
    }
    assert [command[1] for command in started] == ["run"]


@pytest.mark.parametrize(("image", "error"), [("-x", ValueError), (None, TypeError)])
def test_image_entry_refuses_a_reference_before_anything_starts(
    image, error, monkeypatch
):
    monkeypatch.setattr(local_run, "run", lambda *a, **k: pytest.fail("started"))
    with pytest.raises(error):
        toolchain_check.image_entry(image)
