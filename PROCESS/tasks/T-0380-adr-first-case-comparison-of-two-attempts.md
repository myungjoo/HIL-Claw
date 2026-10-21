---
id: T-0380
title: Write the ADR that gives a first-case verdict its comparison of two attempts — how the `difference` of a `comparison` entry of `eval/verdicts.json` is given by a function of the package over the journaled `sim.run`/`board.run` results, which of them enter, and how `verdicts.write` holds such an entry (ADR-0128 Consequences slice 3, ADR-0131 Consequences slice 4; OD-16/OD-23 part, PLAN P2-3)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-9, FR-17, OD-16, OD-23, OD-18, OD-13, OD-30, S1]
dependsOn: [T-0360]
touchesFiles:
  - ARCHITECTURE/decisions/          # one new record, the next free number at execution time (ADR-0140 at planning time; ADR-0068, ADR-0074, ADR-0088, ADR-0132 and ADR-0137 are held by the unlanded branches of T-0210, T-0231, T-0264, T-0361 and T-0375)
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2-3 (the evaluator, "OD-16 종결 필요(§9 ADR 경로)") is a checklist item that comes before P2-5 in the P2 order (PLAN P2 head, D18), so the D18 rule for work outside the checklist does not apply.

The evaluator of a first-case turn can write verdicts today, but every verdict is `inconclusive`. `verdicts.write` refuses every record that holds a `comparison` entry (`comparison_not_given`), because no function of the package gives the `difference` (ADR-0128 decision 6). ADR-0128 Consequences slice 3 and ADR-0131 Consequences slice 4 both name the missing piece as "after a record": the comparison of ADR-0007 decision 7 for two attempts. Without it, no hypothesis of P2-5's first run can be `supported` or `refuted` (FR-17, ADR-0071 decision 4), and S1's round loop judges nothing.

The rule itself exists. ADR-0007 decisions 7 and 9 fix it, and `hilclaw/harness/measurement.py` implements it (`ratio_interval`, `is_different`). The run tools' result (ADR-0063) holds `intervals_ns`. ADR-0114 says a "not converged" result must not be barred from `against`. What is missing is the record that says which journaled results enter the rule, which function gives the `difference`, and how `verdicts.write` holds the entry. This is a design-level part of OD-16/OD-23 (DRIVER §9), so the record is written in this task.

The record does not need any open HQ. It must leave the base of the comparison open (which attempt `against` must be: OD-20 `best_ref`, OD-28 beyond ADR-0119, OD-29), as ADR-0071 decision 3 does. HQ-0021 (`sim.run`/`board.run` tool failure of an operation, ⑲ (나)) and the registration of the run tools are not needed by the record: a comparison reads end lines that hold a `result`, and the record only says what happens when there are none.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming convention, D4 size cap) and §9 (ADR path for a design-level OD).
- `CLAUDE.md` sections "미결은 발명하지 않는다", "문서 커버리지 재검사", "브랜치·merge 절차", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (document-mode checks).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md` decisions 4, 5, 7, 9, 10 (lines 40-103) and Boundaries (lines 150-159).
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md` decisions 3-6 (lines 50-85), the Example (lines 86-113) and Boundaries (lines 141-154). Its `comparison` entry members (`metric`, `point`, `measured`, `against`, `difference`) are the form. No member is added by this task.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md` decisions 3 and 6 (lines 43-50, 61-75) and Consequences (lines 112-134).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` decisions 3-6 (lines 40-82), Alternatives (lines 107-130), Consequences (lines 131-151) and Boundaries (lines 152-163). This is the closest precedent: one `check` entry against several ended executions (decision 4), and the log check in `verdicts.write` (decision 5).
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md` decisions 2-3 (lines 31-62).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md` decision 3 (lines 53-65), the meaning of `execution`.
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` decisions 2-4 and 7 (lines 37-76, 95-106).
- `ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md` decision 2 (lines 33-43) and `ADR-0114-od13-not-converged-against.md` decisions 2-5 (lines 33-68).
- `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md` decisions 2-4 (lines 40-61) and Consequences (lines 92-114).
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8), § OD-18 sub-question ⑳ registered by ADR-0062 (line 361), and §§ OD-13, OD-16, OD-23, OD-30 (lines 200-276, 398-474, 475-end), only to find the sub-questions this record answers or touches.
- `ARCHITECTURE/Requirements.md`: the register's "행 형식" (line 84) and rows OD-13, OD-16, OD-18, OD-23, OD-30 (lines 104-121).
- `ARCHITECTURE/StandardScenarios.md`: the check rules (around line 26) and the first paragraph of §검사 결과 (line 168 onward).
- `hilclaw/verdicts_tool.py` lines 1-120 (the checks in order and their kinds), `hilclaw/checks_tool.py` lines 1-80, `hilclaw/harness/measurement.py` lines 1-60 and 113-171, `hilclaw/run_identity.py` lines 1-40 (the two `step` values). Code statements in the record are observations, as earlier records phrase them.

## Acceptance Criteria

1. **One new record** `ARCHITECTURE/decisions/ADR-NNNN-od16-first-case-attempt-comparison.md` (the next free number; the slug may differ). It has the structure of ADR-0131: Status (accepted under DRIVER §9, not confirmed by the owner; builds on ...), Context with the open points cited, Decision, Walk-through, Alternatives considered, Consequences, Boundaries, References. Scope: the runs of ADR-0120 decision 1, as ADR-0128 and ADR-0131 have it.
2. **The decision answers each of these, with the alternatives weighed and the choice stated**:
   - (a) **The means.** Which function of the package gives the `difference`, and how the evaluator gets it. Weigh at least: a typed read tool through the MCP front (in the manner of `checks.read`) whose answer the evaluator copies into the entry, with `verdicts.write` recomputing it; and `verdicts.write` alone computing or checking the `difference` of an entry it is given. The record says how a given comparison is told from an invented one, which ADR-0128 decision 6 asks of "the record that adds the comparison tool". If a new registry tool is chosen, name it, its request members, its result and its kinds, and say whether it is journaled. The description and input schema are left to the code slice.
   - (b) **Which results enter.** For one `ref` at one `point`, which end lines of `sim.run`/`board.run` give the sample set of the rule. Cover several ended executions (part of OD-18 ⑳ for comparisons, first case only), an end line with a `failure` and no `result`, a `result` whose `outcome` is `broken`, an open identity, and no line at all. Say what the function or tool answers in each case. It either compares or refuses with a named kind; it never compares a set the rule's domain excludes (ADR-0007 decisions 4-5). It must not refuse, and must not leave uncounted, a comparison because the result behind `against` is `"not_converged"` (ADR-0114; ADR-0128 Consequences slice 3).
   - (c) **The rule applied.** Name the ordered pair, A = `against` and B = `measured`, as ADR-0071 decision 3 reads it. Say how `lower` / `higher` / `not_different` follow from ADR-0007 decision 7 on `intervals_ns`, with the fixed seed of decision 9. Do not add a parameter, a margin or an equivalence rule (OD-13, OD-1).
   - (d) **`verdicts.write`.** Which check replaces `comparison_not_given`, where it sits in the order of checks of ADR-0128 decision 6 as ADR-0131 decision 5 extends it, and its kinds. Kinds are names of the tool layer, not a change of the data plane (as ADR-0128 says). Say whether a `comparison` entry's `ref`s must also have a founded `check` entry (ADR-0071 decision 4 counts a comparison only when both sides pass at `board`), or whether that stays a rule of the value only.
   - (e) **The evaluator.** What its `tools` list and its "Verdicts" text become in the code slice, in the manner of ADR-0131 decision 6. If a tool is added, the list changes. ADR-0139's derivation of `--allowedTools` from the agent files then carries it, and the record says so.
3. **Stays open, and is written as open** (Boundaries): the base of the comparison, i.e. which attempt `against` must be (OD-20 `best_ref`, OD-28 beyond ADR-0119, OD-29), and which comparisons a verdict must include; whether a sim comparison counts on sim-only hardware (OD-26); a comparison when the memory ceiling is over or not judged (ADR-0071 Boundaries); drift across sessions (ADR-0007 decision 10); what stops a caller from requesting more executions until a better figure appears (the rest of ⑳, OD-17, OD-10); the run tools' registration and ⑲ (나) (HQ-0021). If an answer to any of these turns out to be needed, the record says so and does not decide it.
4. **No data-plane change.** No member, file, kind of a data-plane file, value or version is added or changed. The `comparison` entry of ADR-0071 is used as it stands. If the design cannot be completed without such a change, stop and return BLOCKED (CLAUDE.md A-13, data-plane schema change). Do the same if a choice turns out to be owner-only (DRIVER §9).
5. **Consequences** list:
   - the code slices for the planner, in code mode with fixture logs only and no `claude` (D16), each within the D4 cap: for example the function or tool, the `verdicts.write` check, and the evaluator definition and its test;
   - the earlier records and docstrings that become less exact, listed and not edited (at least ADR-0128 decision 6 and Consequences slice 3, ADR-0131 Consequences slice 4, ADR-0071 decision 3 "Open", and the `hilclaw/verdicts_tool.py` docstring's "until a tool gives a comparison");
   - any runtime acceptance item the record adds, numbered from (xli) on in the turn-session series. The executor names them in the Result so that the driver can notify them through the HQ path with reason `runtime-acceptance` (DRIVER §8). The record adds none if nothing in it rests on a live session.
6. **Register edits follow the recording rules written in the files themselves.** Do not copy the wording of earlier task files:
   - `ARCHITECTURE/Requirements.md`: follow the register's "행 형식" (line 84). Add one ADR link to `**확정분**:` of the OD row(s) the record answers part of, and rewrite `**잔여**:` in place. Do not restate the record and do not add dated paragraphs. Change the status cell only if the vocabulary requires it.
   - `ARCHITECTURE/OpenDecisionProposals.md`: follow the header's "기록 규칙" (line 8). Add one `- **채택분** [ADR-NNNN](…) — …` line in each section the record answers part of. Rewrite the end state of each sub-question it answers or partly answers (⑳ of OD-18 at least, if (b) answers it for comparisons) in place, and keep the question's wording.
   - `ARCHITECTURE/StandardScenarios.md`: recheck coverage by its check rules (CLAUDE.md "문서 커버리지 재검사"). Update §검사 결과 only as its first paragraph prescribes, i.e. record history only if a verdict changed.
7. Document mode under CLAUDE.md A-13: a context-isolated reviewer cycle (dev-item-address steps 10-12), rebase on `origin/main`, and a direct push to `main` with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer and `Task: T-0380`. No file outside `touchesFiles` changes. In particular, no `hilclaw/`, `tests/`, `orchestration/` or `PROCESS/` file changes, and `.claude/settings*.json` are not touched.
8. D16: no real `claude` is started in any form, and nothing is required of the development machine. Quotes of Claude Code documentation, if any, are checked against the official pages and cited.
9. The Result names the commit, the review rounds, the ADR number, the runtime acceptance items added (or "none"), and the less-exact list.

## Out of Scope

- Any code: the function or tool, the `verdicts.write` change, `orchestration/agents/evaluator.md` (later code slices).
- The base of the comparison, `best_ref`, promotion and improvement for the run (OD-20, OD-28 rest, OD-29, ADR-0050 decision 3); the selection role and `hypotheses.write` (ADR-0132 on the unlanded T-0361 branch, HQ-0048).
- The run tools' tool function, registration and ⑲ (나) (T-0210, HQ-0021); the `cpu_standin` operation of `correctness.check`.
- Editing the "Less exact, not edited" sentences of any earlier ADR.
- Anything from the unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`, `claude/T-0361-*`, `claude/T-0375-*`, and from draft PR #186. Overlap note: T-0210 touches the OD-18 lines and T-0361 the OD-23 lines of the two registers. If either lands first, rebase onto it and keep both edits.

## Follow-ups

- The code slices that the record's Consequences lists (planner, after landing).

## Result

- **DONE.** Landed on `main` in document mode as one commit with `Task: T-0380` and `Reviewed-by: reviewer agent (3 rounds, Approve)` (find it with `git log origin/main --grep='^Task: T-0380'`); branch `claude/T-0380-adr-first-case-attempt-comparison` deleted. Review rounds: 3 (round 1 Request changes: a `failure` end line may hide a lost measurement, so it now refuses like an open identity, `measurement_unknown`; OD-30 link order. Round 2 Approve with one minor: ADR-0065 added to the sources. Round 3 Approve, no findings).
- **ADR number**: [ADR-0140](../../ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md). Means: a typed registry tool `timings.compare` (not journaled), recomputed by `verdicts.write`; `comparison_not_given` is replaced by `timing_result_invalid` in the step pass, `comparison_unfounded` and `comparison_unverified` (a counted comparison rests on the standing verified at board). Registers: OD-16, OD-18, OD-23, OD-30 rows and sections gain the link; OD-18 sub-question ⑳ is partly answered; StandardScenarios rechecked (S0, S1, S7), no verdict change.
- **Runtime acceptance items added**: none.
- **Less exact, not edited**: ADR-0128 decisions 3 and 6, Consequences slice 3, "The cost, plainly", Boundaries; ADR-0131 decisions 4 to 6, Consequences slice 4, "The cost, plainly", Boundaries; ADR-0129 decision 5; ADR-0071 decision 3, decision 4 "Open", Boundaries (⑳); ADR-0114 and ADR-0110 Boundaries (⑳); ADR-0063 decision 4 (which component compares); ADR-0019 decision 2 (widened once more); `hilclaw/verdicts_tool.py` docstring ("until a tool gives a comparison"), `KIND_COMPARISON_NOT_GIVEN` comment and description; `hilclaw/run_identity.py` and `hilclaw/tools.py` docstrings; `orchestration/agents/evaluator.md` "Verdicts".
- **Follow-ups (planner)**: the three code slices of ADR-0140 Consequences — (1) `timings.compare` with its tests and registration; (2) the `verdicts.write` checks of decision 5; (3) `orchestration/agents/evaluator.md` and its `tools` test. They give no `supported`/`refuted` verdict in a real run until `sim.run`/`board.run` are registered (T-0210, HQ-0021).
