---
id: T-0235
title: Correct ADR-0072 and ADR-0071 after acceptance - the two round-7 nits of T-0222 (a present but invalid verdicts file in the Promotion boundary; a run_id collision finds the case name taken) and the round-4 nit of T-0218 (OD-19 beside OD-20 / OD-29 in ADR-0071 decision 1) - each with an after-acceptance Status bullet; no other file
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-30, FR-17, FR-18, "#5 D6"]
dependsOn: [T-0218, T-0222]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md   # existing record; nits (a) and (b) plus a Status bullet
  - ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md      # existing record; nit (c) plus a Status bullet
estimatedSize: {loc: 12, files: 2}
hq: []
---
## Why

Two accepted OD-30 records carry reviewer nits that were recorded as follow-ups and never applied.

- **ADR-0072** (T-0222, landed as `b7ab953`; 7 review rounds, the last allowed). Round 7 approved with two nits that were left unapplied because the cap was reached. `PROCESS/tasks/T-0222-adr-od30-case-file.md`, `## Result`, the **Review** bullet (line 119), records them:
  - (a) "Boundaries could name a round whose verdicts file is present but invalid";
  - (b) "decision 1 could add that a `run_id` collision ADR-0027 decision 5 does not exclude finds the name taken and replaces nothing".
  The **Follow-ups** bullet (line 121) lists "the two R7 nits above in a later correction". T-0223, T-0224 and T-0225 repeat "the two R7 nits of T-0222" as a follow-up. `git log -- ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md` shows only `b7ab953`, so neither nit has been applied.
- **ADR-0071** (T-0218, landed as `5ab4767`). Round 4 approved with one optional nit, left unapplied: "decision 1 could also name OD-19 beside OD-20 / OD-29" (`PROCESS/tasks/T-0218-adr-od30-hypothesis-verdict.md`, `## Result`, **Review** bullet, line 122). Call it nit (c). It is an accuracy point, not a style point. ADR-0071 decision 1 (line 27) says "**It does not pre-empt what OD-20 and OD-29 keep**: it holds no ranking, no record of which attempts went to the board, no cost, … — the round-level files ADR-0004 decision 3 lists for them". ADR-0004 (line 92) leaves those files to "OD-20, OD-29 and OD-19", and ADR-0071's own Context (line 16) quotes all three. "Cost" is OD-19's (budgets and spend).

Both records are inside their objection windows: the ADR-0071 notice is https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125 and the ADR-0072 notice is https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6208691987, both until 2026-10-23. This is a correction of accepted records during their windows. It needs no design decision, changes no decision's meaning, changes no OD status and touches no data-plane schema. It ticks **no PLAN checkbox** (P2-6 and P2-7 continue). Earlier corrections of the same kind, each with an after-acceptance Status bullet: T-0234 (ADR-0075), T-0230 (ADR-0073), T-0217 (ADR-0070), T-0213 (ADR-0069).

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-16 at `c4aad96`). Every other candidate is blocked:
- T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023) and T-0233 (HQ-0024) are BLOCKED.
- The P2-8 metric tool rests on ADR-0074, which is unlanded (T-0231).
- The cross-file check of `hypotheses.json` against `instance.json` `injections` rests on T-0233, which is unlanded.
- P1-1's run tools rest on T-0210. P1-8 and P2-1 to P2-4 need roster or hook decisions (OD-23, OD-16, OD-18) that are not landed.
- Any new ADR or register edit would touch `ARCHITECTURE/Requirements.md`, `OpenDecisionProposals.md` and `StandardScenarios.md`, which are in the diffs of the BLOCKED T-0210 and T-0231.
- P0.5-4 waits on the owner's hook registration.

The diffs of the unlanded branches were checked: `claude/T-0210-*` and `claude/T-0231-*` each add one ADR (ADR-0068, ADR-0074) and edit the three registers; `claude/T-0225-*` and `claude/T-0233-*` edit only `hilclaw/` and `tests/`. None of them edits ADR-0071 or ADR-0072. Do not read those branches for content, depend on them or reconcile with them.

**Planner's reading** (line numbers of `main` at `c4aad96`; the executor and the reviewer re-check each one; the text wins):

- **Nit (a), ADR-0072.** Line 132 is the Boundaries bullet **Promotion**. It already holds open "what promotion does with a round whose pair of files breaks the rules of ADR-0071 (it can have no case)" and "whether a round without verdicts is promoted". It does not name a round whose `verdicts.json` is **present but invalid**. By decision 3 (line 58) a case that holds `verdict_record` needs each copy to be valid by its own record. By ADR-0071 decision 2 (line 47) "An invalid file is reported, no member of it is used". By decision 3 of ADR-0072 (line 59) an absent `verdict_record` "means only that the round's tree held no verdicts file when the case was written". So the planner reads it this way: such a round has no valid case with `verdict_record`, and a case without it would state something untrue. What promotion does with such a round is open, like its neighbours in the bullet. The executor states only what the cited texts support. The new item must not decide whether such a round is promoted.
- **Nit (b), ADR-0072.** Line 27 is decision 1's "**The name is unique**" bullet. It cites ADR-0004 decision 8 ("a `run_id` is unique within `runs/`"; ADR-0004 line 129). ADR-0027 decision 5 (lines 57-63, above all line 62) says collisions of the built form are "improbable, not excluded", and that nothing on `main` notices one. Line 31 (the write) says that the last step "gives the final name only if it does not exist, with no fallback to a replacing rename; a taken name is reported". So the planner reads the consequence like this. If two runs ever share a `run_id` (ADR-0027 decision 5 does not exclude that), the second case write of a shared (`run_id`, round) in one key directory finds the name taken: it replaces nothing and is reported. The sentence adds no rule. It also does not say what follows the report: line 132 already holds "what a second case write for a round means after its name was taken" open.
- **Nit (c), ADR-0071.** In line 27, change "what OD-20 and OD-29 keep" so that it also names OD-19. For example: "what OD-20, OD-29 and OD-19 keep", or name OD-19 for the cost. Choose what fits ADR-0004 line 92 and ADR-0071 line 16 exactly. "for them" at the end of that dash clause must still refer correctly. No other word of the bullet changes.

## Required Reading

ARCHITECTURE lines are very long: read them with `sed -n '<line>p' <file> | fold -w 400`, not whole files at once. Line numbers are those of `main` at `c4aad96`; the text wins.

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, the 2h30m limit) and **§5** (task format, naming, size cap D4, trailers). Also read §2 (document mode), §8 (comment format) and §9.
- `CLAUDE.md`, whole. Above all: "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16) and "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` (document mode: steps 9 to 12 and 15) and `.claude/skills/dev-code-review/SKILL.md` (document-mode path).
- `PROCESS/tasks/T-0222-adr-od30-case-file.md` lines 119 and 121 (the R7 nits (a), (b) as recorded). `PROCESS/tasks/T-0218-adr-od30-hypothesis-verdict.md` line 122 (the round-4 nit (c) as recorded).
- `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md`: Status (lines 3-9), decision 1 (lines 22-32), decision 3 (lines 51-60), Boundaries (lines 127-141), References (lines 143-149).
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: Status (lines 3-9), Context line 16, decision 1 (lines 24-31), decision 2 line 47.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md` lines 88-92 (the decision that line 92 belongs to: check that it is decision 3) and line 129 (decision 8). Read only.
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md` decision 5 (lines 57-63). Read only.
- `ARCHITECTURE/decisions/ADR-0075-od30-injection-at-instance-start.md` line 10 and `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md` line 10: two forms of an "Edited after acceptance" Status bullet. Read only. Do not copy their wording.

## Acceptance Criteria

1. **ADR-0072. Make only these edits:**
   - **Nit (a)**: the Boundaries bullet **Promotion** (line 132) adds, as one more open item, what promotion does with a round whose `verdicts.json` is present but invalid. Cite ADR-0071 decision 2 and this record's decision 3 only as far as they support it. Keep it to one clause or one short sentence in the bullet's existing style. Do not decide whether such a round is promoted, whether its case is written without `verdict_record`, or what a reader does. If the executor finds that the bullet already covers this case (for example, under "a round whose pair of files breaks the rules of ADR-0071"), leave the bullet unchanged and argue so in `## Result`.
   - **Nit (b)**: decision 1's "**The name is unique**" bullet (line 27) adds one or two sentences. They say that ADR-0027 decision 5 leaves collisions of the built form improbable and not excluded, and that a case write whose name is then already taken in the key directory replaces nothing and reports the taken name, by the write of this decision (line 31). Add no new rule and no remedy. Point to the open item of line 132 ("what a second case write for a round means after its name was taken") rather than restating it. Add ADR-0027 (decision 5) to the Status "builds on" sentence (line 7) and to References (line 147, where ADR-0027 is listed as "(example)") only if the edit newly cites it.
   - **One new last Status bullet**, after line 9. It says the record was edited after acceptance on the execution date by task T-0235 (document mode). It names the edits briefly. It says that no decision changed meaning and that the objection window of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6208691987 (until 2026-10-23) is unchanged. Write it in this record's own words.
   - Nothing else of ADR-0072 changes: decisions 2 to 4, the Example, Alternatives, Consequences (including the "Not edited and now less exact" list and its A-13 reading), the other Boundaries bullets (including line 140 on the S6 metric) and References, except an entry that an edit newly cites.
2. **ADR-0071. Make only these edits:**
   - **Nit (c)**: decision 1, line 27, names OD-19 beside OD-20 and OD-29 where it lists who keeps the round-level files that ADR-0004 decision 3 leaves open. The wording must match ADR-0004 line 92 ("OD-20, OD-29 and OD-19") and must keep the dash clause's "for them" correct. No other word of that bullet changes.
   - **One new last Status bullet**, after line 9. It says the record was edited after acceptance on the execution date by task T-0235 (document mode), for that one citation. It says that no decision changed meaning and that the objection window of https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125 (until 2026-10-23) is unchanged.
   - Nothing else of ADR-0071 changes. This includes its "Not edited and now less exact" list and its Boundaries.
3. **No other file changes.** This includes `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md`, `ARCHITECTURE/StandardScenarios.md`, `ARCHITECTURE/UsageCases.md`, every other ADR, `README.md`, `PROCESS/` (except this task file's `## Result`, written by the executor as DRIVER §3-5 says), `CLAUDE.md`, `.claude/`, `hilclaw/`, tests and CI. No register file changes, so no coverage re-check is due (CLAUDE.md "문서 커버리지 재검사" covers Requirements, UsageCases and StandardScenarios). Say so in `## Result`.
4. **Guarded exit**: if a nit turns out wrong on the cited texts, leave that part unchanged and give the argument in `## Result`. If a fix would change what ADR-0071 or ADR-0072 decides, leave it unapplied and record it as a follow-up. Do not invent a rule or an OD. A record none of whose edits is applied gets no Status bullet. If no edit is applied at all, finish DONE with no landing commit.
5. **Document checks**: every relative link in edited lines resolves; `git diff --check` is clean; line endings are LF; `git diff --stat origin/main` lists only files in `touchesFiles`.
6. **`## Result`** records the landed commit, the review rounds and their findings, the exact new wording of each edit, any part left unchanged and why, and any remaining follow-up.

### Process

- Work only in the driver's dedicated clone. First do the §3-5 landed check: `git log origin/main --grep='^Task: T-0235'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0235 --state all`. Then do the CLAUDE.md session entry check: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8. An open PR that edits ADR-0071 or ADR-0072 makes the task BLOCKED ("open PR conflict"). None was open at planning time.
- Read the comments on issue #5 after https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6206950125 (the ADR-0071 notice). Skip the driver's own comments (last line `— posted by driver`). An owner objection to ADR-0071 or ADR-0072 makes the task BLOCKED ("requirement unclear"); quote the objection. An answer to an open HQ (HQ-0021 to HQ-0024 among them) does not stop this task; name it in `## Result`.
- **D16**: neither the executor nor any agent it spawns starts the Claude Code program (`claude`) as a child process, with any subcommand or flag. Nothing is built or run except read-only git/gh commands, grep and link checks. Tell each reviewer to write no file and start no `claude` process.
- **Document mode** (CLAUDE.md A-13): branch `claude/T-0235-adr-0072-r7-nits-and-adr-0071-od19` from `origin/main`; **no PR**.
  - Run the reviewer cycle of dev-item-address steps 10 to 12 with a fresh-context `dev-reviewer` each round. Give it the branch name and this file's path.
  - Allow at most 7 rounds. Past the cap without a final Approve, the task is BLOCKED. A result starting with `SECURITY` is BLOCKED. If no reviewer can be spawned, the task is BLOCKED; do not review your own work.
  - Ask the reviewer to (a) check each edit against the nit as recorded and against the cited texts (ADR-0004 lines 92 and 129, ADR-0027 decision 5, ADR-0071 decision 2, ADR-0072 decisions 1 and 3), (b) confirm that no decision changed meaning and that nit (a) decides nothing about promotion, and (c) confirm that no file other than the two records changed.
- **Landing**:
  - `git fetch origin`, rebase onto `origin/main`, then squash to one commit (`git reset --soft origin/main` after the rebase). A rebase that changed content goes back to review.
  - Commit subject: `T-0235: correct ADR-0072 and ADR-0071 after acceptance (review nits)`. The body says what changed and why. It ends with `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0235` and the attribution line the session's system reminder gives.
  - Push to `main` directly (no force; DRIVER §3-5 branch-contention rule). Delete the task branch after landing.
- **No #5 notice**: no decision changes, as with T-0230 and T-0234. If the executor judges that an edit does change a decision, that edit is out of scope (criterion 4).

## Out of Scope

- The "Not edited and now less exact" items of ADR-0071 and ADR-0072 Consequences. They stay follow-ups for the integrator.
- The Boundaries line "The S6 metric, its boundary cases, repetitions and control (P2-8)" of ADR-0071 / ADR-0072. It becomes less exact only when ADR-0074 (T-0231, BLOCKED) lands, and that is the integrator's follow-up there.
- Registering the round promotion `runs/` → `db/` timing in the OD-29 row (T-0222 follow-up). It edits `ARCHITECTURE/Requirements.md`, which is in the diffs of the BLOCKED T-0210 and T-0231.
- Nit (e) of T-0232 R7 (OpenDecisionProposals ADR-0075 adopted line): same reason.
- Any register edit, coverage re-check, OD status change or new ADR. No code, no tests.

## Follow-ups

- (planner, document mode, after T-0210 / T-0231 land) The OD-29 row naming the round promotion `runs/` → `db/` timing (T-0222 follow-up) and nit (e) of T-0232 R7. Both edit register files of those branches.

## Result
