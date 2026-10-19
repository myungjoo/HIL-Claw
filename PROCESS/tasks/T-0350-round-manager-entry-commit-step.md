---
id: T-0350
title: Add run.commit as step 0 of the Round-Manager's turn entry and to the "Your run" tool list in orchestration/round-manager.md (ADR-0127 slice (2); PLAN P2-1)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-13, NFR-1, OD-8, OD-23, S0, S1, S2]
dependsOn: [T-0345, T-0348, T-0349]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
estimatedSize: {loc: 30, files: 2}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). This task is a slice of P2-1, so the D18 rule for non-checklist work does not apply. P2-5 needs it. ADR-0127 (part of OD-8 sub-question ⑪, first-case runs) makes `run.commit` the **first step of every turn's entry** (decision 5). That step is what makes a round-end commit that a dead turn left owed, before any new round begins. Without it, the step-1 change of slice (3) would start a turn for owed P2 that never makes the commit.

T-0349 (PR #199, `5507f98`) added the tool `run.commit` (MCP `mcp__hilclaw__run_commit`) to `default_registry`. This task is slice (2) of ADR-0127 Consequences. It writes step 0 into "The entry of a turn" of `orchestration/round-manager.md` and adds the tool to the list in "Your run". The call **right after the write that ends a round** is not part of this task. ADR-0127 Consequences gives it to the slice that writes "The round steps", and those steps are still undefined.

Open HQs checked. HQ-0043 (#5 A-3, the commit of a turn that ends before its round ends) does not block this slice. Step 0 commits only an owed round end, and ADR-0127 decision 8 leaves the cut-short case open. HQ-0044 holds runtime acceptance items (xv) to (xvii), which a live session would confirm. Those items stay open. The other open HQs concern other functions or are runtime-acceptance notices.

All verification is by reading, the existing suite and CI. No real `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, code-task test rule D12).
- `CLAUDE.md`, "상시 규칙": comment policy, the test rules ①–⑤, the code-mode branch and merge procedure (A-13), and the driver/runtime separation (D16).
- `orchestration/round-manager.md`, the whole file.
- `hilclaw/turn_definition.py`: the module docstring only, the "*The prompt*" bullet.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`:
  - Decision §2 (the Round-Manager is the one committer; no Bash);
  - §3 (the moments);
  - §4: the paragraph "A round end is owed", the tool table, and the bullets on `commit_refused`, `no_repository` and `commit_not_made`;
  - §5 (whole: step 0, a failure at the entry, a failure at the round end);
  - §8;
  - Walk-through rows 1, 3, 4, 6 and 8;
  - Consequences, slice (2), and runtime acceptance items (xv) to (xvii).
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: decision 3 (a Round-Manager that finds `"over"`). ADR-0127's Status revises it for this scope, and step 0 comes before it.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: decision 2 (typed tools, not Bash or file tools).
- `hilclaw/run_commit.py`: the module docstring and the description text of `run.commit` only (request and result shape, failure kinds).

## Acceptance Criteria

Language: no new layer-2 code. The change is Markdown in layer 1 plus one docstring bullet in an existing Python module. State this in one line in the commit body and in `## Result`.

### The definition (`orchestration/round-manager.md`)

1. **"Your run"**: the tool-list bullet names `mcp__hilclaw__run_commit` along with the four tools already listed. It says that this tool commits the run's round ends in the data repository, and that no other means is used for that, Bash or `git` included (ADR-0127 decision 2). Keep the bullet's existing rule for the four tools as it is. The other bullets of "Your run" and the whole of "One round at most" stay unchanged.
2. **"The entry of a turn"** gets a new first step. Number it 0, or renumber the list, whichever reads more clearly. It comes before `mcp__hilclaw__state_read` (ADR-0127 decision 5):
   - Call `mcp__hilclaw__run_commit` with your run id as `run_id`.
   - Whether `committed` is `true` or `false`, go on with the next step as written. Do not report the value.
   - If the call fails with any kind, report the kind in one line and end the session. Begin no round and write nothing into the run (ADR-0127 decision 5; ADR-0012 decision 6).
   - Cite the ADR decisions briefly, as the existing steps do.
3. The rest of the entry steps stays as it is, in substance. Change a step's wording only where step 0 makes it false. For example, step 4 ("If the state holds `run_status` `"over"` … Write nothing into the run") stays true: the commit came before it in step 0 (the ADR-0127 Status revision of ADR-0121 decision 3). Add **no** call of `run.commit` after the `"over"` write of the round-budget end in step 6. That write ends no round, and ADR-0127 decision 8 leaves its commit open (HQ-0043). Add **no** call after `state_write` anywhere else either.
4. **"The round steps"** stays as it is. Do not add the round-end call there. ADR-0127 Consequences gives that call to the slice that writes the round steps.
5. Keep the file short and imperative. Do not restate ADR-0127. Put no run's data into the file (ADR-0118 decision 5).

### The docstring (`hilclaw/turn_definition.py`)

6. Correct the "*The prompt*" bullet in one sentence or less, so that it also names the commit of an owed round end as the first step of the entry. No code change.

### Tests and checks

7. No `hilclaw/` code changes. So test rules ①–④ need no new test, and rule ⑤ forbids tests of test code. Do not add a test that pins the prompt's wording.
8. Run the existing suite locally (`pytest`, `ruff check`, `ruff format --check`) and confirm it passes, in particular `tests/test_turn_definition.py`, `tests/test_turn_start.py` and `tests/test_run_commit.py`. Then get CI green on the PR. No real `claude` is started at any point (D16). The stub `claude` of the existing tests is the only one.
9. Code mode (CLAUDE.md A-13: `orchestration/` is not a doc-mode path):
   - use branch `claude/T-0350-round-manager-entry-commit-step` and a Draft PR whose title holds `T-0350`;
   - run the reviewer cycle to Approve and get CI green;
   - squash-merge with the PR body as the squash message, whose last line is `Task: T-0350` (DRIVER §5);
   - delete the branch.
10. No runtime acceptance item is added or closed. Items (xv) to (xvii) of ADR-0127 stay with HQ-0044.

## Out of Scope

- The call of `run.commit` right after the write that ends a round, and every other round step (bring-up, coder, measurement, baseline, the end-of-round write, the fold of the spend view). These belong to later P2-1/P2-2 slices.
- ADR-0127 slice (3): owed P2 at step 1 in `hilclaw/further_turn.py` and `hilclaw/turn_start.py`.
- Any commit of a turn cut short, or of ADR-0121's own `"over"` write (decision 8, HQ-0043).
- Any change to `hilclaw/run_commit.py`, `hilclaw/run_file_tools.py`, `hilclaw/tools.py` or their tests.
- Every less-exact docstring or ADR sentence that ADR-0127 lists (D18 hold). Any edit to `ARCHITECTURE/`.
- `hilclaw/start_instance.py` and the other files of the open draft PR #186.

## Follow-ups

- Next slice (planner's candidate; code mode; stub `claude` and a temporary git repository only): ADR-0127 slice (3). Step 1 of the turn loop tells owed P2 from P2 with nothing owed, through `hilclaw.run_commit.owed_rounds`, in `hilclaw/further_turn.py` and `hilclaw/turn_start.py`. Owed P2 is treated as P4. A P2 in which the rule cannot be applied is an open state. The self-check runs before the first turn of a start in owed P2 (ADR-0127 decision 6).

## Result
