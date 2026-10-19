---
id: T-0352
title: Write ADR-0128 — who holds the evaluation role of a first-case turn, which tools it may use, what it is given and what it returns, and what writes the evaluation role's files (part of OD-23 and OD-16, PLAN P2-3; for the runs of ADR-0120 decision 1)
phase: P2
status: IN_PROGRESS
commitMode: doc
coversReq: [FR-1, FR-9, FR-17, NFR-4, NFR-6, OD-23, OD-16, OD-30, OD-18, S0, S1, S7]
dependsOn: [T-0329, T-0341, T-0343, T-0346, T-0348]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

The P2 order of PLAN (D18) is P2-1 to P2-4, then P2-6 and P2-7, then P2-5. What remains of P2-1 is "The round steps" of `orchestration/round-manager.md`. That work now waits on the owner: ADR-0126 Consequences ("The cost, plainly") says that until Q1 is answered (HQ-0040: Bash or `coder.run` for the coder-driver), and until #5 A-8 is answered (HQ-0041), no agent can reach the coder call, "so the round steps of P2-1 wait on it". What remains of P2-2 waits on the same Q1. The next item in the order is **P2-3, the evaluator** ("Write 권한 없음, 하네스만 호출 — OD-16 종결 필요(§9 ADR 경로)"). It is a checklist item, so the D18 rule for non-checklist work does not apply. P2-5 needs it: round 0 of a first-case run has to check and measure its bring-up attempt (ADR-0119 decisions 2 and 4), and FR-17 has evaluate record a verdict per hypothesis.

No record says who does the evaluation in a first-case turn. ADR-0004 decision 4 gives `eval/` to an "evaluation role". ADR-0071 decision 1 and its Boundaries leave "which agent writes the file, whether the evaluator has Write permission or a tool writes for it" to OD-23, OD-16 and P2-3. ADR-0110 decision 1 names no component that reads the hard-floor rule, and points to P2-1 and P2-3. ADR-0126 Boundaries leave "the rest of the roster: … evaluator, … their inputs and outputs, how they get the run id" open. OD-23 and OD-16 are design-level ODs, not owner-only (DRIVER §9). So this task writes the ADR (DRIVER §6).

Sources that bound the record:

- **K2**, the #4 comment of 2026-07-31 01:59Z (§3a revision, an agreement ADR-0120 and ADR-0126 treat as binding): the roster row "evaluator | 정확도·점수 (FR-9) | MCP correctness.check | eval.json"; the "experiment-runner | sim/board 측정 | MCP sim.run / board.run" row; condition 2 ("subagent는 자기 산출물 파일만 쓰고 … commit은 매니저 전담"); condition 3 (journaling of expensive results is done in the tool layer); condition 4 (deterministic steps are not made sub-agents).
- **K4**, the #4 comment of the same day 06:08Z: the owner premises ("읽기 제한은 채택하지 않는다"; a write zone given by prompt alone is too weak). The OD-23 proposal ("`evaluator`는 반대로 강화 — 실험 수행 주체가 아닐 것, Write 권한 없음, 아티팩트 경로+해시만 수신") and #7 are research, not owner decisions.
- **HQ-0040 is not crossed.** An evaluator whose tools are MCP registry tools agrees with both K2 and K4. If any point of the record turns on the owner's reading of K2 against K4 (Bash or not), the record leaves that point open in Boundaries and names HQ-0040. It does not decide it.
- **Owner-only points stay untouched**: #5 A-4 and the rest of OD-1 (which measurement is "better", the choice among measurements, which ADR-0119 decision 4 leaves open), OD-3 (gates), #5 A-8 (models and tokens, including the evaluator's model), OD-25 and C-6.

Open HQs checked (HQ-0013 to HQ-0044). HQ-0032 is the given `run_id` of the start function (draft PR #186, `hilclaw/start_instance.py` only). HQ-0040 and HQ-0041 are about the coder call. HQ-0043 is #5 A-3 for a cut-short turn. The rest are runtime-acceptance notices or concern other tasks. None decides this point.

This is a record, not code. No `claude` process is started, and nothing requires a live session (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task file format, naming convention, size cap) and §9 (OD closing authority, owner notice).
- `CLAUDE.md`, "상시 규칙": "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분" (D16), "문서 커버리지 재검사", and the document-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, section "Record format".
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`, whole file. It is the closest model for the record's shape: an issuer, a sub-agent definition (decision 6), an owner question left open, and runtime acceptance items. Do not copy its wording.
- `ARCHITECTURE/decisions/ADR-0124-od23-round-manager-run-file-access.md`: Context (the #7 lines on the evaluator), decisions 1 to 3 and 5.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decisions 2, 5 and 6, and the runtime acceptance items (i) to (vii).
- `ARCHITECTURE/decisions/ADR-0010-od18-tool-exposure-form.md`: decisions 3, 4 and 6, and line 149 ("P2-2 / P2-3 inherit").
- `ARCHITECTURE/decisions/ADR-0004-od8-data-plane-layout.md`: the path table rows for `measure/` and `eval/` (around line 75), decision 4, and the bullets around lines 96 and 100.
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decisions 1 and 6, and Boundaries ("Which agent writes the file").
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: decisions 1 to 3.
- `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md`: decisions 2, 4 and 5, and the Walk-through.
- `ARCHITECTURE/decisions/ADR-0127-od8-commit-step.md`: decisions 2 and 5 (only the Round-Manager commits).
- `ARCHITECTURE/decisions/ADR-0120-od8-first-state-file.md`: decision 1 (the scope) and Context W1.
- `hilclaw/tools.py`: `default_registry` and the tool names it registers. `hilclaw/check_tool.py`: the module docstring (what `correctness.check` writes and journals).
- `orchestration/round-manager.md`, whole file.
- `ARCHITECTURE/Requirements.md`:
  - the register's "행 형식" paragraph (line 84);
  - the rows FR-1, FR-9, FR-17, NFR-4, NFR-6, OD-16, OD-18, OD-20, OD-23 and OD-30.
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's "기록 규칙" (line 8);
  - § OD-16 (around line 239), § OD-23 (around line 389) and its "제안으로 남는 부분" bullet, § OD-20 (around line 366) and § OD-30 (around line 455), as far as they name the evaluator or the writer of `eval/` files.
- `ARCHITECTURE/StandardScenarios.md`: § 검사 규칙, the first paragraph of § 검사 결과 (line 168 onward) with its "최근 재검사" line, and the S0, S1 and S7 rows of the judgement table.
- GitHub #4 comments https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 (K2: §1, the roster table and conditions 1 to 4, and §6) and https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 (K4), read with `gh api repos/myungjoo/HIL-Claw/issues/comments/<id>`.

## Acceptance Criteria

1. **New file** `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md` in the record format of ADR-0001. If the executor keeps the number but needs a clearer slug, it updates `touchesFiles` in `## Result`. Status is "Accepted" under DRIVER §9, as part of OD-23 and OD-16. Its scope is limited to the runs of ADR-0120 decision 1. It includes an owner-sentence search (bodies and comments of #4, #5, #7 and #8, with the search terms listed) and cites rather than restates the records above. It decides at least the following for that scope, with alternatives weighed:
   - (a) **Who holds the evaluation role** in a turn: a sub-agent `evaluator` that the Round-Manager issues, the Round-Manager itself, or a deterministic package function. Weigh this against K2 conditions 3 and 4 and against what in evaluation needs judgment (for example, a hypothesis verdict and its cause, FR-17) as opposed to what is deterministic (the pass or fail of a check, ADR-0110).
   - (b) **Its tools**: the exact `mcp__hilclaw__…` names it may use (ADR-0010) out of those `default_registry` registers. State whether `correctness.check`, `sim.run` and `board.run` belong to it or to the experiment side of K2's roster. State whether it has Write, Edit, Bash or any other file-writing means, and how that agrees with "Write 권한 없음" in PLAN P2-3 and with OD-16 threat A. Reading is not restricted (K4).
   - (c) **What it is given**: how it learns the run id and the attempt tuple (`run_id`, `round`, `candidate`, `attempt`), for example in its delegation prompt in the manner of ADR-0123 and ADR-0126. Also whether it receives paths and hashes or reads through tools.
   - (d) **What it returns** to the Round-Manager, and in which form.
   - (e) **What writes the evaluation role's files** for this scope: `rounds/<RRRR>/eval/verdicts.json` (ADR-0071) and `…/eval/…/eval.json` (ADR-0004). If the evaluator has no Write, name the writing means (for example a typed registry tool) as a later code slice, or leave it open. The fields of `eval.json` are OD-20 and stay open.
   - (f) **Its definition**: the place and name under `orchestration/` (ADR-0118 decision 5), as ADR-0126 decision 6 does for the coder-driver. The definition file itself is a later slice.
2. **No data-plane schema change.** The record adds no member, file, kind, value or version to `STATE.json`, `instance.json`, `events.ndjson`, `artifacts.json`, `verdicts.json` or `eval.json`, and defines no fields of `eval.json`. If the decision needs such a change, the executor stops and returns BLOCKED (CLAUDE.md BLOCKED reason "데이터 plane 스키마 변경").
3. **No owner-only point is decided.** Boundaries name what stays open, each with its owner: the choice among measurements and "better than" (#5 A-4, the rest of OD-1); promotion and k (OD-15, OD-29); gates (OD-3); the evaluator's model and tokens (#5 A-8); whether any agent has a shell (HQ-0040, where it applies); the permissions, allowlists and hooks of the session (rest of OD-18, PLAN P2-4); the rest of the roster (technique-selector, experiment-runner if not decided, promoter); and runs outside ADR-0120 decision 1. If the record cannot decide (a) or (b) without one of these, it decides only what every answer allows and lists in Follow-ups the HQ that the driver should raise, with English text and the reason (`owner-only-decision` or `requirement-unclear`).
4. **Consequences** name the code and prompt slices the record enables, for example the definition `orchestration/agents/<name>.md`, a writing tool if one is chosen with its registration in `default_registry`, and the delegation step in "The round steps" of `orchestration/round-manager.md` (which waits on HQ-0040 and HQ-0041 together with the coder step). Say which slices can be planned now. Each slice must be testable with a stub `claude` only (D16). The record lists the earlier sentences that become less exact (found by a stated search), and edits none of them.
5. **Runtime acceptance items.** The record lists any fact that only a live session can establish, continuing the turn-session series after ADR-0127's (xvii). An example is that a sub-agent of a `-p` turn session gets only the tools its definition lists. The executor puts the proposed `runtime-acceptance` HQ text in Follow-ups for DRIVER §8.
6. **`ARCHITECTURE/Requirements.md`**: follow the register's "행 형식" (line 84) for each row the record answers part of. That is OD-23, OD-16 if the record answers part of it, and OD-30 only if it answers who writes `verdicts.json`. Each new ADR gets one link with a few-word topic after `**확정분**:`. The open part after `**잔여**:` is rewritten in place. The record is not restated and no dated text is added. The status cell keeps one status word with a short date and path.
7. **`ARCHITECTURE/OpenDecisionProposals.md`**: follow the header's "기록 규칙" (line 8). Each section whose OD the record answers part of gets one `채택분` line in the form that rule gives. Where an open part or a sub-question is now partly or wholly answered, its status and state word are rewritten in place, and the question's wording stays. Examples are the evaluator items of § OD-23's roster bullet and "제안으로 남는 부분". No dated paragraph is added and the record is not restated.
8. **`ARCHITECTURE/StandardScenarios.md`**: re-check coverage by § 검사 규칙 (CLAUDE.md "문서 커버리지 재검사"), at least for S0, S1 and S7. Follow the recording convention in the first paragraph of § 검사 결과: rewrite the "최근 재검사" line in place, and add to "판정 변화 이력" only if a judgement or a gap changes. A judgement-table note changes only where it names the evaluator or the writer of `eval/` files as open.
9. Document mode (A-13): a context-isolated reviewer cycle ends in Approve. Then the branch is rebased onto `origin/main` and pushed directly to main with the `Reviewed-by:` and `Task: T-0352` trailers. `## Result` carries the proposed DRIVER §9 owner notice for #5 (with the `— posted by driver` marker) and any HQ texts from criteria 3 and 5.
10. No `claude` process is started, and no runtime-only resource is required (D16).

## Out of Scope

- Any code or prompt file: `orchestration/agents/…`, a writing tool, and the delegation step in `orchestration/round-manager.md`. These are later slices.
- The coder-driver's means (HQ-0040), the coder's model and tokens (HQ-0041), and the rest of "The round steps" (P2-1).
- The fields of `eval.json` (OD-20), promotion (OD-15, OD-29), static checks, roofline and adversarial re-verification (the rest of OD-16), and hooks (P2-4).
- Wording fixes in earlier ADRs (D18 hold).

## Follow-ups

- **Runtime-acceptance HQ (DRIVER §8, reason `runtime-acceptance`, non-blocking), proposed text:**
  > ### HQ-NNNN — T-0352: runtime acceptance items (xviii)-(xx) of ADR-0128
  > ADR-0128 (the evaluator of a first-case turn, part of OD-23 and OD-16; T-0352) adds three turn-session runtime acceptance items. Under D16 they are closed by your check on a runtime machine or by the runtime's own self-check, never by a driver task: (xviii) a sub-agent of a `-p` turn session defined in `.claude/agents/evaluator.md` gets exactly the tools its `tools` list names, the `hilclaw` tools given by `--mcp-config` among them, and no `Write`, `Edit`, `Bash` or other unlisted tool; (xix) the Round-Manager's delegation message reaches the evaluator whole, and the evaluator's final message reaches the Round-Manager whole; (xx) a `correctness.check` called from a sub-agent through MCP returns within the MCP idle window (about 30 minutes) for the largest first-case check ADR-0117's limits allow, and a call cut off there leaves no check running. Please reply with `HQ-NNNN` and what you observed when you have checked them.
  >
  > — posted by driver
- **No owner-only HQ.** Nothing of ADR-0128 turns on #5 A-4, A-8, OD-1, OD-3, OD-25, C-6 or the K2/K4 reading of HQ-0040.
- **Later slices (for the planner):** (1) the registry tool `verdicts.write` of ADR-0128 decision 6 (code, can be planned now); (2) `orchestration/agents/evaluator.md` (code, can be planned now); (3) records for the read, standing and comparison tools (ADR-0128 Consequences slice 3); (4) the delegation steps of the round steps, with HQ-0040/HQ-0041.

## Result

- **Outcome**: DONE. ADR-0128 (`ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`, slug kept) landed on main in document mode with the edits of `ARCHITECTURE/Requirements.md` (rows OD-23, OD-16, OD-30), `ARCHITECTURE/OpenDecisionProposals.md` (OD-23, OD-16, OD-30) and `ARCHITECTURE/StandardScenarios.md` (S0 step 6 note, recent re-check line; no judgement change). The landed commit is the one whose trailer is `Task: T-0352`.
- **Decided (first-case runs of ADR-0120 decision 1)**: the `evaluator` sub-agent issued by the Round-Manager holds `eval/`; tools `mcp__hilclaw__correctness_check` (its one HW tool), the three registered read tools and Read/Grep/Glob, no Write/Edit/Bash; it gets the run id and tuple in the delegation, no place; returns a text report; `verdicts.json` is written by a new registry tool `verdicts.write` that checks ADR-0071's file rules and the rules against `hypotheses.json`, and refuses any comparison entry until a comparison tool exists; no `eval.json` while OD-20 is open; definition `orchestration/agents/evaluator.md`.
- **Data plane**: unchanged. **OD status words**: unchanged.
- **Review**: see the `Reviewed-by` trailer of the landed commit.
- **Proposed DRIVER §9 owner notice for #5:**
  > ### OD-23 / OD-16 (part) — ADR-0128: the evaluator of a first-case turn (T-0352)
  > ADR-0128 was accepted under DRIVER §9 for the runs of ADR-0120 decision 1. It decides that the `evaluator` sub-agent, issued by the Round-Manager, holds the evaluation role (`eval/`); its only HW tool is `correctness.check`, it has no Write, Edit or Bash, and reading is not restricted; it receives the run id and the attempt tuple or round in the delegation message and returns a text report; the round's `verdicts.json` is written for it by a new registry tool `verdicts.write`, which refuses a record that fails ADR-0071's rules or its rules against `hypotheses.json`, and, until a comparison tool exists, any comparison entry (so verdicts are `inconclusive` for now); no `eval.json` is written while OD-20 is open. Owner-only points (#5 A-4, A-8, OD-1, OD-3) and HQ-0040 are untouched. Objections within 7 days create a task that reverts the record and its edits.
  >
  > — posted by driver

