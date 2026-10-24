---
id: T-0435
title: Write ADR-0158 - the operational contract of RMSNorm in bf16 for C kernels on cpu_standin (kind value and shape members, dtype and layout, the operation with fp32 sum of squares and its other intermediate precisions, eps, the rounding of the output conversion, the uint16_t prototype and its symbol, operand entries, call guarantees, the input value set, and the op_signature records of the ADR-0152 RMSNorm calls), and update the OD-6 and OD-31 register entries (second Llama kind contract of PLAN P2-11; extension of OD-6 sub-question 1, part of OD-31 sub-questions 1 to 3)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0429, T-0431, T-0434]
touchesFiles: [ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 250, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `a705146`):
- PLAN P2-11 asks for a kernel contract, op_signature and harness check for every kind of operation the Llama 3.2 1B forward pass needs. ADR-0152 lists six instance-target kinds: GEMM, RMSNorm, RoPE, SDPA with KV cache, SwiGLU activation and elementwise add. It says each gets its own contract record (its Boundaries, "Each kind's contract").
- The owner answered the precision and oracle questions (HQ-0065, HQ-0066, recorded in ADR-0154): bf16 only; inputs and outputs bf16; fp32 accumulation for the GEMM dot product, **the RMSNorm sum of squares** and the softmax sum; `uint16_t` bit patterns at the kernel boundary, with the kernel converting; a float64 NumPy reference; element-wise `rtol`/`atol` with no default; and each kind's input distribution fixed by a driver record, finite inputs only.
- The only bf16 contract so far is GEMM (ADR-0156, T-0429). Its code is landed (T-0430 to T-0434). ADR-0157's code slices are done, so the executor's GEMM path runs a bf16 generation end to end.
- T-0434's planner follow-up names the next P2-13/P2-14 step: ADR-0153 code slice 2, the forward pass. That step needs bf16 contracts for the other five kinds. ADR-0157 decision 4 makes `bf16` an invalid model dtype while any call-site kind lacks a bf16 contract record. None of the five has one: a search of `ARCHITECTURE/decisions/` finds no RMSNorm, RoPE, SDPA, SwiGLU or elementwise-add contract.

**Why RMSNorm next** (the planner's choice; ADR-0152 Boundaries leave "the order in which kinds are taken up after `gemm`" open, beyond B-4's "GEMM first, then the attention family"):
- B-4's sentence orders the **instances and runs**. This task writes a contract record. It decides no instance, run or order of runs, and the record must say so. The forward pass of P2-14 needs all five records whatever their order.
- RMSNorm is the first non-GEMM operation of the pass (ADR-0152 decision 2, rows 2, 10 and 15). Its shape set is settled and does not depend on the head count (ADR-0152 decision 5). It is one of the three sums the owner named.
- It is the first kind that `hilclaw.keys` does not know. So it is the first record to name a new `kind` value and its `shape` members (ADR-0001 decisions 2 and 6). It sets the pattern that the other row-wise kinds (elementwise add, SwiGLU activation) can follow with less review. RoPE and SDPA also carry layout questions about Q, K, V and the cache.

**D18.** P2-11 is a PLAN checklist item, and a contract per kind is inside its completion text, so the priority rule does not apply. It is also needed for P2-14 (ADR-0157 decision 4, above).

**DRIVER §9.** This is design-level OD work (OD-6 sub-question 1 extended; OD-31 sub-questions 1 to 3, driver parts), closed by an ADR, reviewer Approve and a #5 notice. Owner-only parts stay with the owner. These are fp16, tolerance values, corner-case and non-finite inputs (#5 B-7), weights (OD-31 ⑤) and the model-level comparison (⑥). The record must not decide them.

**D16.** Nothing here starts `claude` or needs a board, a model file or an API key. Meta's public reference code is read at a pinned commit, as ADR-0152 did.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0435-<slug>`, commit trailer `Task: T-0435`; size cap; lines 86-114);
  - §8 (lines 136-142) and §9 (OD closure by ADR, owner-only parts, 7-day notice; lines 144-151).
- `CLAUDE.md`: "상시 규칙", especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`, the whole record (207 lines). It is the model for structure, Status content and the kind of decisions a contract makes. Do not copy its wording where the reasons differ.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: Status (lines 3-19), decisions 2 and 3 (lines 45-60), Boundaries (lines 87-95).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: Status "Meta's reference" bullet (lines 21-23), decision 1 (lines 33-39), decision 2 table (lines 41-65), decision 3 bullet on RMSNorm's weight multiply (line 73), decision 5 (lines 84-103), decision 7 (lines 110-113), Boundaries (lines 150-160).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (lines 40-46, inputs incl. `eps` as a model parameter, binding, fit, "every shape", the call) and decision 5 (lines 58-62).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-71).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 1 to 8 (lines 25-112), for the parts a new contract restates or cites.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: decisions 2, 3 and 6 (lines 37-62, 73-78) and "Record format" (line 146 on).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: decisions 3 and 4 (lines 38-56).
- `ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md` (zero dimensions; whether its reading carries over).
- Meta, `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`:
  - `models/llama3/model.py`, class `RMSNorm` (lines 31-42). `forward` normalises `x.float()`, casts the result back to `x`'s dtype with `type_as`, then multiplies by `weight`;
  - `models/sku_list.py` lines 327-346 (`norm_eps` 1e-05).
  - Read with `gh api "repos/meta-llama/llama-models/contents/<path>?ref=<commit>" -H "Accept: application/vnd.github.raw"`.
- Code, read only: `hilclaw/keys.py` (`_SHAPE_MEMBERS`, `op_signature_key`, the name pattern), `hilclaw/spec.py` (`validate`, the `task.contract` checks), `hilclaw/gemm_bf16_contract.py` (how ADR-0156 became code).
- Register files and their recording rules:
  - `ARCHITECTURE/Requirements.md`: "행 형식" (line 84); rows OD-6 (line 97) and OD-31 (line 122);
  - `ARCHITECTURE/OpenDecisionProposals.md`: header "기록 규칙" (line 8); § OD-6 (line 59 on) and § OD-31 (line 524 on);
  - `ARCHITECTURE/StandardScenarios.md`: the check rules, and the first paragraph of § 검사 결과 (lines 168-172).
- `PROCESS/STATE.json` `humanQuestions`: the unresolved ones, to list which open HQs this record does not cross. These include HQ-0033 (build flags, `-ffp-contract`), HQ-0034 (OpenMP) and HQ-0069.

## Acceptance Criteria

1. **New file `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`** in the format of ADR-0001 "Record format". First check that ADR-0158 is still free on `origin/main`. If it is not, take the next free number, use it everywhere and record that in `## Result`.
2. **Status** separates three kinds of content, as ADR-0156 does:
   - owner answers (HQ-0065, HQ-0066 through ADR-0154), marked owner and not subject to the objection window;
   - statements of accepted records and of Meta's code, cited;
   - the record's own content, accepted under DRIVER §9: written by the executor, approved by a context-isolated reviewer, with a 7-day objection window after the #5 notice.

   Status also holds:
   - **An owner-sentence search** of issues #4, #5, #7 and #8 for terms such as RMSNorm, norm, eps, rsqrt, 정규화, normalization, bf16, rounding. List what was found, or say nothing was found. If a found owner sentence conflicts with a choice of this record on an owner-only value, stop and return BLOCKED (`requirement-unclear`).
   - The open HQs checked and not crossed.
   - What is not changed (A-13 reading, criterion 4).
   - What the record answers of OD-6 ① and OD-31 ①, ② and ③.
3. **Decisions.** Each point gets a choice with its reasons, or an explicit "not decided here" with where it goes:
   - **Scope**: one contract, RMSNorm with dtype `bf16`, layout `row_major` and language `c`, on `cpu_standin`. No fp32 or fp16 RMSNorm contract is defined.
   - **`kind` value and `shape` members** (ADR-0001 decision 2: member names fixed per kind). Check them against the name pattern of `hilclaw.keys`. Say how T and the feature width map onto the members. State that, by ADR-0001 decision 6, a new kind with its shape members raises no `schema_version`.
   - **Layout `row_major`** for this kind's operands, with each element a `uint16_t` bf16 pattern. Read ADR-0156 decision 2 for what "the C type of its dtype" means.
   - **The operation**, from Meta's `RMSNorm`: y(i, j) = x(i, j) · w(j) / sqrt(mean over j of x(i, j)² + eps). Cover:
     - **The sum of squares in fp32**, as owner (HQ-0065 (2)). Say what that obliges, as ADR-0156 decision 3 does for the dot product: accumulator width, addition order, fused steps.
     - **Every other intermediate step**, whose precision the owner did not settle (ADR-0154 decision 2): the mean, the addition of eps, the reciprocal square root, the scaling of x, and the multiply by w. Say also whether the normalised value is rounded to bf16 before the weight multiply, as Meta's `type_as` does, or not. Choose and give reasons, or leave a step to the kernel and say why. Where the choice departs from Meta's order of roundings, state the departure.
   - **eps**: its value (1e-05, cited from Meta and ADR-0152) and where it lives. One of: a constant of the contract, a key field (`ext` of the op_signature), or a kernel parameter in the prototype. Give reasons. Note that ADR-0153 decision 3 lists `eps` among the executor's model parameters.
   - **The fp32 → bf16 conversion of the output**: fix the rounding or leave it to the kernel, with reasons. If ADR-0156 decision 4's reasons carry over, cite them rather than restate them. Cover overflow, and say whether a non-finite or subnormal result can arise for the inputs of the input-value-set point.
   - **C prototype and symbol**: one exact line that is the text of `task.contract.prototype`. Give the parameter order and types (`size_t` dimensions, `const uint16_t *restrict` inputs, `uint16_t *restrict` output, unless reasoned otherwise) and the symbol name with reasons. ADR-0156 decision 5 set no naming rule for other kinds.
   - **Operand entries**: a table (`name`, `role`, `dtype`, `shape`, parameter) and one complete `task.contract` JSON example for one shape. `hilclaw.spec.validate` refuses an op_signature of a kind `hilclaw.keys` does not know. So either validate the example with the kind added in memory, in a throwaway interpreter with no repository change, and say so, or say it was not validated.
   - **Guarantees and obligations at a call**, as a table like ADR-0156 decision 7. Cover:
     - dimensions (at least 1, or reasoned otherwise; whether ADR-0037's reading carries over);
     - overlap, including whether in-place use (y = x) is allowed;
     - inputs, output, alignment, memory, repeated calls, completion and result.
   - **Every shape**: whether a kernel must be correct for every set of dimensions. ADR-0153 decision 3 leaves to each kind's record whether a binding "for every shape" is accepted.
   - **What the kernel source provides**, as ADR-0008 decision 7 and ADR-0156 decision 8 (one definition, no `main`, the reserved prefix).
   - **The input value set of verification** for x and for w: finite only (owner, HQ-0066 (3)). Give reasons for the range of each, as ADR-0156 decision 9 does: no overflow of the fp32 sum of squares, a dropped or doubled term detectable in principle, and no zero or subnormal values unless reasoned. Leave the generator, seed, number of draws and widening to the P2-12 harness record. **Choose no tolerance value** (owner, no default).
   - **The `op_signature` records** for the ADR-0152 RMSNorm calls: T ∈ {1, 32, 512}, width 2048 (ADR-0152 decision 5). Give the canonical record of each. Directory names are optional. If given, compute them with `hilclaw.keys.op_signature_key` with the kind added in memory (no repository change), state that method, and check the method on one fp32 `gemm` control name from ADR-0008 decision 9. Say that how a shape set maps to instances stays OD-6 sub-question 3.
   - **Order and runs**: one sentence that this record chooses no order of kinds, no instance and no run (ADR-0152 Boundaries; B-4's run order stands).
4. **A-13 reading** (Consequences): no schema file, member, file, version or validator of the data plane changes, and `hilclaw/` is not touched. The new `kind` value and its shape members are values that ADR-0001 decision 6 admits without a version change. Teaching `hilclaw.keys` the kind is a code slice for later. If the executor or reviewer finds that the record needs a change of the data-plane schema beyond that, stop and return BLOCKED (A-13 schema change).
5. **Consequences** also list:
   - **The code slice this record makes possible**, for the planner, with no code here: the kind in `hilclaw.keys`, a contract module like `hilclaw/gemm_bf16_contract.py`, fit in `hilclaw/model_binding.py`, hand-written bf16 RMSNorm kernel fixtures, and the P2-12 harness part.
   - **"Less exact, not edited"**: found by a search of `ARCHITECTURE/` for RMSNorm, `future contract records`, `other five kinds` and the like. Say it is not claimed complete.
   - Runtime acceptance items (expected: none).
   - Readings for the owner to check, which go into the #5 notice.
   - The UsageCases and StandardScenarios re-check result.
6. **Alternatives considered**: at least the eps placement, the rounding before the weight multiply, the symbol name, in-place use and the input range.
7. **Boundaries** include at least:
   - fp16 (owner, after P2-14);
   - tolerance values;
   - build settings and OpenMP (HQ-0033, HQ-0034);
   - the harness mechanism (P2-12);
   - corner-case, non-finite and subnormal inputs (#5 B-7, OD-16);
   - shapes outside an instance's (OD-16 ①);
   - how a shape set maps to instances (OD-6 ③);
   - contract change and keys (OD-6 ④);
   - the contracts of the other four kinds;
   - backends other than `cpu_standin`;
   - the weights and their conversion (OD-31 ⑤, owner);
   - any change to the first case or to ADR-0156.
8. **`ARCHITECTURE/Requirements.md`**: edit only the OD-6 and OD-31 rows, following that file's "행 형식" (line 84).
9. **`ARCHITECTURE/OpenDecisionProposals.md`**: edit only § OD-6 and § OD-31, following that file's header "기록 규칙" (line 8). Leave the opening paragraph of § OD-31 (owner text) unchanged.
10. **`ARCHITECTURE/StandardScenarios.md`**: re-check S0 and S1, and any scenario whose row cites OD-6 ① or OD-31, by the file's check rules (CLAUDE.md "문서 커버리지 재검사"). Record the result as the first paragraph of § 검사 결과 prescribes.
11. **Size**: the ADR stays within the DRIVER §5 cap together with the register edits (≤ 300 changed lines). If it cannot, cut restatement of ADR-0156 and ADR-0008 in favour of citation before cutting decisions. If it still cannot, propose a split in `## Follow-ups` and finish the current scope.
12. **No other file changes.** In particular, do not edit:
    - `PROCESS/PLAN.md` or `PROCESS/STATE.json`;
    - ADR-0001, ADR-0008, ADR-0017, ADR-0152, ADR-0153, ADR-0154, ADR-0156 or ADR-0157;
    - any `hilclaw/` file, test, C file or catalog file.
13. **Process**: document mode (CLAUDE.md A-13).
    - Pass the context-isolated reviewer cycle (dev-item-address steps 10-12) to Approve.
    - Then rebase on `origin/main` and push to `main` directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0435`.
    - The reviewer checks at least:
      - that the owner answers are cited without change of meaning, and nothing beyond them is presented as the owner's;
      - that Meta's `RMSNorm` is cited correctly at the pinned commit;
      - that no tolerance value, build flag or OpenMP setting is chosen;
      - that the prototype text is exact;
      - that the record chooses no order of kinds, instance or run;
      - that the three register edits follow the recording rules of their own files.
    - Post the DRIVER §9 owner notice on issue #5 after landing, ending with `— posted by driver`, and record its URL in `## Result`. If posting fails, put the notice text in `## Result` and say so.

## Out of Scope

- Any code: `hilclaw.keys`, a contract module, `model_binding`, kernels, the harness (later tasks).
- The contracts of RoPE, SDPA with KV cache, SwiGLU activation and elementwise add.
- fp16, tolerance values, corner-case and non-finite inputs, weights, model-level comparison (owner).
- Editing #5 comments or earlier ADRs. List those as less exact instead.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this lands, the code slice of ADR-0158 (criterion 5) can be planned as a code task. The contract records of elementwise add, SwiGLU activation, RoPE and SDPA with KV cache follow, one ADR task each. Any part that touches owner-only sub-questions goes to an HQ instead.

## Result
