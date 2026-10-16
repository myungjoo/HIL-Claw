import builtins
import copy
import io
import json
import os
import re
import secrets
from pathlib import Path

import pytest

from hilclaw import cases, cases_file, keys, layout
from hilclaw.cases_file import (
    InvalidCaseFileError,
    NameTakenError,
    UnsupportedVersionError,
    WrittenFormError,
    final_name,
    parse,
    write,
)

MAX = keys.MAX_INTEGER
MARK = "@@synthetic-mark@@"
NOT_ONE_TEXT = "content: cannot be read as one JSON text"
RUN_ID = "20261009t012331z-9f3a6c1e0b7d4a52"
HW = "cpu_standin-b0d8610d8f470856"
OP = "gemm-c43e96fb16cc3f35"
KEY_DIR = f"db/{HW}/{OP}"
EXAMPLE_FILE = f"{KEY_DIR}/case-{RUN_ID}-0001.json"

EXAMPLE = b"""{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "hypothesis_record": {
    "schema_version": 1, "run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1, "candidates": 1,
    "hypotheses": [
      {"id": "h1", "statement": "NOT-DECIDED-HERE",
       "basis": [{"kind": "attempt", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "text": "NOT-DECIDED-HERE"}],
       "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
       "origin": "system", "tested_by": [1]}
    ]
  },
  "verdict_record": {
    "schema_version": 1, "run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1,
    "verdicts": [
      {"hypothesis": "h1", "verdict": "supported", "cause": "NOT-DECIDED-HERE",
       "evidence": [
         {"kind": "check", "ref": {"round": 1, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
         {"kind": "check", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
         {"kind": "comparison", "metric": "latency_minimisation", "point": "board",
          "measured": {"round": 1, "candidate": 1, "attempt": 1},
          "against": {"round": 0, "candidate": 1, "attempt": 1}, "difference": "lower"}]}
    ]
  }
}
"""


def _ref(round, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


HYPOTHESIS_RECORD = {
    "schema_version": 1,
    "run_id": RUN_ID,
    "round": 1,
    "candidates": 1,
    "hypotheses": [
        {
            "id": "h1",
            "statement": "NOT-DECIDED-HERE",
            "basis": [{"kind": "attempt", "ref": _ref(0), "text": "NOT-DECIDED-HERE"}],
            "expected": [{"metric": "latency_minimisation", "direction": "lower"}],
            "origin": "system",
            "tested_by": [1],
        }
    ],
}

VERDICT_RECORD = {
    "schema_version": 1,
    "run_id": RUN_ID,
    "round": 1,
    "verdicts": [
        {
            "hypothesis": "h1",
            "verdict": "supported",
            "cause": "NOT-DECIDED-HERE",
            "evidence": [
                {"kind": "check", "ref": _ref(1), "point": "board", "outcome": "pass"},
                {"kind": "check", "ref": _ref(0), "point": "board", "outcome": "pass"},
                {
                    "kind": "comparison",
                    "metric": "latency_minimisation",
                    "point": "board",
                    "measured": _ref(1),
                    "against": _ref(0),
                    "difference": "lower",
                },
            ],
        }
    ],
}

EXAMPLE_DOCUMENT = {
    "schema_version": 1,
    "run_id": RUN_ID,
    "round": 1,
    "hypothesis_record": HYPOTHESIS_RECORD,
    "verdict_record": VERDICT_RECORD,
}


def example():
    return copy.deepcopy(EXAMPLE_DOCUMENT)


def without_verdicts():
    return cases.build(copy.deepcopy(HYPOTHESIS_RECORD))


def changed(document, path, value):
    document = copy.deepcopy(document)
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return document


def removed(document, path):
    document = copy.deepcopy(document)
    target = document
    for part in path[:-1]:
        target = target[part]
    del target[path[-1]]
    return document


def raw(document):
    return json.dumps(document, indent=2).encode() + b"\n"


def spelt(document, path, literal):
    return raw(changed(document, path, MARK)).replace(f'"{MARK}"'.encode(), literal)


def invalid(start, content):
    with pytest.raises(InvalidCaseFileError) as caught:
        parse(content)
    message = str(caught.value)
    assert message.startswith(start)
    return message


def set_apart(content):
    with pytest.raises(UnsupportedVersionError) as caught:
        parse(content)
    assert not isinstance(caught.value, ValueError)
    return str(caught.value)


H = ("hypothesis_record",)
V = ("verdict_record",)
EVIDENCE = (*V, "verdicts", 0, "evidence")
INTEGER_PLACES = {
    "round": ("round",),
    "hypothesis_record.round": (*H, "round"),
    "hypothesis_record.candidates": (*H, "candidates"),
    "basis ref.round": (*H, "hypotheses", 0, "basis", 0, "ref", "round"),
    "tested_by": (*H, "hypotheses", 0, "tested_by", 0),
    "verdict_record.round": (*V, "round"),
    "check ref.round": (*EVIDENCE, 1, "ref", "round"),
    "check ref.attempt": (*EVIDENCE, 0, "ref", "attempt"),
    "against.round": (*EVIDENCE, 2, "against", "round"),
}


def test_the_example_of_the_record_parses_to_its_document():
    assert parse(EXAMPLE) == EXAMPLE_DOCUMENT


def test_the_example_of_the_record_has_its_final_name(tmp_path):
    assert final_name(tmp_path, HW, OP, parse(EXAMPLE)) == tmp_path / EXAMPLE_FILE
    assert final_name("data", HW, OP, parse(EXAMPLE)) == Path("data") / EXAMPLE_FILE


@pytest.mark.parametrize("document", [example(), without_verdicts()])
def test_a_valid_content_parses_to_a_new_document(document):
    content = raw(document)
    first, second = parse(content), parse(content)
    assert first == document == second
    assert first is not second


def test_a_case_without_verdicts_has_no_verdict_record():
    document = parse(raw(without_verdicts()))
    assert "verdict_record" not in document
    assert document["hypothesis_record"] == HYPOTHESIS_RECORD


def test_any_member_order_is_accepted():
    document = example()
    reordered = dict(reversed(list(document.items())))
    reordered["hypothesis_record"] = dict(
        reversed(list(reordered["hypothesis_record"].items()))
    )
    assert list(parse(raw(reordered))) == list(reordered)
    assert list(parse(raw(reordered))["hypothesis_record"]) == list(
        reordered["hypothesis_record"]
    )


@pytest.mark.parametrize(
    "form",
    [
        EXAMPLE.replace(b"\n", b"\r\n"),
        EXAMPLE[:-1],
        json.dumps(EXAMPLE_DOCUMENT, separators=(",", ":")).encode(),
        b" \t\n" + EXAMPLE + b"\n\n ",
    ],
)
def test_white_space_and_line_ends_are_not_checked(form):
    assert parse(form) == EXAMPLE_DOCUMENT


UNKNOWN = {
    "case": ("ext",),
    "hypothesis copy": (*H, "ext"),
    "verdict copy": (*V, "ext"),
}


@pytest.mark.parametrize("where", UNKNOWN)
@pytest.mark.parametrize(
    ("literal", "value"),
    [
        (b"-0", 0),
        (b"1.5", 1.5),
        (b"1e400", float("inf")),
        (b"-3", -3),
        (str(MAX + 1).encode(), MAX + 1),
        (b'"text"', "text"),
        (b"null", None),
        (b"true", True),
        (b'[-0, 1.0, {"a": -0}]', [0, 1.0, {"a": 0}]),
        (b'{"b": {"c": -0.0}}', {"b": {"c": -0.0}}),
    ],
)
def test_any_json_value_is_accepted_below_an_unknown_top_level_member(
    where, literal, value
):
    path = UNKNOWN[where]
    document = parse(spelt(changed(example(), path, None), path, literal))
    target = document
    for part in path:
        target = target[part]
    assert target == value
    assert type(target) is type(value)


@pytest.mark.parametrize("content", ["text", bytearray(EXAMPLE), None, memoryview(b"")])
def test_a_content_that_is_no_bytes_is_a_type_error(content):
    with pytest.raises(TypeError, match="content must be bytes, got"):
        parse(content)


def test_a_document_is_no_content():
    with pytest.raises(TypeError, match="content must be bytes, got dict"):
        parse(example())


@pytest.mark.parametrize("rest", [b"", b"{}", EXAMPLE, b"\xff"])
def test_a_byte_order_mark_is_refused(rest):
    message = invalid("content: starts", b"\xef\xbb\xbf" + rest)
    assert message == "content: starts with a byte order mark"


@pytest.mark.parametrize(
    "content",
    [
        b"\xff",
        EXAMPLE + b"\xc3",
        EXAMPLE.replace(b"NOT-DECIDED", b"NOT-\xe9-DECIDED", 1),
        json.dumps(EXAMPLE_DOCUMENT).encode("utf-16"),
    ],
)
def test_bytes_that_are_not_utf_8_are_refused(content):
    invalid(NOT_ONE_TEXT, content)


@pytest.mark.parametrize(
    "content",
    [b"", b" ", b"\n", EXAMPLE + EXAMPLE, EXAMPLE + b"x", EXAMPLE[:-3], b"{,}"],
)
def test_a_content_that_is_not_exactly_one_json_text_is_refused(content):
    invalid(NOT_ONE_TEXT, content)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_the_tokens_that_are_no_json_are_refused_everywhere(token):
    literal = token.encode()
    assert f"{token} is not a JSON value" in invalid(NOT_ONE_TEXT, literal)
    invalid(NOT_ONE_TEXT, spelt(example(), ("ext",), literal))
    invalid(NOT_ONE_TEXT, spelt(example(), (*H, "ext"), literal))
    invalid(NOT_ONE_TEXT, spelt(example(), ("round",), literal))


@pytest.mark.parametrize(
    ("content", "kind"),
    [
        (b"[]", "list"),
        (b"[" + EXAMPLE + b"]", "list"),
        (b'"text"', "str"),
        (b"1", "int"),
        (b"-0", "int"),
        (b"1.5", "float"),
        (b"null", "NoneType"),
    ],
)
def test_a_json_text_that_is_no_object_is_refused(content, kind):
    message = invalid("content: must be", content)
    assert message == f"content: must be a JSON object, got {kind}"


def test_nesting_too_deep_for_the_interpreter_is_reported():
    deep = b"[" * 2_000_000 + b"]" * 2_000_000
    message = invalid("content: is nested", spelt(example(), ("ext",), deep))
    assert message == "content: is nested too deeply to parse"


def test_an_integer_literal_too_long_for_the_interpreter_is_not_read():
    invalid(NOT_ONE_TEXT, spelt(example(), ("ext",), b"1" + b"0" * 5000))


TWICE = {
    "the top level": lambda text: text.replace(b"{", b'{"schema_version": 1, ', 1),
    "an unknown top-level member": lambda text: text.replace(
        b"{", b'{"ext": {"a": 1, "a": 1}, ', 1
    ),
    "an unknown top-level member twice": lambda text: text.replace(
        b"{", b'{"ext": 1, "ext": 1, ', 1
    ),
    "the top level of the hypothesis copy": lambda text: text.replace(
        b'"candidates": 1', b'"candidates": 1, "candidates": 1'
    ),
    "an unknown member of a copy": lambda text: text.replace(
        b'"candidates": 1', b'"candidates": 1, "ext": {"a": 1, "a": 2}'
    ),
    "a hypothesis": lambda text: text.replace(b'"id": "h1"', b'"id": "h1", "id": "h1"'),
    "a basis ref": lambda text: text.replace(
        b'"ref": {"round": 0', b'"ref": {"round": 0, "round": 0', 1
    ),
    "the top level of the verdict copy": lambda text: text.replace(
        b'"round": 1,\n    "verdicts"', b'"round": 1, "round": 1,\n    "verdicts"'
    ),
    "a check entry": lambda text: text.replace(
        b'"outcome": "pass"', b'"outcome": "pass", "outcome": "pass"', 1
    ),
    "a measured ref": lambda text: text.replace(
        b'"measured": {"round": 1', b'"measured": {"round": 1, "round": 1'
    ),
}


@pytest.mark.parametrize("place", TWICE)
def test_a_member_name_twice_in_any_object_is_refused(place):
    content = TWICE[place](EXAMPLE)
    assert content != EXAMPLE
    assert "repeats a member name" in invalid(NOT_ONE_TEXT, content)


@pytest.mark.parametrize("version", [0, 2, 7, MAX])
def test_another_version_of_the_case_is_set_apart(version):
    document = changed(example(), ("schema_version",), version)
    assert set_apart(raw(document)) == f"schema_version: is {version}, not 1"


@pytest.mark.parametrize("copy_name", ["hypothesis_record", "verdict_record"])
@pytest.mark.parametrize("version", [0, 2, MAX])
def test_another_version_of_a_copy_is_set_apart(copy_name, version):
    document = changed(example(), (copy_name, "schema_version"), version)
    message = set_apart(raw(document))
    assert message == f"{copy_name}.schema_version: is {version}, not 1"


@pytest.mark.parametrize(
    "rest",
    [
        b"",
        b', "round": 0',
        b', "hypothesis_record": 1',
        b', "round": -0',
        b', "x": 1e999',
        b', "hypothesis_record": {"schema_version": 2}',
    ],
)
def test_another_version_is_reported_whatever_else_the_content_holds(rest):
    assert set_apart(b'{"schema_version": 2' + rest + b"}").startswith(
        "schema_version:"
    )


@pytest.mark.parametrize(
    ("content", "path"),
    [
        (b'{"schema_version": 1, "hypothesis_record": {"schema_version": 2}}', "h"),
        (
            (
                b'{"round": -0, "hypothesis_record": {"schema_version": 3, "round": 0},'
                b' "schema_version": 1}'
            ),
            "h",
        ),
        (
            (
                b'{"schema_version": 1, "hypothesis_record": [],'
                b' "verdict_record": {"schema_version": 2, "verdicts": 1}}'
            ),
            "v",
        ),
        (
            (
                b'{"schema_version": 1, "verdict_record": {"schema_version": 2},'
                b' "hypothesis_record": {"schema_version": 1}}'
            ),
            "v",
        ),
        (
            (
                b'{"schema_version": 1, "verdict_record": {"schema_version": 2},'
                b' "hypothesis_record": {"schema_version": 4}}'
            ),
            "h",
        ),
    ],
)
def test_a_copy_of_another_version_is_reported_whatever_else_the_case_holds(
    content, path
):
    name = {"h": "hypothesis_record", "v": "verdict_record"}[path]
    assert set_apart(content).startswith(f"{name}.schema_version:")


def test_the_version_of_the_case_wins_over_that_of_a_copy():
    document = changed(example(), ("schema_version",), 2)
    document = changed(document, (*H, "schema_version"), 3)
    document = changed(document, (*V, "schema_version"), 4)
    assert set_apart(raw(document)) == "schema_version: is 2, not 1"


@pytest.mark.parametrize(
    "literal", [b"-1", str(MAX + 1).encode(), b"1.0", b'"1"', b"true", b"null"]
)
def test_a_copy_version_is_not_looked_at_when_the_case_version_is_invalid(literal):
    content = spelt(
        changed(example(), (*H, "schema_version"), 2), ("schema_version",), literal
    )
    invalid("schema_version:", content)


@pytest.mark.parametrize(
    "content",
    [
        b'{"schema_version": 2, "a": 1, "a": 1}',
        b'{"schema_version": 2, "a": NaN}',
        b'\xef\xbb\xbf{"schema_version": 2}',
        b'{"schema_version": 2}{}',
        b'{"schema_version": 1, "hypothesis_record": {"schema_version": 2, "a": 1, "a": 1}}',
    ],
)
def test_the_rules_for_the_whole_text_come_before_the_version(content):
    with pytest.raises(InvalidCaseFileError):
        parse(content)


@pytest.mark.parametrize(
    "path", [("schema_version",), (*H, "schema_version"), (*V, "schema_version")]
)
@pytest.mark.parametrize(
    "literal", [b"-1", str(MAX + 1).encode(), b"1.0", b"1e0", b'"1"', b"true", b"null"]
)
def test_a_schema_version_that_is_no_other_version_is_invalid(path, literal):
    dotted = ".".join(path)
    message = invalid(f"{dotted}:", spelt(example(), path, literal))
    assert "must be the integer 1" in message


@pytest.mark.parametrize(
    "path", [("schema_version",), (*H, "schema_version"), (*V, "schema_version")]
)
def test_minus_zero_as_a_schema_version_is_invalid_and_no_other_version(path):
    dotted = ".".join(path)
    message = invalid(f"{dotted}:", spelt(example(), path, b"-0"))
    assert message == f"{dotted}: is written as -0, which is no integer"


def test_minus_zero_as_a_version_is_refused_whatever_else_the_content_holds():
    invalid("schema_version:", b'{"schema_version": -0}')
    invalid(
        "hypothesis_record.schema_version:",
        b'{"schema_version": 1, "hypothesis_record": {"schema_version": -0}}',
    )


@pytest.mark.parametrize(
    ("path", "start"),
    [
        (("schema_version",), "schema_version: required member is missing"),
        (H, "hypothesis_record: required member is missing"),
        ((*H, "schema_version"), "hypothesis_record.schema_version: required"),
        ((*V, "schema_version"), "verdict_record.schema_version: required"),
    ],
)
def test_an_absent_required_member_is_invalid(path, start):
    invalid(start, raw(removed(example(), path)))


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("round",), 0),
        (("run_id",), ""),
        (H, None),
        (H, []),
        (V, None),
        (V, "inconclusive"),
        ((*H, "run_id"), "synthetic-other-run"),
        ((*V, "run_id"), "synthetic-other-run"),
        ((*V, "round"), 2),
        ((*H, "hypotheses", 0, "id"), "h2"),
        ((*H, "hypotheses", 0, "tested_by"), [2]),
        ((*V, "verdicts", 0, "verdict"), "partial"),
        ((*EVIDENCE, 2, "metric"), "memory_ceiling"),
    ],
)
def test_a_document_the_validator_refuses_is_invalid_with_its_message(path, value):
    document = changed(example(), path, value)
    with pytest.raises(cases.InvalidCaseError) as expected:
        cases.validate(document)
    with pytest.raises(InvalidCaseFileError) as caught:
        parse(raw(document))
    assert str(caught.value) == str(expected.value)
    assert ":" in str(caught.value)
    assert isinstance(caught.value.__cause__, cases.InvalidCaseError)


def test_a_pair_that_breaks_the_rules_between_its_files_is_invalid():
    document = changed(example(), (*V, "verdicts", 0, "hypothesis"), "h2")
    message = invalid("verdict_record", raw(document))
    with pytest.raises(cases.InvalidCaseError) as expected:
        cases.validate(document)
    assert message == str(expected.value)


@pytest.mark.parametrize("place", INTEGER_PLACES)
def test_minus_zero_at_an_integer_place_is_refused(place):
    path = INTEGER_PLACES[place]
    with pytest.raises(InvalidCaseFileError):
        parse(spelt(example(), path, b"-0"))


ZERO_PLACES = {
    "basis ref.round": "hypothesis_record.hypotheses[0].basis[0].ref.round",
    "check ref.round": "verdict_record.verdicts[0].evidence[1].ref.round",
    "against.round": "verdict_record.verdicts[0].evidence[2].against.round",
}


@pytest.mark.parametrize("place", ZERO_PLACES)
def test_minus_zero_where_zero_is_valid_is_refused_by_its_text(place):
    path = INTEGER_PLACES[place]
    assert parse(spelt(example(), path, b"0")) == example()
    message = invalid(ZERO_PLACES[place], spelt(example(), path, b"-0"))
    assert message == f"{ZERO_PLACES[place]}: is written as -0, which is no integer"


def test_the_first_minus_zero_in_the_order_of_the_text_is_named():
    content = EXAMPLE.replace(b'"round": 0', b'"round": -0')
    assert content.count(b'"round": -0') == 3
    invalid("hypothesis_record.hypotheses[0].basis[0].ref.round:", content)
    reordered = {"verdict_record": VERDICT_RECORD} | example()
    content = json.dumps(reordered).encode().replace(b'"round": 0', b'"round": -0')
    invalid("verdict_record.verdicts[0].evidence[1].ref.round:", content)


@pytest.mark.parametrize("literal", [b"1.0", b"1e0", b"-1", str(MAX + 1).encode()])
@pytest.mark.parametrize("path", [("round",), (*H, "round"), (*V, "round")])
def test_a_number_that_is_no_integer_at_an_integer_place_is_refused(path, literal):
    invalid(path[0], spelt(example(), path, literal))


def test_the_string_minus_zero_is_no_number():
    document = changed(example(), (*V, "verdicts", 0, "cause"), "-0")
    assert parse(raw(document)) == document


OTHER_RUN = "20261001t000000z-0123456789abcdef"


def with_case_basis():
    document = example()
    document["hypothesis_record"]["cases_read"] = [
        {"run_id": "third-run", "round": 4},
        {"run_id": OTHER_RUN, "round": 2},
    ]
    case = {"run_id": OTHER_RUN, "round": 2, "hypothesis": "h3"}
    document["hypothesis_record"]["hypotheses"][0]["basis"].append(
        {"kind": "case", "case": case, "text": "stored case"}
    )
    return document


def test_a_case_whose_hypothesis_copy_rests_on_a_case_parses():
    document = with_case_basis()
    assert parse(raw(document)) == document


@pytest.mark.parametrize(
    ("path", "start"),
    [
        ((*H, "cases_read", 1, "round"), "hypothesis_record.cases_read[1].round:"),
        (
            (*H, "hypotheses", 0, "basis", 1, "case", "round"),
            "hypothesis_record.hypotheses[0].basis[1].case.round:",
        ),
    ],
)
def test_minus_zero_at_a_case_round_of_the_copy_is_refused_with_its_path(path, start):
    invalid(start, spelt(with_case_basis(), path, b"-0"))


def test_a_copy_breaking_an_in_file_rule_of_the_case_basis_is_invalid():
    document = with_case_basis()
    document["hypothesis_record"]["cases_read"].pop()
    message = invalid("hypothesis_record.hypotheses[0].basis[1].case:", raw(document))
    assert "no entry of cases_read" in message


def test_the_classes_tell_invalid_from_another_version():
    assert issubclass(InvalidCaseFileError, ValueError)
    assert not issubclass(UnsupportedVersionError, ValueError)
    assert not issubclass(InvalidCaseFileError, UnsupportedVersionError)
    assert not issubclass(InvalidCaseFileError, cases.InvalidCaseError)


def test_the_order_of_the_checks_of_parse():
    order = [
        ("x", TypeError),
        (b"\xef\xbb\xbf\xff", InvalidCaseFileError),
        (b"[", InvalidCaseFileError),
        (b"[2]", InvalidCaseFileError),
        (b'{"schema_version": 2, "round": -0}', UnsupportedVersionError),
        (
            b'{"schema_version": 1, "round": -0, "hypothesis_record": {"schema_version": 2}}',
            UnsupportedVersionError,
        ),
        (b'{"schema_version": 1, "round": -0}', InvalidCaseFileError),
    ]
    for content, error in order:
        with pytest.raises(error):
            parse(content)


@pytest.mark.parametrize(
    ("run_id", "round", "name"),
    [
        (RUN_ID, 1, f"case-{RUN_ID}-0001.json"),
        ("synthetic-run-1", 12, "case-synthetic-run-1-0012.json"),
        ("r", 12345, "case-r-12345.json"),
    ],
)
def test_the_final_name_is_the_path_of_run_id_and_round(run_id, round, name):
    document = example()
    for target in (document, document[H[0]], document[V[0]]):
        target["run_id"], target["round"] = run_id, round
    for place in ((*EVIDENCE, 0, "ref"), (*EVIDENCE, 2, "measured")):
        document = changed(document, (*place, "round"), round)
    expected = Path("root") / KEY_DIR / name
    assert final_name(Path("root"), HW, OP, document) == expected
    assert expected == layout.case_record("root", HW, OP, run_id, round)


@pytest.mark.parametrize(
    "document",
    [
        changed(example(), ("round",), 0),
        changed(example(), ("schema_version",), 2),
        changed(example(), (*H, "schema_version"), 2),
        removed(example(), H),
        [],
        None,
    ],
)
def test_a_document_that_is_no_valid_case_yields_no_path(document):
    with pytest.raises(cases.InvalidCaseError):
        final_name("root", HW, OP, document)


def test_an_invalid_document_is_reported_before_a_bad_key_name():
    with pytest.raises(cases.InvalidCaseError):
        final_name("root", "Bad Key", OP, None)


@pytest.mark.parametrize(
    ("hw", "op"),
    [("Bad Key", OP), (HW, "a/b"), (HW, ".."), ("", OP), (HW, "x.y"), (None, OP)],
)
def test_a_bad_key_name_has_no_path(hw, op):
    with pytest.raises(layout.InvalidPathValueError):
        final_name("root", hw, op, example())


@pytest.mark.parametrize("run_id", ["No Path", "..", "a/b"])
def test_a_valid_document_without_a_run_directory_name_has_no_path(run_id):
    document = example()
    for target in (document, document[H[0]], document[V[0]]):
        target["run_id"] = run_id
    assert parse(raw(document)) == document
    with pytest.raises(layout.InvalidPathValueError):
        final_name("root", HW, OP, document)


@pytest.mark.parametrize("data_root", [None, 7, b"data"])
def test_a_data_root_that_is_no_path_is_a_type_error(data_root):
    with pytest.raises(TypeError):
        final_name(data_root, HW, OP, example())


def test_nothing_is_modified():
    document = example()
    content = raw(document)
    parse(content)
    final_name("root", HW, OP, document)
    assert document == EXAMPLE_DOCUMENT
    assert content == raw(EXAMPLE_DOCUMENT)


def test_parse_and_final_name_open_no_file(monkeypatch, tmp_path):
    def refuse(*arguments, **named):
        raise AssertionError("a file was touched")

    monkeypatch.setattr(builtins, "open", refuse)
    monkeypatch.setattr(io, "open", refuse)
    monkeypatch.setattr(os, "open", refuse)
    for name in ("stat", "lstat", "listdir", "scandir", "mkdir"):
        monkeypatch.setattr(os, name, refuse)
    final_name(tmp_path, HW, OP, parse(EXAMPLE))


TEMPORARY = re.compile(rf"case-{RUN_ID}-0001\.json\.[0-9]+-[0-9a-f]{{16}}\.tmp")
OTHER = raw(changed(example(), (*V, "verdicts", 0, "cause"), "another"))
STEPS = ("creation", "write", "flush", "link")


class Stop(BaseException):
    pass


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    (path / KEY_DIR).mkdir(parents=True)
    return path


@pytest.fixture(autouse=True)
def no_replacing_step(monkeypatch):
    def refuse(*arguments, **named):
        pytest.fail("a replacing step was called")

    monkeypatch.setattr(os, "replace", refuse)
    monkeypatch.setattr(os, "rename", refuse)


def place(root, content, relative=EXAMPLE_FILE):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def snapshot(directory):
    return {
        path.relative_to(directory).as_posix(): (
            path.read_bytes() if path.is_file() else None
        )
        for path in directory.rglob("*")
    }


def temporaries(directory):
    return [n for n in snapshot(directory) if TEMPORARY.fullmatch(Path(n).name)]


class Partial:
    def __init__(self, file, error):
        self.file = file
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return self.file.__exit__(*exception)

    def write(self, content):
        self.file.write(content[:7])
        raise self.error


def break_step(monkeypatch, step, error):
    real = open

    def refuse(*arguments, **named):
        raise error

    def creation(file, mode="r", *arguments, **named):
        if "x" not in mode:
            return real(file, mode, *arguments, **named)
        if step == "creation":
            raise error
        return Partial(real(file, mode, *arguments, **named), error)

    if step in ("creation", "write"):
        monkeypatch.setattr("builtins.open", creation)
    else:
        name = {"flush": "fsync", "link": "link"}[step]
        monkeypatch.setattr(os, name, refuse)


@pytest.mark.parametrize("as_type", [Path, str])
def test_the_example_is_written_byte_for_byte_under_its_final_name(root, as_type):
    before = snapshot(root)
    assert write(as_type(root), HW, OP, EXAMPLE) is None
    assert snapshot(root) == before | {EXAMPLE_FILE: EXAMPLE}
    assert (root / EXAMPLE_FILE).read_bytes() == EXAMPLE


def test_a_case_without_verdicts_is_written(root):
    content = json.dumps(without_verdicts()).encode() + b"\n"
    write(root, HW, OP, content)
    assert (root / EXAMPLE_FILE).read_bytes() == content


def test_no_other_file_is_required_read_or_touched(root, monkeypatch):
    place(root, b"not even json", f"{KEY_DIR}/op_signature.json")
    place(root, b"x", f"{KEY_DIR}/case-{RUN_ID}-0002.json")
    place(root, b"not even json", f"runs/{RUN_ID}/instance.json")
    before = snapshot(root)
    opened = []
    real = open

    def spy(file, mode="r", *arguments, **named):
        opened.append((Path(file).name, mode))
        return real(file, mode, *arguments, **named)

    monkeypatch.setattr("builtins.open", spy)
    write(root, HW, OP, EXAMPLE)
    monkeypatch.undo()

    ((name, mode),) = opened
    assert TEMPORARY.fullmatch(name) and mode == "xb"
    assert snapshot(root) == before | {EXAMPLE_FILE: EXAMPLE}


def test_a_key_directory_without_record_files_takes_a_case(root):
    write(root, HW, OP, EXAMPLE)
    assert snapshot(root) == {
        "db": None,
        f"db/{HW}": None,
        KEY_DIR: None,
        EXAMPLE_FILE: EXAMPLE,
    }


def test_white_space_member_order_and_unknown_members_are_written_as_given(root):
    content = (
        b'{"ext": [-0, 1.50, 1E+2],\n "verdict_record": '
        + json.dumps(VERDICT_RECORD | {"ext": -0.0}).encode()
        + b', "hypothesis_record": '
        + json.dumps(HYPOTHESIS_RECORD).encode()
        + b', "round": 1, "run_id": "'
        + RUN_ID.encode()
        + b'",  "schema_version": 1}\n'
    )
    write(root, HW, OP, content)
    assert (root / EXAMPLE_FILE).read_bytes() == content


@pytest.mark.parametrize("previous", [EXAMPLE, OTHER])
def test_a_taken_name_is_reported_and_what_is_there_is_unchanged(root, previous):
    place(root, previous)
    before = snapshot(root)

    with pytest.raises(NameTakenError) as caught:
        write(root, HW, OP, EXAMPLE)

    assert str(caught.value) == (
        f"{EXAMPLE_FILE}: the name is taken; the content was not written"
    )
    assert not isinstance(caught.value, OSError)
    assert snapshot(root) == before
    assert temporaries(root) == []


def test_a_taken_name_is_not_opened(root, monkeypatch):
    place(root, OTHER)
    opened = []
    real = open

    def spy(file, mode="r", *arguments, **named):
        opened.append((Path(file).name, mode))
        return real(file, mode, *arguments, **named)

    monkeypatch.setattr("builtins.open", spy)
    with pytest.raises(NameTakenError):
        write(root, HW, OP, EXAMPLE)
    monkeypatch.undo()

    ((name, mode),) = opened
    assert TEMPORARY.fullmatch(name) and mode == "xb"


def test_equal_bytes_are_reported_as_other_bytes(root):
    write(root, HW, OP, EXAMPLE)
    before = snapshot(root)
    reports = []
    for content in (EXAMPLE, OTHER):
        with pytest.raises(NameTakenError) as caught:
            write(root, HW, OP, content)
        reports.append(str(caught.value))

    assert reports[0] == reports[1]
    assert snapshot(root) == before


REFUSED = {
    "no bytes": (EXAMPLE.decode(), TypeError),
    "invalid": (EXAMPLE[:20], InvalidCaseFileError),
    "round 0": (raw(changed(example(), ("round",), 0)), InvalidCaseFileError),
    "minus zero": (
        EXAMPLE.replace(b'"round": 0', b'"round": -0'),
        InvalidCaseFileError,
    ),
    "another version": (
        raw(changed(example(), ("schema_version",), 2)),
        UnsupportedVersionError,
    ),
    "a copy of another version": (
        raw(changed(example(), (*V, "schema_version"), 2)),
        UnsupportedVersionError,
    ),
    "no final line feed": (EXAMPLE[:-1], WrittenFormError),
    "carriage return": (EXAMPLE.replace(b"\n", b"\r\n"), WrittenFormError),
}


@pytest.mark.parametrize(("content", "error"), REFUSED.values(), ids=REFUSED)
def test_a_refused_content_creates_and_changes_nothing(root, content, error):
    before = snapshot(root)
    with pytest.raises(error) as caught:
        write(root, HW, OP, content)

    assert type(caught.value) is error
    assert snapshot(root) == before


def test_bad_names_create_and_change_nothing(root):
    before = snapshot(root)
    with pytest.raises(layout.InvalidPathValueError):
        write(root, "Bad Key", OP, EXAMPLE)
    with pytest.raises(layout.InvalidPathValueError):
        write(
            root,
            HW,
            OP,
            raw(changed(example(), ("ext",), 1)).replace(RUN_ID.encode(), b"No Path"),
        )
    assert snapshot(root) == before


def test_the_written_form_errors_name_the_rule():
    with pytest.raises(WrittenFormError, match="does not end with a line feed"):
        write("absent", HW, OP, EXAMPLE[:-1])
    with pytest.raises(WrittenFormError, match="holds a carriage return byte"):
        write("absent", HW, OP, b"\r" + EXAMPLE)
    assert issubclass(WrittenFormError, ValueError)
    assert not issubclass(WrittenFormError, InvalidCaseFileError)
    assert not issubclass(NameTakenError, (OSError, ValueError))


MISSING = {
    "data root": None,
    "db": "data",
    "hardware directory": "data/db",
    "key directory": f"data/db/{HW}",
}


@pytest.mark.parametrize("as_type", [Path, str])
@pytest.mark.parametrize("missing", MISSING)
def test_a_missing_directory_is_not_created(tmp_path, missing, as_type):
    if MISSING[missing] is not None:
        (tmp_path / MISSING[missing]).mkdir(parents=True)
    before = snapshot(tmp_path)

    with pytest.raises(FileNotFoundError, match="key directory"):
        write(as_type(tmp_path / "data"), HW, OP, EXAMPLE)

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("name", [KEY_DIR, f"db/{HW}", "db"])
def test_a_file_in_the_place_of_a_directory(tmp_path, name):
    place(tmp_path, b"a file", f"data/{name}")
    before = snapshot(tmp_path)
    error = NotADirectoryError if name == KEY_DIR else FileNotFoundError

    with pytest.raises(error, match="key directory") as caught:
        write(tmp_path / "data", HW, OP, EXAMPLE)

    assert type(caught.value) is error
    assert snapshot(tmp_path) == before


def test_a_file_in_the_place_of_the_data_root(tmp_path):
    place(tmp_path, b"a file", "data")

    with pytest.raises(FileNotFoundError, match="key directory"):
        write(tmp_path / "data", HW, OP, EXAMPLE)

    assert snapshot(tmp_path) == {"data": b"a file"}


@pytest.mark.parametrize("data_root", [None, 7, b"data"])
def test_write_with_a_data_root_that_is_no_path(data_root):
    with pytest.raises(TypeError):
        write(data_root, HW, OP, EXAMPLE)


def test_the_order_of_the_checks_of_write(tmp_path):
    absent = tmp_path / "absent"
    key_file = place(tmp_path, b"a file", f"data/{KEY_DIR}").parents[2]
    no_path = EXAMPLE.replace(RUN_ID.encode(), b"No Path")
    order = [
        (None, OP, None, TypeError),
        (None, OP, EXAMPLE[:20], InvalidCaseFileError),
        (None, OP, b'{"schema_version": 2}', UnsupportedVersionError),
        (
            absent,
            "a/b",
            raw(changed(example(), ("round",), 0)) + b"\r",
            InvalidCaseFileError,
        ),
        (
            absent,
            "a/b",
            raw(changed(example(), (*H, "schema_version"), 2))[:-1],
            UnsupportedVersionError,
        ),
        (absent, OP, no_path[:-1], layout.InvalidPathValueError),
        (absent, "a/b", EXAMPLE[:-1], layout.InvalidPathValueError),
        (None, OP, EXAMPLE[:-1], TypeError),
        (absent, OP, EXAMPLE[:-1], WrittenFormError),
        (key_file, OP, b"\r" + EXAMPLE, WrittenFormError),
        (absent, OP, EXAMPLE, FileNotFoundError),
        (key_file, OP, EXAMPLE, NotADirectoryError),
    ]
    before = snapshot(tmp_path)

    for data_root, op, content, error in order:
        with pytest.raises(error) as caught:
            write(data_root, HW, op, content)
        assert type(caught.value) is error

    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("previous", [None, OTHER])
@pytest.mark.parametrize("step", STEPS)
def test_a_failed_step_leaves_the_final_name_and_no_temporary_file(
    root, monkeypatch, step, previous
):
    if previous is not None:
        place(root, previous)
    before = snapshot(root)
    error = OSError(f"{step} refused")
    break_step(monkeypatch, step, error)

    with pytest.raises(OSError) as caught:
        write(root, HW, OP, EXAMPLE)
    monkeypatch.undo()

    assert caught.value is error
    assert snapshot(root) == before
    assert temporaries(root) == []


@pytest.mark.parametrize("step", STEPS[1:])
def test_an_interrupt_removes_the_temporary_file_too(root, monkeypatch, step):
    before = snapshot(root)
    break_step(monkeypatch, step, Stop())

    with pytest.raises(Stop):
        write(root, HW, OP, EXAMPLE)
    monkeypatch.undo()

    assert snapshot(root) == before


def test_a_leftover_of_another_write_is_not_touched(root):
    leftover = f"{EXAMPLE_FILE}.4242-0123456789abcdef.tmp"
    place(root, b"of another writer", leftover)
    before = snapshot(root)

    write(root, HW, OP, EXAMPLE)

    assert snapshot(root) == before | {EXAMPLE_FILE: EXAMPLE}


def test_the_temporary_file_is_in_the_key_directory(root, monkeypatch):
    sources = []
    give = os.link

    def linking(source, target):
        sources.append((Path(source), Path(target)))
        return give(source, target)

    monkeypatch.setattr(os, "link", linking)
    write(root, HW, OP, EXAMPLE)
    monkeypatch.undo()

    ((source, target),) = sources
    assert TEMPORARY.fullmatch(source.name)
    assert source.parent == target.parent == root / KEY_DIR
    assert target == root / EXAMPLE_FILE


def test_a_temporary_name_in_use_is_an_error_and_that_file_stays(root, monkeypatch):
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * 2 * size)
    name = f"{EXAMPLE_FILE}.{os.getpid()}-{'0' * 16}.tmp"
    place(root, b"of another writer", name)
    before = snapshot(root)

    with pytest.raises(FileExistsError) as caught:
        write(root, HW, OP, EXAMPLE)

    assert not isinstance(caught.value, NameTakenError)
    assert snapshot(root) == before


def test_no_directory_is_created_by_write(root, monkeypatch):
    def refuse(*arguments, **named):
        pytest.fail("a directory was created")

    monkeypatch.setattr(os, "mkdir", refuse)
    monkeypatch.setattr(os, "makedirs", refuse)
    write(root, HW, OP, EXAMPLE)
    monkeypatch.undo()
    assert (root / EXAMPLE_FILE).read_bytes() == EXAMPLE


def test_the_public_names():
    public = sorted(name for name in vars(cases_file) if not name.startswith("_"))
    assert public == [
        "InvalidCaseFileError",
        "NameTakenError",
        "Path",
        "UnsupportedVersionError",
        "WrittenFormError",
        "cases",
        "codecs",
        "final_name",
        "hypotheses",
        "json",
        "keys",
        "layout",
        "once_write",
        "parse",
        "verdicts",
        "write",
    ]
