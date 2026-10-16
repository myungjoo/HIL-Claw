---
id: T-0241
title: Add the package test of ADR-0077 that checks, for every tool of `default_registry`, that each request derived from one accepted request and refused by the stated input schema is refused by the tool function as `invalid_request`; tests only, no module of `hilclaw/` changes
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, "#5 D12"]
dependsOn: [T-0240]
touchesFiles: [tests/test_default_registry_schemas.py]
estimatedSize: {loc: 250, files: 1}   # all of it is test code, outside the cap (DRIVER §5, D4)
hq: []
---
## Why

ADR-0077 (landed as `43e10d7` by T-0240, accepted under DRIVER §9, owner window until 2026-10-23) answers the first half of OD-18 sub-question 5: the agreement between a tool's stated input schema and its tool function's own check is checked by **one test of the package's test suite, over every tool `default_registry` registers**, and nowhere else (decision 2). Its Consequences name the code slice this task is: "a test module that builds `default_registry` bound to a failing, counting source; holds one accepted request per tool; reads the eight keywords; derives the refused requests of decision 3 and asserts the outcomes; and fails on an unreadable keyword, a missing or stale accepted request, or an occurrence decision 3 derives from that yields no sure refused request. Its names, its layout and its candidate values are the code task's." It advances PLAN P1-1 and ticks **no PLAN checkbox**.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-17 at `2e4e524`). The BLOCKED tasks T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024) and T-0239 (HQ-0025) are not needed by this task, and none of their branches touches `tests/` files this task creates. When T-0210's later code slice registers `sim.run` / `board.run`, that change adds their accepted requests to this test's data (ADR-0077 Consequences) - not this task. Do not read or depend on any of those branches.

**D16.** Nothing here starts `claude`, needs a board, an accelerator or an API key. The second half of sub-question 5 (what Claude Code does with an `inputSchema`, F14) is a runtime acceptance item and is **not** touched (ADR-0077 decision 6).

## Required Reading

Line numbers are those of `main` at `2e4e524`; the text wins. Read Korean files and Python with `PYTHONIOENCODING=utf-8` (the console code page is cp949).

- **PROCESS/DRIVER.md §3-5** (executor procedure, landed check, resume rule, time limit) and **§5** (task format, naming, size cap D4, trailers, the test rules D12 - note rule 5).
- CLAUDE.md, the whole file; above all "테스트 규칙" (rule 5: no tests of test code), "브랜치·merge 절차" (code mode), "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode, all steps); .claude/skills/dev-code-review/SKILL.md.
- **ARCHITECTURE/decisions/ADR-0077-od18-schema-function-agreement-check.md, the whole record** (113 lines): decision 1 (lines 22-25, terms, draft 2020-12 reading), decision 2 (27-32, where; the failing counting source), decision 3 (34-40, the accepted request per tool, the derivation rules, "never counts a request as admitted or refused on a reading it cannot vouch for", which occurrences derive and which fail), decision 4 (42-48, the eight keywords and their allowed positions, `pattern` read the ECMA-262 way), Walk-through (60-76, the expected outcomes), Consequences (93-98).
- ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md decisions 2 and 3 (lines 39-66): refusal before the data root is asked; a failing source is `no_data_root`.
- ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md decision 4 (lines 63-84) and Walk-through (91-105); ADR-0039-od18-blob-push-fetch-local.md decision 3 (lines 36-42).
- `hilclaw/tools.py` lines 108-208 (`Registry`, `names`, `definition`, `default_registry`) and 284-310 (`call`) - read only.
- `hilclaw/data_root_source.py` lines 28-80 (`obtain`: a source that raises gives `no_data_root`) - read only.
- `hilclaw/blob_tools.py` lines 50-120 (`definitions`, `_input_schema`, `_checked`) and `hilclaw/check_definition.py` lines 82-150 (`input_schema`, `definition`) - read only.
- Test patterns to follow, not to import from: `tests/test_tools.py` lines 488-512 (`CountingSource`, `DEFAULT_SET`), `tests/test_blob_tools.py` lines 329-353, `tests/test_check_definition.py` lines 42-60 and 196-216 (`REQUEST`) and 464-467.

## Acceptance Criteria

Scope and files:
1. **Exactly one new file, `tests/test_default_registry_schemas.py`**; the module name and every name in it are yours if you have a better one (state it in `## Result`). **No file under `hilclaw/` is edited, and no existing test file is edited** - none needs to be: the only tests that pin import sets or public names in this area (`tests/test_gemm_contract.py::test_module_is_bound_by_the_default_registry_only_and_imports_keys_only`, which scans `hilclaw/*.py` only; `tests/test_check_definition.py::test_the_module_imports_what_it_names_and_has_its_public_names_only`; `tests/test_tools.py::test_default_registry_holds_the_fixed_set_and_is_not_shared`) are about modules this task does not change, and the CI "Test presence" job maps `hilclaw/` modules to tests and is unaffected by a test file with no module of its own. If you find that any other file must change, stop and report BLOCKED (`requirement-unclear`) rather than widen the scope.
2. Language: Python (the suite's); standard library and `pytest` only - **no new dependency**, no JSON Schema library (ADR-0077 decision 5, A-13). Its reader of the schema lives in this test file; it does **not** use `hilclaw/driver_state.py` (ADR-0077 Alternatives).

What the module does (ADR-0077 decisions 2-4):
3. **Coverage of the registry.** The tools are enumerated from `tools.default_registry(source).names()`, not listed in the test; the schema of each is read with `Registry.definition`. One mapping, tool name to one accepted request, is the only per-tool content (data, no per-tool test code). A test fails when a registered name has no entry, or an entry names no registered tool (both directions, with the names in the message).
4. **The source.** Each call goes through `tools.call` on a `default_registry` bound to a data-root source that raises (so `no_data_root`) and counts its calls. No file is read or written under any data root; no `tmp_path` data plane is built.
5. **Happy path - the accepted request.** For each tool: the test's own reading of the schema admits the accepted request, and the call ends in `ToolFailure` of kind `no_data_root` with the source asked exactly once.
6. **Negative cases - derived refused requests**, one change from the accepted request at a time (ADR-0077 decision 3), each required to end in `ToolFailure` of kind `invalid_request` with the source asked zero times:
   - each member named by the top-level `required` left out;
   - with top-level `additionalProperties` `false`, one added member whose name is no property;
   - for each property, a value of every JSON type its `type` does not admit (JSON types, not Python's: `True` is no integer; for `integer` the "number" candidate has a fraction, e.g. `0.5`, never `1.0`); a property absent from the accepted request gets such values as an added member;
   - a value not in its `enum`; a value below its `minimum` and one above its `maximum` (integers when the type is `integer`);
   - a string its `pattern` does not match, from a fixed list of candidate strings of your choice (ASCII, no line terminator, so Python `re.search` and ECMA-262 agree on them); the pattern is read unanchored, as JSON Schema reads it.
   The test checks with its own reading that each derived request is refused by the schema before using it; a candidate it cannot vouch for is dropped, never counted.
7. **Failure branches of the reader** (ADR-0077 decisions 3-4): the test fails, naming tool, keyword and position, when a schema has (a) a keyword outside the eight (`type`, `properties`, `required`, `additionalProperties`, `pattern`, `enum`, `minimum`, `maximum`), (b) one of the eight in a position decision 4 does not allow (e.g. `enum` at the top level, `required` inside a property's subschema, any deeper subschema), (c) a top-level non-empty `required` / `additionalProperties: false`, or a property's `type`, `enum`, `minimum`, `maximum` or `pattern`, that yields no sure refused request (including a `type` listing every JSON type, a `pattern` every candidate matches, or a `pattern` `re` cannot compile). Top-level `type: "object"`, `properties` itself, `additionalProperties` other than `false` and an empty `required` derive nothing and do not fail.
8. **Direction (B) is not checked**: no assertion about descriptions, and admitted requests a function refuses (e.g. `"execution": 1.0`) are neither used nor judged.
9. **Branch coverage of today's three tools** is visible in the parametrized test ids or messages: `blob.fetch` and `blob.push` (`required`, `additionalProperties`, `type` string, `pattern`) and `correctness.check` (adds `type` integer, `minimum`, `maximum`, `enum`). The ADR-0077 Walk-through rows for `correctness.check` are among the derived requests.

Rule-5 boundary and verification:
10. **No test of the test's own reader is added** (CLAUDE.md test rule 5; owner's global rule). Instead, before the PR, verify branches 3 and 7 by hand with throwaway local edits that are **not committed** - for example temporarily add `minLength` to one schema in `hilclaw/blob_tools.py`, drop an entry from the accepted-request mapping, and add `"enum"` at a schema's top level - and record in `## Result` each edit, that the test failed, and its message. Revert every edit (`git diff --stat` shows only the new test file).
11. The full suite passes locally (`python -m pytest`), `ruff check` and `ruff format --check` pass on the new file, and the coverage gate of `hilclaw/` is unchanged (no module changed). CI green before squash-merge.
12. Code mode (A-13): branch `claude/T-0241-<slug>`, Draft PR whose title contains `T-0241` and whose body ends with `Task: T-0241`; review cycle per dev-code-review; squash-merge with that body; delete the branch. The commit body gives the language choice in one line.
13. Comments minimal (CLAUDE.md): a short module docstring naming ADR-0077 decisions 2-4 and what the module does not do (direction B, F14, registries other than the default one); no multi-line comments.
14. `## Result` records: PR and squash commit, review rounds, the module/test names, the candidate `pattern` strings chosen, the throwaway checks of criterion 10, and any tool found in disagreement (if one is found, do not change the tool: report BLOCKED with the failing request, since ADR-0077's observation at `ad665f0` found the three tools in agreement).

## Out of Scope

- Any change to `hilclaw/` (registry, fronts, schemas, descriptions, tool functions), to `Registry.register`, or to any existing test.
- Checking descriptions (direction B), Claude Code's handling of `inputSchema` (F14, runtime acceptance item), registries built by tests, tools outside `default_registry`, refusals after the data root is asked.
- Any `ARCHITECTURE/` edit (ADR-0077 already records the decision; ADR-0015 decision 7 and ADR-0069 decision 4 are left as ADR-0077 Consequences says).
- `sim.run` / `board.run` accepted requests (their registration task adds them).

## Follow-ups

- When T-0210's code slices register `sim.run` / `board.run`, each adds its accepted request to this test's mapping in the same change (ADR-0077 Consequences).

## Result

- **DONE.** PR #154, squash-merged (the squash commit is the one on `main` with trailer `Task: T-0241`, subject "T-0241: test that each default-registry tool refuses what its input schema refuses (ADR-0077)"). Review: 3 rounds (1 Request changes: an `assert derived` would have failed a schema with no deriving occurrence, against ADR-0077 decision 3 - removed; round-1 nits: added member renamed `draws` to match the Walk-through, Python-only pattern syntax treated as unsure; round 2 Approve with a nit (`\z`, `{,n}`) addressed; round 3 Approve, no findings).
- **Module**: `tests/test_default_registry_schemas.py`. Tests: `test_every_registered_tool_has_an_accepted_request_and_no_other_entry`; `test_the_schema_is_read_and_each_occurrence_yields_a_refused_request[<tool>]`; `test_the_accepted_request_is_admitted_and_reaches_the_source[<tool>]`; `test_a_request_the_schema_refuses_is_invalid_request[<tool>: <keyword> <member>=<value>]` (93 derived requests over the three tools; 96 tests in the module). Data: `ACCEPTED` (the mapping), `CountingSource`; reader: `reading`, `_admits`, `_unreadable`. A candidate for `enum` / `minimum` / `maximum` / `pattern` is kept only when that keyword refuses it and the rest of its subschema surely admits it, so a vacuous occurrence (e.g. `minimum` on a string-only property) fails.
- **Pattern candidates**: `""`, `"R1"`, `"-"`, `"x y"`, `"G" * 64`, `"A" * 64`, `"0" * 65`. A pattern holding Python-only syntax (`(?P`, inline flags, `(?#`, `\A`, `\Z`, `\z`, `{,`) or a value with non-ASCII or CR/LF is not vouched for.
- **Walk-through rows of `correctness.check`** all derived: without `point`, added `draws`, `round=-1`, `execution=9007199254740992`, `round=True` / `0.5` / `'3'`, `point='simboardx'`, `run_id='R1'`; `run_id='r10'` and `execution=1.0` are not used.
- **Throwaway checks (criterion 10), none committed, all reverted (`git status` showed only the new test file):** `"minLength": 64` in the `sha256` subschema of `hilclaw/blob_tools.py` -> fails with `blob.fetch: keyword 'minLength' at properties.sha256 is not read` (and blob.push), plus `the schema of blob.fetch does not surely admit {...}`; top-level `"enum": [{}]` in `hilclaw/check_definition.py` `input_schema` -> `correctness.check: keyword 'enum' at the top level is in a position not read`; `blob.push` dropped from `ACCEPTED` -> `registered tools without an accepted request: ['blob.push']` and `blob.push has no accepted request`; a stale `"sim.run"` entry -> `accepted requests naming no registered tool: ['sim.run']`; `type` listing all seven JSON types -> `keyword 'type' at properties.sha256 yields no sure refused request`; pattern `""` -> `keyword 'pattern' ... yields no sure refused request`; pattern `"^[0-9a-f"` (re cannot compile) and `"(?i)^[0-9a-f]{64}$"` -> the same plus `does not surely admit`; `"required": []` inside the property -> `keyword 'required' at properties.sha256 is in a position not read`; `additionalProperties: {"type": "string"}` -> `keyword 'additionalProperties' at the top level is a deeper subschema, not read`; `"minimum": 1` on the string `sha256` -> `keyword 'minimum' at properties.sha256 yields no sure refused request`.
- **Disagreement found**: none; all three tools refuse every derived request as `invalid_request` without asking the source, and the accepted requests end in `no_data_root` with one ask.
- Local: `python -m pytest` 22113 passed, 355 skipped; `ruff check .` and `ruff format --check .` clean; no `hilclaw/` module changed, so the coverage gate is unchanged.
