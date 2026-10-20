---
id: T-0360
title: Give the evaluator definition checks.read and the verdicts work of ADR-0131 decision 6 (ADR-0131 Consequences slice 3; PLAN P2-3, P2-6)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-11, FR-17, OD-23, OD-16, OD-30, S0, S1]
dependsOn: [T-0357, T-0358, T-0359]
touchesFiles:
  - orchestration/agents/evaluator.md
  - tests/test_turn_definition.py
estimatedSize: {loc: 60, files: 1}
hq: []
---
## Why

ADR-0131 (landed on `main` up to 9e29340) has three code slices. Slice 1, the registry tool `checks.read` (`hilclaw/checks_tool.py`), landed in T-0358 (PR #205, 6dc16dc). Slice 2, the log check of `verdicts.write` (`check_result_invalid`, `check_unfounded`), landed in T-0359 (PR #206, 11ca25f). This task is **slice 3**: `orchestration/agents/evaluator.md` becomes what ADR-0131 decision 6 says, its `tools` list gains `mcp__hilclaw__checks_read` (decision 7), and the `tools`-set test of that file follows. After this, the evaluator reports the standing of a check, and on a verdicts delegation it writes the round's verdicts, every one `inconclusive`, instead of the one-line "cannot yet" report.

Priority (DRIVER §6, D18): this is work on the checklist items PLAN P2-3 (evaluator) and P2-6 (verdicts), which come before P2-5, the near goal. Without it, every round of the first run that reaches evaluate ends without verdicts (FR-17; ADR-0131 decision 6, "Weighed against FR-17"). It is not input hardening and not a wording cleanup.

Open HQs checked: none is crossed. The definition names no model or budget (HQ-0041, #5 A-8) and gives the evaluator no shell (HQ-0040). It does not touch `sim.run`, `board.run` or the comparison (HQ-0021). It does not change `orchestration/round-manager.md`, whose delegation steps wait on HQ-0040 and HQ-0041. Runtime acceptance items (xviii) to (xx) of ADR-0128 (HQ-0045) and (xxii) of ADR-0131 (HQ-0047) are not closed by this task. Its files do not overlap open PR #186 (HQ-0032: `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`. This is the specification. Read **decision 4 (every bullet), decision 6 (every bullet, above all "What `orchestration/agents/evaluator.md` becomes in the code slice") and decision 7**, the Walk-through, Consequences slice 3 and Boundaries.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: decisions 2 to 7 (the holder, the tools, what it is given, the report, `verdicts.write`, the fixed rules of the definition) and the Walk-through.
- `ARCHITECTURE/decisions/ADR-0129-od23-round-hypotheses-read.md`: decisions 2, 3 and 5 (the `hypotheses.read` request, round from 1, and the "cannot yet" report this task removes).
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decisions 1, 3 and 4 (written once and never replaced; a `check` entry is `ref`, `point`, `outcome`, one per `ref` and `point`; `inconclusive` with no counted comparison).
- `orchestration/agents/evaluator.md`, the whole file. This is the file that changes.
- `orchestration/round-manager.md`, only for the style of the runtime's definitions (citations in parentheses, one-line reports). It is not changed.
- `hilclaw/checks_tool.py`: the module docstring and `_DESCRIPTION` (request members `run_id`, `round` from 0, `candidate`, `point` required and `attempt` optional; the result; the kinds).
- `hilclaw/verdicts_tool.py`: the module docstring and `_DESCRIPTION` (the checks in order and every kind, `check_result_invalid` and `check_unfounded` included).
- `hilclaw/hypotheses_tool.py`: the module docstring and `_DESCRIPTION`.
- `tests/test_turn_definition.py`: lines 1 to 25 (`EVALUATOR_TOOLS`) and `test_the_evaluator_frontmatter`.
- `PROCESS/tasks/T-0354-evaluator-agent-definition.md`, `## Result`, the last bullet: the reviewer's note on "can be corrected and sent again" that this task takes up (criterion 4).

## Acceptance Criteria

1. **Frontmatter of `orchestration/agents/evaluator.md`**: `tools` adds exactly `mcp__hilclaw__checks_read` (ADR-0131 decision 7). Nothing else of the frontmatter changes. In particular there is still no `model` key and no `Write`, `Edit`, `NotebookEdit`, `Bash` or agent-delegating tool (ADR-0128 decision 3).
2. **"A check"** follows ADR-0131 decision 6:
   - after `mcp__hilclaw__correctness_check` has answered, with a result or a tool failure, the evaluator calls `mcp__hilclaw__checks_read` with the same `run_id`, `round`, `candidate`, `attempt` and `point`;
   - it reports the `outcome` or failure kind that `correctness.check` returned and the `standing` that `checks.read` returned, or the failure kind of `checks.read` (ADR-0128 decision 5);
   - the sentences that no tool gives the standing, and that the evaluator must not report a standing, go. The rule that it does not work out a standing from the log itself stays in substance (ADR-0128 decision 2: it copies no computation into its own text).
3. **"Verdicts"** follows ADR-0131 decision 6:
   - the paragraph that the verdicts work is not yet given, the one-line "cannot yet" report, "You need not call `mcp__hilclaw__hypotheses_read`" and "Later slices of the definition replace this paragraph" go;
   - on a verdicts delegation the evaluator reads the round's hypotheses with `mcp__hilclaw__hypotheses_read` (`run_id`, `round`);
   - for each candidate of each hypothesis's `tested_by`, it calls `mcp__hilclaw__checks_read` **without `attempt`** at the points it judges (which attempts and points a verdict names stays its judgement — ADR-0131 decision 4, last bullet);
   - it composes one verdict per hypothesis, `verdict` `inconclusive`, with `check` entries only and no `comparison` entry (ADR-0128 decision 6);
   - each `check` entry follows the rule of ADR-0131 decision 4, stated in plain words: `"pass"` only when the attempt holds at least one ended result at that point and every one is `"pass"`; otherwise an outcome among those results that is not `"pass"`; and no `check` entry for an attempt and point with no ended result (no line, only `failure` results, or only open checks);
   - each verdict's `cause` says that no comparison could be given and what the checks showed (ADR-0131 decision 6);
   - it sends the whole record with `mcp__hilclaw__verdicts_write`;
   - it still requests no check on a verdicts delegation (ADR-0128 decision 7; the fixed rule "Request a check only for the tuple and the point you were given" covers it, and the executor makes sure the text does not read otherwise);
   - it reports as ADR-0128 decision 5 says: one line per tool request, and for a written record one line per hypothesis `id` with its `verdict`.
4. **Refusals of `verdicts.write`**. ADR-0131 decision 6 says "correcting and sending again on a refusal", and ADR-0128 decision 6 says a refused record "can be corrected and sent again". The text keeps this. Following the T-0354 reviewer note, it says which refusals a corrected record can answer, by what the kinds mean and no further: the kinds about the record itself (`invalid_request`, `verdicts_mismatch`, `comparison_not_given`, `check_unfounded`). For any other kind (`no_data_root`, the `hypotheses_*` kinds, the `run_file_*` kinds, `check_result_invalid`, `verdicts_not_written`) the evaluator reports the kind and ends, since no change of the record answers it. On `verdicts_exist` the file was already written and nothing is replaced (ADR-0071 decision 1). The definition adds **no retry count, budget or other rule** that no record gives. If the executor or the reviewer finds that this split cannot be stated without a choice the records leave open, the executor keeps only the cited sentences ("a refused record can be corrected and sent again"; `verdicts_exist`) and records the point under `## Follow-ups`; it does not invent the choice.
5. **Style and limits**:
   - Every rule cites its source in parentheses, in the manner of the existing file. Nothing is added beyond ADR-0128, ADR-0129, ADR-0131 and the records they cite, except the wording of the reports.
   - The "Fixed rules", "What you are given" and "Your report" sections stay in substance. A citation may gain ADR-0131 where the rule now rests on it.
   - The file name and every name below `orchestration/` keep the naming rule of ADR-0118 decision 5.
   - English, Markdown.
6. **Tests** in `tests/test_turn_definition.py`:
   - `EVALUATOR_TOOLS` gains `mcp__hilclaw__checks_read`. `test_the_evaluator_frontmatter` then checks the new exact set and, through its existing loop, that `checks_read` is served by `tools.default_registry` through the MCP front.
   - No other test changes are expected. The existing test that `put` copies `.claude/agents/evaluator.md` byte for byte keeps passing.
   - No `claude` is started, stub or real. The tests pass on Linux CI and on the local Windows machine.
7. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more (no `hilclaw/` code changes); ② the changed test keeps its negative path (a tool outside the expected set, or one not served, fails the assertion); ③ no public function of `hilclaw/` changes; ④ no new module is added; ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
8. **No change** to any tool, registry entry, kind, description, validator or `hilclaw/` module, and **no data-plane change**. If the work turns out to need one, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
9. **Language**: the definition is Markdown (layer 1), the test change is Python. Record this and one reason in the commit body and in `## Result`.
10. **Code mode (A-13)**: a Draft PR whose title contains `T-0360`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0360`, and the branch `claude/T-0360-evaluator-verdicts-work` deleted.
11. No `claude` process is started, and nothing runtime-only is required (D16). Runtime acceptance items (xviii) to (xx) and (xxii) are not closed by this task.

## Out of Scope

- Any edit of `ARCHITECTURE/`, including the "Less exact, not edited" lists of ADR-0131 and ADR-0128, and ADR-0129 decision 5's "cannot yet" sentences. They stay unedited.
- `orchestration/round-manager.md` and its delegation steps (HQ-0040, HQ-0041); the Round-Manager's use of `checks.read` (ADR-0131 decision 7).
- The comparison tool, `sim.run`, `board.run` (HQ-0021), `eval.json`, a re-judgement of `inconclusive` verdicts, and a bound on a result or a paged read (item (xxii)).
- Any change to `hilclaw/` code or docstrings, including `hilclaw/turn_definition.py`, `hilclaw/checks_tool.py` and `hilclaw/verdicts_tool.py`.
- Merging `hilclaw/check_identity.py`'s private `_STEP_OF` with `checks_tool.STEP_OF` (T-0359 review nit; set aside under D18).
- The files of open PR #186.

## Follow-ups

- After this, ADR-0131's slices are done. The next evaluator work, the comparison of ADR-0007 decision 7 for two attempts, needs its own record (ADR-0131 Consequences slice 4) and depends on `sim.run`/`board.run` (T-0210, HQ-0021).

## Result
