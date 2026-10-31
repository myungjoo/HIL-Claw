import copy
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    contract_table,
    instance,
    instance_start,
    keys,
    model_instances,
    new_run,
    nightly,
    standin_image,
    standin_profile,
)
from hilclaw.model_instances import (
    KINDS,
    RefusedValuesError,
    documents,
    main,
    op_records,
)
from hilclaw.start_instance import _ACCELERATORS

IMAGE = "example.invalid/standin:0"
ENVIRON = {standin_image.ENV_IMAGE: IMAGE}
PROFILE = {
    "schema_version": 1,
    "accelerator": "cpu_standin",
    "revision": "host",
    "toolchain": {"clang": "Example clang version 0.0.0"},
    "host": {"cpu": "Example CPU", "os": "linux exampleos 0.0"},
    "hw_source": "external",
}
SHAPES = {
    "gemm": {"m": 3, "k": 8, "n": 12},
    "rmsnorm": {"m": 3, "n": 8},
    "elementwise_add": {"m": 3, "n": 8},
    "swiglu": {"m": 3, "n": 12},
    "rope": {"m": 3, "h": 4, "d": 4},
    "sdpa_kv_cache": {"m": 1, "l": 4, "h": 4, "h_kv": 2, "d": 4},
}


def values():
    return {
        "n_max": 7,
        "draws": 2,
        "round_budget": 3,
        "kinds": {
            kind: {**shape, "rtol": 0.25, "atol": 0.5} for kind, shape in SHAPES.items()
        },
    }


class Reader:
    def __init__(self, answer=PROFILE, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def __call__(self, hw_source, *, timeout_s, image):
        self.calls.append((hw_source, timeout_s, image))
        if self.error is not None:
            raise self.error
        return copy.deepcopy(self.answer)


class Directories:
    def __init__(self, tmp_path):
        self.input = tmp_path / "input"
        self.output = tmp_path / "output"
        self.input.mkdir()
        self.output.mkdir()

    def file(self, content):
        path = self.input / "values.json"
        if not isinstance(content, bytes):
            content = json.dumps(content).encode("utf-8")
        path.write_bytes(content)
        return str(path)


@pytest.fixture
def places(tmp_path):
    return Directories(tmp_path)


def run(args, reader=None, environ=ENVIRON):
    stdout = io.BytesIO()
    stderr = io.BytesIO()
    status = main(
        [str(arg) for arg in args],
        profile=reader or Reader(),
        environ=environ,
        stdout=stdout,
        stderr=stderr,
    )
    assert stderr.getvalue() == b""
    line = stdout.getvalue()
    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    return status, json.loads(line)


def refused(places, given, word="must", outcome="refused_values", status=11):
    reader = Reader()
    got, told = run([places.file(given), places.output], reader)
    assert (got, told["outcome"]) == (status, outcome)
    assert word in told["reason"]
    assert list(places.output.iterdir()) == []
    return reader, told


def changed(path, value):
    given = values()
    place = given
    for name in path[:-1]:
        place = place[name]
    place[path[-1]] = value
    return given


def removed(path):
    given = values()
    place = given
    for name in path[:-1]:
        place = place[name]
    del place[path[-1]]
    return given


def test_the_kinds_are_the_six_bf16_ones():
    assert set(KINDS) == set(SHAPES)
    assert len(KINDS) == 6


@pytest.mark.parametrize("kind", SHAPES)
def test_each_kind_gives_a_document_the_start_accepts(places, kind):
    reader = Reader()
    status, told = run([places.file(values()), places.output], reader)
    assert status == 0
    assert told["outcome"] == "written"
    assert told["files"] == [str(places.output / f"{name}.json") for name in KINDS]
    assert reader.calls == [("external", nightly.PROFILE_TIMEOUT_S, IMAGE)]

    raw = (places.output / f"{kind}.json").read_bytes()
    document = json.loads(raw)
    assert instance.parse(raw).round_budget == 3
    prepared = instance_start.prepare(
        document, accelerators=_ACCELERATORS, covers=contract_table.start_covers
    )
    assert prepared["candidates_per_round"] == 1
    assert prepared["objective"] == {
        "objectives": [{"type": "latency_minimisation"}],
        "constraints": [],
    }
    record = document["op_signature"]["record"]
    assert record["kind"] == kind
    assert record["dtype"] == "bf16"
    assert record["shape"] == SHAPES[kind]
    assert document["op_signature"]["key"] == keys.op_signature_key(record).name
    assert document["hw_profile"] == {
        "key": keys.hw_profile_key(PROFILE).name,
        "record": PROFILE,
    }
    assert document["tolerance"] == {"rtol": 0.25, "atol": 0.5}
    assert (document["n_max"], document["draws"], document["round_budget"]) == (7, 2, 3)
    assert "coder_model" not in document


def test_a_document_goes_through_the_new_run_entry(places, tmp_path):
    run([places.file(values()), places.output])
    root = tmp_path / "root"
    root.mkdir()
    stdout = io.BytesIO()
    status = new_run.main(
        [str(places.output / "rope.json")],
        source=lambda: str(root),
        stdout=stdout,
        stderr=io.BytesIO(),
    )
    assert status == 0, stdout.getvalue()
    assert json.loads(stdout.getvalue())["outcome"] == "started"


def test_two_shapes_of_one_kind_give_different_keys():
    first = documents(values(), PROFILE)["gemm"]
    other = changed(("kinds", "gemm", "n"), 16)
    second = documents(other, PROFILE)["gemm"]
    assert first["op_signature"]["key"] != second["op_signature"]["key"]
    assert first["hw_profile"]["key"] == second["hw_profile"]["key"]


def test_op_records_gives_the_contract_record_of_each_kind():
    given = values()
    before = copy.deepcopy(given)
    records = op_records(given)
    assert given == before
    assert list(records) == list(KINDS)
    for kind, record in records.items():
        contract = model_instances.CONTRACTS[kind]
        assert contract.covers(record)
        assert record == contract.op_signature_record(**SHAPES[kind])


@pytest.mark.parametrize(
    ("given", "word"),
    [
        (removed(("n_max",)), "n_max"),
        (removed(("draws",)), "draws"),
        (removed(("round_budget",)), "round_budget"),
        (removed(("kinds",)), "kinds"),
        (changed(("target",), 1), "target"),
        (changed(("kinds",), []), "object"),
        (removed(("kinds", "rope")), "rope"),
        (changed(("kinds", "lm_head"), {}), "lm_head"),
        (changed(("kinds", "gemm"), 1), "object"),
        (removed(("kinds", "gemm", "k")), "'k'"),
        (removed(("kinds", "swiglu", "rtol")), "rtol"),
        (removed(("kinds", "swiglu", "atol")), "atol"),
        (changed(("kinds", "rmsnorm", "k"), 1), "'k'"),
        (changed(("kinds", "gemm", "m"), 0), "shape.m"),
        (changed(("kinds", "gemm", "m"), 1.0), "shape.m"),
        (changed(("kinds", "gemm", "m"), True), "shape.m"),
        (changed(("kinds", "gemm", "m"), "<m>"), "shape.m"),
        (changed(("kinds", "rope", "d"), 3), "shape.d"),
        (changed(("kinds", "sdpa_kv_cache", "l"), 0), "shape.l"),
        (changed(("kinds", "sdpa_kv_cache", "h_kv"), 3), "h_kv"),
    ],
)
def test_a_refused_member_starts_no_container_and_writes_nothing(places, given, word):
    reader, _ = refused(places, given, word)
    assert reader.calls == []


def test_a_values_file_of_a_list_is_bad_input(places):
    refused(places, [1], "no object", "bad_input", 22)


@pytest.mark.parametrize(
    ("path", "value", "word"),
    [
        (("n_max",), 4, "n_max"),
        (("n_max",), None, "n_max"),
        (("n_max",), 10.0, "n_max"),
        (("draws",), 0, "draws"),
        (("draws",), True, "draws"),
        (("round_budget",), 0, "round_budget"),
        (("round_budget",), "5", "round_budget"),
        (("kinds", "gemm", "rtol"), -1, "tolerance.rtol"),
        (("kinds", "rope", "atol"), True, "tolerance.atol"),
        (("kinds", "swiglu", "atol"), "<atol>", "tolerance.atol"),
    ],
)
def test_a_value_out_of_range_is_refused_with_nothing_written(
    places, path, value, word
):
    refused(places, changed(path, value), word)


def test_an_infinite_tolerance_is_refused(places):
    text = json.dumps(values()).replace('"rtol": 0.25', '"rtol": 1e400', 1)
    refused(places, text.encode("utf-8"), "tolerance.rtol")


def test_a_covers_of_the_start_that_refuses_is_refused(places, monkeypatch):
    monkeypatch.setattr(contract_table, "start_covers", lambda record: False)
    refused(places, values(), "ADR-0041")


def test_a_contract_that_does_not_cover_its_own_record_is_refused(monkeypatch):
    contract = model_instances.CONTRACTS["gemm"]
    monkeypatch.setattr(contract, "covers", lambda record: False)
    with pytest.raises(RefusedValuesError, match="does not cover"):
        op_records(values())


def test_documents_refuses_a_bad_profile():
    with pytest.raises(RefusedValuesError, match="kinds.gemm"):
        documents(values(), {"accelerator": "cpu_standin"})


def test_documents_refuses_as_op_records_does():
    with pytest.raises(RefusedValuesError, match="kinds"):
        documents(removed(("kinds",)), PROFILE)


def test_an_unreadable_file(places):
    status, told = run([places.input / "absent.json", places.output])
    assert (status, told["outcome"]) == (21, "unreadable_input")
    assert list(places.output.iterdir()) == []


@pytest.mark.parametrize(
    "content",
    [
        b"{",
        b"\xff",
        b"\xef\xbb\xbf{}",
        b'{"n_max": NaN}',
        b'{"n_max": 1, "n_max": 2}',
    ],
)
def test_malformed_json(places, content):
    status, told = run([places.file(content), places.output])
    assert (status, told["outcome"]) == (22, "bad_input")
    assert list(places.output.iterdir()) == []


@pytest.mark.parametrize("count", [0, 1, 3])
def test_bad_usage(places, count):
    status, told = run([places.output] * count)
    assert (status, told["outcome"]) == (20, "bad_usage")


def test_an_existing_output_file_is_refused_and_kept(places):
    there = places.output / "swiglu.json"
    there.write_bytes(b"mine")
    reader = Reader()
    status, told = run([places.file(values()), places.output], reader)
    assert (status, told) == (14, {"outcome": "output_exists", "files": [str(there)]})
    assert there.read_bytes() == b"mine"
    assert [path.name for path in places.output.iterdir()] == ["swiglu.json"]
    assert reader.calls == []


def test_an_output_directory_that_is_absent(places):
    reader = Reader()
    absent = places.output / "absent"
    status, told = run([places.file(values()), absent], reader)
    assert (status, told["outcome"]) == (15, "no_output_directory")
    assert not absent.exists()
    assert reader.calls == []


def test_an_output_directory_that_is_a_file(places):
    status, told = run([places.file(values()), places.input / "values.json"])
    assert (status, told["outcome"]) == (15, "no_output_directory")


@pytest.mark.parametrize(
    "error",
    [
        standin_profile.UnreadableFactError("toolchain.clang: no"),
        OSError("no"),
        ValueError("no"),
    ],
)
def test_a_failing_profile(places, error):
    status, told = run([places.file(values()), places.output], Reader(error=error))
    assert (status, told["outcome"]) == (13, "hw_profile")
    assert list(places.output.iterdir()) == []


def test_a_profile_that_is_no_record(places):
    reader = Reader(answer={"accelerator": "cpu_standin"})
    status, told = run([places.file(values()), places.output], reader)
    assert (status, told["outcome"]) == (13, "hw_profile")
    assert list(places.output.iterdir()) == []


@pytest.mark.parametrize(
    ("environ", "word"),
    [
        ({}, "is not set"),
        ({standin_image.ENV_IMAGE: ""}, "is not set"),
        ({standin_image.ENV_IMAGE: "-x"}, "must not begin"),
    ],
)
def test_no_image_starts_no_container(places, environ, word):
    reader = Reader()
    status, told = run([places.file(values()), places.output], reader, environ)
    assert (status, told["outcome"]) == (12, "no_standin_image")
    assert word in told["reason"]
    assert reader.calls == []
    assert list(places.output.iterdir()) == []


def test_a_write_that_fails_removes_what_this_call_wrote(places, monkeypatch):
    real = open
    opened = []

    def failing(path, *arguments, **options):
        if str(path).endswith(".json") and arguments and arguments[0] == "xb":
            opened.append(path)
            if len(opened) == 3:
                raise OSError("disk full")
        return real(path, *arguments, **options)

    monkeypatch.setattr("builtins.open", failing)
    status, told = run([places.file(values()), places.output])
    assert (status, told["outcome"]) == (16, "file_system")
    assert list(places.output.iterdir()) == []


def test_a_file_that_appears_during_the_write_is_kept(places, monkeypatch):
    real = open
    there = places.output / f"{KINDS[1]}.json"

    def appearing(path, *arguments, **options):
        if str(path) == str(there) and arguments and arguments[0] == "xb":
            there.write_bytes(b"mine")
        return real(path, *arguments, **options)

    monkeypatch.setattr("builtins.open", appearing)
    status, told = run([places.file(values()), places.output])
    assert (status, told["outcome"]) == (14, "output_exists")
    assert told["files"] == [str(there)]
    assert [path.name for path in places.output.iterdir()] == [there.name]
    assert there.read_bytes() == b"mine"


def test_an_unexpected_exception_is_a_fault(places):
    status, told = run(
        [places.file(values()), places.output], Reader(error=KeyError("x"))
    )
    assert (status, told) == (24, {"outcome": "fault", "fault": "KeyError"})
    assert list(places.output.iterdir()) == []


def test_no_standard_output_is_said_on_standard_error(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    stderr = io.BytesIO()
    assert main([], stderr=stderr) == 24
    assert b"no standard output" in stderr.getvalue()


class Partial(io.BytesIO):
    def write(self, data):
        return 0


def test_a_line_that_cannot_be_written_is_said_on_standard_error():
    stderr = io.BytesIO()
    assert main([], stdout=Partial(), stderr=stderr) == 24
    assert b"cannot write standard output" in stderr.getvalue()


def test_the_command_line_runs_as_a_module(places):
    env = {k: v for k, v in os.environ.items() if k != standin_image.ENV_IMAGE}
    done = subprocess.run(
        [
            sys.executable,
            "-m",
            "hilclaw.model_instances",
            places.file(values()),
            str(places.output),
        ],
        env=env,
        cwd=Path(model_instances.__file__).parent.parent,
        capture_output=True,
        check=False,
    )
    assert done.returncode == 12
    assert json.loads(done.stdout)["outcome"] == "no_standin_image"
    assert list(places.output.iterdir()) == []
