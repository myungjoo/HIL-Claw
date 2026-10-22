---
id: T-0411
title: Write ADR-0149, whether a hook journals or verifies anything after a tool call in a first-case turn session, beyond the two step lines the tool layer writes (part of OD-18; PLAN P2-4)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-11, NFR-1, OD-18, OD-17, "PLAN P2-4"]
dependsOn: [T-0408, T-0410]
touchesFiles: [ARCHITECTURE/decisions/ADR-0149-od18-first-case-post-tool-use.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2-4 covers the runtime hooks: "PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제", and says **OD-18 and OD-19 are to be closed by ADR (DRIVER §9)**. It is a PLAN checklist item in the group that PLAN's P2 header runs before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it.

What is done of P2-4 as of `main` `1d5a634`:
- the caller check hook: ADR-0146, code T-0403, T-0404;
- the round-budget check on the two spending tools: ADR-0147, code T-0406, T-0407;
- the `Stop` hook that holds the end commit: ADR-0148, code T-0409, T-0410.

What remains of P2-4:
- the gate half of "예산·gate": owner-only (OD-3, #5 A-5); not planned here;
- **"PostToolUse 저널링"** — this task.

**What is already settled about journaling** (cited, do not re-decide):
- ADR-0011 decision 2: a journaled step leaves a start line and an end line, both appended by the tool layer, never by an agent.
- ADR-0015 decision 5: those two lines and the lookup are carried out **below the fronts, inside the tool function**; a `PostToolUse` hook alone, and a `PreToolUse`/`PostToolUse` pair, were rejected for them. It names what is left for PLAN P2-4: "journaling of events other than the two step lines; and whether a hook verifies that a journaled call left its lines. A hook is no longer the writer of the two step lines." ADR-0015 Consequences also gives the reading the integrator should apply to PLAN P2-4's wording.
- OpenDecisionProposals § OD-18 "제안으로 남는 부분": "저널 대상 단계의 두 줄 … 밖의 이벤트를 누가 추가하는지(PLAN P2-4)는 미결이다", and the proposal's own concern: "`PostToolUse`(**결과 저널링은 모델 행동이면 안 됨**)".

**Scope, to keep one record reviewable.** For the turn sessions of the runs of ADR-0120 decision 1 (first case) only — the same sessions ADR-0146, ADR-0147 and ADR-0148 cover — the record answers:

(a) **What there is to journal after a call, and who writes it today.** List, from the code on `main` and the records, which `mcp__hilclaw__*` tools of these sessions are journaled steps (two lines through `hilclaw/journaled_step.py` / `hilclaw/journaled_tool.py`), which write run files of their own (for example `verdicts.write`, `hypotheses.write` if it exists on `main`, `case.write`, `key.store`, `round.end`, `spec.write`, `run.commit`), and which only read. Say for each group whether any event about the call is a model action today. Do not invent tools: use `default_registry` and the turn session's tool list as they are on `main`.

(b) **Whether a hook is adopted after a call, and in which form.** Weigh at least:
- (i) a `PostToolUse` (and/or `PostToolUseFailure`) command hook that appends a further event to `events.ndjson` for some or all calls;
- (ii) a `PostToolUse` hook that only **verifies** that a journaled call left its lines (ADR-0015 decision 5's open question) and tells the model something, or nothing, when they are missing;
- (iii) a hook that writes somewhere other than the data plane (for example the standard error or log of the turn, as the self-check writes to standard output and the instance log only — PLAN P1-9);
- (iv) nothing beyond the tool layer: the record says plainly that for these sessions "PostToolUse 저널링" is carried by the tool layer of ADR-0015 and no hook is added, with the cost.

The record may conclude that no hook is adopted. It then says so, states the cost plainly and names what stays open.

(c) **If one is adopted**, the record says, as ADR-0146 to ADR-0148 do: its matcher and which tools; what it reads (and whether it starts a process); how it learns the run and the data root (the loop already passes both to the `Stop` hook — ADR-0148 decision 4); what it does when it cannot tell; what the model is told, if anything; the delivery and which sentence of ADR-0148 decision 4 ("two `PreToolUse` entries and one `Stop` entry, and nothing else") it revises, keeping the three existing entries unchanged; and why its writes do not race the tool layer's appends (ADR-0006 decision 5, ADR-0011 decision 2's window).

(d) **What follows**: the code slices (each within the D4 cap of DRIVER §5, each tested with fixtures and a stub `claude` only); the runtime acceptance items, numbered after ADR-0148's **(lxvi)**; the "Less exact, not edited" list. If no hook is adopted, there may be no code slice; say so.

**Planner's judgements** (from `main` `1d5a634`; **the reviewer is asked to re-check each**):

- **Not owner-only.** OD-18 is a design-level OD; ADR-0146 and ADR-0148 closed parts of it under DRIVER §9. No gate (OD-3), retry policy (OD-17), budget value (OD-19) or new meaning of an owner answer is needed. If a coherent answer needs one, stop and return BLOCKED (`requirement-unclear`) with the question.
- **Data-plane schema.** Option (i) needs a new `events.ndjson` kind or payload, which is a **data-plane schema change** (CLAUDE.md A-13 BLOCKED reason; ADR-0006 decision 8 on versioning). This task may **weigh** (i) but may not **adopt** it: if the executor finds that a coherent answer needs a new kind, member, file or `schema_version`, it does not choose one; it either concludes on another option and leaves (i) named as open, or returns BLOCKED (`data-plane-schema`) with the question. Options (ii), (iii) and (iv) add nothing to the data plane.
- **No new external dependency.** A hook program in Python of the package is not one.
- **No open HQ is crossed.**
  - HQ-0053 (the coder's container sign-in), HQ-0021 and HQ-0026 (`sim.run`/`board.run` and the `cpu_standin` operations), HQ-0048 (the selection role, unlanded ADR-0132), HQ-0032 (open PR #186) are unrelated; do not presume their answers. `board.run` and `sim.run` are not in `default_registry` on `main`; do not presume them registered.
  - HQ-0061, HQ-0062, HQ-0063 and the other `runtime-acceptance` HQs are runtime items: cite them, treat none as confirmed.
  - Unlanded branches (`claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0318-*`, `claude/T-0324-*`, `claude/T-0361-*`, `claude/T-0375-*`) are not sources, and their ADR numbers are not taken. **ADR-0149 is free** on `main` and on every remote branch as of `1d5a634`.
- **Test-rule note for a later code slice.** As in ADR-0146 to ADR-0148: CLAUDE.md test rule ⑤ excludes "hook 스크립트", while a hook entry point under `hilclaw/` is a module of the layer-2 package (rules ① to ④). T-0403, T-0406, T-0409 read it as the latter. The record names the question for its code slice and does not decide it.
- **No open PR overlaps.** PR #186 (T-0324, BLOCKED by HQ-0032) touches `hilclaw/start_instance.py` and three test files only.

All work is documents and documentation reading. **No `claude` process is started on this machine** (D16; DRIVER §1-5). Every fact about Claude Code hooks comes from the official documentation (https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/headless, and https://code.claude.com/docs/en/settings if needed), read with a web fetch or `curl` and quoted with URL and date read, in a Context fact table with verification marks numbered after ADR-0148's **H22**. Facts needed include: when `PostToolUse` and `PostToolUseFailure` fire (success, MCP tool error result, refused by a `PreToolUse` hook, refused by permissions); their input fields (`tool_input`, `tool_response`, `tool_use_id`, `agent_type`); whether their output or exit status can change what the model sees, and how; matchers for MCP tools; whether they fire for a sub-agent's call; timeouts and `onFailure` for these events; whether they are run in a `-p` session. What the documentation cannot show becomes a runtime acceptance item. ADR-0015 F13 and ADR-0147 H10 already quote part of this; cite them and re-read only what is needed.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0411-<slug>`, trailer `Task: T-0411`); the D4 size cap;
  - §9 (lines 144-151): OD closing authority, the #5 notice with the `— posted by driver` footer (§8, line 140).
- `CLAUDE.md`, 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세 층 모델", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode; BLOCKED reasons), "테스트 규칙" ⑤.
- `ARCHITECTURE/decisions/ADR-0148-od18-first-case-stop-hook-commit.md` (186 lines, all). It is the model for structure, Status bullets, the fact table, Consequences and Boundaries. Note decision 4 (lines 85-92, the settings the loop writes and the run id and data root it passes) and Boundaries line 171.
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md`: Status, Context fact H1 (line 25), decisions 1, 4, 5, Consequences, Boundaries.
- `ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md`: fact H10 (line 34), decision 4, Boundaries (line 167).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: Context F13 (line 26) and line 18; decision 5 (lines 83-92); Alternatives rows 139-140; Consequences line 146; Boundaries (lines 150-160).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decisions 1 and 2 (lines 26-41), decision 9 (lines 109-118).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md`: decisions 3, 5, 7, 8 (lines 36-86).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: decision 6 (lines 104-113) and Boundaries (lines 155-164).
- `ARCHITECTURE/Requirements.md`: line 84 (**행 형식**) and the OD-18 row (line 109).
- `ARCHITECTURE/OpenDecisionProposals.md`: line 8 (**기록 규칙**) and § OD-18 (lines 281-372).
- `ARCHITECTURE/StandardScenarios.md`: §검사 결과 (from line 168), its first paragraph (기록 규약) and the "최근 재검사" line; S0, S1, S2.
- Code, as observation only: `hilclaw/turn_loop.py` lines 1-120 (docstring) and 323-353 (`_hook`, `_entry`, `_settings_text`); `hilclaw/journaled_step.py` and `hilclaw/journaled_tool.py` module docstrings; `hilclaw/tools.py` (`default_registry`); `hilclaw/turn_permissions.py` (`ROUND_MANAGER_TOOLS`); `orchestration/round-manager.md` and `orchestration/agents/*.md` (`tools` frontmatter only).

## Acceptance Criteria

1. **The record.** `ARCHITECTURE/decisions/ADR-0149-od18-first-case-post-tool-use.md` exists in the format of ADR-0001 "Record format", as ADR-0148 follows it: Status (accepted under DRIVER §9, not owner-confirmed; the two kinds of content; what it answers and that **OD-18 keeps its status word `제안됨`**; open HQs checked and not crossed; not owner-only; no data-plane change and no new dependency; nothing started; which earlier sentences it revises, none edited; what it builds on; the 7-day objection), Context (with the fact table, H23 onward), Decision (scope and terms, then answers (a) to (d) of Why), Walk-through if a hook is adopted, Alternatives considered (at least options (i) to (iv) of Why), Consequences, Boundaries, References.
2. **Every sentence is either cited (source named) or the record's own**, and every reading is marked as such. Facts about Claude Code come only from the documentation, with URL and date read; nothing is tried in a live session.
3. **The conclusion is explicit**: either "no hook is added after a call in these sessions; journaling stays with the tool layer of ADR-0015" with "The cost, plainly", or one adopted hook with every point of Why (c). A new `events.ndjson` kind, member, file or version is **not** adopted (Why, data-plane judgement).
4. **Boundaries** name at least: runs outside ADR-0120 decision 1 and other sessions; the rest of OD-18 (`SessionStart`, `PreCompact`, the kill switch, default-FAIL in general, the invariant list, the `run_id` check of a request, sub-question ②); gates (OD-3, owner-only); option (i) if it was left open; budget values (OD-19).
5. **Consequences** give: the code slices (or "none"), each within the D4 cap and tested with a stub `claude` only, and the test-rule question for them; runtime acceptance items numbered from **(lxvii)**, each with how it is closed (owner by hand, or a runtime self-check); "Less exact, not edited" (sentences of ADR-0015, ADR-0011, ADR-0010, ADR-0146 to ADR-0148, docstrings, `orchestration/` that the answer makes less exact; say how the list was found, not claimed complete); "UsageCases and StandardScenarios"; the A-13 reading; "The cost, plainly".
6. **`ARCHITECTURE/Requirements.md`**: edit the OD-18 row by the row's **행 형식** (line 84): add exactly one link to ADR-0149 with a topic of a few words after `**확정분**:`, rewrite `**잔여**:` in place so it no longer lists what ADR-0149 answers, keep the status cell's status word `제안됨`. No restatement of the record, no dated sentence or chain. If the record also answers part of OD-17 or OD-19, apply the same rule to that row; otherwise leave it.
7. **`ARCHITECTURE/OpenDecisionProposals.md`**: edit § OD-18 by the **기록 규칙** (line 8): add one `- **채택분** [ADR-0149](…) — …` line after the ADR-0148 line; rewrite in place the sentences of "제안으로 남는 부분" that ADR-0149 answers (the `PostToolUse` part of the hook list, and "저널 대상 단계의 두 줄 … 밖의 이벤트를 누가 추가하는지(PLAN P2-4)는 미결이다" if answered for the first case), keeping the proposal's wording; no restatement, no dated annotation.
8. **`ARCHITECTURE/StandardScenarios.md`**: recheck the coverage (CLAUDE.md "문서 커버리지 재검사"; at least S0, S1, S2) and update §검사 결과 by the rule in its first paragraph: the "최근 재검사" line in place; a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed.
9. **No other file** changes: no `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, `CLAUDE.md`, `PROCESS/PLAN.md`, `PROCESS/STATE.json`, UsageCases, earlier ADRs or the `HIL-Claw-data` repository. `git diff origin/main --stat` lists only `touchesFiles` (plus this task file's `Result`, if written on the branch); `git ls-files --eol` shows `i/lf` for them.
10. **Review.** Run the reviewer cycle with a fresh-context `dev-reviewer` (dev-code-review, document-mode return path), at most 7 rounds. Ask the reviewer explicitly to:
    - (a) check every Claude Code fact against the cited documentation page and date, and that nothing undocumented is stated as fact;
    - (b) check that nothing already settled by ADR-0011 decision 2 or ADR-0015 decision 5 is re-decided, and that the two step lines stay the tool layer's;
    - (c) check that no data-plane kind, member, file or version is adopted;
    - (d) check that the three existing hook entries of ADR-0146 to ADR-0148 are unchanged by the answer;
    - (e) check the register edits against **행 형식** and **기록 규칙**, and the §검사 결과 edit against its first paragraph;
    - (f) re-check each planner's judgement in Why.
    A finding starting with `SECURITY` is BLOCKED.
11. **Landing.** On Approve: rebase on `origin/main`, push to `main` directly (document mode, A-13) with the trailer `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0411`. Post the DRIVER §9 notice on issue #5 (link to the landed commit, the OD, the 7-day objection window, last line `— posted by driver`) and record its URL in `Result`.

## Out of Scope

- Any code, test, settings or definition change (later code slices, if the record adopts a hook).
- Adopting a new `events.ndjson` kind or any other data-plane schema change (A-13 BLOCKED reason).
- Gates (OD-3, owner-only) and the gate half of P2-4; budget values and the usage-limit pause (OD-19); the retry of a failed step or commit (OD-17).
- `SessionStart`, `PreCompact`, `SubagentStop`, the kill switch, default-FAIL in general, the invariant list, the `run_id` check of a request against the session's run, and every session outside ADR-0120 decision 1 (coder container, checkpoint session, self-check session).
- Editing the "Less exact, not edited" sentences of earlier records (PLAN "보류" holds many such lines; D18).
- Editing `PROCESS/PLAN.md` (the driver checks boxes; whether P2-4 can be checked with the gate half open is the driver's and the next planner's reading).
- Starting `claude` (D16), and closing any runtime acceptance item.

## Follow-ups

- (planner) If ADR-0149 adopts a hook, its code slices are the next tasks (P2-4). If not, P2-4's only open part is the gate half, which is owner-only (OD-3); the next planner then moves on in PLAN P2 order (P2-1, P2-2, P2-3, P2-6, P2-7 open parts not held by HQ-0021, HQ-0026, HQ-0048, HQ-0053).

## Result

- **Outcome**: DONE (document mode). `ARCHITECTURE/decisions/ADR-0149-od18-first-case-post-tool-use.md` landed on `main` with the register edits, pushed directly per CLAUDE.md A-13 with `Reviewed-by: reviewer agent (6 rounds, Approve)` and `Task: T-0411`.
- **Conclusion**: alternative (iv). For the turn sessions of the runs of ADR-0120 decision 1 no `PostToolUse`, `PostToolUseFailure` or `PostToolBatch` hook is added. What a call leaves stays with the tool layer: the two step lines of the one journaled tool (`correctness.check`, ADR-0015 decision 5) and each writing tool's own file. No hook verifies the lines. Option (i), appending further events, would need a new `events.ndjson` kind (a data-plane schema change) and a second concurrent appender (ADR-0006 decision 10). It is weighed, not adopted, and left open in Boundaries. Options (ii) and (iii) are rejected. The existing hook settings (two `PreToolUse` entries and one `Stop` entry, ADR-0148 decision 4) are unchanged.
- **Facts**: H23 to H28 come from https://code.claude.com/docs/en/hooks and https://code.claude.com/docs/en/headless, read 2026-10-23. The documentation does not settle three points, which are marked not verified: what `tool_response` holds for an MCP tool, whether a call a `PreToolUse` hook stopped fires either event, and whether `PostToolUseFailure` fires for a sub-agent. No `claude` process was started.
- **Register edits**:
  - `Requirements.md` OD-18 row: one link after `**확정분**:`; `**잔여**:` rewritten in place; the status stays `제안됨`.
  - `OpenDecisionProposals.md` § OD-18: one `채택분` line after ADR-0148's; "제안으로 남는 부분" rewritten in place for the `PostToolUse` hook and for who appends events beyond the two lines.
  - `StandardScenarios.md`: "최근 재검사" line only. S0, S1 and S2 were rechecked; no verdict changed and no gap was found.
- **Review**: 6 rounds with a fresh-context `dev-reviewer` (opus).
  - Rounds 1 and 2 (Request changes): the scope of which failed calls fire `PostToolUseFailure`; the stderr wording; a truncated docstring quote; the P2-4 reading against the Boundaries heading; the callers of `events.append` and `run.commit`'s torn-tail removal; the source of `step_open`.
  - Rounds 3 to 5: Approve with nits, each fixed.
  - Round 6: Approve with no findings.
  - There was no `SECURITY` finding.
- **Follow-ups**:
  - No code slice and no runtime acceptance item; the next item number stays (lxvii).
  - For these sessions, P2-4's open part is now only the gate half of "예산·gate", which is owner-only (OD-3). Whether P2-4 can be checked is the driver's and the next planner's reading.
  - The next planner moves on in PLAN P2 order (P2-1, P2-2, P2-3, P2-6, P2-7, taking only open parts not held by HQ-0021, HQ-0026, HQ-0048 or HQ-0053).
