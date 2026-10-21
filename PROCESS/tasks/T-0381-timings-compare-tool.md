---
id: T-0381
title: Add the registry tool timings.compare of ADR-0140 decisions 3 and 4 and register it in the default registry (ADR-0140 Consequences slice 1; PLAN P2-3)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-17, OD-16, OD-23, OD-18, OD-30, S0, S1]
dependsOn: [T-0380]
touchesFiles:
  - hilclaw/timings_tool.py
  - hilclaw/tools.py
  - hilclaw/run_identity.py
  - tests/test_timings_tool.py
  - tests/test___main__.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_tools.py
estimatedSize: {loc: 290, files: 3}
hq: []
---
## Why

ADR-0140 (task T-0380, landed on `main` as 230e70b) decides how the evaluator of a first-case turn gets the `difference` of a `comparison` entry of `verdicts.json`. The evaluator calls a new typed registry tool, `timings.compare` (MCP name `mcp__hilclaw__timings_compare`). The tool reads the one journaled timing measurement of each of two attempts at a point and applies the rule of ADR-0007 decision 7. `verdicts.write` later recomputes each entry by the same function. ADR-0140 Consequences lists three code slices. Slice 1 is marked "Now": the tool in a module of `hilclaw/` with its test file, registered in `default_registry` of `hilclaw/tools.py` with its docstring, plus the `hilclaw/run_identity.py` docstring ("which of several executions counts"). This task is slice 1. Slice 2 (`verdicts.write`: `comparison_not_given` removed, `timing_result_invalid`, `comparison_unfounded`, `comparison_unverified`) and slice 3 (`orchestration/agents/evaluator.md` and its `tools` test) are later tasks.

Priority (DRIVER §6, D18): this is work on the checklist item PLAN P2-3 (evaluator). ADR-0140 is the OD-16 / OD-23 record that the item requires. Without the comparison, every verdict of the first run (P2-5, the near goal) stays `inconclusive` even after the run tools are registered. This task is not input hardening, a refactor or a wording cleanup.

Open HQs checked (HQ-0013 to HQ-0055): none is crossed. `sim.run` and `board.run` stay unregistered, and the tool only reads end lines that a fixture log holds (HQ-0021). The tool is a registry read and gives no shell (HQ-0040). It names no model or budget (HQ-0041). It does not touch the selection role or `hypotheses.write` (HQ-0048). Its files do not overlap open draft PR #186 (T-0324, HQ-0032), which touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the language policy, the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md`, the whole file. This is the specification. Read closely: **decision 2**, **decision 3 with its table and every bullet under it**, **decision 4**, the Walk-through rows, and Consequences slice 1. Decision 5 is read only to know what slice 2 will reuse.
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`: decisions 4, 5, 7 and 9 (one measurement, `n_min`, the ordered pair, the fixed seed).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decisions 2 to 5 (`outcome`, a broken run, `intervals_ns`, `shape`).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: decision 3 (the two `step` values).
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decision 3 (the `comparison` entry: `against` = A, `measured` = B, `difference`).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`: decision 3 (the read of the log and the widening of the reserved kinds, which `timings.compare` repeats).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decisions 1 and 4 (start and end lines, the "open" identity).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 2 to 4. `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md`: decisions 1 to 4. `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md`: decisions 2 to 4 (what the `ACCEPTED` entry of the new tool must satisfy).
- `hilclaw/checks_tool.py`, the whole file. This is the closest pattern: request check, data-root source, `log_lines`, the scoped step-line pass, description, input schema, no journaling. Reuse `log_lines`; do not change it.
- `hilclaw/harness/measurement.py`: the module docstring, `N_MIN`, `DELTA`, `RESAMPLES`, `SEED`, `InvalidSamplesError`, `ratio_interval` and `is_different`.
- `hilclaw/run_identity.py`, the whole file. `hilclaw/run_result.py`: the module docstring and `CONVERGED`, `NOT_CONVERGED`, `BROKEN`.
- `hilclaw/journal.py`: the module docstring, `JournalError`, `Identity`, `identity_of`, `STEP_STARTED`, `STEP_ENDED`. `hilclaw/hypotheses.py`: `_METRICS`. `hilclaw/layout.py`: `check_run_id`. `hilclaw/keys.py`: `MAX_INTEGER`.
- `hilclaw/tools.py`: the module docstring, `ToolDefinition`, `ToolFailure`, the kind constants, `RESERVED_KINDS`, and `default_registry` with its docstring. `hilclaw/mcp_front.py`: `mcp_name`.
- Tests as the pattern for the new test file and for the listing tests that must be updated: `tests/test_checks_tool.py`, `tests/test_default_registry_schemas.py` (note that its schema reading knows only the keywords `type`, `enum`, `minimum`, `maximum`, `pattern` inside a property), and the `checks.read` / `checks_read` entries in `tests/test___main__.py`, `tests/test_blob_tools.py`, `tests/test_check_definition.py`, `tests/test_mcp_front.py` and `tests/test_tools.py`.

## Acceptance Criteria

1. **New module** `hilclaw/timings_tool.py`. The executor may choose a clearer name and then updates `touchesFiles` in `## Result`. Its module docstring names ADR-0140 decisions 3 and 4 and states the request, the result, the checks in order with their kinds, the measurement rule of one `ref` at one point, the rule applied, and the choices left to the slice (ADR-0140 decision 3, "Left to the code slice"). It exposes `definition(source)`, which returns one `tools.ToolDefinition` for `timings.compare` bound to the data-root source `source`. The source is not called at definition time. A non-callable `source` raises `TypeError`, as `checks_tool.definition` does.
2. **Shared computation for slice 2.** The work after the log read (the step-line pass for the two named attempts, the measurement of each side, `shapes_differ`, `samples_out_of_domain`, and the `difference`) is a public function of the module that takes the `run_id`, the lines as `checks_tool.log_lines` returns them, and the entry's `metric`, `point`, `measured` and `against`. It returns the result of AC 5 or raises `tools.ToolFailure` with the kinds of AC 4. Slice 2 (`verdicts.write`, ADR-0140 decision 5) will call this function so that the tool and the write give the same `difference` over the same lines. The executor chooses the name and signature and states them in `## Result`. The function is tested directly as well as through the tool.
3. **Request** (ADR-0140 decision 3, table). Exactly the members `run_id`, `metric`, `point`, `measured` and `against`, all required. Any other member, or a missing one, is `invalid_request`. So is a value outside its form:
   - `run_id` is checked as `layout.check_run_id` checks it.
   - `metric` is exactly the string `"latency_minimisation"`.
   - `point` is exactly `"sim"` or `"board"`, compared as it is. It names the `step` read: `sim_run_timing` (`run_identity.STEP_SIM_RUN`) or `board_run_timing` (`run_identity.STEP_BOARD_RUN`).
   - `measured` and `against` are each a `dict` of exactly `round`, `candidate` and `attempt`. `round` is an `int` from 0 to `keys.MAX_INTEGER`. `candidate` and `attempt` are `int` values from 1 to `keys.MAX_INTEGER`. A `bool` is not an integer. A missing or extra member of either object is refused.
   - `measured` equal to `against` is refused.
   The input schema states what the reading of `tests/test_default_registry_schemas.py` can check (`additionalProperties: false`; `measured` and `against` as `{"type": "object"}`, as `verdicts_tool` declares `record`). The data-root source is not asked when the request is refused.
4. **Checks after the request, in order** (ADR-0140 decision 3, table):
   - The data root, from `data_root_source.obtain(source)`. A failure is `no_data_root`.
   - The read of `runs/<run_id>/events.ndjson` from its first line by `checks_tool.log_lines`, with its kinds (`run_file_missing`, `run_file_unreadable`, `run_file_invalid`, `run_file_unsupported`).
   - Then the step lines, in line order. The first that fails decides:
     - a step line about any attempt that `journal.identity_of` refuses → `run_file_invalid`;
     - an end line of `measured` or `against` at the point's `step` whose `result` is not an admitted timing result → the new kind `timing_result_invalid`. An admitted timing result has `outcome` `"converged"`, `"not_converged"` or `"broken"`. For the first two it also holds `intervals_ns`, an array of at least 5 (`n_min`) integers of at least 1, and `shape`, an object of exactly `m`, `k` and `n`, each an integer of at least 1. Its other members are not looked at. End lines of other attempts, or at the other `step`, are not held to this rule.
   - Then `measured`, and after it `against`, by the measurement rule of ADR-0140 decision 3. M is the end lines of that attempt at the `step`, over every `execution`, whose `result` has `outcome` `"converged"` or `"not_converged"`. U is its end lines that hold a `failure`, together with its identities that have a start line and no end line. The side has a measurement exactly when M holds one line and U is empty. Otherwise the kinds are, in this order:
     - `measurement_several` when M holds more than one line;
     - `measurement_unknown` when U is not empty;
     - `measurement_missing` otherwise.
     Each message names the side (`measured` or `against`). End lines whose `result` has `outcome` `"broken"` neither enter nor refuse.
   - `shapes_differ` when the two results' `shape` differ.
   - `samples_out_of_domain` when the functions of `hilclaw/harness/measurement.py` raise `InvalidSamplesError` for the two sample sets.
   - A missing log, or a missing run directory below an existing data root, holds no line. The answer is then `measurement_missing` for `measured`. The same holds for a `run_id` that names no run.
   - The six new kinds (`timing_result_invalid`, `measurement_several`, `measurement_unknown`, `measurement_missing`, `shapes_differ`, `samples_out_of_domain`) are constants of the new module and are not added to `RESERVED_KINDS`. No other new kind is added.
5. **Result and rule** (ADR-0140 decisions 3 and 4). The result is exactly `{"difference": d, "measured": {"execution": n, "outcome": o}, "against": {"execution": n, "outcome": o}}`. For each side, `execution` and `outcome` are those of the end line whose measurement entered. With x the `intervals_ns` of `against` and y those of `measured`, the interval is `measurement.ratio_interval(x, y)`. `d` is `"lower"` when the whole interval lies strictly below `1 / (1 + DELTA)`, `"higher"` when it lies strictly above `1 + DELTA`, and `"not_different"` otherwise. The strict comparisons are those of `is_different`. The order of the pair is never exchanged. No parameter is added. A `"not_converged"` result enters on either side exactly like a `"converged"` one.
6. **What the tool does not do.**
   - It is not journaled: it appends nothing to `events.ndjson` and selects no backend.
   - It reads no file but the run's `events.ndjson`. It reads no `STATE.json` and no instance record.
   - It creates nothing and keeps nothing between calls.
   - It does not check that the run is one of ADR-0120 decision 1, that the rounds of the two attempts stand in any order, or that either attempt passed a check.
   - It does not compare `sample_form` or `n_max`, and does not read `ceiling`.
   - What a number beyond the float range in a stored result does is the executor's choice (ADR-0140 decision 3, "Left to the code slice"). `checks.read` answers `bad_result`. The choice is stated in the module docstring and tested.
   - The description tells the model what the tool reads and computes, that the data root is never part of the request, the request's members and forms, the result's shape and the three `difference` values, that `measured` is compared against `against`, and every failure kind with its meaning. It follows the manner of `checks_tool._DESCRIPTION`.
7. **`hilclaw/run_identity.py`**: the module docstring's sentence that "says nothing of who may raise `execution` or which of several executions counts (OD-10, OD-17, OD-18 sub-question ⑳)" is made accurate. For the comparisons of a verdict in the runs of ADR-0120 decision 1, ADR-0140 decision 3 now says which result enters: exactly one, and the comparison is refused otherwise. The rest of ⑳ stays open. Behaviour is unchanged.
8. **`hilclaw/tools.py`**: `default_registry` registers `timings.compare` from the new module, in the source only. Its docstring names the tool and ADR-0140 decision 3, and says the evaluator gets with it the `difference` of a comparison of two attempts at one point. Building the registry still imports no NumPy (the existing checks in `tests/test_check_definition.py`).
9. **Tests** in a new file `tests/test_timings_tool.py`. They use a temporary data root built by the test, with fixture log lines written by `events.append` or as bytes. The timing results are built with `run_result.completed` / `run_result.broken`, or as plain dicts where a result must be invalid. No `claude` is started, stub or real. The tests pass on Linux CI and on the local Windows machine. They cover at least:
   - **happy**: one converged end line on each side, with samples chosen so that the interval lies wholly below `1 / 1.02`, gives `"lower"`. The reverse gives `"higher"`. Close samples give `"not_different"`. The result's members are exactly as in AC 5. The result agrees with `measurement.ratio_interval` on the same sets in the order (`against`, `measured`).
   - **branch**, the Walk-through rows of ADR-0140: a `"not_converged"` side on either side enters; a broken end line (`execution` 1) beside a converged one (`execution` 2) gives the converged one with `execution` 2; two converged end lines (two executions, and two end lines of one identity) give `measurement_several`; a converged end line beside an open identity, and beside a `failure` end line, give `measurement_unknown`; only a `failure` end line gives `measurement_unknown`; no line, or only a broken end line, gives `measurement_missing`; the order `measured` before `against` among these kinds (a missing `measured` with a several `against` names `measured`); round 0 attempts; lines of the other point, other attempts and other candidates are ignored; a missing log; a torn tail; `shapes_differ`; `samples_out_of_domain` (through samples beyond the float range or through a seam); the number-range choice of AC 6.
   - **negative and error**: each `invalid_request` form (an extra member; each member missing; a bad `run_id`; another `metric`; a `point` of another string or case; `measured` or `against` not a `dict`, with an extra or missing member, or with a negative, too large, `bool`, float or string number, `candidate` or `attempt` 0; `measured` equal to `against`); `no_data_root`; the four `run_file_*` kinds as `tests/test_checks_tool.py` produces them (seams, not permission changes that Windows ignores); `run_file_invalid` for a step line about another attempt that breaks ADR-0011; `timing_result_invalid` for each rule of an admitted timing result (bad `outcome`, missing or short `intervals_ns`, a sample of 0, a non-integer sample, a missing `shape`, a `shape` with an extra member or a member below 1) on either named side; an invalid result of an unnamed attempt is no failure; when a broken step line comes before an in-scope invalid result, the first in line order decides. After every call no file or directory has been created under the data root and the log is byte-identical.
   - **the public function of AC 2**: called directly with lines, it gives the same results and kinds as the tool.
   - **registry**: `timings.compare` is listed by `default_registry` and through the MCP front as `timings_compare`. The listing tests in the test files of `touchesFiles` are updated. `tests/test_default_registry_schemas.py` gets an `ACCEPTED` entry that satisfies ADR-0077.
10. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases; ③ every public function of the new module and of each touched module that changes behaviour is tested; ④ the new module has its own test file; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
11. **No data-plane change**: no member, file, kind of event, value or version of `events.ndjson`, `verdicts.json`, `hypotheses.json`, `STATE.json`, `instance.json` or `artifacts.json` is added or changed, and no validator changes. The six new kinds are tool-layer names (ADR-0140 Consequences, "A-13 reading"). If the work turns out to need a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
12. **Size**: the non-test change stays within the D4 cap (≤ 300 LOC, ≤ 5 files). If it would not, the executor keeps the tool and its registration in this task and proposes a split in `## Follow-ups`.
13. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
14. **Code mode (A-13)**: a Draft PR whose title contains `T-0381`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0381`, and the branch `claude/T-0381-timings-compare-tool` deleted.
15. No `claude` process is started, and nothing runtime-only is required (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/`: no ADR, register row, proposal section or scenario note. The "less exact, not edited" sentences listed in ADR-0140 Consequences are not edited, except the `hilclaw/run_identity.py` and `hilclaw/tools.py` docstrings named in slice 1.
- Slice 2: any change of `hilclaw/verdicts_tool.py` (`comparison_not_given`, `timing_result_invalid` in its step pass, `comparison_unfounded`, `comparison_unverified`) and its tests.
- Slice 3: `orchestration/agents/evaluator.md`, its `tools` list, and the tools tests in `tests/test_turn_definition.py` and `tests/test_turn_permissions.py`. The Round-Manager is not given the tool.
- `sim.run` and `board.run` and their registration (HQ-0021, T-0210), the base of the comparison (which attempt `against` is), `eval.json`, and the rest of OD-18 ⑳.
- Any change of `hilclaw/checks_tool.py` behaviour, of `hilclaw/harness/measurement.py`, of the MCP front, of `hilclaw/events.py` or `hilclaw/journal.py`, or of the files of open PR #186.

## Follow-ups

- Next for the planner: ADR-0140 Consequences slice 2 (decision 5 in `hilclaw/verdicts_tool.py`, reusing the public function of AC 2), then slice 3 (`orchestration/agents/evaluator.md` per decision 6 and its `tools` test).

## Result

- **DONE**: landed by squash-merge of PR #219 after CI green ( whose body ends with `Task: T-0381`; branch `claude/T-0381-timings-compare-tool` deleted). Review rounds: 3 (round 1 Approve with one minor — the D4 size note — and two nits: line wrapping and a comma, and a test of `1e999` in a stored `shape`; round 2 Approve with one nit, two lines still wide; round 3 Approve, no findings).
- **Module**: `hilclaw/timings_tool.py` (name as planned; `touchesFiles` unchanged). `definition(source)` returns the `ToolDefinition` of `timings.compare`; the six kinds are module constants `KIND_TIMING_RESULT_INVALID`, `KIND_MEASUREMENT_SEVERAL`, `KIND_MEASUREMENT_UNKNOWN`, `KIND_MEASUREMENT_MISSING`, `KIND_SHAPES_DIFFER`, `KIND_SAMPLES_OUT_OF_DOMAIN`, none in `RESERVED_KINDS`.
- **Shared function for slice 2 (AC 2)**: `timings_tool.compare(run_id, lines, metric, point, measured, against)`. `lines` as `checks_tool.log_lines` returns them; `measured`/`against` mappings of `round`, `candidate`, `attempt` in the request's forms and different; it raises `ValueError` only for a `metric` other than `METRIC` or a `point` outside `STEP_OF`, and otherwise returns the AC 5 result or raises `ToolFailure` with the AC 4 kinds after the read. `verdicts.write` can call it per `comparison` entry.
- **Number-range choice (AC 6)**: a number beyond the float range in a stored result is read as a float infinity: in `intervals_ns` or `shape` it is no `int`, so `timing_result_invalid`; in any other member it changes nothing (the result returns no stored member, so no `bad_result`). An `int` too large for the float range in `intervals_ns` is admitted and then `samples_out_of_domain`.
- **Other choices**: the three `outcome` values are spelled in the module, not imported from `hilclaw.run_result`, because `tests/test_run_result.py` holds that no other module of the package imports it.
- **Size (D4)**: the non-test change is about 415 lines (`hilclaw/timings_tool.py` about 400, `hilclaw/tools.py` +6/-1, `hilclaw/run_identity.py` +7/-4), over the 300-line cap and the 290 estimate; about 150 statements are code, the rest the module docstring, function docstrings and model-facing description required by AC 1 and AC 6. No split is proposed: AC 12 keeps the tool and its registration together and the tool has no smaller part that works alone.
- **Language**: Python — the registry, the MCP front and the measurement functions the tool calls are Python modules of the same package.
- **Local tests**: `ruff check`, `ruff format --check`, full `pytest` (25416 passed, 730 skipped); coverage of `hilclaw/` 96.8 % lines, 96.8 % functions; `hilclaw/timings_tool.py` 100 % lines.
- **Runtime acceptance items / HQ**: none.
- **Follow-ups**: as listed above (slice 2, then slice 3).
