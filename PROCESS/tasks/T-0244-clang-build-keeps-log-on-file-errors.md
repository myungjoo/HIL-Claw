---
id: T-0244
title: Let `hilclaw.clang_build.build` keep the compiler's log when moving the artefact into place or removing its temporary file fails, by raising two new `OSError` subclasses that carry the `BuildResult` (ADR-0078 Consequences, code slice 4)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-6, FR-10, OD-18, "#5 D12"]
dependsOn: [T-0242]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 70, files: 1}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

ADR-0078 (landed on `main` by T-0242, accepted under DRIVER §9, owner window until 2026-10-23) keeps the compiler's log of every build whose compiler process was started and has ended, S9 included (decision 2). Its Consequences name four code slices. Slice (4) reads: "`hilclaw/clang_build.py` passes on an `OSError` from moving the artefact, and one from removing its temporary file, without the log (observation), so the log of that case of S9, and of any build during which the removal fails, is lost unless that function changes; a code task changes it or registers the case." This task changes it. The record says "names and modules are the code task's; this record binds no code".

A side effect, not a decision: today ADR-0060 decision 4 notes that an `OSError` from starting the compiler (S6), from moving the artefact (S9) and from removing the temporary file come up "in the same class from the same call". After this task the last two have classes of their own. This task does not say which row or answer any of them maps to. That stays with the operation of `cpu_standin` and with OD-18 ⑱ (마). It edits no `ARCHITECTURE/` file.

**Why this item now.** No lock, no TODO or INTERRUPTED task, no open PR (checked 2026-10-17 at `b335892`). T-0243 (slices 1 and 2 of the same record: `hilclaw/layout.py` and a new `hilclaw/build_log.py`) is BLOCKED on HQ-0026. This task does not depend on it, touches none of its files, and does not work around its question: no layout function, no keeper, no writer. The other BLOCKED tasks (T-0210, T-0225, T-0231, T-0233, T-0239) touch neither file of this task.

**Planner's design (the reviewer is asked to check it against ADR-0078 decision 2 and Consequences, and against the `build` docstring it amends):**
- Two new exception classes in `hilclaw/clang_build.py`, both subclasses of `OSError`:
  - `ArtefactNotPlacedError`: the compiler exited with 0 and left the temporary file, and `os.replace(temporary, target)` raised an `OSError`.
  - `TemporaryNotRemovedError`: removing the temporary file after the compiler process ended raised an `OSError`, and no `ArtefactNotPlacedError` is being raised.
  The executor may give them a shared base class (for example one that owns `result`). The two names above are fixed because the acceptance criteria test them.
- Each instance has the attribute `result`: the `BuildResult` of the ended compiler process, with the same `log`, `command`, `returncode`, `timed_out`, `duration_s` and `output` the call would otherwise have returned. For `ArtefactNotPlacedError`, `result.ok` is `False`, because `ok` means that the artefact is at `output` and it is not. For `TemporaryNotRemovedError`, `result.ok` is whatever the build reached: `True` if the artefact was moved into place.
- Each instance carries `errno`, `strerror`, `filename` and `filename2` of the `OSError` it replaces, and has that error as `__cause__` (`raise … from error`). An existing `except OSError` keeps catching both. The docstrings of `hilclaw/harness/verification_build.py` and `timing_build.py` ("passed on unchanged") stay true and are not edited.
- When the move fails, the call still tries to remove the temporary file. If that removal also fails, `ArtefactNotPlacedError` is still the one raised. The removal error is kept as an attribute of it, `removal_error` (`None` when the removal succeeded or the file was already gone). It is neither raised nor lost.
- Nothing changes for the errors raised before the compiler is started, for an `OSError` from starting the compiler process, or for anything else `subprocess.run` raises. Those propagate exactly as today, never as one of the new classes, and carry no `result`, since no compiler ended and no log exists.
- Language: Python (the module is Python; record this in `## Result`, CLAUDE.md language policy).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0244-<slug>`, the trailer `Task: T-0244` on commits and as the last line of the PR body, size cap, the D12 test rules).
- `CLAUDE.md`: "테스트 규칙", "브랜치·merge 절차" (code mode: Draft PR, review cycle, CI green, self squash-merge), "코멘트 최소화", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure) and `.claude/skills/dev-code-review/SKILL.md` (what the reviewer checks).
- `ARCHITECTURE/decisions/ADR-0078-od18-correctness-check-compiler-log-file.md`: line 22 (observations of `clang_build`), decision 2 (around line 34, which builds' logs are kept), Consequences lines 123-129 (slice 4).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: the S9 row (line 96) and the paragraph "What the functions on `main` report, against the rows" (line 102). Read only, to see which errors are meant; do not edit.
- `hilclaw/clang_build.py` (whole file, 231 lines) and `tests/test_clang_build.py` (fixtures and the stub-compiler `PRELUDE` at the top, `test_exit_zero_without_artefact_is_not_ok`, `test_timeout_kills_the_compiler`, `test_existing_artefact_survives_failure_and_is_replaced_on_success`).
- `hilclaw/harness/verification_build.py` and `hilclaw/harness/timing_build.py`, the `build` docstrings only (to confirm they stay true).

## Acceptance Criteria

1. `hilclaw/clang_build.py` defines `ArtefactNotPlacedError` and `TemporaryNotRemovedError`, both subclasses of `OSError` and not of each other. Each has `result` (a `BuildResult`). `ArtefactNotPlacedError` also has `removal_error` (`OSError` or `None`). Each class has a short docstring saying when it is raised (Doxygen-like docs on public API are allowed by "코멘트 최소화"; no other new comments).
2. **Move fails (happy path of the new behaviour).** With the stub compiler exiting 0 and writing its output, and `os.replace` as seen by the module raising `PermissionError(13, "denied", <tmp>, None, <target>)`, `build` raises `ArtefactNotPlacedError`:
   - `__cause__` is that error, and `errno`, `strerror`, `filename` and `filename2` equal its values;
   - `result.ok is False`, `result.returncode == 0`, `result.timed_out is False`;
   - `result.log` holds what the stub wrote to stdout and stderr;
   - `result.command` and `result.output` are as a normal call would report them;
   - `removal_error is None`;
   - the temporary file is gone;
   - a file that was already at `output` is untouched (same bytes).
3. **Move fails and removal fails.** As in 2, with the removal of the temporary file also raising `OSError`: `ArtefactNotPlacedError` is raised, its `removal_error` is the removal's error, and its `__cause__` is still the move's error.
4. **Removal fails after an ok build.** With the stub exiting 0 and the move succeeding, a failing removal raises `TemporaryNotRemovedError`. In the case where the removal fails while the temporary file still exists (the executor arranges this with a stub or patch it chooses): `result.ok is True`, the artefact is at `output`, `result.log` holds the stub's output, and `__cause__`, `errno`, `strerror` and `filename` come from the removal's error.
5. **Removal fails after a failed build (branch cases).** One test each:
   - non-zero exit: `TemporaryNotRemovedError` with `result.ok is False` and `result.returncode != 0`;
   - timeout: `result.timed_out is True` and `result.returncode is None`;
   - exit 0 without an artefact: `result.ok is False`, `result.returncode == 0`.
   In each case `result.log` holds what the stub wrote before ending.
6. **Unchanged paths (negative and regression).**
   - an `OSError` from starting the compiler process (for example `subprocess.run` patched to raise `PermissionError`) propagates as that very object, `isinstance(…, (ArtefactNotPlacedError, TemporaryNotRemovedError))` is false, and it has no `result` attribute;
   - every error raised before the start (bad source, output directory, flags, timeout, `CompilerNotFoundError`) is unchanged, so the existing tests pass untouched;
   - when nothing fails, `build` returns as today with no exception.
7. An `except OSError` around `build` catches both new classes (one test is enough). `BuildResult` keeps its fields and their order (no new field).
8. The `build` docstring states the new behaviour in place of "An :class:`OSError` from starting the process or from moving the artefact into place is passed on": what is raised for each of the three `OSError` sources, that the two new classes carry `result` with the log, and the `removal_error` rule. The module docstring stays accurate: it says the artefact is "moved into place … only when the build succeeded". Change nothing else in it.
9. **Tests.** All new tests go in `tests/test_clang_build.py`. Add the two new names to its `from hilclaw.clang_build import (…)` list. Patch through the module (for example `monkeypatch.setattr(clang_build.os, "replace", …)`, or patch `Path.unlink` so that it fails only for the temporary path) so the tests run the same on Linux, macOS and Windows. Do not rely on file permissions. The existing tests of this file may be edited only where the import list or a renamed helper requires it. No other existing test file is edited. If an existing test elsewhere fails because of this change, stop and return BLOCKED (`requirement-unclear`) naming the test, rather than editing it.
10. `python -m pytest` passes in full. `ruff check .` and `ruff format --check .` are clean. Line and function coverage of `hilclaw/` stays ≥ 80% (`hilclaw/clang_build.py` itself should not drop). The real-clang tests stay skipped where clang is absent, as today.
11. D16: no `claude` process is started. The only compiler run is the existing stub, plus real `clang` in the existing clang-marked tests where present. No new external dependency.

## Out of Scope

- Any `ARCHITECTURE/` edit, including OD-18 ⑱ (마), ADR-0060 or ADR-0078 text. A follow-up doc task may record that the code now tells these errors apart.
- `hilclaw/layout.py`, a path function of the log file, the log keeper, `build_log_unwritable`, `hilclaw/check_operation.py`, the mock's operation (ADR-0078 slices 1 to 3; T-0243, BLOCKED on HQ-0026).
- Which row (S6, S9, …) or `error.kind` any of these errors maps to, and any operation of `cpu_standin`.
- Killing the compiler's children on a timeout, or any other change of `build`'s behaviour or of `compiler_version`.
- Edits to `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py` or their tests.

## Follow-ups

- (doc) Note in the OD-18 register text (⑱ (마)) and in OpenDecisionProposals that `clang_build.build` now raises `ArtefactNotPlacedError` / `TemporaryNotRemovedError` with the log, so an operation can tell those cases apart from S6. When editing `ARCHITECTURE/Requirements.md` and `ARCHITECTURE/OpenDecisionProposals.md`, follow the recording rules written in those files: the Requirements register's "행 형식" and the OpenDecisionProposals header's "기록 규칙". Re-check coverage per the first paragraph of StandardScenarios §검사 결과.
- ADR-0078 slices 1 to 3 after HQ-0026 is answered.

## Result

- **Outcome:** DONE. PR #155 (https://github.com/myungjoo/HIL-Claw/pull/155), squash-merged into `main`. The squash commit carries the trailer `Task: T-0244`; look it up with `git log origin/main --grep='^Task: T-0244'`.
- **Review:** 2 rounds by a context-isolated reviewer agent, both Approve. Round 1 raised two nits, both fixed in round 2: the new errors could not be pickled, and the docstring did not say that a failed removal after a failed start replaces the start error. Round 2 found nothing.
- **Change:** `hilclaw/clang_build.py` adds `ArtefactNotPlacedError` and `TemporaryNotRemovedError`. Both are `OSError` subclasses through the private base `_EndedBuildError`, which copies `errno`/`strerror`/`filename`/`filename2`, holds `result` and defines `__reduce__`. Once the compiler process has ended, a failed `os.replace` raises `ArtefactNotPlacedError`, with `result.ok` false and `removal_error` holding the error of the removal that is still attempted. A failed removal alone raises `TemporaryNotRemovedError`. Errors raised before the start, and the error from starting the compiler, are unchanged: an `ended` flag keeps today's `finally` behaviour. The `build` docstring is updated. `BuildResult` and the module docstring are unchanged.
- **Tests:** `tests/test_clang_build.py` has new tests for each of AC2 to AC7, plus pickling and an `OSError` without an errno. They patch through the module and do not rely on file permissions. The existing tests changed only in the import list. Full `python -m pytest` passed locally (22125 passed, 355 skipped), and ruff check and ruff format are clean. Coverage of `hilclaw/clang_build.py` is 100% and of `hilclaw/` 99%.
- **Language:** Python, because the module is Python (CLAUDE.md tool-layer language policy).
- **Follow-ups:** the doc follow-up in the task (record in OD-18 ⑱ (마) and in OpenDecisionProposals that `build` now tells these errors apart from S6). ADR-0078 slices 1 to 3 wait on HQ-0026. No new follow-up.
