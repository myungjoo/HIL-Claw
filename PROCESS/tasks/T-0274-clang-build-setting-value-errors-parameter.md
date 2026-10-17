---
id: T-0274
title: Give the pre-start `ValueError`s of `clang_build.build` for a setting (`timeout_s`, `flags`, `trailing_flags`, `compiler`) the attribute `parameter`, as T-0267 did for `env` and `cwd`; leave `sources`, `output` and `compiler_version` as they are
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0267, T-0268, T-0271, T-0272, T-0273]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 30, files: 1}   # non-test: four `_parameter` calls and the docstring sentences of `build`; tests outside the cap (D4)
hq: []
---
## Why

ADR-0089 (`ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`, landed `a4a8e7f`, T-0273) left one kind of pre-start error of `clang_build.build` open: a `ValueError` with no `parameter`. Its decision 5 says the operation of `correctness.check` "cannot tell them apart by the class". Such an error may be a refused setting (S4), the "no kernel source" error of `build_verification_executable` (no row), or something `subprocess` passes on. The decision then names what would let these errors be placed: "a `parameter` on V2 to V7 — `"timeout_s"`, `"flags"`, `"trailing_flags"` or `"compiler"` —, as T-0267 did for `env` and `cwd`; a later record then places them. That is a code change of the code task's". T-0273's `## Result` lists this as its code follow-up. This task makes that code change. It places nothing in a row (see Follow-ups).

The V-numbers are those of ADR-0089 P3. On `main` (`f243f0a`) these are the pre-start `ValueError`s of `build` that carry no `parameter`:

- V2: `timeout_s` is not a positive finite number. V3: `timeout_s` is above (2**31 - 1) / 1000 s. Both come from `_check_timeout`.
- V4: the compiler prefix is empty (`_resolve`).
- V5: a flag or trailing flag sets the output (`_checked_flags`).
- V6: a flag, a trailing flag or a compiler part after the first contains a NUL character. V7: on POSIX, `os.fsencode` cannot convert such a flag or part and raises `UnicodeEncodeError`, a `ValueError` subclass. Both come from `_check_argument`, called from `_checked_flags` and `_resolve`.
- V1 is a different case: "no source file given" (`_checked_sources`). It concerns the sources, an argument the operation forms, not a setting. This task leaves it with no `parameter`.

All of these are raised inside `build`'s `with _parameter("timeout_s"):`, `with _parameter("flags"):`, `with _parameter("trailing_flags"):` and `with _parameter("compiler"):` blocks (`hilclaw/clang_build.py` lines 295-300 and 316-317). Those blocks use the default `kinds=(TypeError,)` of `_parameter` (line 462). T-0267 made the `env` and `cwd` steps use `_parameter(name, (TypeError, ValueError))` (lines 318-321).

**The change, stated.**

1. In `build`, the four steps `timeout_s`, `flags`, `trailing_flags` and `compiler` tag both `TypeError` and `ValueError`, as the `env` and `cwd` steps already do. So every `ValueError` raised inside those steps carries `parameter` set to the step's name, including a subclass such as `UnicodeEncodeError` and one that Python or the code of a handed object raises inside the step (for example a custom iterable of flags whose iterator raises `ValueError`). The error object stays the same object, with its class, `args` and message unchanged. Only the attribute is added.
2. The `sources` and `output` steps keep tagging `TypeError` only. V1 and every `OSError` of those steps keep their current attributes (`path_role` and no `parameter`).
3. `CompilerNotFoundError` is not a `ValueError` and stays without `parameter`.
4. `compiler_version` is unchanged. It calls `_check_timeout` and `_resolve` with no `_parameter` context today, and its errors carry no `parameter`. ADR-0089 decision 6 keeps it a Boundary, and existing tests assert this (`test_type_errors_of_compiler_version_have_no_parameter`, `test_malformed_compiler_argument`, `test_compiler_version_refuses_a_bad_part_before_the_start`, `assert_unprintable_timeout_refused`). Do not change it.
5. Order of checks, messages and classes are unchanged. It is still true that nothing is started, no temporary name is drawn and the clock is not read before these checks.
6. The executor decides whether `_parameter` keeps its `kinds` parameter, or whether the six steps call it with explicit kinds.

This is an engineering choice inside `build` that ADR-0060 decision 4, ADR-0087 decision 5 and ADR-0089 decision 5 leave to the code. It adds no module-level public name. It adds no data-plane member or file, and no value of `condition` or `error.kind`. It records nothing in `ARCHITECTURE/`. It is not an owner-only item under DRIVER §9, and it needs no real `claude` (D16).

**Why this item now.** STATE has no lock, no current task and no next task, and there is no open PR. Every non-DONE task file is BLOCKED on an open HQ (HQ-0021..HQ-0027). PLAN P1-1 continues through the OD-18 work. This task depends on none of those HQs and touches no file of a BLOCKED task. The BLOCKED code tasks T-0225, T-0233 and T-0243 touch other `hilclaw/` modules. T-0264 (HQ-0027) is the `local_run.run` side and touches only `ARCHITECTURE/`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0274-<slug>`, the PR title with `T-0274`, the trailer `Task: T-0274` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md`: Context P3 and Decision 5 and 6 only. Do not edit it.
- `hilclaw/clang_build.py` at `f243f0a` or later:
  - `build`: its docstring, the paragraph from "Raised before anything is started" to "carry no ``parameter``" (lines 221-258), and the check steps (lines 295-321);
  - `compiler_version` (lines 404-430);
  - `_parameter` (line 462), `_check_timeout`, `_checked_flags`, `_check_argument`, `_checked_sources` and `_resolve` (lines 501-578).
- `tests/test_clang_build.py`:
  - constants and fixtures: `BAD_TIMEOUT_VALUES` (line 49), `stub`, `src`, `out_dir`, `names` (lines 80-111), `forbid_start` and `refused` (lines 1939-1960), `forbid_the_temporary_and_the_clock`, `placed`, `PLACES` and `REFUSED_ARGUMENTS` (lines 2534-2575);
  - the tests listed in Acceptance Criterion 4;
  - `test_type_errors_keep_their_parameter_through_pickling` (line 1891) and `test_env_and_cwd_errors_keep_their_parameter_through_pickling` (line 2343), as the pattern for the pickling test.
- `PROCESS/tasks/T-0267-clang-build-env-and-cwd-parameter.md`, "The change, stated" and `## Result` only, for the precedent.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build`.** Make the change described in "The change, stated":
   - Each of V2 to V7 raised by `build` carries `parameter`. The value is `"timeout_s"` for V2 and V3, `"compiler"` for V4 and for V6/V7 in a compiler part, and `"flags"` or `"trailing_flags"` for V5 and for V6/V7 in a flag. The class (`type(error)`), `args` and message are as on `main`. For V7 the error is the very object `os.fsencode` raised.
   - V1 (`sources=[]`), every `OSError` with `path_role`, `CompilerNotFoundError`, `CompilerNotStartedError`, and a `TypeError` or `ValueError` from creating the process (`subprocess.Popen` patched to raise it) carry no `parameter`, as on `main`.
   - The order of checks is unchanged. For example, `timeout_s=0` together with a NUL flag raises the `timeout_s` error, and a NUL flag together with a NUL compiler part raises the `flags` error.
   - Add no module-level public name. Add no comment that restates the code.
3. **Docstrings.** In `build`'s docstring, rewrite the sentence about `parameter` so that it is exact:
   - `TypeError` is tagged by the checks of `sources` and `output`;
   - `TypeError` and `ValueError` (including one Python raises inside the check) are tagged by the checks of `timeout_s`, `flags`, `trailing_flags`, `compiler`, `env` and `cwd`;
   - the `ValueError` for no source, and a `TypeError` or `ValueError` from anywhere else (such as binding the call or creating the compiler process), carry no `parameter`.

   Keep every other sentence unless it becomes wrong. "the UnicodeEncodeError it raises is passed on" stays true, because it is the same object. Touch the module docstring only if one of its sentences becomes wrong. `compiler_version`'s docstring ("with the same errors") may gain a short clause saying its errors carry no `parameter`, if the executor or the reviewer finds that the sentence is otherwise wrong; nothing more. Do not change the docstrings of `hilclaw/harness/verification_build.py` or `timing_build.py`. They say only that what `build` raises is passed on unchanged, which stays true.
4. **Existing tests that may be edited.** These assertions on `main` (`f243f0a`) state that one of V2-V7 raised by `build` has no `parameter`. Only they may be edited, in `tests/test_clang_build.py`:
   - `test_checks_other_than_paths_have_no_role` (line 1675): the `else` branch, for the `{"timeout_s": 0}` row only; expect `"timeout_s"`.
   - `test_other_errors_before_the_start_have_no_parameter` (line 1829): remove the three `ValueError` rows (`timeout_s: 0`, `compiler: ()`, `flags: ("-o", "x.o")`) from its parametrisation and cover them in a new test that asserts their `parameter`. The remaining rows stay.
   - `test_earlier_value_errors_come_before_env_and_cwd` (line 2293): expect the parameter named by the row's key.
   - `test_malformed_compiler_argument` (line 2448): the `build` `ValueError` branch; expect `"compiler"`. The `compiler_version` assertion stays.
   - `test_a_nul_in_an_argument_is_refused_before_the_start` (line 2576) and `test_an_unencodable_argument_is_the_error_of_fsencode` (line 2596): expect `parameter == place`.
   - `test_an_output_flag_with_a_nul_keeps_the_output_message` (line 2693) and `test_the_first_bad_flag_in_the_sequence_is_reported` (line 2722, its `ValueError` half): expect `keyword`.
   - `test_a_bad_timeout_comes_before_a_nul_flag` (line 2708, its `ValueError` half), `test_a_timeout_too_long_to_wait_for_is_refused_before_the_start` (line 2854), `test_a_timeout_too_long_is_checked_before_the_other_arguments` (line 2907) and `test_an_unprintable_timeout_is_checked_before_the_other_arguments` (line 3006): expect `"timeout_s"`.
   - `assert_unprintable_timeout_refused` (line 2931): expect `"timeout_s"` for the `build` error. The `compiler_version` error keeps no `parameter`.
   - `test_the_existing_value_errors_still_have_no_parameter` (line 2810): it may be renamed, and it may gain an expected-parameter column, so that it asserts the parameter of each of its four rows.

   In each of these, only the `parameter` assertion may change, from `not hasattr(..., "parameter")` to an equality with the expected name. Every other assertion of these tests stays (class, message, `path_role`, not started, no files). No other existing test may be edited, renamed or deleted, including those under `tests/harness/`. If another existing test fails, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
5. **New tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures or helpers.
   - **Happy path.** A build with valid settings still succeeds, and its result has no `parameter` (the existing `test_successful_build_carries_no_parameter` covers this; leave it).
   - **Branch.** For each of V2 (`0`, `nan`, `-1`), V3 (`2**31`), V4 (`()`, `[]`), V5 (`flags=("-o", "x")`, `trailing_flags=("-ox",)`), V6 (NUL in a flag, in a trailing flag, in a compiler part after the first) and V7 (POSIX only, a lone surrogate in each of those places):
     - `parameter` is the expected name;
     - `type(error)` is as on `main`;
     - `subprocess.Popen` is not called (`forbid_start`);
     - `names(out_dir) == []`.
   - **Inside a step.** A `flags` or `trailing_flags` iterable whose iterator raises `ValueError` carries that parameter, and the error is the same object. A non-`ValueError`, non-`TypeError` exception raised by such an iterator (for example `RuntimeError`) carries no `parameter`.
   - **Negative, nothing else changes.**
     - V1 (`sources=[]`) has no `parameter`.
     - `FileNotFoundError` for a missing source or output keeps its `path_role` and has no `parameter`.
     - `CompilerNotFoundError` has no `parameter`, including for a NUL or surrogate first part (`test_a_bad_first_compiler_part_is_still_not_found` stays as it is).
     - A `ValueError` raised by a patched `Popen` with valid settings has no `parameter`.
     - Each V2, V4, V6 error of `compiler_version` has no `parameter`.
   - **Pickling.** A pickled and loaded V2 `ValueError`, a V5 `ValueError` and (POSIX) a V7 `UnicodeEncodeError` keep class, `args` and `parameter`.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
6. **Local checks.** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only `sys.executable` and the stub compilers the suite already writes, and the real `clang` only where the suite already does. Start no `claude` process in any form (D16).
7. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0274-<slug>` with a Draft PR whose title contains `T-0274`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green (Python 3.11 and 3.14 jobs, coverage gate, test presence);
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0274`;
   - delete the branch.
8. **Result.** Record in `## Result`:
   - the PR and the review rounds;
   - CI and local test results;
   - the language (Python, the language of the module being changed) with a one-line reason;
   - which lines now tag `ValueError` for the four steps;
   - every existing test edited under criterion 4, with what changed;
   - the size and the follow-ups.
9. **Size** within DRIVER §5: at most 300 changed lines and at most 5 files, excluding tests.

## Out of Scope

- Any `ARCHITECTURE/` file. In particular, no record of which row the newly named `ValueError`s place: that is a later doc task (Follow-ups). Also the files of T-0264 (ADR-0088).
- A `parameter` on V1, on the `output` step's errors, on `CompilerNotFoundError` or on any error of `compiler_version`.
- Any change to the order, classes or messages of the checks; any new check.
- `hilclaw/local_run.py` (its pre-start errors wait on HQ-0027, T-0264); `hilclaw/harness/` (`verification_build.py`, `timing_build.py`, `standin_profile.py` pass on what `build` raises); the `cpu_standin` operation of `correctness.check` (HQ-0026).
- Starting `claude` in any form (D16).

## Follow-ups

- (doc) An OD-18 sub-question 18 part (ma) record: what the named `ValueError`s of `build` with `parameter` `"timeout_s"`, `"flags"`, `"trailing_flags"` or `"compiler"` make true for `correctness.check`. ADR-0089 decision 5 names this "a later record then places them". The record follows the recording rules of `ARCHITECTURE/Requirements.md` ("행 형식"), of the `ARCHITECTURE/OpenDecisionProposals.md` header ("기록 규칙") and of the first paragraph of `ARCHITECTURE/StandardScenarios.md` §검사 결과. It must be planned after this task lands, against the code as landed. It must not overlap the unlanded T-0264 branch, which edits the same OD-18 lines.
- (code, after HQ-0027) The same change in `local_run.run`, if the record on its pre-start errors asks for it.

## Result

- PR #174 (https://github.com/myungjoo/HIL-Claw/pull/174), squash-merged as ecc319f5ed8f967507af5842766570484fd79a9a on main; branch `claude/T-0274-clang-build-setting-value-errors-parameter` deleted. The squash message ends with `Task: T-0274`.
- Entry check: `gh pr list` showed no open PR before the first edit.
- Review: 2 rounds, both Approve (https://github.com/myungjoo/HIL-Claw/pull/174#issuecomment-6236232459, #issuecomment-6236268876). Round 1 had one Low (docstring precision: a `ValueError` Python raises inside the `sources`/`output` checks was only covered by "anywhere else"); fixed in 68ff183 by naming "any `ValueError` from the checks of `sources` and `output`, such as the one for no source". Round 2: no findings.
- CI green on 68ff183 (run 39047599513): Python 3.11 and 3.14, coverage gate (lines 99.58%, functions 100%), test presence, shellcheck, clang. Local (Windows, Python 3.14): full pytest 22624 passed, 482 skipped; `ruff check` and `ruff format --check` clean. POSIX-only V7 cases ran on CI only.
- Language: Python, the language of the module being changed (`hilclaw/clang_build.py`).
- Implementation: `_parameter` keeps `kinds=(TypeError,)`. `build` now calls `_parameter("timeout_s", (TypeError, ValueError))` (line 297), `_parameter("flags", ...)` (line 299), `_parameter("trailing_flags", ...)` (line 301) and `_parameter("compiler", ...)` (line 318), as `env`/`cwd` already did. `sources` and `output` still tag `TypeError` only; `compiler_version` code unchanged. `build`'s docstring sentence on `parameter` rewritten per criterion 3; `compiler_version`'s docstring gained "except that they carry no ``parameter``" (otherwise "with the same errors" became wrong). Module docstring unchanged.
- Existing tests edited (criterion 4, `parameter` assertion only): `test_checks_other_than_paths_have_no_role` (new `elif` for the `timeout_s: 0` row → `"timeout_s"`); `test_other_errors_before_the_start_have_no_parameter` (three `ValueError` rows removed, covered by new `test_value_errors_of_the_settings_before_the_start_have_their_parameter`); `test_earlier_value_errors_come_before_env_and_cwd` (→ row key); `test_malformed_compiler_argument` (`build` branch → `"compiler"`, `compiler_version` assertion kept); `test_a_nul_in_an_argument_is_refused_before_the_start` and `test_an_unencodable_argument_is_the_error_of_fsencode` (→ `place`); `test_an_output_flag_with_a_nul_keeps_the_output_message` and `test_the_first_bad_flag_in_the_sequence_is_reported` (→ `keyword`); `test_a_bad_timeout_comes_before_a_nul_flag`, `test_a_timeout_too_long_to_wait_for_is_refused_before_the_start`, `test_a_timeout_too_long_is_checked_before_the_other_arguments`, `test_an_unprintable_timeout_is_checked_before_the_other_arguments` (→ `"timeout_s"`); `assert_unprintable_timeout_refused` (`build` error → `"timeout_s"`, `compiler_version` error still none); `test_the_existing_value_errors_still_have_no_parameter` renamed `test_the_existing_value_errors_have_their_parameter` with a `parameter` column. No other existing test edited; all pass, including `tests/harness/`.
- New tests: V2-V7 branch cases (parameter, class, no start, no temporary/clock, empty output dir); error otherwise unchanged (class/args/message equal to an untagged run); `ValueError` inside a flags iterator tagged and same object, `RuntimeError` not tagged; check order; negatives (no source, missing source/output path role, `CompilerNotFoundError`, `Popen` `ValueError`, `compiler_version` V2/V4/V6/V7); pickling of V2, V5, V7.
- Size: `hilclaw/clang_build.py` +19/-16 (1 non-test file); `tests/test_clang_build.py` +334/-24.
- Follow-ups: unchanged (the doc OD-18 (ma) record placing the newly named `ValueError`s; the `local_run.run` analogue after HQ-0027). None new.
- No `claude` was started (D16).
