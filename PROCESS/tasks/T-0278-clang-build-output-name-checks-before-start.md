---
id: T-0278
title: Make `clang_build.build` refuse, before the start, an output file name that holds a NUL character or (on POSIX) cannot be converted by `os.fsencode`, with the class `subprocess` would raise and `parameter` "output"
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0276, T-0277]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 40, files: 2}
hq: []
---
## Why

ADR-0091 (T-0277, landed `d993253`) left exactly one kind of pre-start `ValueError` of `clang_build.build` unnamed. Its name there is U4: a `ValueError` raised after the checks, up to and including the start, which holds what `build` passes on from `subprocess`. ADR-0091 decision 3 keeps U4 open because what `subprocess` raises was not read. Its Consequences and T-0277's `## Follow-ups` name a candidate follow-up: a code change that makes `build` refuse such a value in a named check before the start.

One such value can be read from the code at `d993253` without reading `subprocess` into a row:

- The `output` step of `build` (inside `_parameter("output")`) only forms the absolute path.
- The tests after it run `target.parent.is_dir()`, `target.parent.exists()` and `target.is_dir()`. A NUL character (or, on POSIX, a character `os.fsencode` cannot convert) **in a parent directory** makes `parent.is_dir()` false. That raises `FileNotFoundError` with `path_role` `"output"`, as `test_a_nul_in_a_path_keeps_the_path_error` confirms.
- The same character **in the file name only** passes these tests: `pathlib` answers `is_dir()` false for a path it cannot test. The temporary path is then built from `target.stem` and `target.suffix`, so the character reaches the command line. `subprocess.Popen` then refuses it with a `ValueError` (embedded null byte) or, on POSIX, a `UnicodeEncodeError`. That error carries no `parameter`, so it is part of U4.

T-0268 and T-0269 already refuse the same defects in flags, compiler parts (`clang_build`) and arguments (`local_run`) before the start, with the class `subprocess` would raise. This task does the same for the output file name. U4 then no longer holds a value the operation formed itself (the artefact path is the operation's own: ADR-0060 decision 3, ADR-0091 decision 1). Whether that is all of U4 is for a later record to say, not this task.

This is a code change only. It records no row of `correctness.check`, adds no data-plane value and decides nothing of OD-18. The row of the new named error follows ADR-0091 decision 2 (a `ValueError` with `parameter` `"output"` gets no row), and confirming that in the record is a follow-up doc task. No owner-only item is touched (DRIVER §9). Nothing needs a real `claude`, a real compiler or a board (D16): the tests use the existing stub compiler and `forbid_start`.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 (line 72; executor procedure, resume rule, time limit) and §5 (lines 86-114; task file format, naming, the `Task: T-0278` trailer in commits and as the last line of the PR body, size cap, D12 test rules).
- `CLAUDE.md`, the standing rules. In particular: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책" (one line in the commit body on the language choice), "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py` at `d993253`:
  - the docstring of `build` (lines 207-297), especially "Raised before anything is started", the sentence on NUL characters and `os.fsencode` in flags and compiler parts, the `parameter` paragraph and "The check of `output` forms its absolute path; the tests of that path below are not part of it";
  - the check steps and output path tests (lines 298-324);
  - the temporary name and command (the lines right after the `cwd` check);
  - `_parameter` (line 466) and `_check_argument` (line 533).
- `tests/test_clang_build.py`: `forbid_start` (line 1963), `test_a_nul_in_an_argument_is_refused_before_the_start` (line 2597), `test_a_nul_in_a_path_keeps_the_path_error` (line 2842), `RaisingPath` (line 3240) and `test_a_value_error_from_the_output_path_object_names_the_output` (line 3291). Follow their style.
- `ARCHITECTURE/decisions/ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md`: Context K1 and K4, decisions 2 and 3, Consequences ("Code"). Read only; do not edit.
- `PROCESS/tasks/T-0268-clang-build-argument-checks-before-start.md`: `## Acceptance Criteria` only, as the earlier change of the same shape.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): run `gh pr list`. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict risk).
2. **The change.** `build` checks the output file name before the start, as `subprocess` would refuse it:
   - The check runs **after** the existing output path tests (so a NUL or unencodable character in a parent directory still gives `FileNotFoundError` with `path_role` `"output"`, and `test_a_nul_in_a_path_keeps_the_path_error` passes unchanged) and **before** the compiler is resolved. It is inside `_parameter("output")`, so the error carries `parameter` `"output"` and no `path_role`.
   - On POSIX, `os.fsencode` of the absolute output path must succeed, else its `UnicodeEncodeError` is raised. On every platform, a NUL character in it raises `ValueError`. Reuse `_check_argument` (or an equivalent helper) so the class is the one `subprocess` would raise for the same single defect. The message does not need to show the path.
   - Nothing else changes: no change to the sources' checks, `env`, `cwd`, `compiler_version`, `local_run`, `build_verification_executable`, or the order of the other checks.
3. **Docstring of `build`**: update the "Raised before anything is started" text and the `parameter` paragraph so they say that the output file name is checked after the output path tests, with the classes above and `parameter` `"output"`. Keep it short and in the existing style; no new comments in code.
4. **Tests** in `tests/test_clang_build.py` (CLAUDE.md test rules ①-④; `forbid_start` or the stub's `started` flag proves no process was started; no file is left in the output directory):
   - happy: a normal output name still builds (existing tests cover this; do not duplicate);
   - error: an output name with a NUL character in the file name only raises `ValueError` with `parameter` `"output"` and no `path_role`, before the start;
   - error (POSIX only, skip on Windows): an output file name with a lone surrogate (for example `"k\udcff.o"`) raises `UnicodeEncodeError` with `parameter` `"output"`, before the start;
   - branch: a NUL in a parent directory still raises `FileNotFoundError` with `path_role` `"output"` (the existing test stays and passes);
   - negative / order: with both a NUL output file name and a missing compiler, the output error comes first (it precedes the compiler lookup); with a valid output and a NUL flag, the flag error still comes first.
   - Do not add tests of test code, CI or hook scripts (rule ⑤).
5. **Gates**: `pytest` and `ruff` pass locally, and the `hilclaw/` line and function coverage stays at or above 80%. CI is green before merge.
6. **Code mode** (CLAUDE.md A-13): branch `claude/T-0278-<slug>`; Draft PR with `T-0278` in its title and `Task: T-0278` as the last line of its body; reviewer cycle (dev-item-address steps 10-12) to Approve within 7 rounds; squash-merge with `gh pr merge --squash --body` using the PR body; delete the branch.
7. **Size**: at most 2 non-test files changed (one in practice) and well under 300 changed lines excluding tests.
8. **Result** records: the PR and merge commit, review rounds and findings, the language line (Python, the existing module), and the follow-ups. The executor starts no `claude` program, real compiler or container (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/` (ADRs, Requirements, OpenDecisionProposals, StandardScenarios). The record of the newly named error is a follow-up.
- Source paths: a NUL or unencodable character in a source path already gives `FileNotFoundError` with `path_role` `"source"`; do not change that.
- An `env` with no `items` method and anything else `subprocess.Popen` raises; `compiler_version`; `local_run.run` (its doc waits on HQ-0027); `hilclaw/harness/timing_build.py` (waits on HQ-0021); the unlanded branches `claude/T-0210-*`, `claude/T-0231-*`, `claude/T-0264-*`.
- Any new value of `error.kind` or `condition`, any data-plane member, any owner-only item (DRIVER §9).

## Follow-ups

## Result

- PR #176 (squash-merged; the merge commit is the one on `main` with the `Task: T-0278` trailer). Branch `claude/T-0278-clang-build-output-name-checks`, deleted at merge.
- Change: `build` runs `_check_argument(str(target), ...)` inside `_parameter("output")` after the output path tests and before the compiler lookup, so a NUL character in the output file name raises `ValueError` and, on POSIX, an unencodable one raises the `UnicodeEncodeError` of `os.fsencode`, both with `parameter` `"output"` and no `path_role`. A defect in a parent directory still gives `FileNotFoundError` with `path_role` `"output"`. Docstring of `build` updated in both paragraphs. One non-test file, +11/-5.
- Tests (`tests/test_clang_build.py`): bad output file names (NUL, NUL only, POSIX lone surrogate, surrogate plus NUL), the `UnicodeEncodeError` args equal those of `os.fsencode`, the output error precedes a missing compiler, a NUL flag precedes the output check; each asserts no start, no temporary name or clock, no file left.
- Gates: local `pytest` 22649 passed / 485 skipped (Windows), `ruff check` and `ruff format --check` clean, `hilclaw/` line coverage 99%. CI failed once: the POSIX-only tests used `"k\udcff.o"` (the example in Acceptance Criteria 4), which `os.fsencode` converts on POSIX through `surrogateescape` (to the byte 0xff), so nothing was refused. The tests now use the lone surrogate `"\ud800"`, as the existing argument tests do. CI green before merge.
- Review: 3 rounds, Approve each round. Round 1: two nits (the docstring sentence on `os.fsencode` was ambiguous about what "one" referred to and did not say which error wins when both defects are present; a short line left by the reflow), both fixed. Round 2: one optional nit (the `parameter` paragraph named the checks in the reverse of their run order), fixed. Round 3: no findings.
- Language: Python, the existing module.
- No `claude` program, real compiler or container was started (D16).
- Follow-ups: a doc task that records in the ADR-0091 line that a `ValueError` with `parameter` `"output"` from the new check gets no row (decision 2), and says what is left of U4.
