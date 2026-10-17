---
id: T-0275
title: Write ADR-0090 on which row of `correctness.check` a pre-start `ValueError` of `clang_build.build` that now carries `parameter` "timeout_s", "flags", "trailing_flags" or "compiler" (T-0274) lets an operation place, and what stays unnamed (more of OD-18 sub-question 18 part (ma)); no `local_run.run`, no code
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18, "#5 D6"]
dependsOn: [T-0273, T-0274]
touchesFiles: [ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 160, files: 4}
hq: []
---
## Why

ADR-0089 (T-0273, landed `a4a8e7f`) left every pre-start `ValueError` of `clang_build.build` with no `parameter` open. Its reason (decision 5): an operation that sees only the class cannot tell a refused setting (V2-V7 of its P3: the two `timeout_s` refusals, the empty compiler prefix, a flag that sets the output, a NUL in a flag or compiler part, and on POSIX the `UnicodeEncodeError` of `os.fsencode`) from `build_verification_executable`'s own `ValueError` for no kernel source or from a `ValueError` that `build` passes on from `subprocess`. It named the way out as a follow-up: give V2-V7 a `parameter`, "a later record then places them".

T-0274 (PR #174, squash-merged as `ecc319f`) made that code change. `build` now tags every `TypeError` or `ValueError` from the checks of `timeout_s`, `flags`, `trailing_flags` and `compiler` with `parameter` set to that name. That includes a `ValueError` Python or a handed object's code raises inside the check. A `ValueError` from the checks of `sources` and `output` (such as no source) and one from anywhere else (binding the call, creating the process) still carry none. `compiler_version` raises the same errors with no `parameter`. No record has placed the newly named errors in a row. This task writes that record.

`local_run.run` is out of scope. ADR-0088, on `local_run.run` only, is held by the unlanded branch `claude/T-0264-adr-od18-local-run-parameter` and waits on HQ-0027. The `clang_build` side does not depend on that answer, as T-0273 already established. Because 0088 is held, this record takes **ADR-0090**.

This is a design-level part of OD-18, not an owner-only item (DRIVER §9). It closes by an ADR under D6, with the §9 notice. It needs no real `claude`, compiler or container (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, `Task:` trailer, size cap), §8 (the driver tail of #5 comments) and §9 (who may close an OD; the 7-day notice).
- `CLAUDE.md`: the standing rules. In particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", and the branch and merge procedure (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`, whole. This record continues it. Read in particular P1 and P3 of its Context, decisions 1, 2, 5, 6 and 9, and its Consequences. Follow its structure, but do not copy its sentences.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`: decisions 1 to 5 and 8 (lines 28-69), above all decision 3 (a named setting is S4, read for one Python raises inside the check).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 3 (lines 46-68, which side holds each setting), decision 4 (lines 69-104, the S4 row and "a `ValueError` or `TypeError` for a setting … → S4"), decision 5 (lines 105-109, messages) and Consequences (lines 154-161).
- Read `ADR-0045-…` decisions 4 and 5, `ADR-0078-…` decision 2 and `ADR-0083-…` decision 2 only where you cite them.
- `hilclaw/clang_build.py` at `ecc319f`. Read the docstring and checks of `build` (lines 196-322, especially the `parameter` paragraph at lines 250-262 and the `_parameter` calls at lines 297-322). Also read `compiler_version` (around line 406), `_parameter` (line 465), `_check_timeout`, `_checked_flags`, `_check_argument`, `_checked_sources` and `_resolve` (lines 504-570). In `hilclaw/harness/verification_build.py`, read `build_verification_executable` (lines 41-90). Read them as files and do not run them.
- `PROCESS/tasks/T-0274-clang-build-setting-value-errors-parameter.md`: `## Result` and `## Follow-ups` only.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8) and section `## OD-18` (lines 250-317), with its adopted-record lines (up to line 300) and sub-question 18 (line 313).
- `ARCHITECTURE/StandardScenarios.md`: the check rules near the top and `# 검사 결과` (from line 168), with its first paragraph (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md), before any edit:
   - Run `gh pr list`, then read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0090` is free on `main` and on every remote branch. Only `claude/T-0264-*` should hold 0088. If 0090 is taken, use the next free number and say so in `## Result`.
   - Look on #5 for an owner comment (one without the driver tail) on ADR-0089, ADR-0087, ADR-0060 decision 4, T-0274 or (ma). If there is one, cite it and follow it. Check whether HQ-0027 has been answered; if it has and the answer bears on this record, say how in `## Result`. Do not land T-0264's branch.
2. **New file** `ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md`, in the ADR-0001 record format.
   - Status: accepted under DRIVER §9 (D6). It says which sentences are the owner's, which are cited, and which are the record's own design.
   - Statements about code are observations at `ecc319f`. They bind no code, and nothing is established by running code.
3. **What the record weighs and answers** for `correctness.check` of the first case and of the mock. Each answer is the record's own design under §9 and states its reason and its cost. Leaving a case open with a reason is an acceptable answer.
   - **(a) A named `ValueError` with `parameter` `"timeout_s"`, `"flags"`, `"trailing_flags"` or `"compiler"`.** Weigh S4 `settings_refused` against ADR-0060 decisions 3 and 4 and against ADR-0087 decision 3, which placed the `TypeError` of the same four names. Cover each of V2-V7 of ADR-0089 P3 and the subclass `UnicodeEncodeError`. Also cover a `ValueError` that Python or a handed object's code raises inside one of these checks; T-0274 now tags it. Say what that reading costs.
   - **(b) What stays unnamed.** List from the code at `ecc319f` every pre-start `ValueError` of `build` and of `build_verification_executable` that still carries no `parameter`. Say which of them can reach the operation through `build_verification_executable`. Weigh whether an unnamed `ValueError` met through that function can now be placed. The operation knows it handed a non-empty compiled set, so it can rule out the function's own no-kernel-source error by its own step. The remaining sources are the `sources`/`output` checks and what `build` passes on from `subprocess`. If it cannot be placed, leave it open with the reason. A further code change may be named as a follow-up, not decided.
   - **(c) `compiler_version`.** It raises the same errors with no `parameter`. Keep it a Boundary unless the record finds that an operation of a check calls it.
   - **(d) No log and the message.** No compiler was started, so no log is handed to the keeper (ADR-0078 decision 2). Say what the `settings_refused` message may name under ADR-0060 decision 5, with no new rule.
   - **(e) No data-plane change.** Add no value of `error.kind` or `condition`, no member, no reserved kind, and no change to `schema_version` or the layout version (CLAUDE.md A-13). `parameter` is an attribute of an in-process exception. If only a new value would place a case, leave it open, say so in the record, and name in this task's `## Result` Follow-ups that it needs an owner HQ. Do not decide it.
   - **(f) How far (ma) is answered.** End the decisions with this. List what this record answers and which entries of ADR-0089 decisions 5, 6 and 9 it narrows or answers. List every entry of (ma) that stays open, read from ADR-0089 decision 9 as it stands on `main`. Keep the `local_run.run` entries listed as open, because ADR-0088 is unlanded.
   - **Walk-through and Alternatives tables.** The walk-through has one line per named case of (a) and at least one line for a case left open. The Alternatives cover at least:
     - the chosen answers;
     - leaving the named `ValueError`s open;
     - S4 only for the `ValueError` the check itself raises, with no row or open for one raised inside a handed object's code;
     - a new kind, declined as a data-plane change.
4. **No sentence of an earlier ADR is edited.** Consequences lists the sentences that become less exact. Find them by reading ADR-0060, ADR-0087 and ADR-0089, not by relying on this list alone. At least check:
   - ADR-0089 Context P3 ("carry no `parameter`"), decision 5, decision 6, decision 9, the walk-through rows for V3, V6 and V7, Consequences and Boundaries;
   - ADR-0087 decision 2's sentence on a `ValueError` of the same checks;
   - ADR-0060 decision 4 and its Consequences, where ADR-0089 already noted they were less exact.

   Consequences also states three things: what a later code task of the `cpu_standin` operation applies; that the record binds no code; and "Runtime acceptance items: none".
5. **Register, proposals and coverage edits** follow the recording rules written in those files, read as they stand. These are the Requirements register's "행 형식" (line 84), the OpenDecisionProposals header's "기록 규칙" (line 8), and the first paragraph of StandardScenarios `# 검사 결과` (line 170). Do not take the wording of earlier task files or the shape of earlier edits as the model.
   - Add one link for the new ADR to the OD-18 row's `**확정분**:`, and one adopted-record line in OpenDecisionProposals `## OD-18`.
   - Rewrite the open parts in place: the row's `**잔여**:` only if its text changes, and the status at the end of sub-question 18. Do not restate the record, and add no dated paragraph. OD-18 keeps its status word.
   - Re-check coverage by StandardScenarios' rules for every scenario row that cites OD-18. Update `# 검사 결과` as its first paragraph says.
6. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0275-<slug>`.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push directly to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0275`.
   - Delete the branch.
   - After landing, post the §9 notice on issue #5 in English, ending with the driver tail of DRIVER §8, and record its URL in `## Result`. If the driver's spawn prompt says the driver posts it, write the notice text in `## Result` instead.
7. **Size**: one new file and three edited files, at most 300 changed lines in total.
8. **Result** records:
   - the landed commit, and the review rounds with their findings;
   - the §9 notice URL or its text;
   - the session entry check;
   - the overlap with the unlanded branches `claude/T-0264-*`, `claude/T-0210-*` and `claude/T-0231-*`. They edit the same register row, the sub-question 18 line and the "최근 재검사" line, and must rebase over this edit. When ADR-0088 lands, its text must keep the entries of ADR-0089 and of this record;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- `local_run.run` and every entry that waits for ADR-0088 and HQ-0027. The branch `claude/T-0264-*` is not touched or landed.
- `hilclaw/harness/timing_build.py` and the timing build of `sim.run` / `board.run` (sub-question 19; T-0210, HQ-0021).
- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or any settings file. Any change to ADR-0001 to ADR-0089 or to `ARCHITECTURE/UsageCases.md`.
- The other open entries of (ma), except to restate them as open: the unroled `OSError` of `build`, the `CompilerRunError` with `timed_out` false and `returncode` `None`, an unnamed `TypeError`, and what `build` still passes on from `subprocess`.
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18; sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).

## Follow-ups

- (doc, optional) Two non-blocking Nits of review round 7, left because a further round would exceed the 7-round cap: (1) in `ARCHITECTURE/OpenDecisionProposals.md` sub-question 18 "남음", the entry "`clang_build.build`(`sources`·`output` 검사와 그 뒤)" could read "(`sources`·`output` 검사, 그리고 모든 검사 뒤 시작까지)" so that it cannot be read as including the now-named `compiler`/`env`/`cwd` checks; (2) ADR-0090 Consequences could also list ADR-0060 decision 7's "except for an error that one call raises in one class for two rows" (under (가) and sub-question 10) as now less exact (ADR-0089 omitted it too). Either goes into the next OD-18 (ma) record's edits rather than a task of its own.
- (code, candidate, not required) Give a `parameter` to a `ValueError` of the `sources` and `output` checks of `clang_build.build` and of the tuple of `kernel_sources` in `build_verification_executable` (ADR-0090 decision 3), then a doc record places them.
- (code, after HQ-0027) The `local_run.run` analogue, unchanged from T-0274.

## Result

- **Landed** as `61504e8` on `main` (document mode, pushed directly; trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0275`). Branch `claude/T-0275-adr-od18-clang-build-named-setting-value-errors` deleted on origin and locally. Files: new `ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md`; `ARCHITECTURE/Requirements.md` (OD-18 `**확정분**:` link; `**잔여**:` unchanged, its text does not change); `ARCHITECTURE/OpenDecisionProposals.md` (adopted-record line; sub-question 18 status rewritten in place); `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line: S0, S1-b, S2, S5, S6 re-checked, no verdict change, no gap). 4 files, +119/-3.
- **Decisions**: named `ValueError` with `parameter` `timeout_s`/`flags`/`trailing_flags`/`compiler` -> S4 `settings_refused`, one raised inside a handed object's code included, no log, message names the setting only; unnamed pre-start `ValueError` (U1-U6 listed from the code at `ecc319f`) stays open, narrowed (U5 ruled out by the operation's own step; U4 = what `subprocess` passes on, not read); `compiler_version` stays a Boundary; no data-plane change, no owner HQ needed.
- **Review**: 7 rounds (context-isolated `dev-reviewer`, opus). R1 Approve with 2 Minor + 2 Nit (ADR-0087 T1/T2 missing from less-exact list; `env` with no `items` presented as a `subprocess` `ValueError`; U3 scope; Status P5) - fixed. R2 Request changes: Minor (U1 would also be named after a further tag) + 3 Nit (traceback vs chain, References, adopted-record line format) - fixed. R3 Approve with 2 Nit (path-test `ValueError` unread; U5 wording) - fixed. R4 Request changes: Medium (alternative (c) said "exception chain", which does not tell the cases apart) + Low (U5 wording in decision 3) - fixed. R5 Approve with 1 Low (V7 and handed-code messages also show values) - fixed. R6 Approve with 1 Low (ADR-0089 Alternatives (a) cost sentence missing from less-exact list) - fixed. R7 Approve with 2 Nit, not applied (Follow-ups) to stay within the cap.
- **§9 notice**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6237037614 (English, ends with `— posted by driver`).
- **Session entry check** (2026-10-18, before any edit): `gh pr list` empty; issues #4, #7 (no activity since 2026-09), #8 (closed) and #5 read. `ADR-0090` free on `main` and every remote branch; only `origin/claude/T-0264-adr-od18-local-run-parameter` holds 0088. No owner comment (without the driver tail) on ADR-0089, ADR-0087, ADR-0060 decision 4, T-0274 or (ma); the last non-driver comment on #5 is of 2026-10-15. HQ-0027 unanswered. T-0264's branch not touched.
- **Resume check**: `git log origin/main --grep='^Task: T-0275'` was empty at start; fresh start.
- **Overlap with unlanded branches** `claude/T-0264-*`, `claude/T-0210-*`, `claude/T-0231-*`: they edit the same OD-18 register row, the sub-question 18 status line and the StandardScenarios "최근 재검사" line, and must rebase over `61504e8`. When ADR-0088 lands, its edits must keep the ADR-0089 and ADR-0090 entries (확정분 link, adopted-record line, the (ma) partial-answer list and the narrowed unnamed-`ValueError` entry of "남음").
- No `claude` program, compiler, Python run of the sources or container was started (D16); code was read as files.
