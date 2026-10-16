---
id: T-0248
title: Write an ADR that answers more of OD-18 sub-question 18 part (ma) for `correctness.check` — `CompilerNotStartedError` (T-0247) as the start error ADR-0079 decision 4 places, and the row of `ArtefactNotCheckedError` (T-0246)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-6, FR-10, OD-18]
dependsOn: [T-0245, T-0246, T-0247]
touchesFiles: [ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 170, files: 4}
hq: []
---
## Why

ADR-0079 (T-0245, `994ca3d`) placed the errors of one `clang_build.build` call that the code told apart at `7003362`. It left two things open under OD-18 ⑱ (마) (its decision 5):
- "telling an error from the start apart from an `OSError` of the same class before the start or after the end (decision 4; N2)". Decision 4 places a start error in S6 (`compiler_unavailable`), but it "applies to an error the operation can tell came from the start".
- "one from the test of the temporary file after the compiler ended, which carries no log". Its Consequences said that log "is lost … unless `clang_build.build` changes".

Two code tasks have since changed `hilclaw/clang_build.py`:
- **T-0246** (PR #156, `a355078`). After an exit 0, `build` tests the temporary file with `os.stat` and `stat.S_ISREG`. `FileNotFoundError` and `NotADirectoryError` read as "no artefact", as before. Any other `OSError` of that test is raised as the new `ArtefactNotCheckedError`. That is an `OSError` subclass whose `result` is the `BuildResult` with `ok` false, `returncode` 0 and the compiler's log, plus a `removal_error`. Nothing is moved. T-0246's Result also notes a behaviour change: on Python 3.11 to 3.13 this turns errors that `Path.is_file` used to swallow as `False` (`ELOOP`, `EBADF`, Windows errors 21/123/1921) into `ArtefactNotCheckedError`. Those builds were "exit 0 and no artefact" before.
- **T-0247** (PR #157, `03f9007`). `build` creates the compiler with `subprocess.Popen`. An `OSError` raised while constructing `Popen` is raised as the new `CompilerNotStartedError`, an `OSError` subclass with no `result` and with a `removal_error`. An `OSError` raised after the process was created (for example from `communicate`) is still passed on as it is, or the removal's error instead when the removal fails too. The T-0247 reviewer noted (info) one more case. An `OSError` raised inside `Popen.__init__` after the OS created the process is also raised as `CompilerNotStartedError` and is practically unreachable. On POSIX that is reading or closing the exec error pipe; on Windows, closing the thread handle.

Under the recording rules in Requirements.md ("행 형식") and OpenDecisionProposals.md ("기록 규칙"), the registers change only with an ADR. So this follow-up (named in the Follow-ups of T-0246 and T-0247) is a design-level ADR under DRIVER §9, not a register note.

**Why this item now.** No lock, no current or next task, no TODO or INTERRUPTED task file, and no open PR (checked 2026-10-17 at `6925fcf`). PLAN P1-1 continues through OD-18 work. Its `profiler.collect` part waits on HQ-0025, and ADR-0078 slices 1 to 3 wait on HQ-0026 (T-0243). This record depends on neither and decides neither question.

The unlanded branches of T-0210 (ADR-0068) and T-0231 (ADR-0074) also edit row OD-18 and the "최근 재검사" line. They are branches, not open PRs (DRIVER §3-3), and this task touches no file on them. 0080 is the next free ADR number on `main` and on every branch (checked). If it is taken by execution time, take the next free number and rename the file and `touchesFiles` to match.

**What the record must settle.** The executor weighs the alternatives, and the reviewer checks them against ADR-0060 decision 4, ADR-0078 decision 2, ADR-0079 and the code at `03f9007` or later.
1. **Start errors told apart.** State that `CompilerNotStartedError` is an error "the operation can tell came from the start" in the sense of ADR-0079 decision 4. Its row and kind then follow from that decision; this record does not restate them. Cover the `removal_error` case (decision 4 already places "after such a failed start, from removing the temporary file"). Say whether the case the T-0247 reviewer named also stays under decision 4 or needs its own sentence: an `OSError` from inside `Popen.__init__` after the OS created the process.
2. **`ArtefactNotCheckedError`.** Decide which row of ADR-0060 decision 4 it is, and what the call answers. Weigh at least these candidates:
   - (a) S9 `build_output_missing`. The carried build has `returncode` 0 and `ok` false, which reads S9 by itself (ADR-0060 decision 4). The row's wording is "Status 0 and no executable at the path, or it cannot be moved there". It also matches what the formerly swallowed errors gave before T-0246.
   - (b) answer by the row the carried `result` shows, as ADR-0079 decision 3 does for `TemporaryNotRemovedError`.
   - (c) leave it open with a reason.
   - (d) another existing kind, for example S3 or `operation_answer_invalid`.
   Say what happens to the log: the compiler ended, so ADR-0078 decision 2 keeps it, and decision 6 hands it over. Cite these; do not restate them. Say what happens to a `removal_error` it carries.
3. **What stays open under (마)**, named in the ADR's decision on scope and in Boundaries. At least:
   - an `OSError` raised after the compiler process was created and before it ended, and the removal error that replaces it;
   - the path tests before the start (`_checked_sources` and the output-directory tests still use `pathlib` `is_file` / `is_dir` / `exists` — read the code), including other `OSError` classes they propagate on 3.11 to 3.13;
   - the other entries ADR-0079 decision 5 names (`FileNotFoundError` / `IsADirectoryError` for a source or the output path, the `TypeError` of `clang_build.build`, what `subprocess` passes on beyond `OSError`, and the `local_run.run` entries).
   Answer only what the code now tells apart.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0248-<slug>`, the trailer `Task: T-0248`, size cap), §8 (lines 135-139: the driver tail of #5 comments) and §9 (lines 141-148: the ADR route, the notice, the 7-day window).
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (whole procedure, document mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`, the whole file (104 lines). It is the record this one extends, and the model of the Status wording and record shape. Do not edit it.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 4 (lines 69-104; table rows S3, S6, S9 at lines 90, 93, 96; the paragraph at line 102), decision 7 (lines 122-130), Consequences (lines 154-161), Boundaries (lines 162-176).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2 (lines 32-38), decision 6 (lines 64-80), decision 7 (lines 81-91).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` decisions 4 and 5 (the build directory, situations S1 to S10).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` "Record format" (line 146 to the end).
- `hilclaw/clang_build.py` at `03f9007` or later: the module docstring (lines 1-23), the error classes (lines 61-147), `build` (lines 150-276) and `_checked_sources` (lines 347-364). Facts about it go into the record as observations at a named commit.
- `PROCESS/tasks/T-0246-clang-build-keeps-log-on-artefact-test-error.md` and `PROCESS/tasks/T-0247-clang-build-tells-start-errors-apart.md`: Why, and Result, including the reviewer notes.
- `ARCHITECTURE/Requirements.md`: paragraph "행 형식" (line 84) and row OD-18 (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: header bullet "기록 규칙" (line 8), the OD-18 adopted-record bullets (lines 290-291), and the sub-question ⑱ bullet (line 304).
- `ARCHITECTURE/StandardScenarios.md` §검사 결과 (line 168 onward: the first paragraph and the "최근 재검사" line at line 172).

## Acceptance Criteria

1. **Session entry check.** Before the first edit, run `gh pr list` and read issues #4, #5, #7 and #8, and state this in the Result. Report any open PR that touches row OD-18, the OD-18 section or the re-check line. If #5 carries an owner comment on ADR-0079, on errors of two rows, on S9 or on ⑱ (마), stop and report it. That includes an objection inside ADR-0079's window.
2. **One new record**, `ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md` (number per Why), in the record format of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References.
   - Status says: it was accepted under DRIVER §9 by the reviewer's approval and is not confirmed by the owner; which part of ⑱ (마) it answers and what it leaves open; it changes no member, `condition` value, `error.kind` value, `schema_version` or layout version; it builds on ADR-0060, ADR-0078 and ADR-0079 and falls with any of them; the owner has a 7-day objection window.
   - It separates owner sentences, cited sentences and its own design, as ADR-0079 Status does.
3. **Points 1 to 3 of Why are settled** for `correctness.check` of the first case and of the mock.
   - Each choice is weighed against at least one alternative in "Alternatives considered". For point 2, weigh at least candidates (a) to (d).
   - Facts about `hilclaw/clang_build.py` are observations at a named commit (`03f9007` or later). The record binds no code: names and modules stay the code task's.
   - Read the version claims of T-0246's Result against the CPython `pathlib` source before stating them. Give them as observations, or name them as taken from T-0246's Result.
4. **Earlier records are not edited.** The record lists the landed sentences it leaves less exact without editing them. At least: ADR-0079 N2, the Consequences sentence on the lost log, and the decision 5 items it now answers; and ADR-0060 decision 4's two-row list where relevant.
5. **Limits.** The record adds:
   - no value of `condition`;
   - no value of `error.kind` and no reserved kind;
   - no member of any file, result, request or line;
   - no `schema_version` or layout version.
   It answers only with the six backend kinds of ADR-0060, `operation_answer_invalid`, or the outcome the carried `result` shows. If none of these fits without one of the additions above, stop and return BLOCKED (`requirement-unclear`) with the question.
6. **Register edits follow the recording rules written in those files.** Read the rules there and apply them as written:
   - `ARCHITECTURE/Requirements.md` row OD-18: follow the "행 형식" paragraph. The new ADR is one more link in the 확정분 list. The 잔여 part is rewritten in place only if it no longer names what is open.
   - `ARCHITECTURE/OpenDecisionProposals.md` OD-18 section: follow the header's "기록 규칙". The new ADR gets one adopted-record line. The ⑱ bullet's end status is rewritten in place so that `남음:` names what is now open under (마). Do not edit the question wording.
   - No other `ARCHITECTURE/` file and no earlier ADR is edited.
7. **Coverage re-check.** Re-check per CLAUDE.md "문서 커버리지 재검사", following the rule in the first paragraph of StandardScenarios §검사 결과, and update that section as the rule says. Change an S-row note only if it now says something untrue.
8. **D16.** No step starts `claude` in any form, builds anything or runs a compiler. Facts come from the code, the CPython source and the records.
9. **Document mode** per CLAUDE.md A-13:
   - Work on branch `claude/T-0248-<slug>`.
   - Run the reviewer cycle (dev-item-address steps 10-12) to Approve within the 7-round cap.
   - Land as one commit: rebase on `origin/main`, squash the branch's commits into one, then push directly to `main`. The commit carries the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0248`.
10. **§9 notice on #5 after landing.** It gives:
    - the record's number and title;
    - the part of OD-18 ⑱ (마) it answers and what stays open;
    - the landing commit link;
    - the 7-day window;
    - the driver tail of DRIVER §8.
11. Size within the DRIVER §5 caps (≤ 300 changed lines, ≤ 5 files).

## Out of Scope

- Any code, test or CI change, including `hilclaw/clang_build.py` and the operation of `cpu_standin`. Any further code means of telling errors apart (for example of an `OSError` after the process was created) is a later code task.
- ADR-0078 slices 1 to 3 (T-0243, BLOCKED on HQ-0026), anything of HQ-0025, and the branches of T-0210 and T-0231.
- `local_run.run`, the run tools' timing build (⑲ (나) to (라)), ⑱ (가), (다), (라), the size bound of (나), and ⑰ (다).

## Follow-ups

- When the operation of `cpu_standin` for `correctness.check` is written (after ⑱ (라), OD-14 ① and ⑱ (다)), its code applies ADR-0079 and this record.
- The remaining entries of ⑱ (마), when code tells them apart or a record places them.

## Result
