---
id: T-0239
title: Write the ADR that closes the rest of OD-18 sub-question 7 for `cpu_standin` - whether the backend offers `profiler.collect`, and whether the `profile` step of FR-1 on `cpu_standin` is carried by the results of the run tools - as the owner answers HQ-0025, and reflect it in the ARCHITECTURE documents
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-1, FR-10, OD-18, "#5 A-7"]
dependsOn: [T-0088]
touchesFiles: [ARCHITECTURE/decisions/, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]   # one new record under ARCHITECTURE/decisions/ with the next free number at execution time (ADR-0077 at planning time; ADR-0068 and ADR-0074 are held by the unlanded branches of T-0210 and T-0231)
estimatedSize: {loc: 180, files: 4}   # one new record of about 100-150 lines; the rest are in-place edits of a few lines each
hq: [HQ-0025]
---
## Why

PLAN P1-1 ("FR-10 도구 계약(`sim.run`/`board.run`/`profiler.collect`/`correctness.check`, `blob.push/fetch`) 인터페이스 + mock 백엔드 + 백엔드 적합성 테스트") is open. `correctness.check` has its records and is registered (ADR-0070); `sim.run` / `board.run` have ADR-0061 to ADR-0067 and wait on ADR-0068 (T-0210, HQ-0021). **`profiler.collect` has no record at all.** ADR-0016 decision 3 registered OD-18 sub-question 7 ("Which of the four the `cpu_standin` backend offers"); ADR-0038 answered it for `sim.run`, `board.run` and `correctness.check` from the owner's HQ-0005 answer and said by name: "`profiler.collect` was not asked and stays open: whether `cpu_standin` offers it is the rest of sub-question ⑦" (ADR-0038 decision 2). The register text of sub-question 7 (`ARCHITECTURE/OpenDecisionProposals.md`, OD-18 section, the paragraph starting "하위 질문(ADR-0016이 넘긴 것") ends with "남음: `cpu_standin`이 `profiler.collect`를 제공하는지, 한 지점이 없는 대상의 규칙(OD-26; StandardScenarios S1-b)".

The answer is a reading of #5 A-7 (an owner item, DRIVER §9) against FR-1 (whose loop has a `profile` step after the board point) and FR-10 (which names `profiler.collect`), as the sim / board half was (HQ-0005, T-0088). So the driver raised **HQ-0025**, and this task is **BLOCKED on HQ-0025** until the owner answers. HQ-0025, as the planner drafted it (the recorded `question` in `PROCESS/STATE.json` is authoritative):

> The rest of PLAN P1-1 needs the owner's reading of #5 A-7 for `profiler.collect` (FR-10), for the first backend `cpu_standin` only (OD-18 sub-question 7, rest). HQ-0005 settled that `cpu_standin` offers `sim.run`, `board.run` and `correctness.check`, and did not ask about `profiler.collect` (ADR-0038 decision 2: "was not asked and stays open"). [...] (1) Does `cpu_standin` offer `profiler.collect` in the MVP: (a) no - on `cpu_standin` the round's profile is what `sim.run` / `board.run` already return (the timing samples and the memory figure), and a call of `profiler.collect` there answers the reserved kind `not_offered`; (b) yes, with a profile taken from the local run by means the package already has, needing no new external dependency and the same on every machine of C-7 (name what it should hold, or leave it to the record); (c) yes, with a hardware-counter or sampling profiler (for example Linux `perf`) - a new external dependency (CLAUDE.md A-13) that is not available alike on macOS and WSL 1 (C-7); (d) something else (name it)? (2) If (1) is (a): may the record of the round loop treat the `profile` step of FR-1 on `cpu_standin` as carried out by the run tools' results, with no further step, until a target that offers `profiler.collect` exists: (a) yes; (b) no (say what the loop does)? Not asked here: [...]

When the owner answers on #5 with `HQ-0025`, the driver sets this task back to `TODO` (DRIVER §3-2). The executor then reads the recorded `decision` and the owner's comment in full and takes the answers as **fixed inputs**. If the answer leaves a point open that this record needs, or goes beyond what this file covers (for example it chooses (c) and so asks for a new external dependency, or names profile contents that need a spec version raise or a data-plane file), **do not fill the gap**: return BLOCKED with reason `requirement-unclear` (or the A-13 reason that applies) and the exact remaining question.

Why a record and not code (DRIVER §6, §9): the owner's answer decides the offer; around it there are design points no document fixes - what a call of `profiler.collect` about a `cpu_standin` run answers, what that means for the round loop's `profile` step and the spec's `feedback.attempts[].profile` place, and what stays open for the tool's contract. OD-18 is design-level, not owner-only, so the record is written under §9. This task writes the record only; it ticks **no PLAN checkbox** (P1-1 stays open).

Planner's notes (2026-10-17 UTC, `main` at `f0be8e5`, from the files; the reviewer is asked to re-check each):
- **Precedent**: T-0088 / ADR-0038 (the same sub-question, the sim / board half, resting on HQ-0005). Its decision 2 is the model for how an owner's answer about an offer is quoted, marked **owner** and kept apart from the record's own reading. Do not copy its wording; follow its manner.
- **What answer (1)(a) would mean, as facts the record may cite**: a backend offers a tool by holding an operation for it; a call of a tool the selected backend does not offer answers the reserved kind `not_offered`, consumes nothing and leaves no line (ADR-0016 decision 3). The run tools' result already holds the timing intervals (`intervals_ns`, ADR-0063 decision 4) and the memory figure (`memory_bytes`, ADR-0063 decision 6; ADR-0061 decision 5). ADR-0004 puts `profile.json` under `measure/` "collected by running the attempt's binary at an execution point (`profiler.collect`, FR-10)" and its content is OD-13 (ADR-0004 path table and the bullet on `profile.json`); ADR-0002 decision 4 has `profile` in a spec's `feedback.attempts` entry as an object whose members version 1 does not list (B4, OD-13). A record that leaves `profile.json` unwritten on `cpu_standin`, or says what goes into a spec's `profile`, touches those places: say what follows for them only as far as the answer makes it necessary, and leave the rest open by name.
- **What answers (1)(b) or (d) would leave**: the contract of `profiler.collect` (request, result members, journaled or not, `step` values, the mock's script) is the next records' and is not written here; this record states only the offer and what the owner's answer says the profile holds.
- **Home in the register**: OD-18 (sub-question 7 is registered there). No new OD number. FR-1 / FR-10 rows change only if the owner's answer is a reading of them that the row must show (as HQ-0005's answer was reflected in FR-10).
- **A-13 reading**: document mode, no code, no dependency, no schema file. If the answer requires a new external dependency or a data-plane schema change, that is a BLOCKED reason (CLAUDE.md A-13), not something this task does.

## Required Reading

- PROCESS/DRIVER.md §3-5 (executor procedure, `T-NNNN` naming, resume rule, time limit) and §5 (task format, size cap D4, commit trailers) - mandatory for every task (§6).
- PROCESS/DRIVER.md §1-5 (forbidden actions held by discipline; a denied or failed tool call is BLOCKED, never worked around), §8 (driver tail on #5 comments), **§9 (the whole section)**.
- PROCESS/STATE.json - `humanQuestions[]` entry `HQ-0025`: `question`, `issueComment` and `decision`; then the owner's reply on #5 in full (`gh issue view 5 --repo myungjoo/HIL-Claw --json comments`, every comment after the HQ-0025 mirror).
- CLAUDE.md - 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", **"세션 진입 점검"** (before the first edit: `gh pr list`, issues #4, #5, #7, #8), "개발 드라이버와 런타임의 구분" (D16), "브랜치·merge 절차" (document mode; BLOCKED reasons).
- .claude/skills/dev-item-address/SKILL.md (document mode) and .claude/skills/dev-code-review/SKILL.md ("no invented decisions" in particular).
- ARCHITECTURE/Requirements.md - rows **FR-1** (line 19) and **FR-10** (line 28), C-7; the Open Decisions preamble with the **"행 형식"** paragraph (line 84); register row **OD-18** (line 109).
- ARCHITECTURE/OpenDecisionProposals.md - the header's **"기록 규칙"** (line 8); section **OD-18** (from line 250): its adopted-record bullets, the "제안으로 남는 부분" bullet (line 258, the sentence "도구 계약이 아직 없는 것: `profiler.collect`(제공 여부는 ⑦)"), and the sub-question paragraph holding ⑥ to ⑧ (line 291).
- **ARCHITECTURE/decisions/ADR-0038-od18-cpu-standin-execution-points.md - the whole record** (Status, decision 1 terms, **decision 2**, decision 8 Limits, Consequences, Boundaries).
- ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md - decisions 2 and 3 (lines 30-56), decision 5 the mock (lines 67-75), Boundaries (from line 132).
- ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md - decisions 1, 2 and 5 (lines 32-48, 70-75), Boundaries (lines 157-170).
- ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md - decisions 4, 6, 8 and 9 (lines 66-76, 87-94, 107-144), Boundaries (from line 216).
- ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md - the path-table rows under `measure/` and `eval/` (lines 73-75) and the bullets on `profile.json` (lines 93-96).
- ARCHITECTURE/decisions/ADR-0002-od6-codegen-spec.md - decision 4 on `feedback.attempts` and `profile` (lines 68, 82) and the version rule (line 100).
- ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md - the name table (line 77, `profiler.collect`).
- ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md - the closing **"Record format"** section.
- ARCHITECTURE/StandardScenarios.md - the checking rules, the first paragraph of **§검사 결과** (line 168), and the steps of S0 (step 6), S1 (step 6) and S1-b that name the profile step.
- Issue #5 owner inputs (fixed): **A-7** `gh api repos/myungjoo/HIL-Claw/issues/comments/5944117402 --jq .body`; the HQ-0005 answer `gh api repos/myungjoo/HIL-Claw/issues/comments/6117798837 --jq .body`.
- PROCESS/tasks/T-0088-adr-od18-cpu-standin-execution-points.md `## Result` (how the record of the sim / board half landed, review findings, notice text).

## Acceptance Criteria

Fixed inputs, not re-decided:
- **The owner's HQ-0025 answer, exactly as far as it goes.** The record **records that answer and decides nothing beyond it** on the owner's side: every sentence that renders it quotes it and is marked **owner**, with the comment URL; nothing the answer did not say is attributed to the owner.
- ADR-0016, ADR-0038, ADR-0061, ADR-0063, ADR-0004, ADR-0002 as they are; FR-1 and FR-10 for every target other than `cpu_standin`; #5 A-7; the HQ-0005 answer.

The ADR:
1. Is a new file `ARCHITECTURE/decisions/ADR-NNNN-od18-cpu-standin-profiler-collect.md` with the next free number at execution time (check `ARCHITECTURE/decisions/` on `origin/main` and the branches of T-0210 and T-0231, which hold ADR-0068 and ADR-0074), in the "Record format" of ADR-0001: Status (accepted under DRIVER §9; the owner's content marked as not subject to the 7-day window; everything else the record's own), Context, Decision, Alternatives considered, Consequences, Boundaries, References.
2. **Scope**: the first backend `cpu_standin` only. Not the mock (unless the owner's answer names it), a simulator, a board or a remote path.
3. **Whether `cpu_standin` offers `profiler.collect`** - from HQ-0025 (1), quoted and marked **owner**. What follows from it is the record's own and argued: under (a), what a call answers (cited: `not_offered`, ADR-0016 decision 3); under (b) or (d), only what the owner's answer says the profile holds, with the tool's contract left to later records by name.
4. **The `profile` step of FR-1 on `cpu_standin`** - from HQ-0025 (2) when asked and answered; if (1) was not (a), say whether the question arises and leave it open by name if the answer does not settle it. State only as far as the answer makes it necessary what follows for `profile.json` (ADR-0004) and for a spec's `feedback.attempts[].profile` (ADR-0002 decision 4); anything further is listed under Boundaries.
5. **Alternatives considered**: the options of HQ-0025 not chosen, with the owner's choice as the reason, and any design alternative of the record's own with one or two lines of reason each.
6. **Boundaries** name at least: the contract of `profiler.collect` (request, result, journaled or not, `step` values, the mock's script), the profile of any other backend, the rule for a target that lacks a point (OD-26), the structure of a profile summary (B4, OD-13), and the round loop's procedure (PLAN P2-1).
7. **A-13 reading** in the record: document mode; no code, dependency, settings or schema file; no member of a data-plane file added.

The register and the other documents (follow the recording rules written in those files; do not copy the wording of earlier task files):
8. `ARCHITECTURE/Requirements.md`: the OD-18 row follows the register's **"행 형식"** - one link to the new ADR with a few words of topic in the `**확정분**` list, and the open part of sub-question 7 rewritten in place in `**잔여**`; no restatement of the record, no dated paragraph. FR-1 / FR-10 change only if the owner's answer is a reading of them that the row must show, with the comment URL.
9. `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's **"기록 규칙"** - one adopted-record line for the new ADR in the OD-18 section; the open part of sub-question 7 (the "남음:" of its paragraph) and the "도구 계약이 아직 없는 것" sentence rewritten in place to say what remains; no restatement of the record, no dated paragraph.
10. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's checking rules (CLAUDE.md "문서 커버리지 재검사") for S0, S1 and S1-b, and update §검사 결과 as its first paragraph prescribes (a verdict change only goes into the history).

Process:
11. Session-entry check before the first edit (CLAUDE.md); if an open PR or an unlanded branch edits the same rows or paragraphs, say so in `## Result` and keep the edits apart.
12. Document mode of CLAUDE.md A-13: reviewer cycle (at most 7 rounds), rebase on `origin/main`, direct push to `main` with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0239` trailers. The driver posts the DRIVER §9 notice on #5.
13. No `claude` is started and nothing of the runtime is required (D16).

## Out of Scope

- The contract of `profiler.collect` and any code (`hilclaw/`), test, schema file or registration in `hilclaw/tools.py`.
- Any new external dependency (a profiler tool) - a BLOCKED reason under A-13 if the answer needs one.
- The run tools' open records (ADR-0068, T-0210 / HQ-0021) and anything of the S6 metric (T-0231 / HQ-0023).
- The mock's offer of `profiler.collect` unless the owner's answer names it; any other backend; OD-26.
- Edits to accepted ADRs (list sentences that become less exact under Consequences instead).

## Follow-ups

- If `profiler.collect` is offered: the records of its contract (request, result, journaled or not, the mock's script), then the code slices.
- If it is not offered: the round loop's treatment of the `profile` step belongs to PLAN P2-1; the code of the `cpu_standin` backend table needs no change (no operation is added).

## Result

- **Outcome**: DONE (document mode). New record `ARCHITECTURE/decisions/ADR-0130-od18-cpu-standin-profiler-collect.md` (the task file's ADR-0077 was stale; ADR-0130 was the next free number on `origin/main` and on every remote branch at execution time). Landed on `main` as one commit with the trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0239`; the branch `claude/T-0239-od18-cpu-standin-profiler-collect` was deleted.
- **Fixed input**: the owner's HQ-0025 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280027094): (1)(a) `cpu_standin` does not offer `profiler.collect`, a call there answers `not_offered`, and the round's profile is what `sim.run` / `board.run` return; (2)(a) the round-loop record may treat FR-1's `profile` step on `cpu_standin` as carried out by those results until a target that offers `profiler.collect` exists; owner's note (MVP starting point, may be reopened once the loop has run end to end) listed under Boundaries. No new external dependency, no data-plane change: no BLOCKED reason applied.
- **The record's own design** (subject to the 7-day window): `not_offered` is the answer at moment ④ of ADR-0016 (today no `profiler.collect` is registered, so a call is refused by the registry as an unknown tool; without a `cpu_standin` table entry it would be `no_backend`); the owner's parenthesis read as the run tools' results as they are (`intervals_ns` with `resolution_ns` and `sample_form`, `memory_bytes`; ADR-0063); for `profile.json` and a spec's `feedback.attempts[].profile` only that no `profiler.collect` call produces anything on `cpu_standin` and that the results are the source, with content, writer, summary structure, the choice among several `execution` results (OD-18 ⑳) and whether a non-promoted attempt is profiled (PLAN P2-1) left open by name.
- **Register**: `Requirements.md` OD-18 row (one `**확정분**` link, `**잔여**` ⑦ rewritten to "지점이 없는 대상" and the `profiler.collect` contract for a target that offers it added); FR-10 row gains one sentence reflecting the answer with the comment URL (as HQ-0005 was reflected there). `OpenDecisionProposals.md` OD-18: one `**채택분**` line, ⑦'s "→ 부분 답 … 남음:" and the "도구 계약이 아직 없는 것" sentence rewritten in place. `StandardScenarios.md`: S0, S1 and S1-b rechecked, no verdict change, no gap; S0 step 6 and S1 step 6 notes name the open OD of the profile; "최근 재검사" updated.
- **Session-entry check**: open PR #186 (T-0324, code: `hilclaw/`, `tests/`) does not touch these files. Unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0318-*` and `feature/uc-alignment` edit the same three register files (T-0210 and T-0264 the OD-18 row and section); the edits here were kept to the ADR-0130 link, sub-question ⑦ and the `profiler.collect` sentence, so those branches will need a manual rebase of the OD-18 row when they land. Issues #4, #7, #8: nothing on `profiler.collect` or HQ-0025.
- **Review**: 7 rounds (dev-reviewer, context-isolated). R1 Request changes (P1-1 reason contradicted PLAN D18; summary wording too broad; ⑳ not left open; ODP line stronger than the answer; nits). R2 Request changes (FR-10 and ODP lines lacked the `cpu_standin` scope; "⑦ 나머지" vs. ⑦ still open). R3 Request changes (decision 3 decided that a non-promoted attempt has a profile; nits). R4 Approve with 2 nits; R5 Approve with 3 nits; R6 Approve with 1 nit; R7 Approve, no findings. All findings addressed.
- **DRIVER §9**: OD-18 stays `제안됨` (partial answer); the owner notice for the record's own design is owed (7-day window).
- **Runtime acceptance**: none new.
- **Follow-ups**: (1) integrator: sentences of ADR-0004 decision 3, ADR-0016 decision 3, ADR-0038 Status / decision 2 / Consequences that are now less exact (listed in ADR-0130 Consequences); (2) PLAN P2-1 writes the `profile` step on `cpu_standin` as carried by the run tools' results; (3) the `profiler.collect` contract only when a target that offers it is taken up or the owner reopens the question.
