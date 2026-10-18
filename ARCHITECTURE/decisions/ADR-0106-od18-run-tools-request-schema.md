# ADR-0106: The member list of a request of `sim.run` and `board.run`, what their tool function does with a member no record names, and their input schemas and descriptions (one more part of OD-18; the eighth record of the run tools' contract)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Whose content.** One sentence of the owner is used, O1 of [ADR-0061](ADR-0061-od18-run-tools-split.md) (the answer to HQ-0005, point 1, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6117798837); it is quoted, marked **owner**, not re-decided and not subject to the objection window. **Everything else this record decides is its own design and has not been confirmed by the owner.**
- Closes **one more part of OD-18** (Open Decisions register in [Requirements](../Requirements.md)): the item [ADR-0062](ADR-0062-od18-run-tools-call-identity.md) decision 4 left to a later slice — "Whether a request carries anything else, the input schema, the description and what the tool function does with a member no record names are a later slice's" — which ADR-0063 to ADR-0067 carry on as "the rest of the request" or "the input schema and the description". It answers **no registered sub-question** — ⑤ (second half), ⑧, ⑲ (나) to (라) and ⑳ stay open (decisions 2, 4 and 5) — and registers none. The register row of OD-18 keeps its status wording.
- **It is not the whole contract of either tool, and neither tool is registered by it** (Consequences). It is a record, not code; nothing was built or run, and no compiler, kernel, container or `claude` process was started. Statements about code were read at `ad9b763` and are observations.
- **No sentence of an earlier record is replaced.** Sentences that call these points open become less exact; Consequences lists those this record found. **No member of any data-plane file or record is added** (Consequences, A-13 reading).
- It builds on [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4), ADR-0062 (decisions 2 to 4 and 6), [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decision 3) and [ADR-0069](ADR-0069-od18-correctness-check-request-schema.md) (for the manner), and on the records that gave each input a source outside the request: ADR-0061 (decisions 2 to 6), [ADR-0064](ADR-0064-od13-run-tools-timing-seed.md) (decision 2), [ADR-0065](ADR-0065-od18-run-tools-operation-form.md) (decisions 2 and 3) and [ADR-0067](ADR-0067-od18-run-tools-admission-kinds.md) (decisions 2 to 5). **If ADR-0015 or ADR-0062 is reverted, this record falls with it; if one of the others is reverted, decision 2 is revisited for the input it gave a source.** [ADR-0077](ADR-0077-od18-schema-function-agreement-check.md) is used as it stands.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0062 decision 4 fixed five required members — `run_id`, `round`, `candidate`, `attempt`, `execution` — and left the rest open; it adds "A member named `point` in a request of either tool states nothing; whether such a request is refused is what the tool function does with a member no record names, a later slice's". Its Alternatives rejected closing the list then: "The input schema and any further member are a later slice's; a closed list would be reopened by it."
- Since then every input a call of these tools uses was given a source that is no member of a request, or a cut that hands it nothing from the request (decision 2). `correctness.check` closed the same item in ADR-0069 once it was in that position.
- A tool definition needs a non-blank description and an input schema (cited: ADR-0015 decision 2), and the check of ADR-0077 runs over every tool of the default registry (its decision 2). Neither run tool has either today.
- **What the code has today** (observations; no code is bound by this record). `hilclaw/run_identity.py` binds the two `step` values and the three numbers, "does not close the member list of a request", and says what is done with a member no record names, "a member ``point`` among them, is a later slice's". The frame check (`hilclaw/journaled_tool.py`, `_checked`) refuses a request whose `run_id`, `execution` or required numbers are missing or ill-formed, and an envelope number the tool does not take, before the tool's own `check`; it does not look at other members. `hilclaw/hw_tool.py` has `stepped_tool_function`, whose `admit` is called "with the request as the caller gave it". `hilclaw/tools.py` `default_registry` registers `blob.fetch`, `blob.push` and `correctness.check`, not the run tools. `hilclaw/check_identity.py` and `hilclaw/check_definition.py` are how ADR-0069 landed for the check.
- **Fixed and not re-decided.** FR-10 and C-4 as they stand; O1; [ADR-0001](ADR-0001-od4-key-schema.md) (*integer*), [ADR-0004](ADR-0004-od8-data-plane-layout.md) decision 8, [ADR-0006](ADR-0006-od8-events-log.md) decision 3, [ADR-0010](ADR-0010-od18-tool-exposure-form.md), [ADR-0011](ADR-0011-od17-journal-and-spend.md) decision 3, ADR-0015, [ADR-0016](ADR-0016-od18-backend-frame.md), ADR-0039, ADR-0061 to ADR-0067, ADR-0069 and ADR-0077 as they are.
- #5 A-4, B-2, B-3 and B-7 are unanswered. Nothing below needs them, and nothing below may be read as an answer to them.

## Decision

A sentence marked **owner** quotes O1. A sentence is **cited** when a record and its decision, or a requirement, is named with it; it then says what that source says and adds nothing. Every other sentence is **this record's own** — among them that the list is closed, the refusal of every other member, its moment and message, the schemas and their keywords, the reading of *integer*, what the descriptions must tell, and every weighing.

### 1. Scope and terms

- This record is about **a request of `sim.run` or `board.run` about one attempt of a run** that ADR-0061 decision 1 covers: a run whose hw_profile names `cpu_standin` — the first case, in the local configuration of ADR-0038 decision 1 — or names the mock (cited: ADR-0062 decision 1). It fixes four points: the member list (decision 2); what is done with a member no record names (decision 3); the input schemas (decision 4); and what the descriptions must tell (decision 5).
- **One record for both tools**, as ADR-0062 and ADR-0063 are: "nothing but the execution point distinguishes the two operations" (**owner**, O1), and every point below is stated once for both. They differ in the name of the tool, the point it times and its `step` value (cited: ADR-0062 decision 3), which follow from the tool and not from the request.
- The terms of ADR-0010 (request, tool failure, front), ADR-0015 (tool definition, reserved kind), ADR-0016 (operation, the moments ① to ⑦), [ADR-0021](ADR-0021-od18-correctness-check-split.md) (the cut, as ADR-0061 uses it) and ADR-0061 (the read of ④) are used unchanged. **A member no record names**: a top-level member of a request whose name is none of the five of ADR-0062 decision 4, compared as it is, case-sensitive.
- **It says nothing of the requests of other tools**: `correctness.check` (ADR-0069 stands unchanged), `blob.push` and `blob.fetch` (ADR-0039 decision 3), `profiler.collect`.

### 2. The member list is closed at the five members of ADR-0062 decision 4

- **A request of either tool has exactly the five members `run_id`, `round`, `candidate`, `attempt` and `execution`, with the meaning and form ADR-0062 decision 4 gave them (cited, taking ADR-0015 decision 4), and no other.**
- **Each input of a call has a source outside the request, or a cut that hands it nothing from the request** (all cited):

| Input | Source | Record |
|---|---|---|
| The execution point | the tool called; "no member of a request says it" | ADR-0061 decision 5 |
| The dimensions `m`, `k`, `n` | the `shape` of the op_signature `instance.json` states, taken in the read of ④; "a member of the request would let a calling agent choose what the kernel is timed on" | ADR-0061 decision 3; ADR-0067 decisions 2, 3 and 5 |
| `n_max` | the member of `instance.json`, read in ④; "a member of a request" does not stand in for it | ADR-0061 decision 3; ADR-0023 decision 5 as ADR-0067 decision 4 cites it |
| The objective | the member `objective` of `instance.json`, read in ④ | ADR-0061 decision 4 |
| The sample form | derived from the objective at each call; "the request carries none" | ADR-0061 decision 4 |
| The `bound` | the `memory_ceiling` entry of `objective.constraints`, read in ④; "not a member of the request" | ADR-0061 decision 6; ADR-0052 decision 7 |
| The seed | drawn by the tool function for each call; "No request member carries it" | ADR-0064 decision 2 |
| The timing executable | built by the operation at each call from what the reader finds at the output path the tool function forms from `run_id` and the three numbers | ADR-0061 decisions 2 and 3; ADR-0065 decision 2 |
| `n_min`, `cv_max` | the constants of `measurement.py`; "not handed" | ADR-0061 decision 3 |
| The settings of the timing build and run | "the backend's own; the tool function hands none of them over" — **their source and values are open: OD-18 sub-question ⑲ (라)** | ADR-0061 decision 3, taking ADR-0060 decision 3 |

- Beside them, a backend "is not a member of a request" (cited: ADR-0016 decision 4, as ADR-0069 decision 2 cites it), "The data root is never a member of a request" (cited: ADR-0015 decision 3), and "`step` is not a member of a request" (cited: ADR-0015 decision 4; ADR-0062 decision 3).
- **Why close it now.** ADR-0062 kept the list open because the schema and any further member were a later slice's; no input in the table waits on a request member, so an open list would wait on nothing. A closed list is what the schemas can state exactly (decision 4) and what a caller can be told in full. **Weighed against keeping it open**: an open list leaves decision 3 without an answer, and a schema with `"additionalProperties": true` would admit members the contract gives no meaning.
- **Relation to ⑲ (라) and ⑧, neither answered.** ⑲ (라) asks for the source and values of the backend's own settings; the cut of ADR-0061 decision 3 already hands no setting from the request, and closing the list adds only that no setting member exists today. ⑧ asks how the default registry's mock injects faults in a live session; an answer that depends on a request member is ⑧'s (cited: ADR-0066 decision 3 (b)). **A later record that gives the request a member — for a setting, for fault injection or for anything else — extends the list and both schemas, and that is a change of this contract**, in the manner of ADR-0069 decision 2. The record says only that no such member exists today.
- **What follows for the operation** (a consequence, not a rule): the request an operation is handed — handed to it as it is (cited: ADR-0065 decision 3, citing ADR-0016 decision 2) — holds exactly the five members, since a request with another one never reaches ⑥ (decision 3). An operation still takes its point from no member (cited: ADR-0065 decision 3).

### 3. A member no record names: refused as `invalid_request` in ①

- **A request of either tool with a member no record names is a refused request: the tool failure of the reserved kind `invalid_request`** (the kind and its meaning are cited: ADR-0015 decision 2). That holds for every such name and every value it carries, `null` included — among them `point` (with any value, also the one that matches the tool called), `seed`, `n_max`, `bound`, `objective`, `sample_form`, `m`, `k`, `n`, `shape`, `op_signature`, `step`, `hw_profile`, `data_root`, a flag, a time limit, and a misspelling such as `Execution` or `run-id`.
- **The moment is ① of the order of ADR-0062 decision 6**, whose row is "`invalid_request`; nothing asked, read, built or appended" (cited), and a tool function refuses "before it asks for the data root" (cited: ADR-0015 decision 2). That this refusal lies in ① with the check of the five members is this record's own. So such a request is not looked up, reads no `instance.json`, selects no backend, draws no seed, builds and runs nothing, appends no line and consumes nothing; it is answered alike on every machine, at either tool, and for an ended, an open or an unused identity alike. Which of several faults of one request the message names is the code task's; the kind is the same for all.
- **The message of this refusal.** It may name the members it refuses, by the names the request gave them, and the five members the tool takes. **It shows nothing of the value of a member it refuses** — not the value and not its type — in the manner of ADR-0069 decision 3. Its text is the code task's. The messages of the frame check of the five members are not changed by this record.
- **Three answers were weighed.**
  - **(a) Refuse** — the choice of ADR-0039 decision 3 ("a request with any other member", cited) and ADR-0069 decision 3. A caller that believes it set the seed, the bound or the point learns at once that it did not.
  - **(b) Ignore it.** A caller that sends `"n_max": 1000` or `"seed": 7` would get a run timed on the run's own `n_max` and a drawn seed and could not tell; the result would be stored under the identity and returned to every repeated call (cited: ADR-0011 decision 3). `"point": "board"` sent to `sim.run` would be timed at the sim point in silence. A misspelled `Execution` would be ignored while `execution` is missing, so (b) needs (a) for the five anyway.
  - **(c) Hand it on to the operation.** The request reaches the operation as it is (cited: ADR-0065 decision 3), so this needs nothing added; but it opens a path from the calling agent to the run that ADR-0061 decisions 3 to 6, ADR-0064 decision 2 and ADR-0065 decision 3 close for the inputs of decision 2, and a script of the mock, asked with the request (cited: ADR-0016 decision 5 (c)), could answer from members no record defines — fault injection in a live session, which is ⑧ (cited: ADR-0066 decision 3 (b)). Choosing (c) would answer ⑧ in passing.
- **The choice is (a).**

### 4. The input schemas

- **Both tool definitions state the same schema** (cited: ADR-0015 decision 2 — "a statement to the caller, not a check of the frame"; "the stated schema admits every request the tool function accepts"):

```json
{"type": "object",
 "properties": {
  "run_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9_-]{0,63}$"},
  "round": {"type": "integer", "minimum": 0, "maximum": 9007199254740991},
  "candidate": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
  "attempt": {"type": "integer", "minimum": 1, "maximum": 9007199254740991},
  "execution": {"type": "integer", "minimum": 1, "maximum": 9007199254740991}},
 "required": ["run_id", "round", "candidate", "attempt", "execution"],
 "additionalProperties": false}
```

- **Where each constraint comes from** (cited): `run_id` matches `[a-z0-9][a-z0-9_-]{0,63}` (ADR-0004 decision 8, as ADR-0015 decision 4 names it); `round` is an *integer* (`0` = bring-up), `candidate` and `attempt` are *integers* ≥ 1 (ADR-0006 decision 3); `execution` is an *integer* ≥ 1 (ADR-0011 decision 3); an *integer* "is in the range 0 to 2^53 - 1" (ADR-0001 decision 1); all five are required (ADR-0062 decision 4). `additionalProperties` false is decision 3. The pattern is anchored at both ends, so that it states the whole value. It is the schema of ADR-0069 decision 4 without `point`.
- **Why one schema for both.** The requests of the two tools have the same members and forms (decision 2); a schema per tool that differed — a `point` with one value each, for one — would state a member decision 3 refuses. The tools are told apart by name and description (decision 5). Whether code holds one object or two equal ones is the code task's.
- **What the schema cannot state, and the descriptions tell** (decision 5): the function refuses a number of the five written with a fraction or an exponent — `1.0`, `1e0` — as no *integer*, while the JSON Schema type `integer` admits a number whose fraction is zero (draft 6 and later; the schema names no `$schema`). *Integer* is read here, for a request, as a JSON number written without a fraction or an exponent, the reading ADR-0069 decision 4 made for the check (cited for the manner; the frame check refuses a value that is not exactly an `int` after parsing — observation). Nothing else the function refuses in ① lies beyond the schema. What a schema-valid request may still be answered with after ① — among them `no_data_root`, a `run_file_*` kind, a stored outcome, `step_open`, `no_backend`, `not_offered`, a kind of ADR-0061 decision 4 or ADR-0067, `seed_not_drawn` (ADR-0064 decision 4), `start_line_failed` and `end_line_failed` (ADR-0026 decision 3) — is no refusal and no schema matter.
- **The reduction rule of ADR-0039 decision 3 is taken over**: "Which keywords Claude Code accepts in a schema is not verified …; if one of these is not accepted, the schema is reduced and the description says what the function refuses beyond it" (cited). Removing a keyword only widens what a schema admits, so a reduced schema still admits every request the function accepts.
- **Relation to ADR-0077, which is not changed.** The schema uses seven of the eight keywords of ADR-0077 decision 4 — `type`, `properties`, `required`, `additionalProperties`, `pattern`, `minimum`, `maximum` — each in a position that decision reads, so no keyword is added to the set. Once a run tool is registered in `default_registry`, the check of ADR-0077 decisions 2 and 3 covers it, and the change that registers it brings its one accepted request as data (cited: ADR-0077 decision 3). Direction (B), that a description tells what lies beyond its schema, stays held by this record and by review (cited: ADR-0077 decision 3).
- **Sub-question ⑤ stays open in its second half**: nothing here says what Claude Code does with `inputSchema` (cited: ADR-0077 decision 6).

### 5. The descriptions

- **Each description must tell the caller at least**: (i) which point the tool times — that a call of `sim.run` times the kernel of the one attempt the request names at the sim point, and `board.run` at the board point, and that no member states the point (cited: ADR-0061 decision 5); (ii) that the tool is journaled — a call with the identity of an ended run is answered with the stored outcome and makes no new run, a call with the identity of an open one gets `step_open`, and a new timing run of the same attempt at the same point is a new identity with a higher `execution` (cited: ADR-0011 decision 3; ADR-0062 decisions 2 and 3); (iii) that the run's own `instance.json` supplies the dimensions, `n_max`, the objective and the `bound`, and that the seed and the settings are no members of the request (decision 2); (iv) that the request has exactly the five members and any other — `point` among them — is refused (decision 3); and (v) what the function refuses beyond the stated schema (decision 4), and, if the schema is reduced, what the reduction left out.
- They name no rule of who may raise `execution` or when (OD-10, OD-17; cited: ADR-0062 decision 3) and no rule of which execution counts (⑳), and they state no dimension, `n_max`, bound, seed or setting as a value.
- The two texts differ in (i) and may be otherwise alike. **Their text is the code task's**, as ADR-0039 decision 3 left the text of the blob tools' descriptions.

### Walk-through

The run `r1` and the attempt `round` 3, `candidate` 2, `attempt` 1 of ADR-0062's Walk-through. "The request" is `{"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1}`. No member of a result is shown.

| The call | Schema | What the tool function does | The caller gets |
|---|---|---|---|
| `sim.run` with the request | admits | ① passes; ② to ⑦ as ADR-0062 decision 6 and ADR-0067 decision 5 have them | A result, or a tool failure of a later moment |
| `board.run` with the request | admits | The same, under `board_run_timing` | A result, or a tool failure of a later moment |
| `sim.run` with `"point": "sim"` added | refuses (`additionalProperties`) | Refused in ①, although the value names the tool's own point. Nothing asked, read, drawn, built or appended | `invalid_request`; the message may name `point` and shows nothing of the value |
| `board.run` with `"point": "sim"` added | refuses | The same: no member says the point | `invalid_request` |
| Either tool with `"seed": 7` or `"n_max": 1000` added | refuses | Refused in ①; no seed is drawn and `instance.json` is not read | `invalid_request`; the message may name `seed` (`n_max`) |
| Either tool with `"bound": 1024`, `"objective": {}` or `"m": 1` added | refuses | The same | `invalid_request` |
| `sim.run` with `"Execution": 1` in place of `"execution": 1` | refuses (`required`, `additionalProperties`) | Refused in ①: `execution` is missing and `Execution` is a member no record names | `invalid_request` |
| `sim.run` with `"execution": 1.0` | admits (draft 6 and later) | Refused in ①: no *integer* | `invalid_request` |
| `sim.run` with the request, again after the first call ended | admits | ③: the stored outcome | The stored result |
| `sim.run` with `"seed": 7` added, after the first call ended | refuses | Refused in ①, before the lookup | `invalid_request`, not the stored result |

### 6. Limits

- **A front or a client that adds a member to every request** would have every call refused. What Claude Code sends as the arguments of an MCP call is not verified (OD-18 sub-questions ① and ⑤); the refusal would show at the first call.
- **The schema is not a check**: a caller that ignores it is told by the function alone (cited: ADR-0015 decision 2).
- **A caller cannot ask for a timing run on other inputs than the run states**, nor at another point than the tool's. That is the purpose of ADR-0061 decisions 3 to 6 and ADR-0064 decision 2 (cited); this record adds only that such an attempt is refused rather than ignored.
- **A test that wants an answer depending on the request** has the members of decision 2 to depend on; "A script of a test can do it" (cited: ADR-0066 decision 3 (b), of an answer that depends on a member of the request). Nothing more is offered until a record answers ⑧.
- The limits of ADR-0062 decision 7 stand unchanged.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Keep the list open | It waits on nothing (decision 2); it leaves decision 3 without an answer and the schemas without `additionalProperties`. |
| 2 | Optional members for inputs that have a source (`n_max` that must equal the file, a `seed` a test may fix) | A second statement of one thing; ADR-0023 decision 5 and ADR-0064 decision 2 (cited) keep each out of the request. A member is added when a record gives it a meaning. |
| 3 | (b) Ignore it | Decision 3: a silent difference between what the caller sent and what was timed, stored under the identity. |
| 3 | (c) Hand it on to the operation | Decision 3: a path from the calling agent to the run that ADR-0061, ADR-0064 and ADR-0065 close, and an answer to ⑧ in passing. |
| 3 | Admit `point` when it equals the tool's point | A second statement of what the tool called says, with a rule needed when they differ — the reason ADR-0065 decision 3 (b) rejects handing the point (cited); a request valid at one tool would be refused at the other. |
| 3 | Refuse only the names of known inputs (`point`, `seed`, `n_max`, `bound`, …) and ignore others | A list to keep in step with every record; a misspelling of one of the five would still be ignored. |
| 3 | Refuse it at a later moment, after the data root is asked | For `invalid_request` "nothing was read, written or consumed", and the refusal is "the same on every machine" (cited: ADR-0015 decision 2). |
| 4 | A schema per tool, each with a `point` of one value | It would state a member decision 3 refuses; the tool name already says the point. |
| 4 | No `pattern`, `minimum` or `maximum`; the descriptions tell all | The schema would state less than it can; ADR-0039 decision 3 and ADR-0069 decision 4 state theirs. The reduction rule covers a keyword that is not accepted. |
| 4 | `"type": "number"` for the numbers | It admits more than `integer` and tells the caller less. |
| 5 | One description for both tools | It could not tell which point a call times (decision 5 (i)). |
| 5 | Fix the texts here | ADR-0039 decision 3 leaves the text to the code task; the record fixes what each must tell. |

## Consequences

- **The code slice this record makes possible** (code mode, a later task; D12 rules): the refusal of a member no record names in ① and the two input schemas and descriptions, with tests for each row of the Walk-through, at both tools. Whether it lives in `hilclaw/run_identity.py` or a new module, and the names, are the code task's.
- **What still stands between that slice and two registered tools**: the tool function that joins the run tools' modules (identity, admission, seed, parameters, operation form, result, journal); ⑲ (나), with what the tool function does with a tool failure an operation raises; and the binding of a backend table and a source of seeds and the registration in `default_registry`, with the accepted request of each tool for the check of ADR-0077. What ADR-0067 Consequences lists beside the input schema otherwise stands as it says.
- **Not edited and now less exact** (follow-ups for the integrator; found by grep on 2026-10-18): ADR-0062 decision 4 ("A member named `point` … whether such a request is refused is what the tool function does with a member no record names, a later slice's"; "The member list of a request is not closed by this record …"), its Walk-through rows whose request ends in "…", its Alternatives row "Close the member list here and refuse every other member" (its reason no longer holds), its Consequences item (1) and its Boundaries ("every other request member, the input schema, the description, what is done with a member no record names (a `point` among them)"); ADR-0062 decision 6, row ① ("the five members of decision 4" — the refusal of decision 3 lies there too); ADR-0061 Limit 5 ("the identity of a call … are open", of which the request part is now closed), its Consequences item (1) ("the request members, the input schema and the description") and its Boundaries ("Every request and result member …"); ADR-0063 Consequences and Boundaries ("The rest of the request"); the same item in the Consequences of ADR-0064, ADR-0065 and ADR-0066, the Boundaries of ADR-0065 ("The rest of the request") and ADR-0066 ("the input schema and the description"), and the "Not decided by this record" bullet of ADR-0066 decision 5 ("The input schema and the description"), and the Consequences ("the input schema" among what is not yet possible) and Boundaries of ADR-0067; ADR-0069 Boundaries ("the member list, schema and description of `sim.run` and `board.run`, a `point` in them included"); ADR-0070 Boundaries ("the registration, requests, schemas and descriptions of `sim.run` and `board.run`" — the registration stays open). No sentence of UsageCases became false.
- **Docstring sentences that become less exact** (observations, not edited): in `hilclaw/run_identity.py`, "It does not close the member list of a request, and what is done with a member no record names, a member ``point`` among them, is a later slice's (decision 4)". It stays true of the code until the code slice lands.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. **This is no "데이터 plane 스키마 변경"**: a request is the interface between layer 1 and layer 2 (ADR-0010 and ADR-0015 Consequences, as ADR-0062 and ADR-0069 read it) and is written to no file of the data plane — the `data` of a start line is exactly `step` and `execution` (cited: ADR-0011 decision 3), and the numbers of a request enter a line only as the envelope numbers and `execution`, members ADR-0006 decision 3 and ADR-0011 decision 3 already fix. No member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec or a result file is added, removed or changed, and no request member is added: the list is closed at the five that ADR-0062 decision 4 already required.
- **Name check** (2026-10-18, `hilclaw/`, `tests/`, `ARCHITECTURE/`): the record adds no kind, no member, no `step` value and no reserved kind; the names it uses are the five of ADR-0062 decision 4 and `invalid_request`. The names it shows as refused are no members of any record of these tools. `ARCHITECTURE/EventKinds.md`, `StepValues.md` and `SpendAxes.md` are not touched.
- **Runtime acceptance items**: none beyond ADR-0077 decision 6.

## Boundaries (not decided here)

- **Other tools' requests**: `correctness.check` (ADR-0069, unchanged); `blob.push` and `blob.fetch` (ADR-0039, unchanged); `profiler.collect`.
- **Sub-questions of OD-18**: ⑤ (what Claude Code does with `inputSchema`); ⑧ (fault injection in a live session, with a request member or otherwise); ⑲ (나) to (라); ⑳.
- **The tool function that joins the run tools' modules, the binding of a backend and a source of seeds, and the registration** of either tool.
- **The result files** (`sim.json`, `board.json`; PLAN P1-8).
- **The spend** (FR-3, OD-2, OD-19) beyond ADR-0062 decision 5.
- **What anybody does after an answer**: a further `execution`, which execution counts, repair (FR-1, OD-10, OD-17, PLAN P2-1).
- **Owner-only (DRIVER §9)**: the #5 A and B items, among them A-4, B-2, B-3 and B-7; OD-3; OD-25; C-6.
- Any change to an earlier record, to UsageCases, to `hilclaw/`, to tests, to CI, to any settings file or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-3, FR-10, C-4; register rows OD-2, OD-10, OD-17, OD-18, OD-19.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ①, ⑤, ⑧, ⑲, ⑳); [StandardScenarios](../StandardScenarios.md).
- [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1; record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 8); [ADR-0006](ADR-0006-od8-events-log.md) (decision 3); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 2 to 4); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decision 3); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 2 to 4); [ADR-0016](ADR-0016-od18-backend-frame.md) (decisions 2, 4, 5); [ADR-0021](ADR-0021-od18-correctness-check-split.md) (the cut); [ADR-0023](ADR-0023-od8-instance-record-n-max.md) (decision 5); [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) (decision 1); [ADR-0039](ADR-0039-od18-blob-push-fetch-local.md) (decision 3); [ADR-0052](ADR-0052-od13-memory-ceiling-measurement.md) (decision 7); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decision 3); [ADR-0061](ADR-0061-od18-run-tools-split.md) (decisions 1 to 6; Limit 5; Consequences; Boundaries); [ADR-0062](ADR-0062-od18-run-tools-call-identity.md) (decisions 1 to 4, 6, 7; Walk-through; Alternatives; Consequences; Boundaries); [ADR-0063](ADR-0063-od18-run-tools-result-members.md); [ADR-0064](ADR-0064-od13-run-tools-timing-seed.md) (decision 2); [ADR-0065](ADR-0065-od18-run-tools-operation-form.md) (decisions 2, 3); [ADR-0066](ADR-0066-od18-run-tools-mock-script.md) (decisions 3, 5); [ADR-0067](ADR-0067-od18-run-tools-admission-kinds.md) (decisions 2 to 5; Consequences); [ADR-0026](ADR-0026-od18-failed-step-line-append.md) (decision 3); [ADR-0069](ADR-0069-od18-correctness-check-request-schema.md) (decisions 2 to 4; Boundaries); [ADR-0070](ADR-0070-od18-correctness-check-registration.md) (Boundaries); [ADR-0077](ADR-0077-od18-schema-function-agreement-check.md) (decisions 2 to 4, 6).
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/run_identity.py`, `hilclaw/hw_tool.py`, `hilclaw/journaled_tool.py`, `hilclaw/tools.py`, `hilclaw/check_identity.py`, `hilclaw/check_definition.py`; task T-0308.
