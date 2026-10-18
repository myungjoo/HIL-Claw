---
id: T-0299
title: Link `ARCHITECTURE/StepValues.md` from the README repository table and apply two of ADR-0101's unapplied round-7 nits (follow-ups of T-0298); no code
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [OD-8, "#5 D6"]
dependsOn: [T-0298]
touchesFiles: [README.md, ARCHITECTURE/decisions/ADR-0101-od8-failure-kind-change-and-step-values.md]
estimatedSize: {loc: 4, files: 2}
hq: []   # No OD is decided and no decision changes: a README link and wording touch-ups of a driver-accepted record (DRIVER §9) within its objection window. No owner-only item (#5 A/B, C-6, OD-25, OD-3). Independent of every open HQ: HQ-0021..HQ-0029 concern OD-18 sub-questions held by blocked tasks, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019 are runtime-acceptance. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py).
---
## Why

T-0298 landed ADR-0101 (OD-8 sub-question ㊱) as `defa8ee`. That record created a new top-level index, `ARCHITECTURE/StepValues.md`, and its Consequences name one document follow-up: link the index from the README document table, as T-0293 did for `ARCHITECTURE/EventKinds.md`. T-0298's reviewer approved in round 7 and left three nits unapplied, because no round 8 was allowed (see `## Result` of `PROCESS/tasks/T-0298-adr-od8-failure-kind-change-and-step-values.md`):

1. Decision 2's "every other failure kind" could carry "under the accepted records".
2. ADR-0016 decision 3 could be listed under "Not edited and now less exact" in Consequences. ADR-0101 decision 3 reads its "as long as no tool's contract uses the name" to include kinds that are no longer raised.
3. In `StepValues.md`, the `not used` state says its later record is "linked in the row", but the row has no column for that link. `EventKinds.md` has the same pattern for `not written`.

This task adds the README link and applies nits 1 and 2. It leaves nit 3 unapplied on purpose. If only `StepValues.md` got a column, the two indexes would no longer share one form. Changing both indexes is a separate question about the index form, and this task does not decide it. The task decides nothing new and writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time limit), §5 (lines 86-115: task format, naming convention, `Task:` trailer, size limit), and §9 (driver-accepted records and the objection window; grep `## 9.`).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode), "코멘트 최소화".
- `PROCESS/tasks/T-0298-adr-od8-failure-kind-change-and-step-values.md` `## Result`: the follow-ups and the three round-7 nits as recorded.
- `README.md` lines 40-56 (the "저장소 구성" table). The `ARCHITECTURE/` row is line 46, and it already holds the `EventKinds.md` link that T-0293 added.
- `ARCHITECTURE/StepValues.md` lines 1-3: the title and first paragraph, so the README description says what the file is.
- `ARCHITECTURE/decisions/ADR-0101-od8-failure-kind-change-and-step-values.md`: Status (lines 3-13), decision 2 (lines 33-37; the "kind answered without an end line" bullet is line 36), decision 3 (lines 39-46; line 42 cites ADR-0016 decision 3), and Consequences (lines 100-110; the "Not edited and now less exact" bullet is line 105).
- `ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md` decision 3 (grep `### 3.`, lines 42-60): the reservation sentence "as long as no tool's contract uses the name", which ADR-0101 decision 3 reads.

## Acceptance Criteria

1. **README link.** On line 46 of `README.md` (the `ARCHITECTURE/` row of "저장소 구성"), add one link `[StepValues.md](ARCHITECTURE/StepValues.md)` with a short Korean description in parentheses. Use the same `[name](path)(설명)` form as the other entries, for example `(기록 단계의 step 값 목록)`. Put it right after the `EventKinds.md` entry and before `reviews/`. Change nothing else in `README.md`. Before editing, run `ls ARCHITECTURE/`. If any other top-level `ARCHITECTURE/*.md` document is missing from the row, do not add it; report it in `## Result` as a follow-up.
2. **Nit 1 (ADR-0101 decision 2, line 36).** In the "A kind answered without an end line" bullet, make "every other failure kind" read as bounded by the accepted records, for example "every other failure kind under the accepted records". This is a wording change only. Its meaning must stay what decision 4 and the Status already say. Nothing else in the bullet changes.
3. **Nit 2 (ADR-0101 Consequences, line 105).** In the "Not edited and now less exact" bullet, add ADR-0016 decision 3. Give it a short note in the form of the other entries: quote its phrase "as long as no tool's contract uses the name", then say how ADR-0101 decision 3 now reads it. A name of a stored kind stays used even when the kind is no longer raised. Do not edit ADR-0016. If References (line 124) does not already list ADR-0016 decision 3, add it there. It does today ("decisions 2, 3, 4"), so expect no change.
4. **Nit 3 is not applied.** Do not edit `ARCHITECTURE/StepValues.md` or `ARCHITECTURE/EventKinds.md`. Record in `## Result` that nit 3 stays unapplied, with the reason given in Why.
5. **No decision changes.** Decisions 1-8, the alternatives, the Boundaries, the four `step` values, every failure kind and the meaning of each, every data member and `schema_version` stay as they are. If either nit cannot be applied without changing what the record decides, stop. Return BLOCKED (reason: 요구 불명확/미결 발명 의심) and do not write the edit. The Status bullets stay as they are, including the commit `07247ff` named in "It is a record, not code", because no observation changes.
6. **Files left alone.** Do not edit `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` or `ARCHITECTURE/StandardScenarios.md`. No OD status changes, and the register row, the adopted line and the ㊱ bullet already follow their recording rules. CLAUDE.md "문서 커버리지 재검사" does not apply, because neither `README.md` nor an ADR is Requirements, UsageCases or StandardScenarios. Say so in `## Result`.
7. **Document mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0299-stepvalues-readme-link-and-adr0101-nits`.
   - Run the reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) until Approve.
   - Rebase on `origin/main`, squash the branch to one commit and push it to main directly.
   - End the commit message with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0299`, in its **last paragraph**. Do not leave a blank line between these trailers and any `Co-Authored-By` line. T-0298's commit broke this rule, and `## Result` there records it as a deviation.
   - Never use `git push --force*`.
8. **No #5 notice is required**, because no OD status changes and no decision is added. If the executor judges the nit-2 entry material to the owner's objection window for ADR-0101, it may post one short English comment on #5 ending with the line `— posted by driver`, and record its URL in `## Result`.
9. **`## Result`** records:
   - the landed commit
   - the edits as applied
   - that nit 3 stays unapplied, and why
   - review rounds and any unapplied findings
   - any #5 comment URL
   - any follow-ups

   Do not start a `claude` process (D16). Run no code, test, compiler or container.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `pyproject.toml` or settings files.
- Any other wording change in `README.md`.
- Editing any ADR other than ADR-0101, in particular ADR-0016 and ADR-0100.
- `ARCHITECTURE/StepValues.md`, `ARCHITECTURE/EventKinds.md`, `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md`, `ARCHITECTURE/StandardScenarios.md`.
- OD-8 sub-questions ⑥, ⑦, ㉟ (나); OD-11, OD-10, the rest of OD-17; the run tools' stored kinds (⑲ (나), HQ-0021).
- Open PR #179 files and blocked tasks (T-0121, T-0149, T-0153, T-0155, T-0156, T-0169, T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- (doc, optional, not planned) Whether `EventKinds.md` and `StepValues.md` should give the later record of a `not written` / `not used` row its own column (nit 3). Change both indexes together, or neither.
- Any other top-level `ARCHITECTURE/` document found missing under criterion 1.

## Result
