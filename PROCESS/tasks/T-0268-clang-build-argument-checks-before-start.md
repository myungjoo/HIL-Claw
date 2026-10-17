---
id: T-0268
title: Make `clang_build.build` refuse, before the start, a flag or compiler part that `subprocess` would refuse (a NUL character, or on POSIX text `os.fsencode` cannot convert)
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0267]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 40, files: 1}
hq: []
---
## Why

`clang_build.build` hands `flags`, `trailing_flags` and the parts of the compiler prefix after the first to `subprocess.Popen` as they are. It checks only their type and, for flags, the `-o`/`--output` prefix. Two defects reach `Popen` today:

- **A NUL character** in such a string. `Popen` raises `ValueError` ("embedded null byte" on POSIX, "embedded null character" on Windows).
- **On POSIX, a string `os.fsencode` cannot convert**, for example a lone surrogate such as `"\ud800"`. `Popen` raises `UnicodeEncodeError`, a `ValueError` subclass.

In both cases the error comes from inside the construction of `Popen`. That is after the random temporary name and the clock read. `build` catches only `OSError` there, so the error leaves `build` as the "escaping" exception: unchanged, and with a note if removing the temporary file fails.

How the records treat this error:

- The accepted records list it as open: "whatever `clang_build.build` passes on from `subprocess` beyond the `OSError` its docstring names". See ADR-0083 decision 2 and ADR-0087 decisions 5 and 8.
- ADR-0060 decision 4 places "a `ValueError` or `TypeError` for a setting — a time limit, a flag, the compiler" as S4 `settings_refused`, whether the setting is refused for its value or for its type.
- `flags`, `trailing_flags` and `compiler` are settings of the backend (ADR-0060 decision 3).

**The change, stated.** `build` makes these defects pre-start errors of its own checks, the way T-0265 did for the arguments of `local_run.run` and T-0266/T-0267 did for `cwd`. The error class stays what `Popen` raises for the same single defect. It no longer comes from `subprocess`.

- In `_checked_flags`, each element of `flags` and `trailing_flags` gets two new checks. They run after the existing `str` check and the existing `-o`/`--output` check, so every error `main` raises today keeps its class and message:
  - on POSIX only, convert the element with `os.fsencode`. A failure leaves as the `UnicodeEncodeError` that `os.fsencode` raised, as the same object.
  - then refuse a NUL character with `ValueError`. The message names the parameter, never the value.
- In `_resolve`, each part of the prefix **after the first** gets the same two checks, after the existing `str` check and before `shutil.which`. The first part keeps exactly today's handling. A NUL or an unencodable first part still ends in `shutil.which` and `CompilerNotFoundError`, as `main` has it. This mirrors T-0265: "The NUL handling of the program is unchanged."
  - `compiler_version` shares `_resolve`. It therefore raises the same `ValueError` before it starts its process, instead of passing on the one from `subprocess.run`. Its docstring already says "with the same errors" as `build`, and the class does not change.
- **No `parameter` on these `ValueError`s.** `_parameter` in `build` tags only `TypeError` for these six steps. T-0261 left the `ValueError`s of the settings untagged on purpose (its Out of Scope: "ADR-0060 decision 4 already places it by what it is for"), and this task keeps that rule. A `TypeError` from these steps still carries `parameter` as it does now.
- **Windows.** A lone surrogate in a `str` argument is not refused here unless a direct `Popen` refuses it too. Observe what a direct `subprocess.Popen` does with such an argument on the machine you run, and record it in Result. If Windows `Popen` accepts it, `build` must accept it as well.
- Order, values handed on, and everything after the checks stay as they are:
  - `flags` and the prefix parts are handed to `Popen` unchanged (as `str`), not as converted bytes;
  - sources, output, `env`, `cwd`, the temporary file, the five error classes, `path_role`, results and the module docstring do not change, unless a sentence becomes wrong.

What this task does not do:

- It places no row of `correctness.check`.
- It adds no data-plane member, no value of `condition` or `error.kind`, and no new public name.
- It edits no record.

Which rows the records now give these errors is a later doc task (Follow-ups). That task waits for HQ-0027, because the unlanded branch of T-0264 edits the same part (ma) list of OD-18. Nothing here is an owner-only item under DRIVER §9, and nothing here depends on the answer to any open HQ.

**Why this item now.** STATE has no lock, no current task and no next task, and there is no open PR. Every non-DONE task file is BLOCKED on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025), T-0243 (HQ-0026) and T-0264 (HQ-0027). None of them touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`. The doc follow-ups of T-0265 to T-0267 all wait for HQ-0027. The `cpu_standin` operation of `correctness.check` waits on HQ-0026, through the log keeper of T-0243. PLAN P1-1 goes on through the open entries of OD-18 part (ma). This is the entry "passed on from `subprocess`", for the arguments of `build`, and a code change can shrink it with no owner decision.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format; the branch `claude/T-0268-<slug>`; a PR title containing `T-0268`; the trailer `Task: T-0268` in the commit and as the last line of the PR body; the size cap; the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`, decision 4 (lines 69-104), especially the bullet "What the functions on `main` report, against the rows" (line 102). Do not edit it.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`, decisions 5 and 8 (lines 51-69). Do not edit it.
- `hilclaw/clang_build.py` at `aadfa49` or later:
  - `build` (line 195), its docstring and its body up to the `Popen` call (line 323) and its `except BaseException` branch;
  - `compiler_version` (line 396);
  - `_parameter` (line 454), `_check_env` and `_env_text` (lines 462-482, the precedent for the platform conversion), `_checked_flags` (line 500) and `_resolve` (line 537).
- `hilclaw/local_run.py`, `_resolve` (line 282), for the precedent of the NUL check of an argument (T-0265).
- `tests/test_clang_build.py`:
  - the `Stub` class and the fixtures `stub`, `src` and `out_dir` (lines 60-100). `stub(...)` returns `(sys.executable, script)`, so the stub's second part is a part "after the first";
  - `test_flags_of_the_wrong_type` (line 2363), `test_flags_must_not_set_the_output` (line 2378), `test_malformed_compiler_argument` (line 2448);
  - `test_a_refused_env_has_the_class_popen_raises` (line 2000) and `test_a_lone_surrogate_in_env_has_the_class_popen_raises` (line 2211), the precedent for comparing with a direct `Popen` with and without `cwd`.
- `PROCESS/tasks/T-0265-local-run-env-and-argument-parameter.md` and `PROCESS/tasks/T-0267-clang-build-env-and-cwd-parameter.md`, "Result", for the platform notes: the `posix_spawn` path on 3.14 when `cwd` is `None`, and the CPython revisions read.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build` and `compiler_version`.** Make the change as "The change, stated" says:
   - A NUL character in any element of `flags` or `trailing_flags`, or in any part of the compiler prefix after the first, raises `ValueError` before anything is started:
     - no temporary name is drawn and no clock is read;
     - no compiler process is created and the output directory stays as it was.
   - On POSIX, an element or part that `os.fsencode` cannot convert raises the `UnicodeEncodeError` that `os.fsencode` gives, as the same object, at the same point.
   - The class each raises is the class a direct `subprocess.Popen` of the same command raises for that single defect on the platform: `ValueError`, or `UnicodeEncodeError` for the conversion.
   - Every check that exists today keeps its order, class and message. The `-o` check comes before the NUL check, so a flag `"-o\0x"` still gets the "must not set the output" message.
   - The first part of the prefix is handled exactly as on `main`.
   - The new `ValueError`s carry no `parameter`. No `path_role` is added.
   - Values are handed to `Popen` unchanged.
   - Add no new module-level public name, and no comment that restates the code.
3. **Docstrings.**
   - Extend `build`'s "Raised before anything is started" list. State:
     - the NUL refusal for flags and for compiler parts after the first;
     - the POSIX conversion;
     - that the class is the one `subprocess` would raise.
   - Keep the sentences on `parameter` true: they say a `ValueError` "from the other checks" carries none, so check that this still covers the new checks.
   - `compiler_version`'s docstring needs no change if "with the same errors" stays true. Do not edit it otherwise.
   - Change no other docstring unless one of its sentences becomes wrong.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures.
   - **Do not edit or delete any existing test.** Every existing test, including `tests/harness/` and `tests/test_standin_profile.py`, must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name.
   - **Happy path.** Flags with ordinary non-ASCII text (for example `"-DNAME=é"`) still reach the stub compiler and give an ok build. On POSIX, a surrogate-escaped value that `os.fsencode` converts (for example `"-D\udcff"`) is accepted and reaches the stub.
   - **Error, each place.** A NUL in an element of `flags`, in an element of `trailing_flags`, and in the stub's second compiler part each raise `ValueError`:
     - the stub is not started;
     - the output directory is unchanged;
     - `not hasattr(error, "parameter")`;
     - the message does not contain the refused value.
   - **Branch, the class against `Popen`.** For each refused value, compare the class with what a direct `subprocess.Popen` of the same command raises, on the running platform:
     - the values are a NUL, and on POSIX a lone surrogate `"\ud800"`;
     - compare both with `cwd=None` and with a `cwd`, the two POSIX start paths on 3.14;
     - use `issubclass` or exact class equality as the case needs, and record which in Result.

     On Windows, add one test that pins what the platform does with a lone surrogate (accepted, or refused with the `Popen` class).
   - **Branch, order.** Each of these keeps its current class, message and `parameter` behaviour:
     - a flag `"-o\0x"`;
     - a call with both a bad `timeout_s` and a NUL flag reports the `timeout_s` error;
     - a non-`str` element after a NUL element in the same sequence reports whichever comes first in the sequence.
   - **Branch, the first part.** A NUL in the first part of the compiler prefix still raises `CompilerNotFoundError`. So does an unencodable first part on POSIX. Neither has `parameter`.
   - **`compiler_version`.** A NUL in a compiler part after the first raises `ValueError` and starts nothing.
   - **Negative.**
     - A `TypeError` for a non-`str` flag still carries `parameter` `"flags"`.
     - An existing `ValueError` (non-positive `timeout_s`, empty prefix, `-o` flag) still has no `parameter`.
     - A NUL in a source path or in the output path still gives the path-test error that `main` gives. Assert its class and `path_role`. Record in Result what was observed on 3.11 and 3.14 if CI differs from the local run.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only the stub compilers the suite already writes, plus the direct `Popen` comparisons, which must not start a process when the platform refuses the value. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0268-<slug>` with a Draft PR whose title contains `T-0268`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0268`;
   - delete the branch.
   - In Result, record:
     - the language (Python, the module's language) with a one-line reason;
     - the lines that now raise the new errors;
     - the CPython source or revisions read for the class `Popen` raises.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/`: ADR-0060, ADR-0079 to ADR-0087, Requirements, OpenDecisionProposals and StandardScenarios. Also the unlanded branch `claude/T-0264-adr-od18-local-run-parameter`.
- Placing any row of `correctness.check`, S4 or otherwise, for the new errors.
- A `parameter` on any `ValueError` of these six steps.
- Any change to the first part of the compiler prefix, to `CompilerNotFoundError`, to sources or output, to `env`/`cwd`, or to what happens from `Popen` on.
- `local_run.run`, including its own handling of unencodable arguments (Follow-ups).
- The callers `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py` and `hilclaw/standin_profile.py`, and their tests.
- The `cpu_standin` operation of `correctness.check` (waits on HQ-0026).

## Follow-ups

- (doc, after HQ-0027) An OD-18 part (ma) record: a NUL or unencodable flag or compiler part is now a pre-start `ValueError` of `build`, so it leaves the entry "whatever `clang_build.build` passes on from `subprocess`". This task leaves it to that record whether ADR-0060 decision 4 ("a `ValueError` … for a setting … → S4") already reaches it.
- (code) `local_run.run`: on POSIX, convert each argument with `os.fsencode` before the start, so an unencodable argument is refused with `parameter` `"command"` like the NUL check of T-0265. Today it is passed on from `subprocess`.

## Result

- PR #169 (https://github.com/myungjoo/HIL-Claw/pull/169), squash-merged as 8aee9ba65ce3bf484c2e76b5c18b765f2de8e2db; branch `claude/T-0268-clang-build-argument-checks-before-start` deleted; squash message ends with `Task: T-0268`. Entry check: `gh pr list` showed no open PR.
- Review: 2 rounds, both Approve (#issuecomment-6233430435, #issuecomment-6233452484). Round-1 Low addressed in 092aba3: the Windows test now covers a lone surrogate in flags, trailing_flags and a compiler part after the first. Info, no action: when one call has several defects, a NUL flag or part is now reported before later steps (sources/output, CompilerNotFoundError, env/cwd); every single-defect input keeps its class and message. The OD-18 (ma) follow-up record can say so.
- CI green on 092aba3: Python 3.11 and 3.14, coverage (lines 99.58%, functions 100%; clang_build.py lines 486-488 are the Windows branch of `_env_text`), test presence, shellcheck, clang. Local (Windows, Python 3.14.4): full pytest 22526 passed, 462 skipped; `ruff check` and `ruff format --check` clean.
- Language: Python, the language of the module being changed (`hilclaw/clang_build.py`).
- New errors: private `_check_argument`: `os.fsencode` on POSIX (its UnicodeEncodeError is passed on as the same object), then a NUL gives ValueError naming the parameter, never the value. Called from `_checked_flags` after the str and -o/--output checks, and from `_resolve` for `prefix[1:]` after the str check of every part and before `shutil.which`. No `parameter`, no `path_role`, values handed on unchanged; `compiler_version` and module docstrings unchanged.
- Platform: on Windows 3.14.4, a direct Popen accepts a lone surrogate with and without cwd, so build accepts it (pinned by a windows_only test). A NUL gives ValueError with and without cwd. Tests compare by exact class equality against a direct Popen with and without cwd; CI confirmed ValueError/UnicodeEncodeError on 3.11 and 3.14.
- CPython read: no new reading; the T-0265/T-0267 record is used, plus the direct-Popen comparisons on CI.
- Path NUL: a NUL in a source gives FileNotFoundError with path_role "source"; a NUL in the output directory gives FileNotFoundError with path_role "output".
- First prefix part unchanged: an absolute path + NUL, or + lone surrogate on POSIX, still gives CompilerNotFoundError without `parameter`.
- Tests: tests/test_clang_build.py only; no existing test edited. Size: clang_build.py +21/-3; tests +308.
- Follow-ups: unchanged from the task file; none new. No `claude` was started (D16).
