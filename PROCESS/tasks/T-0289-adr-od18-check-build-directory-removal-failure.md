---
id: T-0289
title: Write ADR-0096 on what the `cpu_standin` operation of `correctness.check` does when removing its build directory fails (first part of OD-18 sub-question 17 part (da))
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-9, FR-10, NFR-2, NFR-4, OD-18, OD-14, OD-16]
dependsOn: [T-0285]
touchesFiles: [ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 150, files: 4}
hq: []
---
## Why

ADR-0056 decision 4 has the `cpu_standin` operation of `correctness.check` build the verification executable in a build directory of its own, made for that one call. The operation removes the directory before the call returns or raises. The same decision leaves one thing open: what the operation does when that removal fails, in whole or in part. It says neither that such a failure changes the answer of the check nor that it does not. That point is part (da) of OD-18 sub-question 17. Part (da) also holds three other points: a record of the source bytes and settings a check was built from, whether the executable is kept, and what clears a directory a dead process left behind.

`hilclaw/check_build.py` (T-0285, `c79f0ce`) now places every returned or raised build in a row of the accepted records. Its Follow-ups name the operation of `cpu_standin` as the next code. That operation is the code that removes the build directory, and no record says what it does when the removal fails. Answering this before the operation is written avoids an unrecorded choice in that code task.

The point is a design-level part of OD-18, so DRIVER §9 lets the executor close it with an ADR. Nothing in it is owner-only. It does not depend on an unresolved HQ:

- HQ-0018 (runtime acceptance of ADR-0056) asks whether a user can make, use and remove a directory at the place the code chooses. That is a fact about machines, not the rule for a failed removal.
- HQ-0026 (T-0243, the compiler's log keeper) is about a test of `hilclaw/layout.py`.

One owner decision bears on it and must be read. On 2026-10-15 the owner decided that the kernel's build and correctness run use an isolated environment, a container. OD-14 sub-question 1, part (da) of OD-18 sub-question 18 and OD-8 sub-question 33 (b) hold what that environment changes, and none of them is answered. The new record must therefore say which build directory it speaks of (the one ADR-0056 decision 4 places), and leave to those sub-questions what the container changes. It must not decide the container design.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0289` trailer;
  - §8 (lines 135-139): the driver tail of a #5 comment;
  - §9 (lines 141-147): ADR closure by the driver, the #5 notice and the 7-day window.
- `CLAUDE.md`, standing rules: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode), "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md`: decision 2 (lines 37-45, a process that outlives its limit, line 43), decision 4 (lines 73-94, the removal sentence at line 82), decision 5 (lines 95-114, line 112 on a dead tool-function process), Consequences (lines 185-192, the runtime acceptance item at line 189), Boundaries and the sub-question it registers (lines 193-206).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 4 (about lines 82-105, the S3 to S10 rows and the reasoning on backend kinds) and Boundaries (lines 160-166, part (da)).
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md`: decision 4 (lines 67-88) and decision 5 (lines 89-97). These fix how a backend kind is named, and what a kind outside the contract is answered with.
- `ARCHITECTURE/decisions/ADR-0049-od8-coder-call-isolation-means.md`: L9 (line 105) and the sub-question it raises (line 159). This is the coder scratch's analogue of a leftover.
- `ARCHITECTURE/decisions/ADR-0095-od18-cas-store-over-a-damaged-place.md`: a recent partial answer to a sub-question. Use its Status and "What stays open" as a model of shape, not of content.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- Code on `main`, read as files and not run:
  - `hilclaw/check_build.py` (160 lines): the module docstring, `read_build` and `place_error`;
  - `hilclaw/check_failure.py` (185 lines): the backend kinds of ADR-0060;
  - `hilclaw/scratch.py`: the module docstring (lines 1-58) and `_remove` (about lines 249-257). This shows how the coder scratch's removal retries and reports, and that a failed removal there is left to OD-8 sub-question 33 (b). Cite it as an observation; it binds nothing for the build directory.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - OD-14 (lines 200-210): the owner decision of 2026-10-15 (line 207) and its sub-question 1 (line 209);
  - OD-16 threat A (line 225);
  - OD-8 sub-question 33 (line 137);
  - OD-18 sub-questions 17 and 18 (lines 318-319), part (da) of each.
- `ARCHITECTURE/Requirements.md`: FR-9 (line 27), NFR-4 (line 47), NFR-2.
- Issue #5, the owner decision of 2026-10-15 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913) and the D6 comment (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506), via `gh issue view 5 --repo myungjoo/HIL-Claw --comments`.
- The recording rules of the three existing files this task edits. Read them there and apply them as written:
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84) and the OD-18 register row (line 109);
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet of the header (line 8), the OD-18 `채택분` lines (ending with the ADR-0095 line, line 306) and the sub-question 17 bullet (line 318);
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph under `# 검사 결과` (line 170) and the "최근 재검사" line (line 172).

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md "세션 진입 점검"). Do this before any edit:
   - Run `gh pr list`. If an open PR changes a file in `touchesFiles`, return BLOCKED (open-PR conflict risk). At planning time the only open PR was #179 (T-0284), which changes only `hilclaw/clang_build.py` and `tests/test_clang_build.py`.
   - Read issues #4, #5, #7 and #8 for anything on the build directory of `correctness.check`, the isolated build environment, or leftovers of a call that is newer than ADR-0060. Follow an owner comment that speaks to it. If one conflicts with this task, return BLOCKED.
   - The unlanded branches `claude/T-0210-*`, `claude/T-0231-*` and `claude/T-0264-*` hold ADR-0068, ADR-0074 and ADR-0088 and edit other bullets of OpenDecisionProposals. Do not reuse those numbers, and do not touch those bullets. Confirm that ADR-0096 is unused on `main` and on every remote branch. If it is taken, use the next free number, adjust the file name, and say so in `## Result`.
2. **New record** `ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md`, in the ADR-0001 "Record format".
   - **Status**: acceptance under DRIVER §9; which sentences are the owner's, which are cited, and which are the record's own; how far part (da) of sub-question 17 is answered; what of the data plane changes, if anything; the records it builds on; the #5 notice and the 7-day window.
   - **Scope.** The record speaks of the build directory as ADR-0056 decision 4 places it, for the operation of `cpu_standin`. It says what of its answer may change once the isolated environment of the owner decision of 2026-10-15 is designed, and leaves that to OD-14 sub-question 1, OD-18 sub-question 18 (da) and OD-8 sub-question 33 (b). It decides nothing of the container.
   - **Observation**, binding nothing. No code removes a build directory yet, and `hilclaw/check_build.py` does not speak of one. `hilclaw/scratch.py` retries a failed removal and only reports whether the scratch is gone. Nothing was established by running code.
   - **The answer, or the part left open with reasons**, for a removal that fails in whole or in part after each kind of outcome the operation can have: a report, a condition, a tool failure of a backend kind (ADR-0060), or a raised error placed by `check_build.place_error`. Weigh at least these alternatives and show each rejected one with its reason:
     - (a) the answer of the check stands as if the removal had succeeded, and the directory is left;
     - (b) the call answers a tool failure instead. A new backend kind is named only as ADR-0047 decision 5 allows: with the situation it means. Say what that does to a report or condition already established;
     - (c) the operation retries for a bounded time before (a) or (b). Say whether the bound is the record's or the code's;
     - (d) the part stays open, with reasons.

     The weighing must cover:
     - a process that outlived its limit and still writes into the directory (ADR-0056 decision 2);
     - what a survivor started by the attempt's own code means for FR-9 and OD-16 threat A;
     - what a leftover means for the next call's own directory (one per call, ADR-0056 decision 4);
     - that no member of the end line or of any data-plane file records a leftover today.
   - **What stays open** of part (da) of sub-question 17, named with what would let each point be placed, and not decided:
     - the record of the source bytes and settings;
     - keeping the executable;
     - what clears a directory a failed removal or a dead process left (with OD-8 sub-question 33 (b), OD-10 and OD-17);
     - whether anything records the finding.
   - **Consequences** name the code follow-up, if the record binds behaviour: in which module the operation of `cpu_standin` will do this, and whether `hilclaw/check_build.py` or `hilclaw/check_failure.py` would change (for example a new kind constant). Name it; write no code. List any sentence of an earlier record that becomes less exact, without editing it. No earlier ADR is edited.
3. **Register and proposal records.** Apply the recording rules written in each file (Required Reading). Do not model the edits on the wording of earlier task files.
   - `ARCHITECTURE/Requirements.md`, OD-18 row: under its "행 형식" rule, one link to ADR-0096 with a few words of topic. Rewrite the remaining-items text in place only where it no longer holds. Do not restate the record, and add no dated paragraph. The status word does not change.
   - `ARCHITECTURE/OpenDecisionProposals.md`, OD-18: under the header's "기록 규칙", one `채택분` line for ADR-0096 after the ADR-0095 line. Rewrite the status of the sub-question 17 bullet in place (its `→ 부분 답:` list and `남음:` text), only as far as the record changes it. If the record changes what sub-question 18 (da) or OD-8 sub-question 33 (b) asks, rewrite those words in place too. No dated note and no copy of the register text.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the file's own rules (CLAUDE.md "문서 커버리지 재검사"), at least for every scenario that cites OD-18, `correctness.check` or FR-9. Update the "최근 재검사" line in place as the first paragraph of `# 검사 결과` prescribes. Add a history entry only where that paragraph calls for one: a judgement changed, or a gap was found or closed.
4. **Do not invent.**
   - No member of `instance.json`, `build.json`, `artifacts.json`, the events log or any other data-plane file, and no layout change.
   - No setting value and no time-limit value of OD-14.
   - No container design.
   - No owner decision.
   - If the answer can only be completed by such a value or by an owner-only choice, stop and return BLOCKED with the question.

   Leaving the part open with stated reasons (alternative (d)) is a valid outcome. So is a partial answer that leaves the rest of part (da) open.
5. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0289-adr-od18-check-build-directory-removal-failure`.
   - Run the context-isolated reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Rebase on `origin/main` and push to `main` directly, with no PR. The commit carries `Reviewed-by: reviewer agent (N rounds, Approve)` and the trailer `Task: T-0289`.
   - After landing, post the DRIVER §9 notice on #5 with the §8 driver tail, and put its URL in `## Result`.
6. **Size**: four files. The new record should stay well under 140 lines. Each edit to an existing file is a few lines.
7. **No runtime prerequisites** (D16): start no `claude`, compiler, container or test run. Nothing in this task needs them.
8. **`## Result`** records:
   - the landed commit;
   - the review rounds and their findings;
   - the #5 notice URL;
   - the answer, or what was left open, and why;
   - the code follow-up, if any;
   - whether the ADR number changed.

## Out of Scope

- Code, tests and CI. In particular `hilclaw/check_build.py`, `hilclaw/check_failure.py`, `hilclaw/scratch.py`, `hilclaw/clang_build.py` (PR #179) and `hilclaw/local_run.py` (HQ-0027, HQ-0029).
- The other points of part (da) of sub-question 17, except to name them as open.
- The design of the build and run container (OD-14 sub-question 1), part (da) of sub-question 18, and OD-8 sub-question 33.
- The compiler's log file and its keeper (ADR-0078; T-0243, HQ-0026).
- Retention, GC and `gc_at` (C-3, #5 A-2, OD-25 — owner-only).
- Editing any earlier ADR, or any `PROCESS/` file other than this task's `## Result`.

## Follow-ups

- Code, later: the operation of `cpu_standin` for `correctness.check` applies this record together with `read_build` / `place_error`. It still waits for T-0243 / HQ-0026.
- Record any new open point the record registers in `## Result`.

## Result

- **Landed**: commit b53d3b9 on `main` (document mode, no PR), trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0289`. Branch deleted. Files: `ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md` (new), `ARCHITECTURE/Requirements.md` (OD-18 row), `ARCHITECTURE/OpenDecisionProposals.md`, `ARCHITECTURE/StandardScenarios.md` ("최근 재검사" line).
- **Answer**: one point of OD-18 sub-question 17 part (da), for the host build directory of ADR-0056 decision 4: when the removal fails, in whole or in part, the call keeps the answer the build and the run established; no `Exception` of the removal leaves the operation; a request to end during the removal still passes; leftovers stay where they are. Code rules: a fresh directory per call, retries bounded by a constant of the code, no symbolic link followed. Rejected: a new backend kind, raising the removal error as well, leaving the point open.
- **Left open**: the record of source bytes and settings (OD-6 ②, OD-14 ① (나)); keeping the executable (C-3, OD-10, OD-16); what clears a leftover (OD-8 ㉝ (나), OD-10, OD-17); whether anything records the finding (new, added to 17 (da)). The container case stays with OD-14 ① and ⑱ (da).
- **Review rounds**: 7, ending with Approve. Not addressed (an 8th round would exceed the A-13 limit): R7 Low — decision 2's heading "The next call is not touched" says more than its stated costs (suggested: "The next call never uses a leftover"); R7 Nits — the objection windows of ADR-0047 and ADR-0079 are not in Status; ADR-0004 and ADR-0078 are missing from References.
- **#5 notice (DRIVER §9)**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6244972784 — the 7-day objection window starts there.
- **Follow-ups**: a small document-mode touch-up for the R7 items above; the code task for the `cpu_standin` operation of `correctness.check` applies ADR-0096 decisions 2 and 3 (still waits for T-0243 / HQ-0026). No new HQ. No `claude` was started (D16).
