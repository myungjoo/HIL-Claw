---
id: T-0306
title: Write ADR-0105 on the vocabulary of `type` in `artifacts.json` and on how a changed meaning of a `type` value is told apart — the vocabulary part of OD-8 sub-question ⑥; names no value; no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, C-3, FR-13, NFR-2, "#5 A-2", "#5 D6"]
dependsOn: [T-0292, T-0300, T-0301]
touchesFiles: [ARCHITECTURE/decisions/ADR-0105-od8-blob-type-vocabulary.md, ARCHITECTURE/BlobTypes.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 170, files: 5}
hq: []   # design-level OD (DRIVER §9; the driver may close it with an ADR). Not owner-only as scoped here: the record sets the rule for the vocabulary of `type` and names no value; which binaries become blobs stays with OD-23 (design-level, 논의중, not owner-only) and criterion 3 turns the task BLOCKED if the vocabulary cannot be answered without it. Independent of every open HQ: HQ-0021..HQ-0029 concern run-tool end-line kinds, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019, HQ-0030 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 (runtime STATE / instance / events schemas, "OD-8 종결 필요(§9 ADR 경로)") is still open. OD-8 sub-question ⑥, registered by ADR-0005, is still 미결:

> ⑥ `type`의 어휘 — 형식(*name*)만 정해졌고 값 목록이 없어 두 도구가 같은 종류를 다른 이름으로 적을 수 있다. 어떤 바이너리가 blob이 되는지와 함께 정한다(OD-23).

ADR-0005 decision 5 fixed the form of `type` (a *name*) and no list. A reader treats an unknown value as an unknown kind (decision 5), and a new value of `type` does not raise `schema_version` (decision 9). So nothing today stops two tools from writing the same kind under two names, or one name from changing its meaning. For `kind` in `events.ndjson`, ADR-0097 and ADR-0098 settled the same question: a vocabulary of names that accepted records define, a name never reused, and one index file. ADR-0098 decision 6 explains why that could be answered without OD-23. ADR-0101 (`step` values) and ADR-0102 (`spend` axes) did the same for their names. `hilclaw/artifacts.add_record` takes `type` from its caller, and no module of `hilclaw/` calls it with a value today. So this record can set the rule that every later definition of a `type` value follows, without naming any value. Which binaries the tools produce, and so which values exist, stays with OD-23. This task writes one design record (DRIVER §9) that answers the vocabulary part of ⑥ and leaves the rest of ⑥ open. It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer, size limit), §9 (lines 141-149; OD closing authority: ADR + reviewer Approve + #5 notice with the driver tail of §8).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` lines 80-86 (정본 규칙, and the **행 형식** at line 84, which is the only rule for editing a register row), line 99 (OD-8 row), line 111 (OD-20 row), line 114 (OD-23 row), line 119 (OD-28 row). Find the C-3 constraint with a search for `C-3`.
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; the **기록 규칙** at line 8 is the only rule for edits to this file), line 120 (the ADR-0102 adopted line; the new adopted line goes after it), line 123 (the ⑥/⑦ bullet: rewrite its tail status and head status word in place), and the OD-23 section (from line 367). Read OD-23 only to see what it leaves open, so that the record decides none of it by accident.
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-172 (§검사 결과; its first paragraph, line 170, is the recording rule for the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md` (whole, 160 lines): especially decision 3 (member table), decision 5 (`type`), decision 6 (identity: the first `type` given is kept), decision 7 (allowed changes: `type` never changes), decision 9 (versioning), Limits, Alternatives 5 and 6, Boundaries.
- `ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md` (whole, 99 lines; decision 6 is the precedent for answering a vocabulary without the OD that names values), `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` (decision 2, never-reused name), `ARCHITECTURE/decisions/ADR-0102-od8-spend-axis-change.md` (whole, 106 lines; decisions 3, 4, 6, 7). These are the sibling answers, and their Status bullets are the model for this record's Status. Weigh, without copying, how they handle "what counts as a change", the never-reused name and the index.
- `ARCHITECTURE/EventKinds.md` (12 lines) and `ARCHITECTURE/SpendAxes.md` (10 lines): the shape of the existing indexes, if the record decides on one.
- `hilclaw/artifacts.py` lines 83-200 (`validate`, `add_record`; the `type` member check near line 94). Also search `hilclaw/` for callers of `add_record`. Read them as files to make observations at a named commit. Run nothing.
- Search `ARCHITECTURE/decisions/` for `artifacts.json` and for a stated `type` value, so that the observation of decision 1 ("which values accepted records define today") is complete.

## Acceptance Criteria

1. Before writing, check that no `ADR-0105-*` exists. If the number is taken, use the next free number consistently in every file and record the actual touchesFiles in `## Result`. Create `ARCHITECTURE/decisions/ADR-0105-od8-blob-type-vocabulary.md` in the record format of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References. Status states:
   - acceptance under DRIVER §9;
   - the three kinds of content: owner sentences quoted word for word (or a statement that no owner sentence speaks of this; C-3 / #5 A-2 give only "type" as a field), cited content with its source, and the record's own design;
   - the 7-day objection window from the #5 notice;
   - that it is a record and not code: observations are read from files at a named commit, and nothing is run.
2. The record answers the vocabulary part of ⑥ with a rule that every later definition of a `type` value follows. The rule says:
   - what the vocabulary of `type` is, and which values it holds today (an observation; the expected answer is none, but the search of Required Reading decides);
   - what a defining record of a `type` value must state (at least what content the value names), and how a changed meaning of a value is told apart: whether a value's meaning may change, and whether a name is ever reused, also after its record is reverted;
   - how two tools are kept from writing the same kind under two names, as far as a rule on records can do that;
   - whether and where the values are listed. If a list is decided, create it in this task as `ARCHITECTURE/BlobTypes.md` in the shape of `EventKinds.md` / `SpendAxes.md`, with only the rows of values that accepted records define. Linking it from the README is a follow-up;
   - what a reader and `hilclaw/artifacts.validate` do with a value outside the vocabulary. ADR-0005 decision 5 is kept unless the record gives a reason, and any code change is a follow-up.

   Alternatives considered weighs at least: a vocabulary of names defined by accepted records with one index; a closed list fixed now (ADR-0005 Alternative 5); a value check in code; and leaving `type` open until OD-23. Each one gets a reason it was taken or rejected.
3. The record names **no** value of `type`. It does not decide which binaries the tools produce or which of them become blobs (OD-23), whether records name candidates or attempts (⑦), baseline blobs (OD-28), or anything of GC (C-3 follow-up). If the executor finds that the vocabulary part cannot be answered without one of these, stop without landing anything and return BLOCKED with the question (DRIVER §8). Do not narrow the answer until it no longer answers the question. The record says why the vocabulary part is answered before OD-23, weighing ADR-0098 decision 6 without copying it.
4. Every observation of code (for example, that no module calls `add_record` and that `validate` checks the *name* form only) names the file and the commit it was read at. No code, test or schema file is changed. `schema_version` of `artifacts.json` is not raised (ADR-0005 decision 9).
5. `ARCHITECTURE/Requirements.md`, OD-8 row only: follow the 행 형식 at line 84. Add one link to the new ADR after `**확정분**:`, with a topic of a few words. Rewrite `**잔여**:` in place so that it still lists the open rest of ⑥ (which values exist, with OD-23) and keeps every other open part. Change the status cell only if the 행 형식 asks for it. Do not restate the record and do not add dated text. No other row changes, unless the record changes that OD's status, which it should not.
6. `ARCHITECTURE/OpenDecisionProposals.md`, OD-8 section only: follow the 기록 규칙 at line 8. Add one `- **채택분** [ADR-0105](…) — … (부분 답: 하위 질문 ⑥)` line after the ADR-0102 line. In the ⑥/⑦ bullet, keep the question text, append the tail status in the `→ 부분 답: [ADR]…. 남음: …` form for ⑥ (⑦ stays 미결), and change the head status word to 일부 답함. If the record raises a new sub-question, add it as a new bullet with the next free number (㊲) and status 미결. Write nothing else, and no dated paragraphs.
7. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the 검사 규칙 for the scenarios that cite OD-8, C-3 or the blob store (artifacts, reproduce, audit). Update the "최근 재검사" line in place according to the first paragraph of §검사 결과. Add an entry to "판정 변화 이력" only if a judgement changed or a gap appeared or closed. Change judgement-table notes only if an open OD reference changed.
8. Run the review cycle of dev-item-address steps 10-12 with a context-isolated reviewer until Approve, at most 7 rounds. Then land in document mode per CLAUDE.md "브랜치·merge 절차": branch `claude/T-0306-<slug>`, rebase on `origin/main`, push to main without force. The commit's last paragraph holds the `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0306` trailers, together with the attribution line (no blank line between them). Report the commit hash so that the driver can post the §9 OD notice on #5.
9. No real `claude` is started and nothing that only the runtime has is required (D16).

## Out of Scope

- Naming or defining any value of `type`, and deciding which binaries become blobs (OD-23).
- OD-8 sub-question ⑦ (records naming candidates or attempts), baseline blobs (OD-28), and GC design.
- Linking `ARCHITECTURE/BlobTypes.md` from the README. That is a follow-up if the index is created.
- Code changes in `hilclaw/` (for example, a check of `type` against the index). Any such change becomes a follow-up.
- Any edit to ADR-0005, ADR-0097, ADR-0098, ADR-0101 or ADR-0102, to `EventKinds.md`, `StepValues.md` or `SpendAxes.md`, and the optional link column or row-transition sentence of those indexes. If one of them is now less exact, list it as a follow-up in `## Result`.

## Follow-ups

- (filled by the executor)

## Result
