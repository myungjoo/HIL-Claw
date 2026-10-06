"""Validator for the driver state file ``PROCESS/STATE.json``.

The shape of the file is defined by ``PROCESS/STATE.schema.json`` (JSON Schema
draft 2020-12). This module interprets exactly the keyword subset that schema
uses, with the standard library only, and raises :class:`SchemaError` for any
other keyword so that a schema change can never be silently ignored.

Command line: ``python -m hilclaw.driver_state [PATH]``. ``PATH`` defaults to
``PROCESS/STATE.json`` at the repository root. Exit status is 0 when the file
is valid, 1 when it is invalid, missing or not JSON.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_PATH = REPO_ROOT / "PROCESS" / "STATE.schema.json"
DEFAULT_STATE_PATH = REPO_ROOT / "PROCESS" / "STATE.json"

_ANNOTATIONS = frozenset({"$schema", "$id", "title", "description"})
_KEYWORDS = _ANNOTATIONS | set(
    "type properties required additionalProperties items enum const pattern format minimum".split()
)
_TYPE_NAMES = frozenset({"object", "array", "string", "integer", "null"})
_FORMATS = frozenset({"date-time"})
_SHAPES = (
    ("properties", dict, "an object"),
    ("required", list, "an array"),
    ("enum", list, "an array"),
    ("minimum", (int, float), "a number"),
)
_DATE_TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})"
)
_ECMA_DOLLAR = re.compile(r"(\\.|\[(?:\\.|[^\]])*\])|\$")
_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class SchemaError(ValueError):
    """The schema itself uses something this validator does not implement."""


def load_schema(path=None):
    """Read the schema; ``path`` defaults to ``PROCESS/STATE.schema.json`` at the repository root."""
    with Path(path or DEFAULT_SCHEMA_PATH).open(encoding="utf-8") as f:
        return json.load(f)


def validate(instance, schema=None):
    """Return every problem of ``instance`` against ``schema`` as ``"<json path>: <keyword>: <detail>"``.

    An empty list means the instance is valid. ``schema`` defaults to
    :func:`load_schema`. Raises :class:`SchemaError` for an unsupported schema.
    """
    if schema is None:
        schema = load_schema()
    compiled = _compile(schema, "#")
    problems = []
    _check(instance, compiled, "$", problems)
    return problems


def _compile(schema, where):
    if not isinstance(schema, dict):
        raise SchemaError(f"{where}: a schema must be an object")
    unknown = sorted(schema.keys() - _KEYWORDS)
    if unknown:
        raise SchemaError(f"{where}: unsupported keyword(s) {unknown}")
    for key, kind, name in _SHAPES:
        if key in schema and (
            not isinstance(schema[key], kind) or isinstance(schema[key], bool)
        ):
            raise SchemaError(f"{where}/{key}: must be {name}")
    out = dict(schema)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        bad = [n for n in names if not isinstance(n, str) or n not in _TYPE_NAMES]
        if bad or not names:
            raise SchemaError(f"{where}/type: unsupported type name(s) {bad}")
        out["type"] = names
    if "format" in schema and schema["format"] not in _FORMATS:
        raise SchemaError(f"{where}/format: unsupported format {schema['format']!r}")
    if "additionalProperties" in schema and not isinstance(
        schema["additionalProperties"], bool
    ):
        raise SchemaError(f"{where}/additionalProperties: only a boolean is supported")
    if "pattern" in schema:
        try:
            out["_regex"] = re.compile(_ecma_anchors(schema["pattern"]), re.ASCII)
        except (re.error, TypeError) as e:
            raise SchemaError(f"{where}/pattern: {e}") from e
    if "properties" in schema:
        out["properties"] = {
            k: _compile(v, f"{where}/properties/{k}")
            for k, v in schema["properties"].items()
        }
    if "items" in schema:
        out["items"] = _compile(schema["items"], f"{where}/items")
    return out


def _ecma_anchors(pattern):
    return _ECMA_DOLLAR.sub(lambda m: m.group(1) or r"\Z", pattern)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _has_type(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "null":
        return value is None
    return isinstance(value, {"object": dict, "array": list, "string": str}[name])


def _json_type(value):
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, float):
        return "number"
    names = [n for n in sorted(_TYPE_NAMES) if _has_type(value, n)]
    return names[0] if names else type(value).__name__


def _json_equal(a, b):
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_number(a) and _is_number(b):
        return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_json_equal(x, y) for x, y in zip(a, b))
    return type(a) is type(b) and a == b


def _is_date_time(value):
    if not _DATE_TIME.fullmatch(value):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError:
        return False
    return True


def _child(path, key):
    return (
        f"{path}.{key}" if _IDENTIFIER.fullmatch(key) else f"{path}[{json.dumps(key)}]"
    )


def _check(value, schema, path, problems):
    if "type" in schema and not any(_has_type(value, n) for n in schema["type"]):
        expected = " or ".join(schema["type"])
        problems.append(f"{path}: type: expected {expected}, got {_json_type(value)}")
        return
    if "const" in schema and not _json_equal(value, schema["const"]):
        problems.append(f"{path}: const: expected {json.dumps(schema['const'])}")
    if "enum" in schema and not any(_json_equal(value, e) for e in schema["enum"]):
        problems.append(
            f"{path}: enum: {json.dumps(value)} is not one of {json.dumps(schema['enum'])}"
        )
    if isinstance(value, str):
        if "pattern" in schema and not schema["_regex"].search(value):
            problems.append(
                f"{path}: pattern: {json.dumps(value)} does not match {json.dumps(schema['pattern'])}"
            )
        if "format" in schema and not _is_date_time(value):
            problems.append(f"{path}: format: {json.dumps(value)} is not a date-time")
    if _is_number(value) and "minimum" in schema and value < schema["minimum"]:
        problems.append(f"{path}: minimum: {value} is less than {schema['minimum']}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                problems.append(f"{_child(path, key)}: required: missing")
        for key, item in value.items():
            if key in properties:
                _check(item, properties[key], _child(path, key), problems)
            elif schema.get("additionalProperties") is False:
                problems.append(
                    f"{_child(path, key)}: additionalProperties: not allowed"
                )
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _check(item, schema["items"], f"{path}[{i}]", problems)


def main(argv=None):
    """Validate a driver state file and return the process exit status."""
    parser = argparse.ArgumentParser(
        prog="python -m hilclaw.driver_state",
        description="Validate PROCESS/STATE.json against PROCESS/STATE.schema.json.",
    )
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_STATE_PATH)
    args = parser.parse_args(argv)
    try:
        with args.path.open(encoding="utf-8") as f:
            instance = json.load(f)
    except OSError as e:
        print(f"{args.path}: cannot read: {e.strerror or e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"{args.path}: not valid JSON: {e}", file=sys.stderr)
        return 1
    problems = validate(instance)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    print(f"{args.path}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
