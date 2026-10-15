---
id: T-0208
title: Record ADR-0067, what a call of sim.run / board.run answers for a run whose file states no op_signature, an op_signature the contract does not cover, or no n_max, and the order of those answers in moment 4 (OD-18 sub-question 19 part (ga), ADR-0061 Consequences item (6))
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-10, OD-18, OD-8, OD-13]
dependsOn: [T-0191, T-0195, T-0199, T-0201, T-0203, T-0205, T-0207]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0067-od18-run-tools-admission-kinds.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The run tools `sim.run` / `board.run` have six records: ADR-0061 (split, sample form from the objective, `objective_not_stated` / `objective_not_covered`), ADR-0062 (call identity), ADR-0063 (result members), ADR-0064 (timing seed, `seed_not_drawn`), ADR-0065 (the form across the cut, `operation_answer_invalid`) and ADR-0066 (the mock's side). Code exists for each of those slices (`hilclaw/run_objective.py`, `run_identity.py`, `run_result.py`, `run_seed.py`, `run_parameters.py`, `run_operation.py`, `mock_run.py`).

The tool functions still cannot be written: ADR-0061 to ADR-0066 Consequences all list item (6), "the answers and kinds of ⑲ (가) and (나), the log of ⑲ (다) and the setting values of ⑲ (라)". Part (가) of OD-18 sub-question ⑲ (registered by ADR-0061 Boundaries) asks what a call answers for a run whose valid `instance.json` states **no op_signature**, an **op_signature this contract does not cover**, or **no `n_max`** — with kinds of this contract's own, the kinds of `correctness.check` (ADR-0041), or kinds the frame reserves — and their place in moment ④ beside `objective_not_stated` and `objective_not_covered` (ADR-0061 decision 4: "Their order relative to the answers of OD-18 sub-question ⑲ (가) is that sub-question's") and beside the seed draw (ADR-0064: its order relative to ⑲ (가) is that sub-question's). For `correctness.check` the same slice was ADR-0041 (op_signature) and ADR-0046 decision 5 (a run that states no number of draws), with code `hilclaw/check_admission.py`.

Part (가) is the smallest closed piece of item (6) and needs no setting value or container design; parts (나) to (라) are left to later tasks. This is part of OD-18, a design-level OD, not owner-only (DRIVER §9: owner-only means #5 A/B items, C-6, OD-25 and OD-3). Under DRIVER §6 and §9 this task therefore writes the ADR.

## Required Reading

- `PROCESS/DRIVER.md` §2 (doc mode), §3-5 (executor procedure, resume rule, time limit), §5 (naming: branch `claude/T-0208-<slug>`, trailer `Task: T-0208`; size cap), §8 (the `— posted by driver` footer), §9 (OD closing authority, owner notice on #5, 7-day objection window).
- `CLAUDE.md`: all rules. In particular "미결은 발명하지 않는다", the 문서 커버리지 재검사 rule, the A-13 branch/merge procedure (doc mode: reviewer cycle, rebase, direct push to main with the `Reviewed-by` trailer), the BLOCKED reasons (a data-plane schema change is one), 코멘트 최소화, and "개발 드라이버와 런타임의 구분" (D16).
- `.claude/skills/dev-item-address/SKILL.md` (whole) and `.claude/skills/dev-code-review/SKILL.md` (whole; doc-mode return path).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` §"Record format" (from line 146) and decision 1 (the *name* form `[a-z][a-z0-9_]{0,31}`).
- The models, read whole: `ARCHITECTURE/decisions/ADR-0041-od18-correctness-check-dimensions.md` (198 lines; decisions 2 to 5 and 8 are the pattern: where the dimensions come from, at which moment and from which read, a run with no op_signature, an op_signature not covered, the order of a call, why not reserved); `ARCHITECTURE/decisions/ADR-0046-od18-correctness-check-draws.md` decisions 4, 5 and 8 (lines 97-123, 138-153) and Alternatives (lines 181-201): a run that states no number of draws, and how its kind was ordered after the op_signature kinds.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`: Status (lines 3-15), decisions 1 and 3 to 7 (lines 32-97; decision 3 what the tool function keeps out of a request — the dimensions among them; decision 4 the two objective kinds and their place in ④), Limits (lines 113-123), Consequences and Boundaries (lines 148-170; the text of ⑲ at line 168).
- `ARCHITECTURE/decisions/ADR-0062-od18-run-tools-call-identity.md` decision 6 (lines 80-98, the order of a call) and Walk-through (lines 99-114).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` decision 5 (lines 77-86: `shape`, `n_max` and `sample_form` in a result) and decision 9 (lines 113-144, the closed member list).
- `ARCHITECTURE/decisions/ADR-0064-od13-run-tools-timing-seed.md` decisions 3, 4 and 7 (lines 51-77, 92-102): the place of the draw and `seed_not_drawn`.
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md` decision 2 (lines 33-54: the timing parameters handed to an operation, `n_max` and the dimensions among them) and decision 8 (lines 111-116).
- `ARCHITECTURE/decisions/ADR-0023-od8-instance-record-n-max.md` decisions 4 and 5 (lines 47-64: a file without `n_max` states no bound; no default substitutes; "what a call answers when no bound is stated" left to the tools; sub-question ㉑ of OD-8).
- `ARCHITECTURE/decisions/ADR-0031-od8-instance-record-op-signature.md` decisions 5 and 6 (lines 74-91) and Limits (lines 92-100).
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` decisions 2 to 4 (lines 30-83: the four reserved kinds and their order with `no_backend` / `not_offered`) and `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decision 2 (lines 39-57: reserved kinds versus each tool's kinds).
- `ARCHITECTURE/decisions/ADR-0008-*.md` (the `gemm` contract) and the decision of ADR-0041 that says when an op_signature is covered (decision 5), as the source of "covered" for the timing run's dimensions.
- `ARCHITECTURE/Requirements.md`: the OD register rows OD-8 (line 97), OD-13 (line 102) and OD-18 (line 107).
- `ARCHITECTURE/OpenDecisionProposals.md`: the OD-18 section (from line 281; its adopted-part bullets for ADR-0061 to ADR-0066 and the registered sub-questions, in particular ⑲ and ⑳ — check the last registered number) and the OD-8 section (from line 90; sub-questions ㉑ and ㉘ — read them so the record does not answer them).
- `ARCHITECTURE/StandardScenarios.md`: §검사 규칙 (lines 13-29) and §검사 결과 from line 168 (its heading and its latest 2026-10-15 passages).
- Code, read only as observations (this record binds no code): `hilclaw/check_admission.py` (the check's four admission answers and their order), `hilclaw/run_objective.py`, `hilclaw/run_seed.py`, `hilclaw/run_parameters.py`, and in `hilclaw/instance.py` the functions `n_max_of` (line 937), `op_signature_of` (line 977) and `objective_of` (line 1127).
- Before you edit `ARCHITECTURE/`, run `gh pr list` and read issues #4, #5, #7 and #8 (the CLAUDE.md 세션 진입 점검). If an open PR touches the same tables or sections, stop and return BLOCKED.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0067-od18-run-tools-admission-kinds.md` exists in the ADR-0001 record format: Status, Context, Decision with numbered decisions, a Walk-through, Limits, Alternatives considered, Consequences, Boundaries, References. Before the push, confirm that ADR-0067 is still free on origin/main; if not, take the next free number and update every reference (file name, links, task Result). Keep the record at about 220 lines or fewer so the task stays within the 300-LOC cap.
2. Scope: a call of `sim.run` or `board.run` about one attempt of a run of ADR-0061 decision 1 (the first case or a run at the mock), both tools, one contract. It answers **part (가) of OD-18 sub-question ⑲ only**. Each point below is weighed against at least one alternative and marked as the record's own design where it is:
   - (a) **Where the dimensions of a timing run come from** and from which read (compare ADR-0041 decisions 2 and 3; ADR-0061 decision 3 keeps the dimensions out of a request), and **what a call answers for a valid file without `op_signature`** and **for a stated op_signature this contract does not cover**. Weigh at least: the kinds of `correctness.check` reused with the same spelling and meaning (as ADR-0064 did with `seed_not_drawn`), kinds of this contract's own with other spellings, and reserving them in the frame (ADR-0015 decision 2; the reasoning of ADR-0041 decision 4). Say whether "covered" for the run tools is the same predicate as for the check, and why.
   - (b) **What a call answers for a valid file without `n_max`** (ADR-0023 decision 4: a silent file states no bound, and no reader substitutes 10, `N_MAX_DEFAULT` or any other value). Weigh a tool failure of its own kind against any reading that would let the call run; do not answer OD-8 sub-question ㉑ (who writes the member, where 10 comes from).
   - (c) **The order in ④** of every answer the call can give there: `no_backend` / `not_offered` (ADR-0019), the answers of (a) and (b), `objective_not_stated` / `objective_not_covered` (ADR-0061 decision 4) and the place of the seed draw and `seed_not_drawn` (ADR-0064 decision 3), for a content with several faults — one answer, the first whose condition holds, as ADR-0046 decision 5 did. Give the reason for each adjacent pair.
   - (d) For each new answer: the call called no operation, built and ran nothing, consumed nothing, appended no line, the request can be repeated, and the answer is never the `failure` of an end line (or say otherwise and why); the message rule (what it names, that it shows nothing of the value); and the name check of ADR-0041 decision 4 (a *name* of ADR-0001; grep `hilclaw/`, `tests/` and `ARCHITECTURE/` on the day and report that it equals no reserved kind, no `step` value and no member name, or that it equals the check's kind on purpose).
   - (e) A Walk-through table of the rows of ④ in the manner of ADR-0041 / ADR-0046 (a file without each member, with two faults, with all members; at `cpu_standin` and at the mock).
3. **Not decided, said openly**: parts (나), (다) and (라) of ⑲ (the kinds of the situations with no timing executable, the compiler's log, the setting values; OD-14); OD-8 sub-questions ㉑ and ㉘; whether the start of an instance checks any of these members and who acts on the answer (FR-1, PLAN P2-1); the spend (OD-2, OD-19); ⑳; the input schema and description; `profiler.collect`; #5 A-4, B-2, B-3, B-7. Do not invent an owner decision.
4. **No data-plane schema change.** Do not add, remove or change a member of a result, a line of `events.ndjson`, `instance.json`, `STATE.json`, a spec or a result file; the closed member list of ADR-0063 decision 9 stays unchanged. A new value of `error.kind` answered before the start line and never written to `events.ndjson` may be named (as ADR-0061 named `objective_not_stated`), with the A-13 reading stated in Consequences as ADR-0061 did. If the design you judge right needs a kind on an end line or any member change, stop and return BLOCKED (`data-plane schema change`) with the question; do not write it.
5. Cite earlier records only as they say things; mark every sentence of the record's own as its own (the "cited" versus "this record's own" convention of ADR-0061 to ADR-0066). No earlier record is edited. Consequences lists the earlier sentences that become less exact, at least: ADR-0061 decision 4 ("Their order relative to the answers of OD-18 sub-question ⑲ (가) is that sub-question's") and its Consequences item (6) and Boundaries ⑲ (가); ADR-0064's sentence that leaves its order relative to ⑲ (가) open; ADR-0023 decision 5 ("what a call answers when no bound is stated") for the run tools; ADR-0066 Consequences item (6); and, as observations, the docstrings of `hilclaw/run_objective.py` and `hilclaw/run_seed.py` where they speak of order.
6. Consequences names the code slice this record makes possible (the run tools' admission of the op_signature, the dimensions and `n_max`, in the manner of `hilclaw/check_admission.py`, with its tests; names and modules left to the code task — and whether it extends `hilclaw/run_objective.py` or adds a module is the code task's) and the contract slices still open: ⑲ (나) to (라), the spend, ⑳, the result files (PLAN P1-8), the input schema and description, the registration.
7. `ARCHITECTURE/Requirements.md`: in the OD-18 row, add a 반영 link to ADR-0067 as earlier ADRs were added; keep the status wording unchanged. Edit the OD-8 or OD-13 rows only if a sentence in them becomes false. Do not change the number of OD rows.
8. `ARCHITECTURE/OpenDecisionProposals.md`: in the OD-18 section, add one adopted-part bullet for ADR-0067 after the ADR-0066 bullet (Korean, as the neighbouring bullets), saying that ⑲ (가) is answered and (나) to (라) stay open. Register a new sub-question only if the record needs one (date 2026-10-16 or later, next free number — check the section).
9. `ARCHITECTURE/StandardScenarios.md`: run the coverage re-check under §검사 규칙; append a dated passage to §검사 결과 with the verdict (expected: no verdict change and no gap; report honestly if otherwise) and extend the heading parenthetical with one clause for this record, as previous ADR tasks did.
10. Document checks reported in `## Result`: every relative link in the new and edited text resolves; `git diff --stat origin/main` shows only the files in `touchesFiles`; `git diff --check` is clean; the OD register has the same number of rows before and after.
11. Doc mode (CLAUDE.md A-13): branch `claude/T-0208-od18-run-tools-admission-kinds`, reviewer cycle with a fresh-context reviewer, at most 7 rounds, then rebase on origin/main and push to main directly. Commit trailers: `Reviewed-by: reviewer agent (N rounds, Approve)`, `Task: T-0208`, and the `Co-Authored-By` line. Delete the branch afterwards (local and remote if pushed).
12. After landing, post the owner notice of DRIVER §9 on issue #5 in English: what ADR-0067 decides, the landed commit, the objection window (7 days from the notice). Last line `— posted by driver`. Record the comment URL in `## Result`.
13. Nothing is built or run except read-only git/gh, grep and link checks. No `claude` process, compiler, kernel or container is started (D16).

## Out of Scope

- Any code, including the run tools' admission, the tool functions and their registration, and changes to `hilclaw/run_*.py`, `hilclaw/check_admission.py`, `hilclaw/instance.py` or `hilclaw/harness/`.
- Parts (나), (다) and (라) of OD-18 sub-question ⑲; the spend (OD-2, OD-19); ⑳; the operation of `cpu_standin` (setting values, container — OD-14).
- OD-8 sub-questions ㉑ and ㉘ (who writes `n_max` / `op_signature` at the start of an instance, and where an instance's own op_signature is checked); what follows an answer in the round loop (FR-1, PLAN P2-1).
- `profiler.collect`; a target on another machine (#5 B-2, B-3); the emulated `sim.run` (OD-18 ⑫); the result files (PLAN P1-8).
- Editing any earlier ADR; list less-exact sentences in Consequences instead.

## Follow-ups

## Result
