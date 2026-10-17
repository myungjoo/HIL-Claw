---
id: T-0259
title: Make every OSError from the path tests of `clang_build.build` say whether it came from a source or from the output, so both are told from the other lines before the start
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0255, T-0257]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 40, files: 1}
hq: []
---
## Why

ADR-0083 decision 3 leaves a plain `OSError` of `clang_build.build` without a row of `correctness.check`. ADR-0084 decision 4 keeps it open now that every plain `OSError` comes from before the start. Two of their reasons are about what `build` states:

- **"One class serves two rows."** `FileNotFoundError` and `IsADirectoryError` come from the source test (S5) and from the output test (S3). Any other `OSError` the tests themselves raise (ADR-0083 P3 (a), for example a `PermissionError` from `Path.is_file` on 3.11) can come from both.
- **"Sources no row names."** The same classes can come from `os.getcwd` inside `os.path.abspath` (P3 (b)), `os.urandom` inside `secrets.token_hex` (P3 (c)), `started = time.monotonic()` (P3 (d)) and the search for the compiler (P3 (e)). A `FileNotFoundError` from `os.getcwd` has the class of a missing source.

The first thing both records name under "What would let it be placed" is: "A code change of `clang_build.build` that tells, by class or by a member of the error, the source tests from the output tests, and both from the other lines before the start (P3 (b) to (e))." ADR-0084 Consequences say that "a code task may tell the source tests from the output tests (decision 4)", that names and modules are the code task's, and that "this record binds no code". T-0257 and T-0258 list this item as their next code follow-up.

**The change, stated.** Tell them apart by a member, not by a class. The classes stay what they are:

- `test_no_start_for_an_error_before_the_start` asserts `type(caught.value) is FileNotFoundError`;
- `hilclaw/harness/verification_build.py` and `timing_build.py` document `FileNotFoundError` as passed on unchanged, and their tests catch the built-in classes.

So add one attribute, `path_role`, to every `OSError` that leaves a path test of `build`, and to no other error:

- `"source"` for an `OSError` from the tests of a source in `_checked_sources`, meaning `path.is_file()`, `path.is_dir()` and the `FileNotFoundError` or `IsADirectoryError` raised after them;
- `"output"` for an `OSError` from the tests of the output in `build`, meaning `target.parent.is_dir()`, `target.parent.exists()`, `target.is_dir()` and the `FileNotFoundError`, `NotADirectoryError` or `IsADirectoryError` raised after them.

What it covers:

- For the errors `build` raises itself, the attribute is set on the object before it is raised.
- For an `OSError` that a test call raises, catch it, set the attribute on that same object, and re-raise it with a bare `raise`. Its class, `args`, `errno`, `filename`, traceback and chain stay unchanged. This is the same kind of addition to a foreign exception as T-0253's note, but here it is a member and not text.
- `os.path.abspath` stays outside that scope, for both the sources and the output. So an `OSError` from `os.getcwd` gets no `path_role`.
- Nothing from `_resolve`, `secrets.token_hex`, `time.monotonic` or after the `try` gets one either.

A caller reads it as `getattr(error, "path_role", None)`. `None` means the error came from no path test. The five error classes of the module never carry it.

This is an engineering choice inside `build`, which ADR-0083 and ADR-0084 leave to the code task. It adds:

- no new module-level public name: the values are the two plain strings, documented in `build`'s docstring;
- no data-plane member or file;
- no value of `condition` or `error.kind`.

It places no row of `correctness.check`. Whether S5 and S3 now hold for these errors is a later doc task (Follow-ups). It is not an owner-only item under DRIVER §9.

Nothing else changes:
- the classes, messages and order of every check before the start;
- `ValueError`, `TypeError` and `CompilerNotFoundError`;
- the five error classes and their members;
- results, `duration_s`, the temporary file and its removal;
- the module docstring, unless one of its sentences becomes wrong.

**Existing tests checked at planning time (`207e34b`).** No existing test pins the absence of an attribute on these errors. The tests that catch the built-in classes still pass, because the classes are unchanged. Among them:
- `test_no_start_for_an_error_before_the_start` (line 602);
- `test_unusable_sources` (line 1485);
- `test_missing_output_directory`, `test_output_parent_is_a_regular_file` and `test_output_is_a_directory` (lines 1493-1517);
- the path tests in `tests/harness/test_verification_build.py` and `tests/harness/test_timing_build.py`.

The name `path_role` occurs nowhere in `hilclaw/` or `tests/` (`grep -rn path_role hilclaw tests`).

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). PLAN P1-1 continues through the OD-18 work. This task depends on none of those HQs. No blocked task touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`. Of the HQ-0026 work, `compiler_version` and the `cpu_standin` operation are out of scope here.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0259-<slug>`, the PR title with `T-0259`, the trailer `Task: T-0259` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0083-od18-correctness-check-plain-oserror-before-start.md`, Context P3 and P4 (lines 22-30) and decision 3 (from line 46), especially "What would let it be placed". Do not edit it.
- `ARCHITECTURE/decisions/ADR-0084-od18-correctness-check-clock-error-after-end.md`, decision 4 (lines 54-63) and Consequences "Code" (line 97). Do not edit it.
- `hilclaw/clang_build.py` at `207e34b` or later:
  - `build`'s docstring (lines 205-258), especially the sentence "Raised before anything is started: …";
  - the lines from `_check_timeout(timeout_s)` to `started = time.monotonic()` (lines 259-274);
  - `_checked_sources` (lines 428-444) and `_resolve` (lines 447-462).
- `tests/test_clang_build.py`:
  - the fixtures `stub`, `src`, `out_dir` and `names` (lines 80-112), and `FILE_ERRORS` (line 331);
  - `test_no_start_for_an_error_before_the_start` (line 602);
  - `failing_clock` (line 948), `test_failed_clock_before_the_start_stays_plain` (line 1101) and `test_errors_outside_the_run_are_not_run_errors` (line 1114);
  - `test_unusable_sources` with its parameters (lines 1472-1490), and the three output tests (lines 1493-1517).
- `PROCESS/tasks/T-0253-clang-build-keeps-non-oserror-over-failed-removal.md` "Result", for the precedent of adding to a foreign exception.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build` and `_checked_sources`.** Make the change as "The change, stated" says:
   - Every `OSError` that leaves a path test of a source has `path_role == "source"`. Every one that leaves a path test of the output has `path_role == "output"`.
   - An `OSError` that a test call raises is the same object after the change (`is`). It keeps its class and its other attributes, and it is re-raised with a bare `raise`.
   - No other error that `build` raises or passes on has the attribute. That covers errors from `os.path.abspath`, `_resolve`, `shutil.which`, `secrets.token_hex`, `time.monotonic`, the run, the stat test of the artefact, the move and the removal.
   - Keep the order of checks and every message. Add no new module-level public name. Add no comment that restates the code.
3. **Docstrings.**
   - Extend `build`'s sentence "Raised before anything is started: …" to state:
     - `path_role` and its two values;
     - that it is set on any `OSError` from those path tests, including one the test itself raises;
     - that an `OSError` from anywhere else carries no `path_role`.
   - Change no other sentence of `build`'s docstring unless it becomes wrong.
   - Touch the module docstring only if one of its sentences becomes wrong.
   - The docstrings of the five classes do not change.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures.
   - **Edits to existing tests are allowed only as additions of assertions or parameters.** No existing assertion may be removed or changed, and no existing test may be renamed or deleted. Additions are allowed only to:
     - `test_no_start_for_an_error_before_the_start`;
     - `test_unusable_sources`;
     - the three output tests;
     - `test_failed_clock_before_the_start_stays_plain`;
     - `test_errors_outside_the_run_are_not_run_errors`.

     Every other existing test, including those under `tests/harness/`, must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
   - **Happy path.** A missing source (`FileNotFoundError`) and a directory as source (`IsADirectoryError`) have `path_role == "source"`, and their `type` is still the built-in class. A source list whose second entry is missing has it too.
   - **Branch, the output.** These have `path_role == "output"`, with their built-in classes:
     - a missing output directory (`FileNotFoundError`);
     - a parent that is a regular file (`NotADirectoryError`);
     - an output that is a directory (`IsADirectoryError`).
   - **Branch, an error the test raises.** These are the same object (`is`), with their class and `errno` kept:
     - Patch `clang_build.Path.is_file` to raise a `PermissionError` for the source. The raised error has `path_role == "source"`.
     - Patch `clang_build.Path.is_dir` (or `exists`) to raise a `PermissionError` for the output's parent, with sources that pass. The raised error has `path_role == "output"`.
   - **Branch, the other lines before the start.** Each of these raises an `OSError` with no `path_role` attribute (`not hasattr(error, "path_role")`):
     - `os.path.abspath` raising an `OSError` (for example a `FileNotFoundError`, which has the class of a missing source) for a source and for the output;
     - `secrets.token_hex` raising;
     - `shutil.which` raising;
     - `time.monotonic` failing before the start (`failing_clock(reads=0)`).

     In each, no compiler is started and the output directory stays as it was.
   - **Negative.**
     - None of `CompilerNotStartedError`, `CompilerRunError`, `ArtefactNotPlacedError`, `ArtefactNotCheckedError` and `TemporaryNotRemovedError`, as `build` raises them in the existing tests you extend, has `path_role`.
     - `ValueError`, `TypeError` and `CompilerNotFoundError` from before the start have no `path_role`.
     - A successful build still returns a `BuildResult`.
   - **Pickling.** A pickled and loaded source error and output error keep their class, message and `path_role`.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only the stub compilers the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0259-<slug>` with a Draft PR whose title contains `T-0259`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0259`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason. State from the code which lines now set `path_role` and to which value.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/`: ADR-0078 to ADR-0085, Requirements, OpenDecisionProposals and StandardScenarios.
- Placing any row of `correctness.check`. This covers S5 or S3 for an error with `path_role`, a row for the sources no row names (P3 (b) to (e)), and the `CompilerRunError` branch with `timed_out` false and `returncode` `None`.
- New error classes, or a changed class for any error before the start.
- Taking `os.getcwd` out of the path forming. That is "a step of the operation's own" (ADR-0083 decision 3), which this task does not take.
- The callers of `build`: `hilclaw/harness/verification_build.py`, `timing_build.py` and `hilclaw/standin_profile.py`, and their tests. Also out: `compiler_version` and the `cpu_standin` operation of `correctness.check` (HQ-0026).

## Follow-ups

- (doc) A record under OD-18 sub-question 18 part (ma) on what `path_role` makes true. With this change, ADR-0083 decision 3's "One class serves two rows" no longer holds as written for an error with `path_role`, and ADR-0084 decision 4 cites it. The record weighs:
  - S5 for `"source"` and S3 for `"output"`, including a test that raises an `OSError` of its own (for example a refused `stat`);
  - whether the rows' wordings ("no longer a regular file", "cannot be made or written") cover such an error;
  - which sentences of ADR-0060 decision 4, ADR-0080 decision 4, ADR-0083 and ADR-0084 become less exact.

  The sources with no `path_role` (P3 (b) to (e)) stay as they are.

## Result
