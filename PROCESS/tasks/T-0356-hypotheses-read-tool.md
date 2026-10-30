---
id: T-0356
title: Add the registry tool hypotheses.read of ADR-0129 decision 3, register it in the default registry, and give it to the evaluator (ADR-0129 Consequences slices 1 and 2; PLAN P2-3, P2-6)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-9, FR-11, FR-17, NFR-1, OD-23, OD-18, OD-30, S0, S1]
dependsOn: [T-0353, T-0354, T-0355]
touchesFiles:
  - hilclaw/hypotheses_tool.py
  - hilclaw/tools.py
  - hilclaw/verdicts_tool.py
  - orchestration/agents/evaluator.md
  - tests/test_hypotheses_tool.py
  - tests/test___main__.py
  - tests/test_blob_tools.py
  - tests/test_check_definition.py
  - tests/test_default_registry_schemas.py
  - tests/test_mcp_front.py
  - tests/test_tools.py
  - tests/test_turn_definition.py
estimatedSize: {loc: 180, files: 4}
hq: []
---
## Why

ADR-0129 (landed as fdc9664, task T-0355) decides that the evaluator of a first-case turn reads a round's `rounds/<RRRR>/decision/hypotheses.json` through a new typed registry tool `hypotheses.read` (MCP name `mcp__hilclaw__hypotheses_read`). Its Consequences name two code slices that can be done now: slice 1, the tool in a module of `hilclaw/` with its test file, registered in `default_registry`; slice 2, the tool added to the evaluator's `tools` list in `orchestration/agents/evaluator.md`, with the "Verdicts" paragraph's reason narrowed to the missing results read. This task does both slices. Together they stay inside the size cap.

Priority (DRIVER §6, D18): this is work on the checklist items PLAN P2-3 (evaluator) and P2-6 (hypothesis records and verdicts). The verdicts work of rounds 1 to 4 of the first run (P2-5, the near goal) needs this read before the evaluator can write verdicts. It is not input hardening and not a wording cleanup.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": language policy, test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md`, whole file. Read **Decision 3 with its table**, Decision 4, Decision 5, the Walk-through and Consequences slices 1 and 2 closely.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: Decision 3 (the evaluator's `tools` list, later tools added "by the records or slices that create them"), Decision 6 (the `hypotheses_*` kinds of `verdicts.write`).
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`: decisions 2 and 5 (a file is valid only when its `run_id` and `round` are those of its path; round 0 has no record).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 2 to 4 (tool definition, `invalid_request`, data-root source, the `run_id` and `round` members).
- `ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md`: decisions 2 to 4 (what the `ACCEPTED` entry of the new tool must satisfy).
- `hilclaw/verdicts_tool.py`, whole file. It is the closest pattern, and its `_hypotheses` function is the read this tool must repeat with the same kinds and messages.
- `hilclaw/run_file_tools.py`: the module docstring, `_DESCRIPTIONS`, `_read`, and the handling of `bad_result` (for the open point on numbers beyond the float range, ADR-0129 decision 3, last bullet).
- `hilclaw/hypotheses_file.py`: the module docstring, `parse`, `final_name` and the error classes.
- `hilclaw/layout.py`: `check_run_id`, `hypothesis_record`. `hilclaw/keys.py`: `MAX_INTEGER`.
- `hilclaw/tools.py`: the module docstring, `ToolDefinition`, `ToolFailure`, the kind constants, `RESERVED_KINDS`, and `default_registry` with its docstring.
- `hilclaw/mcp_front.py`: `mcp_name`, `SERVER_NAME`.
- `orchestration/agents/evaluator.md`, whole file.
- `tests/test_verdicts_tool.py`, `tests/test_run_file_tools.py`, `tests/test_default_registry_schemas.py` and `tests/test_turn_definition.py` (`EVALUATOR_TOOLS`, `test_the_evaluator_frontmatter`), as the pattern for the new tests and for the listing tests that must be updated.

## Acceptance Criteria

1. **New module** `hilclaw/hypotheses_tool.py` (the executor may choose a clearer name and then updates `touchesFiles` in `## Result`). It has a module docstring that names ADR-0129 decision 3 and states the request, result, checks in order and kinds. It exposes `definition(source)`, which returns one `tools.ToolDefinition` for `hypotheses.read` bound to the data-root source `source`. The source is not called at definition time. A non-callable `source` raises `TypeError`, as in `verdicts_tool.definition`.
2. **Behaviour of the tool function**, exactly as the table of ADR-0129 decision 3 states it:
   - The request is exactly `{"run_id": ..., "round": ...}`. Both are required. Any other member, a missing member, a `run_id` that `layout.check_run_id` refuses, or a `round` that is not an integer (a `bool` is not an integer) from 1 to `keys.MAX_INTEGER` is `invalid_request`. Round 0 is among these refusals. The input schema has the form of `verdicts_tool._input_schema` (`additionalProperties: false`, the same `run_id` pattern, `round` an integer with `minimum` 1 and `maximum` `keys.MAX_INTEGER`).
   - Then the data root is obtained with `data_root_source.obtain(source)`. A failure is `no_data_root`. The source is not asked when the request is refused.
   - Then the tool reads and parses the round's file with the same kinds `verdicts.write` uses for it: a place holding no regular file → `hypotheses_invalid`; no file → `hypotheses_missing`; any other failing read → `hypotheses_unreadable`; bytes `hypotheses_file.parse` refuses → `hypotheses_invalid`; another `schema_version` → `hypotheses_unsupported`. The kind strings are the ones `verdicts_tool` already defines. The executor either reuses `verdicts_tool`'s constants and read function from the new module, or moves the read into the new module and makes `verdicts_tool` use it. In both cases the behaviour, kinds and messages of `verdicts.write` do not change, and the existing `tests/test_verdicts_tool.py` passes unchanged. The executor states the choice in `## Result`.
   - Then a document whose `run_id` or `round` differs from the request's is `hypotheses_invalid`, and its message names the member that differs.
   - The result is `{"record": document}`: the whole parsed document, its members as stored, unknown top-level members included.
   - The executor decides what a number beyond the float range in a top-level member that no record defines does to the result (ADR-0129 decision 3 leaves it to this slice; `state.read` answers `bad_result`). The choice is stated in the module docstring and tested.
   - The tool is not journaled, appends nothing to `events.ndjson`, selects no backend, reads no `STATE.json` and reads no file but the round's `hypotheses.json`. It creates nothing and keeps nothing between calls. No new kind is added, and none is added to `RESERVED_KINDS`.
   - The description tells the model what the tool reads, that the data root is never part of the request, that round 0 is refused, that the result is the whole record under `record`, and lists every failure kind, in the manner of `verdicts_tool._DESCRIPTION`.
3. **`hilclaw/tools.py`**: `default_registry` registers `hypotheses.read` from the new module, in the source only, and its docstring names the tool and ADR-0129 (the docstring's list of the set is one of the "less exact" items of ADR-0129 Consequences). Building the registry still imports no NumPy (the existing check in `tests/test_check_definition.py`).
4. **`orchestration/agents/evaluator.md`** (ADR-0129 decision 4, decision 5, Consequences slice 2):
   - `mcp__hilclaw__hypotheses_read` is added to the frontmatter `tools` list. No other entry is added or removed.
   - The "Verdicts" paragraph's reason is narrowed to the missing results read: on a verdicts delegation the evaluator still reports in one line that the verdicts of round `<round>` cannot yet be written, now because no tool reads the attempts' results, and ends. It does not need to call `mcp__hilclaw__hypotheses_read` for such a delegation, does not call `mcp__hilclaw__verdicts_write`, and writes nothing. The sentence that names what is missing no longer says that no tool reads a round's `hypotheses.json`.
   - The rules listed for "when the verdicts work is given" may gain one line saying that the round's hypotheses are read with `mcp__hilclaw__hypotheses_read` (ADR-0129 decision 2). Nothing else of the definition changes. Each sentence cites its ADR as the file already does.
5. **Tests** in a new file `tests/test_hypotheses_tool.py`, using a temporary data root built by the test, with a valid hypothesis record written by `hypotheses_file` functions or as bytes. No `claude` is started, stub or real. The tests pass on Linux CI and on the local Windows machine. They cover at least:
   - happy: a valid round-1 record is returned whole under `record` and equals the parsed file; an unknown top-level member is returned as stored; the result has the single member `record`;
   - branch: the data-root source is not asked when the request is refused; a `round` above any round the run has is read without consulting `STATE.json` (no `STATE.json` exists in the fixture); the number-range choice of AC 2;
   - negative and error: each `invalid_request` form (extra member, missing `run_id`, missing `round`, bad `run_id`, `round` 0, a negative `round`, `round` above `keys.MAX_INTEGER`, a `bool`, a float, a string); `no_data_root`; `hypotheses_missing` (also when the data root is not an existing directory); `hypotheses_invalid` for a directory at the file's place, for invalid bytes, and for a file whose `round` (and, separately, whose `run_id`) differs from the request; `hypotheses_unsupported`; `hypotheses_unreadable` through a seam, not by changing permissions that Windows ignores; after every call no file or directory has been created under the data root;
   - registry: `hypotheses.read` is listed by `default_registry` and through the MCP front as `hypotheses_read`. The listing tests in the test files of `touchesFiles` are updated, and `tests/test_default_registry_schemas.py` gets an `ACCEPTED` entry that satisfies ADR-0077;
   - evaluator definition: `EVALUATOR_TOOLS` in `tests/test_turn_definition.py` includes `mcp__hilclaw__hypotheses_read`, and `test_the_evaluator_frontmatter` passes (every `mcp__hilclaw__` name is served by the default registry).
6. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases (invalid input, failure paths); ③ every public function of the new module and of each touched module that changes behaviour is tested; ④ the new module has its own test file; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
7. **No data-plane change**: no member, file, kind of event, value or version of `hypotheses.json`, `verdicts.json`, `STATE.json`, `instance.json`, `events.ndjson` or `artifacts.json` is added or changed, and no validator changes. The failure kinds are tool-layer names reused from `verdicts.write` (ADR-0129 decision 3). If the work turns out to need a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
8. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
9. Code mode (A-13): a Draft PR whose title contains `T-0356`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0356`, and the branch `claude/T-0356-hypotheses-read-tool` deleted.
10. No `claude` process is started, and nothing runtime-only is required (D16). Runtime acceptance item (xxi) of ADR-0129 (HQ-0046) is not closed by this task.

## Out of Scope

- Any edit of `ARCHITECTURE/` (no ADR, register row, proposal section or scenario note changes). The "less exact" ADR sentences listed in ADR-0129 Consequences (ADR-0128, ADR-0124) are not edited.
- The Round-Manager's use of the tool (`orchestration/round-manager.md` is not edited; ADR-0129 decision 4 leaves it to P2-1).
- The read of an attempt's journaled results, the standing and the comparison tools (ADR-0128 Consequences slice 3), and giving the verdicts work to the evaluator.
- Any change of `verdicts.write` behaviour, kinds or messages, of `hilclaw/hypotheses_file.py`, of the MCP front, or of the files of open PR #186 (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`).
- A bound on the size of a hypothesis record or a paged read (ADR-0129 item (xxi)).

## Follow-ups

- Next for the planner: the record for the read of an attempt's journaled results (ADR-0128 Consequences slice 3, ADR-0129 decision 5), which decides whether that read is enough to give the verdicts work to the evaluator.

## Result

- **DONE.** PR #204, squash-merged as 1644e7b; branch `claude/T-0356-hypotheses-read-tool` deleted. Review: 2 rounds, Approve (round-1 nit addressed: the file's path is computed once in `_read`). CI green on 845f391 (Python 3.11/3.14, coverage, test presence, sh, C gates).
- Module name as planned: `hilclaw/hypotheses_tool.py`; `touchesFiles` unchanged.
- Shared read (AC 2): the read moved into the new module as the public `hypotheses_tool.read(data_root, run_id, round)`; `verdicts_tool` calls it and its four `KIND_HYPOTHESES_*` constants are now those of `hypotheses_tool`. `verdicts.write` behaviour, kinds and messages are unchanged and `tests/test_verdicts_tool.py` passes unchanged. Moving rather than importing the private `_hypotheses` keeps ruff SLF001 clean.
- Number-range choice (AC 2): a number beyond the float range in an open top-level member is parsed as an infinity, so the call through the registry fails with `bad_result`, as `state.read` does; stated in the module docstring and tested (a large integer there is returned as stored).
- Language: Python, because the tool joins the Python registry and reuses `hypotheses_file`, `layout` and `data_root_source`.
- Local: ruff check/format clean; `coverage run -m pytest`: 24175 passed, 724 skipped; `hilclaw/` 97 %, `hypotheses_tool.py` 100 %.
- No data-plane change; no `claude` started; runtime acceptance item (xxi) of ADR-0129 (HQ-0046) not closed.
- Follow-ups: none beyond the task's own (the results-read record).
