---
id: T-0294
title: Write ADR-0099 on the time form of moments in data-plane files other than `events.ndjson` (`gc_at` of `artifacts.json`, `STATE.json`, `instance.json`) — OD-8 sub-question ⑨; no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, FR-13, NFR-2, C-3, "#5 D6"]
dependsOn: [T-0292]
touchesFiles: [ARCHITECTURE/decisions/ADR-0099-od8-moment-form-of-other-files.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 170, files: 4}
hq: []   # design-level OD (DRIVER §9, driver may close with an ADR); not owner-only (not #5 A/B, C-6, OD-25, OD-3) — the owner fixed that `gc_at` exists and what it means (C-3, #5 A-2), not its time form, which ADR-0005 left to a later record. Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 / OD-30 / OD-8 instance-start checks, clang_build, local_run, the build log and json helpers; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 (runtime STATE / instance / events schemas, "OD-8 종결 필요(§9 ADR 경로)") is still open. With ADR-0097 and ADR-0098 (T-0291, T-0292), OD-8 sub-question ⑧ is answered; the next sub-question in the same bullet, ⑨, is still `미결`:

> ⑨ 다른 파일의 시각 표기 — ADR-0006은 `time`의 표기를 이 파일에 한해 정했다. `artifacts.json`의 `gc_at`(ADR-0005가 미정으로 둠)과 `STATE.json`·`instance.json`의 시각이 같은 표기를 쓸지는 그 스키마들(PLAN P1-8)과 GC 설계에서 정한다.

ADR-0006 decision 3 fixed the form `YYYY-MM-DDThh:mm:ssZ` "for this file only". ADR-0005 decision 3 typed `gc_at` as a *string* and left its time form open, reserving that a later record may fix it without raising `schema_version`. Today no other file of the data plane holds a moment (ADR-0033 Context), and no MVP tool writes `gc_at`. This task writes one design record (DRIVER §9) that answers ⑨: whether moments in other data-plane files take ADR-0006's form, and what that means for `gc_at`. It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer), §9 (lines 141-149; OD closing authority, ADR + reviewer Approve + #5 notice with the driver tail).
- `CLAUDE.md` "상시 규칙", in particular "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` lines 80-86 (정본 규칙 and **행 형식** at line 84 — the rule for editing a register row) and line 99 (OD-8 row); the C-3 constraint sentence (grep `C-3`).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; the **기록 규칙** at line 8 — the rule for adopted lines and in-place status rewrites), lines 87-153 (OD-8; ⑨ is in the "하위 질문(ADR-0006이 넘긴 것 …)" bullet at line 120, whose tail and head status word are rewritten in place).
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-173 (§검사 결과: its first paragraph is the recording rule, then the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` lines 36-60 (decision 3, the `time` member and its form; "for this file only") and lines 110-120 (rejected alternatives for `time`).
- `ARCHITECTURE/decisions/ADR-0005-od8-artifacts-record.md` lines 40-50 (decision 3, `gc_at`), lines 70-90 (allowed changes, version rule — "not raised … by a later record that fixes the time form of `gc_at`"), lines 105-112 (example with `TIME-FORM-NOT-DECIDED-HERE`), line 124 (rejected: fixing the form then), lines 140-150 (Boundaries: GC).
- `ARCHITECTURE/decisions/ADR-0033-od8-instance-record-wall-clock-budget.md` lines 15-25 (moments vs amounts; no file holds a start time) and line 54 (duration notation rejected).
- `ARCHITECTURE/decisions/ADR-0027-od8-run-id-form.md` lines 40-50 (the time part of a `run_id` — ISO 8601 basic form, lower case; a name, not a member).
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md` (skim the member table: no moment member) and `ARCHITECTURE/decisions/ADR-0018-od8-instance-record-hw-profile.md` (skim: the file frame; no moment member).
- `ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md` (a recent record, for the Status bullets: §9 acceptance, three kinds of content, objection window, observations at a named commit).
- `hilclaw/events.py` lines 55-80 and 150-160 (the `_TIME` check and the writer's clock reading) and `hilclaw/artifacts.py` lines 20-125 and 185-250 (`gc_at` checked as an ADR-0001 *string* only; never written) — read as files for the record's observations; run nothing.

## Acceptance Criteria

1. A new file `ARCHITECTURE/decisions/ADR-0099-od8-moment-form-of-other-files.md` (verify first that no `ADR-0099-*` exists; if the number is taken, use the next free one consistently in every file) in the Record format of ADR-0001, with Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here) and References. Status states acceptance under DRIVER §9, the three kinds of content (owner sentences quoted word for word — or that none speaks of this —, cited content with its source, the record's own design), the 7-day objection window from the #5 notice, and that it is a record, not code (observations read from files at a named commit; nothing run).
2. The Decision answers ⑨: **whether a member of another data-plane file that records a moment takes the form of ADR-0006 decision 3** (one form for the data plane, or a form per file, or no rule until a member exists — with the reason), **what the answer means for `gc_at`** (its form within ADR-0005's *string* is fixed here, or stays with the GC design with a stated reason), and **what the answer says about `STATE.json` and `instance.json`**, which today hold no moment member. It must state that the time part of a `run_id` (ADR-0027) is a name, not a moment member, and is not changed; and that amounts (durations, ADR-0033) are not moments and are not covered.
3. Alternatives considered weighs at least: (a) ADR-0006's form for every moment member of the data plane, `gc_at` included; (b) the same rule but `gc_at` left to the GC design; (c) a form chosen per file when its first moment member is defined; (d) another form (for example with fractions or an offset, or a number) for files that are not logs; (e) leaving ⑨ open. Each with its reason.
4. Observations (binding nothing) cite `hilclaw/events.py` and `hilclaw/artifacts.py` as read at a named commit: `events.py` checks and writes exactly ADR-0006's form; `artifacts.py` checks a present `gc_at` only as an ADR-0001 *string* and never writes it; no other module of `hilclaw/` writes a moment into a data-plane file (re-confirm by grep). Consequences says what the answer means for these modules: either "no code changes", or exactly one code follow-up task named there (for example narrowing the `gc_at` check in `hilclaw/artifacts.py`; nothing written here). A narrower `gc_at` check, if chosen, must be a follow-up.
5. **No member, type, value or version that exists today changes**: `schema_version` of `artifacts.json`, `events.ndjson`, `STATE.json` and `instance.json` stays as it is; no member is added, removed or renamed; the `gc_at` type stays *string*; filling in its time form is allowed only because ADR-0005 reserved it without a version raise (cite that sentence). If the executor finds that no sound answer is possible without such a change, stop and return BLOCKED (reason: data-plane schema change, CLAUDE.md A-13) instead of writing the record.
6. **Kept out of the record** and said so in Boundaries: the GC itself (tool, when it runs, grace period, run end, a `gc_at` after content is stored again, a hash with several classes — C-3, #5 A-2; owner decisions stand as they are), retention classes, data governance (OD-25, owner-only); any new moment member of any file (for example a start time of an instance — ADR-0033 and ㉚ stay as they are); clocks and their correctness (㉚ (가)); sub-questions ⑥, ⑦ and ㉟ of OD-8.
7. `ARCHITECTURE/OpenDecisionProposals.md`, OD-8 section, edited by the header's **기록 규칙** (line 8) and nothing else: one adopted line for ADR-0099 added after the ADR-0098 line, in the form the rule gives; the ⑨ status at the end of the line-120 bullet and that bullet's head status word rewritten in place for what ADR-0099 answered and what (if anything) still stands open. Nothing of the record is restated; no dated paragraph is added. A new sub-question, if registered, is added under OD-8 in the same form as the existing ones (next free number, ㊱).
8. `ARCHITECTURE/Requirements.md`, OD-8 row only, edited by **행 형식** (line 84): one ADR link with a few words after `**확정분**:` (after the ADR-0098 link), the `**잔여**:` text rewritten in place only where it names what this record answers, and the status date range updated if needed. The status cell keeps `확정`. No other row changes unless the record answers part of that row's question (then the same rule applies; C-3's sentence is not edited — a more precise wording, if any, goes into Consequences).
9. `ARCHITECTURE/StandardScenarios.md`: coverage re-checked under its 검사 규칙 for the scenarios that cite OD-8, `artifacts.json`, `events.ndjson`, C-3, NFR-2 or FR-13; the "최근 재검사" line is rewritten in place as the first paragraph of §검사 결과 prescribes (date, trigger ADR-0099 / T-0294, result); a history entry is added only if a verdict changes or a gap is found or closed.
10. Document mode (CLAUDE.md A-13): branch `claude/T-0294-adr-od8-moment-form-of-other-files`, reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) to Approve, rebase on `origin/main`, push to main directly (squash the branch to one commit before the push), commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0294`. No `git push --force*`.
11. After landing, the owner is notified on issue #5 (DRIVER §9), English, ending with the line `— posted by driver`; the comment URL goes into `## Result`.
12. `## Result` records: the answer in a few lines, what was left open, review rounds and any unapplied findings, the #5 notice URL, follow-ups (the code task of criterion 4 if any). No `claude` process is started (D16); no code, test, compiler or container is run.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI or settings files; the code follow-up of criterion 4.
- Editing earlier ADRs (ADR-0005, ADR-0006, ADR-0027, ADR-0033 and others are not edited — including ADR-0005's example value; places that become less exact are listed in Consequences).
- GC design, retention, OD-25; any new member of any file; OD-8 sub-questions ⑥, ⑦, ㉚, ㉟.
- Blocked tasks and their sub-questions (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- (code, only if ADR-0099 fixes the form of `gc_at`) Narrow the `gc_at` check in `hilclaw/artifacts.py` with tests in a separate code task, editing only the existing tests the record names.
- Record any sub-question the record registers in `## Result`.

## Result
