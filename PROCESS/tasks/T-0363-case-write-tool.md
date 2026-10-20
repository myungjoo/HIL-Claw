---
id: T-0363
title: Add the registry tool case.write of ADR-0133 decision 3, which builds a round's case from its two files and stores it in the run's stored key directory (ADR-0133 slice 1; PLAN P2-7)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-18, FR-11, FR-10, OD-23, OD-30, S0, S1]
dependsOn: [T-0362]
touchesFiles:
  - hilclaw/case_tool.py
  - hilclaw/tools.py
  - hilclaw/cases.py
  - hilclaw/cases_file.py
  - hilclaw/run_file_tools.py
  - tests/test_case_tool.py
  - tests/test_tools.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
estimatedSize: {loc: 260, files: 5}
hq: []
---
## Why

PLAN P2-7 (store a round's hypothesis-outcome case at the round's end, rejected and failed included; exact-key lookup) is a checklist item. It comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. ADR-0133 (landed on main as 67b6d6a, T-0362) decided the case write of a first-case round. The Round-Manager holds it inline and calls one new registry tool, `case.write`. Its Consequences name this tool as slice 1, "Now": the module with its test file, registration in `default_registry`, and the docstrings of `hilclaw/cases.py` and `hilclaw/cases_file.py`. Without the tool, nothing calls `cases.build` or `cases_file.write`, and the first run (P2-5) cannot store a case (FR-18).

This task does not depend on T-0361 / ADR-0132, which is BLOCKED on HQ-0048 and has not landed. The tool reads the round's `decision/hypotheses.json` as a file, whoever wrote it. Do not take anything from the branch `claude/T-0361-*`. That branch also registers a tool in `hilclaw/tools.py`, so whichever of the two lands later needs a rebase there. It is not an open PR.

Until an OD-26 record exists, nothing in a real run creates the key directory and its two record files (ADR-0133 Consequences), so in a real run every call answers `key_not_stored`. That is the decided behaviour. Tests create the key directory with `hilclaw.key_records.store_hw_profile` and `store_op_signature`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (code mode)
  - §3-5 (executor procedure, resume rule, the 2 h 30 min time limit)
  - §5 (naming: branch `claude/T-0363-<slug>`, PR title containing `T-0363`, trailer `Task: T-0363`, and `Task: T-0363` as the last line of the PR body used as the squash message; the size cap, which excludes tests; the language line in the Result; test rules ① to ⑤)
- `CLAUDE.md`: all rules. In particular the test rules (D12), the language policy (Python here; one line in the commit body saying why), the A-13 code-mode procedure (Draft PR, reviewer cycle, CI green, squash-merge, delete the branch), the BLOCKED reasons (a data-plane schema change is one), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- **The record to implement**: `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md`. Read decisions 1 to 5 (lines 28-67), the Walk-through (lines 73-84) and Consequences (lines 104-116). Decision 3's table, at line 46, is the contract: request, result, the nine checks in order, and their kinds.
- Context for that contract:
  - `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decisions 2 to 4 (lines 39-82).
  - `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decisions 2 and 3 (lines 30-75).
  - `ARCHITECTURE/decisions/ADR-0072-od30-hypothesis-outcome-case-file.md` decisions 1 to 3 (lines 23-62).
  - `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decision 3 (lines 43-63).
  - `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md` decision 6 (lines 61-75).
- Code, in this order:
  - `hilclaw/verdicts_tool.py` (whole; the closest model for module shape, description, input schema, `_checked`, encoding of the written bytes, `_reported`).
  - `hilclaw/hypotheses_tool.py` (whole; `read` and the `run_id`/`round` comparison in `_read`).
  - `hilclaw/run_file_tools.py` (whole; `_read` with `_STATE_FILE` / `_INSTANCE_FILE` and `run_files.reading`).
  - `hilclaw/run_files.py`.
  - `hilclaw/key_records.py` (module docstring, `lookup`, the three error classes, `store_hw_profile`, `store_op_signature`).
  - `hilclaw/case_lookup.py` `lookup` (lines 157-170), as a model for taking the key out of an `instance.json`.
  - `hilclaw/instance.py` `Instance` (lines 640-680) and `parse`.
  - `hilclaw/run_state.py` `parse`.
  - `hilclaw/verdicts_file.py` `parse` and its errors.
  - `hilclaw/verdicts_hypotheses.py` `check`.
  - `hilclaw/cases.py` (module docstring, `build`).
  - `hilclaw/cases_file.py` (module docstring, `write` and what it raises).
  - `hilclaw/layout.py` (`run_file`, `hypothesis_record`, `verdict_record`, `op_signature_dir`, `case_record`).
  - `hilclaw/tools.py` (`ToolFailure`, `KIND_*`, the kind pattern, `default_registry`).
  - `hilclaw/data_root_source.py`.
- Tests to model on and to extend: `tests/test_verdicts_tool.py`, `tests/test_hypotheses_tool.py`, `tests/test_tools.py` (`DEFAULT_SET`), `tests/test_default_registry_schemas.py` (`ACCEPTED`), `tests/test_mcp_front.py` (the tool-name lists).
- Before you start, run `gh pr list`. Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and its test, and does not overlap. If another open PR touches a file of `touchesFiles`, stop and return BLOCKED (DRIVER §3-3).

## Acceptance Criteria

1. **New module `hilclaw/case_tool.py`.** It exposes `definition(source)`, which returns a `tools.ToolDefinition` for the name `case.write` (MCP `case_write`), as `verdicts_tool.definition` does.
   - `source` is asked once per call, after the request is checked.
   - `definition` raises `TypeError` for a `source` that is not callable.
   - The module docstring states the contract below and cites ADR-0133. The `KIND_*` constants each carry a `#:` line.
   - Description and input schema:
     - The description tells the model the request, the result, and every failure kind in order.
     - The input schema has `run_id` with the same pattern as the other tools, `round` as an integer from 1 to `keys.MAX_INTEGER`, both required, and `additionalProperties: false`.
2. **Request and result** (ADR-0133 decision 3):
   - The request is exactly `run_id` and `round`. Any other member, a missing member, a `run_id` that `layout.check_run_id` refuses, or a `round` that is not an `int` from 1 to `keys.MAX_INTEGER` (a `bool` is none, and 0 is refused) gives `invalid_request`.
   - The result is `{"with_verdicts": bool}`: true exactly when the stored case holds `verdict_record`.
3. **The checks, in exactly this order.** The first failing check decides, and every check before ⑨ creates nothing:
   1. The request (`invalid_request`).
   2. The data root, through `data_root_source.obtain` (`no_data_root`).
   3. `STATE.json`:
      - It is read once and parsed by `run_state.parse`. Use the four `run_file_*` kinds exactly as `state.read` answers them: missing, a place holding no regular file, an invalid file, another version, an unreadable file.
      - Its `round` must equal the request's `round`; otherwise `round_not_current`.
   4. `instance.json`: read once and parsed by `instance.parse`, with the same four kinds as `instance.read`.
   5. The key:
      - An instance with no `op_signature` gives `key_not_stored`.
      - Otherwise call `key_records.lookup(data_root, instance.hw_profile, instance.op_signature.record)`. `None` gives `key_not_stored`. `KeyCollisionError` or `CorruptKeyRecordError` gives `key_record_invalid`. Any `OSError` gives `key_record_unreadable`, including a data root removed since ②.
   6. The round's `decision/hypotheses.json`:
      - Read it with `hypotheses_tool.read`, which gives the four `hypotheses_*` kinds.
      - Then compare its `run_id` and then its `round` with the request's. A difference gives `hypotheses_invalid`, worded as `hypotheses.read` words it.
   7. The round's `eval/verdicts.json` (`layout.verdict_record`):
      - Not there (`run_files.NOT_THERE` on `os.lstat`) is **no failure**, and there are then no verdicts.
      - A place holding no regular file gives `verdicts_invalid`.
      - A failing read gives `verdicts_unreadable`.
      - If `verdicts_file.parse` raises `InvalidVerdictFileError`, the answer is `verdicts_invalid`. If it raises `UnsupportedVersionError`, the answer is `verdicts_unsupported`.
      - A `run_id` or `round` other than the request's gives `verdicts_invalid`.
   8. With verdicts present, `verdicts_hypotheses.check(verdicts, hypotheses)` raises `MismatchError`, which gives `verdicts_mismatch`. Then `cases.build(hypotheses, verdicts or None)`.
   9. The bytes of the case:
      - Encode them by the fixed rule `verdicts_tool` uses: `json.dumps(case, ensure_ascii=False, indent=2, allow_nan=False) + "\n"`, in UTF-8. State the rule in the docstring.
      - Write them with `cases_file.write(data_root, hw.name, op.name, content)`, using the two `keys.Key` values of ⑤.
      - `NameTakenError` gives `case_exists`, with nothing replaced.
      - Any `OSError` gives `case_not_written`, including a key directory removed since ⑤. Its message uses the class and the system text, without the absolute path, and says when the data root is gone, as `verdicts_tool._reported` does.

   Every failure message starts with the path of the file concerned, relative to the data root, where there is one.
4. **Kinds.**
   - New constants: `KIND_ROUND_NOT_CURRENT = "round_not_current"`, `KIND_KEY_NOT_STORED`, `KIND_KEY_RECORD_INVALID`, `KIND_KEY_RECORD_UNREADABLE`, `KIND_VERDICTS_INVALID`, `KIND_VERDICTS_UNSUPPORTED`, `KIND_VERDICTS_UNREADABLE`, `KIND_CASE_EXISTS` and `KIND_CASE_NOT_WRITTEN`, with the exact strings of ADR-0133 decision 3.
   - The four `hypotheses_*` kinds are the `hypotheses_tool` constants, re-exported as `verdicts_tool` does. `verdicts_mismatch` is `verdicts_tool.KIND_VERDICTS_MISMATCH`.
   - Re-grep `hilclaw/`, `tests/` and `orchestration/` before the PR. None of the new strings may already be in use with another meaning. Report the result in the Result.
5. **Encoding edge, not decided by the record.** A hypothesis or verdicts file can hold content that `json.dumps(..., allow_nan=False)` or UTF-8 cannot encode: a number beyond the float range, or a lone surrogate, in a top-level member no record defines. Do **not** invent a kind for it, and do not map it onto a kind of decision 3. Let the exception pass out of the tool function so that `tools.call` answers it as it answers any other exception (state which kind that is in the docstring). Cover it with a test, and name it in Follow-ups as an open point for a later record. Do the same for any `cases.InvalidCaseError` from `cases.build` that is not chained to a `MismatchError`, and for a `cases_file` refusal that cannot arise after a successful build (`InvalidCaseFileError`, `WrittenFormError`). These are not mapped.
6. **Not journaled** (ADR-0133 decision 3; ADR-0124 decision 3).
   - The tool appends no line to `events.ndjson`, selects no backend, and keeps nothing between calls.
   - It reads only `STATE.json`, `instance.json`, the two key record files, `hypotheses.json` and `verdicts.json`. It writes only through `cases_file.write`.
   - It creates no directory, and in particular no key directory.
7. **Reuse without changing behaviour.**
   - You may make the `STATE.json` / `instance.json` read of `hilclaw/run_file_tools.py` callable from the new module, for example by factoring its private read into a function both use. The four existing tools must keep their exact answers and messages, and their existing tests must pass unchanged.
   - Do the same if you factor the `run_id`/`round` comparison out of `hypotheses_tool._read`. In that case add `hilclaw/hypotheses_tool.py` to the touched files only if the 5-file cap still holds. If it would not, duplicate the few lines instead.
8. **Registration.**
   - `default_registry` in `hilclaw/tools.py` registers `case_tool.definition(data_root_source)`, imported lazily like the others.
   - Its docstring names `case.write` (`hilclaw.case_tool.definition`, ADR-0133 decision 3), with which the Round-Manager writes a round's case.
   - Update `DEFAULT_SET` in `tests/test_tools.py`, `ACCEPTED` in `tests/test_default_registry_schemas.py` (accepted request `{"run_id": "r1", "round": 1}`) and the name lists in `tests/test_mcp_front.py`.
9. **Docstrings of `hilclaw/cases.py` and `hilclaw/cases_file.py`.**
   - Narrow the "Promotion (whether, when and by whom ...) is open" sentences. For the runs of ADR-0120 decision 1, the case is written by the tool `case.write` (`hilclaw.case_tool`, ADR-0133): which rounds, and when.
   - What stays open stays named: `best.json` and `technique_stats.json`, OD-29, OD-25, OD-17 beyond ADR-0133 decision 5, the key directory's creation (OD-26), and runs outside ADR-0120 decision 1.
   - No behaviour change in either module.
10. **Tests: `tests/test_case_tool.py`, new**, following D12 and DRIVER §5. Each scenario below is a test.
    - **Happy paths** (ADR-0133 Walk-through):
      - A round with valid hypotheses and verdicts: the file sits at `layout.case_record(...)`, `cases_file.parse` accepts its bytes, the copies are byte-equal by JSON value to the source documents, and `with_verdicts` is true.
      - A round whose verdicts are all `inconclusive`.
      - A round with no `verdicts.json`: no `verdict_record` member, and `with_verdicts` false.
      - The tool called through `tools.call` on `default_registry`, and through the MCP front by its MCP name once.
    - **Every kind, in order.** For each kind of AC 3, a fixture where every earlier check passes and only that one fails.
      - Include `round_not_current` for a request after `STATE.json`'s round has moved on, and for one before it.
      - Include `key_not_stored` for an instance without `op_signature`, for no key directory, for an `hw_profile.json` alone, and for a key directory without `op_signature.json`.
      - Include `key_record_invalid` for a corrupt record and for a colliding record.
      - Include `hypotheses_missing` and a `hypotheses_invalid` that comes from a `run_id` or `round` mismatch.
      - Include `verdicts_invalid` for invalid bytes, for a directory in its place and for a mismatched `round`, plus `verdicts_unsupported` and `verdicts_mismatch`.
      - Include `case_exists` on a second call, where the first case is byte-identical afterwards, and `case_not_written`.
      - Include `no_data_root` and the `*_unreadable` kinds through a seam (for example `monkeypatch` of the read or of `once_write.write_once`), as the neighbouring tool tests do.
    - **Order**: at least three fixtures with two failures at once, showing that the earlier check decides. One is `invalid_request` before `no_data_root`. One is `round_not_current` before `key_not_stored`. One is `key_not_stored` before `hypotheses_missing`.
    - **Negative requests**: an extra member, a missing member, a bad `run_id`, `round` 0, a `bool`, a float, `MAX_INTEGER + 1`, and a non-callable `source`.
    - **Nothing created on refusal**:
      - After each refused call the tree under the data root holds the same entries. In particular, no key directory or `db/` is created when `key_not_stored` is answered.
      - `STATE.json`, `instance.json`, `hypotheses.json` and `verdicts.json` are byte-identical after every call.
      - No `events.ndjson` appears.
    - The encoding edge of AC 5.
    - Coverage of the new module, and of every touched module's public functions, as CI requires (line ≥ 80% and function ≥ 80% for `hilclaw/`).
11. **No data-plane change.** No member, file, path, value, version or `events.ndjson` kind of any data-plane file is added or changed, and no validator changes. If the implementation needs any of these, stop and return BLOCKED with the question.
12. **Procedure**:
    - Code mode: open a Draft PR, run the reviewer cycle (dev-code-review), get CI green (pytest, ruff, the test-existence and coverage gates), then squash-merge with `gh pr merge --squash --body` whose last line is `Task: T-0363`, and delete the branch.
    - The commit body carries one line on the language choice (Python, because the registry and every reused module are Python).
    - Never start `claude`, and use no stub of it either: this tool needs none (D16).

## Out of Scope

- The promotion step in `orchestration/round-manager.md` (ADR-0133 slice 2, written with P2-1's round steps), and any agent definition or `.claude/` change.
- Who creates the key directory and its record files (OD-26). Do not add a caller of `key_records.store_*` outside tests.
- `best.json`, `technique_stats.json`, the lookup and selection side (ADR-0073, ADR-0132 / T-0361), HQ-0043, HQ-0031, HQ-0040, HQ-0041.
- Any `ARCHITECTURE/` edit, and any edit of an earlier ADR.
- Refactoring the private `_STEP_OF` of `check_identity.py` (a deferred T-0359 follow-up), and any other clean-up outside AC 7.
- Starting `claude`, or requiring a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- ADR-0133 slice 2: the promotion step in "The round steps" of `orchestration/round-manager.md`, with `mcp__hilclaw__case_write` added to its tool sentence, written with PLAN P2-1.
- The next record that P2-7's storing half needs (ADR-0133 Consequences): an OD-26 record for first-case runs, covering who stores the two key record files, when, and how they enter a commit. Until it exists, every real `case.write` answers `key_not_stored`.
- The encoding edge of AC 5, if the executor confirms it can occur: a point for a later record. It is not decided here.

## Result

- **Outcome**: DONE. PR #208 (`claude/T-0363-case-write-tool`), squash-merged; the merge commit is the one whose last line is `Task: T-0363`. The reviewer approved in round 3 of 3. CI was green: Python gate 3.11/3.14, Coverage gate, Test presence, sh gate and C gate.
- **Language**: Python, because the registry and every reused module are Python.
- **What landed**:
  - New module `hilclaw/case_tool.py`, the tool `case.write` (MCP `case_write`). It runs the nine checks of ADR-0133 decision 3 in order, and its kinds carry the record's exact strings.
  - `hilclaw/run_file_tools.py`: the `STATE.json` / `instance.json` read is factored into the public `read(data_root, run_id, name)`, so `state.read` and `instance.read` share it with `case.write`. Their answers and messages are unchanged, and their existing tests pass unchanged.
  - `default_registry` registers the tool, and its docstring names it.
  - `hilclaw/cases.py` and `hilclaw/cases_file.py`: only their docstrings change. The promotion sentences now point to `case.write` / ADR-0133, and the open points stay named: `best.json`/`technique_stats.json` (OD-20, OD-7), OD-29, OD-25, NFR-1, OD-17 beyond ADR-0133 decision 5, OD-26, and runs outside ADR-0120 decision 1.
  - The `run_id`/`round` comparison of `hypotheses_tool._read` is duplicated (`case_tool._same`) and not factored out, so `hilclaw/hypotheses_tool.py` is untouched (AC 7, 5-file cap).
- **Messages beyond the AC minimum**:
  - `key_not_stored` from a lookup miss names the key directory (`db/<hw>/<op>`), because `key_records.lookup` does not say which record file is missing.
  - `case_not_written` adds "the key directory is not an existing directory" when the key directory vanished after ⑤ (review round 1).
- **Kind re-grep (AC 4)**: searched `hilclaw/`, `tests/` and `orchestration/` before the PR. `round_not_current`, `key_not_stored`, `key_record_invalid`, `key_record_unreadable`, `verdicts_invalid`, `verdicts_unsupported`, `verdicts_unreadable`, `case_exists` and `case_not_written` occur only in `hilclaw/case_tool.py` and `tests/test_case_tool.py`. The one other hit is `case_exists`, which the new `hilclaw/cases_file.py` docstring sentence uses with the same meaning. No string was in use with another meaning.
- **Files outside `touchesFiles`** (tests only):
  - `tests/test_blob_tools.py` and `tests/test_check_definition.py` pin the full default-registry name list, so they had to change.
  - The new public `run_file_tools.read` is tested in `tests/test_case_tool.py`.
- **Size**:
  - Non-test change is about 430 lines, over the 300 LOC cap and the 260 estimate. `hilclaw/case_tool.py` alone is about 355 lines, most of it the module docstring, the `#:` lines and the model-facing description that AC 1 requires.
  - It was not split. The tool, its registration and its tests form one unit, and a partial tool cannot be registered (DRIVER §5).
- **Tests**:
  - `tests/test_case_tool.py` has 86 tests. They cover every kind in order, the order pairs of AC 10 plus two more, the negative requests, and the nothing-created and byte-identical properties. They also cover no `events.ndjson`, the encoding edge (`1e999` and a lone `\ud800` in an undefined top-level member of `hypotheses.json` give `tool_crashed` through `tools.call`, with nothing written), and an unmapped `InvalidCaseError`.
  - `hilclaw/case_tool.py` and `hilclaw/run_file_tools.py` have 100 % line coverage. The full suite (24509 passed) gives 97 % total line coverage for `hilclaw/`.
  - No `claude` and no stub of it are used.
- **AC 5 finding**: the encoding edge does occur. `hypotheses_file.parse` and `verdicts_file.parse` accept a float-overflowing number or a lone-surrogate escape in an undefined top-level member, and `cases.build` / `cases.validate` pass it on. The tool then answers `tool_crashed` and writes nothing. No `InvalidCaseError` not chained to a `MismatchError`, and no `cases_file` refusal after a successful build, was found reachable; both are left unmapped.
- **Follow-ups**:
  - The three Follow-ups of this task stand: ADR-0133 slice 2 in `orchestration/round-manager.md`; an OD-26 record for the key directory, until which every real `case.write` answers `key_not_stored`; and the encoding edge as an open point for a later record, now confirmed to occur.
  - No new follow-up.
