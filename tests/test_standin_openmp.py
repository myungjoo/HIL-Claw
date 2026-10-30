"""Tests of the check that the stand-in image builds and starts an OpenMP program (ADR-0188)."""

import os
import shutil
import stat
import subprocess

import openmp_clang
import pytest

from hilclaw import (
    clang_build,
    local_run,
    standin_container,
    standin_openmp,
    standin_run,
    standin_settings,
    standin_waiter_line,
)

IMAGE = "stub.invalid/standin:fake"
POSIX = pytest.mark.skipif(not hasattr(os, "getuid"), reason="needs a numeric user")
STUB = """#!/bin/sh
log={log}
echo "$*" >> "$log"
if [ "$1" = rm ]; then
    exit {removal}
fi
for word in "$@"; do
    case "$word" in
    source=*) ;;
    type=bind,source=*)
        directory=${{word#type=bind,source=}}
        directory=${{directory%,target=*}}
        ls "$directory" >> "$log"
        ;;
    esac
done
case "$*" in
*" clang "*) {build} ;;
*) {start} ;;
esac
"""


def docker_stub(tmp_path, monkeypatch, build="exit 0", start="exit 0", removal=0):
    directory = tmp_path / "bin"
    directory.mkdir()
    log = tmp_path / "docker.log"
    stub = directory / "docker"
    stub.write_text(
        STUB.format(log=log, build=build, start=start, removal=removal),
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return log


def lines(log):
    return log.read_text(encoding="utf-8").splitlines()


def runs(log):
    return [line for line in lines(log) if line.startswith("run ")]


def after_the_image(line):
    return line.split(f" {IMAGE} ", 1)[1].split()


def holds_no_build_directory(log):
    for line in runs(log):
        for word in line.split():
            if word.startswith("type=bind,source="):
                assert not os.path.exists(
                    word.removeprefix("type=bind,source=").split(",")[0]
                )


@POSIX
def test_a_usable_image_gives_none_with_one_container_each(tmp_path, monkeypatch):
    log = docker_stub(tmp_path, monkeypatch)
    assert standin_openmp.check(IMAGE) is None
    build, start = runs(log)
    inside = standin_container.CONTAINER_BUILD_DIR
    assert after_the_image(build) == [
        "clang",
        *standin_settings.FLAGS,
        f"{inside}/{standin_openmp.SOURCE_NAME}",
        *standin_settings.TRAILING_FLAGS,
        "-o",
        f"{inside}/{standin_openmp.EXECUTABLE_NAME}",
    ]
    assert after_the_image(start) == [f"{inside}/{standin_openmp.EXECUTABLE_NAME}"]
    for line in (build, start):
        for option in (
            "--rm",
            "--network none",
            "--pull never",
            "--cap-drop ALL",
            "no-new-privileges=true",
            "--entrypoint=",
        ):
            assert option in line
    assert standin_openmp.SOURCE_NAME in lines(log)
    holds_no_build_directory(log)


@POSIX
@pytest.mark.parametrize(
    ("given", "answer", "containers"),
    [
        ({"build": "exit 1"}, "build ended with status 1", 1),
        ({"build": "exit 125"}, "build ended with status 125", 1),
        ({"start": "exit 1"}, "start ended with status 1", 2),
        ({"start": "exit 127"}, "start ended with status 127", 2),
    ],
)
def test_a_status_other_than_0_is_the_answer(
    tmp_path, monkeypatch, given, answer, containers
):
    log = docker_stub(tmp_path, monkeypatch, **given)
    assert standin_openmp.check(IMAGE) == answer
    assert len(runs(log)) == containers
    holds_no_build_directory(log)


@POSIX
@pytest.mark.parametrize("step", ["build", "start"])
def test_a_time_limit_ends_the_step_and_removes_the_container(
    tmp_path, monkeypatch, step
):
    log = docker_stub(tmp_path, monkeypatch, **{step: "exec sleep 30"})
    answer = standin_openmp.check(IMAGE, timeout_s=0.5, removal_timeout_s=10)
    assert answer == f"{step} did not finish within 0.5 s"
    removed = [line for line in lines(log) if line.startswith("rm ")]
    assert len(removed) == 1
    assert removed[0].split()[-1] in runs(log)[-1]
    holds_no_build_directory(log)


@POSIX
def test_a_removal_that_fails_is_told(tmp_path, monkeypatch):
    docker_stub(tmp_path, monkeypatch, build="exec sleep 30", removal=1)
    answer = standin_openmp.check(IMAGE, timeout_s=0.5, removal_timeout_s=10)
    assert answer.startswith("build did not finish within 0.5 s; the forced removal of")
    assert standin_container.NAME_PREFIX in answer
    assert answer.endswith("did not succeed")


@pytest.mark.parametrize(
    ("error", "answer"),
    [
        (local_run.ProgramNotFoundError("docker"), "ProgramNotFoundError"),
        (PermissionError("docker"), "PermissionError"),
        (standin_container.NoNumericUserError("none"), "NoNumericUserError"),
        (ValueError("build_dir"), "ValueError"),
    ],
)
def test_a_container_not_started_is_the_answer(monkeypatch, error, answer):
    def refused(*_, **__):
        raise error

    monkeypatch.setattr(standin_container, "run_in_container", refused)
    assert standin_openmp.check(IMAGE) == f"build could not be started ({answer})"


def test_a_failure_after_the_start_names_the_container(monkeypatch):
    def failed(*_, **__):
        error = OSError("read")
        error.container_name = "hilclaw-standin-x"
        raise error

    monkeypatch.setattr(standin_container, "run_in_container", failed)
    assert standin_openmp.check(IMAGE) == (
        "build failed after its start (OSError); hilclaw-standin-x may remain"
    )


def test_a_temporary_directory_that_fails_is_the_answer(monkeypatch):
    def refused(*_, **__):
        raise PermissionError("no")

    monkeypatch.setattr(standin_openmp.tempfile, "TemporaryDirectory", refused)
    assert standin_openmp.check(IMAGE) == (
        "the temporary directory failed (PermissionError)"
    )


def test_an_interrupt_is_passed_on(monkeypatch):
    def interrupted(*_, **__):
        raise KeyboardInterrupt

    monkeypatch.setattr(standin_container, "run_in_container", interrupted)
    with pytest.raises(KeyboardInterrupt):
        standin_openmp.check(IMAGE)


def test_the_message_says_what_is_needed_why_and_that_nothing_changed():
    text = standin_openmp.message("build ended with status 1")
    assert "HILCLAW_STANDIN_IMAGE" in text
    assert "build ended with status 1" in text
    assert "-fopenmp" in text
    assert "<omp.h>" in text
    assert "Nothing was installed or changed" in text
    assert "ADR-0188" in text


def test_the_message_holds_no_output_of_the_container(tmp_path, monkeypatch):
    if not hasattr(os, "getuid"):
        pytest.skip("needs a numeric user")
    docker_stub(tmp_path, monkeypatch, build="echo SECRET-OF-THE-IMAGE; exit 1")
    assert "SECRET" not in standin_openmp.message(standin_openmp.check(IMAGE))


def test_the_module_starts_no_install():
    source = standin_openmp.__file__
    with open(source, encoding="utf-8") as stream:
        text = stream.read()
    for word in ("apt-get", "brew ", "docker pull", "docker build", "--pull always"):
        assert word not in text


def test_the_probe_builds_and_runs_with_the_set(tmp_path):
    openmp_clang.need()
    source = tmp_path / standin_openmp.SOURCE_NAME
    source.write_bytes(standin_openmp.SOURCE)
    output = tmp_path / standin_openmp.EXECUTABLE_NAME
    subprocess.run(
        [
            shutil.which("clang"),
            *standin_settings.FLAGS,
            source,
            *standin_settings.TRAILING_FLAGS,
            "-o",
            output,
        ],
        check=True,
    )
    assert subprocess.run([output], check=False, timeout=60).returncode == 0


def test_the_probe_does_not_build_without_the_flag(tmp_path):
    openmp_clang.need()
    source = tmp_path / standin_openmp.SOURCE_NAME
    source.write_bytes(standin_openmp.SOURCE)
    done = subprocess.run(
        [
            shutil.which("clang"),
            *standin_settings.WAITER_FLAGS,
            source,
            "-o",
            tmp_path / "plain",
        ],
        capture_output=True,
        check=False,
    )
    assert done.returncode != 0


THREADS = """#include <omp.h>
#include <stdlib.h>
#include <unistd.h>
int main(void)
{
    size_t size = (size_t)16 * 1024 * 1024;
    char *block = malloc(size);
    int team = 0;
    if (block == NULL)
        return 1;
#pragma omp parallel
    {
#pragma omp for
        for (long i = 0; i < (long)size; i++)
            block[i] = 1;
#pragma omp master
        team = omp_get_num_threads();
    }
    return team >= 1 && write(1, "threaded\\n", 9) == 9 && block[size - 1] == 1 ? 0 : 1;
}
"""
NAMESPACE = ("--user", "--pid", "--fork", "--mount-proc", "--kill-child")


def working_unshare():
    path = shutil.which("unshare")
    if path is not None:
        done = subprocess.run(
            [path, *NAMESPACE, "/bin/sh", "-c", 'test "$$" -eq 1'],
            capture_output=True,
            check=False,
            timeout=60,
        )
        if done.returncode == 0:
            return path
    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.fail("no new user and PID namespace on the CI runner")
    pytest.skip("no new user and PID namespace can be made")


def test_the_waiter_built_without_openmp_keeps_its_line_for_a_child_with_threads(
    tmp_path,
):
    openmp_clang.need()
    unshare = working_unshare()
    source = tmp_path / "threads.c"
    source.write_text(THREADS, encoding="utf-8")
    child = tmp_path / "threads"
    built = clang_build.build(
        source,
        child,
        timeout_s=120,
        flags=standin_settings.FLAGS,
        trailing_flags=standin_settings.TRAILING_FLAGS,
    )
    assert built.ok, built.log
    waiter = tmp_path / "waiter"
    built = clang_build.build(
        standin_run.WAITER_SOURCE,
        waiter,
        timeout_s=120,
        flags=standin_settings.WAITER_FLAGS,
    )
    assert built.ok, built.log
    run = subprocess.run(
        [unshare, *NAMESPACE, waiter, child],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert run.returncode == 0, run.stderr
    read = standin_waiter_line.read(run.stdout)
    assert read.report == b"threaded\n"
    assert read.memory_bytes >= 16 * 1024 * 1024
    assert b"libomp" not in waiter.read_bytes()
    assert b"libomp" in child.read_bytes()
