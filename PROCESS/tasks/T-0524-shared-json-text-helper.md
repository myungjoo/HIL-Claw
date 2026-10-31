---
id: T-0524
title: Move the repeated JSON text helpers of the file modules into hilclaw/json_text.py with no change of behaviour (replan of T-0225)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [HQ-0080, FR-13, "ADR-0029", "ADR-0059", "ADR-0071", "ADR-0072"]
dependsOn: [T-0523]
touchesFiles:
  - hilclaw/json_text.py
  - hilclaw/spec_file.py
  - hilclaw/hypotheses_file.py
  - hilclaw/verdicts_file.py
  - hilclaw/cases_file.py
  - hilclaw/artifacts.py
  - hilclaw/events.py
  - hilclaw/instance.py
  - hilclaw/key_records.py
  - hilclaw/run_state.py
  - tests/test_json_text.py
estimatedSize: {loc: 220, files: 10}
hq: []
---
## Why

HQ-0080 closed T-0225 without a result and asked for a replan on current main. This is that replan; the line is not judged again here, and P2-15 does not need the work.

The same private helpers still exist in copies:

- `_object(pairs)`, raising `ValueError("a JSON object repeats a member name")`: `artifacts`, `cases_file`, `events`, `hypotheses_file`, `instance`, `key_records`, `run_state`, `spec_file`, `verdicts_file`.
- `_nan(name)`, raising `ValueError(f"{name} is not a JSON value")`: the same modules but `artifacts` and `key_records`.
- `_MINUS_ZERO`, `_literal` and the `-0` walk `_unsigned`: `spec_file`, `hypotheses_file`, `verdicts_file`, `cases_file`.

What differs stays in the callers: the error class raised for a `-0`, `spec_file`'s `_FREE` skip and its path join for an empty path, and which members each module walks.

T-0225 stopped at the four `*_file` modules because of the file cap at that time. The other five fit the current cap, so they are included.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5.
- `PROCESS/tasks/T-0225-*.md`, `## Why` and `## Acceptance Criteria`, for the earlier analysis only. Its line numbers and its ban on editing tests are out of date; this file wins.
- `hilclaw/once_write.py`, as the example of a shared helper module.
- In each caller: the helpers above and the `parse` or read function that uses them.
- `ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md` decision 2, read only.

## Acceptance Criteria

1. **New module `hilclaw/json_text.py`.** Public names, chosen by the executor under review. It imports nothing from `hilclaw`, and holds only what the callers repeat. Its docstring says which text rules it carries and what stays in the callers, and adds no rule. Each public function has a docstring.
2. **Callers.** The nine modules drop their copies and use the module. A thin private wrapper that only binds a module's own error class or `_FREE` is allowed. The `_object` of `hypotheses.py`, `spec.py`, `verdicts.py` and `selfcheck_wire.py` are different functions and stay.
3. **No change of behaviour.** For every caller, messages, the first path reported, the exception class and its chaining, and the order of checks stay as they are. Public names and signatures of the callers do not change. A module docstring sentence that becomes untrue, including an import sentence, is corrected in the fewest words.
4. **Modules left alone.** The hook entry modules `budget_check`, `caller_check` and `stop_check`, and `new_run`, `tools`, `mcp_front`, `selfcheck_login` and `selfcheck_stream`, keep their own helpers.
5. **New tests, `tests/test_json_text.py`.**
   - Happy: distinct names give a `dict` in order; literals other than `-0` are not marked; a spelling with no `-0` gives no finding.
   - Error: a repeated name and each of `NaN`, `Infinity`, `-Infinity` give the exact message; a `-0` gives the exact path.
   - Branch: `-0` at the top level, in an object, in an array and in an array of objects; the first in pre-order wins; a skipped path hides what is below it but not what is beside it.
   - Negative: `0`, `-0.0`, the string `"-0"`, `False` and a member named `"-0"` are not reported.
6. **Existing tests** pass unchanged, except list pins (D21). Foreseen: the import assertions `tests/test_spec_file.py::test_the_module_imports_only_what_it_needs` and the import assertion near `tests/test_instance.py` line 2643, and any like them in the test files of the other seven callers. List them in the PR body. If another test fails, the move changed behaviour: fix the move, not the test.
7. **Gates.** `ruff check`, `ruff format --check`, the test suite, the coverage gate and the test-presence check pass.
8. `## Result` records the language line (Python, the language of the callers), the public names chosen and the net line change.

## Out of Scope

- Any change of a text rule, a message, a version rule, a validator, a layout path or a record; any edit under `ARCHITECTURE/`.
- Sharing `parse`, `write`, the exception classes, or the decode, byte order mark and version steps.
- A real `claude`, a Docker daemon or a D25 test run.

## Follow-ups

## Result
