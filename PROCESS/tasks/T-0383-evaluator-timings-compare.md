---
id: T-0383
title: Give the evaluator definition timings.compare and the comparison work of ADR-0140 decision 6 (ADR-0140 Consequences slice 3; PLAN P2-3, P2-6)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-17, OD-16, OD-23, OD-18, OD-30, S0, S1]
dependsOn: [T-0381, T-0382]
touchesFiles:
  - orchestration/agents/evaluator.md
  - tests/test_turn_definition.py
  - tests/test_turn_permissions.py
estimatedSize: {loc: 60, files: 1}
hq: []
---
## Why

ADR-0140 (T-0380, landed on `main` as 230e70b) decides how a first-case verdict gets the comparison of two attempts. Its Consequences list three code slices:

- Slice 1, the registry tool `timings.compare` (`hilclaw/timings_tool.py`), landed in T-0381 (PR #219, f86bc53).
- Slice 2, decision 5 in `hilclaw/verdicts_tool.py` (`comparison_not_given` removed; `timing_result_invalid` in the step pass; `comparison_unfounded`; `comparison_unverified`), landed in T-0382 (PR #220, 300d880).
- Slice 3 is this task: `orchestration/agents/evaluator.md` becomes what ADR-0140 decision 6 says, and the test of that file's `tools` set changes with it.

Today the definition still tells the evaluator to write every verdict `inconclusive` with no `comparison` entry, and it names `comparison_not_given`, a kind `verdicts.write` no longer has. After this task the evaluator calls `mcp__hilclaw__timings_compare` for the pairs it judges, records the comparisons it is given, and composes each verdict's value by ADR-0071 decision 4. Until `sim.run` and `board.run` are registered (T-0210, HQ-0021) every call answers `measurement_missing`, so every verdict stays `inconclusive` in a real run (ADR-0140 Consequences, "What it does not enable"); the definition is still correct for that case.

Priority (DRIVER §6, D18): this is work on the checklist items PLAN P2-3 (evaluator) and P2-6 (verdicts), which come before P2-5 (the near goal) in the P2 order. It is the last slice of the ADR-0140 record that P2-3 needs. It is not input hardening, a refactor or a wording cleanup: without it the definition is wrong against the landed `verdicts.write` (it names a removed kind and forbids what the write now admits).

Open HQs checked: none is crossed. The definition names no model or budget (HQ-0041, #5 A-8) and gives the evaluator no shell (HQ-0040). It does not register or call `sim.run` or `board.run` (HQ-0021, T-0210). It does not change `orchestration/round-manager.md` (ADR-0140 decision 6: the Round-Manager is not given the tool). Runtime acceptance items of ADR-0128 (HQ-0045) and ADR-0131 (HQ-0047) are not closed by this task. Its files do not overlap open PR #186 (T-0324, HQ-0032: `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0140-od16-first-case-attempt-comparison.md`. This is the specification. Read **decision 2, decision 5 (every bullet) and decision 6 (every bullet)**, the Walk-through, Consequences slice 3 and Boundaries (above all "The base of the comparison").
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decision 3 (the `check` and `comparison` entries, their members and the rules on `measured` and `against`) and decision 4 (counted comparison; as expected / contrary / no difference; `supported`, `refuted`, `inconclusive`; "not different" never refutes).
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: decisions 2 to 7 (copy no computation, the tools, what the evaluator is given, the report, `verdicts.write`, the fixed rules).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`: decisions 4 and 6 (the `check` entry rule and the verdicts work this task extends).
- `ARCHITECTURE/decisions/ADR-0139-od18-first-case-turn-session-permissions.md`: decision 3 (the pre-approved list gains each entry of an agent file's `tools`).
- `orchestration/agents/evaluator.md`, the whole file. This is the file that changes.
- `hilclaw/timings_tool.py`: the module docstring and `_DESCRIPTION` (the request members `run_id`, `metric`, `point`, `measured`, `against`; the result; the kinds in order).
- `hilclaw/verdicts_tool.py`: the module docstring and `_DESCRIPTION` (the checks in order and every kind, as T-0382 left them).
- `tests/test_turn_definition.py`: lines 1 to 25 (`EVALUATOR_TOOLS`) and `test_the_evaluator_frontmatter`.
- `tests/test_turn_permissions.py`: lines 1 to 60 (`EVALUATOR`, `EVALUATOR_TOOLS`), `test_the_evaluator` and `test_the_real_definition`.
- `PROCESS/tasks/T-0360-evaluator-verdicts-work.md`, `## Acceptance Criteria` 4 and `## Follow-ups`: how the refusal split of the definition was stated and why `check_result_invalid` is among the kinds a corrected record cannot answer.

## Acceptance Criteria

1. **Frontmatter of `orchestration/agents/evaluator.md`**: `tools` adds exactly `mcp__hilclaw__timings_compare` (ADR-0140 decision 6). Nothing else of the frontmatter changes: still no `model` key and no `Write`, `Edit`, `NotebookEdit`, `Bash` or agent-delegating tool (ADR-0128 decision 3).
2. **"What you are given" and "Fixed rules"**: the text says that the `difference` of a pair is what `mcp__hilclaw__timings_compare` returns (ADR-0140 decision 2; ADR-0128 decision 2: copy no computation into its own text). "Request no measurement" stays: `timings.compare` is a read and requests no measurement (ADR-0140 decision 2, "Not journaled"). No other fixed rule changes.
3. **"Verdicts"** follows ADR-0140 decision 6:
   - the sentences that each verdict is `inconclusive`, that its `evidence` holds no `comparison` entry, and that its `cause` says no comparison could be given, go;
   - after `mcp__hilclaw__hypotheses_read` and `mcp__hilclaw__checks_read`, for each hypothesis whose `expected` names `latency_minimisation`, the evaluator chooses the pairs it judges — `measured` an attempt of a candidate in the hypothesis's `tested_by` in the file's round, `against` another attempt of the run (the rules of ADR-0071 decision 3 on `measured` and `against` may be cited) — and calls `mcp__hilclaw__timings_compare` for each with `run_id`, `metric`, `point`, `measured` and `against`;
   - on a result it writes a `comparison` entry with the same `metric`, `point`, `measured` and `against` and the returned `difference` copied; on a failure kind it writes no entry for that pair, and the verdict's `cause` says which kind;
   - for a comparison at `board` to count, it adds `"pass"` `check` entries at `board` for both sides only when `checks.read` gave both attempts the standing `"verified"` at `board` (ADR-0140 decision 5); the existing `check` entry rule of ADR-0131 decision 4 stays;
   - it composes each verdict's value by ADR-0071 decision 4. The definition may state that rule in plain words (counted comparison; as expected, contrary, no difference; `supported`, `refuted`, `inconclusive`; "not different" never refutes), citing it, and adds nothing to it;
   - **which attempt `against` is stays its judgement**: the definition names no base, no required set of comparisons and no rule that a verdict must include every comparison (ADR-0140 decision 6 and Boundaries; ADR-0071 decision 4 "Open");
   - it still requests no check on a verdicts delegation, and the round-of-at-least-1 rule stays.
4. **Refusals of `verdicts.write`**: the list of kinds a corrected record can answer becomes `invalid_request`, `verdicts_mismatch`, `check_unfounded`, `comparison_unfounded` and `comparison_unverified`; `comparison_not_given` is gone from the file. On `comparison_unverified` the record is corrected by dropping the two `"pass"` entries or the comparison (ADR-0140 decision 5 and Walk-through; the `verdicts.write` description says the same). `timing_result_invalid` joins `check_result_invalid` among the kinds about a file of the run, reported and ending the work, as T-0360 placed `check_result_invalid`. `verdicts_exist` keeps its sentence. No retry count, budget or other rule that no record gives is added. If the executor or the reviewer finds that placing `timing_result_invalid` needs a choice the records leave open, the executor states only the cited sentences and records the point under `## Follow-ups`.
5. **"Your report"** is unchanged in substance: one line per tool request (now including each `timings_compare` call with its pair and its `difference` or failure kind), and for a written record one line per hypothesis `id` with its `verdict` (ADR-0128 decision 5).
6. **Style**: the definition keeps its form — short bullets, each with its citation in parentheses — and stays a runtime definition in English. It cites; it does not restate the ADRs at length. No `ARCHITECTURE/` file is edited.
7. **Tests** (D12; the definition is layer 1, the tests are the existing Python tests of the files that read it):
   - `tests/test_turn_definition.py`: `EVALUATOR_TOOLS` gains `mcp__hilclaw__timings_compare`. `test_the_evaluator_frontmatter` then holds that the tool is in the set and is served by `default_registry` through the MCP front (it already loops over every `mcp__hilclaw__` entry). Add a test (or an assertion in an existing one) that the file names no `comparison_not_given` (negative: a removed kind must not come back).
   - `tests/test_turn_permissions.py`: `test_the_real_definition` asserts that `mcp__hilclaw__timings_compare` is in the pre-approved list built from the repository definition (ADR-0139 decision 3, source 2). The synthetic `EVALUATOR` fixture and its `EVALUATOR_TOOLS` may stay as they are or gain the tool; if they change, they change together and `test_the_evaluator` stays green.
   - No test of test code, of CI or of hook scripts is added (D12 ⑤).
8. **Local checks**: `ruff check`, `ruff format --check` and the full `pytest` pass; `hilclaw/` line and function coverage stay at least 80 %. No `claude` process is started; nothing outside fixtures and the repository tree is needed (D16).
9. **Result**: record the language line (Markdown for the definition, Python for the tests), the review rounds, the PR and squash commit, and any follow-up.

## Out of Scope

- **Any change under `hilclaw/`**: no change of `timings.compare`, `verdicts.write`, `checks.read`, `hypotheses.read`, the MCP front, `hilclaw/tools.py`, `hilclaw/turn_definition.py` or `hilclaw/turn_permissions.py`.
- **`orchestration/round-manager.md`**: unchanged (ADR-0140 decision 6; its delegation steps wait on HQ-0040 and HQ-0041).
- **Any edit of `ARCHITECTURE/`**: no ADR, register row, proposal section or scenario note. The "Less exact, not edited" sentences of ADR-0140 Consequences in earlier records are not edited.
- **The base of the comparison** (which attempt `against` must be, OD-20, OD-28, OD-29), whether a verdict must include every comparison, sim comparisons on sim-only hardware (OD-26), memory ceilings, and the rest of OD-18 ⑳.
- **Run tools**: `sim.run` and `board.run` and their registration (HQ-0021, T-0210).
- **Runtime acceptance**: whether a live Claude Code session pre-approves and serves the new tool is a runtime acceptance item (ADR-0128 item (xviii), used unchanged per ADR-0140 Consequences); this task does not try it.
- **Open PR #186**: none of its files.

## Follow-ups

## Result
