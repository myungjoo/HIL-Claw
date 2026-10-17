---
id: T-0254
title: Write ADR-0083 on what T-0253 makes true for `correctness.check` - the K4 (ii) entry of OD-18 sub-question 18 (ma), and whether a plain `OSError` of `clang_build.build`, now only from before `Popen`, gets a row
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18]
dependsOn: [T-0253]
touchesFiles: [ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 130, files: 4}
hq: []
---
## Why

ADR-0081 K4 found two sources of an `OSError` that `hilclaw.clang_build.build` raises outside its five classes:
- (i) a line of `build` before `subprocess.Popen` is called;
- (ii) a failed removal of the temporary file, raised in place of an exception that is no `OSError`.

ADR-0081 decision 5 and ADR-0082 decision 5 both keep "the removal error raised in place of an exception that is no `OSError` (ADR-0081 K4 (ii))" open under OD-18 sub-question 18 part (ma).

Task T-0253 (PR #160, `0305d7b`) changed (ii). When an exception that is no `OSError` leaves `build`'s `try` and the removal then fails, that exception now passes on unchanged: the same object, with its own traceback and chain. The removal error is attached to it as one note (`add_note`) and is not raised. T-0253's Result states the consequence: "A plain OSError of build now comes only from the lines before subprocess.Popen (ADR-0081 K4 (i))." It names this record as the follow-up.

No record yet says what this change means for `correctness.check`. Two questions are open:
1. **The K4 (ii) entry of (ma).** The exception that now passes on is either a request to end (`KeyboardInterrupt`, `SystemExit`) or another `Exception` (for example a `TypeError` from inside the construction of `Popen`). ADR-0045 decisions 4 and 5 already say what the landed rules do with each. The record weighs whether the entry is now answered by those rules, with the note changing nothing, and states the answer.
2. **A plain `OSError` of `build`.** Is the fact that it now comes only from before the creation of the compiler process enough to give it a row (for example S3 or S5 of ADR-0060 decision 4), or does it stay open? ADR-0081 alternatives point 4 declined S3 or S5 partly because of K4 (ii). Its other reason still holds: one class serves both a source (S5) and the output path (S3). The path-test classes of ADR-0080 decision 4 are a separate open entry. Leaving the row open is an acceptable outcome if the record gives its reasons and names what would let a later record place it, as ADR-0081 decision 2 did.

This is a design-level OD part. Under DRIVER §9 the executor may answer it with an ADR, accepted by a reviewer's Approve and followed by a notice on #5 with a 7-day window. No owner-only item is needed (#5 A/B items, OD-3, OD-25, C-6). If a step would need a new value of `condition` or `error.kind`, a new data-plane member, or an owner fact or value judgement, do not take that step. Leave the point open, say so in the record, or return BLOCKED (requirement unclear / owner-only decision, DRIVER §3).

**Why this item now.** STATE has no lock, current task or next task, and no task file is TODO or INTERRUPTED. There was no open PR on 2026-10-17 at `b772521`. PLAN P1-1 continues through OD-18 work. Its `profiler.collect` part waits on HQ-0025, and ADR-0078 slices 1 to 3 wait on HQ-0026 (T-0243); this task depends on neither. The other open follow-up, the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4), may need a new `error.kind`, a data-plane or owner question, so it is not taken here.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit.
  - §5 (lines 86-114): task format, the branch `claude/T-0254-<slug>`, the trailer `Task: T-0254`.
  - §8 and §9 (lines 135-148): HQ path, OD closure authority, the #5 notice with the driver tail `— posted by driver`.
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (document mode, steps 10-12) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: section "Record format".
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`, all of it, especially:
  - K4 (line 23), decision 4 (lines 47-51), decision 5 (lines 53-56);
  - alternatives point 4 (line 80), Consequences (lines 82-93), Boundaries.
- `ARCHITECTURE/decisions/ADR-0082-od18-correctness-check-compiler-run-error-time-limit.md`: Status (lines 3-13), decision 5 (lines 53-56), Boundaries (lines 99-107). Use it as the latest model of form and tone.
- `ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md`: M4 (line 23), decision 4 (lines 49-52).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 4 (from line 69), for S3, S5 and S6 and "What the operation observes decides the row".
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 and 5 (lines 64-84), for a raised error and a raised request to end.
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`: decision 5 (from line 53).
- `hilclaw/clang_build.py` at `0305d7b` or later, read only:
  - `build` (lines 183-327): the docstring paragraph on raised errors, the lines before `Popen` (243-260), and the `try` / `except BaseException` / `finally` (261-304);
  - `_checked_sources` (line 409) and `_resolve` (line 428).
- `PROCESS/tasks/T-0253-clang-build-keeps-non-oserror-over-failed-removal.md`: "The change, stated" and Result.
- The recording rules of the three registers. Follow them, not the wording of earlier task files or earlier entries:
  - `ARCHITECTURE/Requirements.md` line 84, "행 형식";
  - `ARCHITECTURE/OpenDecisionProposals.md` line 8, "기록 규칙";
  - `ARCHITECTURE/StandardScenarios.md` line 170, the first paragraph of §검사 결과;
  - the OD-18 row (line 109), the OD-18 section of OpenDecisionProposals (its 채택분 lines around line 294 and sub-question ⑱ around line 307), and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Entry check** (CLAUDE.md "세션 진입 점검"), before the first edit:
   - run `gh pr list` and read issues #4, #5, #7 and #8;
   - confirm that `ADR-0083` is free on `main` and on every remote branch (`git ls-remote`, `git log --all`). If not, take the next free number and use it everywhere this task says 0083;
   - check #5 for an owner comment, without the driver tail, on ADR-0081, ADR-0082, T-0253 or ⑱ (ma). If one bears on this choice, follow it, or return BLOCKED if it conflicts.
   - If an open PR touches any file in `touchesFiles`, return BLOCKED (open-PR conflict).
2. **ADR-0083** in `ARCHITECTURE/decisions/`, in the format of ADR-0001 "Record format", with the same Status conventions as ADR-0082:
   - the three kinds of content, the window, and the records it builds on with their windows;
   - "no member, no `condition` or `error.kind` value, no version";
   - "no earlier sentence edited".
   The slug may differ from the one in `touchesFiles` if the content warrants it.
   - **Context**: observations of `build` at `0305d7b` of what it states (docstring, raised classes), binding no code:
     - what now happens after an exception that is no `OSError` when the removal fails;
     - the full list of lines before `Popen` that can raise a plain `OSError`. Confirm the list from the code and do not copy K4 (i) blindly. For example, check whether `os.path.abspath` or `shutil.which` can raise one.
   - **Decision**, covering both questions of Why:
     - (1) whether the K4 (ii) entry of (ma) is now answered, and by which landed rules (ADR-0045 decisions 4 and 5), including that the note changes nothing or why it does;
     - (2) whether a plain `OSError` of `build` gets a row now, or stays open with the reason and what would let it be placed;
     - a section "How far (ma) is answered" that restates the open list as it stands after this record.
     - Every cited sentence is quoted with its source, and every reading of a cited row is labelled as this record's reading.
   - **Alternatives considered** (table), **Consequences** (including the sentences of ADR-0080, ADR-0081 and ADR-0082 that become less exact, without editing them), **Boundaries**, **References**.
   - No new value of `condition` or `error.kind` and no reserved kind. "Runtime acceptance items: none" unless the executor finds one; if so, name it and do not try to close it.
3. **Register edits**, each by the recording rule written in that file (see Required Reading). In short:
   - Requirements OD-18 row: one link to ADR-0083 after `**확정분**:` with a few words of topic, and `**잔여**:` rewritten in place only if what is open changes;
   - OpenDecisionProposals OD-18: one `**채택분**` line for ADR-0083, and ⑱'s end status and head word rewritten in place;
   - StandardScenarios: the "최근 재검사" line updated in place after re-checking the S-rows that cite OD-18 by the rules of that document. Add a history entry only if a verdict changes or a gap appears or closes.
   Do not restate the ADR's content in any register. Add no dated paragraph.
4. **No other file** is edited. No change to ADR-0001 to ADR-0082, `hilclaw/`, `tests/`, CI, UsageCases or any settings file.
5. **Document mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0254-<slug>`;
   - run the context-isolated reviewer cycle to Approve within 7 rounds;
   - rebase on `origin/main` and push straight to `main`, with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0254`;
   - delete the branch.
6. **§9 notice.** After landing, post a comment on #5 in English. It names ADR-0083 and the landed commit and states the 7-day objection window. Its last line is `— posted by driver`. Put the URL in Result.
7. Nothing is built or run except reading tools (`git`, `gh`, reading files). Start no `claude` process in any form (D16).
8. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files.

## Out of Scope

- The row of the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4), and any new `error.kind` or `condition` value.
- The classes the path tests raise on 3.11 to 3.13 (ADR-0080 decision 4) as their own entry, unless the answer to question 2 settles them as a direct consequence; the record says which.
- Any code change to `clang_build.build` or its callers, the `cpu_standin` operation of `correctness.check` (HQ-0026), ⑱ (ga), (da), (ra) and the size bound of (na), ⑰ (da), ⑲.

## Follow-ups

- (doc) The row of the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4). It may need a new `error.kind`, and so may be a data-plane or owner question (HQ).
- (code, if ADR-0083 names one) A change of `build` that would let a later record place a plain `OSError` before the start, for example telling the source tests apart from the output-path tests by class.

## Result
