---
id: T-0523
title: Remove the check builders and the read-stepped tool builders no caller uses, and name the build log through layout (HQ-0080 group B)
phase: P2
status: DONE
commitMode: code
coversReq: [HQ-0080, "ADR-0183", "ADR-0078"]
dependsOn: []
touchesFiles:
  - hilclaw/check_result.py
  - hilclaw/check_judging.py
  - hilclaw/hw_tool.py
  - hilclaw/journaled_tool.py
  - hilclaw/spec_feedback.py
  - tests/test_check_result.py
  - tests/test_check_judging.py
  - tests/test_hw_tool.py
  - tests/test_journaled_tool.py
  - tests/test_spec_feedback.py
estimatedSize: {loc: 520, files: 5}
hq: []
---
## Why

The owner approved group B of the PLAN hold section in HQ-0080 ("dead code and refactoring"). The lines are not judged again here, and P2-15 does not need this work. It leaves four hold lines:

- T-0510 follow-up: the old check result builders no tool calls since ADR-0183 decision 9 item 2.
- T-0510 planning: `hw_tool.read_stepped_tool_function` and `journaled_tool.read_stepped_function`, which have no caller outside their own tests.
- T-0243 follow-up: `hilclaw/spec_feedback.py` writes the build log file name by hand although `layout.build_log_file` exists.
- T-0359 follow-up: merge `check_identity._STEP_OF` with `checks_tool.STEP_OF`. The planner found no work left: `checks_tool` no longer has `STEP_OF`, and `tests/test_checks_tool.py` asserts that. The `_STEP_OF` in `hilclaw/run_identity.py` maps other values and is not part of this line.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5.
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md`, decision 9 item 2.
- `hilclaw/check_result.py` and `hilclaw/check_judging.py`: module docstrings and the functions named below.
- `hilclaw/hw_tool.py` and `hilclaw/journaled_tool.py`: module docstrings and the read-stepped functions.
- `hilclaw/spec_feedback.py`, the `build-log-` line near line 291, and `hilclaw/layout.py` `build_log_file`.

## Acceptance Criteria

1. **Check builders removed.** `check_result.completed`, `broken`, `bf16_completed`, `bf16_broken` and `BF16_KINDS`, and `check_judging.from_judgement`, `from_report`, `from_bf16_judgement` and `from_bf16_report`, are gone, with every private name only they used. First confirm with `git grep` over `hilclaw/`, `orchestration/` and `tests/` that only these two modules and their test files use them. If another user exists, keep what it needs and say so in `## Result`.
2. **What stays.** `DrawCounts.cache_differences` stays, because `hilclaw/harness/bf16_sdpa_kv_cache_verification.py` uses it. All v2 functions, `PASS`, `FAIL`, `BROKEN`, `CONDITIONS`, `BIT_EXACT`, `output_operands` and `condition_of` keep their behaviour.
3. **Docstrings of the surviving code.** No docstring in `hilclaw/` names a removed function. `from_v2_judgement` and `from_v2_report` say "As `from_judgement`" and the like today, so they must state their checks themselves. The sentences saying that the removal "follows in a later task" go. The module's import sentence stays true.
4. **Read-stepped builders removed.** `hw_tool.read_stepped_tool_function` and `journaled_tool.read_stepped_function` are gone, with every private name only they used and the docstring text describing them. Confirm first with `git grep` that no module calls them. `tool_function`, `stepped_tool_function`, `checked_function` and `stepped_function` keep their behaviour.
5. **Build log name.** `spec_feedback` gets the log path from `layout.build_log_file`. The answer of `spec.write` stays the same for every line the module admits. `build_log_file` refuses a `step` outside `BUILD_LOG_STEPS` and an out-of-range `execution`. Check whether a line that reaches this code can hold such a value. If one can, keep today's outcome for it and add a test; say which case held in `## Result`.
6. **T-0359 line.** Confirm the finding in Why. Make no change for it and say so in `## Result`.
7. **Tests (D12).** Tests of removed functions go with them. The remaining public functions of the touched modules stay covered, including the v2 happy, error, branch and negative cases that the removed tests may have been the only ones to reach. Check this in the coverage report for `check_result` and `check_judging`, and add a test where a surviving line loses its coverage. Line and function coverage of `hilclaw/` stay at or above 80 %.
8. **List pins (D21).** Foreseen edits: the public-name assertions in `tests/test_check_result.py` (`test_public_names_of_the_module`), `tests/test_check_judging.py` (`test_public_names_of_the_module_and_no_default`, and `test_module_imports_the_builder_and_the_judging_only_and_has_no_entry` if an import drops), `tests/test_hw_tool.py` (`test_the_public_names_and_the_signature`) and `tests/test_journaled_tool.py` (its public-name assertion). List every such edit in the PR body. Other assertions on surviving behaviour stay unchanged.
9. **No behaviour change** of any registered tool. The size is mostly deleted lines; if it passes the §5 cap, propose the split in Follow-ups.
10. `## Result` records the language line: Python, the language of the touched modules.

## Out of Scope

- Any file under `ARCHITECTURE/`, including sentences in ADRs that name the removed functions.
- The JSON text helpers (T-0524).
- The other hold lines, including T-0510's stale-docstring line, which T-0522 closed.
- A real `claude`, a Docker daemon or a D25 test run.

## Follow-ups

- **Size, proposed split** (criterion 9): the change is about 2780 changed lines (644 in, 2132 out) over 10 files, above the DRIVER §5 cap of 600 lines; nearly all of it is deletion and tests moved to v2. It could have landed as three tasks: `check_result` and `check_judging` with their tests; the two read-stepped builders; the `spec_feedback` line. No further work is proposed.

## Result

- **Outcome**: DONE. PR #343 squash-merged as `d346d0e6` after 2 review rounds (round 1 Request changes: one Should-fix, one Nit, both fixed; round 2 Approve with no findings). CI green on `ace7660d`: Python gate 3.11/3.14, Coverage gate, C, sh, test-presence. Locally only the affected test modules and `ruff` ran; the one full-suite run was CI's.
- **Language**: Python, the language of the touched modules.
- **Criteria 1 and 4**: `git grep` over `hilclaw/`, `orchestration/` and `tests/` found no other user of the removed names, so nothing was kept for one. Same-named items are separate: the helpers `bf16_broken` in `tests/test_checks_tool.py` and `tests/test_spec_feedback.py`, the constants `BF16_KINDS` in `tests/test_run_tool.py` and `tests/test_standin_run.py`, `check_answer._BF16_KINDS`, and `run_result.completed` and `run_result.broken`.
- **Beyond the named lines**: `_bf16_judge` lost its `type(kind) is str` guard, because its kind now always comes from a contract, and the `from_v2_report` docstring now names the `dims` that `start_position` refuses, as the removed `from_bf16_report` docstring did.
- **Criterion 5, which case held**: no line that reaches this code can hold a value `build_log_file` refuses. `step` is an item of `check_standing.STEPS_OF`, both of which are in `BUILD_LOG_STEPS`, and `journal.identity_of` has already checked `execution` as an exact `int` from 1 to `MAX_INTEGER`, the range `layout` admits. No outcome needed keeping. The added test `test_a_compiler_log_is_found_by_the_name_of_the_layout` pins the name at executions 1, 100 and `MAX_INTEGER`.
- **Criterion 6, T-0359 line**: confirmed, no change. `checks_tool` has no `STEP_OF` and `tests/test_checks_tool.py` asserts that. `run_identity._STEP_OF` maps other values.
- **Criterion 7**: `check_result` and `check_judging` have 100 % line coverage from their own two test files, measured before the round 1 fix, which only added a test case and docstring text. The Coverage gate passed for `hilclaw/`.
- **Criterion 8**: edits of the public-name assertions are listed in the PR body. `test_module_imports_the_builder_and_the_judging_only_and_has_no_entry` is unchanged, because no import dropped. Beyond the foreseen edits, `test_public_names_of_the_module_and_no_default` lost its keyword-only loop over the removed functions, and the v2 sdpa test lost its comparison with `from_bf16_report` and was renamed `test_an_sdpa_report_gives_per_allocation_v2_counts`.
- **Runtime acceptance**: none.
