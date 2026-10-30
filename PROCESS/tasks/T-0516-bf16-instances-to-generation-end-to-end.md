---
id: T-0516
title: Prove PLAN P2-14 with stubs — a bf16 instance of each of the six kinds runs to run_over through stub claude, and the model executor generates tokens from their attempts that match the reference
phase: P2
status: DONE
commitMode: code
coversReq: [C-6, S0, FR-1, FR-9, FR-10, OD-31, "PLAN P2-14"]
dependsOn: [T-0515]
touchesFiles:
  - tests/test_bf16_end_to_end.py
  - tests/first_run_stubs.py
  - tests/test_first_run_end_to_end.py
  - hilclaw/
estimatedSize: {loc: 80, files: 3}   # test code is outside the cap; the non-test lines are fixes of what the run finds, sized only as a guess
hq: []
---
## Why

**State.** PLAN P2-14 reads: "P2-11의 각 연산에 대해 instance가 커널을 내고, P2-13의 실행기가 그 커널로 토큰을 생성해 reference와 맞는다 — 드라이버 task의 검증은 스텁 `claude`와 합성 가중치·토크나이저이고(D16), 이 항목의 완료는 실제 run의 결과에 달려 있지 않다."

After T-0515 the instance start admits all six bf16 kinds. Two tests hold the parts of this separately:

- `tests/test_first_run_end_to_end.py` runs fp32 `gemm` only, from `hilclaw.new_run` and `hilclaw.turn_start` through stub `claude` and stub `docker`.
- `tests/test_attempt_kernel.py::test_a_greedy_generation_whose_every_kernel_comes_from_an_attempt` generates tokens from attempts that the test wrote by hand.

Nothing joins them, and no test has yet taken a bf16 kind through the round steps. This task joins them and fixes what the join breaks.

**Why now (PLAN checklist, D24 ⑤).** P2-11 to P2-14 go first to a run with the minimal set and then fill what breaks. The set is the six bf16 instance kinds of ADR-0152 decision 2, with lm_head not in the first runs. A real run of that set is the owner's to start (D17 (가), D25). This task is the stub part that P2-14 itself names, and it is a checklist item, so D18 does not apply.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `44b79238`.

**D16.** Everything uses the stub `claude` and stub `docker` of `tests/first_run_stubs.py` and synthetic weights. No real `claude`, Docker daemon, weights, tokenizer or key is used.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5. These cover the branch name `claude/T-0516-<slug>`, the `Task: T-0516` trailer in commits and as the last line of the PR body, the size cap, D12 and D21. Also read §3 "BLOCKED 사유" and §8 (D22).
- `CLAUDE.md`: the A-13 code mode, the BLOCKED reasons, the test rules (rule ⑤ forbids tests that target test code; this task tests the package through its entries) and comment minimisation.
- `PROCESS/PLAN.md`: P2-11, P2-13, P2-14 and P2-15, and the P2 header on D24 ⑤.
- `PROCESS/tasks/T-0515-standin-bf16-run-and-timed-flags.md`, `## Result`.
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: decisions 2 and 4.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (how a kernel is referenced).
- `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md`: decision 4 (the executor's binding stays with OD-20 and OD-7).
- Tests:
  - `tests/test_first_run_end_to_end.py`: `document` (lines 272-286), `World` (289-381), the `world` fixture (384-405), `ROUND_ZERO` (410-429), and `test_round_zero_of_a_first_run_ends_the_run_over` (506 on).
  - `tests/first_run_stubs.py`: the module docstring, `_coder` (841-854) and `_standin` / `_timing` (863-903).
  - `tests/test_attempt_kernel.py`: `write_forward_attempts`, `attempt_binding` and the greedy generation test (lines 496-572).
  - `tests/test_model_reference.py`: `REAL_SOURCES`, `REAL_PRELUDE`, `sharp_model`, `arguments`, `tolerance`.
  - `tests/test_model_forward.py` and `tests/test_model_forward_execute.py`: `KINDS`, `KERNEL_FLAGS`, `binding_of`.
- Code: `hilclaw/attempt_kernel.py` (`kernel_reference`), `hilclaw/model_forward_execute.py` (`execute`), `hilclaw/model_reference.py`, and each contract's `op_signature_record` in `hilclaw/*_bf16_contract.py`.

## Acceptance Criteria

1. **A new test file**, `tests/test_bf16_end_to_end.py`, reuses the fixtures of `tests/test_first_run_end_to_end.py` and `tests/test_attempt_kernel.py` by import, as `tests/test_attempt_kernel.py` imports its neighbours. Small changes to the shared fixtures are allowed:
   - a kernel file name that is not `gemm.c`;
   - a document built from any op_signature record;
   - the stub's handling of anything fp32-specific.

   Existing tests keep passing and their assertions do not change. The file has the same skips as its model: no `os.getuid`, no git, no clang.
2. **One instance of each kind.** For each of `gemm`, `rmsnorm`, `elementwise_add`, `swiglu`, `rope` and `sdpa_kv_cache` at `bf16`, at a small shape the contract's `covers` admits, with `round_budget` 2:
   - `hilclaw.new_run` answers `started`, and `hilclaw.turn_start` ends the run `run_over`, turn after turn.
   - Round 0 walks the `ROUND_ZERO` steps. The coder's stub leaves a correct kernel of the kind, from `tests/test_model_reference.py`'s sources or an equivalent.
   - The spec's `task.contract` is the kind's `task_contract` for the stated shape.
   - The checks at `sim` and `board` stand as verified, on the real bf16 verification program built by the host clang behind the stub `docker`.
   - The `board.run` line holds a v2 result with the kind's `contract_key` and `shape`, `unit` `ns` and `outcome` `converged` or `not_converged`, measured by the real bf16 timing program.
   - For `rope`, the rows reach the verification and the timing process on standard input, and the docker log shows no input given to a build container.
   - Round 1 runs the later-round steps with a selector choice of an empty `techniques` list. Verdicts are written and a case is stored. The verdict value is not pinned, because it depends on timing noise.
   - The hooks ran and passed, as `assert_hooks_ran_and_passed` asserts, and the data checkout is clean, as `assert_committed_clean` asserts.
   - Tolerance values in the fixture are test inputs only and decide nothing (owner, HQ-0066 (2)). Use values wide enough for a correct kernel. If a correct kernel fails the check, treat it as a finding: do not loosen the fixture to hide it.
3. **A negative case of the same path.** For one kind, a wrong kernel from the coder's stub leaves its attempt not standing, and the run still ends as the fp32 test `test_round_zero_without_an_attempt_that_stands_ends_its_round` says, apart from the kind.
4. **Generation from those runs.** A test runs the six instances of criterion 2 in one data root, or one shared `world`, then:
   - names each run's round 0 attempt with `attempt_kernel.kernel_reference(root, run_id, 0, 1, 1, flags=...)`;
   - forms the binding of the model executor from those references;
   - calls `model_forward_execute.execute` with the synthetic model of `tests/test_model_reference.py`, as the greedy generation test does;
   - asserts that the check, the build and the run succeed, that the tokens hold more than one distinct selected token, and that `model_reference` comparison answers `ok` under the fixture's tolerance.

   If the instance shapes differ from the synthetic model's dimensions, keep to what the executor's call-site check accepts, and say in the Result what shape each instance used.
5. **Fixes.** Anything fp32-only or `m`-`k`-`n`-only that this run finds in `hilclaw/` or `orchestration/` is fixed in this task if a landed record already decides it and the task stays within the size cap (DRIVER §5). Each fix gets a test under D12. The Result lists each finding.
   - A finding that needs a design decision no record gives is not invented. It is a BLOCKED reason (DRIVER §3, §9), or an ADR under §9 only when it is clearly design-level and small.
   - A finding that only a real session can show is a runtime acceptance item.
   - A fix over the cap is proposed as a split in Follow-ups (DRIVER §5).
6. **Binding stays by name.** This task adds no way of choosing kernels from a key's best (OD-20, OD-7, and the owner's OD-1 / #5 A-4) and no user-facing entry for the executor (OD-31 ⑩, OD-18, OD-23). The test names the attempts itself. If a helper is needed, it lives in the test file.
7. **Result** records:
   - the language and reason, if a package module changes;
   - the kind-to-shape table;
   - the findings and their fixes, or that there were none;
   - any edited assertion (D21);
   - runtime acceptance items;
   - whether PLAN P2-14's stated completion now holds in the executor's reading, so that the driver can set its checkbox, and P2-15's RA item follows from the PLAN rule;
   - what stays open for the real run: the executor's exposure and the binding from a key's best.

## Out of Scope

- A real `claude` run, including a D25 test run, and a real Docker daemon, real weights or a real tokenizer (D16; P2-15).
- Widening the nightly run configuration (D17 (가), the owner's value, through DRIVER §8).
- Five rounds per kind, lm_head instances (ADR-0152 decision 4), fp16 (after P2-14, HQ-0065 (1)) and catalog entries for bf16 (OD-22).
- Moving the fp32 `model_execute` path into containers (ADR-0182 slice 3, on the PLAN hold list).
- Any accepted value of an owner decision.

## Follow-ups

## Result

- **DONE.** PR #335 squash-merged as `b72560ac`; the branch is deleted.
- **Review**: 1 round, Approve with no findings.
- **Tests**:
  - CI on `b8ddca06`: the run concluded `success`. `tests/test_bf16_end_to_end.py` ran on Linux with all 8 tests passing, not skipped (the Python 3.11 and Coverage gate logs). Each suite: 38773 passed, 50 skipped.
  - Coverage: line TOTAL 99 % as the reviewer read it from the log. No `hilclaw/` line changed.
  - `gh pr checks` kept showing `sh gate (shellcheck)` as `pending`, while the jobs API gave status `in_progress` and conclusion `success`, and the run as `completed` / `success`. The PR changes no shell file, so the merge treated this as a stale display.
  - WSL (Python 3.12, clang 14): the new file plus `test_first_run_end_to_end` and `test_attempt_kernel` passed, the new file again after the last edit. The WSL copy was temporary and is removed.
  - Native Windows: the new file skips as a module (1 skipped). The full suite was not rerun on Windows, because only test files changed.
- **Language**: none to record. No package module changed.
- **Files changed**: `tests/test_bf16_end_to_end.py` (new), `tests/first_run_stubs.py`, `tests/test_first_run_end_to_end.py`.
- **Kinds and shapes**, all call shapes of the synthetic model at prompt length 3, bound with `"every"` entries so the executor's call-site check does not compare them:
  | Kind | Shape | Call site |
  | --- | --- | --- |
  | `gemm` | m=3, k=8, n=12 | `gate`, prefill |
  | `rmsnorm` | m=3, n=8 | prefill |
  | `elementwise_add` | m=3, n=8 | prefill |
  | `swiglu` | m=3, n=12 | prefill |
  | `rope` | m=3, h=4, d=4 | `rope_q`, prefill |
  | `sdpa_kv_cache` | m=1, l=4, h=4, h_kv=2, d=4 | first decode pass |
- **Fixture values**: instance tolerance `rtol` and `atol` 1e-2, a test input only (HQ-0066 (2)). Correct kernels passed at this value on the first try. The generation's comparison uses the existing `reference.tolerance`. The negative case is a wrong `elementwise_add` kernel.
- **Findings in `hilclaw/` and `orchestration/`**: none, so no fixes.
- **Fixture changes (no assertion edited, so D21 has nothing to list)**:
  - `document` gained `op` and `tolerance`, `World.install` gained `name`, and `round_paths` and `stored_round` gained `op`, all defaulting to the old values.
  - The stub `docker` now reads its standard input for an `--interactive` container, hands it to the process and logs it as `input`.
  - The `rope` assertion rests on that log: rows of m·d·4 bytes reach the process and timing containers in both rounds, and no input reaches a build container.
- **Host path used by the generation test**: `model_forward_execute.execute` runs builds on the host, as criterion 4 names. ADR-0182 decision 7 keeps this path for kernels a test wrote itself. Here the stub coder places those test-written kernels in the run's attempt directory, and the test asserts they are byte-equal to its source. The reviewer called this a slightly wider reading and raised no finding. The test calls `monkeypatch.undo()` to lift the `world` guard for the host clang.
- **Runtime acceptance items**: none new from this change. P2-15's item follows from the PLAN rule below.
- **PLAN P2-14**: complete in the executor's reading. Each of the six kinds' instances gives a kernel, and the executor generates tokens from those kernels that match the reference, on stub `claude` and synthetic weights as P2-14 states. The checkbox is the driver's.
  - The P2-15 RA item (source `P2-15`, evidence task T-0516) is due at the first iteration in which the planner reads PLAN after the box is checked.
  - P2-12 stays unchecked and this task does not change that; fp16 comes after P2-14 (HQ-0065 (1)).
- **Open for the real run**:
  - the executor's exposure: no user-facing entry (OD-31 ⑩, OD-18, OD-23);
  - the binding from a key's best (OD-20, OD-7, #5 A-4);
  - a coder's real kernels must go through `hilclaw/model_forward_container.py`, never the host path (ADR-0182 decision 7);
  - real weights and tokenizer (OD-31 ⑤·⑦, P2-15);
  - the nightly configuration (D17 (가)).
- **Not exercised here**: five rounds per kind, lm_head instances, fp16 and bf16 catalog entries, all out of scope for this task. The empty `techniques` choice is why no bf16 catalog entry was needed.
- **Follow-ups**: none.
