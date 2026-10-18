---
id: T-0307
title: Link `ARCHITECTURE/BlobTypes.md` from the README document table and apply the three unapplied round-7 findings of T-0306 to ADR-0105 (decision 9 review check, Consequences reviewer check, Terms on owner-decision commits); no code
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-8, "ADR-0105", "#5 D6"]
dependsOn: [T-0306]
touchesFiles: [ARCHITECTURE/decisions/ADR-0105-od8-blob-type-vocabulary.md, README.md]
estimatedSize: {loc: 8, files: 2}
hq: []   # Wording corrections of a driver-accepted design record (DRIVER §9) within its objection window, and a README link that ADR-0105 Consequences names as a follow-up. No owner-only item (#5 A/B, C-6, OD-25, OD-3), no new decision, no value of `type` named (OD-23 untouched). Independent of every open HQ: HQ-0021..HQ-0029 concern run-tool end-line kinds, OD-30, instance-start members, profiler.collect, the build log, clang_build/local_run env checks and a shared JSON helper; HQ-0013, HQ-0014, HQ-0016..HQ-0019 and HQ-0030 are runtime-acceptance, and this task tries none of their facts. No overlap with open PR #179 (hilclaw/clang_build.py, tests/test_clang_build.py) or with the touchesFiles of any non-DONE task.
---
## Why

T-0306 landed ADR-0105 (the vocabulary part of OD-8 sub-question ⑥) as `2aa6bc8`, with the reviewer's round-7 Approve. Two kinds of follow-up are left:

1. **README link.** ADR-0105 created the index `ARCHITECTURE/BlobTypes.md`. Its Consequences (line 112) name one document follow-up: "link `ARCHITECTURE/BlobTypes.md` from the README document table, as `EventKinds.md`, `StepValues.md` and `SpendAxes.md` are."
2. **Three round-7 findings.** The reviewer raised them in round 7, the last round allowed. T-0306 `## Follow-ups` (line 68) records them:
   - (1, minor) Decision 9, second bullet (line 82). The review check reads "names a kind that a `defined` value names, or exactly the kind of a `not written` value". Decisions 3 and 6 ask more: no `defined` value names **any of its content**, other than the values the record sets to `not written` in its landing commit. The review check should say that.
   - (2, nit) Consequences, "For a defining record" (line 107). The list of what a defining record does should also say that it checks that no `defined` value names any of its content (decisions 3 and 6).
   - (3, nit) Terms (line 23). A value defined by an owner decision has the document commit that records the decision as its defining record. The Terms do not say when such a commit counts as accepted. They should say that it counts as accepted while it is not reverted.

This task applies these four edits. It decides nothing new and writes no code.

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 (line 72: executor procedure, resume rule, time limit), §5 (lines 86-115: task format, naming convention, `Task:` trailer, size limit) and §9 (lines 141-149: driver-accepted records and the objection window).
- `CLAUDE.md` "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `PROCESS/tasks/T-0306-adr-od8-blob-type-vocabulary.md` `## Follow-ups` (lines 65-69) and `## Result` (lines 71-78).
- `ARCHITECTURE/decisions/ADR-0105-od8-blob-type-vocabulary.md`: Status (lines 3-12), Terms (line 23), decision 3 (lines 38-43), decision 6 (lines 58-63), decision 8 (lines 73-77), decision 9 (lines 79-83), Consequences (lines 103-112).
- `ARCHITECTURE/BlobTypes.md` (10 lines). Read it to keep the wording of the edits consistent with it. Do not edit it.
- `README.md` line 46 (the `ARCHITECTURE/` row of the document table, which links `EventKinds.md`, `StepValues.md` and `SpendAxes.md`).

## Acceptance Criteria

1. **README link.** In `README.md` line 46, add a link to `ARCHITECTURE/BlobTypes.md` right after the `SpendAxes.md` link. Use the same pattern: `[BlobTypes.md](ARCHITECTURE/BlobTypes.md)(<short Korean description>)`, for example `(artifacts.json blob type 값 목록)`. Change nothing else in the README.
2. **Finding 1 (decision 9, second bullet).** Edit the bullet in place so that the review catches a defining record that "names any content that a `defined` value names (other than the values it sets to `not written` in its landing commit), or exactly the kind of a `not written` value". Keep the rest of the bullet: no row added, a taken value reused, and the constant that the code task adds.
3. **Finding 2 (Consequences, "For a defining record").** Add to the list of what a defining record does that it checks that no `defined` value names any of its content (decisions 3 and 6). Keep the existing items and the reviewer sentence. If the reviewer sentence ("the disjointness against the `defined` rows") already says the same thing, do not repeat it.
4. **Finding 3 (Terms).** Add one short clause to Terms: the document commit that records an owner decision counts as accepted while it is not reverted. This applies the existing rule of decision 2 ("accepted", "reverted") to that kind of defining record. It adds no new state or rule. If it would need another decision to change (for example decision 7's state `reverted` or decision 8's second sentence), stop and return BLOCKED (reason: 요구 불명확/미결 발명 의심) instead of widening the task.
5. **No decision changes.** Decisions 1-10, the adopted alternative (a), the Alternatives table, Boundaries and the Status bullets stay as they are in meaning. No value of `type` is named. If an edit would change what the record decides, stop and return BLOCKED (reason: 요구 불명확/미결 발명 의심).
6. **Other files.** No other file changes. Do not edit `ARCHITECTURE/BlobTypes.md`, `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` or `ARCHITECTURE/StandardScenarios.md`. The OD-8 register row and the OD-8 section already link ADR-0105 under their recording rules (the register's "행 형식", the OpenDecisionProposals header's "기록 규칙"). None of these edits changes the topic of that link. Because none of Requirements, UsageCases or StandardScenarios changes, no coverage re-check is owed (CLAUDE.md "문서 커버리지 재검사"). If the executor finds that one of those files, or `BlobTypes.md`, must change after all, stop and return BLOCKED instead of widening the task.
7. **No history.** Do not add a dated paragraph or an edit history. Leave the observation "at `b6ac0a9`" (Status, line 10) as it is.
8. **Document mode** (CLAUDE.md A-13):
   - branch `claude/T-0307-blobtypes-readme-link-and-adr0105-r7`;
   - reviewer cycle (dev-code-review, context-isolated, at most 7 rounds) until Approve;
   - rebase on `origin/main` and squash the branch into one commit;
   - push to main directly, without force;
   - the commit message's last paragraph holds `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0307` and the attribution line, with no blank line between them.
   Files use LF only and `git diff --check` is clean.
9. **No #5 notice** is required, since no OD status changes and no decision is added.
10. **D16.** No `claude` process is started. No code, test, compiler or container is run. `## Result` records the four edits as applied, the review rounds and any finding left unapplied.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, `pyproject.toml` or settings files. A writer-side check of `type` against the index stays with the first defining record (ADR-0105 decision 9, Consequences).
- Any edit of ADR-0005, ADR-0097, ADR-0098, ADR-0099, ADR-0101, ADR-0102 or any other ADR. ADR-0105 Consequences lists their less exact statements, and they stay unedited.
- Any edit of `EventKinds.md`, `StepValues.md`, `SpendAxes.md` or `BlobTypes.md`, including the optional link column (T-0299 follow-up).
- Naming any value of `type`, OD-23, OD-8 sub-question ⑦, OD-28, OD-11 and GC.
- Open PR #179 files and the blocked tasks (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243, T-0264, T-0284, T-0286).

## Follow-ups

- None expected. Record in `## Result` any new finding left unapplied.

## Result

- DONE. Landed in document mode as `6b3ef6a` on main (fast-forward from `f2fd615`), `Reviewed-by: reviewer agent (3 rounds, Approve)`; branch `claude/T-0307-blobtypes-readme-link-and-adr0105-r7` deleted (remote and local).
- Four edits applied: README line 46 links `[BlobTypes.md](ARCHITECTURE/BlobTypes.md)(artifacts.json blob type 값 목록)` after `SpendAxes.md`; ADR-0105 Terms adds "that commit counts as accepted while it is not reverted"; decision 9 second bullet now reads "The review of a defining record catches one that adds no row, reuses a taken value, names any content that a `defined` value names (other than the values it sets to `not written` in its landing commit), or names exactly the kind of a `not written` value" (split into two sentences, constant sentence kept); Consequences "For a defining record" adds "checks that no `defined` value names any of its content, other than the values it sets to `not written` in its landing commit (decisions 3 and 6)", reviewer sentence kept.
- Review: round 1 approve with one nit (ambiguous `which` in Terms; applied), round 2 approve with one nit (long decision 9 bullet; split, applied), round 3 approve with no findings. No finding left unapplied.
- No other file changed; no decision changed, no value of `type` named; no coverage re-check owed; no #5 notice needed. No code, test or compiler run; no `claude` started (D16).
