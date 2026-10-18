---
id: T-0303
title: Write ADR-0104 on where and in which form the imprecise-timing finding of ADR-0103 is kept in the data plane — OD-13 sub-question ⑪ (나); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-13, NFR-3, OD-8, FR-10, "#5 D6", "owner decision 2026-10-15 item 3"]
dependsOn: [T-0302]
touchesFiles: [ARCHITECTURE/decisions/ADR-0104-od13-imprecise-timing-mark.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md, ARCHITECTURE/EventKinds.md, ARCHITECTURE/StepValues.md]
estimatedSize: {loc: 200, files: 5}
hq: []   # Design-level OD (DRIVER §9): OD-13 is not owner-only. The owner's decision of 2026-10-15 item 3 approved recording the mark in the data plane and left its form to a record; the integrator note on OD-13 reads that approval as the A-13 owner approval of the schema change the mark needs, and of nothing else. Only one of the two index files (EventKinds.md, StepValues.md) may change, and only if the record's choice needs it, so at most 5 files change. Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 run-tool and check records, OD-30, instance members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, 0014, 0016..0019 and 0030 are runtime-acceptance (HQ-0030 is about ADR-0103's facts, and this task tries none of them). No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

The owner decided on 2026-10-15 (item 3, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913) that recording in the data plane that a measurement or a run was made in an environment where timing is hard or imprecise "is approved; its form is left to a record". ADR-0103 (T-0302, main 274fed8) answered OD-13 sub-question ⑪ (가) for the runs of ADR-0061 decision 1. It says when a measurement or a run is "found imprecise". It deliberately left open where that finding is kept, in which form, and whether it is stored or derived: that is ⑪ (나). ADR-0103 Consequences names (나) as the expected next record. It also notes that a measurement's finding can be computed from its result alone, so the mark could be derived rather than stored. If the mark goes into a tool result, ADR-0100 applies.

No code can apply ADR-0103 until (나) says where its output goes. This task writes one design record (DRIVER §9) that answers ⑪ (나) for the same scope. It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time limit), §5 (lines 86-115: task format, naming convention, `Task:` trailer, size limit), §8 (lines 135-139: the driver tail of #5 comments), §9 (lines 141-149: OD closing authority, ADR + reviewer Approve + #5 notice).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode and its BLOCKED reasons, including "데이터 plane 스키마 변경").
- `ARCHITECTURE/Requirements.md` line 36 (FR-18), line 46 (NFR-3), lines 80-86 (정본 규칙 and **행 형식** at line 84: the only rule for editing a register row), and the register rows OD-8 (line 99), OD-11 (line 102), OD-13 (line 104), OD-14 (line 105), OD-27 (line 118).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; **기록 규칙** at line 8: the only rule for edits to this file) and lines 190-207 (OD-13 section: the owner decision at line 202, the **integrator note at line 203** on the schema approval, sub-question ⑪ at line 204).
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙), S2 (lines 66-75), S6 (lines 101-111), S9 (lines 148-155), lines 168-173 (§검사 결과; its first paragraph at line 170 is the recording rule for the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md` in full (136 lines). This is the record whose finding is to be kept. Note especially decisions 1, 5 and 6, Limits 1 and 2, Consequences and Boundaries.
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md` lines 23-80 (decision 1: the run files, their writers and what is open for each, including `STATE.json`, `instance.json`, `events.ndjson`, `sim.json`/`board.json`) and lines 98-105 (decision 4: one writer role per directory).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` lines 20-97 (decisions 1-10: line format, envelope, append only, the log and the result files, versioning).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` lines 26-60 (decisions 1-3: the two lines around a journaled step; `result` on `step_ended`) and lines 94-102 (decision 7).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` lines 37-44 (decision 2), lines 66-76 (decision 4), lines 107-152 (decisions 8-10: what a result never holds, the closed member list, what is not decided), lines 170-183 (Limits) and lines 216-232 (Boundaries).
- `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` lines 21-58 (a changed payload is a new kind; `result` is the contract's).
- `ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md` lines 21-63 (vocabulary, the index, how a name enters it).
- `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` lines 22-56 (a changed result definition takes a new `step` value; what counts as a change).
- `ARCHITECTURE/EventKinds.md` and `ARCHITECTURE/StepValues.md` in full (short). Read their "Adding a row" rules.
- `ARCHITECTURE/decisions/ADR-0102-od8-spend-axis-change.md` Status section only, as the model of a Status bullet list for a §9 record (including the objection window line).

## Acceptance Criteria

1. **Pre-check.** Before writing, confirm that `ARCHITECTURE/decisions/ADR-0104-*` does not exist on `origin/main` and that no accepted record has answered OD-13 ⑪ (나) since this task was written (`git log origin/main -- ARCHITECTURE/OpenDecisionProposals.md`, and the ⑪ bullet). Run the CLAUDE.md "세션 진입 점검": open PRs and issues #4, #5, #7, #8. If the number is taken, use the next free one and say so in `## Result`. If ⑪ (나) has been answered, ADR-0103 has been reverted, or an owner comment on #5 addresses the mark, stop and report BLOCKED (requirement unclear).
2. **The record.** One new file, `ARCHITECTURE/decisions/ADR-0104-od13-imprecise-timing-mark.md`, in English, with the sections the sibling records use: Status, Context, Decision (numbered), Alternatives considered, Consequences, Boundaries (not decided here), References. The Status says that it closes OD-13 ⑪ (나) for the scope it states. It cites DRIVER §9 and states the 7-day objection window from the #5 notice.
3. **Scope.** The scope is the scope of ADR-0103: the runs of ADR-0061 decision 1. It may be narrower, with a reason. It may not be wider, because ⑪ (가) is unanswered outside it.
4. **What it decides (⑪ (나)).** The record answers, for that scope:
   - for the finding of a **measurement** and for the finding of a **run** (ADR-0103 decision 5), whether each is **stored** or **derived** from what is already kept. If it is derived, the record says from which kept records a later reader derives it, and checks that these records actually hold the inputs ADR-0103 decision 6 needs, citing where each input is kept today. If it is stored, the record says in which file of ADR-0004 decision 1, under which member, in which form, written by which writer role (ADR-0004 decision 4) and at which moment;
   - how the class ground of ADR-0103 decision 4, whose input does not exist yet, fits the choice. Either the record makes room for it, or it leaves that part to the record that produces the input and says so. It does not decide how the class is established (that is OD-14 ① and a later record);
   - what a reader concludes when a mark is absent. In particular, the record says how a reader tells "not found imprecise" from "made before this record" or "not computed", or why it does not need to;
   - how the choice serves what O1 needs it for, namely knowing which numbers carry the warning, without deciding where the warning is shown (⑪ (라)).
5. **Alternatives.** Weigh at least these, against the owner's text, ADR-0004, ADR-0006 decision 5 (append only), ADR-0007 decision 9 / ADR-0103 decision 6 (reproducibility), C-7, and what each choice costs under ADR-0097, ADR-0098 and ADR-0100:
   - (a) nothing stored: both findings are derived;
   - (b) a new member of the `sim.run`/`board.run` result. This is a result-definition change under ADR-0100, so it needs new `step` values;
   - (c) a new event kind in `events.ndjson` (ADR-0098);
   - (d) a member of `STATE.json`;
   - (e) a member of `sim.json`/`board.json`, whose fields are still open (OD-13 ⑩, PLAN P1-8).
   For any alternative that is rejected because it would decide an open question, name that question.
6. **Schema changes, if any.** The integrator note at OpenDecisionProposals line 203 reads the owner's approval as covering the data-plane schema change needed to carry the mark, and nothing else. If the record adds anything to the data plane, it adds only what carries the finding. It follows the rule that governs that kind of addition:
   - for an event kind: ADR-0098 decision 4, plus one row in `ARCHITECTURE/EventKinds.md` with state `defined`;
   - for a tool-result member: ADR-0100 decision 3, which means new `step` values for every affected value, a row for each in `ARCHITECTURE/StepValues.md` per its "Adding a row" rule, and the old values left as they are;
   - for a member of an existing file: the record names any `schema_version` consequence, or names it as left to OD-11.
   At most one of `EventKinds.md` and `StepValues.md` may change. If the choice needs both, or needs any code, test or existing ADR to change in the same commit, stop. Report BLOCKED (requirement unclear) and propose a split in `## Result`. If (나) cannot be answered without deciding ⑪ (다) or (라), OD-14 ①, OD-13 ⑩ beyond the mark itself, or the fields of `STATE.json`, `sim.json` or `board.json` beyond the mark, stop and report BLOCKED with the proposed owner question in `## Result`.
7. **What it must not decide or change.** Under Boundaries the record names as left open:
   - ⑪ (다): reuse across runs (FR-18) and judgement against an absolute target (FR-2);
   - ⑪ (라): where and how the warning is shown (OD-27);
   - the producing of the class input, and OD-14 ①;
   - ⑪ (가) outside the scope;
   - OD-13 ①, ② and ⑥.
   The record does not change ADR-0103's detection rule or its constant. It does not change ADR-0007's improvement rule. It does not stop a run.
8. **Runtime facts (D16).** If the record rests on a fact that only a runtime machine can establish, it lists that fact as a Limit, and `## Result` lists it as a runtime-acceptance item for the driver to raise through DRIVER §8. Do not repeat the facts already raised as HQ-0030; cite ADR-0103 Limit 2 instead. Nothing is tried on this machine, and no `claude`, container, compiler or timing run is started.
9. **Records not edited.** The record does not edit ADR-0103, ADR-0063, ADR-0004, ADR-0006, ADR-0011 or any other accepted record. The record's Consequences list every statement in those records that becomes less exact (for example ADR-0103's "Where and in which form the finding is kept is part (나)", and ADR-0061 Limit 3 / ADR-0063 Limit 5), each marked as "not edited and now less exact".
10. **Register edits.** Follow the rules written in the files themselves. Do not copy wording from earlier task files and do not restate the record.
    - `ARCHITECTURE/Requirements.md`: edit the OD-13 row only, as the **행 형식** at line 84 prescribes. Add one link to the new ADR with a few words of topic after `**확정분**:`, and rewrite the ⑪ part of `**잔여**:` in place so it says what remains. Extend the status date range if the format requires it. The status word stays. NFR-3 is not edited.
    - `ARCHITECTURE/OpenDecisionProposals.md`: edit the OD-13 section only, as the **기록 규칙** at line 8 prescribes. Add one adopted line for the new ADR in the place the rule gives. Rewrite the ⑪ bullet's tail status and head status word in place. Keep the question's wording. Add no dated paragraph. If the record registers a new sub-question, add it as the rule says and name it in `## Result`.
    - `ARCHITECTURE/StandardScenarios.md`: re-check coverage under 검사 규칙, at least S2, S5, S6, S9, S10 and every scenario that cites NFR-3 or OD-13. Update the "최근 재검사" line as the first paragraph of §검사 결과 (line 170) prescribes. Add a history entry only if a verdict changes or a gap is found or closed.
    - `ARCHITECTURE/EventKinds.md` or `ARCHITECTURE/StepValues.md`: edit one of them only if criterion 6 requires it, and only by its "Adding a row" rule.
11. **Mode and landing.** Document mode (CLAUDE.md A-13): branch `claude/T-0303-adr-od13-imprecise-timing-mark`, context-isolated reviewer cycle (dev-code-review, at most 7 rounds), rebase on `origin/main`, one squashed commit on `main`. The trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0303` go in the **last paragraph** of the message, together with `Co-Authored-By`, with no blank line between them. No force push. Delete the branch. `git diff --check` must be clean, files use LF only, and every new relative link and anchor must resolve.
12. **#5 notice (DRIVER §9).** After landing, post the OD-closing notice on issue #5 in English. It states the commit, the scope and the 7-day objection window, and its last line is `— posted by driver`. Record its URL in `## Result`.

## Out of Scope

- Any code: no change to `hilclaw/` or `tests/`. A later code task applies ADR-0103 and this record.
- ⑪ (가) outside ADR-0103's scope; ⑪ (다), (라); the producing of the class input; OD-14 ①; OD-13 ①-⑩ other than what the mark itself requires; OD-27; FR-2 or FR-18 semantics.
- The fields of `STATE.json`, `instance.json`, `sim.json` and `board.json` beyond the mark (PLAN P1-8).
- Editing NFR-3, any FR, any existing ADR, `ARCHITECTURE/SpendAxes.md` or `README.md`.
- Any runtime check (D16).

## Follow-ups

- (code, expected after this task) Apply ADR-0103 decisions 3 and 5 as a pure function, with the constant `resolution_share_max`, and store or derive the mark as this record decides. Plan it within the size cap. If it adds a tool-result member, it carries the new `step` values.
- (doc) The record that produces the class input of ADR-0103 decision 4, together with OD-14 ①.
- (doc) ⑪ (다) and (라), when their dependencies (FR-18 case records, OD-27) allow.

## Result
