---
id: T-0384
title: Write the ADR that records the owner's answer to HQ-0040 (form (T)) and designs the registry tool `coder.run` of a first-case turn - its request, result and kinds over `hilclaw.coder_call.call`, its place in `default_registry` while the coder's container start (slice (d)) is still open, how a call longer than the MCP idle window is kept alive or bounded, and what the coder-driver definition and the Round-Manager's delegation step become (part of OD-23, PLAN P2-2)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-5, OD-23, OD-18, OD-14, NFR-4, S0, S1]
dependsOn: [T-0346]
touchesFiles:
  - ARCHITECTURE/decisions/          # one new record, the next free number at execution time (ADR-0141 at planning time; ADR-0068, ADR-0074, ADR-0088, ADR-0132 and ADR-0137 are held by the unlanded branches of T-0210, T-0231, T-0264, T-0361 and T-0375)
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-2 (the coder-driver, "OD-23 종결 필요(§9 ADR 경로)") is a checklist item. In the P2 order of the PLAN P2 head it comes before P2-5, so the D18 rule for work outside the checklist does not apply. P2-5's first run cannot have a round without a coder call.

ADR-0126 landed the function that performs a first-case coder call (`hilclaw/coder_call.py`, `call(request, *, source, runtime)`). It left one point to the owner as Q1 (HQ-0040): does the coder-driver reach that function through Bash or as the registry tool `coder.run`? Until that was answered, ADR-0126 decision 3 allowed neither front, and "no agent can reach the function" (ADR-0126 Consequences, "The cost, plainly"). ADR-0139 decision 9 and `hilclaw/turn_permissions.py` wait on the same answer.

The owner answered on 2026-10-21 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6306222689): "(T): the coder-driver reaches the coder-call function as the registry tool `coder.run` through the MCP front. The coder-driver has no Bash. K4 supersedes K2's 'Bash → claude -p' for the coder-driver; a coder call that outlasts the MCP idle window is a design point of the record that adds `coder.run` (server timeout or progress notifications). This unblocks planning of the `coder.run` front, `orchestration/agents/coder-driver.md` and the coder step of `round-manager.md`."

The owner chose the form. The design of the tool is a design-level part of OD-23/OD-18, and that design is driver-closable (DRIVER §9). It includes the owner-named point about the idle window. The record is therefore written first, in this task, and the code slices follow it. The record needs no open HQ:
- HQ-0053 (how the sign-in reaches the coder's container, owner-only, T-0375/ADR-0137 unlanded) blocks slice (d), the real runtime. It does not block the front. The record must stay inside what holds while slice (d) is absent.
- HQ-0042 holds the runtime acceptance items (xii)-(xiv) of ADR-0126. They stay open and are not needed here.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming convention, D4 size cap) and §9 (ADR path for a design-level OD; owner-only items).
- `CLAUDE.md` sections "미결은 발명하지 않는다", "문서 커버리지 재검사", "브랜치·merge 절차", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (document-mode checks).
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`, the whole record (144 lines). It is the base. Pay most attention to decision 3 (the function's request, result and kinds in order), decision 6 (the definition's fixed rule), decision 7 (not journaled), Consequences items "Code slices it enables" 2 and "How long the coder-driver can wait for one call", and the runtime acceptance items (xii)-(xiv).
- `hilclaw/coder_call.py` lines 1-200 (the module docstring, `FAILURE_KINDS`, the `runtime` seam with `available()` and `run(scratch_root, coder_model=...)`, and `call`'s docstring). Code statements in the record are observations, phrased as earlier records phrase them.
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: the facts table row F9 (line 30), decisions 3 and 4 (lines 49-99), the "A long call" row (line 60) and line 125 ("No time limit and no size limit of a call are decided").
- `hilclaw/mcp_front.py` lines 1-40 and the `_call`/`_result` functions (lines 104-147). The front handles one message at a time and sends no notification today.
- `hilclaw/tools.py` lines 182-258 (`default_registry(data_root_source)` and how each tool is registered with its description and input schema).
- `hilclaw/turn_loop.py` around `SERVERS_MEMBER` (line 135): the server entry a turn session gets by `--mcp-config` (ADR-0118 decision 6, `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md` lines 114-123).
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md` decisions 3, 5 and 9 (lines 59-66, 74-80, 100-104), and Boundaries. Under (T) its derivation pre-approves `mcp__hilclaw__coder_run` from the agent file "with no change of this record or of the code".
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md` decisions 3 and 4 (lines 62-86). The coder-driver writes the spec with `spec.write` before the call. Decision 4 is written "under either answer to HQ-0040".
- `ARCHITECTURE/decisions/ADR-0136-od8-first-case-coder-model.md`, decisions 5 and 7 only (the `coder_model` read inside the call and its hand-over to slice (d)).
- `orchestration/round-manager.md` "The round steps" (lines 87-107) and `orchestration/agents/evaluator.md` (the form of an existing agent definition).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - § OD-23 (lines 400-426);
  - § OD-14 (from line 222), for the call's time limit;
  - § OD-18 (from line 278): find sub-question ② by searching for "셸을 가진 에이전트".
- `ARCHITECTURE/Requirements.md`: the register's "행 형식" (line 84) and rows OD-14 (line 105), OD-18 (line 109) and OD-23 (line 114).
- `ARCHITECTURE/StandardScenarios.md`: the check rules (around line 26) and the first paragraph of §검사 결과 (from line 168).
- Official Claude Code documentation on MCP tool timeouts and progress notifications: https://code.claude.com/docs/en/mcp ("MCP tool timeouts") and https://code.claude.com/docs/en/env-vars (`MCP_TIMEOUT`, `MCP_TOOL_TIMEOUT`). Also the MCP specification revision 2025-06-18 on progress (`_meta.progressToken`, `notifications/progress`). Read them; do not run anything.

## Acceptance Criteria

1. **One new record** `ARCHITECTURE/decisions/ADR-NNNN-od23-first-case-coder-run-tool.md` (the next free number; the slug may differ).
   - Structure as in ADR-0126 and ADR-0140: Status, Context, Decision, Walk-through, Alternatives considered, Consequences, Boundaries, References.
   - Status says it is accepted under DRIVER §9, that the owner has not confirmed the design, and what it builds on. The form (T) itself is the owner's decision: cite it with the HQ-0040 answer link above and mark it as such, apart from this record's own design.
   - Scope: the runs of ADR-0120 decision 1, as ADR-0126 has it.
2. **The decision answers each of these. For each, it weighs the alternatives and states the choice:**
   - (a) **The tool.** Its registry name `coder.run` and MCP name `mcp__hilclaw__coder_run` (ADR-0010 decision 4, as ADR-0126 decision 3 named them). It performs `hilclaw.coder_call.call` and adds nothing to the call's contract: the request members, the result and the kinds in the order of ADR-0126 decision 3 and `FAILURE_KINDS` stand, cited and not restated. Say that it is not journaled (ADR-0126 decision 7) and that it writes nothing of the data plane except what the bring-in writes. Leave the description and the input schema to the code slice, as ADR-0140 did for `timings.compare`.
   - (b) **The runtime the registered tool gets while slice (d) is absent.** `call` needs a `runtime` object, `default_registry` takes only a data-root source, and the real runtime waits for HQ-0053 and the unlanded ADR-0137. Weigh at least these three:
     - register now with a runtime that reports no container runtime, so that every call that passes the checks fails with `no_container_runtime`;
     - let the registry builder take a runtime, with none given by default;
     - register only when slice (d) lands.

     Say what P2-5's stub-`claude` verification then needs (a stub runtime given by tests only, D16). Do not design slice (d): no image, no container flag, no sign-in, no prompt text and no permission mode of the coder's `claude -p` (ADR-0126 "Open parts of the start"; HQ-0053).
   - (c) **The MCP idle window**, the point the owner assigned to this record. F9 says that a stdio-server call that sends neither a response nor a progress notification for about 30 minutes is aborted by default, and that a per-server `timeout` or `MCP_TOOL_TIMEOUT` changes the wall-clock limit. Weigh at least two means:
     - progress notifications from the front during a `coder.run` call, against what the single-threaded front of `hilclaw/mcp_front.py` does today and against how a request carries `_meta.progressToken`;
     - a server-level timeout setting in the `--mcp-config` entry that `hilclaw/turn_loop.py` writes, or an environment variable of the turn session.

     Check each documented behaviour against the official pages listed in Required Reading, and cite the page and section. A behaviour the pages do not establish is not assumed: it becomes a runtime acceptance item (see 5). Keep apart what this record decides (how the session is kept from cutting off a long call) and what it does not decide (the time limit of a coder call itself, OD-14 / ADR-0126 "Open parts of the start"). If the chosen means needs a front change that shifts the protocol behaviour other tools see, say so and confine it.
   - (d) **The coder-driver definition** `orchestration/agents/coder-driver.md` for the code slice. Its `tools` list holds exactly `mcp__hilclaw__spec_write` (ADR-0138) and `mcp__hilclaw__coder_run`, and no `Bash` (owner answer). Say whether it holds anything else, such as read tools, and why. Its fixed rule is ADR-0126 decision 6, together with the order spec write, then call, from ADR-0138. Confirm against ADR-0139 decisions 3, 5 and 9 that the permission derivation carries the new entry with no change. If it does not, say what changes.
   - (e) **The Round-Manager's delegation step** in "The round steps" of `orchestration/round-manager.md`: what the code slice may write now. The steps of round 0 are only partly defined, and the record does not define the rest of a round. Where the step sits relative to the present stop after step 1, and what the Round-Manager does with each result or failure kind the coder-driver reports, is decided only as far as ADR-0126, ADR-0138 and ADR-0119 (the first-case baseline) already allow. Anything beyond is left open and named.
3. **The record does not answer, and writes as open:**
   - slice (d) and everything in ADR-0126 "Open parts of the start" (HQ-0053; ADR-0137 unlanded);
   - the time limit of a call (OD-14);
   - the coder's token budget and usage report (#5 A-8, HQ-0041 (2));
   - calls that do not end normally and repair calls (OD-19);
   - N > 1 (OD-29), and a second call for one tuple (OD-23 ① (가));
   - hooks (OD-18, PLAN P2-4);
   - the rest of the roster.

   If an answer to any of these turns out to be needed, stop and return BLOCKED. If the point is owner-only (DRIVER §9), propose the question in the Result.
4. **No data-plane change.** No member, file, kind of a data-plane file, value or version is added or changed. If the design cannot be completed without such a change, stop and return BLOCKED (CLAUDE.md A-13).
5. **Consequences** lists the following:
   - **The code slices** for the planner. Each is in code mode, tested only with stub runtimes and stub `claude`, never a real `claude` (D16), and each is within the D4 cap. For example: the registration of `coder.run` with whatever the idle-window means needs in `hilclaw/tools.py` / `hilclaw/mcp_front.py` / `hilclaw/turn_loop.py`; then `orchestration/agents/coder-driver.md` with its test; then the delegation step of `orchestration/round-manager.md`.
   - **What is now less exact**, listed and not edited. At least:
     - ADR-0126 decision 3 "Until Q1 is answered …", Consequences Q1, "The cost, plainly" and Boundaries;
     - ADR-0139 decision 9 (B branch) and Boundaries;
     - ADR-0138 decision 4;
     - the `hilclaw/coder_call.py` docstring ("Nothing calls it yet", "either front of ADR-0126 decision 3 (Q1)");
     - the `hilclaw/turn_permissions.py` docstring ("Not done here: the coder-driver's entry (ADR-0139 decision 9, HQ-0040)").
   - **How OD-18 sub-question ② stands for the coder-driver.** Under (T) the coder-driver has no shell, so the question does not arise for it. Say so, and leave the question open for any other agent.
   - **Runtime acceptance items.** Name whatever this record adds, numbered from (xli) on in the turn-session series; for example, that a call longer than the idle window survives under the chosen means. State which of ADR-0126's (xii) and (xiii) become narrower under (T). The executor names the new items in the Result so that the driver can notify them through the HQ path with reason `runtime-acceptance` (DRIVER §8). If nothing in the record rests on a live session, it adds none and says so.
6. **Register edits follow the rules written in each register file, not the wording of earlier task files:**
   - `ARCHITECTURE/Requirements.md`: apply the "행 형식" paragraph (line 84) to row OD-23, and to OD-18 / OD-14 only if the record answers part of them. The new ADR is one more link under `**확정분**:`. The owner's part is marked as that paragraph prescribes for owner decisions. The open text under `**잔여**:` is rewritten where it stands: at least "coder-driver가 그 함수에 닿는 형태(…)" is no longer open. Nothing the record says is copied into the row.
   - `ARCHITECTURE/OpenDecisionProposals.md`: apply the header's "기록 규칙" (line 8). Each section the record answers part of gets one `채택분` line. The end state of each sub-question it touches is rewritten in place, and the question's wording stays. In § OD-23 the open-part sentence that names "`coder.run`의 존재" is rewritten.
   - `ARCHITECTURE/StandardScenarios.md`: recheck coverage by its check rules (CLAUDE.md "문서 커버리지 재검사"). Touch §검사 결과 only as its first paragraph prescribes.
7. **Document mode** under CLAUDE.md A-13: a context-isolated reviewer cycle (dev-item-address steps 10-12), a rebase on `origin/main`, and a direct push to `main` with the trailer `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0384`. No file outside `touchesFiles` changes. In particular, no file under `hilclaw/`, `tests/`, `orchestration/` or `PROCESS/` changes, and `.claude/settings*.json` is not touched.
8. **D16.** No real `claude` is started in any form, no container runtime is started, and nothing is required of the development machine.
9. **The Result** names: the commit, the review rounds, the ADR number, the runtime acceptance items added (or "none"), the less-exact list, and the code slices in the order the planner should take them.

## Out of Scope

- Any code: the registration of `coder.run`, front changes, `orchestration/agents/coder-driver.md`, `orchestration/round-manager.md`. These are later code slices.
- Slice (d), the real container and coder start (HQ-0053, the T-0375 branch).
- The widening of ADR-0127 decision 8 and `run.commit` that the owner's HQ-0043 answer unblocks. That is a separate record for the planner.
- Editing the "Less exact, not edited" sentences of any earlier ADR or docstring.
- Anything from the unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0361-*`, `claude/T-0375-*`, and from draft PR #186 (T-0324, `hilclaw/start_instance.py`). Overlap note: T-0210 touches the OD-18 lines and T-0361 the OD-23 lines of the two registers. If either lands first, rebase onto it and keep both edits.

## Follow-ups

- The code slices that the record's Consequences lists (planner, after landing).
- The record that widens ADR-0127 decision 8 and `run.commit` by the owner's HQ-0043 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6306369119), PLAN P2-4 / P1-8 area (planner).

## Result

DONE (2026-10-21). Document mode: landed on `main` as 3815c42 (rebased on decc5bd, pushed fast-forward; branch deleted), `Reviewed-by: reviewer agent (7 rounds, Approve)`.

- **Record**: `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`. It cites the owner's form (T) as O1, apart from its own design. The tool `coder.run` adds nothing to the contract of ADR-0126 and ADR-0136. It is registered now, bound to a package runtime that reports no container runtime until slice (d) replaces that binding; tests bind a stub runtime through `mcp_front.main(registry=...)`. The turn session's environment gets `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=0` and `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, and loses `CLAUDE_AUTO_BACKGROUND_TASKS`. The record weighed and rejected progress notifications, a per-server `timeout`, a settings-file `env` and a prompt-only wait. No time limit is chosen (OD-14). The coder-driver's `tools` are exactly `mcp__hilclaw__spec_write` and `mcp__hilclaw__coder_run`: no Bash, no read tools, no `background`. On `spec_exists` the interim rule is: no call. The Round-Manager gets a round-0 step 2 (delegate 0/1/1, wait, report) that ends at the present stop.
- **Registers**: Requirements OD-23 and OD-18 rows; OpenDecisionProposals § OD-23 and § OD-18 (sub-question ③ partly answered, bullet head "일부 답함"); StandardScenarios rechecked for S0 and S1, with no verdict change and no gap.
- **Runtime acceptance items added** (notify by the HQ path, reason `runtime-acceptance`):
  - (xli) A `coder.run` call from the coder-driver in a `-p` turn session with `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT=0` is not aborted after 30+ silent minutes. This assumes managed settings do not set the variable and item (xl) holds.
  - (xlii) With `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` (and `CLAUDE_AUTO_BACKGROUND_TASKS` removed), the delegation to the coder-driver runs in the foreground and reports in the same turn. The sub-agent stall timer (`CLAUDE_ASYNC_AGENT_STALL_TIMEOUT_MS`) does not abort the coder-driver while its call is pending.
  - (xliii) While the single-threaded front serves a long call, the session neither aborts it nor marks the server failed because of other requests it sends, such as `ping`.
  - Narrowed: ADR-0126 (xii) now covers the MCP form only. (xiii) now covers the MCP limits only; its idle part is (xli).
- **Less exact, not edited**:
  - ADR-0126: decision 3, decision 6, Consequences Q1, slice 2, "How long…", items (xii) and (xiii), "The cost, plainly", Boundaries, and the Walk-through row "No container runtime".
  - ADR-0139: decision 9 (B branch), decision 3 ("`spec.write` until a coder-driver exists"), slice 2, Boundaries.
  - ADR-0138: decision 4 and "in the form HQ-0040 gives".
  - ADR-0136: decision 5's (B) reading and its Boundaries.
  - ADR-0118: decision 6, R7 and item (v), and the `hilclaw/turn_loop.py` docstring ("environment … unchanged").
  - ADR-0010: decision 8.
  - ADR-0128: slice 4.
  - `hilclaw/coder_call.py` docstring: "Nothing calls it yet", "(Q1)", and the `available()` sentence.
  - `hilclaw/turn_permissions.py` docstring: "Not done here: the coder-driver's entry".
- **Code slices, in the planner's order** (each code mode, stub runtimes and stub `claude` only):
  1. The `coder.run` definition, registered in `default_registry` with the no-container runtime, plus tests and docstrings.
  2. The three environment changes in `hilclaw/turn_loop.py`, plus a test.
  3. `orchestration/agents/coder-driver.md`, plus a test (no `background` member).
  4. Round-Manager step 2 in `orchestration/round-manager.md` and the moved stop, plus a test.
- **Cost stated in the record**: a run whose round 0 runs before slice (d) never gets a round-0 coder call (rule 4) until OD-23 ① (가) and OD-8 ㉖ (가) are answered.
- No BLOCKED reason; the runtime acceptance items above are recorded by the driver as HQ-0056 (runtime-acceptance, non-blocking).
