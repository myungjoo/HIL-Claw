---
id: T-0266
title: Check `cwd` in `local_run.run` before the start, so a refused `cwd` carries `parameter` "cwd" and a missing or non-directory `cwd` raises an `OSError` with `path_role` "cwd"
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0265]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 70, files: 1}
hq: []
---
## Why

ADR-0060 decision 4 (`ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`, the bullet "What the functions on `main` report, against the rows", line 102) reads `ProgramNotFoundError` or an `OSError` from starting the process of `local_run.run` as row S10, "but for an `OSError` for 'a `cwd` that does not exist' (cited: `hilclaw/local_run.py`), which means S3 and is an error of two rows as well". The same bullet lists "an `OSError` from starting the compiler for a missing working directory (S3) or a compiler that cannot be started (S6)" among the errors that "arise in one class in two rows", and leaves telling them apart to the operation's code ("for example by a change of those functions, binding nothing here").

On `main` (`23acb9d`), `run` hands `cwd` to `subprocess` unchecked. So a `cwd` that does not exist arrives as an `OSError` from the start, in the same classes as other start errors (on POSIX `FileNotFoundError`, which is also what an executable that is missing at the moment of `exec` gives; on native Windows `NotADirectoryError` `[WinError 267]`, with `filename` `None`). A `cwd` of a wrong type or with a NUL character is refused by `subprocess` with a `TypeError` or `ValueError` that carries no `parameter`, unlike the errors of `timeout_s`, `command` and `env` (T-0263, T-0265).

T-0265's Follow-ups name this as the next code task: "Split the `OSError` for a missing `cwd` (S3) from other start errors (S10) in `local_run.run`, and name `cwd` errors; include the pre-start lookup `OSError`".

**The change, stated.** Add one more check before the start, after the `env` check, in the style of T-0265 (a check that refuses with the class `subprocess` would raise) and of T-0259 (an attribute on an `OSError` from a path test the function makes itself):

1. **Type and NUL, `parameter` `"cwd"`.** When `cwd` is not `None`, convert it with `os.fspath` (as `subprocess` does; `str`, `bytes` and `os.PathLike` pass on both platforms) and refuse a NUL character in it. Run this inside `with _parameter("cwd"):`, so every `TypeError` and `ValueError` of this step, including one Python raises inside `os.fspath` or a `__fspath__`, carries `parameter == "cwd"`. The class must be the one a direct `subprocess.run(..., cwd=cwd)` raises for the same value on the platform.
2. **A path test, `path_role` `"cwd"`.** Then test the converted path with `os.stat`:
   - if `os.stat` raises an `OSError`, or the path is not a directory, raise before anything is started an `OSError` whose class (and `errno`; on Windows also `winerror`) is what a direct `subprocess.run(..., cwd=cwd)` raises for that `cwd` on the platform. Planning-time observations: POSIX gives `FileNotFoundError` for a missing path and `NotADirectoryError` for a regular file (from `chdir` in the child, `filename` = the `cwd`); native Windows (Python 3.14.4) gives `NotADirectoryError` with `errno` 20 and `winerror` 267 for both, while `os.stat` on a missing path gives `FileNotFoundError` `[WinError 2]`. Where the class `os.stat` raised already matches, re-raise that same object with a bare `raise`; otherwise raise a new error of the matching class with the `cwd` as `filename`, chained from the `os.stat` error if there is one. How the matching class is produced is the executor's, but the tests below decide it.
   - Every `OSError` that leaves this test carries the attribute `path_role == "cwd"`, set on the object before it leaves `run`.
3. **Nothing else gets the new attribute.** No `OSError` from the start itself (a `cwd` removed between the test and the start, a file the system cannot execute, a directory without search permission that `os.stat` passes), none from the program lookup (`shutil.which`, and `os.getcwd` inside `os.path.abspath` in `_resolve`, which is the "pre-start lookup `OSError`" of the follow-up: it stays as it is on `main`, with neither `parameter` nor `path_role`), and none of the other errors of `run` carries `path_role`. The `OSError` of the `cwd` test carries no `parameter`.

A caller reads them as `getattr(error, "parameter", None)` and `getattr(error, "path_role", None)`. The check order becomes: `timeout_s`, `command` (so `ProgramNotFoundError` still comes first), `env`, `cwd`. `cwd` itself is handed on to `subprocess` as given.

This is an engineering choice inside `run`, which ADR-0060 decision 4 leaves to the code. It adds no module-level public name (the values are plain strings documented in `run`'s docstring), no data-plane member or file and no value of `condition` or `error.kind`. It places no row of `correctness.check`: whether S3 now holds for an `OSError` with `path_role` `"cwd"`, and which row a `TypeError`/`ValueError` with `parameter` `"cwd"` is (a setting, S4, or an argument the operation's own code formed, no row), is a later doc task, after HQ-0027 (Follow-ups). It is not an owner-only item under DRIVER §9.

**Existing tests checked at planning time (`23acb9d`).** In `tests/test_local_run.py`:
- `test_missing_cwd_passes_the_oserror_on` (line 329) asserts `OSError` and that the child did not start; it still passes.
- `test_a_missing_cwd_names_no_parameter` (line 732) asserts `isinstance(error, OSError)` and `not hasattr(error, "parameter")`; it still passes, because the new attribute on the `OSError` is `path_role`, not `parameter`.
- `test_an_error_of_subprocess_names_no_parameter` (line 748) and the `env` tests that pass `cwd=tmp_path` use an existing directory, so the new test passes them through.
- `test_the_parameter_survives_pickling` (line 1031) is a parametrised list that may gain rows.
- `tests/harness/test_timing.py` and `tests/harness/test_verification.py` call `run` only with an existing `cwd` or none, and their docstrings say what `local_run.run` raises "is passed on", which stays true.
- The name `path_role` occurs only in `hilclaw/clang_build.py` and its tests (`grep -rn path_role hilclaw tests`). No test pins the set of public names of `hilclaw.local_run`.

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ (HQ-0021..HQ-0027). PLAN P1-1 continues through the OD-18 work. This task depends on none of those HQs: HQ-0027 blocks the ADR-0088 doc task on `ARCHITECTURE/` files, which this task does not touch. No blocked task touches `hilclaw/local_run.py` or `tests/test_local_run.py`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0266-<slug>`, the PR title with `T-0266`, the trailer `Task: T-0266` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`, decision 4, line 102 only. Do not edit it.
- `hilclaw/local_run.py` at `23acb9d` or later: `run`'s docstring (lines 77-133), the body of `run` (lines 134-152), `_parameter` (lines 239-245), `_resolve` (lines 255-279), `_check_env` and `_env_text` (lines 282-302).
- `tests/test_local_run.py`: the markers `posix_only`/`windows_only` (lines 45-46), `test_missing_cwd_passes_the_oserror_on` (line 329), `raised` (line 606), `IntPath` (line 696), `test_a_missing_cwd_names_no_parameter` (line 732), `refusing` and `test_an_error_of_subprocess_names_no_parameter` (lines 738-761), `directly` (line 802), `test_the_parameter_survives_pickling` (lines 1031-1046).
- `PROCESS/tasks/T-0265-local-run-env-and-argument-parameter.md` "Result", and `PROCESS/tasks/T-0259-clang-build-path-test-role.md` "Why" ("The change, stated"), for the two precedents.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/local_run.py` or `tests/test_local_run.py`, stop and return BLOCKED (open-PR conflict).
2. **`run`.** Make the change as "The change, stated" says:
   - A `TypeError` or `ValueError` from the `cwd` step carries `parameter == "cwd"` and has the class a direct `subprocess.run` raises for the same `cwd`.
   - For a `cwd` that does not exist and a `cwd` that is a regular file, `run` raises before the start an `OSError` of the class (and `errno`; on Windows `winerror`) a direct `subprocess.run` raises for that `cwd`, with `path_role == "cwd"`. No process is started (`subprocess.Popen` and `subprocess.run` are not called).
   - An `OSError` that `os.stat` raises and whose class already matches is the same object after the change (`is`), re-raised with a bare `raise`, with its class, `args`, `errno` and `filename` kept.
   - No other error that `run` raises or passes on has `path_role`, and the `OSError` of the `cwd` test has no `parameter`.
   - The order is `timeout_s`, `command`, `env`, `cwd`. Keep every existing message and the classes of every existing check. Add no new module-level public name. Add no comment that restates the code.
3. **Docstrings.**
   - In `run`'s docstring, state the `cwd` check: what is refused and with which class, that it comes after `env`, that `parameter` `"cwd"` is set on its `TypeError`/`ValueError`, and `path_role` (`"cwd"`) on an `OSError` from the path test, including one `os.stat` itself raises.
   - Correct the sentences that become wrong: the list of what `subprocess` raises that is passed on (a "`cwd` that does not exist" and "what it raises for `cwd`"), and the list of `parameter` values. State that an `OSError` from the start, including one for a `cwd` that changed after the test, carries no `path_role`.
   - Touch the module docstring only if one of its sentences becomes wrong. The docstrings of `RunResult` and `ProgramNotFoundError` do not change.
4. **Tests** in `tests/test_local_run.py`, following D12. Do not test the fixtures or helpers.
   - **Edits to existing tests are allowed only as additions of assertions or parameters**, and only to `test_missing_cwd_passes_the_oserror_on`, `test_a_missing_cwd_names_no_parameter` and `test_the_parameter_survives_pickling`. No existing assertion may be removed or changed, and no existing test may be renamed or deleted. Every other existing test, including those under `tests/harness/`, must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
   - **Happy path.** An existing directory as `str`, as `Path` and as `bytes` still runs the process in it (the child reports that `cwd`); `cwd=None` still inherits.
   - **Branch, refused types and NUL.** `cwd=3`, `cwd=IntPath()`, `cwd="a\0b"` and `cwd=Path("a\0b")` raise the class a direct `subprocess.run` raises for them, with `parameter == "cwd"`; the child did not start.
   - **Branch, the path test.** A missing `cwd`, a missing `cwd` under a missing parent and a regular file as `cwd` raise the class (and `errno`; on Windows `winerror`; on POSIX `filename`) that a direct `subprocess.run` raises for the same `cwd`, with `path_role == "cwd"` and no `parameter`; no `Popen`/`run` call (patch both with `refusing(AssertionError)`) and the path is not created.
   - **Branch, an error `os.stat` raises.** Patch `os.stat` (as `run` reaches it) to raise a `PermissionError` for the `cwd`; the error that leaves `run` has `path_role == "cwd"`, and is the same object if its class is the one `run` keeps (state in Result which applies on each platform).
   - **Branch, order.** A missing program with a missing `cwd` still raises `ProgramNotFoundError` (no `path_role`); a refused `env` with a missing `cwd` raises the `env` error (`parameter == "env"`, no `path_role`).
   - **Negative, nothing else gets `path_role`.** No `path_role` on: `ProgramNotFoundError`; the errors of `timeout_s`, `command` and `env`; an `OSError` from `subprocess.Popen`/`subprocess.run` patched to raise a `FileNotFoundError` with an existing `cwd`, on both wait paths (the case of a `cwd` removed after the test); a file the system cannot execute (POSIX); and an `OSError` from `os.getcwd` inside `os.path.abspath` in `_resolve` (patch it to raise `FileNotFoundError` with a relative program), which also has no `parameter`.
   - **Pickling.** A pickled and loaded `cwd` `TypeError` keeps class, args and `parameter`; a pickled and loaded missing-`cwd` `OSError` keeps class, `errno`, `filename` and `path_role`.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only `sys.executable` and the child scripts the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0266-<slug>` with a Draft PR whose title contains `T-0266`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green (Python 3.11 and 3.14 jobs, coverage gate, test presence);
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0266`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason, the CPython revisions read for the `cwd` handling of `subprocess` (POSIX `_fork_exec`/`chdir` and the `noexec:chdir` filename, Windows `CreateProcess`), and which lines now set `parameter` `"cwd"` and `path_role` `"cwd"`.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any `ARCHITECTURE/` file, in particular the files of T-0264 (ADR-0088, `Requirements.md`, `OpenDecisionProposals.md`, `StandardScenarios.md`), and any record of which row `parameter` `"cwd"` or `path_role` `"cwd"` places.
- Giving the `OSError` of `os.getcwd` inside `os.path.abspath`, or any `OSError` from the start, an attribute; a NUL in the program; a search-permission test of `cwd`.
- `hilclaw/clang_build.py`, `hilclaw/harness/timing.py`, `hilclaw/harness/verification.py` and the `cpu_standin` operation of `correctness.check` (HQ-0026, PLAN P1-1).
- Starting `claude` in any form (D16).

## Follow-ups

- (doc, after HQ-0027) An OD-18 sub-question 18 part (ma) record on what `parameter` `"env"`, `parameter` `"cwd"` and `path_role` `"cwd"` of `local_run.run` make true for `correctness.check` (S3 against S10, S4 against no row), and the pre-start lookup `OSError` that stays without an attribute.

## Result
