import ast
import datetime
import getpass
import inspect
import io
import itertools
import json
import math
import os
import re
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
from hilclaw.harness import measurement, verification_arrays
from hilclaw.instance import (
    SCHEMA_VERSION,
    Instance,
    InvalidInstanceError,
    MissingInstanceError,
    OpSignature,
    Tolerance,
    UnsupportedVersionError,
    candidates_per_round_of,
    hw_profile_of,
    layout_version_of,
    n_max_of,
    op_signature_of,
    owner_of,
    parse,
    project_of,
    read,
    round_budget_of,
    source_commit_of,
    tolerance_of,
    validate,
    wall_clock_budget_s_of,
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
# Made-up object names: the placeholder of the Example of ADR-0022 and two more, no commit of any repository.
COMMIT = "0123456789abcdef0123456789abcdef01234567"
OTHER_COMMIT = "abcdef0123" * 4
LONG_COMMIT = "fedcba9876543210" * 4

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
        "OpSignature",
        "SCHEMA_VERSION",
        "Tolerance",
        "UnsupportedVersionError",
        "candidates_per_round_of",
        "hw_profile_of",
        "layout_version_of",
        "n_max_of",
        "op_signature_of",
        "owner_of",
        "parse",
        "project_of",
        "read",
        "round_budget_of",
        "source_commit_of",
        "tolerance_of",
        "validate",
        "wall_clock_budget_s_of",
    ]
    assert SCHEMA_VERSION == 1
    assert Instance._fields == (
        "hw_profile_key",
        "hw_profile",
        "tolerance",
        "source_commit",
        "n_max",
        "candidates_per_round",
        "op_signature",
        "round_budget",
        "wall_clock_budget_s",
        "owner",
        "project",
        "others",
    )
    assert Tolerance._fields == ("rtol", "atol")
    assert OpSignature._fields == ("key", "record")
    assert Tolerance._field_defaults == Instance._field_defaults == {}
    assert OpSignature._field_defaults == {}
    assert issubclass(InvalidInstanceError, ValueError)
    for error in (UnsupportedVersionError, MissingInstanceError):
        assert not issubclass(error, (ValueError, OSError))
    for error in (InvalidInstanceError, UnsupportedVersionError, MissingInstanceError):
        assert not issubclass(error, ToolFailure)
    assert UnsupportedVersionError is not run_state.UnsupportedVersionError
    for function in (
        read,
        hw_profile_of,
        tolerance_of,
        source_commit_of,
        n_max_of,
        candidates_per_round_of,
        op_signature_of,
        round_budget_of,
        wall_clock_budget_s_of,
        owner_of,
        project_of,
        layout_version_of,
    ):
        parameters = inspect.signature(function).parameters
        assert list(parameters) == ["data_root", "run_id"]
        for parameter in parameters.values():
            assert parameter.default is inspect.Parameter.empty
    assert list(inspect.signature(parse).parameters) == ["content"]
    assert list(inspect.signature(validate).parameters) == ["document"]


def test_a_minimal_content_gives_the_key_and_the_record():
    result = parse(raw(doc()))

    assert type(result) is Instance
    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, {}
    )
    assert type(result.hw_profile) is dict
    assert key_of(result.hw_profile) == result.hw_profile_key
    assert validate(doc()) is None


def test_a_record_with_its_optional_fields():
    profile = record(ext={"example_field": 3}, label="a label")

    result = parse(raw(doc(profile)))

    assert result == Instance(
        key_of(profile),
        profile,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        {},
    )
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

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, OTHERS
    )
    assert list(result.others) == list(OTHERS)
    assert validate(doc(**OTHERS)) is None


@pytest.mark.parametrize(
    "others",
    [
        {"hw_profiles": [record("acc_b")]},
        {"hw_profiles": {"key": OTHER_KEY, "record": OTHER_RECORD}},
        {"objective": None, "budget": -1},
        {"budget": [], "objective": "", "hw_profile_key": OTHER_KEY},
        {"layout_version": 99, "run_id": "another"},
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
        (VERSION, SECTION, f'"n_max": {TOO_LONG_TEXT}'),
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
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        {"example": [1]},
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

    assert result == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        {},
    )


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

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
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
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )

    assert done.stdout.strip() == "[]"


def test_nothing_of_the_module_holds_a_tolerance_value():
    numbers = {
        name: value
        for name, value in vars(instance).items()
        if type(value) in (int, float, Tolerance)
    }

    assert numbers == {"SCHEMA_VERSION": 1, "_MAX": MAX}


# --- happy: the member source_commit (ADR-0022) ---


def committed(literal, *more):
    return text(VERSION, SECTION, f'"source_commit": {literal}', *more)


@pytest.mark.parametrize(
    "commit",
    [COMMIT, OTHER_COMMIT, LONG_COMMIT, "0" * 40, "f" * 64, "9a" * 20, COMMIT[::-1]],
)
def test_a_content_with_the_member_states_that_string(commit):
    document = doc(source_commit=commit, example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY,
        record(),
        None,
        commit,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        {"example": [1]},
    )
    assert type(result.source_commit) is str
    assert "source_commit" not in result.others
    assert validate(document) is None
    assert parse(committed(f'"{commit}"')).source_commit == commit


def test_every_one_of_the_sixteen_characters_and_both_lengths_are_accepted():
    assert sorted(set(COMMIT)) == sorted(set(LONG_COMMIT)) == list("0123456789abcdef")
    assert (len(COMMIT), len(OTHER_COMMIT), len(LONG_COMMIT)) == (40, 40, 64)

    for character in "0123456789abcdef":
        for length in (40, 64):
            assert parse(committed(f'"{character * length}"')).source_commit == (
                character * length
            )


def test_a_content_without_the_member_states_no_source_commit():
    without = parse(raw(doc(tolerance=TOLERANCE)))
    stating = parse(raw(doc(tolerance=TOLERANCE, source_commit=COMMIT)))

    assert without.source_commit is None
    assert parse(raw(doc())).source_commit is None
    assert (
        without[:3] == stating[:3] == (KEY, record(), Tolerance(TEST_RTOL, TEST_ATOL))
    )
    assert without.others == stating.others == {}
    assert validate(doc(tolerance=TOLERANCE)) is None


MEMBERS = [
    VERSION,
    SECTION,
    '"tolerance": {"rtol": 0.25, "atol": 3.0}',
    f'"source_commit": "{COMMIT}"',
]


@pytest.mark.parametrize("order", list(itertools.permutations(range(4))), ids=repr)
def test_any_order_of_the_three_members_and_the_version(order):
    content = text(*(MEMBERS[index] for index in order))

    assert parse(content) == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        {},
    )
    assert validate(json.loads(content)) is None


def test_white_space_of_json_around_the_member_is_not_part_of_the_value():
    content = text(VERSION, SECTION, f'\r\n\t"source_commit" :\n "{COMMIT}" \n')

    assert parse(content).source_commit == COMMIT


def test_an_escape_of_json_for_one_of_the_sixteen_states_that_character():
    content = committed('"\\u0030' + COMMIT[1:] + '"')

    assert parse(content).source_commit == COMMIT


# The Example of ADR-0022, as written in the record: the shape of the member, not a valid file.
EXAMPLE_OF_ADR_0022 = b"""{
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
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567"
}
"""


def test_the_member_of_the_example_of_adr_0022():
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0022)

    source = b'"hw_source": "NOT-DECIDED-HERE"'
    result = parse(EXAMPLE_OF_ADR_0022.replace(source, b'"hw_source": "in_house"'))
    assert result.source_commit == COMMIT
    assert result.tolerance == Tolerance(0.0001, 0.01)
    assert result.others == {}


# --- branch: the member source_commit ---

BROKEN_COMMITS = [
    None,
    False,
    7,
    "",
    "main",
    COMMIT[:7],
    COMMIT.upper(),
    {"commit": COMMIT},
]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("commit", [*BROKEN_COMMITS, COMMIT], ids=repr)
def test_another_version_is_reported_before_a_source_commit_is_looked_at(
    version, commit
):
    document = doc(schema_version=version, source_commit=commit)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"source-commit": COMMIT},
        {"sourceCommit": COMMIT},
        {"source_commits": [COMMIT]},
        {"commit": COMMIT},
        {"Source_Commit": COMMIT},
        {"source_commit ": "main"},
        {"source-commit": False, "commit": "main", "sourceCommit": COMMIT[:7]},
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_source_commit(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
    assert validate(doc(**others)) is None

    result = parse(raw(doc(source_commit=OTHER_COMMIT, **others)))
    assert result.source_commit == OTHER_COMMIT
    assert result.others == others


NO_COMMIT = "source_commit: must be a str of 40 or of 64 characters, each one of 0-9 and a-f, got "


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "source_commit": None}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "source_commit": "main"},
        ),
        (
            "hw_profile.key: ",
            {"hw_profile": section(key=OTHER_KEY), "source_commit": False},
        ),
        ("tolerance: must be", {"tolerance": None, "source_commit": None}),
        (
            "tolerance: lacks the member atol",
            {"tolerance": {"rtol": TEST_RTOL}, "source_commit": "main"},
        ),
        (
            "tolerance.rtol: must be",
            {"tolerance": {"rtol": -1, "atol": 0}, "source_commit": COMMIT[:7]},
        ),
        (NO_COMMIT + "str 'main'", {"tolerance": TOLERANCE, "source_commit": "main"}),
        (NO_COMMIT + "bool", {"source_commit": False}),
    ],
)
def test_the_first_broken_rule_is_reported_with_a_source_commit(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member source_commit ---

NO_COMMITS = [
    None,
    True,
    False,
    0,
    7,
    int("1" * 40),
    int(COMMIT, 16),
    0.5,
    [],
    [COMMIT],
    list(COMMIT),
    {},
    {"commit": COMMIT},
    {"sha1": COMMIT},
    "",
    COMMIT[:7],
    COMMIT[:12],
    COMMIT[:39],
    COMMIT + "0",
    LONG_COMMIT[:63],
    LONG_COMMIT + "0",
    COMMIT + COMMIT,
    COMMIT + "0" * 12,
    COMMIT.upper(),
    LONG_COMMIT.upper(),
    COMMIT[:-1] + "F",
    "A" + COMMIT[1:],
    COMMIT[:20] + "E" + COMMIT[21:],
    COMMIT[:-1] + "g",
    COMMIT[:-1] + " ",
    COMMIT[:20] + "-" + COMMIT[21:],
    COMMIT[:20] + " " + COMMIT[21:],
    COMMIT + "\n",
    COMMIT[:-1] + "\n",
    LONG_COMMIT[:-1] + "\n",
    COMMIT + "\r\n",
    " " + COMMIT,
    " " + COMMIT[1:],
    COMMIT + " ",
    "\t" + COMMIT[2:] + "\t",
    "sha1:" + COMMIT,
    "sha1:" + COMMIT[5:],
    "0x" + COMMIT,
    "0x" + COMMIT[2:],
    "+" + COMMIT[1:],
    "-" + COMMIT[1:],
    COMMIT[:5] + "_" + COMMIT[6:],
    "\x00" + COMMIT[1:],
    "\uff10" + COMMIT[1:],
    "\uff10" * 40,
    "\u0660" + COMMIT[1:],
    "\u0663" * 40,
    "\u0966" * 64,
    "\uff41" + COMMIT[1:],
    "\u00e9" + COMMIT[1:],
    "main",
    "v1.0",
    "HEAD",
    "refs/heads/main",
    "v1.0-3-g0123456",
    "0123456-dirty",
    COMMIT + "-dirty",
]


@pytest.mark.parametrize("value", NO_COMMITS, ids=ascii)
def test_what_is_no_value_of_the_member(value):
    document = doc(tolerance=TOLERANCE, source_commit=value, example=[1])
    expected = NO_COMMIT + type(value).__name__

    for content in (raw(document), json.dumps(document, ensure_ascii=False).encode()):
        message = invalid(expected, parse, content)
        if type(value) is str:
            assert message == f"{expected} {reprlib.repr(value)}"
    invalid(expected, validate, document)


LOOSER_RULES = {
    "str.isdigit": (str.isdigit, ["０" * 40, "٣" * 40, "०" * 64]),
    "a digit class": (
        lambda value: re.fullmatch(r"\d{40}", value),
        ["０" * 40, "٣" * 40],
    ),
    "int(value, 16)": (
        lambda value: int(value, 16) >= 0,
        [
            COMMIT.upper(),
            " " + COMMIT[1:],
            "+" + COMMIT[1:],
            COMMIT[:5] + "_" + COMMIT[6:],
            "0x" + COMMIT[2:],
            COMMIT[:-1] + "\n",
            "０" * 40,
        ],
    ),
    "bytes.fromhex": (
        lambda value: len(bytes.fromhex(value)) > 0,
        [COMMIT.upper(), LONG_COMMIT.upper(), COMMIT[:20] + "  " + COMMIT[20:-2]],
    ),
    "a pattern ending in $": (
        lambda value: re.match(r"[0-9a-f]{40}$|[0-9a-f]{64}$", value),
        [COMMIT + "\n", LONG_COMMIT + "\n"],
    ),
}


@pytest.mark.parametrize("rule", LOOSER_RULES)
def test_a_value_a_looser_rule_would_accept_is_refused(rule):
    looser, values = LOOSER_RULES[rule]

    for value in values:
        assert looser(value)
        invalid(NO_COMMIT + "str", parse, raw(doc(source_commit=value)))
        invalid(NO_COMMIT + "str", validate, doc(source_commit=value))


@pytest.mark.parametrize(
    "literal",
    [
        '"0123456"',
        '"main"',
        '"0123456789ABCDEF0123456789ABCDEF01234567"',
        "false",
        '{"commit": "0123456789abcdef0123456789abcdef01234567"}',
        "null",
        "true",
        "1111111111111111111111111111111111111111",
        '["0123456789abcdef0123456789abcdef01234567"]',
        '"0123456789abcdef0123456789abcdef01234567\\n"',
        '"0123456789abcdef0123456789abcdef0123456\\n"',
    ],
)
def test_the_invalid_files_of_the_walk_through_of_adr_0022(literal):
    more = '"tolerance": {"rtol": 0.25, "atol": 3.0}'

    invalid("source_commit: must be", parse, committed(literal, more))
    assert parse(text(VERSION, SECTION, more)).tolerance is not None


@pytest.mark.parametrize(
    "members",
    [
        (f'"source_commit": "{COMMIT}"', f'"source_commit": "{COMMIT}"'),
        (f'"source_commit": "{COMMIT}"', f'"source_commit": "{OTHER_COMMIT}"'),
        (f'"source_commit": "{COMMIT}"', '"source_commit": false'),
        ('"source_commit": "main"', f'"source_commit": "{COMMIT}"'),
    ],
)
def test_the_member_name_twice_at_the_top_level(members):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, *members),
    )
    assert "a JSON object repeats a member name" in message


class Text(str):
    """A test-only subclass: not exactly a ``str``."""


@pytest.mark.parametrize(
    "value",
    [
        Text(COMMIT),
        Text(LONG_COMMIT),
        COMMIT.encode(),
        LONG_COMMIT.encode(),
        bytes.fromhex(COMMIT),
        bytearray(COMMIT.encode()),
        tuple(COMMIT),
        (COMMIT,),
    ],
    ids=shown,
)
def test_validate_refuses_a_source_commit_built_in_memory(value):
    document = doc(source_commit=value)

    assert invalid(NO_COMMIT, validate, document) == NO_COMMIT + type(value).__name__


def test_a_long_value_is_shown_shortened():
    message = invalid(NO_COMMIT, parse, raw(doc(source_commit=COMMIT.upper())))

    assert message == f"{NO_COMMIT}str {reprlib.repr(COMMIT.upper())}"
    assert COMMIT.upper() not in message and "..." in message


def test_a_check_of_a_source_commit_modifies_nothing():
    for document in (doc(source_commit=COMMIT), doc(source_commit="main")):
        kept = json.dumps(document)
        assert accepted(validate, document) == (document["source_commit"] == COMMIT)
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module is or obtains a commit ---


def test_nothing_of_the_module_holds_a_source_commit():
    held = []
    for value in vars(instance).values():
        if type(value) in (tuple, list, set, frozenset):
            held.extend(value)
        elif type(value) is dict and value is not vars(instance).get("__builtins__"):
            held.extend(value.values())
        else:
            held.append(value)

    texts = [value for value in held if type(value) in (str, bytes)]
    assert len(texts) > 10
    assert not [
        value for value in texts if accepted(validate, doc(source_commit=value))
    ]
    assert re.search(r"[0-9a-fA-F]{40}", inspect.getsource(instance)) is None
    for function in (
        parse,
        validate,
        read,
        hw_profile_of,
        tolerance_of,
        source_commit_of,
        n_max_of,
    ):
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert Instance._field_defaults == {}


def test_the_module_does_not_load_subprocess():
    code = (
        "import sys, hilclaw.instance; "
        "print(sorted(name for name in sys.modules "
        "if name.split('.')[0] == 'subprocess'))"
    )

    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )

    assert done.stdout.strip() == "[]"
    assert not set(vars(instance)) & {"subprocess", "hilclaw", "__version__"}


# --- happy: the member n_max (ADR-0023) ---

# Test values of a bound: neither is a default, recommended or typical value.
BOUND, OTHER_BOUND = 12, 7
NO_BOUND = f"n_max: must be an int from 5 to {MAX}, got "


def bounded(literal, *more):
    return text(VERSION, SECTION, f'"n_max": {literal}', *more)


@pytest.mark.parametrize(
    "bound", [5, 6, 9, 10, 11, 12, 30, 31, 1000, 2**31, 2**32 + 1, MAX - 1, MAX]
)
def test_a_content_with_the_member_states_that_bound(bound):
    document = doc(n_max=bound, example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY,
        record(),
        None,
        None,
        bound,
        None,
        None,
        None,
        None,
        None,
        None,
        {"example": [1]},
    )
    assert type(result.n_max) is int
    assert "n_max" not in result.others
    assert validate(document) is None
    assert parse(bounded(str(bound))).n_max == bound


def test_both_bounds_of_the_member_are_inclusive():
    assert MAX == 2**53 - 1

    for bound in (5, MAX):
        assert parse(bounded(str(bound))).n_max == bound
        assert validate(doc(n_max=bound)) is None
    for bound in (4, MAX + 1):
        assert invalid(NO_BOUND, parse, bounded(str(bound))) == NO_BOUND + "int"
        assert invalid(NO_BOUND, validate, doc(n_max=bound)) == NO_BOUND + "int"
    invalid(NO_BOUND, parse, bounded("9007199254740992"))
    assert parse(bounded("9007199254740991")).n_max == MAX


def test_a_content_without_the_member_states_no_bound():
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT}
    without = parse(raw(doc(**members)))
    stating = parse(raw(doc(**members, n_max=BOUND)))

    assert without.n_max is None
    assert parse(raw(doc())).n_max is None
    assert stating.n_max == BOUND
    assert (
        without[:4]
        == stating[:4]
        == (KEY, record(), Tolerance(TEST_RTOL, TEST_ATOL), COMMIT)
    )
    assert without.others == stating.others == {}
    assert validate(doc(**members)) is None


BOUNDED_MEMBERS = [*MEMBERS, f'"n_max": {BOUND}']


@pytest.mark.parametrize("order", list(itertools.permutations(range(5))), ids=repr)
def test_any_order_of_the_four_members_and_the_version(order):
    content = text(*(BOUNDED_MEMBERS[index] for index in order))

    assert parse(content) == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        None,
        None,
        None,
        None,
        None,
        None,
        {},
    )
    assert validate(json.loads(content)) is None


def test_white_space_of_json_around_the_number_is_not_part_of_the_value():
    content = text(VERSION, SECTION, f'\r\n\t"n_max" :\n {BOUND} \n')

    assert parse(content).n_max == BOUND


# The Example of ADR-0023, as written in the record: the shape of the member, not a valid file.
EXAMPLE_OF_ADR_0023 = b"""{
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
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10
}
"""


def test_the_member_of_the_example_of_adr_0023():
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0023)

    source = b'"hw_source": "NOT-DECIDED-HERE"'
    result = parse(EXAMPLE_OF_ADR_0023.replace(source, b'"hw_source": "in_house"'))
    assert result.n_max == 10 and type(result.n_max) is int
    assert result.source_commit == COMMIT
    assert result.tolerance == Tolerance(0.0001, 0.01)
    assert result.others == {}

    silent = parse(EXAMPLE_OF_ADR_0022.replace(source, b'"hw_source": "in_house"'))
    assert silent.n_max is None
    assert silent[:4] == result[:4]


# --- branch: the member n_max ---

BROKEN_BOUNDS = [None, True, 4, 0, -10, 10.0, "10", [10], {"value": 10}, MAX + 1]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("bound", [*BROKEN_BOUNDS, BOUND], ids=repr)
def test_another_version_is_reported_before_a_bound_is_looked_at(version, bound):
    document = doc(schema_version=version, n_max=bound)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"nmax": BOUND},
        {"N_max": BOUND},
        {"n-max": BOUND},
        {"nMax": BOUND},
        {"N_MAX": BOUND},
        {"n_max ": 4},
        {"n_min": 5},
        {"repeats": BOUND},
        {"nmax": True, "n-max": 4, "N_max": "10", "nMax": 10.0, "n_min": 0},
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_bound(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
    assert result.n_max is None
    assert validate(doc(**others)) is None

    result = parse(raw(doc(n_max=OTHER_BOUND, **others)))
    assert result.n_max == OTHER_BOUND
    assert result.others == others


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "n_max": 4}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "n_max": True},
        ),
        (
            "hw_profile.key: ",
            {"hw_profile": section(key=OTHER_KEY), "n_max": "10"},
        ),
        ("tolerance: must be", {"tolerance": None, "n_max": None}),
        (
            "tolerance.rtol: must be",
            {"tolerance": {"rtol": -1, "atol": 0}, "n_max": 0},
        ),
        (NO_COMMIT + "str 'main'", {"source_commit": "main", "n_max": 4}),
        (
            NO_COMMIT + "bool",
            {"tolerance": TOLERANCE, "source_commit": False, "n_max": 10.0},
        ),
        (
            NO_BOUND + "int",
            {"tolerance": TOLERANCE, "source_commit": COMMIT, "n_max": 4},
        ),
        (NO_BOUND + "bool", {"n_max": False}),
    ],
)
def test_the_first_broken_rule_is_reported_with_a_bound(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member n_max ---

NO_BOUND_LITERALS = {
    "true": "bool",
    "false": "bool",
    "null": "NoneType",
    '"10"': "str '10'",
    '"12"': "str '12'",
    '""': "str ''",
    '"ten"': "str 'ten'",
    "[10]": "list",
    "[]": "list",
    '{"value": 10}': "dict",
    "{}": "dict",
    "10.0": "float",
    "1e1": "float",
    "1E1": "float",
    "10e0": "float",
    "5.0": "float",
    "12.5": "float",
    "4.9": "float",
    "1e999": "float",
    "-0.0": "float",
    "-0": "int",
    "0": "int",
    "1": "int",
    "2": "int",
    "3": "int",
    "4": "int",
    "-1": "int",
    "-5": "int",
    "-10": "int",
    "-12": "int",
    "9007199254740992": "int",
    "9007199254740993": "int",
    "10000000000000000000000": "int",
}


@pytest.mark.parametrize("literal", NO_BOUND_LITERALS)
def test_what_is_no_value_of_the_bound(literal):
    more = (MEMBERS[2], MEMBERS[3], '"example": [1]')
    content = bounded(literal, *more)

    assert invalid(NO_BOUND, parse, content) == NO_BOUND + NO_BOUND_LITERALS[literal]
    invalid(NO_BOUND, validate, json.loads(content))
    assert parse(text(VERSION, SECTION, *more)) == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        {"example": [1]},
    )


@pytest.mark.parametrize(
    "literal",
    [
        "4",
        "0",
        "-10",
        "10.0",
        "1e1",
        '"10"',
        "true",
        "null",
        "[10]",
        "9007199254740992",
    ],
)
def test_the_invalid_files_of_the_walk_through_of_adr_0023(literal):
    more = (MEMBERS[2], MEMBERS[3])

    invalid("n_max: must be", parse, bounded(literal, *more))
    kept = parse(text(VERSION, SECTION, *more))
    assert (kept.tolerance, kept.source_commit) == (
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
    )
    assert parse(text(VERSION, SECTION, '"nmax": 12')).n_max is None
    assert parse(bounded("12")).n_max == 12


def test_minus_zero_is_refused_as_the_integer_0_below_the_bound():
    assert type(json.loads("-0")) is int and json.loads("-0") == 0

    assert invalid(NO_BOUND, parse, bounded("-0")) == NO_BOUND + "int"
    assert invalid(NO_BOUND, parse, bounded("0")) == NO_BOUND + "int"


class Number(int):
    """A test-only subclass: not exactly an ``int``."""


LOOSER_BOUND_RULES = {
    "isinstance(value, int)": (
        lambda value: isinstance(value, int) and 5 <= value <= MAX,
        [Number(10), Number(5), Number(MAX)],
    ),
    "isinstance(value, int) without the bound": (
        lambda value: isinstance(value, int),
        [True, False, Number(12)],
    ),
    "an equal value": (
        lambda value: value == 10 or value == 5,
        [10.0, 5.0, Number(10)],
    ),
    "float.is_integer": (
        lambda value: float(value).is_integer() and value >= 5,
        [10.0, 5.0, 12.0, 1e1, float(2**40)],
    ),
    "int(value)": (
        lambda value: 5 <= int(value) <= MAX,
        ["10", " 12 ", "1_0", "+10", 10.0, 10.9, 5.5, Number(10)],
    ),
}


@pytest.mark.parametrize("rule", LOOSER_BOUND_RULES)
def test_a_bound_a_looser_rule_would_accept_is_refused(rule):
    looser, values = LOOSER_BOUND_RULES[rule]

    for value in values:
        assert looser(value)
        expected = NO_BOUND + type(value).__name__
        invalid(expected, validate, doc(n_max=value))
        if type(value) is not Number:
            invalid(expected, parse, raw(doc(n_max=value)))


@pytest.mark.parametrize(
    "members",
    [
        (f'"n_max": {BOUND}', f'"n_max": {BOUND}'),
        (f'"n_max": {BOUND}', f'"n_max": {OTHER_BOUND}'),
        (f'"n_max": {BOUND}', '"n_max": 4'),
        ('"n_max": true', f'"n_max": {BOUND}'),
    ],
)
def test_the_member_name_n_max_twice_at_the_top_level(members):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, *members),
    )
    assert "a JSON object repeats a member name" in message


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        10.0,
        5.0,
        float("inf"),
        float("nan"),
        Number(10),
        Number(5),
        Number(4),
        TOO_LONG,
        -TOO_LONG,
        b"10",
        (10,),
        {10},
        range(10),
    ],
    ids=shown,
)
def test_validate_refuses_a_bound_built_in_memory(value):
    document = doc(n_max=value)

    assert invalid(NO_BOUND, validate, document) == NO_BOUND + type(value).__name__


def test_a_refused_integer_is_not_shown():
    for bound in (4, 0, -10, MAX + 1):
        message = invalid(NO_BOUND, validate, doc(n_max=bound))
        assert message == NO_BOUND + "int"
        assert not message.endswith(str(bound))


def test_a_check_of_a_bound_modifies_nothing():
    for document in (doc(n_max=BOUND), doc(n_max=4), doc(n_max=10.0)):
        kept = json.dumps(document)
        assert accepted(validate, document) == (document["n_max"] == BOUND)
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module is a bound ---


def test_a_content_without_the_member_states_no_bound_though_the_harness_has_a_default():
    default = measurement.N_MAX_DEFAULT
    assert type(default) is int

    for document in (
        doc(),
        doc(tolerance=TOLERANCE, source_commit=COMMIT),
        doc(nmax=7),
    ):
        result = parse(raw(document))
        assert result.n_max is None
        assert default not in result


def test_nothing_of_the_module_holds_a_bound():
    default = measurement.N_MAX_DEFAULT
    held = []
    for value in vars(instance).values():
        if type(value) in (tuple, list, set, frozenset):
            held.extend(value)
        elif type(value) is dict and value is not vars(instance).get("__builtins__"):
            held.extend(value.values())
        else:
            held.append(value)

    numbers = [value for value in held if type(value) in (int, float)]
    assert len(numbers) >= 2
    assert default not in numbers
    functions = [
        value
        for value in vars(instance).values()
        if inspect.isfunction(value) and value.__module__ == instance.__name__
    ]
    assert len(functions) > 10 and n_max_of in functions
    for function in functions:
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert Instance._field_defaults == Tolerance._field_defaults == {}
    written = [
        node.value
        for node in ast.walk(ast.parse(inspect.getsource(instance)))
        if isinstance(node, ast.Constant) and type(node.value) is int
    ]
    assert 5 in written and default not in written
    assert not {"measurement", "harness", "N_MIN", "N_MAX_DEFAULT", "n_max"} & set(
        vars(instance)
    )


# --- happy: the member candidates_per_round (ADR-0028) ---

# Test values of a number of candidates per round: neither is a default, recommended or typical value.
COUNT, OTHER_COUNT = 3, 4
NO_COUNT = f"candidates_per_round: must be an int from 1 to {MAX}, got "


def counted(literal, *more):
    return text(VERSION, SECTION, f'"candidates_per_round": {literal}', *more)


@pytest.mark.parametrize(
    "count", [1, 2, 3, 5, 6, 7, 100, 1000, 2**31, 2**32 + 1, MAX - 1, MAX]
)
def test_a_content_with_the_member_states_that_number(count):
    document = doc(candidates_per_round=count, example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY,
        record(),
        None,
        None,
        None,
        count,
        None,
        None,
        None,
        None,
        None,
        {"example": [1]},
    )
    assert type(result.candidates_per_round) is int
    assert "candidates_per_round" not in result.others
    assert validate(document) is None
    assert parse(counted(str(count))).candidates_per_round == count


def test_both_ends_of_the_range_are_inclusive_and_nothing_ends_it_below_the_maximum():
    assert MAX == 2**53 - 1

    for count in (1, 6, 100, MAX):
        assert parse(counted(str(count))).candidates_per_round == count
        assert validate(doc(candidates_per_round=count)) is None
    for count in (0, MAX + 1):
        assert invalid(NO_COUNT, parse, counted(str(count))) == NO_COUNT + "int"
        document = doc(candidates_per_round=count)
        assert invalid(NO_COUNT, validate, document) == NO_COUNT + "int"
    invalid(NO_COUNT, parse, counted("9007199254740992"))
    assert parse(counted("9007199254740991")).candidates_per_round == MAX


def test_a_content_without_the_member_states_no_number():
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT, "n_max": BOUND}
    without = parse(raw(doc(**members)))
    stating = parse(raw(doc(**members, candidates_per_round=COUNT)))

    assert without.candidates_per_round is None
    assert parse(raw(doc())).candidates_per_round is None
    assert stating.candidates_per_round == COUNT
    assert (
        without[:5]
        == stating[:5]
        == (KEY, record(), Tolerance(TEST_RTOL, TEST_ATOL), COMMIT, BOUND)
    )
    assert without.others == stating.others == {}
    assert validate(doc(**members)) is None


COUNTED_MEMBERS = [*BOUNDED_MEMBERS, f'"candidates_per_round": {COUNT}']


@pytest.mark.parametrize("order", list(itertools.permutations(range(6))), ids=repr)
def test_any_order_of_the_five_members_and_the_version(order):
    content = text(*(COUNTED_MEMBERS[index] for index in order))

    assert parse(content) == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        COUNT,
        None,
        None,
        None,
        None,
        None,
        {},
    )
    assert validate(json.loads(content)) is None


def test_white_space_of_json_around_the_number_of_candidates_is_not_part_of_the_value():
    content = text(VERSION, SECTION, f'\r\n\t"candidates_per_round" :\n {COUNT} \n')

    assert parse(content).candidates_per_round == COUNT


# The Example of ADR-0028, as written in the record: the shape of the member, not a valid file.
EXAMPLE_OF_ADR_0028 = b"""{
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
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10,
  "candidates_per_round": 2
}
"""


def test_the_member_of_the_example_of_adr_0028():
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0028)

    source = b'"hw_source": "NOT-DECIDED-HERE"'
    result = parse(EXAMPLE_OF_ADR_0028.replace(source, b'"hw_source": "in_house"'))
    assert result.candidates_per_round == 2
    assert type(result.candidates_per_round) is int
    assert result.n_max == 10
    assert result.source_commit == COMMIT
    assert result.tolerance == Tolerance(0.0001, 0.01)
    assert result.others == {}

    silent = parse(EXAMPLE_OF_ADR_0023.replace(source, b'"hw_source": "in_house"'))
    assert silent.candidates_per_round is None
    assert silent[:5] == result[:5]


# --- branch: the member candidates_per_round ---


@pytest.mark.parametrize(
    "count, bound", [(100, 5), (1, MAX), (MAX, 5), (6, 6), (1, 5), (MAX, MAX)]
)
def test_the_member_and_n_max_do_not_bound_each_other(count, bound):
    document = doc(candidates_per_round=count, n_max=bound)

    result = parse(raw(document))

    assert (result.candidates_per_round, result.n_max) == (count, bound)
    assert validate(document) is None


BROKEN_COUNTS = [None, True, 0, -1, 2.0, "2", [2], {"value": 2}, MAX + 1]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("count", [*BROKEN_COUNTS, COUNT], ids=repr)
def test_another_version_is_reported_before_the_number_of_candidates_is_looked_at(
    version, count
):
    document = doc(schema_version=version, candidates_per_round=count)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"candidates": COUNT},
        {"n": COUNT},
        {"N": COUNT},
        {"candidatesPerRound": COUNT},
        {"candidates-per-round": COUNT},
        {"Candidates_per_round": COUNT},
        {"CANDIDATES_PER_ROUND": COUNT},
        {"candidates_per_round ": 0},
        {"candidates_per_rounds": COUNT},
        {"id": {"candidates": COUNT, "candidates_per_round": COUNT}},
        {
            "candidates": True,
            "n": 0,
            "candidatesPerRound": "2",
            "candidates-per-round": 2.0,
            "id": {"candidates": -1},
        },
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_number(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
    assert result.candidates_per_round is None
    assert validate(doc(**others)) is None

    result = parse(raw(doc(candidates_per_round=OTHER_COUNT, **others)))
    assert result.candidates_per_round == OTHER_COUNT
    assert result.others == others


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "candidates_per_round": 0}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "candidates_per_round": True},
        ),
        (
            "hw_profile.key: ",
            {"hw_profile": section(key=OTHER_KEY), "candidates_per_round": "2"},
        ),
        ("tolerance: must be", {"tolerance": None, "candidates_per_round": None}),
        (
            "tolerance.rtol: must be",
            {"tolerance": {"rtol": -1, "atol": 0}, "candidates_per_round": 0},
        ),
        (
            NO_COMMIT + "str 'main'",
            {"source_commit": "main", "candidates_per_round": 0},
        ),
        (NO_BOUND + "int", {"n_max": 4, "candidates_per_round": 0}),
        (
            NO_BOUND + "bool",
            {
                "tolerance": TOLERANCE,
                "source_commit": COMMIT,
                "n_max": True,
                "candidates_per_round": 2.0,
            },
        ),
        (
            NO_COUNT + "int",
            {
                "tolerance": TOLERANCE,
                "source_commit": COMMIT,
                "n_max": BOUND,
                "candidates_per_round": 0,
            },
        ),
        (NO_COUNT + "bool", {"candidates_per_round": False}),
    ],
)
def test_the_first_broken_rule_is_reported_with_a_number_of_candidates(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member candidates_per_round ---

NO_COUNT_LITERALS = {
    "true": "bool",
    "false": "bool",
    "null": "NoneType",
    '"2"': "str '2'",
    '"1"': "str '1'",
    '""': "str ''",
    '"two"': "str 'two'",
    "[2]": "list",
    "[]": "list",
    '{"value": 2}': "dict",
    "{}": "dict",
    "2.0": "float",
    "2e0": "float",
    "2E0": "float",
    "1.0": "float",
    "1.5": "float",
    "0.5": "float",
    "1e999": "float",
    "-0.0": "float",
    "-0": "int",
    "0": "int",
    "-1": "int",
    "-2": "int",
    "-5": "int",
    "9007199254740992": "int",
    "9007199254740993": "int",
    "10000000000000000000000": "int",
}


@pytest.mark.parametrize("literal", NO_COUNT_LITERALS)
def test_what_is_no_value_of_the_number_of_candidates(literal):
    more = (MEMBERS[2], MEMBERS[3], BOUNDED_MEMBERS[4], '"example": [1]')
    content = counted(literal, *more)

    assert invalid(NO_COUNT, parse, content) == NO_COUNT + NO_COUNT_LITERALS[literal]
    invalid(NO_COUNT, validate, json.loads(content))
    assert parse(text(VERSION, SECTION, *more)) == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        None,
        None,
        None,
        None,
        None,
        None,
        {"example": [1]},
    )


WALK_THROUGH_OF_ADR_0028 = [
    "0",
    "-1",
    "2.0",
    "2e0",
    '"2"',
    "true",
    "null",
    "[2]",
    "9007199254740992",
]


@pytest.mark.parametrize("literal", WALK_THROUGH_OF_ADR_0028)
def test_the_invalid_files_of_the_walk_through_of_adr_0028(literal):
    more = (MEMBERS[2], MEMBERS[3], BOUNDED_MEMBERS[4])

    invalid("candidates_per_round: must be", parse, counted(literal, *more))
    kept = parse(text(VERSION, SECTION, *more))
    assert kept[2:6] == (Tolerance(TEST_RTOL, TEST_ATOL), COMMIT, BOUND, None)
    silent = parse(text(VERSION, SECTION, '"candidates": 2'))
    assert silent.candidates_per_round is None
    assert silent.others == {"candidates": 2}
    assert parse(counted("2")).candidates_per_round == 2
    for count in (6, 100):
        assert parse(counted(str(count), *more)).candidates_per_round == count


def test_minus_zero_is_refused_as_the_integer_0_below_the_lower_end():
    assert type(json.loads("-0")) is int and json.loads("-0") == 0

    assert invalid(NO_COUNT, parse, counted("-0")) == NO_COUNT + "int"
    assert invalid(NO_COUNT, parse, counted("0")) == NO_COUNT + "int"


LOOSER_COUNT_RULES = {
    "isinstance(value, int)": (
        lambda value: isinstance(value, int) and 1 <= value <= MAX,
        [True, Number(2), Number(1), Number(MAX)],
    ),
    "isinstance(value, int) without the range": (
        lambda value: isinstance(value, int),
        [True, False, Number(3)],
    ),
    "an equal value": (
        lambda value: value == 2 or value == 1,
        [2.0, 1.0, True, Number(2)],
    ),
    "float.is_integer": (
        lambda value: float(value).is_integer() and value >= 1,
        [2.0, 1.0, 3.0, 2e0, float(2**40)],
    ),
    "int(value)": (
        lambda value: 1 <= int(value) <= MAX,
        ["2", " 3 ", "1_0", "+2", 2.0, 2.9, 1.5, True, Number(2)],
    ),
}


@pytest.mark.parametrize("rule", LOOSER_COUNT_RULES)
def test_a_number_of_candidates_a_looser_rule_would_accept_is_refused(rule):
    looser, values = LOOSER_COUNT_RULES[rule]

    for value in values:
        assert looser(value)
        expected = NO_COUNT + type(value).__name__
        invalid(expected, validate, doc(candidates_per_round=value))
        if type(value) is not Number:
            invalid(expected, parse, raw(doc(candidates_per_round=value)))


@pytest.mark.parametrize(
    "members",
    [
        (f'"candidates_per_round": {COUNT}', f'"candidates_per_round": {COUNT}'),
        (f'"candidates_per_round": {COUNT}', f'"candidates_per_round": {OTHER_COUNT}'),
        (f'"candidates_per_round": {COUNT}', '"candidates_per_round": 0'),
        ('"candidates_per_round": true', f'"candidates_per_round": {COUNT}'),
    ],
)
def test_the_member_name_candidates_per_round_twice_at_the_top_level(members):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, *members),
    )
    assert "a JSON object repeats a member name" in message


def test_a_number_of_candidates_too_long_for_the_interpreter_is_a_text_error():
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        counted(TOO_LONG_TEXT),
    )
    assert "candidates_per_round" not in message


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        2.0,
        1.0,
        float("inf"),
        float("nan"),
        Number(2),
        Number(1),
        Number(0),
        TOO_LONG,
        -TOO_LONG,
        "2",
        None,
        b"2",
        (2,),
        {2},
        range(2),
    ],
    ids=shown,
)
def test_validate_refuses_a_number_of_candidates_built_in_memory(value):
    document = doc(candidates_per_round=value)

    message = invalid(NO_COUNT + type(value).__name__, validate, document)

    if type(value) is not str:
        assert message == NO_COUNT + type(value).__name__


def test_a_refused_number_of_candidates_is_not_shown_and_a_string_is():
    for count in (0, -1, -7, MAX + 1):
        message = invalid(NO_COUNT, validate, doc(candidates_per_round=count))
        assert message == NO_COUNT + "int"
        assert not message.endswith(str(count))

    message = invalid(NO_COUNT, validate, doc(candidates_per_round="2" * 200))
    assert message == NO_COUNT + "str " + reprlib.repr("2" * 200)
    assert len(message) < 120


def test_a_check_of_a_number_of_candidates_modifies_nothing():
    for document in (
        doc(candidates_per_round=COUNT),
        doc(candidates_per_round=0),
        doc(candidates_per_round=2.0),
    ):
        kept = json.dumps(document)
        valid = document["candidates_per_round"] == COUNT
        assert accepted(validate, document) == valid
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module stands in for the number of candidates ---


@pytest.mark.parametrize(
    "document",
    [
        doc(),
        doc(tolerance=TOLERANCE, source_commit=COMMIT, n_max=BOUND),
        doc(candidates=2),
        doc(n=1, id={"candidates": 1}),
    ],
    ids=repr,
)
def test_a_content_without_the_member_states_no_number_and_not_1(document):
    result = parse(raw(document))

    assert result.candidates_per_round is None
    assert result._asdict()["candidates_per_round"] is None
    assert validate(document) is None


def test_nothing_of_the_module_stands_in_for_the_number_of_candidates():
    functions = [
        value
        for value in vars(instance).values()
        if inspect.isfunction(value) and value.__module__ == instance.__name__
    ]
    assert candidates_per_round_of in functions
    for function in functions:
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert Instance._field_defaults == {}
    imported = set()
    for node in ast.walk(ast.parse(inspect.getsource(instance))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert "hilclaw.keys" in imported
    assert not [name for name in imported if "spec" in name]
    assert not {"spec", "candidates", "candidates_per_round"} & set(vars(instance))


# --- happy: the member op_signature (ADR-0031) ---


# Synthetic gemm records: no operation, shape, dtype, layout or M of a real run, and no default.
def op_record(**changes):
    made = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 3, "k": 5, "n": 7},
        "dtype": "dtype_a",
        "layout": "layout_a",
    }
    for name, value in changes.items():
        made[name] = value
    return {name: value for name, value in made.items() if value is not REMOVE}


def op_key_of(op):
    return keys.op_signature_key(op).name


def stating(op):
    return {"key": op_key_of(op), "record": op}


OP_KEY = op_key_of(op_record())
OTHER_OP = op_record(shape={"m": 4, "k": 5, "n": 7}, label="another")
OTHER_OP_KEY = op_key_of(OTHER_OP)
OP_SECTION = f'"op_signature": {json.dumps(stating(op_record()))}'
OP_MEMBERS = {
    "tolerance": TOLERANCE,
    "source_commit": COMMIT,
    "n_max": BOUND,
    "candidates_per_round": COUNT,
}
OP_PLACE = "op_signature"
NO_OP_KEY = f"op_signature.key: must be {OP_KEY}, the name derived from op_signature.record, got "


def op_section(**changes):
    made = stating(op_record())
    for name, value in changes.items():
        if value is REMOVE:
            del made[name]
        else:
            made[name] = value
    return made


OP_RECORDS = {
    "the key fields": op_record(),
    "a label": op_record(label="a label"),
    "an ext": op_record(ext={"example": 1, "other": "x"}),
    "an ext and a label": op_record(ext={"example": "x"}, label="both"),
    "m 0": op_record(shape={"m": 0, "k": 0, "n": 0}),
    "the largest integers": op_record(shape={"m": MAX, "k": MAX, "n": MAX}),
    "other names": op_record(dtype="x9", layout="col_major"),
}


@pytest.mark.parametrize("case", OP_RECORDS)
def test_a_content_with_the_member_states_that_key_and_that_record(case):
    stated_record = OP_RECORDS[case]
    document = doc(op_signature=stating(stated_record), example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY,
        record(),
        None,
        None,
        None,
        None,
        OpSignature(op_key_of(stated_record), stated_record),
        None,
        None,
        None,
        None,
        {"example": [1]},
    )
    assert type(result.op_signature) is OpSignature
    assert type(result.op_signature.key) is str
    assert type(result.op_signature.record) is dict
    assert "op_signature" not in result.others
    assert validate(document) is None


def test_the_record_handed_out_is_the_one_parsed_from_the_content():
    stated_record = op_record(label="kept", ext={"example": 1})
    content = raw(doc(op_signature=stating(stated_record)))

    first, second = parse(content), parse(content)

    assert first.op_signature == second.op_signature
    assert first.op_signature.record == stated_record
    assert first.op_signature.record is not second.op_signature.record
    assert first.op_signature.record["label"] == "kept"
    assert list(first.op_signature._asdict()) == ["key", "record"]


def test_a_content_without_the_member_states_no_op_signature():
    without = parse(raw(doc(**OP_MEMBERS)))
    with_it = parse(raw(doc(**OP_MEMBERS, op_signature=stating(op_record()))))

    assert without.op_signature is None
    assert parse(raw(doc())).op_signature is None
    assert with_it.op_signature == OpSignature(OP_KEY, op_record())
    assert (
        without[:6]
        == with_it[:6]
        == (KEY, record(), Tolerance(TEST_RTOL, TEST_ATOL), COMMIT, BOUND, COUNT)
    )
    assert without.others == with_it.others == {}
    assert validate(doc(**OP_MEMBERS)) is None
    assert validate(doc()) is None


def test_any_order_of_the_six_members_and_the_version():
    members = [*COUNTED_MEMBERS, OP_SECTION]
    expected = Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        COUNT,
        OpSignature(OP_KEY, op_record()),
        None,
        None,
        None,
        None,
        {},
    )

    for order in itertools.permutations(range(7)):
        content = text(*(members[index] for index in order))
        assert parse(content) == expected
    assert validate(json.loads(text(*reversed(members)))) is None


def test_any_order_and_any_white_space_inside_the_member():
    turned = json.dumps(op_record(label="x"), sort_keys=True)
    shape = '{"n": 7, "k": 5, "m": 3}'
    for member in (
        f'"op_signature": {{"record": {json.dumps(op_record())}, "key": "{OP_KEY}"}}',
        f'"op_signature": {{"record": {turned}, "key": "{OP_KEY}"}}',
        f'\r\n\t"op_signature" :\n {{ "key" : "{OP_KEY}" ,\n "record" : {turned} }} \n',
        OP_SECTION.replace('{"m": 3, "k": 5, "n": 7}', shape),
    ):
        result = parse(text(VERSION, SECTION, member))
        assert result.op_signature.key == OP_KEY
        assert op_key_of(result.op_signature.record) == OP_KEY
        assert result.others == {}


# The Example of ADR-0031, as written in the record: the shape of the member, not a valid file.
EXAMPLE_OF_ADR_0031 = b"""{
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
  },
  "op_signature": {
    "key": "gemm-485b9bc494d477eb",
    "record": {
      "schema_version": 1,
      "kind": "gemm",
      "shape": {"m": 1, "k": 2048, "n": 8192},
      "dtype": "fp32",
      "layout": "row_major"
    }
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10,
  "candidates_per_round": 2
}
"""
EXAMPLE_SOURCE = b'"hw_source": "NOT-DECIDED-HERE"'
EXAMPLE_FILE = EXAMPLE_OF_ADR_0031.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
EXAMPLE_OP_KEY = "gemm-485b9bc494d477eb"
EXAMPLE_OP_KEY_OF_M_32 = "gemm-a463eb52b19cfa97"


def example_op(**changes):
    made = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 1, "k": 2048, "n": 8192},
        "dtype": "fp32",
        "layout": "row_major",
    }
    for name, value in changes.items():
        made[name] = value
    return {name: value for name, value in made.items() if value is not REMOVE}


def test_the_member_of_the_example_of_adr_0031():
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0031)

    result = parse(EXAMPLE_FILE)
    assert result.op_signature == OpSignature(EXAMPLE_OP_KEY, example_op())
    assert op_key_of(example_op()) == EXAMPLE_OP_KEY
    assert op_key_of(example_op(shape={"m": 32, "k": 2048, "n": 8192})) == (
        EXAMPLE_OP_KEY_OF_M_32
    )
    assert result.candidates_per_round == 2
    assert result.n_max == 10
    assert result.source_commit == COMMIT
    assert result.tolerance == Tolerance(0.0001, 0.01)
    assert result.others == {}

    silent = parse(
        EXAMPLE_OF_ADR_0028.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
    )
    assert silent.op_signature is None
    assert silent[:6] == result[:6]


# --- branch: the member op_signature ---


def test_a_change_of_the_label_keeps_the_key_and_one_of_a_key_field_does_not():
    for label in ("x", "another label"):
        section = op_section(record=op_record(label=label))
        assert parse(raw(doc(op_signature=section))).op_signature == (
            OpSignature(OP_KEY, op_record(label=label))
        )
        assert validate(doc(op_signature=section)) is None
    for changed in (
        op_record(shape={"m": 4, "k": 5, "n": 7}),
        op_record(shape={"m": 3, "k": 6, "n": 7}),
        op_record(shape={"m": 3, "k": 5, "n": 8}),
        op_record(dtype="dtype_b"),
        op_record(layout="layout_b"),
        op_record(ext={"example": 1}),
    ):
        document = doc(op_signature=op_section(record=changed))
        expected = (
            f"op_signature.key: must be {op_key_of(changed)}, "
            f"the name derived from op_signature.record, got str '{OP_KEY}'"
        )
        assert invalid("op_signature.key: ", parse, raw(document)) == expected
        assert invalid("op_signature.key: ", validate, document) == expected
        assert validate(doc(op_signature=stating(changed))) is None


@pytest.mark.parametrize("profile", [record(), OTHER_RECORD], ids=["a", "b"])
@pytest.mark.parametrize("case", OP_RECORDS)
@pytest.mark.parametrize("tolerance", [REMOVE, TOLERANCE, {"rtol": 0, "atol": 0}])
def test_the_member_the_hw_profile_and_the_tolerance_are_valid_each_by_itself(
    profile, case, tolerance
):
    stated_record = OP_RECORDS[case]
    changes = {"op_signature": stating(stated_record)}
    if tolerance is not REMOVE:
        changes["tolerance"] = tolerance
    document = doc(profile, **changes)

    result = parse(raw(document))

    assert (result.hw_profile_key, result.hw_profile) == (key_of(profile), profile)
    assert result.op_signature == OpSignature(op_key_of(stated_record), stated_record)
    assert (result.tolerance is None) == (tolerance is REMOVE)
    assert validate(document) is None


BROKEN_OPS = [
    None,
    OP_KEY,
    7,
    True,
    [],
    [stating(op_record())],
    {},
    {"key": OP_KEY},
    op_section(key=OTHER_OP_KEY),
    op_section(record=op_record(kind="attention")),
]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("value", [*BROKEN_OPS, stating(op_record())], ids=shown)
def test_another_version_is_reported_before_the_op_signature_is_looked_at(
    version, value
):
    document = doc(schema_version=version, op_signature=value)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"op": stating(op_record())},
        {"opSignature": stating(op_record())},
        {"op-signature": stating(op_record())},
        {"Op_signature": stating(op_record())},
        {"OP_SIGNATURE": stating(op_record())},
        {"op_signature ": None},
        {"op_signatures": [stating(op_record())]},
        {"operation": OP_KEY, "kernel": OP_KEY},
        {"task": {"op_signature": stating(op_record())}},
        {"op": None, "opSignature": OP_KEY, "task": {"op_signature": 7}},
    ],
    ids=shown,
)
def test_a_top_level_member_of_another_name_states_no_op_signature(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
    assert result.op_signature is None
    assert validate(doc(**others)) is None

    result = parse(raw(doc(op_signature=stating(OTHER_OP), **others)))
    assert result.op_signature == OpSignature(OTHER_OP_KEY, OTHER_OP)
    assert result.others == others


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "op_signature": None}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "op_signature": OP_KEY},
        ),
        (
            "hw_profile.key: ",
            {"hw_profile": section(key=OTHER_KEY), "op_signature": {}},
        ),
        ("tolerance: must be", {"tolerance": None, "op_signature": None}),
        (NO_COMMIT + "str 'main'", {"source_commit": "main", "op_signature": []}),
        (NO_BOUND + "int", {"n_max": 4, "op_signature": None}),
        (
            NO_COUNT + "int",
            {**OP_MEMBERS, "candidates_per_round": 0, "op_signature": None},
        ),
        ("op_signature: must be an object, got NoneType", {"op_signature": None}),
        (
            "op_signature: must be an object, got list",
            {**OP_MEMBERS, "op_signature": []},
        ),
        ("op_signature: must be an object without", {"op_signature": {"example": 1}}),
        (
            "op_signature: must be an object without",
            {"op_signature": {"key": 7, "example": 1}},
        ),
        ("op_signature: lacks the member key", {"op_signature": {"record": None}}),
        ("op_signature: lacks the member record", {"op_signature": {"key": 7}}),
        (
            "op_signature.key: must be a str",
            {"op_signature": {"key": 7, "record": None}},
        ),
        (
            "op_signature.key: must be a str",
            {"op_signature": {"key": 7, "record": op_record(kind="Gemm")}},
        ),
        (
            "op_signature.record: must be an object",
            {"op_signature": {"key": "", "record": None}},
        ),
        (
            "op_signature.record.kind",
            {"op_signature": {"key": "", "record": op_record(kind="Gemm")}},
        ),
        ("op_signature.key: must be gemm-", {"op_signature": op_section(key="")}),
    ],
)
def test_the_first_broken_rule_is_reported_with_an_op_signature(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member op_signature ---


@pytest.mark.parametrize(
    "value",
    [None, [], [stating(op_record())], "text", OP_KEY, "", 7, 0, 1.5, True, False],
    ids=shown,
)
def test_an_op_signature_that_is_no_object(value):
    document = doc(**OP_MEMBERS, op_signature=value, example=[1])
    expected = "op_signature: must be an object, got " + type(value).__name__
    if type(value) is str:
        expected += " " + reprlib.repr(value)

    assert invalid("op_signature: ", parse, raw(document)) == expected
    assert invalid("op_signature: ", validate, document) == expected
    del document["op_signature"]
    assert parse(raw(document)).op_signature is None


@pytest.mark.parametrize(
    ("place", "op_signature"),
    [
        ("op_signature: lacks the member key", {}),
        ("op_signature: lacks the member key", op_section(key=REMOVE)),
        ("op_signature: lacks the member record", op_section(record=REMOVE)),
        (
            "op_signature: must be an object without the member, got str 'label'",
            op_section(label="x"),
        ),
        (
            "op_signature: must be an object without the member, got str 'schema_version'",
            op_section(schema_version=1),
        ),
        (
            "op_signature: must be an object without the member, got str 'schema_version'",
            op_record(),
        ),
        (
            "op_signature: must be an object without the member, got str 'Key'",
            {"Key": OP_KEY, "record": op_record()},
        ),
        (
            "op_signature: must be an object without the member, got str 'hw_profile'",
            op_section(hw_profile=section()),
        ),
        ("op_signature.key: must be a str, got int", op_section(key=7)),
        ("op_signature.key: must be a str, got NoneType", op_section(key=None)),
        ("op_signature.key: must be a str, got bool", op_section(key=True)),
        ("op_signature.key: must be a str, got list", op_section(key=[OP_KEY])),
        ("op_signature.key: must be a str, got dict", op_section(key={"name": OP_KEY})),
        (
            "op_signature.record: must be an object, got NoneType",
            op_section(record=None),
        ),
        ("op_signature.record: must be an object, got list", op_section(record=[])),
        (
            "op_signature.record: must be an object, got list",
            op_section(record=[op_record()]),
        ),
        (
            "op_signature.record: must be an object, got str 'text'",
            op_section(record="text"),
        ),
        ("op_signature.record: must be an object, got str", op_section(record=OP_KEY)),
        ("op_signature.record: must be an object, got int", op_section(record=7)),
        ("op_signature.record: must be an object, got bool", op_section(record=True)),
    ],
)
def test_an_op_signature_that_is_not_the_closed_object(place, op_signature):
    document = doc(op_signature=op_signature)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


@pytest.mark.parametrize(
    "key",
    [
        "",
        " ",
        OTHER_OP_KEY,
        op_key_of(op_record(dtype="dtype_b")),
        "gemm",
        OP_KEY.upper(),
        OP_KEY[:-1],
        OP_KEY + "0",
        " " + OP_KEY,
        OP_KEY + "\n",
        OP_KEY.replace("-", "_"),
        keys.op_signature_key(op_record()).digest,
        "../" + OP_KEY,
        KEY,
    ],
)
def test_a_key_that_is_not_the_name_derived_from_the_op_signature_record(key):
    document = doc(op_signature=op_section(key=key))

    assert invalid(NO_OP_KEY, parse, raw(document)) == (
        NO_OP_KEY + f"str {reprlib.repr(key)}"
    )
    assert invalid(NO_OP_KEY, validate, document) == (
        NO_OP_KEY + f"str {reprlib.repr(key)}"
    )


OP_RECORD = "op_signature.record."


@pytest.mark.parametrize(
    ("place", "stated_record"),
    [
        (OP_RECORD + "schema_version: required", {}),
        (OP_RECORD + "schema_version: required", op_record(schema_version=REMOVE)),
        (OP_RECORD + "kind: required", op_record(kind=REMOVE)),
        (OP_RECORD + "shape: required", op_record(shape=REMOVE)),
        (OP_RECORD + "dtype: required", op_record(dtype=REMOVE)),
        (OP_RECORD + "layout: required", op_record(layout=REMOVE)),
        (OP_RECORD + "schema_version: must be", op_record(schema_version=2)),
        (OP_RECORD + "schema_version: must be", op_record(schema_version=True)),
        (OP_RECORD + "kind: must be a name", op_record(kind="Gemm")),
        (OP_RECORD + "kind: must be a name", op_record(kind=7)),
        (OP_RECORD + "shape: must be a map", op_record(shape=[3, 5, 7])),
        (OP_RECORD + "shape: must be a map with", op_record(shape={})),
        (OP_RECORD + "shape: must be a map with", op_record(shape={"k": 5, "n": 7})),
        (
            OP_RECORD + "shape: must be a map with",
            op_record(shape={"m": 3, "k": 5, "n": 7, "p": 1}),
        ),
        (OP_RECORD + "shape.m: must be", op_record(shape={"m": 3.0, "k": 5, "n": 7})),
        (OP_RECORD + "shape.m: must be", op_record(shape={"m": -1, "k": 5, "n": 7})),
        (
            OP_RECORD + "shape.k: must be",
            op_record(shape={"m": 3, "k": 2**53, "n": 7}),
        ),
        (OP_RECORD + "shape.n: must be", op_record(shape={"m": 3, "k": 5, "n": "7"})),
        (OP_RECORD + "shape: member name", op_record(shape={"M": 3, "k": 5, "n": 7})),
        (OP_RECORD + "dtype: must be a name", op_record(dtype="FP32")),
        (OP_RECORD + "dtype: must be a name", op_record(dtype=None)),
        (OP_RECORD + "layout: must be a name", op_record(layout="row major")),
        (OP_RECORD + "ext: must be", op_record(ext={})),
        (OP_RECORD + "ext.example: must be", op_record(ext={"example": None})),
        (OP_RECORD + "label: must be", op_record(label="")),
        (OP_RECORD + "'language': unknown field", op_record(language="c")),
        (OP_RECORD + "'key': unknown field", op_record(key=OP_KEY)),
        (OP_RECORD + "'hw_source': unknown field", op_record(hw_source="external")),
        (OP_RECORD + "'accelerator': unknown field", record()),
    ],
)
@pytest.mark.parametrize("key", [OP_KEY, OTHER_OP_KEY, ""])
def test_an_op_signature_record_that_is_not_valid_by_adr_0001(
    place, stated_record, key
):
    document = doc(op_signature={"key": key, "record": stated_record})

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


@pytest.mark.parametrize("kind", ["attention", "conv", "gemm2", "matmul"])
@pytest.mark.parametrize("key", [OP_KEY, "", "attention-0123456789abcdef"])
def test_a_record_of_a_kind_the_keys_module_does_not_know(kind, key):
    unknown = op_record(kind=kind)
    with pytest.raises(keys.InvalidRecordError) as refused:
        keys.op_signature_key(unknown)
    document = doc(**OP_MEMBERS, op_signature={"key": key, "record": unknown})

    assert invalid(OP_RECORD, parse, raw(document)) == OP_RECORD + str(refused.value)
    assert invalid(OP_RECORD, validate, document) == OP_RECORD + str(refused.value)
    assert str(refused.value).startswith("kind: must be a known kind")


WALK_THROUGH_OF_ADR_0031 = {
    "the key of the m 32 record": (
        {"key": EXAMPLE_OP_KEY_OF_M_32, "record": example_op()},
        (
            f"op_signature.key: must be {EXAMPLE_OP_KEY}, the name derived from "
            f"op_signature.record, got str '{EXAMPLE_OP_KEY_OF_M_32}'"
        ),
    ),
    "no layout": (
        {"key": EXAMPLE_OP_KEY, "record": example_op(layout=REMOVE)},
        "op_signature.record.layout: required field is missing",
    ),
    "a shape without m": (
        {"key": EXAMPLE_OP_KEY, "record": example_op(shape={"k": 2048, "n": 8192})},
        "op_signature.record.shape: must be a map with exactly the members k, m, n",
    ),
    "the dtype FP32": (
        {"key": EXAMPLE_OP_KEY, "record": example_op(dtype="FP32")},
        "op_signature.record.dtype: must be a name",
    ),
    "a member language": (
        {"key": EXAMPLE_OP_KEY, "record": example_op(language="c")},
        "op_signature.record.'language': unknown field",
    ),
    "the key string alone": (
        EXAMPLE_OP_KEY,
        f"op_signature: must be an object, got str '{EXAMPLE_OP_KEY}'",
    ),
    "null": (None, "op_signature: must be an object, got NoneType"),
    "an array": ([], "op_signature: must be an object, got list"),
    "an array of one valid object": (
        [{"key": EXAMPLE_OP_KEY, "record": example_op()}],
        "op_signature: must be an object, got list",
    ),
}


@pytest.mark.parametrize("row", WALK_THROUGH_OF_ADR_0031)
def test_the_invalid_files_of_the_walk_through_of_adr_0031(root, row):
    value, reason = WALK_THROUGH_OF_ADR_0031[row]
    document = json.loads(EXAMPLE_FILE)
    assert document["op_signature"] == {"key": EXAMPLE_OP_KEY, "record": example_op()}
    document["op_signature"] = value

    invalid(reason, parse, raw(document))
    invalid(reason, validate, document)
    place(root, raw(document))
    invalid(f"{FILE}: {reason}", read, root, RUN)
    invalid(f"{FILE}: {reason}", op_signature_of, root, RUN)
    invalid(f"{FILE}: {reason}", hw_profile_of, root, RUN)

    for renamed in (value, {"key": EXAMPLE_OP_KEY, "record": example_op()}):
        del document["op_signature"]
        document["op"] = renamed
        place(root, raw(document))
        assert op_signature_of(root, RUN) is None
        assert read(root, RUN).others == {"op": renamed}
        document["op_signature"] = document.pop("op")
    assert hw_profile_of(root, RUN)["accelerator"] == "cpu_standin"
    assert tolerance_of(root, RUN) == Tolerance(0.0001, 0.01)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == 10
    assert candidates_per_round_of(root, RUN) == 2


@pytest.mark.parametrize(
    "members",
    [
        (OP_SECTION, OP_SECTION),
        (OP_SECTION, '"op_signature": null'),
        ('"op_signature": null', OP_SECTION),
        (OP_SECTION, f'"op_signature": {json.dumps(stating(OTHER_OP))}'),
        (f'"op_signature": {{"key": "{OP_KEY}", "key": "{OP_KEY}", "record": {{}}}}',),
        (
            (
                f'"op_signature": {{"key": "{OP_KEY}", "record": '
                '{"schema_version": 1, "kind": "gemm", "kind": "gemm"}}'
            ),
        ),
        (
            OP_SECTION.replace(
                '{"m": 3, "k": 5, "n": 7}', '{"m": 3, "m": 3, "k": 5, "n": 7}'
            ),
        ),
    ],
)
def test_a_member_name_twice_with_an_op_signature_is_a_text_error(members):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, *members),
    )
    assert "a JSON object repeats a member name" in message
    assert "op_signature" not in message


def test_an_integer_too_long_inside_the_member_is_a_text_error():
    member = OP_SECTION.replace('"m": 3', f'"m": {TOO_LONG_TEXT}')

    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, member),
    )
    assert "op_signature" not in message


class Map(dict):
    pass


def test_validate_refuses_an_op_signature_built_in_memory():
    looped = {"k": 5, "n": 7}
    looped["m"] = looped
    for place_of, value in (
        ("op_signature: must be an object, got Map", Map(stating(op_record()))),
        ("op_signature: must be an object, got tuple", (OP_KEY, op_record())),
        (
            "op_signature: must be an object, got OpSignature",
            OpSignature(OP_KEY, op_record()),
        ),
        ("op_signature.key: must be a str, got Text", op_section(key=Text(OP_KEY))),
        ("op_signature.key: must be a str, got bytes", op_section(key=OP_KEY.encode())),
        (
            "op_signature.record: must be an object, got Map",
            op_section(record=Map(op_record())),
        ),
        (
            "op_signature.record.shape.m: must be",
            op_section(record=op_record(shape=looped)),
        ),
        (
            "op_signature.record.ext.m: must be",
            op_section(record=op_record(ext=looped)),
        ),
        (
            "op_signature.record.shape: must be a map with",
            op_section(record=op_record(shape=Map())),
        ),
        (
            "op_signature.record.kind: must be a name",
            op_section(record=op_record(kind=Text("gemm"))),
        ),
        (
            "op_signature.record.1: unknown field",
            op_section(record={**op_record(), 1: 2}),
        ),
    ):
        invalid(place_of, validate, doc(op_signature=value))

    assert (
        validate(
            doc(op_signature=op_section(record=op_record(shape=Map(m=3, k=5, n=7))))
        )
        is None
    )


def test_a_long_key_is_shown_shortened():
    document = doc(op_signature=op_section(key="gemm-" + "0" * 200))

    message = invalid(NO_OP_KEY, validate, document)

    assert message == NO_OP_KEY + "str " + reprlib.repr("gemm-" + "0" * 200)
    assert len(message) < 160


def test_a_check_of_an_op_signature_modifies_nothing():
    for valid, value in (
        (True, stating(op_record(label="x", ext={"example": 1}))),
        (False, op_section(key=OTHER_OP_KEY)),
        (False, op_section(record=op_record(kind="attention"))),
        (False, op_section(record=op_record(layout=REMOVE))),
        (False, None),
    ):
        document = doc(op_signature=value)
        kept = json.dumps(document)
        assert accepted(validate, document) == valid
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module stands in for the op_signature ---


@pytest.mark.parametrize(
    "document",
    [
        doc(),
        doc(**OP_MEMBERS),
        doc(op=stating(op_record())),
        doc(task={"op_signature": stating(op_record())}),
        doc(OTHER_RECORD, op_signatures=[stating(op_record())]),
    ],
    ids=shown,
)
def test_a_content_without_the_member_states_none_and_nothing_else(document):
    result = parse(raw(document))

    assert result.op_signature is None
    assert result._asdict()["op_signature"] is None
    assert validate(document) is None


def test_nothing_of_the_module_stands_in_for_the_op_signature():
    functions = [
        value
        for value in vars(instance).values()
        if inspect.isfunction(value) and value.__module__ == instance.__name__
    ]
    assert op_signature_of in functions
    for function in functions:
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert OpSignature._field_defaults == Instance._field_defaults == {}
    held = [
        name
        for name, value in vars(instance).items()
        if isinstance(value, (OpSignature, keys.Key))
    ]
    assert held == []

    tree = ast.parse(inspect.getsource(instance))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert "hilclaw.keys" in imported
    assert not [name for name in imported if "spec" in name or "key_records" in name]
    documented = (ast.Module, ast.ClassDef, ast.FunctionDef)
    docstrings = {
        ast.get_docstring(node, clean=False)
        for node in ast.walk(tree)
        if isinstance(node, documented)
    }
    written = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and type(node.value) is str
    } - docstrings
    for word in ("gemm", "attention", "fp32", "row_major"):
        assert not [value for value in written if word in value]


def test_the_module_does_not_load_the_spec_or_the_key_records():
    code = (
        "import sys, hilclaw.instance; "
        "print(sorted(name for name in sys.modules "
        "if name in ('hilclaw.spec', 'hilclaw.spec_file', 'hilclaw.key_records')))"
    )

    done = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )

    assert done.stdout.strip() == "[]"


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
        == Instance(
            KEY,
            record(),
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            {"example": [1, 2]},
        )
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


# --- the reader of the source commit ---


def test_the_reader_returns_the_source_commit_the_file_states(tmp_path, root):
    place(root, raw(doc(tolerance=TOLERANCE, source_commit=COMMIT, example=[1])))
    before = snapshot(tmp_path)

    found = source_commit_of(root, RUN)

    assert found == COMMIT and type(found) is str
    assert found == read(root, RUN).source_commit
    assert source_commit_of(str(root), RUN) == found
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert snapshot(tmp_path) == before

    place(root, raw(doc(source_commit=LONG_COMMIT)))
    assert source_commit_of(root, RUN) == LONG_COMMIT


def test_a_run_without_the_member_states_no_source_commit(tmp_path, root):
    others = {"source-commit": COMMIT, "commit": OTHER_COMMIT, "sourceCommit": COMMIT}
    place(root, raw(doc(tolerance=TOLERANCE, **others)))
    before = snapshot(tmp_path)

    assert source_commit_of(root, RUN) is None
    assert read(root, RUN).source_commit is None
    assert read(root, RUN).others == others
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert snapshot(tmp_path) == before


def refuse(*arguments, **options):
    raise AssertionError("a process was started")


def test_no_value_is_substituted_inside_a_checkout(tmp_path, monkeypatch):
    checkout = tmp_path / "checkout"
    place(checkout, f"{OTHER_COMMIT}\n".encode(), ".git/HEAD")
    place(checkout, f"{OTHER_COMMIT}\n".encode(), ".git/ORIG_HEAD")
    place(checkout, f"{OTHER_COMMIT}\n".encode(), ".git/refs/heads/main")
    place(checkout, raw(doc()))
    place(checkout, raw(doc(source_commit=COMMIT)), f"runs/{OTHER_RUN}/instance.json")
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setattr(subprocess, "run", refuse)
    for name in ("GIT_COMMIT", "GITHUB_SHA", "SOURCE_COMMIT", "HILCLAW_SOURCE_COMMIT"):
        monkeypatch.setenv(name, OTHER_COMMIT)
    before = snapshot(tmp_path)

    for directory in (checkout, checkout / ".git", Path(__file__).resolve().parents[1]):
        monkeypatch.chdir(directory)
        assert source_commit_of(checkout, RUN) is None
        assert read(checkout, RUN).source_commit is None
        assert source_commit_of(checkout, OTHER_RUN) == COMMIT
    monkeypatch.chdir(checkout)
    assert source_commit_of(".", RUN) is None
    assert source_commit_of(Path("."), OTHER_RUN) == COMMIT

    assert snapshot(tmp_path) == before


def test_a_source_commit_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(source_commit=COMMIT)))
    assert source_commit_of(root, RUN) == COMMIT

    place(root, raw(doc(source_commit=OTHER_COMMIT)))
    assert source_commit_of(root, RUN) == OTHER_COMMIT

    place(root, raw(doc()))
    assert source_commit_of(root, RUN) is None

    place(root, raw(doc(schema_version=2, source_commit=COMMIT)))
    with pytest.raises(UnsupportedVersionError):
        source_commit_of(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        source_commit_of(root, RUN)

    place(root, raw(doc(source_commit=LONG_COMMIT)))
    assert source_commit_of(root, RUN) == LONG_COMMIT


@pytest.mark.parametrize("value", ["main", COMMIT[:7], COMMIT.upper(), False, None])
def test_no_member_of_a_file_with_an_invalid_source_commit_is_used(root, value):
    place(root, raw(doc(tolerance=TOLERANCE, source_commit=COMMIT)))
    assert source_commit_of(root, RUN) == COMMIT

    place(root, raw(doc(tolerance=TOLERANCE, source_commit=value)))
    for call in READERS:
        invalid(f"{FILE}: {NO_COMMIT}{type(value).__name__}", call, root, RUN)

    place(root, raw(doc(tolerance=TOLERANCE)))
    assert source_commit_of(root, RUN) is None
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)


def test_two_runs_state_their_own_source_commits(root):
    place(root, raw(doc(source_commit=COMMIT)))
    place(root, raw(doc(source_commit=LONG_COMMIT)), f"runs/{OTHER_RUN}/instance.json")
    place(root, raw(doc()), "runs/run-c/instance.json")

    assert source_commit_of(root, RUN) == COMMIT
    assert source_commit_of(root, OTHER_RUN) == LONG_COMMIT
    assert source_commit_of(root, "run-c") is None
    assert source_commit_of(root, RUN) == COMMIT


def test_the_reader_of_the_source_commit_opens_only_the_instance_file(
    root, monkeypatch
):
    place(root, raw(doc(source_commit=COMMIT)))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    place(root, f"{OTHER_COMMIT}\n".encode(), ".git/HEAD")
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setattr(subprocess, "Popen", refuse)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert source_commit_of(root, RUN) == COMMIT
    assert opened == [FILE]

    place(root, raw(doc()))
    assert source_commit_of(root, RUN) is None
    assert opened == [FILE, FILE]


# --- the reader of the bound of repeats ---


def test_the_reader_returns_the_bound_the_file_states(tmp_path, root):
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT}
    place(root, raw(doc(**members, n_max=BOUND, example=[1])))
    before = snapshot(tmp_path)

    found = n_max_of(root, RUN)

    assert found == BOUND and type(found) is int
    assert found == read(root, RUN).n_max
    assert n_max_of(str(root), RUN) == found
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert snapshot(tmp_path) == before

    for bound in (5, 10, 11, MAX):
        place(root, raw(doc(n_max=bound)))
        assert n_max_of(root, RUN) == bound
        assert type(n_max_of(root, RUN)) is int


def test_a_run_without_the_member_states_no_bound(tmp_path, root, monkeypatch):
    others = {"nmax": BOUND, "N_max": BOUND, "n-max": BOUND, "nMax": BOUND}
    place(root, raw(doc(tolerance=TOLERANCE, source_commit=COMMIT, **others)))
    place(root, raw(doc(n_max=OTHER_BOUND)), f"runs/{OTHER_RUN}/instance.json")
    for name in ("N_MAX", "HILCLAW_N_MAX", "N_MAX_DEFAULT"):
        monkeypatch.setenv(name, str(BOUND))
    before = snapshot(tmp_path)

    assert type(measurement.N_MAX_DEFAULT) is int
    assert n_max_of(root, RUN) is None
    assert read(root, RUN).n_max is None
    assert read(root, RUN).others == others
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, OTHER_RUN) == OTHER_BOUND
    assert n_max_of(root, RUN) is None
    assert snapshot(tmp_path) == before


def test_a_bound_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(n_max=BOUND)))
    assert n_max_of(root, RUN) == BOUND

    place(root, raw(doc(n_max=OTHER_BOUND)))
    assert n_max_of(root, RUN) == OTHER_BOUND

    place(root, raw(doc()))
    assert n_max_of(root, RUN) is None

    place(root, raw(doc(n_max=4)))
    invalid(f"{FILE}: {NO_BOUND}int", n_max_of, root, RUN)

    place(root, raw(doc(schema_version=2, n_max=BOUND)))
    with pytest.raises(UnsupportedVersionError):
        n_max_of(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        n_max_of(root, RUN)

    place(root, raw(doc(n_max=5)))
    assert n_max_of(root, RUN) == 5


@pytest.mark.parametrize(
    "literal",
    [
        "4",
        "0",
        "-0",
        "-10",
        "10.0",
        "1e1",
        '"10"',
        "true",
        "null",
        "[10]",
        "9007199254740992",
    ],
)
def test_no_member_of_a_file_with_an_invalid_n_max_is_used(root, literal):
    more = (MEMBERS[2], MEMBERS[3])
    place(root, bounded(str(BOUND), *more))
    assert n_max_of(root, RUN) == BOUND

    place(root, bounded(literal, *more))
    for call in READERS:
        invalid(f"{FILE}: {NO_BOUND}", call, root, RUN)

    place(root, text(VERSION, SECTION, *more))
    assert n_max_of(root, RUN) is None
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT


def test_two_runs_state_their_own_bounds(root):
    place(root, raw(doc(n_max=12)))
    place(root, raw(doc(n_max=5)), f"runs/{OTHER_RUN}/instance.json")
    place(root, raw(doc()), "runs/run-c/instance.json")

    assert n_max_of(root, RUN) == 12
    assert n_max_of(root, OTHER_RUN) == 5
    assert n_max_of(root, "run-c") is None
    assert n_max_of(root, RUN) == 12


def test_the_reader_of_the_bound_opens_only_the_instance_file(root, monkeypatch):
    place(root, raw(doc(n_max=BOUND)))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    place(root, raw(doc(n_max=OTHER_BOUND)), f"runs/{OTHER_RUN}/instance.json")
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert n_max_of(root, RUN) == BOUND
    assert opened == [FILE]

    place(root, raw(doc()))
    assert n_max_of(root, RUN) is None
    assert opened == [FILE, FILE]


# --- the reader of the number of candidates per round (ADR-0028) ---


def test_the_reader_returns_the_number_the_file_states(tmp_path, root):
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT, "n_max": BOUND}
    place(root, raw(doc(**members, candidates_per_round=COUNT, example=[1])))
    before = snapshot(tmp_path)

    found = candidates_per_round_of(root, RUN)

    assert found == COUNT and type(found) is int
    assert found == read(root, RUN).candidates_per_round
    assert candidates_per_round_of(str(root), RUN) == found
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == BOUND
    assert snapshot(tmp_path) == before

    for count in (1, 2, 5, 6, 100, MAX):
        place(root, raw(doc(candidates_per_round=count)))
        assert candidates_per_round_of(root, RUN) == count
        assert type(candidates_per_round_of(root, RUN)) is int


def test_a_run_without_the_member_states_no_number(tmp_path, root, monkeypatch):
    others = {
        "candidates": COUNT,
        "n": COUNT,
        "candidatesPerRound": COUNT,
        "candidates-per-round": COUNT,
        "id": {"candidates": COUNT},
    }
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT, "n_max": BOUND}
    place(root, raw(doc(**members, **others)))
    place(root, raw(doc(candidates_per_round=OTHER_COUNT)), OTHER_FILE)
    for name in ("N", "CANDIDATES_PER_ROUND", "HILCLAW_CANDIDATES_PER_ROUND"):
        monkeypatch.setenv(name, str(COUNT))
    before = snapshot(tmp_path)

    assert candidates_per_round_of(root, RUN) is None
    assert read(root, RUN).candidates_per_round is None
    assert read(root, RUN).others == others
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == BOUND
    assert candidates_per_round_of(root, OTHER_RUN) == OTHER_COUNT
    assert candidates_per_round_of(root, RUN) is None
    assert snapshot(tmp_path) == before

    place(root, raw(doc()))
    assert candidates_per_round_of(root, RUN) is None


def test_a_number_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(candidates_per_round=COUNT)))
    assert candidates_per_round_of(root, RUN) == COUNT

    place(root, raw(doc(candidates_per_round=OTHER_COUNT)))
    assert candidates_per_round_of(root, RUN) == OTHER_COUNT

    place(root, raw(doc()))
    assert candidates_per_round_of(root, RUN) is None

    place(root, raw(doc(candidates_per_round=0)))
    invalid(f"{FILE}: {NO_COUNT}int", candidates_per_round_of, root, RUN)

    place(root, raw(doc(schema_version=2, candidates_per_round=COUNT)))
    with pytest.raises(UnsupportedVersionError):
        candidates_per_round_of(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        candidates_per_round_of(root, RUN)

    place(root, raw(doc(candidates_per_round=1)))
    assert candidates_per_round_of(root, RUN) == 1


@pytest.mark.parametrize(
    "literal", [*WALK_THROUGH_OF_ADR_0028, "-0", "false", "{}", "1.5"]
)
def test_no_member_of_a_file_with_an_invalid_candidates_per_round_is_used(
    root, literal
):
    more = (MEMBERS[2], MEMBERS[3], BOUNDED_MEMBERS[4])
    place(root, counted(str(COUNT), *more))
    assert candidates_per_round_of(root, RUN) == COUNT

    place(root, counted(literal, *more))
    assert candidates_per_round_of in READERS and len(READERS) == 12
    for call in READERS:
        invalid(f"{FILE}: {NO_COUNT}", call, root, RUN)

    place(root, text(VERSION, SECTION, *more))
    assert candidates_per_round_of(root, RUN) is None
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == BOUND
    assert layout_version_of(root, RUN) == 1


def test_two_runs_state_their_own_numbers(root):
    place(root, raw(doc(candidates_per_round=1)))
    place(root, raw(doc(candidates_per_round=3)), OTHER_FILE)
    place(root, raw(doc()), "runs/run-c/instance.json")

    assert candidates_per_round_of(root, RUN) == 1
    assert candidates_per_round_of(root, OTHER_RUN) == 3
    assert candidates_per_round_of(root, "run-c") is None
    assert candidates_per_round_of(root, RUN) == 1


def test_the_reader_of_the_number_opens_only_the_instance_file(root, monkeypatch):
    place(root, raw(doc(candidates_per_round=COUNT)))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    place(root, b"{}", f"runs/{RUN}/rounds/0001/candidates/01/spec.json")
    place(root, raw(doc(candidates_per_round=OTHER_COUNT)), OTHER_FILE)
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert candidates_per_round_of(root, RUN) == COUNT
    assert opened == [FILE]

    place(root, raw(doc()))
    assert candidates_per_round_of(root, RUN) is None
    assert opened == [FILE, FILE]


# --- the reader of the op_signature (ADR-0031) ---


def test_the_reader_returns_the_op_signature_the_file_states(tmp_path, root):
    stated_record = op_record(label="of this run", ext={"example": 1})
    place(root, raw(doc(**OP_MEMBERS, op_signature=stating(stated_record), x=[1])))
    before = snapshot(tmp_path)

    found = op_signature_of(root, RUN)

    assert found == OpSignature(op_key_of(stated_record), stated_record)
    assert type(found) is OpSignature
    assert type(found.key) is str and type(found.record) is dict
    assert found == read(root, RUN).op_signature
    assert op_signature_of(str(root), RUN) == found
    assert op_signature_of(Path(root), RUN) == found
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == BOUND
    assert candidates_per_round_of(root, RUN) == COUNT
    assert snapshot(tmp_path) == before

    place(root, EXAMPLE_FILE)
    assert op_signature_of(root, RUN) == OpSignature(EXAMPLE_OP_KEY, example_op())


def test_a_run_without_the_member_states_no_op_signature(tmp_path, root, monkeypatch):
    others = {
        "op": stating(op_record()),
        "opSignature": stating(op_record()),
        "op-signature": OP_KEY,
        "op_signatures": [stating(op_record())],
        "task": {"op_signature": stating(op_record())},
    }
    place(root, raw(doc(**OP_MEMBERS, **others)))
    place(root, raw(doc(op_signature=stating(OTHER_OP))), OTHER_FILE)
    place(
        root, json.dumps(op_record()).encode(), f"db/{KEY}/{OP_KEY}/op_signature.json"
    )
    spec = f"runs/{RUN}/rounds/0001/coder/candidates/01/attempts/01/spec.json"
    place(root, raw({"task": {"op_signature": stating(op_record())}}), spec)
    for name in ("OP_SIGNATURE", "HILCLAW_OP_SIGNATURE"):
        monkeypatch.setenv(name, OP_KEY)
    before = snapshot(tmp_path)

    assert op_signature_of(root, RUN) is None
    assert read(root, RUN).op_signature is None
    assert read(root, RUN).others == others
    assert hw_profile_of(root, RUN) == record()
    assert tolerance_of(root, RUN) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == BOUND
    assert candidates_per_round_of(root, RUN) == COUNT
    assert op_signature_of(root, OTHER_RUN) == OpSignature(OTHER_OP_KEY, OTHER_OP)
    assert op_signature_of(root, RUN) is None
    assert snapshot(tmp_path) == before

    place(root, raw(doc()))
    assert op_signature_of(root, RUN) is None


def test_an_op_signature_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(op_signature=stating(op_record()))))
    assert op_signature_of(root, RUN) == OpSignature(OP_KEY, op_record())

    place(root, raw(doc(op_signature=stating(OTHER_OP))))
    assert op_signature_of(root, RUN) == OpSignature(OTHER_OP_KEY, OTHER_OP)

    place(root, raw(doc()))
    assert op_signature_of(root, RUN) is None

    place(root, raw(doc(op_signature=op_section(key=OTHER_OP_KEY))))
    invalid(f"{FILE}: {NO_OP_KEY}", op_signature_of, root, RUN)

    place(root, raw(doc(schema_version=2, op_signature=stating(op_record()))))
    with pytest.raises(UnsupportedVersionError):
        op_signature_of(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        op_signature_of(root, RUN)

    place(root, raw(doc(op_signature=stating(op_record(label="again")))))
    assert op_signature_of(root, RUN) == OpSignature(OP_KEY, op_record(label="again"))


def test_each_call_returns_a_new_op_signature(root):
    place(root, raw(doc(op_signature=stating(op_record()))))

    first, second = op_signature_of(root, RUN), op_signature_of(root, RUN)
    assert first == second
    assert first is not second
    assert first.record is not second.record

    first.record["dtype"] = "changed"
    first.record["shape"]["m"] = 99
    assert op_signature_of(root, RUN) == OpSignature(OP_KEY, op_record())


@pytest.mark.parametrize(
    "value",
    [row[0] for row in WALK_THROUGH_OF_ADR_0031.values()]
    + [7, True, {}, {"key": EXAMPLE_OP_KEY}, {"record": example_op()}],
    ids=shown,
)
def test_no_member_of_a_file_with_an_invalid_op_signature_is_used(root, value):
    document = json.loads(EXAMPLE_FILE)
    place(root, raw(document))
    assert op_signature_of(root, RUN) == OpSignature(EXAMPLE_OP_KEY, example_op())

    document["op_signature"] = value
    place(root, raw(document))
    assert op_signature_of in READERS and len(READERS) == 12
    for call in READERS:
        invalid(f"{FILE}: op_signature", call, root, RUN)

    del document["op_signature"]
    place(root, raw(document))
    assert op_signature_of(root, RUN) is None
    assert hw_profile_of(root, RUN)["accelerator"] == "cpu_standin"
    assert tolerance_of(root, RUN) == Tolerance(0.0001, 0.01)
    assert source_commit_of(root, RUN) == COMMIT
    assert n_max_of(root, RUN) == 10
    assert candidates_per_round_of(root, RUN) == 2
    assert layout_version_of(root, RUN) == 1


def test_two_runs_that_differ_in_m_only_state_their_own_op_signatures(root):
    other = json.loads(EXAMPLE_FILE)
    other["op_signature"] = stating(example_op(shape={"m": 32, "k": 2048, "n": 8192}))
    place(root, EXAMPLE_FILE)
    place(root, raw(other), OTHER_FILE)
    place(root, raw(doc()), "runs/run-c/instance.json")

    first, second = op_signature_of(root, RUN), op_signature_of(root, OTHER_RUN)

    assert (first.key, second.key) == (EXAMPLE_OP_KEY, EXAMPLE_OP_KEY_OF_M_32)
    assert (first.record["shape"]["m"], second.record["shape"]["m"]) == (1, 32)
    assert {**first.record, "shape": None} == {**second.record, "shape": None}
    assert hw_profile_of(root, RUN) == hw_profile_of(root, OTHER_RUN)
    assert op_signature_of(root, "run-c") is None
    assert op_signature_of(root, RUN) == first


@pytest.mark.parametrize(
    "stored",
    [
        json.dumps(op_record(label="changed since")).encode(),
        json.dumps(OTHER_OP).encode(),
        b"",
        b"not JSON",
        None,
        REMOVE,
    ],
    ids=["another label", "another record", "empty", "no JSON", "no file", "no db"],
)
def test_the_reader_of_the_op_signature_opens_only_the_instance_file(
    tmp_path, root, monkeypatch, stored
):
    stated_record = op_record(label="of this run")
    place(root, raw(doc(op_signature=stating(stated_record))))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    spec = f"runs/{RUN}/rounds/0001/coder/candidates/01/attempts/01/spec.json"
    place(root, raw({"task": {"op_signature": stating(OTHER_OP)}}), spec)
    place(root, raw(doc(op_signature=stating(OTHER_OP))), OTHER_FILE)
    if stored is None:
        layout.op_signature_dir(root, KEY, OP_KEY).mkdir(parents=True)
    elif stored is not REMOVE:
        file = layout.op_signature_file(root, KEY, OP_KEY, "op_signature.json")
        place(root, stored, file.relative_to(root))
    before = snapshot(tmp_path)
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert op_signature_of(root, RUN) == OpSignature(OP_KEY, stated_record)
    assert opened == [FILE]

    monkeypatch.undo()
    assert snapshot(tmp_path) == before
    assert (root / "db").exists() == (stored is not REMOVE)


# --- the reader of the layout version (ADR-0024) ---

ALL_MEMBERS = {"tolerance": TOLERANCE, "source_commit": COMMIT, "n_max": BOUND}
OTHER_FILE = f"runs/{OTHER_RUN}/instance.json"


@pytest.mark.parametrize("members", [{}, ALL_MEMBERS, {"example": [1]}], ids=repr)
def test_the_reader_returns_the_layout_version_the_file_states(tmp_path, root, members):
    place(root, raw(doc(**members)))
    before = snapshot(tmp_path)

    found = layout_version_of(root, RUN)

    assert found == 1 and type(found) is int
    assert layout_version_of(str(root), RUN) == 1
    assert read(root, RUN) == parse(raw(doc(**members)))
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("stamp", [2, 99, 0, "2", None, [1]], ids=repr)
def test_a_member_that_looks_like_a_stamp_is_passed_over(root, stamp):
    others = {"layout_version": stamp, "layoutVersion": stamp}
    place(root, raw(doc(**others)))

    assert layout_version_of(root, RUN) == 1
    assert read(root, RUN).others == others
    assert parse(raw(doc(**others))).others == others
    assert validate(doc(**others)) is None


def test_the_layout_version_is_read_from_the_file_at_each_call(root):
    place(root, raw(doc()))
    assert layout_version_of(root, RUN) == 1

    place(root, raw(doc(schema_version=2)))
    with pytest.raises(UnsupportedVersionError):
        layout_version_of(root, RUN)

    place(root, raw(doc(**ALL_MEMBERS)))
    assert layout_version_of(root, RUN) == 1

    place(root, raw(doc(n_max=4)))
    invalid(f"{FILE}: {NO_BOUND}int", layout_version_of, root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        layout_version_of(root, RUN)

    place(root, raw(doc()))
    assert layout_version_of(root, RUN) == 1


def test_each_run_states_its_own_layout_version(root):
    place(root, raw(doc()))
    place(root, raw(doc(schema_version=2)), OTHER_FILE)

    assert layout_version_of(root, RUN) == 1
    with pytest.raises(UnsupportedVersionError) as caught:
        layout_version_of(root, OTHER_RUN)
    assert str(caught.value) == f"{OTHER_FILE}: schema_version: 2 is not supported"
    assert layout_version_of(root, RUN) == 1


BROKEN_AT_VERSION_1 = {
    "no hw_profile": {"hw_profile": REMOVE},
    "another key": {"hw_profile": section(key=OTHER_KEY)},
    "a tolerance with one value": {"tolerance": {"rtol": TEST_RTOL}},
    "an abbreviated source_commit": {"source_commit": COMMIT[:7]},
    "an n_max below 5": {"n_max": 4},
}


@pytest.mark.parametrize("case", BROKEN_AT_VERSION_1)
def test_an_invalid_file_that_holds_version_1_states_no_layout_version(root, case):
    document = doc(**BROKEN_AT_VERSION_1[case])
    assert document["schema_version"] == 1
    place(root, raw(document))

    invalid(f"{FILE}: ", layout_version_of, root, RUN)


@pytest.mark.parametrize("version", [REMOVE, 1.0, True, "1", None, -1, MAX + 1])
def test_a_version_that_is_no_integer_states_no_layout_version(root, version):
    place(root, raw(doc(schema_version=version)))

    invalid(f"{FILE}: ", layout_version_of, root, RUN)


@pytest.mark.parametrize("built", [0, 2, 99])
def test_the_layout_the_source_builds_does_not_stand_in(root, monkeypatch, built):
    place(root, raw(doc(layout_version=built)))
    place(root, raw(doc(schema_version=2)), OTHER_FILE)
    place(root, raw(doc(n_max=4)), "runs/run-c/instance.json")
    place(root, b"", "runs/run-d/instance.json")
    monkeypatch.setattr(layout, "LAYOUT_VERSION", built)

    assert layout_version_of(root, RUN) == 1
    with pytest.raises(UnsupportedVersionError):
        layout_version_of(root, OTHER_RUN)
    invalid("runs/run-c/instance.json: n_max: ", layout_version_of, root, "run-c")
    invalid("runs/run-d/instance.json: content: ", layout_version_of, root, "run-d")
    with pytest.raises(MissingInstanceError):
        layout_version_of(root, "run-e")


def test_the_module_does_not_name_the_layout_the_source_builds():
    tree = ast.parse(inspect.getsource(instance))
    named = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    named |= {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}

    assert "run_file" in named and "LAYOUT_VERSION" not in named
    assert layout_version_of.__defaults__ is None
    assert layout_version_of.__kwdefaults__ is None


def test_the_reader_of_the_layout_version_opens_only_the_instance_file(
    root, monkeypatch
):
    place(root, raw(doc()))
    place(root, b"{}", f"runs/{RUN}/STATE.json")
    place(root, b"", f"runs/{RUN}/events.ndjson")
    place(root, raw(doc(schema_version=2)), OTHER_FILE)
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert layout_version_of(root, RUN) == 1
    assert opened == [FILE]

    assert layout_version_of(root, RUN) == 1
    assert opened == [FILE, FILE]


# --- error / negative: the four situations of decision 4 ---

READERS = [
    read,
    hw_profile_of,
    tolerance_of,
    source_commit_of,
    n_max_of,
    candidates_per_round_of,
    op_signature_of,
    round_budget_of,
    wall_clock_budget_s_of,
    owner_of,
    project_of,
    layout_version_of,
]


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


@pytest.mark.parametrize("call", READERS)
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
    "a source_commit that is no string": (
        raw(doc(source_commit=False)),
        "source_commit: must be",
    ),
    "an abbreviated source_commit": (
        raw(doc(tolerance=TOLERANCE, source_commit=COMMIT[:7])),
        "source_commit: must be",
    ),
    "an n_max below 5": (raw(doc(n_max=4)), "n_max: must be"),
    "an n_max that is no integer": (
        raw(doc(tolerance=TOLERANCE, source_commit=COMMIT, n_max=10.0)),
        "n_max: must be",
    ),
    "an op_signature that is no object": (
        raw(doc(op_signature=OP_KEY)),
        "op_signature: must be an object, got str",
    ),
    "an op_signature whose key is not the derived name": (
        raw(doc(**OP_MEMBERS, op_signature=op_section(key=OTHER_OP_KEY))),
        NO_OP_KEY,
    ),
    "a round_budget of 0": (raw(doc(round_budget=0)), "round_budget: must be"),
    "a round_budget that is no integer": (
        raw(doc(**OP_MEMBERS, round_budget=8.0)),
        "round_budget: must be",
    ),
    "a wall_clock_budget_s of 0": (
        raw(doc(wall_clock_budget_s=0)),
        "wall_clock_budget_s: must be",
    ),
    "a wall_clock_budget_s that is a string": (
        raw(doc(**OP_MEMBERS, round_budget=1, wall_clock_budget_s="8h")),
        "wall_clock_budget_s: must be",
    ),
    "an owner that is the empty string": (raw(doc(owner="")), "owner: must be"),
    "an owner that is no string": (
        raw(doc(**OP_MEMBERS, project="example-project", owner=7)),
        "owner: must be",
    ),
    "a project that is null": (raw(doc(project=None)), "project: must be"),
    "a project with a line feed": (
        raw(doc(**OP_MEMBERS, owner="example-owner", project="example\nproject")),
        "project: must be",
    ),
}


@pytest.mark.parametrize("call", READERS)
@pytest.mark.parametrize("case", INVALID_FILES)
def test_an_invalid_file_is_named_by_its_relative_path(tmp_path, root, call, case):
    content, reason = INVALID_FILES[case]
    place(root, content)
    before = snapshot(tmp_path)

    message = invalid(f"{FILE}: {reason}", call, root, RUN)

    assert str(root) not in message
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", READERS)
@pytest.mark.parametrize("version", [0, 2, MAX])
def test_a_file_of_another_version(root, call, version):
    place(root, raw(doc(schema_version=version, hw_profile=REMOVE)))

    with pytest.raises(UnsupportedVersionError) as caught:
        call(root, RUN)

    assert str(caught.value) == f"{FILE}: schema_version: {version} is not supported"
    assert not isinstance(caught.value, (ToolFailure, ValueError, OSError))


@pytest.mark.parametrize("call", READERS)
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


@pytest.mark.parametrize("call", READERS)
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


@pytest.mark.parametrize("call", READERS)
def test_a_directory_in_the_place_of_the_file(tmp_path, root, call):
    (root / FILE).mkdir(parents=True)
    before = snapshot(tmp_path)

    assert invalid(FILE, call, root, RUN) == f"{FILE}: is not a regular file"
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("call", READERS)
@pytest.mark.parametrize("target", ["a file", "nothing"])
def test_a_symbolic_link_in_the_place_of_the_file(tmp_path, root, call, target):
    elsewhere = tmp_path / "elsewhere.json"
    if target == "a file":
        elsewhere.write_bytes(raw(doc()))
    link(root / FILE, elsewhere)

    assert invalid(FILE, call, root, RUN) == f"{FILE}: is not a regular file"
    assert elsewhere.exists() == (target == "a file")


# --- error / negative: arguments ---


@pytest.mark.parametrize("call", READERS)
@pytest.mark.parametrize(
    "run_id", ["", "Run-A", "../run-a", "a/b", ".", "a" * 65, None, 1, b"run-a"]
)
def test_an_invalid_run_id_is_refused_before_the_file_system(tmp_path, call, run_id):
    for data_root in (tmp_path, tmp_path / "absent"):
        with pytest.raises(layout.InvalidPathValueError, match="^run_id: must be"):
            call(data_root, run_id)
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("call", READERS)
def test_a_data_root_that_does_not_exist(tmp_path, call):
    with pytest.raises(FileNotFoundError, match="data root is not an existing"):
        call(tmp_path / "absent", RUN)
    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("call", READERS)
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


def test_an_ended_identity_is_not_answered_after_the_file_was_removed(root):
    path = place(started(root), raw(doc()))
    tool = Tool(root)
    assert tool.function(dict(REQUEST)) == {"example_member": 1}

    path.unlink()

    before = snapshot(root)
    for asked in (REQUEST, {**REQUEST, "execution": 2}):
        with pytest.raises(ToolFailure) as caught:
            tool.function(dict(asked))
        assert caught.value.kind == tools.KIND_RUN_FILE_MISSING == "run_file_missing"
        assert type(caught.value.__cause__) is MissingInstanceError
        assert caught.value.message.startswith(f"{FILE}: is missing")
        for way in THROUGH_CALL.values():
            assert way(tool, asked) == (True, caught.value.error_object())
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert snapshot(root) == before

    place(root, raw(doc()))
    for way in THROUGH_CALL.values():
        assert way(tool, REQUEST) == (False, {"example_member": 1})
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert (len(tool.asked), tool.performed) == (1, 1)


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
    file = place(root, raw(doc()))

    def reader(data_root, run_id):
        file.unlink()
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


@pytest.mark.parametrize(
    "repaired", [doc(), doc(source_commit=COMMIT)], ids=["removed", "valid"]
)
@pytest.mark.parametrize("broken", ["main", COMMIT[:7], COMMIT.upper(), False])
def test_a_file_invalid_by_its_source_commit_alone_is_run_file_invalid(
    root, broken, repaired
):
    place(started(root), raw(doc(tolerance=TOLERANCE, source_commit=broken)))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "source_commit: must be a str of 40 or of 64 characters",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]


@pytest.mark.parametrize(
    "repaired", [doc(), doc(n_max=BOUND)], ids=["removed", "valid"]
)
@pytest.mark.parametrize("broken", [4, 0, 10.0, "10", True, None, MAX + 1], ids=repr)
def test_a_file_invalid_by_its_n_max_alone_is_run_file_invalid(root, broken, repaired):
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT}
    place(started(root), raw(doc(**members, n_max=broken)))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "n_max: must be an int from 5 to",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]


@pytest.mark.parametrize(
    "repaired", [doc(), doc(candidates_per_round=COUNT)], ids=["removed", "valid"]
)
@pytest.mark.parametrize("broken", [0, -1, 2.0, "2", True, None, MAX + 1], ids=repr)
def test_a_file_invalid_by_its_candidates_per_round_alone_is_run_file_invalid(
    root, broken, repaired
):
    members = {"tolerance": TOLERANCE, "source_commit": COMMIT, "n_max": BOUND}
    place(started(root), raw(doc(**members, candidates_per_round=broken)))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "candidates_per_round: must be an int from 1 to",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]


@pytest.mark.parametrize(
    "repaired",
    [doc(), doc(op_signature=stating(op_record()))],
    ids=["removed", "valid"],
)
@pytest.mark.parametrize(
    "broken",
    [
        None,
        OP_KEY,
        [stating(op_record())],
        {"key": OP_KEY},
        op_section(key=OTHER_OP_KEY),
        op_section(record=op_record(kind="attention")),
        op_section(record=op_record(layout=REMOVE)),
    ],
    ids=shown,
)
def test_a_file_invalid_by_its_op_signature_alone_is_run_file_invalid(
    root, broken, repaired
):
    place(started(root), raw(doc(**OP_MEMBERS, op_signature=broken)))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "op_signature",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]


# --- happy: the member round_budget (ADR-0032) ---

# Test values of a round budget: neither is a default, recommended or typical value.
BUDGET, OTHER_BUDGET = 6, 13
NO_BUDGET = f"round_budget: must be an int from 1 to {MAX}, got "
BUDGET_MEMBER = f'"round_budget": {BUDGET}'
EVERY_MEMBER = {**OP_MEMBERS, "op_signature": stating(op_record())}
EVERY_MEMBER_TEXT = (*COUNTED_MEMBERS[2:], OP_SECTION)


def budgeted(literal, *more):
    return text(VERSION, SECTION, f'"round_budget": {literal}', *more)


def assert_the_other_members_are_stated(root, run=RUN):
    assert hw_profile_of(root, run) == record()
    assert tolerance_of(root, run) == Tolerance(TEST_RTOL, TEST_ATOL)
    assert source_commit_of(root, run) == COMMIT
    assert n_max_of(root, run) == BOUND
    assert candidates_per_round_of(root, run) == COUNT
    assert op_signature_of(root, run) == OpSignature(OP_KEY, op_record())
    assert layout_version_of(root, run) == 1


@pytest.mark.parametrize(
    "budget", [1, 2, 4, 5, 8, 10, 11, 20, 1000, 2**31, 2**32 + 1, MAX - 1, MAX]
)
def test_a_content_with_the_member_states_that_round_budget(budget):
    document = doc(round_budget=budget, example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY,
        record(),
        None,
        None,
        None,
        None,
        None,
        budget,
        None,
        None,
        None,
        {"example": [1]},
    )
    assert type(result.round_budget) is int
    assert "round_budget" not in result.others
    assert validate(document) is None
    assert parse(budgeted(str(budget))).round_budget == budget


def test_both_ends_of_the_round_budget_are_inclusive_and_nothing_ends_it_between():
    assert MAX == 2**53 - 1

    for budget in (1, 4, 11, 1000, MAX):
        assert parse(budgeted(str(budget))).round_budget == budget
        assert validate(doc(round_budget=budget)) is None
    for budget in (0, MAX + 1):
        assert invalid(NO_BUDGET, parse, budgeted(str(budget))) == NO_BUDGET + "int"
        document = doc(round_budget=budget)
        assert invalid(NO_BUDGET, validate, document) == NO_BUDGET + "int"
    invalid(NO_BUDGET, parse, budgeted("9007199254740992"))
    assert parse(budgeted("9007199254740991")).round_budget == MAX


def test_a_content_without_the_member_states_no_round_budget():
    without = parse(raw(doc(**EVERY_MEMBER)))
    stated = parse(raw(doc(**EVERY_MEMBER, round_budget=BUDGET)))

    assert without.round_budget is None
    assert parse(raw(doc())).round_budget is None
    assert stated.round_budget == BUDGET
    assert without[:7] == stated[:7]
    assert without[:7] == (
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        COUNT,
        OpSignature(OP_KEY, op_record()),
    )
    assert without.others == stated.others == {}
    assert validate(doc(**EVERY_MEMBER)) is None


@pytest.mark.parametrize("index", range(8))
def test_any_place_of_the_round_budget_among_the_other_members(index):
    expected = Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        COUNT,
        OpSignature(OP_KEY, op_record()),
        BUDGET,
        None,
        None,
        None,
        {},
    )

    for others in (
        [*COUNTED_MEMBERS, OP_SECTION],
        [OP_SECTION, *COUNTED_MEMBERS[::-1]],
    ):
        members = [*others[:index], BUDGET_MEMBER, *others[index:]]
        assert parse(text(*members)) == expected
        assert validate(json.loads(text(*members))) is None


def test_white_space_of_json_around_the_round_budget_is_not_part_of_the_value():
    content = text(VERSION, SECTION, f'\r\n\t"round_budget" :\n {BUDGET} \n')

    assert parse(content).round_budget == BUDGET


# The Example of ADR-0032, as written in the record: the shape of the member, not a valid file.
EXAMPLE_OF_ADR_0032 = b"""{
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
  },
  "op_signature": {
    "key": "gemm-485b9bc494d477eb",
    "record": {
      "schema_version": 1,
      "kind": "gemm",
      "shape": {"m": 1, "k": 2048, "n": 8192},
      "dtype": "fp32",
      "layout": "row_major"
    }
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10,
  "candidates_per_round": 2,
  "round_budget": 8
}
"""


def test_the_member_of_the_example_of_adr_0032():
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0032)

    result = parse(
        EXAMPLE_OF_ADR_0032.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
    )
    assert result.round_budget == 8
    assert type(result.round_budget) is int
    assert result.candidates_per_round == 2
    assert result.n_max == 10
    assert result.source_commit == COMMIT
    assert result.tolerance == Tolerance(0.0001, 0.01)
    assert result.op_signature == OpSignature(EXAMPLE_OP_KEY, example_op())
    assert result.others == {}

    silent = parse(EXAMPLE_FILE)
    assert silent.round_budget is None
    assert silent[:7] == result[:7]


# --- branch: the member round_budget ---


@pytest.mark.parametrize(
    "budget, count, bound",
    [
        (1, 100, 5),
        (1000, 1, 5),
        (1, MAX, MAX),
        (MAX, 1, 5),
        (MAX, MAX, MAX),
        (6, 6, 6),
    ],
)
def test_the_round_budget_the_candidates_and_n_max_do_not_bound_each_other(
    budget, count, bound
):
    document = doc(round_budget=budget, candidates_per_round=count, n_max=bound)

    result = parse(raw(document))

    assert (result.round_budget, result.candidates_per_round, result.n_max) == (
        budget,
        count,
        bound,
    )
    assert validate(document) is None


BROKEN_BUDGETS = [None, True, 0, -8, 8.0, "8", [8], {"value": 8}, MAX + 1]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("budget", [*BROKEN_BUDGETS, BUDGET], ids=repr)
def test_another_version_is_reported_before_the_round_budget_is_looked_at(
    version, budget
):
    document = doc(schema_version=version, round_budget=budget)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"rounds": BUDGET},
        {"budget": BUDGET},
        {"roundBudget": BUDGET},
        {"budget_rounds": BUDGET},
        {"round-budget": BUDGET},
        {"Round_budget": BUDGET},
        {"ROUND_BUDGET": BUDGET},
        {"max_rounds": BUDGET},
        {"round_limit": BUDGET},
        {"round_budget ": 0},
        {"round_budgets": BUDGET},
        {"budget": {"rounds": BUDGET, "round_budget": BUDGET}},
        {
            "rounds": True,
            "budget": 0,
            "roundBudget": "8",
            "round-budget": 8.0,
            "max_rounds": -1,
            "budget_rounds": None,
        },
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_round_budget(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
    assert result.round_budget is None
    assert validate(doc(**others)) is None

    result = parse(raw(doc(round_budget=OTHER_BUDGET, **others)))
    assert result.round_budget == OTHER_BUDGET
    assert result.others == others


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "round_budget": 0}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "round_budget": True},
        ),
        (
            "hw_profile.key: ",
            {"hw_profile": section(key=OTHER_KEY), "round_budget": "8"},
        ),
        ("tolerance: must be", {"tolerance": None, "round_budget": None}),
        (NO_COMMIT + "str 'main'", {"source_commit": "main", "round_budget": 0}),
        (NO_BOUND + "int", {"n_max": 4, "round_budget": 0}),
        (NO_COUNT + "int", {"candidates_per_round": 0, "round_budget": 0}),
        (
            "op_signature: must be an object, got NoneType",
            {"op_signature": None, "round_budget": 0},
        ),
        (
            "op_signature.key: must be gemm-",
            {**OP_MEMBERS, "op_signature": op_section(key=""), "round_budget": 8.0},
        ),
        (NO_BUDGET + "int", {**EVERY_MEMBER, "round_budget": 0}),
        (NO_BUDGET + "bool", {"round_budget": False}),
    ],
)
def test_the_first_broken_rule_is_reported_with_a_round_budget(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member round_budget ---

NO_BUDGET_LITERALS = {
    "true": "bool",
    "false": "bool",
    "null": "NoneType",
    '"8"': "str '8'",
    '"1"': "str '1'",
    '""': "str ''",
    '"unlimited"': "str 'unlimited'",
    '"eight"': "str 'eight'",
    "[8]": "list",
    "[]": "list",
    '{"value": 8}': "dict",
    "{}": "dict",
    "8.0": "float",
    "8e0": "float",
    "8E0": "float",
    "1.0": "float",
    "8.5": "float",
    "0.5": "float",
    "1e999": "float",
    "-0.0": "float",
    "-0": "int",
    "0": "int",
    "-1": "int",
    "-8": "int",
    "9007199254740992": "int",
    "9007199254740993": "int",
    "10000000000000000000000": "int",
}


@pytest.mark.parametrize("literal", NO_BUDGET_LITERALS)
def test_what_is_no_value_of_the_round_budget(literal):
    content = budgeted(literal, *EVERY_MEMBER_TEXT, '"example": [1]')

    assert invalid(NO_BUDGET, parse, content) == NO_BUDGET + NO_BUDGET_LITERALS[literal]
    invalid(NO_BUDGET, validate, json.loads(content))
    kept = parse(text(VERSION, SECTION, *EVERY_MEMBER_TEXT, '"example": [1]'))
    assert kept == Instance(
        KEY,
        record(),
        Tolerance(TEST_RTOL, TEST_ATOL),
        COMMIT,
        BOUND,
        COUNT,
        OpSignature(OP_KEY, op_record()),
        None,
        None,
        None,
        None,
        {"example": [1]},
    )


WALK_THROUGH_OF_ADR_0032 = [
    '"8"',
    "8.0",
    "8e0",
    "-8",
    "0",
    "null",
    "true",
    "[8]",
    "9007199254740992",
]


@pytest.mark.parametrize("literal", WALK_THROUGH_OF_ADR_0032)
def test_the_invalid_files_of_the_walk_through_of_adr_0032(literal):
    invalid("round_budget: must be", parse, budgeted(literal, *EVERY_MEMBER_TEXT))
    kept = parse(text(VERSION, SECTION, *EVERY_MEMBER_TEXT))
    assert kept[2:6] == (Tolerance(TEST_RTOL, TEST_ATOL), COMMIT, BOUND, COUNT)
    assert kept.round_budget is None
    for name in ("rounds", "budget", "budget_rounds"):
        silent = parse(text(VERSION, SECTION, f'"{name}": 8'))
        assert silent.round_budget is None
        assert silent.others == {name: 8}
    for budget in (8, 20, 1):
        found = parse(budgeted(str(budget), *EVERY_MEMBER_TEXT))
        assert found.round_budget == budget


def test_minus_zero_is_refused_as_the_integer_0_below_the_lower_end_of_the_budget():
    assert invalid(NO_BUDGET, parse, budgeted("-0")) == NO_BUDGET + "int"
    assert invalid(NO_BUDGET, parse, budgeted("0")) == NO_BUDGET + "int"


LOOSER_BUDGET_RULES = {
    "isinstance(value, int)": (
        lambda value: isinstance(value, int) and 1 <= value <= MAX,
        [True, Number(8), Number(1), Number(MAX)],
    ),
    "isinstance(value, int) without the range": (
        lambda value: isinstance(value, int),
        [True, False, Number(3), 0, -8, MAX + 1],
    ),
    "an equal value": (
        lambda value: value == 8 or value == 1,
        [8.0, 1.0, True, Number(8)],
    ),
    "float.is_integer": (
        lambda value: float(value).is_integer() and value >= 1,
        [8.0, 1.0, 3.0, 8e0, float(2**40)],
    ),
    "int(value)": (
        lambda value: 1 <= int(value) <= MAX,
        ["8", " 3 ", "1_0", "+8", 8.0, 8.9, 1.5, True, Number(8)],
    ),
    "a sign of no limit": (
        lambda value: value in (None, 0, math.inf, "unlimited", ""),
        [None, 0, 0.0, False, float("inf"), "unlimited", ""],
    ),
}


@pytest.mark.parametrize("rule", LOOSER_BUDGET_RULES)
def test_a_round_budget_a_looser_rule_would_accept_is_refused(rule):
    looser, values = LOOSER_BUDGET_RULES[rule]

    for value in values:
        assert looser(value)
        expected = NO_BUDGET + type(value).__name__
        invalid(expected, validate, doc(round_budget=value))
        if type(value) is not Number and value != math.inf:
            invalid(expected, parse, raw(doc(round_budget=value)))


@pytest.mark.parametrize(
    "members",
    [
        (BUDGET_MEMBER, BUDGET_MEMBER),
        (BUDGET_MEMBER, f'"round_budget": {OTHER_BUDGET}'),
        (BUDGET_MEMBER, '"round_budget": 0'),
        ('"round_budget": true', BUDGET_MEMBER),
    ],
)
def test_the_member_name_round_budget_twice_at_the_top_level(members):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, *members),
    )
    assert "a JSON object repeats a member name" in message


def test_a_round_budget_too_long_for_the_interpreter_is_a_text_error():
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        budgeted(TOO_LONG_TEXT),
    )
    assert "round_budget" not in message


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        8.0,
        1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
        Number(8),
        Number(1),
        Number(0),
        TOO_LONG,
        -TOO_LONG,
        "8",
        "unlimited",
        None,
        b"8",
        (8,),
        {8},
        range(8),
    ],
    ids=shown,
)
def test_validate_refuses_a_round_budget_built_in_memory(value):
    document = doc(round_budget=value)

    message = invalid(NO_BUDGET + type(value).__name__, validate, document)

    if type(value) is not str:
        assert message == NO_BUDGET + type(value).__name__


def test_a_refused_round_budget_is_not_shown_and_a_string_is():
    for budget in (0, -1, -7, MAX + 1):
        message = invalid(NO_BUDGET, validate, doc(round_budget=budget))
        assert message == NO_BUDGET + "int"
        assert not message.endswith(str(budget))

    message = invalid(NO_BUDGET, validate, doc(round_budget="8" * 200))
    assert message == NO_BUDGET + "str " + reprlib.repr("8" * 200)
    assert len(message) < 120


def test_a_check_of_a_round_budget_modifies_nothing():
    for document in (
        doc(round_budget=BUDGET),
        doc(round_budget=0),
        doc(round_budget=8.0),
    ):
        kept = json.dumps(document)
        valid = document["round_budget"] == BUDGET
        assert accepted(validate, document) == valid
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module stands in for the round budget ---


@pytest.mark.parametrize(
    "document",
    [
        doc(),
        doc(**EVERY_MEMBER),
        doc(rounds=8),
        doc(budget={"rounds": 8}, max_rounds=10, round=12),
    ],
    ids=repr,
)
def test_a_content_without_the_member_states_no_round_budget_and_no_number(document):
    result = parse(raw(document))

    assert result.round_budget is None
    assert result._asdict()["round_budget"] is None
    assert validate(document) is None


def test_nothing_of_the_module_stands_in_for_the_round_budget():
    functions = [
        value
        for value in vars(instance).values()
        if inspect.isfunction(value) and value.__module__ == instance.__name__
    ]
    assert round_budget_of in functions
    for function in functions:
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert Instance._field_defaults == {}
    imported = set()
    for node in ast.walk(ast.parse(inspect.getsource(instance))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    assert "hilclaw.keys" in imported
    assert not [name for name in imported if "state" in name or "journal" in name]
    assert not {"run_state", "journal", "run_journal", "round_budget", "budget"} & set(
        vars(instance)
    )


# --- the reader of the round budget (ADR-0032) ---

STATE_FILE = f"runs/{RUN}/STATE.json"


def test_the_reader_returns_the_round_budget_the_file_states(tmp_path, root):
    place(root, raw(doc(**EVERY_MEMBER, round_budget=BUDGET, example=[1])))
    before = snapshot(tmp_path)

    found = round_budget_of(root, RUN)

    assert found == BUDGET and type(found) is int
    assert found == read(root, RUN).round_budget
    assert round_budget_of(str(root), RUN) == found
    assert_the_other_members_are_stated(root)
    assert snapshot(tmp_path) == before

    for budget in (1, 4, 5, 8, 10, 11, 20, 1000, MAX):
        place(root, raw(doc(round_budget=budget)))
        assert round_budget_of(root, RUN) == budget
        assert type(round_budget_of(root, RUN)) is int


def test_a_run_without_the_member_states_no_round_budget(tmp_path, root, monkeypatch):
    others = {
        "rounds": BUDGET,
        "budget": {"rounds": BUDGET},
        "roundBudget": BUDGET,
        "budget_rounds": BUDGET,
        "round-budget": BUDGET,
        "max_rounds": BUDGET,
    }
    place(root, raw(doc(**EVERY_MEMBER, **others)))
    place(root, raw(doc(round_budget=OTHER_BUDGET)), OTHER_FILE)
    place(root, run_state.dump(12, EMPTY), STATE_FILE)
    for number in range(3):
        place(root, b"{}", f"runs/{RUN}/rounds/{number:04}/candidates/01/spec.json")
    for name in ("ROUND_BUDGET", "HILCLAW_ROUND_BUDGET", "BUDGET"):
        monkeypatch.setenv(name, str(BUDGET))
    before = snapshot(tmp_path)

    assert round_budget_of(root, RUN) is None
    assert read(root, RUN).round_budget is None
    assert read(root, RUN).others == others
    assert_the_other_members_are_stated(root)
    assert round_budget_of(root, OTHER_RUN) == OTHER_BUDGET
    assert round_budget_of(root, RUN) is None
    assert snapshot(tmp_path) == before

    place(root, raw(doc()))
    assert round_budget_of(root, RUN) is None


def test_a_round_budget_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(round_budget=BUDGET)))
    assert round_budget_of(root, RUN) == BUDGET

    place(root, raw(doc(round_budget=OTHER_BUDGET)))
    assert round_budget_of(root, RUN) == OTHER_BUDGET

    place(root, raw(doc()))
    assert round_budget_of(root, RUN) is None

    place(root, raw(doc(round_budget=0)))
    invalid(f"{FILE}: {NO_BUDGET}int", round_budget_of, root, RUN)

    place(root, raw(doc(schema_version=2, round_budget=BUDGET)))
    with pytest.raises(UnsupportedVersionError):
        round_budget_of(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        round_budget_of(root, RUN)

    place(root, raw(doc(round_budget=1)))
    assert round_budget_of(root, RUN) == 1


@pytest.mark.parametrize(
    "literal",
    [*WALK_THROUGH_OF_ADR_0032, "-0", "false", "{}", "8.5", '"unlimited"', '""'],
)
def test_no_member_of_a_file_with_an_invalid_round_budget_is_used(root, literal):
    place(root, budgeted(str(BUDGET), *EVERY_MEMBER_TEXT))
    assert round_budget_of(root, RUN) == BUDGET
    assert_the_other_members_are_stated(root)

    place(root, budgeted(literal, *EVERY_MEMBER_TEXT))
    assert round_budget_of in READERS and len(READERS) == 12
    for call in READERS:
        invalid(f"{FILE}: {NO_BUDGET}", call, root, RUN)

    place(root, text(VERSION, SECTION, *EVERY_MEMBER_TEXT))
    assert round_budget_of(root, RUN) is None
    assert_the_other_members_are_stated(root)


def test_two_runs_state_their_own_round_budgets(root):
    place(root, raw(doc(round_budget=1)))
    place(root, raw(doc(round_budget=20)), OTHER_FILE)
    place(root, raw(doc()), "runs/run-c/instance.json")

    assert round_budget_of(root, RUN) == 1
    assert round_budget_of(root, OTHER_RUN) == 20
    assert round_budget_of(root, "run-c") is None
    assert round_budget_of(root, RUN) == 1


@pytest.mark.parametrize(
    "state",
    [b'{"round": 12}', run_state.dump(12, EMPTY), run_state.dump(0, EMPTY), b"\xff"],
    ids=["a text with a round", "round 12", "round 0", "no text"],
)
def test_the_reader_of_the_round_budget_opens_only_the_instance_file(
    root, monkeypatch, state
):
    place(root, raw(doc(round_budget=8)))
    place(root, state, STATE_FILE)
    place(root, b"", f"runs/{RUN}/events.ndjson")
    for number in range(13):
        place(root, b"{}", f"runs/{RUN}/rounds/{number:04}/candidates/01/spec.json")
    place(root, raw(doc(round_budget=OTHER_BUDGET)), OTHER_FILE)
    before = snapshot(root)
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert round_budget_of(root, RUN) == 8
    assert opened == [FILE]
    assert round_budget_of(root, RUN) == 8
    assert opened == [FILE, FILE]
    monkeypatch.setattr(Path, "read_bytes", real)
    assert snapshot(root) == before


# --- with hilclaw.hw_tool: a file invalid by its round_budget alone ---


@pytest.mark.parametrize(
    "repaired",
    [doc(), doc(round_budget=BUDGET), doc(round_budget=1)],
    ids=["removed", "valid", "valid and below the round of the request"],
)
@pytest.mark.parametrize("broken", [0, -8, 8.0, "8", True, None, MAX + 1], ids=repr)
def test_a_file_invalid_by_its_round_budget_alone_is_run_file_invalid(
    root, broken, repaired
):
    place(started(root), raw(doc(**EVERY_MEMBER, round_budget=broken)))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "round_budget: must be an int from 1 to",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]


# --- happy: the member wall_clock_budget_s (ADR-0033) ---

# Test values of a wall-clock budget, in seconds: neither is a default, recommended or typical value.
SECONDS, OTHER_SECONDS = 754, 13007
NO_SECONDS = f"wall_clock_budget_s: must be an int from 1 to {MAX}, got "
SECONDS_MEMBER = f'"wall_clock_budget_s": {SECONDS}'
ALL_BUT_SECONDS = {**EVERY_MEMBER, "round_budget": BUDGET}
ALL_BUT_SECONDS_TEXT = (*EVERY_MEMBER_TEXT, BUDGET_MEMBER)
STATED_BESIDE_THE_SECONDS = (
    KEY,
    record(),
    Tolerance(TEST_RTOL, TEST_ATOL),
    COMMIT,
    BOUND,
    COUNT,
    OpSignature(OP_KEY, op_record()),
    BUDGET,
)
EVENTS_FILE = f"runs/{RUN}/events.ndjson"


def timed(literal, *more):
    return text(VERSION, SECTION, f'"wall_clock_budget_s": {literal}', *more)


def assert_the_members_beside_the_seconds_are_stated(root, run=RUN):
    assert_the_other_members_are_stated(root, run)
    assert round_budget_of(root, run) == BUDGET


@pytest.mark.parametrize(
    "seconds",
    [1, 59, 60, 3600, 5400, 28800, 86400, 2**31, 2**32 + 1, MAX - 1, MAX],
)
def test_a_content_with_the_member_states_that_wall_clock_budget(seconds):
    document = doc(wall_clock_budget_s=seconds, example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY,
        record(),
        None,
        None,
        None,
        None,
        None,
        None,
        seconds,
        None,
        None,
        {"example": [1]},
    )
    assert type(result.wall_clock_budget_s) is int
    assert "wall_clock_budget_s" not in result.others
    assert validate(document) is None
    assert parse(timed(str(seconds))).wall_clock_budget_s == seconds


def test_both_ends_of_the_wall_clock_budget_are_inclusive_and_nothing_ends_it_between():
    assert MAX == 2**53 - 1

    for seconds in (1, 2, 59, 86400, 86401, 10**12, MAX):
        assert parse(timed(str(seconds))).wall_clock_budget_s == seconds
        assert validate(doc(wall_clock_budget_s=seconds)) is None
    for seconds in (0, MAX + 1):
        assert invalid(NO_SECONDS, parse, timed(str(seconds))) == NO_SECONDS + "int"
        document = doc(wall_clock_budget_s=seconds)
        assert invalid(NO_SECONDS, validate, document) == NO_SECONDS + "int"
    invalid(NO_SECONDS, parse, timed("9007199254740992"))
    assert parse(timed("9007199254740991")).wall_clock_budget_s == MAX


@pytest.mark.parametrize(
    "members", [{}, EVERY_MEMBER, ALL_BUT_SECONDS, {"round_budget": 1}], ids=repr
)
def test_a_content_without_the_member_states_no_wall_clock_budget(members):
    without = parse(raw(doc(**members)))
    stated = parse(raw(doc(**members, wall_clock_budget_s=SECONDS)))

    assert without.wall_clock_budget_s is None
    assert stated.wall_clock_budget_s == SECONDS
    assert without[:8] == stated[:8]
    assert without.round_budget == members.get("round_budget")
    assert without.others == stated.others == {}
    assert validate(doc(**members)) is None


@pytest.mark.parametrize("index", range(9))
def test_any_place_of_the_wall_clock_budget_among_the_other_members(index):
    expected = Instance(*STATED_BESIDE_THE_SECONDS, SECONDS, None, None, {})

    for others in (
        [*COUNTED_MEMBERS, OP_SECTION, BUDGET_MEMBER],
        [BUDGET_MEMBER, OP_SECTION, *COUNTED_MEMBERS[::-1]],
    ):
        members = [*others[:index], SECONDS_MEMBER, *others[index:]]
        assert parse(text(*members)) == expected
        assert validate(json.loads(text(*members))) is None


def test_white_space_of_json_around_the_wall_clock_budget_is_not_part_of_the_value():
    content = text(VERSION, SECTION, f'\r\n\t"wall_clock_budget_s" :\n {SECONDS} \n')

    assert parse(content).wall_clock_budget_s == SECONDS


# The Example of ADR-0033, as written in the record: the shape of the member, not a valid file.
EXAMPLE_OF_ADR_0033 = b"""{
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
  },
  "op_signature": {
    "key": "gemm-485b9bc494d477eb",
    "record": {
      "schema_version": 1,
      "kind": "gemm",
      "shape": {"m": 1, "k": 2048, "n": 8192},
      "dtype": "fp32",
      "layout": "row_major"
    }
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10,
  "candidates_per_round": 2,
  "round_budget": 8,
  "wall_clock_budget_s": 5400
}
"""


def test_the_member_of_the_example_of_adr_0033():
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0033)

    result = parse(
        EXAMPLE_OF_ADR_0033.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
    )
    assert result.wall_clock_budget_s == 5400
    assert type(result.wall_clock_budget_s) is int
    assert result.round_budget == 8
    assert result.candidates_per_round == 2
    assert result.n_max == 10
    assert result.source_commit == COMMIT
    assert result.tolerance == Tolerance(0.0001, 0.01)
    assert result.op_signature == OpSignature(EXAMPLE_OP_KEY, example_op())
    assert result.others == {}

    silent = parse(
        EXAMPLE_OF_ADR_0032.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
    )
    assert silent.wall_clock_budget_s is None
    assert silent[:8] == result[:8]


# --- branch: the member wall_clock_budget_s ---


@pytest.mark.parametrize(
    "budget, seconds",
    [
        (1000, 1),
        (1, MAX),
        (MAX, 1),
        (MAX, MAX),
        (1, 1),
        (8, 5400),
        (None, SECONDS),
        (BUDGET, None),
        (None, None),
    ],
)
def test_the_two_budget_members_do_not_bound_each_other(root, budget, seconds):
    stated = {"round_budget": budget, "wall_clock_budget_s": seconds}
    document = doc(
        **{name: value for name, value in stated.items() if value is not None},
        candidates_per_round=MAX,
        n_max=5,
    )

    result = parse(raw(document))

    assert (result.round_budget, result.wall_clock_budget_s) == (budget, seconds)
    assert validate(document) is None
    place(root, raw(document))
    assert round_budget_of(root, RUN) == budget
    assert wall_clock_budget_s_of(root, RUN) == seconds


BROKEN_SECONDS = [None, True, 0, -5400, 5400.0, "5400", "8h", [5400], {}, MAX + 1]


@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("seconds", [*BROKEN_SECONDS, SECONDS], ids=repr)
def test_another_version_is_reported_before_the_wall_clock_budget_is_looked_at(
    version, seconds
):
    document = doc(schema_version=version, wall_clock_budget_s=seconds)

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"wall_clock_budget": SECONDS},
        {"wall_clock_s": SECONDS},
        {"wallclock_budget_s": SECONDS},
        {"time_budget": SECONDS},
        {"wall_clock_budget_seconds": SECONDS},
        {"Wall_clock_budget_s": SECONDS},
        {"WALL_CLOCK_BUDGET_S": SECONDS},
        {"wall-clock-budget-s": SECONDS},
        {"wall_clock_budget_s ": 0},
        {"deadline": SECONDS},
        {"timeout_s": SECONDS},
        {"duration_s": SECONDS},
        {"max_wall_clock_s": SECONDS},
        {"budget": SECONDS},
        {"budget": {"wall_clock_budget_s": SECONDS, "wall_clock_s": SECONDS}},
        {
            "wall_clock_budget": "8h",
            "wall_clock_s": 0,
            "time_budget": "PT90M",
            "deadline": None,
            "timeout_s": -1,
            "budget": True,
        },
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_wall_clock_budget(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(
        KEY, record(), None, None, None, None, None, None, None, None, None, others
    )
    assert result.wall_clock_budget_s is None
    assert validate(doc(**others)) is None

    result = parse(raw(doc(wall_clock_budget_s=OTHER_SECONDS, **others)))
    assert result.wall_clock_budget_s == OTHER_SECONDS
    assert result.others == others


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "wall_clock_budget_s": 0}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "wall_clock_budget_s": True},
        ),
        (
            "hw_profile.key: ",
            {"hw_profile": section(key=OTHER_KEY), "wall_clock_budget_s": "8h"},
        ),
        ("tolerance: must be", {"tolerance": None, "wall_clock_budget_s": None}),
        (
            NO_COMMIT + "str 'main'",
            {"source_commit": "main", "wall_clock_budget_s": 0},
        ),
        (NO_BOUND + "int", {"n_max": 4, "wall_clock_budget_s": 0}),
        (NO_COUNT + "int", {"candidates_per_round": 0, "wall_clock_budget_s": 0}),
        (
            "op_signature: must be an object, got NoneType",
            {"op_signature": None, "wall_clock_budget_s": 0},
        ),
        (NO_BUDGET + "int", {"round_budget": 0, "wall_clock_budget_s": 0}),
        (
            NO_BUDGET + "float",
            {**EVERY_MEMBER, "round_budget": 8.0, "wall_clock_budget_s": "5400"},
        ),
        (NO_SECONDS + "int", {**ALL_BUT_SECONDS, "wall_clock_budget_s": 0}),
        (NO_SECONDS + "bool", {"wall_clock_budget_s": False}),
    ],
)
def test_the_first_broken_rule_is_reported_with_a_wall_clock_budget(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the member wall_clock_budget_s ---

NO_SECONDS_LITERALS = {
    "true": "bool",
    "false": "bool",
    "null": "NoneType",
    '"5400"': "str '5400'",
    '"1"': "str '1'",
    '""': "str ''",
    '"8h"': "str '8h'",
    '"PT90M"': "str 'PT90M'",
    '"PT8H"': "str 'PT8H'",
    '"unlimited"': "str 'unlimited'",
    "[5400]": "list",
    "[]": "list",
    '{"value": 8, "unit": "h"}': "dict",
    "{}": "dict",
    "5400.0": "float",
    "5.4e3": "float",
    "5.4E3": "float",
    "54e2": "float",
    "1.0": "float",
    "1.5": "float",
    "0.5": "float",
    "1e999": "float",
    "-0.0": "float",
    "-0": "int",
    "0": "int",
    "-1": "int",
    "-5400": "int",
    "9007199254740992": "int",
    "9007199254740993": "int",
    "10000000000000000000000": "int",
}


@pytest.mark.parametrize("literal", NO_SECONDS_LITERALS)
def test_what_is_no_value_of_the_wall_clock_budget(literal):
    content = timed(literal, *ALL_BUT_SECONDS_TEXT, '"example": [1]')

    expected = NO_SECONDS + NO_SECONDS_LITERALS[literal]
    assert invalid(NO_SECONDS, parse, content) == expected
    invalid(NO_SECONDS, validate, json.loads(content))
    kept = parse(text(VERSION, SECTION, *ALL_BUT_SECONDS_TEXT, '"example": [1]'))
    assert kept == Instance(
        *STATED_BESIDE_THE_SECONDS, None, None, None, {"example": [1]}
    )


WALK_THROUGH_OF_ADR_0033 = [
    '"5400"',
    '"PT90M"',
    "5400.0",
    "5.4e3",
    "1.5",
    "-5400",
    "0",
    "null",
    "true",
    "[5400]",
    "9007199254740992",
]


@pytest.mark.parametrize("literal", WALK_THROUGH_OF_ADR_0033)
def test_the_invalid_files_of_the_walk_through_of_adr_0033(literal):
    invalid(
        "wall_clock_budget_s: must be", parse, timed(literal, *ALL_BUT_SECONDS_TEXT)
    )


def test_the_valid_files_of_the_walk_through_of_adr_0033():
    kept = parse(text(VERSION, SECTION, *ALL_BUT_SECONDS_TEXT))
    assert kept[:8] == STATED_BESIDE_THE_SECONDS
    assert kept.wall_clock_budget_s is None
    for name in ("wall_clock_budget", "wall_clock_s", "time_budget"):
        silent = parse(text(VERSION, SECTION, f'"{name}": 5400'))
        assert silent.wall_clock_budget_s is None
        assert silent.others == {name: 5400}
    found = parse(timed("5400", *ALL_BUT_SECONDS_TEXT))
    assert (found.round_budget, found.wall_clock_budget_s) == (BUDGET, 5400)


def test_minus_zero_is_refused_as_the_integer_0_below_the_lower_end_of_the_seconds():
    assert invalid(NO_SECONDS, parse, timed("-0")) == NO_SECONDS + "int"
    assert invalid(NO_SECONDS, parse, timed("0")) == NO_SECONDS + "int"


JSON_TYPES = (bool, int, float, str, type(None))
LOOSER_SECONDS_RULES = {
    "isinstance(value, int)": (
        lambda value: isinstance(value, int) and 1 <= value <= MAX,
        [True, Number(5400), Number(1), Number(MAX)],
    ),
    "a float equal to an integer": (
        lambda value: float(value).is_integer() and value >= 1,
        [5400.0, 1.0, 5.4e3, float(2**40)],
    ),
    "a string of digits": (
        lambda value: 1 <= int(value) <= MAX,
        ["5400", " 60 ", "5_400", "+5400", 5400.9, 1.5, True, Number(5400)],
    ),
    "a duration string": (
        lambda value: re.fullmatch(r"PT\d+[HMS]|\d+[hms]", value) is not None,
        ["PT90M", "PT8H", "PT5400S", "8h", "90m", "5400s"],
    ),
    "an amount of time of the standard library": (
        lambda value: value.total_seconds() >= 1,
        [datetime.timedelta(seconds=5400), datetime.timedelta(hours=8)],
    ),
    "a sign of no limit": (
        lambda value: value in (None, 0, math.inf, "unlimited", ""),
        [None, 0, 0.0, False, float("inf"), "unlimited", ""],
    ),
}


@pytest.mark.parametrize("rule", LOOSER_SECONDS_RULES)
def test_a_wall_clock_budget_a_looser_rule_would_accept_is_refused(rule):
    looser, values = LOOSER_SECONDS_RULES[rule]

    for value in values:
        assert looser(value)
        expected = NO_SECONDS + type(value).__name__
        invalid(expected, validate, doc(wall_clock_budget_s=value))
        if type(value) in JSON_TYPES and value != math.inf:
            invalid(expected, parse, raw(doc(wall_clock_budget_s=value)))


@pytest.mark.parametrize(
    "members",
    [
        (SECONDS_MEMBER, SECONDS_MEMBER),
        (SECONDS_MEMBER, f'"wall_clock_budget_s": {OTHER_SECONDS}'),
        (SECONDS_MEMBER, '"wall_clock_budget_s": 0'),
        ('"wall_clock_budget_s": true', SECONDS_MEMBER),
    ],
)
def test_the_member_name_wall_clock_budget_s_twice_at_the_top_level(members):
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        text(VERSION, SECTION, *members),
    )
    assert "a JSON object repeats a member name" in message


def test_a_wall_clock_budget_too_long_for_the_interpreter_is_a_text_error():
    message = invalid(
        "content: cannot be read as one JSON text",
        parse,
        timed(TOO_LONG_TEXT),
    )
    assert "wall_clock_budget_s" not in message


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        5400.0,
        1.0,
        float("inf"),
        float("-inf"),
        float("nan"),
        Number(5400),
        Number(1),
        Number(0),
        TOO_LONG,
        -TOO_LONG,
        "5400",
        "8h",
        "unlimited",
        None,
        b"5400",
        (5400,),
        {5400},
        range(5400),
        datetime.timedelta(seconds=5400),
    ],
    ids=shown,
)
def test_validate_refuses_a_wall_clock_budget_built_in_memory(value):
    document = doc(wall_clock_budget_s=value)

    message = invalid(NO_SECONDS + type(value).__name__, validate, document)

    if type(value) is not str:
        assert message == NO_SECONDS + type(value).__name__


def test_a_refused_wall_clock_budget_is_not_shown_and_a_string_is():
    for seconds in (0, -1, -7, MAX + 1):
        message = invalid(NO_SECONDS, validate, doc(wall_clock_budget_s=seconds))
        assert message == NO_SECONDS + "int"
        assert not message.endswith(str(seconds))

    message = invalid(NO_SECONDS, validate, doc(wall_clock_budget_s="8" * 200))
    assert message == NO_SECONDS + "str " + reprlib.repr("8" * 200)
    assert len(message) < 130


def test_a_check_of_a_wall_clock_budget_modifies_nothing():
    for document in (
        doc(wall_clock_budget_s=SECONDS),
        doc(wall_clock_budget_s=0),
        doc(wall_clock_budget_s=5400.0),
        doc(**ALL_BUT_SECONDS, wall_clock_budget_s="8h"),
    ):
        kept = json.dumps(document)
        valid = document["wall_clock_budget_s"] == SECONDS
        assert accepted(validate, document) == valid
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module stands in for the wall-clock budget ---


@pytest.mark.parametrize(
    "document",
    [
        doc(),
        doc(**EVERY_MEMBER),
        doc(**ALL_BUT_SECONDS),
        doc(round_budget=MAX),
        doc(wall_clock_budget=5400),
        doc(budget={"wall_clock_budget_s": 5400}, time_budget="8h", timeout_s=60),
    ],
    ids=repr,
)
def test_a_content_without_the_member_states_no_wall_clock_budget_and_no_number(
    document,
):
    result = parse(raw(document))

    assert result.wall_clock_budget_s is None
    assert result._asdict()["wall_clock_budget_s"] is None
    assert validate(document) is None


def test_nothing_of_the_module_stands_in_for_the_wall_clock_budget():
    functions = [
        value
        for value in vars(instance).values()
        if inspect.isfunction(value) and value.__module__ == instance.__name__
    ]
    assert wall_clock_budget_s_of in functions
    for function in functions:
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert Instance._field_defaults == {}
    imported = set()
    for node in ast.walk(ast.parse(inspect.getsource(instance))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    parts = {part for name in imported for part in name.split(".")}
    assert "keys" in parts
    assert not parts & {
        "time",
        "datetime",
        "calendar",
        "run_state",
        "journal",
        "run_journal",
        "events",
        "run_id",
    }
    assert not {"time", "datetime", "events", "run_id", "wall_clock_budget_s"} & set(
        vars(instance)
    )


# --- the reader of the wall-clock budget (ADR-0033) ---


def test_the_reader_returns_the_wall_clock_budget_the_file_states(tmp_path, root):
    place(root, raw(doc(**ALL_BUT_SECONDS, wall_clock_budget_s=SECONDS, example=[1])))
    before = snapshot(tmp_path)

    found = wall_clock_budget_s_of(root, RUN)

    assert found == SECONDS and type(found) is int
    assert found == read(root, RUN).wall_clock_budget_s
    assert wall_clock_budget_s_of(str(root), RUN) == found
    assert_the_members_beside_the_seconds_are_stated(root)
    assert snapshot(tmp_path) == before

    for seconds in (1, 59, 60, 3600, 5400, 28800, 86400, MAX):
        place(root, raw(doc(wall_clock_budget_s=seconds)))
        assert wall_clock_budget_s_of(root, RUN) == seconds
        assert type(wall_clock_budget_s_of(root, RUN)) is int


def test_a_run_without_the_member_states_no_wall_clock_budget(
    tmp_path, root, monkeypatch
):
    others = {
        "wall_clock_budget": SECONDS,
        "wall_clock_s": SECONDS,
        "wallclock_budget_s": SECONDS,
        "time_budget": SECONDS,
        "budget": {"wall_clock_budget_s": SECONDS},
        "deadline": "2026-01-01T00:00:00Z",
        "timeout_s": SECONDS,
    }
    place(root, raw(doc(**ALL_BUT_SECONDS, **others)))
    place(root, raw(doc(wall_clock_budget_s=OTHER_SECONDS)), OTHER_FILE)
    place(root, run_state.dump(12, EMPTY), STATE_FILE)
    place(root, b'{"time": "2026-01-01T00:00:00Z"}\n', EVENTS_FILE)
    for name in ("WALL_CLOCK_BUDGET_S", "HILCLAW_WALL_CLOCK_BUDGET_S", "TIMEOUT"):
        monkeypatch.setenv(name, str(SECONDS))
    before = snapshot(tmp_path)

    found = wall_clock_budget_s_of(root, RUN)

    assert found is None
    for stand_in in (28800, 5400, 3600, 1, 0, math.inf, BUDGET, SECONDS):
        assert found != stand_in
    assert read(root, RUN).wall_clock_budget_s is None
    assert read(root, RUN).others == others
    assert_the_members_beside_the_seconds_are_stated(root)
    assert wall_clock_budget_s_of(root, OTHER_RUN) == OTHER_SECONDS
    assert wall_clock_budget_s_of(root, RUN) is None
    assert snapshot(tmp_path) == before

    place(root, raw(doc()))
    assert wall_clock_budget_s_of(root, RUN) is None


def test_a_wall_clock_budget_replaced_between_two_calls_is_seen_at_the_second(root):
    place(root, raw(doc(wall_clock_budget_s=SECONDS)))
    assert wall_clock_budget_s_of(root, RUN) == SECONDS

    place(root, raw(doc(wall_clock_budget_s=OTHER_SECONDS)))
    assert wall_clock_budget_s_of(root, RUN) == OTHER_SECONDS

    place(root, raw(doc()))
    assert wall_clock_budget_s_of(root, RUN) is None

    place(root, raw(doc(wall_clock_budget_s=0)))
    invalid(f"{FILE}: {NO_SECONDS}int", wall_clock_budget_s_of, root, RUN)

    place(root, raw(doc(schema_version=2, wall_clock_budget_s=SECONDS)))
    with pytest.raises(UnsupportedVersionError):
        wall_clock_budget_s_of(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        wall_clock_budget_s_of(root, RUN)

    place(root, raw(doc(wall_clock_budget_s=1)))
    assert wall_clock_budget_s_of(root, RUN) == 1


@pytest.mark.parametrize(
    "literal",
    [
        *WALK_THROUGH_OF_ADR_0033,
        "-0",
        "false",
        "{}",
        "0.5",
        '"8h"',
        '"unlimited"',
        '""',
    ],
)
def test_no_member_of_a_file_with_an_invalid_wall_clock_budget_is_used(root, literal):
    place(root, timed(str(SECONDS), *ALL_BUT_SECONDS_TEXT))
    assert wall_clock_budget_s_of(root, RUN) == SECONDS
    assert_the_members_beside_the_seconds_are_stated(root)

    place(root, timed(literal, *ALL_BUT_SECONDS_TEXT))
    assert wall_clock_budget_s_of in READERS and len(READERS) == 12
    for call in READERS:
        invalid(f"{FILE}: {NO_SECONDS}", call, root, RUN)

    place(root, text(VERSION, SECTION, *ALL_BUT_SECONDS_TEXT))
    assert wall_clock_budget_s_of(root, RUN) is None
    assert_the_members_beside_the_seconds_are_stated(root)


def test_two_runs_state_their_own_wall_clock_budgets(root):
    place(root, raw(doc(wall_clock_budget_s=1)))
    place(root, raw(doc(wall_clock_budget_s=86400)), OTHER_FILE)
    place(root, raw(doc(round_budget=BUDGET)), "runs/run-c/instance.json")

    assert wall_clock_budget_s_of(root, RUN) == 1
    assert wall_clock_budget_s_of(root, OTHER_RUN) == 86400
    assert wall_clock_budget_s_of(root, "run-c") is None
    assert wall_clock_budget_s_of(root, RUN) == 1


# Two lines whose time values lie a day apart: bytes beside the file, which no reader of the module opens.
LOG_OF_A_DAY = (
    b'{"seq": 1, "time": "2026-01-01T00:00:00Z"}\n'
    b'{"seq": 2, "time": "2026-01-02T00:00:00Z"}\n'
)


@pytest.mark.parametrize(
    "state, log",
    [
        (run_state.dump(12, EMPTY), LOG_OF_A_DAY),
        (run_state.dump(0, EMPTY), b""),
        (b'{"round": 12, "started": "2026-01-01T00:00:00Z"}', LOG_OF_A_DAY),
        (b"\xff", b"\xff"),
    ],
    ids=["round 12 and a day", "round 0 and no line", "a text with a time", "no text"],
)
def test_times_beside_the_file_change_nothing_and_only_the_instance_file_is_opened(
    root, monkeypatch, state, log
):
    place(root, raw(doc(round_budget=8, wall_clock_budget_s=5400)))
    place(root, state, STATE_FILE)
    place(root, log, EVENTS_FILE)
    place(root, b"{}", f"runs/{RUN}/rounds/0000/candidates/01/spec.json")
    place(root, raw(doc(wall_clock_budget_s=OTHER_SECONDS)), OTHER_FILE)
    before = snapshot(root)
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert wall_clock_budget_s_of(root, RUN) == 5400
    assert opened == [FILE]
    assert wall_clock_budget_s_of(root, RUN) == 5400
    assert round_budget_of(root, RUN) == 8
    assert opened == [FILE, FILE, FILE]
    monkeypatch.setattr(Path, "read_bytes", real)
    assert snapshot(root) == before


# --- with hilclaw.hw_tool: a file invalid by its wall_clock_budget_s alone ---


@pytest.mark.parametrize(
    "repaired",
    [doc(), doc(wall_clock_budget_s=SECONDS), doc(wall_clock_budget_s=1)],
    ids=["removed", "valid", "valid and of one second"],
)
@pytest.mark.parametrize(
    "broken", [0, -5400, 5400.0, "5400", "8h", True, None, MAX + 1], ids=repr
)
def test_a_file_invalid_by_its_wall_clock_budget_alone_is_run_file_invalid(
    root, broken, repaired
):
    place(started(root), raw(doc(**ALL_BUT_SECONDS, wall_clock_budget_s=broken)))
    tool = Tool(root)

    assert_no_step_started(
        tool,
        root,
        "run_file_invalid",
        InvalidInstanceError,
        "wall_clock_budget_s: must be an int from 1 to",
    )
    assert kinds(root) == []

    place(root, raw(repaired))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]


# --- happy: the members owner and project (ADR-0034) ---

# Placeholders: they name no person, no account and no project that exists, and none is a default.
OWNER, OTHER_OWNER = "example-owner", "another-example-owner"
PROJECT, OTHER_PROJECT = "example-project", "another-example-project"
NAMED = {"owner": owner_of, "project": project_of}
STATED = {"owner": OWNER, "project": PROJECT}
OTHER_OF = {"owner": "project", "project": "owner"}
NO_NAME = ": must be a str of 1 to 255 printable ASCII characters, got "
OWNER_MEMBER = f'"owner": "{OWNER}"'
PROJECT_MEMBER = f'"project": "{PROJECT}"'
EVERY_CHARACTER = "".join(chr(code) for code in range(0x20, 0x7F))
NAMES = [
    OWNER,
    PROJECT,
    "Example-Owner",
    "example-owner ",
    " example-owner",
    "a b",
    "x/y",
    "user@example.invalid",
    " ",
    "   ",
    "~",
    "e",
    '"',
    "\\",
    "e" * 255,
    " " * 255,
    EVERY_CHARACTER,
]
ALL_BUT_THE_NAMES = {**ALL_BUT_SECONDS, "wall_clock_budget_s": SECONDS}
ALL_BUT_THE_NAMES_TEXT = (*ALL_BUT_SECONDS_TEXT, SECONDS_MEMBER)
STATED_BESIDE_THE_NAMES = (*STATED_BESIDE_THE_SECONDS, SECONDS)
# A made-up word that is no name of a user, of a directory or of a run outside these tests.
MARKER = "marker-of-the-tests"


def named(member, literal, *more):
    return text(VERSION, SECTION, f'"{member}": {literal}', *more)


def pair(member, value):
    return (value, None) if member == "owner" else (None, value)


def assert_the_members_beside_the_names_are_stated(root, run=RUN):
    assert_the_members_beside_the_seconds_are_stated(root, run)
    assert wall_clock_budget_s_of(root, run) == SECONDS


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize("name", NAMES, ids=shown)
def test_a_content_with_the_member_states_that_name(member, name):
    document = doc(**{member: name}, example=[1])

    result = parse(raw(document))

    assert result == Instance(
        KEY, record(), *[None] * 7, *pair(member, name), {"example": [1]}
    )
    assert type(getattr(result, member)) is str
    assert member not in result.others
    assert validate(document) is None
    assert getattr(parse(named(member, json.dumps(name))), member) == name


def test_both_ends_of_the_length_and_of_the_character_range_are_inclusive():
    assert (EVERY_CHARACTER[0], EVERY_CHARACTER[-1]) == (" ", "~")
    assert len(EVERY_CHARACTER) == 95

    for member in NAMED:
        refused = member + NO_NAME + "str"
        for length in (1, 2, 254, 255):
            for character in (" ", "e", "~"):
                document = doc(**{member: character * length})
                assert getattr(parse(raw(document)), member) == character * length
                assert validate(document) is None
        for name in ("", "e" * 256, "e" * 257, " " * 256, "\x1f", "\x7f"):
            invalid(refused, validate, doc(**{member: name}))
            invalid(refused, parse, raw(doc(**{member: name})))


@pytest.mark.parametrize(
    "literal, name",
    [
        ('"\\u0041"', "A"),
        ('"\\u0020"', " "),
        ('"\\u007e"', "~"),
        ('"\\u007E"', "~"),
        ('"x\\/y"', "x/y"),
        ('"\\"\\\\"', '"\\'),
        ('"\\u0065xample-owner"', OWNER),
    ],
)
def test_the_value_is_the_string_after_json_decoding(literal, name):
    for member in NAMED:
        assert getattr(parse(named(member, literal)), member) == name


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize(
    "members", [{}, EVERY_MEMBER, ALL_BUT_THE_NAMES, {"round_budget": 1}], ids=repr
)
def test_a_content_without_a_member_states_none_for_it(member, members):
    other = OTHER_OF[member]

    for beside in ({}, {other: STATED[other]}):
        without = parse(raw(doc(**members, **beside)))
        stated = parse(raw(doc(**members, **beside, **{member: STATED[member]})))

        assert getattr(without, member) is None
        assert getattr(stated, member) == STATED[member]
        assert getattr(without, other) == getattr(stated, other) == beside.get(other)
        assert without[:9] == stated[:9]
        assert without.others == stated.others == {}
        assert validate(doc(**members, **beside)) is None


@pytest.mark.parametrize("index", range(10))
def test_any_place_of_the_names_among_the_other_members(index):
    expected = Instance(*STATED_BESIDE_THE_NAMES, OWNER, PROJECT, {})
    others = [*COUNTED_MEMBERS, OP_SECTION, BUDGET_MEMBER, SECONDS_MEMBER]

    for first, second in (
        (OWNER_MEMBER, PROJECT_MEMBER),
        (PROJECT_MEMBER, OWNER_MEMBER),
    ):
        members = [*others[:index], first, *others[index:]]
        members.insert(len(others) - index, second)
        assert parse(text(*members)) == expected
        assert validate(json.loads(text(*members))) is None


def test_white_space_of_json_around_a_name_is_not_part_of_the_value_and_inside_it_is():
    for member, name in STATED.items():
        content = text(VERSION, SECTION, f'\r\n\t"{member}" :\n "{name}" \n')
        assert getattr(parse(content), member) == name

        assert getattr(parse(named(member, f'" {name}  "')), member) == f" {name}  "


# The Example of ADR-0034: that of ADR-0033 with the two members the record adds, not a valid file.
EXAMPLE_OF_ADR_0034 = EXAMPLE_OF_ADR_0033.replace(
    b'"wall_clock_budget_s": 5400\n',
    b'"wall_clock_budget_s": 5400,\n'
    b'  "owner": "example-owner",\n'
    b'  "project": "example-project"\n',
)


def test_the_members_of_the_example_of_adr_0034():
    assert EXAMPLE_OF_ADR_0034.count(b'"example-') == 2
    invalid("hw_profile.record.hw_source: must be ", parse, EXAMPLE_OF_ADR_0034)

    result = parse(
        EXAMPLE_OF_ADR_0034.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
    )
    assert (result.owner, result.project) == ("example-owner", "example-project")
    assert (result.round_budget, result.wall_clock_budget_s) == (8, 5400)
    assert result.others == {}

    silent = parse(
        EXAMPLE_OF_ADR_0033.replace(EXAMPLE_SOURCE, b'"hw_source": "in_house"')
    )
    assert (silent.owner, silent.project) == (None, None)
    assert silent[:9] == result[:9]


def test_the_valid_files_of_the_walk_through_of_adr_0034(root):
    stated = (*ALL_BUT_THE_NAMES_TEXT, OWNER_MEMBER)

    place(root, text(VERSION, SECTION, *stated, PROJECT_MEMBER))
    for _ in range(2):
        assert (owner_of(root, RUN), project_of(root, RUN)) == (OWNER, PROJECT)

    place(root, text(VERSION, SECTION, *stated))
    assert (owner_of(root, RUN), project_of(root, RUN)) == (OWNER, None)

    place(root, text(VERSION, SECTION, *ALL_BUT_THE_NAMES_TEXT))
    assert (owner_of(root, RUN), project_of(root, RUN)) == (None, None)
    assert_the_members_beside_the_names_are_stated(root)

    for name, value in (("Owner", OWNER), ("user", OWNER), ("projectname", PROJECT)):
        place(root, text(VERSION, SECTION, f'"{name}": "{value}"'))
        assert (owner_of(root, RUN), project_of(root, RUN)) == (None, None)
        assert read(root, RUN).others == {name: value}


# --- branch: the members owner and project ---


@pytest.mark.parametrize(
    "owner, project",
    [
        (OWNER, PROJECT),
        (OWNER, None),
        (None, PROJECT),
        (None, None),
        (OWNER, OWNER),
        (PROJECT, OWNER),
        (" ", "~"),
        ("e" * 255, "e"),
        ("Example-Owner", "example-owner"),
    ],
    ids=shown,
)
def test_the_two_members_do_not_bound_each_other(root, owner, project):
    stated = {"owner": owner, "project": project}
    document = doc(
        **{name: value for name, value in stated.items() if value is not None}
    )

    result = parse(raw(document))

    assert (result.owner, result.project) == (owner, project)
    assert validate(document) is None
    place(root, raw(document))
    assert owner_of(root, RUN) == owner
    assert project_of(root, RUN) == project


def test_values_that_differ_in_case_or_in_a_final_space_are_three_values(root):
    spellings = ["Example-Owner", "example-owner", "example-owner "]

    for member, reader in NAMED.items():
        found = []
        for spelling in spellings:
            place(root, raw(doc(**{member: spelling})))
            found.append(reader(root, RUN))
        assert found == spellings
        assert len(set(found)) == 3


def test_a_name_equal_to_another_value_of_the_run_is_valid_and_nothing_follows(
    tmp_path, root
):
    profile = record(label="a label")

    for name in ("a label", "external", RUN, root.name, COMMIT, key_of(profile)):
        for member, reader in NAMED.items():
            document = doc(profile, source_commit=COMMIT, **{member: name})
            place(root, raw(document))
            before = snapshot(tmp_path)

            assert reader(root, RUN) == name
            assert validate(document) is None
            assert hw_profile_of(root, RUN) == profile
            assert source_commit_of(root, RUN) == COMMIT
            assert snapshot(tmp_path) == before


BROKEN_NAMES = [None, True, 7, "", "e" * 256, "a\nb", [OWNER], {"name": OWNER}]


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize("version", [0, 2, MAX])
@pytest.mark.parametrize("name", [*BROKEN_NAMES, OWNER], ids=shown)
def test_another_version_is_reported_before_the_names_are_looked_at(
    member, version, name
):
    document = doc(schema_version=version, **{member: name})

    for function, argument in ((parse, raw(document)), (validate, document)):
        with pytest.raises(UnsupportedVersionError) as caught:
            function(argument)
        assert str(caught.value) == f"schema_version: {version} is not supported"


@pytest.mark.parametrize(
    "others",
    [
        {"Owner": OWNER},
        {"OWNER": OWNER},
        {"user": OWNER},
        {"username": OWNER},
        {"owner_name": OWNER},
        {"account": OWNER},
        {"started_by": OWNER},
        {"owner ": ""},
        {"Project": PROJECT},
        {"PROJECT": PROJECT},
        {"projectname": PROJECT},
        {"project_name": PROJECT},
        {"project ": None},
        {"meta": {"owner": OWNER, "project": PROJECT}},
        {"lock": {"owner": OWNER, "heartbeat": 1}},
        {
            "Owner": "",
            "user": None,
            "username": 7,
            "meta": {"owner": "", "project": []},
            "Project": [],
            "projectname": "a\nb",
        },
    ],
    ids=repr,
)
def test_a_top_level_member_of_another_name_states_no_owner_and_no_project(others):
    result = parse(raw(doc(**others)))

    assert result == Instance(KEY, record(), *[None] * 9, others)
    assert (result.owner, result.project) == (None, None)
    assert validate(doc(**others)) is None

    result = parse(raw(doc(owner=OTHER_OWNER, project=OTHER_PROJECT, **others)))
    assert (result.owner, result.project) == (OTHER_OWNER, OTHER_PROJECT)
    assert result.others == others


@pytest.mark.parametrize(
    "place, changes",
    [
        ("hw_profile: must be", {"hw_profile": None, "owner": ""}),
        (
            "document: lacks the member hw_profile",
            {"hw_profile": REMOVE, "project": 7},
        ),
        ("tolerance: must be", {"tolerance": None, "owner": None}),
        (NO_COMMIT + "str 'main'", {"source_commit": "main", "project": ""}),
        (NO_BOUND + "int", {"n_max": 4, "owner": ""}),
        (NO_COUNT + "int", {"candidates_per_round": 0, "owner": ""}),
        (
            "op_signature: must be an object, got NoneType",
            {"op_signature": None, "project": ""},
        ),
        (NO_BUDGET + "int", {"round_budget": 0, "owner": "", "project": ""}),
        (NO_SECONDS + "int", {"owner": "", "project": "", "wall_clock_budget_s": 0}),
        (
            NO_SECONDS + "str '8h'",
            {**ALL_BUT_SECONDS, "wall_clock_budget_s": "8h", "owner": 7},
        ),
        ("owner" + NO_NAME + "str ''", {"owner": "", "project": 7}),
        ("owner" + NO_NAME + "str ''", {"project": 7, "owner": ""}),
        ("owner" + NO_NAME + "int", {**ALL_BUT_THE_NAMES, "owner": 7, "project": ""}),
        ("owner" + NO_NAME + "NoneType", {"project": PROJECT, "owner": None}),
        ("project" + NO_NAME + "str ''", {"owner": OWNER, "project": ""}),
        ("project" + NO_NAME + "bool", {"project": False}),
    ],
)
def test_the_first_broken_rule_is_reported_with_the_names(place, changes):
    document = doc(**changes)

    invalid(place, parse, raw(document))
    invalid(place, validate, document)


# --- error / negative: the members owner and project ---

WALK_THROUGH_OF_ADR_0034 = [
    '""',
    "null",
    "7",
    "true",
    '["example-owner"]',
    '{"name": "example-owner"}',
    '"' + "e" * 256 + '"',
    '"example\\nowner"',
    '"\\u00e9xample-owner"',
]
NO_NAME_LITERALS = [
    *WALK_THROUGH_OF_ADR_0034,
    "false",
    "0",
    "1.5",
    "[]",
    "{}",
    '"example-owner\\n"',
    '"\\nexample-owner"',
    '"\\u000a"',
    '"\\t"',
    '"example\\towner"',
    '"example-owner\\r"',
    '"example\\u007fowner"',
    '"example-owner\\u0000"',
    '"\\u001f"',
    '"\\u0080"',
    '"examplé"',
    '"example-한"',
    '"\\ud55c\\uae00"',
    '"\\ud83d"',
    '"example-owner\\ud83d"',
]


def got(literal):
    value = json.loads(literal)
    if type(value) is str:
        return f"str {reprlib.repr(value)}"
    return type(value).__name__


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize("literal", NO_NAME_LITERALS, ids=ascii)
def test_what_is_no_value_of_the_names(root, member, literal):
    content = named(member, literal, *ALL_BUT_THE_NAMES_TEXT, '"example": [1]')
    expected = member + NO_NAME + got(literal)

    assert invalid(member + NO_NAME, parse, content) == expected
    assert invalid(member + NO_NAME, validate, json.loads(content)) == expected
    place(root, content)
    assert invalid(FILE, NAMED[member], root, RUN) == f"{FILE}: {expected}"
    kept = parse(text(VERSION, SECTION, *ALL_BUT_THE_NAMES_TEXT, '"example": [1]'))
    assert kept == Instance(*STATED_BESIDE_THE_NAMES, None, None, {"example": [1]})


# A line feed, a carriage return, a tab, U+0000, U+001F, U+007F, U+0080, a letter with an accent, a Hangul letter, a full-width letter and a lone surrogate.
OUTSIDE = [
    "\n",
    "\r",
    "\t",
    "\x00",
    "\x1f",
    "\x7f",
    "\x80",
    "é",
    "한",
    "ａ",
    "\ud83d",
]


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize("character", OUTSIDE, ids=ascii)
def test_a_character_outside_the_range_is_refused_at_any_position(member, character):
    for name in (
        character,
        character + OWNER,
        OWNER[:7] + character + OWNER[7:],
        OWNER + character,
        "e" * 254 + character,
    ):
        expected = f"{member}{NO_NAME}str {reprlib.repr(name)}"
        assert invalid(member + NO_NAME, validate, doc(**{member: name})) == expected
        assert invalid(member + NO_NAME, parse, raw(doc(**{member: name}))) == expected
        assert validate(doc(**{member: name.replace(character, "e")})) is None


LOOSER_NAME_RULES = {
    "valid after trimming": (
        lambda value: re.fullmatch(r"[\x20-\x7e]{1,255}", value.strip()) is not None,
        [
            "example-owner\n",
            "\texample-owner",
            "\r\nexample-owner\r\n",
            "e" * 255 + "\n",
        ],
    ),
    "a pattern ending in $": (
        lambda value: re.match(r"[\x20-\x7e]{1,255}$", value) is not None,
        ["example-owner\n", "e" * 255 + "\n", " \n"],
    ),
    "a non-empty string of any characters": (
        lambda value: isinstance(value, str) and len(value) > 0,
        ["éxample", "한글", "a\nb", "\t", "e" * 256, Text(OWNER)],
    ),
    "a JSON string of any length": (
        lambda value: type(value) is str,
        ["", "e" * 256, "e" * 5000],
    ),
    "str.isascii": (str.isascii, ["", "\t", "example\x7fowner", "\x00", "e" * 256]),
    "str.isprintable": (str.isprintable, ["", "éxample", "한", "e" * 256]),
    "a value for nobody": (
        lambda value: value in (None, 0, ""),
        [None, 0, False, ""],
    ),
}


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize("rule", LOOSER_NAME_RULES)
def test_a_name_a_looser_rule_would_accept_is_refused(member, rule):
    looser, values = LOOSER_NAME_RULES[rule]

    for value in values:
        assert looser(value)
        expected = member + NO_NAME + type(value).__name__
        invalid(expected, validate, doc(**{member: value}))
        if type(value) in JSON_TYPES:
            invalid(expected, parse, raw(doc(**{member: value})))


@pytest.mark.parametrize("member", NAMED)
def test_the_member_name_of_a_name_twice_at_the_top_level(member):
    stated = f'"{member}": "{STATED[member]}"'

    for members in (
        (stated, stated),
        (stated, f'"{member}": "{OTHER_OWNER}"'),
        (stated, f'"{member}": ""'),
        (f'"{member}": null', stated),
    ):
        message = invalid(
            "content: cannot be read as one JSON text",
            parse,
            text(VERSION, SECTION, *members),
        )
        assert "a JSON object repeats a member name" in message


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize(
    "value",
    [
        Text(OWNER),
        Text(" "),
        OWNER.encode(),
        bytearray(OWNER.encode()),
        7,
        0,
        1.5,
        True,
        None,
        [OWNER],
        list(OWNER),
        (OWNER,),
        {OWNER},
        {"name": OWNER},
    ],
    ids=shown,
)
def test_validate_refuses_a_name_built_in_memory(member, value):
    document = doc(**{member: value})

    expected = member + NO_NAME + type(value).__name__
    assert invalid(member + NO_NAME, validate, document) == expected


@pytest.mark.parametrize("member", NAMED)
def test_a_refused_string_is_shown_and_a_refused_value_of_another_type_is_not(member):
    start = member + NO_NAME
    assert invalid(start, validate, doc(**{member: ""})) == start + "str ''"
    assert invalid(start, validate, doc(**{member: "a\nb"})) == start + "str 'a\\nb'"

    long = "example-" * 40
    message = invalid(start, parse, raw(doc(**{member: long})))
    assert message == start + "str " + reprlib.repr(long)
    assert long not in message and "..." in message and len(message) < 130

    for value in ([OWNER], {"name": OWNER}, (OWNER,), 7, None):
        message = invalid(start, validate, doc(**{member: value}))
        assert message == start + type(value).__name__
        assert OWNER not in message


def test_a_check_of_a_name_modifies_nothing():
    for document, valid in (
        (doc(owner=OWNER, project=PROJECT), True),
        (doc(owner=" Example-Owner ", project=" "), True),
        (doc(owner=""), False),
        (doc(owner=OWNER, project="a\nb"), False),
        (doc(**ALL_BUT_THE_NAMES, project=[PROJECT]), False),
    ):
        kept = json.dumps(document)
        assert accepted(validate, document) == valid
        assert json.dumps(document) == kept


# --- no substitute: nothing of the module stands in for an owner or a project ---


@pytest.mark.parametrize("member", NAMED)
def test_a_run_without_the_member_states_none_and_nothing_stands_in(
    tmp_path, monkeypatch, member
):
    def fail(*arguments):
        pytest.fail("the user name of the process was asked for")

    monkeypatch.setattr(getpass, "getuser", fail)
    monkeypatch.setattr(os, "getlogin", fail)
    for name in ("USER", "USERNAME", "LOGNAME"):
        monkeypatch.setenv(name, MARKER)
    root = tmp_path / MARKER
    root.mkdir()
    run, other = f"{MARKER}-run", OTHER_OF[member]
    file = f"runs/{run}/instance.json"
    others = {"Owner": "o", "user": "u", "projectname": "p", "meta": {member: "m"}}
    place(root, raw(doc(**ALL_BUT_THE_NAMES, **{other: STATED[other]}, **others)), file)
    place(root, raw(doc(**{member: OTHER_OWNER})), OTHER_FILE)
    before = snapshot(tmp_path)

    found = NAMED[member](root, run)

    assert found is None
    for stand_in in (MARKER, STATED[other], OTHER_OWNER, "anonymous", "unknown", ""):
        assert found != stand_in
    result = read(root, run)
    assert getattr(result, member) is None
    assert getattr(result, other) == STATED[other]
    assert result.others == others
    assert MARKER not in repr(result)
    assert NAMED[other](root, run) == STATED[other]
    assert NAMED[member](root, OTHER_RUN) == OTHER_OWNER
    assert NAMED[member](root, run) is None
    assert snapshot(tmp_path) == before

    place(root, raw(doc()), file)
    assert (owner_of(root, run), project_of(root, run)) == (None, None)


def test_nothing_of_the_module_stands_in_for_an_owner_or_a_project():
    functions = [
        value
        for value in vars(instance).values()
        if inspect.isfunction(value) and value.__module__ == instance.__name__
    ]
    assert owner_of in functions and project_of in functions
    for function in functions:
        assert function.__defaults__ is None and function.__kwdefaults__ is None
    assert Instance._field_defaults == {}
    imported = set()
    for node in ast.walk(ast.parse(inspect.getsource(instance))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    parts = {part for name in imported for part in name.split(".")}
    assert "keys" in parts
    assert not parts & {
        "getpass",
        "pwd",
        "subprocess",
        "socket",
        "driver_state",
        "run_state",
        "journal",
        "run_journal",
        "events",
        "run_id",
    }
    assert not {"getpass", "pwd", "owner", "project"} & set(vars(instance))


# --- the readers of the owner and of the project (ADR-0034) ---


@pytest.mark.parametrize("member", NAMED)
def test_the_reader_returns_the_name_the_file_states(tmp_path, root, member):
    reader, other = NAMED[member], OTHER_OF[member]
    place(root, raw(doc(**ALL_BUT_THE_NAMES, **STATED, example=[1])))
    before = snapshot(tmp_path)

    found = reader(root, RUN)

    assert found == STATED[member] and type(found) is str
    assert found == getattr(read(root, RUN), member)
    assert reader(str(root), RUN) == found
    assert NAMED[other](root, RUN) == STATED[other]
    assert_the_members_beside_the_names_are_stated(root)
    assert snapshot(tmp_path) == before

    for name in NAMES:
        place(root, raw(doc(**{member: name})))
        assert reader(root, RUN) == name
        assert NAMED[other](root, RUN) is None


@pytest.mark.parametrize("member", NAMED)
def test_a_name_replaced_between_two_calls_is_seen_at_the_second(root, member):
    reader = NAMED[member]
    place(root, raw(doc(**{member: OWNER})))
    assert reader(root, RUN) == OWNER

    place(root, raw(doc(**{member: OTHER_OWNER})))
    assert reader(root, RUN) == OTHER_OWNER

    place(root, raw(doc()))
    assert reader(root, RUN) is None

    place(root, raw(doc(**{member: ""})))
    invalid(f"{FILE}: {member}{NO_NAME}str ''", reader, root, RUN)

    place(root, raw(doc(schema_version=2, **{member: OWNER})))
    with pytest.raises(UnsupportedVersionError):
        reader(root, RUN)

    (root / FILE).unlink()
    with pytest.raises(MissingInstanceError):
        reader(root, RUN)

    place(root, raw(doc(**{member: " "})))
    assert reader(root, RUN) == " "


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize(
    "literal",
    [*WALK_THROUGH_OF_ADR_0034, "false", "{}", '"example-owner\\n"', '"\\t"'],
    ids=ascii,
)
def test_no_member_of_a_file_with_an_invalid_name_is_used(root, member, literal):
    other = OTHER_OF[member]
    stated = (*ALL_BUT_THE_NAMES_TEXT, f'"{other}": "{STATED[other]}"')
    place(root, named(member, json.dumps(STATED[member]), *stated))
    assert NAMED[member](root, RUN) == STATED[member]
    assert_the_members_beside_the_names_are_stated(root)

    place(root, named(member, literal, *stated))
    assert owner_of in READERS and project_of in READERS and len(READERS) == 12
    for call in READERS:
        invalid(f"{FILE}: {member}{NO_NAME}", call, root, RUN)

    place(root, text(VERSION, SECTION, *stated))
    assert NAMED[member](root, RUN) is None
    assert NAMED[other](root, RUN) == STATED[other]
    assert_the_members_beside_the_names_are_stated(root)


@pytest.mark.parametrize("member", NAMED)
def test_two_runs_that_state_the_same_name_state_their_own_and_nothing_follows(
    tmp_path, root, member
):
    reader = NAMED[member]
    place(root, raw(doc(**{member: OWNER})))
    place(root, raw(doc(OTHER_RECORD, **{member: OWNER})), OTHER_FILE)
    place(root, raw(doc(**{member: OTHER_OWNER})), "runs/run-c/instance.json")
    place(root, raw(doc()), "runs/run-d/instance.json")
    before = snapshot(tmp_path)

    assert reader(root, RUN) == reader(root, OTHER_RUN) == OWNER
    assert reader(root, "run-c") == OTHER_OWNER
    assert reader(root, "run-d") is None
    assert hw_profile_of(root, RUN) == record()
    assert hw_profile_of(root, OTHER_RUN) == OTHER_RECORD
    assert reader(root, RUN) == OWNER
    assert snapshot(tmp_path) == before


def test_only_the_instance_file_is_opened_for_an_owner_and_a_project(root, monkeypatch):
    place(root, raw(doc(owner=OWNER, project=PROJECT)))
    place(root, run_state.dump(12, EMPTY), STATE_FILE)
    place(root, b'{"seq": 1, "owner": "another-example-owner"}\n', EVENTS_FILE)
    place(root, raw(doc(owner=OTHER_OWNER, project=OTHER_PROJECT)), OTHER_FILE)
    place(root, b'{"owner": "another-example-owner"}', f"db/{KEY}/example.json")
    before = snapshot(root)
    opened, real = [], Path.read_bytes

    def read_bytes(path):
        opened.append(path.relative_to(root).as_posix())
        return real(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    monkeypatch.setenv("HILCLAW_DATA_ROOT", "elsewhere")

    assert owner_of(root, RUN) == OWNER
    assert opened == [FILE]
    assert project_of(root, RUN) == PROJECT
    assert opened == [FILE, FILE]
    monkeypatch.setattr(Path, "read_bytes", real)
    assert snapshot(root) == before


# --- the rule of the two members and the string of the key records ---

STRINGS = [
    *NAMES,
    "e" * 254,
    *(json.loads(literal) for literal in NO_NAME_LITERALS if literal[0] == '"'),
    *("example" + character for character in OUTSIDE),
    *(values for _, strings in LOOSER_NAME_RULES.values() for values in strings),
]


@pytest.mark.parametrize(
    "value", [value for value in STRINGS if type(value) is str], ids=ascii
)
def test_the_rule_agrees_with_the_string_of_the_key_records(value):
    try:
        keys.hw_profile_key(record(label=value))
        a_string = True
    except keys.InvalidRecordError:
        a_string = False

    for member in NAMED:
        assert accepted(validate, doc(**{member: value})) == a_string


# --- with hilclaw.hw_tool: a file invalid by its owner or its project alone ---


@pytest.mark.parametrize("member", NAMED)
@pytest.mark.parametrize(
    "repaired", [None, OWNER, " "], ids=["removed", "valid", "valid and one space"]
)
@pytest.mark.parametrize("broken", ["", "e" * 256, "a\nb", 7, None, [OWNER]], ids=shown)
def test_a_file_invalid_by_a_name_alone_is_run_file_invalid(
    root, member, broken, repaired
):
    place(started(root), raw(doc(**ALL_BUT_THE_NAMES, **{member: broken})))
    tool = Tool(root)

    assert_no_step_started(
        tool, root, "run_file_invalid", InvalidInstanceError, member + NO_NAME
    )
    assert kinds(root) == []

    place(root, raw(doc() if repaired is None else doc(**{member: repaired})))
    assert tool.function(dict(REQUEST)) == {"example_member": 1}
    assert kinds(root) == ["step_started", "step_ended"]
    assert (len(tool.asked), tool.performed) == (1, 1)
    assert [seen for _, _, seen in tool.asked] == [record()]
