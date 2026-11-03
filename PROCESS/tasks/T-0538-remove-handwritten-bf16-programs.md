---
id: T-0538
title: Remove the eight handwritten bf16 harness programs of gemm, rmsnorm, elementwise_add and swiglu, keeping their report digests as test data (ADR-0193 decision 6, "Order")
phase: P3
status: TODO
commitMode: code
coversReq: [D27, OD-32, FR-9, "PLAN P3-5"]
dependsOn: [T-0536, T-0537]
touchesFiles:
  - hilclaw/harness/bf16_verification_gemm.c
  - hilclaw/harness/bf16_verification_rmsnorm.c
  - hilclaw/harness/bf16_verification_elementwise_add.c
  - hilclaw/harness/bf16_verification_swiglu.c
  - hilclaw/harness/bf16_timing_gemm.c
  - hilclaw/harness/bf16_timing_rmsnorm.c
  - hilclaw/harness/bf16_timing_elementwise_add.c
  - hilclaw/harness/bf16_timing_swiglu.c
  - hilclaw/harness/__init__.py
  - hilclaw/harness/bf16_verification_build.py
  - hilclaw/harness/bf16_timing_build.py
  - tests/harness/test_bf16_program_generator.py
  - tests/harness/test_bf16_verification_programs.py
  - tests/harness/test_bf16_timing_programs.py
  - tests/harness/bf16_program_digests.json
estimatedSize: {loc: 600, files: 10}
hq: []
---
## Why

**PLAN P3-5** ("표 기반 생성"), the last of three tasks. ADR-0193 decision 6, "Order": "The handwritten files stay until those tests pass in one task, and are removed in a later one, which keeps the report digests as test data." T-0536 landed the generator and its equivalence tests against the handwritten programs, and T-0537 made every build compile the generated programs. This task removes the eight handwritten files that no build uses any more. The equivalence tests then compare against digests recorded from the handwritten programs before removal. **The commit that adds the digests is made while the handwritten files are still in the tree**, so the recorded values come from the files and not from the generator.

Most of this task's counted size is the deleted C lines, about 600. The remaining changes are small.

**Before code, check T-0536 and T-0537 (DRIVER §6 "task 단위" ④).** Both must be `DONE`. Read their `## Result`s, and especially the list in T-0537's `Result` of the places in `hilclaw/` that still name a handwritten program file. If T-0537 left any build path compiling a handwritten file of the four kinds, stop and report it.

**Order (DRIVER §6 D27 ①).** Check again that there is no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md` and no P2-15 preparation pending. If one has appeared, report it in `## Result` and stop before writing code.

**P2-15 must not change (D27).** As in T-0536 and T-0537. `rope`, `sdpa_kv_cache`, fp32 `gemm`, the waiter and both headers stay.

**Open HQs not crossed (D27 ⑦).** HQ-0088 to HQ-0091: none concerns this.

**D16.** Development machine and clang only. No `claude`, no Docker, no test run (D25).

**After this task is `DONE`** the driver checks PLAN P3-5. No runtime acceptance item is expected.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0538-<slug>`, the `Task: T-0538` trailer and the PR body's last line, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D27 and "task 단위" ④.
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "코멘트 최소화", "바이너리 금지" (the digests are small text, not binary output).
- `PROCESS/tasks/T-0536-bf16-harness-program-generator.md` and `PROCESS/tasks/T-0537-build-generated-bf16-programs.md`, whole, their `## Result`s especially.
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decision 6 in full, and Consequences "Less exact, not edited".
- Code: `hilclaw/harness/__init__.py` (module docstring); `hilclaw/harness/bf16_verification_build.py`, `hilclaw/harness/bf16_timing_build.py` and `hilclaw/harness/bf16_program_generator.py` (as landed); every other place listed in T-0537's `Result`.
- Tests: `tests/harness/test_bf16_program_generator.py`, `tests/harness/test_bf16_verification_programs.py`, `tests/harness/test_bf16_timing_programs.py` (as landed).

## Acceptance Criteria

1. **Digests recorded from the handwritten programs.** Before any file is removed, a test data file records the digests of the equivalence cases of T-0536 criteria 5 and 6, for each of the four kinds:
   - the SHA-256 of each verification report, for the fixed test kernel, dimension tuples, seeds and draws;
   - the timing operand digests (or their SHA-256) for the fixed timing cases;
   - the exit status and standard error of each command-line case of T-0536 criterion 7.

   The data file is `tests/harness/bf16_program_digests.json`, or another small text file the executor names in `## Result`. The values are produced by building and running the handwritten programs with clang, on the branch before the removal commit. The executor states in `## Result` how they were produced (the command, the clang version and the machine). Any helper used to produce them is not added to the package, and no test of that helper is added (CLAUDE.md test rule ⑤).
2. **Equivalence tests against the recorded digests.** The tests of T-0536 criteria 5 to 7 compare the generated programs' reports, operand digests, exit statuses and standard error with the recorded values instead of with a build of the handwritten programs. The cases do not shrink. The fixed test kernel and its flags are part of the test, so the recorded values stay meaningful. A test that needs a handwritten file is removed or rewritten, and each one is listed in `## Result`.
3. **Removal.** The eight files `hilclaw/harness/bf16_{verification,timing}_{gemm,rmsnorm,elementwise_add,swiglu}.c` are deleted. No file of `hilclaw/` names them any more as a source that exists. This covers:
   - the C-source list in the module docstring of `hilclaw/harness/__init__.py`, which now says that the four kinds' programs are generated by `hilclaw.harness.bf16_program_generator` and that `rope` and `sdpa_kv_cache` keep their handwritten programs;
   - the docstrings of the two build modules;
   - any `PROGRAM_SOURCES` value or comment that T-0537 left pointing at them;
   - every other place in T-0537's list.

   A historical mention in a test name or in a recorded-digest description may stay. `ARCHITECTURE/` is not edited (see Out of Scope).
4. **Packaging.** If `pyproject.toml` or any package-data rule lists the harness `.c` files by name, it is updated to match, and the rest of the package data is unchanged. If none does, say so in `## Result`. The headers and the remaining `.c` files are still installed.
5. **Same behaviour.** The full suite passes, including the clang tests of the build modules, the generator, `standin_check`, `standin_run` and `run_definition`. No `step` value, result definition, data-plane member or value changes. If the work shows otherwise, stop and return `BLOCKED` (A-13).
6. **Tests (D12).** No new 2-layer module, so no new test file is required beyond the data file. Package line and function coverage stay at or above 80 %. `ruff check` / `ruff format --check` pass locally. The clang tests keep the existing rule: skip without clang locally, fail on the CI runner.
7. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21) and the tests criterion 2 rewrites. Pinning assertions this task may touch: any assertion that lists the files of `hilclaw/harness/` or the package data. Each edited assertion is listed in the PR body.
8. **Size.** About 600 LOC deleted and 10 files, tests excluded. If deletion and the docstring edits are seen to pass 10 files, remove the four verification programs first, and propose the four timing programs as a split in `## Follow-ups`. In that case PLAN P3-5 is not checked until the split lands.
9. **`## Result`** states:
   - the data file's path and how its values were produced;
   - the rewritten and edited tests;
   - the packaging finding;
   - for the driver, the sentences of `ARCHITECTURE/` that this removal makes less exact (ADR-0163 and ADR-0181 decision 2, "a program per kind in fixed source", and any other the executor finds by searching for the eight file names). These sentences are not edited.

## Out of Scope

- Any edit of `ARCHITECTURE/` (ADRs stay as accepted records; their less exact sentences are reported for the driver), PLAN or RuntimeAcceptance.
- Changing the generator's output, the builds, `rope`, `sdpa_kv_cache`, fp32 `gemm`, the waiter or the headers.
- Generating any further kind or form.

## Follow-ups

## Result
