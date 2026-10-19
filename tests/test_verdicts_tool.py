import copy
import errno
import io
import json
import os
from pathlib import Path

import pytest

from hilclaw import (
    hypotheses_file,
    layout,
    mcp_front,
    once_write,
    tools,
    verdicts_file,
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
            "tested_by": [1],
        },
        {
            "id": "h2",
            "statement": "tiling lowers latency",
            "basis": [
                {
                    "kind": "attempt",
                    "ref": {"round": 0, "candidate": 1, "attempt": 1},
                    "text": "the baseline",
                }
            ],
            "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
            "origin": "system",
            "tested_by": [2],
        },
    ],
}
HYPOTHESES_PATH = f"runs/{RUN}/rounds/0001/decision/hypotheses.json"
VERDICTS_PATH = f"runs/{RUN}/rounds/0001/eval/verdicts.json"
KINDS = (
    "invalid_request",
    "hypotheses_missing",
    "hypotheses_invalid",
    "hypotheses_unsupported",
    "hypotheses_unreadable",
    "verdicts_mismatch",
    "comparison_not_given",
    "verdicts_exist",
    "verdicts_not_written",
)


def ref(round=1, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


def check_entry(at=(1, 1, 1), point="board", outcome="pass"):
    return {"kind": "check", "ref": ref(*at), "point": point, "outcome": outcome}


def comparison(point="board", difference="lower"):
    return {
        "kind": "comparison",
        "metric": "latency_minimisation",
        "point": point,
        "measured": ref(1, 1, 1),
        "against": ref(0, 1, 1),
        "difference": difference,
    }


def verdict(hypothesis, evidence, value="inconclusive", cause="no comparison yet"):
    return {
        "hypothesis": hypothesis,
        "verdict": value,
        "cause": cause,
        "evidence": evidence,
    }


def record(*entries, **top):
    if not entries:
        entries = (
            verdict("h1", [check_entry()]),
            verdict("h2", [check_entry((1, 2, 1), point="sim", outcome="fail")]),
        )
    return {
        "schema_version": 1,
        "run_id": RUN,
        "round": 1,
        "verdicts": list(entries),
    } | top


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


def with_hypotheses(root, document=HYPOTHESES):
    content = (json.dumps(document, indent=2) + "\n").encode()
    hypotheses_file.write(root, content)


def eval_dir(root):
    return root / "runs" / RUN / "rounds" / "0001" / "eval"


def verdicts_path(root):
    return layout.verdict_record(root, RUN, 1)


def write(source, request):
    return verdicts_tool.definition(source).function(request)


def failure(source, request):
    with pytest.raises(ToolFailure) as refused:
        write(source, request)
    return refused.value


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = verdicts_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == verdicts_tool.NAME == "verdicts.write"
    assert source.calls == 0
    assert definition.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
            "record": {"type": "object"},
        },
        "required": ["run_id", "record"],
        "additionalProperties": False,
    }
    definition.input_schema["properties"].clear()
    assert verdicts_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError):
        verdicts_tool.definition(source)


def test_the_description_names_every_kind_and_what_it_tells():
    description = verdicts_tool.definition(lambda: None).description
    for kind in KINDS:
        assert kind in description
    assert "eval/verdicts.json" in description
    assert "never part of the request" in description
    assert "corrected and sent again" in description
    assert "refused for now" in description


def test_no_kind_of_the_module_is_reserved():
    kinds = {
        value for name, value in vars(verdicts_tool).items() if name.startswith("KIND_")
    }
    assert kinds == set(KINDS[1:])
    assert not kinds & tools.RESERVED_KINDS


def test_a_valid_record_is_written_and_parses_back(root):
    with_hypotheses(root)
    source = Source(root)
    given = record()
    sent = copy.deepcopy(given)
    assert not eval_dir(root).exists()
    assert write(source, {"run_id": RUN, "record": sent}) == {}
    assert source.calls == 1
    assert sent == given
    content = verdicts_path(root).read_bytes()
    assert verdicts_file.parse(content) == given
    assert list(eval_dir(root).iterdir()) == [verdicts_path(root)]


def test_the_written_bytes_end_with_one_line_feed_and_hold_no_carriage_return(root):
    with_hypotheses(root)
    given = record(
        verdict("h1", [check_entry()], cause="line one\r\nline two\rend\n"),
        verdict("h2", [check_entry((1, 2, 1))]),
    )
    write(Source(root), {"run_id": RUN, "record": given})
    content = verdicts_path(root).read_bytes()
    assert content.endswith(b"}\n")
    assert not content.endswith(b"\n\n")
    assert b"\r" not in content
    assert not content.startswith(b"\xef\xbb\xbf")
    assert verdicts_file.parse(content) == given


def test_non_ascii_text_is_written_as_utf_8_and_round_trips(root):
    with_hypotheses(root)
    cause = "지연이 줄지 않았다 — é \U0001f600"
    given = record(
        verdict("h1", [check_entry()], cause=cause),
        verdict("h2", [check_entry((1, 2, 1))]),
        note={"키": "값"},
    )
    write(Source(root), {"run_id": RUN, "record": given})
    content = verdicts_path(root).read_bytes()
    assert cause.encode("utf-8") in content
    assert json.loads(content.decode("utf-8")) == given


def test_the_members_are_written_in_the_order_given(root):
    with_hypotheses(root)
    given = record()
    reordered = dict(reversed(list(given.items())))
    write(Source(root), {"run_id": RUN, "record": reordered})
    text = verdicts_path(root).read_text(encoding="utf-8")
    assert list(json.loads(text)) == list(reordered)
    assert text.index('"verdicts"') < text.index('"schema_version"')


def bad_record_cases():
    empty = record()
    empty["verdicts"] = []
    unknown_member = record()
    unknown_member["verdicts"][0]["note"] = "x"
    no_version = record()
    del no_version["schema_version"]
    return [
        ("extra member", {"run_id": RUN, "record": record(), "data_root": "/x"}),
        ("missing run_id", {"record": record()}),
        ("missing record", {"run_id": RUN}),
        ("empty request", {}),
        ("bad run_id", {"run_id": "Run A", "record": record()}),
        ("run_id not a string", {"run_id": 3, "record": record()}),
        ("record a list", {"run_id": RUN, "record": [record()]}),
        ("record a string", {"run_id": RUN, "record": "{}"}),
        ("record null", {"run_id": RUN, "record": None}),
        ("no verdict", {"run_id": RUN, "record": empty}),
        ("unknown verdict member", {"run_id": RUN, "record": unknown_member}),
        ("no schema_version", {"run_id": RUN, "record": no_version}),
        ("round 0", {"run_id": RUN, "record": record(round=0)}),
        ("other schema_version", {"run_id": RUN, "record": record(schema_version=2)}),
        ("run_id mismatch", {"run_id": RUN, "record": record(run_id="run-b")}),
        ("lone surrogate", {"run_id": RUN, "record": record(note="\ud800")}),
        ("not a number", {"run_id": RUN, "record": record(note=float("nan"))}),
    ]


@pytest.mark.parametrize(
    "request_",
    [case for _, case in bad_record_cases()],
    ids=[label for label, _ in bad_record_cases()],
)
def test_a_refused_request_or_record_asks_no_source_and_creates_nothing(root, request_):
    with_hypotheses(root)
    source = Source(root)
    refused = failure(source, request_)
    assert refused.kind == tools.KIND_INVALID_REQUEST
    assert source.calls == 0
    assert not eval_dir(root).exists()


def test_the_messages_of_invalid_request_name_the_member(root):
    source = Source(root)
    other = failure(source, {"run_id": RUN, "record": record(schema_version=2)})
    assert other.message == "record: schema_version: is 2, not 1"
    mismatch = failure(source, {"run_id": RUN, "record": record(run_id="run-b")})
    assert mismatch.message == (
        "record.run_id: must be the request's run_id 'run-a', got 'run-b'"
    )
    extra = failure(source, {"run_id": RUN, "record": record(), "x": 1})
    assert extra.message == "the request takes the members run_id, record only, not 'x'"
    lacking = failure(source, {"run_id": RUN})
    assert lacking.message == "the request lacks the member record"
    listed = failure(source, {"run_id": RUN, "record": []})
    assert listed.message == "record: must be an object, got list"
    assert source.calls == 0


def test_a_failing_source_is_no_data_root(root):
    with_hypotheses(root)
    source = FailingSource()
    refused = failure(source, {"run_id": RUN, "record": record()})
    assert refused.kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1


def test_missing_hypotheses_are_hypotheses_missing(root):
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_MISSING
    assert refused.message == f"{HYPOTHESES_PATH}: is missing"
    assert not (root / "runs").exists()


def test_hypotheses_missing_with_a_vanished_data_root_say_so(root, monkeypatch):
    with_hypotheses(root)
    real = layout.hypothesis_record

    def vanishing(data_root, run_id, round):
        os.rename(root, root.with_name("gone"))
        return real(data_root, run_id, round)

    monkeypatch.setattr(layout, "hypothesis_record", vanishing)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_MISSING
    assert refused.message == (
        f"{HYPOTHESES_PATH}: is missing: the data root is not an existing directory"
    )


def test_a_file_in_place_of_a_directory_is_hypotheses_missing(root):
    (root / "runs").mkdir()
    (root / "runs" / RUN).write_bytes(b"")
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_MISSING


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"", verdicts_tool.KIND_HYPOTHESES_INVALID),
        (b"{not json}\n", verdicts_tool.KIND_HYPOTHESES_INVALID),
        (b'{"schema_version": 1}\n', verdicts_tool.KIND_HYPOTHESES_INVALID),
        (b'{"schema_version": 2}\n', verdicts_tool.KIND_HYPOTHESES_UNSUPPORTED),
    ],
)
def test_unusable_hypotheses_are_refused_by_kind(root, content, kind):
    path = layout.hypothesis_record(root, RUN, 1)
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == kind
    assert refused.message.startswith(f"{HYPOTHESES_PATH}: ")
    assert not eval_dir(root).exists()
    assert path.read_bytes() == content


def test_a_directory_at_the_place_of_the_hypotheses_is_hypotheses_invalid(root):
    layout.hypothesis_record(root, RUN, 1).mkdir(parents=True)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_INVALID
    assert refused.message == f"{HYPOTHESES_PATH}: is not a regular file"
    assert not eval_dir(root).exists()


def test_a_failed_read_of_the_hypotheses_is_hypotheses_unreadable(root, monkeypatch):
    with_hypotheses(root)

    def denied(path):
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(Path, "read_bytes", denied)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_HYPOTHESES_UNREADABLE
    assert refused.message == (
        f"{HYPOTHESES_PATH}: could not be read: PermissionError: Permission denied"
    )
    assert str(root) not in refused.message
    assert not eval_dir(root).exists()


@pytest.mark.parametrize(
    "given",
    [
        record(verdict("h1", [check_entry()])),
        record(*record()["verdicts"], verdict("h3", [check_entry()])),
        record(
            verdict("h1", [check_entry(), check_entry((0, 1, 1)), comparison()]),
            verdict("h2", [check_entry((1, 2, 1))]),
        ),
        record(
            verdict(
                "h1",
                [check_entry(), check_entry((0, 1, 1)), comparison()],
                value="refuted",
            ),
            verdict("h2", [check_entry((1, 2, 1))]),
        ),
    ],
    ids=["missing verdict", "unknown id", "inconclusive by rule supported", "refuted"],
)
def test_a_record_against_the_hypotheses_is_verdicts_mismatch(root, given):
    with_hypotheses(root)
    refused = failure(Source(root), {"run_id": RUN, "record": given})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_MISMATCH
    assert refused.message.startswith("record: verdicts")
    assert not eval_dir(root).exists()


def test_the_mismatch_message_names_the_broken_rule(root):
    with_hypotheses(root)
    refused = failure(
        Source(root), {"run_id": RUN, "record": record(verdict("h1", [check_entry()]))}
    )
    assert refused.message == (
        "record: verdicts: must hold a verdict for hypothesis 'h2' "
        "(hypotheses[1].id of the hypothesis record)"
    )


def test_hypotheses_of_another_run_id_are_verdicts_mismatch(root):
    path = layout.hypothesis_record(root, RUN, 1)
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps(HYPOTHESES | {"run_id": "run-b"}).encode())
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_MISMATCH
    assert refused.message.startswith("record: run_id: ")


def test_a_comparison_entry_is_comparison_not_given(root):
    with_hypotheses(root)
    given = record(
        verdict("h1", [check_entry()]),
        verdict(
            "h2",
            [
                check_entry((1, 2, 1)),
                comparison(point="sim") | {"measured": ref(1, 2, 1)},
            ],
        ),
    )
    refused = failure(Source(root), {"run_id": RUN, "record": given})
    assert refused.kind == verdicts_tool.KIND_COMPARISON_NOT_GIVEN
    assert refused.message.startswith("record.verdicts[1].evidence[1]: ")
    assert not eval_dir(root).exists()


def test_a_taken_name_is_verdicts_exist_and_the_file_is_unchanged(root):
    with_hypotheses(root)
    source = Source(root)
    write(source, {"run_id": RUN, "record": record()})
    before = verdicts_path(root).read_bytes()
    other = record(
        verdict("h1", [check_entry()], cause="another cause"),
        verdict("h2", [check_entry((1, 2, 1))]),
    )
    refused = failure(source, {"run_id": RUN, "record": other})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_EXIST
    assert refused.message == f"{VERDICTS_PATH}: is already there; nothing was replaced"
    assert verdicts_path(root).read_bytes() == before
    assert list(eval_dir(root).iterdir()) == [verdicts_path(root)]


def test_a_failed_write_is_verdicts_not_written(root, monkeypatch):
    with_hypotheses(root)

    def full(path, content):
        raise OSError(errno.ENOSPC, "No space left on device", str(path))

    monkeypatch.setattr(once_write, "write_once", full)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_NOT_WRITTEN
    assert refused.message == (
        f"{VERDICTS_PATH}: was not written: OSError: No space left on device"
    )
    assert str(root) not in refused.message
    assert not verdicts_path(root).exists()


def test_a_vanished_data_root_is_named_without_its_path(root, monkeypatch):
    with_hypotheses(root)
    real = verdicts_file.write

    def vanishing(data_root, content):
        os.rename(root, root.with_name("gone"))
        return real(data_root, content)

    monkeypatch.setattr(verdicts_file, "write", vanishing)
    refused = failure(Source(root), {"run_id": RUN, "record": record()})
    assert refused.kind == verdicts_tool.KIND_VERDICTS_NOT_WRITTEN
    assert refused.message == (
        f"{VERDICTS_PATH}: was not written: FileNotFoundError: "
        "the data root is not an existing directory"
    )


def test_the_default_registry_holds_verdicts_write(root):
    registry = default_registry(lambda: root)
    assert "verdicts.write" in registry.names()
    with_hypotheses(root)
    assert (
        tools.call(registry, "verdicts.write", {"run_id": RUN, "record": record()})
        == {}
    )
    assert verdicts_path(root).is_file()


def _mcp(request_id, method, params):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return json.dumps(document).encode() + b"\n"


def test_the_mcp_front_lists_and_serves_verdicts_write(root):
    with_hypotheses(root)
    data = b"".join(
        [
            _mcp(1, "tools/list", {}),
            _mcp(
                2,
                "tools/call",
                {
                    "name": "verdicts_write",
                    "arguments": {"run_id": RUN, "record": record()},
                },
            ),
            _mcp(
                3,
                "tools/call",
                {
                    "name": "verdicts_write",
                    "arguments": {"run_id": RUN, "record": record()},
                },
            ),
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
    listed, written, taken = (
        json.loads(line) for line in stdout.getvalue().splitlines()
    )
    names = [tool["name"] for tool in listed["result"]["tools"]]
    assert "verdicts_write" in names
    assert mcp_front.mcp_name("verdicts.write") == "verdicts_write"
    assert written["result"]["isError"] is False
    assert json.loads(written["result"]["content"][0]["text"]) == {}
    assert taken["result"]["isError"] is True
    error = json.loads(taken["result"]["content"][0]["text"])["error"]
    assert error["kind"] == "verdicts_exist"
