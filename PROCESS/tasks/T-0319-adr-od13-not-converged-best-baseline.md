---
id: T-0319
title: Record an ADR on whether a timing measurement marked "not converged" may stand as a best or as a baseline (OD-13 sub-question 2, for the runs of ADR-0061 decision 1); no code
phase: P1
status: DONE
commitMode: doc
coversReq: [NFR-3, FR-1, FR-10, OD-13, OD-20, OD-28]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

ADR-0007 decision 4 makes a timing measurement that reaches `n_max` without CV < `cv_max` "usable and marked 'not converged'", and leaves one thing open: "What else a consumer does with the mark (whether such a measurement may stand as a best or a baseline) is not decided here." That is OD-13 sub-question ②. Since then the mark has been given more work. The run tools report it as `outcome` `not_converged` (ADR-0063 decision 2). It is one ground of the imprecise-timing finding (ADR-0103 decision 3, derived by ADR-0104). The owner decided on 2026-10-15 (#5, item 3) that a run in an imprecise timing environment goes on with relative figures, that improvement is judged by ADR-0007 as it stands, and that the user is warned. ADR-0103 Consequences lists ② as still open. P2 work (the Round-Manager's round 0 and baseline, P2-1; the first end-to-end run, P2-5) will need an answer. No task has tried ② before.

The task answers ② for the runs the run tools' contract already serves: the runs of ADR-0061 decision 1, meaning the first case in its local configuration and runs whose hw_profile names the mock. The question is about the measurement, and only about this: may a measurement marked not converged be the measurement that stands for a best, or for the baseline of round 0? The executor writes the ADR and reflects it in the registers. The ADR must not decide how a best is chosen, how the order "better than" works, which baseline a run uses (OD-28), or how a best is stored (`best_ref`, OD-20).

This is a design-level part of OD-13. Under DRIVER §9 the executor writes the ADR, a context-isolated reviewer's approval accepts it, and the driver posts the 7-day owner notice. As far as the planner found, it is not owner-only. Two things could still make it owner-only:

- ADR-0007 Boundaries lists "the order 'better than'" and the target quantity and direction (OD-1, #5 A-4) as owner-only.
- The 2026-10-15 owner decision (item 3) may already answer ②, or may answer it in two ways.

So before writing, the executor reads #5 and #4 for an owner sentence on unconverged or noisy measurements standing as a best or a baseline. If such a sentence answers ②, or reads two ways about it, or if the answer needs the order "better than", the choice of baseline or any other owner-only item (#5 A/B, C-6, OD-25, OD-3), the executor stops with BLOCKED (`owner-only-decision` or `requirement-unclear`) and does not decide it.

No open HQ blocks this. The blocked tasks cover other subjects: HQ-0031 / T-0318 is OD-30 on injected hypotheses, HQ-0030 is a runtime acceptance item of ADR-0103, and T-0231 is the S6 metric of OD-30. The one open PR (#179, `hilclaw/clang_build.py`) touches no file of this task.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77: executor step 5, the resume rule, the time cap, step 6), §5 (lines 86-114: format, naming rule, trailers), §8 (lines 135-139), §9 (lines 141-148).
- `CLAUDE.md`: the rules "미결은 발명하지 않는다", "문서 커버리지 재검사", "세션 진입 점검" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/Requirements.md`: FR-1 (line 19), FR-16 (line 34; "비수렴 종료" is the run ending without progress, not this mark), NFR-3 (line 46), the "행 형식" paragraph (line 84), and the rows OD-1 (line 92), OD-13 (line 104), OD-20 (line 111) and OD-28 (line 119).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`: decisions 1, 4, 5 and 7 (lines 22-27, 40-53, 60-71), Limits (lines 97-103), the worked example (lines 104-120, measurement C is not converged) and Boundaries (lines 150-159).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`: decision 8, on the stop the report states and its replay.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: decision 1 (lines 32-37, the scope of runs this task uses), and Boundaries (lines 157-170).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decisions 2 and 4 (lines 37-44, 66-76) and decision 10 (lines 145-152).
- `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md`: decisions 1 to 3 and 5 (lines 25-48, 58-65) and Consequences (lines 106-117, the list that names ② as open).
- `ARCHITECTURE/decisions/ADR-0104-od13-imprecise-timing-mark.md`: decisions 2, 3 and 5 (lines 29-57, 64-71).
- The owner decision of 2026-10-15, item 3: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913 .
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8), the OD-13 section (lines 193-212; ② is in the bullet that starts "하위 질문(ADR-0007이 넘긴 것"), the OD-20 section (from line 351), the OD-28 section (from line 415) and the OD-29 section (from line 424).
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (lines 168-170), and the scenarios that use a best or a baseline: S0, S1, S2, S3, S8, S9.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md). Before editing, list the open PRs and read #4, #5, #7 and #8 for anything on OD-13 ②. If an open PR edits the OD-13 row or the OD-13 section, stop with BLOCKED (open-PR conflict). Report the search in `## Result`.
2. **Owner-sentence search.** Search the #5 comments that carry no driver marker, and the body and comments of #4, for sentences on unconverged, noisy or imprecise measurements standing as a best or a baseline. Include the Korean forms (미수렴, 수렴, best, baseline, 기준). Quote every match in the ADR's Status or Context, or state that there is none. If a sentence decides ② or reads two ways about it, stop as **Why** says.
3. **One new ADR** under `ARCHITECTURE/decisions/`. Use ADR-0113: at planning time it was the lowest number free both on `origin/main` and on every remote branch (ADR-0112 is used on the kept T-0318 branch). Check again with `git ls-tree` over `git branch -r`. If ADR-0113 has been taken by then, use the next free number and rename the file in `touchesFiles` to match. Follow the ADR-0001 record format: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References. Keep cited text apart from the record's own choices, as recent ADRs (for example ADR-0110) do.
4. **Scope and question.** The ADR states its scope: the runs of ADR-0061 decision 1. It answers, for a measurement in a completed result of `sim.run` or `board.run` whose `outcome` is `not_converged`, whether that measurement may stand as a best and whether it may stand as the baseline of round 0. If the two get different answers, give each its reason. The answer must not depend on how a best is chosen or stored, or on which baseline a run uses. If it cannot be given without one of those, stop with BLOCKED as **Why** says.
5. **Alternatives.** At least these three are weighed against ADR-0007 decision 7, the owner decision of 2026-10-15, NFR-3 and FR-1:
   - (a) The mark changes nothing for standing.
   - (b) A not-converged measurement never stands as a best or a baseline.
   - (c) It stands only if nothing converged is available, or only with a re-measurement.

   For each, say what it needs that is still open (paired re-measurement ①, OD-20, OD-28, OD-29, OD-17). An alternative that needs an open item is not adopted.
6. **Relation to the imprecise-timing finding.** The ADR says what its answer means for a run that ADR-0103/ADR-0104 find imprecise on the measured ground, given the owner's "continue with relative figures". It must not change ADR-0103 or ADR-0104.
7. **Consequences.**
   - Say whether a code slice follows. If one does, name what it needs and what it waits on; bind no module unless the slice is ready.
   - Give the A-13 reading: no member, file, kind, `outcome` value or schema of the data plane is added or changed. If the answer would need one, stop with BLOCKED (data-plane schema change).
   - List the sentences of accepted records that become less exact, found by a search of `ARCHITECTURE/decisions/` for "not converged", "best" and "baseline". List them only; do not edit them.
   - Do a name check against the index documents (EventKinds, StepValues, BlobTypes, SpendAxes).
   - Name the runtime acceptance items, or say there are none.
8. **Register and proposals edits**, following the rules written in those files. Do not copy the wording of earlier task files.
   - `Requirements.md`, OD-13 row: follow its "행 형식". Add the new ADR as one link under `**확정분**:`, and rewrite the open part of `**잔여**:` in place to show what of ② stays open. Do not restate the record and add no dated chain. The status cell keeps its status word; widen its date range only if that paragraph asks for it.
   - `OpenDecisionProposals.md`, OD-13 section: follow its "기록 규칙". Add one adopted-record line for the new ADR. Rewrite the status at the end of ② and the status word at the head of its bullet in place. Keep the wording of the question.
   - The OD register has the same number of rows before and after.
9. **Coverage re-check** (CLAUDE.md "문서 커버리지 재검사"). Re-check the scenarios that use a best or a baseline by the rules of StandardScenarios. Then follow the first paragraph of §검사 결과: rewrite the "최근 재검사" line in place, and add a history entry only if a verdict changed or a gap was found or closed.
10. **Document checks**, reported in `## Result`:
    - every relative link in the new and edited text resolves;
    - `git diff --stat origin/main` shows only the files in `touchesFiles`;
    - `git diff --check` is clean.
11. **Doc mode** (CLAUDE.md A-13):
    - Branch `claude/T-0319-adr-od13-not-converged-best-baseline`.
    - A fresh-context reviewer cycle (dev-code-review), at most 7 rounds.
    - Then rebase on `origin/main` and push to `main` directly.
    - The commit message ends with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0319` and the `Co-Authored-By` line, in one paragraph with no blank line between them. Check them with `git interpret-trailers --parse`.
    - Delete the branch afterwards, locally and on the remote if it was pushed.
12. **Owner notice** (DRIVER §9). After landing, post the notice on #5 in English. It states what the ADR decides, the landed commit and the 7-day objection window, and ends with the line `— posted by driver`. Record the comment URL in `## Result`.

## Out of Scope

- Any change to `hilclaw/`, `tests/`, CI, settings files or the `HIL-Claw-data` repository. In particular `hilclaw/clang_build.py` and its tests (open PR #179).
- Editing any earlier ADR, including the sentences listed as less exact.
- Not decided here:
  - how a best is chosen or ordered (OD-1 rest, #5 A-4);
  - which baseline a run uses (OD-28);
  - the archive and `best_ref` (OD-20);
  - the paired re-measurement (OD-13 ①);
  - promotion (OD-15, OD-29);
  - ⑳ of OD-18;
  - ⑪ (다) and (라);
  - values for a simulator or a board (③).
- OD-30 and anything about hypotheses or cases (T-0318, HQ-0031; T-0231).
- Starting any compiler, container or `claude` process.

## Follow-ups

- If the ADR makes a code slice possible (for example a predicate over a run-tool result that says whether it may stand), a later code task.
- If the ADR's answer depends on ① or OD-28, register that link where the recording rules allow.

## Result

- **Landed**: 7dca3994175e76697cd607a35338a54fc51db609 on `main` (doc mode, direct push after rebase on `origin/main` at df1602c). Trailers checked with `git interpret-trailers --parse`: `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0319`, `Co-Authored-By`. Branch `claude/T-0319-adr-od13-not-converged-best-baseline` deleted locally and on the remote.
- **Record**: `ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md` (ADR-0113 was free on `origin/main` and on every remote branch; ADR-0112 is on the kept T-0318 branch). Decision: for the runs of ADR-0061 decision 1, the "not converged" mark alone never makes a measurement of a completed `sim.run`/`board.run` result ineligible to stand as a best or as the round-0 baseline, and no re-measurement is required first. Whether a choice rule prefers converged measurements is left to the rest of OD-1 (best) and to OD-28 / OD-18 ⑳ (baseline). The `against` question that ADR-0071 files under ② stays open.
- **Review**: 7 rounds (dev-reviewer, fresh context each). R1: narrow from "neither bars nor conditions" to eligibility only, since a preference for converged measurements is part of the owner-only choice rule; complete the less-exact list. R3: keep ADR-0071's `against` question open under ②, cut the restated ADR content from the proposals status line, widen the status-cell date range. R2, R4–R6: completeness nits and citation nits. R7: Approve, with two nits left unfixed because a further round would go past the 7-round cap: (1) decision 2 "a best is the base of the comparisons that follow it" could be conditional ("where a best is the base of later comparisons"); (2) "That is the effect NFR-3 asks for, an interval and not a cut-off" mixes a citation with this record's reading.
- **Session entry check (AC1)**: one open PR, #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`); it does not touch OD-13. Read #4, #5, #7 and #8. Nothing on OD-13 ② except #7 N7 (research, about sim results, not the mark).
- **Owner-sentence search (AC2)**: the #5 comments without the driver marker, the #5 body, and the #4 body and comments, searched for converge/not converged/noisy/imprecise/best/baseline/미수렴/수렴/노이즈/부정확/기준. No owner sentence decides ② or reads two ways about it. Quoted in the ADR: O1 (2026-10-15 item 3), #5 A-6, #5 B-4, #5 A-5 "비수렴 시" (the run that stops progressing, not this mark), #7 N7.
- **Register edits (AC8)**: OD-13 row: one link added under `**확정분**:`, the ② part of `**잔여**:` rewritten in place, status word kept. The status-cell date range went from `~18` to `~19`, as T-0302 did; the "행 형식" paragraph lists dates in the status cell. Proposals OD-13: one 채택분 line added, `→ 부분 답 … 남음 …` appended to ② with its wording kept, bullet head "일부 답함" unchanged. OD row count unchanged (30).
- **Coverage re-check (AC9)**: S0, S1, S2, S3, S8 and S9 re-checked, no verdict change and no gap. Only the "최근 재검사" line was rewritten; no history entry.
- **Document checks (AC10)**: every relative link in the new and edited text resolves. One link in `OpenDecisionProposals.md` was already broken on `origin/main` and is not part of this change. `git diff --stat origin/main` showed only the four `touchesFiles`. `git diff --check` is clean.
- **Owner notice (AC12)**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6256211016
- **Follow-ups**: no code slice (the eligibility predicate would be `outcome != "broken"`). The P2-1 code that sets the round-0 baseline and keeps the best must not treat a `not_converged` measurement as ineligible. The two R7 nits above could be fixed in a later doc touch of ADR-0113. Runtime acceptance items: none.
