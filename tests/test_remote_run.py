import json
import math
import os
import shutil
import sys

import pytest

from hilclaw import local_run, toolchain_check
from hilclaw.remote_run import (
    CONNECT_TIMEOUT_S,
    DESTINATION_VARIABLE,
    PLACEHOLDER,
    SSH,
    SSH_FAILURE,
    TASK_ROOT,
    NotConfiguredError,
    RemoteResult,
    configured,
    destination,
    get,
    make_task_directory,
    put,
    quote,
    remote_path,
    remove_task_directory,
    run,
    task_directory,
)

DEST = "tester@host.invalid"
ENV = {DESTINATION_VARIABLE: DEST}
needs_sh = pytest.mark.skipif(shutil.which("sh") is None, reason="no POSIX sh")

# A stub ssh: it records its arguments, answers as told by answer.json beside
# it, and otherwise runs the remote command string with the local sh in a
# fake home directory, as the remote account's shell would.
SSH_STUB = """\
import json, os, subprocess, sys, time
here = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[1:]
with open(os.path.join(here, "calls.jsonl"), "a", encoding="utf-8") as log:
    log.write(json.dumps(args) + "\\n")
answer = {}
if os.path.exists(os.path.join(here, "answer.json")):
    with open(os.path.join(here, "answer.json"), encoding="utf-8") as source:
        answer = json.load(source)
target = args[args.index("--") + 1]
if answer.get("hang"):
    time.sleep(60)
if "status" in answer:
    sys.stdout.write("out " + target)
    sys.stderr.write("ssh: connect to host " + target + ": refused")
    sys.exit(answer["status"])
home = os.path.join(here, "home")
os.makedirs(home, exist_ok=True)
sys.stdout.flush()
sys.exit(subprocess.run(["sh", "-c", args[-1]], cwd=home).returncode)
"""


@pytest.fixture
def stub(tmp_path):
    directory = tmp_path / "ssh"
    directory.mkdir()
    path = directory / "ssh_stub.py"
    path.write_text(SSH_STUB, encoding="utf-8")

    class Stub:
        program = (sys.executable, str(path))
        home = directory / "home"

        def answer(self, **values):
            (directory / "answer.json").write_text(json.dumps(values), encoding="utf-8")

        def calls(self):
            log = directory / "calls.jsonl"
            if not log.exists():
                return []
            return [json.loads(line) for line in log.read_text().splitlines()]

    return Stub()


def leaks(value):
    text = repr(value)
    return DEST in text or "host.invalid" in text or "tester" in text


def test_constants():
    assert DESTINATION_VARIABLE == "HILCLAW_AARCH64_SSH"
    assert PLACEHOLDER == "<destination>"
    assert SSH == ("ssh",)
    assert (CONNECT_TIMEOUT_S, SSH_FAILURE, TASK_ROOT) == (15, 255, "hilclaw-driver")


def test_destination_is_read_from_the_variable():
    assert destination(ENV) == DEST
    assert configured(ENV)


def test_destination_defaults_to_the_process_environment(monkeypatch):
    monkeypatch.setenv(DESTINATION_VARIABLE, "alias")
    assert destination() == "alias"
    monkeypatch.delenv(DESTINATION_VARIABLE)
    assert not configured()


@pytest.mark.parametrize("environ", [{}, {DESTINATION_VARIABLE: ""}])
def test_an_unset_destination_is_not_configured(environ):
    with pytest.raises(NotConfiguredError, match=DESTINATION_VARIABLE):
        destination(environ)
    assert not configured(environ)


@pytest.mark.parametrize(
    "value", ["-oProxyCommand=x", "a b", "a\tb", "host\n", "höst", "a\x7fb"]
)
def test_a_destination_that_could_be_an_option_or_split_is_refused(value):
    with pytest.raises(ValueError) as caught:
        destination({DESTINATION_VARIABLE: value})
    assert value not in str(caught.value)
    assert not configured({DESTINATION_VARIABLE: value})


@pytest.mark.parametrize(
    ("argument", "quoted"),
    [("a", "'a'"), ("", "''"), ("a b", "'a b'"), ("it's", "'it'\"'\"'s'")],
)
def test_quote(argument, quoted):
    assert quote(argument) == quoted


@needs_sh
def test_arguments_reach_the_remote_program_as_words(stub):
    words = ["a b", "it's", 'say "hi"', "$HOME", "*", "", "-n", "x;y|z"]
    done = run(["printf", "[%s]", *words], timeout_s=30, environ=ENV, ssh=stub.program)
    assert done == RemoteResult(
        returncode=0,
        timed_out=False,
        stdout="".join(f"[{word}]" for word in words).encode(),
        stderr=b"",
        command=done.command,
        duration_s=done.duration_s,
        ssh_failed=False,
    )
    assert done.duration_s >= 0


def test_the_command_hides_the_destination_and_keeps_host_key_checks(stub):
    stub.answer(status=0)
    done = run(["true"], timeout_s=30, environ=ENV, ssh=stub.program)
    (call,) = stub.calls()
    assert call == [
        "-q",
        "-T",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "--",
        DEST,
        "'true'",
    ]
    assert done.command == (*stub.program, *call[:-2], PLACEHOLDER, "'true'")
    assert not any("StrictHostKeyChecking" in part for part in call)
    assert not any("KnownHostsFile" in part for part in call)


@needs_sh
def test_a_remote_non_zero_exit_is_the_programs_status(stub):
    done = run(
        ["sh", "-c", "echo out; echo err >&2; exit 3"],
        timeout_s=30,
        environ=ENV,
        ssh=stub.program,
    )
    assert (done.returncode, done.timed_out, done.ssh_failed) == (3, False, False)
    assert (done.stdout.strip(), done.stderr.strip()) == (b"out", b"err")


def test_an_ssh_failure_drops_its_output_and_names_no_destination(stub):
    stub.answer(status=255)
    done = run(["true"], timeout_s=30, environ=ENV, ssh=stub.program)
    assert (done.returncode, done.timed_out, done.ssh_failed) == (None, False, True)
    assert (done.stdout, done.stderr) == (b"", b"")
    assert not leaks(done)


def test_another_status_of_ssh_is_passed_on(stub):
    stub.answer(status=254)
    done = run(["true"], timeout_s=30, environ=ENV, ssh=stub.program)
    assert (done.returncode, done.ssh_failed) == (254, False)


def test_a_timeout_is_a_result(stub):
    stub.answer(hang=True)
    done = run(["true"], timeout_s=0.5, environ=ENV, ssh=stub.program)
    assert (done.returncode, done.timed_out, done.ssh_failed) == (None, True, False)
    assert not leaks(done)


@needs_sh
def test_standard_input_reaches_the_remote_program(stub):
    done = run(["cat"], timeout_s=30, environ=ENV, ssh=stub.program, stdin_data=b"x\0y")
    assert done.stdout == b"x\0y"


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ([], ValueError),
        ((), ValueError),
        ("ls", TypeError),
        (b"ls", TypeError),
        (["ls", 1], TypeError),
        ([None], TypeError),
        (["ls", "a\0b"], ValueError),
    ],
)
def test_a_refused_argument_list_starts_nothing(stub, arguments, error):
    with pytest.raises(error):
        run(arguments, timeout_s=30, environ=ENV, ssh=stub.program)
    assert stub.calls() == []


@pytest.mark.parametrize(
    ("timeout_s", "error"),
    [
        (0, ValueError),
        (-1, ValueError),
        (math.nan, ValueError),
        (math.inf, ValueError),
        (True, TypeError),
        ("1", TypeError),
        (None, TypeError),
    ],
)
def test_a_refused_time_limit_starts_nothing(stub, timeout_s, error):
    with pytest.raises(error):
        run(["true"], timeout_s=timeout_s, environ=ENV, ssh=stub.program)
    assert stub.calls() == []


def test_an_unset_destination_starts_nothing(stub):
    with pytest.raises(NotConfiguredError):
        run(["true"], timeout_s=30, environ={}, ssh=stub.program)
    assert stub.calls() == []


def test_a_refused_destination_starts_nothing_and_is_not_repeated(stub):
    with pytest.raises(ValueError) as caught:
        run(
            ["true"],
            timeout_s=30,
            environ={DESTINATION_VARIABLE: "-x"},
            ssh=stub.program,
        )
    assert "-x" not in str(caught.value)
    assert stub.calls() == []


def test_an_ssh_program_given_as_one_string_is_refused(stub):
    with pytest.raises(TypeError):
        run(["true"], timeout_s=30, environ=ENV, ssh="ssh")


def test_a_missing_ssh_program_is_not_found(tmp_path):
    with pytest.raises(local_run.ProgramNotFoundError) as caught:
        run(["true"], timeout_s=30, environ=ENV, ssh=(str(tmp_path / "no-ssh"),))
    assert not leaks(caught.value)


def test_task_directory_and_remote_path():
    assert task_directory("T-0567") == "hilclaw-driver/T-0567"
    assert remote_path("T-0567", "a/b-1_c.txt") == "hilclaw-driver/T-0567/a/b-1_c.txt"
    assert remote_path("T-0567", "-x") == "hilclaw-driver/T-0567/-x"


@pytest.mark.parametrize(
    ("task", "error"),
    [
        ("T-1", ValueError),
        ("t-0001", ValueError),
        ("T-00001", ValueError),
        ("../T-0001", ValueError),
        ("T-0001/", ValueError),
        ("", ValueError),
        (1, TypeError),
        (None, TypeError),
    ],
)
def test_a_refused_task_id(stub, tmp_path, task, error):
    with pytest.raises(error):
        task_directory(task)
    with pytest.raises(error):
        make_task_directory(task, timeout_s=30, environ=ENV, ssh=stub.program)
    with pytest.raises(error):
        remove_task_directory(task, timeout_s=30, environ=ENV, ssh=stub.program)
    with pytest.raises(error):
        get(task, "f", tmp_path / "f", timeout_s=30, environ=ENV, ssh=stub.program)
    assert stub.calls() == []


@pytest.mark.parametrize(
    ("relative", "error"),
    [
        ("", ValueError),
        ("/etc/passwd", ValueError),
        ("..", ValueError),
        ("../x", ValueError),
        ("a/../../b", ValueError),
        (".", ValueError),
        ("a/./b", ValueError),
        ("a//b", ValueError),
        ("a/", ValueError),
        ("a\\b", ValueError),
        ("a b", ValueError),
        ("~/x", ValueError),
        ("$HOME", ValueError),
        (3, TypeError),
    ],
)
def test_a_path_that_leaves_the_task_directory_is_refused(
    stub, tmp_path, relative, error
):
    local = tmp_path / "local.bin"
    local.write_bytes(b"x")
    with pytest.raises(error):
        remote_path("T-0001", relative)
    with pytest.raises(error):
        put(local, "T-0001", relative, timeout_s=30, environ=ENV, ssh=stub.program)
    with pytest.raises(error):
        get(
            "T-0001",
            relative,
            tmp_path / "f",
            timeout_s=30,
            environ=ENV,
            ssh=stub.program,
        )
    assert stub.calls() == []


@needs_sh
def test_task_directory_lifecycle_and_copies(stub, tmp_path):
    common = {"timeout_s": 30, "environ": ENV, "ssh": stub.program}
    assert make_task_directory("T-0001", **common).returncode == 0
    assert (stub.home / "hilclaw-driver" / "T-0001").is_dir()
    assert make_task_directory("T-0001", **common).returncode == 0
    local = tmp_path / "kernel.c"
    payload = bytes(range(256)) * 3
    local.write_bytes(payload)
    assert put(local, "T-0001", "kernel.c", **common).returncode == 0
    assert (
        stub.home / "hilclaw-driver" / "T-0001" / "kernel.c"
    ).read_bytes() == payload
    back = tmp_path / "back.c"
    done = get("T-0001", "kernel.c", back, **common)
    assert (done.returncode, done.stdout) == (0, payload)
    assert back.read_bytes() == payload
    assert remove_task_directory("T-0001", **common).returncode == 0
    assert not (stub.home / "hilclaw-driver" / "T-0001").exists()
    assert (stub.home / "hilclaw-driver").is_dir()
    commands = [call[-1] for call in stub.calls()]
    assert commands[0] == "'mkdir' '-p' '--' 'hilclaw-driver/T-0001'"
    assert commands[-1] == "'rm' '-r' '--' 'hilclaw-driver/T-0001'"
    assert commands[2] == (
        "'sh' '-c' 'cat > \"$1\"' 'sh' 'hilclaw-driver/T-0001/kernel.c'"
    )


@needs_sh
def test_get_of_a_missing_file_writes_nothing(stub, tmp_path):
    back = tmp_path / "back"
    done = get("T-0001", "missing", back, timeout_s=30, environ=ENV, ssh=stub.program)
    assert done.returncode != 0
    assert not back.exists()


@needs_sh
def test_put_into_a_missing_directory_fails_remotely(stub, tmp_path):
    local = tmp_path / "f"
    local.write_bytes(b"x")
    done = put(local, "T-0002", "f", timeout_s=30, environ=ENV, ssh=stub.program)
    assert done.returncode not in (0, None)
    assert not done.ssh_failed


def test_put_of_a_missing_local_file_starts_nothing(stub, tmp_path):
    with pytest.raises(FileNotFoundError):
        put(
            tmp_path / "nope",
            "T-0001",
            "f",
            timeout_s=30,
            environ=ENV,
            ssh=stub.program,
        )
    assert stub.calls() == []


def test_removal_after_an_ssh_failure_is_a_result(stub):
    stub.answer(status=255)
    done = remove_task_directory("T-0001", timeout_s=30, environ=ENV, ssh=stub.program)
    assert done.ssh_failed
    assert not leaks(done)


@pytest.mark.skipif(
    not configured(os.environ), reason=f"{DESTINATION_VARIABLE} is not configured"
)
def test_the_real_machine_round_trip(tmp_path):
    task = "T-0567"
    common = {"timeout_s": 120}
    report = toolchain_check.remote_check()
    assert report["state"] == toolchain_check.READ
    assert report["system"]["kernel"]["state"] == "present"
    assert destination() not in json.dumps(report)
    made = make_task_directory(task, **common)
    assert made.returncode == 0, made.stderr
    try:
        local = tmp_path / "probe.bin"
        local.write_bytes(b"hilclaw remote probe\n\0\xff")
        assert put(local, task, "probe.bin", **common).returncode == 0
        back = tmp_path / "back.bin"
        assert get(task, "probe.bin", back, **common).returncode == 0
        assert back.read_bytes() == local.read_bytes()
    finally:
        removed = remove_task_directory(task, **common)
    assert removed.returncode == 0
    gone = run(["test", "-e", task_directory(task)], **common)
    assert gone.returncode == 1
    for done in (made, removed, gone):
        assert destination() not in repr(done)
