import inspect
import io
import json
import math
import reprlib
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import __main__ as command_line
from hilclaw import (
    events,
    hw_tool,
    instance,
    keys,
    layout,
    mcp_front,
    mock_backend,
    run_state,
    tools,
)
from hilclaw.backends import BackendTable
from hilclaw.harness import verification_arrays
from hilclaw.instance import (
    SCHEMA_VERSION,
    Instance,
    InvalidInstanceError,
    MissingInstanceError,
    Tolerance,
    UnsupportedVersionError,
    hw_profile_of,
    parse,
    read,
    tolerance_of,
    validate,
)
from hilclaw.journal import EMPTY
from hilclaw.tools import Registry, ToolFailure

# Synthetic values only: no record, key, member or step of a real run.
RUN = "run-a"
OTHER_RUN = "run-b"
FILE = f"runs/{RUN}/instance.json"
MAX = keys.MAX_INTEGER
TOO_LONG = 10**5000
TOO_LONG_TEXT = "1" + "0" * 5000
REMOVE = object()
TOOL = "sim.run"
STEP = "example_step"
SPEND = {"example_axis": 7}
REQUEST = {"run_id": RUN, "round": 3, "candidate": 2, "attempt": 1, "execution": 1}
# Test values of a tolerance: no default, recommended or typical value.
TEST_RTOL, TEST_ATOL = 0.25, 3.0
OTHER_TEST_RTOL, OTHER_TEST_ATOL = 0.5, 7.0
TOLERANCE = {"rtol": TEST_RTOL, "atol": TEST_ATOL}
OTHER_TOLERANCE = {"rtol": OTHER_TEST_RTOL, "atol": OTHER_TEST_ATOL}

# The Example of ADR-0018, as written in the record: the shape of the member, not a valid file.
EXAMPLE = b"""{
  "schema_version": 1,
  "hw_profile": {
    "key": "cpu_standin-b0d8610d8f470856",
    "record": {
      "schema_version": 1,
      "accelerator": "cpu_standin",
      "revision": "NOT-DECIDED-HERE",
      "toolchain": {"clang": "NOT-DECIDED-HERE"},
      "host": {"cpu": "NOT-DECIDED-HERE", "os": "NOT-DECIDED-HERE"},
      "hw_source": "NOT-DECIDED-HERE"
    }
  }
}
"""


def record(accelerator=mock_backend.NAME, **changes):
    made = {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "rev 1",
        "toolchain": {"cc": "1.0"},
        "host": {"cpu": "cpu x", "os": "os y"},
        "hw_source": "external",
    }
    for name, value in changes.items():
        made[name] = value
    return {name: value for name, value in made.items() if value is not REMOVE}


def key_of(profile):
    return keys.hw_profile_key(profile).name


KEY = key_of(record())
OTHER_RECORD = record("acc_b", label="another")
OTHER_KEY = key_of(OTHER_RECORD)


def doc(profile=None, **changes):
    profile = record() if profile is None else profile
    made = {
        "schema_version": 1,
        "hw_profile": {"key": key_of(profile), "record": profile},
    }
    for name, value in changes.items():
        if value is REMOVE:
            del made[name]
        else:
            made[name] = value
    return made


def section(**changes):
    made = {"key": KEY, "record": record()}
    for name, value in changes.items():
        if value is REMOVE:
            del made[name]
        else:
            made[name] = value
    return made


def raw(document):
    return json.dumps(document).encode()


VERSION = '"schema_version": 1'
RECORD = json.dumps(record())
SECTION = f'"hw_profile": {{"key": "{KEY}", "record": {RECORD}}}'


def text(*members):
    return ("{" + ", ".join(members) + "}").encode()


def shown(value):
    try:
        return repr(value)[:20]
    except ValueError:
        return "an int too long to show"


def invalid(place, function, *arguments):
    with pytest.raises(InvalidInstanceError) as caught:
        function(*arguments)
    assert str(caught.value).startswith(place), str(caught.value)
    return str(caught.value)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


def place(root, content, relative=FILE):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def snapshot(path):
    return {
        item.relative_to(path).as_posix(): (
            (item.read_bytes(), item.stat().st_mtime_ns) if item.is_file() else None
        )
        for item in path.rglob("*")
    }


def link(path, target):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


# --- happy: the pure half ---


def test_the_public_names():
    public = sorted(
        name
        for name, value in vars(instance).items()
        if not name.startswith("_")
        and not inspect.ismodule(value)
        and getattr(value, "__module__", instance.__name__) == instance.__name__
    )
    assert public == [
        "Instance",
        "InvalidInstanceError",
        "MissingInstanceError",
        "SCHEMA_VERSION",
        "Tolerance",
        "UnsupportedVersionError",
        "hw_profile_of",
        "parse",
        "read",
        "tolerance_of",
        "validate",
    ]
    assert SCHEMA_VERSION == 1
    assert Instance._fields == ("hw_profile_key", "hw_profile", "tolerance", "others")
    assert Tolerance._fields == ("rtol", "atol")
    assert Tolerance._field_defaults == Instance._field_defaults == {}
    assert issubclass(InvalidInstanceError, ValueError)
    for error in (UnsupportedVersionError, MissingInstanceError):
        assert not issubclass(error, (ValueError, OSError))
    for error in (InvalidInstanceError, UnsupportedVersionError, MissingInstanceError):
        assert not issubclass(error, ToolFailure)
    assert UnsupportedVersionError is not run_state.UnsupportedVersionError
    for function in (read, hw_profile_of, tolerance_of):
        parameters = inspect.signature(function).parameters
        assert list(parameters) == ["data_root", "run_id"]
        for parameter in parameters.values():
            assert parameter.default is inspect.Parameter.empty
    assert list(inspect.signature(parse).parameters) == ["content"]
    assert list(inspect.signature(validate).parameters) == ["document"]


def test_a_minimal_content_gives_the_key_and_the_record():
    result = parse(raw(doc()))

    assert type(result) is Instance
    assert result == Instance(KEY, record(), None, {})
    assert type(result.hw_profile) is dict
    assert key_of(result.hw_profile) == result.hw_profile_key
    assert validate(doc()) is None


def test_a_record_with_its_optional_fields():
    profile = record(ext={"example_field": 3}, label="a label")

    result = parse(raw(doc(profile)))

    assert result == Instance(key_of(profile), profile, None, {})
    assert result.hw_profile_key == key_of(record(ext={"example_field": 3}))
    assert result.hw_profile_key != KEY


@pytest.mark.parametrize(
    "content",
    [
        text(SECTION, VERSION),
        text(
            VERSION, f'"hw_profile": {{"record": {RECORD}, "key": "{KEY}"}}', '"z": 1'
        ),
        json.dumps(doc(), indent=2).encode(),
        json.dumps(doc(), indent=2).encode() + b"\n",
        json.dumps(doc(), indent=2).replace("\n", "\r\n").encode() + b"\r\n",
        json.dumps(doc(), indent="\t").encode(),
        b" \t\r\n" + raw(doc()) + b"\n\n ",
        json.dumps(doc(), separators=(",", ":")).encode(),
        json.dumps(doc(), sort_keys=True).encode(),
    ],
)
def test_any_order_of_members_and_any_white_space_are_accepted(content):
    result = parse(content)

    assert (result.hw_profile_key, result.hw_profile) == (KEY, record())


OTHERS = {
    "an_object": {"nested": {"deeper": [1, {"x": None}]}},
    "an_array": [1, "two", 3.5, None, True, [], {}],
    "a_string": "text é",
    "an_integer": -7,
    "a_number": 2.5,
    "a_true": True,
    "a_false": False,
    "a_null": None,
    "": "an empty name",
    "Schema_Version": "not the member",
}


def test_members_not_defined_are_returned_as_parsed_and_not_interpreted():
    result = parse(raw(doc(**OTHERS)))

    assert result == Instance(KEY, record(), None, OTHERS)
    assert list(result.others) == list(OTHERS)
    assert validate(doc(**OTHERS)) is None


@pytest.mark.parametrize(
    "others",
    [
        {"hw_profiles": [record("acc_b")]},
        {"hw_profiles": {"key": OTHER_KEY, "record": OTHER_RECORD}},
        {"objective": None, "budget": -1},
        {"budget": [], "objective": "", "hw_profile_key": OTHER_KEY},
        {"layout_version": 99, "source_commit": False, "run_id": "another"},
    ],
)
def test_the_top_level_is_open(others):
    result = parse(raw(doc(**others)))

    assert (result.hw_profile_key, result.hw_profile) == (KEY, record())
    assert result.others == others
    validate(doc(**others))


def test_a_number_beyond_the_float_range_in_a_member_not_defined_is_not_an_error():
    result = parse(text(VERSION, SECTION, '"example_member": 1e999'))

    assert result.others == {"example_member": float("inf")}


# --- branch: another version ---

BROKEN_SECTIONS = [REMOVE, None, [], {"key": 7}, section(key=OTHER_KEY)]


@pytest.mark.parametrize("version", [0, 2, 3, MAX])
@pytest.mark.parametrize("hw_profile", [*BROKEN_SECTIONS, section()], ids=repr)
def test_another_version_is_reported_before_any_other_member(version, hw_profile):
    document = doc(schema_version=version, hw_profile=hw_profile, example=[1])

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"
        assert not isinstance(caught.value, ValueError)


@pytest.mark.parametrize("hw_profile", BROKEN_SECTIONS, ids=repr)
def test_at_version_1_the_same_content_is_judged_by_its_hw_profile(hw_profile):
    document = doc(hw_profile=hw_profile, example=[1])

    invalid("", parse, raw(document))
    invalid("", validate, document)


def test_minus_zero_is_read_as_the_version_0():
    with pytest.raises(UnsupportedVersionError, match="^schema_version: 0 is not"):
        parse(text('"schema_version": -0', SECTION))


# --- error / negative: the whole text ---


@pytest.mark.parametrize(
    "value",
    [raw(doc()).decode(), bytearray(raw(doc())), memoryview(raw(doc())), None, doc()],
    ids=lambda value: type(value).__name__,
)
def test_content_must_be_bytes(value):
    with pytest.raises(TypeError, match="content must be bytes"):
        parse(value)


def test_a_byte_order_mark():
    invalid("content: starts with a byte order mark", parse, b"\xef\xbb\xbf")
    invalid(
        "content: starts with a byte order mark", parse, b"\xef\xbb\xbf" + raw(doc())
    )


@pytest.mark.parametrize(
    "content",
    [
        b"\xff",
        raw(doc()).replace(b"rev 1", b"rev \xff"),
        raw(doc()).decode().encode("utf-16"),
        raw(doc()).decode().encode("utf-16-le"),
        text(VERSION, SECTION, '"example": "\xe9"').decode().encode("latin-1"),
    ],
)
def test_bytes_that_are_not_utf_8(content):
    invalid("content: cannot be read as one JSON text", parse, content)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b" ",
        b"\n",
        b" \t\r\n",
        b"{",
        raw(doc())[:-1],
        raw(doc())[: len(raw(doc())) // 2],
        raw(doc())[1:],
        raw(doc()) + raw(doc()),
        raw(doc()) + b"\n" + raw(doc()),
        raw(doc()) + b"}",
        raw(doc()) + b"\x00",
        text(VERSION, SECTION, '"example": 01'),
        text(VERSION, SECTION, "'example': 1"),
        text(VERSION, SECTION, '"example": 1,'),
        text(VERSION, SECTION, '"example": NaN'),
        text(VERSION, SECTION, '"example": [Infinity]'),
        text(VERSION, SECTION, '"example": {"deep": -Infinity}'),
        text('"schema_version": NaN', SECTION),
        text('"schema_version": 2', '"example": NaN'),
    ],
)
def test_content_that_is_not_exactly_one_json_text(content):
    invalid("content: cannot be read as one JSON text", parse, content)


@pytest.mark.parametrize(
    "content",
    [b"[]", b"1", b'"text"', b"null", b"true", b"1.5", b"[" + raw(doc()) + b"]"],
)
def test_a_text_that_is_not_an_object(content):
    invalid("document: must be an object, got ", parse, content)


@pytest.mark.parametrize(
    "content",
    [
        text(VERSION, VERSION, SECTION),
        text(VERSION, SECTION, SECTION),
        text(VERSION, SECTION, '"example": 1', '"example": 1'),
        text(VERSION, f'"hw_profile": {{"key": "{KEY}", "key": "{KEY}", "record": 0}}'),
        text(VERSION, f'"hw_profile": {{"key": "{KEY}", "record": 0, "record": 0}}'),
        text(VERSION, SECTION.replace('"revision"', '"revision": "rev 1", "revision"')),
        text(VERSION, SECTION.replace('"cc"', '"cc": "1.0", "cc"')),
        text(VERSION, SECTION.replace('"cpu"', '"cpu": "cpu x", "cpu"')),
        text(VERSION, SECTION, '"example": {"a": 1, "a": 1}'),
        text(VERSION, SECTION, '"example": [0, [{"a": {"b": 1, "c": 2, "b": 3}}]]'),
        text('"schema_version": 2', '"example": {"a": 1, "a": 2}'),
        text('"schema_version": 2', '"schema_version": 2'),
    ],
)
def test_a_member_name_twice_in_any_object(content):
    message = invalid("content: cannot be read as one JSON text", parse, content)
    assert "a JSON object repeats a member name" in message


def test_nesting_too_deep_for_the_interpreter_is_reported():
    deep = '"example_member": ' + "[" * 2_000_000 + "]" * 2_000_000
    invalid(
        "content: is nested too deeply to parse", parse, text(VERSION, SECTION, deep)
    )


@pytest.mark.parametrize(
    "members",
    [
        (VERSION, SECTION, f'"example_member": {TOO_LONG_TEXT}'),
        (f'"schema_version": {TOO_LONG_TEXT}', SECTION),
        ('"schema_version": 2', f'"example_member": [-{TOO_LONG_TEXT}]'),
    ],
)
def test_an_integer_too_long_for_the_interpreter_is_reported(members):
    invalid("content: cannot be read as one JSON text", parse, text(*members))


# --- error / negative: schema_version ---


def test_schema_version_is_required():
    assert invalid("document: lacks", parse, raw(doc(schema_version=REMOVE))) == (
        "document: lacks the member schema_version"
    )
    invalid("document: lacks the member schema_version", validate, {})
    invalid("document: lacks the member schema_version", parse, b"{}")


@pytest.mark.parametrize(
    "value", [True, False, 1.0, 1.5, "1", "", None, [1], {"value": 1}, -1, -MAX, 2**53]
)
@pytest.mark.parametrize("hw_profile", [REMOVE, None, section()], ids=repr)
def test_a_schema_version_that_is_no_integer(value, hw_profile):
    document = doc(schema_version=value, hw_profile=hw_profile)
    expected = f"schema_version: must be an int from 0 to {MAX}, got "

    assert type(value).__name__ in invalid(expected, parse, raw(document))
    invalid(expected, validate, document)


@pytest.mark.parametrize("value", [TOO_LONG, -TOO_LONG], ids=["above", "below"])
def test_a_schema_version_too_long_to_show_is_still_named(value):
    assert invalid("schema_version: ", validate, doc(schema_version=value)) == (
        f"schema_version: must be an int from 0 to {MAX}, got int"
    )


@pytest.mark.parametrize("document", [None, [], "text", 1, (), raw(doc())])
def test_validate_refuses_what_is_no_object(document):
    invalid("document: must be an object, got ", validate, document)


# --- error / negative: hw_profile ---


def test_hw_profile_is_required():
    document = doc(hw_profile=REMOVE, hw_profiles=section(), example=1)

    assert invalid("document: ", parse, raw(document)) == (
        "document: lacks the member hw_profile"
    )
    invalid("document: lacks the member hw_profile", validate, document)


@pytest.mark.parametrize(
    "value", [None, [], [section()], "text", KEY, 7, 1.5, True], ids=repr
)
def test_a_hw_profile_that_is_no_object(value):
    document = doc(hw_profile=value)

    invalid("hw_profile: must be an object, got ", parse, raw(document))
    invalid("hw_profile: must be an object, got ", validate, document)


@pytest.mark.parametrize(
    ("place", "hw_profile"),
    [
        ("hw_profile: lacks the member key", {}),
        ("hw_profile: lacks the member key", section(key=REMOVE)),
        ("hw_profile: lacks the member record", section(record=REMOVE)),
        (
            "hw_profile: must be an object without the member, got str 'label'",
            section(label="x"),
        ),
        (
            "hw_profile: must be an object without the member, got str 'schema_version'",
            section(schema_version=1),
        ),
        (
            "hw_profile: must be an object without the member, got str 'schema_version'",
            record(),
        ),
        (
            "hw_profile: must be an object without the member, got str 'Key'",
            {"Key": KEY, "record": record()},
        ),
        ("hw_profile.key: must be a str, got int", section(key=7)),
        ("hw_profile.key: must be a str, got NoneType", section(key=None)),
        ("hw_profile.key: must be a str, got bool", section(key=True)),
        ("hw_profile.key: must be a str, got list", section(key=[KEY])),
        ("hw_profile.key: must be a str, got dict", section(key={"name": KEY})),
        ("hw_profile.record: must be an object, got NoneType", section(record=None)),
        ("hw_profile.record: must be an object, got list", section(record=[])),
        (
            "hw_profile.record: must be an object, got str 'text'",
            section(record="text"),
        ),
        ("hw_profile.record: must be an object, got str", section(record=KEY)),
        ("hw_profile.record: must be an object, got int", section(record=7)),
    ],
)
def test_a_hw_profile_that_is_not_the_closed_object(place, hw_profile):
    document = doc(hw_profile=hw_profile)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


@pytest.mark.parametrize(
    "key",
    [
        "",
        " ",
        OTHER_KEY,
        key_of(record(revision="rev 2")),
        mock_backend.NAME,
        KEY.upper(),
        KEY[:-1],
        KEY + "0",
        " " + KEY,
        KEY + "\n",
        KEY.replace("-", "_"),
        keys.hw_profile_key(record()).digest,
        "../" + KEY,
    ],
)
def test_a_key_that_is_not_the_name_derived_from_the_record(key):
    document = doc(hw_profile=section(key=key))
    expected = f"hw_profile.key: must be {KEY}, the name derived from hw_profile.record"

    assert invalid(expected, parse, raw(document)).endswith(
        f", got str {reprlib.repr(key)}"
    )
    invalid(expected, validate, document)


def test_a_change_of_an_attribute_keeps_the_key_and_one_of_a_key_field_does_not():
    assert parse(raw(doc(hw_profile=section(record=record(label="x"))))).hw_profile == (
        record(label="x")
    )
    invalid(
        "hw_profile.key: must be ",
        parse,
        raw(doc(hw_profile=section(record=record(revision="rev 2")))),
    )


@pytest.mark.parametrize(
    ("place", "profile"),
    [
        ("hw_profile.record.accelerator: required", record(accelerator=REMOVE)),
        ("hw_profile.record.schema_version: required", record(schema_version=REMOVE)),
        ("hw_profile.record.hw_source: required", record(hw_source=REMOVE)),
        ("hw_profile.record.schema_version: required", {}),
        ("hw_profile.record.schema_version: must be", record(schema_version=2)),
        ("hw_profile.record.schema_version: must be", record(schema_version=True)),
        ("hw_profile.record.accelerator: must be a name", record("Mock")),
        ("hw_profile.record.accelerator: must be a name", record(7)),
        ("hw_profile.record.revision: must be a string", record(revision=7)),
        ("hw_profile.record.revision: must be a string", record(revision="")),
        ("hw_profile.record.revision: must be a string", record(revision="rév")),
        ("hw_profile.record.toolchain: must be a map", record(toolchain=[])),
        ("hw_profile.record.toolchain: must be a map with", record(toolchain={})),
        ("hw_profile.record.toolchain.cc: must be", record(toolchain={"cc": 1})),
        (
            "hw_profile.record.toolchain: member name",
            record(toolchain={"CC": "1.0"}),
        ),
        ("hw_profile.record.host.cpu: required", record(host={"os": "os y"})),
        (
            "hw_profile.record.host.os: must be",
            record(host={"cpu": "c", "os": 1.5}),
        ),
        (
            "hw_profile.record.host.cpu: must be",
            record(host={"cpu": 2**53, "os": "o"}),
        ),
        ("hw_profile.record.ext: must be", record(ext={})),
        ("hw_profile.record.ext.example: must be", record(ext={"example": None})),
        ("hw_profile.record.label: must be", record(label="")),
        ("hw_profile.record.hw_source: must be", record(hw_source="NOT-DECIDED-HERE")),
        ("hw_profile.record.hw_source: must be", record(hw_source=None)),
        ("hw_profile.record.'example': unknown field", record(example=1)),
        ("hw_profile.record.'key': unknown field", record(key=KEY)),
    ],
)
@pytest.mark.parametrize("key", [KEY, OTHER_KEY, ""])
def test_a_record_that_is_not_valid_by_adr_0001(place, profile, key):
    document = doc(hw_profile={"key": key, "record": profile})

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


def test_the_example_of_adr_0018_is_not_a_valid_file():
    message = invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE)
    assert "external or in_house" in message

    source = b'"hw_source": "NOT-DECIDED-HERE"'
    result = parse(EXAMPLE.replace(source, b'"hw_source": "in_house"'))
    assert result.hw_profile_key == "cpu_standin-b0d8610d8f470856"
    assert result.hw_profile["accelerator"] == "cpu_standin"


@pytest.mark.parametrize(
    ("place", "hw_profile"),
    [
        ("hw_profile: must be an object without", {"example": 1}),
        ("hw_profile: must be an object without", {"key": 7, "example": 1}),
        ("hw_profile: lacks the member key", {"record": None}),
        ("hw_profile: lacks the member record", {"key": 7}),
        ("hw_profile.key: must be a str", {"key": 7, "record": None}),
        ("hw_profile.key: must be a str", {"key": 7, "record": record("Mock")}),
        ("hw_profile.record: must be an object", {"key": "", "record": None}),
        ("hw_profile.record.accelerator", {"key": "", "record": record("Mock")}),
    ],
)
def test_the_first_broken_rule_of_a_hw_profile_is_reported(place, hw_profile):
    invalid(place, validate, doc(hw_profile=hw_profile))


def test_nothing_is_modified_by_a_check():
    document = doc(example={"a": [1]})
    before = json.dumps(document)

    validate(document)
    for broken in (doc(hw_profile=section(key="")), doc(schema_version=2)):
        kept = json.dumps(broken)
        with pytest.raises((InvalidInstanceError, UnsupportedVersionError)):
            validate(broken)
        assert json.dumps(broken) == kept

    assert json.dumps(document) == before


# --- happy: the member tolerance (ADR-0020) ---


def stated(rtol, atol, *more):
    member = f'"tolerance": {{"rtol": {rtol}, "atol": {atol}}}'
    return text(VERSION, SECTION, member, *more)


def test_a_content_with_the_member_states_the_two_values():
    result = parse(raw(doc(tolerance=TOLERANCE, example=[1])))

    assert result == Instance(
        KEY, record(), Tolerance(TEST_RTOL, TEST_ATOL), {"example": [1]}
    )
    assert type(result.tolerance) is Tolerance
    assert (result.tolerance.rtol, result.tolerance.atol) == (TEST_RTOL, TEST_ATOL)
    assert "tolerance" not in result.others
    assert validate(doc(tolerance=TOLERANCE, example=[1])) is None


def test_a_content_without_the_member_states_no_tolerance():
    result = parse(raw(doc()))

    assert result.tolerance is None
    assert (result.hw_profile_key, result.hw_profile) == (KEY, record())
    assert result[:2] == parse(raw(doc(tolerance=TOLERANCE)))[:2]


ZERO_LITERALS = ["0", "0.0", "-0", "-0.0", "-1e-999", "1e-999", "0e5"]
LITERALS = [
    "0.001",
    "1e-5",
    "1E-5",
    "2",
    "1.7976931348623158e308",
    "5e-324",
    str(2**1023),
    *ZERO_LITERALS,
]


@pytest.mark.parametrize("literal", LITERALS)
def test_a_number_literal_is_handed_out_as_its_float(literal):
    expected = 0.0 if literal in ZERO_LITERALS else float(literal)
    assert math.isfinite(expected) and (expected > 0) == (literal not in ZERO_LITERALS)

    for content, found in (
        (stated(literal, TEST_ATOL), Tolerance(expected, TEST_ATOL)),
        (stated(TEST_RTOL, literal), Tolerance(TEST_RTOL, expected)),
        (stated(literal, literal), Tolerance(expected, expected)),
    ):
        result = parse(content).tolerance
        assert result == found
        assert [type(value) for value in result] == [float, float]
        assert [math.copysign(1.0, value) for value in result] == [1.0, 1.0]
        assert validate(json.loads(content)) is None


def test_both_values_may_be_zero_and_neither_bounds_the_other():
    assert parse(stated(0, 0)).tolerance == Tolerance(0.0, 0.0)
    assert parse(stated(0, 1e300)).tolerance == Tolerance(0.0, 1e300)
    assert parse(stated(1e300, 0)).tolerance == Tolerance(1e300, 0.0)


def test_a_minus_zero_built_in_memory_is_handed_out_as_zero():
    document = doc(tolerance={"rtol": -0.0, "atol": 0})

    assert validate(document) is None
    result = parse(raw(document)).tolerance
    assert [math.copysign(1.0, value) for value in result] == [1.0, 1.0]
    assert [type(value) for value in result] == [float, float]


@pytest.mark.parametrize(
    "content",
    [
        text(VERSION, SECTION, '"tolerance": {"atol": 3.0, "rtol": 0.25}'),
        text('"tolerance": {"atol": 3.0, "rtol": 0.25}', SECTION, VERSION),
        text(VERSION, '"tolerance":{"rtol":0.25,"atol":3.0}', SECTION),
        text(VERSION, SECTION, '"tolerance" : {\n "rtol" : 25e-2,\r\n\t"atol" : 3 }'),
    ],
)
def test_any_order_of_the_members_of_a_tolerance(content):
    result = parse(content)

    assert result == Instance(KEY, record(), Tolerance(TEST_RTOL, TEST_ATOL), {})


def test_the_member_of_the_example_of_adr_0020():
    result = parse(stated("1e-4", "0.01"))

    assert result.tolerance == Tolerance(0.0001, 0.01)


# --- branch: the member tolerance ---

BROKEN_TOLERANCES = [None, 0.1, [], {}, {"rtol": TEST_RTOL}, {"rel": "broken"}]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("tolerance", [*BROKEN_TOLERANCES, TOLERANCE], ids=repr)
def test_another_version_is_reported_before_a_tolerance_is_looked_at(
    version, tolerance
):
    document = doc(schema_version=version, tolerance=tolerance)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"tolerence": TOLERANCE},
        {"tolerances": TOLERANCE},
        {"Tolerance": TOLERANCE},
        {"tolerance ": {"rel": "broken"}},
        {"rtol": TEST_RTOL, "atol": TEST_ATOL},
        {"rtol": -1, "atol": "broken", "tolerence": 0.1},
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_tolerance(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(KEY, record(), None, others)
    assert validate(doc(**others)) is None

    result = parse(raw(doc(tolerance=TOLERANCE, **others)))
    assert result.tolerance == Tolerance(TEST_RTOL, TEST_ATOL)
    assert result.others == others


NO_MEMBER = "tolerance: must be an object without the member, got str "
NO_NUMBER = ": must be a finite number that is not negative, got "


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "tolerance": None}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "tolerance": 1},
        ),
        ("hw_profile.key: ", {"hw_profile": section(key=OTHER_KEY), "tolerance": {}}),
        (NO_MEMBER + "'x'", {"tolerance": {"x": 1}}),
        (NO_MEMBER + "'x'", {"tolerance": {"rtol": -1, "x": 1}}),
        (NO_MEMBER + "'x'", {"tolerance": {"rtol": -1, "atol": -1, "x": 1}}),
        ("tolerance: lacks the member rtol", {"tolerance": {}}),
        ("tolerance: lacks the member rtol", {"tolerance": {"atol": -1}}),
        ("tolerance: lacks the member atol", {"tolerance": {"rtol": "broken"}}),
        ("tolerance.rtol" + NO_NUMBER, {"tolerance": {"rtol": -1, "atol": -1}}),
        ("tolerance.rtol" + NO_NUMBER, {"tolerance": {"atol": None, "rtol": None}}),
    ],
)
def test_the_first_broken_rule_is_reported_with_a_tolerance(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member tolerance ---


@pytest.mark.parametrize(
    "value", [None, 0.1, 1, 0, "0.1", "", [TEST_RTOL, TEST_ATOL], [], True, False]
)
def test_a_tolerance_that_is_no_object(value):
    document = doc(tolerance=value)
    expected = f"tolerance: must be an object, got {type(value).__name__}"

    invalid(expected, parse, raw(document))
    invalid(expected, validate, document)


@pytest.mark.parametrize(
    "place, tolerance",
    [
        ("tolerance: lacks the member rtol", {}),
        ("tolerance: lacks the member atol", {"rtol": TEST_RTOL}),
        ("tolerance: lacks the member rtol", {"atol": TEST_ATOL}),
        (NO_MEMBER + "'kind'", {**TOLERANCE, "kind": "example"}),
        (NO_MEMBER + "''", {**TOLERANCE, "": 1}),
        (NO_MEMBER + "'atoll'", {"rtol": TEST_RTOL, "atoll": TEST_ATOL}),
        (NO_MEMBER + "'Rtol'", {"Rtol": TEST_RTOL, "atol": TEST_ATOL}),
        (NO_MEMBER + "'rel'", {"rel": "broken"}),
        (NO_MEMBER + "'rtol '", {"rtol ": TEST_RTOL, "atol": TEST_ATOL}),
    ],
)
def test_a_tolerance_that_is_not_the_closed_object(place, tolerance):
    document = doc(tolerance=tolerance)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


NO_NUMBERS = [
    True,
    False,
    None,
    "1e-4",
    "",
    [1e-4],
    {"value": 1e-4},
    -1,
    -1e-9,
    -0.5,
    -5e-324,
    10**400,
    -(10**400),
    2**1024,
]


@pytest.mark.parametrize("name", ["rtol", "atol"])
@pytest.mark.parametrize("value", NO_NUMBERS, ids=shown)
def test_a_value_that_is_no_finite_number_that_is_not_negative(name, value):
    document = doc(tolerance={**TOLERANCE, name: value})
    expected = f"tolerance.{name}{NO_NUMBER}{type(value).__name__}"

    invalid(expected, parse, raw(document))
    invalid(expected, validate, document)


@pytest.mark.parametrize("literal", ["1e999", "-1e999", "1" + "0" * 400, "1.8e308"])
def test_a_literal_no_float_holds_is_never_read_as_an_infinity(literal):
    invalid("tolerance.rtol" + NO_NUMBER, parse, stated(literal, 0))
    invalid("tolerance.atol" + NO_NUMBER, parse, stated(0, literal))


@pytest.mark.parametrize(
    "content",
    [
        stated("NaN", 0),
        stated(0, "Infinity"),
        stated("-Infinity", 0),
        stated(0, TOO_LONG_TEXT),
    ],
)
def test_a_tolerance_that_is_no_json(content):
    invalid("content: cannot be read as one JSON text", parse, content)


@pytest.mark.parametrize(
    "member",
    [
        '"tolerance": {"rtol": 0.25, "atol": 3.0, "rtol": 0.25}',
        '"tolerance": {"rtol": 0.25, "atol": 3.0, "atol": 3.0}',
        '"tolerance": {"rtol": 0.25, "atol": 3.0}, "tolerance": {"rtol": 0.25, "atol": 3.0}',
    ],
)
def test_a_member_name_twice_with_a_tolerance(member):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, member),
    )
    assert "a JSON object repeats a member name" in message


class Number(float):
    """A test-only subclass: not exactly a ``float``."""


@pytest.mark.parametrize("name", ["rtol", "atol"])
@pytest.mark.parametrize(
    "value",
    [float("inf"), float("-inf"), float("nan"), True, False, TOO_LONG, Number(0.5)],
    ids=shown,
)
def test_validate_refuses_a_value_built_in_memory(name, value):
    document = doc(tolerance={**TOLERANCE, name: value})

    message = invalid(f"tolerance.{name}{NO_NUMBER}", validate, document)
    assert message.endswith(f"got {type(value).__name__}")


@pytest.mark.parametrize(
    "tolerance",
    [
        '{"rtol": 1e-4}',
        '{"rtol": -1, "atol": 0}',
        '{"rtol": "1e-4", "atol": 0}',
        '{"rtol": 1e999, "atol": 0}',
        '{"rtol": 1e-4, "atol": 0.01, "example": 1}',
    ],
)
def test_the_invalid_files_of_the_walk_through_of_adr_0020(tolerance):
    invalid("tolerance", parse, text(VERSION, SECTION, f'"tolerance": {tolerance}'))


# --- with the harness: the same rule for a value ---

VALUES = [
    0,
    0.0,
    -0.0,
    1,
    2.5,
    1e-5,
    5e-324,
    sys.float_info.max,
    2**1023,
    *NO_NUMBERS,
    float("inf"),
    float("-inf"),
    float("nan"),
    TOO_LONG,
    Number(0.5),
]


def accepted(function, *arguments):
    try:
        function(*arguments)
    except (InvalidInstanceError, verification_arrays.VerificationArgumentError):
        return False
    return True


@pytest.mark.parametrize("rtol", VALUES, ids=shown)
def test_a_pair_is_valid_here_exactly_when_check_tolerance_accepts_it(rtol):
    for atol in VALUES:
        here = accepted(validate, doc(tolerance={"rtol": rtol, "atol": atol}))
        there = accepted(verification_arrays.check_tolerance, rtol, atol)
        assert here == there, (rtol, atol)
        assert here == all(
            any(value is valid for valid in VALUES[:9]) for value in (rtol, atol)
        )


def test_the_module_imports_neither_numpy_nor_the_harness():
    code = (
        "import sys, hilclaw.instance; "
        "print(sorted(name for name in sys.modules "
        "if name.split('.')[0] == 'numpy' or name.startswith('hilclaw.harness')))"
    )

    done = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert done.stdout.strip() == "[]"


def test_nothing_of_the_module_holds_a_tolerance_value():
    numbers = {
        name: value
        for name, value in vars(instance).items()
        if type(value) in (int, float, Tolerance)
    }

    assert numbers == {"SCHEMA_VERSION": 1, "_MAX": MAX}


# --- happy: the reader ---


def test_the_reader_returns_the_record_the_file_embeds(tmp_path, root):
    content = raw(doc(example=[1, 2]))
    place(root, content)
    before = snapshot(tmp_path)

    found = hw_profile_of(root, RUN)

    assert found == record() and type(found) is dict
    assert key_of(found) == KEY == read(root, RUN).hw_profile_key
    assert (
        read(root, RUN)
        == parse(content)
        == Instance(KEY, record(), None, {"example": [1, 2]})
    )
    assert type(read(root, RUN)) is Instance
    assert snapshot(tmp_path) == before


def test_each_call_returns_new_objects(root):
    place(root, raw(doc(example={})))

    first, second = read(root, RUN), read(root, RUN)
    assert first == second
    assert first.hw_profile is not second.hw_profile
    assert first.others is not second.others
    assert hw_profile_of(root, RUN) is not hw_profile_of(root, RUN)

    hw_profile_of(root, RUN)["accelerator"] = "changed"
    assert hw_profile_of(root, RUN) == record()


def test_a_data_root_given_as_a_str_and_a_relative_one(root, monkeypatch):
    place(root, raw(doc()))

    assert hw_profile_of(str(root), RUN) == record()
    monkeypatch.chdir(root.parent)
    assert hw_profile_of(root.name, RUN) == record()
    assert read(Path(root.name), RUN).hw_profile_key == KEY


# --- branch: nothing kept, only this file ---


def test_a_file_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc()))
    assert hw_profile_of(root, RUN) == record()

    place(root, raw(doc(OTHER_RECORD)))
    assert hw_profile_of(root, RUN) == OTHER_RECORD
    assert read(root, RUN).hw_profile_key == OTHER_KEY

    place(root, b"")
    invalid(f"{FILE}: content: ", hw_profile_of, root, RUN)

    place(root, raw(doc()))
    assert hw_profile_of(root, RUN) == record()


def test_two_runs_under_one_data_root(root):
    place(root, raw(doc()))
    place(root, raw(doc(OTHER_RECORD)), f"runs/{OTHER_RUN}/instance.json")

    assert hw_profile_of(root, RUN) == record()
    assert hw_profile_of(root, OTHER_RUN) == OTHER_RECORD
    assert hw_profile_of(root, RUN) == record()


def test_no_other_file_of_the_run_is_needed(root):
    place(root, raw(doc()))

    assert sorted(path.name for path in root.rglob("*")) == [
        "instance.json",
        "run-a",
        "runs",
    ]
    assert hw_profile_of(root, RUN) == record()


@pytest.mark.parametrize(
    "stored",
    [
        json.dumps(record(label="changed since", hw_source="in_house")).encode(),
        json.dumps(record(revision="another")).encode(),
        b"",
        b"not JSON",
        None,
    ],
)
def test_the_stored_record_of_the_key_is_not_read_or_compared(tmp_path, root, stored):
    place(root, raw(doc()))
    place(root, b"not a state", f"runs/{RUN}/STATE.json")
    place(root, b"not a log", f"runs/{RUN}/events.ndjson")
    if stored is None:
        layout.hw_profile_dir(root, KEY).mkdir(parents=True)
    else:
        place(root, stored, layout.hw_profile_record(root, KEY).relative_to(root))
    before = snapshot(tmp_path)

    assert hw_profile_of(root, RUN) == record()
    assert snapshot(tmp_path) == before


def test_only_the_instance_file_is_opened(root, monkeypatch):
    place(root, raw(doc()))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    place(root, json.dumps(record()).encode(), f"db/{KEY}/hw_profile.json")
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert hw_profile_of(root, RUN) == record()
    assert opened == [FILE]


# --- the reader of the tolerance ---


def test_the_reader_returns_the_tolerance_the_file_states(tmp_path, root):
    place(root, raw(doc(tolerance=TOLERANCE, example=[1])))
    before = snapshot(tmp_path)

    found = tolerance_of(root, RUN)

    assert found == Tolerance(TEST_RTOL, TEST_ATOL) and type(found) is Tolerance
    assert found == read(root, RUN).tolerance
    assert tolerance_of(str(root), RUN) == found
    assert hw_profile_of(root, RUN) == record()
    assert snapshot(tmp_path) == before


def test_a_run_without_the_member_states_no_tolerance(tmp_path, root):
    place(root, raw(doc(tolerence=TOLERANCE, rtol=TEST_RTOL, atol=TEST_ATOL)))
    before = snapshot(tmp_path)

    assert tolerance_of(root, RUN) is None
    assert read(root, RUN).tolerance is None
    assert hw_profile_of(root, RUN) == record()
    assert snapshot(tmp_path) == before


def test_a_tolerance_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(tolerance=TOLERANCE)))
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)

    place(root, raw(doc(tolerance=OTHER_TOLERANCE)))
    assert tolerance_of(root, RUN) == Tolerance(OTHER_TEST_RTOL, OTHER_TEST_ATOL)

    place(root, raw(doc()))
    assert tolerance_of(root, RUN) is None

    place(root, raw(doc(tolerance={"rtol": TEST_RTOL})))
    invalid(f"{FILE}: tolerance: lacks the member atol", tolerance_of, root, RUN)
    invalid(f"{FILE}: tolerance: lacks the member atol", hw_profile_of, root, RUN)
    invalid(f"{FILE}: tolerance: lacks the member atol", read, root, RUN)

    place(root, raw(doc(schema_version=2, tolerance=TOLERANCE)))
    with pytest.raises(UnsupportedVersionError):
        tolerance_of(root, RUN)

    place(root, raw(doc(tolerance=TOLERANCE)))
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)


def test_two_runs_state_their_own_tolerances(root):
    place(root, raw(doc(tolerance=TOLERANCE)))
    place(root, raw(doc(tolerance=OTHER_TOLERANCE)), f"runs/{OTHER_RUN}/instance.json")
    place(root, raw(doc()), "runs/run-c/instance.json")

    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert tolerance_of(root, OTHER_RUN) == Tolerance(OTHER_TEST_RTOL, OTHER_TEST_ATOL)
    assert tolerance_of(root, "run-c") is None
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)


def test_each_call_returns_a_new_tolerance(root):
    place(root, raw(doc(tolerance=TOLERANCE)))

    first, second = tolerance_of(root, RUN), tolerance_of(root, RUN)

    assert first == second and first is not second
    assert read(root, RUN).tolerance is not read(root, RUN).tolerance


def test_the_reader_of_the_tolerance_opens_only_the_instance_file(root, monkeypatch):
    place(root, raw(doc(tolerance=TOLERANCE)))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert opened == [FILE]


# --- error / negative: the four situations of decision 4 ---


def absent(root):
    pass


def no_run_directory(root):
    place(root, raw(doc()), f"runs/{OTHER_RUN}/instance.json")


def a_run_directory_without_the_file(root):
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    place(root, b"", f"runs/{RUN}/events.ndjson")
    place(root, raw(doc()), f"runs/{RUN}/rounds/instance.json")


def a_file_in_the_place_of_the_run_directory(root):
    place(root, raw(doc()), f"runs/{RUN}")


def a_file_in_the_place_of_runs(root):
    place(root, raw(doc()), "runs")


MISSING = [
    absent,
    no_run_directory,
    a_run_directory_without_the_file,
    a_file_in_the_place_of_the_run_directory,
    a_file_in_the_place_of_runs,
]


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
@pytest.mark.parametrize("build", MISSING)
def test_a_missing_file(tmp_path, root, call, build):
    build(root)
    before = snapshot(tmp_path)

    with pytest.raises(MissingInstanceError) as caught:
        call(root, RUN)

    assert str(caught.value) == (
        f"{FILE}: is missing: no instance record was written for this run_id"
    )
    assert not isinstance(caught.value, (ToolFailure, OSError, ValueError))
    assert snapshot(tmp_path) == before


INVALID_FILES = {
    "empty": (b"", "content: cannot be read as one JSON text"),
    "white space": (b"\n", "content: cannot be read as one JSON text"),
    "partial": (raw(doc())[:40], "content: cannot be read as one JSON text"),
    "a byte order mark": (b"\xef\xbb\xbf" + raw(doc()), "content: starts with"),
    "no version": (raw(doc(schema_version=REMOVE)), "document: lacks the member"),
    "no hw_profile": (raw(doc(hw_profile=REMOVE)), "document: lacks the member"),
    "a third member": (raw(doc(hw_profile=section(x=1))), "hw_profile: must be"),
    "another key": (raw(doc(hw_profile=section(key=OTHER_KEY))), "hw_profile.key: "),
    "the example of the record": (EXAMPLE, "hw_profile.record.hw_source: must be"),
    "a tolerance that is no object": (raw(doc(tolerance=0.1)), "tolerance: must be"),
    "a tolerance with one value": (
        raw(doc(tolerance={"rtol": TEST_RTOL})),
        "tolerance: lacks the member atol",
    ),
    "a negative tolerance": (
        raw(doc(tolerance={"rtol": TEST_RTOL, "atol": -1})),
        "tolerance.atol: must be",
    ),
}


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
@pytest.mark.parametrize("case", INVALID_FILES)
def test_an_invalid_file_is_named_by_its_relative_path(tmp_path, root, call, case):
    content, reason = INVALID_FILES[case]
    place(root, content)
    before = snapshot(tmp_path)

    message = invalid(f"{FILE}: {reason}", call, root, RUN)

    assert str(root) not in message
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
@pytest.mark.parametrize("version", [0, 2, MAX])
def test_a_file_of_another_version(root, call, version):
    place(root, raw(doc(schema_version=version, hw_profile=REMOVE)))

    with pytest.raises(UnsupportedVersionError) as caught:
        call(root, RUN)

    assert str(caught.value) == f"{FILE}: schema_version: {version} is not supported"
    assert not isinstance(caught.value, (ToolFailure, ValueError, OSError))


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
@pytest.mark.parametrize(
    "error", [PermissionError("denied"), OSError("example"), FileNotFoundError("gone")]
)
def test_an_os_error_while_the_file_is_read_passes_through(
    root, call, monkeypatch, error
):
    place(root, raw(doc()))

    def fail(path):
        raise error

    monkeypatch.setattr(Path, "read_bytes", fail)

    with pytest.raises(OSError) as caught:
        call(root, RUN)
    assert caught.value is error
    assert not isinstance(caught.value, ToolFailure)


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
def test_a_file_that_cannot_be_examined_passes_the_os_error_through(
    root, call, monkeypatch
):
    place(root, raw(doc()))
    error = PermissionError("denied")

    def fail(path):
        raise error

    monkeypatch.setattr(instance.os, "lstat", fail)

    with pytest.raises(PermissionError) as caught:
        call(root, RUN)
    assert caught.value is error


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
def test_a_directory_in_the_place_of_the_file(tmp_path, root, call):
    (root / FILE).mkdir(parents=True)
    before = snapshot(tmp_path)

    assert invalid(FILE, call, root, RUN) == f"{FILE}: is not a regular file"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
@pytest.mark.parametrize("target", ["a file", "nothing"])
def test_a_symbolic_link_in_the_place_of_the_file(tmp_path, root, call, target):
    elsewhere = tmp_path / "elsewhere.json"
    if target == "a file":
        elsewhere.write_bytes(raw(doc()))
    link(root / FILE, elsewhere)

    assert invalid(FILE, call, root, RUN) == f"{FILE}: is not a regular file"
    assert elsewhere.exists() == (target == "a file")


# --- error / negative: arguments ---


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
@pytest.mark.parametrize(
    "run_id", ["", "Run-A", "../run-a", "a/b", ".", "a" * 65, None, 1, b"run-a"]
)
def test_an_invalid_run_id_is_refused_before_the_file_system(tmp_path, call, run_id):
    for data_root in (tmp_path, tmp_path / "absent"):
        with pytest.raises(layout.InvalidPathValueError, match="^run_id: must be"):
            call(data_root, run_id)
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
def test_a_data_root_that_does_not_exist(tmp_path, call):
    with pytest.raises(FileNotFoundError, match="data root is not an existing"):
        call(tmp_path / "absent", RUN)
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("call", [read, hw_profile_of, tolerance_of])
def test_a_file_in_the_place_of_the_data_root(tmp_path, call):
    (tmp_path / "data").write_bytes(raw(doc()))

    with pytest.raises(NotADirectoryError, match="data root is not an existing"):
        call(tmp_path / "data", RUN)


# --- with hilclaw.hw_tool: the reader handed over as it is ---


class Tool:
    """A test-only journaled HW tool whose reader is the one of the module."""

    def __init__(self, root, offered=(TOOL,), reader=hw_profile_of):
        self.asked, self.performed = [], 0
        self.table = BackendTable([mock_backend.backend(self.script, offered)])
        self.function = hw_tool.tool_function(
            tool=TOOL,
            step=STEP,
            numbers=("round", "candidate", "attempt"),
            source=lambda: root,
            table=self.table,
            hw_profile_of=reader,
            check=lambda request: None,
            perform=self.perform,
        )
        self.registry = Registry()
        self.registry.register(
            TOOL, self.function, "A HW tool of the tests.", {"type": "object"}
        )

    def perform(self, data_root, request, hw_profile, operation):
        self.performed += 1
        return SPEND, operation(request, hw_profile)

    def script(self, tool, request, hw_profile):
        self.asked.append((tool, request, hw_profile))
        return {"example_member": request["execution"]}


def by_call(tool, asked):
    try:
        return False, tools.call(tool.registry, TOOL, asked)
    except ToolFailure as failure:
        return True, failure.error_object()


def by_command_line(tool, asked):
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = command_line.main(
        [TOOL],
        registry=tool.registry,
        stdin=io.BytesIO(json.dumps(asked).encode()),
        stdout=stdout,
        stderr=stderr,
    )
    assert status in (0, 3)
    return status == 3, json.loads(stdout.getvalue())


def by_mcp(tool, asked):
    params = {"name": TOOL.replace(".", "_"), "arguments": asked}
    document = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": params}
    stdout, stderr = io.BytesIO(), io.BytesIO()
    status = mcp_front.main(
        [],
        registry=tool.registry,
        stdin=io.BytesIO(json.dumps(document).encode() + b"\n"),
        stdout=stdout,
        stderr=stderr,
    )
    assert (status, stderr.getvalue()) == (0, b"")
    answer = json.loads(stdout.getvalue())
    (block,) = answer["result"]["content"]
    return answer["result"]["isError"], json.loads(block["text"])


THROUGH_CALL = {"call": by_call, "cli": by_command_line, "mcp": by_mcp}


def started(root, run=RUN):
    place(root, run_state.dump(3, EMPTY), f"runs/{run}/STATE.json")
    return root


def kinds(root, run=RUN):
    return [line["kind"] for line in events.read(root, run).events]


UNUSABLE = {
    "missing": (None, MissingInstanceError, "run_file_missing"),
    "empty": (b"", InvalidInstanceError, "run_file_invalid"),
    "partial": (raw(doc())[:40], InvalidInstanceError, "run_file_invalid"),
    "a hw_profile that breaks decision 3": (
        raw(doc(hw_profile=section(key=OTHER_KEY))),
        InvalidInstanceError,
        "run_file_invalid",
    ),
    "another version": (
        raw(doc(schema_version=2)),
        UnsupportedVersionError,
        "run_file_unsupported",
    ),
}


def assert_no_step_started(tool, root, kind, cause, message):
    before = snapshot(root)
    with pytest.raises(ToolFailure) as caught:
        tool.function(dict(REQUEST))
    assert caught.value.kind == kind
    assert type(caught.value.__cause__) is cause
    assert caught.value.message.startswith(f"{FILE}: {message}")
    assert str(root) not in caught.value.message
    for way in THROUGH_CALL.values():
        assert way(tool, REQUEST) == (True, caught.value.error_object())
    assert (tool.asked, tool.performed) == ([], 0)
    assert snapshot(root) == before


@pytest.mark.parametrize("way", THROUGH_CALL)
def test_a_first_call_selects_the_backend_of_the_embedded_record(root, way):
    profile = record(label="of this run")
    place(started(root), raw(doc(profile)))
    tool = Tool(root)

    assert THROUGH_CALL[way](tool, REQUEST) == (False, {"example_member": 1})

    assert kinds(root) == ["step_started", "step_ended"]
    ((called, asked, seen),) = tool.asked
    assert (called, asked, seen) == (TOOL, REQUEST, profile)
    assert tool.performed == 1


def test_an_ended_identity_is_answered_after_the_file_was_removed(root):
    path = place(started(root), raw(doc()))
    tool = Tool(root)
    assert tool.function(dict(REQUEST)) == {"example_member": 1}

    path.unlink()

    for way in THROUGH_CALL.values():
        assert way(tool, REQUEST) == (False, {"example_member": 1})
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert (len(tool.asked), tool.performed) == (1, 1)
    with pytest.raises(ToolFailure) as caught:
        tool.function({**REQUEST, "execution": 2})
    assert caught.value.kind == tools.KIND_RUN_FILE_MISSING == "run_file_missing"
    assert kinds(root) == ["step_started", "step_ended"]


@pytest.mark.parametrize("case", UNUSABLE)
def test_a_run_whose_hw_profile_cannot_be_had_starts_no_step(root, case):
    content, error, kind = UNUSABLE[case]
    started(root)
    if content is not None:
        place(root, content)
    tool = Tool(root)

    assert_no_step_started(tool, root, kind, error, "")

    place(root, raw(doc()))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)


def test_a_directory_in_the_place_of_the_file_is_run_file_invalid(root):
    (started(root) / FILE).mkdir()

    assert_no_step_started(
        Tool(root),
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "is not a regular file",
    )


def failing_at_the_bytes(monkeypatch, read_bytes):
    """The reader of the module, with ``Path.read_bytes`` replaced during its call only."""

    def reader(data_root, run_id):
        with monkeypatch.context() as patch:
            patch.setattr(Path, "read_bytes", read_bytes)
            return hw_profile_of(data_root, run_id)

    return reader


def test_a_file_that_cannot_be_read_is_run_file_unreadable(root, monkeypatch):
    place(started(root), raw(doc()))

    def read_bytes(path):
        raise PermissionError(13, "Permission denied", str(path))

    assert_no_step_started(
        Tool(root, reader=failing_at_the_bytes(monkeypatch, read_bytes)),
        root,
        "run_file_unreadable",
        PermissionError,
        "could not be read: PermissionError: Permission denied",
    )

    assert Tool(root).function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]


def test_a_file_gone_between_the_check_and_the_read_is_run_file_missing(
    root, monkeypatch
):
    place(started(root), raw(doc()))

    def read_bytes(path):
        raise FileNotFoundError(2, "No such file or directory", str(path))

    assert_no_step_started(
        Tool(root, reader=failing_at_the_bytes(monkeypatch, read_bytes)),
        root,
        "run_file_missing",
        FileNotFoundError,
        "is missing",
    )


def test_a_data_root_gone_at_the_call_of_the_reader_is_run_file_missing(root):
    state = started(root) / f"runs/{RUN}/STATE.json"

    def reader(data_root, run_id):
        state.unlink()
        for directory in (state.parent, state.parent.parent, root):
            directory.rmdir()
        return hw_profile_of(data_root, run_id)

    tool = Tool(root, reader=reader)

    with pytest.raises(ToolFailure) as caught:
        tool.function(dict(REQUEST))
    gone = f"{FILE}: is missing: the data root is not an existing directory"
    assert (caught.value.kind, caught.value.message) == ("run_file_missing", gone)
    assert type(caught.value.__cause__) is FileNotFoundError
    assert (tool.asked, tool.performed) == ([], 0)
    assert not root.exists()
    for way in THROUGH_CALL.values():
        failed, answer = way(tool, REQUEST)
        assert (failed, answer["error"]["kind"]) == (True, tools.KIND_NO_DATA_ROOT)


def test_each_run_selects_by_its_own_file(root):
    place(started(root), raw(doc()))
    place(
        started(root, OTHER_RUN),
        raw(doc(OTHER_RECORD)),
        f"runs/{OTHER_RUN}/instance.json",
    )
    tool = Tool(root)

    failed, answer = by_call(tool, {**REQUEST, "run_id": OTHER_RUN})
    assert (failed, answer["error"]["kind"]) == (True, tools.KIND_NO_BACKEND)
    assert kinds(root, OTHER_RUN) == []
    assert by_call(tool, REQUEST) == (False, {"example_member": 1})

    place(root, raw(doc()), f"runs/{OTHER_RUN}/instance.json")
    assert by_call(tool, {**REQUEST, "run_id": OTHER_RUN}) == (
        False,
        {"example_member": 1},
    )
    assert [seen for _, _, seen in tool.asked] == [record(), record()]


@pytest.mark.parametrize(
    "repaired", [doc(), doc(tolerance=TOLERANCE)], ids=["removed", "valid"]
)
def test_a_file_invalid_by_its_tolerance_alone_is_run_file_invalid(root, repaired):
    place(started(root), raw(doc(tolerance={"rtol": TEST_RTOL})))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "tolerance: lacks the member atol",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]
