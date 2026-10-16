---
id: T-0245
title: Write an ADR that answers OD-18 sub-question 18 part (ma) for the errors of one `clang_build.build` call that the code now tells apart (start of the compiler, moving the artefact, removing the temporary file), for `correctness.check`
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-6, FR-10, OD-18]
dependsOn: [T-0244]
touchesFiles: [ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 190, files: 4}
hq: []
---
## Why

ADR-0060 decision 4 lists errors that one call of `clang_build.build` or `local_run.run` raises "in one class" for two rows of its table, and gives them no answer. Its Consequences say: "The code task that writes the operation makes them distinguishable ... or registers what it cannot tell apart; this record gives no kind to an error of two rows (⑱ (마))". Sub-question ⑱ (마) of OD-18 asks what a call answers for such an error, "until the code tells them apart".

T-0244 (PR #155, `7003362`) changed the code for one of those entries. `hilclaw.clang_build.build` now raises `ArtefactNotPlacedError` when moving the artefact into place fails, and `TemporaryNotRemovedError` when only removing its temporary file fails. Both carry the `BuildResult` (with the compiler's log) as `result`. An `OSError` from starting the compiler process is unchanged and is neither class. So the entry "an `OSError` from starting the compiler (S6) or from moving the artefact (S9) ... an `OSError` of `clang_build.build` from removing its temporary file ..., which comes up in the same class from the same call as S6 and S9" can now be placed by class. T-0244 left the mapping to a later record ("This task does not say which row or answer any of them maps to"). Its Follow-ups proposed only a note in the registers. Under the recording rules now written in Requirements.md ("행 형식") and OpenDecisionProposals.md ("기록 규칙"), the registers change only with an ADR. So the follow-up is done as a design-level ADR under DRIVER §9, not as a register note.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-17 at `aa91c3e`). PLAN P1-1 continues. The other open slices of ADR-0078 wait on HQ-0026 (T-0243), and the remaining P1-1 parts wait on HQ-0025. This record depends on neither. It uses no file of their branches and decides none of their questions. Unlanded ADR numbers: 0068 (branch of T-0210) and 0074 (branch of T-0231). 0079 is the next free number. Take the next free number at execution time if 0079 is taken by then, and rename the file and `touchesFiles` to match.

**What the record must settle (the executor weighs the alternatives; the reviewer checks them against ADR-0060 decision 4, ADR-0078 decision 2 and the code):**
1. **`ArtefactNotPlacedError`**: which row of ADR-0060 decision 4 it is. The S9 row reads "Status 0 and no executable at the path, or it cannot be moved there", answered `build_output_missing`. The record also says that the build's log is in `result.log` and so falls under ADR-0078 decision 2 ("S9" builds are kept). If the record also says how the operation hands that log over, it only cites ADR-0078 decision 6.
2. **`TemporaryNotRemovedError`**: what the call answers when only the removal of the temporary file failed. The build may have ended ok, not ok (S7, S8) or with status 0 and no artefact (S9). ADR-0060 decision 4 says what the landed rules do with "one from removing the temporary file" today (`operation_answer_invalid`, via ADR-0045 decisions 4 and 5), and that this is "no answer of this record". Candidates the record must weigh at least: (a) keep that landed answer; (b) answer by the row the carried `result` shows (ok, S7, S8, S9), treating the left-over temporary file like the rest of the build directory that ADR-0056 decision 4 has the operation remove; (c) the S9 row or another existing backend kind. The record also says what happens to the log in each case (ADR-0078 decision 2 keeps the log of every build whose compiler ended).
3. **An `OSError` from starting the compiler that is neither new class**: S6 (`compiler_unavailable`), except the case decision 4 names separately, "an `OSError` from starting the compiler for a missing working directory (S3)". The record either places that case as well, for example by a rule on the `cwd` the operation hands `build`, citing the module docstring ("the output are handed to it as absolute paths, so `cwd` does not change what ..."), or leaves it open under (마) by name.
4. **How far (마) is answered**: only this `clang_build.build` entry, for `correctness.check`. The other two-row entries of decision 4 stay open and are named: `FileNotFoundError` / `IsADirectoryError` for a source (S5) or for the output path (S3); the `ValueError` / `TypeError` of `local_run.run`; the `TypeError` of `clang_build.build`; anything else that `subprocess` passes on. So do the timing build of `sim.run` / `board.run` (⑲ (나); ADR-0068 is on an unlanded branch) and the isolated environment (⑱ (다)).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit) and §5 (lines 86-114: task format, naming `claude/T-0245-<slug>`, the trailer `Task: T-0245`, size cap), §8 (lines 135-139: the driver tail of #5 comments) and §9 (lines 141-148: the ADR route, the notice and the 7-day window).
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (whole procedure, document mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 4 (lines 69-104, especially the table rows S3 to S10 at lines 90-97 and the paragraph at line 102), decision 6 row ⑥ (line 117), decision 7 (lines 122-127), Consequences (line 157), Boundaries (line 174, part (마)).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: Status (lines 3-13), Context observations (line 22), decision 2 (lines 32-37), decision 6 (lines 64-80), decision 7 (lines 81-91), Consequences slice 4 (line 125), Boundaries (lines 131-143). It is the model of the record format and the Status wording, not of the register edits.
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` decisions 4 and 5 (lines 73-114: the build directory and the situations S1 to S10).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` decisions 4 and 5 (lines 64-84) and `ADR-0047-od18-correctness-check-operation-tool-failure.md` decision 5 (lines 89-97).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` "Record format" (line 146 to the end).
- `hilclaw/clang_build.py` lines 1-30 (module docstring), 58-206 (the error classes and `build`), as landed by T-0244. Facts about it go into the record as observations at a named commit.
- `PROCESS/tasks/T-0244-clang-build-keeps-log-on-file-errors.md` (Why and Result).
- `ARCHITECTURE/Requirements.md` paragraph "행 형식" (line 84) and row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md` header bullet "기록 규칙" (line 8), the OD-18 adopted-record bullets (around line 290) and the sub-question ⑱ bullet (line 303).
- `ARCHITECTURE/StandardScenarios.md` §검사 결과 (line 168 onward, first paragraph and the "최근 재검사" line).

## Acceptance Criteria

1. **Session entry check** done and stated in the Result: `gh pr list` and issues #4, #5, #7, #8 read before the first edit. Report any open PR touching row OD-18, the OD-18 section or the re-check line. If #5 carries an owner comment that speaks to errors of two rows, to S9 or to ⑱ (마), stop and report it.
2. **One new record** `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md` (number per Why), in the record format of ADR-0001, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here) and References. Status says that it was accepted under DRIVER §9 by the reviewer's approval and not confirmed by the owner, which part of ⑱ it answers and which it leaves open, that it changes no member, `condition` value, `schema_version` or layout version, and the owner's 7-day objection window. It separates owner sentences, cited sentences and its own design, as ADR-0078 Status does.
3. The record **settles points 1 to 4 of Why** for `correctness.check` of the first case and of the mock. Each choice is weighed against at least one alternative in "Alternatives considered". It states which landed sentences it leaves less exact, without editing them, at least ADR-0060 decision 4 and its Consequences, and ADR-0078 Consequences slice 4. Facts about `hilclaw/clang_build.py` are stated as observations at `7003362` or later, and the record binds no code (names and modules stay the code task's).
4. **Limits.** The record adds no value of `condition` (ADR-0060 decision 4: a result for S9 or S10 "would need a value of `condition` the owner has not approved"), no value of `error.kind` and no reserved kind, no member of any file, result, request or line, and no `schema_version` or layout version. It answers only with the six backend kinds of ADR-0060, `operation_answer_invalid`, or the outcome the carried `result` shows. If the executor finds that none of these fits without one of the additions above, stop and return BLOCKED (`requirement-unclear`) with the question.
5. **Not decided** (named in Boundaries where the answer touches them): the other two-row entries of ADR-0060 decision 4 (Why point 4); the timing build of `sim.run` / `board.run` (⑲ (나), ⑲ (다)); ⑱ (가), (다), (라) and the size bound of (나); ⑰ (다), including what happens when removing the build directory fails; the owner-only items of DRIVER §9.
6. **Register edits follow the recording rules written in those files.** Read them there and apply them as written. Do not copy the wording of earlier task files:
   - `ARCHITECTURE/Requirements.md` row OD-18: as the "행 형식" paragraph prescribes. Add one link to the new record to the row's 확정분 list, and rewrite the 잔여 part in place for ⑱ (마) (partly answered, the rest named briefly). No restatement of the record and no dated paragraph. The status cell is unchanged unless that paragraph requires otherwise.
   - `ARCHITECTURE/OpenDecisionProposals.md` OD-18 section: as the header's "기록 규칙" prescribes. Add one adopted-record bullet, and rewrite the ⑱ bullet's end status (`→ 부분 답: …. 남음: …`) in place. The bullet keeps its wording and head status word. No restatement of the record. The ⑩ and ⑰ bullets, which point to "⑱ (마)", are edited only if they now say something untrue.
   - No other `ARCHITECTURE/` file and no earlier ADR is edited.
7. **Coverage re-check** per CLAUDE.md "문서 커버리지 재검사" and the first paragraph of StandardScenarios §검사 결과: update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed. Change an S-row note only if it now says something untrue.
8. **D16**: no step starts `claude` in any form, builds anything or runs a compiler. Facts come from the code and the records.
9. **Document mode** per CLAUDE.md A-13: branch `claude/T-0245-<slug>`, reviewer cycle (dev-item-address steps 10-12) to Approve within the 7-round cap, rebase on `origin/main`, then direct push to `main` with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0245`.
10. **§9 notice** on #5 after landing: the record's number and title, the part of OD-18 ⑱ (마) it answers and what stays open, the landing commit link, the 7-day window, and the driver tail of DRIVER §8.
11. Size within DRIVER §5 caps (≤ 300 changed lines, ≤ 5 files).

## Out of Scope

- Any code, test or CI change, including `hilclaw/clang_build.py`, `hilclaw/check_operation.py`, `hilclaw/check_failure.py` and the operation of `cpu_standin`. The code that applies the record belongs to the task that writes that operation.
- ADR-0078 slices 1 to 3 (T-0243, BLOCKED on HQ-0026) and anything of HQ-0025.
- Edits to ADR-0060, ADR-0078 or any other accepted record, and to the branches of T-0210 and T-0231.
- The other errors of two rows, `local_run.run`, and the run tools' timing build.

## Follow-ups

- When the operation of `cpu_standin` for `correctness.check` is written (after ⑱ (라), OD-14 ① and ⑱ (다)), its code applies this record.
- The remaining entries of ⑱ (마), when code tells them apart or a record places them.

## Result

- **Outcome:** DONE. Document mode; landed on `main` as `994ca3d` (https://github.com/myungjoo/HIL-Claw/commit/994ca3d51c40cfe7cfff1b704062d8f5c07b86e8), one commit with `Reviewed-by: reviewer agent (5 rounds, Approve)` and `Task: T-0245`. Branch `claude/T-0245-adr-od18-build-errors-told-apart` deleted (remote and local).
- **Session entry check (before the first edit):** `gh pr list` showed no open PR; issues #4, #5, #7, #8 read. No owner comment on #5 speaks to errors of two rows, to S9 or to ⑱ (마) (the latest owner comments are the 2026-10-15 decisions and the HQ-0020 answer, both already quoted by ADR-0060). ADR-0079 was free on `main` and on every remote branch.
- **Change:** new `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`. `ArtefactNotPlacedError` → S9 `build_output_missing`. `TemporaryNotRemovedError` → the row of the carried build (candidate (b)), because the temporary file lies in the build directory that the operation removes. An `OSError` from starting the compiler, a missing cwd included → S6 `compiler_unavailable`, placed by moment, only where the operation can tell the error came from the start; telling it apart stays the code's. Open under (마) and named: same-class errors before the start or after the end, the path errors S5/S3, the `TypeError` of `clang_build.build`, other `subprocess` errors, and the `local_run.run` entries. Register edits: Requirements OD-18 row (one 확정분 link, 잔여 "(마)의 나머지"), OpenDecisionProposals (one 채택분 bullet, ⑱ end status rewritten), StandardScenarios "최근 재검사" line (S0, S1-b, S2, S5 and S6 re-checked; no verdict change, no gap). 4 files, +108/-3.
- **Review:** 5 rounds, all by a context-isolated `dev-reviewer` (opus). Round 1 asked for changes. The S6 rule was too broad: by class, a start error cannot be told from pre-start path-test errors (pathlib propagates other `OSError`s on Python 3.11-3.13) or from the post-end `temporary.is_file()` error. "Found usable" was presented as cited, and the two registers' open lists differed. Rounds 2 to 4 approved, each with one nit that was then fixed: the Python version of the pathlib observation, a reachable walk-through row, and the version scope of the lost-log consequence. Round 5 approved with no findings.
- **§9 notice:** https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6225487199 (7-day objection window from 2026-10-17).
- **D16:** nothing was built or run, and no `claude` was started. The facts come from the code and the records (pathlib behaviour was read from the installed 3.14 source and the 3.11-3.13 docs).
- **Follow-ups:** (1) code: on Python 3.11-3.13 an `OSError` from `clang_build.build`'s post-build `temporary.is_file()` test is passed on with no `result`, so the log is lost against ADR-0078 decision 2. A code task should wrap it or register it, in the manner of T-0244. (2) code: a way for the operation to tell a compiler-start `OSError` from same-class errors (for example a class of its own in `clang_build.build`), so that ADR-0079 decision 4 can be applied. (3) the remaining entries of ⑱ (마).
