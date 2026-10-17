---
id: T-0263
title: Make every TypeError and ValueError that `local_run.run` raises from its checks before the start name the parameter it is about, so a refused time limit is told from a malformed command
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0261]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 30, files: 1}
hq: []
---
## Why

ADR-0060 decision 4 ("What the functions on `main` report, against the rows") names, among the errors that "arise in one class in two rows", "a `ValueError` or `TypeError` of `local_run.run` for an `env` (S4) or for an argument the operation's own code formed". It answers the two halves differently:

- a `ValueError` or `TypeError` for a **setting**, among them a time limit, is S4 `settings_refused`, "whether the setting is refused for its value or for its type";
- a `TypeError` or `ValueError` of `local_run.run` "for an argument its own code formed or an empty command" is no row; the landed rules answer it `operation_answer_invalid` (ADR-0045 decisions 4 and 5).

ADR-0060 ("Telling the rows apart is a condition of the operation's code") leaves making them distinguishable to a code task, "for example by a change of those functions, binding nothing here". ADR-0087 decision 8 still lists "the `ValueError` or `TypeError` and the `OSError` for 'a `cwd` that does not exist' of `local_run.run`" as open under part (ma) of sub-question 18 of OD-18. On `main` (`3485be8`) every such error of `run` is a plain `TypeError` or `ValueError` with a message.

`run` raises these classes from two places:

1. **Its own checks before the start**: `_check_timeout(timeout_s)` (a `TypeError` for a non-number, a `ValueError` for a value that is not positive and finite) and `_resolve(command)` (a `TypeError` for one `str` or `bytes`, a non-iterable, a program of the wrong type, a non-`str` argument; a `ValueError` for an empty command). These can be told apart by which check raised them.
2. **What `subprocess` passes on** after `run` hands over `command`, `cwd` and `env`: a `ValueError` or `TypeError` for an `env` or an argument it cannot hand over, an `OSError` from the start, an `OverflowError`. These cannot be told apart by which line raised them, and their design is left to a later task (Follow-ups).

This task covers part 1 only.

**The change, stated.** Follow the precedent of T-0261 (`parameter` on the pre-start `TypeError`s of `clang_build.build`). The classes stay what they are, because existing tests catch them with `pytest.raises(TypeError)` and `pytest.raises(ValueError)`. Add one attribute, `parameter`, to every `TypeError` and every `ValueError` that leaves `run` from the checks it makes before the start. Its value is the name of the parameter of `run` the error is about:

- `"timeout_s"`: from `_check_timeout(timeout_s)`, both the `TypeError` and the `ValueError`;
- `"command"`: from `_resolve(command)`, both classes. This includes an error Python raises inside that check, for example the `TypeError` of `tuple(command)` for a non-iterable, or the `TypeError` of `os.fspath` for an `os.PathLike` whose `__fspath__` returns neither `str` nor `bytes`.

Unlike T-0261, `ValueError` is tagged too. In `local_run.run` one `ValueError` is for a setting (`timeout_s`) and one is for the command the operation forms (empty), so the class alone is two rows. In `clang_build.build` every pre-start `ValueError` was already placed by ADR-0060.

What it covers:

- For an error that `run` or its helpers raise themselves, the attribute is set on the object before it leaves `run`.
- A foreign `TypeError` or `ValueError` (from `tuple`, iteration or `os.fspath`) is caught, given the attribute on that same object, and re-raised with a bare `raise`. Its class, `args`, traceback, `__cause__` and `__context__` stay unchanged.
- **Set it in `run`.** Attach it however you like: a `try` around each check, or one small private context manager like `clang_build._parameter`, extended to `(TypeError, ValueError)`. Do not import a private name from `clang_build`; `local_run` has no import of `clang_build` today and must not gain one. Each of the two checks gets its own value.
- **No other error carries it:**
  - `ProgramNotFoundError` (a `LookupError`);
  - a `TypeError` that Python raises while binding the call before `run` runs, for example a missing `timeout_s` (`test_timeout_has_no_default`);
  - anything from `subprocess.Popen`, `subprocess.run` or later: an `OSError` from the start (a missing `cwd`, a file the system cannot execute), a `ValueError` or `TypeError` for an `env` or `cwd` that cannot be handed over, an `OverflowError` for a time limit too long to wait for, a `KeyboardInterrupt` during the wait.

A caller reads it as `getattr(error, "parameter", None)`. `None` means the error came from none of the two checks.

This is an engineering choice inside `run`, which ADR-0060 leaves to the code task. It adds:

- no new module-level public name: the values are two plain strings, documented in `run`'s docstring;
- no data-plane member or file;
- no value of `condition` or `error.kind`.

It places no row of `correctness.check`; that is for a later doc task (Follow-ups). It is not an owner-only item under DRIVER §9.

Nothing else changes:

- the order of the checks (`_check_timeout` before `_resolve`), every message and every class;
- `RunResult`, `ProgramNotFoundError`, the wait, the reaping and the usage;
- the module docstring, unless one of its sentences becomes wrong.

**Existing tests checked at planning time (`3485be8`).** No test under `tests/` asserts anything about an attribute named `parameter` on an error of `run`. The tests that pin a module's public names with `vars(...)` (`tests/test_selfcheck.py` line 320, `tests/test_selfcheck_login.py` line 149, `tests/test_selfcheck_session.py` line 321, `tests/test_standin_profile.py` line 1066) pin other modules, and this task adds no public name to `local_run` anyway. The tests in `tests/test_local_run.py` that catch these errors still pass, because the classes are unchanged:

- `test_empty_command` (line 248);
- `test_command_as_one_string` (line 256);
- `test_command_that_is_not_iterable` (line 263);
- `test_argument_that_is_not_a_str` (line 269);
- `test_program_of_the_wrong_type` (line 286);
- `test_timeout_must_be_positive_and_finite` (line 334);
- `test_timeout_must_be_a_number` (line 341);
- `test_timeout_has_no_default` (line 347).

The callers `hilclaw/harness/timing.py`, `hilclaw/harness/verification.py`, `hilclaw/harness/memory_ceiling.py`, `hilclaw/selfcheck_login.py`, `hilclaw/selfcheck_session.py` and `hilclaw/standin_profile.py` catch the built-in classes or `ProgramNotFoundError`. An added attribute does not change what they see.

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). None of them touches `hilclaw/local_run.py` or `tests/test_local_run.py`, and this task depends on none of those HQs. PLAN P1-1 continues through the OD-18 (ma) work. The `local_run.run` split is the follow-up named by T-0261 and T-0262. Of the other entries ADR-0087 decision 8 leaves open:

- the unroled `OSError` of `build` may need a new `error.kind`, which is the owner's (ADR-0086 decision 6);
- the `CompilerRunError` with `timed_out` false and `returncode` `None` has no stated status (ADR-0085 decision 6);
- the unnamed `TypeError` of `build` from `subprocess` was not read.

The pre-start errors of `run` are the part a member can split with no owner decision.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0263-<slug>`, the PR title with `T-0263`, the trailer `Task: T-0263` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`, decision 4: the bullet "What the functions on `main` report, against the rows" (line 102), its sentences on `local_run.run`; and the Consequences bullet "Telling the rows apart is a condition of the operation's code" (line 157). Do not edit it.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`, decision 8 (lines 64-68). Do not edit it.
- `hilclaw/local_run.py` at `3485be8` or later: the whole file (238 lines), especially `run` (line 76) and its docstring paragraph "Raised before anything is started: …", `_check_timeout` (line 209) and `_resolve` (line 216).
- `hilclaw/clang_build.py`: `_parameter` (line 433) and the lines of `build` that use it (lines 270-293), as the precedent only. Do not edit it.
- `tests/test_local_run.py`: the fixture `child` and its helper class (lines 50-75), and the tests listed under "Existing tests checked at planning time" above (lines 248-350).
- `PROCESS/tasks/T-0261-clang-build-type-error-parameter.md`, "The change, stated" and "Result", for the precedent.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/local_run.py` or `tests/test_local_run.py`, stop and return BLOCKED (open-PR conflict).
2. **`run`.** Make the change as "The change, stated" says:
   - Every `TypeError` and `ValueError` that leaves one of the two checks carries `parameter` with the value listed for it.
   - A foreign error is the same object after the change (`is`). It keeps its class, `args` and message, and it is re-raised with a bare `raise`.
   - No other error that `run` raises or passes on has the attribute.
   - Keep the order of the checks and every message. Add no new module-level public name. Add no import of `hilclaw.clang_build`. Add no comment that restates the code.
3. **Docstring.**
   - Extend the paragraph of `run`'s docstring that begins "A non-zero exit, a signal or a timeout is a result" so it states:
     - `parameter` and its two values;
     - that it is set on any `TypeError` or `ValueError` from those checks, including one Python raises inside them;
     - that an error from anywhere else, including what `subprocess` raises, carries no `parameter`.
   - Change no other sentence of `run`'s docstring unless it becomes wrong.
   - The docstrings of `RunResult`, `ProgramNotFoundError` and the module do not change, unless one of their sentences becomes wrong.
4. **Tests** in `tests/test_local_run.py`, following D12. Do not test the fixture.
   - **Edits to existing tests are allowed only as additions of assertions or parameters.** No existing assertion may be removed or changed, and no existing test may be renamed or deleted. Additions are allowed only to the eight tests listed under "Existing tests checked at planning time". Every other existing test, including those under `tests/harness/`, `tests/test_selfcheck*.py` and `tests/test_standin_profile.py`, must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
   - **Happy path, `"timeout_s"`.** These raise with `parameter == "timeout_s"`: every value of `BAD_TIMEOUT_TYPES` (a `TypeError`) and every value of `BAD_TIMEOUT_VALUES` (a `ValueError`). In each, `type(error)` is exactly the built-in class and the child is not started.
   - **Branch, `"command"`.** These raise with `parameter == "command"`:
     - an empty list and an empty tuple (`ValueError`);
     - one `str` and one `bytes` as the command (`TypeError`);
     - a program of each wrong type used by `test_program_of_the_wrong_type` (`TypeError`);
     - each non-`str` argument used by `test_argument_that_is_not_a_str` (`TypeError`).
   - **Branch, a foreign error.** These carry `parameter == "command"` and the message Python gave them:
     - `run(5, ...)`: the `TypeError` of `tuple`;
     - a command given as an iterable whose iteration raises a given `ValueError` instance: `run` raises that same object (`is`), with `__cause__` and `__context__` unchanged;
     - a program that is an `os.PathLike` whose `__fspath__` returns an `int`: the `TypeError` of `os.fspath`.
   - **Branch, order.** A call with both a bad `timeout_s` and an empty command reports `"timeout_s"`, as the order of the checks has it.
   - **Negative.** Each of these has no `parameter` attribute (`not hasattr(error, "parameter")`):
     - a missing `timeout_s` (`test_timeout_has_no_default`);
     - `ProgramNotFoundError` for a program that does not exist;
     - the `OSError` for a missing `cwd` (`test_missing_cwd_passes_the_oserror_on`);
     - a `ValueError` and a `TypeError` raised by a patched `subprocess.Popen` (POSIX path) and by a patched `subprocess.run` (the path without `wait4`, patched as the existing `without wait4` tests do), with no child started;
     - an `env` that `subprocess` refuses, for example `{"A=B": "x"}` (a `ValueError`) or `{"A": 3}` (a `TypeError`). If on some platform `subprocess` accepts such a value, assert what it actually does there, or skip on that platform with the reason, and record that in Result.

     A successful run still returns a `RunResult`.
   - **Pickling.** A pickled and loaded `TypeError` and `ValueError` with `parameter` keep their class, message and `parameter` (T-0261 found that a plain `TypeError` keeps its instance attribute through `pickle`).
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only the Python child processes the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0263-<slug>` with a Draft PR whose title contains `T-0263`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0263`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason. State from the code which lines now set `parameter` and to which value.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/`: ADR-0060, ADR-0078 to ADR-0087, Requirements, OpenDecisionProposals and StandardScenarios.
- Placing any row of `correctness.check`, including S4 or no row for either value of `parameter`.
- Everything `run` passes on from `subprocess`: telling an `env` error from an argument error, the `OSError` for a missing `cwd` (S3) against other start errors (S10), the `OverflowError`. No new check of `env` or `cwd` before the start.
- `hilclaw/clang_build.py` and its tests; `compiler_version`.
- New error classes, or a changed class for any error.
- The callers of `run` and their tests. Also out: the `cpu_standin` operation of `correctness.check` (HQ-0026).

## Follow-ups

- (doc) A record under OD-18 sub-question 18 part (ma) on what `parameter` of `local_run.run` makes true for `correctness.check`. It weighs, from ADR-0060 decision 4: S4 `settings_refused` for `"timeout_s"`, no row (`operation_answer_invalid`) for `"command"`, and an error with no `parameter`.
- (code, later) The errors `run` passes on from `subprocess`: an `env` error against an argument error (S4 against no row), and the `OSError` for a missing `cwd` (S3) against other start errors (S10). The design is left to that task.

## Result
