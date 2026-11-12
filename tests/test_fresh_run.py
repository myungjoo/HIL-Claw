import inspect
import os

import pytest

from hilclaw import fresh_run, keys, layout, start_instance
from hilclaw.layout import InvalidPathValueError

RUN = "run-a"
OTHERS = ["STATE.json", "events.ndjson", "artifacts.json", "rounds"]


def run_path(root):
    return root / "runs" / RUN


def started(root):
    run = run_path(root)
    run.mkdir(parents=True)
    (run / "instance.json").write_text("{}")
    return run


def entries(root):
    return sorted(str(path.relative_to(root)) for path in root.rglob("*"))


def link_or_skip(target, link, directory=False):
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"symbolic links are not available: {error}")


def test_the_public_names():
    public = sorted(
        name
        for name, value in vars(fresh_run).items()
        if not name.startswith("_") and not inspect.ismodule(value)
    )
    assert public == ["is_fresh"]
    assert list(inspect.signature(fresh_run.is_fresh).parameters) == [
        "data_root",
        "run_id",
    ]


# --- happy ---


def test_only_instance_json_is_fresh(tmp_path):
    started(tmp_path)
    assert fresh_run.is_fresh(tmp_path, RUN) is True


def test_a_string_data_root_is_accepted(tmp_path):
    started(tmp_path)
    assert fresh_run.is_fresh(str(tmp_path), RUN) is True


def test_a_leftover_does_not_change_the_answer(tmp_path):
    run = started(tmp_path)
    (run / ".STATE.json.tmp-1234").write_text("partial")
    assert fresh_run.is_fresh(tmp_path, RUN) is True


def test_another_run_does_not_change_the_answer(tmp_path):
    started(tmp_path)
    other = tmp_path / "runs" / "run-b"
    other.mkdir()
    (other / "STATE.json").write_text("{}")
    assert fresh_run.is_fresh(tmp_path, RUN) is True


# --- branch ---


@pytest.mark.parametrize("name", OTHERS)
def test_another_file_of_the_tree_as_a_file_is_not_fresh(tmp_path, name):
    (started(tmp_path) / name).write_text("{}")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


@pytest.mark.parametrize("name", OTHERS)
def test_another_file_of_the_tree_as_a_directory_is_not_fresh(tmp_path, name):
    (started(tmp_path) / name).mkdir()
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_rounds_with_a_round_is_not_fresh(tmp_path):
    started(tmp_path)
    layout.round_dir(tmp_path, RUN, 0).mkdir(parents=True)
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_instance_json_as_a_directory_is_not_fresh(tmp_path):
    (run_path(tmp_path) / "instance.json").mkdir(parents=True)
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_an_empty_run_directory_is_not_fresh(tmp_path):
    run_path(tmp_path).mkdir(parents=True)
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_other_files_without_instance_json_are_not_fresh(tmp_path):
    run = run_path(tmp_path)
    run.mkdir(parents=True)
    (run / "STATE.json").write_text("{}")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_no_run_directory_is_not_fresh(tmp_path):
    (tmp_path / "runs").mkdir()
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_no_runs_directory_is_not_fresh(tmp_path):
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_no_data_root_is_not_fresh(tmp_path):
    assert fresh_run.is_fresh(tmp_path / "missing", RUN) is False


def test_a_file_as_the_run_directory_is_not_fresh(tmp_path):
    (tmp_path / "runs").mkdir()
    run_path(tmp_path).write_text("not a directory")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_a_file_as_runs_is_not_fresh(tmp_path):
    (tmp_path / "runs").write_text("not a directory")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_a_file_as_the_data_root_is_not_fresh(tmp_path):
    root = tmp_path / "root"
    root.write_text("not a directory")
    assert fresh_run.is_fresh(root, RUN) is False


# --- links ---


def test_instance_json_as_a_link_to_a_regular_file_is_fresh(tmp_path):
    run = run_path(tmp_path)
    run.mkdir(parents=True)
    target = tmp_path / "instance-target.json"
    target.write_text("{}")
    link_or_skip(target, run / "instance.json")
    assert fresh_run.is_fresh(tmp_path, RUN) is True


def test_instance_json_as_a_broken_link_is_not_fresh(tmp_path):
    run = run_path(tmp_path)
    run.mkdir(parents=True)
    link_or_skip(tmp_path / "gone.json", run / "instance.json")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_state_json_as_a_broken_link_is_not_fresh(tmp_path):
    run = started(tmp_path)
    link_or_skip(tmp_path / "gone.json", run / "STATE.json")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_rounds_as_a_broken_link_is_not_fresh(tmp_path):
    run = started(tmp_path)
    link_or_skip(tmp_path / "gone", run / "rounds", directory=True)
    assert fresh_run.is_fresh(tmp_path, RUN) is False


# --- negative and error ---


@pytest.mark.parametrize("run_id", ["", "Run-A", "..", ".", "a/b", None, 7, b"run-a"])
def test_an_invalid_run_id_is_refused_before_any_check(tmp_path, monkeypatch, run_id):
    def untouched(*args, **kwargs):
        raise AssertionError("checked a path")

    monkeypatch.setattr(os, "stat", untouched)
    monkeypatch.setattr(os, "lstat", untouched)
    with pytest.raises(InvalidPathValueError):
        fresh_run.is_fresh(tmp_path, run_id)


def failing(real, path_name, error):
    def call(path, *args, **kwargs):
        if os.fspath(path).endswith(path_name):
            raise error
        return real(path, *args, **kwargs)

    return call


def test_a_permission_error_of_stat_is_raised_unchanged(tmp_path, monkeypatch):
    started(tmp_path)
    error = PermissionError(13, "denied")
    monkeypatch.setattr(os, "stat", failing(os.stat, "instance.json", error))
    with pytest.raises(PermissionError) as caught:
        fresh_run.is_fresh(tmp_path, RUN)
    assert caught.value is error


@pytest.mark.parametrize("name", OTHERS)
def test_a_permission_error_of_lstat_is_raised_unchanged(tmp_path, monkeypatch, name):
    started(tmp_path)
    error = PermissionError(13, "denied")
    monkeypatch.setattr(os, "lstat", failing(os.lstat, name, error))
    with pytest.raises(PermissionError) as caught:
        fresh_run.is_fresh(tmp_path, RUN)
    assert caught.value is error


def test_not_a_directory_from_stat_is_not_fresh(tmp_path, monkeypatch):
    started(tmp_path)
    monkeypatch.setattr(
        os,
        "stat",
        failing(os.stat, "instance.json", NotADirectoryError(20, "not a dir")),
    )
    assert fresh_run.is_fresh(tmp_path, RUN) is False


@pytest.mark.parametrize("name", OTHERS)
def test_not_a_directory_from_lstat_is_absent(tmp_path, monkeypatch, name):
    started(tmp_path)
    monkeypatch.setattr(
        os, "lstat", failing(os.lstat, name, NotADirectoryError(20, "not a dir"))
    )
    assert fresh_run.is_fresh(tmp_path, RUN) is True


# --- no side effect ---


@pytest.mark.parametrize("extra", [None, "STATE.json", "rounds"])
def test_a_call_changes_no_entry(tmp_path, extra):
    run = started(tmp_path)
    if extra == "rounds":
        (run / extra).mkdir()
    elif extra:
        (run / extra).write_text("{}")
    before = entries(tmp_path)
    contents = (run / "instance.json").read_bytes()
    fresh_run.is_fresh(tmp_path, RUN)
    assert entries(tmp_path) == before
    assert (run / "instance.json").read_bytes() == contents


def test_a_missing_run_creates_nothing(tmp_path):
    fresh_run.is_fresh(tmp_path, RUN)
    assert entries(tmp_path) == []


def test_instance_json_is_never_opened(tmp_path, monkeypatch):
    started(tmp_path)

    def refused(*args, **kwargs):
        raise AssertionError("opened a file")

    monkeypatch.setattr("builtins.open", refused)
    monkeypatch.setattr(os, "open", refused)
    monkeypatch.setattr(os, "listdir", refused)
    monkeypatch.setattr(os, "scandir", refused)
    assert fresh_run.is_fresh(tmp_path, RUN) is True


def test_the_module_does_not_import_the_turn_loop():
    assert "turn_loop" not in vars(fresh_run)
    assert "hilclaw.turn_loop" not in inspect.getsource(fresh_run)


# --- a run that states given code (ADR-0201 decision 1) ---

GIVEN_PROFILE = {
    "schema_version": 1,
    "accelerator": "cpu_standin",
    "revision": "test-revision",
    "toolchain": {"clang": "test"},
    "host": {"cpu": "test", "os": "test"},
    "hw_source": "external",
}
GIVEN_OP = {
    "schema_version": 1,
    "kind": "gemm",
    "shape": {"m": 4, "k": 8, "n": 4},
    "dtype": "fp32",
    "layout": "row_major",
}


def started_given(root, code=b"int x;\n"):
    document = {
        "schema_version": 1,
        "hw_profile": {
            "key": keys.hw_profile_key(GIVEN_PROFILE).name,
            "record": GIVEN_PROFILE,
        },
        "op_signature": {
            "key": keys.op_signature_key(GIVEN_OP).name,
            "record": GIVEN_OP,
        },
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
        "n_max": 6,
        "draws": 1,
        "tolerance": {"rtol": 1e-4, "atol": 1e-5},
        "round_budget": 1,
    }
    root.mkdir(exist_ok=True)
    if code is None:
        return start_instance.start(document, data_root=root)
    path = root.parent / "given.c"
    path.write_bytes(code)
    return start_instance.start(document, data_root=root, code_file=path)


def test_a_started_given_code_run_is_fresh_with_its_artifacts_json(tmp_path):
    root = tmp_path / "data"
    run_id = started_given(root)
    assert (root / "runs" / run_id / "artifacts.json").is_file()
    assert fresh_run.is_fresh(root, run_id) is True


@pytest.mark.parametrize("name", ["STATE.json", "events.ndjson", "rounds"])
def test_a_given_code_run_with_another_file_is_not_fresh(tmp_path, name):
    root = tmp_path / "data"
    run_id = started_given(root)
    (root / "runs" / run_id / name).mkdir()
    assert fresh_run.is_fresh(root, run_id) is False


def test_artifacts_json_beside_a_version_1_instance_is_not_fresh(tmp_path):
    root = tmp_path / "data"
    run_id = started_given(root, code=None)
    run = root / "runs" / run_id
    assert fresh_run.is_fresh(root, run_id) is True
    (run / "artifacts.json").write_text("{}")
    assert fresh_run.is_fresh(root, run_id) is False


@pytest.mark.parametrize(
    "content",
    [b"{}", b"{", b'{"schema_version": 4}'],
    ids=["invalid", "not_json", "version_4"],
)
def test_artifacts_json_beside_an_unreadable_instance_is_not_fresh(tmp_path, content):
    (started(tmp_path) / "instance.json").write_bytes(content)
    (run_path(tmp_path) / "artifacts.json").write_text("{}")
    assert fresh_run.is_fresh(tmp_path, RUN) is False


def test_an_instance_gone_before_its_read_is_not_fresh(tmp_path, monkeypatch):
    root = tmp_path / "data"
    run_id = started_given(root)
    read_bytes = type(root).read_bytes

    def gone(path):
        if path.name == "instance.json":
            raise FileNotFoundError(2, "gone")
        return read_bytes(path)

    monkeypatch.setattr(type(root), "read_bytes", gone)
    assert fresh_run.is_fresh(root, run_id) is False


def test_a_permission_error_of_the_instance_read_is_raised_unchanged(
    tmp_path, monkeypatch
):
    root = tmp_path / "data"
    run_id = started_given(root)
    error = PermissionError(13, "denied")

    def denied(path):
        raise error

    monkeypatch.setattr(type(root), "read_bytes", denied)
    with pytest.raises(PermissionError) as caught:
        fresh_run.is_fresh(root, run_id)
    assert caught.value is error
