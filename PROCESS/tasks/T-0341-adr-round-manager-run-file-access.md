---
id: T-0341
title: Write ADR-0124 — how the Round-Manager of a first-case turn reads its run's STATE.json and instance.json and reaches hilclaw.run_state_file.replace, and whether it then needs the place of the run (part of OD-23 and OD-18, for the runs of ADR-0120 decision 1)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-10, FR-13, NFR-1, NFR-6, OD-23, OD-18, OD-8, S0, S1]
dependsOn: [T-0333, T-0339, T-0340]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and the round-0 procedure) is the first unchecked item of the P2 order (D18). This task is one of its slices, so the D18 priority rule for non-checklist work does not apply. The P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) needs it: the round-0 part of the Round-Manager prompt cannot be written while it is open.

The Round-Manager of the round-0 turn must read `STATE.json` (its entry point, #4 §1 and §3c), tell a fresh run directory (ADR-0120 decision 4), check that `instance.json` is under its final name (ADR-0120 decision 3), and write the first `STATE.json` through `hilclaw.run_state_file.replace` (ADR-0120 decision 2). ADR-0012 decision 6 has it write the end of each round the same way. Four records leave the means open:

- ADR-0120 decision 2: "How the Round-Manager reaches `replace` — a tool of the registry, a command-line entry of the package, or another way — is not decided here (OD-23; OD-18)", with one constraint: the first write is not the step of a journaled call.
- ADR-0118 decision 4: "How the session reaches the run's files — for example `--add-dir` of the data checkout — is the definition's and the code task's", and the source checkout is never added with `--add-dir`.
- ADR-0123 decision 2: the session is handed the run id and no place. Whether it needs the place "depends only on how it will read the run's files and reach `replace`". A record that chooses a means needing the place says how the place reaches the session.
- `hilclaw/run_state_file.py`: "who calls it is open (OD-23, the rest of OD-17, sub-questions 10, 12 and 15 of OD-8)".

This is a design-level choice, not an owner-only one. It concerns the means one agent of the runtime uses to reach its own run's files (OD-23 input and output contract; OD-18 tool exposure), and needs none of #5 A or B, C-6, OD-25 or OD-3. So under DRIVER §9 the task writes the ADR. No open HQ covers it: HQ-0013 to HQ-0037 were checked. HQ-0032 (PR #186) is about how the start function learns of a given id, which is a different point.

The record decides the means. It does not write code: the code slice (and the round-0 part of the definition) is a later task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap) and §9 (OD closing authority, owner notice).
- `CLAUDE.md`, "상시 규칙": "미결은 발명하지 않는다", "세션 진입 점검", the three-layer model, "개발 드라이버와 런타임의 구분" (D16), and the document-mode branch/merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, the "Record format" section (the format of the new ADR).
- `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md`, whole file. It is the closest model for the shape of the new record (Status with the owner-sentence search, cited versus own sentences, Walk-through, Alternatives table, Consequences, Boundaries). Do not copy its wording.
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`, decisions 1 to 4 and Boundaries.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`, decisions 2 to 6 (especially decision 4, "How the session reaches the run's files" and "Workspace trust", and decision 6).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`, decisions 1, 3, 5, 6 and 8 (agents call tools through the MCP front; what a hook and an allowlist can see; no access control).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`, decisions 2 to 4 and 7 (tool definition, data root never in a request, `run_id` in the request).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`, decisions 2, 3, 6 and 7. `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`, decisions 2 to 7 (the replacement, not journaled).
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decision 3 and `ARCHITECTURE/decisions/ADR-0030-od8-layout-stamp-read-order.md` decisions 3 and 7 (why the first write cannot be a journaled step).
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md` decisions on `run_status` and its writer (the Round-Manager writes it too, through the same means).
- `ARCHITECTURE/decisions/ADR-0039-od18-blob-push-fetch-local.md`, decision headings and the request/result form only (a model of how a registry tool's contract is written).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8), § OD-23 (whole), § OD-18 (the "제안으로 남는 부분" bullet and the ADR-0118 and ADR-0123 lines), § OD-8 candidate ① items 4 and 5 (no Bash for in-process agents; per-agent allowlist).
- `ARCHITECTURE/Requirements.md`: the register's "행 형식" paragraph (line 84) and the rows OD-8, OD-17, OD-18 and OD-23.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과 (the recording rule), the "최근 재검사" line, and the S0 and S1 rows of the judgement table.
- Code, as observation only: `hilclaw/run_state_file.py` (module docstring), `hilclaw/run_journal.py` (`read_state`, `current`), `hilclaw/fresh_run.py` (`is_fresh`), `hilclaw/further_turn.py` (`classify`), `hilclaw/tools.py` (`default_registry` and the reserved kinds), `hilclaw/turn_loop.py` (module docstring: what a session gets), `orchestration/round-manager.md` (whole).
- Issue #4 body §1, §2, §3c and the comment https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ("확정된 전제 2가지": no read restriction; a write zone given by prompt alone is too weak). Issue #5 A-12 point 3 (fixed tool set, no runtime tool generation).

## Acceptance Criteria

### Before editing

1. Run the session entry check of CLAUDE.md: `gh pr list`, and issues #4, #5, #7, #8. PR #186 (T-0324) touches only `hilclaw/start_instance.py` and three test files. If any open PR edits the four files of `touchesFiles`, stop and return BLOCKED (open-PR conflict risk).
2. Search for owner sentences on the point, as ADR-0123 Status did: #4 body and comments, #5 comments without the "posted by driver" marker, #7, #8. Use terms such as STATE.json, 진입점, add-dir, 파일 도구, file tool, Read, Write, Bash, tool, 도구, replace, 쓰기 구역, write zone and allowlist. Record in Status what was searched and every sentence found that touches the point, each read for what it says and no further. **If an owner sentence decides the means, cite it and do not decide against it. If the point turns out to need an owner-only decision (#5 A or B, C-6, OD-25, OD-3), stop and return BLOCKED with the question (DRIVER §9).**

### The record `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`

3. Format of ADR-0001 "Record format". Status states: accepted under DRIVER §9 (D6), not confirmed by the owner; which OD points it answers (part of OD-23 and of OD-18, for the runs of ADR-0120 decision 1); that the OD statuses are unchanged; what it builds on, with "if one of them is reverted, this record is revisited with it"; that it is a record, not code, and that no `claude` was started (D16).
4. **Scope**: the Round-Manager (the main conversation) of a turn session of a run of ADR-0120 decision 1, driven through `hilclaw.turn_start`. The reads are its run's `STATE.json` and `instance.json`, including telling a fresh run directory. The writes are its run's `STATE.json` through `replace`, the first one (ADR-0120 decision 2) and the round-end ones (ADR-0012 decision 6; `run_status`, ADR-0121). Sub-agents, other files of the run (`events.ndjson`, `artifacts.json`, `rounds/`, hypotheses, verdicts, cases) and other runs are outside. Say so.
5. **Decide the means** by weighing at least these alternatives in an Alternatives table, with the columns you find relevant. Include at least: what a hook can see (ADR-0010 decision 6); what a per-agent allowlist can express; whether the place of the run must reach the session; the S4 premise 2 write zone; NFR-6 (method A); NFR-1 (nothing only in the session directory); and the write being no journaled step.
   - (a) typed tools of the registry over the MCP front, taking `run_id` in the request;
   - (b) a command-line entry of the package run through the Bash tool;
   - (c) the session's own file tools (Read/Write) on the data checkout added with `--add-dir`;
   - (d) a mix, for example reads by file tools and the write by a tool.
   The chosen means must keep these cited constraints: agents call tools through the MCP front (ADR-0010 decision 3); the data root is never a member of a request (ADR-0015 decision 3); the first write is not the step of a journaled call (ADR-0120 decision 2); no read is restricted (S4 premise 1); the source checkout is never added with `--add-dir` (ADR-0118 decision 4); the definition stays one for every run (ADR-0118 decision 5). It must not present itself as the run's protection against writes into another run (S4 premise 2; ADR-0123 decision 4).
6. **Answer ADR-0123's open half**: whether the Round-Manager then needs the place of the run. If the chosen means needs it, say how the place reaches the session, and keep ADR-0123 decision 3 (the prompt names the run). If not, say so in one sentence.
7. **If the chosen means adds tools to the registry**, give each one:
   - its name, under the name rule of `hilclaw/tools.py` and the MCP naming of ADR-0010;
   - its request members (`run_id` and what else) and result members;
   - the failure kinds it uses, reusing the reserved kinds of `hilclaw/tools.py` where they fit;
   - which existing function it is a tool over (for example `run_journal.read_state`, `fresh_run.is_fresh`, `run_state_file.replace`);
   - whether it is journaled (the first write cannot be).
   Keep it to what the round-0 turn and the round-end write need. State that the fixed tool set of #5 A-12 point 3 grows by these tools in the source. State whether they count as FR-10 tools or as tools of the registry beside them (ADR-0010 decision 1 speaks of FR-10 tools). Leave the rest to the code slice, and name it.
   **If the chosen means adds no tool**, say what the Round-Manager runs or reads, and how a later hook would see it.
8. **Add no member, file, kind of the data plane, value or version, and change no validator.** A new *tool failure kind* is a tool-layer name, not a data-plane change; if you add one, say so. If the decision turns out to need a data-plane schema change, stop and return BLOCKED (CLAUDE.md A-13).
9. **Walk-through**: at least these cases.
   - The round-0 turn on a fresh run directory (read, tell fresh, check `instance.json`, write the first `STATE.json`).
   - A later turn reading a `STATE.json` that names round k.
   - A turn that finds neither file (ADR-0120 decision 3: it writes no `STATE.json`).
   - A turn whose `STATE.json` is invalid or of another `schema_version` (ADR-0012 decision 6).
   - A Round-Manager that names another run's id (nothing stops it, ADR-0123 decision 4).
10. **Consequences**:
    - the code slice it enables (code mode, later task, stub `claude` only — D16): name the modules and the definition's section it touches;
    - what the round-0 part of the Round-Manager prompt still waits on (at least OD-18 ⑯ (가), the self-check at a resume; OD-8 ⑪, the commit step; who folds the spend view for the round-end write, ADR-0012, OD-23);
    - a "Less exact, not edited" list from a search of `ARCHITECTURE/decisions/` and `hilclaw/` for the open-means sentences (at least ADR-0118 decision 4, ADR-0120 decision 2, ADR-0123 decision 2 and Boundaries, and the `run_state_file.py` docstring), marked as not claimed complete;
    - UsageCases and StandardScenarios sentences that become false (or "none");
    - the A-13 reading (document mode, no data-plane change);
    - new runtime acceptance items numbered after ADR-0123's (ix), if any — for example whether a `-p` turn session reaches the chosen tools or directories without a permission prompt. They are only listed here; nothing is required of the development machine.
11. **Boundaries**: at least the roster and sub-agents' access and run id (rest of OD-23); permissions, allowlists and hooks (rest of OD-18, PLAN P2-4); the isolation means (rest of OD-8, OD-14); the lock (rest of OD-17); the commit step (OD-8 ⑪); the self-check at a resume (OD-18 ⑯ (가)); resumed, continued or branched runs (OD-8 ①); gates (OD-3, owner-only); any edit to `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, settings or the `HIL-Claw-data` repository.
12. Keep it a decision record, not an essay. Each sentence is either cited with its source or the record's own; mark readings as readings. Aim at about 150 to 200 lines.

### The registers (follow the recording rules written in those files; do not copy earlier task wording)

13. `ARCHITECTURE/Requirements.md`: in the rows OD-23 and OD-18 (and OD-8 only if the record answers part of it), apply the register's "행 형식": add one link to ADR-0124 with a few words after `**확정분**:`, and rewrite `**잔여**:` in place. Do not restate the record and add no dated paragraph. Status cells keep their status word.
14. `ARCHITECTURE/OpenDecisionProposals.md`: apply the header's "기록 규칙". Add one `- **채택분** [ADR-0124](…) — …` line under § OD-23 and under § OD-18. Rewrite in place the open part that this record narrows: § OD-23's "제안으로 남는 부분" mentions "Round-Manager가 run의 파일과 `replace`에 닿는 방법(run의 자리가 필요한지 포함)". Do not restate the record and add no dated note.
15. `ARCHITECTURE/StandardScenarios.md`: recheck coverage under the rules of the file (CLAUDE.md "문서 커버리지 재검사"). Update the "최근 재검사" line in place, following the first paragraph of § 검사 결과. Add an item to "판정 변화 이력" only if a judgement changed or a gap was found or closed. Change a judgement-table note only if an open OD it names is narrowed.

### Mode, review and notice

16. Document mode (A-13): branch `claude/T-0341-adr-round-manager-run-file-access`. Commit with trailer `Task: T-0341`. Run the context-isolated reviewer cycle (dev-code-review, at most 7 rounds). Then rebase on `origin/main` and push to main without a PR, with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer. Never `git push --force*`.
17. In `## Result`, write the owner notice text for #5 that the driver posts (DRIVER §9, §8 footer `— posted by driver`). If the record lists new runtime acceptance items, also write the one-paragraph HQ text (reason `runtime-acceptance`) for the driver to record (DRIVER §8). Do not post on GitHub yourself.

## Out of Scope

- Any code: `hilclaw/`, `orchestration/round-manager.md`, tests, CI, `pyproject.toml`, `.claude/`, settings. The code slice and the round-0 steps of the definition are later tasks.
- The roster, the sub-agents and how they get the run id or reach the run's files; per-agent allowlists (rest of OD-23).
- Permissions of a turn session, hooks, the check of a request's `run_id` against the session's run, any access control (rest of OD-18, PLAN P2-4); the isolation means (rest of OD-8, OD-14).
- Who folds the spend view for the round-end write and how the result reaches the writer (ADR-0012 decision 6, OD-23), except as a named boundary.
- The commit step (OD-8 ⑪), the self-check at a resume (OD-18 ⑯ (가)), the lock (rest of OD-17), resumed/continued/branched runs (OD-8 ①), who calls the ADR-0115 start (HQ-0032's area, PR #186).
- The files of the run other than `STATE.json` and `instance.json`.
- Editing earlier ADRs; the less-exact sentences are listed in Consequences, not edited. Any wording follow-ups of T-0323 to T-0339 (held in the PLAN 보류 section).
- Any data-plane schema or validator change; any new external dependency.
- Starting a real `claude`, or requiring a logged-in `claude`, a board or an API key (D16).

## Follow-ups

- The code slice of ADR-0124 (stub `claude` only); then OD-18 ⑯ (가) and OD-8 ⑪; then the round-0 part of the Round-Manager prompt (PLAN P2-1).

## Result
