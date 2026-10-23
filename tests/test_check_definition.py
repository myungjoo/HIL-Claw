import ast
import copy
import inspect
import io
import json
import re
import struct
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    __main__,
    backends,
    check_definition,
    check_identity,
    check_tool,
    data_root_source,
    events,
    gemm_contract,
    keys,
    layout,
    mcp_front,
    mock_backend,
    mock_check,
    run_state,
    tools,
)
from hilclaw.backends import Backend, BackendTable
from hilclaw.check_definition import (
    DESCRIPTION,
    default_table,
    definition,
    input_schema,
)
from hilclaw.check_parameters import CheckParameters
from hilclaw.harness import seed_source
from hilclaw.journal import EMPTY

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = "correctness.check"
# ADR-0069 decision 4, written out.
SCHEMA = {
    "type": "object",
    "properties": {
        "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
        "round": {"type": "integer", "minimum": 0, "maximum": 9007199254740991},
        "candidate": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "attempt": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "execution": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
        "point": {"type": "string", "enum": ["sim", "board"]},
    },
    "required": ["run_id", "round", "candidate", "attempt", "execution", "point"],
    "additionalProperties": False,
}


def stub(request):
    raise AssertionError("the stub was called")


def test_the_schema_is_that_of_the_record():
    schema = input_schema()
    assert schema == SCHEMA
    assert type(schema["additionalProperties"]) is bool
    assert keys.MAX_INTEGER == 9007199254740991
    tools.check_json_object(schema)


def test_the_required_members_and_the_properties_are_the_members_of_a_request():
    schema = input_schema()
    assert schema["required"] == list(check_identity.MEMBERS)
    assert tuple(schema["properties"]) == check_identity.MEMBERS
    assert schema["properties"]["point"]["enum"] == [
        check_identity.SIM,
        check_identity.BOARD,
    ]


@pytest.mark.parametrize(
    "run_id",
    ["r1", "0", "a" * 64, "a" * 65, "", "R1", "-a", "_a", "a-b_c", "a.b", "a\n", "a b"],
)
def test_the_pattern_states_the_run_id_the_layout_accepts(run_id):
    pattern = input_schema()["properties"]["run_id"]["pattern"]
    # An ECMA-262 "$" ends the input only, as Python's "\Z" does.
    pattern = pattern.removesuffix("$") + r"\Z"
    try:
        layout.check_run_id(run_id)
        accepted = True
    except ValueError:
        accepted = False
    assert bool(re.search(pattern, run_id)) is accepted


def test_a_changed_schema_does_not_change_the_next():
    first = input_schema()
    kept = copy.deepcopy(first)
    first["required"].append("draws")
    first["properties"]["point"]["enum"].append("other")
    first["properties"]["candidate"]["minimum"] = 0
    first["properties"]["draws"] = {"type": "integer"}
    first["additionalProperties"] = True
    second = input_schema()
    assert second == kept == SCHEMA
    assert second is not first
    counts = [
        second["properties"][name] for name in ("candidate", "attempt", "execution")
    ]
    assert len({id(count) for count in counts}) == 3


def test_a_registry_accepts_the_description_and_the_schema():
    registry = tools.Registry()
    registry.register(TOOL, stub, DESCRIPTION, input_schema())
    held = registry.definition(TOOL)
    assert (held.description, held.input_schema) == (DESCRIPTION, SCHEMA)
    assert registry.names() == (TOOL,)


def test_the_default_registry_holds_the_definition_of_the_tool():
    registry = tools.default_registry(lambda: None)
    assert registry.names() == (
        "blob.fetch",
        "blob.push",
        "case.write",
        "checks.read",
        "coder.run",
        TOOL,
        "hypotheses.read",
        "instance.read",
        "key.store",
        "round.end",
        "run.commit",
        "run.fresh",
        "spec.write",
        "state.read",
        "state.write",
        "timings.compare",
        "verdicts.write",
    )
    held = registry.definition(TOOL)
    assert (held.name, held.description, held.input_schema) == (
        TOOL,
        DESCRIPTION,
        SCHEMA,
    )


def test_the_description_tells_what_the_record_asks():
    assert type(DESCRIPTION) is str
    assert DESCRIPTION.strip()
    for member in check_identity.MEMBERS:
        assert member in DESCRIPTION
    for term in ("execution", "step_open", "fraction", "exponent"):
        assert term in DESCRIPTION


def test_input_schema_takes_no_argument():
    assert list(inspect.signature(input_schema).parameters) == []
    with pytest.raises(TypeError):
        input_schema(None)


def test_a_call_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert input_schema() == SCHEMA
    assert list(tmp_path.iterdir()) == []


def imports_by_function(node, owner=None, found=None):
    found = {} if found is None else found
    for child in ast.iter_child_nodes(node):
        assert not isinstance(child, ast.Import)
        if isinstance(child, ast.ImportFrom):
            assert child.module in ("hilclaw", "hilclaw.harness")
            found.setdefault(owner, set()).update(alias.name for alias in child.names)
        inner = child.name if isinstance(child, ast.FunctionDef) else owner
        imports_by_function(child, inner, found)
    return found


def test_the_module_imports_what_it_names_and_has_its_public_names_only():
    own = Path(check_definition.__file__)
    text = own.read_text(encoding="utf-8")
    assert imports_by_function(ast.parse(text)) == {
        None: {
            "backends",
            "check_identity",
            "gemm_contract",
            "keys",
            "mock_backend",
            "tools",
            "seed_source",
        },
        "default_table": {"mock_check"},
        "function": {"check_tool"},
    }
    public = {
        name
        for name, value in vars(check_definition).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    }
    assert public == {"DESCRIPTION", "default_table", "definition", "input_schema"}
    code = text.split('"""', 2)[2]
    for word in ("register(", "default_registry", "__main__", "environ", "getenv"):
        assert word not in code


# The default registry (ADR-0070); test values only.

RUN = "run-a"
ROUND = 3
SHAPE = {"m": 2, "k": 3, "n": 4}
DRAWS = 2
TOLERANCE = {"rtol": 0.25, "atol": 3.0}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": SHAPE,
    "dtype": "fp32",
    "layout": "row_major",
}
REQUEST = {
    "run_id": RUN,
    "round": ROUND,
    "candidate": 2,
    "attempt": 1,
    "execution": 1,
    "point": "sim",
}
PASSED = {
    "outcome": "pass",
    "shape": SHAPE,
    "draws": DRAWS,
    "tolerance": TOLERANCE,
    "counts": [{"failed": 0, "non_finite": 0}] * DRAWS,
}
STEP = {"step": "correctness_check_sim", "execution": 1}
NUMBERS = {"round": ROUND, "candidate": 2, "attempt": 1}


def profile(accelerator=mock_backend.NAME):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"cc": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }


def a_run(root, run_id=RUN, accelerator=mock_backend.NAME, op=OP):
    record = profile(accelerator)
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
        "op_signature": {"key": keys.op_signature_key(op).name, "record": op},
        "draws": DRAWS,
        "tolerance": TOLERANCE,
    }
    run = root / "runs" / run_id
    run.mkdir(parents=True)
    (run / "instance.json").write_text(json.dumps(document), encoding="utf-8")
    (run / "STATE.json").write_bytes(run_state.dump(ROUND, EMPTY))
    return root


def lines(root, run_id=RUN):
    found = events.read(root, run_id).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def no_log(root, run_id=RUN):
    return not (root / "runs" / run_id / "events.ndjson").exists()


class Recorder:
    def __init__(self, real):
        self.real, self.calls, self.answers = real, [], []

    def __call__(self, *args):
        self.calls.append(args)
        self.answers.append(self.real(*args))
        return self.answers[-1]


class CountingSource:
    def __init__(self, root=None):
        self.root, self.calls = root, 0

    def __call__(self):
        self.calls += 1
        return self.root


@pytest.fixture
def root(tmp_path):
    return a_run(tmp_path / "data")


@pytest.fixture
def parties(monkeypatch):
    """Record the source of seeds, the predicate and the default script the source binds."""
    recorded = {
        "seeds": Recorder(seed_source.system),
        "covers": Recorder(gemm_contract.covers),
        "script": Recorder(mock_check.default_script),
        "table": Recorder(check_definition.default_table),
    }
    monkeypatch.setattr(seed_source, "system", recorded["seeds"])
    monkeypatch.setattr(gemm_contract, "covers", recorded["covers"])
    monkeypatch.setattr(mock_check, "default_script", recorded["script"])
    monkeypatch.setattr(check_definition, "default_table", recorded["table"])
    return recorded


def counts(parties):
    return tuple(len(parties[name].calls) for name in ("seeds", "covers", "script"))


def refused(registry, request, kind):
    with pytest.raises(tools.ToolFailure) as caught:
        tools.call(registry, TOOL, request)
    assert caught.value.kind == kind
    return caught.value


def mcp_document(name, arguments):
    params = {"name": name, "arguments": arguments}
    document = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    return json.dumps(document).encode() + b"\n"


def test_default_table_holds_the_mock_offering_this_tool_alone():
    table = default_table()
    assert type(table) is BackendTable
    assert table.names() == (mock_backend.NAME,)
    assert callable(backends.select(table, profile(), TOOL))
    for tool in backends.HW_TOOLS:
        if tool != TOOL:
            with pytest.raises(tools.ToolFailure) as caught:
                backends.select(table, profile(), tool)
            assert caught.value.kind == tools.KIND_NOT_OFFERED
    for accelerator in ("cpu_standin", "acc_b"):
        with pytest.raises(tools.ToolFailure) as caught:
            backends.select(table, profile(accelerator), TOOL)
        assert caught.value.kind == tools.KIND_NO_BACKEND
    assert default_table() is not table


def test_default_table_operation_answers_with_the_default_script(parties):
    operation = backends.select(default_table(), profile(), TOOL)
    asked = CheckParameters(7, 1, 1, 1, 1)
    answer = operation(REQUEST, profile(), asked, Path("output"))
    assert parties["script"].calls == [
        (TOOL, REQUEST, profile(), asked, Path("output"))
    ]
    assert answer == parties["script"].answers[0]


def test_definition_is_the_tool_of_the_record(parties):
    source = CountingSource()
    held = definition(source)
    assert type(held) is tools.ToolDefinition
    assert (held.name, held.description, held.input_schema) == (
        TOOL,
        DESCRIPTION,
        SCHEMA,
    )
    assert callable(held.function)
    assert definition(source).input_schema is not held.input_schema
    assert (source.calls, *counts(parties)) == (0, 0, 0, 0)
    assert parties["table"].calls == []


@pytest.mark.parametrize("source", [None, "data", 3, {}, Path(".")])
def test_definition_refuses_a_source_that_is_not_callable(source):
    with pytest.raises(TypeError, match="callable"):
        definition(source)


def test_building_the_default_registry_calls_no_party(parties):
    source = CountingSource()
    registry = tools.default_registry(source)
    assert registry.names() == (
        "blob.fetch",
        "blob.push",
        "case.write",
        "checks.read",
        "coder.run",
        TOOL,
        "hypotheses.read",
        "instance.read",
        "key.store",
        "round.end",
        "run.commit",
        "run.fresh",
        "spec.write",
        "state.read",
        "state.write",
        "timings.compare",
        "verdicts.write",
    )
    assert (source.calls, *counts(parties)) == (0, 0, 0, 0)
    assert tools.default_registry(source).get(TOOL) is not registry.get(TOOL)
    assert parties["table"].calls == []


@pytest.mark.parametrize("source", [None, "data", 3])
def test_the_default_registry_refuses_a_source_that_is_not_callable(source, parties):
    with pytest.raises(TypeError, match="must be callable"):
        tools.default_registry(source)
    assert counts(parties) == (0, 0, 0)
    assert parties["table"].calls == []


def test_tools_list_of_the_mcp_front_holds_the_fixed_tool_set():
    data = (
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode() + b"\n"
    )
    stdout = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=tools.default_registry(lambda: None),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0
    listed = json.loads(stdout.getvalue())["result"]["tools"]
    assert [tool["name"] for tool in listed] == [
        "blob_fetch",
        "blob_push",
        "case_write",
        "checks_read",
        "coder_run",
        "correctness_check",
        "hypotheses_read",
        "instance_read",
        "key_store",
        "round_end",
        "run_commit",
        "run_fresh",
        "spec_write",
        "state_read",
        "state_write",
        "timings_compare",
        "verdicts_write",
    ]
    assert listed[5]["description"] == DESCRIPTION
    assert listed[5]["inputSchema"] == SCHEMA


def test_a_call_about_a_run_at_the_mock_passes(root, parties):
    registry = tools.default_registry(lambda: root)
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    assert lines(root) == [
        {"schema_version": 1, "kind": "step_started", **NUMBERS, "data": STEP},
        {
            "schema_version": 1,
            "kind": "step_ended",
            **NUMBERS,
            "data": {**STEP, "spend": {}, "result": PASSED},
        },
    ]
    assert counts(parties) == (1, 1, 1)
    ((_, _, _, parameters, _),) = parties["script"].calls
    assert parameters.seed == parties["seeds"].answers[0]


@pytest.mark.parametrize("accelerator", ["cpu_standin", "acc_b"])
def test_a_call_about_a_run_at_another_accelerator_is_no_backend(
    tmp_path, parties, accelerator
):
    root = a_run(tmp_path / "data", accelerator=accelerator)
    registry = tools.default_registry(lambda: root)
    refused(registry, REQUEST, tools.KIND_NO_BACKEND)
    refused(registry, REQUEST, tools.KIND_NO_BACKEND)
    assert no_log(root)
    assert counts(parties) == (0, 0, 0)


def test_the_same_request_again_returns_the_stored_result(root, parties):
    first = tools.call(tools.default_registry(lambda: root), TOOL, dict(REQUEST))
    again = tools.call(tools.default_registry(lambda: root), TOOL, dict(REQUEST))
    assert again == first == PASSED
    assert counts(parties) == (1, 1, 1)
    assert len(lines(root)) == 2


def test_an_op_signature_not_covered_is_answered_through_the_default_registry(
    tmp_path, parties
):
    root = a_run(tmp_path / "data", op={**OP, "dtype": "fp16"})
    registry = tools.default_registry(lambda: root)
    refused(registry, REQUEST, "op_signature_not_covered")
    assert no_log(root)
    assert counts(parties) == (0, 1, 0)


@pytest.mark.parametrize(
    "asked",
    [
        {**REQUEST, "draws": 3},
        {**REQUEST, "seed": 7},
        {**REQUEST, "point": "elsewhere"},
        {name: REQUEST[name] for name in REQUEST if name != "point"},
    ],
)
def test_a_request_the_record_refuses_is_invalid_request(root, parties, asked):
    refused(tools.default_registry(lambda: root), asked, tools.KIND_INVALID_REQUEST)
    assert no_log(root)
    assert counts(parties) == (0, 0, 0)


def test_no_environment_variable_chooses_the_table_or_the_seeds(
    tmp_path, parties, monkeypatch
):
    monkeypatch.setenv("HILCLAW_BACKEND", "cpu_standin")
    monkeypatch.setenv("HILCLAW_SEED", "7")
    monkeypatch.setenv("HILCLAW_SCRIPT", "fail")
    root = a_run(a_run(tmp_path / "data"), "run-b", accelerator="cpu_standin")
    registry = tools.default_registry(lambda: root)
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    refused(registry, {**REQUEST, "run_id": "run-b"}, tools.KIND_NO_BACKEND)
    assert counts(parties) == (1, 1, 1)
    assert parties["script"].calls[0][3].seed == parties["seeds"].answers[0]


def wrong_product(tool, asked, hw_profile, parameters, output_path):
    report = bytearray(
        mock_check.default_script(tool, asked, hw_profile, parameters, output_path)
    )
    (element,) = struct.unpack_from("=f", report, 4)
    struct.pack_into("=f", report, 4, element + 1000.0)
    return bytes(report)


def test_a_registry_of_the_test_answers_what_its_script_answers(root, parties):
    script = Recorder(wrong_product)
    operation = mock_check.operation(script)
    function = check_tool.tool_function(
        source=lambda: root,
        table=BackendTable([Backend(mock_backend.NAME, {TOOL: operation})]),
        seeds=lambda: 7,
        covers=gemm_contract.covers,
    )
    registry = tools.Registry()
    registry.register(TOOL, function, DESCRIPTION, input_schema())
    stdout = io.BytesIO()
    status = __main__.main(
        [TOOL],
        registry=registry,
        stdin=io.BytesIO(json.dumps(REQUEST).encode()),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == __main__.EXIT_RESULT
    result = json.loads(stdout.getvalue())
    assert result["outcome"] == "fail"
    assert result["counts"][0]["failed"] >= 1
    ((_, _, _, parameters, _),) = script.calls
    assert parameters.seed == 7
    stdout = io.BytesIO()
    data = io.BytesIO(mcp_document("correctness_check", REQUEST))
    assert mcp_front.main([], registry=registry, stdin=data, stdout=stdout) == 0
    answer = json.loads(stdout.getvalue())["result"]
    assert answer["isError"] is False
    assert json.loads(answer["content"][0]["text"]) == result
    assert len(script.calls) == 1
    assert counts(parties) == (0, 1, 1)


@pytest.fixture
def configured(tmp_path, monkeypatch):
    """A data root with a run at the mock and one at cpu_standin, as the fronts' source."""
    root = a_run(a_run(tmp_path / "data"), "run-b", accelerator="cpu_standin")
    monkeypatch.setattr(data_root_source, "configured", lambda: root)
    return root


def mcp_call(arguments):
    stdin = io.BytesIO(mcp_document("correctness_check", arguments))
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main([], stdin=stdin, stdout=stdout, stderr=stderr)
    assert (status, stderr.getvalue()) == (0, b"")
    answer = json.loads(stdout.getvalue())["result"]
    return answer["isError"], json.loads(answer["content"][0]["text"])


def command_call(arguments):
    stdout = io.BytesIO()
    status = __main__.main(
        [TOOL],
        stdin=io.BytesIO(json.dumps(arguments).encode()),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    return status, json.loads(stdout.getvalue())


def test_the_mcp_front_serves_the_tool_of_the_default_registry(configured, parties):
    assert mcp_call(REQUEST) == (False, PASSED)
    failed, answer = mcp_call({**REQUEST, "run_id": "run-b"})
    assert failed is True
    assert answer["error"]["kind"] == tools.KIND_NO_BACKEND
    assert no_log(configured, "run-b")
    assert counts(parties) == (1, 1, 1)


def test_the_command_line_front_serves_the_tool_of_the_default_registry(
    configured, parties
):
    assert command_call(REQUEST) == (__main__.EXIT_RESULT, PASSED)
    status, answer = command_call({**REQUEST, "run_id": "run-b"})
    assert status == __main__.EXIT_TOOL_FAILURE
    assert answer["error"]["kind"] == tools.KIND_NO_BACKEND
    assert no_log(configured, "run-b")
    assert counts(parties) == (1, 1, 1)


# When the modules of the operation are imported

HEAVY = (
    "numpy",
    "hilclaw.check_tool",
    "hilclaw.mock_check",
    "hilclaw.harness.verification",
)
CHILD_END = """
import sys
print(",".join(name for name in {heavy!r} if name in sys.modules))
"""
LIST_CHILD = """
import io, json
from hilclaw import mcp_front
line = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\\n"
out = io.BytesIO()
status = mcp_front.main([], stdin=io.BytesIO(line.encode()), stdout=out, stderr=io.BytesIO())
print(status, *(tool["name"] for tool in json.loads(out.getvalue())["result"]["tools"]))
"""
CALL_CHILD = """
import io, sys
from hilclaw import __main__, data_root_source
data_root_source.configured = lambda: sys.argv[1]
out = io.BytesIO()
request = io.BytesIO(b'{{"sha256": "{hash}"}}')
status = __main__.main([{name!r}], stdin=request, stdout=out, stderr=io.BytesIO())
print(status, out.getvalue().decode().strip())
"""
ABSENT = "0" * 64


def heavy_modules_after(code, tmp_path):
    done = subprocess.run(
        [sys.executable, "-c", code + CHILD_END.format(heavy=HEAVY), str(tmp_path)],
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=60,
        check=False,
    )
    assert (done.returncode, done.stderr) == (0, b"")
    *answers, loaded = done.stdout.decode().splitlines()
    return answers, loaded


def test_building_the_default_registry_imports_no_numpy(tmp_path):
    code = "from hilclaw import tools\ntools.default_registry(lambda: None)\n"
    assert heavy_modules_after(code, tmp_path) == ([], "")


def test_listing_the_tools_through_the_mcp_front_imports_no_numpy(tmp_path):
    answers, loaded = heavy_modules_after(LIST_CHILD, tmp_path)
    assert answers == [
        "0 blob_fetch blob_push case_write checks_read coder_run correctness_check"
        + " hypotheses_read instance_read key_store round_end run_commit run_fresh spec_write state_read"
        + " state_write timings_compare verdicts_write"
    ]
    assert loaded == ""


@pytest.mark.parametrize(
    ("name", "answer"),
    [
        ("blob.push", '0 {"sha256":"' + ABSENT + '","present":false}'),
        ("blob.fetch", '0 {"sha256":"' + ABSENT + '","present":false}'),
        (
            "sim.run",
            '4 {"error":{"kind":"unknown_tool","message":"unknown tool \'sim.run\'"}}',
        ),
    ],
)
def test_a_call_of_another_tool_through_the_command_line_imports_no_numpy(
    tmp_path, name, answer
):
    code = CALL_CHILD.format(hash=ABSENT, name=name)
    assert heavy_modules_after(code, tmp_path) == ([answer], "")


def test_the_first_call_binds_the_tool_function_of_the_record(
    root, parties, monkeypatch
):
    bound = []
    real = check_tool.tool_function

    def binding(**parts):
        bound.append(parts)
        return real(**parts)

    monkeypatch.setattr(check_tool, "tool_function", binding)
    source = CountingSource(root)
    registry = tools.default_registry(source)
    assert bound == []
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    assert bound == [
        {
            "source": source,
            "table": parties["table"].answers[0],
            "seeds": parties["seeds"],
            "covers": parties["covers"],
        }
    ]


def test_the_table_is_built_once_per_registry(tmp_path, parties):
    root = a_run(a_run(tmp_path / "data"), "run-b", accelerator="cpu_standin")
    registry = tools.default_registry(lambda: root)
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    refused(registry, {**REQUEST, "run_id": "run-b"}, tools.KIND_NO_BACKEND)
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    assert len(parties["table"].calls) == 1
    other = tools.default_registry(lambda: root)
    assert tools.call(other, TOOL, dict(REQUEST)) == PASSED
    assert len(parties["table"].calls) == 2
    assert parties["table"].answers[0] is not parties["table"].answers[1]


def test_a_first_call_whose_binding_fails_keeps_nothing(root, parties, monkeypatch):
    broken = RuntimeError("no table")
    failures = [broken]

    def fails_once():
        if failures:
            raise failures.pop()
        return parties["table"]()

    monkeypatch.setattr(check_definition, "default_table", fails_once)
    registry = tools.default_registry(lambda: root)
    failure = refused(registry, REQUEST, tools.KIND_TOOL_CRASHED)
    assert failure.__cause__ is broken
    assert no_log(root)
    assert counts(parties) == (0, 0, 0)
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    assert tools.call(registry, TOOL, dict(REQUEST)) == PASSED
    assert len(parties["table"].calls) == 1
    assert counts(parties) == (1, 1, 1)
