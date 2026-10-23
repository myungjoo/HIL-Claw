---
id: T-0423
title: Write ADR-0154 - record the owner's answers HQ-0064 (32 query heads, 8 KV heads, head_dim 64), HQ-0065 (bf16 only, fp32 accumulation, uint16_t bit patterns at the kernel boundary) and HQ-0066 (float64 reference on widened inputs, per-instance rtol/atol with no default, per-kind input distribution by driver record) as the frame of the Llama 3.2 1B kind contracts, and update the OD-31 register entries (OD-31 sub-questions 1, 2 and 3; for PLAN P2-11 and P2-12)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-9, OD-31, OD-6, "#5 B-4", "#5 B-7", "PLAN P2-11", "PLAN P2-12"]
dependsOn: [T-0417, T-0418]
touchesFiles: [ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `627fb3b`):
- PLAN P2-5 (the near goal) still cannot move: each remaining part waits on an open owner HQ (HQ-0048, HQ-0021, HQ-0026). P2-10 comes after P2-5.
- PLAN P2-11 (one contract per Llama kind) and P2-12 (the bf16/fp16 harness) were waiting on three owner HQs. **The owner answered all three on 2026-10-24** (chat, recorded in `PROCESS/STATE.json` by commit `eafce0a`):
  - **HQ-0064** (a): 32 query heads, 8 KV heads, head_dim 64. #5 B-4's "16 heads" and "GQA 16/8" are corrected to 32 and 32/8. ADR-0152 gets the substitution H = 32, d_h = 64.
  - **HQ-0065**: (1) (a) bf16 only; fp16 is put off until after the Llama 3.2 1B end-to-end (P2-14). (2) (a) inputs and outputs are bf16; accumulation is fp32 (GEMM dot product, RMSNorm sum of squares, softmax sum). (3) (a) the kernel boundary carries 16-bit bit patterns (`uint16_t`); the kernel does the conversion.
  - **HQ-0066**: (1) (a) the reference widens the inputs to float64 and computes in NumPy float64, with no new dependency. (2) (a) every kind uses element-wise rtol and atol, which are instance parameters with no default. (3) (a) a driver record fixes the input distribution of each kind (finite inputs only).
- These answers exist only in `PROCESS/STATE.json`. The architecture documents still show them as open:
  - the OD-31 register row lists "①의 query head 수" as remaining;
  - OpenDecisionProposals § OD-31 marks sub-questions ② and ③ as `미결`;
  - ADR-0152 decision 6 says "Not decided";
  - ADR-0153 Status lists the head count, dtype and oracle as open.
  
  Every P2-11 contract record and the P2-12 harness must cite these answers. The record they cite must exist first. Under the convention of this repository an accepted ADR is not edited; a later record restates what it amends (e.g. ADR-0056, ADR-0078).
- **Priority (DRIVER §6, D18)**: P2-11 and P2-12 are PLAN checklist items, and this record is their first step. PLAN P2 lists P2-11 before P2-13.
- **Not taken now**: the joining task of ADR-0153 code slice 1 (run `hilclaw.model_binding.check`, then hand `BindingCheck.calls` to `hilclaw.model_execute`). It is the follow-up of T-0422, now unblocked by T-0419. It is not set aside; it is the candidate after this task.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0423-<slug>`, commit trailer `Task: T-0423`; lines 86-114);
  - §8 (HQ form; lines 136-142);
  - §9 (OD closure by ADR, owner-only parts, 7-day notice; lines 144-151).
- `CLAUDE.md`: "상시 규칙" (three-layer model, "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분", document mode of A-13) and "현재 프로젝트 상태 주의사항".
- `PROCESS/STATE.json` `humanQuestions`:
  - HQ-0064, HQ-0065 and HQ-0066: the `question` and the `decision` of each. These are the sources this record cites. Quote the `decision` text exactly.
  - Also check every unresolved HQ, and say in Status that the record crosses none of them.
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`, whole file (167 lines). Read especially:
  - Status (the owner-sentence search, the form of "cited" vs "this record's own");
  - decision 5 and its shape table (lines 84-104): the RoPE and SDPA rows are written over H and d_h;
  - decision 6 (the head count);
  - Consequences (the HQ-0064 text, "The planner's next steps under P2-11");
  - Boundaries.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Status (lines 3-15), decision 3 (lines 40-47), decision 6 (lines 64-69), Boundaries (lines 101-116).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decision 1 (another dtype has its own contract), decision 4 (the C prototype), decision 6, Boundaries.
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: how the fp32 `gemm` reference, tolerance and input distribution of the first case are set. This is the precedent HQ-0066 (3) names ("ADR-0017처럼 유한 입력만").
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` "Record format" (from line 146): the sections and naming of an ADR.
- `ARCHITECTURE/Requirements.md`:
  - C-6 (line 63);
  - FR-9 (verification and tolerance);
  - the **"행 형식" paragraph (line 84)**: the recording rule for the register row;
  - OD-6 and OD-31 (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's **"기록 규칙" (line 8)**: the recording rule for a proposal section;
  - § OD-31 (from line 521, about 15 lines).
- `ARCHITECTURE/StandardScenarios.md`:
  - S0 and S1, and their rows of the verdict table (lines 186-187);
  - **the first paragraph of § 검사 결과 (line 170)**: the recording rule for a re-check, and the "최근 재검사" line (line 172).
- `PROCESS/PLAN.md` P2-11 to P2-14 (lines 47-50). Read only; do not edit.

## Acceptance Criteria

1. **New record** `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`, in English, in the ADR-0001 "Record format":
   - sections Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References.
   - Status says what is the owner's and what is the record's own:
     - The **owner's answers are cited** from `PROCESS/STATE.json` (HQ ids, commit `eafce0a`, chat of 2026-10-24) and are not subject to the DRIVER §9 objection window.
     - Any **reading or consequence that is the record's own** is accepted under §9 (written by the executor, approved by a context-isolated reviewer, 7-day objection window after the #5 notice).
   - Status also states:
     - that no member, file, kind value, `op_signature` member or version of the data plane is added or changed;
     - that no `claude` process was started and no model file was downloaded (D16);
     - which unresolved HQs were checked and not crossed.
   - Status includes an owner-sentence search, as ADR-0152's does: issues #4, #5, #7, #8, for terms such as bf16, fp16, 정밀도, accumulation, 누적, tolerance, rtol, atol, oracle, reference, heads, GQA. It lists what was found, or says nothing was found. Any found owner sentence that conflicts with the HQ answers is named, and the record says which one it follows and why. If the conflict touches an owner-only value, the executor stops and returns BLOCKED (`requirement-unclear`).
2. **Head count** (HQ-0064):
   - The record restates the RoPE and SDPA rows of ADR-0152 decision 5 with H = 32, KV heads = 8, d_h = 64 substituted. Every other value and set stays as ADR-0152 has it. ADR-0152 is not edited; a sentence names the restated rows as amending it.
   - It cites the owner's correction of #5 B-4's "16 heads" and "GQA 16/8" to 32 and 32/8. It does not edit the #5 comment.
   - It notes that ADR-0152's GEMM shapes are unchanged (they already equal H = 32, d_h = 64).
3. **Precision** (HQ-0065):
   - The **dtype of the Llama goal is bf16**. fp16 is later, after PLAN P2-14, as the owner put it. The first case (fp32 `gemm`, ADR-0008, PLAN P1-5) is unchanged.
   - **Inputs and outputs are bf16; accumulation is fp32** for exactly the three sums the owner named: the GEMM dot product, the RMSNorm sum of squares and the softmax sum.
     - The precision of every other intermediate value is not settled by the answer. Examples are RoPE's angles and sin/cos, SwiGLU's SiLU, the SDPA score scale, and the cast between the score and value products.
     - The record says so and leaves each one to its kind's contract record (a design part, driver, OD-6 sub-question 1). It does not choose them.
   - **On `cpu_standin`, a bf16 value crosses the kernel boundary as its 16-bit pattern in `uint16_t`, and the kernel converts.**
     - The rounding of the kernel's fp32 → bf16 conversion is not stated by the owner. Neither is whether it belongs to the contract or to the kernel. The record leaves this to the contract records and names it in Boundaries.
4. **Oracle, tolerance, inputs** (HQ-0066):
   - The reference widens each bf16 input to float64 and computes in NumPy float64. It does not emulate bf16 rounding. No new dependency is added (no `ml_dtypes`, no PyTorch).
   - Every kind compares element-wise with `rtol` and `atol`, which are instance parameters with no default. This extends the HQ-0004 answer of the first case to every Llama kind.
   - **Each kind's input distribution is fixed by a driver record**, which is that kind's contract record or harness record, with finite inputs only, after ADR-0017. This record fixes no distribution.
   - The record may state one consequence as its own reading, marked as such. bf16 → float64 widening of inputs and outputs is exact, so the comparison of a bf16 output against the float64 reference loses nothing beyond the bf16 rounding the tolerance must allow. It must not choose tolerance values.
5. **Consequences** include:
   - **What is now unblocked**: per-kind contract records under P2-11 (GEMM in bf16, RMSNorm, elementwise add, SwiGLU activation, RoPE, SDPA with KV cache), and P2-12's harness. It does **not** choose the order of the contracts or whether bf16 projections are `gemm` with another dtype or another kind. Both stay in Boundaries (ADR-0152 Boundaries).
   - **Less exact, not edited**: list what this record makes less exact without editing it. At least:
     - C-6 row "정밀도는 bf16/fp16" (the owner's text, kept);
     - ADR-0152 decision 6 and its Consequences;
     - ADR-0153 Status "Open HQs checked" and Boundaries on dtype, oracle and head count;
     - the opening paragraph of OpenDecisionProposals § OD-31 (owner text);
     - PLAN P2-12 "bf16/fp16".
     
     Search `ARCHITECTURE/` and `PROCESS/PLAN.md` for `bf16/fp16`, `head count`, `16 heads` and `GQA 16/8`, and do not claim the list is complete.
   - **Runtime acceptance items**: none expected. If one appears, write it in the DRIVER §8 form for the driver to record (reason `runtime-acceptance`).
6. **Boundaries** name, each with its owner or OD:
   - each kind's contract (OD-6 sub-question 1, driver), including its intermediate precisions, conversion rounding, input distribution and layout;
   - the timing of fp16 (owner, after P2-14);
   - tolerance values (instance parameters);
   - OD-31 sub-questions 4 (its open parts) and 5 to 10;
   - how a shape set maps to instances (OD-6 sub-question 3);
   - any change to the first case.
7. **`ARCHITECTURE/Requirements.md`**: only the OD-31 row (line 122) changes, following the "행 형식" paragraph of that file:
   - Add this record as **one link** in the confirmed part. Mark the owner-answered content in the way that paragraph prescribes for what the owner confirmed directly.
   - Rewrite `**잔여**:` in place, dropping the head count and the parts of sub-questions ② and ③ that the answers closed.
   - Do not restate what ADR-0154 says, and add no dated paragraph.
   - Change the status cell only as that paragraph allows.
   - Do not edit C-6.
8. **`ARCHITECTURE/OpenDecisionProposals.md`**: only § OD-31 changes, following that file's header "기록 규칙":
   - Add one `**채택분**` line for ADR-0154.
   - Rewrite in place the end-of-question status of sub-questions ①, ② and ③, and the state word at the head of each bullet, so that each shows what is left. Keep the question wording.
   - No dated note and no restatement of the record.
   - Do not edit the section's opening paragraph (owner text).
9. **`ARCHITECTURE/StandardScenarios.md`**: re-check S0 and S1 (and any scenario whose row cites OD-31) by the check rules, and record the result as the first paragraph of § 검사 결과 prescribes:
   - Update the "최근 재검사" line in place.
   - Add a "판정 변화 이력" entry only if a verdict changes or a gap appears or is closed.
   - In a verdict-table note, change only the open OD references that this record closes (e.g. S1's "첫 사례 밖의 어휘 #5 B-7·OD-31 ③" if its vocabulary part is now answered). Keep anything still open.
10. **No other file changes.** In particular, do not edit:
    - `PROCESS/PLAN.md` or `PROCESS/STATE.json`;
    - ADR-0152 or ADR-0153;
    - any `hilclaw/` file;
    - any test.
11. **Process**: document mode (CLAUDE.md A-13).
    - Pass the context-isolated reviewer cycle (dev-item-address steps 10-12) to Approve.
    - Then rebase on `origin/main` and push to `main` directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0423`.
    - The reviewer checks, at least:
      - that every owner answer is quoted from `PROCESS/STATE.json` without change of meaning;
      - that nothing beyond the answers is presented as the owner's;
      - that no intermediate precision, rounding, distribution or tolerance value is chosen;
      - that the three register edits follow the recording rules of their files.

## Out of Scope

- Any kind contract (bf16 `gemm`, RMSNorm, RoPE, SDPA, SwiGLU activation, elementwise add): one later record per kind under P2-11.
- The P2-12 harness code, and any change to `hilclaw/`.
- Editing #5 comments, including the B-4 answer. Posting the DRIVER §9 notice on #5 is the driver's.
- fp16 in any form.
- The joining task of ADR-0153 code slice 1 (the binding check feeding `model_execute`), and runtime acceptance item (lxvii) of ADR-0153.
- OD-31 sub-questions 5 to 10, the PLAN P2-5 work and the PLAN hold list.

## Follow-ups

- Candidate next task (P2-13, code): join `hilclaw.model_binding.check` with `hilclaw.model_execute.execute`, so that an ok `BindingCheck` gives the kernel list and call indices of `execute` (T-0422 Follow-ups). After it lands, the driver asks runtime acceptance item (lxvii) of ADR-0153 as an HQ (reason `runtime-acceptance`).
- Then under P2-11: the first bf16 kind contract record, in an order the planner chooses and states in that task's Why.

## Result

- DONE, document mode. Landed on `main` as one commit with `Reviewed-by: reviewer agent (5 rounds, Approve)` and `Task: T-0423` (the commit that carries this Result).
- Files: new `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`; the OD-31 row of `ARCHITECTURE/Requirements.md`; § OD-31 of `ARCHITECTURE/OpenDecisionProposals.md` (adopted line, sub-questions 1-3 statuses); `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line, S0 and S1 notes scoped to the Llama kinds on `cpu_standin`).
- Review: 5 rounds (round 1 Approve with Low/Nit, round 2 Approve with Low/Nit, round 3 Request changes on one Medium (③ kept among the owner-only parts), rounds 4 and 5 Approve); every point addressed on the branch.
- Owner-sentence search (#4, #5, #7, #8): no conflict touching an owner-only value; K1 "16 heads"/"GQA 16/8" and K2 "bf16/fp16" are followed as corrected or narrowed by HQ-0064 and HQ-0065.
- StandardScenarios: S0 and S1 re-checked, verdicts unchanged, no gap.
- Runtime acceptance items: none. New HQ: none.
- The DRIVER §9 owner notice on issue #5 is posted by the executor after landing, at the driver's instruction; its URL is in the executor's summary.
- Follow-ups: as listed above (the ADR-0153 slice 1 joining task; then the first bf16 kind contract record under P2-11).
