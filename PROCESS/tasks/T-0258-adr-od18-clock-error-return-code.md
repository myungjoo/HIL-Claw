---
id: T-0258
title: Write ADR-0085 on what the `returncode` of `CompilerRunError` (T-0257) lets `correctness.check` place for a failed clock read after the compiler ended by itself (more of OD-18 sub-question 18 part (ma))
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0256, T-0257]
touchesFiles: [ARCHITECTURE/decisions/ADR-0085-od18-correctness-check-clock-error-return-code.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0084 decision 3 kept one source of `CompilerRunError` open under OD-18 sub-question 18 part (ma): an `OSError` from reading the clock (`duration_s = time.monotonic() - started`) after the compiler process had ended by itself. It gave two reasons, both about what `clang_build.build` stated at `8782cf8`:

- **"It is not told apart"** from an error from closing the process after a read that ended (both: `timed_out` false, `log` all the output).
- **"The row would depend on a status that is not stated"**: `CompilerRunError` did not carry the return code.

The first item of its "What would let it be placed" was a code change that states that return code and tells the source apart from the closing source; "Then a record can weigh S7 for a non-zero status, with its log, by the value O1 gave." T-0257 (PR #162, `2124a33`) made that change: `CompilerRunError` now has a keyword-only `returncode`, which is not `None` only for a failed clock read after a normal end (0, a non-zero status, or a negative signal number on POSIX), and is `None` for every other source, including the closing source and a clock read after a kill for the time limit (T-0257 Result; class docstring in `hilclaw/clang_build.py`).

This task writes the record ADR-0084 named: a design-level ADR under DRIVER §9 that weighs, for `correctness.check` of the first case and of the mock, what the operation now observes for that source and places what it can. OD-18 is a design-level OD (not owner-only under §9), so the ADR is in scope.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming convention, size limits), §8 (driver tail on #5 comments), §9 (OD closing authority, 7-day notice).
- `CLAUDE.md` (repository root): "미결은 발명하지 않는다", "문서 커버리지 재검사", "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0084-od18-correctness-check-clock-error-after-end.md` — all of it; above all C1 to C4, decision 3 (its reasons, its cost and "What would let it be placed"), the walk-through, Alternatives (c), (d), (f), (g), and Consequences.
- `ARCHITECTURE/decisions/ADR-0082-od18-correctness-check-compiler-run-error-time-limit.md` — Context L2, L4, L5; decisions 1 to 5.
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md` — decisions 1 and 2.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` — Status (whose content), Context O1 and O2 (line 20 onward), decision 4 (the rows S3 to S10, the reading of a negative `returncode` as S7, "What the operation observes decides the row"), decision 5.
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md` — decisions 2, 6 and 7.
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md` — decision 1 (terms, the keeper) and the `TemporaryNotRemovedError` reading of a carried build (S7 by a non-zero `returncode`, S9 by `returncode` 0 and `ok` false); decision 5.
- `ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md` — decisions 3 and 4 (for the open entries this record does not touch).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` — decision 5 (the list of situations, S7 and S9 wording).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` — decisions 4 and 5 (`operation_answer_invalid`).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` — "Record format" section.
- `hilclaw/clang_build.py` at `2124a33`: the `CompilerRunError` class (around lines 99-138) and the body of `build` around `_communicate` (around lines 280-335). Read only; do not edit.
- `PROCESS/tasks/T-0257-clang-build-run-error-states-return-code.md` — Result and Follow-ups.
- `ARCHITECTURE/Requirements.md` — the "행 형식" paragraph (line 84) and register row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md` — the "기록 규칙" bullet in the header (line 8) and section `## OD-18` (from line 250; the 채택분 lines and sub-question 18 bullet near lines 296-309).
- `ARCHITECTURE/StandardScenarios.md` — line 26, the first paragraph of `# 검사 결과` (line 170, the recording rule), the "최근 재검사" line, and the verdict rows that cite OD-18.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): before editing, check `gh pr list` and issues #4, #5, #7, #8 for anything touching OD-18 sub-question 18 or the files above; if an open PR edits the same sections, stop and return BLOCKED (open-PR conflict risk). Confirm that `ADR-0085` is still the next free ADR number and that no owner comment on #5 (one without the driver tail) speaks to ADR-0084, T-0257 or (ma); if one does, cite it and follow it.
2. **New file** `ARCHITECTURE/decisions/ADR-0085-od18-correctness-check-clock-error-return-code.md` in the ADR-0001 record format, Status "Accepted under DRIVER §9 (D6)", stating which sentences are the owner's (O1, O2 quoted word for word as ADR-0060 Context quotes them), which are cited, and which are this record's own design; statements about code are observations at `2124a33` and bind no code.
3. **What the record must weigh and answer** (the answers are the record's own design, reviewed under §9; each choice states its reason and its cost):
   - (a) Whether the operation can now tell a failed clock read after a normal end apart from the closing source and the other sources of the `timed_out`-false branch, from what `build` states alone (the class, `timed_out`, `returncode`), and on which reading of ADR-0060 decision 4 "What the operation observes decides the row".
   - (b) The row of such an error with a **non-zero** `returncode`, a negative signal number on POSIX included: weigh S7, `(B)` `"build_exit_status"`, by O1, against the cost that the artefact step never ran and the duration was not read; state which reading ADR-0084 decision 3 gave ("Not for the reason that entry gives", "a compiler the call lost while it ran") and whether it still holds.
   - (c) Whether and when the operation hands `log` over for that row (ADR-0078 decisions 2, 6, 7; ADR-0082 decision 3 as the precedent), and what that does to the cost ADR-0084 decision 3 stated against ADR-0078 decision 2 and O2.
   - (d) The case `returncode` 0 (the artefact removed untested with the temporary file): weigh reading an existing row's wording (S9 or another) to cover it against leaving it open. **No new value of `error.kind` or `condition`, no new member, no new reserved kind, no `schema_version` or layout version change** (CLAUDE.md A-13 data-plane rule). If the record finds that only a new value would place it, it leaves the case open, says so, and names in Follow-ups that placing it needs an owner HQ — it does not decide it.
   - (e) The closing source (and the first read, the kill after it) stays with the open entry of ADR-0082 decision 4 unless (a) shows otherwise; the record says what it leaves open, in a "How far (ma) is answered" decision as ADR-0084 decision 5 has it.
   - A walk-through table and an Alternatives table covering at least: S7 for non-zero (chosen or not), leaving all open, S9 for status 0, a new kind for status 0 (declined as data-plane change).
4. **No sentence of an earlier ADR is edited.** Consequences lists the sentences of ADR-0081, ADR-0082, ADR-0083 and ADR-0084 that become less exact, as ADR-0084 Consequences does. Consequences states what a later code task of the `cpu_standin` operation applies, and that this record binds no code; "Runtime acceptance items" is stated (expected: none; no `claude`, compiler or container is started or required).
5. **Register and proposals edits follow the recording rules written in those files**, not the wording of earlier task files:
   - `ARCHITECTURE/Requirements.md` row OD-18: as the "행 형식" paragraph (line 84) says — one ADR link added under `**확정분**:`, `**잔여**:` rewritten in place; no restatement of the record, no dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md` section OD-18: as the header "기록 규칙" (line 8) says — one `**채택분**` line for ADR-0085, the status at the end of sub-question 18 (and its bullet's status word) rewritten in place; question wording kept.
   - `ARCHITECTURE/StandardScenarios.md`: recheck coverage by the rules of that file for every scenario row citing OD-18, and update `# 검사 결과` exactly as its first paragraph says (rewrite the "최근 재검사" line; add to "판정 변화 이력" only if a verdict changed or a gap was found or closed).
   - OD-18 keeps its status word unless the record closes all of it (it will not).
6. Document mode (CLAUDE.md A-13): branch `claude/T-0258-<slug>`, reviewer cycle (dev-item-address steps 10-12) until Approve, rebase on `origin/main`, direct push to `main`, commit message with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0258` trailers. After landing, post the §9 notice on issue #5 in English, ending with the line `— posted by driver` (DRIVER §8), and record its URL in `## Result`.
7. Size: one new file plus three edited files; at most 300 changed lines in total.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or settings files; any change to ADR-0001 to ADR-0084 or to UsageCases.
- The row of a plain `OSError` of `build` (ADR-0084 decision 4) and the other open entries of (ma) (ADR-0084 decision 5), except to restate them as still open.
- (ga), (da), (ra) and the size bound of (na) of sub-question 18; sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any new data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).
- Starting `claude`, a compiler or a container, or running code to establish facts about the clock (observations are from reading the source).

## Follow-ups

- (code, candidate next task) Make `clang_build.build` tell the source path tests from the output path tests, and both from the other lines before the start (ADR-0083 decision 3, ADR-0084 decision 4).
- (possible HQ) If ADR-0085 leaves `returncode` 0 open because only a new `error.kind` would place it, the driver records that question for the owner.

## Result

- DONE. Document mode: landed on `main` as `55d4760` (direct push after rebase on `origin/main`; trailers `Reviewed-by: reviewer agent (6 rounds, Approve)`, `Task: T-0258`); branch `claude/T-0258-clock-error-return-code` deleted.
- Review: 6 rounds, context-isolated `dev-reviewer`. Round 1 asked for changes: register and proposal lines restated the answers, and the less-exact list was incomplete. Round 2 approved with nits. Round 3 asked for changes: less-exact entries of ADR-0082 and ADR-0083 were missing. Rounds 4 and 5 approved with nits. Round 6 approved with no findings.
- Session entry check (2026-10-17): no open PR; no owner comment on #4, #5, #7 or #8 since 2026-10-16 without the driver tail; ADR-0085 was the next free number.
- ADR-0085: a `CompilerRunError` whose `returncode` is not `None` is told apart as a failed clock read after a normal end. A non-zero value (a negative signal included) is S7 `(B) "build_exit_status"`, and 0 is S9 `build_output_missing`, on ADR-0080 decision 3's reading. Both hand `log` over to the keeper. The branch with `timed_out` false and `returncode` `None` (first read, kill after it, closing source) stays open. No data-plane change; no earlier ADR edited.
- Register: OD-18 row gained one `**확정분**` link (`**잔여**` "(마)의 나머지" still exact, unchanged); proposals gained one `**채택분**` line and the ⑱ status/남음 was rewritten in place (status word 일부 답함 kept); StandardScenarios "최근 재검사" rewritten (S0, S1-b, S2, S5, S6: no verdict change, no gap). OD-18 status word unchanged.
- Size: 4 files, +128/-3.
- §9 notice on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6229982692 (objection window until 2026-10-24).
- Runtime acceptance items: none.
- Follow-ups: the first follow-up (telling the source path tests from the output path tests) is unchanged. The possible HQ for `returncode` 0 is not needed, since S9 places it without a new value.
