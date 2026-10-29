import errno
import io
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    catalog,
    coder_call,
    elementwise_add_bf16_contract,
    events,
    gemm_bf16_contract,
    gemm_contract,
    journal,
    keys,
    layout,
    mcp_front,
    once_write,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    run_admission,
    run_file_tools,
    run_objective,
    sdpa_kv_cache_bf16_contract,
    spec,
    spec_feedback,
    spec_file,
    spec_tool,
    swiglu_bf16_contract,
    tools,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
INSTANCE_PATH = f"runs/{RUN}/instance.json"
SPEC_PATH = f"runs/{RUN}/rounds/0000/coder/candidates/01/attempts/01/spec.json"
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}


def hw(**changes):
    record = {
        "schema_version": 1,
        "accelerator": "synthetic_hw",
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }
    return record | changes


def op(**changes):
    record = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "fp32",
        "layout": "row_major",
    }
    return record | changes


def instance_document(op_record=None, **changes):
    record = op() if op_record is None else op_record
    document = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(hw()).name, "record": hw()},
        "op_signature": {"key": keys.op_signature_key(record).name, "record": record},
        "candidates_per_round": 1,
        "objective": OBJECTIVE,
    }
    for name, value in changes.items():
        if value is None:
            del document[name]
        else:
            document[name] = value
    return document


def encoded(document):
    return (json.dumps(document, indent=2) + "\n").encode()


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


class Source:
    def __init__(self, root):
        self.root = root
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self.root


class FailingSource:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise RuntimeError("no data root in this test")


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    yield directory
    assert not list(tmp_path.rglob("events.ndjson"))


def instance_path(root):
    return layout.run_file(root, RUN, "instance.json")


def spec_path(root):
    return layout.attempt_artefact(root, RUN, 0, 1, 1, "spec.json")


def run(root, document=None):
    place(instance_path(root), encoded(document or instance_document()))


def request(**changes):
    body = {"run_id": RUN, "round": 0, "candidate": 1, "attempt": 1} | changes
    return {name: value for name, value in body.items() if value is not None}


def write(source, body=None):
    return spec_tool.definition(source).function(request() if body is None else body)


def tree(root):
    found = {}
    for directory, _, files in os.walk(root):
        here = Path(directory)
        found[here.relative_to(root).as_posix()] = None
        for name in files:
            path = here / name
            with open(path, "rb") as file:
                found[path.relative_to(root).as_posix()] = file.read()
    return found


def refused(root, body=None, source=None):
    before = tree(root)
    with pytest.raises(ToolFailure) as failure:
        write(source or Source(root), body)
    assert tree(root) == before
    assert not (root / "runs" / RUN / "rounds").exists()
    return failure.value


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = spec_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == spec_tool.NAME == "spec.write"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 0, "maximum": keys.MAX_INTEGER},
            "candidate": {"type": "integer", "minimum": 1, "maximum": 1},
            "attempt": {"type": "integer", "minimum": 1, "maximum": 1},
            "techniques": {"type": "array"},
        },
        "required": ["run_id", "round", "candidate", "attempt"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert spec_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="callable"):
        spec_tool.definition(source)


KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_invalid",
    "run_file_unsupported",
    "run_file_unreadable",
    "candidates_per_round_not_stated",
    "candidates_per_round_not_covered",
    "op_signature_not_stated",
    "op_signature_not_covered",
    "objective_not_stated",
    "catalog_unusable",
    "technique_unknown",
    "technique_not_applicable",
    "feedback_unreadable",
    "check_result_invalid",
    "spec_invalid",
    "spec_exists",
    "spec_not_written",
)


def test_the_description_names_every_kind_in_order():
    description = spec_tool.definition(lambda: None).description
    start = description.index("checked in this order")
    places = [description.index(kind, start) for kind in KINDS]
    assert places == sorted(places)
    assert "The result is {}." in description
    assert "never part of the request" in description
    assert SPEC_PATH.replace(RUN, "<run_id>").replace("0000", "<RRRR>") in description
    assert "exactly when round is 1 or more, techniques" in description


def test_the_kinds_are_those_of_the_record():
    assert spec_tool.KIND_CANDIDATES_PER_ROUND_NOT_STATED == (
        "candidates_per_round_not_stated"
    )
    assert spec_tool.KIND_CANDIDATES_PER_ROUND_NOT_COVERED == (
        "candidates_per_round_not_covered"
    )
    assert spec_tool.KIND_SPEC_EXISTS == "spec_exists"
    assert spec_tool.KIND_SPEC_NOT_WRITTEN == "spec_not_written"
    assert (
        spec_tool.KIND_OP_SIGNATURE_NOT_STATED
        is run_admission.KIND_OP_SIGNATURE_NOT_STATED
    )
    assert (
        spec_tool.KIND_OP_SIGNATURE_NOT_COVERED
        is run_admission.KIND_OP_SIGNATURE_NOT_COVERED
    )
    assert (
        spec_tool.KIND_OBJECTIVE_NOT_STATED is run_objective.KIND_OBJECTIVE_NOT_STATED
    )
    assert spec_tool.KIND_SPEC_INVALID is coder_call.KIND_SPEC_INVALID
    assert spec_tool.KIND_CATALOG_UNUSABLE == "catalog_unusable"
    assert spec_tool.KIND_TECHNIQUE_UNKNOWN == "technique_unknown"
    assert spec_tool.KIND_TECHNIQUE_NOT_APPLICABLE == "technique_not_applicable"
    assert spec_tool.KIND_FEEDBACK_UNREADABLE is spec_feedback.KIND_FEEDBACK_UNREADABLE
    new = (
        spec_tool.KIND_CANDIDATES_PER_ROUND_NOT_STATED,
        spec_tool.KIND_CANDIDATES_PER_ROUND_NOT_COVERED,
        spec_tool.KIND_CATALOG_UNUSABLE,
        spec_tool.KIND_TECHNIQUE_UNKNOWN,
        spec_tool.KIND_TECHNIQUE_NOT_APPLICABLE,
        spec_tool.KIND_FEEDBACK_UNREADABLE,
        spec_tool.KIND_SPEC_EXISTS,
        spec_tool.KIND_SPEC_NOT_WRITTEN,
    )
    for kind in new:
        assert re.fullmatch(r"[a-z][a-z0-9_]{0,31}", kind)
        assert kind not in tools.RESERVED_KINDS


# Happy paths (ADR-0138 Walk-through)


def expected_spec(document):
    record = document["op_signature"]["record"]
    shape = record["shape"]
    return {
        "schema_version": 2,
        "id": {
            "run_id": RUN,
            "round": 0,
            "candidate": 1,
            "attempt": 1,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": document["hw_profile"],
        "task": {
            "op_signature": document["op_signature"],
            "contract": gemm_contract.task_contract(shape["m"], shape["k"], shape["n"]),
            "objective": document["objective"],
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }


def test_the_bring_up_spec_is_composed_and_written(root):
    document = instance_document()
    run(root, document)
    source = Source(root)
    instance = instance_path(root).read_bytes()
    assert spec_tool.definition(source).function(request()) == {}
    assert source.calls == 1
    path = spec_path(root)
    assert path.relative_to(root).as_posix() == SPEC_PATH
    content = path.read_bytes()
    assert content.endswith(b"\n")
    assert b"\r" not in content
    written = spec_file.parse(content)
    assert spec_file.final_name(root, written) == path
    assert written["schema_version"] == 2
    assert written["id"] == {
        "run_id": RUN,
        "round": 0,
        "candidate": 1,
        "attempt": 1,
        "candidates": 1,
        "relation": "single",
    }
    assert written["hw_profile"] == {
        "key": document["hw_profile"]["key"],
        "record": document["hw_profile"]["record"],
    }
    assert written["task"]["op_signature"] == document["op_signature"]
    assert written["task"]["contract"] == gemm_contract.task_contract(2, 3, 5)
    assert written["task"]["objective"] == OBJECTIVE
    assert written["guidance"] == {"techniques": []}
    assert written["feedback"] == {"attempts": []}
    assert set(written) == {
        "schema_version",
        "id",
        "hw_profile",
        "task",
        "guidance",
        "feedback",
    }
    assert set(written["task"]) == {"op_signature", "contract", "objective"}
    assert written == expected_spec(document)
    expected = json.dumps(written, ensure_ascii=False, indent=2) + "\n"
    assert content == expected.encode("utf-8")
    assert instance_path(root).read_bytes() == instance
    assert sorted(p.name for p in path.parent.iterdir()) == ["spec.json"]


def test_a_record_with_label_and_ext_is_carried_whole(root):
    record = op(label="the first gemm", ext={"synthetic_tile": 4, "note": "x"})
    document = instance_document(record)
    run(root, document)
    assert write(Source(root)) == {}
    written = json.loads(spec_path(root).read_bytes())
    assert written["task"]["op_signature"] == {
        "key": keys.op_signature_key(record).name,
        "record": record,
    }
    assert written == expected_spec(document)


def test_the_hw_profile_of_the_run_is_carried_not_a_stored_one(root):
    document = instance_document()
    document["hw_profile"]["record"]["label"] = "the run's label"
    run(root, document)
    stored = layout.hw_profile_record(root, document["hw_profile"]["key"])
    place(stored, b"not json")
    place(layout.run_file(root, RUN, "STATE.json"), b"not json")
    assert write(Source(root)) == {}
    written = json.loads(spec_path(root).read_bytes())
    assert written["hw_profile"]["record"]["label"] == "the run's label"


def test_the_tool_answers_through_the_registry(root):
    run(root)
    registry = default_registry(Source(root))
    assert tools.call(registry, "spec.write", request()) == {}
    assert mcp_front.mcp_names(registry)["spec_write"] == "spec.write"
    assert spec_path(root).is_file()


def test_the_tool_answers_by_its_mcp_name(root):
    run(root)
    params = {"name": "spec_write", "arguments": request()}
    data = (
        json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
        )
        + "\n"
    ).encode()
    stdout = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(Source(root)),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0
    result = json.loads(stdout.getvalue())["result"]
    assert result["isError"] is False
    assert json.loads(result["content"][0]["text"]) == {}
    assert spec_path(root).is_file()


def test_a_refusal_reaches_the_mcp_front_as_an_error(root):
    run(root, instance_document(objective=None))
    registry = default_registry(Source(root))
    with pytest.raises(ToolFailure) as failure:
        tools.call(registry, "spec.write", request())
    assert failure.value.kind == "objective_not_stated"


# Negative requests


@pytest.mark.parametrize(
    "body",
    [
        request(round=1),
        request(round=7),
        request(round=0, techniques=[]),
        request(candidate=2),
        request(attempt=2),
        request(round=-1),
        request(candidate=0),
        request(round=True),
        request(candidate=True),
        request(attempt=1.0),
        request(round="0"),
        request(round=None),
        request(candidate=None),
        request(attempt=None),
        request(run_id=None),
        request(extra=1),
        request(execution=1),
        {},
        request(run_id="Bad Run"),
        request(run_id=""),
        request(run_id="../x"),
        request(run_id=3),
    ],
)
def test_a_request_that_is_not_the_bring_up_tuple_is_invalid(root, body):
    run(root)
    source = Source(root)
    failure = refused(root, body, source)
    assert failure.kind == "invalid_request"
    assert source.calls == 0


def test_an_extra_member_is_named(root):
    failure = refused(root, request(zeta=1, alpha=2))
    assert "not 'alpha', 'zeta'" in failure.message


@pytest.mark.parametrize("name", ["run_id", "round", "candidate", "attempt"])
def test_a_missing_member_is_named(root, name):
    failure = refused(root, request(**{name: None}))
    assert f"lacks the member {name}" in failure.message


def test_a_wrong_number_is_named(root):
    failure = refused(root, request(attempt=2))
    assert failure.message.startswith("attempt: must be 1")
    failure = refused(root, request(round=False))
    assert failure.message == "round: must be an int, got bool"


# Every kind, in order


def test_no_data_root(root):
    run(root)
    source = FailingSource()
    failure = refused(root, source=source)
    assert failure.kind == "no_data_root"
    assert source.calls == 1


def test_a_missing_instance_is_run_file_missing(root):
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(INSTANCE_PATH)


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{", "run_file_invalid"),
        (encoded({"schema_version": 1}), "run_file_invalid"),
        (encoded(instance_document(schema_version=2)), "run_file_unsupported"),
    ],
)
def test_an_instance_that_cannot_be_used_is_its_kind(root, content, kind):
    place(instance_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(INSTANCE_PATH)


def test_a_directory_in_the_place_of_the_instance_is_run_file_invalid(root):
    instance_path(root).mkdir(parents=True)
    assert refused(root).kind == "run_file_invalid"


def test_an_unreadable_instance_is_run_file_unreadable(root, monkeypatch):
    run(root)
    original = Path.read_bytes

    def read_bytes(path):
        if path.name == "instance.json":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original(path)

    before = tree(root)
    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root))
    monkeypatch.undo()
    assert failure.value.kind == "run_file_unreadable"
    assert failure.value.message.startswith(INSTANCE_PATH)
    assert tree(root) == before


def test_no_candidates_per_round_is_not_stated(root):
    run(root, instance_document(candidates_per_round=None))
    failure = refused(root)
    assert failure.kind == "candidates_per_round_not_stated"
    assert failure.message.startswith(INSTANCE_PATH)


@pytest.mark.parametrize("count", [2, 7])
def test_more_than_one_candidate_is_not_covered(root, count):
    run(root, instance_document(candidates_per_round=count))
    failure = refused(root)
    assert failure.kind == "candidates_per_round_not_covered"
    assert failure.message.startswith(
        f"{INSTANCE_PATH}: states candidates_per_round {count}"
    )


def test_no_op_signature_is_not_stated(root):
    run(root, instance_document(op_signature=None))
    failure = refused(root)
    assert failure.kind == "op_signature_not_stated"
    assert failure.message.startswith(INSTANCE_PATH)


@pytest.mark.parametrize(
    "record",
    [
        op(dtype="fp16"),
        op(layout="col_major"),
        op(shape={"m": 0, "k": 3, "n": 5}),
    ],
)
def test_an_op_signature_outside_the_contract_is_not_covered(root, record):
    run(root, instance_document(record))
    failure = refused(root)
    assert failure.kind == "op_signature_not_covered"
    assert failure.message.startswith(INSTANCE_PATH)


def test_no_objective_is_not_stated(root):
    run(root, instance_document(objective=None))
    failure = refused(root)
    assert failure.kind == "objective_not_stated"
    assert failure.message.startswith(INSTANCE_PATH)


def test_a_refused_composition_is_spec_invalid(root, monkeypatch):
    run(root)

    def parse(content):
        raise spec_file.InvalidSpecFileError("synthetic refusal")

    monkeypatch.setattr(spec_file, "parse", parse)
    failure = refused(root)
    assert failure.kind == "spec_invalid"
    assert failure.message.startswith(SPEC_PATH)
    assert "synthetic refusal" in failure.message


def test_another_version_of_the_composition_is_spec_invalid(root, monkeypatch):
    run(root)
    original = spec_tool._compose

    def compose(run_id, stated):
        return original(run_id, stated) | {"schema_version": 3}

    monkeypatch.setattr(spec_tool, "_compose", compose)
    failure = refused(root)
    assert failure.kind == "spec_invalid"
    assert "schema_version: is 3, not 2" in failure.message


def test_a_composition_without_a_final_name_is_spec_invalid(root, monkeypatch):
    run(root)

    def final_name(data_root, document):
        raise layout.InvalidPathValueError("synthetic: no path")

    monkeypatch.setattr(spec_file, "final_name", final_name)
    assert refused(root).kind == "spec_invalid"


@pytest.mark.parametrize("content", [b'{"a": 1}', b'{"a": 1}\r\n', b'{"a": 1}\n'])
def test_a_content_out_of_the_written_form_is_spec_invalid(root, monkeypatch, content):
    run(root)
    monkeypatch.setattr(spec_tool, "_encoded", lambda document: content)
    assert refused(root).kind == "spec_invalid"


def test_a_composition_that_cannot_be_encoded_is_spec_invalid(root, monkeypatch):
    run(root)
    original = spec_tool._compose

    def compose(run_id, stated):
        document = original(run_id, stated)
        document["task"]["op_signature"]["record"]["label"] = "\ud800"
        return document

    monkeypatch.setattr(spec_tool, "_compose", compose)
    assert refused(root).kind == "spec_invalid"


def test_a_second_call_is_spec_exists_and_changes_nothing(root):
    run(root)
    write(Source(root))
    first = spec_path(root).read_bytes()
    before = tree(root)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root))
    assert failure.value.kind == "spec_exists"
    assert failure.value.message.startswith(SPEC_PATH)
    assert tree(root) == before
    assert spec_path(root).read_bytes() == first


def test_a_file_under_the_name_is_neither_read_nor_replaced(root, monkeypatch):
    run(root)
    place(spec_path(root), b"anything at all")
    before = tree(root)
    original = Path.read_bytes

    def read_bytes(path):
        assert path.name != "spec.json"
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root))
    monkeypatch.undo()
    assert failure.value.kind == "spec_exists"
    assert tree(root) == before


def test_a_failing_write_is_spec_not_written(root, monkeypatch):
    run(root)

    def write_once(path, content):
        raise OSError(errno.EIO, "Input/output error", str(path))

    monkeypatch.setattr(once_write, "write_once", write_once)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root))
    assert failure.value.kind == "spec_not_written"
    assert failure.value.message == (
        f"{SPEC_PATH}: was not written: OSError: Input/output error"
    )
    assert str(root) not in failure.value.message
    assert not spec_path(root).exists()


def test_a_failure_of_the_spec_file_write_is_spec_not_written(root, monkeypatch):
    run(root)

    def failing(data_root, content):
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(spec_file, "write", failing)
    failure = refused(root)
    assert failure.kind == "spec_not_written"
    assert failure.message == (
        f"{SPEC_PATH}: was not written: PermissionError: Permission denied"
    )


def test_a_data_root_gone_since_it_was_obtained_is_spec_not_written(root, monkeypatch):
    run(root)
    original = run_file_tools.read

    def read(data_root, run_id, name):
        found = original(data_root, run_id, name)
        shutil.rmtree(data_root)
        return found

    monkeypatch.setattr(run_file_tools, "read", read)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root))
    assert failure.value.kind == "spec_not_written"
    assert failure.value.message == (
        f"{SPEC_PATH}: was not written: FileNotFoundError: "
        "the data root is not an existing directory"
    )
    assert not root.exists()


# Order


def test_invalid_request_comes_before_no_data_root(root):
    source = FailingSource()
    assert refused(root, request(round=1), source).kind == "invalid_request"
    assert source.calls == 0


def test_no_data_root_comes_before_run_file_missing(root, tmp_path):
    assert refused(root, source=Source(tmp_path / "missing")).kind == "no_data_root"


def test_candidates_per_round_comes_before_op_signature(root):
    document = instance_document(op(dtype="fp16"), candidates_per_round=2)
    run(root, document)
    assert refused(root).kind == "candidates_per_round_not_covered"
    run(root, instance_document(candidates_per_round=None, op_signature=None))
    assert refused(root).kind == "candidates_per_round_not_stated"


def test_op_signature_comes_before_objective(root):
    run(root, instance_document(op(layout="col_major"), objective=None))
    assert refused(root).kind == "op_signature_not_covered"
    run(root, instance_document(op_signature=None, objective=None))
    assert refused(root).kind == "op_signature_not_stated"


def test_objective_comes_before_spec_invalid(root, monkeypatch):
    run(root, instance_document(objective=None))
    monkeypatch.setattr(spec_tool, "_encoded", lambda document: b"{")
    assert refused(root).kind == "objective_not_stated"


def test_spec_invalid_comes_before_spec_exists(root, monkeypatch):
    run(root)
    write(Source(root))
    monkeypatch.setattr(spec_tool, "_encoded", lambda document: b"{")
    with pytest.raises(ToolFailure) as failure:
        write(Source(root))
    assert failure.value.kind == "spec_invalid"


# What is not mapped, and what is read


def test_an_error_of_covers_is_not_mapped(root, monkeypatch):
    run(root)

    def covers(record):
        raise keys.InvalidRecordError("synthetic")

    monkeypatch.setattr(gemm_contract, "covers", covers)
    with pytest.raises(keys.InvalidRecordError):
        write(Source(root))
    with pytest.raises(ToolFailure) as failure:
        tools.call(default_registry(Source(root)), "spec.write", request())
    assert failure.value.kind == "tool_crashed"
    assert not (root / "runs" / RUN / "rounds").exists()


def test_each_call_asks_the_source_once_and_reads_the_instance_only(root, monkeypatch):
    run(root)
    names = []
    original = run_file_tools.read

    def read(data_root, run_id, name):
        names.append(name)
        return original(data_root, run_id, name)

    monkeypatch.setattr(run_file_tools, "read", read)
    source = Source(root)
    definition = spec_tool.definition(source)
    assert definition.function(request()) == {}
    with pytest.raises(ToolFailure):
        definition.function(request())
    assert source.calls == 2
    assert names == ["instance.json", "instance.json"]
    assert not layout.run_file(root, RUN, "STATE.json").exists()
    assert not (root / "db").exists()


# Rounds >= 1 (ADR-0151)

ACCELERATOR = "synthetic_hw"
SIM = "correctness_check_sim_v2"
BOARD = "correctness_check_board_v2"
PASS = {"outcome": "pass", "max_abs_error": 0.0}


def entry(entry_id, applies=None):
    lines = "\n".join(catalog.APPLIES_TO if applies is None else applies)
    return (
        f"# {entry_id}\n\n## Applies to\n\n{lines}\n\n## When\n\nWorth trying.\n\n"
        f"## Guidance\n\nUse {entry_id}.\n"
    ).encode()


@pytest.fixture
def shelf(tmp_path, monkeypatch):
    source = tmp_path / "catalog"
    directory = source / ACCELERATOR
    directory.mkdir(parents=True)
    for entry_id in ("loop_order", "tiling", "unrolling"):
        (directory / f"{entry_id}.md").write_bytes(entry(entry_id))
    monkeypatch.setattr(catalog, "SOURCE", source)
    return directory


@pytest.fixture
def logged(tmp_path):
    directory = tmp_path / "logged"
    directory.mkdir()
    return directory


def technique(entry_id):
    return {"id": entry_id, "text": f"Use {entry_id}."}


def later(round=1, techniques=None, **changes):
    listed = [] if techniques is None else techniques
    return request(round=round, **changes) | {"techniques": listed}


def later_path(root, round=1):
    return layout.attempt_artefact(root, RUN, round, 1, 1, "spec.json")


def expected_later(document, round=1, techniques=(), attempts=()):
    made = expected_spec(document)
    made["id"]["round"] = round
    made["guidance"]["techniques"] = [technique(t) for t in techniques]
    made["feedback"]["attempts"] = list(attempts)
    return made


def check(root, round, step, **outcome):
    numbers = {"round": round, "candidate": 1, "attempt": 1}
    data = {"step": step, "execution": 1}
    events.append(root, RUN, journal.STEP_STARTED, data, **numbers)
    ended = data | {"spend": {}, **outcome}
    events.append(root, RUN, journal.STEP_ENDED, ended, **numbers)


def passed_round_0(root):
    write(Source(root))
    check(root, 0, SIM, result=PASS)
    check(root, 0, BOARD, result=PASS)


def no_path_in(message, root):
    for path in (root.parent, catalog.SOURCE):
        assert str(path) not in message
        assert Path(path).as_posix() not in message


def refused_later(root, body, source=None):
    before = tree(root)
    with pytest.raises(ToolFailure) as failure:
        write(source or Source(root), body)
    assert tree(root) == before
    no_path_in(failure.value.message, root)
    return failure.value


def written(root, round=1):
    content = later_path(root, round).read_bytes()
    document = json.loads(content)
    spec.validate(document)
    final = spec_file.final_name(root, spec_file.parse(content))
    assert final == later_path(root, round)
    assert content == (json.dumps(document, indent=2) + "\n").encode()
    return document


def test_round_1_after_a_round_0_that_passed_carries_the_ids_and_the_attempt(
    logged, shelf
):
    document = instance_document()
    run(logged, document)
    passed_round_0(logged)
    log = layout.run_file(logged, RUN, "events.ndjson").read_bytes()
    round_0 = spec_path(logged).read_bytes()
    source = Source(logged)
    body = later(techniques=["tiling", "loop_order"])
    assert spec_tool.definition(source).function(body) == {}
    assert source.calls == 1
    relative = later_path(logged).relative_to(logged).as_posix()
    assert relative == SPEC_PATH.replace("rounds/0000", "rounds/0001")
    attempt = {"round": 0, "candidate": 1, "attempt": 1, "techniques": []}
    assert written(logged) == expected_later(
        document, 1, ["tiling", "loop_order"], [attempt]
    )
    assert layout.run_file(logged, RUN, "events.ndjson").read_bytes() == log
    assert spec_path(logged).read_bytes() == round_0


def test_round_1_with_no_ids_and_no_earlier_attempt_reads_no_catalog(
    root, tmp_path, monkeypatch
):
    document = instance_document()
    run(root, document)
    monkeypatch.setattr(catalog, "SOURCE", tmp_path / "missing")
    calls = []
    monkeypatch.setattr(catalog, "technique", lambda *a, **k: calls.append(a))
    assert write(Source(root), later()) == {}
    assert written(root) == expected_later(document)
    assert calls == []


def test_a_round_1_request_answers_through_the_registry_and_the_mcp_name(root, shelf):
    run(root)
    registry = default_registry(Source(root))
    assert tools.call(registry, "spec.write", later(techniques=["tiling"])) == {}
    assert written(root)["guidance"]["techniques"] == [technique("tiling")]
    params = {"name": "spec_write", "arguments": later(2, ["unrolling"])}
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    stdout = io.BytesIO()
    status = mcp_front.main(
        [],
        registry=registry,
        stdin=io.BytesIO((json.dumps(message) + "\n").encode()),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0
    result = json.loads(stdout.getvalue())["result"]
    assert result["isError"] is False
    assert written(root, 2)["guidance"]["techniques"] == [technique("unrolling")]


def test_a_run_whose_accelerator_has_no_catalog_takes_only_an_empty_list(
    root, tmp_path, monkeypatch
):
    document = instance_document()
    run(root, document)
    (tmp_path / "empty").mkdir()
    monkeypatch.setattr(catalog, "SOURCE", tmp_path / "empty")
    failure = refused_later(root, later(techniques=["tiling"]))
    assert failure.kind == "catalog_unusable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: the catalog directory is not there; "
        "nothing was written"
    )
    assert write(Source(root), later()) == {}
    assert written(root) == expected_later(document)


def test_a_large_round_with_no_earlier_rounds_has_empty_feedback(root):
    document = instance_document()
    run(root, document)
    assert write(Source(root), later(9999)) == {}
    assert "rounds/9999/" in later_path(root, 9999).as_posix()
    assert written(root, 9999) == expected_later(document, 9999)
    assert write(Source(root), later(keys.MAX_INTEGER)) == {}
    assert written(root, keys.MAX_INTEGER)["id"]["round"] == keys.MAX_INTEGER


def test_the_order_of_the_ids_is_the_requests(root, shelf):
    run(root)
    ids = ["unrolling", "loop_order", "tiling"]
    write(Source(root), later(techniques=ids))
    assert [t["id"] for t in written(root)["guidance"]["techniques"]] == ids


@pytest.mark.parametrize(
    ("body", "named"),
    [
        (request(techniques=[]), "techniques"),
        (request(techniques=["tiling"]), "techniques"),
        (request(round=1), "techniques"),
        (later(techniques="tiling"), "techniques"),
        (later(techniques={"tiling": 1}), "techniques"),
        (later() | {"techniques": None}, "techniques"),
        (later(techniques=[3]), "techniques[0]"),
        (later(techniques=["tiling", None]), "techniques[1]"),
        (later(techniques=["A"]), "techniques[0]"),
        (later(techniques=[""]), "techniques[0]"),
        (later(techniques=["a" * 33]), "techniques[0]"),
        (later(techniques=["x-y"]), "techniques[0]"),
        (later(techniques=["tiling", "unrolling", "tiling"]), "techniques[2]"),
        (later(round=True), "round"),
        (later(round=-1), "round"),
        (later(round=2**53), "round"),
        (later(round=1.0), "round"),
        (later(candidate=2), "candidate"),
        (later(attempt=2), "attempt"),
        (later(extra=1), "'extra'"),
    ],
)
def test_a_later_round_request_breaking_the_rule_is_invalid(root, body, named):
    run(root)
    source = Source(root)
    failure = refused_later(root, body, source)
    assert failure.kind == "invalid_request"
    assert named in failure.message
    assert source.calls == 0
    assert not (root / "runs" / RUN / "rounds").exists()


def test_the_messages_of_the_techniques_member(root):
    assert refused_later(root, request(techniques=[])).message == (
        "techniques: is taken only with a round of 1 or more"
    )
    assert refused_later(root, request(round=1)).message == (
        "the request lacks the member techniques, which a round of 1 or more requires"
    )
    assert refused_later(root, later(techniques="x")).message == (
        "techniques: must be an array, got str"
    )
    assert refused_later(root, later(techniques=["x", "x"])).message == (
        "techniques[1]: 'x' is given twice"
    )
    assert refused_later(root, later(extra=1)).message == (
        "the request takes the members run_id, round, candidate, attempt, "
        "techniques only, not 'extra'"
    )
    assert refused_later(root, later(round=-1)).message == (
        f"round: must be from 0 to {keys.MAX_INTEGER}, got -1"
    )


def test_a_catalog_refused_by_its_rules_is_catalog_unusable(root, shelf):
    run(root)
    (shelf / "notes.txt").write_bytes(b"x")
    failure = refused_later(root, later(techniques=["tiling"]))
    assert failure.kind == "catalog_unusable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: the catalog directory is refused: the catalog "
        "holds a file not named '<name>.md'; nothing was written"
    )


def test_a_catalog_that_cannot_be_read_is_catalog_unusable(root, shelf, monkeypatch):
    run(root)
    original = Path.read_bytes

    def read_bytes(path):
        if path.suffix == ".md":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    failure = refused_later(root, later(techniques=["tiling"]))
    assert failure.kind == "catalog_unusable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: the catalog directory cannot be read: "
        "PermissionError: Permission denied; nothing was written"
    )


def test_an_id_with_no_entry_is_technique_unknown(root, shelf):
    run(root)
    failure = refused_later(root, later(techniques=["tiling", "fusion", "vectors"]))
    assert failure.kind == "technique_unknown"
    assert failure.message == (
        f"catalog/{ACCELERATOR}: holds no entry fusion: the accelerator "
        f"{ACCELERATOR} has no such technique; nothing was written"
    )


def test_an_entry_for_another_dtype_is_technique_not_applicable(
    root, shelf, monkeypatch
):
    run(root)
    applies = ("- kind: gemm", "- dtype: fp16", "- layout: row_major", "- language: c")
    monkeypatch.setattr(catalog, "APPLIES_TO", applies)
    for path in shelf.iterdir():
        path.write_bytes(entry(path.stem, applies))
    failure = refused_later(root, later(techniques=["tiling"]))
    assert failure.kind == "technique_not_applicable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}/tiling.md: applies to the dtype fp16, not the "
        "spec's fp32; nothing was written"
    )


def test_an_earlier_spec_that_is_not_json_is_feedback_unreadable(root):
    run(root)
    place(spec_path(root), b"not json")
    failure = refused_later(root, later())
    assert failure.kind == "feedback_unreadable"
    assert failure.message.startswith(SPEC_PATH)


def test_a_damaged_log_line_is_run_file_invalid(logged):
    run(logged)
    write(Source(logged))
    place(layout.run_file(logged, RUN, "events.ndjson"), b"{\n")
    failure = refused_later(logged, later())
    assert failure.kind == "run_file_invalid"
    assert failure.message.startswith(f"runs/{RUN}/events.ndjson")


def test_a_check_result_without_an_admitted_outcome_is_check_result_invalid(logged):
    run(logged)
    write(Source(logged))
    check(logged, 0, SIM, result={"outcome": "maybe"})
    assert refused_later(logged, later()).kind == "check_result_invalid"


def test_a_second_round_1_call_is_spec_exists_and_changes_nothing(root, shelf):
    run(root)
    write(Source(root), later(techniques=["tiling"]))
    first = later_path(root).read_bytes()
    failure = refused_later(root, later(techniques=["unrolling"]))
    assert failure.kind == "spec_exists"
    assert failure.message.startswith(SPEC_PATH.replace("0000", "0001"))
    assert later_path(root).read_bytes() == first


def test_invalid_request_of_a_later_round_comes_before_no_data_root(root):
    source = FailingSource()
    assert refused_later(root, request(round=2), source).kind == "invalid_request"
    body = request(techniques=[])
    assert refused_later(root, body, source).kind == "invalid_request"
    assert source.calls == 0


def test_objective_comes_before_catalog_unusable(root, tmp_path, monkeypatch):
    run(root, instance_document(objective=None))
    monkeypatch.setattr(catalog, "SOURCE", tmp_path / "missing")
    body = later(techniques=["tiling"])
    assert refused_later(root, body).kind == "objective_not_stated"


def test_technique_unknown_comes_before_feedback_unreadable(root, shelf):
    run(root)
    place(spec_path(root), b"not json")
    body = later(techniques=["fusion"])
    assert refused_later(root, body).kind == "technique_unknown"


def test_feedback_unreadable_comes_before_spec_invalid(root, monkeypatch):
    run(root)
    place(spec_path(root), b"not json")
    original = spec_tool._compose

    def compose(run_id, stated):
        return original(run_id, stated) | {"schema_version": 3}

    monkeypatch.setattr(spec_tool, "_compose", compose)
    assert refused_later(root, later()).kind == "feedback_unreadable"
    spec_path(root).unlink()
    failure = refused_later(root, later())
    assert failure.kind == "spec_invalid"
    assert failure.message.startswith(SPEC_PATH.replace("0000", "0001"))


def test_spec_invalid_of_a_later_round_comes_before_spec_exists(root, monkeypatch):
    run(root)
    write(Source(root), later())
    monkeypatch.setattr(spec_tool, "_encoded", lambda document: b"{")
    assert refused_later(root, later()).kind == "spec_invalid"


def test_a_later_round_reads_no_state_or_selection_file(logged, shelf, monkeypatch):
    run(logged)
    passed_round_0(logged)
    place(layout.run_file(logged, RUN, "STATE.json"), b"not json")
    hypotheses = layout.hypothesis_record(logged, RUN, 1)
    place(hypotheses, b"not json")
    place(hypotheses.parent / "decision.md", b"not markdown")
    opened = []
    for module, name in ((io, "open"), (os, "open")):
        original = getattr(module, name)

        def spy(path, *args, original=original, **kwargs):
            opened.append(Path(os.fsdecode(path)).name)
            return original(path, *args, **kwargs)

        monkeypatch.setattr(module, name, spy)
    source = Source(logged)
    assert write(source, later(techniques=["tiling"])) == {}
    monkeypatch.undo()
    assert source.calls == 1
    assert "instance.json" in opened
    assert "events.ndjson" in opened
    assert "tiling.md" in opened
    for name in ("STATE.json", "hypotheses.json", "decision.md"):
        assert name not in opened
    assert written(logged)["id"]["round"] == 1


# The contracts of the contract table (ADR-0177 decision 2)

CONTRACTS = (
    (gemm_contract, gemm_contract.FIRST_SHAPES[0]),
    (gemm_bf16_contract, gemm_bf16_contract.SHAPES[-1]),
    (rmsnorm_bf16_contract, rmsnorm_bf16_contract.SHAPES[1]),
    (elementwise_add_bf16_contract, elementwise_add_bf16_contract.SHAPES[2]),
    (swiglu_bf16_contract, swiglu_bf16_contract.SHAPES[0]),
    (rope_bf16_contract, rope_bf16_contract.SHAPES[0]),
    (sdpa_kv_cache_bf16_contract, sdpa_kv_cache_bf16_contract.SHAPES[-1]),
)
BF16 = CONTRACTS[1:]


def named(contract):
    return contract.__name__.rsplit(".", 1)[1]


def applies_to(contract):
    return (
        f"- kind: {contract.KIND}",
        f"- dtype: {contract.DTYPE}",
        f"- layout: {contract.LAYOUT}",
        f"- language: {contract.LANGUAGE}",
    )


@pytest.mark.parametrize(
    "contract, shape", CONTRACTS, ids=[named(c) for c, _ in CONTRACTS]
)
def test_round_0_composes_the_spec_of_each_contract(root, contract, shape):
    record = contract.op_signature_record(*shape)
    document = instance_document(record)
    run(root, document)
    assert write(Source(root)) == {}
    content = spec_path(root).read_bytes()
    composed = spec_file.parse(content)
    assert composed["task"]["contract"] == contract.task_contract(*shape)
    assert composed["task"]["op_signature"] == document["op_signature"]
    expected = expected_spec(document) if contract is gemm_contract else None
    if expected is not None:
        assert composed == expected
    else:
        assert set(composed) == set(expected_spec(instance_document()))
        assert composed["id"] == expected_spec(instance_document())["id"]
        assert composed["hw_profile"] == document["hw_profile"]
        assert composed["task"]["objective"] == OBJECTIVE
        assert composed["guidance"] == {"techniques": []}
        assert composed["feedback"] == {"attempts": []}


@pytest.mark.parametrize("contract, shape", BF16, ids=[named(c) for c, _ in BF16])
def test_a_later_round_of_a_bf16_contract_takes_entries_that_name_it(
    root, shelf, monkeypatch, contract, shape
):
    applies = applies_to(contract)
    monkeypatch.setattr(catalog, "APPLIES_TO", applies)
    for path in shelf.iterdir():
        path.write_bytes(entry(path.stem, applies))
    record = contract.op_signature_record(*shape)
    run(root, instance_document(record))
    assert write(Source(root), later(techniques=["tiling", "loop_order"])) == {}
    made = written(root)
    assert made["guidance"]["techniques"] == [
        technique("tiling"),
        technique("loop_order"),
    ]
    assert made["task"]["contract"] == contract.task_contract(*shape)


@pytest.mark.parametrize("contract, shape", BF16, ids=[named(c) for c, _ in BF16])
def test_a_later_round_of_a_bf16_contract_refuses_an_fp32_entry(
    root, shelf, contract, shape
):
    run(root, instance_document(contract.op_signature_record(*shape)))
    failure = refused_later(root, later(techniques=["tiling"]))
    assert failure.kind == "technique_not_applicable"
    assert failure.message == (
        f"catalog/{ACCELERATOR}/tiling.md: applies to the kind gemm, not the "
        f"spec's {contract.KIND}; nothing was written"
        if contract.KIND != "gemm"
        else f"catalog/{ACCELERATOR}/tiling.md: applies to the dtype fp32, not the "
        "spec's bf16; nothing was written"
    )


NOT_COVERED = {
    "gemm_bf16_zero": gemm_bf16_contract.op_signature_record(1, 2048, 8192)
    | {"shape": {"m": 0, "k": 2048, "n": 8192}},
    "rope_odd_d": rope_bf16_contract.op_signature_record(1, 32, 64)
    | {"shape": {"m": 1, "h": 32, "d": 63}},
    "sdpa_l_below_m": sdpa_kv_cache_bf16_contract.op_signature_record(32, 32, 32, 8, 64)
    | {"shape": {"m": 32, "l": 31, "h": 32, "h_kv": 8, "d": 64}},
    "sdpa_h_not_a_multiple": sdpa_kv_cache_bf16_contract.op_signature_record(
        1, 1, 32, 8, 64
    )
    | {"shape": {"m": 1, "l": 1, "h": 32, "h_kv": 7, "d": 64}},
    "rmsnorm_unknown_dtype": rmsnorm_bf16_contract.op_signature_record(1, 2048)
    | {"dtype": "bf8"},
    "gemm_fp16": op(dtype="fp16"),
    "swiglu_fp32": swiglu_bf16_contract.op_signature_record(1, 8192)
    | {"dtype": "fp32"},
    "elementwise_add_col_major": elementwise_add_bf16_contract.op_signature_record(
        1, 2048
    )
    | {"layout": "col_major"},
    "gemm_bf16_col_major": gemm_bf16_contract.op_signature_record(1, 2, 3)
    | {"layout": "col_major"},
}


@pytest.mark.parametrize("record", NOT_COVERED.values(), ids=list(NOT_COVERED))
def test_a_record_no_contract_covers_is_op_signature_not_covered(root, record):
    run(root, instance_document(record))
    failure = refused(root)
    assert failure.kind == "op_signature_not_covered"
    assert failure.message == (
        f"{INSTANCE_PATH}: op_signature: the stated record is not covered by any "
        "kernel contract of the package; nothing was written"
    )
