import errno
import io
import json
import os
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    case_lookup,
    cases,
    cases_file,
    cases_tool,
    hypotheses_cases,
    hypotheses_write_tool,
    instance_file,
    key_records,
    keys,
    layout,
    mcp_front,
    tools,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

READER = "20261020t093000z-0f1e2d3c4b5a6978"
OTHER_A = "20261009t012331z-9f3a6c1e0b7d4a52"
OTHER_B = "20261001t000000z-0000000000000001"
PLACEHOLDER = "NOT-DECIDED-HERE"
INSTANCE_PATH = f"runs/{READER}/instance.json"


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
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }
    return record | changes


HW_KEY = keys.hw_profile_key(hw())
OP_KEY = keys.op_signature_key(op())
KEY_DIR = f"db/{HW_KEY.name}/{OP_KEY.name}"


def ref(round):
    return {"round": round, "candidate": 1, "attempt": 1}


def hypothesis_record(run_id, round, ids=("h1",)):
    return {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "candidates": 1,
        "hypotheses": [
            {
                "id": hypothesis,
                "statement": PLACEHOLDER,
                "basis": [{"kind": "attempt", "ref": ref(0), "text": PLACEHOLDER}],
                "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
                "origin": "system",
                "tested_by": [1],
            }
            for hypothesis in ids
        ],
    }


def written(document):
    return json.dumps(document, indent=2).encode() + b"\n"


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


@pytest.fixture
def key_dir(root):
    key_records.store_hw_profile(root, hw())
    key_records.store_op_signature(root, HW_KEY.name, op())
    return layout.op_signature_dir(root, HW_KEY.name, OP_KEY.name)


def store_case(root, run_id, round, ids=("h1",)):
    document = cases.build(hypothesis_record(run_id, round, ids))
    cases_file.write(root, HW_KEY.name, OP_KEY.name, written(document))
    return document


def case_name(run_id, round):
    return f"case-{run_id}-{round:04d}.json"


def write_instance(root, with_op=True):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": HW_KEY.name, "record": hw()},
    }
    if with_op:
        document["op_signature"] = {"key": OP_KEY.name, "record": op()}
    instance_file.write(root, READER, written(document))


def instance_path(root):
    return layout.run_file(root, READER, "instance.json")


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


def tree(path):
    found = {}
    for directory, _, files in os.walk(path):
        here = Path(directory)
        found[here.relative_to(path).as_posix()] = None
        for name in files:
            found[(here / name).relative_to(path).as_posix()] = (
                here / name
            ).read_bytes()
    return found


def look_up(source, request=None):
    _, function, _, _ = cases_tool.definition(source)
    return function({"run_id": READER} if request is None else request)


def refused(root, request=None, *, source=None):
    with pytest.raises(ToolFailure) as caught:
        look_up(Source(root) if source is None else source, request)
    return caught.value


def no_case(key=None):
    return {"key": key, "cases": [], "cases_read": [], "reports": []}


THE_KEY = {"hw_profile": HW_KEY.name, "op_signature": OP_KEY.name}


# The definition


def test_public_names_and_documentation():
    assert cases_tool.__doc__
    assert cases_tool.definition.__doc__
    assert cases_tool.NAME == "cases.lookup"
    assert cases_tool.KIND_CASES_UNREADABLE == "cases_unreadable"
    assert (
        cases_tool.KIND_CASES_UNREADABLE == hypotheses_write_tool.KIND_CASES_UNREADABLE
    )


def test_the_definition_is_a_tool_definition():
    made = cases_tool.definition(lambda: Path("."))
    assert isinstance(made, ToolDefinition)
    name, function, description, schema = made
    assert name == "cases.lookup"
    assert callable(function)
    for word in ("cases_read", "reports", "cases_unreadable", "not a failure"):
        assert word in description
    assert schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"}
        },
        "required": ["run_id"],
        "additionalProperties": False,
    }


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="callable"):
        cases_tool.definition(source)


# The result


def test_a_hit_gives_the_cases_of_other_runs_in_name_order(root, key_dir):
    store_case(root, READER, 1)
    a = store_case(root, OTHER_A, 2, ids=("h1", "h2"))
    b = store_case(root, OTHER_B, 3)
    write_instance(root)
    source = Source(root)
    before = tree(root)

    result = look_up(source)

    assert result == {
        "key": THE_KEY,
        "cases": [b, a],
        "cases_read": [
            {"run_id": OTHER_B, "round": 3},
            {"run_id": OTHER_A, "round": 2},
        ],
        "reports": [],
    }
    assert source.calls == 1
    assert tree(root) == before
    json.dumps(result, allow_nan=False)


def test_the_result_is_the_lookup_of_the_run(root, key_dir):
    store_case(root, OTHER_A, 1)
    store_case(root, READER, 2)
    place(key_dir / case_name(OTHER_B, 1), b"{}")
    write_instance(root)

    found = case_lookup.lookup(root, READER)
    result = look_up(Source(root))

    assert result["cases"] == list(found.cases)
    assert result["cases_read"] == case_lookup.cases_read(found)
    assert result["reports"] == [
        {"path": report.path, "kind": report.kind, "reason": report.reason}
        for report in found.reports
    ]


def test_a_record_copying_cases_read_passes_the_rules_between_files(root, key_dir):
    store_case(root, OTHER_A, 1, ids=("h1", "h2"))
    store_case(root, OTHER_B, 2)
    write_instance(root)

    result = look_up(Source(root))
    record = hypothesis_record(READER, 1)
    record["cases_read"] = result["cases_read"]
    record["hypotheses"][0]["basis"].append(
        {
            "kind": "case",
            "case": {"run_id": OTHER_A, "round": 1, "hypothesis": "h2"},
            "text": PLACEHOLDER,
        }
    )

    found = hypotheses_cases.check_run(root, record)
    assert case_lookup.cases_read(found) == record["cases_read"]


def test_a_hit_with_no_case_gives_the_key_alone(root, key_dir):
    store_case(root, READER, 1)
    write_instance(root)
    assert look_up(Source(root)) == no_case(THE_KEY)


def test_a_miss_gives_no_key_and_no_case(root):
    write_instance(root)
    assert look_up(Source(root)) == no_case()
    assert not (root / "db").exists()


def test_a_missing_op_signature_record_is_a_miss(root):
    key_records.store_hw_profile(root, hw())
    place(
        layout.case_record(root, HW_KEY.name, OP_KEY.name, OTHER_A, 1),
        written(cases.build(hypothesis_record(OTHER_A, 1))),
    )
    write_instance(root)
    assert look_up(Source(root)) == no_case()


def test_a_run_that_states_no_op_signature_has_no_key(root, key_dir):
    store_case(root, OTHER_A, 1)
    write_instance(root, with_op=False)
    assert look_up(Source(root)) == no_case()


def test_a_colliding_key_record_is_carried_as_a_report(root, key_dir):
    store_case(root, OTHER_A, 1)
    path = key_dir / "op_signature.json"
    path.write_bytes(written(op(dtype="other_dtype")))
    write_instance(root)

    result = look_up(Source(root))

    assert (result["key"], result["cases"], result["cases_read"]) == (None, [], [])
    [report] = result["reports"]
    assert set(report) == {"path", "kind", "reason"}
    assert (report["path"], report["kind"]) == (
        f"{KEY_DIR}/op_signature.json",
        "key_record",
    )


def test_invalid_and_set_apart_files_are_reports_beside_the_cases(root, key_dir):
    a = store_case(root, OTHER_A, 1)
    other = cases.build(hypothesis_record(OTHER_B, 1))
    other["schema_version"] = 2
    place(key_dir / case_name(OTHER_B, 1), written(other))
    place(key_dir / "case-x.json", b"{not json")
    write_instance(root)

    result = look_up(Source(root))

    assert result["key"] == THE_KEY
    assert result["cases"] == [a]
    assert result["cases_read"] == [{"run_id": OTHER_A, "round": 1}]
    assert [(r["path"], r["kind"]) for r in result["reports"]] == [
        (f"{KEY_DIR}/{case_name(OTHER_B, 1)}", "set_apart"),
        (f"{KEY_DIR}/case-x.json", "invalid"),
    ]
    assert "schema_version" in result["reports"][0]["reason"]


def test_an_unreadable_case_is_a_report_and_the_rest_are_read(
    root, key_dir, monkeypatch
):
    a = store_case(root, OTHER_A, 1)
    store_case(root, OTHER_B, 1)
    write_instance(root)
    original = Path.read_bytes

    def failing(self):
        if self.name == case_name(OTHER_B, 1):
            raise PermissionError(errno.EACCES, "synthetic denial", str(self))
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", failing)
    result = look_up(Source(root))
    monkeypatch.undo()

    assert result["cases"] == [a]
    [report] = result["reports"]
    assert report["kind"] == "unreadable"
    assert "synthetic denial" in report["reason"]


# Every kind, in order


@pytest.mark.parametrize(
    ("request_", "message"),
    [
        ({}, "the request lacks the member run_id"),
        (
            {"run_id": READER, "round": 1},
            "the request takes the member run_id only, not 'round'",
        ),
        (
            {"run_id": READER, "b": 1, "a": 2},
            "the request takes the member run_id only, not 'a', 'b'",
        ),
    ],
)
def test_a_request_of_other_members_is_invalid(root, request_, message):
    source = Source(root)
    failure = refused(root, request_, source=source)
    assert (failure.kind, failure.message) == ("invalid_request", message)
    assert source.calls == 0


@pytest.mark.parametrize("run_id", [3, None, "", "Run-A", "../x", "a" * 65, True])
def test_a_malformed_run_id_is_invalid(root, run_id):
    source = Source(root)
    failure = refused(root, {"run_id": run_id}, source=source)
    assert failure.kind == "invalid_request"
    assert failure.message.startswith("the request's ")
    assert source.calls == 0


def test_no_data_root(root):
    write_instance(root)
    source = FailingSource()
    assert refused(root, source=source).kind == "no_data_root"
    assert source.calls == 1


def test_a_missing_instance_is_run_file_missing(root, key_dir):
    store_case(root, OTHER_A, 1)
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(INSTANCE_PATH)


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{", "run_file_invalid"),
        (written({"schema_version": 1}), "run_file_invalid"),
        (written({"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_an_instance_that_cannot_be_used_is_its_kind(root, content, kind):
    place(instance_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(INSTANCE_PATH)


def test_an_instance_that_is_no_regular_file_is_run_file_invalid(root):
    instance_path(root).mkdir(parents=True)
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message == f"{INSTANCE_PATH}: is not a regular file"


def test_an_unreadable_instance_is_run_file_unreadable(root, monkeypatch):
    write_instance(root)
    original = Path.read_bytes

    def read_bytes(path):
        if path.name == "instance.json":
            raise PermissionError(errno.EACCES, "Permission denied", str(path))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ToolFailure) as caught:
        look_up(Source(root))
    monkeypatch.undo()
    assert caught.value.kind == "run_file_unreadable"


def test_a_key_directory_that_cannot_be_listed_is_cases_unreadable(
    root, key_dir, monkeypatch
):
    store_case(root, OTHER_A, 1)
    write_instance(root)

    def listdir(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(case_lookup.os, "listdir", listdir)
    failure = refused(root)
    monkeypatch.undo()
    assert failure.kind == "cases_unreadable"
    assert failure.message == (
        f"{KEY_DIR}: the cases of the run's key could not be read: "
        "PermissionError: Permission denied"
    )
    assert str(root) not in failure.message


def test_a_failing_lookup_without_op_signature_names_the_instance(root, monkeypatch):
    write_instance(root, with_op=False)

    def find(*args):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(case_lookup, "find", find)
    failure = refused(root)
    assert failure.kind == "cases_unreadable"
    assert failure.message == (
        f"{INSTANCE_PATH}: the cases of the run's key could not be read: "
        "OSError: Input/output error"
    )


def test_a_data_root_gone_during_the_lookup_says_so(root, key_dir, monkeypatch):
    write_instance(root)

    def find(data_root, *args):
        shutil.rmtree(data_root)
        raise FileNotFoundError(errno.ENOENT, "No such file or directory")

    monkeypatch.setattr(case_lookup, "find", find)
    failure = refused(root)
    assert failure.kind == "cases_unreadable"
    assert failure.message.endswith(
        "FileNotFoundError: No such file or directory: the data root is not an "
        "existing directory"
    )


# Order


def test_invalid_request_comes_before_no_data_root():
    source = FailingSource()
    with pytest.raises(ToolFailure) as caught:
        look_up(source, {"run_id": READER, "x": 1})
    assert caught.value.kind == "invalid_request"
    assert source.calls == 0


def test_the_instance_comes_before_the_lookup(root, key_dir, monkeypatch):
    def find(*args):
        raise AssertionError("the lookup was reached")

    monkeypatch.setattr(case_lookup, "find", find)
    assert refused(root).kind == "run_file_missing"


def test_a_failing_call_creates_nothing(root, key_dir, monkeypatch):
    store_case(root, OTHER_A, 1)
    write_instance(root)
    before = tree(root)

    def listdir(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(case_lookup.os, "listdir", listdir)
    assert refused(root).kind == "cases_unreadable"
    monkeypatch.undo()
    assert tree(root) == before


# The registry and the MCP front


def test_the_default_registry_holds_cases_lookup(root, key_dir):
    a = store_case(root, OTHER_A, 1)
    write_instance(root)
    registry = default_registry(lambda: root)
    assert "cases.lookup" in registry.names()
    assert tools.call(registry, "cases.lookup", {"run_id": READER}) == {
        "key": THE_KEY,
        "cases": [a],
        "cases_read": [{"run_id": OTHER_A, "round": 1}],
        "reports": [],
    }


def _mcp(request_id, method, params):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return json.dumps(document).encode() + b"\n"


def test_the_mcp_front_lists_and_serves_cases_lookup(root, key_dir):
    a = store_case(root, OTHER_A, 1)
    write_instance(root)
    data = b"".join(
        [
            _mcp(1, "tools/list", {}),
            _mcp(
                2,
                "tools/call",
                {"name": "cases_lookup", "arguments": {"run_id": READER}},
            ),
            _mcp(3, "tools/call", {"name": "cases_lookup", "arguments": {}}),
        ]
    )
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=default_registry(lambda: root),
        stdin=io.BytesIO(data),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    listed, served, failed = (
        json.loads(line) for line in stdout.getvalue().splitlines()
    )
    assert "cases_lookup" in [tool["name"] for tool in listed["result"]["tools"]]
    assert mcp_front.mcp_name("cases.lookup") == "cases_lookup"
    assert served["result"]["isError"] is False
    assert json.loads(served["result"]["content"][0]["text"]) == {
        "key": THE_KEY,
        "cases": [a],
        "cases_read": [{"run_id": OTHER_A, "round": 1}],
        "reports": [],
    }
    assert failed["result"]["isError"] is True
    error = json.loads(failed["result"]["content"][0]["text"])["error"]
    assert error["kind"] == "invalid_request"
