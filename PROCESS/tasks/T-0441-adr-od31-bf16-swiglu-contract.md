---
id: T-0441
title: Write ADR-0160 - the operational contract of the SwiGLU activation of the Llama feed-forward in bf16 for C kernels on cpu_standin (kind value and shape members, dtype and layout, the operation and the precision of its SiLU and product, the rounding of the output conversion, the uint16_t prototype and its symbol, operand entries, call guarantees, "every shape", the input value set, the op_signature records of the ADR-0152 row 12 calls and the name of its call site), and update the OD-6, OD-31 and StandardScenarios records (fourth Llama kind contract of PLAN P2-11; extension of OD-6 sub-question 1, part of OD-31 sub-questions 1 to 3)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0438, T-0440]
touchesFiles: [ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `d119254`):
- ADR-0152 decision 2 lists six instance-target kinds for one Llama 3.2 1B forward pass. Three have a bf16 contract on `cpu_standin`: GEMM (ADR-0156), RMSNorm (ADR-0158) and elementwise add (ADR-0159). The code slices of all three have landed: their contract modules under `hilclaw/`, their kinds in `hilclaw.keys`, and their binding checks in `hilclaw/model_binding.py` (T-0430 to T-0440).
- ADR-0159 Boundaries and the planner follow-ups of T-0438 and T-0440 name the next step: the contracts of the other three kinds (SwiGLU activation, RoPE, SDPA with KV cache), one record each.
- **This task writes the SwiGLU activation record.** Its shapes do not depend on the head count (ADR-0152 decision 5: "two T × 8192 inputs (gate, up) → T × 8192; T ∈ {1, 32, 512}", "No" in the head-count column). It has no model parameter. It is called once per layer (row 12). RoPE and SDPA are larger and come after it.

**What already settles part of it** (cited, not chosen here):
- The call: row 12 of ADR-0152 decision 2, "SwiGLU activation: silu(gate) · up, elementwise", between the gate and up projections (row 11, two GEMM calls `gate` and `up` in `hilclaw/model_binding.py`) and the down projection (row 13). ADR-0152's Alternatives row "SwiGLU activation as its own kernel" says why it is not a GEMM epilogue.
- The owner (HQ-0065 through ADR-0154 decision 2): bf16 inputs and outputs; `uint16_t` bit patterns at the kernel boundary with the kernel converting; fp32 accumulation for three named sums only. ADR-0154 decision 2 names "the SiLU of the SwiGLU activation" as an intermediate precision the answer does not settle, and says "Each belongs to its kind's contract record". So the precision of the SiLU, of its exponential and of the product is this record's to choose.
- The owner (HQ-0066 through ADR-0154 decision 3): a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; each kind's input distribution fixed by a driver record, finite inputs only.
- ADR-0153 decision 3: a binding "for every shape" is accepted only where the contract obliges correctness at every shape; "distinct arrays for each operand". ADR-0157 decision 4: a call-site kind without a contract at the generation's dtype makes the dtype invalid input.
- ADR-0158 and ADR-0159 are the models for form and depth. One difference matters here: SiLU uses an exponential, so a correctly rounded result (as ADR-0159 decision 4 obliges for the add) may not be cheap or even practical. The record must weigh this openly and choose an obligation it can justify (see criterion 3.4).

**What this record decides** is its own under DRIVER §9 (driver design, accepted by a context-isolated reviewer, owner notified on #5 with a 7-day objection window). None of it is owner-only: the dtype (HQ-0065), the oracle and tolerance vocabulary (HQ-0066) and the input distribution (given to a driver record by HQ-0066 (3)) are answered, and no value of a #5 B-4 answer changes. If the executor finds a point that would change an owner answer, it must not decide it: it leaves it in Boundaries and writes the question for the driver to record as an HQ. If the record cannot be written without that point, the executor stops with BLOCKED (`owner-only-decision`).

**PLAN order and D18.** P2 runs in list order. The round-loop items and P2-5 are held by unresolved HQs in `PROCESS/STATE.json` (HQ-0021 for round 0's board step; HQ-0048 and HQ-0031 for rounds >= 1, P2-6 and P2-7; the gate half of P2-4 is owner-only, OD-3), and P2-10 comes after P2-5. So work goes on with P2-11 to P2-14. This task is part of the P2-11 checklist item itself ("forward에 필요한 연산 종류마다 커널 계약·op_signature·하네스 검증"), and P2-14 needs it, so D18 does not set it aside.

**D16.** Nothing here starts `claude`, needs a board, a model file or an API key. Reading Meta's public source with `gh api` or a public URL is allowed (ADR-0158 and ADR-0159 did the same). Throwaway interpreter checks that change no repository file are allowed.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5: executor procedure, resume rule, time limit (line 72);
  - §5: task format, size cap and naming (lines 86-114). Here: branch `claude/T-0441-<slug>`; commit trailer `Task: T-0441`; doc mode, so no PR.
  - §9: OD closing authority and the owner notice (lines 144-152).
- `CLAUDE.md`: "상시 규칙", especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검" and "브랜치·merge 절차" (doc mode).
- `.claude/skills/dev-item-address/SKILL.md`: steps 7 and 9 to 12 (doc mode, reviewer cycle, 7-round limit).
- `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`: the whole file (210 lines). It is the closest model for structure, the owner-sentence search, the open-HQ check, the cited/own split, Consequences and Boundaries. Read decision 4 (the obligation on the result and its argument), decision 8 (no in-place call), decision 10 (value set and what it detects) and decision 12 (call sites and operand table) closely.
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`: decision 3 (lines 44-51; binary32 or wider intermediates without a result obligation, and a stated departure from Meta's order of roundings), decision 4 (lines 52-56) and decision 9 (lines 116-122).
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`: decisions 2, 4, 5 and 9 (lines 37-42, 52-73, 121-128).
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: decisions 2 and 3 (lines 45-60).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: Context (lines 17-28, the FFN hidden size at line 26), decision 2 (lines 41-65, row 12), decision 5 (lines 84-103, the SwiGLU row at line 97), decision 7 (lines 110-113) and the Alternatives row at line 121.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (lines 40-46) and decision 4 (lines 48-56).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-72).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 1 to 9 (lines 25-132).
- `ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md`: the decision.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: decision 2 (lines 37-52), decision 6 (lines 73-79) and "Record format" (lines 146-153).
- `hilclaw/keys.py` (`_SHAPE_MEMBERS`, `op_signature_key`) and `hilclaw/elementwise_add_bf16_contract.py`: how a kind's members are known and how ADR-0159 computed its directory names. Read only.
- `hilclaw/model_binding.py`: the module docstring and `CALL_SITES`, `RMSNORM_CALL_SITES`, `ELEMENTWISE_ADD_CALL_SITES` (lines 94-110), to see how call sites are named today. Read only.
- Meta's `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py`: `FeedForward.__init__` and `FeedForward.forward` (`w1`, `w2`, `w3`, `F.silu`). Read through `gh api repos/meta-llama/llama-models/contents/models/llama3/model.py?ref=0e0b8c519242d5833d8c11bffc1232b77ad7f301` or the raw URL, and cite the line numbers you read. If neither works, cite ADR-0152's account and say so in Status.
- `ARCHITECTURE/Requirements.md`: line 84 (the register's "행 형식"); the OD-6 row (line 97) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (the header's "기록 규칙"); § OD-6 (lines 59-81); § OD-31 (lines 526-546, the end of the file).
- `ARCHITECTURE/StandardScenarios.md`: lines 13-29 (the check rules); S0 (from line 30) and S1 (from line 45); § 검사 결과 (from line 168), especially its first paragraph (the recording rule) and the S0 and S1 rows of the verdict table.
- `PROCESS/STATE.json`: the unresolved `humanQuestions`, for the "Open HQs checked and not crossed" bullet.

## Acceptance Criteria

1. **New file `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`** in English (adjust the slug to the kind name you choose, and update `touchesFiles` in `## Result` if it differs). Follow ADR-0001's "Record format" and the section order of ADR-0159: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References. The title names what it decides. The status is "Accepted on <date of landing>".
2. **Status** has the same parts as ADR-0159 Status:
   - the three kinds of content (owner through ADR-0154, cited, this record's own) and the §9 objection window;
   - **the owner-sentence search** over the bodies and owner comments of #4, #5, #7 and #8 (comments without the "posted by driver" marker), with the terms used (at least: SwiGLU, SiLU, swish, sigmoid, activation, gate, feed-forward, FFN, MLP, exp, 활성화, 게이트, bf16, bfloat16, rounding, 반올림, in-place). Quote what is found and say what each quote does and does not say; say if nothing is found;
   - **the open HQs checked and not crossed**, with the `main` commit read: at least HQ-0033 (compiler flags; say what `-ffp-contract` and IEEE-relaxing flags can change for this operation, which has a multiply and a transcendental function, unlike the add), HQ-0034 (OpenMP) and HQ-0069 (runtime acceptance of the model executor); name the rest as not touched;
   - **not changed**: no data-plane schema, member, file, version or validator;
   - **answers**: which parts of OD-6 sub-question 1 and OD-31 sub-questions 1 to 3 this record answers;
   - **builds on**: only records cited by decision number in the body.
3. **Decision** settles each of the following, with the reason for each choice and the weighed alternatives in the Alternatives table:
   1. **Scope**: one contract, for the SwiGLU activation of ADR-0152 row 12, at dtype `bf16`, layout `row_major`, language `c`, on `cpu_standin`. Say plainly that no fp32 or fp16 contract of this kind is defined.
   2. **The `kind` value and its shape members**. The value matches `[a-z][a-z0-9_]{0,31}` and names the operation, not its place (ADR-0001 decision 2); say how it stays distinct from a later plain SiLU or other gated activation if that matters. Give the members' meaning against ADR-0152's T and intermediate width 8192, their relation to the `m`/`n` of `gemm` (the gate/up output and the down input), and why the kind raises no `schema_version` (ADR-0001 decision 6).
   3. **Dtype and layout** of each operand, with the `uint16_t` element reading of ADR-0156 decision 2.
   4. **The operation and its precision**:
      - what is computed element by element, with the definition of SiLU used (x · σ(x) = x / (1 + e^−x)) and which input is the gate and which the up operand, from Meta's code (cite the lines);
      - the precision of the exponential, the SiLU, and the product with `up`. The owner's three sums do not cover them (ADR-0154 decision 2), so this record chooses;
      - **whether the contract obliges a correctly rounded result or not**, and why. A correctly rounded bf16 result of x·σ(x)·u would need an argument like ADR-0159 decision 4's, which an exponential does not give for free; if the record obliges only binary32-or-wider intermediates (as ADR-0158 decision 3) or an error bound, say what it requires of the exponential (for example whether `expf` of the C library qualifies, given that its accuracy is not fixed by the C standard) and give the argument or source for any accuracy claim. Do not leave a bare assertion;
      - how the choice compares with Meta's bf16 `w2(F.silu(w1(x)) * w3(x))`: in a bf16 model the SiLU output is a bf16 tensor before the product. Say whether this contract keeps or drops that intermediate bf16 rounding, and state any departure from Meta's order of roundings as ADR-0158 decision 3 does. Do not rely on how PyTorch computes `silu` internally unless you read and cite it.
   5. **The output conversion to bf16**: as ADR-0156 decision 4 or otherwise, with its range consequences (overflow, zero and its sign, subnormal) for the value set of item 10.
   6. **The C prototype and the symbol**: the one line that is `task.contract.prototype`, byte for byte; parameter order (dimensions first, as ADR-0008 decision 4), operand names and order, `restrict` or not; the symbol in the form of ADR-0156/ADR-0158/ADR-0159 or with a reason to differ.
   7. **The operand entries table and the complete `task.contract`** at T = 1. Check it with `hilclaw.spec.validate` inside the committed spec example, in a throwaway interpreter that adds the kind to `hilclaw.keys._SHAPE_MEMBERS` in memory, as ADR-0159 decision 7 did, including one refused variant. Record the check; change no repository file.
   8. **Guarantees and obligations at a call**, in the table form of ADR-0159 decision 8. It decides: **aliasing** (whether the output may be `gate` or `up`; weigh `restrict`, ADR-0153 decision 3's "distinct arrays for each operand", what the pass reads afterwards (ADR-0152 decision 2) and ADR-0158/ADR-0159's refusals); **every set of dimensions** and so whether the binding "for every shape" of ADR-0153 decision 3 is accepted; zero dimensions read with ADR-0037; what is outside the input guarantee (finiteness).
   9. **What the kernel source provides** (ADR-0008 decision 7 with this record's symbol). Its other `hilclaw_` names include `hilclaw_gemm`, `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16` and `hilclaw_elementwise_add_bf16`. Say whether `<math.h>` (and linking `-lm`) is allowed under ADR-0008 decision 7's header list, or leave the link setting to Boundaries with HQ-0033 if it is a build setting.
   10. **The input value set of verification** (HQ-0066 (3) gives it to a driver record):
       - which bf16 values `gate` and `up` are drawn from, and why. Consider whether the set of ADR-0156 decision 9 (±[0.5, 1)) suits a SiLU input, which is not symmetric in sign (σ(x) for negative x), or whether another finite set serves better;
       - computed facts of the set (output range, whether any output is zero or subnormal, the reference's own exactness or error), computed and shown;
       - what the set can and cannot detect (for example a missing SiLU, a ReLU or a sigmoid in place of SiLU, swapped `gate` and `up`, a wrong row, the intermediate bf16 rounding of item 4), and whether that depends on the tolerance;
       - what is left to the P2-12 harness record (generator, seed, draws, widening). No tolerance value or default.
   11. **The `op_signature` records**: the rule, the canonical line and the sha256 at T = 1; the directory names for T in {1, 32, 512}, computed with `hilclaw.keys.op_signature_key` in the same throwaway interpreter, with the method recorded; that all layers share them.
   12. **The call site's name**: name the call of row 12 for the executor's binding, after Meta's code where it gives a name, and distinct from every GEMM, RMSNorm and elementwise add call-site name in `hilclaw/model_binding.py`. Give the reason, and the operand each input and the output take in the pass (which GEMM call site's output is `gate`, which is `up`, which call reads the output), so the code slice invents nothing.
   13. **Order and runs**: no order of kinds, instance or run is chosen (as ADR-0159 decision 13).
4. **Consequences**: the A-13 reading; the code slice this record makes possible, for the planner, without code (the kind in `hilclaw.keys`, a contract module, the binding check with its call site in `hilclaw/model_binding.py`, hand-written kernel fixtures, the P2-12 harness part); **less exact, not edited** (search `ARCHITECTURE/` for at least "SwiGLU", "other three kinds", "other four kinds", "other five kinds", "future contract records" and "Each kind's contract"; list what is found and do not claim completeness); runtime acceptance items (expected: none); the readings for the owner to check, listed in the #5 notice; the UsageCases and StandardScenarios result (criterion 7).
5. **Boundaries**: at least fp16 and an fp32 contract of this kind; tolerance values; build settings, `-lm` if left open, and OpenMP (HQ-0033, HQ-0034); the harness mechanism (P2-12); corner-case, non-finite and subnormal inputs (#5 B-7, OD-16); shapes outside an instance's (OD-16 sub-question 1); how a shape set maps to instances (OD-6 sub-question 3); contract change and keys (OD-6 sub-question 4); fusion with the gate/up GEMM (later, C-6); the contracts of RoPE and SDPA with KV cache; backends other than `cpu_standin`; the weights and the model-level comparison (OD-31 sub-questions 5 and 6, owner); any change to the first case or to ADR-0156, ADR-0158 and ADR-0159.
6. **Register and proposal edits**, each following the recording rule written in its own file (Required Reading); do not take the wording from earlier task files or commits:
   - `ARCHITECTURE/Requirements.md`, OD-6 and OD-31 rows: apply the register's "행 형식" (line 84) as written there — one new ADR link in the confirmed part, the open part rewritten in place so that it stays true after this record, no restatement of the record and no dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md`, § OD-6 and § OD-31: apply the header's "기록 규칙" (line 8) as written there — one adoption line per section for ADR-0160, the status at the end of each sub-question it partly answers and the bullet-head status word rewritten in place, no dated note and no restatement of the record.
   - No other part of these files is edited.
7. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"): re-check S0 and S1 and every scenario row that cites OD-6 sub-question 1 or OD-31 with the rules of `ARCHITECTURE/StandardScenarios.md`, and update § 검사 결과 exactly as its first paragraph prescribes (the latest re-check line rewritten in place; a history entry only if a verdict or gap changed; a verdict-table note changed only if an open part it names is no longer open). Say the result in the ADR's Consequences.
8. **Invents nothing**: no tolerance value, no order of kinds, no change to a #5 B-4 value, no fp16, no build flag value, no code. Every number in the record is cited or computed and shown (sha256 values, value-set facts, any accuracy bound).
9. **Process**: doc mode (CLAUDE.md A-13). Branch `claude/T-0441-<slug>`. Context-isolated reviewer cycle (dev-item-address 10 to 12) until Approve, at most 7 rounds; then rebase on `origin/main` and push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0441`. After landing, post the owner notice on #5 (DRIVER §9) with the record link, the readings for the owner to check and the 7-day objection window, and put the comment URL in `## Result`. The reviewer checks at least: every cited sentence against its source (Meta's lines included); the precision obligation and any accuracy argument; the value-set facts and what they detect (recomputed); the sha256 and directory names (recomputed); the `task.contract` validation; the aliasing and "every shape" decisions against ADR-0153 decision 3; the call-site name and operand table against ADR-0152 rows 11 to 13 and `hilclaw/model_binding.py`; that the register, proposal and scenario edits follow the rules written in those files; that no owner-only point is decided.
10. **Size**: the four files above only, about 230 changed lines.

## Out of Scope

- Any code: the kind in `hilclaw.keys`, a contract module, `hilclaw/model_binding.py`, the model program, kernel fixtures. These are the next code slices.
- The contracts of RoPE and SDPA with KV cache.
- The P2-12 harness mechanism, tolerance values, fp16, build flag values.
- Editing ADR-0152, ADR-0153, ADR-0154, ADR-0156, ADR-0157, ADR-0158 or ADR-0159; list what becomes less exact instead.
- The PLAN "보류" items.
- `PROCESS/` files other than this task file's `## Result`, which the executor fills.

## Follow-ups

- (planner) After this record, its code slice follows in the pattern of T-0439 and T-0440: the kind in `hilclaw.keys` and a contract module, then the binding check with the named call site in `hilclaw/model_binding.py`. The RoPE contract record comes after that, then SDPA with KV cache.

## Result
