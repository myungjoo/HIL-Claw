---
id: T-0292
title: Write ADR-0098 on the vocabulary of `kind` in `events.ndjson` — what list of event kinds exists, where it is kept and how a name enters it (the remaining part of OD-8 sub-question ⑧); no code
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-8, FR-13, NFR-7, OD-11, OD-17]
dependsOn: [T-0291]
touchesFiles: [ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 180, files: 4}
hq: []   # design-level OD (DRIVER §9, driver may close with an ADR); not owner-only (not #5 A/B, C-6, OD-25, OD-3). Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 / OD-30 / OD-8 instance records, clang_build, local_run, the build log and json helpers; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 (runtime STATE / instance / events schemas, "OD-8 종결 필요(§9 ADR 경로)") is still open. OD-8 sub-question ⑧ asks two things about `runs/<run_id>/events.ndjson`: the vocabulary of `kind`, and how a change in the `data` of a kind is told apart. T-0291 landed ADR-0097 (main 2c9e8c9), which answered the second part (a changed payload is a new kind under a name never used; a line is told apart by `kind` alone) and left the first part open in its Boundaries: "what list of kinds exists and where it is kept. Today the names used are those of accepted records …; decision 2's 'a name no accepted record has used' relies on those records and fixes no list."

ADR-0097's rule now depends on being able to tell which names have been used, so the open vocabulary part is the next piece of ⑧. This task writes one design record (DRIVER §9) that answers it: what the vocabulary of `kind` is, where the list of kinds is kept, how a new name enters it, and whether anything checks a line's `kind` against it. It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer), §9 (lines 141-149; OD closing authority, ADR + reviewer Approve + #5 notice with the driver tail).
- `CLAUDE.md` "상시 규칙", in particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` lines 80-86 (정본 규칙 and **행 형식** at line 84 — the rule for editing a register row), line 99 (OD-8 row), line 102 (OD-11), line 108 (OD-17), line 114 (OD-23).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; the **기록 규칙** at line 8 — the rule for adopted lines and in-place status rewrites), lines 87-153 (OD-8; sub-question ⑧ is in the "하위 질문(ADR-0006이 넘긴 것 …)" bullet at line 119; ㉟ is the bullet at line 140), lines 165-172 (OD-11), lines 242-251 (OD-17), lines 359-370 (OD-23).
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-173 (§검사 결과: its first paragraph is the recording rule, then the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` (whole file, 93 lines; decisions 1-2, Consequences and Boundaries are the direct base of this record).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` decisions 3 and 8 (lines 36-54, 81-86), Consequences and Boundaries (lines 129-151).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` lines 42-60 (decision 3: the two kinds `step_started` / `step_ended`) and lines 165-183.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` lines 146-153 (Record format; the *name* form) and `ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md` (a recent record, for the Status bullets: §9 acceptance, three kinds of content, objection window).
- `hilclaw/events.py` lines 30-40, 70-85, 105-165 (the envelope check; `kind` checked against no vocabulary; `append`) and `hilclaw/journal.py` lines 40-50, 110-130, 225-240 (`STEP_STARTED`, `STEP_ENDED`, `_MEMBERS`; a line of another kind is not a step line) — read as files for the record's observations; run nothing.

## Acceptance Criteria

1. A new file `ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md` (verify first that no `ADR-0098-*` exists; if the number is taken, use the next free one consistently in every file) in the Record format of ADR-0001, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here) and References. Status states acceptance under DRIVER §9, the three kinds of content (owner sentences quoted word for word — or that none speaks of this —, cited content with its source, the record's own design), the 7-day objection window from the #5 notice, and that it is a record, not code (observations read from files at a named commit; nothing run).
2. The Decision answers, for `events.ndjson`: **what the vocabulary of `kind` is** (the set of names a line may carry with a defined meaning), **where the one list of kinds is kept** (or why there is no separate list and where a reader finds the defined kinds instead), **how a name enters it** (what a kind-defining record must do so that ADR-0097's "a name no accepted record has used" can be checked), and **whether anything checks a line's `kind` against it** (writer side, reader side, or nothing), consistent with ADR-0006 decision 3 ("an unknown kind, not an error") and ADR-0097 decision 2 (names never reused, including names of reverted records).
3. Alternatives considered weighs at least these, each with its reason: (a) no separate list — the accepted records are the vocabulary, found by a stated means (for example the OD-8 adopted lines or ADR references); (b) one list in an `ARCHITECTURE/` document that each kind-defining record updates; (c) a list in 2층 code (for example constants in `hilclaw/events.py`), with or without a check at `append`; (d) leaving the part open. The OD-8 text says ⑧ is to be decided "종류를 정의하는 task들과 함께 (OD-11·OD-23)"; the record states why it can answer the vocabulary part now without defining any kind, or, if it cannot answer some piece without OD-23, leaves that piece open with a reason.
4. Observations (binding nothing) cite `hilclaw/events.py` and `hilclaw/journal.py` as read at a named commit: `kind` is checked against no vocabulary in `validate`/`append`; `journal.py` knows exactly `step_started` and `step_ended`; no other kind exists in any accepted record or in the code (re-confirm ADR-0097 decision 1; grep the decisions directory for any other kind name). The record states in Consequences what its answer means for these modules: either "no code changes", or exactly one code follow-up task named there (nothing written here). A writer-side refusal of unknown kinds, if chosen, must be a follow-up and must not change how a reader treats an unknown kind.
5. **No line that exists today changes**: `schema_version` stays 1, the envelope and the exact `data` members of `step_started` and `step_ended` stay as ADR-0006 and ADR-0011 have them, and **no new kind is named**. If the chosen list lives in a document, this task may create it with exactly the two existing kinds only if it stays within 5 files (add it to `## Result`); otherwise the record names its place and the creation is a follow-up. If the executor finds that no sound answer is possible without changing existing lines or naming a kind, stop and return BLOCKED (reason: data-plane schema change, CLAUDE.md A-13) instead of writing the record.
6. **Kept out of the record** and said so in Boundaries: every event kind and payload not yet named (OD-17 `intent`/`result` events and idempotency keys, OD-23, OD-10); OD-11 (two definitions in one file, read guarantees, migration — its proposals stay unconfirmed, as ADR-0024, ADR-0051 and ADR-0097 left them); sub-question ⑨ (time form of other files); ㉟ (가)/(나); `artifacts.json` `type` vocabulary (sub-question ⑥ — the record may note the parallel but does not answer it).
7. `ARCHITECTURE/OpenDecisionProposals.md`, OD-8 section, edited by the header's **기록 규칙** (line 8) and nothing else: one adopted line for ADR-0098 added after the ADR-0097 line, in the form the rule gives; the ⑧ status at the end of its text and the bullet's head status word rewritten in place to say what ADR-0098 answered and what (if anything) still stands open in ⑧ and ⑨. Nothing of the record is restated; no dated paragraph is added. A new sub-question, if registered, is added under OD-8 in the same form as the existing ones (next free number, ㊱).
8. `ARCHITECTURE/Requirements.md`, OD-8 row only, edited by **행 형식** (line 84): one ADR link with a few words after `**확정분**:`, the `**잔여**:` text rewritten in place for what remains of the event kinds, and the status date range updated if the row carries one. The status cell keeps `확정`. No other row changes unless the record answers part of that row's question (then the same rule applies).
9. `ARCHITECTURE/StandardScenarios.md`: coverage re-checked under its 검사 규칙 for the scenarios that cite OD-8, `events.ndjson`, NFR-7 or FR-13; the "최근 재검사" line is rewritten in place as the first paragraph of §검사 결과 prescribes (date, trigger ADR-0098 / T-0292, result); a history entry is added only if a verdict changes or a gap is found or closed.
10. Document mode (CLAUDE.md A-13): branch `claude/T-0292-adr-od8-event-kind-vocabulary`, reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) to Approve, rebase on `origin/main`, push to main directly (squash the branch to one commit before the push), commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0292`. No `git push --force*`.
11. After landing, the owner is notified on issue #5 (DRIVER §9), English, ending with the line `— posted by driver`; the comment URL goes into `## Result`.
12. `## Result` records: the answer in a few lines, what was left open, review rounds and any unapplied findings, the #5 notice URL, follow-ups (the code task of criterion 4 if any). No `claude` process is started (D16); no code, test, compiler or container is run.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI or settings files; the code follow-up of criterion 4.
- Editing earlier ADRs (ADR-0006, ADR-0011, ADR-0097 and others are not edited; places that become less exact are listed in Consequences).
- Defining any event kind or payload; OD-11's read and migration policy; OD-17's proposals; sub-questions ⑥, ⑦, ⑨ and ㉟ of OD-8.
- Blocked tasks and their sub-questions (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- (code, only if ADR-0098 puts the list in code or asks for a check) Apply it with tests in a separate code task, editing only the existing tests the record names.
- (doc, only if the list lives in a document that this task could not create within its size cap) Create that list with the two existing kinds.
- Record any sub-question the record registers in `## Result`.

## Result

- DONE. Landed on main as 9750cc8 (document mode, one squashed commit; `Reviewed-by: reviewer agent (2 rounds, Approve)`, `Task: T-0292`). Files: ADR-0098, new `ARCHITECTURE/EventKinds.md` (exactly `step_started` and `step_ended`, both `defined`, ADR-0011 decision 3; within the 5-file cap), Requirements OD-8 row, OpenDecisionProposals OD-8 (adopted line, ⑧ status now 답함), StandardScenarios "최근 재검사" (no verdict change, no gap).
- Answer: the vocabulary of `kind` is the set of kinds whose defining record is accepted; one index `ARCHITECTURE/EventKinds.md` lists every taken name with its defining record and state (`defined` / `not written` / `reverted`), rows never removed; a defining record adds its row in its landing commit; nothing checks a line's `kind` against the list (ADR-0006 decision 3 kept). No code changes. With ADR-0097, ⑧ is answered.
- Left open: ⑨, ㉟, every kind not yet named (OD-17, OD-23, OD-10), OD-11 (including what a reader does with lines of a reverted kind), ⑥. No sub-question registered.
- Review: round 1 Request changes (blocking: reverted-kind reading was both decided and left to OD-11 — now OD-11 only; nits applied). Round 2 Approve. Unapplied: round-2 nit (ADR-0034's rejected-alternative `"kind": "person"` not listed among other `kind` vocabularies; not a vocabulary, list not claimed complete).
- #5 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6245667137
- Follow-ups: (doc) add `ARCHITECTURE/EventKinds.md` to the ARCHITECTURE document table of `README.md` (line 46) — reviewer round 1 finding 2, out of the 5-file cap. No code follow-up.
