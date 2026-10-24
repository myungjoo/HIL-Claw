---
id: T-0451
title: Write ADR-0163 - the verification run of one built bf16 kernel on cpu_standin for the kinds gemm, rmsnorm, elementwise_add and swiglu (program and process, command line, generator over each contract's value set, independence of operands, seed and draws, output content before the call, widening and float64 reference per kind including the RMSNorm eps the reference uses, input check, report, comparison, verdict, calibration, parameters, limits), and update the OD-16, OD-31 and StandardScenarios records (P2-12 harness record, first part; part of OD-31 sub-question 3 and of OD-16)
phase: P1
status: DONE
commitMode: doc
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0448]
touchesFiles: [ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 270, files: 4}
hq: []
---
## Why

**State on `main` `acfdb9b`.** Every instance-target kind of ADR-0152 decision 2 now has a bf16 contract record on `cpu_standin`: GEMM (ADR-0156), RMSNorm (ADR-0158), elementwise add (ADR-0159), SwiGLU activation (ADR-0160), RoPE (ADR-0161) and SDPA with KV cache (ADR-0162). Each kind also has landed op-side code: a contract module `hilclaw/<kind>_bf16_contract.py` and a binding check in `hilclaw/model_binding.py` (T-0430 to T-0450).

**What is missing is the harness verification of a bf16 kernel.** PLAN P2-11 asks, for every kind, for "커널 계약·op_signature·하네스 검증". PLAN P2-12 asks for the harness's inputs, reference and tolerance in bf16. P2-14 needs instances that produce kernels for these kinds, and an instance cannot judge a bf16 kernel without such a run.
- `hilclaw/harness/` knows only the fp32 `gemm` run of ADR-0017. `verification_program.c` calls `hilclaw_gemm` over `float`, and `verification_arrays.py` draws binary32 values in [0.5, 1).
- Each bf16 contract record fixes only its **value set** of verification inputs. It hands the rest to "the P2-12 harness record". That rest is listed in ADR-0156 decision 9 (line 126), ADR-0158 decision 9 (line 121), ADR-0159 decision 10 (line 130), ADR-0160 decision 10 (line 133), ADR-0161 decision 13 and ADR-0162 decision 13 (line 159): the generator, the seed, the number of draws, whether two operands are drawn independently, the content of the output before the call, the `eps` the RMSNorm reference uses, the widening, and for SDPA the cache rows, guard rows and cache comparison.
- No such record exists. **This task writes its first part.**

**Scope of this record, and why it is split.**
- **In scope: four kinds** — `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. Their operands are plain bf16 arrays plus, for RMSNorm, the scalar `eps`. They differ only in the points the records left open.
- **Out of scope: RoPE and SDPA.** They are left to a second harness record.
  - RoPE takes a frequency table built outside the kernel (ADR-0161 decision 4; `hilclaw/rope_table.py`). That table depends on the RoPE scale factor, which the open owner question HQ-0070 still holds.
  - SDPA needs decisions on cache rows P … l − 1, guard rows past l and a cache comparison (ADR-0162 decision 13).
- **Also out of scope: the timing run of a bf16 kernel.** This is the counterpart of ADR-0009 and ADR-0145; how a timing run fills bf16 operands is its own record.
- If the executor finds that one record should cover RoPE or SDPA too, it does not widen the scope. It writes the point in `## Follow-ups`.

**Already fixed elsewhere** (cite these; do not re-decide them):
- **Owner, through ADR-0154 decision 3 (HQ-0066):**
  - the reference widens each bf16 input to float64 and computes in NumPy float64, with no bf16 emulation and no new dependency;
  - element-wise `rtol`/`atol` are instance parameters with no default;
  - each kind's input distribution is fixed by a driver record, with finite inputs only.
- **Owner, through ADR-0154 decision 2 (HQ-0065):** bf16 crosses the kernel boundary as `uint16_t` bit patterns.
- **The fp32 model:** ADR-0017 is the fp32 `gemm` verification run (drawn inputs from a seed parameter, regeneration on the Python side, input check value, NaN-filled output, report channel, completed/broken/pass/fail). This record may reuse its mechanism by citation. It must not change ADR-0017 or the first case.
- **Each kind's operation, precision, prototype, symbol and value set:** the contract records named above.

**Authority (DRIVER §9).** This is driver design: a context-isolated reviewer accepts it, and the owner is notified on #5 with a 7-day objection window. No owner-only point is needed, because HQ-0066 (3) hands the distribution to a driver record and (1)/(2) fix the oracle and the tolerance vocabulary. **Points the record must not decide** (leave each in Boundaries):
- tolerance values;
- where the seed comes from, and how many draws an instance uses (OD-16 sub-question 5);
- shapes outside the op_signature (OD-16 sub-question 1);
- corner-case and non-finite inputs (#5 B-7);
- build flags and OpenMP (HQ-0033, HQ-0034);
- how `correctness.check` or an instance reaches this run (OD-18, ADR-0021, ADR-0041, ADR-0048).

If the executor finds a point that would change an owner answer, it leaves it in Boundaries and writes the question in `## Result` for the driver to record as an HQ. If the record cannot be written without that point, stop with BLOCKED (`owner-only-decision`).

**PLAN order and D18.** P2 runs in list order. Unresolved HQs in `PROCESS/STATE.json` still hold the round-loop items and P2-5: HQ-0021 (round 0's board step), HQ-0048 and HQ-0024 (rounds >= 1, P2-6 and P2-7), and the gate half of P2-4, which is owner-only (OD-3). P2-10 follows P2-5. So work goes on with P2-11 to P2-14. This record is part of the P2-11 and P2-12 checklist items themselves (the harness verification and the bf16 harness), and P2-14 needs it, so the D18 rule does not apply to it.

**D16.** Nothing here starts `claude` or needs a board, a model file or an API key. Throwaway interpreter checks that change no repository file are allowed (for example, recomputing a value-set fact or a widening).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap and the naming. Branch `claude/T-0451-<slug>`; commit trailer `Task: T-0451`; doc mode, so there is no PR;
  - §9 (lines 144-152): who may close an OD, and the owner notice.
- `CLAUDE.md`, "상시 규칙": especially "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검" and "브랜치·merge 절차" (doc mode).
- `.claude/skills/dev-item-address/SKILL.md`: steps 7 and 9 to 12 (doc mode, the reviewer cycle, the 7-round limit).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: the whole file (152 lines). It is the model for structure, terms and depth, and the mechanism this record extends.
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`: decisions 2 to 7 (lines 29-88).
- `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md`: decisions 1 to 3 (lines 26-59). Read it so you can say whether its rule carries over to these kinds or stays with the first case.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: decisions 2 and 3 and Boundaries.
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`: decisions 2 to 9 (lines 37-128) and Boundaries (lines 187-201).
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`: decisions 3 to 9 (lines 44-122).
- `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`: decisions 4 to 10 (lines 49-131).
- `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`: decisions 4 to 10 (lines 50-134).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md` decision 13 (lines 130-137) and `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md` decision 13 (lines 153-160). Read only, to state precisely what the second harness record inherits.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- Read only. This is today's code of the fp32 run, which the record may reuse or depart from:
  - `hilclaw/harness/verification_program.c`, header comment (lines 1-56);
  - `hilclaw/harness/verification.py`, module docstring (lines 1-80);
  - `hilclaw/harness/verification_arrays.py` (`draw_inputs`, `check_value`, `reference`, `count_failures`, `_mix`);
  - `hilclaw/harness/verification_build.py`;
  - `hilclaw/gemm_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/elementwise_add_bf16_contract.py`, `hilclaw/swiglu_bf16_contract.py` (the `PROTOTYPE`, `INPUT_PATTERNS` / `GATE_PATTERNS` / `UP_PATTERNS` and `EPS` constants).
- `ARCHITECTURE/Requirements.md`: line 84 (the register's "행 형식"), the OD-16 row (line 107) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (the header's "기록 규칙"), § OD-16 (lines 254-278) and § OD-31 (lines 530-553).
- `ARCHITECTURE/StandardScenarios.md`:
  - lines 13-29, the check rules;
  - S0 (from line 30), S1 (from line 45) and S7 (from line 138);
  - § 검사 결과 (from line 168): its first paragraph and the S0, S1 and S7 rows.
- `PROCESS/STATE.json`: the unresolved `humanQuestions`, for the "open HQs checked" part of Status.

## Acceptance Criteria

1. **New file `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`**, in English.
   - If ADR-0163 is taken when you land, use the next free number and say so in `## Result`.
   - Use ADR-0001's "Record format" and ADR-0017's section order.
   - The title names what the record decides and the four kinds.
   - The status is "Accepted on <landing date>".
2. **Status**, with the parts ADR-0162 Status has:
   - **The kinds of content**: owner answers (through ADR-0154 and, for the fp32 model, HQ-0004 through ADR-0017), what is cited, and what is this record's own; plus the §9 objection window.
   - **The owner-sentence search** over the bodies of #4, #5, #7 and #8 and their owner comments (comments without the "posted by driver" marker).
     - Search at least these terms: verification, 검증, harness, 하네스, seed, 시드, draw, NaN, reference, oracle, tolerance, rtol, atol, 입력 분포, bf16, widen, CRC.
     - Quote what you find and state what each quote says and does not say. If nothing is found, say so.
   - **The open HQs checked and not crossed**, with the `main` commit you read. Cover at least:
     - HQ-0033 (compiler flags of `cpu_standin`): the program must stay correct under the caller's flags, as ADR-0017 decision 2 requires;
     - HQ-0034: answered (a), not yet reflected in ADR-0116. Say that this record depends on neither OpenMP nor threads;
     - HQ-0070 (the RoPE scale factor): one reason RoPE is outside this record;
     - HQ-0069 (runtime acceptance of the model executor): not touched;
     - name all the others as not touched.
   - **Not changed**: no data-plane schema, member, file, version or validator.
   - **Answers**: which parts of OD-31 sub-question 3 and of OD-16 this record answers. **Builds on**: only records cited by decision number in the body.
3. **Decision.** Settle each item below for the four kinds. Give the reason for each choice, and put the alternatives you weighed in the Alternatives table. Where a choice repeats ADR-0017, cite its decision instead of restating it.
   1. **Scope and terms.**
      - The verification run of one built attempt of a C kernel of ADR-0156, ADR-0158, ADR-0159 or ADR-0160 on `cpu_standin`.
      - Not the timing run. Not RoPE or SDPA (say which open points they bring, and that they are left to a later record). Not an FR-10 tool contract (as ADR-0017 decision 1).
      - ADR-0017 and the first case are unchanged.
   2. **Program and process.**
      - One C source per kind, or one source whose kind is chosen at build time. Weigh the four symbols, ADR-0008 decision 7's "the caller provides the program", and the cost of each choice.
      - One kernel per executable, built with `clang_build.build`, and a process of its own through `local_run.run` (cite ADR-0017 decision 2).
      - Whether the program needs `<math.h>` or `-lm`. SwiGLU kernels may use them (ADR-0160 decision 9), but the program itself computes no `exp`.
      - Say whether ADR-0107's rule carries over to these kinds, is left with the first case, or is left open.
   3. **Command line per kind**: the dimensions in the order of each prototype, `draws` and the seed, under ADR-0017's argument rules or your own.
      - **RMSNorm `eps`**: say whether the program passes `rmsnorm_bf16_contract.EPS` (the only value the Llama calls pass, ADR-0158 decision 9) as a constant of the mechanism, or takes it as an argument. Give the reason.
   4. **Drawn inputs.**
      - A deterministic generator over **each operand's value set**:
        - `gemm`: `a`, `b`;
        - `rmsnorm`: `x`, `w`;
        - `elementwise_add`: `a`, `b`;
        - `swiglu`: `gate` from the 1024-value set, `up` from the 256-value set.
      - **How an element chooses its entry of the set**, and that the choice is uniform. Both set sizes are powers of two; show the mapping.
      - **Whether two operands of one kind are drawn independently.** ADR-0159 and ADR-0160 leave this to this record, and ADR-0159 decision 10 notes that cancellation to zero needs b = −a.
      - The generator's second implementation on the Python side, and the bit-for-bit agreement of the two (as ADR-0017 decision 3). Say whether ADR-0017's integer mixing construction is reused, or whether the algorithm is the code task's and identified by its source commit.
      - Seed and `draws`: parameters of the run with no default; their source stays OD-16 sub-question 5.
      - Shapes: those the caller passes. Whether other shapes are ever passed stays OD-16 sub-question 1.
   5. **The output before the call.** Choose the content of `c`, `y`, `c` and `out` before each call (for example a bf16 NaN pattern written as bits, as ADR-0017 decision 4 does for fp32), and give its consequence for an element the kernel does not write.
   6. **The reference.**
      - Whether the Python side regenerates the inputs (ADR-0017 decision 4) and computes the reference from its own arrays.
      - The widening of a 16-bit pattern to float64 (ADR-0154 decision 3's reading), for the inputs and for the reported output.
      - The float64 formula per kind, cited to its contract record's operation decision. For SwiGLU say which float64 `exp` is used. For RMSNorm settle **the `eps` the reference uses**: the binary32 value passed, widened, or 1e-05. ADR-0158 decision 9 states their difference.
      - **The input check value**: the check function and the bytes it covers, or a reason to drop it.
   7. **The comparison**: element-wise `rtol`/`atol`, and a non-finite output fails (owner). It is done on the Python side, on the widened output, and the tolerance is not passed to the program. Use the validity rule of ADR-0017 decision 5 or your own. Add a note for whoever sets a tolerance, citing each contract record's computed facts; give no value.
   8. **The report and the verdict.**
      - The channel, and the per-draw content (check value, then the output as the bytes of its `uint16_t` elements in memory order).
      - The end mark, and a complete length that follows from the parameters alone.
      - Completed / broken / pass / fail, by citing ADR-0017 decision 7, or stating where it differs.
   9. **Calibration** (ADR-0003): how the three states apply to each of the four kinds.
      - Which hand-written fixtures the code slice's tests need, at least one conforming, one failing and one violating kernel per kind, or a reason for fewer.
      - Which wrong kernels named in the contract records' "what the set detects" serve as failing fixtures, and which of them the set cannot detect, so no test may require them to fail. Examples: the elementwise add rounding (ADR-0159 decision 10), and a single square in RMSNorm (ADR-0158 decision 9).
   10. **Parameters**, in the table form of ADR-0017 decision 9.
   11. **Limits**, as ADR-0017 decision 10, extended by what is specific to bf16 and to these kinds: what the value sets cannot detect (cite the contract records), the report size at the largest shape of each kind (computed), and one machine.
4. **Consequences**:
   - the A-13 reading;
   - for the planner, the code slices this record makes possible, without code: the program or programs, the Python-side generator, the reference and the comparison per kind, and the calibration fixtures. Note that registering a bf16 kind with `correctness.check` or with the instance start is not one of them;
   - the second harness record (RoPE, SDPA) and the bf16 timing run, named as later work;
   - **less exact, not edited**: search `ARCHITECTURE/` for at least "P2-12 harness record", "Left to the P2-12", "the harness mechanism", "for no other kind, dtype" and "verification run". List what you find, and do not claim the list is complete;
   - runtime acceptance items (expected: none);
   - the readings the owner should check, to be listed in the #5 notice (for example the operand independence, the output fill, and the RMSNorm reference `eps`);
   - the result of the UsageCases and StandardScenarios check (criterion 7).
5. **Boundaries**, covering at least:
   - tolerance values;
   - seed source, draws per instance and recording (OD-16 sub-question 5);
   - other shapes (OD-16 sub-question 1);
   - corner-case, non-finite and subnormal inputs (#5 B-7, OD-16);
   - build settings and OpenMP (HQ-0033, HQ-0034);
   - isolation of the run (OD-14; ADR-0144 for the first case);
   - RoPE and SDPA (HQ-0070 for RoPE);
   - the bf16 timing run;
   - `correctness.check`, the instance start and the spec for bf16 kinds (OD-18, OD-6, ADR-0021, ADR-0041, ADR-0048);
   - fp16;
   - backends other than `cpu_standin`;
   - any change to ADR-0017 or to a contract record.
6. **Register and proposal edits.** Read each file's own recording rule and apply it as written there. Do not reuse wording from earlier task files or commits.
   - `ARCHITECTURE/Requirements.md`, OD-31 row, and the OD-16 row if the record answers part of OD-16: follow the "행 형식" of line 84.
     - Add the one new ADR link to the confirmed part.
     - Rewrite the open part in place so that it is true after this record.
     - Do not restate the record and do not add a dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md`, § OD-31, and § OD-16 if the record answers part of it: follow the "기록 규칙" of line 8.
     - Add one adoption line for the new ADR in each section it answers.
     - Rewrite in place the status at the end of each sub-question it partly answers, and the status word at the head of that bullet.
     - No dated note and no restatement.
   - Edit no other part of these files.
7. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"):
   - Re-check S0, S1 and S7, and every scenario row that cites OD-31 sub-question 3 or OD-16, with the rules of `ARCHITECTURE/StandardScenarios.md`.
   - Update § 검사 결과 exactly as its first paragraph prescribes.
   - State the result in the ADR's Consequences.
8. **Invent nothing.**
   - No tolerance value or default.
   - No seed source and no number of draws for an instance.
   - No change to ADR-0017, to the first case or to a contract record's value set.
   - No new dependency; NumPy and the Python standard library only.
   - No fp16.
   - No build flag value.
   - No code.
   - Every number in the record is cited, or computed and shown (set sizes, mappings, report sizes, any value-set fact you add).
9. **Process**: doc mode (CLAUDE.md A-13).
   - Work on branch `claude/T-0451-<slug>`.
   - Run the context-isolated reviewer cycle (dev-item-address steps 10 to 12) until Approve, at most 7 rounds.
   - Then rebase on `origin/main` and push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0451`.
   - After landing, post the owner notice on #5 (DRIVER §9; driver footer of §8). It holds the record link, the readings for the owner to check and the 7-day objection window. Put the comment URL in `## Result`.
   - The reviewer checks at least:
     - every cited sentence against its source;
     - the four value sets and the entry mapping against the contract modules' constants (recomputed);
     - the operand-independence choice against ADR-0159 decision 10 and ADR-0160 decision 10;
     - the RMSNorm reference `eps` against ADR-0158 decision 9;
     - the calibration fixtures against what each contract record says its set detects;
     - that nothing of ADR-0017 or the first case changes;
     - that RoPE, SDPA and the timing run are left out and named;
     - the register, proposal and scenario edits against their recording rules;
     - that no owner-only point is decided.

## Out of Scope

- RoPE and SDPA verification (a second harness record), and the bf16 timing run.
- Any code: the verification programs, the Python side, the fixtures, and registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- The model executor's full pass and generation loop (ADR-0153 code slice 2).
- Tolerance values, seed source, draws per instance (OD-16 sub-question 5), other shapes (OD-16 sub-question 1), corner-case inputs (#5 B-7).
- fp16; build settings and OpenMP (HQ-0033; the HQ-0034 follow-up in PLAN "보류").
- Any edit to ADR-0017, to an earlier ADR, to `PROCESS/` (other than this file's `## Result`) or to `hilclaw/`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next toward P2-12 and P2-14: the code slices this record names (the first kind's verification program and Python side), the second harness record (RoPE, SDPA; RoPE waits on HQ-0070 only where the table's values matter), and a record of the bf16 timing run.

## Result

- **Outcome**: DONE. `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` (the number was free at landing) landed on `main` in doc mode with `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0451`; the task branch was deleted. Edited with it: the OD-16 and OD-31 rows of `ARCHITECTURE/Requirements.md` (one link each in the confirmed part; OD-31's open part ③ rewritten; OD-16's open part now names the rest of sub-question ②), § OD-16 and § OD-31 of `ARCHITECTURE/OpenDecisionProposals.md` (one adoption line each; OD-16 sub-question ② partly answered and its bullet head now 일부 답함; OD-31 ③'s status rewritten), and the "최근 재검사" line of `ARCHITECTURE/StandardScenarios.md`.
- **Decided** (driver design, §9 objection window): one verification program per kind; command lines; RMSNorm `eps` as the mechanism's binary32 constant `0x3727C5AC`; entry index = top b bits of a per-element word (b = 8 or 10) mapping onto the contract modules' tuples (checked for all 256 and 1024 indices); operands drawn independently; output filled with bf16 NaN `0x7FC0`; widening via the upper-half pattern; float64 reference per kind, the RMSNorm reference using the passed binary32 `eps`; 32-bit input check; report length draws·(4 + 2·m·n) + E; verdict as ADR-0017 decision 7; three calibration kernels per kind (bf16 `gemm` separate from fp32), with failing fixtures from each contract record's detection list.
- **Reading that differs from the task file**: the task asked to cite HQ-0070 as one reason RoPE is outside the record. ADR-0161 decision 13 builds the verification table "with the constants of decision 4 (s = 8) whatever the answer on the scale factor", so the record states that HQ-0070 bears on the model's table only and rests RoPE's exclusion on the table operand and the open T = 1 row.
- **Review**: 7 rounds (fresh-context `dev-reviewer`). Rounds 1, 2 and 6 requested changes (a wrong fixture share, the coverage rows, owner-search completeness, the `hilclaw_` linkage rule, HQ-0070, the check-value width, the reading of "as ADR-0017 decision n"); rounds 3, 4, 5 and 7 approved with nits that were addressed in rounds 3 to 6. Round 7 approved with one minor point and one nit left unfixed, because fixing them would need an eighth review round (see Follow-ups below).
- **Landed commit**: `c004ccc` on `main`. **Owner notice** (DRIVER §9): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6388472665 (7-day objection window from 2026-10-25).
- **Open HQs**: none created. No owner-only point was decided.
- **Follow-ups** (2):
  1. ADR-0163 decision 7, "Every kind" bullet: the largest relative error of a correctly rounded bf16 value is 2^−8/(1 + 2^−8) = 1/257 (about 0.00389), not 2^−8. The inference "an `rtol` below that … can fail a conforming kernel" therefore holds for an `rtol` below 1/257, not for one in [1/257, 2^−8) (round 7 reviewer, minor).
  2. ADR-0163 Alternatives, point 4 ("Index by `word mod size` or by the low bits"): the first case takes its magnitudes from `word >> 41`, not its whole value, since its sign comes from `word & 1` (round 7 reviewer, nit).
