# ADR-0010: The form in which the FR-10 tools are exposed to layer 1, and the invocation convention (one part of OD-18)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of OD-18** (Open Decisions register in [Requirements](../Requirements.md)): the question #5 A-12 point 1 handed to it — in which form the FR-10 tools of the layer-2 package are exposed to layer 1 — and the invocation convention as far as PLAN P1-1 needs it. The register row keeps its status.
- What stays open of OD-18: which hooks exist and what they check, whether a round boundary is a process boundary (#8 M4), the list of CLAUDE.md invariants, default-FAIL, the kill switch, and the three sub-questions this record raises (see Boundaries).
- It builds on [ADR-0006](ADR-0006-od8-events-log.md) (decision 7 and its boundary "who appends") and on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (binary content is named by hash); the objection windows of both run until 2026-10-14. If either is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- FR-10 exposes the HW experiment tools "MCP/Bash로" and ends with "MCP 서버 vs CLI 노출 형태 = OD-18". #5 A-12 point 1 makes layer 2 the layer-1 agent's toolset, one package `hilclaw/`, and leaves the exposure form "open … decided together with OD-18". The package has modules (`cas`, `artifacts`, `events`, `key_records`, `clang_build`, `local_run`, `harness/`) none of which has a command line or an MCP exposure (the tasks that landed them put both out of scope), so no agent can reach them yet. PLAN P1-1 (tool contract, mock backend, conformance tests) cannot be written before the way of calling a tool is known.
- Fixed inputs. FR-10: the tool names `sim.run`, `board.run`, `profiler.collect`, `correctness.check`; a contract independent of where a backend runs (C-7 ⑤ ⑥); a mock backend always present. C-3: `blob.push` and `blob.fetch`. #5 A-12 point 2: layer-2 languages {Python, POSIX sh, C}; point 3: no tool is created during a run. C-7 ③: orchestrator session → sub-agents → `claude -p`; C-7: the same behaviour on Linux, macOS and WSL. NFR-6: the interface must exclude neither Method A nor later dynamic tool registration. NFR-7 ①: components are replaceable at a round boundary. ADR-0006 decision 7 and #4 §3b: the line of an expensive result is appended by the tool layer, not by an agent.
- `pyproject.toml` declares no runtime dependency, no build backend and no console script, and `requires-python >= 3.11`. The package has two command-line entries of the form `python -m hilclaw.<module>` (`merge_guard`, `driver_state`). A new external dependency needs the owner (CLAUDE.md A-13), so **only forms that the standard library of the pinned Python can implement are open to this record**.
- A discussion comment on #4 (candidate ① of OD-8) argues that the choice "is not a convenience but a security decision": in-process sub-agents would get no Bash and reach privileged actions through typed tools only. That candidate is a registered proposal and **not chosen** (rest of OD-8, OD-14). The integrator memo of [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) compares the two forms and names "both, as two entry points of one package" as a candidate.
- **Facts about Claude Code and MCP** the decisions use. *Verified* = read in the named documentation on 2026-10-07; none was tried in a live session.

| # | Fact | Status |
|---|---|---|
| F1 | A project-scoped MCP server is declared in `.mcp.json` at the project root; a stdio server entry is `command`, `args`, `env`. An interactive session asks for approval before using such a server. | verified — https://code.claude.com/docs/en/mcp |
| F2 | An MCP tool is named `mcp__<server>__<tool>` to agents, permission rules and hook matchers. | verified — https://code.claude.com/docs/en/hooks ("Match MCP tools") |
| F3 | The `tools` frontmatter of a sub-agent is an allowlist of tool names; it accepts a single MCP tool name or `mcp__<server>`. Omitted, the sub-agent inherits the tools of the main conversation, MCP tools included. It names `Bash` as a tool, not a command. A sub-agent definition can also refer to a configured server or define one inline in `mcpServers`; an inline server is connected when that sub-agent starts and disconnected when it finishes. | verified — https://code.claude.com/docs/en/sub-agents |
| F4 | A `PreToolUse` hook receives `tool_name` and `tool_input` (for an MCP tool also `mcp_server`); for Bash, `tool_input.command` is the shell command string. Exit status 2 blocks the call. | verified — https://code.claude.com/docs/en/hooks; task T-0007 |
| F5 | Hooks of the settings files also fire for tool calls made inside a sub-agent; the input then carries `agent_id` and `agent_type`. | verified — https://code.claude.com/docs/en/hooks |
| F6 | A `claude -p` session is a session of its own: without `--bare` it runs the hooks of its project's `.claude/settings.json` and connects the servers of its project's `.mcp.json`, with no approval prompt; with `--bare` only servers passed by `--mcp-config` connect. The documentation announces that `--bare` will become the default of `-p` in a later release. | verified — https://code.claude.com/docs/en/headless |
| F7 | A stdio server is a local process started by the session; Claude Code does not reconnect it automatically. | verified — https://code.claude.com/docs/en/mcp |
| F8 | The stdio transport of MCP is JSON-RPC messages in UTF-8, one per line, on the server's standard input and output; standard error is free for logging; a tool is listed with `name`, `description` and `inputSchema`, called with `tools/call`, and its result carries `content` and `isError`. | verified — https://modelcontextprotocol.io/specification/2025-06-18/basic/transports and `/server/tools` |
| F9 | A foreground Bash command has a default time limit of 2 minutes and a default ceiling of 10 minutes. An MCP tool call has a wall-clock limit of about 28 hours by default (a per-server `timeout` or `MCP_TOOL_TIMEOUT` changes it); a call to a stdio server that sends neither a response nor a progress notification for 30 minutes is aborted by default; a call of the main conversation that runs longer than 2 minutes is moved to a background task, while a call from a sub-agent or in a `-p` session is not by default. Claude Code caps the output it reads back from either form. | verified — https://code.claude.com/docs/en/env-vars, https://code.claude.com/docs/en/mcp ("MCP tool timeouts", "Automatic backgrounding of long tool calls") |
| F10 | That a server written against F8 with the standard library only is accepted by the Claude Code version in use (the protocol revision it negotiates included); whether a `.` is allowed in an MCP tool name; how a `structuredContent` member is shown to the model. | **not verified** |

## Decision

A value below is **cited** when a source or a fact number is named with it; every other value is **this record's own** choice.

### 1. Scope and terms

- This record is about **how a layer-1 agent invokes an FR-10 tool of the package**. It is not the argument list or the result of any tool, not the way a backend is reached, and not a hook.
- **Tool function**: the callable of the package that carries out one tool. **Registry**: the table from tool name to tool function. **Front**: an entry point that makes the registry callable from outside the Python process. **Request** and **result**: what goes into and comes out of one call. **Tool failure**: a call that produced no result.

### 2. Where the contract lives

- **A tool is defined once, as a tool function, at a level that knows no front.** A tool function takes one request and returns one result or raises a tool failure. A request and a result are each **one JSON object** (strict JSON, no non-finite number), so they can cross any process boundary unchanged. Binary content is never inside them; it is named by its hash in the blob store (cited: C-3, ADR-0004 decision 6).
- The contract of a tool — what PLAN P1-1 writes and the conformance tests check — is the contract of its tool function. **A front adds nothing to it**: it decodes a request, looks the name up in the registry, calls, and encodes the outcome (decision 3).
- FR-10's "transport 무관" speaks of where a backend runs; this decision adds the same property on the other side: a tool does not depend on the front through which it was called. Nothing in the convention names a host, a transport or a front.
- **NFR-6.** Method A can call the tool functions directly or connect to the same MCP server; nothing ties them to Claude Code. The registry is a table built when a process starts — in the MVP always the same fixed set (cited: #5 A-12 point 3) — and no front lists tool names of its own, so a later dynamic registration changes the registry and not the fronts; the MCP protocol can announce a changed tool list.

### 3. The exposure forms of the MVP

Compared on the points that differ:

| Point | Typed tool of an MCP server | Command line through the Bash tool |
|---|---|---|
| What a `PreToolUse` hook sees | The tool by name and the request as an object (F2, F4) | `Bash` and a command string; recognising a call inside a shell command is unreliable (`bash -c`, `eval`, variables, aliases — "Known limits" of T-0007) |
| What a per-agent allowlist can express | Single tools, or the server (F3) | The shell as a whole: an agent that can call the tool can run any command (F3). Permission rules of the session can narrow commands by pattern, but they are not per agent and match strings |
| Reaching a `claude -p` child (C-7 ③) | Only when that session is given the server, by its project's `.mcp.json` or by `--mcp-config` — by `--mcp-config` alone once `--bare` is the default (F6) | Whenever the child has a shell and can run the package |
| Cost with the standard library | A loop over JSON-RPC lines with `json` and `sys` (F8); the package follows the protocol itself, with no SDK (F10) | Small; two entries of this kind exist |
| Use by a person, a test or a script | Needs an MCP client | One shell line; runs outside any session |
| A long call | About 28 hours by default, but aborted after 30 minutes without a response or a progress notification; both limits can be set (F9) | 10 minutes in the foreground by default (F9) |

- **Choice: both, as two fronts of the one package over the one registry.** The **MCP front** is a stdio MCP server; **agents call tools through it**, and layer-1 prompts, skills and agent definitions name tools by their MCP names. The **command-line front** is for people, scripts and tests, and for whatever runs outside a Claude Code session.
- **Why agents use the MCP front**: only a typed tool gives a hook the request as data and gives an allowlist a single tool to name. Both are what the registered proposals for enforcement and isolation are written against; this record adopts none of them (decision 6), but the form agents use must not make them impossible.
- **Why not the command line alone**: every agent that calls a tool would need a shell, which candidate ① item 4 excludes for in-process agents. Choosing it would reject that candidate in effect, which is not this record's to do.
- **Why not the MCP server alone**: the whole of P1-1 would rest on F10, which is not verified; tests and CI would need an MCP client to reach a tool; and a person would have no direct way to repeat a call.
- **What keeps the two identical**: for a call that reaches a tool function, a front holds no tool logic, no default, no check and no side effect — everything the call does happens in the tool function. The conformance tests of P1-1 put the same requests through both fronts and compare the outcomes. What a front answers by itself — an unknown tool name, an input that is not a request — it reports in its own way (decision 4); the `kind` values of the command-line front for those cases are the code task's.
- **What reopens this decision**: if the first code task of the MCP front finds that a standard-library server cannot be made to work with Claude Code (F10), the choice of the agents' front is reopened. The alternatives then are an MCP SDK — a new external dependency, the owner's decision (A-13) — or the command line as the agents' front, with decision 6 rewritten. Neither is chosen in advance. The registry, the tool functions and the command-line front do not depend on F10.

### 4. Invocation convention

**Names.** The name of a tool is its FR-10 / C-3 name. The MCP server is named `hilclaw`, and a tool's MCP name replaces each `.` by `_` (whether a `.` is allowed there is not verified — F10):

| Tool | Command-line front | MCP front, as an agent sees it (F2) |
|---|---|---|
| `sim.run` | `sim.run` | `mcp__hilclaw__sim_run` |
| `board.run` | `board.run` | `mcp__hilclaw__board_run` |
| `profiler.collect` | `profiler.collect` | `mcp__hilclaw__profiler_collect` |
| `correctness.check` | `correctness.check` | `mcp__hilclaw__correctness_check` |
| `blob.push`, `blob.fetch` | `blob.push`, `blob.fetch` | `mcp__hilclaw__blob_push`, `mcp__hilclaw__blob_fetch` |

None of these six names contains a `_`, so the mapping is reversible for them. The table shows the mapping, not a list this record closes: which tools exist beyond FR-10 and C-3 is not decided here, and a later tool name that contains a `_` reopens the mapping.

**Command-line front.** One command of the package with the tool name as its only argument — for example `python -m hilclaw sim.run`; the spelling before the name is the code task's (no console script exists — cited: `pyproject.toml`).

- The request is read from **standard input**: one JSON object in UTF-8, to the end of input. It is not passed as arguments, so no shell quoting touches it.
- **Exit status 0** means a result: standard output holds exactly one JSON object and one LF.
- **Any other exit status** means a tool failure: standard output holds one JSON object `{"error": {"kind": …, "message": …}}` and one LF. An unknown tool name and a standard input that is not one JSON object are reported in this same way, although no tool function was reached. Standard output is empty only when the front could not report at all (it was killed, or the interpreter failed to start it). The non-zero values are the code task's.
- **Standard error** is free text for a reader and is never parsed.

**MCP front.** A stdio server (F8), started by Claude Code for the session or the sub-agent it is given to (F1, F3, F6); its module name and the way it is registered are later tasks'.

- A tool is listed with its MCP name, a description and an input schema (F8); the content of both is each tool's (P1-1).
- The request is the `arguments` object of `tools/call`.
- A result is returned with `isError` false and **one text block that holds the result as JSON text**; a tool failure with `isError` true and one text block holding the same error object as above. Whether `structuredContent` is sent as well is the code task's (F10).
- What never reaches a tool function — an unknown tool name, a malformed message — is answered as the protocol requires (a JSON-RPC error).
- The server writes nothing but protocol messages to its standard output (F8), so **a tool function never writes to standard output**; diagnostics go to standard error under both fronts.

**Result or tool failure.** A **result** says what the experiment or operation established, **its failure included**: a candidate that fails verification, a measurement that did not converge and whatever else a tool's contract defines as an outcome are results. A **tool failure** says that no outcome was established — the request was refused, or the tool could not do its work. `error.kind` is a *name* in the sense of ADR-0001 and `error.message` a string; this record fixes the form and **no list of kinds**. Which situations of a tool are results and which are failures, the kinds, and what a caller does after either (retry, triage) belong to each tool's contract and to OD-10.

### 5. Configuration and data root

Nothing new is decided. A front obtains the data root as the existing loader gives it: `hilclaw.config.load_data_repo()` reads `hilclaw.config.json` at the root of the source checkout the package was loaded from — not the working directory — with the overrides `HILCLAW_DATA_REPO_URL` and `HILCLAW_DATA_REPO_LOCAL_PATH`. The modules below keep taking `data_root` from their caller and reading no configuration, as their docstrings say; the front is that caller. Tests and a person redirect a call with the existing variables.

### 6. What follows for enforcement and isolation

**No isolation means, no hook, no gate and no allowlist is adopted or rejected by this record.** The following are consequences of decision 3, stated so that those decisions can be taken later.

- **Under OD-8 candidate ①** (item 4: no Bash for in-process agents): possible. Such an agent can be given single tools by MCP name in its `tools` list (F3) and needs no shell to run an experiment. The command-line front opens nothing for an agent without a shell.
- **Under OD-8 candidate ②** (scratch copy, diff import): possible, and indifferent to the form. A coder working in a scratch directory has no `hilclaw` server unless its session is given one (F6).
- **A `claude -p` child** has the hooks and servers of its own session, not its parent's (F6; this agrees with the correction recorded in the #4 comment). Whether a coder is given any tool is OD-23 and the rest of OD-8.
- **A later hook** (rest of OD-18, PLAN P2-4) can match one tool or `mcp__hilclaw__.*`, read the request as `tool_input`, tell the calling sub-agent by `agent_type` (F4, F5), and block with exit status 2. It **cannot** see a call made through the command-line front except as a Bash command string.
- Therefore a check that must hold on every path has two possible places — a hook on the typed tool, together with no shell for the agents concerned, or the tool layer below the fronts. The same holds for the append of ADR-0006 decision 7: an append performed by a hook would not happen for a command-line call. **Where a check or the append is placed is not decided here.**

### 7. Versioning and change

- The convention carries **no version member**. Both fronts, the registry and the tool functions are parts of one package at one source commit, and in P1 that commit is the pin (cited for the harness: OD-11 confirmed part, #5 A-12 point 4; that the same commit pins the rest of the one package is this record's reading). A change of the convention is a change of the source and of this record. The `serverInfo` the MCP protocol asks for is not a pin.
- **NFR-7 ①.** A command-line call is a new process that loads the source as it is at that moment. An MCP server process lives as long as what it was given to — the session, when it is registered in `.mcp.json` or passed by `--mcp-config`; one sub-agent, when it is defined inline in that agent's `mcpServers` (F1, F3, F6). It runs the code it loaded at its start and is not restarted or reconnected by Claude Code (F7). A replaced tool layer therefore takes effect for agents only when the server process is replaced. Which of these ways is used is not decided here.
- This record requires one thing of the server so that it can be replaced at any call boundary: **the outcome of a call does not depend on state the server process kept from an earlier call**; what a later call needs is in the data plane. A connection or a cache that can be built again is not such state: how long a connection to a backend lives, and a reservation or a lock of a board, are #5 B-2, OD-10 and OD-17 and are not restricted here. Whether a round boundary is a process boundary — which would also replace the server — is #8 M4 and stays open; whether a tool checks its own commit against the one a run recorded is OD-11.

### 8. Limits

- **No access control.** A front authenticates nobody: whoever can start the command or connect the server can call every tool. Who may call what is OD-23; the isolation means is OD-8 and OD-14.
- **An agent with a shell can use the command-line front**, unseen by a hook on the typed tools (decision 6). Whether such agents exist is OD-23 and OD-8 (sub-question ②).
- **No budget, gate or duplicate check**, and no protection against two concurrent calls (OD-19, OD-3, OD-17, C-2).
- **No time limit and no size limit of a call are decided.** The limits Claude Code applies to each form (F9) are not chosen here. A call to the MCP front that runs longer than the idle window is aborted unless the server sends progress notifications or the window is raised, and only a long call of the main conversation is moved to the background — the callers of an experiment are mostly sub-agents and `-p` sessions, to which that does not apply; what the server does about either is open. A result is expected to stay small because binary content travels by hash (sub-question ③; OD-14, OD-10).
- **The MCP front is not proven** in a live session (F10, sub-question ①), and without an SDK the package has to follow revisions of the protocol by itself.
- **Registration is not done or chosen by this record**: an agent has no tool until the server is given to its session or to the agent itself — `.mcp.json`, `--mcp-config` or `mcpServers` (F1, F3, F6) — and, for a project-scoped server in an interactive session, approved (F1).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Each front implements its tools separately | Two contracts to keep equal, and "transport-independent" would hold for neither. |
| 3 | MCP server only | See decision 3: P1-1 would rest on F10 alone; no direct path for tests, CI and people. |
| 3 | Command line through Bash only | See decision 3: a shell for every calling agent, a hook that parses command strings, and candidate ① item 4 made impossible. |
| 3 | Both fronts, and agents use the command line | Keeps the costs of "command line only" for agents while paying for the server too. |
| 3 | An MCP server built on an MCP SDK | A new external dependency: the owner's decision (A-13). It becomes a question only if F10 fails. |
| 3 | An HTTP MCP server | A listening port and a process to supervise for a tool layer that runs on the orchestrator's machine; stdio needs neither. |
| 4 | The request as command-line arguments or as a file path | Shell quoting and length limits for arguments; a file needs a path and a writer rule in a tree where no scratch location is decided (rest of OD-8). |
| 4 | The dotted FR-10 name as the MCP name | Not verified to be accepted (F10); a name the allowlists and matchers are written against should not depend on it. |
| 4 | Exit status alone for a tool failure, the reason on standard error | An agent would have to parse free text to tell a refused request from a backend that is down. |
| 4 | A failed experiment reported as a tool failure | The outcome of a spent experiment would arrive as "no result": FR-1 routes a failed candidate by its result. |
| 7 | A version member in every request and result | Both sides are one commit of one package; the member could only repeat the commit or disagree with it. |

## Consequences

- **P1-1 becomes code slices**, each within the size cap: ① the registry, the tool failure type and the command-line front, with one tool that needs no undecided contract; ② the MCP front over the same registry (standard library only), which also settles F10; ③ the mock backend; ④ the conformance tests, run through both fronts; then one tool at a time. Each slice judges which of OD-10, OD-13 and OD-23 it touches.
- **Registration** — by which way of F1, F3 and F6 the server is given to a session or an agent, for example a `.mcp.json` at the repository root with the approval of F1 — is a later task and partly an owner action; `.claude/settings.json` is not involved in exposing a tool.
- **P2-2 / P2-3 inherit** tool names an agent definition can list one by one (`mcp__hilclaw__…`), so "an evaluator that only calls the harness" or "no Bash for an in-process agent" is expressible; whether to do so is theirs (OD-23, OD-16, OD-8).
- **P2-4 inherits** a typed request to check before a call and a typed outcome after it, the caller's `agent_type`, and the open placement question of decision 6.
- **Existing modules** are consistent and unchanged: they take `data_root` from the caller, read no configuration and print nothing to standard output; `merge_guard` and `driver_state` stay separate entries and are not tools.
- **FR-10 wording (follow-up for the integrator, not edited here)**: once the objection window has passed, "MCP 서버 vs CLI 노출 형태 = OD-18" should read that the form is fixed by ADR-0010 — a stdio MCP server for agents and a command line for people and scripts, two fronts of the one package; #5 A-12 point 1 likewise. No sentence of UsageCases became false.
- **A-13 reading**: no code, no dependency, no settings file, no data-plane file or field changes. The request / result convention is an interface between layer 1 and layer 2, not a data-plane schema.

## Boundaries (not decided here)

- **Rest of OD-18**: which hooks exist and what they check; round boundary = process boundary (#8 M4, UC-3 `/loop`); the CLAUDE.md invariant list; default-FAIL; the kill switch. **Gates** — the gate layer and the gate list — are OD-3 / #5 A-5, owner-only.
- **Isolation and roster**: the isolation means (OD-8 candidates ① and ②, OD-14); the agent roster, who may call which tool, the `tools` list of any agent, whether `coder.run` exists (OD-23, PLAN P2-2 / P2-3).
- **Each tool**: its arguments, result members, failure kinds and retry; the mock's fault injection; event kinds and payloads, and which tool or hook appends an event (PLAN P1-1, P1-8; OD-10, OD-13, OD-17, OD-19).
- **Backends and references**: how a backend is reached — local, LAN, SSH (#5 B-2, A-7 ③); the external-reference MCP adapters, which are a different use of MCP (OD-12, FR-14).
- **Owner-only (DRIVER §9)**: any oracle, tolerance, objective or hw-side value; OD-3, OD-25, C-6, the #5 A and B items.
- **Sub-questions this record raises** (registered under OD-18): ① whether a standard-library MCP server works with Claude Code in a live session (F10) — settled by the first code task of the MCP front; ② whether an agent that holds a shell may call the command-line front, which a hook on the typed tools does not see (with OD-23, OD-8, PLAN P2-4); ③ the time limit and the result size of a call under each front — for the MCP front also whether the server sends progress notifications or the idle window is raised for a long call, and what automatic backgrounding means for the caller (with OD-14, OD-10).
- Code, tests, CI, packaging (`pyproject.toml`, console scripts, `.mcp.json`) and any settings file: later tasks.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-1, FR-9, FR-10, FR-11, NFR-2, NFR-4, NFR-5, NFR-6, NFR-7 ①, C-3, C-5, C-7; register rows OD-3, OD-8, OD-10, OD-11, OD-12, OD-14, OD-17, OD-18, OD-19, OD-23.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (the two "흡수" bullets, the integrator memo), [OD-8](../OpenDecisionProposals.md#od-8) (candidate ① items 2, 4, 5; candidate ②), [OD-14](../OpenDecisionProposals.md#od-14), [OD-23](../OpenDecisionProposals.md#od-23); [UsageCases](../UsageCases.md) UC-0, UC-2, UC-3.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; *name*); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 6); [ADR-0006](ADR-0006-od8-events-log.md) (decisions 7, 10; Boundaries "who appends"); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decision 1: "not an FR-10 tool contract").
- #5 A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-5, B-6.
- #4 body §3a, §3b; roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; candidate ① https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 (discussion, not an owner decision) ; #7 body §5 G5 and comment 5139423949 §2(8); #8 M4.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P2-2, P2-3, P2-4; `pyproject.toml`; `hilclaw/config.py` (`load_data_repo`), `hilclaw/merge_guard.py`, `hilclaw/driver_state.py`, and the module docstrings of `hilclaw/events.py`, `hilclaw/artifacts.py`, `hilclaw/cas.py`, `hilclaw/local_run.py`, `hilclaw/harness/timing.py`; tasks T-0007, T-0026, T-0037.
