---
id: T-0338
title: Add the command-line entry of the turn loop for a first-case run, applying ADR-0122 (no further turn after a failed or unchanged turn or in an open state; five outcomes told by exit status and standard streams)
phase: P2
status: IN_PROGRESS
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

Language: Python (the entry composes existing in-process Python functions). Record the choice and reason in one line in the commit body and in `## Result`.

### The entry (`hilclaw/turn_start.py`, new)

1. Command line `python -m hilclaw.turn_start <run_id>`: exactly one argument, the run id, checked with `hilclaw.layout.check_run_id` before anything else is read. The tool front `hilclaw/__main__.py` is not changed. A public `main(argv=None, *, ...)` returns the exit status. It takes injectable keyword arguments at least for the data-root source (default `hilclaw.data_root_source.configured`), the session-directory `parent` passed to `turn_loop.run` (default `None`) and the standard streams, so tests need no global state. `if __name__ == "__main__": raise SystemExit(main())`.
2. The data root comes from the data-root source. A `ConfigError`, or a root that is not an existing directory, is an error (item 8). The definition is `hilclaw.turn_definition.put` with its default `SOURCE`. The prompt is one fixed line that satisfies the prompt rule of `turn_loop`. It does not name the run. How a turn session learns which run it carries is not decided by any record, so do not invent it; state it as open in the module docstring and in `## Follow-ups`.
3. Step 1 (each call of the `further_turn` given to `turn_loop.run`) bases its answer and its outcome on **one** `classify` finding of the run. The entry may build on `further_turn.predicate` or call `classify` directly. Either way it gives the P1–P4 answers of ADR-0121 decision 5 as narrowed by ADR-0122, in the precedence order of ADR-0122 decision 5: P2, then P3, then open state, then decision 2, then decision 3.
   - **P2** (`run_status` `"over"`): no further turn; outcome "run over", whatever the previous exit status.
   - **P3** (any other `run_status` value): no further turn; outcome "unknown run_status", with the value.
   - **Open state** (ADR-0122 decision 4): no turn, before the first turn as well as after any turn. Outcome "open state", naming which of the seven states it is: `STATE.json` missing beyond P1, invalid, or of another version; `instance.json` missing, invalid, or of another version beside a valid version-1 `STATE.json` without `run_status`; no `round_budget`. After a turn whose exit status was not 0, the outcome also carries that status.
   - **Decision 2**: after a turn whose exit status is not 0, in P1 or P4: no further turn; outcome "stopped after a failed turn", with the exit status.
   - **Decision 3**: after a turn with exit status 0, no further turn when the state is P1 both before and after that turn, or P4 both before and after with the same `round` (equality only; `round` is never compared with `round_budget`). Outcome "stopped after an unchanged turn". P1 before and P4 after, or P4 with another `round`, is progress: a further turn.
   - Before the first turn of a start, P1 and P4 answer a further turn.
4. To tell the open states apart and to read `round` in P4, extend `hilclaw.further_turn.classify` without changing what it reads or which case it returns:
   - `Finding.value` of `OPEN` carries one of seven new public reason constants;
   - `Finding.value` of `DUE` carries `round`, read from the same `STATE.json` read.
   - `predicate` keeps its present answers and signature.
   - Update the `classify` docstring and the existing assertions in `tests/test_further_turn.py`.
   - If you choose another way to get the same information from one read, explain it in `## Result`.
5. Kept from ADR-0122 decision 1. The entry writes nothing into the run or anywhere else on the starter's behalf: no `run_status`, no file, no notification. It makes no judgement, calls no model and is no FR-10 tool (it is not registered in `hilclaw.tools`). It has no retry, retry count, pause or turn-count bound.
6. **Outcomes through the process only** (decision 5):
   - Each of the five outcomes and the error writes exactly one line on standard output naming its kind and its datum (exit status, `run_status` value, open-state reason). You choose the encoding (for example one JSON object per line) and document it in the module docstring.
   - "Run over" is the only outcome with exit status 0.
   - The error has an exit status distinct from all five outcomes.
   - Whether the other four share a status is your choice, documented. Do not use 1 or 2 (the interpreter's).
   - Standard error gets at most one line of free text, which is never parsed.
7. The module docstring states the limit ADR-0122 Consequences gives: until the lock of two loops on one run exists (rest of OD-17), no starter may start the entry on a run where a loop may still be running, so no schedule may start it yet. The entry does not try to enforce this.
8. **Errors** (one error kind, told apart from the five outcomes; no traceback reaches the starter): a wrong argument count or invalid run id; a data-root source failure or a root that is no existing directory; a refused place (`ValueError` from `turn_loop.run`); no `claude` found (`ClaudeNotFoundError`); and any other `Exception` raised by `turn_loop.run` or by reading the run. `KeyboardInterrupt` and `SystemExit` are not caught.

### Docstring corrections (named by ADR-0122 Consequences, "In code")

9. `hilclaw/turn_loop.py`: the sentence "no command-line entry, which waits on the OD-8 member …" and "Nothing calls the module yet" are corrected to point at `hilclaw.turn_start`. The policy after a failed turn is now that entry's (ADR-0122), not the loop's. Change no code in this file.
10. `hilclaw/further_turn.py`: "has no command-line entry" and the "**Open** … what follows a failed turn …; and the loop's command-line entry" paragraph are corrected for ADR-0122. The paragraph on exit-0 unchanged turns is kept true: the predicate alone still does not catch them, and the entry does.

### Tests (`tests/test_turn_start.py`, new; `tests/test_further_turn.py`, updated)

11. Use a stub `claude` on `PATH` written by the test, following `tests/test_turn_loop.py`, including its skip when a marker lies above the temporary directory. The stub can be told, per call, which exit status to return and which run files to write (for example a first `STATE.json`, a `round` increment, `run_status` `"over"`), so the walk-through rows can be driven. Never start a real `claude`.
12. Cover, at least, as asserted outputs and exit statuses:
    - **Happy:**
      - a fresh run where the stub writes the first `STATE.json` (P1 → P4), then ends rounds until it writes `"over"` → "run over", status 0, with the expected number of stub calls;
      - P2 at once → no stub call.
    - **Decision 2:**
      - a stub exiting non-zero on a fresh run → failed-turn outcome with that status, one call;
      - the same in P4.
    - **Decision 3:**
      - the placeholder-like stub (exit 0, writes nothing) on a fresh run → unchanged-turn outcome after exactly one call;
      - P4 with the same `round` after the turn → unchanged after one call;
      - P1 → P4 and then P4 unchanged → exactly two calls.
    - **Open states:** each of the seven reasons before the first turn, with no stub call. Also one open state reached after a failed turn, told with the exit status.
    - **Precedence:** a stub that writes `"over"` and exits non-zero → "run over".
    - **P3:** a non-`"over"` value, a non-string value included → its value reported.
    - **Errors / negative:**
      - no argument, two arguments, an invalid run id;
      - a data-root source that raises `ConfigError`, and a root that is no directory;
      - no `claude` on `PATH`;
      - a refused `parent`;
      - an unexpected exception from `turn_loop.run` (monkeypatched).
      - Each error test also asserts that nothing was written into the run.
    - The entry writes nothing into the run in any outcome: compare the run tree before and after, ignoring what the stub wrote.
13. All public functions of `hilclaw/turn_start.py` and of `hilclaw/further_turn.py` are tested. The `hilclaw/` totals of line and function coverage stay ≥ 80 %. `ruff check`, `ruff format --check` and the full `pytest` suite pass locally and in CI.
14. Code mode: Draft PR titled with `T-0338`, PR body ending in `Task: T-0338`, reviewer cycle, CI green, then squash-merge with `gh pr merge --squash --body` and delete the branch `claude/T-0338-turn-loop-command-line-entry`.

## Out of Scope

- The lock of two loops on one run and fencing (rest of OD-17); a retry, pause or usage-limit handling (rest of OD-19, ADR-0122 decision 6); notification channels (OD-27); recovery inside a turn (OD-10).
- What ends a run without `round_budget` (OD-8 ㉙ (나)); a "waiting"/"stopped" `run_status` value.
- How the turn session learns which run it carries; the Round-Manager's round steps and round-0 procedure; anything under `orchestration/`; permissions and hooks (P2-4); the commit step (OD-8 ⑪).
- Calling the start function of ADR-0115 (`hilclaw/start_instance.py`, open PR #186): do not touch it.
- Any edit to `ARCHITECTURE/` (the less-exact ADR sentences listed in ADR-0122 Consequences stay as they are), `README.md`, CI, `.claude/`, `pyproject.toml`; any new dependency; any data-plane schema or validator change (`STATE.json`, `instance.json` validators unchanged).
- Starting a real `claude`, or requiring a logged-in `claude`, a board or an API key (D16). That a real session behaves as the stub does stays runtime acceptance items (v), (vi) and (viii) of ADR-0118 and ADR-0122.

## Follow-ups

- How a turn session learns the run it carries (needed before the round-0 part of the Round-Manager prompt). Whether this is a design-level OD question or needs an owner answer is for the planner of that slice.
- The remaining P2-1 slices: OD-18 ⑯ (가), OD-8 ⑪, how the Round-Manager reaches `replace` (OD-23, OD-18), then the round-0 part of the Round-Manager prompt.
- Size: if the entry exceeds the cap, split as DRIVER §5 says. One example split is the `classify` extension first, then the entry.

## Result
