---
id: T-0345
title: Define the turn-entry steps of the Round-Manager (first STATE.json, the over states, the round-budget end) in orchestration/round-manager.md
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-3, NFR-7, OD-8, OD-19, OD-23, OD-28, S0, S1]
dependsOn: [T-0331, T-0340, T-0342]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
estimatedSize: {loc: 50, files: 2}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one of its slices, so the D18 priority rule for non-checklist work does not apply. P2-5 needs it.

Today `orchestration/round-manager.md` has a placeholder section "The steps of a round". It tells the session to report and end without writing any file. The accepted records already fix everything the Round-Manager does at the **entry** of a turn, before any bring-up or round work:

- ADR-0120 decisions 2–4: the round-0 turn's Round-Manager writes the first `STATE.json`, as its first write into the run, only into a fresh run directory. If `instance.json` is missing it writes nothing.
- ADR-0012 decisions 2, 4 and the Example: the content of that first file (`round` 0, the start spend view).
- ADR-0121 decisions 2–4: what the Round-Manager does when it finds `run_status` `"over"` or another value. Also: the one write of its own when `round` ≥ `round_budget`, which carries `round` and `budget_spent` over.
- ADR-0012 decision 6: an invalid file is an error and the turn does not go on. Another `schema_version` is not interpreted.
- ADR-0124: the four tools that do these reads and writes, with their failure kinds.

Writing these entry steps into the definition is the next slice. The round-0 bring-up steps stay open: the coder call, `sim.run`/`board.run`/`correctness.check`, the baseline of ADR-0119, and the end-of-round write. How the coder is started is PLAN P2-2 and the rest of OD-23. Who folds the spend view for the end-of-round write is OD-23 (ADR-0012 decision 6). After this task, a turn on a fresh run writes the first file and then reports that the bring-up steps are not yet defined. The turn loop then stops after the next turn, which leaves the run as it found it (ADR-0122 decision 3). That is the intended interim behaviour.

All verification is by reading and CI. No real `claude` is started (D16). Whether a real session follows these steps and reaches the tools is already covered by runtime acceptance items (x)–(xi) of ADR-0124 (HQ-0038) and by the nightly run of PLAN P2-10. This task adds no new runtime acceptance item and closes none.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, test rules D12).
- `CLAUDE.md`, "상시 규칙": comment policy, test rules ①–⑤, the code-mode branch/merge procedure, and the driver/runtime separation (D16).
- `orchestration/round-manager.md`, whole file.
- `hilclaw/turn_definition.py`, module docstring only. Read the "*The placeholder prompt*" bullet, around lines 33–35.
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`: decisions 2, 3, 4 and 6, and the Example (the first line is the exact start file).
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: decisions 2, 3 and 4, and the Walk-through.
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: decisions 2, 3 and 4.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: decision 3 (the tool table and the failure kinds).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decision 3 only. It explains why a turn that writes nothing is acceptable here.
- `ARCHITECTURE/OpenDecisionProposals.md` § OD-8: the bullet "하위 질문(ADR-0012가 넘긴 것 …)", sub-questions ⑪ and ⑫. Read them only to know what stays open.
- `hilclaw/run_file_tools.py`: module docstring only (request and result shapes).

## Acceptance Criteria

Language: no new layer-2 code. The change is Markdown in layer 1 plus one docstring bullet in an existing Python module. Say so in one line in the commit body and in `## Result`.

### The definition (`orchestration/round-manager.md`)

1. Replace the placeholder section "The steps of a round" with a section on the **entry of a turn**, plus a short section saying that the round steps themselves are not yet defined. Every step names the tool it uses, by its MCP name, with the session's run id as `run_id`. Keep "One round at most" and "Your run" as they are.
2. **Entry steps**, in this order (cite each ADR decision briefly in the text, as the existing sections do):
   1. Call `mcp__hilclaw__state_read`.
   2. **If it fails with `run_file_missing`**: call `mcp__hilclaw__run_fresh`.
      - If `fresh` is `true`, write the first file with `mcp__hilclaw__state_write`. Its `state` is exactly `{"schema_version": 1, "round": 0, "budget_spent": {"totals": {}, "position": 0, "open_steps": []}}` (ADR-0012 decision 2 and Example; ADR-0120 decision 2). This must be the first write of the turn into the run. Then go to the not-yet-defined round steps (item 3).
      - If `fresh` is `false`, write nothing into the run. Report in one line that the run directory is not fresh and holds no `STATE.json`, and end the session (ADR-0120 decisions 3 and 4). Whether the cause is a missing `instance.json` or other files is not to be told apart. The records leave that open.
   3. **If it fails with any other kind**, or `run.fresh` fails: report the kind in one line and end the session. Write nothing (ADR-0012 decision 6; ADR-0124 decision 3).
   4. **If it returns a state** and `run_status` is `"over"`: end the session without writing anything into the run (ADR-0121 decision 3).
   5. **If `run_status` is present with any other value or type**: report the value in one line, begin no round, write nothing, and end (ADR-0121 decision 2).
   6. **If `run_status` is absent**: call `mcp__hilclaw__instance_read`.
      - If it fails, report the kind in one line and end the session. Write nothing.
      - If `instance.json` states no `round_budget`, report that in one line and end the session. Write nothing. This case is ㉙ (나), which is open.
      - If `round` ≥ `round_budget`, write `"over"` with `mcp__hilclaw__state_write` and end the session (ADR-0121 decisions 3 and 4). The new `state` is the three members `schema_version`, `round` and `budget_spent`, exactly as read, plus `run_status` `"over"`. **But if the state read holds any top-level member other than those three, write nothing.** Report that in one line and end. Whether a writer keeps a member it does not know is OD-8 sub-question ⑫, which is open. Do not decide it.
      - Otherwise go to item 3.
   7. If `state.write` fails, report the kind in one line and end the session.
3. **The round steps** — the bring-up and baseline of round 0 and the work of later rounds — are not yet defined. When an entry step leads here, report in one line that the steps of round `<round>` are not yet defined. End the session. Write nothing further.
   - State in one sentence that later slices replace this section.
   - **Do not define**: any bring-up, coder, measurement, evaluation or baseline step; the end-of-round write; the fold of the spend view; a commit step; any `phase` member. These are open: ADR-0119 is not to be applied here; P2-2 and OD-23 cover the coder and the fold; OD-8 ⑪ covers the commit.
4. Keep the file short and imperative. Do not restate the ADRs. Put no run's data into it: it stays one definition for every run (ADR-0118 decision 5). Use no Bash or file tools for the run's files, as "Your run" already says.

### The docstring (`hilclaw/turn_definition.py`)

5. Correct the "*The placeholder prompt*" bullet so it matches the new definition, in one or two sentences. The definition now defines the entry of a turn (the first `STATE.json`, the over states, the round-budget end). The round steps are not yet defined. Rename the bullet if "placeholder" no longer fits. No code change.

### Tests and checks

6. No `hilclaw/` code changes. So test rules ①–④ need no new test, and rule ⑤ forbids tests of test code. Do not add a test that pins the prompt's wording.
7. Run the existing suite locally (`pytest`, `ruff`) and confirm it still passes, in particular `tests/test_turn_definition.py` and `tests/test_turn_start.py`. Then get CI green on the PR. No real `claude` is started at any point (D16). The stub `claude` of the existing tests is the only one.
8. Code mode (CLAUDE.md A-13: `orchestration/` is not a doc-mode path). Use branch `claude/T-0345-<slug>` and a Draft PR whose title holds `T-0345`. Run the reviewer cycle, then squash-merge with the PR body as the squash message. The body's last line is `Task: T-0345` (DRIVER §5).

## Out of Scope

- Any step of round 0's bring-up or baseline (ADR-0119), the coder call (PLAN P2-2), the evaluator (P2-3), hooks (P2-4), hypotheses (P2-6) and cases (P2-7).
- The end-of-round write and who folds the spend view (OD-23); the commit step and how a fresh turn learns that a commit is owed (OD-8 ⑪).
- Any change to `hilclaw/run_file_tools.py`, `hilclaw/turn_loop.py`, `hilclaw/turn_start.py`, `hilclaw/further_turn.py` or their tests.
- Any edit to `ARCHITECTURE/` (no OD changes state; no ADR is written).
- `hilclaw/start_instance.py` and the files of open PR #186.

## Follow-ups

- Next P2-1/P2-2 slice (planner's candidate, no file yet): an ADR on how the first-case Round-Manager starts the round-0 coder call and points it at the scratch's spec copy (OD-23 "코더를 띄우고 그 자리를 알리는 방법", PLAN P2-2; scratch and bring-in exist in `hilclaw/scratch.py` and `hilclaw/bring_in.py`). Check first whether any part is owner-only (#5 A-8).
- Alternatively: an ADR on OD-8 sub-question ⑪ (which step commits a round and how a fresh turn learns a commit is owed).

## Result

- DONE. PR #197 (Draft -> ready), squash-merged as a4f5004; branch deleted.
- Review: 2 rounds by a context-isolated dev-reviewer. Round 1 Approve with one optional nit (name the run id as `run_id` for the entry steps), applied in 84995c9. Round 2 Approve, no findings.
- CI: all six checks green on 84995c9 (C gate, Coverage gate, Python gate 3.11/3.14, Test presence, sh gate).
- Local: `python -m pytest -q` 23806 passed, 709 skipped; `python -m ruff check .` and `ruff format --check .` clean.
- Change: `orchestration/round-manager.md` replaces the placeholder section with "The entry of a turn": state_read, then run_fresh and the first STATE.json, the over and unknown run_status cases, and the round_budget end (write "over" only when the state holds just the three ADR-0012 members, so OD-8 sub-question 12 stays open). A short section "The round steps" says those steps are not yet defined. The `hilclaw/turn_definition.py` docstring bullet is renamed "*The prompt*" and corrected.
- Language: no new layer-2 code; Markdown in layer 1 plus one docstring bullet in an existing Python module.
- No new tests (rules 1-5); no real `claude` started (D16). No runtime acceptance item added or closed.
- Follow-ups: as listed in the task (an ADR on the round-0 coder call for OD-23 / P2-2, or one on OD-8 sub-question 11).
