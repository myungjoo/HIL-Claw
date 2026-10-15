# ADR-0069: The member list of a request of `correctness.check`, what the tool function does with a member no record names, and the tool's input schema and description (one more part of OD-18; a slice of the second record of that contract)

## Status

- **Accepted on 2026-10-16** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Whose content.** No sentence of the owner is used as a decision of this record. **Everything this record decides is its own design and has not been confirmed by the owner.**
- Closes **one more part of OD-18** (Open Decisions register in [Requirements](../Requirements.md)): the item [ADR-0040](ADR-0040-od18-correctness-check-call-identity.md) decision 5 left to a later slice — "Whether a request carries anything else …; so are the input schema and the description, and so is what the tool function does with a member that no record names" — which ADR-0041 to ADR-0048, ADR-0056 and ADR-0060 carry on as "the rest of the request". It answers **no registered sub-question** — sub-question ⑤ and part (가) of ⑱ stay open (decisions 2 and 5) — and registers none. The register row of OD-18 keeps its status wording.
- **It is not the whole contract of the tool, and the tool is not registered by it** (Consequences). It is a record, not code; nothing was built or run, and no compiler, kernel, container or `claude` process was started. Statements about code were read at `3d8fc45` and are observations.
- **No sentence of an earlier record is replaced.** Sentences that call these points open become less exact; Consequences lists those this record found. **No member of any data-plane file or record is added** (Consequences, A-13 reading).
- It builds on [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4), ADR-0040 (decisions 4, 5 and 7) and [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decision 3, for the manner), and on the records that gave each input a source outside the request: [ADR-0021](ADR-0021-od18-correctness-check-split.md) (decisions 3 and 4), [ADR-0041](ADR-0041-od18-correctness-check-dimensions.md) (decisions 2 and 6), [ADR-0046](ADR-0046-od18-correctness-check-draws.md) (decisions 2 and 6), [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decision 3) and [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decision 3). **If ADR-0015 or ADR-0040 is reverted, this record falls with it; if one of the others is reverted, decision 2 is revisited for the input it gave a source.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).
- **Edited after acceptance on 2026-10-16** by task T-0213 (document mode): decision 1 now takes the moments ① to ⑦ from ADR-0016 decision 2, which defines them, and `point` from ADR-0040, where it took both from ADR-0040; the ADR-0016 entry under References names decision 2 beside decision 4. What moment ① does in a call of this tool is still cited from ADR-0040 decision 7 as ADR-0048 decision 10 has it. No decision changed meaning, and the objection window of the notice on issue #5 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6199031235, until 2026-10-22) is unchanged.

## Context

- ADR-0040 decision 5 fixed six required members — `run_id`, `round`, `candidate`, `attempt`, `execution`, `point` — and left the rest open, naming the candidates: "for `draws`, the dimensions, the kernel of the attempt, flags or time limits". Its Alternatives rejected closing the list then, because "The members for `draws`, the dimensions and the kernel are a later slice's; a closed list would be reopened by it".
- Since then every one of those inputs was given a source that is no member of a request (decision 2). Nothing named in ADR-0040 decision 5 is left without a source.
- **What the code has today** (observations; no code is bound by this record). `hilclaw/check_tool.py` says of its function: "it has no input schema and no description, looks at no member but `point` and the four the output path is formed from, and hands the request on as the caller gave it". The frame check (`hilclaw/journaled_tool.py`) refuses a request whose `run_id`, `execution` or required numbers are missing or ill-formed, and an envelope number the tool does not take; it does not look at other members. `hilclaw/check_identity.py` checks `point` only. `hilclaw/blob_tools.py` refuses any member but `sha256` and states the schema of ADR-0039 decision 3. `hilclaw/tools.py` holds a tool definition with a non-blank description and a schema that is one JSON object, and `hilclaw/mcp_front.py` lists the schema as `inputSchema` unchanged.
- **Fixed and not re-decided.** FR-9, FR-10 and C-4 as they stand; [ADR-0001](ADR-0001-od4-key-schema.md) (*integer*), [ADR-0004](ADR-0004-od8-data-plane-layout.md) decision 8, [ADR-0006](ADR-0006-od8-events-log.md) decision 3, [ADR-0010](ADR-0010-od18-tool-exposure-form.md), [ADR-0011](ADR-0011-od17-journal-and-spend.md) decision 3, ADR-0015, ADR-0021, ADR-0040 to ADR-0048, ADR-0056 and ADR-0060 as they are.
- #5 A-4, B-2, B-3 and B-7 are unanswered. Nothing below needs them, and nothing below may be read as an answer to them.

## Decision

A sentence is **cited** when a record and its decision, or a requirement, is named with it; it then says what that source says and adds nothing. Every other sentence is **this record's own** — among them that the list is closed, the refusal of every other member, the schema and its keywords, the reading of *integer* in decision 4, what the description must tell, and every weighing.

### 1. Scope and terms

- This record is about **a request of `correctness.check` about one attempt of a run** that ADR-0040 decision 1 covers (a run of the first case, and a run whose hw_profile names the mock). It fixes four points: the member list (decision 2); what is done with a member no record names (decision 3); the input schema (decision 4); and what the description must tell (decision 5).
- The terms of ADR-0010 (request, tool failure, front), ADR-0015 (tool definition, reserved kind), [ADR-0016](ADR-0016-od18-backend-frame.md) (the moments ① to ⑦, decision 2) and ADR-0040 (`point`) are used unchanged. **A member no record names**: a top-level member of a request whose name is none of the six of ADR-0040 decision 5, compared as it is, case-sensitive.
- **It says nothing of the requests of other tools**: not of `sim.run` or `board.run` — whether a `point` in their request is refused "is what the tool function does with a member no record names" (cited: [ADR-0062](ADR-0062-od18-run-tools-call-identity.md) decision 4), and that stays theirs — and not of `blob.push` or `blob.fetch`, whose request ADR-0039 decision 3 closed.

### 2. The member list is closed at the six members of ADR-0040 decision 5

- **A request of this tool has exactly the six members `run_id`, `round`, `candidate`, `attempt`, `execution` and `point`, with the forms ADR-0040 decisions 4 and 5 gave them, and no other.**
- **Each input ADR-0040 decision 5 named has a source outside the request** (all cited):

| Input | Source | Record |
|---|---|---|
| The dimensions `m`, `k`, `n` | the `shape` of the op_signature `instance.json` states; "A request of this tool carries no member for the dimensions" | ADR-0041 decisions 2 and 6 |
| `draws` | the member `draws` of `instance.json`; "A request of this tool carries no member for the number of draws" | ADR-0046 decisions 2 and 6 |
| The kernel of the attempt | the output path the tool function forms from `run_id`, `round`, `candidate` and `attempt` and hands to the operation | ADR-0056 decision 3 |
| Flags, compiler, the two time limits, the environment | "Every setting is the backend's own"; an operation reads no setting "from the request" | ADR-0060 decision 3 |
| The seed | "The seed is not a member of a request" | ADR-0021 decision 3 |
| The tolerance | `instance.json`; "no value carried by a request stands in for it" | ADR-0021 decision 4 |

- Beside them, a backend "is not a member of a request" (cited: [ADR-0016](ADR-0016-od18-backend-frame.md) decision 4, which takes the hw_profile of a call from the run the request names), "The data root is never a member of a request" (cited: ADR-0015 decision 3), and "`step` is not a member of a request" (cited: ADR-0015 decision 4).
- **Why close it now.** ADR-0040 kept the list open only because the sources above were undecided; none is now, so an open list would wait on nothing. A closed list is what the input schema can state exactly (decision 4) and what a caller can be told in full. **Weighed against keeping it open**: an open list leaves decision 3 without an answer, and a schema with `"additionalProperties": true` would admit members the contract gives no meaning.
- **A later record that gives the request a member extends the list and the schema, and that is a change of this contract**, in the manner of ADR-0060 decision 3, which a later record "reopens" for a setting (cited: OD-18 sub-question ⑱ (가)). **This does not answer ⑱ (가)**: whether a setting written in a file of the run or of the attempt, or a member a later record gives the request, reaches the operation stays open. The record says only that no such member exists today.
- **What follows for the operation** (a consequence, not a rule): the request an operation is handed (cited: ADR-0056 decision 3, "the request, the hw_profile of the call, the check parameters and the output path") holds exactly the six members, since a request with another one never reaches ⑥ (decision 3).

### 3. A member no record names: refused as `invalid_request` in ①

- **A request with a member no record names is a refused request: the tool failure of the reserved kind `invalid_request`** (the kind and its meaning are cited: ADR-0015 decision 2). That holds for every such name — among them `draws`, `seed`, `tolerance`, `m`, `k`, `n`, `shape`, `op_signature`, `step`, `hw_profile`, `data_root`, a flag or a time limit, and a misspelling such as `Point` or `run-id` — and for every value it carries, `null` included.
- **The moment is ① of ADR-0040 decision 7, as ADR-0048 decision 10 now has it**: the answer of that row is "`invalid_request`; nothing asked, read, drawn or appended" (cited: ADR-0048 decision 10, row ①), and a tool function refuses "before it asks for the data root" (cited: ADR-0015 decision 2). That the refusal of this decision lies in ① with the check of the six members is this record's own. So such a request reads no `instance.json`, is not looked up, selects no backend, draws no seed, appends no line and consumes nothing; it is answered alike on every machine and for an ended or open identity alike. Which of several faults of one request the message names is the code task's; the kind is the same for all.
- **The message of this refusal.** It may name the members it refuses, by the names the request gave them, and the six members the tool takes. **It shows nothing of the value of a member it refuses** — not the value and not its type — in the manner of `hilclaw/check_identity.py` for `point` (observation). Its text is the code task's. The messages of the frame check of the six members are not changed by this record.
- **Three answers were weighed.**
  - **(a) Refuse** — the choice ADR-0039 decision 3 made for the blob tools ("a request with any other member", cited). A caller that believes it set something learns at once that it did not.
  - **(b) Ignore it.** A caller that sends `"draws": 1000` or `"tolerance": …` would be given a result checked on the run's own number and tolerance and could not tell; the result would be stored under the identity of the attempt and returned to every repeated call (cited: ADR-0011 decision 3). A misspelled `Point` would be ignored while `point` is missing, so (b) needs (a) for the six anyway.
  - **(c) Pass it on to the operation.** It opens the path from the calling agent to the check that ADR-0016 decision 4, ADR-0020 decision 5 and ADR-0021 decision 3 close for the hw_profile, the tolerance and the seed (all cited), and that ADR-0060 decision 3 closes for settings ("from the request", cited); a script of the mock, asked with the request (cited: ADR-0056 decision 3), would answer from members no record defines.
- **The choice is (a).**

### 4. The input schema

- The tool definition states this schema (cited: ADR-0015 decision 2 — "a statement to the caller, not a check of the frame"; "the stated schema admits every request the tool function accepts"):

```json
{"type": "object",
 "properties": {
  "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
  "round": {"type": "integer", "minimum": 0, "maximum": 9007199254740991},
  "candidate": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
  "attempt": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
  "execution": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
  "point": {"type": "string", "enum": ["sim", "board"]}},
 "required": ["run_id", "round", "candidate", "attempt", "execution", "point"],
 "additionalProperties": false}
```

- **Where each constraint comes from** (cited): `run_id` matches `[a-z0-9][a-z0-9_-]{0,63}` (ADR-0004 decision 8, as ADR-0015 decision 4 names it); `round` is an *integer* (`0` = bring-up), `candidate` and `attempt` are *integers* ≥ 1 (ADR-0006 decision 3); `execution` is an *integer* ≥ 1 (ADR-0011 decision 3); an *integer* "is in the range 0 to 2^53 - 1" (ADR-0001 decision 1); `point` is exactly `"sim"` or `"board"` (ADR-0040 decision 4); all six are required (ADR-0040 decision 5). `additionalProperties` false is decision 3. The `run_id` pattern is anchored at both ends, so that it states the whole value and not a part of it.
- **What the schema cannot state, and the description tells** (decision 5): the function refuses a number of the six that is written with a fraction or an exponent — `1.0`, `1e0` — as no *integer*, while the JSON Schema type `integer` admits a number whose fraction is zero (draft 6 and later; the schema names no `$schema`, and under draft 4, whose `integer` excludes `1.0`, the schema only admits less). *Integer* is read here, for a request, as a JSON number written without a fraction or an exponent (this record's own reading; the frame check refuses a value that is not exactly an `int` after parsing — observation). Nothing else the function refuses in ① lies beyond the schema. What a schema-valid request may still be answered with after ① — `no_data_root`, a `run_file_*` kind, a stored outcome, `step_open`, a kind of ④ — is no refusal and is not a schema matter.
- **The reduction rule of ADR-0039 decision 3 is taken over**: "Which keywords Claude Code accepts in a schema is not verified (cited: ADR-0015 F14, sub-question ⑤); if one of these is not accepted, the schema is reduced and the description says what the function refuses beyond it" (cited). Removing a keyword only widens what a schema admits, so a reduced schema still admits every request the function accepts. This record adds `minimum`, `maximum` and `enum` to the keywords ADR-0039 used; whether Claude Code accepts them is as unverified as the others.
- **Sub-question ⑤ stays open**: nothing here checks that the schema and the function agree, and nothing here says what Claude Code does with `inputSchema`.

### 5. The description

- **The description must tell the caller at least**: (i) that a call checks the kernel of the one attempt the request names, at the execution point `point` states; (ii) that the tool is journaled — a call with the identity of an ended check is answered with the stored outcome and makes no new check, a call with the identity of an open one gets `step_open`, and a new check of the same attempt at the same point is a new identity with a higher `execution` (cited: ADR-0011 decision 3; ADR-0040 decisions 2 and 3); (iii) that the request has exactly the six members and that any other member is refused (decision 3); and (iv) what the function refuses beyond the stated schema (decision 4), and, if the schema is reduced, what the reduction left out.
- It names no rule of who may raise `execution` or when — that is OD-10 and the retry part of OD-17 (cited: ADR-0040 decision 3) — and it states no tolerance, number of draws, dimension or setting as a value.
- **Its text is the code task's**, as ADR-0039 decision 3 left the text of the blob tools' descriptions.

### Walk-through

The run `r1` and the attempt `round` 3, `candidate` 2, `attempt` 1 of ADR-0040's Walk-through. "The request" is `{"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1, "point": "sim"}`. No member of a result is shown.

| The call | Schema | What the tool function does | The caller gets |
|---|---|---|---|
| The request | admits | ① passes; ② to ⑦ as ADR-0048 decision 10 has them | A result, or a tool failure of a later moment |
| The request with `"draws": 1000`, `"seed": 7` or `"tolerance": {"rtol": 0.1}` added | refuses (`additionalProperties`) | Refused in ①. Nothing asked, read, drawn or appended | `invalid_request`; the message may name `draws` (`seed`, `tolerance`) and shows nothing of the value |
| The request with `"m": 1` added | refuses | The same | `invalid_request` |
| The request with `"Point": "sim"` in place of `"point": "sim"` | refuses (`required`, `additionalProperties`) | Refused in ①: `point` is missing and `Point` is a member no record names | `invalid_request` |
| The request with `"execution": 1.0` | admits (draft 6 and later) | Refused in ①: no *integer* | `invalid_request` |
| The request with `"point": "Sim"` | refuses (`enum`) | Refused in ① (ADR-0040 decision 4) | `invalid_request` |
| The request, sent again after the first call ended | admits | ③: the stored outcome | The stored result |
| The request with `"draws": 1000` added, after the first call ended | refuses | Refused in ①, before the lookup | `invalid_request`, not the stored result |

### 6. Limits

- **A front or a client that adds a member to every request** would have every call refused. What Claude Code sends as the arguments of an MCP call is not verified (OD-18 sub-question ⑤, and ① for the MCP front in a live session); the refusal would show at the first call.
- **The schema is not a check**: a caller that ignores it is told by the function alone (cited: ADR-0015 decision 2).
- **A caller cannot ask for a check on other inputs than the run states.** That is the purpose of ADR-0041, ADR-0046 and ADR-0021 (cited); this record adds only that such an attempt is refused rather than ignored.
- The limits of ADR-0040 decision 8 stand unchanged.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Keep the list open | It waits on nothing (decision 2); it leaves decision 3 without an answer and the schema without `additionalProperties`. |
| 2 | Close it with an optional member for an input that has a source (for example `draws` that must equal the file, or may only raise it) | "A second statement of one thing" (ADR-0041 Alternatives, cited); ADR-0046 decision 2 weighed request members under (a) and (d) and chose the file (cited). A member is added when a record gives it a meaning. |
| 3 | (b) Ignore it | Decision 3: a silent difference between what the caller sent and what was checked, stored under the identity. |
| 3 | (c) Pass it on to the operation | Decision 3: a path from the calling agent to the check that ADR-0016, ADR-0020, ADR-0021 and ADR-0060 close. |
| 3 | Refuse only the names of known inputs (`draws`, `seed`, `tolerance`, `m`, …) and ignore others | A list to keep in step with every record; a misspelling of one of the six would still be ignored. |
| 3 | Refuse it at a later moment, after the data root is asked | For `invalid_request` "nothing was read, written or consumed", and the refusal is "the same on every machine" (ADR-0015 decision 2, cited). |
| 4 | No `pattern`, `minimum`, `maximum` or `enum`; the description tells all | The schema would state less than it can; ADR-0039 decision 3 states its pattern. The reduction rule covers a keyword that is not accepted. |
| 4 | `"type": "number"` for the numbers | It admits more than `integer` and tells the caller less. |
| 5 | Fix the text of the description here | ADR-0039 decision 3 leaves the text to the code task; the record fixes what it must tell. |

## Consequences

- **The code slice this record makes possible** (code mode, a later task): the refusal of a member no record names in ① and the input schema and description of `correctness.check`, with tests for each row of the Walk-through. Whether it lives in `hilclaw/check_identity.py`, `hilclaw/check_tool.py` or a new module, and its names, are the code task's.
- **What still stands between that and a registered tool**: the binding of a backend, a source of seeds and the predicate "covered" (`hilclaw/check_tool.py` takes each as a parameter without a default), and the registration itself. Also open: the spend beyond ADR-0040 decision 6, sub-question ⑤, and ⑱.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0040 decision 5 ("The member list of a request is not closed by this record …"), its Alternatives row "Close the member list here and refuse every other member" (its reason no longer holds), its Consequences (the first item) and its Boundaries ("every other request member, the input schema, the description, what is done with a member no record names"); ADR-0021 decision 1 ("the members of the request, the input schema and the description") and ADR-0038 decision 7 (the same item); ADR-0041 decision 6 ("The member list of a request stays open"; "This record does not say what the tool function does with a member no record names — a member named `m` …") and its Consequences and Boundaries; ADR-0046 decision 6 (the same, with `draws`), the Walk-through row "the request with a member `draws` added" (such a request is now `invalid_request`) and the Alternatives row "Decide it together with the closed member list of a request"; the "rest of the request" items in the Consequences and Boundaries of ADR-0042, ADR-0043, ADR-0044, ADR-0045, ADR-0046, ADR-0047, ADR-0048, ADR-0056 and ADR-0060. No sentence of UsageCases became false.
- **Docstring sentences that become less exact** (observations, not edited): in `hilclaw/check_tool.py`, "The member list of a request is open (ADR-0040 decision 5) … it has no input schema and no description, looks at no member but `point` and the four …, and hands the request on as the caller gave it"; in `hilclaw/check_identity.py`, "It does not close the member list of a request and says nothing of a member no record names" and "the member list of a request is open (ADR-0040 decision 5)" in `check`. Each stays true of the code until the code slice lands.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. **This is no "데이터 plane 스키마 변경"**: a request is the interface between layer 1 and layer 2 (ADR-0010 and ADR-0015 Consequences, as ADR-0039 and ADR-0040 read it) and is written to no file of the data plane — the `data` of a start line is exactly `step` and `execution` (cited: ADR-0011 decision 3), and the numbers of a request enter a line only as the envelope numbers and `execution`, members ADR-0006 decision 3 and ADR-0011 decision 3 already fix, `point` only through the `step` that follows from it (ADR-0040 decision 3). That a call of this tool writes its `run_id` into no line, using it only to find the directory of the run (`runs/<run_id>/`, cited: ADR-0004 decision 8), is this record's own reading. No member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec, `build.json` or a result file is added, removed or changed, and no request member is added.
- **Name check** (2026-10-16, `hilclaw/`, `tests/`, `ARCHITECTURE/`): the record adds no kind, no member, no `step` value and no reserved kind; the names it uses are the six of ADR-0040 decision 5 and `invalid_request`.

## Boundaries (not decided here)

- **Other tools' requests**: the member list, schema and description of `sim.run` and `board.run`, a `point` in them included (ADR-0062 decision 4); `blob.push` and `blob.fetch` (unchanged); `profiler.collect`.
- **Sub-questions of OD-18**: ⑤ (what checks that a schema and a function agree; what Claude Code does with `inputSchema`); ⑱ (가) to (마); ⑭.
- **The registration** of `correctness.check`, and the binding of a backend, a source of seeds and the predicate "covered".
- **The spend** (FR-3, OD-2, OD-19) beyond ADR-0040 decision 6.
- **What anybody does after an answer**: repair, a further `execution`, which check counts (FR-1, OD-10, OD-17, PLAN P2-1).
- **Owner-only (DRIVER §9)**: the #5 A and B items, among them A-4, B-2, B-3 and B-7; OD-3; OD-25; C-6.
- Any change to an earlier record, to UsageCases, to `hilclaw/`, to tests, to CI, to any settings file or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-3, FR-9, FR-10, C-4; register rows OD-2, OD-10, OD-17, OD-18, OD-19.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ①, ⑤, ⑭, ⑱); [StandardScenarios](../StandardScenarios.md).
- [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1; record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 8); [ADR-0006](ADR-0006-od8-events-log.md) (decision 3); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 2); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decision 3); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4); [ADR-0016](ADR-0016-od18-backend-frame.md) (decisions 2, 4); [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) (decision 5); [ADR-0021](ADR-0021-od18-correctness-check-split.md) (decisions 1, 3, 4); [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) (decision 7); [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decision 3); [ADR-0040](ADR-0040-od18-correctness-check-call-identity.md) (decisions 1 to 5, 7, 8; Alternatives; Boundaries); [ADR-0041](ADR-0041-od18-correctness-check-dimensions.md) (decisions 2, 6); [ADR-0042](ADR-0042-od18-correctness-check-result-members.md); [ADR-0043](ADR-0043-od18-correctness-check-operation-form.md); [ADR-0044](ADR-0044-od18-correctness-check-mock-script.md); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md); [ADR-0046](ADR-0046-od18-correctness-check-draws.md) (decisions 2, 6; Walk-through; Alternatives); [ADR-0047](ADR-0047-od18-correctness-check-operation-tool-failure.md); [ADR-0048](ADR-0048-od18-correctness-check-seed-draw.md) (decision 10); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decision 3); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decision 3; Boundaries); [ADR-0062](ADR-0062-od18-run-tools-call-identity.md) (decision 4).
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/check_tool.py`, `hilclaw/check_identity.py`, `hilclaw/journaled_tool.py`, `hilclaw/blob_tools.py`, `hilclaw/tools.py`, `hilclaw/mcp_front.py`; task T-0211.
