---
id: T-0387
title: Add the coder-driver definition orchestration/agents/coder-driver.md of ADR-0141 decision 5, with its tests and the turn_permissions/turn_definition docstrings (ADR-0141 Consequences slice 3; PLAN P2-2)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-5, OD-23, OD-18, NFR-4, S0, S1]
dependsOn: [T-0384, T-0385, T-0386]
touchesFiles:
  - orchestration/agents/coder-driver.md
  - hilclaw/turn_permissions.py
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
estimatedSize: {loc: 90, files: 3}
hq: []
---
## Why

ADR-0141 (T-0384, landed on `main` as 3815c42) builds out the owner's form (T) for the first-case coder call: one registry tool `coder.run`, the turn session's environment, a `coder-driver` sub-agent with exactly `spec.write` and `coder.run`, and a round-0 delegation step of the Round-Manager. Its Consequences list four code slices, in order:

- Slice 1, the registry tool `coder.run` (`hilclaw/coder_tool.py`, registered in `default_registry`), landed in T-0385 (PR #222, 90935b1).
- Slice 2, the turn session environment in `hilclaw/turn_loop.py`, landed in T-0386 (PR #223, 1d83884).
- **Slice 3, this task**: the agent definition `orchestration/agents/coder-driver.md` (decision 5) with its test, and the `hilclaw/turn_permissions.py` docstring.
- Slice 4 (next task): step 2 of "The round steps" in `orchestration/round-manager.md` and the moved stop (decision 6).

This is a PLAN P2-2 checklist item (OD-23 closed by ADR path), so the D18 priority rule does not apply. The definition is copied into every turn session by `hilclaw.turn_definition.put` (`LAYOUT` maps `agents` to `.claude/agents`), and `hilclaw.turn_permissions.options` derives `Agent(coder-driver)` and the two MCP entries from it with no code change (ADR-0141 decision 5, last bullet; ADR-0139 decision 9 "(T)" branch). The task also fixes the `hilclaw/turn_definition.py` docstring sentence "The roster: `orchestration/agents/` holds the evaluator's definition", which becomes false when a second agent file lands.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md` (repository): "상시 규칙" (comment minimisation, test rules, language policy, branch/merge procedure A-13) and "개발 드라이버와 런타임의 구분" (D16).
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`: Status (lines 3-14), decision 4's bullet "The delegation must not end first" (line 66), decision 5 (lines 74-84), decision 6 (lines 86-92, for context only — slice 4), Consequences slices and the "Less exact, not edited" list (lines 126-140).
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`: decision 2 (lines 37-42) and decision 6 (lines 70-75).
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`: decision 3 (lines 62-80), the `spec.write` order and its kinds.
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`: decisions 3-5 (lines 59-80) and decision 9 (lines 100-104).
- `orchestration/agents/evaluator.md` (whole file): the form an agent definition of this repository takes (frontmatter keys, sections, how it cites decisions).
- `hilclaw/turn_permissions.py` lines 1-70 (module docstring: the accepted frontmatter form and the "Not done here" paragraph).
- `hilclaw/turn_definition.py` lines 55-70 (the "The roster" sentence and the runtime acceptance paragraph).
- `hilclaw/coder_tool.py` (the tool description: request members, result `taken`/`scratch_removed`, kinds) and the `DESCRIPTION` of `hilclaw/spec_tool.py` (including `spec_exists`).
- `tests/test_turn_definition.py` lines 1-160 (`EVALUATOR`, `EVALUATOR_TOOLS`, `test_the_repository_definition_by_default`, `test_the_repository_definition_holds_the_prompt_and_the_evaluator`, `frontmatter`, `test_the_evaluator_frontmatter`).
- `tests/test_turn_permissions.py` lines 1-60, 149-160 and 236-247 (`test_the_evaluator`, `test_the_real_definition`); `tests/test_turn_start.py` lines 560-580 (asserts `Agent(evaluator)` is in the list — must keep passing unchanged).

## Acceptance Criteria

1. **The file** `orchestration/agents/coder-driver.md` exists, UTF-8 text with LF line ends, in the form `hilclaw.turn_permissions` accepts. Its frontmatter has exactly the keys `name`, `description` and `tools`: `name: coder-driver`; a one-line `description` saying the Round-Manager delegates the round-0 coder call of a first-case turn to it; `tools: mcp__hilclaw__spec_write, mcp__hilclaw__coder_run` (exactly these two, this order or any). No `background`, `model`, `permissionMode` or any other key (ADR-0141 decision 5: no `background` member; ADR-0139: no `permissionMode`). No `Bash`, no file tool, no read tool (`Read`, `Grep`, `Glob`) and no `Agent`.
2. **The body** states, citing the decisions as `evaluator.md` does (decision numbers, no restatement beyond what the agent needs):
   - what it is given: the delegation message names the run id and the tuple (`round`, `candidate`, `attempt`) and no place (ADR-0126 decision 6);
   - the fixed rule of ADR-0141 decision 5, items 1-5: call `mcp__hilclaw__spec_write` with the run id and tuple; if it succeeds, call `mcp__hilclaw__coder_run` once with the same run id and tuple and report its result (`taken`, `scratch_removed`) or its kind; if `spec.write` fails with any kind but `spec_exists`, request no call and report the kind; if it fails with `spec_exists`, request no call and report the kind — marked as the interim rule of ADR-0141 decision 5, not an answer to OD-8 ㉖ (가) or OD-23 ① (가); never call either tool twice in one delegation, never retry, code nothing, write nothing of the run by any other means (ADR-0126 decisions 2 and 6);
   - what it reports: one report to the Round-Manager carrying the tool result or the kind as the tool returned it, with no judgement of what the kind means for the round (open: OD-19, PLAN P2-1).
   It invents nothing ADR-0141, ADR-0126 or ADR-0138 does not decide: no time limit, no container, image, sign-in or prompt of the coder (slice (d), HQ-0053), no step after the call.
3. **`tests/test_turn_definition.py`**: a `CODER_DRIVER` name and `CODER_DRIVER_TOOLS` set beside `EVALUATOR`/`EVALUATOR_TOOLS`; `test_the_repository_definition_by_default` expects `.claude/agents/coder-driver.md` with the source bytes; the repository-listing test (rename it to match) expects `agents/` to hold exactly the two files; a new frontmatter test for the coder-driver asserting: keys exactly `{name, description, tools}`, `name == "coder-driver"`, a non-empty description, no repeated tool, tools exactly `CODER_DRIVER_TOOLS`, every `mcp__hilclaw__` entry served by `default_registry` (as the evaluator test does), and none of `Bash`, `Read`, `Grep`, `Glob`, `Write`, `Edit`, `Agent` among them; a text test asserting the body names `spec_exists`, `taken` and `scratch_removed` (negative guard against a rule that drops item 4 or the report).
4. **`tests/test_turn_permissions.py`**: `test_the_real_definition` additionally asserts `Agent(coder-driver)`, `mcp__hilclaw__spec_write` and `mcp__hilclaw__coder_run` are in the pre-approved list, and that the built-in set stays `"Agent,Glob,Grep,Read"` (the coder-driver adds no built-in tool, ADR-0141 decision 5). Add a fixture-based test (a written coder-driver frontmatter text, not the repository file) for happy derivation of exactly `{*FIXED, "Agent(coder-driver)", spec_write, coder_run}`, and a negative test that the same file with `Bash` added to its `tools` is refused with the existing fixed text (the coder-driver keeps no shell — O1). `tests/test_turn_start.py` passes unchanged.
5. **`hilclaw/turn_permissions.py` docstring**: the "Not done here" sentence "the coder-driver's entry (ADR-0139 decision 9, HQ-0040) — a `Bash` entry is refused" is rewritten so that it is accurate: the coder-driver's entry is derived with no change under form (T) (ADR-0141 decision 5), and a `Bash` entry is still refused. If the runtime acceptance paragraph is extended, it names only items ADR-0141 or ADR-0139 already state. No code change in this module.
6. **`hilclaw/turn_definition.py` docstring**: "The roster" sentence names both definitions (the evaluator, ADR-0128 decision 7; the coder-driver, ADR-0126 decision 6 and ADR-0141 decision 5) and keeps "the rest of the roster stays open (OD-23)". No code change in this module.
7. **No other file changes.** In particular `orchestration/round-manager.md` and its tests are untouched (slice 4); the Round-Manager's fixed list `ROUND_MANAGER_TOOLS` is untouched (the Round-Manager does not get `coder_run`).
8. **Tests and gates**: the full test suite passes locally and in CI; `hilclaw/` coverage stays ≥ 80 % line and function; ruff clean. Tests cover happy (real definition derived), branch (fixture vs repository file) and negative (`Bash` refused; the text guards) cases (D12).
9. **Size**: the non-test change stays within the D4 cap (≤ 300 LOC, ≤ 5 files). If it would not, the executor keeps the agent file and its tests in this task and proposes a split in `## Follow-ups`.
10. **Language**: the agent file is Markdown (layer 1); the docstring edits are in existing Python modules. The executor records this in one line in the commit body and in `## Result` (CLAUDE.md language policy).
11. **Code mode (A-13)**: a Draft PR whose title contains `T-0387`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0387`, and the branch `claude/T-0387-coder-driver-definition` deleted.
12. No `claude` process is started, no container is started, and nothing runtime-only is required (D16). Runtime acceptance items (xii), (xiii), (xli)-(xliii) (HQ-0042, HQ-0056) are not closed by this task.

## Out of Scope

- Any edit of `ARCHITECTURE/`: no ADR, register row, proposal section or scenario note. The "less exact, not edited" sentences of ADR-0141 Consequences are not edited, except the `hilclaw/turn_permissions.py` docstring of AC 5 and the `hilclaw/turn_definition.py` roster sentence of AC 6.
- Slice 4: `orchestration/round-manager.md` (step 2 and the moved stop) and its test.
- Slice (d): the real container runtime, image, flag, sign-in, prompt or permission mode of the coder's `claude -p` (HQ-0053).
- Any change of `hilclaw/coder_tool.py`, `hilclaw/spec_tool.py`, `hilclaw/tools.py`, `hilclaw/turn_loop.py`, or the code of `turn_permissions`/`turn_definition`.
- The files of open PR #186 (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`).
- A hook that checks which agent calls `coder.run` (PLAN P2-4).

## Follow-ups

- Next for the planner: ADR-0141 Consequences slice 4 (step 2 of "The round steps" in `orchestration/round-manager.md` and the moved stop, decision 6, with its test).

## Result
