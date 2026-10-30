---
id: T-0327
title: Record an ADR on where the `cpu_standin` operations' time limits of the build and of the process come from and what their first values are, for the first case (OD-14, the call-level part of the timeout hierarchy)
phase: P1
status: DONE
commitMode: doc
coversReq: [NFR-4, FR-10, FR-9, OD-14, OD-18, C-7]
dependsOn: [T-0326]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 240, files: 4}
hq: []
---
## Why

PLAN P1-1 is open. Its D18 completion criterion needs `sim.run`, `board.run` and `correctness.check` to work on `cpu_standin`, and P2-5, the near goal, is a run on `cpu_standin` × GEMM. No `cpu_standin` operation exists yet for any of the three tools.

The records name what that operation still lacks:
- ADR-0060 decision 3 makes every setting of the `correctness.check` operation "the backend's own": the time limit of the build and the time limit of the process among them. It leaves their source and values open "with OD-14 and its hierarchy". ADR-0061 decision 3 makes the same cut for the timing build and the timing run of `sim.run` and `board.run`.
- ADR-0116 (T-0325) answered the flags, trailing flags and environment, and T-0326 put them in `hilclaw/standin_settings.py`. ADR-0116 Consequences still list "the two time limits (OD-14)" among the stops of the operations.
- ADR-0017 decision 9 and ADR-0009 decision 9 give the process time limits "the caller, no default" and send "values and hierarchy" to OD-14.

This task closes the call-level time limits of those operations for the first case with one ADR: four values in all, a build and a process time limit for the verification side and for the timing side. It does not close the rest of OD-14.

OD-14 is a design-level OD, so the DRIVER §9 path applies: an ADR, reviewer Approve, and the owner notice. It is not owner-only. The owner-only items of §9 are the #5 A and B items, C-6, OD-25 and OD-3. The owner decision of 2026-10-15 on OD-14 (container as isolation means, changes only after approval) fixes the means and the approval rule, not time limits. No open HQ is needed:
- HQ-0021 and HQ-0026 block other parts of the operations;
- HQ-0034 (OpenMP) does not touch the limits;
- HQ-0033 and the other runtime-acceptance notices block nothing.

D18: this is not a PLAN checklist item of its own. It is a stop of the `cpu_standin` operations that P1-1's completion criterion and P2-5 need, so the priority rule does not set it aside.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0327` trailer, size cap;
  - §9 (lines 142-149): OD closure by ADR, reviewer Approve and owner notice on #5.
- `CLAUDE.md`, these rules:
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "문서 커버리지 재검사";
  - "개발 드라이버와 런타임의 구분";
  - "브랜치·merge 절차" (document mode, `Reviewed-by` trailer).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- The record format: `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md`, the whole file (150 lines). It is the closest earlier record: same backend, same runs, same "source and first values" question. Its decision 1 (scope, host or container) and decision 2 (source weighed against tests) are the pattern to follow or depart from with reasons.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`:
  - decision 3 and its settings table (lines 46-68), including cost (i) at line 55: an operation is handed the output path, not the data root, so a limit stated in a file of the run has no way to it;
  - decision 4, rows S4 and S8 (lines 69-104): a time limit that is no positive finite number, or one the platform cannot wait for, is `settings_refused`; a build past its limit is a broken result `build_time_limit`;
  - Consequences (lines 154-161) and Boundaries (lines 162-176), with the text of ⑱ (가).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`, decisions 9 and 10 (lines 86-108). The process limit bounds the process over all its draws. Line 106 gives the cost per draw and the largest output of the first instances (gate/up at M = 512).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`, decisions 7, 9 and 10 (lines 65-117). This covers the repeat loop up to `n_max` and the untimed cost inside the time limit (line 115).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`, decisions 4 and 8 (lines 40-47, 72-90): number of repeats; `n_max` per instance, default 10.
- `ARCHITECTURE/decisions/ADR-0046-od18-correctness-check-draws.md`, Status line 9 and decisions 2-3 (lines 35-96). Where `draws` comes from. Which number an instance uses is not decided.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`:
  - decision 3 (lines 49-59);
  - decision 7 (lines 86-97): the order of the broken conditions, the build and the run past their time limits.
- `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md`:
  - decision 3, line 48: time limits differ as each run needs and are outside the sameness rule;
  - Alternatives row 3 (line 105).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`, Limits (lines 120-128): "No time limit and no size limit of a call are decided"; the MCP idle window.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - header "기록 규칙" (line 8);
  - §OD-14 (lines 216-225): the proposal "계층 타임아웃 (커널 워치독 < 호출 < 서브프로세스 SIGKILL < 라운드 < run)" and sub-question ①;
  - OD-18 sub-question ③ (line 329): the limits Claude Code applies per exposure form. Bash foreground 10 min by default; a stdio MCP call aborted after 30 min with neither response nor progress notification;
  - OD-18 sub-question ⑱ (line 341), part (가).
- `ARCHITECTURE/Requirements.md`:
  - NFR-4 (line 47);
  - the register's "행 형식" (line 84);
  - the OD-14 row (line 105) and the OD-18 row (line 109).
- `ARCHITECTURE/decisions/ADR-0032-od8-instance-record-round-budget.md` and `ARCHITECTURE/decisions/ADR-0033-od8-instance-record-wall-clock-budget.md`, decisions 2-5 of each. These are the round and run levels of the hierarchy that already have members. Read them so the ADR can state the relation without deciding them.
- `ARCHITECTURE/StandardScenarios.md`, §검사 결과, the first paragraph (lines 168-172).
- Code, as observations only:
  - `hilclaw/clang_build.py`, `build` docstring (lines 196-270) and `_check_timeout` (from line 520);
  - `hilclaw/local_run.py`, `run` docstring (lines 79-150);
  - `hilclaw/standin_settings.py` (the one source of ADR-0116; "The set holds no compiler and no time limit (OD-14)").

## Acceptance Criteria

1. **Session entry check.** Run `gh pr list`, and read issues #4, #5, #7 and #8 for anything on OD-14 or on time limits posted after 2026-10-19T03:34Z.
   - Draft PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files. It does not touch this task's files.
   - If an open PR edits the OD-14 or OD-18 row, or §OD-14 or §OD-18 of the proposals, stop and report it.
   - Check with `git ls-tree` on `origin/main` and every remote branch that no `ADR-0117` exists. If the number is taken, take the next free one, rename the file, update touchesFiles and say so in Result.
2. **The ADR** `ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md`, in the ADR-0001 "Record format", with Status, Context, Decision, Walk-through, Limits, Alternatives considered, Consequences, Boundaries and References. It decides, for the runs of ADR-0116 decision 1 (`cpu_standin`, the first case, the local configuration; the mock out of scope):
   - **Scope.** The four time limits:
     - the build of the verification executable and its process (`correctness.check`);
     - the timing build and the timing run (`sim.run`, `board.run`).
     Each value must hold whether the build and run happen on the host or in the container of the owner decision of 2026-10-15. If one cannot hold in both, leave it open, as ADR-0116 decision 1 does.
   - **The source.** Weigh at least three alternatives against named tests: fixed constants of the package (the ADR-0116 pattern); a value derived in the operation from what it is handed (for example the shape, `draws` or `n_max`); a value read from a file of the run (for example a member of `instance.json` or the wall-clock budget of ADR-0033).
     - The tests must include NFR-7 ③, C-7, O4 item 2, and the stop of ADR-0060 cost (i) and decision 3: an operation reads no setting from a file of the run.
     - A choice that reads the run's files reopens ADR-0060 decision 3, and one that needs a new member is a data-plane schema change (CLAUDE.md A-13). Do not take either. If no other choice can be defended, stop and return BLOCKED (`requirement-unclear`) with the question.
   - **The values.** A value, or a stated rule from handed inputs to a value, for each of the four limits, with the reasons and the stated worst case it is meant to cover. Ground each in the records:
     - the largest operands of the first instances (ADR-0017 line 106);
     - per-draw cost (ADR-0017) and per-repeat cost with `n_max` (ADR-0007, ADR-0009);
     - compiler start-up.
     Where a figure cannot be derived from the records, mark it as this record's estimate. Do not present it as measured.
   - **The relation to the call limits Claude Code applies** (OD-18 ③). State whether the longest call these limits allow fits inside the MCP idle window and the Bash default limit. Take each of the two builds and the process of one call into account. If it does not fit, say what follows.
     - Do **not** decide progress notifications, the idle window or a call's size limit; OD-18 ③ stays open.
     - If no defensible value fits without deciding them, stop and return BLOCKED with the question.
   - **The relation to the rest of the hierarchy.** Say which parts of the OD-14 proposal "계층 타임아웃" this record adopts for these calls and which stay open:
     - the kernel watchdog;
     - SIGKILL after the limit, as `clang_build` and `local_run` already do (observation);
     - round and run, which have the budget members of ADR-0032 and ADR-0033.
     Say how the four limits stand to those budgets, without deciding the budgets.
   - **What a call answers when a limit is reached.** Cite the existing answers and add no new one: `build_time_limit` (ADR-0060 decision 4), the process time-limit condition (ADR-0021, ADR-0061 decision 7), and S4 `settings_refused` for a value the functions refuse. If a new `condition` value, kind or member seems needed, it is a data-plane schema change: stop and return BLOCKED.
   - **Limits, Consequences and Boundaries:**
     - **Limits:** nothing was built or run.
     - **Consequences, the code slice:** for example the constants or rule beside `hilclaw/standin_settings.py`. Names and modules are the code task's, and this record binds no code.
     - **Consequences, "not edited and now less exact":** ADR-0060, ADR-0061, ADR-0017 decision 9, ADR-0009 decision 9, ADR-0116 Consequences and Boundaries, and the module docstring of `hilclaw/standin_settings.py`. Find the list by grep, and name the grep terms.
     - **Consequences, runtime acceptance items (D16):** that the values suffice on each C-7 system and in the container, which only a runtime machine can show.
     - **Boundaries:** the container design (OD-14 ①); resource caps, board health and blacklist; round and run limits; OD-18 ③; ⑱ (가).
3. **No earlier record is edited.** List the less-exact sentences in the ADR's Consequences instead. If the ADR answers part of an OD-18 sub-question (for example ⑱ (가) for time limits), say so in its Status.
4. **Register and proposals.** Follow the recording rules written in the files themselves, and do not copy wording from earlier task files:
   - `Requirements.md`: follow its "행 형식" (line 84). In the OD-14 row, add one `**확정분**:` link for ADR-0117 with a few words of topic, and rewrite `**잔여**:` in place so the timeout hierarchy reads as answered only for the call-level limits of the first case. Keep the status word unless the whole OD is closed (it is not). Edit the OD-18 row only if the ADR answers part of an OD-18 sub-question, and then in the same way.
   - `OpenDecisionProposals.md`: follow its "기록 규칙" (line 8). In §OD-14, add one `- **채택분** [ADR-0117](…) — …` line. Do not restate the record. If the ADR answers part of a sub-question, rewrite that sub-question's state marker in place (`→ 부분 답: … 남음: …`). Add no dated paragraph. If the ADR registers a new sub-question, add it under §OD-14 as a numbered sub-question in the existing style.
5. **Coverage recheck.** Following CLAUDE.md "문서 커버리지 재검사" and the first paragraph of StandardScenarios §검사 결과:
   - recheck the scenarios that involve builds, verification and timing (at least S0, S1, S7);
   - update the "최근 재검사" line in place;
   - add a history entry only if a verdict changed or a gap was found or closed.
6. **D16.** No `claude` program is started, and no compiler, kernel or container is run for this task. No board, accelerator or API key is required. Do not claim the runtime acceptance items as checked.
7. **Scope and size.**
   - `git diff --stat origin/main` lists only the touchesFiles (plus this task file's Result if the driver asks for it).
   - About 300 changed lines or fewer.
   - No edit under `hilclaw/`, `tests/`, CI, `.claude/`, any settings file, UsageCases or the `HIL-Claw-data` repository. No new external dependency.
8. **Landing.** Document mode under CLAUDE.md A-13:
   - work on branch `claude/T-0327-adr-od14-cpu-standin-time-limits`;
   - run the context-isolated reviewer cycle (dev-code-review, at most 7 rounds) to Approve;
   - rebase on `origin/main` and push to main with the `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0327` trailers;
   - post the DRIVER §9 owner notice on #5 with the driver footer (§8), and record its URL in Result.

## Out of Scope

- The code slice (the constants or rule in the package) and the `cpu_standin` operations themselves. The operations still wait on the compiler installation (OD-14 ①), HQ-0021 (T-0210) and HQ-0026 (T-0243).
- The container design, resource caps, board health, recovery and blacklist (OD-14 ① and the rest of OD-14).
- Round and run time limits or budgets (OD-2, OD-19, ADR-0032, ADR-0033); progress notifications and call size limits (OD-18 ③).
- Settings reaching an operation from a file of the run (⑱ (가)), `task.build` (OD-6 ②), OpenMP (HQ-0034).
- Any edit to an earlier ADR, to `hilclaw/standin_settings.py` or to any file of PR #186.

## Follow-ups

- Next candidate: the code slice of ADR-0117, which adds the four time limits (or their rule) to the one `cpu_standin` settings source, with tests.

## Result

- **DONE.** Landed on `main` as `a4b07b5` (document mode, one commit, trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0327`). The task branch was deleted on origin and locally.
- **Session entry check (03:38Z).** Open PRs: only #186 (T-0324), which touches none of this task's files. No comment on #4, #5, #7 or #8 after 03:34Z touches OD-14 or time limits. `ADR-0117` was free on `origin/main` and on every remote branch, so no renumbering.
- **Files.** `ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md` (new), `Requirements.md` (OD-14 row: one `**확정분**` link, `**잔여**` rewritten in place; OD-18 row: one link for the time-limit part of ⑲ (라)), `OpenDecisionProposals.md` (§OD-14: one `채택분` line; the ⑲ state marker rewritten in place) and `StandardScenarios.md` ("최근 재검사" line only). In all: 4 files, +148/−4.
- **Decision.** For processes the limits come from one package rule applied to handed values (shape, `draws`, `n_max`). For builds they are fixed constants. Options (c), file of the run, and (d), config or environment, were rejected. The values:
  - each build: 60 s;
  - each process: `min(1500, 10 + c·(1 + 2mkn/2e8))` s, where `c = draws` for the verification run and `c = n_max + 1` for the timing run.
  - **Fit:** the limits allow at most 1560 s, which fits the MCP idle window with 240 s to spare; checks above about 80 draws at the largest shape may not fit. The Bash default does not hold every call; what follows is stated, and OD-18 ③ is left open.
- **OD-18 ⑲ (라).** The ADR also answers its time-limit part, because ADR-0061 decision 3 puts the time limits under ⑲ (라). ⑱ is not answered.
- **Coverage recheck.** S0, S1, S7, S2 and S9: no verdict change and no gap, so no history entry.
- **D16.** Nothing was built or run, and no `claude` process was started. The runtime acceptance items are stated in the ADR's Consequences and not claimed as checked.
- **Review rounds (7).**
  - R1: observation and quote fixes (merge_guard's 60 s, local_run's SIGKILL, generation vs. regeneration, the 4e8 figure, the wording of "met"), plus the less-exact list.
  - R2: kill in a container, the build log kept for a killed compiler, a table cell, exact quotes of the §OD-14 sentences.
  - R3: ADR-0043 classification, a quote ellipsis.
  - R4: one blocking item. The MCP fit claim wrongly bounded draws at 17; it now says the tool function's own work grows with draws.
  - R5: the ⑲ (라) grep term, the `n_max` replay, References.
  - R6: one blocking item. An exhaustive reclassification of the grep hits.
  - R7: Approve with two nits.
- **Open nits, left unfixed** (fixing them after the round-7 Approve would have needed an eighth round):
  - The "every other hit stays exact" rule in Consequences does not name ADR-0116 decision 7 (which states what ADR-0116 answers) or ADR-0116's own less-exact bullet. Both stay exact.
  - Boundaries says "sub-questions ㉙, ㉚" without naming their OD (OD-8).
- **Owner notice (DRIVER §9):** https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6259729110
- **Follow-ups.**
  - The code slice of ADR-0117: the constants and the rule beside `hilclaw/standin_settings.py`, with tests.
  - Optionally, a doc touch-up for the two nits (D18: probably a hold line, as it changes no behaviour).

