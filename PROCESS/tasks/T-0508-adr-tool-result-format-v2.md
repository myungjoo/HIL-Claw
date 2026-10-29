---
id: T-0508
title: Write the v2 record — one result format for correctness.check, sim.run and board.run (owner HQ-0078), its step values and the code slices that migrate fp32 gemm and the bf16 checks (part of OD-18 sub-question ⑩ and OD-8)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-9, FR-10, NFR-1, OD-8, OD-18, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md
  - ARCHITECTURE/StepValues.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 340, files: 5}   # ADR ~280 lines, StepValues ~10, registers ~30, StandardScenarios ~10. The ADR number and file name are a suggestion (next free number after ADR-0182; check `ARCHITECTURE/decisions/` at start).
hq: []
---
## Why

**State.** PLAN P2-14 (Llama 3.2 1B end-to-end, the D18 goal) needs every bf16 contract of P2-11 admitted by the instance start, which takes a contract's table entry to be both `checked` and `timed` (ADR-0177 decision 2). All six bf16 entries are `checked`; none is `timed`. ADR-0181 (T-0505, `main` `9e806a46`) defines the bf16 timing run, but its decision 7 leaves the **result** of that run to a separate record, and its decision 8 item 0 puts that record first: "the v2 record (a document task), then its code for `correctness.check` and for `sim.run` / `board.run`, fp32 `gemm` and the bf16 checks migrated. The v2 record lists and sizes those slices; this record does not." This task writes that record.

**The owner's answer this record implements** (HQ-0078 in `PROCESS/STATE.json`, resolved 2026-10-29; quoted in ADR-0181 Context): one v2 result format for `correctness.check` and `sim.run` / `board.run`. ① Both tools, fp32 `gemm` migrated too; the step values `correctness_check_sim`, `correctness_check_board`, `correctness_check_bf16_sim`, `correctness_check_bf16_board`, `sim_run_timing`, `board_run_timing` are retired and never reused; one new `step` value per tool and point (no stored run data exists yet). ② A member with the contract table's key (kind, dtype, layout). ③ `shape` = all shape members of the kind. ④ `counts` = one entry per output or inout operand of the contract, `failed` and `non_finite` for an operand judged by tolerance, `differs` for one judged bit-exact (replacing HQ-0077's `cache_differs`). ⑤ The measured values of `sim.run` / `board.run` carry a unit member whose only value for now is `ns` (an open list of units is the owner's, later). Other members carried over; "멤버 이름·철자와 세부는 ADR이 정한다". Order: the v2 ADR and both tools' code land before any bf16 timing slice.

**Why a document-only task (DRIVER §6 "task 단위" ①, ③).** ADR-0181 decision 8 calls it a document task. The record touches five documents; its code (the check result builder and identity, the run result builder and identity, the build-log file names of `hilclaw/layout.py`, and every reader of check and run lines) spans well over ten files, so the record plus even its first code slice exceeds DRIVER §5's cap of 10 files. The code slices are therefore planned after this record lands, from its slice list; they are not created now because their content depends on spellings this record has not yet fixed (§6 "task 단위" ④). ADR-0181's own slices 1–4 wait behind those code slices (owner order, HQ-0078).

**PLAN order and D18.** P2-11 and P2-14 are PLAN checklist items, so D18 does not apply. P2-10 waits on HQ-0076 (T-0493). `PROCESS/RuntimeAcceptance.md` has no `실패` item as of `main` `cf7b0585`. No PR is open.

**D16.** A record; nothing is built or run.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §3 "승인된 열린 목록" (D23 — what is and is not a data-plane schema change; the kernel contract table as an open list), §5 (task format, naming `claude/T-0508-<slug>`, `Task: T-0508` trailer, size cap), §8 (HQ format, runtime acceptance items, D22), §9 (OD closing: ADR + reviewer Approve + owner notice on #5).
- `CLAUDE.md` (rules; "미결은 발명하지 않는다"; "세션 진입 점검"; A-13 doc mode and BLOCKED reasons).
- `PROCESS/STATE.json` HQ-0077 and HQ-0078 (questions and owner answers, verbatim).
- `PROCESS/tasks/T-0505-adr-bf16-timing-run.md` (Result) and `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md` (Status, Context, decisions 4, 7, 8, A-13 reading, Boundaries "The v2 record's") — what this record must decide and must not decide.
- Result definitions being replaced: `ADR-0042-od18-correctness-check-result-members.md` (all; decision 7 member list), `ADR-0063-od18-run-tools-result-members.md` (all; decision 9 member list, A-13 reading), `ADR-0177-od18-od6-contract-table.md` decisions 1–3 (contract key, `task_contract`, the bf16 check's step values and result under HQ-0077, around line 75), `ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md` decision 8 (the cache comparison — the bit-exact operands), `ADR-0002-od6-codegen-spec.md` decision 6 (operand roles `input`/`output`/`inout`).
- Step values and result changes: `ADR-0040-od18-correctness-check-call-identity.md` decision 3, `ADR-0062-od18-run-tools-call-identity.md` decision 3, `ADR-0100-od8-tool-result-change.md` decisions 3–5, `ADR-0101-od8-failure-kind-change-and-step-values.md` decisions 7–8, `ARCHITECTURE/StepValues.md` (all; note it has no rows for `correctness_check_bf16_sim` / `correctness_check_bf16_board`).
- Build-log file names that embed step values: `ADR-0078-od18-correctness-check-compiler-log-file.md` decision 3, `ADR-0108-od18-run-tools-timing-build-compiler-log.md` decision 3.
- Readers of check and run lines (to list the slices, not to edit): `ADR-0104-od13-imprecise-timing-mark.md`, `ADR-0110-od18-check-executions-hard-floor.md`, `ADR-0131-od23-attempt-check-results-read.md`, `ADR-0140-od16-first-case-attempt-comparison.md`, `ADR-0178-od23-bf16-check-lines-read.md`.
- Registers: `ARCHITECTURE/Requirements.md` the "행 형식" paragraph (line ~84) and rows OD-8 (~99), OD-18 (~109), OD-31 (~122); `ARCHITECTURE/OpenDecisionProposals.md` the header's "기록 규칙" (line ~8), § OD-8 (~98; sub-questions ㉟, ㊱ at ~168), § OD-18 (~304; sub-question ⑩); `ARCHITECTURE/StandardScenarios.md` the first paragraph of § 검사 결과 (line ~168) and rows S0, S1.
- Code, read only (for the slice list and sizes): `hilclaw/check_identity.py`, `hilclaw/check_result.py`, `hilclaw/check_tool.py`, `hilclaw/check_standing.py`, `hilclaw/checks_tool.py`, `hilclaw/run_identity.py`, `hilclaw/run_result.py`, `hilclaw/run_tool.py`, `hilclaw/layout.py` (`BUILD_LOG_STEPS`, `build_log_file`), `hilclaw/timings_tool.py`, `hilclaw/verdicts_tool.py`, `hilclaw/spec_feedback.py`, `hilclaw/contract_table.py`, `orchestration/agents/evaluator.md`; search `hilclaw/`, `orchestration/` and `tests/` for the six retired step values and for the result member names to find every reader.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): before editing `ARCHITECTURE/`, check open PRs, Issues #4/#5/#7/#8 and the unresolved `humanQuestions` of `PROCESS/STATE.json` (HQ-0076 concerns P2-10 and is not crossed). Name in the ADR's Status what was checked.
2. **ADR** at `ARCHITECTURE/decisions/ADR-0183-<slug>.md` (next free number), in the form of recent ADRs (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References), separating **owner** content (HQ-0078, cited) from the record's own. It decides, for `correctness.check`, `sim.run` and `board.run` at every target the code serves today (`cpu_standin`, the mock):
   - (a) **The new `step` values**: one per tool and point (four in all), spelled as ADR-0001 *names* not used anywhere in `hilclaw/`, `tests/` and `ARCHITECTURE/` (StepValues "Adding a row"); the same value for fp32 `gemm` and every bf16 kind. State how a call chooses its value (no dtype chooses it — ADR-0181 decision 4), replacing the read of ⓢ of ADR-0177 decision 3.
   - (b) **The v2 member list of each tool's result**, written once as a table like ADR-0042 decision 7 and ADR-0063 decision 9: the contract-key member and its form (HQ-0078 ②), `shape` (③), `counts` per output/inout operand name and which operands of which contract are judged bit-exact (`differs`) vs. by tolerance (`failed`, `non_finite`) (④; the `sdpa_kv_cache` caches per ADR-0165 decision 8, `out` and every other operand by tolerance unless a record says otherwise), the unit member of the measured values of `sim.run` / `board.run` and which members it applies to (⑤; value `ns` only), and every other member of ADR-0042 and ADR-0063 carried over unchanged in meaning (name changes only where ⑤ or the key member requires them, each justified).
   - (c) **What the result of each broken or tool-failure path holds** under v2 (the members present when no shape or contract is known, e.g. `op_signature_not_covered`), so the code slices do not have to decide it.
   - (d) **The build-log file names** (ADR-0078 decision 3, ADR-0108 decision 3) under the new step values.
   - (e) **The readers**: which tools and prompts read check or run lines and what each reads under v2 (at least the `timings` reader, `checks`/`verdicts` readers, `check_standing`, `spec_feedback`, the hard floor of ADR-0110 and ADR-0178, the comparison of ADR-0140, the evaluator prompt); whether any reader keeps accepting the retired values (no stored run data exists — HQ-0078 ①).
   - (f) **The code slices**, in landing order, each sized to DRIVER §5's cap (≤ 600 LOC excluding tests, ≤ 10 files), for the planner — at least: the `correctness.check` v2 (fp32 `gemm` and bf16 checks), the `sim.run` / `board.run` v2 (fp32 `gemm`), the readers; and where ADR-0181 decision 8 items 1–4 then start.
   Decide nothing owner-only (#5 A/B, C-6, OD-25, OD-3): no unit value beyond `ns`, no open list of units, no tolerance, seed, draw count or `n_min`/`cv_max`; no change to the owner's ①–⑤.
3. **A-13 reading** (D23, DRIVER §3 "승인된 열린 목록"): the frame change is the owner's (HQ-0078); name what the record itself adds to the frame beyond ①–⑤ (if anything) and why it is within "멤버 이름·철자와 세부는 ADR이 정한다", and which values enter members defined as "what the contract fixes" (approved open list "kernel contract table"). **Stop rule**: if a point needs a frame choice the owner's answer does not cover and the "details" clause cannot honestly carry (for example a new member of a meaning ①–⑤ do not name, or a closed value list widened), stop as BLOCKED (`data-plane-schema-change`) with a Korean question in the HQ-0078 form (쟁점, options (a)/(b)/…, what it blocks — the v2 code slices, ADR-0181's slices, P2-14's instance start — and what it does not), after pushing the branch with the draft so the resume can continue it. Any other owner-only point (DRIVER §9) is handled the same way.
4. **`ARCHITECTURE/StepValues.md`**: add the four new rows (state `defined`, fixed by this ADR) per the file's "Adding a row" rule; set the rows of the retired values to `not used` linking this ADR (the file's "States"); the two bf16 check values fixed by ADR-0177 decision 3 have no row today — add their rows (fixed by ADR-0177 decision 3) with state `not used` linking this ADR, so the list holds every value records have fixed. No row is removed and no value changes.
5. **Register edits** follow the recording rules written in those files — not earlier task files: `Requirements.md` rows of the ODs the ADR answers part of (at least OD-18 and OD-8) per its "행 형식" paragraph (one link for the new ADR in `**확정분**:`, `**잔여**:` rewritten in place, no restatement of the record, no dated paragraph); `OpenDecisionProposals.md` per its header's "기록 규칙" (one `채택분` line per section the ADR answers, the status at the end of each sub-question it answers rewritten in place, the bullet head's status word updated); `StandardScenarios.md` § 검사 결과 per its first paragraph (CLAUDE.md "문서 커버리지 재검사"), S0 and S1 at least.
6. **Less exact sentences**: list in Consequences the sentences of earlier records, prompts and docstrings that v2 makes less exact (at least ADR-0040 decision 3, ADR-0042 decision 7, ADR-0062 decision 3, ADR-0063 decisions 5 and 9, ADR-0177 decision 3, ADR-0178, ADR-0181 decision 7's "until the v2 record", and the `hilclaw/` docstrings naming retired values — the code slices will fix the docstrings they touch); do not edit them.
7. **Runtime acceptance items**: state whether any fact of this record can only be established at runtime (D16); hand any to `PROCESS/RuntimeAcceptance.md` (D22) through Result. None is expected.
8. **Review and landing** (doc mode, CLAUDE.md A-13): context-isolated reviewer cycle (dev-item-address steps 10–12), rebase on `origin/main`, direct push to `main` with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0508`.
9. **Owner notice** (DRIVER §9): after landing, one comment on Issue #5 announcing the ADR, the OD rows it changes, the chosen spellings and the readings for the owner to check, ending with `— posted by driver`; record the URL in Result.
10. **Result** names: the commit, review rounds, the decisions in one line each, the HQ raised if any, runtime acceptance items if any, and the planner's next candidates (the first code slices of criterion 2 (f), with their expected files).

## Out of Scope

- Any code under `hilclaw/`, `tests/`, `orchestration/` or `catalog/` (the code slices follow in later tasks after this record lands).
- ADR-0181's slices 1–4 (bf16 timing programs, run tools for bf16, `cpu_standin` operation, `timed` flags).
- Any edit of an accepted ADR's text (list them under criterion 6 instead); any deferred line of PLAN "보류"; fp16 (after P2-14, HQ-0065 (1)); OpenMP (HQ-0034); targets other than `cpu_standin` and the mock (#5 B-2, B-7); the open list of units (owner).
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result

- **DONE.** ADR-0183 (`ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`) landed on `main` in doc mode as the commit with trailer `Task: T-0508` (`git log origin/main --grep='^Task: T-0508'`); reviewer: 1 round, Approve (5 nits fixed after Approve, wording and slice-list only, D20).
- **Decisions, one line each**:
  - (a) step values `correctness_check_sim_v2`, `correctness_check_board_v2` (from `point` alone), `sim_run_timing_v2`, `board_run_timing_v2` (from the tool alone); the six of today retired; ADR-0177's choice from the read of the stamp and its dtype-mismatch rule not applied.
  - (b) check v2: `outcome`, `condition` (six), `contract_key` {`kind`, `dtype`, `layout`}, `shape` (the kind's members), `draws`, `tolerance`, `counts` = object keyed by output/inout operand name, each a per-draw array of {`failed`, `non_finite`} or {`differs`}; bit-exact today only `sdpa_kv_cache` `cache_k`/`cache_v` (per allocation, guard rows included); pass iff every count is 0.
  - (b) run v2: ADR-0063's list with `contract_key`, kind `shape`, and the measurement renamed `intervals`/`resolution` with `unit` `"ns"` (present with the measurement; does not reach `memory_bytes`).
  - (c) every result has a known contract and shape; broken results hold no counts/measurement/unit; tool failures stay results-free.
  - (d) build-log names `build-log-<new step>-<EE>.txt`; retired names not admitted.
  - (e) readers read only the new values: `checks.read`, `check_standing`, `verdicts.write`, `spec_feedback` (names only), `timings.compare` (admitted timing result on v2 names; `shapes_differ` also on `contract_key`), `timing_finding` (names only); prompts unchanged.
  - (f) slices below; then ADR-0181 decision 8 items 1-4.
- **HQ raised**: none. **Runtime acceptance items**: none.
- **Readings for the owner to check** (owner notice): the renames `resolution_ns`/`intervals_ns` -> `resolution`/`intervals` under ⑤ and "멤버 이름·철자는 ADR이 정한다"; `unit` not applying to `memory_bytes`; `counts` keyed by operand name (not per-draw first); the `_v2` suffix spelling.
- **Planner's next candidates** (ADR-0183 decision 9):
  1. Code: v2 check result builder + sdpa per-allocation cache counts — `hilclaw/check_result.py`, `hilclaw/harness/bf16_sdpa_kv_cache_verification.py` (+ tests); no tool path change.
  2. Code: `correctness.check` v2 switch — `check_identity.py`, `check_tool.py`, `check_admission.py`, `check_judging.py`, `check_answer.py`, `check_result.py`, `layout.py`, `check_standing.py`, `checks_tool.py`, `spec_feedback.py`, `verdicts_tool.py` (check part), maybe `hw_tool.py`; may need cutting along the cap.
  3. Code: `sim.run`/`board.run` v2 — `run_identity.py`, `run_result.py`, `run_tool.py`, `run_admission.py` (if needed), `layout.py`, `timings_tool.py`, `verdicts_tool.py`, `harness/timing_finding.py`.
- **Owner notice (#5)**: see below.
