import io
import json
import os
import re
import tempfile
from pathlib import Path

import pytest

from hilclaw import __main__ as cli_front
from hilclaw import coder_call, coder_tool, keys, layout, mcp_front, scratch, tools
from hilclaw.coder_call import CoderNotStartedError
from hilclaw.coder_tool import NAME, NoContainerRuntime, definition

# Synthetic values only: no record, key, member or tuple of a real run.
RUN_ID = "synthetic-run-1"
TUPLE = (0, 1, 1)
KERNEL = b"/* synthetic kernel */\n"
MODEL = "claude-test-model-1"
HW = {
    "schema_version": 1,
    "accelerator": "synthetic_accel",
    "revision": "synthetic-rev-A",
    "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
    "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
    "hw_source": "in_house",
}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 3, "k": 5, "n": 7},
    "dtype": "synthetic_dtype",
    "layout": "synthetic_layout",
}
RESULT = {"taken": ["kernel.c"], "scratch_removed": True}


def request(**members):
    made = {"run_id": RUN_ID, "round": 0, "candidate": 1, "attempt": 1}
    made.update(members)
    return made


def instance_content(**changes):
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(HW).name, "record": HW},
        "coder_model": MODEL,
        **changes,
    }
    return (
        json.dumps({k: v for k, v in made.items() if v is not None}) + "\n"
    ).encode()


def spec_content():
    document = {
        "schema_version": 2,
        "id": {
            "run_id": RUN_ID,
            "round": 0,
            "candidate": 1,
            "attempt": 1,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": {"key": keys.hw_profile_key(HW).name, "record": HW},
        "task": {
            "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
            "contract": {
                "language": "synthetic_lang",
                "prototype": "synthetic prototype text",
                "operands": [
                    {
                        "name": "synthetic_a",
                        "role": "input",
                        "dtype": "synthetic_dtype",
                        "shape": [3, 5],
                    }
                ],
            },
            "objective": {
                "objectives": [{"type": "latency_minimisation"}],
                "constraints": [],
            },
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }
    return (json.dumps(document) + "\n").encode()


class StubRuntime:
    def __init__(self, *, available=True, status=0, files=None, error=None):
        self._available = available
        self.status = status
        self.files = {"kernel.c": KERNEL} if files is None else files
        self.error = error
        self.asked = 0
        self.models = []

    def available(self):
        self.asked += 1
        return self._available

    def run(self, scratch_root, *, coder_model):
        self.models.append(coder_model)
        if self.error is not None:
            raise self.error
        output = Path(scratch_root) / "output"
        output.mkdir()
        for name, data in self.files.items():
            (output / name).write_bytes(data)
        return self.status


class CountingSource:
    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.root


@pytest.fixture(autouse=True)
def parent(tmp_path, monkeypatch):
    directory = tmp_path / "scratches"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


@pytest.fixture
def data_root(tmp_path):
    root = tmp_path / "data"
    instance = layout.run_file(root, RUN_ID, "instance.json")
    instance.parent.mkdir(parents=True)
    instance.write_bytes(instance_content())
    spec = layout.attempt_artefact(root, RUN_ID, *TUPLE, "spec.json")
    spec.parent.mkdir(parents=True)
    spec.write_bytes(spec_content())
    return root


@pytest.fixture
def source(data_root):
    return CountingSource(data_root)


def output_path(data_root):
    return layout.attempt_artefact(data_root, RUN_ID, *TUPLE, "output")


def tree(root):
    return sorted(
        (path.relative_to(root).as_posix(), path.is_file() and path.read_bytes())
        for path in Path(root).rglob("*")
    )


def failure_of(function, req):
    with pytest.raises(tools.ToolFailure) as caught:
        function(req)
    return caught.value


def mcp_call(registry, arguments):
    lines = [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "coder_run", "arguments": arguments},
        },
    ]
    data = b"".join(json.dumps(line).encode() + b"\n" for line in lines)
    stdout = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=registry,
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0
    listed, called = (json.loads(line) for line in stdout.getvalue().splitlines())
    (block,) = called["result"]["content"]
    return (
        listed["result"]["tools"],
        called["result"]["isError"],
        json.loads(block["text"]),
    )


# Happy path


def test_the_tool_performs_the_call_and_brings_the_kernel_in(data_root, source, parent):
    runtime = StubRuntime(files={"kernel.c": KERNEL, "notes.txt": b"x"})
    assert definition(source, runtime).function(request()) == RESULT
    assert runtime.models == [MODEL]
    assert source.calls == 1
    assert sorted(os.listdir(output_path(data_root))) == ["kernel.c"]
    assert (output_path(data_root) / "kernel.c").read_bytes() == KERNEL
    assert list(parent.iterdir()) == []


def test_the_tool_answers_through_tools_call(data_root, source):
    registry = tools.Registry()
    registry.register(*definition(source, StubRuntime()))
    assert tools.call(registry, NAME, request()) == RESULT
    assert (output_path(data_root) / "kernel.c").read_bytes() == KERNEL


def test_the_tool_answers_through_the_mcp_front(data_root, source):
    registry = tools.Registry()
    registry.register(*definition(source, StubRuntime()))
    listed, failed, answer = mcp_call(registry, request())
    assert [tool["name"] for tool in listed] == ["coder_run"]
    assert (failed, answer) == (False, RESULT)
    assert (output_path(data_root) / "kernel.c").read_bytes() == KERNEL


def test_definition_returns_the_name_description_and_schema(source):
    held = definition(source, StubRuntime())
    assert isinstance(held, tools.ToolDefinition)
    assert (held.name, held.description) == ("coder.run", coder_tool._DESCRIPTION)
    assert held.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 0, "maximum": keys.MAX_INTEGER},
            "candidate": {"type": "integer", "minimum": 1, "maximum": keys.MAX_INTEGER},
            "attempt": {"type": "integer", "minimum": 1, "maximum": keys.MAX_INTEGER},
        },
        "required": ["run_id", "round", "candidate", "attempt"],
        "additionalProperties": False,
    }


def test_the_description_names_every_kind_in_the_order_of_the_function():
    text = coder_tool._DESCRIPTION.split("checked in this order", 1)[1]
    found = [
        re.search(rf"(?<!\w){kind}(?!\w)", text) for kind in coder_call.FAILURE_KINDS
    ]
    assert None not in found
    positions = [match.start() for match in found]
    assert positions == sorted(positions)
    for words in ("spec.write", "taken", "scratch_removed", "data root"):
        assert words in coder_tool._DESCRIPTION
    assert "install" not in coder_tool._DESCRIPTION.lower()


# The package runtime


def test_the_package_runtime_reports_no_container_runtime_and_starts_nothing(tmp_path):
    runtime = NoContainerRuntime()
    assert runtime.available() is False
    before = tree(tmp_path)
    with pytest.raises(CoderNotStartedError):
        runtime.run(str(tmp_path / "scratch"), coder_model=MODEL)
    assert tree(tmp_path) == before
    with pytest.raises(TypeError):
        NoContainerRuntime("option")


def test_the_tool_with_the_package_runtime_fails_and_creates_nothing(
    data_root, source, parent
):
    before = tree(data_root)
    failed = failure_of(definition(source, NoContainerRuntime()).function, request())
    assert failed.kind == coder_call.KIND_NO_CONTAINER_RUNTIME
    assert failed.message == "no container runtime is available"
    assert tree(data_root) == before
    assert list(parent.iterdir()) == []


def test_the_default_registry_gives_no_container_runtime(data_root, parent):
    before = tree(data_root)
    registry = tools.default_registry(lambda: data_root)
    with pytest.raises(tools.ToolFailure) as caught:
        tools.call(registry, NAME, request())
    assert (caught.value.kind, caught.value.message) == (
        "no_container_runtime",
        "no container runtime is available",
    )
    assert tree(data_root) == before
    assert list(parent.iterdir()) == []


# Pass-through of the function's kinds


def assert_passed_through(source, runtime, req, kind):
    failed = failure_of(definition(source, runtime).function, req)
    with pytest.raises(tools.ToolFailure) as direct:
        coder_call.call(req, source=source, runtime=runtime)
    assert failed.kind == kind
    assert (failed.kind, failed.message) == (direct.value.kind, direct.value.message)
    return failed


@pytest.mark.parametrize(
    "req",
    [
        request(extra=1),
        {"run_id": RUN_ID, "round": 0, "candidate": 1},
        request(run_id="Bad Run"),
        request(round=-1),
        request(attempt=True),
        request(candidate=0),
        request(round=keys.MAX_INTEGER + 1),
    ],
)
def test_an_invalid_request_passes_through_before_the_source(source, req):
    runtime = StubRuntime()
    assert_passed_through(source, runtime, req, "invalid_request")
    assert (source.calls, runtime.asked) == (0, 0)


def test_no_data_root_passes_through(tmp_path):
    source = CountingSource(tmp_path / "absent")
    assert_passed_through(source, StubRuntime(), request(), "no_data_root")


def test_a_missing_instance_passes_through(data_root, source):
    layout.run_file(data_root, RUN_ID, "instance.json").unlink()
    assert_passed_through(source, StubRuntime(), request(), "run_file_missing")


def test_an_unstated_coder_model_passes_through(data_root, source):
    path = layout.run_file(data_root, RUN_ID, "instance.json")
    path.write_bytes(instance_content(coder_model=None))
    assert_passed_through(source, StubRuntime(), request(), "coder_model_not_stated")


def test_an_existing_output_passes_through(data_root, source):
    output_path(data_root).mkdir()
    assert_passed_through(source, StubRuntime(), request(), "output_exists")


def test_a_missing_spec_passes_through(data_root, source):
    layout.attempt_artefact(data_root, RUN_ID, *TUPLE, "spec.json").unlink()
    runtime = StubRuntime()
    assert_passed_through(source, runtime, request(), scratch.SPEC_UNREADABLE)
    assert runtime.asked == 0


def test_a_coder_not_started_passes_through(data_root, source, parent):
    runtime = StubRuntime(error=CoderNotStartedError("synthetic"))
    failed = failure_of(definition(source, runtime).function, request())
    assert (failed.kind, failed.message) == (
        "coder_not_started",
        "the coder could not be started",
    )
    assert list(parent.iterdir()) == []


def test_a_coder_not_ended_passes_through(data_root, source):
    failed = failure_of(definition(source, StubRuntime(status=1)).function, request())
    assert failed.kind == "coder_not_ended"
    assert failed.message == (
        "the coder process ended with status 1; nothing was brought in"
    )
    assert not os.path.lexists(output_path(data_root))


# Negative and error cases


@pytest.mark.parametrize("bad", [None, "data", 3])
def test_definition_refuses_a_source_that_is_not_callable(bad):
    with pytest.raises(TypeError, match="data-root source must be callable"):
        definition(bad, StubRuntime())


class OnlyAvailable:
    def available(self):
        raise AssertionError("not asked at definition time")


class RunNotCallable:
    run = None

    def available(self):
        raise AssertionError("not asked at definition time")


@pytest.mark.parametrize(
    ("runtime", "method"),
    [
        (None, "available"),
        (object(), "available"),
        (OnlyAvailable(), "run"),
        (RunNotCallable(), "run"),
    ],
)
def test_definition_refuses_a_runtime_without_both_methods(source, runtime, method):
    with pytest.raises(TypeError, match=f"callable {method}"):
        definition(source, runtime)
    assert source.calls == 0


def test_definition_neither_asks_the_source_nor_uses_the_runtime(source):
    runtime = StubRuntime()
    definition(source, runtime)
    assert (source.calls, runtime.asked, runtime.models) == (0, 0, [])


def test_another_exception_of_the_runtime_propagates_unchanged(
    data_root, source, parent
):
    error = RuntimeError("synthetic runtime fault")
    function = definition(source, StubRuntime(error=error)).function
    with pytest.raises(RuntimeError) as caught:
        function(request())
    assert caught.value is error
    assert list(parent.iterdir()) == []
    registry = tools.Registry()
    registry.register(*definition(source, StubRuntime(error=RuntimeError("x"))))
    with pytest.raises(tools.ToolFailure) as crashed:
        tools.call(registry, NAME, request())
    assert crashed.value.kind == tools.KIND_TOOL_CRASHED


def test_no_call_is_journaled(data_root, source):
    events = layout.run_file(data_root, RUN_ID, "events.ndjson")
    events.write_bytes(b"")
    function = definition(source, StubRuntime(status=1)).function
    failure_of(function, request())
    failure_of(definition(source, NoContainerRuntime()).function, request())
    assert definition(source, StubRuntime()).function(request()) == RESULT
    assert events.read_bytes() == b""
    assert [p.name for p in data_root.rglob("events.ndjson")] == ["events.ndjson"]


# The registry and the fronts


def test_the_default_registry_holds_the_tool(data_root):
    registry = tools.default_registry(lambda: data_root)
    assert NAME in registry.names()
    held = registry.definition(NAME)
    made = definition(lambda: data_root, NoContainerRuntime())
    assert (held.description, held.input_schema) == (
        made.description,
        made.input_schema,
    )


def test_the_mcp_front_lists_and_calls_coder_run_of_the_default_registry(data_root):
    listed, failed, answer = mcp_call(
        tools.default_registry(lambda: data_root), request()
    )
    assert "coder_run" in [tool["name"] for tool in listed]
    assert failed is True
    assert answer["error"]["kind"] == "no_container_runtime"


def test_the_command_line_front_answers_coder_run(source):
    registry = tools.Registry()
    registry.register(*definition(source, StubRuntime()))
    stdout = io.BytesIO()
    status = cli_front.main(
        [NAME],
        registry=registry,
        stdin=io.BytesIO(json.dumps(request()).encode()),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert (status, json.loads(stdout.getvalue())) == (0, RESULT)
