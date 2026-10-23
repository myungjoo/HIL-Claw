---
id: T-0355
title: Write ADR-0129 — how the evaluator of a first-case turn reads a round's hypothesis record through a typed registry tool (ADR-0128 Consequences slice 3, first record; part of OD-23, OD-30 and OD-18; PLAN P2-3, P2-6)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-9, FR-11, FR-17, OD-23, OD-30, OD-18, OD-16, S0, S1]
dependsOn: [T-0352, T-0353, T-0354]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 200, files: 4}
hq: []
---
## Why

The P2 order in PLAN (D18) is P2-1 to P2-4, then P2-6 and P2-7, then P2-5. P2-1's round steps and P2-2 wait on the owner (HQ-0040, HQ-0041; ADR-0126 Consequences). P2-3 (the evaluator) is the item in progress. ADR-0128 (T-0352) fixed the evaluator, T-0353 added `verdicts.write`, and T-0354 added `orchestration/agents/evaluator.md`. That definition still cannot do the verdicts work. On a verdicts delegation it reports in one line that the round's verdicts cannot yet be written, because no typed tool reads a round's `hypotheses.json` or an attempt's journaled results (ADR-0128 decision 4: the record "rests on" typed tools of the registry; Consequences slice 3: "After a record each").

P2-5 needs this work. Rounds 1 to 4 of its five rounds reach evaluate, and FR-17 does not let such a round end without verdicts. The first of the slice-3 records is the read of a round's hypothesis record. Of the four, it has the fewest open dependencies: the file, its validator and its parser exist (ADR-0059; `hilclaw/hypotheses_file.py`), and `verdicts.write` already reads the same file for its own check (`hilclaw/verdicts_tool.py` `_hypotheses`). The journaled-results read, the standing tool and the comparison tool come later, each after its own record. This task is part of the PLAN checklist item P2-3 (and the verdict step of P2-6), so the D18 rule for non-checklist work does not apply.

OD-23, OD-30 and OD-18 are design-level ODs, not owner-only ones (DRIVER §9), so this task writes the ADR (DRIVER §6). Open HQs checked (HQ-0013 to HQ-0045): HQ-0040 (shell for the coder-driver) is not crossed, because the evaluator has no shell and this is a registry tool. HQ-0041 (#5 A-8) is not crossed because no model is named. HQ-0031 (whether injected hypotheses must be tested) is about selection, not about reading the file. HQ-0032 concerns PR #186 (`hilclaw/start_instance.py` and three test files), which does not overlap `touchesFiles`. Issues #4, #7 and #8 have had no comments since 2026-10-03. The last #5 entries are the ADR-0128 notice and HQ-0045. No open PR edits `ARCHITECTURE/`.

This is a record, not code. No `claude` process is started, and nothing requires a live session (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap) and §9 (OD closing authority, owner notice).
- `CLAUDE.md`, "상시 규칙": "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), "문서 커버리지 재검사", and the document-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format".
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`, whole file. In particular, decisions 2 to 6 and Consequences slice 3.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: decisions 2, 3 and 5 and the Walk-through. This is the precedent for typed read tools that take `run_id` (`state.read`, `instance.read`), with their kinds and the reason they are not journaled. Do not copy its wording.
- `ARCHITECTURE/decisions/ADR-0059-od30-round-hypothesis-record.md`: decisions 1, 2 and 5 (place, file as a whole, round 0) and Boundaries.
- `ARCHITECTURE/decisions/ADR-0073-od30-case-lookup-and-case-basis.md`: the decisions on `cases_read` and the basis kind `case`, only far enough to see what a read returns.
- `ARCHITECTURE/decisions/ADR-0015-od18-tool-contract-frame.md`: decisions 2 to 4 and 7 (request frame, data root never in a request, `run_id`).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: decisions 3, 4 and 6.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decision 6 and the runtime acceptance items (i) to (vii).
- Code, as observation only: `hilclaw/hypotheses_file.py` (module docstring, `parse`, `final_name`), `hilclaw/verdicts_tool.py` (module docstring, `_hypotheses`, `_reported`), `hilclaw/run_file_tools.py` (module docstring, `definitions`, `_read`, `_reported`), `hilclaw/tools.py` `default_registry`, and `orchestration/agents/evaluator.md`.
- `ARCHITECTURE/Requirements.md`: the register's "행 형식" paragraph (line 84) and the rows FR-17, OD-16, OD-18, OD-23 and OD-30.
- `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" (line 8), § OD-23 (around line 390), § OD-30 (around line 457) and § OD-18 (around line 273), as far as they bear on reading the hypothesis record or on the evaluator's inputs.
- `ARCHITECTURE/StandardScenarios.md`: § 검사 규칙, the first paragraph of § 검사 결과 (its 기록 규약, line 170) and the "최근 재검사" line, and the S0 and S1 rows of the judgement table.

## Acceptance Criteria

1. **New file** `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md` in the record format of ADR-0001. If the executor needs a clearer slug, it keeps the number and records the final path in `## Result`. Status is "Accepted" under DRIVER §9. Its scope is the runs of ADR-0120 decision 1. It includes an owner-sentence search (bodies and comments of #4, #5, #7 and #8, with the search terms listed) and cites the records above instead of restating them. It decides, with alternatives weighed:
   - (a) **The means**: a typed registry tool reached through the MCP front with `run_id` and the round in the request, or another means that keeps ADR-0128 decision 4 and ADR-0123 decision 2 (no place in the session). The alternatives to weigh include a tool, an evaluator `Read` of a path it finds (the record rests on typed tools, ADR-0128 decision 4), and the Round-Manager passing the content in the delegation (another agent's account, ADR-0128 decision 4).
   - (b) **The tool**, if (a) chooses one: its name and MCP name (ADR-0010 decision 4), its request members, its result, and its failure kinds in check order. State whether the kinds reuse those `verdicts.write` already reports for the same file (ADR-0128 decision 6). State whether it is journaled (precedent: ADR-0124 decision 3), how round 0 is treated (ADR-0059 decision 5), and what it returns for a valid file: the document as it is, or a part of it. The record says why.
   - (c) **Who may use it** in a first-case turn: the evaluator's `tools` list (ADR-0128 decision 3). Say whether the Round-Manager also gets it, or leave that to P2-1 and the rest of OD-23 in Boundaries. Nothing is decided for the selection side or other roster members.
   - (d) **What the evaluator then has**, and what it still lacks for the verdicts work: the journaled results of an attempt, the standing and the comparison stay slice 3 (ADR-0128 Consequences). The record says whether the definition's one-line "cannot yet" report for a verdicts delegation stays until the journaled-results read exists. It does not decide that read.
2. **No data-plane schema change.** No member, file, kind, value or version is added to or changed in `hypotheses.json` or any other data-plane file, and no validator changes. Failure kinds of the tool layer are not data-plane changes (ADR-0128 decision 6 reading). If the decision needs a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
3. **No owner-only point is decided**, and nothing is invented. Boundaries name what stays open: who writes `hypotheses.json` in a turn (the selection side, rest of OD-23; P2-6), whether injected hypotheses must be tested (HQ-0031), the journaled-results read, the standing and comparison tools (ADR-0128 slice 3), the evaluator's model (#5 A-8, HQ-0041), session permissions and hooks (rest of OD-18; P2-4), and runs outside ADR-0120 decision 1. If a point cannot be decided without one of these, the record decides only what every answer allows, and Follow-ups give the HQ text for the driver with its reason (`owner-only-decision` or `requirement-unclear`).
4. **Consequences** name the code slices the record enables, each testable without a real `claude` (D16). Examples: the tool module with its test file and its registration in `default_registry`, and the addition of its MCP name to `orchestration/agents/evaluator.md` together with that file's test of the `tools` set. Say which slices can be planned now. Give a stated search for earlier sentences that become less exact, list them, and edit none of them (D18 hold class).
5. **Runtime acceptance items**: if the record depends on a fact that only a live session can establish, number it in the turn-session series after ADR-0128's (xx). Put the proposed `runtime-acceptance` HQ text in Follow-ups (DRIVER §8). If there is no new item, say so.
6. **`ARCHITECTURE/Requirements.md`**: edit each row the record answers part of (OD-23 and, if it applies, OD-30 or OD-18) as the "행 형식" paragraph at line 84 prescribes. Do not use earlier task files as a template for these edits.
7. **`ARCHITECTURE/OpenDecisionProposals.md`**: edit each section the record answers part of as the header's "기록 규칙" at line 8 prescribes.
8. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage by § 검사 규칙 (CLAUDE.md "문서 커버리지 재검사"), at least for S0 and S1. Record the result as the 기록 규약 in the first paragraph of § 검사 결과 prescribes. The "최근 재검사" line is rewritten in place to this re-check. Earlier same-day or earlier-date re-checks are not chained onto it, because the 기록 규약 keeps their account in git history.
9. Document mode (A-13): a context-isolated reviewer cycle ends in Approve. Then the branch `claude/T-0355-adr-round-hypotheses-read` is rebased onto `origin/main` and pushed directly to main with the `Reviewed-by:` and `Task: T-0355` trailers. `## Result` carries the proposed DRIVER §9 owner notice for #5 (ending with `— posted by driver`) and any HQ texts from criteria 3 and 5.
10. No `claude` process is started, and no runtime-only resource is required (D16).

## Out of Scope

- Any code, test or prompt file: the tool module, its registration, and edits of `orchestration/agents/evaluator.md` or `orchestration/round-manager.md`. These are later slices.
- The journaled-results read, the standing tool and the comparison tool (ADR-0128 slice 3, each its own record), the fields of `eval.json` (OD-20), and the writer of `hypotheses.json`.
- Wording fixes in earlier ADRs or docstrings that become less exact (D18 hold).
- `hilclaw/start_instance.py` and the other files of PR #186.

## Follow-ups

- Next for the planner, if the record chooses a tool: the code slice (tool module, test file, `default_registry`, `evaluator.md` `tools` list and its test). After that, the record for an attempt's journaled-results read (ADR-0128 slice 3).

## Result

- Outcome: DONE. `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md` landed on main as fdc9664 in document mode (reviewer agent, 7 rounds, Approve), one squashed commit with trailers `Reviewed-by: reviewer agent (7 rounds, Approve)` and `Task: T-0355`. Rounds 3-6 were Approve with nits only; round 7 reviewed the rebased result.
- Rebase: commit 9db2701 (owner session, #5 link of the 2026-10-19 decision) landed during the task and also edited the StandardScenarios "최근 재검사" line. The conflict was resolved by keeping this task's rewritten line (AC 8 and the 기록 규약: a re-check with no verdict change is kept only in git history); 9db2701's edits to Requirements.md, OpenDecisionProposals.md and DRIVER.md are intact.
- Decision: the evaluator reads a round's `decision/hypotheses.json` through a new typed registry tool `hypotheses.read` (`mcp__hilclaw__hypotheses_read`) via the MCP front. Request exactly `run_id` and `round` (round 0 refused as `invalid_request`); result `{"record": ...}`, the whole valid document; failures reuse the `hypotheses_*` kinds of `verdicts.write`, and a file whose `run_id` or `round` differs from the request is `hypotheses_invalid`; no journaling. A later code slice adds it to the evaluator's `tools`; the Round-Manager's use is left to P2-1. The evaluator's one-line "cannot yet" report for a verdicts delegation stays at least until the journaled-results read exists.
- Register: OD-23 and OD-18 rows and proposals sections cite ADR-0129, status words unchanged; OD-30 not edited. StandardScenarios S0 and S1 re-checked: no verdict change, no gap, no note change. Data plane unchanged.
- §9 owner notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280154011
- New HQ-0046 (runtime-acceptance, non-blocking): runtime acceptance item (xxi) of ADR-0129.
- Follow-ups: ADR-0129 Consequences slice 1 (tool module + test, registered in default_registry) and slice 2 (evaluator.md `tools` list and test, "Verdicts" reason narrowed) can be planned now; after both, the record for an attempt's journaled-results read (ADR-0128 slice 3).
