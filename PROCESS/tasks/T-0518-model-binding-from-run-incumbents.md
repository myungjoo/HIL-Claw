---
id: T-0518
title: Derive the model executor's binding from the incumbents of named runs (ADR-0189, OD-31 sub-question 4, part of OD-20)
phase: P2
status: DONE
commitMode: code
coversReq: [OD-31, OD-20, C-6, FR-10, "PLAN P2-15", D26]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0189-od31-binding-from-run-incumbents.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/model_run_binding.py
  - hilclaw/spec_feedback.py
  - hilclaw/attempt_kernel.py
  - tests/test_model_run_binding.py
  - tests/test_spec_feedback.py
estimatedSize: {loc: 400, files: 7}   # test code is outside the cap
hq: []
---
## Why

**State.** PLAN P2-15 is the owner's run of the real Llama 3.2 1B through the kernels the instances produced. The executor takes an explicit binding: each call site names a kernel reference. `hilclaw.attempt_kernel.kernel_reference` makes a reference from an attempt that its caller names. Nothing goes from a finished run to the attempt to use, so the owner would have to read each run's journal by hand. ADR-0153 decision 3 and OD-31 sub-question 4 leave open "how a binding is derived from a key's best". T-0516's Result lists the same point as open for the real run.

**Why now (D26).** DRIVER §6 D26 asks what the owner needs to run P2-15. It names this work: the T-0516 follow-up line of the PLAN hold section ("P2-15 준비"), with the binding method closed through the ADR path of §9. It comes ahead of the HQ-0080 groups and of the remaining checklist items.

**Not waiting on an HQ.** HQ-0084 (real weights, tokenizer and the entry point) is unanswered and says other driver tasks are not blocked. Whichever way its part ④ goes, the owner's run needs a binding, so this task reads none of its answers. The user-facing entry half of the same hold line stays open and is out of scope here.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `1bfb054d`.

**D16.** Verification uses test-written runs, kernels and synthetic weights. No real `claude`, Docker daemon, weights or tokenizer is used.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (branch `claude/T-0518-<slug>`, the `Task: T-0518` trailer in commits and as the last line of the PR body, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D26, §8 (D22) and §9.
- `CLAUDE.md`: A-13 code mode, the BLOCKED reasons, the test rules, comment minimisation, the language policy and the coverage recheck for `ARCHITECTURE/` edits.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decisions 1, 3 and 5, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0184-od20-first-case-incumbent-base.md`: all of it.
- `ARCHITECTURE/decisions/ADR-0074-od30-s6-metric.md` (the file whose name starts `ADR-0074-`): decision 1, on the first-run best and on why it need not be the incumbent.
- `ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md`: decision 7 (a coder's kernels run only through `hilclaw/model_forward_container.py`).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: decisions 2 and 4 (call sites; lm_head).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decision 5 (`best.json`).
- `ARCHITECTURE/decisions/ADR-0053-od8-instance-record-objective.md` and `hilclaw/instance.py` `objective_of`.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph and the OD-20 and OD-31 rows.
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" paragraph in the header, and sections OD-20 and OD-31.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과.
- Code: `hilclaw/spec_feedback.py` (`feedback`, `_found`, `_board_median`), `hilclaw/attempt_kernel.py`, `hilclaw/model_binding.py` (`BindingEntry`, `KernelReference`, `_entry`, the call-site tuples), `hilclaw/model_forward_container.py` (`execute`), `hilclaw/standin_settings.py` (`FLAGS`).
- Tests: `tests/test_bf16_end_to_end.py` (the generation test), `tests/test_attempt_kernel.py` (`attempt_binding`), `tests/test_spec_feedback.py` (fixtures).

## Acceptance Criteria

1. **ADR-0189**, in the "Record format" of ADR-0001, decides for first-case runs with one candidate per round:
   - **Which attempt of a run.** The starting point is the rule of ADR-0184 decision 2, applied over all rounds of the run: verified at both points, lowest median, earliest `(round, attempt)` on a tie. The owner approved that rule for choosing the fastest correct code. State why it fits a binding and why the trimmed mean of ADR-0074 decision 1 was not chosen. If the reading shows the ADR-0074 rule is the better one, choose it and say why. Do not make the two rules read each other.
   - **Which runs.** The first form: the caller names, for each call site, the run whose incumbent it binds. The call site, not the kind, is the unit, because ADR-0153 keeps lm_head and each projection as separate call sites and ADR-0152 decision 4 keeps lm_head out of the first runs. Choosing among several runs of a key is left to Boundaries unless the ADR shows a small rule. A cross-run rule must say how it treats drift between runs and runs of a test or nightly routine that stored cases in the same data root (DRIVER D25).
   - **What it does not add.** No file, member, value or version of the data plane. `best.json` and `best_ref` stay open (OD-20). A design that needs any of them is the BLOCKED reason of A-13, not a choice for this ADR.
   - **Objective.** The rule compares latency, which is what OD-1's decided part gives. A run whose `instance.json` states another objective, or a constraint the rule cannot honour, gets a named refusal. Nothing is invented for it. If a value the owner must give comes to light (#5 A-4, OD-1, C-6), return BLOCKED so the driver asks through §8.
   - **Shapes.** Which `shapes` the entry carries: `"every"` where the kind's contract obliges correctness at every shape (ADR-0153 decision 3), otherwise what the contract and the run's spec allow. Do not assume "every" for all kinds; read each kind's contract record. A kind that cannot be bound from one instance shape is stated in the ADR with what follows from it for P2-15.
   - **Build settings.** Where `flags` comes from. The caller gives them, as in `attempt_kernel.kernel_reference`, unless the ADR shows a better landed source. Do not add a build-settings record.
   - **Boundaries** names what stays open: the user-facing entry (OD-31 ⑩, OD-18, OD-23, HQ-0084 ④), real weights and tokenizer (OD-31 ⑤·⑦), runs with N > 1, a run still in progress if the ADR does not settle it, and the rest of OD-20. It also lists any runtime acceptance item for `PROCESS/RuntimeAcceptance.md`.
2. **A new module**, `hilclaw/model_run_binding.py` (or a better name the ADR gives), with the Doxygen-style public documentation of its neighbours:
   - Its public function takes the data root, a mapping from call site to run id and the build settings, and returns the mapping `hilclaw.model_binding.check` and its siblings take, of `BindingEntry` values, built with `attempt_kernel.kernel_reference`.
   - It reuses the incumbent code of `spec_feedback` through a public function rather than a copy. If reading the incumbent needs a small public function there, add it, with no change of `feedback`'s behaviour.
   - It reads only and writes nothing. It starts no build, container or process, and is registered as no tool.
3. **Tests**, in `tests/test_model_run_binding.py` (a new module needs its own test file), cover:
   - **Happy:** a run with several verified attempts binds the one with the lowest median; a later slower round does not displace it; the same run may serve two call sites.
   - **Branch:** the tie rule; a not-converged measurement, as the ADR rules; a repair attempt (`attempt` > 1); each `shapes` form the ADR names.
   - **Error and negative:** a run with no verified attempt; a run that is missing; a malformed run id or call site or flags; a damaged journal or spec, with the failure the module names; a verified attempt whose `output/` is gone; a run with an unsupported objective. Each outcome is a named error, never a silent fallback to another attempt.
   - **One joined path:** runs written as the existing fixtures write them, whose derived binding passes the executor's binding check and is accepted by `model_forward_container.execute` under the stub `docker` client of `tests/test_model_forward_container.py`. If that stub cannot carry a whole generation, the test stops at the first container call and asserts what was built, and the Result says so. Do not use the host path of ADR-0182 decision 7 for this test unless the kernels are test-written and the Result says so.
   - Every public function of a touched module is covered. Existing tests keep passing. Their assertions do not change except the list assertions D21 allows; the foreseen one is any assertion pinning the public names or imports of `hilclaw/spec_feedback.py` or `hilclaw/attempt_kernel.py`, if one exists. List each edited assertion in the PR body.
4. **Records.**
   - `Requirements.md` follows its "행 형식": one link per new ADR in the OD-31 and OD-20 rows, with the open parts rewritten in place.
   - `OpenDecisionProposals.md` follows its header's "기록 규칙": one `채택분` line in each of OD-31 and OD-20, and the sub-question ④ status rewritten in place (`남음` loses what this ADR answers).
   - `StandardScenarios.md` §검사 결과 follows the rule in its first paragraph: record only if a verdict changes. Recheck coverage either way, as CLAUDE.md requires.
   - Restate no content of the ADR in any of them, and add no dated paragraph.
   - If `hilclaw/attempt_kernel.py`'s docstring sentence "chooses no attempt for a call site" stays true, leave it. Add only a pointer if a reader needs one.
5. **Result** records: the language and the reason for it; the rule the ADR chose and why; the call-site-to-`shapes` table by kind; any edited assertion (D21); runtime acceptance items, for the driver to add; that the §9 notice on #5 is due with its 7-day window; and what the owner's P2-15 run still lacks after this task.

## Out of Scope

- The user-facing entry of the executor, and reading real weights or a tokenizer, including the `transformers` comparison (HQ-0084, OD-31 ⑤·⑦, ⑩). Do not guess its answers.
- A real `claude` run, a D25 test run, a Docker daemon, real weights or a tokenizer (D16; RA-0056).
- `best.json`, `best_ref` and any other data-plane change (A-13).
- Moving the fp32 `hilclaw/model_execute.py` path into containers, and other lines of the PLAN hold section.
- Editing ADR-0184's sentence that the median is the figure ADR-0140's comparison rests on (T-0231 follow-up line on the hold list).
- fp16 (HQ-0083) and P2-8.

## Follow-ups

## Result

**DONE.** PR #338, squash-merged as 4755248c. 1 review round (Approve). CI green on f62e5323, including the coverage gate. Commit f62e5323 came after the Approve and was not re-reviewed: three wording nits (D20), and the `standin_profile` import replaced by the local constant `TARGET`, with the same behaviour, because `tests/test_standin_profile.py` pins who may name that module.

**Language:** Python. The module is host-side layer-2 code that reads run files and returns the executor's Python binding values.

**Rule chosen (ADR-0189):** the caller names one run per call site. The entry is the run's incumbent by ADR-0184 decision 2 over all rounds: verified at both points, lowest median, earliest `(round, attempt)` on a tie. The trimmed mean of ADR-0074 was not chosen: it admits only converged measurements because `not_different` grants reaching there, while a binding grants nothing to a wide interval and would lose a kernel that never converges. A wrong pick costs speed, not correctness. Each outcome other than a binding is a named refusal, never a fallback to another attempt. Refusals beyond the task's list: `other_target`, `not_one_candidate`, `no_op_signature`, `attempt_without_spec`. A run in progress gives its incumbent so far and is not refused. `flags` come from the caller. No data-plane change.

**Call site to `shapes`:**

| Kind | Call sites | Obligation | `shapes` |
|---|---|---|---|
| `gemm` fp32, bf16 | `qkv`, `o`, `gate`, `up`, `down`, `lm_head` | ADR-0008 d6; ADR-0156 d7 | `"every"` |
| `rmsnorm` | `attention_norm`, `ffn_norm`, `norm` | ADR-0158 d7 | `"every"` |
| `elementwise_add` | `attention_residual`, `ffn_residual` | ADR-0159 d8 | `"every"` |
| `swiglu` | `ffn_activation` | ADR-0160 d8 | `"every"` |
| `rope` | `rope_q`, `rope_k` | ADR-0161 d11 | `"every"` |
| `sdpa_kv_cache` | `sdpa` | ADR-0162 d11 | `"every"` |

**Joined test:** six runs whose derived binding passes the whole-generation check and is accepted by `model_forward_container.execute` under the stub `docker` client, through a full generation with the stub's report. Kernels are test-written; the host path is not used.

**Edited assertions (D21):** none.

**Runtime acceptance items:** none new. RA-0056 (P2-15) exercises a derived binding at real dimensions.

**§9:** the notice is posted on #5 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6531737224); the 7-day objection window runs from it.

**What the owner's P2-15 run still lacks:** the user-facing entry (OD-31 ⑩, OD-18, OD-23, HQ-0084 ④); real weights and tokenizer reading and the `transformers` comparison (OD-31 ⑤·⑦, HQ-0084); the instance runs themselves, including a bf16 `gemm` run to name for `lm_head` (B-4 excludes an lm_head instance from the first runs). "Every" rests on the contract, not on verification at other shapes (OD-16 ①), so a kernel correct only at its instance shape shows up as `run failed` or in the model-level comparison.

**Follow-ups:** none.
