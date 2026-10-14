---
id: T-0174
title: Clear the document nits left by T-0157 and T-0169 - ADR-0057 "For P2-1" says "with 0 or 10 to 15", ADR-0055 decision 3 notes that the include expectation was shown on the CI runner, StandardScenarios 2026-10-14 paragraph drops the quotes around "설계됨"; coverage re-check recorded
phase: P1
status: DONE
commitMode: doc
coversReq: [OD-18, OD-23, "CLAUDE.md 문서 커버리지 재검사"]
dependsOn: [T-0157, T-0169]
touchesFiles: [ARCHITECTURE/decisions/ADR-0057-od18-runtime-self-check-as-landed.md, ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 15, files: 3}   # one phrase in ADR-0057, one or two dated notes in ADR-0055, one quote pair plus the re-check entry in StandardScenarios
hq: []
---
## Why
Five tasks in a row (T-0169 to T-0173) carried the same small document-mode follow-up. This task does the parts of it that are document-only, are corrections or plain updates of fact, and need no design decision. It ticks **no PLAN checkbox**, changes no OD status and decides nothing.

1. **ADR-0057, Consequences, bullet "For P2-1" (line 117).** The bullet says "with 0 to 15, the report line on standard output". The exit statuses the record itself lists (decision 1, line 41) are 0 and 10 to 15 for a report and 20 for none; 1 to 9 are never produced. The phrase should read "with 0 or 10 to 15". The T-0169 executor raised this in its Result.
2. **ADR-0055 decision 3, "Flat, so that no flag is needed" (line 63).** The decision says the include expectation (clang looks for `#include "name.h"` first in the directory of the including file) "is **not verified** here, and a test of a code slice can show it with clang alone". T-0157 (PR #106) added that test, `tests/test_kernel_source.py::test_compiled_set_builds_with_clang_and_no_include_path` (line 519). Its Result line 120 says it passed on the CI runner (Ubuntu, both Python versions) and that "a later document task may say so in the record" (Result line 144). L6 (line 43) says the two "not verified" expectations are the record's own. The other one, in decision 5 (line 92, reading files written inside a container), stays not verified.
3. **StandardScenarios, 2026-10-14 (1차) paragraph (line 190).** The paragraph writes `"설계됨"` in quotes, as if quoting a verdict label. The verdict labels of the 검사 규칙 section are 지원/미결/갭, and "설계됨" is not one of them. The quotes are dropped. The T-0169 executor raised this.

Planner's judgements (the reviewer is asked to re-check each):
- **How an accepted record is edited.** No ADR has ever had a second commit. Each record says of itself "No earlier record is edited" and lists the sentences of others that became less exact. This task still edits two records in place. ADR-0057's phrase is a slip in the record's own sentence, against its own decision 1, not a change of design. ADR-0055's sentence stays as written and gains a dated note: the record anticipated the test, and T-0157 named a document task as the place to say so. To keep the edits visible, each edited ADR gains **one Status bullet** that says it was edited after acceptance on 2026-10-14 by T-0174, what changed, and that no decision, limit or boundary changed meaning. The objection windows are unchanged: ADR-0055's notice was 2026-10-13 and ADR-0057's 2026-10-14. If the reviewer judges that an accepted record must not be edited even this way, the executor drops that ADR edit, keeps the rest, and records the judgement in `## Result`. No new ADR is written for a nit.
- **Left out on purpose.** These are the other parts of the queued follow-up:
  - The ADR-0053 Consequences list (line 153): sentences of about twelve other records that became less exact. ADR-0053 files them as "follow-ups for the integrator". They are not this driver task's, and editing a dozen records goes well beyond a nit.
  - ADR-0052 Status line 8 and ADR-0050 Context line 25: "No module of `hilclaw/` measures the memory...". **No edit.** Both are facts dated to the record's day: ADR-0050 says "checked on 2026-10-13", and ADR-0052 line 8 describes the record as written. ADR-0052 Consequences line 112 already names the ADR-0050 sentence as one that "stays true until slice (1)". Slice (1) landed with T-0172 and T-0173, which is what line 112 foresaw, so nothing needs saying.
  - The `hilclaw/spec.py` module-docstring sentence ending "that ``task.objective`` is what the instance stated (ADR-0050 L2)" (lines 30-31). It can now name ADR-0053 and `hilclaw.instance.objective_of`, but changing it is **code mode** (CLAUDE.md A-13), so it stays a separate follow-up.
- **Coverage re-check (CLAUDE.md "문서 커버리지 재검사").** This task changes `ARCHITECTURE/StandardScenarios.md` and two ADRs, so the re-check runs and the result section is updated the way earlier no-change edits did it: one short clause appended to the parenthetical list of the `# 검사 결과` heading (line 168), as was done for "등록부 OD-8 행의 ... 옮김(상태·결정 변화 없음)", and one short `**2026-10-14 (2차, ...)**` paragraph after the 1차 paragraph. Expected result: no verdict change and no gap, because no scenario step, FR or OD status changes. The executor confirms this, and does not assume it.
- **Session entry check (planner, 2026-10-14, `main` at cbe25e7).** No open pull request. HQ-0013, 0014, 0016, 0017, 0018 and 0019 are `runtime-acceptance` notices that block no task. No owner answer on #5 since the last iteration. The executor repeats the CLAUDE.md "세션 진입 점검": `gh pr list`, and issues #4, #5, #7 and #8 for anything touching ADR-0055, ADR-0057 or the StandardScenarios result section, including an owner objection to either ADR. If an objection to ADR-0055 or ADR-0057 is pending, the executor stops and reports BLOCKED (requirement unclear) instead of editing.
- **A-13**: document mode. Review cycle with a context-isolated reviewer, then rebase on `origin/main`, then push straight to `main` with the trailer `Reviewed-by: reviewer agent (N rounds, Approve)` and the trailer `Task: T-0174`. No code, test, schema or settings file is touched.
- **D16**: nothing here starts any process or needs `claude`, a board or an API key.

## Required Reading
- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5. §5 gives the naming convention (branch `claude/T-0174-<slug>`, trailer `Task: T-0174`) and the size cap.
- `CLAUDE.md` "상시 규칙": comment minimisation, 문서 커버리지 재검사, 미결은 발명하지 않는다, 세션 진입 점검, 브랜치·merge 절차 (document mode).
- `.claude/skills/dev-item-address/SKILL.md`, steps 10 to 12 (reviewer cycle and document-mode landing).
- `ARCHITECTURE/decisions/ADR-0057-od18-runtime-self-check-as-landed.md`: Status (lines 3-11), decision 1's exit-status bullet (line 41), Consequences (lines 110-118).
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md`: Status (lines 3-12), L6 (line 43), decision 3 (around lines 58-66), decision 5's "not verified" sentence (line 92), Consequences (around lines 140-150).
- `PROCESS/tasks/T-0157-kernel-source-reader.md`: Acceptance Criteria line 81, Result lines 120 and 144.
- `tests/test_kernel_source.py` lines 515-535 (the clang test, read only).
- `ARCHITECTURE/StandardScenarios.md`: `## 검사 규칙` (from line 13), the `# 검사 결과` heading (line 168) and the 2026-10-13 7차, 8차 and 2026-10-14 1차 paragraphs (lines 184-190).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` "Record format" (lines 146-153).

## Acceptance Criteria
1. **ADR-0057**:
   - In the Consequences bullet "For P2-1", "with 0 to 15, the report line on standard output" reads "with 0 or 10 to 15, the report line on standard output". No other word of that bullet changes.
   - One Status bullet is added. It says the record was edited after acceptance on 2026-10-14 by T-0174, that the edit corrected that phrase to match decision 1, and that no decision changed meaning.
2. **ADR-0055**:
   - Decision 3's sentence keeps its words, "**not verified** here" included, and gains a short dated note. The note says that on 2026-10-14 a test of T-0157 (`tests/test_kernel_source.py`, the compiled set of an `output/` with `a.c` including `"pack.h"`, built by `hilclaw.clang_build.build` with no include-path flag) showed the expectation on the CI runner (Ubuntu, clang) only. It also says that no other machine kind of C-7 was observed, so the conditional "If it did not hold, ..." still stands for those.
   - L6 gains at most a short pointer to that note, if the executor judges that L6 otherwise reads as wrong.
   - Decision 5's "not verified" (line 92) is unchanged.
   - One Status bullet is added, in the same form as in ADR-0057.
   - No decision, limit, boundary or Alternatives row changes meaning.
3. **StandardScenarios**:
   - In the 2026-10-14 (1차) paragraph, `"설계됨"` becomes `설계됨`. Nothing else in that paragraph changes.
   - The coverage re-check is run by the 검사 규칙 over the scenario steps the two ADRs touch: for ADR-0057, the steps named in the 1차 paragraph; for ADR-0055, those named in the 2026-10-13 8차 paragraph.
   - The result is recorded as a clause appended to the `# 검사 결과` heading list and as one `**2026-10-14 (2차, ...)**` paragraph. That paragraph names the three edits and gives the verdict: no change and no gap, if that is what the re-check finds.
   - No scenario step or 비고 row is edited.
4. No other file changes. In particular, `Requirements.md` and `OpenDecisionProposals.md` are untouched, since no OD row or status changes, and `README.md` is untouched.
5. A context-isolated reviewer approves. The commit lands on `main` in document mode with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0174`. `git diff --check` is clean and line endings are LF.
6. `## Result` records:
   - the landed commit;
   - the review rounds;
   - the re-check outcome;
   - whether the L6 pointer was added;
   - any reviewer judgement on editing accepted records in place.

## Out of Scope
- The ADR-0053 Consequences list of less-exact sentences in other records, which belongs to the integrator.
- Any edit of ADR-0050 or ADR-0052 (see Why).
- `hilclaw/spec.py` or any other code or test file (code mode).
- Any new ADR, OD status change or PLAN checkbox.
- Closing any runtime acceptance item.
- The OD-13 sub-question ⑩ and ADR-0052 decision 7 (c) work, which waits on PLAN P1-1/P1-8.

## Follow-ups
- (planner, code mode, small) The `hilclaw/spec.py` module-docstring sentence "that ``task.objective`` is what the instance stated (ADR-0050 L2)" can now say that `instance.json` has the member (ADR-0053; `hilclaw.instance.objective_of`) and that nothing compares the two yet. Docstring only.
- (integrator) The less-exact sentences ADR-0053 Consequences line 153 lists in other records.
- (planner, later) OD-13 sub-question ⑩ and ADR-0052 decision 7 (c) wait for the run-tool contracts (PLAN P1-1) and the instance member (PLAN P1-8).

## Result
- Commit `37f4df1` on `main` (document mode, fast-forward from `f4c5066`), trailers `Reviewed-by: reviewer agent (2 rounds, Approve)` and `Task: T-0174`; task branch deleted on the remote and locally.
- Review: 2 rounds with a fresh-context dev-reviewer. Round 1 requested changes (minor: the 2nd paragraph omitted resume steps S2-3 and S3-2 - added with the reason they are unaffected; nit: name the CI run in the ADR-0055 note - run 38430280742 named). Round 2 Approve, no findings.
- ADR-0057: "For P2-1" bullet now reads "with 0 or 10 to 15"; a Status bullet records the post-acceptance edit.
- ADR-0055: decision 3 unchanged; a dated note (2026-10-14, T-0174) records that the T-0157 clang test showed the include expectation on the CI runner (Ubuntu, clang) only (push run of 2026-10-13 on `e8c19ce`); other C-7 machine kinds stay not verified. Status bullet added; no L6 pointer (L6 still true).
- StandardScenarios: quotes around "설계됨" removed in the 1st paragraph; a 2026-10-14 (2nd) paragraph and a heading-list clause added.
- Coverage re-check over the steps of the 1st paragraph and the 2026-10-13 8th paragraph (resume steps included): no verdict change, no gap; no FR, OD status or registered sub-question changed.
- Follow-ups: unchanged (the `hilclaw/spec.py` docstring, code mode; the ADR-0053 less-exact list, integrator; OD-13 ⑩ / ADR-0052 7(c)).
