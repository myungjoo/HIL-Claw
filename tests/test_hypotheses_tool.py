import errno
import json
import os
from pathlib import Path

import pytest

from hilclaw import (
    hypotheses_file,
    hypotheses_tool,
    keys,
    layout,
    mcp_front,
    tools,
    verdicts_tool,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
HYPOTHESES = {
    "schema_version": 1,
    "run_id": RUN,
    "round": 1,
    "candidates": 2,
    "hypotheses": [
        {
            "id": "h1",
            "statement": "unrolling lowers latency",
            "basis": [
                {
                    "kind": "attempt",
                    "ref": {"round": 0, "candidate": 1, "attempt": 1},
                    "text": "the baseline",
                }
            ],
            "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
            "origin": "system",
            "tested_by": [1, 2],
        }
    ],
}
KINDS = (
    "invalid_request",
    "no_data_root",
    "hypotheses_missing",
    "hypotheses_invalid",
    "hypotheses_unsupported",
    "hypotheses_unreadable",
    "bad_result",
)


def relative(round):
    return f"runs/{RUN}/rounds/{round:04d}/decision/hypotheses.json"


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
    data_root = tmp_path / "data"
    data_root.mkdir()
    return data_root


def entries(root):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


def with_document(root, document=HYPOTHESES):
    content = (json.dumps(document, indent=2) + "\n").encode()
    hypotheses_file.write(root, content)
    return content


def with_bytes(root, content, round=1, run_id=RUN):
    path = layout.hypothesis_record(root, run_id, round)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def read(source, request):
    return hypotheses_tool.definition(source).function(request)


def failure(source, request):
    root = getattr(source, "root", None)
    before = entries(root) if root is not None and root.is_dir() else None
    with pytest.raises(ToolFailure) as refused:
        read(source, request)
    if before is not None:
        assert entries(root) == before
    return refused.value


def request(round=1, run_id=RUN):
    return {"run_id": run_id, "round": round}


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = hypotheses_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == hypotheses_tool.NAME == "hypotheses.read"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "round": {"type": "integer", "minimum": 1, "maximum": keys.MAX_INTEGER},
        },
        "required": ["run_id", "round"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert hypotheses_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError, match="must be callable"):
        hypotheses_tool.definition(source)


def test_the_description_names_every_kind_and_what_it_tells():
    description = hypotheses_tool.definition(lambda: None).description
    for kind in KINDS:
        assert kind in description
    assert "rounds/<RRRR>/decision/hypotheses.json" in description
    assert "never part of the request" in description
    assert "round 0" in description
    assert '{"record":' in description


def test_the_kinds_are_those_of_verdicts_write_and_none_is_reserved():
    kinds = {
        name: value
        for name, value in vars(hypotheses_tool).items()
        if name.startswith("KIND_")
    }
    assert set(kinds.values()) == set(KINDS[2:6])
    for name, value in kinds.items():
        assert getattr(verdicts_tool, name) == value
    assert not set(kinds.values()) & tools.RESERVED_KINDS


# Happy path


def test_a_valid_record_is_returned_whole(root):
    content = with_document(root)
    source = Source(root)
    before = entries(root)
    result = read(source, request())
    assert list(result) == ["record"]
    assert result["record"] == HYPOTHESES == hypotheses_file.parse(content)
    assert source.calls == 1
    assert entries(root) == before


def test_an_unknown_top_level_member_is_returned_as_stored(root):
    document = HYPOTHESES | {"note": {"free": [1.5, -2, None, "x"]}}
    with_document(root, document)
    assert read(Source(root), request()) == {"record": document}


def test_the_result_passes_the_registry_and_the_mcp_front(root):
    with_document(root)
    registry = default_registry(Source(root))
    assert tools.call(registry, "hypotheses.read", request()) == {"record": HYPOTHESES}
    assert mcp_front.mcp_names(registry)["hypotheses_read"] == "hypotheses.read"


def test_a_round_above_any_round_of_the_run_is_read_without_state(root):
    document = HYPOTHESES | {"round": 7}
    with_document(root, document)
    assert read(Source(root), request(7)) == {"record": document}
    assert not layout.run_file(root, RUN, "STATE.json").exists()


def test_each_call_reads_the_file_anew(root):
    with_document(root)
    definition = hypotheses_tool.definition(Source(root))
    first = definition.function(request())
    first["record"]["round"] = 99
    assert definition.function(request()) == {"record": HYPOTHESES}


# The number range


def test_a_number_beyond_the_float_range_is_bad_result(root):
    text = json.dumps(HYPOTHESES)[:-1] + ', "far": 1e999}\n'
    with_bytes(root, text.encode())
    registry = default_registry(Source(root))
    with pytest.raises(ToolFailure) as refused:
        tools.call(registry, "hypotheses.read", request())
    assert refused.value.kind == tools.KIND_BAD_RESULT
    assert "far" in refused.value.message


def test_a_large_integer_in_an_open_member_is_returned(root):
    text = json.dumps(HYPOTHESES)[:-1] + ', "far": 1' + "0" * 400 + "}\n"
    with_bytes(root, text.encode())
    registry = default_registry(Source(root))
    result = tools.call(registry, "hypotheses.read", request())
    assert result["record"]["far"] == 10**400


# The request


@pytest.mark.parametrize(
    ("given", "message"),
    [
        (
            {"run_id": RUN, "round": 1, "data_root": "/x"},
            "the request takes the members run_id, round only, not 'data_root'",
        ),
        ({"round": 1}, "the request lacks the member run_id"),
        ({"run_id": RUN}, "the request lacks the member round"),
        ({"run_id": "Run A", "round": 1}, "the request's run_id"),
        ({"run_id": 3, "round": 1}, "the request's run_id"),
        (request(0), "round: must be an int from 1 to"),
        (request(-1), "round: must be an int from 1 to"),
        (request(keys.MAX_INTEGER + 1), "round: must be an int from 1 to"),
        (request(True), "round: must be an int from 1 to"),
        (request(1.0), "round: must be an int from 1 to"),
        (request("1"), "round: must be an int from 1 to"),
        (request(None), "round: must be an int from 1 to"),
    ],
)
def test_a_refused_request_is_invalid_request_and_asks_no_source(root, given, message):
    with_document(root)
    source = Source(root)
    refused = failure(source, given)
    assert refused.kind == tools.KIND_INVALID_REQUEST
    assert refused.message.startswith(message)
    assert source.calls == 0


def test_round_zero_is_refused_as_having_no_record(root):
    refused = failure(Source(root), request(0))
    assert "round 0 has no hypothesis record" in refused.message


def test_the_largest_round_is_admitted(root):
    refused = failure(Source(root), request(keys.MAX_INTEGER))
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_MISSING


# The data root


def test_a_failing_source_is_no_data_root():
    source = FailingSource()
    with pytest.raises(ToolFailure) as refused:
        read(source, request())
    assert refused.value.kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1


def test_a_data_root_that_is_no_directory_is_no_data_root(tmp_path):
    with pytest.raises(ToolFailure) as refused:
        read(Source(tmp_path / "absent"), request())
    assert refused.value.kind == tools.KIND_NO_DATA_ROOT
    assert not (tmp_path / "absent").exists()


# The read of the file


def test_a_missing_file_is_hypotheses_missing(root):
    refused = failure(Source(root), request())
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_MISSING
    assert refused.message == f"{relative(1)}: is missing"
    assert entries(root) == []


def test_a_missing_file_of_another_round_is_hypotheses_missing(root):
    with_document(root)
    refused = failure(Source(root), request(2))
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_MISSING
    assert refused.message == f"{relative(2)}: is missing"


def test_a_vanished_data_root_is_hypotheses_missing_and_says_so(root, monkeypatch):
    with_document(root)
    real = layout.hypothesis_record

    def vanishing(data_root, run_id, round):
        if root.exists():
            os.rename(root, root.with_name("gone"))
        return real(data_root, run_id, round)

    monkeypatch.setattr(layout, "hypothesis_record", vanishing)
    with pytest.raises(ToolFailure) as refused:
        read(Source(root), request())
    assert refused.value.kind == hypotheses_tool.KIND_HYPOTHESES_MISSING
    assert refused.value.message == (
        f"{relative(1)}: is missing: the data root is not an existing directory"
    )
    assert not root.exists()


def test_a_file_in_place_of_a_directory_is_hypotheses_missing(root):
    (root / "runs").mkdir()
    (root / "runs" / RUN).write_bytes(b"")
    refused = failure(Source(root), request())
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_MISSING


def test_a_directory_at_the_place_of_the_file_is_hypotheses_invalid(root):
    layout.hypothesis_record(root, RUN, 1).mkdir(parents=True)
    refused = failure(Source(root), request())
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_INVALID
    assert refused.message == f"{relative(1)}: is not a regular file"


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", hypotheses_tool.KIND_HYPOTHESES_INVALID),
        (b"{not json}\n", hypotheses_tool.KIND_HYPOTHESES_INVALID),
        (b"[]\n", hypotheses_tool.KIND_HYPOTHESES_INVALID),
        (b'{"schema_version": 1}\n', hypotheses_tool.KIND_HYPOTHESES_INVALID),
        (b'{"schema_version": 2}\n', hypotheses_tool.KIND_HYPOTHESES_UNSUPPORTED),
    ],
)
def test_unusable_bytes_are_refused_by_kind(root, content, kind):
    path = with_bytes(root, content)
    refused = failure(Source(root), request())
    assert refused.kind == kind
    assert refused.message.startswith(f"{relative(1)}: ")
    assert path.read_bytes() == content


def test_a_failed_read_is_hypotheses_unreadable(root, monkeypatch):
    with_document(root)

    def denied(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(Path, "read_bytes", denied)
    refused = failure(Source(root), request())
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_UNREADABLE
    assert refused.message == (
        f"{relative(1)}: could not be read: PermissionError: Permission denied"
    )
    assert str(root) not in refused.message


def test_a_failed_look_at_the_place_is_hypotheses_unreadable(root, monkeypatch):
    with_document(root)

    def failing(path):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(os, "lstat", failing)
    with pytest.raises(ToolFailure) as refused:
        read(Source(root), request())
    assert refused.value.kind == hypotheses_tool.KIND_HYPOTHESES_UNREADABLE
    assert refused.value.message == (
        f"{relative(1)}: could not be read: OSError: Input/output error"
    )


# The document against the request


def test_a_file_naming_another_round_is_hypotheses_invalid(root):
    content = (json.dumps(HYPOTHESES) + "\n").encode()
    with_bytes(root, content, round=2)
    refused = failure(Source(root), request(2))
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_INVALID
    assert refused.message == (
        f"{relative(2)}: round: must be the request's round 2, got 1"
    )


def test_a_file_naming_another_run_is_hypotheses_invalid(root):
    document = HYPOTHESES | {"run_id": "run-b"}
    with_bytes(root, (json.dumps(document) + "\n").encode())
    refused = failure(Source(root), request())
    assert refused.kind == hypotheses_tool.KIND_HYPOTHESES_INVALID
    assert refused.message == (
        f"{relative(1)}: run_id: must be the request's run_id 'run-a', got 'run-b'"
    )


def test_the_run_id_is_compared_before_the_round(root):
    document = HYPOTHESES | {"run_id": "run-b", "round": 3}
    with_bytes(root, (json.dumps(document) + "\n").encode(), round=2)
    refused = failure(Source(root), request(2))
    assert ": run_id: " in refused.message


# The read function


def test_read_returns_the_document_without_comparing_it(root):
    document = HYPOTHESES | {"run_id": "run-b"}
    with_bytes(root, (json.dumps(document) + "\n").encode())
    assert hypotheses_tool.read(root, RUN, 1) == document


@pytest.mark.parametrize(("run_id", "round"), [(RUN, 0), ("Run A", 1), (RUN, True)])
def test_read_refuses_arguments_that_name_no_record(root, run_id, round):
    with pytest.raises(layout.InvalidPathValueError):
        hypotheses_tool.read(root, run_id, round)
    assert entries(root) == []


def test_read_accepts_a_str_data_root(root):
    with_document(root)
    assert hypotheses_tool.read(str(root), RUN, 1) == HYPOTHESES


# The registry


def test_the_default_registry_holds_the_tool(root):
    registry = default_registry(Source(root))
    assert "hypotheses.read" in registry.names()
    held = registry.definition("hypotheses.read")
    made = hypotheses_tool.definition(lambda: root)
    assert (held.description, held.input_schema) == (
        made.description,
        made.input_schema,
    )
    assert mcp_front.mcp_name("hypotheses.read") == "hypotheses_read"
