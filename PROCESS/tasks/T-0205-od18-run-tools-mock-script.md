---
id: T-0205
title: Record ADR-0066, the mock's side of sim.run / board.run - how the mock's operation asks its script, what the default script answers and the rule of its report (ADR-0061 Consequences item (5), OD-18)
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-10, OD-18, OD-13]
dependsOn: [T-0191, T-0195, T-0199, T-0201, T-0203, T-0204]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 270, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` now have five records: ADR-0061 (split), ADR-0062 (call identity), ADR-0063 (result members), ADR-0064 (timing seed) and ADR-0065 (the form between the tool function and an operation, and the answer of neither form). Code exists for the objective admission (`hilclaw/run_objective.py`), the step values (`hilclaw/run_identity.py`), the result builder (`hilclaw/run_result.py`), the seed draw (`hilclaw/run_seed.py`), the judging of a report (`hilclaw/harness/timing.py` `judge_report`), the timing parameters (`hilclaw/run_parameters.py`) and the check of an operation's answer (`hilclaw/run_operation.py`, T-0204, `8ab70a9`).

ADR-0061 Consequences lists the next contract slices; item (5) is "the mock's operation, its script and a default script". ADR-0065 Consequences repeats it as the first still-open slice and lists it under "Not yet possible" (the mock's operation) and Boundaries. ADR-0061 decision 1 put a run at the mock in scope for these tools, so the contract tests of P1-1 can run the judging of `judge_report` over the mock. For `correctness.check` the same slice was ADR-0044 (and its code `hilclaw/mock_check.py`). Without this slice the mock cannot answer either run tool, and the tool functions cannot be tested end to end over the mock.

This is part of OD-18, a design-level OD, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9 this task therefore writes the ADR. Item (6) of ADR-0061 Consequences (OD-18 ⑲ (가) to (라)) and item (7) (the spend) are not in this task.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0205-<slug>`, trailer `Task: T-0205`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", the 문서 커버리지 재검사 rule, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase, direct push to main with the `Reviewed-by` trailer), the BLOCKED reasons (a data-plane schema change is one), 코멘트 최소화, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146).
- The model, whole: `ARCHITECTURE/decisions/ADR-0044-od18-correctness-check-mock-script.md` (186 lines; decisions 1 to 6 are the pattern: how the mock's operation asks its script, what the default script answers, the rule of its report, what a script of a test can express, the two tables, the Limits, and how it kept fault injection in a live session (OD-18 ⑧) out).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md`: Status, decisions 1 to 8 (lines 22-116; decision 2 the timing parameters and what is never handed — `n_min`, `cv_max`, the `bound`, the `objective`; decision 4 forms (A) and (B); decision 7 the neither-form answer), Limits (lines 145-154), Consequences and Boundaries (lines 171-190).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: Status (lines 3-15), decision 1 (lines 32-38; the mock is this record's scope), decisions 2, 3, 5, 6 and 7 (lines 39-97), Limits (lines 113-123), Consequences and Boundaries (lines 148-170).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: decisions 3, 4 and 6 (request members, `execution`, the order of a call) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decisions 2 to 7 (lines 37-106; `outcome`, `condition`, `intervals_ns` / `resolution_ns`, `memory_bytes`, `ceiling` and `bound`) and Limits (lines 170-183).
- `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md` decisions 2, 5 and 6 (lines 32-91): the seed reaches the operation; it is recorded nowhere.
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 7, 8 and 9 (lines 65-110): the repeat loop and stopping rule, the report form, the parameters. `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md` decisions 4 and 5 (lines 40-53): `n_min`, `cv_max`.
- `ARCHITECTURE/decisions/ADR-0052-od13-memory-ceiling-measurement.md` decisions 3 to 5 (lines 44-72): the figure, how it is taken, the verdict.
- `ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md` decisions 2, 3 and 5 (lines 30-56, 67-75): what an operation is called with, the mock backend, its script, the default registry, 5 (e) "depends on its script and its call alone".
- `ARCHITECTURE/Requirements.md`: the OD register rows OD-13 (line 102) and OD-18 (line 107).
- `ARCHITECTURE/OpenDecisionProposals.md`: the OD-18 section (from line 281; its adopted-part bullets for ADR-0044 and ADR-0061 to ADR-0065, and the registered sub-questions, in particular ⑧ and ⑲ — check the last registered number) and the OD-13 section (lines 207-229).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 from line 168 (its heading and its latest 2026-10-15 passages).
- Code, read only as observations (this record binds no code): `hilclaw/mock_backend.py` and `hilclaw/mock_check.py` (how the check's mock asks its script and what its default script computes), `hilclaw/run_parameters.py`, `hilclaw/run_operation.py`, `hilclaw/harness/timing.py` (`parse_report`, `judge_report`, the report form in the module docstring) and `hilclaw/harness/measurement.py` (`N_MIN`, `CV_MAX`, `stopping_state`).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0066-od18-run-tools-mock-script.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Before the push, confirm that ADR-0066 is still free on origin/main; if not, take the next free number and update every reference. Keep the record at about 230 lines or fewer so the task stays within the 300-LOC cap.
2. Scope: the mock backend and a call of `sim.run` or `board.run` about one attempt of a run whose hw_profile names the mock (ADR-0061 decision 1), both tools; no rule of the frame, nothing for `profiler.collect`, nothing for `cpu_standin`'s operation. Each point below is weighed against at least one alternative and is the record's own design:
   - (a) **How the mock's operation of each tool asks its script**: with which things (the called tool, and the four things of ADR-0065 decision 2 — request, hw_profile, timing parameters, output path — as they are, or otherwise), how often, and whether the operation looks at the answer (compare ADR-0044 decision 2 and ADR-0065 decision 5 on who establishes the form).
   - (b) **What the default script answers for each tool**, and on which of the things it is asked with that answer depends (ADR-0016 decision 5 (e): no clock, no random source, no counter, no file of its own). Say whether it answers (A) or (B), whether the two tools answer alike (nothing but the point distinguishes the two operations — **owner**, O1, as ADR-0061 quotes it), and whether it raises any tool failure (it may name no backend kind; ⑲ (나) stays open).
   - (c) **The rule by which the default script derives its report and its figure**: the report form of ADR-0009 decision 8 as `judge_report` reads it (`resolution_ns`, `interval_ns` lines, `stop` line); how many intervals and which values; whether `judge_report` judges it completed and converged or not converged, given that the operation is **never handed `n_min` or `cv_max`** (ADR-0065 decision 2) while the replay uses them — say how the rule still agrees with the replay (for example by reading the constants the records fix, or by a report that agrees with the replay for any admitted value, or otherwise) and weigh it; how the rule treats the sample form and the seed; and the figure of ADR-0052 decision 4 (a value or none), with what follows for the verdict against a `bound` under ADR-0061 decision 6 and ADR-0063 decisions 6 and 7. The mock has no process (ADR-0016 decision 5 (a)); say what its report and figure stand for and what they do not show (a Limits entry, as ADR-0044 decision 7 did).
   - (d) What a script of a test can express (by citation, as ADR-0044 decision 5): each thing an operation may return, an answer of neither form (ADR-0065 decisions 6 and 7), and the death of the process; the backend tool-failure kinds are not named.
   - (e) Two tables in the manner of ADR-0044 decision 6: what a script of these tools is asked with, and what the default script's report and figure hold.
3. **Not decided, said openly**: fault injection in a live session (OD-18 ⑧ stays open; the default script's answer depends on no member of the request beyond what the record states); OD-18 ⑲ (가) to (라); the spend (OD-2, OD-19); when the default registry comes to hold the mock with these operations; the input schema and description; #5 A-4, B-2, B-3. Do not invent an owner decision.
4. **No data-plane schema change.** Do not add, remove or change a member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec or a result file; the closed member list of ADR-0063 decision 9 stays unchanged; no value of `error.kind` is added or given a place. If the design you judge right needs any of these, stop and return BLOCKED (`data-plane schema change`) with the question; do not write it.
5. Cite earlier records only as they say things; mark every sentence of the record's own as its own (the "cited" versus "this record's own" convention of ADR-0044/ADR-0065). No earlier record is edited. Consequences lists the earlier sentences that become less exact, at least: ADR-0061 Consequences item (5) and its Boundaries bullet on the mock; ADR-0065 Consequences ("Not yet possible": the mock's operation) and its Boundaries bullet on the mock; and, as observations, the docstring of `hilclaw/mock_backend.py` ("Not here yet: the script of the default registry").
6. Consequences names the code slice this record makes possible (the mock's operation and default script of the run tools and their tests, in the manner of `hilclaw/mock_check.py`; names and modules left to the code task) and the contract slices still open from ADR-0061 Consequences: (6) ⑲, (7) the spend.
7. `ARCHITECTURE/Requirements.md`: in the OD-18 row, add a 반영 link to ADR-0066 as earlier ADRs were added; keep the status wording unchanged. Edit the OD-13 row only if a sentence in it becomes false. Do not change the number of OD rows.
8. `ARCHITECTURE/OpenDecisionProposals.md`: in the OD-18 section, add one adopted-part bullet for ADR-0066 after the ADR-0065 bullet (Korean, as the neighbouring bullets). Register a new sub-question only if the record needs one (date 2026-10-15 or later, next free number — check the section).
9. `ARCHITECTURE/StandardScenarios.md`: run the coverage re-check under §검사 규칙; append a dated passage to §검사 결과 with the verdict (expected: no verdict change and no gap; report honestly if otherwise) and extend the heading parenthetical with one clause for this record, as previous ADR tasks did.
10. Document checks reported in `## Result`: every relative link in the new and edited text resolves; `git diff --stat origin/main` shows only the files in `touchesFiles`; `git diff --check` is clean; the OD register has the same number of rows before and after.
11. Doc mode (CLAUDE.md A-13): branch `claude/T-0205-od18-run-tools-mock-script`, reviewer cycle with a fresh-context reviewer, at most 7 rounds, then rebase on origin/main and push to main directly. Commit trailers: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0205`, and the `Co-Authored-By` line. Delete the branch afterwards (local and remote if pushed).
12. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what ADR-0066 decides, the landed commit, the objection window (7 days from the notice). Last line `— posted by driver`. Record the comment URL in `## Result`.
13. Nothing is built or run except read-only git/gh and link checks. No `claude` process, compiler, kernel or container is started (D16).

## Out of Scope

- Any code, including the mock's operation and default script of the run tools, the tool functions, their registration, and changes to `hilclaw/mock_backend.py`, `hilclaw/mock_check.py`, `hilclaw/run_*.py` or `hilclaw/harness/`.
- ADR-0061 Consequences items (6) and (7): the answers and kinds of OD-18 ⑲ (가) to (라), including what the tool function does with a tool failure an operation raises (bound by ADR-0065 decision 8); the spend (OD-2, OD-19).
- Fault injection in a live session (OD-18 ⑧); the operation of `cpu_standin` (setting values, container — OD-14).
- `profiler.collect`; a target on another machine (#5 B-2, B-3); the emulated `sim.run` (OD-18 ⑫); OD-13 sub-questions ⑧ and ⑪; the result files (PLAN P1-8).
- Editing any earlier ADR; list less-exact sentences in Consequences instead. The integrator lists of less-exact sentences from ADR-0063 to ADR-0065.

## Follow-ups

## Result

- **DONE.** Landed on `main` as `edf70d5` (doc mode, direct push after rebase on `origin/main` at `15984d5`; one squashed commit with `Reviewed-by: reviewer agent (7 rounds, Approve)`, `Task: T-0205`, `Co-Authored-By`). Branch `claude/T-0205-od18-run-tools-mock-script` deleted locally and on origin. No PR.
- **Review:** 7 rounds with a fresh-context `dev-reviewer`. R1-R5 approved with minors/nits, each addressed. R6 asked for changes: a not-converged report that reads neither `n_min` nor `cv_max` does exist, so the weighing in decision 4 was rewritten. R7 approved with one minor, left open (Follow-ups).
- **What ADR-0066 decides:** the mock's operation asks its script once per call with the called tool and the four things of ADR-0065 decision 2, as they are; the answer is passed on unseen. The default script answers both tools alike and depends on nothing it is asked with: form (A), with the report `resolution_ns 1`, `n_min` x `interval_ns 1000000`, `stop converged`, and no figure. `n_min` is read from the source commit's constant (ADR-0009 decision 7, ADR-0061 decision 3). It never gives (B), a tool failure or an answer of neither form. No sub-question registered.
- **A-13:** no data-plane schema change. No member is added or changed, ADR-0063 decision 9 is unchanged, and no `error.kind` value is added or given a place.
- **Document checks:** all 62 relative links in the added lines resolve (`#od-18` included). `git diff --stat 15984d5 edf70d5` shows only the four `touchesFiles` (169 insertions, 2 deletions; ADR 164 lines). `git diff --check` is clean. The OD register has 30 rows before and after. ADR-0066 was still free on `origin/main` at push time.
- **Coverage re-check:** StandardScenarios got the 2026-10-15 11th passage and a heading clause. There was no verdict change and no gap.
- **Owner notice (DRIVER §9):** https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6194231066 (objection window until 2026-10-22).
- **D16:** no `claude` was started.
- **Follow-ups:**
  - R7 minor: ADR-0066 decision 4 (iii) says "None exists" for a converged report that reads neither constant; under the standard applied to (ii), such a report fitted to a narrow window of `cv_max` around 0.05 can be built. The sentence and the "(존재하지 않는다)" in the OpenDecisionProposals bullet should say it is tuned to `cv_max`'s value. The choice of (i) is unaffected.
  - Code slice: the mock's operation and default script per ADR-0066.
