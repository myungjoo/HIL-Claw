import errno
import json
import os
import pickle
import shutil
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from hilclaw import clang_build
from hilclaw.clang_build import (
    DEFAULT_COMPILER,
    ArtefactNotCheckedError,
    ArtefactNotPlacedError,
    BuildResult,
    CompilerNotFoundError,
    CompilerNotStartedError,
    CompilerRunError,
    TemporaryNotRemovedError,
    build,
    compiler_version,
)

GOOD_C = "double scale(double x) { return 2.0 * x; }\n"
MATH_C = "#include <math.h>\ndouble root(double x) { return sqrt(x); }\n"
BAD_C = "int broken( {\n"

PRELUDE = """\
import json, os, sys, time
from pathlib import Path
here = Path(__file__).parent
argv = sys.argv[1:]
call = {"argv": argv, "cwd": os.getcwd(), "mark": os.environ.get("HILCLAW_TEST_MARK")}
(here / "started.json").write_text(json.dumps(call), encoding="utf-8")
out = Path(argv[argv.index("-o") + 1]) if "-o" in argv else None
"""
WRITE = "out.write_bytes(b'artefact')"
FAIL = "out.write_bytes(b'partial'); print('kernel.c:1:1: error: stub says no'); sys.exit(1)"
SLEEP = "out.write_bytes(b'partial'); print('before sleep', flush=True); time.sleep(30)"
NOTHING = "pass"
BAD_UTF8 = "sys.stdout.buffer.write(b'caf\\xe9 \\xff\\n'); sys.exit(1)"
BOTH = "print('to stdout'); print('to stderr', file=sys.stderr); out.write_bytes(b'a')"
VERSION = "print('stub clang version 1.2.3 (test)  '); print('Target: nowhere')"

BAD_TIMEOUT_VALUES = [0, -1, -0.5, 0.0, float("nan"), float("inf")]
BAD_TIMEOUT_TYPES = [None, True, False, "10", [1], 1 + 0j]
OUTPUT_FLAGS = [("-o", "x.o"), ("-ox.o",), ("--output", "x.o"), ("--output=x.o",)]
MISSING_COMPILERS = [
    "hilclaw-no-such-compiler",
    Path("no-such-directory") / "clang",
    ("hilclaw-no-such-compiler", "clang"),
    "",
]
TIMEOUT = 60


class Stub:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.json"

    def __call__(self, body):
        script = self.directory / "cc.py"
        script.write_text(PRELUDE + body + "\n", encoding="utf-8")
        return (sys.executable, str(script))

    @property
    def started(self):
        return self.record.exists()

    def call(self):
        return json.loads(self.record.read_text(encoding="utf-8"))


@pytest.fixture
def stub(tmp_path):
    directory = tmp_path / "stub"
    directory.mkdir()
    return Stub(directory)


@pytest.fixture
def src(tmp_path):
    path = tmp_path / "src" / "kernel.c"
    path.parent.mkdir()
    path.write_text(GOOD_C, encoding="utf-8")
    return path


@pytest.fixture
def out_dir(tmp_path):
    path = tmp_path / "out"
    path.mkdir()
    return path


@pytest.fixture
def clang():
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def names(directory):
    return sorted(p.name for p in directory.iterdir())


def test_stub_build_succeeds_and_reports_the_call(stub, src, out_dir):
    out = out_dir / "kernel.o"
    result = build(src, out, timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert isinstance(result, BuildResult)
    assert result.ok is True
    assert result.returncode == 0
    assert result.timed_out is False
    assert result.output == out
    assert result.log == ""
    assert result.duration_s >= 0
    assert out.read_bytes() == b"artefact"
    assert names(out_dir) == ["kernel.o"]


def test_command_order_and_temporary_name(stub, src, out_dir, tmp_path):
    other = tmp_path / "src" / "other.c"
    other.write_text(GOOD_C, encoding="utf-8")
    compiler = stub(WRITE)
    result = build(
        [src, other],
        out_dir / "kernel.o",
        timeout_s=TIMEOUT,
        flags=["-DA=1", "-c"],
        trailing_flags=("-lm",),
        compiler=compiler,
    )
    command = result.command
    assert isinstance(command, tuple)
    assert os.path.samefile(command[0], sys.executable)
    assert os.path.isabs(command[0])
    assert command[1:-1] == (
        compiler[1],
        "-DA=1",
        "-c",
        str(src),
        str(other),
        "-lm",
        "-o",
    )
    temporary = Path(command[-1])
    assert temporary.parent == out_dir
    assert temporary.name.startswith("kernel.tmp-")
    assert temporary.suffix == ".o"
    assert stub.call()["argv"] == list(command[2:])
    assert result.ok


def test_temporary_name_without_suffix(stub, src, out_dir):
    result = build(src, out_dir / "kernel", timeout_s=TIMEOUT, compiler=stub(WRITE))
    temporary = Path(result.command[-1])
    assert temporary.name.startswith("kernel.tmp-")
    assert names(out_dir) == ["kernel"]


def test_cwd_and_env_reach_the_process(stub, src, out_dir, tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    env = {**os.environ, "HILCLAW_TEST_MARK": "marked"}
    result = build(
        src,
        out_dir / "kernel.o",
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
        cwd=work,
        env=env,
    )
    assert result.ok
    call = stub.call()
    assert os.path.samefile(call["cwd"], work)
    assert call["mark"] == "marked"


def test_environment_is_inherited_by_default(stub, src, out_dir, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    call = stub.call()
    assert call["mark"] == "inherited"
    assert os.path.samefile(call["cwd"], os.getcwd())


def test_relative_paths_do_not_depend_on_cwd(stub, src, out_dir, tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(tmp_path)
    relative = os.path.join("out", "kernel.o")
    result = build(
        os.path.join("src", "kernel.c"),
        relative,
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
        cwd=work,
    )
    assert result.ok
    assert result.output == Path(relative)
    assert (out_dir / "kernel.o").is_file()
    assert names(work) == []
    assert str(src) in result.command


def test_single_source_and_one_element_list_agree(stub, src, out_dir):
    compiler = stub(WRITE)
    single = build(src, out_dir / "a.o", timeout_s=TIMEOUT, compiler=compiler)
    listed = build([src], out_dir / "a.o", timeout_s=TIMEOUT, compiler=compiler)
    assert single.command[:-1] == listed.command[:-1]


def test_str_and_path_arguments_agree(stub, src, out_dir):
    compiler = stub(WRITE)
    out = out_dir / "a.o"
    as_path = build(src, out, timeout_s=TIMEOUT, compiler=compiler)
    as_str = build(str(src), str(out), timeout_s=TIMEOUT, compiler=compiler)
    assert as_str.command[:-1] == as_path.command[:-1]
    assert as_str[:4] == as_path[:4]
    assert isinstance(as_str.output, Path)


def test_timeout_accepts_int_and_float(stub, src, out_dir):
    compiler = stub(WRITE)
    assert build(src, out_dir / "a.o", timeout_s=60, compiler=compiler).ok
    assert build(src, out_dir / "a.o", timeout_s=60.5, compiler=compiler).ok


@pytest.mark.parametrize("how", ["default", "str", "path"])
def test_single_executable_forms_of_compiler(how, stub, out_dir, monkeypatch):
    script = stub(WRITE)[1]
    if how == "default":
        monkeypatch.setattr(
            clang_build.shutil,
            "which",
            lambda name: sys.executable if name == DEFAULT_COMPILER else None,
        )
        compiler = None
    else:
        compiler = sys.executable if how == "str" else Path(sys.executable)
    result = build(script, out_dir / "a.o", timeout_s=TIMEOUT, compiler=compiler)
    assert result.ok
    assert os.path.samefile(result.command[0], sys.executable)
    assert result.command[1:3] == (script, "-o")


def test_default_compiler_is_clang():
    assert DEFAULT_COMPILER == "clang"


def test_compile_error_is_a_result(stub, src, out_dir):
    out = out_dir / "kernel.o"
    result = build(src, out, timeout_s=TIMEOUT, compiler=stub(FAIL))
    assert result.ok is False
    assert result.returncode == 1
    assert result.timed_out is False
    assert "error: stub says no" in result.log
    assert result.output == out
    assert names(out_dir) == []


def test_existing_artefact_survives_failure_and_is_replaced_on_success(
    stub, src, out_dir
):
    out = out_dir / "kernel.o"
    out.write_bytes(b"previous")
    assert not build(src, out, timeout_s=TIMEOUT, compiler=stub(FAIL)).ok
    assert out.read_bytes() == b"previous"
    assert not build(src, out, timeout_s=TIMEOUT, compiler=stub(NOTHING)).ok
    assert out.read_bytes() == b"previous"
    assert build(src, out, timeout_s=TIMEOUT, compiler=stub(WRITE)).ok
    assert out.read_bytes() == b"artefact"
    assert names(out_dir) == ["kernel.o"]


def test_exit_zero_without_artefact_is_not_ok(stub, src, out_dir):
    result = build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(NOTHING))
    assert result.ok is False
    assert result.returncode == 0
    assert result.timed_out is False
    assert names(out_dir) == []


def test_timeout_kills_the_compiler(stub, src, out_dir):
    out = out_dir / "kernel.o"
    out.write_bytes(b"previous")
    before = time.monotonic()
    result = build(src, out, timeout_s=5, compiler=stub(SLEEP))
    assert time.monotonic() - before < 20
    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode is None
    assert "before sleep" in result.log
    assert 5 <= result.duration_s < 20
    assert stub.started
    assert out.read_bytes() == b"previous"
    assert names(out_dir) == ["kernel.o"]


def test_invalid_utf8_in_compiler_output(stub, src, out_dir):
    result = build(
        src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(BAD_UTF8)
    )
    assert isinstance(result.log, str)
    assert result.log.startswith("caf� �")
    assert result.ok is False


def test_stdout_and_stderr_are_both_in_the_log(stub, src, out_dir):
    result = build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(BOTH))
    assert result.ok
    assert "to stdout" in result.log
    assert "to stderr" in result.log


def test_stub_compiler_version_is_the_first_line(stub):
    assert compiler_version(stub(VERSION), timeout_s=TIMEOUT) == (
        "stub clang version 1.2.3 (test)"
    )
    assert stub.call()["argv"] == ["--version"]


LOGGED_WRITE = "print('stub warning: kept'); out.write_bytes(b'artefact')"
LOGGED_NOTHING = "print('stub warning: no artefact')"
FILE_ERRORS = (
    ArtefactNotPlacedError,
    TemporaryNotRemovedError,
    ArtefactNotCheckedError,
)


def is_temporary(path):
    return ".tmp-" in Path(path).name


@pytest.fixture
def failing_replace(monkeypatch):
    errors = []

    def replace(source, destination):
        error = PermissionError(13, "denied", str(source), None, str(destination))
        errors.append(error)
        raise error

    monkeypatch.setattr(clang_build.os, "replace", replace)
    return errors


@pytest.fixture
def failing_unlink(monkeypatch):
    errors = []
    unlink = Path.unlink

    def fake(self, missing_ok=False):
        if not is_temporary(self):
            return unlink(self, missing_ok=missing_ok)
        error = PermissionError(13, "busy", str(self))
        errors.append(error)
        raise error

    monkeypatch.setattr(clang_build.Path, "unlink", fake)
    return errors


def test_new_error_classes():
    for cls in FILE_ERRORS:
        assert issubclass(cls, OSError)
        assert cls.__doc__
    assert not issubclass(ArtefactNotPlacedError, TemporaryNotRemovedError)
    assert not issubclass(TemporaryNotRemovedError, ArtefactNotPlacedError)
    for other in (ArtefactNotPlacedError, TemporaryNotRemovedError):
        assert not issubclass(ArtefactNotCheckedError, other)
        assert not issubclass(other, ArtefactNotCheckedError)
    assert BuildResult._fields == (
        "ok",
        "returncode",
        "timed_out",
        "output",
        "log",
        "command",
        "duration_s",
    )


def test_new_error_without_errno_keeps_its_message():
    error = TemporaryNotRemovedError(OSError("plain"), None)
    assert str(error) == "plain"
    assert error.errno is None
    assert error.filename is None
    assert error.result is None
    placed = ArtefactNotPlacedError(OSError("plain"), None)
    assert placed.removal_error is None


def test_new_errors_survive_pickling():
    result = BuildResult(True, 0, False, Path("a.o"), "log", ("cc",), 0.5)
    removal = OSError(5, "io", "a.tmp")
    move = PermissionError(13, "denied", "a.tmp", None, "a.o")
    errors = [
        ArtefactNotPlacedError(move, result, removal),
        TemporaryNotRemovedError(removal, result),
        TemporaryNotRemovedError(OSError("plain"), result),
        ArtefactNotCheckedError(move, result, removal),
        ArtefactNotCheckedError(OSError("plain"), result),
    ]
    for error in errors:
        copy = pickle.loads(pickle.dumps(error))
        assert type(copy) is type(error)
        assert str(copy) == str(error)
        assert (copy.errno, copy.strerror) == (error.errno, error.strerror)
        assert (copy.filename, copy.filename2) == (error.filename, error.filename2)
        assert copy.result == result
    for error in (errors[0], errors[3]):
        copy = pickle.loads(pickle.dumps(error))
        assert (copy.removal_error.errno, copy.removal_error.filename) == (5, "a.tmp")
    assert pickle.loads(pickle.dumps(errors[4])).removal_error is None


def test_failed_move_raises_with_the_log(stub, src, out_dir, failing_replace):
    out = out_dir / "kernel.o"
    out.write_bytes(b"previous")
    with pytest.raises(ArtefactNotPlacedError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=stub(BOTH))
    error = caught.value
    (cause,) = failing_replace
    assert error.__cause__ is cause
    assert (error.errno, error.strerror) == (13, "denied")
    assert (error.filename, error.filename2) == (cause.filename, cause.filename2)
    assert is_temporary(error.filename)
    assert error.filename2 == str(out)
    assert error.removal_error is None
    result = error.result
    assert isinstance(result, BuildResult)
    assert result.ok is False
    assert result.returncode == 0
    assert result.timed_out is False
    assert "to stdout" in result.log
    assert "to stderr" in result.log
    assert result.output == out
    assert result.command[-1] == cause.filename
    assert result.command[-2] == "-o"
    assert result.duration_s >= 0
    assert out.read_bytes() == b"previous"
    assert names(out_dir) == ["kernel.o"]


def test_failed_move_and_failed_removal(
    stub, src, out_dir, failing_replace, failing_unlink
):
    with pytest.raises(ArtefactNotPlacedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(LOGGED_WRITE))
    error = caught.value
    assert error.__cause__ is failing_replace[0]
    assert error.removal_error is failing_unlink[0]
    assert error.errno == 13
    assert error.strerror == "denied"
    assert error.result.ok is False
    assert "stub warning: kept" in error.result.log


def test_failed_removal_after_an_ok_build(
    stub, src, out_dir, failing_unlink, monkeypatch
):
    monkeypatch.setattr(clang_build.os, "replace", shutil.copyfile)
    out = out_dir / "kernel.o"
    with pytest.raises(TemporaryNotRemovedError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=stub(LOGGED_WRITE))
    error = caught.value
    (cause,) = failing_unlink
    assert not isinstance(error, ArtefactNotPlacedError)
    assert error.__cause__ is cause
    assert (error.errno, error.strerror, error.filename) == (13, "busy", cause.filename)
    assert Path(cause.filename).is_file()
    result = error.result
    assert result.ok is True
    assert result.returncode == 0
    assert "stub warning: kept" in result.log
    assert result.command[-1] == cause.filename
    assert out.read_bytes() == b"artefact"


def test_failed_removal_after_a_compile_error(stub, src, out_dir, failing_unlink):
    with pytest.raises(TemporaryNotRemovedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(FAIL))
    result = caught.value.result
    assert caught.value.__cause__ is failing_unlink[0]
    assert result.ok is False
    assert result.returncode not in (0, None)
    assert result.timed_out is False
    assert "error: stub says no" in result.log
    assert not (out_dir / "kernel.o").exists()


def test_failed_removal_after_a_timeout(stub, src, out_dir, failing_unlink):
    with pytest.raises(TemporaryNotRemovedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=5, compiler=stub(SLEEP))
    result = caught.value.result
    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode is None
    assert "before sleep" in result.log
    assert not (out_dir / "kernel.o").exists()


def test_failed_removal_after_exit_zero_without_artefact(
    stub, src, out_dir, failing_unlink
):
    with pytest.raises(TemporaryNotRemovedError) as caught:
        build(
            src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(LOGGED_NOTHING)
        )
    result = caught.value.result
    assert result.ok is False
    assert result.returncode == 0
    assert result.timed_out is False
    assert "stub warning: no artefact" in result.log
    assert names(out_dir) == []


def failing_start(monkeypatch, make_error):
    errors = []

    def popen(command, *args, **kwargs):
        error = make_error(command[0])
        errors.append(error)
        raise error

    monkeypatch.setattr(clang_build.subprocess, "Popen", popen)
    return errors


def cannot_start(path):
    return PermissionError(errno.EACCES, "cannot start", path)


@pytest.mark.parametrize(
    "make_error",
    [cannot_start, lambda path: FileNotFoundError(errno.ENOENT, "absent", path)],
    ids=["permission", "not-found"],
)
def test_error_from_starting_the_compiler_is_raised_as_not_started(
    make_error, stub, src, out_dir, monkeypatch
):
    errors = failing_start(monkeypatch, make_error)
    out = out_dir / "kernel.o"
    out.write_bytes(b"previous")
    with pytest.raises(CompilerNotStartedError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=stub(WRITE))
    error = caught.value
    (cause,) = errors
    assert error.__cause__ is cause
    assert (error.errno, error.strerror, error.filename) == (
        cause.errno,
        cause.strerror,
        cause.filename,
    )
    assert os.path.samefile(error.filename, sys.executable)
    assert error.removal_error is None
    assert not isinstance(error, FILE_ERRORS)
    assert not hasattr(error, "result")
    assert not stub.started
    assert out.read_bytes() == b"previous"
    assert names(out_dir) == ["kernel.o"]


def test_failed_removal_after_a_failed_start(
    stub, src, out_dir, monkeypatch, failing_unlink
):
    errors = failing_start(monkeypatch, cannot_start)
    with pytest.raises(CompilerNotStartedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    error = caught.value
    assert error.__cause__ is errors[0]
    assert error.removal_error is failing_unlink[0]
    assert (error.errno, error.strerror) == (errno.EACCES, "cannot start")
    assert not isinstance(error, FILE_ERRORS)
    assert not hasattr(error, "result")
    assert names(out_dir) == []


def test_missing_working_directory_is_a_failed_start(stub, src, out_dir, tmp_path):
    with pytest.raises(CompilerNotStartedError) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            cwd=tmp_path / "absent",
        )
    assert isinstance(caught.value.__cause__, OSError)
    assert caught.value.removal_error is None
    assert not stub.started
    assert names(out_dir) == []


def test_no_start_for_an_error_before_the_start(stub, src, out_dir, monkeypatch):
    calls = []

    def popen(*args, **kwargs):
        calls.append(args)
        raise AssertionError("the compiler was started")

    monkeypatch.setattr(clang_build.subprocess, "Popen", popen)
    with pytest.raises(FileNotFoundError) as caught:
        build(
            src.parent / "missing.c",
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert type(caught.value) is FileNotFoundError
    assert caught.value.path_role == "source"
    assert calls == []
    assert names(out_dir) == []


@pytest.fixture
def failing_communicate(monkeypatch):
    processes = []
    errors = [OSError(errno.EIO, "input/output error")]

    class Popen(clang_build.subprocess.Popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            processes.append(self)

        def communicate(self, *args, **kwargs):
            if not getattr(self, "failed", False):
                self.failed = True
                raise errors[0]
            return super().communicate(*args, **kwargs)

    monkeypatch.setattr(clang_build.subprocess, "Popen", Popen)
    return processes, errors


@pytest.mark.parametrize(
    "error",
    [
        OSError(errno.EIO, "input/output error"),
        FileNotFoundError(errno.ENOENT, "absent"),
    ],
    ids=["io", "not-found"],
)
def test_error_after_the_start_is_raised_as_run_error(
    error, stub, src, out_dir, failing_communicate
):
    processes, errors = failing_communicate
    errors[0] = error
    before = time.monotonic()
    with pytest.raises(OSError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert time.monotonic() - before < 20
    raised = caught.value
    assert type(raised) is CompilerRunError
    assert raised.__cause__ is error
    assert (raised.errno, raised.strerror) == (error.errno, error.strerror)
    assert raised.removal_error is None
    assert raised.timed_out is False
    assert raised.log is None
    assert raised.returncode is None
    assert not isinstance(raised, (CompilerNotStartedError, *FILE_ERRORS))
    assert not isinstance(raised, FileNotFoundError)
    assert not hasattr(raised, "result")
    (process,) = processes
    assert process.poll() is not None
    assert process.returncode != 0
    assert process.stdout.closed
    assert names(out_dir) == []


def test_failed_removal_after_an_error_after_the_start(
    stub, src, out_dir, failing_communicate, failing_unlink
):
    processes, errors = failing_communicate
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    error = caught.value
    assert error.__cause__ is errors[0]
    assert error.removal_error is failing_unlink[0]
    assert not getattr(error, "__notes__", [])
    assert error.timed_out is False
    assert error.log is None
    assert (error.errno, error.strerror) == (errno.EIO, "input/output error")
    assert not isinstance(error, (CompilerNotStartedError, *FILE_ERRORS))
    assert not hasattr(error, "result")
    assert processes[0].poll() is not None


def test_error_from_kill_after_a_failed_communicate(
    stub, src, out_dir, failing_communicate, monkeypatch
):
    processes, errors = failing_communicate
    popen = clang_build.subprocess.Popen
    kill_errors = []

    def kill(self):
        error = OSError(errno.EPERM, "cannot kill")
        kill_errors.append(error)
        raise error

    monkeypatch.setattr(popen, "kill", kill)
    try:
        with pytest.raises(CompilerRunError) as caught:
            build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    finally:
        for process in processes:
            super(popen, process).kill()
            process.wait()
    (kill_error,) = kill_errors
    assert caught.value.__cause__ is kill_error
    assert kill_error.__context__ is errors[0]
    assert caught.value.errno == errno.EPERM
    assert caught.value.removal_error is None
    assert caught.value.timed_out is False
    assert caught.value.log is None
    assert stub.started
    assert names(out_dir) == []


@pytest.fixture
def timed_out_run(monkeypatch):
    processes = []
    plan = {"time_limit": True, "output": b"read so far", "errors": {}}
    popen = clang_build.subprocess.Popen

    def fail(step):
        error = plan["errors"].pop(step, None)
        if error is not None:
            raise error

    class Popen(popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            processes.append(self)

        def communicate(self, input=None, timeout=None):
            if timeout is not None and plan["time_limit"]:
                raise subprocess.TimeoutExpired(self.args, timeout, plan["output"])
            fail("communicate")
            return super().communicate(input, timeout)

        def kill(self):
            super().kill()
            fail("kill")

        def wait(self, timeout=None):
            if self.returncode is None and "wait" in plan["errors"]:
                super().wait(timeout)
                fail("wait")
            return super().wait(timeout)

        def __exit__(self, *args):
            super().__exit__(*args)
            fail("exit")

    monkeypatch.setattr(clang_build.subprocess, "Popen", Popen)
    yield processes, plan
    for process in processes:
        if process.poll() is None:
            popen.kill(process)
            popen.wait(process)


def test_failed_kill_after_the_time_limit(stub, src, out_dir, monkeypatch):
    popen = clang_build.subprocess.Popen
    kill = popen.kill
    kill_errors = []

    def failing_kill(self):
        kill(self)
        error = OSError(errno.EPERM, "cannot kill")
        kill_errors.append(error)
        raise error

    monkeypatch.setattr(popen, "kill", failing_kill)
    before = time.monotonic()
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=5, compiler=stub(SLEEP))
    assert time.monotonic() - before < 20
    error = caught.value
    (kill_error,) = kill_errors
    assert error.__cause__ is kill_error
    assert error.errno == errno.EPERM
    assert error.timed_out is True
    assert error.removal_error is None
    assert not hasattr(error, "result")
    if sys.platform == "win32":
        assert error.log is None
    else:
        assert "before sleep" in error.log
    assert names(out_dir) == []


@pytest.mark.parametrize(
    "output", [b"read so far \xff", b"", None], ids=["output", "empty", "none"]
)
def test_failed_kill_keeps_what_the_time_limit_read(
    output, stub, src, out_dir, timed_out_run
):
    processes, plan = timed_out_run
    plan["output"] = output
    plan["errors"]["kill"] = OSError(errno.EPERM, "cannot kill")
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value.timed_out is True
    expected = None if output is None else output.decode("utf-8", errors="replace")
    assert caught.value.log == expected
    assert processes[0].poll() is not None
    assert names(out_dir) == []


@pytest.mark.parametrize("windows", [True, False], ids=["windows", "posix"])
def test_failed_read_or_wait_after_the_kill(
    windows, stub, src, out_dir, timed_out_run, monkeypatch
):
    monkeypatch.setattr(clang_build, "_WINDOWS", windows)
    processes, plan = timed_out_run
    step = "communicate" if windows else "wait"
    failure = plan["errors"][step] = OSError(errno.EIO, "input/output error")
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value.__cause__ is failure
    assert caught.value.timed_out is True
    assert caught.value.log == "read so far"
    assert caught.value.removal_error is None
    assert plan["errors"] == {}
    assert processes[0].poll() is not None
    assert names(out_dir) == []


@pytest.mark.parametrize("windows", [True, False], ids=["windows", "posix"])
def test_failed_close_after_the_time_limit(
    windows, stub, src, out_dir, timed_out_run, monkeypatch
):
    monkeypatch.setattr(clang_build, "_WINDOWS", windows)
    processes, plan = timed_out_run
    plan["output"] = None
    failure = plan["errors"]["exit"] = OSError(errno.EIO, "input/output error")
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value.__cause__ is failure
    assert caught.value.timed_out is True
    assert isinstance(caught.value.log, str) is windows
    assert processes[0].poll() is not None
    assert names(out_dir) == []


def test_failed_close_after_a_read_that_ended(stub, src, out_dir, timed_out_run):
    processes, plan = timed_out_run
    plan["time_limit"] = False
    failure = plan["errors"]["exit"] = OSError(errno.EIO, "input/output error")
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(BOTH))
    assert caught.value.__cause__ is failure
    assert caught.value.timed_out is False
    assert "to stdout" in caught.value.log
    assert "to stderr" in caught.value.log
    assert processes[0].returncode == 0
    assert caught.value.returncode is None
    assert names(out_dir) == []


def test_failed_removal_after_the_time_limit(
    stub, src, out_dir, timed_out_run, failing_unlink
):
    processes, plan = timed_out_run
    plan["errors"]["kill"] = OSError(errno.EPERM, "cannot kill")
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    error = caught.value
    assert error.timed_out is True
    assert error.log == "read so far"
    assert error.removal_error is failing_unlink[0]
    assert error.errno == errno.EPERM
    assert processes[0].poll() is not None


def test_keyboard_interrupt_after_the_start_is_passed_on(
    stub, src, out_dir, failing_communicate
):
    processes, errors = failing_communicate
    errors[0] = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value is errors[0]
    assert not getattr(caught.value, "__notes__", [])
    (process,) = processes
    assert process.wait(timeout=20) != 0
    assert names(out_dir) == []


def test_failed_removal_after_a_keyboard_interrupt_after_the_start(
    stub, src, out_dir, failing_communicate, failing_unlink
):
    processes, errors = failing_communicate
    errors[0] = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value is errors[0]
    assert_removal_note(caught.value, failing_unlink)
    (process,) = processes
    assert process.wait(timeout=20) != 0


def assert_removal_note(error, removal_errors):
    (removal,) = removal_errors
    (note,) = error.__notes__
    assert Path(removal.filename).name in note
    assert removal.strerror in note
    assert error.__cause__ is None
    assert error.__context__ is None


def test_failed_removal_after_a_keyboard_interrupt_from_starting(
    stub, src, out_dir, monkeypatch, failing_unlink
):
    errors = failing_start(monkeypatch, lambda path: KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value is errors[0]
    assert not isinstance(caught.value, CompilerNotStartedError)
    assert_removal_note(caught.value, failing_unlink)
    assert not stub.started


def test_failed_removal_after_a_non_os_error_after_the_start(
    stub, src, out_dir, failing_communicate, failing_unlink
):
    processes, errors = failing_communicate
    errors[0] = RuntimeError("not an OSError")
    with pytest.raises(RuntimeError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value is errors[0]
    assert not isinstance(caught.value, CompilerRunError)
    assert_removal_note(caught.value, failing_unlink)
    assert caught.value.__traceback__ is not None
    (process,) = processes
    assert process.wait(timeout=20) != 0


@pytest.fixture
def failing_clock(monkeypatch):
    errors = []

    def arm(reads=1, make=lambda: OSError(errno.EIO, "clock")):
        calls = []

        def monotonic():
            calls.append(None)
            if len(calls) <= reads:
                return time.monotonic()
            error = make()
            errors.append(error)
            raise error

        monkeypatch.setattr(clang_build, "time", SimpleNamespace(monotonic=monotonic))
        return errors

    return arm


def assert_clock_run_error(raised, errors):
    (error,) = errors
    assert type(raised) is CompilerRunError
    assert raised.__cause__ is error
    assert (raised.errno, raised.strerror) == (errno.EIO, "clock")
    assert not isinstance(raised, (CompilerNotStartedError, *FILE_ERRORS))
    assert not hasattr(raised, "result")


@pytest.mark.parametrize("previous", [None, b"previous"], ids=["new", "existing"])
def test_failed_clock_after_an_ok_build_is_a_run_error(
    previous, stub, src, out_dir, failing_clock
):
    out = out_dir / "kernel.o"
    if previous is not None:
        out.write_bytes(previous)
    errors = failing_clock()
    with pytest.raises(OSError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=stub(LOGGED_WRITE))
    raised = caught.value
    assert_clock_run_error(raised, errors)
    assert raised.timed_out is False
    assert raised.log.splitlines() == ["stub warning: kept"]
    assert raised.removal_error is None
    assert raised.returncode == 0
    assert not getattr(raised, "__notes__", [])
    assert stub.started
    if previous is None:
        assert names(out_dir) == []
    else:
        assert out.read_bytes() == previous
        assert names(out_dir) == ["kernel.o"]


def test_failed_clock_after_a_compile_error_is_a_run_error(
    stub, src, out_dir, failing_clock
):
    errors = failing_clock()
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(FAIL))
    raised = caught.value
    assert_clock_run_error(raised, errors)
    assert raised.timed_out is False
    assert "kernel.c:1:1: error: stub says no" in raised.log
    assert raised.removal_error is None
    assert raised.returncode == 1
    assert names(out_dir) == []


def test_failed_clock_after_the_time_limit_is_a_timed_out_run_error(
    stub, src, out_dir, failing_clock
):
    errors = failing_clock()
    before = time.monotonic()
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=5, compiler=stub(SLEEP))
    assert time.monotonic() - before < 20
    raised = caught.value
    assert_clock_run_error(raised, errors)
    assert raised.timed_out is True
    assert "before sleep" in raised.log
    assert raised.removal_error is None
    assert raised.returncode is None
    assert names(out_dir) == []


def test_failed_clock_and_failed_removal(
    stub, src, out_dir, failing_clock, failing_unlink
):
    errors = failing_clock()
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    raised = caught.value
    assert_clock_run_error(raised, errors)
    assert raised.removal_error is failing_unlink[0]
    assert not getattr(raised, "__notes__", [])
    assert raised.timed_out is False
    assert raised.returncode == 0


@pytest.mark.parametrize("status", [3, 77])
def test_failed_clock_states_the_exit_status(status, stub, src, out_dir, failing_clock):
    errors = failing_clock()
    body = f"print('exiting with {status}'); sys.exit({status})"
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(body))
    raised = caught.value
    assert_clock_run_error(raised, errors)
    assert raised.returncode == status
    assert raised.timed_out is False
    assert raised.log.splitlines() == [f"exiting with {status}"]
    assert names(out_dir) == []


def test_failed_kill_after_the_time_limit_states_no_return_code(
    stub, src, out_dir, timed_out_run
):
    processes, plan = timed_out_run
    plan["errors"]["kill"] = OSError(errno.EPERM, "cannot kill")
    with pytest.raises(CompilerRunError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value.timed_out is True
    assert caught.value.returncode is None
    assert processes[0].poll() is not None


def test_other_errors_carry_no_return_code(stub, src, out_dir, failing_unlink):
    with pytest.raises(TemporaryNotRemovedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value.result.returncode == 0
    assert not hasattr(caught.value, "returncode")
    for error in (
        CompilerNotStartedError(OSError("plain")),
        ArtefactNotPlacedError(OSError("plain"), None),
        ArtefactNotCheckedError(OSError("plain"), None),
        TemporaryNotRemovedError(OSError("plain"), None),
    ):
        assert not hasattr(error, "returncode")
        assert not hasattr(pickle.loads(pickle.dumps(error)), "returncode")


def test_non_os_error_from_the_clock_after_the_end_is_passed_on(
    stub, src, out_dir, failing_clock, failing_unlink
):
    errors = failing_clock(make=lambda: RuntimeError("not an OSError"))
    with pytest.raises(RuntimeError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value is errors[0]
    assert not isinstance(caught.value, CompilerRunError)
    assert_removal_note(caught.value, failing_unlink)
    assert stub.started


def test_failed_clock_before_the_start_stays_plain(stub, src, out_dir, failing_clock):
    errors = failing_clock(reads=0)
    with pytest.raises(OSError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value is errors[0]
    assert type(caught.value) is OSError
    assert not isinstance(
        caught.value, (CompilerRunError, CompilerNotStartedError, *FILE_ERRORS)
    )
    assert not hasattr(caught.value, "path_role")
    assert not stub.started
    assert names(out_dir) == []


def test_errors_outside_the_run_are_not_run_errors(stub, src, out_dir, monkeypatch):
    with pytest.raises(FileNotFoundError) as caught:
        build(src.parent / "missing.c", out_dir / "kernel.o", timeout_s=TIMEOUT)
    assert not isinstance(caught.value, CompilerRunError)
    assert caught.value.path_role == "source"
    failing_start(monkeypatch, cannot_start)
    with pytest.raises(CompilerNotStartedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert not isinstance(caught.value, CompilerRunError)
    assert not hasattr(caught.value, "path_role")


@pytest.mark.parametrize("windows", [True, False], ids=["windows", "posix"])
def test_timeout_on_either_platform(windows, stub, src, out_dir, monkeypatch):
    monkeypatch.setattr(clang_build, "_WINDOWS", windows)
    before = time.monotonic()
    result = build(src, out_dir / "kernel.o", timeout_s=5, compiler=stub(SLEEP))
    assert time.monotonic() - before < 20
    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode is None
    if windows or sys.platform != "win32":
        assert "before sleep" in result.log
    assert stub.started
    assert names(out_dir) == []


def test_not_started_error_class():
    assert issubclass(CompilerNotStartedError, OSError)
    assert CompilerNotStartedError.__doc__
    for other in FILE_ERRORS:
        assert not issubclass(CompilerNotStartedError, other)
        assert not issubclass(other, CompilerNotStartedError)
    error = CompilerNotStartedError(OSError("plain"))
    assert str(error) == "plain"
    assert error.errno is None
    assert error.filename is None
    assert error.removal_error is None
    assert not hasattr(error, "result")


def test_not_started_error_survives_pickling():
    removal = OSError(errno.EIO, "io", "a.tmp")
    errors = [
        CompilerNotStartedError(
            PermissionError(13, "denied", "cc", None, "x"), removal
        ),
        CompilerNotStartedError(FileNotFoundError(errno.ENOENT, "absent", "cc")),
        CompilerNotStartedError(OSError("plain")),
    ]
    for error in errors:
        copy = pickle.loads(pickle.dumps(error))
        assert type(copy) is CompilerNotStartedError
        assert str(copy) == str(error)
        assert (copy.errno, copy.strerror) == (error.errno, error.strerror)
        assert (copy.filename, copy.filename2) == (error.filename, error.filename2)
        assert not hasattr(copy, "result")
    copy = pickle.loads(pickle.dumps(errors[0]))
    assert (copy.removal_error.errno, copy.removal_error.filename) == (
        errno.EIO,
        "a.tmp",
    )
    assert copy.filename2 == "x"
    assert pickle.loads(pickle.dumps(errors[1])).removal_error is None


def test_run_error_class():
    assert issubclass(CompilerRunError, OSError)
    assert CompilerRunError.__doc__
    for other in (CompilerNotStartedError, *FILE_ERRORS):
        assert not issubclass(CompilerRunError, other)
        assert not issubclass(other, CompilerRunError)
    error = CompilerRunError(OSError("plain"))
    assert str(error) == "plain"
    assert error.errno is None
    assert error.filename is None
    assert error.removal_error is None
    assert error.timed_out is False
    assert error.log is None
    assert error.returncode is None
    assert not hasattr(error, "result")
    assert CompilerRunError(OSError("plain"), returncode=2).returncode == 2
    assert CompilerRunError(OSError("plain"), returncode=0).returncode == 0
    with pytest.raises(TypeError):
        CompilerRunError(OSError("plain"), None, False, None, 0)
    removal = OSError("removal")
    error = CompilerRunError(OSError("plain"), removal)
    assert (error.removal_error, error.timed_out, error.log) == (removal, False, None)
    error = CompilerRunError(OSError("plain"), timed_out=True, log="")
    assert (error.removal_error, error.timed_out, error.log) == (None, True, "")
    with pytest.raises(TypeError):
        CompilerRunError(OSError("plain"), None, True)


def test_run_error_survives_pickling():
    removal = OSError(errno.EIO, "io", "a.tmp")
    errors = [
        CompilerRunError(PermissionError(13, "denied", "cc", None, "x"), removal),
        CompilerRunError(OSError(errno.EIO, "input/output error")),
        CompilerRunError(OSError("plain")),
        CompilerRunError(
            OSError(errno.EPERM, "cannot kill"), removal, timed_out=True, log="so far"
        ),
    ]
    for error in errors:
        copy = pickle.loads(pickle.dumps(error))
        assert type(copy) is CompilerRunError
        assert str(copy) == str(error)
        assert (copy.errno, copy.strerror) == (error.errno, error.strerror)
        assert (copy.filename, copy.filename2) == (error.filename, error.filename2)
        assert (copy.timed_out, copy.log) == (error.timed_out, error.log)
        assert copy.returncode is None
        assert not hasattr(copy, "result")
    for returncode in (0, 1, -9, None):
        error = CompilerRunError(
            OSError(errno.EIO, "clock"), log="kept", returncode=returncode
        )
        copy = pickle.loads(pickle.dumps(error))
        assert type(copy) is CompilerRunError
        assert copy.returncode == returncode
        assert (copy.errno, copy.log, copy.timed_out) == (errno.EIO, "kept", False)
    copy = pickle.loads(pickle.dumps(errors[3]))
    assert (copy.timed_out, copy.log) == (True, "so far")
    assert copy.removal_error.filename == "a.tmp"
    copy = pickle.loads(pickle.dumps(errors[1]))
    assert (copy.timed_out, copy.log) == (False, None)
    copy = pickle.loads(pickle.dumps(errors[0]))
    assert type(copy.removal_error) is OSError
    assert (copy.removal_error.errno, copy.removal_error.filename) == (
        errno.EIO,
        "a.tmp",
    )
    assert copy.filename2 == "x"
    assert pickle.loads(pickle.dumps(errors[1])).removal_error is None


@pytest.mark.parametrize(
    "make",
    [
        CompilerNotStartedError,
        CompilerRunError,
        lambda error: ArtefactNotPlacedError(error, None),
        lambda error: ArtefactNotCheckedError(error, None),
        lambda error: TemporaryNotRemovedError(error, None),
    ],
    ids=["not-started", "run", "not-placed", "not-checked", "not-removed"],
)
def test_error_with_errno_and_no_filename_survives_pickling(make):
    error = make(OSError(errno.EIO, "input/output error"))
    copy = pickle.loads(pickle.dumps(error))
    assert type(copy) is type(error)
    assert str(copy) == str(error) == "[Errno 5] input/output error"
    assert copy.args == error.args
    assert (copy.filename, copy.filename2) == (None, None)


def test_except_oserror_catches_run_error(stub, src, out_dir, failing_communicate):
    try:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    except OSError as error:
        caught = error
    else:
        pytest.fail("build did not raise")
    assert type(caught) is CompilerRunError
    assert BuildResult._fields == (
        "ok",
        "returncode",
        "timed_out",
        "output",
        "log",
        "command",
        "duration_s",
    )


def test_except_oserror_catches_not_started(stub, src, out_dir, monkeypatch):
    failing_start(monkeypatch, cannot_start)
    try:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    except OSError as error:
        caught = error
    else:
        pytest.fail("build did not raise")
    assert type(caught) is CompilerNotStartedError


@pytest.mark.parametrize("which", ["move", "removal"])
def test_except_oserror_catches_both_new_errors(which, stub, src, out_dir, request):
    request.getfixturevalue("failing_replace" if which == "move" else "failing_unlink")
    try:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    except OSError as error:
        caught = error
    else:
        pytest.fail("build did not raise")
    expected = ArtefactNotPlacedError if which == "move" else TemporaryNotRemovedError
    assert type(caught) is expected


def test_artefact_not_checked_error_without_errno():
    error = ArtefactNotCheckedError(OSError("plain"), None)
    assert str(error) == "plain"
    assert error.errno is None
    assert error.filename is None
    assert error.result is None
    assert error.removal_error is None


def fail_stat_of_temporary(monkeypatch, make_error):
    errors = []
    real = os.stat

    def fake(path, *args, **kwargs):
        if isinstance(path, (str, os.PathLike)) and is_temporary(path):
            error = make_error(str(path))
            errors.append(error)
            raise error
        return real(path, *args, **kwargs)

    monkeypatch.setattr(clang_build.os, "stat", fake)
    return errors


@pytest.fixture
def failing_stat(monkeypatch):
    return fail_stat_of_temporary(
        monkeypatch, lambda path: PermissionError(13, "denied", path)
    )


@pytest.fixture
def recorded_replace(monkeypatch):
    calls = []
    real = os.replace

    def replace(source, destination):
        calls.append((source, destination))
        return real(source, destination)

    monkeypatch.setattr(clang_build.os, "replace", replace)
    return calls


def test_failed_test_of_the_temporary_raises_with_the_log(
    stub, src, out_dir, failing_stat, recorded_replace
):
    out = out_dir / "kernel.o"
    out.write_bytes(b"previous")
    compiler = stub(BOTH)
    with pytest.raises(ArtefactNotCheckedError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=compiler)
    error = caught.value
    (cause,) = failing_stat
    assert error.__cause__ is cause
    assert (error.errno, error.strerror, error.filename) == (
        13,
        "denied",
        cause.filename,
    )
    assert is_temporary(error.filename)
    assert error.removal_error is None
    assert not isinstance(error, (ArtefactNotPlacedError, TemporaryNotRemovedError))
    result = error.result
    assert isinstance(result, BuildResult)
    assert result.ok is False
    assert result.returncode == 0
    assert result.timed_out is False
    assert "to stdout" in result.log
    assert "to stderr" in result.log
    assert result.output == out
    assert os.path.samefile(result.command[0], sys.executable)
    assert result.command[1:] == (compiler[1], str(src), "-o", cause.filename)
    assert result.duration_s >= 0
    assert recorded_replace == []
    assert out.read_bytes() == b"previous"
    assert names(out_dir) == ["kernel.o"]


def test_failed_test_of_the_temporary_and_failed_removal(
    stub, src, out_dir, failing_stat, failing_unlink
):
    try:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(LOGGED_WRITE))
    except OSError as caught:
        error = caught
    else:
        pytest.fail("build did not raise")
    assert type(error) is ArtefactNotCheckedError
    assert not isinstance(error, TemporaryNotRemovedError)
    assert error.__cause__ is failing_stat[0]
    assert error.removal_error is failing_unlink[0]
    assert (error.errno, error.strerror) == (13, "denied")
    assert error.result.ok is False
    assert "stub warning: kept" in error.result.log


@pytest.mark.parametrize(
    "absent, number",
    [(FileNotFoundError, errno.ENOENT), (NotADirectoryError, errno.ENOTDIR)],
)
def test_absent_temporary_reads_as_no_artefact(
    absent, number, stub, src, out_dir, monkeypatch
):
    errors = fail_stat_of_temporary(
        monkeypatch, lambda path: absent(number, "absent", path)
    )
    out = out_dir / "kernel.o"
    result = build(src, out, timeout_s=TIMEOUT, compiler=stub(LOGGED_WRITE))
    assert len(errors) == 1
    assert result.ok is False
    assert result.returncode == 0
    assert result.timed_out is False
    assert "stub warning: kept" in result.log
    assert names(out_dir) == []


def test_temporary_that_is_no_regular_file_reads_as_no_artefact(stub, src, out_dir):
    body = "out.mkdir(); print('made a directory')"
    with pytest.raises(TemporaryNotRemovedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(body))
    result = caught.value.result
    assert result.ok is False
    assert result.returncode == 0
    assert "made a directory" in result.log
    assert not (out_dir / "kernel.o").exists()


def test_no_test_of_the_temporary_after_a_compile_error(
    stub, src, out_dir, failing_stat
):
    result = build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(FAIL))
    assert failing_stat == []
    assert result.ok is False
    assert result.returncode not in (0, None)
    assert "error: stub says no" in result.log
    assert names(out_dir) == []


def test_no_test_of_the_temporary_after_a_timeout(stub, src, out_dir, failing_stat):
    result = build(src, out_dir / "kernel.o", timeout_s=5, compiler=stub(SLEEP))
    assert failing_stat == []
    assert result.ok is False
    assert result.timed_out is True
    assert result.returncode is None
    assert "before sleep" in result.log


def test_error_from_starting_is_not_started_with_a_failing_test(
    stub, src, out_dir, failing_stat, monkeypatch
):
    errors = failing_start(monkeypatch, cannot_start)
    with pytest.raises(CompilerNotStartedError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value.__cause__ is errors[0]
    assert caught.value.removal_error is None
    assert not isinstance(caught.value, FILE_ERRORS)
    assert not hasattr(caught.value, "result")
    assert failing_stat == []


@pytest.mark.parametrize(
    "sources, error",
    [
        ("missing.c", FileNotFoundError),
        (["kernel.c", "missing.c"], FileNotFoundError),
        (".", IsADirectoryError),
        ([], ValueError),
        ((), ValueError),
        ([3], TypeError),
        ([None], TypeError),
        (b"kernel.c", TypeError),
    ],
)
def test_unusable_sources(sources, error, stub, src, out_dir, monkeypatch):
    monkeypatch.chdir(src.parent)
    with pytest.raises(error) as caught:
        build(sources, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert type(caught.value) is error
    if issubclass(error, OSError):
        assert caught.value.path_role == "source"
    else:
        assert not hasattr(caught.value, "path_role")
    if error is TypeError:
        assert caught.value.parameter == "sources"
    else:
        assert not hasattr(caught.value, "parameter")
    assert not stub.started
    assert names(out_dir) == []


def test_missing_output_directory(stub, src, tmp_path):
    with pytest.raises(FileNotFoundError) as caught:
        build(
            src,
            tmp_path / "absent" / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert type(caught.value) is FileNotFoundError
    assert caught.value.path_role == "output"
    assert not stub.started
    assert not (tmp_path / "absent").exists()


def test_output_parent_is_a_regular_file(stub, src, out_dir):
    blocker = out_dir / "file"
    blocker.write_bytes(b"x")
    with pytest.raises(NotADirectoryError) as caught:
        build(src, blocker / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert type(caught.value) is NotADirectoryError
    assert caught.value.path_role == "output"
    assert not stub.started


def test_output_is_a_directory(stub, src, out_dir):
    with pytest.raises(IsADirectoryError) as caught:
        build(src, out_dir, timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert type(caught.value) is IsADirectoryError
    assert caught.value.path_role == "output"
    assert not stub.started
    assert names(out_dir) == []


def refusing(monkeypatch, name, refused):
    errors = []
    real = getattr(clang_build.Path, name)

    def fake(path):
        if os.fspath(path) == os.fspath(refused):
            error = PermissionError(errno.EACCES, "refused", os.fspath(path))
            errors.append(error)
            raise error
        return real(path)

    monkeypatch.setattr(clang_build.Path, name, fake)
    return errors


def assert_refusal(caught, errors, role):
    (error,) = errors
    assert caught.value is error
    assert type(caught.value) is PermissionError
    assert caught.value.errno == errno.EACCES
    assert caught.value.args == (errno.EACCES, "refused")
    assert caught.value.__traceback__ is not None
    assert caught.value.path_role == role


@pytest.mark.parametrize("name", ["is_file", "is_dir"])
def test_refused_test_of_a_source_has_the_source_role(
    name, stub, src, out_dir, monkeypatch
):
    if name == "is_dir":
        monkeypatch.setattr(clang_build.Path, "is_file", lambda self: False)
    errors = refusing(monkeypatch, name, src)
    with pytest.raises(PermissionError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert_refusal(caught, errors, "source")
    assert not stub.started
    assert names(out_dir) == []


@pytest.mark.parametrize(
    "name, tested",
    [("is_dir", "parent"), ("exists", "parent"), ("is_dir", "output")],
)
def test_refused_test_of_the_output_has_the_output_role(
    name, tested, stub, src, out_dir, tmp_path, monkeypatch
):
    out = (tmp_path / "absent" if name == "exists" else out_dir) / "kernel.o"
    errors = refusing(monkeypatch, name, out.parent if tested == "parent" else out)
    with pytest.raises(PermissionError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert_refusal(caught, errors, "output")
    assert not stub.started
    assert names(out_dir) == []
    assert not os.path.exists(tmp_path / "absent")


def failing_abspath(monkeypatch, failing):
    errors = []
    real = os.path.abspath

    def fake(path):
        if os.fspath(path) == os.fspath(failing):
            error = FileNotFoundError(errno.ENOENT, "no working directory")
            errors.append(error)
            raise error
        return real(path)

    monkeypatch.setattr(clang_build.os.path, "abspath", fake)
    return errors


def failing_call(monkeypatch, owner, name):
    errors = []

    def fake(*args, **kwargs):
        error = PermissionError(errno.EACCES, "refused")
        errors.append(error)
        raise error

    monkeypatch.setattr(owner, name, fake)
    return errors


@pytest.mark.parametrize("where", ["source", "output", "token_hex", "which"])
def test_other_errors_before_the_start_have_no_role(
    where, stub, src, out_dir, monkeypatch
):
    out = out_dir / "kernel.o"
    compiler = stub(WRITE)
    if where == "source":
        errors = failing_abspath(monkeypatch, src)
    elif where == "output":
        errors = failing_abspath(monkeypatch, out)
    elif where == "token_hex":
        errors = failing_call(monkeypatch, clang_build.secrets, "token_hex")
    else:
        errors = failing_call(monkeypatch, clang_build.shutil, "which")
    with pytest.raises(OSError) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=compiler)
    assert caught.value is errors[0]
    assert not hasattr(caught.value, "path_role")
    assert not isinstance(caught.value, (CompilerRunError, CompilerNotStartedError))
    assert not stub.started
    assert names(out_dir) == []


@pytest.mark.parametrize(
    "fixture, expected",
    [
        ("failing_communicate", CompilerRunError),
        ("failing_replace", ArtefactNotPlacedError),
        ("failing_stat", ArtefactNotCheckedError),
        ("failing_unlink", TemporaryNotRemovedError),
    ],
)
def test_errors_of_the_run_and_after_have_no_role(
    fixture, expected, stub, src, out_dir, request
):
    request.getfixturevalue(fixture)
    with pytest.raises(expected) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert type(caught.value) is expected
    assert not hasattr(caught.value, "path_role")


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"timeout_s": 0}, ValueError),
        ({"timeout_s": TIMEOUT, "flags": "-O2"}, TypeError),
        (
            {"timeout_s": TIMEOUT, "compiler": "hilclaw-no-such-compiler"},
            CompilerNotFoundError,
        ),
    ],
)
def test_checks_other_than_paths_have_no_role(kwargs, expected, src, out_dir):
    with pytest.raises(expected) as caught:
        build(src, out_dir / "kernel.o", **kwargs)
    assert not hasattr(caught.value, "path_role")
    if expected is TypeError:
        assert caught.value.parameter == "flags"
    else:
        assert not hasattr(caught.value, "parameter")
    assert names(out_dir) == []


def test_successful_build_after_the_path_tests(stub, src, out_dir):
    result = build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert type(result) is BuildResult
    assert result.ok is True
    assert not hasattr(result, "path_role")
    assert names(out_dir) == ["kernel.o"]


@pytest.mark.parametrize("role", ["source", "output"])
def test_path_errors_keep_their_role_through_pickling(role, stub, src, out_dir):
    if role == "source":
        sources, out = src.parent / "missing.c", out_dir / "kernel.o"
    else:
        sources, out = src, out_dir / "absent" / "kernel.o"
    with pytest.raises(FileNotFoundError) as caught:
        build(sources, out, timeout_s=TIMEOUT, compiler=stub(WRITE))
    loaded = pickle.loads(pickle.dumps(caught.value))
    assert type(loaded) is FileNotFoundError
    assert str(loaded) == str(caught.value)
    assert loaded.path_role == role


@pytest.mark.parametrize(
    "kwargs, parameter",
    [
        ({"timeout_s": "10"}, "timeout_s"),
        ({"timeout_s": True}, "timeout_s"),
        ({"flags": "-O2"}, "flags"),
        ({"trailing_flags": ("-lm", 1)}, "trailing_flags"),
    ],
)
def test_type_errors_name_the_setting(kwargs, parameter, stub, src, out_dir):
    arguments = {"timeout_s": TIMEOUT, "compiler": stub(WRITE), **kwargs}
    with pytest.raises(TypeError) as caught:
        build(src, out_dir / "kernel.o", **arguments)
    assert type(caught.value) is TypeError
    assert caught.value.parameter == parameter
    assert not stub.started
    assert names(out_dir) == []


@pytest.mark.parametrize(
    "kwargs, parameter",
    [
        ({"sources": [3]}, "sources"),
        ({"sources": [None]}, "sources"),
        ({"sources": b"kernel.c"}, "sources"),
        ({"output": 3}, "output"),
        ({"compiler": (sys.executable, 3)}, "compiler"),
        ({"compiler": b"clang"}, "compiler"),
    ],
)
def test_type_errors_name_each_parameter(kwargs, parameter, stub, src, out_dir):
    arguments = {"sources": src, "output": out_dir / "kernel.o", "timeout_s": TIMEOUT}
    arguments["compiler"] = stub(WRITE)
    arguments.update(kwargs)
    with pytest.raises(TypeError) as caught:
        build(**arguments)
    assert type(caught.value) is TypeError
    assert caught.value.parameter == parameter
    assert not stub.started
    assert names(out_dir) == []


def python_type_error(call):
    with pytest.raises(TypeError) as caught:
        call()
    return caught.value


@pytest.mark.parametrize(
    "keyword, call",
    [
        ("flags", lambda: tuple(3)),
        ("sources", lambda: [source for source in 3]),
        ("compiler", lambda: tuple(3)),
    ],
)
def test_type_errors_python_raises_in_a_check_name_the_parameter(
    keyword, call, stub, src, out_dir
):
    arguments = {"sources": src, "timeout_s": TIMEOUT, "compiler": stub(WRITE)}
    arguments[keyword] = 3
    with pytest.raises(TypeError) as caught:
        build(output=out_dir / "kernel.o", **arguments)
    expected = python_type_error(call)
    assert type(caught.value) is TypeError
    assert caught.value.args == expected.args
    assert str(caught.value) == str(expected)
    assert caught.value.parameter == keyword
    assert not stub.started
    assert names(out_dir) == []


def test_type_error_of_a_source_path_is_the_same_object(
    stub, src, out_dir, monkeypatch
):
    error = TypeError("abspath refused")
    real = os.path.abspath

    def fake(path):
        if os.fspath(path) == os.fspath(src):
            raise error
        return real(path)

    monkeypatch.setattr(clang_build.os.path, "abspath", fake)
    with pytest.raises(TypeError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value is error
    assert type(caught.value) is TypeError
    assert caught.value.args == ("abspath refused",)
    assert caught.value.__traceback__ is not None
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None
    assert caught.value.parameter == "sources"
    assert not stub.started


def test_first_type_error_in_check_order_is_named(stub, src, out_dir):
    with pytest.raises(TypeError) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s="10",
            flags="-O2",
            compiler=stub(WRITE),
        )
    assert caught.value.parameter == "timeout_s"
    assert "timeout_s" in str(caught.value)
    assert not stub.started


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"timeout_s": 0}, ValueError),
        ({"compiler": ()}, ValueError),
        ({"flags": ("-o", "x.o")}, ValueError),
        ({"compiler": "hilclaw-no-such-compiler"}, CompilerNotFoundError),
        ({"sources": "missing.c"}, FileNotFoundError),
        ({"output": Path("absent") / "kernel.o"}, FileNotFoundError),
    ],
)
def test_other_errors_before_the_start_have_no_parameter(
    kwargs, expected, stub, src, out_dir, monkeypatch
):
    monkeypatch.chdir(src.parent)
    arguments = {"sources": src, "output": out_dir / "kernel.o", "timeout_s": TIMEOUT}
    arguments["compiler"] = stub(WRITE)
    arguments.update(kwargs)
    with pytest.raises(expected) as caught:
        build(**arguments)
    assert type(caught.value) is expected
    assert not hasattr(caught.value, "parameter")
    if issubclass(expected, OSError):
        assert caught.value.path_role == ("source" if "sources" in kwargs else "output")
    assert not stub.started
    assert names(out_dir) == []


def test_type_error_from_creating_the_process_has_no_parameter(
    stub, src, out_dir, monkeypatch
):
    error = TypeError("cannot hand over")

    def popen(*args, **kwargs):
        raise error

    monkeypatch.setattr(clang_build.subprocess, "Popen", popen)
    with pytest.raises(TypeError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert caught.value is error
    assert not hasattr(caught.value, "parameter")
    assert not stub.started
    assert names(out_dir) == []


@pytest.mark.parametrize(
    "kwargs",
    [{"timeout_s": "10"}, {"compiler": (sys.executable, 3), "timeout_s": TIMEOUT}],
)
def test_type_errors_of_compiler_version_have_no_parameter(kwargs, stub):
    arguments = {"compiler": stub(VERSION), **kwargs}
    with pytest.raises(TypeError) as caught:
        compiler_version(**arguments)
    assert type(caught.value) is TypeError
    assert not hasattr(caught.value, "parameter")
    assert not stub.started


def test_successful_build_carries_no_parameter(stub, src, out_dir):
    result = build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert type(result) is BuildResult
    assert result.ok is True
    assert not hasattr(result, "parameter")


@pytest.mark.parametrize(
    "kwargs, parameter",
    [
        ({"timeout_s": "10"}, "timeout_s"),
        ({"output": 3}, "output"),
        ({"cwd": 3}, "cwd"),
    ],
)
def test_type_errors_keep_their_parameter_through_pickling(
    kwargs, parameter, stub, src, out_dir
):
    arguments = {"output": out_dir / "kernel.o", "timeout_s": TIMEOUT, **kwargs}
    with pytest.raises(TypeError) as caught:
        build(src, compiler=stub(WRITE), **arguments)
    loaded = pickle.loads(pickle.dumps(caught.value))
    assert type(loaded) is TypeError
    assert str(loaded) == str(caught.value)
    assert loaded.args == caught.value.args
    assert loaded.parameter == parameter


posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")
windows_only = pytest.mark.skipif(os.name != "nt", reason="native Windows behaviour")
PASSED_ON = (AttributeError, OSError, TypeError, ValueError)


class IntPath:
    def __fspath__(self):
        return 3


class Items(dict):
    def __init__(self, error):
        super().__init__()
        self.error = error

    def items(self):
        raise self.error


def directly(cwd, env):
    try:
        process = subprocess.Popen(
            (os.path.abspath(sys.executable), "-c", "pass"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            env=env,
        )
    except PASSED_ON as error:
        return type(error)
    process.communicate()
    return None


def forbid_start(monkeypatch):
    def popen(*args, **kwargs):
        pytest.fail("a process was started")

    monkeypatch.setattr(clang_build.subprocess, "Popen", popen)


def refused(compiler, src, out_dir, **settings):
    out = out_dir / "kernel.o"
    out.write_bytes(b"kept")
    with pytest.raises(Exception) as caught:
        build(src, out, timeout_s=TIMEOUT, compiler=compiler, **settings)
    assert out.read_bytes() == b"kept"
    assert names(out_dir) == ["kernel.o"]
    return caught.value


REFUSED_ENVS = [
    ({"A=B": "x"}, ValueError),
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


@pytest.mark.parametrize("variable, kind", REFUSED)
def test_a_refused_env_names_env_and_starts_nothing(
    variable, kind, stub, src, out_dir, monkeypatch
):
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    error = refused(compiler, src, out_dir, env={**os.environ, **variable})
    assert type(error) is kind
    assert error.parameter == "env"
    assert not hasattr(error, "path_role")
    assert not stub.started


@pytest.mark.parametrize("variable, kind", REFUSED)
@pytest.mark.parametrize("in_cwd", [False, True])
def test_a_refused_env_has_the_class_popen_raises(variable, kind, in_cwd, tmp_path):
    cwd = tmp_path if in_cwd else None
    assert directly(cwd, {**os.environ, **variable}) is kind


def test_an_env_error_message_names_the_key_and_not_the_value(
    stub, src, out_dir, monkeypatch
):
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    env = {**os.environ, "HILCLAW_K": "secret\0"}
    error = refused(compiler, src, out_dir, env=env)
    assert "HILCLAW_K" in str(error)
    assert "secret" not in str(error)


ACCEPTED_ENVS = [
    {"HILCLAW_TEST_MARK": "accepted"},
    pytest.param({b"HILCLAW_TEST_MARK": b"accepted"}, marks=posix_only),
    pytest.param({"HILCLAW_TEST_MARK": Path("accepted")}, marks=posix_only),
    pytest.param({"=A": "x", "HILCLAW_TEST_MARK": "accepted"}, marks=windows_only),
]


@pytest.mark.parametrize("variable", ACCEPTED_ENVS)
@pytest.mark.parametrize("in_cwd", [False, True])
def test_an_accepted_env_reaches_the_compiler(
    variable, in_cwd, stub, src, out_dir, tmp_path, monkeypatch
):
    monkeypatch.delenv("HILCLAW_TEST_MARK", raising=False)
    cwd = tmp_path if in_cwd else None
    result = build(
        src,
        out_dir / "kernel.o",
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
        cwd=cwd,
        env={**os.environ, **variable},
    )
    assert result.ok
    assert stub.call()["mark"] == "accepted"


def test_no_env_and_no_cwd_inherit_after_the_checks(stub, src, out_dir, monkeypatch):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "inherited")
    result = build(
        src,
        out_dir / "kernel.o",
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
        cwd=None,
        env=None,
    )
    assert result.ok
    call = stub.call()
    assert call["mark"] == "inherited"
    assert os.path.samefile(call["cwd"], os.getcwd())


def test_env_and_cwd_are_handed_on_as_given(stub, src, out_dir, tmp_path, monkeypatch):
    seen = []

    def record(*args, **kwargs):
        seen.append((kwargs["cwd"], kwargs["env"]))
        raise LookupError("recorded")

    monkeypatch.setattr(clang_build.subprocess, "Popen", record)
    env = {**os.environ, "HILCLAW_TEST_MARK": "given"}
    with pytest.raises(LookupError):
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            cwd=tmp_path,
            env=env,
        )
    assert len(seen) == 1
    assert seen[0][0] is tmp_path
    assert seen[0][1] is env
    assert names(out_dir) == []


UNCHANGED_ENVS = [
    {"": "x"},
    pytest.param({"=A": "x"}, marks=posix_only),
    pytest.param({b"=A": b"x"}, marks=posix_only),
    pytest.param({b"": b"x"}, marks=posix_only),
]


@pytest.mark.parametrize("variable", UNCHANGED_ENVS)
@pytest.mark.parametrize("in_cwd", [False, True])
def test_an_env_left_to_subprocess_names_no_parameter(
    variable, in_cwd, stub, src, out_dir, tmp_path
):
    cwd = tmp_path if in_cwd else None
    env = {**os.environ, **variable}
    expected = directly(cwd, env)
    try:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            cwd=cwd,
            env=env,
        )
    except PASSED_ON as error:
        assert expected is not None
        if issubclass(expected, OSError):
            assert type(error) is CompilerNotStartedError
            assert type(error.__cause__) is expected
        else:
            assert type(error) is expected
        assert not hasattr(error, "parameter")
        assert names(out_dir) == []
    else:
        assert expected is None


@pytest.mark.parametrize("env", [[("A", "x")], 5, "A=x"])
def test_an_env_that_is_not_a_mapping_keeps_its_class(env, stub, src, out_dir):
    expected = directly(None, env)
    with pytest.raises(PASSED_ON) as caught:
        build(
            src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE), env=env
        )
    assert expected is not None
    assert type(caught.value) is expected
    assert not hasattr(caught.value, "parameter")
    assert not stub.started
    assert names(out_dir) == []


def test_a_type_error_of_env_items_names_env(stub, src, out_dir, monkeypatch):
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    given = TypeError("items refused")
    error = refused(compiler, src, out_dir, env=Items(given))
    assert error is given
    assert error.parameter == "env"


@pytest.mark.parametrize("given", [RuntimeError("broken"), LookupError("gone")])
def test_another_error_of_env_items_is_passed_on(
    given, stub, src, out_dir, monkeypatch
):
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    error = refused(compiler, src, out_dir, env=Items(given))
    assert error is given
    assert not hasattr(error, "parameter")


CWD_TYPES = [str, Path, pytest.param(os.fsencode, marks=posix_only)]


@pytest.mark.parametrize("as_type", CWD_TYPES)
def test_an_existing_cwd_is_where_the_compiler_runs(
    as_type, stub, src, out_dir, tmp_path
):
    work = tmp_path / "work"
    work.mkdir()
    result = build(
        src,
        out_dir / "kernel.o",
        timeout_s=TIMEOUT,
        compiler=stub(WRITE),
        cwd=as_type(str(work)),
    )
    assert result.ok
    assert os.path.samefile(stub.call()["cwd"], work)


REFUSED_CWDS = [
    3,
    IntPath(),
    "a\0b",
    Path("a\0b"),
    b"a\0b",
    pytest.param("a\ud800b", marks=posix_only),
]


@pytest.mark.parametrize("cwd", REFUSED_CWDS)
def test_a_refused_cwd_names_cwd_and_starts_nothing(
    cwd, stub, src, out_dir, monkeypatch
):
    expected = directly(cwd, None)
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    error = refused(compiler, src, out_dir, cwd=cwd)
    assert issubclass(expected, (TypeError, ValueError))
    assert type(error) is expected
    assert error.parameter == "cwd"
    assert not hasattr(error, "path_role")
    assert not stub.started


@posix_only
def test_a_lone_surrogate_cwd_is_a_value_error(stub, src, out_dir, monkeypatch):
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    error = refused(compiler, src, out_dir, cwd="a\ud800b")
    assert isinstance(error, ValueError)
    assert error.parameter == "cwd"


def test_the_type_error_of_fspath_names_cwd(stub, src, out_dir, monkeypatch):
    with pytest.raises(TypeError) as direct:
        os.fspath(IntPath())
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    error = refused(compiler, src, out_dir, cwd=IntPath())
    assert error.args == direct.value.args
    assert error.parameter == "cwd"


def absent_directory(tmp_path):
    return tmp_path / "absent"


def regular_file(tmp_path):
    path = tmp_path / "plain"
    path.write_text("not a directory", encoding="utf-8")
    return path


@pytest.mark.parametrize("make_cwd", [absent_directory, regular_file])
def test_an_unusable_cwd_is_still_a_failed_start(
    make_cwd, stub, src, out_dir, tmp_path
):
    with pytest.raises(CompilerNotStartedError) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            cwd=make_cwd(tmp_path),
        )
    assert isinstance(caught.value.__cause__, OSError)
    assert not hasattr(caught.value, "parameter")
    assert not hasattr(caught.value, "path_role")
    assert not hasattr(caught.value.__cause__, "parameter")
    assert not hasattr(caught.value.__cause__, "path_role")
    assert not stub.started
    assert names(out_dir) == []


@pytest.mark.parametrize("kind", [TypeError, ValueError])
def test_an_error_from_creating_the_process_with_env_and_cwd_has_no_parameter(
    kind, stub, src, out_dir, tmp_path, monkeypatch
):
    error = kind("cannot hand over")

    def popen(*args, **kwargs):
        raise error

    monkeypatch.setattr(clang_build.subprocess, "Popen", popen)
    with pytest.raises(kind) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            cwd=tmp_path,
            env=dict(os.environ),
        )
    assert caught.value is error
    assert not hasattr(caught.value, "parameter")
    assert names(out_dir) == []


@pytest.mark.parametrize(
    "kwargs",
    [{"timeout_s": 0}, {"compiler": ()}, {"flags": ("-o", "x.o")}],
)
def test_earlier_value_errors_come_before_env_and_cwd(kwargs, stub, src, out_dir):
    arguments = {"timeout_s": TIMEOUT, "compiler": stub(WRITE), **kwargs}
    with pytest.raises(ValueError) as caught:
        build(src, out_dir / "kernel.o", env={"A=B": "x"}, cwd="a\0b", **arguments)
    assert type(caught.value) is ValueError
    assert not hasattr(caught.value, "parameter")
    assert not stub.started


def test_a_missing_compiler_comes_before_the_env(src, out_dir):
    with pytest.raises(CompilerNotFoundError) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler="hilclaw-no-such-compiler",
            env={"A=B": "x"},
        )
    assert not hasattr(caught.value, "parameter")
    assert names(out_dir) == []


def test_a_compiler_type_error_comes_before_the_env(src, out_dir):
    with pytest.raises(TypeError) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=(sys.executable, 3),
            env={"A": 3},
        )
    assert caught.value.parameter == "compiler"


def test_the_env_is_named_before_the_cwd(stub, src, out_dir, monkeypatch):
    compiler = stub(WRITE)
    forbid_start(monkeypatch)
    error = refused(compiler, src, out_dir, env={"A=B": "x"}, cwd=3)
    assert type(error) is ValueError
    assert error.parameter == "env"


@pytest.mark.parametrize(
    "settings, kind, parameter",
    [
        ({"env": {"A=B": "x"}}, ValueError, "env"),
        ({"env": {"A": 3}}, TypeError, "env"),
        ({"cwd": "a\0b"}, ValueError, "cwd"),
    ],
)
def test_env_and_cwd_errors_keep_their_parameter_through_pickling(
    settings, kind, parameter, stub, src, out_dir
):
    with pytest.raises(kind) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            **settings,
        )
    loaded = pickle.loads(pickle.dumps(caught.value))
    assert type(loaded) is kind
    assert str(loaded) == str(caught.value)
    assert loaded.args == caught.value.args
    assert loaded.parameter == parameter


@pytest.mark.parametrize("keyword", ["flags", "trailing_flags"])
@pytest.mark.parametrize("value", ["-O2", b"-O2", ("-c", 1), ("-c", None), 5])
def test_flags_of_the_wrong_type(keyword, value, stub, src, out_dir):
    with pytest.raises(TypeError) as caught:
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            **{keyword: value},
        )
    assert not stub.started
    assert caught.value.parameter == keyword


@pytest.mark.parametrize("keyword", ["flags", "trailing_flags"])
@pytest.mark.parametrize("value", OUTPUT_FLAGS)
def test_flags_must_not_set_the_output(keyword, value, stub, src, out_dir):
    with pytest.raises(ValueError, match="must not set the output"):
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            **{keyword: ("-c", *value)},
        )
    assert not stub.started


@pytest.mark.parametrize("value", BAD_TIMEOUT_VALUES)
def test_timeout_must_be_positive_and_finite(value, stub, src, out_dir):
    with pytest.raises(ValueError):
        build(src, out_dir / "kernel.o", timeout_s=value, compiler=stub(WRITE))
    with pytest.raises(ValueError):
        compiler_version(stub(VERSION), timeout_s=value)
    assert not stub.started


@pytest.mark.parametrize("value", BAD_TIMEOUT_TYPES)
def test_timeout_must_be_a_number(value, stub, src, out_dir):
    with pytest.raises(TypeError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=value, compiler=stub(WRITE))
    assert caught.value.parameter == "timeout_s"
    with pytest.raises(TypeError) as caught:
        compiler_version(stub(VERSION), timeout_s=value)
    assert not hasattr(caught.value, "parameter")
    assert not stub.started


def test_timeout_has_no_default(stub, src, out_dir):
    with pytest.raises(TypeError) as caught:
        build(src, out_dir / "kernel.o", compiler=stub(WRITE))
    assert not hasattr(caught.value, "parameter")
    with pytest.raises(TypeError) as caught:
        compiler_version(stub(VERSION))
    assert not hasattr(caught.value, "parameter")
    assert not stub.started


@pytest.mark.parametrize("compiler", MISSING_COMPILERS)
def test_compiler_that_does_not_exist(compiler, src, out_dir):
    with pytest.raises(CompilerNotFoundError):
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=compiler)
    with pytest.raises(CompilerNotFoundError):
        compiler_version(compiler, timeout_s=TIMEOUT)
    assert names(out_dir) == []


def test_default_compiler_not_on_path(src, out_dir, monkeypatch):
    monkeypatch.setattr(clang_build.shutil, "which", lambda name: None)
    with pytest.raises(CompilerNotFoundError, match="clang"):
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT)
    with pytest.raises(CompilerNotFoundError, match="clang"):
        compiler_version(timeout_s=TIMEOUT)
    assert issubclass(CompilerNotFoundError, LookupError)


@pytest.mark.parametrize(
    "compiler, error",
    [
        ((), ValueError),
        ([], ValueError),
        ((sys.executable, 3), TypeError),
        (3, TypeError),
        (b"clang", TypeError),
    ],
)
def test_malformed_compiler_argument(compiler, error, src, out_dir):
    with pytest.raises(error) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=compiler)
    if error is TypeError:
        assert caught.value.parameter == "compiler"
    else:
        assert not hasattr(caught.value, "parameter")
    with pytest.raises(error) as caught:
        compiler_version(compiler, timeout_s=TIMEOUT)
    assert not hasattr(caught.value, "parameter")


def test_compiler_version_of_a_failing_compiler(stub):
    compiler = stub("print('broken install', file=sys.stderr); sys.exit(3)")
    with pytest.raises(RuntimeError, match="exited with 3: broken install"):
        compiler_version(compiler, timeout_s=TIMEOUT)


@pytest.mark.parametrize("body", ["pass", "print()", "print('   ')"])
def test_compiler_version_without_a_version_line(body, stub):
    with pytest.raises(RuntimeError, match="no version line"):
        compiler_version(stub(body), timeout_s=TIMEOUT)


def test_compiler_version_times_out(stub):
    before = time.monotonic()
    with pytest.raises(RuntimeError, match="did not finish"):
        compiler_version(stub("time.sleep(30)"), timeout_s=1)
    assert time.monotonic() - before < 15


def test_clang_builds_an_object_file(clang, src, out_dir):
    out = out_dir / "kernel.o"
    result = build(src, out, timeout_s=TIMEOUT, flags=("-c",))
    assert result.ok, result.log
    assert result.returncode == 0
    assert result.timed_out is False
    assert out.stat().st_size > 0
    assert os.path.samefile(result.command[0], shutil.which("clang"))
    assert str(src) in result.command
    assert "-o" in result.command
    assert names(out_dir) == ["kernel.o"]


@pytest.mark.skipif(os.name != "posix", reason="shared library flags are POSIX ones")
def test_clang_builds_a_shared_library(clang, src, out_dir):
    src.write_text(MATH_C, encoding="utf-8")
    out = out_dir / "libkernel.so"
    result = build(
        src,
        out,
        timeout_s=TIMEOUT,
        flags=("-shared", "-fPIC"),
        trailing_flags=("-lm",),
    )
    assert result.ok, result.log
    assert out.stat().st_size > 0
    assert names(out_dir) == ["libkernel.so"]


def test_clang_compile_error(clang, src, out_dir):
    src.write_text(BAD_C, encoding="utf-8")
    result = build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, flags=("-c",))
    assert result.ok is False
    assert result.returncode not in (0, None)
    assert "error" in result.log
    assert "kernel.c" in result.log
    assert names(out_dir) == []


def test_clang_exit_zero_without_artefact(clang, src, out_dir):
    result = build(
        src, out_dir / "kernel.o", timeout_s=TIMEOUT, flags=("-fsyntax-only",)
    )
    assert result.returncode == 0
    assert result.ok is False
    assert names(out_dir) == []


def test_clang_version(clang):
    line = compiler_version(timeout_s=TIMEOUT)
    assert "clang" in line
    assert "\n" not in line
    assert line == line.strip()
