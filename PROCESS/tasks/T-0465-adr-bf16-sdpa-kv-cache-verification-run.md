---
id: T-0465
title: Write ADR-0165, the verification run of one built bf16 SDPA-with-KV-cache kernel (kind `sdpa_kv_cache`) on `cpu_standin` (P2-12 harness record, third part; part of OD-31 sub-question 3 and of OD-16)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0459, T-0464]
touchesFiles: [ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

**State on `main` `7a54977b`.** The bf16 contract records of PLAN P2-11 leave how each kind is verified to the harness record of P2-12. Two parts of that record exist, and both have their code and calibration:
- ADR-0163 (T-0451) covers `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. Its code is T-0452 to T-0458.
- ADR-0164 (T-0459) covers `rope`. Its code is T-0460 to T-0464.

**What is missing.** Both records leave **SDPA with KV cache** out (ADR-0163 decision 1, ADR-0164 decision 1 "Not covered", and ADR-0164 Consequences "Later work"). The reason they give: the run needs cache content, guard rows past `l` and a comparison of the written cache rows, which no other kind has. ADR-0162 decision 13 fixes the value sets as an owner answer (HQ-0066 (3)). It also lists what it leaves to P2-12: "generator, seed, draws, the content of cache rows P … l − 1 and of `out` before the call, any guard rows past l, the cache comparison, the widening". Until this record exists, the kind `sdpa_kv_cache` cannot be verified, so P2-14 cannot be reached. The SDPA calls are rows 6 and 7 of every layer.

**Why a document task first.** Code for this kind needs these design choices made first. The choices are design-level parts of OD-16 and OD-31 sub-question 3. Under DRIVER §9 they close by an ADR that a reviewer approves, followed by an owner notice. The owner-only parts are already answered, and this record stays inside those answers:
- HQ-0066 (1): the float64 NumPy reference with no bf16 emulation;
- HQ-0066 (2): element-wise `rtol`/`atol`, instance parameters, no default;
- HQ-0066 (3): the value sets, as ADR-0162 decision 13 fixes them;
- HQ-0065: bf16 only, and `uint16_t` at the kernel boundary.
ADR-0154 decisions 2 and 3 record these answers. No new HQ is needed unless the executor finds a choice that only the owner can make (see criterion 9).

**PLAN order and D18.** This is the harness work of P2-11 and P2-12. Both are checklist items that P2-14 needs, so the D18 rule does not apply. The items before P2-11 in the P2 order are held by unresolved HQs:
- the round loop and P2-5: HQ-0021, HQ-0024 and HQ-0048;
- the gate half of P2-4: OD-3.
So work continues on P2-11 to P2-14, as it has since T-0451.

**D16.** This is a record, not code. Figures are computed in a throwaway interpreter in the session's scratchpad. No `claude` is started. No board, model file or API key is needed.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap and the naming;
  - §8 (lines 136-142) and §9 (lines 144-151): the HQ path and the closing of design-level ODs, including the 7-day owner notice on #5 with the driver footer;
  - for this task: branch `claude/T-0465-<slug>`, commit trailer `Task: T-0465`, document mode.
- `CLAUDE.md`, "상시 규칙":
  - "문서 커버리지 재검사";
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "개발 드라이버와 런타임의 구분";
  - "브랜치·merge 절차" (document mode: reviewer cycle, rebase, direct push to `main` with the `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in document mode.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, § "Record format" (line 146 onward).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`, the contract this record verifies. Read the whole file, closely at:
  - decisions 3 to 9 (lines 45-102): members, cache operands, other operands, operation, precision bound ε and domain D, output conversion, prototype;
  - decisions 11 and 12 (lines 133-152): guarantees and obligations at a call, kernel source;
  - decision 13 (lines 153-159): value sets, computed facts, detection shares, the cache remarks, and "Left to P2-12";
  - decision 14 (lines 161-175): the four op_signature shapes;
  - Boundaries (line 222 onward).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`, the model this record follows "as ADR-0163 decision n". Read the whole file, decisions 1 to 11 (lines 37-164).
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`, the closest precedent for form and depth. Read the whole file (163 lines), especially:
  - the Status bullets (owner-sentence search, open HQs checked, "Not changed", "Answers");
  - decision 11 (calibration: a failing fault that is outside under every tolerance a conforming kernel passes, and the list of faults no test may require to fail);
  - Consequences (code slices, "Less exact, not edited");
  - Boundaries.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`, decisions 1 to 3.
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`, decisions 2 to 7 (lines 29-88).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`, decisions 1 to 10 and Alternatives (lines 24-125).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`, decision 4: the model program's cache buffers of C ≥ l rows.
- Code at `7a54977b`, for the facts the record states:
  - `hilclaw/harness/bf16_verification.h` (185 lines);
  - `hilclaw/harness/bf16_verification_rmsnorm.c` (96 lines);
  - `hilclaw/harness/bf16_verification_arrays.py` and `hilclaw/harness/bf16_verification.py`;
  - `hilclaw/harness/bf16_verification_build.py`;
  - `hilclaw/sdpa_kv_cache_bf16_contract.py` (216 lines): the value set and the contract constants of ADR-0162.
- The registers and their recording rules:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the rows OD-16 (line 107) and OD-31 (line 122);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" header bullet (line 8), § OD-16 (lines 254-280) and § OD-31 (lines 532-557);
  - `ARCHITECTURE/StandardScenarios.md`: the check rules near line 26, and § 검사 결과 from line 168, whose first paragraph is the recording rule, plus the S0, S1, S7 and S8 rows.
- `PROCESS/STATE.json`, `humanQuestions`: the unresolved entries, for the "Open HQs checked" bullet.

## Acceptance Criteria

1. **One new record** `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md`, in the ADR-0001 record format, in English, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries and References. If the number 0165 is taken on `main` when the executor starts, it takes the next free number and says so in `## Result`.
   - **Status** follows ADR-0164's bullets:
     - the three kinds of content (owner, cited, this record's own) and the DRIVER §9 acceptance with the 7-day objection window;
     - an owner-sentence search over #4, #5 (comments without the driver marker), #7 and #8. Give the terms searched (at least SDPA, attention, softmax, KV cache, cache, 캐시, causal, mask, GQA, verification, 검증, harness, 하네스, seed, reference, tolerance, bf16), what was found, and any conflict;
     - the open HQs checked and whether each is crossed. At least HQ-0070, HQ-0033 (the kernel may call `expf`; linking the math library is a build setting of the caller, ADR-0162 decision 12) and HQ-0069;
     - "Not changed": no data-plane schema, and no `claude` started;
     - the parts of OD-31 sub-question 3 and of OD-16 it answers, with what stays open.
2. **The Decision decides, for `sdpa_kv_cache` in bf16 on `cpu_standin`, every item that ADR-0162 decision 13 leaves to P2-12, plus what a verification run needs besides.** For each choice, give the reason and the rejected alternatives. Where a point equals ADR-0163, write "as ADR-0163 decision n" and do not restate it. At least:
   - **Program and process**: a sixth verification program under `hilclaw/harness/` calling `hilclaw_sdpa_kv_cache_bf16` (ADR-0162 decision 9), or the reason for another arrangement. Say whether ADR-0017's no-standard-input rule holds here. ADR-0164 departed from it for `rope` only, and here every input can be drawn.
   - **Command line**: the arguments and their order (for example `<m> <l> <h> <h_kv> <d> <draws> <seed>`), and the checks: `l ≥ m`, `h` a multiple of `h_kv`, each ≥ 1. P = l − m stays derived (ADR-0162 decision 3).
   - **Drawn inputs**: the generator mapping for `q`, `k_new`, `v_new` and cache rows 0 … P − 1 over the value set of ADR-0162 decision 13, and one sequence order over the operands.
   - **The buffers and their content before each call**:
     - the content of cache rows P … l − 1 (unspecified on entry, ADR-0162 decision 11; whether the harness fills them so that a read-before-write shows);
     - `out` (as ADR-0163 decision 5 or otherwise);
     - whether the harness allocates guard rows past row l − 1, how many, what they hold, and whether that content would change the output if a kernel attended to or wrote those rows. ADR-0162 decision 13 says attention past l "shows only through what the harness places there".
   - **The cache comparison**:
     - which rows are compared after the call: P … l − 1 against `k_new`/`v_new` bit for bit; rows 0 … P − 1 unchanged; the guard rows unchanged;
     - how the result reaches the Python side (in the report or otherwise), and the report's size formula;
     - whether a mismatch is a fail or a broken run, kept consistent with ADR-0017 decision 7 and ADR-0163 decision 8 (a harness defect is never a fail; a kernel defect is never broken).
   - **Widening and the reference**, owner HQ-0066 (1): float64 NumPy on the widened arrays, the GQA mapping, the causal rule and the scale 1/√d of ADR-0162 decision 6. State how the reference is evaluated so that its own error stays negligible against ε (ADR-0162 decision 13 measured 7.9·10^−17·Σ p·|V|). Give its memory and time at the largest shape (m = l = 2048, h = 32, d = 64), computed. A full float64 score array at that shape is about 1 GiB, so say whether the reference is evaluated per head or per block.
   - **The input check value**: as ADR-0163 decision 6, over which byte ranges, including the cache rows the kernel receives.
   - **The comparison and the verdict**, as ADR-0163 decisions 7 and 8. Add a short "for whoever sets a tolerance" note with no value and no default, as ADR-0164 decision 10 does. It gives an absolute bound that every compliant output meets, derived from ε and D of ADR-0162 decision 7 and the round-to-nearest-even output. It also says that an `rtol` with `atol` = 0 can fail a conforming kernel (the cancellation figures of ADR-0162 decision 13). Computed figures are labelled as computed.
   - **Calibration**, ADR-0003 as ADR-0163 decision 9 and ADR-0164 decision 11 apply it:
     - three kernels: conforming, violating (V1) and failing;
     - the failing fault, chosen so that the record can show it is outside under every tolerance a conforming kernel passes with some margin, or that the two ranges meet. For example a fault that is outside on every seed at a chosen shape, as ADR-0164 used row 0. ADR-0162 decision 13's detection shares are candidates (no scale, no normalisation, a wrong GQA mapping that never moves heads 0, 10, 21 and 31). Name the shape and P the functional test uses;
     - whether a cache fault (a wrong write position, or no write) gets its own required case or is left to the cache comparison;
     - the list of faults no test may require to fail: at least Meta's probability rounding (ADR-0162 decision 7), blocked or online orders, fused multiply-adds, the sign of a zero, and errors of the binding.
   - **Parameters** (table as ADR-0164 decision 12): who gives each value, which have no default, and the mechanism's constants.
   - **Limits**: as ADR-0163 decision 11; what the set cannot detect; the computed cost at the largest shape (report bytes per draw, runner memory, reference time); and that the Python side is bounded by nothing here (OD-14).
3. **No invented values.** The record names no tolerance value or default (owner, HQ-0066 (2)). It names no default seed, draws, shapes beyond the op_signature shapes, cache capacity of the model program, build flags or time limits. These go in Boundaries with their OD or HQ (OD-16 sub-questions ①, ⑤ and ⑥; OD-14; HQ-0033; #5 B-7 for zero, subnormal and non-finite inputs).
4. **Consequences**:
   - the A-13 reading (document mode);
   - the code slices the record makes possible, for the planner, each within 300 LOC and 5 files excluding tests, in landing order. For example: program; arrays and reference; runner and judge; calibration kernels. Registering `sdpa_kv_cache` with `correctness.check`, `spec.write` or the instance start is not one of them;
   - runtime acceptance items: expected none. If one appears, name it, and `## Result` reports it so that the driver records an HQ with reason `runtime-acceptance`;
   - the readings for the owner to check, listed in the #5 notice;
   - "Later work" (the bf16 timing run);
   - a "Less exact, not edited" list from a search of `ARCHITECTURE/`. At least ADR-0162 decision 13 "Left to P2-12" and its Boundaries, and the SDPA parts of ADR-0163 decision 1, Consequences and Boundaries, and of ADR-0164 decision 1 and Boundaries. These are listed, not edited.
5. **Register edits, by the recording rules in the files and not by imitation of earlier tasks**:
   - `ARCHITECTURE/Requirements.md`, rows OD-16 and OD-31: follow the "행 형식" paragraph (line 84). Add exactly one link to the new ADR after `**확정분**:` with a few words of topic. Rewrite `**잔여**:` in place, only if this record changes what is open. Do not restate the record and add no dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md`, § OD-16 and § OD-31: follow the "기록 규칙" header bullet (line 8). Add one `- **채택분**` line per section for the new ADR. Rewrite the end status and the head status word of each sub-question it answers, in place (`→ 부분 답: …. 남음: …` / `→ 답함: …`). Keep the question text, add no dated paragraph, and copy nothing from the register row.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage (CLAUDE.md "문서 커버리지 재검사") and record it by the first paragraph of § 검사 결과. Update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a verdict changes or a gap appears or closes. Add no ADR summary.
6. **Nothing else changes**: no code, test, workflow, `pyproject.toml`, `PROCESS/` file (except this task file's `## Result`), `CLAUDE.md`, `.claude/` file or accepted ADR. Figures are computed in a throwaway interpreter outside the repository. The size stays at 4 files.
7. **Process**: document mode (CLAUDE.md A-13).
   - Run the context-isolated reviewer cycle (dev-code-review), at most 7 rounds.
   - On Approve, rebase on `origin/main` and push directly to `main`. The commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0465`.
   - Then post the DRIVER §9 owner notice on #5. It names the record and the readings for the owner to check, ends with `— posted by driver`, and its URL goes in `## Result`.
   - The reviewer checks at least:
     - every item of ADR-0162 decision 13's "Left to P2-12" is decided or put in Boundaries with its OD;
     - owner sentences match HQ-0065 and HQ-0066 as ADR-0154 renders them;
     - no tolerance value, default or other undecided value is invented;
     - the failing kernel's argument holds (recompute the figures);
     - the verdict classes keep a harness defect out of "fail";
     - the register edits follow the three recording rules.
8. **`## Result`**: the commit, the review rounds, the #5 notice URL, the code slices with a proposed first slice for the planner, and any follow-up. Wording follow-ups that neither P2-5 nor P2-14 needs are listed as such, so that the planner can defer them (D18).
9. **Stop rule.** Stop and return BLOCKED (`requirement-unclear` or the DRIVER §3 OD reason) with a question in Korean for the driver's HQ in these cases:
   - a choice turns out to need an owner-only decision (#5 A/B items, C-6, OD-25, OD-3), for example a tolerance-like value the mechanism cannot avoid;
   - the value set of ADR-0162 decision 13 cannot serve a needed part of the run, for example guard-row content.
   Do not decide such a choice in the record.

## Out of Scope

- Any code: the program, the arrays, the runner, the calibration kernels (later code slices).
- The bf16 timing run, and whether ADR-0107's rule extends to it (OD-16 sub-question ⑥).
- Registering `sdpa_kv_cache` with `correctness.check`, `spec.write` or the instance start (OD-18, OD-6).
- The model executor's SDPA call site, cache buffers and capacity (ADR-0153, P2-13).
- The RoPE scale factor (HQ-0070), the model-level comparison and Meta's probability rounding at model level (OD-31 sub-questions 5 and 6, owner).
- fp16; backends other than `cpu_standin`; tolerance values or defaults.
- Editing ADR-0162, ADR-0163, ADR-0164 or another accepted record.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this record lands, plan its code slices in the order its Consequences give, as ADR-0164 was followed by T-0460 to T-0464.

## Result
