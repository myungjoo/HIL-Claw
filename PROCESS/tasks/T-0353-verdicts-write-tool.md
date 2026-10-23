---
id: T-0353
title: Add the registry tool verdicts.write of ADR-0128 decision 6 in a new module of hilclaw/, registered in the default registry (ADR-0128 Consequences slice 1; PLAN P2-3, P2-6)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-9, FR-17, NFR-1, OD-23, OD-16, OD-30, S0, S1]
dependsOn: [T-0352]
touchesFiles:
  - hilclaw/verdicts_tool.py
  - hilclaw/tools.py
  - hilclaw/verdicts_file.py
  - hilclaw/verdicts_hypotheses.py
  - tests/test_verdicts_tool.py
  - tests/test___main__.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_tools.py
estimatedSize: {loc: 240, files: 4}
hq: []
---
## Why

PLAN P2-3 (the evaluator) and P2-6 (hypothesis records and their verdicts) are checklist items, so the D18 rule for non-checklist work does not apply. Both come before P2-5 in the P2 order. ADR-0128 (T-0352) decided that, for the runs of ADR-0120 decision 1, the `evaluator` sub-agent has no Write, Edit or Bash. The round's `rounds/<RRRR>/eval/verdicts.json` is written for it by a new registry tool, `verdicts.write` (MCP name `verdicts_write`). ADR-0128 Consequences lists this tool as slice 1, "Now". Without it, no agent can write a verdicts file within ADR-0128's rules, so a first run cannot record the verdicts FR-17 asks for. The definition `orchestration/agents/evaluator.md` (slice 2) lists this tool in its `tools`, so this slice comes first.

The record fixes the request, the result, the order of the checks and the failure kinds (ADR-0128 decision 6, table). It leaves three things to this slice: the encoding of `record` into the bytes that `verdicts_file.write` takes, the description, and the input schema. Nothing here needs an owner answer. HQ-0040 and HQ-0041 concern the coder call. HQ-0032 is PR #186, which touches `hilclaw/start_instance.py` and other test files, not these files. No other open HQ concerns this tool.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": language policy, test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: Decision 2 (third bullet), Decision 3 (first bullet), **Decision 6 in full, with its table**, the Walk-through rows "Round 2 reaches evaluate", "The record gives a hypothesis no verdict …" and "The verdicts of the round were already written", and Consequences slice 1.
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: §1 (place, name, write), §2 (the file as a whole, text form), §3 (one verdict, evidence entries and their `kind`), §6 (round 0).
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` §3: the model for tools of the registry that are not FR-10 tools and are not journaled.
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 2 to 4 (tool definition, `invalid_request`, data-root source, the `run_id` member).
- `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md`: decisions 2 to 4 (what the `ACCEPTED` entry of the new tool must satisfy).
- `hilclaw/run_file_tools.py`, whole file. It is the closest pattern for request checking, the order of the data-root source, descriptions, input schemas and the reporting of `OSError`.
- `hilclaw/verdicts_file.py`: the module docstring, `parse`, `final_name`, `write` and the error classes.
- `hilclaw/verdicts_hypotheses.py`: the module docstring and `check`.
- `hilclaw/hypotheses_file.py`: the module docstring and `parse` (reading the round's `hypotheses.json`).
- `hilclaw/verdicts.py`: `validate` and the evidence entry `kind` values.
- `hilclaw/layout.py`: `check_run_id`, `hypothesis_record`, `verdict_record`.
- `hilclaw/tools.py`: the module docstring, `ToolDefinition`, `ToolFailure`, the kind constants and `RESERVED_KINDS`, and `default_registry`.
- `hilclaw/mcp_front.py`: `mcp_name`.
- `tests/test_run_file_tools.py` and `tests/test_default_registry_schemas.py`, as the pattern for the new tests and for the `ACCEPTED` entry.

## Acceptance Criteria

1. **New module** `hilclaw/verdicts_tool.py` (the executor may choose a clearer name and then updates `touchesFiles` in `## Result`). It has a module docstring that names ADR-0128 decision 6. It exposes `definition(source)`, which returns one `tools.ToolDefinition` for `verdicts.write` bound to the data-root source `source`. The source is not called at definition time, and a non-callable `source` raises `TypeError` (as in `run_file_tools.definitions`).
2. **Behaviour of the tool function**, exactly as ADR-0128 decision 6 states it:
   - The request is exactly `{"run_id": ..., "record": ...}`. Both are required. Any other member, a missing member, a `run_id` that `layout.check_run_id` refuses, or a `record` that is not a JSON object is `invalid_request`. The input schema has the form of `run_file_tools` (`additionalProperties: false`, the same `run_id` pattern, `record` of type `object`).
   - `record` is encoded into bytes by a fixed rule that the executor picks and states in the module docstring. The rule must produce UTF-8 JSON text with no byte order mark, ending with one line feed and holding no carriage return byte. The bytes are checked with `verdicts_file.parse` before the data-root source is asked. Every refusal of `parse` (invalid, other `schema_version`, a round-0 record per ADR-0071 decision 6) is `invalid_request`, as is a `record` whose `run_id` differs from the request's.
   - Then the data root is obtained with `data_root_source.obtain(source)`. A failure is `no_data_root`.
   - Then the tool reads the round's `decision/hypotheses.json` at `layout.hypothesis_record(data_root, run_id, round)` and parses it with `hypotheses_file.parse`. The failures map to new kinds of this module: not there → `hypotheses_missing`; invalid, or not a regular file → `hypotheses_invalid`; another `schema_version` → `hypotheses_unsupported`; any other `OSError` → `hypotheses_unreadable`.
   - Then `verdicts_hypotheses.check(record, hypotheses)`. A `MismatchError` is `verdicts_mismatch`, and its message names the broken rule.
   - Then any evidence entry of `kind` `comparison` in any verdict is `comparison_not_given`.
   - Then `verdicts_file.write(data_root, content)`. `NameTakenError` is `verdicts_exist`. Every `OSError` is `verdicts_not_written`, with the message reported as `run_file_tools._reported` reports it.
   - The result is `{}`.
   - Every check before the write creates nothing. The tool is not journaled, appends nothing to `events.ndjson`, selects no backend and reads no file but `hypotheses.json`. None of its kinds is added to `RESERVED_KINDS`, and each kind is a module constant with a `#:` comment, in the manner of `run_file_tools`.
   - The description tells the model what the tool writes, that the data root is never part of the request, that a refused record can be corrected and sent again, that a comparison entry is refused for now, and lists every failure kind, in the manner of `run_file_tools._DESCRIPTIONS`.
3. **`hilclaw/tools.py`**: `default_registry` registers `verdicts.write` from the new module, in the source only, and its docstring names the tool and ADR-0128. Building the registry still imports no NumPy (the existing check in `tests/test_check_definition.py`).
4. **Docstrings** (ADR-0128 Consequences slice 1): in `hilclaw/verdicts_file.py`, the sentence "Which agent writes the file and when … are open" says that, for the runs of ADR-0120 decision 1, the tool `verdicts.write` writes the file for the evaluator (ADR-0128). When it is written, a taken name and a second write stay open. In `hilclaw/verdicts_hypotheses.py`, "it does not decide who calls it" names `verdicts.write` as one caller. Behaviour does not change in either module.
5. **Tests** in a new file `tests/test_verdicts_tool.py`, using a temporary data root built by the test. A valid hypothesis record is written with `hypotheses_file.write` or as bytes. No `claude` is started, stub or real. The tests pass on Linux CI and on the local Windows machine. They cover at least:
   - happy: a valid round-1 record with `check` entries only, all verdicts `inconclusive`, is written, and the file at `layout.verdict_record` parses back to the given record; the result is `{}`; the missing directories up to `eval/` are created;
   - branch: the encoded bytes end with exactly one line feed and hold no carriage return; a record whose strings hold non-ASCII text round-trips; the data-root source is not asked when the request or the record is refused;
   - negative and error: each `invalid_request` form (extra member, missing member, bad `run_id`, non-object `record`, invalid record, round-0 record, other `schema_version`, `run_id` mismatch); `no_data_root`; each `hypotheses_*` kind, with `hypotheses_unreadable` reached through a seam or a directory at the file's place (whichever the executor's mapping gives), not by changing permissions that Windows ignores; `verdicts_mismatch` for a missing verdict, for a verdict of an unknown `id` and for a `verdict` value against the rule; `comparison_not_given` for a record with one `comparison` entry that would otherwise pass; `verdicts_exist` when the file exists, with its content unchanged; `verdicts_not_written` through a seam of the write; after every refusal before the write, no file or directory has been created under `eval/`;
   - registry: `verdicts.write` is listed by `default_registry` and through the MCP front as `verdicts_write`. The listing tests in the test files of `touchesFiles` are updated, and `tests/test_default_registry_schemas.py` gets an `ACCEPTED` entry that satisfies ADR-0077.
6. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases (invalid input, failure paths); ③ every public function of the new module and of each touched module that changes behaviour is tested; ④ the new module has its own test file; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
7. **No data-plane change**: `verdicts.json` keeps its record, version and validator. No member, file, kind of event, value or version of `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, `hypotheses.json` or `verdicts.json` is added, and no validator changes. The new failure kinds are tool-layer names (ADR-0128 decision 6). If the work turns out to need a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
8. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
9. Code mode (A-13): a Draft PR whose title contains `T-0353`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0353`, and the branch `claude/T-0353-verdicts-write-tool` deleted.
10. No `claude` process is started, and nothing runtime-only is required (D16). Runtime acceptance items (xviii) to (xx) of ADR-0128 are not closed by this task.

## Out of Scope

- `orchestration/agents/evaluator.md` and its `LAYOUT` copy (ADR-0128 slice 2), and any change to `orchestration/round-manager.md`.
- The read, standing and comparison tools (ADR-0128 slice 3). Lifting `comparison_not_given` is left to the record that adds the comparison tool.
- Holding a `check` entry's `outcome` against the log, `eval.json` (OD-20), and when a second write is allowed (ADR-0128 Boundaries).
- Any edit of `ARCHITECTURE/` documents, and the wording fixes of earlier ADRs (D18 hold).
- `hilclaw/start_instance.py` and the other files of PR #186.

## Follow-ups

- Next slice for the planner: `orchestration/agents/evaluator.md` (ADR-0128 decision 7, Consequences slice 2), whose `tools` list includes `mcp__hilclaw__verdicts_write`.

## Result

- Outcome: DONE. PR #202 squash-merged as 9fbc00c; branch `claude/T-0353-verdicts-write-tool` deleted.
- Review: reviewer agent, 2 rounds, Approve. Round 1 had one minor and three nits; the minor and two nits were addressed in 33456a2, and the `_reported` duplication was kept on purpose (see below). Round 2 had one nit, a duplicated assert, which is not in the file, so no change was made.
- CI: all six gates green on head 33456a2. Locally: ruff check/format clean; full pytest 24095 passed, 724 skipped; coverage of `hilclaw/` 97 %, `hilclaw/verdicts_tool.py` 100 %.
- Files: new `hilclaw/verdicts_tool.py` (name as planned) and `tests/test_verdicts_tool.py`. Also changed: `hilclaw/tools.py` (registration and docstring), and the docstrings of `hilclaw/verdicts_file.py` and `hilclaw/verdicts_hypotheses.py`; the listing tests in `tests/test___main__.py`, `test_blob_tools.py`, `test_check_definition.py`, `test_mcp_front.py` and `test_tools.py`; and the `ACCEPTED` entry in `tests/test_default_registry_schemas.py`. No file outside `touchesFiles` was changed.
- Encoding rule (stated in the module docstring): `json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n"`, in UTF-8 with no BOM and members kept in the given order. A string UTF-8 cannot encode (a lone surrogate) is `invalid_request`.
- Mapping of the `hypotheses.json` read: a directory at the file's place is `hypotheses_invalid` (not a regular file), so the tests reach `hypotheses_unreadable` through a `Path.read_bytes` seam.
- The OSError message is composed like `run_file_tools._reported`. The five lines are copied rather than importing a private name, because ruff SLF001 is on for the package. Possible follow-up: move the helper to a public function of `run_files`.
- Language: Python, because the tool is a function of the existing Python registry and reuses its Python parsers and writers.
- No data-plane change. No `claude` was started. Runtime acceptance items (xviii) to (xx) of ADR-0128 stay open.
