---
id: T-0391
title: Write ADR-0143, the commit at the end of a first-case turn that ends no round, carrying out the owner's answer to HQ-0043 (a) (part of OD-8 sub-question ⑪; PLAN P2-1/P2-5)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-13, NFR-1, OD-8, OD-23, "#5 A-3", S0, S1, S2]
dependsOn: [T-0348, T-0390]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

ADR-0127 (T-0348, main e9f16a0) defines the commit step of a first-case run (the runs of ADR-0120 decision 1). The Round-Manager calls the registry tool `run.commit` right after the write that ends its round, and as the first step of every turn's entry. `run.commit` commits only when a round end is owed (the working tree's `round` is beyond that of `HEAD`). ADR-0127 decision 8 left one case open: a turn that ends before its round ends (ADR-0118 decision 2 (ii)), and ADR-0121's own write of `"over"`, which ends no round. That case is owner-only (#5 A-3). It was asked as HQ-0043.

The owner answered on 2026-10-21 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6306369119; recorded in `PROCESS/STATE.json` HQ-0043 `decision`):

1. **(a) Every turn end.** Such a turn's end commits what the run directory then holds. After a death, the next turn's entry commits what the dead turn left. So a round that takes several turns gets several commits.
2. **One exception.** The case file of the round in progress is not taken into a commit that ends no round. It stays in the working tree and is committed with the end of its round, so a round's promotion stays in the same commit as the round it promotes (#5 A-1).

The owner's note says why: a measurement or a failed attempt in a turn that ends early is data (FR-18), and a turn boundary is where a replaced component takes effect (ADR-0118 decision 2).

The answer is given, but no record carries it out yet. ADR-0142 decision 1 ("The stop") and Consequences, and the T-0390 Follow-ups, name that record as a separate task: it widens ADR-0127 decision 8 and `run.commit`. Today every first-case turn ends at a stop that ends no round (`orchestration/round-manager.md`, "The stop": "no `round.end` and no `run.commit`"). This holds until `board.run` is registered (ADR-0142 slice 2; T-0210/HQ-0021, unanswered). So none of a run's turns commits anything.

**D18 judgment.** This is not a PLAN checklist item. It is follow-up work for P2-1 (Round-Manager round 0) and P2-5 (the first run). It is needed for P2-5. The first run's turns that stop or die mid-round would otherwise leave their data uncommitted. That breaks the durability invariant of #5 A-3 as the owner has now read it, and NFR-1 (resume after process death) rests on that invariant. It is not wording cleanup, input hardening or a refactor. It carries out an owner decision that changes behaviour.

This task writes the design record only (DRIVER §9 path; OD-8 is design-level). The code slices it names are later tasks.

Open HQs checked:

- HQ-0043: answered (a). This task carries it out and does not reinterpret it.
- HQ-0021 (T-0210, `sim.run`/`board.run` registration; ADR-0068 unlanded): not crossed. Nothing of ADR-0068 is cited as accepted.
- HQ-0031, HQ-0032, HQ-0048 and HQ-0053 (unlanded ADR-0112, ADR-0132, ADR-0137 on branches): not crossed. Nothing of those drafts is cited as accepted. The next free record number on main is ADR-0143.
- HQ-0026 and OD-14 ①: no backend is presumed.
- The runtime-acceptance HQs (HQ-0013 … HQ-0057): none is closed. ADR-0127 items (xv)-(xvii) are used, not changed.

Open PR #186 (T-0324) touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. It touches nothing under `ARCHITECTURE/`, so there is no overlap.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, the 2 h 30 min limit), §5 (task file format, naming convention, D4 size cap), §8 (HQ) and §9 (OD closure by ADR, the #5 notice).
- `CLAUDE.md` (repository), "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", the doc-mode branch and merge procedure (A-13), and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- The owner's answer: `PROCESS/STATE.json`, the `humanQuestions` entry `HQ-0043` (`question` and `decision`), and `gh api repos/myungjoo/HIL-Claw/issues/comments/6306369119`.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`, the whole file (167 lines). Above all: Status (lines 3-19), decisions 1 to 6 (lines 32-83), decision 8 (lines 92-95), Walk-through (lines 97-112), Alternatives (e) (line 122), Consequences (lines 127-147) and Boundaries (lines 149-159).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, "Record format" (lines 146-153).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`, decision 2 (lines 57-66).
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`, decision 3 (lines 47-53) and decision 5 (lines 73-86).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`, decisions 2 to 5 (lines 45-89).
- `ARCHITECTURE/decisions/ADR-0125-od18-self-check-in-round-zero.md`, decision 2 (lines 34-41).
- `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md`, decision 5 (lines 63-67).
- `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md`, decision 7 (lines 71-77).
- `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md`, decision 5 (lines 66-72).
- `ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md`, decision 1 "The stop" (line 39) and Boundaries (line 157).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md`, decision 6 (lines 66-73). `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md`, decision 3 (lines 49-59). `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`, decisions 6 and 7 (lines 82-100).
- `ARCHITECTURE/Requirements.md`: the register's "행 형식" paragraph (line 84) and the OD-8 row (line 99).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8); § OD-8 (from line 88), its 채택분 lines (around lines 120-130) and sub-question ⑪ (line 135); § OD-18, the bullet on NFR-7 ① and "1 turn = 1 commit" (line 283).
- `ARCHITECTURE/StandardScenarios.md`: the check rules (around line 26), S0, S1 and S2, and the first paragraph of § 검사 결과 (lines 168-172).
- Code, as observation only, not to be edited: `orchestration/round-manager.md` (167 lines; "The entry of a turn", "The round steps", "The stop" and "The closing steps of a round"); the module docstring of `hilclaw/run_commit.py` (lines 1-29) and `owed_rounds`/`commit` (lines 146-281); the module docstring of `hilclaw/further_turn.py` (lines 1-50).

## Acceptance Criteria

### The record (`ARCHITECTURE/decisions/ADR-0143-od8-first-case-turn-end-commit.md`)

1. **Format.** Follow ADR-0001 "Record format". Write it in English, with the sections in that order. Status says it is accepted under DRIVER §9 by reviewer approval and is not owner-confirmed. It separates cited content from the record's own, as ADR-0127 Status does. The scope is the runs of ADR-0120 decision 1 only.
2. **Status must make these points:**
   - The governing sentence is the owner's answer to HQ-0043 (a), with its link. It is cited, not re-derived, and not reinterpreted. Both points 1 and 2 are cited in substance.
   - The record answers the rest of OD-8 sub-question ⑪ for this scope: the commit of a turn that ends no round.
   - The record **revises, without editing,** ADR-0127 decision 8 and the parts of ADR-0127 decisions 1 to 6 that this changes. Name each revised decision, the way ADR-0127 Status names what it revises.
   - OD-8 keeps its status. No sub-question is registered.
   - No member, file, kind, value or version of the data plane is added or changed. If the executor finds that one would be, it stops and reports BLOCKED (A-13: data-plane schema change).
3. **The decisions must answer, each with the reason in one or two sentences:**
   - (a) **Which turn ends commit, and who makes the commit.** For a turn whose session ends while it is alive (a stop of `orchestration/round-manager.md`, an entry step that ends the session, ADR-0121's own `"over"` write), say whether and where the Round-Manager calls `run.commit` before it ends. Cover every way a live session ends in the present definition, a failed `run.commit` at entry step 0 included. A dead turn cannot commit, so its work is committed at the next turn's entry (owner point 1). Keep W1 (C2 of ADR-0127) under both readings, or say plainly why a choice departs from it.
   - (b) **What `run.commit` takes in when no round end is owed** (*W* = *H*, or no committed `STATE.json`). This is the widening of ADR-0127 decision 4's "Nothing owed" bullet. Cover the run's files below `runs/<run_id>/`, the key record files of ADR-0134 decision 7, and the owner's exception: the case file of the round in progress (`case-<run_id>-<W>.json`) is never taken into a commit that ends no round. Say whether the exclusions of ADR-0127 decision 4 (`.tmp`, ignored paths, `blobs/`) and its `commit_refused` conditions apply unchanged. Say whether the torn-tail removal of ADR-0006 decision 6 applies to such a commit.
   - (c) **The tool's surface.** Say whether the request, the result (`committed`) and the failure kinds of `run.commit` stay as ADR-0127 decision 4 has them. If a name or a kind changes, it is a tool-layer name and not a data-plane change. Say so.
   - (d) **The first `STATE.json` and a fresh run.** ADR-0127 decision 3 gives the first `STATE.json` no commit of its own. Say what holds now for a round-0 turn that writes it and then stops.
   - (e) **Step 1 of the turn loop and the self-check.** ADR-0127 decision 6 splits P2 into "nothing owed" and "owed P2" by the round-end rule. Say whether a P2 whose run directory holds uncommitted changes that end no round counts as owed. The case to consider is a death after ADR-0121's own `"over"` write. Say whether such a P2 starts a further turn, whether ADR-0125 decision 2 then runs the self-check, and what the P3 and open states of ADR-0122 decision 4 do with such changes. Also say whether ADR-0122 decision 3 ("as it found it", read on `round`) is affected by a commit that ends no round. If the executor finds a point here that the owner's answer does not cover and that is not design-level, leave it open in Boundaries with the reason and report it in Follow-ups. Do not decide it.
   - (f) **What is not promised.** For example: two writers at once, the loss of the machine before the commit, and no push (cite ADR-0127 decision 7; do not restate it).
4. **Walk-through.** A short table covering at least these cases:
   - a round-0 turn that writes the first `STATE.json` and stops at step 2 (`no_container_runtime`);
   - a round-0 turn that stops after step 4;
   - a turn that dies mid-round, and the next entry;
   - a round ≥ 1 turn that dies after `case.write` and before `round.end`: the case file stays uncommitted until its round ends;
   - ADR-0121's own `"over"` write, and a death after it;
   - a turn whose entry step 0 fails.
5. **Alternatives considered.** Include at least these:
   - the adopted design;
   - a commit only at the next entry, with no call at a live stop;
   - a commit made by the turn loop or `hilclaw.turn_start` (ADR-0127 alternatives (b) and (c));
   - taking the in-progress case file in as well (rejected by the owner's point 2).
6. **Consequences.**
   - Name the code slices, in order, as later code-mode tasks. Each is tested with a temporary git repository and, where a session is involved, a stub `claude` only (D16). Candidates, for the executor to confirm or reshape: (1) `hilclaw/run_commit.py`, the widened rule and commit, with its docstring and `MESSAGE`; (2) `orchestration/round-manager.md`, the call at each live session end, "The stop" sentence and entry step 0; (3) `hilclaw/further_turn.py` and `hilclaw/turn_start.py`, if decision (e) changes step 1.
   - List "Less exact, not edited", found by a search, not claimed complete. It must include at least: ADR-0127 decision 1 "Not answered", decision 4 "Nothing owed", decision 8, its Walk-through row "A turn dies inside round 3" and its Boundaries first item; ADR-0133 decision 5; ADR-0134 decision 7; ADR-0135 decision 5; ADR-0142 decision 1 "The stop" and Boundaries; ADR-0118 Boundaries where they name the commit of a cut-short turn; and the docstrings of `hilclaw/run_commit.py` and `hilclaw/further_turn.py`.
   - Add a runtime acceptance paragraph only if the record relies on a fact that only a live session or a runtime machine can show. Number any new item after (xlvi) of HQ-0057, in the turn-session series. Otherwise state that none is added.
   - Include "The cost, plainly".
7. **Boundaries.**
   - Runs outside ADR-0120 decision 1.
   - The push and the unpushed count (#5 A-3).
   - The Stop hook that would enforce a commit (PLAN P2-4).
   - `best.json` and `technique_stats.json` (OD-20, OD-7).
   - Whatever of decision (e) is left open.
   - Any edit of an earlier record, `hilclaw/`, `orchestration/`, tests, `.claude/`, any settings file, or the `HIL-Claw-data` repository.
8. **Do not invent.** Every sentence attributed to the owner is the HQ-0043 answer or another cited owner sentence, with its link. Nothing that is #5 A or B, C-6, OD-25 or OD-3 is decided.

### The registers

9. `ARCHITECTURE/Requirements.md`, OD-8 row: apply the register's "행 형식" rule (line 84). The row gains one link to ADR-0143 under `**확정분**:`, plus a short topic phrase that marks the owner's answer as the owner's. `**잔여**:` is rewritten in place so it no longer lists the commit of a turn that ends no round as the owner's open point. Do not restate the record, and add no dated paragraph. Change the status cell only as that rule allows.
10. `ARCHITECTURE/OpenDecisionProposals.md`: apply the header's "기록 규칙" (line 8).
    - § OD-8 gains one `- **채택분** [ADR-0143](…) — …` line next to the ADR-0127 line.
    - Sub-question ⑪'s trailing status (line 135) is rewritten in place. Its "남음" drops the owner part. It keeps "그 범위 밖의 run" and anything decision (e) leaves open. The bullet head's status word is updated only if the rule calls for it.
    - The question text stays.
    - Check the OD-18 bullet at line 283 ("남음: 1 turn = 1 commit …"). If this record answers it for this scope, rewrite its status in place by the same rule; if not, leave it.
    - Add no dated note.
11. `ARCHITECTURE/StandardScenarios.md`: re-check S0, S1 and S2 by the check rules (CLAUDE.md "문서 커버리지 재검사"). Follow the first paragraph of § 검사 결과: update the "최근 재검사" line in place (date, trigger ADR-0143/T-0391, result). Add a "판정 변화 이력" entry only if a verdict or gap changes. Write no ADR summary.
12. No other file changes. `UsageCases.md` changes only if a sentence there becomes false. If so, name it in the commit body and keep the edit minimal.

### Gates and procedure

13. Size: within the D4 cap (≤ 300 changed lines excluding tests, ≤ 5 files).
14. Doc mode (A-13; DRIVER §2):
    - work on branch `claude/T-0391-adr-first-case-turn-end-commit`;
    - run the context-isolated reviewer cycle to Approve;
    - rebase on `origin/main` and push to `main` directly;
    - the commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0391`.
    - If 7 rounds pass without Approve, stop with BLOCKED (review rounds exceeded) and keep the branch.
15. Report to the driver the text of the DRIVER §9 notice for #5. The driver posts it.
16. D16: no `claude` process and no container is started, and nothing is required of the development machine.

## Out of Scope

- Any code, test or prompt change: `hilclaw/run_commit.py`, `hilclaw/further_turn.py`, `hilclaw/turn_start.py`, `orchestration/round-manager.md` and their tests. These are the code slices of decision 6, later tasks.
- Editing any earlier ADR. Their sentences that become less exact are listed, not edited.
- ADR-0142 slice 2 (`board.run`, `experiment-runner`) and anything waiting on HQ-0021.
- The push, the unpushed count, hooks (PLAN P2-4), and `best.json`/`technique_stats.json`.
- The files of open PR #186.
- The PLAN "보류" lines (for example T-0370's "One round at most" wording).

## Follow-ups

- After landing: the code slices of ADR-0143 Consequences, in order. The first is probably `hilclaw/run_commit.py`, then `orchestration/round-manager.md`.
- Any point of decision (e) left open as not design-level goes to the driver as a possible HQ.

## Result

(to be filled by the executor)
