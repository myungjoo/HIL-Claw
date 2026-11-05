---
id: T-0557
title: ADR-0198 slice 4 for PLAN P3-6 — land the first non-kernel candidate kind in the documents: change the three-layer "C 커널" wording of CLAUDE.md and Requirements, add the compile-settings scenario to StandardScenarios with the coverage re-check, link ADR-0199 in the registers, and hand over the runtime acceptance item for a coder-free round
phase: P3
status: DONE
commitMode: doc
coversReq: [D27, OD-32, OD-6, C-6, FR-1, FR-5, "PLAN P3-6", HQ-0088, HQ-0089, ADR-0198, "#5 A-12"]
dependsOn: [T-0556]
touchesFiles:
  - CLAUDE.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 120, files: 4}
hq: []
---
## Why

**PLAN P3-6** (커널 밖의 후보): the owner's answers HQ-0088 and HQ-0089 (2026-11-05) are recorded in **ADR-0198** (T-0552), whose decision 9 orders the slices 1, 2a, 2b, 3, 4; T-0552 to T-0555 landed slices 1, 2a, the first half of 2b and 3, and T-0556 (this batch) lands the second half of 2b (`spec.write` writes the version-3 spec on the technique-selector's request; the round text makes no coder call in a `compile_settings` round) with **ADR-0199**. This task is **slice 4, the landing** ("first non-kernel kind lands" of HQ-0088 ③ and ⑤):

- HQ-0088 ③ (a) (owner): CLAUDE.md's three-layer "C 커널" wording changes when the first non-kernel kind lands. The integrator's reading in HQ-0088's `decision` (not the owner's words): the task that lands the first non-kernel kind changes it. `ARCHITECTURE/Requirements.md` line 11 carries the same three-layer definition ("**3층** = 코더가 산출하는 C 커널(FR-5, A-7)") and is changed with it so the two do not disagree.
- HQ-0088 ⑤ (a) (owner): the scenario of this flow is added in the same work as the first kind that lands; the integrator's reading: the same task adds it to StandardScenarios and re-checks coverage.
- ADR-0198 Consequences: a runtime acceptance item for a live coder-free round is handed to `PROCESS/RuntimeAcceptance.md` by slice 4. The executor returns it in `## Result`; the driver adds it (D22). The executor does not edit `PROCESS/RuntimeAcceptance.md`.
- ADR-0199 (T-0556) gets its register link here, as T-0556's criterion 1 says.

After this task lands, the driver checks PLAN P3-6 (ADR-0198 decision 9: "PLAN P3-6 is checked after it").

**Why a separate task (D20 ③; D4 file cap).** Merged with T-0556 the work would touch about 11 non-test files, over the cap of 10; this part is document mode.

**Order (DRIVER §6 D27 ①)** as in T-0556's Why. In dev-item-address step 1 confirm that T-0556 is `DONE` with ADR-0199 on `main`; if T-0556 ended without the version-3 write or the round text (for example closed with no result), the landing has nothing to describe: report that in `## Result` and stop.

**Open HQs (D27 ⑥/⑦).** Do not ask again or anticipate HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0097. The scenario's tier (basic MVP or extension) and its number are not owner decisions given anywhere; choose them, state the choice as the integrator's reading (통합자 독해) in the scenario's heading line or the 계층 paragraph, and keep the step tags to existing FR/OD ids. If writing the scenario shows a step with no FR and no OD (a gap), do not invent an FR or OD: record the gap by the rules of §검사 결과 and return a question in `## Result` in the DRIVER §8 structure (Korean), then return `DONE`.

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5** (document mode of §2: branch `claude/T-0557-<slug>`, context-isolated reviewer cycle, rebase and direct push to `main` with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0557` trailers; storage D29), §8 (question structure), D22 (runtime acceptance items go to the driver, not into an HQ).
- `CLAUDE.md` "상시 규칙" — **세 층 모델** and **문서 커버리지 재검사** bullets.
- `ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md` (decisions 2, 3, 4, 5, 6, 9; Consequences "Runtime acceptance item"; Boundaries) and `ARCHITECTURE/decisions/ADR-0199-*.md` (T-0556; the request form and the round text).
- `ARCHITECTURE/Requirements.md`: line 11 (세 층 모델), the **"행 형식"** paragraph (line ~85), and the rows OD-6, OD-23 and OD-32. `ARCHITECTURE/OpenDecisionProposals.md`: the header's **"기록 규칙"** (line 8) and § OD-32 (sub-questions ①, ⑥, ⑦), § OD-6 ②, and the section of any OD ADR-0199 answers part of.
- `ARCHITECTURE/StandardScenarios.md`: 계층, 검사 규칙, S0, S1, S12 (for the tagging style), and **§검사 결과** — its first paragraph (기록 규약), the "최근 재검사" line, the verdict table and "판정 변화 이력".
- `PROCESS/STATE.json` `humanQuestions` entries HQ-0088 and HQ-0089 (`question` and `decision`).

## Acceptance Criteria

1. **Three-layer wording**: CLAUDE.md's "세 층 모델" bullet and `ARCHITECTURE/Requirements.md` line 11 say that layer 3 is the candidate the run optimizes — the C kernel the coder (`claude -p`) produces, or, for the candidate kind `compile_settings`, the compile settings the orchestrator's selection role writes into the spec (HQ-0088 ② (a)) — with a citation of HQ-0088 ③ and ADR-0198; the rest of both bullets (layers 1 and 2, the language policy's "2층에만") is unchanged. Edit nothing else in CLAUDE.md.
2. **Scenario** (HQ-0088 ⑤ (a)): one new scenario in `ARCHITECTURE/StandardScenarios.md` for a `compile_settings` run, in the existing step style with each step tagged by FR/OD ids: start with the kind; round 0 brings up the C kernel with the coder; in each round ≥ 1 the selection role chooses flags and has the version-3 spec written, no coder call; evaluation builds round 0's kernel with the target's and the candidate's flags and records `build.json`; verdicts and the round end as in S0. Its remaining open parts are tagged by the OD sub-questions that hold them (for example OD-32 ①·⑦ for other and model-level kinds; cases and the S6 metric of this kind as ADR-0198 Boundaries leaves them). No ADR content is restated beyond one tag per step.
3. **Coverage re-check** by the first paragraph of §검사 결과: a verdict-table row for the new scenario (비고 holds only the grounding FRs and the open ODs); the "최근 재검사" line rewritten in place (date, trigger: ADR-0198 slice 4 and ADR-0199, result); one entry (1 to 3 lines) in "판정 변화 이력" only if a verdict changed or a gap was found or resolved — the new scenario's first verdict counts as a change. No dated narrative paragraph and no ADR summary elsewhere.
4. **Registers**: ADR-0199's link added as one item per the "행 형식" (Requirements, `**확정분**:`) and the "기록 규칙" (OpenDecisionProposals, one `**채택분**` line in the section of the OD it answers part of, the sub-question's end-state and bullet head rewritten in place if it changes). If the landing closes a part of OD-32 ⑥ or ⑦ that the row's `**잔여**:` still names (for example "the wording changes when the first kind lands"), rewrite that `**잔여**:` in place. One link per new ADR; no restatement of what the ADRs record; no dated paragraph.
5. **Runtime acceptance item** returned in `## Result` (not written to `PROCESS/RuntimeAcceptance.md`), in Korean, with source `P3-6, T-0556, T-0557, ADR-0198, ADR-0199`: on a runtime machine with a logged-in `claude` and the clang image, a live round ≥ 1 of a `compile_settings` run in which the technique-selector calls `spec.write` with the ADR-0199 request and the version-3 spec is written, the Round-Manager takes no step 8 and makes no coder call, `correctness.check` at `sim` builds round 0's kernel with the target's flags followed by the candidate's and writes `measure/…/build.json`, and the round ends through steps 9 to 12 and the closing steps (with `case.write` refused and the round going on); plus any item ADR-0199 names. State that it becomes checkable after T-0556 and T-0557 land.
6. **Process**: document mode — dev-item-address steps 1 to 12 with a context-isolated reviewer to Approve (≤ 14 rounds, D28); rebase on `origin/main` and push to `main` directly; commit trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0557`. In `## Result` list the files changed, the scenario number and tier chosen and why, and the runtime acceptance item text.

## Out of Scope

- Any code, test or `orchestration/` change (T-0556 and earlier).
- `PROCESS/PLAN.md` (the driver checks P3-6), `PROCESS/RuntimeAcceptance.md` and `PROCESS/STATE.json` (the driver writes them).
- README's three-layer table (an existing hold line, T-0530 follow-up), the ADR wording ADR-0198 lists as less exact (a hold line), and other ADR edits.
- Quantization settings and vendor-language kernels as kinds (not chosen, D27 ①), model-level kinds (HQ-0088 ④ (a)), and HQ-0081, HQ-0083, HQ-0085, HQ-0095 to HQ-0097.
- Starting `claude` in any form (D16); no test run (D25).

## Follow-ups

- None planned. After this lands the driver checks PLAN P3-6 in its §3-6 status commit and adds the returned runtime acceptance item to `PROCESS/RuntimeAcceptance.md`.

## Result

- **Outcome**: DONE (document mode). T-0556 was confirmed `DONE` with ADR-0199 on `main` (dev-item-address step 1).
- **Landed on `main`**: `78d1b334` (main change), `14cbd779` (round-1 nits), `a7271068` (round-2 nit; carries `Reviewed-by: reviewer agent (2 rounds, Approve)` and `Task: T-0557`). Review: 2 rounds with a context-isolated `dev-reviewer`; round 1 Approve with 5 nits (4 fixed, the N > 1 tag not added), round 2 Approve with 3 nits (the OD-32 tag of S13 step 2 fixed; the step-4 tag/verdict-row symmetry and the pre-existing OD-6 status-cell date range left).
- **Process deviation**: the landing script ran `git push origin HEAD:main` on a separate line after a failed `git rebase` (unstaged nit fix), so the two reviewed branch commits reached `main` unsquashed and without the `Reviewed-by` trailer. History was not rewritten (no force push); the follow-up commit `a7271068` holds the trailer and states the review record of `78d1b334` and `14cbd779` in its body. All three carry `Task: T-0557`. The branch `claude/T-0557-compile-settings-landing` is deleted (remote and local).
- **Files changed**: `CLAUDE.md` (three-layer bullet, layer 3 only), `ARCHITECTURE/Requirements.md` (line 11; rows OD-6, OD-23, OD-32: ADR-0199 link, OD-32 `**잔여**` rewritten), `ARCHITECTURE/OpenDecisionProposals.md` (one ADR-0199 `**채택분**` line each in § OD-6, § OD-23, § OD-32; OD-32 ⑥ and ⑦ end-states rewritten), `ARCHITECTURE/StandardScenarios.md` (계층, S13, 최근 재검사, 판정 변화 이력, verdict row).
- **Scenario**: **S13** (next free number), **extension tier (Post-MVP)** — integrator's reading, stated in the 계층 paragraph: compile settings is PLAN P3 (D27), outside the MVP scope, and promoting a scenario to the basic tier has been an owner decision (S8, OD-21); same placement as S12. Verdict: 확장 호환; no other verdict changed; no gap. Observation (not a gap: FR-18 grounds it and nothing structurally excludes it): cases and the S6 metric of a `compile_settings` run have no registered OD (ADR-0198 Boundaries); S13 step 5 and its verdict row say so. No HQ is raised.
- **Runtime acceptance item** (for the driver to append to `PROCESS/RuntimeAcceptance.md`; source `P3-6, T-0556, T-0557, ADR-0198, ADR-0199`; checkable now that T-0556 and T-0557 have landed):
  - 로그인된 `claude`와 clang 이미지가 있는 런타임 머신에서, 후보 종류 `compile_settings`(N = 1) run의 실제 라운드 ≥ 1 하나가 다음을 모두 만족한다 — technique-selector가 ADR-0199의 요청(`run_id`, `round`, `candidate` 1, `attempt` 1, `flags`)으로 `spec.write`를 불러 `(round, 1, 1)`의 버전 3 spec이 쓰이고 보고에 `spec: written` 한 줄이 있다; Round-Manager가 단계 8을 하지 않고 코더 호출이 없다(그 시도의 `output/`은 비어 있다); `sim` 지점의 `correctness.check`가 라운드 0 시도 `(0, 1, 1)`의 커널을 대상의 플래그 뒤에 후보의 플래그를 붙여 빌드하고 `measure/…/build.json`을 쓴다; 라운드가 단계 9~12와 닫는 단계로 끝난다(`case.write`는 거부되고 라운드는 이어진다). ADR-0199가 이 항목에 넣은 것: 실제 technique-selector가 "A compile-settings run" 절을 따르는 것과 실제 Round-Manager가 단계 8을 건너뛰는 것. 확인 가능 시점: T-0556·T-0557 land 뒤(지금).
- **Storage**: no task directory, image or install was created; nothing to clean. No `claude` process and no test run (D16, D25).
- **Follow-ups**: none. The driver checks PLAN P3-6.
