---
id: T-0459
title: Write ADR-0164 - the verification run of one built bf16 RoPE kernel (kind rope) on cpu_standin (program, command line, how the frequency table rows reach the program, which rows a draw uses, generator for x, output fill, float64 reference, input check, report, comparison, verdict, calibration, parameters, limits), and update the OD-16, OD-31 and StandardScenarios records (P2-12 harness record, second part; part of OD-31 sub-question 3 and of OD-16)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0444, T-0446, T-0451]
touchesFiles: [ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 250, files: 4}
hq: []
---
## Why

PLAN P2-11 asks for a kernel contract, an op_signature and a **harness verification** for every operation kind the Llama 3.2 1B forward pass needs, and P2-12 for the bf16 harness itself; both lie on the path to the reach goal P2-14 (D18). ADR-0163 (landed as `c004ccc`, all seven of its code slices landed by T-0452..T-0458) gave the verification run to four kinds (`gemm`, `rmsnorm`, `elementwise_add`, `swiglu`) and left RoPE and SDPA with KV cache to a later harness record (ADR-0163 decision 1, "Not covered"; Boundaries). ADR-0161 decision 13 fixed RoPE's verification value sets and left to the P2-12 harness record the generator, the seed, the draws, which T = 1 row a draw uses, the content of `out` before the call and the widening.

This task writes that record for **RoPE only**. SDPA with KV cache needs cache rows, guard rows and a cache comparison (ADR-0162 decision 13) and is left to the next record, so that each record stays reviewable (ADR-0163 needed 7 review rounds for four simpler kinds). The new design question RoPE brings is its second operand: `freqs_cis` is not drawn from a value set but is rows of a table built outside the kernel by the host side (ADR-0161 decisions 4 and 13; `hilclaw/rope_table.py`), while ADR-0163 decision 2 says a verification program does no floating-point arithmetic and ADR-0017 decision 9 says the first case's program reads only its command line.

This is a design-level part of OD-31 sub-question 3 and of OD-16, so it is closed by an executor ADR, reviewer Approve and an owner notice (DRIVER §9, D6). The owner answers it rests on (HQ-0065, HQ-0066, through ADR-0154) are already given. **HQ-0070** (RoPE scale factor 8 vs 32) is open and must not be crossed: ADR-0161 decision 13 builds the verification table with s = 8 whatever the answer, because the kernel's verification needs angles, not the model's values.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, time limit) and §5 (task file format, naming convention, size cap), §9 (OD closing authority and the owner notice).
- `CLAUDE.md` (all; in particular "미결은 발명하지 않는다", "문서 커버리지 재검사", the A-13 branch/merge procedure for document mode, "개발 드라이버와 런타임의 구분").
- `.claude/skills/dev-item-address/SKILL.md` (document-mode path, steps 4 and 9-13).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` (all) — the record this one follows; reuse its mechanism by citing "as ADR-0163 decision n" with stated substitutions rather than restating it.
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md` — Status, decisions 3 to 13 (lines 33-137), Boundaries (lines 195-207).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md` — decisions 2, 3, 4, 7, 9 and 10 (lines 30-108), Alternatives.
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md` — decisions 2 to 7.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md` — decisions 1 to 3 (the T = 1 positions 127 and 2047 come from decision 1's table, RoPE row).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md` — decision 13 only, to state why SDPA stays outside.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` — "Record format" (line 146 on).
- `hilclaw/rope_table.py` (module docstring and `build`, lines 1-160) and `hilclaw/rope_bf16_contract.py` (`PROTOTYPE`, `SHAPES`, `X_PATTERNS`).
- `hilclaw/harness/bf16_verification.h`, `hilclaw/harness/bf16_verification_arrays.py`, `hilclaw/harness/bf16_verification.py`, `hilclaw/harness/bf16_verification_build.py` — what ADR-0163's code slices built (read to state which parts a RoPE code slice reuses; do not change them).
- `ARCHITECTURE/Requirements.md` — "행 형식" (line 84) and the OD-16 and OD-31 register rows.
- `ARCHITECTURE/OpenDecisionProposals.md` — the header's "기록 규칙" (line 8), § OD-16 (line 254 on) and § OD-31 (line 531 on).
- `ARCHITECTURE/StandardScenarios.md` — the check rules near line 26 and the first paragraph of §검사 결과 (line 168 on); S0, S1, S7, S8.
- `PROCESS/STATE.json` — `humanQuestions`, in particular HQ-0065, HQ-0066, HQ-0070 and every unresolved entry (to list the open HQs checked and not crossed).

## Acceptance Criteria

1. **One new record** `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md` (renumber if 0164 is taken at landing, and keep every link consistent) in the ADR-0001 "Record format", accepted under DRIVER §9. Its Status separates owner answers (marked owner, cited through ADR-0154 or ADR-0017), cited statements of accepted records (each with record and decision) and the record's own sentences, as ADR-0163 Status does.
2. **Owner-sentence search** before writing: the bodies and comments of issues #4, #5 (comments without a "posted by driver" marker), #7 and #8, for terms on the subject (at least RoPE, rotary, freqs, cos/sin, position, verification/검증, harness/하네스, seed/시드, reference, tolerance, bf16, table). The record lists what it found and read, and any conflict. If an owner sentence conflicts with a decision the record would make, do not decide it: stop and report BLOCKED (requirement unclear / invention suspected).
3. **Open HQs checked and not crossed** are listed with one reason each; HQ-0070 in particular: no scale factor is chosen for the model, and the verification table uses the constants ADR-0161 decision 13 names.
4. **The record decides, with reasons and with the rejected alternatives in its Alternatives table**, each of the following for kind `rope`, bf16, `cpu_standin`. The task fixes none of these answers; any that cannot be decided from accepted records and design reasoning alone, or that would need an owner-only decision (DRIVER §9: #5 A/B items, C-6), is left in Boundaries or raised as a BLOCKED concern, not invented:
   1. **Program and process**: a fifth verification program calling `hilclaw_rope_bf16`, whether "as ADR-0163 decision 2" holds for it (one kernel per executable, own process, internal linkage, no floating-point arithmetic in the program) and what changes.
   2. **How the `freqs_cis` rows reach the kernel.** Weigh at least: the table bytes over standard input; a file the harness writes; a generated C source or header of the needed rows built into the executable (against ADR-0163 decision 2's "the harness adds no flag" and one build call); the command line (state its size at the largest shape); computing entries inside the program (against the no-floating-point rule and ADR-0161 decision 4's correctly rounded entries). If the choice departs from ADR-0017 decision 9's "no standard input, no file and no environment variable", say so, limit the departure to this kind and give the reason. Whatever the channel, the reference must not rest on bytes coming from the kernel's process (ADR-0017 Alternatives, as ADR-0163 decision 6 carries it).
   3. **Which table rows a draw uses**: rows 0 … m−1 for prefill and row 127 or 2047 for T = 1 (ADR-0161 decision 13; ADR-0154 decision 1), and what happens for a caller's m outside {1, 128, 2048} — whether the start position P is a run parameter, a function of the seed and draw, or fixed, and the bound P + m ≤ the table's positions. State the table's constants (ADR-0161 decision 4, s = 8) and what is done when the caller's `d` is not 64 (refuse, or build the table for that `d` with the same constants — decide and give the reason).
   4. **Building the table on the Python side**: that `hilclaw.rope_table.build` (or its rows) is the source, and its cost at the largest number of rows a run uses — compute it in a throwaway interpreter that changes no repository file, and state the figure with the machine and versions; whether it is built once per run.
   5. **Generator for `x`**: the element-to-entry mapping of ADR-0163 decision 4 (b = 8) over `rope_bf16_contract.X_PATTERNS`, the element order, the words "as ADR-0163 decision 4"; the table is not drawn.
   6. **Command line** in the form of ADR-0163 decision 3's table (dimensions in prototype order `m`, `h`, `d`, then `draws`, seed, and whatever item 2 and 3 add).
   7. **Output before the call**: as ADR-0163 decision 5 or otherwise, with reason (ADR-0161 decision 11 "Output" row).
   8. **Reference**: widening of `x` as ADR-0163 decision 6 and of the binary32 table entries to float64 (exact), and y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c in NumPy float64 (owner, HQ-0066 (1); ADR-0161 decision 7; its error figure in ADR-0161 decision 13).
   9. **Input check value**: which bytes it covers (at least `x`; whether the table rows as the kernel receives them are covered too, given item 2's channel), its order and width, and that a disagreement makes the run broken, never a fail.
   10. **Comparison, report and verdict**: as ADR-0163 decisions 7 and 8 with RoPE's substitutions — the report length draws · (4 + 2·m·h·d) + E — and the RoPE notes for whoever sets a tolerance (cancellation: ADR-0161 decision 13's relative 457 at the smallest outputs, so `rtol` alone can fail a conforming kernel).
   11. **Calibration** (ADR-0003 per kind): three hand-written kernels — conforming, violating (V1), failing — where the failing kernel is chosen from what ADR-0161 decision 13 says the set detects, with the reason it lies outside every tolerance under which the conforming kernel passes in the functional test (detection there is a share of cases, so say what the functional test's shape and seed must ensure). List what no test may require to fail (at least: a bf16-rounded table, truncation in place of RNE, and anything else ADR-0161 decisions 7, 8 and 13 say is compliant or undetectable).
   12. **Parameters** table and **Limits**, including the cost at the largest shape (T = 2048, h = 32, d = 64) for the report and the Python side.
5. **Scope statements**: SDPA with KV cache is outside, with the reason (ADR-0162 decision 13) and that a later record covers it; the bf16 timing run and ADR-0107's rule stay outside as in ADR-0163 decision 2; ADR-0017, ADR-0163, ADR-0161 and every other accepted record are not edited; registering `rope` with `correctness.check`, `spec.write` or the instance start is Boundaries.
6. **Consequences** list the code slices this record makes possible (for the planner; each ≤ 300 LOC and ≤ 5 files excluding tests), any runtime acceptance items (expected: none — if one is found, name it for a `runtime-acceptance` HQ), the readings for the owner to check in the #5 notice, and a "less exact, not edited" list found by a search of `ARCHITECTURE/` (at least ADR-0161 decision 13's "Left to P2-12" and its Boundaries "The harness mechanism", and ADR-0163's "a second harness record" sentences, now that RoPE has its record and SDPA does not).
7. **`ARCHITECTURE/Requirements.md`**: the OD-16 and OD-31 rows follow the register's "행 형식" (line 84): one link to the new ADR added to the confirmed part of each, the open part rewritten in place, no restatement of the record and no dated chain.
8. **`ARCHITECTURE/OpenDecisionProposals.md`**: § OD-16 and § OD-31 follow the header's "기록 규칙" (line 8): one adopted-ADR line each, and the status at the end of each sub-question the record answers in part (OD-31 ③; OD-16 ② and any other it touches) rewritten in place; no dated paragraph, nothing copied from the register.
9. **`ARCHITECTURE/StandardScenarios.md`**: re-check the coverage under its check rules (S0, S1, S7, S8 and every row citing OD-31 sub-question 3 or OD-16) and update §검사 결과 as its first paragraph prescribes (the "최근 재검사" line in place; a history entry only if a verdict or gap changes).
10. **Document mode** (CLAUDE.md A-13): a context-isolated reviewer cycle (dev-item-address 10-12) reaches Approve within 7 rounds; rebase on `origin/main`, push to `main` directly with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0459` trailers; delete the task branch. Then post the owner notice on #5 (DRIVER §9; last line `— posted by driver`) naming the record and the readings of item 6, and record its URL in Result.
11. **D16**: no `claude` process is started; no runtime-only resource is used; every computed figure in the record comes from a throwaway interpreter that changes no repository file, and the record says so.
12. Diff stays within the touched files above, ≤ 300 changed lines.

## Out of Scope

- Any code, C file, test, CI or schema change (the record's code slices are later tasks).
- SDPA with KV cache verification; the bf16 timing run; fp16; backends other than `cpu_standin`.
- Choosing the model's RoPE scale factor (HQ-0070), tolerance values or defaults (owner, HQ-0066 (2)), seed source and number of draws (OD-16 sub-question ⑤), other shapes (OD-16 sub-question ①), corner-case inputs (#5 B-7).
- Editing ADR-0017, ADR-0161, ADR-0163 or any other accepted record, including the ADR-0163 wording follow-ups already held in PLAN's 보류 section.
- Editing `PROCESS/PLAN.md` or `PROCESS/STATE.json` (the driver does).

## Follow-ups

(executor fills)

## Result

(executor fills: commit, review rounds, owner-notice URL, follow-ups)
