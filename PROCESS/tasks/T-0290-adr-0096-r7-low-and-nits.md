---
id: T-0290
title: Correct ADR-0096 after acceptance - the round-7 Low (the heading "The next call is not touched" of decision 2) and the two round-7 nits (objection windows of ADR-0047 and ADR-0079 in Status; ADR-0004 and ADR-0078 in References) left open by T-0289
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-18, FR-9, "#5 D6"]
dependsOn: [T-0289]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md   # existing; no new ADR
estimatedSize: {loc: 8, files: 1}
hq: []
---
## Why

T-0289 landed ADR-0096 (`b53d3b9`, document mode) after 7 review rounds, the last allowed. Round 7 approved with three non-blocking findings. They were left unapplied, because a change after the last round would have landed unreviewed text. `PROCESS/tasks/T-0289-adr-od18-check-build-directory-removal-failure.md`, `## Result`, "Review rounds" lists them:

- **R7 Low**: the heading of the third "Why" bullet of decision 2, "*The next call is not touched.*", says more than the bullet and the "cost, stated" bullet after it allow. A leftover or a survivor can still reach a later call through disk space, or by writing under an absolute name. The reviewer suggested "*The next call never uses a leftover.*"
- **R7 nit 1**: the Status bullet "It builds on ..." gives the objection windows of ADR-0056 and ADR-0060 but not those of ADR-0047 and ADR-0079.
- **R7 nit 2**: the body cites ADR-0004 (decision 3, in decision 5) and ADR-0078 (in Boundaries), but References does not list them.

T-0289's Follow-ups name "a small document-mode touch-up for the R7 items above". This task is that touch-up. It corrects an accepted record during its objection window (notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6244972784). It changes no decision's outcome, no OD status and no data-plane schema. It ticks **no PLAN checkbox** (P1-1 continues). Earlier corrections of the same kind, each with an "Edited after acceptance" Status bullet, are T-0238 (ADR-0076), T-0234 (ADR-0075) and T-0190 (ADR-0060).

**Why this item now.** STATE has no lock, no current task and no next task. Every TODO, INTERRUPTED or BLOCKED task is held by an unresolved HQ: T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284 and T-0286. The runtime-acceptance HQs 0013, 0014 and 0016-0019 are also open. The code of the `cpu_standin` operation of `correctness.check`, which applies ADR-0096, waits on T-0243 / HQ-0026. The only open PR is #179 (T-0284), and it changes only `hilclaw/clang_build.py` and `tests/test_clang_build.py`.

**Planner's reading.** Line numbers are those of `main` at `1b3ddda`. The executor and the reviewer re-check each one; the text wins.

- ADR-0096 has 101 lines.
  - Line 9 is the "It builds on ..." Status bullet. It reads "[ADR-0047](...) (decisions 4 and 5) and [ADR-0079](...) (decision 3)", with no window for either.
  - Line 11 is the 7-day notice bullet and line 12 the record-format bullet. The new Status bullet goes after line 12, as the last one.
  - Line 46 is the bullet "*The next call is not touched.*" (decision 2, "Why").
  - Line 62 cites "ADR-0004 decision 3" (decision 5). Line 90 cites "ADR-0078" (Boundaries).
  - Line 99 is the References list of ADRs.
- ADR-0047 Status line 5 says "Accepted on 2026-10-12". ADR-0079 Status line 5 says "Accepted on 2026-10-17". Each window runs 7 days from that record's #5 notice (DRIVER §9). Take the window's end from the date of the notice comment on #5, not from the acceptance date. Find the notice by searching #5 for the ADR number among comments that end with `— posted by driver`.
- ADR-0004 is `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`. ADR-0078 is `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`.

## Required Reading

ARCHITECTURE lines are long. Read them with `sed -n '<line>p' <file> | fold -w 400`, not whole files at once.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, size cap D4, trailers). Also §2 (document mode), §8 (comment format) and §9 (lines 141-147).
- `CLAUDE.md`, whole. Above all: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16) and "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` (the document-mode steps) and `.claude/skills/dev-code-review/SKILL.md` (the document-mode path).
- `PROCESS/tasks/T-0289-adr-od18-check-build-directory-removal-failure.md`, `## Result`: the findings are given there.
- `ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md`, whole.
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md` and `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`: their Status sections only. Read only.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md` decision 3 and `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md` (title and Decision headings). Read only, to confirm what ADR-0096 cites them for.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` line 14: one form of an "Edited after acceptance" Status bullet. Read only; do not copy its wording.
- Issue #5: the ADR-0096 notice above, and the ADR-0047 and ADR-0079 notices (`gh issue view 5 --repo myungjoo/HIL-Claw --comments`).

## Acceptance Criteria

1. **ADR-0096. Make only these edits:**
   - **R7 Low.** Rename the heading of the line-46 bullet so that it claims no more than the bullet establishes. The bullet establishes that a later call never builds or runs in a leftover, and that a name a leftover holds is drawn around. The reviewer's "*The next call never uses a leftover.*" is acceptable. If the bullet's body or the "cost, stated" bullet still claims more than that ("is not touched" or similar), adjust only those words. Do not change what decision 2 or decision 3 decides.
   - **R7 nit 1.** In the line-9 Status bullet, give the objection window of ADR-0047 and of ADR-0079 in the form already used there for ADR-0056 and ADR-0060 ("until YYYY-MM-DD"), with dates taken from their #5 notices. If a window has already ended on the execution date, write it the same way; do not add a sentence about it. If a notice cannot be found, leave that window out and say so in `## Result`.
   - **R7 nit 2.** Add ADR-0004 (decision 3) and ADR-0078 to the References ADR list (line 99), as relative links, keeping the list's order by number and its "(decision n)" form. Link the ADR-0004 and ADR-0078 mentions in the body only if the record's convention is to link an ADR on first mention; otherwise leave the body as it is.
   - **One new last Status bullet**, after line 12. It says the record was edited after acceptance on the execution date (UTC) by task T-0290 (document mode). It names the three edits briefly and says that no decision changed meaning. It says that the objection window of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6244972784 is unchanged. Write it in this record's own words.
   - Nothing else of ADR-0096 changes: the title, Context, decisions 1 to 5, Alternatives, Consequences (including its "less exact" list), Boundaries, and the References entries other than the ones added.
2. **Guarded exit.** If a finding turns out wrong on the cited texts, leave that part unchanged and give the argument in `## Result`. If a fix would change what ADR-0096 decides, leave it unapplied and record it as a follow-up. Do not invent a rule, a value or an OD. If every part is left unchanged, finish DONE with no landing commit and no Status bullet.
3. **No register, proposal or scenario edits.** No decision's outcome and no OD status changes. So `ARCHITECTURE/Requirements.md` (OD-18 row; its "행 형식" rule, line 84) and `ARCHITECTURE/OpenDecisionProposals.md` (OD-18 `채택분` line of ADR-0096 and sub-question ⑰; its "기록 규칙", line 8) do not change. Check both against their recording rules and confirm in `## Result` that neither became untrue. If one did, stop and return BLOCKED: the edit would then be outside this task's files. `ARCHITECTURE/StandardScenarios.md` stays unchanged, because CLAUDE.md "문서 커버리지 재검사" applies to edits of Requirements, UsageCases or StandardScenarios, and none is edited here.
4. **No other file changes.** This covers every other ADR, `README.md`, `PROCESS/` (except this task file's `## Result`, which the executor writes as DRIVER §3-5 says), `CLAUDE.md`, `.claude/`, `hilclaw/`, tests and CI.
5. **Document checks.** Every relative link in edited lines resolves. `git diff --check` is clean. Line endings are LF. `git diff --stat origin/main` lists only the file in `touchesFiles`.
6. **`## Result`** records the landed commit, the review rounds and their findings, the exact new wording of each edit, each part left unchanged and why, the two window dates and the notice URLs they came from, and any follow-ups left.

### Process

- Work only in the driver's dedicated clone.
- First do the §3-5 landed check: `git log origin/main --grep='^Task: T-0290'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0290 --state all`.
- Then do the CLAUDE.md session entry check: `gh pr list --repo myungjoo/HIL-Claw --state open`, and issues #4, #5, #7 and #8. An open PR that edits the file in `touchesFiles` makes the task BLOCKED ("open PR conflict"). At planning time the only open PR was #179, which does not edit it.
- Read the comments on issue #5 after the ADR-0096 notice. Skip the driver's own comments (last line `— posted by driver`). An owner objection to ADR-0096 makes the task BLOCKED ("requirement unclear"); quote the objection. An answer to an open HQ does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built or run except read-only git and gh commands, grep and link checks. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0290-adr-0096-r7-low-and-nits` from `origin/main`, with **no PR**. Run the context-isolated reviewer cycle (at most 7 rounds). After it approves, rebase on `origin/main` and push to `main` directly. The commit carries the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0290`. Delete the task branch afterwards.
- No §9 owner notice is due, because no decision and no OD status changes.

## Out of Scope

- Any change to what ADR-0096 decides, including the open points of its decision 5.
- The code of the `cpu_standin` operation of `correctness.check` (waits on T-0243 / HQ-0026), and `hilclaw/`, tests and CI generally.
- Editing any other accepted ADR, including the sentences ADR-0096 lists as "less exact".
- The edits of the BLOCKED document tasks T-0210, T-0231 and T-0264 (branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`). Do not read those branches for content.

## Follow-ups

- (code, waits on T-0243 / HQ-0026) The `cpu_standin` operation of `correctness.check` applies ADR-0096 decisions 2 and 3, as its Consequences say.

## Result
