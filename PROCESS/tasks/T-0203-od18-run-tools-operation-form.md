---
id: T-0203
title: Record ADR-0065, the form between the tool function and an operation of sim.run / board.run and the answer of neither form (ADR-0061 Consequences item (4), OD-18)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, OD-13]
dependsOn: [T-0191, T-0195, T-0199, T-0201]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 280, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` now have four records: ADR-0061 (split, sample form, the call that carries the memory figure, the `bound`, classes of outcome), ADR-0062 (call identity and order of a call), ADR-0063 (result members) and ADR-0064 (timing seed). Code exists for the objective admission (`hilclaw/run_objective.py`), the step values (`hilclaw/run_identity.py`), the result builder (`hilclaw/run_result.py`), the seed draw (`hilclaw/run_seed.py`) and the judging half (`hilclaw/harness/timing.py` `judge_report`). The tool function still cannot be written to its end, because nothing fixes what crosses the cut between it and an operation, or what a call answers when an operation returns something of neither form.

ADR-0061 Consequences item (4) names exactly this slice: "the form of what crosses the cut, and what a call answers when an operation returns neither form (as ADR-0043 and ADR-0045 did for the check)". ADR-0062 decision 6 (last bullet) and ADR-0063 decisions 3 and 10 hand the same item on. ADR-0064 decision 4 asks this slice that **no end line of either tool holds `seed_not_drawn` as its `failure` kind**. The Follow-ups of T-0201 and T-0202 name this task.

This is part of OD-18, a design-level OD, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9 this task therefore writes the ADR. For `correctness.check` the same ground took two records (ADR-0043 the form, ADR-0045 the neither-form answer); here one record covers both, because ADR-0045 is now a landed precedent whose reasoning can be cited instead of rebuilt.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0203-<slug>`, trailer `Task: T-0203`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", the 문서 커버리지 재검사 rule, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase, direct push to main with the `Reviewed-by` trailer), the BLOCKED reasons (a data-plane schema change is one), 코멘트 최소화, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146).
- The two models, whole: `ARCHITECTURE/decisions/ADR-0043-od18-correctness-check-operation-form.md` (204 lines; decisions 2 to 7 are the pattern of the form) and `ARCHITECTURE/decisions/ADR-0045-od18-correctness-check-neither-form-answer.md` (187 lines; the kind `operation_answer_invalid`, what the log holds, the three ways into the case, the message, its A-13 reading at line 166).
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: Status (lines 3-15), decisions 1 to 3 (lines 32-59; decision 3 lists what an operation is handed and what it returns as classes (A) and (B), the figure with (A), and "The spelling of what is handed and returned is the next slices' and the code's"), decision 7 (lines 86-97), Limits (lines 113-123), Consequences and Boundaries (lines 148-170).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md`: decision 4 (lines 66-73, the request members), decision 6 and the Walk-through (lines 80-114), Consequences and Boundaries (lines 144-166).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md`: decision 3 (lines 45-65, the seven values of `condition`; its last bullet says they are "not the spelling of what an operation returns"), decision 6 (lines 87-94, `memory_bytes`), decisions 9 and 10 (lines 113-152), Consequences and Boundaries (lines 207-232).
- `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md`: decisions 2 to 4 and 7 (lines 32-102; decision 4's request at the bullet "Never on an end line of these tools by this contract"), Consequences and Boundaries (lines 143-160).
- `ARCHITECTURE/decisions/ADR-0052-od13-memory-ceiling-measurement.md` decision 4 (the figure, its unit rule and "A run that is not completed yields no figure").
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` decisions 3 and 4 (lines 46-104): the build conditions the check's operation returns, which this record may take for the timing build.
- `ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md` decisions 2, 5 and 6 (lines 30-41, 67-75, 92 onward) and `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decision 2 (lines 39-57): what an operation is called with, the mock's script, the reserved kinds `tool_crashed` and `bad_result`.
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 5, 7, 8 and 9 (lines 50-58, 65-110): the seed on the command line, the report channel and form, the parameters.
- `ARCHITECTURE/Requirements.md`: the OD register rows OD-13 (line 102) and OD-18 (line 107).
- `ARCHITECTURE/OpenDecisionProposals.md`: the OD-18 section (lines 281-331; its adopted-part bullets for ADR-0043, ADR-0045 and ADR-0061 to ADR-0064, and the registered sub-questions, in particular ⑲) and the OD-13 section (lines 207-229).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 from line 168 (its heading and its latest 2026-10-15 passages).
- Code, read only as observations (this record binds no code): `hilclaw/check_operation.py` (how the check's tool function tells (A), (B) and neither form apart, and `operation_answer_invalid`), `hilclaw/harness/timing.py` (`judge_report` and its parameters), `hilclaw/run_result.py`, `hilclaw/run_seed.py` and `hilclaw/run_objective.py` (the kinds the run tools' contract already has).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Before the push, confirm that ADR-0065 is still free on origin/main; if not, take the next free number and update every reference. Keep the record at about 240 lines or fewer so the task stays within the 300-LOC cap. If both halves (criteria 2 and 3) cannot fit, land the form half only, register the neither-form answer as a new OD-18 sub-question in the manner ADR-0043 registered ⑮, and say so in `## Result` and Follow-ups.
2. **The form** (the ADR-0043 half). Scope: the runs of ADR-0061 decision 1 only (a hw_profile naming `cpu_standin` in the local configuration, or the mock), both tools, an operation that runs on the host of the tool function or an operation of the mock; not a rule of the frame, not a rule for any other HW tool, nothing about a target on another machine (#5 B-2). Each point weighed against at least one alternative, each the record's own design:
   - (a) **What an operation is handed**, beyond the request and the hw_profile (ADR-0016 decision 2): the classes ADR-0061 decision 3 lists (the dimensions, `n_max`, the sample form, the timing seed of ADR-0064, the output path) — as one further value or otherwise, with each value's kind and bounds and its source. State what is never handed (the `bound`, the `objective`, `n_min`/`cv_max`, any setting of ADR-0061 decision 3).
   - (b) **How the execution point reaches an operation** (ADR-0062 decision 4 members; compare ADR-0043 decision 3).
   - (c) **What an operation returns**: the spelling of (A), the report with the figure of ADR-0052 decision 4 or that there is none, and of (B), one of the four conditions in the order of ADR-0061 decisions 3 and 7. Say whether the (B) values are tied to the first four values of `condition` of ADR-0063 decision 3, as ADR-0043 tied its two to ADR-0042, and how (A) and (B) are told apart.
   - (d) A table "What crosses the cut" in the manner of ADR-0043 decision 7.
3. **The answer of neither form** (the ADR-0045 half): what is meant (a value of neither form, including a figure of the wrong kind with (A), and something raised that is no tool failure); that it is never made into a result; what the log holds after the call (end line or open identity) and what the call answers, with a `kind` and whether it is the run tools' own (if `operation_answer_invalid` is reused, say how a tool's own kind is shared, as ADR-0064 decision 4 did for `seed_not_drawn`); what the message may carry. **Answer ADR-0064 decision 4's request**: no end line of either tool holds `seed_not_drawn` as its `failure` (and say the same, or not, of `objective_not_stated` / `objective_not_covered`, which ADR-0061 placed before the start line). Which backend kinds may stand as the `failure` of an end line stays with OD-18 ⑲ (나); do not name them.
4. **No data-plane schema change.** Do not add, remove or change a member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec or a result file; the closed member list of ADR-0063 decision 9 stays unchanged. Giving a value of `error.kind` a place as the `failure` of an end line is read as ADR-0045 read it (its line 166); state that A-13 reading openly. If the design you judge right needs a new member, stop and return BLOCKED (`data-plane schema change`) with the question; do not write it.
5. Cite earlier records only as they say things; mark every sentence of the record's own as its own (the "cited" versus "this record's own" convention of ADR-0043/ADR-0061). Do not invent an owner decision. No earlier record is edited. Consequences lists the earlier sentences that become less exact, at least: ADR-0061 decision 3 ("The spelling of what is handed and returned is the next slices' and the code's") and Consequences item (4); ADR-0062 decision 6 last bullet; ADR-0063 decision 3 last bullet and decision 10; ADR-0064 decision 4 ("What the tool function does with an operation that raises a tool failure of this kind belongs to the slice ...").
6. Consequences names the code slice this record makes possible (the run tools' check of an operation's answer — form (A), (B) or neither — and its tests; names and modules left to the code task) and the next contract slices still open from ADR-0061 Consequences: (5) the mock's operation and scripts, (6) ⑲, (7) the spend.
7. `ARCHITECTURE/Requirements.md`: in the OD-18 row, add a 반영 link to ADR-0065 as earlier ADRs were added; keep the status wording unchanged. Edit the OD-13 row only if a sentence in it becomes false. Do not change the number of OD rows.
8. `ARCHITECTURE/OpenDecisionProposals.md`: in the OD-18 section, add one adopted-part bullet for ADR-0065 after the ADR-0064 bullet. Register a new sub-question only if the record needs one (date 2026-10-15 or later, next free number after ⑳ — check the section).
9. `ARCHITECTURE/StandardScenarios.md`: run the coverage re-check under §검사 규칙; append a dated passage to §검사 결과 with the verdict (expected: no verdict change and no gap; report honestly if otherwise) and extend the heading parenthetical with one clause for this record, as previous ADR tasks did.
10. Document checks reported in `## Result`: every relative link in the new and edited text resolves; `git diff --stat origin/main` shows only the files in `touchesFiles`; `git diff --check` is clean; the OD register has the same number of rows before and after.
11. Doc mode (CLAUDE.md A-13): branch `claude/T-0203-<slug>`, reviewer cycle with a fresh-context reviewer, at most 7 rounds, then rebase on origin/main and push to main directly. Commit trailers: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0203`, and the `Co-Authored-By` line. Delete the branch afterwards (local and remote if pushed).
12. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what ADR-0065 decides, the landed commit, the objection window (7 days from the notice). Last line `— posted by driver`. Record the comment URL in `## Result`.
13. Nothing is built or run except read-only git/gh and link checks. No `claude` process, compiler, kernel or container is started (D16).

## Out of Scope

- Any code, including the run tools' tool functions, their operations, the check of an operation's answer, and changes to `hilclaw/check_operation.py`, `hilclaw/run_*.py` or `hilclaw/harness/timing.py`.
- ADR-0061 Consequences items (5) to (7): the mock's operation, its script and a default script; the answers and kinds of OD-18 ⑲ (가) to (라); the spend (OD-2, OD-19).
- The backend tool-failure kinds that may stand on an end line (⑲ (나)); recovery after any answer (OD-10, the retry part of OD-17).
- `profiler.collect`; a target on another machine (#5 B-2, B-3); the emulated `sim.run` (OD-18 ⑫); OD-13 sub-questions ⑧ and ⑪.
- Editing any earlier ADR; list less-exact sentences in Consequences instead.
- The integrator list of less-exact sentences from ADR-0063 / ADR-0064 Consequences.

## Follow-ups

## Result
