---
id: T-0261
title: Make every TypeError that `clang_build.build` raises from its checks before the start name the parameter it is about, so a setting is told from an argument the operation forms
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0259]
touchesFiles: [hilclaw/clang_build.py, tests/test_clang_build.py]
estimatedSize: {loc: 40, files: 1}
hq: []
---
## Why

ADR-0060 decision 4 gives a `TypeError` two different answers in `correctness.check`, depending on what it is about:

- **A setting of the wrong type** (the time limit, a flag, the compiler) is S4 `settings_refused`, "whether the setting is refused for its value or for its type".
- **An argument that is no setting** (a path, an argument of the command) is "a defect of the operation's own code and is no row". The landed rules answer it `operation_answer_invalid` (ADR-0045 decisions 4 and 5).

The record then says: "a `TypeError` of `clang_build.build`, whose docstring does not say which argument, is an error of two rows (Consequences)". It also says: "The code task that writes the operation makes them distinguishable — for example by a change of those functions, binding nothing here". ADR-0086 decision 8 still lists "the `TypeError` of `clang_build.build`" as open under part (ma) of sub-question 18 of OD-18. Nothing on `main` tells these errors apart today: every one is a plain `TypeError` with a message.

**The change, stated.** Tell them apart by a member, the same way T-0259 used `path_role` for the path tests. The class stays `TypeError`, because existing tests catch it with `pytest.raises(TypeError)`. Add one attribute, `parameter`, to every `TypeError` that leaves `build` from the checks it makes before the start. Its value is the name of the parameter of `build` the error is about:

- `"timeout_s"`: from `_check_timeout(timeout_s)`;
- `"flags"` and `"trailing_flags"`: from `_checked_flags(...)` for that parameter, including the `TypeError` that `tuple(flags)` raises for a value that cannot be iterated;
- `"sources"`: from `_checked_sources(sources)`, including the `TypeError` that iterating a value that cannot be iterated raises, and one from `os.path.abspath` for a source;
- `"output"`: from `Path(os.path.abspath(output))`;
- `"compiler"`: from `_resolve(compiler)`, including the `TypeError` that `tuple(compiler)` raises.

What it covers:

- For a `TypeError` that `build` or its helpers raise themselves, the attribute is set on the object before it leaves `build`.
- A foreign `TypeError` (from `tuple`, iteration or `os.path.abspath`) is caught, given the attribute on that same object, and re-raised with a bare `raise`. Its class, `args`, traceback and chain stay unchanged.
- **Set it in `build`, not in the helpers.** `compiler_version` also calls `_check_timeout` and `_resolve`, and its errors do not change. Attach it however you like (a `try` around each check, or one small private context manager), as long as every listed source gets its own value.
- **No other error carries it:**
  - a `ValueError`, any `OSError` (with or without `path_role`) or `CompilerNotFoundError`;
  - a `TypeError` that Python raises while binding the call before `build` runs, for example a missing `timeout_s` (`test_timeout_has_no_default`);
  - anything from `subprocess.Popen` or later, for example an `env` or a `cwd` that cannot be handed over. Those remain what `build` passes on from `subprocess`, a separate open entry of (ma).

A caller reads it as `getattr(error, "parameter", None)`. `None` means the `TypeError` came from none of the checks listed above.

This is an engineering choice inside `build`, which ADR-0060 leaves to the code task. It adds:

- no new module-level public name: the values are the six plain strings, documented in `build`'s docstring;
- no data-plane member or file;
- no value of `condition` or `error.kind`.

It places no row of `correctness.check`. Which values are S4 and which are no row is for a later doc task (Follow-ups). It is not an owner-only item under DRIVER §9.

Nothing else changes:
- the order of the checks, every message, and every class;
- `path_role` and the five error classes of the module;
- results, the temporary file and its removal;
- `compiler_version`;
- the module docstring, unless one of its sentences becomes wrong.

**Existing tests checked at planning time (`d1326a1`).** No existing test asserts anything about an attribute named `parameter`. `grep -rn '\.parameter\b\|"parameter"' hilclaw tests` finds nothing. The tests that catch `TypeError` still pass, because the class is unchanged:
- `test_unusable_sources` (line 1489), whose parameters include `[3]`, `[None]` and `b"kernel.c"`;
- `test_checks_other_than_paths_have_no_role` (line 1671);
- `test_flags_of_the_wrong_type` (line 1702);
- `test_timeout_must_be_a_number` (line 1738);
- `test_timeout_has_no_default` (line 1746);
- `test_malformed_compiler_argument` (line 1782).

The callers `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py` and `hilclaw/standin_profile.py` check their own arguments first. Their tests catch the built-in class.

**Why this item now.** STATE has no lock, current task or next task, and there is no open PR. Every BLOCKED task file waits on an open HQ: T-0210 (HQ-0021), T-0225 (HQ-0022), T-0231 (HQ-0023), T-0233 (HQ-0024), T-0239 (HQ-0025) and T-0243 (HQ-0026). None of them touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, and this task depends on none of those HQs. PLAN P1-1 continues through the OD-18 (ma) work. Of the entries ADR-0086 decision 8 leaves open:
- the unroled `OSError` may need a new `error.kind`, which is the owner's (ADR-0086 decision 6), so it is not taken here;
- the `CompilerRunError` with `timed_out` false and `returncode` `None` has no stated status (ADR-0085 decision 6), so it is not taken here either;
- the `TypeError` is the entry a member can split with no owner decision.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 (line 72): executor procedure, resume rule, the 2h30 time limit;
  - §5 (lines 86-114): task format, the branch `claude/T-0261-<slug>`, the PR title with `T-0261`, the trailer `Task: T-0261` in the commit and as the last line of the PR body, the size cap, the D12 test rules.
- `CLAUDE.md`: "브랜치·merge 절차" (code mode), "테스트 규칙", "도구 계층 언어 정책", "개발 드라이버와 런타임의 구분", "코멘트 최소화".
- `.claude/skills/dev-item-address/SKILL.md` (code mode) and `.claude/skills/dev-code-review/SKILL.md`.
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md`, decision 4 (lines 69-104), especially the bullet "What the functions on `main` report, against the rows" (line 102) and its sentences on `TypeError`. Do not edit it.
- `ARCHITECTURE/decisions/ADR-0086-od18-correctness-check-path-role.md`, decision 8 (lines 72-76). Do not edit it.
- `hilclaw/clang_build.py` at `d1326a1` or later:
  - `build` from line 194: its docstring, especially "Raised before anything is started: …", and its lines up to `prefix = _resolve(compiler)`;
  - `compiler_version` (line 361), only to see that it shares `_check_timeout` and `_resolve`;
  - `_check_timeout` (line 418), `_checked_flags` (line 425), `_checked_sources` (line 439) and `_resolve` (line 462).
- `tests/test_clang_build.py`:
  - the fixtures `stub`, `src` and `out_dir` (lines 80-100);
  - `test_no_start_for_an_error_before_the_start` (line 602);
  - the tests listed under "Existing tests checked at planning time" above, and `test_path_errors_keep_their_role_through_pickling` (line 1687) for the pickling precedent.
- `PROCESS/tasks/T-0259-clang-build-path-test-role.md`, "The change, stated" and "Result", for the precedent of `path_role`.

## Acceptance Criteria

1. **Entry check.** Run `gh pr list` before the first edit. If an open PR touches `hilclaw/clang_build.py` or `tests/test_clang_build.py`, stop and return BLOCKED (open-PR conflict).
2. **`build`.** Make the change as "The change, stated" says:
   - Every `TypeError` that leaves one of the listed checks carries `parameter` with the value listed for it.
   - A foreign `TypeError` is the same object after the change (`is`). It keeps its class, `args` and message, and it is re-raised with a bare `raise`.
   - No other error that `build` raises or passes on has the attribute. `compiler_version`'s errors have none either.
   - Keep the order of the checks and every message. Add no new module-level public name. Add no comment that restates the code.
3. **Docstrings.**
   - Extend `build`'s sentence about `TypeError` ("… :class:`TypeError` for arguments of the wrong type, including a bare ``str`` as flags …") so it states:
     - `parameter` and its six values;
     - that it is set on any `TypeError` from those checks, including one Python raises inside them;
     - that a `TypeError` from anywhere else carries no `parameter`.
   - Change no other sentence of `build`'s docstring unless it becomes wrong.
   - The docstrings of `compiler_version`, of the five classes and of the module do not change, unless one of their sentences becomes wrong.
4. **Tests** in `tests/test_clang_build.py`, following D12. Do not test the fixtures.
   - **Edits to existing tests are allowed only as additions of assertions or parameters.** No existing assertion may be removed or changed, and no existing test may be renamed or deleted. Additions are allowed only to:
     - `test_unusable_sources`;
     - `test_checks_other_than_paths_have_no_role`;
     - `test_flags_of_the_wrong_type`;
     - `test_timeout_must_be_a_number`;
     - `test_timeout_has_no_default`;
     - `test_malformed_compiler_argument`.

     Every other existing test, including those under `tests/harness/` and `tests/test_standin_profile.py`, must pass unchanged. If one does not, stop and return BLOCKED (requirement unclear) with the test's name. Do not edit it.
   - **Happy path.** These raise `TypeError` with the given `parameter`:
     - a `timeout_s` of `"10"` and of `True`: `"timeout_s"`;
     - a bare `str` as `flags` and a non-`str` element of `trailing_flags`: `"flags"` and `"trailing_flags"`.

     In each, `type(error) is TypeError`, no compiler is started and the output directory stays as it was.
   - **Branch, each parameter.**
     - `sources` of `[3]`, `[None]` and `b"kernel.c"`: `"sources"`.
     - `output=3`: `"output"`.
     - `compiler=(sys.executable, 3)` and `compiler=b"clang"`: `"compiler"`.
   - **Branch, a foreign `TypeError`.** These carry the given `parameter` and the message Python gave them:
     - `flags=3` (the `TypeError` of `tuple`): `"flags"`;
     - `sources=3` (the `TypeError` of iteration): `"sources"`;
     - `compiler=3` (the `TypeError` of `tuple`): `"compiler"`.

     A patched `clang_build.os.path.abspath` that raises a given `TypeError` instance for a source makes `build` raise that same object (`is`), with `parameter == "sources"`.
   - **Branch, order.** A call with both a bad `timeout_s` and a bad `flags` reports `"timeout_s"`, as the order of the checks has it.
   - **Negative.** Each of these has no `parameter` attribute (`not hasattr(error, "parameter")`):
     - a missing `timeout_s` (`test_timeout_has_no_default`);
     - a `ValueError` for a non-positive `timeout_s`, for an empty compiler prefix and for a flag that sets the output;
     - `CompilerNotFoundError`;
     - an `OSError` with `path_role` for a missing source and for a missing output directory;
     - a `TypeError` from a patched `subprocess.Popen` (the stub compiler is not started);
     - a `TypeError` from `compiler_version` for a bad `timeout_s` and for a bad `compiler`.

     A successful build still returns a `BuildResult`.
   - **Pickling.** A pickled and loaded `TypeError` with `parameter` keeps its class, its message and its `parameter`. If a plain `TypeError` loses an instance attribute through `pickle`, record that in Result and assert what `pickle` actually does. Do not add a class to make it survive.
   - Line and function coverage of `hilclaw/` stays at or above 80%.
5. **Local checks:** `pytest` (whole suite), `ruff check` and `ruff format --check` pass. Tests start only the stub compilers the suite already writes. Start no `claude` process in any form (D16).
6. **Code mode** per CLAUDE.md A-13:
   - work on the branch `claude/T-0261-<slug>` with a Draft PR whose title contains `T-0261`;
   - run the reviewer cycle to Approve within 7 rounds;
   - wait for CI green;
   - squash-merge with `gh pr merge --squash --body`, where the body's last line is `Task: T-0261`;
   - delete the branch.
   - In Result, record the language (Python, the module's language) with a one-line reason. State from the code which lines now set `parameter` and to which value.
7. **Size** within DRIVER §5: ≤ 300 changed lines and ≤ 5 files, excluding tests.

## Out of Scope

- Any edit of `ARCHITECTURE/`: ADR-0060, ADR-0078 to ADR-0086, Requirements, OpenDecisionProposals and StandardScenarios.
- Placing any row of `correctness.check`. That includes S4 or no row for any value of `parameter`.
- `ValueError`: ADR-0060 decision 4 already places it by what it is for. Do not tag it.
- What `build` passes on from `subprocess` (`env`, `cwd`, an `OverflowError`), the unroled `OSError` (ADR-0086 decision 6), and the `CompilerRunError` with `timed_out` false and `returncode` `None`.
- `local_run.run` and its `ValueError`, `TypeError` and `OSError` for a missing `cwd`.
- New error classes, or a changed class for any error.
- The callers of `build`: `hilclaw/harness/verification_build.py`, `timing_build.py` and `hilclaw/standin_profile.py`, and their tests. Also out: the `cpu_standin` operation of `correctness.check` (HQ-0026).

## Follow-ups

- (doc) A record under OD-18 sub-question 18 part (ma) on what `parameter` makes true for `correctness.check`. It weighs, from ADR-0060 decision 4:
  - S4 `settings_refused` for `"timeout_s"`, `"flags"`, `"trailing_flags"` and `"compiler"`;
  - no row (`operation_answer_invalid`) for `"sources"` and `"output"`, which the operation forms;
  - a `TypeError` with no `parameter`.

  It also names the sentences of ADR-0060 decision 4 and ADR-0086 decision 8 that become less exact.
- (code, later) The same kind of split for `local_run.run`: its `ValueError` or `TypeError` for an `env` against one for an argument, and its `OSError` for a missing `cwd` (S3) against other start errors (S10). The design is left to that task.

## Result
