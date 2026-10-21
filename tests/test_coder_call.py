import ast
import inspect
import json
import os
import tempfile
from pathlib import Path

import pytest

from hilclaw import bring_in, coder_call, instance, keys, layout, scratch, tools
from hilclaw.coder_call import (
    FAILURE_KINDS,
    KIND_CODER_MODEL_NOT_STATED,
    KIND_CODER_NOT_ENDED,
    KIND_CODER_NOT_STARTED,
    KIND_NO_CONTAINER_RUNTIME,
    KIND_OUTPUT_EXISTS,
    KIND_OUTPUT_NOT_WRITTEN,
    KIND_SPEC_INVALID,
    KIND_SPEC_UNSUPPORTED,
    CoderNotStartedError,
    call,
)

# Synthetic values only: no record, key, member or tuple of a real run.
RUN_ID = "synthetic-run-1"
TUPLE = (1, 1, 1)
KERNEL = b"/* synthetic kernel */\n"
MODEL = "claude-test-model-1"
HW = {
    "schema_version": 1,
    "accelerator": "synthetic_accel",
    "revision": "synthetic-rev-A",
    "toolchain": {"synthetic_cc": "0.0.1-synthetic"},
    "host": {"cpu": "synthetic cpu", "os": "synthetic os"},
    "hw_source": "in_house",
}
UNSTATED = object()


def request(**members):
    made = {"run_id": RUN_ID, "round": 1, "candidate": 1, "attempt": 1}
    made.update(members)
    return made


def instance_document(coder_model=MODEL, **changes):
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(HW).name, "record": HW},
        "coder_model": coder_model,
        **changes,
    }
    if coder_model is UNSTATED:
        del made["coder_model"]
    return made


def instance_content(coder_model=MODEL, **changes):
    return (json.dumps(instance_document(coder_model, **changes)) + "\n").encode()


def instance_path(data_root, run_id=RUN_ID):
    return layout.run_file(data_root, run_id, "instance.json")


def put_instance(data_root, content=None, run_id=RUN_ID):
    path = instance_path(data_root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(instance_content() if content is None else content)
    return path


def document(run_id=RUN_ID, round=1, candidate=1, attempt=1):
    hw = HW
    op = {
        "schema_version": 1,
        "kind": "gemm",
        "shape": {"m": 3, "k": 5, "n": 7},
        "dtype": "synthetic_dtype",
        "layout": "synthetic_layout",
    }
    operand = {
        "name": "synthetic_a",
        "role": "input",
        "dtype": "synthetic_dtype",
        "shape": [3, 5],
    }
    return {
        "schema_version": 2,
        "id": {
            "run_id": run_id,
            "round": round,
            "candidate": candidate,
            "attempt": attempt,
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


class FakeRuntime:
    def __init__(self, *, available=True, status=0, files=None, error=None, act=None):
        self._available = available
        self.status = status
        self.files = {} if files is None else files
        self.error = error
        self.act = act
        self.runs = []
        self.models = []
        self.spec_copies = []

    def available(self):
        return self._available

    def run(self, scratch_root, *, coder_model):
        self.runs.append(scratch_root)
        self.models.append(coder_model)
        root = Path(scratch_root)
        self.spec_copies.append((root / scratch.SPEC_COPY_NAME).read_bytes())
        if self.error is not None:
            raise self.error
        if self.files:
            (root / "output").mkdir()
            for name, data in self.files.items():
                (root / "output" / name).write_bytes(data)
        if self.act is not None:
            self.act(root)
        return self.status


@pytest.fixture
def data_root(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    put_instance(root)
    return root


@pytest.fixture
def parent(tmp_path, monkeypatch):
    directory = tmp_path / "scratches"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


@pytest.fixture
def source(data_root):
    return lambda: data_root


@pytest.fixture
def spec_path(data_root):
    return layout.attempt_artefact(data_root, RUN_ID, *TUPLE, "spec.json")


@pytest.fixture
def output_path(data_root):
    return layout.attempt_artefact(data_root, RUN_ID, *TUPLE, "output")


def put_spec(spec_path, content=None):
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(document()) + "\n").encode() if content is None else content
    spec_path.write_bytes(data)
    return data


@pytest.fixture
def spec(spec_path):
    return put_spec(spec_path)


def symlink(link, target):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError):
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise
        pytest.skip("this machine refuses to create a symbolic link")


def failure(kind, data_root, req, source, runtime):
    with pytest.raises(tools.ToolFailure) as caught:
        call(req, source=source, runtime=runtime)
    assert caught.value.kind == kind
    assert str(data_root) not in caught.value.message
    assert str(data_root.resolve()) not in caught.value.message
    return caught.value


def assert_nothing_started(parent, runtime):
    assert runtime.runs == []
    assert list(parent.iterdir()) == []


def test_a_call_takes_the_admitted_file_and_removes_the_scratch(
    data_root, parent, source, spec, output_path
):
    runtime = FakeRuntime(files={"kernel.c": KERNEL, "notes.txt": b"x"})
    assert call(request(), source=source, runtime=runtime) == {
        "taken": ["kernel.c"],
        "scratch_removed": True,
    }
    assert runtime.spec_copies == [spec]
    assert type(runtime.runs[0]) is str
    assert Path(runtime.runs[0]).parent == parent.resolve()
    assert not os.path.lexists(runtime.runs[0])
    assert list(parent.iterdir()) == []
    assert sorted(os.listdir(output_path)) == ["kernel.c"]
    assert (output_path / "kernel.c").read_bytes() == KERNEL


def test_taken_names_come_in_the_order_of_bring_in(parent, source, spec, output_path):
    runtime = FakeRuntime(files={"b.h": b"b", "a.c": b"a"})
    result = call(request(), source=source, runtime=runtime)
    assert result["taken"] == ["a.c", "b.h"]


def test_nothing_admitted_is_a_result_and_creates_no_output(
    parent, source, spec, output_path
):
    runtime = FakeRuntime()
    result = call(request(), source=source, runtime=runtime)
    assert result == {"taken": [], "scratch_removed": True}
    assert not os.path.lexists(output_path)
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize(
    "req",
    [
        None,
        [],
        "request",
        request(extra=1),
        {"run_id": RUN_ID, "round": 1, "candidate": 1},
        {"round": 1, "candidate": 1, "attempt": 1},
        {},
        request(run_id="Bad Run"),
        request(run_id=1),
        request(run_id=""),
        request(round=-1),
        request(round="1"),
        request(round=1.0),
        request(round=True),
        request(round=keys.MAX_INTEGER + 1),
        request(candidate=0),
        request(candidate=None),
        request(attempt=0),
        request(attempt=-3),
    ],
)
def test_a_bad_request_is_refused_before_the_source_is_asked(data_root, parent, req):
    asked = []

    def source():
        asked.append(True)
        return data_root

    runtime = FakeRuntime()
    failure(tools.KIND_INVALID_REQUEST, data_root, req, source, runtime)
    assert asked == []
    assert_nothing_started(parent, runtime)


def test_a_request_member_that_is_no_str_is_named_in_the_refusal(data_root, source):
    req = {**request(), 7: "x"}
    caught = failure(tools.KIND_INVALID_REQUEST, data_root, req, source, FakeRuntime())
    assert "7" in caught.message


@pytest.mark.parametrize("round", [0, keys.MAX_INTEGER])
def test_the_bounds_of_round_are_accepted(data_root, parent, source, round):
    req = request(round=round)
    numbers = (round, 1, 1)
    path = layout.attempt_artefact(data_root, RUN_ID, *numbers, "spec.json")
    put_spec(path, (json.dumps(document(RUN_ID, *numbers)) + "\n").encode())
    assert call(req, source=source, runtime=FakeRuntime())["taken"] == []


def test_a_failing_source_gives_no_data_root(data_root, parent):
    def source():
        raise RuntimeError("no configuration")

    runtime = FakeRuntime()
    failure(tools.KIND_NO_DATA_ROOT, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_a_source_that_is_not_callable_raises_type_error(parent):
    with pytest.raises(TypeError):
        call(request(), source="not callable", runtime=FakeRuntime())


@pytest.mark.parametrize("as_file", [False, True])
def test_an_existing_output_is_refused(
    data_root, parent, source, spec, output_path, as_file
):
    if as_file:
        output_path.write_bytes(b"")
    else:
        output_path.mkdir()
    runtime = FakeRuntime(files={"kernel.c": KERNEL})
    failure(KIND_OUTPUT_EXISTS, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_output_exists_wins_over_a_missing_spec(data_root, parent, source, output_path):
    output_path.mkdir(parents=True)
    runtime = FakeRuntime()
    failure(KIND_OUTPUT_EXISTS, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_an_attempt_directory_that_cannot_be_listed_propagates_its_error(
    data_root, parent, source, spec, output_path, monkeypatch
):
    listdir = os.listdir

    def refusing(path="."):
        if Path(path) == output_path.parent:
            raise PermissionError(13, "denied", str(path))
        return listdir(path)

    monkeypatch.setattr(os, "listdir", refusing)
    runtime = FakeRuntime()
    with pytest.raises(PermissionError) as caught:
        call(request(), source=source, runtime=runtime)
    assert not isinstance(caught.value, tools.ToolFailure)
    assert_nothing_started(parent, runtime)


def test_a_missing_spec_is_unreadable(data_root, parent, source):
    runtime = FakeRuntime()
    failure(scratch.SPEC_UNREADABLE, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_an_attempt_path_through_a_file_is_unreadable(data_root, parent, source):
    attempts = layout.attempt_artefact(data_root, RUN_ID, *TUPLE, "spec.json")
    attempts.parent.parent.mkdir(parents=True)
    attempts.parent.write_bytes(b"")
    failure(scratch.SPEC_UNREADABLE, data_root, request(), source, FakeRuntime())


def test_a_spec_that_cannot_be_opened_is_unreadable(
    data_root, parent, source, spec, spec_path, monkeypatch
):
    opening = os.open

    def refusing(path, *args, **kwargs):
        if Path(path) == spec_path:
            raise PermissionError(13, "denied", str(path))
        return opening(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", refusing)
    runtime = FakeRuntime()
    failure(scratch.SPEC_UNREADABLE, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_a_spec_whose_read_fails_is_unreadable(
    data_root, parent, source, spec, monkeypatch
):
    def refusing(descriptor, size):
        raise OSError(5, "input/output error")

    monkeypatch.setattr(os, "read", refusing)
    runtime = FakeRuntime()
    failure(scratch.SPEC_UNREADABLE, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_a_spec_replaced_while_opened_is_unreadable(
    data_root, parent, source, spec, monkeypatch
):
    real = os.fstat

    def other(descriptor):
        found = real(descriptor)
        fields = list(found)
        fields[1] = found.st_ino + 1
        return os.stat_result(fields)

    monkeypatch.setattr(os, "fstat", other)
    runtime = FakeRuntime()
    caught = failure(scratch.SPEC_UNREADABLE, data_root, request(), source, runtime)
    assert "changed" in caught.message
    assert_nothing_started(parent, runtime)


def test_a_spec_directory_is_no_regular_file(data_root, parent, source, spec_path):
    spec_path.mkdir(parents=True)
    runtime = FakeRuntime()
    failure(scratch.SPEC_NOT_REGULAR_FILE, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_a_spec_link_is_no_regular_file(data_root, parent, source, spec_path, tmp_path):
    target = tmp_path / "elsewhere.json"
    target.write_bytes((json.dumps(document()) + "\n").encode())
    spec_path.parent.mkdir(parents=True)
    symlink(spec_path, target)
    runtime = FakeRuntime()
    failure(scratch.SPEC_NOT_REGULAR_FILE, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"not json",
        b"[]",
        b'{"schema_version": 2}',
        (json.dumps({**document(), "extra": 1}) + "\n").encode(),
    ],
)
def test_a_spec_that_parse_refuses_is_invalid(
    data_root, parent, source, spec_path, content
):
    put_spec(spec_path, content)
    runtime = FakeRuntime()
    failure(KIND_SPEC_INVALID, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize(
    "members",
    [
        {"attempt": 2},
        {"candidate": 2},
        {"round": 0},
        {"round": 2},
        {"run_id": "synthetic-run-2"},
    ],
)
def test_a_spec_whose_id_names_another_tuple_is_invalid(
    data_root, parent, source, members
):
    req = request(**members)
    numbers = req["round"], req["candidate"], req["attempt"]
    put_instance(data_root, run_id=req["run_id"])
    put_spec(layout.attempt_artefact(data_root, req["run_id"], *numbers, "spec.json"))
    runtime = FakeRuntime()
    caught = failure(KIND_SPEC_INVALID, data_root, req, source, runtime)
    assert "tuple" in caught.message
    assert_nothing_started(parent, runtime)


def test_a_spec_whose_id_has_no_path_is_invalid(data_root, parent, source, spec_path):
    put_spec(spec_path, (json.dumps(document(run_id="Not A Run")) + "\n").encode())
    runtime = FakeRuntime()
    caught = failure(KIND_SPEC_INVALID, data_root, request(), source, runtime)
    assert "no path" in caught.message
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize("version", [1, 3])
def test_a_spec_of_another_version_is_unsupported(
    data_root, parent, source, spec_path, version
):
    other = {**document(), "schema_version": version}
    put_spec(spec_path, (json.dumps(other) + "\n").encode())
    runtime = FakeRuntime()
    failure(KIND_SPEC_UNSUPPORTED, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_no_container_runtime_creates_nothing(data_root, parent, source, spec):
    runtime = FakeRuntime(available=False)
    failure(KIND_NO_CONTAINER_RUNTIME, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_an_invalid_spec_wins_over_no_container_runtime(
    data_root, parent, source, spec_path
):
    put_spec(spec_path, b"not json")
    runtime = FakeRuntime(available=False)
    failure(KIND_SPEC_INVALID, data_root, request(), source, runtime)


def test_an_exception_of_available_propagates(data_root, parent, source, spec):
    class Broken(FakeRuntime):
        def available(self):
            raise RuntimeError("probe failed")

    runtime = Broken()
    with pytest.raises(RuntimeError, match="probe failed"):
        call(request(), source=source, runtime=runtime)
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize("value", scratch.SCRATCH_FAILURES)
def test_a_scratch_error_gives_its_value(
    data_root, parent, source, spec, monkeypatch, value
):
    def refusing(*args, **kwargs):
        raise scratch.ScratchError(value)

    monkeypatch.setattr(scratch, "create", refusing)
    runtime = FakeRuntime()
    failure(value, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize(
    "error", [OSError(28, "no space left"), scratch.InvalidScratchArgumentError("x")]
)
def test_an_error_of_making_the_scratch_propagates(
    parent, source, spec, monkeypatch, error
):
    def refusing(*args, **kwargs):
        raise error

    monkeypatch.setattr(scratch, "create", refusing)
    runtime = FakeRuntime()
    with pytest.raises(type(error)) as caught:
        call(request(), source=source, runtime=runtime)
    assert caught.value is error
    assert not isinstance(caught.value, tools.ToolFailure)
    assert runtime.runs == []


def test_the_scratch_is_made_with_the_data_root_kept_out(
    data_root, parent, source, spec, monkeypatch
):
    seen = []
    create, remove = scratch.create, scratch.remove

    def creating(path, **kwargs):
        seen.append(("create", Path(path), kwargs))
        return create(path, **kwargs)

    def removing(path, **kwargs):
        seen.append(("remove", Path(path), kwargs))
        return remove(path, **kwargs)

    monkeypatch.setattr(scratch, "create", creating)
    monkeypatch.setattr(scratch, "remove", removing)
    runtime = FakeRuntime()
    call(request(), source=source, runtime=runtime)
    assert [step for step, _, _ in seen] == ["create", "remove"]
    assert seen[0][2] == {"keep_out": (data_root,)}
    assert seen[1] == ("remove", Path(runtime.runs[0]), {"keep_out": (data_root,)})


def test_a_coder_that_cannot_start_gives_coder_not_started(
    data_root, parent, source, spec, output_path
):
    runtime = FakeRuntime(error=CoderNotStartedError("no image"))
    failure(KIND_CODER_NOT_STARTED, data_root, request(), source, runtime)
    assert len(runtime.runs) == 1
    assert list(parent.iterdir()) == []
    assert not os.path.lexists(output_path)


@pytest.mark.parametrize("status", [1, 2, -9, 137])
def test_a_coder_that_does_not_end_normally_brings_nothing_in(
    data_root, parent, source, spec, output_path, status
):
    runtime = FakeRuntime(status=status, files={"kernel.c": KERNEL})
    caught = failure(KIND_CODER_NOT_ENDED, data_root, request(), source, runtime)
    assert str(status) in caught.message
    assert list(parent.iterdir()) == []
    assert not os.path.lexists(output_path)


@pytest.mark.parametrize("status", ["0", 0.0, True, None])
def test_a_status_that_is_no_int_raises_type_error_after_removal(
    parent, source, spec, output_path, status
):
    runtime = FakeRuntime(status=status, files={"kernel.c": KERNEL})
    with pytest.raises(TypeError):
        call(request(), source=source, runtime=runtime)
    assert list(parent.iterdir()) == []
    assert not os.path.lexists(output_path)


def test_another_exception_of_run_propagates_after_removal(parent, source, spec):
    runtime = FakeRuntime(error=RuntimeError("runtime broke"))
    with pytest.raises(RuntimeError, match="runtime broke"):
        call(request(), source=source, runtime=runtime)
    assert list(parent.iterdir()) == []


@pytest.mark.parametrize("value", bring_in.BRING_IN_FAILURES)
def test_a_bring_in_error_gives_its_value_after_removal(
    data_root, parent, source, spec, monkeypatch, value
):
    def refusing(scratch_root, output_path):
        raise bring_in.BringInError(value)

    monkeypatch.setattr(bring_in, "bring_in", refusing)
    failure(value, data_root, request(), source, FakeRuntime())
    assert list(parent.iterdir()) == []


def test_output_taken_during_the_call_gives_output_exists(
    data_root, parent, source, spec, output_path
):
    runtime = FakeRuntime(
        files={"kernel.c": KERNEL}, act=lambda root: output_path.mkdir()
    )
    failure(KIND_OUTPUT_EXISTS, data_root, request(), source, runtime)
    assert list(parent.iterdir()) == []
    assert os.listdir(output_path) == []


def test_a_write_that_fails_gives_output_not_written(
    data_root, parent, source, spec, output_path, monkeypatch
):
    def refusing(scratch_root, path):
        raise PermissionError(13, "denied", str(path))

    monkeypatch.setattr(bring_in, "bring_in", refusing)
    caught = failure(
        KIND_OUTPUT_NOT_WRITTEN, data_root, request(), source, FakeRuntime()
    )
    assert "PermissionError" in caught.message
    assert list(parent.iterdir()) == []


def test_an_invalid_bring_in_argument_propagates_after_removal(
    parent, source, spec, monkeypatch
):
    def refusing(scratch_root, output_path):
        raise bring_in.InvalidBringInArgumentError("x")

    monkeypatch.setattr(bring_in, "bring_in", refusing)
    with pytest.raises(bring_in.InvalidBringInArgumentError):
        call(request(), source=source, runtime=FakeRuntime())
    assert list(parent.iterdir()) == []


def test_a_failed_removal_is_reported_on_success(parent, source, spec, monkeypatch):
    calls = []
    monkeypatch.setattr(scratch, "remove", lambda *a, **k: calls.append(a) or False)
    result = call(request(), source=source, runtime=FakeRuntime())
    assert result == {"taken": [], "scratch_removed": False}
    assert len(calls) == 1


@pytest.mark.parametrize(
    ("runtime", "kind"),
    [
        (FakeRuntime(status=3), KIND_CODER_NOT_ENDED),
        (FakeRuntime(error=CoderNotStartedError()), KIND_CODER_NOT_STARTED),
    ],
)
def test_a_failed_removal_is_added_to_the_failure_text(
    data_root, parent, source, spec, monkeypatch, runtime, kind
):
    calls = []
    monkeypatch.setattr(scratch, "remove", lambda *a, **k: calls.append(a) or False)
    caught = failure(kind, data_root, request(), source, runtime)
    assert caught.message.endswith("the scratch was not removed")
    assert isinstance(caught.__cause__, tools.ToolFailure)
    assert caught.__cause__.kind == kind
    assert len(calls) == 1


def test_a_removed_scratch_leaves_the_failure_text_alone(
    data_root, parent, source, spec
):
    caught = failure(
        KIND_CODER_NOT_ENDED, data_root, request(), source, FakeRuntime(status=1)
    )
    assert "not removed" not in caught.message


def test_the_kinds_are_names_and_only_two_and_the_run_file_four_are_reserved():
    assert len(set(FAILURE_KINDS)) == len(FAILURE_KINDS)
    for kind in FAILURE_KINDS:
        tools.ToolFailure(kind, "")
    reserved = {k for k in FAILURE_KINDS if k in tools.RESERVED_KINDS}
    assert reserved == {
        tools.KIND_INVALID_REQUEST,
        tools.KIND_NO_DATA_ROOT,
        tools.KIND_RUN_FILE_MISSING,
        tools.KIND_RUN_FILE_UNREADABLE,
        tools.KIND_RUN_FILE_INVALID,
        tools.KIND_RUN_FILE_UNSUPPORTED,
    }
    assert FAILURE_KINDS[:2] == (tools.KIND_INVALID_REQUEST, tools.KIND_NO_DATA_ROOT)
    assert FAILURE_KINDS[-1] == KIND_OUTPUT_NOT_WRITTEN


def test_the_module_starts_no_process_and_its_only_front_is_coder_run():
    tree = ast.parse(inspect.getsource(coder_call))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    assert not {"subprocess", "multiprocessing", "asyncio"} & imported
    assert "__main__" not in inspect.getsource(coder_call)
    names = tools.default_registry(lambda: None).names()
    assert [name for name in names if "coder" in name] == ["coder.run"]


def test_the_synthetic_instance_file_is_valid():
    assert instance.parse(instance_content()).coder_model == MODEL
    assert instance.parse(instance_content(UNSTATED)).coder_model is None


@pytest.mark.parametrize(
    "model", [MODEL, "claude-opus-5-5", "claude-sonnet-4-5-20250929", "claude-x"]
)
def test_the_runtime_gets_the_model_the_file_states(
    data_root, parent, source, spec, output_path, model
):
    put_instance(data_root, instance_content(model))
    runtime = FakeRuntime(files={"kernel.c": KERNEL})
    assert call(request(), source=source, runtime=runtime) == {
        "taken": ["kernel.c"],
        "scratch_removed": True,
    }
    assert runtime.models == [model]
    assert type(runtime.models[0]) is str


def test_the_file_is_read_again_at_every_call(
    data_root, parent, source, spec, output_path
):
    runtime = FakeRuntime()
    call(request(), source=source, runtime=runtime)
    put_instance(data_root, instance_content("claude-test-model-2"))
    call(request(), source=source, runtime=runtime)
    assert runtime.models == [MODEL, "claude-test-model-2"]


class Unasked(FakeRuntime):
    def available(self):
        raise AssertionError("the runtime was asked")


def refused(kind, data_root, parent, source, output_path):
    runtime = Unasked(files={"kernel.c": KERNEL})
    caught = failure(kind, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)
    assert runtime.models == []
    assert not os.path.lexists(output_path)
    return caught


def test_a_missing_instance_file_gives_run_file_missing(
    data_root, parent, source, spec, output_path
):
    instance_path(data_root).unlink()
    caught = refused(
        tools.KIND_RUN_FILE_MISSING, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")


def test_a_missing_run_directory_gives_run_file_missing(
    data_root, parent, source, output_path
):
    instance_path(data_root).unlink()
    instance_path(data_root).parent.rmdir()
    caught = refused(
        tools.KIND_RUN_FILE_MISSING, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")


def test_an_instance_directory_gives_run_file_invalid(
    data_root, parent, source, spec, output_path
):
    instance_path(data_root).unlink()
    instance_path(data_root).mkdir()
    caught = refused(
        tools.KIND_RUN_FILE_INVALID, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")


def test_an_instance_link_gives_run_file_invalid(
    data_root, parent, source, spec, output_path, tmp_path
):
    target = tmp_path / "elsewhere.json"
    target.write_bytes(instance_content())
    instance_path(data_root).unlink()
    symlink(instance_path(data_root), target)
    caught = refused(
        tools.KIND_RUN_FILE_INVALID, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"not json",
        b"[]",
        *(
            instance_content(value)
            for value in ("opus", "default", "claude-opus-5-5[1m]", "", 5, None)
        ),
    ],
)
def test_an_instance_file_that_parse_refuses_gives_run_file_invalid(
    data_root, parent, source, spec, output_path, content
):
    put_instance(data_root, content)
    caught = refused(
        tools.KIND_RUN_FILE_INVALID, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")


def test_an_instance_file_of_another_version_gives_run_file_unsupported(
    data_root, parent, source, spec, output_path
):
    put_instance(data_root, instance_content(schema_version=2))
    caught = refused(
        tools.KIND_RUN_FILE_UNSUPPORTED, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")


def test_an_instance_file_whose_read_fails_gives_run_file_unreadable(
    data_root, parent, source, spec, output_path, monkeypatch
):
    reading = Path.read_bytes
    target = instance_path(data_root)

    def refusing(path):
        if path == target:
            raise PermissionError(13, "denied", str(path))
        return reading(path)

    monkeypatch.setattr(Path, "read_bytes", refusing)
    caught = refused(
        tools.KIND_RUN_FILE_UNREADABLE, data_root, parent, source, output_path
    )
    assert caught.message.startswith(f"runs/{RUN_ID}/instance.json: ")
    assert "PermissionError" in caught.message


def test_a_file_without_coder_model_gives_coder_model_not_stated(
    data_root, parent, source, spec, output_path
):
    put_instance(data_root, instance_content(UNSTATED))
    caught = refused(
        KIND_CODER_MODEL_NOT_STATED, data_root, parent, source, output_path
    )
    assert caught.message == f"runs/{RUN_ID}/instance.json: states no coder_model"


def test_a_bad_request_wins_over_a_missing_instance_file(data_root, parent):
    instance_path(data_root).unlink()
    asked = []

    def source():
        asked.append(True)
        return data_root

    runtime = Unasked()
    failure(tools.KIND_INVALID_REQUEST, data_root, request(round=-1), source, runtime)
    assert asked == []
    assert_nothing_started(parent, runtime)


def test_a_failing_source_wins_and_the_file_is_not_read(data_root, parent, monkeypatch):
    read = []
    monkeypatch.setattr(coder_call.run_file_tools, "read", lambda *a: read.append(a))

    def source():
        raise RuntimeError("no configuration")

    runtime = Unasked()
    failure(tools.KIND_NO_DATA_ROOT, data_root, request(), source, runtime)
    assert read == []
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize("spec_content", [None, b"not json"])
@pytest.mark.parametrize("with_output", [False, True])
def test_a_missing_instance_file_wins_over_output_and_spec(
    data_root, parent, source, spec_path, output_path, spec_content, with_output
):
    if spec_content is not None:
        put_spec(spec_path, spec_content)
    if with_output:
        output_path.mkdir(parents=True)
    instance_path(data_root).unlink()
    runtime = Unasked()
    failure(tools.KIND_RUN_FILE_MISSING, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


@pytest.mark.parametrize("with_output", [False, True])
def test_coder_model_not_stated_wins_over_output_spec_and_runtime(
    data_root, parent, source, output_path, with_output
):
    if with_output:
        output_path.mkdir(parents=True)
    put_instance(data_root, instance_content(UNSTATED))
    runtime = FakeRuntime(available=False)
    failure(KIND_CODER_MODEL_NOT_STATED, data_root, request(), source, runtime)
    assert_nothing_started(parent, runtime)


def test_a_run_that_takes_no_model_raises_type_error_after_removal(
    data_root, parent, source, spec, output_path, monkeypatch
):
    class Old(FakeRuntime):
        def run(self, scratch_root):
            raise AssertionError("run was entered")

    removed = []
    remove = scratch.remove

    def removing(path, **kwargs):
        removed.append(path)
        return remove(path, **kwargs)

    monkeypatch.setattr(scratch, "remove", removing)
    with pytest.raises(TypeError):
        call(request(), source=source, runtime=Old())
    assert len(removed) == 1
    assert list(parent.iterdir()) == []
    assert not os.path.lexists(output_path)


def test_the_new_kinds_stand_between_no_data_root_and_output_exists():
    assert FAILURE_KINDS[2:8] == (
        tools.KIND_RUN_FILE_MISSING,
        tools.KIND_RUN_FILE_UNREADABLE,
        tools.KIND_RUN_FILE_INVALID,
        tools.KIND_RUN_FILE_UNSUPPORTED,
        KIND_CODER_MODEL_NOT_STATED,
        KIND_OUTPUT_EXISTS,
    )
    assert KIND_CODER_MODEL_NOT_STATED == "coder_model_not_stated"
    assert KIND_CODER_MODEL_NOT_STATED not in tools.RESERVED_KINDS


def test_the_module_names_no_model_and_imports_no_default():
    tree = ast.parse(inspect.getsource(coder_call))
    imported = set()
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        if (
            isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
            and node.body
            and isinstance(node.body[0], ast.Expr)
        ):
            docstrings.add(id(node.body[0].value))
    assert "hilclaw.instance_start" not in imported
    assert "hilclaw.run_file_tools" in imported
    constants = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and type(node.value) is str
        and id(node) not in docstrings
    ]
    assert "coder_model_not_stated" in constants
    assert not [
        text
        for text in constants
        if text.startswith("claude-") or text in {"opus", "sonnet", "default"}
    ]
