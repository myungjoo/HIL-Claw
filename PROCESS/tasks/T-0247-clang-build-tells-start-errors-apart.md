---
id: T-0247
title: Let `hilclaw.clang_build.build` tell an `OSError` from starting the compiler apart from same-class errors before the start and after the end, by raising it as a new `OSError` subclass `CompilerNotStartedError` (ADR-0079 decision 4)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-6, FR-10, OD-18, "#5 D12"]
dependsOn: [T-0244, T-0245, T-0246]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 90, files: 1}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

ADR-0079 (T-0245, `994ca3d`) decision 4 places "An `OSError` from starting the compiler process — or, after such a failed start, from removing the temporary file (N2)" in row S6, `compiler_unavailable`. It also says: "By its class alone an operation cannot see that an `OSError` came from the start: N2 shows errors of the same classes before the start and after the end. **This decision applies to an error the operation can tell came from the start** — by a change of `clang_build.build`, as T-0244 made for the move and the removal, or by a step of its own … which way is the code task's." Decision 5 keeps "telling an error from the start apart from an `OSError` of the same class before the start or after the end" open under OD-18 ⑱ (마). This task gives the code the means. It is follow-up (2) in T-0245's Result and the code follow-up in T-0246's Result.

Today `build` passes the start error on as the very object `subprocess.run` raised (for example a `PermissionError` or `FileNotFoundError`). A missing source or output directory raises `FileNotFoundError` before the start too. On Python 3.11 to 3.13, `pathlib` tests before the start can also propagate other `OSError`s. And `subprocess.run` raises an `OSError` from talking to the process after it started (for example reading its pipe) in the same way as one from creating it. If the start error is "passed on instead" by a failing removal, the start is not visible at all. After this task, an `OSError` from creating the compiler process is always raised as one class that nothing else in `build` raises.

This task does not place any other error and edits no `ARCHITECTURE/` file. A later doc record notes that the code now tells start errors apart (Follow-ups).

**Why this item now.** STATE has no lock, no current or next task, no TODO or INTERRUPTED task file, and no open PR (checked 2026-10-17 at `1c16df0`). PLAN P1 has three open items. P1-1 continues through OD-18 work like this one, and its `profiler.collect` part waits on HQ-0025. P1-8 and P0.5-4 have no follow-up queued. T-0243 (`hilclaw/layout.py`, a new `hilclaw/build_log.py`) is BLOCKED on HQ-0026. This task does not depend on it, touches none of its files, and does not work around its question: it adds no layout function, keeper or writer. No other BLOCKED task (T-0210, T-0225, T-0231, T-0233, T-0239, T-0243) touches either file of this task.

**Planner's design (the reviewer is asked to check it against ADR-0079 N2 and decision 4, and against the `build` docstring it amends):**
- **A new public class `CompilerNotStartedError`** in `hilclaw/clang_build.py`, an `OSError` subclass. It is not in a subclass relation, in either direction, with `ArtefactNotPlacedError`, `ArtefactNotCheckedError`, `TemporaryNotRemovedError` or the private `_EndedBuildError`, and it has no `result` attribute: no compiler process exists, so there is no log (ADR-0079 decision 4, "No log"). It carries `errno`, `strerror`, `filename` and `filename2` of the start error, has that error as `__cause__`, and has `removal_error`: the `OSError` from removing the temporary file afterwards, or `None`. The executor may share code with `_EndedBuildError` (for example a common private base for copying the error and pickling) as long as these relations hold. The name is fixed, because the acceptance criteria test it.
- **"From starting" means from creating the process**: an `OSError` raised while constructing `subprocess.Popen`, before any process exists. `subprocess.run` does not let the caller tell this apart from an `OSError` raised after the process was created, so `build` creates the process with `subprocess.Popen` and then does what `subprocess.run` does today. The executor writes this by reading `subprocess.run` in the CPython source of the installed version. It must keep, on POSIX and on Windows: `communicate(timeout=…)`; on `TimeoutExpired`, kill only the started process and collect the output as `run` does on that platform; on any other exception after the start, kill the process and re-raise; wait for the process and close the pipes on every path (as `with Popen(...)` does). The module docstring's sentences on timeouts (only the started process is killed; a survivor holding the pipe open can make the call last longer than the limit) must stay true. Every existing timeout test passes unchanged.
- **Precedence.** A start error is raised as `CompilerNotStartedError`. If the removal of the temporary file then fails too, `CompilerNotStartedError` is still raised and the removal error is its `removal_error`, in place of today's "the removal error is passed on instead". This matches ADR-0079 decision 4, which puts both cases in S6.
- **Unchanged.** Errors before the start (`ValueError`, `TypeError`, `CompilerNotFoundError`, the path errors) are unchanged. An `OSError` raised after the process was created (for example from `communicate`) is passed on as that very object, not as the new class, with no `result`. When its removal also fails, the removal error is passed on instead, as today. That error stays open under (마); this task does not place it. Everything after the compiler ended (the three classes of T-0244/T-0246, the results) is unchanged. `BuildResult` keeps its fields and their order. `compiler_version` is not changed.
- Language: Python, because the module is Python. Record this in `## Result` (CLAUDE.md language policy).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0247-<slug>`, the trailer `Task: T-0247` on commits and as the last line of the PR body, size cap, the D12 test rules).
- `CLAUDE.md`: "테스트 규칙", "브랜치·merge 절차" (code mode: Draft PR, review cycle, CI green, self squash-merge), "코멘트 최소화", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`: Context N2, decision 4 ("### 4. An `OSError` from starting the compiler"), decision 5. Read only; do not edit.
- `hilclaw/clang_build.py` (whole file, 332 lines; the error classes at lines 59-120, `build` at lines 122-244, the `subprocess.run` call at line 192).
- The CPython source of `subprocess.run` (`subprocess.py` of the installed Python; the `with Popen(...)` block), to mirror it.
- `tests/test_clang_build.py`: the imports and the stub-compiler `PRELUDE`, `Stub` and fixtures (lines 1-105), `test_timeout_kills_the_compiler` (line 286), and lines 325-735 (`FILE_ERRORS`, `failing_unlink`, the class-relation and pickling tests, and the three start-error tests at lines 522, 537 and 712).
- `PROCESS/tasks/T-0246-clang-build-keeps-log-on-artefact-test-error.md` (the same pattern, for reference only).

## Acceptance Criteria

1. `hilclaw/clang_build.py` defines `CompilerNotStartedError`, an `OSError` subclass with `removal_error` (`OSError` or `None`, default `None`) and no `result` attribute. It is in no subclass relation, in either direction, with `ArtefactNotPlacedError`, `ArtefactNotCheckedError` or `TemporaryNotRemovedError`. It has a short docstring saying when it is raised (Doxygen-like docs on public API are allowed by "코멘트 최소화"; no other new comments). Built from an `OSError` without `errno`, its `str` is the message and `errno` is `None`. It survives `pickle` with `type`, `str`, `errno`, `strerror`, `filename`, `filename2` and `removal_error` preserved.
2. **Start fails (happy path of the new behaviour).** `subprocess.Popen` as seen by the module (for example `monkeypatch.setattr(clang_build.subprocess, "Popen", …)`) raises `PermissionError(13, "cannot start", <path>)`. Then `build` raises `CompilerNotStartedError`:
   - `__cause__` is that error, and `errno`, `strerror` and `filename` equal its values;
   - `removal_error is None`;
   - it is none of the three classes of `FILE_ERRORS` and has no `result`;
   - the output directory holds no new file, and a file that was already at `output` is untouched.
   One more parametrized case does the same with `FileNotFoundError(2, …)`, as a missing compiler or working directory gives.
3. **Start fails and removal fails.** As in 2, with `failing_unlink` as well: `CompilerNotStartedError` is raised, its `removal_error` is the removal error, and its `__cause__` is still the start error.
4. **A real failed start (branch, no patching).** `build` with the stub compiler and `cwd` set to a directory that does not exist raises `CompilerNotStartedError` whose `__cause__` is an `OSError`, and the stub was not started. Assert only what holds on Linux and on Windows; do not assert the platform's class or `errno`.
5. **An `OSError` after the process was created is not the new class (negative).** `subprocess.Popen` is replaced by a subclass of the real one whose `communicate` raises `OSError(5, "input/output error")` on its first call. Then `build`:
   - raises that very object, which is not a `CompilerNotStartedError` and none of the `FILE_ERRORS`, with no `result`;
   - leaves no temporary file;
   - leaves the started process ended (killed and waited for), and that can be observed in the test (for example `poll()` of the recorded instance is not `None`).
   With `failing_unlink` as well, the removal error is passed on instead, as today.
6. **Unchanged paths (regression).**
   - Every error raised before the start (missing source, missing output directory, bad flags, bad timeout, missing compiler) is unchanged, and `Popen` is not called for them. One test with a recording `Popen` and a missing source is enough.
   - A successful build, a compile error, exit 0 without an artefact, and a timeout give the same results as today. `test_timeout_kills_the_compiler` passes unchanged.
   - The T-0244/T-0246 tests pass unchanged, and so do the real-clang tests where clang is present.
7. An `except OSError` around `build` catches `CompilerNotStartedError` (one test is enough). `BuildResult._fields` is unchanged.
8. The `build` docstring replaces the sentence "An :class:`OSError` from starting the process is passed on as it is, unless removing the temporary file then fails too, whose error is passed on instead." with the new behaviour: an `OSError` from creating the compiler process is raised as `CompilerNotStartedError` (an `OSError` subclass without `result`); the `removal_error` rule; and that any other `OSError` raised while the process runs is passed on as it is, or the removal's error instead when that removal fails. Change nothing else in the docstring except what the new sentence makes inexact. The module docstring stays as it is unless one of its sentences becomes untrue, which the executor then corrects and reports in `## Result`.
9. **Tests.** All new tests go in `tests/test_clang_build.py`. The existing tests of this file may be edited only as follows:
   - Add the new name to the `from hilclaw.clang_build import (…)` list.
   - Replace the three tests that patch `clang_build.subprocess.run` (`test_error_from_starting_the_compiler_is_passed_on`, `test_failed_removal_after_a_failed_start_is_passed_on`, `test_error_from_starting_is_no_new_error_with_a_failing_test`). They patch a function `build` no longer calls. Their replacements patch `Popen` and assert the new behaviour (criteria 2 and 3). The third replacement keeps its own point: a start error with `failing_stat` is a `CompilerNotStartedError`, and `failing_stat` records nothing.
   Do not add the new class to `FILE_ERRORS`. Its relation and pickling assertions go in new tests. No other existing test file is edited. If an existing test elsewhere fails because of this change, stop and return BLOCKED (`requirement-unclear`) naming the test, rather than editing it.
10. `python -m pytest` passes in full on the development machine (Windows) and in CI (Linux, Python 3.11 and 3.14). `ruff check .` and `ruff format --check .` are clean. Line and function coverage of `hilclaw/` stays ≥ 80%, and `hilclaw/clang_build.py` stays at its current 100%, including the branches that mirror `subprocess.run` on each platform. A branch that only one platform reaches may be covered by a test that patches the module's platform test, if the executor's mirror has one. Otherwise the executor names the uncovered lines in `## Result` and the reviewer accepts them.
11. D16: no `claude` process is started. The only compiler run is the existing stub, plus real `clang` in the existing clang-marked tests where present. No new external dependency.

## Out of Scope

- Any `ARCHITECTURE/` edit, including OD-18 ⑱ (마), ADR-0060, ADR-0078 or ADR-0079 text. Recording that the code now tells start errors apart is a later doc task.
- Placing the `OSError` raised after the process was created, the path errors before the start, or `ArtefactNotCheckedError` in a row (ADR-0079 decision 5).
- `compiler_version` (it keeps `subprocess.run`), `hilclaw/local_run.py`, and any caller: `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py`, `hilclaw/standin_profile.py` and their tests. Their docstrings ("passed on unchanged") stay true.
- `hilclaw/layout.py`, `hilclaw/build_log.py`, the log keeper, `hilclaw/check_operation.py`, any operation of `cpu_standin` (T-0243, BLOCKED on HQ-0026).

## Follow-ups

- (doc, candidate next task) Under OD-18 ⑱ (마), record that `clang_build.build` now tells apart the start error (`CompilerNotStartedError`, this task) and the post-end test error (`ArtefactNotCheckedError`, T-0246), and place the latter in a row or leave it open with a reason. Note that on 3.11 to 3.13 T-0246 also turns errors `Path.is_file` used to swallow (`ELOOP`, `EBADF`, Windows errors 21/123/1921) into `ArtefactNotCheckedError` (T-0246 Result). Also note that an `OSError` raised after the process was created stays open. When editing `ARCHITECTURE/Requirements.md` and `ARCHITECTURE/OpenDecisionProposals.md`, follow the recording rules written in those files: the Requirements register's "행 형식" and the OpenDecisionProposals header's "기록 규칙". Re-check coverage per the first paragraph of StandardScenarios §검사 결과.

## Result

- PR #157 (squash-merged; the squash commit is recorded by the driver). Review: 2 rounds, Approve (round 1 Approve with one docstring-reflow nit, fixed and re-reviewed).
- `hilclaw/clang_build.py`: `build` creates the compiler with `subprocess.Popen` and mirrors the `with Popen(...)` block of CPython 3.14's `subprocess.run` in the private `_communicate`; the platform test is the module constant `_WINDOWS` (`sys.platform == "win32"`, as `subprocess._mswindows`), patched by `test_timeout_on_either_platform` so both timeout branches are covered on every platform. New public `CompilerNotStartedError(error, removal_error=None)`; it and the private `_EndedBuildError` share the private base `_CopiedOSError` (copy of `errno`/`strerror`/`filename`/`filename2` and the pickling copy), so it is in no subclass relation with the three file-error classes. The `build` docstring sentence was replaced as criterion 8 says; the module docstring is unchanged (its timeout sentences stay true).
- Tests: the three `subprocess.run`-patching tests were replaced by `Popen`-patching ones (criteria 2, 3 and the `failing_stat` case); new tests cover a real failed start (missing `cwd`), an `OSError` from `communicate` with and without a failing removal, no `Popen` call for a pre-start error, both timeout branches, class relations, pickling and `except OSError`. Local (Windows, Python 3.14): full `python -m pytest` 22145 passed, 355 skipped; ruff check/format clean; `hilclaw/clang_build.py` coverage 100%.
- CI run 38978665951 on head `f17bd17`: all gates green (Python 3.11 and 3.14, coverage with `hilclaw/clang_build.py` 100% and `hilclaw/` 99%, C, sh, test presence). Landed as squash commit `03f9007`; branch deleted.
- Language: Python, because the module is Python.
- Follow-ups: the doc follow-up above stands. The reviewer noted (info) that an `OSError` raised inside `Popen.__init__` after the OS created the process (POSIX: reading or closing the exec error pipe; Windows: closing the thread handle) is also raised as `CompilerNotStartedError`; this is within the task's definition ("raised while constructing `subprocess.Popen`") and practically unreachable, and may be noted in the same doc task under OD-18 ⑱ (마).
