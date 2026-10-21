---
id: T-0394
title: Tell owed P2 in step 1 of the turn loop by run_commit.commit_owed (ADR-0143 Consequences slice (3); PLAN P2-1/P2-4)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-13, NFR-1, OD-8, OD-19, S0, S1, S2]
dependsOn: [T-0391, T-0392, T-0393]
touchesFiles:
  - hilclaw/further_turn.py
  - hilclaw/turn_start.py
  - tests/test_further_turn.py
  - tests/test_turn_start.py
estimatedSize: {loc: 60, files: 2}
hq: []
---
## Why

ADR-0143 (T-0391, main a3eb31c) carries out the owner's answer (a) to HQ-0043: every live end of a first-case turn commits what the run directory then holds, and after a death the next turn's entry commits what the dead turn left. Its Consequences list three code slices, in order:

- Slice (1), done by T-0392 (PR #227, main 5594875): `hilclaw.run_commit.commit` commits whenever a commit is owed, and the new read-only `run_commit.commit_owed` tells whether one is.
- Slice (2), done by T-0393 (PR #228, main ce26ac3): the Round-Manager calls `run.commit` before every end of its session after a successful entry step 0.
- **Slice (3), this task**: `hilclaw/further_turn.py` and `hilclaw/turn_start.py` tell owed P2 by `commit_owed` instead of `owed_rounds` (ADR-0143 decision 6), with their docstrings.

Today `further_turn._p2` asks `run_commit.owed_rounds`, so a run whose `"over"` was written by ADR-0121's own write (entry step 6, *W* = *H*) and left uncommitted by a death is classified as P2 with nothing owed: step 1 tells "run over" and no turn ever commits it, which breaks O1 of ADR-0143 ("after a death the next turn's entry commits what the dead turn left"). Since slice (1), the tool and step 1 also disagree on what "owed" means.

D18 judgement: this is the last code slice of an owner decision (HQ-0043 (a)), made through the PLAN P2-1 turn loop and the P2-4 commit work. P2-5 needs it: the first end-to-end run ends on `"over"`, and a run that ends must leave its last state committed in the data repository by the rule step 1 applies. The T-0392 Result also notes that `commit_owed` can raise `CommitNotMadeError`, which `further_turn` does not catch today; with the switch, an uncaught exception would surface as the `fault` error of `turn_start` instead of an answer of ADR-0127 decision 6.

Open HQs checked:

- HQ-0043: answered (a); ADR-0143 records it.
- HQ-0058 (runtime acceptance item (xlvii), a live Round-Manager's call) stays open and non-blocking; this task does not touch the prompt.
- HQ-0021 (`board.run` registration), HQ-0032 (T-0324), HQ-0053 and every other open HQ: not crossed.

Open PR #186 (T-0324, draft) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. None overlaps this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit) and §5 (task file format, naming convention, D4 size cap, D12 test rules).
- `CLAUDE.md` (repository), "상시 규칙": comment minimisation, test rules ① to ⑤, the code-mode branch and merge procedure (A-13), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md`: Status (lines 3-19), decision 3 (lines 44-51), decision 6 (lines 63-69), the Walk-through rows "ADR-0121's own `"over"` write", "The same, with a death before that call" and "Entry step 0 fails" (lines 87-89), Consequences slice (3) (line 108) and the docstring item of "Less exact, not edited" (line 113).
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` decision 6 (lines 76-83): owed P2, the self-check, failed and unchanged turns, and "If the rule cannot be applied".
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md` decisions 2 to 5 (lines 45-89).
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md` decision 5 (from line 73).
- `hilclaw/further_turn.py`, the whole file (192 lines).
- `hilclaw/turn_start.py`, the module docstring and `_outcome` (lines 1-190).
- `hilclaw/run_commit.py`: the constants `KIND_*` (lines 55-70), the exception classes (lines 118-160), and the docstrings of `owed_rounds` and `commit_owed` (lines 170-212).
- `tests/test_further_turn.py`: lines 1-240 (imports, fixtures `owed`, `owed_without_head`, public-name test) and lines 540-752 (P2 and the owed rule).
- `tests/test_turn_start.py`: lines 280-410 (fixtures `over`, `owed`, `settle`) and lines 780-935 (precedence, owed P2, commit refused).

## Acceptance Criteria

Language: Python, the language of the existing modules. State this in one line in the commit body and in `## Result`.

1. **The rule.** `further_turn._p2` calls `run_commit.commit_owed(data_root, run_id)` exactly once instead of `owed_rounds`: `True` gives `Finding(OWED, None)`, `False` gives `Finding(OVER_CASE, None)` (ADR-0143 decision 6, revising ADR-0127 decision 6). No other state calls git (unchanged), and `owed_rounds` is no longer called by this module.
2. **Where the rule cannot be applied** (ADR-0127 decision 6 "If the rule cannot be applied", with the conditions of ADR-0143 decision 3; ADR-0143 decision 6 last bullet): `NoRepositoryError` and `GitNotRunError` stay `OPEN` with `NO_REPOSITORY`; every `CommitRefusedError` stays `OPEN` with `COMMIT_REFUSED`, now including `FileMissingError` and `EventsNotRegularError` whenever a commit is owed. `CommitNotMadeError` (git failed a comparison step or `events.ndjson` could not be read) gives `OPEN` with a new reason constant `COMMIT_NOT_MADE = run_commit.KIND_COMMIT_NOT_MADE` — ADR-0127 decision 6 has the package function answer "what the tool would answer there with nothing committed", and that is the tool's `commit_not_made`. Any other exception passes through unchanged. If the executor or reviewer reads ADR-0127/ADR-0143 as forbidding this mapping or as requiring another reason value, stop and return BLOCKED (`requirement-unclear`) rather than choose a different answer.
3. **`turn_start`** needs no code change: `_outcome` already tells any `OPEN` reason as `open_state` with `reason`. Verify this; if a code change turns out to be needed, keep it within the module and list it in `## Result`.
4. **Docstrings** match the new rule, without restating the ADR: in `further_turn.py`, the module docstring's P2 and owed-P2 bullets ("no round end is owed" / "a round end owed" become "no commit is owed" / "a commit owed", citing ADR-0143 decision 6), the paragraph naming `owed_rounds` (now `commit_owed`), the `Finding` docstring ("nine reason constants" becomes ten, `COMMIT_NOT_MADE` named) and the `classify` docstring (the one `commit_owed` call and the four exception mappings). In `turn_start.py`, the step-1 list item 1 ("with no round end owed" becomes "with no commit owed") and any other sentence that defines owed P2 by a round end. No other docstring or module is edited.
5. **Tests** in `tests/test_further_turn.py` (the module's public names test gains `COMMIT_NOT_MADE` and its equality with `run_commit.KIND_COMMIT_NOT_MADE == "commit_not_made"`); revised tests are listed by name in `## Result`:
   - happy: P2 whose `"over"` was written with *W* = *H* and not committed (the case ADR-0143 decision 6 adds) is `Finding(OWED, None)` and the predicate answers a further turn before the first turn and after exit status 0; P2 with `"over"` committed and nothing else changed is still `OVER_CASE`; P2 with only a torn tail of `events.ndjson` or only changed key record files is `OVER_CASE` (neither owes a commit — ADR-0143 decision 3); the existing owed fixtures (round end owed, with and without `HEAD`) are still `OWED`.
   - branch: a changed tracked file below the run directory alone, and a new untracked file there alone, each make P2 `OWED`; a `.tmp` file alone does not; the rule is asked exactly once per `classify` (replace the monkeypatched `owed_rounds` counters with `commit_owed`).
   - negative: `CommitNotMadeError` from `commit_owed` gives `OPEN` with `COMMIT_NOT_MADE` (monkeypatched, in the style of `test_every_refusal_is_commit_refused`); `FileMissingError` with *W* = *H* (a tracked file removed) gives `OPEN` with `COMMIT_REFUSED`; another exception passes through; states other than P2 still need no git (the `refuse` monkeypatch now replaces `commit_owed`); an invalid run id and a missing data root still raise before the rule.
   In `tests/test_turn_start.py`:
   - happy: a start on a P2 run whose `"over"` is uncommitted with *W* = *H* runs the self-check and one turn; a stub turn that commits leads to `run_over` (the Walk-through row "The same, with a death before that call").
   - branch: `test_over_written_by_a_failed_turn_without_a_commit` and any other test whose fixture leaves a P2 run with uncommitted changes is revised to the new answer (owed P2, so a failed turn is `failed_turn` and an exit-0 turn that leaves it owed is `unchanged_turn`); each revision is named in `## Result` with the reason.
   - negative: a P2 run where `commit_owed` raises `CommitNotMadeError` tells `open_state` with `reason` `commit_not_made`, exit status 13, and starts no turn and no check.
   Every other existing test of `tests/test_further_turn.py`, `tests/test_turn_start.py`, `tests/test_run_commit.py` and `tests/test_turn_loop.py` passes, unchanged where its state is not affected. Tests use temporary git repositories and the existing stub `claude` only. Coverage of `hilclaw/` stays ≥ 80 % line and function; ruff check and ruff format pass.
6. **No other file changes**: `git diff --stat origin/main` lists only the touchesFiles; `git diff --check` is clean. No tool, registry entry, data-plane member, kind, file or validator is added or changed; the request, result and failure kinds of `run.commit` stay. No `claude` process is started other than the stub the tests write (D16).

## Out of Scope

- `hilclaw/run_commit.py` (slice (1), done) and `orchestration/round-manager.md` (slice (2), done), including the T-0349 follow-ups held in PLAN "보류".
- The cost of `commit_owed` rehashing every tracked file below the run directory (T-0392 Result note); do not optimise it here.
- The self-check rules and the turn loop itself (`hilclaw/turn_loop.py`, `hilclaw/selfcheck*.py`): unchanged by ADR-0143 decision 6.
- The lock of two loops on one run and any retry of `run.commit` (rest of OD-17).
- Any ADR, Requirements, OpenDecisionProposals, StandardScenarios or UsageCases edit, including ADR-0143's "Less exact, not edited" list and the T-0391 round-7 nit.

## Follow-ups

- None planned. ADR-0143's three code slices are complete once this lands; whether PLAN P2-1/P2-4 can be checked is left to the next planner reading of PLAN.

## Result

- Outcome: `further_turn._p2` asks `run_commit.commit_owed` once instead of `owed_rounds` (ADR-0143 decision 6); `CommitNotMadeError` now gives `OPEN` with the new `COMMIT_NOT_MADE = run_commit.KIND_COMMIT_NOT_MADE` instead of passing through to `turn_start`'s `fault`. Language: Python, the language of the existing modules.
- `turn_start`: no code change needed; `_outcome` tells every `OPEN` reason as `open_state` with `reason`, verified by the new test with `commit_not_made` (exit 13, no check, no turn). Docstring step-1 item 1 now reads "with no commit owed"; item 4 keeps its ADR-0127 decision 6 citation (the failed-turn rule is that decision's, unchanged).
- Revised tests in `tests/test_further_turn.py`: `test_the_public_names` (`COMMIT_NOT_MADE`, ten reasons); `counted` now wraps `commit_owed` and refuses `owed_rounds`, so `test_p2_with_nothing_owed_asks_the_rule_once` became `test_p2_asks_the_rule_once` (over, owed, over uncommitted); `test_p2_at_round_zero_without_head_owes_nothing` became `test_p2_at_round_zero_without_head_is_owed` (without `HEAD` every file of the run is new, so a commit is owed under ADR-0143 decision 3); `test_owed_p2_is_a_further_turn` gains the *W* = *H* fixture; `test_every_refusal_is_commit_refused` patches `commit_owed` and gains `EventsNotRegularError`; `test_another_exception_of_the_rule_passes_through` drops `CommitNotMadeError` (now mapped) and patches `commit_owed`; `test_other_states_need_no_git`, `test_a_missing_data_root_raises_before_the_rule` and `test_an_invalid_run_id` refuse `commit_owed`; `test_nothing_in_the_run_changes` gains the *W* = *H* and `.tmp` fixtures; `P2_OPEN` gains a removed tracked file with *W* = *H* (`COMMIT_REFUSED`).
- New tests in `tests/test_further_turn.py`: `test_p2_committed_with_nothing_changed_owes_nothing`, `test_over_written_without_a_round_end_and_not_committed_is_owed`, `test_a_torn_tail_alone_owes_nothing` (with and without a committed log), `test_key_record_files_alone_owe_nothing`, `test_a_changed_tracked_file_alone_is_owed`, `test_a_new_untracked_file_alone_is_owed`, `test_a_tmp_file_alone_owes_nothing`, `test_a_commit_not_made_is_open`.
- `tests/test_turn_start.py`: new `test_over_left_uncommitted_by_a_death_checks_and_its_turn_commits` (the Walk-through row "The same, with a death before that call"), `test_over_left_uncommitted_and_left_owed_is_an_unchanged_turn`, `test_over_left_uncommitted_with_a_failed_turn`, `test_p2_where_the_commit_cannot_be_compared`. No existing test needed revision: `test_over_written_by_a_failed_turn_without_a_commit` already answered `failed_turn` (its run has no `HEAD`, so a round end was owed before as well), and no other fixture leaves a P2 run with only non-round-end changes.
- Review: round 1 Approve with one nit (the module docstring did not say `commit_owed` also compares `round`), fixed in round 2.
- Local: full suite 25859 passed, 522 skipped (pytest `--basetemp` outside `%TEMP%`, which holds a stray `CLAUDE.md` marker that makes the turn-loop tests skip); coverage of `hilclaw/` 99 % (further_turn 100 %, turn_start 99 %); ruff check and format clean; `git diff --check` clean.
