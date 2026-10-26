---
id: T-0486
title: Land ADR-0171 code slice 2 - give the technique-selector `catalog.read`, the choice and its `techniques:` report line, extend the coder-driver to round >= 1, and add the Round-Manager's step 8 with the stop moved after the coder-driver's report, with tests
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-5, FR-8, FR-17, OD-23, OD-22, OD-6, S0, S1, "PLAN P2-1"]
dependsOn: []
touchesFiles:
  - orchestration/agents/technique-selector.md
  - orchestration/agents/coder-driver.md
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
  - tests/test_caller_check.py
estimatedSize: {loc: 150, files: 4}   # tests excluded from the cap (DRIVER §5, D4/D20)
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round procedure) is open. In the P2 order (P2-1 to P2-4, P2-6, P2-7, then P2-5) it is the item that can move now. This is checklist work, so the D18 rule for work outside the checklist does not apply.

ADR-0171 (landed by T-0485 as `b8480143`) decided who chooses the technique ids of a round >= 1 spec and how they reach `spec.write`. Its first code slice, the registry tool `catalog.read`, is on `main`. Its **code slice 2, the definitions**, is not. ADR-0171 Consequences, "Code slices for the planner", item 2, names it. Until it lands:
- `catalog.read` is registered but held by no agent, so the caller check refuses every call of it.
- A turn of a round >= 1 still stops right after `hypotheses.read` (step 7 of "The round steps" in `orchestration/round-manager.md`).
- No round >= 1 reaches a spec write or a coder call, so P2-5's five-round run cannot get past round 1.

This task writes exactly what ADR-0171 decisions 2 to 6 fix. It decides nothing new. If a sentence the definitions need is not supported by ADR-0171 or an earlier accepted record, stop and return BLOCKED (`requirement-unclear`). Do not write it.

Sizing (D20 ③): the slice is below half the cap. The adjacent P2-1 work is the record of the round >= 1 steps after the coder call. That work needs a new design record with its own review risk, so it is the next task of this batch (T-0487, which depends on this one). It is not folded in here, so that this slice does not carry the record's review risk.

No owner-only decision is touched (#5 A/B items, C-6, OD-25, OD-3). No model of any agent is named (#5 A-8). No unresolved HQ exists in `PROCESS/STATE.json` at `a099ac5d`, and no item of `PROCESS/RuntimeAcceptance.md` has the state `실패`.

## Required Reading

Line numbers are those of `main` at `a099ac5d`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 73: executor procedure, landed check, resume rule, time limit) and **§5** (lines 87-116: task format, naming, trailers, size cap D4/D20, test rules D12, the pinning-list rule D21). Also §8 (lines 144-151): runtime acceptance items go to `PROCESS/RuntimeAcceptance.md`, not to an HQ.
- CLAUDE.md, the whole file. These sections matter most:
  - "개발 드라이버와 런타임의 구분": no `claude`, Docker or `clang` is started; tests use fixture files and stubs only;
  - "테스트 규칙";
  - "브랜치·merge 절차": code mode;
  - "코멘트 최소화";
  - "미결은 발명하지 않는다".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **The record this slice applies**: `ARCHITECTURE/decisions/ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md`, the whole file (138 lines). Above all:
  - decision 2 (lines 32-38): the selector's choice, its criteria in order of weight, and when an empty list is allowed;
  - decision 3 (lines 40-55): `catalog.read`, the selector's `tools`, and the reasons for it;
  - decision 4 (lines 57-62): the `techniques:` report line and when it is given;
  - decision 5 (lines 64-69): the coder-driver's round >= 1 rule;
  - decision 6 (lines 71-76): step 8 and the stop;
  - the Walk-through (lines 78-89);
  - Consequences, slice 2 (line 114).
- Records cited by the sentences you write. Read only the decisions named:
  - ADR-0132 decisions 3, 4, 6 and 7 (`ARCHITECTURE/decisions/ADR-0132-od23-first-case-selection.md`);
  - ADR-0141 decisions 5 and 6;
  - ADR-0151 decision 3;
  - ADR-0126 decision 6;
  - ADR-0123 decisions 2 and 4;
  - ADR-0143 decisions 2 and 7.
- **Definitions (whole)**:
  - `orchestration/round-manager.md` (222 lines). "Your run" `Agent` bullet at lines 44-53; step 2 at 131-143; steps 6-7 at 167-177; the stop at 179-193; the closing steps at 195-222.
  - `orchestration/agents/technique-selector.md` (70 lines).
  - `orchestration/agents/coder-driver.md` (45 lines).
- **Code**:
  - `hilclaw/turn_definition.py`, the module docstring (lines 1-84), above all the *prompt* bullet (lines 34-51) and "Not done here" (lines 72-76);
  - `hilclaw/catalog_tool.py`, the module docstring (read only);
  - `hilclaw/turn_permissions.py`, the module docstring (read only: the pre-approved list derived from the agents' `tools`);
  - `hilclaw/caller_check.py`, the module docstring (read only).
- **Tests (whole)**:
  - `tests/test_turn_definition.py`. Constants at lines 25-38; the coder-driver tests at 500-522; the prompt tests from 577; the selector tests at 795-840; the later-round tests at 841-904.
  - `tests/test_turn_permissions.py`: `test_the_real_definition` at 261 and `test_holder_lists_the_real_definition` at 406.
  - `tests/test_caller_check.py`: constants at lines 20-40; `test_the_real_experiment_runner_holds_board_run` at 298, as the model for a real-definition test.

## Acceptance Criteria

1. **`orchestration/agents/technique-selector.md`** (ADR-0171 decisions 2 to 4):
   - `tools` gains `mcp__hilclaw__catalog_read`. Every other entry stays.
   - "What you are given" says that `mcp__hilclaw__catalog_read` gives the `## When` selection criteria of the entries of the run's catalog, and nothing more (decision 3).
   - A new section states the choice of decision 2:
     - after the round's record exists, choose the technique ids of the spec of candidate 1;
     - weigh, in this order: the round's hypotheses (those whose `tested_by` holds candidate 1); the entries' `## When`; the earlier attempts and records;
     - the hypotheses name no technique (ADR-0059 decision 3);
     - which entries, how many and in what order are the selector's judgement;
     - an empty list on `catalog_unusable`, on an empty result, or when no entry serves the hypotheses.
   - "Your report" adds the one fixed line of decision 4:
     - `techniques: <id>, <id>, ...` in the chosen order, or `techniques: none`;
     - given only when the round's record exists (written, or answered `hypotheses_exist`) and `catalog.read` returned a result or `catalog_unusable`;
     - otherwise no such line.
   - The existing fixed rule "Request no check, measurement, spec or coder call" stays.
   - Each changed sentence cites ADR-0171 and the decision it follows. Update the `description` if it no longer covers the work.
2. **`orchestration/agents/coder-driver.md`** (ADR-0171 decision 5):
   - The `description` no longer says only "round-0".
   - "What you are given": for a round >= 1 the message also names the technique ids of the selector's line in their order, or that there are none.
   - Fixed rule 1:
     - in a round >= 1 the `spec.write` request carries `techniques`: the message's ids in their order, or an empty array for none;
     - in round 0 it carries no `techniques` member (ADR-0151 decision 3);
     - a round >= 1 delegation that gives no list: request nothing and report that.
   - Rules 2 to 5, the interim `spec_exists` rule among them, stay unchanged. `tools` stays exactly `mcp__hilclaw__spec_write, mcp__hilclaw__coder_run`.
3. **`orchestration/round-manager.md`** (ADR-0171 decision 6):
   - **Step 7.** On a returned record it goes on to step 8 and no longer comes to the stop. A failed read still reports the kind and comes to the stop before any coder delegation.
   - **New step 8, "Round >= 1 only."** If the selector's report of step 6 holds exactly one `techniques:` line:
     - delegate to `coder-driver` with the `Agent` tool and wait;
     - the message names the run id, the tuple `round` r, `candidate` 1, `attempt` 1, the ids of that line in its order (or that there are none), and no place;
     - whatever the coder-driver reports, report it in one line and come to the stop;
     - in that turn delegate no second time, issue no call yourself and ask for no repair.
     Otherwise report in one line that no choice was given and come to the stop, delegating nothing.
   - **The stop paragraph.** In rounds >= 1 it now follows step 7 after a failed read, and step 8 otherwise. After a coder-driver report, it reports in one line that the following steps of round `<round>` are not yet defined. The round is not ended, and `run.commit` is called as "The end of a session" says.
   - **"Your run".** The `Agent` bullet allows the delegation to `coder-driver` "as steps 2 and 8 say" (or equivalent). The prohibitions on calling `spec_write`/`coder_run` yourself stay.
   - **Step 2's last sentence** ("In a round >= 1 there are no steps 2 to 5: step 6 follows step 1") stays true. Keep it.
   - **"The closing steps of a round" and "The end of a session".** Change them only where the new step makes a sentence false. No round >= 1 reaches the closing steps yet.
   - **"Later slices of the definition replace this stop in rounds >= 1 ..."** stays: the steps after the coder call are still undefined.
   - Each changed or added sentence cites ADR-0171 decision 6, plus decision 5 for the message.
4. **`hilclaw/turn_definition.py`**: docstring only, no code change. The *prompt* bullet and "Not done here" now say:
   - a round >= 1 turn delegates the selection, reads the record, delegates the coder call with the selector's ids, and then stops;
   - the steps after the coder call are not yet defined.
   Keep the runtime acceptance list as it is.
5. **Tests** (code mode; D12; test files are outside the size cap). Use the real definition copied by `turn_definition.put` into `tmp_path`, and fixture files only. Never use a real `claude`, `docker` or `clang` (D16).
   - `tests/test_turn_definition.py`:
     - the selector body names `catalog_read`, the order of the criteria, the empty-list cases, the exact `techniques:` and `techniques: none` forms, and the condition for giving the line;
     - the coder-driver body names the round >= 1 `techniques` rule, the round-0 "no `techniques` member" rule and the no-list case;
     - the prompt's step 8 exists, starts "Round ≥ 1 only.", delegates to `coder-driver` only on exactly one `techniques:` line, names the tuple with `candidate` 1 and `attempt` 1, and comes to the stop after the report;
     - step 7's failed-read branch still comes to the stop and does not name `coder-driver`;
     - **negative**: steps 6 to 8 name no `evaluator`, `experiment-runner`, `case_write`, `round_end` or "closing steps", and there is no step 9 in "The round steps";
     - the stop paragraph names step 8 and still says the following steps of a round >= 1 are not yet defined.
   - `tests/test_caller_check.py`: with the real definition, `mcp__hilclaw__catalog_read` passes for `agent_type` `technique-selector`. It is refused for the main session, the evaluator, the coder-driver and the experiment-runner.
   - **Pinning assertions you may touch** (DRIVER §5 D21: only as far as they reflect the change; list each in the PR body):
     - `TECHNIQUE_SELECTOR_TOOLS` (`tests/test_turn_definition.py` line 29);
     - the selector tuple in `test_holder_lists_the_real_definition` (`tests/test_turn_permissions.py` line 431);
     - an added `catalog_read` presence line in `test_the_real_definition` (line 261).
   - **Assertions that pin the old prompt or definition text** change only where this slice replaces that text. State each change and its reason in the PR body:
     - `test_the_prompt_delegates_the_selection_in_later_rounds` (841): its "If it returns" part;
     - `test_the_stop_follows_the_read_in_later_rounds` (865);
     - `test_no_later_round_reaches_a_spec_write_or_a_coder_delegation` (889). It becomes a test that the coder delegation is step 8's alone and follows only a returned record. Keep its negative intent for evaluator, experiment-runner and closing steps;
     - `test_the_prompt_keeps_the_stop_in_later_rounds` (593);
     - `test_the_prompt_reaches_the_closing_steps_from_round_0_only` (659), only if its text is touched;
     - `test_the_coder_driver_names_the_kind_and_the_result` (518), only if a word it pins moves.
     Every other existing assertion stays as it is.
   - Run the full local suite (`python -m pytest`), `ruff check .` and `ruff format --check .`. Coverage of `hilclaw/` stays at line >= 80% and function >= 80%. CI must be green before the squash-merge.
6. **Landing.**
   - The commit body names the languages and the reason in one line: Markdown for the definitions, Python for the docstring.
   - The PR body ends with `Task: T-0486`.
   - No owner notice is needed: no new record and no OD status change.
7. **Result.** In `## Result`, write:
   - every prompt or definition sentence added or rewritten, quoted briefly, with the ADR-0171 decision it follows;
   - the test assertions changed (as in the PR body);
   - that ADR-0171 runtime acceptance items (lxxxiii) and (lxxxiv) (RA-0040) can now be checked. No new item, unless the review finds one;
   - the sentences of earlier records this slice makes less exact (for example ADR-0132 decision 3's exact `tools` list, as ADR-0171 Consequences foresaw), without editing them.

## Out of Scope

- The round >= 1 steps after the coder call: checks, measurement, comparison, verdicts, `case.write`, the closing steps. That is T-0487.
- Any edit of an ADR, `ARCHITECTURE/` register, README, UsageCases, `catalog/`, `hilclaw/` code (beyond the one docstring), `.claude/settings*.json`, or any data-plane file, member or version.
- Any change of `ROUND_MANAGER_TOOLS`, the coder-driver's or the evaluator's `tools`, or `catalog.read` itself.
- Starting `claude`, Docker or `clang` on this machine (D16).

## Follow-ups

- (planner) T-0487: the record of the round >= 1 steps after the coder call and its first slice.

## Result

DONE. PR #300 squash-merged as `681538c7` after 1 review round (Approve with 3 Nits). Two wording-only Nits were fixed in the PR without re-review (D20); the third (`hilclaw/tools.py` `default_registry` docstring, around line 231: "the coder-driver performs the round-0 coder call") is out of scope and listed below. CI green (Python 3.11/3.14, C, sh, Coverage, Test presence). Local full suite before the Nit fixes: 33979 passed, 1858 skipped; after them the three touched test files: 302 passed, 9 skipped; `ruff check .` and `ruff format --check .` pass.

**Definitions changed**
- `orchestration/agents/technique-selector.md`: `tools` gains `mcp__hilclaw__catalog_read` (ADR-0171 decision 3); new section "The choice of techniques" (decision 2: weigh the round's hypotheses testing candidate 1, the `## When` sections, earlier attempts and rounds; empty list on `catalog_unusable`, no entry, or no fitting entry); report gains exactly one `techniques: <id>, ...` / `techniques: none` line when the round's record exists and `catalog_read` answered (decision 4).
- `orchestration/agents/coder-driver.md` (decision 5): delegation in round 0 and in rounds >= 1; a round >= 1 request carries `techniques` (the message's ids in order, or an empty array); round 0 carries no `techniques` member; a round >= 1 delegation without a list requests nothing.
- `orchestration/round-manager.md` (decision 6): step 7 goes on to new step 8 after a successful read; step 8 (round >= 1 only) delegates once to `coder-driver` with run id, tuple (round, candidate 1, attempt 1) and the `techniques:` ids, reports in one line and comes to the stop; the stop now says the following steps of a round >= 1 are not yet defined and the round is not ended.
- `hilclaw/turn_definition.py`: docstring only (prompt bullet, roster citing ADR-0171 decisions 2-5, "Not done here").

**Test assertions changed**: D21 list pins (`TECHNIQUE_SELECTOR_TOOLS` and the selector tuple in `test_holder_lists_the_real_definition` gain `mcp__hilclaw__catalog_read`; `test_the_real_definition` gains a presence line); `test_the_prompt_delegates_the_selection_in_later_rounds` and `test_the_stop_follows_the_read_in_later_rounds` updated for step 8; `test_no_later_round_reaches_a_spec_write_or_a_coder_delegation` replaced by `test_only_step_8_of_a_later_round_delegates_the_coder_call`. New tests: `test_the_coder_driver_carries_the_techniques`, `test_step_8_delegates_the_coder_call_with_the_choice`, `test_the_stop_names_step_8`, `test_the_technique_selector_reads_the_catalog`, `test_the_technique_selector_chooses_the_techniques`, `test_the_technique_selector_reports_one_techniques_line`, `test_the_real_technique_selector_holds_catalog_read` (tests/test_caller_check.py).

**Runtime acceptance**: ADR-0171 (lxxxiii)-(lxxxiv) (RA-0040) can now be checked; no new item. No `claude` was started (D16).

**Earlier sentences made less exact (not edited)**: ADR-0132 decision 3 (selector `tools` list), decision 1 "Outside" and Boundaries second bullet; ADR-0126 decision 6; ADR-0141 decision 6 "Left open and named" and Walk-through row "A round >= 1"; ADR-0151 decision 2 (c) and Boundaries first/second bullets; ADR-0150 decision 2 last bullet and decision 4 "Not decided here"; `hilclaw/tools.py` `default_registry` docstring.
