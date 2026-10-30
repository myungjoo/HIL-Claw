---
id: T-0264
title: Write ADR-0088 on which rows of `correctness.check` the `parameter` of a pre-start `TypeError` or `ValueError` of `local_run.run` (T-0263) lets an operation place (more of OD-18 sub-question 18 part (ma))
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0263]
touchesFiles: [ARCHITECTURE/decisions/ADR-0088-od18-correctness-check-local-run-parameter.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: [HQ-0027]
---
## Why

ADR-0060 decision 4 (the bullet "What the functions on `main` report, against the rows", line 102) lists, among the errors that "arise in one class in two rows", "a `ValueError` or `TypeError` of `local_run.run` for an `env` (S4) or for an argument the operation's own code formed". In the same bullet it answers the two halves differently:

- a `ValueError` or `TypeError` "for a setting — a time limit, a flag, the compiler" → S4 `settings_refused`, "whether the setting is refused for its value or for its type, as every setting is the backend's own";
- "a `TypeError` or `ValueError` of `local_run.run` for an argument its own code formed or an empty command" is an error the operation lets pass, answered `operation_answer_invalid` (cited there: ADR-0045 decisions 4 and 5).

ADR-0060 Consequences (line 157, "Telling the rows apart is a condition of the operation's code") leaves making them distinguishable to a code task. ADR-0087 decision 8 still lists "the `ValueError` or `TypeError` and the `OSError` for 'a `cwd` that does not exist' of `local_run.run`" as open under part (ma) of sub-question 18 of OD-18.

T-0263 (PR #165, `7994476`) made part of that change and placed no row. Every `TypeError` and `ValueError` that leaves one of the two checks `run` makes before the start now carries `parameter`:

- `"timeout_s"` from the check of the time limit (a `TypeError` for a non-number, a `ValueError` for a value that is not positive and finite);
- `"command"` from the check of the command (a `TypeError` for one `str` or `bytes`, a non-iterable, a program of the wrong type, a non-`str` argument; a `ValueError` for an empty command), including an error Python raises inside that check, re-raised as the same object.

No other error carries it: not `ProgramNotFoundError`, not a `TypeError` from binding the call, and nothing `subprocess` raises (an `OSError` from the start, a `ValueError` or `TypeError` for an `env` or `cwd` it cannot hand over, an `OverflowError`). See the `run` docstring (`hilclaw/local_run.py` lines 88-109) and T-0263 Result.

This task writes the record that weighs what `parameter` of `run` makes true for `correctness.check`. It is a design-level ADR under DRIVER §9. OD-18 is not owner-only under §9, so the ADR is in scope.

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025), T-0243 (HQ-0026). The runtime-acceptance HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019) do not bear on this record. None of the blocked tasks touches the four files, and this task depends on none of those HQs. HQ-0026 (the code of the `cpu_standin` operation of `correctness.check`) is not needed: this record binds no code. PLAN P1-1 continues through the OD-18 (ma) work. This is the doc follow-up named in T-0263 Follow-ups, the same step ADR-0087 (T-0262) took after T-0261.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, 2h30 time limit;
  - §5 (lines 86-114): task format, branch `claude/T-0264-<slug>`, trailer `Task: T-0264`, size cap;
  - §8 (lines 135-139): the driver tail on #5 comments;
  - §9 (lines 141-148): OD closing authority, the 7-day notice.
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode, `Reviewed-by` trailer), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`:
  - decision 3 (lines 46-68), above all the settings table: "Time limit of the build; time limit of the process" and "Environment" are the backend's own; "Path of the executable; working directory" are the operation's own;
  - decision 4 (lines 69-104): the situation table (S4, S10 rows), the bullet at line 102 with all its sentences on `local_run.run` (the two-row entries, "the rest", the `ProgramNotFoundError`/`OSError` → S10 sentence and the "`cwd` that does not exist" exception, and "An error the operation lets pass …"), and the bullet "What the operation observes decides the row" (line 103);
  - decision 5 (line 105 onward), on what an S4 message may say;
  - Consequences, the bullet at line 157.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`: whole file, as the direct precedent and latest model of this series (Status, Context observations, decisions 1 to 8, Walk-through, Alternatives, Consequences, Boundaries).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decisions 3 and 4 (who forms the paths and the command), decision 5 (lines 95-114, the situation list read against `local_run.run`).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 and 5 (lines 64-84), `operation_answer_invalid`.
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2 (which situations have a log).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (line 146).
- Code at `7994476` or later, read only, do not edit:
  - `hilclaw/local_run.py`: `run` (line 76) and its docstring (lines 77-115), `_parameter` (line 219), `_check_timeout` (line 228), `_resolve` (line 235);
  - `hilclaw/harness/verification.py`: the module docstring paragraph at lines 61-67 and `run_verification` (lines 224-285), which forms the command from `executable` and `program_arguments`, raises its own `TypeError`/`ValueError` for `executable` before calling `run`, and passes on what `run` raises.
- `PROCESS/tasks/T-0263-local-run-pre-start-error-parameter.md`: "The change, stated", Result, Follow-ups.
- The recording rules, read and followed as written:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet of the header (line 8), and section `## OD-18` (from line 250), including the 채택분 lines up to line 299 and the sub-question 18 bullet (line 312);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of `# 검사 결과` (line 170), the "최근 재검사" line (line 172), and the verdict rows whose notes cite OD-18.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md). Before editing:
   - Run `gh pr list` and read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0088` is still the next free number under `ARCHITECTURE/decisions/`.
   - Check #5 for an owner comment (one without the driver tail) that speaks to ADR-0060 decision 4, ADR-0087, T-0263 or (ma). If there is one, cite it and follow it.
2. **New file** `ARCHITECTURE/decisions/ADR-0088-od18-correctness-check-local-run-parameter.md`, in the ADR-0001 record format.
   - Status is "Accepted under DRIVER §9 (D6)". It says which sentences are the owner's, which are cited, and which are this record's own design.
   - Statements about code are observations at `7994476` (or the commit read) and bind no code. Nothing is established by running code.
3. **What the record must weigh and answer.** The answers are the record's own design, reviewed under §9. Each choice states its reason and its cost.
   - **(a) Telling the cases apart.** Can the operation now tell, from what `run` states alone (the class and `getattr(error, "parameter", None)`), a `TypeError` or `ValueError` for the time limit from one for the command, and both from one with no `parameter`? On the same reading of "What the operation observes decides the row" that ADR-0085, ADR-0086 and ADR-0087 took, or on a different one with its reason. Say what "an error of two rows" of ADR-0060 decision 4 still holds for and what it no longer holds for.
   - **(b) `"timeout_s"`.** Weigh S4 `settings_refused` for both classes, against ADR-0060 decision 3's table ("time limit of the process" is the backend's own) and the S4 row's wording. Say whether a `TypeError` Python raises inside that check is covered, as ADR-0087 decision 3 weighed for `clang_build.build`.
   - **(c) `"command"`.** Weigh no row (`operation_answer_invalid`, as the landed rules answer it) for both classes, against ADR-0056 decisions 3 and 4 (the operation forms the path of the executable and its arguments) and ADR-0060 decision 4's "an argument its own code formed or an empty command". Say whether this record changes what ADR-0060 decision 4 says or only applies it. Say whether a program of the wrong type that comes from the backend's side (for example a command prefix, if any reading of ADR-0060 decision 3 puts one there) changes the answer; if no landed record says where a prefix comes from, say so and do not decide it.
   - **(d) Errors with no `parameter`.** A `TypeError`, `ValueError` or `OverflowError` from `subprocess` or the wait, one from binding the call, and the `OSError` for "a `cwd` that does not exist" (S3 against S10) stay as ADR-0060 decision 4 leaves them; reading them into a row is out of scope. Say how `ProgramNotFoundError` (S10 by ADR-0060 decision 4) and the own pre-call `TypeError`/`ValueError` of `run_verification` for `executable` relate to this record, from what they state, with no new rule.
   - **(e) No log, and the message.** No process was started. Say whether any log is involved (ADR-0078 decision 2) and what an S4 message may name under ADR-0060 decision 5, with no new rule.
   - **(f) No data-plane change.** Add no new value of `error.kind` or `condition`, no new member, no reserved kind, and no change to `schema_version` or the layout version (CLAUDE.md A-13 data-plane rule). `parameter` is a Python attribute of an in-process exception, not a data-plane member; the record says so. If only a new value would place a case, leave it open, say so, and name in Follow-ups that placing it needs an owner HQ. Do not decide it.
   - **(g) "How far (ma) is answered".** End the decisions with this, as ADR-0087 decision 8 does. List what this record answers and every entry of (ma) that stays open, taken from ADR-0087 decision 8 by reading it, minus what this record answers.
   - **Walk-through and Alternatives tables.** A walk-through table with at least one line per value of `parameter` and class, and at least one line each for an `env` error from `subprocess`, a missing `cwd`, and `ProgramNotFoundError`. An Alternatives table covering at least: S4 for `"timeout_s"` and no row for `"command"` (chosen or not); leaving all open; S4 for every error with a `parameter`; S10 for `"command"`; a new kind for a malformed command (declined as a data-plane change); the operation's own step instead of `parameter`.
4. **No sentence of an earlier ADR is edited.**
   - Consequences lists the sentences that become less exact. Look at least at ADR-0060 decision 4 (line 102) and Consequences (line 157), and ADR-0087 decision 8 and Boundaries. Find each one by reading, not from this list alone.
   - Consequences states what a later code task of the `cpu_standin` operation applies, and that this record binds no code and needs no change of `local_run.run` or `run_verification`.
   - Consequences states the "Runtime acceptance items". None are expected: no `claude`, compiler, verification executable or container is started or required.
5. **Register, proposals and coverage edits follow the recording rules written in those files**, read as they stand: the Requirements "행 형식" paragraph (line 84), the OpenDecisionProposals header's "기록 규칙" (line 8), and the first paragraph of StandardScenarios `# 검사 결과` (line 170). Do not take the wording of earlier task files or the shape of earlier edits as the model.
   - In each of the three, add one link for ADR-0088 where the rule says links go. Rewrite the open parts in place where they change (the `**잔여**:` of row OD-18 if it changes; the "부분 답 … 남음 …" end of sub-question 18). Do not restate the record and add no dated paragraphs. OD-18 keeps its status word.
   - Recheck coverage by StandardScenarios' rules for every scenario row that cites OD-18, and update `# 검사 결과` as its first paragraph says.
6. **Document mode** (CLAUDE.md A-13):
   - branch `claude/T-0264-<slug>`;
   - the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds;
   - rebase on `origin/main`, then a direct push to `main`;
   - commit trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0264`;
   - delete the branch.

   After landing, post the §9 notice on issue #5 in English, ending with the line `— posted by driver` (DRIVER §8), unless the driver's spawn prompt says the driver posts it; in that case put the exact notice text in `## Result`. Record its URL in `## Result` when posted.
7. **Size:** one new file and three edited files, at most 300 changed lines in total.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or the settings files.
- Any change to ADR-0001 to ADR-0087 or to `ARCHITECTURE/UsageCases.md`.
- Rows for what `run` passes on from `subprocess` (an `env` against an argument, a missing `cwd` S3 against S10, the `OverflowError`) and the other entries of (ma), except to restate them as still open.
- `clang_build.build` and `compiler_version`; the timing runs of `sim.run` / `board.run` (sub-question 19).
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18, and sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any new data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).
- Starting `claude`, a compiler, a verification executable or a container, or running code to establish facts.

## Follow-ups

- (code, later) Split the errors `run` passes on from `subprocess`: an `env` error against an argument error (S4 against no row), and the `OSError` for a missing `cwd` (S3) against other start errors (S10) (T-0263 Follow-ups). The design is that task's.
- (code, later) The `cpu_standin` operation of `correctness.check` applies ADR-0079 to ADR-0088 when it is written. HQ-0026 and PLAN P1-1 govern that.
- (possible HQ) If ADR-0088 leaves a case open because only a new `error.kind` would place it, the driver records that question for the owner.

## Result

- **BLOCKED (review rounds exceeded, CLAUDE.md A-13).** Not landed; nothing pushed to `main`; no §9 notice posted on #5.
- Branch `claude/T-0264-adr-od18-local-run-parameter` (kept, pushed), head `f2f8318`, 4 files, +135/-3: new `ARCHITECTURE/decisions/ADR-0088-od18-correctness-check-local-run-parameter.md`; OD-18 register row link (`**잔여**` unchanged); OpenDecisionProposals adopted line and the "부분 답 … 남음 …" end of sub-question 18 rewritten; StandardScenarios "최근 재검사" updated (S0, S1-b, S2, S5, S6 rechecked; no verdict change, no gap).
- ADR-0088 decides: a `TypeError`/`ValueError` of `local_run.run` with `parameter` `"timeout_s"` is S4 `settings_refused`; with `"command"` it is no row (`operation_answer_invalid` by the landed rules); errors with no `parameter`, the missing-`cwd` `OSError` and the pre-start lookup `OSError` stay open under (마). No data-plane change; no earlier ADR edited; no runtime acceptance item.
- Session entry check (2026-10-17): no open PR; ADR-0088 was free; no owner comment on #5 without the driver tail since 2026-10-15.
- Review: 7 rounds. R1 Approve (4 low/nit, fixed), R2 Approve (3 nits, fixed), R3 Request changes (a misquoted ADR-0060 phrase, fixed), R4 Approve (3 nits, fixed), R5 Approve (2 nits, fixed), R6 Approve (2 nits; the pre-start lookup `OSError` added to Boundaries), R7 Request changes (minor: that `OSError` must also be listed open in decision 8 and in the sub-question 18 "남음"; nit: L3 "only" → "chiefly"). The R7 fix is committed on the branch as `f2f8318` but has not been reviewed, because an 8th round is not allowed.
- Question for the owner: "T-0264 (ADR-0088, OD-18 sub-question 18 (ma)) stopped after 7 review rounds. Round 7 asked for one change: list the pre-start `OSError` of `local_run.run`'s program lookup as still open in decision 8 and in the OpenDecisionProposals 'remaining' list. That change is on branch `claude/T-0264-adr-od18-local-run-parameter` (`f2f8318`) but was not reviewed. Do you allow (a) one more reviewer round and landing on Approve, (b) landing the branch as it is, or (c) dropping the branch and re-planning?"
- Follow-ups: as in the task file; plus (code, later) the pre-start lookup `OSError` of `local_run.run` (`os.getcwd` inside `os.path.abspath`) needs a way to be told apart if it is to get a row.
- No `claude` was started (D16).

Closed without a result by the driver under HQ-0080 (1)(3) (owner, 2026-10-30). Nothing landed.
