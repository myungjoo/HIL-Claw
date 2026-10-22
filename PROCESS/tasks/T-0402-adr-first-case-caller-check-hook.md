---
id: T-0402
title: Write ADR-0146 - whether and how a first-case turn session refuses a call of a hilclaw tool by a caller that is not meant to hold it (a PreToolUse hook that checks the calling agent against the tool, or another place), how the hook settings reach the session, and what the check does when it cannot tell (first part of PLAN P2-4; part of OD-18)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-9, FR-10, FR-11, NFR-4, OD-18, OD-23, "#5 A-12"]
dependsOn: [T-0378, T-0379, T-0387, T-0354]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P2-4 (hooks: PreToolUse budget and gate checks, PostToolUse journaling, Stop commit; **OD-18 and OD-19 to be closed by ADR, DRIVER §9**) is unchecked and no hook of the runtime exists yet. It is a PLAN checklist item in the group that PLAN's P2 header puts before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it. Most other routes to P2-5 are held by unanswered HQs: `board.run` and the `cpu_standin` operations by HQ-0021 and HQ-0026 (ADR-0144 slice (4), ADR-0142 slice 2), the coder's container by HQ-0053 (ADR-0141 slice (d)), the selection role by HQ-0048 (T-0361). P2-4 is not held by any of them.

**Which part of P2-4, and why this one.** ADR-0139 decision 5 and "The cost, plainly" (line 165) record the gap this task addresses: sub-agents are confined by their `tools` lists, but the main session (the Round-Manager) shares the pre-approved pool, so it *can* call `mcp__hilclaw__verdicts_write`, `mcp__hilclaw__correctness_check`, `mcp__hilclaw__spec_write` or `mcp__hilclaw__coder_run`, and only its prompt keeps it from doing so, "until a hook tells callers apart". The evaluator's sole hold on verdicts is what keeps the hard floor of FR-9 out of the Round-Manager's hands, so this gap bears on the first run (P2-5). ADR-0010 decision 6 (lines 104-113) and F5 say a `PreToolUse` hook can tell the calling sub-agent by `agent_type`, and that a check on every path has two possible places (a hook on the typed tool with no shell for the agents concerned, or the tool layer). ADR-0139 Boundaries (line 169) names "a check of the calling agent against a tool (ADR-0010 decision 6)" among the open hook questions, and the OD-18 register row's 잔여 names "호출한 에이전트를 도구와 대조하는지". This record is the first hook record, so it also has to say how hook settings reach a first-case turn session, which ADR-0118 decision 5 and ADR-0139 decision 7 leave as "where the hooks of PLAN P2-4 would live" (the definition's `settings.json`, copied by `hilclaw/turn_definition.py` `LAYOUT` to `.claude/settings.json` when present; `orchestration/settings.json` does not exist today).

**Scope, to keep one record reviewable**: for the runs of ADR-0120 decision 1 (first case) only —
(a) whether the caller of each `mcp__hilclaw__*` tool is checked against the callers meant to hold it, and where (a `PreToolUse` hook, the tool layer, both, or nothing beyond today's prompt and lists), with the alternatives weighed;
(b) if checked: what the check takes as "meant to hold" (the record should weigh using exactly the sources ADR-0139 decision 3 already uses — `ROUND_MANAGER_TOOLS` of `hilclaw/turn_permissions.py` for the main session and each agent file's `tools` frontmatter — so that one list governs both pre-approval and the check, against any second list), and how the main session is told apart from a sub-agent in the hook input;
(c) how the hook settings are given to a turn session (the definition file, its copy, `--setting-sources project`, a folder never trusted — ADR-0118 R10, ADR-0139 P6/P7) and what program the hook runs (a layer-2 entry point of the package — CLAUDE.md "세 층 모델" counts hook entry points in layer 2), including how that program is found from a static settings file (the MCP server entry uses `sys.executable`, `hilclaw/turn_loop.py` line 84; a static copy cannot hold a per-machine path unless something writes it) — decide or leave named to the code slice, but coherently;
(d) what this one check does when it cannot read its input, meets an unknown caller or tool, or fails itself (refuse or let through), for this check only; the general default-FAIL contract of OD-18 stays open;
(e) the code slices this implies, the runtime acceptance items, and the less exact sentences of earlier records.

The record may conclude that no hook is adopted (for example if the documentation shows the main session cannot be told apart, or that hooks in a session's project settings do not run under the flags of ADR-0139); it then says so, with the cost, and names what stays open.

Planner's judgements (from `main` `70e6b11`; **the reviewer is asked to re-check each**):

- **Not owner-only.** No gate is set or listed (OD-3, #5 A-5 — owner-only): a refusal of a caller that the definition never meant to hold a tool is not a gate (FR-4's stop-and-wait). If the executor finds the check cannot be written without choosing a gate or what a gate checks, stop and return BLOCKED (`requirement-unclear`) with the question. No budget check (OD-19 "다음 지출 경로 위의 검사"), no journaling, no Stop hook, no `run_id` check, no `PreCompact`, no kill switch is decided: each is named in Boundaries.
- **No open HQ is crossed.** HQ-0053 (the coder container's sign-in): the check concerns who may call `coder.run`, not how the coder starts. HQ-0048 / T-0361 (selection role, `hypotheses.write`): the unlanded draft ADR-0132 on branch `claude/T-0361-*` is not a record; do not cite it or presume a `technique-selector` agent or a `hypotheses.write` tool. HQ-0021, HQ-0026: no run tool is presumed registered beyond what `default_registry` holds on `main`. HQ-0055 (ADR-0139 items (xxxiv)-(xl)) and HQ-0035 are runtime acceptance items: the record may add numbered items but must not treat those as confirmed. Unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0361-*`, `claude/T-0375-*` are not sources and their ADR numbers are not taken.
- **No data-plane schema change and no new external dependency.** A refusal is the hook's, not a tool result: no tool-failure kind, event kind, member, file or version is added. If the record cannot be coherent without one, leave it open or return BLOCKED (A-13 data-plane schema change). A hook program in the package's languages (Python, POSIX sh, C) is not a new dependency; a library or a separate tool the user must install is.
- **Test rule note for the later code slice.** CLAUDE.md test rule ⑤ excludes tests of "hook 스크립트"; a runtime hook entry point under `hilclaw/` is also a module of the layer-2 package, which rules ①-④ cover. The record does not decide which applies; it names the question under Consequences for the code slice's planner.
- **No open PR overlaps**: PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files.

All work is documents and documentation reading. No `claude` process is started on this machine (D16; DRIVER §1-5). Every fact about Claude Code hooks, their input (`agent_id`, `agent_type`, what a main-session call carries), their exit statuses and JSON output, matchers for MCP tools, and which settings a `-p` session reads under `--setting-sources project` in a folder never trusted, comes from the official documentation (https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/permissions, https://code.claude.com/docs/en/headless), quoted with URL and date read, as ADR-0139 Context does; what the documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (executor procedure, resume rule, the 2 h 30 min limit); §5 (task format; naming: branch `claude/T-0402-<slug>`, trailer `Task: T-0402`; D4 size cap); §3 "BLOCKED 사유"; §8; §9 (closing an OD part by ADR; the #5 notice with the driver footer; the 7-day objection window).
- `CLAUDE.md` (repository), "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "세 층 모델", "개발 드라이버와 런타임의 구분" (D16), "도구 계층 언어 정책", "브랜치·merge 절차", "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format" (the ADR format).
- **`ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`**: Status and Context (lines 3-41, in particular P2, P6, P7); decisions 3, 5, 7 and 8 (lines 59-66, 74-80, 88-99); Walk-through (lines 110-124); Consequences and "The cost, plainly" (lines 144-166); Boundaries (lines 167-177). The record this one builds on; read only.
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: Context facts F2, F4, F5, F6 (lines 20-31); decision 6 (lines 104-113); Boundaries (lines 155-164). Read only.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: R4 and R10 (around lines 35-41); decisions 4 to 6 (lines 91-123); Boundaries (lines 186-201). Read only.
- `ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md` Boundaries (lines 120-129) and `ADR-0128-*` decisions 2 and 3 (who holds the evaluation tools). Read only.
- Code and definition, as observation only: `hilclaw/turn_permissions.py` (module docstring, lines 1-80; `ROUND_MANAGER_TOOLS`, lines 91-100), `hilclaw/turn_definition.py` (module docstring, lines 1-40; `LAYOUT`), `hilclaw/turn_loop.py` (module docstring, the server entry at line 84), `orchestration/round-manager.md` ("Your run", lines 15-51), the frontmatter of `orchestration/agents/evaluator.md` and `orchestration/agents/coder-driver.md`.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph (line 84); FR-4, FR-9; register rows OD-3, OD-18, OD-19 (lines 94, 109, 110).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header "기록 규칙" (line 8); § OD-18 (lines 281-369, in particular lines 283-289 and sub-question ② at line 353 and the integrator note at line 368).
- `ARCHITECTURE/StandardScenarios.md`: the inspection rules and § 검사 결과 (from line 168).
- Issue #5: every comment after the ADR-0145 §9 notice (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6331854598), via `gh issue view 5 --repo myungjoo/HIL-Claw --json comments`. If the owner has objected to ADR-0139 or said anything about hooks, callers or the Round-Manager's tools, do not start: return BLOCKED (`requirement-unclear`) and quote the comment.
- Session entry check (CLAUDE.md): `gh pr list`, issues #4, #7 and #8 for anything on hooks, and the unresolved `humanQuestions` of `PROCESS/STATE.json`.

## Acceptance Criteria

### The record

1. One new record `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md` in the ADR-0001 "Record format" (take the next free number at the time of writing if 0146 has been taken on `main`, and rename the file to match). Its Status states: which part of OD-18 it answers (the check of the calling agent against a tool and the way hook settings reach a turn session, for the runs of ADR-0120 decision 1) and that OD-18 keeps its status word; which open HQs were checked and not crossed; that no data-plane member, file, kind, value or version is added; that nothing was started for it (D16); which sentences of earlier records it replaces for those runs, quoted without editing them; the #5 notice and the 7-day objection window. Every sentence is cited or marked as the record's own.
2. **(a) Whether and where**: the record decides whether the caller of each `mcp__hilclaw__*` tool of a first-case turn session is checked, and where. "Alternatives considered" weighs at least: a `PreToolUse` hook; a check in the tool layer (what the MCP request does or does not carry about the caller); `--agent` for the main thread (ADR-0139 rejected it — cite, do not re-decide); and no check beyond today's prompt and lists — each with its cost.
3. **(b) The list it checks against**: what counts as the tools a caller is meant to hold, how the main session is told apart from each sub-agent in the hook input (grounded in quoted documentation), and how the record keeps that list from diverging from ADR-0139 decision 3's pre-approved list. Calls of built-in tools (`Agent`, `Read`, `Grep`, `Glob`) are in or out of the check by an explicit statement.
4. **(c) Delivery**: where the hook settings live in `orchestration/` and how they reach the session directory (ADR-0118 decision 5; `turn_definition.LAYOUT`), whether they act under `--setting-sources project` in a folder never trusted (ADR-0118 R10; ADR-0139 P7 — state what is verified and what is a runtime acceptance item), what program a hook runs and how it is found; anything left to the code slice is named.
5. **(d) When the check cannot tell**: what this check does on unreadable input, an unknown caller, an unknown `mcp__hilclaw__*` tool, a tool of another server, and its own failure, and what the refused caller is told. The general default-FAIL of OD-18 is named open in Boundaries.
6. **Walk-through** table: at least the Round-Manager calling `mcp__hilclaw__verdicts_write`, `mcp__hilclaw__coder_run` and `mcp__hilclaw__state_write`; the evaluator calling `mcp__hilclaw__verdicts_write` and `mcp__hilclaw__run_commit`; the coder-driver calling `mcp__hilclaw__coder_run`; and a call of a tool no list names.
7. **Boundaries** names as open, each with the OD or HQ it belongs to: budget checks and the next spend path (OD-19), gates (OD-3, owner-only), journaling beyond the tool layer, the Stop hook (ADR-0127, ADR-0143), a check of a request's `run_id` against the session's run, `PreCompact`, the kill switch, default-FAIL in general, the CLAUDE.md invariant list, sub-question ② (an agent holding a shell and the command-line front), hooks of any session other than a first-case turn session, and the selection role (HQ-0048).
8. **Consequences** lists: the code slice(s) for the planner (code mode; each tested with fixture inputs and a stub `claude` only, never a real `claude` — D16; each within the D4 cap), naming no module or signature beyond what the decisions need, and naming the test-rule question of Why for the hook entry point; the runtime acceptance items, numbered after the highest item number in `ARCHITECTURE/decisions/` on `main` (grep for the last used roman numeral; ADR-0145 used (liii)-(lv)); and the sentences of earlier records that become less exact (not edited), found by reading the records of Required Reading and by grep over `ARCHITECTURE/decisions/` for "until a hook", "a hook is P2-4's", "Only the prompt keeps" and "tells callers apart".

### Register edits

9. `ARCHITECTURE/Requirements.md`: edit the OD-18 row only, by the rule in that file's "행 형식" paragraph (line 84): one link to the new ADR with a few words of topic after `**확정분**:`, and `**잔여**:` rewritten in place; no restatement of the record, no dated sentence.
10. `ARCHITECTURE/OpenDecisionProposals.md`: edit § OD-18 only, by the header's "기록 규칙" (line 8): one `- **채택분**` line for the new ADR, and the status of each sub-question or proposal bullet it answers rewritten in place (in particular the "제안으로 남는 부분(채택분 밖)" bullet, line 289, if a `PreToolUse` hook is adopted or rejected); no register text copied, no dated paragraph.
11. `ARCHITECTURE/StandardScenarios.md`: re-inspect coverage by its rules (CLAUDE.md "문서 커버리지 재검사") and record the result as the first paragraph of § 검사 결과 prescribes.

### Process

12. Document mode (A-13): branch `claude/T-0402-<slug>`, context-isolated reviewer cycle of dev-item-address steps 10-12, rebase on `origin/main`, direct push to `main` with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0402`. After landing, post the §9 notice on #5 with the driver footer. List any runtime acceptance items the record adds in `## Result` with their numbers, so the driver records them as one HQ with reason `runtime-acceptance` (DRIVER §8).
13. `git diff --stat origin/main` lists only the touchesFiles (Requirements/OpenDecisionProposals/StandardScenarios only where criteria 9-11 require); `git diff --check` is clean. No code, test, `orchestration/` file, PLAN or STATE file is changed. No `claude` is started (D16).

## Out of Scope

- Any code: the hook entry point, `orchestration/settings.json`, changes to `turn_definition`, `turn_permissions` or `turn_loop` (later code slices).
- Budget, gate, journaling, Stop, `run_id`, `PreCompact` and kill-switch hooks; default-FAIL in general; hooks of the coder's `claude -p` session (its permissions belong to slice (d), HQ-0053).
- Editing earlier ADRs (less exact sentences are listed, not edited), or the deferred T-0399 follow-ups in PLAN's 보류 section.

## Follow-ups

## Result
