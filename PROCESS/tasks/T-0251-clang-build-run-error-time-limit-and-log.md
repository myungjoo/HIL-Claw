---
id: T-0251
title: Make `CompilerRunError` of `clang_build.build` state whether the time limit had passed and carry the output read so far
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-1, FR-10, OD-18]
dependsOn: [T-0249, T-0250]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 60, files: 1}
hq: []
---
## Why

ADR-0081 (T-0250, `d2a2c03`) decision 2 leaves the row of `CompilerRunError` for `correctness.check` open under OD-18 ⑱ (마). It names what would let a later record place it. The first item is "A code change of `clang_build.build` that tells the time-limit branch apart, by a class or by a member of the error, and keeps the output read so far." Its Consequences say: "A code task may tell the time-limit branch apart and keep the output read so far (decision 2)." T-0250's Result lists this change as its first follow-up. This task makes that change.

Today, at `d2a2c03`, in `hilclaw/clang_build.py`:
- `_communicate` kills the process when `process.communicate(timeout=...)` raises `subprocess.TimeoutExpired`. Then it reads again (Windows) or waits (elsewhere), and returns `(None, expired.stdout or b"")`. On any other exception, it kills the process and re-raises. All of this runs inside `with process:`.
- `build` turns any `OSError` that leaves `_communicate` into `CompilerRunError(run_error, removal_error)`. The class has no `result` and keeps no output (its docstring says "the output read so far is not kept"). Nothing in it says whether the time limit had passed.
- So an `OSError` from the kill, the second read, the wait, or the exit of `with process:` after the time limit had passed looks the same as an `OSError` from reading the pipe of a compiler that is still within its limit (ADR-0081 K2). The output that `TimeoutExpired` carries on POSIX is reachable only through the implicit `__context__` chain, and ADR-0081 refuses to rest an answer on that chain.

**The change, stated.** `CompilerRunError` gets two public members. Set both in `build` from what `_communicate` itself observed, never from `__context__`:
- `timed_out` (`bool`): true exactly when `process.communicate(timeout=timeout_s)` raised `TimeoutExpired` before the `OSError`. That covers an `OSError` from the kill, from the follow-up `communicate()` or `wait()`, and from the exit of `with process:` after the time-limit branch. It is false for an `OSError` from the first `communicate`, from the kill in the other branch, and from the `with process:` exit after a normal `communicate`.
- `log` (`str | None`): the output that `build` holds when the error is raised, decoded as `BuildResult.log` is (UTF-8, invalid bytes replaced). In the time-limit branch this is the `output` of the `TimeoutExpired`, plus anything the follow-up read returned. It is `None` when `build` holds no output: the branch that is not the time limit, a `TimeoutExpired` without output (Windows, or nothing read yet), or a follow-up read that failed. The docstring says that `None` does not mean the compiler wrote nothing. Do not read private attributes of `subprocess.Popen` to recover more.

ADR-0081 allows "a class or a member". This task picks members. They keep the class hierarchy of ADR-0081 K3 unchanged, so `except CompilerRunError` and the earlier records' reading of the class still hold. If the executor finds a concrete reason that members cannot work, stop and return BLOCKED (`requirement-unclear`) with the reason. Do not switch to a subclass silently.

This is the Python API of a layer-2 tool, not the data plane: no `STATE`/spec/eval/artifacts schema, no `condition` or `error.kind` value. It does not place the row; that is a later record (T-0250 Follow-ups, the doc task).

**Why this item now.** STATE has no lock and no current or next task, and no task file is TODO or INTERRUPTED. There is no open PR (checked 2026-10-17 at `bcbe396`). PLAN P1-1 continues through OD-18 work. Its `profiler.collect` part waits on HQ-0025, and ADR-0078 slices 1 to 3 wait on HQ-0026 (T-0243). This change depends on neither. The doc follow-up of T-0250 depends on this change. The other code follow-up (K4 (ii), the removal error raised in place of an exception that is no `OSError`) is independent and is the candidate after this one.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (line 72: executor procedure, resume rule, time limit 2h30) and §5 (lines 86-114: task format, naming `claude/T-0251-<slug>`, the trailer `Task: T-0251`, the PR body's last line, size cap, D12 test rules).
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0081-od18-correctness-check-compiler-run-error.md`: Context K1 to K4 (lines 19-23), decision 2 (lines 32-40), decision 3 (lines 42-45), Consequences (lines 82-93). Do not edit it.
- `hilclaw/clang_build.py` at `d2a2c03` or later: the module docstring, `_CopiedOSError`, `_UnendedBuildError`, `CompilerNotStartedError`, `CompilerRunError` (lines 64-110), `build` (lines 166-300), `_communicate` (lines 332-347).
- `tests/test_clang_build.py`: the `stub` fixture (line 78) and its scripts (`SLEEP`, `WRITE`), `test_timeout_kills_the_compiler` (line 288), the `failing_communicate` fixture and the run-error tests (lines 620-760), `test_run_error_class`, `test_run_error_survives_pickling` and the pickling parametrization (lines 807-865).
- `PROCESS/tasks/T-0249-clang-build-tells-run-errors-apart.md`: Result (how the kill-branch test was made safe, the 30 s wait of a failing kill, the Windows pickling fix).
- CPython `Lib/subprocess.py` of the installed Python (read only, do not import-and-run it for this): `Popen.communicate`, `_check_timeout` and `TimeoutExpired`. Check what `output` holds on POSIX and on Windows.

## Acceptance Criteria

1. **Members.** `CompilerRunError` has `timed_out` and `log` as stated in Why. They have defaults (`False` and `None`), so `CompilerRunError(error)` and `CompilerRunError(error, removal_error)` still work. `CompilerNotStartedError` and the three after-the-end classes are unchanged in members and behaviour. The class hierarchy is unchanged (ADR-0081 K3).
2. **`build`.** The members are set from state that `_communicate` returns or records, for example a flag and the bytes held when the `OSError` left it. They are not set from `__context__` or `__cause__`. Nothing else changes: the existing exception chaining (`raise ... from run_error`), `removal_error`, the removal in `finally`, the results of a normal or timed-out build, and the `KeyboardInterrupt` path.
3. **Docstrings.** The class docstring and the `build` docstring say what the two members mean. They replace "the output read so far is not kept" with what is kept and when `log` is `None`. They stay within the style of the neighbouring docstrings. Add no other comments ("코멘트 최소화").
4. **Pickling.** A `CompilerRunError` with `timed_out=True` and a non-`None` `log`, and one with the defaults, survive `pickle` round trips with the members intact. The existing pickling tests still pass on Windows and POSIX.
5. **Tests** (D12: happy, error, branch and negative cases; every public function of the touched module stays covered; coverage of `hilclaw/` stays at or above 80 % line and function). Use the stub compiler and monkeypatching only. At least:
   - time-limit branch, the kill fails: `timed_out is True`; on POSIX, `log` holds what the stub wrote before sleeping; make sure no stub process outlives the test (see T-0249's Result);
   - time-limit branch, the kill succeeds and the follow-up `communicate()` (Windows) or `wait()` (elsewhere) fails: `timed_out is True`. Patch the call this platform takes, or both;
   - an `OSError` from the exit of `with process:` after the time-limit branch: `timed_out is True`. After a normal `communicate`: `timed_out is False`;
   - the first `communicate` fails (the existing `failing_communicate` tests): `timed_out is False`, `log is None`;
   - the kill fails after a failed first `communicate`: `timed_out is False`;
   - a `removal_error` together with `timed_out=True`;
   - a `TimeoutExpired` without output gives `log is None`, not `""`;
   - the defaults of a directly constructed `CompilerRunError`.
   Platform-specific assertions are skipped or parametrized by platform, never left to fail on one OS.
6. **Gates.** `pytest`, `ruff check` and `ruff format --check` pass locally and in CI. No new dependency. The language is Python (the module's language); record that in one line in the commit body (CLAUDE.md language policy).
7. **D16.** No step starts `claude` in any form. Only the test stub compiler and, where the existing tests already use it, a real `clang` if present are run.
8. **Code mode** per CLAUDE.md A-13: branch `claude/T-0251-<slug>`, Draft PR whose title contains `T-0251` and whose body's last line is `Task: T-0251`, reviewer cycle to Approve within 7 rounds, CI green, squash-merge with `gh pr merge --squash --body`, delete the branch.
9. Size within the DRIVER §5 caps (≤ 300 changed lines excluding tests, ≤ 5 files).

## Out of Scope

- Any `ARCHITECTURE/` edit, any ADR, and placing the row of `CompilerRunError`. That is the doc follow-up (a record that weighs S8 with its log for the time-limit branch).
- Telling apart the removal error raised in place of an exception that is no `OSError` (ADR-0081 K4 (ii)). That is a separate code task.
- Keeping output in the branch that is not the time limit by reading private `Popen` state; killing the compiler's children; any change to `compiler_version`, `build_verification_executable`, the `cpu_standin` operation or `local_run`.
- A new exception class, or any change to `BuildResult`.

## Follow-ups

- (doc) A record that places `CompilerRunError` for `correctness.check` now that the time-limit branch and its output are stated (ADR-0081 decision 2, first item). The other branch still needs the record that ADR-0081 decision 2 names second.
- (code) Tell apart the removal error raised in place of an exception that is no `OSError` (ADR-0081 K4 (ii)).

## Result
