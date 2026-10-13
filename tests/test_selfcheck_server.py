import io
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import mcp_front, selfcheck_server, tools
from hilclaw.selfcheck_server import (
    ENV_FAIL_TOKEN,
    ENV_TOKEN,
    ENV_WIRE_COPY,
    FAIL_KIND,
    FAIL_TOOL,
    FROM_CLIENT,
    FROM_SERVER,
    RESULT_MEMBER,
    TOKEN_TOOL,
    WIRE_COPY_MAGIC,
    WireCopy,
    WireCopyError,
    main,
    new_token,
    read_wire_copy,
    registry,
    server_entry,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "0123456789abcdef0123456789abcdef"
FAIL_TOKEN = "fedcba9876543210fedcba9876543210"
ODD_NAME = "self check é한"
# What a platform needs to start the interpreter at all, and nothing else of
# the test process: Windows cannot initialise a process without SYSTEMROOT,
# and a runner's interpreter may find its shared library by LD_LIBRARY_PATH.
PLATFORM_NAMES = ("SYSTEMROOT", "LD_LIBRARY_PATH")
BAD_TOKENS = [
    pytest.param(None, FAIL_TOKEN, TypeError, id="first missing"),
    pytest.param(TOKEN, None, TypeError, id="second missing"),
    pytest.param("", FAIL_TOKEN, ValueError, id="first empty"),
    pytest.param(TOKEN, "", ValueError, id="second empty"),
    pytest.param(TOKEN.upper(), FAIL_TOKEN, ValueError, id="upper case"),
    pytest.param(TOKEN[:-1], FAIL_TOKEN, ValueError, id="too short"),
    pytest.param(TOKEN, FAIL_TOKEN + "0", ValueError, id="too long"),
    pytest.param(TOKEN, FAIL_TOKEN[:-1] + "g", ValueError, id="not hexadecimal"),
    pytest.param(TOKEN + "\n", FAIL_TOKEN, ValueError, id="trailing line feed"),
    pytest.param(TOKEN.encode(), FAIL_TOKEN, TypeError, id="bytes"),
    pytest.param(TOKEN, 7, TypeError, id="int"),
    pytest.param(TOKEN, TOKEN, ValueError, id="equal"),
]


def request(request_id, method, params=None):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return json.dumps(message).encode() + b"\n"


def call(request_id, name, arguments=None):
    params = {"name": name}
    if arguments is not None:
        params["arguments"] = arguments
    return request(request_id, "tools/call", params)


INITIALIZE = request(
    1,
    "initialize",
    {
        "protocolVersion": "2025-11-25",
        "capabilities": {},
        "clientInfo": {"name": "test client", "version": "0"},
    },
)
LIST = request(2, "tools/list")
CALL_TOKEN = call(3, "selfcheck_token")
CALL_FAIL = call(4, "selfcheck_fail")
EXCHANGE = [INITIALIZE, LIST, CALL_TOKEN, CALL_FAIL]


def environment(place, token=TOKEN, fail_token=FAIL_TOKEN):
    given = {ENV_TOKEN: token, ENV_FAIL_TOKEN: fail_token, ENV_WIRE_COPY: place}
    return {name: value for name, value in given.items() if value is not None}


class Served:
    def __init__(self, tmp_path, lines, environ=None, argv=(), stdout=None):
        self.place = tmp_path / "wire-copy"
        self.stdin = io.BytesIO(b"".join(lines))
        self.stdout = io.BytesIO() if stdout is None else stdout
        self.stderr = io.BytesIO()
        self.status = main(
            argv,
            environ=environment(str(self.place)) if environ is None else environ,
            stdin=self.stdin,
            stdout=self.stdout,
            stderr=self.stderr,
        )
        self.answers = self.stdout.getvalue().splitlines(keepends=True)
        self.said = self.stderr.getvalue()

    def assert_gave_up_unserved(self, tmp_path):
        assert self.status == 4
        assert self.answers == []
        assert self.stdin.tell() == 0
        assert_says_nothing_secret(self.said, tmp_path)
        assert self.said.startswith(b"hilclaw.selfcheck_server: ")
        assert self.said.count(b"\n") == 1


def assert_says_nothing_secret(text, tmp_path):
    for secret in (TOKEN, FAIL_TOKEN, str(tmp_path), tmp_path.name, "secret"):
        assert secret.encode() not in text


def front_alone(lines):
    out = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=registry(TOKEN, FAIL_TOKEN),
        stdin=io.BytesIO(b"".join(lines)),
        stdout=out,
        stderr=io.BytesIO(),
    )
    assert status == 0
    return out.getvalue().splitlines(keepends=True)


def result_of(answer):
    return json.loads(answer)["result"]


def text_of(answer):
    (block,) = result_of(answer)["content"]
    assert block["type"] == "text"
    return json.loads(block["text"])


def record(mark, line):
    return mark + b" " + str(len(line)).encode() + b"\n" + line + b"\n"


def child_environment(entry):
    kept = {name: os.environ[name] for name in PLATFORM_NAMES if name in os.environ}
    return {**kept, **entry["env"]}


def run_child(entry, cwd, lines, extra=None):
    return subprocess.run(
        [entry["command"], *entry["args"]],
        input=b"".join(lines),
        capture_output=True,
        cwd=cwd,
        env={**child_environment(entry), **(extra or {})},
        timeout=60,
        check=False,
    )


def odd_directory(tmp_path):
    directory = tmp_path / ODD_NAME
    directory.mkdir()
    return directory


def assert_full_exchange(answers, lines):
    assert [json.loads(answer)["id"] for answer in answers] == [1, 2, 3, 4]
    listed = result_of(answers[1])["tools"]
    assert [tool["name"] for tool in listed] == ["selfcheck_fail", "selfcheck_token"]
    assert result_of(answers[2])["isError"] is False
    assert text_of(answers[2]) == {RESULT_MEMBER: TOKEN}
    assert result_of(answers[3])["isError"] is True
    failure = text_of(answers[3])["error"]
    assert failure["kind"] == FAIL_KIND
    assert failure["message"].endswith(FAIL_TOKEN)
    expected = []
    for sent, answered in zip(EXCHANGE, answers, strict=True):
        expected += [(FROM_CLIENT, sent), (FROM_SERVER, answered)]
    assert lines == tuple(expected)


def test_the_names_are_spelt_as_the_record_spells_them():
    assert TOKEN_TOOL == "selfcheck.token"
    assert FAIL_TOOL == "selfcheck.fail"
    assert mcp_front.mcp_name(TOKEN_TOOL) == "selfcheck_token"
    assert mcp_front.mcp_name(FAIL_TOOL) == "selfcheck_fail"
    assert RESULT_MEMBER == "token"
    assert FAIL_KIND not in tools.RESERVED_KINDS
    assert (FROM_CLIENT, FROM_SERVER) == ("client", "server")
    assert WIRE_COPY_MAGIC.endswith(b"\n") and WIRE_COPY_MAGIC.count(b"\n") == 1
    names = {ENV_TOKEN, ENV_FAIL_TOKEN, ENV_WIRE_COPY}
    assert len(names) == 3
    assert all(name.startswith("HILCLAW_SELFCHECK_") for name in names)


def test_the_public_names_of_the_module():
    public = {name for name in vars(selfcheck_server) if not name.startswith("_")}
    imported = {"contextlib", "os", "re", "secrets", "sys", "NamedTuple"}
    assert public - imported - {"mcp_front", "tools"} == {
        "ENV_FAIL_TOKEN",
        "ENV_TOKEN",
        "ENV_WIRE_COPY",
        "FAIL_KIND",
        "FAIL_TOOL",
        "FROM_CLIENT",
        "FROM_SERVER",
        "RESULT_MEMBER",
        "TOKEN_TOOL",
        "WIRE_COPY_MAGIC",
        "WireCopy",
        "WireCopyError",
        "main",
        "new_token",
        "read_wire_copy",
        "registry",
        "server_entry",
    }


def test_the_exchange_in_process_is_what_the_front_writes_alone(tmp_path):
    served = Served(tmp_path, EXCHANGE)
    assert served.status == 0
    assert served.said == b""
    assert served.answers == front_alone(EXCHANGE)
    copy = read_wire_copy(served.place)
    assert isinstance(copy, WireCopy)
    assert copy.torn is False
    assert_full_exchange(served.answers, copy.lines)
    assert all(type(line) is bytes for _, line in copy.lines)


def test_the_entry_reads_the_process_environment_and_arguments_by_default(
    tmp_path, monkeypatch
):
    place = tmp_path / "wire-copy"
    for name, value in environment(str(place)).items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(sys, "argv", ["entry"])
    out = io.BytesIO()
    status = main(stdin=io.BytesIO(INITIALIZE), stdout=out, stderr=io.BytesIO())
    assert status == 0
    assert out.getvalue() == front_alone([INITIALIZE])[0]
    assert read_wire_copy(place).lines == (
        (FROM_CLIENT, INITIALIZE),
        (FROM_SERVER, out.getvalue()),
    )


def test_the_entry_started_from_the_server_entry_alone(tmp_path):
    cwd = odd_directory(tmp_path)
    place = cwd / "wire copy é"
    entry = server_entry(token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=place)
    assert not REPO_ROOT.samefile(cwd) and REPO_ROOT not in cwd.parents
    done = run_child(entry, cwd, EXCHANGE)
    assert done.returncode == 0
    assert done.stderr == b""
    answers = done.stdout.splitlines(keepends=True)
    assert answers == front_alone(EXCHANGE)
    copy = read_wire_copy(place)
    assert copy.torn is False
    assert_full_exchange(answers, copy.lines)


def test_the_child_rests_on_neither_the_working_directory_nor_python_variables(
    tmp_path,
):
    cwd = odd_directory(tmp_path)
    for decoy in (cwd / "hilclaw", tmp_path / "decoy" / "hilclaw"):
        decoy.mkdir(parents=True)
        (decoy / "__init__.py").write_text("raise SystemExit(9)\n", encoding="utf-8")
    entry = server_entry(
        token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=tmp_path / "wire-copy"
    )
    extra = {"PYTHONPATH": str(tmp_path / "decoy"), "PYTHONSTARTUP": "missing"}
    done = run_child(entry, cwd, EXCHANGE, extra)
    assert done.returncode == 0
    assert done.stdout.splitlines(keepends=True) == front_alone(EXCHANGE)


def test_a_package_under_a_path_with_a_space_and_a_non_ascii_character(tmp_path):
    home = odd_directory(tmp_path)
    shutil.copytree(
        REPO_ROOT / "hilclaw",
        home / "hilclaw",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    place = tmp_path / "wire-copy"
    build = (
        "import json, sys; sys.path.insert(0, sys.argv.pop(1)); "
        "from hilclaw import selfcheck_server; "
        "entry = selfcheck_server.server_entry("
        "token=sys.argv[1], fail_token=sys.argv[2], wire_copy=sys.argv[3]); "
        "sys.stdout.buffer.write(json.dumps(entry).encode('ascii'))"
    )
    built = subprocess.run(
        [sys.executable, "-I", "-c", build, str(home), TOKEN, FAIL_TOKEN, str(place)],
        capture_output=True,
        cwd=tmp_path,
        env={name: os.environ[name] for name in PLATFORM_NAMES if name in os.environ},
        timeout=60,
        check=True,
    )
    entry = json.loads(built.stdout)
    assert Path(entry["args"][-1]).samefile(home)
    done = run_child(entry, tmp_path, EXCHANGE)
    assert done.returncode == 0
    assert done.stdout.splitlines(keepends=True) == front_alone(EXCHANGE)
    assert len(read_wire_copy(place).lines) == 8


def test_a_killed_child_leaves_every_handled_line_in_the_copy(tmp_path):
    place = tmp_path / "wire-copy"
    entry = server_entry(token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=place)
    child = subprocess.Popen(
        [entry["command"], *entry["args"]],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        cwd=tmp_path,
        env=child_environment(entry),
    )
    try:
        answers = []
        for line in (INITIALIZE, CALL_TOKEN):
            child.stdin.write(line)
            child.stdin.flush()
            answers.append(child.stdout.readline())
    finally:
        child.kill()
        child.wait(timeout=60)
        child.stdin.close()
        child.stdout.close()
    assert read_wire_copy(place) == WireCopy(
        (
            (FROM_CLIENT, INITIALIZE),
            (FROM_SERVER, answers[0]),
            (FROM_CLIENT, CALL_TOKEN),
            (FROM_SERVER, answers[1]),
        ),
        False,
    )


@pytest.mark.parametrize(
    "arguments", [{"stray": 1}, {"token": "x", "nested": {"a": [None]}}, {}]
)
def test_stray_arguments_change_neither_answer(tmp_path, arguments):
    lines = [
        call(1, "selfcheck_token", arguments),
        call(2, "selfcheck_fail", arguments),
    ]
    served = Served(tmp_path, lines)
    assert served.status == 0
    assert result_of(served.answers[0])["isError"] is False
    assert text_of(served.answers[0]) == {RESULT_MEMBER: TOKEN}
    assert result_of(served.answers[1])["isError"] is True
    assert text_of(served.answers[1])["error"]["kind"] == FAIL_KIND


def test_the_tools_keep_no_state_between_calls(tmp_path):
    lines = [call(i, "selfcheck_token") for i in range(1, 4)]
    served = Served(tmp_path, lines)
    assert [text_of(answer) for answer in served.answers] == [{"token": TOKEN}] * 3


def test_a_method_the_front_does_not_serve_is_in_the_copy_with_its_answer(tmp_path):
    probe = request(0, "server/discover", {"protocolVersion": "2026-07-28"})
    served = Served(tmp_path, [probe, INITIALIZE])
    assert served.status == 0
    assert json.loads(served.answers[0])["error"]["code"] == -32601
    assert read_wire_copy(served.place).lines == (
        (FROM_CLIENT, probe),
        (FROM_SERVER, served.answers[0]),
        (FROM_CLIENT, INITIALIZE),
        (FROM_SERVER, served.answers[1]),
    )


def test_lines_without_an_answer_are_copied_as_client_lines(tmp_path):
    notification = b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
    lines = [notification, b"\n", b"  \r\n", INITIALIZE]
    served = Served(tmp_path, lines)
    assert served.status == 0
    assert len(served.answers) == 1
    assert read_wire_copy(served.place).lines == (
        *((FROM_CLIENT, line) for line in lines),
        (FROM_SERVER, served.answers[0]),
    )


def test_a_last_client_line_without_a_line_feed(tmp_path):
    last = LIST[:-1]
    served = Served(tmp_path, [INITIALIZE, last])
    assert served.status == 0
    assert served.answers == front_alone([INITIALIZE, last])
    assert read_wire_copy(served.place).lines[2] == (FROM_CLIENT, last)


def test_client_lines_of_any_bytes_pass_unchanged_and_round_trip(tmp_path):
    lines = [
        b"\xff\xfe invalid utf-8\n",
        b"a\x00b\n",
        b"carriage\rreturn\r\n",
        b"\n",
        b"C 3\n",
        WIRE_COPY_MAGIC,
        b"x" * 1_000_000 + b"\n",
        b"\x80 no line feed",
    ]
    served = Served(tmp_path, lines)
    assert served.status == 0
    assert served.answers == front_alone(lines)
    copy = read_wire_copy(served.place)
    assert copy.torn is False
    assert [line for direction, line in copy.lines if direction == FROM_CLIENT] == lines
    assert [
        line for direction, line in copy.lines if direction == FROM_SERVER
    ] == served.answers


def test_new_token_returns_accepted_tokens_that_differ():
    first, second = new_token(), new_token()
    assert type(first) is str
    assert re.fullmatch(r"[0-9a-f]{32}", first)
    assert first != second
    assert registry(first, second).names() == (FAIL_TOOL, TOKEN_TOOL)


def test_the_registry_holds_exactly_the_two_tools(tmp_path):
    held = registry(TOKEN, FAIL_TOKEN)
    assert held.names() == ("selfcheck.fail", "selfcheck.token")
    assert tools.call(held, TOKEN_TOOL, {}) == {"token": TOKEN}
    with pytest.raises(tools.ToolFailure) as caught:
        tools.call(held, FAIL_TOOL, {})
    assert caught.value.kind == FAIL_KIND
    assert registry(TOKEN, FAIL_TOKEN) is not held


def test_the_registry_of_a_run_holds_neither_tool():
    before = tools.default_registry(lambda: None).names()
    registry(TOKEN, FAIL_TOKEN)
    after = tools.default_registry(lambda: None).names()
    assert before == after
    assert TOKEN_TOOL not in after and FAIL_TOOL not in after
    assert not any(name.startswith("selfcheck") for name in after)


def test_no_token_is_shown_before_a_call(tmp_path):
    held = registry(TOKEN, FAIL_TOKEN)
    for name in held.names():
        definition = held.definition(name)
        shown = json.dumps([definition.description, definition.input_schema, name])
        assert TOKEN not in shown and FAIL_TOKEN not in shown
        assert len(definition.description) < 300
        assert definition.input_schema["type"] == "object"
    lines = [INITIALIZE, LIST, request(5, "ping"), request(6, "server/discover")]
    served = Served(tmp_path, lines)
    assert len(served.answers) == 4
    for answer in served.answers:
        assert TOKEN.encode() not in answer and FAIL_TOKEN.encode() not in answer


def test_neither_answer_holds_the_token_of_the_other(tmp_path):
    served = Served(tmp_path, [CALL_TOKEN, CALL_FAIL])
    assert TOKEN.encode() in served.answers[0]
    assert FAIL_TOKEN.encode() not in served.answers[0]
    assert FAIL_TOKEN.encode() in served.answers[1]
    assert TOKEN.encode() not in served.answers[1]


@pytest.mark.parametrize("name", ["selfcheck.token", "blob_push", "selfcheck", None])
def test_no_other_tool_can_be_called(tmp_path, name):
    served = Served(tmp_path, [call(1, name)])
    answer = json.loads(served.answers[0])
    assert answer["error"]["code"] == -32602
    assert TOKEN not in served.answers[0].decode()
    assert FAIL_TOKEN not in served.answers[0].decode()


@pytest.mark.parametrize(("token", "fail_token", "error"), BAD_TOKENS)
def test_bad_tokens_are_refused_before_anything_is_served(
    tmp_path, token, fail_token, error
):
    for build in (
        lambda: registry(token, fail_token),
        lambda: server_entry(
            token=token, fail_token=fail_token, wire_copy=tmp_path / "wire-copy"
        ),
    ):
        with pytest.raises(error) as caught:
            build()
        assert_says_nothing_secret(str(caught.value).encode(), tmp_path)
    served = Served(
        tmp_path, EXCHANGE, environment(str(tmp_path / "wire-copy"), token, fail_token)
    )
    served.assert_gave_up_unserved(tmp_path)
    assert not served.place.exists()


@pytest.mark.parametrize("place", [None, "", "relative/wire-copy", "nul\0inside"])
def test_a_place_that_is_missing_or_not_absolute_ends_the_entry(tmp_path, place):
    served = Served(tmp_path, EXCHANGE, environment(place))
    served.assert_gave_up_unserved(tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("argv", [["extra"], ["--help"], [TOKEN, FAIL_TOKEN], [""]])
def test_an_argument_ends_the_entry(tmp_path, argv):
    served = Served(tmp_path, EXCHANGE, argv=argv)
    served.assert_gave_up_unserved(tmp_path)
    assert not served.place.exists()


def test_an_argument_of_the_process_ends_the_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["entry", "extra"])
    served = Served(tmp_path, EXCHANGE, argv=None)
    served.assert_gave_up_unserved(tmp_path)


def test_a_missing_directory_ends_the_entry_before_a_line_is_read(tmp_path):
    place = tmp_path / "secret missing" / "wire-copy"
    served = Served(tmp_path, EXCHANGE, environment(str(place)))
    served.assert_gave_up_unserved(tmp_path)
    assert not place.parent.exists()


def test_an_existing_file_is_refused_and_left_as_it_was(tmp_path):
    place = tmp_path / "wire-copy"
    earlier = WIRE_COPY_MAGIC + record(b"C", b"earlier\n")
    place.write_bytes(earlier)
    served = Served(tmp_path, EXCHANGE)
    served.assert_gave_up_unserved(tmp_path)
    assert place.read_bytes() == earlier


def test_giving_up_without_a_standard_error_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stderr", None)
    status = main(["extra"], environ={}, stdin=io.BytesIO(), stdout=io.BytesIO())
    assert status == 4


def test_a_failing_standard_error_does_not_change_the_status(tmp_path):
    class Broken(io.BytesIO):
        def write(self, data):
            raise OSError("secret")

    status = main(["extra"], environ={}, stdin=io.BytesIO(), stderr=Broken())
    assert status == 4


class FakeCopy:
    def __init__(self, good_writes, chunk=None):
        self.good_writes = good_writes
        self.chunk = chunk
        self.data = bytearray()
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True

    def write(self, view):
        if self.good_writes == 0:
            raise OSError(28, "No space left on device", "/secret/place")
        self.good_writes -= 1
        taken = bytes(view[: self.chunk])
        self.data += taken
        return len(taken)


def serve_over(fake, tmp_path, monkeypatch, lines, stdout=None):
    with monkeypatch.context() as patched:
        patched.setattr(selfcheck_server, "open", lambda *a, **k: fake, raising=False)
        served = Served(tmp_path, lines, stdout=stdout)
    assert fake.closed
    if not fake.data.startswith(WIRE_COPY_MAGIC):
        return served, None
    return served, read_wire_copy_of(served.place, bytes(fake.data))


def test_a_copy_that_cannot_take_its_first_line_ends_the_entry(tmp_path, monkeypatch):
    served, copy = serve_over(FakeCopy(0), tmp_path, monkeypatch, EXCHANGE)
    assert copy is None
    served.assert_gave_up_unserved(tmp_path)


def test_a_client_line_that_cannot_be_copied_is_not_served(tmp_path, monkeypatch):
    served, copy = serve_over(FakeCopy(3), tmp_path, monkeypatch, EXCHANGE)
    assert served.status == 4
    assert served.answers == front_alone([INITIALIZE])
    assert copy == WireCopy(
        ((FROM_CLIENT, INITIALIZE), (FROM_SERVER, served.answers[0])), False
    )
    assert served.stdin.tell() == len(INITIALIZE + LIST)
    assert_says_nothing_secret(served.said, tmp_path)
    assert served.said.count(b"\n") == 1


def test_after_an_answer_that_cannot_be_copied_none_follows(tmp_path, monkeypatch):
    served, copy = serve_over(FakeCopy(2), tmp_path, monkeypatch, EXCHANGE)
    assert served.status == 4
    assert served.answers == front_alone([INITIALIZE])
    assert copy == WireCopy(((FROM_CLIENT, INITIALIZE),), False)
    assert served.stdin.tell() == len(INITIALIZE)
    assert_says_nothing_secret(served.said, tmp_path)


def test_a_copy_closed_under_the_entry_is_the_give_up_of_the_front(
    tmp_path, monkeypatch
):
    class Closed(FakeCopy):
        def write(self, view):
            if self.good_writes == 0:
                raise ValueError("write to closed file /secret/place")
            return super().write(view)

    served, copy = serve_over(Closed(1), tmp_path, monkeypatch, EXCHANGE)
    assert served.status == 4
    assert served.answers == []
    assert copy == WireCopy((), False)
    assert_says_nothing_secret(served.said, tmp_path)


def test_a_copy_taken_in_small_pieces_holds_whole_records(tmp_path, monkeypatch):
    served, copy = serve_over(FakeCopy(-1, chunk=7), tmp_path, monkeypatch, EXCHANGE)
    assert served.status == 0
    assert copy.torn is False
    assert_full_exchange(served.answers, copy.lines)


class BrokenOutput(io.BytesIO):
    def __init__(self, good_writes, fail_flush=False):
        super().__init__()
        self.good_writes = good_writes
        self.fail_flush = fail_flush

    def write(self, data):
        self.good_writes -= 1
        if self.good_writes < 0 and not self.fail_flush:
            raise OSError("the pipe is broken")
        return super().write(data)

    def flush(self):
        if self.good_writes < 0:
            raise OSError("the pipe is broken")


@pytest.mark.parametrize("fail_flush", [False, True])
def test_an_answer_that_was_not_sent_is_not_in_the_copy(tmp_path, fail_flush):
    served = Served(tmp_path, EXCHANGE, stdout=BrokenOutput(1, fail_flush))
    assert served.status == 4
    copy = read_wire_copy(served.place)
    assert copy == WireCopy(
        (
            (FROM_CLIENT, INITIALIZE),
            (FROM_SERVER, front_alone([INITIALIZE])[0]),
            (FROM_CLIENT, LIST),
        ),
        False,
    )
    assert served.stdin.tell() == len(INITIALIZE + LIST)


def test_closed_standard_streams_are_the_give_up_of_the_front(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdin", None)
    monkeypatch.setattr(sys, "stdout", None)
    place = tmp_path / "wire-copy"
    err = io.BytesIO()
    assert main([], environ=environment(str(place)), stderr=err) == 4
    assert b"standard input" in err.getvalue()
    assert read_wire_copy(place) == WireCopy((), False)
    other = tmp_path / "other"
    status = main(
        [], environ=environment(str(other)), stdin=io.BytesIO(INITIALIZE), stderr=err
    )
    assert status == 4
    assert read_wire_copy(other) == WireCopy(((FROM_CLIENT, INITIALIZE),), False)


def test_the_server_entry_holds_only_what_the_check_made(tmp_path, monkeypatch):
    planted = {
        "HILCLAW_TEST_MARKER": "marker-value-1",
        "ANTHROPIC_API_KEY": "sk-ant-planted-2",
        "CLAUDE_CODE_OAUTH_TOKEN": "oauth-planted-3",
    }
    for name, value in planted.items():
        monkeypatch.setenv(name, value)
    place = tmp_path / "wire-copy"
    entry = server_entry(token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=place)
    assert set(entry) == {"command", "args", "env"}
    assert entry["command"] == sys.executable
    assert type(entry["args"]) is list
    assert all(type(value) is str for value in entry["args"])
    assert entry["args"][:2] == ["-I", "-c"]
    assert Path(entry["args"][-1]).samefile(REPO_ROOT)
    assert entry["env"] == {
        ENV_TOKEN: TOKEN,
        ENV_FAIL_TOKEN: FAIL_TOKEN,
        ENV_WIRE_COPY: str(place),
    }
    assert all(type(value) is str for value in entry["env"].values())
    text = json.dumps(entry)
    for name, value in planted.items():
        assert name not in text and value not in text
    for value in os.environ.values():
        if len(value) > 8 and value not in (sys.executable, str(REPO_ROOT)):
            assert value not in entry["args"] and value not in entry["env"].values()
    assert TOKEN not in json.dumps(entry["args"])
    assert FAIL_TOKEN not in json.dumps(entry["args"])
    assert not place.exists()
    again = server_entry(token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=str(place))
    assert again == entry and again is not entry and again["env"] is not entry["env"]


@pytest.mark.parametrize(
    ("place", "error"),
    [
        (None, TypeError),
        (7, TypeError),
        (b"/bytes/secret", TypeError),
        ("", ValueError),
        ("relative/secret", ValueError),
        (Path("relative secret"), ValueError),
        ("nul\0secret", ValueError),
    ],
)
def test_the_server_entry_refuses_a_place_that_is_no_absolute_path(
    tmp_path, place, error
):
    with pytest.raises(error) as caught:
        server_entry(token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=place)
    assert_says_nothing_secret(str(caught.value).encode(), tmp_path)


def test_the_server_entry_needs_the_path_of_the_interpreter(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "executable", "")
    with pytest.raises(RuntimeError) as caught:
        server_entry(token=TOKEN, fail_token=FAIL_TOKEN, wire_copy=tmp_path / "w")
    assert_says_nothing_secret(str(caught.value).encode(), tmp_path)


WIRE_LINES = [
    (b"C", b"\xff\xfe\n"),
    (b"S", b"a\x00b\rc"),
    (b"C", b"\n"),
    (b"S", b""),
    (b"C", b"S 4\nfake\n"),
    (b"S", WIRE_COPY_MAGIC),
]


def test_the_reader_returns_any_bytes_of_either_direction(tmp_path):
    place = tmp_path / "wire-copy"
    lines = [*WIRE_LINES, (b"S", b"\x00" * 1_000_000), (b"C", bytes(range(256)))]
    place.write_bytes(WIRE_COPY_MAGIC + b"".join(record(*line) for line in lines))
    directions = {b"C": FROM_CLIENT, b"S": FROM_SERVER}
    expected = tuple((directions[mark], line) for mark, line in lines)
    assert read_wire_copy(place) == WireCopy(expected, False)
    assert read_wire_copy(str(place)) == WireCopy(expected, False)


def test_a_copy_cut_anywhere_never_yields_a_line_that_was_not_copied(tmp_path):
    place = tmp_path / "wire-copy"
    records = [record(*line) for line in WIRE_LINES]
    whole = WIRE_COPY_MAGIC + b"".join(records)
    full = read_wire_copy_of(place, whole).lines
    assert len(full) == len(WIRE_LINES)
    ends = [len(WIRE_COPY_MAGIC)]
    for one in records:
        ends.append(ends[-1] + len(one))
    for cut in range(len(whole)):
        if cut < len(WIRE_COPY_MAGIC):
            with pytest.raises(WireCopyError):
                read_wire_copy_of(place, whole[:cut])
            continue
        copy = read_wire_copy_of(place, whole[:cut])
        complete = sum(1 for end in ends[1:] if end <= cut)
        assert copy.lines == full[:complete]
        assert copy.torn is (cut not in ends)


def read_wire_copy_of(place, data):
    place.write_bytes(data)
    return read_wire_copy(place)


@pytest.mark.parametrize(
    "tail",
    [
        b"c 1\nx\n",
        b"X 1\nx\n",
        b"C1\nx\n",
        b"C  1\nx\n",
        b"C 01\nx\n",
        b"C -1\nx\n",
        b"C +1\nx\n",
        b"C 1 \nx\n",
        b"C 1\r\nx\n",
        b"C " + b"9" * 19 + b"\nx\n",
        b"C 1\nxy\n",
        b"C 2\nx\n",
        b"C 1\nx",
        b"C 1\nx\r",
        b"C \n\n",
        b"\n",
        b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n',
        WIRE_COPY_MAGIC,
    ],
)
def test_a_malformed_record_ends_the_reading_and_is_no_line(tmp_path, tail):
    place = tmp_path / "wire-copy"
    good = record(b"C", b"good\n")
    assert read_wire_copy_of(place, WIRE_COPY_MAGIC + tail) == WireCopy((), True)
    assert read_wire_copy_of(place, WIRE_COPY_MAGIC + good + tail + good) == WireCopy(
        ((FROM_CLIENT, b"good\n"),), True
    )


@pytest.mark.parametrize(
    "content",
    [
        b"",
        WIRE_COPY_MAGIC[:-1],
        WIRE_COPY_MAGIC.replace(b"1", b"2"),
        b" " + WIRE_COPY_MAGIC,
        record(b"C", b"line\n"),
        b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n',
        b"\x00\xff" * 100,
    ],
)
def test_a_file_that_is_no_wire_copy_is_told(tmp_path, content):
    with pytest.raises(WireCopyError) as caught:
        read_wire_copy_of(tmp_path / "wire-copy", content)
    assert isinstance(caught.value, ValueError)
    assert not isinstance(caught.value, OSError)
    assert_says_nothing_secret(str(caught.value).encode(), tmp_path)


def test_an_empty_wire_copy_is_not_an_error(tmp_path):
    copy = read_wire_copy_of(tmp_path / "wire-copy", WIRE_COPY_MAGIC)
    assert copy == WireCopy((), False)


def test_a_file_that_is_not_there_or_cannot_be_read_is_an_error_of_its_own(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_wire_copy(tmp_path / "missing")
    with pytest.raises(OSError) as caught:
        read_wire_copy(tmp_path)
    assert not isinstance(caught.value, WireCopyError)


@pytest.mark.parametrize("path", [None, 0, 3.5])
def test_the_reader_takes_only_a_path(path):
    with pytest.raises(TypeError):
        read_wire_copy(path)
