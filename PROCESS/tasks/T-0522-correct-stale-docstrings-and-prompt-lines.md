---
id: T-0522
title: Correct stale module docstrings and Round-Manager prompt lines (HQ-0080 group A)
phase: P2
status: DONE
commitMode: code
coversReq: [HQ-0080, FR-1, OD-31]
dependsOn: [T-0521]
touchesFiles:
  - hilclaw/standin_profile.py
  - hilclaw/standin_answer.py
  - hilclaw/standin_container.py
  - hilclaw/standin_copies.py
  - hilclaw/standin_image.py
  - hilclaw/standin_waiter_line.py
  - hilclaw/events.py
  - hilclaw/gemm_contract.py
  - hilclaw/turn_definition.py
  - hilclaw/spec_feedback.py
  - hilclaw/checkout_boundary.py
  - hilclaw/model_program.c
  - hilclaw/case_lookup.py
  - hilclaw/rope_table.py
  - hilclaw/check_seed.py
  - orchestration/round-manager.md
estimatedSize: {loc: 60, files: 16}
hq: []
---
## Why

The owner approved group A of the PLAN hold section in HQ-0080 ("code wording and prompts"). The lines are not judged again here. For the lines that also list ADR sentences, HQ-0080 dropped the ADR part, so only code and prompt text is in scope.

The prompt line matters most, because a real model reads it: `orchestration/round-manager.md` says "The session ends after the write that ends its round", while its own section "The end of a session" has `run_commit` follow that write. The docstrings mislead the next reader of a module.

This task touches 16 files against the DRIVER §5 cap of 10. It is a deliberate batch of small edits, about 60 lines against the 600 line cap, and HQ-0080 approved the group as one. Say so in the PR body. If a reviewer asks for a split, propose it in Follow-ups (DRIVER §5).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5.
- Each file below, at the place named. To learn what is true now, search for importers (`git grep -n "<module>" -- hilclaw`).
- `orchestration/round-manager.md`: lines 6-14, 27-34 and 65-90.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` lines 56-71, and ADR-0143 decision 2, for criterion 1.

## Acceptance Criteria

Each sentence is rewritten to what the code does now, or removed if it says nothing useful once corrected. A sentence the search shows to be still true stays, and `## Result` says so. Keep each edit to that sentence; no reflow of its neighbours and no new claims.

1. `orchestration/round-manager.md`, "One round at most": the session ends after the `mcp__hilclaw__run_commit` call that follows the write ending its round, citing "The end of a session" or ADR-0143 decision 2. It must not contradict closing step 3.
2. `orchestration/round-manager.md` line 31, "not Bash or file tools": ADR-0139 Consequences lists it as less exact. Change it only if a tool list in the definition now contradicts it; otherwise leave it and say so.
3. `hilclaw/turn_definition.py` module docstring: the sentence ADR-0139 Consequences lists as less exact (read `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md` line 157). The turn loop now writes `.claude/settings.json` itself and refuses a definition's own, so "`.claude/settings.json`" among the names the definition gets is the candidate.
4. `hilclaw/events.py` `remove_torn_tail`: "for the step that commits the data repository" names `run.commit` (`hilclaw/run_commit.py`).
5. `hilclaw/standin_profile.py` and `hilclaw/standin_answer.py`, "is bound to no tool" and "nothing imports it yet"; `hilclaw/standin_copies.py` and `hilclaw/standin_image.py`, "nothing calls it yet"; `hilclaw/standin_waiter_line.py`, "ADR-0144 slice (4) will call it"; `hilclaw/standin_container.py`, "bound to no tool" (check it against `hilclaw/standin_openmp.py` and `hilclaw/coder_runtime.py`).
6. `hilclaw/gemm_contract.py`: "It is bound to one tool: `covers` is the predicate of the `correctness.check` …" (`spec.write` also calls `covers` and `task_contract`).
7. `hilclaw/spec_feedback.py`: "Nothing calls this module until `spec.write` … is widened".
8. `hilclaw/checkout_boundary.py`: the users it names are `hilclaw.scratch` and `hilclaw.selfcheck_session`. The importers now also include `bring_in`, `coder_runtime`, `model_execute`, `selfcheck_server` and `turn_loop`. Check what each uses. Name those that do use the test, or word the sentence so that it does not list them.
9. `hilclaw/model_program.c` header: "It is not yet a forward pass (ADR-0153 code slice 2)" and "first code slice" (ADR-0166 made the program a forward program).
10. `hilclaw/case_lookup.py`: the sentences T-0484 Result named less exact, about who calls the lookup and how a selection takes its output (read `PROCESS/tasks/T-0484-hypotheses-write-and-technique-selector.md` line 167 and the `git grep` for `case_lookup`).
11. `hilclaw/rope_table.py`, `**Inputs.**`: the scale factor 8 or 32 is no longer open. The owner answered 32 in HQ-0070 (ADR-0176 O2); the value stays the caller's input.
12. `hilclaw/check_seed.py` line 41: drop the removed `check_admission.admit_for_step`, keeping `admit`. Confirm with `git grep admit_for_step -- hilclaw` that nothing else names it.
13. **No behaviour changes.** The C file's code is unchanged; only its comment changes. The existing test suite passes unchanged, except list-pinning edits DRIVER §5 allows (D21). None is foreseen. A test that pins a prompt line of criteria 1 or 2 may follow that line's new text; list it in the PR body. New tests are not needed, because nothing executable changes.
14. `ARCHITECTURE/` is not edited (HQ-0080 dropped the ADR parts of these lines).

## Out of Scope

- Any ADR, Requirements or OpenDecisionProposals sentence.
- Docstrings outside these lines, including those named by hold lines outside HQ-0080.
- Removing dead code (group B).
- A real `claude`, a Docker daemon or a D25 test run.

## Follow-ups

## Result

- **Outcome**: DONE. PR #342 squash-merged as `8c2bb517` after 3 review rounds (round 1 Request changes: one Should-fix, one Nit; round 2 Approve with 2 Nits, both fixed; round 3 Approve after a CI fix, with one PR body Nit fixed after it, D20). CI green on `d9bab112`: Python gate 3.11/3.14, Coverage gate, C, sh, test-presence. Locally only the affected test modules and `ruff` ran; the one full-suite run was CI's (`-n auto` is not available locally).
- **Edited**: criterion 1 (`orchestration/round-manager.md`), 3 (`turn_definition`), 4 (`events`), 5 (`standin_profile`, `standin_answer`, `standin_container`, `standin_copies`, `standin_image`, `standin_waiter_line`), 8 (`checkout_boundary`), 9 (`model_program.c`), 11 (`rope_table`), 12 (`check_seed`; `git grep admit_for_step -- hilclaw` is now empty).
- **Left as is, still true**: criterion 2, `round-manager.md` "not Bash or file tools": no tool list contradicts it (the session has `Read`, `Grep`, `Glob`; ADR-0139 decisions 4 and 6). Criterion 6, `gemm_contract.py`: the "bound to one tool" sentence is already gone. Criterion 7, `spec_feedback.py`: "Nothing calls this module until" is already gone. Criterion 10, `case_lookup.py`: T-0488 already rewrote those sentences, and they match `cases_tool` and ADR-0173.
- **A task premise that differs**: criterion 9 says ADR-0166 made `model_program.c` a forward program. ADR-0166 (Context, alternative 1) keeps it as the GEMM-list program and adds `model_forward.c`, so the header now says that.
- **Criterion 8**: named `scratch`, `selfcheck_session`, `turn_loop`, `model_execute` (with `keep_out`) and `standin_check` (package directory alone). `bring_in` and `coder_runtime` use only `within`, and `selfcheck_server` only reads `PACKAGE_DIRECTORY`, so they are not named. `standin_check` is an importer the task's list omits.
- **Criterion 5, `standin_container`**: its direct callers are `standin_openmp`, `standin_profile` and `model_forward_container`, but `tests/test_standin_profile.py::test_module_is_bound_by_the_start_only_and_imports_no_store` lets only three modules name `standin_profile`. The sentence therefore says "other modules of the package". No test changed.
- **Noticed, not edited (out of scope)**: `standin_answer.py` line 8 still says "ahead of the operations of ADR-0144 slice (4)". `standin_copies.py` `place_harness_copy` is also called by `model_forward_container`, which the docstring does not say.
- **Runtime acceptance**: none. The prompt line changes wording only.
