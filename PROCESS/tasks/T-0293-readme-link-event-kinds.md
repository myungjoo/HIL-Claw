---
id: T-0293
title: Add `ARCHITECTURE/EventKinds.md` to the ARCHITECTURE row of the repository table in `README.md` (follow-up of T-0292)
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-8]
dependsOn: [T-0292]
touchesFiles: [README.md]
estimatedSize: {loc: 2, files: 1}
hq: []   # No OD is decided here. Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 / OD-30 / OD-8 instance records, clang_build, local_run, the build log and json helpers; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

T-0292 landed ADR-0098 (main 9750cc8), which created a new top-level design document, `ARCHITECTURE/EventKinds.md`: the one index of the event kinds of `runs/<run_id>/events.ndjson`. The repository table in `README.md` lists the `ARCHITECTURE/` documents by name on its `ARCHITECTURE/` row (line 46). It does not list the new file. T-0292's reviewer flagged this in round 1 (finding 2). T-0292 left it as a doc follow-up because the fix was outside its 5-file cap (see `## Result` of `PROCESS/tasks/T-0292-adr-od8-event-kind-vocabulary.md`). This task adds that one link.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: the executor procedure, the resume rule and the time limit) and §5 (lines 86-115: the task format, the naming convention and the `Task:` trailer).
- `CLAUDE.md` "상시 규칙", in particular "브랜치·merge 절차" (document mode) and "코멘트 최소화".
- `README.md` lines 40-56 ("저장소 구성" table; the `ARCHITECTURE/` row is line 46).
- `ARCHITECTURE/EventKinds.md` lines 1-3 (title and first paragraph). Read them so the description you add says what the file is.
- `PROCESS/tasks/T-0292-adr-od8-event-kind-vocabulary.md` `## Result` (the follow-up this task closes).

## Acceptance Criteria

1. On line 46 of `README.md` (the `ARCHITECTURE/` row of "저장소 구성"), add one link `[EventKinds.md](ARCHITECTURE/EventKinds.md)` with a short Korean description in parentheses, in the same `[name](path)(설명)` form as the other entries on that row. The description should say what the file is: the event-kind list of `events.ndjson`, for example `(events.ndjson 이벤트 종류 목록)`. Put the link after `OpenDecisionProposals.md` and before `reviews/`.
2. Change nothing else in `README.md` and no other file. In particular, do not edit `ARCHITECTURE/` files, ADRs or the `ARCHITECTURE/decisions/` row. Do not describe ADR-0098's content beyond the short description.
3. Before editing, check that no other `ARCHITECTURE/*.md` top-level document is missing from that row (`ls ARCHITECTURE/`). If one is, do not add it. Report it in `## Result` as a follow-up.
4. CLAUDE.md "문서 커버리지 재검사" does not apply, because `README.md` is not one of Requirements, UsageCases or StandardScenarios. Leave `ARCHITECTURE/StandardScenarios.md` untouched and say so in `## Result`.
5. Use document mode (CLAUDE.md A-13):
   - Work on branch `claude/T-0293-readme-link-event-kinds`.
   - Run the reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) until Approve.
   - Rebase on `origin/main`, squash to one commit and push it to main directly.
   - End the commit message with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0293`.
   - Never use `git push --force*`.
6. Write `## Result` with the landed commit, the review rounds, any unapplied findings and any follow-ups. Do not start a `claude` process (D16). Run no code, test, compiler or container.

## Out of Scope

- Any other wording change in `README.md`, including the descriptions of the 2층 contents (lines 34-35).
- Any change to `ARCHITECTURE/`, `PROCESS/` (other than this task file's `## Result`), `hilclaw/`, `tests/`, CI or settings files.
- No #5 notice is needed, because no OD is decided (DRIVER §9 does not apply).

## Follow-ups

- Any other unlisted `ARCHITECTURE/` document found under criterion 3.

## Result

- DONE. Landed on main as b5a9111 (document mode, one squashed commit, fast-forward; `Reviewed-by: reviewer agent (1 rounds, Approve)`, `Task: T-0293`). Only `README.md` line 46 changed: `[EventKinds.md](ARCHITECTURE/EventKinds.md)(events.ndjson 이벤트 종류 목록)` added between `OpenDecisionProposals.md` and `reviews/`.
- Criterion 3: `ls ARCHITECTURE/` shows EventKinds, OpenDecisionProposals, Requirements, StandardScenarios, UsageCases (+ `decisions/`, `reviews/`); all are now listed. No other missing document.
- Coverage re-check not applicable (README.md is not Requirements/UsageCases/StandardScenarios); `ARCHITECTURE/StandardScenarios.md` untouched.
- Review: round 1 Approve. Unapplied: none (the one nit, adding the `Reviewed-by` trailer at squash time, was applied).
- No #5 notice (no OD decided). Task branch deleted (remote and local).
- Follow-ups: none.
