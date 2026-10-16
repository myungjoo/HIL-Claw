"""The stated input schema of every tool of the default registry against its tool function.

ADR-0077 decisions 2 to 4: the tools of ``tools.default_registry``, bound to
a data-root source that fails and counts its calls, are called with one
accepted request each and with the requests derived from it that the
schema refuses, one change at a time; the schema is read here, in the eight
keywords and positions of decision 4, and a keyword or position it cannot
read, or an occurrence that yields no sure refused request, fails the test.
Not checked here: direction (B), whether a description tells what a
function refuses beyond its schema; what Claude Code does with an
``inputSchema`` (F14); registries other than the default one.
"""

import math
import re

import pytest

from hilclaw import tools


class CountingSource:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        raise RuntimeError("no data root in this test")


ACCEPTED = {
    "blob.fetch": {"sha256": "0123456789abcdef" * 4},
    "blob.push": {"sha256": "0123456789abcdef" * 4},
    "correctness.check": {
        "run_id": "r1",
        "round": 3,
        "candidate": 2,
        "attempt": 1,
        "execution": 1,
        "point": "sim",
    },
}

TOP_LEVEL = ("type", "properties", "required", "additionalProperties")
IN_PROPERTY = ("type", "enum", "minimum", "maximum", "pattern")
KEYWORDS = frozenset(TOP_LEVEL + IN_PROPERTY)
JSON_TYPES = ("null", "boolean", "integer", "number", "string", "array", "object")
OF_TYPE = {
    "null": None,
    "boolean": True,
    "integer": 3,
    "number": 0.5,
    "string": "3",
    "array": [],
    "object": {},
}
PATTERN_CANDIDATES = ("", "R1", "-", "x y", "G" * 64, "A" * 64, "0" * 65)
ENUM_CANDIDATES = (None, True, False, 0, -1, 0.5, "", "x", [], {})


def _is_number(value):
    return type(value) in (int, float)


def _type_admits(declared, value):
    types = [declared] if type(declared) is str else declared
    if value is None:
        return "null" in types
    if type(value) is bool:
        return "boolean" in types
    if type(value) is int:
        return "integer" in types or "number" in types
    if type(value) is float:
        if "number" in types:
            return True
        if "integer" in types and value.is_integer():
            return None
        return False
    if type(value) is str:
        return "string" in types
    if type(value) is list:
        return "array" in types
    if type(value) is dict:
        return "object" in types
    return None


def _json_equal(a, b):
    if _is_number(a) and _is_number(b):
        return a == b
    if type(a) is not type(b):
        return False
    if type(a) is list:
        return len(a) == len(b) and all(map(_json_equal, a, b))
    if type(a) is dict:
        return a.keys() == b.keys() and all(_json_equal(a[k], b[k]) for k in a)
    return a == b


def _pattern_admits(pattern, value):
    if not value.isascii() or any(c in value for c in "\n\r"):
        return None
    try:
        return re.search(pattern, value) is not None
    except re.error:
        return None


def _keyword_admits(keyword, argument, value):
    if keyword == "type":
        return _type_admits(argument, value)
    if keyword == "enum":
        return any(_json_equal(member, value) for member in argument)
    if keyword == "minimum":
        return not _is_number(value) or value >= argument
    if keyword == "maximum":
        return not _is_number(value) or value <= argument
    if keyword != "pattern":
        return None
    if type(value) is not str:
        return True
    return _pattern_admits(argument, value)


def _all(readings):
    readings = list(readings)
    if False in readings:
        return False
    return None if None in readings else True


def _value_admits(subschema, value):
    return _all(_keyword_admits(k, a, value) for k, a in subschema.items())


def _admits(schema, request):
    """True, False, or None where this reading cannot vouch for either."""
    properties = schema.get("properties", {})
    readings = [all(name in request for name in schema.get("required", []))]
    if schema.get("additionalProperties") is False:
        readings.append(all(name in properties for name in request))
    readings += [
        _value_admits(properties[name], value)
        for name, value in request.items()
        if name in properties
    ]
    return _all(readings)


def _type_problem(argument):
    if type(argument) is str:
        argument = [argument]
    if (
        type(argument) is not list
        or not argument
        or any(t not in JSON_TYPES for t in argument)
        or len(set(argument)) != len(argument)
    ):
        return "is not a JSON type or a list of distinct JSON types"
    return None


def _argument_problem(keyword, argument):
    if keyword == "type":
        return _type_problem(argument)
    if keyword == "enum" and (type(argument) is not list or not argument):
        return "is not a non-empty array"
    if keyword in ("minimum", "maximum") and not _is_number(argument):
        return "is not a number"
    if keyword == "pattern" and type(argument) is not str:
        return "is not a string"
    return None


def _unreadable(name, schema):
    problems = []

    def check(keyword, argument, position, allowed):
        if keyword not in KEYWORDS:
            problems.append(f"{name}: keyword {keyword!r} at {position} is not read")
        elif keyword not in allowed:
            problems.append(
                f"{name}: keyword {keyword!r} at {position} is in a position not read"
            )
        else:
            problem = _argument_problem(keyword, argument)
            if problem:
                problems.append(f"{name}: keyword {keyword!r} at {position} {problem}")

    for keyword, argument in schema.items():
        check(keyword, argument, "the top level", TOP_LEVEL)
    if schema.get("type") != "object":
        problems.append(f"{name}: keyword 'type' at the top level is not \"object\"")
    required = schema.get("required", [])
    if type(required) is not list or any(type(m) is not str for m in required):
        problems.append(
            f"{name}: keyword 'required' at the top level is not an array of strings"
        )
    if type(schema.get("additionalProperties", True)) is not bool:
        problems.append(
            f"{name}: keyword 'additionalProperties' at the top level "
            "is a deeper subschema, not read"
        )
    properties = schema.get("properties", {})
    if type(properties) is not dict:
        problems.append(f"{name}: keyword 'properties' at the top level is no object")
        return problems
    for member, subschema in properties.items():
        position = f"properties.{member}"
        if type(subschema) is not dict:
            problems.append(f"{name}: the subschema at {position} is no object")
            continue
        for keyword, argument in subschema.items():
            check(keyword, argument, position, IN_PROPERTY)
    return problems


def _with(request, member, value):
    changed = dict(request)
    changed[member] = value
    return changed


def _candidates(keyword, argument):
    if keyword == "type":
        types = [argument] if type(argument) is str else argument
        return [OF_TYPE[t] for t in JSON_TYPES if not _type_admits(types, OF_TYPE[t])]
    if keyword == "enum":
        joined = "".join(m for m in argument if type(m) is str) + "x"
        numbers = [m for m in argument if _is_number(m)]
        above = [math.floor(max(numbers)) + 1] if numbers else []
        return [joined, *above, *ENUM_CANDIDATES]
    if keyword == "minimum":
        return [math.ceil(argument) - 1, argument - 0.5]
    if keyword == "maximum":
        return [math.floor(argument) + 1, argument + 0.5]
    return list(PATTERN_CANDIDATES)


def _keyword_refuses_alone(subschema, keyword, value):
    if keyword == "type":
        return _keyword_admits(keyword, subschema[keyword], value) is False
    rest = {k: a for k, a in subschema.items() if k != keyword}
    return (
        _keyword_admits(keyword, subschema[keyword], value) is False
        and _value_admits(rest, value) is True
    )


def _label(value):
    text = repr(value)
    return text if len(text) <= 24 else f"{text[:12]}...{text[-6:]}"


def reading(name, schema, accepted):
    """Return the problems of a schema and (label, request) pairs it surely refuses."""
    problems = _unreadable(name, schema)
    if problems or accepted is None:
        return problems, []
    derived = []

    def keep(label, request):
        if _admits(schema, request) is False:
            derived.append((f"{name}: {label}", request))
            return True
        return False

    properties = schema.get("properties", {})
    required = schema.get("required", [])
    for member in required:
        without = {k: v for k, v in accepted.items() if k != member}
        if not keep(f"required without {member}", without):
            problems.append(f"{name}: leaving out the required {member} is not refused")
    if schema.get("additionalProperties") is False:
        extra = "unlisted"
        while extra in properties:
            extra += "_"
        if not keep(f"additionalProperties with {extra}", _with(accepted, extra, 0)):
            problems.append(f"{name}: an added member {extra} is not refused")
    for member, subschema in properties.items():
        for keyword in IN_PROPERTY:
            if keyword not in subschema:
                continue
            seen = []
            kept = 0
            for value in _candidates(keyword, subschema[keyword]):
                if any(_json_equal(value, s) and type(value) is type(s) for s in seen):
                    continue
                seen.append(value)
                if not _keyword_refuses_alone(subschema, keyword, value):
                    continue
                request = _with(accepted, member, value)
                if keep(f"{keyword} {member}={_label(value)}", request):
                    kept += 1
                    if keyword == "enum":
                        break
            if not kept:
                problems.append(
                    f"{name}: keyword {keyword!r} at properties.{member} "
                    "yields no sure refused request"
                )
    return problems, derived


def _registry():
    source = CountingSource()
    return tools.default_registry(source), source


def _schemas():
    registry, _ = _registry()
    return {name: registry.definition(name).input_schema for name in registry.names()}


SCHEMAS = _schemas()
DERIVED = [
    (name, label, request)
    for name, schema in SCHEMAS.items()
    for label, request in reading(name, schema, ACCEPTED.get(name))[1]
]


def test_every_registered_tool_has_an_accepted_request_and_no_other_entry():
    registered = set(_registry()[0].names())
    assert registered, "the default registry holds no tool"
    missing = sorted(registered - ACCEPTED.keys())
    stale = sorted(ACCEPTED.keys() - registered)
    assert not missing, f"registered tools without an accepted request: {missing}"
    assert not stale, f"accepted requests naming no registered tool: {stale}"


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_the_schema_is_read_and_each_occurrence_yields_a_refused_request(name):
    problems, derived = reading(name, SCHEMAS[name], ACCEPTED.get(name))
    assert not problems, "\n".join(problems)
    assert derived, f"{name}: no refused request is derived"


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_the_accepted_request_is_admitted_and_reaches_the_source(name):
    assert name in ACCEPTED, f"{name} has no accepted request"
    request = ACCEPTED[name]
    assert _admits(SCHEMAS[name], request) is True, (
        f"the schema of {name} does not surely admit {request}"
    )
    registry, source = _registry()
    with pytest.raises(tools.ToolFailure) as e:
        tools.call(registry, name, request)
    assert e.value.kind == tools.KIND_NO_DATA_ROOT, e.value.message
    assert source.calls == 1


@pytest.mark.parametrize(
    ("name", "request_"),
    [(name, request) for name, _, request in DERIVED],
    ids=[label for _, label, _ in DERIVED],
)
def test_a_request_the_schema_refuses_is_invalid_request(name, request_):
    registry, source = _registry()
    with pytest.raises(tools.ToolFailure) as e:
        tools.call(registry, name, request_)
    assert e.value.kind == tools.KIND_INVALID_REQUEST, (
        f"{name} gave {e.value.kind} for {request_}: {e.value.message}"
    )
    assert source.calls == 0
