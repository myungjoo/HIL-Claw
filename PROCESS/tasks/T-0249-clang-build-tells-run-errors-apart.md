---
id: T-0249
title: Let `hilclaw.clang_build.build` raise an `OSError` from talking to the running compiler as a new `OSError` subclass `CompilerRunError`, so it is told apart by class from errors before the start (ADR-0080 decision 4, M3)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-6, FR-10, OD-18, "#5 D12"]
dependsOn: [T-0247, T-0248]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 60, files: 1}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

ADR-0080 (T-0248, `afb9f2e`) decision 4 keeps open under OD-18 ⑱ (마) "an `OSError` raised after the compiler process was created and before it ended, and the removal error passed on in its place (M3), which by class cannot be told apart from an error before the start". Its alternatives table says of placing that error: "It comes in the same classes as errors before the start (M3, M4), so an operation could not apply either; telling it apart is a code change." Its Consequences say: "A further means of telling apart the errors of decision 4's open list is a later code task." This is that code task for M3. It is the follow-up "the rest of ⑱ (마): `OSError` after the process exists and before it ends" in T-0248's Result.

Today, at `ab950da`, `build` creates the process with `subprocess.Popen` and then calls `_communicate`. An `OSError` raised from `_communicate` is passed on as that very object, for example from reading the pipe, from `kill`, or from the `with process:` exit. If removing the temporary file then fails too, the removal error is passed on instead. In both cases the caller gets a plain `OSError` with no `result`, of the same classes that the path tests raise before the start (`FileNotFoundError`, `IsADirectoryError`, `NotADirectoryError`, and on 3.11 to 3.13 others; ADR-0080 M4). After this task, every `OSError` that `build` raises once the process exists is one of its own subclasses, and a plain `OSError` class from `build` can only come from before the start.

This task places no error in a row and edits no `ARCHITECTURE/` file. A later doc record places the new class (Follow-ups).

**Why this item now.** STATE has no lock, no current or next task, no TODO or INTERRUPTED task file, and no open PR (checked 2026-10-17 at `ab950da`). PLAN P1 has three open items. P1-1 continues through OD-18 work like this one, and its `profiler.collect` part waits on HQ-0025. P1-8 and P0.5-4 have no follow-up queued. The unlanded branches of the BLOCKED tasks T-0210, T-0225, T-0231 and T-0233 do not touch either file of this task. T-0243 (BLOCKED on HQ-0026) owns `hilclaw/layout.py` and a new `hilclaw/build_log.py`. This task does not depend on it and adds no layout function, keeper or writer. The two round-7 wording minors of T-0248 are to be applied only "if a later record touches the same lines", so they are not a task of their own.

**Planner's design (the reviewer is asked to check it against ADR-0080 M3 and decision 4, and against the `build` docstring it amends):**
- **A new public class `CompilerRunError`** in `hilclaw/clang_build.py`. It is an `OSError` subclass built on the private `_CopiedOSError`, like `CompilerNotStartedError`. It carries `errno`, `strerror`, `filename` and `filename2` of the error, has that error as `__cause__`, and has `removal_error`: the `OSError` from removing the temporary file afterwards, or `None`. It has **no `result`**. The output that `communicate` read before it failed is not available to `build`, and this task does not try to recover it (Out of Scope). It is in no subclass relation, in either direction, with `CompilerNotStartedError`, `ArtefactNotPlacedError`, `ArtefactNotCheckedError`, `TemporaryNotRemovedError` or `_EndedBuildError`. The executor may share the `removal_error` and pickling code with `CompilerNotStartedError` through a private base, as long as these relations hold. The name is fixed, because the acceptance criteria test it.
- **What it covers.** It covers any `OSError` raised by the `_communicate(process, timeout_s)` call in `build`, that is, after `Popen` construction returned and before `build` has the return code. It does not cover an `OSError` inside `Popen` construction (ADR-0080 M5, which stays `CompilerNotStartedError`). It also does not cover the test, move or removal after the end (the existing three classes). `_communicate` already kills the process on any exception and waits for it on the `with` exit. Keep that.
- **Precedence.** If the removal of the temporary file then fails too, `CompilerRunError` is still raised and the removal error is its `removal_error`. Today the removal error is passed on instead. This mirrors T-0247 for the start error.
- **Unchanged.** Errors before the start, `CompilerNotStartedError`, everything after the compiler ended, the results, `BuildResult._fields`, `compiler_version`, and any non-`OSError` exception from `_communicate` (for example `KeyboardInterrupt`). The process is still killed and the exception passes on as it is. If such an exception is followed by a failed removal, the current behaviour stays: the removal error is raised.
- Language: Python, because the module is Python. Record this in `## Result` (CLAUDE.md language policy).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0249-<slug>`, the trailer `Task: T-0249` on commits and as the last line of the PR body, size cap, the D12 test rules).
- `CLAUDE.md`: "테스트 규칙", "브랜치·merge 절차" (code mode: Draft PR, review cycle, CI green, self squash-merge), "코멘트 최소화", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- `ARCHITECTURE/decisions/ADR-0080-od18-correctness-check-build-errors-now-told-apart.md`: Context M1 to M5 (lines 18-24), decision 4 (lines 49-52), the last row of the Alternatives table (line 75). Read only; do not edit.
- `hilclaw/clang_build.py` (whole file, 381 lines; the error classes at lines 61-147, `build` at lines 150-276 with its docstring sentence "Any other :class:`OSError` raised while the process runs …" at line 186, `_communicate` at lines 309-323).
- `tests/test_clang_build.py`: imports, `PRELUDE`, `Stub` and fixtures (lines 1-105), `FILE_ERRORS` and `failing_unlink` (lines 328-366), the start-error tests and `failing_communicate` with its two tests (lines 520-667), and the class and pickling tests of `CompilerNotStartedError` (lines 683-745).
- `PROCESS/tasks/T-0247-clang-build-tells-start-errors-apart.md` (the same pattern for the start error, for reference only).

## Acceptance Criteria

1. **The class.** `hilclaw/clang_build.py` defines `CompilerRunError`, an `OSError` subclass with `removal_error` (`OSError` or `None`, default `None`) and no `result` attribute.
   - It is in no subclass relation, in either direction, with `CompilerNotStartedError`, `ArtefactNotPlacedError`, `ArtefactNotCheckedError` or `TemporaryNotRemovedError`.
   - It has a short docstring saying when it is raised. Doxygen-like docs on public API are allowed by "코멘트 최소화"; add no other new comments.
   - Built from an `OSError` without `errno`, its `str` is the message and its `errno` is `None`.
   - It survives `pickle` with `type`, `str`, `errno`, `strerror`, `filename`, `filename2` and `removal_error` preserved.
2. **Talking to the process fails (happy path of the new behaviour).** Use the existing `failing_communicate` fixture: a `Popen` subclass whose first `communicate` raises `OSError(errno.EIO, "input/output error")`. Then `build` with the stub compiler (`SLEEP`) raises `CompilerRunError`:
   - its `__cause__` is that error, and its `errno` and `strerror` equal that error's;
   - its `removal_error` is `None`;
   - it is not a `CompilerNotStartedError`, is none of the three `FILE_ERRORS` classes, and has no `result`;
   - the recorded process has ended (`poll()` is not `None`, and its return code is not 0) and its `stdout` is closed;
   - the output directory holds no file, and the call returns well within the existing 20 s bound.
   One more parametrized case does the same with an error of a class that a path test before the start also raises, for example `FileNotFoundError(errno.ENOENT, …)`. It must still come out as `CompilerRunError` and not as `FileNotFoundError` itself.
3. **Talking fails and removal fails.** As in 2, with `failing_unlink` as well: `CompilerRunError` is raised, its `removal_error` is the removal error, and its `__cause__` is still the communicate error.
4. **Branch: an error from `kill` after a failed communicate.** Patch the recorded `Popen` subclass so that `kill` also raises an `OSError`. Then `build` raises `CompilerRunError` whose `__cause__` is the `OSError` that left `_communicate` (whichever the code's structure gives, asserted exactly), and leaves no temporary file. After the test, the test itself ends the process it started (for example by calling the real `kill` and `wait`) so that no stub survives. If the executor finds this case already covered by criterion 2, or impossible without changing `_communicate`, it says so in `## Result` and the reviewer accepts it.
5. **Not the new class (negative).**
   - A failed start (the existing `failing_start` tests and the real missing-`cwd` test) is still `CompilerNotStartedError` and not `CompilerRunError`.
   - Errors before the start (missing source, missing output directory) are still the plain classes, and `Popen` is not called.
   - A timeout, a compile error, exit 0 without an artefact, and a successful build give the same results as today.
   - The `ArtefactNotPlacedError`, `ArtefactNotCheckedError` and `TemporaryNotRemovedError` tests pass unchanged and none of them is a `CompilerRunError`.
   - A `KeyboardInterrupt` raised by `communicate` passes on as it is (not wrapped), and the process has ended. One test is enough.
6. An `except OSError` around `build` catches `CompilerRunError`. Extend the existing `test_except_oserror_catches_*` parametrization or add one test. `BuildResult._fields` is unchanged.
7. **Docstring.** In the `build` docstring, replace the sentence "Any other :class:`OSError` raised while the process runs is passed on as it is, unless removing the temporary file then fails too, whose error is passed on instead." with the new behaviour: such an error is raised as `CompilerRunError` (an `OSError` subclass without `result`), and when removing the temporary file then fails too, the removal's error is its `removal_error`. Change nothing else in the docstring except what the new sentence makes inexact. The module docstring stays as it is unless one of its sentences becomes untrue; the executor then corrects it and reports the change in `## Result`.
8. **Tests.** All new tests go in `tests/test_clang_build.py`. The existing tests of this file may be edited only as follows:
   - Add the new name to the `from hilclaw.clang_build import (…)` list.
   - Replace `test_error_after_the_start_is_passed_on` and `test_failed_removal_after_an_error_after_the_start` with tests of criteria 2 and 3. They assert the behaviour this task changes.
   - Extend `failing_communicate` (for example to record the instance or let a test choose the error) if criteria 2 and 4 need it.
   - Add the new class to the parametrization of `test_except_oserror_catches_*` if criterion 6 is met there.
   Do not add the new class to `FILE_ERRORS`. No other existing test file is edited. If an existing test elsewhere fails because of this change, stop and return BLOCKED (`requirement-unclear`) naming the test, rather than editing it.
9. `python -m pytest` passes in full on the development machine (Windows) and in CI (Linux, Python 3.11 and 3.14). `ruff check .` and `ruff format --check .` are clean. Line and function coverage of `hilclaw/` stays ≥ 80%, and `hilclaw/clang_build.py` stays at its current 100%.
10. D16: no `claude` process is started. The only compiler run is the existing stub, plus real `clang` in the existing clang-marked tests where present. No new external dependency.

## Out of Scope

- Any `ARCHITECTURE/` edit, including OD-18 ⑱ (마) and the text of ADR-0060, ADR-0078, ADR-0079 or ADR-0080. Placing `CompilerRunError` in a row is a later doc task.
- Recovering the output the compiler wrote before `communicate` failed, or giving the new class a `result` or a log.
- The case inside `Popen` construction after the process exists (ADR-0080 M5). It stays `CompilerNotStartedError`.
- The path tests before the start (ADR-0080 M4) and their version-dependent classes; `compiler_version`; `hilclaw/local_run.py`.
- Any caller: `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py`, `hilclaw/standin_profile.py`, `hilclaw/harness/timing.py`, and their tests. Their docstrings ("passed on unchanged") stay true.
- `hilclaw/layout.py`, `hilclaw/build_log.py`, the log keeper, `hilclaw/check_operation.py`, and any operation of `cpu_standin` (T-0243, BLOCKED on HQ-0026).

## Follow-ups

- (doc, candidate next task) Under OD-18 ⑱ (마), write an ADR that places `CompilerRunError`, or leaves it open with a reason. The compiler process existed and was killed, and no log is kept. Weigh S6 against S9 and other candidates under ADR-0060 decision 4, ADR-0078 decision 2 and ADR-0080 decision 4. The record must also say that a plain `OSError` class from `build` now comes only from before the start. If that record edits the same lines, it may apply the two round-7 wording minors of T-0248's Result. When it edits `ARCHITECTURE/Requirements.md`, `ARCHITECTURE/OpenDecisionProposals.md` or `ARCHITECTURE/StandardScenarios.md`, it follows the recording rules written in those files: the Requirements register's "행 형식", the "기록 규칙" in the OpenDecisionProposals header, and the first paragraph of StandardScenarios §검사 결과.
- (code, later) The path tests before the start (ADR-0080 M4): make their raised classes independent of the Python version, if a record asks for it.

## Result
DONE. PR #158, squash-merged as `065113b` (branch `claude/T-0249-clang-build-tells-run-errors-apart`, deleted). Review: 2 rounds (round 1 Approve with one nit: one docstring line ran to 84 columns, rewrapped in `daf8bc0`; round 2 Approve). CI green on the final head (Python 3.11 and 3.14 gates, coverage gate, C, sh and test-presence gates). Local (Windows, Python 3.14): full `pytest` 22157 passed, 355 skipped; `ruff check .` and `ruff format --check .` clean; `hilclaw/clang_build.py` at 100% line coverage.

- Language: Python, because the module is Python.
- `CompilerRunError` and `CompilerNotStartedError` now share a private base `_UnendedBuildError` (`removal_error` and `__reduce__`). Neither is a subclass of the other or of the three after-the-end classes. `build` wraps only the `_communicate` call, so an error inside `Popen` construction (ADR-0080 M5) stays `CompilerNotStartedError`.
- Criterion 4 (kill branch) is covered by its own test. The test uses the `WRITE` stub, which exits by itself. With `SLEEP`, the `with process:` exit would wait the full 30 s for a process that a failing `kill` did not end. The `__cause__` is the `kill` error, and its `__context__` is the communicate error. The test then calls the real `kill` and `wait`.
- A fix outside the task's design, needed for criterion 1's pickling (`str` preserved): `_CopiedOSError._copy` set `filename` and `filename2` to `None` explicitly. That made `OSError.__reduce__` emit five arguments. On Windows, an error with `errno` and no filename (for example the EIO of a failed communicate) then came back from pickle as `[WinError None] ...`. The bug affected all five error classes. Now the filenames are set only when there is a filename. A new regression test covers all five classes.
- An extra test, `test_failed_removal_after_a_keyboard_interrupt_after_the_start`, keeps the unchanged path of a failed removal after a non-`OSError` covered. This path was covered before by the test that was replaced.
- Criterion 6 is met with a new test, `test_except_oserror_catches_run_error`, and not by extending the existing parametrization, whose body would have needed editing. The module docstring is unchanged; none of its sentences became untrue.
- Follow-ups: as listed above. The doc task that places `CompilerRunError` under OD-18 ⑱ (마) is the next candidate.
