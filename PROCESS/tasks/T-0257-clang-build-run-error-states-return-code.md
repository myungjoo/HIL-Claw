---
id: T-0257
title: Make `CompilerRunError` state the return code `clang_build.build` holds when reading the clock fails after the compiler ended by itself, so that source is told apart from the closing source
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0255, T-0256]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 30, files: 1}
hq: []
---
## Why

ADR-0084 (landed as `26e8ac0`) leaves one source of `CompilerRunError` open: a failed clock read after the compiler ended by itself (exit 0 or a non-zero status). It gives two reasons, both about what `build` states (ADR-0084 decision 3):

- **It is not told apart.** The class and its members say the same thing for this source as for an error from closing the process after a read that ended: `timed_out` false and `log` all the output.
- **The row would depend on a status that is not stated.** When the clock is read, the return code returned by `_communicate` is already bound in `build` (ADR-0084 C2). But `CompilerRunError` does not carry it: its members are `timed_out`, `log` and `removal_error`.

The first thing ADR-0084 decision 3 names under "What would let it be placed" is: "A code change of `clang_build.build` that states the return code it already holds (C2) for a failed clock read, and tells that source from the closing source". Its Consequences say: "A code task may make `build` state the return code for a failed clock read and tell it from the closing source (decision 3)". They also say that names and modules are the code task's and that "this record binds no code". T-0256's Result lists this as its suggested next follow-up.

**The change, stated.** Add one keyword-only member to `CompilerRunError`, named `returncode`, with default `None`:

- When `build` raises `CompilerRunError` from an `OSError` of the clock read after `_communicate` returned, `returncode` is the return code `_communicate` returned. That is the value `BuildResult.returncode` would have held for the same build.
  - After a normal end, it is an `int`: 0, a non-zero status, or a negative signal number on POSIX.
  - After a kill for the time limit, `_communicate` returns `None`, so the member stays `None`. That source is already told apart by `timed_out` true.
- For every other source of `CompilerRunError`, `returncode` is `None`. These sources are the first read, the kill after it, the kill for the time limit, reading or waiting after that kill, and closing the process. In each of them `_communicate` raised, so `build` holds no return code.

So for an error whose `timed_out` is false, `returncode is not None` holds exactly when the error came from the clock read after a normal end. That tells it apart from the closing source. Name the member `returncode` after `BuildResult.returncode`, so a caller reads the same value under the same name. Its documented meaning:

- "the return code of the compiler process when the error came from reading the clock after the process had ended by itself";
- otherwise `None`;
- `None` does not mean the process did not end.

This is an engineering choice inside `build`, which ADR-0084 leaves to the code task. It adds:

- no new module-level public name;
- no data-plane member or file;
- no value of `condition` or `error.kind`.

It places no row of `correctness.check`. What the member means for that row (S7 for a non-zero status, and status 0 with no artefact tested) is a later doc task (Follow-ups). It is not an owner-only item under DRIVER §9.

Nothing else changes:
- the other members and their values for every source;
- the five classes' other sources;
- the results and `duration_s` of a normal, failed or timed-out build;
- `_communicate`;
- the note for an exception that is no `OSError` (T-0253);
- a plain `OSError` from `started = time.monotonic()` before the `try`.

**Existing tests checked at planning time (`31a46d5`).** No existing test pins the absence of this member or the exact set of `CompilerRunError` attributes:
- `test_run_error_class` (line 1131) checks that `CompilerRunError(OSError("plain"), None, True)` raises `TypeError`. That still holds with a keyword-only member.
- `test_run_error_survives_pickling` (line 1154) compares the members it names. `_UnendedBuildError.__reduce__` passes `self.__dict__` as the state, so the new member survives pickling with no change to `__reduce__`.
- No module outside `hilclaw/clang_build.py` and `tests/test_clang_build.py` names `CompilerRunError` (`grep -rn CompilerRunError hilclaw tests`).

So every existing test should pass unchanged. Edits to existing tests are allowed only as in criterion 4.

**Why this item now.** STATE has no lock, current task or next task. Every TODO, INTERRUPTED or BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). There was no open PR on 2026-10-17 at `31a46d5`. PLAN P1-1 continues through OD-18 work. This task depends on none of those HQs, and none of the blocked tasks touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`. T-0256 names two other follow-ups, and this task takes neither:
- telling the source path tests from the output path tests (ADR-0083 decision 3), a separate code task;
- the row of the `timed_out`-false branch as a whole, which may need a new `error.kind` and so an HQ.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0257-<slug>`, the PR title with `T-0257`, the trailer `Task: T-0257` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0084-od18-correctness-check-clock-error-after-end.md`. Do not edit it. Read:
  - Context C1 to C3 (lines 19-24);
  - decision 3 (lines 42-53), especially "What would let it be placed";
  - Consequences "Code" (line 97).
- `hilclaw/clang_build.py` at `26e8ac0` or later:
  - `BuildResult` (lines 39-56), for the meaning of `returncode`;
  - `_UnendedBuildError` and `CompilerRunError` (lines 77-129), its docstring and `__init__`;
  - `build` (from line 186), especially:
    - the docstring sentence on `CompilerRunError` (from line 222);
    - the lines from `start_error = run_error = …` (line 262) to the `CompilerRunError` raise (line 312);
  - `_Held` and `_communicate` (lines 365-389).
- `tests/test_clang_build.py`:
  - the stub bodies (lines 41-46) and `LOGGED_WRITE` (line 329), and the fixtures `stub` (line 80), `names` (line 109) and `failing_unlink` (line 356);
  - `timed_out_run` (line 726) and `test_failed_close_after_a_read_that_ended` (line 853), for the closing source;
  - `failing_clock`, `assert_clock_run_error` and the clock tests (lines 945-1065);
  - `test_run_error_class` and `test_run_error_survives_pickling` (lines 1131-1184).
- `PROCESS/tasks/T-0255-clang-build-clock-error-after-start.md`: "The change, stated" and Result. `PROCESS/tasks/T-0256-adr-od18-clock-error-after-end.md`: Result.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`CompilerRunError` and `build`.** Make the change as "The change, stated" says:
   - `CompilerRunError.__init__` gains a keyword-only `returncode=None`, stored as the attribute `returncode`. Positional use still raises `TypeError`.
   - When the clock read after `_communicate` returned raises an `OSError`, `build` passes the return code `_communicate` returned.
   - Every other `CompilerRunError` that `build` raises has `returncode` `None`. Do not read the return code from `process` or from the log on those paths.
   - Pickling keeps `returncode`, through the existing `__reduce__` if it does so (it should). Change `__reduce__` only if a test shows the need.
   - Every other path and member keeps its current behaviour. Add no new module-level public name and no comment that restates the code.
3. **Docstrings.**
   - In `CompilerRunError`'s docstring, add the meaning of `returncode`:
     - its value after a failed clock read following a normal end;
     - `None` for every other source, including after a kill for the time limit;
     - that `None` does not mean the process did not end.
   - Do not change what the docstring says of `timed_out`, `log` and `removal_error`.
   - Extend the sentence of `build`'s docstring on `CompilerRunError` to name the member.
   - Touch the module docstring only if a sentence in it becomes wrong.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures.
   - **Edits to existing tests are allowed only as additions of assertions.** No existing assertion may be removed or changed, and no existing test may be renamed or deleted. Assertions may be added only to:
     - `test_run_error_class`;
     - `test_run_error_survives_pickling`;
     - `test_error_after_the_start_is_raised_as_run_error`;
     - `test_failed_close_after_a_read_that_ended`;
     - the five `test_failed_clock_*` tests and `test_non_os_error_from_the_clock_after_the_end_is_passed_on`.

     Any other existing test must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
   - **Happy path.** With `LOGGED_WRITE` (exit 0) and a failing clock read after the end (`failing_clock()`), the raised `CompilerRunError` has `returncode == 0`.
   - **Branch.**
     - With `FAIL` (exit 1), `returncode == 1`.
     - With a stub that exits with another status, for example 3, `returncode` equals that status. This shows the value is the process's return code, not a constant.
   - **Branch.** With `SLEEP` and a short `timeout_s`, the failed clock read gives `timed_out` true and `returncode` `None`.
   - **Branch, the closing source.** In `test_failed_close_after_a_read_that_ended`, or in a new test built on `timed_out_run`, the `CompilerRunError` from closing the process after a read that ended has `returncode` `None`. Its `timed_out` stays false and its `log` stays all the output. This is the test that shows the two sources are now told apart.
   - **Branch, other sources.** `returncode` is `None` for:
     - the first read failing (`failing_communicate`);
     - a failed kill after the time limit.
   - **Branch.** With `failing_unlink` as well, a failed clock read after exit 0 keeps `returncode == 0` and has the removal's error as its `removal_error`.
   - **Class and pickling.**
     - `CompilerRunError(OSError("plain")).returncode is None`.
     - `CompilerRunError(OSError("plain"), returncode=2).returncode == 2`.
     - A pickled and loaded `CompilerRunError` keeps `returncode`: `0`, a non-zero value and `None`.
   - **Negative.**
     - `CompilerRunError(OSError("plain"), None, False, None, 0)` raises `TypeError`.
     - A failing clock read before the start still raises the plain `OSError`, as `test_failed_clock_before_the_start_stays_plain` asserts.
     - A successful build still returns a `BuildResult`. No attribute `returncode` appears on the other four error classes.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only the stub compilers the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0257-<slug>` with a Draft PR whose title contains `T-0257`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0257`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason. State from the code which sources of `CompilerRunError` now carry a non-`None` `returncode`.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/`: ADR-0078 to ADR-0084, Requirements, OpenDecisionProposals and StandardScenarios.
- Placing any row of `correctness.check`. This covers S7 for a non-zero status, status 0 with no artefact tested, handing the log over, and the `timed_out`-false branch as a whole.
- A `returncode` (or any other new member) on `CompilerNotStartedError` or on the three `_EndedBuildError` classes.
- Telling the source path tests from the output path tests (ADR-0083 decision 3).
- Any change to `_communicate`'s kill, wait or read.
- Callers of `build`: `hilclaw/harness/verification_build.py`, `timing_build.py` and `hilclaw/standin_profile.py`. Also out: `compiler_version` and the `cpu_standin` operation of `correctness.check` (HQ-0026).

## Follow-ups

- (doc) A record under OD-18 sub-question 18 part (ma) on what this member makes true. ADR-0084 decision 3's "It is not told apart" and "The row would depend on a status that is not stated" no longer hold as written for a failed clock read after a normal end. The record weighs:
  - S7 with its log for a non-zero `returncode`, by O1;
  - what status 0 with no artefact tested is;
  - which sentences of ADR-0082 and ADR-0084 become less exact.

  Status 0 may need a new `error.kind`, and so an HQ.
- (code) Make `build` tell the source path tests from the output path tests, and both from the other lines before the start (ADR-0083 decision 3, ADR-0084 decision 4).

## Result

- PR #162 (`claude/T-0257-run-error-returncode`), squash-merged into `main`; reviewer cycle 2 rounds, Approve (round 1 Approve with nits: a duplicate test dropped and a docstring rewrap, then round 2 Approve).
- Language: Python, the language of `hilclaw/clang_build.py`, which the change extends.
- `CompilerRunError.__init__` gains keyword-only `returncode=None`, stored as `returncode`; `__reduce__` is unchanged and pickling keeps the member through `self.__dict__`.
- From the code: `build` binds `returncode = None` before `_communicate` and passes it to every `CompilerRunError` it raises. The only source with a non-`None` `returncode` is an `OSError` from `duration_s = time.monotonic() - started` after `_communicate` returned from a normal end (0, a non-zero status, or a negative signal number on POSIX). After a kill for the time limit `_communicate` returns `None`, so that clock source keeps `None` (told apart by `timed_out` true). The first read, the kill after it, the kill for the time limit, the read or wait after that kill and closing the process all raise inside `_communicate`, so `returncode` stays `None`.
- Tests: assertions added only to the permitted existing tests; new tests `test_failed_clock_states_the_exit_status` (3, 77), `test_failed_kill_after_the_time_limit_states_no_return_code`, `test_other_errors_carry_no_return_code`.
- Local: full `pytest` 22182 passed / 355 skipped, `ruff check` and `ruff format --check` clean; `hilclaw/` line coverage 99%, functions 698/702.
- Follow-ups unchanged from the task file (the OD-18 (ma) doc record on what the member makes true; telling the source path tests from the output path tests).
