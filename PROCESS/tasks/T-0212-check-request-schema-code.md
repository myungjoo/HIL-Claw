---
id: T-0212
title: Refuse a correctness.check request member no record names in moment 1 and state the tool's input schema and description (ADR-0069)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0211]
touchesFiles:
  - hilclaw/check_identity.py
  - hilclaw/check_definition.py
  - hilclaw/check_tool.py
  - tests/test_check_identity.py
  - tests/test_check_definition.py
  - tests/test_check_tool.py
estimatedSize: {loc: 170, files: 3}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts + mock backend) is open. ADR-0069 (landed by T-0211 as `bf4a795`) closed the member list of a request of `correctness.check` at the six members of ADR-0040 decision 5 (`run_id`, `round`, `candidate`, `attempt`, `execution`, `point`), decided that a request with any other member is refused as `invalid_request` in moment ① (before the data root is asked), fixed the input schema in full and fixed what the description must at least tell.

ADR-0069 Consequences names this slice: "the refusal of a member no record names in ① and the input schema and description of `correctness.check`, with tests for each row of the Walk-through. Whether it lives in `hilclaw/check_identity.py`, `hilclaw/check_tool.py` or a new module, and its names, are the code task's." No ADR is needed: every design point is fixed by ADR-0069 or left to the code by it.

This task does not depend on T-0210 (ADR-0068, BLOCKED on HQ-0021, unlanded): that record is about `sim.run` / `board.run` and touches only `ARCHITECTURE/` files; nothing here reads it.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention: branch `claude/T-0212-<slug>`, `Task: T-0212` trailer in commits and as the last line of the PR body, size cap, D12 test rules).
- `CLAUDE.md` sections "상시 규칙" — the test rule (D12 ①-⑤), the language policy (record the language choice and its reason in one line of the commit body), the branch/merge procedure (code mode: Draft PR, review cycle, CI green, self squash-merge, delete branch), the comment-minimisation rule, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- `ARCHITECTURE/decisions/ADR-0069-od18-correctness-check-request-schema.md` (150 lines): Decision §1 to §5 (lines 22-89), the Walk-through (lines 90-104), Limits (lines 105-111) and Consequences (lines 126-134: the code-slice bullet and the docstring sentences of `check_tool.py` / `check_identity.py` that become less exact).
- `PROCESS/tasks/T-0211-od18-correctness-check-request-schema.md` section "Follow-ups (from the executor)" (the reviewer note on echoing caller-supplied member names: length bound and control characters).
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md` decisions 4, 5 and 7 (the forms of the six members; moment ①).
- `ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md` decision 3 (the manner: refusal of other members, stated schema, the reduction rule).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decision 2 (tool definition; "a statement to the caller, not a check of the frame"; "the stated schema admits every request the tool function accepts").
- `hilclaw/check_identity.py` (whole; `check`, `step_of`, `_step`, message style, the "does not close the member list" sentences).
- `hilclaw/check_tool.py` (whole; the module docstring paragraph "What the module does not do", which says the member list is open and the function has no schema and no description).
- `hilclaw/journaled_tool.py` lines 297-344 (`_function`: the frame check `_checked`, then `check(request)`, then `step_of`, then the data root — i.e. where moment ① ends).
- `hilclaw/blob_tools.py` (whole; the analogue: `_checked` refusing other members, `_input_schema()`, the description texts).
- `hilclaw/tools.py` lines 1-20 and 99-140 (`ToolDefinition`, `Registry.register` and what it requires of a description and a schema).
- `hilclaw/keys.py` line 30 (`MAX_INTEGER`) and `hilclaw/layout.py` `check_run_id` (the `run_id` form).
- `tests/test_check_identity.py` (whole) and `tests/test_check_tool.py` lines 1-130 (fixtures, `REQUEST`, the request helper) — skim the rest for tests that rely on an open member list.

## Acceptance Criteria

1. **Language**: Python, as the other `check_*` modules. Record it and the reason in one line of the commit body and in `## Result`.
2. **The closed member list.** A public tuple of the six member names of ADR-0040 decision 5 (name is the executor's, e.g. `check_identity.MEMBERS`), in a fixed documented order.
3. **Refusal of a member no record names, in moment ①** (ADR-0069 decision 3), placed in `hilclaw/check_identity.check` (or a function it calls) so that it runs through the existing `check` hook of `hw_tool.stepped_tool_function`, i.e. after the frame check and before the data root is asked:
   - A request with any top-level key that is not exactly one of the six names (compared as it is, case-sensitive; a key that is not exactly a `str`, a `str` subclass included, is such a key) raises `hilclaw.tools.ToolFailure` of kind `invalid_request`, for every value, `null` included — among them `draws`, `seed`, `tolerance`, `m`, `k`, `n`, `shape`, `op_signature`, `step`, `hw_profile`, `data_root`, `Point`, `run-id`.
   - No code of a key or of a value is called (no hashing, comparison, `repr` or `str` of a non-`str` key; the existing hostile-key/value discipline of `check_identity` is kept). The request is not modified.
   - **The message** is the module's own text: it shows nothing of the value of a refused member (not the value, not its type). It may name the refused members by the names the request gave and the six members the tool takes; if it echoes caller-supplied names, it bounds its total length (state the bound in the docstring; at most 200 characters is suggested) and shows no control character as is (e.g. escaped by `repr`, or names that are not printable ASCII replaced by a fixed placeholder). Not echoing the names at all is equally acceptable. Choose one, state it in the docstring.
   - Which fault is named when a request has several (e.g. `point` missing and `Point` present) is the module's own and is documented; the kind is `invalid_request` in every case.
   - `step_of` keeps its documented invariant: for every request `check` refuses, it raises the same `ToolFailure` (same kind and message).
   - The existing refusals of `point` and their messages are unchanged; the frame's messages are not changed.
4. **The input schema** (ADR-0069 decision 4), exposed by a public function or constant (name and module are the executor's — a new module `hilclaw/check_definition.py`, or `check_identity.py`; keep `touchesFiles` and the PR in sync). It equals, as a Python value, exactly the JSON object of ADR-0069 decision 4: `type` object; `properties` with `run_id` (`string`, `pattern` `^[a-z0-9][a-z0-9_-]{0,63}$`), `round` (`integer`, `minimum` 0, `maximum` 9007199254740991), `candidate`, `attempt`, `execution` (`integer`, `minimum` 1, `maximum` 9007199254740991), `point` (`string`, `enum` `["sim", "board"]`); `required` all six; `additionalProperties` false. The maximum is taken from `hilclaw.keys.MAX_INTEGER`, the `enum` from `check_identity.SIM`/`BOARD`, the required list from the member tuple of criterion 2. A caller that mutates a returned schema does not change the next one (return a fresh object or a deep-frozen copy).
5. **The description** (ADR-0069 decision 5): a non-blank `str` constant whose text tells at least (i) a call checks the kernel of the one attempt the request names at the execution point `point` states; (ii) the tool is journaled — a call with the identity of an ended check gets the stored outcome and makes no new check, a call with the identity of an open one gets `step_open`, and a new check of the same attempt at the same point needs a higher `execution`; (iii) the request has exactly the six members and any other member is refused; (iv) what the function refuses beyond the schema: a number of the six written with a fraction or an exponent (`1.0`, `1e0`). It names no rule of who may raise `execution` or when, and states no tolerance, number of draws, dimension or setting as a value.
6. **No registration**: nothing is added to `hilclaw.tools.default_registry` or a front; no `ToolDefinition` of `correctness.check` is built in library code (a test may build one in a fresh `tools.Registry()` to show the description and schema are accepted).
7. **Docstrings now less exact** (ADR-0069 Consequences): update the sentences in `hilclaw/check_identity.py` ("It does not close the member list of a request and says nothing of a member no record names", and "the member list of a request is open (ADR-0040 decision 5)" in `check`) and in `hilclaw/check_tool.py` ("The member list of a request is open (ADR-0040 decision 5) ... it has no input schema and no description, looks at no member but `point` and the four ..., and hands the request on as the caller gave it") so that they cite ADR-0069 and say where the schema and description live; the tool function is still not registered (backend, seed source and "covered" are unbound). No code change in `check_tool.py`.
8. **Tests** (D12 ②-④): update `tests/test_check_identity.py` (the tests that assumed an open list, e.g. `test_no_other_member_is_looked_at`, become tests of the refusal) and add a test file for any new module; extend `tests/test_check_tool.py` where an end-to-end refusal is shown. Cover at least:
   - happy: the six-member request of the ADR-0069 Walk-through passes `check` for `sim` and `board`, and the tool function built over the mock reaches its usual result (existing tests stay green).
   - Walk-through rows as a table, through the tool function of `check_tool` with a recording data-root source: `draws`, `seed`, `tolerance`, `m` added → `invalid_request`, the source never asked, nothing read, no line appended, `seeds` and `covers` not called; `Point` in place of `point` → `invalid_request`; `"execution": 1.0` → `invalid_request`; `"point": "Sim"` → `invalid_request`; the request sent again after an ended call → the stored result; the same with `draws` added after the ended call → `invalid_request`, not the stored result.
   - branch/negative: every value of an unnamed member (`None`, a number, a list, a hostile object whose `__eq__`/`__hash__`/`__repr__`/`__str__` raise) refused without calling its code; a non-`str` key and a `str`-subclass key refused without calling its code; the message contains none of the refused values and, if names are echoed, respects the bound and shows no raw control character for a long name and for a name with `\n`/`\x00`; `step_of` raises the same failure as `check` for each refused request; the request is not modified.
   - schema: equals the literal of ADR-0069 decision 4 (written out in the test); its `required` equals the member tuple; `Registry().register("correctness.check", <a stub function>, DESCRIPTION, schema)` accepts it; mutating a returned schema leaves the next one unchanged.
   - description: non-blank, mentions each of the six member names and `execution`, `step_open`, and the fraction/exponent refusal (assert on the member names and those two terms only, not on prose).
   - each touched module: all public names tested; the module imports exactly what its docstring names; its public names are exactly the documented ones; no file written by `check` (`tmp_path` + `monkeypatch.chdir`).
9. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally; the coverage gate of `hilclaw/` (line >= 80%, function >= 80%) holds; the test-existence check finds a test file for any new module; CI green on the PR.
10. Size: non-test change <= 300 LOC and <= 5 files (expected about 170 LOC, mostly docstrings and the description). If exceeded, split per DRIVER §5 and record the split in Follow-ups.
11. No data-plane schema change: no member of a result, a line of `events.ndjson`, `STATE.json`, `instance.json`, a spec or a result file is added, removed or changed; no new `error.kind`, no new request member, no new `step` value. No new dependency (no `jsonschema`; the schema is compared as a literal). If the design seems to need one, stop and return BLOCKED.
12. Nothing in this task starts `claude`, builds or runs a kernel, starts a compiler, or needs a board or an API key (D16).
13. Code mode per CLAUDE.md A-13: branch `claude/T-0212-check-request-schema-code`, Draft PR whose title contains `T-0212` and whose body ends with `Task: T-0212`, fresh-context reviewer cycle (dev-code-review), CI green, `gh pr merge --squash --body <PR body>`, branch deleted. Fill `## Result` with the commit/PR, review rounds, the language line and any follow-ups.

## Out of Scope

- The registration of `correctness.check`, the binding of a backend, a source of seeds and the predicate "covered"; any change to `hilclaw/tools.py`, `hilclaw/mcp_front.py`, `hilclaw/journaled_tool.py`, `hilclaw/hw_tool.py`, `hilclaw/blob_tools.py` or the frame's messages.
- The requests, schemas and descriptions of `sim.run`, `board.run`, `profiler.collect` (ADR-0062 decision 4; OD-18 ⑲ and T-0210's ADR-0068).
- OD-18 sub-questions ⑤ (whether Claude Code accepts the schema keywords; nothing here verifies it — a runtime acceptance matter) and ⑱; the spend; who may raise `execution`.
- Any `ARCHITECTURE/` edit, including the "Not edited and now less exact" list of ADR-0069 Consequences and the T-0211 round-7 nit on ADR-0069 decision 1 (integrator follow-ups).
- Any new dependency.

## Follow-ups

## Result

- **DONE.** PR #142, squash-merged as `5ed027b` (branch deleted). Review: 3 rounds by a context-isolated `dev-reviewer`, final verdict Approve with no findings (round 1: three nits, round 2: one nit, all addressed). CI green on head `99cc2e9` (Python 3.11/3.14, coverage, sh, C, test presence).
- Language: Python, as the other `check_*` modules of the layer-2 package.
- Changes: `hilclaw/check_identity.py` (`MEMBERS`; refusal of a member no record names in moment 1, before `point`; message shows the given name only if 1-32 chars of `[A-Za-z0-9_.-]`, else `(a name not shown)`, at most 160 chars, no value), new `hilclaw/check_definition.py` (`input_schema()`, `DESCRIPTION`), `hilclaw/check_tool.py` (docstring only); tests in `tests/test_check_identity.py`, new `tests/test_check_definition.py`, `tests/test_check_tool.py`. Non-test change about 184 added lines in 3 files.
- Local: ruff check/format clean; full pytest 20667 passed, 354 skipped; coverage of the touched modules 100%, `hilclaw/` total 99%.
- Follow-ups: none.
