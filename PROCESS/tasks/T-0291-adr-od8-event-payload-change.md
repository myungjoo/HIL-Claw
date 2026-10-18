---
id: T-0291
title: Write ADR-0097 on how a change in the `data` of an event kind of `events.ndjson` is told apart, given that `schema_version` covers the envelope only (the payload-change part of OD-8 sub-question ⑧); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, FR-13, NFR-7, OD-11, OD-17]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 180, files: 4}
hq: []   # design-level OD (DRIVER §9, driver may close with an ADR); not owner-only (not #5 A/B, C-6, OD-25, OD-3). Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 / OD-30 / OD-8 instance records, clang_build, local_run and the build log; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 (runtime STATE / instance / events schemas, "OD-8 종결 필요(§9 ADR 경로)") is still open. ADR-0006 fixed the envelope of a line of `runs/<run_id>/events.ndjson` and, in its decision 8, said that `schema_version` covers the envelope only: it "is **not** raised by a new value of `kind`, nor by a change in the `data` of a kind; how such a change is told apart is left open". ADR-0011 named the only two kinds that exist (`step_started`, `step_ended`, with exact `data` members) and again left "how a later change in the `data` of these two is told apart" to OD-8 sub-question ⑧. The question has stood unanswered since 2026-10-07, while every later tool contract that puts a `result` into a `step_ended` line adds to the payloads a log will hold for the whole life of a run.

This task writes one design record (DRIVER §9) that answers the payload-change part of sub-question ⑧: when the `data` of an existing kind changes, how a line written under the old payload is told apart from one written under the new one. It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer), §9 (lines 141-149; OD closing authority, ADR + reviewer Approve + #5 notice with the driver tail).
- `CLAUDE.md` "상시 규칙" (lines 12-21), in particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` lines 80-86 (정본 규칙, **행 형식**), line 99 (OD-8 row), line 102 (OD-11 row), line 108 (OD-17 row).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header, **기록 규칙**), lines 87-151 (OD-8; sub-question ⑧ and ⑨ are in the bullet at line 118), lines 163-170 (OD-11), lines 240-248 (OD-17).
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-172 (§검사 결과: its first paragraph is the recording rule, then the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` (whole file, 159 lines; decisions 3, 8 and Boundaries are the base of this record).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` lines 42-60 (decision 3: the two kinds, their exact `data` members, `result` as the call's own result object) and lines 165-183 (Boundaries, References).
- `ARCHITECTURE/decisions/ADR-0024-od8-instance-record-layout-version.md` and `ARCHITECTURE/decisions/ADR-0051-od6-spec-file-version-2.md` (Decision and Boundaries sections) — precedents for marking a version without deciding read guarantees or migration (OD-11).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` lines 146-153 (Record format) and `ARCHITECTURE/decisions/ADR-0096-od18-check-build-directory-removal-failure.md` (a recent record, for the Status bullets: §9 acceptance, three kinds of content, objection window).
- `hilclaw/events.py` lines 1-60 and 100-170 (the envelope check; `kind` checked against no vocabulary) and `hilclaw/journal.py` lines 1-50 and 220-260 (`_MEMBERS`: a step line whose `data` has a member outside the exact set is rejected) — read as files for the record's observations; run nothing.

## Acceptance Criteria

1. A new file `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` (verify first that no `ADR-0097-*` exists; if the number is taken, use the next free one and use it consistently) in the Record format of ADR-0001, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here) and References. Status states acceptance under DRIVER §9, the three kinds of content (owner sentences quoted word for word, cited content with its source, the record's own design), the 7-day objection window from the #5 notice, and that it is a record, not code (the observations were read from files at a named commit; nothing was run).
2. The Decision answers, for `events.ndjson`, **how a change in the `data` of an existing kind is told apart** from the payload it replaces, and states what counts as such a change. At least these options are weighed in Alternatives considered, each with its reason: a new `kind` name for the changed payload; a version marker inside `data`; raising `schema_version` (which ADR-0006 decision 8 excludes — reopening it must be argued, not assumed); and leaving the part open. The record says whether its rule distinguishes kinds of change (for example a member added, removed, renamed, or changed in type or meaning), and why.
3. The record says whether a change in the members of the `result` object a `step_ended` line carries (the call's own result object — ADR-0011 decision 3; each tool contract fixes those members) is a change in the `data` of `step_ended` under its rule, or is told apart by that tool's contract, and why. If it leaves this open, it says so with a reason and registers it.
4. Observations (binding nothing) cite `hilclaw/events.py` and `hilclaw/journal.py` as read at a named commit: `kind` is checked against no vocabulary; a step line with a `data` member outside the exact set is rejected; only `step_started` and `step_ended` exist. The record states what its rule means for these two modules as a code follow-up (one code task, named in Consequences, nothing written here), or that no code changes.
5. **No line that exists today changes**: `schema_version` stays 1, the envelope and the exact `data` members of `step_started` and `step_ended` stay as ADR-0006 and ADR-0011 have them, and no new kind is named. If the executor finds that no sound rule is possible without changing them, stop and return BLOCKED (reason: data-plane schema change, CLAUDE.md A-13) instead of writing the record.
6. **Kept out of the record** and said so in Boundaries: the vocabulary of `kind` (the first part of ⑧ — what list exists and where; unless the record answers it with no new kind and states that it does, the part stays open); whether a file may hold lines of two payload versions and what a reader does with an older line, read guarantees and migration (OD-11; the OD-11 proposals stay unconfirmed, as ADR-0024 and ADR-0051 left them); sub-question ⑨ (time form of other files); every event kind and payload not yet named (OD-17, OD-23, OD-10); `artifacts.json` `type` (sub-question ⑥).
7. `ARCHITECTURE/OpenDecisionProposals.md`, OD-8 section, edited by the header's **기록 규칙**: one `- **채택분** [ADR-0097](…) — … (답함: 하위 질문 ⑧의 …)` line added with the other adopted lines; the ⑧ text at line 118 keeps its wording and gets its status at its end rewritten in place (`→ 부분 답: [ADR-0097](…)…. 남음: …` or `→ 답함: …`), replacing the current `→ ⑧ 미결: …` tail, and the bullet's head status word is rewritten in place (미결 → 일부 답함 if ⑨ or part of ⑧ stays open). Nothing of the record is restated; no dated paragraph is added. If the record registers a new sub-question, it is added under OD-8 in the same form as the existing ones (next free number in that section).
8. `ARCHITECTURE/Requirements.md`, OD-8 row only, edited by **행 형식**: one ADR link with a few words added after `**확정분**:`, and the `**잔여**:` text rewritten in place so that "`events.ndjson`의 이벤트 종류·페이로드" says what is still open. The status cell keeps `확정` (OD-8 keeps its status word). No other row changes unless the record answers part of that row's question (then the same rules apply).
9. `ARCHITECTURE/StandardScenarios.md`: coverage re-checked under its 검사 규칙 for the scenarios that cite OD-8, `events.ndjson`, NFR-7 or FR-13; the "최근 재검사" line is rewritten in place by the first paragraph of §검사 결과 (date, trigger ADR-0097 / T-0291, result); a history entry is added only if a verdict changes or a gap is found or closed.
10. Document mode (CLAUDE.md A-13): branch `claude/T-0291-adr-od8-event-payload-change`, reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) to Approve, rebase on `origin/main`, push to main directly, commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0291`. No `git push --force*`.
11. After landing, the owner is notified on issue #5 (DRIVER §9), English, ending with the line `— posted by driver`; the comment URL goes into `## Result`.
12. `## Result` records: the answer in a few lines, what was left open, review rounds and any unapplied findings, the #5 notice URL, follow-ups (the code task of criterion 4 if any). No `claude` process is started (D16); no code, test, compiler or container is run.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI or settings files; the code follow-up of criterion 4.
- Editing earlier ADRs (ADR-0006, ADR-0011 and others are not edited; places that become less exact are listed in Consequences).
- The vocabulary of `kind` beyond what criterion 6 allows; OD-11's read and migration policy; OD-17's proposals (`intent`/`result` events, idempotency keys); sub-questions ⑥, ⑦, ⑨ of OD-8.
- Blocked tasks and their sub-questions (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- (code, only if ADR-0097 changes what `hilclaw/events.py` or `hilclaw/journal.py` must check) Apply the rule with tests, editing only the existing tests the record names.
- Record any sub-question the record registers in `## Result`.

## Result
