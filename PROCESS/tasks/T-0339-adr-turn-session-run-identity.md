---
id: T-0339
title: Write ADR-0123 — how a turn session of a first-case run learns which run it carries (its run id, and the place of the run if the session needs it), so that the round-0 part of the Round-Manager prompt can be written (OD-18 round boundary, one point of OD-23, for the runs of ADR-0120 decision 1)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-13, NFR-1, NFR-7, OD-18, OD-23, OD-8, S0, S1]
dependsOn: [T-0329, T-0331, T-0338]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one of its slices, so the D18 priority rule does not apply. The P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) needs a Round-Manager that reads and writes the files of *its* run.

What exists today:

- `python -m hilclaw.turn_start <run_id>` (T-0338, PR #193, main 8ea06d5) knows the run id. It starts each turn through `hilclaw.turn_loop.run` with the fixed prompt `PROMPT`, which does not name the run.
- Its module docstring states the gap: "**Open**: how a turn session learns which run it carries. No record decides it, so the prompt does not name the run and nothing else hands it over." The T-0338 Follow-ups name this as the next question. It must be answered before the round-0 part of the Round-Manager prompt: ADR-0120 decision 2 has the Round-Manager read `STATE.json` and write the first file into the run directory, and every journaled tool request carries `run_id` (ADR-0015, the envelope table).
- No accepted record decides it, and the OD-18 and OD-23 sections of OpenDecisionProposals list no sub-question for it.

This is a design-level point of OD-18 (round boundary: what a turn session is given) and of OD-23 (the Round-Manager's inputs). It is not owner-only (DRIVER §9: none of #5 A/B, C-6, OD-25, OD-3), so this task writes the ADR that closes it for the first case (DRIVER §6, §9). The code slice that applies the answer is the next task.

**Facts the executor will need to weigh, observed by the planner and not decisions:**

- The turn loop's prompt rule is `[A-Za-z0-9 .,_]+` (`hilclaw/turn_loop.py`, `_PROMPT`). A run id matches `[a-z0-9][a-z0-9_-]{0,63}` (`hilclaw/layout.py`, ADR-0004 decision 8). The id a component builds has the form `<time>-<random>` with a hyphen (ADR-0027 decision 2). So a prompt that names a built run id is refused by today's rule.
- The turn session gets the caller's environment unchanged. The MCP server's environment is set in the configuration file the loop writes (only the data-root variable, `hilclaw.config.ENV_LOCAL_PATH`). The session directory is made per turn and holds a copy of `orchestration/` (ADR-0118 decisions 4 to 6; `hilclaw/turn_loop.py` docstring).
- Candidate channels include: the prompt; an environment variable of the session; a file the loop or the entry writes into the session directory; the definition copy carrying it; the server's environment, with a tool that reports it. Each has a cost: the prompt rule, a hook's view of tool input, NFR-7 ① replaceability, NFR-1 (nothing a run needs lives in the session directory), and what a later lock or resume (OD-17, OD-8 ①) would need.

The executor chooses the answer and weighs the alternatives in the record. If the choice turns out to need an owner sentence that does not exist, return BLOCKED (`requirement-unclear`) instead of inventing.

Open Draft PR #186 (T-0324, BLOCKED on HQ-0032) touches only `hilclaw/start_instance.py` and three test files. None of them is in this task's touchesFiles.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, branch contention, the 2h30 time cap;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0339` trailer, size cap;
  - §9 (lines 142-149): the D6 route for a design-level OD, the owner notice, and the owner-only list.
- `CLAUDE.md`, these rules: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`: the document-mode path.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format" (from line 146).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`:
  - Status (lines 3-21), as a model of the owner-sentence search;
  - Decision §1-§6 (lines 48-123): above all §3 ("What starts the loop"), §4 (session directory, "Workspace trust", "Agent memory is not settled"), §5 (definition copy) and §6 (server configuration);
  - Walk-through (from line 124), Consequences (lines 154-185), Boundaries (lines 186-201).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: decisions 1 and 5 (lines 38-44, 77-89), Consequences (lines 129-144), Boundaries (lines 145-159).
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: decisions 1, 2 and 4 (lines 38-69), Consequences item (1) (around line 95).
- `ARCHITECTURE/decisions/ADR-0115-od8-instance-start-performer.md`: decisions 1-3 (lines 44-89). The start returns the run id to its caller. Who calls the start stays open.
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: the envelope table and the journaled-request bullet (lines 70-82); "No access control" (line 114).
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md`: decisions 1 and 2. `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decision 8 (the run id pattern).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: decision 7 and decision 8 (no access control).
- Code, as observation only (this task changes no code):
  - `hilclaw/turn_start.py`: module docstring (lines 1-85) and `PROMPT`;
  - `hilclaw/turn_loop.py`: module docstring (lines 1-120), `_PROMPT` (line 125) and `run` (the configuration file and the server environment);
  - `hilclaw/turn_definition.py`: module docstring and `put`;
  - `orchestration/round-manager.md` (whole file, 21 lines).
- `ARCHITECTURE/Requirements.md`: FR-1, FR-13, NFR-1, NFR-7, C-7; the "행 형식" paragraph (line 84); register rows OD-8 (line 99), OD-17 (line 108), OD-18 (line 109), OD-23 (line 114).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet of the header (line 8); § OD-18 (lines 271-384); § OD-23 (lines 385-398).
- `ARCHITECTURE/UsageCases.md`: UC-2, UC-3 and UC-4 (the runs a person or a schedule starts and resumes).
- `ARCHITECTURE/StandardScenarios.md`: "검사 규칙" (from line 13); S0 (line 30), S1 (line 45); "# 검사 결과" with its first paragraph and the "최근 재검사" line (lines 168-172), and the S0/S1 rows of the 판정표.
- GitHub, before editing (CLAUDE.md "세션 진입 점검"): `gh pr list`; issues #4, #5, #7 and #8, for the owner-sentence search below.

## Acceptance Criteria

1. **New record `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md`** in the ADR-0001 record format: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References. If ADR-0123 is already taken on `origin/main` when the task starts, use the next free number, adjust the file name, and say so in Result.
2. **Status**:
   - It is accepted under DRIVER §9 (D6) by the reviewer's approval and is not confirmed by the owner. It states the 7-day objection window.
   - It separates cited content from the record's own.
   - It reports an **owner-sentence search** over #4, #5 (comments without the "posted by driver" marker), #7 and #8, with its search terms (for example: run_id, run id, 어느 run, which run, prompt, 프롬프트, 환경변수, environment, session, 세션, Round-Manager, STATE.json 진입점, 단일 진입점). It quotes each sentence found that touches the point, read for what it says and no further.
   - It states that the point is design-level (OD-18, OD-23) and needs none of #5 A or B, C-6, OD-25 or OD-3.
   - It lists what it builds on: at least ADR-0015, ADR-0118, ADR-0120 and ADR-0122, with "if one of them is reverted, this record is revisited with it".
3. **Scope**: the runs of ADR-0120 decision 1 (the first case), driven by the turn loop of ADR-0118 decision 3 through its command-line entry `hilclaw.turn_start`. Nothing is required or allowed of other runs.
4. **Decision** answers each of these points for that scope, each with its reason:
   - (a) **What the turn session must learn about its run**: the run id, and whether the session also needs the place of the run (the data root or the run directory). The data root already reaches the MCP server through the server's environment (ADR-0118 §6 as built). If the record finds that the Round-Manager itself needs the place only because of how it will reach `hilclaw.run_state_file.replace`, it says so and leaves that means open (point (d)). It does not choose that means.
   - (b) **Through which channel it reaches the session, and which side hands it over**: the entry, the loop or the definition. The record says whether the channel is the same in every turn of a run. It says what the Round-Manager does when the run id is missing or is no valid run id (reported, nothing written into any run), in kind only. If the answer needs the loop's prompt rule or the entry's fixed prompt to change, the record says so as a consequence for the code slice and does not edit code.
   - (c) **What the session may do with it**, in kind: the run it names is the only run whose files the turn reads or writes, and the only `run_id` its tool requests carry. Say how this relates to ADR-0015's "No access control" and ADR-0010 decision 8: this record adds no access control unless it says so, with its cost.
   - (d) **What it keeps from earlier records, citing them**: the loop makes no judgement, calls no model and is no FR-10 tool; it writes nothing into the run (ADR-0122 decision 1); nothing a run needs lives in the session directory (NFR-1; ADR-0118 §4); `STATE.json` stays the single entry point of a turn (#4 §1). If the chosen channel writes a file into the session directory, the record says why that does not break these.
5. **Alternatives considered** has at least one row for each of these, each with its cost (prompt rule, hook visibility, NFR-7 ① replaceability, NFR-1, a later lock or resume): run id in the prompt; an environment variable of the session; a file in the session directory written by the loop or the entry; the definition copy carrying the run id; the server's environment with a tool that reports it; leave it open (the round-0 prompt would wait).
6. **Consequences** names:
   - the code slice it enables: the change to `hilclaw/turn_start.py`, and to `hilclaw/turn_loop.py` if needed, that hands the run over; tested against a stub `claude` only (D16);
   - what the round-0 part of the Round-Manager prompt still waits on: how the Round-Manager reaches `replace` (OD-23, OD-18), OD-18 ⑯ (가) and OD-8 ⑪;
   - the sentences of accepted records and code docstrings it makes less exact, found by a search of `ARCHITECTURE/decisions/` and `hilclaw/` for "which run", "does not name the run" and "prompt", and listed, not edited;
   - the A-13 reading: document mode, **no data-plane change** (no member, file, kind, value or version, no validator change);
   - runtime acceptance items, if any. Any fact only a live Claude Code session can establish (for example whether a session sees a given environment variable or prompt text as the record assumes) is listed and not tried (D16). If one is new (not among ADR-0118's (i)-(vii) or ADR-0122's (viii)), say so in Result so the driver can raise an HQ with reason `runtime-acceptance`.
7. **Boundaries** keep these open, each with its OD:
   - how the Round-Manager reaches `replace` and the roster (OD-23, OD-18);
   - the lock of two loops on one run (rest of OD-17);
   - who calls the start of ADR-0115 (OD-8, OD-23);
   - resumed, continued or branched runs (OD-8 ①);
   - the self-check at round boundaries (OD-18 ⑯ (가));
   - the commit step (OD-8 ⑪);
   - permissions and hooks (rest of OD-18, P2-4);
   - gates (OD-3, owner-only);
   - runs outside the scope.
8. **Register and proposals, following the rules written in those files** (not the wording of earlier task files):
   - `ARCHITECTURE/Requirements.md`: follow its "행 형식" (line 84). For each OD whose part the record answers (at least OD-18; OD-23 if point (a) or (b) answers a part of the Round-Manager's input contract), add **one link** to ADR-0123 with a few words of topic to that row's `**확정분**:`, and rewrite its `**잔여**:` in place. Do not restate the record and add no dated paragraph. Status cells change only as the "행 형식" allows.
   - `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). In each section concerned (§ OD-18, and § OD-23 if it applies), add one `- **채택분**` line linking ADR-0123 with what it covers. Rewrite the open parts in place ("제안으로 남는 부분" and any sub-question ending touched, with `→ 부분 답: … 남음: …` / `→ 답함: …`). The proposal text and the sub-question wording stay. No dated note and no restatement of the record.
   - `ARCHITECTURE/StandardScenarios.md`: re-check at least S0 and S1 under "검사 규칙" (CLAUDE.md "문서 커버리지 재검사"), and record the result as the first paragraph of "# 검사 결과" says. Rewrite the "최근 재검사" line in place. Add a "판정 변화 이력" entry only if a verdict changed or a gap was found or closed. In the 판정표 notes, name only the FRs and the ODs (with sub-question numbers) still open.
   - UsageCases is edited only if a sentence becomes false. Say in Result whether one did.
9. **No invention.** The record cites a source for every sentence that is not its own, decides nothing owner-only, and settles no point listed in AC 7. If the reviewer finds a choice that needs an owner sentence, stop and return BLOCKED (`requirement-unclear`, or the §9 owner-only reason) with the question.
10. **D16.** No `claude` is started (no subcommand, no flag), and nothing needs a board, an accelerator or an API key. No fact is tried in a live session.
11. **Scope of the change.** `git diff --stat origin/main` lists only the touchesFiles and this task file's Result. No edit to `hilclaw/`, `orchestration/`, `tests/`, CI, `.claude/`, `CLAUDE.md`, `README.md`, `PROCESS/` (other than this file's Result) or any earlier ADR. No new dependency.
12. **Merge (document mode, CLAUDE.md A-13).**
    - Work on branch `claude/T-0339-adr-turn-session-run-identity`.
    - Run the context-isolated reviewer cycle (dev-code-review document path), at most 7 rounds, until Approve.
    - Rebase on `origin/main` and push to `main` without a PR, never with `--force`.
    - The commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0339`.
    - In Result: the landed commit(s), the number of review rounds, any review point left as a follow-up, and the text of the owner notice for #5. The driver posts the notice (DRIVER §9, §8 footer).

## Out of Scope

- The code slice itself: any change to `hilclaw/turn_start.py`, `hilclaw/turn_loop.py` (its prompt rule included), `hilclaw/turn_definition.py`, tests, or `orchestration/round-manager.md`.
- How the Round-Manager reaches `replace` or other layer-2 writes (OD-23, OD-18); the round-0 text of the Round-Manager prompt; OD-18 ⑯ (가); OD-8 ⑪; the lock of two loops (OD-17); permissions, trust and hooks (P2-4).
- The start of ADR-0115 and open PR #186 (T-0324): do not touch `hilclaw/start_instance.py`.
- Any edit to ADR-0115, ADR-0118, ADR-0120, ADR-0122 or another accepted record, or to the sentences they list as less exact. Anything in PLAN's 보류 section. Anything blocked by HQ-0013..HQ-0036.

## Follow-ups

- The code slice (code mode): hand the run over as ADR-0123 decides, in `hilclaw/turn_start.py` (and `hilclaw/turn_loop.py` if the record requires it). Correct the "**Open**: how a turn session learns which run it carries" sentence of the `turn_start` docstring. Tests use a stub `claude` only (D16).
- The remaining P2-1 slices: how the Round-Manager reaches `replace` (OD-23, OD-18), OD-18 ⑯ (가), OD-8 ⑪, then the round-0 part of the Round-Manager prompt.

## Result
