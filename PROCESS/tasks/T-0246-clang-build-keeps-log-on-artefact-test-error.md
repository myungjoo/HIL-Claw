---
id: T-0246
title: Let `hilclaw.clang_build.build` keep the compiler's log when testing for the temporary file after the compiler ended raises an `OSError`, on every supported Python version, by raising a new `OSError` subclass `ArtefactNotCheckedError` that carries the `BuildResult`
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-6, FR-10, OD-18, "#5 D12"]
dependsOn: [T-0244, T-0245]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 60, files: 1}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

ADR-0078 decision 2 keeps "The log of every build whose compiler process was started and has ended". T-0244 (PR #155, `7003362`) made `clang_build.build` keep that log when moving the artefact or removing the temporary file fails. One post-end error is still passed on without the log. ADR-0079 (T-0245, `994ca3d`) observes this in N2 (line 21): "After the compiler ended, the call tests whether the temporary file exists with `is_file` outside the two classes of N1, so where that test propagates an `OSError`, it comes up with no `result` and no log." Its Consequences (line 84) say: "**The log of a build whose test of the temporary file propagates an `OSError` after the compiler ended is lost** with the error (Python 3.11 to 3.13, N2), against ADR-0078 decision 2, unless `clang_build.build` changes; a code task changes it or registers the case". This task changes it. It is follow-up (1) in T-0245's Result.

The behaviour also depends on the Python version today. On 3.11 to 3.13, `Path.is_file` propagates errors other than "not found" (for example permission errors). On 3.14 it returns `False` instead, so the same situation reads silently as "exit 0 without an artefact". `requires-python` is `>=3.11`, and CI runs 3.11 and 3.14 (`.github/workflows/ci.yml` line 22). C-7 asks the system to behave alike on every machine. After this task, `build` reports the same thing on every supported version.

This task does not say which row (S6, S9, …) or `error.kind` the new error maps to. ADR-0079 decision 5 keeps "one from the test of the temporary file after the compiler ended" open under OD-18 ⑱ (마), and placing it is a later record's job. This task edits no `ARCHITECTURE/` file.

**Why this item now.** STATE has no lock, no current or next task, no TODO or INTERRUPTED task file, and no open PR (checked 2026-10-17 at `a30534a`). PLAN P1 has three open items. P1-1 continues through OD-18 work like this one, and its `profiler.collect` part waits on HQ-0025. P1-8 and P0.5-4 have no follow-up queued here. T-0243 (ADR-0078 slices 1 and 2: `hilclaw/layout.py`, a new `hilclaw/build_log.py`) is BLOCKED on HQ-0026. This task does not depend on it, touches none of its files, and does not work around its question: it adds no layout function, keeper or writer. No other BLOCKED task (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243) touches either file of this task.

**Planner's design (the reviewer is asked to check it against ADR-0078 decision 2, ADR-0079 N2 and Consequences, and against the `build` docstring it amends):**
- A new exception class `ArtefactNotCheckedError` in `hilclaw/clang_build.py`, an `OSError` subclass built on the existing private base `_EndedBuildError`. It is not a subclass of `ArtefactNotPlacedError` or `TemporaryNotRemovedError`, and neither of those is a subclass of it. It is raised when the compiler exited with 0 and testing whether the temporary file exists and is a regular file raised an `OSError` that does not mean "absent". The name is fixed, because the acceptance criteria test it.
- `result` is the `BuildResult` of the ended compiler process, with `ok` `False` (the artefact is not at `output`), `returncode` 0, `timed_out` `False`, and the compiler's `log`, `command`, `output` and `duration_s`. Like `ArtefactNotPlacedError`, it has `removal_error`: the `OSError` from removing the temporary file afterwards, or `None`. The removal is still attempted. The new class carries `errno`, `strerror`, `filename` and `filename2` of the test's error, and has that error as `__cause__`.
- **The same on every version.** The post-end test must propagate every `OSError` other than "absent" on 3.11 to 3.14. "Absent" means `FileNotFoundError` and `NotADirectoryError`, which leave today's result: exit 0 without an artefact, `ok` `False`, no exception. One way is `os.stat(temporary)` with `stat.S_ISREG` in place of `temporary.is_file()`. The executor chooses the means, but the acceptance criteria must hold on 3.11 and on 3.14. A path that exists but is not a regular file reads as "no artefact", as today.
- **Precedence.** Only one of the three classes is raised per call. The move is not attempted when the test failed, so `ArtefactNotPlacedError` cannot arise together with the new class. If the removal also fails, `ArtefactNotCheckedError` is raised and the removal error is its `removal_error`. `TemporaryNotRemovedError` is not raised in that case.
- **Unchanged.** The test is made only when the compiler exited with 0. With a non-zero exit or a timeout, nothing about the test changes (short-circuit as today). Nothing changes for errors raised before the start, for the error from starting the compiler, or for anything else `subprocess.run` raises. `BuildResult` keeps its fields and their order.
- Language: Python, because the module is Python. Record this in `## Result` (CLAUDE.md language policy).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0246-<slug>`, the trailer `Task: T-0246` on commits and as the last line of the PR body, size cap, the D12 test rules).
- `CLAUDE.md`: "테스트 규칙", "브랜치·merge 절차" (code mode: Draft PR, review cycle, CI green, self squash-merge), "코멘트 최소화", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`: N2 (line 21), decision 5 (line 56), Consequences (line 84). Read only; do not edit.
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: decision 2 (section "### 2. Which builds' logs are kept", from line 32). Read only.
- `hilclaw/clang_build.py` (whole file, 295 lines; `build` is at lines 103-207, the post-end test at line 180).
- `tests/test_clang_build.py`: the stub-compiler `PRELUDE` and the fixtures at the top (lines 26-105), and lines 325-540 (`FILE_ERRORS`, `is_temporary`, the fixtures `failing_replace` and `failing_unlink`, and the T-0244 tests including pickling).
- `PROCESS/tasks/T-0244-clang-build-keeps-log-on-file-errors.md` (the same pattern, for reference only).

## Acceptance Criteria

1. `hilclaw/clang_build.py` defines `ArtefactNotCheckedError`, an `OSError` subclass with `result` (a `BuildResult` or `None`, as the existing classes allow) and `removal_error` (`OSError` or `None`, default `None`). It is not in a subclass relation with `ArtefactNotPlacedError` or `TemporaryNotRemovedError` in either direction. It has a short docstring saying when it is raised (Doxygen-like docs on public API are allowed by "코멘트 최소화"; no other new comments). It survives `pickle` with `type`, `str`, `errno`, `strerror`, `filename`, `filename2`, `result` and `removal_error` preserved.
2. **Test fails after exit 0 (happy path of the new behaviour).** The stub compiler exits 0 and writes its output. `os.stat` as seen by the module (for example `monkeypatch.setattr(clang_build.os, "stat", …)`) raises `PermissionError(13, "denied", <tmp>)` only for the temporary path (`is_temporary`) and delegates for every other path. Then `build` raises `ArtefactNotCheckedError`:
   - `__cause__` is that error, and `errno`, `strerror` and `filename` equal its values;
   - `result.ok is False`, `result.returncode == 0`, `result.timed_out is False`;
   - `result.log` holds what the stub wrote to stdout and stderr;
   - `result.command` and `result.output` are as a normal call would report them;
   - `removal_error is None`;
   - the temporary file is gone;
   - a file that was already at `output` is untouched (same bytes), and `os.replace` was not called.
   This test passes unchanged on Python 3.11 and on Python 3.14 (CI runs both).
3. **Test fails and removal fails.** As in 2, with `failing_unlink` as well: `ArtefactNotCheckedError` is raised, its `removal_error` is the removal error, its `__cause__` is still the test's error, and no `TemporaryNotRemovedError` is raised.
4. **"Absent" is unchanged (branch).** As in 2, but the patched call raises `FileNotFoundError` for the temporary path: `build` returns, with no exception, a result with `ok` `False` and `returncode` 0, as the existing exit-0-without-artefact case does. One more test does the same with `NotADirectoryError`.
5. **No test without exit 0 (branch).** With the same failing patch as in 2 and the stub exiting non-zero, `build` returns a result with `ok` `False` and the stub's log, with no exception. With a timeout, `build` returns a result with `timed_out` `True`, with no exception.
6. **Unchanged paths (negative and regression).** An `OSError` from starting the compiler still propagates as that very object, is none of the three classes, and has no `result`. Every existing test in `tests/test_clang_build.py` still passes. When nothing fails, `build` returns as today.
7. An `except OSError` around `build` catches the new class (one test is enough). `BuildResult._fields` is unchanged.
8. The `build` docstring states the new behaviour next to the T-0244 sentences: what is raised when testing for the temporary file fails after the compiler ended, that the new class carries `result` with the log, the `removal_error` rule, and that only "absent" reads as no artefact. Change nothing else in the docstring except what the new sentence makes inexact. The module docstring stays as it is.
9. **Tests.** All new tests go in `tests/test_clang_build.py`. The existing tests of this file may be edited only to:
   - add the new name to the `from hilclaw.clang_build import (…)` list and to `FILE_ERRORS`;
   - add the new class to the existing pickling and class-relation tests.
   Make the patch delegate to the real function for every path that is not the temporary file, so the earlier path checks and `shutil.which` keep working. Do not rely on file permissions. No other existing test file is edited. If an existing test elsewhere fails because of this change, stop and return BLOCKED (`requirement-unclear`) naming the test, rather than editing it.
10. `python -m pytest` passes in full. `ruff check .` and `ruff format --check .` are clean. Line and function coverage of `hilclaw/` stays ≥ 80%, and `hilclaw/clang_build.py` stays at its current 100%. The real-clang tests stay skipped where clang is absent, as today.
11. D16: no `claude` process is started. The only compiler run is the existing stub, plus real `clang` in the existing clang-marked tests where present. No new external dependency.

## Out of Scope

- Any `ARCHITECTURE/` edit, including OD-18 ⑱ (마), ADR-0060, ADR-0078 or ADR-0079 text. Mapping the new error to a row or `error.kind` is a later record's job.
- A separate class or means for telling an `OSError` from starting the compiler apart from same-class errors (ADR-0079 decision 4). That is a separate code task (candidate next task).
- The path tests before the start (`_checked_sources`, the output directory checks) and their version-dependent behaviour (ADR-0079 decision 5).
- `hilclaw/layout.py`, `hilclaw/build_log.py`, the log keeper, `hilclaw/check_operation.py`, any operation of `cpu_standin` (T-0243, BLOCKED on HQ-0026).
- `compiler_version`, `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py`, `hilclaw/standin_profile.py` and their tests. Their docstrings ("passed on unchanged") stay true.

## Follow-ups

- (code, candidate next task) Give `clang_build.build` a way to tell an `OSError` from starting the compiler apart from same-class errors before the start or after the end (ADR-0079 decision 4, T-0245 follow-up (2)). For example, raise a class of its own only from the start of the process.
- (doc) Record under OD-18 ⑱ (마) that `build` now tells apart the post-end test error, and place it in a row, or leave it open with a reason. When editing `ARCHITECTURE/Requirements.md` and `ARCHITECTURE/OpenDecisionProposals.md`, follow the recording rules written in those files: the Requirements register's "행 형식" and the OpenDecisionProposals header's "기록 규칙". Re-check coverage per the first paragraph of StandardScenarios §검사 결과.

## Result

- PR #156 (squash-merged; the squash commit is the one with trailer `Task: T-0246` on `main`). Branch `claude/T-0246-clang-build-keeps-log-on-artefact-test-error`.
- `hilclaw/clang_build.py`: after an exit 0, `build` tests the temporary file with `os.stat` + `stat.S_ISREG` instead of `Path.is_file`. `FileNotFoundError` and `NotADirectoryError` read as no artefact (unchanged result); any other `OSError` is raised as the new `ArtefactNotCheckedError` (on `_EndedBuildError`, `removal_error` as in `ArtefactNotPlacedError`), carrying the `BuildResult` with the log. No move is attempted then; it takes precedence over `TemporaryNotRemovedError`. Same behaviour on Python 3.11 to 3.14. `build` and `TemporaryNotRemovedError` docstrings amended; module docstring unchanged.
- Tests: new tests in `tests/test_clang_build.py` for AC 2-7 (failing test, failing test plus failing removal, `FileNotFoundError`/`NotADirectoryError` as absent, non-regular temporary, no test after non-zero exit or timeout, start error unchanged); the new class added to the import list, `FILE_ERRORS`, the class-relation, no-errno and pickling tests. Full `pytest` passes (22134 passed, 355 skipped locally on 3.14); `hilclaw/` coverage 99%, `hilclaw/clang_build.py` 100%; ruff check/format clean. CI green on 3.11 and 3.14.
- Review: 2 rounds (round 1 Approve with one nit fixed: `NotADirectoryError` built with `ENOTDIR`; round 2 Approve).
- Language: Python, because the module is Python.
- Follow-ups:
  - (doc) The Follow-ups above stand. When placing `ArtefactNotCheckedError` under OD-18 ⑱ (마), record that on 3.11 to 3.13 the change also turns errors `Path.is_file` used to swallow as `False` (`ELOOP`, `EBADF`, Windows errors 21/123/1921) into `ArtefactNotCheckedError` (reviewer round 1, Low).
  - (code, candidate next task) ADR-0079 decision 4, as in Follow-ups above.
