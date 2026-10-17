---
id: T-0270
title: Make the TypeError that `build_verification_executable` raises itself for `kernel_sources` carry `parameter` "kernel_sources", so it is no longer an unnamed TypeError
phase: P1
status: DONE
commitMode: code
coversReq: [FR-10, OD-18]
dependsOn: [T-0261]
touchesFiles: [hilclaw/harness/verification_build.py, tests/harness/test_verification_build.py]
estimatedSize: {loc: 15, files: 1}
hq: []
---
## Why

`hilclaw.harness.verification_build.build_verification_executable` is the way the `cpu_standin` operation of `correctness.check` builds the verification executable (ADR-0056 decision 4; ADR-0080 decision 1 and ADR-0081 decision 1: "through `clang_build.build` directly or through `build_verification_executable`, which passes everything on").

T-0261 (PR #164, `a46a4d6`) gave every `TypeError` that `clang_build.build` raises from its checks before the start an attribute `parameter`. ADR-0087 then placed those errors by that attribute: a setting (`"timeout_s"`, `"flags"`, `"trailing_flags"`, `"compiler"`) is S4 `settings_refused`, and `"sources"` or `"output"` is no row. ADR-0087 names one `TypeError` on the build path that still carries no `parameter`, because `build_verification_executable` raises it itself:

- T5 (`ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`, line 23): "It raises its own `TypeError`, with no `parameter`, for `kernel_sources` that are neither a path nor iterable, before it calls `build`".
- Decision 5 (line 53) and the open list (line 68): "an unnamed `TypeError` — … or of `build_verification_executable` for `kernel_sources`" stays open under part (ma) of OD-18 sub-question 18.
- `ARCHITECTURE/OpenDecisionProposals.md` line 312 lists "`build_verification_executable` 자신의 `TypeError`" among what remains of (ma).

ADR-0060 (Consequences) leaves telling such errors apart to the code: "The code task that writes the operation makes them distinguishable — for example by a change of those functions, binding nothing here". This task makes that change for this one error, in the way T-0261 did it for `build`. It places no row; a later doc task does that (Follow-ups).

**The change, stated.** In `build_verification_executable`, a `TypeError` that leaves the conversion of `kernel_sources` (today the line `kernel_sources = tuple(kernel_sources)`) gets the attribute `parameter` with the value `"kernel_sources"`, the name of the function's own parameter. This covers:

- the `TypeError` that `tuple()` raises for a value that cannot be iterated (`None`, `7`, `1.5`, as in `test_kernel_sources_that_cannot_be_iterated`);
- a `TypeError` raised while iterating an iterable `kernel_sources`, for example by a generator that raises `TypeError`. It is the same object, with the attribute added, re-raised with a bare `raise`, so its class, `args`, traceback and chain stay unchanged.

What does not change:

- **Errors that come from `clang_build.build`** are passed on unchanged, as today. A `bytes` path among the kernel sources, or a `bytes` path alone, keeps the `parameter` `"sources"` that `build` gives it. It is not re-tagged as `"kernel_sources"`.
- **The `ValueError` for no kernel source** carries no `parameter`. In `build`, too, a `ValueError` from the checks other than `env` and `cwd` carries none. It is still tested before every other argument.
- No other exception class gets the attribute: not an exception that is not a `TypeError` raised while iterating (for example `RuntimeError`), and not a `TypeError` that Python raises while binding the call (a missing `timeout_s` or `output`).
- Every message, every class, the order of the checks and the arguments handed to `build`.
- `hilclaw/harness/timing_build.py`. Its `build_timing_executable` has the same shape, but it belongs to the run tools (OD-18 sub-question 19), whose record of situations is held on the unlanded branch of T-0210 (HQ-0021). It is a Follow-up.
- The module docstring, unless one of its sentences becomes wrong.

`hilclaw.clang_build._parameter` is private. Do not import it (ruff `SLF001` is on for `hilclaw/`). A local `try`/`except TypeError` around the conversion is enough. This change adds no module-level public name, no data-plane member or file, and no value of `condition` or `error.kind`. It is not an owner-only item under DRIVER §9.

**Existing tests checked at planning time (`956af78`).** Nothing in `tests/harness/test_verification_build.py` asserts anything about an attribute named `parameter`. `test_kernel_sources_that_cannot_be_iterated` (line 363) and `test_bytes_path_is_refused` (line 372) catch `TypeError` and still pass, because the class is unchanged. No module in `hilclaw/` other than the harness module calls `build_verification_executable` (`grep -rn build_verification_executable hilclaw`).

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task file format, naming convention, `Task:` trailer, size cap, the test rules of D12).
- `CLAUDE.md`: the standing rules (comments, the language policy of layer 2, branch and merge procedure, test rules ①-⑤).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `hilclaw/harness/verification_build.py`: the whole file (83 lines), in particular `build_verification_executable` (lines 41-83) and its docstring paragraph "Raised before anything is started" (lines 61-67).
- `tests/harness/test_verification_build.py`: the fixtures `stub`, `kernel`, `out` and the constants `WRITE`, `TIMEOUT` at the top of the file; the tests at lines 345-382.
- `hilclaw/clang_build.py`: `build`'s docstring sentences on `parameter` (lines 247-257, from "Any :class:`TypeError` from the checks of ``timeout_s``"), and `_parameter` (line 460), only to copy the way the attribute is set.
- `ARCHITECTURE/decisions/ADR-0087-od18-correctness-check-type-error-parameter.md`: lines 18-30 (T1-T5 and the terms), decision 5 (around line 53) and the open list (line 68).
- `PROCESS/tasks/T-0261-clang-build-type-error-parameter.md`: `## Why` and `## Result`, for the precedent (pickling, the same object re-raised).

## Acceptance Criteria

1. **The attribute.** A `TypeError` that leaves the conversion of `kernel_sources` in `build_verification_executable` has `parameter == "kernel_sources"`. Nothing is started, `clang_build.build` is not called, and nothing is created in the output directory.
2. **The same object.** A `TypeError` raised from inside the iteration of `kernel_sources` (a generator that raises `TypeError("x")` after yielding one valid path) leaves the function as that same object (`is`), with unchanged `args` and `parameter == "kernel_sources"`.
3. **What stays without it, or keeps `build`'s value:**
   - the `ValueError` for no kernel source (`()`, `[]`, an empty generator) has no attribute `parameter`;
   - a `bytes` path among the kernel sources, and a `bytes` path alone, still give a `TypeError` with `parameter == "sources"` (from `build`);
   - a `TypeError` for a bad `timeout_s`, `flags`, `trailing_flags` or `compiler` still carries the value `build` gives it;
   - a `RuntimeError` raised while iterating `kernel_sources` passes through unchanged, as the same object, with no attribute `parameter`;
   - a missing `timeout_s` (binding the call) gives a `TypeError` with no attribute `parameter`.
4. **Unchanged behaviour.** Every existing test in `tests/harness/test_verification_build.py` and in the rest of the suite (including `tests/harness/calibration`) passes unchanged. No existing test is edited or removed.
5. **Pickling.** The `TypeError` of criterion 1 keeps `parameter == "kernel_sources"` through `pickle.dumps`/`pickle.loads`.
6. **Docstring.** The paragraph "Raised before anything is started" of `build_verification_executable` says that its own `TypeError` for `kernel_sources` carries `parameter` `"kernel_sources"`, read as `getattr(error, "parameter", None)`, and that what `build` raises keeps its own attributes (`"sources"` for a `bytes` path). Nothing else in the docstrings changes, unless a sentence becomes wrong.
7. **Tests** (D12): happy and branch cases (path, sequence and generator forms still build with the stub, as today), the error and negative cases of criteria 1 to 3 and 5, in `tests/harness/test_verification_build.py` only. No test targets test code, CI or hook scripts (rule ⑤). The rules of `.github/workflows` hold: pytest with coverage (`hilclaw/` lines ≥ 80 %, functions ≥ 80 %), `ruff check` and `ruff format --check` clean.
8. **Scope.** Only the two files of `touchesFiles` change. No change to `hilclaw/clang_build.py`, `hilclaw/harness/timing_build.py`, `ARCHITECTURE/`, `PROCESS/` (other than this task file's `## Result`), CI or settings. No new dependency.
9. **Result.** `## Result` records the PR, the review rounds, CI, the language and the reason for it (Python, the language of the module being changed), the size, and the follow-ups. The executor starts no `claude` program (D16).

## Out of Scope

- `build_timing_executable` in `hilclaw/harness/timing_build.py` (Follow-ups).
- A `parameter` on the `ValueError` for no kernel source, or on any `ValueError` of `build`.
- Re-tagging what `clang_build.build` raises.
- Any row, kind or record of `correctness.check`: the place of `"kernel_sources"` in ADR-0060 decision 4 is a doc task.
- `local_run.run` and its program-lookup `OSError` (held by HQ-0027).
- The `cpu_standin` operation of `correctness.check` (HQ-0026, PLAN P1-1).

## Follow-ups

- (doc, after HQ-0027) A record under OD-18 sub-question 18 part (ma) on what `parameter` `"kernel_sources"` of `build_verification_executable` makes true (an argument the operation forms, so no row, as for `"sources"` in ADR-0087), together with the T-0265..T-0269 follow-ups. That record lists ADR-0087 T5 ("with no `parameter`") as now less exact.
- (code, after HQ-0021) The same change in `build_timing_executable` (`hilclaw/harness/timing_build.py`), if the run tools' record of situations does not settle it otherwise.

## Result

- PR #171 (https://github.com/myungjoo/HIL-Claw/pull/171), squash-merged with `gh pr merge --squash --body` (the body ends with `Task: T-0270`); branch `claude/T-0270-verification-build-kernel-sources-parameter` deleted.
- Review: 1 round, Approve (#issuecomment-6234153874), no findings.
- CI green on 955433d: Python 3.11 and 3.14, coverage, test presence, shellcheck, clang. Local (Windows, Python 3.14): full pytest 22547 passed, 474 skipped; `ruff check` and `ruff format --check` clean. Without the source change, 5 of the new tests fail.
- Language: Python, the language of the module being changed (`hilclaw/harness/verification_build.py`).
- Implementation: `tuple(kernel_sources)` wrapped in a local `try`/`except TypeError` that sets `parameter = "kernel_sources"` and re-raises with a bare `raise`; `clang_build._parameter` not imported. Docstring paragraph "Raised before anything is started" updated. Size: `hilclaw/harness/verification_build.py` +15/-6; tests +121 in `tests/harness/test_verification_build.py`, no existing test edited.
- Follow-ups: unchanged from the list above; none new. No `claude` was started (D16).
