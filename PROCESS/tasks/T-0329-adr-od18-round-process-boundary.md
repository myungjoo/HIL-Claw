---
id: T-0329
title: Record an ADR on the round boundary of a first-case run - whether one round's turn is one OS process, what starts each turn, and the working directory and definition place of the Round-Manager session (OD-18 round boundary, #8 M4; one point of OD-23)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-1, NFR-1, NFR-7, OD-18, OD-23, C-7]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/UsageCases.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 5}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first item of the P2 order (D18): round loop P2-1 to P2-4, P2-6 and P2-7, then the first run P2-5. P1-1 and P1-8 have no stop left that can be planned now:
- the `cpu_standin` operations and the registration of `sim.run`/`board.run` wait on HQ-0021 (T-0210, ADR-0068, OD-18 ⑲ (나)), HQ-0026 (T-0243) and OD-14 ① (the build/run container);
- `profiler.collect` waits on HQ-0025;
- the last planner noted that P1-8's D18 completion criterion looks met. The checkbox is the driver's to tick, not this task's.

So this task is a P2-1 slice. It is a PLAN checklist item, so the D18 priority rule does not apply to it.

No P2-1 prompt can be written before one design point is fixed: how a round of a run is carried out as Claude Code processes. That means:
- what a "turn" is in processes;
- what starts the next one;
- in which directory that session runs, and where its definition lives.

The #4 body §1 and §3 agree on "turn ≡ Round" with a fresh context per turn. They do not say whether a turn is a new OS process. Several sources leave that question open:
- OD-18 ("라운드=프로세스 경계 채택 여부", NFR-7 ① premise);
- #8 M4 (UC-3 `/loop` versus NFR-7 ①);
- ADR-0010 and ADR-0015 (Rest of OD-18);
- ADR-0054 Boundaries, "Round 0".

The working directory matters for a concrete reason. A `claude -p` session started at the root of this repository would load the driver's `CLAUDE.md`, `.claude/settings.json` hooks and `.claude/agents`, which are the development driver's and not the runtime's (ADR-0010 F6; CLAUDE.md "개발 드라이버와 런타임의 구분").

OD-18 and OD-23 are design-level ODs, not owner-only (DRIVER §9). This task closes the point with an ADR. It is a document only: no `claude` is started (D16). Any fact that only a live session can confirm becomes a runtime acceptance item.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, 2h30 time cap;
  - §5 (lines 86-114): format, naming, the `Task: T-0329` trailer, size cap;
  - §9 (lines 142-149): the ADR path and the owner notice.
- `CLAUDE.md`, these rules: "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검", "세 층 모델", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- Issue #4 body (`gh issue view 4`):
  - §1 "실행 모델 — Stateless turn";
  - §2e (the lock against two turns at once);
  - §3 to §3c ("turn ≡ Round", the three kinds of delegation, intra-round checkpoints, the round sketch).
- Issue #8 body, item M4 (`gh issue view 8`).
- `ARCHITECTURE/Requirements.md`:
  - FR-1 (line 19), NFR-1 (line 44), NFR-7 (line 50), C-7 (line 64);
  - the "행 형식" paragraph (line 84);
  - register rows OD-18 (line 109) and OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header and its "기록 규칙" (lines 1-8);
  - §OD-18 (lines 268-346, in particular lines 270-276 and sub-question ⑯ near line 340);
  - §OD-23 (lines 379-390).
- `ARCHITECTURE/UsageCases.md`: UC-1 to UC-4 (lines 69-115). UC-3 step 1 is at line 97.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph and the "최근 재검사" line of §검사 결과 (from line 168).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`:
  - facts F1-F10 (lines 20-32);
  - NFR-7 ① and server lifetime (lines 115-130);
  - Consequences "Registration" (line 148);
  - Boundaries (from line 150).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`:
  - lines 12-16 (#4 premises);
  - decision on `round` and the moments table (lines 40-56);
  - lines 84 and 96 (one writer; the death between the end of a round and its commit);
  - Boundaries (lines 145-152).
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: the path table (lines 60-75) and lines 84 and 100-106 (round numbering; roles versus agents; the writers of the run-level files).
- `ARCHITECTURE/decisions/ADR-0054-od18-runtime-self-check.md`:
  - fact K10 (line 39);
  - line 149 (how the check gives the server to a session);
  - Boundaries (lines 190-200).
- `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`: the whole record (155 lines). It is the model for the form and for the "no owner sentence decides this point" search.
- `ARCHITECTURE/decisions/ADR-0117-od14-cpu-standin-time-limits.md`: read as the current form example (Status, cited/own convention, Alternatives table, Consequences, Boundaries). Do not copy its wording.

## Acceptance Criteria

1. **Session entry check.**
   - Run `gh pr list` and read issues #4, #5, #7 and #8 as CLAUDE.md "세션 진입 점검" asks.
   - Open Draft PR #186 (T-0324) touches only `hilclaw/` and `tests/` files. If any open PR edits a file of this task's touchesFiles, stop and report it.
   - The ADR number is the next free one: ADR-0118 expected. Check `ARCHITECTURE/decisions/` and the open branches (`claude/T-0210-*` holds ADR-0068, `claude/T-0318-*` holds ADR-0112). If ADR-0118 is taken, use the next free number and rename the touched file.

2. **Owner sentences first.**
   - Search the #4 body and comments and the #5 body and comments for any owner sentence on how a round or turn maps to processes, on `/loop` or cron for the runtime, or on where the runtime's layer-1 files live. Record what you searched in Status, as ADR-0115 does.
   - If an owner sentence decides a point, cite it and do not re-decide it.
   - If an owner sentence reads two ways about a point, stop: return BLOCKED (`requirement-unclear`) with one English question for the driver's HQ.

3. **The ADR** `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`, in English, in the form of recent ADRs: Status, Context with cited facts, Decisions, Walk-through, Alternatives table, Consequences, Boundaries, References. Its scope is the runs of ADR-0076 decision 1, the first case. It decides these points:
   - **(a) Turn and process.** Is one turn of the Round-Manager one OS process of its own, a session started fresh, so that NFR-7 ① can hold? Or may one session carry several turns (UC-3 `/loop`)? Take the #4 §1/§3 agreement as fixed ("turn ≡ Round", fresh context per turn), and keep ADR-0012's moments: a process that dies inside round *k* leaves round *k* to the next turn. Say what ends a turn, and whether a turn may end before its round ends.
   - **(b) What starts each turn.** Weigh at least these options and choose:
     - a deterministic layer-2 loop that starts one session per turn until the run's files say no further turn is to run;
     - UC-3's `/loop`;
     - an OS cron or schedule re-run;
     - the user by hand (UC-2).
     If the choice differs between checkpoint mode (UC-2) and autonomous mode (UC-3), say so. Keep it consistent with the #4 §2e lock. If the choice needs a member of `STATE.json` or of another data-plane file that no record defines (for example "the run is over or waiting"), do not define it: name it as open under OD-8/OD-17.
   - **(c) Where the turn session runs and where its definition lives.** Decide in which working directory the turn session runs, so that the development driver's `CLAUDE.md`, `.claude/settings.json` and `.claude/agents` of this repository are not loaded as the runtime's. Decide which place in this repository holds the Round-Manager's definition (prompt and, if any, agent files), apart from the driver's `.claude/`. Give the reasons from ADR-0010 F3/F6 and ADR-0054 K10 and from the documentation you cite. You may also decide how the turn session is given the MCP server (`--mcp-config` as in ADR-0054, `.mcp.json`, or `mcpServers`), or leave it open with a reason. ADR-0010 calls this "partly an owner action", so do not decide any approval the owner gives.
   - Mark each sentence as **cited** (record, requirement or owner sentence named with it) or **this record's own**, as recent ADRs do.

4. **What the ADR leaves open.** Each of these is named in Boundaries, and none is decided:
   - which hooks exist and what they check, and default-FAIL and the kill switch (P2-4; OD-18 rest);
   - the gate list and what a gate checks (OD-3, #5 A-5: owner-only). The ADR may say that a turn ends while a run waits; it must not say which gates exist;
   - budget enforcement (OD-19);
   - the roster beyond the Round-Manager and the per-agent allowlists (OD-23);
   - how the coder is started (P2-2);
   - the content of round 0 and the baseline (P2-1 later slices; OD-28);
   - the commit step and who makes it (OD-8 ⑪);
   - whether the self-check runs again at a round boundary (OD-18 ⑯ (가)). Answer it only if decision (a) or (b) settles it, and say so;
   - resume from a chosen point (UC-4);
   - the CLAUDE.md invariant list.

5. **Runtime acceptance items (D16).** Some facts the decisions rest on can be confirmed only by a live, logged-in `claude` on a C-7 machine. Examples:
   - what a `-p` session started in the chosen directory loads and does not load;
   - whether a sub-agent definition placed there is found;
   - that the chosen way of giving the server works.
   List them in a "Runtime acceptance items" bullet of Consequences: nothing was tried and nothing was required of the development machine. Copy that list into Result so the driver can raise one `runtime-acceptance` HQ. Do not start `claude`, and do not claim any such fact as verified unless a documentation page you cite states it.

6. **Register and proposals**, following the recording rules written in those files; do not copy the wording of earlier task files:
   - `Requirements.md`: the OD-18 row gets one link to the new ADR with a few-word topic, per the "행 형식" paragraph (line 84). If decision (c) closes a point of OD-23, its row gets the same kind of link. Rewrite the rows' open parts ("잔여" / proposals) in place where the ADR answers them. No restatement of the ADR, no dated paragraph. If NFR-7 ①'s "*전제*" sentence becomes inexact, do not rewrite the requirement: name it under "Not edited and now less exact" in the ADR's Consequences.
   - `OpenDecisionProposals.md`, per its header "기록 규칙" (line 8): one `- **채택분** [ADR-0118](…) — …` line in §OD-18 (and in §OD-23 if (c) closes an OD-23 point). Rewrite in place the open parts the ADR answers, for example "라운드 = 프로세스 경계도 … 채택되거나 기각되지 않았다" in the "제안으로 남는 부분" bullet and the M4 bullet at line 273. If ⑯ (가) is answered in part, update the state at the end of that sub-question in place. No dated note.
   - `UsageCases.md`: rewrite in place the parenthesis of UC-3 step 1 (line 97) so that it reflects decision (b) for the first case and links the ADR. Change no other UC sentence unless the ADR makes it false; if so, list it in Result.
   - `StandardScenarios.md`: re-check coverage by its rules (CLAUDE.md "문서 커버리지 재검사"). Update the "최근 재검사" line of §검사 결과 in place, as its first paragraph says. Add a history entry only if a verdict changed.

7. **Scope and size.**
   - `git diff --stat origin/main` lists only the touchesFiles (plus this task file's Result if the driver asks).
   - About 300 changed lines or fewer outside the ADR.
   - No code, test, CI, `pyproject.toml`, `.claude/`, `CLAUDE.md`, `README.md` or `PROCESS/` edit.
   - No data-plane schema change: no new member, file, kind or version.
   - Do not edit issue #8. Name the M4 resolution for the first case as a follow-up for the integrator in Consequences and in Follow-ups.

8. **D16.** No `claude` program is started (no subcommand, no flag), and no board, accelerator or API key is required.

9. **Merge.** Document mode under CLAUDE.md A-13:
   - branch `claude/T-0329-adr-od18-round-process-boundary`;
   - context-isolated reviewer cycle (dev-code-review, at most 7 rounds) until Approve;
   - rebase on `origin/main`, then push to main directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0329`;
   - delete the branch;
   - post the DRIVER §9 owner notice on #5 (English, the ADR link, the 7-day objection window, last line `— posted by driver`).

## Out of Scope

- Writing the Round-Manager prompt or any agent, skill or hook file. Any code, among it the turn-starting loop, if (b) chooses one.
- `sim.run`/`board.run` registration, the `cpu_standin` operations, and anything blocked by HQ-0021, HQ-0025, HQ-0026, HQ-0032, HQ-0034 or OD-14 ①.
- Editing any existing ADR. Sentences that become less exact are listed in Consequences, not edited.
- Ticking any PLAN checkbox.
- The held ADR wording follow-ups in PLAN's 보류 section.

## Follow-ups

- Next P2-1 slices once this lands:
  - the Round-Manager definition at the place decision (c) names;
  - if (b) chose a layer-2 loop, its code task, verified only with a test-written stub `claude` (D16);
  - the round-0 procedure.
- Integrator: #8 M4 for the first case, and the NFR-7 ① / UC-3 wording if the ADR lists them as less exact.

## Result
- Landed: a2d9e96 on main (document mode, branch claude/T-0329-adr-od18-round-process-boundary deleted); review: 7 rounds, Approve (`Reviewed-by` trailer).
- ADR-0118 (first-case runs): one turn = one Claude Code session process; a layer-2 turn loop starts each turn (cron/a person restarts the loop, not a turn; `/loop` rejected); the turn session runs in a session directory outside both checkouts; the runtime definition lives under `orchestration/` and is copied in at every turn; the main session gets the server by `--mcp-config` + `--strict-mcp-config`.
- Synced: OD-18/OD-23 register rows and proposal sections, UC-3 step 1, StandardScenarios latest re-check (no verdict change, no gap).
- Owner notice (§9): https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6260591063
- Runtime acceptance items (i)-(vii) notified as HQ-0035 (`runtime-acceptance`, non-blocking).
- Follow-ups: integrator — #8 M4 (first case), NFR-7 ① wording, S2 steps 1/3, CLAUDE.md "세 층 모델" and the #4 §2 agent-memory row; nit: OD-18 ⑯ (마) status is less exact. Next P2-1 slices: turn loop code (stub `claude` only), session-dir preparation, the definition under `orchestration/`, round-0 procedure. Note: `orchestration/` is not in the A-13 document-mode list, so edits there run in code mode.
