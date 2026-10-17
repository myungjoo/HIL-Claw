---
id: T-0269
title: Make `local_run.run` refuse, before the start, an argument that on POSIX `os.fsencode` cannot convert, with `parameter` "command"
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0265, T-0268]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 25, files: 1}
hq: []
---
## Why

T-0265 (PR #166, `f785231`) moved the NUL check of the arguments of `local_run.run` before the start, so that a refused argument carries `parameter == "command"` (ADR-0060 decision 4: a `ValueError` for an argument the operation's own code formed must be told apart from a refused setting). One case is still passed on from `subprocess` with no `parameter`:

- **On POSIX, an argument `os.fsencode` cannot convert**, for example a lone surrogate such as `"a\ud800b"`. `_resolve` accepts it (it is a `str` with no NUL), and `subprocess.Popen` then raises `UnicodeEncodeError` (a `ValueError` subclass) while converting the argument list. That happens after the start of the clock in `run`, outside every `_parameter` block, so the error has no `parameter` and a caller cannot tell it from other errors passed on from `subprocess`.

T-0268 (PR #169, `8aee9ba`) closed the same gap in `clang_build.build` with a private `_check_argument` (`os.fsencode` on POSIX, then the NUL check). Its Result records that on native Windows (Python 3.14.4) a direct `Popen` accepts a lone surrogate in an argument, with and without `cwd`, so nothing may be refused there. This task is the T-0268 follow-up "(code) `local_run.run`: on POSIX, convert each argument with `os.fsencode` before the start". It changes no `ARCHITECTURE/` file and does not depend on HQ-0027 (T-0264, ADR-0088): no record of which row `parameter` `"command"` places is written here.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (executor procedure, naming convention, size cap, test rules, time limit).
- `CLAUDE.md` "테스트 규칙" (D12), "도구 계층 언어 정책" and "코멘트 최소화".
- `hilclaw/local_run.py` (whole file, 355 lines): `run` and its docstring (lines 79-175), `_parameter`, `_resolve` (lines 282-306), `_env_text`, `_check_cwd`.
- `hilclaw/clang_build.py` lines 505-570 (`_checked_flags`, `_check_argument`, `_resolve`) — the pattern to follow. Read only; do not edit and do not import from it.
- `tests/test_local_run.py` lines 40-80 (fixtures `child`, `QUIET`, `TIMEOUT`, `posix_only`, `windows_only`), lines 600-620 (`raised`), lines 795-880 (`wait_path`, `directly`, and the NUL argument tests `test_a_nul_in_an_argument_*`), lines 1040-1060 (`test_the_parameter_survives_pickling`), and lines 1095-1120 (`REFUSED_CWDS` with its POSIX-only lone surrogate row, as an example of the parametrisation).
- `PROCESS/tasks/T-0268-clang-build-argument-checks-before-start.md` (Acceptance Criteria and Result) and `PROCESS/tasks/T-0265-local-run-env-and-argument-parameter.md` (Acceptance Criteria 2 and Result) for the conventions this task continues.

## Acceptance Criteria

1. **Check.** In `_resolve`, for each argument after the program, after the existing `str` type check and before the existing NUL check: on POSIX (`os.name != "nt"`, the test the module already uses) the argument is converted with `os.fsencode`; a `UnicodeEncodeError` from that conversion is passed on as the same object (no new exception, no rewrapping, no message change). Because it is raised inside the existing `with _parameter("command"):` and is a `ValueError`, it carries `parameter == "command"`. Nothing is started and the program lookup (`shutil.which`) is not reached. The argument is handed on unchanged (the converted bytes are discarded).
2. **Same class as `subprocess`.** The class raised is the class a direct `Popen` raises for the same argument on the platform (`UnicodeEncodeError` on POSIX). On native Windows a lone surrogate in an argument stays accepted and reaches the process exactly as on `main`. For an argument that holds both a NUL and an unencodable character, state in the Result which error `run` now gives and which a direct `Popen` gives on POSIX (CI); they must agree.
3. **Unchanged elsewhere.** The handling of the program (the first element, including a NUL or a lone surrogate in it) is unchanged. Classes, messages and order of all other checks are unchanged: `timeout_s`, then `command` (type checks, then per argument: type, the new conversion, NUL), then `ProgramNotFoundError`, then `env`, then `cwd`. An argument that `os.fsencode` converts on POSIX (for example one with a surrogate-escaped byte such as `"\udc80"` under a UTF-8 file system encoding — check `sys.getfilesystemencoding()` and `sys.getfilesystemencodeerrors()` in the test and skip it otherwise) is still accepted and reaches the process. No new public name, no new import of another `hilclaw` module, no change to `RunResult` or `ProgramNotFoundError`.
4. **Docstring.** The docstring of `run` lists, among the `ValueError`s raised before anything is started, an argument that on POSIX `os.fsencode` cannot convert (as `UnicodeEncodeError`), and the `parameter` paragraph says that it carries `"command"`. Keep it accurate for both platforms (on Windows such an argument is not refused). No other comment beyond what CLAUDE.md "코멘트 최소화" allows.
5. **Tests (D12)**, in `tests/test_local_run.py` only, all new:
   - negative: on POSIX (`posix_only`) an argument with a lone surrogate raises `UnicodeEncodeError` with `parameter == "command"`, `child.started` is false, for both wait paths (`platform_wait` true/false via `wait_path`); its class equals the class of `directly(...)` for the same command;
   - branch: the order — a bad `timeout_s` with such an argument gives `"timeout_s"`; such an argument with a missing program gives `UnicodeEncodeError` with `"command"` (before the lookup); such an argument with a bad `env` gives `"command"`; an argument that is not a `str` before it gives `TypeError`;
   - happy: on POSIX an argument `os.fsencode` converts (criterion 3) reaches the process unchanged; on native Windows (`windows_only`) a lone surrogate argument is accepted and the run completes (compare with `directly(...)` as T-0268 did);
   - error: an argument with both a NUL and a lone surrogate gives the class of criterion 2 on POSIX;
   - pickling: the new error keeps `parameter` through `pickle` (new test or a new row of `test_the_parameter_survives_pickling`, `posix_only`).
   **Existing tests:** none may be edited or deleted except adding rows to `test_the_parameter_survives_pickling`. If an existing test turns out to pin the old behaviour, stop and report it (BLOCKED, requirement-unclear) rather than editing it.
6. Line and function coverage of `hilclaw/` stay ≥ 80% (CI gate); `ruff check` and `ruff format --check` clean; full `pytest` passes locally; CI green on both Python versions of the matrix.
7. Size: ≤ 300 LOC changed and ≤ 5 files excluding tests (expected: `hilclaw/local_run.py` only, about +5 lines of code plus docstring).
8. The Result states the language (Python — the module's language) and the finding of criterion 2 for the NUL-plus-surrogate argument.

## Out of Scope

- The program (first element of `command`) and how a NUL or an unencodable character in it is reported on each platform.
- `hilclaw/clang_build.py`, `hilclaw/harness/`, and the `cpu_standin` operation of `correctness.check` (HQ-0026).
- Any `ARCHITECTURE/` file, in particular the files of T-0264 (ADR-0088, `Requirements.md`, `OpenDecisionProposals.md`, `StandardScenarios.md`) and any OD-18 (ma) record of what this check makes true; that is a doc task after HQ-0027 is answered.
- Starting `claude` in any form (D16).

## Follow-ups

- (doc, after HQ-0027) The OD-18 sub-question 18 (ma) record: an unencodable argument of `local_run.run` now carries `parameter` `"command"` before the start, together with the T-0265..T-0268 follow-ups.

## Result
