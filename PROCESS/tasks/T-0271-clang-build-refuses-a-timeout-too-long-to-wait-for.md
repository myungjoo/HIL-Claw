---
id: T-0271
title: Make `clang_build.build` and `compiler_version` refuse, before anything is started, a `timeout_s` longer than (2**31 - 1) / 1000 seconds, so a time limit no platform wait can take no longer starts the compiler and then escapes as an undocumented OverflowError
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0268]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 20, files: 1}
hq: []
---
## Why

`hilclaw.clang_build.build` is the build step of every stand-in kernel: `build_verification_executable` (the verification executable of `correctness.check`, ADR-0056) and `build_timing_executable` (the timing executable) both pass their arguments through to it. Its `_check_timeout` (`hilclaw/clang_build.py`, line 499) accepts any `int` or `float` with `0 < timeout_s < math.inf`. A finite value that is too long for the platform's wait passes that check. The compiler is then started, and `process.communicate(timeout=timeout_s)` in `_communicate` (line 441) raises `OverflowError`. Because that is not an `OSError`, `_communicate` kills the process and `build` passes the `OverflowError` on through the branch "An exception that is not an `OSError` and leaves the build early … is passed on unchanged" (docstring, line 287). `build`'s docstring does not name this error.

**Observed at planning time (`6df15b7`, Windows, Python 3.14.4).** With a stub compiler (`(sys.executable, script)`, where the script writes the `-o` file) and an existing source file:

- `timeout_s=1e300` raises `OverflowError: timestamp out of range for platform time_t` after the compiler was started. The same happens for `1e10`.
- `timeout_s=1e7`, `4294967.0` (`threading.TIMEOUT_MAX` on Windows) and `2147483.648` returned `ok=True`. This is because the stub ended at once, so the long wait was never needed. It does not show that those values are safe for a compiler that runs long.

The bound where the wait overflows depends on the platform and the Python version. `local_run.run`'s docstring says "can be a matter of weeks". On POSIX, `subprocess` waits through a selector whose `poll` takes its timeout in milliseconds as a C `int`, which tops out at 2**31 - 1 ms. On Windows, `WaitForSingleObject` takes a 32-bit millisecond count and the thread joins are capped by `threading.TIMEOUT_MAX`.

ADR-0060 decision 4 places "a `ValueError` or `TypeError` for a setting — a time limit, a flag, the compiler —" as S4, found "before the process the refused setting belongs to is started". The time limit of the build is the backend's own setting (ADR-0060 decision 3). Today a time limit that is too long is found only after the compiler process exists, and in a class that ADR-0060 names only for `local_run.run`. This task moves that refusal before the start, into the check `build` already makes, with the class and message style that check already uses. One bound for every platform keeps the tool's behaviour the same on Linux, macOS and Windows with WSL (C-7).

**The change, stated.**

- `_check_timeout` also raises `ValueError` when `timeout_s` is greater than `(2**31 - 1) / 1000` seconds (2147483.647 s, about 24.8 days). That is the largest number of whole milliseconds a C `int` holds, so it is below the POSIX `poll` bound and below the Windows bounds above. Values equal to the bound are accepted. Hold the bound in a private module constant. Do not add a public name.
- The message names `timeout_s` and the bound, in the style of the existing message `"timeout_s must be positive and finite: …"`. Whether it also shows the value is the executor's choice, as long as it matches the existing message's practice.
- The new check comes after the existing type check and after the positive-and-finite check, so `nan`, `inf`, `0` and negatives keep their current message.
- `compiler_version` calls `_check_timeout` too, so it gets the same refusal before `subprocess.run`. Its docstring already says "with the same errors".
- **No `parameter` on the new `ValueError`.** In `build`, a `ValueError` from the check of `timeout_s` carries no `parameter`. T-0261 left it so on purpose, T-0267 and T-0268 kept that, and `test_the_existing_value_errors_still_have_no_parameter` (line 2810) asserts it. Keep that rule: `_parameter("timeout_s")` stays `TypeError`-only. A `TypeError` for `timeout_s` still carries `parameter == "timeout_s"`.

What does not change: every other check, its order, class and message; the command; the handling after the start, including a non-`OSError` that leaves the build early; `local_run.run`, `verification_build.py` and `timing_build.py` (both pass on what `build` raises, unchanged).

This adds no public name, no data-plane member or file, and no value of `condition` or `error.kind`. It places no row of `correctness.check`, because ADR-0060 decision 4 already says where a `ValueError` for a time limit goes. It is not an owner-only item under DRIVER §9, and it needs no real `claude` (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, `Task:` trailer, size cap, the test rules of D12).
- `CLAUDE.md`: the standing rules (minimal comments, the language policy of layer 2, branch and merge procedure, test rules ①-⑤).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py`: the module docstring (lines 1-23); `build`'s docstring from "A compile failure or a timeout is a result" (line 219) to the end of the sentence on `parameter` (about line 257), and the sentence "An exception that is not an `OSError` …" (line 287); the body of `build` down to the `Popen` call (lines 293-336); `compiler_version` (line 402); `_communicate` (line 441); `_parameter` and `_check_timeout` (lines 460-503).
- `tests/test_clang_build.py`: the constants and fixtures at the top (lines 41-100: `WRITE`, `SLEEP`, `VERSION`, `BAD_TIMEOUT_VALUES`, `BAD_TIMEOUT_TYPES`, `TIMEOUT`, `stub`, `src`, `out_dir`); `test_timeout_must_be_positive_and_finite` and `test_timeout_must_be_a_number` (lines 2390-2407); the helper `forbid_start` (find it with `grep -n "def forbid_start"`); `test_the_existing_value_errors_still_have_no_parameter` (line 2800).
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`: decision 3 (the table of settings) and the paragraph of decision 4 around line 102 ("The rest: a `ValueError` or `TypeError` for a setting …"). Read it only to know what this change makes true. Do not edit it.
- `PROCESS/tasks/T-0268-clang-build-argument-checks-before-start.md`: `## Why` and `## Result`, for the precedent of moving a refusal before the start without adding `parameter`.

## Acceptance Criteria

1. **The refusal.** `build(..., timeout_s=v)` raises exactly `ValueError` (`type(error) is ValueError`) for each of these values: the bound plus a small amount (for example `2147483.648`), `1e10`, `1e300`, the `int` `2**31` and the `int` `10**400`. In every case:
   - the stub compiler is not started, and `subprocess.Popen` is not called (use `forbid_start`);
   - nothing is created in the output directory;
   - the error has no attribute `parameter` and no attribute `path_role`;
   - the message contains `timeout_s`.
2. **`compiler_version`.** `compiler_version(stub(VERSION), timeout_s=v)` raises exactly `ValueError` for the same values, before anything is started.
3. **The bound is accepted and works.** With `timeout_s` equal to the bound (`(2**31 - 1) / 1000`), and with `2147483` (an `int`), `build` with `stub(WRITE)` returns `ok=True`, and `compiler_version(stub(VERSION), …)` returns the version line. These run on every CI platform, so they show the bound is within what the platform's wait accepts there. If the bound fails on a CI platform, stop and report it in `## Result` as BLOCKED. Do not lower the bound on your own: the number is stated in this task.
4. **Order.** A `TypeError` value (for example `"10"`) still raises `TypeError` with `parameter == "timeout_s"`. The values of `BAD_TIMEOUT_VALUES` (`0`, negatives, `nan`, `inf`) still raise `ValueError` with the existing message "positive and finite". A too-long `timeout_s` together with a bad flag (`flags=("-o", "x")`), a missing source, or an empty compiler prefix raises the `timeout_s` error, because the time limit is still checked first.
5. **Unchanged behaviour.** Every existing test in `tests/test_clang_build.py`, in `tests/harness/` (including `tests/harness/test_calibration.py`) and in the rest of the suite passes unchanged. No existing test is edited or removed. If an existing test does fail, stop and return BLOCKED with its name. Do not edit it.
6. **Docstrings.** In `build`'s docstring, the list of what is raised before anything is started names a `timeout_s` longer than the bound, stated as (2**31 - 1) / 1000 seconds or in equivalent words, as a `ValueError`. Edit the sentence on `parameter` only if it becomes wrong; it already says a `ValueError` from the other checks carries none. `compiler_version`'s docstring needs no change unless a sentence becomes wrong. Add no code comment beyond what CLAUDE.md "코멘트 최소화" allows.
7. **Tests** (D12): put the cases of criteria 1 to 4 in `tests/test_clang_build.py` only, including negative cases (just above the bound, very large `float` and `int`), the branch at the bound (accepted), and the interaction cases of criterion 4. Add no test that targets test code, CI or hook scripts (rule ⑤). The CI gates hold: pytest with coverage (`hilclaw/` lines ≥ 80 %, functions ≥ 80 %), `ruff check` and `ruff format --check` clean.
8. **Scope.** Only the two files in `touchesFiles` change. No change to `hilclaw/local_run.py`, `hilclaw/harness/`, `ARCHITECTURE/`, `PROCESS/` (other than this task file's `## Result`), CI or settings. No new dependency.
9. **Result.** `## Result` records:
   - the PR, the review rounds and CI;
   - the language and the reason for it (Python, the language of the module being changed);
   - the size;
   - what a run with the bound showed on the local machine and on each CI platform;
   - the follow-ups.

   The executor starts no `claude` program (D16).

## Out of Scope

- `local_run.run`'s `OverflowError` for a time limit too long for the platform. It is documented there, ADR-0060 decision 4 places it, and the pending ADR-0088 (T-0264, HQ-0027) reads it. See Follow-ups.
- A `parameter` on any `ValueError` of `build`, including the new one.
- Any change after the start, including the handling of a non-`OSError` that leaves the build early.
- Any row, kind or record of `correctness.check`, and any edit of an ADR, `Requirements.md` or `OpenDecisionProposals.md`.
- `build_timing_executable` and `build_verification_executable`. They pass the new error on unchanged and need no edit.

## Follow-ups

- (code, after HQ-0027) The same refusal before the start in `local_run.run`, if the record of OD-18 sub-question 18 part (ma) on `local_run.run` does not settle the `OverflowError` otherwise.
- (doc, after HQ-0027) Fold into the pending OD-18 sub-question 18 part (ma) record, together with the T-0265..T-0270 follow-ups: a time limit too long for the platform's wait is now a pre-start `ValueError` of `build` and `compiler_version`, so ADR-0060 decision 4's "a `ValueError` … for a setting — a time limit … → S4" reaches it. Before this change it reached only `local_run.run`'s `OverflowError`.

## Result

- PR #172 (https://github.com/myungjoo/HIL-Claw/pull/172), squash-merged as e6553a2 with `gh pr merge --squash --body` (the body ends with `Task: T-0271`); branch `claude/T-0271-clang-build-timeout-bound` deleted.
- Review: 2 rounds, both Approve. Round 1 had one Low nit: a `{timeout_s!r}` of an int past the int-to-str digit limit would raise a different `ValueError` and drop "timeout_s" from the message; fixed by naming only the bound in the message, with a `10**5000` test case added.
- CI green on e27ca95: Python 3.11 and 3.14, coverage, C, sh, test presence. Local (Windows, Python 3.14): full pytest 22569 passed, 474 skipped; `hilclaw/` coverage 99 %; `ruff check` and `ruff format --check` clean. Without the source change, 13 of the new tests fail.
- Language: Python, the language of the module being changed (`hilclaw/clang_build.py`).
- Implementation: private `_MAX_TIMEOUT_S = (2**31 - 1) / 1000`; `_check_timeout` raises `ValueError("timeout_s must be at most 2147483.647 s")` after the type check and the positive-and-finite check, with no `parameter`; `compiler_version` gets the same refusal; `build`'s docstring names it. Size: source +6/-2, tests +89; no existing test edited.
- Bound runs (`(2**31 - 1) / 1000` and the int 2147483, with stub compilers) passed locally (Windows) and on Linux CI (ubuntu-latest). CI has no macOS or Windows runner.
- Follow-ups: the two above, plus (code, low) the existing "positive and finite" message also uses `{timeout_s!r}`, so a negative int past the digit limit (e.g. `-10**5000`) raises a `ValueError` whose message lacks "timeout_s" (class unchanged, nothing started). No `claude` was started (D16).
