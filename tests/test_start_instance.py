import copy
import datetime
import inspect
import json
import re
from pathlib import Path

import pytest

from hilclaw import (
    gemm_contract,
    instance,
    instance_file,
    instance_start,
    keys,
    layout,
    mock_backend,
    once_write,
    run_id,
    standin_profile,
)
from hilclaw.harness import measurement
from hilclaw.instance import InvalidInstanceError, UnsupportedVersionError
from hilclaw.instance_start import (
    CODER_MODEL_DEFAULT,
    REPORT_ORDER,
    MissingMembersError,
    OutOfScopeError,
)
from hilclaw.start_instance import GivenRunIdError, RunIdInUseError, start

ABSENT = object()
MARKER = "zq7-marker-zq7"
# Test values only: none is a default or a recommended value.
TEST_N_MAX = 12
TEST_CANDIDATES = 2
TEST_DRAWS = 3
TEST_TOLERANCE = {"rtol": 0.25, "atol": 3.0}
TEST_CODER_MODEL = "claude-test-model"
OBJECTIVE = {"objectives": [{"type": "latency_minimisation"}], "constraints": []}
RECORD = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 1, "k": 2048, "n": 8192},
    "dtype": "fp32",
    "layout": "row_major",
}
TIME = datetime.datetime(2026, 10, 9, 1, 23, 31, tzinfo=datetime.UTC)
BITS = 0x9F3A6C1E0B7D4A52
FIXED_ID = "20261009t012331z-9f3a6c1e0b7d4a52"
FORM = re.compile(r"[0-9]{8}t[0-9]{6}z-[0-9a-f]{16}")


def document(
    accelerator=standin_profile.ACCELERATOR,
    op_signature=RECORD,
    objective=OBJECTIVE,
    candidates_per_round=TEST_CANDIDATES,
    n_max=TEST_N_MAX,
    draws=TEST_DRAWS,
    tolerance=TEST_TOLERANCE,
    **others,
):
    profile = {
        "schema_version": 1,
        "accelerator": accelerator,
        "revision": "test-revision",
        "toolchain": {"clang": "test"},
        "host": {"cpu": "test", "os": "test"},
        "hw_source": "external",
    }
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(profile).name, "record": profile},
    }
    stated = {
        "op_signature": op_signature
        if op_signature is ABSENT
        else {
            "key": keys.op_signature_key(op_signature).name,
            "record": copy.deepcopy(op_signature),
        },
        "objective": objective,
        "candidates_per_round": candidates_per_round,
        "n_max": n_max,
        "draws": draws,
        "tolerance": tolerance,
    }
    made.update(
        {
            name: copy.deepcopy(value)
            for name, value in stated.items()
            if value is not ABSENT
        }
    )
    made.update(others)
    return made


def without(*names, **changes):
    return document(**{name: ABSENT for name in names}, **changes)


class Ids:
    def __init__(self):
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return run_id.compose(TIME, BITS)


@pytest.fixture
def ids(monkeypatch):
    counter = Ids()
    monkeypatch.setattr(run_id, "new", counter)
    return counter


@pytest.fixture
def fixed_sources(monkeypatch):
    monkeypatch.setattr(run_id, "_utc_now", lambda: TIME)
    monkeypatch.setattr(run_id.secrets, "randbits", lambda bits: BITS)


def tree(root):
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


def assert_refused(given, error, root, ids):
    before = copy.deepcopy(given)
    with pytest.raises(error) as caught:
        start(given, data_root=root)
    assert given == before
    assert tree(root) == []
    assert ids.calls == 0
    return caught.value


@pytest.mark.parametrize(
    "accelerator", [standin_profile.ACCELERATOR, mock_backend.NAME]
)
def test_a_valid_document_is_written_under_the_built_id(
    tmp_path, fixed_sources, accelerator
):
    given = document(accelerator=accelerator)
    before = copy.deepcopy(given)
    built = start(given, data_root=tmp_path)
    assert built == FIXED_ID
    assert layout.check_run_id(built) == built
    assert FORM.fullmatch(built)
    assert given == before
    assert tree(tmp_path) == ["runs", f"runs/{built}", f"runs/{built}/instance.json"]
    read = instance.read(tmp_path, built)
    assert read.hw_profile == given["hw_profile"]["record"]
    assert read.hw_profile["accelerator"] == accelerator
    assert read.hw_profile_key == given["hw_profile"]["key"]
    assert read.tolerance.rtol == TEST_TOLERANCE["rtol"]
    assert read.tolerance.atol == TEST_TOLERANCE["atol"]
    assert read.objective == OBJECTIVE
    assert read.op_signature.record == RECORD
    assert read.others == {}
    assert read.n_max == TEST_N_MAX
    assert read.draws == TEST_DRAWS
    assert read.candidates_per_round == TEST_CANDIDATES
    assert read.coder_model == CODER_MODEL_DEFAULT
    stored = json.loads((tmp_path / "runs" / built / "instance.json").read_bytes())
    assert stored == {**given, "coder_model": CODER_MODEL_DEFAULT}


def test_the_returned_id_has_the_form_with_the_real_sources(tmp_path):
    built = start(document(), data_root=tmp_path)
    assert type(built) is str
    assert FORM.fullmatch(built)
    assert layout.check_run_id(built) == built
    assert (tmp_path / "runs" / built / "instance.json").is_file()


def test_a_path_data_root_and_a_str_data_root_are_both_taken(tmp_path):
    first = start(document(), data_root=tmp_path / "")
    second = start(document(), data_root=str(tmp_path))
    assert first != second
    assert tree(tmp_path / "runs") == sorted(
        [first, f"{first}/instance.json", second, f"{second}/instance.json"]
    )


def test_n_max_is_filled_in_with_the_default_when_absent(tmp_path, ids):
    given = without("n_max")
    built = start(given, data_root=tmp_path)
    assert "n_max" not in given
    assert instance.read(tmp_path, built).n_max == measurement.N_MAX_DEFAULT
    stored = json.loads((tmp_path / "runs" / built / "instance.json").read_bytes())
    assert stored["n_max"] == measurement.N_MAX_DEFAULT


def test_a_given_n_max_is_kept(tmp_path, ids):
    built = start(document(n_max=7), data_root=tmp_path)
    assert instance.read(tmp_path, built).n_max == 7


def test_coder_model_is_filled_in_with_the_default_when_absent(tmp_path, ids):
    given = document()
    built = start(given, data_root=tmp_path)
    assert "coder_model" not in given
    assert instance.coder_model_of(tmp_path, built) == CODER_MODEL_DEFAULT


def test_a_given_coder_model_is_kept(tmp_path, ids):
    built = start(document(coder_model=TEST_CODER_MODEL), data_root=tmp_path)
    assert instance.coder_model_of(tmp_path, built) == TEST_CODER_MODEL
    stored = json.loads((tmp_path / "runs" / built / "instance.json").read_bytes())
    assert stored["coder_model"] == TEST_CODER_MODEL


def test_the_bytes_are_in_the_written_form(tmp_path, ids):
    built = start(document(label="é"), data_root=tmp_path)
    content = (tmp_path / "runs" / built / "instance.json").read_bytes()
    assert content.endswith(b"}\n")
    assert not content.endswith(b"\n\n")
    assert b"\r" not in content
    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.isascii()
    expected = {**document(label="é"), "coder_model": CODER_MODEL_DEFAULT}
    assert content == json.dumps(expected, indent=2).encode() + b"\n"
    instance.parse(content)


def test_undefined_members_are_kept(tmp_path, ids):
    extra = {"nested": [1, 2.5, None, True, MARKER]}
    built = start(document(note=MARKER, extra=extra), data_root=tmp_path)
    stored = json.loads((tmp_path / "runs" / built / "instance.json").read_bytes())
    assert stored["note"] == MARKER
    assert stored["extra"] == extra


def test_the_members_keep_the_order_of_the_document(tmp_path, ids):
    given = {"zz_first": 1, **document()}
    built = start(given, data_root=tmp_path)
    stored = json.loads((tmp_path / "runs" / built / "instance.json").read_bytes())
    assert list(stored) == [*given, "coder_model"]


def test_one_id_is_built_per_start(tmp_path, ids):
    start(document(), data_root=tmp_path)
    assert ids.calls == 1


@pytest.mark.parametrize(
    "given",
    [
        document(run_id=FIXED_ID),
        document(run_id="not a valid name"),
        document(run_id=None),
        document(run_id=MARKER),
        without(*REPORT_ORDER, run_id=FIXED_ID),
        without("tolerance", run_id=MARKER),
        without("n_max", run_id=FIXED_ID),
        document(accelerator=mock_backend.NAME, run_id=FIXED_ID),
    ],
)
def test_a_given_run_id_is_refused(tmp_path, ids, given):
    error = assert_refused(given, GivenRunIdError, tmp_path, ids)
    assert not isinstance(error, MissingMembersError)
    assert "run_id" in str(error)
    assert MARKER not in str(error)
    assert FIXED_ID not in str(error)
    assert error.__cause__ is None


def test_a_given_run_id_is_refused_without_building_an_id(tmp_path, monkeypatch):
    def refuse():
        raise AssertionError("an id was built")

    monkeypatch.setattr(run_id, "new", refuse)
    with pytest.raises(GivenRunIdError):
        start(document(run_id=FIXED_ID), data_root=tmp_path)
    assert tree(tmp_path) == []


def test_given_run_id_error_is_told_apart():
    for other in (ValueError, OSError, MissingMembersError, OutOfScopeError):
        assert not issubclass(GivenRunIdError, other)
    assert issubclass(GivenRunIdError, Exception)
    assert not issubclass(GivenRunIdError, RunIdInUseError)
    assert not issubclass(RunIdInUseError, GivenRunIdError)


def test_a_run_id_member_below_the_top_level_is_no_given_id(tmp_path, ids):
    built = start(document(extra={"run_id": MARKER}), data_root=tmp_path)
    assert built == FIXED_ID


def test_a_run_id_with_an_invalid_document_is_refused_as_invalid(tmp_path, ids):
    assert_refused(
        document(n_max=4, run_id=FIXED_ID), InvalidInstanceError, tmp_path, ids
    )


def test_a_run_id_out_of_scope_is_refused_as_out_of_scope(tmp_path, ids):
    given = document(accelerator="acc_other", run_id=FIXED_ID)
    assert_refused(given, OutOfScopeError, tmp_path, ids)


@pytest.mark.parametrize(
    ("given", "error"),
    [
        (document(n_max=4), InvalidInstanceError),
        (document(tolerance={"rtol": -1.0, "atol": 0.0}), InvalidInstanceError),
        ({"hw_profile": document()["hw_profile"]}, InvalidInstanceError),
        (document(schema_version=2), UnsupportedVersionError),
        (document(tolerance={"rtol": float("nan"), "atol": 0.0}), InvalidInstanceError),
    ],
)
def test_an_invalid_document_passes_through(tmp_path, ids, given, error):
    assert_refused(given, error, tmp_path, ids)


@pytest.mark.parametrize("given", [None, [], "{}", b"{}", 1])
def test_a_document_that_is_no_dict_is_a_type_error(tmp_path, ids, given):
    with pytest.raises(TypeError):
        start(given, data_root=tmp_path)
    assert tree(tmp_path) == []
    assert ids.calls == 0


def test_a_dict_subclass_is_a_type_error(tmp_path, ids):
    class Sub(dict):
        pass

    with pytest.raises(TypeError):
        start(Sub(document()), data_root=tmp_path)
    assert tree(tmp_path) == []
    assert ids.calls == 0


def test_another_accelerator_is_out_of_scope(tmp_path, ids):
    assert_refused(document(accelerator="acc_other"), OutOfScopeError, tmp_path, ids)


@pytest.mark.parametrize(
    "record",
    [
        {**RECORD, "dtype": "fp16"},
        {**RECORD, "layout": "col_major"},
    ],
)
def test_an_op_signature_that_is_not_covered_is_out_of_scope(tmp_path, ids, record):
    assert not gemm_contract.covers(record)
    assert_refused(document(op_signature=record), OutOfScopeError, tmp_path, ids)


@pytest.mark.parametrize(
    "missing",
    [
        ("op_signature",),
        ("objective",),
        ("candidates_per_round",),
        ("draws",),
        ("tolerance",),
        ("tolerance", "op_signature"),
        ("draws", "objective", "n_max"),
        REPORT_ORDER,
    ],
)
def test_missing_members_pass_through(tmp_path, ids, missing):
    error = assert_refused(without(*missing), MissingMembersError, tmp_path, ids)
    expected = tuple(name for name in REPORT_ORDER if name in missing)
    assert error.missing == expected
    assert type(error) is MissingMembersError


def test_the_errors_of_prepare_are_the_same_objects(tmp_path, monkeypatch, ids):
    raised = MissingMembersError(("draws",))

    def prepare(document, *, accelerators, covers):
        assert accelerators == (mock_backend.NAME, standin_profile.ACCELERATOR)
        assert covers is gemm_contract.covers
        raise raised

    monkeypatch.setattr(instance_start, "prepare", prepare)
    with pytest.raises(MissingMembersError) as caught:
        start(document(), data_root=tmp_path)
    assert caught.value is raised
    assert ids.calls == 0


def test_prepare_is_given_the_bound_accelerators_and_covers(tmp_path, monkeypatch, ids):
    seen = {}
    real = instance_start.prepare

    def prepare(document, *, accelerators, covers):
        seen.update(accelerators=accelerators, covers=covers)
        return real(document, accelerators=accelerators, covers=covers)

    monkeypatch.setattr(instance_start, "prepare", prepare)
    start(document(), data_root=tmp_path)
    assert type(seen["accelerators"]) is tuple
    assert set(seen["accelerators"]) == {mock_backend.NAME, standin_profile.ACCELERATOR}
    assert seen["covers"] is gemm_contract.covers


def test_a_taken_name_stops_the_start(tmp_path, fixed_sources, monkeypatch):
    calls = []
    real_new = run_id.new

    def counted():
        calls.append(None)
        return real_new()

    monkeypatch.setattr(run_id, "new", counted)
    directory = tmp_path / "runs" / FIXED_ID
    directory.mkdir(parents=True)
    existing = b"not even json \r\n" + MARKER.encode()
    (directory / "instance.json").write_bytes(existing)
    given = document()
    before = copy.deepcopy(given)
    with pytest.raises(RunIdInUseError) as caught:
        start(given, data_root=tmp_path)
    error = caught.value
    assert error.run_id == FIXED_ID
    assert not isinstance(error, OSError)
    assert not isinstance(error, instance_file.NameTakenError)
    assert FIXED_ID in str(error)
    assert "nothing was written" in str(error)
    assert MARKER not in str(error)
    assert error.__cause__ is None
    assert error.__suppress_context__
    assert (directory / "instance.json").read_bytes() == existing
    assert tree(tmp_path) == [
        "runs",
        f"runs/{FIXED_ID}",
        f"runs/{FIXED_ID}/instance.json",
    ]
    assert len(calls) == 1
    assert given == before


def test_run_id_in_use_error_is_told_apart():
    for other in (
        ValueError,
        OSError,
        MissingMembersError,
        OutOfScopeError,
        instance_file.NameTakenError,
    ):
        assert not issubclass(RunIdInUseError, other)
    error = RunIdInUseError(FIXED_ID)
    assert error.run_id == FIXED_ID
    assert FIXED_ID in str(error)


def test_a_data_root_that_does_not_exist_passes_through(tmp_path, ids):
    missing = tmp_path / "absent"
    with pytest.raises(FileNotFoundError):
        start(document(), data_root=missing)
    assert not missing.exists()
    assert ids.calls == 1


def test_a_data_root_that_is_a_file_passes_through(tmp_path, ids):
    file = tmp_path / "file"
    file.write_bytes(b"")
    with pytest.raises(NotADirectoryError):
        start(document(), data_root=file)
    assert tree(tmp_path) == ["file"]


@pytest.mark.parametrize(
    "raised",
    [OSError(5, "io"), PermissionError(13, "denied"), FileExistsError(17, "tmp")],
)
def test_an_os_error_of_the_write_passes_through(tmp_path, monkeypatch, ids, raised):
    def write_once(path, content):
        raise raised

    monkeypatch.setattr(once_write, "write_once", write_once)
    with pytest.raises(OSError) as caught:
        start(document(), data_root=tmp_path)
    assert caught.value is raised
    assert not (tmp_path / "runs" / FIXED_ID / "instance.json").exists()
    assert ids.calls == 1


def test_the_write_is_handed_the_built_id_and_the_bytes(tmp_path, monkeypatch, ids):
    seen = []
    monkeypatch.setattr(instance_file, "write", lambda *handed: seen.append(handed))
    given = without("n_max")
    assert start(given, data_root=tmp_path) == FIXED_ID
    ((root, built, content),) = seen
    assert root is tmp_path
    assert built == FIXED_ID
    assert json.loads(content) == {
        **given,
        "n_max": measurement.N_MAX_DEFAULT,
        "coder_model": CODER_MODEL_DEFAULT,
    }


def test_a_value_json_cannot_write_without_nan_is_refused_before_an_id(tmp_path, ids):
    for value in (float("nan"), float("inf"), -float("inf")):
        given = document(extra=value)
        instance.validate(given)
        before = copy.deepcopy(given)
        with pytest.raises(ValueError):
            start(given, data_root=tmp_path)
        assert repr(given) == repr(before)
    assert tree(tmp_path) == []
    assert ids.calls == 0


def test_a_value_json_cannot_write_at_all_is_refused_before_an_id(tmp_path, ids):
    with pytest.raises(TypeError):
        start(document(extra={1, 2}), data_root=tmp_path)
    assert tree(tmp_path) == []
    assert ids.calls == 0


def test_a_run_id_keyword_is_a_type_error(tmp_path, ids):
    given = document()
    before = copy.deepcopy(given)
    with pytest.raises(TypeError, match="run_id"):
        start(given, data_root=tmp_path, run_id=FIXED_ID)
    assert given == before
    assert tree(tmp_path) == []
    assert ids.calls == 0


def test_a_positional_data_root_is_a_type_error(tmp_path, ids):
    given = document()
    with pytest.raises(TypeError):
        start(given, tmp_path)
    assert tree(tmp_path) == []
    assert ids.calls == 0


def test_a_missing_data_root_is_a_type_error(ids):
    with pytest.raises(TypeError):
        start(document())
    assert ids.calls == 0


def test_the_public_surface():
    parameters = inspect.signature(start).parameters
    assert list(parameters) == ["document", "data_root"]
    assert parameters["data_root"].kind is inspect.Parameter.KEYWORD_ONLY
    assert parameters["data_root"].default is inspect.Parameter.empty
    assert all(
        parameter.kind is not inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )


def test_the_module_is_no_registered_tool():
    from hilclaw import tools

    source = Path(tools.__file__).read_text(encoding="utf-8")
    assert "start_instance" not in source
