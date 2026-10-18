---
id: T-0314
title: Record an ADR on which of several ended checks of one attempt at one execution point counts for the hard floor of FR-9 (OD-18 sub-question 14, first part, for `correctness.check` on first-case and mock runs)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-9, FR-1, FR-10, NFR-4, OD-18, OD-16]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P1-1 (the FR-10 tool contracts) is open. `correctness.check` is journaled, and a request carries `execution` (ADR-0040). A request with a higher `execution` is a new check on newly drawn inputs, and nothing stops a caller from asking for one. ADR-0040 Limits says it outright: "this is a hole in the hard floor of FR-9". The failed checks stay in the log, but no record says which ended check counts. So a kernel that is right for some inputs and wrong for others can pass at some `execution`. The open question is OD-18 sub-question ⑭: "which of them counts for the hard floor of FR-9, and what keeps a caller from asking for further executions until one passes".

This task answers only the first part: which ended checks count, and how they combine into the attempt's standing at that point. It covers the runs that the `correctness.check` contract already serves, namely the first case and runs whose hw_profile names the mock (ADR-0021, ADR-0038 decision 6). The second part, what keeps a caller from asking for more executions, needs the hooks and gates of the rest of OD-18 and the retry part of OD-17. It stays open.

This is a design-level OD part. Under DRIVER §9 the executor writes the ADR, a reviewer's approval accepts it, and the driver posts the 7-day owner notice. It is not owner-only as far as the planner found. HQ-0005 (3) settled the number of checks per attempt and the fresh draw per check, not which ended check counts. #5 A-6 (OD-5) fixed that accuracy is a gate and not a score. Before writing, the executor checks #5 and #4 for an owner sentence that answers ⑭. If one does, or if the answer needs an owner-only item (#5 A/B, C-6, OD-25, OD-3 — gates in particular), stop with BLOCKED `requirement-unclear` or `owner-only-decision`. Do not decide it.

No open HQ blocks it. None of the blocked tasks (T-0210 on ⑲ (나), T-0231 on OD-30, T-0264 on ⑱ (마)) and no open PR (#179, `clang_build`) touches ⑭.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77: executor steps 5-6, the naming rule, the time cap), §5 (lines 86-114), §8 (lines 135-139), §9 (lines 141-148).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md`: FR-1 (line 19, the outcomes ⑴-⑶ of a check at each point), FR-3 ④ (line 21), FR-9 (line 27), the "행 형식" paragraph (line 84), the OD-18 row (line 109) and the OD-16 row (line 107).
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md`: decisions 2 and 3 (lines 34-60), the Walk-through (lines 106-122), Limits (lines 124-135), and Boundaries (lines 163-175, which hold the text of ⑭).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decision 3 (lines 42-60, identity and "a new identity with a higher `execution`") and decision 9 (lines 109-118).
- `ARCHITECTURE/decisions/ADR-0021-od18-correctness-check-split.md`: decisions 3 to 5 and 6 (Limits) (lines 54-113).
- `ARCHITECTURE/decisions/ADR-0038-od18-cpu-standin-execution-points.md`: decisions 4 to 6 (lines 48-71), the Walk-through and Limits (lines 76-100).
- `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md`: decisions 2 and 3 (lines 35-61, `outcome` pass/fail/broken and `condition`), and decision 8 (lines 132-139).
- `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` and `ADR-0047-od18-correctness-check-operation-tool-failure.md`: the Decision sections, for what an ended check with a `failure` (not a result) is.
- `ARCHITECTURE/decisions/ADR-0046-od18-correctness-check-draws.md`: Status (lines 7-12), decision 7 (lines 130-137), Limits (lines 171-180) and Boundaries (lines 209-224). These cover the draw count, re-verification and gates, which stay open.
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: Limits item 1 (line 117) and Boundaries (lines 152-166). This is the parallel hole of the run tools, ⑳, which is not answered here.
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8), the OD-18 section (lines 263-339, with ⑭ at line 331 and ⑳ at line 337), the OD-16 section (lines 231-252, with ⑤ at line 249) and the OD-17 section (lines 253-261).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (from line 168), and the scenarios that exercise correctness (S0, S1, S7, S8).

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`, in the record format of ADR-0001. Before writing, make sure ADR-0110 is free on `origin/main` and on every remote branch (`git ls-tree`; the unlanded branches of T-0210, T-0231 and T-0264 hold ADR-0068, ADR-0074 and ADR-0088). If it is taken, use the next free number, rename the file, update the touchesFiles path, and say so in Result.
2. Status says the record was accepted under DRIVER §9 and is not owner-confirmed. It keeps cited sentences (quoted, with their source) apart from the record's own choices. It names the records it builds on (at least ADR-0011, ADR-0021, ADR-0038, ADR-0040 and ADR-0042) and says it is revisited if one of them is reverted.
3. Scope: the checks of `correctness.check` about one attempt at one execution point, on runs the contract serves today (first case; hw_profile naming the mock). The record says who reads the rule: the consumer of check outcomes that FR-1 names (repair, elimination, triage, promotion). It names no component, because the Round-Manager and evaluator are PLAN P2-1/P2-3 and OD-23.
4. The Decision answers the first part of ⑭ within the scope. It weighs alternatives, at least these:
   - the first ended check counts and later ones do not;
   - the last ended check counts;
   - every ended check counts, so one fail stands against the attempt at that point;
   - any pass counts.
   For each alternative the record says:
   - what it does to the hole ADR-0040 Limits names, and to FR-9's "hard floor";
   - how it treats an ended check whose end line holds a `failure` instead of a result (ADR-0045, ADR-0047), a `broken` result (ADR-0042), and an identity that is still open;
   - whether the counting checks are found by reading the log alone (ADR-0011).
   It keeps the two points apart, following ADR-0038 decision 4 and FR-1 ⑴-⑶. It does not merge the sim and board checks.
5. The record does not answer the second part of ⑭, what keeps a caller from asking for further executions. It adds no hook, gate, retry rule, draw count or re-verification rule (OD-18 rest, OD-17, OD-10, OD-3, OD-16 ⑤, ADR-0046 Boundaries). If the first part cannot be answered without one of these, record that as a finding, leave the part open, and do not invent it.
6. The record does not decide ⑳ (the run tools). It may state in Boundaries whether its reasoning would carry over, without deciding it.
7. The record adds no member, file, kind of file, `step` value, event kind or tool-failure kind to the data plane. It changes no code, `instance.json`, `STATE.json` or `events.ndjson`. Consequences carries an A-13 reading saying so. If the decision cannot be written without such a change, stop with BLOCKED (data-plane schema change). It checks the index documents (`ARCHITECTURE/StepValues.md`, `EventKinds.md`) only to confirm that nothing is added.
8. Consequences:
   - name the code slice the record makes possible, if any (for example, a pure function over a log's ended check lines), and what it waits on;
   - name no module or function as binding;
   - list, found by grep, the sentences of earlier records that become less exact (ADR-0040 Limits at least), and do not edit them;
   - name the runtime acceptance items, or say there are none.
9. Boundaries list at least: the second part of ⑭, ⑳, OD-16 ⑤ (draw counts and re-verification), FR-3 ④ re-verification, OD-17 retry and OD-10 recovery, OD-15/OD-29 promotion, OD-3 gates, OD-23, PLAN P2-1/P2-3, and any change to earlier records, `hilclaw/`, tests, CI, settings files or `HIL-Claw-data`.
10. The edit to `ARCHITECTURE/Requirements.md` touches only the OD-18 row and follows the "행 형식" rule written in that register (line 84). Apply that rule as written; do not model the edit on earlier task files.
11. The edit to `ARCHITECTURE/OpenDecisionProposals.md` touches only the OD-18 section and follows the "기록 규칙" in that file's header (line 8). Apply that rule as written; do not model the edit on earlier task files.
12. `ARCHITECTURE/StandardScenarios.md`: re-check coverage by the document's rules (CLAUDE.md "문서 커버리지 재검사"). Update §검사 결과 exactly as its first paragraph prescribes.
13. No other file changes. `git diff --stat origin/main` lists only the touchesFiles. `git diff --check` is clean. Every relative link added resolves. The OD register has the same number of rows before and after.
14. Document mode (CLAUDE.md A-13): branch `claude/T-0314-<slug>`, context-isolated reviewer cycle of at most 7 rounds, rebase on `origin/main`, direct push to main. The commit message ends with one trailer block, with no blank line inside it, holding `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0314`. Check with `git interpret-trailers --parse` that git parses both. The §9 owner notice on #5 follows, with the §8 footer.
15. Start no compiler, kernel, container or `claude` process (D16).

## Out of Scope

- Any code, test, CI or settings change.
- The second part of ⑭; ⑳; OD-16 ⑤; OD-17; OD-10; OD-15; OD-29; OD-23; owner-only items (OD-25, OD-3, C-6, #5 A/B).
- Editing earlier ADRs (including the "less exact" sentences other records list), UsageCases, the README or the index documents.
- The unlanded branches of T-0210, T-0231 and T-0264, and PR #179 (T-0284).

## Follow-ups

- If the record makes a code slice possible, a later code task. It must not need a Round-Manager or evaluator component that does not exist yet.
- If the reasoning carries over, a later doc task on ⑳'s counting part for `sim.run`/`board.run`.

## Result
