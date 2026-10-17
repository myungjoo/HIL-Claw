---
id: T-0265
title: Check `env` and NUL characters in the arguments in `local_run.run` before the start, so a refused `env` carries `parameter` "env" and a refused argument carries `parameter` "command"
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0263]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 60, files: 1}
hq: []
---
## Why

ADR-0060 decision 4 (`ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`, the bullet "What the functions on `main` report, against the rows", line 102) lists among the errors that "arise in one class in two rows" "a `ValueError` or `TypeError` of `local_run.run` for an `env` (S4) or for an argument the operation's own code formed". It answers the two halves differently: a setting refused for its value or its type is S4 `settings_refused`; a `TypeError` or `ValueError` of `local_run.run` "for an argument its own code formed" is no row (`operation_answer_invalid`, ADR-0045 decisions 4 and 5). ADR-0060 leaves making the rows distinguishable to the operation's code, "for example by a change of those functions, binding nothing here".

T-0263 (PR #165, `7994476`) made every `TypeError`/`ValueError` from the checks of `run` before the start carry an attribute `parameter` (`"timeout_s"` or `"command"`). The errors `subprocess` raises at the start still carry none, and two of them are the two halves above:

- an `env` that `subprocess` cannot hand over (`{"A=B": "x"}` → `ValueError`, `{"A": 3}` → `TypeError`, a NUL in a key or a value → `ValueError`);
- an argument of the command that holds a NUL character (`ValueError`). `_resolve` already checks that each argument is a `str`, so a NUL is the only way an argument passes the check of `run` and is then refused by `subprocess`.

Both arrive in the same class with no `parameter`, so a caller cannot tell S4 from no row. This task moves those two checks before the start, into `run`'s own checks, so the existing `_parameter` mechanism names them. This is the first half of the T-0263 follow-up "(code, later) The errors `run` passes on from `subprocess`". The other half (the `OSError` for a missing `cwd`, S3, against other start errors, S10, and a `TypeError`/`ValueError` for `cwd`) is not in this task. This task does not depend on HQ-0027 (T-0264, ADR-0088). It changes no `ARCHITECTURE/` file.

Observed on Windows, Python 3.14.4, with `subprocess.run([sys.executable, "-c", "pass"], env={**os.environ, **extra})`:

| `extra` / argument | outcome |
|---|---|
| `{"A=B": "x"}` | `ValueError` illegal environment variable name |
| `{"A": 3}` | `TypeError` environment can only contain strings |
| `{3: "x"}` | `TypeError` bad argument type for built-in operation |
| `{"A\0": "x"}`, `{"A": "x\0"}` | `ValueError` embedded null character |
| `{b"A": b"x"}` | `TypeError` (Windows takes `str` only) |
| `{"": "x"}` | `OSError` [WinError 87] |
| `{"=A": "x"}` | accepted |
| env `[("A", "x")]` (not a mapping) | `AttributeError` |
| argument `"x\0y"` | `ValueError` embedded null character |

On POSIX, `subprocess` converts `env` in one of two places depending on the start path it picks: the loop in `Popen._execute_child` of `Lib/subprocess.py` (`os.fsencode` of key and value, `ValueError` for any `=` in the key, NUL refused later by `_fork_exec`) or `os.posix_spawn` (`parse_envlist` in `Modules/posixmodule.c`, which refuses an empty key or a `=` after the first character). Which path is taken depends on, among others, whether `cwd` is `None`. So the two POSIX paths disagree on a leading `=` and on an empty key, and the check must not take either side on those.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (executor procedure, naming convention, size cap, test rules, time limit).
- `CLAUDE.md` "테스트 규칙" (D12) and "도구 계층 언어 정책".
- `hilclaw/local_run.py` (whole file, 257 lines): `run` and its docstring, `_parameter`, `_check_timeout`, `_resolve`, `_run_with_usage`, `_run_without_usage`.
- `tests/test_local_run.py` lines 600-810 (the `parameter` tests of T-0263 and the helpers `raised`, `refusing`, `without_wait4`), and lines 1-80 for the fixtures `child`, `QUIET`, `TIMEOUT`, `posix_only`, `windows_only`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` line 102 only (decision 4, the bullet quoted in Why). Read, do not edit.
- `PROCESS/tasks/T-0263-local-run-pre-start-error-parameter.md` (Acceptance Criteria and Result) for the conventions this task continues.
- CPython sources for 3.11 and 3.14 (the CI matrix, `.github/workflows/ci.yml`): `Lib/subprocess.py` `Popen._execute_child` (both the POSIX and the Windows branch), `Modules/posixmodule.c` `parse_envlist`, `Modules/_winapi.c` `getenvironment`. The installed `Lib/subprocess.py` can be read locally; the C files can be read with `gh api` or the web on the `3.11` and `3.14` branches of `python/cpython`. Record in the Result which revisions were read.

## Acceptance Criteria

1. **Check order and placement.** `run` checks, in this order and before anything is started: `timeout_s` (unchanged), `command` (unchanged, plus criterion 2), then `env` (criterion 3). The `env` check runs inside `with _parameter("env"):`. `ProgramNotFoundError` from `_resolve` keeps coming before any `env` error.
2. **NUL in an argument.** `_resolve` raises `ValueError` for an argument (any element after the program) that contains `"\0"`, before the program lookup or after it at the executor's choice (state which in the Result). It carries `parameter == "command"` through the existing `with _parameter("command"):`. Nothing is started. The class is the one `subprocess` raised before (`ValueError`). The handling of a NUL in the **program** is unchanged (it is platform-dependent on `main`: `shutil.which` raises `ValueError` on Windows, which `_parameter` already tags `"command"`, and returns `None` on POSIX, giving `ProgramNotFoundError`); do not change it.
3. **`env` checked before the start.** When `env` is not `None`, a new private check iterates `env.items()` once and raises, with the same class `subprocess` would raise, for each of these cases on every platform of the CI and on native Windows:
   - a key or a value of a type `subprocess` refuses on the platform → `TypeError` (on Windows anything that is not `str`; on POSIX anything `os.fsencode` refuses — `str`, `bytes` and `os.PathLike` are accepted);
   - a key with `=` after its first character → `ValueError`;
   - a NUL in a key or a value → `ValueError`.
   The error carries `parameter == "env"` and nothing is started.
4. **Never stricter than `subprocess`.** The check refuses nothing that `subprocess` accepts on the platform along any of its start paths. In particular these are still accepted and reach the process: `env=None`; a copy of `os.environ`; on POSIX `bytes` keys and values (for example `{b"HILCLAW_T": b"x"}`); on Windows a key with a leading `=` (`{"=A": "x"}`). These stay exactly as on `main` (same class as before, no `parameter`, the check does not raise for them): a key that is empty, a key whose only `=` is its first character on POSIX, and an `env` that is not a mapping (the `AttributeError` from `.items()` may now come from the check, but its class is unchanged and it carries no `parameter`, because `_parameter` catches only `TypeError` and `ValueError`).
5. **Unchanged elsewhere.** Classes, messages and order of the existing checks are unchanged. `cwd` is not checked (a `TypeError`/`ValueError`/`OSError` for `cwd` stays a pass-on from `subprocess` with no `parameter`). The `OverflowError` for a too long `timeout_s`, errors from the wait, `KeyboardInterrupt` handling and the reaping are unchanged. `env` is handed to `subprocess` as it was given (no copy, no conversion). No new public name, no new import of another `hilclaw` module, no change to `RunResult` or `ProgramNotFoundError`.
6. **Docstring.** The docstring of `run` says that `env` is checked before the start, lists the refused cases of criterion 3 and their classes, extends the `parameter` paragraph with `"env"` (and that a NUL in an argument is `"command"`), and keeps saying what remains passed on from `subprocess` (`OSError` from the start, errors for `cwd`, `OverflowError`). Keep it accurate for both platforms. No other comment beyond what CLAUDE.md "코멘트 최소화" allows.
7. **Tests (D12).** In `tests/test_local_run.py`:
   - happy: each accepted `env` of criterion 4 reaches the process (the child sees a set variable) for both wait paths (`platform_wait` true/false, as in the existing tests), with POSIX-only and Windows-only cases marked with `posix_only`/`windows_only`;
   - negative: each refused case of criterion 3 and criterion 2 raises the stated class with the stated `parameter`, and `child.started` is false, for both wait paths;
   - branch: the order — a bad `timeout_s` with a bad `env` gives `"timeout_s"`; a bad `command` with a bad `env` gives `"command"`; a missing program with a bad `env` gives `ProgramNotFoundError` with no `parameter`;
   - error: an `env` mapping whose `items()` raises `TypeError` gets `parameter == "env"`; one whose `items()` raises another exception passes it on with no `parameter`; a non-mapping `env` keeps its class (`AttributeError`) and has no `parameter`; criterion 4's unchanged cases (empty key, leading `=` on POSIX) raise what they raised on `main` and have no `parameter` — assert the class only where it is the same on both POSIX start paths, otherwise assert only the absence of `parameter`;
   - pickling: an `env` error keeps `parameter` through `pickle` (extend the parametrisation of `test_the_parameter_survives_pickling` or add a test).
   **Existing tests that may be edited:** only `test_an_env_that_subprocess_refuses_names_no_parameter` (around lines 764-776), which pins the old behaviour; replace or rename it so that it asserts `parameter == "env"`. `test_the_parameter_survives_pickling` may get new parameter rows. No other existing test in any file may be edited or deleted. If another existing test turns out to pin the old behaviour, stop and report it (BLOCKED, requirement-unclear) rather than editing it.
8. Line and function coverage of `hilclaw/` stay ≥ 80% (CI gate); `ruff check` and `ruff format --check` clean; full `pytest` passes locally; CI green.
9. Size: ≤ 300 LOC changed and ≤ 5 files excluding tests (expected: `hilclaw/local_run.py` only).
10. The Result states the language (Python — the module's language), the CPython revisions read for criterion 3/4, and whether the NUL check of criterion 2 is before or after the lookup.

## Out of Scope

- The `OSError` for a missing `cwd` (S3) against other start errors (S10), a `TypeError`/`ValueError` for `cwd`, and the pre-start `OSError` of the program lookup (`os.getcwd` inside `os.path.abspath`) — the next code task.
- A NUL in the program, and the POSIX/Windows difference in how it is reported.
- Any `ARCHITECTURE/` file, in particular the files of T-0264 (ADR-0088, `Requirements.md`, `OpenDecisionProposals.md`, `StandardScenarios.md`) and any record of which row `parameter` `"env"` places; that is a doc task after HQ-0027 is answered.
- `hilclaw/clang_build.py`, `hilclaw/harness/timing.py`, `hilclaw/harness/verification.py` and the `cpu_standin` operation of `correctness.check` (HQ-0026, PLAN P1-1).
- Starting `claude` in any form (D16).

## Follow-ups

- (code) Split the `OSError` for a missing `cwd` (S3) from other start errors (S10) in `local_run.run`, and name `cwd` errors; include the pre-start lookup `OSError` (T-0264 Follow-ups).
- (doc, after HQ-0027) An OD-18 sub-question 18 (ma) record on what `parameter` `"env"` and the argument NUL check of `local_run.run` make true for `correctness.check`.

## Result
