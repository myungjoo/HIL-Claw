---
id: T-0207
title: Clear the round-7 review minor of T-0205 - ADR-0066 decision 4 (iii) and its Alternatives row no longer say a converged report that reads neither constant "does not exist" but that one exists only tuned to a narrow window around the value of cv_max, and the "(존재하지 않는다)" in the OD-18 ADR-0066 bullet of OpenDecisionProposals says the same; coverage re-check recorded
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-18, FR-10, "CLAUDE.md 문서 커버리지 재검사"]
dependsOn: [T-0205, T-0206]
touchesFiles: [ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 12, files: 3}   # one sentence of decision 4 (iii), one Alternatives row and one Status bullet in ADR-0066; one parenthesis in OpenDecisionProposals line 316; one heading clause and one dated paragraph in StandardScenarios
hq: []
---
## Why

T-0205 landed ADR-0066 (`edf70d5`) after 7 review rounds, the last allowed. Round 7 approved with one minor that was deliberately not applied, because a change after the last round would have landed unreviewed text (`PROCESS/tasks/T-0205-od18-run-tools-mock-script.md` `## Result`, `**Follow-ups:**`, first bullet). T-0206 then landed the code slice of ADR-0066 (`e18264d`, PR #140, `hilclaw/mock_run.py`), which implements choice (i) and is not affected by this task.

The minor, as recorded: "ADR-0066 decision 4 (iii) says "None exists" for a converged report that reads neither constant; under the standard applied to (ii), such a report fitted to a narrow window of `cv_max` around 0.05 can be built. The sentence and the "(존재하지 않는다)" in the OpenDecisionProposals bullet should say it is tuned to `cv_max`'s value. The choice of (i) is unaffected."

This is a correction of a factual claim inside a weighing; it makes (iii) use the same standard as (ii), which ADR-0066 already describes as a report that "reads neither constant" while it "rests on a bound of `cv_max`". It needs no design decision, changes no choice (the choice stays (i)), changes no OD status and touches no data-plane schema. This task ticks **no PLAN checkbox** (P1-1 continues) and decides nothing new. The precedent is T-0190 (ADR-0060, `57d38ff`), T-0193 (ADR-0061, `d7a6090`) and T-0197 (ADR-0062, `69745a1`): an accepted record is edited in place during its objection window, with a Status bullet that says so.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-15 at `6692525`). The open HQs (HQ-0013, HQ-0014, HQ-0016..HQ-0019) are `runtime-acceptance` items on DONE tasks and do not bear on this task. The next run-tools contract slices (OD-18 sub-question ⑲, the tool functions and registration) will edit the same OD-18 passages of `ARCHITECTURE/OpenDecisionProposals.md`, so clearing this minor first keeps those larger §9 records on a cleaned base.

**Planner's reading of the finding (line numbers of `main` at `6692525`; the executor and the reviewer re-check each, and the arithmetic is theirs to confirm):**
1. **Decision 4 (iii)** (ADR-0066 line 65) reads: "**(iii) A converged report that reads neither constant.** None exists: a converged report stops "at the first n with n ≥ `n_min` and CV < `cv_max`" (cited: ADR-0007 decision 4). Of equal samples, ...; of unequal samples, it must have a CV of at least `cv_max` at each proper prefix from `n_min` on and below `cv_max` at the whole, so it places values on both sides of `cv_max` and reads it." The last clause already says such a report depends on `cv_max`; but (ii) (line 64) is also called a report that "reads neither constant" although it "rests on a bound of `cv_max`". Under (ii)'s standard — a report built from the handed `n_max` alone that the replay accepts for a range of values of the constants — a converged report of unequal samples does exist (for example, `n_max` samples whose every proper prefix from two samples on has a CV at or just above some value and whose whole has a CV just below it), but only for `cv_max` inside a narrow window that the report's values are tuned to, around today's 0.05. So "None exists" overstates; the fix says such a report exists only when tuned to a narrow window around the value of `cv_max`, so it rests on that value far more closely than (i) or (ii) rest on a bound of it, and it is not chosen. The equal-samples half of the sentence stays as it is if the executor finds it correct.
2. **The Alternatives row** (ADR-0066 line 133) reads "See decision 4: none exists." and is aligned with the new wording (for example "See decision 4: one exists only tuned to a narrow window around the value of `cv_max`.").
3. **OpenDecisionProposals** line 316 (the ADR-0066 채택분 bullet of OD-18) contains "두 상수를 읽지 않는 수렴 보고(존재하지 않는다)". The fix replaces the parenthesis in substance with "(`cv_max`의 값 둘레의 좁은 창에 맞춘 것만 있다)" or equivalent Korean wording that says the same as the new (iii). A grep at planning time found no other copy of the claim: `Requirements.md` and `StandardScenarios.md` have no "존재하지 않" about it, and ADR-0066 has it only at lines 65 and 133.

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<line>p' <file> | fold -w 400`, never whole files at once. Line numbers are those of `main` at `6692525`; the text wins.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, size cap D4, trailers). Also §8 (lines 135-139, the comment format) and §9 (lines 141-148).
- CLAUDE.md, the whole file; above all "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", and "브랜치·merge 절차" (document mode and the `Reviewed-by` trailer).
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15); .claude/skills/dev-code-review/SKILL.md (document-mode path).
- `PROCESS/tasks/T-0205-od18-run-tools-mock-script.md` `## Result`: the `**Review:**` bullet (R6 and R7) and the `**Follow-ups:**` first bullet (the minor as given).
- `PROCESS/tasks/T-0193-adr-0061-r7-nits.md` `## Acceptance Criteria` and `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` line 14: the model for the Status bullet of an edit after acceptance and for recording the re-check.
- `ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md`: Status (lines 3-14), decision 4 (lines 57-72, above all 60-66), Limits (lines 112-122), Alternatives considered (lines 123-137, row at line 133).
- For the arithmetic: `ARCHITECTURE/decisions/ADR-0007-*.md` decisions 4 and 8 (stopping rule, `n_min`, `cv_max`, `n_max`), `ARCHITECTURE/decisions/ADR-0009-*.md` decision 7 (the replay of every proper prefix), and `hilclaw/harness/measurement.py` (`N_MIN`, `CV_MAX`, `stopping_state`) — read only.
- `ARCHITECTURE/OpenDecisionProposals.md` line 316 (the ADR-0066 채택분 bullet of OD-18; the parenthesis is in item ⑶).
- `ARCHITECTURE/StandardScenarios.md`: 검사 규칙 (lines 13-28), the `# 검사 결과` heading (line 168), and the 2026-10-15 paragraphs (above all 11차 at line 220 for the steps it re-checked, and an earlier nit-fix paragraph of the same date, such as the one T-0197 or T-0193 added, as the model).
- Read only, to confirm nothing there must change: the OD-18 row of `ARCHITECTURE/Requirements.md` (search for `ADR-0066`).

## Acceptance Criteria

1. **ADR-0066**:
   - **Decision 4 (iii) (line 65)**: no longer says that no such report exists. It says, in substance as in planner reading 1, that a converged report reading neither constant exists only when its values are tuned to a narrow window around the value of `cv_max`, and why that is weaker than (i) and (ii) (it rests on the value of `cv_max`, not on a bound of it). The argument from ADR-0007 decision 4 stays cited. If the executor finds a further, correct reason (for example how `n_max` = `n_min` bears on it), it may be stated in one clause; nothing beyond the finding is added.
   - **Alternatives row (line 133)** agrees with the new (iii).
   - **"The choice is (i)" is unchanged**, and so are (i), (ii), the values, the figure, decision 5, decision 6, the Walk-through, the Limits, Consequences and Boundaries. No decision changes meaning.
   - **One Status bullet** is added after ADR-0060 line 14's pattern: "Edited after acceptance on <execution date> by task T-0207 (document mode)", the (iii) and Alternatives-row edit in one line, a note that the OpenDecisionProposals OD-18 bullet was aligned, and "no decision changed meaning". The objection window of the notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6194231066 (ends 2026-10-22) is unchanged.
2. **OpenDecisionProposals line 316**: the parenthesis "(존재하지 않는다)" after "두 상수를 읽지 않는 수렴 보고" says the same as the new (iii), in Korean like its neighbours. Nothing else on the line changes. If a further copy of the claim is found elsewhere in `ARCHITECTURE/`, it is aligned in the same way and named in `## Result`; if that copy is in `Requirements.md`, it is not edited here but recorded as a follow-up.
3. **StandardScenarios**:
   - The coverage re-check (CLAUDE.md "문서 커버리지 재검사") is run by the 검사 규칙 over the steps the 2026-10-15 11차 paragraph re-checked.
   - The result is recorded as a clause appended to the `# 검사 결과` heading list and as one `**2026-10-15 (12차, ...)**` paragraph (or the next free ordinal for the execution date), in Korean like its neighbours, after the model of an earlier nit-fix paragraph. It names the edits and gives the verdict: no verdict change and no gap, if that is what the re-check finds.
   - No scenario step or 비고 row is edited; the 11차 paragraph is unchanged.
4. **No other file changes.** `Requirements.md` stays untouched: OD-18 stays `제안됨`. `README.md`, `PROCESS/PLAN.md`, `PROCESS/DRIVER.md`, CLAUDE.md, other ADRs, `hilclaw/` (including `hilclaw/mock_run.py`), tests and CI stay untouched.
5. **Guarded exit.** If the executor or the reviewer finds that the minor is wrong (no converged report reading neither constant can be built under (ii)'s standard), leave ADR-0066 unchanged, record the argument in `## Result`, and finish DONE with no landing commit only if no file changed; otherwise land just what is correct. If a fix would change what ADR-0066 decides (for example, reopen the choice of (i)), leave it unapplied and record it as a follow-up; do not invent a rule or an OD. If leaving it out keeps a wrong statement in the record, return BLOCKED ("requirement unclear").
6. **Document checks.** Every relative link in edited lines resolves. `git diff --check` is clean, line endings are LF, and `git diff --stat origin/main` lists the three files only.
7. **`## Result`** records the landed commit, the review rounds and findings, the exact new wording of each edit, the arithmetic the executor relied on (one or two lines, or a short example), the re-check outcome, any follow-up left, and any reviewer judgement on editing an accepted record in place during its objection window.

### Process

- Work only in the driver's dedicated clone. First do the §3-5 landed check: `git log origin/main --grep='^Task: T-0207'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0207 --state all`. Then do the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open`, and issues #4, #5, #7, #8. An open PR that edits ADR-0066, the OD-18 passages of OpenDecisionProposals or the 검사 결과 section makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6194231066 (the ADR-0066 notice). Skip the driver's own comments, which end `— posted by driver`. An owner objection to ADR-0066 makes the task BLOCKED ("requirement unclear"); quote it. An answer to HQ-0013, HQ-0014 or HQ-0016..HQ-0019 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built. Running `python` to check the arithmetic against `hilclaw.harness.measurement.stopping_state` is allowed and is an observation, not part of the record. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0207-adr-0066-r7-minor` from `origin/main`; **no PR**. Run the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this file's path. Allow at most 7 rounds; past the cap without a final Approve, the task is BLOCKED. A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, the task is BLOCKED; do not review your own work. Ask the reviewer to (a) re-check the planner's reading in `## Why` and the arithmetic against the cited lines, (b) confirm that no decision changed meaning and the choice stays (i), and (c) run the coverage re-check independently.
- **Landing**:
  - `git fetch origin`, rebase onto `origin/main`, and squash to one commit (`git reset --soft origin/main` after the rebase). A rebase that changed content goes back to review.
  - `git push origin HEAD:main` (fast-forward). If rejected: fetch, rebase, and retry at most 3 times.
  - Commit message in English. The subject starts with `T-0207:`. The body names the correction and the coverage outcome, and says that nothing was built.
  - Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0207`, then any attribution trailer the session requires.
  - Delete the task branch only after the push is confirmed, remote and local in separate commands. Then check out `main` at `origin/main`.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`. Do not edit `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call means BLOCKED; do not work around it. If the task-branch push is rejected, rebase and retry once, then return BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- Fill in `## Result` on `main` after the push and leave it uncommitted for the driver (DRIVER §3-6). `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- Any change to the choice of (i), the default script's report, values or figure, and any change to `hilclaw/mock_run.py` or its tests.
- The "now less exact" sentences of other records that ADR-0066 Consequences lists; this task edits none of them.
- OD-18 sub-question ⑲ (가)-(라) (the run tool functions, their registration and the backend tool-failure kinds), binding the mock's operations into a backend or the default registry, and the operation of `cpu_standin`.

## Follow-ups

- (planner, document mode, §9, P1-1) The next run-tools contract slice: OD-18 sub-question ⑲ — the tool functions of `sim.run` / `board.run` and their registration over the mock (ADR-0061 to ADR-0066 Consequences), in the manner of the earlier ADRs of this contract.

## Result
