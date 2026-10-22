import errno
import os
import re

import pytest

from hilclaw import local_run, standin_container
from hilclaw.standin_container import (
    CONTAINER_BUILD_DIR,
    NAME_PREFIX,
    ContainerResult,
    NoNumericUserError,
    Removal,
    run_in_container,
)

NAME = re.compile(re.escape(NAME_PREFIX) + r"[0-9a-f]{32}")
FORBIDDEN = {
    "--privileged",
    "--cap-add",
    "-v",
    "--volume",
    "-e",
    "--env",
    "--env-file",
    "-i",
    "-t",
    "-it",
    "--interactive",
    "--tty",
    "-p",
    "--publish",
    "-P",
    "--publish-all",
    "--memory",
    "-m",
    "--cpus",
    "--pids-limit",
    "--memory-swap",
    "-H",
    "--host",
    "--context",
    "-c",
    "--cpu-shares",
}


def result(returncode=0, *, timed_out=False, stdout=b"out", stderr=b"err"):
    def make(command):
        return local_run.RunResult(
            returncode=None if timed_out else returncode,
            timed_out=timed_out,
            stdout=stdout,
            stderr=stderr,
            command=("/usr/bin/docker", *command[1:]),
            duration_s=1.5,
            max_rss=4321,
        )

    return make


class Starts:
    def __init__(self):
        self.calls = []
        self.answers = []

    def __call__(self, command, **options):
        self.calls.append((list(command), options))
        answer = self.answers.pop(0) if self.answers else result()
        if isinstance(answer, BaseException):
            raise answer
        return answer(command)


@pytest.fixture(autouse=True)
def starts(monkeypatch):
    real = local_run.run
    stub = Starts()
    monkeypatch.setattr(local_run, "run", stub)
    assert standin_container.local_run.run is stub
    assert real is not stub
    return stub


@pytest.fixture(autouse=True)
def user(monkeypatch):
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)


@pytest.fixture
def build_dir(tmp_path):
    directory = tmp_path / "build"
    directory.mkdir()
    return directory


def call(build_dir, program="clang", arguments=(), **options):
    options.setdefault("timeout_s", 30)
    options.setdefault("removal_timeout_s", 10)
    return run_in_container(
        "example/standin:1", build_dir, program, arguments, **options
    )


def option(command, flag):
    before = command[: command.index("example/standin:1")]
    assert before.count(flag) == 1
    return before[before.index(flag) + 1]


def assert_client_list(command, build_dir, program, arguments):
    assert command[0] == "docker"
    assert command[1] == "run"
    image_at = command.index("example/standin:1")
    options = command[2:image_at]
    assert "--rm" in options
    assert NAME.fullmatch(option(command, "--name"))
    assert option(command, "--mount") == (
        f"type=bind,source={os.fspath(build_dir)},target={CONTAINER_BUILD_DIR}"
    )
    assert options.count("--mount") == 1
    assert option(command, "--workdir") == CONTAINER_BUILD_DIR
    assert option(command, "--network") == "none"
    assert option(command, "--pull") == "never"
    assert option(command, "--user") == "1234:567"
    assert option(command, "--cap-drop") == "ALL"
    assert option(command, "--security-opt") == "no-new-privileges=true"
    assert "--entrypoint=" in options
    assert command[image_at + 1 :] == [program, *arguments]
    flags = {item.split("=", 1)[0] for item in options if item.startswith("-")}
    assert not flags & FORBIDDEN
    assert not any("docker.sock" in item for item in options)
    assert set(flags) == {
        "--rm",
        "--name",
        "--mount",
        "--workdir",
        "--network",
        "--pull",
        "--user",
        "--cap-drop",
        "--security-opt",
        "--entrypoint",
    }


def test_build_like_call_starts_the_client_with_every_property(starts, build_dir):
    arguments = ["-std=gnu11", "-O2", "kernel/kernel.c", "-o", "check", "-lm"]
    call(build_dir, "clang", arguments, timeout_s=60)
    ((command, options),) = starts.calls
    assert_client_list(command, build_dir, "clang", arguments)
    assert options == {"timeout_s": 60, "env": None}


def test_process_like_call_keeps_program_and_arguments_in_order(starts, build_dir):
    arguments = ["--seed", "7", "-", "--rm", ""]
    call(os.fspath(build_dir), "./check", arguments)
    ((command, _),) = starts.calls
    assert_client_list(command, build_dir, "./check", arguments)


def test_normal_end_hands_back_the_client_outcome(starts, build_dir):
    starts.answers.append(result(3, stdout=b"\x00o", stderr=b"e\xff"))
    done = call(build_dir)
    assert isinstance(done, ContainerResult)
    ((command, _),) = starts.calls
    assert done.returncode == 3
    assert done.timed_out is False
    assert done.stdout == b"\x00o"
    assert done.stderr == b"e\xff"
    assert done.command == ("/usr/bin/docker", *command[1:])
    assert done.duration_s == 1.5
    assert done.name == option(command, "--name")
    assert done.removal is None
    assert not hasattr(done, "max_rss")
    assert 4321 not in done


@pytest.mark.parametrize("status", [125, 126, 127, 0])
def test_client_statuses_are_handed_back_unchanged(starts, build_dir, status):
    starts.answers.append(result(status))
    done = call(build_dir)
    assert done.returncode == status
    assert done.removal is None
    assert len(starts.calls) == 1


def test_two_calls_get_different_names(starts, build_dir):
    first = call(build_dir)
    second = call(build_dir)
    assert NAME.fullmatch(first.name)
    assert NAME.fullmatch(second.name)
    assert first.name != second.name


@pytest.mark.parametrize(
    ("removal", "expected"),
    [
        (result(0, stdout=b"name\n", stderr=b""), (0, False, b"name\n", b"")),
        (
            result(1, stdout=b"", stderr=b"No such container"),
            (1, False, b"", b"No such container"),
        ),
        (result(timed_out=True, stdout=b"", stderr=b"x"), (None, True, b"", b"x")),
    ],
)
def test_timeout_force_removes_the_container_once(starts, build_dir, removal, expected):
    starts.answers += [result(timed_out=True, stdout=b"part", stderr=b"e"), removal]
    done = call(build_dir, timeout_s=5, removal_timeout_s=2.5, client="podman-ish")
    (run_call, remove_call) = starts.calls
    assert remove_call == (
        ["podman-ish", "rm", "--force", done.name],
        {"timeout_s": 2.5, "env": None},
    )
    assert run_call[0][0] == "podman-ish"
    assert run_call[1] == {"timeout_s": 5, "env": None}
    assert done.timed_out is True
    assert done.returncode is None
    assert (done.stdout, done.stderr) == (b"part", b"e")
    assert isinstance(done.removal, Removal)
    removed = done.removal
    assert (
        removed.returncode,
        removed.timed_out,
        removed.stdout,
        removed.stderr,
    ) == expected
    assert removed.command == ("/usr/bin/docker", "rm", "--force", done.name)
    assert removed.duration_s == 1.5
    assert not hasattr(removed, "max_rss")


def test_an_exception_of_the_removal_is_passed_on(starts, build_dir):
    error = OSError(errno.EACCES, "denied")
    starts.answers += [result(timed_out=True), error]
    with pytest.raises(OSError) as raised:
        call(build_dir)
    assert raised.value is error
    assert len(starts.calls) == 2


@pytest.mark.parametrize(
    "error",
    [local_run.ProgramNotFoundError("docker"), OSError(errno.ENOEXEC, "bad")],
)
def test_client_start_errors_are_passed_on_without_removal(starts, build_dir, error):
    starts.answers.append(error)
    with pytest.raises(type(error)) as raised:
        call(build_dir)
    assert raised.value is error
    assert len(starts.calls) == 1


@pytest.mark.parametrize(
    ("image", "kind"),
    [
        (None, TypeError),
        (b"img", TypeError),
        ("", ValueError),
        ("-v", ValueError),
        ("--privileged", ValueError),
        ("img name", ValueError),
        ("img\tname", ValueError),
        ("img\n", ValueError),
        ("img\0", ValueError),
    ],
)
def test_image_refusals(starts, build_dir, image, kind):
    with pytest.raises(kind) as raised:
        run_in_container(image, build_dir, "clang", timeout_s=1, removal_timeout_s=1)
    assert type(raised.value) is kind
    assert raised.value.parameter == "image"
    assert starts.calls == []


class BytesPath:
    def __fspath__(self):
        return b"/tmp/build"


@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (None, TypeError),
        (b"/tmp/build", TypeError),
        (BytesPath(), TypeError),
        ("relative/build", ValueError),
        ("", ValueError),
    ],
)
def test_build_dir_type_and_form_refusals(starts, value, kind):
    with pytest.raises(kind) as raised:
        call(value)
    assert type(raised.value) is kind
    assert raised.value.parameter == "build_dir"
    assert starts.calls == []


@pytest.mark.parametrize("character", [",", '"', "\n", "\r", "\0"])
def test_build_dir_characters_a_mount_cannot_carry(starts, tmp_path, character):
    with pytest.raises(ValueError) as raised:
        call(os.fspath(tmp_path) + os.sep + "a" + character + "b")
    assert raised.value.parameter == "build_dir"
    assert starts.calls == []


def test_missing_build_dir_raises_the_stat_error(starts, tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError) as raised:
        call(missing)
    assert getattr(raised.value, "parameter", None) is None
    assert starts.calls == []


def test_build_dir_that_is_a_file(starts, tmp_path):
    file = tmp_path / "file"
    file.write_text("x")
    with pytest.raises(NotADirectoryError) as raised:
        call(file)
    assert raised.value.errno == errno.ENOTDIR
    assert raised.value.filename == os.fspath(file)
    assert starts.calls == []


@pytest.mark.parametrize(
    ("program", "kind"),
    [(None, TypeError), (["clang"], TypeError), ("", ValueError), ("a\0", ValueError)],
)
def test_program_refusals(starts, build_dir, program, kind):
    with pytest.raises(kind) as raised:
        call(build_dir, program)
    assert type(raised.value) is kind
    assert raised.value.parameter == "program"
    assert starts.calls == []


@pytest.mark.parametrize(
    ("arguments", "kind"),
    [
        ("-O2", TypeError),
        (b"-O2", TypeError),
        (["-O2", 3], TypeError),
        ([b"-O2"], TypeError),
        (None, TypeError),
        (["a\0b"], ValueError),
    ],
)
def test_argument_refusals(starts, build_dir, arguments, kind):
    with pytest.raises(kind) as raised:
        call(build_dir, "clang", arguments)
    assert type(raised.value) is kind
    assert raised.value.parameter == "arguments"
    assert starts.calls == []


def test_arguments_from_an_iterator_are_used_once(starts, build_dir):
    call(build_dir, "clang", iter(["-c", "k.c"]))
    ((command, _),) = starts.calls
    assert command[-3:] == ["clang", "-c", "k.c"]


@pytest.mark.parametrize("parameter", ["timeout_s", "removal_timeout_s"])
@pytest.mark.parametrize(
    ("value", "kind"),
    [
        (None, TypeError),
        ("5", TypeError),
        (True, TypeError),
        (0, ValueError),
        (-1, ValueError),
        (float("inf"), ValueError),
        (float("nan"), ValueError),
    ],
)
def test_time_limit_refusals(starts, build_dir, parameter, value, kind):
    with pytest.raises(kind) as raised:
        call(build_dir, **{parameter: value})
    assert type(raised.value) is kind
    assert raised.value.parameter == parameter
    assert starts.calls == []


def test_removal_limit_is_required(starts, build_dir):
    with pytest.raises(TypeError):
        run_in_container("img", build_dir, "clang", timeout_s=1)
    assert starts.calls == []


@pytest.mark.parametrize("missing", ["getuid", "getgid"])
def test_no_numeric_user_refuses_before_any_start(
    starts, build_dir, monkeypatch, missing
):
    monkeypatch.delattr(os, missing, raising=False)
    with pytest.raises(NoNumericUserError):
        call(build_dir)
    assert starts.calls == []


def test_no_numeric_user_comes_before_the_directory_test(starts, tmp_path, monkeypatch):
    monkeypatch.delattr(os, "getuid", raising=False)
    with pytest.raises(NoNumericUserError):
        call(tmp_path / "missing")
    assert starts.calls == []


@pytest.mark.parametrize(
    ("client", "kind"),
    [(None, TypeError), (["docker"], TypeError), ("", ValueError), ("d\0", ValueError)],
)
def test_client_refusals(starts, build_dir, client, kind):
    with pytest.raises(kind) as raised:
        call(build_dir, client=client)
    assert type(raised.value) is kind
    assert raised.value.parameter == "client"
    assert starts.calls == []


@pytest.mark.parametrize("error", [TypeError("x"), ValueError("y")])
def test_pre_start_refusals_of_local_run_are_passed_on_without_removal(
    starts, build_dir, error
):
    starts.answers.append(error)
    with pytest.raises(type(error)) as raised:
        call(build_dir)
    assert raised.value is error
    assert not hasattr(error, "container_name")
    assert len(starts.calls) == 1


@pytest.mark.parametrize(
    "error", [OverflowError("too long"), KeyboardInterrupt(), RuntimeError("x")]
)
def test_an_exception_after_the_start_force_removes_the_container(
    starts, build_dir, error
):
    starts.answers += [error, result(1, stdout=b"", stderr=b"gone")]
    with pytest.raises(type(error)) as raised:
        call(build_dir, removal_timeout_s=3)
    assert raised.value is error
    (run_call, remove_call) = starts.calls
    name = option(run_call[0], "--name")
    assert remove_call == (
        ["docker", "rm", "--force", name],
        {"timeout_s": 3, "env": None},
    )
    assert error.container_name == name
    assert error.removal == Removal(
        returncode=1,
        timed_out=False,
        stdout=b"",
        stderr=b"gone",
        command=("/usr/bin/docker", "rm", "--force", name),
        duration_s=1.5,
    )


@pytest.mark.parametrize(
    "failure",
    [OSError(errno.EACCES, "denied"), local_run.ProgramNotFoundError("docker")],
)
def test_a_failed_removal_after_an_exception_is_noted(starts, build_dir, failure):
    error = OverflowError("too long")
    starts.answers += [error, failure]
    with pytest.raises(OverflowError) as raised:
        call(build_dir)
    assert raised.value is error
    assert error.removal is None
    assert error.container_name in error.__notes__[0]
    assert repr(failure) in error.__notes__[0]
    assert len(starts.calls) == 2
