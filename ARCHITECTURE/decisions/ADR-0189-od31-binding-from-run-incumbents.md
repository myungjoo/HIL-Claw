# ADR-0189: The model executor's binding from runs the caller names — each call site binds its run's incumbent over all rounds, for every shape, with the build settings the caller gives (part of OD-31 sub-question 4, part of OD-20, for first-case runs with one candidate per round)

## Status

- **Accepted on 2026-10-31** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Two kinds of content.** What an owner decision or an accepted record says is **cited**, with its source named. **Everything else is this record's own**: applying ADR-0184's rule to a binding, the unit, the scope and its refusals, the use of `"every"`, and the treatment of a run in progress.
- **The owner-sentence search.** Searched: the comments of #4, #5, #7 and #8 that hold no "posted by driver" marker, for binding, incumbent, `best.json`, `best_ref`. No sentence says how a binding is derived. The nearest is the owner's real-run record that approves the incumbent rule of ADR-0184 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6512287389), which is about the start of a coder call.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `897b2f79`). **HQ-0084** (weights, tokenizer, packages, the entry point): none of its answers is used. **HQ-0081** (the S6 scale), **HQ-0082** (the guard hook) and **HQ-0083** (fp16): not touched.
- **No member, file, kind, value or version of the data plane is added or changed.** `best.json` and `best_ref` stay open (OD-20). The derivation reads existing files and writes nothing.
- **Answers part of OD-31 sub-question 4**: how a binding is derived from what a first-case run has recorded (ADR-0153 decision 3 left this open). **Answers part of OD-20** only for that use. Boundaries lists the rest.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The explicit binding** (cited, ADR-0153 decision 3): for each call site, a kernel reference for listed shapes or for every shape; "The executor never chooses a kernel itself"; "How a binding is derived from a key's best is open".
- **What exists**: `attempt_kernel.kernel_reference` makes a reference from an attempt its caller names. `spec_feedback.feedback` applies ADR-0184 decision 2 to the rounds below the one it is given. `best.json` has no content (cited: ADR-0004 decision 5).
- **Why now** (cited: DRIVER §6 D26): the work is what the owner needs to run PLAN P2-15.
- **Two rules of "best" exist**, for different purposes, and neither reads the other (cited: ADR-0074 decision 1): the incumbent of ADR-0184 decision 2 and the first-run best of ADR-0074 decision 1.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

A run whose `instance.json` names the accelerator `cpu_standin`, the executor's only target (cited: ADR-0153 decision 1), and states `candidates_per_round` 1 and an `op_signature`, the run shape of ADR-0151 decision 1 and of ADR-0184 decision 1. Any other run is refused by name: `other_target` (the mock among them, whose timings say nothing of a kernel), `not_one_candidate` (a run that states no number among them, cited: ADR-0028 decision 4), `no_op_signature`.

### 2. Which attempt of a run: the incumbent over all rounds

- **The rule** is ADR-0184 decision 2, unchanged, applied over every round of the run, the last included: verified at both points, the lowest median at `board_run_timing_v2`, the earliest `(round, attempt)` on a tie. A repair attempt and a `not_converged` measurement compete as there. The code is one reading: `spec_feedback.incumbent` uses what `feedback` uses.
- **Why it fits a binding**: the owner approved it for finding the fastest correct code of a run (cited: the #5 record above). A binding asks the same question. Correctness comes from the standing at both points, so a wrong pick costs some speed and not correctness.
- **Why not the trimmed mean of ADR-0074 decision 1**: that order serves a comparison across two runs, and it admits only `converged` measurements because there `not_different` grants reaching (cited: ADR-0074 decision 1). A binding grants nothing to a wide interval. It does need a kernel: the owner's real runs found that a small kernel may never converge (cited: the #5 record, F1), and the metric's rule would leave such a call site with no kernel, so the owner's run could not start. The binding also stays the attempt a next round of the run would start from, so one name holds for both. The two rules stay separate and may name different attempts; this record makes neither read the other.
- **No silent fallback.** No incumbent is `no_incumbent`. An incumbent that gives no kernel, its `output/` gone among them, is the reason of `attempt_kernel`, and the next-fastest attempt is not tried. A timing step in the journal whose attempt has no `spec.json` is `attempt_without_spec`, since the rule would not see that attempt and could name a slower one. A damaged journal or spec is the kind of the read that refused it.

### 3. Which runs: the caller names one run per call site

- The input is a mapping from call site to run id. The call site is the unit, not the kind: lm_head and each projection are separate call sites (cited: ADR-0153 decision 3). One run may serve several call sites, and they then share one reference, which the executor builds once.
- **No choice among several runs of a key.** A cross-run rule would have to compare medians across runs, which drift between measurements does not allow (cited: ADR-0074 Context, on ADR-0007 decision 7), and to tell the owner's runs from those of a test or nightly routine stored in the same data root (cited: DRIVER D25). Naming the run needs neither. Boundaries keeps the rule open.
- **lm_head.** B-4's exclusion of lm_head from the first runs stands (cited: ADR-0152 decision 4), and this record starts no instance for it. The whole-generation check still requires a binding for that call site (cited: ADR-0166 decision 6). The caller may name a run of the same contract, such as a bf16 `gemm` run of a projection; decision 5 is what makes that binding valid. This reading is listed for the owner in the #5 notice.

### 4. Objective

The rule compares latency, the one objective a run can state today (cited: ADR-0053 decision 4, the owner's O1). A run whose `objective` is exactly `latency_minimisation` with no constraint is taken. A valid file that states none is `no_objective`, with no value standing in (cited: ADR-0053 decision 5). A value `hilclaw.instance` refuses is `instance_invalid`. Should a later record admit another objective or a constraint, this code refuses it as `objective_unsupported` until a record gives its order. No value of the owner's was needed (#5 A-4, OD-1, C-6).

### 5. Shapes: `"every"`, from each kind's contract

ADR-0153 decision 3 accepts "every" only where the contract obliges correctness at every shape. Each contract does:

| Kind | Call sites | Obligation (cited) | `shapes` |
|---|---|---|---|
| `gemm` fp32, bf16 | `qkv`, `o`, `gate`, `up`, `down`, `lm_head` | ADR-0008 decision 6; ADR-0156 decision 7 | `"every"` |
| `rmsnorm` | `attention_norm`, `ffn_norm`, `norm` | ADR-0158 decision 7 | `"every"` |
| `elementwise_add` | `attention_residual`, `ffn_residual` | ADR-0159 decision 8 | `"every"` |
| `swiglu` | `ffn_activation` | ADR-0160 decision 8 | `"every"` |
| `rope` | `rope_q`, `rope_k` | ADR-0161 decision 11 | `"every"` |
| `sdpa_kv_cache` | `sdpa` | ADR-0162 decision 11 | `"every"` |

No kind needs more than one instance shape to be bound. **What follows for P2-15**:

- The obligation is not a verification. Whether a verification passes other values stays OD-16 sub-question 1 (cited: the same decisions). A coder's kernel that holds only at its instance's shape passes its run and fails at a generation's other shapes. Such a failure shows as `run failed` or in the model-level comparison of RA-0056, and is not detected here.
- The incumbent is the fastest at the run's own shape. The binding claims correctness at the others by contract and nothing about their speed.

### 6. Build settings: from the caller

`flags` is a required argument, as in `attempt_kernel.kernel_reference`. No landed record of a run holds them: no result of the journal carries flags, and `build.json` is not defined (cited: the docstring of `attempt_kernel`). The constant `hilclaw.standin_settings.FLAGS` is a value of the checkout at the call, and it has changed between commits (cited: ADR-0188 decision 1), so reading it here would state a fact about an older run that may be false. The caller passes the settings of the runs it names, and one call takes one set. No build-settings record is added.

### 7. A run in progress

The derivation reads what the journal holds at the call and does not read `STATE.json`. A run in progress gives its incumbent so far, and a later call may give another. It is not refused, because a run stopped before `run_over` keeps verified kernels the owner may want to use. An open timing step is no measurement (cited: ADR-0184 decision 2).

## Alternatives considered

| Alternative | Why not |
|---|---|
| The trimmed mean of ADR-0074 | Decision 2. |
| Write the choice into `best.json` | Its content is open (OD-20), and a new content is the BLOCKED reason of A-13. |
| Find the runs of a key and pick one | Decision 3. |
| Refuse a run not `over` | Decision 7. |
| Listed shapes: only the run's own shape | Every generation calls other shapes, so it would be `no_kernel` for every call site whose rows change. The contract allows more. |
| Copy the incumbent loop into the new module | Two readings of one rule could drift. |

## Consequences

- `hilclaw/model_run_binding.py` holds `binding_from_runs`. `hilclaw/spec_feedback.py` gains `incumbent`, and `feedback` behaves as before. The module reads only, starts nothing and is no tool.
- A kernel of a coder still runs only through `hilclaw/model_forward_container.py` (cited: ADR-0182 decision 7); the module hands its result to that path and does not call it.
- **Runtime acceptance items**: none new. A binding derived from real runs at the real dimensions is exercised by P2-15 (RA-0056). They go to `PROCESS/RuntimeAcceptance.md`, not to an HQ, should a later record add any (DRIVER D22).
- **UsageCases and StandardScenarios** (S0 re-checked): no step changes, no verdict changes, no gap.
- **Less exact, not edited**: the sentence of `hilclaw/model_binding.py` that it "derives no binding from a key's best (OD-20, OD-7)" stays true of that module. ADR-0153 decision 3 calls the derivation open; this record answers it for the scope of decision 1.

## Boundaries (not decided here)

- **The user-facing entry** of the executor (OD-31 sub-question 10, OD-18, OD-23, HQ-0084 ④).
- **Real weights and the tokenizer** (OD-31 sub-questions 5 and 7, HQ-0084).
- **Runs with N > 1**, and a run with no `candidates_per_round`.
- **Choosing among several runs of a key**, and several runs for one call site, one per shape (OD-6 sub-question 3).
- **The rest of OD-20**: the archive, `best_ref`, `best.json`.
- **Whether verification draws other shapes** (OD-16 sub-question 1).
- **Targets other than `cpu_standin`** (ADR-0153 Boundaries).

## References

- Owner: #5 record of 2026-10-30 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6512287389); DRIVER §6 D26, D25, D22; [Requirements](../Requirements.md) OD-20, OD-31.
- Records: [ADR-0004](ADR-0004-od8-data-plane-layout.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0028](ADR-0028-od8-instance-record-candidates-per-round.md), [ADR-0053](ADR-0053-od8-instance-record-objective.md), [ADR-0074](ADR-0074-od30-s6-metric-one-pair.md), [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md), [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md), [ADR-0160](ADR-0160-od31-bf16-swiglu-contract.md), [ADR-0161](ADR-0161-od31-bf16-rope-contract.md), [ADR-0162](ADR-0162-od31-bf16-sdpa-kv-cache-contract.md), [ADR-0166](ADR-0166-od31-bf16-forward-pass.md), [ADR-0182](ADR-0182-od14-model-executor-container.md), [ADR-0184](ADR-0184-od20-first-case-incumbent-base.md), [ADR-0188](ADR-0188-od18-standin-openmp-in-the-build-set.md).
- Code: `hilclaw/model_run_binding.py`, `hilclaw/spec_feedback.py` (`incumbent`), `hilclaw/attempt_kernel.py`, `hilclaw/model_binding.py`.
