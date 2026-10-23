---
id: T-0358
title: Add the registry tool checks.read of ADR-0131 decision 3, with the standing of ADR-0110 folded in, and register it in the default registry (ADR-0131 Consequences slice 1; PLAN P2-3, P2-6)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-9, FR-11, FR-17, NFR-1, OD-23, OD-18, OD-16, S0, S1]
dependsOn: [T-0356, T-0357]
touchesFiles:
  - hilclaw/checks_tool.py
  - hilclaw/check_standing.py
  - hilclaw/tools.py
  - tests/test_checks_tool.py
  - tests/test_check_standing.py
  - tests/test___main__.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_tools.py
estimatedSize: {loc: 260, files: 3}
hq: []
---
## Why

ADR-0131 (task T-0357, landed on `main` up to 9e29340) decides that the evaluator of a first-case turn gets the results of an attempt's `correctness.check` calls, and the standing of ADR-0110, through a new typed registry tool `checks.read` (MCP name `mcp__hilclaw__checks_read`). The tool reads the run's `events.ndjson` from its first line. ADR-0131 Consequences lists three code slices. Slice 1 is marked "Now": the tool in a module of `hilclaw/` with its test file, registered in `default_registry`, and the `hilclaw/check_standing.py` docstring brought up to date (it says the module "names no consumer"). This task is slice 1. Slice 2 is the log check of `verdicts.write` (`check_unfounded`). Slice 3 is the `orchestration/agents/evaluator.md` change of ADR-0131 decision 6. Both are later tasks.

Priority (DRIVER §6, D18): this is work on the checklist items PLAN P2-3 (evaluator) and P2-6 (verdicts). Rounds 1 to 4 of the first run (P2-5, the near goal) reach evaluate, and FR-17 does not let them end without verdicts. ADR-0131 decision 6 gives the verdicts work only once `checks.read` exists. This task is not input hardening and not a wording cleanup.

Open HQs checked (HQ-0013 to HQ-0047): none is crossed. The tool is a registry read (HQ-0040, no shell). It names no model or budget (HQ-0041). It does not touch `sim.run` or `board.run` (HQ-0021). It writes nothing (HQ-0043). Its files do not overlap open PR #186 (HQ-0032: `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`). Runtime acceptance item (xxii) of ADR-0131 is not closed by this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the language policy, the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`, the whole file. This is the specification. Read **decision 3 with its table and every bullet under it**, decision 7, the Walk-through rows about `checks.read`, and Consequences slice 1 closely.
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: decisions 2, 3 and 5. They define what counts and the three standings.
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md`: decisions 1 to 4 (the reserved `run_file_*` kinds and "not there").
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 2 to 4 (definition, `invalid_request`, the data-root source, the forms of `run_id`, `round`, `candidate` and `attempt`).
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md`: decisions 3 and 4 (`point` and its `step`).
- `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md`: decisions 2 to 4 (what the `ACCEPTED` entry of the new tool must satisfy).
- `hilclaw/check_standing.py`, the whole file. `standing` is the computation the tool reuses or repeats.
- `hilclaw/hypotheses_tool.py`, the whole file. This is the closest pattern: definition, input schema, description, request check, data-root source, no journaling.
- `hilclaw/events.py`: the module docstring and `read`. `hilclaw/journal.py`: the module docstring, `JournalError`, `Identity`, `identity_of`, `step_identity`.
- `hilclaw/run_files.py`, the whole file. `hilclaw/journaled_step.py`: `_LOG_KINDS`, `_state` and `_lines`. This is the existing mapping of a log read to the `run_file_*` kinds, including the case of a data root gone since the source was asked.
- `hilclaw/check_identity.py`: the module docstring, `MEMBER`, `SIM`, `BOARD`, `STEPS`, `NUMBERS`, `_STEP_OF`. `hilclaw/check_result.py`: `PASS`, `FAIL`, `BROKEN`. `hilclaw/check_tool.py`: the module docstring (the start and end lines it journals).
- `hilclaw/tools.py`: the module docstring, `ToolDefinition`, `ToolFailure`, the kind constants, `RESERVED_KINDS`, and `default_registry` with its docstring. `hilclaw/mcp_front.py`: `mcp_name`.
- Tests as the pattern for the new tests and for the listing tests that must be updated: `tests/test_hypotheses_tool.py`, `tests/test_check_standing.py`, `tests/test_default_registry_schemas.py`, and the `hypotheses.read` / `hypotheses_read` entries in `tests/test___main__.py`, `tests/test_blob_tools.py`, `tests/test_check_definition.py`, `tests/test_mcp_front.py` and `tests/test_tools.py`.

## Acceptance Criteria

1. **New module** `hilclaw/checks_tool.py`. The executor may choose a clearer name and then updates `touchesFiles` in `## Result`. Its module docstring names ADR-0131 decision 3 and states the request, the result, the checks in order with their kinds, and the choices left to the slice. It exposes `definition(source)`, which returns one `tools.ToolDefinition` for `checks.read` bound to the data-root source `source`. The source is not called at definition time. A non-callable `source` raises `TypeError`, as `hypotheses_tool.definition` does.
2. **Request** (ADR-0131 decision 3, table). The members `run_id`, `round`, `candidate` and `point` are required. `attempt` is optional. Any other member, or a missing required member, is `invalid_request`. So is a value outside its form:
   - `run_id` is checked as `layout.check_run_id` checks it.
   - `round` is an integer from 0 to `keys.MAX_INTEGER`. Round 0 is admitted.
   - `candidate` and `attempt` have the forms of ADR-0015 decision 4.
   - `point` is exactly `"sim"` or `"board"`, compared as it is.
   - A `bool` is not an integer.
   The input schema states the same (`additionalProperties: false`), in the form of `hypotheses_tool._input_schema`. The data-root source is not asked when the request is refused.
3. **Checks after the request, in order** (ADR-0131 decision 3, table):
   - The data root, from `data_root_source.obtain(source)`. A failure is `no_data_root`.
   - The read of `runs/<run_id>/events.ndjson` from its first line. Every complete line is parsed before any step line is looked at. The kinds are those of ADR-0019 for the log, with messages in the form of `run_files`:
     - a data root that is no longer an existing directory → `run_file_missing`;
     - another failing read of the file system → `run_file_unreadable`;
     - a path that is no regular file, or a damaged complete line → `run_file_invalid`;
     - a complete line of another version → `run_file_unsupported`.
     The situations of the file come first. Among complete lines, the first in line order decides.
   - Then the step lines, in line order. The first that fails decides:
     - a step line that breaks ADR-0011 (as `journal.identity_of` checks it), about any attempt → `run_file_invalid`;
     - an end line in the request's scope whose `result` has no `outcome` of `"pass"`, `"fail"` or `"broken"` → the new kind `check_result_invalid`. The scope is the named attempt at the point's `step` when `attempt` is given, and every attempt of the candidate at that `step` when it is not.
   - A missing log, or a missing run directory below an existing data root, is no failure. It holds no line (ADR-0131 decision 3, "A missing log is no failure").
   - A torn tail is not a line and causes no failure.
4. **Result** `{"attempts": [...]}`, one entry per attempt in ascending `attempt`. Each entry has exactly `attempt`, `standing` and `checks`.
   - With `attempt` in the request there is exactly one entry, for that attempt, even when the log holds no line for it.
   - Without `attempt` there is one entry for each attempt of the candidate for which the log holds a line of the point's `step`. There may be none.
   - `checks` holds one element per end line of that attempt at the step: `{"execution": n, "state": "ended", "result": ...}` or `{"execution": n, "state": "ended", "failure": ...}`, with the `result` or `failure` as the line holds it. It also holds one element `{"execution": n, "state": "open"}` per identity that has a start line and no end line. Elements stand in the order of their lines; an open identity stands at its first start line. Two end lines of one identity give two elements, and an end line without a start line gives one.
   - `standing` is the ADR-0110 decision 3 standing of that attempt at that step over the same lines, as one of the strings `"verified"`, `"not_verified"` and `"undetermined"`. It is computed by `check_standing.standing` or by code that gives the same answer on every input. The tests show agreement with `check_standing.standing` on the walk-through rows.
   - With `attempt` given and no line, the entry has `checks` `[]` and `standing` `"undetermined"`.
5. **Telling `run_file_invalid` from `check_result_invalid`** (the T-0357 reviewer's note). `check_standing.standing` raises `journal.JournalError` both for a step line that breaks ADR-0011 and for a result without an admitted `outcome`. The executor makes the two distinguishable without string matching on messages. For example, `check_standing` may raise a new subclass of `journal.JournalError` for the outcome case, or the new module may make its own scoped pass. Existing callers of `check_standing.standing` and `tests/test_check_standing.py` keep passing. If the executor adds a public name to `check_standing`, it is tested there. The executor states the choice in `## Result`.
6. **What the tool does not do.**
   - It is not journaled: it appends nothing to `events.ndjson` and selects no backend.
   - It reads no `STATE.json` and no file but the run's `events.ndjson`. A `run_id` naming no run is answered like an empty log.
   - It creates nothing and keeps nothing between calls.
   - It does not check that the run is one of ADR-0120 decision 1.
   - `check_result_invalid` is a tool-layer kind, defined as a constant of the new module and not added to `RESERVED_KINDS`. No other new kind is added.
   - What a number beyond the float range in a stored `result` does is the executor's choice (ADR-0131 decision 3, "Left to the code slice"). `state.read` and `hypotheses.read` answer `bad_result`. The choice is stated in the module docstring and tested.
   - The description tells the model what the tool reads, that the data root is never part of the request, that `attempt` is optional and what leaving it out does, the result's shape and the three standing strings, and every failure kind. It follows the manner of `hypotheses_tool._DESCRIPTION`.
7. **`hilclaw/check_standing.py`**: the module docstring no longer says the module "names no consumer". It names `checks.read` (ADR-0131 decision 3) as the consumer. Its behaviour is unchanged, except for AC 5 if the executor takes that route.
8. **`hilclaw/tools.py`**: `default_registry` registers `checks.read` from the new module, in the source only. Its docstring names the tool and ADR-0131. Building the registry still imports no NumPy (the existing check in `tests/test_check_definition.py`).
9. **Tests** in a new file `tests/test_checks_tool.py`. They use a temporary data root built by the test, with log lines written by `events.append` or as bytes. No `claude` is started, stub or real. The tests pass on Linux CI and on the local Windows machine. They cover at least:
   - **happy**: one pass gives `"verified"` (Walk-through row 1). An entry's members are exactly `attempt`, `standing` and `checks`. A `result` is returned as stored, including members outside ADR-0042 decision 7's table.
   - **branch**, the walk-through rows of `checks.read`: fail then pass gives `"not_verified"`; pass plus open gives `"undetermined"`; two end lines of one `execution` give two elements; a class (i) `failure` alone gives `"undetermined"`; without `attempt`, two attempts come back in ascending order and an attempt with lines only at the other point is left out; round 0; the other point's lines and other candidates' lines are ignored; a missing log with and without `attempt`; a torn tail; the data-root source is not asked when the request is refused; agreement of `standing` with `check_standing.standing`; the number-range choice of AC 6.
   - **negative and error**: each `invalid_request` form (an extra member; each required member missing; a bad `run_id`; a negative or too large or `bool` or float or string `round`, `candidate` or `attempt`; a `point` of another string or case); `no_data_root`; `run_file_missing` for a data root removed between the source and the read (through a seam); `run_file_unreadable` through a seam, not by changing permissions that Windows ignores; `run_file_invalid` for a directory at the log's place, for a damaged line anywhere in the log, and for a step line about another attempt that breaks ADR-0011; `run_file_unsupported`; `check_result_invalid` in scope (with and without `attempt`). A result without `outcome` out of scope is no failure. When a broken step line comes before an out-of-scope bad result, the first in line order decides. After every call no file or directory has been created under the data root and the log is byte-identical.
   - **registry**: `checks.read` is listed by `default_registry` and through the MCP front as `checks_read`. The listing tests in the test files of `touchesFiles` are updated. `tests/test_default_registry_schemas.py` gets an `ACCEPTED` entry that satisfies ADR-0077.
10. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases; ③ every public function of the new module and of each touched module that changes behaviour is tested; ④ the new module has its own test file; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
11. **No data-plane change**: no member, file, kind of event, value or version of `events.ndjson`, `verdicts.json`, `hypotheses.json`, `STATE.json`, `instance.json` or `artifacts.json` is added or changed, and no validator changes. The standing strings and `check_result_invalid` are tool-layer values (ADR-0131 decision 3, Consequences "A-13 reading"). If the work turns out to need a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
12. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
13. **Code mode (A-13)**: a Draft PR whose title contains `T-0358`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0358`, and the branch `claude/T-0358-checks-read-tool` deleted.
14. No `claude` process is started, and nothing runtime-only is required (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/`: no ADR, register row, proposal section or scenario note. The "less exact, not edited" sentences listed in ADR-0131 Consequences are not edited.
- Slice 2: the log check of `verdicts.write` (`check_unfounded`, the log-read kinds in `hilclaw/verdicts_tool.py`). Sharing code with it later is allowed; changing `verdicts.write` now is not.
- Slice 3: `orchestration/agents/evaluator.md`, its `tools` list and `tests/test_turn_definition.py`'s `EVALUATOR_TOOLS`. The Round-Manager's use of the tool (`orchestration/round-manager.md`).
- The comparison tool, `sim.run` and `board.run` (HQ-0021), `eval.json`, and a bound on the result or a paged read (item (xxii)).
- Any change of the MCP front, of `hilclaw/events.py` or `hilclaw/journal.py` behaviour, or of the files of open PR #186.

## Follow-ups

- Next for the planner: ADR-0131 Consequences slice 2 (the log check of `verdicts.write` with `check_unfounded` and the log-read kinds, decision 5), then slice 3 (`orchestration/agents/evaluator.md` per decision 6 and its `tools` test).

## Result
- **Outcome**: the tool `checks.read` of ADR-0131 decision 3 in `hilclaw/checks_tool.py` (the module name of AC 1, so `touchesFiles` is unchanged), registered in `default_registry`; PR #205 (code mode, squash-merged by the executor after the reviewer's Approve and CI green).
- **Files**: `hilclaw/checks_tool.py` (new), `hilclaw/check_standing.py` (docstring only), `hilclaw/tools.py`; tests `tests/test_checks_tool.py` (new) and the listing updates in `tests/test___main__.py`, `tests/test_blob_tools.py`, `tests/test_check_definition.py`, `tests/test_default_registry_schemas.py` (the ADR-0077 `ACCEPTED` entry, without `attempt`, so the schema test also derives the requests that add a bad `attempt`), `tests/test_mcp_front.py` and `tests/test_tools.py`. `tests/test_check_standing.py` did not need a change.
- **AC 5 choice**: the new module makes its own scoped pass over the step lines. A step line that `journal.identity_of` refuses gives `run_file_invalid`, an in-scope end line without an admitted `outcome` gives `check_result_invalid`, each told apart by the check that refuses, not by its message, and the first failing line in line order decides across attempts (a call to `check_standing.standing` per attempt could not keep that order without attempt). `check_standing.standing` is then asked for each attempt's standing over lines it no longer refuses. `check_standing` gains no public name and its behaviour is unchanged.
- **AC 6 number-range choice**: a number beyond the float range in a returned `result` or `failure` is read by `events.read` as an infinity; the call ends in `bad_result` at `tools.call`, as for `state.read` and `hypotheses.read`; such a number on a line outside the result does nothing. Stated in the module docstring and tested.
- **Other choices of the slice**: a step line of the candidate without `attempt` is no attempt's line and is ignored, as `check_standing.standing` ignores it; a log that vanishes between its look and its read below an existing data root holds no line; the messages of the step-line kinds start with `runs/<run_id>/events.ndjson: line N:`.
- **Language**: Python. The registry and every module the tool reuses (`events`, `journal`, `run_files`, `check_standing`) are Python.
- **Tests**: full local suite green on Windows (Python 3.14), ruff check and format clean; line coverage of `hilclaw/` 97 %, `checks_tool.py` 98 % (the uncovered `ValueError` guard of a value too long to show runs on Python 3.11 only).
- **Review**: 2 rounds with the dev-reviewer agent in a fresh context; round 1 Approve with two Low nits (an explicit point-to-step map, the outcome message in the form of `check_standing`), both fixed; round 2 Approve with no finding.
- **Follow-ups**: none new. ADR-0131 slices 2 and 3 stay as listed under Follow-ups.
