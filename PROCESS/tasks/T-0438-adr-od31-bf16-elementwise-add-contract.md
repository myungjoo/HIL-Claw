---
id: T-0438
title: Write ADR-0159 - the operational contract of the elementwise add of the Llama residual stream in bf16 for C kernels on cpu_standin (kind value and shape members, dtype and layout, the operation and its precision, the rounding of the output conversion, the uint16_t prototype and its symbol, operand entries, call guarantees including aliasing, "every shape", the input value set, the op_signature records of the ADR-0152 add calls and the names of its two call sites), and update the OD-6, OD-31 and StandardScenarios records (third Llama kind contract of PLAN P2-11; extension of OD-6 sub-question 1, part of OD-31 sub-questions 1 to 3)
phase: P1
status: DONE
commitMode: doc
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0435, T-0437]
touchesFiles: [ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `3483beb`):
- ADR-0152 decision 2 lists six instance-target kinds for one Llama 3.2 1B forward pass. Two of them now have a bf16 contract on `cpu_standin`: GEMM (ADR-0156) and RMSNorm (ADR-0158). Their code slices have landed: `hilclaw/gemm_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, the kind `rmsnorm` in `hilclaw.keys`, and the GEMM and RMSNorm binding checks in `hilclaw/model_binding.py` (T-0430 to T-0437).
- ADR-0158 Boundaries and the planner follow-up of T-0437 name the next step: "the contracts of the other four kinds - elementwise add, SwiGLU activation, RoPE, SDPA with KV cache - one record each, and their symbol names".
- **This task writes the elementwise add record.** It is the simplest of the four. Its shapes do not depend on the head count. It has no model parameter. It is called twice per layer (ADR-0152 rows 9 and 14). The executor's full pass (ADR-0153 code slice 2) needs it like every other kind.

**What already settles part of it** (cited, not chosen here):
- The calls: rows 9 and 14 of ADR-0152 decision 2 ("Residual add after attention" and "after the feed-forward"). Their shapes are "two T × 2048 inputs; T ∈ {1, 32, 512}" (ADR-0152 decision 5, unchanged by ADR-0154 decision 1). ADR-0152 Alternatives say why the add is its own kernel and is not fused.
- The owner (HQ-0065 through ADR-0154 decision 2):
  - bf16 inputs and outputs;
  - `uint16_t` bit patterns at the kernel boundary, and the kernel converts;
  - fp32 accumulation for three named sums only, and the residual add is not one of them. ADR-0154 decision 2: "Every other intermediate precision is not settled by the answer ... Each belongs to its kind's contract record".
- The owner (HQ-0066 through ADR-0154 decision 3):
  - a float64 NumPy reference without bf16 emulation;
  - element-wise `rtol` and `atol` with no default;
  - each kind's input distribution fixed by a driver record, finite inputs only.
- ADR-0153 decision 3: a binding "for every shape" is accepted only where the contract obliges correctness at every shape. ADR-0157 decision 4: a call-site kind without a contract at the generation's dtype makes the dtype invalid input.
- ADR-0156 and ADR-0158 are the models for form and depth. ADR-0158 decision 2 already gives `row_major` its rank-1 meaning. The add needs only rank 2.

**What this record decides** is its own under DRIVER §9 (driver design, accepted by a context-isolated reviewer, owner notified on #5 with a 7-day objection window). None of it is owner-only:
- C-6 and the dtype are answered (bf16, HQ-0065).
- The oracle and tolerance vocabulary are answered (HQ-0066).
- The input distribution is given to a driver record by HQ-0066 (3).
- No value of a #5 B-4 answer changes.
- If the executor finds a point that would change an owner answer, it must not decide that point. It leaves it in Boundaries and writes the question for the driver to record as an HQ (the form of ADR-0152 Consequences). If the record cannot be written without that point, the executor stops with BLOCKED (`owner-only-decision`).

**PLAN order and D18.** P2 runs in list order. The round-loop items and P2-5 are held by unresolved HQs in `PROCESS/STATE.json`:
- HQ-0021 holds round 0's board step;
- HQ-0048 and HQ-0031 hold rounds >= 1, P2-6 and P2-7;
- the gate half of P2-4 is owner-only (OD-3);
- P2-10 comes after P2-5.

So work goes on with P2-11 to P2-14. This task is part of the P2-11 checklist item itself ("forward에 필요한 연산 종류마다 커널 계약·op_signature·하네스 검증"), and P2-14 needs it. It is not a follow-up or a wording item, so D18 does not set it aside.

**D16.** Nothing here starts `claude`, needs a board, a model file or an API key. Reading Meta's public source with `gh api` or a public URL is allowed (ADR-0158 did the same).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5: executor procedure, resume rule, time limit (line 72);
  - §5: task format, size cap and naming (lines 86-114). Here: branch `claude/T-0438-<slug>`; commit trailer `Task: T-0438`; doc mode, so no PR.
  - §9: OD closing authority and the owner notice.
- `CLAUDE.md`: "상시 규칙", especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검" and "브랜치·merge 절차" (doc mode).
- `.claude/skills/dev-item-address/SKILL.md`: steps 7 and 9 to 12 (doc mode, reviewer cycle, 7-round limit).
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`: the whole file (187 lines). It is the closest model for structure, the owner-sentence search, the open-HQ check, the cited/own split, Consequences and Boundaries.
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`: decisions 2 to 5, 7 and 9 (lines 37-128). Read decision 4 (output rounding) and decision 9 (value set) closely.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: decisions 1 to 3 (lines 31-60).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: decision 2 (lines 41-65), decision 5 (lines 84-103), decision 7 (lines 110-113), and the Alternatives row "Residual add as its own kernel" (line 125).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (lines 40-46) and decision 4 (lines 48-56).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-72).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 1 to 9 (lines 25-132).
- `ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md`: the decision.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: decision 2 (lines 37-52), decision 6 (lines 73-79) and "Record format" (lines 146-153).
- `hilclaw/keys.py` (`_SHAPE_MEMBERS`, `op_signature_key`) and `hilclaw/rmsnorm_bf16_contract.py`: how a kind's members are known and how ADR-0158 computed its directory names. Read only.
- `hilclaw/model_binding.py`: the module docstring, `CALL_SITES` and `RMSNORM_CALL_SITES`, to see how call sites are named today. Read only.
- Meta's `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py`, `TransformerBlock.forward` (the two residual adds). Read through `gh api repos/meta-llama/llama-models/contents/models/llama3/model.py?ref=0e0b8c5...` or the raw URL, and cite the line numbers you read. If neither works, cite ADR-0152 Context's account of the block and say so in Status.
- `ARCHITECTURE/Requirements.md`:
  - line 84: the register's "행 형식";
  - the OD-6 row (line 97) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - line 8: the header's "기록 규칙";
  - § OD-6 (lines 59-79);
  - § OD-31 (lines 525-544, the end of the file).
- `ARCHITECTURE/StandardScenarios.md`:
  - lines 1-29: the check rules;
  - S0 (from line 30) and S1 (from line 45);
  - § 검사 결과 (from line 168), especially its first paragraph, the recording rule, and the S0 and S1 rows of the verdict table (lines 186-187).
- `PROCESS/STATE.json`: the unresolved `humanQuestions`, for the "Open HQs checked and not crossed" bullet.

## Acceptance Criteria

1. **New file `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`** in English.
   - Follow the "Record format" of ADR-0001 and the section order of ADR-0158: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References.
   - The title names what it decides. The status is "Accepted on <date of landing>".
2. **Status** has the same parts as ADR-0158 Status:
   - the three kinds of content (owner through ADR-0154, cited, this record's own) and the §9 objection window;
   - **the owner-sentence search**: the bodies and owner comments of #4, #5, #7 and #8 (comments without the "posted by driver" marker), with the terms you used (at least: add, residual, skip connection, elementwise, element-wise, 덧셈, 잔차, bf16, bfloat16, rounding, 반올림, in-place, alias). Quote what you find and say what each quote does and does not say. Say if nothing is found;
   - **the open HQs checked and not crossed**, with the `main` commit you read. At least HQ-0033 (compiler flags; say what contraction can or cannot change for an add), HQ-0034 (OpenMP) and HQ-0069 (runtime acceptance of the model executor). Name the rest as not touched;
   - **not changed**: no data-plane schema, member, file, version or validator;
   - **answers**: which parts of OD-6 sub-question 1 and OD-31 sub-questions 1 to 3 this record answers;
   - **builds on**: list only records cited by decision number in the body.
3. **Decision** settles each of the following. Give the reason for each choice and list the alternatives you weighed in the Alternatives table:
   1. **Scope**: one contract, for the elementwise add of ADR-0152 rows 9 and 14, at dtype `bf16`, layout `row_major`, language `c`, on `cpu_standin`. Say plainly that no fp32 or fp16 contract of this kind is defined.
   2. **The `kind` value and its shape members**. The value must match `[a-z][a-z0-9_]{0,31}`. Give the members' meaning against ADR-0152's T and hidden width, and their relation to the `m`/`n` of `gemm` and `rmsnorm`. Say why the kind raises no `schema_version` (ADR-0001 decision 6).
   3. **Dtype and layout** of each operand, with the `uint16_t` element reading of ADR-0156 decision 2.
   4. **The operation and its precision**:
      - what is computed, element by element;
      - the precision in which the sum is formed. The owner's three sums do not cover it (ADR-0154 decision 2), so this record chooses it;
      - whether a binary32 add followed by the output rounding of item 5 always gives the correctly rounded bf16 sum of the two inputs, or else what the contract obliges. If you claim a result about double rounding, give its source or its argument in the record. Do not leave it as a bare assertion;
      - how the choice compares with Meta's bf16 `h = x + ...` (cite the lines). Say if this record departs from Meta's result anywhere.
   5. **The fp32 -> bf16 output rounding**: as ADR-0156 decision 4 or otherwise, with its range consequences (overflow, zero, subnormal) for the value set of item 9.
   6. **The C prototype and the symbol**:
      - the one line that is `task.contract.prototype`, byte for byte;
      - the parameter order (dimensions first, as ADR-0008 decision 4), the operand names and order, `restrict` or not;
      - the symbol, in the form of ADR-0156/ADR-0158 or with a reason to differ.
   7. **The operand entries table and the complete `task.contract`** at T = 1. Check it with `hilclaw.spec.validate` inside the committed spec example, in a throwaway interpreter that adds the kind to `hilclaw.keys._SHAPE_MEMBERS` in memory, as ADR-0158 decision 6 did. Record that check and change no repository file.
   8. **Guarantees and obligations at a call**, in the table form of ADR-0158 decision 7. It must decide:
      - **aliasing**: whether the output may be one of the inputs (an in-place residual add is natural in an executor). Weigh `restrict`, ADR-0153 decision 3's "distinct arrays for each operand" and what the pass reads afterwards (ADR-0152 decision 2). Whichever way you choose, give the reason;
      - **every set of dimensions**: whether a kernel must be correct for every shape, and so whether ADR-0153 decision 3's binding "for every shape" is accepted for this contract;
      - zero dimensions, read with ADR-0037;
      - finiteness: what is outside the guarantee.
   9. **What the kernel source provides** (ADR-0008 decision 7 with this record's symbol). Its other `hilclaw_` names include `hilclaw_gemm`, `hilclaw_gemm_bf16` and `hilclaw_rmsnorm_bf16`.
   10. **The input value set of verification** (HQ-0066 (3) gives it to a driver record):
       - which bf16 values the two inputs are drawn from, and why;
       - what the set can and cannot detect (for example a dropped operand, a swapped operand, a wrong row, a missing rounding), and what it does to the output's range. Cancellation to zero is possible when both inputs come from a set symmetric in sign. Say whether that matters for the comparison with `rtol` and `atol`;
       - what is left to the P2-12 harness record (generator, seed, draws, widening). No tolerance value or default.
   11. **The `op_signature` records**:
       - the rule, the canonical line and the sha256 at T = 1;
       - the directory names for T in {1, 32, 512}, computed with `hilclaw.keys.op_signature_key` in the same throwaway interpreter, and the method recorded;
       - that rows 9 and 14 share these records.
   12. **The two call sites' names**. Meta's code gives the residual adds no module name. Name the two calls of rows 9 and 14 for the executor's binding (as `hilclaw/model_binding.py` names `attention_norm`, `ffn_norm`, `norm` after Meta's modules). Give names, order and reason. Also give the operand that each call passes as each input, so the code slice invents nothing.
   13. **Order and runs**: no order of kinds, instance or run is chosen (as ADR-0158 decision 11).
4. **Consequences**:
   - the A-13 reading;
   - the code slice this record makes possible, for the planner, without code: the kind in `hilclaw.keys`, a contract module, the binding check with its call sites, hand-written kernel fixtures, the P2-12 harness part;
   - **less exact, not edited**: search `ARCHITECTURE/` for at least "elementwise add", "other four kinds", "other five kinds", "future contract records" and "Each kind's contract". List what you find and say you do not claim it is complete;
   - runtime acceptance items (expected: none);
   - the readings for the owner to check, listed in the #5 notice;
   - the UsageCases and StandardScenarios result (criterion 7).
5. **Boundaries**: at least fp16 and an fp32 contract of this kind; tolerance values; build settings and OpenMP (HQ-0033, HQ-0034); the harness mechanism (P2-12); corner-case, non-finite and subnormal inputs (#5 B-7, OD-16); shapes outside an instance's (OD-16 sub-question 1); how a shape set maps to instances (OD-6 sub-question 3); contract change and keys (OD-6 sub-question 4); the contracts of the other three kinds (SwiGLU activation, RoPE, SDPA with KV cache); backends other than `cpu_standin`; the weights and the model-level comparison (OD-31 sub-questions 5 and 6, owner); any change to the first case or to ADR-0156 and ADR-0158.
6. **Register and proposal edits**, each following the recording rule written in its own file (Required Reading). Do not copy the wording of earlier task files or commits for these edits:
   - `ARCHITECTURE/Requirements.md`: in the OD-6 and OD-31 rows, follow the register's "행 형식": one link to ADR-0159 with a few words of subject, added under `**확정분**:`. Rewrite `**잔여**:` in place so that the open parts it names are still true after this record (for example, the open contracts are now the kinds outside GEMM, RMSNorm and this kind). Do not restate the record and do not add a dated chain. Update the status cell's date range only if the rule asks for it.
   - `ARCHITECTURE/OpenDecisionProposals.md`: in § OD-6 and § OD-31, follow the header's "기록 규칙": one `**채택분**` line per section for ADR-0159. Rewrite in place the status at the end of each sub-question it partly answers (OD-6 ①; OD-31 ①, ②, ③) and the bullet-head status word if it changes. No dated note and no restatement of the record.
   - Do not edit any other part of these files.
7. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"): re-check S0 and S1 and every scenario row that cites OD-6 sub-question 1 or OD-31 with the rules of `ARCHITECTURE/StandardScenarios.md`. Update § 검사 결과 as its first paragraph says:
   - rewrite the "최근 재검사" line in place (date, the trigger ADR-0159 with T-0438, the result);
   - add a "판정 변화 이력" entry only if a verdict or gap changed;
   - change a verdict-table note only if an open OD part it names is no longer open, keeping only FRs and open ODs in it.
   Say the result in the ADR's Consequences.
8. **Invents nothing**: no tolerance value, no order of kinds, no change to a #5 B-4 value, no fp16, no build flag, no code. Every number in the record is either cited or computed and shown, such as the sha256 values, the value-set bounds and the double-rounding argument.
9. **Process**: doc mode (CLAUDE.md A-13).
   - Branch `claude/T-0438-<slug>`.
   - Context-isolated reviewer cycle (dev-item-address 10 to 12) until Approve, at most 7 rounds. Then rebase on `origin/main` and push to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0438`.
   - After landing, post the owner notice on #5 (DRIVER §9). It has the record link, the readings for the owner to check (criterion 4) and the 7-day objection window. Put the comment URL in `## Result`.
   - The reviewer checks at least:
     - every "cited" sentence against its source;
     - the precision and double-rounding argument;
     - the value-set bounds and what they detect;
     - the sha256 and directory names (recomputed);
     - the `task.contract` validation;
     - the aliasing and "every shape" decisions against ADR-0153 decision 3;
     - the call-site names against ADR-0152 rows 9 and 14;
     - that the register, proposal and scenario edits follow the rules written in those files;
     - that no owner-only point is decided.
10. **Size**: the four files above only, about 220 changed lines.

## Out of Scope

- Any code. This includes the kind in `hilclaw.keys`, a contract module, `hilclaw/model_binding.py`, the model program, and kernel fixtures. These are the next code slices.
- The contracts of SwiGLU activation, RoPE and SDPA with KV cache.
- The P2-12 harness mechanism, the tolerance values, and fp16.
- Editing ADR-0152, ADR-0153, ADR-0154, ADR-0156, ADR-0157 or ADR-0158. List what becomes less exact instead.
- The PLAN "보류" items, including the ADR-0158 wording follow-up of T-0435.
- `PROCESS/` files other than this task file's `## Result`, which the executor fills.

## Follow-ups

- (planner) After this record, the next piece is its code slice, in the pattern of T-0436 and T-0437: the kind in `hilclaw.keys` and a contract module, then the binding check with the two named call sites in `hilclaw/model_binding.py`. The SwiGLU activation contract record comes next after that. RoPE and SDPA with KV cache follow; both now have their shapes (ADR-0154 decision 1).

## Result
- **DONE.** Landed on `main` as `278cffcb` (doc mode, direct push; trailers `Task: T-0438` and `Reviewed-by: reviewer agent (5 rounds, Approve)`). Branch `claude/T-0438-adr-0159-bf16-elementwise-add` deleted locally and on origin.
- Files: `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md` (new), `ARCHITECTURE/Requirements.md` (OD-6 and OD-31 rows), `ARCHITECTURE/OpenDecisionProposals.md` (§ OD-6 and § OD-31), `ARCHITECTURE/StandardScenarios.md` (re-check line, S0 note); +220/-8 lines.
- Decisions: kind `elementwise_add` with members `m`, `n`; the output must be the correctly rounded bf16 sum (a binary32 or wider add plus RNE suffices, proved in the record); prototype `void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);`; no in-place call; binding for every shape accepted; value set of ADR-0156 (the output rounding is not detectable with it); directory names `elementwise_add-1af54bf2a0744c69`, `-7ca4cdf06f7c3008`, `-dd63031857ec45cd`; call sites `attention_residual`, `ffn_residual`.
- Coverage re-check: S0 and S1 re-checked, verdicts unchanged, no gap.
- Review rounds: 5 (r1 and r2 Request changes; r3 to r5 Approve; non-blocking items addressed each round).
- Owner notice (DRIVER §9): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6381155590
- Runtime acceptance items: none. HQ: none.
- Follow-ups: as listed above (code slice: kind in `hilclaw.keys`, contract module, binding check with the two call sites; then the SwiGLU activation contract record).
