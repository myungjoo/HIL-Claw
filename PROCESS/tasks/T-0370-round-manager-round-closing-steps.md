---
id: T-0370
title: Write the closing steps of a round (case.write in a round >= 1, round.end, run.commit) into "The round steps" of orchestration/round-manager.md behind the explicit stop (ADR-0135 slice 2 and ADR-0133 slice 2; PLAN P2-1)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-13, FR-18, OD-23, OD-30, OD-8, S0, S1]
dependsOn: [T-0363, T-0367, T-0368, T-0369]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
estimatedSize: {loc: 45, files: 2}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and its round steps) is a checklist item and the first group in the P2 order (PLAN P2 head, D18). This task is a slice of P2-1, so the D18 rule for work outside the checklist does not apply. P2-5 needs it: a first-case round must end with its case, the write that ends the round, and the commit. No definition of the Round-Manager says that yet.

Three records fix the steps that close a round, and all their tools have landed:

- ADR-0133 decisions 4 to 6: in a round >= 1, `case.write` comes right before the write that ends the round. A refusal does not stop the round. Round 0 has no case. The tool landed with T-0363 (PR #208).
- ADR-0135 decisions 5 and 6: the round-end write is made only through `round.end`. On a failure the Round-Manager reports the kind and ends the session with the round not ended. The tool landed with T-0369 (PR #212).
- ADR-0127 decisions 3 and 5: `run.commit` comes right after the round-end write. On a failure the Round-Manager reports the kind and ends the session, as it would anyway.

ADR-0135 Consequences, slice 2, says the `round.end` step "can be written once the steps before it are defined, or behind an explicit stop". The steps between the key store and the round's close (bring-up, baseline, the coder call, the measurement, the verdicts) are still undefined. They wait on HQ-0040, on the holder of `sim.run`/`board.run` (T-0210/HQ-0021) and on later records. So this task takes the second option. The closing steps are written as the last part of "The round steps", and the existing stop stays in front of them. A turn still ends after step 1, so no turn reaches the closing steps until a later slice replaces the stop with the missing steps. ADR-0133 slice 2 (the `case.write` step) goes in the same task: ADR-0135 decision 6 places `round.end` "after `case.write`", so one step cannot be written without the other. Together they are under the D4 cap.

Open HQs checked. HQ-0051 (items (xxix)/(xxx) of ADR-0135) and HQ-0049 (items (xxv)/(xxvi) of ADR-0133) are runtime-acceptance notices. This task neither adds nor closes them. HQ-0043 (whether a turn cut short commits) is not crossed: the steps are as ADR-0135 decision 5 and ADR-0133 decision 5 cite it, and nothing new is decided. HQ-0040 and HQ-0041 concern the coder call, which stays out of scope. Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files, so it does not overlap.

All verification is by reading, by the existing suite and by CI. No real `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit) and §5 (task file format, naming convention, size cap, code-task test rules D12).
- `CLAUDE.md`, "상시 규칙": the comment policy, test rules ① to ⑤, the code-mode branch and merge procedure (A-13), and the driver/runtime separation (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `orchestration/round-manager.md`, the whole file (97 lines).
- `hilclaw/turn_definition.py`, lines 25-75 only: the module docstring's "*The prompt*" bullet and the "Not done here" sentence.
- `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md`:
  - Decision §1 (line 30: the scope, and that the first `STATE.json` and ADR-0121's own `"over"` write keep `state.write`);
  - §2, the first bullet and the table rows "Name", "Request" and "Result" (lines 34-40);
  - §3, the "Reported lines" bullet (line 55);
  - §5 (lines 66-72) and §6 (lines 74-76);
  - Walk-through (lines 78-90);
  - Consequences, slice 2 (line 116), and runtime acceptance items (xxix) and (xxx) (lines 127-129).
- `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md`:
  - §3, the table rows "Name", "Request" and "Result" only;
  - §4, the last bullet "A refusal does not stop the round";
  - §5 (whole);
  - §6 (whole);
  - Consequences, slice 2 (line 108).
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`, decision 3 (from line 43) and decision 5's bullet "If the call fails at the end of a round" (line 73).
- `hilclaw/round_end_tool.py` and `hilclaw/case_tool.py`: the module docstrings only (request, result, kinds).

## Acceptance Criteria

Language: no new layer-2 code. The change is layer-1 Markdown plus a docstring correction in an existing Python module. State this in one line in the commit body and in `## Result`.

### "Your run" (`orchestration/round-manager.md`)

1. The tool sentences add two tools, each with your run id as `run_id`. Bash, file tools and any other means are not used for these writes:
   - `mcp__hilclaw__case_write` is the only means of writing the round's case (ADR-0133 decision 6).
   - `mcp__hilclaw__round_end` is the only means of the write that ends a round (ADR-0135 decisions 2 and 6). `mcp__hilclaw__state_write` is then no longer the means of that write. Narrow the existing `state_write` sentence only as far as this makes it false: it keeps the first `STATE.json` (entry step 2) and ADR-0121's own `"over"` write (entry step 6), as ADR-0135 decision 1 has it.
2. The other bullets of "Your run", the whole of "One round at most" and the whole of "The entry of a turn" stay unchanged in substance.

### "The round steps" (`orchestration/round-manager.md`)

3. Step 1 (`key.store`) stays as it is.
4. The explicit stop stays right after step 1. A turn still reports in one line that the steps between step 1 and the closing steps of round `<round>` are not yet defined, and ends the session without a further write. Reword the stop only as far as the closing steps make its present wording false. It must still be plain that no turn goes past it, so the closing steps are not reached today.
5. After the stop, write the **closing steps** of a round as a separate, clearly headed part. Say in one sentence that they follow the round's last other step and are reached only once later slices define the steps before them. Then give these steps, in this order:
   - **`case.write`, only in a round >= 1.** Call `mcp__hilclaw__case_write` with your run id as `run_id` and the round's number as `round`. Whether `with_verdicts` is `true` or `false`, go on and do not report it. If the call fails with any kind, report the kind in one line and go on to the next step. Do not end the session, do not call it again in this turn and do not write the case another way. In round 0, skip this step (ADR-0133 decisions 1, 4 and 5).
   - **`round.end`.** Call `mcp__hilclaw__round_end` with your run id as `run_id` and the round's number as `round`. Supply no total, position, open step, next round or run status.
     - Whether `over` is `true` or `false`, go on to `run.commit`.
     - If `reported_lines` is not empty, report the line numbers in one line and go on.
     - If the call fails with any kind, report the kind in one line and end the session. Do not call `round.end` again in this turn, do not write `STATE.json` with `mcp__hilclaw__state_write` or any other way, and do not call `run.commit` (ADR-0135 decisions 3 and 5).
   - **`run.commit`.** Call `mcp__hilclaw__run_commit`. Whether `committed` is `true` or `false`, do not report it. If the call fails with any kind, report the kind in one line. In either case end the session (ADR-0127 decisions 3 and 5; ADR-0118 decision 2 (i)).
   - Cite the ADR decisions briefly, as the entry steps and step 1 do.
6. Keep the sentence that later slices replace the stop with the remaining steps of a round, in substance.
7. Keep the file short and imperative:
   - Do not restate ADR-0133, ADR-0135 or ADR-0127.
   - Add no step for the middle of a round: no bring-up, baseline, coder call, measurement or verdicts.
   - Add no member check at the entry. ADR-0135 "The cost, plainly" names it as an option, and this task does not take it.
   - Put no run's data into the file (ADR-0118 decision 5). Name no model (HQ-0041). Create no file under `orchestration/agents/`.

### The docstring (`hilclaw/turn_definition.py`)

8. Correct the "*The prompt*" bullet in one sentence or less. It must say that a round begins with the store of the key record files and ends with the case, the round-end write and the commit, and that the steps between are not yet defined, so a turn ends after the key store. Adjust the "Not done here" sentence ("no round steps after the key store (later P2-1 slices)") only as far as it becomes false. No code change.

### Tests and checks

9. No `hilclaw/` code changes. So test rules ① to ④ need no new test, and rule ⑤ forbids tests of test code. Do not add a test that pins the prompt's wording.
10. Run the existing suite locally (`pytest`, `ruff check`, `ruff format --check`) and confirm it passes, in particular `tests/test_turn_definition.py`, `tests/test_turn_start.py`, `tests/test_round_end_tool.py` and `tests/test_case_tool.py`. Then get CI green on the PR. No real `claude` is started at any point (D16). The stub `claude` of the existing tests is the only one.
11. Code mode (CLAUDE.md A-13; `orchestration/` is not a doc-mode path):
    - use branch `claude/T-0370-round-manager-round-closing-steps` and a Draft PR whose title holds `T-0370`;
    - run the reviewer cycle to Approve and get CI green;
    - squash-merge with the PR body as the squash message, whose last line is `Task: T-0370` (DRIVER §5);
    - delete the branch.
12. No runtime acceptance item is added or closed. Items (xxv)/(xxvi) stay with HQ-0049 and (xxix)/(xxx) with HQ-0051.

## Out of Scope

- Every round step between `key.store` and the closing steps: bring-up, the self-check, baseline, the selection, the coder call, the measurement and the evaluator delegation. These belong to later P2-1, P2-2 and P2-3 slices and wait on HQ-0040, T-0210/HQ-0021 and their own records.
- What ends a round (ADR-0135 Boundaries), and removing the explicit stop.
- Any change to `hilclaw/round_end_tool.py`, `hilclaw/case_tool.py`, `hilclaw/run_commit.py`, `hilclaw/tools.py` or their tests.
- The less-exact sentences listed in the Consequences of ADR-0133 and ADR-0135, apart from the `turn_definition.py` docstring of criterion 8 (D18 hold). Any edit to `ARCHITECTURE/`.
- `hilclaw/start_instance.py` and the other files of the open draft PR #186. The unlanded branch `claude/T-0361-*` (ADR-0132) is not taken from.

## Follow-ups

- Next P2-1 work (planner's view): the steps between the key store and the closing steps. The first that needs no unanswered HQ is round 0's bring-up and baseline. The planner decides whether a design record (OD-23) can cover it without HQ-0040 or the `sim.run`/`board.run` holder.

## Result
DONE (code mode). Language: no new layer-2 code; the change is layer-1 Markdown (`orchestration/round-manager.md`) plus a docstring correction in `hilclaw/turn_definition.py`.

- "Your run": two tool sentences added, `mcp__hilclaw__case_write` (ADR-0133 decision 6) and `mcp__hilclaw__round_end` (ADR-0135 decisions 2 and 6), each the only means of its write with the run id as `run_id`. The `state_write` sentence is narrowed to the first `STATE.json` of entry step 2 and the `"over"` of entry step 6 (ADR-0135 decision 1). Other bullets, "One round at most" and "The entry of a turn" unchanged.
- "The round steps": step 1 (`key.store`) unchanged. The explicit stop stays right after it, reworded to name "the steps between step 1 and the closing steps of round `<round>`" and to say no turn goes past it. The sentence that later slices replace the stop is kept. A new subsection "The closing steps of a round" gives `case.write` (round >= 1 only; a refusal is reported and the round goes on), `round.end` (go on to `run.commit` whether `over` or not; non-empty `reported_lines` reported; a failure is reported and ends the session with no retry, no other `STATE.json` write and no `run.commit`) and `run.commit` (failure reported; the session ends either way), with brief ADR citations.
- `hilclaw/turn_definition.py`: the "*The prompt*" bullet and the "Not done here" sentence corrected; no code change.
- Tests: no new test (no `hilclaw/` code change; rule ⑤). Local `pytest` 24707 passed, 725 skipped; `ruff check` and `ruff format --check` clean. No real `claude` started (D16).
- No runtime acceptance item added or closed; (xxv)/(xxvi) stay with HQ-0049, (xxix)/(xxx) with HQ-0051.
- Review: 2 rounds, Approve (round 1 Approve with two nits, both fixed: the docstring's comma splice and the round-0 case, and a line wrap). Observation left for a later slice (criterion 2 kept it out): "One round at most" says the session ends after the round-end write, while `run.commit` now follows it.
