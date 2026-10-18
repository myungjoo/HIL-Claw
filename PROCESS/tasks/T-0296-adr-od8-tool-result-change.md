---
id: T-0296
title: Write ADR-0100 on how a change in the members of a tool's `result` object, carried by a `step_ended` line, is told apart and what the repeated call finds across it — OD-8 sub-question ㉟ (가); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, OD-18, FR-13, NFR-2, NFR-7, "#5 D6"]
dependsOn: [T-0291, T-0292]
touchesFiles: [ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 170, files: 4}
hq: []   # design-level OD (DRIVER §9; driver may close with an ADR). Not owner-only: not a #5 A/B item, C-6, OD-25 or OD-3; part (나) of ㉟, which names #5 A-8 (budget axes), is kept out. Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 sub-questions 18/19, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

PLAN P1-8 (runtime STATE / instance / events schemas, "OD-8 종결 필요(§9 ADR 경로)") is still open. ADR-0097 (T-0291) decided that a changed `data` of an event kind is a new kind, but that a change in the members of the `result` object carried by `step_ended` is **not** a change of `step_ended` (ADR-0097 decision 4): how such a change is told apart is the tool contract's, and it registered this as OD-8 sub-question ㉟ (가):

> (가) `step_ended` 줄이 싣는 도구의 `result` 객체의 멤버가 바뀌었을 때 옛 결과와 새 결과를 어떻게 구분하는지 — 새 `step` 값인지, 결과 안의 멤버인지, 다른 방법인지 — 와, 그런 변경을 건너서 ADR-0011의 반복 호출이 무엇을 찾는지(도구의 계약이 정한다; OD-18·OD-11과 함께).

Three tool contracts already close their result member lists (`correctness.check`, ADR-0042; `sim.run`/`board.run`, ADR-0063) and fix their `step` values (ADR-0040, ADR-0062), and ADR-0042 decision 7 rejected a version member inside a result. A repeated call "returns what the end line holds" (ADR-0011 decision 3), so a result stored under one member list can be returned to a caller of a later list. This task writes one design record (DRIVER §9) that answers ㉟ (가) as a rule shared by every tool contract (the frame of ADR-0015). It writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72; executor procedure, resume rule, time limit), §5 (lines 86-115; task format, naming convention, `Task:` trailer, size limit), §9 (lines 141-149; OD closing authority: ADR + reviewer Approve + #5 notice with the driver tail of §8).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md` lines 80-86 (정본 규칙 and **행 형식** at line 84 — the rule for editing a register row), line 99 (OD-8 row), line 102 (OD-11 row), line 109 (OD-18 row); the NFR-2 and NFR-7 rows (grep `NFR-2`, `NFR-7`).
- `ARCHITECTURE/OpenDecisionProposals.md` lines 1-10 (header; the **기록 규칙** at line 8 — the rule for adopted lines and in-place status rewrites), lines 87-115 (OD-8 adopted lines, to place the new one after the ADR-0099 line), line 142 (the ㉟ bullet, whose tail status and head status word are rewritten in place), lines 167-175 (OD-11 proposals: the P1 pin and resumption across versions).
- `ARCHITECTURE/StandardScenarios.md` lines 13-29 (검사 규칙) and lines 168-173 (§검사 결과: its first paragraph is the recording rule, then the "최근 재검사" line).
- `ARCHITECTURE/decisions/ADR-0097-od8-event-payload-change.md` (whole, 93 lines; decision 4 and Boundaries in particular).
- `ARCHITECTURE/decisions/ADR-0098-od8-event-kind-vocabulary.md` lines 1-12 (Status bullets as a model: §9 acceptance, three kinds of content, observations at a named commit, objection window).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` lines 26-70 (decisions 1, 3 and 4: identity = envelope numbers + `step` + `execution`; the repeated call; what a resumed turn may conclude).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` decisions 5 and 8 (grep `### 5.` and `### 8.`; append only, versioning).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` lines 114-120 (decision 7: no version member; "in P1 that commit is the pin"; OD-11 owns commit checks).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` lines 67-92 (decision 4: `step` is the contract's, not a request member, two tools never share a value; decision 5) and line 152 (Boundaries: each tool's `step` value and result members).
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md` lines 50-60 (decision 3: `correctness_check_sim` / `correctness_check_board`; how they were formed).
- `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md` lines 117-121 (the closed list; "Only a record adds a member"; "What a caller may rely on"; "A result carries no version member" and what follows).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md` lines 53-60 (decision 3: `sim_run_timing` / `board_run_timing`) and `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` (grep `closed` / `version`; its list rule).
- `ARCHITECTURE/decisions/ADR-0022-od8-instance-record-source-commit.md` (skim: `source_commit` in `instance.json`).
- `hilclaw/journal.py` (`_ENDED`, `_checked`, module docstring: `result` "is a `dict`; its members are not looked at") and `hilclaw/journaled_tool.py` / `hilclaw/hw_tool.py` (where `step` is fixed per tool and the lookup returns a stored result) — read as files for observations; run nothing.

## Acceptance Criteria

1. A new file `ARCHITECTURE/decisions/ADR-0100-od8-tool-result-change.md` (verify first that no `ADR-0100-*` exists; if taken, use the next free number consistently in every file) in the Record format of ADR-0001: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References. Status states acceptance under DRIVER §9, the three kinds of content (owner sentences quoted word for word, or that none speaks of this; cited content with its source; the record's own design), the 7-day objection window from the #5 notice, and that it is a record, not code (observations read from files at a named commit; nothing run).
2. The Decision answers ㉟ (가) as a rule for every tool contract whose results are carried by `step_ended`: **how a result made under a changed member list is told apart from one made under the earlier list** (for example a new `step` value per change, a member inside the result, the source commit of `instance.json`, or another means — with the reason), **what counts as a change of a result's members** (state whether it mirrors ADR-0097 decision 3 — addition, removal, rename, type/form/meaning change — or differs, and why), and **what the repeated call of ADR-0011 decision 3 finds across such a change** (which state an identity under the earlier list presents to a call under the later one, and what the call returns). It must be consistent with ADR-0042 decision 7 (no version member in a result) or say explicitly, with reason, why that decision is not reopened; and with ADR-0015 decision 4 (`step` is fixed by the contract, never shared by two tools).
3. Alternatives considered weighs at least: (a) a new `step` value for every change of a contract's result members; (b) a member inside the result that marks its list (against ADR-0042 decision 7); (c) relying on the P1 pin (`source_commit`, ADR-0010 decision 7, ADR-0022) and leaving results unmarked; (d) a new event kind per change (rejected by ADR-0097 decision 4 — cite, do not re-weigh at length); (e) leaving ㉟ (가) open. Each with its reason, including what each means for a step whose identity was ended under the earlier list and is called again under the later one (NFR-7 ① round-boundary replacement of the tool layer; resumption, FR-6).
4. **No contract, value or member that exists today changes**: the `step` values `correctness_check_sim`, `correctness_check_board`, `sim_run_timing`, `board_run_timing` and the closed result lists of ADR-0042 and ADR-0063 stay as they are; no member of `data`, the envelope, `instance.json` or any other data-plane file is added, removed or renamed; no `schema_version` changes; no new event kind. The rule applies to a later change. If the executor finds that no sound answer is possible without such a change, stop and return BLOCKED (reason: data-plane schema change, CLAUDE.md A-13) instead of writing the record.
5. Observations (binding nothing) cite `hilclaw/journal.py` and `hilclaw/journaled_tool.py` / `hilclaw/hw_tool.py` as read at a named commit: the journal does not look at the members of `result`; each tool function fixes its `step`; a lookup that finds an ended identity returns the stored result unchanged. Consequences says what the answer means for code: either "no code changes", or exactly one code follow-up named there (nothing written here). It also lists the earlier records that become less exact (for example ADR-0042 decision 7's "how a reader treats a result of another list is the open question just cited", ADR-0097 decision 4's "not decided here", ADR-0063's corresponding sentence) without editing them.
6. **Kept out of the record** and said so in Boundaries: ㉟ (나) (the axes of `spend`, with FR-3, OD-19, #5 A-8 — owner-related; not answered here); OD-11 beyond what the rule needs (read guarantees, migration, whether a run may pass from one source commit to another, what a reader does with an older result); recovery of an open step and retry (OD-10, the rest of OD-17); the members of any tool's result; any new tool, `step` value or kind; `profiler.collect` (HQ-0025); OD-18 sub-questions held by blocked tasks (T-0210, T-0239, T-0264).
7. `ARCHITECTURE/OpenDecisionProposals.md`, edited by the header's **기록 규칙** (line 8) and nothing else: one adopted line for ADR-0100 in the OD-8 section after the ADR-0099 line, in the form the rule gives; the ㉟ status at the end of the line-142 bullet and that bullet's head status word rewritten in place (for example `일부 답함`, with (가) answered and (나) still open). If the record also answers part of an OD-18 sub-question, apply the same rule in the OD-18 section. Nothing of the record is restated; no dated paragraph is added. A new sub-question, if registered, is added under OD-8 in the same form as the existing ones (next free number, ㊱).
8. `ARCHITECTURE/Requirements.md`, edited by **행 형식** (line 84): in the OD-8 row, one ADR link with a few words after `**확정분**:` (after the ADR-0099 link), the `**잔여**:` text rewritten in place only where it names what this record answers, and the status date range updated if needed; the status cell keeps `확정`. The OD-18 or OD-11 row changes only if the record answers part of that row's question (then the same rule applies). No other row changes.
9. `ARCHITECTURE/StandardScenarios.md`: coverage re-checked under its 검사 규칙 for the scenarios that cite OD-8, OD-18, OD-11, `events.ndjson`, NFR-2, NFR-7 or FR-6 (S3, S5, S9, S10 at least); the "최근 재검사" line is rewritten in place as the first paragraph of §검사 결과 prescribes (date, trigger ADR-0100 / T-0296, result); a history entry is added only if a verdict changes or a gap is found or closed.
10. Document mode (CLAUDE.md A-13): branch `claude/T-0296-adr-od8-tool-result-change`, reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) to Approve, rebase on `origin/main`, squash the branch to one commit, push to main directly; the commit message ends with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0296`. No `git push --force*`.
11. After landing, the owner is notified on issue #5 (DRIVER §9), English, ending with the line `— posted by driver`; the comment URL goes into `## Result`.
12. `## Result` records: the answer in a few lines, what was left open, review rounds and any unapplied findings, the #5 notice URL, follow-ups (the code task of criterion 5, if any). No `claude` process is started (D16); no code, test, compiler or container is run.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `pyproject.toml` or settings files; the code follow-up of criterion 5.
- Editing earlier ADRs (ADR-0006, ADR-0010, ADR-0011, ADR-0015, ADR-0040, ADR-0042, ADR-0062, ADR-0063, ADR-0097 and others are not edited; places that become less exact are listed in Consequences).
- ㉟ (나), OD-11 policy, OD-10, the rest of OD-17; OD-8 sub-questions ⑥ and ⑦; `README.md`, `ARCHITECTURE/EventKinds.md` (no kind is added).
- Open PR #179 files and blocked tasks and their sub-questions (T-0121, T-0149, T-0153, T-0155, T-0156, T-0169, T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- (code, only if ADR-0100 names one) the code follow-up in Consequences, as a separate code task.
- Record any sub-question the record registers in `## Result`.

## Result
