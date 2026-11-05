import codecs
import inspect
import json

import pytest

from hilclaw import build_record, keys, layout
from hilclaw.build_record import (
    BuildRecord,
    InvalidBuildRecordError,
    MissingBuildRecordError,
    UnsupportedVersionError,
    parse,
    read,
    validate,
)

RUN = "synthetic-run-1"
FILE = f"runs/{RUN}/rounds/0002/measure/candidates/01/attempts/01/build.json"
REMOVE = object()


def doc(**changes):
    made = {
        "schema_version": 1,
        "outcome": "built",
        "flags": ["-std=gnu11", "-O2", "-ffp-contract=off", "-O3"],
        "trailing_flags": ["-lm"],
    }
    for name, value in changes.items():
        if value is REMOVE:
            del made[name]
        else:
            made[name] = value
    return made


def raw(document):
    return json.dumps(document).encode()


def invalid(place, document):
    with pytest.raises(InvalidBuildRecordError) as caught:
        validate(document)
    assert str(caught.value).startswith(place), str(caught.value)
    with pytest.raises(InvalidBuildRecordError):
        parse(raw(document))
    return str(caught.value)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


def place(root, content):
    path = root / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_the_public_names():
    public = sorted(
        name
        for name, value in vars(build_record).items()
        if not name.startswith("_")
        and getattr(value, "__module__", build_record.__name__) == build_record.__name__
        and not inspect.ismodule(value)
    )
    assert public == [
        "BuildRecord",
        "CONDITIONS",
        "InvalidBuildRecordError",
        "MissingBuildRecordError",
        "OUTCOMES",
        "SCHEMA_VERSION",
        "UnsupportedVersionError",
        "parse",
        "read",
        "validate",
    ]
    assert build_record.SCHEMA_VERSION == 1
    assert build_record.OUTCOMES == ("built", "broken")
    assert build_record.CONDITIONS == ("build_time_limit", "build_exit_status")
    assert BuildRecord._fields == ("outcome", "condition", "flags", "trailing_flags")
    assert issubclass(InvalidBuildRecordError, ValueError)
    assert not issubclass(UnsupportedVersionError, ValueError)


def test_a_built_record_is_read_as_it_states():
    document = doc()

    assert validate(document) is None
    assert parse(raw(document)) == BuildRecord(
        "built", None, document["flags"], ["-lm"]
    )


@pytest.mark.parametrize("condition", ["build_time_limit", "build_exit_status"])
def test_a_broken_record_states_its_condition(condition):
    document = doc(outcome="broken", condition=condition, flags=[], trailing_flags=[])

    assert parse(raw(document)) == BuildRecord("broken", condition, [], [])


@pytest.mark.parametrize("version", [0, 2, 4, keys.MAX_INTEGER])
def test_another_version_is_reported_before_any_other_member(version):
    for function in (validate, lambda d: parse(raw(d))):
        with pytest.raises(
            UnsupportedVersionError, match=f"^schema_version: {version} is"
        ):
            function({"schema_version": version, "outcome": 7})


@pytest.mark.parametrize("value", [-1, keys.MAX_INTEGER + 1, True, 1.0, "1", None])
def test_a_version_that_is_no_integer_is_invalid(value):
    invalid("schema_version: must be an int", doc(schema_version=value))


def test_the_document_must_be_an_object_with_a_version():
    invalid("document: must be an object", [1])
    invalid("document: lacks the member schema_version", doc(schema_version=REMOVE))


@pytest.mark.parametrize("name", ["outcome", "flags", "trailing_flags"])
def test_each_member_is_required(name):
    invalid(f"document: lacks the member {name}", doc(**{name: REMOVE}))


def test_no_other_member_is_admitted():
    invalid("document: must be an object without the member, got 'step'", doc(step="x"))


@pytest.mark.parametrize("value", ["Built", "failed", "", None, 1, ["built"]])
def test_an_outcome_outside_the_list_is_invalid(value):
    invalid("outcome: must be built or broken", doc(outcome=value))


def test_a_condition_with_built_is_invalid():
    invalid("condition: must be absent", doc(condition="build_exit_status"))


def test_broken_without_a_condition_is_invalid():
    invalid("document: lacks the member condition", doc(outcome="broken"))


@pytest.mark.parametrize("value", ["time_limit", "exit_status", "", None, 1])
def test_a_condition_outside_the_list_is_invalid(value):
    invalid(
        "condition: must be build_time_limit or build_exit_status",
        doc(outcome="broken", condition=value),
    )


@pytest.mark.parametrize("name", ["flags", "trailing_flags"])
@pytest.mark.parametrize("value", ["-O3", None, {"a": 1}])
def test_the_arguments_must_be_an_array(name, value):
    invalid(f"{name}: must be an array", doc(**{name: value}))


def test_a_tuple_built_in_memory_is_no_array():
    with pytest.raises(InvalidBuildRecordError, match="^flags: must be an array"):
        validate(doc(flags=("-O3",)))


@pytest.mark.parametrize("name", ["flags", "trailing_flags"])
@pytest.mark.parametrize("item", ["", "a\0b", 1, None, ["-O3"]])
def test_each_argument_is_a_string_of_at_least_one_character(name, item):
    invalid(f"{name}[1]: must be a str", doc(**{name: ["-x", item]}))


def test_the_text_rules():
    with pytest.raises(TypeError):
        parse("{}")
    for content, reason in [
        (codecs.BOM_UTF8 + raw(doc()), "content: starts with a byte order mark"),
        (b"", "content: cannot be read as one JSON text"),
        (b"\xff", "content: cannot be read as one JSON text"),
        (b'{"outcome": "built", "outcome": "built"}', "content: cannot be read"),
        (b'{"schema_version": NaN}', "content: cannot be read"),
        (b"[" * 2_000_000 + b"]" * 2_000_000, "content: is nested too deeply"),
    ]:
        with pytest.raises(InvalidBuildRecordError, match=f"^{reason}"):
            parse(content)


def test_read_returns_the_record_of_the_attempt(root):
    place(root, raw(doc()))

    assert read(root, RUN, 2, 1, 1) == parse(raw(doc()))
    assert (root / FILE).read_bytes() == raw(doc())


def test_read_names_the_file_in_its_errors(root):
    with pytest.raises(MissingBuildRecordError, match=f"^{FILE}: is missing"):
        read(root, RUN, 2, 1, 1)
    place(root, raw(doc(outcome="broken")))
    with pytest.raises(InvalidBuildRecordError, match=f"^{FILE}: document: lacks"):
        read(root, RUN, 2, 1, 1)
    place(root, raw(doc(schema_version=2)))
    with pytest.raises(UnsupportedVersionError, match=f"^{FILE}: schema_version: 2"):
        read(root, RUN, 2, 1, 1)


def test_read_refuses_what_is_no_regular_file_and_no_data_root(root, tmp_path):
    (root / FILE).mkdir(parents=True)
    with pytest.raises(
        InvalidBuildRecordError, match=f"^{FILE}: is not a regular file"
    ):
        read(root, RUN, 2, 1, 1)
    with pytest.raises(FileNotFoundError):
        read(tmp_path / "absent", RUN, 2, 1, 1)
    (tmp_path / "plain").write_bytes(b"")
    with pytest.raises(NotADirectoryError):
        read(tmp_path / "plain", RUN, 2, 1, 1)
    with pytest.raises(layout.InvalidPathValueError):
        read(root, "../x", 2, 1, 1)
    with pytest.raises(layout.InvalidPathValueError):
        read(root, RUN, 2, 0, 1)
