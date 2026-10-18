---
id: T-0301
title: Create the empty spend-axis index `ARCHITECTURE/SpendAxes.md` and link it from the README repository table (follow-up of T-0300, ADR-0102 decision 6); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, OD-17, "#5 D6"]
dependsOn: [T-0300]
touchesFiles: [ARCHITECTURE/SpendAxes.md, README.md]
estimatedSize: {loc: 15, files: 2}
hq: []   # No OD is decided and no decision changes: this creates the index that ADR-0102 (driver-accepted, DRIVER §9) already decided, with no row, and adds a README link. No axis, unit, measuring party or token scope is named (FR-3, #5 A-8 owner-only, OD-2, OD-19 untouched). Independent of every open HQ: HQ-0021..HQ-0029 concern run-tool end-line kinds, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py) or with any blocked task's touchesFiles.
---
## Why

T-0300 landed ADR-0102 (OD-8 sub-question ㉟ (나)) as `7b0a22d`. Decision 6 of that record says that the spend-axis names are listed in one index, `ARCHITECTURE/SpendAxes.md`. The index has three columns: the name, a link to the defining record (with its decision), and the state. Its states are the same as those of `ARCHITECTURE/StepValues.md`. The record created no file because no axis exists yet. Its Consequences name one document follow-up: "create `ARCHITECTURE/SpendAxes.md` with no row and link it from the README document table (decision 6)". This task does that follow-up and nothing more. T-0298 created `ARCHITECTURE/StepValues.md` and T-0299 linked it from the README; this is the same pair of steps for the spend-axis index. The task decides nothing new and writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time limit), §5 (lines 86-115: task format, naming convention, `Task:` trailer, size limit), §9 (lines 141-149: driver-accepted records and the 7-day objection window).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0102-od8-spend-axis-change.md`: Status (lines 3-12), decision 1 (lines 23-28; the placeholder axis names used in tests and records), decision 2 (lines 30-33; what an axis definition is), decision 6 (lines 56-61; the index, its columns and states, and what it does not hold), decision 7 (lines 63-67; how a name enters the index), and Consequences (lines 82-90).
- `ARCHITECTURE/StepValues.md` (whole, 14 lines) and `ARCHITECTURE/EventKinds.md` lines 1-12. These are the two existing indexes. The new file follows their form: a title, one intro paragraph that links the deciding record, the bullets "Adding a row", "States" and "Nothing checks …", and then the table.
- `README.md` lines 40-56 (the "저장소 구성" table). The `ARCHITECTURE/` row is line 46, and it already holds the `EventKinds.md` and `StepValues.md` links.
- `PROCESS/tasks/T-0300-adr-od8-spend-axis-change.md` `## Result` (the follow-up as recorded).

## Acceptance Criteria

1. **Pre-check.** Before you write anything, confirm that `ARCHITECTURE/SpendAxes.md` does not exist on `origin/main`. Also confirm that ADR-0102 decision 6 still names that path and those three columns. If the file already exists, or if ADR-0102 has been reverted or changed so that it no longer asks for the index, stop and land nothing. Return BLOCKED with the reason `요구 불명확/미결 발명 의심`.
2. **Create `ARCHITECTURE/SpendAxes.md`** in English, in the form of `StepValues.md`:
   - A title, for example ``# Axes of `spend` ``.
   - One intro paragraph. Say that this is the one list of the axis names that records have defined for the `spend` of `step_ended` lines of `runs/<run_id>/events.ndjson`, and link ADR-0102 decisions 6 and 7. Say that it is an index only. The unit, the meaning and the measuring party are stated only by the defining record, and that record wins when the two disagree.
   - **"Adding a row"**, rendering ADR-0102 decision 7. The defining record chooses a *name* of ADR-0001 that is not in this list. The name must not be a placeholder of a record or a test (give `example_axis`, `other_example_axis`, `a_axis` "and the like", as ADR-0102 decision 1 lists them). The record checks that the string is no other name in `hilclaw/`, `tests/` and `ARCHITECTURE/`, and adds its row with the state `defined` in the commit that lands it. A changed definition is a new axis under a new name (ADR-0102 decision 3), and a name is never reused.
   - **"States"**, rendering ADR-0102 decision 6:
     - `defined`: the defining record is accepted.
     - `not used`: an accepted later record, linked in the row, says that no tool of the current contracts states amounts of the axis any more.
     - `reverted`: the defining record has been reverted, and the name stays used.

     State also that a row is never removed and its name never changes.
   - **"Nothing checks a line's axis names against this list"** (ADR-0102 decision 7).
   - A table with exactly the three columns of decision 6, for example `| Axis | Defined by | State |` followed by its separator line, and **no data row**. Do not add a placeholder, example or "none yet" row. Do not add a dated sentence or a sentence saying that no axis exists yet; the empty table says that.

   Render only what ADR-0102 decisions 3, 6 and 7 say. Name no axis, unit, meaning, measuring party or token scope (FR-3, #5 A-8, OD-2, OD-19). Add no rule the record does not state. Keep wording that the record and the two sibling indexes share as it is, so that the three indexes read alike.
3. **README link.** On line 46 of `README.md` (the `ARCHITECTURE/` row of "저장소 구성"), add one link `[SpendAxes.md](ARCHITECTURE/SpendAxes.md)` with a short Korean description in parentheses, in the same `[name](path)(설명)` form as the other entries, for example `(spend 축 이름 목록)`. Put it right after the `StepValues.md` entry and before `reviews/`. Change nothing else in `README.md`.
4. **Files left alone.** Do not edit any ADR (ADR-0102 included: its decision 6 already says that a later document task creates the file), `ARCHITECTURE/StepValues.md`, `ARCHITECTURE/EventKinds.md`, `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` or `ARCHITECTURE/StandardScenarios.md`. No OD status, register row, adopted line or sub-question changes. CLAUDE.md "문서 커버리지 재검사" does not apply, because neither file is Requirements, UsageCases or StandardScenarios. Say so in `## Result`. If the reviewer or the executor finds that ADR-0102 is now less exact because the file exists (for example, Status line 11 does not say that a revert also removes or marks the index), do not edit it; list it in `## Result` as a follow-up.
5. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0301-spendaxes-index-and-readme-link`.
   - Run the reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) until Approve.
   - Rebase on `origin/main`, squash the branch to one commit and push it to main directly as a fast-forward.
   - Put the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0301`, together with the attribution line, in the commit message's **last paragraph**, with no blank line between them.
   - Never use `git push --force*`.
6. **No #5 notice is required**, because no OD status changes and no decision is added.
7. **`## Result`** records:
   - the landed commit
   - the two files as written
   - review rounds and any unapplied findings
   - the coverage re-check note of criterion 4
   - any follow-ups

   Do not start a `claude` process (D16). Run no code, test, compiler or container. This task needs nothing that only the runtime has.

## Out of Scope

- Naming or defining any spend axis, its unit, meaning or measuring party (FR-3, #5 A-8, OD-2), and budget enforcement (OD-19).
- Any code change in `hilclaw/` or `tests/`, for example a check of axis names against the index. ADR-0102 decision 7 says that nothing checks it.
- Edits to ADR-0011, ADR-0012, ADR-0097, ADR-0100, ADR-0101 or ADR-0102. T-0300's `## Result` lists their "less exact" points, and this task does not take them up.
- The optional link column for `not written` / `not used` rows in `EventKinds.md` and `StepValues.md` (T-0299 nit 3). Do not add such a column to `SpendAxes.md` either: decision 6 fixes three columns.
- OD-8 sub-questions ⑥ and ⑦ (they wait on OD-23).
- Open PR #179 files and blocked tasks (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- (filled by the executor)

## Result

- (filled by the executor)
