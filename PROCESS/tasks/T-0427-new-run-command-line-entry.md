---
id: T-0427
title: Add the command-line entry python -m hilclaw.new_run <file> that hands a person's or a script's instance document to hilclaw.start_instance.start and reports the run id or why nothing was started (ADR-0155 code slice; PLAN P2-5)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-13, OD-23, OD-8, "UC-1", "PLAN P2-5"]
dependsOn: [T-0426]
touchesFiles: [hilclaw/new_run.py, tests/test_new_run.py, hilclaw/start_instance.py]
estimatedSize: {loc: 200, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `ba4aa06`):
- ADR-0155 (T-0426, landed as `6f2a4ef`) decides that a person or a script starts a first-case instance (ADR-0076 decision 1) with `python -m hilclaw.new_run <file>`. It is a new module `hilclaw/new_run.py`, not a registry tool. Its Consequences name this code slice: the module, its test file `tests/test_new_run.py`, and the docstring fix of `hilclaw/start_instance.py`.
- `hilclaw.start_instance.start(document, *, data_root)` (T-0324) exists and needs no change. No module calls it. Outside a test, nothing can write the `instance.json` of a run, so the PLAN P2-5 run, and later the P2-10 nightly run, cannot be started.
- `hilclaw/new_run.py` and `tests/test_new_run.py` do not exist.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items P2-1 to P2-4, P2-6 and P2-7 have no part that can be taken now: round 0's board step waits on HQ-0021, the round >= 1 steps on HQ-0048, the gate half of P2-4 is owner-only (OD-3), and P2-6/P2-7 wait on HQ-0048 and HQ-0031. This entry is work of P2-5, because a run has to be started before any of its rounds. It is a slice of a recorded decision, not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, D16.** ADR-0155 decides everything this task needs. What it leaves to the code task (decision 5: the words of `outcome`, the other member names, the status numbers, the texts and the order of the checks; decision 3: the decoding rules) are this task's choices, not owner decisions. The ADR's 7-day objection window runs from 2026-10-24. If the owner objects, the DRIVER §9 revert covers this code too. The entry starts no `claude`, no container and no board. The tests use fixtures and temporary data roots only, and no stub `claude` is needed. Nothing is required of this machine.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming convention, size cap, the D12 test rules).
- `CLAUDE.md`: "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0155-od23-first-case-instance-start-command-line.md`, whole (165 lines). It is the specification, in particular:
  - decisions 2 to 6 (lines 35-92);
  - the report table and the paragraphs "When the line cannot be written" and "Fixed here / Left to the code task" (lines 62-83);
  - the Walk-through (lines 103-116);
  - Consequences, "The code slice" and the `start_instance.py` docstring item (lines 132-136, 146).
- `hilclaw/start_instance.py`, whole (130 lines): `start`, `GivenRunIdError`, `RunIdInUseError` (`.run_id`), and the docstring sentence on lines 39-41 that this task fixes.
- `hilclaw/instance_start.py` lines 86-133 (`REPORT_ORDER`, `OutOfScopeError`, `MissingMembersError` and its members) and `hilclaw/instance.py` lines 637-652 (`InvalidInstanceError` is a `ValueError`; `UnsupportedVersionError`).
- `hilclaw/turn_start.py`, whole (336 lines). It is the pattern to follow: module docstring with the outcome/status table, `_error`, `_described`, `_standard`, `_say`, and `main(argv=None, *, source=..., stdout=None, stderr=None)`, which takes its arguments, data-root source and streams from the caller. `hilclaw.tools.encode` (`hilclaw/tools.py` lines 336-343) writes the line.
- `hilclaw/data_root_source.py`, whole (74 lines): `configured`, and `obtain` with its `ToolFailure` of kind `no_data_root`.
- `tests/test_start_instance.py` lines 1-120: the `document(...)` fixture builder for a valid first-case document (copy what you need; do not import from another test module unless the repository already does so).
- `tests/test_turn_start.py` lines 318-330 and 420-480: temporary data roots, injecting `source`, and binary `stdout`/`stderr` streams in tests.

## Acceptance Criteria

1. **Module `hilclaw/new_run.py`** (Python; give the language reason in one line of the commit body and of Result). It implements ADR-0155 decisions 2 to 6:
   - **Command line.** `python -m hilclaw.new_run <file>`: exactly one argument, the path of a file holding the JSON document. No option exists and nothing is read from standard input. `if __name__ == "__main__": raise SystemExit(main())`.
   - **`main(argv=None, *, source=data_root_source.configured, stdout=None, stderr=None)`**, after `hilclaw.turn_start.main`. `argv` defaults to `sys.argv[1:]`, and the streams are binary and default to the standard ones. No `Exception` leaves the call, and `KeyboardInterrupt` and `SystemExit` are not caught. Adding a keyword that lets tests replace the start function is allowed but not required (monkeypatching `hilclaw.start_instance.start` is the alternative).
   - **Input** (decision 3):
     - The file is read as bytes and decoded as UTF-8, then parsed as one JSON text.
     - Only an object (`dict`) is passed to `hilclaw.start_instance.start`, unchanged: no member is added, defaulted or removed, and nobody is asked.
     - Kinds: not exactly one argument is **bad usage**, and nothing is read. A file that cannot be opened or read is **unreadable input**. Bytes that are not UTF-8, not one JSON text, or JSON whose value is not an object are **bad input**.
     - Choose the decoding rules for a byte order mark, duplicate member names and the `NaN`/`Infinity` tokens, and state them in the module docstring. Whatever the choice, the `ValueError` of `json.dumps` raised inside `start` stays its own kind.
   - **Data root** (decision 4): `data_root_source.obtain(source)`, asked once per start. Its `ToolFailure` is **no data root**, and `start` is not called. Nothing is written before `start`.
   - **Standard output check** (decision 5): the entry checks that it has a standard output before it calls `start`. If it has none, the outcome is **fault**, said on standard error, and nothing is started.
   - **Report** (decision 5):
     - Standard output gets exactly one line: a compact ASCII JSON object (`tools.encode`) with an `outcome` member.
     - Status 0 only for **started**. No status is 1 or 2. Each of the kinds of the decision 5 table is told apart: started, given run id, missing members, invalid, out of scope, run id in use, file system, unwritable value, bad usage, unreadable input, bad input, no data root, fault.
     - Fixed by the ADR: the run id is a member on **started** and on **run id in use**. On **missing members**, the missing members are a list in the order `MissingMembersError` gives them (the `REPORT_ORDER`).
     - `InvalidInstanceError` is told apart from the plain `ValueError` of `json.dumps` by class. `RunIdInUseError` is told apart from `OSError`.
     - Your choices, all stated in a module-docstring table as `hilclaw.turn_start` does: the words of `outcome`, the other member names, the status numbers, and whether kinds share a status.
     - No traceback reaches the starter. Free texts that may name a path go to standard error or to a text member, never into a status.
   - **Line write fails after a start** (decision 5): standard error gets one line that names the run id, and the status is not 0. If writing the line fails before any start, standard error says so and the status is not 0.
   - **Does not** (decision 6): no turn, turn loop, self-check or `claude`; no `STATE.json`, no `events.ndjson` line, no commit, no lock; no look at a run directory before `start`; no registry entry or MCP name. It is not added to `hilclaw/tools.py` or to any registry. The module docstring says the starter goes on with `python -m hilclaw.turn_start <run_id>`.
   - **Within the D4 cap**: about 200 LOC of non-test change in 2 non-test files.

2. **Docstring fix of `hilclaw/start_instance.py`** (ADR-0155 Consequences, line 146). Replace "it binds no caller (OD-23, UC-1)" with a short statement that its caller for a person's or a script's start is `hilclaw.new_run` (ADR-0155), and that other callers stay open. Keep "is no FR-10 tool, is not registered in :mod:`hilclaw.tools` and has no command-line or MCP entry (ADR-0115 decision 3)" in a form that stays true: the function has no entry of its own. No code change in this file.

3. **Tests `tests/test_new_run.py`** (CLAUDE.md "테스트 규칙", DRIVER §5 D12). Use fixtures written by the tests and `tmp_path` data roots only. No `claude`, no stub `claude`, no container, no board, no network.
   - **Happy path**: a valid first-case document file under a temporary data root gives status 0 and one **started** line. The run id on that line names the file `runs/<run_id>/instance.json`, which exists. Its parsed content equals what `start` writes for the same document; for example, compare against `hilclaw.instance.load` or the parsed JSON, not against a guessed byte layout. Nothing else is created under the data root.
   - **Each kind** of criterion 1 gets at least one test, with the exact `outcome` word, status, members and the absence of any run written:
     - given run id; missing members (two members missing, in `REPORT_ORDER` order, as in the ADR Walk-through: `draws`, `tolerance`); invalid; out of scope (an accelerator outside the first case);
     - run id in use (force the taken name, for example by fixing `hilclaw.run_id.new` and pre-creating the name); file system (an `OSError` of the write); unwritable value (a NaN reaching `start`, through the file if the decoding rules let it through, otherwise through a replaced `start`);
     - bad usage (zero and two arguments); unreadable input (missing file, and a directory as the path); bad input (non-UTF-8 bytes, invalid JSON, a JSON array, a JSON string);
     - no data root (a source that raises, and a source naming a missing directory);
     - fault (an unexpected `Exception` from `start`, and a missing standard output before the start, with `start` not called).
   - **Branch and negative cases**:
     - the document passed to `start` equals the parsed file and is not modified (for example, a recording replacement of `start`);
     - the source is asked exactly once;
     - your chosen decoding rules for the BOM, duplicate names and NaN tokens each have a test;
     - standard output whose write fails or is short after a started run: standard error names the run id, and the status is not 0;
     - no status is 1 or 2 across all kinds;
     - standard error carries no traceback;
     - `main()` with `argv=None` reads `sys.argv[1:]` (monkeypatch);
     - `KeyboardInterrupt` from `start` propagates.
   - **Coverage**: `hilclaw/` line coverage >= 80% and function coverage >= 80% stay met. Every public function of `hilclaw/new_run.py` is tested, and `hilclaw/new_run.py` itself is fully or nearly fully covered. `tests/test_start_instance.py` still passes unchanged.
   - No test of test code, CI or hooks is added (D12 ⑤).

4. **Local gates**: `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass.

5. **Procedure** (dev-item-address, code mode):
   - Work on branch `claude/T-0427-new-run-command-line-entry`.
   - Open a Draft PR whose title contains `T-0427` and whose body ends with `Task: T-0427`.
   - Run the isolated reviewer cycle (dev-code-review) to Approve, at most 7 rounds.
   - Wait for CI green, then squash-merge with `gh pr merge --squash --body` carrying the PR body, and delete the branch.
   - Result records the PR, the merge commit, the review rounds, the language reason and the choices made for the items decision 5 leaves open.

6. **Stop conditions.** Return BLOCKED with the reason, and do not work around it, if any of these holds:
   - implementing a kind needs a change to `hilclaw.start_instance.start` or `hilclaw.instance_start`, beyond the docstring;
   - it needs a new data-plane member, file, kind or version;
   - it needs a new external dependency.

## Out of Scope

- Any edit to `ARCHITECTURE/`, including the "less exact, not edited" ADR sentences listed in ADR-0155 Consequences (they are a D18 hold line). The one exception is the `hilclaw/start_instance.py` docstring of criterion 2.
- A UI, a menu, a range check of `candidates_per_round` (ADR-0155 decision 7), the K2 caps, the autonomy mode, gates, and injected hypotheses beyond what the document holds.
- Joining the start with `hilclaw.turn_start`, and any change to `hilclaw/turn_start.py`, `hilclaw/turn_loop.py` or the registry.
- The P2-10 nightly routine and how it starts its run.
- README or user documentation of the command. Leave it for P2-5's run-procedure work, unless a README section already lists the package's command-line entries; then add one line there and name the fourth file in Result.

## Follow-ups

- (planner) After this lands, the P2-13 joining task of ADR-0153 slice 1 (T-0423 Follow-ups) is the candidate, unless an HQ answer reopens a round-loop item first.

## Result
