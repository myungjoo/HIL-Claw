"""PLAN P2-14 with stubs: a bf16 instance of each kind, and a generation from their attempts."""

import numpy as np
import pytest
import test_attempt_kernel as attempt_fixtures
import test_first_run_end_to_end as first_run
import test_model_forward as forward
import test_model_forward_execute as forward_execute
import test_model_reference as reference
from test_first_run_end_to_end import world  # noqa: F401
from test_model_reference import clang  # noqa: F401

from hilclaw import (
    attempt_kernel,
    catalog,
    check_standing,
    elementwise_add_bf16_contract,
    events,
    gemm_bf16_contract,
    model_forward_execute,
    rmsnorm_bf16_contract,
    rope_bf16_contract,
    sdpa_kv_cache_bf16_contract,
    spec,
    spec_file,
    standin_settings,
    swiglu_bf16_contract,
    timings_tool,
)
from hilclaw.model_reference import compare, reference_logits

INSTANCES = {
    "gemm": (gemm_bf16_contract, (3, 8, 12)),
    "rmsnorm": (rmsnorm_bf16_contract, (3, 8)),
    "add": (elementwise_add_bf16_contract, (3, 8)),
    "swiglu": (swiglu_bf16_contract, (3, 12)),
    "rope": (rope_bf16_contract, (3, 4, 4)),
    "sdpa": (sdpa_kv_cache_bf16_contract, (1, 4, 4, 2, 4)),
}
TOLERANCE = {"rtol": 1e-2, "atol": 1e-2}
CHOICES = {
    "default": {
        "techniques": [],
        "statement": "Compiling the same kernel again leaves the board latency "
        "lower against the round-0 baseline.",
        "direction": "lower",
    }
}
CHECKS = ("correctness_check_sim_v2", "correctness_check_board_v2")
ROUND_CONTAINERS = [
    None,
    "coder",
    None,
    "build",
    "process",
    "build",
    "process",
    "build",
    "build",
    "timing",
]
WRONG_ADD = reference.REAL_PRELUDE + reference.REAL_SOURCES["add"].replace(
    "widen(a[i]) + widen(b[i])", "widen(a[i]) + widen(b[i]) + 1.0f"
)


def record_of(kind):
    module, shape = INSTANCES[kind]
    return module.op_signature_record(*shape)


def kernel_of(kind):
    return reference.REAL_PRELUDE + reference.REAL_SOURCES[kind]


def run_instance(world, kind, choices=CHOICES):  # noqa: F811
    record = record_of(kind)
    module, shape = INSTANCES[kind]
    key = {name: record[name] for name in ("kind", "dtype", "layout")}
    world.install(kernel=kernel_of(kind), name=f"{kind}.c", choices=choices)
    turns_before = len(first_run.turns(world.session_log()))
    docker_before = len(world.docker_runs())

    run_id = world.new_run(first_run.document(budget=2, op=record, tolerance=TOLERANCE))
    done = world.turn_start(run_id)

    first_run.told(done, "run_over", 0)
    state = first_run.state_of(world, run_id)
    assert (state.round, state.others) == (2, {"run_status": "over"})
    log = world.session_log()
    zero, one = turns_before + 1, turns_before + 2
    assert first_run.turns(log)[turns_before:] == [zero, one]
    assert first_run.steps(log, zero) == first_run.ROUND_ZERO
    assert first_run.steps(log, one) == first_run.later_round(1)
    first_run.assert_hooks_ran_and_passed(
        first_run.requests(log, zero) + first_run.requests(log, one)
    )

    run = world.run_dir(run_id)
    content = spec_file.parse((run / first_run.ATTEMPT / "spec.json").read_bytes())
    spec.validate(content)
    assert content["task"]["contract"] == attempt_fixtures.as_parsed(
        module.task_contract(*shape)
    )
    output = run / first_run.ATTEMPT / "output" / f"{kind}.c"
    assert output.read_text(encoding="utf-8") == kernel_of(kind)

    lines = events.read(world.root, run_id).events
    for line in lines:
        events.validate(line)
    for round_ in (0, 1):
        ended = [
            line
            for line in lines
            if line["round"] == round_ and line["kind"] == "step_ended"
        ]
        assert [line["data"]["step"] for line in ended] == [
            *CHECKS,
            "board_run_timing_v2",
        ]
        for name, line in zip(CHECKS, ended):
            assert line["data"]["result"]["outcome"] == "pass", line
            assert line["data"]["result"]["contract_key"] == key
            for counted in line["data"]["result"]["counts"].values():
                assert not any(value for c in counted for value in c.values())
            found = check_standing.standing(lines, name, round_, 1, 1)
            assert found is check_standing.Standing.VERIFIED
        timing = ended[-1]["data"]["result"]
        assert timings_tool.timing_problem(timing) is None
        assert timing["contract_key"] == key
        assert timing["shape"] == record["shape"]
        assert timing["unit"] == "ns"
        assert timing["outcome"] in ("converged", "not_converged")

    _, judged, later = first_run.stored_round(world, run_id, 1, record)
    assert later["guidance"]["techniques"] == []
    assert [entry["hypothesis"] for entry in judged["verdicts"]] == ["h1"]
    first_run.assert_committed_clean(world, run_id)

    runs = world.docker_runs()[docker_before:]
    assert all(entry["status"] == 0 for entry in runs)
    assert [entry.get("container") for entry in runs] == ROUND_CONTAINERS * 2
    fed = [entry for entry in runs if entry.get("input")]
    if kind == "rope":
        assert [entry["container"] for entry in fed] == [
            "process",
            "process",
            "timing",
        ] * 2
        m, _, d = shape
        assert {len(entry["input"]) // 2 for entry in fed} == {m * d * 4}
    else:
        assert fed == []
    return run_id


@pytest.mark.parametrize("kind", sorted(INSTANCES))
def test_an_instance_of_each_kind_runs_to_run_over(world, kind):  # noqa: F811
    run_instance(world, kind)


def test_a_selector_that_would_choose_a_catalog_id_sees_no_entry(world):  # noqa: F811
    wanted = "loop_order_ikj"
    assert wanted in catalog.criteria("cpu_standin")
    choices = {"default": CHOICES["default"] | {"techniques": [wanted]}}
    run_instance(world, "gemm", choices)


def test_a_wrong_kernel_leaves_its_attempt_not_standing(world):  # noqa: F811
    world.install(kernel=WRONG_ADD, name="add.c")
    run_id = world.new_run(first_run.document(op=record_of("add"), tolerance=TOLERANCE))
    run = world.run_dir(run_id)

    done = world.turn_start(run_id)

    first_run.told(done, "run_over", 0)
    state = first_run.state_of(world, run_id)
    assert (state.round, state.others) == (1, {"run_status": "over"})
    log = world.session_log()
    assert first_run.turns(log) == [1]
    assert first_run.steps(log, 1) == first_run.ROUND_ZERO[:11] + [
        ("round-manager", "round_end"),
        ("round-manager", "run_commit"),
    ]
    assert (run / first_run.ATTEMPT / "output/add.c").is_file()
    lines = events.read(world.root, run_id).events
    assert [line["data"]["step"] for line in lines] == [CHECKS[0]] * 2
    assert lines[-1]["data"]["result"]["outcome"] == "fail"
    found = check_standing.standing(lines, CHECKS[0], 0, 1, 1)
    assert found is check_standing.Standing.NOT_VERIFIED
    first_run.assert_hooks_ran_and_passed(first_run.requests(log))
    first_run.assert_stopped_once(log, 1)
    assert not (run / "rounds/0000/eval").exists()
    coders = [e for e in world.docker_runs() if e.get("container") == "coder"]
    assert len(coders) == 1
    timing_log = run / first_run.MEASURE / "build-log-board_run_timing_v2-01.txt"
    assert not timing_log.exists()
    first_run.assert_committed_clean(world, run_id)


def test_a_generation_from_the_attempts_of_the_six_instances_matches_the_reference(
    world,  # noqa: F811
    clang,  # noqa: F811
    tmp_path,
    monkeypatch,
):
    runs = {kind: run_instance(world, kind) for kind in INSTANCES}
    assert len(set(runs.values())) == len(INSTANCES)
    # The world's guard allows only Python and git; the generation builds with clang.
    monkeypatch.undo()
    kernels = {
        kind: attempt_kernel.kernel_reference(
            world.root, run_id, 0, 1, 1, flags=standin_settings.FLAGS
        )
        for kind, run_id in runs.items()
    }
    for kind, kernel in kernels.items():
        assert [path.name for path in kernel.sources] == [f"{kind}.c"]
        assert runs[kind] in str(kernel.sources[0])
    model = reference.sharp_model(73, 3, 3)
    builds = tmp_path / "builds"
    builds.mkdir()

    result = model_forward_execute.execute(
        reference.DIMENSIONS,
        forward_execute.binding_of(kernels),
        **reference.arguments(model, lm_head_rows="all", given=None),
        generation_length=model["G"],
        build_timeout_s=forward.BUILD_TIMEOUT,
        run_timeout_s=forward.RUN_TIMEOUT,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )

    assert result.check.ok, result.check.outcomes
    assert result.build_failed is None, result.build_failed
    assert result.run.failed is None, result.run.run.stderr
    report = result.run.report
    assert np.array_equal(report.tokens[:3], model["tokens"][:3])
    selected = [int(token) for token in report.tokens[3:]]
    assert len(set(selected)) > 1
    expected = reference_logits(
        reference.DIMENSIONS,
        **reference.arguments(model, given=selected, lm_head_rows="all"),
    )
    rtol, atol = reference.tolerance(expected)
    assert compare(report, expected, rtol=rtol, atol=atol).ok
