---
id: T-0280
title: Make a `ValueError` that `PurePath.with_name` raises while `clang_build.build` forms the temporary name carry `parameter` "output" (for example a Windows output file name such as `a:b.exe`), before the start
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18, C-7]
dependsOn: [T-0278, T-0279]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 30, files: 2}
hq: []
---
## Why

ADR-0092 (T-0279, landed `1ac785b`) narrowed U4, the pre-start `ValueError` of `clang_build.build` that carries no `parameter`. Its decision 3 says U4 now holds three things:

- a `ValueError` from `with_name` other than its documented case;
- one from `time.monotonic`, if one arises;
- one from `subprocess.Popen` for what `build` hands it.

It also says: "What else `with_name` may refuse in the new name was not read; that may include a defect of the output file name that J1 does not test."

T-0279's round-1 reviewer named one such case (not established by running code). On Windows, an output file name whose second character is `:` (for example `a:b.exe`) passes the NUL check. The temporary name built from it (`a:b.tmp-<pid>-<hex>.exe`) may then look like a drive to `with_name`, which refuses it with an unnamed `ValueError`.

The temporary name is built only from the output path, which is the operation's own (ADR-0060 decision 3). So any `ValueError` from `with_name` there is a defect of `output`. This task makes it carry `parameter` `"output"`. It does so by running only the `with_name` call inside `_parameter("output")`. It writes no platform rule of its own about which names `with_name` refuses. U4 is then left with only the clock and `subprocess.Popen`.

The pid and the random hex part are drawn **outside** that step, at the place where they are drawn now: after the `cwd` check. So:

- the existing tests that use `forbid_the_temporary_and_the_clock` stay valid;
- a `ValueError` from `os.getpid` or `secrets.token_hex`, if one arises, is not given `"output"`.

This is a code change only. It records no row of `correctness.check` (the follow-up record is a doc task), adds no data-plane value and decides nothing of OD-18. No owner-only item is touched (DRIVER §9). The tests need no real `claude`, compiler or board (D16). They use the existing stub compiler and `forbid_start`, and a test that only native Windows can run is marked `windows_only`.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task file format, naming, the `Task: T-0280` trailer in commits and as the last line of the PR body, size cap, D12 test rules.
- `CLAUDE.md`, the standing rules. In particular:
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙";
  - "도구 계층 언어 정책" (one line in the commit body on the language choice);
  - "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/clang_build.py` at `8bb1a06`:
  - the docstring of `build` (lines 196-301). Read in particular "Raised before anything is started" (line 221), the sentence "Once the output path has passed its tests, its absolute path is checked the same way", and the `parameter` paragraph ("The check of `output` forms its absolute path and, after the tests of that path below, …", line 261, through "carries no ``parameter``");
  - the check steps, the second `_parameter("output")` step (line 323) and the temporary name (line 331) up to the command;
  - `_parameter` (line 472).
- `tests/test_clang_build.py`. Follow their style:
  - `windows_only` and `posix_only` (lines 1928-1929);
  - `forbid_start` (line 1963) and `forbid_the_temporary_and_the_clock` (line 2555);
  - `test_command_order_and_temporary_name` (line 128) and `test_temporary_name_without_suffix` (line 161);
  - `OUTPUT_NAMES` and the output-name tests after it (from line 2863);
  - `test_a_value_error_from_the_output_path_object_names_the_output` (line 3367).
- `ARCHITECTURE/decisions/ADR-0092-od18-correctness-check-output-name-value-errors.md`: Context J3 and J4, decision 3, Consequences ("Code"). Read only; do not edit.
- `PROCESS/tasks/T-0278-clang-build-output-name-checks-before-start.md`: `## Acceptance Criteria` only, as the earlier change of the same shape.

## Acceptance Criteria

1. **Session entry check** (CLAUDE.md): run `gh pr list`. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict risk).
2. **The change.** In `build`:
   - Draw the pid and the `secrets.token_hex(8)` part where they are drawn now, after the `cwd` check and outside any `_parameter` step.
   - Then call `target.with_name(...)` with the same name text as today (`f"{target.stem}.tmp-{pid}-{hex}{target.suffix}"`) inside `with _parameter("output"):`. A `ValueError` it raises (or a `TypeError`, by the same context manager) then carries `parameter` `"output"` and no `path_role`. The class and message are those of `with_name`, unchanged.
   - Nothing else changes:
     - the temporary name text and the command;
     - the order of the other checks (a defect of `compiler`, `env` or `cwd` is still raised first, and no temporary name or clock is drawn for it);
     - the output path tests and the NUL/`os.fsencode` check of the output name;
     - `compiler_version`, `local_run`, `build_verification_executable`.
   - Write no own rule of which names `with_name` refuses: no drive or `:` test.
3. **Docstring of `build`**: say in the `parameter` paragraph, briefly and in the existing style, that after the check of `cwd`, a `ValueError` from forming the temporary name beside the output path carries `"output"` too. Add the matching words to "Raised before anything is started" only if it stays short. Keep the sentence that a `TypeError` or `ValueError` "from anywhere else, such as binding the call or creating the compiler process, carries no ``parameter``" true. Add no comments in code.
4. **Tests** in `tests/test_clang_build.py`. Follow CLAUDE.md test rules ①-④. Prove that no process was started with `forbid_start` or the stub's `started` flag, and that no file is left in the output directory.
   - **error, every platform**: monkeypatch `with_name` on the path class `build` uses so that it raises `ValueError` (for example `pathlib.PurePath.with_name`, through `monkeypatch`). Then `build` raises that same `ValueError` object with `parameter` `"output"` and no `path_role`, and nothing is started.
   - **error, `windows_only`**: an output path `out_dir / "a:b.exe"` (an existing directory, a file name whose second character is `:`) raises `ValueError` with `parameter` `"output"` and no `path_role`, before the start.
     - If on this machine `build` does not raise there (for example because a path test refuses it first, or `with_name` accepts it), replace this test by one for what it does raise. Assert what the code actually does, and record the observation in `## Result`.
     - Do not claim a platform behaviour the test does not show.
   - **branch / order**: with the patched `with_name` and also a refused `cwd` (for example a NUL in it), the `cwd` error comes first, with `parameter` `"cwd"`. This shows that the temporary name is still formed after the `cwd` check.
   - **negative**: a `ValueError` from `secrets.token_hex` (monkeypatched) is passed on with no `parameter`. This shows that only `with_name` is inside the step.
   - **happy**: the existing temporary-name tests (`test_command_order_and_temporary_name`, `test_temporary_name_without_suffix`) pass unchanged. Do not duplicate them.
   - Do not add tests of test code, CI or hook scripts (rule ⑤).
5. **Gates**:
   - `pytest` and `ruff` (`ruff check`, `ruff format --check`) pass locally.
   - The `hilclaw/` line and function coverage stays at or above 80%.
   - CI is green before merge. CI runs on Ubuntu, so the `windows_only` test runs only locally; say so in `## Result`.
6. **Code mode** (CLAUDE.md A-13):
   - Work on branch `claude/T-0280-<slug>`.
   - Open a Draft PR with `T-0280` in its title and `Task: T-0280` as the last line of its body.
   - Run the reviewer cycle (dev-item-address steps 10-12) until Approve, within 7 rounds.
   - Squash-merge with `gh pr merge --squash --body`, using the PR body.
   - Delete the branch.
7. **Size**: one non-test file changed, well under 300 changed lines excluding tests.
8. **Result** records:
   - the PR and the merge commit;
   - the review rounds and their findings;
   - what the `windows_only` test showed on this machine;
   - the language line (Python, the existing module);
   - the follow-ups.

   The executor starts no `claude` program, real compiler or container (D16).

## Out of Scope

- Any edit of `ARCHITECTURE/` (ADRs, Requirements, OpenDecisionProposals, StandardScenarios). The record of the newly named case is a follow-up.
- A named check of the output file name before the compiler lookup for the `:` case, or any own rule of which names `with_name` refuses.
- The following, each left as it is:
  - `time.monotonic`;
  - what `subprocess.Popen` raises, including for an `env` with no `items` method;
  - the source paths;
  - `compiler_version`;
  - `local_run.run` (its doc waits on HQ-0027);
  - `hilclaw/harness/timing_build.py` (waits on HQ-0021).
- The unlanded branches `claude/T-0210-*`, `claude/T-0231-*` and `claude/T-0264-*`.
- Any new value of `error.kind` or `condition`, any data-plane member, and any owner-only item (DRIVER §9).

## Follow-ups

- A doc task (ADR-0093, if free): place in `correctness.check` the `ValueError` with `parameter` `"output"` from forming the temporary name. Under ADR-0091 decision 2 and ADR-0092 decision 2, a `ValueError` named `"output"` is no row. Then say what is left of U4: the clock and `subprocess.Popen`.

## Result

- **Outcome**: DONE. PR #177, squash-merged as `04b8a38` (branch `claude/T-0280-temporary-name-error-names-the-output` deleted, remote and local).
- **Change**: `hilclaw/clang_build.py` (+8/-6). The pid and `secrets.token_hex(8)` are drawn after the `cwd` check and outside any step. Only `target.with_name(...)`, with the same name text, runs inside `with _parameter("output"):`. The `parameter` paragraph of the `build` docstring now says that, after the check of `cwd`, forming the temporary name beside the output path is part of the check of `output`. "Raised before anything is started" is unchanged. No code comments were added.
- **Tests** (`tests/test_clang_build.py`, +100):
  - error: a patched `pathlib.PurePath.with_name` raises `ValueError`, and separately `TypeError`. `build` raises the same object, with `parameter` `"output"` and no `path_role`.
  - order: with that patch and a NUL in `cwd`, the error carries `parameter` `"cwd"`, so the `cwd` check still comes first.
  - negative: a `ValueError` from `secrets.token_hex` comes out with no `parameter`.
  - `windows_only` (see below).
  - Every test proves that nothing was started (`forbid_start` and `stub.started`) and that the output directory is empty. The existing temporary-name tests pass unchanged.
- **`windows_only` observation** (Windows 11, Python 3.14.4):
  - `out_dir / "a:b.exe"` does not keep the name in `out_dir`: pathlib joins it to the drive-relative path `a:b.exe`, and `os.path.abspath` makes that `A:\b.exe`. `build` therefore refuses it in the parent test, with `FileNotFoundError` and `path_role` `"output"`, before the temporary name is drawn. The test asserts exactly this, and is skipped if `A:\` exists. So the round-1 reviewer case of T-0279 does not reach `with_name` in this form.
  - Also seen here but not tested: a string path `<out_dir>\a:b.exe` keeps the name `a:b.exe`, and on Python 3.14 `with_name` accepts `a:b.tmp-<pid>-<hex>.exe` without error. Whether Python 3.11's `with_name` refuses it was not established.
  - CI runs on Ubuntu, so the `windows_only` test ran only locally.
- **Gates**: local `ruff check` and `ruff format --check` clean. Full `pytest` passed: 22654 passed, 485 skipped. `hilclaw/` coverage: lines 99%, functions 622/625. CI green on head `562469a`: Python 3.11 and 3.14, coverage, C, sh and test-presence gates.
- **Review**: 2 rounds.
  - Round 1: Approve, with one Nit (assert no `path_role` on the `TypeError` test), fixed in `562469a`, and two Info notes (wait for CI green; record the Windows observation here), both addressed.
  - Round 2: Approve, with no new findings.
- **Language**: Python, the existing module.
- **Follow-ups**:
  - The doc task from `## Follow-ups` (ADR-0093, if free): place in `correctness.check` the `ValueError` with `parameter` `"output"` from forming the temporary name, and say that U4 is left with the clock and `subprocess.Popen`.
  - That record may cite the Windows observation above: the drive-relative form fails the parent test, and on Python 3.14 the in-directory form passes `with_name`.
- D16: no `claude` program, real compiler or container was started. Only the stub compiler was used.
