---
id: T-0252
title: Write an ADR that places the time-limit branch of `CompilerRunError` (now told apart by `timed_out` and `log`) for `correctness.check`, or leaves it open with a reason, under OD-18 sub-question 18 part (ma)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-6, FR-10, OD-18]
dependsOn: [T-0250, T-0251]
touchesFiles: [ARCHITECTURE/decisions/ADR-0082-od18-correctness-check-compiler-run-error-time-limit.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0081 (T-0250, `d2a2c03`) decision 2 left the row of `CompilerRunError` for `correctness.check` open under OD-18 sub-question ⑱ (마). It named two things that would let a later record place it:
1. A code change of `clang_build.build` that tells the time-limit branch apart and keeps the output read so far. "Then a record can weigh S8 with its log for that branch."
2. A record for the other branch, where the call lost a compiler while it ran.

Task T-0251 (PR #159, `d3becf0`) made the first change. `CompilerRunError` now has the keyword-only members `timed_out` (`bool`) and `log` (`str | None`). `build` sets both from what `_communicate` observed, never from the exception chain. T-0251's Result records two choices:
- When the exit of `with process:` fails after a normal `communicate`, `log` is the full output and `timed_out` is false.
- On real Windows, `TimeoutExpired` carries no output, so a failed kill, or a failed read after the kill, leaves `log` as `None`.

T-0250's and T-0251's Follow-ups both list this record as the next item.

**What this task decides.** Write ADR-0082, which answers more of ⑱ (마) for `correctness.check` of the first case and of the mock:
- **The time-limit branch** (`timed_out is True`). Weigh S8 (`outcome` `"broken"`, `condition` `"build_time_limit"`; O1 is **the owner's**, as ADR-0060 quotes it) against leaving the branch open, and against any other candidate the executor finds. Then either place it, or leave it open with a stated reason and say what would let it be placed. The record must address at least:
  - that the end of the compiler is not always seen (a failed kill followed by the unbounded wait in the exit of `with process:`; a failure of that exit itself; ADR-0081 K2);
  - what `log is None` means for the log that ADR-0078 decision 2 keeps and for O2 (ADR-0081 decision 3). The docstring says `None` does not mean the compiler wrote nothing, and on Windows `log` is always `None` in this branch;
  - whether `removal_error` changes anything (ADR-0081 decision 2 said it did not, for the class as a whole);
  - whether the operation can apply the answer from what `build` states alone.
- **The other branch** (`timed_out is False`) stays open unless the executor finds that a record can place it with no new value of `error.kind`. ADR-0081 decision 2 says placing it "may need a new value of `error.kind`, which this record does not add". This record adds none either; if placing that branch needs one, it stays open. Re-state, for that branch, only what has changed since ADR-0081: `log` can now be non-`None` after a failed exit of `with process:` that follows a normal `communicate`.
- **What becomes less exact** among the sentences of ADR-0081 (for example K1's class docstring, "the class keeps no output", and decision 3's cost), listed in Consequences. Earlier records are not edited.

This is a design-level OD part. Under DRIVER §9 the driver's executor may close it with an ADR, accepted by a reviewer's Approve, followed by a notice on #5 with a 7-day window. It needs no owner-only item: O1 and O2 are already the owner's, and the record only applies them. If a step would need a new owner fact or a value judgement that only the owner can make (#5 A/B items, OD-3, OD-25, C-6), stop and return BLOCKED (`owner-only-decision`) with the question.

**Why this item now.** STATE has no lock, current task or next task, and no task file is TODO or INTERRUPTED. There was no open PR on 2026-10-17 at `14bbcbc`. PLAN P1-1 continues through OD-18 work:
- its `profiler.collect` part waits on HQ-0025;
- ADR-0078 slices 1 to 3 wait on HQ-0026 (T-0243).
This record depends on neither. The other open follow-up, telling apart the K4 (ii) removal error in code, is independent and is the candidate after this one.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, the 2h30 time limit), §5 (lines 86-114: task format, the branch name `claude/T-0252-<slug>`, the trailer `Task: T-0252`), §8 and §9 (lines 135-148: HQ path, the OD closure authority, the #5 notice with the driver tail).
- `CLAUDE.md`: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (document mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`, all of it (111 lines). It is the record this one builds on.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: Status (lines 3-15), Context O1 and O2 (lines 16-27), decisions 4 and 5 (lines 69-109).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2 (lines 32-38), decision 6 (lines 64-80), decision 7 (lines 81-91).
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`: decisions 1 and 3 (lines 28-45).
- `ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md`: decisions 2 and 4.
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md`: decisions 4 and 5 (lines 64-84).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decisions 4 and 5 (lines 73-114).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section.
- `hilclaw/clang_build.py` at `d3becf0` or later: `CompilerRunError` (lines 99-127), the `build` docstring and body (lines 183-322), `_Held` and `_communicate` (lines 354-380). Read the code only; build or run nothing.
- `PROCESS/tasks/T-0251-clang-build-run-error-time-limit-and-log.md`: Why ("The change, stated") and Result.
- The recording rules, which the edits below follow:
  - `ARCHITECTURE/Requirements.md` line 84 ("행 형식") and the OD-18 row (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md` line 8 ("기록 규칙"), the OD-18 채택분 lines (around line 293) and the ⑱ sub-question bullet (around line 306);
  - `ARCHITECTURE/StandardScenarios.md` §검사 결과 (line 168 on): its first paragraph (기록 규약) and the "최근 재검사" line.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md), before the first edit:
   - check `gh pr list` and issues #4, #5, #7 and #8;
   - confirm that 0082 is free on `main` and on every remote branch (`git ls-remote --heads origin`). If it is taken, use the next free number and record that in Result;
   - do not touch the branches of T-0210 or T-0231;
   - check #5 for any owner comment on ADR-0081, `CompilerRunError` or ⑱ (마). If an owner comment bears on this choice, follow it, or return BLOCKED if it conflicts.
2. **The record.** One new file `ARCHITECTURE/decisions/ADR-0082-<slug>.md` in the ADR-0001 record format, with a Status that says the following:
   - it was accepted under DRIVER §9;
   - which sentences are the owner's (quoted word for word), which are cited, and which are this record's own design;
   - which part of ⑱ (마) it answers and which it leaves open;
   - that it adds or changes no member of any file, result, request or line, no value of `condition` or `error.kind`, and no `schema_version`;
   - that it edits no earlier record;
   - which records it builds on and falls with;
   - that nothing was built or run.
   Context states the observations of the code at `d3becf0`. They bind no code, and they rest only on what `build` states (members and docstrings), not on the exception chain or on private `Popen` state. The Decision covers the points in Why. Alternatives considered weighs every candidate for the time-limit branch, including leaving it open. Consequences lists the earlier sentences that become less exact, and any code change the record makes possible. Boundaries keeps the other open entries of (마) (ADR-0081 decision 5, minus what this record answers), and the owner-only items.
3. **No invention.**
   - Use no new owner fact.
   - Add no value of `error.kind` or `condition`, and reserve none.
   - Where a choice rests on a reading of an owner sentence, say that it is this record's reading.
   - If the time-limit branch cannot be placed without a new owner fact or a data-plane change, leave it open, with the reason and with what would let it be placed. That is an allowed outcome; do not force a row.
4. **Registers**, edited only as their own recording rules say. Do not copy the wording of earlier task files or commits:
   - `Requirements.md`: follow "행 형식" (line 84) for the OD-18 row. Add one link to this ADR after `**확정분**:`, and rewrite `**잔여**:` in place only if what is open has changed. No restatement of the record and no dated chain. The status cell keeps its status word.
   - `OpenDecisionProposals.md`: follow "기록 규칙" (line 8). Add one `**채택분**` line for this ADR, and rewrite the end status of ⑱ and its bullet's head word in place. Keep the question's wording, and add no dated note.
   - `StandardScenarios.md`: re-check coverage by the document's rules for every S-row that cites OD-18 (CLAUDE.md "문서 커버리지 재검사"). Update the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed, as the 기록 규약 says.
5. **Document mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0252-<slug>`;
   - run the context-isolated reviewer cycle to Approve within 7 rounds;
   - rebase on `origin/main`, then push to `main` directly as one commit with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0252`;
   - delete the branch locally and on `origin`.
6. **§9 notice.** After landing, post a comment on #5 in English. It names ADR-0082 and the landed commit, and states the 7-day objection window. Its last line is `— posted by driver`. Put the URL in Result.
7. **D16.** Build, compile and run nothing, and start no `claude` process in any form. Reading the installed CPython `Lib/subprocess.py` as a file is allowed.
8. **Size** within DRIVER §5: ≤ 300 changed lines, ≤ 5 files.

## Out of Scope

- Any change to `hilclaw/`, tests, CI or settings files, and any edit of ADR-0001 to ADR-0081 or of UsageCases.
- Telling apart the K4 (ii) removal error, the removal error raised in place of an exception that is no `OSError` (a separate code task).
- The classes of the path tests of ADR-0080 decision 4, ⑱ (가), (다), (라) and the size bound of (나), ⑰ (다), and the timing build of `sim.run` / `board.run` (⑲).
- Writing the `cpu_standin` operation of `correctness.check` or the log keeper of ADR-0078 (HQ-0026).

## Follow-ups

- (code) Tell apart the K4 (ii) removal error, the removal error raised in place of an exception that is no `OSError` (ADR-0081 K4 (ii)). It currently turns a `KeyboardInterrupt` into an `OSError`.
- (doc) If this record leaves the branch that is not the time limit open, a record for it (ADR-0081 decision 2, second item).

## Result

DONE. Document mode: one commit `4d13e64` pushed to `main` (fast-forward from `96be15c`), trailers `Reviewed-by: reviewer agent (6 rounds, Approve)` and `Task: T-0252`; branch `claude/T-0252-adr-od18-compiler-run-error-time-limit` deleted on `origin` and locally. §9 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6228367785 (window until 2026-10-24).

- Session entry check (2026-10-17): no open PR; 0082 free on `main` and every remote branch; branches of T-0210 and T-0231 untouched; every #5 comment since 2026-10-16 carries the driver tail, so no owner comment bears on ADR-0081, `CompilerRunError` or ⑱ (마).
- ADR-0082: a `CompilerRunError` whose `timed_out` is true is S8, form (B) `"build_time_limit"` (O1 applied); its `log` is handed to the keeper when not `None`, and a `None` is handed over as nothing; `removal_error` changes nothing; the operation applies it from the class and `timed_out` alone. Labelled readings of the record: S8/O1 reach a build whose kill, read or close failed after the limit; S8's moment "the build ended" / "the build ended; `ok` false" is the end of the call of the build; ADR-0078 decision 2 does not forbid keeping a log whose compiler's end was not seen. The branch whose `timed_out` is false stays open (ADR-0081 decision 2), no new `error.kind`. Consequences list the less exact sentences of ADR-0081 (K1, K2, decisions 2, 3, 5, walk-through, alternatives, Consequences Code) and of ADR-0078 decisions 2 and 7.
- Registers: OD-18 row gets one link after `**확정분**:` (`**잔여**` unchanged, "(마)의 나머지" still holds); OpenDecisionProposals gets one `**채택분**` line and ⑱'s end status rewritten in place (head word "일부 답함" kept); StandardScenarios "최근 재검사" updated in place. Re-check of S0, S1-b, S2, S5, S6 (the S-rows citing OD-18): no verdict change, no gap, so no history entry.
- Review rounds: 1 to 5 Request changes (citation accuracy: error.kind vs data plane, ADR-0081 quotes per alternative, missing less-exact sentences, ADR-0056 S8 "`ok` false", K2 vs decision 3 attribution, ADR-0078 decision 7); round 6 Approve with one optional nit (split the source of "Status 0" per row in alternatives point 4), left as is.
- Note on the task's Why: it says that on Windows `log` is always `None` in the time-limit branch. The docstring at `d3becf0` says only a failed kill or a failed read after it leaves `None`; an error from closing the process after the post-kill read leaves the log set. The ADR follows the docstring (L3, L4).
- Size: 4 files, +119/-3. Nothing built or run; no `claude` process started. Read the installed CPython 3.14.4 `Lib/subprocess.py` `Popen.__exit__` only as a file; the ADR rests on `build`'s docstrings and cites ADR-0081 K2 for the rest.
- Follow-ups: (code) tell apart the K4 (ii) removal error (unchanged); (doc) a record for the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4), which may need a new `error.kind` and so may be a data-plane/owner question.
