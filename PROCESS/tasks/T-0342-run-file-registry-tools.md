---
id: T-0342
title: Add the four registry tools of ADR-0124 (state.read, instance.read, run.fresh, state.write) and register them in the default registry
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-10, FR-13, NFR-1, NFR-6, OD-23, OD-18, S0, S1]
dependsOn: [T-0341]
touchesFiles:
  - hilclaw/run_file_tools.py
  - hilclaw/tools.py
  - hilclaw/run_state_file.py
  - hilclaw/fresh_run.py
  - orchestration/round-manager.md
  - tests/test_run_file_tools.py
  - tests/test_default_registry_schemas.py
  - tests/test_check_definition.py
  - tests/test_mcp_front.py
  - tests/test___main__.py
estimatedSize: {loc: 260, files: 5}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one of its slices, so the D18 priority rule for non-checklist work does not apply. The round-0 steps of the Round-Manager cannot be written until the Round-Manager has a means to read its run's `STATE.json` and `instance.json`, tell a fresh run directory, and write `STATE.json`; the P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) needs those steps.

ADR-0124 (landed as 6de1c68, T-0341) decided the means: four typed tools of the registry, called through the MCP front with `run_id` in the request, and named this code slice in its Consequences. This task writes that slice. It is code mode (A-13). It needs no live `claude`: every check runs in-process or through the package's own fronts, and nothing here starts `claude` (D16). Whether a real `-p` turn session sees and may call the tools is ADR-0124 runtime acceptance items (x) and (xi), already recorded as HQ-0038; this task does not close them.

Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files; no overlap with `touchesFiles`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, test rules D12).
- `CLAUDE.md`, "상시 규칙": comment minimisation, the three-layer model, "개발 드라이버와 런타임의 구분" (D16), the language policy, the code-mode branch/merge procedure (A-13), the test rules (D12).
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`, whole file. Decisions 2 to 5 and the Walk-through are the contract of this task; Consequences, first bullet, names this slice.
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md`, decisions 2 to 4 and 6 (the `run_file_*` kinds and the message form), as widened by ADR-0124 decision 3.
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`, decisions 2 to 4 (tool definition, data-root source asked after the request is checked, `run_id` form).
- `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`, decision 2 (the steps; step 1 is the validity check) and decision 7 (nothing carried over).
- `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md`, decisions 2 to 4 (what `tests/test_default_registry_schemas.py` checks of every tool of the default registry).
- `ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md`, decision 3 (refusing any other request member) — the model followed by `hilclaw/blob_tools.py`.
- Code: `hilclaw/blob_tools.py` (whole; the model for a module of tool definitions), `hilclaw/tools.py` (lines 1-60 and `default_registry`), `hilclaw/data_root_source.py` (`obtain`), `hilclaw/run_files.py` (whole: `reading`, `read_failure`, `NOT_THERE`), `hilclaw/run_journal.py` (`read_state`, `MissingStateError`), `hilclaw/run_state.py` (module docstring, `parse`, `validate`, `from_stored`, `dump`, the two error classes), `hilclaw/instance.py` (`InvalidInstanceError`, `UnsupportedVersionError`, `MissingInstanceError`, `parse`, `read` at about lines 597-615 and 682 and 848-883), `hilclaw/fresh_run.py` (whole), `hilclaw/run_state_file.py` (whole), `hilclaw/layout.py` (`check_run_id`, `run_file`), `hilclaw/journaled_step.py` lines 130-150 (an existing kind map for `reading`), `orchestration/round-manager.md` (whole).
- Tests that enumerate the default registry (update them, do not weaken them): `tests/test_default_registry_schemas.py` (`ACCEPTED` and the three tests at the end), `tests/test_check_definition.py` (`registry.names() ==`), `tests/test_mcp_front.py` (the tool-name lists around lines 23, 455, 496, 929, 1018), `tests/test___main__.py` (`FIXED_NAMES` and the fixed-set test around line 205).

## Acceptance Criteria

### Before editing

1. Run `gh pr list`. If an open PR other than #186 touches a file of `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).

### The module `hilclaw/run_file_tools.py` (new; name may be changed if a better one fits, keep one new module)

2. A function `definitions(source)` in the shape of `blob_tools.definitions`: returns a tuple of four `tools.ToolDefinition` for `state.read`, `instance.read`, `run.fresh` and `state.write`, each with its own description (written for the calling agent: what it reads or writes, the result members, that the data root is never in the request) and input schema. Raises `TypeError` when `source` is not callable. The source is asked at each call, after the request is checked, never at build time.
3. Request check, common to all four, before the data-root source is asked: the request has exactly the members of ADR-0124 decision 3 (`run_id`; `state.write` also `state`); any other member, a missing member, and a `run_id` that `layout.check_run_id` refuses are `invalid_request`.
4. `state.read`: result `{"state": <object>}`. `instance.read`: result `{"instance": <object>}`. Each reads its file **once per call** (no second read for the result): the place is checked by `os.lstat` as `run_journal.read_state` / `instance.read` do (missing -> `run_file_missing`; not a regular file -> `run_file_invalid`), the bytes are validated by `run_state.parse` / `instance.parse`, and the result object is the JSON parsed from those same bytes (members as stored, ADR-0124 decision 3). Error classes map through `run_files.reading` to `run_file_missing`, `run_file_invalid`, `run_file_unsupported`, and any other `OSError` to `run_file_unreadable`; messages start with `runs/<run_id>/<file>` (ADR-0019 decision 6). A missing `STATE.json` is a failure, not a result. If reusing `read_state` / `instance.read` with a rebuilt object is clearly simpler and still yields the stored members for every valid file, the executor may choose it and must state why in the commit body.
5. `run.fresh`: result `{"fresh": <bool>}` from `fresh_run.is_fresh`. Any `OSError` it raises becomes the new kind `run_dir_unreadable` (a module constant `KIND_RUN_DIR_UNREADABLE`, not added to `tools.RESERVED_KINDS`).
6. `state.write`: `state` must be a JSON object that `run_state.validate` accepts at version 1 and that `run_state.dump(round, from_stored(budget_spent), others)` can write, with `others` = every member but `schema_version`, `round`, `budget_spent`. Anything else — not an object, invalid, another `schema_version` (`UnsupportedVersionError`) — is `invalid_request`, raised **before** the data-root source is asked and before anything is written. Then `run_state_file.replace(data_root, run_id, round, view, others)`; any `OSError` it raises becomes the new kind `state_not_written` (module constant `KIND_STATE_NOT_WRITTEN`, not reserved). Result: `{}`. The content written is exactly the content given; nothing is read or carried over (ADR-0013 decision 7).
7. None of the four is journaled: no line is appended to `events.ndjson`, nothing but `STATE.json` (and its temporary file during `state.write`) is created, and no backend is selected.
8. The module docstring states what the four tools read and write, that they are registry tools beside the FR-10 tools, not journaled, and the ADR they implement; it follows the comment-minimisation rule otherwise.

### Registration and docstrings

9. `hilclaw/tools.py` `default_registry` registers the four definitions from the same data-root source; its docstring names them with `hilclaw.run_file_tools` and ADR-0124. `registry.names()` becomes `("blob.fetch", "blob.push", "correctness.check", "instance.read", "run.fresh", "state.read", "state.write")`. Building the registry still asks no source and imports no NumPy.
10. `hilclaw/run_state_file.py`: replace "is not a tool: who calls it is open (OD-23, …)" with a sentence saying the tool `state.write` of `hilclaw.run_file_tools` calls it (ADR-0124), keeping what remains open (the rest of OD-17; sub-questions 10, 12 and 15 of OD-8) as far as it is still true. `hilclaw/fresh_run.py`: replace "how the Round-Manager reaches ``replace`` (OD-23, OD-18)" in the same way, and note that `run.fresh` is a tool over `is_fresh` (its "is no FR-10 tool" stays true).
11. `orchestration/round-manager.md`, section "Your run": add the rule of ADR-0124 decision 2 in at most four lines — the Round-Manager reads its run's `STATE.json` and `instance.json`, tells a fresh run directory and writes `STATE.json` only through `mcp__hilclaw__state_read`, `mcp__hilclaw__instance_read`, `mcp__hilclaw__run_fresh` and `mcp__hilclaw__state_write`, with its run id in each request; it does not use Bash or its own file tools on these two files. Do not touch "The steps of a round".

### Tests (D12; tests are outside the size cap)

12. New `tests/test_run_file_tools.py`, with a temporary data root and `blob_tools`-style sources (a counting/failing source and one returning the path):
    - happy: each tool through `tools.call` on a valid run — `state.read` and `instance.read` return objects equal to `json.loads` of the files (including a member not defined by ADR-0012 and a total above `keys.MAX_INTEGER`); `run.fresh` true on a directory holding only `instance.json`, false once `STATE.json` exists; `state.write` writes round 0 start values to a fresh run, and a later write replaces it; a written file reads back equal through `state.read` and `run_journal.read_state`.
    - the Walk-through of ADR-0124: the round-0 sequence (state.read -> `run_file_missing`, run.fresh -> true, instance.read, state.write) and the "neither file is there" case (`run_file_missing`, fresh false).
    - error/negative: extra member, missing member, bad `run_id`, `state` not an object, `state` invalid, `state` of `schema_version` 2 — all `invalid_request` with `source.calls == 0` and nothing written; a failing source -> `no_data_root`; `STATE.json` / `instance.json` invalid, of another version, a directory in its place, or unreadable (e.g. a monkeypatched read raising `PermissionError`) -> the matching `run_file_*` kind with the relative path at the start of the message; `is_fresh` raising an `OSError` other than not-there -> `run_dir_unreadable`; `replace` raising an `OSError` -> `state_not_written` and the previous `STATE.json` unchanged.
    - branch: `definitions` with a non-callable source -> `TypeError`; no line appended to `events.ndjson` by any call.
    - the CLI and MCP fronts each serve at least one of the four tools (as `test_check_definition.py` does for `correctness.check`), with the MCP names `state_read`, `instance_read`, `run_fresh`, `state_write`.
13. Update the tests that enumerate the default registry so they hold the seven names and give each new tool an accepted request in `tests/test_default_registry_schemas.py` (`ACCEPTED`); all three of its tests must pass for the new tools, i.e. every request the stated schema refuses is `invalid_request` with no source call, and the accepted request reaches the source. Do not loosen any existing assertion.
14. Full `pytest` passes; `ruff check` and `ruff format --check` pass; `hilclaw/` line and function coverage stay at or above 80%.

### Mode and result

15. Code mode (A-13): branch `claude/T-0342-run-file-registry-tools`, commits with trailer `Task: T-0342`, Draft PR titled with `T-0342`, reviewer cycle (dev-code-review, at most 7 rounds), CI green, then squash-merge with the PR body (last line `Task: T-0342`) via `gh pr merge --squash --body`, and delete the branch. Never `git push --force*`.
16. `## Result`: PR and merge commit, review rounds, the language chosen (Python, the package language) with one line of reason, and any follow-ups.

## Out of Scope

- The steps of a round in `orchestration/round-manager.md` (the round-0 slice of P2-1) and anything ADR-0124 lists as still waited on: OD-18 ⑯ (가), OD-8 ⑪, who folds the spend view, how a `-p` turn session is permitted to call the tools.
- Any hook, allowlist, permission option or check of a request's `run_id` against the session's run (rest of OD-18, PLAN P2-4); the roster and sub-agents (rest of OD-23); the lock (rest of OD-17).
- Holding the layout stamp before a read (㉗ (가)); `state.write` refusing without `instance.json` (ADR-0124 Alternatives (a′)); carrying members over (Alternatives (a″)).
- Any data-plane change: no new member, file, kind, value or version, and no validator change. The two new tool failure kinds are tool-layer names only.
- Editing any ADR or register; the "Less exact, not edited" list of ADR-0124 Consequences (besides the two docstrings of criterion 10).
- `hilclaw/start_instance.py` and anything of PR #186 (HQ-0032).
- Starting a real `claude`, or requiring a logged-in `claude`, a board or an API key (D16). Runtime acceptance items (x) and (xi) stay with HQ-0038.

## Follow-ups

- Next for P2-1: the record of OD-18 ⑯ (가) (whether the self-check runs again at a resume), then OD-8 ⑪ (the commit step), then who folds the round-end spend view (OD-23), then the round-0 steps of the Round-Manager definition.

## Result

- Landed: PR #195 (Draft, DONOTMERGE removed), squash-merged as a08ec70; branch claude/T-0342-run-file-registry-tools deleted.
- Review: 4 rounds by the context-isolated dev-reviewer, all Approve. Fixed in the PR: docstring precision (state.write may create runs/ and the run directory); no absolute data-root path in state_not_written / run_dir_unreadable messages; a test pinning bad_result for a number beyond the float range; two renamed front tests; round-manager.md rewrap; one long line.
- New hilclaw/run_file_tools.py defines state.read, instance.read, run.fresh and state.write (ADR-0124), registered in default_registry. The reads read the file once, validate it with run_state.parse / instance.parse and return json.loads of those bytes (read_state / instance.read not reused: they return package values, not the stored object). New unreserved kinds: run_dir_unreadable, state_not_written.
- Docstrings of run_state_file.py / fresh_run.py updated. orchestration/round-manager.md "Your run" gains the 4-line rule of ADR-0124 decision 2.
- Tests: new tests/test_run_file_tools.py (71 tests); the seven names are in every registry-enumerating test. tests/test_blob_tools.py and tests/test_tools.py were outside touchesFiles but had to change because they also list the default registry.
- Local: full pytest 23805 passed, ruff check/format clean, hilclaw/ line coverage 97% (run_file_tools.py 100%). CI green on ff3f934. No real claude started (D16).
- Language: Python, the language of the hilclaw package the tools extend.
- Follow-up (not needed for P2-5/P2-14, no task): a state file holding a number beyond the float range in a member neither validator defines makes state.read fail with bad_result (documented and tested). Runtime acceptance items (x) and (xi) remain with HQ-0038.
