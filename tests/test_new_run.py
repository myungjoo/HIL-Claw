import copy
import dataclasses
import datetime
import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hilclaw import (
    artifacts,
    bring_in,
    cas,
    instance,
    keys,
    once_write,
    run_id,
    standin_profile,
    start_instance,
    targets,
)
from hilclaw.instance_start import REPORT_ORDER
from hilclaw.new_run import (
    BAD_GIVEN_CODE,
    BAD_INPUT,
    BAD_USAGE,
    EXIT_STATUS,
    FAULT,
    FILE_SYSTEM,
    GIVEN_CODE_OPTION,
    GIVEN_CODE_REFUSED,
    GIVEN_CODE_UNRECORDED,
    GIVEN_RUN_ID,
    INVALID,
    MISSING_MEMBERS,
    NO_DATA_ROOT,
    OUT_OF_SCOPE,
    RUN_ID_IN_USE,
    STARTED,
    UNREADABLE_INPUT,
    UNWRITABLE_VALUE,
    _started,
    main,
)

ABSENT = object()
# Test values only: none is a default or a recommended value.
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


def document(
    accelerator=standin_profile.ACCELERATOR,
    draws=3,
    tolerance=ABSENT,
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
        "op_signature": {
            "key": keys.op_signature_key(RECORD).name,
            "record": copy.deepcopy(RECORD),
        },
        "objective": copy.deepcopy(OBJECTIVE),
        "candidates_per_round": 1,
        "n_max": 12,
        "draws": draws,
        "tolerance": {"rtol": 0.25, "atol": 3.0} if tolerance is ABSENT else tolerance,
    }
    for name in ("draws", "tolerance"):
        if made[name] is None:
            del made[name]
    made.update(others)
    return made


def tree(root):
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))


class Source:
    def __init__(self, root=None, error=None):
        self.root = root
        self.error = error
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.root


class Ran:
    def __init__(self, status, stdout, stderr, source):
        self.status = status
        self.lines = stdout.getvalue().splitlines()
        self.stderr = stderr.getvalue().decode("utf-8")
        self.source = source

    @property
    def told(self):
        assert len(self.lines) == 1
        assert self.lines[0].isascii()
        assert self.status not in (1, 2)
        assert "Traceback" not in self.stderr
        return json.loads(self.lines[0])


@pytest.fixture
def root(tmp_path):
    directory = tmp_path / "data"
    directory.mkdir()
    return directory


@pytest.fixture
def given(tmp_path):
    def written(content):
        path = tmp_path / "inst.json"
        if not isinstance(content, bytes):
            content = json.dumps(content).encode("utf-8")
        path.write_bytes(content)
        return str(path)

    return written


@pytest.fixture
def fixed_sources(monkeypatch):
    monkeypatch.setattr(run_id, "_utc_now", lambda: TIME)
    monkeypatch.setattr(run_id.secrets, "randbits", lambda bits: BITS)


class Recorder:
    def __init__(self, answer=FIXED_ID, error=None):
        self.answer = answer
        self.error = error
        self.calls = []

    def __call__(self, document, **options):
        self.calls.append((copy.deepcopy(document), options))
        if self.error is not None:
            raise self.error
        return self.answer


@pytest.fixture
def recorder(monkeypatch):
    def made(**options):
        recording = Recorder(**options)
        monkeypatch.setattr(start_instance, "start", recording)
        return recording

    return made


def run(args, root=None, source=None, stdout=None):
    stdout = io.BytesIO() if stdout is None else stdout
    stderr = io.BytesIO()
    source = Source(root) if source is None else source
    status = main(list(args), source=source, stdout=stdout, stderr=stderr)
    return Ran(status, stdout, stderr, source)


def assert_refused(ran, root, outcome, **members):
    assert ran.told == {"outcome": outcome, **members}
    assert ran.status == EXIT_STATUS[outcome]
    assert ran.status != 0
    assert ran.stderr == ""
    assert tree(root) == []


def test_a_valid_document_is_started(tmp_path, root, given):
    content = document()
    ran = run([given(content)], root)
    told = ran.told
    assert ran.status == 0
    assert ran.stderr == ""
    assert set(told) == {"outcome", "run_id"}
    assert told["outcome"] == STARTED
    built = told["run_id"]
    assert tree(root) == ["runs", f"runs/{built}", f"runs/{built}/instance.json"]
    other = tmp_path / "other"
    other.mkdir()
    expected = start_instance.start(copy.deepcopy(content), data_root=other)
    written = json.loads((root / "runs" / built / "instance.json").read_bytes())
    assert written == json.loads(
        (other / "runs" / expected / "instance.json").read_bytes()
    )
    assert instance.read(root, built).draws == 3
    assert ran.source.calls == 1


def test_the_document_is_handed_on_unchanged_and_the_source_asked_once(
    root, given, recorder
):
    content = document(extra={"nested": [1, "two", None, True]})
    recording = recorder()
    ran = run([given(content)], root)
    assert ran.told == {"outcome": STARTED, "run_id": FIXED_ID}
    ((handed, options),) = recording.calls
    assert handed == content
    assert options == {"data_root": Path(root)}
    assert ran.source.calls == 1


def test_a_given_run_id_starts_nothing(root, given):
    assert_refused(run([given(document(run_id="abc"))], root), root, GIVEN_RUN_ID)


def test_missing_members_are_listed_in_report_order(root, given):
    ran = run([given(document(tolerance=None, draws=None))], root)
    assert_refused(ran, root, MISSING_MEMBERS, missing=["draws", "tolerance"])
    assert REPORT_ORDER.index("draws") < REPORT_ORDER.index("tolerance")


@pytest.mark.parametrize(
    "content",
    [
        document(n_max=4),
        document(schema_version=2),
        json.dumps(document()).replace('"rtol": 0.25', '"rtol": 1e400').encode(),
    ],
)
def test_an_invalid_document_starts_nothing(root, given, content):
    ran = run([given(content)], root)
    assert ran.told["outcome"] == INVALID
    assert set(ran.told) == {"outcome", "reason"}
    assert ran.status == EXIT_STATUS[INVALID]
    assert tree(root) == []


def test_an_accelerator_outside_the_first_case_is_out_of_scope(root, given):
    ran = run([given(document(accelerator="acc_other"))], root)
    assert ran.told["outcome"] == OUT_OF_SCOPE
    assert "accelerator" in ran.told["reason"]
    assert ran.status == EXIT_STATUS[OUT_OF_SCOPE]
    assert tree(root) == []


def test_a_taken_name_is_run_id_in_use(root, given, fixed_sources):
    directory = root / "runs" / FIXED_ID
    directory.mkdir(parents=True)
    (directory / "instance.json").write_bytes(b"taken")
    ran = run([given(document())], root)
    assert ran.told == {"outcome": RUN_ID_IN_USE, "run_id": FIXED_ID}
    assert ran.status == EXIT_STATUS[RUN_ID_IN_USE]
    assert (directory / "instance.json").read_bytes() == b"taken"
    assert tree(root) == ["runs", f"runs/{FIXED_ID}", f"runs/{FIXED_ID}/instance.json"]


def test_an_os_error_of_the_write_is_file_system(root, given, monkeypatch):
    def failed(path, content):
        raise PermissionError(13, "denied")

    monkeypatch.setattr(once_write, "write_once", failed)
    ran = run([given(document())], root)
    assert ran.told["outcome"] == FILE_SYSTEM
    assert "PermissionError" in ran.told["reason"]
    assert ran.status == EXIT_STATUS[FILE_SYSTEM]
    assert not list(root.rglob("instance.json"))


def test_an_infinity_in_an_undefined_member_is_unwritable(root, given):
    content = json.dumps(document(extra=1)).replace('"extra": 1', '"extra": 1e400')
    ran = run([given(content.encode())], root)
    assert ran.told["outcome"] == UNWRITABLE_VALUE
    assert ran.status == EXIT_STATUS[UNWRITABLE_VALUE]
    assert tree(root) == []


@pytest.mark.parametrize("args", [[], ["a", "b"]])
def test_not_one_argument_is_bad_usage(root, args, recorder):
    recording = recorder()
    ran = run(args, root)
    assert ran.told["outcome"] == BAD_USAGE
    assert str(len(args)) in ran.told["reason"]
    assert ran.status == EXIT_STATUS[BAD_USAGE]
    assert ran.source.calls == 0
    assert recording.calls == []


@pytest.mark.parametrize("name", ["absent.json", ".", "bad\0name"])
def test_a_file_that_cannot_be_read_is_unreadable_input(tmp_path, root, recorder, name):
    recording = recorder()
    ran = run([str(tmp_path / name)], root)
    assert ran.told["outcome"] == UNREADABLE_INPUT
    assert ran.status == EXIT_STATUS[UNREADABLE_INPUT]
    assert ran.source.calls == 0
    assert recording.calls == []
    assert tree(root) == []


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xfe{}",
        b'{"a": "\xc3"}',
        b"{",
        b"",
        b"{} {}",
        b"[1, 2]",
        b'"a string"',
        b"null",
        b"3",
        b"\xef\xbb\xbf{}",
        b'{"a": 1, "a": 1}',
        b'{"a": {"b": 1, "b": 2}}',
        b'{"a": [{"b": 1, "b": 2}]}',
        b'{"a": NaN}',
        b'{"a": Infinity}',
        b'{"a": -Infinity}',
    ],
)
def test_bytes_that_give_no_json_object_are_bad_input(root, given, recorder, content):
    recording = recorder()
    ran = run([given(content)], root)
    assert ran.told["outcome"] == BAD_INPUT
    assert ran.status == EXIT_STATUS[BAD_INPUT]
    assert ran.source.calls == 0
    assert recording.calls == []


def test_nesting_too_deep_to_parse_is_bad_input(root, given, recorder):
    recording = recorder()
    ran = run([given(b"[" * 100000 + b"]" * 100000)], root)
    assert ran.told["outcome"] == BAD_INPUT
    assert recording.calls == []


def test_the_bad_input_reasons_name_the_rule(root, given):
    for content, word in [
        (b"\xef\xbb\xbf{}", "BOM"),
        (b'{"a": 1, "a": 2}', "twice"),
        (b'{"a": NaN}', "NaN"),
        (b"[1]", "list"),
    ]:
        assert word in run([given(content)], root).told["reason"]


@pytest.mark.parametrize(
    "source",
    [
        Source(error=RuntimeError("no config")),
        Source(root="absent-directory-zq7"),
        Source(root=""),
        Source(root=7),
    ],
)
def test_a_data_root_that_cannot_be_obtained_starts_nothing(
    tmp_path, given, recorder, source
):
    recording = recorder()
    ran = run([given(document())], source=source)
    assert ran.told["outcome"] == NO_DATA_ROOT
    assert ran.status == EXIT_STATUS[NO_DATA_ROOT]
    assert source.calls == 1
    assert recording.calls == []
    assert tree(tmp_path) == ["inst.json"]


def test_a_source_that_is_not_callable_is_a_fault(given, recorder):
    recording = recorder()
    ran = run([given(document())], source="not callable")
    assert ran.told == {"outcome": FAULT, "fault": "TypeError"}
    assert ran.status == EXIT_STATUS[FAULT]
    assert recording.calls == []


@pytest.mark.parametrize(
    "error", [RuntimeError("boom zq7"), TypeError("t"), KeyError("k")]
)
def test_any_other_exception_of_start_is_a_fault(root, given, recorder, error):
    recorder(error=error)
    ran = run([given(document())], root)
    assert ran.told == {"outcome": FAULT, "fault": type(error).__name__}
    assert ran.status == EXIT_STATUS[FAULT]
    assert ran.stderr == ""


def test_a_value_error_subclass_of_start_is_no_unwritable_value(root, given, recorder):
    class Other(ValueError):
        pass

    recorder(error=Other("x"))
    assert run([given(document())], root).told == {"outcome": FAULT, "fault": "Other"}


def test_a_plain_value_error_of_start_is_unwritable_value(root, given, recorder):
    recorder(error=ValueError("Out of range float values are not JSON compliant"))
    ran = run([given(document())], root)
    assert ran.told["outcome"] == UNWRITABLE_VALUE
    assert "JSON compliant" in ran.told["reason"]


def test_an_exception_whose_text_fails_is_still_reported(root, given, recorder):
    class Wordless(OSError):
        def __str__(self):
            raise RuntimeError("no words")

    recorder(error=Wordless())
    assert run([given(document())], root).told == {
        "outcome": FILE_SYSTEM,
        "reason": "Wordless",
    }


@pytest.mark.parametrize("missing", ["none", "no_buffer"])
def test_a_missing_standard_output_is_a_fault_before_anything(
    root, given, recorder, monkeypatch, missing
):
    recording = recorder()
    source = Source(root)
    monkeypatch.setattr(sys, "stdout", None if missing == "none" else object())
    stderr = io.BytesIO()
    status = main([given(document())], source=source, stderr=stderr)
    assert status == EXIT_STATUS[FAULT]
    said = stderr.getvalue().decode("utf-8")
    assert said.count("\n") == 1
    assert "no standard output" in said
    assert "Traceback" not in said
    assert recording.calls == []
    assert source.calls == 0
    assert tree(root) == []


def test_a_missing_standard_error_is_tolerated(given, recorder, monkeypatch):
    recorder()
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    assert main([given(document())], source=Source()) == EXIT_STATUS[FAULT]


class Failing:
    def __init__(self, short=False):
        self.short = short

    def write(self, data):
        if self.short:
            return len(data) - 1
        raise OSError("broken pipe zq7")

    def flush(self):
        pass


@pytest.mark.parametrize("short", [False, True])
def test_a_failed_line_after_a_start_names_the_run_id(root, given, short):
    stderr = io.BytesIO()
    status = main(
        [given(document())], source=Source(root), stdout=Failing(short), stderr=stderr
    )
    assert status == EXIT_STATUS[FAULT]
    assert status not in (0, 1, 2)
    said = stderr.getvalue().decode("utf-8")
    assert said.count("\n") == 1
    (built,) = [path.name for path in (root / "runs").iterdir()]
    assert built in said
    assert "was started" in said
    assert "Traceback" not in said


def test_a_failed_line_before_any_start_is_said(root):
    stderr = io.BytesIO()
    status = main([], source=Source(root), stdout=Failing(), stderr=stderr)
    assert status == EXIT_STATUS[FAULT]
    said = stderr.getvalue().decode("utf-8")
    assert "cannot write standard output" in said
    assert "was started" not in said


def test_the_statuses_are_distinct_and_only_started_is_zero():
    statuses = list(EXIT_STATUS.values())
    assert len(set(statuses)) == len(statuses) == 16
    assert [k for k, v in EXIT_STATUS.items() if v == 0] == [STARTED]
    assert not {1, 2} & set(statuses)
    assert all(0 <= status < 256 for status in statuses)


def test_argv_defaults_to_the_process_arguments(root, given, monkeypatch, recorder):
    recording = recorder()
    path = given(document())
    monkeypatch.setattr(sys, "argv", ["new_run", path])
    stdout, stderr = io.BytesIO(), io.BytesIO()
    assert main(source=Source(root), stdout=stdout, stderr=stderr) == 0
    assert len(recording.calls) == 1
    monkeypatch.setattr(sys, "argv", ["new_run"])
    stdout = io.BytesIO()
    assert main(source=Source(root), stdout=stdout, stderr=stderr) == 20
    assert json.loads(stdout.getvalue())["outcome"] == BAD_USAGE


def test_a_keyboard_interrupt_of_start_propagates(root, given, recorder):
    recorder(error=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        run([given(document())], root)


def test_the_module_runs_as_a_command():
    done = subprocess.run(
        [sys.executable, "-m", "hilclaw.new_run"],
        capture_output=True,
        check=False,
        timeout=60,
    )
    assert done.returncode == EXIT_STATUS[BAD_USAGE]
    assert json.loads(done.stdout)["outcome"] == BAD_USAGE
    assert done.stderr == b""


# The candidate kind of ADR-0198 decision 7


def test_a_compile_settings_document_is_started_as_version_2(root, given):
    content = document(schema_version=2, candidate_kind="compile_settings")
    ran = run([given(content)], root)
    assert ran.status == EXIT_STATUS[STARTED]
    assert set(ran.told) == {"outcome", "run_id"}
    assert ran.told["outcome"] == STARTED
    built = ran.told["run_id"]
    assert tree(root) == ["runs", f"runs/{built}", f"runs/{built}/instance.json"]
    assert instance.candidate_kind_of(root, built) == "compile_settings"
    assert instance.read_kinded(root, built).schema_version == 2


def test_a_c_kernel_document_is_started_as_version_1(root, given):
    ran = run([given(document(candidate_kind="c_kernel"))], root)
    assert ran.told["outcome"] == STARTED
    read = instance.read(root, ran.told["run_id"])
    assert "candidate_kind" not in read.others


@pytest.mark.parametrize(
    "changes",
    [
        {"candidate_kind": "compile_settings"},
        {"schema_version": 2, "candidate_kind": "c_kernel"},
        {"schema_version": 2, "candidate_kind": "vendor_kernel"},
        {"schema_version": 3, "candidate_kind": "compile_settings"},
    ],
    ids=["v1_compile_settings", "v2_c_kernel", "v2_unknown", "v3"],
)
def test_a_refused_kind_is_invalid_and_starts_nothing(root, given, changes):
    ran = run([given(document(**changes))], root)
    assert ran.told["outcome"] == INVALID
    assert set(ran.told) == {"outcome", "reason"}
    assert ran.status == EXIT_STATUS[INVALID]
    assert tree(root) == []


# The option --given-code (ADR-0200 decision 6, slice 2)

CODE = b"int given(void) { return 0; }\n"
DIGEST = hashlib.sha256(CODE).hexdigest()


@pytest.fixture
def code(tmp_path):
    def written(content=CODE):
        path = tmp_path / "given.c"
        path.write_bytes(content)
        return str(path)

    return written


def given_run(root, path, content, **options):
    return run([path, GIVEN_CODE_OPTION, content], root, **options)


def test_the_option_starts_a_run_with_given_code(root, given, code, fixed_sources):
    ran = given_run(root, given(document()), code())
    assert ran.told == {"outcome": STARTED, "run_id": FIXED_ID}
    assert ran.status == 0
    assert ran.stderr == ""
    assert instance.given_code_of(root, FIXED_ID) == DIGEST
    assert instance.read_given(root, FIXED_ID).schema_version == 3
    (record,) = artifacts.load(root, FIXED_ID)
    assert record["type"] == "given_code"
    assert record["retention_class"] == "final"
    assert cas.has_blob(root, DIGEST)
    assert ran.source.calls == 1


def test_the_option_hands_the_path_to_start(root, given, code, recorder):
    recording = recorder()
    path = code()
    ran = given_run(root, given(document()), path)
    assert ran.told == {"outcome": STARTED, "run_id": FIXED_ID}
    ((handed, options),) = recording.calls
    assert handed == document()
    assert options == {"data_root": Path(root), "code_file": path}


@pytest.mark.parametrize(
    ("content", "outcome"),
    [
        (
            document(candidate_kind="compile_settings", schema_version=2),
            GIVEN_CODE_REFUSED,
        ),
        (document(candidates_per_round=2), GIVEN_CODE_REFUSED),
        (document(given_code=DIGEST), INVALID),
        (document(schema_version=3, given_code=DIGEST), INVALID),
    ],
    ids=["compile_settings", "two candidates", "given_code v1", "given_code v3"],
)
def test_a_request_not_admitted_with_given_code_starts_nothing(
    root, given, code, content, outcome
):
    ran = given_run(root, given(content), code())
    assert ran.told["outcome"] == outcome
    assert set(ran.told) == {"outcome", "reason"}
    assert_refused(ran, root, outcome, reason=ran.told["reason"])


def test_compile_settings_with_given_code_is_named(root, given, code):
    content = document(candidate_kind="compile_settings", schema_version=2)
    ran = given_run(root, given(content), code())
    assert "compile_settings" in ran.told["reason"]
    assert ran.status == EXIT_STATUS[GIVEN_CODE_REFUSED] == 17


@pytest.mark.parametrize("name", ["absent.c", "."])
def test_an_unreadable_c_file_is_bad_given_code(tmp_path, root, given, name):
    ran = given_run(root, given(document()), str(tmp_path / name))
    assert_refused(ran, root, BAD_GIVEN_CODE, reason=ran.told["reason"])
    assert "cannot be read" in ran.told["reason"]
    assert ran.status == 18


def test_an_oversize_c_file_is_bad_given_code(root, given, code):
    path = code(b"x" * (bring_in.MAX_FILE_BYTES + 1))
    ran = given_run(root, given(document()), path)
    assert_refused(ran, root, BAD_GIVEN_CODE, reason=ran.told["reason"])
    assert str(bring_in.MAX_FILE_BYTES) in ran.told["reason"]


def test_a_failed_record_is_given_code_unrecorded(
    root, given, code, fixed_sources, monkeypatch
):
    def failed(*args, **kwargs):
        raise OSError("injected")

    monkeypatch.setattr(artifacts, "add_record", failed)
    ran = given_run(root, given(document()), code())
    assert ran.told == {
        "outcome": GIVEN_CODE_UNRECORDED,
        "run_id": FIXED_ID,
        "reason": "OSError: injected",
    }
    assert ran.status == EXIT_STATUS[GIVEN_CODE_UNRECORDED] == 19
    assert ran.stderr == ""
    assert instance.given_code_of(root, FIXED_ID) == DIGEST
    assert cas.has_blob(root, DIGEST)


@pytest.mark.parametrize(
    "args",
    [
        ["a", GIVEN_CODE_OPTION],
        ["a", "--given", "b"],
        [GIVEN_CODE_OPTION, "b", "a"],
        ["a", GIVEN_CODE_OPTION, "b", "c"],
        ["a", "b", "c"],
    ],
)
def test_other_forms_of_the_option_are_bad_usage(root, args, recorder):
    recording = recorder()
    ran = run(args, root)
    assert ran.told["outcome"] == BAD_USAGE
    assert str(len(args)) in ran.told["reason"]
    assert GIVEN_CODE_OPTION in ran.told["reason"]
    assert ran.source.calls == 0
    assert recording.calls == []


def test_a_bad_request_file_with_the_option_is_read_first(
    tmp_path, root, code, recorder
):
    recording = recorder()
    ran = given_run(root, str(tmp_path / "absent.json"), code())
    assert ran.told["outcome"] == UNREADABLE_INPUT
    assert recording.calls == []


# The round loop and coder_loop (ADR-0207 decision 3)


def test_cuda_gpu_is_out_of_scope_with_and_without_the_option(root, given, code):
    path = given(document(accelerator=targets.CUDA_GPU))
    for ran in (run([path], root), given_run(root, path, code())):
        assert ran.told["outcome"] == OUT_OF_SCOPE
        assert "accelerator" in ran.told["reason"]
    assert tree(root) == []


@pytest.fixture
def loop_closed(monkeypatch):
    standin = targets.TABLE[targets.CPU_STANDIN]
    table = {"test_gpu": dataclasses.replace(standin, coder_loop=False)}
    monkeypatch.setattr(
        start_instance,
        "_ACCELERATORS",
        ("mock", *targets.coder_loop_accelerators(table)),
    )
    monkeypatch.setattr(
        start_instance,
        "_GIVEN_ACCELERATORS",
        ("mock", *targets.instance_start_accelerators(table)),
    )


def test_a_target_closed_to_the_coder_loop_is_out_of_scope_with_the_option(
    loop_closed, root, given, code
):
    path = given(document(accelerator="test_gpu"))
    for ran in (run([path], root), given_run(root, path, code())):
        assert ran.told["outcome"] == OUT_OF_SCOPE
        assert ran.status == EXIT_STATUS[OUT_OF_SCOPE]
    assert tree(root) == []


def test_the_start_out_of_the_loop_admits_that_target(
    loop_closed, root, code, fixed_sources
):
    told = _started(document(accelerator="test_gpu"), root, code(), coder_loop=False)
    assert told == {"outcome": STARTED, "run_id": FIXED_ID}
    assert (
        instance.read_given(root, FIXED_ID).instance.hw_profile["accelerator"]
        == "test_gpu"
    )


def test_only_a_start_out_of_the_loop_hands_coder_loop_to_start(root, recorder):
    recording = recorder()
    _started(document(), root, None)
    _started(document(), root, "given.c", coder_loop=False)
    assert [options for _, options in recording.calls] == [
        {"data_root": root},
        {"data_root": root, "code_file": "given.c", "coder_loop": False},
    ]
