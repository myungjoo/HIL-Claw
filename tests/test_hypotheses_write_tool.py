import copy
import errno
import io
import json
import os
from pathlib import Path

import pytest

from hilclaw import (
    case_lookup,
    case_tool,
    cases,
    cases_file,
    events,
    hypotheses_file,
    hypotheses_tool,
    hypotheses_write_tool,
    key_records,
    keys,
    layout,
    mcp_front,
    once_write,
    run_file_tools,
    tools,
)
from hilclaw.tools import ToolDefinition, ToolFailure, default_registry

RUN = "run-a"
OTHER = "other-run_02"
STATE_PATH = f"runs/{RUN}/STATE.json"
INSTANCE_PATH = f"runs/{RUN}/instance.json"
HYPOTHESES_PATH = f"runs/{RUN}/rounds/0001/decision/hypotheses.json"
KINDS = (
    "invalid_request",
    "no_data_root",
    "run_file_missing",
    "run_file_invalid",
    "run_file_unsupported",
    "run_file_unreadable",
    "round_not_current",
    "cases_unreadable",
    "cases_mismatch",
    "hypotheses_exist",
    "hypotheses_not_written",
)


def hw():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_hw",
        "revision": "synthetic-r1",
        "toolchain": {"synthetic_cc": "0.0-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }


def op():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 2, "k": 3, "n": 5},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }


HW_KEY = keys.hw_profile_key(hw())
OP_KEY = keys.op_signature_key(op())
KEY_DIR = f"db/{HW_KEY.name}/{OP_KEY.name}"


def hypothesis(ident="h1", candidate=1, basis=None, **changes):
    return {
        "id": ident,
        "statement": f"{ident} lowers latency",
        "basis": basis
        or [
            {
                "kind": "attempt",
                "ref": {"round": 0, "candidate": 1, "attempt": 1},
                "text": "the baseline",
            }
        ],
        "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
        "origin": "system",
        "tested_by": [candidate],
    } | changes


def record(*entries, run_id=RUN, round=1, **top):
    return {
        "schema_version": 1,
        "run_id": run_id,
        "round": round,
        "candidates": 1,
        "hypotheses": list(entries) or [hypothesis()],
    } | top


def case_basis(run_id=OTHER, round=1, ident="h1"):
    case = {"run_id": run_id, "round": round, "hypothesis": ident}
    return {"kind": "case", "case": case, "text": "a stored case"}


def citing(ident="h1", read=((OTHER, 1),)):
    return record(
        hypothesis(basis=[case_basis(ident=ident)]),
        cases_read=[{"run_id": run_id, "round": round} for run_id, round in read],
    )


def encoded(document):
    return (json.dumps(document, indent=2) + "\n").encode()


def place(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


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


def run(root, state_round=1, instance=True, with_op=True):
    place(state_path(root), encoded(state_document(state_round)))
    if instance:
        place(instance_path(root), encoded(instance_document(with_op)))


def store_case(root, run_id=OTHER, round=1, ids=("h1",)):
    key_records.store_hw_profile(root, hw())
    key_records.store_op_signature(root, HW_KEY.name, op())
    stored = record(*(hypothesis(ident) for ident in ids), run_id=run_id, round=round)
    content = encoded(cases.build(stored))
    cases_file.write(root, HW_KEY.name, OP_KEY.name, content)


def _content(path):
    with open(path, "rb") as file:
        return file.read()


def tree(root):
    found = {}
    for directory, names, files in os.walk(root):
        for name in names + files:
            path = Path(directory) / name
            found[path.relative_to(root).as_posix()] = (
                _content(path) if path.is_file() else None
            )
    return found


def write(source, request):
    return hypotheses_write_tool.definition(source).function(request)


def failure(source, request):
    with pytest.raises(ToolFailure) as refused:
        write(source, request)
    return refused.value


def refused(root, document=None, request=None):
    before = tree(root)
    error = failure(Source(root), request or {"run_id": RUN, "record": document})
    assert tree(root) == before
    return error


def fixed_bytes(document):
    text = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    return (text + "\n").encode("utf-8")


def test_the_definition_is_bound_to_the_source_and_does_not_call_it(root):
    source = Source(root)
    definition = hypotheses_write_tool.definition(source)
    assert type(definition) is ToolDefinition
    assert definition.name == hypotheses_write_tool.NAME == "hypotheses.write"
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
    assert hypotheses_write_tool.definition(source).input_schema["properties"]


@pytest.mark.parametrize("source", [None, "data", 3, Path(".")])
def test_a_source_that_is_not_callable_is_refused(source):
    with pytest.raises(TypeError):
        hypotheses_write_tool.definition(source)


def test_the_description_names_every_kind_in_order():
    description = hypotheses_write_tool.definition(lambda: None).description
    places = [description.index(kind) for kind in KINDS]
    assert places == sorted(places)
    assert "decision/hypotheses.json" in description
    assert "never part of the request" in description
    assert "corrected and sent again" in description
    assert "Only for a record whose cases_read holds an entry" in description


def test_the_kinds_of_the_module():
    kinds = {
        value
        for name, value in vars(hypotheses_write_tool).items()
        if name.startswith("KIND_")
    }
    assert kinds == {
        "round_not_current",
        "cases_unreadable",
        "cases_mismatch",
        "hypotheses_exist",
        "hypotheses_not_written",
    }
    assert not kinds & tools.RESERVED_KINDS
    assert hypotheses_write_tool.KIND_ROUND_NOT_CURRENT == (
        case_tool.KIND_ROUND_NOT_CURRENT
    )
    read_kinds = {
        value
        for name, value in vars(hypotheses_tool).items()
        if name.startswith("KIND_")
    }
    assert not kinds & read_kinds


def test_a_valid_record_is_written_by_the_fixed_encoding(root):
    run(root)
    source = Source(root)
    given = record(note={"키": "값 — é \U0001f600"})
    sent = copy.deepcopy(given)
    assert write(source, {"run_id": RUN, "record": sent}) == {}
    assert source.calls == 1
    assert sent == given
    content = hypotheses_path(root).read_bytes()
    assert content == fixed_bytes(given)
    assert content.endswith(b"}\n")
    assert not content.startswith(b"\xef\xbb\xbf")
    assert hypotheses_file.parse(content) == given
    directory = hypotheses_path(root).parent
    assert list(directory.iterdir()) == [hypotheses_path(root)]


def test_the_members_are_written_in_the_order_given_without_a_carriage_return(root):
    run(root)
    given = record(hypothesis(statement="one\r\ntwo\rthree"))
    reordered = dict(reversed(list(given.items())))
    write(Source(root), {"run_id": RUN, "record": reordered})
    content = hypotheses_path(root).read_bytes()
    assert b"\r" not in content
    assert list(json.loads(content)) == list(reordered)


def test_an_injected_entry_is_admitted(root):
    run(root)
    given = record(
        hypothesis(),
        hypothesis("h2", origin="injected", injection="u1"),
    )
    assert write(Source(root), {"run_id": RUN, "record": given}) == {}
    assert hypotheses_file.parse(hypotheses_path(root).read_bytes()) == given


def test_an_injected_entry_without_its_injection_is_invalid_request(root):
    run(root)
    error = refused(root, record(hypothesis(origin="injected")))
    assert error.kind == "invalid_request"
    assert "injection" in error.message


def bad_requests():
    no_version = record()
    del no_version["schema_version"]
    untested = record(candidates=2)
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
        ("not a number", {"run_id": RUN, "record": record(note=float("nan"))}),
        ("lone surrogate", {"run_id": RUN, "record": record(note="\ud800")}),
        ("no schema_version", {"run_id": RUN, "record": no_version}),
        ("an untested candidate", {"run_id": RUN, "record": untested}),
        ("round 0", {"run_id": RUN, "record": record(round=0)}),
        ("other schema_version", {"run_id": RUN, "record": record(schema_version=2)}),
        ("run_id mismatch", {"run_id": RUN, "record": record(run_id="run-b")}),
    ]


@pytest.mark.parametrize(
    "request_",
    [case for _, case in bad_requests()],
    ids=[label for label, _ in bad_requests()],
)
def test_a_refused_request_or_record_asks_no_source_and_creates_nothing(root, request_):
    run(root)
    source = Source(root)
    before = tree(root)
    error = failure(source, request_)
    assert error.kind == tools.KIND_INVALID_REQUEST
    assert source.calls == 0
    assert tree(root) == before


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
    nan = failure(source, {"run_id": RUN, "record": record(note=float("nan"))})
    assert nan.message.startswith("record: cannot be encoded as UTF-8 JSON text: ")
    zero = failure(source, {"run_id": RUN, "record": record(round=0)})
    assert zero.message.startswith("record: round: ")
    assert source.calls == 0


def test_a_failing_source_is_no_data_root(root):
    run(root)
    source = FailingSource()
    before = tree(root)
    error = failure(source, {"run_id": RUN, "record": record()})
    assert error.kind == tools.KIND_NO_DATA_ROOT
    assert source.calls == 1
    assert tree(root) == before


def test_a_missing_state_is_run_file_missing(root):
    error = refused(root, record())
    assert error.kind == "run_file_missing"
    assert error.message.startswith(STATE_PATH)
    assert not (root / "runs").exists()


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"{not json", "run_file_invalid"),
        (encoded(state_document() | {"schema_version": 2}), "run_file_unsupported"),
    ],
)
def test_a_state_that_cannot_be_used_is_its_kind(root, content, kind):
    place(state_path(root), content)
    error = refused(root, record())
    assert error.kind == kind
    assert error.message.startswith(STATE_PATH)


def test_a_directory_in_the_place_of_state_is_run_file_invalid(root):
    state_path(root).mkdir(parents=True)
    error = refused(root, record())
    assert error.kind == "run_file_invalid"
    assert error.message == f"{STATE_PATH}: is not a regular file"


def failing_read(monkeypatch, name):
    original = Path.read_bytes

    def read_bytes(self):
        if self.name == name:
            raise PermissionError(errno.EACCES, "denied", str(self))
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)


def test_an_unreadable_state_is_run_file_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "STATE.json")
    error = refused(root, record())
    assert error.kind == "run_file_unreadable"
    assert error.message == f"{STATE_PATH}: could not be read: PermissionError: denied"


@pytest.mark.parametrize("state_round", [2, 0])
def test_a_record_of_another_round_is_round_not_current(root, state_round):
    run(root, state_round)
    error = refused(root, record())
    assert error.kind == hypotheses_write_tool.KIND_ROUND_NOT_CURRENT
    assert error.message == (
        f"{STATE_PATH}: names round {state_round} as in progress, not the "
        "record's round 1"
    )


@pytest.mark.parametrize("cases_read", [None, []])
def test_check_4_is_skipped_without_cases_read(root, monkeypatch, cases_read):
    run(root, instance=False)
    given = record() if cases_read is None else record(cases_read=cases_read)
    monkeypatch.setattr(case_lookup, "find", None)
    assert write(Source(root), {"run_id": RUN, "record": given}) == {}
    assert not (root / "db").exists()
    assert not instance_path(root).exists()


def test_a_record_citing_a_stored_case_is_written(root):
    run(root)
    store_case(root, ids=("h1", "h3"))
    given = citing("h3")
    assert write(Source(root), {"run_id": RUN, "record": given}) == {}
    assert hypotheses_path(root).read_bytes() == fixed_bytes(given)


def test_the_reports_of_the_lookup_are_not_judged(root):
    run(root)
    store_case(root)
    place(root / KEY_DIR / "case-broken.json", b"{not json")
    found = case_lookup.lookup(root, RUN)
    assert found.reports
    assert write(Source(root), {"run_id": RUN, "record": citing()}) == {}


def test_cases_read_naming_no_stored_case_is_cases_mismatch(root):
    run(root)
    store_case(root)
    error = refused(root, citing(read=((OTHER, 1), (OTHER, 2))))
    assert error.kind == hypotheses_write_tool.KIND_CASES_MISMATCH
    assert error.message.startswith("record: cases_read[1]: ")


def test_a_case_basis_naming_an_id_the_case_does_not_hold_is_cases_mismatch(root):
    run(root)
    store_case(root)
    error = refused(root, citing("h9"))
    assert error.kind == "cases_mismatch"
    assert error.message.startswith("record: hypotheses[0].basis[0].case.hypothesis: ")


def test_a_run_without_a_key_has_no_case_to_cite(root):
    run(root, with_op=False)
    error = refused(root, citing())
    assert error.kind == "cases_mismatch"


def test_a_missing_instance_is_run_file_missing(root):
    run(root, instance=False)
    error = refused(root, citing())
    assert error.kind == "run_file_missing"
    assert error.message.startswith(INSTANCE_PATH)


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
    error = refused(root, citing())
    assert error.kind == kind
    assert error.message.startswith(INSTANCE_PATH)


def test_an_unreadable_instance_is_run_file_unreadable(root, monkeypatch):
    run(root)
    failing_read(monkeypatch, "instance.json")
    error = refused(root, citing())
    assert error.kind == "run_file_unreadable"
    assert error.message.startswith(INSTANCE_PATH)


def test_a_failing_listing_of_the_key_is_cases_unreadable(root, monkeypatch):
    run(root)
    store_case(root)

    def denied(path):
        raise PermissionError(errno.EACCES, "denied", str(path))

    monkeypatch.setattr(os, "listdir", denied)
    error = refused(root, citing())
    assert error.kind == hypotheses_write_tool.KIND_CASES_UNREADABLE
    assert error.message == (
        f"{KEY_DIR}: the cases of the run's key could not be read: "
        "PermissionError: denied"
    )
    assert str(root) not in error.message


@pytest.mark.parametrize(
    ("with_op", "where"), [(True, KEY_DIR), (False, INSTANCE_PATH)]
)
def test_a_data_root_gone_before_the_lookup_is_cases_unreadable(
    root, monkeypatch, with_op, where
):
    run(root, with_op=with_op)
    original = run_file_tools.read

    def read(data_root, run_id, name):
        result = original(data_root, run_id, name)
        if name == "instance.json":
            os.rename(root, root.with_name("gone"))
        return result

    monkeypatch.setattr(run_file_tools, "read", read)
    error = failure(Source(root), {"run_id": RUN, "record": citing()})
    assert error.kind == "cases_unreadable"
    assert error.message == (
        f"{where}: the cases of the run's key could not be read: "
        "FileNotFoundError: the data root is not an existing directory"
    )


def test_a_taken_name_is_hypotheses_exist_and_the_file_is_unchanged(root):
    run(root)
    source = Source(root)
    write(source, {"run_id": RUN, "record": record()})
    before = tree(root)
    other = record(hypothesis(statement="another statement"))
    error = failure(source, {"run_id": RUN, "record": other})
    assert error.kind == hypotheses_write_tool.KIND_HYPOTHESES_EXIST
    assert error.message == f"{HYPOTHESES_PATH}: is already there; nothing was replaced"
    assert tree(root) == before


def test_a_taken_name_is_not_read(root, monkeypatch):
    run(root)
    place(hypotheses_path(root), b"not a record")
    original = Path.read_bytes

    def read_bytes(self):
        assert self.name != "hypotheses.json"
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    error = failure(Source(root), {"run_id": RUN, "record": record()})
    assert error.kind == "hypotheses_exist"


def test_a_failed_write_is_hypotheses_not_written(root, monkeypatch):
    run(root)

    def full(path, content):
        raise OSError(errno.ENOSPC, "No space left on device", str(path))

    monkeypatch.setattr(once_write, "write_once", full)
    error = failure(Source(root), {"run_id": RUN, "record": record()})
    assert error.kind == hypotheses_write_tool.KIND_HYPOTHESES_NOT_WRITTEN
    assert error.message == (
        f"{HYPOTHESES_PATH}: was not written: OSError: No space left on device"
    )
    assert str(root) not in error.message
    assert not hypotheses_path(root).exists()


def test_a_vanished_data_root_is_named_without_its_path(root, monkeypatch):
    run(root)
    real = hypotheses_file.write

    def vanishing(data_root, content):
        os.rename(root, root.with_name("gone"))
        return real(data_root, content)

    monkeypatch.setattr(hypotheses_file, "write", vanishing)
    error = failure(Source(root), {"run_id": RUN, "record": record()})
    assert error.kind == "hypotheses_not_written"
    assert error.message == (
        f"{HYPOTHESES_PATH}: was not written: FileNotFoundError: "
        "the data root is not an existing directory"
    )


def test_invalid_request_comes_before_no_data_root():
    source = FailingSource()
    error = failure(source, {"run_id": RUN, "record": record(round=0)})
    assert error.kind == "invalid_request"
    assert source.calls == 0


def test_no_data_root_comes_before_the_state():
    assert failure(FailingSource(), {"run_id": RUN, "record": citing()}).kind == (
        "no_data_root"
    )


def test_round_not_current_comes_before_check_4_and_the_write(root):
    run(root, state_round=2, instance=False)
    place(hypotheses_path(root), encoded(record()))
    assert refused(root, citing()).kind == "round_not_current"


def test_run_file_missing_of_state_comes_before_that_of_instance(root):
    error = refused(root, citing())
    assert error.message.startswith(STATE_PATH)


def test_the_kind_of_instance_comes_before_the_lookup(root, monkeypatch):
    run(root, instance=False)
    store_case(root)
    monkeypatch.setattr(case_lookup, "find", None)
    assert refused(root, citing()).kind == "run_file_missing"


def test_cases_unreadable_comes_before_hypotheses_exist(root, monkeypatch):
    run(root)
    store_case(root)
    place(hypotheses_path(root), encoded(record()))

    def denied(path):
        raise PermissionError(errno.EACCES, "denied", str(path))

    monkeypatch.setattr(os, "listdir", denied)
    assert refused(root, citing()).kind == "cases_unreadable"


def test_cases_mismatch_comes_before_hypotheses_exist(root):
    run(root)
    store_case(root)
    place(hypotheses_path(root), encoded(record()))
    assert refused(root, citing("h9")).kind == "cases_mismatch"


def test_a_refused_record_corrected_is_then_written(root):
    run(root)
    store_case(root)
    source = Source(root)
    assert failure(source, {"run_id": RUN, "record": citing("h9")}).kind == (
        "cases_mismatch"
    )
    assert write(source, {"run_id": RUN, "record": citing()}) == {}


def test_the_tool_appends_nothing_to_the_log(root, monkeypatch):
    run(root)
    monkeypatch.setattr(events, "append", None)
    assert write(Source(root), {"run_id": RUN, "record": record()}) == {}
    assert not layout.run_file(root, RUN, "events.ndjson").exists()


def test_the_default_registry_holds_hypotheses_write(root):
    registry = default_registry(lambda: root)
    assert "hypotheses.write" in registry.names()
    run(root)
    request = {"run_id": RUN, "record": record()}
    assert tools.call(registry, "hypotheses.write", request) == {}
    assert hypotheses_path(root).is_file()


def _mcp(request_id, method, params):
    document = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    return json.dumps(document).encode() + b"\n"


def test_the_mcp_front_lists_and_serves_hypotheses_write(root):
    run(root)
    arguments = {"run_id": RUN, "record": record()}
    data = b"".join(
        [
            _mcp(1, "tools/list", {}),
            _mcp(2, "tools/call", {"name": "hypotheses_write", "arguments": arguments}),
            _mcp(3, "tools/call", {"name": "hypotheses_write", "arguments": arguments}),
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
    assert "hypotheses_write" in names
    assert mcp_front.mcp_name("hypotheses.write") == "hypotheses_write"
    assert written["result"]["isError"] is False
    assert json.loads(written["result"]["content"][0]["text"]) == {}
    assert taken["result"]["isError"] is True
    error = json.loads(taken["result"]["content"][0]["text"])["error"]
    assert error["kind"] == "hypotheses_exist"
