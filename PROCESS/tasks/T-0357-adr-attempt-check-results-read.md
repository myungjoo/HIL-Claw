---
id: T-0357
title: Write ADR-0131 — how the evaluator of a first-case turn reads an attempt's journaled check results through a typed registry tool, and whether that read is enough to give it the verdicts work (ADR-0128 Consequences slice 3, second record; ADR-0129 decision 5; part of OD-23 and OD-18; PLAN P2-3, P2-6)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-9, FR-11, FR-17, OD-23, OD-18, OD-16, OD-30, S0, S1]
dependsOn: [T-0352, T-0355, T-0356]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

PLAN P2 runs in this order (D18): P2-1 to P2-4, then P2-6 and P2-7, then P2-5. P2-1's round steps and P2-2 wait on the owner (HQ-0040, HQ-0041; ADR-0126 Consequences). P2-3 (the evaluator) is the item in progress. ADR-0128 (T-0352) fixed the evaluator and its write tool `verdicts.write`. ADR-0129 (T-0355) fixed `hypotheses.read`. T-0356 (PR #204, 1644e7b) landed that tool and gave it to the evaluator. The evaluator still cannot do the verdicts work. `orchestration/agents/evaluator.md` "Verdicts" answers a verdicts delegation with one line: the verdicts cannot yet be written because no tool reads the attempts' results. A verdicts record must rest on what typed tools return (ADR-0128 decision 4). ADR-0129 decision 5 assigns two questions to the record of the journaled-results read: the read itself, and "whether the results read alone is enough for the verdicts work to be given — every verdict `inconclusive` until the comparison exists".

P2-5 needs this work. Rounds 1 to 4 of its five rounds reach evaluate, and FR-17 does not let such a round end without verdicts. `verdicts.write` refuses every `comparison` entry for now (ADR-0128 decision 6), so the only evidence a verdict can hold today is a `check` entry (`ref`, `point`, `outcome`; ADR-0071 decision 3). That entry's `outcome` is the result of a `correctness.check` call, journaled in the run's `events.ndjson` by the tool layer (ADR-0042; `hilclaw/check_tool.py`). This record decides how the evaluator gets that ground. This task belongs to PLAN checklist items P2-3 and P2-6 (the verdict step), so the D18 rule for non-checklist work does not apply.

OD-23, OD-18 and OD-16 are design-level ODs, not owner-only ones (DRIVER §9), so this task writes the ADR (DRIVER §6). Open HQs checked (HQ-0013 to HQ-0046):
- HQ-0040 (a shell for the coder-driver) is not crossed: the evaluator has no shell, and the read is a registry tool.
- HQ-0041 and #5 A-8 are not crossed: no model or token budget is named.
- HQ-0021 (T-0210, ADR-0068 on the run tools' tool failure, unlanded) is not crossed: `sim.run` and `board.run` are not registered, and their results are the comparison record's ground, not this one's. The record states this boundary and does not cite the unlanded ADR-0068 or ADR-0088 as accepted.
- HQ-0031 (whether injected hypotheses must be tested) concerns selection, not reading the log.
- HQ-0043 (#5 A-3 commit of a turn cut short) is not crossed: the read writes nothing.
- HQ-0032 concerns open PR #186 (`hilclaw/start_instance.py` and three test files). Those files do not overlap `touchesFiles`.

Issues #4, #7 and #8 have had no comments since 2026-10-03. The last #5 entries are the ADR-0129 and ADR-0130 notices and HQ-0046. No open PR edits `ARCHITECTURE/`. The unlanded branches of T-0210 and T-0264 touch the OD-18 register row and proposal section. ADR-0129 and ADR-0130 already edited the same places after them.

This is a record, not code. No `claude` process is started, and nothing requires a live session (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap) and §9 (OD closure under D6: §9 notice on #5, the 7-day objection window).
- `CLAUDE.md`, "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), and the document-mode branch and merge procedure (A-13).
- `.claude/skills/dev-item-address/SKILL.md` (document mode, reviewer cycle steps 10 to 12).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, the "Record format" section only.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`, whole file. Read decisions 2 to 7, Consequences slice 3, "The cost, plainly" and Boundaries closely. Boundaries leaves open "whether `verdicts.write` holds `check` entries against the log (OD-16; OD-18 ⑳ for several executions)". This record either answers that point or keeps it open, and says which.
- `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md`, whole file. It is the closest pattern for structure, tool table, kinds reasoning and the runtime acceptance item numbering. Decision 5 is the open point this record answers.
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decisions 1, 3 (the `check` entry), 4 (the rule that leads to each value) and 6 (round 0).
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: decisions 1 to 3, 5 and 6. A standing is computed from every end line of an identity, and the standing tool is a separate slice-3 item of ADR-0128. This record either covers the standing too or keeps it separate, and weighs that choice in Alternatives.
- `ARCHITECTURE/decisions/ADR-0040-od18-correctness-check-call-identity.md` (the identity of a check call: tuple, point, `execution`) and `ARCHITECTURE/decisions/ADR-0042-od18-correctness-check-result-members.md` (result members, `outcome` values, decision 7's closed member list).
- `ARCHITECTURE/decisions/ADR-0006-od8-events-log.md` (lines, torn tail, damage) and `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md` decisions 3, 4 and 6 (start and end lines, step states, the tail).
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md` decisions 2 to 4 and 7, `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md` decisions 3, 4 and 6, and `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md` decision 3 (registry read tools that are not journaled).
- `ARCHITECTURE/decisions/ADR-0123-od18-turn-session-run-identity.md` decisions 2 and 4.
- `ARCHITECTURE/EventKinds.md` (the kinds of log lines).
- Code, as observation: the module docstrings of `hilclaw/events.py`, `hilclaw/journal.py`, `hilclaw/run_journal.py`, `hilclaw/check_tool.py`, `hilclaw/check_result.py`, `hilclaw/check_identity.py`, `hilclaw/check_standing.py`, `hilclaw/hypotheses_tool.py` and `hilclaw/verdicts_tool.py`. Also `default_registry` in `hilclaw/tools.py` and `orchestration/agents/evaluator.md`.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph and the register rows OD-16, OD-18 and OD-23. `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" and the sections OD-23, OD-18 and OD-16. `ARCHITECTURE/StandardScenarios.md`: the check rules, S0, S1, and the first paragraph of §검사 결과.

## Acceptance Criteria

1. **New record** `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`. The executor may choose a clearer slug and then updates `touchesFiles` in `## Result`. The file follows ADR-0001's "Record format": a Status with the owner-sentence search (sources, terms, the sentences found, each read for what it says and no further), Context, Decision, a Walk-through, Alternatives considered, Consequences, Boundaries and References. Every sentence is either cited with its source or marked as the record's own, as ADR-0128 and ADR-0129 do. The scope is the runs of ADR-0120 decision 1.
2. **The decision answers, with weighings in Alternatives:**
   - (a) **The means** by which the evaluator gets the outcome of an attempt's `correctness.check` calls at a point. The means follows from the constraints of ADR-0128 decision 4, ADR-0123 decision 2 (no place in the prompt or the delegation), ADR-0010 decision 3 (MCP front) and K4 premise 1 (no read is restricted). If the means is a registry tool, the record gives its name (no `_` in the name, ADR-0010 decision 4), its request (`run_id` and the members that name the attempt and point, per ADR-0015 decision 4 and ADR-0040), its result, its checks in order with their kinds, and whether it is journaled. Kinds are reused where the same situation of the same file already has a name, or new kinds are justified as names of the tool layer.
   - (b) **What the result holds when an identity has several end lines, an open start line, or an end line without an outcome** (ADR-0110 decision 2 counts all of them). The record also says how a `check` entry's single `outcome` (ADR-0071 decision 3) relates to that result.
   - (c) **Whether the standing of ADR-0110 is part of this read or stays a separate tool.** If the standing is folded in, the record says which form it gives the standings, because ADR-0110 gave them none as values (ADR-0128 Consequences slice 3).
   - (d) **Whether `verdicts.write` holds `check` entries against the log** (ADR-0128 Boundaries). The record answers it or states that it stays open, with the reason.
   - (e) **Whether this read is enough to give the verdicts work to the evaluator** (ADR-0129 decision 5), and with it every verdict `inconclusive` until the comparison exists (ADR-0128 decision 6, "The cost, plainly"). The record weighs this against FR-17 ("evaluate에 이른 라운드는 판정 없이 끝나지 않는다") and against FR-17's demand that only verified results support. It then states what `orchestration/agents/evaluator.md` "Verdicts" becomes in the code slice.
   - (f) **Who may use the means.** At least the evaluator (ADR-0128 decision 3: later tools are added "by the records or slices that create them"). Whether the Round-Manager gets it stays with P2-1 unless the record gives a reason.
3. **Not decided here, and listed under Boundaries**: the results of `sim.run` and `board.run` and the comparison of ADR-0007 decision 7 (the comparison record; HQ-0021); the fields of `eval.json` (OD-20); who may ask for a further `execution` (ADR-0110 decision 6; OD-18 ⑭); the evaluator's model and budget (#5 A-8, HQ-0041); hooks and permissions beyond the `tools` list (P2-4); any owner-only point (#5 A and B items, C-6, OD-25, OD-3). If an answer under AC 2 turns out to need an owner-only decision, the executor writes that part as open in the record and returns the question to the driver as an HQ. The executor does not decide it.
4. **No data-plane change.** No member, file, kind of event, value or version of `events.ndjson`, `verdicts.json`, `hypotheses.json`, `STATE.json`, `instance.json`, `eval.json` or `artifacts.json` is added or changed, and no validator changes. Tool failure kinds are tool-layer names. If the answer needs a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md, "데이터 plane 스키마 변경").
5. **Consequences** names the code slices this record enables (each tested with a stub `claude` only, or none; D16). It also has a "less exact, not edited" list found by a stated search (for example ADR-0128 decision 3 and slice 3, ADR-0129 decision 5, ADR-0110 Boundaries, the docstring of `hilclaw/check_standing.py`, evaluator.md "Verdicts"), not claimed complete. It adds any new runtime acceptance item, numbered after ADR-0129's (xxi) in the turn-session series. A plain cost paragraph closes it.
6. **`ARCHITECTURE/Requirements.md`**: edit the register rows that the record answers part of (OD-23 and OD-18, and OD-16 only if AC 2 (d) answers part of it) as the "행 형식" paragraph prescribes. The status words do not change.
7. **`ARCHITECTURE/OpenDecisionProposals.md`**: edit the matching sections as the header's "기록 규칙" prescribes. If a sub-question is answered in whole or in part, its state is rewritten where it stands, as that rule says.
8. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage by the document's check rules (supported / open / gap) for at least S0 and S1, and record the result in §검사 결과 as the first paragraph of that section prescribes. Notes of S0 or S1 that this record narrows are rewritten in place.
9. **Edits stay inside `touchesFiles`.** No edit of an earlier ADR, of FR or NFR text, of UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, settings files or the `HIL-Claw-data` repository. If the coverage re-check finds a UsageCases change necessary, the executor lists it as a follow-up.
10. **Document mode (A-13)**: branch `claude/T-0357-<slug>`, the context-isolated reviewer cycle ending in Approve (at most 7 rounds), rebase on `origin/main`, direct push to `main`. The commit message ends with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0357`. After landing, post the DRIVER §9 notice on #5 with the driver marker (DRIVER §8). New runtime acceptance items go back to the driver for an HQ with the reason `runtime-acceptance`.
11. No `claude` process is started, and nothing runtime-only is required of this machine (D16).

## Out of Scope

- Any code: the tool module, registry entry, evaluator definition change and tests are the code slices this record enables.
- The comparison tool, the run tools' results, and the registration of `sim.run` and `board.run` (T-0210, HQ-0021).
- The round steps of `orchestration/round-manager.md` (P2-1) and the selection side (rest of OD-23, P2-6).
- The "less exact" wording follow-ups of earlier ADRs (PLAN 보류, D18).

## Follow-ups

- Next for the planner: the code slice(s) of this record (tool module and registry entry; evaluator.md "Verdicts" per AC 2 (e)), then the comparison record of ADR-0128 Consequences slice 3.

## Result

- **Outcome**: DONE. `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` written (slug as planned, `touchesFiles` unchanged), with the edits of `ARCHITECTURE/Requirements.md` (rows OD-16, OD-18, OD-23 and OD-30), `ARCHITECTURE/OpenDecisionProposals.md` (sections OD-16, OD-18, OD-23, OD-30) and `ARCHITECTURE/StandardScenarios.md` (S0 step 6 note; recheck line). Document mode, pushed directly to `main` (fast-forward). **Deviation**: a failed `git rebase` in a chained command (the Result edit was staged) skipped the squash, and the following `git push origin HEAD:main` landed the four reviewed branch commits a2e8afe, ed9d8b7, 8f798d3 and 7f76719 unsquashed and without the `Reviewed-by` trailer. Their content is exactly the content approved in review round 4. No force push was used to rewrite them; the closing commit on `main` that adds this Result carries `Reviewed-by: reviewer agent (4 rounds, Approve)` and `Task: T-0357` as the review record.
- **Decisions** (for the runs of ADR-0120 decision 1): (a) a registry tool `checks.read` (`run_id`, `round`, `candidate`, `point`, optional `attempt`), not journaled, reading the whole log; (b) every end line its own element, open identities listed, results and failures as stored, and a rule for a `check` entry's single `outcome` (`pass` only when every result is `pass`); (c) the ADR-0110 standing folded in as the tool-layer strings `verified` / `not_verified` / `undetermined`; reserved `run_file_*` kinds of ADR-0019 widened to this log read, one new kind `check_result_invalid`; (d) answered: `verdicts.write` holds every `check` entry against the log (`check_unfounded`); (e) the verdicts work is given, every verdict `inconclusive` until the comparison exists, and the evaluator.md changes are named; (f) only the evaluator gets the tool. OD-30 was added to the answered ODs after review round 1 (the `check`-entry rule binds the writer of `verdicts.json`). No status word changed; no data-plane change.
- **Review**: 4 rounds (round 1 Request changes: OD-30 part, kind order and scope, ADR-0019 decision 4, walk-through, citations; round 2 Request changes: builds-on list, decision 6 wording, log read for every record, `run_file_missing` boundary; round 3 Approve with one Minor and two Nits, all fixed; round 4 Approve, no findings).
- **Coverage re-check**: S0 and S1 re-checked by the StandardScenarios rules: no verdict change, no gap; no UsageCases change needed.
- **For the driver**: post the DRIVER §9 notice on #5 (done by the executor after landing; see below). New runtime acceptance item **(xxii)** of ADR-0131 (the result of `checks.read` reaches the evaluator whole within Claude Code's MCP output limit) goes to the driver for an HQ with reason `runtime-acceptance` (non-blocking notice).
- **Follow-ups (planner)**: code slice 1 — `checks.read` module, tests, registration, `check_standing.py` docstring (note from the reviewer: `check_standing.standing` raises `journal.JournalError` both for a step line breaking ADR-0011 and for a result without an admitted `outcome`; the slice must tell them apart to answer `run_file_invalid` vs `check_result_invalid`); slice 2 — the log check of `verdicts.write` (`check_unfounded` and the log-read kinds); slice 3 — `orchestration/agents/evaluator.md` per ADR-0131 decision 6 and its `tools` test; then the comparison record of ADR-0128 Consequences slice 3.
