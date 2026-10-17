---
id: T-0253
title: Make `clang_build.build` pass on an exception that is no `OSError` when removing the temporary file then fails, with the removal error attached as a note
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0251]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 30, files: 1}
hq: []
---
## Why

ADR-0081 K4 (ii) names one way that `hilclaw.clang_build.build` raises an `OSError` that is none of its five classes. An exception that is no `OSError` leaves the block that creates and runs the compiler before `ended` is set. Examples are a `KeyboardInterrupt` from `communicate`, or a `KeyboardInterrupt` or `TypeError` from inside the construction of `subprocess.Popen`. If removing the temporary file then fails, the bare `raise` in the `finally` (around line 291 at `d3becf0`) raises the removal's `OSError` in place of that exception. So today a `KeyboardInterrupt` turns into a `PermissionError`, and the existing test `test_failed_removal_after_a_keyboard_interrupt_after_the_start` pins that behaviour.

Two records leave this open under OD-18 sub-question 18 part (ma). ADR-0081 decision 5 and ADR-0082 decision 5 both list "the removal error raised in place of an exception that is no `OSError` (ADR-0081 K4 (ii))" as open. ADR-0081 Consequences says "Telling the removal error of K4 (ii) apart is another code task" and leaves names and modules to that task. The Follow-ups of T-0250, T-0251 and T-0252 all list this task.

**The change, stated.** When an exception that is no `OSError` is leaving `build`'s `try` and removing the temporary file fails:
- that exception passes on as it is: the same object and type, with its own traceback and chain;
- the removal's error is not raised in its place. It is attached to the exception with `BaseException.add_note` (Python ≥ 3.11 is the floor in `pyproject.toml`), as one line that names the temporary path and the removal error, for example its `repr`.

No new class and no new member. After this change, a plain `OSError` of `build` (none of the five classes) comes only from the lines before `subprocess.Popen` is called (ADR-0081 K4 (i)). The executor confirms that from the code; it is the fact a later record can use.

Nothing else changes:
- the five classes and their members;
- the `removal_error` of `CompilerNotStartedError`, `CompilerRunError`, `ArtefactNotPlacedError` and `ArtefactNotCheckedError`;
- `TemporaryNotRemovedError` after the compiler ended;
- the results of a normal, failed or timed-out build;
- the kill of the process in `_communicate` on any `BaseException`;
- a non-`OSError` exception whose removal succeeds, which passes on with no note.

This is an engineering choice inside `build`, which ADR-0081 left to the code task. It adds no data-plane member, file, `condition` or `error.kind` value, and it binds no row of `correctness.check`. The row of a plain `OSError` and the K4 entry of (ma) stay for a later doc task.

**Why this item now.** STATE has no lock, current task or next task, and no task file is TODO or INTERRUPTED. There was no open PR on 2026-10-17 at `514f2ef`. PLAN P1-1 continues through OD-18 work:
- its `profiler.collect` part waits on HQ-0025;
- ADR-0078 slices 1 to 3 wait on HQ-0026 (T-0243).

This task depends on neither. The other open follow-up, a record for the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4), may need a new `error.kind`. That would be a data-plane question, so it is not taken first.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, the 2h30 time limit) and §5 (lines 86-114: task format, the branch name `claude/T-0253-<slug>`, the PR title with `T-0253`, the trailer `Task: T-0253` in the commit and as the last line of the PR body, the size cap, the D12 test rules).
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`: Context K4 (line 23), decision 4 (lines 47-51), decision 5 (lines 53-56), Consequences "Code" (line 84). Do not edit it.
- `ARCHITECTURE/decisions/ADR-0082-od18-correctness-check-compiler-run-error-time-limit.md`: decision 5 (lines 53-56). Do not edit it.
- `hilclaw/clang_build.py` at `d3becf0` or later: the module docstring (lines 1-24), `build` (lines 183-321, especially the `try`/`finally` from line 257 and the docstring's paragraph on raised errors), `_communicate` (lines 363-378).
- `tests/test_clang_build.py`: the fixtures `failing_unlink` (line 355), `failing_start` (line 525) and `failing_communicate` (line 622); the tests `test_failed_removal_after_a_failed_start` (line 571), `test_keyboard_interrupt_after_the_start_is_passed_on` (line 880), `test_failed_removal_after_a_keyboard_interrupt_after_the_start` (line 893) and `test_errors_outside_the_run_are_not_run_errors` (line 907).
- `PROCESS/tasks/T-0249-clang-build-tells-run-errors-apart.md`, "Unchanged" (line 27): the behaviour this task changes.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build`.** Change the cleanup as "The change, stated" says:
   - When an exception that is no `OSError` is in flight and the removal fails, that exception is re-raised unchanged. Its `__context__`, `__cause__` and traceback are not replaced. It carries exactly one added note that names the temporary path and the removal error.
   - Find the in-flight exception from the `try` itself, for example with an `except BaseException` that records it and re-raises. Do not rely on `sys.exc_info()` inside `finally`.
   - Every other path keeps its current behaviour.
   - Keep the change small. Add no new public name and no comment that restates the code.
3. **Docstrings.** In `build`'s docstring, state that an exception that is no `OSError` is passed on, and that a failed removal after it is attached as a note rather than raised. Touch the module docstring only if a sentence in it becomes wrong.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the test fixtures.
   - Happy path: a `KeyboardInterrupt` from `communicate` with a failed removal (`failing_unlink`) is raised as the same object. It has exactly one note, which contains the temporary file's name and the removal error's message. The process has ended. Rewrite `test_failed_removal_after_a_keyboard_interrupt_after_the_start`; do not keep the old expectation of a `PermissionError`.
   - Branch: a `KeyboardInterrupt` raised by the construction of `Popen` (through `failing_start` or a similar monkeypatch) with a failed removal is passed on with the note. It is not a `CompilerNotStartedError`.
   - Branch: an `Exception` that is no `OSError` (for example `RuntimeError`) from `communicate` with a failed removal is passed on with the note. It is not a `CompilerRunError`.
   - Negative: when the removal succeeds, the `KeyboardInterrupt` passes on with no note (`getattr(e, "__notes__", [])` is empty). An `OSError` from `communicate` with a failed removal is still a `CompilerRunError` whose `removal_error` is the removal's error, with no note on it. An existing test may already cover this; if so, leave it and do not duplicate it.
   - The existing tests other than the rewritten one pass unchanged. Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite) and `ruff check` / `ruff format --check` pass. Tests start only the stub compilers the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0253-<slug>` with a Draft PR whose title contains `T-0253`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, with the body's last line `Task: T-0253`;
   - delete the branch.
   - Record in Result the language (Python, the module's language) with a one-line reason.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/` (ADR-0081, ADR-0082, Requirements, OpenDecisionProposals, StandardScenarios). A record that says what a plain `OSError` of `build` now means for `correctness.check` is a follow-up doc task.
- The `CompilerRunError` branch whose `timed_out` is false, the classes of the path tests (ADR-0080 decision 4), and any change to `_communicate`'s kill, wait or read.
- Callers of `build` (`hilclaw/harness/verification_build.py`, `timing_build.py`, `hilclaw/standin_profile.py`), `compiler_version`, and the `cpu_standin` operation of `correctness.check` (HQ-0026).

## Follow-ups

- (doc) A record under OD-18 ⑱ (ma) for what this change makes true. A plain `OSError` of `build` now comes only from before the creation of the compiler process (ADR-0081 K4 (i)), and K4 (ii) no longer raises one. The record weighs whether that lets the K4 entry, or the plain `OSError`, be placed for `correctness.check` (ADR-0081 decision 4, ADR-0082 decision 5).
- (doc) A record for the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4). It may need a new `error.kind`, which would make it a data-plane or owner question.

## Result
