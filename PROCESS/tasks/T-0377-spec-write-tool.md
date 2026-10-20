---
id: T-0377
title: Add the registry tool spec.write of ADR-0138 decision 3, which composes and writes the spec of the first round-0 coder call of a first-case run (ADR-0138 slice 1; PLAN P2-1/P2-2)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-5, OD-6, OD-23, OD-28, S0]
dependsOn: [T-0376]
touchesFiles:
  - hilclaw/spec_tool.py
  - hilclaw/tools.py
  - hilclaw/spec_file.py
  - tests/test_spec_tool.py
  - tests/test_tools.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
estimatedSize: {loc: 230, files: 3}
hq: []
---
## Why

PLAN P2-1 (Round-Manager round 0: bring-up and baseline) and P2-2 (coder-driver: `claude -p` call, spec passing) are checklist items. They come before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply.

Today nothing in `hilclaw/` issues a spec. `hilclaw.coder_call.call` performs a coder call only for a spec file already written, so the round-0 bring-up call of P2-5's first run has no spec to read. ADR-0138 (landed on main as acb6801, T-0376) decides what that one spec holds and that a new registry tool, `spec.write`, composes and writes it. Its Consequences name slice 1 as "Now": a new module `hilclaw/spec_tool.py` with its test file, plus the registration in `default_registry`. The slice does not wait on HQ-0040, and it fits the D4 cap. This task is that slice.

Slice 2 (the `coder-driver` definition and the Round-Manager delegation step) waits on HQ-0040 and is not part of this task. HQ-0053 (T-0375, the coder's sign-in) is not touched. The tool needs no `claude` and no hardware: tests use fixture `instance.json` files only (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (code mode).
  - §3-5 (executor procedure, the resume rule, the time limit).
  - §5: naming (branch `claude/T-0377-<slug>`, a PR title containing `T-0377`, the trailer `Task: T-0377`, and `Task: T-0377` as the last line of the PR body used as the squash message); the size cap, which excludes tests; the language line in the Result; test rules ① to ⑤.
- `CLAUDE.md`: all rules. In particular:
  - the test rules (D12);
  - the language policy (Python here, with one line in the commit body saying why);
  - the A-13 code-mode procedure and its BLOCKED reasons (a data-plane schema change is one; this task makes none);
  - "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- **The record to implement**: `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`.
  - Decision 1 (lines 33-37): the scope.
  - Decision 2 (lines 38-61): the member table, which is the content contract, and points (a) to (c).
  - Decision 3 (lines 62-80): the tool table (name, request, result, checks ① to ⑧ in order) and the bullets after it (nothing created before ⑧, ⑦ cannot refuse today, `spec_exists`, the kinds, not journaled, what is left to the code slice).
  - Walk-through (lines 87-97).
  - Consequences slice 1 and "Less exact, not edited" (lines 110-125).
- Context for the contract:
  - `ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md` decisions 2 to 4 (the spec members).
  - `ARCHITECTURE/decisions/ADR-0029-od8-spec-file.md` decisions 2 to 4 (the written form, the final name, the write steps).
  - `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decisions 2 to 4.
  - `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decisions 2 and 3.
  - `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decision 4 (the MCP name mapping).
  - `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md` decision 3, the precedent for a tuple check and for "reading is the tool's step".
- Code, in this order:
  - `hilclaw/key_store_tool.py` (whole, 213 lines) and `hilclaw/case_tool.py` (whole). They are the closest models for the module shape, the description, the input schema, `_checked`, `_relative` and `_reported`.
  - `hilclaw/spec_file.py`: the module docstring (lines 1-161), `parse`, `final_name`, `write` and the four error classes (from line 174).
  - `hilclaw/spec.py`: the module docstring and `validate`.
  - `hilclaw/gemm_contract.py`: `covers` and `task_contract`.
  - `hilclaw/instance.py`: `OpSignature` and `Instance` (lines 666-725) and `parse`.
  - `hilclaw/run_file_tools.py` `read` (from line 197).
  - `hilclaw/run_admission.py` lines 70-74 (`KIND_OP_SIGNATURE_NOT_STATED`, `KIND_OP_SIGNATURE_NOT_COVERED`), `hilclaw/run_objective.py` line 58 (`KIND_OBJECTIVE_NOT_STATED`), `hilclaw/coder_call.py` line 69 (`KIND_SPEC_INVALID`).
  - `hilclaw/tools.py` (`ToolFailure`, the kind constants at lines 29-39, `default_registry` from line 182).
  - `hilclaw/data_root_source.py`.
- Tests to model on and to extend:
  - `tests/test_key_store_tool.py`, `tests/test_case_tool.py` and `tests/test_spec_file.py`;
  - `tests/test_tools.py` (`DEFAULT_SET`) and `tests/test_default_registry_schemas.py` (`ACCEPTED`);
  - the tool-name lists in `tests/test_mcp_front.py`, `tests/test_blob_tools.py` and `tests/test_check_definition.py`. `git show f291c5f -- tests/` shows exactly where T-0365 added `key.store` to each of them; add `spec.write` in the same places.
- Before you start, run `gh pr list`. Open PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`, none of them in `touchesFiles`, so it does not overlap. If another open PR touches a file of `touchesFiles`, stop and return BLOCKED (DRIVER §3-3). The unlanded branch `claude/T-0361-*` (ADR-0132, not a PR) also registers a tool in `hilclaw/tools.py`. Take nothing from it; whichever lands later rebases there.

## Acceptance Criteria

1. **New module `hilclaw/spec_tool.py`.** It exposes `definition(source)`, which returns a `tools.ToolDefinition` for the name `spec.write` (MCP `spec_write`), as `key_store_tool.definition` does.
   - `source` is asked once per call, after the request is checked.
   - `definition` raises `TypeError` for a `source` that is not callable.
   - The module docstring states the contract below and cites ADR-0138. Each `KIND_*` constant carries a `#:` line. Reused kinds are bound to the existing constants (`tools`, `run_admission`, `run_objective`, `coder_call`), not retyped as new strings.
   - The description tells the model the request, the result, and every failure kind in check order. The input schema has `run_id` (the same pattern as the other tools), `round`, `candidate` and `attempt`, all required, with `additionalProperties: false`.
2. **Request and result** (ADR-0138 decision 3).
   - The request is exactly `run_id`, `round`, `candidate`, `attempt`, with the meaning and form of ADR-0015 decision 4. Any other member, a missing member, a value of the wrong type or form, or a tuple other than `round` 0, `candidate` 1, `attempt` 1 gives `invalid_request`.
   - The result is the empty object `{}`.
3. **The checks, in exactly this order.** The first failing check decides. Nothing is created before ⑧, and only the run's `instance.json` is read; `STATE.json` and the stored key records under `db/` are not read.
   1. The request (`invalid_request`).
   2. The data root, through `data_root_source.obtain` (`no_data_root`).
   3. `instance.json`, read once by `run_file_tools.read(data_root, run_id, "instance.json")`, which gives the four `run_file_*` kinds.
   4. `candidates_per_round` stated (`candidates_per_round_not_stated`) and equal to 1 (`candidates_per_round_not_covered`).
   5. `op_signature` stated (`op_signature_not_stated`) and covered by `gemm_contract.covers` (`op_signature_not_covered`).
   6. `objective` stated (`objective_not_stated`).
   7. The document of ADR-0138 decision 2 composed, encoded in the written form of ADR-0029 decision 2 (UTF-8, a final line feed, no carriage return), accepted by `spec_file.parse` and given its final name by `spec_file.final_name`. A refusal of either gives `spec_invalid`.
   8. The content written by `spec_file.write`. `NameTakenError` gives `spec_exists`: nothing is written, and the file under the name is not read or compared. Any other failure of the file system gives `spec_not_written`.
4. **The composed document** is exactly the table of ADR-0138 decision 2:
   - `schema_version` 2;
   - `id` = {`run_id` from the request, `round` 0, `candidate` 1, `attempt` 1, `candidates` 1, `relation` `"single"`}, with no `variant`;
   - `hw_profile` = {`key`, `record`} taken unchanged from the instance's `hw_profile_key` and `hw_profile`;
   - `task.op_signature` = {`key`, `record`} taken unchanged from the instance's `op_signature`, `label` and `ext` of the record included;
   - `task.contract` = `gemm_contract.task_contract(m, k, n)` of that record's `shape`;
   - `task.objective` = the instance's `objective`, the same JSON value;
   - `guidance.techniques` = `[]`;
   - `feedback.attempts` = `[]`;
   - no `task.build`, `feedback.base`, `repair` or `ext`.
   A test reads the written file back and compares it member by member with these sources, and checks that its path is `runs/<run_id>/rounds/0000/coder/candidates/01/attempts/01/spec.json`.
5. **Kinds.** The four new kinds are module constants with these exact strings: `candidates_per_round_not_stated`, `candidates_per_round_not_covered`, `spec_exists`, `spec_not_written`. Each one matches the kind pattern of `hilclaw/tools.py`. Every failure message that names a file uses the path relative to the data root, as the model modules do.
6. **Registration.** `default_registry` in `hilclaw/tools.py` registers `spec_tool.definition(data_root_source)`, and its docstring names `spec.write` with ADR-0138 decision 3 and the coder-driver as its caller. The name lists in `tests/test_tools.py`, `tests/test_default_registry_schemas.py`, `tests/test_mcp_front.py`, `tests/test_blob_tools.py` and `tests/test_check_definition.py` gain `spec.write` / `spec_write`, so every existing test passes.
7. **Docstrings made false.** The last sentence of the module docstring of `hilclaw/spec_file.py` ("What composes or writes a spec, when, … are open") is rewritten so that it is true once this tool exists: for the spec of ADR-0138 decision 1 the tool `spec.write` (`hilclaw.spec_tool`) composes and writes it; for every other spec, and for what follows a taken name and a second write for a tuple, it stays open. Nothing else of that docstring changes. "builds no spec" in `hilclaw/spec.py` and `hilclaw/gemm_contract.py` stays true of those modules, so they are not edited (ADR-0138 Consequences).
8. **Tests** (`tests/test_spec_tool.py`, new), with fixture `instance.json` files written by the test (do not use the unlanded `hilclaw.start_instance`):
   - happy: the Walk-through row 1, with a covered op_signature, N 1 and an objective; the result is `{}` and the file content is as in criterion 4 and in the written form;
   - an `op_signature` record with `label` and `ext` is carried whole;
   - each kind of criterion 3 reached at its own check, including `invalid_request` for each wrong tuple member (`round` 1, `candidate` 2, `attempt` 2), for an extra member and for a missing member; `candidates_per_round` absent and 2; `op_signature` absent and not covered (for example `fp16` or `col_major`); `objective` absent;
   - order: a file that fails ④ and ⑤ together reports ④; no file or directory is created under `runs/<run_id>/rounds/` for any refusal before ⑧;
   - `spec_exists` on a second call for the same run, with the first file left byte-for-byte unchanged;
   - `spec_not_written` for a non-name failure of `spec_file.write` (for example by monkeypatching it to raise `OSError`);
   - `spec_invalid` by monkeypatching the composition or `spec_file.parse` to refuse (⑦ cannot refuse today, ADR-0138 decision 3);
   - `definition` with a non-callable source raises `TypeError`, and the tool reached through `default_registry` and the MCP front name `spec_write` works end to end.
   - Line and function coverage of `hilclaw/` stays at least 80 % (D12 ①).
9. **No data-plane change.** No member, file, kind, value or version of the data plane is added or changed and no validator changes. If the implementation seems to need one, stop and return BLOCKED (A-13).
10. **No `claude` is started** at any point, and nothing is required of the machine beyond the package's existing test dependencies (D16).

## Out of Scope

- ADR-0138 slice 2: `orchestration/agents/coder-driver.md`, the Round-Manager delegation step in `orchestration/round-manager.md`, any allowlist. It waits on HQ-0040.
- Any spec other than that of ADR-0138 decision 1: later rounds, other candidates, repair attempts, N above 1.
- What follows `spec_exists` (OD-8 ㉖ (가); OD-23 ① (가)); any check of a stored spec against its instance.
- Changes to `hilclaw/coder_call.py`, `hilclaw/spec.py`, `hilclaw/gemm_contract.py`, `hilclaw/instance.py` or any `ARCHITECTURE/` file. The "Less exact, not edited" ADR sentences of ADR-0138 Consequences are not edited.
- The files of open PR #186 and anything from the unlanded branches `claude/T-0361-*` and `claude/T-0375-*`.

## Follow-ups

- Planner's view of what follows: ADR-0138 slice 2 after HQ-0040 is answered.

## Result

- **Outcome**: DONE. PR #217 (`claude/T-0377-spec-write-tool`), squash-merged; the merge commit is the one whose last line is `Task: T-0377`. Reviewer rounds: see the PR comments (round 1 Approve with three minor notes, all answered here). CI green: Python gate 3.11/3.14, Coverage gate, Test presence, sh gate, C gate.
- **Language**: Python, because the registry and every reused module are Python.
- **What landed**:
  - New module `hilclaw/spec_tool.py`, the tool `spec.write` (MCP `spec_write`) with the eight checks of ADR-0138 decision 3 in order. The request check takes exactly the four members, refuses a non-`int` (a `bool` included) number and any tuple other than 0, 1, 1; the input schema states each number with `minimum` = `maximum`. ⑦ maps a failing encoding, a content out of the written form, `spec_file.parse` refusals (`InvalidSpecFileError`, `UnsupportedVersionError`) and `final_name` refusals to `spec_invalid`; ⑧ maps `NameTakenError` to `spec_exists` and any `OSError` to `spec_not_written` (class and `strerror` only, plus "the data root is not an existing directory" when it is gone). An error of `gemm_contract.covers` is not mapped (`tool_crashed` through `tools.call`).
  - Reused kinds are bound to `run_admission.KIND_OP_SIGNATURE_NOT_STATED`/`_NOT_COVERED`, `run_objective.KIND_OBJECTIVE_NOT_STATED` and `coder_call.KIND_SPEC_INVALID`; importing `coder_call` pulls in no NumPy (checked) and causes no cycle (`default_registry` imports tool modules lazily).
  - `default_registry` registers it, and its docstring names `spec.write` with ADR-0138 decision 3 and the coder-driver. The last sentence of the `hilclaw/spec_file.py` module docstring now names `spec.write` for the spec of ADR-0138 decision 1 and keeps every other spec, a taken name and a second write open. `hilclaw/spec.py` and `hilclaw/gemm_contract.py` are not edited.
  - The tool-name lists of `tests/test_tools.py`, `tests/test_default_registry_schemas.py`, `tests/test_mcp_front.py`, `tests/test_blob_tools.py` and `tests/test_check_definition.py` gain `spec.write`/`spec_write`.
  - **Outside `touchesFiles`**: `tests/test_gemm_contract.py::test_module_is_bound_by_the_default_registry_only_and_imports_keys_only` failed once `spec_tool.py` names `gemm_contract`; it now admits `spec_tool.py` beside `check_definition.py` (the function name stays true: both are bound by the default registry). Draft PR #186 (T-0324, BLOCKED on HQ-0032) edits the same function to admit `start_instance.py`, so whichever of the two lands later needs a trivial rebase of that hunk. Taken as necessary for AC 6 ("every existing test passes"); the reviewer agreed.
- **Tests**: `tests/test_spec_tool.py`, 74 tests: the happy path compared member by member with `instance.json` and the path `runs/<run_id>/rounds/0000/coder/candidates/01/attempts/01/spec.json` and the exact bytes; `label`/`ext` carried whole; the run's hw_profile carried while a corrupt stored record and a corrupt `STATE.json` are ignored; every kind at its check (each wrong tuple member, extra and missing members, bad types, the four `run_file_*` kinds, N absent/2/7, op_signature absent/`fp16`/`col_major`/m 0, objective absent, `spec_invalid` by monkeypatching `parse`, `final_name`, `_compose` and `_encoded`, `spec_exists` with the first file and a foreign file under the name unchanged and unread, `spec_not_written` through `once_write.write_once`, `spec_file.write` and a data root removed after ②); order pairs ①/②, ②/③, ④/⑤, ⑤/⑥, ⑥/⑦, ⑦/⑧; the tree unchanged and no `rounds/` directory for every refusal before ⑧; the registry and the MCP front by `spec_write`. `hilclaw/spec_tool.py` has 100 % line and branch coverage; the full local suite passed (25134 passed, 728 skipped), total `hilclaw/` coverage 97 %.
- **Size (D4)**: about 327 non-test lines changed (module 314, `tools.py` 6, `spec_file.py` 7), above the 300 cap and the 230 estimate; most of the module is the docstring and the model-facing description the acceptance criteria ask for. The tool is one unit (definition, checks, composition, write), so no split was proposed.
- **Data plane**: no member, file, path, kind value of the data plane, version or validator changed; the four new kinds are names of the tool layer.
- **D16**: no `claude` was started and no stub of it was used. The runtime acceptance item of this slice is the one ADR-0138 already lists, (xxxiii) (HQ-0054); none is new.
- **Follow-ups**:
  - ADR-0138 slice 2 after HQ-0040 (as planned).
  - `hilclaw/gemm_contract.py` module docstring: "It is bound to one tool: `covers` is the predicate of the `correctness.check` …" is no longer exact, since `spec.write` also calls `covers` and `task_contract`. The file was out of scope here; a docstring-only fix (together with the T-0324 follow-up on `standin_profile.py` if that lands) is left to the planner.
