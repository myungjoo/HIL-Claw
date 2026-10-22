---
id: T-0408
title: Write ADR-0148 - whether a first-case turn session gets a Stop hook that holds the commit at the end of a turn (ADR-0143 decision 2), in which form (refuse the stop while a commit is owed, commit in the hook, or nothing beyond the prompt and the next entry), how such a hook learns its run, and what it does when it cannot tell (Stop-commit part of PLAN P2-4; part of OD-18)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-11, NFR-1, OD-18, OD-8, "PLAN P2-4"]
dependsOn: [T-0405, T-0406, T-0407]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0148-od18-first-case-stop-hook-commit.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-4 is still unchecked. It covers the runtime hooks: "PreToolUse 예산·gate 검사, PostToolUse 저널링, Stop 커밋 강제", and it says **OD-18 and OD-19 are to be closed by ADR (DRIVER §9)**. It is a PLAN checklist item in the group that PLAN's P2 header runs before P2-5, so the D18 priority rule (DRIVER §6) does not apply to it.

What is done as of `main` `e9e6620`:
- the caller check hook: ADR-0146, with T-0403 and T-0404;
- the round-budget check on the two spending tools: ADR-0147, with T-0406 (`hilclaw/budget_check.py`) and T-0407 (second `PreToolUse` entry written by `hilclaw/turn_loop.py`).

What remains of P2-4:
- the gate half of "예산·gate": owner-only (OD-3, #5 A-5) and not planned here;
- `PostToolUse` journaling;
- the `Stop` commit.

This task takes the **Stop commit**. Three earlier records name it under Boundaries as left to P2-4: ADR-0127, ADR-0143 ("The Stop hook that would enforce a commit at a turn's end") and ADR-0147 ("the `Stop` hook (ADR-0127, ADR-0143)"). The proposal in OpenDecisionProposals § OD-18 lists "`Stop`(commit 강제)", and its "제안으로 남는 부분" bullet says no `Stop` hook has been adopted or rejected. `PostToolUse` journaling is left to a later task, and so is anything else under the OD-18 rest.

**What holds the commit today** for the runs of ADR-0120 decision 1 (first case):
- **The Round-Manager's prompt.** `orchestration/round-manager.md` "The end of a session" (ADR-0143 decision 2) has the model call `mcp__hilclaw__run_commit` as its last act before every end of its session that follows a successful entry step 0.
- **The next turn's entry step 0.** It commits what a dead turn left (ADR-0143 decision 2, O1).
- **Step 1 of the turn loop.** It starts a further turn in owed P2, through `hilclaw.further_turn` and `hilclaw.run_commit.commit_owed` (ADR-0143 decision 6).

A live Round-Manager that skips the call at its end leaves the turn's work uncommitted until the next start. That start may never come for an unattended run (ADR-0143 "The cost, plainly"). The model's adherence is runtime acceptance item (xlvii) of ADR-0143. ADR-0146 treated a hold that lives only in the prompt as a gap to weigh before the first run, and this record asks the same question for the end commit.

**Scope, to keep one record reviewable.** It covers the turn sessions of the runs of ADR-0120 decision 1 only, and the end commit of ADR-0143 decision 2 only. It answers:

(a) **What a hook could hold, and what it cannot.** A `Stop` hook fires when the main session's model finishes responding. Whether it fires on a crash, a kill, a usage limit or an API error, and whether a related event (`StopFailure`, `SessionEnd`, `SubagentStop`) exists, comes from the official documentation only. ADR-0143 already sends a dead turn's work to the next entry. The record says plainly which live ends a hook would add a hold to. It also states the ends where the Round-Manager rightly makes no call, so that a hook must not force one there:
- after a prompt with no valid run id (ADR-0123 decision 4);
- after a failed `run.commit`, at entry step 0 or at an end ("do not call it again in this turn": ADR-0143 decision 2, ADR-0127 decision 5).

(b) **Whether a hook is adopted, and in which form.** Weigh at least these alternatives:
- (i) a `Stop` command hook that refuses the stop (`decision: "block"` with a reason, or exit 2, as the hooks page has it) while `hilclaw.run_commit.commit_owed` answers true, so that the Round-Manager makes the call;
- (ii) a hook that makes the commit itself. This one is weighed against W1 (C2 of ADR-0127), which says every commit is the Round-Manager's through `run.commit` only, and against ADR-0143 alternative (c), the second committer it rejected;
- (iii) a `SessionEnd` hook or another event, if the documentation has one that fits;
- (iv) nothing beyond the prompt, the next entry and step 1.

The record may conclude that no hook is adopted. It then says so, states the cost plainly and names what stays open.

(c) **If one is adopted**, the record says:
- **How the hook learns the run.** The `Stop` input carries no `run_id`. The command-line entry (`hilclaw/turn_start.py`) knows the run id, but `hilclaw.turn_loop.run` takes none, and ADR-0123 hands the session the run id through the prompt only, with no place. Candidates include a hook argument that the loop writes, which would need a new parameter of `turn_loop.run`; say what this revises.
- **How it reaches the data root**: as an argument, as ADR-0147 decision 4 does, or by another way the record grounds.
- **What it reads**: `commit_owed` runs the machine's `git` read-only, unlike the two existing hooks, which start no process.
- **How it avoids a loop of refused stops.** Use `stop_hook_active` or whatever the documentation gives, and keep in mind that each refused stop spends plan usage.
- **How it leaves the two no-call ends of (a) alone.**
- **What it does when it cannot tell**: let the stop through, or refuse it. Refusing on fault, as ADR-0146 decision 5 and ADR-0147 decision 5 do, could keep a session spending, so weigh it for this hook on its own. The general default-FAIL of OD-18 stays open.
- **The delivery.** The turn loop already writes the session's `.claude/settings.json` with exactly two `PreToolUse` entries and nothing else (ADR-0146 decision 4 as revised by ADR-0147 decision 4). The record says which sentence it revises, and it keeps the two existing checks unchanged.
- **What the model is told.** One fixed line or reason; the wording belongs to the code slice.

(d) **What follows from it**:
- the code slices (each within the D4 cap of DRIVER §5, each tested with fixtures and a stub `claude` only);
- the runtime acceptance items, numbered after ADR-0147's **(lxii)**;
- the "Less exact, not edited" list.

**Planner's judgements** (from `main` `e9e6620`; **the reviewer is asked to re-check each**):

- **Not owner-only.** OD-18 is a design-level OD, and ADR-0146 and ADR-0147 closed parts of it under DRIVER §9.
  - The owner's answer to HQ-0043 (O1, O2, quoted in ADR-0143 Status) governs *which* turn ends commit and what a commit leaves out. This record carries those answers out and does not reinterpret them.
  - If a coherent answer needs a new meaning of O1, O2 or #5 A-3, the executor stops and returns BLOCKED (`requirement-unclear`) with the question. The same applies if it needs a gate (OD-3), a retry policy for a failed `run.commit` (OD-17; ADR-0143 Boundaries) or a budget value (OD-19).
- **No data-plane schema change and no new external dependency** (CLAUDE.md A-13).
  - A hook that only reads adds no member, event kind, file or `schema_version`.
  - A hook that commits changes which commits the data repository receives. ADR-0143 Status treated that as no data-plane schema change; the reviewer judges whether the same reading holds here.
  - Any new `events.ndjson` kind or payload is out of scope: avoid it, or return BLOCKED.
- **No open HQ is crossed.**
  - HQ-0053 (the coder's container), HQ-0021 and HQ-0026 (`sim.run`/`board.run`) and HQ-0048 (the selection role) are unrelated; do not presume their answers.
  - HQ-0061 (ADR-0146 items (lvi) to (lx)), HQ-0062 (ADR-0147 items (lxi), (lxii)) and the ADR-0127/ADR-0143 items (xv) to (xvii) and (xlvii) are runtime acceptance items. Cite them, but do not treat them as confirmed.
  - Unlanded branches (`claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0318-*`, `claude/T-0361-*`, `claude/T-0375-*`) are not sources, and their ADR numbers are not taken.
  - ADR-0148 is free on `main` and on every remote branch as of `e9e6620`.
- **Test-rule note for a later code slice.** T-0403 and T-0406 read CLAUDE.md test rule ⑤ ("hook 스크립트") as not covering a hook entry point that is a module of `hilclaw/`, so rules ① to ④ applied. Their reviewers accepted that reading as Info. The record names the same question for its code slice and does not decide it.
- **No open PR overlaps.** PR #186 (T-0324, BLOCKED) touches `hilclaw/start_instance.py` and three test files only.

All work is documents and documentation reading. **No `claude` process is started on this machine** (D16; DRIVER §1-5). Every fact about Claude Code hooks comes from the official documentation (https://code.claude.com/docs/en/hooks, https://code.claude.com/docs/en/settings, https://code.claude.com/docs/en/headless). Read it with a web fetch or `curl`, and quote it with the URL and the date read, in a Context fact table with verification marks as ADR-0146 and ADR-0147 do. The facts needed include:
- when `Stop` fires and when it does not;
- its input fields;
- how a block makes the model continue;
- `stop_hook_active`;
- whether `Stop` hooks run in `-p` mode;
- the `SessionEnd` and `StopFailure` events, if any;
- how a `Stop` matcher is written, if one applies;
- timeouts and `onFailure`.

Whatever the documentation cannot show becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, time cap;
  - §5 (lines 86-114): task format, naming convention, size cap;
  - §9 (lines 144-151): OD closing authority, the owner notice on #5, the 7-day objection period.
- `CLAUDE.md`: "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode) and "세 층 모델".
- `ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md`, whole. It is the closest model for form and scope, the Context fact table (H-rows) and its marks, the revision sentences in Status, the runtime acceptance numbering (last item (lxii)) and the "Less exact, not edited" list.
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md`: Context (lines 16-32), decisions 4 to 6 (lines 61-92), Consequences and Boundaries (lines 130-165).
- `ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md`, whole (136 lines). Note in particular Status O1/O2, decisions 2, 3 and 6, Alternatives (c), item (xlvii) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`: decisions 2 to 6 (lines 37-84) and runtime acceptance items (xv) to (xvii) (lines 144-146). Find W1 / C2 by searching for "C2".
- `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md`: decisions 2 to 4 (lines 41-61).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decisions 2, 3 and 6 (lines 45-64, 90-95).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decision 2 (lines 57-66).
- `ARCHITECTURE/Requirements.md`:
  - FR-11 (line 29) and NFR-1 (line 44);
  - **the "행 형식" rule (line 84)**;
  - the OD-8 and OD-18 rows (search for "| OD-8 |" and "| OD-18 |").
- `ARCHITECTURE/OpenDecisionProposals.md`: **the "기록 규칙" bullet of the header (line 8)** and § OD-18 (from line 281; read at least its first bullets and the "제안으로 남는 부분" bullet).
- `ARCHITECTURE/StandardScenarios.md`: line 26 and **the first paragraph of §검사 결과 (lines 168-172: the 기록 규약 and the "최근 재검사" line)**. Also the S2 row; search for "commit".
- `orchestration/round-manager.md`: "The end of a session" (lines 52-68), entry step 0 (lines 75-80) and the closing steps (lines 163-189).
- Code:
  - `hilclaw/run_commit.py`: lines 1-45 (docstring) and 170-215 (`owed_rounds`, `commit_owed`);
  - `hilclaw/turn_loop.py`: lines 1-60 (docstring), 299-321 (`_entry`, `_settings_text`) and the signature of `run` (line 417);
  - `hilclaw/turn_start.py`: lines 1-30 and 240-275;
  - `hilclaw/further_turn.py`: lines 1-40;
  - `hilclaw/budget_check.py`: lines 1-50.

## Acceptance Criteria

1. **New file** `ARCHITECTURE/decisions/ADR-0148-od18-first-case-stop-hook-commit.md`, in the form of ADR-0147: Status, Context, Decision with a Walk-through, Alternatives considered, Consequences, Boundaries, References.
   - **Status** says:
     - that it is accepted under DRIVER §9 and the owner has not confirmed it;
     - which part of OD-18 it answers, and for which runs;
     - which sentences of earlier records it revises without editing them (at least ADR-0146 decision 4 as revised by ADR-0147 decision 4, if settings change; and ADR-0123, ADR-0127 or ADR-0143 sentences, if touched);
     - that it is a record, not code, and that no `claude` was started (D16).
   - **The record separates cited content from its own**, as ADR-0143 and ADR-0147 do. The owner's O1 and O2 are quoted, not re-derived.
2. **Each of (a) to (d) in "Why" is answered or explicitly left open** with a reason. In particular:
   - the two no-call ends (no valid run id; after a failed `run.commit`) are handled without contradicting ADR-0143 decision 2;
   - the loop guard is stated;
   - the fault behaviour is stated for this hook alone, with its cost.
   - If no hook is adopted, the cost of that and what stays held only by the prompt are stated plainly.
3. **Context fact table**: every Claude Code fact the decision relies on is quoted with its URL and the date read, and marked verified or not verified. Each unverified fact the decision depends on becomes a runtime acceptance item, numbered from **(lxiii)** on. Each item says how it would be closed (by the owner by hand, or by a runtime self-check).
4. **Alternatives considered** has a table covering at least (i) to (iv) of "Why" (b), with the reason for each rejection. The row for (ii) cites W1 (C2 of ADR-0127) and ADR-0143 alternative (c).
5. **Consequences** lists:
   - the code slices in order, each named by file and kept within the D4 cap, each tested with fixtures, a temporary git repository and a stub `claude` only (D16);
   - the test-rule question of "Why", left undecided;
   - the runtime acceptance items;
   - "Less exact, not edited" (found by a search of `ARCHITECTURE/decisions/`, `hilclaw/` and `orchestration/`, not claimed complete);
   - an A-13 reading (document mode; no data-plane change, no dependency);
   - "The cost, plainly".
6. **Boundaries** names at least:
   - runs outside ADR-0120 decision 1;
   - `PostToolUse` journaling, `PreCompact`, the kill switch, default-FAIL in general and the CLAUDE.md invariant list (rest of OD-18 and P2-4);
   - gates (OD-3, owner-only);
   - the retry of a failed `run.commit` (OD-17);
   - the push (#5 A-3; ADR-0127 decision 7);
   - sub-agent stops, if not decided.
7. **`ARCHITECTURE/Requirements.md`**: edit the OD-18 row by the "행 형식" rule written in that file (line 84). Add one link to ADR-0148 for what it settles, and rewrite the row's open part in place so that it no longer names what ADR-0148 settles. Add no dated paragraph and do not restate the record. Do not change OD-18's status unless the rule says so. If ADR-0148 settles nothing of OD-8, leave the OD-8 row alone.
8. **`ARCHITECTURE/OpenDecisionProposals.md`** § OD-18: edit by the header's "기록 규칙" (line 8). The bullet that says no `Stop` hook has been adopted or rejected is rewritten in place to reflect ADR-0148, with one link and no restatement of the record.
9. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage by the rules of that file (CLAUDE.md "문서 커버리지 재검사"), and update §검사 결과 by the 기록 규약 in its first paragraph (lines 168-172): replace the "최근 재검사" line in place, with no dated paragraph added. Change no S-row unless a sentence becomes false.
10. No other file changes: no code, test, CI, `orchestration/`, `.claude/`, settings file, earlier ADR or `HIL-Claw-data`.
11. Document mode (CLAUDE.md A-13):
    - reviewer cycle per dev-item-address steps 10 to 12;
    - rebase on `origin/main`, then direct push to `main`;
    - commit trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0408`;
    - after landing, the DRIVER §9 owner notice on #5, ending with `— posted by driver`.
    - New runtime acceptance items are reported in `## Result`, so that the driver can record one HQ (`runtime-acceptance`, non-blocking) for them.

## Out of Scope

- Any code: the hook program, the `turn_loop` settings change, the `turn_start` change and their tests are later code-mode tasks, which the planner makes from this record's Consequences.
- `PostToolUse` journaling and every other part of P2-4 or OD-18 not named in "Why".
- Gates (OD-3, owner-only), budget values (OD-19), retry policy (OD-17), push and remote (#5 A-3).
- Editing earlier ADRs, `orchestration/round-manager.md` or any docstring. Those go into the "Less exact, not edited" list.
- Starting `claude` in any form, and requiring a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- Code slice 1 (code mode): the stop-check program, a new module of `hilclaw/` and its test file (ADR-0148 decisions 4, 5; `commit_owed`, `check_run_id`; fixtures and temporary git repositories). It settles the test-rule ⑤ question again or raises it.
- Code slice 2 (code mode): `hilclaw/turn_loop.py` gains the required keyword-only `run_id` and writes the `Stop` entry beside the two `PreToolUse` entries; `hilclaw/turn_start.py` passes its run id; docstrings of both; stub `claude` only.
- Both slices are PLAN P2-4 work (a checklist item), so the D18 hold rule does not apply to them.

## Result

- **DONE.** ADR-0148 landed on `main` in document mode, squashed into one commit with trailers `Reviewed-by: reviewer agent (2 rounds, Approve)` and `Task: T-0408`.
- **Review**: 2 rounds with a context-isolated `dev-reviewer`. Round 1: Approve with 2 Minor (SIGINT end; a timed-out `Stop` hook marked verified), 2 Nit, 2 Info, all addressed. Round 2: Approve, Info only.
- **ADR outcome**: for the turn sessions of the runs of ADR-0120 decision 1, a `Stop` command hook refuses one stop of the main session (exit 2, one fixed line) while `hilclaw.run_commit.commit_owed` answers true and `stop_hook_active` is exactly `false`. The line asks the Round-Manager to call `run.commit` as "The end of a session" says, or to end at once after a prompt with no valid run id or a failed call. The hook never commits (W1, ADR-0143 alternative (c)); it lets the stop through whenever it cannot tell (`onFailure` has no effect on `Stop`). `SessionEnd`, `StopFailure` and a committing hook are rejected; no `SubagentStop` entry. The run id reaches the hook as an argument through a new required keyword-only parameter of `turn_loop.run`, the data root as in ADR-0147. It revises, without editing, ADR-0146 decision 4 as revised by ADR-0147 decision 4 (settings: two `PreToolUse` entries and one `Stop` entry), ADR-0123 decision 3 ("knows no run") and ADR-0127 decision 2 (whether a hook does anything with commits). OD-18 keeps `제안됨`; the OD-8 row is untouched.
- **Register edits**: Requirements OD-18 row (one link and the 잔여 rewritten in place), OpenDecisionProposals § OD-18 ("제안으로 남는 부분" bullet rewritten in place, one 채택분 line), StandardScenarios "최근 재검사" line (S0, S1, S2 rechecked; no verdict change, no gap).
- **New runtime acceptance items** (for one HQ, reason `runtime-acceptance`, non-blocking): (lxiii) the `Stop` entry of the written settings runs when the main session of a `-p` turn session finishes its reply, before the process exits, and not for sub-agents; (lxiv) exit 2 with one stderr line makes the `-p` main session go on with the line, and the following `Stop` carries `stop_hook_active` `true`, also after a tool call; (lxv) the hook process finds the server's `git`, `commit_owed` finishes within the hook's timeout, and a timed-out `Stop` hook lets the stop through; (lxvi) a live Round-Manager told the line calls `run_commit` once and ends, and at the two no-call ends ends at once.
- No `claude` process was started (D16). Claude Code facts were read on 2026-10-22 from the hooks, headless and env-vars pages.
