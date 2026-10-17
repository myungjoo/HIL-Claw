---
id: T-0267
title: Check `env` and `cwd` in `clang_build.build` before the start, so a refused `env` carries `parameter` "env" and a refused `cwd` carries `parameter` "cwd"; a missing `cwd` stays a `CompilerNotStartedError`
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0261, T-0265, T-0266]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 80, files: 1}   # non-test: about 40-60 lines of checks and helpers in clang_build.py plus docstring sentences; tests outside the cap (D4)
hq: []
---
## Why

ADR-0087 (`ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`) placed every `TypeError` of `clang_build.build` that carries `parameter` (T-0261). It left one kind open: a `TypeError` "from `subprocess.Popen` or later (for example a `cwd` or an `env` that cannot be handed over)" carries no `parameter` (T4, line 22), and "for it the class is still of two rows — an `env` is a setting (S4), a `cwd` is the operation's own (cited: ADR-0060 decision 3)" (decision 5, line 53). Its open list (line 68) names it again, together with "whatever `clang_build.build` passes on from `subprocess` beyond the `OSError` its docstring names".

On `main` (`d7046d2`), `build` hands `cwd` and `env` to `subprocess.Popen` unchecked (`hilclaw/clang_build.py`, the `Popen` call in `build`). A `cwd` or `env` of a wrong type, or with a NUL character, or an `env` key with `=` after its first character, is refused by `subprocess` with a `TypeError` or `ValueError` that carries no `parameter`, after `time.monotonic()` was read and the temporary name formed. `hilclaw/local_run.py` already checks both before the start (T-0265 `_check_env`, T-0266 `_check_cwd`), so the two modules that start processes for the first case differ here. This task is the `clang_build` side of T-0262's Follow-ups ("the same kind of split") for `env` and `cwd`.

**The change, stated.** In `build`, after the `compiler` step and before the temporary name, the clock read and the start, add two checks in the style of T-0265 and T-0266:

1. **`env`, `parameter` `"env"`.** Inside a context that sets `parameter = "env"` on every `TypeError` and `ValueError` of this step: when `env` has no `items` attribute, do nothing (`None` and every non-mapping are left to `subprocess`, class and `parameter`-less behaviour unchanged). Otherwise iterate `env.items()` once; per entry convert key and value as `subprocess` does on the platform (`os.fsencode` on POSIX; a `str` check raising `TypeError` on Windows), refuse a NUL character in either (`ValueError`), then refuse `=` after the first character of the key (`ValueError`). The class of each refusal must be what a direct `subprocess.Popen` with the same arguments `build` uses raises for that single defect on the platform. Error messages may show the key, never the value. `env` is handed on unchanged.
2. **`cwd`, `parameter` `"cwd"`.** Inside a context that sets `parameter = "cwd"` on every `TypeError` and `ValueError` of this step: when `cwd` is not `None`, convert it as `subprocess` does (`os.fsdecode` on Windows, `os.fsencode` on POSIX) and refuse a NUL character in it (`ValueError`). The class must be the one a direct `subprocess.Popen(..., cwd=cwd)` raises for the same value on the platform (T-0266's Result: `UnicodeEncodeError`, a `ValueError` subclass, for a lone surrogate on POSIX). `cwd` is handed on unchanged.
3. **No path test of `cwd`.** Unlike T-0266, `build` does **not** test whether `cwd` exists or is a directory. A missing `cwd` must still fail at creating the compiler process and be raised as `CompilerNotStartedError`, as ADR-0079 decision 4 and ADR-0080 decision 2 placed it (S6) and as the existing test `test_missing_working_directory_is_a_failed_start` asserts. No error of `build` gains `path_role` `"cwd"`.
4. **Only these two steps tag a `ValueError`.** The existing `_parameter` of `clang_build` tags `TypeError` only, and the existing tests assert that the `ValueError`s of `timeout_s`, `compiler` and `flags` carry no `parameter` (`test_other_errors_before_the_start_have_no_parameter`). Keep that: the `env` and `cwd` steps tag `TypeError` and `ValueError`; the six existing steps keep tagging `TypeError` only. How this is done (a second private context manager, or a parameter of the existing one) is the executor's.
5. **No sharing with `local_run`.** Do not import private names from `hilclaw.local_run` and do not add a shared module (the shared-helper move T-0225 is blocked on HQ-0022). Small private helpers in `clang_build.py` are expected.

The check order becomes `timeout_s`, `flags`, `trailing_flags`, `sources`, `output` (its path test), `compiler` (so `CompilerNotFoundError` still comes before `env` and `cwd`), `env`, `cwd`.

This is an engineering choice inside `build`, which ADR-0060 decision 4 and ADR-0087 decision 5 leave to the code ("by a change of those functions"). It adds no module-level public name (the two values are plain strings documented in `build`'s docstring), no data-plane member or file and no value of `condition` or `error.kind`. It places no row of `correctness.check`: whether `parameter` `"env"` of `build` is S4 and `"cwd"` is no row is a later doc task, after HQ-0027 (Follow-ups). It is not an owner-only item under DRIVER §9.

**Existing tests checked at planning time (`d7046d2`)**, in `tests/test_clang_build.py`:
- `test_cwd_and_env_reach_the_process` (line 167), `test_environment_is_inherited_by_default` (line 185) and `test_relative_paths_do_not_depend_on_cwd` (line 193) pass a `str`-keyed, `str`-valued `env` and an existing `cwd`; they still pass.
- `test_missing_working_directory_is_a_failed_start` (line 587) must still pass unchanged (point 3).
- `test_other_errors_before_the_start_have_no_parameter` (line 1829) still passes (point 4).
- `test_type_error_from_creating_the_process_has_no_parameter` (line 1846) patches `Popen` with no `env` or `cwd`; it still passes.
- `test_type_errors_keep_their_parameter_through_pickling` (line 1884) is a parametrised list that may gain rows.
- `tests/harness/` callers through `timing_build.py` and `verification_build.py` hand `cwd`/`env` through and state that what `build` raises is passed on unchanged, which stays true.

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every non-DONE task file is BLOCKED on an open HQ (HQ-0021..HQ-0027); the follow-up of T-0266 is a doc task that waits on HQ-0027. PLAN P1-1 continues through the OD-18 work. This task depends on none of those HQs and touches no file of a BLOCKED task (T-0243 touches `hilclaw/layout.py` and `hilclaw/build_log.py`; the doc tasks touch `ARCHITECTURE/`).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0267-<slug>`, the PR title with `T-0267`, the trailer `Task: T-0267` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`, lines 22, 53 and 68 only; `ARCHITECTURE/decisions/ADR-0079-od18-correctness-check-build-errors-told-apart.md`, lines 48-49 only (why a missing working directory is S6). Do not edit either.
- `hilclaw/clang_build.py` at `d7046d2` or later: the module docstring (lines 1-23), `build` (lines 195-373, docstring and body), `_parameter` (lines 433-439).
- `hilclaw/local_run.py` at `d7046d2`: `_parameter`, `_check_env`, `_env_text`, `_check_cwd` (lines 267-356), as the precedent to mirror (not to import).
- `tests/test_clang_build.py`: fixtures `stub`, `src`, `out_dir` and helper `names` (lines 79-111), `failing_start` (line 526), and the tests listed under "Existing tests" above.
- `PROCESS/tasks/T-0265-local-run-env-and-argument-parameter.md` and `PROCESS/tasks/T-0266-local-run-cwd-checks-before-start.md`, "Result" only (platform behaviour of `subprocess` for `env` and `cwd`, the CPython revisions read).

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build`.** Make the change as "The change, stated" says:
   - A `TypeError` or `ValueError` from the `env` step carries `parameter == "env"`, one from the `cwd` step carries `parameter == "cwd"`, and each has the class a direct `subprocess.Popen` raises for the same single defect, with the other arguments `build` uses.
   - For each such refusal no process is started (`subprocess.Popen` is not called), no temporary file exists in the output directory, and an artefact already at `output` is untouched.
   - A missing `cwd` and a `cwd` that is a regular file still raise `CompilerNotStartedError` with an `OSError` cause, and carry neither `parameter` nor `path_role`.
   - The order is as stated: a missing compiler with a refused `env` raises `CompilerNotFoundError`; a refused `env` with a refused `cwd` raises the `env` error.
   - Keep every existing message, class and check. Add no module-level public name. Add no comment that restates the code.
3. **Docstrings.** In `build`'s docstring: state the `env` and `cwd` checks (what is refused, with which class, that they come after `compiler` and before anything is started), add `"env"` and `"cwd"` to the list of `parameter` values and say that for these two steps `parameter` is set on a `ValueError` as well as a `TypeError`; correct the sentence "`cwd` and `env` are handed to the process unchanged" only as far as it becomes wrong (they are still handed on unchanged); keep stating that a `TypeError` from creating the compiler process carries no `parameter`. Touch the module docstring only if one of its sentences becomes wrong. Do not change the docstrings of `hilclaw/harness/timing_build.py` or `verification_build.py`.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures or helpers.
   - **Edits to existing tests are allowed only as additions of parameters**, and only to `test_type_errors_keep_their_parameter_through_pickling`. No existing assertion may be removed or changed, and no existing test may be renamed or deleted. Every other existing test, including those under `tests/harness/`, must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
   - **Happy path.** An `env` mapping of `str` (and on POSIX of `bytes`) keys and values still reaches the process; an existing `cwd` as `str`, `Path` and (POSIX) `bytes` is still the process's working directory; `env=None` and `cwd=None` still inherit; a non-mapping `env` is still left to `subprocess` with the class of a direct `Popen` and no `parameter`.
   - **Branch, refused `env`.** A key or value of a wrong type, a NUL in a key, a NUL in a value, and `=` after the first character of a key each raise the class of a direct `Popen` with `parameter == "env"`; an empty key or a key whose only `=` is the first character is not refused by the check (whatever `subprocess` then does is passed on as on `main`). A `TypeError` from `items()` itself carries `parameter == "env"`.
   - **Branch, refused `cwd`.** `cwd=3`, a `PathLike` whose `__fspath__` returns an `int`, `cwd="a\0b"` and `cwd=Path("a\0b")` raise the class of a direct `Popen` with `parameter == "cwd"`; on POSIX a lone surrogate `cwd` raises a `ValueError` subclass with `parameter == "cwd"`.
   - **No start.** For every refusal above, patch `clang_build.subprocess.Popen` to fail the test if called, and assert `names(out_dir) == []`.
   - **Negative, nothing else changes.** `CompilerNotStartedError` for a missing `cwd` and a regular-file `cwd` has no `parameter` and no `path_role`; the `ValueError`s of `timeout_s`, `compiler` and `flags` still have no `parameter`; a `TypeError` or `ValueError` from `Popen` patched to raise it with valid `env` and `cwd` has no `parameter`; order cases of criterion 2.
   - **Pickling.** A pickled and loaded `env` `ValueError` and `cwd` `TypeError` keep class, args and `parameter`.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only `sys.executable` and the stub compilers the suite already writes (and the real `clang` only where the suite already does). Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0267-<slug>` with a Draft PR whose title contains `T-0267`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green (Python 3.11 and 3.14 jobs, coverage gate, test presence);
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0267`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason, the CPython revisions read for how `subprocess.Popen` converts `env` and `cwd` on each platform (or a pointer to T-0265/T-0266's Result where unchanged), and which lines now set `parameter` `"env"` and `"cwd"`.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any `ARCHITECTURE/` file, in particular the files of T-0264 (ADR-0088, `Requirements.md`, `OpenDecisionProposals.md`, `StandardScenarios.md`), and any record of which row `parameter` `"env"` or `"cwd"` of `build` places.
- A path test of `cwd` in `build`, or any change to how a missing `cwd` is raised (ADR-0079 decision 4, ADR-0080).
- A NUL check of flags, sources, the output path or the compiler; tagging the existing `ValueError`s of `build` with `parameter`; any change to `compiler_version`.
- `hilclaw/local_run.py`, `hilclaw/harness/`, and the `cpu_standin` operation of `correctness.check` (HQ-0026, PLAN P1-1).
- Starting `claude` in any form (D16).

## Follow-ups

- (doc, after HQ-0027) An OD-18 sub-question 18 part (ma) record on what `parameter` `"env"` and `"cwd"` of `clang_build.build` and of `local_run.run`, and `path_role` `"cwd"` of `local_run.run`, make true for `correctness.check` (S4 against no row; S3 against S10).

## Result

- PR #168 (https://github.com/myungjoo/HIL-Claw/pull/168), squash-merged as e932bf3ff18490a54a7eaf1a9d64b4c77dcbedbe on main; branch `claude/T-0267-clang-build-env-and-cwd-parameter` deleted. The squash message ends with `Task: T-0267`.
- Entry check: `gh pr list` showed no open PR before the first edit.
- Review: 2 rounds, both Approve (https://github.com/myungjoo/HIL-Claw/pull/168#issuecomment-6232891868, #issuecomment-6232918342). No Critical/Major/Minor. Round-1 Nits addressed in 3a807c3: a 120-character docstring line rewrapped, and a POSIX test added for a lone surrogate in an `env` key or value (`UnicodeEncodeError`, the class of a direct `Popen`, `parameter == "env"`; the exception's `object` holds the value, as `subprocess` on `main` already did). Remaining Nit, no action: the Windows branches (`_env_text`'s `str` check, `_check_cwd`'s `os.fsdecode`) run only in `windows_only` tests and are not covered on Linux CI.
- CI green on 3a807c3: Python 3.11 and 3.14, coverage gate (lines 99.58%, functions 100%; `hilclaw/clang_build.py` lines 480-482, the Windows branch of `_env_text`, not executed on Linux), test presence, shellcheck, clang. Local (Windows, Python 3.14.4): full pytest 22484 passed, 434 skipped; `ruff check` and `ruff format --check` clean.
- Language: Python, the language of the module being changed (`hilclaw/clang_build.py`).
- Implementation: `_parameter` gained `kinds=(TypeError,)`; the six existing steps still tag `TypeError` only. `parameter` `"env"` is set by `with _parameter("env", (TypeError, ValueError)):` around `_check_env(env)` (line 310) and `"cwd"` by `with _parameter("cwd", (TypeError, ValueError)):` around `_check_cwd(cwd)` (line 312), both after the `compiler` step and before the temporary name, the clock read and `Popen`. `_check_env`/`_env_text` mirror `local_run`'s (no `items` → left to `subprocess`; `os.fsencode` on POSIX, `str` check on Windows; NUL; `=` in `key[1:]`; message shows the key only). `_check_cwd` converts with `os.fsdecode` on Windows / `os.fsencode` on POSIX and refuses a NUL; no path test, so a missing or regular-file `cwd` stays `CompilerNotStartedError` without `parameter`/`path_role`. Platform test uses the module's `_WINDOWS` (`sys.platform == "win32"`, as `subprocess`'s `_mswindows`). `env` and `cwd` are handed on unchanged. No import from `hilclaw.local_run`, no new public name. `build`'s docstring states the checks and the two new `parameter` values; module docstring unchanged (no sentence became wrong).
- CPython read: unchanged from T-0265's and T-0266's Results (installed `Lib/subprocess.py` 3.14.4; `posixmodule.c` `parse_envlist`/`path_converter`, `_winapi.c` `getenvironment`, `_posixsubprocess.c` on branches 3.11 and 3.14 at the revisions recorded there). New for `build`: with `cwd=None` its `Popen` arguments (stdin DEVNULL, stdout PIPE, stderr STDOUT, absolute executable) allow the `posix_spawn` path on 3.14 Linux, so the tests compare each refused `env` with a direct `Popen` with and without `cwd`; CI confirmed the classes on 3.11 and 3.14.
- Tests: only `tests/test_clang_build.py`. Existing tests: one row (`{"cwd": 3}`) added to `test_type_errors_keep_their_parameter_through_pickling`; nothing else edited; all existing tests, including `tests/harness/`, pass unchanged. The `env` `ValueError` pickling case is a new test because the existing one catches `TypeError` only. Size: `hilclaw/clang_build.py` +60/-11; tests +463.
- Follow-ups: unchanged ((doc, after HQ-0027) the OD-18 (ma) record for `parameter` `"env"`/`"cwd"` of `clang_build.build` and `local_run.run`). None new.
- No `claude` was started (D16).
