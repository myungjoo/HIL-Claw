import gc
import json
import os
import pickle
import signal
import subprocess
import sys
import time
import traceback
import warnings
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
windows_only = pytest.mark.skipif(os.name != "nt", reason="native Windows behaviour")
MIB = 1 << 20
PID = "out.write(str(os.getpid()).encode()); out.flush()"
HANG = PID + "; os.close(1); os.close(2); time.sleep(30)"
CLOSED = "os.close(1); os.close(2); time.sleep(1); os._exit(0)"
NOTED = "Path(__file__).with_name('pid').write_text(str(os.getpid()))"
LOUD = "out.write(b'o' * (2 << 20)); err.write(b'e' * (2 << 20))"


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
        "max_rss",
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


def allocating(size):
    return f"b = bytearray({size})\nfor i in range(0, {size}, 4096):\n    b[i] = 1"


def without_wait4(monkeypatch):
    if hasattr(os, "wait4"):
        monkeypatch.delattr(os, "wait4")


def assert_reaped(pid):
    with pytest.raises(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)


def test_a_result_built_with_six_values_has_no_usage():
    result = RunResult(0, False, b"", b"", ("x",), 0.0)
    assert result.max_rss is None
    assert result._replace(stdout=b"y").max_rss is None


@posix_only
def test_a_quiet_process_hands_on_a_positive_usage(child):
    result = run(child(QUIET), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert type(result.max_rss) is int
    assert result.max_rss > 0


@posix_only
def test_a_process_that_touches_more_memory_reports_a_larger_usage(child):
    import resource

    linux = sys.platform.startswith("linux")
    own_peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    size = 64 * MIB + own_peak * (1024 if linux else 1)
    quiet = run(child(QUIET), timeout_s=TIMEOUT)
    touched = run(child(allocating(size)), timeout_s=TIMEOUT)
    assert touched.returncode == 0
    assert type(touched.max_rss) is int
    assert touched.max_rss > quiet.max_rss
    if linux:
        assert touched.max_rss >= size // 1024


@posix_only
@pytest.mark.parametrize(
    "body, returncode, stdout, timeout_s",
    [
        (FAIL, 3, b"partial result", TIMEOUT),
        (SIGNAL, -getattr(signal, "SIGKILL", 9), b"last words", TIMEOUT),
        (SLEEP, None, b"before", 3),
    ],
)
def test_the_usage_is_handed_on_for_a_broken_run(
    body, returncode, stdout, timeout_s, child
):
    result = run(child(body), timeout_s=timeout_s)
    assert result.returncode == returncode
    assert result.timed_out is (returncode is None)
    assert result.stdout == stdout
    assert type(result.max_rss) is int
    assert result.max_rss > 0


@posix_only
def test_the_wait_goes_through_wait4_for_the_started_process(child, monkeypatch):
    real, calls = os.wait4, []

    def watched(pid, options):
        calls.append(pid)
        return real(pid, options)

    monkeypatch.setattr(os, "wait4", watched)
    result = run(child(PID), timeout_s=TIMEOUT)
    assert calls
    assert set(calls) == {int(result.stdout)}
    assert type(result.max_rss) is int


@posix_only
def test_a_process_that_closes_its_output_and_runs_on_is_waited_for(child):
    result = run(child(CLOSED), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.duration_s >= 1
    assert type(result.max_rss) is int


@posix_only
def test_a_process_that_closes_its_output_and_hangs_times_out(child):
    result = run(child(HANG), timeout_s=3)
    assert result.timed_out is True
    assert result.returncode is None
    assert result.stdout.isdigit()
    assert 3 <= result.duration_s < 20
    assert type(result.max_rss) is int
    assert_reaped(int(result.stdout))


@pytest.mark.parametrize("body", [QUIET, BOTH, FAIL, BAD_UTF8])
def test_without_wait4_the_usage_is_none_and_the_rest_is_kept(body, child, monkeypatch):
    with_platform_wait = run(child(body, "x"), timeout_s=TIMEOUT)
    without_wait4(monkeypatch)
    result = run(child(body, "x"), timeout_s=TIMEOUT)
    assert result.max_rss is None
    assert result[:5] == with_platform_wait[:5]
    assert 0 <= result.duration_s < TIMEOUT


def test_without_wait4_a_timeout_is_kept(child, monkeypatch):
    without_wait4(monkeypatch)
    result = run(child(SLEEP), timeout_s=3)
    assert result.timed_out is True
    assert result.returncode is None
    assert (result.stdout, result.stderr) == (b"before", b"sleep")
    assert result.max_rss is None


@windows_only
def test_native_windows_hands_on_no_usage(child):
    result = run(child(BOTH), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert result.stdout == b"to stdout\n"
    assert result.max_rss is None


@pytest.mark.parametrize("platform_wait", [True, False])
def test_a_large_output_on_both_streams_does_not_deadlock(
    platform_wait, child, monkeypatch
):
    if not platform_wait:
        without_wait4(monkeypatch)
    result = run(child(LOUD), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert result.stdout == b"o" * (2 * MIB)
    assert result.stderr == b"e" * (2 * MIB)


@pytest.mark.parametrize("platform_wait", [True, False])
def test_a_timeout_too_long_for_the_platform_is_an_overflow_error(
    platform_wait, child, monkeypatch
):
    if not platform_wait:
        without_wait4(monkeypatch)
    with pytest.raises(OverflowError):
        run(child(QUIET), timeout_s=1e300)


@pytest.mark.parametrize("platform_wait", [True, False])
@pytest.mark.parametrize("body", [QUIET, LOUD, SLEEP])
def test_no_resource_warning_is_left_behind(body, platform_wait, child, monkeypatch):
    if not platform_wait:
        without_wait4(monkeypatch)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        run(child(body), timeout_s=3)
        gc.collect()
    assert not [w for w in caught if issubclass(w.category, ResourceWarning)]


@posix_only
@pytest.mark.parametrize("body, timeout_s", [(PID, TIMEOUT), (HANG, 3)])
def test_the_process_is_reaped(body, timeout_s, child):
    result = run(child(body), timeout_s=timeout_s)
    assert_reaped(int(result.stdout))


@posix_only
def test_a_process_reaped_by_someone_else_gives_no_usage(child, monkeypatch):
    def reaped_elsewhere(pid, options):
        os.waitpid(pid, 0)
        raise ChildProcessError(10, "No child processes")

    monkeypatch.setattr(os, "wait4", reaped_elsewhere)
    result = run(child(PID), timeout_s=TIMEOUT)
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.max_rss is None
    assert_reaped(int(result.stdout))


@posix_only
def test_a_process_reaped_by_someone_else_after_the_kill_gives_no_usage(
    child, monkeypatch
):
    real = os.wait4

    def reaped_after_the_kill(pid, options):
        if options == os.WNOHANG:
            return real(pid, options)
        os.waitpid(pid, 0)
        raise ChildProcessError(10, "No child processes")

    monkeypatch.setattr(os, "wait4", reaped_after_the_kill)
    result = run(child(HANG), timeout_s=3)
    assert result.timed_out is True
    assert result.returncode is None
    assert result.max_rss is None
    assert_reaped(int(result.stdout))


@posix_only
def test_a_process_gone_before_the_kill_gives_no_usage(child, monkeypatch):
    real_kill = os.kill

    def gone(pid, sig):
        real_kill(pid, sig)
        os.waitpid(pid, 0)
        raise ProcessLookupError(3, "No such process")

    monkeypatch.setattr(os, "kill", gone)
    result = run(child(HANG), timeout_s=3)
    assert result.timed_out is True
    assert result.returncode is None
    assert result.max_rss is None
    assert_reaped(int(result.stdout))


@posix_only
def test_an_interrupted_wait_kills_and_reaps_the_process(child, monkeypatch):
    def interrupted(pid, options):
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "wait4", interrupted)
    before = time.monotonic()
    with pytest.raises(KeyboardInterrupt):
        run(child(NOTED + "; " + HANG), timeout_s=TIMEOUT)
    assert time.monotonic() - before < 20
    assert_reaped(int((child.directory / "pid").read_text()))


@posix_only
def test_a_descendant_holding_a_pipe_makes_a_timeout_at_the_limit(child):
    body = (
        "import subprocess\n"
        "kept = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
        "Path(__file__).with_name('pid').write_text(str(kept.pid))"
    )
    try:
        result = run(child(body), timeout_s=3)
    finally:
        noted = child.directory / "pid"
        if noted.exists():
            os.kill(int(noted.read_text()), signal.SIGKILL)
    assert result.timed_out is True
    assert result.returncode is None
    assert 3 <= result.duration_s < 20
    assert type(result.max_rss) is int


def raised(command, **settings):
    settings.setdefault("timeout_s", TIMEOUT)
    with pytest.raises(BaseException) as caught:
        run(command, **settings)
    return caught.value


@pytest.mark.parametrize(
    "value, kind",
    [(v, TypeError) for v in BAD_TIMEOUT_TYPES]
    + [(v, ValueError) for v in BAD_TIMEOUT_VALUES],
)
def test_a_refused_time_limit_names_timeout_s(value, kind, child):
    error = raised(child(QUIET), timeout_s=value)
    assert type(error) is kind
    assert error.parameter == "timeout_s"
    assert not child.started


@pytest.mark.parametrize("command", [[], ()])
def test_an_empty_command_names_command(command):
    error = raised(command)
    assert type(error) is ValueError
    assert error.parameter == "command"
    assert str(error) == "command is empty"


@pytest.mark.parametrize("as_type", [str, os.fsencode])
def test_a_command_as_one_string_names_command(as_type, child):
    error = raised(as_type(" ".join(child(QUIET))))
    assert type(error) is TypeError
    assert error.parameter == "command"
    assert not child.started


@pytest.mark.parametrize(
    "as_type", [os.fsencode, BytesPath, lambda _: 3, lambda _: None]
)
def test_a_program_of_the_wrong_type_names_command(as_type, child):
    command = child(QUIET)
    error = raised((as_type(command[0]), *command[1:]))
    assert type(error) is TypeError
    assert error.parameter == "command"
    assert "program" in str(error)
    assert not child.started


@pytest.mark.parametrize("argument", [3, None, b"x", Path("x"), ("x",)])
def test_an_argument_that_is_not_a_str_names_command(argument, child):
    error = raised(child(QUIET, "ok") + (argument,))
    assert type(error) is TypeError
    assert error.parameter == "command"
    assert "argument must be str" in str(error)
    assert not child.started


def test_the_type_error_of_a_command_that_is_not_iterable_names_command():
    with pytest.raises(TypeError) as direct:
        tuple(5)
    error = raised(5)
    assert type(error) is TypeError
    assert error.parameter == "command"
    assert error.args == direct.value.args


class Broken:
    def __init__(self, error):
        self.error = error

    def __iter__(self):
        return self

    def __next__(self):
        raise self.error


def test_an_error_of_the_command_iteration_is_passed_on_as_the_same_object():
    cause, context = KeyError("cause"), LookupError("context")
    given = ValueError("broken iteration")
    given.__cause__, given.__context__ = cause, context
    error = raised(Broken(given))
    assert error is given
    assert error.parameter == "command"
    assert error.args == ("broken iteration",)
    assert error.__cause__ is cause
    assert error.__context__ is context
    frames = [frame.name for frame in traceback.extract_tb(error.__traceback__)]
    assert frames[-1] == "__next__"


class IntPath:
    def __fspath__(self):
        return 3


def test_the_type_error_of_fspath_names_command(child):
    with pytest.raises(TypeError) as direct:
        os.fspath(IntPath())
    error = raised((IntPath(), *child(QUIET)[1:]))
    assert type(error) is TypeError
    assert error.parameter == "command"
    assert error.args == direct.value.args
    assert not child.started


def test_the_time_limit_is_named_before_the_command():
    error = raised([], timeout_s=0)
    assert type(error) is ValueError
    assert error.parameter == "timeout_s"


def test_a_missing_time_limit_names_no_parameter(child):
    with pytest.raises(TypeError) as caught:
        run(child(QUIET))
    assert not hasattr(caught.value, "parameter")
    assert not child.started


@pytest.mark.parametrize("program", MISSING_PROGRAMS)
def test_a_program_not_found_names_no_parameter(program, child):
    error = raised((program, child(QUIET)[1]))
    assert type(error) is ProgramNotFoundError
    assert not hasattr(error, "parameter")
    assert not child.started


def test_a_missing_cwd_names_no_parameter(child, tmp_path):
    error = raised(child(QUIET), cwd=tmp_path / "absent")
    assert isinstance(error, OSError)
    assert not hasattr(error, "parameter")
    assert not child.started


def refusing(error):
    def refuse(*arguments, **keywords):
        raise error

    return refuse


@pytest.mark.parametrize("kind", [ValueError, TypeError])
@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_error_of_subprocess_names_no_parameter(
    kind, platform_wait, child, monkeypatch
):
    given = kind("refused by subprocess")
    if platform_wait:
        monkeypatch.setattr(os, "wait4", refusing(AssertionError), raising=False)
        monkeypatch.setattr(subprocess, "Popen", refusing(given))
    else:
        without_wait4(monkeypatch)
        monkeypatch.setattr(subprocess, "run", refusing(given))
    error = raised(child(QUIET))
    assert error is given
    assert not hasattr(error, "parameter")
    assert not child.started


REFUSED_ENVS = [
    ({"A=B": "x"}, ValueError),
    ({"AB=": "x"}, ValueError),
    ({"A\0": "x"}, ValueError),
    ({"A": "x\0"}, ValueError),
    ({"\0": ""}, ValueError),
    ({"A": 3}, TypeError),
    ({3: "x"}, TypeError),
    ({"A": None}, TypeError),
    ({"A": bytearray(b"x")}, TypeError),
]
REFUSED_POSIX_ENVS = [
    ({b"A=B": b"x"}, ValueError),
    ({b"A\0": b"x"}, ValueError),
    ({"A": b"x\0"}, ValueError),
    ({"A": Path("x\0")}, ValueError),
    ({"A": IntPath()}, TypeError),
]
REFUSED_WINDOWS_ENVS = [
    ({b"A": b"x"}, TypeError),
    ({"A": b"x"}, TypeError),
    ({"A": Path("x")}, TypeError),
]
REFUSED = (
    REFUSED_ENVS
    + [pytest.param(*case, marks=posix_only) for case in REFUSED_POSIX_ENVS]
    + [pytest.param(*case, marks=windows_only) for case in REFUSED_WINDOWS_ENVS]
)


PASSED_ON = (AttributeError, OSError, TypeError, ValueError)


def wait_path(platform_wait, monkeypatch):
    if not platform_wait:
        without_wait4(monkeypatch)


def directly(command, cwd, env):
    try:
        subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            cwd=cwd,
            env=env,
            check=False,
        )
    except PASSED_ON as error:
        return type(error)
    return None


@pytest.mark.parametrize("variable, kind", REFUSED)
@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_env_that_subprocess_refuses_names_env(
    variable, kind, platform_wait, child, monkeypatch
):
    wait_path(platform_wait, monkeypatch)
    error = raised(child(QUIET), env={**os.environ, **variable})
    assert type(error) is kind
    assert error.parameter == "env"
    assert not child.started
    assert isinstance(run(child(QUIET), timeout_s=TIMEOUT), RunResult)


@pytest.mark.parametrize("variable, kind", REFUSED)
@pytest.mark.parametrize("in_cwd", [False, True])
def test_a_refused_env_has_the_class_subprocess_raises(
    variable, kind, in_cwd, child, tmp_path
):
    cwd = tmp_path if in_cwd else None
    assert directly(child(QUIET), cwd, {**os.environ, **variable}) is kind
    assert not child.started


@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_env_error_message_names_the_key_and_not_the_value(
    platform_wait, child, monkeypatch
):
    wait_path(platform_wait, monkeypatch)
    error = raised(child(QUIET), env={**os.environ, "HILCLAW_K": "secret\0"})
    assert "HILCLAW_K" in str(error)
    assert "secret" not in str(error)


@pytest.mark.parametrize("platform_wait", [True, False])
def test_a_nul_in_an_argument_names_command(platform_wait, child, monkeypatch):
    wait_path(platform_wait, monkeypatch)
    error = raised(child(QUIET, "ok", "x\0y"))
    assert type(error) is ValueError
    assert error.parameter == "command"
    assert str(error) == "an argument contains a NUL character"
    assert not child.started


def test_a_nul_in_an_argument_has_the_class_subprocess_raises(child):
    assert directly(child(QUIET, "x\0y"), None, None) is ValueError
    assert not child.started


def test_a_nul_in_an_argument_is_named_before_the_program_lookup():
    error = raised(("hilclaw-no-such-program", "x\0y"))
    assert type(error) is ValueError
    assert error.parameter == "command"


ACCEPTED_ENVS = [
    {"HILCLAW_TEST_MARK": "accepted"},
    pytest.param({b"HILCLAW_TEST_MARK": b"accepted"}, marks=posix_only),
    pytest.param({"HILCLAW_TEST_MARK": Path("accepted")}, marks=posix_only),
    pytest.param({"=A": "x", "HILCLAW_TEST_MARK": "accepted"}, marks=windows_only),
]


@pytest.mark.parametrize("variable", ACCEPTED_ENVS)
@pytest.mark.parametrize("in_cwd", [False, True])
@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_accepted_env_reaches_the_process(
    variable, in_cwd, platform_wait, child, monkeypatch, tmp_path
):
    monkeypatch.delenv("HILCLAW_TEST_MARK", raising=False)
    wait_path(platform_wait, monkeypatch)
    cwd = tmp_path if in_cwd else None
    result = run(
        child(QUIET), timeout_s=TIMEOUT, cwd=cwd, env={**os.environ, **variable}
    )
    assert result.returncode == 0
    assert child.call()["mark"] == "accepted"


@pytest.mark.parametrize("platform_wait", [True, False])
def test_no_env_inherits_after_the_check(platform_wait, child, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    wait_path(platform_wait, monkeypatch)
    result = run(child(QUIET), timeout_s=TIMEOUT, env=None)
    assert result.returncode == 0
    assert child.call()["mark"] == "inherited"


@pytest.mark.parametrize("platform_wait", [True, False])
def test_the_env_is_handed_on_as_given(platform_wait, child, monkeypatch):
    seen = []

    def record(*arguments, **keywords):
        seen.append(keywords["env"])
        raise LookupError("recorded")

    if platform_wait and hasattr(os, "wait4"):
        monkeypatch.setattr(subprocess, "Popen", record)
    else:
        without_wait4(monkeypatch)
        monkeypatch.setattr(subprocess, "run", record)
    env = {**os.environ, "HILCLAW_TEST_MARK": "given"}
    error = raised(child(QUIET), env=env)
    assert type(error) is LookupError
    assert seen == [env]
    assert seen[0] is env


UNCHANGED_ENVS = [
    {"": "x"},
    pytest.param({"=A": "x"}, marks=posix_only),
    pytest.param({b"=A": b"x"}, marks=posix_only),
    pytest.param({b"": b"x"}, marks=posix_only),
]


@pytest.mark.parametrize("variable", UNCHANGED_ENVS)
@pytest.mark.parametrize("in_cwd", [False, True])
@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_env_left_to_subprocess_names_no_parameter(
    variable, in_cwd, platform_wait, child, monkeypatch, tmp_path
):
    wait_path(platform_wait, monkeypatch)
    cwd = tmp_path if in_cwd else None
    env = {**os.environ, **variable}
    expected = directly(child(QUIET), cwd, env)
    try:
        run(child(QUIET), timeout_s=TIMEOUT, cwd=cwd, env=env)
    except PASSED_ON as error:
        assert type(error) is expected
        assert not hasattr(error, "parameter")
    else:
        assert expected is None


@pytest.mark.parametrize("env", [[("A", "x")], 5, "A=x"])
@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_env_that_is_not_a_mapping_keeps_its_class(
    env, platform_wait, child, monkeypatch
):
    wait_path(platform_wait, monkeypatch)
    expected = directly(child(QUIET), None, env)
    error = raised(child(QUIET), env=env)
    assert expected is not None
    assert type(error) is expected
    assert not hasattr(error, "parameter")
    assert not child.started


def test_a_list_env_still_raises_attribute_error(child):
    error = raised(child(QUIET), env=[("A", "x")])
    assert type(error) is AttributeError
    assert not hasattr(error, "parameter")


class Items(dict):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def items(self):
        raise self.error


def test_a_type_error_of_env_items_names_env(child):
    given = TypeError("items refused")
    error = raised(child(QUIET), env=Items(given))
    assert error is given
    assert error.parameter == "env"
    assert not child.started


@pytest.mark.parametrize("given", [RuntimeError("broken"), LookupError("gone")])
def test_another_error_of_env_items_is_passed_on(given, child):
    error = raised(child(QUIET), env=Items(given))
    assert error is given
    assert not hasattr(error, "parameter")
    assert not child.started


def test_the_time_limit_is_named_before_the_env(child):
    error = raised(child(QUIET), timeout_s=0, env={"A=B": "x"})
    assert type(error) is ValueError
    assert error.parameter == "timeout_s"


@pytest.mark.parametrize("command", [[], ("x", 3), ("x", "y\0")])
def test_the_command_is_named_before_the_env(command):
    error = raised(command, env={"A": 3})
    assert error.parameter == "command"


def test_a_missing_program_comes_before_the_env():
    error = raised(("hilclaw-no-such-program", "x"), env={"A=B": "x"})
    assert type(error) is ProgramNotFoundError
    assert not hasattr(error, "parameter")


@pytest.mark.parametrize("platform_wait", [True, False])
def test_an_overflow_error_names_no_parameter(platform_wait, child, monkeypatch):
    if not platform_wait:
        without_wait4(monkeypatch)
    error = raised(child(QUIET), timeout_s=1e300)
    assert type(error) is OverflowError
    assert not hasattr(error, "parameter")


@posix_only
def test_an_interrupted_wait_names_no_parameter(child, monkeypatch):
    monkeypatch.setattr(os, "wait4", refusing(KeyboardInterrupt))
    error = raised(child(NOTED + "; " + HANG))
    assert type(error) is KeyboardInterrupt
    assert not hasattr(error, "parameter")
    assert_reaped(int((child.directory / "pid").read_text()))


@pytest.mark.parametrize(
    "command, settings, kind",
    [
        (["x"], {"timeout_s": "10"}, TypeError),
        ([], {"timeout_s": TIMEOUT}, ValueError),
        ([sys.executable], {"env": {"A=B": "x"}}, ValueError),
        ([sys.executable], {"env": {"A": 3}}, TypeError),
    ],
)
def test_the_parameter_survives_pickling(command, settings, kind):
    error = raised(command, **settings)
    loaded = pickle.loads(pickle.dumps(error))
    assert type(loaded) is kind
    assert loaded.args == error.args
    assert loaded.parameter == error.parameter
