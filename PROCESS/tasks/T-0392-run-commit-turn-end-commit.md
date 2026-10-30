---
id: T-0392
title: Make run.commit commit a turn end that ends no round, with the read-only owed-commit rule (ADR-0143 Consequences slice (1); PLAN P2-1/P2-4)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-13, FR-18, NFR-1, OD-8, S0, S1, S2]
dependsOn: [T-0391]
touchesFiles:
  - hilclaw/run_commit.py
  - tests/test_run_commit.py
estimatedSize: {loc: 150, files: 1}
hq: []
---
## Why

ADR-0143 (T-0391, landed on main as a3eb31c) carries out the owner's answer (a) to HQ-0043: every live end of a first-case turn commits what the run directory then holds, a dead turn's work is committed by the next turn's entry, and the case file of the round in progress is never taken into a commit that ends no round. Its Consequences list three code slices, in order:

- **Slice (1), this task**: `hilclaw/run_commit.py` — the rule of an owed commit (ADR-0143 decision 3) as a read-only function beside `owed_rounds`, the commit that ends no round, the checks of decision 3, the module docstring, `MESSAGE` and the tool description.
- Slice (2), not this task: `orchestration/round-manager.md` calls `run.commit` before every end of its session.
- Slice (3), not this task: `hilclaw/further_turn.py` and `hilclaw/turn_start.py` tell owed P2 by the function this task adds.

D18 judgement: this is not a follow-up phrasing fix. It is the code of an owner decision (HQ-0043 (a)) on which commits a run's data repository receives, made through the PLAN P2-1/P2-4 Round-Manager and commit work. P2-5 needs it: today every first-case turn ends at a stop that ends no round (ADR-0142 decision 1), so no turn of a run commits anything, and the first run's attempts and failures (FR-18, data under O1) would reach the history only at a round end. Slice (1) is the base the other two slices call.

Open HQs checked:

- HQ-0043: answered (a); this task carries out ADR-0143, which records it.
- HQ-0058 ((xlvii), runtime acceptance of the Round-Manager's call): not crossed. This task changes no prompt and starts no session.
- HQ-0021 (`board.run` registration), HQ-0053 (coder sign-in), HQ-0032 (T-0324): not crossed. No tool is registered or removed; `hilclaw/tools.py` and the start function are untouched.
- Every other open runtime-acceptance HQ: nothing is added or closed.

Open PR #186 (T-0324, draft) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None overlaps this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit) and §5 (task file format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md` (repository), "상시 규칙": comment minimisation, test rules ① to ⑤, the language policy, the code-mode branch and merge procedure (A-13), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md`: Status (lines 3-19), Context (lines 21-26), decisions 1, 3, 4 and 5 (lines 32-36, 44-62), the Walk-through (lines 78-90) and Consequences slice (1) (lines 103-106). Decision 6 (lines 63-70) only to see what slice (3) will need from the new function.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`: decision 4 (lines 50-68), which stays the rule of a round end and of everything decision 3 of ADR-0143 leaves unchanged.
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md`: decision 6 (lines 66-73), the torn tail.
- `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`: decision 7 (lines 71-77), the key record files.
- `hilclaw/run_commit.py`, the whole file (512 lines).
- `hilclaw/further_turn.py`, lines 1-160: the present caller of `owed_rounds`, which this task must not change in behaviour.
- `tests/test_run_commit.py`: lines 1-215 (helpers and fixtures) and the tests this task revises (named in criterion 6).

## Acceptance Criteria

Language: Python, the language of the existing module. State this in one line in the commit body and in `## Result`.

1. **The owed rule, read-only.** A new public function in `hilclaw/run_commit.py` beside `owed_rounds` (the executor names it, for example `commit_owed(data_root, run_id) -> bool`) answers ADR-0143 decision 3: a commit is owed when a round end is owed (ADR-0127 decision 4, unchanged), or, with none owed, when a file below `runs/<run_id>/` that the commit would take in (the same candidate set `commit` lists: not a `.tmp` name, not ignored, not a directory) is new against `HEAD` or differs from `HEAD`'s entry as `git` would record it, or a file `HEAD` holds below `runs/<run_id>/` is missing from the working tree (which then raises `FileMissingError`, criterion 3). `events.ndjson` is compared with `HEAD` only up to and including its last line feed, so a torn tail alone owes nothing. The key record files alone owe nothing. Like `owed_rounds`, it writes nothing to the working tree, the index or `HEAD`, takes no optional lock of `git`, and writes no object to the repository (no `-w`, no `git add` into the real or a temporary index that writes blobs); the docstring states what it raises.
2. **The commit that ends no round.** `commit` makes a commit whenever the function of criterion 1 says one is owed. With no round end owed: (1) the torn tail of `events.ndjson` is removed by `events.remove_torn_tail`; (2) one commit holds, against `HEAD`, every new or changed file below `runs/<run_id>/` and each key record file of ADR-0134 decision 7 that `HEAD` does not hold, and no case file (the range *H* to *W* − 1 is empty, so `case-<run_id>-<W>.json` stays untracked — ADR-0143 O2); (3) the result is `True`. Everything of today's commit path stays: the index handling, the lock, `.tmp`/ignored/`blobs/` exclusion, nothing else of the working tree or the index changed. With nothing owed the result is `False` and nothing is written (no tail removed), so a second call with nothing written in between finds nothing owed. The cases of decision 5 hold: on a fresh run directory (`instance.json` only, `HEAD` holding no file of the run) the call commits `instance.json`; a round-0 working `STATE.json` with `HEAD` holding none is committed with the other files; `HEAD` then holds `round` 0 and a later working `round` 1 owes the end of round 0 as before.
3. **The checks.** `WorkingStateError`, `HeadStateError`, `RoundBehindError` and `StateMissingError` stay checked at every call, in today's order. `FileMissingError` and `EventsNotRegularError` are raised whenever a commit is owed, round end or not (a missing tracked file makes a commit owed and so is always refused once those four pass). `NoKeyDirectoryError` stays checked only when a round end from round 1 is owed. Every refusal still leaves the working tree, the index and `HEAD` unchanged and removes nothing.
4. **`owed_rounds` keeps its behaviour**: same result for every state, and the same exceptions in the same states as today (its docstring stays true), so `hilclaw/further_turn.py` and `hilclaw/turn_start.py` behave exactly as before; slice (3) switches them. The tool's request, result, failure kinds and MCP name stay (ADR-0143 decision 4).
5. **Texts.** The module docstring states the rule of criterion 1, the commit that ends no round, the case-file exclusion and which checks run when, citing ADR-0143. `MESSAGE` no longer says "round end" only (any wording; nothing reads it). `_DESCRIPTION` (the text the model sees) states that a commit is made whenever the run directory holds new or changed files since the last commit or a round end is owed, that the case file of the round in progress is not taken in until its round ends, and that with nothing owed nothing is written so the call is safe at every entry and before every end; the words pinned by `test_the_definition_states_its_name_schema_and_failures` stay. `commit`'s docstring matches the new behaviour. No comment beyond the CLAUDE.md minimum.
6. **Tests** in `tests/test_run_commit.py` (existing tests may be revised where ADR-0143 changes the behaviour they pin; list each revised test in `## Result`): at least `test_round_zero_end_of_a_fresh_run_is_committed`, `test_inside_a_round_nothing_is_committed_even_with_changed_files`, `test_a_missing_file_is_refused_only_when_a_round_end_is_owed`, `test_events_that_are_no_regular_file_are_refused_only_when_owed`, `test_with_nothing_owed_no_record_file_is_staged_or_committed`, and the `STATES`/`ANSWERS` read-only test are expected to change or gain a counterpart. New or revised tests cover, each with the commit's file list checked:
   - happy: a fresh run directory commits `instance.json` at entry; a round-0 stop commits `STATE.json` (round 0), `events.ndjson` and the other run files plus the key record files `HEAD` lacks; a change inside round 2 is committed with `HEAD`'s `round` unchanged; then a round end commits as before;
   - branch: a torn tail alone owes nothing and is not removed; whole new lines plus a torn tail owe a commit, the tail is removed and the commit holds the lines; a changed key record file alone, or a new one alone, owes nothing; a case file of the round in progress is not taken in by a commit that ends no round and is taken in by its round's end; a second call returns `False` and leaves `HEAD` unchanged; a file mode change below the run directory (where the platform allows) is judged as `git` records it;
   - error/negative: a missing tracked file inside a round is `FileMissingError` with nothing changed; a non-regular `events.ndjson` inside a round is `EventsNotRegularError`; `NoKeyDirectoryError` is not raised when no round end is owed with an `instance.json` that gives no key; `StateMissingError`, `RoundBehindError` and an invalid working state still refuse before anything is compared; the index lock held while a commit that ends no round is owed is `commit_not_made` and the next call commits; the new function refuses a bad `run_id` as `owed_rounds` does;
   - read-only: the new function and `owed_rounds` leave `snapshot(root)` and the object count of the repository (`git count-objects -v` or equivalent) unchanged in every state of the read-only test, including one inside a round with changed files.
   Every existing test of `tests/test_further_turn.py`, `tests/test_turn_start.py`, `tests/test_mcp_front.py`, `tests/test_turn_permissions.py` passes unchanged. Coverage of `hilclaw/` stays ≥ 80 % line and function (CI gate); ruff passes.
7. **No other file changes**: `git diff --stat origin/main` lists only the two touchesFiles; `git diff --check` is clean. No data-plane member, file, kind, value, version or validator changes; no tool, failure kind, event kind or dependency is added. No `claude` process is started, real or stub (D16).

## Out of Scope

- `orchestration/round-manager.md` and every other prompt or agent file (slice (2)).
- `hilclaw/further_turn.py`, `hilclaw/turn_start.py` and owed P2 (slice (3)).
- Any ADR, Requirements, OpenDecisionProposals or StandardScenarios edit, including the ADR-0143 "Less exact, not edited" list and the round-7 Status nit of T-0391.
- Retry of a failed `run.commit`, removal of a stale `git` lock (OD-17), push or remote (ADR-0143 Boundaries), the Stop hook (P2-4 hooks).

## Follow-ups

- Slice (2) of ADR-0143: `orchestration/round-manager.md` ("Your run", the call before every end after a successful step 0, "The stop", the failed `round.end`).
- Slice (3) of ADR-0143: `hilclaw/further_turn.py` and `hilclaw/turn_start.py` tell owed P2 by the function of criterion 1.

## Result

DONE: PR #227 squash-merged as 5594875 after 3 review rounds (round 1 Approve with nits; round 2 asked to keep the task file out of the PR, done by a revert commit; round 3 Approve).

Language: Python, the language of the existing module.

- `hilclaw/run_commit.py`: new read-only `commit_owed(data_root, run_id) -> bool` (ADR-0143 decision 3). HEAD's entries of the run go into a temporary index outside the repository (`update-index --index-info`, split index off); a porcelain `git diff --raw` with the in-memory index refresh tells content and mode changes as git records them; `ls-files --others --exclude-standard` lists the new candidates with the filter `commit` uses; `events.ndjson` is compared up to its last line feed by `hash-object` without `-w` (one HEAD lacks counts as empty). No object, no optional lock. `commit` commits whenever a commit is owed; with no round end owed no case file is taken in. `owed_rounds` keeps its results and exceptions. Module docstring, `commit` docstring, `MESSAGE` and `_DESCRIPTION` updated.
- Revised tests: `test_round_zero_end_of_a_fresh_run_is_committed` (now commits `instance.json` at entry and round 0 at its stop), `test_a_repository_without_head_owes_nothing_at_round_zero_or_without_a_state` → `test_a_repository_without_head_commits_the_run_at_round_zero_or_without_a_state`, `test_no_run_directory_owes_nothing` (also `commit_owed`), `test_inside_a_round_nothing_is_committed_even_with_changed_files` → `test_inside_a_round_the_changed_files_are_committed_with_the_round_unchanged`, `test_with_nothing_owed_no_record_file_is_staged_or_committed` (also `commit_owed`), `test_a_missing_file_is_refused_only_when_a_round_end_is_owed` → `test_a_missing_file_is_refused_inside_a_round_and_at_its_end`, `test_events_that_are_no_regular_file_are_refused_only_when_owed` → `test_events_that_are_no_regular_file_are_refused_whenever_owed`, the helper `refused_unchanged` (now also `commit_owed`), `STATES`/`ANSWERS` and `test_the_read_only_answer_writes_nothing` → `test_the_read_only_answers_write_nothing` (both functions, object count, states "nothing" and "inside changed"), `test_the_read_only_answer_refuses_a_bad_run_id` → `test_the_read_only_answers_refuse_a_bad_run_id`.
- New tests: round-0 stop with record files; torn tail alone (tracked and new log); case file of the round in progress; changed tracked file alone; tracked and new `.tmp`; mode change as git records it; log changed beyond a torn tail; log as a symbolic link (skipped where no link can be made); changed record file alone; no key directory asked inside a round; the every-call checks before any comparison; held index lock inside a round; git failing each comparison step; unreadable log.
- Local: full suite 25612 passed, 738 skipped; `hilclaw/` 97 % line and function coverage (`run_commit.py` 98 %); ruff clean. Symbolic-link tests and the `core.fileMode=true` branch of the mode test do not run on this Windows machine; CI (Linux) runs them.
- Notes for later slices (not done here): `commit_owed` can raise `CommitNotMadeError` (git failing a comparison step, unreadable log), which `further_turn.py` does not catch today; slice (3) must map it. Each call with no round end owed rehashes every tracked file below the run directory (no cached stat information), a cost that grows with the run's history; a later task may bound it if it matters.
