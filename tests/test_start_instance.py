import copy
import datetime
import hashlib
import inspect
import json
import re
from pathlib import Path

import pytest

from hilclaw import (
    artifacts,
    bring_in,
    cas,
    contract_table,
    elementwise_add_bf16_contract,
    gemm_bf16_contract,
    gemm_contract,
    instance,
    instance_file,
    instance_start,
    keys,
    layout,
    mock_backend,
    once_write,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    run_id,
    sdpa_kv_cache_bf16_contract,
    standin_profile,
    swiglu_bf16_contract,
    targets,
)
from hilclaw.harness import measurement
from hilclaw.instance import InvalidInstanceError, UnsupportedVersionError
from hilclaw.instance_start import (
    CODER_MODEL_DEFAULT,
    REPORT_ORDER,
    MissingMembersError,
    OutOfScopeError,
)
from hilclaw.start_instance import (
    GIVEN_CODE_TYPE,
    GivenCodeFileError,
    GivenCodeNotAdmittedError,
    GivenCodeUnrecordedError,
    GivenRunIdError,
    RunIdInUseError,
    start,
)

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
        (document(schema_version=3), UnsupportedVersionError),
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


def test_fp32_gemm_at_virtual_npu_is_out_of_scope(tmp_path, ids):
    """ADR-0197 decision 3: virtual_npu does not serve the fp32 gemm contract."""
    assert contract_table.start_covers(RECORD)
    given = document(accelerator=targets.VIRTUAL_NPU)
    error = assert_refused(given, OutOfScopeError, tmp_path, ids)
    assert str(error).startswith("op_signature:")


def test_an_instance_at_virtual_npu_lacking_members_is_refused_as_at_cpu_standin(
    tmp_path, ids
):
    for accelerator in (targets.VIRTUAL_NPU, standin_profile.ACCELERATOR):
        given = without(
            "draws", "tolerance", accelerator=accelerator, op_signature=BF16_RECORDS[1]
        )
        error = assert_refused(given, MissingMembersError, tmp_path, ids)
        assert error.missing == ("draws", "tolerance")


def test_an_instance_at_virtual_npu_with_no_op_signature_is_missing_it(tmp_path, ids):
    given = without("op_signature", accelerator=targets.VIRTUAL_NPU)
    error = assert_refused(given, MissingMembersError, tmp_path, ids)
    assert error.missing == ("op_signature",)


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
        assert accelerators == (
            mock_backend.NAME,
            standin_profile.ACCELERATOR,
            targets.VIRTUAL_NPU,
        )
        assert covers(RECORD) is True
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
    assert set(seen["accelerators"]) == {
        mock_backend.NAME,
        standin_profile.ACCELERATOR,
        targets.VIRTUAL_NPU,
    }
    covers = seen["covers"]
    assert covers(RECORD) is True
    assert covers(BF16_RECORDS[0]) is True
    assert covers({**RECORD, "dtype": "fp16"}) is False


def test_the_bound_covers_reads_the_accelerator_of_the_document(monkeypatch):
    seen = []

    def prepare(document, *, accelerators, covers):
        seen.append(covers)
        raise MissingMembersError(("draws",))

    monkeypatch.setattr(instance_start, "prepare", prepare)
    for accelerator in (targets.VIRTUAL_NPU, standin_profile.ACCELERATOR):
        with pytest.raises(MissingMembersError):
            start(document(accelerator=accelerator), data_root="unused")
    at_virtual, at_standin = seen
    assert at_virtual(RECORD) is False
    assert at_standin(RECORD) is True
    for record in BF16_RECORDS:
        assert at_virtual(record) is True
        assert at_standin(record) is True


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
    assert list(parameters) == ["document", "data_root", "code_file"]
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


# A bf16 record in the slice of ADR-0177 decision 2

BF16_RECORDS = (
    gemm_bf16_contract.op_signature_record(*gemm_bf16_contract.SHAPES[0]),
    rmsnorm_bf16_contract.op_signature_record(*rmsnorm_bf16_contract.SHAPES[0]),
    elementwise_add_bf16_contract.op_signature_record(
        *elementwise_add_bf16_contract.SHAPES[0]
    ),
    swiglu_bf16_contract.op_signature_record(*swiglu_bf16_contract.SHAPES[0]),
    rope_bf16_contract.op_signature_record(*rope_bf16_contract.SHAPES[0]),
    sdpa_kv_cache_bf16_contract.op_signature_record(
        *sdpa_kv_cache_bf16_contract.SHAPES[0]
    ),
)
BF16_IDS = [record["kind"] for record in BF16_RECORDS]


@pytest.mark.parametrize("record", BF16_RECORDS, ids=BF16_IDS)
def test_a_bf16_record_is_admitted_by_the_start(tmp_path, ids, record):
    assert contract_table.start_covers(record)
    built = start(document(op_signature=record), data_root=tmp_path)
    assert instance.read(tmp_path, built).op_signature.record == record


@pytest.mark.parametrize("record", BF16_RECORDS, ids=BF16_IDS)
def test_a_record_of_another_dtype_is_out_of_scope_of_the_start(tmp_path, ids, record):
    other = {**record, "dtype": "fp16"}
    assert not contract_table.covers(other)
    assert not contract_table.start_covers(other)
    assert_refused(document(op_signature=other), OutOfScopeError, tmp_path, ids)


def test_the_admitted_accelerators_are_the_mock_and_the_targets_that_start():
    from hilclaw import start_instance, targets

    assert start_instance._ACCELERATORS == (
        mock_backend.NAME,
        *targets.instance_start_accelerators(),
    )
    assert start_instance._ACCELERATORS == ("mock", "cpu_standin", "virtual_npu")


@pytest.mark.parametrize("record", BF16_RECORDS, ids=BF16_IDS)
def test_a_bf16_instance_at_virtual_npu_is_started(tmp_path, ids, record):
    """ADR-0197 decision 1: the required set is cpu_standin's."""
    given = document(accelerator=targets.VIRTUAL_NPU, op_signature=record)
    built = start(given, data_root=tmp_path)
    read = instance.read(tmp_path, built)
    assert read.hw_profile["accelerator"] == targets.VIRTUAL_NPU
    assert read.op_signature.record == record
    assert ids.calls == 1


def test_an_unknown_accelerator_is_still_out_of_scope_with_a_bf16_record(tmp_path, ids):
    given = document(accelerator="npu_other", op_signature=BF16_RECORDS[0])
    error = assert_refused(given, OutOfScopeError, tmp_path, ids)
    assert str(error).startswith("hw_profile.record.accelerator:")


# The candidate kind of ADR-0198 decision 7


def kinded(kind="compile_settings", version=2, **changes):
    made = document(**changes)
    made["schema_version"] = version
    made["candidate_kind"] = kind
    return made


def stored_bytes(root, built):
    return (root / "runs" / built / "instance.json").read_bytes()


@pytest.mark.parametrize(
    ("accelerator", "record"),
    [
        (standin_profile.ACCELERATOR, RECORD),
        (mock_backend.NAME, RECORD),
        (targets.VIRTUAL_NPU, BF16_RECORDS[0]),
    ],
)
def test_a_compile_settings_start_writes_version_2(tmp_path, ids, accelerator, record):
    given = kinded(accelerator=accelerator, op_signature=record)
    before = copy.deepcopy(given)
    built = start(given, data_root=tmp_path)
    assert given == before
    assert ids.calls == 1
    assert tree(tmp_path) == ["runs", f"runs/{built}", f"runs/{built}/instance.json"]
    expected = {**given, "coder_model": CODER_MODEL_DEFAULT}
    assert stored_bytes(tmp_path, built) == (
        json.dumps(expected, indent=2).encode() + b"\n"
    )
    read = instance.read_kinded(tmp_path, built)
    assert read.schema_version == instance.KIND_SCHEMA_VERSION
    assert read.candidate_kind == "compile_settings"
    assert read.layout_version == 1
    assert read.instance.hw_profile["accelerator"] == accelerator
    assert read.instance.op_signature.record == record
    assert read.instance.others == {}
    assert instance.candidate_kind_of(tmp_path, built) == "compile_settings"


def test_a_strict_reader_still_refuses_a_run_the_start_wrote_as_version_2(
    tmp_path, ids
):
    built = start(kinded(), data_root=tmp_path)
    with pytest.raises(UnsupportedVersionError):
        instance.read(tmp_path, built)
    with pytest.raises(UnsupportedVersionError):
        instance.layout_version_of(tmp_path, built)


@pytest.mark.parametrize("named", [True, False], ids=["c_kernel", "no_kind"])
def test_a_start_naming_no_kind_or_c_kernel_writes_the_bytes_of_today(
    tmp_path, fixed_sources, named
):
    given = kinded("c_kernel", 1) if named else document()
    today = tmp_path / "today"
    today.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    built = start(given, data_root=other)
    assert start(document(), data_root=today) == built
    assert stored_bytes(other, built) == stored_bytes(today, built)
    assert b"candidate_kind" not in stored_bytes(other, built)
    assert instance.read(other, built).others == {}
    assert instance.candidate_kind_of(other, built) == "c_kernel"


@pytest.mark.parametrize(
    ("version", "kind", "error"),
    [
        (1, "compile_settings", InvalidInstanceError),
        (1, "vendor_kernel", InvalidInstanceError),
        (2, "c_kernel", InvalidInstanceError),
        (2, "vendor_kernel", InvalidInstanceError),
        (2, ABSENT, InvalidInstanceError),
        (3, "compile_settings", UnsupportedVersionError),
    ],
)
def test_a_contradictory_or_unknown_kind_is_refused_and_nothing_is_built(
    tmp_path, ids, version, kind, error
):
    given = kinded(kind, version)
    if kind is ABSENT:
        del given["candidate_kind"]
    assert_refused(given, error, tmp_path, ids)


def test_a_version_2_start_at_another_accelerator_is_out_of_scope(tmp_path, ids):
    assert_refused(kinded(accelerator="acc_other"), OutOfScopeError, tmp_path, ids)


def test_a_version_2_start_with_an_uncovered_op_signature_is_out_of_scope(
    tmp_path, ids
):
    other = {**RECORD, "dtype": "fp16"}
    assert_refused(kinded(op_signature=other), OutOfScopeError, tmp_path, ids)


def test_a_version_2_start_lacking_members_reports_them(tmp_path, ids):
    given = kinded(draws=ABSENT, tolerance=ABSENT)
    error = assert_refused(given, MissingMembersError, tmp_path, ids)
    assert error.missing == ("draws", "tolerance")


def test_a_version_2_start_with_a_run_id_is_refused_as_a_given_id(tmp_path, ids):
    assert_refused(kinded(run_id=FIXED_ID), GivenRunIdError, tmp_path, ids)


# Given code (ADR-0200 decisions 5 and 6, slice 2)

CODE = b"int given(void) { return 0; }\n"
DIGEST = hashlib.sha256(CODE).hexdigest()


def code_file(tmp_path, content=CODE, name="given.c"):
    path = tmp_path / "input" / name
    path.parent.mkdir(exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "data"
    path.mkdir()
    return path


def one(**changes):
    return document(candidates_per_round=1, **changes)


def assert_given_refused(given, error, root, ids, path):
    before = copy.deepcopy(given)
    with pytest.raises(error) as caught:
        start(given, data_root=root, code_file=path)
    assert given == before
    assert tree(root) == []
    assert ids.calls == 0
    return caught.value


@pytest.mark.parametrize("candidate_kind", [ABSENT, "c_kernel"])
def test_given_code_is_stored_written_and_recorded(
    tmp_path, root, fixed_sources, candidate_kind
):
    given = one()
    if candidate_kind is not ABSENT:
        given["candidate_kind"] = candidate_kind
    before = copy.deepcopy(given)
    built = start(given, data_root=root, code_file=code_file(tmp_path))
    assert built == FIXED_ID
    assert given == before
    blob = f"blobs/sha256/{DIGEST[:2]}/{DIGEST}"
    assert tree(root) == [
        "blobs",
        "blobs/sha256",
        f"blobs/sha256/{DIGEST[:2]}",
        blob,
        "runs",
        f"runs/{built}",
        f"runs/{built}/artifacts.json",
        f"runs/{built}/instance.json",
    ]
    assert (root / blob).read_bytes() == CODE
    assert cas.verify_blob(root, DIGEST)
    read = instance.read_given(root, built)
    assert read.schema_version == instance.GIVEN_SCHEMA_VERSION == 3
    assert read.candidate_kind == "c_kernel"
    assert read.given_code == DIGEST
    assert read.layout_version == 1
    assert read.instance.others == {}
    assert read.instance.coder_model == CODER_MODEL_DEFAULT
    assert read.instance.n_max == TEST_N_MAX
    assert instance.given_code_of(root, built) == DIGEST
    stored = json.loads(stored_bytes(root, built))
    instance.validate_given(stored)
    assert next(iter(stored)) == "schema_version"
    assert list(stored)[-1] == "given_code"
    assert "candidate_kind" not in stored
    assert artifacts.load(root, built) == [
        {
            "sha256": DIGEST,
            "size": len(CODE),
            "type": "given_code",
            "round": 0,
            "retention_class": "final",
        }
    ]
    for strict in (instance.read, instance.read_kinded):
        with pytest.raises(UnsupportedVersionError):
            strict(root, built)


def test_the_written_bytes_are_those_without_given_code_but_two_members(tmp_path, root):
    plain = start(one(), data_root=root)
    given = start(one(), data_root=root, code_file=code_file(tmp_path))
    without_code = json.loads(stored_bytes(root, plain))
    with_code = json.loads(stored_bytes(root, given))
    assert with_code.pop("given_code") == DIGEST
    assert with_code.pop("schema_version") == 3
    assert without_code.pop("schema_version") == 1
    assert with_code == without_code


def test_the_three_writes_come_in_the_order_of_decision_5(tmp_path, root, monkeypatch):
    order = []

    def spied(module, name):
        real = getattr(module, name)

        def call(*args, **kwargs):
            order.append(name)
            if name == "write":
                assert cas.has_blob(root, DIGEST)
            if name == "add_record":
                assert (root / "runs" / args[1] / "instance.json").is_file()
            return real(*args, **kwargs)

        monkeypatch.setattr(module, name, call)

    spied(cas, "put_bytes")
    spied(instance_file, "write")
    spied(artifacts, "add_record")
    spied(run_id, "new")
    start(one(), data_root=root, code_file=code_file(tmp_path))
    assert order == ["put_bytes", "new", "write", "add_record"]


def test_a_file_of_exactly_the_limit_is_taken(tmp_path, root):
    content = b"x" * bring_in.MAX_FILE_BYTES
    path = str(code_file(tmp_path, content))
    built = start(one(), data_root=root, code_file=path)
    assert instance.given_code_of(root, built) == hashlib.sha256(content).hexdigest()


def test_an_empty_file_is_taken_as_given(tmp_path, root):
    built = start(one(), data_root=root, code_file=code_file(tmp_path, b""))
    assert artifacts.load(root, built)[0]["size"] == 0


def test_a_file_over_the_limit_is_refused(tmp_path, root, ids):
    path = code_file(tmp_path, b"x" * (bring_in.MAX_FILE_BYTES + 1))
    error = assert_given_refused(one(), GivenCodeFileError, root, ids, path)
    assert str(bring_in.MAX_FILE_BYTES) in error.reason
    assert not isinstance(error, OSError)


@pytest.mark.parametrize("name", ["absent.c", "directory", "bad\0name"])
def test_a_file_that_cannot_be_read_is_refused(tmp_path, root, ids, name):
    (tmp_path / "directory").mkdir()
    path = tmp_path / name if "\0" not in name else str(tmp_path) + "/" + name
    error = assert_given_refused(one(), GivenCodeFileError, root, ids, path)
    assert "cannot be read" in error.reason
    assert not isinstance(error, OSError)


def test_the_file_is_read_before_the_document_is_checked(tmp_path, root, ids):
    path = tmp_path / "absent.c"
    assert_given_refused(one(n_max=4), GivenCodeFileError, root, ids, path)


@pytest.mark.parametrize(
    ("given", "error"),
    [
        (kinded(candidates_per_round=1), GivenCodeNotAdmittedError),
        (document(candidates_per_round=2), GivenCodeNotAdmittedError),
        (one(given_code=DIGEST), InvalidInstanceError),
        (one(schema_version=3, given_code=DIGEST), UnsupportedVersionError),
        (one(schema_version=3), UnsupportedVersionError),
        (one(n_max=4), InvalidInstanceError),
        (one(accelerator="acc_other"), OutOfScopeError),
        (without("draws", candidates_per_round=1), MissingMembersError),
        (one(run_id=FIXED_ID), GivenRunIdError),
        (document(candidates_per_round=2, run_id=FIXED_ID), GivenRunIdError),
        (one(extra=float("nan")), ValueError),
    ],
    ids=[
        "compile_settings",
        "two candidates",
        "given_code at version 1",
        "given_code at version 3",
        "version 3 without given_code",
        "invalid",
        "out of scope",
        "missing members",
        "run_id",
        "run_id before the admission",
        "unwritable value",
    ],
)
def test_every_refusal_with_given_code_writes_nothing(
    tmp_path, root, ids, given, error
):
    assert_given_refused(given, error, root, ids, code_file(tmp_path))


def test_compile_settings_is_refused_by_name(tmp_path, root, ids):
    path = code_file(tmp_path)
    given = kinded(candidates_per_round=1)
    error = assert_given_refused(given, GivenCodeNotAdmittedError, root, ids, path)
    assert "compile_settings" in str(error)
    assert not isinstance(error, (OSError, ValueError))


def test_two_candidates_are_refused_by_name(tmp_path, root, ids):
    path = code_file(tmp_path)
    given = document(candidates_per_round=2)
    error = assert_given_refused(given, GivenCodeNotAdmittedError, root, ids, path)
    assert "candidates_per_round" in str(error)


def test_a_missing_data_root_with_given_code_writes_nothing(tmp_path, ids):
    absent = tmp_path / "absent"
    with pytest.raises(FileNotFoundError):
        start(one(), data_root=absent, code_file=code_file(tmp_path))
    assert not absent.exists()
    assert ids.calls == 0


def test_a_failed_record_leaves_the_blob_and_the_instance(
    tmp_path, root, fixed_sources, monkeypatch
):
    failure = OSError("injected")

    def failed(*args, **kwargs):
        raise failure

    monkeypatch.setattr(artifacts, "add_record", failed)
    with pytest.raises(GivenCodeUnrecordedError) as caught:
        start(one(), data_root=root, code_file=code_file(tmp_path))
    error = caught.value
    assert error.run_id == FIXED_ID
    assert error.reason == "OSError: injected"
    assert FIXED_ID in str(error)
    assert error.__cause__ is failure
    assert not isinstance(error, OSError)
    assert cas.has_blob(root, DIGEST)
    assert instance.given_code_of(root, FIXED_ID) == DIGEST
    assert not (root / "runs" / FIXED_ID / "artifacts.json").exists()


def test_a_taken_name_with_given_code_leaves_the_blob(tmp_path, root, fixed_sources):
    directory = root / "runs" / FIXED_ID
    directory.mkdir(parents=True)
    (directory / "instance.json").write_bytes(b"taken")
    with pytest.raises(RunIdInUseError):
        start(one(), data_root=root, code_file=code_file(tmp_path))
    assert (directory / "instance.json").read_bytes() == b"taken"
    assert not (directory / "artifacts.json").exists()
    assert cas.has_blob(root, DIGEST)


def test_prepare_is_handed_given_code_only_with_a_file(tmp_path, root, monkeypatch):
    seen = []
    real = instance_start.prepare

    def prepare(document, **options):
        seen.append(options.get("given_code", ABSENT))
        return real(document, **options)

    monkeypatch.setattr(instance_start, "prepare", prepare)
    start(one(), data_root=root)
    start(one(), data_root=root, code_file=code_file(tmp_path))
    assert seen == [ABSENT, DIGEST]


def test_the_given_code_type_is_a_valid_artifacts_type():
    assert GIVEN_CODE_TYPE == "given_code"
    record = {
        "sha256": DIGEST,
        "size": len(CODE),
        "type": GIVEN_CODE_TYPE,
        "round": 0,
        "retention_class": "final",
    }
    artifacts.validate(
        {"schema_version": artifacts.SCHEMA_VERSION, "artifacts": [record]}
    )
