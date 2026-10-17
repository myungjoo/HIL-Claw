---
id: T-0255
title: Make `clang_build.build` raise no plain `OSError` after the compiler starts - a failed read of the clock after `_communicate` becomes a `CompilerRunError` that keeps the log
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0253, T-0254]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 25, files: 1}
hq: []
---
## Why

ADR-0083 (landed as `5a82c0c`) found one line of `hilclaw.clang_build.build` that raises a plain `OSError` (none of its five classes) after the compiler process has ended. In ADR-0083 P2 this line is `duration_s = time.monotonic() - started`. It stands in the `else` of the `try` around `_communicate` (line 280 at `0305d7b`), and no `except OSError` covers it. If the monotonic clock cannot be read there:
- the `OSError` leaves `build` plain;
- the compiler's output, already read, is dropped;
- the artefact in the temporary file is removed.

ADR-0083 decision 3 states the costs. The log is lost, against ADR-0078 decision 2. A build that S7 or S8 would make a result is answered by a tool failure. Among the things that "would let it be placed", the same decision names "a code change that raises no plain `OSError` after the compiler started, for example by reading the clock where a failure is caught or by raising it in a class that keeps the result". Its Consequences say that "names and modules are the code task's" and that "this record binds no code". T-0254's Result lists this change as its code follow-up.

**The change, stated.** Read the end time of the build where an `OSError` is already caught as a run error. Then an `OSError` from that clock read is raised as `CompilerRunError` by the existing path:
- `timed_out` is `held.timed_out`, which is true only when the time limit had passed before the error;
- `log` is `held.decoded()`;
- `removal_error` follows the existing rule;
- the chain is `from` the clock's `OSError`.

For example, move the line into the `try` whose `except OSError as error: run_error = error` already exists, after the call of `_communicate`. Then:
- after a normal end, `log` is all the output;
- after a time-limit kill, `log` is what the call held.

Neither case leaves an artefact at `output`, and a file already there stays untouched. After this change a plain `OSError` of `build` comes only from lines before `subprocess.Popen` is called (ADR-0083 P3 (a) to (e)). The executor confirms this from the code and states it in Result.

This change reuses one existing class. Its documented meaning must then be widened. `CompilerRunError`'s docstring says the error was raised "after creating the compiler process returned and before its return code was known". That stops being exact for a clock read after a normal end, so the docstrings must say it. The values of `timed_out` stay true to their stated meaning, "true when the time limit had passed before the error". This change adds no new public name, no member, no data-plane file and no value of `condition` or `error.kind`, and it binds no row of `correctness.check`. What it means for ADR-0081 decision 4 and ADR-0082 decisions 2 and 4 is left to a later doc task (Follow-ups). It is an engineering choice inside `build`, which ADR-0083 leaves to the code task. It is not an owner-only item under DRIVER §9.

Nothing else changes:
- the start time `started = time.monotonic()` before the `try` (an `OSError` from it stays plain, before the start, ADR-0083 P3 (d));
- the five classes' other sources;
- the note added for an exception that is no `OSError` (T-0253);
- `_communicate`;
- the results and `duration_s` of a normal, failed or timed-out build.

**Why this item now.** STATE has no lock, current task or next task. Every TODO, INTERRUPTED or BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). There was no open PR on 2026-10-17 at `e21d97e`. PLAN P1-1 continues through OD-18 work. This task depends on none of those HQs. None of the blocked tasks touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`. The other open follow-up, the row of the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4), may need a new `error.kind`, which would make it a data-plane or owner question, so it is not taken here.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0255-<slug>`, the PR title with `T-0255`, the trailer `Task: T-0255` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md`: Context P2 and P3, decision 3 ("What would let it be placed"), Consequences "Code". Do not edit it.
- `ARCHITECTURE/decisions/ADR-0082-od18-correctness-check-compiler-run-error-time-limit.md`: decisions 2 and 4. Read only, so that the docstring wording of `timed_out` and `log` stays what those decisions read.
- `hilclaw/clang_build.py` at `0305d7b` or later:
  - the docstring of `CompilerRunError` (lines 99-126);
  - `build` (lines 183-328), especially its docstring paragraph on raised errors (lines 207-241) and the `try` from line 261 to the `CompilerRunError` raise at line 308;
  - `_Held` and `_communicate` (lines 361-385).
- `tests/test_clang_build.py`:
  - the stub bodies `WRITE`, `FAIL`, `SLEEP` (lines 37-40) and the fixtures `stub`, `src`, `out_dir` (lines 78-97);
  - `failing_unlink` (line 355);
  - `test_timeout_kills_the_compiler` (line 289);
  - `failing_communicate` (line 622) and `test_error_after_the_start_is_raised_as_run_error` (line 649), as the model for asserting a `CompilerRunError`.
- `PROCESS/tasks/T-0254-adr-od18-plain-oserror-before-popen.md`: Result. `PROCESS/tasks/T-0253-clang-build-keeps-non-oserror-over-failed-removal.md`: "The change, stated".

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build`.** Make the change as "The change, stated" says:
   - An `OSError` from reading the clock after `_communicate` returned is raised as `CompilerRunError`, `from` that `OSError`, with:
     - `timed_out` equal to `held.timed_out`;
     - `log` equal to `held.decoded()`;
     - `removal_error` set by the existing rule.
   - No artefact is moved to `output`, and the temporary file is removed (or its removal error recorded) as on every other path.
   - An exception from that read that is no `OSError` passes on as T-0253 has it.
   - Every other path keeps its current behaviour, including that an `OSError` from the start-time read before the `try` stays plain.
   - Add no new public name and no comment that restates the code.
3. **Docstrings.**
   - Update `CompilerRunError`'s docstring so that it covers an error from reading the clock after the process ended. Say what `timed_out` and `log` are then, without changing their meaning for the existing sources.
   - Update the sentence of `build`'s docstring on `CompilerRunError` to match.
   - Touch the module docstring only if a sentence in it becomes wrong.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures.
   - Fake the clock only inside the module, for example `monkeypatch.setattr(clang_build, "time", SimpleNamespace(monotonic=fake))`, where `fake` returns the real time on its first call and raises an `OSError` (for example `OSError(errno.EIO, "clock")`) on its second. Do not patch `time.monotonic` globally: `subprocess` and the tests use it.
   - Happy path. With stub `WRITE`, exit 0 and a failing clock read after the end, `build` raises `CompilerRunError`, and:
     - `__cause__` is the fake's error, and `errno` and `strerror` are copied;
     - `timed_out` is false, and `log` is the stub's whole output (use a body that prints a line);
     - `removal_error` is `None`, and there is no `result`;
     - nothing is left in the output directory, and a file already at `output` keeps its bytes.
   - Branch. With stub `FAIL` (exit 1), the same holds, and `log` contains the stub's error line.
   - Branch. With stub `SLEEP` and a short `timeout_s` (as in `test_timeout_kills_the_compiler`), the error is a `CompilerRunError` whose `timed_out` is true and whose `log` contains `before sleep` where the platform reads output before the kill.
   - Branch. With `failing_unlink`, `removal_error` is the removal's error and the error has no note.
   - Negative. When the first clock read (before the `try`) raises `OSError`:
     - `build` raises that `OSError` itself, which is not a `CompilerRunError` or any of the five classes;
     - `Popen` is not called, or `stub.started` is false.
   - Negative. Existing tests that assert `duration_s` keep passing unchanged.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only the stub compilers the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0255-<slug>` with a Draft PR whose title contains `T-0255`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0255`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason, and confirm from the code where a plain `OSError` of `build` can now come from.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/`: ADR-0078 to ADR-0083, Requirements, OpenDecisionProposals and StandardScenarios.
- Telling the source path tests from the output path tests by class or member (ADR-0083 decision 3, ADR-0080 decision 4), and the other lines before the start (ADR-0083 P3 (b) to (e)).
- Any change to `_communicate`'s kill, wait or read; the row of a `CompilerRunError` whose `timed_out` is false.
- Callers of `build`: `hilclaw/harness/verification_build.py`, `timing_build.py` and `hilclaw/standin_profile.py`. Also out: `compiler_version` and the `cpu_standin` operation of `correctness.check` (HQ-0026).

## Follow-ups

- (doc) A record under OD-18 sub-question 18 part (ma) for what this change makes true. A clock error after the end is now a `CompilerRunError`, so ADR-0082 decision 2 (time-limit branch, S8) and decision 4 (the open branch) reach it. The record weighs whether ADR-0082's reading ("the error came afterwards, from the steps by which the call ends a build past its limit") still holds, and lists the sentences of ADR-0081 (K4, decision 4), ADR-0082 and ADR-0083 that become less exact.
- (code) Make `build` tell the source path tests from the output path tests, and both from the other lines before the start (ADR-0083 decision 3).
- (doc) The row of the `CompilerRunError` branch whose `timed_out` is false (ADR-0082 decision 4). It may need a new `error.kind`, which would make it a data-plane or owner question (HQ).

## Result
