import inspect
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest

from hilclaw import __main__ as front
from hilclaw import (
    config,
    data_root_source,
    local_run,
    selfcheck,
    selfcheck_login,
    selfcheck_outcome,
    selfcheck_report,
    selfcheck_session,
)
from hilclaw.selfcheck import (
    EXIT_FAULT,
    LOGIN_TIMEOUT_S,
    SESSION_TIMEOUT_S,
    check,
    main,
)
from hilclaw.selfcheck_stream import (
    FAIL_TOOL_SESSION_NAME,
    TOKEN_TOOL_SESSION_NAME,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
ACCOUNT = "alice-the-account"
EMAIL = "alice@example.com"
HOME = "/home/alice-the-user/.claude"
SECRETS = (ACCOUNT, EMAIL, HOME, "alice-the-user")
PLANTED = f"[Errno 13] Permission denied: '{HOME}/x' {ACCOUNT} <{EMAIL}>"
FAULT_LINE = b"hilclaw.selfcheck: fault: %s\n"
USAGE_LINE = b"hilclaw.selfcheck: usage: no argument is taken\n"
LOGGED_IN = json.dumps(
    {
        "loggedIn": True,
        "authMethod": "claude.ai",
        "email": EMAIL,
        "orgName": ACCOUNT,
        "configDirectory": HOME,
    }
)
NOT_LOGGED_IN = json.dumps({"loggedIn": False, "authMethod": "none"})
OPT_PRINT = selfcheck_session.OPT_PRINT
PREFIX = "hilclaw-selfcheck-"

STUB = r"""
import json, os, subprocess, sys, time
from pathlib import Path

here = Path(__file__).parent
scenario = json.loads((here / "scenario.json").read_text(encoding="utf-8"))
sys.path.insert(0, scenario["repo"])
from hilclaw import selfcheck_server, selfcheck_stream as names

argv = sys.argv[1:]
out, err = sys.stdout.buffer, sys.stderr.buffer
with (here / "started.ndjson").open("a", encoding="utf-8") as record:
    record.write(json.dumps({"argv": argv, "cwd": os.getcwd()}) + "\n")
noise = " ".join(scenario["noise"]) + " " + os.getcwd()
err.write(noise.encode() + b"\n")
err.flush()
if argv == ["auth", "status"]:
    time.sleep(scenario["auth_sleep"])
    out.write(scenario["auth_output"].encode())
    out.flush()
    sys.exit(scenario["auth_exit"])


def emit(event):
    out.write(json.dumps(event).encode() + b"\n")
    out.flush()


def option(name):
    return argv[argv.index(name) + 1]


config = json.loads(Path(option("--mcp-config")).read_text(encoding="utf-8"))
entry = config["mcpServers"][names.SERVER_NAME]
allowed = option("--allowedTools").split(",")
upto = scenario["upto"]
tools, reply = [], []


def serve():
    server = subprocess.Popen(
        [entry["command"], *entry["args"]],
        env={**os.environ, **entry["env"]},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )

    def ask(method, params=None, request_id=None):
        message = {"jsonrpc": "2.0", "method": method}
        if request_id is not None:
            message["id"] = request_id
        if params is not None:
            message["params"] = params
        server.stdin.write(json.dumps(message).encode() + b"\n")
        server.stdin.flush()
        if request_id is None:
            return None
        return json.loads(server.stdout.readline())

    client = {"name": "stub", "version": "0.0.0-stub"}
    asked = {"protocolVersion": "2025-11-25", "capabilities": {}}
    ask("initialize", {**asked, "clientInfo": client}, 1)
    if upto in ("list", "call"):
        ask("notifications/initialized")
        for tool in ask("tools/list", None, 2)["result"]["tools"]:
            tools.append(names.TOOL_PREFIX + tool["name"])
    if upto == "call":
        for number, tool in enumerate(tools, 3):
            if tool in allowed:
                short = tool[len(names.TOOL_PREFIX):]
                answer = ask("tools/call", {"name": short}, number)
                reply.extend(block["text"] for block in answer["result"]["content"])
    server.stdin.close()
    server.wait()


serve()
status = scenario["status"]
named = {names.SERVER_NAME_KEY: names.SERVER_NAME, names.SERVER_STATUS_KEY: status}
emit(
    {
        names.EVENT_KIND_KEY: names.INIT_KIND,
        names.EVENT_SUBKIND_KEY: names.INIT_SUBKIND,
        "cwd": os.getcwd(),
        "account": noise,
        names.SERVERS_KEY: [] if status is None else [named],
        names.TOOLS_KEY: tools,
    }
)
emit({names.EVENT_KIND_KEY: "assistant", "message": {"content": noise}})
time.sleep(scenario["sleep"])
emit(
    {
        names.EVENT_KIND_KEY: names.RESULT_KIND,
        names.REPLY_KEY: " and ".join(reply) + " " + noise,
        "by": noise,
    }
)
sys.exit(scenario["exit"])
"""


class Stub:
    def __init__(self, directory):
        self.directory = directory
        self.launcher = directory / ("claude" if os.name == "posix" else "claude.cmd")

    def install(self, **changes):
        scenario = {
            "repo": str(REPO_ROOT),
            "noise": [ACCOUNT, EMAIL, HOME],
            "auth_output": LOGGED_IN,
            "auth_exit": 0,
            "auth_sleep": 0,
            "upto": "call",
            "status": "connected",
            "exit": 0,
            "sleep": 0,
        }
        assert set(changes) <= set(scenario)
        scenario.update(changes)
        script = self.directory / "stub.py"
        script.write_text(STUB, encoding="utf-8")
        (self.directory / "scenario.json").write_text(
            json.dumps(scenario), encoding="utf-8"
        )
        if os.name == "posix":
            self.launcher.write_text(
                f"#!/bin/sh\nexec '{sys.executable}' '{script}' \"$@\"\n",
                encoding="utf-8",
            )
            self.launcher.chmod(0o755)
        else:
            self.launcher.write_text(
                f'@"{sys.executable}" "{script}" %*\r\n', encoding="utf-8"
            )
        assert os.path.samefile(shutil.which("claude"), self.launcher)

    def calls(self):
        file = self.directory / "started.ndjson"
        if not file.exists():
            return []
        lines = file.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def kinds(self):
        return [
            "session" if OPT_PRINT in call["argv"] else "login" for call in self.calls()
        ]


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


@pytest.fixture(autouse=True)
def starts(stub, monkeypatch):
    seen = []
    real = local_run.run

    def only_the_stub(command, **options):
        found = shutil.which("claude")
        assert found is None or Path(found).resolve().parent == (
            stub.directory.resolve()
        )
        seen.append((tuple(command), options))
        return real(command, **options)

    monkeypatch.setattr(local_run, "run", only_the_stub)
    return seen


@pytest.fixture(autouse=True)
def checks(tmp_path, monkeypatch):
    directory = tmp_path / "checks"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


@pytest.fixture(autouse=True)
def data_root(tmp_path, monkeypatch):
    directory = tmp_path / "data"
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(directory))
    return directory


class Streams:
    def __init__(self):
        self.out, self.err = io.BytesIO(), io.BytesIO()

    def run(self, argv=()):
        return main(argv, stdout=self.out, stderr=self.err)

    def report(self):
        return one_report(self.out.getvalue())


def one_report(data):
    assert data.endswith(b"\n") and data.count(b"\n") == 1
    assert data.isascii()
    report = json.loads(data)
    assert type(report) is dict
    assert data == selfcheck_report.line(report)
    return report


def left_behind(directory):
    return [name for name in os.listdir(directory) if name.startswith(PREFIX)]


def assert_nothing_leaked(stub, *texts):
    hidden = list(SECRETS)
    for call in stub.calls():
        hidden += [call["cwd"], os.path.basename(call["cwd"])]
    for text in texts:
        text = text.decode()
        for secret in hidden:
            assert secret not in text
        assert not re.search(r"[0-9a-f]{32}", text)
        assert selfcheck_session.PROMPT not in text
        assert PREFIX not in text


OUTCOMES = {
    "no_claude": (None, selfcheck_report.EXIT_NO_CLAUDE, []),
    "not_logged_in": (
        {"auth_exit": 1, "auth_output": NOT_LOGGED_IN},
        selfcheck_report.EXIT_NOT_LOGGED_IN,
        ["login"],
    ),
    "login_unreadable": (
        {"auth_exit": 3},
        selfcheck_report.EXIT_LOGIN_UNREADABLE,
        ["login"],
    ),
    "front_refused": (
        {"upto": "initialize", "status": "failed"},
        selfcheck_report.EXIT_FRONT_REFUSED,
        ["login", "session"],
    ),
    "passed": ({}, selfcheck_report.EXIT_PASSED, ["login", "session"]),
    "no_call": ({"upto": "list"}, selfcheck_report.EXIT_NO_CALL, ["login", "session"]),
    "session_failed": (
        {"exit": 3},
        selfcheck_report.EXIT_SESSION_FAILED,
        ["login", "session"],
    ),
}


def test_public_names():
    public = {name for name in vars(selfcheck) if not name.startswith("_")}
    modules = {name for name in public if inspect.ismodule(vars(selfcheck)[name])}
    assert modules == {
        "contextlib",
        "sys",
        "config",
        "data_root_source",
        "selfcheck_login",
        "selfcheck_report",
        "selfcheck_session",
    }
    assert public - modules == {
        "EXIT_FAULT",
        "LOGIN_TIMEOUT_S",
        "SESSION_TIMEOUT_S",
        "check",
        "main",
    }


def test_the_two_time_limits():
    assert LOGIN_TIMEOUT_S == 30
    assert SESSION_TIMEOUT_S == 300


def test_the_fault_status_is_no_status_of_anything_else():
    taken = {0, 1, 2, 3, 4, *range(10, 16), 120}
    taken |= {front.EXIT_RESULT, front.EXIT_TOOL_FAILURE, front.EXIT_FRONT_FAILURE}
    taken |= {selfcheck_report.exit_status(word) for word in selfcheck_outcome.OUTCOMES}
    assert type(EXIT_FAULT) is int
    assert EXIT_FAULT not in taken
    assert 0 < EXIT_FAULT < 126
    assert EXIT_FAULT == 20


def test_the_outcome_table_of_the_tests_is_the_closed_list():
    assert set(OUTCOMES) == set(selfcheck_outcome.OUTCOMES)


@pytest.mark.parametrize("word", OUTCOMES)
def test_every_outcome_through_main(word, stub, starts, checks, capfdbinary):
    changes, status, kinds = OUTCOMES[word]
    if changes is not None:
        stub.install(**changes)
    streams = Streams()
    assert streams.run() == status
    report = streams.report()
    assert report["outcome"] == word
    assert status == selfcheck_report.exit_status(word)
    assert (status == 0) == (word == "passed")
    assert stub.kinds() == kinds
    assert len(starts) == max(len(kinds), 1)
    assert ("session" in report) == ("session" in kinds)
    assert streams.err.getvalue() == b""
    assert left_behind(checks) == []
    assert capfdbinary.readouterr() == (b"", b"")
    assert_nothing_leaked(stub, streams.out.getvalue())


def test_not_logged_in_stops_with_the_instruction(stub):
    stub.install(auth_exit=1, auth_output=NOT_LOGGED_IN)
    streams = Streams()
    assert streams.run() == selfcheck_report.EXIT_NOT_LOGGED_IN
    report = streams.report()
    assert list(report) == [
        "outcome",
        "refused_a",
        "refused_b",
        "instruction",
        "login",
        "system",
    ]
    assert report["instruction"] == selfcheck_login.LOGIN_INSTRUCTION
    assert report["login"] == {
        "auth_method": "none",
        "exit_status": 1,
        "timed_out": False,
    }
    assert [call["argv"] for call in stub.calls()] == [["auth", "status"]]


def test_a_pass(stub, starts, data_root, tmp_path, checks):
    stub.install()
    before = dict(os.environ)
    streams = Streams()
    assert streams.run() == 0
    report = streams.report()
    assert list(report) == [
        "outcome",
        "refused_a",
        "refused_b",
        "login",
        "system",
        "session",
        "wire",
    ]
    assert report["outcome"] == "passed"
    assert (report["refused_a"], report["refused_b"]) == (False, False)
    assert report["login"] == {
        "auth_method": "claude.ai",
        "exit_status": 0,
        "timed_out": False,
    }
    assert list(report["system"]) == ["os_name", "os_release", "python_version"]
    assert report["session"] == {
        "started": True,
        "init_read": True,
        "result_read": True,
        "exit_status": 0,
        "timed_out": False,
        "wire_copy_read": True,
        "tools": [FAIL_TOOL_SESSION_NAME, TOKEN_TOOL_SESSION_NAME],
        "tools_dropped": False,
        "token_tool_listed": True,
        "fail_tool_listed": True,
        "token_in_reply": True,
        "fail_token_in_reply": True,
        "directory_removed": True,
    }
    assert report["wire"]["client_version"] == "0.0.0-stub"
    assert report["wire"]["token_call_answered"] is True
    assert report["wire"]["fail_call_answered"] is True

    login, session = stub.calls()
    assert login["argv"] == ["auth", "status"]
    assert Path(login["cwd"]).resolve() == (tmp_path / "work").resolve()
    assert session["argv"] == list(selfcheck_session.COMMAND[1:])
    assert Path(session["cwd"]).parent.resolve() == checks.resolve()
    assert not Path(session["cwd"]).exists()
    assert [command[:2] for command, _ in starts] == [
        ("claude", "auth"),
        ("claude", OPT_PRINT),
    ]
    first, second = (options for _, options in starts)
    assert first == {"timeout_s": LOGIN_TIMEOUT_S, "cwd": None}
    assert set(second) == {"timeout_s", "cwd"}
    assert second["timeout_s"] == SESSION_TIMEOUT_S
    assert dict(os.environ) == before
    assert not data_root.exists()


def test_check_returns_the_report_and_writes_nothing(stub, capfdbinary):
    stub.install(upto="list")
    report = check()
    assert type(report) is dict
    assert report["outcome"] == "no_call"
    assert stub.kinds() == ["login", "session"]
    assert capfdbinary.readouterr() == (b"", b"")


def test_check_passes_an_error_on(monkeypatch):
    def fail(**options):
        raise OSError(PLANTED)

    monkeypatch.setattr(selfcheck_login, "read", fail)
    with pytest.raises(OSError, match="Permission denied"):
        check()


def test_the_data_root_is_named_to_the_session(stub, data_root, monkeypatch):
    stub.install()
    asked, handed = [], []
    source, real = data_root_source.configured, selfcheck_session.run

    def configured():
        asked.append(None)
        return source()

    def run(**options):
        handed.append(options)
        return real(**options)

    monkeypatch.setattr(data_root_source, "configured", configured)
    monkeypatch.setattr(selfcheck_session, "run", run)
    assert Streams().run() == 0
    assert handed == [{"timeout_s": SESSION_TIMEOUT_S, "keep_out": (data_root,)}]
    assert len(asked) == 1


def test_no_data_root_configured_goes_on_with_nothing_kept_out(stub, monkeypatch):
    stub.install()
    handed = []
    real = selfcheck_session.run

    def configured():
        raise config.ConfigError(f"{HOME}/hilclaw.config.json: cannot read {ACCOUNT}")

    def run(**options):
        handed.append(options)
        return real(**options)

    monkeypatch.setattr(data_root_source, "configured", configured)
    monkeypatch.setattr(selfcheck_session, "run", run)
    streams = Streams()
    assert streams.run() == 0
    assert streams.report()["outcome"] == "passed"
    assert handed == [{"timeout_s": SESSION_TIMEOUT_S, "keep_out": ()}]
    assert streams.err.getvalue() == b""
    assert_nothing_leaked(stub, streams.out.getvalue())


def test_the_data_root_is_not_asked_without_a_session(stub, monkeypatch):
    stub.install(auth_exit=1)

    def configured():
        raise AssertionError("asked")

    monkeypatch.setattr(data_root_source, "configured", configured)
    assert Streams().run() == selfcheck_report.EXIT_NOT_LOGGED_IN


@pytest.mark.parametrize(
    "changes",
    [
        {"auth_output": "[1, 2]"},
        {"auth_output": f"logged in as {EMAIL}"},
        {"auth_output": json.dumps({"authMethod": "none"})},
        {"auth_exit": 7},
    ],
)
def test_a_login_that_cannot_be_read_starts_no_session(changes, stub):
    stub.install(**changes)
    streams = Streams()
    assert streams.run() == selfcheck_report.EXIT_LOGIN_UNREADABLE
    assert streams.report()["outcome"] == "login_unreadable"
    assert stub.kinds() == ["login"]
    assert_nothing_leaked(stub, streams.out.getvalue(), streams.err.getvalue())


def test_the_time_limit_of_step_one(stub, starts, monkeypatch):
    stub.install(auth_sleep=8)
    monkeypatch.setattr(selfcheck, "LOGIN_TIMEOUT_S", 3)
    before = time.monotonic()
    streams = Streams()
    assert streams.run() == selfcheck_report.EXIT_LOGIN_UNREADABLE
    assert time.monotonic() - before < 40
    report = streams.report()
    assert report["outcome"] == "login_unreadable"
    assert report["login"]["timed_out"] is True
    assert report["login"]["exit_status"] is None
    assert stub.kinds() == ["login"]
    assert [options["timeout_s"] for _, options in starts] == [3]


def test_the_time_limit_of_the_session(stub, starts, checks, monkeypatch):
    stub.install(sleep=12)
    monkeypatch.setattr(selfcheck, "SESSION_TIMEOUT_S", 5)
    before = time.monotonic()
    streams = Streams()
    assert streams.run() == selfcheck_report.EXIT_SESSION_FAILED
    assert time.monotonic() - before < 60
    report = streams.report()
    assert report["outcome"] == "session_failed"
    assert report["session"]["timed_out"] is True
    assert report["session"]["exit_status"] is None
    assert stub.kinds() == ["login", "session"]
    assert [options["timeout_s"] for _, options in starts] == [LOGIN_TIMEOUT_S, 5]
    assert left_behind(checks) == []


@pytest.mark.parametrize(
    "changes, kinds",
    [
        ({"upto": "list"}, ["login", "session"]),
        ({"exit": 1}, ["login", "session"]),
        ({"auth_output": "no object"}, ["login"]),
    ],
    ids=["no_call", "session_failed", "login_unreadable"],
)
def test_nothing_is_tried_again(changes, kinds, stub, starts):
    stub.install(**changes)
    assert Streams().run() not in (0, EXIT_FAULT)
    assert stub.kinds() == kinds
    assert len(starts) == len(kinds)
    assert all("login" not in call["argv"] for call in stub.calls())


@pytest.mark.parametrize("changes", [{}, {"exit": 1}], ids=["passed", "session_failed"])
def test_nothing_of_a_child_reaches_a_stream(changes, stub, checks, capfdbinary):
    stub.install(**changes)
    assert main([]) in (0, selfcheck_report.EXIT_SESSION_FAILED)
    out, err = capfdbinary.readouterr()
    assert one_report(out)["session"]["started"] is True
    assert err == b""
    assert stub.kinds() == ["login", "session"]
    assert_nothing_leaked(stub, out, err)
    assert left_behind(checks) == []


def test_the_default_arguments_are_those_of_the_process(stub, monkeypatch, capfdbinary):
    stub.install(auth_exit=1)
    monkeypatch.setattr(sys, "argv", ["selfcheck"])
    assert main() == selfcheck_report.EXIT_NOT_LOGGED_IN
    out, err = capfdbinary.readouterr()
    assert one_report(out)["outcome"] == "not_logged_in"
    assert err == b""
    monkeypatch.setattr(sys, "argv", ["selfcheck", "--help"])
    assert main() == EXIT_FAULT
    assert capfdbinary.readouterr() == (b"", USAGE_LINE)
    assert stub.kinds() == ["login"]


@pytest.mark.parametrize(
    "argv",
    [["x"], ["--help"], ["-h"], [""], ["--timeout", "5"], ["a", "b", "c"], ("--json",)],
)
def test_any_argument_is_refused_before_anything_is_started(argv, stub, starts):
    stub.install()
    streams = Streams()
    assert streams.run(argv) == EXIT_FAULT
    assert streams.out.getvalue() == b""
    assert streams.err.getvalue() == USAGE_LINE
    assert stub.calls() == []
    assert starts == []


def test_a_directory_inside_the_data_root_is_a_fault(
    stub, data_root, monkeypatch, capfdbinary
):
    stub.install()
    inside = data_root / "tmp"
    inside.mkdir(parents=True)
    monkeypatch.setattr(tempfile, "tempdir", str(inside))
    streams = Streams()
    assert streams.run() == EXIT_FAULT
    assert streams.out.getvalue() == b""
    assert streams.err.getvalue() == FAULT_LINE % b"ValueError"
    assert stub.kinds() == ["login"]
    assert left_behind(inside) == []
    assert capfdbinary.readouterr() == (b"", b"")
    with pytest.raises(ValueError, match="inside a checkout"):
        check()


def planted(error):
    def fail(*arguments, **options):
        raise error

    return fail


FAULTS = {
    "an OSError of the session": (selfcheck_session, "run", OSError(PLANTED)),
    "an OSError of step one": (selfcheck_login, "read", OSError(PLANTED)),
    "an OverflowError of the session": (
        selfcheck_session,
        "run",
        OverflowError(PLANTED),
    ),
    "a RuntimeError of the session": (selfcheck_session, "run", RuntimeError(PLANTED)),
    "a TypeError of step one": (selfcheck_login, "read", TypeError(PLANTED)),
    "the system facts": (selfcheck_report, "system_facts", OSError(PLANTED)),
    "the line": (selfcheck_report, "line", TypeError(PLANTED)),
    "the data-root source": (data_root_source, "configured", RuntimeError(PLANTED)),
}


@pytest.mark.parametrize("fault", FAULTS.values(), ids=FAULTS.keys())
def test_a_fault_of_the_check_says_the_class_and_never_the_text(
    fault, stub, checks, monkeypatch, capfdbinary
):
    module, name, error = fault
    stub.install()
    monkeypatch.setattr(module, name, planted(error))
    streams = Streams()
    assert streams.run() == EXIT_FAULT
    assert streams.out.getvalue() == b""
    assert streams.err.getvalue() == FAULT_LINE % type(error).__name__.encode()
    assert capfdbinary.readouterr() == (b"", b"")
    assert left_behind(checks) == []
    assert_nothing_leaked(stub, streams.err.getvalue())


@pytest.mark.parametrize(
    "found, error",
    [(None, b"ValueError"), ("no run", b"TypeError"), ((), b"TypeError")],
)
def test_a_report_that_cannot_be_built_is_a_fault(found, error, stub, monkeypatch):
    stub.install()
    monkeypatch.setattr(selfcheck_session, "run", lambda **options: found)
    streams = Streams()
    assert streams.run() == EXIT_FAULT
    assert streams.out.getvalue() == b""
    assert streams.err.getvalue() == FAULT_LINE % error


def test_a_step_one_of_another_form_is_a_fault(stub, monkeypatch):
    stub.install()
    status = selfcheck_login.LoginStatus("passed", None, 0, False)
    monkeypatch.setattr(selfcheck_login, "read", lambda **options: status)
    streams = Streams()
    assert streams.run() == EXIT_FAULT
    assert streams.out.getvalue() == b""
    assert stub.calls() == []


class Broken(io.BytesIO):
    def __init__(self, error, on):
        super().__init__()
        self.error, self.on = error, on

    def write(self, data):
        if self.on == "write":
            raise self.error
        return super().write(data)

    def flush(self):
        if self.on == "flush":
            raise self.error


class Short(io.BytesIO):
    def write(self, data):
        return super().write(data[:10])


@pytest.mark.parametrize(
    "stdout, error",
    [
        (Broken(OSError(PLANTED), "write"), b"OSError"),
        (Broken(ValueError(PLANTED), "write"), b"ValueError"),
        (Broken(OSError(PLANTED), "flush"), b"OSError"),
        (Short(), b"OSError"),
    ],
    ids=["write", "closed", "flush", "short"],
)
def test_a_standard_output_that_cannot_be_written_is_a_fault(stdout, error, stub):
    stub.install()
    err = io.BytesIO()
    assert main([], stdout=stdout, stderr=err) == EXIT_FAULT
    assert err.getvalue() == FAULT_LINE % error
    assert stub.kinds() == ["login", "session"]


def test_a_closed_standard_output_is_a_fault(stub, monkeypatch, capfdbinary):
    stub.install()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stdout", None)
        assert main([]) == EXIT_FAULT
    assert capfdbinary.readouterr() == (b"", FAULT_LINE % b"OSError")


@pytest.mark.parametrize("error", [OSError(PLANTED), ValueError(PLANTED)])
def test_a_standard_error_that_cannot_be_written_changes_nothing(error, stub):
    stub.install()
    out = io.BytesIO()
    assert main(["x"], stdout=out, stderr=Broken(error, "write")) == EXIT_FAULT
    assert main([], stdout=out, stderr=Broken(error, "write")) == 0
    assert one_report(out.getvalue())["outcome"] == "passed"


def test_a_closed_standard_error_changes_nothing(stub, monkeypatch, capfdbinary):
    stub.install()
    with monkeypatch.context() as patch:
        patch.setattr(sys, "stderr", None)
        assert main(["x"]) == EXIT_FAULT
        assert main([], stdout=Broken(OSError(PLANTED), "write")) == EXIT_FAULT
    assert capfdbinary.readouterr() == (b"", b"")


@pytest.mark.parametrize("error", [KeyboardInterrupt, SystemExit])
def test_an_interrupt_is_not_caught(error, monkeypatch):
    monkeypatch.setattr(selfcheck_login, "read", planted(error()))
    streams = Streams()
    with pytest.raises(error):
        streams.run()
    assert (streams.out.getvalue(), streams.err.getvalue()) == (b"", b"")


@pytest.mark.parametrize(
    "arguments, status",
    [((), 0), (("--help",), EXIT_FAULT)],
    ids=["a pass", "an argument"],
)
def test_the_command(arguments, status, stub, checks, tmp_path):
    stub.install()
    work = tmp_path / "work"
    env = {
        **os.environ,
        "PATH": str(stub.directory),
        "PYTHONPATH": str(REPO_ROOT),
        "TMPDIR": str(checks),
        "TEMP": str(checks),
        "TMP": str(checks),
    }
    assert os.listdir(work) == []
    assert os.path.samefile(shutil.which("claude", path=env["PATH"]), stub.launcher)
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.selfcheck", *arguments],
        env=env,
        cwd=work,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert done.returncode == status
    if arguments:
        assert done.stdout == b""
        assert done.stderr.replace(b"\r\n", b"\n") == USAGE_LINE
        assert stub.calls() == []
    else:
        assert one_report(done.stdout)["outcome"] == "passed"
        assert done.stderr == b""
        assert stub.kinds() == ["login", "session"]
        assert_nothing_leaked(stub, done.stdout)
    assert left_behind(checks) == []
