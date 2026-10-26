---
id: T-0487
title: Record the Round-Manager's round >= 1 steps after the coder-driver's report (which reports go on, the checks, the measurement, the verdicts delegation and the closing steps) as one new ADR (part of OD-23, with OD-16/OD-17/OD-30 where touched), and land its first code slice, with tests
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-9, FR-11, FR-17, FR-18, OD-23, OD-16, OD-17, OD-30, S0, S1, "PLAN P2-1"]
dependsOn: [T-0486]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0172-od23-first-case-round-one-after-coder-call.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - orchestration/round-manager.md
  - orchestration/agents/experiment-runner.md
  - orchestration/agents/evaluator.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
  - tests/test_caller_check.py
estimatedSize: {loc: 280, files: 8}   # tests excluded from the cap; the ADR's lines count (DRIVER §5, D4/D20). If the record needs a tool change first (criterion 3 (B)), the changed module and its tests join touchesFiles.
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round procedure) is open, and in the P2 order it is the item that can move. This is checklist work, so the D18 rule for work outside the checklist does not apply.

P2-5 (the first end-to-end run, `cpu_standin` x GEMM, N=1, 5 rounds) needs every round >= 1 to reach its end. After T-0486 (ADR-0171 slice 2), a turn of a round >= 1 delegates the coder call (step 8) and then comes to the stop. The stop says "the following steps of round `<round>` are not yet defined". So no round >= 1 is ever ended, and no run gets past round 1.

ADR-0171 Boundaries (first bullet) and ADR-0142 Boundaries ("the rounds >= 1, their sim measurement, its holder ...") leave these steps open by name: the checks, the measurement, the comparison (ADR-0140), the verdicts (ADR-0128), `case.write` and the closing steps. The parts already exist:
- the evaluator holds the checks and the verdicts work (ADR-0128, ADR-0140; its `## Verdicts` section in `orchestration/agents/evaluator.md`);
- the experiment-runner holds `board.run` (ADR-0142 decision 4);
- `case.write` (ADR-0133) and `round.end` (ADR-0135) are registered tools, and the closing steps are written for round 0.

No record decides the sequence for a round >= 1, or what each report leads to. These are design parts of OD-23 that the driver may close (DRIVER §9, D6). By D20 ①, the record goes with its first code slice in one task: code mode, with the ADR file in the PR. This task depends on T-0486 because both edit "The round steps" of `orchestration/round-manager.md`; this record continues from T-0486's step 8. ADR-0171, whose decisions fix that step, has landed.

No owner-only part is known. No unresolved HQ exists in `PROCESS/STATE.json` at `a099ac5d`, and no item of `PROCESS/RuntimeAcceptance.md` has the state `실패`.

**Stop conditions. The executor checks these and does not assume them away:**
- If the only defensible sequence needs any of the following, return BLOCKED with a Korean question for the owner (DRIVER §8: the issue, options (a)/(b)/(c), what stays blocked and what does not):
  - **"better than" or a choice among measurements** (#5 A-4, OD-1);
  - **a gate**, for example before a board's use (OD-3);
  - **a model or token budget** of an agent (#5 A-8);
  - **C-6 or OD-25**.
  The evaluator's existing verdict rules (ADR-0071, ADR-0140) are cited, not extended.
- If the sequence needs a new data-plane file, member, value or version, that is a data-plane schema change (CLAUDE.md A-13). Examples: a member that records why a round ended without an attempt; a writer of `decision/decision.md`. If no means that avoids it can be argued on the record's own ground, stop and return BLOCKED with the owner question.
- If an open PR touches the same rows or sections of `ARCHITECTURE/`, stop and return BLOCKED (CLAUDE.md 세션 진입 점검).
- If T-0486 is not `DONE` on `main` when this task starts, stop. T-0486's step 8 and stop are the text this record continues.

## Required Reading

Line numbers are those of `main` at `a099ac5d`, before T-0486; T-0486 changes `orchestration/round-manager.md`, the two agent files it names and `tests/test_turn_definition.py`, so locate those by heading or test name. The text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 73) and **§5** (lines 87-116: format, naming, trailers, size cap D4/D20, test rules D12, the pinning-list rule D21), **§8** (lines 144-151: HQ form; runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`; the `— posted by driver` footer) and **§9** (lines 153-160: which ODs the driver may close; the owner notice on #5; the 7-day window).
- CLAUDE.md, the whole file. These sections matter most:
  - "미결은 발명하지 않는다";
  - "문서 커버리지 재검사";
  - "세션 진입 점검";
  - "개발 드라이버와 런타임의 구분";
  - "테스트 규칙";
  - "브랜치·merge 절차";
  - "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- Before you edit `ARCHITECTURE/`, run `gh pr list`, read issues #4, #5, #7 and #8, and read the unresolved `humanQuestions` in `PROCESS/STATE.json` (CLAUDE.md 세션 진입 점검).
- **The direct predecessor and the model for form**: `ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md`, the whole file (168 lines). It answered the same question for round 0: decision 2 (the stop when no attempt came), decision 3 (sim then board checks), decision 4 (the experiment-runner), decision 5 (no `sim.run` timing in round 0), decision 6 (closing steps), the Walk-through and the Boundaries (lines 152-161). Format: ADR-0001 "Record format"; status marking, K-rows of Context, Walk-through table and the "less exact, not edited" list as in ADR-0171.
- `ARCHITECTURE/decisions/ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md`: decisions 5 and 6 (lines 64-76), Walk-through (78-89), "The cost, plainly" (line 120: `spec_exists` leaves a round >= 1 with no later call), Boundaries (122-130).
- What the steps after the call use and what they leave open. Read the parts named:
  - ADR-0128 (`…/ADR-0128-od23-first-case-evaluator.md`): decisions 4 to 7 and Boundaries (lines 135-145), above all "a round that never reaches evaluate" and "what follows a standing or a verdict (P2-1, OD-10)".
  - ADR-0140 (`…/ADR-0140-od16-first-case-attempt-comparison.md`): decisions 5 and 6 (lines 63-77) and Boundaries (142-153): the base of the comparison stays open and is the evaluator's judgement.
  - ADR-0133 (`…/ADR-0133-od23-first-case-round-promotion.md`): decisions 4 and 5 (lines 55-67). A round with a hypothesis record and no verdicts file is still promoted; a refusal does not stop the round.
  - ADR-0135 (`…/ADR-0135-od23-first-case-round-end-write.md`): decisions 2 to 6.
  - ADR-0119 decisions 4 and 5 (round 0 only; read to see what is not carried to round >= 1).
  - ADR-0131 decision 7 (the standing taken from the report).
  - ADR-0143 decisions 2 and 7 (the stop's `run.commit`).
  - ADR-0132 decision 6 (the round's go-on rests on the record, not on a report).
  - ADR-0062 decision 3 and ADR-0110 decision 6 (a further `execution`, which stays open).
- **Where the record is entered.** Read each file's own rules, and do not copy the wording of earlier task files:
  - `ARCHITECTURE/Requirements.md`:
    - the "행 형식" paragraph (line 84);
    - the OD-23 row (line 114);
    - the OD-16 row (107), OD-17 row (108) and OD-30 row (121), only where the record answers part of them.
  - `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" in its header (line 8); § OD-23 (from line 431; "제안으로 남는 부분" at 462); § OD-16 (256), § OD-17 (284) and § OD-30 (516), if touched.
  - `ARCHITECTURE/StandardScenarios.md`: its check rules (from line 13) and the first paragraph of § 검사 결과 (line 168).
- **Definitions (whole)**: `orchestration/round-manager.md`; `orchestration/agents/evaluator.md`; `orchestration/agents/experiment-runner.md`; `orchestration/agents/coder-driver.md`; `orchestration/agents/technique-selector.md`.
- **Code**:
  - `hilclaw/turn_definition.py`: the module docstring;
  - `hilclaw/case_tool.py`, `hilclaw/round_end_tool.py`, `hilclaw/verdicts_tool.py`: module docstrings, read to confirm each takes a round >= 1 as the sequence needs;
  - `hilclaw/turn_permissions.py`: `ROUND_MANAGER_TOOLS`;
  - `hilclaw/tools.py` `default_registry`.
- **Tests (whole)**: `tests/test_turn_definition.py` (the prompt tests and the later-round tests as T-0486 left them), `tests/test_turn_permissions.py`, `tests/test_caller_check.py`.

## Acceptance Criteria

1. **The ADR.** Write a new `ARCHITECTURE/decisions/ADR-0172-<slug>.md`. If 0172 is taken, use the next free number; check `ARCHITECTURE/decisions/` and the remote branches. The file name in `touchesFiles` is a suggestion. Scope: the runs of ADR-0120 decision 1 with `candidates_per_round` 1, rounds >= 1, from the coder-driver's report of step 8 to the end of the turn.
   - It decides at least these points:
     - **(a) Which coder-driver reports go on**, as ADR-0142 decision 2 did for round 0. Weigh what a report that brings no attempt leads to. The candidates:
       - the stop, as today, with the round left open (re-entry is OD-17's; ADR-0171 "The cost, plainly" says `spec_exists` then blocks every later turn of that round);
       - the verdicts and the closing steps, so the round ends with its case (ADR-0133 decision 4 promotes a round with a hypothesis record and no verdicts file; FR-18 stores failed attempts).
       Say which and why, and do not answer OD-23 ① (가) / OD-8 ㉖ (가) (a second call for one tuple) or repairs (OD-19).
     - **(b) The checks**: the evaluator's sim-point and board-point checks of the attempt (`r`, 1, 1), and what each standing leads to (cf. ADR-0142 decision 3).
     - **(c) The measurement**: the experiment-runner's `board.run` of that attempt; whether a round >= 1 has a `sim.run` timing (cf. ADR-0142 decision 5); what each `outcome` leads to.
     - **(d) The verdicts**: a delegation to the evaluator for the round's verdicts. Its message names the run id and the round, and no place (cf. ADR-0128 decision 7; ADR-0129 decision 5). Say when it is made, including after a failed check or a broken measurement if (a)/(b)/(c) go on to it, and what each report of it leads to. The base of the comparison stays the evaluator's judgement (ADR-0140 Boundaries) unless the record argues otherwise without an owner-only part.
     - **(e) The closing steps**: `case.write`, then `round.end`, then `run.commit` (cited: ADR-0133 decision 5; ADR-0135 decision 6). Say which steps reach them, and confirm from the tools' docstrings that each takes a round >= 1. A refusal there is handled as ADR-0133 decision 4 and ADR-0135 decision 5 say.
     - **What stays a stop**, and that every stop ends as "The end of a session" says (ADR-0143 decisions 2 and 7).
   - Mark every sentence as owner, cited, or the record's own.
   - **Consequences**:
     - The A-13 reading, with no data-plane change.
     - The code slices for the planner, in order. This task's slice is the first.
     - The sentences of earlier records and docstrings that become less exact, without editing them. At least: ADR-0171 decision 6 and its Boundaries first bullet; ADR-0142 Boundaries "the rounds >= 1"; ADR-0128 Boundaries "a round that never reaches evaluate"; the `hilclaw/turn_definition.py` docstring until the slice lands.
     - Runtime acceptance items for facts only a live session can show, for example a round >= 1 turn's six or more foreground delegations in one session (cf. ADR-0142 (xlv)). Number them after the last item in use: (lxxxiv) is ADR-0171's, so the next is (lxxxv). Check the records and T-0486's Result for a higher roman numeral first. State that these items go to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22).
   - **Boundaries** keep open what the record does not answer: N > 1 (OD-29), repairs (OD-19), a second call for a tuple, a further `execution`, re-entry of a round (OD-17), the base of the comparison (OD-20, OD-28), promotion beyond `case.write` (OD-15), hooks (P2-4), the lookup tool (P2-7), and the owner-only items.
2. **Register entries** follow the recording rules written in those files, not the wording of earlier task files:
   - Requirements.md: follow the "행 형식" paragraph (line 84) in the OD-23 row, and in the OD-16, OD-17 or OD-30 rows only where the record answers part of them.
   - OpenDecisionProposals.md: follow the header's "기록 규칙" (line 8) in § OD-23, and in the other touched sections.
   - StandardScenarios.md: re-check coverage under its check rules (CLAUDE.md "문서 커버리지 재검사"). S0, S1 and S8 are the likely ones. Update § 검사 결과 as its first paragraph says. Add a history entry only if a verdict changes.
3. **Code: the first slice the ADR names.** Exactly one of (A) or (B) applies, whichever the record makes first:
   - **(A) If no registry tool or `ROUND_MANAGER_TOOLS` change is needed**, the slice is the definitions:
     - `orchestration/round-manager.md`: the round >= 1 steps after step 8 as the record says. The stop paragraph, "Later slices of the definition replace this stop in rounds >= 1 ...", the first sentence of "The closing steps of a round" and the "Your run" `Agent` bullet are rewritten where the new steps make them false. Each changed sentence cites the new ADR's decision.
     - `orchestration/agents/experiment-runner.md` and `orchestration/agents/evaluator.md`: only their `description` or body sentences that say "round-0" or otherwise exclude a round >= 1. Their `tools` do not change unless the record says so.
     - The `hilclaw/turn_definition.py` docstring: the *prompt* bullet and "Not done here". Docstring only.
   - **(B) If the record needs a change of a registry tool** (for example `round.end` or `case.write` refusing a state the sequence produces) **before the definitions can use it**, the slice is that change with its tests. The definitions become the next slice, named in Consequences. Update `touchesFiles` in the PR body and in `## Result`. If the ADR and that slice exceed 600 lines or 10 files (tests excluded), land the ADR with the smallest slice that fits and name the rest in `## Follow-ups` (DRIVER §5).

   Use no wording in a definition that the records do not support. No multi-line comments in code.
4. **Tests** (code mode; D12; test files are outside the size cap). Use the real definition copied into `tmp_path` and fixture files only. Never use a real `claude`, `docker` or `clang` (D16).
   - **For (A)**, in `tests/test_turn_definition.py`:
     - each new step exists in the order the record gives, starts "Round ≥ 1 only." where it is round >= 1 only, and names the delegation, tuple and point the record gives;
     - the go-on and stop branches of each step are as the record says (happy and branch);
     - a round >= 1 reaches the closing steps with `case.write` and round 0 still skips `case.write`;
     - negative: no round >= 1 step calls `coder_run`, `spec_write`, `board_run`, `correctness_check` or `verdicts_write` itself; no second coder delegation in a turn;
     - the stop still ends with `run.commit` and leaves the round open.
   - In `tests/test_caller_check.py`, only if an agent's `tools` changed: the real definition passes each new tool for its holder and refuses it elsewhere.
   - **For (B)**: the changed module's tests cover happy, error, branch and negative cases for every changed public function.
   - **Pinning assertions you may touch** (DRIVER §5 D21; list each in the PR body): `TECHNIQUE_SELECTOR_TOOLS`, `CODER_DRIVER_TOOLS` and `EVALUATOR_TOOLS` in `tests/test_turn_definition.py`, and the tuples in `tests/test_turn_permissions.py` `test_holder_lists_the_real_definition` and `FIXED`. Each only if the record changes those lists.
   - **Assertions that pin the old prompt text** change only where the slice replaces that text. Locate them by name after T-0486, and state each change and its reason in the PR body. The ones foreseen:
     - `test_the_prompt_keeps_the_stop_in_later_rounds`;
     - `test_the_stop_follows_the_read_in_later_rounds`, or its T-0486 successor;
     - the later-round negative test T-0486 rewrote from `test_no_later_round_reaches_a_spec_write_or_a_coder_delegation`, keeping its negative intent for what the record still forbids;
     - `test_the_prompt_reaches_the_closing_steps_from_round_0_only`;
     - `test_the_stop_commits_and_leaves_round_0_open`;
     - `test_the_prompt_delegates_the_measurement_to_the_experiment_runner` and `test_step_4_goes_on_to_step_5_only_when_verified_at_board`, if their round-0 text moves;
     - `test_the_experiment_runner_body`, if a pinned phrase moves.
     Every other existing assertion stays as it is.
   - Run `python -m pytest`, `ruff check .` and `ruff format --check .`. Coverage of `hilclaw/` stays at line >= 80% and function >= 80%, and the test-presence check holds. CI must be green before the squash-merge.
5. **Landing.**
   - The commit body names the language and reason in one line.
   - The PR body ends with `Task: T-0487`.
   - After landing, post the owner notice of DRIVER §9 on issue #5 in English: what the ADR decides, the landed commit, and the 7-day objection window. Its last line is `— posted by driver`. Record the URL in `## Result`.
6. **Result.** In `## Result`, write:
   - the ADR and what it decides, in a few lines;
   - which of (A) or (B) landed and why;
   - the prompt sentences rewritten or added, quoted briefly, each with its decision;
   - the test assertions changed;
   - the record sentences made less exact but not edited;
   - the runtime acceptance items, for the driver to add to `PROCESS/RuntimeAcceptance.md` (not as an HQ);
   - the next slices for the planner.

## Out of Scope

- A writer of `decision/decision.md`, `eval.json` or any new data-plane file, member, value or version (a BLOCKED reason, CLAUDE.md A-13).
- N > 1, repairs, a second coder call for a tuple, a further `execution`, re-entry of a round, the lookup tool (P2-7), hooks (P2-4).
- Editing any earlier ADR, README, UsageCases, `catalog/`, `.claude/settings.json` or `.claude/settings.local.json`; any new external dependency.
- Starting `claude`, Docker or `clang` on this machine (D16). A five-round run through a stub `claude` is P2-5's verification, not this task's.

## Follow-ups

- (planner) The remaining slices the new ADR names, if any.

## Result

- **Outcome**: DONE. PR #301 (branch `claude/T-0487-round-one-after-coder-call`), squash-merged; 2 review rounds (round 1 Request changes: FR-17 for step 12, a register narrowing, citation nits; round 2 Approve, one wording nit fixed after approval under the D20 exception). Local `python -m pytest`, `ruff check .`, `ruff format --check .` green; CI green before the merge.
- **The ADR**: `ARCHITECTURE/decisions/ADR-0172-od23-first-case-round-one-after-coder-call.md` (part of OD-23; OD-23 keeps its status). For the runs of ADR-0120 decision 1 with `candidates_per_round` 1, rounds >= 1, after the coder-driver's report: (a) a `coder.run` result with a non-empty `taken` goes to the checks; a `coder.run` result with an empty `taken` or a `coder.run` kind goes to the verdicts (the tuple is consumed by the spec, no repair exists, so the attempt is settled as failed); a failed `spec.write`, `spec_exists` or an unreadable report keeps the stop; (b) evaluator sim then board check of (`r`, 1, 1), going on only on `"verified"`, any other report to the verdicts; (c) experiment-runner `board.run`, every report to the verdicts, no `sim.run` in rounds >= 1; (d) one verdicts delegation (run id and round only), the base of the comparison left to the evaluator; only a report of written verdicts (or `verdicts_exist`) goes on, any other report is the stop (FR-17); (e) `case.write`, `round.end`, `run.commit`; what stays a stop is listed in decision 7.
- **Criterion 3 (A) landed**: no registry tool, agent `tools` list or `ROUND_MANAGER_TOOLS` change was needed; every tool already takes a round >= 1 (`case_tool`, `round_end_tool`, `verdicts_tool` docstrings).
- **Prompt sentences** (`orchestration/round-manager.md`): step 8 "Go on to step 9 only when the report is a result of `coder.run` whose `taken` holds at least one name. When it is a result of `coder.run` with an empty `taken`, or a failure kind of `coder.run`, go on to step 12. On any other report ... come to the stop" (ADR-0172 decision 2); steps 9/10 "Delegate to `evaluator` ... the point `sim`/`board` ... On any other report go on to step 12" (decision 3); step 11 "Delegate to `experiment-runner` ... Whatever it reports ... go on to step 12" (decision 4); step 12 "Delegate to `evaluator` ... for the verdicts of the round ... When the report says that the verdicts file was written, or that `verdicts.write` answered `verdicts_exist`, go to 'The closing steps of a round' ... On any other report ... come to the stop" (decisions 5, 6); the stop "step 8 or step 12 as they say", "a turn of a round >= 1 only through step 12" (decision 7); closing steps "a round >= 1 after step 12" (decision 6); the Agent bullet "to `evaluator`, only as steps 9, 10 and 12 say, and to `experiment-runner`, only as step 11 says" and "Do not call `mcp__hilclaw__verdicts_write` yourself" (decisions 3 to 5). The "not yet defined" line and the "Later slices ..." paragraph are gone. `orchestration/agents/experiment-runner.md`: `description` no longer says "round-0" (decision 4). `hilclaw/turn_definition.py`: docstring *prompt* bullet and "Not done here" only. `orchestration/agents/evaluator.md` unchanged (nothing in it excludes a round >= 1).
- **Test assertions changed** (`tests/test_turn_definition.py`, listed in the PR body): `test_the_prompt_keeps_the_stop_in_later_rounds` (renamed `..._after_steps_7_and_8_only`), `test_the_stop_follows_the_read_in_later_rounds`, `test_only_step_8_of_a_later_round_delegates_the_coder_call` (negative intent kept and widened to steps 9-12), `test_the_prompt_reaches_the_closing_steps_from_round_0_only` (renamed `..._from_steps_5_and_12`), `test_the_stop_commits_and_leaves_round_0_open`, `test_step_8_delegates_the_coder_call_with_the_choice`, `test_the_stop_names_step_8`, and the helper `the_stop()`. No pinning list (D21) touched; `tests/test_caller_check.py` unchanged (no `tools` changed). New tests cover step 8's branches, steps 9-12 order and content, round 0 still skipping `case.write`, no round >= 1 step calling a held tool, one coder delegation per turn, the `verdicts_write` prohibition, the Agent bullet and the experiment-runner description.
- **Language**: Python for the tests and the docstring (the package's existing language); the definitions are Markdown (layer 1).
- **Registers**: Requirements OD-23 row (`**확정분**` link added, `**잔여**` rewritten in place); OpenDecisionProposals § OD-23 (partial-answer note, adopted line, remaining part rewritten); StandardScenarios "최근 재검사" line (S0, S1, S8 re-checked, no verdict change, no gap). OD-16, OD-17, OD-30 untouched (not answered further).
- **Less exact, not edited**: ADR-0171 decision 6, its Walk-through rows ending in the stop after a coder result, Alternatives row (e), Boundaries first bullet and "The cost, plainly" (`spec_exists`); ADR-0142 decision 1 ("rounds >= 1, which keep the stop after step 1") and Boundaries ("the rounds >= 1, their sim measurement, its holder"); ADR-0128 Consequences slice 4 and Boundaries ("a round that never reaches evaluate", "what follows a standing or a verdict"); ADR-0059 and ADR-0071 Boundaries ("hypotheses of a round that never reaches evaluate"); ADR-0143 decision 7 ("round steps 2 to 4").
- **Runtime acceptance items** (for `PROCESS/RuntimeAcceptance.md`, DRIVER §8 D22; not an HQ):
  - **(lxxxv)** In one round >= 1 turn session, the six foreground delegations of steps 6, 8, 9, 10, 11 and 12 (technique-selector, coder-driver, evaluator at `sim`, evaluator at `board`, experiment-runner, evaluator for the verdicts) each return their report in the same turn and in order, and the session reaches `case.write`, `round.end` and `run.commit` before any limit of the session itself ends it (as ADR-0142 (xlv) for round 0).
  - **(lxxxvi)** From the coder-driver's final message, the Round-Manager tells a result of `coder.run` with a non-empty `taken`, a result with an empty one or a kind of `coder.run`, and a kind of `spec.write`, and takes step 9, step 12 or the stop as ADR-0172 decision 2 says; and from the evaluator's final message of step 12 it tells written verdicts (the file written, or `verdicts_exist`) from any other report, and goes to the closing steps or the stop as decision 5 says.
- **Next slices for the planner**: none required by ADR-0172 (its only slice landed here). A whole round >= 1 through a stub `claude` is PLAN P2-5's verification.
- **Merge**: squash commit e4107adc4f591265eb266a7c1ba7a44e0359a666.
- **Owner notice (DRIVER §9)**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6410031887
