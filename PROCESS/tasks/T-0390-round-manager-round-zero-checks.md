---
id: T-0390
title: Add the round-0 checks (steps 3 and 4) and the stop after the board-point check to orchestration/round-manager.md (ADR-0142 Consequences slice 1; PLAN P2-1/P2-2)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-9, OD-23, OD-16, S0, S1]
dependsOn: [T-0388, T-0389]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
estimatedSize: {loc: 50, files: 2}
hq: []
---
## Why

ADR-0142 (T-0389, landed on main as cd4879b) decides what the Round-Manager does in round 0 of a first-case turn after the coder call (part of OD-23). Its Consequences list two code slices, in order:

- **Slice 1, this task ("now")**: in "The round steps" of `orchestration/round-manager.md`, the go-on condition of decision 2 after step 2, steps 3 and 4 (decision 3) with their conditions, and the stop of decision 7 after step 4; with the test that pins the present stop, the "Your run" `Agent` bullet and the `hilclaw/turn_definition.py` docstring.
- Slice 2 (not this task): `orchestration/agents/experiment-runner.md`, step 5 and the go-on to the closing steps. It waits until PLAN P1-1 registers `board.run` in `default_registry` (T-0210/HQ-0021, unresolved).

This is PLAN checklist work (P2-1 Round-Manager round 0; P2-2 OD-23 part, closed for this scope by ADR-0142 through the DRIVER §9 path), so the D18 rule for work outside the checklist does not apply. P2-5 needs it: the first run's round 0 must check its attempt at both points before a baseline can exist (ADR-0119 decision 4). Slice 1 needs nothing unregistered (ADR-0142 decision 7, "This depends on nothing unlanded").

Open HQs checked:

- HQ-0021 (T-0210, `sim.run`/`board.run` registration): not crossed. This slice names no `board_run` or `sim_run` anywhere; step 5 and the experiment-runner are slice 2.
- HQ-0026 / OD-14 ①: no backend of `correctness.check` is presumed. With the package's registry a `cpu_standin` check answers `no_backend`/`not_offered`, the standing is `"undetermined"`, and step 3 stops (ADR-0142 decision 7).
- HQ-0053 (slice (d), the coder's container): not crossed. With the package's runtime `coder.run` fails with `no_container_runtime` and decision 2 stops.
- HQ-0043 (commit at the end of a turn that stops; answered (a), record not yet made): not crossed. The stops add no write and no commit (ADR-0142 decision 1, "The stop").
- HQ-0057 ((xliv)-(xlvi)), HQ-0056, HQ-0042 and the other runtime-acceptance HQs: nothing is added or closed.

Open PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None overlaps this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit) and §5 (task file format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md` (repository), "상시 규칙": comment minimisation, test rules ① to ⑤, the language policy, the code-mode branch and merge procedure (A-13), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md`:
  - Context, "The stop" and "The agents" (lines 22-23);
  - decision 1, the bullet "The stop" (line 39);
  - decision 2 (lines 41-45);
  - decision 3 (lines 47-53);
  - decision 4, the last bullet on the permission lists (line 64), only to see what slice 2 adds and this slice does not;
  - decision 7 (lines 79-83);
  - Walk-through (lines 85-101);
  - Alternatives, the (b) row "The Round-Manager calls `checks.read` itself" and the (f) rows (lines 103-129);
  - Consequences, the code slices (lines 132-134).
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: decision 2 (lines 35-42), decision 4 (lines 51-55) and decision 7 (lines 76-80).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`: decision 7 (lines 83-87).
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`: decision 6 (lines 86-92).
- `orchestration/round-manager.md`, the whole file (145 lines).
- `orchestration/agents/evaluator.md`, "What you are given", "Fixed rules" and "A check": what the delegate expects and reports.
- `hilclaw/turn_definition.py`, lines 1-72 (module docstring: the "*The prompt*" bullet, the roster, "Not done here", the runtime acceptance paragraph).
- `tests/test_turn_definition.py`, lines 1-130 (names, `SOURCE`, `PROMPT`) and lines 477-511 (the coder-driver tests and `test_the_prompt_delegates_to_the_coder_driver_and_keeps_the_stop`).

## Acceptance Criteria

Language: no new layer-2 code. The change is layer-1 Markdown, a docstring correction in an existing Python module, and tests. State this in one line in the commit body and in `## Result`.

### "Your run" (`orchestration/round-manager.md`)

1. Widen the `Agent` bullet to the delegations of steps 3 and 4: use only the `Agent` tool to delegate to `coder-driver` and to `evaluator`, and only as steps 2, 3 and 4 say. Keep its prohibition on `mcp__hilclaw__spec_write` and `mcp__hilclaw__coder_run` as is. The executor may add, citing ADR-0128 decision 2 and ADR-0142 decision 3, that the Round-Manager does not call `mcp__hilclaw__correctness_check` or `mcp__hilclaw__checks_read` itself. If it does, it uses the same "Do not call …" form as the existing prohibition.
2. Name no `mcp__hilclaw__board_run`, `mcp__hilclaw__sim_run` or `experiment-runner` anywhere in the file. The prohibition "Do not call `mcp__hilclaw__board_run` yourself" belongs to slice 2 (ADR-0142 Consequences). Leave every other bullet of "Your run" unchanged in substance.

### "The round steps" (`orchestration/round-manager.md`)

3. Step 1 (`key.store`) and its opening sentence stay as they are.
4. **Step 2** stays, except as far as decision 2 makes it false. It still reports the coder-driver's report in one line. Then add decision 2's condition: go on to step 3 only when the report is a result of `coder.run` whose `taken` holds at least one name. On every other report — any failure kind (`spec_exists` and `no_container_runtime` among them), an empty `taken`, or no report it can read — come to the stop. Do not say what a kind or an empty `taken` means for the round (ADR-0141 decision 6; OD-19).
5. **Step 3, round 0 only.** Delegate to `evaluator` with the `Agent` tool and wait for its report. The message names your run id, the tuple `round` 0, `candidate` 1, `attempt` 1, the point `sim`, and no place. Name no `execution` (the evaluator states 1). Cite ADR-0142 decision 3 and ADR-0128 decisions 4 and 7, briefly, as the other steps do.
6. **Step 4, round 0 only.** The same with the point `board`. Step 4 follows step 3 only when the evaluator reports the standing `"verified"` at `sim`. Any other report — `"not_verified"`, `"undetermined"`, a failure kind without a standing, or no report it can read — comes to the stop.
7. **The stop of decision 7.** When step 4's evaluator report gives the standing `"verified"` at `board`, report in one line that the board measurement of round 0 waits on `board.run`, and end the session. Any other report at step 4 comes to the stop.
8. **The stop sentence, rewritten for round 0.** In round 0 the stop follows steps 2, 3 or 4 under the conditions above. In rounds ≥ 1 it stays after step 1, with the present report that the following steps of round `<round>` are not yet defined. In every case the stop ends the session and writes nothing further. Round 0 is not ended, so no `round.end` and no `run.commit` (ADR-0142 decisions 1 and 2). It must stay plain that no turn reaches the closing steps today. Keep, in substance, the sentence that later slices replace the stop with the remaining steps.
9. "The closing steps of a round", "One round at most" and "The entry of a turn" stay unchanged. Their first sentence ("reached only once later slices define the steps before them") is rewritten only by slice 2. The "One round at most" wording is a held follow-up (PLAN 보류, T-0370). Do not edit it.
10. Keep the file short and imperative:
    - do not restate ADR-0142, ADR-0128 or ADR-0119;
    - add no step 5, no measurement, no `profiler.collect`, no verdicts delegation and no `case.write` in round 0;
    - add no retry, repair, second delegation per point, or another `execution`;
    - do not read `checks.read` or the log yourself: the standing comes from the evaluator's report (ADR-0131 decision 7; ADR-0142 decision 3);
    - add no step to rounds ≥ 1;
    - put no run's data into the file (ADR-0118 decision 5).

### The docstring (`hilclaw/turn_definition.py`)

11. Correct the "*The prompt*" bullet so it is true again, in at most two sentences. It must say that in round 0, after the coder-driver delegation, a turn whose call brought something in delegates the sim-point and then the board-point check to the evaluator, and ends after the board-point check. Other rounds still end after the key store.
12. Adjust "Not done here" ("no round steps between the last defined step … and the closing steps") only as far as it becomes false.
13. The runtime acceptance paragraph is not extended, or it names only items ADR-0128 or ADR-0142 already state. No code change in this module.

### The tests (`tests/test_turn_definition.py`)

14. Replace or rename `test_the_prompt_delegates_to_the_coder_driver_and_keeps_the_stop` as slice 1 says. It must keep its coder-driver guards (the prompt names `coder-driver`; its definition exists in `SOURCE`; `mcp__hilclaw__coder_run` appears only in a "Do not call" sentence). It no longer pins the present round-0 stop wording.
15. Add tests against the repository's `orchestration/round-manager.md`:
    - **Happy:** the prompt names `evaluator`, and `orchestration/agents/evaluator.md` exists in `SOURCE`. The prompt names both points, `sim` and `board`.
    - **Branch:** the prompt still holds a stop for rounds ≥ 1 ("not yet defined").
    - **Negative guard (slice 2 not leaked):** the prompt names neither `board_run`, `sim_run` nor `experiment-runner`. A change that lands step 5 without the tool's registration fails the test.
    - **Negative guard (no check of its own):** if the prompt names `mcp__hilclaw__correctness_check` or `mcp__hilclaw__checks_read`, it does so only in a "Do not call …" sentence.
    - **Negative guard (no round end in round 0 today):** the closing steps are not presented as reachable. The executor picks a check that does not pin wording beyond this, for example that the closing-steps section keeps its "reached only once later slices" qualifier.
    - Pin no other wording.
16. Existing tests pass unchanged, except the one of criterion 14. This includes `tests/test_turn_permissions.py::test_the_real_definition` and `tests/test_turn_start.py`. No agent file changes, so the derived permission list is unchanged.

### Gates and procedure

17. Run the full suite locally: `pytest`, `ruff check` and `ruff format --check`. Then get CI green on the PR. `hilclaw/` coverage stays at or above 80 % line and 80 % function.
18. Size: within the D4 cap (≤ 300 non-test LOC, ≤ 5 files).
19. Code mode (A-13; `orchestration/` is not a doc-mode path):
    - work on branch `claude/T-0390-round-manager-round-zero-checks`, with a Draft PR whose title contains `T-0390`;
    - run the reviewer cycle to Approve and get CI green;
    - squash-merge with the PR body as the squash message, its last line `Task: T-0390` (DRIVER §5);
    - delete the branch.
20. D16:
    - No `claude` process is started and no container is started. The stub `claude` of the existing tests is the only one.
    - No runtime acceptance item is added or closed. (xliv)-(xlvi) stay with HQ-0057, (xviii)-(xx) with their HQ.

## Out of Scope

- Any edit of `ARCHITECTURE/`. The "Less exact, not edited" sentences of ADR-0142 Consequences are not edited, except the `hilclaw/turn_definition.py` docstring of criteria 11 to 13.
- Slice 2 of ADR-0142: `orchestration/agents/experiment-runner.md`, step 5, the go-on to the closing steps, the closing-steps first sentence, and the `board_run` prohibition. All of it waits for `board.run` in `default_registry` (PLAN P1-1; T-0210/HQ-0021).
- `orchestration/agents/evaluator.md`, `orchestration/agents/coder-driver.md`, and any code of `hilclaw/` (`tools.py`, `turn_permissions.py`, `turn_loop.py`, `checks_tool.py`, and the code of `turn_definition.py`).
- The commit at the end of a turn that stops (HQ-0043 (a); widening ADR-0127 decision 8 and `run.commit`, a separate record).
- A hook that checks which agent calls a tool (PLAN P2-4).
- The "One round at most" wording (PLAN 보류, T-0370 follow-up).
- The files of open PR #186.

## Follow-ups

- Next for the planner: slice 2 of ADR-0142 waits on `board.run` registration (P1-1, T-0210/HQ-0021). Until that HQ is answered, see what else PLAN P2-1/P2-2/P2-3/P2-6 need for P2-5. One candidate is the separate record that carries out the owner's HQ-0043 (a) answer (the commit at the end of a turn that stops, widening ADR-0127 decision 8 and `run.commit`).
- For the slice that lands step 5: the tests of criterion 15 that guard against `board_run`/`experiment-runner` must then be changed with it.

## Result

- Outcome: DONE. PR #226 squash-merged as 653c7a7 after 3 review rounds (round 1 Request changes: no one-line report at the step-3/4 stops, docstring typo; round 2 Approve with a nit, addressed; round 3 Approve). CI green on head 93fbdd4; local full suite 25589 passed, 736 skipped; ruff check/format clean; `hilclaw/` coverage 97 % line.
- `orchestration/round-manager.md`: "Your run" `Agent` bullet widened to `coder-driver` and `evaluator` (steps 2-4), plus "Do not call `mcp__hilclaw__correctness_check` or `mcp__hilclaw__checks_read` yourself"; step 2 go-on condition (ADR-0142 decision 2); steps 3 and 4 (decision 3), each reporting the evaluator's report in one line; the stop of decision 7 after "verified" at `board`; the stop sentence rewritten (round 0 after steps 2/3/4, rounds >= 1 after step 1 with "not yet defined"; no `round.end`, no `run.commit`). No `board_run`, `sim_run` or `experiment-runner`; closing steps, "One round at most" and the entry unchanged.
- `hilclaw/turn_definition.py`: docstring "*The prompt*" and "Not done here" corrected; runtime acceptance paragraph unchanged; no code change.
- `tests/test_turn_definition.py`: `test_the_prompt_delegates_to_the_coder_driver_and_keeps_the_stop` renamed to `test_the_prompt_delegates_to_the_coder_driver` (coder-driver guards kept, stop wording dropped); new tests for the evaluator delegation and both points, the later-round stop, no slice-2 names, the "Do not call" form for the check tools, and the closing-steps qualifier.
- Language: no new layer-2 code; layer-1 Markdown, a docstring correction in an existing Python module, and Python tests.
- D16: no `claude` process or container started; no runtime acceptance item added or closed.
- Follow-up: as in the task's Follow-ups (slice 2 waits on `board.run` registration, T-0210/HQ-0021; its slice must change `test_the_prompt_names_no_measurement_step`).
