---
id: T-0365
title: Add the registry tool key.store of ADR-0134 decision 3, which stores the two key record files a run's instance.json states (ADR-0134 slice 1, tool half; PLAN P2-7)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-13, FR-14, FR-18, NFR-1, OD-26, OD-23, S0, S1]
dependsOn: [T-0364]
touchesFiles:
  - hilclaw/key_store_tool.py
  - hilclaw/tools.py
  - tests/test_key_store_tool.py
  - tests/test_tools.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
estimatedSize: {loc: 220, files: 2}
hq: []
---
## Why

PLAN P2-7 is a checklist item: store a round's hypothesis-outcome case at the round's end, and look cases up by exact key. It comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply.

`case.write` (T-0363) refuses every case of a real first-case run with `key_not_stored`, because nothing creates the key directory `db/<hw_profile_key>/<op_signature>/` and its two record files. ADR-0134 (landed on main as 961dbfd, T-0364) decides that the Round-Manager stores them itself through a new registry tool, `key.store`. Its Consequences name slice 1 as "Now": the tool, plus the widening of `run.commit` by decision 7, "one task or two". This task is the tool half. The `run.commit` widening changes landed behaviour pinned by `tests/test_run_commit.py`, so it is a separate next task, which keeps each review small. Without this tool, P2-5's first run stores no case (FR-18).

The tool reads `instance.json` as a file, so a test writes that file itself. It does not need the unlanded start function of PR #186 (T-0324, BLOCKED on HQ-0032), and it touches none of that PR's files.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (code mode).
  - §3-5 (executor procedure, the resume rule, the 2 h 30 min time limit).
  - §5: naming (branch `claude/T-0365-<slug>`, a PR title containing `T-0365`, the trailer `Task: T-0365`, and `Task: T-0365` as the last line of the PR body used as the squash message); the size cap, which excludes tests; the language line in the Result; test rules ① to ⑤.
- `CLAUDE.md`: all rules. In particular:
  - the test rules (D12);
  - the language policy (Python here, with one line in the commit body saying why);
  - the A-13 code-mode procedure and its BLOCKED reasons (a data-plane schema change is one);
  - "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- **The record to implement**: `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`. Read the Decision (lines 23-90) and Consequences (lines 108-120). Decision 3's table is the contract: request, result, the six checks in order, and their kinds. Decision 6 gives the answer for each outcome that is not a plain success.
- Context for the contract:
  - `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decisions 2 to 4.
  - `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decisions 2 and 3.
  - `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decision 4 (lines 69-99, the MCP name mapping).
  - `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decision 3 (lines 43-63).
  - `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md` decision 3 (lines 39-54).
- Code, in this order:
  - `hilclaw/case_tool.py` (whole). It is the closest model for the module shape, the description, the input schema, `_checked`, `_key`, `_relative` and `_reported`.
  - `hilclaw/key_records.py`: the module docstring, the three error classes, `store_hw_profile`, `store_op_signature`, `_root`, `_read` and `_store`.
  - `hilclaw/run_file_tools.py` `read` (from line 197).
  - `hilclaw/run_files.py` (`NOT_THERE`, `relative`, `data_root_is_there`).
  - `hilclaw/instance.py` `Instance` and `parse` (the `hw_profile`, `hw_profile_key` and `op_signature` members).
  - `hilclaw/layout.py` (`hw_profile_dir`, `op_signature_dir` or their equivalents).
  - `hilclaw/run_admission.py` line 70 (`KIND_OP_SIGNATURE_NOT_STATED`).
  - `hilclaw/tools.py` (`ToolFailure`, the kind pattern, `default_registry` from line 182).
  - `hilclaw/data_root_source.py`.
- Tests to model on and to extend:
  - `tests/test_case_tool.py` and `tests/test_key_records.py`;
  - `tests/test_tools.py` (`DEFAULT_SET`) and `tests/test_default_registry_schemas.py` (`ACCEPTED`);
  - the tool-name lists in `tests/test_mcp_front.py`, `tests/test_blob_tools.py` (around lines 176-190 and 700) and `tests/test_check_definition.py` (around lines 120-135, 380-430 and 660).
- Before you start, run `gh pr list`. Open PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files outside this task, so it does not overlap. If another open PR touches a file of `touchesFiles`, stop and return BLOCKED (DRIVER §3-3). The unlanded branch `claude/T-0361-*` (ADR-0132, not a PR) also registers a tool in `hilclaw/tools.py`. Take nothing from it; whichever lands later rebases there.

## Acceptance Criteria

1. **New module `hilclaw/key_store_tool.py`.** It exposes `definition(source)`, which returns a `tools.ToolDefinition` for the name `key.store` (MCP `key_store`), as `case_tool.definition` does.
   - `source` is asked once per call, after the request is checked.
   - `definition` raises `TypeError` for a `source` that is not callable.
   - The module docstring states the contract below and cites ADR-0134. Each `KIND_*` constant carries a `#:` line.
   - Description and input schema:
     - The description tells the model the request, the result, and every failure kind in order.
     - The input schema has `run_id` with the same pattern as the other tools, required, and `additionalProperties: false`.
2. **Request and result** (ADR-0134 decision 3).
   - The request is exactly `run_id`. Any other member, a missing `run_id`, or a `run_id` that `layout.check_run_id` refuses gives `invalid_request`.
   - The result is `{"hw_profile_created": bool, "op_signature_created": bool}`. Each value is the `created` flag of the matching `key_records.Stored`.
3. **The checks, in exactly this order.** The first failing check decides, and nothing is created before ⑤.
   1. The request (`invalid_request`).
   2. The data root, through `data_root_source.obtain` (`no_data_root`).
   3. `instance.json`, read once by `run_file_tools.read(data_root, run_id, "instance.json")`, which gives the four `run_file_*` kinds exactly as `instance.read` answers them.
   4. An `op_signature` stated. An instance whose `op_signature` is `None` gives `op_signature_not_stated`, and nothing is stored, not even the hw_profile (decision 4).
   5. `key_records.store_hw_profile(data_root, instance.hw_profile)`:
      - `KeyCollisionError` or `CorruptKeyRecordError` gives `key_record_invalid`.
      - Any `OSError` gives `key_not_written`. This includes a failing read of a stored record, a data root removed since ②, and the `FileExistsError` that `_store` raises when the name was taken during the write and is free again when re-read.
   6. `key_records.store_op_signature(data_root, instance.hw_profile_key, instance.op_signature.record)`:
      - The same two kinds as ⑤.
      - `KeyRecordNotFoundError` (a hw_profile record gone since ⑤) also gives `key_not_written`.
      - A refusal here keeps the file ⑤ created (decision 3; ADR-0014 decision 6). Do not remove it.

   Every failure message starts with the path concerned, relative to the data root, where there is one. A message for an `OSError` uses the class and the system text, without the absolute path, and says when the data root is gone, as `case_tool._reported` does. Before you pass `instance.hw_profile` or `instance.hw_profile_key`, check the form `store_*` expects (a mapping record, a `keys.Key` or a name) against `hilclaw/instance.py` and `hilclaw/case_tool.py` `_key`.
4. **Kinds.**
   - `KIND_OP_SIGNATURE_NOT_STATED` reuses the string `"op_signature_not_stated"` of ADR-0041 decision 4. Import it from `run_admission` if that adds no import cycle and does not import NumPy when the registry is built. Otherwise define it with the same string and say why in the commit body.
   - `KIND_KEY_RECORD_INVALID` is `case_tool.KIND_KEY_RECORD_INVALID`, re-exported.
   - New: `KIND_KEY_NOT_WRITTEN = "key_not_written"`.
   - Re-grep `hilclaw/`, `tests/` and `orchestration/` before the PR. `key.store`, `key_store` and `key_not_written` must not already be in use with another meaning. Report the result in the Result.
5. **Not mapped, not invented.** An `InvalidRecordError` (or any other error of `hilclaw.keys` or `hilclaw.layout`) from `store_*` cannot arise for a valid parsed `instance.json` (decision 4). Do not map it to a kind. Let it pass out of the tool function so that `tools.call` answers it as it answers any other exception, and state which kind that is in the docstring. Cover it with one test through a seam.
6. **Not journaled, nothing else checked** (ADR-0134 decision 3).
   - The tool appends no line to `events.ndjson`, selects no backend, and keeps nothing between calls.
   - It reads `instance.json` and, through `key_records`, the two record files. It does not read `STATE.json`, and it checks neither the round nor the scope.
   - It writes only through `key_records.store_hw_profile` and `store_op_signature`.
   - It does not compare stored attributes (`hw_source`, `label`) with the instance's, and does not report a difference (decision 6).
7. **Registration.**
   - `default_registry` in `hilclaw/tools.py` registers `key_store_tool.definition(data_root_source)`, imported lazily like the others.
   - Its docstring names `key.store` (`hilclaw.key_store_tool.definition`, ADR-0134 decision 3), with which the Round-Manager stores its run's two key record files.
   - Update the tool-name lists: `DEFAULT_SET` in `tests/test_tools.py`; `ACCEPTED` in `tests/test_default_registry_schemas.py`, with `{"run_id": "r1"}` as the accepted request; and the lists in `tests/test_mcp_front.py`, `tests/test_blob_tools.py` and `tests/test_check_definition.py`. Registry order is sorted by name, so `key.store` falls between `instance.read` and `run.commit`. Adjust any slice index that shifts.
   - Leave the `hilclaw/key_records.py` docstring unchanged ("registers no key on its own" stays true of the module; ADR-0134 Consequences).
8. **Tests: `tests/test_key_store_tool.py`, new**, following D12 and DRIVER §5. Each scenario below is a test.
   - **Happy paths** (the ADR-0134 Walk-through rows that the tool alone shows):
     - A fresh key gives `true`, `true`. Both files are at their `layout` paths, and `key_records.lookup` of the instance's two records then hits.
     - A second call gives `false`, `false`, and both files are byte-identical afterwards.
     - A key stored with another `hw_source` or `label` gives `false`, `false`. The stored file is unchanged, and the run's `instance.json` is unchanged.
     - An `hw_profile.json` already stored without `op_signature.json` gives `false`, `true`.
     - A `case.write` after `key.store`, on a fixture with a valid `STATE.json` and `hypotheses.json`, no longer answers `key_not_stored`. This ties the slice to ADR-0133.
     - One call through `tools.call` on `default_registry`, and one through the MCP front by its MCP name.
   - **Every kind, in order.** For each kind of AC 3, a fixture where every earlier check passes and only that one fails. Include:
     - each of the four `run_file_*` kinds;
     - `op_signature_not_stated`, where `db/` is not created;
     - `key_record_invalid` at ⑤ for a corrupt `hw_profile.json` and for a colliding one;
     - `key_record_invalid` at ⑥ for a corrupt `op_signature.json` and for a colliding one;
     - `key_not_written` at ⑤ and at ⑥ through a seam (for example `monkeypatch` of `once_write.write_once`), with the `hw_profile.json` of ⑤ kept after a refusal at ⑥;
     - `key_not_written` for a data root removed after ②, and for `KeyRecordNotFoundError` at ⑥;
     - `no_data_root`.
   - **Order**: at least three fixtures with two failures at once, showing that the earlier check decides. Use `invalid_request` before `no_data_root`, a `run_file_*` kind before anything in `db/`, and `op_signature_not_stated` before a corrupt stored `hw_profile.json`.
   - **Negative requests**: an extra member, no member, a bad `run_id`, a non-string `run_id`, and a non-callable `source`.
   - **Nothing created on refusal before ⑤**: after each such refused call, the tree under the data root holds the same entries and `instance.json` is byte-identical. No `events.ndjson` appears in any test.
   - The unmapped error of AC 5.
   - Coverage of the new module, and of every public function of the touched modules, as CI requires (line ≥ 80% and function ≥ 80% for `hilclaw/`).
9. **No data-plane change.** No member, file, path, value, version or `events.ndjson` kind of any data-plane file is added or changed, and no validator changes. If the implementation needs any of these, stop and return BLOCKED with the question.
10. **Procedure.**
    - Code mode: open a Draft PR, run the reviewer cycle (dev-code-review), and get CI green (pytest, ruff, the test-existence gate and the coverage gate).
    - Then squash-merge with `gh pr merge --squash --body`, whose last line is `Task: T-0365`, and delete the branch.
    - The commit body carries one line on the language choice: Python, because the registry and every reused module are Python.
    - Never start `claude`, and use no stub of it either: this tool needs none (D16).

## Out of Scope

- The widening of `hilclaw/run_commit.py` by ADR-0134 decision 7 (record files that `HEAD` does not hold go into the run's commit), with its docstring, its tool description and `tests/test_run_commit.py`. That is the next task.
- The `key.store` step in "The round steps" of `orchestration/round-manager.md` (ADR-0134 slice 2, written with P2-1's round steps), and any agent definition or `.claude/` change.
- Updating a stored attribute, the onboarding registry (#5 B-2), the `hw_source` of `cpu_standin`, OD-8 ⑱, HQ-0032 and HQ-0043.
- Any `ARCHITECTURE/` edit, any edit of an earlier ADR, and the "less exact" docstrings that ADR-0134 Consequences lists, other than `default_registry`'s.
- Starting `claude`, or requiring a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- ADR-0134 slice 1, second half: the widening of `run.commit` by decision 7 in `hilclaw/run_commit.py`, its docstring and tool description, and the decision-7 cases added to `tests/test_run_commit.py`. Reviewer hint from T-0364: test that when nothing is owed, no record file is committed either, and that a record file `HEAD` holds is never taken in again.
- ADR-0134 slice 2: the `key.store` step in `orchestration/round-manager.md`, with P2-1.

## Result

- **Outcome**: DONE. PR #209 (`claude/T-0365-key-store-tool`), squash-merged; the merge commit is the one whose last line is `Task: T-0365`. The reviewer approved in round 1 and again in round 2 of 2 (round 1 had two non-blocking nits: a doubled "and" in the `default_registry` docstring, fixed; a message at ⑥ starting with the hw_profile path for a hw_profile record damaged between ⑤ and ⑥, accepted as the path concerned). CI was green: Python gate 3.11/3.14, Coverage gate, Test presence, sh gate and C gate.
- **Language**: Python, because the registry and every reused module are Python.
- **What landed**:
  - New module `hilclaw/key_store_tool.py`, the tool `key.store` (MCP `key_store`), with the six checks of ADR-0134 decision 3 in order. Errors of ⑤ and ⑥ are mapped by one context manager: `KeyCollisionError`/`CorruptKeyRecordError` give `key_record_invalid` (the `key_records` message, which starts with the relative record path); `KeyRecordNotFoundError` and any `OSError` give `key_not_written`, the message starting with the path of the file not written. `OSError` texts carry class and `strerror` only, plus "the data root is not an existing directory" when it is gone.
  - Errors of `keys`/`layout` from a store are not mapped; `tools.call` answers them with `tool_crashed` (docstring and one seam test).
  - `KIND_OP_SIGNATURE_NOT_STATED` is imported from `run_admission`: no import cycle (the tool module is imported lazily by `default_registry`), and `run_admission` imports no NumPy; `test_building_the_default_registry_imports_no_numpy` and the MCP-front listing test still pass. `KIND_KEY_RECORD_INVALID` is `case_tool.KIND_KEY_RECORD_INVALID`.
  - `default_registry` registers the tool and its docstring names it; the tool-name lists of `tests/test_tools.py`, `tests/test_default_registry_schemas.py` (`{"run_id": "r1"}`), `tests/test_mcp_front.py`, `tests/test_blob_tools.py` and `tests/test_check_definition.py` gain `key.store`/`key_store`. The `[:5]`/`[5:]` slices of `test_blob_tools.py` needed no change (the new name sorts after index 5). `hilclaw/key_records.py` is unchanged.
- **Re-grep (AC 4)**: before the PR, `key.store`, `key_store` and `key_not_written` (fixed strings) occurred nowhere in `hilclaw/`, `tests/` or `orchestration/`. A regex search for `key.store` matches only "key stored" in the `key_records` docstring, a different phrase, not a use of the name.
- **Tests**: `tests/test_key_store_tool.py`, 52 tests: the walk-through rows the tool shows (fresh key, second call byte-identical, other `hw_source`/`label` kept, hw_profile stored without op_signature, `case.write` no longer `key_not_stored` after the store, `tools.call` and the MCP front by `key_store`); every kind in order (four `run_file_*`, `op_signature_not_stated` with no `db/`, `key_record_invalid` at ⑤ for corrupt, colliding and directory-in-place records and at ⑥ for corrupt and colliding ones, `key_not_written` at ⑤ and ⑥ through `once_write.write_once`, a name taken and free again, an unreadable stored record, a data root removed after ②, a hw_profile record gone before ⑥, `no_data_root`); four order pairs; negative requests and a non-callable source; tree and `instance.json` unchanged on every refusal before ⑤; no `events.ndjson` in any test (fixture teardown); the unmapped error. `hilclaw/key_store_tool.py` and `hilclaw/tools.py` have 100 % line coverage; the full local suite passed (24579 passed, 724 skipped), total `hilclaw/` line coverage 97 %.
- **Size**: about 230 non-test lines changed (module 225, `tools.py` 6), most of the module the docstring and the model-facing description.
- **Data plane**: no member, file, path, value, version, event kind or validator changed.
- **D16**: no `claude` was started and no stub of it was used. Runtime acceptance items of this slice are those ADR-0134 already lists, (xxvii) and (xxviii) (HQ-0050); none is new.
- **Follow-ups**: those of this task stand (the `run.commit` widening of ADR-0134 decision 7; slice 2 in `orchestration/round-manager.md`). No new follow-up.
