import io
import json
import os
import posixpath
import tempfile

import pytest

from hilclaw import (
    backends,
    check_definition,
    data_root_source,
    events,
    keys,
    layout,
    local_run,
    mcp_front,
    mock_backend,
    mock_check,
    mock_run,
    run_state,
    standin_check,
    standin_image,
    standin_profile,
    standin_waiter_line,
    tools,
)
from hilclaw.check_parameters import Bf16CheckParameters, CheckParameters
from hilclaw.harness import bf16_verification_build
from hilclaw.harness.measurement import N_MIN
from hilclaw.journal import EMPTY

MOCK = mock_backend.NAME
STANDIN = standin_profile.ACCELERATOR
ENTRIES = (MOCK, STANDIN)
IMAGE = "registry.example/hilclaw-clang:1"
ROUND = 3
SHAPE = {"m": 2, "k": 3, "n": 4}
N_MAX = 40
DRAWS = 2
TOLERANCE = {"rtol": 0.25, "atol": 3.0}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": SHAPE,
    "dtype": "fp32",
    "layout": "row_major",
}
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
NUMBERS = {"round": ROUND, "candidate": 2, "attempt": 1}
CALL = {"round": ROUND, "candidate": 2, "attempt": 1, "execution": 1}
TOOLS = {
    "correctness.check": ("correctness_check", {"point": "sim"}),
    "sim.run": ("sim_run", {}),
    "board.run": ("board_run", {}),
}
STEPS = {
    "correctness.check": "correctness_check_sim_v2",
    "sim.run": "sim_run_timing_v2",
    "board.run": "board_run_timing_v2",
}
PASSED = {
    "outcome": "pass",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": SHAPE,
    "draws": DRAWS,
    "tolerance": TOLERANCE,
    "counts": {"c": [{"failed": 0, "non_finite": 0}] * DRAWS},
}
CONVERGED = {
    "outcome": "converged",
    "contract_key": {"kind": "gemm", "dtype": "fp32", "layout": "row_major"},
    "shape": SHAPE,
    "n_max": N_MAX,
    "sample_form": "interval",
    "unit": "ns",
    "resolution": 1,
    "intervals": [1000000] * N_MIN,
    "ceiling": "not_stated",
}
CONTAINERS = {"correctness.check": 2, "sim.run": 3, "board.run": 3}
EXPECTED = {
    "correctness.check": PASSED,
    "sim.run": CONVERGED,
    "board.run": CONVERGED,
}
each_entry = pytest.mark.parametrize("entry", ENTRIES)
each_tool = pytest.mark.parametrize("tool", list(TOOLS))


def run_id(entry):
    return f"run-{entry.replace('_', '-')}"


def request(tool, entry, execution=1):
    return {"run_id": run_id(entry), **CALL, "execution": execution, **TOOLS[tool][1]}


def hw_profile(accelerator):
    return {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"cc": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }


def a_run(root, accelerator):
    record = hw_profile(accelerator)
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
        "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
        "n_max": N_MAX,
        "objective": OBJECTIVE,
        "draws": DRAWS,
        "tolerance": TOLERANCE,
    }
    run = root / "runs" / run_id(accelerator)
    run.mkdir(parents=True)
    (run / "instance.json").write_text(json.dumps(document), encoding="utf-8")
    (run / "STATE.json").write_bytes(run_state.dump(ROUND, EMPTY))
    output = layout.attempt_artefact(root, run_id(accelerator), ROUND, 2, 1, "output")
    output.mkdir(parents=True)
    (output / "gemm.c").write_bytes(b"void gemm(void) {}\n")
    (output / "gemm.h").write_bytes(b"void gemm(void);\n")


def step_lines(root, entry):
    found = events.read(root, run_id(entry)).events
    return [{name: line[name] for name in line if name != "time"} for line in found]


def ended(tool, **outcome):
    step = {"step": STEPS[tool], "execution": 1}
    return [
        {"schema_version": 1, "kind": "step_started", **NUMBERS, "data": step},
        {
            "schema_version": 1,
            "kind": "step_ended",
            **NUMBERS,
            "data": {**step, "spend": {}, **outcome},
        },
    ]


class Client:
    """The container client: it builds, runs and reports as a passing kernel would."""

    def __init__(self):
        self.runs = []
        self.build_status = 0
        self.missing = False
        self.kind = None

    def __call__(self, command, **options):
        command = list(command)
        if command[1] == "rm":
            return self.result(command, 0)
        if self.missing:
            raise local_run.ProgramNotFoundError(command[0])
        self.runs.append(command)
        program, *arguments = command[command.index(IMAGE) + 1 :]
        if program == standin_check.COMPILER:
            return self.build(command, arguments)
        if posixpath.basename(program) == standin_check.EXECUTABLE_NAME:
            *dims, draws, seed = (int(value) for value in arguments)
            if self.kind is None:
                parameters = CheckParameters(seed, draws, *dims)
            else:
                parameters = Bf16CheckParameters(
                    seed, draws, self.kind, "bf16", tuple(dims)
                )
            report = mock_check.default_script(None, None, None, parameters, None, None)
            return self.result(command, 0, report)
        report, _ = mock_run.default_script(None, None, None, None, None, None)
        line = standin_waiter_line.NONE_LINE
        return self.result(command, 0, report + b"\n" + line + b"\n")

    def build(self, command, arguments):
        names = {posixpath.basename(argument) for argument in arguments}
        self.kind = next(
            (
                kind
                for kind, source in bf16_verification_build.PROGRAM_SOURCES.items()
                if source.name in names
            ),
            None,
        )
        if self.build_status == 0:
            option = command[command.index("--mount") + 1]
            fields = dict(field.split("=", 1) for field in option.split(","))
            name = posixpath.basename(arguments[arguments.index("-o") + 1])
            with open(os.path.join(fields["source"], name), "wb") as file:
                file.write(b"\x7fELF")
        return self.result(command, self.build_status, b"", b"gemm.c: compiled\n")

    @staticmethod
    def result(command, returncode, stdout=b"", stderr=b""):
        return local_run.RunResult(
            returncode=returncode,
            timed_out=False,
            stdout=stdout,
            stderr=stderr,
            command=tuple(command),
            duration_s=0.5,
            max_rss=None,
        )


@pytest.fixture(autouse=True)
def client(monkeypatch, tmp_path):
    stub = Client()
    monkeypatch.setattr(local_run, "run", stub)
    monkeypatch.setattr(os, "getuid", lambda: 1234, raising=False)
    monkeypatch.setattr(os, "getgid", lambda: 567, raising=False)
    monkeypatch.setenv(standin_image.ENV_IMAGE, IMAGE)
    directory = tmp_path / "tmp"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    monkeypatch.setattr(standin_check, "REMOVE_PAUSES_S", (0.0, 0.0))
    return stub


@pytest.fixture
def root(tmp_path, monkeypatch):
    data = tmp_path / "data"
    for entry in ENTRIES:
        a_run(data, entry)
    monkeypatch.setattr(data_root_source, "configured", lambda: data)
    return data


def via_registry(root, tool, asked):
    registry = tools.default_registry(lambda: root)
    try:
        return False, tools.call(registry, tool, asked)
    except tools.ToolFailure as failure:
        return True, {"error": {"kind": failure.kind, "message": failure.message}}


def via_mcp(root, tool, asked):
    params = {"name": TOOLS[tool][0], "arguments": asked}
    document = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    stdin = io.BytesIO(json.dumps(document).encode() + b"\n")
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main([], stdin=stdin, stdout=stdout, stderr=stderr)
    assert (status, stderr.getvalue()) == (0, b"")
    answer = json.loads(stdout.getvalue())["result"]
    return answer["isError"], json.loads(answer["content"][0]["text"])


each_front = pytest.mark.parametrize("call", [via_registry, via_mcp])


class Script:
    def __init__(self, answer=None):
        self.answer, self.calls = answer, 0

    def __call__(self, *_):
        self.calls += 1
        if self.answer is None:
            raise tools.ToolFailure("compiler_unavailable", "the script fails")
        return self.answer


def mock_answers(monkeypatch, check, run):
    monkeypatch.setattr(mock_check, "default_script", check)
    monkeypatch.setattr(mock_run, "default_script", run)


@each_front
@each_tool
@each_entry
def test_a_passing_kernel_is_answered_alike_by_both_entries(
    root, client, entry, tool, call
):
    assert call(root, tool, request(tool, entry)) == (False, EXPECTED[tool])
    assert step_lines(root, entry) == ended(tool, result=EXPECTED[tool])
    built = len(client.runs)
    assert call(root, tool, request(tool, entry)) == (False, EXPECTED[tool])
    assert len(step_lines(root, entry)) == 2
    assert len(client.runs) == built
    assert built == (CONTAINERS[tool] if entry == STANDIN else 0)


@each_front
@each_tool
@each_entry
def test_a_tool_failure_is_answered_alike_and_again_from_the_log(
    root, client, monkeypatch, entry, tool, call
):
    script = Script()
    if entry == MOCK:
        mock_answers(monkeypatch, script, script)
    else:
        monkeypatch.delenv(standin_image.ENV_IMAGE)
    failed, answer = call(root, tool, request(tool, entry))
    assert failed is True
    assert answer["error"]["kind"] == "compiler_unavailable"
    assert step_lines(root, entry) == ended(tool, failure=answer["error"])
    monkeypatch.setenv(standin_image.ENV_IMAGE, IMAGE)
    assert call(root, tool, request(tool, entry)) == (True, answer)
    assert len(step_lines(root, entry)) == 2
    assert (script.calls, client.runs) == ((1 if entry == MOCK else 0), [])


def build_fails(entry, monkeypatch, client):
    script = Script("build_exit_status")
    if entry == MOCK:
        mock_answers(monkeypatch, script, script)
    else:
        client.build_status = 1
    return script


@each_front
@each_tool
@each_entry
def test_a_failed_build_is_answered_alike_as_a_broken_result(
    root, client, monkeypatch, entry, tool, call
):
    script = build_fails(entry, monkeypatch, client)
    failed, result = call(root, tool, request(tool, entry))
    assert failed is False
    assert result["outcome"] == "broken"
    assert result["condition"] == "build_exit_status"
    assert step_lines(root, entry) == ended(tool, result=result)
    assert call(root, tool, request(tool, entry)) == (False, result)
    assert (script.calls, len(client.runs)) == ((1, 0) if entry == MOCK else (0, 1))


@each_tool
def test_the_results_of_both_entries_have_one_form(root, tool):
    answers = [via_registry(root, tool, request(tool, entry)) for entry in ENTRIES]
    assert answers[0] == answers[1] == (False, EXPECTED[tool])
    for _, result in answers:
        tools.check_json_object(result)
        assert list(result) == list(EXPECTED[tool])


@each_front
@each_tool
def test_no_image_named_is_compiler_unavailable_with_no_container(
    root, client, monkeypatch, tool, call
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    failed, answer = call(root, tool, request(tool, STANDIN))
    assert (failed, answer["error"]["kind"]) == (True, "compiler_unavailable")
    assert client.runs == []


@each_front
@each_tool
def test_a_client_not_found_is_compiler_unavailable_at_the_build(
    root, client, tool, call
):
    client.missing = True
    failed, answer = call(root, tool, request(tool, STANDIN))
    assert (failed, answer["error"]["kind"]) == (True, "compiler_unavailable")
    assert client.runs == []
    assert step_lines(root, STANDIN) == ended(tool, failure=answer["error"])


@each_tool
def test_the_image_is_read_at_the_call_and_not_when_the_table_is_built(
    root, client, monkeypatch, tool
):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    registry = tools.default_registry(lambda: root)
    with pytest.raises(tools.ToolFailure) as caught:
        tools.call(registry, tool, request(tool, STANDIN))
    assert caught.value.kind == "compiler_unavailable"
    monkeypatch.setenv(standin_image.ENV_IMAGE, IMAGE)
    again = tools.call(registry, tool, request(tool, STANDIN, execution=2))
    assert again == EXPECTED[tool]
    assert client.runs


@each_entry
def test_profiler_collect_is_refused_by_the_registry_at_both_entries(root, entry):
    asked = {"run_id": run_id(entry), **CALL}
    registry = tools.default_registry(lambda: root)
    assert "profiler.collect" not in registry.names()
    with pytest.raises(tools.UnknownToolError, match="'profiler.collect'"):
        tools.call(registry, "profiler.collect", asked)
    params = {"name": "profiler_collect", "arguments": asked}
    document = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    stdin = io.BytesIO(json.dumps(document).encode() + b"\n")
    stdout = io.BytesIO()
    assert mcp_front.main([], stdin=stdin, stdout=stdout) == 0
    error = json.loads(stdout.getvalue())["error"]
    assert error == {
        "code": mcp_front.INVALID_PARAMS,
        "message": "unknown tool 'profiler_collect'",
    }
    assert not (root / "runs" / run_id(entry) / "events.ndjson").exists()


def test_the_default_table_offers_the_three_tools_and_no_profiler_at_both_entries():
    table = check_definition.default_table()
    assert table.names() == tuple(sorted(ENTRIES))
    for entry in ENTRIES:
        for tool in TOOLS:
            assert callable(backends.select(table, hw_profile(entry), tool))
        with pytest.raises(tools.ToolFailure) as caught:
            backends.select(table, hw_profile(entry), "profiler.collect")
        assert caught.value.kind == tools.KIND_NOT_OFFERED


# A check of a bf16 kind at both entries (ADR-0177 decisions 2 and 3; ADR-0179)

BF16_SHAPES = {
    "gemm": {"m": 2, "k": 3, "n": 4},
    "rmsnorm": {"m": 2, "n": 8},
    "elementwise_add": {"m": 3, "n": 5},
    "swiglu": {"m": 2, "n": 6},
    "sdpa_kv_cache": {"m": 2, "l": 3, "h": 4, "h_kv": 2, "d": 4},
}


def a_bf16_run(root, accelerator, kind):
    record = hw_profile(accelerator)
    op = {**OP, "kind": kind, "shape": BF16_SHAPES[kind], "dtype": "bf16"}
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(record).name, "record": record},
        "op_signature": {"key": keys.op_signature_key(op).name, "record": op},
        "draws": DRAWS,
        "tolerance": TOLERANCE,
    }
    run_id = f"bf16-{kind.replace('_', '-')}-{accelerator.replace('_', '-')}"
    run = root / "runs" / run_id
    run.mkdir(parents=True)
    (run / "instance.json").write_text(json.dumps(document), encoding="utf-8")
    (run / "STATE.json").write_bytes(run_state.dump(ROUND, EMPTY))
    output = layout.attempt_artefact(root, run_id, ROUND, 2, 1, "output")
    output.mkdir(parents=True)
    (output / f"{kind}.c").write_bytes(b"void kernel(void) {}\n")
    return run_id


@each_front
@pytest.mark.parametrize("kind", list(BF16_SHAPES))
def test_a_passing_bf16_kernel_is_answered_alike_by_both_entries(
    root, client, kind, call
):
    answers = []
    for entry in ENTRIES:
        run_id = a_bf16_run(root, entry, kind)
        asked = {"run_id": run_id, **CALL, "point": "board"}
        answers.append(call(root, "correctness.check", asked))
        found = events.read(root, run_id).events
        assert [line["data"]["step"] for line in found] == [
            "correctness_check_board_v2"
        ] * 2
    assert answers[0] == answers[1]
    failed, result = answers[0]
    assert failed is False
    assert (result["outcome"], result["shape"]) == ("pass", BF16_SHAPES[kind])
    assert result["contract_key"] == {
        "kind": kind,
        "dtype": "bf16",
        "layout": "row_major",
    }
    assert len(client.runs) == 2
    build, process = client.runs
    program = bf16_verification_build.PROGRAM_SOURCES[kind].name
    assert any(argument.endswith(f"/{program}") for argument in build)
    dims = [str(value) for value in BF16_SHAPES[kind].values()]
    assert process[process.index(IMAGE) + 2 :][: len(dims)] == dims
