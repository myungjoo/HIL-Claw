---
id: T-0483
title: Add the experiment-runner definition and round-0 step 5 (the board measurement by `board.run`) with the go-on to the closing steps to orchestration/round-manager.md (ADR-0142 Consequences slice 2; PLAN P2-1)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-10, OD-23, OD-28, S0, S1, "PLAN P2-1"]
dependsOn: []
touchesFiles:
  - orchestration/agents/experiment-runner.md
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
  - tests/test_caller_check.py
estimatedSize: {loc: 110, files: 3}   # tests excluded from the cap (DRIVER §5, D4/D20)
hq: []
---
## Why

PLAN P2-1 is "Round-Manager 프롬프트·라운드 0(bring-up+baseline) 절차". It is the first unchecked item of P2 in the stated P2 order (P2-1 to P2-4, P2-6, P2-7, then P2-5). This is checklist work, so the D18 rule for work outside the checklist does not apply. P2-5 needs it: the first run gets no baseline until round 0 can end.

ADR-0142 (T-0389) decides what the Round-Manager does in round 0 of a first-case turn after the coder call (part of OD-23, closed for this scope through the DRIVER §9 path). Its Consequences list two code slices:

- **Slice 1 is on `main`** (T-0390, then T-0393 for the commit before each end). It added steps 3 and 4 (the sim-point and board-point checks delegated to the evaluator) and the stop of decision 7 after step 4.
- **Slice 2 is this task.** It adds:
  - `orchestration/agents/experiment-runner.md` (decision 4);
  - step 5, the board measurement delegated to the experiment-runner;
  - the go-on to "The closing steps of a round" in round 0 (decision 6), which replaces the stop of decision 7;
  - the prompt and docstring sentences and tests that go with these.

ADR-0142 decision 7 held slice 2 back until `board.run` is in `default_registry`. That condition now holds:

- ADR-0167 (T-0478) registered `sim.run` and `board.run` in `default_registry`.
- T-0482 bound the `cpu_standin` entry of the default backend table.
- `hilclaw/budget_check.py` already lists `mcp__hilclaw__board_run` in `SPENDING_TOOLS` (ADR-0167 decision 5; ADR-0147).

ADR-0167 decision 5 says: "the stop after step 4 stays until step 5 and the experiment-runner land (PLAN P2 work)".

No record leaves a design choice of this slice open, so no ADR is written. If you find one open, stop and return BLOCKED with the reason. Do not write an ADR beyond this task's scope.

Runtime acceptance: ADR-0142 items (xliv) to (xlvi) are already recorded in `PROCESS/RuntimeAcceptance.md` (RA-0026, moved from HQ-0057, task T-0389). Do not return them again. This task adds no new runtime acceptance item unless your change creates a fact that only a live session can confirm and that those items do not cover. If it does, name it in `## Result` for the driver (DRIVER §8, D22).

## Required Reading

Line numbers are those of `main` at `c9bd27f1`; the text wins. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 73: executor procedure, landed check, resume rule, time limit) and **§5** (lines 87-116: task format, naming, size cap D4/D20, trailers, the test rules D12, the pinning-list rule D21).
- CLAUDE.md, the whole file. Above all read these sections:
  - "개발 드라이버와 런타임의 구분": no `claude`, container or board is started on this machine, and tests use stubs only.
  - "테스트 규칙".
  - "브랜치·merge 절차": this task is code mode.
  - "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- **Records**:
  - ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md:
    - decisions 3 to 7 (lines 47-83);
    - Walk-through (85-101);
    - Consequences slice 2 (line 134) and the "Less exact" list (136-143).
  - ARCHITECTURE/decisions/ADR-0167-od18-run-tools-registration.md decision 5 (lines 60-66): how it reads ADR-0142 decision 7.
  - ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md decisions 2 and 7 (from line 37 and line 71): every end of the session after a successful entry step 0 calls `run.commit`; the stop's commit.
  - ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md decision 5: the coder-driver's definition is the model for the experiment-runner's (no `background` member, foreground delegation, judges nothing).
  - ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md decisions 3 to 5: the pre-approved list is derived from the agent files with no code change.
  - ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md decision 3 and its Walk-through row for "A future `orchestration/agents/experiment-runner.md`" (line 107): `board_run` is held by `experiment-runner` and refused to the Round-Manager, with no code change.
  - ARCHITECTURE/decisions/ADR-0106-od18-run-tools-request-schema.md decision 2 and ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md decision 3: the request members `run_id`, `round`, `candidate`, `attempt`, `execution`.
  - ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md decisions 2, 4 and 5: what makes the board-point run the baseline, and what stays open when there is none.
  - ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md decision 1: `case.write` is skipped in round 0.
- **Definition (whole)**:
  - `orchestration/round-manager.md`;
  - `orchestration/agents/coder-driver.md` (the model for the new file);
  - `orchestration/agents/evaluator.md`.
- **Code**:
  - `hilclaw/turn_definition.py`: the module docstring, lines 1-78. Its prompt bullet (lines 33-45) and its roster paragraph (lines 61-63) describe the definition, and both change.
  - `hilclaw/turn_permissions.py`: `ROUND_MANAGER_TOOLS` (line 96) and `holder_lists`. Read only; no code change is expected.
  - `hilclaw/caller_check.py` and `hilclaw/budget_check.py` (`SPENDING_TOOLS`, line 63). Read only.
  - `hilclaw/tools.py` `default_registry` (from line 182). Read only: `board.run` is served as `mcp__hilclaw__board_run`.
- **Tests (whole)**: `tests/test_turn_definition.py`, `tests/test_turn_permissions.py` (above all `test_the_real_definition`, line 260, and `test_holder_lists_the_real_definition`, line 401) and `tests/test_caller_check.py` (the fixture at line 47 puts the real definition).

## Acceptance Criteria

1. **The experiment-runner definition.** A new file `orchestration/agents/experiment-runner.md` follows ADR-0142 decision 4.
   - **Frontmatter**: exactly the keys `name`, `description` and `tools`.
     - `name` is `experiment-runner`.
     - `tools` is exactly `mcp__hilclaw__board_run`.
     - There is no `background`, `model` or other member.
     - No read tool, file tool, `Bash` or `Agent` is listed, and `mcp__hilclaw__sim_run` is not listed.
     - LF line endings, like `coder-driver.md`.
   - **Body**: the same sections as `coder-driver.md` (what you are given, fixed rule, your report). It states:
     - The delegation message names the run id and the tuple `round`, `candidate`, `attempt`, and no place.
     - Its inputs are that message and what its tool returns; it judges nothing.
     - It calls `mcp__hilclaw__board_run` **once**, with exactly `run_id`, `round`, `candidate`, `attempt` as given and `execution` 1.
     - It never calls it twice in one delegation, never retries and never states another `execution`.
     - It reports the result's `outcome`, with its `condition` when `outcome` is `"broken"`, or the failure kind, as the tool returned it.
     - It copies no interval or figure into its report and writes nothing by any means.
     - It says nothing of what an outcome or kind means for the round.
     - It ends with one final text message with one line per tool request, naming the tool, the run id and the tuple, as the coder-driver does.
   - Cite ADR-0142 decision 4 (and ADR-0106 decision 2, ADR-0062 decision 3) in the style of the other agent files.
2. **Step 5 in `orchestration/round-manager.md`**, "The round steps", per ADR-0142 decisions 4 and 6.
   - Step 4's go-on changes. When the evaluator's report gives the standing `"verified"` at `board`, go on to step 5. On any other report, come to the stop. The sentence that reports "the board measurement of round 0 waits on `board.run`" is removed.
   - New **step 5, round 0 only**:
     - Delegate to `experiment-runner` with the `Agent` tool and wait for its report. The message names the run id and the tuple `round` 0, `candidate` 1, `attempt` 1, and no place.
     - Report what it reports in one line.
     - When the report gives `outcome` `"converged"` or `"not_converged"`, go to "The closing steps of a round". In round 0 that means no `case.write`, then `round.end`, then `run.commit`.
     - On `"broken"`, a failure kind, or no report it can read, come to the stop. Round 0 is not ended.
     - Cite ADR-0142 decisions 4 and 6 and ADR-0119 decisions 2 and 4.
   - **The stop** paragraph changes:
     - In round 0 the stop follows step 2, 3, 4 or 5 as they say. In other rounds it still follows step 1 ("not yet defined" stays for rounds ≥ 1).
     - "No turn goes past this stop, so no turn reaches the closing steps below" is rewritten. A round-0 turn reaches the closing steps through step 5. No turn of a round ≥ 1 reaches them yet.
     - The stop's `run.commit` and "Round 0 is not ended: no `round.end`" stay as they are (ADR-0143 decisions 2 and 7).
     - "Later slices of the definition replace this stop with the remaining steps of a round" stays true for rounds ≥ 1. Keep it, narrowed to rounds ≥ 1.
   - "The closing steps of a round": rewrite its first sentence ("reached only once later slices define the steps before them"). Round 0 reaches them after step 5. Rounds ≥ 1 reach them only once later slices define their steps.
   - "Your run":
     - Widen the `Agent` bullet to the `experiment-runner` delegation of step 5.
     - Add "Do not call `mcp__hilclaw__board_run` yourself" (ADR-0142 decision 4, the limit of ADR-0139 decision 5).
     - Every sentence of the prompt that names `board_run` is that prohibition. `sim_run` is named nowhere.
   - The "The end of a session" list of ends ("the ends of entry steps 2, …, the stop, and a failed `round.end` in closing step 2") stays correct. Check it, and change it only if the new step makes it wrong.
   - Use no wording that the records do not support. Where the prompt now cites a decision, cite the record and decision number.
3. **`hilclaw/turn_definition.py` docstring.**
   - Update the *prompt* bullet. In round 0, after the board-point check, the turn delegates the board measurement to the experiment-runner. On a completed result it goes to the closing steps; otherwise it stops. In other rounds the later steps are not yet defined.
   - Update the roster paragraph: `orchestration/agents/` holds the evaluator's, the coder-driver's and the experiment-runner's definitions (ADR-0142 decision 4).
   - Update the "Not done here" sentence: "the board-point check in round 0" is no longer the last defined step of round 0.
   - No code of the module changes.
4. **No code change elsewhere.** Do not change these:
   - `hilclaw/turn_permissions.py`;
   - `hilclaw/caller_check.py`;
   - `hilclaw/budget_check.py`;
   - `hilclaw/tools.py`;
   - `hilclaw/turn_loop.py`;
   - any `hilclaw/` code.

   The derivation and the caller check take the new file up as it is (ADR-0139 decision 3; ADR-0146 decision 3). If a test shows otherwise, stop and return BLOCKED with the reason.
5. **Tests.** This is code mode, and the D12 rules apply to the tests it changes. The test files are not counted in the size cap.
   - `tests/test_turn_definition.py`. Add these:
     - **Experiment-runner frontmatter**, like `test_the_coder_driver_frontmatter`:
       - the key set is exactly `name`, `description`, `tools`;
       - `name` is `experiment-runner`;
       - `tools` is exactly `{"mcp__hilclaw__board_run"}`;
       - every `mcp__hilclaw__` name is served by `default_registry` (`served_names()`);
       - no `Bash`/`Read`/`Grep`/`Glob`/`Write`/`Edit`/`Agent`, no `mcp__hilclaw__sim_run`;
       - no `\r`.
     - **Experiment-runner body**: it names `outcome`, `condition`, `execution` and the one-call rule.
     - **Step 5 in the prompt** (positive):
       - `experiment-runner` is named;
       - the file exists;
       - step 5 names `"converged"`, `"not_converged"` and `"broken"`;
       - step 5 leads to the closing steps;
       - `board_run` appears only in a sentence that starts with "Do not call " (use `only_forbidden`).
     - **Negative/branch cases**:
       - `sim_run` appears nowhere in the prompt;
       - "waits on `board.run`" no longer appears;
       - rounds ≥ 1 still stop after step 1 ("not yet defined" remains);
       - the stop still commits and still leaves round 0 not ended.
   - **Pinning assertions you will touch** (DRIVER §5 D21 allows these edits as far as they reflect the new agent file and the new step). List them in the PR body:
     - `test_the_repository_definition_by_default`: the copied tree gains `.claude/agents/experiment-runner.md`.
     - `test_the_repository_definition_holds_the_prompt_and_the_two_agents`: the agent list gains `experiment-runner.md`. Renaming the test to say three agents is allowed.
     - `test_holder_lists_the_real_definition` in `tests/test_turn_permissions.py`: `set(found)` gains `"experiment-runner"`. Add an assertion `found["experiment-runner"] == ("mcp__hilclaw__board_run",)`.
     - `test_the_real_definition` in `tests/test_turn_permissions.py`: add assertions that `Agent(experiment-runner)` and `mcp__hilclaw__board_run` are in the allowed list. The built-in set stays `"Agent,Glob,Grep,Read"`.
   - **Assertions that pin the old prompt text.** These change because the slice replaces the text they pin, as ADR-0142 Consequences slice 2 says. They are not pinning lists, so state each change and its reason in the PR body:
     - `test_the_prompt_names_no_measurement_step` becomes a test that the prompt names `board_run` only in the prohibition and names no `sim_run`.
     - `test_the_prompt_reaches_no_closing_steps_yet` follows the rewritten first sentence of the closing steps.
     - `test_the_stop_commits_and_leaves_round_0_open` follows the rewritten stop paragraph. The helper `the_stop()` may need a new end marker.

     Every other existing assertion of these files stays as it is.
   - `tests/test_caller_check.py`: add a test with the real definition put by the existing fixture:
     - a `mcp__hilclaw__board_run` call by the agent type `experiment-runner` is let through;
     - the same call from the main session (no agent id/type) is refused;
     - the same call by `evaluator` or `coder-driver` is refused.
   - Run the full local suite (`pytest`), `ruff check` and `ruff format --check`. CI must be green before the squash-merge.
6. **Result.** In `## Result`, write these:
   - the language (Markdown for the definition; the docstring is Python);
   - every prompt sentence you rewrote, quoted briefly, with the decision it follows;
   - the test assertions you changed (as listed in the PR body);
   - any record sentence that this slice makes less exact but that you did not edit. Candidates you should check, not edit:
     - ADR-0142 decision 7 and its Walk-through row "`board.run` is not registered (today)";
     - ADR-0143 decision 7, "round steps 2 to 4";
     - ADR-0146 decision 3 / item list on ADR-0142 decision 4.

## Out of Scope

- **Any step of a round ≥ 1.** Those steps are the rest of P2-1, and they need ADR-0132 slices 1 and 2 (P2-6) and a record of the round ≥ 1 steps. Rounds ≥ 1 keep the stop after step 1.
- Any `sim.run` step or `mcp__hilclaw__sim_run` grant (ADR-0142 decision 5). Any write of `sim.json`, `board.json` or `build.json` (ADR-0142 decision 4, "The `measure/` role").
- Any retry, repair, triage or termination rule for a round 0 without a baseline (OD-19, OD-10, OD-17; ADR-0119 decision 5).
- An end-to-end test of a whole round 0 through a stub `claude` (ADR-0142 Walk-through, last row). That is P2-5's verification and not this slice.
- Editing any ADR, `ARCHITECTURE/` file, `README.md`, `.claude/settings.json` or `.claude/settings.local.json`.
- Starting `claude`, Docker or `clang` on this machine (D16).

## Follow-ups

- (planner) The next P2-1 work needs P2-6 first: ADR-0132 slices 1 and 2 (the tool `hypotheses.write` and `orchestration/agents/technique-selector.md`). After those, a record of the Round-Manager's round ≥ 1 steps can follow (ADR-0132 slice 3, ADR-0151, ADR-0140).

## Result

- **Outcome**: DONE. PR #297 was squash-merged as `39f004ad` (branch deleted). Review: 1 round, Approve. The reviewer left two Nits. Nit 1 (redundant parentheses in a test) was fixed after the Approve; under the D20 Nit exception it was not re-reviewed. Nit 2 (optional docstring mention of RA item (xliv)) was not taken. CI was green on the final commit, and the local full `pytest`, `ruff check` and `ruff format --check` passed.
- **Language**: Markdown for the layer-1 definition (`orchestration/agents/experiment-runner.md`, `orchestration/round-manager.md`). The `hilclaw/turn_definition.py` change is a Python docstring only; no code changed.
- **Prompt sentences rewritten or added** (`orchestration/round-manager.md`):
  - "Your run": "Use only the `Agent` tool to delegate to `coder-driver`, to `evaluator` and to `experiment-runner`, and only as steps 2, 3, 4 and 5 …" follows ADR-0142 decision 4. Added: "Do not call `mcp__hilclaw__board_run` yourself (ADR-0142 decision 4; ADR-0139 decision 5)." This is the only sentence that names `board_run`, and `sim_run` appears nowhere.
  - Step 4: "Go on to step 5 only when it gives the standing `"verified"` at `board` (ADR-0142 decision 3)." It replaces "report … waits on `board.run` … (ADR-0142 decision 7)".
  - Step 5 (new, round 0 only) delegates to `experiment-runner` with the tuple 0/1/1 and no place. It reports in one line.
    - On `"converged"`/`"not_converged"` it goes to the closing steps: no `case.write`, then `round.end`, then `run.commit` (ADR-0142 decisions 4 and 6; ADR-0119 decisions 2 and 4; ADR-0133 decision 1).
    - On `"broken"`, a failure kind or an unreadable report it comes to the stop (ADR-0142 decision 6; ADR-0119 decision 5).
  - The stop:
    - "in round 0 it follows step 2, 3, 4 or 5 … (ADR-0143 decision 7; ADR-0142 decision 6)";
    - "Round 0 is not ended: no `round.end` (ADR-0142 decisions 1, 2 and 6)";
    - "A round-0 turn reaches the closing steps below only through step 5; no turn of a round ≥ 1 reaches them yet." This replaces "No turn goes past this stop …";
    - "Later slices of the definition replace this stop in rounds ≥ 1 …".
  - Closing steps, first sentence: "These steps follow the round's last other step. Round 0 reaches them after step 5 (ADR-0142 decision 6); rounds ≥ 1 reach them only once later slices define their steps."
  - The list in "The end of a session" was checked and is unchanged; it is still correct.
- **Test assertions changed** (as listed in the PR body):
  - D21 pinning lists:
    - `test_the_repository_definition_by_default`: the copied tree gains `.claude/agents/experiment-runner.md`.
    - `test_the_repository_definition_holds_the_prompt_and_the_three_agents`: renamed from `_two_agents`, and the agent list gains the new file.
    - `test_holder_lists_the_real_definition`: `set(found)` gains `experiment-runner`, and an assertion of its tool tuple is added.
    - `test_the_real_definition`: `Agent(experiment-runner)` and `mcp__hilclaw__board_run` are now asserted allowed; the built-in set is unchanged.
  - Old-text assertions:
    - `test_the_prompt_names_no_measurement_step` became `test_the_prompt_names_board_run_only_in_the_prohibition`.
    - `test_the_prompt_reaches_no_closing_steps_yet` became `test_the_prompt_reaches_the_closing_steps_from_round_0_only`.
    - `test_the_stop_commits_and_leaves_round_0_open`: "No turn goes past this stop" is now asserted absent, and the new wording is asserted.
    - `test_the_prompt_keeps_the_stop_in_later_rounds`: assertions were added.
  - New tests: the experiment-runner frontmatter and body, step 5, the step-4 go-on, and the caller check with the real definition (`test_the_real_experiment_runner_holds_board_run`).
- **Records made less exact, not edited**:
  - ADR-0142 decision 7 ("While `board.run` is not in `default_registry`, the round-0 steps end with step 4") and its Walk-through row "`board.run` is not registered (today)": the stop after step 4 is replaced by step 5.
  - ADR-0143 decision 7 ("round steps 2 to 4") now reads as steps 2 to 5. Its Walk-through row "Round-0 turn that stops after step 4 (board standing, `board.run` not registered)" is affected too.
  - ADR-0146: the Walk-through row "A future `orchestration/agents/experiment-runner.md`" (line 107) is no longer future. The "less exact" item on ADR-0142 decision 4 (line 149) now holds, since both slices have landed.
  - ADR-0167 decision 5 ("the stop after step 4 stays until step 5 and the experiment-runner land") is now past.
  - ADR-0141 decision 6 and Boundaries ("the steps after the call in round 0" left open), for round 0.
- **Runtime acceptance**: none new. ADR-0142 (xliv) to (xlvi) are already in RA-0026.
- **Follow-ups**: none beyond the task's own (the next P2-1 work needs P2-6 first).
