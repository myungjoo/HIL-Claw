---
id: T-0037
title: Write ADR-0010 closing one part of OD-18 (the form in which the FR-10 tools of the layer-2 package are exposed to layer 1 - MCP server, command line, or both - and the invocation convention the tool contract needs) and reflect it in the ARCHITECTURE documents
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-18, FR-10, NFR-6, NFR-7, C-7, "#5 A-12", "#5 D6"]
dependsOn: [T-0007, T-0026]
touchesFiles: [ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 190, files: 4}   # one new record of about 110-160 lines, the rest are in-place edits of a few lines each
hq: []   # OD-18 is a design-level OD (DRIVER §9; the owner's D6 answer names "OD-17/18" as closable by the development process); #5 A-12 point 1 hands the exposure question to OD-18 instead of answering it
---
## Why
PLAN P1-1 ("FR-10 도구 계약 인터페이스 + mock 백엔드 + 백엔드 적합성 테스트") cannot be written before one thing is known: **how layer 1 calls a tool of the layer-2 package**. FR-10 says the tools are exposed "MCP/Bash로" and ends with "MCP 서버 vs CLI 노출 형태 = OD-18"; #5 A-12 point 1 says "Exposure form (MCP server vs CLI via Bash) stays open and is decided together with OD-18"; the OD-18 register row repeats it. Every module landed so far states "no command line, MCP exposure or hook integration (OD-18)" as out of scope, so the package has functions (`cas`, `artifacts`, `events`, `key_records`, `clang_build`, `local_run`, `harness/*`) and no agreed way for an agent to reach them.

DRIVER §6: a task that needs a design-level decision carries the record that closes it; the route used so far is two tasks (record, then code). **This task writes the record**: ADR-0010, closing **one part of OD-18** — the exposure form of the FR-10 tools and the invocation convention as far as P1-1 needs it. It ticks **no PLAN checkbox** (prerequisite slice of P1-1).

Why this item now (planner's judgement, DRIVER §6, 2026-10-07 UTC, judged afresh from the files):
- P0.5-3 is BLOCKED on HQ-0003 (T-0014). The rest of P0.5-1 ("harness pass" half of the C gate), the verification half of P1-3, and P1-4 wait for HQ-0004 (T-0036). The rest of P0.5-4 is the owner's hook registration in `.claude/settings.json`, which the driver may not edit. P1-5 slice 3 (the committed GEMM example) needs hw-side values and an objective no source gives (#5 A-4 is owner-only). The rest of P1-8 needs OD-17 with #8 M7 and holds owner-only members (gates, target, tolerance).
- What is left that needs neither owner answer: the design-level closures the journal of 2026-10-07 and the Follow-ups of T-0030 / T-0035 / T-0036 name — OD-18 (before P1-1) and OD-17 (before the runtime `STATE.json`). OD-18's exposure part is taken first because it unblocks code (P1-1) and has explicit, answered inputs (#5 A-12).
- No open PR at planning time. Last comments: #5 = the HQ-0004 mirror (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6029803639), #4 = 2026-07-31, #7 = 2026-09-07, #8 = 2026-10-03. No objection to ADR-0001..0009.

Planner's judgement that the slice is design-level — **the reviewer is asked to re-check it**:
- DRIVER §9 owner-only items are #5 A/B items, C-6, OD-25, OD-3. OD-18 is none of them; the owner's D6 answer (issue comment 5986348506) lists "OD-17/18" among the design-level ODs. #5 A-12 is an answered A item whose point 1 explicitly leaves the form to OD-18.
- **Two entanglements must be handled, not ignored.** (1) The #4 comment 5139876430 argues that the choice is "not a convenience but a security decision": under OD-8 isolation candidate ① item 4, in-process sub-agents get no Bash and reach privileged actions only through typed tools. That candidate is **not chosen** (OD-8 rest, OD-14; waits on container availability and #5 B-1). The record must not choose or reject an isolation means; it must say what its choice leaves possible under candidate ① and under candidate ②. (2) An MCP server built on an MCP SDK would be a **new external dependency** (CLAUDE.md A-13, owner). The record may only choose forms that can be implemented with the standard library of the pinned Python and the layer-2 language set.
- If the executor or the reviewer concludes that the form cannot be chosen without deciding the isolation means, without a new external dependency, or without a fact only the owner has, return **BLOCKED** with the exact question — do not fill the gap.

A-13 check (planner's reading): document mode, no code, no dependency, no data-plane file or field. The request / result convention of a tool call is an interface between layer 1 and layer 2, not a data-plane schema. Ask the reviewer explicitly for this reading.

Known risk, accepted: ADR-0006 (who appends an event line: "the tool layer") is inside its objection window (until 2026-10-13); the Status must say the record is revisited if a record it builds on is reverted.

## Required Reading
- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, 2h30m limit) and §5 (task format, size cap D4, commit trailers) — mandatory for every task (§6)
- PROCESS/DRIVER.md §0 last bullet, §1-5 (Bypass permissions; forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §3 "BLOCKED 사유" paragraph, §8 (driver tail on #5 comments), **§9 (whole section)**, §11 row D6
- CLAUDE.md — 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"**, "세 층 모델", "도구 계층 언어 정책", "브랜치·merge 절차" (document mode, BLOCKED reasons)
- .claude/skills/dev-item-address/SKILL.md (document mode: steps 2, 7, 9-12, 15); .claude/skills/dev-code-review/SKILL.md (what the reviewer checks, "no invented decisions")
- ARCHITECTURE/Requirements.md — line 11 (three-layer model); rows FR-1, FR-9, **FR-10** (line 28), FR-11, NFR-2, NFR-4, NFR-5, **NFR-6**, **NFR-7**, C-5, **C-7**; the "Open Decisions" preamble (lines 80-85: status vocabulary, one-line rule); register rows OD-3, OD-8, OD-10, OD-12, OD-14, OD-17, **OD-18** (line 105), OD-19, OD-23
- ARCHITECTURE/OpenDecisionProposals.md — **OD-18** (lines 183-191, in particular the two "흡수" bullets and the integrator memo), **OD-8** (lines 75-96: candidate ① items 2, 4, 5 and candidate ②), OD-14 (140-146), OD-17 (176-181), OD-23 (222-229), OD-12 (117-126: the *other* use of MCP — external references; not this record's)
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md — closing **"Record format"** section (lines 146-153; this record follows it); ADR-0006-od8-events-log.md — decisions 7 and 10 and Boundaries ("which tool or hook appends"); ADR-0009-od13-cpu-standin-timing-run.md — Status (as a template for the Status of a record closing one part of an OD) and decision 1 ("not an FR-10 tool contract")
- ARCHITECTURE/UsageCases.md lines 58, 89, 95 and ARCHITECTURE/StandardScenarios.md "검사 규칙" and "검사 결과" (from line 155) — read, UsageCases not edited
- Issue sources (fixed inputs unless marked proposal): **#5 A-12** `gh api repos/myungjoo/HIL-Claw/issues/comments/5946779596 --jq .body`; #5 A-7 `.../comments/5944117402`; #5 D6 `.../comments/5986348506`; #5 B-6 (C-7 source, in the issue body / its answer comment); **#4** body §3a and comments `.../comments/5138366881` (roster with "MCP sim.run / board.run", "비싼 결과의 저널링은 도구 계층에서") and **`.../comments/5139876430`** (candidate ①; "hook은 `claude -p` 자식에게 닿지 않는다"; "Bash가 있으면 경로 기반 deny는 무의미"; exposure as a security decision) — these two comments are **proposals / discussion**, not owner decisions, except the two premises the second one marks as owner judgement; #7 body §5 G5 and comment 5139423949 §2(8); #8 body M4. Then every #5 comment after 6029803639.
- Existing code the record must not contradict (not edited): the module docstrings of `hilclaw/events.py`, `hilclaw/artifacts.py`, `hilclaw/cas.py`, `hilclaw/config.py`, `hilclaw/local_run.py`, `hilclaw/harness/timing.py`; `hilclaw/merge_guard.py` and `hilclaw/driver_state.py` (the two existing `python -m hilclaw.<module>` entry points); `pyproject.toml` (no runtime dependency, no build backend, no console script; `requires-python >= 3.11`)
- PROCESS/tasks/T-0007-merge-guard-hook.md `## Result` bullet "Hook protocol" (what a `PreToolUse` hook receives: `tool_name`, `tool_input.command`; exit 2 blocks) and its "Known limits" (how unreliable shell-command recognition is); PROCESS/tasks/T-0031-adr-cpu-standin-timing-run.md `## Result` (how a record closing one part of an OD landed; notice text); PROCESS/PLAN.md items P1-1, P2-2, P2-3, P2-4

## Acceptance Criteria
What is **fixed** and taken as input, not re-decided:
- #5 A-12: layer 2 is the layer-1 agent's toolset, one package `hilclaw/` (FR-10 tools, backends, CAS, schema validation, hook entry points, harness); languages {Python, POSIX sh, C}; **no runtime tool creation in MVP** (the tool set is fixed at run start). FR-10: the tool names `sim.run`, `board.run`, `profiler.collect`, `correctness.check` (and `blob.push` / `blob.fetch`, C-3), a contract that is **transport-independent**, a mock backend always present. C-7 ③: orchestrator session → sub-agents → `claude -p`; C-7: POSIX (Linux, macOS, WSL). NFR-6: the interface must not exclude Method A or later dynamic tool registration. ADR-0006 decision 7 / #4 §3b: the line of an expensive result is appended by the tool layer.
- No new external dependency (see `## Why`).

What the ADR **decides**. The content of each decision is the executor's to work out and justify from the fixed inputs; the reviewer's Approve confirms it. For every point give the choice, the alternatives considered (at least: MCP server only, command line through Bash only, both as two entry points of one package) and one or two lines of reason; mark each value as **cited** or as **this record's own**:
1. **Scope and terms**: the record is about how a layer-1 agent invokes an FR-10 tool of the package; name the parts it speaks of (for example: tool function, entry point, request, result). It is not a tool's argument list, not a backend transport, not a hook.
2. **Where the contract lives**: whether a tool is defined once at an exposure-neutral level inside the package (a callable with a serialisable request and result) with the exposure as a thin front — and what "transport-independent" (FR-10) and NFR-6 require of that level.
3. **The exposure form(s) for MVP**: which form layer 1 uses, argued against the alternatives on these points at least: what a `PreToolUse` hook can see of a call (typed tool name and arguments versus a command string — T-0007 known limits), what a per-agent tool allowlist can express, whether the form reaches a `claude -p` child (C-7 ③), implementation cost with the standard library only, and use by a person for debugging. If more than one form is provided, say which is the one agents use and what keeps them identical in behaviour.
4. **Invocation convention of the chosen form(s)**, as little as P1-1 needs: how a tool is named at that form (mapping of `sim.run` and the others), how the request goes in and the result comes out, how a failure of the tool itself is told apart from a result that reports a failed experiment, and where diagnostics go. No argument or result member of any single tool.
5. **How the entry point finds its configuration and data root** only as far as existing modules already fix it (`hilclaw.config`); nothing new is decided there.
6. **What follows for enforcement and isolation, stated as consequences, not decisions**: what the choice leaves possible under OD-8 candidate ① (item 4: no Bash for in-process agents) and under candidate ②; what a later hook (OD-18 rest, PLAN P2-4) can intercept. Explicit sentence: **no isolation means, no hook, no gate and no allowlist is adopted or rejected by this record.**
7. **Versioning and change**: how a change of the convention is tracked in P1 (the source commit hash is the confirmed P1 pin — OD-11 confirmed part) and what NFR-7 ① (replaceable at a round boundary) means for a long-lived server process, if the chosen form has one — without deciding the round = process question (#8 M4).
8. **Limits**: what the form does not protect against or provide, each with the place where it is decided.

What the ADR must **not** decide — name each as a boundary in the record, with the place where it is decided:
- The rest of OD-18: which hooks exist and what they check, round boundary = process boundary (#8 M4, UC-3 `/loop`), the CLAUDE.md invariant list, default-FAIL, the kill switch. The gate layer and gate list (OD-3 / #5 A-5, owner-only).
- The isolation means (OD-8 candidates ① / ②, OD-14); the agent roster, who may call which tool, whether `coder.run` exists (OD-23, PLAN P2-2 / P2-3).
- The arguments, results, errors and retry of each tool; the mock's fault injection; event kinds and payloads (PLAN P1-1, P1-8; OD-10, OD-13, OD-17, OD-19).
- How a backend is reached (local, LAN, SSH — #5 B-2, A-7 ③); the external-reference MCP adapters (OD-12 / FR-14).
- Any oracle, tolerance, objective, or hw-side value. Any code, test, CI change, packaging change (`pyproject.toml`, console scripts, `.mcp.json`), or settings file.

If a point of 1-8 cannot be written without an excluded item, narrow the point and say so, or return BLOCKED with the exact question (DRIVER §3, §9).

The record (`ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`, new; use the next free ADR number at execution time if 0010 is taken, and adjust the file name in `touchesFiles` terms accordingly):
- Follows the "Record format" of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References; one closure; English; about 110-160 lines.
- **Status**: accepted under DRIVER §9 (D6) by reviewer approval, the date, that it closes one part of OD-18 (exposure form of the FR-10 tools) and what of OD-18 stays open, the records it builds on and that it is revisited if one is reverted, and the owner's 7-day objection window after the #5 notice. Do not write that the owner confirmed it.
- Facts about Claude Code that a decision rests on (how an MCP server is configured and named to agents, sub-agent `tools` frontmatter, what a hook receives, whether a child `claude -p` inherits them) are each marked **verified** (with the documentation URL and the date) or **not verified**; a decision must not rest on a not-verified fact alone — say what would reopen it.
- **Consequences** list, without doing them: the P1-1 code slices (entry point, one tool at a time, mock backend, conformance tests), what P2-2 / P2-3 / P2-4 inherit, and what the FR-10 sentence "MCP 서버 vs CLI 노출 형태 = OD-18" should read afterwards (a follow-up for the integrator; FR rows are not edited here).

Edits of existing documents (same commit — register update rule):
- `ARCHITECTURE/Requirements.md`: the **OD-18 row only**. Keep its status word as the precedent of OD-16 does (`제안됨` with a "확정분" clause naming ADR-0010), keep the open rest visible, one line. No other row, no FR / NFR / C row, no preamble; do not renumber, add or remove an OD row. A new open question the record raises is registered as a sub-question under OD-18 in OpenDecisionProposals; **do not create a new OD number** — if you conclude one is needed, return BLOCKED with the reason.
- `ARCHITECTURE/OpenDecisionProposals.md`: section **OD-18** — heading note, the "흡수: FR-10 도구의 노출 형태" bullet (what ADR-0010 fixed; keep the old text visible as T-0030 did), the integrator memo marked as far as adopted or not, sub-questions raised. Sections OD-8 / OD-14 / OD-23 only if a sentence needs a pointer saying ADR-0010 adopted none of their proposals. Delete no proposal text.
- `ARCHITECTURE/StandardScenarios.md`: re-run the coverage check (CLAUDE.md "문서 커버리지 재검사") for every step that cites FR-10 or OD-18 or rests on an agent calling a tool; update "검사 결과" (heading note, one new dated passage in the history paragraph, affected rows). State the outcome in the commit body even if no verdict changes.
- In-place edits keep the language of the surrounding text (Korean).
- No edit to ADR-0001..0009, `ARCHITECTURE/UsageCases.md` (name a sentence made false as a follow-up), `CLAUDE.md`, `README.md`, `PROCESS/DRIVER.md`, `PROCESS/PLAN.md`, the skills, the agents, or anything under `hilclaw/`, `tests/`, `.github/`, `.claude/`.

Tests: none. Document mode, no code change; CLAUDE.md test rules ①-④ do not apply. The document checks below replace steps 4, 6 and 8 of dev-item-address.

Document checks (record each outcome in `## Result`; scripts used are **not committed**):
- Session-entry check before the first edit: `gh pr list --repo myungjoo/HIL-Claw --state open` and issues #4, #5, #7, #8 read for anything newer than this task file about OD-18, FR-10 or tool exposure. An open PR editing the OD register or the OD-18 section → BLOCKED ("open PR conflict"). An owner comment that answers or contradicts a point → take it as fixed input, or BLOCKED ("requirement unclear") quoting it. (Positive case: nothing new → proceed. Negative cases: the two above.)
- Each decision is checked against FR-10, #5 A-12 points 1-4, NFR-6, NFR-7 ① and ADR-0006 decision 7; list the pairs checked. Nothing contradicts the docstrings of the modules named in Required Reading.
- Nothing in the record states an excluded item as decided: no hook, no gate, no isolation means, no roster or allowlist, no tool argument or result member, no backend transport, no new dependency, no data-plane field.
- Every relative link in the new record and the edited lines resolves; `git diff origin/main -- ARCHITECTURE/Requirements.md` touches the OD-18 row only; the count (29) and numbering of register rows are unchanged.
- `git ls-files --eol` shows `i/lf` for the changed files; `git diff origin/main --stat` lists only files in `touchesFiles`.
- After landing, the `push` run on `main`: `gh api "repos/myungjoo/HIL-Claw/actions/runs?branch=main&event=push&per_page=1"`; record its conclusion; if it is not `success`, do not fix forward — record it and say so in the summary.

Process (document mode, CLAUDE.md A-13, dev-item-address steps 9-12 and 15):
- First the §3-5 landed check: `git log origin/main --grep='^Task: T-0037'` and `gh pr list --repo myungjoo/HIL-Claw --search T-0037 --state all`.
- Branch `claude/T-0037-adr-od18-tool-exposure-form` from `origin/main`; commit and push the branch; **no PR**.
- Reviewer cycle: a fresh-context `dev-reviewer` sub-agent per round, given the branch name (target = diff against `origin/main`) and this task file's path. Ask it explicitly to check (a) the planner's judgement in `## Why` (design-level, the two entanglements, the A-13 reading); (b) that no excluded item is decided — in particular that no isolation means of OD-8 / OD-14 and no hook or gate is adopted or rejected; (c) that the chosen form needs no new external dependency; (d) that each decision is cited or argued with alternatives and that Claude Code facts are marked verified / not verified; (e) the register and coverage-check updates. Address findings and re-request until Approve with nothing trivially fixable left; more than 7 rounds is BLOCKED; a result starting with `SECURITY` is BLOCKED; if no reviewer can be spawned, BLOCKED — no self-review.
- Landing: `git fetch origin`, rebase onto `origin/main`, squash to **one** commit (`git reset --soft origin/main` + commit, only after the rebase); `git show --stat HEAD` lists only `touchesFiles`. A rebase that changed content goes back to review.
- Commit message: English; subject starts with `T-0037:`; body gives the decisions in one line each, the boundaries, the register edits and the coverage re-check outcome; trailers in this order: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0037`, then any attribution trailer your session requires.
- Push with `git push origin HEAD:main` (fast-forward). If rejected, fetch, rebase, retry (at most 3 times); never `git push --force*`; never push the rewritten branch back to its remote branch. Delete the remote and the local branch in **separate** commands only after the push to `main` is confirmed, then check out `main` at `origin/main`.
- **Owner notice (DRIVER §9)**: do not post it unless the driver's spawn prompt tells you to. Put the ready-to-post English text in `## Result`: heading `### OD-18 — exposure form of the FR-10 tools fixed by ADR-0010 under DRIVER §9 (T-0037)`, what was decided in six lines or fewer, the record's path and commit, owner inputs (#5 A-12, C-7) versus the record's own choices, the **readings to check** (the choice next to the OD-8 candidate ① argument that exposure is a security decision; no new dependency; what stays open of OD-18), the A-13 reading, the date the 7-day window ends; last line `— posted by driver`.
- `## Result`: fill it in **after** the push, on `main`, and leave that edit **uncommitted** for the driver (DRIVER §3-6); the landed commit must not contain this task file. Record: commit hash, review rounds and findings, the decisions with reasons, boundaries, document-check outcomes, the notice text, follow-ups. Say that this task ticks **no** PLAN checkbox.
- `PROCESS/STATE.json`, `PROCESS/journal/` and `PROCESS/PLAN.md` belong to the driver.
- Size: one new file and three small edits, within 300 LOC / 5 files. If consistency needs a sixth file, do not exceed the cap: finish and list it as a follow-up (DRIVER §5).
- If a needed tool call is denied or fails, return BLOCKED rather than working around it (DRIVER §1-5). Never edit `.claude/settings.json` or `.claude/settings.local.json`; never use `git push --force*`, `rm -rf` or `gh repo delete`.
- Return a summary of at most 200 characters (result, commit, BLOCKED or not).

## Out of Scope
- Any code: an entry point (`hilclaw/__main__.py`, an MCP server, a dispatcher), a tool function, the mock backend, conformance tests, `.mcp.json`, packaging (PLAN P1-1 code slices).
- Registering any hook or MCP server; any edit under `.claude/`.
- The rest of OD-18 and anything of OD-3, OD-8, OD-10, OD-12, OD-14, OD-17, OD-19, OD-23; resolving #8 M4 or M7.
- Editing FR-10 or any other FR / NFR / C row, issue bodies, ADR-0001..0009, UsageCases.
- Answering HQ-0003, HQ-0004 or any #5 A / B item on the owner's behalf.

## Follow-ups
- (driver, after the wrap-up push) Post the §9 owner notice on #5 from the text in `## Result`, with the driver tail.
- (planner, next — code mode, P1-1 slices) The entry point of the chosen form with one tool that needs no undecided contract, then the mock backend and conformance tests; judge per slice which of OD-10 / OD-13 / OD-23 it touches.
- (planner, independent of HQ-0003 / HQ-0004) OD-17 with #8 M7 as a §9 record before the runtime `STATE.json` of PLAN P1-8; its gate, target and tolerance members are owner-only and stay out.
- (integrator, document mode) FR-10's closing sentence "MCP 서버 vs CLI 노출 형태 = OD-18" and #5 A-12 point 1, once the objection window has passed.

## Result
