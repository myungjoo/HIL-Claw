---
id: T-0388
title: Add the round-0 delegation step to the coder-driver and the moved stop to orchestration/round-manager.md (ADR-0141 decision 6, Consequences slice 4; PLAN P2-2)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-5, OD-23, OD-18, S0, S1]
dependsOn: [T-0384, T-0385, T-0386, T-0387]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
estimatedSize: {loc: 45, files: 2}
hq: []
---
## Why

ADR-0141 (T-0384, landed as 3815c42) works out the owner's form (T) for the first-case coder call (HQ-0040 answer, O1). Its Consequences list four code slices, to be done in order:

- Slice 1: the registry tool `coder.run`. Landed in T-0385 (PR #222, 90935b1).
- Slice 2: the turn session environment. Landed in T-0386 (PR #223, 1d83884).
- Slice 3: the agent definition `orchestration/agents/coder-driver.md`. Landed in T-0387 (PR #224, 72bc967).
- **Slice 4, this task**: "step 2 of 'The round steps' in `orchestration/round-manager.md` and the moved stop (decision 6), with its test".

This slice is part of PLAN P2-2. P2-2 is a checklist item, and its OD-23 part closes by the ADR path, so the D18 priority rule for work outside the checklist does not apply. P2-5 needs it: the first run's round 0 must reach the coder call. Today the Round-Manager stops after `key.store` in every round, so no turn ever delegates to the coder-driver, even though the coder-driver now exists.

Open HQs checked:

- HQ-0053 (slice (d): the container runtime and the coder's start) is not crossed. With the package's runtime, `coder.run` fails with `no_container_runtime` (ADR-0141 decision 3). The step reports that kind and stops.
- HQ-0056 (runtime acceptance items (xli) to (xliii)) and HQ-0042 (items (xii) and (xiii)) are neither added to nor closed.
- HQ-0041 (the coder's model and tokens) is not crossed. The step names no model, and ADR-0141 decision 6 says no token accounting waits here.
- HQ-0043 (whether a turn that is cut short commits) is not crossed. The step ends the session at the existing stop and adds no write.

Open PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None of them overlaps this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit) and §5 (task file format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md` (repository), "상시 규칙": comment minimisation, test rules ① to ⑤, the language policy, the code-mode branch and merge procedure (A-13), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`:
  - Status (lines 3-14);
  - decision 4, the bullet "The delegation must not end first" (line 66);
  - decision 5, the last bullet, on what the Round-Manager can call (around line 84);
  - decision 6 (lines 86-92);
  - Walk-through (lines 94-105);
  - Consequences, the code slices (lines 126-131).
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`: decision 2 (lines 37-42) and decision 6 (lines 70-75).
- `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md`: decisions 2 and 4 (lines 41-61).
- `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md`: decision 2 (lines 40-49).
- `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`: decision 5 (lines 59-63).
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`: decision 3 (lines 62-80), only the tuple `spec.write` accepts.
- `orchestration/round-manager.md`, the whole file (133 lines).
- `orchestration/agents/coder-driver.md`, the whole file: what the delegate expects in its message and what it reports.
- `hilclaw/turn_definition.py`, lines 1-72 (module docstring: the "*The prompt*" bullet, the roster, "Not done here", and the runtime acceptance paragraph).
- `tests/test_turn_definition.py`, lines 1-130 (names, `SOURCE`, the repository-definition tests) and lines 477-500 (the coder-driver tests).

## Acceptance Criteria

Language: no new layer-2 code. The change is layer-1 Markdown, a docstring correction in an existing Python module, and one test. State this in one line in the commit body and in `## Result`.

### "Your run" (`orchestration/round-manager.md`)

1. Add one sentence: use only the `Agent` tool to delegate to `coder-driver`, and only as step 2 says. Add one more sentence: do not call `mcp__hilclaw__spec_write` or `mcp__hilclaw__coder_run` yourself, and write no spec or kernel by any other means. Cite ADR-0126 decision 2 and ADR-0141 decisions 5 and 6. The prompt is what holds this rule until a P2-4 hook checks which agent makes the call (ADR-0141 decision 5). Leave every other bullet of "Your run" unchanged in substance.

### "The round steps" (`orchestration/round-manager.md`)

2. Step 1 (`key.store`) and its opening sentence stay as they are.
3. **Step 2, round 0 only**, follows step 1:
   - Delegate to `coder-driver` with the `Agent` tool and wait for its report.
   - The message names your run id and the tuple `round` 0, `candidate` 1, `attempt` 1. It names no place.
   - Cite ADR-0141 decision 6, ADR-0126 decision 6 and ADR-0123 decisions 2 and 4. Cite briefly, as the other steps do.
   - Whatever the coder-driver reports, report it in one line: a result with any `taken`, or any kind.
   - In that turn: delegate no second time, issue no call yourself, write no spec or kernel by any other means, and ask for no repair.
   - In rounds ≥ 1 there is no step 2.
4. **The moved stop.** The stop follows step 2 in round 0 and step 1 in every other round. It still reports in one line that the following steps of round `<round>` are not yet defined, and ends the session with nothing more written.
   - Reword the stop only as far as step 2 makes its present wording false.
   - It must stay plain that no turn goes past the stop, so the closing steps are not reached today.
   - Keep the sentence that later slices replace the stop with the remaining steps of a round, in substance.
5. "The closing steps of a round", "One round at most" and "The entry of a turn" stay unchanged. The "One round at most" wording about `run.commit` is a held follow-up (PLAN 보류, T-0370). Do not edit it.
6. Keep the file short and imperative:
   - Do not restate ADR-0141 or ADR-0126.
   - Add no step after the call: no checks of the attempt, no baseline run, no evaluator delegation.
   - Do not say what a kind or an empty `taken` means for the round (OD-19, PLAN P2-1).
   - Add no coder call in a round ≥ 1.
   - Name no model (HQ-0041), no time limit (OD-14) and no container (HQ-0053).
   - Put no run's data into the file (ADR-0118 decision 5).

### The docstring (`hilclaw/turn_definition.py`)

7. Correct the "*The prompt*" bullet in one sentence or less. It must say that in round 0 a turn delegates the coder call to the coder-driver after the key store, and that a turn ends after that step in round 0, or after the key store in other rounds.
8. Adjust the "Not done here" phrase "no round steps between the key store and the closing steps" only as far as it becomes false.
9. If the runtime acceptance paragraph is extended, it may name only items that ADR-0141 already states: (xlii), the foreground delegation.
10. No code change in this module.

### The test (`tests/test_turn_definition.py`)

11. Add the test that slice 4 names, against the repository's `orchestration/round-manager.md`:
    - **Happy:** the prompt names `coder-driver`, and `orchestration/agents/coder-driver.md` exists in `SOURCE`. Every agent the prompt delegates to then has a definition the session gets.
    - **Negative guard (the stop):** the prompt still holds the stop's "not yet defined" sentence. A slice that drops the stop without defining the steps after it fails the test.
    - **Negative guard (no call of its own):** the prompt never tells the Round-Manager to call `mcp__hilclaw__coder_run`. One way to check this: no "Use only `mcp__hilclaw__coder_run`" sentence appears. If the prompt names the tool, it does so only in the prohibition of criterion 1. The executor picks the exact check.
    - Do not pin any other wording.
12. Existing tests pass unchanged. This includes `tests/test_turn_permissions.py::test_the_real_definition` and `tests/test_turn_start.py`.

### Gates and procedure

13. Run the full suite locally: `pytest`, `ruff check` and `ruff format --check`. Then get CI green on the PR. `hilclaw/` coverage stays at or above 80 % line and 80 % function.
14. Size: within the D4 cap (≤ 300 non-test LOC, ≤ 5 files).
15. Code mode (A-13; `orchestration/` is not a doc-mode path):
    - work on branch `claude/T-0388-round-manager-coder-delegation-step`, with a Draft PR whose title contains `T-0388`;
    - run the reviewer cycle to Approve and get CI green;
    - squash-merge with the PR body as the squash message. Its last line is `Task: T-0388` (DRIVER §5);
    - delete the branch.
16. D16:
    - No `claude` process is started and no container is started. The stub `claude` of the existing tests is the only one.
    - No runtime acceptance item is added or closed. (xli) to (xliii) stay with HQ-0056, and (xii) and (xiii) with HQ-0042.

## Out of Scope

- Any edit of `ARCHITECTURE/`. The "Less exact, not edited" sentences of ADR-0141 Consequences are not edited, except the `hilclaw/turn_definition.py` docstring of criteria 7 to 9.
- `orchestration/agents/coder-driver.md`, `orchestration/agents/evaluator.md`, and any code of `hilclaw/` (`coder_tool.py`, `coder_call.py`, `spec_tool.py`, `tools.py`, `turn_loop.py`, `turn_permissions.py`, and the code of `turn_definition.py`).
- Slice (d): the real container runtime, image, sign-in, prompt or model of the coder (HQ-0053, HQ-0041).
- The steps after the call in round 0: the checks of the attempt, the baseline board run (ADR-0119), the evaluator (ADR-0128) and the round's end. These belong to later PLAN P2-1, P2-2 and P2-3 slices.
- A hook that checks which agent calls `coder.run` (PLAN P2-4).
- The "One round at most" wording (PLAN 보류, T-0370 follow-up).
- The files of open PR #186.

## Follow-ups

- Next for the planner: with the four slices of ADR-0141 done, see what PLAN P2-1/P2-2 need next for round 0 after the coder call, beginning with the checks of the attempt and the baseline. Check first whether the existing records already decide that step, or whether it waits on an HQ (for example T-0210/HQ-0021, the holder of `sim.run`/`board.run`).

## Result
