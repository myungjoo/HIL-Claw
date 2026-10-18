---
id: T-0321
title: Make ADR-0113's remaining sentences that state a best's comparison role as a fact conditional on the choice rule (follow-up of T-0320)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [NFR-3, OD-13, OD-1]
dependsOn: [T-0320]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md
estimatedSize: {loc: 8, files: 1}
hq: []
---
## Why

T-0320 (landed as `8409de1`) made one sentence of ADR-0113 decision 2 conditional: "where a best is the base of later comparisons (whether it is, is part of the choice rule; decision 3)". The reason was that whether later candidates are compared against the best is part of the rule that chooses a best. That rule is the rest of OD-1 (#5 A-4, owner-only), and ADR-0113 decision 3 leaves it open. T-0320's `## Result` left two follow-ups:

1. **Follow-up sentences.** Two more sentences still state that role as a fact:
   - decision 2, first "Why" bullet (line 37): "So a noisy candidate seldom displaces an incumbent, and a noisy incumbent is seldom shown to be beaten."
   - Limits 1 (line 60): "A candidate is seldom called different from a noisy best, so a run can keep a noisy best for many rounds even when a candidate is in fact better."
2. **Unapplied reviewer nit.** The reviewer of T-0320 left one nit unapplied: the parenthetical on line 42 could read "(whether it is belongs to the choice rule, decision 3)".

This task makes those sentences exact. The planner also found a third sentence of the same shape:

- Limits 2 (line 61): "a noisy measurement can be called different by chance and become a best". It assumes that being called different is how a measurement becomes a best.

The executor checks it under the same rule. The record's decisions do not change, so ADR-0113's §9 owner window is not affected. The task is small, in document mode, and needs no owner decision, no runtime and no HQ.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77: executor steps 5-6, the resume rule, the time cap) and §5 (lines 86-114: format, naming rule, trailers).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사" and "브랜치·merge 절차" (document mode).
- `PROCESS/tasks/T-0320-adr0113-r7-nits.md`: `## Result`, the bullets "Review" and "Follow-ups".
- `ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md`: the whole record (112 lines). Read especially Status line 6 ("Three kinds of content"), decision 1 (lines 27-31), decision 2 (lines 33-42), decision 3 (lines 44-49) and Limits (lines 58-64).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`: decision 4 (lines 40-47) and decision 7 (lines 60-71). Read these only to check that a cited sentence is quoted correctly.

## Acceptance Criteria

1. **Line 37.** Rewrite "So a noisy candidate seldom displaces an incumbent, and a noisy incumbent is seldom shown to be beaten" so that it no longer asserts that candidates are compared against an incumbent best. One possible form is "where a candidate is compared against an incumbent (whether it is, is part of the choice rule; decision 3), …". The point of the bullet stays: the wide interval of a not-converged measurement already limits the harm its noise can do, and a second bar would count the same noise twice. Do not change the NFR-3 citation and the reading that T-0320 put in this bullet.
2. **Limits 1 (line 60).** Give the comparison against a best the same conditional form. Keep what the Limit says: a noisy best can persist, O1 accepts that, and the remedy (①) is open.
3. **Limits 2 (line 61).** Check whether "be called different by chance and become a best" asserts as a fact that being called different is how a best is chosen. If it does, make it conditional in the same way. If it does not, leave it and give the reason in one line in `## Result`.
4. **Line 42 nit.** You may shorten the parenthetical to "(whether it is belongs to the choice rule, decision 3)". If you do, use the same parenthetical wording in every conditional this task adds, so the record uses one form throughout.
5. **Search.** Grep ADR-0113 for "incumbent", "against", "displace", "beaten", "noisy best" and "become a best". Treat every other sentence that states a best's comparison role as a fact the same way. Leave the baseline clauses as they are, because FR-1 states the baseline's role (Context line 23). Leave line 93 as it is (`against` of ADR-0071, not a best). List each changed line in `## Result`.
6. **No decision changes.** The decisions, the reasons, the Alternatives table, Consequences, Boundaries, Status, Context and References keep their content. Do not add a dated paragraph or a change log to the record. If an edit would change what the record decides, stop and return BLOCKED (reason: 요구 불명확/미결 발명 의심). Do not edit ADR-0007 or any other record.
7. **Other files.** Change no other file. `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` and `ARCHITECTURE/StandardScenarios.md` are not edited. The OD-13 register link and the adopted line for ADR-0113 name the record and its topic, not these sentences, so the recording rules of those files ask for no change. None of Requirements, UsageCases or StandardScenarios changes, so no coverage re-check is owed. If one of them must change after all, stop and return BLOCKED; do not widen the task. `git diff --stat origin/main` lists only the touchesFiles path. `git diff --check` is clean, and the file keeps LF line endings.
8. **Document mode** (CLAUDE.md A-13):
   - work on branch `claude/T-0321-adr0113-best-role-conditional`;
   - run a context-isolated reviewer cycle (dev-code-review, at most 7 rounds) until Approve;
   - rebase on `origin/main` and squash to one commit;
   - push to main directly, never with `git push --force*`;
   - end the commit message with one trailer block that holds `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0321`, with no blank line inside the block and a blank line before it. Check with `git interpret-trailers --parse` that git parses both.
9. **No #5 notice.** No OD status changes and no decision is added, so none is needed.
10. **D16.** Start no `claude` process, compiler, container or test. `## Result` records the edits as applied, the review rounds and any finding left unapplied.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `pyproject.toml`, `README.md`, the index files or settings files.
- Editing any other ADR, including ADR-0007, ADR-0071, ADR-0103 and ADR-0104.
- Deciding anything of OD-1 (how a best is chosen, whether candidates are compared against it), OD-28, OD-20, OD-29 or OD-18 ⑳. Also out of scope: the rest of OD-13 ②, including whether a not-converged measurement may serve as `against` (ADR-0071), and every question blocked by an open HQ (including HQ-0031 and the kept T-0318 branch).
- The files of open PR #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`).

## Follow-ups

- None expected. If the reviewer finds a further slip in ADR-0113 outside these sentences, list it here and do not widen the task.

## Result
