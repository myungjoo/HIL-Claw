---
id: T-0461
title: Add the bf16 RoPE verification program bf16_verification_rope.c, which takes the freqs_cis rows on standard input, and register rope in bf16_verification_build.PROGRAM_SOURCES (ADR-0164 code slice 2)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0460]
touchesFiles: [hilclaw/harness/bf16_verification_rope.c, hilclaw/harness/bf16_verification_build.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification_rope.py, tests/harness/test_bf16_verification_build.py]
estimatedSize: {loc: 170, files: 3}
hq: []
---
## Why

**State on `main` `fe12fbce`.** ADR-0164 (T-0459, `f9b8096`) records how one built bf16 RoPE kernel (kind `rope`) is verified on `cpu_standin`. It lists four code slices in its Consequences (line 136). Slice 1 is done: T-0460 (`48f1d05`) gave `hilclaw.local_run.run` the optional `stdin_data` argument.

**This task is slice 2: "the program `bf16_verification_rope.c` and `rope` in `bf16_verification_build.PROGRAM_SOURCES`".**
- It adds a fifth verification program under `hilclaw/harness/`, built on the shared header `bf16_verification.h`, which stays unchanged.
- What is new compared with ADR-0163's four programs (ADR-0164 decisions 2 and 3): the program reads the m `freqs_cis` rows (4·m·d bytes) from standard input before its first draw and then requires end of input. It keeps them in a buffer of its own and copies them into the kernel's `freqs_cis` array before each call. The check value covers `x` followed by those rows.
- ADR-0164 decision 3 leaves the exit status for bad standard input "the code task's". This task fixes it at **5**, defined in the new program (not in the header) and documented in that program's header comment.

**Not in this slice.** Slice 3 is the Python side: drawing `x` in `bf16_verification_arrays`, the rows from `rope_table.build`, the reference, and judging the report with P and the bytes on standard input. Slice 4 is the three calibration kernels. Because slice 3 is not here, `bf16_verification_arrays.KINDS` and `bf16_verification.py` do not learn `rope` in this task. The tests compute the expected `x` and check values themselves (see criterion 7).

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items, and P2-14 needs them, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as it did for T-0451 to T-0460.

**D16.** The program is built with the local `clang` and run as a local process, with stub kernels that the test writes and input fed through `local_run.run(..., stdin_data=...)`. Nothing starts `claude` or needs a board, a model file or an API key. Where `clang` is absent, the clang tests skip locally and fail on CI, as the existing bf16 program tests do.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules.
  - For this task: branch `claude/T-0461-<slug>`; commit trailer `Task: T-0461`; code mode, so a Draft PR whose body ends with `Task: T-0461`.
- `CLAUDE.md`, "상시 규칙":
  - "코멘트 최소화" (the file boilerplate comment of a C source may be long);
  - "도구 계층 언어 정책";
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`:
  - the Decision preamble (line 32);
  - decision 2 (lines 40-43): program and process, the own buffer of rows;
  - decision 3 (lines 45-50): the rows on standard input, exact length, end of input, non-zero status;
  - decision 4 (lines 52-58): P stays on the Python side;
  - decision 6 (lines 65-68): `x` with b = 8, one sequence in memory order;
  - decision 7 (lines 70-76): the command line `<m> <h> <d> <draws> <seed>`, with `d` even;
  - decision 8 (lines 78-80): the output fill;
  - decision 9, the "Input check value" bullet: over `x`, then the rows as passed to the kernel;
  - decision 10 (lines 88-91): report length draws · (4 + 2·m·h·d) + E;
  - decision 13, item 4 (line 115): cost at the largest shape;
  - Consequences (lines 133-145) and Boundaries (lines 146-155).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 2 (lines 44-53);
  - decision 3 (lines 55-65);
  - decision 4 (lines 67-88);
  - decision 8 (lines 123-127).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`:
  - decision 6 (lines 62-66): the `x` layout `(i·h + j)·d + k` and the `freqs_cis` layout;
  - decision 9 (lines 79-86): the prototype and symbol;
  - decision 11 (lines 112-124): `d` even and ≥ 2, the obligations at a call.
- `hilclaw/harness/bf16_verification.h`: the whole file (185 lines). Use it as it is and do not edit it.
- `hilclaw/harness/bf16_verification_rmsnorm.c`: the whole file (96 lines). It is the model for the header comment, `PROGRAM`, the declaration, the argument and size checks, the draw loop and the end mark.
- `hilclaw/harness/bf16_verification_build.py`: the whole file (120 lines).
- `hilclaw/harness/__init__.py`: the package docstring (lines 1-25).
- `hilclaw/rope_bf16_contract.py`: lines 60-82 (`PROTOTYPE`, `SHAPES`, `X_PATTERNS`).
- `hilclaw/rope_table.py`: the `build` signature and docstring (from line 132).
- `hilclaw/local_run.py`: the `run` docstring (lines 85-110), in particular `stdin_data`.
- `hilclaw/harness/bf16_verification_arrays.py`:
  - the module docstring (lines 1-60);
  - `draw_inputs` (lines 98-121);
  - `widen`.
- `tests/harness/test_bf16_verification_programs.py`: the whole file (569 lines). It is the model for the session fixture, the stub kernels, the report splitting, the agreement tests and the refusal tests.
- `tests/harness/test_bf16_verification_build.py`:
  - lines 1-30;
  - lines 150-180;
  - lines 355-380;
  - lines 575-620.
- `.github/workflows/ci.yml` lines 73-100: the C gate compiles every tracked `*.c` alone with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.

## Acceptance Criteria

1. **The program `hilclaw/harness/bf16_verification_rope.c`.** It is written in C because it is linked with a C kernel into one executable and includes the C header (ADR-0163 decision 2, as ADR-0164 decision 2 applies it); say so in one line of the commit body. The program:
   - defines `_POSIX_C_SOURCE 200809L` and `PROGRAM` `"bf16_verification_rope"`, then includes `bf16_verification.h`;
   - declares `rope_bf16_contract.PROTOTYPE` byte for byte and calls `hilclaw_rope_bf16` exactly once per draw;
   - defines no identifier with external linkage other than `main`, and no name starting with `hilclaw_` other than the declared symbol;
   - does no floating-point arithmetic, converts no `float` and includes no `<math.h>`. The rows are bytes that it receives and copies, for example with `memcpy` into a `float` array;
   - **leaves `bf16_verification.h` unchanged**. If a needed change shows up, stop and propose it in Follow-ups instead of editing the header.
2. **Command line**: exactly `<m> <h> <d> <draws> <seed>` (ADR-0164 decision 7), with the `digits` rules of the existing programs: m, h, d ≥ 1 within `size_t`, 1 ≤ draws < 2^64, 0 ≤ seed < 2^64.
   - An odd `d` is refused with status 2 and one stderr line.
   - A wrong argument count gives status 2 and a usage line naming the five arguments.
   - No file and no environment variable is read.
3. **Sizes**: before allocation and before anything is read from standard input, check with `byte_size` (or an equivalent overflow check) that these fit in `size_t`:
   - the m·h·d elements of `x` and `out`, and their 2·m·h·d bytes;
   - the 4·m·d bytes of the rows.
   A failure, or a failed allocation, gives status 3 as in the existing programs.
4. **Standard input** (ADR-0164 decision 3). After the argument and size checks and before the first draw, the program reads exactly 4·m·d bytes into its own row buffer. It retries on `EINTR` and accepts reads of any length. It then requires end of input: one further read must return 0.
   - The program exits with **status 5** if standard input ends early (including empty input or the null device), has bytes beyond 4·m·d, or a read fails. It writes one stderr line starting with `bf16_verification_rope: ` and writes nothing on the report (no check value, no end mark).
   - Define the status in the program, for example `enum { STATUS_INPUT = 5 };`, and document it in the program's header comment next to the reference to the header's statuses.
   - The kernel is never called in that case.
5. **Per draw d**, using `draw_base(seed, d)`:
   - draw `x`: m·h·d elements, sequence indices 0 … m·h·d − 1, bits = 8, in memory order (ADR-0164 decision 6);
   - copy the row buffer into the kernel's `freqs_cis` array (m·d `float`s; a separate allocation from the buffer);
   - report the check value over the 2·m·h·d bytes of `x` followed by the 4·m·d bytes of the kernel's `freqs_cis` array (ADR-0164 decision 9);
   - fill `out` with `0x7FC0`;
   - call `hilclaw_rope_bf16(m, h, d, x, freqs_cis, out)`;
   - write the 2·m·h·d bytes of `out`.

   After the last draw, write `end\n`. A complete report has draws · (4 + 2·m·h·d) + 4 bytes. Descriptor 1 points at standard error before the first call (`report_open`). Status 0 is returned only after the end mark.
6. **Header comment** of the program, in the form of `bf16_verification_rmsnorm.c`. It states:
   - the command line;
   - the standard input (4·m·d bytes of binary32 patterns in host byte order, exactly, then end of input);
   - the inputs (`x` with bits = 8, the layout `x[(i*h + j)*d + k]` and `freqs_cis[i*d + c]`);
   - that the rows are copied from the program's buffer before every call;
   - the check value;
   - the report and its length;
   - the fill;
   - the exit statuses, including 5.

   It points to `bf16_verification.h` for the generator and the shared statuses instead of restating them. It must not claim that no standard input is read. The program compiles alone under the CI C gate command.
7. **`hilclaw/harness/bf16_verification_build.py`**:
   - Add `rope` as the last key of `PROGRAM_SOURCES`, so the order is gemm, rmsnorm, elementwise_add, swiglu, rope. It maps to `bf16_verification_rope.c` next to the module.
   - Update the module docstring: the rope program is ADR-0164's, and it reads the rows on standard input. Running it, and the input, stay the caller's, through `local_run.run(..., stdin_data=...)`. The module still runs nothing.
   - `build_bf16_verification_executable` behaves as before for the other kinds, and its error message lists the five kinds.
8. **`hilclaw/harness/__init__.py`**: update the docstring sentence on the C sources of the bf16 run so that it names five programs, with `bf16_verification_rope.c` of ADR-0164. Keep the claim about the modules that import `numpy` true.
9. **Size**: at most 300 changed lines outside tests, in at most 5 files. The expected files are the program, the build module and the package docstring. If the work would go over the cap, shorten the header comment, not the behaviour.
10. **Tests.**
   - **New file `tests/harness/test_bf16_verification_rope.py`.** Follow the fixture of `tests/harness/test_bf16_verification_programs.py`: a session fixture that builds each stub with `clang_build.build((program, kernel), output, flags=..., trailing_flags=("-lm",))`, skips without a POSIX system or without `clang`, and fails on CI (`GITHUB_ACTIONS == "true"`) without `clang`. Run every executable through `local_run.run(..., stdin_data=...)`. Follow D12 (DRIVER §5): happy, error, branch and negative cases. The **expected values are computed in the test**, since `bf16_verification_arrays` does not know `rope` yet:
     - expected `x` of draw d: `draw_inputs("elementwise_add", (m*h, d), seed=..., draw=d)[0]`, reshaped to (m, h, d). This is the same generator sequence (indices 0 … m·h·d − 1, bits = 8); say so in a short comment;
     - expected check value: `zlib.crc32` of the bytes of `x` followed by the bytes of the `float32` rows that were sent, packed as a host-order `uint32`.

     At least:
     - **Source**: the program is ASCII and declares `rope_bf16_contract.PROTOTYPE` byte for byte. It has no `<math.h>` and no `float` arithmetic operator on a `float` object; a textual check of the source for `<math.h>` is enough.
     - **Generator and row agreement (the ADR-0164 Consequences test)**: use seeds 0, 1, 2**63 and 2**64 − 1, at least two draws, and shapes including m = 1, h = 1 and d = 2.
       - Send rows P … P+m−1 from `rope_table.build(head_dim=d, theta=500000.0, scale_factor=8.0, low_freq_factor=1.0, high_freq_factor=4.0, old_context_len=8192, positions=P+m)`, for P = 0 and for P = 127 with m = 1.
       - Send also arbitrary `float32` bit patterns, including a NaN pattern and a negative zero, to show the bytes are passed through uninterpreted.
       - Each reported check value equals the expected one.
       - A stub that copies `x` into `out` reports exactly the expected `x`, at both ends of the array.
       - A stub that writes the bit patterns of `freqs_cis` (as two `uint16_t` halves, via `memcpy`) into `out` reports exactly the rows that were sent. Use h ≥ 2 so that `out` holds them.
     - **Rows are restored every draw**: a stub that casts away `const` and overwrites `freqs_cis` (and `x`) still gets, on the second draw, the check value expected for the original rows, and the copying stub sees the original rows.
     - **Plain bf16 kernel**: a stub that widens `x` by integer shift, computes y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c in `float` and rounds to bf16 by round-to-nearest-even on the bit pattern. Its reported output, passed through `widen`, is within a loose tolerance stated in the test (for example `atol` = 2**-7) of a test-local float64 rotation of the widened `x` with the sent rows broadcast over the heads. This checks layout and byte order, not the tolerance.
     - **Fill**: a stub that writes nothing reports `0x7FC0` in every element on every draw. A stub that writes only the first token reports `0x7FC0` in the other tokens on the second draw too.
     - **Calls and arguments**: one call per draw, and m, h and d reach the kernel.
     - **Kernel output on stderr**: what a stub prints to standard output appears on stderr, not in the report.
     - **Report length**: draws · (4 + 2·m·h·d) + 4 bytes, ending with `end\n`.
     - **Standard input refusals**, each with status 5, one stderr line starting with the program's name, empty stdout and no kernel call (for example a stub that would print a marker to stderr):
       - the null device (`stdin_data=None`);
       - `b""`;
       - one byte short;
       - one byte too many;
       - twice the expected bytes.
     - **Command-line refusals**, each with status 2 (or 3 for sizes), one stderr line and empty stdout:
       - wrong argument counts, including the four arguments of the other kinds and six arguments;
       - malformed arguments: sign, space, leading zero, empty, non-digit, zero dimension, zero draws, values past the range;
       - odd `d` (1 and 63);
       - dimensions whose arrays do not fit in `size_t` or cannot be allocated, refused before any standard input is read (status 3 with valid-length or empty input).
     - **Abnormal kernels**: a kernel that aborts leaves the report written so far; a kernel that never returns leaves the first check value (with a short run time limit).
     - Keep builds session-scoped, one per stub, and every test within a few seconds on a CI runner.
   - **Update `tests/harness/test_bf16_verification_build.py`.** Its tests compare `PROGRAM_SOURCES` with `bf16_verification_arrays.KINDS`, which has no `rope` until slice 3. Make them expect `KINDS + ("rope",)`, for example through a local constant. Remove `"rope"` from `BAD_KINDS`, and use another unknown kind in the "cannot be assigned to" test. Add one real-clang case for `rope`: a stub kernel that compiles, rows fed through `stdin_data`, and a complete report of the expected length. Keep the parametrized real-clang test of the four kinds as it is. Do not add tests that target test code (D12 ⑤).
11. **No other behaviour change**:
   - Leave these files unchanged: `bf16_verification.h`, the four existing programs and their tests, `bf16_verification_arrays.py`, `bf16_verification.py`, `rope_table.py`, `rope_bf16_contract.py`, `local_run.py`, the first case's files and the CI workflow.
   - Add no dependency.
   - The local `pytest` (with coverage at or above the 80 % line and function gates) and `ruff` are green, and the new `.c` file passes the C gate command locally where `clang` is available.
12. **Process**: code mode (CLAUDE.md A-13).
   - Open a Draft PR titled with `T-0461`, whose body ends with `Task: T-0461`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green (the C gate and the clang tests run there).
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - the read loop: exact length, end-of-input check, `EINTR`, status 5, nothing on the report;
     - the copy of the rows before every call into an array separate from the buffer;
     - the check value range (`x` then the kernel's rows) against ADR-0164 decision 9;
     - the element sequence and bits of `x` against ADR-0164 decision 6;
     - the report layout and length;
     - that every identifier except `main` is `static` or the declared symbol;
     - that the header and the other programs are unchanged.

## Out of Scope

- The Python side of the rope run (ADR-0164 slice 3): `rope` in `bf16_verification_arrays.KINDS`, `draw_inputs`, `reference`, `program_arguments`, the runner and judge in `bf16_verification.py`, P as a run parameter, and building the table in the harness.
- The three calibration kernels of ADR-0164 decision 11 (slice 4), and any change to the calibration tests or the CI calibration step.
- Any change to `bf16_verification.h`, to ADR-0017's first-case program, or to the four ADR-0163 programs.
- Registering `rope` with `correctness.check`, `spec.write` or the instance start (ADR-0164 Boundaries).
- SDPA with KV cache verification, the bf16 timing run, fp16.
- Editing ADR-0009, ADR-0017, ADR-0161, ADR-0163 or ADR-0164 (including the "less exact" sentences ADR-0164 Consequences lists).

## Follow-ups

- Next slice (planner candidate): ADR-0164 code slice 3, the Python side of the rope verification run.

## Result

- **Outcome**: DONE. PR #275 (https://github.com/myungjoo/HIL-Claw/pull/275), squash-merged as `4043e70a` with `--delete-branch`; the squash message is the PR body, ending with `Task: T-0461`. Branch commits: `17b6022d` (implementation and tests), `10858360` (round 1 docstring nits).
- **Review**: 2 rounds with a context-isolated dev-reviewer. Round 1: Approve with two docstring nits (doubled "and" in `hilclaw/harness/__init__.py`; summary line of `bf16_verification_build.py` named only ADR-0163), both fixed. Round 2: Approve, no findings.
- **CI**: all six gates green on head `10858360` (run 40155826829): C gate (clang), Python 3.11 and 3.14, Coverage, Test presence, shellcheck.
- **Local checks**: full `pytest` under coverage 31029 passed, 1575 skipped, line coverage 97 %; ruff check/format clean; the clang tests (skipped on Windows) ran under WSL: 550 passed across the three bf16 test files.
- **Changes**: new `hilclaw/harness/bf16_verification_rope.c` (command line `<m> <h> <d> <draws> <seed>`; odd d gives status 2; reads exactly 4·m·d bytes of freqs_cis rows from standard input, a short, longer or unreadable input gives the new status 5 with nothing written and no kernel call; per draw: draw x, copy the rows into `freqs_cis`, CRC-32 over x then `freqs_cis`, fill `out` with 0x7FC0, call the kernel, write `out`; `end\n` after the last draw). `rope` is the last key of `PROGRAM_SOURCES`; module and package docstrings updated. About 165 changed lines outside tests in 3 files; `bf16_verification.h` and the ADR-0163 programs unchanged.
- **Tests**: new `tests/harness/test_bf16_verification_rope.py` (criterion 10); `tests/harness/test_bf16_verification_build.py` expects `KINDS + ("rope",)`, uses `sdpa` as the unknown kind, adds one real-clang rope build fed through `stdin_data`.
- **Language**: C, because the program is linked with a C kernel into one executable and includes the C header `bf16_verification.h` (ADR-0163 decision 2, as ADR-0164 decision 2 applies it).
- **Follow-ups**: none new. Next: ADR-0164 code slice 3, the Python side of the rope verification run.
