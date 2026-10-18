---
id: T-0316
title: Apply T-0314's two round-7 citation nits to ADR-0110 — the ADR-0026 location for "open or ended" after `end_line_failed`, and the ADR-0011 parts named in the Status builds-on list
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-9, OD-18]
dependsOn: [T-0314]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md
estimatedSize: {loc: 6, files: 1}
hq: []
---
## Why

T-0314 landed ADR-0110 as `4bc7f78` after 7 review rounds. The round-7 Approve left two non-blocking nits about where citations point. They are recorded in T-0314's `## Result`. They were not applied, because applying them would have needed an eighth round:

1. ADR-0110 decision 3, the bullet "**A call that ended with `end_line_failed`**" (line 60), cites "ADR-0026 decision 4" for the fact that such a call leaves its identity "open or ended". The reviewer said ADR-0026 decisions 2 and 4 would be more exact. On reading, the literal words "open or ended" are in ADR-0026 decision 3, in the `end_line_failed` row of its table (line 53). Decision 2's bullet "What the answer does not establish" (lines 40-43) says that the answer does not say "which of its two states the identity is in". Decision 4 (from line 61) is about the outcome the failing call returns.
2. The Status builds-on list (line 10) names ADR-0011 "decisions 3, 6 and 9". ADR-0110 decision 3 (line 59) also leans on ADR-0011 decision 4 and on its Consequences ("an open step is a point the run does not pass by itself"). Both are already in References (line 155).

The record's decisions do not change. Only the citations are made exact. This is the same kind of follow-up as T-0305, T-0307 and T-0312. It is small and in document mode, and it needs no owner decision, no runtime and no HQ. The §9 owner window of ADR-0110 (until 2026-10-26) is not affected, because nothing decided changes. The code slice T-0315 (`hilclaw/check_standing.py`) is not affected either.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77: executor steps 5-6, the naming rule, the time cap) and §5 (lines 86-114).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사" and "브랜치·merge 절차" (document mode).
- `PROCESS/tasks/T-0314-adr-od18-check-executions-hard-floor.md`: `## Result`, the bullet "Left unaddressed" (the two nits as the reviewer stated them).
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: Status (lines 3-12, especially line 10), decision 3 (lines 46-62, especially lines 59-60), and References (line 155, the ADR-0011 and ADR-0026 entries).
- `ARCHITECTURE/decisions/ADR-0026-od18-failed-step-line-append.md`: decision 2 (lines 37-44), decision 3 (lines 46-63, the `end_line_failed` row at line 53) and decision 4 (lines 61-68).
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decision 4 (lines 61-71) and Consequences (from line 156).

## Acceptance Criteria

1. **Nit 1 (ADR-0110 decision 3, line 60).** Read ADR-0026 decisions 2, 3 and 4. Edit the cited location in place, so that it names the decision or decisions whose text states that a call ending with `end_line_failed` leaves its identity open or ended. If the bullet quotes words, they must match the source word for word. If the reading supports the reviewer's "decisions 2 and 4", use that. If it supports another set (for example decision 3, the `end_line_failed` row, with decision 2), use what the text supports and give the reason in one line in Result. Do not change what the bullet says. Update the ADR-0026 entry in References (line 155) so that it lists the decisions the record now cites. Also update the ADR-0026 entry in the Status "cites" list (line 10) if it names decisions.
2. **Nit 2 (ADR-0110 Status, line 10).** Make the ADR-0011 parenthesis of the builds-on list name what the record leans on: decisions 3, 4, 6 and 9 and Consequences. Before writing, grep ADR-0110 for every "ADR-0011" citation and confirm the set. Use the set found by the grep, and say in Result if it differs from this list. Keep the sentence's form. The revisit clause at the end of that bullet stays as it is.
3. **No decision changes.** The decisions, Walk-through, Limits, Alternatives, Consequences and Boundaries of ADR-0110 keep their content, and so does the rest of Status. If either edit would change what the record decides, stop and return BLOCKED (reason: 요구 불명확/미결 발명 의심). Do not edit ADR-0026, ADR-0011 or any other record.
4. **Other files.** No other file changes. `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` and `ARCHITECTURE/StandardScenarios.md` are not edited. The OD-18 register link and the adopted line for ADR-0110 name the record and its topic, not its citations, so neither changes. None of Requirements, UsageCases or StandardScenarios changes, so no coverage re-check is owed (CLAUDE.md "문서 커버리지 재검사"). If the executor finds that one of them must change after all, stop and return BLOCKED instead of widening the task. `git diff --stat origin/main` lists only the touchesFiles path. `git diff --check` is clean, and the file keeps LF line endings.
5. **Document mode** (CLAUDE.md A-13):
   - branch `claude/T-0316-adr0110-r7-citation-nits`;
   - context-isolated reviewer cycle (dev-code-review, at most 7 rounds) until Approve;
   - rebase on `origin/main`, then one commit;
   - push to main directly, with no `git push --force*`;
   - the commit message ends with one trailer block, with no blank line inside it, holding `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0316`. Check with `git interpret-trailers --parse` that git parses both.
6. **No #5 notice** is needed, because no OD status changes and no decision is added.
7. **D16.** Start no `claude` process, compiler, container or test. `## Result` records the two edits as applied, the review rounds and any finding left unapplied.

## Out of Scope

- Any change to `hilclaw/` (including `hilclaw/check_standing.py`), `tests/`, CI, `pyproject.toml`, `README.md`, the index files (`EventKinds.md`, `StepValues.md`, `BlobTypes.md`, `SpendAxes.md`) or settings files.
- Editing any other ADR, including the "less exact" sentences that ADR-0110 Consequences lists (ADR-0040 Limits and others).
- The second part of OD-18 ⑭, ⑳ (the run tools' counting part), OD-16 ⑤, OD-17, OD-10.
- The files of open PR #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`) and every BLOCKED task.

## Follow-ups

- None expected. If the reviewer finds a further citation slip in ADR-0110 that is outside these two nits, list it here and do not widen the task.

## Result
