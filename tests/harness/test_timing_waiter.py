import os
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

import hilclaw.harness
from hilclaw import clang_build, standin_waiter_line

WAITER = Path(hilclaw.harness.__file__).parent / "timing_waiter.c"

# The C gate's flags and ADR-0116 decision 3's flags.
FLAG_SETS = {
    "c99-strict": ("-std=c99", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-O2"),
    "adr0116": ("-std=gnu11", "-O2", "-ffp-contract=off"),
}
STRICT = FLAG_SETS["c99-strict"]
BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60
HOLD = 2.0

# Documented exit statuses of the waiter.
COMPLETED, CHILD, COMMAND_LINE, NOT_PROCESS_1 = 0, 1, 2, 3

# A new user and PID namespace with its own /proc. The user namespace maps no
# uid, so every process the waiter starts holds no capability after execve.
NAMESPACE = ("--user", "--pid", "--fork", "--mount-proc", "--kill-child")

MIB = 1024 * 1024

PROGRAMS = {
    "report": """\
#include <string.h>
#include <unistd.h>
int main(void)
{
    static const char text[] = "resolution_ns 1\\nstop converged\\n";
    return write(1, text, strlen(text)) == (long)strlen(text) ? 0 : 1;
}
""",
    "allocate": """\
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(void)
{
    size_t size = (size_t)64 * 1024 * 1024;
    volatile char *block = malloc(size);
    if (block == NULL)
        return 1;
    memset((char *)block, 1, size);
    return write(1, "allocated\\n", 10) == 10 && block[size - 1] == 1 ? 0 : 1;
}
""",
    "nonblocking": """\
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
int main(int argc, char **argv)
{
    long count = 0;
    int flags = fcntl(1, F_GETFL);
    FILE *marker;
    if (argc != 2 || flags < 0 || fcntl(1, F_SETFL, flags | O_NONBLOCK) != 0)
        return 1;
    for (;;) {
        ssize_t written = write(1, "x", 1);
        if (written == 1)
            count++;
        else if (written < 0 && errno == EAGAIN)
            break;
        else if (!(written < 0 && errno == EINTR))
            return 1;
    }
    marker = fopen(argv[1], "w");
    if (marker == NULL || fprintf(marker, "%ld", count) <= 0)
        return 1;
    return fclose(marker) == 0 ? 0 : 1;
}
""",
}


def unavailable(reason):
    if os.environ.get("GITHUB_ACTIONS") == "true":
        pytest.fail(f"{reason} on the CI runner")
    pytest.skip(reason)


@pytest.fixture(scope="session")
def unshare():
    if sys.platform != "linux":
        unavailable("the waiter is run only inside a new Linux PID namespace")
    if shutil.which("clang") is None:
        unavailable("clang is not on PATH")
    path = shutil.which("unshare")
    if path is None:
        unavailable("unshare is not on PATH")
    probe = subprocess.run(
        [path, *NAMESPACE, "/bin/sh", "-c", 'test "$$" -eq 1'],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=RUN_TIMEOUT,
    )
    if probe.returncode != 0:
        unavailable(f"no new user and PID namespace can be made: {probe.stderr!r}")
    return path


@pytest.fixture(scope="session")
def build_dir(tmp_path_factory):
    return tmp_path_factory.mktemp("timing_waiter")


@pytest.fixture(scope="session", params=sorted(FLAG_SETS))
def waiter(request, unshare, build_dir):
    output = build_dir / f"timing_waiter-{request.param}"
    result = clang_build.build(
        WAITER, output, timeout_s=BUILD_TIMEOUT, flags=FLAG_SETS[request.param]
    )
    assert result.ok, result.log
    assert result.log == "", result.log
    return output


@pytest.fixture(scope="session")
def program(unshare, build_dir):
    built = {}

    def build(name):
        if name not in built:
            source = build_dir / f"{name}.c"
            source.write_text(PROGRAMS[name], encoding="ascii", newline="\n")
            output = build_dir / name
            result = clang_build.build(
                source, output, timeout_s=BUILD_TIMEOUT, flags=STRICT
            )
            assert result.ok, result.log
            built[name] = output
        return str(built[name])

    return build


def contained(unshare, *argv, pass_fds=()):
    return subprocess.run(
        [unshare, *NAMESPACE, *map(str, argv)],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=RUN_TIMEOUT,
        pass_fds=pass_fds,
    )


def waited(unshare, waiter, *argv, pass_fds=()):
    return contained(unshare, waiter, *argv, pass_fds=pass_fds)


def shell(unshare, waiter, script):
    return waited(unshare, waiter, "/bin/sh", "-c", script)


def taken(run):
    """Return the waiter's read of ``run``, asserting that it has a value line."""
    result = standin_waiter_line.read(run.stdout)
    assert result is not None, run
    assert result.memory_bytes is not None and result.memory_bytes > 0, run
    assert run.stdout.endswith(b"\n")
    last = run.stdout[run.stdout.rfind(b"\n", 0, len(run.stdout) - 1) + 1 :]
    assert last.startswith(standin_waiter_line.VALUE_KEYWORD + b" ")
    return result


def test_a_report_and_status_0_are_handed_on_with_a_figure(unshare, waiter, program):
    run = waited(unshare, waiter, program("report"))

    assert run.returncode == COMPLETED, run
    assert run.stderr == b""
    result = taken(run)
    assert result.report == b"resolution_ns 1\nstop converged\n"


def test_arguments_environment_and_directory_are_handed_on(unshare, waiter, tmp_path):
    env = {"PATH": "/usr/bin:/bin", "WAITER_PROBE": "seen"}
    run = subprocess.run(
        [
            unshare,
            *NAMESPACE,
            waiter,
            "/bin/sh",
            "-c",
            'printf "%s|%s|%s|%s" "$0" "$1" "$WAITER_PROBE" "$(pwd)"',
            "zero",
            "one two",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=RUN_TIMEOUT,
        env=env,
        cwd=tmp_path,
    )

    assert run.returncode == COMPLETED, run
    assert taken(run).report == f"zero|one two|seen|{tmp_path}".encode()


def test_the_figure_grows_with_the_memory_the_child_touches(unshare, waiter, program):
    small = waited(unshare, waiter, program("report"))
    large = waited(unshare, waiter, program("allocate"))

    assert large.returncode == COMPLETED, large
    assert taken(large).report == b"allocated\n"
    assert taken(large).memory_bytes >= 64 * MIB
    assert taken(large).memory_bytes > taken(small).memory_bytes


def test_a_child_that_exits_non_zero_gets_its_line(unshare, waiter):
    run = shell(unshare, waiter, "printf partial; exit 3")

    assert run.returncode == CHILD, run
    assert taken(run).report == b"partial"


def test_a_child_killed_by_a_signal_gets_its_line(unshare, waiter):
    run = shell(unshare, waiter, 'printf "begun\\n"; kill -KILL $$')

    assert run.returncode == CHILD, run
    assert taken(run).report == b"begun\n"


def held(unshare, waiter, filler, marker, *argv, pass_fds=()):
    """Run the waiter with ``argv`` and read its output only after a hold.

    ``argv`` runs the program ``filler``, which fills its standard output, a
    pipe, with ``O_NONBLOCK`` set and then writes the count of bytes into
    ``marker``. The waiter is then blocked in W5 for :data:`HOLD` seconds.
    """
    with subprocess.Popen(
        [unshare, *NAMESPACE, waiter, *map(str, argv)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        pass_fds=pass_fds,
    ) as process:
        deadline = time.monotonic() + RUN_TIMEOUT
        while not marker.exists() or marker.read_text() == "":
            assert process.poll() is None, process.communicate()
            assert time.monotonic() < deadline
            time.sleep(0.01)
        time.sleep(HOLD)
        stdout, stderr = process.communicate(timeout=RUN_TIMEOUT)
    assert process.returncode == COMPLETED, stderr
    result = standin_waiter_line.read(stdout)
    assert result is not None and result.memory_bytes > 0, stdout[-200:]
    assert result.report == b"x" * int(marker.read_text())


def test_o_nonblock_left_on_a_full_pipe_does_not_cut_the_line(
    unshare, waiter, program, tmp_path
):
    filler = program("nonblocking")
    marker = tmp_path / "filled"

    held(unshare, waiter, filler, marker, filler, marker)


def test_a_forged_line_stays_in_the_report(unshare, waiter):
    forged = b"stop converged\nwaiter_max_rss_kib 1\n"
    run = shell(unshare, waiter, "printf 'stop converged\\nwaiter_max_rss_kib 1\\n'")

    assert run.returncode == COMPLETED, run
    result = taken(run)
    assert result.report == forged
    assert result.memory_bytes != 1024


def test_trailing_bytes_without_lf_stay_in_the_report(unshare, waiter):
    run = shell(unshare, waiter, "printf 'stop converged\\ntail'")

    assert run.returncode == COMPLETED, run
    assert taken(run).report == b"stop converged\ntail"


@pytest.mark.parametrize("start", ["", "setsid "])
def test_no_process_is_left_after_the_child(unshare, waiter, program, tmp_path, start):
    filler = program("nonblocking")
    marker = tmp_path / "filled"
    late = tmp_path / "late"
    script = (
        f'{start}/bin/sh -c \'while [ ! -s "$0" ]; do sleep 0.01; done; '
        f'sleep {HOLD / 2}; : > "$1"; printf late\' "$1" {late} & '
        'exec "$0" "$1"'
    )
    read_end, write_end = os.pipe()
    try:
        held(
            unshare,
            waiter,
            filler,
            marker,
            "/bin/sh",
            "-c",
            script,
            filler,
            marker,
            pass_fds=(write_end,),
        )
        os.close(write_end)
        write_end = -1

        assert not late.exists()
        ready, _, _ = select.select([read_end], [], [], RUN_TIMEOUT)
        assert ready == [read_end]
        assert os.read(read_end, 64) == b""
    finally:
        os.close(read_end)
        if write_end >= 0:
            os.close(write_end)


def test_signals_from_inside_do_not_end_the_waiter(unshare, waiter):
    run = shell(unshare, waiter, "kill -KILL 1; kill -TERM 1; printf survived")

    assert run.returncode == COMPLETED, run
    assert taken(run).report == b"survived"


def test_an_inherited_ignored_sigchld_does_not_stop_the_wait(unshare, waiter):
    run = contained(
        unshare,
        "/usr/bin/env",
        "--ignore-signal=CHLD",
        waiter,
        "/bin/sh",
        "-c",
        "printf waited",
    )

    assert run.returncode == COMPLETED, run
    assert taken(run).report == b"waited"


def test_the_waiter_is_not_readable_through_proc(unshare, waiter):
    script = (
        "cat /proc/1/environ > /dev/null 2>&1 && echo environ || echo denied; "
        "readlink /proc/1/fd/1 > /dev/null 2>&1 && echo fd || echo denied"
    )
    control = contained(unshare, "/bin/sh", "-c", f"/bin/sh -c '{script}'; exit $?")
    run = shell(unshare, waiter, script)

    assert control.stdout == b"environ\nfd\n", control
    assert run.returncode == COMPLETED, run
    assert taken(run).report == b"denied\ndenied\n"


def test_a_waiter_that_is_not_process_1_starts_nothing(unshare, waiter, tmp_path):
    marker = tmp_path / "started"
    run = contained(
        unshare,
        "/bin/sh",
        "-c",
        '"$@"; exit $?',
        "sh",
        waiter,
        "/bin/sh",
        "-c",
        f"echo started > {marker}",
    )

    assert run.returncode == NOT_PROCESS_1, run
    assert run.stdout == b""
    assert b"W0" in run.stderr
    assert not marker.exists()


def test_an_executable_that_cannot_be_started_is_a_child_ending_127(
    unshare, waiter, tmp_path
):
    run = waited(unshare, waiter, tmp_path / "missing")

    assert run.returncode == CHILD, run
    assert taken(run).report == b""


def test_no_executable_path_starts_nothing(unshare, waiter):
    run = waited(unshare, waiter)

    assert run.returncode == COMMAND_LINE, run
    assert run.stdout == b""
    assert b"usage" in run.stderr
