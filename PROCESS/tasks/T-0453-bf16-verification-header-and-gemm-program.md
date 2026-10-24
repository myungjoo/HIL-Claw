---
id: T-0453
title: Add the shared C header of ADR-0163's bf16 verification programs and the first program, for bf16 gemm, with a clang test that its inputs and check values agree with bf16_verification_arrays (ADR-0163 code slice 2)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0452]
touchesFiles: [hilclaw/harness/bf16_verification.h, hilclaw/harness/bf16_verification_gemm.c, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification_gemm.py]
estimatedSize: {loc: 270, files: 3}
hq: []
---
## Why

**State on `main` `f387802`.** ADR-0163 (landed as `c004ccc`, T-0451) records the verification run of one built bf16 kernel on `cpu_standin` for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. T-0452 (PR #267, `cafb152`) added its array side in `hilclaw/harness/bf16_verification_arrays.py`: the generator, the check value, the widening, the float64 reference and the failure counts. No C program exists yet, so no bf16 kernel can be run.

**This task is the second slice: the C side's shared code and the first program.**
- ADR-0163 decision 2 asks for **one verification program per kind**, four C sources under `hilclaw/harness/`. Code they share (generator, check value, report writer) "may be one header of the harness included by each; that is the code task's", and every identifier a program defines besides `main` has internal linkage (`static`).
- This slice writes that header and the `gemm` program, the counterpart of the first case's `verification_program.c` for `hilclaw_gemm_bf16`. `gemm` comes first because it is the first case's kind and has the same command line shape (`<m> <k> <n> <draws> <seed>`).
- It also adds the test ADR-0163 Consequences names: "A test that needs clang shows that the two generators agree". The test compares the program's check values and its reported input-derived outputs with `draw_inputs` and `check_value` of the array module.
- Four programs plus a header would exceed the size cap, so the other three programs come in the next slice. They reuse this header unchanged.

**Later slices (not here):**
- the `rmsnorm`, `elementwise_add` and `swiglu` programs;
- the build of a bf16 verification executable (the counterpart of `verification_build.py`);
- the report reader and the verdict over an executable (the counterpart of `verification.py`);
- the twelve calibration kernels (ADR-0163 decision 9).

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12, both checklist items, and P2-14 needs it, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14.

**D16.** The C program is built with the local `clang` and run as a local process with a stub kernel written by the test. Nothing starts `claude` or needs a board, a model file or an API key. Where `clang` is absent the clang tests skip locally (and fail on CI), as `tests/harness/test_verification_program.py` does.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules. Branch `claude/T-0453-<slug>`; commit trailer `Task: T-0453`; code mode, so a Draft PR whose body ends with `Task: T-0453`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화" (the file boilerplate comment of a C source may be long), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, code mode).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - the Decision preamble (line 35);
  - decision 2 (lines 44-53): one program per kind, the shared header, internal linkage, no floating-point arithmetic, no `<math.h>`;
  - decision 3 (lines 55-65): the command line;
  - decision 4 (lines 67-88): the value sets, the index mapping, the words, the element order;
  - decision 5 (lines 90-93): the output fill `0x7FC0`;
  - decision 6, the "Input check value" bullet (line 110);
  - decision 8 (lines 123-127): the report and its length;
  - Consequences (lines 183-193) and Boundaries (lines 195-207).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: decisions 2, 3, 4, 7 and 9 (the first case's program, which this slice mirrors).
- `hilclaw/harness/verification_program.c`: the whole file (224 lines). It is the model for the header comment, the argument rules (`digits`), the size checks, `mix`, the CRC-32 table, the report descriptor, `emit`, the exit statuses and the stderr line.
- `hilclaw/harness/bf16_verification_arrays.py`: the module docstring (lines 1-60) states the generator and the check value the C side must reproduce bit for bit; `draw_inputs`, `check_value` and `widen` are what the test compares against.
- `tests/harness/test_verification_program.py`: the whole file (392 lines). It is the model for the clang fixture, the stub kernels, the report splitting and the refusal tests.
- `hilclaw/gemm_bf16_contract.py`: `PROTOTYPE` (lines 56-60) and `INPUT_PATTERNS`.
- `hilclaw/harness/__init__.py` (the package docstring that lists the harness files).
- `.github/workflows/ci.yml` lines 73-100: the C gate compiles every tracked `*.c` alone with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.

## Acceptance Criteria

1. **Shared header `hilclaw/harness/bf16_verification.h`** (C; give the reason for the language in one line of the commit body). It holds the code the four programs of ADR-0163 decision 2 share and nothing specific to one kind:
   - the argument parser of the first case (`digits`: decimal digits, no sign, space or leading zero, within a range), the size check, the error line and the exit statuses 2, 3 and 4 with the meanings of `verification_program.c`;
   - `mix`, `GOLDEN` and the word of an element exactly as the docstring of `bf16_verification_arrays.py` states them;
   - **one** function that fills a `uint16_t` array of `count` elements from `base`, the index of its first element in the draw's sequence and the index width `bits` (8 or 10), using the two mappings of ADR-0163 decision 4. One function serves every operand of every kind;
   - the bf16 output fill with `0x7FC0`, written as an integer;
   - the CRC-32 of `zlib.crc32` (reflected polynomial `0xEDB88320`, initial value and final XOR `0xFFFFFFFF`) over the first operand's bytes, then the second's;
   - the report descriptor setup (descriptor 1 pointed at standard error before the first call, the original standard output kept) and the write loop.
   - **Internal linkage only**: every identifier is `static` (ADR-0163 decision 2), and no name starts with `hilclaw_`.
   - **No warning in a program that uses only part of it**: a program for another kind may not call every function, so define the functions so that `-Wall -Wextra -Wpedantic -Werror` gives no unused-function warning in that case (for example `static inline`, or a check that clang does not warn for unused `static` functions defined in a header). Show this in the commit body.
   - The stderr line names the program that failed. How the header learns that name is the executor's choice.
   - A header comment states what the header provides and that it is included by each bf16 verification program. The generator is stated once, here or in the program; the other place points to it.
   - It needs the C library and POSIX.1-2008 only: no `<math.h>`, no floating-point arithmetic (ADR-0163 decision 2).
2. **Program `hilclaw/harness/bf16_verification_gemm.c`**. It includes the header and calls `hilclaw_gemm_bf16` once per draw:
   - **Declaration**: `PROTOTYPE` of `hilclaw/gemm_bf16_contract.py` byte for byte.
   - **Command line**: exactly `<m> <k> <n> <draws> <seed>`, with the digit rules and ranges of the first case (m, k, n ≥ 1 within `size_t`, 1 ≤ draws < 2^64, 0 ≤ seed < 2^64). No standard input, file or environment variable is read.
   - **Per draw d**: draw `a` (m·k elements, sequence indices 0 … m·k − 1) and then `b` (k·n elements, indices m·k … m·k + k·n − 1), both with b = 8; write the check value as the 4 bytes of a `uint32_t`; fill `c` with `0x7FC0`; call the kernel; write the m·n elements of `c` as their 2·m·n bytes in memory order.
   - **After the last draw**: the end mark `end\n`. A complete report has draws · (4 + 2·m·n) + 4 bytes (ADR-0163 decision 8).
   - Exit status 0 only after the end mark; 2, 3 and 4 as the first case, each with one stderr line and without the end mark.
   - A header comment in the form of `verification_program.c`'s: the command line, the inputs (or a pointer to the header's statement), the check value, the report, the fill, the exit statuses.
   - It compiles alone under the CI C gate (`-std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`).
3. **No Python module changes behaviour.** Add one sentence to the docstring of `hilclaw/harness/__init__.py` naming the header and the `gemm` program as C sources of the bf16 verification run of ADR-0163. Keep its existing claim about the three modules that import `numpy` true. No build module in this slice: the tests build with `hilclaw.clang_build.build((program, kernel), output, ...)` as the first case's program test does.
4. **Size**: at most 300 changed lines outside tests, in at most 5 files. Expected: the header, the program, and the one sentence in `__init__.py`. If it would exceed the cap, move code from the header comment, not behaviour, and propose a split in Follow-ups.
5. **Tests**, in the new file `tests/harness/test_bf16_verification_gemm.py`, following `tests/harness/test_verification_program.py` (session fixture that builds stub kernels with `clang`, skipped without a POSIX system or `clang`, failing on CI without `clang`). Follow D12 (DRIVER §5): happy, error, branch and negative cases. At least:
   - **Source**: the program and the header are ASCII, and the program declares `gemm_bf16_contract.PROTOTYPE` byte for byte.
   - **Generator agreement (the ADR-0163 Consequences test)**: for several seeds (including 0, 2**63 and 2**64 − 1), several draws and a few shapes (including dimensions of 1), with stub kernels that copy `a` into `c` and that copy `b` into `c`, every reported check value equals `bf16_verification_arrays.check_value(*draw_inputs("gemm", (m, k, n), seed=…, draw=…))` packed as a host-order `uint32`, and every reported output element equals the pattern the stub copied from `draw_inputs`. Cover elements from both ends of each operand.
   - **Fill**: a stub that writes nothing reports `0x7FC0` in every element on every draw; a stub that writes only the first row reports `0x7FC0` in the rest on the second draw too (no stale element).
   - **One call per draw**, and the arguments m, k, n reach the kernel (for example a stub that writes them into the output).
   - **Kernel output on stderr**: what a stub prints to standard output appears on stderr, not in the report.
   - **A plain bf16 kernel**: a stub that widens with integer shifts, accumulates in `float` and rounds to bf16 by round-to-nearest-even on the bit pattern gives a report whose output, through `widen` and `count_failures` against `reference("gemm", …)`, has no failing element under a loose tolerance stated in the test. This shows the report's layout and byte order, not the tolerance.
   - **Report length**: draws · (4 + 2·m·n) + 4 bytes, ending with `end\n`.
   - **Refusals** (each with its exit status, one stderr line, empty stdout): wrong argument count; malformed arguments (sign, space, leading zero, empty, non-digit, zero dimension, zero draws, values past the range); arrays whose size does not fit in `size_t` or cannot be allocated.
   - **Abnormal kernels**: a kernel that aborts leaves the report written so far; a kernel that never returns leaves the first check value (with a short run time limit).
   - No test may need more than a few seconds on a CI runner.
6. **No behaviour change** to `verification_program.c`, `verification_build.py`, `verification.py`, `verification_arrays.py`, `bf16_verification_arrays.py`, the contract modules, the CI workflow or anything else. No new dependency. The local `pytest` and `ruff` runs are green, and the new `.c` file passes the C gate command locally where `clang` is available.
7. **Process**: code mode (CLAUDE.md A-13).
   - Draft PR titled with `T-0453`; its body ends with `Task: T-0453`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green (the C gate and the clang tests run there).
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - the header's generator, mapping and element order against the docstring of `bf16_verification_arrays.py` and ADR-0163 decision 4;
     - that every identifier of the header and program is `static` except `main`, and none starts with `hilclaw_`;
     - the report layout and length against ADR-0163 decision 8;
     - that the program does no floating-point arithmetic and needs no `<math.h>` (decision 2);
     - that nothing of the first case changed.

## Out of Scope

- The `rmsnorm`, `elementwise_add` and `swiglu` programs.
- A build module for bf16 verification executables, the report reader, the verdict over an executable and the broken conditions (ADR-0163 decision 8 on the Python side).
- The calibration kernels of ADR-0163 decision 9 and any change to `test_calibration.py` or the CI calibration step.
- RoPE and SDPA, the bf16 timing run, fp16.
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Tolerance values or defaults, seed sources, the number of draws, OpenMP or other build settings.
- Any edit to `ARCHITECTURE/` or `PROCESS/` (except this task file's `## Result`).
- The PLAN "보류" items.

## Follow-ups

- (planner) Next slice: the `rmsnorm` (with `eps` = `0x3727C5AC` passed as a binary32 formed from its bit pattern, ADR-0163 decision 3), `elementwise_add` and `swiglu` (`gate` with b = 10) programs on this header, each with a clang agreement test against `draw_inputs` and `check_value`. After that: the build module, the report reader and verdict, and the calibration kernels (ADR-0163 decisions 2, 8 and 9).

## Result
