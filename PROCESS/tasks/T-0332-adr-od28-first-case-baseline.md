---
id: T-0332
title: Write ADR-0119 — the baseline of round 0 for a first-case run is a measurement of the run's own round-0 bring-up code, taken in the run's tree; a vendor-library baseline, an earlier run's best and the choice among several passing attempts stay open (OD-28 for the runs of ADR-0076 decision 1)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-1, OD-28, S0, S1]
dependsOn: [T-0329]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2-1 ("Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차") is the first unchecked item of the P2 order (D18). It is a PLAN checklist item, so the D18 priority rule does not apply. P1 has nothing plannable now:
- P0.5-4 waits on the owner's hook registration;
- the rest of P1-1 waits on HQ-0021, HQ-0025, HQ-0026 and OD-14 ①;
- P1-8's D18 completion criterion is the driver's to tick.

ADR-0118 fixed the round boundary of a first-case run, and T-0330 and T-0331 built its turn loop, the definition copy and a placeholder Round-Manager prompt under `orchestration/`. The next P2-1 slice is round 0. FR-1 says round 0 is bring-up plus a baseline measurement, which "이후 라운드 evaluate의 기준이 된다(baseline 선택 = OD-28)". OD-28 is open, and several accepted records wait on it:
- ADR-0059 decisions 3 and 5 and its Example;
- ADR-0073's Example and Consequences;
- ADR-0075 decision 2, its Example and its Boundaries.
Each assumes "a round-0 attempt `0000/01/01`, which no record yet says exists (OD-28)". Without an answer, the round-0 part of the Round-Manager prompt cannot be written without inventing an undecided item.

OD-28 is a design-level OD and is not on the owner-only list of DRIVER §9. #5 B-4 (owner, 2026-10-02) names the `cpu_standin` candidates: "the round-0 bring-up code or OpenBLAS `cblas_sgemm` (nntrainer excluded)". This task writes the ADR that closes the first-case part of OD-28 by the §9 path. The other two OD-28 sub-points needed for round 0 are left to later tasks: OD-18 ⑯ (가) (the self-check in round 0) and OD-8 ⑩ (who writes the first `STATE.json`). This task neither answers nor narrows them.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0332` trailer, size cap;
  - §9 (lines 142-149): the ADR path and the owner notice on #5.
- `CLAUDE.md`, these rules: "미결은 발명하지 않는다", "세션 진입 점검", "문서 커버리지 재검사", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/Requirements.md`:
  - FR-1 (line 19);
  - the "행 형식" paragraph (line 84);
  - register rows OD-1 (line 92), OD-28 (line 119).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - header, in particular the "기록 규칙" bullet (lines 1-10);
  - § OD-28 (lines 423-431).
- `ARCHITECTURE/StandardScenarios.md`:
  - §검사 규칙 (lines 13-26);
  - S0 and S1 (lines 30-56);
  - the first paragraph of §검사 결과 and the "최근 재검사" line (lines 168-172);
  - the S0 and S1 rows of the verdict table (search `| **S0**` and `| S1 |`).
- `ARCHITECTURE/UsageCases.md`: line 33 (the 라운드 0 / bring-up term) and UC-0 step 4 (line 61).
- Accepted records, read for what they cite and leave open:
  - ADR-0001 "Record format" (lines 146-153), the format to follow;
  - ADR-0004: path table and decision 3 (lines 30-90), the round, candidate and attempt tree;
  - ADR-0007 decision 7 (lines 60-71), how a difference is judged against a base;
  - ADR-0061 decision 1 (lines 32-38), and ADR-0063 decisions 1-2 (lines 28-44), the run tools and their result;
  - ADR-0076 decision 1 (lines 25-30), the scope "first case";
  - ADR-0113, all (112 lines): eligibility of a not-converged measurement as the baseline; which baseline is OD-28; the choice rule among eligible measurements is the rest of OD-1 (#5 A-4, owner-only);
  - ADR-0059: decision 3 (line 68), decision 5 (line 86), Example (line 90), Boundaries (line 152);
  - ADR-0071 decision 6 (lines 82-84);
  - ADR-0118: decision 2 and Boundaries (lines 69-77, 198-212).
- #5 B-4 confirmation: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 (point 4 and "Consequences").

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md):
   - run `gh pr list`, and read issues #4, #5, #7 and #8 for OD-28 and baseline;
   - open Draft PR #186 (T-0324) touches only `hilclaw/` and `tests/`, not this task's files;
   - if an open PR edits any file of touchesFiles in the OD-28 row or section, the S0/S1 rows or the "최근 재검사" line, stop and report;
   - check that `ADR-0119` is still a free number; if not, take the next free one and say so in Result.

2. **Owner-sentence search, before writing any decision.**
   - Search the comments of #5 that carry no "posted by driver" marker, and the body and comments of #4, #7 and #8. Use English and Korean terms: baseline, OD-28, bring-up, cblas, OpenBLAS, vendor library, 기준, 벤더 라이브러리, 개선율.
   - List in Status the sentences found that touch the point. Quote each for what it says and no further, as ADR-0118 Status does.
   - Tell whether the B-4 "Consequences" sentence on OD-28 is the owner's or the integrator's, and treat it as what it is.
   - **If an owner sentence decides the point differently, or reads two ways about it, write no ADR. Return BLOCKED (`requirement-unclear`) with the question.** The same applies if the choice turns out to need an owner-only item: #5 A/B, C-6, OD-25, OD-3, or the rest of OD-1 / #5 A-4.

3. **New `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md`** in the ADR-0001 record format, in English: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References. Mark each sentence as cited (source named) or as this record's own, as ADR-0118 does. Scope is **the runs of ADR-0076 decision 1** only. It decides at most the following, and each point it does not decide is named in Boundaries:
   - **(a) What the baseline of such a run is: the run's own round-0 bring-up code.** That is, the code a coder call of round 0 produces, kept as an attempt of round 0 in the run's tree under ADR-0004 decision 3. The baseline is a measurement of that attempt by the run tools of ADR-0061 decision 1. The record says which execution point the baseline measurement is (sim, board, or either), with its reason. The reason cites FR-1 and C-4 for the board's role; if no source settles it, the point is left open.
     - It says that such a round-0 attempt then exists. This is what ADR-0059, ADR-0073 and ADR-0075 assume.
     - It cites ADR-0113 for eligibility, and does not restate it.
   - **(b) Not a vendor-library kernel for the first case.** OpenBLAS `cblas_sgemm`, the #5 B-4 candidate, would be a new external dependency (CLAUDE.md A-13 BLOCKED reason). So the record does not adopt it and does not exclude it. Whether a library reference figure is also recorded is left open, together with the onboarding sub-question of the OD-28 section (UC-0 step 4). This is the proposal "두 값을 모두 기록".
   - **(c) Not an earlier run's best.** A resumed or branched run (S3; OD-8 ①; ADR-0113 limit 5) is outside the record.
   - **(d) Only the case it can answer without a choice rule.** Where round 0 leaves more than one attempt that could stand as the baseline (N > 1, or repairs), which one stands is the choice rule. That is the rest of OD-1 (#5 A-4, owner-only), with OD-18 ⑳, so it is left open. The record answers only the case where exactly one attempt can stand. P2-5 is N = 1.
   - **(e) A round 0 that leaves no attempt able to stand** (bring-up fails up to the repair limit) is left open, with OD-19 and OD-10.
   - **Not decided:**
     - how many candidates round 0 runs (OD-29; ADR-0028);
     - how the baseline is recorded or referenced: `best_ref`, eval or result files, a `STATE.json` member (OD-20, OD-8, OD-23);
     - which component measures and who calls the coder (OD-23, PLAN P2-2, P2-3);
     - the self-check in round 0 (OD-18 ⑯ (가));
     - the first `STATE.json` (OD-8 ⑩);
     - the commit step (OD-8 ⑪).
   - **No member, file, kind, value or version of the data plane is added or changed.** If the decision cannot be stated without one, stop and return BLOCKED (`data-plane schema change`).
   - Consequences:
     - list the accepted records whose OD-28 sentences are now less exact, found by a search of `ARCHITECTURE/decisions/` for "OD-28" and "baseline". Do not edit them; name them as integrator follow-ups;
     - name the next code or prompt slice it enables (the round-0 part of `orchestration/round-manager.md`) and what that slice still waits on;
     - list runtime acceptance items only if any exists (D16).
   - Around 150-220 lines. No dated paragraphs.

4. **`ARCHITECTURE/Requirements.md`, OD-28 row only.** Edit by the "행 형식" rule at line 84 of that file: one ADR link with a few words of topic under `**확정분**:`, the open parts rewritten in place under `**잔여**:`, and the status cell per that rule. Mark it as a partial answer for the first case, with the §9 path and the 7-day objection period. Do not restate the record. Do not edit FR-1 or any other row.

5. **`ARCHITECTURE/OpenDecisionProposals.md`, § OD-28 only.** Edit by the "기록 규칙" bullet of that file's header: one `채택분` line for the new ADR; the question and sub-question rewritten in place with their state markers. Do not restate the record or add dated notes.

6. **`ARCHITECTURE/StandardScenarios.md`** (CLAUDE.md "문서 커버리지 재검사"). Re-check S0, S1 and S8 by §검사 규칙, and record the result as the first paragraph of §검사 결과 prescribes: update the "최근 재검사" line in place, and add a "판정 변화 이력" entry only if a verdict changed or a gap opened or closed. In the S0 and S1 rows, change only the OD pointers that the ADR narrows (for example "baseline OD-28").

7. **Scope.**
   - `git diff --stat origin/main` lists only touchesFiles.
   - No edit to FR or NFR text, UsageCases, earlier ADRs, `orchestration/`, `hilclaw/`, tests, CI, `.claude/`, `CLAUDE.md`, README or `PROCESS/` (besides this task file's Result).
   - No new dependency.

8. **D16.** No `claude` is started by the executor or the reviewer (no subcommand, no flag). Nothing here needs a board, an accelerator or an API key.

9. **Merge (document mode, CLAUDE.md A-13).**
   - Branch `claude/T-0332-adr-od28-first-case-baseline`.
   - Context-isolated reviewer cycle (dev-code-review), at most 7 rounds, until Approve.
   - Rebase on `origin/main`, then push to main with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0332`.
   - Then post the OD-28 notice on #5 (DRIVER §9, ending with `— posted by driver`), and put its URL in Result.

## Out of Scope

- The round-0 text of `orchestration/round-manager.md` and any code. These are the next slices.
- OD-18 ⑯ (가), OD-8 ⑩ and ⑪, the run-status member of `STATE.json`, the coder (P2-2), the evaluator (P2-3), hooks and gates (P2-4, OD-3).
- The choice rule among eligible measurements (rest of OD-1, #5 A-4), OD-29's N and k, and OD-20's `best_ref`.
- Integrator follow-ups of ADR-0118, and edits to earlier ADRs that this record makes less exact.
- Anything in PLAN's 보류 section, and anything blocked by HQ-0021..HQ-0029, HQ-0031, HQ-0032 or HQ-0034.

## Follow-ups

- Next P2-1 slices, each likely needing its own ADR first:
  - OD-18 ⑯ (가): whether the turn loop runs the self-check before the round-0 turn or at every loop start, and what follows each outcome;
  - OD-8 ⑩: who writes the first `STATE.json` and in what order relative to `instance.json`;
  - the `STATE.json` member that says a run is over, stopped or waiting (rest of OD-8, OD-19), which the loop's command-line entry waits on.
- Then the round-0 part of the Round-Manager prompt.

## Result

- **Outcome: DONE.** Landed on main as `1f04d63` (document mode; trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0332`). Branch `claude/T-0332-adr-od28-first-case-baseline` deleted locally and on origin (non-force).
- **Files:** new `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md` (ADR-0119 was free); OD-28 row of `ARCHITECTURE/Requirements.md`; § OD-28 of `ARCHITECTURE/OpenDecisionProposals.md`; S0 and S1 rows and the "최근 재검사" line of `ARCHITECTURE/StandardScenarios.md` (S0, S1 and S8 re-checked: no verdict change, no gap, so no history entry). `git diff --stat` held only the touchesFiles.
- **Session entry check:** the only open PR was #186 (T-0324, `hilclaw/` and `tests/` only). Issues #4, #5, #7 and #8 were read.
- **Owner-sentence search** (#4 body and its 6 comments; #5 body and the 38 of its 189 comments without the driver marker; #7 with 2 comments; #8 with 6): no owner sentence decides the point or reads two ways about it. The B-4 "Consequences" candidate line is read as the integrator's derivation, because it sits outside "Decided (owner)" 1-5 and ends "To be reflected … in the next PR". ADR-0113 Context had filed the same line as an owner sentence; ADR-0119 names that difference and lists it as an integrator follow-up.
- **Decision:**
  - **Scope:** runs of ADR-0076 decision 1 that the run tools of ADR-0061 decision 1 cover (`cpu_standin` in the local configuration, or the mock) and that start from their own round 0.
  - **Baseline:** a measurement of the run's own round-0 bring-up attempt, taken at the board point by `board.run`. Eligibility is ADR-0113's.
  - **Case answered:** only a round 0 in which exactly one attempt can stand (P2-5, N = 1).
  - **Left open:** OpenBLAS (a new external dependency) and a library figure; resumed or branched runs; the choice among several attempts (rest of OD-1, #5 A-4); a round 0 with no attempt that can stand; the baseline's record; round 0's spec, N, budget counting and injected input; re-measurement.
  - No data-plane change and no new dependency.
- **Review:** 7 rounds; rounds 1-6 Request changes, all addressed; round 7 Approve. Non-blocking findings of round 7 were not addressed, because a further round would have exceeded the 7-round limit. Integrator follow-ups:
  - The StandardScenarios "최근 재검사" line and the S0/S1 row pointers could name "로컬 구성 밖 첫 사례 run" and the re-measurement, as the register row does.
  - ADR-0029 (Context line 20, Boundaries line 127, "round 0 (OD-28)") is missing from ADR-0119's "now less exact" list.
  - ADR-0119 files "round 0's use of cases" (ADR-0073 Boundaries) under OD-28, which ADR-0073 itself did not do.
  - The ADR is 134 lines, below the "around 150-220" target; its lines are long.
- **Other integrator follow-ups** (named in ADR-0119 Consequences): the accepted records whose OD-28 sentences are now less exact (ADR-0059, 0073, 0075, 0113, 0007, 0071, 0114, 0061, 0004, 0005, 0002, 0008, 0009, 0050, 0053, 0105, 0118); the UsageCases line 33 term entry; S1's order of steps 3 and 5 for a run of this scope in checkpoint mode.
- **OD notice on #5 (DRIVER §9):** https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6261910420 (7-day objection period starts there).
- **D16:** no `claude` was started; nothing needs a board, an accelerator or an API key. No runtime acceptance items.
- **Next slice:** the round-0 part of `orchestration/round-manager.md`, which still waits on OD-18 ⑯ (가), OD-8 ⑩ and ⑪, and the baseline's record (OD-20, OD-8, OD-23).
