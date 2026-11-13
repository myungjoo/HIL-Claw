import io
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from hilclaw import keys, remote_run
from hilclaw.remote_eval import (
    BUNDLE,
    CODE,
    DATA,
    IDENTITY,
    OK,
    PACKAGE,
    PYTHON,
    REMOTE_STATUS,
    REQUEST,
    SNAPSHOT_PATHS,
    SSH_FAILED,
    TIMED_OUT,
    Outcome,
    RemoteStepError,
    evaluate,
    fetch,
    hw_profile,
    prepare,
    snapshot,
    summary,
)

DEST = "tester@host.invalid"
ENV = {remote_run.DESTINATION_VARIABLE: DEST}
TASK = "T-0001"
IMAGE = "example/standin:arm64"
REAL_TASK_VARIABLE = "HILCLAW_REMOTE_TEST_TASK"
REAL_IMAGE_VARIABLE = "HILCLAW_REMOTE_TEST_IMAGE"
needs_tools = pytest.mark.skipif(
    shutil.which("sh") is None or shutil.which("git") is None,
    reason="no POSIX sh or git",
)

SSH_STUB = """\
import json, os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
target = args[args.index("--") + 1]
if os.path.exists(os.path.join(here, "fail")):
    sys.stderr.write("ssh: connect to host " + target + ": refused")
    sys.exit(255)
home = os.path.join(here, "home")
os.makedirs(home, exist_ok=True)
sys.stdout.flush()
sys.exit(subprocess.run(["sh", "-c", args[-1]], cwd=home).returncode)
"""

FAKE_GIVEN_EVAL = """\
import json, os, subprocess, sys, time
root = os.environ["HILCLAW_DATA_REPO_LOCAL_PATH"]
time.sleep(float(os.environ.get("FAKE_EVAL_SLEEP", "0")))
status = int(os.environ.get("FAKE_EVAL_STATUS", "0"))
parts = [open(path, encoding="utf-8").read() for path in sys.argv[1:]]
parts.append(os.environ["HILCLAW_STANDIN_IMAGE"])
with open(os.path.join(root, "run.txt"), "w", encoding="utf-8") as target:
    target.write("|".join(parts))
subprocess.run(["git", "-C", root, "add", "-A"], check=True)
subprocess.run(["git", "-C", root, "commit", "-q", "-m", "run"], check=True)
outcome = "measured" if status == 0 else "not_measured"
print(json.dumps({"outcome": outcome, "args": sys.argv[1:]}))
sys.exit(status)
"""

FAKE_PROFILE = """\
def local_record(hw_source, *, timeout_s, image):
    return {"hw_source": hw_source, "timeout_s": timeout_s, "image": image}
"""


def archive():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for name, text in (
            ("hilclaw/__init__.py", ""),
            ("hilclaw/given_eval.py", FAKE_GIVEN_EVAL),
            ("hilclaw/standin_profile.py", FAKE_PROFILE),
        ):
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


@pytest.fixture
def stub(tmp_path):
    directory = tmp_path / "ssh"
    directory.mkdir()
    path = directory / "ssh_stub.py"
    path.write_text(SSH_STUB, encoding="utf-8")

    class Stub:
        program = (sys.executable, str(path))
        home = directory / "home"

        def fail(self):
            (directory / "fail").write_text("")

        def calls(self):
            log = directory / "calls.jsonl"
            if not log.exists():
                return []
            return [json.loads(line) for line in log.read_text().splitlines()]

    return Stub()


@pytest.fixture
def files(tmp_path):
    request = tmp_path / "request.json"
    request.write_text('{"request": 1}', encoding="utf-8")
    code = tmp_path / "given.c"
    code.write_text("int x;", encoding="utf-8")
    return request, code


def python():
    return (Path(sys.executable).as_posix(),)


def common(stub, timeout_s=60):
    return {"timeout_s": timeout_s, "environ": ENV, "ssh": stub.program}


def leaks(value):
    text = repr(value)
    return "host.invalid" in text or "tester" in text


def no_file_leaks(root):
    for path in Path(root).rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            assert b"host.invalid" not in path.read_bytes(), path


def git(*args):
    return subprocess.run(
        ["git", *map(str, args)], capture_output=True, check=True, text=True
    ).stdout


def test_constants():
    assert (OK, REMOTE_STATUS, SSH_FAILED, TIMED_OUT) == (
        "ok",
        "remote_status",
        "ssh_failed",
        "timed_out",
    )
    assert (PACKAGE, DATA, REQUEST, CODE, BUNDLE) == (
        "package",
        "data",
        "request.json",
        "given.c",
        "data.bundle",
    )
    assert PYTHON == ("python3",)
    assert SNAPSHOT_PATHS == ("hilclaw", "catalog", "hilclaw.config.json")
    assert IDENTITY[1].endswith("@example.invalid")


@needs_tools
def test_the_whole_path(stub, files, tmp_path):
    request, code = files
    prepare(TASK, archive=archive(), **common(stub))
    data = stub.home / "hilclaw-driver" / TASK / DATA
    assert git("-C", data, "config", "--local", "user.name").strip() == IDENTITY[0]
    assert git("-C", data, "config", "--local", "user.email").strip() == IDENTITY[1]
    record = hw_profile(TASK, IMAGE, "external", python=python(), **common(stub))
    assert record == {"hw_source": "external", "timeout_s": 60.0, "image": IMAGE}
    done = evaluate(
        request, code, task=TASK, image=IMAGE, python=python(), **common(stub)
    )
    assert (done.state, done.returncode) == (OK, 0)
    assert summary(done) == {
        "outcome": "measured",
        "args": [f"../{REQUEST}", f"../{CODE}"],
    }
    bundle = tmp_path / "back.bundle"
    fetch(TASK, bundle, **common(stub))
    clone = tmp_path / "clone"
    git("clone", "-q", bundle, clone)
    assert (clone / "run.txt").read_text() == '{"request": 1}|int x;|' + IMAGE
    assert not leaks(done)
    no_file_leaks(stub.home)
    assert all(DEST in call for call in stub.calls())


@needs_tools
def test_a_remote_non_zero_status(stub, files, monkeypatch):
    monkeypatch.setenv("FAKE_EVAL_STATUS", "10")
    prepare(TASK, archive=archive(), **common(stub))
    done = evaluate(*files, task=TASK, image=IMAGE, python=python(), **common(stub))
    assert (done.state, done.returncode) == (REMOTE_STATUS, 10)
    assert summary(done)["outcome"] == "not_measured"


@needs_tools
def test_a_remote_status_255_reads_as_an_ssh_failure(stub, files, monkeypatch):
    monkeypatch.setenv("FAKE_EVAL_STATUS", "255")
    prepare(TASK, archive=archive(), **common(stub))
    done = evaluate(*files, task=TASK, image=IMAGE, python=python(), **common(stub))
    assert done == Outcome(SSH_FAILED, None, "", "", done.command)
    assert remote_run.PLACEHOLDER in done.command
    assert not leaks(done)


@needs_tools
def test_a_time_out(stub, files, monkeypatch):
    prepare(TASK, archive=archive(), **common(stub))
    monkeypatch.setenv("FAKE_EVAL_SLEEP", "30")
    done = evaluate(*files, task=TASK, image=IMAGE, python=python(), **common(stub, 5))
    assert (done.state, done.returncode) == (TIMED_OUT, None)


@needs_tools
def test_an_ssh_failure_stops_each_step(stub, files, tmp_path):
    stub.fail()
    with pytest.raises(RemoteStepError) as caught:
        prepare(TASK, archive=archive(), **common(stub))
    assert (caught.value.step, caught.value.outcome.state) == ("mkdir", SSH_FAILED)
    with pytest.raises(RemoteStepError) as caught:
        hw_profile(TASK, IMAGE, "external", **common(stub))
    assert caught.value.step == "hw_profile"
    with pytest.raises(RemoteStepError) as caught:
        evaluate(*files, task=TASK, image=IMAGE, **common(stub))
    assert caught.value.step == "put_request"
    with pytest.raises(RemoteStepError) as caught:
        fetch(TASK, tmp_path / "b", **common(stub))
    assert str(caught.value) == "remote step bundle failed: ssh_failed"
    assert not leaks(caught.value) and not leaks(caught.value.outcome)
    assert not (tmp_path / "b").exists()


@needs_tools
def test_a_failed_step_names_its_status(stub, tmp_path):
    with pytest.raises(RemoteStepError) as caught:
        fetch(TASK, tmp_path / "b", **common(stub))
    assert caught.value.outcome.state == REMOTE_STATUS
    assert str(caught.value).startswith("remote step bundle failed: status ")
    assert not (tmp_path / "b").exists()


@needs_tools
def test_a_bad_archive_stops_at_unpack(stub):
    with pytest.raises(RemoteStepError) as caught:
        prepare(TASK, archive=b"no tar", **common(stub))
    assert caught.value.step == "unpack"


def test_an_archive_that_is_no_bytes_is_refused(stub):
    with pytest.raises(TypeError):
        prepare(TASK, archive="text", **common(stub))
    assert stub.calls() == []


def every_call(files, tmp_path, **override):
    arguments = {"timeout_s": 60, "environ": ENV, "ssh": ("ssh-not-started",)}
    arguments.update(override)
    task = arguments.pop("task", TASK)
    yield lambda: prepare(task, archive=b"", **arguments)
    yield lambda: hw_profile(task, IMAGE, "external", **arguments)
    yield lambda: evaluate(*files, task=task, image=IMAGE, **arguments)
    yield lambda: fetch(task, tmp_path / "b", **arguments)


@pytest.mark.parametrize("environ", [{}, {remote_run.DESTINATION_VARIABLE: ""}])
def test_an_unset_destination_is_refused_first(files, tmp_path, environ):
    for call in every_call(files, tmp_path, environ=environ):
        with pytest.raises(remote_run.NotConfiguredError):
            call()


@pytest.mark.parametrize("task", ["T-1", "T-00001", "t-0001", "x", "../T-0001"])
def test_a_bad_task_is_refused(files, tmp_path, task):
    for call in every_call(files, tmp_path, task=task):
        with pytest.raises(ValueError):
            call()


def test_a_task_of_another_type_is_refused(files, tmp_path):
    for call in every_call(files, tmp_path, task=1):
        with pytest.raises(TypeError):
            call()


@pytest.mark.parametrize("timeout_s", [0, -1, -0.5, math.nan, math.inf])
def test_a_limit_that_is_not_positive_and_finite_is_refused(files, tmp_path, timeout_s):
    for call in every_call(files, tmp_path, timeout_s=timeout_s):
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("timeout_s", [None, True, "10"])
def test_a_limit_that_is_no_number_is_refused(files, tmp_path, timeout_s):
    for call in every_call(files, tmp_path, timeout_s=timeout_s):
        with pytest.raises(TypeError):
            call()


@pytest.mark.parametrize("image", ["", "-x", "a b"])
def test_a_refused_image(files, image):
    with pytest.raises(ValueError):
        evaluate(*files, task=TASK, image=image, timeout_s=60, environ=ENV)
    with pytest.raises(ValueError):
        hw_profile(TASK, image, "external", timeout_s=60, environ=ENV)


@pytest.mark.parametrize("missing", [0, 1])
def test_a_missing_file_is_refused(stub, files, tmp_path, missing):
    paths = list(files)
    paths[missing] = tmp_path / "absent"
    with pytest.raises(FileNotFoundError):
        evaluate(*paths, task=TASK, image=IMAGE, **common(stub))
    assert stub.calls() == []


def test_a_directory_is_no_file(stub, files, tmp_path):
    with pytest.raises(FileNotFoundError):
        evaluate(files[0], tmp_path, task=TASK, image=IMAGE, **common(stub))
    assert stub.calls() == []


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("", None),
        ("not json\n", None),
        ("[1]\n", None),
        ('noise\n{"outcome": "measured"}\n', {"outcome": "measured"}),
    ],
)
def test_summary(stdout, expected):
    assert summary(Outcome(OK, 0, stdout, "", ())) == expected


def test_snapshot_holds_the_package_and_no_git_directory():
    with tarfile.open(fileobj=io.BytesIO(snapshot())) as tar:
        names = tar.getnames()
    assert "hilclaw/remote_eval.py" in names
    assert "hilclaw.config.json" in names
    assert not any(name == ".git" or name.startswith(".git/") for name in names)
    assert {name.split("/")[0] for name in names} <= set(SNAPSHOT_PATHS)


def test_snapshot_of_an_unknown_revision_fails():
    with pytest.raises(subprocess.CalledProcessError):
        snapshot(revision="no-such-revision-T-0568")


KERNEL = b"""#include <stddef.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a,
                  const float *restrict b, float *restrict c)
{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
"""
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 8, "k": 8, "n": 8},
    "dtype": "fp32",
    "layout": "row_major",
}


@pytest.mark.skipif(
    not remote_run.configured(os.environ)
    or not os.environ.get(REAL_TASK_VARIABLE)
    or not os.environ.get(REAL_IMAGE_VARIABLE),
    reason=(
        f"{remote_run.DESTINATION_VARIABLE}, {REAL_TASK_VARIABLE} "
        f"or {REAL_IMAGE_VARIABLE} is not set"
    ),
)
def test_the_real_machine_evaluates_given_code(tmp_path):
    task = os.environ[REAL_TASK_VARIABLE]
    image = os.environ[REAL_IMAGE_VARIABLE]
    try:
        prepare(task, timeout_s=300)
        profile = hw_profile(task, image, "external", timeout_s=300)
        request = tmp_path / "request.json"
        request.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "hw_profile": {
                        "key": keys.hw_profile_key(profile).name,
                        "record": profile,
                    },
                    "op_signature": {
                        "key": keys.op_signature_key(OP).name,
                        "record": OP,
                    },
                    "objective": {
                        "objectives": [{"type": "latency_minimisation"}],
                        "constraints": [],
                    },
                    "candidates_per_round": 1,
                    "n_max": 6,
                    "draws": 1,
                    "tolerance": {"rtol": 1e-4, "atol": 1e-5},
                    "round_budget": 1,
                }
            ),
            encoding="utf-8",
        )
        code = tmp_path / "given.c"
        code.write_bytes(KERNEL)
        done = evaluate(request, code, task=task, image=image, timeout_s=1200)
        assert done.state in (OK, REMOTE_STATUS)
        assert summary(done)["sim"]["standing"] == "verified"
        fetch(task, tmp_path / "data.bundle", timeout_s=300)
        assert (tmp_path / "data.bundle").stat().st_size > 0
        assert not leaks(done) and remote_run.destination() not in repr(done)
    finally:
        removed = remote_run.remove_task_directory(task, timeout_s=120)
    assert removed.returncode == 0
