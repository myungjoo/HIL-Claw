---
id: T-0389
title: Write ADR-0142, the round-0 steps of a first-case turn after the coder call and the holder of the board-point measurement (part of OD-23; PLAN P2-1/P2-2)
phase: P2
status: DONE
commitMode: doc
coversReq: [FR-1, FR-9, FR-10, OD-23, OD-28, OD-18, S0, S1]
dependsOn: [T-0384, T-0388]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
estimatedSize: {loc: 240, files: 4}
hq: []
---
## Why

All four code slices of ADR-0141 have landed (T-0385 to T-0388). In round 0 the Round-Manager now delegates the coder call to `coder-driver` (step 2 of "The round steps" in `orchestration/round-manager.md`). Then it stops, because "the steps that follow step 2 in round 0 … are not yet defined". No turn reaches the closing steps (`round.end`, `run.commit`), so a first-case run can never finish round 0. PLAN P2-5 (the near goal, D18) needs a round 0 that gets past this stop.

The registers name this gap as open:

- Requirements OD-23 row, `**잔여**:` "첫 사례 라운드 0의 코더 호출 뒤 단계", and "로스터의 나머지(첫 사례에서는 측정·선택 쪽 …)".
- ADR-0128 Consequences, slice 4: the evaluator's delegation steps wait "on the holder of `sim.run` and `board.run`".
- ADR-0128 Boundaries: "the holder of `sim.run`, `board.run` and `measure/` (experiment-runner or another)".

ADR-0119 already decides what round 0 must give for a baseline: checks passed at both points, and one completed `board.run` result of the attempt (decisions 2 and 4). It leaves a round 0 with no attempt that can stand undecided (decision 5).

This is a design-level part of OD-23, which the driver may close by the ADR path (DRIVER §9). The task is part of the PLAN checklist (P2-1/P2-2, with P2-3 for the evaluator's delegation), so the D18 rule for work outside the checklist does not apply.

The task writes only the record. The code slices come after it.

Known state the record must take as it is, not change:

- `sim.run` and `board.run` are **not registered** in `hilclaw.tools.default_registry`. Only their request schema exists, in `hilclaw/run_definition.py` (ADR-0106). PLAN P1-1 stays open on this. The unlanded ADR-0068 (T-0210, branch `claude/T-0210-od18-run-tools-operation-tool-failure`) waits on the unanswered HQ-0021. The `cpu_standin` operations also wait on HQ-0026 and OD-14 ①.
- The backend table of `correctness.check` in `default_registry` holds the mock alone.
- With the package's runtime, `coder.run` fails with `no_container_runtime` until ADR-0049 slice (d) lands (ADR-0141 decision 3). Slice (d) waits on HQ-0053.

Open HQs the record must not cross:

- HQ-0021: the content of ADR-0068 is not landed. Do not cite it as a decision.
- HQ-0053: the coder's sign-in and container start.
- HQ-0031: the duty to test injected hypotheses.
- The runtime-acceptance HQs (HQ-0035, HQ-0042, HQ-0045, HQ-0055, HQ-0056 and the rest): use their items, do not close them.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit), §5 (task format, naming convention, size cap) and §9 (OD closing authority, notice to #5).
- `CLAUDE.md`: all of "상시 규칙", in particular "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분" and "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md`, `.claude/skills/dev-code-review/SKILL.md`.
- `orchestration/round-manager.md` (whole; "The round steps" and "The closing steps of a round"), `orchestration/agents/evaluator.md` (whole), and `orchestration/agents/coder-driver.md` (whole).
- `ARCHITECTURE/decisions/ADR-0141-od23-first-case-coder-run-tool.md`: whole. It is the format model: the Status, Context, Decision with "cited"/"own" sentences, Walk-through, Alternatives, Consequences with slices, "Less exact, not edited" and runtime acceptance items, Boundaries, and References. Decision 6 is the step this record continues.
- `ARCHITECTURE/decisions/ADR-0119-od28-first-case-baseline.md`: decisions 1 to 5 and Boundaries.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: decisions 2 to 7, Consequences and Boundaries.
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md` and `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: the standing an evaluator reports.
- `ARCHITECTURE/decisions/ADR-0061-od18-run-tools-split.md`, `ADR-0062-od18-run-tools-call-identity.md`, `ADR-0063-od18-run-tools-result-members.md`, `ADR-0067-od18-run-tools-admission-kinds.md` and `ADR-0106-od18-run-tools-request-schema.md`: what `sim.run` and `board.run` are, and what they take and return.
- `ARCHITECTURE/decisions/ADR-0113-od13-not-converged-best-baseline.md`: decisions 1 to 3.
- `ARCHITECTURE/decisions/ADR-0126-od23-coder-call-issuer.md`: decisions 2 and 6.
- `ARCHITECTURE/decisions/ADR-0133-od23-first-case-round-promotion.md`: decision 1 (no case in round 0).
- `ARCHITECTURE/decisions/ADR-0135-od23-first-case-round-end-write.md`: decisions 2 to 5.
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decisions 2 and 6.
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`: how the allowed-tools list follows the Round-Manager's fixed list and the agent files.
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md`: decision 1 (round 0 carries no technique).
- `ARCHITECTURE/Requirements.md`: FR-1, FR-9, FR-10, C-4; the "행 형식" paragraph above the OD register (about line 84); the OD-18, OD-23 and OD-28 rows.
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet in the header (line 8); § OD-23 (from about line 401, the roster sub-question about line 405 and "제안으로 남는 부분" about line 426); § OD-28 (from about line 459); § OD-18 only if the record answers part of one of its sub-questions.
- `ARCHITECTURE/StandardScenarios.md`: the check rules (above line 30), S0, S1, and the first paragraph of § 검사 결과 (line 168 on).
- `hilclaw/tools.py` `default_registry` docstring: what is registered today.
- `PROCESS/STATE.json` `humanQuestions`: HQ-0021, HQ-0026, HQ-0031, HQ-0053, HQ-0056 and the open runtime-acceptance HQs.

## Acceptance Criteria

1. A new record `ARCHITECTURE/decisions/ADR-0142-od23-first-case-round-zero-after-coder-call.md` in the form of ADR-0141. Status: accepted by the driver path of DRIVER §9, part of OD-23. Its scope is the runs of ADR-0119 decision 1 with `candidates_per_round` 1 (P2-5's N = 1).
2. The record decides, or leaves open with a stated reason and an owner or OD, each of the following. For each one it weighs at least two alternatives under "Alternatives considered".
   - (a) **No attempt from the call.** What the Round-Manager does after step 2 when the coder-driver reports no attempt it can check. This covers any failure kind, `no_container_runtime` among them, and the interim "no call" on `spec_exists`. The answer must agree with ADR-0119 decision 5. It must not invent a repair, retry or termination rule (OD-19, OD-10).
   - (b) **The checks of round 0.** Which checks of the attempt `0000/01/01` round 0 asks for, at which points and in which order. The work is delegated to the evaluator (ADR-0128). The record also says what the Round-Manager takes from the evaluator's report to decide whether to go on (outcome and standing, ADR-0131, ADR-0110).
   - (c) **The holder of the measurement.** Who holds `board.run`, and `sim.run` if round 0 uses it, in a first-case turn. Weigh at least the Round-Manager inline, a new sub-agent (the experiment-runner of the #4 roster, § OD-23) and any other the executor finds. State why the evaluator is not a candidate (ADR-0128 decisions 3 and 7). Give the effect on the permission lists of ADR-0139.
   - (d) **A `sim.run` timing in round 0.** Whether round 0 asks for one, consistent with ADR-0119 decision 2 ("the sim point is not chosen") and C-4.
   - (e) **After a baseline exists.** Whether round 0 then goes to the closing steps (`case.write` is skipped in round 0, ADR-0133 decision 1; then `round.end`, `run.commit`). Also whether round 0 has any verdicts work (ADR-0138 decision 1: no technique).
   - (f) **Until the run tools are registered.** What the step does while `sim.run` and `board.run` are not registered and the check backend table holds only the mock. For example, a stop that stays, moved later, as ADR-0141 decision 6 moved it. The answer must not depend on the unlanded ADR-0068 or on any answer to HQ-0021, HQ-0026 or HQ-0053.
3. A Walk-through table covers at least these cases: the coder call fails; a check fails at the sim point; a check passes at sim and fails at board; both pass and `board.run` gives a completed result; `board.run` fails or gives only broken results (ADR-0063 decision 2); and a tool is missing from the registry.
4. Consequences lists:
   - The code slices in the order the planner should make them, each code mode and each tested with stub runtimes and a stub `claude` only (D16). The slice that replaces the stop in `orchestration/round-manager.md` must name the test of T-0388 that pins the stop's "not yet defined" sentence (`tests/test_turn_definition.py`).
   - "Less exact, not edited" sentences found by a stated search of `ARCHITECTURE/decisions/`, `orchestration/` and `hilclaw/` docstrings. It is not claimed complete.
   - Any new runtime acceptance items, numbered after (xliii) in the turn-session series, and the items of earlier records the decision uses or narrows. The driver records new items as an HQ with the reason `runtime-acceptance`; the record does not close them.
5. Boundaries names, without deciding them:
   - The owner-only points: the choice among measurements and "better than" (#5 A-4, the rest of OD-1), gates (OD-3), tokens (#5 A-8 beyond HQ-0041's answer), OD-25 and C-6.
   - Repair and its bound (OD-19), failure and retry (OD-10), promotion (OD-15, OD-29), hooks (PLAN P2-4), and the rounds ≥ 1.
6. No sentence of the record says that an owner decided something unless it cites the owner's answer by link. No undecided item is treated as decided (CLAUDE.md "미결은 발명하지 않는다"). If a point turns out to need an owner-only decision, the record leaves it open, and the task returns BLOCKED with the question only if the whole record cannot stand without that answer.
7. `ARCHITECTURE/Requirements.md` is changed in the OD-23 row only, plus the OD-28 or OD-18 row if the record answers part of either, following the register's "행 형식" paragraph: one link to ADR-0142 with a topic of a few words is added after `**확정분**:`, and `**잔여**:` is rewritten in place for what the record answers. Nothing the record decides is restated, and no dated paragraph is added.
8. `ARCHITECTURE/OpenDecisionProposals.md` is changed under its header's "기록 규칙": one `**채택분**` line per touched section, and the status of each answered sub-question and the head word of its bullet rewritten in place. This covers the roster sub-question of § OD-23 and "제안으로 남는 부분" in place. No register text is copied, and no dated note is added.
9. `ARCHITECTURE/StandardScenarios.md`: S0 and S1 (and any other scenario the record touches) are rechecked with the check rules. § 검사 결과 is updated only as its first paragraph prescribes.
10. No file other than the four in `touchesFiles` and this task file's `## Result` is changed. In particular, no file under `orchestration/`, `hilclaw/` or `tests/` and no earlier ADR is changed.
11. Document mode (CLAUDE.md A-13):
    - The work is done on branch `claude/T-0389-adr-first-case-round-zero-after-coder-call`.
    - It passes the context-isolated reviewer cycle (dev-item-address steps 10–12).
    - It is rebased on `origin/main` and pushed to `main` without a PR.
    - The commit message carries `Reviewed-by: reviewer agent (N rounds, Approve)` and the trailer `Task: T-0389`.
12. No `claude` process, container or board is started, and nothing only the runtime has is required (D16).

## Out of Scope

- Any code, prompt or test change: `orchestration/round-manager.md`, `orchestration/agents/*.md`, `hilclaw/`, `tests/`. These are the slices the record lists.
- Registering `sim.run` or `board.run`, or adding `cpu_standin` to the backend table of `correctness.check` (PLAN P1-1; T-0210/HQ-0021, HQ-0026, OD-14 ①).
- The content of the unlanded ADR-0068, ADR-0132 or ADR-0137, and their branches.
- Repair calls, the rounds ≥ 1, the selection side (technique-selector), and `best.json`/`technique_stats.json` (OD-20, OD-7).
- Editing earlier ADRs' "Less exact, not edited" sentences. The PLAN 보류 lines stay as they are.
- The files of open PR #186 (`hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`).

## Follow-ups

- For the planner after landing: the code slices of ADR-0142's Consequences, in its order. Any slice that needs `sim.run` or `board.run` in the registry waits for P1-1 (T-0210/HQ-0021).
- For the driver: the new runtime acceptance items, if any, become one HQ with the reason `runtime-acceptance`. The §9 notice goes to #5.

## Result

DONE. Landed on main as cd4879b (document mode, no PR); Reviewed-by: reviewer agent (7 rounds, Approve); branch deleted.
ADR-0142 (part of OD-23, DRIVER §9 path) for round-0 turns of ADR-0119 decision 1 runs (ADR-0120 decision 1, candidates_per_round 1):
(a) go on only from a coder.run result with non-empty `taken`; every other path stops with round 0 not ended (no round.end; ADR-0119 decision 5); a stopping turn's commit follows the owner's HQ-0043 (a) answer once its record lands.
(b) step 3/4: evaluator checks 0000/01/01 at sim, then board; go on only on standing "verified" from the report.
(c) step 5: new sub-agent `experiment-runner`, tools exactly mcp__hilclaw__board_run, one call with execution 1 (K2 §5, ADR-0128 decision 2); ADR-0139 lists change by derivation only.
(d) no sim.run in round 0. (e) on converged/not_converged: closing steps (no case.write, round.end, run.commit), no verdicts.
(f) until board.run is registered, the stop sits after the board check.
New runtime acceptance items (xliv)-(xlvi) → HQ-0057 (runtime-acceptance, non-blocking). Requirements OD-23 row, OpenDecisionProposals § OD-23 and the StandardScenarios recheck line updated; S0/S1 rechecked, no verdict change, no gap.
§9 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6309370256

Follow-ups (code slices, in order):
1. Now: `orchestration/round-manager.md` steps 3 and 4, their go-on conditions and the stop after step 4; with the "Your run" `Agent` bullet, the `hilclaw/turn_definition.py` docstring and `tests/test_turn_definition.py::test_the_prompt_delegates_to_the_coder_driver_and_keeps_the_stop`.
2. After P1-1 registers `board.run` (T-0210/HQ-0021): `orchestration/agents/experiment-runner.md`, step 5 and the go-on to the closing steps; with the first sentence of "The closing steps of a round".
- A separate record executing the HQ-0043 (a) answer (widening ADR-0127 decision 8 and `run.commit`).
- Two Nits left after the round-7 Approve (fixing them would need round 8): decision 1/7 `no_backend`/`not_offered` grounds should read "ADR-0016 decision 3; ADR-0019 decision 4" with ADR-0016 added to builds-on and References; builds-on ADR-0062 should read "decisions 2, 3" and References ADR-0063 "(decisions 1 to 3; Limits 4)".
