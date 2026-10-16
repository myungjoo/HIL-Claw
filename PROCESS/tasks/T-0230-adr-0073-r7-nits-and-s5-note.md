---
id: T-0230
title: Correct ADR-0073 after acceptance - the four round-7 nits of T-0226 - and rewrite the S5 note of StandardScenarios to name only what OD-30 still leaves open; coverage re-check recorded
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-30, FR-11, FR-18, "CLAUDE.md 문서 커버리지 재검사"]
dependsOn: [T-0226, T-0227, T-0228, T-0229]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md
  - ARCHITECTURE/OpenDecisionProposals.md   # the ADR-0073 채택분 line of OD-30 only (nit d)
  - ARCHITECTURE/StandardScenarios.md       # the S5 row note; the S0 / S6 notes only if stale the same way; the "최근 재검사" line
estimatedSize: {loc: 14, files: 3}
hq: []
---
## Why

T-0226 landed ADR-0073 (`e350435`, document mode) after 7 review rounds, the last allowed. Round 7 approved with four nits that were deliberately left unapplied, because a change after the last round would have landed unreviewed text. They are recorded in `PROCESS/tasks/T-0226-adr-od30-case-lookup.md`, `## Result`, the `**Review**` bullet ("R7 nits left unapplied"):

- (a) decision 3, "FR-18 and FR-11 require a selection ... to record it": the record should say that it reads FR-11's "참조한 과거 사례" as every case the selection was given, and list that reading among its own design.
- (b) Status, "ADR-0072's Boundaries name these three as one later record": cite ADR-0072's Boundaries **and** its Alternatives point 4.
- (c) the long A-13 sentence (Consequences, "A-13 reading") should be split.
- (d) the OD-30 채택분 line of ADR-0073 in OpenDecisionProposals should be shortened to "선택이 읽은 사례의 식별(FR-11)".

The same `## Result` (Follow-ups) and the follow-ups of T-0227 name a second, related item: the S5 row note of StandardScenarios, "3단계 FR-11·17·18·NFR-2(가설·판정·참조 사례의 필드·파일 OD-30)". ADR-0059 (hypothesis record), ADR-0071 (verdict record), ADR-0072 (case file) and ADR-0073 (`case` basis kind, `cases_read`) now fix those fields and files, so the note names as open what is answered. The 검사 결과 recording rule says a note carries only the grounding FRs and the ODs **still open**.

These are corrections of an accepted record during its objection window (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6210927027, window until 2026-10-23) and of a coverage note. They need no design decision, change no decision, change no OD status and touch no data-plane schema. They tick **no PLAN checkbox** (P2-7 continues). Earlier in-place corrections of an accepted record with a Status bullet saying so: T-0213 (ADR-0069), T-0217 (ADR-0070).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked at `d0b6c52`). T-0210 and T-0225 are BLOCKED on HQ-0021 and HQ-0022; HQ-0013, HQ-0014 and HQ-0016..HQ-0019 are `runtime-acceptance` items. None bears on this task. The code slices of ADR-0073 have landed (T-0227 `4407ebe`, T-0228 `3b5591b`, T-0229 `c3e0abd`), so the record can be cleaned without racing them. Do not read for content, depend on or reconcile with the unlanded branches `claude/T-0210-*` and `claude/T-0225-*`.

**Planner's reading** (line numbers of `main` at `d0b6c52`; the executor and the reviewer re-check each; the text wins):

- ADR-0073 line 6 (Status, second bullet) holds nit (b)'s sentence. ADR-0072 line 117 is its Alternatives row "| 4 | A `basis` kind `case` admitted now | ... the reference member is best fixed with the lookup and the FR-11 identification." and line 130 its Boundaries item "The `basis` kind `case` ... fixed with the lookup". Whether the Boundaries name all three parts (lookup, kind, identification) or the Alternatives row is needed to cover the third is for the executor to state exactly.
- ADR-0073 line 22 (Decision, opening paragraph) lists "this record's own design"; line 59 (decision 3, "Present and empty" bullet) holds nit (a)'s sentence. FR-11 (Requirements line 29) says the decision log includes "그 결정이 참조한 과거 사례(FR-18)와 주입된 가설(FR-15)의 식별".
- ADR-0073 line 106 is the "A-13 reading" bullet (nit c).
- OpenDecisionProposals line 404 is the ADR-0073 채택분 line: "... 선택이 읽은 사례의 식별(FR-11; `hypotheses.json`의 멤버) (부분 답: 조회해 싣는 사례의 선택과 양)".
- StandardScenarios line 192 is the S5 row; line 186 (S0, 6단계 "가설·판정·사례의 필드·파일 OD-30") and line 193 (S6, 2단계 "싣는 사례의 선택·양 OD-30") may be stale in the same way; line 172 is the "최근 재검사" line.

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<line>p' <file> | fold -w 400`, not whole files at once. Line numbers are those of `main` at `d0b6c52`; the text wins.

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4, trailers). Also §2 (document mode), §8 (comment format) and §9.
- `CLAUDE.md`, whole; above all "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16) and "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` (document mode: steps 9 to 12 and 15); `.claude/skills/dev-code-review/SKILL.md` (document-mode path).
- `PROCESS/tasks/T-0226-adr-od30-case-lookup.md` `## Result`: the `**Review**` bullet (the four nits as given) and the `**Follow-ups**` bullet (the S5 note).
- `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`, whole (131 lines; the lines above in particular).
- `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`: Alternatives considered (around lines 110-118), Consequences line 123, Boundaries (around lines 126-135) - read only.
- `ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md` and `ADR-0070-od18-correctness-check-registration.md`: the last Status bullet of each ("Edited after acceptance ...") - read only, as the form of an after-acceptance Status bullet.
- `ARCHITECTURE/Requirements.md`: line 29 (FR-11), line 36 (FR-18), line 84 (**행 형식**), line 121 (OD-30 row) - read only.
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (**기록 규칙**) and the OD-30 section (from line 397, about 20 lines).
- `ARCHITECTURE/StandardScenarios.md`: 검사 규칙 (lines 13-29), the S0 step 6, S5 and S6 step texts (lines 39, 97-110), and the `# 검사 결과` section (from line 168): its first paragraph (**기록 규약**), the "최근 재검사" line and the 판정표.

## Acceptance Criteria

1. **ADR-0073** (only these edits):
   - **Nit (a)**: decision 3's sentence at line 59 says that this record reads FR-11's "참조한 과거 사례" as every case the lookup gave the selection (read, whether or not rested on), and that FR-18 and FR-11 require the runtime's selection to record that; the reading is added to the list of "this record's own" design at line 22. What decision 3 decides (`cases_read` optional in the file's validity; enforcement OD-18 / OD-23) is unchanged.
   - **Nit (b)**: the Status sentence at line 6 cites the ADR-0072 passages that actually name the three parts as one later record - its Boundaries and its Alternatives point 4 row, or only what the texts support - with no other change to that bullet.
   - **Nit (c)**: the "A-13 reading" bullet at line 106 is split into shorter sentences (the executor may keep it one bullet). Every claim in it stays, with the same citations; nothing is added or dropped.
   - **One new last Status bullet** saying the record was edited after acceptance on the execution date by task T-0230 (document mode), naming the three edits briefly, saying that no decision changed meaning and that the objection window of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6210927027 (until 2026-10-23) is unchanged. Write it in this record's own words; it need not mirror the bullets of ADR-0069 / ADR-0070.
   - Nothing else of ADR-0073 changes: decisions 1 to 3, the Example, Alternatives, the other Consequences bullets (the "Not edited and now less exact" list included), Boundaries, References (except an entry an edit newly cites).
2. **OpenDecisionProposals** (nit d): only the ADR-0073 채택분 line of OD-30 (line 404) changes - its "다룬 것" part ends with "선택이 읽은 사례의 식별(FR-11)" and drops "; `hypotheses.json`의 멤버". The line keeps the form the **기록 규칙** (line 8) gives a 채택분 line - one line, `- **채택분** [ADR-NNNN](…) — 다룬 것 (답함/부분 답: …)` - and restates nothing of the record. No other line of the file changes.
3. **StandardScenarios**:
   - **S5 note**: the 3단계 part of the S5 비고 names the grounding FRs and only what OD-30 (or another OD) still leaves open for that step, per the 기록 규약 sentence "판정표 비고에는 근거 FR과 아직 열린 OD(필요하면 하위 질문 번호)만 쓴다". The executor reads the step text (line 99) against ADR-0059, ADR-0071, ADR-0072 and ADR-0073 and the OD-30 section's "제안으로 남는 부분" and open bullets (for example the identification of injected hypotheses, FR-11 / FR-15) to decide what is still open. If nothing of that step is open under OD-30, the note keeps only its FRs. The note does not restate any ADR.
   - **S0 6단계 and S6 2단계 notes**: apply the same test; edit a note only if it names as open what a landed ADR answers, and say in `## Result` why each was or was not edited.
   - Scenario step texts (including the "필드·파일 = OD-30" parentheses of lines 39 and 99) are not edited; if the executor judges one wrong, record it as a follow-up.
   - **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사") of S0, S5, S6 and S11 by the 검사 규칙. Record it as the **기록 규약** (first paragraph of 검사 결과) requires: the "최근 재검사" line is rewritten in place (date, cause, result). A history entry under "판정 변화 이력" is added **only** if a verdict changed or a gap was found or closed - expected: none. No dated paragraph, no ADR summary.
4. **No other file changes**: `ARCHITECTURE/Requirements.md` (the OD-30 row stays as is; OD-30 stays `제안됨`; 30 rows), ADR-0059, ADR-0071, ADR-0072 and every other ADR, `README.md`, `PROCESS/`, `CLAUDE.md`, `.claude/`, `hilclaw/`, tests and CI.
5. **Guarded exit**: if a nit turns out wrong on the cited texts, leave that part unchanged and give the argument in `## Result`. If a fix would change what ADR-0073 decides, leave it unapplied and record it as a follow-up; do not invent a rule or an OD. If every part is left unchanged, finish DONE with no landing commit.
6. **Document checks**: every relative link in edited lines resolves; `git diff --check` is clean; line endings are LF; `git diff --stat origin/main` lists only files in `touchesFiles`.
7. **`## Result`** records the landed commit, the review rounds and findings, the exact new wording of each edit, the re-check outcome, why each optional note was or was not edited, and any follow-up left.

### Process

- Work only in the driver's dedicated clone. First the §3-5 landed check: `git log origin/main --grep='^Task: T-0230'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0230 --state all`. Then the CLAUDE.md session entry check: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8. An open PR that edits ADR-0073, the OD-30 section of OpenDecisionProposals or the 검사 결과 section makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6210927027 (the ADR-0073 notice). Skip the driver's own comments (last line `— posted by driver`). An owner objection to ADR-0073, ADR-0072, ADR-0071 or ADR-0059 makes the task BLOCKED ("requirement unclear"); quote it. An answer to an open HQ does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built or run except read-only git/gh, grep and link checks. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0230-adr-0073-r7-nits-and-s5-note` from `origin/main`; **no PR**. Run the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this file's path. At most 7 rounds; past the cap without a final Approve, the task is BLOCKED. A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, the task is BLOCKED; do not review your own work. Ask the reviewer to (a) check each edit against the nit as recorded and against the cited texts, (b) confirm no decision changed meaning, (c) check the OpenDecisionProposals line and the StandardScenarios edits against the recording rules of those files, and (d) run the coverage re-check independently.
- **Landing**:
  - `git fetch origin`, rebase onto `origin/main`, squash to one commit (`git reset --soft origin/main` after the rebase). A rebase that changed content goes back to review.
  - `git push origin HEAD:main` (fast-forward). If rejected: fetch, rebase, retry at most 3 times.
  - Commit message in English; subject starts with `T-0230:`; the body names the corrections and the coverage outcome and says nothing was built or run.
  - Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0230`, then any attribution trailer the session requires.
  - Delete the task branch only after the push is confirmed (local; remote only if it was pushed). Then check out `main` at `origin/main`.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`. Do not edit `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call means BLOCKED; do not work around it. If the task-branch push is rejected, rebase and retry once, then return BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- No #5 comment is needed (DRIVER §9 is not triggered: no OD status change, no decision changed), unless the reviewer judges that an edit changes a reason for a decision; then record that judgement and leave posting to the driver.
- Fill in `## Result` on `main` after the push and leave it uncommitted for the driver (DRIVER §3-6). `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- The "Not edited and now less exact" sentences of ADR-0059, ADR-0071 and ADR-0072 that ADR-0073 Consequences lists. Those records file them as follow-ups for the integrator (the session that works with the owner), and no driver task has edited an earlier record from such a list; the three records are not edited here.
- FR-11 / FR-18 parentheses in Requirements and the Requirements OD-30 row.
- Any change to what ADR-0073 decides; any new OD-30 part (a selection rule for many cases, injection, promotion, the S6 metric); `hilclaw/` and tests.
- PLAN checkboxes (P2-7 stays open).

## Follow-ups

## Result
