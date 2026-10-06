import json
import os
import signal
import sys
import time
from pathlib import Path

import pytest

from hilclaw.local_run import ProgramNotFoundError, RunResult, run

PRELUDE = """\
import json, os, signal, sys, time
from pathlib import Path
call = {
    "argv": sys.argv[1:],
    "cwd": os.getcwd(),
    "mark": os.environ.get("HILCLAW_TEST_MARK"),
    "stdin": sys.stdin.read(),
}
Path(__file__).with_name("started.json").write_text(json.dumps(call), encoding="utf-8")
out, err = sys.stdout.buffer, sys.stderr.buffer
"""
QUIET = "pass"
BOTH = "out.write(b'to stdout\\n'); err.write(b'to stderr\\n')"
FAIL = "out.write(b'partial result'); err.write(b'it broke'); sys.exit(3)"
BAD_UTF8 = "out.write(b'caf\\xe9 \\xff\\x00'); err.write(b'\\xfe\\r\\n')"
SLEEP = "out.write(b'before'); out.flush(); err.write(b'sleep'); err.flush(); time.sleep(30)"
SIGNAL = "out.write(b'last words'); out.flush(); os.kill(os.getpid(), signal.SIGKILL)"

BAD_TIMEOUT_VALUES = [0, -1, -0.5, 0.0, float("nan"), float("inf")]
BAD_TIMEOUT_TYPES = [None, True, False, "10", [1], 1 + 0j]
MISSING_PROGRAMS = [
    "hilclaw-no-such-program",
    Path("no-such-directory") / "program",
    "",
]
TIMEOUT = 60

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")


class Child:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(self, body, *arguments):
        script = self.directory / "child.py"
        script.write_text(PRELUDE + body + "\n", encoding="utf-8")
        return (sys.executable, str(script), *arguments)

    @property
    def started(self):
        return self.record.exists()

    def call(self):
        return json.loads(self.record.read_text(encoding="utf-8"))


@pytest.fixture
def child(tmp_path):
    directory = tmp_path / "child"
    directory.mkdir()
    return Child(directory)


def test_exit_zero_is_reported_with_the_command(child):
    command = child(QUIET, "first", "second")
    result = run(command, timeout_s=TIMEOUT)
    assert isinstance(result, RunResult)
    assert result.returncode == 0
    assert result.timed_out is False
    assert isinstance(result.duration_s, float)
    assert 0 <= result.duration_s < TIMEOUT
    assert isinstance(result.command, tuple)
    assert os.path.isabs(result.command[0])
    assert os.path.samefile(result.command[0], sys.executable)
    assert result.command[1:] == command[1:]
    assert child.call()["argv"] == ["first", "second"]


def test_result_fields():
    assert RunResult._fields == (
        "returncode",
        "timed_out",
        "stdout",
        "stderr",
        "command",
        "duration_s",
    )


def test_stdout_and_stderr_are_kept_apart_as_bytes(child):
    result = run(child(BOTH), timeout_s=TIMEOUT)
    assert result.stdout == b"to stdout\n"
    assert result.stderr == b"to stderr\n"


def test_no_output_gives_empty_bytes(child):
    result = run(child(QUIET), timeout_s=TIMEOUT)
    assert (result.stdout, result.stderr) == (b"", b"")
    assert isinstance(result.stdout, bytes)
    assert isinstance(result.stderr, bytes)


def test_arguments_are_passed_through_unchanged(child):
    arguments = ["a b", "", "$HOME; echo x", '"quoted"', "-o", "café", "*"]
    result = run(child(QUIET, *arguments), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert child.call()["argv"] == arguments
    assert list(result.command[2:]) == arguments


def test_cwd_and_env_reach_the_process(child, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "marked"}
    result = run(child(QUIET), timeout_s=TIMEOUT, cwd=work, env=env)
    assert result.returncode == 0
    call = child.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "marked"


def test_cwd_and_environment_are_inherited_by_default(child, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    run(child(QUIET), timeout_s=TIMEOUT)
    call = child.call()
    assert call["mark"] == "inherited"
    assert os.path.samefile(call["cwd"], os.getcwd())


def test_env_replaces_the_environment(child, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    env = {k: v for k, v in os.environ.items() if k != "HILCLAW_TEST_MARK"}
    run(child(QUIET), timeout_s=TIMEOUT, env=env)
    assert child.call()["mark"] is None


def test_the_process_sees_end_of_file_on_standard_input(child):
    result = run(child(QUIET), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert child.call()["stdin"] == ""


def test_str_and_path_program_give_the_same_command(child):
    command = child(BOTH, "x")
    as_str = run(command, timeout_s=TIMEOUT)
    as_path = run((Path(command[0]), *command[1:]), timeout_s=TIMEOUT)
    assert as_path.command == as_str.command
    assert as_path[:4] == as_str[:4]


def test_list_and_tuple_command_give_the_same_result(child):
    command = child(BOTH, "x")
    as_tuple = run(tuple(command), timeout_s=TIMEOUT)
    as_list = run(list(command), timeout_s=TIMEOUT)
    assert as_list[:5] == as_tuple[:5]


def test_timeout_accepts_int_and_float(child):
    command = child(QUIET)
    assert run(command, timeout_s=60).returncode == 0
    assert run(command, timeout_s=60.5).returncode == 0


def test_relative_program_is_resolved_against_the_callers_directory(
    child, tmp_path, monkeypatch
):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(tmp_path)
    try:
        relative = os.path.relpath(sys.executable)
    except ValueError:
        pytest.skip("the interpreter is on another drive than the temporary directory")
    command = child(QUIET)
    result = run((relative, *command[1:]), timeout_s=TIMEOUT, cwd=work)
    assert result.returncode == 0
    assert os.path.isabs(result.command[0])
    assert os.path.samefile(result.command[0], sys.executable)
    assert os.path.samefile(child.call()["cwd"], work)


def test_non_zero_exit_is_a_result(child):
    result = run(child(FAIL), timeout_s=TIMEOUT)
    assert result.returncode == 3
    assert result.timed_out is False
    assert result.stdout == b"partial result"
    assert result.stderr == b"it broke"


def test_output_is_not_decoded(child):
    result = run(child(BAD_UTF8), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert result.stdout == b"caf\xe9 \xff\x00"
    assert result.stderr == b"\xfe\r\n"


def test_timeout_kills_the_process_and_keeps_the_output(child):
    before = time.monotonic()
    result = run(child(SLEEP), timeout_s=5)
    assert time.monotonic() - before < 20
    assert result.timed_out is True
    assert result.returncode is None
    assert result.stdout == b"before"
    assert result.stderr == b"sleep"
    assert 5 <= result.duration_s < 20
    assert child.started


@pytest.mark.parametrize(
    "body, stdout, stderr",
    [
        ("time.sleep(30)", b"", b""),
        ("out.write(b'only out'); out.flush(); time.sleep(30)", b"only out", b""),
        ("err.write(b'only err'); err.flush(); time.sleep(30)", b"", b"only err"),
    ],
)
def test_timeout_with_a_silent_stream_gives_empty_bytes(body, stdout, stderr, child):
    result = run(child(body), timeout_s=5)
    assert result.timed_out is True
    assert result.returncode is None
    assert (result.stdout, result.stderr) == (stdout, stderr)
    assert isinstance(result.stdout, bytes)
    assert isinstance(result.stderr, bytes)


@posix_only
def test_death_by_signal_is_a_negative_returncode(child):
    result = run(child(SIGNAL), timeout_s=TIMEOUT)
    assert result.returncode == -signal.SIGKILL
    assert result.timed_out is False
    assert result.stdout == b"last words"


def test_empty_command():
    with pytest.raises(ValueError, match="empty"):
        run([], timeout_s=TIMEOUT)
    with pytest.raises(ValueError, match="empty"):
        run((), timeout_s=TIMEOUT)


@pytest.mark.parametrize("as_type", [str, os.fsencode])
def test_command_as_one_string(as_type, child):
    line = as_type(" ".join(child(QUIET)))
    with pytest.raises(TypeError, match="sequence of arguments"):
        run(line, timeout_s=TIMEOUT)
    assert not child.started


def test_command_that_is_not_iterable():
    with pytest.raises(TypeError):
        run(5, timeout_s=TIMEOUT)


@pytest.mark.parametrize("argument", [3, None, b"x", Path("x"), ("x",)])
def test_argument_that_is_not_a_str(argument, child):
    with pytest.raises(TypeError, match="argument must be str"):
        run(child(QUIET, "ok") + (argument,), timeout_s=TIMEOUT)
    assert not child.started


class BytesPath:
    def __init__(self, path):
        self.path = path

    def __fspath__(self):
        return os.fsencode(self.path)


@pytest.mark.parametrize(
    "as_type", [os.fsencode, BytesPath, lambda _: 3, lambda _: None]
)
def test_program_of_the_wrong_type(as_type, child):
    command = child(QUIET)
    with pytest.raises(TypeError, match="program"):
        run((as_type(command[0]), *command[1:]), timeout_s=TIMEOUT)
    assert not child.started


@pytest.mark.parametrize("program", MISSING_PROGRAMS)
def test_program_that_does_not_exist(program, child):
    script = child(QUIET)[1]
    with pytest.raises(ProgramNotFoundError) as caught:
        run((program, script), timeout_s=TIMEOUT)
    assert repr(os.fspath(program)) in str(caught.value)
    assert isinstance(caught.value, LookupError)
    assert not child.started


@posix_only
def test_file_without_the_execute_bit_is_not_found(tmp_path):
    marker = tmp_path / "ran"
    program = tmp_path / "program"
    program.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
    program.chmod(0o644)
    with pytest.raises(ProgramNotFoundError, match="program"):
        run([program], timeout_s=TIMEOUT)
    assert not marker.exists()
    program.chmod(0o755)
    assert run([program], timeout_s=TIMEOUT).returncode == 0
    assert marker.exists()


@posix_only
def test_file_the_system_cannot_execute_passes_the_oserror_on(tmp_path):
    program = tmp_path / "program"
    program.write_bytes(b"\x00\x01\x02 not a program\n")
    program.chmod(0o755)
    with pytest.raises(OSError):
        run([program], timeout_s=TIMEOUT)


def test_missing_cwd_passes_the_oserror_on(child, tmp_path):
    with pytest.raises(OSError):
        run(child(QUIET), timeout_s=TIMEOUT, cwd=tmp_path / "absent")
    assert not child.started
    assert not (tmp_path / "absent").exists()


@pytest.mark.parametrize("value", BAD_TIMEOUT_VALUES)
def test_timeout_must_be_positive_and_finite(value, child):
    with pytest.raises(ValueError, match="timeout_s"):
        run(child(QUIET), timeout_s=value)
    assert not child.started


@pytest.mark.parametrize("value", BAD_TIMEOUT_TYPES)
def test_timeout_must_be_a_number(value, child):
    with pytest.raises(TypeError, match="timeout_s"):
        run(child(QUIET), timeout_s=value)
    assert not child.started


def test_timeout_has_no_default(child):
    with pytest.raises(TypeError):
        run(child(QUIET))
    assert not child.started
