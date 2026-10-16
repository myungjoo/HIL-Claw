# ADR-0077: What checks that the stated input schema of a tool and the check of its tool function agree — a test over every tool of the default registry (the first half of OD-18 sub-question ⑤)

## Status

- **Accepted on 2026-10-16** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Two kinds of content.** No sentence of the owner is used as a decision of this record. What a requirement or an accepted record says is **cited** with its source; statements about code were read at `ad665f0` and are **observations**, binding no module or function. **Everything else is this record's own design**: the scope of the check, where it lives, the directions it covers, the source of its accepted requests, the named keyword set and what an unreadable schema leads to.
- Answers **the first half of OD-18 sub-question ⑤** (Open Decisions register in [Requirements](../Requirements.md)): "Whether anything checks that the stated schema of a tool and the check of its function agree". **The second half stays open** — "what Claude Code does with an `inputSchema` (F14)" (decision 6). No new sub-question is registered. The register row of OD-18 keeps its status.
- **No tool's request, result, schema, description or failure kind changes, no `schema_version` changes, and no file of the data plane is touched.** It is a record, not code; nothing was built, and no `claude` process was started (D16).
- It builds on [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2, 3 and 6), [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 2 to 4), [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decision 3), [ADR-0069](ADR-0069-od18-correctness-check-request-schema.md) (decisions 4 and 5) and [ADR-0070](ADR-0070-od18-correctness-check-registration.md) (decision 5). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The rule.** ADR-0015 decision 2: "The schema is a statement to the caller, not a check of the frame: no part of the package validates a request against it. The tool function checks its own request … What ties the two: the stated schema admits every request the tool function accepts, and what the function refuses beyond what the schema says is told in the description." Its Why rejects a check against the schema in the package: a full validator is a new dependency, and "a subset the package implements itself would be a schema dialect of its own to maintain, and it could not express what a request must satisfy anyway … so every tool function would check its request a second time and the two checks could disagree" (cited). It refuses a request "before it asks for the data root" (cited), and a failing data-root source is the tool failure `no_data_root` (cited: decision 3).
- **Sub-question ⑤** (ADR-0015 Boundaries, cited): "Whether anything checks that the stated schema of a tool and the check of its function agree, and what Claude Code does with an `inputSchema` (F14)". F14, whether Claude Code checks arguments against `inputSchema` and which keywords it accepts, is "not verified" (cited). ADR-0039 decision 3 and ADR-0069 decision 4 each stated a schema and left ⑤ open by name; both take the reduction rule "if one of these is not accepted, the schema is reduced and the description says what the function refuses beyond it" (cited).
- **Observations.** `default_registry(data_root_source)` registers `blob.fetch`, `blob.push` and `correctness.check`, each bound to the source it is given, and a tool is added "here, in the source, and in no other way" (`hilclaw/tools.py`). `Registry.register` checks of a schema only that it is a strict JSON object whose `type` is `"object"` (`tests/test_tools.py::test_register_checks_nothing_of_a_schema_but_its_type`). The three schemas use the keywords `type`, `properties`, `required`, `additionalProperties`, `pattern`, `enum`, `minimum` and `maximum` (`hilclaw/blob_tools.py` `_input_schema`, `hilclaw/check_definition.py` `input_schema`). Refusals are tested tool by tool from requests each test chose (`tests/test_blob_tools.py::test_a_refused_request_asks_no_source_and_looks_at_nothing`, `tests/test_check_definition.py::test_a_request_the_record_refuses_is_invalid_request`); no test takes its requests from a stated schema. The package already holds one reader of a JSON Schema subset, `hilclaw/driver_state.py`, the validator of the development driver's `PROCESS/STATE.json` (a named exception of the test rule, CLAUDE.md): it reads `type`, `properties`, `required`, `additionalProperties`, `items`, `enum`, `const`, `pattern`, `format` and `minimum` with four annotations, fails on any other keyword, and reads `$` the ECMA-262 way; it has no `maximum` and no `boolean` or `number` type, and the runtime modules `hilclaw/instance.py` and `hilclaw/run_state.py` state that they are not it. Two `sim.run` / `board.run` tools are to follow (ADR-0061 to ADR-0067).
- Fixed and not re-decided: ADR-0015 decision 2 as it stands (decision 5 below), except its sentence "which keywords a schema may use is not fixed (F14)", which decision 4 narrows for the schemas of the default registry; FR-10, the standard library only (a new dependency is the owner's — CLAUDE.md A-13), and D16.

## Decision

### 1. Terms

- **Accepted** request of a tool: one its tool function does not refuse — through the call the fronts use, the outcome is not the tool failure `invalid_request`. **Admitted** request: one the stated schema admits, read as JSON Schema draft 2020-12 reads it (the schemas name no `$schema`); where drafts differ — whether `integer` admits `1.0`, for one — the test relies on neither reading.
- The rule of ADR-0015 decision 2 has **two directions**. **(A) Containment**: every accepted request is admitted; equivalently, every request the schema refuses is refused as `invalid_request`. **(B) Telling**: an admitted request the function refuses is told in the description. The two are not one rule read twice: (A) forbids a schema narrower than the function, (B) governs a schema wider than it.

### 2. Where: one check in the package's tests, over every tool of the default registry

- **The agreement is checked by one test of the package's test suite, and nowhere else.** No part of the package reads a schema to answer a request; `Registry.register` and both fronts stay as they are.
- **The test covers every name `default_registry` registers**, enumerated from the registry and not listed in the test. It carries no test code per tool; its only per-tool content is data (decision 3).
- **How acceptance is seen without the data plane.** The test builds the default registry bound to a data-root source that fails and counts its calls. Because a refusal comes before the source is asked and a failing source is `no_data_root` (cited: ADR-0015 decisions 2 and 3), a request the function accepts ends in `no_data_root` with the source asked, and a refused one ends in `invalid_request` with the source not asked. Nothing is read from or written to any data plane.
- Why in the tests: a test runs at every change and at no call of a caller; its reader of a schema never stands between a caller and a tool function (decision 5). Why not elsewhere: Alternatives.

### 3. What it checks: direction (A), at the requests derived from one accepted request per tool

- **Each tool of the default registry has one accepted request, held as data by the test**, keyed by tool name. A registered tool without one, or an entry naming no registered tool, fails the test. So a tool added later to `default_registry` is covered when it is added: the change that registers it cannot pass the tests without its accepted request.
- **The accepted request itself**: the schema admits it, and through the failing source it ends in `no_data_root` with the source asked once. This sees a schema narrower than its function at that request.
- **Requests derived from it that the schema refuses**, one change at a time, by keyword occurrence: a required member left out; with `additionalProperties` false, a member added whose name is no property; for a property, a value of each JSON type its `type` does not admit (a number with a fraction for `integer`); a value not in its `enum`; one below its `minimum`, one above its `maximum`; a string its `pattern` does not match. A property absent from the accepted request is given such a value as an added member. Each derived request must end in `invalid_request` with the source not asked.
- **Every assertion of the schema can refuse alone** (JSON Schema keywords of the named set are conjunctive), so a derived request that violates one keyword is refused whatever the others say. The test still confirms each derived request is refused by its own reading of the schema, and **never counts a request as admitted or refused on a reading it cannot vouch for**: a candidate it is unsure of is not used, and an occurrence of a keyword the rules above derive from — the top-level `required` naming at least one member and `additionalProperties` false, and each property's `type`, `enum`, `minimum`, `maximum` and `pattern` — that yields no sure refused request fails the test, as an unreadable keyword does (decision 4). The top-level `type` (`"object"`, which `Registry.register` already requires of a schema, and a request is an object) and `properties` itself are structural and derive none, nor do `additionalProperties` other than false and an empty `required`. Any other occurrence that refuses no value — a `type` listing every JSON type, a `pattern` every string matches — fails the test on purpose: it states nothing to the caller, and the rule above does not set it apart from one the test cannot vouch for. Types are JSON's, not Python's: a boolean is no integer.
- **Direction (B) is not checked by the test.** Whether a description tells what lies beyond its schema is a reading of prose; it is held where it is today — by each tool's record, which states what lies beyond its schema (as ADR-0069 decision 4 does, cited), and by the review of the change that writes the text. The test may observe admitted requests a function refuses, but it does not judge the description.

### 4. The keyword set, and a schema the check cannot read

- **A schema of a tool of the default registry uses only the keywords the check reads.** This narrows, for those schemas, the sentence of ADR-0015 decision 2 "which keywords a schema may use is not fixed (F14)"; what Claude Code accepts stays open (decision 6). The set is today's eight: `type`, `properties`, `required`, `additionalProperties`, `pattern`, `enum`, `minimum`, `maximum`, read only in the positions of decision 3 — `type`, `properties`, `required` and `additionalProperties` at the top level, and `type`, `enum`, `minimum`, `maximum` and `pattern` in a subschema of `properties`. A keyword of the set in any other position — `enum` at the top level, `properties`, `required` or `additionalProperties` inside a property's subschema, any deeper subschema — is unreadable as well.
- **A schema with any other keyword fails the test for that tool**, naming the keyword. The registry still holds such a schema (`Registry.register` unchanged); the failure is a failing test, so the change that brought the keyword does not land (CLAUDE.md A-13: tests or CI green before merge).
- **The set grows only together with the check's reading of the keyword, in the same change**, and the record of the tool that first uses it names it (as ADR-0069 decision 4 named `minimum`, `maximum` and `enum`). The reduction rule of ADR-0039 decision 3 only removes keywords, so a reduced schema stays within the set and is checked alike.
- Why fail rather than ignore: an unread keyword can refuse (`minLength`, for one), and a check that ignored it would call a request admitted that the schema refuses.
- `pattern` is read as JSON Schema reads it (an ECMA-262 regular expression, not anchored by itself). Where the standard library's `re` could read a pattern otherwise — `$` before a final newline, for one — the test does not rely on that reading (decision 3).

### 5. Relation to the Why of ADR-0015 decision 2: kept

- **It stands.** Nothing in the package validates a request against a schema, and the tool function stays the only check of a request and authoritative.
- **Why the test's reader of the schema is not what that Why rejected.** The objection "the two checks could disagree" is about two checks of one request, each able to answer a caller; here only the function answers, and a disagreement is what the test exists to report. The objection "a schema dialect of its own to maintain" holds in part: the reader is a subset of JSON Schema maintained in the tests, and with the driver's validator (Context) the repository then holds two such readers, of different sets for different purposes. Its cost is bounded by the named set (decision 4), and an error in it can fail or pass a test but never changes an answer to a caller. The objection to a full validator stands too: it is a new external dependency, test-only or not, and is not chosen.

### 6. The second half of sub-question ⑤ stays open

- **What Claude Code does with an `inputSchema`** — whether it checks the arguments of an MCP call against it before sending, and which keywords it accepts (F14) — **is not established by this record and not tried.** Only a live Claude Code session can show it: it is a runtime acceptance item (CLAUDE.md "개발 드라이버와 런타임의 구분", DRIVER D16), closed by the owner by hand or by the runtime's own self-check, not by a driver task.
- Nothing decided here depends on it. If Claude Code refuses a keyword of the set, the reduction rule of ADR-0039 decision 3 applies as it stands, and the test checks the reduced schema.

### Walk-through

The failing source as in decision 2. "The example" is the accepted request of `correctness.check`, `{"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1, "point": "sim"}` (ADR-0069 Walk-through, cited).

| Request | The test's reading of the schema | Required outcome |
|---|---|---|
| The example | admits | `no_data_root`, source asked once |
| Without `point` (`required`) | refuses | `invalid_request`, source not asked |
| With an added `draws` (`additionalProperties`) | refuses | the same |
| `"round": -1` (`minimum`), `"execution": 9007199254740992` (`maximum`) | refuses | the same |
| `"round": true`, `"round": 0.5`, `"round": "3"` (`type`) | refuses | the same |
| `"point": "simboardx"` (`enum`) | refuses | the same |
| `"run_id": "R1"` (`pattern`) | refuses | the same |
| `"run_id": "r10"` | admits — not used as a derived request | none |
| `"execution": 1.0` | not relied on (admitted from draft 6 on, refused by draft 4) | not checked: a refusal beyond the schema, direction (B) |
| A schema with `minLength` | cannot read | the test fails for the tool |
| A tool added to `default_registry` without an accepted request | — | the test fails |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Nothing checks it beyond each tool's own tests (today's state) | Their requests are chosen by each test's author, not taken from the stated schema: a schema edited without its function, or reduced, is not seen, and a tool registered later is held to the rule only if its author writes such tests. |
| 2 | At registration: `Registry.register` refuses a keyword outside the set, or calls the function with derived requests | It puts a schema dialect into the package, which the Why of ADR-0015 decision 2 keeps out; it runs tool code at the start of every front process, and a failure would stop a server from listing any tool; it changes a landed function that test registries use with arbitrary keywords. The tools it would see are the same the test sees. |
| 2 | The test reads the schemas with the driver's validator `hilclaw/driver_state.py`, extended by `maximum` and the missing types | It ties the runtime's tool contract to the program that builds it — the driver and the runtime are different programs (D16), and the runtime modules keep apart from that validator (Context). Its set and its mandated tests are those of `PROCESS/STATE.json`: it raises `SchemaError` on `maximum`, which today's schemas use; it reads `integer` as a Python `int` and so refuses `1.0`, a reading decision 1 does not rely on; and it has no notion of a reading it cannot vouch for (decision 3). |
| 2 | A full JSON Schema validator, in the tests only | A new external dependency: the owner's (CLAUDE.md A-13). |
| 3 | Derive refused requests from the schema alone, without an accepted request | Each would be refused for several reasons at once; a function that refuses everything passes, and a schema narrower than its function is never seen. |
| 3 | Generate the accepted request from the schema | A string matching any `pattern` needs a generator of regular expressions — a larger dialect than the reader. |
| 3 | Carry the accepted request in the schema (`examples`) or in the tool definition | It changes each tool's schema or the tool definition, and whether Claude Code accepts `examples` is as unverified as the rest (F14). |
| 3 | Check (B) by matching the description for words | Prose is not matched reliably, and the text is each code task's. |
| 4 | Ignore a keyword the check cannot read | A refusing keyword would go unseen, and the test would call refused requests admitted. |
| 4 | Fix no keyword set | The test could not say what it read; see decision 4. |

## Consequences

- **The code slice the planner can cut** (one task, code mode, tests only; no module of `hilclaw/` changes): a test module that builds `default_registry` bound to a failing, counting source; holds one accepted request per tool; reads the eight keywords; derives the refused requests of decision 3 and asserts the outcomes; and fails on an unreadable keyword, a missing or stale accepted request, or an occurrence decision 3 derives from that yields no sure refused request. Its names, its layout and its candidate values are the code task's. A throwaway script run during this task at `ad665f0`, not kept — each tool's accepted request through a failing source, and requests derived by the rules of decision 3 with hand-picked `pattern` candidates — found the three registered tools in agreement at those requests (observation, not a test).
- **Later tool registrations** (`sim.run`, `board.run`, T-0210 and after) add one accepted request to the test's data in the change that registers them.
- **Not edited and now less exact**: ADR-0015 decision 2, the sentence "which keywords a schema may use is not fixed (F14)": narrowed by decision 4 for the schemas of the default registry; it holds for what Claude Code accepts. ADR-0069 decision 4 ("nothing here checks that the schema and the function agree") holds for that record. ADR-0015 decision 7, Limits ("a tool function … that accepts what its schema excludes … is not detected by the frame"): once the test of decision 2 lands, it is detected for the tools of the default registry at the requests derived from each accepted request (decision 3); elsewhere it stays undetected.
- **A-13 reading**: document mode; no code, test, dependency, settings file or schema file changes, and no data-plane file is named.

## Boundaries (not decided here)

- **The second half of sub-question ⑤**: what Claude Code does with an `inputSchema` (decision 6); whether and how it is notified as a runtime acceptance item, or folded into the runtime self-check ([ADR-0054](ADR-0054-od18-runtime-self-check.md), [ADR-0057](ADR-0057-od18-runtime-self-check-as-landed.md)), is the driver's.
- **A tool that needs no data plane**: none is registered. For one, an accepted request would run its step in the test; how its acceptance is seen without effects is decided with that tool.
- Registries built by tests, and tools outside `default_registry`.
- What a tool refuses after the data root is asked (`run_file_*` kinds, `step_open` and the rest): no refusal, no schema matter (cited: ADR-0069 decision 4).
- Any tool's request, schema or description; the hooks of PLAN P2-4; the rest of OD-18.

## References

- [Requirements](../Requirements.md): FR-10; register row OD-18. [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-question ⑤). [StandardScenarios](../StandardScenarios.md).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 2 to 4); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (F14, decisions 2, 3, 6 and 7, Boundaries); [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decision 3); [ADR-0069](ADR-0069-od18-correctness-check-request-schema.md) (decisions 4 and 5, Walk-through); [ADR-0070](ADR-0070-od18-correctness-check-registration.md) (decision 5); ADR-0054, ADR-0057; ADR-0061 to ADR-0067.
- #5 D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 ; [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9, D16; CLAUDE.md A-13.
- `hilclaw/tools.py` (module docstring, `Registry.register`, `default_registry`), `hilclaw/blob_tools.py`, `hilclaw/check_definition.py`; `tests/test_tools.py`, `tests/test_blob_tools.py`, `tests/test_check_definition.py`; task T-0240.
