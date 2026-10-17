---
id: T-0262
title: Write ADR-0087 on which rows of `correctness.check` the `parameter` of a `TypeError` of `clang_build.build` (T-0261) lets an operation place (more of OD-18 sub-question 18 part (ma))
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0261]
touchesFiles: [ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0060 decision 4 (the bullet "What the functions on `main` report, against the rows", line 102) gives a `TypeError` two answers, by what it is about:

- a `TypeError` "for a setting — a time limit, a flag, the compiler" → S4 `settings_refused`, "whether the setting is refused for its value or for its type";
- a `TypeError` "for an argument that is no setting (a path, an argument of the command)" → "a defect of the operation's own code and is no row"; an operation that lets it pass is answered `operation_answer_invalid` (cited there: ADR-0045 decisions 4 and 5).

It then says "a `TypeError` of `clang_build.build`, whose docstring does not say which argument, is an error of two rows (Consequences)". ADR-0060 Consequences (line 157) makes telling them apart "a condition of the operation's code", for example "by a change of those functions". ADR-0086 decision 8 still lists "the `TypeError` of `clang_build.build`" as open under part (ma) of sub-question 18 of OD-18.

T-0261 (PR #164, `a46a4d6`) made that change and placed no row. Every `TypeError` that leaves one of the checks `build` makes before the start now carries `parameter`, one of `"timeout_s"`, `"flags"`, `"trailing_flags"`, `"sources"`, `"output"`, `"compiler"`. This includes a `TypeError` Python raises inside such a check (from `tuple`, iteration or `os.path.abspath`), re-raised as the same object. No other error carries it: not a `TypeError` from binding the call, not one from `subprocess.Popen` or later, not a `ValueError`, an `OSError` or one of the module's error classes, and not any error of `compiler_version`. See the `build` docstring (lines 220-235) and T-0261 Result.

This task writes the record that weighs what `parameter` makes true. It is a design-level ADR under DRIVER §9. OD-18 is not owner-only under §9, so the ADR is in scope.

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025), T-0243 (HQ-0026). The runtime-acceptance HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019) do not bear on this record. None of the blocked tasks touches the four files, and this task depends on none of those HQs. HQ-0026 (the code of the `cpu_standin` operation of `correctness.check`) is not needed: this record binds no code. PLAN P1-1 continues through the OD-18 (ma) work. It is the doc follow-up named in T-0261 Follow-ups.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, 2h30 time limit;
  - §5 (lines 86-114): task format, branch `claude/T-0262-<slug>`, trailer `Task: T-0262`, size cap;
  - §8 (lines 135-139): the driver tail on #5 comments;
  - §9 (lines 141-148): OD closing authority, the 7-day notice.
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode, `Reviewed-by` trailer), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`:
  - decision 3 (the table of settings before line 69: which settings are "the backend's own" and which the operation's own);
  - decision 4 (lines 69-104), above all the S4 row of the situation table and the bullet at line 102 with its sentences on `TypeError`, "An operation places such an error by the step of its own …", and "An error the operation lets pass that is no tool failure …";
  - decision 5 (line 105 onward), on what a message of S4 may say ("for S4 which setting");
  - Consequences (from line 154), the bullet "Telling the rows apart is a condition of the operation's code" (line 157).
- `ARCHITECTURE/decisions/ADR-0086-od18-correctness-check-path-role.md`: whole file, as the latest model of an ADR of this series (Status, the decisions, decision 8, Walk-through, Alternatives, Consequences).
- `ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md`: Context P3 (line 29, "`_check_timeout` and `_checked_flags` raise `TypeError` or `ValueError` only"), decision 1 (the bullet "Another `Exception`", line 43), decision 4.
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decisions 3 and 4 (who forms the paths), decision 5 (lines 95-114, the situation list).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 and 5 (lines 64-84), `operation_answer_invalid`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (line 146).
- `hilclaw/clang_build.py` at `a46a4d6`, read only, do not edit: the `build` docstring (lines 195-240), the wrappers at lines 271-292, `_parameter` (line 434), `_check_timeout`, `_checked_flags`, `_checked_sources`, `_resolve` (lines 442-510).
- `PROCESS/tasks/T-0261-clang-build-type-error-parameter.md`: "The change, stated", Result, Follow-ups.
- The recording rules, read and followed as written:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet of the header (line 8), and section `## OD-18` (from line 250), including the 채택분 lines up to line 298 and the sub-question 18 bullet (line 311);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of `# 검사 결과` (line 170), the "최근 재검사" line (line 172), and the verdict rows whose notes cite OD-18.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md). Before editing:
   - Run `gh pr list` and read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0087` is still the next free number under `ARCHITECTURE/decisions/`.
   - Check #5 for an owner comment (one without the driver tail) that speaks to ADR-0060 decision 4, ADR-0086, T-0261 or (ma). If there is one, cite it and follow it.
2. **New file** `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`, in the ADR-0001 record format.
   - Status is "Accepted under DRIVER §9 (D6)". It says which sentences are the owner's, which are cited, and which are this record's own design.
   - Statements about code are observations at `a46a4d6` and bind no code. Nothing is established by running code.
3. **What the record must weigh and answer.** The answers are the record's own design, reviewed under §9. Each choice states its reason and its cost.
   - **(a) Telling the cases apart.** Can the operation now tell, from what `build` states alone (`isinstance(error, TypeError)` and `getattr(error, "parameter", None)`), a `TypeError` for a setting from one for an argument it forms, and both from a `TypeError` with no `parameter`? On which reading of ADR-0060 decision 4's "What the operation observes decides the row"? Say what "an error of two rows" still holds for and what it no longer holds for.
   - **(b) Settings.** Weigh S4 `settings_refused` for `"timeout_s"`, `"flags"`, `"trailing_flags"` and `"compiler"`, against ADR-0060 decision 3's table of settings and the S4 row's wording ("a setting of the wrong type"). Say whether a `TypeError` Python raises inside such a check (for example `tuple(3)` for `flags`) is covered by the same wording.
   - **(c) Arguments the operation forms.** Weigh no row (`operation_answer_invalid`, as the landed rules answer it) for `"sources"` and `"output"`, which ADR-0056 has the operation form. Say whether this record changes what ADR-0060 decision 4 says for them or only applies it.
   - **(d) No `parameter`.** A `TypeError` from `build` with no `parameter` (from `subprocess.Popen` or later, or from binding the call) stays as ADR-0060 decision 4 and ADR-0083 decision 1 leave it: the entry "whatever `clang_build.build` passes on from `subprocess`" remains open. Reading it into a row is out of scope.
   - **(e) No log, and the message.** No compiler was started, so there is no log (ADR-0078 decision 2). Say what an S4 message may name under ADR-0060 decision 5 (which setting), with no new rule.
   - **(f) No data-plane change.** Add no new value of `error.kind` or `condition`, no new member, no reserved kind, and no change to `schema_version` or the layout version (CLAUDE.md A-13 data-plane rule). `parameter` is a Python attribute of an in-process exception, not a data-plane member; the record says so. If only a new value would place a case, leave it open, say so, and name in Follow-ups that placing it needs an owner HQ. Do not decide it.
   - **(g) "How far (ma) is answered".** End the decisions with this, as ADR-0086 decision 8 does. List what this record answers and every entry of (ma) that stays open: the unroled `OSError` of `build` (ADR-0086 decision 6); the `CompilerRunError` with `timed_out` false and `returncode` `None`; what `build` passes on from `subprocess`; the `local_run.run` entries.
   - **Walk-through and Alternatives tables.** A walk-through table with one line per value of `parameter` and at least one line for a `TypeError` with no `parameter`. An Alternatives table covering at least: S4 for settings and no row for formed arguments (chosen or not); leaving all open; S4 for every `TypeError` with a `parameter`; a new kind for a formed argument of the wrong type (declined as a data-plane change); the operation's own step instead of `parameter`.
4. **No sentence of an earlier ADR is edited.**
   - Consequences lists the sentences that become less exact. Look at least at ADR-0060 decision 4 (line 102, "a `TypeError` of `clang_build.build`, whose docstring does not say which argument, is an error of two rows") and Consequences (line 157), ADR-0083 decision 1 (line 43) and decision 4, and ADR-0086 decision 8. Find each one by reading, not from this list alone.
   - Consequences states what a later code task of the `cpu_standin` operation applies, and that this record binds no code and needs no change of `clang_build.build`.
   - Consequences states the "Runtime acceptance items". None are expected: no `claude`, compiler or container is started or required.
5. **Register, proposals and coverage edits follow the recording rules written in those files**, read as they stand: the Requirements "행 형식" paragraph (line 84), the OpenDecisionProposals header's "기록 규칙" (line 8), and the first paragraph of StandardScenarios `# 검사 결과` (line 170). Do not take the wording of earlier task files or the shape of earlier edits as the model.
   - In each of the three, add one link for ADR-0087. Rewrite the open parts in place (the `**잔여**:` of row OD-18; the "→ 부분 답: … 남음: …" end of sub-question 18). Do not restate the record and add no dated paragraphs. OD-18 keeps its status word.
   - Recheck coverage by StandardScenarios' rules for every scenario row that cites OD-18, and update `# 검사 결과` as its first paragraph says.
6. **Document mode** (CLAUDE.md A-13):
   - branch `claude/T-0262-<slug>`;
   - the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds;
   - rebase on `origin/main`, then a direct push to `main`;
   - commit trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0262`;
   - delete the branch.

   After landing, post the §9 notice on issue #5 in English, ending with the line `— posted by driver` (DRIVER §8). Record its URL in `## Result`.
7. **Size:** one new file and three edited files, at most 300 changed lines in total.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or the settings files.
- Any change to ADR-0001 to ADR-0086 or to `ARCHITECTURE/UsageCases.md`.
- `ValueError`: ADR-0060 decision 4 already places it by what it is for.
- Rows for the other entries of (ma), except to restate them as still open (listed in AC 3 (g)).
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18, and sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any new data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).
- Starting `claude`, a compiler or a container, or running code to establish facts.

## Follow-ups

- (code, later) The same kind of split for `local_run.run`: its `ValueError` or `TypeError` for an `env` against one for an argument, and its `OSError` for a missing `cwd` (S3) against other start errors (S10) (T-0261 Follow-ups).
- (code, later) The `cpu_standin` operation of `correctness.check` applies ADR-0079 to ADR-0087 when it is written. HQ-0026 and PLAN P1-1 govern that.
- (possible HQ) If ADR-0087 leaves a case open because only a new `error.kind` would place it, the driver records that question for the owner.

## Result

- **Outcome:** DONE. Document mode. Landed on `main` as `31b0654` (one squashed commit, fast-forward push, trailers `Reviewed-by: reviewer agent (6 rounds, Approve)` and `Task: T-0262`). The branch `claude/T-0262-adr-od18-type-error-parameter` was deleted on the remote and locally; the clone is on `main` = `origin/main`.
- **Entry check:** `gh pr list` showed no open PR. `ADR-0087` was the next free number. Issues #4, #7 and #8 have nothing newer that bears on this. #5 has no owner comment (without the driver tail) on ADR-0060 decision 4, ADR-0086, T-0261 or (ma).
- **Files:** 4 files, +132/-3 lines.
  - New: `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`.
  - Edited: `ARCHITECTURE/Requirements.md` (one link added to `**확정분**:` of row OD-18; `**잔여**:` "(마)의 나머지" still holds and was left as is).
  - Edited: `ARCHITECTURE/OpenDecisionProposals.md` (one `채택분` line; sub-question 18's "부분 답 … 남음 …" rewritten in place).
  - Edited: `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line).
- **What the record decides (its own design, under DRIVER §9):**
  - The operation tells a `TypeError` of `build` apart by `getattr(error, "parameter", None)`, reading "what the operation observes" as the class and documented members, as ADR-0085 and ADR-0086 do.
  - `"timeout_s"`, `"flags"`, `"trailing_flags"`, `"compiler"`: S4 `settings_refused`, including a `TypeError` Python raises inside the check. No log.
  - `"sources"`, `"output"`: no row. This applies ADR-0060 decision 4 without changing it; the landed rules answer `operation_answer_invalid`.
  - A `TypeError` with no `parameter` (binding the call, `subprocess.Popen` or later, or `build_verification_executable`'s own for `kernel_sources`) stays open.
  - No data-plane change.
- **Coverage recheck:** the rows that cite OD-18 (S0, S1-b, S2, S5, S6) were rechecked. None cites sub-question 18, and OD-18 stays open. No verdict changed and there is no gap.
- **Review:** 6 rounds with `dev-reviewer` (opus, fresh context each round). Every round was Approve; the rounds continued only to fix Minor and Nit findings.
  - Round 1: the owner-sentence account in Status (O1 to O5, the O4 basis of the settings table), the order note, and one ambiguous "Either".
  - Round 2: the `bytes` wording in T5, a T1 citation, and the Status builds-on list.
  - Round 3: the `bytes` wording in T5 again.
  - Round 4: the scope of the open unnamed `TypeError` in decision 8 and in Proposals, and the source of T2.
  - Round 5: the ADR-0045 citation (decisions 4 and 5), and the open-list wording in Proposals.
  - Round 6: one optional Nit, not applied. It suggested listing ADR-0060's "a `TypeError` of the build for an argument of the wrong type" as now less exact; the reviewer itself read "argument" there as a non-setting argument and said no change was needed.
- **A discrepancy in the task file:** AC 3 (d) and Required Reading cite ADR-0083 "decision 1" for the "Another `Exception`" bullet (line 43). That bullet is in decision 2. The ADR cites decision 2.
- **Runtime acceptance items:** none.
- **New HQ:** none. No case was left open for want of a new `error.kind`.
- **§9 notice:** needed. The ADR closes part of OD-18 (a design-level OD). Following the driver's instruction, the executor did not post it, so the driver posted it after landing: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6231613019. Text posted on #5:

```
### OD-18 - correctness.check after T-0261: the TypeError of clang_build.build placed by parameter in ADR-0087 under DRIVER §9 (T-0262)

**Record:** [ADR-0087](https://github.com/myungjoo/HIL-Claw/blob/main/ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md) covers what a check of `correctness.check` answers for a `TypeError` of `clang_build.build`. Since T-0261 (`a46a4d6`), every `TypeError` from the checks `build` makes before the start carries `parameter`: one of `"timeout_s"`, `"flags"`, `"trailing_flags"`, `"sources"`, `"output"`, `"compiler"`. No other error of `build` carries it. The record covers more of part (마) of sub-question ⑱ of OD-18. A context-isolated reviewer approved it under DRIVER §9 after 6 rounds. You have not confirmed it.

**Answered, for `correctness.check` of the first case and of the mock:**
- **Told apart by `parameter`:** the operation reads the class and the documented member, as ADR-0085 read `returncode` and ADR-0086 read `path_role`. "An error of two rows" (ADR-0060 decision 4) no longer holds for a `TypeError` that carries `parameter`.
- **`"timeout_s"`, `"flags"`, `"trailing_flags"`, `"compiler"`:** S4, `settings_refused`. These are the backend's own settings (ADR-0060 decision 3). This includes a `TypeError` Python raises inside the check (for example `tuple(3)` for `flags`). Cost stated: a fault in the code of a handed setting object is read as a refused setting.
- **`"sources"`, `"output"`:** no row. The operation forms these arguments. This applies ADR-0060 decision 4 without changing it; the landed rules answer `operation_answer_invalid`. Cost stated: a wrong path type handed by the tool function is answered the same way.
- **No log:** no compiler ran (ADR-0078 decision 2). The S4 message may say which setting, but it does not show the error text or the value (ADR-0060 decision 5). No new rule.

**Left open:** a `TypeError` with no `parameter`. It can come from binding the call, from `subprocess.Popen` or later (an `env` or a `cwd` that cannot be handed over), or from `build_verification_executable` itself for `kernel_sources`. The class does not say which argument, and what `Popen` passes on was not read.

**Still open under (마):** what `build` passes on from `subprocess`; the `OSError` with no `path_role`; the `CompilerRunError` with `timed_out` false and `returncode` `None`; and the `local_run.run` entries.

The record adds or changes no member, `condition` value, `error.kind` value, `schema_version` or layout version. It edits no earlier record. There is no question for you.

**Landing commit:** https://github.com/myungjoo/HIL-Claw/commit/31b0654

**Objection window:** you may object within 7 days of this notice. An objection creates a task that reverts the record and its register edits.

— posted by driver
```

- **Follow-ups:** the same as the task's Follow-ups: the `local_run.run` split (code), and the `cpu_standin` operation applying ADR-0079 to ADR-0087 (HQ-0026, PLAN P1-1). The "possible HQ" follow-up is not needed.
