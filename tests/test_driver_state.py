import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw.driver_state import SchemaError, load_schema, main, validate

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "PROCESS" / "STATE.json"
SCHEMA_PATH = REPO_ROOT / "PROCESS" / "STATE.schema.json"
FIELDS = {
    "schema_version",
    "phase",
    "currentTask",
    "nextTask",
    "lock",
    "humanQuestions",
    "counters",
    "lastIteration",
    "notes",
}


def full_state():
    return {
        "schema_version": 1,
        "phase": "P0.5",
        "currentTask": "T-0012",
        "nextTask": "T-0013",
        "lock": {
            "owner": "host-1:abc123",
            "acquiredAt": "2026-10-06T02:26:06.123Z",
            "ttlMinutes": 180,
        },
        "humanQuestions": [
            {
                "id": "HQ-0001",
                "taskId": "T-0003",
                "reason": "permission-denied",
                "question": "Allow it?",
                "askedAt": "2026-10-05T18:22:00Z",
                "issueComment": "https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-1",
                "resolvedAt": "2026-10-06T09:00:00Z",
                "decision": "HQ-0001 confirmed (a)",
            },
            {
                "id": "HQ-0002",
                "taskId": "T-0012",
                "reason": "task-timeout",
                "question": "Split it?",
                "askedAt": "2026-10-06T10:00:00Z",
                "issueComment": None,
            },
        ],
        "counters": {
            "iterations": 0,
            "tasksDone": 0,
            "tasksBlocked": 0,
            "reviewRoundsTotal": 0,
        },
        "lastIteration": None,
        "notes": "",
    }


def mutated(change):
    state = full_state()
    change(state)
    return state


def paths(problems):
    return {p.split(": ", 1)[0] for p in problems}


def keywords(problems):
    return {p.split(": ")[1] for p in problems}


def test_committed_state_is_valid():
    with STATE_PATH.open(encoding="utf-8") as f:
        assert validate(json.load(f)) == []


def test_full_state_is_valid():
    assert validate(full_state()) == []


def test_minimal_branches_are_valid():
    state = mutated(
        lambda s: s.update(
            currentTask=None, nextTask=None, lock=None, humanQuestions=[]
        )
    )
    state["lastIteration"] = {
        "at": "2026-10-05T18:22:00Z",
        "owner": "AKIHA:1",
        "taskId": "T-0003",
        "outcome": "BLOCKED",
    }
    assert validate(state) == []


def test_schema_fields_match_driver_table():
    schema = load_schema()
    assert set(schema["properties"]) == FIELDS
    assert set(schema["required"]) == FIELDS
    assert len(schema["required"]) == len(FIELDS)


def _set(*keys_and_value):
    *keys, value = keys_and_value

    def change(state):
        target = state
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value

    return change


def _delete(*keys):
    def change(state):
        target = state
        for key in keys[:-1]:
            target = target[key]
        del target[keys[-1]]

    return change


NEGATIVE = [
    (
        "iterations-as-string",
        _set("counters", "iterations", "3"),
        "$.counters.iterations",
        "type",
    ),
    ("ttl-as-bool", _set("lock", "ttlMinutes", True), "$.lock.ttlMinutes", "type"),
    ("ttl-as-float", _set("lock", "ttlMinutes", 1.5), "$.lock.ttlMinutes", "type"),
    ("notes-null", _set("notes", None), "$.notes", "type"),
    ("hq-not-array", _set("humanQuestions", {}), "$.humanQuestions", "type"),
    (
        "hq-item-not-object",
        _set("humanQuestions", ["HQ-0001"]),
        "$.humanQuestions[0]",
        "type",
    ),
    ("lock-as-string", _set("lock", "AKIHA:1"), "$.lock", "type"),
    ("missing-top-level", _delete("notes"), "$.notes", "required"),
    ("missing-in-lock", _delete("lock", "owner"), "$.lock.owner", "required"),
    (
        "missing-issue-comment",
        _delete("humanQuestions", 1, "issueComment"),
        "$.humanQuestions[1].issueComment",
        "required",
    ),
    (
        "missing-counter",
        _delete("counters", "reviewRoundsTotal"),
        "$.counters.reviewRoundsTotal",
        "required",
    ),
    ("bad-enum", _set("phase", "P4"), "$.phase", "enum"),
    ("bad-const", _set("schema_version", 2), "$.schema_version", "const"),
    ("const-not-bool", _set("schema_version", True), "$.schema_version", "type"),
    ("bad-task-id", _set("currentTask", "T-4"), "$.currentTask", "pattern"),
    ("task-id-trailing-newline", _set("nextTask", "T-0004\n"), "$.nextTask", "pattern"),
    ("task-id-non-ascii-digits", _set("nextTask", "T-١٢٣٤"), "$.nextTask", "pattern"),
    (
        "bad-hq-id",
        _set("humanQuestions", 0, "id", "HQ-1"),
        "$.humanQuestions[0].id",
        "pattern",
    ),
    ("owner-without-colon", _set("lock", "owner", "AKIHA"), "$.lock.owner", "pattern"),
    (
        "not-a-date",
        _set("lock", "acquiredAt", "yesterday"),
        "$.lock.acquiredAt",
        "format pattern",
    ),
    (
        "bad-calendar",
        _set("humanQuestions", 0, "askedAt", "2026-13-01T00:00:00Z"),
        "$.humanQuestions[0].askedAt",
        "format",
    ),
    (
        "bad-time",
        _set("humanQuestions", 0, "resolvedAt", "2026-10-01T25:00:00Z"),
        "$.humanQuestions[0].resolvedAt",
        "format",
    ),
    (
        "hour-24",
        _set("lock", "acquiredAt", "2026-10-06T24:00:00Z"),
        "$.lock.acquiredAt",
        "format",
    ),
    (
        "no-timezone",
        _set("lock", "acquiredAt", "2026-10-06T02:26:06"),
        "$.lock.acquiredAt",
        "format pattern",
    ),
    (
        "plus-offset",
        _set("lock", "acquiredAt", "2026-10-06T02:26:06+00:00"),
        "$.lock.acquiredAt",
        "pattern",
    ),
    (
        "date-only",
        _set("lock", "acquiredAt", "2026-10-06"),
        "$.lock.acquiredAt",
        "format pattern",
    ),
    (
        "negative-counter",
        _set("counters", "tasksDone", -1),
        "$.counters.tasksDone",
        "minimum",
    ),
    ("zero-ttl", _set("lock", "ttlMinutes", 0), "$.lock.ttlMinutes", "minimum"),
    (
        "extra-top-level",
        _set("$schema", "./STATE.schema.json"),
        '$["$schema"]',
        "additionalProperties",
    ),
    (
        "extra-in-lock",
        _set("lock", "heartbeat", "x"),
        "$.lock.heartbeat",
        "additionalProperties",
    ),
    (
        "extra-in-hq",
        _set("humanQuestions", 1, "answer", "x"),
        "$.humanQuestions[1].answer",
        "additionalProperties",
    ),
    (
        "extra-in-last-iteration",
        _set(
            "lastIteration",
            {
                "at": "2026-10-05T18:22:00Z",
                "owner": "a:b",
                "taskId": "T-0001",
                "outcome": "DONE",
                "x": 1,
            },
        ),
        "$.lastIteration.x",
        "additionalProperties",
    ),
]


@pytest.mark.parametrize(
    ("change", "path", "keyword"),
    [c[1:] for c in NEGATIVE],
    ids=[c[0] for c in NEGATIVE],
)
def test_negative_cases_name_path_and_keyword(change, path, keyword):
    problems = validate(mutated(change))
    assert paths(problems) == {path}
    assert keywords(problems) == set(keyword.split())
    assert len(problems) == len(keyword.split()), problems


@pytest.mark.parametrize(
    ("instance", "name"),
    [
        ([], "array"),
        ("state", "string"),
        (None, "null"),
        (1, "integer"),
        (1.5, "number"),
        (True, "boolean"),
        ((), "tuple"),
    ],
)
def test_top_level_not_an_object(instance, name):
    assert validate(instance) == [f"$: type: expected object, got {name}"]


def test_type_failure_reports_only_the_type():
    problems = validate(mutated(_set("currentTask", 4)))
    assert problems == ["$.currentTask: type: expected string or null, got integer"]


def test_several_problems_are_all_reported():
    def change(state):
        state["phase"] = "P9"
        state["lock"]["ttlMinutes"] = 0
        del state["humanQuestions"][0]["question"]
        state["counters"]["iterations"] = "1"
        state["extra"] = True

    problems = validate(mutated(change))
    assert paths(problems) == {
        "$.phase",
        "$.lock.ttlMinutes",
        "$.humanQuestions[0].question",
        "$.counters.iterations",
        "$.extra",
    }


def test_validate_does_not_mutate_input():
    state = mutated(_set("lock", "ttlMinutes", 0))
    before = copy.deepcopy(state)
    validate(state)
    assert state == before


def test_validate_does_not_mutate_schema():
    schema = load_schema()
    before = copy.deepcopy(schema)
    validate(full_state(), schema)
    assert schema == before


@pytest.mark.parametrize(
    ("schema", "instance", "expected"),
    [
        ({"enum": [1, "a"]}, 1.0, []),
        ({"enum": [1]}, True, ["$: enum: true is not one of [1]"]),
        ({"const": False}, 0, ["$: const: expected false"]),
        ({"const": {"a": [1, None]}}, {"a": [1, None]}, []),
        ({"const": {"a": [1]}}, {"a": [2]}, ['$: const: expected {"a": [1]}']),
        ({"const": [1, 2]}, [1], ["$: const: expected [1, 2]"]),
        ({"const": "1"}, 1, ['$: const: expected "1"']),
        ({"minimum": 1}, "0", []),
        ({"minimum": 1}, 0.5, ["$: minimum: 0.5 is less than 1"]),
        ({"pattern": "^a"}, 1, []),
        ({"pattern": "[$]"}, "a$", []),
        ({"pattern": "\\$"}, "a$", []),
        ({"pattern": "[\\]$]x$"}, "]x", []),
        (
            {"pattern": "[\\]$]x$"},
            "$x\n",
            [r'$: pattern: "$x\n" does not match "[\\]$]x$"'],
        ),
        ({"format": "date-time"}, "2026-10-06T02:26:06-05:00", []),
        (
            {"format": "date-time"},
            "2026-10-06T02:26:06+24:00",
            ['$: format: "2026-10-06T02:26:06+24:00" is not a date-time'],
        ),
        (
            {"items": {"type": "integer"}},
            [1, "x"],
            ["$[1]: type: expected integer, got string"],
        ),
        (
            {"properties": {"a b": {"type": "null"}}},
            {"a b": 0, "c": 0},
            ['$["a b"]: type: expected null, got integer'],
        ),
        ({"$id": "x", "title": "t", "description": "d", "type": "array"}, [], []),
    ],
)
def test_keyword_semantics(schema, instance, expected):
    assert validate(instance, schema) == expected


@pytest.mark.parametrize(
    "schema",
    [
        {"oneOf": [{"type": "string"}]},
        {"properties": {"a": {"$ref": "#/$defs/x"}}},
        {"items": {"minLength": 1}},
        {"format": "email"},
        {"type": "number"},
        {"type": ["string", "boolean"]},
        {"type": []},
        {"type": [["string"]]},
        {"additionalProperties": {"type": "string"}},
        {"pattern": "("},
        {"pattern": 1},
        {"properties": []},
        {"required": "a"},
        {"enum": "a"},
        {"minimum": True},
        {"items": [{"type": "string"}]},
        [],
    ],
)
def test_unsupported_schema_raises(schema):
    with pytest.raises(SchemaError):
        validate({}, schema)


def test_schema_error_is_a_value_error():
    assert issubclass(SchemaError, ValueError)


def test_load_schema_default_path(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    schema = load_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_load_schema_explicit_path(tmp_path):
    path = tmp_path / "s.json"
    path.write_text('{"type": "object"}', encoding="utf-8")
    assert load_schema(path) == {"type": "object"}
    assert load_schema(str(path)) == {"type": "object"}


def test_load_schema_missing_path(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_schema(tmp_path / "missing.json")


def write_json(tmp_path, value):
    path = tmp_path / "STATE.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_main_valid_file(tmp_path, capsys):
    path = write_json(tmp_path, full_state())
    assert main([str(path)]) == 0
    out, err = capsys.readouterr()
    assert out.strip().endswith(": OK")
    assert err == ""


def test_main_invalid_file(tmp_path, capsys):
    path = write_json(tmp_path, mutated(_set("phase", "P4")) | {"extra": 1})
    assert main([str(path)]) == 1
    out, err = capsys.readouterr()
    assert out == ""
    lines = err.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("$.phase: enum:")
    assert lines[1] == "$.extra: additionalProperties: not allowed"


def test_main_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "missing.json")]) == 1
    err = capsys.readouterr().err
    assert len(err.splitlines()) == 1
    assert "cannot read" in err


def test_main_non_json_file(tmp_path, capsys):
    path = tmp_path / "STATE.json"
    path.write_text("{not json", encoding="utf-8")
    assert main([str(path)]) == 1
    err = capsys.readouterr().err
    assert len(err.splitlines()) == 1
    assert "not valid JSON" in err


def test_main_non_utf8_file(tmp_path, capsys):
    path = tmp_path / "STATE.json"
    path.write_bytes(b'{"notes": "\xff"}')
    assert main([str(path)]) == 1
    assert "not valid JSON" in capsys.readouterr().err


def test_main_default_path_is_committed_state(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    assert main([]) == 0
    assert str(STATE_PATH) in capsys.readouterr().out


def test_module_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "hilclaw.driver_state", str(STATE_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith(": OK")
