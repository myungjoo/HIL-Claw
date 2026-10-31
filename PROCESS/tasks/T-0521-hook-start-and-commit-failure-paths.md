---
id: T-0521
title: Harden the hook start, turn-session setup and commit failure paths (HQ-0080 group C)
phase: P2
status: DONE
commitMode: code
coversReq: [HQ-0080, OD-18, OD-8, FR-11, NFR-4]
dependsOn: []
touchesFiles:
  - hilclaw/caller_check.py
  - hilclaw/budget_check.py
  - hilclaw/turn_loop.py
  - hilclaw/run_commit.py
  - tests/test_caller_check.py
  - tests/test_budget_check.py
  - tests/test_turn_loop.py
  - tests/test_run_commit.py
  - tests/harness/test_bf16_timing.py
estimatedSize: {loc: 120, files: 4}   # test code is outside the cap
hq: []
---
## Why

The owner approved group C of the PLAN hold section in HQ-0080 ("failure paths and input hardening", with the `caller_check.START` line first). No P2-15 work can be planned now: it waits on HQ-0084, and DRIVER §6 D26 says that wait blocks no other task. The approved lines are not judged again here.

The planner read each line against main at 0bfe600c:

| Hold line | Finding on main | This task |
|---|---|---|
| T-0406, `START` failures before `main` | `caller_check.START` and `budget_check.START` end with exit 1 on a missing package argument or a failed import. Exit 1 is a non-blocking error, so only `onFailure: "block"` (unconfirmed item (lix) of ADR-0146) stops the call. | Criterion 1 |
| T-0406, `NaN`/`Infinity` | `budget_check` and `stop_check` pass `parse_constant`; `caller_check` does not. | Criterion 2 |
| T-0407, placeholders | `turn_loop._settings_text` refuses a placeholder in the data root only. | Criterion 3 |
| T-0404, `settings.local.json` | `turn_loop` refuses a definition's `.claude/settings.json` but not `.claude/settings.local.json`. | Criterion 4 |
| T-0349, failed fallback reset | The unchecked `_git(... "reset" ...)` at the end of the commit block in `run_commit.commit` ignores a failure. If `_git` raises `GitNotRunError` there, the tool answers `no_repository` though the commit stands. | Criterion 5 |
| T-0514, CRLF test | The stand-in writes stderr in text mode, so native Windows gives `\r\n`. | Criterion 6 |
| T-0379, duplicate agent `name` | Already refused: `turn_permissions._agents` raises `_NAME_TWICE`, and `options` calls `_agents`. | Criterion 7, no code |
| T-0243, ADR-0078 slice 4 | Already handled: `clang_build` raises `ArtefactNotPlacedError` and `TemporaryNotRemovedError` with `result`, which holds the log. | Criterion 7, no code |

These fit the decided rules (ADR-0146 decision 5: a fault of the program refuses; ADR-0127: the commit stands). They need no new ADR.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5.
- `hilclaw/caller_check.py`, whole file; `hilclaw/budget_check.py`, lines 60-153.
- `hilclaw/stop_check.py`, lines 1-110: read for contrast, not changed.
- `hilclaw/turn_loop.py`: docstring lines 42-60 and 137-180, code lines 268-280, 345-400 and 449-455.
- `hilclaw/run_commit.py`: lines 216-235 and 285-332.
- `ARCHITECTURE/decisions/ADR-0146-od18-first-case-caller-check-hook.md`: H3 (line 27), decision 4 (line 65), decision 5 (line 73).
- `tests/test_run_commit.py`: lines 1178-1215. `tests/harness/test_bf16_timing.py`: lines 25-40 and `test_standard_error_is_captured_and_not_parsed`.

## Acceptance Criteria

1. **Start texts refuse.** `caller_check.START` and `budget_check.START` end with exit status 2, never 1, when anything before `main` raises: no package argument, or a package directory that does not hold `hilclaw`.
   - Each stays one line with no `"` and no line feed, because it is an exec-form argument (ADR-0146 item (lix)).
   - Each may write one fixed line to standard error and nothing to standard output.
   - A form that meets this: `import os, sys; sys.excepthook = lambda *_: (sys.stderr.write('caller check: the hook could not start\n'), sys.stderr.flush(), os._exit(2)); sys.path.insert(0, sys.argv.pop(1)); from hilclaw.caller_check import main; raise SystemExit(main())`. A `SystemExit` does not reach `excepthook`, so `main`'s status is kept.
   - `stop_check.START` is not changed: exit 1 there lets the stop through, which is what ADR-0148 decision 5 asks of a fault.
   - State the form under "Chosen here" in both module docstrings.
2. **Constants.** `caller_check` treats an input holding `NaN`, `Infinity` or `-Infinity` as not JSON and refuses it (exit 2), as `budget_check` does. `_line` must not name a tool from such an input.
3. **Placeholders.** `_settings_text` also refuses `PACKAGE_DIRECTORY` and `os.path.abspath(sys.executable)` when either holds a value of `_PLACEHOLDERS`. It raises `ValueError` with one new fixed text, before the first turn. The existing `_PLACEHOLDER_HELD` text and its data-root behaviour stay. Update the module docstring.
4. **Local settings.** A `.claude/settings.local.json` found after `put_definition` is refused like `.claude/settings.json`: a `ValueError` with a fixed text, before the settings file is written and before the process starts, at every turn. Update the module docstring.
5. **Failed fallback.** When the replacement of the index has failed and the fallback `git reset` then fails, by a non-zero exit or by `GitNotRunError`:
   - `commit` still returns `True`, since the commit stands;
   - it writes one fixed line to standard error that says the commit was made and the index was not updated.
   - The `run.commit` answer is unchanged (ADR-0127 decision 3, a contract this task does not change).
   - Rewrite the docstring's "nothing reports it". Print no `git` text. Do not touch any other path of `commit`.
6. **Windows test.** The stand-in in `tests/harness/test_bf16_timing.py` writes stderr as bytes, for example `sys.stderr.buffer.write(plan["stderr"].encode())`, so the test passes on native Windows. The assertion stays.
7. **Lines already done.** Confirm the two "already" rows of the table by reading the code and the existing tests. Add a test only where a public function's refusal has none. If one of them is in fact open, list it in Follow-ups rather than widening this task. Say the result in `## Result`.
8. **Tests** (CLAUDE.md test rules):
   - Happy: an unchanged pass, and an unchanged normal commit (the subprocess tests of the start texts keep passing).
   - Error and negative: criterion 1 by a real subprocess in both failure forms, for both modules, asserting status 2 and empty standard output; each constant in criterion 2; each of the two paths in criterion 3 through `monkeypatch`; a `put_definition` that writes `settings.local.json`, with no process started; both failure forms in criterion 5.
   - `test_a_failed_replacement_and_reset_leave_the_commit_and_the_old_index` keeps its assertions and gains one on the line.
   - No other existing assertion changes, except list-pinning edits DRIVER §5 allows (D21). None is foreseen.
9. `ARCHITECTURE/` is not edited. In `## Result`, list the sentences this makes less exact (for example ADR-0146 decision 5, "an import that fails before the guard"), without editing them, and state whether an `ARCHITECTURE/` coverage recheck was needed (expected: no).

## Out of Scope

- A start failure of the interpreter itself and timeouts: `onFailure` and item (lix) stay as they are.
- Changing `run.commit`'s answer or the Round-Manager prompt.
- Group A docstrings (T-0522), groups B, D, E, F, and every hold line outside HQ-0080.
- A real `claude`, a Docker daemon or a D25 test run: fixtures and subprocesses of the hook programs suffice.

## Follow-ups

## Result
- PR #341 squash-merged as 77db895c (code mode, Task trailer kept, branch deleted). 1 review round, Approve; the one Nit (a docstring reflow in `turn_loop.py`) was fixed after the Approve with no re-review (D20).
- Language: Python, because all changed code is existing Python layer-2 modules.
- CI: all six jobs of run 41154416421 green on the final head 3eef8c4e. Local (Windows, Python 3.14) at 745631c7: 37072 passed, 2063 skipped, ruff clean; the only later change is the reflow. Coverage: `hilclaw/` 99%; `caller_check`, `budget_check`, `turn_loop` 100%, `run_commit` 98%. `tests/test_turn_loop.py` needed `--basetemp` outside the default temp directory on this machine, and 3 of its symlink tests skip there.
- Criteria 1-6 implemented. Criterion 7: T-0379 and ADR-0078 slice 4 (T-0243) were already in the code; confirmed, no test added. Criterion 8: the only changed existing test is the one the task requires. New public names: `turn_loop.LOCAL_SETTINGS_FILE`, `run_commit.INDEX_NOT_UPDATED`.
- ARCHITECTURE sentences now less exact, not edited: ADR-0146 decision 5 (an import failure now exits 2 by itself) and decision 4 (a `settings.local.json` is now refused too).
- Known limit, inferred and not run: an interpreter with no usable `sys.stderr` probably exits 1 from the `excepthook`; `onFailure: "block"` remains the backstop (ADR-0146 (lix)).
- Follow-ups: none. New runtime acceptance items: none. New HQ: none.
