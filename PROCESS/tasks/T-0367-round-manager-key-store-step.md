---
id: T-0367
title: Write the key.store step of ADR-0134 decision 5 as the first round step in orchestration/round-manager.md (ADR-0134 slice 2; PLAN P2-1)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-13, FR-18, OD-26, OD-23, S0, S1]
dependsOn: [T-0364, T-0365, T-0366]
touchesFiles:
  - orchestration/round-manager.md
  - hilclaw/turn_definition.py
estimatedSize: {loc: 30, files: 2}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and the round-0 procedure) is the first unchecked item in the P2 order (D18). This task is a slice of P2-1, so the D18 rule for non-checklist work does not apply. P2-5 needs it: without this step no first-case run stores its two key record files, and every `case.write` of the run then answers `key_not_stored` (ADR-0133 decision 3 ⑤).

ADR-0134 makes the Round-Manager store the hw_profile and op_signature record files that its run's `instance.json` states. It does this inline, through the registry tool `key.store` (`mcp__hilclaw__key_store`), as **the first round step of every turn that carries a round** (decisions 2 and 5). A failure is reported in one line and does not stop the round (decision 5). The tool landed with T-0365 (PR #209). The commit of the record files by `run.commit` landed with T-0366 (PR #210). ADR-0134 Consequences, slice 2, leaves one thing: writing this step into "The round steps" of `orchestration/round-manager.md`, with `mcp__hilclaw__key_store` as the only means of storing the files.

ADR-0134 decision 5 fixes this step completely (order, when it is called, what follows a failure), and it does not depend on the round steps that are still undefined. So the step can be written now, in front of the "not yet defined" text that the section keeps for the rest of the round. This is the same incremental pattern as T-0345 (entry steps) and T-0350 (step 0, `run.commit`). The other P2-1 steps stay out of this task: ADR-0133 slice 2 (`case.write` right before the write that ends the round), the write that ends a round, the `run.commit` right after it, bring-up and baseline. They need the round's end, which no record defines yet.

Open HQs checked. None blocks this slice. HQ-0050 holds runtime acceptance items (xxvii) and (xxviii) of ADR-0134, which only a live session can confirm. They stay open, and this task neither adds nor closes them. HQ-0043 (commit of a turn cut short) is not touched. Open PR #186 (T-0324) touches `hilclaw/start_instance.py` and three test files, and none of them overlaps this task.

All verification is by reading, the existing suite and CI. No real `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, code-task test rule D12).
- `CLAUDE.md`, "상시 규칙": comment policy, test rules ①–⑤, the code-mode branch and merge procedure (A-13), and the driver/runtime separation (D16).
- `orchestration/round-manager.md`, the whole file (85 lines).
- `hilclaw/turn_definition.py`: the module docstring only, the "*The prompt*" bullet (around lines 33–37) and the sentence near line 57 that mentions "no round steps (later P2-1 slices)".
- `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`:
  - Decision §2 (who: the Round-Manager, inline, through `key.store`);
  - §3, the table rows "Name", "Request" and "Result" only;
  - §5 (whole: the order, and that a failure does not stop the round);
  - §6 (what a non-simple outcome answers; read it to see that a success with `false` flags needs no report);
  - Walk-through rows 1, 4, 5 and 6;
  - Consequences, slice 2, and runtime acceptance items (xxvii) and (xxviii).
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: decision 2 (typed tools, not Bash or file tools). This is the pattern that the "Your run" tool bullet follows.
- `hilclaw/key_store_tool.py`: the module docstring only (request, result, kinds).

## Acceptance Criteria

Language: no new layer-2 code. The change is Markdown in layer 1 plus a docstring correction in an existing Python module. State this in one line in the commit body and in `## Result`.

### The definition (`orchestration/round-manager.md`)

1. **"Your run"**: the tool-list bullets name `mcp__hilclaw__key_store`, with your run id as `run_id`, as the only means of storing the run's two key record files. Bash, file tools and any other means are not used for that (ADR-0134 decisions 2 and 3; ADR-0124 decision 2 for the pattern). Keep the existing rules for the other five tools in substance. The other bullets of "Your run", the whole of "One round at most" and the whole of "The entry of a turn" stay unchanged.
2. **"The round steps"** begins with one defined step, the first step of every round that a turn carries, whether the round is begun or gone on with (ADR-0134 decision 5):
   - Call `mcp__hilclaw__key_store` with your run id as `run_id`.
   - Whether `hw_profile_created` and `op_signature_created` are `true` or `false`, go on. Do not report the values (decision 6: a stored key, with the same or other attributes, is a success).
   - If the call fails with any kind, report the kind in one line and go on. Do not end the session, do not call the tool again in this turn, and do not try to store the files another way (decision 5; a retry within a turn is OD-17's).
   - Cite the ADR decisions briefly, as the entry steps do.
3. After that step, the section keeps the present rule for everything else: report in one line that the remaining steps of round `<round>` are not yet defined, end the session and write nothing further. Reword the existing sentences only as far as the new step makes them false. For example, "The steps of a round … are not yet defined" becomes "the remaining steps", and "When an entry step leads here …" must still hold for both entry paths (step 2's fresh run and step 6's round below budget). The sentence that later slices replace the section stays, in substance.
4. Add **no** call of `run.commit`, `case.write` or `state.write` in "The round steps". The write that ends a round, the commit after it, and ADR-0133 slice 2 (`case.write`) belong to later P2-1 slices.
5. Keep the file short and imperative. Do not restate ADR-0134. Put no run's data into the file (ADR-0118 decision 5). Name no model (HQ-0041). Create no file under `orchestration/agents/`.

### The docstring (`hilclaw/turn_definition.py`)

6. Correct the "*The prompt*" bullet in one sentence or less, so that it says the round steps begin with the store of the run's key record files and that the remaining steps of a round are not yet defined. Adjust the sentence near line 57 ("no round steps (later P2-1 slices)") only if it becomes false. No code change.

### Tests and checks

7. No `hilclaw/` code changes. So test rules ①–④ need no new test, and rule ⑤ forbids tests of test code. Do not add a test that pins the prompt's wording.
8. Run the existing suite locally (`pytest`, `ruff check`, `ruff format --check`) and confirm it passes, in particular `tests/test_turn_definition.py`, `tests/test_turn_start.py` and `tests/test_key_store_tool.py`. Then get CI green on the PR. No real `claude` is started at any point (D16). The stub `claude` of the existing tests is the only one.
9. Code mode (CLAUDE.md A-13: `orchestration/` is not a doc-mode path):
   - use branch `claude/T-0367-round-manager-key-store-step` and a Draft PR whose title holds `T-0367`;
   - run the reviewer cycle to Approve and get CI green;
   - squash-merge with the PR body as the squash message, whose last line is `Task: T-0367` (DRIVER §5);
   - delete the branch.
10. No runtime acceptance item is added or closed. Items (xxvii) and (xxviii) of ADR-0134 stay with HQ-0050.

## Out of Scope

- ADR-0133 slice 2 (the `case.write` step right before the write that ends a round), the write that ends a round, the `run.commit` call right after it, and every other round step (bring-up, self-check, coder call, measurement, baseline, evaluator, fold of the spend view). These belong to later P2-1/P2-2/P2-3 slices.
- Any change to `hilclaw/key_store_tool.py`, `hilclaw/run_commit.py`, `hilclaw/tools.py`, `hilclaw/key_records.py` or their tests.
- Every less-exact ADR or docstring sentence that ADR-0134 Consequences lists, apart from the `turn_definition.py` bullet of criterion 6 (D18 hold). Any edit to `ARCHITECTURE/`.
- `hilclaw/start_instance.py` and the other files of the open draft PR #186.

## Follow-ups

- Next P2-1 work (planner's view): the round's end for first-case runs — what ends a round and its write, with ADR-0133 slice 2 (`case.write`) and the `run.commit` after it — needs a record of the round steps before code. The planner decides whether a design-level OD record (OD-23/OD-8) can cover it without an unanswered HQ.

## Result
