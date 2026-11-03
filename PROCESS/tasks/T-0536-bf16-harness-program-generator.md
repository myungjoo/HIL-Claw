---
id: T-0536
title: Add the bf16 harness program generator of ADR-0193 decision 6 for gemm, rmsnorm, elementwise_add and swiglu, the contract constants it reads, the dimension lists read from task_contract, and the equivalence tests against the handwritten programs
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, FR-9, "PLAN P3-5"]
dependsOn: []
touchesFiles:
  - hilclaw/harness/bf16_program_generator.py
  - hilclaw/gemm_bf16_contract.py
  - hilclaw/rmsnorm_bf16_contract.py
  - hilclaw/elementwise_add_bf16_contract.py
  - hilclaw/swiglu_bf16_contract.py
  - hilclaw/harness/bf16_verification_arrays.py
  - hilclaw/harness/bf16_timing.py
  - hilclaw/standin_settings.py
  - tests/harness/test_bf16_program_generator.py
  - tests/harness/test_bf16_timing.py
  - tests/harness/test_bf16_verification_arrays.py
  - tests/test_standin_settings.py
  - tests/test_gemm_bf16_contract.py
  - tests/test_rmsnorm_bf16_contract.py
  - tests/test_elementwise_add_bf16_contract.py
  - tests/test_swiglu_bf16_contract.py
estimatedSize: {loc: 450, files: 8}
hq: []
---
## Why

**PLAN P3-5** ("표 기반 생성"), the first of three tasks. ADR-0193 decision 6 is the design and decision 8 sizes P3-5 at "~500 LOC for the generator and tests' support, ~600 changed for the removal: 2 tasks". The planner split the second of those into two (T-0537 switches the builds, T-0538 removes the handwritten files). Together they would touch about 13 files (8 deleted C files and 4 or 5 build and operation modules), over the 10-file cap of DRIVER §5. This task is the generator and its proof. **Nothing that builds or runs a program changes here**: the container operations (`standin_check`, `standin_run`) and the host builds (`bf16_verification_build`, `bf16_timing_build`) keep building the handwritten files. T-0537 switches them.

ADR-0193 decision 6, in short:
- **Generated**: the `bf16_timing_*.c` and `bf16_verification_*.c` programs of `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`, produced from a contract-table entry by a pure function of the package.
- **Read from the table, not generated**: the per-kind dimension lists of Python (`_DIMENSIONS` in `hilclaw/harness/bf16_timing.py`, `_BF16_DIMENSIONS` in `hilclaw/standin_settings.py`) become the shape parameters of each contract's `task_contract`.
- **What the table must gain**: draw bits per operand and the scalar arguments, today only in C and in `bf16_verification_arrays.py`. They become constants of the contract modules. `task_contract` and `op_signature_record` do not change.
- **How "existing results unchanged" is verified**: items 1 to 4 of decision 6, which are this task's acceptance criteria 5 to 8.

**Order (DRIVER §6 D27 ①).** At planning time (main `995b34b6`) there was no open `nightly-failure` issue, no open PR, no `실패` item in `PROCESS/RuntimeAcceptance.md` and no P2-15 preparation pending. P3-3 is unchecked, but its remaining parts wait on HQ-0090 and HQ-0091 (ADR-0193 decision 8), so P3-5 is next (P3-4 is checked). Check this again before writing code. If something has changed, report it in `## Result` and stop.

**P2-15 must not change (D27).** The model executor (`model_forward*.py`, `model_forward.c`, `model_check.py`) and every program it builds are untouched. The harness programs of `rope` and `sdpa_kv_cache`, the fp32 `gemm` programs (`timing_driver.c`, `verification_program.c`) and the waiter (`timing_waiter.c`) stay handwritten (decision 6, "Stays handwritten").

**Open HQs not crossed (D27 ⑦).** HQ-0088 to HQ-0091 concern candidate kinds, the record format, the unit list and the oracle at `virtual_npu`. Nothing here depends on them, and `virtual_npu`'s behaviour does not change. HQ-0081 and HQ-0083 are other subjects. No fp16 (HQ-0083 (b)).

**D16.** Verification uses clang on the development machine and test kernels the tests write. No `claude`, no Docker, no test run (D25).

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0536-<slug>`, the `Task: T-0536` trailer and the PR body's last line, the size cap, D12, D21), §3 "BLOCKED 사유" and "승인된 열린 목록", §6 D27 and "task 단위" ④.
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (one line in the commit body and `## Result`), "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: decision 1 (the rows for P3-5), decision 6 in full, decision 8 (row P3-5), Consequences ("A-13 reading", "Less exact, not edited").
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` decisions 2 to 5 and 8 (program, command line, drawn inputs, output before the call, report). `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md` decisions 2 and 3. `ARCHITECTURE/decisions/ADR-0177-od18-od6-contract-table.md` decisions 1 and 2.
- Code, whole: `hilclaw/harness/bf16_verification_{gemm,rmsnorm,elementwise_add,swiglu}.c`, `hilclaw/harness/bf16_timing_{gemm,rmsnorm,elementwise_add,swiglu}.c`, `hilclaw/harness/bf16_verification.h`, `hilclaw/harness/bf16_timing.h`. Also `hilclaw/contract_table.py`, `hilclaw/{gemm,rmsnorm,elementwise_add,swiglu}_bf16_contract.py`, and `hilclaw/harness/bf16_verification_arrays.py` (`KINDS`, `EPS_BITS`, `draw_inputs`, `_shapes`, `_patterns`).
- Code, parts: `hilclaw/harness/bf16_timing.py` lines 1-80; `hilclaw/standin_settings.py` lines 110-200; `hilclaw/harness/bf16_verification_build.py` and `hilclaw/harness/bf16_timing_build.py` (how a program is built; not edited here); `hilclaw/harness/bf16_verification.py` (`program_arguments`, `judge_report`); `hilclaw/harness/timing.py` (`judge_report`).
- Tests: `tests/harness/test_bf16_verification_programs.py` and `tests/harness/test_bf16_timing_programs.py` (their test kernels, clang fixtures, strict flags and the CI rule for clang).

## Acceptance Criteria

1. **Contract constants.** Each of `hilclaw/{gemm,rmsnorm,elementwise_add,swiglu}_bf16_contract.py` gains public constants for what its programs draw and pass and the table does not hold yet:
   - the draw bits of each input operand, in the order the programs draw them (8 for every operand except `swiglu`'s `gate`, which is 10);
   - for `rmsnorm`, the binary32 bit pattern of `eps` (`0x3727C5AC`, whose value is the existing `EPS`).
   The executor names the constants and states the names in `## Result`. `task_contract`, `op_signature_record`, `covers` and every existing constant are unchanged. `hilclaw/harness/bf16_verification_arrays.py` takes its draw bits and `EPS_BITS` from these constants. `EPS_BITS` stays a public name with the same value, and `draw_inputs` returns the same arrays.
2. **Dimension lists from the table.** `_DIMENSIONS` in `hilclaw/harness/bf16_timing.py` and `_BF16_DIMENSIONS` in `hilclaw/standin_settings.py` are derived, for all six bf16 kinds, from the parameter names of the covering entry's `task_contract` in `hilclaw.contract_table.TABLE`, in their order. They are no longer written by hand. `KINDS`, `BF16_CHECK_KINDS`, the order of kinds and every function's behaviour are unchanged. If an import cycle or an existing import-boundary test forbids an import, the executor states which and uses the nearest import that satisfies it.
3. **The generator.** A new module `hilclaw/harness/bf16_program_generator.py` imports no NumPy and has these public names:
   - `GENERATED_KINDS`: the tuple `("gemm", "rmsnorm", "elementwise_add", "swiglu")`.
   - `verification_source(kind)`: the C source text of the verification program of `kind`, as a `str`.
   - `timing_source(kind)`: the same for the timing program.
   - `verification_name(kind)` and `timing_name(kind)`: the file names the program has today, for example `bf16_verification_swiglu.c` and `bf16_timing_swiglu.c`.

   Each source function reads the kind's bf16 entry of `contract_table.TABLE` and builds the text from it:
   - the function and prototype: `PROTOTYPE`;
   - the dimension and operand names, the operand shapes and roles: `task_contract`'s parameters and its operands, evaluated symbolically or by an equivalent reading the executor states;
   - the draw bits and the scalar: the constants of criterion 1.

   It is a pure function: no file is read or written, nothing is started, and nothing is kept between calls. A `kind` that is not exactly a `str` of `GENERATED_KINDS` raises `ValueError` with an attribute `parameter` `"kind"`, as the build modules do. `rope` and `sdpa_kv_cache` are refused. Any differences between kinds that the table cannot express, such as the form of a kind's size-overflow check, are kept in the generator as a small per-kind input, and `## Result` lists each one. A generator branch on a kind name, where a table value would serve, is a review finding.
4. **The generated programs are equivalent programs.** Each includes the same header as today (`bf16_verification.h` or `bf16_timing.h`, with quotes) and defines the same `PROGRAM` name. It has the same command line, argument checks, drawing order, offsets, check values, output fill, report, calls and exit statuses as the handwritten program of the same kind and form. The header comment of a generated program may be short. It says that the program was generated, the command line and the decision that rules it. The text need not equal the handwritten file.
5. **Verification reports equal byte for byte** (ADR-0193 decision 6 item 1). With clang present, the tests build each of the four kinds' generated and handwritten verification programs with the same test kernel and the strict flags of `tests/harness/test_bf16_verification_programs.py`. The generated source and copies of the headers go to a temporary directory. For each kind the tests run both programs with several dimension tuples (a 1 among them), at least two seeds and at least two draws. The tests assert that the reports are equal byte for byte.
6. **Timing digests equal** (decision 6 item 2). The tests build both timing programs of each kind with one test kernel. On every call, the kernel writes a digest of the operands it is called with (the dimensions and the input bytes) to standard error. The tests assert that the two programs' digests are equal and that both reports pass `hilclaw.harness.timing.judge_report` (through `hilclaw.harness.bf16_timing.run_bf16_timing`, or the way the existing timing program tests judge a report).
7. **Command lines, exit statuses and names equal** (decision 6 item 3). For each kind and form, the following give the same exit status and the same standard error from both programs:
   - a wrong argument count;
   - an argument that is not decimal digits;
   - a dimension of 0;
   - dimensions whose arrays do not fit in `size_t`.

   Both programs also give the same `PROGRAM` name in their messages.
8. **No result change** (decision 6 item 4). No `step` value, result definition, data-plane member or value changes. No contract-table entry is added, and no open list gets a value. If the work shows otherwise, stop and return `BLOCKED` (A-13; DRIVER §3 "승인된 열린 목록").
9. **Tests (D12).** Every public function of each touched or new module is covered by happy, error, branch and negative cases. New test file: `tests/harness/test_bf16_program_generator.py`. It holds criteria 3 to 7, including:
   - each refused `kind`: `rope`, `sdpa_kv_cache`, an unknown string, a non-`str`, a `str` subclass;
   - that the source functions read nothing from disk;
   - that the constants of criterion 1 equal the bits of today's programs.

   The clang tests follow the existing rule: skip without clang locally, fail on the CI runner. Package line and function coverage stay at or above 80 %. The full suite and `ruff check` / `ruff format --check` pass locally.
10. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21). Pinning assertions this task is expected to touch: the public-name assertions of the four contract modules' tests (the new constants); any import-list or allowed-importer assertion that names `contract_table` or the contract modules, once `bf16_timing.py`, `standin_settings.py` or `bf16_verification_arrays.py` import them (for example the allow-lists in `tests/test_contract_table.py` or `tests/test_standin_settings.py`, if any); and the public-name assertion of `hilclaw/harness/bf16_verification_arrays.py`'s test, if `EPS_BITS` moves. Each edited assertion is listed in the PR body.
11. **Size.** About 450 LOC and 8 files, tests excluded (DRIVER §5). If the change is seen to exceed 600 LOC or 10 files, land criteria 1 and 3 to 9, and propose criterion 2 as a split in `## Follow-ups`.
12. **`## Result`** states:
    - the language line (Python for the generator, as the harness's other Python modules);
    - the names of the new constants;
    - the per-kind inputs the generator keeps (criterion 3);
    - the edited assertions;
    - the public names T-0537 will call, if any differ from criterion 3.

## Out of Scope

- Changing what any build or operation compiles (`bf16_verification_build.py`, `bf16_timing_build.py`, `standin_check.py`, `standin_run.py`, `standin_copies.py`): T-0537.
- Removing or editing the handwritten `.c` files, or `hilclaw/harness/__init__.py`'s list of them: T-0538.
- `rope`, `sdpa_kv_cache`, fp32 `gemm`, the waiter, the headers `bf16_timing.h` and `bf16_verification.h`, and the references and work measures (decision 6, "Stays handwritten").
- Any edit of `ARCHITECTURE/`, PLAN or RuntimeAcceptance. ADR-0163 and ADR-0181 decision 2 become less exact (ADR-0193 Consequences), and only after T-0537 lands. They are not edited here.

## Follow-ups

## Result

- Landed PR #353 (squash c44f90bf), 1 review round (Approve), CI green.
- Language: Python, as the harness's other Python modules.
- New constants: `DRAW_BITS` in the `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` bf16 contracts; `EPS_BITS` in `rmsnorm`.
- Per-kind input kept in the generator: `_INPUTS_FIT_TOGETHER`.
- Public names for T-0537: `GENERATED_KINDS`, `verification_source`, `timing_source`, `verification_name`, `timing_name`.
- Edited pinning assertions (D21): the four contracts' `test_public_names_of_the_module`; `test_standin_settings.py::test_the_module_exposes_only_the_settings_and_the_time_limits`.
- Details in the PR body. No follow-ups, no runtime-acceptance items.
