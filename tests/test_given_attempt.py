import hashlib
import json
import os

import pytest

from hilclaw import (
    bring_in,
    cas,
    given_attempt,
    keys,
    layout,
    mcp_front,
    run_files,
    standin_profile,
    start_instance,
    tools,
)
from hilclaw.given_attempt import (
    GIVEN_ATTEMPT,
    GIVEN_NAME,
    KIND_GIVEN_CODE_CORRUPT,
    KIND_GIVEN_CODE_MISSING,
    KIND_GIVEN_CODE_NOT_STATED,
    KIND_GIVEN_CODE_TOO_LARGE,
    KIND_GIVEN_CODE_UNREADABLE,
    KIND_OUTPUT_EXISTS,
    KIND_OUTPUT_NOT_WRITTEN,
    NAME,
    definition,
    place,
)
from hilclaw.tools import ToolFailure

KERNEL = b"""#include <stddef.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a,
                  const float *restrict b, float *restrict c) {}
"""
PROFILE = {
    "schema_version": 1,
    "accelerator": standin_profile.ACCELERATOR,
    "revision": "test-revision",
    "toolchain": {"clang": "test"},
    "host": {"cpu": "test", "os": "test"},
    "hw_source": "external",
}
OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 4, "k": 8, "n": 4},
    "dtype": "fp32",
    "layout": "row_major",
}
DOCUMENT = {
    "schema_version": 1,
    "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
    "op_signature": {"key": keys.op_signature_key(OP).name, "record": OP},
    "objective": {"objectives": [{"type": "latency_minimisation"}], "constraints": []},
    "candidates_per_round": 1,
    "n_max": 6,
    "draws": 1,
    "tolerance": {"rtol": 1e-4, "atol": 1e-5},
    "round_budget": 1,
}


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


def started(root, code=KERNEL):
    if code is None:
        return start_instance.start(DOCUMENT, data_root=root)
    path = root.parent / "given.c"
    path.write_bytes(code)
    return start_instance.start(DOCUMENT, data_root=root, code_file=path)


def output_of(root, run_id):
    return layout.attempt_artefact(root, run_id, *GIVEN_ATTEMPT, "output")


def instance_of(root, run_id):
    return json.loads((root / "runs" / run_id / "instance.json").read_bytes())


def rewrite_instance(root, run_id, document):
    path = root / "runs" / run_id / "instance.json"
    path.write_bytes(json.dumps(document).encode())


def blob_of(root, run_id):
    return cas.blob_path(root, instance_of(root, run_id)["given_code"])


def refused(root, run_id, kind):
    rounds = root / "runs" / run_id / "rounds"
    before = sorted(p.relative_to(root) for p in rounds.rglob("*"))
    with pytest.raises(ToolFailure) as caught:
        place(root, run_id)
    assert caught.value.kind == kind
    assert sorted(p.relative_to(root) for p in rounds.rglob("*")) == before
    return caught.value


def test_the_public_names():
    assert given_attempt.__doc__
    assert GIVEN_NAME == "given.c"
    assert GIVEN_ATTEMPT == (0, 1, 1)
    assert NAME == "given.place"
    assert mcp_front.mcp_name(NAME) == "given_place"
    assert (
        KIND_GIVEN_CODE_NOT_STATED,
        KIND_GIVEN_CODE_MISSING,
        KIND_GIVEN_CODE_CORRUPT,
        KIND_GIVEN_CODE_UNREADABLE,
        KIND_GIVEN_CODE_TOO_LARGE,
        KIND_OUTPUT_EXISTS,
        KIND_OUTPUT_NOT_WRITTEN,
    ) == (
        "given_code_not_stated",
        "given_code_missing",
        "given_code_corrupt",
        "given_code_unreadable",
        "given_code_too_large",
        "output_exists",
        "output_not_written",
    )


def test_the_given_code_is_placed_as_attempt_0_1_1(root):
    run_id = started(root)
    digest = instance_of(root, run_id)["given_code"]

    assert place(root, run_id) == digest

    output = output_of(root, run_id)
    assert sorted(os.listdir(output)) == [GIVEN_NAME]
    assert (output / GIVEN_NAME).read_bytes() == KERNEL
    assert sorted(os.listdir(output.parent)) == ["output"]
    assert not layout.attempt_artefact(root, run_id, 0, 1, 1, "spec.json").exists()
    rounds = root / "runs" / run_id / "rounds"
    assert sorted(p.relative_to(rounds).as_posix() for p in rounds.rglob("*")) == [
        "0000",
        "0000/coder",
        "0000/coder/candidates",
        "0000/coder/candidates/01",
        "0000/coder/candidates/01/attempts",
        "0000/coder/candidates/01/attempts/01",
        "0000/coder/candidates/01/attempts/01/output",
        "0000/coder/candidates/01/attempts/01/output/given.c",
    ]
    assert not (root / "runs" / run_id / "STATE.json").exists()
    assert not (root / "runs" / run_id / "events.ndjson").exists()


def test_a_second_placement_is_refused_and_keeps_the_first(root):
    run_id = started(root)
    place(root, run_id)
    failure = refused(root, run_id, KIND_OUTPUT_EXISTS)
    assert failure.message.startswith(
        f"runs/{run_id}/rounds/0000/coder/candidates/01/attempts/01/output: "
    )
    assert (output_of(root, run_id) / GIVEN_NAME).read_bytes() == KERNEL


@pytest.mark.parametrize("entry", ["directory", "file"])
def test_any_entry_output_is_refused(root, entry):
    run_id = started(root)
    output = output_of(root, run_id)
    output.parent.mkdir(parents=True)
    if entry == "directory":
        output.mkdir()
    else:
        output.write_bytes(b"")
    refused(root, run_id, KIND_OUTPUT_EXISTS)
    assert not (output / GIVEN_NAME).exists()


def test_a_run_without_given_code_is_refused(root):
    run_id = started(root, code=None)
    assert instance_of(root, run_id)["schema_version"] == 1
    failure = refused(root, run_id, KIND_GIVEN_CODE_NOT_STATED)
    assert failure.message == (
        f"runs/{run_id}/instance.json: states no given_code (schema_version 1); "
        "nothing was placed"
    )
    assert not (root / "runs" / run_id / "rounds").exists()


def test_a_version_2_run_is_refused(root):
    run_id = started(root, code=None)
    document = instance_of(root, run_id)
    document.update(schema_version=2, candidate_kind="compile_settings")
    rewrite_instance(root, run_id, document)
    failure = refused(root, run_id, KIND_GIVEN_CODE_NOT_STATED)
    assert "(schema_version 2)" in failure.message


def test_a_missing_blob_is_refused(root):
    run_id = started(root)
    blob_of(root, run_id).unlink()
    failure = refused(root, run_id, KIND_GIVEN_CODE_MISSING)
    assert failure.message.startswith("blobs/sha256/")
    assert not (root / "runs" / run_id / "rounds").exists()


def test_a_corrupted_blob_is_refused(root):
    run_id = started(root)
    blob_of(root, run_id).write_bytes(KERNEL + b"\n")
    failure = refused(root, run_id, KIND_GIVEN_CODE_CORRUPT)
    assert failure.message.endswith("its content is not its hash; nothing was placed")
    assert not (root / "runs" / run_id / "rounds").exists()


def test_a_blob_changed_after_its_verification_is_refused(root, monkeypatch):
    run_id = started(root)
    verify = cas.verify_blob

    def verify_then_change(data_root, digest):
        intact = verify(data_root, digest)
        cas.blob_path(data_root, digest).write_bytes(b"changed")
        return intact

    monkeypatch.setattr(cas, "verify_blob", verify_then_change)
    refused(root, run_id, KIND_GIVEN_CODE_CORRUPT)
    assert not (root / "runs" / run_id / "rounds").exists()


def test_a_blob_larger_than_a_kernel_file_is_refused(root):
    run_id = started(root)
    large = b"/* x */\n" * (bring_in.MAX_FILE_BYTES // 8 + 1)
    digest = cas.put_bytes(root, large).digest
    document = instance_of(root, run_id)
    document["given_code"] = digest
    rewrite_instance(root, run_id, document)
    failure = refused(root, run_id, KIND_GIVEN_CODE_TOO_LARGE)
    assert f"holds {len(large)} bytes, more than the 262144" in failure.message


def test_a_blob_of_exactly_the_bound_is_placed(root):
    run_id = started(root)
    bound = b"/" * bring_in.MAX_FILE_BYTES
    document = instance_of(root, run_id)
    document["given_code"] = cas.put_bytes(root, bound).digest
    rewrite_instance(root, run_id, document)
    place(root, run_id)
    assert (output_of(root, run_id) / GIVEN_NAME).read_bytes() == bound


@pytest.mark.parametrize("where", ["verify", "read"])
def test_an_unreadable_blob_is_refused(root, monkeypatch, where):
    run_id = started(root)
    error = PermissionError(13, "Permission denied")
    if where == "verify":

        def fail(data_root, digest):
            raise error

        monkeypatch.setattr(cas, "verify_blob", fail)
    else:
        blob = blob_of(root, run_id)
        read_bytes = type(blob).read_bytes

        def fail(path):
            if path == blob:
                raise error
            return read_bytes(path)

        monkeypatch.setattr(type(blob), "read_bytes", fail)
    failure = refused(root, run_id, KIND_GIVEN_CODE_UNREADABLE)
    assert "could not be read: PermissionError: Permission denied" in failure.message


@pytest.mark.parametrize(
    "change, kind",
    [
        (lambda path: path.unlink(), "run_file_missing"),
        (lambda path: path.write_bytes(b"{"), "run_file_invalid"),
        (
            lambda path: path.write_bytes(
                json.dumps(
                    {**json.loads(path.read_bytes()), "schema_version": 4}
                ).encode()
            ),
            "run_file_unsupported",
        ),
        (
            lambda path: path.write_bytes(
                json.dumps(
                    {**json.loads(path.read_bytes()), "given_code": "AB"}
                ).encode()
            ),
            "run_file_invalid",
        ),
    ],
    ids=["missing", "invalid", "version_4", "malformed_given_code"],
)
def test_an_unusable_instance_is_its_run_file_kind(root, change, kind):
    run_id = started(root)
    change(root / "runs" / run_id / "instance.json")
    with pytest.raises(ToolFailure) as caught:
        place(root, run_id)
    assert caught.value.kind == kind
    assert not (root / "runs" / run_id / "rounds").exists()


def test_a_run_id_that_is_none_is_refused_before_the_file_system(root):
    with pytest.raises(layout.InvalidPathValueError):
        place(root, "../x")


def test_an_unlistable_attempt_directory_is_output_not_written(root, monkeypatch):
    run_id = started(root)
    output_of(root, run_id).parent.mkdir(parents=True)
    listdir = os.listdir

    def refuse(path):
        if str(path).endswith("01"):
            raise PermissionError(13, "Permission denied")
        return listdir(path)

    monkeypatch.setattr(os, "listdir", refuse)
    failure = refused(root, run_id, KIND_OUTPUT_NOT_WRITTEN)
    assert failure.message.endswith(
        "attempts/01: could not be listed: PermissionError: Permission denied"
    )


def test_a_failed_write_is_output_not_written(root, monkeypatch):
    run_id = started(root)

    def fail(*arguments, **options):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "open", fail)
    with pytest.raises(ToolFailure) as caught:
        place(root, run_id)
    assert caught.value.kind == KIND_OUTPUT_NOT_WRITTEN
    assert caught.value.message == (
        f"runs/{run_id}/rounds/0000/coder/candidates/01/attempts/01/output/given.c: "
        "was not written: OSError: No space left on device"
    )
    assert os.listdir(output_of(root, run_id)) == []


def test_an_output_taken_meanwhile_is_output_exists(root, monkeypatch):
    run_id = started(root)

    mkdir = os.mkdir

    def taken(path, *arguments, **options):
        if os.path.basename(path) == "output":
            raise FileExistsError(17, "File exists")
        return mkdir(path, *arguments, **options)

    monkeypatch.setattr(os, "mkdir", taken)
    with pytest.raises(ToolFailure) as caught:
        place(root, run_id)
    assert caught.value.kind == KIND_OUTPUT_EXISTS


def test_a_data_root_gone_is_said(root, monkeypatch):
    run_id = started(root)

    def gone(*arguments, **options):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(os, "makedirs", gone)
    monkeypatch.setattr(run_files, "data_root_is_there", lambda data_root: False)
    with pytest.raises(ToolFailure) as caught:
        place(root, run_id)
    assert caught.value.kind == KIND_OUTPUT_NOT_WRITTEN
    assert caught.value.message.endswith(
        "FileNotFoundError: No such file or directory: the data root is not an "
        "existing directory"
    )


def test_the_tool_places_through_the_default_registry(root):
    run_id = started(root)
    registry = tools.default_registry(lambda: root)
    answer = tools.call(registry, NAME, {"run_id": run_id})
    assert answer == {"given_code": instance_of(root, run_id)["given_code"]}
    assert (output_of(root, run_id) / GIVEN_NAME).read_bytes() == KERNEL
    assert not (root / "runs" / run_id / "events.ndjson").exists()


def test_the_definition():
    calls = []
    found = definition(lambda: calls.append(1))
    assert found.name == NAME
    assert calls == []
    assert found.input_schema == {
        "type": "object",
        "properties": {
            "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
        },
        "required": ["run_id"],
        "additionalProperties": False,
    }
    for kind in (
        "invalid_request",
        "no_data_root",
        "run_file_missing",
        "run_file_invalid",
        "run_file_unsupported",
        "run_file_unreadable",
        KIND_GIVEN_CODE_NOT_STATED,
        KIND_OUTPUT_EXISTS,
        KIND_GIVEN_CODE_MISSING,
        KIND_GIVEN_CODE_CORRUPT,
        KIND_GIVEN_CODE_UNREADABLE,
        KIND_GIVEN_CODE_TOO_LARGE,
        KIND_OUTPUT_NOT_WRITTEN,
    ):
        assert kind in found.description
    assert str(bring_in.MAX_FILE_BYTES) in found.description


def test_a_source_that_is_not_callable_is_refused():
    with pytest.raises(TypeError):
        definition("data")


@pytest.mark.parametrize(
    "request_, text",
    [
        ({}, "the request lacks the member run_id"),
        (
            {"run_id": "r", "round": 0},
            "the request takes the member run_id only, not 'round'",
        ),
        ({"run_id": "../x"}, "the request's "),
        ({"run_id": 1}, "the request's "),
    ],
    ids=["empty", "another_member", "bad_run_id", "not_a_string"],
)
def test_a_bad_request_is_refused_before_the_source_is_asked(request_, text):
    calls = []
    found = definition(lambda: calls.append(1))
    with pytest.raises(ToolFailure) as caught:
        found.function(request_)
    assert caught.value.kind == "invalid_request"
    assert caught.value.message.startswith(text)
    assert calls == []


def test_no_data_root(tmp_path):
    found = definition(lambda: tmp_path / "missing")
    with pytest.raises(ToolFailure) as caught:
        found.function({"run_id": "r"})
    assert caught.value.kind == "no_data_root"


def test_the_placed_bytes_hash_to_the_given_code(root):
    run_id = started(root)
    digest = place(root, run_id)
    data = (output_of(root, run_id) / GIVEN_NAME).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest
