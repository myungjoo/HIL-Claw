---
id: T-0444
title: Write ADR-0161 - the operational contract of RoPE on Q and K of Llama 3.2 1B in bf16 for C kernels on cpu_standin (kind value and op_signature members including the position, dtype and layout, where the frequency table comes from and its Llama 3 scaling, the pairing convention, the precision of angles, sin/cos and rotation, the rounding of the output, one call or two, in place or not and the strides over the QKV output, the uint16_t prototype and its symbol, operand entries, call guarantees, the input value set, the op_signature records of the ADR-0152 row 5 calls and the name of its call site), and update the OD-6, OD-31 and StandardScenarios records (fifth Llama kind contract of PLAN P2-11; extension of OD-6 sub-question 1, part of OD-31 sub-questions 1 to 3)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0441, T-0443]
touchesFiles: [ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 270, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `9c5f184`):
- ADR-0152 decision 2 lists six instance-target kinds for one Llama 3.2 1B forward pass. Four have a bf16 contract on `cpu_standin` and a landed code slice (kind in `hilclaw.keys`, contract module, binding check in `hilclaw/model_binding.py`):
  - GEMM (ADR-0156);
  - RMSNorm (ADR-0158);
  - elementwise add (ADR-0159);
  - SwiGLU activation (ADR-0160; code slices T-0442, T-0443).
- ADR-0160 Boundaries (line 202) and the planner follow-ups of T-0441 and T-0443 name the next step: the RoPE contract record, then SDPA with KV cache.
- **This task writes the RoPE record.** Until now it waited on the head count (ADR-0152 decision 6). The owner answered it (HQ-0064 through ADR-0154 decision 1): 32 query heads, 8 KV heads, head_dim 64. ADR-0154 decision 1 restates the RoPE row of ADR-0152 decision 5 with those values and marks it "No" in the "Waits on the head count?" column.

**What already settles part of it** (cited, not chosen here):
- **The call**: row 5 of ADR-0152 decision 2, "RoPE on Q and K at positions P … P+T−1", ×16. It runs after the QKV projection (row 4) and before SDPA (rows 6, 7). Three passages of ADR-0152 bear on it:
  - line 70: Q, K and V are column ranges of the one QKV output, and the order and strides in which RoPE reads them are "conventions of those kinds' contracts";
  - line 74: the frequency table (`precompute_freqs_cis` with `apply_scaling`) is a model constant, and "Whether the RoPE kernel takes them as an operand computed outside the kernels or computes them itself is the RoPE contract's";
  - Alternatives line 124: RoPE is its own kernel, not inside SDPA.
- **The shapes**: ADR-0154 decision 1's RoPE row. Q is T × 32 × 64 and K is T × 8 × 64, at positions P … P+T−1, with `rope_theta` 500000 and Llama 3 scaling (Meta). For prefill P = 0 and T ∈ {128, 2048}; for a decode step T = 1 at P ∈ {127, 2047}. ADR-0152 Alternatives line 126 says why RoPE takes the (T, P) of the SDPA calls.
- **The count**: ADR-0153 line 22 counts RoPE as one call and says "its contract may make it two". The executor's handling of copies a contract leaves is ADR-0153 decision 4.
- **The owner on precision and oracle**:
  - HQ-0065, through ADR-0154 decision 2: bf16 inputs and outputs, and `uint16_t` bit patterns at the kernel boundary with the kernel converting. fp32 accumulation is fixed only for the three sums the owner named, and RoPE has none of them. ADR-0154 decision 2 names "RoPE's angles, frequencies and sin/cos" as intermediate precisions the answer does not settle, and leaves each to its kind's contract record.
  - HQ-0066, through ADR-0154 decision 3: a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; each kind's input distribution fixed by a driver record, finite inputs only.
- **ADR-0153 decision 3**: a binding "for every shape" is accepted only where the contract obliges correctness at every shape, and the executor passes "distinct arrays for each operand".
- **ADR-0157 decision 4**: a call-site kind without a contract at the generation's dtype makes the dtype invalid input.
- **ADR-0158, ADR-0159 and ADR-0160** are the models for form and depth. RoPE differs from them in four ways the record must face openly:
  - its result depends on the position, a scalar that is not a dimension;
  - it involves a model constant table with a non-trivial scaling rule;
  - it uses sin and cos of large angles: P up to 2047 times frequencies up to 1. Argument reduction and the precision of the angle matter;
  - its inputs are column ranges of a wider row, so in-place use and strides are real questions.

**What this record decides** is its own under DRIVER §9 (driver design, accepted by a context-isolated reviewer, owner notified on #5 with a 7-day objection window). None of it is owner-only:
- the head count (HQ-0064), the dtype (HQ-0065), the oracle and tolerance vocabulary (HQ-0066) and the input distribution (given to a driver record by HQ-0066 (3)) are answered;
- no value of a #5 B-4 answer changes.

**The one owner-adjacent point** is the weights. The pairing convention interacts with the layout of the Q and K projection weights in a checkpoint. Meta's `model.py` pairs adjacent elements, and other published checkpoints may store the weights permuted for a half-split pairing. The weights and their source are OD-31 sub-question 5, which is the owner's. The record may choose the pairing the kernel implements, citing Meta's code. It must not decide which checkpoint format the executor reads or whether a weight permutation happens; it leaves that in Boundaries.

If the executor finds another point that would change an owner answer, it must not decide it: it leaves it in Boundaries and writes the question for the driver to record as an HQ. If the record cannot be written without that point, the executor stops with BLOCKED (`owner-only-decision`).

**PLAN order and D18.** P2 runs in list order. The round-loop items and P2-5 are held by unresolved HQs in `PROCESS/STATE.json`:
- HQ-0021 for round 0's board step;
- HQ-0048 for rounds >= 1, P2-6 and P2-7;
- the gate half of P2-4 is owner-only (OD-3).

P2-10 comes after P2-5. So work goes on with P2-11 to P2-14. This task is part of the P2-11 checklist item itself ("forward에 필요한 연산 종류마다 커널 계약·op_signature·하네스 검증"), and P2-14 needs it, so D18 does not set it aside.

**D16.** Nothing here starts `claude` or needs a board, a model file or an API key. Reading Meta's public source with `gh api` or a public URL is allowed (ADR-0158 to ADR-0160 did the same). Throwaway interpreter checks that change no repository file are allowed.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5: executor procedure, resume rule, time limit (line 72);
  - §5: task format, size cap and naming (lines 86-114). Here: branch `claude/T-0444-<slug>`; commit trailer `Task: T-0444`; doc mode, so no PR;
  - §9: OD closing authority and the owner notice (lines 144-152).
- `CLAUDE.md`: "상시 규칙", especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검" and "브랜치·merge 절차" (doc mode).
- `.claude/skills/dev-item-address/SKILL.md`: steps 7 and 9 to 12 (doc mode, reviewer cycle, 7-round limit).
- `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`: the whole file (215 lines). It is the closest model for:
  - structure, the owner-sentence search, the open-HQ check, the cited/own split, Consequences and Boundaries;
  - an obligation built on a transcendental function: decision 4 (lines 50-62), the error bound over a stated domain;
  - decision 8 (lines 104-118), decision 10 (lines 125-134) and decision 12 (lines 151-161).
- `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`: decisions 7, 8 and 12 (lines 78-117, 148-159).
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`: decision 3 (lines 44-51) and decision 5 (lines 57-68). Decision 5 is how a scalar model constant, `eps`, became part of a prototype and an `op_signature`. Compare it with `rope_theta`, the scaling constants and the position.
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`: decisions 2, 4 and 5 (lines 37-42, 52-73).
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: decisions 1 to 3 (lines 31-61) and Boundaries (lines 87-96).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`:
  - Context (lines 17-28, Meta's `apply_rotary_emb`, `precompute_freqs_cis`, `use_scaled_rope` at lines 22-23);
  - decision 2 (lines 41-66, rows 4 to 7);
  - decision 3 (lines 67-77, lines 70 and 74);
  - decision 5 (lines 84-104, the RoPE row at line 98, superseded in values by ADR-0154 decision 1);
  - decision 7 (lines 110-114);
  - Alternatives lines 124 and 126;
  - Boundaries line 152.
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Context line 22, decision 3 (lines 40-46) and decision 4 (lines 48-56).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-72).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: decisions 1 to 9 (lines 25-132).
- `ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md`: the decision.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: decision 2 (lines 37-52), decision 6 (lines 73-79) and "Record format" (lines 146-153).
- Read only, to see how a kind's members are known, how earlier records computed their directory names, and how call sites are named today:
  - `hilclaw/keys.py` (`_SHAPE_MEMBERS`, `op_signature_key`);
  - `hilclaw/rmsnorm_bf16_contract.py` and `hilclaw/swiglu_bf16_contract.py`;
  - `hilclaw/model_binding.py`: the module docstring and the `*_CALL_SITES` constants.
- Meta's `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`:
  - `models/llama3/model.py`: `precompute_freqs_cis`, `apply_scaling` (with its constants), `reshape_for_broadcast`, `apply_rotary_emb` and the lines of `Attention.forward` that call it and slice `freqs_cis` by `start_pos`;
  - `models/sku_list.py`: the `llama3_2_1b` `arch_args`.
  - Read them through `gh api repos/meta-llama/llama-models/contents/<path>?ref=0e0b8c519242d5833d8c11bffc1232b77ad7f301` or the raw URL, and cite the line numbers you read. If `apply_scaling` lives in another file at that commit, follow the import and cite that file. If neither way works, cite ADR-0152's account, say so in Status, and do not state any scaling constant you could not read.
- `ARCHITECTURE/Requirements.md`: line 84 (the register's "행 형식"); the OD-6 row (line 97) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (the header's "기록 규칙"); § OD-6 (from line 59); § OD-31 (from line 528 to the end of the file).
- `ARCHITECTURE/StandardScenarios.md`:
  - lines 13-29 (the check rules);
  - S0 (from line 30) and S1 (from line 45);
  - § 검사 결과 (from line 168), especially its first paragraph (the recording rule) and the S0 and S1 rows of the verdict table.
- `PROCESS/STATE.json`: the unresolved `humanQuestions`, for the "Open HQs checked and not crossed" bullet.

## Acceptance Criteria

1. **New file `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`** in English. If the chosen kind name differs, adjust the slug and update `touchesFiles` in `## Result`.
   - If another ADR-0161 has landed meanwhile, take the next free number and say so in `## Result`.
   - Follow ADR-0001's "Record format" and the section order of ADR-0160: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References.
   - The title names what it decides. The status is "Accepted on <date of landing>".
2. **Status** has the same parts as ADR-0160 Status:
   - the kinds of content (owner through ADR-0154, cited, this record's own) and the §9 objection window;
   - **the owner-sentence search** over the bodies and owner comments of #4, #5, #7 and #8 (comments without the "posted by driver" marker):
     - terms used, at least: RoPE, rotary, rope_theta, theta, scaling, scaled, position, positional, frequency, freqs, sin, cos, 회전, 위치, interleave, half, pair, bf16, bfloat16, rounding, 반올림, in-place, stride;
     - quote what is found and say what each quote does and does not say; say if nothing is found;
   - **the open HQs checked and not crossed**, with the `main` commit read. At least:
     - HQ-0033 (compiler flags): say what `-ffp-contract` and IEEE-relaxing flags can change for an operation with sin, cos, multiplies and adds;
     - HQ-0034 (OpenMP);
     - HQ-0069 (runtime acceptance of the model executor);
     - name the rest as not touched;
   - **not changed**: no data-plane schema, member, file, version or validator;
   - **answers**: which parts of OD-6 sub-question 1 and OD-31 sub-questions 1 to 3 this record answers;
   - **builds on**: only records cited by decision number in the body.
3. **Decision** settles each of the following, with the reason for each choice and the weighed alternatives in the Alternatives table:
   1. **Scope**: one contract, for RoPE of ADR-0152 row 5, at dtype `bf16`, layout `row_major` or a named alternative, language `c`, on `cpu_standin`. Say plainly that no fp32 or fp16 contract of this kind is defined.
   2. **One call or two, and the operands rotated**.
      - Choose between one call that rotates Q and K together, and a kind whose call rotates one tensor of any head count, called twice (once for Q, once for K).
      - Weigh ADR-0153 line 22, the shape set (Q has 32 heads and K has 8), the binding check, and the number of instance targets.
      - Say what the choice means for the count of kernel calls of one pass.
   3. **The `kind` value and its `op_signature` members**:
      - the value matches `[a-z][a-z0-9_]{0,31}` and names the operation, not its place (ADR-0001 decision 2);
      - the members' meaning against ADR-0154 decision 1's T, head counts, head_dim and positions P;
      - **whether the position P (or the start position) is a member of the key or a call argument only**, weighed against ADR-0152 Alternatives line 126 (the shape sets differ by P) and against what a member costs;
      - **whether `rope_theta` and the scaling constants are key members, prototype arguments, contract constants, or reach the kernel inside a table operand**, compared with how ADR-0158 decision 5 treated `eps`;
      - why the kind raises no `schema_version` (ADR-0001 decision 6).
   4. **The frequency table**, as ADR-0152 line 74 leaves to this contract:
      - whether the kernel computes the inverse frequencies and angles itself or receives a table (of frequencies, of angles, or of cos/sin values per position) computed outside the kernels;
      - if outside: by whom (the model program or the host side, ADR-0153 decision 4), in what dtype and precision, its shape and range of positions, and whether it is a new operand of the contract;
      - if inside: what the kernel must reproduce of `precompute_freqs_cis` and `apply_scaling`, with the constants read from Meta's code.
      - Either way, state the Llama 3 scaling rule exactly as Meta's code at that commit computes it (cite the lines), and name every constant with its source.
   5. **The pairing convention**: which elements of a head form a rotated pair (adjacent, as Meta's `apply_rotary_emb` reads them as complex numbers, or another), from Meta's code (cite the lines). Say which pair index takes which frequency. Leave the relation to a checkpoint's weight layout to Boundaries (OD-31 sub-question 5, owner); do not choose a checkpoint format or a weight permutation.
   6. **Dtype, layout and strides** of each operand, with the `uint16_t` element reading of ADR-0156 decision 2.
      - Decide whether the kernel reads Q and K where the QKV GEMM wrote them (columns of a row of width 3072, ADR-0152 line 70), with a row stride in the prototype, or reads contiguous arrays the model program copies (ADR-0153 decision 4).
      - Say what the SDPA contract then receives, without deciding the SDPA contract.
   7. **The operation and its precision**:
      - the rotation computed for each pair, from Meta's code (cite the lines);
      - the precision of the inverse frequencies, the angle (position × frequency, with P up to 2047), its argument reduction, sin and cos, and the rotation's multiplies and adds. The owner's three sums do not cover them (ADR-0154 decision 2), so this record chooses;
      - **whether the contract obliges a correctly rounded result, an error bound over a stated domain (as ADR-0160 decision 4), or binary32-or-wider intermediates only (as ADR-0158 decision 3)**, and why.
        - If it relies on `sinf`/`cosf` or `sin`/`cos` of the C library, say what it requires of them; their accuracy is not fixed by the C standard.
        - Give the argument or source for any accuracy claim, including the effect of an fp32 angle at positions near 2047. Do not leave a bare assertion.
      - How the choice compares with Meta's computation (`freqs_cis` built in float, `xq`/`xk` cast with `.float()`, the result cast back with `type_as`). State any departure from Meta's order of roundings as ADR-0158 decision 3 does. Do not rely on how PyTorch computes internally unless you read and cite it.
   8. **The output conversion to bf16**: as ADR-0156 decision 4 or otherwise, with its range consequences (overflow, zero and its sign, subnormal) for the value set of item 13.
   9. **The C prototype and the symbol**:
      - the one line that is `task.contract.prototype`, byte for byte;
      - parameter order (dimensions first, as ADR-0008 decision 4, then any position and constants), operand names and order, `restrict` or not;
      - the symbol in the form of ADR-0156/ADR-0158/ADR-0159/ADR-0160 or with a reason to differ.
   10. **The operand entries table and the complete `task.contract`** at one small shape of the set (say which).
       - Check it with `hilclaw.spec.validate` inside the committed spec example, in a throwaway interpreter that adds the kind to `hilclaw.keys._SHAPE_MEMBERS` in memory, as ADR-0160 decision 7 did, including one refused variant.
       - Record the check; change no repository file.
   11. **Guarantees and obligations at a call**, in the table form of ADR-0160 decision 8. It decides:
       - **aliasing and in-place use**: whether the output may be the input. Weigh `restrict`, ADR-0153 decision 3's "distinct arrays for each operand", item 6's strides, what the pass reads afterwards (rows 6 and 7 of ADR-0152 decision 2: SDPA reads the rotated Q and writes the rotated K into the cache), and the refusals of ADR-0158 to ADR-0160. If in-place is allowed, say how that is reconciled with ADR-0153 decision 3, and list ADR-0153 as less exact rather than editing it.
       - **every set of dimensions and positions**, and so whether the binding "for every shape" of ADR-0153 decision 3 is accepted; any limit on P and how it relates to the table of item 4;
       - zero dimensions read with ADR-0037;
       - what is outside the input guarantee (finiteness).
   12. **What the kernel source provides** (ADR-0008 decision 7 with this record's symbol).
       - Its other `hilclaw_` names include `hilclaw_gemm`, `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16` and `hilclaw_swiglu_bf16`.
       - Say whether `<math.h>` and the math library are needed, and treat them as ADR-0160 decision 9 did (cite its reading rather than re-deciding it, unless this kind needs something more).
   13. **The input value set of verification** (HQ-0066 (3) gives it to a driver record):
       - which bf16 values Q and K are drawn from, and any table operand's values, and why;
       - computed facts of the set (output range, whether any output is zero or subnormal, the reference's own error at the largest angles), computed and shown;
       - what the set can and cannot detect, and whether that depends on the tolerance. For example: the half-split pairing in place of adjacent pairs, a missing or wrong Llama 3 scaling, a wrong `rope_theta`, a position off by one, the sign of the sine term, Q and K swapped, a head of the wrong count;
       - what is left to the P2-12 harness record (generator, seed, draws, widening). No tolerance value or default.
   14. **The `op_signature` records**:
       - the rule, the canonical line and the sha256 at one shape;
       - the directory names for every shape of ADR-0154 decision 1's RoPE row, computed with `hilclaw.keys.op_signature_key` in the same throwaway interpreter, with the method recorded;
       - that all layers share them.
   15. **The call site name or names**:
       - name the call(s) of row 5 for the executor's binding, after Meta's code where it gives a name, and distinct from every call-site name in `hilclaw/model_binding.py`;
       - give the reason, and the operand each input and output takes in the pass: which part of which GEMM call site's output, and which call reads the output. The code slice must invent nothing.
   16. **Order and runs**: no order of kinds, instance or run is chosen (as ADR-0160 decision 13).
4. **Consequences**:
   - the A-13 reading;
   - the code slice this record makes possible, for the planner, without code: the kind in `hilclaw.keys`, a contract module, the binding check with its call site(s) and the (T, P) shapes in `hilclaw/model_binding.py`, any table built outside the kernels, hand-written kernel fixtures, the P2-12 harness part;
   - **less exact, not edited**: search `ARCHITECTURE/` for at least "RoPE", "other two kinds", "other five kinds", "future contract records", "Each kind's contract" and "counted as one call". List what is found and do not claim completeness;
   - runtime acceptance items (expected: none);
   - the readings for the owner to check, listed in the #5 notice, with the pairing/checkpoint point among them;
   - the UsageCases and StandardScenarios result (criterion 7).
5. **Boundaries**, at least:
   - fp16 and an fp32 contract of this kind;
   - tolerance values;
   - build settings and OpenMP (HQ-0033, HQ-0034);
   - the harness mechanism (P2-12);
   - corner-case, non-finite and subnormal inputs (#5 B-7, OD-16);
   - positions and shapes outside an instance's (OD-16 sub-question 1, ADR-0152 decision 7);
   - how a shape set maps to instances (OD-6 sub-question 3);
   - contract change and keys (OD-6 sub-question 4);
   - fusion with the QKV GEMM or with SDPA (later, C-6);
   - the SDPA with KV cache contract, including how it reads the rotated Q and K;
   - **the weights and checkpoint format, including any permutation of the Q and K projection weights for a pairing (OD-31 sub-question 5, owner)**;
   - the model-level comparison (sub-question 6, owner);
   - backends other than `cpu_standin`;
   - any change to the first case or to ADR-0156, ADR-0158, ADR-0159 and ADR-0160.
6. **Register and proposal edits**, each following the recording rule written in its own file (Required Reading). Do not take the wording from earlier task files or commits.
   - `ARCHITECTURE/Requirements.md`, OD-6 and OD-31 rows: apply the register's "행 형식" (line 84) as written there:
     - one new ADR link in the confirmed part;
     - the open part rewritten in place so that it stays true after this record;
     - no restatement of the record and no dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md`, § OD-6 and § OD-31: apply the header's "기록 규칙" (line 8) as written there:
     - one adoption line per section for ADR-0161;
     - the status at the end of each sub-question it partly answers, and the bullet-head status word, rewritten in place;
     - no dated note and no restatement of the record.
   - No other part of these files is edited.
7. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"):
   - re-check S0 and S1, and every scenario row that cites OD-6 sub-question 1 or OD-31, with the rules of `ARCHITECTURE/StandardScenarios.md`;
   - update § 검사 결과 exactly as its first paragraph prescribes;
   - say the result in the ADR's Consequences.
8. **Invents nothing**:
   - no tolerance value, no order of kinds, no change to a #5 B-4 value or an owner answer, no fp16, no build flag value, no checkpoint format, no code;
   - every number in the record is cited or computed and shown: scaling constants, frequencies, sha256 values, value-set facts, any accuracy bound.
9. **Process**: doc mode (CLAUDE.md A-13).
   - Branch `claude/T-0444-<slug>`. Context-isolated reviewer cycle (dev-item-address 10 to 12) until Approve, at most 7 rounds.
   - Then rebase on `origin/main` and push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0444`.
   - After landing, post the owner notice on #5 (DRIVER §9) with the record link, the readings for the owner to check and the 7-day objection window, and put the comment URL in `## Result`.
   - The reviewer checks at least:
     - every cited sentence against its source, Meta's lines and the scaling constants included;
     - the one-call-or-two, position-as-member, table and stride decisions against ADR-0152 lines 70, 74 and 126 and ADR-0153 decisions 3 and 4;
     - the precision obligation and any accuracy argument, at the largest angles;
     - the value-set facts and what they detect (recomputed);
     - the sha256 and directory names (recomputed);
     - the `task.contract` validation;
     - the aliasing and "every shape" decisions against ADR-0153 decision 3;
     - the call-site name(s) and operand table against ADR-0152 rows 4 to 7 and `hilclaw/model_binding.py`;
     - that the register, proposal and scenario edits follow the rules written in those files;
     - that no owner-only point is decided, in particular no checkpoint format or weight permutation.
10. **Size**: the four files above only, about 270 changed lines. If the record cannot fit under the D4 cap of 300 changed lines, stop before writing past it. Propose a split in `## Follow-ups`, for example a separate record for the frequency table, and finish the part that fits.

## Out of Scope

- Any code: the kind in `hilclaw.keys`, a contract module, `hilclaw/model_binding.py`, the model program, a frequency table builder, kernel fixtures. These are the next code slices.
- The contract of SDPA with KV cache.
- The P2-12 harness mechanism, tolerance values, fp16, build flag values.
- The weights, their checkpoint format and any permutation (OD-31 sub-question 5, owner).
- Editing ADR-0152, ADR-0153, ADR-0154, ADR-0156, ADR-0157, ADR-0158, ADR-0159 or ADR-0160; list what becomes less exact instead.
- The PLAN "보류" items.
- `PROCESS/` files other than this task file's `## Result`, which the executor fills.

## Follow-ups

- (planner) After this record, its code slice follows in the pattern of T-0442 and T-0443:
  - the kind in `hilclaw.keys` and a contract module;
  - then the binding check with the named call site(s) and (T, P) shapes in `hilclaw/model_binding.py`.
  - The SDPA with KV cache contract record comes after that.

## Result
