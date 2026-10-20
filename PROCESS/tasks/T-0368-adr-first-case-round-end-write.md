---
id: T-0368
title: Record ADR-0135, the write that ends a first-case round - who folds the spend view, how the result reaches STATE.json, and what that one write holds (part of OD-23; PLAN P2-1)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-1, FR-3, NFR-1, OD-23, OD-8, OD-17, S0, S1]
dependsOn: [T-0366, T-0367]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 220, files: 4}
hq: []
---
## Why

PLAN P2-1 (the Round-Manager prompt and the round-0 procedure) is the first unchecked item in the P2 order (PLAN P2 head, D18). This task is a slice of P2-1, so the D18 rule for work outside the checklist does not apply. P2-5 needs it: no round of any run can end without this write. P2-5's five rounds each end in it, and ADR-0121's `"over"` comes in the write that ends the last round.

Every round of a first-case run ends in one write of `STATE.json`. That write sets `round` to the next round and `budget_spent` to the spend view of the log folded to a position the log has reached (ADR-0012 decisions 3 and 6, ADR-0011 decision 6). In the write that ends the run's last round it also sets `run_status` `"over"` (ADR-0121 decisions 3 and 4). The order around it is already fixed: `case.write` right before it in a round of 1 or more (ADR-0133 decision 5), and `run.commit` right after it (ADR-0127 decision 3). One point is still open, and the records name it as OD-23's:
- ADR-0012 decision 6: "Who folds, and how the result reaches the writer, is not decided here (OD-23)".
- ADR-0011 decision 6: "Which function folds, and how the result reaches the Round-Manager as the only writer of `STATE.json`, is PLAN P1-8 and OD-23".
- ADR-0124 Boundaries: "a tool for the fold is not added here".

Today the Round-Manager has only `state.write`. That tool writes exactly the content it is given. So the model would have to produce the totals, the position and the open steps itself.

T-0367's Follow-ups name this record as the next P2-1 work. OD-23 and OD-8 are design-level ODs and not owner-only (DRIVER §9). So this task writes the ADR (DRIVER §6, §9).

Open HQs were checked. None of them blocks this record, but the record must not answer any of them:
- HQ-0043 (whether a turn that ends before its round ends commits);
- HQ-0041 (the coder's model, and whether coder tokens count toward the run's budget; an axis not accounted through the log);
- HQ-0031;
- HQ-0048 (ADR-0132 is unlanded, so no `hypotheses.write` exists on main).

All verification is by reading and review. No `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §2 (doc mode);
  - §3-5 (executor procedure, resume rule, time limit);
  - §5 (naming: branch `claude/T-0368-<slug>`, trailer `Task: T-0368`; size cap);
  - §8 (the `— posted by driver` footer);
  - §9 (OD closing authority, the owner notice on #5, the 7-day objection window).
- `CLAUDE.md`, all rules. In particular:
  - "미결은 발명하지 않는다";
  - 문서 커버리지 재검사;
  - the A-13 doc-mode procedure: the reviewer cycle, a rebase onto `origin/main`, one squashed commit with the `Reviewed-by` and `Task:` trailers, and a direct push to main;
  - the BLOCKED reasons (a data-plane schema change is one);
  - "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- The file and its write, in `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`:
  - decisions 3 to 7 (lines 41-100);
  - Boundaries (lines 142-152).
- The spend view and the fold, in `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`:
  - decisions 6 and 7 (lines 79-102: snapshot rule, replay, bound, disagreement);
  - decision 9 (lines 109-118).
- The log's torn tail: `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` decision 6 (lines 66-73).
- The replacement: `ARCHITECTURE/decisions/ADR-0013-od8-state-file-replacement.md` decisions 2 and 7 (lines 29-48, 84-89).
- The `"over"` write: `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md` decisions 3 and 4 (lines 47-72) and Boundaries (lines 123-135).
- The present tools: `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`:
  - decisions 2 and 3 (lines 37-63);
  - Consequences (lines 102-120), especially the bullets "What the round-0 part … still waits on" and "The cost, plainly" ("The model copies values");
  - Boundaries (lines 121-128).
- What comes right before and right after the write:
  - `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md` decisions 4 and 5 (lines 55-68) and Walk-through (lines 73-85);
  - `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md` decisions 3, 5 and 8 (lines 43-49, 69-75, 92-96).
- The turn and its end: `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md` decision 2 (lines 57-66). The first file: `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md` decision 2 (lines 43-53).
- A recent record of the same kind, as a model of form only (do not restate it): `ARCHITECTURE/decisions/ADR-0134-od26-first-case-key-records-store.md` (136 lines).
- The record format: `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (line 146 on).
- `ARCHITECTURE/Requirements.md`:
  - FR-1 and FR-3;
  - the OD register preamble, **"행 형식"** (line 84);
  - rows OD-8, OD-17, OD-19 and OD-23.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's **"기록 규칙"** (line 8);
  - § OD-23 (from line 394), with its "제안으로 남는 부분(미확정)" bullet;
  - § OD-8 (from line 87) and § OD-17 (from line 263), only to check that nothing there becomes false.
- `ARCHITECTURE/StandardScenarios.md`:
  - §검사 규칙 (lines 13-29);
  - §검사 결과 (from line 168). **Its first paragraph is the recording rule.**
  - S0, S1 and S2.
- Code, read only as observations. This record binds no code.
  - `hilclaw/run_journal.py`: the module docstring and `current`. It already folds the stored view over the tail.
  - `hilclaw/journal.py`: `fold`, `SpendView`.
  - `hilclaw/run_state_file.py`: `replace`.
  - `hilclaw/run_file_tools.py`: the module docstring. `state.write` writes exactly what it is given.
  - `hilclaw/events.py`: `read` and `remove_torn_tail`.
  - `hilclaw/run_commit.py`: the module docstring.
  - `hilclaw/tools.py`: `default_registry`.
  - `orchestration/round-manager.md` (whole, 97 lines).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.
  - Open PR #186 (T-0324, BLOCKED by HQ-0032) touches only `hilclaw/start_instance.py` and three test files. It does not overlap this task.
  - The unlanded branches `claude/T-0361-*`, `claude/T-0318-*`, `claude/T-0231-*`, `claude/T-0210-*` and `claude/T-0264-*` edit `Requirements.md`, `OpenDecisionProposals.md` and `StandardScenarios.md`. `claude/T-0361-*` edits the OD-23 row and section (ADR-0132). Do not take their content, and note in the Result any overlap you find.

## Acceptance Criteria

1. **The record and its number.**
   - A new record `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Alternatives considered, Consequences, Boundaries, References.
   - ADR-0132 is held by the unlanded branch `claude/T-0361-*`. Before the push, confirm that ADR-0135 is free on `origin/main` and on every remote branch. If it is not, take the next free number and update every reference.
   - Keep the record at about 180 lines or fewer.
   - Mark what is cited (with its source) apart from what is this record's own.
   - Include the owner-sentence search: name the places searched and the terms used, and quote what was found or say that nothing was found.
2. **Scope.** The runs of ADR-0120 decision 1 only. The record answers the write that ends a round, given that the Round-Manager has reached it. It does **not** define what ends a round, or when a round's work is done: bring-up, baseline, the coder call, the measurement and the verdicts stay with later P2-1/P2-2/P2-3 records. It also leaves open every end of a run other than `round_budget`, as ADR-0121 decision 4 lists them.
3. **Points to weigh.** Weigh each point against at least one alternative, in the Alternatives table.
   - (a) **Who folds, and how the result reaches the writer.** Weigh at least these three:
     - a new registry tool that folds and performs the write itself, so that the model supplies no number;
     - a read tool that returns the view, which the Round-Manager then copies into `state.write`;
     - widening `state.write` so that it computes the view.
     Count as a cost of each choice whether the model copies or computes values (ADR-0124 Consequences, "The model copies values"). If a tool is chosen, give it a name, a request, a result and failure kinds in the form of ADR-0124 decision 3. Say whether it is journaled and whether it is an FR-10 tool. Say which existing failure kinds it reuses, and justify every new kind. Search `hilclaw/`, `tests/`, `orchestration/` and `ARCHITECTURE/` for the chosen name and its new kinds on the day, and record that search.
   - (b) **Which view is stored.** Choose between the stored view folded over the tail (ADR-0011 *Replay*, the bound on lines interpreted) and a fold from the first line. Say to which position the fold runs. Say how a torn tail and a damaged line are treated, citing ADR-0006 decision 6. A disagreement between the stored view and the log is OD-17 sub-question ③. Answer it only as far as ADR-0011 decision 6 already does, and say so.
   - (c) **What the one write holds.** It holds `schema_version`, the next `round` and the view. It also holds `run_status` `"over"` when the new `round` reaches the `round_budget` of the run's `instance.json` read then (ADR-0121 decision 4). Say who makes that comparison, the tool or the model. Say what happens when the instance states no `round_budget`. Say what happens to a top-level member that the record does not define (ADR-0013 decision 7, sub-question ⑫). Do not add a member or a value to the data plane. If the answer seems to need one, stop and return BLOCKED (data-plane schema change).
   - (d) **What the Round-Manager does when the write fails.** Weigh at least two answers. One is to report the kind in one line and end the session with the round not ended, so that the next turn goes on with the same round (ADR-0118 decision 2; ADR-0127 decision 5 finds nothing owed). Weigh any other answer you find. Do not answer HQ-0043. A retry within a turn is OD-17's.
   - (e) **The place in the definition.** Say where the write sits in "The round steps" of `orchestration/round-manager.md`: after the `case.write` of a round of 1 or more, with no `case.write` in round 0 (ADR-0133 decision 4), and before `run.commit`. Cite that order. Do not decide it again. This record does not edit the definition (point 6).
4. **Walk-through.** Cover at least these rows: the end of round 0 of a run with `round_budget` 6; the end of round 4 of a run with `round_budget` 5 (the `"over"` row of ADR-0121's worked example); a log with a torn tail at the write; the write failing; a death between the write and `run.commit` (cite ADR-0127 decision 5); and a death inside the write (cite ADR-0013).
5. **Consequences.** These must cover:
   - the code slices the record enables, as later tasks, each under the D4 cap: the tool, if one is chosen, with its test file and its registration in `default_registry`; and the step in `orchestration/round-manager.md`;
   - every sentence of an earlier record or docstring that becomes less exact, listed and not edited. At least ADR-0012 decision 6, ADR-0011 decision 6, ADR-0121 decision 3 ("The means is open") and ADR-0124 Boundaries;
   - new runtime acceptance items in the turn-session series, numbered after ADR-0134's (xxvii) and (xxviii). For example: the main session of a `-p` turn session sees the new tool and may call it. Their HQ is the driver's to raise, not this task's;
   - the A-13 reading: doc mode, no code, and no data-plane change.
6. **Boundaries.** List what stays open: what ends a round; the other ends of a run (ADR-0121 decision 4); axes not accounted through the log, HQ-0041 included; the lock and the retry (rest of OD-17); budget enforcement (OD-19); `best_ref`, `next_action` and `phase` (OD-20, OD-23, OD-29); HQ-0043; and resumed, continued or branched runs (OD-8 ①). Edit nothing in `hilclaw/`, `orchestration/`, `tests/`, `.claude/`, any settings file or the `HIL-Claw-data` repository. Edit no earlier ADR.
7. **Requirements.md.** Follow the register's "행 형식" rule (line 84). Change only the OD-23 row (and the OD-8 row, if the record answers part of OD-8), with one link to ADR-0135. Rewrite the open part of the row in place so that it no longer lists what ADR-0135 answers. Do not restate the record in the row and do not add a dated note. Change no OD status: OD-23 stays open.
8. **OpenDecisionProposals.md.** Follow the header's "기록 규칙" (line 8). In § OD-23, add one link line for ADR-0135 among the adopted parts, and rewrite the "제안으로 남는 부분" bullet in place where the record narrows it. Write no summary of the decisions and no dated paragraph. Touch § OD-8 or § OD-17 only where a sentence there becomes false, and in the same way.
9. **StandardScenarios.md.** Re-check coverage by §검사 규칙. Record the result as the first paragraph of §검사 결과 prescribes. If no verdict changes, write only what that paragraph asks for in that case, and add no history entry.
10. **Process.**
    - Doc mode (CLAUDE.md A-13): use branch `claude/T-0368-<slug>`.
    - Run the context-isolated reviewer cycle (at most 7 rounds) to Approve.
    - Rebase onto `origin/main`.
    - Push one squashed commit to main whose message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0368`.
    - The §9 notice on #5 is the driver's. Write its text (English, one paragraph, the link to ADR-0135, the 7-day objection window) into `## Result` for the driver to post.
    - No `claude` is started at any point (D16).

## Out of Scope

- Any code: the tool, its tests, `default_registry`, and the round step in `orchestration/round-manager.md`. These are later code slices.
- What ends a round, and every other round step (bring-up, the self-check, the coder call, the measurement, baseline, the evaluator, the selection, ADR-0133 slice 2).
- Any change to the data plane (members, files, kinds, values or versions), or to a validator.
- HQ-0031, HQ-0032, HQ-0041, HQ-0043 and HQ-0048. The owner-only items: #5 A/B, C-6, OD-25 and OD-3 (gates).
- Every less-exact sentence of earlier records: list it, do not edit it (D18 hold).

## Follow-ups

- Planner's view: after this record, a code slice adds the chosen tool, and a further slice writes the round-end step into `orchestration/round-manager.md`. That step can be written only once the steps before it (round 0's bring-up and baseline) are defined, or with an explicit stop in front of it.

## Result

- **Outcome**: DONE. Doc mode. One squashed commit `0d5a3ba` was pushed to `main` with trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0368`. The task branch `claude/T-0368-adr-first-case-round-end-write` is deleted locally and on origin.
- **Files**:
  - new `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md` (147 lines);
  - `ARCHITECTURE/Requirements.md`: the OD-23 row gains one `확정분` link, and the `잔여` "who folds" item is narrowed to runs outside the first case;
  - `ARCHITECTURE/OpenDecisionProposals.md`: § OD-23 gains one 채택분 line, and its 제안으로 남는 부분 is narrowed in the same way; in § OD-8 the "누가 fold하는지" phrase is narrowed in the same way;
  - `ARCHITECTURE/StandardScenarios.md`: the 최근 재검사 line now reads "S0·S1·S2, no verdict change, no gap".
- **Decision in brief**: a new registry tool `round.end` with request `{run_id, round}`. It folds the stored view over the tail, compares `round` + 1 with `round_budget` and writes `run_status` `"over"` when the budget is reached. It refuses a `STATE.json` that has any top-level member other than the three, using a new kind `state_member_extra`. It replaces `STATE.json` through `run_state_file.replace`. On a failure the Round-Manager reports the kind and ends the session, and the round stays open. No data-plane change. The number ADR-0135 was free on `origin/main` and on every remote branch before the push.
- **Review**: 7 rounds.
  - Rounds 1 and 3 were Request changes.
  - Rounds 2 and 4 to 7 were Approve with Low/Nit findings. Each finding through round 6 was fixed and sent back for review.
- **Follow-ups (not fixed: fixing would need an 8th review round)**: the Low and Nit findings of round 7, all in ADR-0135. The driver may file these in the PLAN "보류" section (D18: citation and wording clean-ups).
  - (1) Decision 5, "Why not go on": the reason given for ADR-0133 decision 4's rejection is loose. ADR-0133 gives as its reason the undecided re-entered round (OD-17) and a refusal that repeats.
  - (2) "The cost, plainly" should also say that a damaged log line makes every turn redo the round's work before `round.end` refuses with `run_file_invalid`, until the log is restored.
  - (3) Nit: checks ③ and ④ may come in either order in code built on `run_journal.current`. A code slice may meet the stated order or note it.
- **Later slices (from Consequences)**:
  - (1) code: the tool `round.end`, its test file, and its registration and docstring in `default_registry`;
  - (2) the step in "The round steps" and its tool sentence in "Your run" of `orchestration/round-manager.md`, written with P2-1's round steps or behind an explicit stop.
- **Runtime acceptance items**: new items (xxix) and (xxx), in the turn-session series. The HQ (`runtime-acceptance`) is the driver's to raise.
- **Overlap with unlanded branches**:
  - `claude/T-0361-adr-first-case-selection-hypotheses-write` (ADR-0132) edits the same OD-23 register row (`확정분` and `잔여`), the same § OD-23 bullets (채택분 lines and 제안으로 남는 부분), and the StandardScenarios 최근 재검사 line. If it is ever landed it must be rebased onto `0d5a3ba`.
  - None of its content was taken.
  - The other unlanded branches named in Required Reading were not compared.
- **Session entry check**: open PR #186 does not overlap this task. #5 has no owner answer to HQ-0031, HQ-0041, HQ-0043 or HQ-0048, and none of them is answered by ADR-0135.
- **§9 notice for #5 (for the driver to post)**:

  ### ADR-0135 accepted — T-0368: the write that ends a first-case round (part of OD-23)
  Under PROCESS/DRIVER.md §9 the driver accepted [ADR-0135](https://github.com/myungjoo/HIL-Claw/blob/main/ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md) (main 0d5a3ba; context-isolated review, 7 rounds, Approve). For first-case runs (ADR-0120 decision 1), the Round-Manager ends a round only by calling a new registry tool, `round.end` (`run_id`, `round`). The tool folds the stored spend view over the log's tail and compares the next round with the run's `round_budget`. In the same write it puts `run_status` `"over"` when the budget is reached, and it replaces `STATE.json` itself, so the model supplies no number. It refuses a `STATE.json` that holds any top-level member other than `schema_version`, `round` and `budget_spent` (OD-8 ⑫ stays open). On any failure the Round-Manager reports the kind and ends the session, and the round stays open. No data-plane member, value or version changes; HQ-0041 and HQ-0043 are not answered, and OD-23 stays open. You may object within 7 days of this notice; an objection creates a task that reverts the record and its edits.

  — posted by driver
