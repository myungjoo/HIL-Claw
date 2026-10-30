import json
import shutil

import pytest
import test_attempt_kernel as attempts
import test_model_forward as forward
import test_model_forward_container as container
import test_model_forward_execute as forward_execute
from test_model_forward_container import client, image, parent, user  # noqa: F401

from hilclaw import (
    attempt_kernel,
    events,
    instance,
    journal,
    kernel_source,
    keys,
    layout,
    local_run,
    model_forward_run,
    model_run_binding,
    spec_feedback,
    spec_file,
    standin_profile,
    tools,
)
from hilclaw.model_binding import BindingEntry, KernelReference
from hilclaw.model_run_binding import (
    ATTEMPT_WITHOUT_SPEC,
    EVERY,
    INSTANCE_INVALID,
    INSTANCE_OTHER_VERSION,
    INSTANCE_UNREADABLE,
    NO_INCUMBENT,
    NO_OBJECTIVE,
    NO_OP_SIGNATURE,
    NOT_ONE_CANDIDATE,
    OBJECTIVE_UNSUPPORTED,
    OTHER_TARGET,
    REASONS,
    RUN_MISSING,
    RunBindingError,
    binding_from_runs,
)

RUN = "synthetic-run-1"
FLAGS = forward.KERNEL_FLAGS
SIM = "correctness_check_sim_v2"
BOARD = "correctness_check_board_v2"
TIMING = "board_run_timing_v2"
PASS = {"outcome": "pass", "max_abs_error": 0.0}
FAIL = {"outcome": "fail"}
PROFILE = {
    "schema_version": 1,
    "accelerator": standin_profile.ACCELERATOR,
    "revision": "synthetic-revision",
    "toolchain": {"clang": "synthetic"},
    "host": {"cpu": "synthetic", "os": "synthetic"},
    "hw_source": "external",
}


@pytest.fixture
def root(tmp_path):
    data_root = tmp_path / "data"
    data_root.mkdir()
    return data_root


def write_instance(root, run_id=RUN, contract="gemm_bf16", **changes):
    module, shape = attempts.CONTRACT_ARGUMENTS[contract]
    op = module.op_signature_record(*shape)
    made = {
        "schema_version": 1,
        "hw_profile": {"key": keys.hw_profile_key(PROFILE).name, "record": PROFILE},
        "op_signature": {"key": keys.op_signature_key(op).name, "record": op},
        "objective": {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [],
        },
        "candidates_per_round": 1,
    }
    made.update(changes)
    made = {name: value for name, value in made.items() if value is not None}
    path = layout.run_file(root, run_id, "instance.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(made), encoding="utf-8")


def write_attempt(root, round, attempt=1, run_id=RUN, contract="gemm_bf16", name="k.c"):
    made = attempts.document(round, 1, attempt, contract=contract, run_id=run_id)
    spec_file.write(root, attempts.content_of(made))
    output = layout.attempt_artefact(root, run_id, round, 1, attempt, "output")
    output.mkdir()
    (output / name).write_bytes(b"/* synthetic */\n")


def step(root, round, name, attempt=1, run_id=RUN, **outcome):
    numbers = {"round": round, "candidate": 1, "attempt": attempt}
    data = {"step": name, "execution": 1}
    events.append(root, run_id, journal.STEP_STARTED, data, **numbers)
    data = data | {"spend": {}, **outcome}
    events.append(root, run_id, journal.STEP_ENDED, data, **numbers)


def timing(intervals, outcome="converged"):
    return {
        "outcome": outcome,
        "intervals": list(intervals),
        "unit": "ns",
        "shape": {"m": 1, "k": 1, "n": 1},
        "contract_key": {"kind": "gemm", "dtype": "bf16", "layout": "row_major"},
    }


def measured(root, round, median, attempt=1, run_id=RUN, outcome="converged"):
    write_attempt(root, round, attempt, run_id)
    step(root, round, SIM, attempt, run_id, result=PASS)
    step(root, round, BOARD, attempt, run_id, result=PASS)
    result = timing([median] * 5, outcome)
    step(root, round, TIMING, attempt, run_id, result=result)


def kernel_of(root, round, attempt=1, run_id=RUN):
    return attempt_kernel.kernel_reference(root, run_id, round, 1, attempt, flags=FLAGS)


def bound(root, run_id=RUN):
    return binding_from_runs(root, {"qkv": run_id}, flags=FLAGS)["qkv"][0].kernel


def refused(root, reason, runs=None):
    with pytest.raises(RunBindingError) as caught:
        binding_from_runs(root, runs or {"qkv": RUN}, flags=FLAGS)
    assert caught.value.reason == reason
    assert reason in REASONS
    return caught.value


def test_the_binding_names_the_attempt_with_the_lowest_median(root):
    write_instance(root)
    measured(root, 0, 50)
    measured(root, 1, 20)
    measured(root, 2, 30)
    binding = binding_from_runs(root, {"qkv": RUN}, flags=FLAGS)
    assert binding == {"qkv": (BindingEntry(kernel_of(root, 1), EVERY),)}
    entry = binding["qkv"][0]
    assert type(entry.kernel) is KernelReference
    assert entry.shapes == "every"
    assert entry.kernel.flags == FLAGS


def test_a_later_slower_round_does_not_displace_the_incumbent(root):
    write_instance(root)
    measured(root, 0, 20)
    assert bound(root) == kernel_of(root, 0)
    measured(root, 1, 90)
    assert bound(root) == kernel_of(root, 0)


def test_one_run_may_serve_two_call_sites_and_is_read_once(root, monkeypatch):
    write_instance(root)
    measured(root, 0, 20)
    reads = []
    real = spec_feedback.incumbent
    monkeypatch.setattr(
        spec_feedback,
        "incumbent",
        lambda *arguments: reads.append(arguments) or real(*arguments),
    )
    binding = binding_from_runs(root, {"qkv": RUN, "lm_head": RUN}, flags=list(FLAGS))
    assert binding["qkv"] == binding["lm_head"]
    assert len(reads) == 1


def test_each_call_site_binds_the_incumbent_of_its_own_run(root):
    other = "synthetic-run-2"
    write_instance(root)
    write_instance(root, other)
    measured(root, 0, 20)
    measured(root, 0, 90, run_id=other)
    binding = binding_from_runs(root, {"qkv": RUN, "o": other}, flags=FLAGS)
    assert binding["qkv"][0].kernel == kernel_of(root, 0)
    assert binding["o"][0].kernel == kernel_of(root, 0, run_id=other)


def test_a_tie_goes_to_the_earliest_attempt(root):
    write_instance(root)
    measured(root, 0, 40)
    measured(root, 1, 40)
    assert bound(root) == kernel_of(root, 0)


def test_a_not_converged_measurement_competes(root):
    write_instance(root)
    measured(root, 0, 50)
    measured(root, 1, 20, outcome="not_converged")
    assert bound(root) == kernel_of(root, 1)


def test_a_repair_attempt_can_be_the_incumbent(root):
    write_instance(root)
    write_attempt(root, 0, 1)
    step(root, 0, SIM, 1, result=FAIL)
    measured(root, 0, 20, attempt=2)
    assert bound(root) == kernel_of(root, 0, attempt=2)


def test_a_faster_attempt_failed_at_the_board_point_is_not_chosen(root):
    write_instance(root)
    measured(root, 0, 50)
    write_attempt(root, 1)
    step(root, 1, SIM, result=PASS)
    step(root, 1, BOARD, result=FAIL)
    step(root, 1, TIMING, result=timing([1] * 5))
    assert bound(root) == kernel_of(root, 0)


def test_a_data_root_as_a_str_and_an_empty_mapping_are_accepted(root):
    write_instance(root)
    measured(root, 0, 20)
    assert binding_from_runs(str(root), {}, flags=FLAGS) == {}
    binding = binding_from_runs(str(root), {"sdpa": RUN}, flags=())
    assert binding["sdpa"][0].kernel.flags == ()


@pytest.mark.parametrize("call_site", model_forward_run.CALL_SITES)
def test_every_call_site_takes_the_every_form(root, call_site):
    write_instance(root)
    measured(root, 0, 20)
    binding = binding_from_runs(root, {call_site: RUN}, flags=FLAGS)
    assert binding[call_site][0].shapes == EVERY


@pytest.mark.parametrize(
    ("argument", "error", "parameter"),
    [
        ({"data_root": 3}, TypeError, "data_root"),
        ({"data_root": "a\0b"}, ValueError, "data_root"),
        ({"runs": ["qkv"]}, TypeError, "runs"),
        ({"runs": {"gemm": RUN}}, ValueError, "runs"),
        ({"runs": {3: RUN}}, ValueError, "runs"),
        ({"runs": {"qkv": "../x"}}, layout.InvalidPathValueError, "runs"),
        ({"runs": {"qkv": None}}, layout.InvalidPathValueError, "runs"),
        ({"flags": "-O2"}, TypeError, "flags"),
        ({"flags": (1,)}, TypeError, "flags"),
        ({"flags": None}, TypeError, "flags"),
    ],
)
def test_a_malformed_argument_is_refused_before_anything_is_read(
    root, argument, error, parameter
):
    arguments = {"data_root": root, "runs": {"qkv": RUN}, "flags": FLAGS} | argument
    with pytest.raises(error) as caught:
        binding_from_runs(
            arguments["data_root"], arguments["runs"], flags=arguments["flags"]
        )
    assert caught.value.parameter == parameter


def test_flags_are_required(root):
    with pytest.raises(TypeError):
        binding_from_runs(root, {"qkv": RUN})


def test_a_run_with_no_verified_attempt_is_no_incumbent(root):
    write_instance(root)
    write_attempt(root, 0)
    step(root, 0, SIM, result=FAIL)
    error = refused(root, NO_INCUMBENT)
    assert (error.call_site, error.run_id) == ("qkv", RUN)
    assert str(error) == f"qkv: run {RUN}: {NO_INCUMBENT}"


def test_a_run_without_attempts_is_no_incumbent(root):
    write_instance(root)
    refused(root, NO_INCUMBENT)


def test_a_missing_run_and_a_missing_data_root_are_run_missing(root, tmp_path):
    refused(root, RUN_MISSING)
    assert refused(tmp_path / "none", RUN_MISSING).__cause__ is not None


def test_the_first_refusal_in_the_order_of_the_mapping_decides(root):
    write_instance(root)
    measured(root, 0, 20)
    error = refused(root, RUN_MISSING, {"qkv": RUN, "o": "gone", "up": "gone-too"})
    assert (error.call_site, error.run_id) == ("o", "gone")


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (b"{", INSTANCE_INVALID),
        (b'{"schema_version": 99}', INSTANCE_OTHER_VERSION),
    ],
)
def test_a_damaged_instance_file_is_named(root, content, reason):
    write_instance(root)
    layout.run_file(root, RUN, "instance.json").write_bytes(content)
    refused(root, reason)


def test_an_unreadable_instance_file_is_named(root, monkeypatch):
    def fails(*_):
        raise PermissionError("denied")

    monkeypatch.setattr(instance, "read", fails)
    assert isinstance(refused(root, INSTANCE_UNREADABLE).__cause__, PermissionError)


def test_a_run_of_another_target_is_refused(root):
    profile = PROFILE | {"accelerator": "mock"}
    hw = {"key": keys.hw_profile_key(profile).name, "record": profile}
    assert profile["accelerator"] != standin_profile.ACCELERATOR
    write_instance(root, hw_profile=hw)
    measured(root, 0, 20)
    refused(root, OTHER_TARGET)


@pytest.mark.parametrize("candidates", [2, None])
def test_a_run_not_of_one_candidate_is_refused(root, candidates):
    write_instance(root, candidates_per_round=candidates)
    measured(root, 0, 20)
    refused(root, NOT_ONE_CANDIDATE)


def test_a_run_without_an_op_signature_is_refused(root):
    write_instance(root, op_signature=None)
    measured(root, 0, 20)
    refused(root, NO_OP_SIGNATURE)


def test_a_run_that_states_no_objective_is_refused(root):
    write_instance(root, objective=None)
    measured(root, 0, 20)
    refused(root, NO_OBJECTIVE)


@pytest.mark.parametrize(
    "objective",
    [
        {"objectives": [{"type": "throughput_maximisation"}], "constraints": []},
        {
            "objectives": [{"type": "latency_minimisation"}],
            "constraints": [{"type": "memory_ceiling", "bound": 1}],
        },
    ],
)
def test_an_objective_the_rule_cannot_honour_is_refused(root, monkeypatch, objective):
    write_instance(root, objective=objective)
    measured(root, 0, 20)
    refused(root, INSTANCE_INVALID)

    write_instance(root)
    real = instance.read
    monkeypatch.setattr(
        instance,
        "read",
        lambda *arguments: real(*arguments)._replace(objective=objective),
    )
    refused(root, OBJECTIVE_UNSUPPORTED)


def test_a_damaged_journal_is_run_file_invalid(root):
    write_instance(root)
    measured(root, 0, 20)
    path = layout.run_file(root, RUN, "events.ndjson")
    path.write_bytes(path.read_bytes() + b"not json\n")
    cause = refused(root, tools.KIND_RUN_FILE_INVALID).__cause__
    assert isinstance(cause, tools.ToolFailure)


def test_a_refused_step_line_without_any_spec_is_run_file_invalid(root):
    write_instance(root)
    data = {"step": "Not A Step", "execution": 1}
    events.append(
        root, RUN, journal.STEP_STARTED, data, round=0, candidate=1, attempt=1
    )
    refused(root, tools.KIND_RUN_FILE_INVALID)


def test_a_check_result_without_outcome_is_named(root):
    write_instance(root)
    write_attempt(root, 0)
    step(root, 0, SIM, result={"max_abs_error": 0.0})
    refused(root, "check_result_invalid")


def test_a_damaged_spec_is_feedback_unreadable(root):
    write_instance(root)
    measured(root, 0, 20)
    layout.attempt_artefact(root, RUN, 0, 1, 1, "spec.json").write_bytes(b"{")
    refused(root, spec_feedback.KIND_FEEDBACK_UNREADABLE)


def test_a_verified_attempt_whose_output_is_gone_is_named_and_not_replaced(root):
    write_instance(root)
    measured(root, 0, 50)
    measured(root, 1, 20)
    shutil.rmtree(layout.attempt_artefact(root, RUN, 1, 1, 1, "output"))
    error = refused(root, kernel_source.NO_OUTPUT_DIRECTORY)
    assert isinstance(error.__cause__, attempt_kernel.AttemptKernelError)


def test_a_timed_attempt_whose_spec_is_gone_is_named_and_not_replaced(root):
    write_instance(root)
    measured(root, 0, 50)
    measured(root, 1, 20)
    layout.attempt_artefact(root, RUN, 1, 1, 1, "spec.json").unlink()
    refused(root, ATTEMPT_WITHOUT_SPEC)


def test_an_output_without_a_compiled_file_is_named(root):
    write_instance(root)
    measured(root, 0, 20)
    output = layout.attempt_artefact(root, RUN, 0, 1, 1, "output")
    (output / "k.c").unlink()
    refused(root, kernel_source.NO_COMPILED_FILE)


def test_nothing_is_written_and_nothing_is_started(root, client):  # noqa: F811
    write_instance(root)
    measured(root, 0, 20)
    before = sorted(
        (path.as_posix(), path.stat().st_mtime_ns) for path in root.rglob("*")
    )
    bound(root)
    after = sorted(
        (path.as_posix(), path.stat().st_mtime_ns) for path in root.rglob("*")
    )
    assert before == after
    assert local_run.run is client
    assert client.calls == []


def test_every_reason_is_distinct():
    assert len(set(REASONS)) == len(REASONS)
    assert set(model_run_binding.READ_FAILURES) <= set(REASONS)
    assert set(attempt_kernel.REASONS) <= set(REASONS)


def test_a_binding_from_six_runs_passes_the_check_and_the_container_path(
    root,
    client,  # noqa: F811
    parent,  # noqa: F811
):
    runs = {kind: f"synthetic-{kind}" for kind in forward.KINDS}
    for kind, run_id in runs.items():
        contract = attempts.FORWARD_CONTRACT[kind]
        write_instance(root, run_id, contract=contract)
        for round_, median in ((0, 50), (1, 20), (2, 90)):
            write_attempt(root, round_, 1, run_id, contract, f"{kind}.c")
            step(root, round_, SIM, 1, run_id, result=PASS)
            step(root, round_, BOARD, 1, run_id, result=PASS)
            step(root, round_, TIMING, 1, run_id, result=timing([median] * 5))
    named = {site: runs[kind] for site, kind in forward_execute.KIND_OF.items()}

    binding = binding_from_runs(root, named, flags=FLAGS)

    assert set(binding) == set(model_forward_run.CALL_SITES)
    for entries in binding.values():
        assert entries[0].shapes == EVERY
        assert entries[0].kernel.sources[0].parent.name == "output"
        assert "rounds/0001/" in entries[0].kernel.sources[0].as_posix()
    result = container.run(parent, binding)
    assert result.check.ok, result.check.outcomes
    assert result.unavailable is None
    assert result.build_failed is None
    assert result.run.failed is None
    assert len(client.runs()) == len(forward.KINDS) + 2
    copied = [name for name in client.seen if name.endswith(".c")]
    assert sorted(name.rsplit("/", 1)[-1] for name in copied if "kernel-" in name) == (
        sorted(f"{kind}.c" for kind in forward.KINDS)
    )
