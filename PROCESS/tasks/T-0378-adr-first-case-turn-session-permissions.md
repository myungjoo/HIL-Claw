---
id: T-0378
title: Write ADR-0139 - how a first-case turn session is given its permissions (permission mode, the pre-approved tools of the main session and of the evaluator, what narrows the built-in tools, and which settings sources it reads), so that the turn loop can pass them (part of OD-18 and OD-23; ADR-0118 item (vii); PLAN P2-1/P2-4)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-18, OD-23, FR-1, NFR-4, C-7]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager, round 0) and P2-4 (hooks and enforcement of a turn session, OD-18) are checklist items. They come before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply. If that reading is disputed: without this record, no turn session of P2-5's run, of the nightly run of P2-10 or of P2-14 can call a single tool, so the work is needed for both goals anyway.

The turn loop (`hilclaw/turn_loop.py`, ADR-0118 decision 3) starts every turn as `claude -p <prompt> --mcp-config <file> --strict-mcp-config` and nothing else. Its docstring says: "No permission, model, turn-limit, setting-source or bypass option is passed: how a turn session is given its permissions is not decided (ADR-0118 decision 4, "Workspace trust")". ADR-0118 decision 4 states the gap. A `-p` session never shows the trust dialog, and in a directory never trusted it does not use the `permissions.allow` rules of the directory's `.claude/settings.json` (its R10). "How a turn session is given its permissions and the agents' allowlists is not decided." Runtime acceptance item (vii) of ADR-0118 waits on "whatever means a later record picks".

The registers say the same. The OD-18 remainder lists "그 도구들을 부를 권한(OD-23과 함께)". The proposal text of § OD-18 says the permission to call those tools in a `-p` session was not decided.

Since then every record of the first-case turn has named its tools: ADR-0124, ADR-0127, ADR-0133, ADR-0134, ADR-0135 for the Round-Manager, and ADR-0128, ADR-0129, ADR-0131 for the evaluator. Each of them leaves "Permissions, allowlists beyond the `tools` list, and hooks of a turn session" open (for example ADR-0131 Boundaries). Several of them keep "not Bash or file tools" by a prompt rule only. The runtime self-check already settled a narrow, prompt-free permission setup for its one throwaway `claude -p` (ADR-0054 decision table, landed as ADR-0057 in `hilclaw/selfcheck_session.py`), so the documented means and one precedent exist.

This is a design-level part of OD-18 (and of OD-23), not owner-only (DRIVER §9). Under DRIVER §6 and §9 this task writes the ADR in document mode. The code slice that passes the chosen options in `hilclaw/turn_loop.py` follows as a separate code task.

What this task does not depend on:
- **HQ-0040** (whether the coder-driver reaches the coder call through Bash or as a registry tool) is unanswered. The coder-driver definition does not exist yet. The record therefore covers the main session and the evaluator, and states only how the coder-driver's entry is added once HQ-0040 is answered. It chooses neither (B) nor (T).
- **HQ-0053** (the coder's sign-in) and the unlanded ADR-0137 (the coder's own `claude -p` inside its container) concern a different session and are not touched.
- No `claude` is started and nothing is required of the development machine (D16). Facts that only a live session can show become runtime acceptance items.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §1-5: the forbidden actions; a denied or failed tool call is BLOCKED and is not worked around.
  - §2 (document mode).
  - §3-5: the executor procedure, the resume rule and the time limit.
  - §5: naming (branch `claude/T-0378-<slug>`, the trailer `Task: T-0378`), the size cap, and the task format.
  - §8 and §9: OD closure by ADR, the owner notice, the owner-only list.
  - §11 rows D16 and D17.
- `CLAUDE.md`: all rules. In particular:
  - "미결은 발명하지 않는다";
  - "세션 진입 점검";
  - "문서 커버리지 재검사";
  - "개발 드라이버와 런타임의 구분" (D16). The driver's own `.claude/settings.json` is not the runtime's and is not edited.
  - the A-13 document-mode procedure and its BLOCKED reasons.
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole).
- **The record format**: `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` § "Record format" (from line 146). For the shape of a recent record (Status with the owner-sentence search, cited versus own content, Walk-through, Alternatives, Consequences, Boundaries), use `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`.
- **The gap and its frame**: `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`, whole. In particular:
  - the facts table (R1 to R10, especially R10, lines 30-46);
  - decision 4 (lines 91-105, "Workspace trust" at line 103);
  - decisions 5 and 6;
  - Consequences items (i) to (vii) (lines 160-167);
  - Boundaries.
- **The precedent**:
  - `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md`: the owner sentences O1 to O8 (lines 16-25), facts K5 to K7 (lines 34-36), and the option table (lines 80-86).
  - `ARCHITECTURE/decisions/ADR-0057-od18-runtime-self-check-as-landed.md` (the values taken, items (ix) and (x)).
  - The module docstring of `hilclaw/selfcheck_session.py`.
  - The owner's HQ-0006 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6135246858), which sets "never with a bypass flag" for the self-check and, under (b-1), the options of the owner's check by hand.
- **The tools each agent is meant to call** (cite, do not restate):
  - ADR-0124 decision 2; ADR-0127 decision 2; ADR-0133 decision 6; ADR-0134 decisions 2 and 3; ADR-0135 decisions 2 and 6. These are the Round-Manager's tools.
  - ADR-0128 decisions 2, 4 and 7, with ADR-0129 and ADR-0131. These are the evaluator's tools and its unrestricted reading.
  - ADR-0138 decision 3 and item (xxxiii): `spec.write` for the coder-driver.
  - ADR-0126 (the coder-driver; HQ-0040).
  - ADR-0010 decisions 3, 4 and 6: the MCP names `mcp__hilclaw__<name>`, and what a hook and an allowlist see.
- **The runtime files as they are**:
  - `hilclaw/turn_loop.py`: module docstring and the `OPT_*` constants (lines 1-125), and the command line built near line 245.
  - `hilclaw/turn_definition.py`: what is copied into the session directory.
  - `orchestration/round-manager.md`.
  - `orchestration/agents/evaluator.md`: its `tools` frontmatter.
- **The registers and their recording rules** (follow these rules; do not copy the wording of earlier task files):
  - `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84), and the rows OD-18 and OD-23.
  - `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8), and § OD-18, especially the "제안으로 남는 부분" bullet and its sentence on "그 도구들을 `-p` 세션에서 부를 권한", plus the 채택분 lines.
  - `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 (line 170) and the "최근 재검사" line; scenarios S0, S1 and S2.
- **Claude Code documentation**, read with a web fetch, with each page's reading date stated in the record:
  - https://code.claude.com/docs/en/permissions (modes, rule syntax, MCP tool rules, workspace trust);
  - https://code.claude.com/docs/en/permission-modes;
  - https://code.claude.com/docs/en/cli-reference (`--permission-mode`, `--allowedTools`, `--disallowedTools`, `--tools`, `--setting-sources`, `--settings`);
  - https://code.claude.com/docs/en/sub-agents (whether a sub-agent's tool calls follow the session's permission rules, and what its `tools` list does);
  - https://code.claude.com/docs/en/settings.
  If a page cannot be reached, say so in the record and treat what it would have settled as unverified (a runtime acceptance item). Do not guess.
- **Context only. Do not rely on, cite as accepted, or copy from these**:
  - `PROCESS/STATE.json` `humanQuestions` HQ-0035 (items (i) to (vii)), HQ-0040, HQ-0053 and HQ-0054.
  - The unlanded branch `claude/T-0375-adr-first-case-coder-process-start` (draft ADR-0137, the coder's container session). Its numbering of runtime acceptance items starting at (xxxiii) collides with `main` and is not followed.
- Before editing, run `gh pr list` and look at issues #4, #5, #7 and #8 (CLAUDE.md "세션 진입 점검"). The only open PR, #186 (T-0324), touches no file of `touchesFiles`. If another open PR touches one, stop and return BLOCKED (DRIVER §3-3). The unlanded branches `claude/T-0210-*`, `claude/T-0264-*` and `claude/T-0375-*` edit the OD-18 or OD-23 rows. Take nothing from them; whichever lands later rebases.

## Acceptance Criteria

1. **New record** `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`, in the record format of ADR-0001.
   - Status: accepted under DRIVER §9, not confirmed by the owner, with the 7-day objection note.
   - An owner-sentence search: name the issues, the comment counts and the terms searched, and quote every owner sentence found that touches permissions, permission modes, bypass flags or allowlists of a runtime session.
   - The record separates cited content from its own.
   - It says it answers part of OD-18 (the permission to call the tools in a `-p` turn session) and part of OD-23 (the agents' allowlists beyond the `tools` lists), for the runs of ADR-0118 decision 1 only, and that OD-18 and OD-23 keep their status.
2. **Scope.** The turn sessions of ADR-0118's runs: the main session (the Round-Manager), and the sub-agents defined under `orchestration/agents/` when the record is written (the evaluator).
   - The coder-driver is not defined yet. For it, the record states only the rule by which its entry is added once HQ-0040 is answered, so that the rule holds under both (B) and (T).
   - The coder's own session in its container is outside the scope (ADR-0049, HQ-0053).
3. **What the record decides, each with its reasons and the documentation it rests on**:
   - (a) **The permission mode** passed to every turn session.
   - (b) **The pre-approved tools**: their form (exact `mcp__hilclaw__<name>` entries or wider), and where the list comes from. One option is a fixed list in the layer-2 code; another is a list derived from the definition, such as the Round-Manager's named tools plus the `tools` frontmatter of each agent. If derived, the record says from what. The list includes the built-in tools the definition needs (for example the tool by which the Round-Manager delegates to a sub-agent).
   - (c) **Whether and how the main session's built-in tools are narrowed**, for example by `--tools` or `--disallowedTools`. Today the rule that the Round-Manager uses no Bash or file tools is held by its prompt alone (ADR-0124, ADR-0127, ADR-0133 to ADR-0135; the owner premise "프롬프트만으로 쓰기 구역을 주는 것은 너무 약하다" as those records cite it).
   - (d) **How sub-agents get their permissions**: what the session's rules and the agent's `tools` list each do. Use the documentation; where it says nothing, make it a runtime acceptance item.
   - (e) **The evaluator's unrestricted reading** (ADR-0128 decision 4) under the chosen mode: what happens to a read outside the session directory, and what the record does about it.
   - (f) **Which settings sources** a turn session reads (`--setting-sources` or none), weighed against ADR-0118 item (ii) (the runtime user's `~/.claude/`).
   - (g) **Whether the session directory's `.claude/settings.json` carries any permission rule**, given R10.
   - The record writes nothing into the runtime user's configuration and presumes no such write (as ADR-0118 does). In particular it adds no trust record in `~/.claude.json`.
4. **No bypass.** The record adopts no `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions` or `--permission-mode bypassPermissions` for a turn session. It states how it reads the owner's "never with a bypass flag" (HQ-0006 answer) for a turn session. If the executor finds that no means without a bypass flag can let a turn session call its tools, or that a decision needs an owner-only item (#5 A/B, C-6, OD-25, OD-3) or a write into the user's configuration, stop and return BLOCKED with the question for an HQ. Do not decide it.
5. **Alternatives considered**, as a table with one outcome per row. Cover at least:
   - `dontAsk` with exact allowed tools;
   - the server as a whole (`mcp__hilclaw`);
   - `default` or `acceptEdits` mode;
   - permission rules in the session directory's `.claude/settings.json`;
   - `--settings` with a generated file;
   - a trust record in `~/.claude.json`;
   - a bypass flag;
   - leaving it open.
6. **Walk-through**, a table of rows, including at least:
   - the Round-Manager calls `mcp__hilclaw__state_read`;
   - it delegates to the evaluator, which calls `mcp__hilclaw__checks_read`;
   - the evaluator reads a file outside the session directory;
   - the main session tries `Bash` or `Write`;
   - a session calls a `hilclaw` tool that is not on its list.
   Each row states what is expected and whether it is cited or this record's expectation.
7. **Consequences**:
   - **Code slices for the planner**, each fitting the D4 cap, in code mode, tested with a stub `claude` only (D16). The first is the command line of `hilclaw/turn_loop.py` (and of its entry if needed). Name the docstring sentence it makes false ("No permission … option is passed").
   - **Runtime acceptance items** (D16), numbered after the last item on `main`, which is (xxxiii) of ADR-0138, so new items start at (xxxiv). Say plainly that item (vii) of ADR-0118 now has its means, and that whether the means works remains that runtime acceptance item.
   - **Less exact, not edited**: found by a stated search of `ARCHITECTURE/decisions/`, `hilclaw/` and `orchestration/` for phrases such as "Workspace trust", "permissions", "allowlists beyond the `tools` list" and "not Bash or file tools". Not claimed complete; nothing in that list is edited.
   - **A-13 reading**: document mode; no code, test, setting or dependency change; no data-plane change.
   - **"The cost, plainly"**.
8. **Boundaries** list at least these as not decided:
   - hooks and what they check (PLAN P2-4: budget and gate checks, journaling, a Stop hook, a check of a request's `run_id` against the session's run);
   - the gate layer (OD-3, owner-only);
   - the coder-driver's front (HQ-0040);
   - the coder's container session (HQ-0053, ADR-0049);
   - the credential form (owner, ADR-0054 O8);
   - runs outside ADR-0118 decision 1;
   - the self-check's command line (unchanged).
9. **Requirements.md**, following its "행 형식" paragraph:
   - the OD-18 row gains one link to ADR-0139 with a few words of topic under `**확정분**:`, and its `**잔여**:` is rewritten in place so that the permission part no longer reads as wholly open;
   - the OD-23 row gets the same treatment only if the record answers a part of OD-23;
   - the status cells keep their vocabulary;
   - nothing the ADR says is restated and no dated paragraph is added.
10. **OpenDecisionProposals.md**, following the header's "기록 규칙":
   - § OD-18 gains one line `- **채택분** [ADR-0139](…) — <what it covers>`;
   - the sentence of the "제안으로 남는 부분" bullet that says the permission to call the tools in a `-p` session was not decided is rewritten in place;
   - § OD-23 gets the same treatment only if criterion 9 touched its row;
   - no restatement and no dated note.
11. **StandardScenarios.md**, following the first paragraph of § 검사 결과:
   - recheck S0, S1 and S2 against the change;
   - rewrite the "최근 재검사" line in place;
   - add a history entry only if a verdict changes or a gap is found or closed.
   UsageCases is not edited. If a sentence of it becomes false, name it in the record's Consequences.
12. **D16 and the boundary of the driver.**
   - No `claude` process is started in any form.
   - Nothing is required of the development machine.
   - `.claude/settings.json` and `.claude/settings.local.json` are not edited.
   - No file outside `touchesFiles` changes.
   - No data-plane member, file, kind, value or version is added or changed.
13. After landing, the executor's Result names the new runtime acceptance items for the driver's HQ path (reason `runtime-acceptance`) and the text of the DRIVER §9 owner notice.

## Out of Scope

- Any code, test or definition change: `hilclaw/turn_loop.py`, `hilclaw/turn_start.py`, `hilclaw/turn_definition.py`, `orchestration/` (the code slice follows as its own task).
- The coder-driver definition and the Round-Manager delegation step (ADR-0138 slice 2, HQ-0040); any answer to HQ-0040 or HQ-0053.
- Hooks of any kind (the rest of PLAN P2-4), gates (OD-3), the budget checks (OD-19).
- The self-check's command line (ADR-0054, ADR-0057), the driver's own permission settings (DRIVER §1-5, D13), and the merge guard hook (P0.5-4).
- Editing any earlier ADR, including the "Less exact" sentences.
- Anything from the unlanded branches `claude/T-0210-*`, `claude/T-0264-*`, `claude/T-0361-*`, `claude/T-0375-*`.

## Follow-ups

- Planner's view of what follows: the code slice of this record in `hilclaw/turn_loop.py` (pass the chosen options; update the docstring; tests with a stub `claude` that check the exact command line).

## Result
