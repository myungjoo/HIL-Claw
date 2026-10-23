---
id: T-0360
title: Give the evaluator definition checks.read and the verdicts work of ADR-0131 decision 6 (ADR-0131 Consequences slice 3; PLAN P2-3, P2-6)
phase: P2
status: DONE
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
4. **Refusals of `verdicts.write`**. ADR-0131 decision 6 says "correcting and sending again on a refusal", and ADR-0128 decision 6 says a refused record "can be corrected and sent again". The text keeps this. Following the T-0354 reviewer note, it says which refusals a corrected record can answer, by what the kinds mean and no further: the kinds about the record itself (`invalid_request`, `verdicts_mismatch`, `comparison_not_given`, `check_unfounded`). For any other kind (`no_data_root`, the `hypotheses_*` kinds, the `run_file_*` kinds, `check_result_invalid`, `verdicts_not_written`) the evaluator reports the kind and ends, since no change of the record answers it. On `verdicts_exist` the file was already written and nothing is replaced (ADR-0071 decision 1). The definition adds **no retry count, budget or other rule** that no record gives. If the executor or the reviewer finds that this split cannot be stated without a choice the records leave open, the executor keeps only the cited sentences ("a refused record can be corrected and sent again"; `verdicts_exist`) and records the point under `## Follow-ups

- The definition does not say what the evaluator does when `hypotheses_read` or `checks_read` fails during the verdicts work, beyond reporting the failure kind under "Your report". No record decides it, so nothing was added (reviewer observation, rounds 1 and 2).
- `check_result_invalid` is put among the kinds a corrected record cannot answer, as the task specified (it names a fault in the log). `verdicts.write` raises it only for an attempt and point that a check entry names, so a record that drops that entry would avoid it. If an owner reading prefers otherwise, the refusal sentence can be narrowed.
- ADR-0131's code slices are done. The next evaluator work, the comparison of ADR-0007 decision 7 (ADR-0131 Consequences slice 4), needs its own record and depends on `sim.run`/`board.run` (T-0210, HQ-0021).

## Result

- DONE. PR #207 (https://github.com/myungjoo/HIL-Claw/pull/207), squash-merged as 3354ddc; branch `claude/T-0360-evaluator-verdicts-work` deleted.
- `orchestration/agents/evaluator.md` (ADR-0131 decisions 6 and 7):
  - frontmatter `tools` adds exactly `mcp__hilclaw__checks_read`; still no model key, Write, Edit, NotebookEdit, Bash or delegating tool.
  - "What you are given" gains one clause: the journaled results and the standing are what `checks_read` returns (ADR-0131 decisions 2 and 3).
  - "A check": after `correctness_check` answers (result or failure), call `checks_read` with the same run_id/round/candidate/attempt/point; report the outcome or failure kind together with `checks_read`'s standing or failure kind. "Do not work out a standing from the log yourself" stays (ADR-0128 decision 2; ADR-0131 decision 3).
  - "Verdicts": the "cannot yet" paragraph is gone. The work is now: request no check; read the hypotheses with `hypotheses_read`; call `checks_read` without attempt for each candidate of each `tested_by`, at the points judged; for a round of at least 1, compose one `inconclusive` verdict per hypothesis with check entries only, each stated by ADR-0131 decision 4; write a cause saying no comparison could be given and what the checks showed; send the record with `verdicts_write`.
  - Refusals: the kinds about the record itself (`invalid_request`, `verdicts_mismatch`, `comparison_not_given`, `check_unfounded`) are named as the ones a corrected record answers; any other kind is reported and ends the work; on `verdicts_exist` nothing is replaced (ADR-0071 decision 1). No retry count or budget was added (takes up the T-0354 reviewer note).
- `tests/test_turn_definition.py`: `EVALUATOR_TOOLS` gains `mcp__hilclaw__checks_read`; the existing loop checks it is served by `default_registry` through the MCP front. Negative path kept.
- Language: Markdown for the definition (layer 1, read by Claude Code); Python for the test (the package's test language).
- Tests: local ruff check / ruff format --check clean; full local pytest exit 0. CI green on head 306619a (Python 3.11/3.14, coverage, C, shellcheck, test presence).
- Review: 2 rounds (round 1 Approve with two nits, both fixed; round 2 Approve, no findings).
- No `hilclaw/` code, tool, kind or data-plane change. No `claude` process was started (D16). Runtime acceptance items (xviii)-(xx) (HQ-0045) and (xxii) (HQ-0047) are not closed.
