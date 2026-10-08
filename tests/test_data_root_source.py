import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import __main__ as command_line
from hilclaw import config, mcp_front, tools
from hilclaw.data_root_source import configured, obtain
from hilclaw.tools import Registry, ToolFailure

REPO_ROOT = Path(__file__).resolve().parent.parent
DESCRIPTION = "A tool of the tests."
SCHEMA = {"type": "object"}

HELPER_SCRIPT = """\
import sys

sys.path.insert(0, {root!r})

from hilclaw import __main__, data_root_source, mcp_front
from hilclaw.tools import Registry


def root(request):
    found = data_root_source.obtain(data_root_source.configured)
    return {{"entries": sorted(entry.name for entry in found.iterdir())}}


registry = Registry()
registry.register("test.root", root, "A tool of the tests.", {{"type": "object"}})
front = mcp_front if sys.argv[1] == "mcp" else __main__
raise SystemExit(front.main(sys.argv[2:], registry=registry))
"""


class Source:
    def __init__(self, *answers):
        self.answers = answers
        self.calls = 0

    def __call__(self):
        self.calls += 1
        answer = self.answers[min(self.calls, len(self.answers)) - 1]
        if isinstance(answer, BaseException):
            raise answer
        return answer


class Named:
    def __init__(self, value):
        self.value = value

    def __fspath__(self):
        if isinstance(self.value, Exception):
            raise self.value
        return self.value

    def __repr__(self):
        raise RuntimeError("no text for this value")


class Text(str):
    pass


def rooted(source):
    def tool(request):
        if "refused" in request:
            raise ToolFailure(tools.KIND_INVALID_REQUEST, "refused is no member")
        return {"entries": sorted(entry.name for entry in obtain(source).iterdir())}

    return tool


def registry_of(source):
    registry = Registry()
    registry.register("test.root", rooted(source), DESCRIPTION, SCHEMA)
    registry.register(
        "test.plain", lambda request: {"plain": True}, DESCRIPTION, SCHEMA
    )
    return registry


def through_command_line(registry, name, request=None):
    stdin = io.BytesIO(json.dumps({} if request is None else request).encode())
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        [name], registry=registry, stdin=stdin, stdout=stdout, stderr=stderr
    )
    return status, json.loads(stdout.getvalue())


def mcp_line(request_id, method, **params):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return json.dumps(document).encode() + b"\n"


def through_mcp(registry, *lines):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=registry,
        stdin=io.BytesIO(b"".join(lines)),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def outcome_of(document):
    (block,) = document["result"]["content"]
    return document["result"]["isError"], json.loads(block["text"])


def no_data_root(error, part):
    assert error.kind == tools.KIND_NO_DATA_ROOT == "no_data_root"
    assert part in error.message
    return error


def everything_under(directory):
    return sorted(directory.rglob("*"))


@pytest.fixture
def tree(tmp_path):
    directory = tmp_path / "one"
    directory.mkdir()
    (directory / "a").write_bytes(b"")
    (directory / "b").mkdir()
    return directory


@pytest.fixture
def other(tmp_path):
    directory = tmp_path / "two"
    directory.mkdir()
    (directory / "c").write_bytes(b"")
    return directory


@pytest.fixture
def no_configuration(monkeypatch, tmp_path):
    missing = tmp_path / "missing.config.json"
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", missing)
    return missing


# obtain: the data root


@pytest.mark.parametrize("form", [str, Path, Text, lambda path: Named(str(path))])
def test_obtain_returns_the_directory_the_source_names(tree, form):
    source = Source(form(tree))
    found = obtain(source)
    assert type(found) is type(tree)
    assert found == tree
    assert source.calls == 1


def test_obtain_asks_once_at_each_call_and_keeps_no_answer(tree, other):
    source = Source(tree, other)
    assert [obtain(source), obtain(source), obtain(source)] == [tree, other, other]
    assert source.calls == 3


def test_obtain_does_not_resolve_a_relative_path(tree, monkeypatch):
    monkeypatch.chdir(tree.parent)
    found = obtain(Source("one"))
    assert found == Path("one")
    assert not found.is_absolute()


def test_obtain_follows_a_symbolic_link_to_a_directory(tree, tmp_path):
    link = tmp_path / "link"
    try:
        os.symlink(tree, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("no symbolic link can be made here")
    assert obtain(Source(link)) == link


def test_obtain_changes_nothing_in_the_directory(tree, tmp_path):
    before = everything_under(tmp_path)
    obtain(Source(tree))
    assert everything_under(tmp_path) == before


# obtain: no data root


@pytest.mark.parametrize(
    "error",
    [
        config.ConfigError("example.json: data_repo.url: missing"),
        OSError(5, "Input/output error"),
        RuntimeError("the source is broken"),
        ToolFailure("backend_down", "raised by a source"),
        ToolFailure(tools.KIND_INVALID_REQUEST, "raised by a source"),
    ],
)
def test_a_source_that_raises_is_no_data_root(error, tmp_path):
    source = Source(error)
    with pytest.raises(ToolFailure) as raised:
        obtain(source)
    no_data_root(raised.value, "the data-root source failed: ")
    assert type(error).__name__ in raised.value.message
    assert str(error) in raised.value.message
    assert raised.value.__cause__ is error
    assert source.calls == 1
    assert everything_under(tmp_path) == []


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(9), GeneratorExit()])
def test_what_is_no_exception_passes_through(error):
    with pytest.raises(type(error)) as raised:
        obtain(Source(error))
    assert raised.value is error


def test_a_missing_path_is_no_data_root(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(ToolFailure) as raised:
        obtain(Source(missing))
    no_data_root(raised.value, "not an existing directory")
    assert str(missing) in raised.value.message
    assert raised.value.__cause__ is None
    assert everything_under(tmp_path) == []


def test_a_file_is_no_data_root(tree, tmp_path):
    before = everything_under(tmp_path)
    with pytest.raises(ToolFailure) as raised:
        obtain(Source(str(tree / "a")))
    no_data_root(raised.value, "not an existing directory")
    assert str(tree / "a") in raised.value.message
    assert everything_under(tmp_path) == before


def test_a_path_the_platform_cannot_ask_about_is_no_data_root(tmp_path):
    with pytest.raises(ToolFailure) as raised:
        obtain(Source(str(tmp_path) + "\0"))
    no_data_root(raised.value, "not an existing directory")


@pytest.mark.parametrize(
    "answer",
    [
        "",
        Text(""),
        None,
        b".",
        0,
        1.5,
        True,
        ["."],
        config.DataRepo("https://example.invalid/data", Path(".")),
        Named(b"."),
        Named(None),
        Named(""),
        Named(RuntimeError("no path today")),
        Named(OSError(5, "Input/output error")),
    ],
)
def test_what_is_no_path_is_no_data_root(answer, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = Source(answer)
    with pytest.raises(ToolFailure) as raised:
        obtain(source)
    no_data_root(raised.value, "named no path")
    assert type(answer).__name__ in raised.value.message
    assert source.calls == 1
    assert everything_under(tmp_path) == []


@pytest.mark.parametrize("source", [None, ".", Path("."), 3, b"."])
def test_obtain_of_what_is_not_callable_is_a_type_error(source):
    with pytest.raises(TypeError, match="must be callable"):
        obtain(source)


# configured: the source of the fronts


def test_configured_is_the_local_path_of_the_loader(tree, monkeypatch):
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(tree))
    assert configured() == config.load_data_repo().local_path == tree
    assert obtain(configured) == tree


def test_configured_reads_the_committed_file_through_the_default_path(monkeypatch):
    monkeypatch.delenv(config.ENV_LOCAL_PATH, raising=False)
    monkeypatch.delenv(config.ENV_URL, raising=False)
    found = configured()
    assert found == REPO_ROOT.parent / "HIL-Claw-data"
    assert isinstance(found, Path) and found.is_absolute()


def test_configured_follows_the_environment_between_two_calls(tree, other, monkeypatch):
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(tree))
    assert configured() == tree
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(other))
    assert configured() == other
    assert obtain(configured) == other


def test_configured_follows_the_configuration_file_between_two_calls(
    tree, other, tmp_path, monkeypatch
):
    monkeypatch.delenv(config.ENV_LOCAL_PATH, raising=False)
    path = tmp_path / "hilclaw.config.json"
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", path)
    for directory in (tree, other):
        document = {"data_repo": {"url": "u", "local_path": str(directory)}}
        path.write_text(json.dumps(document), encoding="utf-8")
        assert configured() == directory


def test_configured_does_not_check_that_the_directory_exists(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(tmp_path / "missing"))
    assert configured() == tmp_path / "missing"
    assert everything_under(tmp_path) == []


def test_configured_raises_what_the_loader_raises(no_configuration):
    with pytest.raises(config.ConfigError, match="cannot read"):
        configured()


def test_a_missing_configuration_file_is_no_data_root(no_configuration, tmp_path):
    with pytest.raises(ToolFailure) as raised:
        obtain(configured)
    no_data_root(raised.value, f"ConfigError: {no_configuration}: cannot read")
    assert isinstance(raised.value.__cause__, config.ConfigError)
    assert everything_under(tmp_path) == []


def test_a_configuration_file_that_is_not_json_is_no_data_root(no_configuration):
    no_configuration.write_text("{", encoding="utf-8")
    with pytest.raises(ToolFailure) as raised:
        obtain(configured)
    no_data_root(raised.value, f"{no_configuration}: not valid JSON")


def test_a_configured_directory_that_is_missing_is_no_data_root(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_LOCAL_PATH, str(tmp_path / "missing"))
    with pytest.raises(ToolFailure) as raised:
        obtain(configured)
    no_data_root(raised.value, str(tmp_path / "missing"))
    assert everything_under(tmp_path) == []


# A tool bound to a source, through tools.call and the two fronts


def test_a_bound_tool_answers_alike_through_the_three_ways(tree):
    source = Source(tree)
    registry = registry_of(source)
    expected = {"entries": ["a", "b"]}
    assert tools.call(registry, "test.root", {}) == expected
    assert through_command_line(registry, "test.root") == (0, expected)
    (document,) = through_mcp(registry, mcp_line(1, "tools/call", name="test_root"))
    assert outcome_of(document) == (False, expected)
    assert source.calls == 3


def test_the_answer_is_not_kept_for_a_later_call(tree, other):
    registry = registry_of(Source(tree, other))
    assert tools.call(registry, "test.root", {}) == {"entries": ["a", "b"]}
    assert tools.call(registry, "test.root", {}) == {"entries": ["c"]}


def test_one_mcp_session_asks_at_each_call(tree, other):
    source = Source(tree, other)
    first, second = through_mcp(
        registry_of(source),
        mcp_line(1, "tools/call", name="test_root"),
        mcp_line(2, "tools/call", name="test_root"),
    )
    assert outcome_of(first) == (False, {"entries": ["a", "b"]})
    assert outcome_of(second) == (False, {"entries": ["c"]})
    assert source.calls == 2


def test_a_registry_of_the_mcp_front_follows_the_environment(tree, other, monkeypatch):
    registry = registry_of(configured)
    stdout = io.BytesIO()
    for request_id, directory in enumerate((tree, other, tree / "missing")):
        monkeypatch.setenv(config.ENV_LOCAL_PATH, str(directory))
        stdin = io.BytesIO(mcp_line(request_id, "tools/call", name="test_root"))
        assert mcp_front.main([], registry=registry, stdin=stdin, stdout=stdout) == 0
    first, second, third = (json.loads(line) for line in stdout.getvalue().splitlines())
    assert outcome_of(first) == (False, {"entries": ["a", "b"]})
    assert outcome_of(second) == (False, {"entries": ["c"]})
    failed, answer = outcome_of(third)
    assert failed is True and answer["error"]["kind"] == "no_data_root"


def test_nothing_but_a_call_that_needs_the_data_root_asks(tree):
    source = Source(tree)
    registry = registry_of(source)
    assert registry.names() == ("test.plain", "test.root")
    registry.get("test.root")
    registry.definition("test.root")
    with pytest.raises(tools.UnknownToolError):
        tools.call(registry, "test.unknown", {})
    assert tools.call(registry, "test.plain", {}) == {"plain": True}
    status, answer = through_command_line(registry, "test.unknown")
    assert (status, answer["error"]["kind"]) == (4, "unknown_tool")
    assert through_command_line(registry, "test.plain") == (0, {"plain": True})
    listed, unknown, plain = through_mcp(
        registry,
        mcp_line(1, "tools/list"),
        mcp_line(2, "tools/call", name="test_unknown"),
        mcp_line(3, "tools/call", name="test_plain"),
    )
    assert [tool["name"] for tool in listed["result"]["tools"]] == [
        "test_plain",
        "test_root",
    ]
    assert unknown["error"]["code"] == -32602
    assert outcome_of(plain) == (False, {"plain": True})
    assert source.calls == 0


def test_a_refused_request_does_not_ask(tree):
    source = Source(tree)
    registry = registry_of(source)
    with pytest.raises(ToolFailure) as raised:
        tools.call(registry, "test.root", {"refused": 1})
    assert raised.value.kind == "invalid_request"
    status, answer = through_command_line(registry, "test.root", {"refused": 1})
    assert (status, answer["error"]["kind"]) == (3, "invalid_request")
    (document,) = through_mcp(
        registry, mcp_line(1, "tools/call", name="test_root", arguments={"refused": 1})
    )
    failed, answer = outcome_of(document)
    assert failed is True and answer["error"]["kind"] == "invalid_request"
    assert source.calls == 0


def test_a_refused_request_is_refused_alike_without_a_data_root():
    registry = registry_of(Source(RuntimeError("the source is broken")))
    status, answer = through_command_line(registry, "test.root", {"refused": 1})
    assert (status, answer["error"]["kind"]) == (3, "invalid_request")


def test_a_tool_that_needs_no_data_root_works_with_a_failing_source():
    source = Source(RuntimeError("the source is broken"))
    registry = registry_of(source)
    assert tools.call(registry, "test.plain", {}) == {"plain": True}
    assert through_command_line(registry, "test.plain") == (0, {"plain": True})
    (document,) = through_mcp(registry, mcp_line(1, "tools/call", name="test_plain"))
    assert outcome_of(document) == (False, {"plain": True})
    assert source.calls == 0


@pytest.mark.parametrize(
    ("answer", "part"),
    [
        (RuntimeError("the source is broken"), "RuntimeError: the source is broken"),
        (config.ConfigError("example.json: cannot read"), "example.json: cannot read"),
        ("missing", "not an existing directory: missing"),
        ("", "named no path"),
        (None, "named no path"),
    ],
)
def test_no_data_root_reaches_the_caller_as_a_tool_failure(
    answer, part, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    source = Source(answer)
    registry = registry_of(source)
    with pytest.raises(ToolFailure) as raised:
        tools.call(registry, "test.root", {})
    expected = no_data_root(raised.value, part).error_object()
    assert through_command_line(registry, "test.root") == (3, expected)
    listed, called = through_mcp(
        registry,
        mcp_line(1, "tools/list"),
        mcp_line(2, "tools/call", name="test_root"),
    )
    assert len(listed["result"]["tools"]) == 2
    assert outcome_of(called) == (True, expected)
    assert expected["error"]["kind"] != tools.KIND_TOOL_CRASHED
    assert source.calls == 3
    assert everything_under(tmp_path) == []


def test_no_data_root_is_written_as_every_tool_failure_is(tmp_path):
    registry = registry_of(Source(tmp_path / "missing"))
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        ["test.root"],
        registry=registry,
        stdin=io.BytesIO(b"{}"),
        stdout=stdout,
        stderr=stderr,
    )
    assert status == command_line.EXIT_TOOL_FAILURE == 3
    answer = json.loads(stdout.getvalue())
    assert list(answer) == ["error"]
    assert list(answer["error"]) == ["kind", "message"]
    assert answer["error"]["kind"] == "no_data_root"
    assert stderr.getvalue().startswith(b"hilclaw: no_data_root: ")


def test_an_interrupt_of_a_source_is_not_answered():
    registry = registry_of(Source(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        tools.call(registry, "test.root", {})


# Through a real process


def run_front(tmp_path, front, data, local_path, *args):
    script = tmp_path / "fronts_with_a_rooted_tool.py"
    script.write_text(HELPER_SCRIPT.format(root=str(REPO_ROOT)), encoding="utf-8")
    environ = dict(os.environ)
    environ.pop(config.ENV_URL, None)
    environ[config.ENV_LOCAL_PATH] = str(local_path)
    done = subprocess.run(
        [sys.executable, str(script), front, *args],
        input=data,
        capture_output=True,
        cwd=tmp_path,
        env=environ,
        timeout=60,
        check=False,
    )
    return done.returncode, json.loads(done.stdout)


def both_fronts(tmp_path, local_path):
    status, answer = run_front(tmp_path, "cli", b"{}", local_path, "test.root")
    line = mcp_line(1, "tools/call", name="test_root", arguments={})
    served, document = run_front(tmp_path, "mcp", line, local_path)
    assert served == 0
    return status, answer, outcome_of(document)


def test_process_both_fronts_answer_from_the_configured_directory(tree, tmp_path):
    status, answer, (failed, served) = both_fronts(tmp_path, tree)
    assert status == 0 and failed is False
    assert answer == served == {"entries": ["a", "b"]}


def test_process_both_fronts_answer_no_data_root(tmp_path):
    missing = tmp_path / "missing"
    status, answer, (failed, served) = both_fronts(tmp_path, missing)
    assert status == 3 and failed is True
    assert answer == served
    assert answer["error"]["kind"] == "no_data_root"
    assert str(missing) in answer["error"]["message"]
    assert not missing.exists()
