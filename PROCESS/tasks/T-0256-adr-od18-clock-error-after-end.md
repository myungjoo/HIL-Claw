---
id: T-0256
title: Write ADR-0084 on what T-0255 makes true for `correctness.check` - a failed clock read after the compiler's end is now a `CompilerRunError`, so ADR-0082 decisions 2 and 4 reach it, and a plain `OSError` of `clang_build.build` comes only from before the start (more of OD-18 sub-question 18 part (ma))
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0254, T-0255]
touchesFiles: [ARCHITECTURE/decisions/ADR-0084-od18-correctness-check-clock-error-after-end.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 140, files: 4}
hq: []
---
## Why

ADR-0083 (`5a82c0c`) found one line of `hilclaw.clang_build.build` that raised a plain `OSError` after the compiler had ended: `duration_s = time.monotonic() - started` (ADR-0083 P2). ADR-0083 decision 3 counted it among the reasons why a plain `OSError` of `build` gets no row ("And not always before the start"). It stated the cost: the log is dropped, and a build that S7 or S8 would make a result is answered by a tool failure. It named, as one thing that "would let it be placed", "a code change that raises no plain `OSError` after the compiler started".

Task T-0255 (PR #161, `8782cf8`) made that change. The clock read now stands inside the `try` around `_communicate`. An `OSError` from it is raised as `CompilerRunError`, `from` that error, with `timed_out = held.timed_out`, `log = held.decoded()` and the existing `removal_error` rule. T-0255's Result: "A plain OSError of build now comes only from lines before subprocess.Popen (ADR-0083 P3 (a)-(e))". The docstring of `CompilerRunError` now covers "reading the clock for the build's duration" once the call had ended the process.

So this error now meets the records written for `CompilerRunError`, and no record yet says what that means:

1. **The time-limit branch.** After a kill for the time limit, `_communicate` returns, and a failed clock read then gives a `CompilerRunError` whose `timed_out` is true. ADR-0082 decision 2 answers that class and member with S8, (B) `"build_time_limit"`, from what `build` states. Its "Why" reads the error as coming "afterwards, from the steps by which the call ends a build past its limit". A clock read is not one of the steps ADR-0082 L2 lists, and here the compiler's end was seen. The record weighs whether decision 2 and its reading still hold for this source, and whether decision 3 (the log handed to the keeper when it is not `None`) applies unchanged.
2. **The other branch.** After a normal end (exit 0 or non-zero), a failed clock read gives a `CompilerRunError` whose `timed_out` is false and whose `log` is all the output. ADR-0082 decision 4 keeps that branch open "for the reason of ADR-0081 decision 2: no wording of S3 to S10 names a compiler the call lost while it ran". This compiler was not lost: it ended, but the error does not state its return code. The record weighs whether this source stays inside the open entry of decision 4 and for what reason, or whether something else follows. It also says what this means for the log, which is now all the output.
3. **A plain `OSError` of `build`.** It now comes only from the lines before the start (ADR-0083 P3 (a) to (e)). The record confirms this from the code at `8782cf8`. It says whether the remaining reasons of ADR-0083 decision 3 ("One class serves two rows", "Sources no row names", "'Before the start' is several rows") still keep it without a row. Leaving it open is an acceptable outcome if the record says why.

Leaving any of these open is acceptable if the record gives its reasons and names what would let a later record decide, as ADR-0082 decision 4 and ADR-0083 decision 3 did. This is a design-level OD part. Under DRIVER §9 the executor may answer it with an ADR, accepted by a reviewer's Approve and followed by a #5 notice with a 7-day window. No owner-only item is needed (#5 A/B items, OD-3, OD-25, C-6). Do not take any step that needs a new value of `condition` or `error.kind`, a new data-plane member, or an owner fact or value judgement. Leave such a point open and say so in the record, or return BLOCKED (requirement unclear / owner-only decision, DRIVER §3).

**Why this item now.** STATE has no lock, current task or next task. Every non-DONE task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). There was no open PR on 2026-10-17 at `e1ffe5c`. PLAN P1-1 continues through OD-18 work. This task depends on none of those HQs. It is the follow-up T-0255's Result names first. The other follow-ups are a code task for the path tests (ADR-0083 decision 3) and the row of the `timed_out`-false branch as a whole, which may need a new `error.kind` and so an HQ. This task does not place that row unless no new value is needed.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0256-<slug>`, the trailer `Task: T-0256`;
  - §8 and §9 (lines 135-148): the HQ path, OD closure authority, the #5 notice with the last line `— posted by driver`.
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (document mode, steps 10-12) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: section "Record format".
- `ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md`, all of it. It is the latest model of form and tone. Read especially P2 to P4 (lines 21-30), decision 3 (lines 46-61), decision 4 (lines 63-66), the walk-through (line 78), Consequences.
- `ARCHITECTURE/decisions/ADR-0082-od18-correctness-check-compiler-run-error-time-limit.md`, all of it. Read especially L1 to L5 (lines 19-24) and decisions 2 to 5 (lines 34-56).
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`: K4 (line 23), decision 2 (from line 32), decision 4 (lines 47-51), Consequences.
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decisions 2, 6 and 7.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: Context O1 and O2 (from line 20), decision 4 (lines 69-104), for S7, S8, S9 and "What the operation observes decides the row".
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 and 5.
- `hilclaw/clang_build.py` at `8782cf8` or later, read only:
  - the docstring of `CompilerRunError` (lines 99-124);
  - `build` (lines 186-336), especially the docstring sentence on `CompilerRunError` and the lines from `started = time.monotonic()` (line 264) to the `CompilerRunError` raise (line 312);
  - `_Held` and `_communicate` (lines 361-387), for what `held.timed_out` and `held.raw` are when `_communicate` returns after a kill.
- `PROCESS/tasks/T-0255-clang-build-clock-error-after-start.md`: "The change, stated" and Result.
- The recording rules of the three registers. Follow them, not the wording of earlier task files or earlier entries:
  - `ARCHITECTURE/Requirements.md` line 84, "행 형식";
  - `ARCHITECTURE/OpenDecisionProposals.md` line 8, "기록 규칙";
  - `ARCHITECTURE/StandardScenarios.md` line 170, the first paragraph of §검사 결과;
  - where they apply: the OD-18 row (Requirements line 109); the OD-18 section of OpenDecisionProposals (from line 250, its 채택분 lines 294-295, sub-question ⑱ at line 308, whose (마) "남음" list names "컴파일러 종료 뒤 `time.monotonic`에서 오는 `OSError`"); the "최근 재검사" line (StandardScenarios line 172).

## Acceptance Criteria

1. **Entry check** (CLAUDE.md "세션 진입 점검"), before the first edit:
   - Run `gh pr list` and read issues #4, #5, #7 and #8.
   - Confirm that `ADR-0084` is free on `main` and on every remote branch (`git ls-remote`, `git ls-tree` of each branch). At planning time the highest number on a remote branch was ADR-0075. If 0084 is taken, use the next free number everywhere this task says 0084.
   - Look on #5 for an owner comment without the driver tail on ADR-0082, ADR-0083, T-0255 or ⑱ (마). If one bears on this record, follow it, or return BLOCKED if it conflicts.
   - If an open PR touches any file in `touchesFiles`, return BLOCKED (open-PR conflict).
2. **ADR-0084** in `ARCHITECTURE/decisions/`, in the format of ADR-0001 "Record format", with the Status conventions of ADR-0083:
   - the three kinds of content;
   - the records it builds on, with their windows;
   - "no member, no value of `condition` or `error.kind`, no version";
   - "no sentence of an earlier record is replaced or edited";
   - the #5 window.
   The slug may differ from the one in `touchesFiles` if the content warrants it.
   - **Context**: observations at `8782cf8` of what `build` states and does, binding no code:
     - where the clock read now stands;
     - what `timed_out` and `log` are for a failed clock read after a time-limit kill and after a normal end, on POSIX and on Windows, as the code and docstring state them;
     - that no artefact is placed and the temporary file is removed;
     - the list of sources of a plain `OSError` of `build`, confirmed from the code and not copied from ADR-0083 P3.
   - **Decision**, covering the three questions of Why:
     - (1) whether ADR-0082 decisions 2 and 3 reach the time-limit branch with a failed clock read, and on which reading;
     - (2) what the other branch with a failed clock read after a normal end is, and what follows for its row and its log;
     - (3) whether a plain `OSError` of `build`, now only from before the start, gets a row or stays open, with the reasons and what would let it be placed;
     - a section "How far (마) is answered" that restates the open list as it stands after this record.
     Quote every cited sentence with its source. Label every reading of a cited row as this record's reading. State every cost.
   - **Alternatives considered** (table), **Consequences**, **Boundaries**, **References**. Consequences lists, without editing them, the sentences of ADR-0081 (K4, decision 4), ADR-0082 (L2, L5, decisions 2 and 4) and ADR-0083 (P2, P4, decision 3, decision 4, walk-through, Consequences) that become less exact. Check each one against the text; list only the ones that do.
   - No new value of `condition` or `error.kind` and no reserved kind. Write "Runtime acceptance items: none" unless the executor finds one. If so, name it and do not try to close it.
3. **Register edits**, each by the recording rule written in that file (Required Reading). Do not restate the ADR's content in any register, and add no dated paragraph.
   - `Requirements.md`, OD-18 row: per its "행 형식".
   - `OpenDecisionProposals.md`, OD-18: per its "기록 규칙". The (마) end status of ⑱ is rewritten in place so that its "남음" list matches decision "How far (마) is answered".
   - `StandardScenarios.md`: re-check the S-rows that cite OD-18 by the rules of that document. Record the result per the first paragraph of §검사 결과.
4. **No other file** is edited: no change to ADR-0001 to ADR-0083, `hilclaw/`, `tests/`, CI, UsageCases, `PROCESS/` or any settings file.
5. **Document mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0256-<slug>`;
   - run the context-isolated reviewer cycle to Approve within 7 rounds;
   - rebase on `origin/main` and push straight to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0256`;
   - delete the branch.
6. **§9 notice.** After landing, post a comment on #5 in English. It names ADR-0084 and the landed commit and states the 7-day objection window. Its last line is `— posted by driver`. Put the URL in Result.
7. Run only reading tools (`git`, `gh`, file reads). Build or run nothing. Start no `claude` process in any form (D16).
8. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files.

## Out of Scope

- Any new `error.kind` or `condition` value, and a row for the `timed_out`-false branch as a whole (a compiler lost while it ran). If question (2) can be answered only with a new value, leave it open.
- Any code change to `clang_build.build` or its callers: telling the source tests from the output tests (ADR-0083 decision 3), stating the return code in `CompilerRunError`, and the `cpu_standin` operation of `correctness.check` (HQ-0026).
- ⑱ (가), (다), (라) and the size bound of (나); ⑰ (다); ⑲.

## Follow-ups

- (code) Make `build` tell the source path tests from the output path tests, and both from the other lines before the start (ADR-0083 decision 3).
- (code, if ADR-0084 names one) A change of `build` that would let a later record place the clock error after a normal end, for example one that keeps the return code it already read.
- (doc) The row of the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4). It may need a new `error.kind`, and so be a data-plane or owner question (HQ).

## Result

DONE — pushed to main as 26e8ac0 (document mode; trailers Reviewed-by: reviewer agent (5 rounds, Approve), Task: T-0256). Branch claude/T-0256-adr-od18-clock-error-after-end deleted locally and on origin.
ADR-0084: (1) a failed clock read after a time-limit kill is S8 by ADR-0082 decisions 2 and 3, on this record's reading of their reason; the compiler had ended and was waited for. (2) After a normal end it stays in ADR-0082 decision 4's open entry, for a reason of its own: what build states cannot tell it from the closing source, and the return code is not stated (S7 if non-zero, no row by its wording for status 0). The log is held but not handed over; costs stated. (3) A plain OSError of build now comes only from before Popen; ADR-0083 decision 3's other three reasons still hold, so it has no row.
Registers: Requirements OD-18 row (one link), OpenDecisionProposals OD-18 (adopted line; the ⑱ (마) list rewritten in place), StandardScenarios latest re-check (S0, S1-b, S2, S5, S6: no verdict change, no gap). No new condition/error.kind value, member or version. Runtime acceptance items: none.
§9 notice on #5 (7-day window until 2026-10-24): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6229403473
Follow-ups: (code, suggested next) make clang_build.build state the return code it holds for a failed clock read and tell that source from the closing source (ADR-0084 decision 3); (code) tell the source path tests from the output path tests (ADR-0083 decision 3); (doc) the row of the timed_out-false branch as a whole, which may need a new error.kind (HQ).
