import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import __main__ as front
from hilclaw.__main__ import main
from hilclaw.tools import Registry, ToolFailure

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXED_NAMES = [
    "sim.run",
    "board.run",
    "profiler.collect",
    "correctness.check",
    "blob.push",
    "blob.fetch",
]
NON_ASCII = {"text": "héllo 한글 \U0001f600", "키": [1, 2.5, None, True, {"a": {}}]}

HELPER_SCRIPT = """\
import sys

sys.path.insert(0, {root!r})

from hilclaw.__main__ import main
from hilclaw.tools import Registry, ToolFailure


def fail(request):
    raise ToolFailure("backend_down", "no answer")


registry = Registry()
registry.register(
    "test.echo", lambda request: {{"echo": request}}, {description!r}, {schema!r}
)
registry.register("test.fail", fail, {description!r}, {schema!r})
raise SystemExit(main(registry=registry))
"""

DESCRIPTION = "A tool of the tests."
SCHEMA = {"type": "object"}


class Calls:
    def __init__(self):
        self.requests = []

    def echo(self, request):
        self.requests.append(request)
        return {"echo": request}


class BrokenStream(io.BytesIO):
    def write(self, data):
        raise BrokenPipeError(32, "Broken pipe")


class UnreadableStream(io.BytesIO):
    def read(self, *args):
        raise OSError(5, "Input/output error")


def raising(error):
    def tool(request):
        raise error

    return tool


def registry_with(**functions):
    registry = Registry()
    for name, function in functions.items():
        registry.register(name.replace("_", "."), function, DESCRIPTION, SCHEMA)
    return registry


def run(args, data=b"{}", registry=None, stdout=None, stderr=None, stdin=None):
    stdin = io.BytesIO(data) if stdin is None else stdin
    stdout = io.BytesIO() if stdout is None else stdout
    stderr = io.BytesIO() if stderr is None else stderr
    registry = Registry() if registry is None else registry
    status = main(args, registry=registry, stdin=stdin, stdout=stdout, stderr=stderr)
    return status, stdout.getvalue(), stderr.getvalue()


def error_of(out, kind):
    assert out.endswith(b"\n") and out.count(b"\n") == 1 and b"\r" not in out
    document = json.loads(out)
    assert list(document) == ["error"]
    assert list(document["error"]) == ["kind", "message"]
    assert document["error"]["kind"] == kind
    assert isinstance(document["error"]["message"], str)
    return document["error"]["message"]


# A result


def test_a_result_is_one_json_line_with_status_0():
    calls = Calls()
    status, out, err = run(
        ["test.echo"],
        b'{"n": 1, "list": [true, null]}\n',
        registry_with(test_echo=calls.echo),
    )
    assert status == front.EXIT_RESULT == 0
    assert out == b'{"echo":{"n":1,"list":[true,null]}}\n'
    assert err == b""
    assert calls.requests == [{"n": 1, "list": [True, None]}]


def test_a_call_reaches_a_tool_whatever_its_schema_says():
    calls = Calls()
    registry = Registry()
    schema = {"type": "object", "required": ["example_member"]}
    registry.register("test.echo", calls.echo, "Echoes the request. 한글", schema)
    status, out, err = run(["test.echo"], b"{}", registry)
    assert (status, out, err) == (0, b'{"echo":{}}\n', b"")
    assert calls.requests == [{}]


def test_a_non_ascii_request_round_trips():
    data = json.dumps(NON_ASCII, ensure_ascii=False).encode("utf-8")
    status, out, err = run(["test.echo"], data, registry_with(test_echo=Calls().echo))
    assert status == 0
    assert out.isascii() and out.endswith(b"\n") and out.count(b"\n") == 1
    assert json.loads(out) == {"echo": NON_ASCII}
    assert err == b""


def test_an_empty_request_and_an_empty_result():
    status, out, err = run(
        ["test.empty"], b"{}", registry_with(test_empty=lambda r: {})
    )
    assert (status, out, err) == (0, b"{}\n", b"")


def test_a_result_may_look_like_an_error_object():
    result = {"error": {"kind": "none", "message": "a result of the tool"}}
    status, out, _ = run(["test.odd"], b"{}", registry_with(test_odd=lambda r: result))
    assert status == 0
    assert json.loads(out) == result


# A tool failure of the call


def test_a_tool_failure_is_the_error_object_with_status_3():
    failure = ToolFailure("backend_down", "no answer from the board")
    status, out, err = run(
        ["test.fail"], b"{}", registry_with(test_fail=raising(failure))
    )
    assert status == front.EXIT_TOOL_FAILURE == 3
    assert out == (
        b'{"error":{"kind":"backend_down","message":"no answer from the board"}}\n'
    )
    assert err == b"hilclaw: backend_down: no answer from the board\n"


@pytest.mark.parametrize(
    ("error", "said"),
    [
        (ValueError("bad value"), "ValueError: bad value"),
        (OSError("gone"), "OSError: gone"),
    ]
    + [(ZeroDivisionError("by zero"), "ZeroDivisionError: by zero")],
)
def test_a_tool_that_raises_anything_else_is_a_tool_failure(error, said):
    status, out, err = run(
        ["test.crash"], b"{}", registry_with(test_crash=raising(error))
    )
    assert status == front.EXIT_TOOL_FAILURE
    assert error_of(out, "tool_crashed") == said
    assert err


@pytest.mark.parametrize(
    "result",
    [None, [], "text", {"a": float("nan")}, {"a": [float("inf")]}, {1: 2}, {"a": b"x"}],
)
def test_a_tool_that_returns_no_result_is_a_tool_failure(result):
    registry = registry_with(test_odd=lambda request: result)
    status, out, err = run(["test.odd"], b"{}", registry)
    assert status == front.EXIT_TOOL_FAILURE
    assert "not a result" in error_of(out, "bad_result")
    assert err


def test_an_interrupt_is_not_answered():
    registry = registry_with(test_stop=raising(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        run(["test.stop"], b"{}", registry)


# What the front answers by itself


@pytest.mark.parametrize("name", FIXED_NAMES)
def test_the_fixed_tool_set_is_empty_today(name):
    """No FR-10 / C-3 tool has a contract yet; this changes when the first tool lands."""
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = main([name], stdin=io.BytesIO(b"{}"), stdout=stdout, stderr=stderr)
    assert status == front.EXIT_FRONT_FAILURE == 4
    assert error_of(stdout.getvalue(), "unknown_tool") == f"unknown tool {name!r}"
    assert stderr.getvalue()


@pytest.mark.parametrize(
    "name", ["test.other", "test", "TEST.ECHO", "", "--help", "-h"]
)
def test_an_unknown_tool_name(name):
    calls = Calls()
    status, out, err = run([name], b"{}", registry_with(test_echo=calls.echo))
    assert status == front.EXIT_FRONT_FAILURE
    assert error_of(out, front.KIND_UNKNOWN_TOOL) == f"unknown tool {name!r}"
    assert err
    assert calls.requests == []


def test_an_unknown_tool_name_is_answered_without_reading_the_request():
    status, out, _ = run(["test.other"], stdin=UnreadableStream())
    assert status == front.EXIT_FRONT_FAILURE
    error_of(out, "unknown_tool")


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["test.echo", "test.echo"],
        ["test.echo", "{}"],
        ["--help", "test.echo"],
        ("a", "b", "c"),
    ],
)
def test_a_wrong_number_of_arguments(args):
    calls = Calls()
    status, out, err = run(args, b"{}", registry_with(test_echo=calls.echo))
    assert status == front.EXIT_FRONT_FAILURE
    message = error_of(out, front.KIND_BAD_USAGE)
    assert message == f"expected one tool name, got {len(args)}"
    assert err
    assert calls.requests == []


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty"),
        pytest.param(b'{"a": "\xff"}', id="not utf-8"),
        pytest.param(b"\xef\xbb\xbf{}", id="byte order mark"),
        pytest.param(b"{", id="not json"),
        pytest.param(b"[]", id="array"),
        pytest.param(b'"text"', id="string"),
        pytest.param(b"3", id="number"),
        pytest.param(b"null", id="null"),
        pytest.param(b'{"a": NaN}', id="NaN"),
        pytest.param(b'{"a": Infinity}', id="Infinity"),
        pytest.param(b'{"a": -Infinity}', id="-Infinity"),
        pytest.param(b'{"a": 1, "a": 2}', id="duplicate member"),
        pytest.param(b"{} {}", id="second object"),
        pytest.param(b"{}\nx", id="trailing text"),
        pytest.param(b"[" * 100_000, id="too deep"),
    ],
)
def test_an_input_that_is_not_a_request(data):
    calls = Calls()
    status, out, err = run(["test.echo"], data, registry_with(test_echo=calls.echo))
    assert status == front.EXIT_FRONT_FAILURE
    assert "not a request" in error_of(out, front.KIND_BAD_REQUEST)
    assert err
    assert calls.requests == []


def test_an_input_that_cannot_be_read():
    calls = Calls()
    registry = registry_with(test_echo=calls.echo)
    status, out, err = run(["test.echo"], registry=registry, stdin=UnreadableStream())
    assert status == front.EXIT_FRONT_FAILURE
    assert "cannot read standard input" in error_of(out, front.KIND_NO_INPUT)
    assert err
    assert calls.requests == []


def test_the_message_on_standard_error_survives_what_utf8_cannot_hold():
    failure = ToolFailure("refused", "lone \ud800 surrogate")
    status, out, err = run(
        ["test.fail"], b"{}", registry_with(test_fail=raising(failure))
    )
    assert status == front.EXIT_TOOL_FAILURE
    assert error_of(out, "refused") == "lone \ud800 surrogate"
    assert err == b"hilclaw: refused: lone \\ud800 surrogate\n"


# Streams that fail


def test_a_standard_output_that_cannot_be_written():
    registry = registry_with(test_echo=Calls().echo)
    status, out, err = run(["test.echo"], b"{}", registry, stdout=BrokenStream())
    assert status == front.EXIT_FRONT_FAILURE
    assert out == b""
    assert b"cannot write standard output" in err


def test_a_standard_error_that_cannot_be_written_changes_nothing():
    status, out, _ = run(["test.other"], stderr=BrokenStream())
    assert status == front.EXIT_FRONT_FAILURE
    error_of(out, "unknown_tool")


def closed():
    stream = io.BytesIO(b"{}")
    stream.close()
    return stream


def test_a_closed_stream_object_is_answered_like_a_failing_one():
    registry = registry_with(test_echo=Calls().echo)
    stdout = io.BytesIO()
    status = main(
        ["test.echo"], registry=registry, stdin=closed(), stdout=stdout, stderr=closed()
    )
    assert status == front.EXIT_FRONT_FAILURE
    error_of(stdout.getvalue(), "no_input")
    stderr = io.BytesIO()
    status = main(
        ["test.echo"],
        registry=registry,
        stdin=io.BytesIO(b"{}"),
        stdout=closed(),
        stderr=stderr,
    )
    assert status == front.EXIT_FRONT_FAILURE
    assert stderr.getvalue().startswith(b"hilclaw: cannot write standard output: ")


# Defaults


def test_main_defaults_to_the_process_arguments_and_streams(monkeypatch):
    class Standard:
        def __init__(self, data=b""):
            self.buffer = io.BytesIO(data)

    stdout, stderr = Standard(), Standard()
    monkeypatch.setattr(sys, "argv", ["python -m hilclaw", "sim.run"])
    monkeypatch.setattr(sys, "stdin", Standard(b"{}"))
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)
    assert main() == front.EXIT_FRONT_FAILURE
    error_of(stdout.buffer.getvalue(), "unknown_tool")
    assert (
        stderr.buffer.getvalue() == b"hilclaw: unknown_tool: unknown tool 'sim.run'\n"
    )


@pytest.mark.parametrize("stream", [None, io.StringIO("{}")])
def test_a_closed_standard_input_is_answered(monkeypatch, stream):
    monkeypatch.setattr(sys, "stdin", stream)
    registry = registry_with(test_echo=Calls().echo)
    stdout = io.BytesIO()
    status = main(["test.echo"], registry=registry, stdout=stdout, stderr=io.BytesIO())
    assert status == front.EXIT_FRONT_FAILURE
    message = error_of(stdout.getvalue(), "no_input")
    assert message == "cannot read standard input: it is closed"
    stdout = io.BytesIO()
    assert main(["test.other"], stdout=stdout, stderr=io.BytesIO()) == 4
    error_of(stdout.getvalue(), "unknown_tool")
    stdout = io.BytesIO()
    assert main([], stdout=stdout, stderr=io.BytesIO()) == 4
    error_of(stdout.getvalue(), "bad_usage")


@pytest.mark.parametrize("stream", [None, io.StringIO()])
def test_a_closed_standard_error_loses_no_answer(monkeypatch, stream):
    monkeypatch.setattr(sys, "stderr", stream)
    registry = registry_with(test_echo=Calls().echo)
    stdin, stdout = io.BytesIO(b"{}"), io.BytesIO()
    assert main(["test.echo"], registry=registry, stdin=stdin, stdout=stdout) == 0
    assert stdout.getvalue() == b'{"echo":{}}\n'
    stdin, stdout = io.BytesIO(b"{}"), io.BytesIO()
    assert main(["test.other"], stdin=stdin, stdout=stdout) == 4
    error_of(stdout.getvalue(), "unknown_tool")


@pytest.mark.parametrize("stream", [None, io.StringIO()])
def test_a_closed_standard_output_is_status_4(monkeypatch, stream):
    monkeypatch.setattr(sys, "stdout", stream)
    registry = registry_with(test_echo=Calls().echo)
    stdin, stderr = io.BytesIO(b"{}"), io.BytesIO()
    assert main(["test.echo"], registry=registry, stdin=stdin, stderr=stderr) == 4
    assert stderr.getvalue() == b"hilclaw: cannot write standard output: it is closed\n"


def test_a_process_started_without_standard_error_still_answers():
    code = "import os, runpy, sys; os.close(2); sys.stderr = None; "
    code += "sys.argv = ['hilclaw', 'sim.run']; runpy.run_module('hilclaw', run_name='__main__')"
    done = subprocess.run(
        [sys.executable, "-c", code],
        input=b"{}",
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert done.returncode == 4
    error_of(done.stdout, "unknown_tool")


# Through a real process


def run_module(args, data):
    return subprocess.run(
        [sys.executable, "-m", "hilclaw", *args],
        input=data,
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )


def run_helper(tmp_path, name, data):
    script = tmp_path / "front_with_test_tools.py"
    text = HELPER_SCRIPT.format(
        root=str(REPO_ROOT), description=DESCRIPTION, schema=SCHEMA
    )
    script.write_text(text, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(script), name],
        input=data,
        capture_output=True,
        cwd=tmp_path,
        timeout=60,
        check=False,
    )


def test_process_unknown_tool():
    done = run_module(["sim.run"], b"{}\r\n")
    assert done.returncode == 4
    assert done.stdout == (
        b'{"error":{"kind":"unknown_tool","message":"unknown tool \'sim.run\'"}}\n'
    )
    assert done.stderr.strip()


@pytest.mark.parametrize("args", [[], ["sim.run", "board.run"]])
def test_process_wrong_number_of_arguments(args):
    done = run_module(args, b"{}")
    assert done.returncode == 4
    error_of(done.stdout, "bad_usage")
    assert done.stderr.strip()


def test_process_help_is_not_a_result():
    done = run_module(["--help"], b"")
    assert done.returncode == 4
    error_of(done.stdout, "unknown_tool")


def test_process_result_is_exact_bytes_with_one_lf(tmp_path):
    data = json.dumps(NON_ASCII, ensure_ascii=False).encode("utf-8") + b"\r\n"
    done = run_helper(tmp_path, "test.echo", data)
    assert done.returncode == 0
    assert (
        done.stdout
        == json.dumps(
            {"echo": NON_ASCII}, ensure_ascii=True, separators=(",", ":")
        ).encode("ascii")
        + b"\n"
    )
    assert b"\r" not in done.stdout
    assert done.stderr == b""


def test_process_malformed_input(tmp_path):
    done = run_helper(tmp_path, "test.echo", b'{"a": NaN}')
    assert done.returncode == 4
    assert "not a request" in error_of(done.stdout, "bad_request")
    assert done.stderr.strip()


def test_process_tool_failure(tmp_path):
    done = run_helper(tmp_path, "test.fail", b"{}")
    assert done.returncode == 3
    assert done.stdout == b'{"error":{"kind":"backend_down","message":"no answer"}}\n'
    assert done.stderr.replace(b"\r\n", b"\n") == b"hilclaw: backend_down: no answer\n"
