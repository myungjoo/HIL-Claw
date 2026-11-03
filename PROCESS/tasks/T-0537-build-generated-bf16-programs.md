---
id: T-0537
title: Build the generated bf16 verification and timing programs of gemm, rmsnorm, elementwise_add and swiglu in the cpu_standin and virtual_npu operations and the host build functions (ADR-0193 decision 6)
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, OD-32, FR-9, "PLAN P3-5"]
dependsOn: [T-0536]
touchesFiles:
  - hilclaw/harness/bf16_verification_build.py
  - hilclaw/harness/bf16_timing_build.py
  - hilclaw/harness/bf16_program_generator.py
  - hilclaw/standin_check.py
  - hilclaw/standin_run.py
  - hilclaw/standin_copies.py
  - tests/harness/test_bf16_verification_build.py
  - tests/harness/test_bf16_timing_build.py
  - tests/harness/test_bf16_program_generator.py
  - tests/test_standin_check.py
  - tests/test_standin_run.py
  - tests/test_standin_copies.py
  - tests/test_run_definition.py
  - tests/test_backend_conformance.py
estimatedSize: {loc: 250, files: 6}
hq: []
---
## Why

**PLAN P3-5** ("표 기반 생성"), the second of three tasks. ADR-0193 decision 6: the programs of `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` are "generated, by a pure function of the package from a contract-table entry, at build time into the build directory, then copied as today's sources are (ADR-0144)". T-0536 landed the generator (`hilclaw/harness/bf16_program_generator.py`) and the tests that prove each generated program equivalent to the handwritten one. This task makes every build of those four kinds compile the generated program:
- the container operations of `cpu_standin` and `virtual_npu`, through `hilclaw/standin_check.py` and `hilclaw/standin_run.py`;
- the host build functions in `hilclaw/harness/bf16_verification_build.py` and `bf16_timing_build.py`.

The handwritten files stay in the tree, unused by any build, so that T-0536's equivalence tests keep comparing against them. T-0538 removes them and keeps the report digests as test data (decision 6, "Order").

**Split, and why this task is under half the cap (DRIVER §6 D20 ③).** This task is about 250 LOC. It cannot join T-0536 (8 files there plus 4 to 6 here) or T-0538 (8 deleted files plus these) without passing the 10-file cap of DRIVER §5.

**Before code, check T-0536 (DRIVER §6 "task 단위" ④).** T-0536 must be `DONE` with its `## Result`. Read in that `Result`:
- the generator's public names (if they differ from T-0536 criterion 3, use the landed ones);
- the per-kind inputs it kept;
- any split it proposed.

If T-0536 is not `DONE`, stop and report it.

**Order (DRIVER §6 D27 ①).** Check again that there is no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md` and no P2-15 preparation pending. If one has appeared, report it in `## Result` and stop before writing code.

**P2-15 must not change (D27).** The model executor and its programs (`model_forward*.py`, `model_forward.c`, `model_check.py`, `model_graph*.py`, `model_graph.c`) are not edited and build nothing of the harness. `rope`, `sdpa_kv_cache`, fp32 `gemm` and the waiter keep their handwritten sources.

**Open HQs not crossed (D27 ⑦).** HQ-0088 to HQ-0091: `virtual_npu` keeps exactly its current offer (`sim.run` and `board.run`, no `correctness.check`) and only the program source it compiles changes.

**D16.** Verification uses clang on the development machine and stub Docker clients written by the tests, as the existing `standin_check` and `standin_run` tests do. No `claude`, no Docker, no test run (D25). Building the generated programs in a real container is the same build as today's with another file of the same name. If the executor finds that this claim does not hold, it writes the runtime acceptance item in `## Result` (D22).

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0537-<slug>`, the `Task: T-0537` trailer and the PR body's last line, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D27 and "task 단위" ④, §8 (runtime acceptance items, D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `PROCESS/tasks/T-0536-bf16-harness-program-generator.md`, whole, its `## Result` especially.
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decision 6 in full and decision 8 (row P3-5).
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md`: the decisions on copies into the build directory. `ARCHITECTURE/decisions/ADR-0179-od14-bf16-standin-check-time-limits.md` decision 5 (the header copy). `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md` decision 3. `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` decision 2 (program and process; the build's argument order, program source first).
- Code: `hilclaw/harness/bf16_program_generator.py` (as landed); `hilclaw/harness/bf16_verification_build.py` and `hilclaw/harness/bf16_timing_build.py` (whole); `hilclaw/standin_check.py` (module docstring, `BF16_HEADER`, the bf16 parameter check that returns `(program, BF16_HEADER)`, and the copy and build path); `hilclaw/standin_run.py` (module docstring, `BF16_HEADERS`, `_bf16_checked`, `_carry_out`, `_placed_copies`, `_build`); `hilclaw/standin_copies.py` (`place_copies`, `place_harness_copy`, `_check`, `_read`, `_writing`, the `CopyError` kinds); `hilclaw/standin_answer.py` (`read_copies`, `place_error`, the `COPIES` answers).
- Tests: `tests/harness/test_bf16_verification_build.py`, `tests/harness/test_bf16_timing_build.py`, the bf16 parts of `tests/test_standin_check.py` and `tests/test_standin_run.py`, and `tests/test_run_definition.py` (the stub Docker client and the build argument lists it asserts).

## Acceptance Criteria

1. **Host build functions.** `build_bf16_verification_executable` and `build_bf16_timing_executable` build the generated program for a kind of `GENERATED_KINDS`, and the handwritten program for `rope` and `sdpa_kv_cache`. For a generated kind, the program text is written under its usual file name (`verification_name` / `timing_name`) into a directory the function creates and removes. The header the program includes is copied beside it, so that the quoted `#include` resolves with no flag, as today. The function's arguments, result, exceptions and order of checks are unchanged, and the harness still adds no flag (`bf16_verification_build`'s docstring). Whether `PROGRAM_SOURCES` keeps its form, and which of its values may name a file that is no longer used by builds, is the executor's design to state. Two constraints:
   - `standin_check.BF16_HEADER` and `standin_run.BF16_HEADERS` must still name the existing headers;
   - every public name of the two modules stays public with its meaning, or its change is listed in `## Result` with its callers.
2. **Container operations.** For a bf16 kind of `GENERATED_KINDS`, the `cpu_standin` and `virtual_npu` operations of `standin_check` and `standin_run` place the generated program text into the build directory under the same file name and position as today's copy of the handwritten program. In the build argument list, the program source comes first, under the same in-container path as today. The header copies, the waiter, the kernel copies, the flags, the limits and the order of steps are unchanged. A failure to place the generated text is answered by the same `COPIES` failures (`standin_copies.CopyError` kinds and `standin_answer.place_error`) as a failure to copy a handwritten program, with no new failure kind. If `standin_copies` needs a public function to write a given text as a harness copy, add one beside `place_harness_copy`, with the same checks and `CopyError`s.
3. **Same builds and same results.** For each of the four kinds and both operations, the existing stub-Docker tests pass unchanged. The build argument lists, the process argument lists, the limits and the results they assert stay as they are. A new test per operation asserts that the file placed under the program's name is the generator's text for that kind. `rope` and `sdpa_kv_cache` still copy their handwritten files.
4. **Generated builds run.** With clang present, for each of the four kinds and both forms, a test builds through the host build function, runs the built program with a test kernel, and checks the result:
   - verification: the report has the length and end mark of a complete report, and `judge_report` gives a verdict on it;
   - timing: `run_bf16_timing` accepts the report.

   T-0536's equivalence tests stay green against the handwritten files.
5. **Negative cases**, each one change at a time: the build directory already holds an entry under the program's name (the existing `ENTRY_EXISTS` path); the generated text cannot be written (`COPY_UNWRITABLE`); a refused `kind` at each entry, before anything is written or started; the temporary directory of criterion 1 is removed after a failed build and after a raise.
6. **No result change.** No `step` value, result definition, data-plane member or value changes, and no contract-table entry or open-list value is added. `instance.json` already records the package commit, and that commit fixes the generated text (ADR-0193 decision 6, NFR-7 ③). No new record is added. If the work shows otherwise, stop and return `BLOCKED` (A-13).
7. **Tests (D12).** Every public function of each touched module is covered by happy, error, branch and negative cases. The clang tests follow the existing rule: skip without clang locally, fail on the CI runner. Package line and function coverage stay at or above 80 %. The full suite and `ruff check` / `ruff format --check` pass locally.
8. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21). Pinning assertions this task is expected to touch:
   - the import lists of `tests/harness/test_bf16_verification_build.py` and `tests/harness/test_bf16_timing_build.py` (the generator import);
   - the public-name assertion of `tests/test_standin_copies.py`, if a function is added;
   - any allow-list of importers of `bf16_program_generator` or `contract_table` that the new imports reach.

   Each edited assertion is listed in the PR body. An existing assertion that compares a placed file with the handwritten file's bytes is not a pinning list. If one exists, stop and report it rather than editing it.
9. **Size.** About 250 LOC and 6 files, tests excluded. If the change is seen to exceed 600 LOC or 10 files, land criterion 2 with its tests and propose criterion 1 as a split in `## Follow-ups`.
10. **`## Result`** states:
    - the language line;
    - the form chosen for `PROGRAM_SOURCES` and the host build directory;
    - any new public name;
    - the edited assertions;
    - every place in `hilclaw/` (docstrings included) that still names a handwritten program file of the four kinds, for T-0538.

## Out of Scope

- Removing the handwritten `.c` files of the four kinds, and editing `hilclaw/harness/__init__.py`'s list of the C sources: T-0538.
- The generator's text and the contract constants, unless a defect found here needs a fix. Any such fix is listed in `## Result` with its test.
- `rope`, `sdpa_kv_cache`, fp32 `gemm`, the waiter, the model executor.
- Any edit of `ARCHITECTURE/`, PLAN or RuntimeAcceptance.

## Follow-ups

- None.

## Result

- Outcome: landed by PR (see the PR titled `T-0537: ...`); review rounds and merge commit are in the driver's record.
- Precondition checks: T-0536 is `DONE` (PR #353) with the public names `GENERATED_KINDS`, `verification_source`, `timing_source`, `verification_name`, `timing_name`, used as landed. No open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`, no P2-15 preparation pending (checked 2026-11-03).
- Language: Python, as the harness and container-operation modules it changes.
- `PROGRAM_SOURCES` (both build modules): form kept, a read-only mapping from each of the six kinds to a path next to the module. For a kind of `GENERATED_KINDS` only the file name of the path is used by any build (host and container); the file it names is read by no build. For `rope` and `sdpa_kv_cache` the path is the program source as before. So `standin_check.BF16_HEADER` and `standin_run.BF16_HEADERS` (derived from `PROGRAM_SOURCES["gemm"]`) still name the existing headers.
- Host build directory: `tempfile.TemporaryDirectory(prefix="hilclaw-bf16-program-")` in the system temporary directory, made only for a generated kind after the argument checks, holding the generated program under `PROGRAM_SOURCES[kind].name` and copies of the header(s) (`bf16_verification.h`; for timing also `bf16_timing.h`); removed before the function returns or raises. `BuildResult.command` therefore names a file that no longer exists.
- Container operations: `place_copies` writes the generated bytes as the harness copy, at the same name and position, so the build argument lists are unchanged; failures to write are the existing `CopyError` kinds (`ENTRY_EXISTS`, `COPY_UNWRITABLE`) placed by `standin_answer.place_error` at `COPIES`.
- New public names: `hilclaw.harness.bf16_verification_build.write_generated(directory, name, text, headers)` (used by both build modules); new optional fourth parameter `harness_text` (exactly `bytes` or `None`) of `hilclaw.standin_copies.place_copies` instead of a new function beside `place_harness_copy` (the harness copy keeps its place inside `place_copies` and its `Copies.harness` answer). No public name removed or changed in meaning. Callers of `place_copies`: `standin_check._placed_copies`, `standin_run._placed_copies` (both pass the text); no other caller.
- Edited existing assertions (listed also in the PR body):
  - D21 pinning: import lists of `tests/harness/test_bf16_verification_build.py`, `tests/harness/test_bf16_timing_build.py`, `tests/test_standin_check.py` (`targets`, `bf16_program_generator`), `tests/test_standin_run.py` (`bf16_program_generator`).
  - Not pinning, made false by criterion 1 itself (they asserted that the build of a generated kind is handed the handwritten file's path): verification build `test_arguments_are_handed_over_unchanged_in_one_call`, `test_defaults_are_those_of_clang_build`, `test_stub_build_succeeds_and_adds_nothing`, `test_flags_surround_the_sources_in_the_order_given`, `test_kernel_sources_in_every_accepted_form`, `test_duplicate_sources_are_not_checked`, `test_real_clang_builds_an_executable_that_writes_a_complete_report`; timing build `test_arguments_are_handed_over_unchanged_in_one_call`, `test_defaults_are_those_of_clang_build`, `test_stub_build_adds_no_flag_and_puts_the_program_first`, `test_kernel_sources_in_every_accepted_form`. Each now asserts the handwritten path for `rope`/`sdpa_kv_cache` and, for a generated kind, a removed temporary file of the same name; everything else they asserted is unchanged.
  - Not pinning, the kind changed to one still copied: verification build `test_missing_program_source` (`rmsnorm` -> `rope`); `tests/test_standin_check.py::test_bf16_the_program_missing_is_build_input_missing` (`gemm` -> `rope`). A generated kind can no longer miss its program; new tests assert that it reads no program file.
  - No existing assertion compares a placed file with a handwritten file's bytes; no stub-Docker build or process argument list, limit or result assertion was edited.
- Places in `hilclaw/` that still name a handwritten program file of the four kinds (for T-0538): `hilclaw/harness/__init__.py` lines 31-32 and 39-40 (the list of C sources); `PROGRAM_SOURCES` in `hilclaw/harness/bf16_verification_build.py` and `hilclaw/harness/bf16_timing_build.py` (paths, now used for the file name only); `BF16_HEADER` in `hilclaw/standin_check.py` and the first of `BF16_HEADERS` in `hilclaw/standin_run.py` derive the header paths from `PROGRAM_SOURCES["gemm"]`; the handwritten `.c` files themselves. `bf16_program_generator` docstrings name the file names, which stay.
- Generator and contract constants: unchanged; no defect found.
- Verification: full suite and `ruff check` / `ruff format --check` on Windows (clang tests skip); the clang tests of the touched files and the generator's equivalence tests run green under clang 14 in WSL (Linux). No `claude`, no Docker, no test run (D25).
- Runtime acceptance items: none. The container build is today's build with another file of the same name and bytes generated on the host.
