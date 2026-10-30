---
id: T-0322
title: Record an ADR on whether a measurement marked "not converged" may be the `against` side of a hypothesis verdict's comparison (rest of OD-13 sub-question 2, for the runs of ADR-0061 decision 1); no code
phase: P1
status: DONE
commitMode: doc
coversReq: [NFR-3, FR-17, OD-13, OD-30]
dependsOn: [T-0319]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0114-od13-not-converged-against.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 160, files: 4}
hq: []
---
## Why

ADR-0071 defines the `comparison` evidence entry of a hypothesis verdict. In that entry, `measured` is the B side of one application of ADR-0007 decision 7 and `against` is the A side. ADR-0071's Boundaries leave one question open and file it under OD-13 sub-question ②: "whether a 'not converged' measurement may serve as `against`". ADR-0071 decision 4 already lets a not-converged measurement appear in a comparison entry, because ADR-0007 decision 4 calls it "usable". It does not say whether that measurement may be the base.

ADR-0113 (T-0319, main `7dca399`; edited by T-0320 and T-0321) answered the best and baseline part of ② for the runs of ADR-0061 decision 1. It left `against` open on purpose (its decision 3 bullets, Consequences line 93 and Boundaries line 102), because `against` belongs to the verdict (OD-30) and is neither a best nor a baseline. The OD-13 register row and the OD-13 section of OpenDecisionProposals now list exactly this as part of what remains of ②. The last driver iteration named it as the next candidate.

This is a design-level part of OD-13, so it is closed by DRIVER §9: the executor writes the ADR, a context-isolated reviewer approves it, and the driver posts the owner notice. The question is about eligibility only: may such a measurement stand on the A side? Which attempt `against` must be (the base of the comparison) is a separate question, open under OD-20, OD-28 and OD-30 (ADR-0071 decision 4, "Open, and not filled here"). The answer must hold whatever base is chosen later.

The question differs from ADR-0113's in one way that the ADR must weigh. A wide interval on the A side makes `not_different` more likely, and ADR-0071 decision 4 maps `not_different` to `inconclusive`, never to `refuted`. So the cost of a noisy base may fall on how often a verdict can be reached, not on wrong verdicts. The ADR must show this from the cited rules and not assume it.

No open HQ covers this. HQ-0031 (T-0318) is about whether injected hypotheses must be tested. HQ-0023 (T-0231) is about the S6 metric. HQ-0030 is a runtime acceptance item of ADR-0103. The only open PR, #179, touches `hilclaw/clang_build.py` and `tests/test_clang_build.py`, which this task does not touch. The kept branches of T-0231 and T-0318 edit the OD-30 row and section, not OD-13. This task leaves the OD-30 entries alone.

## Required Reading

- `PROCESS/DRIVER.md` §3 (lines 63-77: executor step 5, resume rule, time cap, step 6), §5 (lines 86-114: format, naming, trailers, size cap), §8 (lines 135-139) and §9 (lines 141-148).
- `CLAUDE.md`: "미결은 발명하지 않는다", "세션 진입 점검", "문서 커버리지 재검사" and "브랜치·merge 절차" (document mode).
- `ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md`: the whole record (112 lines). It is the sibling answer. Reuse its scope and terms, and do not repeat its reasons.
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: Status (lines 3-11), decision 3 (lines 50-66, the `comparison` entry), decision 4 (lines 68-75: counted comparisons, the three values, "Not different never refutes", the open base), decision 5 (lines 77-80), the example (lines 86-112) and Boundaries (lines 141-153).
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md`: decision 4 (lines 40-47), decision 7 (lines 60-71), decision 10 (lines 97-103) and Boundaries (lines 150-159).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: decision 1 (lines 32-37).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decisions 2 to 4 (lines 37-76).
- `ARCHITECTURE/decisions/ADR-0103-od13-imprecise-timing-detection.md` decisions 3 and 5, and `ARCHITECTURE/decisions/ADR-0104-od13-imprecise-timing-mark.md` decisions 3, 4 and 6. Read only what ADR-0113 decision 4 cites from them.
- `ARCHITECTURE/Requirements.md`: FR-17 (line 35), NFR-3 (line 46), the "행 형식" paragraph (line 84), and the rows OD-13 (line 104) and OD-30 (line 121; read it, do not edit it).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8) and the OD-13 section (lines 193-213). ② is in the bullet that starts "하위 질문(ADR-0007이 넘긴 것". Also skim the OD-30 section (from line 435) for any proposal text about the base of a comparison or noise.
- `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과 (lines 168-172), and the scenarios that use hypothesis verdicts (search for FR-17 and "판정").
- The owner decisions of 2026-10-15, item 3 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913), and of 2026-10-13 on hypotheses (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136462569).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: "Record format".

## Acceptance Criteria

1. **Entry check.** Before any edit, list the open PRs and look at issues #4, #5, #7 and #8 for anything on `against`, the base of a verdict's comparison, or not-converged measurements in verdicts. If an open PR edits the OD-13 row, the OD-13 section or ADR-0071, stop and return BLOCKED (open-PR conflict). Report what you found in `## Result`.
2. **Owner sentences.** Search the #5 comments without the driver marker, and #4, for owner text on noisy or not-converged measurements as the base of a hypothesis judgement. Search in English and Korean (for example: against, base, verdict, hypothesis, 판정, 가설, 기준, 미수렴, 노이즈). Quote what you find, or say that nothing was found. If an owner sentence answers the question, reads two ways about it, or makes it depend on an owner-only item (#5 A/B, C-6, OD-25, OD-3), stop and return BLOCKED (`owner-only-decision` or `requirement-unclear`). Do not choose a reading.
3. **The record.** Write one new ADR as `ARCHITECTURE/decisions/ADR-0114-od13-not-converged-against.md`. ADR-0114 was the lowest number free on `origin/main` and on every remote branch when this task was planned (ADR-0112 is on the kept T-0318 branch, ADR-0113 is on main). Check again over `git branch -r`. If the number is taken, use the next free one and report the new path in `## Result`. Use ADR-0001's record format, and keep cited text apart from the record's own choices.
4. **What it answers.** The scope is the runs of ADR-0061 decision 1, the same scope as ADR-0113. The ADR answers one question: may a measurement from a completed `sim.run` or `board.run` result with `outcome` `not_converged` be named as `against` in a `comparison` entry, and may that entry count under ADR-0071 decision 4? The ADR must not choose which attempt `against` is. It must not change the three verdict values or their rule, and it must not change ADR-0071, ADR-0113 or ADR-0007. If no answer is possible without fixing the base, stop and return BLOCKED (`requirement-unclear`).
5. **The asymmetry.** From ADR-0007 decisions 4 and 7 and ADR-0071 decision 4, state what a wide A-side interval does to each of `supported`, `refuted` and `inconclusive`. Say whether that differs from the effect ADR-0113 found for a best or a baseline. Say whether a not-converged `measured` side is already admitted, citing the sentence in ADR-0071 decision 4.
6. **Alternatives.** Weigh at least these, each with what it would still need that is open:
   - the mark does not bar the measurement from `against`;
   - it bars the measurement from `against`;
   - it may be `against` but the comparison does not count;
   - it may be `against` only after a re-measurement (sub-question ①).

   An alternative that needs an open item is not adopted.
7. **Consequences.**
   - Say whether a code slice follows; for example, whether the verdict validator that ADR-0071 Consequences allows would gain or lose a check. Bind no module.
   - Give the A-13 reading. If the answer needs a new or changed member, value or schema of the data plane, stop and return BLOCKED (data-plane schema change).
   - List the sentences of accepted records that become less exact: ADR-0071 Boundaries, ADR-0113 (Status line 9, Consequences line 93, Boundaries line 102), and any others a search of `ARCHITECTURE/decisions/` for "against" and "not converged" finds. Only list them; do not edit those records.
   - Do a name check against EventKinds, StepValues, BlobTypes and SpendAxes.
   - Name the runtime acceptance items, or say there are none.
8. **Register edits.** Follow the rules written in the three files themselves. Do not reuse wording from earlier task files.
   - `Requirements.md`, OD-13 row: follow "행 형식" (line 84). The record gets one link under `**확정분**:`, and the `**잔여**:` text about ② is rewritten in place so it no longer lists `against` for this scope. Do not restate the record, add no dated text, and leave the OD-30 row unchanged.
   - `OpenDecisionProposals.md`, OD-13 section: follow "기록 규칙" (line 8). Add one adopted-record line, and rewrite the state at the end of ② in place. Keep the question's wording and add no dated note.
   - The register keeps the same number of rows.
9. **Coverage re-check.** The Requirements row changes, so re-check coverage by the StandardScenarios rules for the scenarios that rely on hypothesis verdicts. Then follow the first paragraph of §검사 결과: rewrite the "최근 재검사" line in place, and add a history entry only if a verdict changed or a gap opened or closed.
10. **Checks**, reported in `## Result`: every new or edited relative link resolves; `git diff --stat origin/main` lists only the `touchesFiles` paths, with the ADR path adjusted if criterion 3 renamed it; `git diff --check` is clean; LF line endings are kept.
11. **Document mode** (CLAUDE.md A-13):
    - work on branch `claude/T-0322-adr-od13-not-converged-against`;
    - run the context-isolated reviewer cycle (dev-code-review, at most 7 rounds) to Approve;
    - rebase on `origin/main`, squash to one commit and push it to `main` (never `git push --force*`);
    - end the commit message with one trailer paragraph: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0322` and the Co-Authored-By line;
    - confirm with `git interpret-trailers --parse` that git parses the trailers.
12. **Owner notice.** OD-13 gains an accepted part, so `## Result` gives the one-paragraph text of the DRIVER §9 notice for #5. The driver posts it.
13. **D16.** Start no `claude` process, compiler, container, timing run or test. `## Result` says so.

## Out of Scope

- Which attempt `against` must be (OD-20, OD-28, OD-30), `best_ref`, promotion (OD-15, OD-29), and any choice rule for a best (the rest of OD-1, owner-only).
- ② outside the runs of ADR-0061 decision 1 (simulator, board, other configurations; OD-13 ③), the paired re-measurement (①), and an equivalence rule that would let `not_different` refute.
- Editing ADR-0007, ADR-0071, ADR-0113 or any other accepted record; the OD-30 row and section; anything under `hilclaw/`, `tests/`, CI or settings.
- Anything blocked by an open HQ, including HQ-0031 and the kept branches of T-0231 and T-0318.
- The files of open PR #179.

## Follow-ups

- If the reviewer finds a slip in ADR-0113 or ADR-0071 that this record exposes, list it here as a follow-up, and do not edit those records.

## Result

- **Landed**: main `b0bcd10` (document mode, one squashed commit, pushed fast-forward from `938defb`; task branch `claude/T-0322-adr-od13-not-converged-against` deleted locally and on origin). Branch commits before the squash: `8fecc00`, `d54466f`, `eb9b433`, `5c118d9`, `62fc7c4`, `cdd244a`, `2524992`. `git interpret-trailers --parse` gives `Reviewed-by: reviewer agent (6 rounds, Approve)`, `Task: T-0322` and the Co-Authored-By line.
- **Review**: 6 rounds of a context-isolated `dev-reviewer`. Round 1 Approve with 2 non-blocking items and 1 nit (O1 read beyond its words in Limit 1; ADR-0023 Boundaries missing from the less-exact list; FR-17 markup). Round 2 Request changes (blocking: decision 3 read O1 and FR-17 as "needing verdicts"; less-exact list incomplete; a heading broader than its body; code observation incomplete). Rounds 3 to 5 Approve with nits, all fixed. Round 6 Approve, no findings.
- **Entry check (criterion 1)**: one open PR, #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`); no PR edits the OD-13 row, the OD-13 section or ADR-0071. Issues #4, #5, #7 and #8 hold nothing on `against`, the base of a verdict's comparison, or not-converged measurements in verdicts. Landed check: no `Task: T-0322` commit on `origin/main` and no PR for T-0322 before this run.
- **Owner sentences (criterion 2)**: the #5 comments without the driver marker, the #5 and #4 bodies and the #4 comments were searched in English and Korean (against, base, verdict, hypothesis, noise, noisy, not converged, unconverged; 판정, 가설, 기준, 미수렴, 노이즈). Nothing answers the question or reads two ways about it. The closest sentences are the owner decision of 2026-10-13, points 1 and 4 (a verdict exists; injected hypotheses get the same verdict), and item 3 of 2026-10-15 (the run goes on in a noisy environment). The record quotes them and does not use them as the answer. #7 §5 G2 (paired re-measurement) is research, not an owner decision.
- **Record**: `ARCHITECTURE/decisions/ADR-0114-od13-not-converged-against.md`. ADR-0114 was still free on `origin/main` and on every remote branch. Answer: a `not_converged` measurement is eligible to be `against`, and the entry counts exactly as ADR-0071 decision 4 says; the base stays open. Decision 2 derives the effect on each value. A wide A side lowers `supported` and, ordinarily, `refuted`, and raises `inconclusive`. One path goes the other way: in a mixed set with a contrary comparison, noise can turn `inconclusive` into `refuted`. That path exists for any `not_different` comparison, and a not-converged `measured` side is already admitted ("is not excluded here", ADR-0071 decision 4). Alternatives (b) bar, (c) record but not count, (d) re-measure first and (e) leave open each need open items and are not adopted.
- **Register edits**: the OD-13 row gains one `**확정분**` link, and its `**잔여**` text on ② now reads "그 밖의 run에 대한 것(②)". The OD-13 section gains one 채택분 line, and the state at the end of ② now reads "남음: 그 밖의 run에 대한 ②." The OD-30 row and section are unchanged, and the register keeps its row count.
- **Coverage re-check**: S0, S5, S6, S8 and S11 (hypothesis verdicts) and S9 (noise) were re-checked. No verdict changed and no gap opened or closed. The "최근 재검사" line was rewritten in place, with no history entry.
- **Checks**: every new or edited relative link resolves. `git diff --stat origin/main` before landing listed only the four `touchesFiles` paths. `git diff --check` is clean, and all four files are LF with no CR.
- **D16**: no `claude` process, compiler, container, timing run or test was started.
- **Owner notice text for #5 (DRIVER §9; the driver posts it)**: "OD-13 (measurement and noise policy) gains an accepted part under DRIVER §9: ADR-0114 (https://github.com/myungjoo/HIL-Claw/blob/main/ARCHITECTURE/decisions/ADR-0114-od13-not-converged-against.md, landed in b0bcd10). It covers the runs of ADR-0061 decision 1, meaning the first case's local configuration and the mock. In those runs a timing measurement marked "not converged" may be the `against` (base) side of a comparison in a hypothesis verdict, and the comparison counts exactly as ADR-0071 decision 4 says. A noisy base mostly turns verdicts into `inconclusive`. In a mixed set it can also hide an as-expected comparison and leave a contrary one to refute; that path exists for any not-different comparison, whichever side is noisy. Which attempt the base must be stays open (OD-20, OD-28, OD-30), and nothing in the data plane changes. You may object within 7 days of this notice; an objection creates a task that reverts the record. — posted by driver"
- **Follow-ups**: none. The reviewer found no slip in ADR-0113 or ADR-0071. The sentences of accepted records that are now less exact are listed in ADR-0114 Consequences and were not edited, as the task requires.
