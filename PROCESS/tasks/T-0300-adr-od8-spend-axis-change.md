---
id: T-0300
title: Write ADR-0102 on how a change in the unit or meaning of a `spend` axis is told apart across the lines of one run — OD-8 sub-question ㉟ (나); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, OD-17, FR-3, FR-13, NFR-1, NFR-2, "#5 D6"]
dependsOn: [T-0296, T-0298]
touchesFiles: [ARCHITECTURE/decisions/ADR-0102-od8-spend-axis-change.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []   # design-level OD (DRIVER §9; the driver may close it with an ADR). Not owner-only as scoped here: the record decides a rule for telling a changed axis apart and names no axis, unit or counting party (those stay FR-3 / #5 A-8 (owner) / OD-2 / OD-19); criterion 3 turns the task BLOCKED if the answer cannot be given without them. Independent of every open HQ: HQ-0021..HQ-0029 concern run-tool end-line kinds, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 (runtime STATE / instance / events schemas, "OD-8 종결 필요(§9 ADR 경로)") is still open. ADR-0097 registered OD-8 sub-question ㉟; ADR-0100 answered its part (가). Part (나) is left:

> (나) `spend`의 한 축의 단위나 뜻이 바뀌었을 때 그것을 어떻게 구분하는지 — ADR-0011 결정 6의 fold는 한 축의 양을 줄들에 걸쳐 더한다(축의 정의가 정한다; FR-3·OD-19·#5 A-8과 함께).

The `spend` of a `step_ended` line is an object from an axis *name* to a non-negative integer (ADR-0011 decision 7). The fold sums each axis by name over the lines of the log (decision 6), and `budget_spent` in `STATE.json` stores those totals with a position (ADR-0012 decision 4). If an axis kept its name while its unit or meaning changed, the fold would add amounts that cannot be added, and a stored total would silently mix the two. ADR-0097, ADR-0100 and ADR-0101 settled the same kind of question for event `data`, tool `result` definitions and failure kinds. No axis is named yet: ADR-0011 names none, and the tools write an empty `spend` today. So this record can only set the rule that every later axis definition follows. Which axes exist, their units and who counts them stay with FR-3, #5 A-8 (owner), OD-2 and OD-19. This task writes one design record (DRIVER §9) that answers ㉟ (나). It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer, size limit), §9 (lines 141-149; OD closing authority: ADR + reviewer Approve + #5 notice with the driver tail of §8).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` line 21 (FR-3), lines 80-86 (정본 규칙 and **행 형식** at line 84, the rule for editing a register row), line 93 (OD-2 row), line 99 (OD-8 row), line 108 (OD-17 row), line 110 (OD-19 row).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; the **기록 규칙** at line 8 is the only rule for edits to this file), line 119 (the ADR-0101 adopted line; the new adopted line goes after it), line 144 (the ㉟ bullet: rewrite its tail status and head status word in place), and the OD-17 (from line 247) and OD-19 (from line 332) sections. Read those two sections only to see what they leave open, so that the record decides none of it by accident.
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-172 (§검사 결과; its first paragraph is the recording rule for the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` lines 1-33 (Status, Context, decision 1: no axis, unit or measuring party named), lines 79-117 (decisions 6-9: fold, `spend` form, axes not accounted through the log, rebuilding, limits), lines 166-183 (Boundaries).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md` lines 57-81 (decisions 4-5: the stored spend view `budget_spent`, totals per axis, position) and lines 92-100 (limits).
- `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` (whole, 93 lines), `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` (whole, 92 lines), `ARCHITECTURE/decisions/ADR-0101-od8-failure-kind-change-and-step-values.md` (whole, 126 lines). These are the sibling answers, and their Status bullets are the model for this record's Status. Weigh, without copying, how they handle "what counts as a change", the never-reused name and the index (ADR-0101 decision 7, `ARCHITECTURE/StepValues.md`).
- `ARCHITECTURE/decisions/ADR-0032-od8-instance-record-round-budget.md` and `ARCHITECTURE/decisions/ADR-0033-od8-instance-record-wall-clock-budget.md`: grep "spend view", "axis" and "Boundaries". These are the budget-side members, which state that none of them is the name of a spend axis.
- `hilclaw/journal.py` (the fold near line 172, the `spend` check near lines 248-252) and `hilclaw/journaled_step.py` (lines 240-325). Read them as files to make observations at a named commit. Run nothing.

## Acceptance Criteria

1. Before writing, check that no `ADR-0102-*` exists. If the number is taken, use the next free number consistently in every file and record the actual touchesFiles in `## Result`. Create `ARCHITECTURE/decisions/ADR-0102-od8-spend-axis-change.md` in the record format of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References. Status states:
   - acceptance under DRIVER §9;
   - the three kinds of content: owner sentences quoted word for word (or a statement that no owner sentence speaks of this), cited content with its source, and the record's own design;
   - the 7-day objection window from the #5 notice;
   - that it is a record and not code: observations are read from files at a named commit, and nothing is run.
2. The record answers ㉟ (나) with a rule that every later definition of a spend axis follows. The rule says:
   - how a change in an axis's unit or meaning is told apart across the lines of one run;
   - what counts as such a change, and what does not;
   - what the fold (ADR-0011 decision 6) and the stored view `budget_spent` (ADR-0012 decision 4) do with amounts on both sides of such a change;
   - whether and where the axis names used so far are listed so that a later record can check that a name was never used. If a list is decided, this task creates no new file: the record names the place, and creating it (with a README link) is a follow-up. No axis exists yet.

   Alternatives considered weighs at least: a new, never-used axis name; a unit or version carried with the amount; a rule that axes never change; and leaving it to each axis definition. Each one gets a reason it was taken or rejected.
3. The record names **no** axis, unit, measuring party or token-accounting scope. It does not decide whether a given axis is accounted through the log (ADR-0011 decision 7), HW quota as an axis (OD-2), enforcement or how an unknown amount is weighed (OD-19), or the token element (#5 A-8, owner-only). If the executor finds that ㉟ (나) cannot be answered without one of these, stop without landing anything and return BLOCKED with the owner question (DRIVER §8). Do not narrow the answer until it no longer answers the question.
4. Every observation of code (for example, that today's tools write an empty `spend` and that the fold sums by name) names the file and the commit it was read at. No code, test or schema file is changed.
5. `ARCHITECTURE/Requirements.md`, OD-8 row only: follow the 행 형식 at line 84. Add one link to the new ADR after `**확정분**:`, with a topic of a few words. Rewrite `**잔여**:` in place so it no longer lists ㉟ (나), and keep every other open part. Change the status cell only if the 행 형식 asks for it. Do not restate the record and do not add dated text. No other row changes unless the record changes that OD's status, which it should not.
6. `ARCHITECTURE/OpenDecisionProposals.md`, OD-8 section only: follow the 기록 규칙 at line 8. Add one `- **채택분** [ADR-0102](…) — … (답함: 하위 질문 ㉟ (나))` line after the ADR-0101 line. In the ㉟ bullet, change the tail to the 답함 form and the head status word to 답함, with the question text kept. If the record raises a new sub-question, add it as a new bullet with the next free number (㊲) and status 미결. Write nothing else, and no dated paragraphs.
7. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the 검사 규칙 for the scenarios that cite OD-8, OD-17, FR-3 or the spend/budget accounting. Update the "최근 재검사" line in place according to the first paragraph of §검사 결과. Add an entry to "판정 변화 이력" only if a judgement changed or a gap appeared or closed. Change judgement-table notes only if an open OD reference changed.
8. Run the review cycle of dev-item-address steps 10-12 with a context-isolated reviewer until Approve, at most 7 rounds. Then land in document mode per CLAUDE.md "브랜치·merge 절차": branch `claude/T-0300-<slug>`, rebase on `origin/main`, push to main without force. The commit's last paragraph holds the `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0300` trailers, together with the attribution line (no blank line between them). Report the commit hash so the driver can post the §9 OD notice on #5.
9. No real `claude` is started and nothing that only the runtime has is required (D16).

## Out of Scope

- Naming or defining any spend axis, its unit or who measures it (FR-3, #5 A-8, OD-2), and budget enforcement (OD-19).
- Creating an axis index file or linking it from the README. That becomes a follow-up if the record decides on a list.
- Code changes in `hilclaw/` (for example, a check of axis names against a list). Any such change becomes a follow-up.
- OD-8 sub-questions ⑥ and ⑦ (wait on OD-23), and the optional link column in `EventKinds.md` and `StepValues.md`.
- Any edit to ADR-0011, ADR-0012, ADR-0097, ADR-0100 or ADR-0101. If one of them is now less exact, list it as a follow-up in `## Result`.

## Follow-ups

- (filled by the executor)

## Result

- (filled by the executor: commit hash, review rounds, follow-ups left)
