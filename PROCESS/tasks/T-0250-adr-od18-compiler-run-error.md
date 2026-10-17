---
id: T-0250
title: Write an ADR that places `CompilerRunError` (T-0249) for `correctness.check`, or leaves it open with a reason, under OD-18 sub-question 18 part (ma)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-6, FR-10, OD-18]
dependsOn: [T-0248, T-0249]
touchesFiles: [ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0080 (T-0248, `afb9f2e`) decision 4 left this open under OD-18 ⑱ (마): "an `OSError` raised after the compiler process was created and before it ended, and the removal error passed on in its place (M3), which by class cannot be told apart from an error before the start". Its alternatives table declined to place that error in S6 or S9 only because "It comes in the same classes as errors before the start (M3, M4) … telling it apart is a code change."

T-0249 (PR #158, `065113b`) made that code change. In `hilclaw/clang_build.py` at `065113b`:
- `build` wraps the `_communicate(process, timeout_s)` call. Any `OSError` that leaves it is raised as the new `CompilerRunError`, an `OSError` subclass with no `result` and a `removal_error` (the error of removing the temporary file afterwards, or `None`). The removal error no longer replaces it.
- `CompilerRunError` and `CompilerNotStartedError` share the private base `_UnendedBuildError`. Neither is a subclass of the other or of the three after-the-end classes.
- `_communicate` kills the process on any exception and waits for it on the `with process:` exit. Read it yourself. One fact matters for the row: in the timeout branch, an `OSError` from `process.kill()` or from the follow-up `communicate`/`wait` also leaves `_communicate`. So a `CompilerRunError` can also come from a build that passed its time limit.
- The output read before the failure is not kept ("the output read so far is not kept", class docstring). So no log reaches the operation.

Under the recording rules of the registers, only an ADR changes them. So placing the new class is a design-level ADR under DRIVER §9. T-0249's Follow-ups name it as the next candidate.

**Why this item now.** STATE has no lock, no current or next task, no TODO or INTERRUPTED task file, and no open PR (checked 2026-10-17 at `791ca37`). PLAN P1-1 continues through OD-18 work. Its `profiler.collect` part waits on HQ-0025, and ADR-0078 slices 1 to 3 wait on HQ-0026 (T-0243). This record depends on neither and decides neither question. The latest owner-facing comments on #5 are driver notices; none objects to ADR-0079 or ADR-0080 (checked).

The unlanded branches of T-0210 (ADR-0068) and T-0231 (ADR-0074) also edit row OD-18 and the "최근 재검사" line. They are branches, not open PRs (DRIVER §3-3), and this task touches no file on them. 0081 is the next free ADR number on `main` and on every remote branch (checked). If it is taken by execution time, take the next free number and rename the file and `touchesFiles` to match.

**What the record must settle.** The executor weighs the alternatives. The reviewer checks them against ADR-0060 decision 4, ADR-0078 decision 2, ADR-0079 decision 4 and ADR-0080, and against the code at `065113b` or later.
1. **The row of `CompilerRunError`.** Say what the call answers, with or without a `removal_error`, or leave it open under (마) with a reason. Weigh at least:
   - (a) S6, `compiler_unavailable`. Its wording is "The compiler is not found, or its process cannot be started", at "the start of the build". But here the process was created.
   - (b) S9, `build_output_missing`. Its moment is "the build ended", but the status is not known.
   - (c) answering by the build the error interrupted, for example S8 after a timeout's kill failed. The class does not tell the timeout branch apart, and S7 and S8 are **results** that ADR-0078 decision 2 gives a log. Say whether that can be applied at all.
   - (d) `operation_answer_invalid`, or another existing kind.
   - (e) leave it open, naming what would have to change.
   Each candidate's weighing states what the operation can observe from the class alone. Use only the six backend kinds of ADR-0060 decision 4, `operation_answer_invalid`, or "open".
2. **The log.** No log reaches the operation (no `result`). ADR-0078 decision 2 keeps "The log of every build whose compiler process was started and has ended". Say how the chosen answer stands against that sentence, and state the cost, in the manner of ADR-0080 decision 2's cost paragraph for M5. Cite ADR-0078; do not restate it. Say what happens to the `removal_error`.
3. **What a plain `OSError` class from `build` now means.** At `065113b`, an `OSError` that `build` raises and that is none of its own subclasses can only come from before the start: the path tests (ADR-0080 M4) or `_resolve`. Verify this against the code and give it as an observation at the named commit. Say what that answers of the entries ADR-0080 decision 4 keeps open, and what it does not. The other classes the path tests raise on 3.11 to 3.13 still lie before the start, but their row is not given by this fact.
4. **What stays open under (마)**, named in the record's scope decision and in Boundaries. Answer only what the code now tells apart.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0250-<slug>`, the trailer `Task: T-0250`, size cap); §8 (lines 135-139: the driver tail of #5 comments) and §9 (lines 141-148: the ADR route, the notice, the 7-day window).
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, document mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md`, the whole file (99 lines). This record extends it; use it as the model for the Status wording and the shape of the record. Do not edit it.
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`: decisions 3 to 5 (lines 39-57) and Consequences (lines 82-88).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 2 (lines 38-45), decision 4 (lines 69-104; rows S3 to S10 at lines 90-97; the paragraph "What the functions on `main` report" at line 102), decision 5 (lines 105-109).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2 (lines 32-38), decision 6 (lines 64-80), decision 7 (lines 81-91).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` decision 4 (what `operation_answer_invalid` says).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` "Record format" (line 146 to the end).
- `hilclaw/clang_build.py` at `065113b` or later: `_UnendedBuildError`, `CompilerNotStartedError`, `CompilerRunError` (lines 79-110), `build` (lines 166-300) and `_communicate` (lines 332-347). Facts about it go into the record as observations at a named commit.
- `PROCESS/tasks/T-0249-clang-build-tells-run-errors-apart.md`: Why, Follow-ups and Result (the kill-branch test and its `__cause__`/`__context__`).
- `PROCESS/tasks/T-0248-adr-od18-build-errors-now-told-apart.md`: Result, the two round-7 wording items.
- The recording rules, read in full before editing:
  - `ARCHITECTURE/Requirements.md`: the paragraph "행 형식" (line 84) and row OD-18 (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the header bullet "기록 규칙" (line 8), the OD-18 채택분 lines (lines 290-292) and the sub-question ⑱ bullet (line 305);
  - `ARCHITECTURE/StandardScenarios.md` §검사 결과: the first paragraph (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check.** Before the first edit, run `gh pr list` and read issues #4, #5, #7 and #8. State this in the Result. Report any open PR that touches row OD-18, the OD-18 section or the re-check line. If #5 carries an owner comment on ADR-0079, ADR-0080, S6, S9 or ⑱ (마), stop and report it. That includes an objection inside either record's window.
2. **One new record**, `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md` (number per Why), in the record format of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References.
   - Status says that it was accepted under DRIVER §9 by the reviewer's approval and is not confirmed by the owner.
   - Status says which part of ⑱ (마) it answers and what it leaves open.
   - Status says that it changes no member, `condition` value, `error.kind` value, `schema_version` or layout version.
   - Status says that it builds on ADR-0060, ADR-0078, ADR-0079 and ADR-0080 and falls with any of them, and that the owner has a 7-day objection window.
   - Like ADR-0080 Status, it keeps owner sentences, cited sentences and its own design apart.
3. **Points 1 to 4 of Why are settled** for `correctness.check` of the first case and of the mock.
   - Each choice is weighed against at least one alternative in "Alternatives considered". For point 1, weigh at least candidates (a) to (e).
   - Facts about `hilclaw/clang_build.py` are observations at a named commit (`065113b` or later). The record binds no code; names and modules stay the code task's.
   - If the chosen answer is "open", the record says which code or record change would let it be placed. It does not write that change.
4. **Earlier records are not edited.** The record lists the landed sentences it makes less exact, without editing them. At least: ADR-0080 M3, decision 4's open list, the walk-through row "Reading the pipe fails while the compiler runs", and the last row of its alternatives table. Also list ADR-0078 decision 2 where the answer touches it.
5. **Limits.** The record adds:
   - no value of `condition`;
   - no value of `error.kind` and no reserved kind;
   - no member of any file, result, request or line;
   - no `schema_version` or layout version.
   If no answer fits without one of these additions, and "open with a reason" does not fit either, stop and return BLOCKED (`requirement-unclear`) with the question.
6. **Register edits.** Apply each file's own recording rule as it is written there. Do not model these edits on how earlier tasks phrased them.
   - `ARCHITECTURE/Requirements.md` row OD-18: per "행 형식". Add one link for the new ADR. Rewrite the 잔여 part in place only if it no longer names what is open.
   - `ARCHITECTURE/OpenDecisionProposals.md` OD-18 section: per "기록 규칙". Add one adopted-record line for the new ADR, without restating its content. Rewrite the end status of the ⑱ bullet in place so that it names what is open under (마) now. Do not edit the wording of the question.
   - Optional: drop the "(S9)" from the ADR-0080 채택분 line, if the reviewer agrees that "기록 규칙" forbids it as restated content. This is the first round-7 item of T-0248. Apply the second item only if the new record restates the paragraph it concerns.
   - Add no dated paragraph to any register. Edit no other `ARCHITECTURE/` file and no earlier ADR.
7. **Coverage re-check.** Re-check per CLAUDE.md "문서 커버리지 재검사", using the rule in the first paragraph of StandardScenarios §검사 결과, and update that section as the rule says. Change an S-row note only if it now says something untrue.
8. **D16.** No step starts `claude` in any form, builds anything or runs a compiler. Facts come from the code and the records.
9. **Document mode** per CLAUDE.md A-13:
   - Work on branch `claude/T-0250-<slug>`.
   - Run the reviewer cycle (dev-item-address steps 10-12) to Approve within the 7-round cap.
   - Land as one commit. Rebase on `origin/main`, squash the branch into one commit and push it directly to `main`. The commit carries `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0250`.
10. **§9 notice on #5 after landing.** It gives:
    - the record's number and title;
    - the part of ⑱ (마) it answers and what stays open;
    - the landing commit link;
    - the 7-day window;
    - the driver tail of DRIVER §8.
11. Size within the DRIVER §5 caps (≤ 300 changed lines, ≤ 5 files).

## Out of Scope

- Any code, test or CI change, including `hilclaw/clang_build.py` (for example keeping the output read before the failure, or telling the timeout branch apart), and the operation of `cpu_standin`. Such a change is a later code task, named in Follow-ups if the record asks for it.
- The path tests before the start (ADR-0080 M4) beyond point 3 of Why; the case inside `Popen` construction (ADR-0080 M5).
- ADR-0078 slices 1 to 3 (T-0243, BLOCKED on HQ-0026), anything of HQ-0025, and the branches of T-0210 and T-0231.
- `local_run.run`, the run tools' timing build (⑲), ⑱ (가), (다), (라), the size bound of (나), and ⑰ (다).

## Follow-ups

- When the operation of `cpu_standin` for `correctness.check` is written, its code applies ADR-0079, ADR-0080 and this record.
- The rest of ⑱ (마), when code tells it apart or a record places it.

## Result

- Landed on `main` as `d2a2c03` (document mode, one squashed commit with `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0250`). The branch `claude/T-0250-adr-od18-compiler-run-error` was deleted locally and on `origin`.
- Session entry check, before the first edit:
  - `gh pr list` showed no open PR.
  - Issues #4 and #7 have had no activity since 2026-10-01 and 2026-09-07. #8 is closed.
  - On #5, every comment since 2026-10-16 carries the driver tail. No owner comment speaks to ADR-0079, ADR-0080, S6, S9 or ⑱ (마).
  - 0081 was free on `main` and on every remote branch. The branches of T-0210 and T-0231 were not touched.
- Record: `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`. Observations at `065113b` are K1 to K4.
  - Decision 2: the row of `CompilerRunError` stays open (candidate (e)); (a), (b), (c), (d) and (d′) were weighed. The reason: from what `build` states, the class does not tell the time-limit branch (S8, O1) from a compiler lost while it ran, and it carries no log. The exception chain tells this in part (`TimeoutExpired` as `__context__`; on POSIX its `output`), but no answer rests on it. To place the row needs (i) a code change that tells the time-limit branch apart and keeps the output, and (ii) a record for the other branch. Cost: until then the landed `operation_answer_invalid` answers an S8 call against O1. `removal_error` changes nothing.
  - Decision 3: the log is lost for every `CompilerRunError` whose compiler ended by itself or was killed for its time limit. That is against ADR-0078 decision 2 and, for S8, against O2.
  - Decision 4: the task's Why point 3 was corrected as an observation. A plain `OSError` of `build` comes from before `Popen`, **or** is the removal error re-raised in place of a non-`OSError` exception (the `finally`). This case is now named as open.
- Registers:
  - Requirements: one 확정분 link in row OD-18; 잔여 unchanged.
  - OpenDecisionProposals: one 채택분 line; ⑱ end status rewritten. The round-7 item of T-0248 was applied: "(S9)" was dropped from the ADR-0080 line, and the reviewer agreed. The second item was not applied, because the record does not restate that paragraph.
  - StandardScenarios: the "최근 재검사" line covers S0, S1-b, S2, S5 and S6. No verdict changed, no gap was found, and no S-row note changed.
  - Size: 4 files, +116/−4.
- Review: 7 rounds.
  - Round 1, Request changes: the log reach of the non-timeout branch, "may need" a new kind, register restatement.
  - Round 2, Request changes: the O1 and O2 costs of the chosen "open".
  - Round 3, Approve with nits.
  - Round 4, Request changes: the exception chain.
  - Round 5, Approve with nits.
  - Round 6, Approve with one nit.
  - Round 7, Approve with two info items and one nit, not applied because the cap was reached. The info items: the "end not seen" wording for the `with` exit after a normal communicate ("may not be seen"), and that K4 (ii) turns a `KeyboardInterrupt` into an `OSError` that the landed rules answer `operation_answer_invalid`.
- §9 notice on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6227726414 (7-day window).
- D16: nothing was built or run, and no `claude` was started. One reviewer round read the CPython `subprocess` source by importing it into Python (read only).
- Follow-ups:
  - (code) Tell the time-limit branch of `CompilerRunError` apart and keep the output read so far (ADR-0081 decision 2).
  - (code) Tell apart the removal error re-raised in place of a non-`OSError` exception (K4 (ii)). Note that it turns a `KeyboardInterrupt` into an `OSError`.
  - (doc) A record that places `CompilerRunError` after the first code change.
