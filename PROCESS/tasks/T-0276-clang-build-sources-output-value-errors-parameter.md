---
id: T-0276
title: Give the pre-start `ValueError`s of the `sources` and `output` checks of `clang_build.build` the attribute `parameter`, and a `ValueError` raised while `build_verification_executable` makes a tuple of `kernel_sources` the `parameter` "kernel_sources"; leave the no-kernel-source error, the output path tests and `compiler_version` as they are
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0270, T-0274, T-0275]
touchesFiles: [hilclaw/clang_build.py, hilclaw/harness/verification_build.py, tests/test_clang_build.py, tests/harness/test_verification_build.py]
estimatedSize: {loc: 25, files: 2}   # non-test: two `_parameter` kinds, one `except` clause and docstring sentences; tests outside the cap (D4)
hq: []
---
## Why

ADR-0090 (`ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md`, landed `61504e8`, T-0275) placed the named pre-start `ValueError`s of `clang_build.build` for the four settings in S4. It left every pre-start `ValueError` with no `parameter` open. Its N3 lists them as U1 to U6:

- U1: no source.
- U2: one raised inside the check of `sources` by Python or by a handed object's code.
- U3: one raised while the output path is formed or tested.
- U4: one from after the checks, up to and including the start (what `build` passes on from `subprocess`).
- U5: the no-kernel-source error of `build_verification_executable`.
- U6: one raised while `build_verification_executable` makes a tuple of `kernel_sources`.

Its reason (decision 3): an operation of `correctness.check` cannot tell U2, U3 and U6 from U4 by the class. U2, U3 and U6 concern an argument the operation forms, so they would be no row. U4 may hold a setting that `subprocess` refuses. ADR-0090 decision 3 names the way out under "What would let it be placed": "a `parameter` on a `ValueError` of the checks of `sources` and `output` and of the tuple of `kernel_sources`, as T-0274 did for the four settings; U1 would then carry `"sources"` as well, and what stays unnamed would be U5 and U4". Its Consequences list this as a candidate code follow-up, and T-0275's `## Follow-ups` repeat it. This task makes that code change. It places nothing in a row (see Follow-ups).

**The change, stated** (observations at `61504e8`; `hilclaw/clang_build.py` is unchanged since `ecc319f`):

1. **`build`, `sources`.** The step `with _parameter("sources"):` (line 303) tags `TypeError` only. Make it tag `TypeError` and `ValueError`, as the steps for the settings, `env` and `cwd` already do (lines 297-301 and 318-323). So every `ValueError` raised inside `_checked_sources` carries `parameter` `"sources"`, including:
   - U1, "no source file given";
   - a subclass of `ValueError`;
   - one that Python or a handed object's code raises inside the step (for example an iterable of sources whose iterator raises `ValueError`, or a path object whose `__fspath__` raises it).

   An `OSError` of the source path tests keeps `path_role` `"source"` and gets no `parameter`, as now.
2. **`build`, `output`.** The step `with _parameter("output"):` (line 305) wraps only `Path(os.path.abspath(output))`. Make it tag `TypeError` and `ValueError`, so a `ValueError` raised while the output path is formed carries `parameter` `"output"`. One example is a path object whose `__fspath__` raises it.
   - The output path tests (lines 307-316) stay outside that step, unchanged. They test a `Path` that `build` itself made, and `Path.is_dir` / `Path.exists` return `False` for a `ValueError` on Python 3.11 and later.
   - Their `OSError` keeps `path_role` `"output"` and gets no `parameter`, as now.
3. **`build_verification_executable`** (`hilclaw/harness/verification_build.py`, lines 76-82). The `try: kernel_sources = tuple(kernel_sources) except TypeError` block sets `parameter` `"kernel_sources"` on a `TypeError` only. Make it do the same for a `ValueError` (including a subclass) raised while the tuple is made. Leave alone:
   - its own `ValueError("no kernel source file given")` (U5), which keeps no `parameter`, as ADR-0090 decision 3 has it ("what stays unnamed would be U5 and U4");
   - every other exception class raised while the tuple is made, which still passes unchanged with no `parameter`.
4. **What does not change.**
   - The error object stays the same object, with its class, `args` and message unchanged. Only the attribute is added.
   - The order of checks and every message are unchanged.
   - It is still true that nothing is started, no temporary name is drawn and the clock is not read before these checks.
   - A `TypeError` or `ValueError` from anywhere else (binding the call, creating the process) keeps no `parameter`. So do `CompilerNotFoundError`, `CompilerNotStartedError` and every `OSError` with `path_role`.
5. **`compiler_version`** is unchanged. It has no `sources` or `output`, and ADR-0090 decision 4 keeps it a Boundary.
6. **`_parameter`.** The executor decides whether `_parameter` keeps its `kinds` parameter now that every caller passes `(TypeError, ValueError)`. It may drop the parameter if no caller uses the default. Add no module-level public name.

This is an engineering choice inside the two functions that ADR-0090 decision 3 names and leaves to a code task. It adds:

- no module-level public name;
- no data-plane member or file;
- no value of `condition` or `error.kind`.

It records nothing in `ARCHITECTURE/`. It is not an owner-only item under DRIVER §9, and it needs no real `claude`, compiler or container (D16).

**Why this item now.** STATE has no lock, no current task and no next task, and there is no open PR. Every non-DONE task file is BLOCKED on an open HQ (HQ-0013..HQ-0027). PLAN P1-1 continues through the OD-18 work. This task depends on none of those HQs. Its files are touched by no unlanded branch: `claude/T-0225-*` and `claude/T-0233-*` touch other `hilclaw/` modules, and `claude/T-0210-*`, `claude/T-0231-*` and `claude/T-0264-*` touch only `ARCHITECTURE/`. `hilclaw/harness/timing_build.py` waits on HQ-0021 and is not touched.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0276-<slug>`, the PR title with `T-0276`, the trailer `Task: T-0276` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0090-od18-correctness-check-clang-build-named-setting-value-errors.md`: Context N3 and N4, decision 3, and Consequences "Code" only. Do not edit it.
- `hilclaw/clang_build.py` at `61504e8` or later:
  - `build`: its docstring, the paragraph from "Raised before anything is started" to "carry no ``parameter``" (lines 220-261), and the check steps (lines 297-323);
  - `_parameter` (line 465), `_checked_sources` (line 539);
  - `compiler_version` (lines 406-413), only to confirm it is not touched.
- `hilclaw/harness/verification_build.py`: `build_verification_executable`, its docstring and body (lines 41-90).
- `tests/test_clang_build.py`:
  - fixtures `stub`, `src`, `out_dir`, `names` (lines 80-111), `forbid_start` and `refused` (lines 1963-1975);
  - `test_value_errors_of_the_settings_before_the_start_have_their_parameter` (line 1854) and the tests of T-0274 near line 3169 (`test_another_error_raised_inside_a_flags_step_has_no_parameter` and its neighbours), as the pattern;
  - `test_no_source_still_has_no_parameter` (line 3215), `test_other_errors_before_the_start_have_no_parameter` (line 1829) and `test_a_missing_path_still_has_its_role_and_no_parameter` (line 3226);
  - `test_type_errors_keep_their_parameter_through_pickling` (line 1915) as the pattern for a pickling test.
- `tests/harness/test_verification_build.py`: lines 393-475 (the `kernel_sources` `parameter` tests, including `test_other_errors_from_the_iteration_pass_unchanged` and `test_no_kernel_source_carries_no_parameter`).
- `PROCESS/tasks/T-0274-clang-build-setting-value-errors-parameter.md`: "The change, stated" and `## Result` only, for the precedent.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches any file in `touchesFiles`, stop and return BLOCKED (open-PR conflict).
2. **`build`.** Make changes 1 and 2 of "The change, stated":
   - U1 (`sources=[]`) raises the same `ValueError` as on `main`, now with `parameter == "sources"` and still no `path_role`.
   - A `ValueError` raised by a handed object's code inside the `sources` step carries `parameter == "sources"`. Test at least an iterator of sources that raises a `ValueError` (or a subclass) and a path object whose `__fspath__` raises one. It is the very object raised.
   - A `ValueError` raised by an `output` path object's `__fspath__` carries `parameter == "output"` and is the very object raised.
   - These keep no `parameter`, as on `main`:
     - a missing or directory source (`OSError` with `path_role` `"source"`);
     - a missing output directory or a directory output (`path_role` `"output"`);
     - `CompilerNotFoundError`;
     - a `TypeError` or `ValueError` from creating the process.
   - The order of checks is unchanged. For example, `timeout_s=0` with `sources=[]` raises the `timeout_s` error, and `sources=[]` with `compiler=()` raises the `sources` error.
   - Nothing is started and no temporary file is left for any of these.
   - A `ValueError` with `parameter` `"sources"` or `"output"` keeps its `parameter` through `pickle` (a subclass with extra `__init__` arguments, such as `UnicodeEncodeError`, is not required here).
3. **`build_verification_executable`.** Make change 3:
   - A `ValueError` (and a subclass) raised while the iterable of `kernel_sources` is made into a tuple carries `parameter == "kernel_sources"`. It is the very object raised, and `clang_build.build` is not called.
   - No kernel source (`()`, `[]`, an empty generator) raises the same `ValueError` with no `parameter`, as now.
   - A non-`TypeError`, non-`ValueError` from the iteration still passes unchanged with no `parameter`.
   - `test_other_errors_from_the_iteration_pass_unchanged` and `test_no_kernel_source_carries_no_parameter` stay as they are.
   - Through `build_verification_executable`, a `ValueError` from a kernel source's `__fspath__` raised inside `build`'s `sources` step arrives with `parameter == "sources"`, unchanged.
4. **Docstrings.**
   - In `build`'s docstring, rewrite the `parameter` sentence (lines 250-261) so that it is exact:
     - every check, `sources` and `output` included, tags `TypeError` and `ValueError`, including one Python raises inside the check;
     - the no-source error now carries `"sources"`;
     - what still carries no `parameter` is a `TypeError` or `ValueError` from anywhere else, such as binding the call or creating the compiler process.
     Keep every other sentence unless it becomes wrong.
   - In `build_verification_executable`'s docstring, say that a `TypeError` or `ValueError` raised while iterating `kernel_sources` carries `"kernel_sources"`, and that the no-kernel-source `ValueError` carries none.
   - Do not touch the module docstrings unless one of their sentences becomes wrong. Do not change `compiler_version`'s docstring or `hilclaw/harness/timing_build.py`.
5. **Existing tests.** Only assertions that state the old behaviour may change. On `main` the one known in `tests/test_clang_build.py` is `test_no_source_still_has_no_parameter` (line 3215). Change it to expect `"sources"`, and rename it so that its name does not say "no parameter". If the executor finds another assertion that a `ValueError` of the `sources` or `output` step, or of the `kernel_sources` tuple, has no `parameter`, it may change that one too and list it in `## Result`. Do not weaken any other assertion.
6. **Tests (D12).**
   - Happy, error, branch and negative cases for each change.
   - The public functions touched (`build`, `build_verification_executable`) are covered.
   - `hilclaw/` line and function coverage stays at or above 80%.
   - No test of the test code, CI or hooks.
   - The tests need no real compiler: use the existing `stub` fixture, `forbid_start` or patching, as the neighbouring tests do. Tests marked for real `clang` keep their markers.
7. **Code mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0276-<slug>` and open a Draft PR whose title contains `T-0276`.
   - Run the reviewer cycle until Approve, within 7 rounds, and wait for CI green (`pytest`, `ruff`).
   - Squash-merge with `gh pr merge --squash --body`, with `Task: T-0276` as the last line of the body, then delete the branch.
   - Add no comment that restates the code.
8. **Size**: the non-test change stays within 300 lines and 5 files (D4).
9. **Result** records:
   - the PR and the merge commit, and the review rounds with their findings;
   - the language and why, in one line (Python, the modules are Python);
   - the entry check;
   - any existing test edited under criterion 5;
   - the follow-ups.

   The executor starts no `claude` program, compiler or container (D16).

## Out of Scope

- Any `ARCHITECTURE/` edit, including the OD-18 (ma) record that places the newly named errors (see Follow-ups).
- `local_run.run` and everything that waits on HQ-0027 (branch `claude/T-0264-*` is not touched).
- `hilclaw/harness/timing_build.py` and its tests (HQ-0021, T-0210).
- The output path tests' own exceptions, `compiler_version`, U4 (what `build` passes on from `subprocess`) and U5 (the no-kernel-source error).
- Any new value of `error.kind` or `condition`, any data-plane member, any new external dependency, any change to CI, `.claude/` or settings files.

## Follow-ups

- (doc, after this lands) An OD-18 sub-question 18 part (ma) record on the `ValueError`s that now carry `parameter` `"sources"`, `"output"` or `"kernel_sources"`, and on what stays unnamed (U4, U5), planned against the code as landed. Its edits follow the recording rules of `ARCHITECTURE/Requirements.md` ("행 형식"), of the `ARCHITECTURE/OpenDecisionProposals.md` header ("기록 규칙") and of the first paragraph of `ARCHITECTURE/StandardScenarios.md` §검사 결과. It can also take up the two Nits listed in T-0275's `## Follow-ups`. It must keep clear of the unlanded branches `claude/T-0264-*`, `claude/T-0210-*` and `claude/T-0231-*`, which edit the same OD-18 lines.

## Result

- Outcome: DONE. PR https://github.com/myungjoo/HIL-Claw/pull/175 was squash-merged as `1d61696` with `gh pr merge --squash --body` (last body line `Task: T-0276`). The branch `claude/T-0276-clang-build-sources-output-value-errors-parameter` is deleted on the remote and locally.
- Entry check: no open PRs before the first edit; `git log origin/main --grep='^Task: T-0276'` found nothing (fresh start).
- Change: `hilclaw/clang_build.py` — the `sources` and `output` check steps set `parameter` on `TypeError` and `ValueError` (output path tests stay outside the `output` step; `OSError`s with `path_role` get no `parameter`); `_parameter` dropped its `kinds` argument. `hilclaw/harness/verification_build.py` — the `kernel_sources` tuple step uses `except (TypeError, ValueError)`; the no-kernel-source `ValueError` (U5) still has no `parameter`. Docstrings of `build` and `build_verification_executable` rewritten per criterion 4. Not touched: `compiler_version`, module docstrings, `timing_build.py`. Size: 2 non-test files, +25/-23.
- Language: Python, because both modules are Python.
- Existing tests edited (criterion 5): `test_no_source_still_has_no_parameter` renamed to `test_no_source_names_the_sources` and expects `"sources"`; `test_unusable_sources` also asserts `parameter == "sources"` on `[]`/`()`; the replacement `_parameter` in `test_the_parameter_leaves_the_error_otherwise_unchanged` lost its unused `kinds` default (round 1 Nit).
- New tests: happy (iterator raising `ValueError`/subclass/`UnicodeError`; source and output `__fspath__` raising), negative (`RuntimeError` gets no `parameter`; directory source/output keeps `path_role`, no `parameter`), check order, pickling, and the `build_verification_executable` `"kernel_sources"` cases (`build` not called). The new and changed tests fail on the old code (19 failures) and pass on the new.
- Local verification: pytest 22644 passed, 482 skipped; `ruff check` and `ruff format --check` clean; `hilclaw/` line coverage 99%. CI on head `fa020e6` all green.
- Review: 2 rounds with a context-isolated `dev-reviewer` — round 1 Approve with one Nit (fixed in `fa020e6`) and one Info (CI pending); round 2 Approve.
- Follow-ups: (doc) an OD-18 sub-question 18 (ma) record on the `ValueError`s that now carry `"sources"`, `"output"` or `"kernel_sources"`, and on what stays unnamed (U4, U5); it can also take up T-0275's two Nits and must keep clear of the unlanded branches `claude/T-0264-*`, `claude/T-0210-*`, `claude/T-0231-*`.
