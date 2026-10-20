---
id: T-0359
title: Make verdicts.write hold each check entry against the run's journal, with check_result_invalid and check_unfounded (ADR-0131 decision 5, Consequences slice 2; PLAN P2-3, P2-6)
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-11, FR-17, NFR-1, OD-23, OD-16, OD-30, S0, S1]
dependsOn: [T-0357, T-0358]
touchesFiles:
  - hilclaw/verdicts_tool.py
  - hilclaw/checks_tool.py
  - tests/test_verdicts_tool.py
  - tests/test_checks_tool.py
estimatedSize: {loc: 120, files: 2}
hq: []
---
## Why

ADR-0131 (landed on `main` up to 9e29340) has three code slices. Slice 1 is done: T-0358 added the registry tool `checks.read` in `hilclaw/checks_tool.py` (PR #205, 6dc16dc). This task is **slice 2**. ADR-0131 decision 5 says that `verdicts.write` (ADR-0128 decision 6, `hilclaw/verdicts_tool.py`) refuses a record when any of its `check` entries breaks the rule of ADR-0131 decision 4. Before the write, the tool reads the run's `events.ndjson` from its first line. It raises the log-read kinds of decision 3 for the log, `check_result_invalid` for an end line of an attempt and point that a `check` entry names, and the new kind `check_unfounded` for an entry the log does not found. Slice 3 (`orchestration/agents/evaluator.md` per decision 6) comes after this task.

Priority (DRIVER §6, D18): this is work on the checklist items PLAN P2-3 (evaluator) and P2-6 (verdicts), which come before P2-5, the near goal. ADR-0131 decision 5 answers the cost that ADR-0128 names ("A `check` entry's `outcome` is the evaluator's copy and is not held against the log", OD-16 threat A). It is not input hardening and not a wording cleanup.

Open HQs checked (HQ-0013 to HQ-0047): none is crossed. This is a check inside an existing registry tool. It gives no agent a shell (HQ-0040) and names no model or budget (HQ-0041). It does not touch `sim.run`, `board.run` or the comparison (HQ-0021). It commits nothing (HQ-0043). Its files do not overlap open PR #186 (HQ-0032: `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py`, `tests/test_start_instance.py`). Runtime acceptance item (xxii) of ADR-0131 is not closed by this task.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, D12 test rules).
- `CLAUDE.md`, "상시 규칙": the language policy, the test rules (D12), comment minimisation, "개발 드라이버와 런타임의 구분" (D16), and the code-mode branch and merge procedure (A-13).
- `ARCHITECTURE/decisions/ADR-0131-od23-attempt-check-results-read.md`. This is the specification. Read **decisions 4 and 5 with every bullet**, decision 3's table and the bullets "The reserved kinds of ADR-0019 for the log, widened", "One new kind" and "Every line is read", the Walk-through rows about `verdicts.write` (the `check_unfounded` rows, the damaged-line row and the no-log/no-run row), and Consequences slice 2.
- `ARCHITECTURE/decisions/ADR-0128-od23-first-case-evaluator.md`: decision 6 (the checks of `verdicts.write` before this change).
- `ARCHITECTURE/decisions/ADR-0071-od30-hypothesis-verdict-record.md`: decision 3 (a `check` entry: `ref`, `point`, `outcome`; one entry per `ref` and `point` in a verdict).
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: decision 2 (every ended check counts, every `execution` together).
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md`: decisions 1 to 4 (the `run_file_*` kinds and "not there").
- `hilclaw/verdicts_tool.py`, the whole file. This is the module that changes.
- `hilclaw/checks_tool.py`, the whole file. Look closely at `_lines`, `_outcome`, `_scoped`, `_LOG_KINDS` and `_STEP_OF`. They are the log read and the step-line pass this check needs.
- `hilclaw/verdicts.py`: the module docstring, `_ref` and `_evidence` (the shape of a `ref` and of a `check` entry in a parsed record).
- `hilclaw/check_identity.py`: `SIM`, `BOARD`, `STEPS`. `hilclaw/check_result.py`: `PASS`, `FAIL`, `BROKEN`. `hilclaw/journal.py`: the module docstring, `JournalError`, `identity_of`. `hilclaw/run_files.py`: `reading`, `relative`, `NOT_THERE`, `data_root_is_there`.
- `tests/test_verdicts_tool.py` and `tests/test_checks_tool.py`: the patterns of the existing tests (fixtures, seams for a vanished data root and a failing read, log lines written by `events.append` or as bytes).

## Acceptance Criteria

1. **The order of the checks of `verdicts.write`** becomes the order of ADR-0131 decision 5:
   1. the request, then the record's validity and `run_id` (`invalid_request`);
   2. the data root (`no_data_root`);
   3. the round's `hypotheses.json` (the four `hypotheses_*` kinds);
   4. `verdicts_hypotheses.check` (`verdicts_mismatch`);
   5. no `comparison` entry (`comparison_not_given`);
   6. **new**: the read of `runs/<run_id>/events.ndjson` from its first line, with the kinds of ADR-0131 decision 3 for the log:
      - a data root gone since the source was asked → `run_file_missing`;
      - another failing read of the file system → `run_file_unreadable`;
      - a path that is no regular file, or a damaged complete line anywhere → `run_file_invalid`;
      - a complete line of another version → `run_file_unsupported`.
      The situations of the file come first. Among complete lines, the first in line order decides.
   7. **new**: the step lines, in line order, the first that fails deciding:
      - a step line about any attempt that `journal.identity_of` refuses → `run_file_invalid`;
      - an end line of an attempt and point that some `check` entry of the record names (the entry's `ref` round, candidate and attempt, at the `step` of its `point`, every `execution`) whose `result` has no `outcome` of `"pass"`, `"fail"` or `"broken"` → `check_result_invalid`.
      An end line without an admitted `outcome` outside that scope is no failure.
   8. **new**: every `check` entry founded by ADR-0131 decision 4 (`check_unfounded`). Let O be the outcomes of the end lines of the entry's attempt at its point that hold a `result`, every `execution` together. Then:
      - the entry is founded when its `outcome` is `"pass"`, O is not empty, and every element of O is `"pass"`;
      - the entry is founded when its `outcome` is not `"pass"` and is an element of O;
      - otherwise it is `check_unfounded`. This includes every entry whose O is empty: no line, only `failure` end lines, or only open identities.
      When several entries are unfounded, the first in record order (verdicts in order, then evidence in order) decides. Its message names its path in the record (for example `record.verdicts[0].evidence[1]`) and what the log holds.
   9. the write (`verdicts_exist`, `verdicts_not_written`), unchanged.
2. **Every record reads the log**, including a record with no `check` entry. A damaged log refuses any record (ADR-0131 decision 5, "The log is read for every record").
   - A missing log, or a missing run directory below an existing data root, holds no line and is no failure. A record without a `check` entry is then written. Any `check` entry is then `check_unfounded` (Walk-through, the no-log row).
   - A torn tail is not a line.
3. **Constants**: `KIND_CHECK_RESULT_INVALID` in `verdicts_tool` is the same value as `checks_tool.KIND_CHECK_RESULT_INVALID`, the way the `hypotheses_*` kinds are taken from `hypotheses_tool`. `KIND_CHECK_UNFOUNDED = "check_unfounded"` is a new constant of `verdicts_tool` with a one-line `#:` comment like its neighbours. Neither is added to `tools.RESERVED_KINDS`. No other new kind is added.
4. **Sharing code with `checks_tool`** is the executor's choice (ADR-0131 decision 3, "Left to the code slice"). The two tools must raise the same kind with the same message form for the same log situation. If the executor turns a private helper of `checks_tool` into a public function, or generalises `_scoped`'s scope, then:
   - `checks.read` keeps its behaviour, and `tests/test_checks_tool.py` keeps passing unchanged;
   - the new public name is tested in `tests/test_checks_tool.py` (D12 ③).
   The executor states the choice in `## Result`. If `hilclaw/checks_tool.py` is not touched, the executor drops it and its test file from `touchesFiles` in `## Result`.
5. **Docstrings and description**:
   - The module docstring of `hilclaw/verdicts_tool.py` states the new checks in their order with their kinds. It names ADR-0131 decisions 4 and 5. Its sentence "The only file read is `hypotheses.json`" becomes true again: the files read are `hypotheses.json` and the run's `events.ndjson`.
   - The `definition` docstring lists the new kinds.
   - `_DESCRIPTION` tells the model:
     - that the run's log is read for every record;
     - the rule of decision 4 in one or two plain sentences: `"pass"` only when every recorded result of that attempt at that point passed, otherwise an outcome the log holds, and no `check` entry for an attempt and point without a result;
     - every kind, the new ones included.
   - It keeps the manner of the existing description.
6. **What does not change**:
   - The request and the input schema (`run_id`, `record`).
   - The encoding of the bytes.
   - `verdicts_file.write`, `verdicts_file.validate` and `verdicts.validate`.
   - The tool's `{}` result.
   - Not journaled: the tool appends nothing to `events.ndjson` and selects no backend.
   - It reads no `STATE.json` and creates nothing before the write.
   - A refused record can be corrected and sent again.
   - The `hilclaw/tools.py` registration.
7. **Tests** in `tests/test_verdicts_tool.py`.
   - Existing tests whose records hold `check` entries get log lines that found them, so that they keep testing what they tested.
   - The tests use a temporary data root built by the test, with log lines written by `events.append` or as bytes. No `claude` is started, stub or real. They pass on Linux CI and on the local Windows machine.
   - They cover at least:
     - **happy**:
       - a `"pass"` entry founded by one pass is written;
       - a `"fail"` entry founded by fail-then-pass is written (Walk-through row 2);
       - a `"pass"` entry beside an open identity is written (row 3);
       - two end lines of one `execution`, both pass, found `"pass"`;
       - a record with no `check` entry and no log is written;
       - entries naming attempts of an earlier round than the record's are founded against that round's lines.
     - **branch**:
       - a `"pass"` entry against an attempt with a fail is `check_unfounded` (row "says pass … holds a fail");
       - an entry naming an attempt and point with no result line is `check_unfounded`, with these variants: no line; only a `failure` end line (row 5); only an open identity; lines only at the other point; lines only of another candidate or attempt;
       - a `"broken"` entry when the log holds only `"fail"` is `check_unfounded`;
       - a `check` entry with a missing log is `check_unfounded`;
       - the first unfounded entry in record order decides;
       - an out-of-scope result without `outcome` is no failure;
       - when a step line that breaks ADR-0011 comes before an in-scope bad result, the first in line order decides, and the reverse order as well;
       - each earlier check still wins over the log checks. Example: a `comparison` entry with a damaged log is `comparison_not_given`, and `verdicts_mismatch` comes before `run_file_invalid`.
     - **negative and error**:
       - `run_file_missing` for a data root removed between the source and the read (through a seam);
       - `run_file_unreadable` through a seam, not by changing permissions that Windows ignores;
       - `run_file_invalid` for a directory at the log's place, for a damaged line anywhere, and for a step line about an attempt no entry names that breaks ADR-0011;
       - `run_file_unsupported`;
       - `check_result_invalid` for an in-scope end line whose `result` lacks `outcome`, and for one whose `outcome` is not admitted;
       - after every refusal, no `eval/` file or directory has been created and the log is byte-identical;
       - a refused record that is corrected is then written.
     - **description and kinds**: the existing tests of the description and of no reserved kind cover the two new kinds.
8. **D12 test rules**: ① line and function coverage of `hilclaw/` stays at 80 % or more; ② the tests include happy, error and branch cases and negative cases; ③ every public function of each touched module that changes behaviour is tested; ④ no new module is expected (if one is added, it gets its own test file and is listed in `## Result`); ⑤ no test is added that targets test code, CI, hooks or driver helper scripts.
9. **No data-plane change**: no member, file, kind of event, value or version of `events.ndjson`, `verdicts.json`, `hypotheses.json`, `STATE.json`, `instance.json` or `artifacts.json` is added or changed, and no validator of a data-plane file changes. `check_result_invalid` and `check_unfounded` are tool-layer kinds (ADR-0131 decision 5 and Consequences "A-13 reading"). If the work turns out to need a data-plane change, the executor stops and returns BLOCKED (CLAUDE.md "데이터 plane 스키마 변경").
10. **Language**: Python. The executor records the choice and one reason in the commit body and in `## Result` (CLAUDE.md language policy).
11. **Code mode (A-13)**: a Draft PR whose title contains `T-0359`, the reviewer cycle ending in Approve, CI green, then squash-merge with the PR body ending in `Task: T-0359`, and the branch `claude/T-0359-verdicts-write-log-check` deleted.
12. No `claude` process is started, and nothing runtime-only is required (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/`. This includes the "less exact, not edited" sentences listed in ADR-0131 Consequences, which stay unedited.
- Slice 3: `orchestration/agents/evaluator.md`, its `tools` list, and `tests/test_turn_definition.py`. The Round-Manager's use of the tools.
- A check that the evidence names every attempt of `tested_by`, or a `"pass"` entry checked against the standing (ADR-0131 decision 5, "What it does not hold").
- The comparison tool, `sim.run` and `board.run` (HQ-0021), `eval.json`, and a bound on a result or a paged read (item (xxii)).
- Any change of `hilclaw/tools.py`, the MCP front, `hilclaw/events.py`, `hilclaw/journal.py`, `hilclaw/check_standing.py`, `hilclaw/verdicts_file.py`, `hilclaw/verdicts.py` or `hilclaw/verdicts_hypotheses.py`, or of the files of open PR #186.

## Follow-ups

- Next for the planner: ADR-0131 Consequences slice 3. It changes `orchestration/agents/evaluator.md` as decision 6 says ("A check" and "Verdicts" sections, `mcp__hilclaw__checks_read` in `tools`) and updates that file's `tools`-set test.

## Result
