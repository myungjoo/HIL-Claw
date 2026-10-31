import builtins
import copy
import io
import json
import os
import re
import secrets
from pathlib import Path

import pytest

from hilclaw import keys, layout, verdicts, verdicts_file
from hilclaw.verdicts_file import (
    InvalidVerdictFileError,
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

EXAMPLE = b"""{
  "schema_version": 1,
  "run_id": "20261009t012331z-9f3a6c1e0b7d4a52",
  "round": 1,
  "verdicts": [
    {
      "hypothesis": "h1",
      "verdict": "supported",
      "cause": "NOT-DECIDED-HERE",
      "evidence": [
        {"kind": "check", "ref": {"round": 1, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
        {"kind": "check", "ref": {"round": 0, "candidate": 1, "attempt": 1}, "point": "board", "outcome": "pass"},
        {"kind": "comparison", "metric": "latency_minimisation", "point": "board",
         "measured": {"round": 1, "candidate": 1, "attempt": 1},
         "against": {"round": 0, "candidate": 1, "attempt": 1}, "difference": "lower"}
      ]
    }
  ]
}
"""


def _ref(round, candidate=1, attempt=1):
    return {"round": round, "candidate": candidate, "attempt": attempt}


EXAMPLE_DOCUMENT = {
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

EXAMPLE_FILE = f"runs/{RUN_ID}/rounds/0001/eval/verdicts.json"


def example():
    return copy.deepcopy(EXAMPLE_DOCUMENT)


def two_verdicts():
    document = example()
    document["round"] = 3
    first = document["verdicts"][0]
    first["evidence"][0]["ref"] = _ref(3, 2, 4)
    first["evidence"][2]["measured"] = _ref(3, 2, 4)
    first["verdict"] = "refuted"
    first["evidence"][2]["difference"] = "higher"
    document["verdicts"].append(
        {
            "hypothesis": "h2",
            "verdict": "inconclusive",
            "cause": "no candidate passed its board check",
            "evidence": [],
        }
    )
    return document


def changed(document, path, value):
    document = copy.deepcopy(document)
    target = document
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    return document


def raw(document):
    return json.dumps(document, indent=2).encode() + b"\n"


def spelt(document, path, literal):
    return raw(changed(document, path, MARK)).replace(f'"{MARK}"'.encode(), literal)


def invalid(start, content):
    with pytest.raises(InvalidVerdictFileError) as caught:
        parse(content)
    message = str(caught.value)
    assert message.startswith(start)
    return message


EVIDENCE = ("verdicts", 0, "evidence")
INTEGER_PLACES = {
    "round": ("round",),
    "check ref.round": (*EVIDENCE, 1, "ref", "round"),
    "check ref.candidate": (*EVIDENCE, 0, "ref", "candidate"),
    "check ref.attempt": (*EVIDENCE, 0, "ref", "attempt"),
    "measured.round": (*EVIDENCE, 2, "measured", "round"),
    "measured.candidate": (*EVIDENCE, 2, "measured", "candidate"),
    "against.round": (*EVIDENCE, 2, "against", "round"),
    "against.attempt": (*EVIDENCE, 2, "against", "attempt"),
}


def test_the_example_of_the_record_parses_to_its_document():
    assert parse(EXAMPLE) == EXAMPLE_DOCUMENT


def test_the_example_of_the_record_has_its_final_name(tmp_path):
    assert final_name(tmp_path, parse(EXAMPLE)) == tmp_path / EXAMPLE_FILE
    assert final_name("data", parse(EXAMPLE)) == Path("data") / EXAMPLE_FILE


@pytest.mark.parametrize("document", [example(), two_verdicts()])
def test_a_valid_content_parses_to_a_new_document(document):
    content = raw(document)
    first, second = parse(content), parse(content)
    assert first == document == second
    assert first is not second


def test_any_member_order_is_accepted():
    document = example()
    reordered = dict(reversed(list(document.items())))
    assert list(parse(raw(reordered))) == list(reordered)


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
def test_any_json_value_is_accepted_below_an_unknown_top_level_member(literal, value):
    document = parse(spelt(changed(example(), ("ext",), None), ("ext",), literal))
    assert document["ext"] == value
    assert type(document["ext"]) is type(value)


@pytest.mark.parametrize(
    "path", [("verdicts", 0, "ext"), (*EVIDENCE, 0, "ext"), (*EVIDENCE, 2, "ext")]
)
def test_an_unknown_member_inside_a_known_one_is_refused(path):
    message = invalid("verdicts[0]", raw(changed(example(), path, 1)))
    assert "unknown member 'ext'" in message


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
        EXAMPLE.replace(b"NOT-DECIDED", b"NOT-\xe9-DECIDED"),
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
    "a verdict": lambda text: text.replace(
        b'"hypothesis": "h1"', b'"hypothesis": "h1", "hypothesis": "h1"'
    ),
    "a check entry": lambda text: text.replace(
        b'"outcome": "pass"', b'"outcome": "pass", "outcome": "pass"', 1
    ),
    "a comparison entry": lambda text: text.replace(
        b'"difference": "lower"', b'"difference": "lower", "difference": "lower"'
    ),
    "a ref": lambda text: text.replace(b'"round": 0', b'"round": 0, "round": 0', 1),
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
def test_another_version_is_set_apart(version):
    document = changed(example(), ("schema_version",), version)
    with pytest.raises(UnsupportedVersionError) as caught:
        parse(raw(document))
    assert str(caught.value) == f"schema_version: is {version}, not 1"
    assert not isinstance(caught.value, ValueError)


@pytest.mark.parametrize(
    "rest",
    [b"", b', "round": 0', b', "verdicts": 1', b', "round": -0', b', "x": 1e999'],
)
def test_another_version_is_reported_whatever_else_the_content_holds(rest):
    with pytest.raises(UnsupportedVersionError):
        parse(b'{"schema_version": 2' + rest + b"}")


@pytest.mark.parametrize(
    "content",
    [
        b'{"schema_version": 2, "a": 1, "a": 1}',
        b'{"schema_version": 2, "a": NaN}',
        b'\xef\xbb\xbf{"schema_version": 2}',
        b'{"schema_version": 2}{}',
    ],
)
def test_the_rules_for_the_whole_text_come_before_the_version(content):
    with pytest.raises(InvalidVerdictFileError):
        parse(content)


@pytest.mark.parametrize(
    "literal", [b"-1", str(MAX + 1).encode(), b"1.0", b"1e0", b'"1"', b"true", b"null"]
)
def test_a_schema_version_that_is_no_other_version_is_invalid(literal):
    message = invalid("schema_version:", spelt(example(), ("schema_version",), literal))
    assert "must be the integer 1" in message


def test_minus_zero_as_a_schema_version_is_invalid_and_no_other_version():
    message = invalid("schema_version:", spelt(example(), ("schema_version",), b"-0"))
    assert message == "schema_version: is written as -0, which is no integer"
    invalid("schema_version:", b'{"schema_version": -0}')


def test_an_absent_schema_version_is_invalid():
    document = example()
    del document["schema_version"]
    assert invalid("schema_version", raw(document)) == (
        "schema_version: required member is missing"
    )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("round",), 0),
        (("run_id",), ""),
        (("verdicts",), []),
        (("verdicts", 0, "verdict"), "partial"),
        (("verdicts", 0, "cause"), ""),
        ((*EVIDENCE, 1, "outcome"), "fail"),
        ((*EVIDENCE, 2, "point"), "sim"),
        ((*EVIDENCE, 2, "metric"), "memory_ceiling"),
        ((*EVIDENCE, 2, "measured", "round"), 0),
        ((*EVIDENCE, 2, "against", "round"), 2),
    ],
)
def test_a_document_the_validator_refuses_is_invalid_with_its_message(path, value):
    document = changed(example(), path, value)
    with pytest.raises(verdicts.InvalidVerdictRecordError) as expected:
        verdicts.validate(document)
    with pytest.raises(InvalidVerdictFileError) as caught:
        parse(raw(document))
    assert str(caught.value) == str(expected.value)
    assert ":" in str(caught.value)
    assert isinstance(caught.value.__cause__, verdicts.InvalidVerdictRecordError)


def test_a_supported_verdict_without_a_counted_comparison_is_invalid():
    document = changed(example(), (*EVIDENCE, 0, "outcome"), "broken")
    message = invalid("verdicts[0].evidence:", raw(document))
    assert "counted comparison" in message


@pytest.mark.parametrize("place", INTEGER_PLACES)
def test_minus_zero_at_an_integer_place_is_refused(place):
    path = INTEGER_PLACES[place]
    content = spelt(example(), path, b"-0")
    with pytest.raises(InvalidVerdictFileError):
        parse(content)


@pytest.mark.parametrize("place", ["check ref.round", "against.round"])
def test_minus_zero_where_zero_is_valid_is_refused_by_its_text(place):
    path = INTEGER_PLACES[place]
    assert parse(spelt(example(), path, b"0")) == example()
    message = invalid("verdicts[0]", spelt(example(), path, b"-0"))
    dotted = "verdicts[0].evidence[{}].{}.{}".format(*path[3:])
    assert message == f"{dotted}: is written as -0, which is no integer"


def test_the_first_minus_zero_in_the_order_of_the_text_is_named():
    content = EXAMPLE.replace(b'"round": 0', b'"round": -0')
    message = invalid("verdicts[0]", content)
    assert message.startswith("verdicts[0].evidence[1].ref.round:")


@pytest.mark.parametrize("literal", [b"1.0", b"1e0", b"-1", str(MAX + 1).encode()])
def test_a_number_that_is_no_integer_at_an_integer_place_is_refused(literal):
    invalid("round:", spelt(example(), ("round",), literal))


def test_the_string_minus_zero_is_no_number():
    document = changed(example(), ("verdicts", 0, "cause"), "-0")
    assert parse(raw(document)) == document


def test_the_classes_tell_invalid_from_another_version():
    assert issubclass(InvalidVerdictFileError, ValueError)
    assert not issubclass(UnsupportedVersionError, ValueError)
    assert not issubclass(InvalidVerdictFileError, UnsupportedVersionError)
    assert not issubclass(InvalidVerdictFileError, verdicts.InvalidVerdictRecordError)


def test_the_order_of_the_checks_of_parse():
    cases = [
        ("x", TypeError),
        (b"\xef\xbb\xbf\xff", InvalidVerdictFileError),
        (b"[", InvalidVerdictFileError),
        (b"[2]", InvalidVerdictFileError),
        (b'{"schema_version": 2, "round": -0}', UnsupportedVersionError),
        (b'{"schema_version": 1, "round": -0}', InvalidVerdictFileError),
    ]
    for content, error in cases:
        with pytest.raises(error):
            parse(content)


@pytest.mark.parametrize(
    ("run_id", "round", "file"),
    [
        (RUN_ID, 1, EXAMPLE_FILE),
        ("synthetic-run-1", 12, "runs/synthetic-run-1/rounds/0012/eval/verdicts.json"),
        ("r", 12345, "runs/r/rounds/12345/eval/verdicts.json"),
    ],
)
def test_the_final_name_is_the_path_of_run_id_and_round(run_id, round, file):
    document = changed(example(), ("run_id",), run_id)
    document = changed(document, ("round",), round)
    for place in ((*EVIDENCE, 0, "ref"), (*EVIDENCE, 2, "measured")):
        document = changed(document, (*place, "round"), round)
    assert final_name(Path("root"), document) == Path("root") / file
    assert final_name(Path("root"), document) == layout.verdict_record(
        "root", run_id, round
    )


@pytest.mark.parametrize(
    "document",
    [
        changed(example(), ("round",), 0),
        changed(example(), ("schema_version",), 2),
        changed(example(), ("verdicts",), []),
        [],
        None,
    ],
)
def test_a_document_that_is_no_valid_record_yields_no_path(document):
    with pytest.raises(verdicts.InvalidVerdictRecordError):
        final_name("root", document)


@pytest.mark.parametrize("run_id", ["No Path", "..", "a/b"])
def test_a_valid_document_without_a_run_directory_name_has_no_path(run_id):
    document = changed(example(), ("run_id",), run_id)
    assert parse(raw(document)) == document
    with pytest.raises(layout.InvalidPathValueError):
        final_name("root", document)


@pytest.mark.parametrize("data_root", [None, 7, b"data"])
def test_a_data_root_that_is_no_path_is_a_type_error(data_root):
    with pytest.raises(TypeError):
        final_name(data_root, example())


def test_nothing_is_modified():
    document = example()
    content = raw(document)
    parse(content)
    final_name("root", document)
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
    final_name(tmp_path, parse(EXAMPLE))


TEMPORARY = re.compile(r"verdicts\.json\.[0-9]+-[0-9a-f]{16}\.tmp")
EVAL = f"runs/{RUN_ID}/rounds/0001/eval"
HYPOTHESES = f"runs/{RUN_ID}/rounds/0001/decision/hypotheses.json"
OTHER = raw(changed(example(), ("verdicts", 0, "cause"), "another"))
STEPS = ("creation", "write", "flush", "link")


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


def between(file):
    return {parent.as_posix(): None for parent in Path(file).parents if parent.name}


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
    elif step == "directory":
        monkeypatch.setattr(os, "mkdir", refuse)
    else:
        name = {"flush": "fsync", "link": "link"}[step]
        monkeypatch.setattr(os, name, refuse)


@pytest.mark.parametrize("as_type", [Path, str])
def test_the_example_is_written_byte_for_byte_under_its_final_name(root, as_type):
    assert write(as_type(root), EXAMPLE) is None
    assert snapshot(root) == between(EXAMPLE_FILE) | {EXAMPLE_FILE: EXAMPLE}


def test_existing_directories_are_used_and_others_untouched(root):
    place(root, b"other", f"{EVAL}/eval.json")
    place(root, b"x", f"runs/{RUN_ID}/rounds/0002/eval/verdicts.json")
    before = snapshot(root)

    write(root, EXAMPLE)

    assert snapshot(root) == before | {EXAMPLE_FILE: EXAMPLE}


def test_the_hypotheses_file_of_the_round_is_not_required_read_or_touched(
    root, monkeypatch
):
    place(root, b"not even json", HYPOTHESES)
    before = snapshot(root)
    opened = []
    real = open

    def spy(file, mode="r", *arguments, **named):
        opened.append((Path(file).name, mode))
        return real(file, mode, *arguments, **named)

    monkeypatch.setattr("builtins.open", spy)
    write(root, EXAMPLE)
    monkeypatch.undo()

    ((name, mode),) = opened
    assert TEMPORARY.fullmatch(name) and mode == "xb"
    assert snapshot(root) == before | between(EXAMPLE_FILE) | {EXAMPLE_FILE: EXAMPLE}


def test_white_space_member_order_and_unknown_members_are_written_as_given(root):
    content = (
        b'{"ext": [-0, 1.50, 1E+2],\n "verdicts": '
        + json.dumps(EXAMPLE_DOCUMENT["verdicts"]).encode()
        + b', "round": 1, "run_id": "'
        + RUN_ID.encode()
        + b'",  "schema_version": 1}\n'
    )
    write(root, content)
    assert (root / EXAMPLE_FILE).read_bytes() == content


@pytest.mark.parametrize("previous", [EXAMPLE, OTHER])
def test_a_taken_name_is_reported_and_what_is_there_is_unchanged(root, previous):
    place(root, previous)
    before = snapshot(root)

    with pytest.raises(NameTakenError) as caught:
        write(root, EXAMPLE)

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
        write(root, EXAMPLE)
    monkeypatch.undo()

    ((name, mode),) = opened
    assert TEMPORARY.fullmatch(name) and mode == "xb"


def test_equal_bytes_are_reported_as_other_bytes(root):
    write(root, EXAMPLE)
    reports = []
    for content in (EXAMPLE, OTHER):
        with pytest.raises(NameTakenError) as caught:
            write(root, content)
        reports.append(str(caught.value))

    assert reports[0] == reports[1]
    assert snapshot(root) == between(EXAMPLE_FILE) | {EXAMPLE_FILE: EXAMPLE}


REFUSED = {
    "no bytes": (EXAMPLE.decode(), TypeError),
    "invalid": (EXAMPLE[:20], InvalidVerdictFileError),
    "round 0": (raw(changed(example(), ("round",), 0)), InvalidVerdictFileError),
    "minus zero": (
        EXAMPLE.replace(b'"round": 0', b'"round": -0'),
        InvalidVerdictFileError,
    ),
    "another version": (
        raw(changed(example(), ("schema_version",), 2)),
        UnsupportedVersionError,
    ),
    "no path": (
        raw(changed(example(), ("run_id",), "No Path")),
        layout.InvalidPathValueError,
    ),
    "no final line feed": (EXAMPLE[:-1], WrittenFormError),
    "carriage return": (EXAMPLE.replace(b"\n", b"\r\n"), WrittenFormError),
}


@pytest.mark.parametrize(("content", "error"), REFUSED.values(), ids=REFUSED)
def test_a_refused_content_creates_and_changes_nothing(root, content, error):
    with pytest.raises(error) as caught:
        write(root, content)

    assert type(caught.value) is error
    assert snapshot(root) == {}


def test_the_written_form_errors_name_the_rule():
    with pytest.raises(WrittenFormError, match="does not end with a line feed"):
        write("absent", EXAMPLE[:-1])
    with pytest.raises(WrittenFormError, match="holds a carriage return byte"):
        write("absent", b"\r" + EXAMPLE)
    assert issubclass(WrittenFormError, ValueError)
    assert not issubclass(WrittenFormError, InvalidVerdictFileError)
    assert not issubclass(NameTakenError, (OSError, ValueError))


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_missing_data_root_is_not_created(tmp_path, as_type):
    with pytest.raises(FileNotFoundError, match="data root"):
        write(as_type(tmp_path / "absent"), EXAMPLE)

    assert snapshot(tmp_path) == {}


@pytest.mark.parametrize("as_type", [Path, str])
def test_a_file_in_the_place_of_the_data_root(tmp_path, as_type):
    place(tmp_path, b"a file", "data")

    with pytest.raises(NotADirectoryError, match="data root"):
        write(as_type(tmp_path / "data"), EXAMPLE)

    assert snapshot(tmp_path) == {"data": b"a file"}


@pytest.mark.parametrize("data_root", [None, 7, b"data"])
def test_write_with_a_data_root_that_is_no_path(data_root):
    with pytest.raises(TypeError):
        write(data_root, EXAMPLE)


def test_the_order_of_the_checks_of_write(tmp_path):
    absent = tmp_path / "absent"
    file = place(tmp_path, b"a file", "file")
    no_path = raw(changed(example(), ("run_id",), "No Path"))
    cases = [
        (None, None, TypeError),
        (None, EXAMPLE[:20], InvalidVerdictFileError),
        (None, b'{"schema_version": 2}', UnsupportedVersionError),
        (
            absent,
            raw(changed(example(), ("round",), 0)) + b"\r",
            InvalidVerdictFileError,
        ),
        (absent, no_path[:-1], layout.InvalidPathValueError),
        (None, EXAMPLE[:-1], TypeError),
        (absent, EXAMPLE[:-1], WrittenFormError),
        (file, b"\r" + EXAMPLE, WrittenFormError),
        (absent, EXAMPLE, FileNotFoundError),
        (file, EXAMPLE, NotADirectoryError),
    ]

    for data_root, content, error in cases:
        with pytest.raises(error) as caught:
            write(data_root, content)
        assert type(caught.value) is error

    assert snapshot(tmp_path) == {"file": b"a file"}


@pytest.mark.parametrize("name", ["runs", f"runs/{RUN_ID}/rounds", EVAL])
def test_a_file_in_the_place_of_a_directory_above_the_final_name(root, name):
    place(root, b"a file", name)
    before = snapshot(root)

    with pytest.raises(OSError):
        write(root, EXAMPLE)

    assert snapshot(root) == before


def test_a_failed_creation_of_a_directory_creates_nothing_further(root, monkeypatch):
    error = OSError("mkdir refused")
    break_step(monkeypatch, "directory", error)

    with pytest.raises(OSError) as caught:
        write(root, EXAMPLE)
    monkeypatch.undo()

    assert caught.value is error
    assert snapshot(root) == {}


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
        write(root, EXAMPLE)
    monkeypatch.undo()

    assert caught.value is error
    assert snapshot(root) == before | between(EXAMPLE_FILE)
    assert temporaries(root) == []


@pytest.mark.parametrize("step", STEPS[1:])
def test_an_interrupt_removes_the_temporary_file_too(root, monkeypatch, step):
    break_step(monkeypatch, step, Stop())

    with pytest.raises(Stop):
        write(root, EXAMPLE)
    monkeypatch.undo()

    assert snapshot(root) == between(EXAMPLE_FILE)


def test_a_leftover_of_another_write_is_not_touched(root):
    leftover = f"{EVAL}/verdicts.json.4242-0123456789abcdef.tmp"
    place(root, b"of another writer", leftover)

    write(root, EXAMPLE)

    assert snapshot(root) == between(EXAMPLE_FILE) | {
        leftover: b"of another writer",
        EXAMPLE_FILE: EXAMPLE,
    }


def test_the_temporary_file_is_in_the_eval_directory(root, monkeypatch):
    sources = []
    give = os.link

    def linking(source, target):
        sources.append((Path(source), Path(target)))
        return give(source, target)

    monkeypatch.setattr(os, "link", linking)
    write(root, EXAMPLE)
    monkeypatch.undo()

    ((source, target),) = sources
    assert TEMPORARY.fullmatch(source.name)
    assert source.parent == target.parent == root / EVAL
    assert target == root / EXAMPLE_FILE


def test_a_temporary_name_in_use_is_an_error_and_that_file_stays(root, monkeypatch):
    monkeypatch.setattr(secrets, "token_hex", lambda size: "0" * 2 * size)
    name = f"{EVAL}/verdicts.json.{os.getpid()}-{'0' * 16}.tmp"
    place(root, b"of another writer", name)
    before = snapshot(root)

    with pytest.raises(FileExistsError) as caught:
        write(root, EXAMPLE)

    assert not isinstance(caught.value, NameTakenError)
    assert snapshot(root) == before


def test_the_public_names():
    public = sorted(name for name in vars(verdicts_file) if not name.startswith("_"))
    assert public == [
        "InvalidVerdictFileError",
        "NameTakenError",
        "Path",
        "UnsupportedVersionError",
        "WrittenFormError",
        "codecs",
        "final_name",
        "json",
        "json_text",
        "keys",
        "layout",
        "once_write",
        "parse",
        "verdicts",
        "write",
    ]
