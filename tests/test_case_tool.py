import errno
import io
import json
import os
import shutil
from pathlib import Path

import pytest

from hilclaw import (
    case_tool,
    cases,
    cases_file,
    hypotheses_tool,
    key_records,
    keys,
    layout,
    mcp_front,
    once_write,
    run_file_tools,
    tools,
    verdicts_tool,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
STATE_PATH = f"runs/{RUN}/STATE.json"
INSTANCE_PATH = f"runs/{RUN}/instance.json"


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


def ref(round=1, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


def hypothesis(ident, candidate):
    return {
        "id": ident,
        "statement": f"{ident} lowers latency",
        "basis": [{"kind": "attempt", "ref": ref(0), "text": "the baseline"}],
        "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
        "origin": "system",
        "tested_by": [candidate],
    }


def hypotheses_document(round=1, **top):
    return {
        "schema_version": 1,
        "run_id": RUN,
        "round": round,
        "candidates": 2,
        "hypotheses": [hypothesis("h1", 1), hypothesis("h2", 2)],
    } | top


def check_entry(at=(1, 1, 1), outcome="pass"):
    return {"kind": "check", "ref": ref(*at), "point": "board", "outcome": outcome}


def verdict(ident, evidence, value="inconclusive"):
    return {
        "hypothesis": ident,
        "verdict": value,
        "cause": "as measured",
        "evidence": evidence,
    }


def supported():
    comparison = {
        "kind": "comparison",
        "metric": "latency_minimisation",
        "point": "board",
        "measured": ref(1, 1, 1),
        "against": ref(0, 1, 1),
        "difference": "lower",
    }
    evidence = [check_entry(), check_entry((0, 1, 1)), comparison]
    return verdict("h1", evidence, "supported")


def verdicts_document(*entries, round=1, **top):
    if not entries:
        entries = (supported(), verdict("h2", [check_entry((1, 2, 1), "fail")]))
    return {
        "schema_version": 1,
        "run_id": RUN,
        "round": round,
        "verdicts": list(entries),
    } | top


def state_document(round=1):
    return {
        "schema_version": 1,
        "round": round,
        "budget_spent": {"totals": {}, "position": 0, "open_steps": []},
    }


def instance_document(with_op=True):
    document = {
        "schema_version": 1,
        "hw_profile": {"key": HW_KEY.name, "record": hw()},
    }
    if with_op:
        document["op_signature"] = {"key": OP_KEY.name, "record": op()}
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
    return directory


def state_path(root):
    return layout.run_file(root, RUN, "STATE.json")


def instance_path(root):
    return layout.run_file(root, RUN, "instance.json")


def hypotheses_path(root, round=1):
    return layout.hypothesis_record(root, RUN, round)


def verdicts_path(root, round=1):
    return layout.verdict_record(root, RUN, round)


def case_path(root, round=1):
    return layout.case_record(root, HW_KEY.name, OP_KEY.name, RUN, round)


def store_key(root, hw_only=False):
    key_records.store_hw_profile(root, hw())
    if not hw_only:
        key_records.store_op_signature(root, HW_KEY.name, op())


def run(
    root,
    round=1,
    state=True,
    instance=True,
    key=True,
    hypotheses=True,
    verdicts=True,
):
    if state:
        place(state_path(root), encoded(state_document(round)))
    if instance:
        place(instance_path(root), encoded(instance_document()))
    if key:
        store_key(root)
    if hypotheses:
        place(hypotheses_path(root, round), encoded(hypotheses_document(round)))
    if verdicts:
        place(verdicts_path(root, round), encoded(verdicts_document(round=round)))


def request(round=1, **changes):
    return {"run_id": RUN, "round": round} | changes


def write(source, body):
    return case_tool.definition(source).function(body)


def tree(root):
    found = {}
    for directory, names, files in os.walk(root):
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
        write(source or Source(root), request() if body is None else body)
    assert tree(root) == before
    return failure.value


# The definition


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = case_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == case_tool.NAME == "case.write"
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
    assert case_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError):
        case_tool.definition(source)


KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_invalid",
    "run_file_unsupported",
    "run_file_unreadable",
    "round_not_current",
    "key_not_stored",
    "key_record_invalid",
    "key_record_unreadable",
    "hypotheses_missing",
    "hypotheses_invalid",
    "hypotheses_unsupported",
    "hypotheses_unreadable",
    "verdicts_invalid",
    "verdicts_unsupported",
    "verdicts_unreadable",
    "verdicts_mismatch",
    "case_exists",
    "case_not_written",
)


def test_the_description_names_every_kind_in_order():
    description = case_tool.definition(lambda: None).description
    places = [description.index(kind) for kind in KINDS]
    assert places == sorted(places)
    assert '{"with_verdicts": true or false}' in description
    assert "never part of the request" in description
    assert "right before the write that ends the round" in description


def test_the_kinds_are_those_of_the_record():
    assert (
        case_tool.KIND_ROUND_NOT_CURRENT,
        case_tool.KIND_KEY_NOT_STORED,
        case_tool.KIND_KEY_RECORD_INVALID,
        case_tool.KIND_KEY_RECORD_UNREADABLE,
        case_tool.KIND_VERDICTS_INVALID,
        case_tool.KIND_VERDICTS_UNSUPPORTED,
        case_tool.KIND_VERDICTS_UNREADABLE,
        case_tool.KIND_CASE_EXISTS,
        case_tool.KIND_CASE_NOT_WRITTEN,
    ) == (
        "round_not_current",
        "key_not_stored",
        "key_record_invalid",
        "key_record_unreadable",
        "verdicts_invalid",
        "verdicts_unsupported",
        "verdicts_unreadable",
        "case_exists",
        "case_not_written",
    )
    assert case_tool.KIND_HYPOTHESES_MISSING is hypotheses_tool.KIND_HYPOTHESES_MISSING
    assert case_tool.KIND_HYPOTHESES_INVALID is hypotheses_tool.KIND_HYPOTHESES_INVALID
    assert (
        case_tool.KIND_HYPOTHESES_UNSUPPORTED
        is hypotheses_tool.KIND_HYPOTHESES_UNSUPPORTED
    )
    assert (
        case_tool.KIND_HYPOTHESES_UNREADABLE
        is hypotheses_tool.KIND_HYPOTHESES_UNREADABLE
    )
    assert case_tool.KIND_VERDICTS_MISMATCH is verdicts_tool.KIND_VERDICTS_MISMATCH


# Happy paths (ADR-0133 Walk-through)


def stored(root, round=1):
    content = case_path(root, round).read_bytes()
    return content, cases_file.parse(content)


def test_a_round_with_hypotheses_and_verdicts_is_stored_with_both(root):
    run(root)
    source = Source(root)
    sources = {
        path: path.read_bytes()
        for path in (
            state_path(root),
            instance_path(root),
            hypotheses_path(root),
            verdicts_path(root),
        )
    }
    assert write(source, request()) == {"with_verdicts": True}
    assert source.calls == 1
    content, document = stored(root)
    assert document["hypothesis_record"] == json.loads(sources[hypotheses_path(root)])
    assert document["verdict_record"] == json.loads(sources[verdicts_path(root)])
    assert (document["run_id"], document["round"]) == (RUN, 1)
    case = cases.build(hypotheses_document(), verdicts_document())
    text = json.dumps(case, ensure_ascii=False, indent=2, allow_nan=False)
    assert content == (text + "\n").encode("utf-8")
    assert all(path.read_bytes() == data for path, data in sources.items())
    assert not layout.run_file(root, RUN, "events.ndjson").exists()


def test_a_round_whose_verdicts_are_all_inconclusive_keeps_them(root):
    run(root, verdicts=False)
    document = verdicts_document(
        verdict("h1", [check_entry()]),
        verdict("h2", [check_entry((1, 2, 1), "fail")]),
    )
    place(verdicts_path(root), encoded(document))
    assert write(Source(root), request()) == {"with_verdicts": True}
    copied = stored(root)[1]["verdict_record"]
    assert copied == document
    assert {entry["verdict"] for entry in copied["verdicts"]} == {"inconclusive"}


def test_a_round_without_verdicts_is_stored_without_them(root):
    run(root, round=3, verdicts=False)
    assert write(Source(root), request(3)) == {"with_verdicts": False}
    document = stored(root, 3)[1]
    assert "verdict_record" not in document
    assert document["hypothesis_record"] == hypotheses_document(3)
    assert case_path(root, 3).name == f"case-{RUN}-0003.json"


def test_non_ascii_text_is_written_as_utf_8(root):
    run(root, hypotheses=False, verdicts=False)
    document = hypotheses_document(note="한글 é")
    place(hypotheses_path(root), encoded(document))
    write(Source(root), request())
    content, parsed = stored(root)
    assert "한글 é".encode() in content
    assert parsed["hypothesis_record"]["note"] == "한글 é"


def test_the_tool_answers_through_the_registry_and_the_mcp_front(root):
    run(root)
    registry = default_registry(Source(root))
    assert tools.call(registry, "case.write", request()) == {"with_verdicts": True}
    assert mcp_front.mcp_names(registry)["case_write"] == "case.write"


def test_the_tool_answers_by_its_mcp_name(root):
    run(root)
    params = {"name": "case_write", "arguments": request()}
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
    assert json.loads(result["content"][0]["text"]) == {"with_verdicts": True}
    assert case_path(root).is_file()


# Negative requests


@pytest.mark.parametrize(
    "body",
    [
        request(extra=1),
        {"run_id": RUN},
        {"round": 1},
        {},
        request(run_id="Bad Run"),
        request(run_id=3),
        request(0),
        request(-1),
        request(True),
        request(1.0),
        request("1"),
        request(None),
        request(keys.MAX_INTEGER + 1),
    ],
)
def test_a_request_that_is_not_exactly_run_id_and_round_is_invalid(root, body):
    run(root)
    source = Source(root)
    failure = refused(root, body, source)
    assert failure.kind == "invalid_request"
    assert source.calls == 0


def test_round_zero_is_refused_with_its_reason(root):
    failure = refused(root, request(0))
    assert "round 0 has no case" in failure.message


def test_the_largest_round_is_accepted_by_the_request(root):
    failure = refused(root, request(keys.MAX_INTEGER))
    assert failure.kind == "run_file_missing"


# Every kind, in order


def test_no_data_root(root):
    run(root)
    source = FailingSource()
    assert refused(root, source=source).kind == "no_data_root"
    assert source.calls == 1


def test_a_missing_state_is_run_file_missing(root):
    run(root, state=False)
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(STATE_PATH)


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{not json", "run_file_invalid"),
        (b"", "run_file_invalid"),
        (encoded(state_document() | {"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_a_state_that_cannot_be_used_is_its_kind(root, content, kind):
    run(root, state=False)
    place(state_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(STATE_PATH)


def test_a_directory_in_the_place_of_state_is_run_file_invalid(root):
    run(root, state=False)
    state_path(root).mkdir(parents=True)
    failure = refused(root)
    assert failure.kind == "run_file_invalid"
    assert failure.message == f"{STATE_PATH}: is not a regular file"


def failing_read(monkeypatch, name, error=None):
    original = Path.read_bytes

    def read_bytes(self):
        if self.name == name:
            raise error or PermissionError(errno.EACCES, "denied", str(self))
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)


def test_an_unreadable_state_is_run_file_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "STATE.json")
    failure = refused(root)
    assert failure.kind == "run_file_unreadable"
    assert (
        failure.message == f"{STATE_PATH}: could not be read: PermissionError: denied"
    )


@pytest.mark.parametrize("state_round", [2, 0])
def test_a_round_other_than_the_one_in_progress_is_round_not_current(root, state_round):
    run(root)
    place(state_path(root), encoded(state_document(state_round)))
    failure = refused(root)
    assert failure.kind == "round_not_current"
    assert failure.message == (
        f"{STATE_PATH}: names round {state_round} as in progress, not the "
        "request's round 1"
    )


def test_a_missing_instance_is_run_file_missing(root):
    run(root, instance=False)
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(INSTANCE_PATH)


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"[]", "run_file_invalid"),
        (encoded(instance_document() | {"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_an_instance_that_cannot_be_used_is_its_kind(root, content, kind):
    run(root, instance=False)
    place(instance_path(root), content)
    failure = refused(root)
    assert failure.kind == kind
    assert failure.message.startswith(INSTANCE_PATH)


def test_an_unreadable_instance_is_run_file_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "instance.json")
    failure = refused(root)
    assert failure.kind == "run_file_unreadable"
    assert failure.message.startswith(INSTANCE_PATH)


def test_an_instance_without_op_signature_is_key_not_stored(root):
    run(root, instance=False)
    place(instance_path(root), encoded(instance_document(with_op=False)))
    failure = refused(root)
    assert failure.kind == "key_not_stored"
    assert failure.message.startswith(f"{INSTANCE_PATH}: states no op_signature")


@pytest.mark.parametrize("stored_key", ["none", "hw_only", "no_op_record"])
def test_a_key_that_is_not_stored_is_key_not_stored_and_creates_nothing(
    root, stored_key
):
    run(root, key=False)
    if stored_key == "hw_only":
        store_key(root, hw_only=True)
    elif stored_key == "no_op_record":
        store_key(root, hw_only=True)
        (root / KEY_DIR).mkdir()
    failure = refused(root)
    assert failure.kind == "key_not_stored"
    assert failure.message.startswith(f"{KEY_DIR}: the key is not stored")
    if stored_key == "none":
        assert not (root / "db").exists()
    elif stored_key == "hw_only":
        assert not (root / KEY_DIR).exists()


@pytest.mark.parametrize(
    ("record", "content"),
    [
        ("hw_profile.json", b"{not json"),
        ("op_signature.json", b"{not json"),
        ("op_signature.json", encoded(op(dtype="other_dtype"))),
        ("hw_profile.json", encoded(hw(revision="synthetic-r2"))),
    ],
)
def test_an_invalid_or_colliding_key_record_is_key_record_invalid(
    root, record, content
):
    run(root)
    path = (
        (root / KEY_DIR).parent / record
        if record == "hw_profile.json"
        else (root / KEY_DIR / record)
    )
    path.write_bytes(content)
    failure = refused(root)
    assert failure.kind == "key_record_invalid"
    assert failure.message.startswith(path.relative_to(root).as_posix())


def test_an_unreadable_key_record_is_key_record_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "op_signature.json")
    failure = refused(root)
    assert failure.kind == "key_record_unreadable"
    assert failure.message == (
        f"{KEY_DIR}: the key records could not be read: PermissionError: denied"
    )


def test_a_data_root_gone_before_the_key_is_key_record_unreadable(
    root, tmp_path, monkeypatch
):
    run(root)
    original = run_file_tools.read
    moved = tmp_path / "moved"

    def read(data_root, run_id, name):
        result = original(data_root, run_id, name)
        if name == "instance.json":
            shutil.move(root, moved)
        return result

    monkeypatch.setattr(run_file_tools, "read", read)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root), request())
    assert failure.value.kind == "key_record_unreadable"
    assert failure.value.message == (
        f"{KEY_DIR}: the key records could not be read: FileNotFoundError: "
        "the data root is not an existing directory"
    )
    assert not list(moved.rglob("case-*"))


def test_a_missing_hypothesis_record_is_hypotheses_missing(root):
    run(root, hypotheses=False)
    failure = refused(root)
    assert failure.kind == "hypotheses_missing"
    assert failure.message.startswith(f"runs/{RUN}/rounds/0001/decision/")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        (
            {"run_id": "run-b"},
            "run_id: must be the request's run_id 'run-a', got 'run-b'",
        ),
        ({"round": 2}, "round: must be the request's round 1, got 2"),
    ],
)
def test_a_hypothesis_record_of_another_run_or_round_is_hypotheses_invalid(
    root, changes, message
):
    run(root, hypotheses=False, verdicts=False)
    place(hypotheses_path(root), encoded(hypotheses_document(**changes)))
    failure = refused(root)
    assert failure.kind == "hypotheses_invalid"
    file = hypotheses_path(root).relative_to(root).as_posix()
    assert failure.message == f"{file}: {message}"


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{not json", "hypotheses_invalid"),
        (encoded(hypotheses_document(schema_version=2)), "hypotheses_unsupported"),
    ],
)
def test_a_hypothesis_record_that_cannot_be_used_is_its_kind(root, content, kind):
    run(root, hypotheses=False)
    place(hypotheses_path(root), content)
    assert refused(root).kind == kind


def test_an_unreadable_hypothesis_record_is_hypotheses_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "hypotheses.json")
    assert refused(root).kind == "hypotheses_unreadable"


VERDICTS_FILE = f"runs/{RUN}/rounds/0001/eval/verdicts.json"


@pytest.mark.parametrize(
    "content",
    [
        b"{not json",
        b"",
        encoded(verdicts_document(run_id="Run B")),
        encoded(verdicts_document(round=0)),
    ],
)
def test_an_invalid_verdicts_file_is_verdicts_invalid(root, content):
    run(root, verdicts=False)
    place(verdicts_path(root), content)
    failure = refused(root)
    assert failure.kind == "verdicts_invalid"
    assert failure.message.startswith(f"{VERDICTS_FILE}: ")


def test_a_directory_in_the_place_of_verdicts_is_verdicts_invalid(root):
    run(root, verdicts=False)
    verdicts_path(root).mkdir(parents=True)
    failure = refused(root)
    assert failure.kind == "verdicts_invalid"
    assert failure.message == f"{VERDICTS_FILE}: is not a regular file"


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"round": 2}, "round: must be the request's round 1, got 2"),
        (
            {"run_id": "run-b"},
            "run_id: must be the request's run_id 'run-a', got 'run-b'",
        ),
    ],
)
def test_verdicts_of_another_round_or_run_are_verdicts_invalid(root, changes, message):
    run(root, verdicts=False)
    document = verdicts_document(
        verdict("h1", [check_entry()]),
        verdict("h2", [check_entry((1, 2, 1), "fail")]),
    )
    place(verdicts_path(root), encoded(document | changes))
    failure = refused(root)
    assert failure.kind == "verdicts_invalid"
    assert failure.message == f"{VERDICTS_FILE}: {message}"


def test_verdicts_of_another_version_are_verdicts_unsupported(root):
    run(root, verdicts=False)
    place(verdicts_path(root), encoded(verdicts_document(schema_version=2)))
    failure = refused(root)
    assert failure.kind == "verdicts_unsupported"
    assert failure.message == f"{VERDICTS_FILE}: schema_version: is 2, not 1"


def test_unreadable_verdicts_are_verdicts_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "verdicts.json")
    failure = refused(root)
    assert failure.kind == "verdicts_unreadable"
    assert failure.message == (
        f"{VERDICTS_FILE}: could not be read: PermissionError: denied"
    )


def test_verdicts_that_cannot_be_looked_at_are_verdicts_unreadable(root, monkeypatch):
    run(root)
    original = os.lstat

    def lstat(path, *args, **kwargs):
        if Path(path).name == "verdicts.json":
            raise PermissionError(errno.EACCES, "denied", str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", lstat)
    failure = refused(root)
    assert failure.kind == "verdicts_unreadable"
    assert failure.message.startswith(f"{VERDICTS_FILE}: could not be read")


def test_verdicts_that_break_a_rule_against_the_hypotheses_are_verdicts_mismatch(
    root,
):
    run(root, verdicts=False)
    place(verdicts_path(root), encoded(verdicts_document(supported())))
    failure = refused(root)
    assert failure.kind == "verdicts_mismatch"
    assert failure.message.startswith(f"{VERDICTS_FILE}: verdicts: must hold")


def test_a_wrong_verdict_value_is_verdicts_mismatch(root):
    run(root, verdicts=False)
    wrong = supported() | {"verdict": "inconclusive"}
    document = verdicts_document(wrong, verdict("h2", [check_entry((1, 2, 1))]))
    place(verdicts_path(root), encoded(document))
    failure = refused(root)
    assert failure.kind == "verdicts_mismatch"
    assert failure.message.startswith(f"{VERDICTS_FILE}: verdicts[0].verdict: ")


def test_a_second_call_is_case_exists_and_replaces_nothing(root):
    run(root)
    write(Source(root), request())
    first = case_path(root).read_bytes()
    failure = refused(root)
    assert failure.kind == "case_exists"
    file = case_path(root).relative_to(root).as_posix()
    assert failure.message == f"{file}: is already there; nothing was replaced"
    assert case_path(root).read_bytes() == first


def test_a_failing_step_of_the_write_is_case_not_written(root, monkeypatch):
    run(root)

    def write_once(path, content):
        raise OSError(errno.EIO, "input/output error", str(path))

    monkeypatch.setattr(once_write, "write_once", write_once)
    failure = refused(root)
    assert failure.kind == "case_not_written"
    file = case_path(root).relative_to(root).as_posix()
    assert failure.message == (f"{file}: was not written: OSError: input/output error")
    assert str(root) not in failure.message


def test_a_key_directory_gone_since_the_lookup_is_case_not_written(root, monkeypatch):
    run(root)
    original = key_records.lookup

    def lookup(data_root, hw_record, op_record):
        found = original(data_root, hw_record, op_record)
        shutil.rmtree(root / KEY_DIR)
        return found

    monkeypatch.setattr(key_records, "lookup", lookup)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root), request())
    assert failure.value.kind == "case_not_written"
    assert failure.value.message.endswith(
        "was not written: FileNotFoundError: "
        "the key directory is not an existing directory"
    )
    assert not (root / KEY_DIR).exists()


def test_a_data_root_gone_before_the_write_is_said_in_case_not_written(
    root, tmp_path, monkeypatch
):
    run(root)
    moved = tmp_path / "moved"
    original = cases.build

    def build(hypotheses, verdicts=None):
        shutil.move(root, moved)
        return original(hypotheses, verdicts)

    monkeypatch.setattr(cases, "build", build)
    with pytest.raises(ToolFailure) as failure:
        write(Source(root), request())
    assert failure.value.kind == "case_not_written"
    assert failure.value.message.endswith(
        "FileNotFoundError: the data root is not an existing directory"
    )


# Order: the earlier check decides


def test_invalid_request_comes_before_no_data_root(root):
    source = FailingSource()
    assert refused(root, request(0), source).kind == "invalid_request"
    assert source.calls == 0


def test_round_not_current_comes_before_key_not_stored(root):
    run(root, key=False)
    place(state_path(root), encoded(state_document(2)))
    assert refused(root).kind == "round_not_current"


def test_key_not_stored_comes_before_hypotheses_missing(root):
    run(root, key=False, hypotheses=False)
    assert refused(root).kind == "key_not_stored"
    assert not (root / "db").exists()


def test_run_file_missing_of_state_comes_before_that_of_instance(root):
    failure = refused(root)
    assert failure.kind == "run_file_missing"
    assert failure.message.startswith(STATE_PATH)


def test_hypotheses_invalid_comes_before_verdicts_invalid(root):
    run(root, hypotheses=False, verdicts=False)
    place(hypotheses_path(root), b"{not json")
    place(verdicts_path(root), b"{not json")
    assert refused(root).kind == "hypotheses_invalid"


# The encoding edge, not decided by the record (AC 5)


@pytest.mark.parametrize(
    "extra",
    [b'"wide": 1e999', b'"text": "\\ud800"'],
)
def test_content_that_cannot_be_encoded_crashes_and_writes_nothing(root, extra):
    run(root, hypotheses=False)
    text = encoded(hypotheses_document()).rstrip()[:-1].rstrip()
    place(hypotheses_path(root), text + b",\n  " + extra + b"\n}\n")
    with pytest.raises(ValueError):
        write(Source(root), request())
    registry = default_registry(Source(root))
    before = tree(root)
    with pytest.raises(ToolFailure) as failure:
        tools.call(registry, "case.write", request())
    assert failure.value.kind == "tool_crashed"
    assert tree(root) == before
    assert not case_path(root).exists()


def test_an_invalid_case_error_of_the_build_is_not_mapped(root, monkeypatch):
    run(root)

    def build(hypotheses, verdicts=None):
        raise cases.InvalidCaseError("case: synthetic")

    monkeypatch.setattr(cases, "build", build)
    with pytest.raises(ToolFailure) as failure:
        tools.call(default_registry(Source(root)), "case.write", request())
    assert failure.value.kind == "tool_crashed"
    assert not case_path(root).exists()


# Nothing created, nothing journaled


def test_a_refusal_leaves_every_source_file_unchanged(root):
    run(root)
    place(state_path(root), encoded(state_document(2)))
    sources = [state_path(root), instance_path(root), hypotheses_path(root)]
    sources.append(verdicts_path(root))
    before = [path.read_bytes() for path in sources]
    refused(root)
    assert [path.read_bytes() for path in sources] == before
    assert not layout.run_file(root, RUN, "events.ndjson").exists()


def test_a_written_case_is_the_only_new_entry(root):
    run(root)
    before = tree(root)
    write(Source(root), request())
    after = tree(root)
    case = case_path(root).relative_to(root).as_posix()
    assert set(after) - set(before) == {case}
    assert {k: v for k, v in after.items() if k != case} == before


def test_each_call_asks_the_source_once(root):
    run(root, key=False)
    source = Source(root)
    with pytest.raises(ToolFailure):
        write(source, request())
    assert source.calls == 1


# The shared read of run_file_tools


def test_the_shared_read_returns_the_parsed_file_and_its_bytes(root):
    run(root)
    state, content = run_file_tools.read(root, RUN, "STATE.json")
    assert state.round == 1
    assert content == state_path(root).read_bytes()
    stated, _ = run_file_tools.read(root, RUN, "instance.json")
    assert stated.op_signature.key == OP_KEY.name


def test_the_shared_read_refuses_another_name(root):
    with pytest.raises(ValueError):
        run_file_tools.read(root, RUN, "events.ndjson")
    with pytest.raises(layout.InvalidPathValueError):
        run_file_tools.read(root, "Bad Run", "STATE.json")
