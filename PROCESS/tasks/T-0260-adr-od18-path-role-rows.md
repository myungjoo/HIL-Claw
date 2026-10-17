---
id: T-0260
title: Write ADR-0086 on which rows of `correctness.check` the `path_role` of `clang_build.build` (T-0259) lets an operation place for an `OSError` of the path tests before the start (more of OD-18 sub-question 18 part (ma))
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0259]
touchesFiles: [ARCHITECTURE/decisions/ADR-0086-od18-correctness-check-path-role.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0083 decision 3 leaves a plain `OSError` of `clang_build.build` without a row of `correctness.check`. ADR-0084 decision 4 keeps it open. Both rest on two reasons about what `build` states:

- **"One class serves two rows."** `FileNotFoundError` and `IsADirectoryError` come from the source test (S5) and from the output test (S3), and the other classes the path tests raise (ADR-0083 P3 (a)) come from both.
- **"Sources no row names."** `os.getcwd`, `os.urandom`, `time.monotonic` and the search for the compiler (P3 (b) to (e)) raise `OSError`s in the same classes before the start.

The first item of "What would let it be placed" in ADR-0083 decision 3 is a code change that tells the source tests from the output tests, and both from the other lines before the start: "Then a record can weigh S5 and S3 for the first two." ADR-0084 decision 4 names the same item.

T-0259 (PR #163, `92d5432`) made that change. Every `OSError` that leaves a path test of a source now carries `path_role == "source"`. Every one that leaves a path test of the output carries `path_role == "output"`. This includes an `OSError` that the test call itself raises, re-raised as the same object. No other error of `build` carries the attribute: not one from `os.path.abspath` (and so `os.getcwd`), `_resolve`, `secrets.token_hex`, `time.monotonic`, the run or after it, and none of the five error classes. The classes and messages are unchanged. See T-0259 Result and the `build` docstring.

This task writes the record those ADRs named. It is a design-level ADR under DRIVER §9, weighing what an operation of `correctness.check` (first case and mock) now observes for these errors and placing what it can. OD-18 is not owner-only under §9, so the ADR is in scope. The T-0259 reviewer also noted that on Python 3.14 `Path.is_file`, `is_dir` and `exists` may swallow `OSError`, so an error raised by the test call itself may occur only on 3.11 to 3.13. ADR-0083 P3 (a) already records this ("none on 3.14 … on Windows not read"). The record states it as a limit and does not establish it by running code.

Why this item now: STATE has no lock, current or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). The runtime-acceptance HQs (HQ-0013, -0014, -0016 to -0019) do not bear on this record. PLAN P1-1 continues through the OD-18 work. This task depends on none of those HQs, and no blocked task touches the four files. HQ-0026 (the log keeper's code) is not needed, because errors before the start have no log (ADR-0078 decision 2).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, 2h30 time limit;
  - §5 (lines 86-114): task format, branch `claude/T-0260-<slug>`, trailer `Task: T-0260`, size cap;
  - §8 (lines 135-139): the driver tail on #5 comments;
  - §9 (lines 141-148): OD closing authority, the 7-day notice.
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode, `Reviewed-by` trailer), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md`: Context P3 and P4 (lines 22-30), decisions 1, 3 and 4 (lines 35-66), Alternatives, Consequences.
- `ARCHITECTURE/decisions/ADR-0084-od18-correctness-check-clock-error-after-end.md`: decisions 4 and 5 (lines 55-69), alternative (h) (line 93), Consequences.
- `ARCHITECTURE/decisions/ADR-0085-od18-correctness-check-clock-error-return-code.md`: Status (lines 3-14, as the latest model of the Status block), decision 6, Consequences (lines 97-107).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: Context O1 and O2 (from line 16), decision 4 (lines 69-104). Above all:
  - the table rows S3 (line 90) and S5 (line 92) with their kinds `build_directory_unusable` and `build_input_missing`;
  - the paragraph at line 102 ("one class can arise in two rows … a `FileNotFoundError` or `IsADirectoryError` for a source (S5) or for the output path (S3)"; the `NotADirectoryError` → S3 sentence; "An operation places such an error by the step of its own …");
  - line 103 ("What the operation observes decides the row");
  - decision 7 (line 122 onward).
- `ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md`: Status (line 7), Context M4 (line 23), decision 4 (line 52).
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`: alternatives row 4 (line 80).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decision 5 (lines 95-114), the list of situations with the S3 and S5 wording.
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2 (lines 32-38), on builds with no log.
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 and 5 (lines 64-84), `operation_answer_invalid`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (line 146).
- `hilclaw/clang_build.py` at `92d5432`, read only, do not edit:
  - the `build` docstring sentence on `path_role` (around lines 222-232);
  - the output tests (around lines 262-275);
  - `_checked_sources` (around lines 439-459).
- `PROCESS/tasks/T-0259-clang-build-path-test-role.md`: "The change, stated", Result, Follow-ups.
- The recording rules, read and followed as written:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and register row OD-18 (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet of the header (line 8), and section `## OD-18` (from line 250), including the 채택분 lines up to line 297 and the sub-question 18 bullet (line 310);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of `# 검사 결과` (line 170), the "최근 재검사" line (line 172), and the verdict rows whose notes cite OD-18.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md). Before editing:
   - Run `gh pr list` and read issues #4, #5, #7 and #8. If an open PR edits OD-18 sub-question 18 or any of the four files, stop and return BLOCKED (open-PR conflict risk).
   - Confirm that `ADR-0086` is still the next free number under `ARCHITECTURE/decisions/`.
   - Check for an owner comment on #5 (one without the driver tail) that speaks to ADR-0083, ADR-0084, ADR-0085, T-0259 or (ma). If there is one, cite it and follow it.
2. **New file** `ARCHITECTURE/decisions/ADR-0086-od18-correctness-check-path-role.md`, in the ADR-0001 record format.
   - Status is "Accepted under DRIVER §9 (D6)". It says which sentences are the owner's (O1 and O2, quoted as ADR-0060 Context quotes them), which are cited, and which are this record's own design.
   - Statements about code are observations at `92d5432` and bind no code.
   - The facts about Python versions are cited from ADR-0080 and ADR-0083 or from T-0246's and T-0259's Results. None is established by running code.
3. **What the record must weigh and answer.** The answers are the record's own design, reviewed under §9. Each choice states its reason and its cost.
   - **(a) Telling the errors apart.** Can the operation now tell, from what `build` states alone (`isinstance(error, OSError)`, not one of the five classes, `getattr(error, "path_role", None)`):
     - a source error from an output error;
     - both from the other sources before the start (P3 (b) to (e)), which carry no `path_role`?

     On which reading of ADR-0060 decision 4's "What the operation observes decides the row"? Say what the reason "One class serves two rows" still holds for and what it no longer holds for.
   - **(b) `"source"`.** Weigh S5, `build_input_missing`, for a `FileNotFoundError` and an `IsADirectoryError` from a source test. Weigh separately an `OSError` that the test call itself raises (for example a `PermissionError` from a refused `stat` on 3.11): does the wording "A file of the compiled set is no longer a regular file when the build is called" cover a file that could not be tested? Weigh S5 against leaving that case open.
   - **(c) `"output"`.** Weigh S3, `build_directory_unusable` ("The build directory cannot be made or written"), for:
     - a missing output directory (`FileNotFoundError`);
     - an output that is a directory (`IsADirectoryError`);
     - an `OSError` the test call itself raises.

     The `NotADirectoryError` for the output path is already S3 (ADR-0060 decision 4). State whether this record changes that row; it is expected not to.
   - **(d) No log.** No compiler was started, so there is no log to hand over (ADR-0078 decision 2). Confirm this, with no new rule.
   - **(e) What stays open.** An `OSError` with no `path_role` before the start (P3 (b) to (e)) stays open under "Sources no row names", unless this record reads a row's wording to cover it. Reading S6 or S3 to cover them is in scope only if the reason is stated against ADR-0083 decision 3's reading. Anything that would need a new situation in the ADR-0056 decision 5 list or a new value is left open.
   - **(f) No data-plane change.** Add no new value of `error.kind` or `condition`, no new member, no reserved kind, and no change to `schema_version` or the layout version (CLAUDE.md A-13 data-plane rule). `path_role` is a Python attribute of an in-process exception, not a data-plane member; the record says so. If the record finds that only a new value would place a case, it leaves that case open, says so, and names in Follow-ups that placing it needs an owner HQ. It does not decide it.
   - **(g) "How far (ma) is answered".** End with this decision, as ADR-0083 decision 4, ADR-0084 decision 5 and ADR-0085 decision 6 do. List what this record answers and every entry of (ma) that stays open. That includes:
     - the `CompilerRunError` with `timed_out` false and `returncode` `None`;
     - the `TypeError` of `build`;
     - what `build` passes on from `subprocess`;
     - the `local_run.run` entries.
   - **Walk-through and Alternatives tables.** A walk-through table with one line per class and role of (b) and (c), and at least one line without `path_role`. An Alternatives table covering at least:
     - S5 and S3 by role (chosen or not);
     - leaving all open;
     - S5 for only the two classes `build` raises itself;
     - a new kind for an error the test raises (declined as a data-plane change);
     - the operation's own step instead of `path_role`.
4. **No sentence of an earlier ADR is edited.**
   - Consequences lists the sentences that become less exact. Look at least at:
     - ADR-0060 decision 4 (the two-row list at line 102);
     - ADR-0080 decision 4;
     - ADR-0081 alternatives row 4;
     - ADR-0083 decision 3 ("One class serves two rows", the first item of "What would let it be placed") and decision 4;
     - ADR-0084 decision 4, alternative (h) and decision 5;
     - ADR-0085 decision 6.

     Find each one by reading, not from this list alone.
   - Consequences states what a later code task of the `cpu_standin` operation applies, and that this record binds no code and needs no change of `clang_build.build`.
   - Consequences states the "Runtime acceptance items". None are expected: no `claude`, compiler or container is started or required.
5. **Register, proposals and coverage edits follow the recording rules written in those files**, read as they stand. Do not use the wording of earlier task files or the shape of earlier edits as the model.
   - `ARCHITECTURE/Requirements.md`, row OD-18: per the "행 형식" paragraph (line 84).
   - `ARCHITECTURE/OpenDecisionProposals.md`, section OD-18: per the header's "기록 규칙" (line 8).
   - `ARCHITECTURE/StandardScenarios.md`: recheck coverage by that file's rules for every scenario row that cites OD-18. Update `# 검사 결과` exactly as its first paragraph (line 170) says.
   - In all three, add one link for the new ADR. Rewrite the open parts in place. Do not restate the record and do not add dated paragraphs. OD-18 keeps its status word, since the record does not close all of it.
6. **Document mode** (CLAUDE.md A-13):
   - branch `claude/T-0260-<slug>`;
   - the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds;
   - rebase on `origin/main`, then a direct push to `main`;
   - commit trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0260`;
   - delete the branch.

   After landing, post the §9 notice on issue #5 in English, ending with the line `— posted by driver` (DRIVER §8). Record its URL in `## Result`.
7. **Size:** one new file and three edited files, at most 300 changed lines in total.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `.claude/` or the settings files.
- Any change to ADR-0001 to ADR-0085 or to `ARCHITECTURE/UsageCases.md`.
- Rows for the other entries of (ma), except to restate them as still open. This covers:
  - the `CompilerRunError` with `timed_out` false and `returncode` `None`;
  - the `TypeError` of `build`;
  - what `build` passes on from `subprocess`;
  - the `local_run.run` entries.
- Parts (ga), (da), (ra) and the size bound of (na) of sub-question 18, and sub-questions 17 and 19.
- Any new value of `error.kind` or `condition`, any new data-plane member, and any owner-only item (DRIVER §9: #5 A/B items, OD-3, OD-25, C-6).
- Starting `claude`, a compiler or a container, or running code to establish facts about `Path` methods on any Python version. The observations come from reading the source and earlier records.

## Follow-ups

- (possible HQ) If ADR-0086 leaves an error the test itself raises, or an `OSError` with no `path_role`, open because only a new `error.kind` or a new situation would place it, the driver records that question for the owner.
- (code, later) The `cpu_standin` operation of `correctness.check` applies ADR-0079 to ADR-0086 when it is written. HQ-0026 and PLAN P1-1 govern that.

## Result

- Landed in document mode as one commit on `main` (hash and the #5 notice URL are added below after landing); branch `claude/T-0260-adr-od18-path-role` deleted.
- Files: new `ARCHITECTURE/decisions/ADR-0086-od18-correctness-check-path-role.md`; one link each in `Requirements.md` (row OD-18), `OpenDecisionProposals.md` (OD-18 adopted line and sub-question 18 "남음" rewritten in place) and `StandardScenarios.md` ("최근 재검사" line; S0, S1-b, S2, S5, S6 rechecked, no verdict change, no gap). 148 lines added, 3 removed.
- Entry check: no open PR; ADR-0086 was the next free number; no owner comment on #5 about ADR-0083/0084/0085, T-0259 or (ma) (every comment since 2026-10-16 carries the driver tail).
- Decisions: `path_role` read as a documented member of what `build` states; `"source"` is S5 `build_input_missing`, `"output"` is S3 `build_directory_unusable`, an OSError the test itself raises included (same answer on every Python version, except a refused `target.is_dir()` that does not raise on 3.14, whose version-dependent cost is stated); no log (ADR-0078 decision 2); the NotADirectoryError S3 row of ADR-0060 decision 4 unchanged; an OSError with no `path_role` stays open. No data-plane change; no earlier ADR edited.
- Deviation from AC 2: Status says no owner sentence is quoted (O1 and O2 reach the record only through ADR-0060 and ADR-0078), as ADR-0080 does, because both rows placed are tool failures before any compiler ran; the reviewer accepted this.
- Review: 6 rounds by a context-isolated dev-reviewer. R1 Request changes (less-exact list incomplete; owner-sentence status); R2 Request changes (a refused `target.is_dir()` on 3.14 lets the build go on); R3 to R5 Approve with nits, each fixed; R6 Approve.
- Follow-ups: (possible HQ) whether an OSError with no `path_role` (failed working directory, random bytes, clock or compiler search before the start) gets its own situation and a new `error.kind`; the record names the question and does not decide it (ADR-0086 decision 6, Consequences). (code, later) the `cpu_standin` operation of `correctness.check` applies ADR-0079 to ADR-0086.
- Landed on `main` as bb4ec03; §9 owner notice on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6230836828.
