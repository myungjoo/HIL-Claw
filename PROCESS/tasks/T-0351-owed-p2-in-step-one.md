---
id: T-0351
title: Tell owed P2 from P2 with nothing owed in step 1 of the turn loop (hilclaw/further_turn.py, hilclaw/turn_start.py; ADR-0127 slice (3); PLAN P2-1)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-13, NFR-1, OD-8, OD-19, S0, S1, S2]
dependsOn: [T-0336, T-0338, T-0344, T-0349, T-0350]
touchesFiles:
  - hilclaw/further_turn.py
  - hilclaw/turn_start.py
  - tests/test_further_turn.py
  - tests/test_turn_start.py
estimatedSize: {loc: 80, files: 2}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18), and P2-5 (the first end-to-end run) needs every round end of its run in the data repository's history. ADR-0127 (part of OD-8 sub-question ⑪, first-case runs) makes the Round-Manager commit each round end through `run.commit`. A turn that dies between the write of the last round end (`run_status` `"over"`) and that commit leaves the commit owed. Today step 1 of the turn loop answers every `"over"` with "run over", so no turn ever makes that commit. ADR-0127 decision 6 splits P2: P2 with a round end owed is treated as P4 is. This task is slice (3) of ADR-0127 Consequences, and so a slice of P2-1. The D18 rule for non-checklist work does not apply.

Done so far: slice (1), T-0349 (PR #199), added `hilclaw/run_commit.py` with the read-only rule `owed_rounds(data_root, run_id)`. Slice (2), T-0350 (PR #200), made `run.commit` step 0 of the Round-Manager's turn entry. That step 0 is what makes the owed commit once this task starts a turn for it.

Open HQs checked. HQ-0043 (#5 A-3, the commit of a turn that ends before its round ends; ADR-0127 decision 8) does not touch this slice. Owed P2 is a run whose **last round end** was written and not committed. A turn cut short inside a round leaves `round` unchanged, so the rule finds nothing owed and this task commits nothing. HQ-0044 holds runtime acceptance items (xv) to (xvii), which only a live session confirms; they stay open. The other open HQs concern other functions or are runtime-acceptance notices. Open draft PR #186 touches `hilclaw/start_instance.py` and its tests only.

All verification uses temporary git repositories and the stub `claude` that the tests write. No real `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, code-task test rule D12).
- `CLAUDE.md`, "상시 규칙": comment policy, test rules ①–⑤, the code-mode branch and merge procedure (A-13), the driver/runtime separation (D16), and the layer-2 language policy.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`:
  - Status, the bullet "What it answers" (the revisions of ADR-0121 decisions 3 and 5, ADR-0122 decisions 2 to 5 and ADR-0125 decision 2);
  - Decision §4, the paragraph "A round end is owed" and the bullet on `commit_refused` ("When each is checked");
  - Decision §6 (whole);
  - Decision §8;
  - Walk-through rows "The last round … ends", "The same, with a death before the commit", "A session ends with exit status 0 after the write that ends round 3 …" and "The data root is not a git working tree";
  - Consequences, slice (3), and the last bullet of "Less exact, not edited" (the docstrings of `hilclaw/further_turn.py` and `hilclaw/turn_start.py`) together with the ADR-0125 bullet before it.
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decisions 2 to 5.
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: decision 5.
- `ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md`: decisions 2 and 4.
- `hilclaw/further_turn.py`: the whole file.
- `hilclaw/turn_start.py`: the module docstring, `_outcome` and `_Step`.
- `hilclaw/run_commit.py`: the module docstring, the exception classes, `owed_rounds` and its docstring, the error mapping inside `definition`, and the constants `KIND_NO_REPOSITORY`, `KIND_COMMIT_REFUSED` and `GIT`.
- `tests/test_run_commit.py`: the fixture `isolated_git` and the helpers `git`, `new_repository`, `write_state` and `commit_by_hand`, as a pattern for temporary repositories.
- `tests/test_further_turn.py` and `tests/test_turn_start.py`: the fixtures and the P2 tests (`test_p2_over_is_no_further_turn`, `test_the_loop_on_a_run_that_is_over_starts_nothing`, `test_over_written_by_a_failed_turn_is_run_over`, and every test that expects `RUN_OVER`).

## Acceptance Criteria

Language: Python. These are existing Python modules of the package. Say so in one line in the commit body and in `## Result`.

### `hilclaw/further_turn.py`

1. **New case and reasons.** Add one case constant for owed P2, for example `OWED = "owed"`. Add two reason constants for `OPEN`: `NO_REPOSITORY = "no_repository"` and `COMMIT_REFUSED = "commit_refused"`. Their values equal `run_commit.KIND_NO_REPOSITORY` and `run_commit.KIND_COMMIT_REFUSED`, so the starter is told the kind the tool would answer (ADR-0127 decision 6, last bullet). The names are the executor's if clearer. The existing constants and their values stay unchanged.
2. **`classify`, P2 only.** When `run_status` is exactly the `str` `"over"`, call `hilclaw.run_commit.owed_rounds(data_root, run_id)` once, and only then. Answer:
   - `Finding(OVER_CASE, None)` when the range is empty: P2 with nothing owed, as before;
   - `Finding(OWED, None)` when it is not empty: owed P2. The value is `None`, so that owed P2 found before and after an exit-0 turn compares equal. This is ADR-0127 decision 6: "owed P2 again counts as 'as it found it'";
   - `Finding(OPEN, NO_REPOSITORY)` for `run_commit.NoRepositoryError` or `run_commit.GitNotRunError`;
   - `Finding(OPEN, COMMIT_REFUSED)` for any `run_commit.CommitRefusedError`.
   Any other exception passes through unchanged, as `classify` already documents for `OSError`.
3. **No other state changes.** P1, P3, P4 and the existing open states are found exactly as now, in the same order, and `git` is not run for them. A data root that is no existing directory still raises before P2 is reached (`fresh_run.is_fresh`). So no `no_data_root` reason is added, and the docstring says why in at most one sentence. Nothing in this module writes, and `owed_rounds` writes nothing either. Do not call `run_commit.commit` from step 1: the loop only reads (ADR-0127 decision 2, "The loop's step 1 of decision 6 only reads").
4. **`predicate`.** `OWED` answers like `DUE`: `True` when `previous` is `None` or the `int` 0, otherwise `fallback(previous)`. `OPEN` with the new reasons goes to `fallback` like every `OPEN`.
5. **Docstrings.** In the module docstring:
   - add owed P2 to the list of states;
   - say that in P2 the module applies the rule of ADR-0127 decision 4 read-only through `run_commit.owed_rounds`. This revises "compares no number" and "interprets no member besides `run_status` and `round_budget`" for P2 only, in the fewest words;
   - drop "a run that is over and whose commit is still owed (OD-8 ⑪)" from what is still open.
   Update the `Finding` docstring (the reasons are now nine, and the value of `OWED` is `None`) and the `classify` and `predicate` docstrings to match the code. Keep each change short. Do not restate ADR-0127.

### `hilclaw/turn_start.py`

6. **Behaviour** (ADR-0127 decision 6 applied to ADR-0122 decisions 2 to 5 and ADR-0125 decision 2). With the finding of criterion 2, the existing `_outcome` order should already give all of the following. Change the code only where it does not:
   - before the first turn, owed P2 is a turn due. The self-check runs once, then the first turn starts if the check lets it;
   - after a turn whose exit status is not 0, owed P2 gives `FAILED_TURN` with that status;
   - after an exit-0 turn that began in owed P2 and left owed P2, the outcome is `UNCHANGED_TURN`;
   - after an exit-0 turn that moved P4 to owed P2, a further turn starts, with no second self-check (ADR-0125 decision 4 (ii));
   - `RUN_OVER` is told only for P2 with nothing owed;
   - the new open reasons give `OPEN_STATE` with that `reason`, with `exit_status` after a failed turn, before the first turn as after any turn, and with no self-check when the first step 1 answers them.
   No new outcome, member or exit status is added. The table of the module docstring stays as it is.
7. **Docstring.** Update the step-1 order list so that P2 "run over" is P2 with nothing owed and owed P2 sits with P1 and P4. Update the self-check paragraph's "(P1 or P4)" to name owed P2 as well. Keep the rest as it is.

### Tests

8. `tests/test_further_turn.py`. Use temporary git repositories with an isolated git configuration and identity, as `tests/test_run_commit.py` does. Do not import from another test module. Cover:
   - P2 with nothing owed (`HEAD` holds the same `STATE.json`) → `OVER_CASE`;
   - owed P2, with `HEAD` holding a lower `round`, and in a repository without `HEAD` with `round` ≥ 1 → `OWED`;
   - P2 in a data root that is no git working tree → `OPEN`/`NO_REPOSITORY`;
   - `git` that cannot be started (monkeypatch `run_commit.GIT` to a missing program) → `OPEN`/`NO_REPOSITORY`;
   - working `round` below that of `HEAD`, and an invalid `STATE.json` in `HEAD` → `OPEN`/`COMMIT_REFUSED`;
   - P1, P3 and P4 in a data root that is no git working tree are found as before (no `git` needed);
   - `predicate` on `OWED` with `previous` `None`, 0 and non-zero, and on the two new open reasons → `fallback`.
   Update the existing P2 tests so that they keep meaning P2 with nothing owed.
9. `tests/test_turn_start.py`, against the stub `claude` only. The stub inherits the test's environment, so it can run `git` in the temporary repository, for example to make the commit that the entry's `run.commit` would make. Cover:
   - owed P2 at the start → check, one turn whose stub commits → `run_over`, with the `check` member;
   - owed P2, stub exits 0 without committing → `unchanged_turn` after one turn;
   - owed P2, stub exits non-zero → `failed_turn`;
   - P4 → stub writes the last round end with `"over"`, exits 0 without committing → a second turn, no second check, whose stub commits → `run_over`;
   - owed P2 with a self-check that does not pass → `stopped_at_check`, no turn;
   - P2 in a data root that is no git working tree → `open_state` with `reason` `no_repository`, no check, no turn;
   - `commit_refused` → `open_state`.
   Revise `test_over_written_by_a_failed_turn_is_run_over` and the other `RUN_OVER` tests to match ADR-0127. For example, a failed turn that writes `"over"` without a commit now gives `failed_turn`. Keep only those tests whose P2 has nothing owed expecting `run_over`.
10. Test rules ①–④ hold: coverage ≥ 80% line and function for `hilclaw/`, negative cases included, and every public function of both modules covered. No test of test code (rule ⑤). Run `pytest`, `ruff check` and `ruff format --check` locally, then get CI green. No real `claude` is started at any point (D16).
11. Code mode (CLAUDE.md A-13):
    - branch `claude/T-0351-owed-p2-in-step-one`;
    - a Draft PR whose title holds `T-0351`;
    - the reviewer cycle to Approve, and CI green;
    - squash-merge with the PR body as the squash message, whose last line is `Task: T-0351` (DRIVER §5);
    - delete the branch.
12. No runtime acceptance item is added or closed. Items (xv) to (xvii) of ADR-0127 stay with HQ-0044. No data-plane file, member, kind or version changes. The new reason strings are told on the entry's standard output only.

## Out of Scope

- Any change to `hilclaw/run_commit.py`, `hilclaw/turn_loop.py`, `hilclaw/turn_definition.py`, `orchestration/round-manager.md` or `hilclaw/events.py`.
- The `run.commit` call right after the write that ends a round. It belongs to the P2-1 slice that writes "The round steps".
- The commit of a turn cut short, or of ADR-0121's `"over"` write that ends no round (ADR-0127 decision 8, HQ-0043).
- The other less-exact ADR sentences and docstrings that ADR-0127 Consequences lists (held under D18), and any edit to `ARCHITECTURE/`.
- The lock of two loops on one run (rest of OD-17).
- `hilclaw/start_instance.py` and the other files of the open draft PR #186.

## Follow-ups

- None planned by the planner. The next P2-1 work is the Round-Manager's round steps, which include the `run.commit` call after the round-ending write.

## Result

- DONE. PR #201 (https://github.com/myungjoo/HIL-Claw/pull/201) squash-merged as `6d23bc7` with the PR body as the message (last line `Task: T-0351`); branch `claude/T-0351-owed-p2-in-step-one` deleted.
- `hilclaw/further_turn.py`: new case `OWED = "owed"` and reasons `NO_REPOSITORY` / `COMMIT_REFUSED` (= `run_commit.KIND_NO_REPOSITORY` / `KIND_COMMIT_REFUSED`). `classify` calls `run_commit.owed_rounds` once, only when `run_status` is exactly "over": empty range -> `OVER_CASE`, non-empty -> `Finding(OWED, None)`, `NoRepositoryError` / `GitNotRunError` -> `OPEN`/`no_repository`, any `CommitRefusedError` -> `OPEN`/`commit_refused`; other exceptions pass through. P1/P3/P4 and the existing open states are unchanged and run no git; nothing writes, and `run_commit.commit` is not called. `predicate` answers `OWED` as `DUE`. Docstrings updated.
- `hilclaw/turn_start.py`: docstring only (step-1 order list and self-check paragraph name owed P2); the existing `_outcome` order already gives every behaviour of criterion 6. No new outcome, member or exit status.
- Tests: `tests/test_further_turn.py` and `tests/test_turn_start.py` use temporary git repositories with an isolated git configuration and identity; the stub `claude` can commit the data root to stand in for the entry's `run.commit`. Covered: nothing owed, owed P2 committed by one turn, owed P2 left owed (`unchanged_turn`), failed turn, P4 -> owed P2 without a second check, check not passing, no repository / git not startable, commit refused (three causes, also after a failed turn), P1/P3/P4 need no git, `predicate` on the new values. Existing P2 tests now commit the run first; `test_over_written_by_a_failed_turn_is_run_over` became two tests (committed "over" -> `run_over`; uncommitted -> `failed_turn`). Test `instance.json` fixtures gained `op_signature` (a key directory is needed once the owed range includes a round >= 1).
- Local: the two test files passed (250) with `--basetemp` outside the marker-holding home directory (with the default temp root they skip on this machine); ruff check and format clean; coverage `further_turn.py` 100%, `turn_start.py` 99%. CI: all 6 checks green.
- Review: dev-reviewer, 2 rounds — round 1 Approve with two nits (docstring wraps; unclear failure when git is missing), both fixed; round 2 Approve.
- Language: Python, because both modules are existing Python modules of the layer-2 package.
- No real `claude` started (D16). No data-plane change. Runtime acceptance items (xv)-(xvii) stay with HQ-0044. Follow-ups: none from this task; the next P2-1 work is the Round-Manager's "The round steps", including the `run.commit` call right after the round-ending write.
