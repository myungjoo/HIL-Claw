---
id: T-0285
title: Add `hilclaw/check_build.py`, which places a build of the verification executable, returned or raised, in the row the accepted OD-18 records give it
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: []
touchesFiles: [hilclaw/check_build.py, tests/test_check_build.py]
estimatedSize: {loc: 150, files: 2}   # tests excluded from the cap (DRIVER §5, D4)
hq: []
---
## Why

PLAN P1-1 (FR-10 tool contracts) is open. The operation of `cpu_standin` for `correctness.check` is not written yet. Each record from ADR-0079 to ADR-0094 ends its Consequences with the same line: the operation, "when it is written", answers a given error of `clang_build.build` in a given row. Nothing in `hilclaw/` applies those rows today. The only code that reads `path_role`, `parameter`, `timed_out` or `returncode` of a build error is `clang_build.py` itself, which raises them.

This task writes the one pure part of that operation that every accepted record already fixes: given what one call of `hilclaw.harness.verification_build.build_verification_executable` returned or raised, say which answer of ADR-0060 decision 4 it is. The answer is one of these:

- a backend kind of `hilclaw/check_failure.py`;
- a value of `condition` of form (B);
- an ok build;
- "not placed", for an error that a record leaves with no row or keeps open. The operation will let such an error pass, and the landed rules then answer `operation_answer_invalid` (ADR-0045 decisions 4 and 5).

This lands ahead of the operation, as `hilclaw/check_failure.py` and `hilclaw/check_operation.py` did ahead of the tool function.

Scope:

- **No rule is decided here.** Every row below is cited from an accepted record. Where two readings seem possible, stop and report; do not choose (CLAUDE.md "미결은 발명하지 않는다").
- No data-plane value is added (no kind, no `condition`, no member). No ARCHITECTURE file changes, so no ADR, no OD status change and no coverage re-check are needed.
- No owner-only item is touched (DRIVER §9).
- No HQ is involved:
  - The log hand-over (ADR-0078, HQ-0026) is out of scope.
  - `local_run.run` and S10 (HQ-0027) are out of scope.
  - The env-key refusal of PR #179 (HQ-0028) does not change any row here. An `env` refused by that check would carry `parameter` "env", which is S4 already.
- The tests build exception and `BuildResult` objects directly. They need no compiler, `claude`, container or board (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3 step 5 and §5 (executor procedure, naming, size cap, D12 test rules).
- `CLAUDE.md`, "테스트 규칙" and "코멘트 최소화".
- `hilclaw/clang_build.py`:
  - lines 43-195: `BuildResult`, `CompilerNotFoundError`, and the five error classes `CompilerNotStartedError`, `CompilerRunError`, `ArtefactNotPlacedError`, `ArtefactNotCheckedError` and `TemporaryNotRemovedError`, with their constructors;
  - the docstring of `build`, from line 196 to about line 305: `parameter`, `path_role`, and which class is raised where.
  - Read only. This file is touched by open PR #179.
- `hilclaw/harness/verification_build.py` lines 41-90 (`build_verification_executable`: what it raises itself and what it passes on).
- `hilclaw/check_failure.py` lines 1-125 (the eight backend kinds and their constants).
- `hilclaw/check_result.py` lines 50-65 (`CONDITIONS`, which holds `"build_time_limit"` and `"build_exit_status"`).
- The "Decision" sections of these records under `ARCHITECTURE/decisions/`. These sections are the authority for every row of the acceptance criteria:
  - ADR-0045 lines 24-90 (decisions 1, 4 and 5: a request to end; what happens to an error the operation lets pass);
  - ADR-0060 lines 69-104 (decision 4: the table of S3 to S10, the reading of a `BuildResult`, `CompilerNotFoundError` → S6, `NotADirectoryError` of the output path → S3);
  - ADR-0079 lines 26-57 (`ArtefactNotPlacedError` → S9; `TemporaryNotRemovedError` → the row of the carried build; start errors → S6);
  - ADR-0080 lines 28-53 (`CompilerNotStartedError` → S6; `ArtefactNotCheckedError` → S9);
  - ADR-0082 lines 28-57 (`CompilerRunError` with `timed_out` true → S8; the other branch open);
  - ADR-0083 lines 33-67 (a request to end; a plain `OSError` stays without a row);
  - ADR-0084 lines 28-69 (a failed clock read after a kill → S8);
  - ADR-0085 lines 25-66 (`timed_out` false with a `returncode`: non-zero → S7, 0 → S9; `returncode` `None` open);
  - ADR-0086 lines 27-76 (`path_role` "source" → S5, "output" → S3; an unroled `OSError` open, except `NotADirectoryError` → S3);
  - ADR-0087 lines 26-69 (`TypeError` by `parameter`: settings → S4, "sources"/"output" no row, unnamed open);
  - ADR-0089 lines 26-76 ("env" → S4; "cwd" no row; "kernel_sources" no row; unnamed `ValueError` open);
  - ADR-0090 lines 26-64 (`ValueError` naming the four settings → S4);
  - ADR-0091 lines 26-65 (`ValueError` naming "sources"/"output"/"kernel_sources" → no row);
  - ADR-0092 lines 26-63 and ADR-0093 lines 25-59 (`ValueError`/`TypeError` with "output" → no row);
  - ADR-0094 lines 26-56 (the no-`items` `TypeError` with "env" → S4).

## Acceptance Criteria

1. **New module `hilclaw/check_build.py`** (code mode, Python; give the language reason in the commit body). It imports `hilclaw.clang_build`, `hilclaw.check_failure` and `hilclaw.check_result` and nothing that starts a process. It has three public names:
   - `BUILT`: a module constant that means "an ok build, go on to start the executable". It is not `None`, and it equals no value of `check_failure` kinds and no value of `check_result.CONDITIONS`.
   - `read_build(result)`
   - `place_error(error)`

   The module docstring (boilerplate, may be long) lists the rows below, each with the record and decision it comes from. It says that `None` means "not placed: let it pass", and that the module neither hands a log over nor writes a message. Otherwise keep comments to the minimum (CLAUDE.md).
2. **`read_build(result)`**, for a `clang_build.BuildResult`, applies ADR-0060 decision 4's reading of a build, in this order:
   - `ok` true → `BUILT`;
   - `timed_out` true → `"build_time_limit"` (S8);
   - a `returncode` that is an `int` other than 0 → `"build_exit_status"` (S7). Negative values count (a signal on POSIX).
   - `returncode` 0 → `check_failure.KIND_BUILD_OUTPUT_MISSING` (S9);
   - anything else (`ok` and `timed_out` false with `returncode` `None`, a state the docstring does not produce) → `None`.

   A value whose type is not exactly `BuildResult` raises `TypeError` that names the type and not the value.
3. **`place_error(error)`** applies these tests in this order and returns the first match:
   1. Not an instance of `Exception` (for example `KeyboardInterrupt`, `SystemExit`) → `None`. A request to end is not placed (ADR-0045 decisions 1 and 5; ADR-0083 decision 2).
   2. `TemporaryNotRemovedError` → `read_build(error.result)`. `BUILT` is a possible answer (ADR-0079 decision 3).
   3. `ArtefactNotPlacedError` or `ArtefactNotCheckedError` → `KIND_BUILD_OUTPUT_MISSING`, with or without `removal_error` (ADR-0079 decision 2; ADR-0080 decision 3).
   4. `CompilerNotStartedError` → `KIND_COMPILER_UNAVAILABLE`, with or without `removal_error` (ADR-0079 decision 4; ADR-0080 decision 2).
   5. `CompilerRunError`, with or without `removal_error`:
      - `timed_out` true → `"build_time_limit"` (ADR-0082 decision 2; ADR-0084 decision 2);
      - otherwise, `returncode` `None` → `None` (ADR-0082 decision 4);
      - `returncode` 0 → `KIND_BUILD_OUTPUT_MISSING` (ADR-0085 decision 5);
      - any other `int` → `"build_exit_status"` (ADR-0085 decision 3).
   6. `CompilerNotFoundError` → `KIND_COMPILER_UNAVAILABLE` (ADR-0060 decision 4).
   7. Any other `OSError`, read as `getattr(error, "path_role", None)`:
      - `"source"` → `KIND_BUILD_INPUT_MISSING` (ADR-0086 decision 3);
      - `"output"` → `KIND_BUILD_DIRECTORY_UNUSABLE` (ADR-0086 decision 4);
      - no `path_role` and an instance of `NotADirectoryError` → `KIND_BUILD_DIRECTORY_UNUSABLE` (ADR-0060 decision 4; ADR-0086 decision 6);
      - every other case, an unknown role included → `None` (ADR-0083 decision 3; ADR-0086 decision 6).
   8. A `TypeError` or `ValueError` (subclasses included, for example `UnicodeEncodeError`), read as `getattr(error, "parameter", None)`:
      - `"timeout_s"`, `"flags"`, `"trailing_flags"`, `"compiler"` or `"env"` → `KIND_SETTINGS_REFUSED` (ADR-0087 decision 3; ADR-0089 decision 2; ADR-0090 decision 2; ADR-0094 decision 2);
      - every other value, `None` included → `None`. This covers `"sources"`, `"output"`, `"cwd"`, `"kernel_sources"` and an unknown string (ADR-0087 decisions 4 and 5; ADR-0089 decisions 3 to 5; ADR-0091 decisions 2 and 3; ADR-0092 decision 2; ADR-0093 decision 2).
   9. Anything else → `None`.

   The function reads only the class and the documented members named above. It does not read the message, `args`, the exception chain, `errno` or private state, and it does not change the object.
4. **Tests in `tests/test_check_build.py`** (new file; D12 ①-④). Build every object directly, constructing the error classes through their public constructors as `clang_build.py` defines them. Start no process. Cover:
   - **Happy:** every row of criteria 2 and 3, each with its exact return value. For `TemporaryNotRemovedError`, cover all five outcomes of the carried build, `BUILT` among them.
   - **Branch:** the order of the tests:
     - a `CompilerRunError` with `timed_out` true and a `returncode` set gives `"build_time_limit"`;
     - a `NotADirectoryError` with `path_role` "source" gives S5, not S3;
     - each of the five classes gives its own row even when it is given a `path_role` attribute;
     - `removal_error` set and not set give the same answer for every class that has one;
     - a negative `returncode` gives S7 in both functions.
   - **Negative:**
     - `read_build` with a tuple of the same fields, with `None` and with a `str` raises `TypeError` whose message does not contain the value;
     - `place_error` of a `TemporaryNotRemovedError` whose `result` is not a `BuildResult` raises that `TypeError`;
     - `place_error` returns `None` for an unnamed `TypeError` and an unnamed `ValueError`, for a plain `OSError` and a `FileNotFoundError` without `path_role`, for a `PermissionError` with `path_role` "cwd", for `parameter` "cwd", "kernel_sources", "sources", "output" and `"bogus"`, for `RuntimeError`, `LookupError`, `KeyboardInterrupt` and `SystemExit`, and for a `UnicodeEncodeError` with `parameter` "output";
     - `UnicodeEncodeError` with `parameter` "flags" gives S4.
   - **Purity:** for one object of each class, the object's `__dict__` and `args` are equal before and after the call.
   - **Values:** every value either function returns is `None`, `BUILT`, a member of `check_result.CONDITIONS[:2]`, or a kind listed in `check_failure`. `BUILT` is none of those.
5. Line and function coverage of `hilclaw/` stay at or above 80 %. `pytest` and `ruff` pass locally and in CI, and the CI test-presence check passes.
6. Only the two files of `touchesFiles` change. In particular, nothing in `hilclaw/clang_build.py`, `tests/test_clang_build.py` (open PR #179), `ARCHITECTURE/`, `PROCESS/` or any settings file changes. If an existing test fails because of the new module, stop and report; do not edit it.
7. If a record seems to give one error two rows, or a row seems to be missing from this list, stop and report it as BLOCKED (requirement unclear). Do not choose.
8. Code mode (CLAUDE.md A-13): Draft PR titled with `T-0285`, reviewer cycle (dev-code-review), CI green, squash-merge with `Task: T-0285` as the last line of the PR body. No `claude` is started (D16).

## Out of Scope

- The operation of `cpu_standin` for `correctness.check` itself: calling the reader and the build, starting the executable, removing the build directory, and raising the kinds as `ToolFailure`s.
- The compiler's log: which answers hand `result.log` or `log` to the keeper (ADR-0078; T-0243 is BLOCKED on HQ-0026).
- The messages of the six kinds (ADR-0060 decision 5).
- Errors of `local_run.run` and S10 `executable_unstartable` (HQ-0027).
- `compiler_version` and the timing build of `sim.run` / `board.run` (⑲; HQ-0021).
- Any change to `clang_build.py`, any open entry of ⑱ (마), and any ADR, OD-register or OpenDecisionProposals edit.

## Follow-ups

- Code, later: the operation of `cpu_standin` for `correctness.check`, which uses `read_build` / `place_error` once the log keeper (T-0243, HQ-0026) can land.
- If a later record places one of the open entries, add its row here in the same task as the record's code follow-up.

## Result
