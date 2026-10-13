import json
import os
import shutil
import signal
import sys
import time

import pytest

from hilclaw import selfcheck_login
from hilclaw.selfcheck_login import (
    AUTH_METHOD_NONE,
    AUTH_METHOD_OTHER,
    AUTH_METHODS,
    LOGIN_INSTRUCTION,
    LOGIN_UNREADABLE,
    NO_CLAUDE,
    NOT_LOGGED_IN,
    LoginStatus,
    read,
)

PRELUDE = """\
import json, os, signal, sys, time
from pathlib import Path
call = {
    "argv": sys.argv[1:],
    "cwd": os.getcwd(),
    "mark": os.environ.get("HILCLAW_TEST_MARK"),
    "stdin": sys.stdin.read(),
}
with Path(__file__).with_name("started.ndjson").open("a", encoding="utf-8") as record:
    record.write(json.dumps(call) + "\\n")
out, err = sys.stdout.buffer, sys.stderr.buffer
"""
TIMEOUT = 60
ACCOUNT = "alice-the-account"
EMAIL = "alice@example.com"
CONFIG_DIR = "/home/alice-the-user/.claude"
SECRETS = (ACCOUNT, EMAIL, CONFIG_DIR, "alice-the-user")
STDERR = f"warning: {ACCOUNT} <{EMAIL}> reads {CONFIG_DIR}\n".encode()
K2_OUTPUT = b'{\n  "loggedIn": false,\n  "authMethod": "none"\n}\n'
LOGGED_IN_METHODS = [method for method in AUTH_METHODS if method != "none"]
UNLISTED_METHODS = ["sso", "None", " none", "", "other", EMAIL, "x" * 10_000]
BAD_TIMEOUT_VALUES = [0, -1, -0.5, 0.0, float("nan"), float("inf")]
BAD_TIMEOUT_TYPES = [None, True, False, "10", [1], 1 + 0j]

posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX behaviour")


def status_output(method, **more):
    members = {
        "loggedIn": True,
        "authMethod": method,
        "email": EMAIL,
        "orgName": ACCOUNT,
        "configDirectory": CONFIG_DIR,
        **more,
    }
    return json.dumps(members, indent=2).encode() + b"\n"


class Stub:
    def __init__(self, directory):
        self.directory = directory
        self.record = directory / "started.ndjson"

    def install(self, body):
        script = self.directory / "stub.py"
        script.write_text(PRELUDE + body + "\n", encoding="utf-8")
        if os.name == "posix":
            launcher = self.directory / "claude"
            launcher.write_text(
                f"#!/bin/sh\nexec '{sys.executable}' '{script}' \"$@\"\n",
                encoding="utf-8",
            )
            launcher.chmod(0o755)
        else:
            launcher = self.directory / "claude.cmd"
            launcher.write_text(
                f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
            )
        assert os.path.samefile(shutil.which("claude"), launcher)

    def answers(self, stdout=b"", code=0, stderr=STDERR):
        self.install(
            f"out.write({stdout!r}); err.write({stderr!r})\n"
            f"out.flush(); err.flush(); sys.exit({code})"
        )

    def calls(self):
        if not self.record.exists():
            return []
        lines = self.record.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]


@pytest.fixture(autouse=True)
def stub(tmp_path, monkeypatch):
    directory = tmp_path / "bin"
    work = tmp_path / "work"
    directory.mkdir()
    work.mkdir()
    monkeypatch.setenv("PATH", str(directory))
    monkeypatch.chdir(work)
    assert shutil.which("claude") is None
    return Stub(directory)


def assert_nothing_leaked(status, capfd):
    captured = capfd.readouterr()
    for text in (repr(status), str(tuple(status)), captured.out, captured.err):
        for secret in SECRETS:
            assert secret not in text
    assert (captured.out, captured.err) == ("", "")


def test_outcome_words_are_those_of_the_record():
    assert NO_CLAUDE == "no_claude"
    assert NOT_LOGGED_IN == "not_logged_in"
    assert LOGIN_UNREADABLE == "login_unreadable"


def test_auth_methods_are_the_six_documented_values():
    assert AUTH_METHODS == (
        "none",
        "claude.ai",
        "oauth_token",
        "api_key",
        "api_key_helper",
        "third_party",
    )
    assert AUTH_METHOD_NONE == "none"
    assert AUTH_METHOD_OTHER == "other"
    assert AUTH_METHOD_OTHER not in AUTH_METHODS


def test_instruction_names_the_login_command():
    assert "claude auth login" in LOGIN_INSTRUCTION
    assert len(LOGIN_INSTRUCTION) < 200
    assert "\n" not in LOGIN_INSTRUCTION


def test_result_fields():
    assert LoginStatus._fields == ("outcome", "auth_method", "returncode", "timed_out")


def test_public_names():
    public = {name for name in vars(selfcheck_login) if not name.startswith("_")}
    assert public - {"json", "os", "NamedTuple", "local_run"} == {
        "AUTH_METHODS",
        "AUTH_METHOD_NONE",
        "AUTH_METHOD_OTHER",
        "LOGIN_INSTRUCTION",
        "LOGIN_UNREADABLE",
        "LoginStatus",
        "NOT_LOGGED_IN",
        "NO_CLAUDE",
        "read",
    }


@pytest.mark.parametrize("method", LOGGED_IN_METHODS)
def test_logged_in_with_a_documented_method(method, stub, monkeypatch, capfd):
    monkeypatch.setenv("HILCLAW_TEST_MARK", "marked")
    stub.answers(status_output(method))
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(None, method, 0, False)
    assert isinstance(status, LoginStatus)
    (call,) = stub.calls()
    assert call["argv"] == ["auth", "status"]
    assert call["stdin"] == ""
    assert call["mark"] == "marked"
    assert_nothing_leaked(status, capfd)


@pytest.mark.parametrize("method", UNLISTED_METHODS)
def test_logged_in_with_an_unlisted_method_carries_other(method, stub, capfd):
    stub.answers(status_output(method))
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(None, "other", 0, False)
    assert len(stub.calls()) == 1
    assert_nothing_leaked(status, capfd)


def test_white_space_around_the_object_is_allowed(stub):
    stub.answers(b' \r\n\t{"authMethod": "claude.ai"} \n\n')
    assert read(timeout_s=TIMEOUT) == LoginStatus(None, "claude.ai", 0, False)


def test_the_size_of_a_number_does_not_matter(stub):
    stub.answers(b'{"authMethod": "claude.ai", "n": ' + b"9" * 10_000 + b"}")
    assert read(timeout_s=TIMEOUT) == LoginStatus(None, "claude.ai", 0, False)


def test_other_members_are_not_read(stub):
    stub.answers(status_output("oauth_token", loggedIn=False))
    assert read(timeout_s=TIMEOUT).outcome is None


def test_cwd_is_handed_on(stub, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    stub.answers(status_output("claude.ai"))
    assert read(timeout_s=TIMEOUT, cwd=elsewhere).outcome is None
    assert read(timeout_s=TIMEOUT, cwd=str(elsewhere)).outcome is None
    first, second = stub.calls()
    assert os.path.samefile(first["cwd"], elsewhere)
    assert os.path.samefile(second["cwd"], elsewhere)


def test_cwd_is_inherited_by_default(stub, tmp_path):
    stub.answers(status_output("claude.ai"))
    assert read(timeout_s=TIMEOUT).outcome is None
    (call,) = stub.calls()
    assert os.path.samefile(call["cwd"], tmp_path / "work")


def test_timeout_accepts_int_and_float(stub):
    stub.answers(status_output("claude.ai"))
    assert read(timeout_s=60).outcome is None
    assert read(timeout_s=60.5).outcome is None


@pytest.mark.parametrize(
    "output, method",
    [
        (K2_OUTPUT, "none"),
        (b"", None),
        (b"Not logged in. Run claude auth login.\n", None),
        (status_output("claude.ai"), "claude.ai"),
        (status_output("sso"), "other"),
    ],
)
def test_exit_status_one_is_not_logged_in(output, method, stub, capfd):
    stub.answers(output, code=1)
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(NOT_LOGGED_IN, method, 1, False)
    assert len(stub.calls()) == 1
    assert_nothing_leaked(status, capfd)


UNREADABLE_OUTPUTS = {
    "method none": (status_output("none"), "none"),
    "the observed not-logged-in output": (K2_OUTPUT, "none"),
    "no output": (b"", None),
    "white space only": (b" \n", None),
    "text": (f"Logged in as {EMAIL}\n".encode(), None),
    "array": (b'[{"authMethod": "claude.ai"}]', None),
    "array of pairs": (b'[["authMethod", "claude.ai"]]', None),
    "string": (b'"claude.ai"', None),
    "number": (b"0", None),
    "null": (b"null", None),
    "true": (b"true", None),
    "empty object": (b"{}", None),
    "no authMethod": (b'{"loggedIn": true, "email": "alice@example.com"}', None),
    "other spelling": (b'{"authmethod": "claude.ai", "auth_method": "x"}', None),
    "nested only": (b'{"auth": {"authMethod": "claude.ai"}}', None),
    "method number": (b'{"authMethod": 1}', None),
    "method null": (b'{"authMethod": null}', None),
    "method true": (b'{"authMethod": true}', None),
    "method list": (b'{"authMethod": ["claude.ai"]}', None),
    "method object": (b'{"authMethod": {"authMethod": "claude.ai"}}', None),
    "invalid utf-8": (b'{"authMethod": "claude.ai", "name": "caf\xe9"}', None),
    "utf-16": ('{"authMethod": "claude.ai"}'.encode("utf-16"), None),
    "byte order mark": (b'\xef\xbb\xbf{"authMethod": "claude.ai"}', None),
    "two values": (b'{"authMethod": "claude.ai"}\n{"authMethod": "claude.ai"}', None),
    "trailing text": (b'{"authMethod": "claude.ai"} ok', None),
    "truncated": (b'{"authMethod": "claude.ai"', None),
    "duplicate key": (b'{"authMethod": "none", "authMethod": "claude.ai"}', None),
    "duplicate key, same": (
        b'{"authMethod": "api_key", "authMethod": "api_key"}',
        None,
    ),
    "NaN": (b'{"authMethod": "claude.ai", "n": NaN}', None),
    "Infinity": (b'{"authMethod": "claude.ai", "n": [-Infinity]}', None),
    "too deep": (b'{"authMethod": "claude.ai", "n": ' + b"[" * 200_000, None),
    "too deep, closed": (
        b'{"authMethod": "claude.ai", "n": ' + b"[" * 200_000 + b"]" * 200_000 + b"}",
        None,
    ),
}


@pytest.mark.parametrize(
    "output, method", UNREADABLE_OUTPUTS.values(), ids=UNREADABLE_OUTPUTS.keys()
)
def test_exit_status_zero_with_another_output_is_unreadable(
    output, method, stub, capfd
):
    stub.answers(output)
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(LOGIN_UNREADABLE, method, 0, False)
    assert len(stub.calls()) == 1
    assert_nothing_leaked(status, capfd)


def test_logged_in_member_without_a_method_is_unreadable(stub):
    stub.answers(b'{"loggedIn": true}')
    assert read(timeout_s=TIMEOUT) == LoginStatus(LOGIN_UNREADABLE, None, 0, False)


@pytest.mark.parametrize("code", [2, 3, 127, 255])
def test_another_exit_status_is_unreadable(code, stub, capfd):
    stub.answers(status_output("claude.ai"), code=code)
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(LOGIN_UNREADABLE, "claude.ai", code, False)
    assert len(stub.calls()) == 1
    assert_nothing_leaked(status, capfd)


@posix_only
def test_a_child_ended_by_a_signal_is_unreadable(stub, capfd):
    stub.install(
        f"out.write({status_output('claude.ai')!r}); out.flush()\n"
        "os.kill(os.getpid(), signal.SIGKILL)"
    )
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(LOGIN_UNREADABLE, "claude.ai", -signal.SIGKILL, False)
    assert len(stub.calls()) == 1
    assert_nothing_leaked(status, capfd)


def test_the_time_limit_is_unreadable(stub, capfd):
    stub.install(
        f"out.write({status_output('claude.ai')!r}); err.write({STDERR!r})\n"
        "out.flush(); err.flush(); time.sleep(12)"
    )
    before = time.monotonic()
    status = read(timeout_s=5)
    assert time.monotonic() - before < 30
    assert status == LoginStatus(LOGIN_UNREADABLE, "claude.ai", None, True)
    assert len(stub.calls()) == 1
    assert_nothing_leaked(status, capfd)


def test_the_time_limit_with_no_output_carries_no_method(stub):
    stub.install("time.sleep(12)")
    assert read(timeout_s=5) == LoginStatus(LOGIN_UNREADABLE, None, None, True)
    assert len(stub.calls()) == 1


def test_no_claude_on_the_path(stub, capfd):
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(NO_CLAUDE, None, None, False)
    assert stub.calls() == []
    assert_nothing_leaked(status, capfd)


def test_a_claude_file_that_is_not_a_program_is_no_claude(stub, capfd):
    marker = stub.directory / "ran"
    program = stub.directory / "claude"
    program.write_text(
        f"#!/bin/sh\necho '{ACCOUNT} {EMAIL} {CONFIG_DIR}'\ntouch '{marker}'\n",
        encoding="utf-8",
    )
    program.chmod(0o644)
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(NO_CLAUDE, None, None, False)
    assert not marker.exists()
    assert_nothing_leaked(status, capfd)


@posix_only
def test_a_claude_file_the_system_cannot_execute_is_no_claude(stub, capfd):
    program = stub.directory / "claude"
    program.write_bytes(b"\x00\x01\x02 " + EMAIL.encode() + b"\n")
    program.chmod(0o755)
    status = read(timeout_s=TIMEOUT)
    assert status == LoginStatus(NO_CLAUDE, None, None, False)
    assert_nothing_leaked(status, capfd)


def test_nothing_is_retried(stub):
    stub.answers(b"", code=1)
    read(timeout_s=TIMEOUT)
    stub.answers(b"garbage", code=0)
    read(timeout_s=TIMEOUT)
    stub.answers(status_output("claude.ai"), code=2)
    read(timeout_s=TIMEOUT)
    assert len(stub.calls()) == 3
    assert all(call["argv"] == ["auth", "status"] for call in stub.calls())


@pytest.mark.parametrize("value", BAD_TIMEOUT_VALUES)
def test_timeout_must_be_positive_and_finite(value, stub):
    stub.answers(status_output("claude.ai"))
    with pytest.raises(ValueError, match="timeout_s"):
        read(timeout_s=value)
    assert stub.calls() == []


@pytest.mark.parametrize("value", BAD_TIMEOUT_TYPES)
def test_timeout_must_be_a_number(value, stub):
    stub.answers(status_output("claude.ai"))
    with pytest.raises(TypeError, match="timeout_s"):
        read(timeout_s=value)
    assert stub.calls() == []


def test_timeout_has_no_default_and_is_keyword_only(stub):
    stub.answers(status_output("claude.ai"))
    with pytest.raises(TypeError):
        read()
    with pytest.raises(TypeError):
        read(TIMEOUT)
    assert stub.calls() == []


def test_missing_cwd_is_refused_before_the_start(stub, tmp_path):
    stub.answers(status_output("claude.ai"))
    absent = tmp_path / EMAIL
    with pytest.raises(FileNotFoundError) as caught:
        read(timeout_s=TIMEOUT, cwd=absent)
    assert EMAIL not in str(caught.value)
    with pytest.raises(FileNotFoundError):
        read(timeout_s=TIMEOUT, cwd=stub.directory / "stub.py")
    assert stub.calls() == []
    assert not absent.exists()


@pytest.mark.parametrize("cwd", [3, 1.5, True, ["work"]])
def test_cwd_that_is_not_a_path(cwd, stub):
    stub.answers(status_output("claude.ai"))
    with pytest.raises(TypeError):
        read(timeout_s=TIMEOUT, cwd=cwd)
    assert stub.calls() == []
