---
id: T-0393
title: Have the Round-Manager call run.commit before every end of its session after a successful entry step 0 (ADR-0143 Consequences slice (2); PLAN P2-1/P2-4)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-13, FR-18, NFR-1, OD-8, S0, S1, S2]
dependsOn: [T-0391, T-0392]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
  - tests/test_turn_definition.py
estimatedSize: {loc: 80, files: 2}
hq: []
---
## Why

ADR-0143 (T-0391, main a3eb31c) carries out the owner's answer (a) to HQ-0043: every live end of a first-case turn commits what the run directory then holds, and the case file of the round in progress stays out of a commit that ends no round. Its Consequences list three code slices, in order:

- Slice (1), done by T-0392 (PR #227, main 5594875): `run.commit` now makes a commit that ends no round whenever one is owed, and does nothing when nothing is owed.
- **Slice (2), this task**: `orchestration/round-manager.md` calls `run.commit` as the last act before every end of its session that follows a successful entry step 0 (ADR-0143 decision 2).
- Slice (3), not this task: `hilclaw/further_turn.py` and `hilclaw/turn_start.py` tell owed P2 by `run_commit.commit_owed`.

D18 judgement: this is the code of an owner decision (HQ-0043 (a)), made through the PLAN P2-1 Round-Manager prompt and the P2-4 commit work. P2-5 needs it: every first-case turn today ends at "The stop", which says "no `run.commit`", so a run's work reaches the data repository only at a round end, and slice (1) has no caller at a turn's end until this lands.

Open HQs checked:

- HQ-0043: answered (a); ADR-0143 records it.
- HQ-0058 (runtime acceptance item (xlvii): a live Round-Manager does this call) stays open and non-blocking. This task writes the prompt; it does not establish (xlvii) and must not claim to.
- HQ-0021 (`board.run` registration, ADR-0142 slice 2): not crossed. Round step 4 keeps its stop; no `experiment-runner`, step 5 or round-0 go-on to the closing steps is added.
- HQ-0032 (T-0324), HQ-0053 (coder sign-in) and every other open HQ: not crossed.

Open PR #186 (T-0324, draft) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None overlaps this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit) and §5 (task file format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md` (repository), "상시 규칙": comment minimisation, test rules ① to ⑤, the code-mode branch and merge procedure (A-13), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md`: Status (lines 3-19), Context "What ends a turn now" (line 25), decision 2 (lines 37-42), decision 3 last bullet (line 51), decision 7 "A writer still at work" (line 75), the Walk-through (lines 78-90), Consequences slice (2) (line 107) and the `orchestration/round-manager.md` and `hilclaw/turn_definition.py`-related items of "Less exact, not edited" (lines 109-113), and runtime item (xlvii) (line 117).
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` decisions 3 and 5 (lines 43-49 and 69-75): the entry call and the closing call, which stay.
- `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md` decision 5 (lines 66-73): the failed `round.end`, whose "does not call `run.commit`" ADR-0143 revises.
- `ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md` decisions 1, 2 and 7 (lines 34-46 and 79-84): "The stop".
- `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md` decision 4: no tool request names a run after a prompt with no valid run id.
- `orchestration/round-manager.md`, the whole file (167 lines).
- `hilclaw/turn_definition.py`, the module docstring (lines 1-80).
- `tests/test_turn_definition.py`, lines 1-120 (helpers, constants) and lines 480-552 (the prompt tests and the helpers `prompt_text` and `only_forbidden`).
- `hilclaw/run_commit.py`, the module docstring and `_DESCRIPTION` only, to see what the tool now promises (nothing owed, nothing written; safe at every entry and before every end).

## Acceptance Criteria

Language: no new layer-2 code; layer-1 Markdown, a docstring correction and Python tests. State this in one line in the commit body and in `## Result`.

1. **"Your run".** The `mcp__hilclaw__run_commit` sentence no longer limits the tool to "round ends": it is the only means of every commit of the run in the data repository (ADR-0143 Consequences slice (2)). The rest of the bullet stays.
2. **The entry steps.** Every entry step that ends the session after a successful step 0 — step 2 (`fresh` false), step 3 (a failed `state_read` of another kind, or a failed `run_fresh`), step 4 (`"over"`), step 5 (another `run_status`), step 6 (a failed `instance_read`, no `round_budget`, an extra top-level member, and the own `"over"` write of ADR-0121) and step 7 (a failed `state_write`) — has the Round-Manager call `mcp__hilclaw__run_commit` as its last act before the session ends (ADR-0143 decision 2). The prompt may state this once (for example as one rule that every end after a successful step 0 follows) instead of repeating it in each step, provided no end of those steps is left out. The "Write nothing" sentences of those steps stay true of the run's work; the prompt makes clear that the commit call is not such a write (it changes no file of the run but a removed torn tail — ADR-0143 Consequences slice (2)). Whether `committed` is `true` or `false` is not reported.
3. **Where it is not called.** After a prompt with no valid run id, nothing changes (no tool request names a run — ADR-0123 decision 4). After a failed `run.commit` — at entry step 0 or at any end — the Round-Manager reports the kind in one line and ends the session without calling it again (ADR-0143 decision 2; ADR-0127 decision 5). Step 0's text keeps that it ends the session on any failure, including when what was owed was only a commit that ends no round.
4. **"The stop".** The sentence "no `round.end` and no `run.commit`" becomes "no `round.end`" plus a call of `mcp__hilclaw__run_commit` before the session ends, in round 0 after step 2, 3 or 4 and in other rounds after step 1. Round 0 is still not ended. The stop is reached only after the delegation's report (round steps 2 to 4 wait for it — ADR-0143 decision 7, "A writer still at work"); the prompt must not place the call before that report. "No turn goes past this stop" and the later-slices sentence stay.
5. **The closing steps.** In closing step 2, a failed `round.end` (any kind) now has the Round-Manager report the kind in one line, call `mcp__hilclaw__run_commit`, and end the session; "do not call `mcp__hilclaw__run_commit`" is removed, the rest of that bullet stays (revising ADR-0135 decision 5, cited as ADR-0143 decision 2). Closing step 3 stays as it is (it is the end's call; a failure of it is reported and the session ends with no second call).
6. **Citations** for every changed sentence name ADR-0143 decision 2 (and the ADR it revises where one is revised). No sentence of the prompt cites HQ-0043 as unanswered. The prompt states no retry of `run.commit`, no removal of a `git` lock and no push (ADR-0143 Boundaries).
7. **`hilclaw/turn_definition.py` docstring** ("The prompt" bullet): "first the commit of an owed round end" and the "ends without a further write" sentences match the new prompt (the entry commits what is owed; every end after a successful entry commit calls `run.commit`; the stop still writes nothing else and ends no round). No code change in that module.
8. **Tests** in `tests/test_turn_definition.py`, in the style of the existing prompt tests (`prompt_text`, sentence splits); a revised test is listed in `## Result`:
   - happy: the stop's text holds a call of `mcp__hilclaw__run_commit` and still says round 0 is not ended (no `round.end`); the "Your run" sentence about `run_commit` no longer says "round ends";
   - branch: the closing step 2 failure bullet calls `run_commit` before ending and still forbids a second `round_end` and a `state_write`; closing step 3 is unchanged; the rule for the entry steps covers steps 2 to 7 (for example by checking that the rule's text names those steps, or that each step's end refers to it — the executor picks a check that fails if a step is dropped);
   - negative: the prompt holds no sentence saying "no `run.commit`" or "do not call `mcp__hilclaw__run_commit`" outside the no-second-call rule after a failed call; the invalid-run-id bullet still makes no tool request that names a run; the step-0 failure still ends the session; "not yet defined" (the later-rounds stop) and the closing-steps qualifier ("reached only once later slices") stay; no `board_run`, `sim_run` or `experiment-runner` appears.
   Every other existing test of `tests/test_turn_definition.py`, `tests/test_turn_permissions.py`, `tests/test_run_commit.py` and `tests/test_mcp_front.py` passes unchanged. Coverage of `hilclaw/` stays ≥ 80 % line and function; ruff passes.
9. **No other file changes**: `git diff --stat origin/main` lists only the touchesFiles; `git diff --check` is clean. No tool, permission, agent file, data-plane member, kind or validator is added or changed (`hilclaw/turn_permissions.py` already allows `mcp__hilclaw__run_commit`). No `claude` process is started, real or stub (D16).

## Out of Scope

- `hilclaw/further_turn.py`, `hilclaw/turn_start.py` and owed P2 (ADR-0143 slice (3)).
- `hilclaw/run_commit.py` and its tests (slice (1), done).
- The "One round at most" bullet "The session ends after the write that ends its round" (held in PLAN "보류", T-0370 follow-up); do not edit it.
- `experiment-runner`, round step 5, the round-0 closing steps after a baseline (ADR-0142 slice 2, waits on HQ-0021).
- Any ADR, Requirements, OpenDecisionProposals or StandardScenarios edit, including the ADR-0143 "Less exact, not edited" list and the T-0391 round-7 nit.
- A wait for the user or a gate (ADR-0143 Boundaries), the Stop hook (P2-4 hooks), retry of `run.commit` and stale `git` locks (OD-17).

## Follow-ups

- Slice (3) of ADR-0143: `hilclaw/further_turn.py` and `hilclaw/turn_start.py` tell owed P2 by `run_commit.commit_owed` and map its `CommitNotMadeError` (T-0392 Result note).

## Result

- **PR**: #228 (branch `claude/T-0393-round-manager-commit-before-every-end`), squash-merged after 3 review rounds (all Approve; nits of rounds 1 and 2 addressed).
- **Language**: no new layer-2 code; layer-1 Markdown, a docstring correction and Python tests.
- **`orchestration/round-manager.md`**: new section "The end of a session" states once that, after a successful entry step 0, `mcp__hilclaw__run_commit` is the last act before every end of the session, naming entry steps 2, 3, 4, 5, 6 and 7, the stop and a failed `round.end` of closing step 2 (closing step 3 is that call); `committed` is not reported; the call is not a write of the run's work; no call after an invalid run id and no second call after a failed one (ADR-0143 decision 2; ADR-0127 decision 5). The entry intro refers to that section; step 0 keeps ending the session on any failure, also when only a commit that ends no round was owed. "Your run": `run_commit` makes every commit of the run. "The stop": reached once the awaited report has come (ADR-0143 decision 7), "no `round.end`" and a `run_commit` call; round 0 is not ended. Closing step 2: a failed `round.end` reports, calls `run_commit`, ends (ADR-0143 decision 2, revising ADR-0135 decision 5). Closing step 3 unchanged. No retry, lock removal or push is stated.
- **`hilclaw/turn_definition.py`**: "The prompt" docstring bullet only; no code change.
- **Tests** (`tests/test_turn_definition.py`, new; no existing test revised): `test_the_prompt_uses_run_commit_for_every_commit`, `test_the_stop_commits_and_leaves_round_0_open`, `test_the_end_rule_covers_entry_steps_2_to_7` (checks the rule's step list and that the session-ending entry steps parsed from the prompt are exactly 0, 2 to 7), `test_the_step_0_failure_still_ends_the_session`, `test_a_failed_run_commit_is_not_called_again`, `test_the_closing_steps_commit_after_a_failed_round_end` (closing step 3 text pinned by prefix), `test_the_prompt_forbids_run_commit_nowhere_else`, `test_an_invalid_run_id_makes_no_request`.
- **Local checks**: full `python -m pytest` 25620 passed, 738 skipped; coverage of `hilclaw/` 97 % line; `ruff check .` and `ruff format --check .` clean; `git diff --check` clean. CI on PR #228: all six checks green (Python 3.11 and 3.14, coverage gate, test presence, C, shellcheck).
- **Runtime acceptance**: item (xlvii) (HQ-0058) is not established by this change; it needs a live Round-Manager. No `claude` process, real or stub, was started (D16).
- **Follow-ups**: ADR-0143 slice (3) (`hilclaw/further_turn.py`, `hilclaw/turn_start.py`, owed P2 by `run_commit.commit_owed`), as already listed.
