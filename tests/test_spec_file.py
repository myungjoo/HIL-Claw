import ast
import builtins
import codecs
import copy
import inspect
import io
import json
import os
import re
import secrets
from pathlib import Path

import pytest

from hilclaw import instance, instance_file, keys, layout, run_state, spec, spec_file
from hilclaw.spec_file import (
    InvalidSpecFileError,
    NameTakenError,
    UnsupportedVersionError,
    WrittenFormError,
    final_name,
    parse,
    write,
)

# Synthetic values only: no record, key, member or tuple of a real run.
MAX = keys.MAX_INTEGER
MARK = "@@synthetic-mark@@"
TOO_LONG_TEXT = "1" + "0" * 5000
NOT_ONE_TEXT = "content: cannot be read as one JSON text"
FREE_PLACES = {
    "a member of a profile": ("feedback", "attempts", 0, "profile", "synthetic"),
    "a value of ext": ("ext", "synthetic_ext"),
}
FREE_LITERALS = [
    "-0",
    "-0.0",
    "1.5",
    "1e3",
    "-7",
    "9007199254740992",
    "123456789012345678901234567890",
    "true",
    "null",
    '"-0"',
    "[-0, [1.5, {}], []]",
    '{"a": {"b": [-0, 1E+2, -0.0]}, "c": null}',
]


def synthetic_hw():
    return {
        "schema_version": 1,
        "accelerator": "synthetic_accel",
        "revision": "synthetic-rev-A",
        "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
        "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
        "hw_source": "in_house",
    }


def synthetic_op():
    return {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 3, "k": 5, "n": 7},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }


def minimal(hw=None, op=None, shape=(3, 5)):
    hw = synthetic_hw() if hw is None else hw
    op = synthetic_op() if op is None else op
    operand = {
        "name": "synthetic_a",
        "role": "input",
        "dtype": "synthetic_dtype",
        "shape": list(shape),
    }
    return {
        "schema_version": 2,
        "id": {
            "run_id": "synthetic-run-1",
            "round": 1,
            "candidate": 1,
            "attempt": 1,
            "candidates": 1,
            "relation": "single",
        },
        "hw_profile": {"key": keys.hw_profile_key(hw).name, "record": hw},
        "task": {
            "op_signature": {"key": keys.op_signature_key(op).name, "record": op},
            "contract": {
                "language": "synthetic_lang",
                "prototype": "synthetic prototype text",
                "operands": [operand],
            },
            "objective": {
                "objectives": [{"type": "latency_minimisation"}],
                "constraints": [],
            },
        },
        "guidance": {"techniques": []},
        "feedback": {"attempts": []},
    }


def entry(**members):
    return {"round": 1, "candidate": 1, "attempt": 1, "techniques": [], **members}


def full():
    hw, op = synthetic_hw(), synthetic_op()
    hw["host"]["synthetic_cores"] = 8
    hw["ext"] = {"synthetic_word": "w", "synthetic_number": 2}
    op["ext"] = {"synthetic_number": 3}
    made = minimal(hw, op)
    made["id"].update(round=4, candidate=2, candidates=3, relation="same_technique")
    made["id"]["variant"] = "synthetic variant: the second of three"
    made["task"]["build"] = {
        "synthetic_flag": "-synthetic",
        "synthetic_threads": 4,
        "synthetic_list": ["a", "b"],
    }
    made["guidance"]["techniques"] = [
        {"id": "synthetic-technique-1", "text": "synthetic guidance"}
    ]
    report = "synthetic report"
    made["feedback"] = {
        "base": {"round": 3, "candidate": 1, "attempt": 2},
        "attempts": [
            entry(round=0, failure={"stage": "compile", "report": report}),
            entry(round=2, profile={"synthetic": [1, 2.5, None]}),
        ],
    }
    made["ext"] = {"synthetic_ext": {"anything": [1.5, None, True]}, "other": None}
    return made


def repair():
    made = minimal()
    made["id"]["attempt"] = 2
    failure = {"attempt": 1, "stage": "compile", "report": "synthetic report"}
    made["repair"] = {"failures": [failure]}
    return made


def version_one():
    made = full()
    made["schema_version"] = 1
    made["task"]["objective"] = {"synthetic_target": 1.5}
    return made


def changed(document, path, value):
    made = copy.deepcopy(document)
    target = made
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return made


def raw(document):
    return json.dumps(document).encode()


def spelt(document, path, literal):
    return raw(changed(document, path, MARK)).replace(f'"{MARK}"'.encode(), literal)


def invalid(place, content):
    with pytest.raises(InvalidSpecFileError) as caught:
        parse(content)
    assert str(caught.value).startswith(place), str(caught.value)
    return str(caught.value)


def other_version(content, version):
    with pytest.raises(UnsupportedVersionError) as caught:
        parse(content)
    assert str(caught.value) == f"schema_version: is {version}, not 2"
    assert not isinstance(caught.value, ValueError)


def with_zeros():
    hw, op = synthetic_hw(), synthetic_op()
    hw["host"]["synthetic_cores"] = 0
    hw["ext"] = {"synthetic_number": 0}
    op["shape"]["m"] = 0
    op["ext"] = {"synthetic_number": 0}
    made = minimal(hw, op, shape=(0, 5))
    made["id"]["round"] = 0
    made["task"]["build"] = {"synthetic_threads": 0}
    made["feedback"] = {
        "base": {"round": 0, "candidate": 1, "attempt": 1},
        "attempts": [entry(round=0)],
    }
    return made


INTEGER_PLACES = {
    "id.round": ("id", "round"),
    "feedback.attempts[0].round": ("feedback", "attempts", 0, "round"),
    "feedback.base.round": ("feedback", "base", "round"),
    "task.contract.operands[0].shape[0]": (
        "task",
        "contract",
        "operands",
        0,
        "shape",
        0,
    ),
    "task.op_signature.record.shape.m": (
        "task",
        "op_signature",
        "record",
        "shape",
        "m",
    ),
    "task.build.synthetic_threads": ("task", "build", "synthetic_threads"),
    "hw_profile.record.host.synthetic_cores": (
        "hw_profile",
        "record",
        "host",
        "synthetic_cores",
    ),
    "hw_profile.record.ext.synthetic_number": (
        "hw_profile",
        "record",
        "ext",
        "synthetic_number",
    ),
    "task.op_signature.record.ext.synthetic_number": (
        "task",
        "op_signature",
        "record",
        "ext",
        "synthetic_number",
    ),
}


@pytest.mark.parametrize("document", [minimal(), full(), repair(), with_zeros()])
def test_a_valid_content_parses_to_the_document_json_gives(document):
    content = raw(document)
    assert parse(content) == document
    assert type(parse(content)) is dict


def test_any_member_order_is_accepted():
    document = full()
    backwards = dict(reversed(document.items()))
    backwards["id"] = dict(reversed(document["id"].items()))
    content = raw(backwards)
    assert content != raw(document)
    assert parse(content) == document
    assert parse(json.dumps(document, sort_keys=True).encode()) == document


@pytest.mark.parametrize(
    "form",
    [
        lambda document: json.dumps(document, indent=1) + "\n",
        lambda document: json.dumps(document, indent=1).replace("\n", "\r\n"),
        lambda document: json.dumps(document, separators=(",", ":")),
        lambda document: " \t\r\n" + json.dumps(document, indent="\t") + "\n\n \t",
    ],
)
def test_white_space_and_line_ends_are_not_checked(form):
    document = full()
    assert parse(form(document).encode()) == document


def test_text_outside_ascii_is_read_as_utf_8():
    document = changed(
        minimal(), ("task", "contract", "prototype"), "원형 é ∑ \U0001f600"
    )
    content = json.dumps(document, ensure_ascii=False).encode("utf-8")
    assert "원형".encode() in content
    assert parse(content) == document
    assert parse(raw(document)) == document


@pytest.mark.parametrize("path", INTEGER_PLACES.values(), ids=INTEGER_PLACES)
def test_zero_is_a_value_of_an_integer_place(path):
    content = spelt(with_zeros(), path, b"0")
    assert parse(content) == with_zeros()


@pytest.mark.parametrize("place", INTEGER_PLACES)
def test_minus_zero_at_an_integer_place_is_refused_by_its_text(place):
    content = spelt(with_zeros(), INTEGER_PLACES[place], b"-0")
    document = json.loads(content)
    assert document == with_zeros()
    spec.validate(document)
    message = invalid(f"{place}: ", content)
    assert message == f"{place}: is written as -0, which is no integer"


@pytest.mark.parametrize(
    ("path", "place"),
    [
        (("schema_version",), "schema_version: is written as -0"),
        (
            ("hw_profile", "record", "schema_version"),
            "hw_profile.record: schema_version: must be the integer 1, got 0",
        ),
        (
            ("task", "op_signature", "record", "schema_version"),
            "task.op_signature.record: schema_version: must be the integer 1, got 0",
        ),
    ],
)
def test_minus_zero_as_a_schema_version_is_invalid_and_no_other_version(path, place):
    invalid(place, spelt(minimal(), path, b"-0"))


def test_minus_zero_as_the_only_member_is_invalid_and_no_other_version():
    message = invalid("schema_version: ", b'{"schema_version": -0}')
    assert message == "schema_version: is written as -0, which is no integer"


@pytest.mark.parametrize("literal", [b"1.0", b"1e0", b"1E0", b"-0.0", b"0.0"])
@pytest.mark.parametrize("place", INTEGER_PLACES)
def test_a_fraction_or_an_exponent_at_an_integer_place_is_refused(place, literal):
    content = spelt(with_zeros(), INTEGER_PLACES[place], literal)
    assert type(json.loads(literal)) is float
    with pytest.raises(spec.InvalidSpecError):
        spec.validate(json.loads(content))
    with pytest.raises(InvalidSpecFileError):
        parse(content)


@pytest.mark.parametrize(
    ("literal", "place"),
    [
        (str(MAX + 1), "id.round: must be an integer from 0 to 2**53 - 1"),
        ("-1", "id.round: must be an integer from 0 to 2**53 - 1"),
        (TOO_LONG_TEXT, NOT_ONE_TEXT),
    ],
)
def test_an_integer_place_outside_the_range_is_refused(literal, place):
    invalid(place, spelt(minimal(), ("id", "round"), literal.encode()))
    assert parse(spelt(minimal(), ("id", "round"), str(MAX).encode()))


@pytest.mark.parametrize("literal", FREE_LITERALS)
@pytest.mark.parametrize("place", FREE_PLACES)
def test_any_json_value_is_accepted_below_the_two_free_places(place, literal):
    document = changed(full(), ("feedback", "attempts", 0, "profile"), {})
    content = spelt(document, FREE_PLACES[place], literal.encode())
    result = parse(content)
    assert repr(result) == repr(json.loads(content))
    target = result
    for part in FREE_PLACES[place]:
        target = target[part]
    assert repr(target) == repr(json.loads(literal))


def test_a_profile_and_an_ext_value_may_nest_minus_zero_deeply():
    document = full()
    content = spelt(document, ("ext", "other"), b'[{"a": [{"b": -0}]}]')
    assert parse(content)["ext"]["other"] == [{"a": [{"b": 0}]}]
    path = ("feedback", "attempts", 1, "profile")
    content = spelt(document, path, b'{"a": -0, "b": {"c": [-0]}}')
    assert parse(content)["feedback"]["attempts"][1]["profile"]["a"] == 0


OBJECTIVE_PATHS = {
    "task.objective": ("task", "objective"),
    "task.objective.objectives": ("task", "objective", "objectives"),
    "task.objective.objectives[0]": ("task", "objective", "objectives", 0),
    "task.objective.objectives[0].type": ("task", "objective", "objectives", 0, "type"),
    "task.objective.constraints": ("task", "objective", "constraints"),
}
OBJECTIVE_LITERALS = [
    "-0",
    "0",
    "1.5",
    "1e999",
    "[-0]",
    "[1.5, 1e999]",
    '{"a": {"b": [-0, 1E+2, -0.0]}, "c": null}',
    '[{"type": "memory_ceiling", "bound": -0}]',
    '[{"type": "memory_ceiling", "bound": 5.0}]',
    '[{"type": "memory_ceiling", "bound": 123456789}]',
    '{"objectives": [{"type": "latency_minimisation", "weight": -0}], "constraints": []}',
    '{"objectives": [{"type": "latency_minimisation"}], "constraints": [], "x": 1.5}',
]


@pytest.mark.parametrize("literal", OBJECTIVE_LITERALS)
@pytest.mark.parametrize("place", OBJECTIVE_PATHS)
def test_a_number_inside_the_objective_is_invalid_by_the_validator(place, literal):
    content = spelt(full(), OBJECTIVE_PATHS[place], literal.encode())
    with pytest.raises(spec.InvalidSpecError) as expected:
        spec.validate(json.loads(content))
    message = invalid("task.objective", content)
    assert message == str(expected.value)
    assert "is written as -0" not in message


@pytest.mark.parametrize("place", FREE_PLACES)
def test_a_number_beyond_the_float_range_in_a_free_place_is_an_infinity(place):
    document = changed(full(), ("feedback", "attempts", 0, "profile"), {})
    target = parse(spelt(document, FREE_PLACES[place], b"[1e999, -1e999]"))
    for part in FREE_PLACES[place]:
        target = target[part]
    assert target == [float("inf"), float("-inf")]


@pytest.mark.parametrize("place", FREE_PLACES)
def test_an_integer_literal_too_long_for_the_interpreter_is_not_read(place):
    document = changed(full(), ("feedback", "attempts", 0, "profile"), {})
    content = spelt(document, FREE_PLACES[place], TOO_LONG_TEXT.encode())
    invalid(NOT_ONE_TEXT, content)


@pytest.mark.parametrize(
    "path",
    [
        ("id", "run_id"),
        ("id", "variant"),
        ("task", "contract", "prototype"),
        ("task", "build", "synthetic_flag"),
        ("hw_profile", "record", "host", "cpu"),
        ("hw_profile", "record", "ext", "synthetic_word"),
        ("guidance", "techniques", 0, "text"),
    ],
)
def test_the_string_minus_zero_is_no_number(path):
    document = changed(full(), path, "-0")
    if path[0] == "hw_profile":
        document["hw_profile"]["key"] = keys.hw_profile_key(
            document["hw_profile"]["record"]
        ).name
    assert parse(raw(document)) == document


@pytest.mark.parametrize(
    "content", ["text", bytearray(b"{}"), None, {}, memoryview(b"")]
)
def test_a_content_that_is_no_bytes_is_a_type_error(content):
    with pytest.raises(TypeError, match="content must be bytes, got"):
        parse(content)


def test_a_document_is_no_content():
    with pytest.raises(TypeError, match="content must be bytes, got dict"):
        parse(minimal())


@pytest.mark.parametrize("rest", [b"", b"{}", raw(minimal()), b"\xff"])
def test_a_byte_order_mark_is_refused(rest):
    message = invalid("content: starts with", b"\xef\xbb\xbf" + rest)
    assert message == "content: starts with a byte order mark"


@pytest.mark.parametrize(
    "content",
    [
        b"\xff",
        raw(minimal()) + b"\xc3",
        raw(minimal()).replace(b"synthetic-run-1", b"synthetic-\xe9-1"),
        json.dumps(minimal()).encode("utf-16"),
        json.dumps(minimal()).encode("utf-16-le"),
        json.dumps(minimal()).encode("utf-32-be"),
    ],
)
def test_bytes_that_are_not_utf_8_are_refused(content):
    invalid(NOT_ONE_TEXT, content)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b" ",
        b"\n",
        b" \t\r\n",
        raw(minimal()) + raw(minimal()),
        raw(minimal()) + b"\n" + raw(minimal()),
        raw(minimal()) + b"x",
        raw(minimal()) + b"}",
        raw(minimal())[:-1],
        b"\x00" + raw(minimal()),
        raw(minimal()) + b"\x00",
        raw(minimal()).replace(b'"', b"'"),
        b"{'schema_version': 1}",
        b'{"schema_version": 1,}',
        b'{"schema_version": 01}',
        b'{"schema_version": +1}',
        b'{"schema_version": 0x1}',
        b'{"schema_version": 1} // note',
    ],
)
def test_a_content_that_is_not_exactly_one_json_text_is_refused(content):
    invalid(NOT_ONE_TEXT, content)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_the_tokens_that_are_no_json_are_refused_everywhere(token):
    literal = token.encode()
    message = invalid(NOT_ONE_TEXT, literal)
    assert f"{token} is not a JSON value" in message
    document = changed(full(), ("feedback", "attempts", 0, "profile"), {})
    for path in FREE_PLACES.values():
        invalid(NOT_ONE_TEXT, spelt(document, path, literal))
        invalid(NOT_ONE_TEXT, spelt(document, path, b'[{"a": ' + literal + b"}]"))
    invalid(NOT_ONE_TEXT, spelt(document, ("id", "round"), literal))
    invalid(NOT_ONE_TEXT, b'{"schema_version": 1, "x": ' + literal + b"}")


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"[]", "list"),
        (b"[" + raw(minimal()) + b"]", "list"),
        (b'"text"', "str"),
        (b"1", "int"),
        (b"2", "int"),
        (b"-0", "int"),
        (b"1.5", "float"),
        (b"true", "bool"),
        (b"null", "NoneType"),
    ],
)
def test_a_json_text_that_is_no_object_is_refused(content, kind):
    message = invalid("content: must be", content)
    assert message == f"content: must be a JSON object, got {kind}"


def test_nesting_too_deep_for_the_interpreter_is_reported():
    deep = b"[" * 2_000_000 + b"]" * 2_000_000
    message = invalid(
        "content: is nested", spelt(minimal(), ("task", "objective"), deep)
    )
    assert message == "content: is nested too deeply to parse"
    invalid("content: is nested", deep)


TWICE = {
    "the top level": lambda text: text.replace("{", '{"schema_version": 1, ', 1),
    "the top level, last": lambda text: text[:-1] + ', "guidance": {"techniques": []}}',
    "id": lambda text: text.replace('"id": {', '"id": {"round": 4, '),
    "the hw_profile record": lambda text: text.replace(
        '"accelerator":', '"accelerator": "synthetic_accel", "accelerator":'
    ),
    "a host": lambda text: text.replace('"cpu":', '"cpu": "synthetic cpu", "cpu":'),
    "the ext of a record": lambda text: text.replace(
        '"synthetic_word":', '"synthetic_word": "w", "synthetic_word":'
    ),
    "the op_signature record": lambda text: text.replace(
        '"kind":', '"kind": "gemm", "kind":'
    ),
    "a shape": lambda text: text.replace('"m":', '"m": 3, "m":'),
    "an operand": lambda text: text.replace('"role":', '"role": "input", "role":'),
    "task.build": lambda text: text.replace(
        '"synthetic_threads":', '"synthetic_threads": 4, "synthetic_threads":'
    ),
    "an entry of feedback.attempts": lambda text: text.replace(
        '"failure":', '"techniques": [], "failure":'
    ),
    "task.objective": lambda text: text.replace(
        '"constraints":', '"constraints": [], "constraints":'
    ),
    "an objective entry": lambda text: text.replace(
        '"type":', '"type": "latency_minimisation", "type":'
    ),
    "a profile": lambda text: text.replace(
        '"synthetic": [', '"synthetic": [1, 2.5, null], "synthetic": ['
    ),
    "a value of ext": lambda text: text.replace(
        '"anything":', '"anything": [1.5, null, true], "anything":'
    ),
    "ext": lambda text: text.replace('"other":', '"other": null, "other":'),
}


@pytest.mark.parametrize("place", TWICE)
def test_a_member_name_twice_in_any_object_is_refused(place):
    text = json.dumps(full())
    twice = TWICE[place](text)
    assert twice != text
    spec.validate(json.loads(twice))
    message = invalid(NOT_ONE_TEXT, twice.encode())
    assert "a JSON object repeats a member name" in message


@pytest.mark.parametrize("place", FREE_PLACES)
def test_a_member_name_twice_deep_inside_a_free_place_is_refused(place):
    document = changed(full(), ("feedback", "attempts", 0, "profile"), {})
    literal = b'[0, [{"a": {"b": 1, "c": 2, "b": 3}}]]'
    invalid(NOT_ONE_TEXT, spelt(document, FREE_PLACES[place], literal))


@pytest.mark.parametrize(
    ("path", "value", "place"),
    [
        (("id", "candidate"), 2, "id.candidate: must be at most id.candidates (1)"),
        (("id", "relation"), "alone", "id.relation: "),
        (("hw_profile", "key"), "synthetic_accel-0000000000000000", "hw_profile.key: "),
        (("task", "contract", "operands"), [], "task.contract.operands: "),
        (("guidance", "unknown"), 1, "guidance: unknown member 'unknown'"),
        (
            ("feedback", "attempts"),
            [entry(profile=[])],
            "feedback.attempts[0].profile: ",
        ),
        (("ext",), {}, "ext: "),
        (("repair",), {"failures": []}, "repair: "),
    ],
)
def test_a_document_the_validator_refuses_is_invalid_with_its_message(
    path, value, place
):
    document = changed(minimal(), path, value)
    with pytest.raises(spec.InvalidSpecError) as expected:
        spec.validate(document)
    with pytest.raises(InvalidSpecFileError) as caught:
        parse(raw(document))
    assert str(caught.value) == str(expected.value)
    assert str(caught.value).startswith(place)
    assert isinstance(caught.value.__cause__, spec.InvalidSpecError)
    assert not isinstance(caught.value, spec.InvalidSpecError)


@pytest.mark.parametrize("version", [1, 0, 3, MAX])
def test_another_version_is_set_apart_from_an_invalid_content(version):
    other_version(raw(changed(minimal(), ("schema_version",), version)), version)
    other_version(json.dumps({"schema_version": version}).encode(), version)


def test_a_version_one_content_is_set_apart_and_not_read():
    document = version_one()
    as_version_two = raw(changed(document, ("schema_version",), 2))
    invalid("task.objective: unknown member", as_version_two)
    other_version(raw(document), 1)
    other_version(written(document), 1)
    other_version(b'{"schema_version": 1}', 1)
    with pytest.raises(spec.InvalidSpecError, match="^schema_version: must be the"):
        spec.validate(document)


@pytest.mark.parametrize(
    "rest",
    [
        '"id": 7',
        '"unknown_member": [1.5, null]',
        '"id": {"round": -0}, "ext": {}',
        '"hw_profile": {"record": {"schema_version": -0}}',
        '"task": "1e999", "x": 1e999',
    ],
)
def test_another_version_is_reported_whatever_else_the_content_holds(rest):
    other_version(f'{{{rest}, "schema_version": 1}}'.encode(), 1)
    other_version(f'{{"schema_version": 1, {rest}}}'.encode(), 1)
    other_version(f'{{"schema_version": 3, {rest}}}'.encode(), 3)


@pytest.mark.parametrize(
    "content",
    [
        b'\xef\xbb\xbf{"schema_version": 1}',
        b'{"schema_version": 1, "schema_version": 1}',
        b'{"schema_version": 1, "x": {"a": 1, "a": 2}}',
        b'{"schema_version": 1, "x": NaN}',
        b'{"schema_version": 1} {}',
        b'{"schema_version": 1, "x": "\xff"}',
        b'[{"schema_version": 1}]',
        b'{"schema_version": 1, "x": ' + TOO_LONG_TEXT.encode() + b"}",
    ],
)
def test_the_rules_for_the_whole_text_come_before_the_version(content):
    invalid("content: ", content)


@pytest.mark.parametrize(
    "literal",
    [
        '"1"',
        '"2"',
        "1.0",
        "2.0",
        "1e0",
        "true",
        "false",
        "null",
        "-1",
        "-2",
        "[2]",
        "{}",
    ]
    + [str(MAX + 1), "2e0", "-0.0"],
)
def test_a_schema_version_that_is_no_integer_is_invalid(literal):
    content = spelt(minimal(), ("schema_version",), literal.encode())
    invalid("schema_version: must be the integer 2, got", content)
    invalid("", f'{{"schema_version": {literal}}}'.encode())


def test_an_absent_schema_version_is_invalid():
    document = minimal()
    del document["schema_version"]
    invalid("schema_version: required member is missing", raw(document))
    invalid("schema_version: required member is missing", b"{}")


def test_the_classes_tell_invalid_from_another_version():
    assert issubclass(InvalidSpecFileError, ValueError)
    assert not issubclass(InvalidSpecFileError, spec.InvalidSpecError)
    assert not issubclass(UnsupportedVersionError, ValueError)
    assert not issubclass(UnsupportedVersionError, InvalidSpecFileError)
    assert UnsupportedVersionError.__mro__[1] is Exception
    for module in (instance, run_state):
        assert UnsupportedVersionError is not module.UnsupportedVersionError


def test_the_order_of_the_checks():
    bad_bytes = b"\xef\xbb\xbf\xff"
    invalid("content: starts with a byte order mark", bad_bytes)
    twice_and_no_object = b'[{"a": 1, "a": 2}]'
    invalid(NOT_ONE_TEXT, twice_and_no_object)
    invalid("content: must be a JSON object", b"[2]")
    refused = changed(with_zeros(), ("id", "candidate"), 2)
    other_version(
        spelt(changed(refused, ("schema_version",), 1), ("id", "round"), b"-0"), 1
    )
    invalid("id.candidate: ", spelt(refused, ("id", "round"), b"-0"))
    invalid("id.round: ", spelt(with_zeros(), ("id", "round"), b"-0"))


def test_the_first_minus_zero_in_the_order_of_the_text_is_named():
    content = spelt(with_zeros(), ("feedback", "base", "round"), b"-0")
    content = content.replace(b'"round": 0', b'"round": -0')
    message = invalid("id.round: ", content)
    assert "feedback" not in message


@pytest.mark.parametrize(
    "run_id",
    [
        "Synthetic",
        "synthetic run",
        "r" * 65,
        "-synthetic",
        "_run",
        "a/b",
        "..",
        "run.1",
    ],
)
def test_a_valid_content_without_a_path_stays_valid(run_id):
    document = changed(full(), ("id", "run_id"), run_id)
    spec.validate(document)
    assert parse(raw(document)) == document
    with pytest.raises(layout.InvalidPathValueError, match="run_id: must be a str"):
        final_name("synthetic-root", document)
    with pytest.raises(layout.InvalidPathValueError):
        final_name("synthetic-root", parse(raw(document)))


@pytest.mark.parametrize(
    ("round", "candidate", "attempt"),
    [
        (0, 1, 1),
        (1, 1, 1),
        (4, 2, 3),
        (9999, 99, 99),
        (10000, 100, 100),
        (MAX, MAX, MAX),
    ],
)
@pytest.mark.parametrize("run_id", ["synthetic-run-1", "0", "r" * 64, "a_b-c"])
def test_the_final_name_is_the_path_of_the_tuple(run_id, round, candidate, attempt):
    document = minimal()
    document["id"].update(
        run_id=run_id,
        round=round,
        candidate=candidate,
        attempt=attempt,
        candidates=candidate,
        relation="single" if candidate == 1 else "different_techniques",
    )
    if attempt > 1:
        failure = {"attempt": attempt - 1, "stage": "sim", "report": "synthetic"}
        document["repair"] = {"failures": [failure]}
    root = Path("synthetic-root")
    expected = layout.attempt_artefact(
        root, run_id, round, candidate, attempt, "spec.json"
    )
    assert final_name(root, document) == expected
    assert final_name(root, parse(raw(document))) == expected
    assert expected.name == "spec.json"
    assert expected.parts[:3] == ("synthetic-root", "runs", run_id)


def test_the_final_name_in_digits():
    document = full()
    relative = (
        "runs/synthetic-run-1/rounds/0004/coder/candidates/02/attempts/01/spec.json"
    )
    assert final_name("synthetic-root", document) == Path("synthetic-root") / relative
    assert final_name(Path("."), document) == Path(relative)
    assert final_name("", document) == Path(relative)


@pytest.mark.parametrize(
    "data_root",
    ["synthetic-root", Path("synthetic-root"), "a/b/../c", Path("relative") / "root"],
)
def test_the_data_root_is_used_as_given(data_root):
    result = final_name(data_root, full())
    assert type(result) is type(Path())
    assert not result.is_absolute()
    assert result.parts[: len(Path(data_root).parts)] == Path(data_root).parts
    assert result.relative_to(Path(data_root)).parts[0] == "runs"


def test_an_absolute_data_root_that_does_not_exist_gives_a_path(tmp_path):
    root = tmp_path / "missing" / "root"
    result = final_name(root, minimal())
    assert result.is_relative_to(root)
    assert not root.exists()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("data_root", [None, 7, b"synthetic-root", ["a"]])
def test_a_data_root_that_is_no_path_is_a_type_error(data_root):
    with pytest.raises(TypeError):
        final_name(data_root, minimal())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("id", "round"), True),
        (("id", "round"), "3"),
        (("id", "round"), 3.0),
        (("id", "round"), -1),
        (("id", "candidate"), 0),
        (("id", "candidate"), "01"),
        (("id", "attempt"), None),
        (("id", "attempt"), 2),
        (("id", "run_id"), 7),
        (("id", "run_id"), ""),
        (("id", "run_id"), "synthetic\nrun"),
        (
            ("id",),
            {"run_id": "synthetic-run-1", "round": 1, "candidate": 1, "attempt": 1},
        ),
        (("schema_version",), 1),
        (("schema_version",), 3),
        (("schema_version",), True),
        (("task", "objective_typo"), None),
    ],
)
def test_a_document_that_is_no_valid_spec_yields_no_path(path, value):
    document = changed(minimal(), path, value)
    with pytest.raises(spec.InvalidSpecError) as caught:
        final_name("synthetic-root", document)
    assert not isinstance(caught.value, InvalidSpecFileError)


def test_a_version_one_document_yields_no_path():
    for document in (version_one(), changed(minimal(), ("schema_version",), 1)):
        with pytest.raises(spec.InvalidSpecError) as caught:
            final_name("synthetic-root", document)
        assert str(caught.value).startswith("schema_version: must be the integer 2")
        assert not isinstance(caught.value, InvalidSpecFileError)


@pytest.mark.parametrize("document", [None, [], "text", 7, b"{}", {}, {"id": {}}])
def test_a_value_that_is_no_spec_yields_no_path(document):
    with pytest.raises(spec.InvalidSpecError):
        final_name("synthetic-root", document)
    with pytest.raises(spec.InvalidSpecError):
        final_name("synthetic-root", raw(minimal()))


def test_nothing_is_modified_or_kept():
    content = raw(full())
    first, second = parse(content), parse(content)
    assert content == raw(full())
    assert first == second and first is not second
    assert first["id"] is not second["id"]
    first["id"]["round"] = 77
    first["ext"].clear()
    assert second == full() == parse(content)
    document = full()
    before = copy.deepcopy(document)
    assert final_name("synthetic-root", document) == final_name(
        "synthetic-root", before
    )
    assert document == before


def test_parse_and_final_name_open_no_file(monkeypatch, tmp_path):
    def refuse(*arguments, **named):
        raise AssertionError("a file was opened")

    content = raw(full())
    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(io, "open", refuse)
    monkeypatch.setattr(os, "open", refuse)
    for name in ("mkdir", "stat", "lstat", "listdir", "scandir", "link", "replace"):
        monkeypatch.setattr(os, name, refuse)
    document = parse(content)
    final_name(tmp_path / "missing", document)
    with pytest.raises(InvalidSpecFileError):
        parse(b"")
    with pytest.raises(UnsupportedVersionError):
        parse(b'{"schema_version": 1}')
    with pytest.raises(layout.InvalidPathValueError):
        final_name(tmp_path, changed(document, ("id", "run_id"), "No Path"))


def test_the_module_imports_only_what_it_needs():
    tree = ast.parse(inspect.getsource(spec_file))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported |= {f"{node.module}.{alias.name}" for alias in node.names}
    assert imported == {
        "codecs",
        "json",
        "re",
        "pathlib.Path",
        "hilclaw.keys",
        "hilclaw.layout",
        "hilclaw.once_write",
        "hilclaw.spec",
    }


def test_the_public_names_and_the_call_forms():
    public = {
        name
        for name, value in vars(spec_file).items()
        if getattr(value, "__module__", None) == spec_file.__name__
        and not name.startswith("_")
    }
    assert public == {
        "InvalidSpecFileError",
        "UnsupportedVersionError",
        "WrittenFormError",
        "NameTakenError",
        "parse",
        "final_name",
        "write",
    }
    assert str(inspect.signature(parse)) == "(content)"
    assert str(inspect.signature(final_name)) == "(data_root, document)"
    assert str(inspect.signature(write)) == "(data_root, content)"
    for function in (parse, final_name, write):
        parameters = inspect.signature(function).parameters.values()
        assert all(item.default is inspect.Parameter.empty for item in parameters)


# --- the write (ADR-0029 decisions 4 to 7) ---

TEMPORARY = re.compile(r"spec\.json\.[a-z0-9-]{1,64}\.tmp")
STEPS = ("creation", "write", "flush", "link")
RUN = "runs/synthetic-run-1"
ROUND = f"{RUN}/rounds/0001"
CANDIDATE = f"{ROUND}/coder/candidates/01"
FIRST = f"{CANDIDATE}/attempts/01"
SECOND = f"{CANDIDATE}/attempts/02"
FILE = f"{FIRST}/spec.json"
LEFTOVER = f"{SECOND}/spec.json.4242-0123456789abcdef.tmp"
TAKEN_REPORT = f"{FILE}: the name is taken; the content was not written"


def written(document):
    return json.dumps(document, indent=2).encode() + b"\n"


def wide():
    made = minimal()
    made["id"].update(round=12345, candidate=123, candidates=200, attempt=100)
    made["id"].update(relation="same_technique", variant="synthetic variant")
    failure = {"attempt": 99, "stage": "compile", "report": "synthetic report"}
    made["repair"] = {"failures": [failure]}
    return made


def unusual():
    prototype = ("task", "contract", "prototype")
    document = changed(full(), prototype, "synthetic\r\nprototype")
    turned = dict(reversed(document.items()))
    marked = changed(turned, ("ext", "other"), MARK)
    body = json.dumps(marked, separators=(" ,", "\t: "))
    free = '[-0,  1.50, 1E+2 ,{"b" :null}]'
    return ("\n\t " + body.replace(f'"{MARK}"', free) + "\n\n").encode()


def no_path(run_id="No Path", **members):
    made = changed(minimal(), ("id", "run_id"), run_id)
    for name, value in members.items():
        made = changed(made, name.split("."), value)
    return made


MINIMAL = written(minimal())
FULL = written(full())
REPAIR = written(repair())
OTHER = written(changed(minimal(), ("task", "contract", "prototype"), "another"))
ELSEWHERE = written(changed(minimal(), ("id", "run_id"), "synthetic-run-2"))
UNUSUAL = unusual()
CONTENTS = {
    "required members only": MINIMAL,
    "every optional part": FULL,
    "repair": REPAIR,
    "round 0": written(with_zeros()),
    "wide numbers": written(wide()),
}
PREVIOUS = {"free": None, "taken": OTHER}
TAKEN = {
    "other bytes": OTHER,
    "equal bytes": MINIMAL,
    "invalid": MINIMAL[:20],
    "empty": b"",
    "directory": None,
    "link to a file": None,
    "dangling link": None,
}
PRESENT = {
    "nothing": {},
    "runs": {"runs": None},
    "run directory": {RUN: None},
    "instance and state": {
        f"{RUN}/instance.json": b"an instance",
        f"{RUN}/STATE.json": b"a state",
    },
    "round directory": {ROUND: None},
    "decision log": {f"{ROUND}/decision/decision.md": b"a decision"},
    "attempt 1": {FILE: MINIMAL, f"{FIRST}/output/kernel.c": b"a source"},
    "output": {f"{SECOND}/output/kernel.c": b"a source"},
    "partial leftover": {LEFTOVER: REPAIR[:9]},
    "whole leftover": {LEFTOVER: REPAIR},
}
REFUSED = {
    "str": (MINIMAL.decode(), TypeError),
    "bytearray": (bytearray(MINIMAL), TypeError),
    "dict": (minimal(), TypeError),
    "None": (None, TypeError),
    "empty": (b"", InvalidSpecFileError),
    "partial": (MINIMAL[:20], InvalidSpecFileError),
    "byte order mark": (codecs.BOM_UTF8 + MINIMAL, InvalidSpecFileError),
    "member name twice": (
        b'{"schema_version": 1, ' + raw(minimal())[1:] + b"\n",
        InvalidSpecFileError,
    ),
    "-0 at an integer place": (
        spelt(minimal(), ("id", "round"), b"-0") + b"\n",
        InvalidSpecFileError,
    ),
    "refused by validate": (
        written(changed(minimal(), ("id", "attempt"), 0)),
        InvalidSpecFileError,
    ),
    "version 0": (
        written(changed(minimal(), ("schema_version",), 0)),
        UnsupportedVersionError,
    ),
    "version 1": (
        written(changed(minimal(), ("schema_version",), 1)),
        UnsupportedVersionError,
    ),
    "version 1, the whole document": (written(version_one()), UnsupportedVersionError),
    "version 1, no other member": (b'{"schema_version": 1}\n', UnsupportedVersionError),
    "version 3": (
        written(changed(minimal(), ("schema_version",), 3)),
        UnsupportedVersionError,
    ),
    "version 2**53 - 1": (
        written(changed(minimal(), ("schema_version",), MAX)),
        UnsupportedVersionError,
    ),
    "a number in the objective": (
        written(changed(minimal(), ("task", "objective", "constraints"), [1.5])),
        InvalidSpecFileError,
    ),
    "no path: upper case": (
        written(no_path("Synthetic")),
        layout.InvalidPathValueError,
    ),
    "no path: space": (written(no_path("synthetic run")), layout.InvalidPathValueError),
    "no path: 65 characters": (
        written(no_path("s" * 65)),
        layout.InvalidPathValueError,
    ),
    "no path: leading hyphen": (
        written(no_path("-synthetic")),
        layout.InvalidPathValueError,
    ),
    "no final line feed": (MINIMAL[:-1], WrittenFormError),
    "CRLF line ends": (MINIMAL.replace(b"\n", b"\r\n"), WrittenFormError),
    "one carriage return": (b"\r" + MINIMAL, WrittenFormError),
}


class Stop(BaseException):
    pass


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


@pytest.fixture(autouse=True)
def no_replacing_step(monkeypatch):
    def refuse(*arguments, **named):
        pytest.fail("a replacing step was called")

    monkeypatch.setattr(os, "replace", refuse)
    monkeypatch.setattr(os, "rename", refuse)


def rel(content):
    return final_name(Path("."), parse(content)).as_posix()


def between(file):
    return {parent.as_posix(): None for parent in Path(file).parents if parent.name}


def place(root, content, relative=FILE):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def fill(root, present):
    for name, content in present.items():
        if content is None:
            (root / name).mkdir(parents=True)
        else:
            place(root, content, name)
    return snapshot(root)


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): (
            path.read_bytes() if path.is_file() else None
        )
        for path in directory.rglob("*")
    }


def temporaries(directory):
    return [
        name for name in snapshot(directory) if TEMPORARY.fullmatch(Path(name).name)
    ]


def held(root):
    path = root / FILE
    return path.read_bytes() if os.path.lexists(path) else None


def link(path, target):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symbolic links cannot be created here")


def kind(path):
    if path.is_symlink():
        return ("link", os.readlink(path))
    return ("directory" if path.is_dir() else "file", None)


def take(root, how):
    path = root / FILE
    target = root.parent / "target.json"
    if how == "directory":
        path.mkdir(parents=True)
    elif how == "link to a file":
        target.write_bytes(OTHER)
        link(path, target)
    elif how == "dangling link":
        link(path, target)
    else:
        place(root, TAKEN[how])


def spy(monkeypatch):
    opened = []
    real, low = open, os.open

    def high(file, mode="r", *arguments, **named):
        opened.append((Path(file), mode))
        return real(file, mode, *arguments, **named)

    def descriptor(file, flags, *arguments, **named):
        opened.append((Path(file), flags))
        return low(file, flags, *arguments, **named)

    monkeypatch.setattr("builtins.open", high)
    monkeypatch.setattr(io, "open", high)
    monkeypatch.setattr(os, "open", descriptor)
    return opened


def no_listing(monkeypatch):
    def refuse(*arguments, **named):
        raise AssertionError("a directory was listed")

    monkeypatch.setattr(os, "listdir", refuse)
    monkeypatch.setattr(os, "scandir", refuse)


@pytest.fixture
def watch(monkeypatch, root):
    seen = []
    flush, give = os.fsync, os.link

    def fsync(descriptor):
        files = {
            name: content
            for name, content in snapshot(root).items()
            if content is not None
        }
        status = os.fstat(descriptor)
        same = [
            name for name in files if os.path.samestat(status, os.stat(root / name))
        ]
        seen.append({"step": "flush", "files": files, "flushed": same})
        seen[-1].update(descriptor=descriptor)
        return flush(descriptor)

    def linking(source, target):
        with pytest.raises(OSError):
            os.fstat(seen[-1]["descriptor"])
        content = Path(source).read_bytes()
        taken = os.path.lexists(target)
        seen.append({"step": "link", "taken": taken, "content": content})
        seen[-1].update(source=Path(source), target=Path(target))
        return give(source, target)

    monkeypatch.setattr(os, "fsync", fsync)
    monkeypatch.setattr(os, "link", linking)
    return seen


class Partial:
    def __init__(self, file, error, observe):
        self.file = file
        self.error = error
        self.observe = observe

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return self.file.__exit__(*exception)

    def write(self, content):
        self.file.write(content[:7])
        self.observe()
        raise self.error


def break_step(monkeypatch, step, error, observe=lambda: None):
    real = open

    def refuse(*arguments, **named):
        observe()
        raise error

    def creation(file, mode="r", *arguments, **named):
        if "x" not in mode:
            return real(file, mode, *arguments, **named)
        if step == "creation":
            raise error
        return Partial(real(file, mode, *arguments, **named), error, observe)

    if step in ("creation", "write"):
        monkeypatch.setattr("builtins.open", creation)
    else:
        name = {"flush": "fsync", "link": "link", "unlink": "unlink"}[step]
        monkeypatch.setattr(os, name, refuse)


@pytest.mark.parametrize("as_type", [Path, str])
@pytest.mark.parametrize("content", CONTENTS.values(), ids=CONTENTS)
def test_the_bytes_given_are_the_bytes_under_the_final_name(root, content, as_type):
    assert write(as_type(root), content) is None

    file = rel(content)
    assert root / file == final_name(root, parse(content))
    assert snapshot(root.parent) == {"data": None} | {
        f"data/{name}": held for name, held in (between(file) | {file: content}).items()
    }
    assert parse((root / file).read_bytes()) == parse(content)


def test_the_directories_created_are_those_between_the_root_and_the_name(root):
    write(root, MINIMAL)
    write(root, CONTENTS["round 0"])
    write(root, CONTENTS["wide numbers"])

    directories = sorted(name for name, held in snapshot(root).items() if held is None)
    lone = [
        "runs",
        RUN,
        f"{RUN}/rounds",
        ROUND,
        f"{ROUND}/coder",
        f"{ROUND}/coder/candidates",
        CANDIDATE,
        f"{CANDIDATE}/attempts",
        FIRST,
    ]
    assert set(between(FILE)) == set(lone)
    zero = f"{RUN}/rounds/0000/coder/candidates/01/attempts/01/spec.json"
    high = f"{RUN}/rounds/12345/coder/candidates/123/attempts/100/spec.json"
    assert directories == sorted(set(lone) | set(between(zero)) | set(between(high)))
    assert not [name for name in snapshot(root) if "output" in name]
    assert snapshot(root)[zero] == CONTENTS["round 0"]
    assert snapshot(root)[high] == CONTENTS["wide numbers"]


def test_data_root_as_a_relative_path(root, monkeypatch):
    monkeypatch.chdir(root.parent)

    write("data", MINIMAL)
    write(Path("data"), FULL)

    assert snapshot(root)[FILE] == MINIMAL
    assert snapshot(root)[rel(FULL)] == FULL
    assert temporaries(root) == []


@pytest.mark.parametrize("present", PRESENT.values(), ids=PRESENT)
def test_the_write_is_the_same_whatever_is_there_before(root, monkeypatch, present):
    before = fill(root, present)
    opened = spy(monkeypatch)
    no_listing(monkeypatch)

    write(root, REPAIR)
    monkeypatch.undo()

    file = f"{SECOND}/spec.json"
    assert snapshot(root) == before | between(file) | {file: REPAIR}
    ((path, mode),) = opened
    assert (path.parent, mode) == (root / SECOND, "xb")
    assert TEMPORARY.fullmatch(path.name)
    assert temporaries(root) == [name for name in present if name == LEFTOVER]


def test_a_second_tuple_and_a_second_run_are_untouched(root):
    write(root, ELSEWHERE)
    write(root, FULL)
    place(root, b"a state", "runs/synthetic-run-2/STATE.json")
    others = snapshot(root)

    write(root, MINIMAL)

    after = snapshot(root)
    assert {name: held for name, held in after.items() if name in others} == others
    assert after == others | between(FILE) | {FILE: MINIMAL}
    assert after[rel(ELSEWHERE)] == ELSEWHERE


def test_the_temporary_file_is_whole_and_the_final_name_absent_until_the_link(
    root, watch
):
    write(root, FULL)

    flush, give = watch
    source = give["source"]
    assert (flush["step"], give["step"]) == ("flush", "link")
    assert give["taken"] is False
    assert give["target"] == final_name(root, parse(FULL))
    assert source.parent == give["target"].parent
    assert TEMPORARY.fullmatch(source.name)
    assert source.name not in layout.ATTEMPT_ARTEFACTS
    assert source.name.startswith(f"spec.json.{os.getpid()}-")
    assert give["content"] == FULL
    assert flush["files"] == {source.relative_to(root).as_posix(): FULL}
    assert flush["flushed"] == list(flush["files"])
    assert temporaries(root) == []
    assert snapshot(root)[rel(FULL)] == FULL


def test_every_write_uses_another_temporary_name(root, watch):
    write(root, MINIMAL)
    write(root, REPAIR)
    with pytest.raises(NameTakenError):
        write(root, MINIMAL)

    sources = [entry["source"].name for entry in watch if entry["step"] == "link"]
    assert len(set(sources)) == 3
    assert all(TEMPORARY.fullmatch(name) for name in sources)


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS[1:])
def test_a_stop_before_the_name_is_given_leaves_the_final_name_as_it_was(
    root, monkeypatch, step, previous
):
    before = fill(root, {} if previous is None else {FILE: previous})
    seen = []
    break_step(monkeypatch, step, Stop(), lambda: seen.append(held(root)))

    with pytest.raises(Stop):
        write(root, MINIMAL)
    monkeypatch.undo()

    assert seen == [previous]
    assert held(root) == previous
    assert snapshot(root) == before | between(FILE)


def test_a_stop_after_the_name_is_given_leaves_the_whole_content(root, monkeypatch):
    seen = []
    break_step(monkeypatch, "unlink", Stop(), lambda: seen.append(held(root)))

    with pytest.raises(Stop):
        write(root, MINIMAL)
    monkeypatch.undo()

    assert seen == [MINIMAL]
    assert held(root) == MINIMAL
    (leftover,) = temporaries(root)
    assert os.path.samefile(root / leftover, root / FILE)


def test_a_stop_at_the_removal_leaves_a_taken_name_as_it_was(root, monkeypatch):
    place(root, OTHER)
    seen = []
    break_step(monkeypatch, "unlink", Stop(), lambda: seen.append(held(root)))

    with pytest.raises(Stop):
        write(root, MINIMAL)
    monkeypatch.undo()

    assert seen == [OTHER]
    assert held(root) == OTHER
    (leftover,) = temporaries(root)
    assert snapshot(root)[leftover] == MINIMAL


@pytest.mark.parametrize("how", TAKEN)
def test_a_taken_name_is_reported_and_what_is_there_is_unchanged(
    root, monkeypatch, how
):
    take(root, how)
    before = (snapshot(root.parent), kind(root / FILE))
    opened = spy(monkeypatch)
    no_listing(monkeypatch)

    with pytest.raises(NameTakenError) as caught:
        write(root, MINIMAL)
    monkeypatch.undo()

    assert str(caught.value) == TAKEN_REPORT
    assert not isinstance(caught.value, OSError)
    assert (snapshot(root.parent), kind(root / FILE)) == before
    assert temporaries(root) == []
    ((path, mode),) = opened
    assert TEMPORARY.fullmatch(path.name) and mode == "xb"


def test_equal_bytes_are_reported_as_other_bytes(root):
    write(root, MINIMAL)
    reports = []
    for content in (MINIMAL, OTHER):
        with pytest.raises(NameTakenError) as caught:
            write(root, content)
        reports.append((type(caught.value), str(caught.value)))

    assert reports[0] == reports[1]
    assert snapshot(root) == between(FILE) | {FILE: MINIMAL}


def test_a_name_freed_by_other_means_is_given_again(root):
    write(root, MINIMAL)
    with pytest.raises(NameTakenError):
        write(root, OTHER)
    (root / FILE).unlink()

    write(root, OTHER)

    assert snapshot(root) == between(FILE) | {FILE: OTHER}


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("content, error", REFUSED.values(), ids=REFUSED)
def test_a_refused_content_creates_and_changes_nothing(root, content, error, previous):
    before = fill(root, {} if previous is None else {FILE: previous})

    with pytest.raises(error) as caught:
        write(root, content)

    assert type(caught.value) is error
    assert snapshot(root) == before


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_missing_data_root_is_not_created(tmp_path, as_type):
    with pytest.raises(FileNotFoundError, match="data root"):
        write(as_type(tmp_path / "absent"), MINIMAL)

    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_file_in_the_place_of_the_data_root(tmp_path, as_type):
    place(tmp_path, b"a file", "data")

    with pytest.raises(NotADirectoryError, match="data root"):
        write(as_type(tmp_path / "data"), MINIMAL)

    assert snapshot(tmp_path) == {"data": b"a file"}


@pytest.mark.parametrize("data_root", [None, 7, b"data"])
def test_a_data_root_that_is_no_path(data_root):
    with pytest.raises(TypeError):
        write(data_root, MINIMAL)


@pytest.mark.parametrize(
    "name", ["runs", RUN, f"{RUN}/rounds", f"{CANDIDATE}/attempts", FIRST]
)
def test_a_file_in_the_place_of_a_directory_above_the_final_name(root, name):
    place(root, b"a file", name)
    before = snapshot(root)

    with pytest.raises(OSError):
        write(root, MINIMAL)

    assert snapshot(root) == before


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS)
def test_a_failed_step_leaves_the_final_name_and_no_temporary_file(
    root, monkeypatch, step, previous
):
    before = fill(root, {} if previous is None else {FILE: previous})
    error = OSError(f"{step} refused: no hard links here")
    break_step(monkeypatch, step, error)

    with pytest.raises(OSError) as caught:
        write(root, MINIMAL)
    monkeypatch.undo()

    assert caught.value is error
    assert snapshot(root) == before | between(FILE)


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
@pytest.mark.parametrize("step", STEPS[1:])
def test_an_interrupt_removes_the_temporary_file_too(root, monkeypatch, step, previous):
    before = fill(root, {} if previous is None else {FILE: previous})
    break_step(monkeypatch, step, KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        write(root, MINIMAL)
    monkeypatch.undo()

    assert snapshot(root) == before | between(FILE)


@pytest.mark.parametrize("previous", PREVIOUS.values(), ids=PREVIOUS)
def test_a_temporary_name_in_use_is_an_error_and_that_file_stays(
    root, monkeypatch, previous
):
    if previous is not None:
        place(root, previous)
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * 2 * size)
    name = f"{FIRST}/spec.json.{os.getpid()}-{'0' * 16}.tmp"
    place(root, b"of another writer", name)
    before = snapshot(root)

    with pytest.raises(FileExistsError) as caught:
        write(root, MINIMAL)

    assert not isinstance(caught.value, NameTakenError)
    assert snapshot(root) == before


def test_a_removal_that_fails_does_not_hide_the_failure_of_the_step(root, monkeypatch):
    error = OSError("link refused")
    break_step(monkeypatch, "link", error)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    with pytest.raises(OSError) as caught:
        write(root, MINIMAL)
    monkeypatch.undo()

    assert caught.value is error
    assert held(root) is None
    (leftover,) = temporaries(root)
    assert snapshot(root)[leftover] == MINIMAL


def test_a_removal_that_fails_does_not_hide_a_taken_name(root, monkeypatch):
    place(root, OTHER)
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    with pytest.raises(NameTakenError):
        write(root, MINIMAL)
    monkeypatch.undo()

    assert held(root) == OTHER
    assert len(temporaries(root)) == 1


def test_a_removal_that_fails_after_the_name_is_given_is_no_failure(root, monkeypatch):
    break_step(monkeypatch, "unlink", OSError("removal refused"))

    assert write(root, MINIMAL) is None
    monkeypatch.undo()

    assert held(root) == MINIMAL
    (leftover,) = temporaries(root)
    assert os.path.samefile(root / leftover, root / FILE)


def test_a_temporary_file_removed_by_another_fails_the_link_and_gives_no_name(
    root, monkeypatch
):
    give = os.link

    def removed_first(source, target):
        Path(source).unlink()
        return give(source, target)

    monkeypatch.setattr(os, "link", removed_first)

    with pytest.raises(FileNotFoundError):
        write(root, MINIMAL)

    assert snapshot(root) == between(FILE)


def test_the_order_of_the_checks_of_write(tmp_path):
    absent = tmp_path / "absent"
    file = place(tmp_path, b"a file", "file")
    cases = [
        (absent, None, TypeError),
        (absent, MINIMAL[:20], InvalidSpecFileError),
        (absent, raw(no_path(schema_version=1)), UnsupportedVersionError),
        (absent, raw(no_path(**{"id.attempt": 0})) + b"\r", InvalidSpecFileError),
        (absent, raw(no_path()) + b"\r", layout.InvalidPathValueError),
        (None, MINIMAL[:-1], TypeError),
        (absent, MINIMAL[:-1], WrittenFormError),
        (file, b"\r" + MINIMAL, WrittenFormError),
        (absent, MINIMAL, FileNotFoundError),
        (file, MINIMAL, NotADirectoryError),
    ]

    for data_root, content, error in cases:
        with pytest.raises(error) as caught:
            write(data_root, content)
        assert type(caught.value) is error

    assert snapshot(tmp_path) == {"file": b"a file"}


def test_white_space_member_order_and_free_values_are_written_as_given(root):
    write(root, UNUSUAL)

    file = rel(UNUSUAL)
    assert snapshot(root)[file] == UNUSUAL
    document = parse((root / file).read_bytes())
    assert document == parse(UNUSUAL)
    assert list(document) == list(reversed(list(full())))
    assert document["task"]["contract"]["prototype"] == "synthetic\r\nprototype"
    assert b"\\r" in UNUSUAL and b"\r" not in UNUSUAL
    assert b'[-0,  1.50, 1E+2 ,{"b" :null}]' in UNUSUAL


def test_the_classes_of_the_write():
    assert issubclass(WrittenFormError, ValueError)
    assert not issubclass(WrittenFormError, InvalidSpecFileError)
    assert not issubclass(NameTakenError, (OSError, ValueError))
    assert WrittenFormError is not instance_file.WrittenFormError
    assert NameTakenError is not instance_file.NameTakenError


def test_the_module_holds_no_value_of_a_content():
    own = [value for name, value in vars(spec_file).items() if not name.startswith("_")]
    assert all(
        inspect.ismodule(value) or inspect.isclass(value) or inspect.isfunction(value)
        for value in own
    )
