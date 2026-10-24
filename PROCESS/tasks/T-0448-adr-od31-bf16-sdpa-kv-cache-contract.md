---
id: T-0448
title: Write ADR-0162 - the operational contract of SDPA with KV cache of Llama 3.2 1B in bf16 for C kernels on cpu_standin (kind value and op_signature members, the cache operands with their capacity and layout and the write of the new K and V rows, GQA head sharing, score scale, causal mask, the precision of both dot products, the softmax and the cast between them, the output layout for the O projection, the rounding of the output, the uint16_t prototype and symbol, operand entries, call guarantees, the input value set, the op_signature records of the ADR-0154 SDPA row and the call site), and update the OD-6, OD-31 and StandardScenarios records (sixth and last Llama kind contract of PLAN P2-11; extension of OD-6 sub-question 1, part of OD-31 sub-questions 1 to 3)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0444, T-0447]
touchesFiles: [ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 290, files: 4}
hq: []
---
## Why

**State on `main` `18b6d1a`.** ADR-0152 decision 2 names six instance-target kinds for one Llama 3.2 1B forward pass. Five of them now have a bf16 contract record on `cpu_standin` and landed code (kind in `hilclaw.keys`, a contract module, a binding check in `hilclaw/model_binding.py`): GEMM (ADR-0156), RMSNorm (ADR-0158), elementwise add (ADR-0159), SwiGLU activation (ADR-0160) and RoPE (ADR-0161, code T-0445 to T-0447). The sixth, **SDPA with KV cache** (rows 6 and 7 of ADR-0152 decision 2), has no contract. Without it the executor (PLAN P2-13) cannot bind attention and P2-14 cannot run a pass. ADR-0161 Boundaries and the follow-ups of T-0444 and T-0447 name this record as the next step. **This task writes it.**

**Already fixed elsewhere** (this record cites them and does not re-decide them):
- **What the kernel does.** ADR-0152 decision 3 puts the KV cache write (row 6) inside the SDPA kernel: the kernel takes the cache as an operand it updates, writes the new K and V rows at positions P … P+T−1, and attends over 0 … L−1. GQA head sharing, the 1/√head_dim scale, the causal mask and the softmax are also inside it. Alternatives lines 122 and 123 give the reasons. Softmax is not a kernel of its own.
- **The shapes.** ADR-0154 decision 1, SDPA row: prefill T = S, P = 0, L = S; a decode step T = 1, P = S − 1, L = S; S ∈ {128, 2048}. Q is T × 32 × 64, the new K and V are T × 8 × 64, the cache holds 8 × 64 per position, the output is T × 2048, and the mask is causal. ADR-0152 Alternatives line 129 explains the reading L = S for a decode step.
- **The cache as executor work.** ADR-0153 decision 4 (line 52): the model program owns the cache of each layer, allocates it before the prefill to hold at least the positions the generation writes, and keeps it across decode steps. It leaves "its capacity, its layout and how the kernel is told the capacity" to this contract. The same decision gives the copies a contract leaves (the SDPA output for the O projection is named there) to the model program.
- **The inputs.** ADR-0161 decisions 6 and 15. RoPE writes contiguous `out` arrays: `rope_q` gives the query input of the SDPA call of the same layer, and `rope_k` gives the new K rows that call writes into the cache. The V range of the QKV output is not rotated; how SDPA receives it is this record's.
- **The owner on precision and oracle.**
  - HQ-0065, through ADR-0154 decision 2: bf16 inputs and outputs; `uint16_t` bit patterns at the boundary, with the kernel converting; fp32 accumulation for the **softmax sum**. Line 50 of ADR-0154 lists what that answer does **not** settle, and leaves each item to this contract: the two dot products inside SDPA (Q·Kᵀ and probabilities·V), the score scaling, the precision of scores and probabilities, and the cast between the score product and the value product.
  - HQ-0066, through ADR-0154 decision 3: a float64 NumPy reference without bf16 emulation; element-wise `rtol`/`atol` with no default; the input distribution fixed by a driver record, finite inputs only.

**Authority.** What this record decides is driver design under DRIVER §9: a context-isolated reviewer accepts it, and the owner is notified on #5 with a 7-day objection window. No owner-only point is needed:
- the head count, the dtype, the softmax-sum precision, the oracle and the tolerance vocabulary are answered;
- the input distribution goes to a driver record (HQ-0066 (3));
- no #5 B-4 value changes.

**Owner-adjacent points the record must not decide** (leave each in Boundaries):
- The cache **capacity value** follows from the prompt and generation lengths, which belong to OD-31 sub-question 6 (owner). The contract may say how the kernel is told the capacity, and what the kernel requires of it. It must not fix a maximum sequence length beyond the ADR-0154 shapes.
- The model-level comparison (sub-question 6), the weights (sub-question 5) and the RoPE scale factor (HQ-0070, open).

If the executor finds another point that would change an owner answer, it does not decide it. It leaves the point in Boundaries and writes the question for the driver to record as an HQ. If the record cannot be written without that point, the executor stops with BLOCKED (`owner-only-decision`).

**PLAN order and D18.** P2 runs in list order. These HQs in `PROCESS/STATE.json` still hold the round-loop items and P2-5:
- HQ-0021 (round 0's board step);
- HQ-0048 (rounds >= 1, P2-6, P2-7);
- the gate half of P2-4, which is owner-only (OD-3).

P2-10 follows P2-5. So work continues on P2-11 to P2-14. This record is part of the P2-11 checklist item itself ("forward에 필요한 연산 종류마다 커널 계약·op_signature·하네스 검증"), and P2-14 needs it, so the D18 rule does not apply to it.

**HQ-0034.** The owner answered HQ-0034 (OpenMP on every C-7 system). That answer is not part of this task (see Out of Scope).

**D16.** Nothing in this task starts `claude` or needs a board, a model file or an API key. The executor may read Meta's public source with `gh api` or a public URL. Throwaway interpreter checks that change no repository file are allowed.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap and the naming. Branch `claude/T-0448-<slug>`; commit trailer `Task: T-0448`; doc mode, so there is no PR;
  - §9 (lines 144-152): who may close an OD, and the owner notice.
- `CLAUDE.md`, "상시 규칙": especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검" and "브랜치·merge 절차" (doc mode).
- `.claude/skills/dev-item-address/SKILL.md`: steps 7 and 9 to 12 (doc mode, the reviewer cycle, the 7-round limit).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`: the whole file (216 lines). It is the closest model for structure and depth:
  - Status (lines 3-20): the owner-sentence search, the open-HQ check, the cited/own split;
  - decision 6 (lines 62-67): copies versus strides;
  - decision 7 (lines 68-74): the precision obligation and the accuracy argument;
  - decisions 9 to 15 (lines 79-164);
  - Consequences and Boundaries (lines 185-208).
- `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`: decision 4 (lines 50-62), an error bound over a stated domain for an `exp`-based operation; decision 9 (lines 120-124), `<math.h>` and the math library.
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`: decision 3 (lines 44-51), the fp32 owner sum and binary32-or-wider intermediates; decision 5 (lines 57-68), a scalar in the prototype and the key.
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`: decisions 2 to 5 (lines 37-73).
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: decisions 1 to 3 (lines 31-61) and Boundaries (from line 87).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`:
  - Context line 23 (Meta's `Attention.forward`);
  - decision 1 (lines 33-39);
  - decision 2 (lines 41-65, rows 3 to 9);
  - decision 3 (lines 67-76, lines 70 to 72);
  - decision 5 (from line 84; the SDPA row at line 99, whose values ADR-0154 decision 1 replaces);
  - decision 7;
  - Alternatives lines 122-129;
  - Boundaries.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Context (lines 16-23), decision 3 (lines 40-46) and decision 4 (lines 48-56, especially line 52).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-72).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 1 to 9 (lines 25-132).
- `ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md`: the decision.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: decision 2 (lines 37-52), decision 6 (lines 73-79) and "Record format" (from line 146).
- Read only. These show how a kind's members are known, how directory names are computed, and how call sites and their operands are named today:
  - `hilclaw/keys.py`: `_SHAPE_MEMBERS` and `op_signature_key`;
  - `hilclaw/rope_bf16_contract.py`;
  - `hilclaw/model_binding.py`: the module docstring, the `*_CALL_SITES` constants, `rope_shape` and `rope_generation_calls`.
- Meta's `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`:
  - `models/llama3/model.py`: `Attention.__init__` (the cache tensors, their shape and dtype), `Attention.forward` (the cache write, `repeat_kv`, the score product and its scale, the mask add, `F.softmax(scores.float(), dim=-1).type_as(xq)`, the value product, the output transpose and reshape), `repeat_kv`, and the mask built in `Transformer.forward`;
  - `models/sku_list.py`: the `llama3_2_1b` `arch_args`.
  - Read them with `gh api repos/meta-llama/llama-models/contents/<path>?ref=0e0b8c519242d5833d8c11bffc1232b77ad7f301` or with the raw URL, and cite the line numbers you read. If neither works, cite ADR-0152's account, say so in Status, and do not state any detail you could not read.
- `ARCHITECTURE/Requirements.md`: line 84 (the register's "행 형식"), the OD-6 row (line 97) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (the header's "기록 규칙"), § OD-6 (from line 59) and § OD-31 (lines 529-551).
- `ARCHITECTURE/StandardScenarios.md`:
  - lines 13-29, the check rules;
  - S0 (from line 30) and S1 (from line 45);
  - § 검사 결과 (from line 168): its first paragraph and the S0 and S1 rows.
- `PROCESS/STATE.json`: the unresolved `humanQuestions` and the answered HQ-0034, for the "open HQs checked" part of Status.

## Acceptance Criteria

1. **New file `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`**, in English.
   - If ADR-0162 is taken when you land, use the next free number and say so in `## Result`. If you choose a different kind name, adjust the slug and record the final path in `## Result`.
   - Use ADR-0001's "Record format" and ADR-0161's section order.
   - The title names what the record decides. The status is "Accepted on <landing date>".
2. **Status**, with the same parts as ADR-0161 Status:
   - **The kinds of content**: what comes from the owner (through ADR-0154), what is cited, and what is this record's own; plus the §9 objection window.
   - **The owner-sentence search** over the bodies of #4, #5, #7 and #8 and their owner comments (comments without the "posted by driver" marker).
     - Search at least these terms: SDPA, attention, KV cache, cache, softmax, causal, mask, GQA, repeat_kv, scale, sqrt, seq_len, max_seq_len, capacity, decode, prefill, bf16, bfloat16, rounding, 반올림, 캐시, 어텐션.
     - Quote what you find and state what each quote says and does not say. If nothing is found, say so.
   - **The open HQs checked and not crossed**, with the `main` commit you read. Cover at least:
     - HQ-0033 (compiler flags): what `-ffp-contract` and IEEE-relaxing flags can change in an operation with dot products, `exp`, a max and a division;
     - HQ-0034: answered (a) on 2026-10-25, not yet reflected in ADR-0116. Say that this record depends on neither OpenMP nor threads;
     - HQ-0069 (runtime acceptance of the model executor);
     - HQ-0070 (the RoPE scale factor): it does not reach this contract;
     - name all the others as not touched.
   - **Not changed**: no data-plane schema, member, file, version or validator.
   - **Answers**: which parts of OD-6 sub-question 1 and OD-31 sub-questions 1 to 3 this record answers.
   - **Builds on**: only records cited by decision number in the body.
3. **Decision.** Settle each item below. Give the reason for each choice, and put the alternatives you weighed in the Alternatives table.
   1. **Scope**: one contract for rows 6 and 7 of ADR-0152 decision 2, at dtype `bf16`, layout `row_major` or a named alternative, language `c`, on `cpu_standin`. State that no fp32 or fp16 contract of this kind is defined.
   2. **One kind for prefill and decode, or two.** Weigh the shape set (T = S at P = 0, against T = 1 at P = S − 1), the mask (Meta builds none for a single token), the binding check, and the number of instance targets.
   3. **The `kind` value and its `op_signature` members.**
      - The value matches `[a-z][a-z0-9_]{0,31}` and names the operation, not its place (ADR-0001 decision 2).
      - Relate each member to ADR-0154 decision 1's T, P, L, query heads, KV heads and head_dim.
      - **Are P and L key members or call arguments only?** Weigh this against ADR-0161's treatment of the position and against the four SDPA shapes.
      - **Is the cache capacity a key member, a prototype argument, or neither?** Weigh this against ADR-0153 line 52 and against what a member costs.
      - Say whether the score scale is a contract constant derived from head_dim, an argument, or a member, and compare with ADR-0158 decision 5's `eps`.
      - Say why the kind raises no `schema_version` (ADR-0001 decision 6).
   4. **The cache operands.**
      - Number and roles (separate K and V caches, or one).
      - Dtype (read against ADR-0154 decision 2's "inputs and outputs are bf16"; state the reading as yours).
      - Layout: position-major or head-major, and any stride.
      - How the kernel is told the capacity, and what it requires of the capacity relative to P + T.
      - What the kernel writes (the rows at P … P+T−1, from the new K and V) and what it leaves unchanged.
      - What the kernel may assume about rows 0 … P−1, and that rows at L and beyond are never read.
      - Compare all of this with Meta's `cache_k`/`cache_v` (cite the lines). Choose no capacity value (Boundaries).
   5. **The other operands, their dtype, layout and strides**, read with the `uint16_t` element reading of ADR-0156 decision 2:
      - Q from `rope_q`'s output and the new K from `rope_k`'s output (ADR-0161 decision 15);
      - the new V: read in place as the V column range of the QKV output with a row stride, or as a contiguous copy by the model program (ADR-0153 decision 4). Give the reason, consistent with ADR-0161 decision 6 or argued against it;
      - the output: its layout as T × 2048 rows for the O projection (Meta's transpose and reshape, cited). Say whether the O GEMM can read it directly or the model program must copy it.
   6. **The operation**, from Meta's code with line citations:
      - GQA: which KV head serves query head h (the `repeat_kv` order);
      - the scale 1/√64 and where it is applied;
      - the causal mask in prefill and in a decode step, and which key positions query row i attends to;
      - the softmax over the attended positions;
      - the value product.
   7. **Precision.**
      - The softmax sum is fp32 (owner).
      - This record chooses everything else that ADR-0154 line 50 lists: the accumulation of Q·Kᵀ and of probabilities·V; the scale; the max subtraction (or not) before `exp`; the precision of `exp`; the precision in which scores and probabilities are held; and **whether the probabilities are rounded to bf16 before the value product**, as Meta's `.type_as(xq)` does, or kept in fp32.
      - **Choose the kind of obligation**: a correctly rounded result, an error bound over a stated domain (as ADR-0160 decision 4), or binary32-or-wider intermediates only (as ADR-0158 decision 3). Say why.
      - If the obligation relies on `expf`/`exp` of the C library, say what it requires of them; the C standard does not fix their accuracy.
      - Back every accuracy claim with an argument or a computation. That includes the effect of the longest row (L = 2048) on the fp32 sums. No bare assertions.
      - State every departure from Meta's order of roundings, as ADR-0158 decision 3 did. Do not rely on PyTorch internals you did not read and cite.
   8. **The output conversion to bf16**: as ADR-0156 decision 4 or otherwise. State its range consequences (overflow, signed zero, subnormal) for the value set of item 13.
   9. **The C prototype and the symbol.**
      - Give the one line that is `task.contract.prototype`, byte for byte.
      - Give the parameter order (dimensions first, as ADR-0008 decision 4, then any position, capacity or stride), the operand names and their order, and whether `restrict` is used.
      - Give the symbol in the form `hilclaw_<kind>_bf16`, or a reason to differ.
   10. **The operand entries table and the complete `task.contract`**, at one small shape of the set (say which).
       - Validate it with `hilclaw.spec.validate` inside the committed spec example, in a throwaway interpreter that adds the kind to `hilclaw.keys._SHAPE_MEMBERS` in memory, as ADR-0161 decision 10 did.
       - Include one refused variant.
       - Record the check. Change no repository file.
       - Say how the in/out role of the cache operands is expressed in the existing operand-entry vocabulary. If that vocabulary has no role for an operand that is both read and written, say so and choose within the vocabulary or leave it in Boundaries. Do not extend the spec schema (A-13: a data-plane schema change is a BLOCKED reason).
   11. **Guarantees and obligations at a call**, in the table form of ADR-0161 decision 11:
       - **aliasing**: which operands may overlap (the caches are updated in place), weighed against `restrict` and ADR-0153 decision 3's "distinct arrays for each operand". If the record departs from ADR-0153, list ADR-0153 as less exact; do not edit it;
       - **every set of dimensions, positions and capacities**, and so whether ADR-0153 decision 3's binding "for every shape" is accepted;
       - zero dimensions, read with ADR-0037;
       - what lies outside the input guarantee (finiteness, the contents of cache rows the kernel did not write).
   12. **What the kernel source provides** (ADR-0008 decision 7, with this record's symbol). Its other `hilclaw_` names include `hilclaw_gemm`, `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16`, `hilclaw_swiglu_bf16` and the RoPE symbol of ADR-0161. For `<math.h>`, cite ADR-0160 decision 9 rather than re-deciding it, unless this kind needs more.
   13. **The input value set of verification** (HQ-0066 (3) gives it to a driver record):
       - which bf16 values Q, the new K and V, and the pre-filled cache rows 0 … P−1 of a decode-step check are drawn from, and why;
       - computed facts of the set: score range, whether `exp` can underflow to zero in a row, the output range, any zero or subnormal output, and the reference's own error. Compute and show them;
       - what the set can and cannot detect, and whether that depends on the tolerance. Examples:
         - a wrong GQA mapping (query head h served by KV head h mod 8 instead of the `repeat_kv` order);
         - a missing or doubled scale;
         - a mask off by one, or no mask in prefill;
         - new rows written at the wrong positions, or the cache not written at all;
         - attention over unwritten rows past L;
         - Q and K swapped;
         - a softmax without normalisation;
       - what is left to the P2-12 harness record (generator, seed, draws, widening). No tolerance value and no default.
   14. **The `op_signature` records.**
       - Give the rule, the canonical line and the sha256 at one shape.
       - Give the directory names for all four shapes of ADR-0154 decision 1's SDPA row, computed with `hilclaw.keys.op_signature_key` in the same throwaway interpreter. Record the method.
       - Say that all 16 layers share them.
   15. **The call site.**
       - Name the call for the executor's binding. Follow Meta's code where it gives a name, and use a name different from every call site in `hilclaw/model_binding.py`.
       - Give the reason.
       - Give the operand each input and output takes in the pass:
         - Q: from `rope_q`;
         - new K: from `rope_k`;
         - new V: from the V range of `qkv`;
         - the caches of the same layer;
         - the output: read by the GEMM call site `o`.
       - The code slice must not need to invent any of this.
   16. **Order and runs**: choose no order of kinds, instances or runs (as ADR-0161 decision 16).
4. **Consequences**:
   - the A-13 reading;
   - for the planner, the code slices this record makes possible, without code:
     - the kind in `hilclaw.keys` and a contract module;
     - the binding check with its call site and its (T, P, L) shapes in `hilclaw/model_binding.py`;
     - the cache buffers of the model program;
     - hand-written kernel fixtures;
     - the P2-12 harness part;
   - say that, with this record, every kind of ADR-0152 decision 2 has a bf16 contract on `cpu_standin`;
   - **less exact, not edited**:
     - search `ARCHITECTURE/` for at least "SDPA", "KV cache", "other two kinds", "the other kinds", "future contract records", "Each kind's contract" and "cache operands";
     - list what you find, and do not claim the list is complete;
   - runtime acceptance items (expected: none);
   - the readings the owner should check, to be listed in the #5 notice. Include the cache dtype reading and the probability-rounding choice;
   - the result of the UsageCases and StandardScenarios check (criterion 7).
5. **Boundaries**, covering at least:
   - fp16, and an fp32 contract of this kind;
   - tolerance values;
   - build settings and OpenMP (HQ-0033; HQ-0034's answer and its reflection in ADR-0116);
   - the harness mechanism (P2-12);
   - corner-case, non-finite and subnormal inputs (#5 B-7, OD-16);
   - positions, lengths and shapes outside an instance's (OD-16 sub-question 1, ADR-0152 decision 7);
   - the capacity value and the maximum sequence length (OD-31 sub-question 6, owner);
   - how a shape set maps to instances (OD-6 sub-question 3);
   - contract change and keys (OD-6 sub-question 4);
   - fusion with RoPE or the O projection, and attention algorithms that change the order of the sums (for example a blocked online softmax), if the chosen obligation excludes them (later, C-6);
   - batches above 1 and paged or shared caches;
   - the weights (sub-question 5) and the model-level comparison (sub-question 6);
   - backends other than `cpu_standin`;
   - any change to the first case or to ADR-0156, ADR-0158, ADR-0159, ADR-0160 and ADR-0161.
6. **Register and proposal edits.** Read each file's own recording rule and apply it as written there. Do not reuse wording from earlier task files or commits.
   - `ARCHITECTURE/Requirements.md`, OD-6 and OD-31 rows: follow the "행 형식" of line 84:
     - add the one new ADR link to the confirmed part;
     - rewrite the open part in place so that it is true after this record (SDPA leaves the open part of sub-questions 1 to 3 for `cpu_standin`);
     - do not restate the record and do not add a dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md`, § OD-6 and § OD-31: follow the "기록 규칙" of line 8:
     - add one adoption line for ADR-0162 in each section;
     - rewrite in place the status at the end of each sub-question it partly answers, and the status word at the head of that bullet;
     - no dated note and no restatement.
   - Edit no other part of these files.
7. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"):
   - Re-check S0 and S1, and every scenario row that cites OD-6 sub-question 1 or OD-31, with the rules of `ARCHITECTURE/StandardScenarios.md`.
   - Update § 검사 결과 exactly as its first paragraph prescribes.
   - State the result in the ADR's Consequences.
8. **Invent nothing.**
   - No tolerance value.
   - No capacity value or maximum sequence length.
   - No order of kinds.
   - No change to a #5 B-4 value or to an owner answer.
   - No fp16.
   - No build flag value.
   - No spec-schema change.
   - No code.
   - Every number in the record is cited, or computed and shown: the scale, sha256 values, value-set facts and any accuracy bound.
9. **Process**: doc mode (CLAUDE.md A-13).
   - Work on branch `claude/T-0448-<slug>`.
   - Run the context-isolated reviewer cycle (dev-item-address steps 10 to 12) until Approve, at most 7 rounds.
   - Then rebase on `origin/main` and push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0448`.
   - After landing, post the owner notice on #5 (DRIVER §9; driver footer of §8). It holds the record link, the readings for the owner to check and the 7-day objection window. Put the comment URL in `## Result`.
   - The reviewer checks at least:
     - every cited sentence against its source, Meta's lines included;
     - the kind, member and capacity decisions against ADR-0152 lines 71 to 72 and Alternatives lines 122 to 129, and against ADR-0153 decisions 3 and 4;
     - the GQA mapping, scale and mask against Meta's code;
     - the precision obligation and any accuracy argument at L = 2048;
     - the value-set facts and what they detect (recomputed);
     - the sha256 values and directory names (recomputed);
     - the `task.contract` validation, and that no spec-schema change is implied;
     - the aliasing and "every shape" decisions;
     - the call site and the operand table against ADR-0161 decision 15 and `hilclaw/model_binding.py`;
     - that the register, proposal and scenario edits follow the rules written in those files;
     - that no owner-only point is decided, and in particular no capacity value.
10. **Size**: only the four files above, about 290 changed lines.
    - If the record cannot fit under the D4 cap of 300 changed lines, stop before you write past it.
    - Propose a split in `## Follow-ups`, and finish the part that fits. For example, items 13 and 14 (the value set and the `op_signature` records) can go into a second record.

## Out of Scope

- Any code. This covers the kind in `hilclaw.keys`, a contract module, `hilclaw/model_binding.py`, the model program, the cache buffers and kernel fixtures. They are the next code slices.
- The P2-12 harness mechanism, tolerance values, fp16 and build flag values.
- Reflecting the HQ-0034 answer (OpenMP) in ADR-0116 or in the build settings. The driver handles it under D18 (PLAN "보류").
- The weights, the model-level comparison, generation lengths and the RoPE scale factor (OD-31 sub-questions 5 and 6, HQ-0070; all owner).
- Editing ADR-0152, ADR-0153, ADR-0154, ADR-0156, ADR-0157, ADR-0158, ADR-0159, ADR-0160 or ADR-0161. List what becomes less exact instead.
- The PLAN "보류" items.
- Any `PROCESS/` file other than this task file's `## Result`, which the executor fills.

## Follow-ups

- (planner) After this record, its code slices follow the pattern of T-0445 to T-0447:
  - first, the kind in `hilclaw.keys` and a contract module;
  - then the binding check, with the call site and the (T, P, L) shapes, in `hilclaw/model_binding.py`.
- After that, P2-11's harness verification (P2-12) and the full pass of P2-13 remain.

## Result
