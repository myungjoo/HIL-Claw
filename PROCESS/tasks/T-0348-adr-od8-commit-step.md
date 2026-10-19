---
id: T-0348
title: Write ADR-0127 — which step of a first-case run commits the data repository, when, what it takes in, and how a fresh turn learns that a commit is owed (OD-8 sub-question ⑪, PLAN P2-1; for the runs of ADR-0120 decision 1)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-4, FR-13, NFR-1, NFR-2, OD-8, OD-17, OD-23, S0, S1, S2]
dependsOn: [T-0042, T-0333, T-0335, T-0337, T-0341, T-0346]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and round 0) is the first unchecked item of the P2 order (D18). This task is a slice of it, so the D18 rule for non-checklist work does not apply. The P2-5 run needs it: a run of five rounds that never commits leaves no history in the data repository. The local commit is the durability boundary (#5 A-3), and Phase 1 uses the Git tree as the database.

The decision is missing. ADR-0118, ADR-0120, ADR-0121, ADR-0122, ADR-0123, ADR-0124 and ADR-0126 each list "the commit step (OD-8 ⑪)" as something the round-0 part of `orchestration/round-manager.md` still waits on. ADR-0012 (Consequences and Boundaries) states the open problem. A process that dies after the round-end write of `STATE.json` and before the commit leaves a working tree that already names the next round, and nothing records that a commit is owed. ADR-0006 decision 6 and ADR-0013 ("Git") each bind "whatever step commits" by a rule: remove a torn log tail first, and never commit a temporary file. No record says which step that is.

This is a design-level point of OD-8 and is not owner-only (DRIVER §9). The task therefore writes the ADR. Three owner facts bound it:

- **#5 A-3** (owner, answered): a local commit to `HIL-Claw-data` at the end of every turn (= Round) is an invariant. The system never pushes. It may show the unpushed-commit count as visibility only. The record must not change any of this.
- **The reading of "매 턴(=Round)"** when a turn ends before its round ends. ADR-0118 Boundaries deliberately read A-3 neither as "every turn end" nor as "every round end". The record may settle the commit of a turn whose round ends. It may settle a cut-short turn only if the answer follows from records and owner text without choosing a meaning for A-3. If the answer turns on what the owner meant, the record leaves that case open, and the executor returns it as an HQ (owner-only, #5 A-3) under Follow-ups. It is not decided.
- **Gates** (OD-3, #5 A-5) and the coder model or tokens (#5 A-8) are owner-only. The record touches neither.

No open HQ covers this point. HQ-0013 to HQ-0042 were checked: HQ-0032 is the given `run_id` of the start function, HQ-0040 and HQ-0041 are about the coder call, and the rest are runtime-acceptance notices or other tasks.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap) and §9 (OD closing authority, owner notice).
- `CLAUDE.md`, "상시 규칙": "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), and the document-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format".
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`: decisions 3 and 6, Consequences (the bullets "The end of a round written and its commit not made" and "Machine loss before the commit"), and Boundaries (sub-question ⑪).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md`: decisions 5, 6 and 10, and the Consequences and Boundaries bullets on the step that commits.
- `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`: the "Git" bullet and the "Not promised" bullet.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: decisions 1, 2, 4 and 7, and the Boundaries bullet on the commit and push cadence.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: Context (the #4 recommendation "1 round = 1 OS process = 1 turn = 1 commit", #5 A-3), decision (i) "With its round", and Boundaries ("The commit step").
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: Context (W1: "phase 마커 갱신·commit은 매니저 전담"), decisions 1 and 4, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: the decisions on `run_status` "over", and Boundaries (the commit owed by a run that is over).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: the decision headings, and the parts on what the loop reads before it starts a turn.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`, whole file. It is the closest model for the record's shape and for how a step reaches package functions. Do not copy its wording.
- `hilclaw/turn_loop.py`, `hilclaw/turn_start.py` and `hilclaw/further_turn.py`, module docstrings and public function signatures only (what a fresh turn and the loop read today).
- `orchestration/round-manager.md`, whole file (what the Round-Manager does at a turn's entry today).
- `ARCHITECTURE/Requirements.md`:
  - the register's "행 형식" paragraph (around line 84);
  - the rows FR-1, FR-4, FR-13, NFR-1, OD-8, OD-17 and OD-18.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - § OD-8, the "쓰기와 작성자" part of "제안으로 남는 부분" (around line 127) and the sub-question bullet holding ⑩ to ⑬ (around line 131);
  - § OD-17, the sub-question bullet (around line 267; lock and the comparison with the committed file).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과, the "최근 재검사" line, and the S0, S1 and S2 rows of the judgement table (S2 step 3: "cron 재기동이 마지막 commit 지점에서 이어간다").
- GitHub #5 comment https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 (A-3), whole.

## Acceptance Criteria

1. **New file** `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`, in the record format of ADR-0001. Status is "Accepted" under DRIVER §9, part of OD-8 (sub-question ⑪), with scope limited to the runs of ADR-0120 decision 1. It cites, rather than restates, ADR-0006, ADR-0012, ADR-0013, ADR-0118, ADR-0120, ADR-0121 and #5 A-3. It decides at least the following for that scope:
   - (a) **which actor or step makes the commit**: the Round-Manager itself, a layer-2 function it calls, the turn loop, or another named step. Give the reason, and say how the choice agrees with W1 ("commit은 매니저 전담") or why it reads W1 otherwise;
   - (b) **when** in a turn the commit is made, relative to the round-end write of `STATE.json` (ADR-0012 decision 6) and to the first `STATE.json` of ADR-0120. Also say whether the run that ADR-0121 marks as over gets a commit, and when;
   - (c) **what the commit takes in and what it must not take in**: the paths under `runs/<run_id>/`, whether anything outside the run directory is included, the torn-tail rule of ADR-0006 decision 6, the temporary-file rule of ADR-0013, and no blob bytes (#5 A-2). Do not fix a commit message format beyond what the decision needs. If the record fixes one, say what reads it;
   - (d) **how a fresh turn learns that a commit is owed** after a death between the round-end write and the commit, and what it does then. For example, it compares the working tree with `HEAD` for the run's paths. Say which actor checks, at which moment of the turn's entry (`orchestration/round-manager.md`, `hilclaw/turn_start.py` or the loop), and what happens when the check itself fails (no repository, a failed commit). Use only failure handling that existing records permit. Where they do not, leave it open;
   - (e) **what is not promised**: machine loss before the commit (#5 A-3), no push, and anything a single repository cannot show.
2. **A-3 is not reinterpreted.** The record says in one bullet how it reads "매 턴(=Round) 종료 시". If the commit of a turn that ends before its round ends can only be decided by choosing a meaning of A-3, the record leaves it open in Boundaries, and the task's Follow-ups carry a proposed HQ (reason: owner-only, #5 A-3) with the question in English. Gates (OD-3), the lock and two writers (rest of OD-17), the Stop hook that enforces a commit (PLAN P2-4, OD-18 and OD-19), the push and the unpushed-count visibility of A-3, and runs outside ADR-0120 decision 1 are named in Boundaries and not decided.
3. **Consequences** name the code and prompt slices the record enables (for example, a layer-2 commit function, a step in `orchestration/round-manager.md`, a check at the turn's entry). Each slice is something a later code-mode task can do with a stub `claude` only (D16). The record states which earlier sentences become less exact, if any, and does not edit them.
4. **No data-plane schema change**: the record adds no member to `STATE.json`, `instance.json`, `events.ndjson` or `artifacts.json` and no event kind. If the executor finds that the decision needs one, it stops and returns BLOCKED (CLAUDE.md BLOCKED reason "데이터 plane 스키마 변경") instead of adding it.
5. **`ARCHITECTURE/Requirements.md`**: the OD-8 row is updated by the register's "행 형식" rule. Add one ADR link with a few-word topic after `**확정분**:`, rewrite `**잔여**:` in place to drop or narrow the "어느 단계가 commit하는지" part, and do not restate the record. Touch the OD-17, OD-18 or OD-19 row only if the record answers part of that OD, and then by the same rule.
6. **`ARCHITECTURE/OpenDecisionProposals.md`**: follow the header's "기록 규칙". Add one `- **채택분** [ADR-0127](…)` line in § OD-8. Rewrite in place the status at the end of sub-question ⑪ and the state word at the head of its bullet, and the "어느 단계가 commit하는지(⑪과 함께)" phrase in "쓰기와 작성자". Keep the question's wording, and add no dated paragraph.
7. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage by the document's rules (CLAUDE.md "문서 커버리지 재검사"), at least for S0, S1 and S2. Update the "최근 재검사" line in place under the first paragraph of § 검사 결과. Add an entry to "판정 변화 이력" only if a judgement or gap changes. Narrow a judgement-table note only where it names ⑪ or "which step commits" as open.
8. Document mode (A-13): a context-isolated reviewer cycle ends in Approve, then the branch is rebased onto `origin/main` and pushed directly to main with the `Reviewed-by:` and `Task: T-0348` trailers. After landing, the owner gets the DRIVER §9 notice on #5. If the record leaves a fact that only a live runtime can establish (for example, a commit made from inside a `-p` session under its permission mode), the executor lists it under Follow-ups as a runtime-acceptance item for DRIVER §8.
9. No `claude` process is started, and no runtime-only resource is required (D16).

## Out of Scope

- Any code: the commit function, the prompt step in `orchestration/round-manager.md`, and the check at a turn's entry. These are later code-mode slices.
- Push, remote handling, and the unpushed-commit visibility of #5 A-3.
- The Stop hook and other hooks (PLAN P2-4), the lock (OD-17), gates (OD-3), and resume or branch from a chosen point (OD-8 ①, UC-4).
- Sub-questions ⑫ and ⑬ of OD-8, and the rest of ⑩.
- Wording fixes in earlier ADRs (D18 hold).

## Follow-ups

- **Proposed HQ (reason: owner-only, #5 A-3)** — the case ADR-0127 decision 8 leaves open. Proposed mirror text for #5:

  > ### HQ-NNNN — T-0348: does #5 A-3's local commit at "매 턴(=Round) 종료 시" apply to a turn that ends before its round ends?
  >
  > Reason: owner-only (#5 A-3).
  >
  > ADR-0127 (part of OD-8 sub-question 11, first-case runs) has the Round-Manager commit the data repository right after the write that ends a round, and has every turn's entry first make a round-end commit that a death left owed. A turn can also end before its round ends (ADR-0118 decision 2 (ii)): the process dies or is stopped, or the session ends while the run waits for you, at a gate, on an error or on a usage limit. ADR-0121's own write of `run_status` "over" also ends no round. When a turn and a round do not end together, which do you mean by "매 턴(=Round) 종료 시"? (a) Every turn end: such a turn's end commits what the run directory then holds, and after a death the next turn's entry commits what the dead turn left, so a round that takes several turns gets several commits. (b) Round ends only: the work of a cut-short turn stays uncommitted until its round ends and is committed with it; a machine loss in between loses it. (c) Something else. Until you answer, ADR-0127 commits nothing in that case and forbids nothing.
  >
  > Answer with a comment that contains `HQ-NNNN`.
  >
  > — posted by driver

  Only a later slice that commits a cut-short turn would need it in its `hq`; the code slices listed below do not.
- **Runtime acceptance items (DRIVER §8, reason `runtime-acceptance`, non-blocking)** — ADR-0127 adds (xv) to (xvii) to the turn-session series. Proposed mirror text for #5:

  > ### HQ-NNNN — T-0348: runtime-acceptance items (xv)-(xvii) of ADR-0127 (non-blocking)
  >
  > Reason: `runtime-acceptance`.
  >
  > ADR-0127 (part of OD-8 sub-question 11; T-0348) adds runtime acceptance items (xv)-(xvii) to the turn-session series. Under D16 they are closed by your check by hand or by the runtime's own self-check, not by a driver task. (xv) The main session of a `-p` turn session sees `mcp__hilclaw__run_commit` and may call it under the permission means of item (vii). (xvi) On a runtime machine, the MCP server process a turn session starts finds `git` and an author identity with which `git` makes a commit in the data checkout. (xvii) A live Round-Manager calls `run.commit` as the first step of its entry and right after the write that ends its round. Best checked after the code slices land. Nothing was tried.
  >
  > Answer with a comment that contains `HQ-NNNN`.
  >
  > — posted by driver
- **Code slices** (code mode; each plannable now, tested with a temporary git repository and a stub `claude` only): (1) the commit function, its read-only owed rule and the registry tool `run.commit` with a test file; (2) step 0 of "The entry of a turn" in `orchestration/round-manager.md` and `mcp__hilclaw__run_commit` in its "Your run" tool list; (3) step 1 for owed P2 in `hilclaw/further_turn.py` and `hilclaw/turn_start.py`. The call after the round-end write goes with the slice that writes "The round steps". Slice (1) runs the `git` program and follows the reading of ADR-0127 decision 4: no package is added (the data repository is a git repository by #5 A-1 and D7).

## Result

- DONE. ADR-0127 (`ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`) landed on main in document mode as one squashed commit with this Result (`Reviewed-by: reviewer agent (7 rounds, Approve)`); the task branch was deleted. Registers: OD-8 row of Requirements (one `확정분` link, `잔여` narrowed in place, status dates to 10-20), § OD-8 of OpenDecisionProposals (one `채택분` line, the status of ⑪ and the "쓰기와 작성자" phrase rewritten in place), StandardScenarios "최근 재검사" line (S0, S1, S2: no verdict change, no gap, no note changed). OD-17, OD-18 and OD-19 rows untouched.
- Decided (runs of ADR-0120 decision 1 only): the Round-Manager makes every round-end commit through one new registry tool `run.commit` (MCP `mcp__hilclaw__run_commit`; request `run_id`; result `committed`; kinds `invalid_request`, `no_data_root`, `no_repository`, `commit_refused`, `commit_not_made`), right after the write that ends the round and as the first step of every turn's entry. A round end is owed when the working tree's `STATE.json` `round` is beyond that of `HEAD`. The commit removes a torn tail of `events.ndjson` first, takes only the run directory's new or changed files and the case files of the committed rounds, never a `.tmp` name, an ignored path or anything under `blobs/`; no commit message format. Step 1 of the loop splits P2: owed P2 is handled like P4 (self-check before the first turn of a start, stop after a failed or unchanged turn); "run over" only when nothing is owed. Declared revisions, not edits: ADR-0121 decisions 3 and 5, ADR-0122 decisions 2 to 5, ADR-0125 decision 2. No data-plane change; W1 holds under both readings.
- Left open: the commit of a turn that ends before its round ends, and ADR-0121's own `"over"` write (#5 A-3 reading, owner-only); `best.json`, `technique_stats.json` and key record files in a round commit; the order of the promotion write (OD-23); push, Stop hook, lock, gates.
- Review: 7 rounds (rounds 1, 2, 4 Request changes; 3, 5, 6, 7 Approve with Low/Nit, all addressed except two round-7 Nits: the OD-18 sub-question line of OpenDecisionProposals was left as is (still true; AC 5/6 give no reason to touch OD-18), and the HQ title below names the turn-session series).
- **For the driver**:
  - DRIVER §9 owner notice on #5 (proposed text):

    > **OD closure notice (DRIVER §9): ADR-0127 — part of OD-8 sub-question 11 (the commit step), for the runs of ADR-0120 decision 1**
    >
    > ADR-0127 (`ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`, landed on `main` as <sha>) decides, for first-case runs: the Round-Manager makes every round-end commit of the data repository through one new typed registry tool, `run.commit`, over the MCP front — right after the write that ends its round, and as the first step of every turn's entry. A round end is owed when the `round` of the working tree's `STATE.json` is beyond that of `HEAD`; the tool then removes a torn tail of `events.ndjson`, commits only the run directory's new or changed files and the case files of the committed rounds, never a `.tmp` file or anything under `blobs/`, and otherwise makes no commit. The system never pushes. Step 1 of the turn loop now gives one turn to a run that is over while its last commit is owed. No data-plane change; W1 ("commit은 매니저 전담") holds under both readings.
    >
    > Left to you: whether #5 A-3's commit at "매 턴(=Round) 종료 시" also applies to a turn that ends before its round ends (asked as an HQ). Runtime acceptance items (xv)-(xvii) of the turn-session series are added. OD-8 keeps its status; its open part was narrowed in place.
    >
    > Accepted by a context-isolated reviewer (7 rounds); not confirmed by the owner. An objection within 7 days creates a task that reverts it.
    >
    > — posted by driver
  - Two HQs, texts under Follow-ups: the owner-only A-3 question (non-blocking for the code slices listed there), and the runtime-acceptance items, titled `### HQ-NNNN — T-0348: runtime-acceptance turn-session items (xv)-(xvii) of ADR-0127 (non-blocking)` so that they are not mistaken for the self-check series' (xv)/(xvi).
  - Follow-up code slices (Follow-ups): `run.commit` with its read-only owed rule; step 0 and the tool list in `orchestration/round-manager.md`; owed P2 in `hilclaw/further_turn.py` / `hilclaw/turn_start.py`.
