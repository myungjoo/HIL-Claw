import codecs
import inspect
import json
from pathlib import Path

import pytest
import test_spec_file as spec_files

from hilclaw import build_record, check_failure, kernel_source, keys, layout
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
        "CandidateBuild",
        "Evaluated",
        "InvalidBuildRecordError",
        "KernelRefused",
        "MissingBuildRecordError",
        "OUTCOMES",
        "SCHEMA_VERSION",
        "UnsupportedVersionError",
        "building",
        "current",
        "evaluated",
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


# --- the writer (ADR-0198 decisions 2, 5 and 6) ---

KERNEL = (0, 1, 1)
CANDIDATE = (1, 1, 1)
CANDIDATE_FLAGS = ("-O3", "-funroll-loops")


def spec_document(run_id, numbers, *, named=None, flags=CANDIDATE_FLAGS):
    round, candidate, attempt = numbers
    made = spec_files.minimal()
    made["id"].update(run_id=run_id, round=round, candidate=candidate, attempt=attempt)
    if candidate > 1:
        made["id"].update(
            candidates=candidate, relation="same_technique", variant="synthetic"
        )
    if attempt > 1:
        failure = {"attempt": attempt - 1, "stage": "compile", "report": "synthetic"}
        made["repair"] = {"failures": [failure]}
    if named is not None:
        made["schema_version"] = 3
        made["task"]["build"] = {
            "candidate_kind": "compile_settings",
            "flags": list(flags),
            "kernel_round": named[0],
            "kernel_candidate": named[1],
            "kernel_attempt": named[2],
        }
    return made


def place_spec(root, run_id, numbers, made=None, *, content=None, **changes):
    if content is None:
        made = spec_document(run_id, numbers, **changes) if made is None else made
        content = (json.dumps(made, indent=2) + "\n").encode()
    path = layout.attempt_artefact(root, run_id, *numbers, "spec.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def place_kernel(root, run_id, numbers, names=("k.c",)):
    output = layout.attempt_artefact(root, run_id, *numbers, "output")
    output.mkdir(parents=True, exist_ok=True)
    for name in names:
        (output / name).write_bytes(b"void k(void) {}\n")
    return output


def a_candidate(root, run_id=RUN, numbers=CANDIDATE, named=KERNEL, **changes):
    place_spec(root, run_id, named)
    place_kernel(root, run_id, named)
    place_spec(root, run_id, numbers, named=named, **changes)
    return root


def build_path(root, numbers=CANDIDATE):
    return layout.attempt_artefact(root, RUN, *numbers, "build.json")


def test_evaluated_follows_a_version_3_spec_to_the_named_kernel(tmp_path):
    a_candidate(tmp_path)
    answer = build_record.evaluated(tmp_path, RUN, *CANDIDATE)
    assert type(answer) is build_record.Evaluated
    assert answer.output_path == layout.attempt_artefact(
        tmp_path, RUN, *KERNEL, "output"
    )
    assert type(answer.build) is build_record.CandidateBuild
    assert answer.build.flags == CANDIDATE_FLAGS
    assert answer.build.path == build_path(tmp_path)
    assert answer.build.document is None
    assert not build_path(tmp_path).exists()


def test_evaluated_follows_a_kernel_of_any_earlier_coder_attempt(tmp_path):
    a_candidate(tmp_path, numbers=(4, 2, 1), named=(2, 3, 2), flags=())
    answer = build_record.evaluated(tmp_path, RUN, 4, 2, 1)
    assert answer.output_path == layout.attempt_artefact(
        tmp_path, RUN, 2, 3, 2, "output"
    )
    assert answer.build.flags == ()


def test_evaluated_keeps_a_version_2_attempt_as_it_is_and_reads_no_output(
    tmp_path, monkeypatch
):
    place_spec(tmp_path, RUN, KERNEL)
    monkeypatch.setattr(build_record.kernel_source, "read_compiled_set", pytest.fail)
    answer = build_record.evaluated(tmp_path, RUN, *KERNEL)
    assert answer == (layout.attempt_artefact(tmp_path, RUN, *KERNEL, "output"), None)


NO_KERNEL = check_failure.KIND_NO_KERNEL_SOURCE
UNREADABLE = check_failure.KIND_KERNEL_SOURCE_UNREADABLE


def no_spec(root):
    place_kernel(root, RUN, CANDIDATE)


def invalid_spec(root):
    place_spec(root, RUN, CANDIDATE, content=b"not json")


def version_4_spec(root):
    made = spec_document(RUN, CANDIDATE)
    made["schema_version"] = 4
    place_spec(root, RUN, CANDIDATE, made)


def spec_of_another_attempt(root):
    place_spec(root, RUN, CANDIDATE, spec_document(RUN, (1, 2, 1)))


def named_version_3(root):
    place_spec(root, RUN, (0, 1, 1))
    place_spec(root, RUN, (1, 1, 1), named=(0, 1, 1))
    place_spec(root, RUN, (2, 1, 1), named=(1, 1, 1))


def named_without_spec(root):
    place_kernel(root, RUN, KERNEL)
    place_spec(root, RUN, CANDIDATE, named=KERNEL)


def named_without_compiled_set(root):
    a_candidate(root)
    output = layout.attempt_artefact(root, RUN, *KERNEL, "output")
    (output / "k.c").unlink()
    (output / "k.h").write_bytes(b"void k(void);\n")


def named_without_output(root):
    place_spec(root, RUN, KERNEL)
    place_spec(root, RUN, CANDIDATE, named=KERNEL)


@pytest.mark.parametrize(
    ("made", "kind", "reason", "numbers"),
    [
        (no_spec, NO_KERNEL, "no_spec_file", CANDIDATE),
        (invalid_spec, UNREADABLE, "spec_invalid", CANDIDATE),
        (version_4_spec, NO_KERNEL, "spec_other_version", CANDIDATE),
        (spec_of_another_attempt, UNREADABLE, "spec_other_attempt", CANDIDATE),
        (named_version_3, NO_KERNEL, "spec_other_version", (2, 1, 1)),
        (named_without_spec, NO_KERNEL, "no_spec_file", CANDIDATE),
        (named_without_compiled_set, NO_KERNEL, "no_compiled_file", CANDIDATE),
        (named_without_output, NO_KERNEL, "no_output_directory", CANDIDATE),
    ],
)
def test_evaluated_refuses_an_attempt_that_gives_no_kernel(
    tmp_path, made, kind, reason, numbers
):
    made(tmp_path)
    with pytest.raises(build_record.KernelRefused) as raised:
        build_record.evaluated(tmp_path, RUN, *numbers)
    assert (raised.value.kind, raised.value.message) == (
        kind,
        f"the attempt gives no kernel to build: {reason}",
    )
    assert raised.value.__cause__ is None
    assert str(tmp_path) not in raised.value.message
    assert not list(tmp_path.rglob("build.json"))


def test_evaluated_refuses_a_reader_failure_as_unreadable(tmp_path, monkeypatch):
    a_candidate(tmp_path)

    def failing(output_path):
        raise kernel_source.KernelSourceReadError(
            kernel_source.OUTPUT_DIRECTORY_UNLISTABLE
        )

    monkeypatch.setattr(build_record.kernel_source, "read_compiled_set", failing)
    with pytest.raises(build_record.KernelRefused) as raised:
        build_record.evaluated(tmp_path, RUN, *CANDIDATE)
    assert raised.value.kind == UNREADABLE
    assert raised.value.message.endswith("output_directory_unlistable")


def test_evaluated_refuses_an_unreadable_spec(tmp_path, monkeypatch):
    a_candidate(tmp_path)

    def broken(*arguments, **keywords):
        raise OSError(5, "input/output error")

    monkeypatch.setattr(build_record.attempt_kernel, "open", broken, raising=False)
    with pytest.raises(build_record.KernelRefused) as raised:
        build_record.evaluated(tmp_path, RUN, *CANDIDATE)
    assert raised.value.message.endswith("spec_unreadable")
    assert raised.value.kind == UNREADABLE


def test_evaluated_passes_a_malformed_argument(tmp_path):
    with pytest.raises(layout.InvalidPathValueError):
        build_record.evaluated(tmp_path, RUN, 1, 0, 1)


def test_kernel_refused_holds_its_kind_and_message():
    refused = build_record.KernelRefused("no_kernel_source", "text")
    assert (refused.kind, refused.message) == ("no_kernel_source", "text")
    assert isinstance(refused, Exception)


def test_a_candidate_build_keeps_the_first_build_it_is_told(tmp_path):
    build = build_record.CandidateBuild(tmp_path / "build.json", ("-O3",))
    assert (build.flags, build.document) == (("-O3",), None)
    assert repr(build) == "<CandidateBuild of 1 flags>"
    assert "-O3" not in repr(build)
    build.ended("build_exit_status", ("-O2", "-O3"), ("-lm",))
    expected = {
        "schema_version": 1,
        "outcome": "broken",
        "condition": "build_exit_status",
        "flags": ["-O2", "-O3"],
        "trailing_flags": ["-lm"],
    }
    assert build.document == expected
    build.ended(None, ("-O0",), ())
    assert build.document == expected


@pytest.mark.parametrize(
    ("condition", "flags", "trailing"),
    [("time_limit", (), ()), (None, ("",), ()), (None, (), ("a\0",))],
)
def test_a_candidate_build_refuses_what_validate_refuses(
    tmp_path, condition, flags, trailing
):
    build = build_record.CandidateBuild(tmp_path / "build.json", ())
    with pytest.raises(build_record.InvalidBuildRecordError):
        build.ended(condition, flags, trailing)
    assert build.document is None


@pytest.mark.parametrize(
    ("path", "flags"),
    [("build.json", ()), (None, ()), (Path("b"), ["-O2"]), (Path("b"), (b"-O2",))],
)
def test_a_candidate_build_refuses_a_bad_argument(path, flags):
    with pytest.raises(TypeError):
        build_record.CandidateBuild(path, flags)


def test_the_write_gives_the_name_once_and_read_reads_it(tmp_path):
    a_candidate(tmp_path)
    first = build_record.CandidateBuild(build_path(tmp_path), ())
    assert first.write() is False
    assert not build_path(tmp_path).exists()
    first.ended(None, ("-O2",), ("-lm",))
    assert first.write() is True
    content = build_path(tmp_path).read_bytes()
    assert content.endswith(b"}\n")
    assert build_record.read(tmp_path, RUN, *CANDIDATE) == (
        "built",
        None,
        ["-O2"],
        ["-lm"],
    )
    later = build_record.CandidateBuild(build_path(tmp_path), ())
    later.ended("build_time_limit", ("-O3",), ())
    assert later.write() is False
    assert build_path(tmp_path).read_bytes() == content
    assert [p.name for p in build_path(tmp_path).parent.iterdir()] == ["build.json"]


def test_a_write_that_fails_is_not_answered(tmp_path):
    (tmp_path / "blocked").write_bytes(b"")
    build = build_record.CandidateBuild(tmp_path / "blocked" / "build.json", ())
    build.ended(None, (), ())
    assert build.write() is False


def test_building_makes_a_build_current_inside_the_block_only(tmp_path):
    assert build_record.current() is None
    build = build_record.CandidateBuild(tmp_path / "build.json", ())
    with build_record.building(build) as held:
        assert held is build
        assert build_record.current() is build
        with build_record.building(None):
            assert build_record.current() is None
        assert build_record.current() is build
    assert build_record.current() is None
    with pytest.raises(RuntimeError), build_record.building(build):
        raise RuntimeError
    assert build_record.current() is None


def test_building_refuses_another_object():
    with pytest.raises(TypeError), build_record.building(object()):
        pass
    assert build_record.current() is None


def test_a_build_is_current_in_its_own_thread_only(tmp_path):
    import threading

    seen = []
    build = build_record.CandidateBuild(tmp_path / "build.json", ())
    with build_record.building(build):
        thread = threading.Thread(target=lambda: seen.append(build_record.current()))
        thread.start()
        thread.join()
    assert seen == [None]
