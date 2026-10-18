---
id: T-0315
title: Add a pure function that reads an attempt's standing at one execution point from the step lines of correctness.check (code slice of ADR-0110)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-9, FR-1, FR-10, OD-18]
dependsOn: [T-0314]
touchesFiles: [hilclaw/check_standing.py, tests/test_check_standing.py]
estimatedSize: {loc: 140, files: 2}
hq: []
---
## Why

T-0314 landed ADR-0110 as 4bc7f78. It answers the first part of OD-18 sub-question ⑭: for one attempt at one execution point of `correctness.check`, every ended check whose end line holds a result counts. The standing at that point is one of three: **not verified**, **verified** or **undetermined**. The record sorts a `failure` into class (i) and class (ii) and treats an open identity as blocking verification. Its Consequences name this slice: "a pure function over the complete lines of a run's log, or over the step lines of one attempt, that returns the standing of the attempt at a point. It needs nothing that does not exist yet ... **No module or function is named as binding.**"

This task writes that function as a new module, in the way T-0309 landed the code slice of ADR-0106. Nothing calls the function yet; its consumer is PLAN P2-1/P2-3. The task registers no tool and decides nothing beyond ADR-0110. It is a step of PLAN P1-1. It needs no owner decision, no runtime and no HQ. It does not touch the files of open PR #179 (`hilclaw/clang_build.py`, `tests/test_clang_build.py`).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (lines 63-77: executor procedure, resume rule, time cap) and §5 (lines 86-114: task format, naming convention, size cap, the D12 test rules).
- `CLAUDE.md`: comment minimisation, the layer-2 language policy, the test rules and the code-mode branch/merge procedure.
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md`: decisions 1, 2, 3 and 5 (lines 25-79), the Walk-through (lines 85-104), Limits (lines 105-118) and Consequences (lines 133-139). Decisions 2 and 3, their two tables and the Walk-through table are the specification.
- `ARCHITECTURE/decisions/ADR-0011-od17-journal-and-spend.md`: decisions 3, 4 and 6 (identity, the three states, the fold, and "counted and reported" end lines).
- `hilclaw/journal.py` (whole): `STEP_STARTED`, `STEP_ENDED`, `Identity`, `identity_of`, `step_identity`, and how `fold` checks every line and prefixes `line <number>:` to an error. Note that `step_state` takes the **first** end line only. ADR-0110 decision 2 counts **every** end line, so do not build the new function on `step_state`.
- `hilclaw/events.py` lines 1-140 and 181-230 (`validate`, `read`, and the line form that `read` returns).
- `hilclaw/check_identity.py` lines 77-95 (`STEP_SIM`, `STEP_BOARD`, `STEPS`, `NUMBERS`).
- `hilclaw/check_failure.py` lines 60-125: the seven backend kind constants of class (i), and `KIND_SETTINGS_REFUSED`, which is class (ii).
- `hilclaw/check_operation.py` line 79 (`KIND_OPERATION_ANSWER_INVALID`).
- `hilclaw/check_result.py` lines 1-65 (`PASS`, `FAIL`, `BROKEN`, `CONDITIONS`).
- `tests/test_journal.py` lines 1-90 (line-building helpers to copy or adapt).

## Acceptance Criteria

1. **New module `hilclaw/check_standing.py`** (Python, the language of the rest of `hilclaw/`). Its module docstring cites ADR-0110. It names the module's own choices (below) apart from the record's rules. It says what the module does not do: it decides no second part of ⑭, appends nothing, reads no file, names no consumer, merges no two points, judges no result again, and does not check that the run is a first-case or mock run (the caller's scope, decision 1). The function and constant names below are this task's choice, as the record names none as binding. Public names:
   - `Standing`: an enum with exactly `NOT_VERIFIED`, `VERIFIED` and `UNDETERMINED`. These are words of ADR-0110 decision 3, not values of any file. The docstring says so.
   - `UNSTARTED_KINDS`: a `frozenset` of the seven class (i) kinds of ADR-0110 decision 2 (`no_kernel_source`, `kernel_source_unreadable`, `build_directory_unusable`, `build_input_missing`, `compiler_unavailable`, `build_output_missing`, `executable_unstartable`). Build it from the constants of `hilclaw.check_failure`, not from literals. Every other `failure` kind is class (ii). That covers `build_log_unwritable`, `operation_answer_invalid`, `operation_failure_invalid`, `settings_refused` and any unknown kind, per the record's "any kind a later record adds unless that record places its situations in (i)".
   - `standing(lines, step, round, candidate, attempt)`: returns the `Standing` of the attempt `(round, candidate, attempt)` at the point `step` after `lines`.
     - `lines` is an iterable of parsed events in the form `hilclaw.events.read(...).events` returns, read once.
     - `step` must be one of `hilclaw.check_identity.STEPS`. Anything else is refused with a `ValueError` subclass (for example `journal.JournalError`) whose message names `step`.
     - The three numbers are checked as `journal.step_identity` checks them, with all three required.
     - The function does not modify any argument.
2. **Line handling** (ADR-0110 decision 2):
   - Every line is checked: `events.validate` for any kind, and the step-line check of `journal.identity_of` for `step_started`/`step_ended`. The first line that fails raises that error with `line <number>:` (from 1) in front, as `journal.fold` does.
   - Lines of other kinds, and step lines of another step or of other envelope numbers (an absent number included), are ignored after the check.
   - The result depends on the **set** of matching lines, not on their order. The test permutes the lines of each Walk-through row and gets the same standing.
   - An identity is **open** when the lines hold a start line of it and no end line of it (ADR-0110 Walk-through: "open" means "a start line without an end line"; the order of the lines does not matter).
   - An end line without a start line counts like any other. Two end lines of one identity both count.
3. **Combining** (ADR-0110 decision 3):
   - **NOT_VERIFIED** if any counting end line has a result whose `outcome` is `fail` or `broken` (any `condition`). This holds whatever else is present: an open identity, a class (ii) failure or a pass.
   - Else **VERIFIED** if at least one result is `pass`, no identity of the point is open and no end line holds a class (ii) `failure`.
   - Else **UNDETERMINED**: no matching line, only failures, or passes beside an open identity or a class (ii) failure.
   - A class (i) `failure` counts neither way.
   - Module's own choice, stated in the docstring: a result whose `outcome` member is missing, not a `str`, or not one of `PASS`/`FAIL`/`BROKEN` is refused with a `ValueError` subclass naming the line, and no standing is returned. `journal` does not look into results, and ADR-0110 does not say what such a line means. No other result member is read.
4. **New `tests/test_check_standing.py`** (D12: happy, error, branch and negative cases; every public name):
   - **Walk-through rows.** One test per row of the ADR-0110 Walk-through table, with the standing as the table gives it, the two-point row and the repaired-attempt row included. The two-point row asserts that board lines never change the sim standing and the other way round.
   - **Every class (ii) kind.** Each class (ii) kind named in decision 2, plus an unknown kind, beside a pass gives `UNDETERMINED`. Beside a fail it gives `NOT_VERIFIED`.
   - **Every class (i) kind.** Each of the seven class (i) kinds beside a pass gives `VERIFIED`. Alone it gives `UNDETERMINED`.
   - **Every condition.** Each of the six `CONDITIONS` gives `NOT_VERIFIED`, also beside a later pass.
   - **Unusual end lines.** An end line without a start line counts. A doubled end line counts (two end lines of one identity, one `pass` and one `fail`, give `NOT_VERIFIED`).
   - **Lines that do not match.** Lines of other kinds, other steps and other numbers are ignored. A line whose numbers lack `attempt` does not match.
   - **Order and arguments.** Permutation invariance as in criterion 2. A generator is accepted as `lines`. The arguments are not modified.
   - **Negative cases.** A `step` not in `STEPS` (for example `"sim_run"`, `None`, a `str` subclass); invalid numbers (missing, `bool`, negative, above `keys.MAX_INTEGER`); a malformed line at position *n*, where the message starts with `line n:`; a result with no `outcome`, an unknown `outcome` or a non-`str` `outcome`.
   - **Module surface.** `UNSTARTED_KINDS` equals the seven constants of `check_failure`. `Standing` has exactly three members. The module has exactly the public names above.
5. `pytest`, `ruff check` and `ruff format --check` pass. Line and function coverage of `hilclaw/` stay ≥ 80%. No new dependency. No data-plane schema change: no member, file, `step` value, event kind or tool-failure kind is added. No file outside the touchesFiles changes, in particular no `ARCHITECTURE/` file, no other `hilclaw/` module and no CI file.
6. **Code mode** (CLAUDE.md A-13):
   - branch `claude/T-0315-check-standing-from-log`;
   - a Draft PR whose title contains `T-0315` and whose body ends with `Task: T-0315`;
   - the reviewer cycle (dev-code-review, at most 7 rounds), then CI green;
   - squash-merge with `gh pr merge --squash --body`, then delete the branch;
   - the commit body records the language choice in one line;
   - no `git push --force*`.
7. **D16.** Start no `claude` process, compiler, kernel or container. The tests use synthetic event dicts only.

## Out of Scope

- The second part of ⑭ (what keeps a caller from asking for further executions), ⑳ (the run tools), FR-1 ⑶ triage, OD-10/OD-17 recovery and retry, OD-16 ⑤, OD-3 gates, and any consumer (PLAN P2-1/P2-3, OD-23).
- Registering anything, wiring the function into `check_tool.py`, `journaled_tool.py` or any hook, or reading a log from disk inside the module.
- Editing any ADR, including the "less exact" sentences that ADR-0110 Consequences lists, and editing `hilclaw/journal.py` (its `step_state` stays first-end-line).
- T-0314's two round-7 citation nits (ADR-0110 decision 3 citing ADR-0026 decision 4; the ADR-0011 decisions in the Status builds-on list). They are a separate doc task.
- `hilclaw/clang_build.py` and `tests/test_clang_build.py` (open PR #179), and every BLOCKED task.

## Follow-ups

- Doc task: apply T-0314's two round-7 citation nits to ADR-0110 (Status builds-on list; the decision 3 bullet on `end_line_failed`).

## Result
