import io
import json
import os

import numpy as np
import pytest
import test_attempt_kernel as attempts
import test_model_files as files_tests
import test_model_forward as forward
import test_model_forward_execute as forward_execute
import test_model_forward_run as forward_run
import test_model_hf_reference as hf_tests
import test_model_run_binding as binding_tests
from test_model_forward_container import (  # noqa: F401
    client,
    ended,
    image,
    parent,
    raises,
    timed_out,
    user,
)

from hilclaw import (
    model_check,
    model_files,
    model_forward_container,
    model_hf_reference,
    model_reference,
    model_run_binding,
    standin_copies,
    standin_image,
)
from hilclaw.model_check import EXIT_STATUS, main

RTOL, ATOL = 2**-8, 1e-9
PROMPT = "\x01\x02\x03"
PROMPT_IDS = [1, 2, 3]
N = 3


def rows_of(weights, tokens):
    return model_reference.reference_logits(
        forward_run.DIMENSIONS,
        eps=forward_run.EPS,
        rope=forward_run.ROPE,
        weights=weights,
        prompt=tokens[:1],
        given=[*tokens[1:], 0],
        lm_head_rows="all",
    )


def greedy_of(weights, prompt, count):
    tokens = list(prompt)
    for _ in range(count):
        tokens.append(int(np.argmax(rows_of(weights, tokens)[-1])))
    return tokens[len(prompt) :]


def bf16_of(rows):
    return forward.narrow(rows.astype(np.float32))


class Stage:
    """Synthetic files, runs, the stub client and fake packages for one call."""

    def __init__(self, tmp_path, stub, monkeypatch, parent_directory):
        self.model = forward_run.model_of(71, prompt=3, given=3)
        self.weights = forward_run.weights_of(self.model)
        self.directory = tmp_path / "model"
        self.directory.mkdir()
        files_tests.write_single(self.directory, files_tests.stored_of(self.weights))
        self.root = tmp_path / "data"
        self.root.mkdir()
        self.client = stub
        self.parent = parent_directory
        self.packages = hf_tests.install(
            monkeypatch,
            hf_tests.Packages(lambda tokens: rows_of(self.weights, tokens)),
        )
        self.packages.backend.vocabulary = forward.V
        self.document_file = tmp_path / "check.json"
        self.members = {
            "model_directory": str(self.directory),
            "runs": write_runs(self.root),
            "flags": list(forward.KERNEL_FLAGS),
            "prompt": PROMPT,
            "n": N,
            "rtol": RTOL,
            "atol": ATOL,
            "build_timeout_s": 30,
            "run_timeout_s": 7,
            "program_flags": ["-O2"],
            "program_trailing_flags": ["-ldl"],
            "parent": str(self.parent),
        }
        self.greedy = greedy_of(self.weights, PROMPT_IDS, N)
        self.report(self.greedy)

    def report(self, selected, change=None, logits_on=None):
        tokens = [*PROMPT_IDS, *(selected if logits_on is None else logits_on)]
        rows = bf16_of(rows_of(self.weights, tokens[:-1]))
        if change is not None:
            change(rows)
        whole = np.array([*PROMPT_IDS, *selected], dtype=np.uint64)
        self.client.report = forward.generated_report(whole, len(PROMPT_IDS), rows)

    def run(self, **changes):
        members = dict(self.members)
        for name, value in changes.items():
            if value is ...:
                del members[name]
            else:
                members[name] = value
        self.document_file.write_text(json.dumps(members), encoding="utf-8")
        return self.call([str(self.document_file)])

    def call(self, args, source=None):
        stdout = io.BytesIO()
        status = main(
            args,
            source=source if source is not None else lambda: str(self.root),
            stdout=stdout,
            stderr=io.BytesIO(),
        )
        line = stdout.getvalue()
        assert line.endswith(b"\n") and line.count(b"\n") == 1
        line.decode("ascii")
        told = json.loads(line)
        assert status == EXIT_STATUS[told["outcome"]]
        return told


def write_runs(root):
    runs = {kind: f"synthetic-{kind}" for kind in forward.KINDS}
    for kind, run_id in runs.items():
        contract = attempts.FORWARD_CONTRACT[kind]
        binding_tests.write_instance(root, run_id, contract=contract)
        binding_tests.write_attempt(root, 0, 1, run_id, contract, f"{kind}.c")
        result = binding_tests.PASS
        binding_tests.step(root, 0, binding_tests.SIM, 1, run_id, result=result)
        binding_tests.step(root, 0, binding_tests.BOARD, 1, run_id, result=result)
        result = binding_tests.timing([20] * 5)
        binding_tests.step(root, 0, binding_tests.TIMING, 1, run_id, result=result)
    return {site: runs[kind] for site, kind in forward_execute.KIND_OF.items()}


@pytest.fixture
def stage(tmp_path, client, monkeypatch, parent):  # noqa: F811
    return Stage(tmp_path, client, monkeypatch, parent)


def tree(directory):
    return {
        os.path.relpath(os.path.join(place, name), directory): os.path.getmtime(
            os.path.join(place, name)
        )
        for place, names, files in os.walk(directory)
        for name in names + files
    }


def test_the_joined_path_is_a_match_and_adds_nothing(stage):
    before = tree(stage.root), tree(stage.directory)
    told = stage.run()
    assert told["outcome"] == "match", told
    assert before == (tree(stage.root), tree(stage.directory))
    assert os.listdir(stage.parent) == []
    assert told["prompt_tokens"] == PROMPT_IDS
    assert told["executor_tokens"] == stage.greedy == told["reference_tokens"]
    assert told["first_differing_token"] is None
    assert told["prompt_text"] == "1 2 3"
    assert told["executor_text"] == " ".join(str(t) for t in stage.greedy)
    assert told["reference_text"] == told["executor_text"]
    assert told["logits"]["ok"] is True
    assert told["logits"]["failed"] == 0
    assert told["logits"]["first"] is None
    assert told["logits"]["row_failures"] == [0] * (len(PROMPT_IDS) + N - 1)
    assert told["removed"] is True
    assert len(stage.client.runs()) == len(forward.KINDS) + 2


def test_the_reference_is_loaded_at_float64_from_the_named_directory(stage):
    stage.run()
    assert stage.packages.loads == [(str(stage.directory), hf_tests.LOADING)]
    fed = [*PROMPT_IDS, *stage.greedy[:-1]]
    assert stage.packages.passes[0] == fed


def test_n_of_one_is_a_match(stage):
    stage.report(greedy_of(stage.weights, PROMPT_IDS, 1))
    assert stage.run(n=1)["outcome"] == "match"


def test_logits_outside_the_tolerance_are_no_match_with_equal_tokens(stage):
    def change(rows):
        rows[1, 2] = forward.narrow(np.float32([1000.0]))[0]

    stage.report(stage.greedy, change)
    told = stage.run()
    assert told["outcome"] == "no_match"
    assert told["executor_tokens"] == told["reference_tokens"]
    assert told["first_differing_token"] is None
    assert told["logits"]["ok"] is False
    assert told["logits"]["failed"] == 1
    assert told["logits"]["first"] == [1, 2]


def other_last(tokens):
    return [*tokens[:-1], (tokens[-1] + 1) % forward.V]


def test_a_differing_token_within_the_tolerance_is_no_match(stage):
    stage.report(other_last(stage.greedy))
    told = stage.run()
    assert told["outcome"] == "no_match"
    assert told["logits"]["ok"] is True
    assert told["first_differing_token"] == N - 1


def test_both_failing_is_no_match(stage):
    def change(rows):
        rows[0, 0] = forward.narrow(np.float32([1000.0]))[0]

    stage.report(other_last(stage.greedy), change)
    told = stage.run()
    assert told["outcome"] == "no_match"
    assert told["logits"]["ok"] is False
    assert told["first_differing_token"] == N - 1


def test_teacher_forcing_follows_the_executors_tokens(stage):
    first = (stage.greedy[0] + 1) % forward.V
    selected = [first, stage.greedy[1], stage.greedy[2]]
    stage.report(selected)
    told = stage.run()
    assert told["first_differing_token"] == 0
    assert told["logits"]["ok"] is True
    assert stage.packages.passes[0] == [*PROMPT_IDS, *selected[:-1]]


def assert_early(stage, told, outcome):
    assert told["outcome"] == outcome, told
    assert stage.client.calls == []
    assert stage.packages.loads == []


def test_usage_and_decoding_refusals(stage, tmp_path):
    assert_early(stage, stage.call([]), "bad_usage")
    assert_early(stage, stage.call(["a", "b"]), "bad_usage")
    missing = str(tmp_path / "none.json")
    assert_early(stage, stage.call([missing]), "unreadable_input")
    for text in (b"{", b"[]", b'{"n":1,"n":2}', b'{"rtol":NaN}'):
        stage.document_file.write_bytes(text)
        told = stage.call([str(stage.document_file)])
        assert_early(stage, told, "bad_input")


@pytest.mark.parametrize(
    "changes",
    [
        {"extra": 1},
        {"model_directory": ...},
        {"runs": ...},
        {"flags": ...},
        {"prompt": ...},
        {"n": ...},
        {"rtol": ...},
        {"atol": ...},
        {"build_timeout_s": ...},
        {"run_timeout_s": ...},
        {"program_flags": ...},
        {"program_trailing_flags": ...},
        {"model_directory": 3},
        {"prompt": 3},
        {"runs": []},
        {"runs": {"gemm": "synthetic"}},
        {"runs": {"qkv": "../x"}},
        {"runs": {"qkv": "synthetic"}},
        {"flags": "-O2"},
        {"n": 0},
        {"n": -1},
        {"n": 1.0},
        {"n": True},
        {"rtol": -1},
        {"rtol": "1"},
        {"rtol": True},
        {"atol": -1e-3},
        {"build_timeout_s": 0},
        {"build_timeout_s": True},
        {"run_timeout_s": -1},
        {"program_flags": [1]},
        {"program_trailing_flags": "-ldl"},
        {"parent": 3},
    ],
)
def test_a_refused_document_starts_nothing(stage, changes):
    assert_early(stage, stage.run(**changes), "refused_document")


@pytest.mark.parametrize("name", ["rtol", "atol", "build_timeout_s", "run_timeout_s"])
def test_a_number_too_large_for_a_float_is_refused(stage, name):
    members = json.dumps(stage.members | {name: 0}).replace(
        f'"{name}": 0', f'"{name}": 1e400'
    )
    stage.document_file.write_text(members, encoding="utf-8")
    told = stage.call([str(stage.document_file)])
    assert_early(stage, told, "refused_document")
    assert name in told["reason"]


@pytest.mark.parametrize("name", model_hf_reference.PACKAGES)
def test_a_missing_package_comes_before_the_files(stage, monkeypatch, name):
    monkeypatch.setitem(hf_tests.sys.modules, name, None)
    reads = []
    monkeypatch.setattr(model_files, "read", reads.append)
    told = stage.run()
    assert_early(stage, told, "missing_package")
    assert told["package"] == name
    assert reads == []


def model_file_reasons():
    return sorted(
        value
        for name, value in vars(model_files).items()
        if name.isupper() and not name.startswith("_") and isinstance(value, str)
    )


@pytest.mark.parametrize("reason", model_file_reasons())
def test_each_model_file_reason_is_told(stage, monkeypatch, reason):
    def fails(directory):
        raise model_files.ModelFileError(reason, "synthetic")

    monkeypatch.setattr(model_files, "read", fails)
    told = stage.run()
    assert_early(stage, told, "model_file")
    assert told["reason"] == reason


def test_a_real_model_file_refusal_is_told(stage):
    (stage.directory / "config.json").unlink()
    told = stage.run()
    assert_early(stage, told, "model_file")
    assert told["reason"] == model_files.NO_CONFIG


def test_a_failed_tokenizer_starts_no_container(stage):
    stage.packages.tokenizer_error = OSError("no tokenizer.json")
    assert_early(stage, stage.run(), "tokenizer_failed")


def test_a_prompt_that_tokenizes_to_nothing_starts_no_container(stage):
    told = stage.run(prompt="")
    assert_early(stage, told, "empty_prompt")


def test_no_data_root_starts_no_container(stage, tmp_path):
    stage.document_file.write_text(json.dumps(stage.members), encoding="utf-8")
    told = stage.call([str(stage.document_file)], source=lambda: str(tmp_path / "gone"))
    assert_early(stage, told, "no_data_root")


def test_a_parent_inside_the_model_directory_is_refused(stage):
    told = stage.run(parent=str(stage.directory))
    assert_early(stage, told, "refused_parent")


def test_a_parent_inside_the_data_root_is_refused(stage):
    told = stage.run(parent=str(stage.root))
    assert_early(stage, told, "refused_parent")


@pytest.mark.parametrize("reason", model_run_binding.REASONS)
def test_each_run_binding_reason_is_told(stage, monkeypatch, reason):
    def fails(root, runs, *, flags):
        raise model_run_binding.RunBindingError(reason, "qkv", "synthetic-run")

    monkeypatch.setattr(model_run_binding, "binding_from_runs", fails)
    told = stage.run()
    assert_early(stage, told, "run_binding")
    assert told["reason"] == reason
    assert (told["call_site"], told["run_id"]) == ("qkv", "synthetic-run")


def test_a_run_with_no_incumbent_starts_no_container(stage):
    binding_tests.write_instance(stage.root, "synthetic-empty", contract="gemm_bf16")
    told = stage.run(runs=stage.members["runs"] | {"qkv": "synthetic-empty"})
    assert_early(stage, told, "run_binding")
    assert told["reason"] == model_run_binding.NO_INCUMBENT


def test_a_binding_check_that_is_not_ok_starts_no_container(stage):
    other = stage.members["runs"]["sdpa"]
    told = stage.run(runs=stage.members["runs"] | {"qkv": other})
    assert_early(stage, told, "binding_check")
    assert told["outcomes"]
    assert told["outcomes"][0]["call_site"] == "qkv"
    assert all(
        set(item) == {"kind", "call_site", "reason"} for item in told["outcomes"]
    )


def test_a_prompt_token_outside_the_vocabulary_is_the_binding_check(stage):
    stage.packages.backend.encode = lambda text, *, add_special_tokens: [10**6]
    assert_early(stage, stage.run(), "binding_check")


def test_no_image_is_container_unavailable(stage, monkeypatch):
    monkeypatch.delenv(standin_image.ENV_IMAGE)
    told = stage.run()
    assert_early(stage, told, "container_unavailable")
    assert told["reason"] == model_forward_container.NO_IMAGE
    assert told["removed"] is None


def test_a_runtime_status_of_a_build_is_container_unavailable(stage):
    stage.client.script[0] = ended(125)
    told = stage.run()
    assert told["outcome"] == "container_unavailable"
    assert told["reason"] == model_forward_container.RUNTIME_STATUS
    assert told["removed"] is True
    assert len(stage.client.runs()) == 1
    assert stage.packages.loads == []


def test_a_failed_kernel_build_is_told_with_its_log(stage):
    stage.client.script[0] = ended(1, stdout=b"out", stderr=b"bad")
    told = stage.run()
    assert told["outcome"] == "build_failed"
    assert told["kernel"] == 0
    assert told["returncode"] == 1
    assert told["timed_out"] is False
    assert "bad" in told["log"]
    assert told["removed"] is True
    assert stage.packages.loads == []


def test_a_failed_program_build_names_no_kernel(stage):
    stage.client.script[len(forward.KINDS)] = ended(1)
    told = stage.run()
    assert told["outcome"] == "build_failed"
    assert told["kernel"] is None


def test_a_build_past_its_limit_is_told(stage):
    stage.client.script[0] = timed_out
    told = stage.run()
    assert told["outcome"] == "build_failed"
    assert told["timed_out"] is True
    assert told["returncode"] is None


@pytest.mark.parametrize(
    ("act", "failed", "returncode"),
    [
        (timed_out, "timeout", None),
        (ended(3, stderr=b"bad \xff"), "exit_status", 3),
        (ended(0, stdout=b"short"), "report_form", 0),
    ],
)
def test_a_failed_run_is_told(stage, act, failed, returncode):
    stage.client.script[len(forward.KINDS) + 1] = act
    told = stage.run()
    assert told["outcome"] == "run_failed"
    assert told["failed"] == failed
    assert told["returncode"] == returncode
    assert stage.packages.loads == []
    if returncode == 3:
        assert told["stderr"] == "bad �"


@pytest.mark.parametrize(
    ("whole", "word"),
    [
        ([*PROMPT_IDS, 0, 0, forward.V], "vocabulary"),
        ([*PROMPT_IDS, forward.V, 0, 0], "vocabulary"),
        ([0, 0, 0, 0, 0, 0], "prompt"),
    ],
    ids=["last", "fed", "echo"],
)
def test_a_report_the_program_could_not_have_made_is_told_before_the_load(
    stage, whole, word
):
    rows = bf16_of(rows_of(stage.weights, [1, 2, 3, 0, 0]))
    tokens = np.array(whole, dtype=np.uint64)
    stage.client.report = forward.generated_report(tokens, len(PROMPT_IDS), rows)
    told = stage.run()
    assert told["outcome"] == "bad_report"
    assert word in told["reason"]
    assert told["removed"] is True
    assert stage.packages.loads == []


def test_a_missing_parent_is_a_file_system_refusal(stage, tmp_path):
    told = stage.run(parent=str(tmp_path / "builds-none"))
    assert told["outcome"] == "file_system"
    assert stage.client.calls == []


def test_an_os_error_of_the_client_is_a_file_system_refusal(stage):
    stage.client.script[0] = raises(OSError("broken pipe"))
    told = stage.run()
    assert told["outcome"] == "file_system"
    assert "broken pipe" in told["reason"]


def test_a_copy_that_cannot_be_read_is_told(stage, monkeypatch):
    def fails(directory, *arguments, **options):
        raise standin_copies.CopyError(standin_copies.KERNEL_FILE_UNREADABLE)

    monkeypatch.setattr(model_forward_container, "_copy_kernel", fails)
    told = stage.run()
    assert told["outcome"] == "copy_failed"
    assert told["reason"] == standin_copies.KERNEL_FILE_UNREADABLE


@pytest.mark.parametrize(
    ("setup", "reason"),
    [
        (
            lambda packages: setattr(packages, "load_error", OSError("gone")),
            model_hf_reference.LOAD_FAILED,
        ),
        (
            lambda packages: setattr(packages, "dtype", "float32"),
            model_hf_reference.WRONG_DTYPE,
        ),
        (
            lambda packages: setattr(packages, "rows", lambda tokens: np.zeros((1, 1))),
            model_hf_reference.WRONG_SHAPE,
        ),
    ],
)
def test_a_failed_reference_is_told(stage, setup, reason):
    setup(stage.packages)
    told = stage.run()
    assert told["outcome"] == "reference_failed"
    assert told["reason"] == reason


def test_a_failed_decoding_is_told_after_the_run(stage):
    backend = stage.packages.backend

    def fails(tokens, *, skip_special_tokens):
        raise ValueError("no such token")

    backend.decode = fails
    assert stage.run()["outcome"] == "tokenizer_failed"


def test_an_unexpected_exception_is_a_fault(stage, monkeypatch):
    def fails(*arguments, **options):
        raise KeyError("x")

    monkeypatch.setattr(model_reference, "compare", fails)
    told = stage.run()
    assert told == {"outcome": "fault", "fault": "KeyError"}


def test_a_keyboard_interrupt_is_not_caught(stage, monkeypatch):
    def fails(directory):
        raise KeyboardInterrupt

    monkeypatch.setattr(model_files, "read", fails)
    stage.document_file.write_text(json.dumps(stage.members), encoding="utf-8")
    with pytest.raises(KeyboardInterrupt):
        stage.call([str(stage.document_file)])


def test_standard_output_missing_is_a_fault(stage, monkeypatch):
    monkeypatch.setattr(model_check.sys, "stdout", None)
    stderr = io.BytesIO()
    assert main(["x"], stderr=stderr) == EXIT_STATUS["fault"]
    assert b"no standard output" in stderr.getvalue()


class Failing(io.BytesIO):
    def __init__(self, short):
        super().__init__()
        self.short = short

    def write(self, data):
        if self.short:
            return 1
        raise OSError("closed")


@pytest.mark.parametrize("short", [False, True])
def test_a_line_that_cannot_be_written_is_said_on_standard_error(stage, short):
    stderr = io.BytesIO()
    status = main([], source=lambda: "x", stdout=Failing(short), stderr=stderr)
    assert status == EXIT_STATUS["fault"]
    assert b"bad_usage" in stderr.getvalue()


def test_the_default_arguments_are_the_process(stage, monkeypatch):
    stream = io.BytesIO()
    fake = type("Out", (), {"buffer": stream})()
    monkeypatch.setattr(model_check.sys, "stdout", fake)
    monkeypatch.setattr(model_check.sys, "stderr", fake)
    monkeypatch.setattr(model_check.sys, "argv", ["model_check"])
    assert main() == EXIT_STATUS["bad_usage"]
    assert json.loads(stream.getvalue())["outcome"] == "bad_usage"


def test_every_status_is_distinct_and_only_match_is_zero():
    statuses = list(EXIT_STATUS.values())
    assert len(set(statuses)) == len(statuses)
    assert [kind for kind, status in EXIT_STATUS.items() if status == 0] == ["match"]
    assert not {1, 2} & set(statuses)
