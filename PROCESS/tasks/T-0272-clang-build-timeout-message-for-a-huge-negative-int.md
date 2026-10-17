---
id: T-0272
title: Make the "positive and finite" refusal of `timeout_s` in `clang_build.build` and `compiler_version` name `timeout_s` for an `int` too long to convert to text (for example `-10**5000`), keeping the message of every other value unchanged
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0271]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 10, files: 1}
hq: []
---
## Why

`hilclaw.clang_build._check_timeout` (`hilclaw/clang_build.py`, line 501) is the first check of `build` (line 296) and of `compiler_version` (line 411). Its second branch raises:

```python
raise ValueError(f"timeout_s must be positive and finite: {timeout_s!r}")
```

For an `int` with more digits than `sys.get_int_max_str_digits()` (4300 by default), `repr` itself raises `ValueError: Exceeds the limit (4300 digits) for integer string conversion ...`. So `build(..., timeout_s=-10**5000)` still raises a `ValueError` before anything is started, but its message does not name `timeout_s` and says nothing about the time limit. The class is the same, so where ADR-0060 decision 4 places it (a `ValueError` for a setting, S4) does not change. Only the message is wrong.

T-0271 found the same problem in its new "at most" message during review and fixed it there by naming only the bound (`"timeout_s must be at most 2147483.647 s"`, line 507), with a `10**5000` test case. Its `## Result` recorded the remaining case of the older message as a low code follow-up. This task closes it.

**The change, stated.**

- When `timeout_s` is an `int` that `repr` cannot convert to text, the "positive and finite" `ValueError` has a message that contains `timeout_s` and `positive and finite`. It need not show the value. How the executor detects this case is its choice (for example, try the `repr` and fall back to a message without the value on `ValueError`, or compare the number of digits with `sys.get_int_max_str_digits()`), as long as the criteria below hold and no other check changes.
- For every other value the message is unchanged, byte for byte: `"timeout_s must be positive and finite: " + repr(timeout_s)`.
- The error stays a plain `ValueError` (`type(error) is ValueError`) with no `parameter` and no `path_role`. `_parameter("timeout_s")` in `build` stays `TypeError`-only (T-0261, T-0267, T-0268, T-0271 kept this rule; `test_the_existing_value_errors_still_have_no_parameter`, line 2810, asserts it).
- Nothing is started and nothing is created, as today.

What does not change: the type check, the "at most" check and its message, the order of checks, every other check of `build`, the handling after the start, `compiler_version`'s other behaviour, `hilclaw/local_run.py` (see Out of Scope), `verification_build.py`, `timing_build.py` and `standin_profile.py` (they pass on what `build` raises).

This adds no public name, no data-plane member or file, and no value of `condition` or `error.kind`. It records nothing in `ARCHITECTURE/`. It is not an owner-only item under DRIVER §9, and it needs no real `claude` (D16).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, `Task:` trailer, size cap, the test rules of D12).
- `CLAUDE.md`: the standing rules (minimal comments, the language policy of layer 2, branch and merge procedure, test rules ①-⑤).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py`: `_MAX_TIMEOUT_S` (line 40); the first lines of the body of `build` (lines 295-300); `compiler_version` (around line 402-415); `_parameter` (line 462) and `_check_timeout` (lines 501-507). Read `build`'s docstring sentence on what is raised before anything is started only to confirm it stays true; it should need no edit.
- `tests/test_clang_build.py`: the constants and fixtures at the top (lines 41-100: `WRITE`, `VERSION`, `BAD_TIMEOUT_VALUES`, `TIMEOUT`, `stub`, `src`, `out_dir`); `test_timeout_must_be_positive_and_finite` (line 2391); `forbid_start` (line 1939); `test_the_existing_value_errors_still_have_no_parameter` (line 2810); `TOO_LONG_TIMEOUTS` and the tests after it down to `test_a_bad_timeout_keeps_its_message` (lines 2845-2900).
- `PROCESS/tasks/T-0271-clang-build-refuses-a-timeout-too-long-to-wait-for.md`: `## Result`, for the review finding and the follow-up this task closes.

## Acceptance Criteria

1. **The fixed case.** For `timeout_s=-10**5000` (default digit limit), `build(src, out_dir / "kernel.o", timeout_s=..., compiler=stub(WRITE))` and `compiler_version(stub(VERSION), timeout_s=...)` each raise exactly `ValueError` whose message contains both `timeout_s` and `positive and finite`. In both calls the stub is not started and `subprocess.Popen` is not called (use `forbid_start`), nothing is created in the output directory, and the error has no attribute `parameter` and no attribute `path_role`.
2. **The limit is read at call time.** With the digit limit lowered for the test (for example `sys.set_int_max_str_digits(640)`, restored afterwards with `monkeypatch` or `try`/`finally`), a negative `int` with more digits than the lowered limit but fewer than 4300 (for example `-10**700`) gives the same result as criterion 1. Under the same lowered limit, a negative `int` within it (for example `-1`) keeps the exact old message.
3. **Unchanged messages.** For each value of `BAD_TIMEOUT_VALUES` (`0`, `-1`, `-0.5`, `0.0`, `nan`, `inf`) and for a negative `int` of 4300 digits or fewer (for example `-10**4000`), the message equals `"timeout_s must be positive and finite: " + repr(value)` exactly, for both `build` and `compiler_version`.
4. **Order and neighbours.** A `TypeError` value (for example `"10"`) still raises `TypeError` with `parameter == "timeout_s"`. A too-long value (for example `10**5000`) still raises the "at most" message. `-10**5000` together with a bad flag (`flags=("-o", "x")`) or an empty compiler prefix (`compiler=()`) raises the `timeout_s` error, because the time limit is still checked first.
5. **Unchanged behaviour.** Every existing test in `tests/test_clang_build.py`, in `tests/harness/` and in the rest of the suite passes unchanged. No existing test is edited or removed. If an existing test does fail, stop and return BLOCKED with its name. Do not edit it.
6. **Docstrings and comments.** No docstring needs a change unless a sentence becomes wrong. Add no code comment beyond what CLAUDE.md "코멘트 최소화" allows.
7. **Tests** (D12): put the cases of criteria 1 to 4 in `tests/test_clang_build.py` only, including the negative cases above and both branches of the new message (value shown / value not shown). Add no test that targets test code, CI or hook scripts (rule ⑤). The CI gates hold: pytest with coverage (`hilclaw/` lines ≥ 80 %, functions ≥ 80 %), `ruff check` and `ruff format --check` clean.
8. **Scope.** Only the two files in `touchesFiles` change. No change to `hilclaw/local_run.py`, `hilclaw/harness/`, other `hilclaw/` modules, `ARCHITECTURE/`, `PROCESS/` (other than this task file's `## Result`), CI or settings. No new dependency.
9. **Result.** `## Result` records the PR, the review rounds and CI; the language and the reason for it (Python, the language of the module being changed); the size; and the follow-ups. The executor starts no `claude` program (D16).

## Out of Scope

- The same message in `hilclaw/local_run.py` `_check_timeout` (line 278). Its pre-start errors are the subject of the pending ADR-0088 (T-0264, HQ-0027); leave it until that HQ is answered. See Follow-ups.
- Any other `{...!r}` in `clang_build.py` (env keys, flags, compiler path). They format `str`/`bytes`/path values, not `int`s.
- `hilclaw/harness/measurement.py` and any other module's messages.
- A `parameter` on any `ValueError` of `build`.
- Any row, kind or record of `correctness.check`, and any edit of an ADR, `Requirements.md`, `OpenDecisionProposals.md` or `StandardScenarios.md`.

## Follow-ups

- (code, low, after HQ-0027) The same message fix in `local_run._check_timeout`, if the record of OD-18 sub-question 18 part (ma) on `local_run.run` leaves its pre-start `ValueError`s as they are.

## Result
