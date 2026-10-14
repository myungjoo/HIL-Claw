---
id: T-0181
title: Clear the four non-blocking round-7 review nits of T-0179 - ADR-0058 cites OD-12 for "a coder chooses a technique itself" (it is OD-23; OD-12 is the coder's own search), gives ADR-0035 a purpose in its own words, says "sha256-derived" instead of ADR-0002's wording, and the StandardScenarios 2026-10-14 (3차) paragraph misses S0-4; coverage re-check recorded
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-6, OD-12, OD-23, "CLAUDE.md 문서 커버리지 재검사"]
dependsOn: [T-0179, T-0180]
touchesFiles: [ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 20, files: 2}   # three or four phrases and one Status bullet in ADR-0058; one OD citation, one step id, one heading clause and one dated paragraph in StandardScenarios
hq: []
---
## Why

T-0179 landed ADR-0058 (aa00f86) after 7 review rounds, the last allowed. Round 7 approved with four non-blocking findings that were deliberately not applied, because a change after the last round would have landed unreviewed text (`PROCESS/tasks/T-0179-adr-od6-committed-gemm-spec-example.md` `## Follow-ups`). T-0180 (5f5621a) then landed the example file and its test, and P1-5 is ticked; its `## Follow-ups` repeats this item.

All four are corrections of citation or wording. None needs a design decision, changes an OD status or touches a data-plane schema. This task ticks **no PLAN checkbox** and decides nothing.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-14 after 8214105). Every non-DONE task is blocked by an unanswered HQ: HQ-0013, HQ-0014, HQ-0016..HQ-0019 (`runtime-acceptance`) and HQ-0020 (T-0176, `data-plane-schema-change`). P1-1 waits on HQ-0020; P1-8's next records and the P2 items rest on the run-tool contracts of P1-1; P0.5-4 waits on hook registration. This task depends on none of those HQs or their answers.

**Planner's checks of the four findings (the reviewer re-checks each):**
1. `ARCHITECTURE/Requirements.md` line 101, the OD-12 row, is "외부 참조 MCP 어댑터 설계 ... 코더의 직접 검색 허용 여부 ...". It is about the coder's own search of external references, not about whether a coder picks a technique when the spec names none. Line 112, the OD-23 row (subagent roster and input/output contracts), is where that question sits. ADR-0058 says "(OD-12, OD-23)" at line 37 (decision 1, "What the empty list says") and at line 143 (Boundaries, "OD-22 and FR-8" bullet). `ARCHITECTURE/StandardScenarios.md` line 194, part ⑵ of the 3차 paragraph, says "(OD-12·OD-23)".
2. ADR-0058 line 122, Alternatives row 3, says "ADR-0035 chose a fictitious one so that no reader takes the example for a real profile". ADR-0035 gives no such reason. Its own words (ADR-0035 line 120) are "A plainly fictitious machine — not the first real instance, not the driver machine and not the repository owner's PC." ADR-0058 line 52 already quotes them.
3. The 3차 paragraph (StandardScenarios line 194) lists the steps where a coder spec is written as "S0-8·9, S1-4 ...". S0-4 (the first code generation by a Claude Code CLI call, round 0 = bring-up + baseline, FR-5) also writes a spec and is missing from the list.
4. ADR-0058 line 67, decision 5 (a), says "each `key` is the sha256-derived name of its `record`". ADR-0002 line 154 (Consequences) says "each `key` equals the name derived from its `record` (`hilclaw.keys`)". The parenthesis already presents these rules as cited from ADR-0002 Consequences, so the wording must be ADR-0002's.

## Required Reading

Line numbers are those of `main` at `8214105`; the text wins. ARCHITECTURE lines are very long: read them with `sed -n '<line>p' | fold -w 400`, never whole files at once.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (lines 86-114: task format, naming, size cap D4, trailers). Also §8 (lines 135-139, the comment format) and §9 (lines 141-148).
- CLAUDE.md, the whole file; above all "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", and "브랜치·merge 절차" (document mode and the `Reviewed-by` trailer).
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 9 to 12 and 15); .claude/skills/dev-code-review/SKILL.md (document-mode path).
- `PROCESS/tasks/T-0179-adr-od6-committed-gemm-spec-example.md` `## Result`, last `**Follow-ups**` list (the four findings as the round-7 reviewer gave them).
- `PROCESS/tasks/T-0174-doc-nits-adr0055-adr0057-scenarios.md` `## Acceptance Criteria`: the model for how an accepted record is edited in place (a Status bullet stating the after-acceptance edit) and how the re-check is recorded.
- `ARCHITECTURE/decisions/ADR-0058-od6-committed-gemm-spec-example.md`: Status (lines 3-11), decision 1 (34-41), decision 3 (49-55), decision 5 (64-70), Alternatives (113-127), Boundaries (141-146).
- `ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md` line 120. `ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md` line 154.
- `ARCHITECTURE/Requirements.md` lines 101 (OD-12) and 112 (OD-23). Read only.
- `ARCHITECTURE/StandardScenarios.md`: 검사 규칙 (lines 13-28), S0 (lines 30-44), the `# 검사 결과` heading (line 168), and the 2026-10-14 paragraphs (lines 190-194).

## Acceptance Criteria

1. **ADR-0058**:
   - Decision 1 (line 37) and the Boundaries bullet "OD-22 and FR-8" (line 143): "(OD-12, OD-23)" becomes "(OD-23; the coder's own search is OD-12)". Nothing else in those sentences changes.
   - Alternatives row 3 (line 122): the reason given for ADR-0035 is replaced by ADR-0035's own words ("not the first real instance, not the driver machine and not the repository owner's PC"), or by a plain pointer to them. The row must not give ADR-0035 a purpose it does not state. The row's rejection still holds.
   - Decision 5 (a) (line 67): "each `key` is the sha256-derived name of its `record`" becomes "each `key` is the name derived from its `record` (`hilclaw.keys`)". Nothing else in (a) changes.
   - One Status bullet is added. It says the record was edited after acceptance on the execution date by T-0181, lists the three edits in one line, and says no decision changed meaning. The objection window of the 2026-10-14 notice is unchanged.
   - No decision, limit, boundary, Example line or Consequences item changes meaning.
2. **StandardScenarios**:
   - In the 2026-10-14 (3차) paragraph, part ⑵: "(OD-12·OD-23)" becomes "(OD-23; 코더의 직접 검색은 OD-12)" or an equivalent Korean clause with the same split. In the step list at its start, S0-4 is added to the steps where a coder spec is written (for example "S0-4·8·9"). Nothing else in that paragraph changes.
   - The coverage re-check is run by the 검사 규칙 over the steps of the 3차 paragraph with S0-4 added. S0-4 is judged on its own: its cited basis (FR-5, FR-1 round 0) is untouched by ADR-0058.
   - The result is recorded as a clause appended to the `# 검사 결과` heading list and as one `**2026-10-14 (4차, ...)**` paragraph, or the next free ordinal for the execution date. The paragraph names the edits and gives the verdict: no change and no gap, if that is what the re-check finds.
   - No scenario step or 비고 row is edited.
3. **No other file changes.** `Requirements.md` and `OpenDecisionProposals.md` stay untouched: no OD row or status changes. `README.md`, `PROCESS/PLAN.md`, `PROCESS/DRIVER.md`, CLAUDE.md, code, tests and `examples/` also stay untouched.
4. **Guarded exit.** If the reviewer or the executor finds that a fix would change what ADR-0058 decides, or that OD-23 is also the wrong citation and no register row fits, leave that finding unapplied. Record it in `## Result` as a follow-up; do not invent an OD. If the finding cannot be left out without a wrong statement remaining, return BLOCKED ("requirement unclear").
5. **Document checks.** Every relative link in edited lines resolves. `git diff --check` is clean, line endings are LF, and the diff stays within 2 files.
6. **`## Result`** records the landed commit, the review rounds and findings, the re-check outcome, and any reviewer judgement on editing an accepted record in place during its objection window.

### Process

- Work only in the driver's dedicated clone. First do the §3-5 landed check: `git log origin/main --grep='^Task: T-0181'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0181 --state all`. Then do the session entry check of CLAUDE.md: `gh pr list --repo myungjoo/HIL-Claw --state open`, and issues #4, #5, #7, #8. An open PR that edits ADR-0058 or the 검사 결과 section makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after `https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6166739084` (the ADR-0058 notice). Skip the driver's own comments, which end `— posted by driver`. An owner objection to ADR-0058 makes the task BLOCKED ("requirement unclear"); quote it. An answer to HQ-0013, HQ-0014 or HQ-0016..HQ-0020 does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built or run. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0181-doc-nits-adr0058-scenarios` from `origin/main`; **no PR**. Run the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round, given the branch name and this file's path. Allow at most 7 rounds; past the cap without a final Approve, the task is BLOCKED. A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, the task is BLOCKED; do not review your own work. Ask the reviewer to (a) re-check the four planner checks in `## Why` against the cited lines, (b) confirm that no decision changed meaning, and (c) run the coverage re-check independently.
- **Landing**:
  - `git fetch origin`, rebase onto `origin/main`, and squash to one commit (`git reset --soft origin/main` after the rebase). A rebase that changed content goes back to review.
  - `git push origin HEAD:main` (fast-forward). If rejected: fetch, rebase, and retry at most 3 times.
  - Commit message in English. The subject starts with `T-0181:`. The body names the four corrections and the coverage outcome, and says that nothing was built or run.
  - Trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0181`, then any attribution trailer the session requires.
  - Delete the task branch only after the push is confirmed, remote and local in separate commands. Then check out `main` at `origin/main`.
- **Prohibitions**: never `git push --force*` / `-f`, never a recursive forced remove, never `gh repo delete`. Do not edit `.claude/settings.json` or `.claude/settings.local.json`. A denied or failed tool call means BLOCKED; do not work around it. If the task-branch push is rejected, rebase and retry once, then return BLOCKED (`branch-contention`). Past 2h30m of wall-clock time, return BLOCKED (`task-timeout`) with the state in `## Result`.
- Fill in `## Result` on `main` after the push and leave it uncommitted for the driver (DRIVER §3-6). `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Return a summary of at most 200 characters.

## Out of Scope

- The "now less exact" sentences of other records that ADR-0058 point 7 lists (ADR-0002, ADR-0050, ADR-0035, ADR-0029, ADR-0008, ADR-0004). This task edits none of them.
- Any change to what ADR-0058 decides, to `examples/spec/gemm-485b9bc494d477eb.json`, to `tests/test_spec_example.py` or to any code.
- OD-12, OD-22 and OD-23 contents and statuses; the technique catalog.
- OD-18 sub-question 17 and HQ-0020 (T-0176); the P1-1 run-tool contracts.

## Follow-ups

- (driver/planner) T-0176 stays BLOCKED until HQ-0020 is answered; P1-1 and what rests on it wait with it.

## Result
