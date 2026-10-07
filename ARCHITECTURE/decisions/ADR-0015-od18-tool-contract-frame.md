# ADR-0015: The frame every FR-10 tool contract shares — the tool definition, the data root, the run and the identity in a request, and where a journaled step is carried out (one more part of OD-18)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one more part of OD-18** (Open Decisions register in [Requirements](../Requirements.md)): the invocation convention of [ADR-0010](ADR-0010-od18-tool-exposure-form.md) continued by what every tool contract has in common, and **one** question of the rest of OD-18 — where the two step lines and the lookup of [ADR-0011](ADR-0011-od17-journal-and-spend.md) are carried out. What ADR-0011 decision 3 handed to PLAN P1-1 ("how a request carries it is the tool's contract") is answered as far as the frame goes. The register rows of OD-18 and OD-17 keep their status.
- What stays open of OD-18: which hooks exist and what they check, where a check before a call is placed, round boundary = process boundary (#8 M4), the invariant list, default-FAIL, the kill switch, the three sub-questions of ADR-0010 and the two this record raises. Of OD-17: the lock and fencing, the retry policy, its three sub-questions.
- It builds on ADR-0010 and ADR-0011, on [ADR-0006](ADR-0006-od8-events-log.md) (envelope, append only), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 4) and [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decision 3), whose objection windows run until 2026-10-14, and on the `id` integers of [ADR-0002](ADR-0002-od6-codegen-spec.md) (until 2026-10-13). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- PLAN P1-1 has its two fronts and its library parts on `main` and no tool: `hilclaw.tools.default_registry()` is empty. Four points common to every tool were each left open by a record on purpose, and a code task would otherwise have to invent them.
- **Description and input schema.** ADR-0010 decision 4: a tool is listed "with its MCP name, a description and an input schema (F8); the content of both is each tool's". Today `Registry.register(name, function)` carries neither, and `hilclaw/mcp_front.py` lists every tool without a description and with the input schema `{"type": "object"}`.
- **The data root.** ADR-0010 decision 5: "A front obtains the data root as the existing loader gives it … The modules below keep taking `data_root` from their caller and reading no configuration …; the front is that caller"; decision 2: "A tool function takes one request and returns one result". Today `tools.call(registry, name, request)` hands over the request only, and neither front calls `hilclaw.config.load_data_repo()`.
- **The run and the identity.** ADR-0011 decision 3: the identity is "given by the caller … How a request carries it is the tool's contract (PLAN P1-1)". `hilclaw.journaled_step.run(data_root, run_id, identity, step)` is the landed sequence of the repeated call; its docstring says "It is not a tool and not a hook: nothing registers or calls it".
- **The placement.** ADR-0010 decision 6: a check or the append has "two possible places — a hook on the typed tool, together with no shell for the agents concerned, or the tool layer below the fronts … Where a check or the append is placed is not decided here". ADR-0011 decision 2 left the same question for its two lines, and observed in decision 3 that "a part that runs only after a call cannot carry it out alone". [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) proposes a `PostToolUse` hook ("결과 저널링은 모델 행동이면 안 됨"), and PLAN P2-4 words it "PostToolUse 저널링".
- Fixed and not re-decided: ADR-0010 and ADR-0011 as they stand, ADR-0006, ADR-0004 decision 4 (the tool layer, never an agent, writes `events.ndjson`), ADR-0012 decision 3, FR-10, C-3, C-7, NFR-6, NFR-7 ①, #4 §1, #5 A-12, and the standard library only (a new dependency is the owner's — CLAUDE.md A-13).
- **Facts** used beyond F1 to F10 of ADR-0010. *Verified* = read in the named documentation on 2026-10-07; none was tried in a live session.

| # | Fact | Status |
|---|---|---|
| F11 | A tool definition of MCP includes `description` ("human-readable description of functionality") and `inputSchema` ("JSON Schema defining expected parameters"); its security considerations say that servers MUST "Validate all tool inputs". | verified — https://modelcontextprotocol.io/specification/2025-06-18/server/tools |
| F12 | The decision fields of a `PreToolUse` hook are `permissionDecision` (allow, deny, ask, defer), its reason, `updatedInput` and `additionalContext`; "deny" prevents the call and the reason is shown to the model. None of them supplies a result for the call. | verified — https://code.claude.com/docs/en/hooks ("PreToolUse decision control") |
| F13 | A `PostToolUse` hook runs after a tool has completed successfully, with `tool_input` and `tool_response`; it can replace what the model sees of the output, and "the tool has already run by the time the hook fires". A call in which an MCP tool returned an error result fires `PostToolUseFailure` instead. | verified — https://code.claude.com/docs/en/hooks ("PostToolUse", "PostToolUseFailure") |
| F14 | Whether Claude Code checks the arguments of an MCP tool call against the tool's `inputSchema` before it sends them, and which JSON Schema keywords it accepts in one. | **not verified** |

## Decision

A value below is **cited** when a source or a fact number is named with it; every other value is **this record's own** choice — among them the tool definition, the reserved kinds, the data-root source, the member names of a request and the placement.

### 1. Scope and terms

- This record is about **the frame**: the part of a tool's contract that is the same for every tool of the registry. It defines no tool: no argument, result member, failure kind, `step` value, axis or amount of any tool, and it does not say which tools are journaled.
- The terms of ADR-0010 decision 1 (tool function, registry, front, request, result, tool failure) and of ADR-0011 decision 1 (journaled step, identity, start line, end line, open, ended) are used unchanged.
- **Tool definition**: what the registry holds for one tool (decision 2). **Journaled tool**: a tool one call of which is one journaled step — the `result` of an end line "is the result object of the call itself" (cited: ADR-0011 decision 3). **Data-root source**: decision 3. **Reserved kind**: a value of `error.kind` to which the frame gives one meaning for every tool.

### 2. The tool definition: description, input schema and the refused request

- **A tool is registered as a tool definition: its name, its tool function, a `description` and an `input_schema`.** The registry maps a name to a definition, and the description and the schema are stated there, once, with the tool. A front holds no text and no schema of its own: the MCP front lists each tool with exactly the `description` and, as `inputSchema`, the `input_schema` the registry holds (F8, F11), and any other reader takes them from the registry too.
- `description` is a non-empty string written for the caller. `input_schema` is one JSON object in the strict sense of ADR-0010 decision 2 that is a JSON Schema whose `type` is `"object"` (cited: F11; a request is an object — ADR-0010 decision 2). The text and the schema are each tool's; which keywords a schema may use is not fixed (F14).
- **The schema is a statement to the caller, not a check of the frame: no part of the package validates a request against it. The tool function checks its own request** — below the fronts (ADR-0010 decision 3: a front holds no check), and this is where the requirement of F11 that a server validate all tool inputs is met. The tool function is authoritative. What ties the two: the stated schema admits every request the tool function accepts, and what the function refuses beyond what the schema says is told in the description.
- Why: a check against the schema would need a validator. A full one is not in the standard library (a new dependency — the owner's). A subset the package implements itself would be a schema dialect of its own to maintain, and it could not express what a request must satisfy anyway — a *name*, a `run_id`, "`candidate` only with `round`" — so every tool function would check its request a second time and the two checks could disagree.
- **A refused request is a tool failure of the reserved kind `invalid_request`** (that a refusal is a tool failure is cited: ADR-0010 decision 4). A tool function refuses before it asks for the data root (decision 3), before anything is read from or written to the data plane, and before any resource is consumed; the refusal is therefore the same on every machine and leaves no trace. The kind is deliberately not the `bad_request` with which the command-line front answers an input that is no request at all (exit status 4, `hilclaw/__main__.py`).
- **Reserved kinds.** No tool's contract defines one of these values with another meaning, and no tool function or step raises one for another situation:

| `kind` | Meaning for every tool | Origin |
|---|---|---|
| `invalid_request` | The tool function refused the request; nothing was read, written or consumed | this record |
| `no_data_root` | The data root could not be obtained (decision 3); nothing was read or written | this record |
| `step_open` | The journaled step of this identity is open (ADR-0011 decision 3) | `hilclaw/journaled_step.py`, where it is "not reserved"; reserved from here on |
| `tool_crashed`, `bad_result` | The tool function raised something that is no tool failure, or returned no result object | `hilclaw/tools.py` (`call`); reserved from here on |

- **How this reads ADR-0010 decision 4** ("this record fixes the form and no list of kinds … the kinds … belong to each tool's contract"): the table is the part of every tool's contract that is common, not a closed list; every other kind stays each tool's. Why reserve at all: a caller must be able to tell "correct the request and call again", "the configuration is wrong", "this step is open — neither skip nor run it" (ADR-0011 decision 4) and "the tool is defective" from a failure a tool defines, in the same way for every tool; with `step_open` unreserved, an ended step whose `failure` carried that kind could not be told from an open one.
- Whether the command-line front gets a way to show the description and the schema to a person is **left to the code task** (ADR-0010 decision 4 gives it "the tool name as its only argument"). If it gets one, it prints what the registry holds, unchanged.

### 3. How the data root reaches a tool function

- **The data root is never a member of a request**, and no calling agent chooses it.
- **A tool function that needs the data plane is bound, when the registry is built, to a data-root source**: a callable without arguments that returns the data root or fails. In the two fronts of the package the source is the existing loader, `hilclaw.config.load_data_repo()` (cited: ADR-0010 decision 5), with the configuration file and the two variables as they are; a test builds a registry bound to a source of its own. How the binding is written and which module builds the bound registry are the code task's.
- **The source is asked at each call that needs the data root, and its answer is not kept for a later call.** A command-line call is one process; an MCP server lives as long as its session (ADR-0010 decision 7, F7), and a value read at its start would let the two fronts answer the same request from two trees after the configuration file changed. The cost is one small file read per call.
- **When the source fails, or what it names is not an existing directory, the call is a tool failure of the reserved kind `no_data_root`**, raised before anything is read or written. It concerns only a call of a tool that needs the data plane, at that call: a tool that needs none never asks, and listing the tools or answering an unknown name never asks either.
- **How this reads ADR-0010.** Decision 2 stands literally: what the registry holds and `tools.call` calls takes one request. Decision 5's "the front is that caller" is read as: the data root enters with the front process — from the loader, the configuration file of the checkout that process loaded and the two variables of its environment — and from nowhere else; the modules below the tool function keep taking `data_root` from their caller and read no configuration. It is not read as the front module itself running the loader before the call: a front would then hold a check and a way to fail of its own for a call that reaches a tool function, and it would have to know which tools need the tree (against decision 3 of ADR-0010). ADR-0010 is not edited.
- Tests and a person redirect a call with the two existing variables (cited: ADR-0010 decision 5). The outcome of a call depends on the request, on the data plane the configuration names, and on nothing a server process kept (ADR-0010 decision 7).

### 4. How a request names the run and carries the identity

- **Five member names of a request have one meaning in every tool**; a tool uses a name with this meaning and form or not at all, always at the top level of the request:

| Member | Meaning and form | Source of the name and form |
|---|---|---|
| `run_id` | The run the call is about: a directory name of `runs/` | ADR-0004 decision 8 |
| `round`, `candidate`, `attempt` | What the call is about, as the envelope numbers of a line: an absent number is left out, never `null`; `candidate` only with `round`, `attempt` only with `candidate` | ADR-0002 (`id`), ADR-0006 decision 3 |
| `execution` | The `execution` of the identity: an *integer* ≥ 1 | ADR-0011 decision 3 |

- **The request of a journaled tool carries `run_id`, `execution` and those of the three numbers its step is about**; which numbers a tool requires is its contract. Flat members with the names of the envelope were chosen so that a request, a line and a later hook's `tool_input` (F4) name a target in one way.
- **`execution` is required and has no default.** The identity is "given by the caller" (cited: ADR-0011 decision 3); a default would be a part of the identity supplied by the tool layer, and one identity would have two spellings. The caller states 1 "unless a decision outside this record asked for a further execution" (cited, same decision). A caller that raises it by itself is not stopped (decision 7).
- **`step` is not a member of a request: the tool's contract fixes it.** A request that named the step could record one tool's execution under the name of another. Two tools of the registry do not share a `step` value, so that identities of different tools never collide in one log. This record lists no value.
- **An invalid run or identity is a refused request**: `invalid_request`, before anything is read or appended (decision 2). `hilclaw.journaled_step.run` already checks `run_id` and the identity before it reads a file; that order is a convention of the code, and the frame fixes the property, not the code.
- **An identity about a round above the stored `round`**: no such round has begun (cited: ADR-0012 decision 3), and the landed lookup finds such a step only until that round is the stored one (Limits of `hilclaw/journaled_step.py`). The fixed inputs state the fact and no rule that refuses such a request, so this record adds none: it is a limit (decision 7), and the question stays with sub-question ① of OD-17.

### 5. Where the two step lines and the lookup are carried out

- **Below the fronts, inside the tool function the registry holds for a journaled tool.** That function checks the request, obtains the data root, forms the identity from the request and the `step` of its contract, and carries out its step by the sequence of ADR-0011 decision 3 — the lookup, the start line, the step, the end line; `hilclaw.journaled_step.run` is the landed library form. Whether this is written in each tool function or as one part applied when a journaled tool is registered is the code task's. Required is that **the registry offers no way to the step of a journaled tool that goes around the lookup and the two lines**.
- This answers the open sentence of ADR-0010 decision 6 and of ADR-0011 decision 2 **for the journaled step only**: the append of ADR-0006 decision 7 for an expensive result is the end line (ADR-0011 decision 2). It is not a model action (the concern of the OD-18 proposal), and it is the tool layer's (ADR-0004 decision 4).
- **Why not a `PostToolUse` hook alone**: it runs after the call (F13), so it can neither complete a start line before the step consumes anything nor settle what a repeated call returns (ADR-0011 decisions 2 and 3, and its observation). A call that ended in a tool failure does not fire it at all (F13), yet such a step has spent and needs its end line (ADR-0011 decision 7).
- **Why not a `PreToolUse` and `PostToolUse` pair**: a call through the command-line front is not seen (ADR-0010 decision 6), so a person, a test or a script would spend without the lines. For an ended step the first hook can only prevent the call and give a reason (F12); it cannot make the call return the stored result, so the two fronts would answer one request differently. A `claude -p` child runs the hooks of its own session (F6), so the lines would depend on how each session is configured. And the end line would be written by another process after the result has left the tool layer, which widens the window of ADR-0011 decision 2.
- **What the choice means.** *Both fronts identical*: everything a call does still happens in the tool function (ADR-0010 decision 3), so the lines are written and a repeated call is answered alike through either front. *No kept state*: the lookup reads `STATE.json` and the log at each call (ADR-0010 decision 7). *The window*: the end line is appended in the process that obtained the outcome, before the result is encoded or leaves that process — the narrowest placement available; it is not closed (ADR-0011 decision 2).
- **What is left for PLAN P2-4**, undecided: which hooks exist; a check before a call (budget, gate, and any duplicate check other than the lookup of this decision, which is the duplicate check of a journaled step and is placed), for which the two possible places of ADR-0010 decision 6 stay open; journaling of events other than the two step lines; and whether a hook verifies that a journaled call left its lines. A hook is no longer the writer of the two step lines.
- Journaling is not a property of every tool. For which tools it holds is each tool's contract (ADR-0011 decision 9); the sources name the board measurement only.

### Walk-through

Placeholders: the tool `example.tool` (`mcp__hilclaw__example_tool`) with the `step` `example_step`; no real tool is given members. The request is `{"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1, …}`.

| Moment | Through either front (the same code below it) |
|---|---|
| The call arrives | The front decodes the request, looks the name up and calls the tool function (`tools.call`); nothing else |
| The request is checked | In the tool function: its own members, `run_id`, the identity. A missing `run_id`, `execution` 0 or `attempt` without `candidate` → `invalid_request`; no configuration read, no file read, nothing appended |
| The data root | The tool function asks its data-root source. An unreadable configuration or a missing directory → `no_data_root`; nothing appended |
| The lookup | From `STATE.json` and the log of `runs/r1/`: no line, open or ended |
| No line | The start line is appended and complete, the step runs, the end line is appended with `spend` and the `result` or `failure`, and the call returns what the end line holds |
| Death before the start line is complete | A repeated call through **the other front** finds no line and runs the step for the first time |
| Death after the start line, before the end line is complete | A repeated call through the other front is the tool failure `step_open`; nothing runs and nothing is appended |
| Death after the end line | A repeated call through the other front returns the `result` of the line, or its `failure` again; nothing runs and nothing is appended |

### 6. What follows for the conformance tests and the mock backend

Consequences, not decisions. With the frame alone a test can check of any registered tool: that both fronts show the description and the schema the registry holds; that one request gives the same outcome through both fronts; that a request its function refuses is `invalid_request` and leaves the data plane untouched; that a failing data-root source is `no_data_root`; and, for a journaled tool, the three states of ADR-0011 decision 4 and the three death points, with the first call through one front and the repeated call through the other. What a backend is, how a tool selects one and what the mock backend injects are the next record's, with the first tool.

### 7. Limits

- **No access control** (ADR-0010 decision 8): whoever can call a tool can present any `run_id` and any identity.
- **A wrong identity**: a caller that states the numbers of another target records the step under them, and a caller that raises `execution` by itself runs an open or an ended step again (cited: ADR-0011 decision 9). Nothing in the frame stops either.
- **A round above the stored `round`** (decision 4): not refused; such a step can be run again, counted twice and not reported, once that round is the stored one.
- **Two calls at once** can both find no line (rest of OD-17).
- **A tool that does not use the frame**: a tool function that spends without the journaled path, that accepts what its schema excludes, or that raises a reserved kind for something else is not detected by the frame (ADR-0011 decision 9; forcing it is the rest of OD-18).
- **Two environments**: the two fronts answer alike only when their processes see the same configuration file and the same two variables. An MCP server has the environment it was started with.
- **A run that cannot be used** — no valid `STATE.json`, a damaged log — is a tool failure (ADR-0010 decision 4) whose kind this record does not fix (sub-question ④).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Each front holds the text and the schema of the tools | Two copies to keep equal, and a front would hold something of a tool (ADR-0010 decision 3). |
| 2 | A named subset of JSON Schema that the package checks | See decision 2: a dialect of its own, and the tool function checks again whatever the subset cannot say. |
| 2 | A full JSON Schema validator | A new external dependency: the owner's decision (A-13). |
| 2 | No reserved kind; a refusal has each tool's own kind | A caller and a conformance test could not recognise a refusal, an open step or a defect without knowing the tool. |
| 3 | The data root as a member of the request | The calling agent would choose the tree the tool layer writes to. A later hook would have to compare a path in every request, and both isolation candidates need one write root per actor (ADR-0004 decision 4), which a tree named by the caller would leave to the caller; neither candidate is chosen here. |
| 3 | A context handed to the tool function beside the request | Against the wording of ADR-0010 decision 2 and the landed `tools.call`; binding gives the same without a second argument. |
| 3 | The tool function reads the configuration itself | Every tool would name the loader, and a test could redirect only through the environment; a source it is bound to is given by its caller. |
| 3 | The front loads the data root before every call | See decision 3: a failure and tool knowledge inside a front. |
| 3 | The data root is read once, when the process starts | The two fronts could use two trees after the configuration changed; a broken configuration would stop a server from listing tools that need no tree. |
| 4 | Each tool names these members itself | A hook, a test and an agent would need a table per tool for the same five things. |
| 4 | The identity as one nested member (as the `id` object of a spec is) | A request and the line written for it would name one target in two shapes, and a hook would read one level deeper; the envelope of ADR-0006 is flat. |
| 4 | `execution` defaults to 1 | See decision 4: a part of the identity supplied by the tool layer; two spellings. |
| 4 | The request carries `step` | See decision 4. |
| 5 | `PostToolUse` alone; a `PreToolUse` and `PostToolUse` pair | See decision 5. |
| 5 | In `tools.call`, for every tool | Journaling is not a property of every tool, and the level that looks a name up would have to know which tools spend. |

## Consequences

- **Code slices that can now be cut** (each within the size cap; `hilclaw/tools.py` has 200 lines, `hilclaw/mcp_front.py` 234): ① the registry entry as a tool definition, the reserved kinds, and the list of `hilclaw/mcp_front.py` without its placeholder; ② the data-root source, with `no_data_root`; ③ the path of a journaled tool over `hilclaw/journaled_step.py`, with the three states and the three death points checked through both fronts by a test-only tool. Then the record of the first tool with the mock backend.
- **Docstring sentences that then change**: in `hilclaw/tools.py`, "The table from tool name to tool function" and the signature of `register` (and "Nothing here … reads configuration", if the bound registry is built in that module); in `hilclaw/mcp_front.py`, "a tool is listed without a description, with the input schema `{"type": "object"}`"; in `hilclaw/journaled_step.py`, "It is not a tool and not a hook … where the append is placed stays open (the rest of OD-18)" and "The kind is not reserved …". Today a data root that is no directory would reach a caller as `tool_crashed`.
- **PLAN P2-4 (follow-up for the integrator; PLAN is not edited)**: "PostToolUse 저널링" should read that the two lines of a journaled step are written by the tool layer below the fronts (ADR-0015), and that what a hook journals or verifies beyond them is open.
- **Not edited and now less exact** (follow-ups): ADR-0010 decision 5 ("the front is that caller" — read alone it suggests that the front module runs the loader; see decision 3); ADR-0010 decision 6, last sentence, and its Boundaries ("which tool or hook appends an event"); ADR-0010 Consequences ("the open placement question of decision 6"); ADR-0011 decision 2 ("Whether the appending part … is not chosen here"), its Consequences ("in a hook or below the fronts") and Boundaries "Tools". No sentence of UsageCases became false.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The frame continues the interface between layer 1 and layer 2 (ADR-0010 Consequences) and names no member of a data-plane file: the lines, the envelope and `STATE.json` keep ADR-0006, ADR-0011 and ADR-0012 as they are.

## Boundaries (not decided here)

- **Each tool**: its arguments, result members, failure kinds, `step` value, axes and amounts, whether it is journaled, its time and size limits (PLAN P1-1, P1-8; OD-10, OD-13, OD-2, OD-19; OD-18 sub-question ③).
- **Backends**: what a backend is, how a request or a hw_profile selects one, how one is reached (#5 B-2, A-7 ③, OD-26); the mock backend and its fault injection; board reservation and the recovery of an open step (OD-10, the retry part of OD-17).
- **Rest of OD-18**: which hooks exist and what they check; budget and gate checks (OD-19; OD-3 / #5 A-5 — owner-only); round boundary = process boundary (#8 M4); the invariant list; default-FAIL; the kill switch; sub-questions ① to ③ of ADR-0010; registration of the server (`.mcp.json`, `--mcp-config`, `mcpServers`).
- **Isolation and roster**: the isolation means (OD-8 candidates ① and ②, OD-14); the roster, who may call which tool, any agent's `tools` list (OD-23); the lock and fencing (rest of OD-17); which step commits.
- **Data plane**: any member of a data-plane file; the result files of an attempt; `instance.json`; reading another version (OD-11).
- **Owner-only (DRIVER §9)**: any oracle, tolerance, objective or hw-side value; OD-3, OD-25, C-6, the #5 A and B items.
- **Sub-questions this record raises** (registered under OD-18): ④ what a call answers for a run that cannot be used — no valid `STATE.json`, a damaged log, a stored position beyond the log — and whether the frame reserves a kind for it (with OD-10 and the code slice of the journaled path). ⑤ Whether anything checks that the stated schema of a tool and the check of its function agree, and what Claude Code does with an `inputSchema` (F14).
- Code, tests, CI, packaging and any settings file: later tasks.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-1, FR-3, FR-10, FR-11, FR-13, NFR-1, NFR-4, NFR-6, NFR-7 ①, C-2, C-3, C-7; register rows OD-3, OD-10, OD-14, OD-17, OD-18, OD-19, OD-23.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18), [OD-17](../OpenDecisionProposals.md#od-17), [OD-8](../OpenDecisionProposals.md#od-8) (candidates ① and ②); [StandardScenarios](../StandardScenarios.md); [UsageCases](../UsageCases.md) UC-0, UC-2, UC-3, UC-4.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; *name*, *integer*); [ADR-0002](ADR-0002-od6-codegen-spec.md) (`id`); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 4, 6, 8); [ADR-0006](ADR-0006-od8-events-log.md) (decisions 3, 7, 10); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 2 to 8; F1 to F10); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decisions 2 to 4, 7, 9); [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decision 3).
- #5 A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-5, A-8, B-2.
- #4 body §1, §3a, §3b; roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; candidate ① https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 (discussion, not an owner decision); #7 body §5 G4, G5; #8 M4, M5.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P1-8, P2-4; `hilclaw/tools.py`, `hilclaw/mcp_front.py`, `hilclaw/__main__.py`, `hilclaw/journaled_step.py`, `hilclaw/journal.py`, `hilclaw/run_journal.py`, `hilclaw/config.py`, `hilclaw/layout.py`; tasks T-0037, T-0038, T-0039, T-0040, T-0048, T-0052.
