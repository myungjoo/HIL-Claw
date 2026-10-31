---
id: T-0525
title: Bring the registers and usage documents up to landed ADRs and correct four ADR errors (HQ-0080 groups E and F)
phase: P2
status: TODO
commitMode: doc
coversReq: [HQ-0080, OD-6, OD-8, OD-28, C-7]
dependsOn: [T-0523, T-0524]
touchesFiles:
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/UsageCases.md
  - ARCHITECTURE/StandardScenarios.md
  - README.md
  - ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md
  - ARCHITECTURE/decisions/ADR-0147-od19-first-case-spend-path-check.md
  - ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md
  - ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md
estimatedSize: {loc: 40, files: 9}
hq: []
---
## Why

The owner approved groups E ("living documents") and F ("factual errors in ADRs") of the PLAN hold section in HQ-0080. The lines are not judged again here, and P2-15 does not need the work. HQ-0080 dropped the ADR wording parts of the group E lines, so only the living documents named below change for them. The group F edits correct the named sentences in place; they decide nothing new and need no §9 notice.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5.
- `CLAUDE.md`, "세션 진입 점검" and "문서 커버리지 재검사".
- The recording rules:
  - `ARCHITECTURE/Requirements.md`, "행 형식";
  - `ARCHITECTURE/OpenDecisionProposals.md`, header "기록 규칙";
  - `ARCHITECTURE/StandardScenarios.md`, first paragraph of "검사 결과".
- For group E: `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md` decision 4 and Consequences; `ADR-0124-od23-round-manager-run-file-access.md` Consequences; `ADR-0137-od23-first-case-coder-process-start.md` decisions 3 to 6 and Consequences.
- For group F: each ADR at the place named below, and `ADR-0133-od23-first-case-round-promotion.md` decision 4 and `ADR-0018`'s decision 2.

## Acceptance Criteria

Group E. Follow the recording rules: one link per ADR not yet linked, open parts rewritten in place, no restatement of the record and no dated paragraphs. An ADR link already in the section or row is not added again.

1. **OD-28, T-0335 line.** In the register row's `잔여` and the question's `남음` in § OD-28, "round budget 계상 — ADR-0032·OD-8 ㉙" is narrowed: ADR-0121 answered the round-0 count for the runs of ADR-0120 decision 1, so what stays open is the count outside those runs. Add the ADR-0121 link to the row's `확정분` and a `채택분` line in the section. Keep the row's status word unless the rules require otherwise.
2. **OD-8 ⑭, T-0341 line.** In the state at the end of the question, "작성자가 어디서 도는지는 OD-23" is narrowed by ADR-0124: for its runs the replacement runs in the server process of the turn session. What stays open stays in `남음`.
3. **OD-8 "제안으로 남는 부분", T-0375 line.** "이미지와 코더 프로세스를 띄우는 방법" and the question of scratch files on Linux are narrowed to what ADR-0137 leaves open for the first case and outside it. Read decisions 3 to 6 for the boundary; do not restate them.
4. **UC-1 "선행조건" and the README line "instance의 선행조건", T-0375 line.** Add that a coder call also needs the image and the token of ADR-0137 decisions 4 and 5. Link the ADR; do not repeat what the image holds. Names are the ADR's: `HILCLAW_STANDIN_IMAGE` belongs to the code, so check the current name in `hilclaw/standin_image.py` if you cite one.
5. **OD-6 ①, T-0429 line.** Move the old "확정: … 미결 그대로: …" form to the state form of the rules, "→ 부분 답: … 남음: …", keeping the question's wording and every link. The meaning does not change.

Group F. Change only the named sentence and what its correction needs. First check the claim against the source; if the sentence is right after all, leave it and say so in `## Result`.

6. **ADR-0135, T-0368 line.**
   - Decision 5 "Why not go on": the citation of ADR-0133 decision 4's reason for rejecting the alternative follows ADR-0133's own text (the re-entered round of OD-17 and the repeated refusal).
   - "The cost, plainly": add that a damaged log line makes each turn repeat the round's work until `run_file_invalid`.
   - Add the memo on the order of checks ③ and ④ that the review asked for, if that order is not already stated.
7. **ADR-0147 decision 4, T-0405 line.** The rule on an unknown top-level member of `instance.json` cites ADR-0018 decision 2, not ADR-0012 decision 2. Keep the ADR-0012 citation for `STATE.json` if the sentence needs it. If ADR-0018 decision 2 does not hold that rule, name the place that does.
8. **ADR-0158 decision 9, T-0435 line.** "no value set changes this much at that width" is narrowed to the statement that holds, "for every square" (of the value range the decision states), because a set with one dominant square is not covered.
9. **ADR-0163, T-0451 line.**
   - Decision 7 "Every kind": the largest relative difference of a correctly rounded bf16 output is 1/257, not 2^−8. Check the arithmetic and the sentence's "against a value of at least 2^e".
   - Alternatives row 4: the first case takes only the magnitude, not the whole value, from `word >> 41`.

Both groups.

10. **Coverage recheck.** Recheck the scenarios the changed documents touch by the rules of `ARCHITECTURE/StandardScenarios.md`. Update "최근 재검사" in place. Add a history entry only if a verdict changes; none is expected.
11. **No decision is made and no open question is closed** beyond what the landed ADRs already answer. If a correction would need a new choice, leave that sentence, name it in `## Result`, and return BLOCKED if it belongs to the owner.
12. **Document mode.** Reviewer cycle, rebase on `origin/main`, push to main with the `Reviewed-by` trailer and `Task: T-0525`. Before editing, make the session-entry check of `CLAUDE.md`.

## Out of Scope

- ADR sentences outside criteria 6 to 9, including the "Less exact" lists of the group E lines, which HQ-0080 dropped.
- Group D (T-0399 and T-0506 lines), and the hold lines HQ-0080 did not list.
- Any code or test.

## Follow-ups

## Result
