---
id: T-0539
title: Remove the four handwritten bf16 timing programs of gemm, rmsnorm, elementwise_add and swiglu, the split T-0538 left (ADR-0193 decision 6, "Order")
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, FR-9, "PLAN P3-5"]
dependsOn: []
touchesFiles:
  - hilclaw/harness/bf16_timing_gemm.c
  - hilclaw/harness/bf16_timing_rmsnorm.c
  - hilclaw/harness/bf16_timing_elementwise_add.c
  - hilclaw/harness/bf16_timing_swiglu.c
  - hilclaw/harness/__init__.py
  - hilclaw/harness/bf16_timing_build.py
  - hilclaw/harness/bf16_program_generator.py
  - hilclaw/standin_run.py
  - tests/harness/test_bf16_program_generator.py
  - tests/harness/test_bf16_timing_build.py
  - tests/harness/test_bf16_timing_programs.py
estimatedSize: {loc: 260, files: 8}
hq: []
---
## Why

**PLAN P3-5** ("표 기반 생성"), the split that T-0538 proposed in its `## Follow-ups` (DRIVER §5 file cap). ADR-0193 decision 6, "Order": "The handwritten files stay until those tests pass in one task, and are removed in a later one, which keeps the report digests as test data." T-0536 landed the generator, T-0537 made every build compile the generated programs, and T-0538 recorded the digests in `tests/harness/bf16_program_digests.json` and removed the four handwritten **verification** programs. That was the most it could do under the cap of 10 files. The four handwritten **timing** programs of `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` are still in the package, and no build reads them. PLAN P3-5 stays unchecked until they are removed. This task removes them.

The timing digests are already recorded (T-0538 `## Result`, "Data file"): the equivalence tests compare the generated timing programs with the recorded operand digests and do not build the handwritten timing files. No new digest is recorded here.

**Order (DRIVER §6 D27 ①).** On 2026-11-03 at planning time there was no open `nightly-failure` issue, no `실패` value in `PROCESS/RuntimeAcceptance.md` and no pending P2-15 preparation. Check again before writing code. If one has appeared, report it in `## Result` and stop.

**P2-15 must not change (D27).** `rope`, `sdpa_kv_cache`, fp32 `gemm`, the waiter and both headers stay. The generated programs' text does not change.

**Open HQs not crossed (D27 ⑦).** HQ-0081 and HQ-0088 to HQ-0091 do not concern this task.

**D16.** Use the development machine and clang only. Do not start `claude`, use Docker or start a test run (D25).

**After this task is `DONE`** the driver checks PLAN P3-5. No runtime acceptance item is expected.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0539-<slug>`, the `Task: T-0539` trailer and the PR body's last line, the size recommendation and file cap, the task directory of "스토리지", D12, D21), §3 "BLOCKED 사유", §6 D27.
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "코멘트 최소화".
- `PROCESS/tasks/T-0538-remove-handwritten-bf16-programs.md`, whole: `## Follow-ups` (the list this task carries out) and `## Result` (data file, rewritten tests, packaging finding, less exact `ARCHITECTURE/` sentences).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decision 6 in full.
- Code: `hilclaw/harness/__init__.py` (module docstring), `hilclaw/harness/bf16_timing_build.py` (module docstring, `PROGRAM_SOURCES`), `hilclaw/harness/bf16_verification_build.py` (`PROGRAM_SOURCES` and its docstring as T-0538 left it, as the model), `hilclaw/harness/bf16_program_generator.py` (module docstring), `hilclaw/standin_run.py` (`BF16_HEADERS`), `hilclaw/standin_check.py` (`BF16_HEADER`, the model for `BF16_HEADERS`).
- Tests: `tests/harness/test_bf16_program_generator.py`, `tests/harness/test_bf16_timing_build.py`, `tests/harness/test_bf16_timing_programs.py`, `tests/harness/bf16_program_digests.json`.

## Acceptance Criteria

1. **Removal.** The four files `hilclaw/harness/bf16_timing_{gemm,rmsnorm,elementwise_add,swiglu}.c` are deleted. `bf16_timing_rope.c`, `bf16_timing_sdpa_kv_cache.c`, `bf16_timing.h`, `bf16_verification.h`, `timing_driver.c`, `timing_waiter.c` and every other file of `hilclaw/harness/` stay unchanged.
2. **No source of `hilclaw/` names the removed files as existing sources.** `git grep` for the four file names over `hilclaw/` finds only a file name that the generator produces (for example in the `timing_name` docstring), not a claim that the file is in the package. This covers:
   - the timing paragraph of the `hilclaw/harness/__init__.py` module docstring. It says that the C sources of the bf16 timing runs are the shared header and the two handwritten programs of `rope` and `sdpa_kv_cache`, and that the four other kinds' timing programs are generated. The sentence "still in the package but read by no build" goes;
   - the module docstring of `hilclaw/harness/bf16_timing_build.py` and the doc comment of `PROGRAM_SOURCES`. They say what the verification build's docstring says after T-0538: for a generated kind only the file name of the entry is used, and no such file exists;
   - the parenthesis "(for the verification programs, as it had before it was removed)" in the `bf16_program_generator` module docstring. It now covers both forms;
   - any other place that `git grep` finds.
3. **`standin_run.BF16_HEADERS`.** Its first entry is derived from `bf16_timing_build.PROGRAM_SOURCES["rope"]`, as `standin_check.BF16_HEADER` is derived from the `rope` verification entry. Its value is unchanged.
4. **`PROGRAM_SOURCES` keeps its form and values.** The timing build's mapping still has six entries with the same paths. Only the files behind four of them are gone.
5. **Tests carried over.** The tests listed in T-0538 `## Follow-ups` are updated:
   - `tests/harness/test_bf16_program_generator.py::test_names_are_those_of_the_handwritten_programs` asserts that the timing file is absent, as it already does for the verification file.
   - `tests/harness/test_bf16_timing_build.py::test_program_sources_are_the_c_files_of_the_kinds_next_to_the_package` asserts `is_file()` only for `rope` and `sdpa_kv_cache`, as the verification-build test does after T-0538.
   - `tests/harness/test_bf16_timing_programs.py::test_each_program_declares_its_prototype_byte_for_byte_and_calls_it_once` and `::test_rmsnorm_compiles_in_the_contracts_eps` read `timing_source(kind)` instead of the file.

   Any other test that reads or builds one of the four removed files is rewritten in the same way, with the generated text or a build through `build_bf16_timing_executable`, and is listed in `## Result`. The cases do not shrink. The digest comparisons of T-0538 criterion 2 stay as they are.
6. **Same behaviour.** The full suite passes, including the clang tests of the build modules, the generator, `standin_check`, `standin_run`, `run_definition` and backend conformance. No `step` value, result definition, data-plane member or value changes. If the work shows otherwise, stop and return `BLOCKED` (A-13).
7. **Packaging.** T-0538 found that no rule lists the harness `.c` files by name. Confirm that this is still so and say so in `## Result`.
8. **Tests (D12).** No new 2-layer module is added, so no new test file is required. Package line and function coverage stay at or above 80 %. `ruff check` and `ruff format --check` pass locally. The clang tests keep the existing rule: they skip without clang locally and fail on the CI runner.
9. **Existing tests pass unchanged**, except:
   - assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21);
   - the tests of criterion 5.

   Pinning assertions this task may touch: any assertion that lists the files of `hilclaw/harness/` or the package data, and the path assertions of the two `test_program_sources_are_the_c_files_of_the_kinds_next_to_the_package` tests. List each edited assertion in the PR body.
10. **Size.** About 240 LOC deleted and 8 files, tests excluded. This is well within the cap.
11. **`## Result`** states:
    - the rewritten and edited tests;
    - the packaging finding;
    - for the driver, the sentences of `ARCHITECTURE/` that this removal makes less exact. Start from ADR-0181 decision 2 (a), "One program per kind, six programs, sharing one header", and the T-0538 list, and search for the four file names to find others. Do not edit these sentences.

## Out of Scope

- Any edit of `ARCHITECTURE/`, PLAN or RuntimeAcceptance. ADRs stay as accepted records, and their less exact sentences are reported for the driver.
- Changing the generator's output, the builds, `rope`, `sdpa_kv_cache`, fp32 `gemm`, the waiter or the headers.
- Recording new digests or changing `tests/harness/bf16_program_digests.json`.
- Generating any further kind or form.
- The `tests/test_fresh_run.py` failure under `coverage run` that T-0538 observed. It is unrelated to this task.

## Follow-ups

## Result

- Outcome: PR #356 (see the summary returned to the driver for the merge commit and review rounds). PLAN P3-5 can be checked: all eight handwritten programs of the four generated kinds are now gone.
- Precondition checks (2026-11-03, before code): no open `nightly-failure` issue; no `실패` status value in `PROCESS/RuntimeAcceptance.md`; no P2-15 preparation pending. HQ-0081 and HQ-0088 to HQ-0091 not crossed.
- Language: Python (docstrings, tests) and C deletions only, as the harness already is.
- **Package**: `hilclaw/harness/bf16_timing_{gemm,rmsnorm,elementwise_add,swiglu}.c` deleted. Docstrings updated: the timing paragraph of `hilclaw/harness/__init__.py` (shared header plus the two handwritten programs of `rope` and `sdpa_kv_cache`; the "still in the package but read by no build" sentence removed); the module docstring of `hilclaw/harness/bf16_timing_build.py` ("no file of the package exists at the path of that entry") and a new doc comment on its `PROGRAM_SOURCES`, worded as the verification build's; the `bf16_program_generator` module docstring parenthesis replaced by "had before it was removed", covering both forms. `standin_run.BF16_HEADERS[0]` is now `bf16_timing_build.PROGRAM_SOURCES["rope"].with_name("bf16_timing.h")` (was the `gemm` entry); same value. `PROGRAM_SOURCES` keeps six entries and the same paths. After the change `git grep` of the four file names over `hilclaw/` finds only the `timing_name` docstring example. No `step`, result definition, data-plane member or value changed; the generated text is unchanged.
- **Rewritten tests** (they read a removed file): `tests/harness/test_bf16_timing_programs.py::test_each_program_declares_its_prototype_byte_for_byte_and_calls_it_once` and `::test_rmsnorm_compiles_in_the_contracts_eps` read `timing_source(kind)`; the now unused `PROGRAM_SOURCES` import of that file is dropped. No other test read or built one of the four files (`test_bf16_timing_build.py::test_the_build_compiles_the_generated_text_beside_both_headers` and `test_standin_run.py::test_a_bf16_call_places_the_generated_text` read the file only for `rope`/`sdpa_kv_cache`; `test_standin_run.py::test_the_headers_are_those_the_programs_include` compares only parents). The digest comparisons of T-0538 are unchanged; no case removed.
- **Edited assertions** (pinning, D21): `tests/harness/test_bf16_program_generator.py::test_names_are_those_of_the_handwritten_programs` (timing file now `not ... exists()`); `tests/harness/test_bf16_timing_build.py::test_program_sources_are_the_c_files_of_the_kinds_next_to_the_package` (`path.is_file() is (kind not in GENERATED_KINDS)`).
- **Packaging**: still no rule lists the harness `.c` files by name — `pyproject.toml` has no build-system or package-data section, and there is no `MANIFEST.in` or `setup.*`. CI's C compile step (`.github/workflows/ci.yml`, `git ls-files -z -- '*.c'`) discovers files, so the deleted files simply drop out. Nothing to update.
- **Less exact sentences of `ARCHITECTURE/`** (not edited): ADR-0181 decision 2 (a) "One program per kind, six programs, sharing one header" (line 32) — four of the six are now generated at build time, not package sources; ADR-0181 code slice 4 "the six programs built with the header copy" (line 93) and code slice 1 "The timing programs of the four ADR-0163 kinds" (line 90) describe handwritten sources as delivered then; ADR-0193 decision 1 table row "One handwritten C program per kind and per run form | `hilclaw/harness/bf16_timing_*.c`, `bf16_verification_*.c`" (line 33) and decision 6 "Generated ... the `bf16_timing_*.c` and `bf16_verification_*.c` programs ... (observed in `bf16_timing_elementwise_add.c`, `bf16_timing_swiglu.c` and `bf16_timing_rmsnorm.c` ...)" (line 118) now name files that no longer exist (they describe the state before P3-5). From the T-0538 list: ADR-0163 decision "One verification program per kind" (line 46) and its title stay as reported there. No other `ARCHITECTURE/` sentence names the four timing files.
- Verification: full suite on WSL2 Ubuntu (development machine), **Ubuntu clang 14.0.0-1ubuntu1.1**, Python 3.12.13, numpy 2.4.6, pytest 9.1.1, coverage 7.16.2, each of the 194 test files in its own process under `coverage run --branch`, 24 in parallel: 39675 passed, 90 skipped, 0 failed; 478 errors in 6 files were pytest `tmp_path` base-directory collisions between the parallel processes (`_pytest/tmpdir.py:198: OSError`) — those 6 files rerun one by one with their own `--basetemp` pass (`test_model_run_binding` 70, `test_model_container` 92, `test_model_forward_container` 89, `test_standin_container` 98, `test_model_check` 138; `test_fresh_run` fails under `coverage run` only, as T-0538 observed, and passes without it, 51 passed — out of scope). Combined coverage of `hilclaw/`: lines 16132/16169 (99 %), functions 1513/1514. `ruff check` / `ruff format --check` pass. Edited test files plus `tests/test_standin_run.py` on Windows: 355 passed, 269 skipped (clang tests skip). No `claude`, no Docker, no test run (D16, D25).
- Tools: a Python 3.12 virtual environment created with the existing `uv` under the task directory `/tmp/hilclaw-driver/T-0539/` in WSL (removed at the end); no host install, no image.
- Runtime acceptance items: none.
