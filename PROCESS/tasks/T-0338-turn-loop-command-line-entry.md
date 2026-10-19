---
id: T-0338
title: Add the command-line entry of the turn loop for a first-case run, applying ADR-0122 (no further turn after a failed or unchanged turn or in an open state; five outcomes told by exit status and standard streams)
phase: P2
status: DONE
commitMode: code
coversReq: [FR-1, FR-4, NFR-1, NFR-5, OD-8, OD-17, OD-19, S0, S1, S2]
dependsOn: [T-0330, T-0331, T-0336, T-0337]
touchesFiles:
  - hilclaw/turn_start.py
  - hilclaw/further_turn.py
  - hilclaw/turn_loop.py
  - tests/test_turn_start.py
  - tests/test_further_turn.py
estimatedSize: {loc: 230, files: 3}
hq: []
---
## Why

PLAN P2-1 (Round-Manager prompt and round-0 procedure) is the first unchecked item of the P2 order (D18), and this task is one of its slices, so the D18 priority rule does not apply. The P2-5 run (`cpu_standin` x GEMM, N=1, 5 rounds) needs something a person or a CI can start that drives one run turn by turn. Today the parts exist but nothing joins them, and nothing calls them:

- `hilclaw.turn_loop.run` (T-0330) starts one `claude -p` per turn, asking a caller-given `further_turn(previous)` before each turn;
- `hilclaw.turn_definition.put` (T-0331) copies `orchestration/` into the session directory;
- `hilclaw.further_turn` (T-0336) classifies the run's files into P1 to P4 of ADR-0121 decision 5, or open.

ADR-0122 (T-0337, main 8ea7115) decided what the loop does where step 1 was still open, and its Consequences name this code slice: the loop's command-line entry. It composes those parts with `hilclaw.config` for the data root. It starts no further turn after a turn whose exit status is not 0 (decision 2), after an exit-0 turn that left the run as it found it (decision 3), or in an open state (decision 4). It tells the starter one of five outcomes, or an error (decision 5). Without the decision-3 check, the placeholder definition (every turn "ends the session without writing any file") would start turns without end, each spending plan usage.

All verification uses a stub `claude` that the tests write. No real `claude` is started (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, size cap, test rules D12).
- `CLAUDE.md`: "상시 규칙" (comment policy, layer-2 language policy, test rules ①–⑤, branch/merge procedure for code mode, the driver/runtime separation D16).
- `ARCHITECTURE/decisions/ADR-0122-od19-turn-loop-open-states.md`: Decision §1–§6, Walk-through, Consequences ("The code slice it enables", "Less exact, not edited" — the code bullet), Boundaries. This is the specification of this task.
- `ARCHITECTURE/decisions/ADR-0121-od8-run-over-member.md`: decision 5 (the P1–P4 table and the "Open" bullet).
- `ARCHITECTURE/decisions/ADR-0118-od18-round-process-boundary.md`: decision 3 ("What starts the loop", "Two loops on one run").
- `ARCHITECTURE/decisions/ADR-0012-od8-runtime-state-file.md`: decisions 3 and 6 (`round` changes only in the write that ends a round; an invalid `STATE.json` is an error).
- `hilclaw/turn_loop.py` (whole file: module docstring, `run`, `ClaudeNotFoundError`, the prompt rule `[A-Za-z0-9 .,_]+`).
- `hilclaw/further_turn.py` (whole file).
- `hilclaw/turn_definition.py` (module docstring, `put`, `SOURCE`).
- `hilclaw/data_root_source.py` (`configured`) and `hilclaw/config.py` (`load_data_repo`, `ConfigError`).
- `hilclaw/run_journal.py` `read_state` and `hilclaw/run_state.py` `RunState` (the `round` member).
- `hilclaw/__main__.py` and `hilclaw/selfcheck.py` `main`: existing command-line conventions (injectable `argv`/streams, binary standard streams, the exit statuses 1 and 2 left to the interpreter).
- `tests/test_turn_loop.py` lines 60–185: the stub `claude` fixture, the `PATH` setup and the skip when a marker (`CLAUDE.md`, `.claude`, …) lies above the test's temporary directory.
- `tests/test_further_turn.py` (the existing assertions on `Finding`).

## Acceptance Criteria

Language: Python (the entry composes existing in-process Python functions). Record the choice and reason in one line in the commit body and in `## Result

- Landed: PR #193, squash-merged as 8ea06d5 on main; branch claude/T-0338-turn-loop-command-line-entry deleted. Branch commits e736d70 (implementation) and 2566cf0 (review fix).
- Review: 2 rounds, context-isolated dev-reviewer. Round 1 Approve with one Nit: `_say` swallowed only OSError/ValueError, so a text stream given as stderr let TypeError leave `main`. Fixed by suppressing any Exception, with a test. Round 2 Approve.
- CI: all gates green on head 2566cf0 (Python 3.11/3.14, Coverage, Test presence, sh, C). Local: full pytest passed (23783 passed); coverage turn_start.py 98 % (the one missed line is the `__main__` guard, run only in a subprocess), further_turn.py 100 %, hilclaw/ total 99 %. Locally the stub tests need `--basetemp` outside %TEMP%, because the machine's system temp holds a CLAUDE.md that triggers the marker skip.
- Language: Python, because the entry composes existing in-process Python functions of the layer-2 package.
- What was built: `python -m hilclaw.turn_start <run_id>`. It gets the data root once from the data-root source (default `data_root_source.configured`) and calls `turn_loop.run` once with `turn_definition.put` and a fixed prompt that does not name the run.
  - Step 1 makes one `further_turn.classify` call per answer and keeps the previous finding for decision 3. Precedence: P2, P3, open state, decision 2, decision 3.
  - Each outcome writes one compact JSON line on stdout with a member `outcome` and has its own exit status: run_over 0, unknown_run_status 10 (`run_status`), failed_turn 11 (`exit_status`), unchanged_turn 12, open_state 13 (`reason`, plus `exit_status` after a failed turn).
  - The error is `outcome` "error" with exit status 20 and a member `error` of bad_usage, no_data_root, no_claude or fault. Only the error writes stderr, one free-text line. No status is 1 or 2.
- Way chosen for AC 3/4: step 1 calls `classify` directly instead of `predicate` with a fallback (ADR-0122 Consequences names the latter). Wrapping `predicate` would need a second `classify` read to get `round` for decision 3, which breaks "one finding". `classify` now carries one of seven public reason constants in `Finding.value` for OPEN (STATE_MISSING, STATE_INVALID, STATE_VERSION, INSTANCE_MISSING, INSTANCE_INVALID, INSTANCE_VERSION, NO_ROUND_BUDGET) and `round` for DUE. What it reads, which case it returns, and `predicate`'s answers and signature are unchanged.
- Docstrings corrected for ADR-0122 in hilclaw/turn_loop.py (no code change) and hilclaw/further_turn.py.
- Size: about 311 inserted and 35 deleted non-test lines, slightly above the 300 LOC cap of DRIVER §5. About 85 of them are the module docstring that AC 6/7 ask for. Not split; the reviewer accepted it, recorded here.
- Follow-ups:
  - How a turn session learns which run it carries. No record decides it; the module docstring states it as open. Needed before the round-0 part of the Round-Manager prompt; whether it is a design-level OD question or needs an owner answer is for the planner of that slice.
  - The remaining P2-1 slices: OD-18 ⑯ (가), OD-8 ⑪, how the Round-Manager reaches `replace` (OD-23, OD-18), then the round-0 part of the Round-Manager prompt.
  - Until the lock of two loops on one run exists (rest of OD-17), no schedule may start the entry. Stated in the docstring, not enforced.
  - Runtime acceptance items (v), (vi) and (viii) of ADR-0118/ADR-0122 are unchanged and remain owner or runtime items.
