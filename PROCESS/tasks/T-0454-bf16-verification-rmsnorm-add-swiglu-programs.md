---
id: T-0454
title: Add the bf16 verification programs for rmsnorm, elementwise_add and swiglu on the shared header, with clang tests that their inputs, check values and eps agree with bf16_verification_arrays (ADR-0163 code slice 3)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0453]
touchesFiles: [hilclaw/harness/bf16_verification_rmsnorm.c, hilclaw/harness/bf16_verification_elementwise_add.c, hilclaw/harness/bf16_verification_swiglu.c, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification_programs.py]
estimatedSize: {loc: 270, files: 4}
hq: []
---
## Why

**State on `main` `b434415`.** ADR-0163 (T-0451, `c004ccc`) records the verification run of one built bf16 kernel on `cpu_standin` for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`, with one C verification program per kind (decision 2). So far:
- T-0452 (`cafb152`) added the array side, `hilclaw/harness/bf16_verification_arrays.py`.
- T-0453 (`5e40098`) added the shared header `hilclaw/harness/bf16_verification.h` and the `gemm` program `hilclaw/harness/bf16_verification_gemm.c`, with a clang test that its generator and check value agree with the array module.

**This task is the third slice: the other three programs.** It adds them on the header, which stays unchanged. With this slice all four kinds of ADR-0163 can produce a report.
- Each program mirrors the `gemm` program. They differ in the symbol, the command line `<m> <n> <draws> <seed>` (ADR-0163 decision 3), the operand sizes and index widths (decision 4) and, for `rmsnorm`, the constant `eps` passed as the binary32 value of the bit pattern `0x3727C5AC` (decision 3).
- It also adds, for each kind, the generator agreement test that ADR-0163 Consequences asks for.
- The T-0453 Result follow-up (1) names this slice. It also asks that the sentence in `hilclaw/harness/__init__.py` naming exactly two C sources be updated.

**Size.** The `gemm` program is 87 lines, of which 37 are its header comment. Three programs of about that size, plus the docstring sentence, fit the cap of 300 lines in at most 5 files.

**Later slices (not here):**
- the build of a bf16 verification executable (the counterpart of `verification_build.py`);
- the report reader and the verdict over an executable (the counterpart of `verification.py`);
- the twelve calibration kernels of ADR-0163 decision 9.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12, both checklist items, and P2-14 needs it, so the D18 rule does not apply. Unresolved HQs still hold the round-loop items and P2-5: HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4. Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0453.

**D16.** Each program is built with the local `clang` and run as a local process with a stub kernel that the test writes. Nothing starts `claude` or needs a board, a model file or an API key. Where `clang` is absent, the clang tests skip locally and fail on CI, as `tests/harness/test_bf16_verification_gemm.py` does.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules. Branch `claude/T-0454-<slug>`; commit trailer `Task: T-0454`; code mode, so a Draft PR whose body ends with `Task: T-0454`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화" (the file boilerplate comment of a C source may be long), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, code mode).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - the Decision preamble (line 35);
  - decision 2 (lines 44-53): one program per kind, internal linkage, no floating-point arithmetic, `eps` formed from its bit pattern, no `<math.h>`, and a SwiGLU kernel may call `expf`;
  - decision 3 (lines 55-65): the command lines and the `eps` constant;
  - decision 4 (lines 67-88): the value sets (the `gate` set has b = 10), the index mapping and the element sequence (`x` then `w`; `gate` then `up`);
  - decision 5 (lines 90-93): the output fill `0x7FC0`;
  - decision 6, the "Input check value" bullet (line 110): `eps` is not covered by the check value, and that both sides use the same `eps` "is a test of the code slice";
  - decision 8 (lines 123-127): the report and its length;
  - Consequences (lines 183-193) and Boundaries (lines 195-207).
- `hilclaw/harness/bf16_verification.h`: the whole file (185 lines). Use it as it is. Do not edit it.
- `hilclaw/harness/bf16_verification_gemm.c`: the whole file (87 lines). It is the model for each new program: the header comment, `PROGRAM`, the declaration, the argument and size checks, the draw loop and the end mark.
- `hilclaw/harness/bf16_verification_arrays.py`: the module docstring (lines 1-60), `EPS_BITS` (line 93), `draw_inputs` (lines 98-121), `check_value`, `widen`, `reference` and `count_failures`.
- `tests/harness/test_bf16_verification_gemm.py`: the whole file (448 lines). It is the model for the fixture, the stub kernels, the report splitting, the agreement tests and the refusal tests.
- `PROTOTYPE` in `hilclaw/rmsnorm_bf16_contract.py` (lines 60-64, with `EPS` at line 67), `hilclaw/elementwise_add_bf16_contract.py` (lines 59-63) and `hilclaw/swiglu_bf16_contract.py` (lines 64-68).
- `hilclaw/clang_build.py` lines 1-20 and the `build` docstring (from line 196): `flags` go before the sources and `trailing_flags` after them, which is where a `-lm` for a stub that calls `expf` goes.
- `hilclaw/harness/__init__.py` (the package docstring, lines 1-21).
- `.github/workflows/ci.yml` lines 73-100: the C gate compiles every tracked `*.c` alone with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.

## Acceptance Criteria

1. **Three programs**, `hilclaw/harness/bf16_verification_rmsnorm.c`, `hilclaw/harness/bf16_verification_elementwise_add.c` and `hilclaw/harness/bf16_verification_swiglu.c`. They are written in C because each is linked with a C kernel into one executable and includes the C header (ADR-0163 decision 2); say this in one line of the commit body. Each program:
   - defines `_POSIX_C_SOURCE 200809L` and `PROGRAM` (`"bf16_verification_<kind>"`), then includes `bf16_verification.h`;
   - declares the kind's `PROTOTYPE` byte for byte;
   - calls the kind's symbol once per draw;
   - defines no identifier other than `main` with external linkage, and no name starting with `hilclaw_` other than the declared symbol;
   - does no floating-point arithmetic and includes no `<math.h>` (decision 2);
   - **leaves `bf16_verification.h` unchanged**. If a needed change shows up, stop and propose it in Follow-ups instead of editing the header.
2. **Command line**: exactly `<m> <n> <draws> <seed>` (decision 3), with the `digits` rules and ranges of the `gemm` program: m, n ≥ 1 within `size_t`, 1 ≤ draws < 2^64, 0 ≤ seed < 2^64. A wrong argument count gives status 2 and a usage line naming the four arguments. No standard input, file or environment variable is read.
3. **Per draw d**, using `draw_base(seed, d)`:
   - **`rmsnorm`**: draw `x` (m·n elements, sequence indices 0 … m·n − 1) and then `w` (n elements, indices m·n … m·n + n − 1), both with bits = 8. Report the check value over `x`, then `w`. Fill `y` with `0x7FC0`. Call `hilclaw_rmsnorm_bf16(m, n, eps, x, w, y)`. Write the m·n elements of `y`.
   - **`eps`**: the binary32 value with bit pattern `0x3727C5AC`, which is `bf16_verification_arrays.EPS_BITS` and `rmsnorm_bf16_contract.EPS`. Form it from that integer without floating-point arithmetic and without converting text to float, for example by `memcpy` from a `uint32_t`. That needs `<string.h>` in the program, since the header does not include it.
   - **`elementwise_add`**: draw `a` (m·n elements, indices 0 … m·n − 1) and then `b` (m·n elements, indices m·n … 2·m·n − 1), both with bits = 8. Report the check value over `a`, then `b`. Fill `c` and call `hilclaw_elementwise_add_bf16(m, n, a, b, c)`.
   - **`swiglu`**: draw `gate` (m·n elements, indices 0 … m·n − 1) with **bits = 10**, and then `up` (m·n elements, indices m·n … 2·m·n − 1) with bits = 8. Report the check value over `gate`, then `up`. Fill `out` and call `hilclaw_swiglu_bf16(m, n, gate, up, out)`.
   - **Sizes**: every array byte size and the total element count of a draw are checked with `byte_size` (or an equivalent check) before allocation. That includes the `elementwise_add` and `swiglu` second-operand start index 2·m·n, which must fit in `size_t`. Failures give status 3 as in the `gemm` program.
4. **Report and statuses** as the `gemm` program and ADR-0163 decision 8:
   - per draw, the 4-byte check value, then the 2·m·n output bytes;
   - after the last draw, `end\n`, so a complete report has draws · (4 + 2·m·n) + 4 bytes;
   - descriptor 1 points at standard error before the first call;
   - exit status 0 only after the end mark; 2, 3 and 4 as the header states, each with one stderr line starting with the program's name and without the end mark.
5. **Header comment of each program**, in the form of the `gemm` program's: the command line, the inputs (operands, sequence indices, bits and layout `x[i*n + j]`, `w[j]`), the check value, the report, the fill and the exit statuses. Point to `bf16_verification.h` for the generator and statuses instead of restating them. For `rmsnorm`, also state the `eps` constant and where its value comes from (ADR-0163 decision 3). Shorter comments than the `gemm` program's are fine. Each program compiles alone under the CI C gate command.
6. **`hilclaw/harness/__init__.py`**: rewrite the last sentence of the docstring so that it names the shared header and the four programs of the bf16 verification run. Keep the existing claim about the three modules that import `numpy` true. No Python module changes behaviour, and this slice adds no build module.
7. **Size**: at most 300 changed lines outside tests, in at most 5 files. Expected: the three programs and the `__init__.py` docstring. If the work would go over the cap, shorten header comments, not behaviour. If it would still go over, finish the `rmsnorm` and `elementwise_add` programs, propose a split in Follow-ups, and leave `swiglu` for the next slice.
8. **Tests**, in the new file `tests/harness/test_bf16_verification_programs.py`. Follow the fixture of `tests/harness/test_bf16_verification_gemm.py`: a session fixture that builds stub kernels with `clang_build.build((program, kernel), output, ...)`; skip without a POSIX system or without `clang`, but fail on CI without `clang`. Parametrize over the three kinds where the behaviour is the same. Follow D12 (DRIVER §5): happy, error, branch and negative cases. At least:
   - **Source**: each program is ASCII and declares its contract module's `PROTOTYPE` byte for byte.
   - **Generator agreement (the ADR-0163 Consequences test), per kind**: use several seeds (0, 1, 2**63 and 2**64 − 1), at least two draws, and a few shapes including m = 1 and n = 1. With stub kernels that copy the first operand and that copy the second operand into the output, each reported check value must equal `check_value(*draw_inputs(kind, (m, n), seed=…, draw=…))` packed as a host-order `uint32`, and each reported output element must equal the pattern copied from `draw_inputs`. For `rmsnorm`, the copied `w` fills each row of `y`. Cover elements at both ends of each operand.
   - **swiglu index width**: over enough elements, the reported `gate` patterns include values outside the b = 8 set (magnitude ≥ 1) and every one lies in `swiglu_bf16_contract.GATE_PATTERNS`. The `up` patterns all lie in `UP_PATTERNS`.
   - **`eps`**: a `rmsnorm` stub writes the bit pattern of the `eps` it receives (through `memcpy`, as two `uint16_t` halves) into the output. The reported bits equal `EPS_BITS`, and `EPS_BITS` as a binary32 equals `rmsnorm_bf16_contract.EPS`. This is the code-slice test that ADR-0163 decision 6 names.
   - **Plain bf16 kernels**: for each kind, a stub that widens by integer shifts, computes in `float` and rounds to bf16 by round-to-nearest-even on the bit pattern. Passing the reported output through `widen` and `count_failures` against `reference(kind, …)` must give no failing element under a loose tolerance stated in the test. The `rmsnorm` stub may use `sqrtf` and the `swiglu` stub `expf`; build those stubs with `-lm` in `trailing_flags`. This checks the report's layout and byte order, not the tolerance.
   - **Fill**: a stub that writes nothing reports `0x7FC0` in every element on every draw. A stub that writes only the first row reports `0x7FC0` in the other rows on the second draw too, so no element is stale.
   - **Calls and arguments**: one call per draw, and m and n reach the kernel, for example through a stub that writes them into the output.
   - **Kernel output on stderr**: what a stub prints to standard output appears on stderr, not in the report.
   - **Report length**: draws · (4 + 2·m·n) + 4 bytes, ending with `end\n`.
   - **Refusals**, per kind. Each gives its exit status, one stderr line starting with the program's name, and empty stdout:
     - wrong argument count, including the five arguments of `gemm`;
     - malformed arguments: sign, space, leading zero, empty, non-digit, zero dimension, zero draws, values past the range;
     - arrays whose size does not fit in `size_t` or cannot be allocated.
   - **Abnormal kernels**, for at least one kind: a kernel that aborts leaves the report written so far, and a kernel that never returns leaves the first check value (with a short run time limit).
   - No test may take more than a few seconds on a CI runner. Keep the number of builds small, for example one session-scoped build per (kind, stub).
9. **No other behaviour change**:
   - Leave unchanged `bf16_verification.h`, `bf16_verification_gemm.c`, `tests/harness/test_bf16_verification_gemm.py`, `bf16_verification_arrays.py`, the first case's files (`verification_program.c`, `verification_build.py`, `verification.py`, `verification_arrays.py`), the contract modules and the CI workflow.
   - Add no dependency.
   - The local `pytest` and `ruff` runs are green, and each new `.c` file passes the C gate command locally where `clang` is available.
10. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0454`, whose body ends with `Task: T-0454`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green (the C gate and the clang tests run there).
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least:
      - each program's operand order, sizes, sequence indices and bits against ADR-0163 decision 4 and `draw_inputs`;
      - the `eps` bit pattern and that it is formed without floating-point arithmetic;
      - the report layout and length against ADR-0163 decision 8;
      - that every identifier except `main` is `static` or the declared contract symbol;
      - that the header, the `gemm` program and the first case are unchanged.

## Out of Scope

- Any change to `bf16_verification.h` or to the `gemm` program and its test.
- A build module for bf16 verification executables, the report reader, the verdict over an executable and the broken conditions (the Python side of ADR-0163 decision 8).
- The calibration kernels of ADR-0163 decision 9, and any change to `test_calibration.py` or the CI calibration step.
- RoPE and SDPA, the bf16 timing run, and fp16.
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Tolerance values or defaults, seed sources, the number of draws, another `eps`, OpenMP or other build settings.
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next slice: the build of a bf16 verification executable (the counterpart of `verification_build.py`, one program per kind chosen by kind). After that, the report reader and the verdict over an executable (the counterpart of `verification.py`, ADR-0163 decision 8), and then the calibration kernels (decision 9).

## Result
