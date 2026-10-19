---
id: T-0337
title: Write ADR-0122 — what the turn loop of a first-case run does where its step 1 is still open (after a failed turn, after a turn that leaves the run as it found it, and in the states ADR-0121 decision 5 leaves to the caller), so that its command-line entry can be built (part of OD-17 and OD-19, for the runs of ADR-0120 decision 1)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-1, FR-3, NFR-1, NFR-5, OD-17, OD-19, OD-8, S0, S1, S2]
dependsOn: [T-0330, T-0335, T-0336]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). ADR-0118 Consequences (1) names "the turn loop of decision 3 and its command-line entry" as a P2-1 slice, so this task is inside the checklist and the D18 priority rule does not apply. The P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) needs something that starts the turn loop on a run and stops it.

The layer-2 parts exist: `hilclaw.turn_loop.run` (T-0330), `hilclaw.turn_definition.put` (T-0331) and `hilclaw.further_turn.predicate` (T-0336). The entry cannot be built yet, for a reason the records already state:

- ADR-0121 Consequences: the loop's command-line entry "still waits on … what follows a failed turn (OD-10, OD-17, OD-19, OD-27)", as well as ㉙ (나), the lock and ⑪.
- `hilclaw.further_turn.predicate` hands every state ADR-0121 decision 5 does not answer to a caller's `fallback(previous)`: a turn whose exit status is not 0 (in P1 and P4), and every OPEN state (missing beyond P1, invalid or other-version files, a run with no `round_budget`). A command-line entry has to supply that `fallback`, and any `fallback` it supplies decides what follows a failed turn.
- The T-0336 Result names a further hole: a turn that exits with 0 and leaves the run as it found it is answered with a further turn again (P1 stays fresh; P4 with `round` unmoved). Today's placeholder `orchestration/round-manager.md` ends every turn exactly that way ("end the session without writing any file"). An entry built now would start turns without end on a runtime machine and spend plan usage (NFR-5, C-7 ②).

ADR-0118 decision 3 lists "retry at once, wait, stop, notify, or a pause on a usage limit" as undecided. These are design-level ODs (OD-17, OD-19; DRIVER §9), not owner-only ones, so this task writes the ADR that closes the part the entry needs (DRIVER §6, §9). The code slice (the entry) is the next task.

**Planner's suggestion, for the executor to weigh, not a decision.** One answer that seems to stay small is "the loop starts no turn on a state no record answers, and does not start a further turn on its own after a turn that failed or changed nothing; it returns and says why, and whatever started it (a person, a schedule — ADR-0118 decision 3) decides whether to start it again". The executor chooses the answer, weighs the alternatives in the record, and returns BLOCKED (`requirement-unclear`) rather than inventing if the choice turns out to need an owner sentence that does not exist.

Open Draft PR #186 (T-0324, BLOCKED on HQ-0032) touches `hilclaw/start_instance.py` and three test files only. None of them is in this task's touchesFiles.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0337` trailer, size cap;
  - §9 (lines 142-149): the D6 route for a design-level OD and its owner notice; the owner-only list.
- `CLAUDE.md`, these rules: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md` (document-mode path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`:
  - decision 2 (lines 57-66), above all (ii), the ways a turn ends before its round;
  - decision 3 (lines 67-90): the loop's steps, "What it does after a turn session failed", "Two loops on one run", "What starts the loop", "Modes";
  - Consequences, runtime acceptance items (v) and (vi) (lines 154-185);
  - Boundaries (lines 186-201).
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: Status (lines 3-21, as a model of the owner-sentence search); decisions 2 to 5 (lines 39-86); Consequences (lines 105-122); Boundaries (lines 123-135).
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: decisions 1, 2 and 4 (lines 38-69).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`: decisions 3 and 6.
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decision 9.
- Code, as observation only (no code is changed by this task):
  - `hilclaw/turn_loop.py`: module docstring (lines 1-90) and `run` (from line 257): what `further_turn` is given and what the loop does with its answer;
  - `hilclaw/further_turn.py`: module docstring (lines 1-40) and `predicate`;
  - `orchestration/round-manager.md` (whole file): the placeholder that ends every turn without a write.
- `ARCHITECTURE/Requirements.md`: FR-1, FR-3, FR-16, NFR-1, NFR-5, C-7; the "행 형식" paragraph (line 84); register rows OD-8 (line 99), OD-10 (line 101), OD-17 (line 108), OD-19 (line 110), OD-27 (line 118).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet of the header (line 8); § OD-10 (from line 170), § OD-17 (from line 260), § OD-19 (from line 350).
- `ARCHITECTURE/UsageCases.md`: UC-2 (from line 79), UC-3 (lines 93-105), UC-4 (from line 106).
- `ARCHITECTURE/StandardScenarios.md`: "검사 규칙" (from line 13); S0, S1, S2 (S2 lines 66-75); "# 검사 결과" with its first paragraph (lines 168-172) and the S0-S2 rows of the 판정표 (around line 187).
- GitHub, before editing (CLAUDE.md "세션 진입 점검"): `gh pr list`; issues #4, #5, #7, #8, for the owner-sentence search below.

## Acceptance Criteria

1. **New record `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`** in the ADR-0001 record format, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries and References. If ADR-0122 is taken on `origin/main` when the task starts, use the next free number and adjust the file name; say so in Result.
2. **Status** says it is accepted under DRIVER §9 (D6) by the reviewer's approval and not confirmed by the owner; separates cited content from the record's own; reports an **owner-sentence search** over #4, #5 (comments without the "posted by driver" marker), #7 and #8 with its search terms (for example: retry, 재시도, failed turn, 실패, stop, 중단, pause, 일시정지, rate limit, usage limit, no progress, 무진전, restart, 재기동, cron) and quotes each sentence found that touches the points, read for what it says and no further; states that the points are design-level (OD-17, OD-19) and need none of #5 A or B, C-6, OD-25 or OD-3; lists what it builds on (at least ADR-0012, ADR-0118, ADR-0120, ADR-0121) with "if one of them is reverted, this record is revisited with it"; states the 7-day objection window.
3. **Scope**: the runs of ADR-0120 decision 1 and the turn loop of ADR-0118 decision 3 driving them. Nothing is required or allowed of other runs.
4. **Decision** answers, for that scope, each of these points, each with its reason:
   - (a) **After a turn whose exit status is not 0**, in states P1 and P4 of ADR-0121 decision 5 and in the states that decision leaves open: whether the loop starts a further turn on its own, and if so how many times and with what pause; if not, what it does instead.
   - (b) **After a turn whose exit status is 0 that leaves the run as it found it** (in P1 the directory is still fresh; in P4 the run's `STATE.json` is unchanged): what "as it found it" is, defined only on reads of files the loop already reads (no new file, no listing of the run tree — #4 §1), and what the loop does then. If the answer changes what ADR-0121 decision 5 concludes in P1 or P4 for that case, the record says so plainly as a narrowing of that decision for this scope, lists it in Consequences, and does not edit ADR-0121. It distinguishes this from OD-19's "무진전 서킷브레이커" (rounds that do not improve), which it does not answer.
   - (c) **In the states ADR-0121 decision 5 leaves open, before the first turn and after a turn that exited with 0**: a `STATE.json` missing beyond P1, invalid or of another version; an `instance.json` missing, invalid or of another version beside a valid `STATE.json`; a run whose `instance.json` states no `round_budget`. For the last, the record either answers OD-8 ㉙ (나) for this scope or says explicitly that its answer for the loop does not answer ㉙ (나) (it does not say the run is over, and writes no `run_status`).
   - (d) **What the loop or its entry tells whoever started it**, in kind only: which outcomes are told apart (for example: run over, unknown `run_status`, stopped after a failed turn, stopped after an unchanged turn, open state) and that they reach the starter through the process (exit status, standard streams). The concrete exit codes, texts and option names are the code task's. No notification channel is chosen (FR-16, OD-27 stay open).
   - The record keeps these from ADR-0118 and ADR-0121, citing them: the loop makes no judgement and calls no model; **it writes nothing into the run** (no `run_status`, no other member, no file) and is no second writer of `STATE.json`; it is no FR-10 tool; two turn sessions of one run never run at once.
5. **The rate-limit pause and the exit status.** The record states how its answers relate to OD-19's proposal that reaching the plan's usage limit is a pause and resume, not a failure (C-7). It may leave the pause open, and it says whether the loop can tell a usage-limit exit from another failure today (ADR-0118 runtime acceptance item (vi)); it does not presume that it can. Any fact only a live Claude Code session can establish is listed as a runtime acceptance item in Consequences and is not tried (D16); if one is new (not already among ADR-0118's (i)-(vii)), say so in Result so the driver can raise an HQ with reason `runtime-acceptance`.
6. **Alternatives considered** has at least one row per point (a)-(d), covering at least: retry at once a fixed number of times; retry after a pause; stop and return to the starter; keep starting turns (today's behaviour of P1 and P4); for (b), a bound on the number of turns per start instead of a check on the run's files; for (c), start a turn anyway and let the Round-Manager decide. Each row gives its cost (plan usage, NFR-5; unattended runs, UC-3, S2 step 3; a run that a person must restart).
7. **Consequences** names: the code slice it enables (the command-line entry composing `turn_loop.run`, `turn_definition.put`, `further_turn.predicate` with the `fallback` this record defines, and `hilclaw.config`; tested against a stub `claude` only, D16) and what that slice still waits on; the sentences of accepted records and of code docstrings it makes less exact (found by a search of `ARCHITECTURE/decisions/` for "failed turn", "what follows", "retry", "caller's predicate"; listed, not edited); the A-13 reading (document mode, **no data-plane change**: no member, file, kind, value or version, no validator change); runtime acceptance items, if any.
8. **Boundaries** keep open, each with its OD: the lock of two loops and fencing (rest of OD-17); the recovery of an open step inside a turn and declarative per-tool retry (OD-17, OD-10); board failure and recovery, which a failed turn session is not (OD-10, #5 B-2); the rest of OD-19 (caps per round and per coder call, the single ledger, the no-progress breaker on results, the rate-limit pause if it is left open, non-convergence with UC-7); notification channels (OD-27); the commit step and the commit owed by a run that is over (OD-8 ⑪); gates and waiting (OD-3 owner-only, OD-8 ㉝ (가)); resumed, continued or branched runs (OD-8 ①); runs outside the scope.
9. **Register and proposals, following the rules written in those files** — not the wording of earlier task files:
   - `ARCHITECTURE/Requirements.md`: follow its "행 형식" (line 84). For each OD whose part the record answers (at least OD-19; OD-17 if (a) answers a part of it; OD-8 if (c) answers ㉙ (나)), add **one link** to ADR-0122 with a few words of topic to that row's `**확정분**:` and rewrite its `**잔여**:` in place. Do not restate the record and add no dated paragraph. Status cells change only as the "행 형식" allows (a short status word with date and route). OD-10 and OD-27 are not edited unless the record answers a part of them.
   - `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). In each section concerned (§ OD-19, and § OD-17 or § OD-8 where the record answers a part), one `- **채택분**` line linking ADR-0122 with what it covers, and the open parts and sub-question endings rewritten in place (`→ 부분 답: … 남음: …` / `→ 답함: …`). The proposal text and the sub-question wording stay. No dated note and no restatement of the record.
   - `ARCHITECTURE/StandardScenarios.md`: re-check S0, S1 and S2 (at least) under "검사 규칙" (CLAUDE.md "문서 커버리지 재검사") and record the result as the first paragraph of "# 검사 결과" (line 170) says: rewrite the "최근 재검사" line in place; add a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed; in the 판정표 notes, name only the FRs and the ODs (with sub-question numbers) still open — for example narrow S2 step 3's "OD-17 잔여·OD-10" pointer if the record answers a part of it.
   - UsageCases is edited only if a sentence becomes false; say in Result whether one did.
10. **No invention.** The record cites a source for every sentence that is not its own, decides nothing owner-only, and does not settle any point listed in AC 8. If the reviewer finds a choice that needs an owner sentence (for example a value judgement on how much plan usage an unattended run may spend on retries, if #5 A-8 or C-7 is found to bind it), stop and return BLOCKED (`requirement-unclear` or the §9 owner-only reason) with the question.
11. **D16.** No `claude` is started (no subcommand, no flag), and nothing needs a board, an accelerator or an API key. No fact is tried in a live session.
12. **Scope of the change.** `git diff --stat origin/main` lists only touchesFiles, plus this task file's Result. No edit to `hilclaw/`, `orchestration/`, `tests/`, CI, `.claude/`, `CLAUDE.md`, `README.md`, `PROCESS/` (other than this file's Result) or any earlier ADR. No new dependency.
13. **Merge (document mode, CLAUDE.md A-13).** Branch `claude/T-0337-adr-turn-loop-open-states`; context-isolated reviewer cycle (dev-code-review document path), at most 7 rounds, until Approve; rebase on `origin/main` and push to `main` without a PR, never with `--force`. The commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0337`. In Result: the landed commit(s), the number of review rounds, any review point left as a follow-up, and the text of the owner notice for #5 (the driver posts it — DRIVER §9, §8 footer).

## Out of Scope

- The command-line entry itself and any code (`hilclaw/`), test or `orchestration/` change, including the `hilclaw/turn_loop.py` and `hilclaw/further_turn.py` docstrings that this record may make less exact.
- The lock of two loops, the commit step (OD-8 ⑪), the round-0 text of the Round-Manager prompt, how the Round-Manager reaches `replace` (OD-23, OD-18), OD-18 ⑯ (가).
- Board failure and recovery (OD-10), notification channels (OD-27), gates (OD-3), the rest of OD-19 listed in AC 8.
- Any edit to ADR-0118, ADR-0121 or another accepted record, or to the sentences they list as less exact; anything in PLAN's 보류 section; anything blocked by HQ-0013..HQ-0035.

## Follow-ups

- The command-line entry of the turn loop (code mode): data root from `hilclaw.config`, the definition source `orchestration/`, a fixed prompt within `turn_loop`'s prompt rule, `further_turn.predicate` with the `fallback` and `report` this record defines, exit status and output as the record's point (d) has it. Tests use a stub `claude` only (D16). The `turn_loop.py` docstring sentence on the missing entry can be corrected in that task.
- The remaining P2-1 slices: OD-18 ⑯ (가), OD-8 ⑪, how the Round-Manager reaches `replace` (OD-23, OD-18), then the round-0 part of the Round-Manager prompt.

## Result

**Outcome**: DONE (document mode). ADR number 0122 was free on `origin/main` and is used as planned.

- **Review**: 4 rounds with a fresh-context dev-reviewer (round 1 and 2 Request changes, round 3 Approve with nits, round 4 Approve). Left as is: the round-4 nit on the "(OD-19)" tag of the § OD-17 채택분 line — it follows the cross-OD tag already used in that section ("[ADR-0012](…) (OD-8)").
- **Landed**: `8ea7115` on `main` (one squashed commit, no PR, document mode); branch deleted. Owner notice posted on #5: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6264725673 (the text below, with `<landed sha>` = `8ea7115`).

- **Record**: `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md` — for the runs of ADR-0120 decision 1, the turn loop starts no further turn on its own after a turn whose exit status is not 0 (decision 2), after a turn that exited with 0 and made no progress (P1 still fresh, or P4 with the same `round`; decision 3), or in the states ADR-0121 decision 5 leaves open (decision 4); it returns and tells its starter one of five outcomes through exit status and standard streams (decision 5). The usage-limit pause stays open (decision 6). It narrows ADR-0121 decision 5 for the "exit 0, no progress" case (listed in Consequences; ADR-0121 not edited). It does **not** answer OD-8 ㉙ (나). No data-plane change.
- **Owner-sentence search**: no owner sentence decides the points; the B-6 "pause-and-resume" sentence is an integrator reading, not an owner answer (ADR-0122 Status O3). FR-4 / UC-3 "무정지" is read as set against gate stops, stated as a reading with its cost (decision 2).
- **Register / proposals**: Requirements OD-17 and OD-19 rows gain one link each with `**잔여**` rewritten in place (status words unchanged); OpenDecisionProposals § OD-17 and § OD-19 gain one `채택분` line each and their open parts are rewritten in place. OD-8, OD-10 and OD-27 are not edited.
- **Coverage re-check**: S0, S1, S2 re-checked — no verdict change, no gap; the "최근 재검사" line is rewritten and S2 step 3's OD pointer narrowed. No history entry (no verdict change).
- **UsageCases**: no sentence became false (UC-3 step 1 and S2 step 3 read with decision 2); not edited.
- **New runtime acceptance item** (for an HQ with reason `runtime-acceptance`): (viii) how a `-p` turn session that reaches the plan's usage limit ends — its exit status, and whether anything in its output tells it from another failure. ADR-0122 does not rely on it; a record defining the usage-limit pause would. ADR-0118 items (v) and (vi) are used, not changed.
- **Follow-ups** (for the integrator / later tasks): the code slice — the command-line entry of the turn loop (Consequences), still waiting on the lock of two loops before any schedule may start it; the less-exact sentences listed in ADR-0122 Consequences (ADR-0118, ADR-0120, ADR-0121, `hilclaw/turn_loop.py`, `hilclaw/further_turn.py` docstrings).
- **Owner notice for #5** (DRIVER §9, §8 footer):

```
### ADR-0122 accepted (D6 route) — turn loop of a first-case run: no further turn on its own after a failed or no-progress turn, or in an open state

ADR-0122 (part of OD-19 and of the rest of OD-17, for the runs of ADR-0120 decision 1) was accepted by reviewer approval under PROCESS/DRIVER.md §9. It is not confirmed by the owner.

- After a turn session whose exit status is not 0, after a turn that exited with 0 and made no progress (fresh directory still fresh, or `round` unchanged), and in the states ADR-0121 decision 5 leaves open, the turn loop starts no further turn on its own; it returns and tells its starter which of five outcomes ended the start (exit status and standard streams). No retry count, pause length or notification channel is chosen.
- It reads FR-4 / UC-3 "무정지" as set against gate stops; the cost is that an unattended first-case run waits for its starter (a person, until the lock of two loops lets a schedule restart it) after each failed turn.
- The usage-limit pause (OD-19 proposal) stays open; OD-8 sub-question ㉙ (나) is not answered. It narrows ADR-0121 decision 5 for the "exit 0, no progress" case. No data-plane change.
- New runtime acceptance item (viii): how a `-p` turn session that reaches the plan's usage limit ends.

Record: ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md (commit <landed sha>). You may object within 7 days of this notice; an objection creates a task that reverts the record and its edits.

— posted by driver
```
