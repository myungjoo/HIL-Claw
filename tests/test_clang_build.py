import errno
import json
import os
import pickle
import shutil
import sys
import time
from pathlib import Path

import pytest

from hilclaw import clang_build
from hilclaw.clang_build import (
    DEFAULT_COMPILER,
    ArtefactNotCheckedError,
    ArtefactNotPlacedError,
    BuildResult,
    CompilerNotFoundError,
    CompilerNotStartedError,
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
    assert calls == []
    assert names(out_dir) == []


@pytest.fixture
def failing_communicate(monkeypatch):
    processes = []
    error = OSError(errno.EIO, "input/output error")

    class Popen(clang_build.subprocess.Popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            processes.append(self)

        def communicate(self, *args, **kwargs):
            if not getattr(self, "failed", False):
                self.failed = True
                raise error
            return super().communicate(*args, **kwargs)

    monkeypatch.setattr(clang_build.subprocess, "Popen", Popen)
    return processes, error


def test_error_after_the_start_is_passed_on(stub, src, out_dir, failing_communicate):
    processes, error = failing_communicate
    before = time.monotonic()
    with pytest.raises(OSError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert time.monotonic() - before < 20
    assert caught.value is error
    assert not isinstance(caught.value, (CompilerNotStartedError, *FILE_ERRORS))
    assert not hasattr(caught.value, "result")
    (process,) = processes
    assert process.poll() is not None
    assert process.returncode != 0
    assert process.stdout.closed
    assert names(out_dir) == []


def test_failed_removal_after_an_error_after_the_start(
    stub, src, out_dir, failing_communicate, failing_unlink
):
    processes, error = failing_communicate
    with pytest.raises(PermissionError) as caught:
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(SLEEP))
    assert caught.value is failing_unlink[0]
    assert caught.value.__context__ is error
    assert not isinstance(caught.value, (CompilerNotStartedError, *FILE_ERRORS))
    assert not hasattr(caught.value, "result")
    assert processes[0].poll() is not None


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
    with pytest.raises(error):
        build(sources, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert not stub.started
    assert names(out_dir) == []


def test_missing_output_directory(stub, src, tmp_path):
    with pytest.raises(FileNotFoundError):
        build(
            src,
            tmp_path / "absent" / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
        )
    assert not stub.started
    assert not (tmp_path / "absent").exists()


def test_output_parent_is_a_regular_file(stub, src, out_dir):
    blocker = out_dir / "file"
    blocker.write_bytes(b"x")
    with pytest.raises(NotADirectoryError):
        build(src, blocker / "kernel.o", timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert not stub.started


def test_output_is_a_directory(stub, src, out_dir):
    with pytest.raises(IsADirectoryError):
        build(src, out_dir, timeout_s=TIMEOUT, compiler=stub(WRITE))
    assert not stub.started
    assert names(out_dir) == []


@pytest.mark.parametrize("keyword", ["flags", "trailing_flags"])
@pytest.mark.parametrize("value", ["-O2", b"-O2", ("-c", 1), ("-c", None), 5])
def test_flags_of_the_wrong_type(keyword, value, stub, src, out_dir):
    with pytest.raises(TypeError):
        build(
            src,
            out_dir / "kernel.o",
            timeout_s=TIMEOUT,
            compiler=stub(WRITE),
            **{keyword: value},
        )
    assert not stub.started


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
    with pytest.raises(TypeError):
        build(src, out_dir / "kernel.o", timeout_s=value, compiler=stub(WRITE))
    with pytest.raises(TypeError):
        compiler_version(stub(VERSION), timeout_s=value)
    assert not stub.started


def test_timeout_has_no_default(stub, src, out_dir):
    with pytest.raises(TypeError):
        build(src, out_dir / "kernel.o", compiler=stub(WRITE))
    with pytest.raises(TypeError):
        compiler_version(stub(VERSION))
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
    with pytest.raises(error):
        build(src, out_dir / "kernel.o", timeout_s=TIMEOUT, compiler=compiler)
    with pytest.raises(error):
        compiler_version(compiler, timeout_s=TIMEOUT)


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
