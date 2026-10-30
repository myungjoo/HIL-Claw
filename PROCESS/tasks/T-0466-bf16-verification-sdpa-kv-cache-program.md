---
id: T-0466
title: Add the bf16 SDPA-with-KV-cache verification program bf16_verification_sdpa_kv_cache.c, with guarded cache allocations and a check value over five ranges, and register sdpa_kv_cache in bf16_verification_build.PROGRAM_SOURCES (ADR-0165 code slice 1)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0465]
touchesFiles: [hilclaw/harness/bf16_verification_sdpa_kv_cache.c, hilclaw/harness/bf16_verification_build.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification_sdpa_kv_cache.py, tests/harness/test_bf16_verification_build.py]
estimatedSize: {loc: 200, files: 3}
hq: []
---
## Why

**State on `main` `0dd9e916`.** ADR-0165 (T-0465, `24d4e0a4`) records how one built bf16 SDPA-with-KV-cache kernel (kind `sdpa_kv_cache`, contract ADR-0162) is verified on `cpu_standin`. Its Consequences (line 146) list four code slices in landing order. None has landed.

**This task is slice 1: "the program `bf16_verification_sdpa_kv_cache.c` — with a check value over more than two byte ranges, a change of the shared header or a function of the program — and `sdpa_kv_cache` in `bf16_verification_build.PROGRAM_SOURCES`".**
- It adds a sixth verification program under `hilclaw/harness/`, built on the shared header `bf16_verification.h`.
- **This task picks "a function of the program"**: a `static` CRC-32 function in the new program over a list of byte ranges. The header stays unchanged, so the five existing programs and their tests are not touched.
- Compared with ADR-0163's programs, the new parts are:
  - seven arguments, with the cross-dimension rules l ≥ m and h a multiple of h_kv (ADR-0165 decision 3);
  - five drawn ranges, the last two being only the first P = l − m rows of each cache (decision 4);
  - each cache held in one allocation of l + 2m rows: m guard rows, the l operand rows, then m guard rows. The kernel gets the address of the first operand row. Before every call, rows P … l − 1 and all guard rows are set to `0x7FC0` (decision 5);
  - a check value over `q`, `k_new`, `v_new` and the two whole allocations (decision 7);
  - a report holding, per draw, the check value, `out` and the two whole allocations (decision 8).
- Like ADR-0163's programs, and unlike `rope`, the program reads **no standard input** (ADR-0165 decision 2).

**Not in this slice.**
- Slice 2 is the array side: the draw of the five ranges, the allocations with their fills, the check value, the per-head reference, and the expected allocations.
- Slice 3 is the runner and judge. Slice 4 is the four calibration kernels.
- So no Python module learns `sdpa_kv_cache` here except `PROGRAM_SOURCES`. The tests compute the expected inputs, fills and check values themselves (criterion 10).

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items, and P2-14 needs them, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4). So work continues on P2-11 to P2-14, as it did for T-0451 to T-0465.

**D16.** The program is built with the local `clang` and run as a local process, with stub kernels that the test writes. Nothing starts `claude`, and nothing needs a board, a model file or an API key. Where `clang` is absent, the clang tests skip locally and fail on CI, like the existing bf16 program tests.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules.
  - For this task: branch `claude/T-0466-<slug>`; commit trailer `Task: T-0466`; code mode, so a Draft PR whose body ends with `Task: T-0466`.
- `CLAUDE.md`, "상시 규칙":
  - "코멘트 최소화" (the file boilerplate comment of a C source may be long);
  - "도구 계층 언어 정책";
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md`:
  - the Decision preamble (line 33);
  - decision 1 (lines 35-39);
  - decision 2 (lines 41-44): program and process, no standard input;
  - decision 3 (lines 46-52): the command line, the cross-dimension rules, status 2 and status 3;
  - decision 4 (lines 54-59): b = 8, one sequence per draw in the order `q`, `k_new`, `v_new`, cache_k rows 0 … P − 1, cache_v rows 0 … P − 1;
  - decision 5 (lines 61-67): the allocations of l + 2m rows, the fills, a fresh fill every draw;
  - decision 7 (lines 77-80): the check value over the whole allocations, without `out`;
  - decision 8, first bullet (line 84): the report content and length;
  - decision 10 (lines 98-104): for context on the later calibration kernels only;
  - decision 11, last row (line 115): the mechanism constants;
  - decision 12, item 4 (line 122): cost at the largest shape;
  - Consequences (lines 143-151) and Boundaries (lines 153-163).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`:
  - decision 4 (lines 52-59): cache layout `(t·h_kv + g)·d + e`, what the kernel writes;
  - decision 5 (lines 61-67): the layouts of `q`, `k_new`, `v_new`, `out`;
  - decision 9 (lines 94-102): the prototype and symbol;
  - decision 11 (lines 133-148): the obligations at a call.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 2 (lines 44-54);
  - decision 3 (lines 55-66);
  - decision 4 (lines 67-89);
  - decision 5 (lines 90-94);
  - decision 8 (lines 123-128).
- `hilclaw/harness/bf16_verification.h`: the whole file (185 lines). Use it as it is and do not edit it. Note that `check_value` takes exactly two ranges, and that `draw_patterns` takes the first sequence index as a `uint64_t`.
- `hilclaw/harness/bf16_verification_rmsnorm.c`: the whole file (96 lines). It is the model for the header comment, `PROGRAM`, the declaration, the argument and size checks, the draw loop and the end mark.
- `hilclaw/harness/bf16_verification_build.py`: the whole file (126 lines).
- `hilclaw/harness/__init__.py`: the package docstring (lines 1-30).
- `hilclaw/sdpa_kv_cache_bf16_contract.py`: lines 66-82 (`PROTOTYPE`, `SHAPES`, `INPUT_PATTERNS`).
- `hilclaw/harness/bf16_verification_arrays.py`:
  - the module docstring (lines 1-60);
  - `draw_inputs` (lines 98-121);
  - `widen`.
- `tests/harness/test_bf16_verification_rope.py`: the whole file (567 lines). It is the model for the session fixture, the stub kernels, the report splitting, the agreement tests and the refusal tests.
- `tests/harness/test_bf16_verification_build.py`:
  - lines 1-50 (`PROGRAM_KINDS`);
  - lines 150-180;
  - lines 360-380;
  - lines 575-651 (the real-clang cases, including the `rope` one).
- `.github/workflows/ci.yml` lines 70-90: the C gate compiles every tracked `*.c` alone with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.

## Acceptance Criteria

1. **The program `hilclaw/harness/bf16_verification_sdpa_kv_cache.c`.** It is written in C because it is linked with a C kernel into one executable and includes the C header (ADR-0163 decision 2, as ADR-0165 decision 2 applies it). Say so in one line of the commit body. The program:
   - defines `_POSIX_C_SOURCE 200809L` and `PROGRAM` `"bf16_verification_sdpa_kv_cache"`, then includes `bf16_verification.h`;
   - declares `sdpa_kv_cache_bf16_contract.PROTOTYPE` byte for byte;
   - calls `hilclaw_sdpa_kv_cache_bf16` exactly once per draw;
   - defines no identifier with external linkage other than `main`, and no name starting with `hilclaw_` other than the declared symbol;
   - does no floating-point arithmetic, has no `float` object and includes no `<math.h>`;
   - reads no standard input, no file and no environment variable;
   - **leaves `bf16_verification.h` unchanged**. If a needed change shows up, stop and propose it in Follow-ups instead of editing the header.
2. **Check value over five ranges.** Add one `static` function in the program that computes the CRC-32 of `zlib.crc32` (reflected polynomial `0xEDB88320`, initial value and final XOR `0xFFFFFFFF`) over a sequence of byte ranges given in order, for example an array of pointer and length pairs.
   - It must give the same value as the header's `check_value` for two ranges. Do not call `check_value`.
   - Do not join operands into one allocation just to reduce the number of ranges. Each of `q`, `k_new`, `v_new`, `out` and the two cache allocations is its own `malloc` (ADR-0165 decision 5: "Each cache is one allocation").
3. **Command line**: exactly `<m> <l> <h> <h_kv> <d> <draws> <seed>` (ADR-0165 decision 3), using the header's `digits`:
   - m, l, h, h_kv, d ≥ 1 within `size_t`; 1 ≤ draws < 2^64; 0 ≤ seed < 2^64.
   - l < m gives status 2 and one stderr line. So does an h that is not a multiple of h_kv.
   - A wrong argument count gives status 2 and a usage line naming the seven arguments.
   - P is not an argument. The program derives it as l − m.
4. **Sizes** (status 3, as in the existing programs). Before any allocation, check that each of these fits in `size_t`:
   - the m·h·d elements of `q` and `out`, and their bytes;
   - the m·h_kv·d elements of `k_new` and `v_new`, and their bytes;
   - l + 2m;
   - the (l + 2m)·h_kv·d elements of each cache allocation, and their bytes;
   - the number of elements of one draw, m·(h + 2·h_kv)·d + 2·P·h_kv·d.

   Use `byte_size` or an equivalent overflow check. A failure, or a failed allocation, gives status 3 with one stderr line.
5. **Per draw dr**, with `base = draw_base(seed, dr)` and bits = 8 throughout:
   - Draw one sequence, in this order (sequence indices continue from one range to the next): `q` (m·h·d elements), `k_new`, `v_new` (m·h_kv·d each), then rows 0 … P − 1 of the `cache_k` operand, then rows 0 … P − 1 of the `cache_v` operand (P·h_kv·d each, possibly zero). The operand of each cache starts m rows into its allocation.
   - Set rows P … l − 1 of each operand and the m leading and m trailing guard rows of each allocation to `0x7FC0` (`OUTPUT_FILL`). Every draw sets both whole allocations anew.
   - Emit the check value of criterion 2 over: `q`, `k_new`, `v_new`, then the whole `cache_k` allocation ((l + 2m)·h_kv·d elements, guard rows included), then the whole `cache_v` allocation.
   - Fill `out` with `0x7FC0`.
   - Call `hilclaw_sdpa_kv_cache_bf16(m, l, h, h_kv, d, q, k_new, v_new, cache_k_operand, cache_v_operand, out)`. Here `cache_x_operand` is the allocation's address plus m·h_kv·d elements.
   - Emit the 2·m·h·d bytes of `out`, then the whole `cache_k` allocation, then the whole `cache_v` allocation, all in memory order.

   After the last draw, write `end\n`. A complete report has draws · (4 + 2·m·h·d + 4·(l + 2m)·h_kv·d) + 4 bytes. Descriptor 1 points at standard error before the first call (`report_open`). Status 0 is returned only after the end mark.
6. **Header comment** of the program, in the form of `bf16_verification_rmsnorm.c`. It states:
   - the command line and its rules, with P = l − m derived;
   - that no standard input, file or environment variable is read;
   - the inputs (bits = 8, the sequence order of criterion 5, and the layouts `q[(i*h + j)*d + e]` and cache element (t, g, e) at `(t*h_kv + g)*d + e`);
   - the allocations with their m guard rows on each side, and the address passed to the kernel;
   - the fills (rows P … l − 1, guard rows, `out`);
   - the check value and its five ranges;
   - the report and its length;
   - the exit statuses.

   It points to `bf16_verification.h` for the generator and the shared statuses instead of restating them. It must not claim that the program needs `-lm`. The program compiles alone under the CI C gate command.
7. **`hilclaw/harness/bf16_verification_build.py`**:
   - Add `sdpa_kv_cache` as the last key of `PROGRAM_SOURCES`. The order becomes gemm, rmsnorm, elementwise_add, swiglu, rope, sdpa_kv_cache.
   - Update the module docstring: the summary line and the rule paragraph name ADR-0165 for kind `sdpa_kv_cache` (decision 2), and say that program reads no standard input. The paragraph on `-lm` may name an SDPA kernel that calls `expf`. The module still runs nothing.
   - `build_bf16_verification_executable` behaves as before for the other kinds, and its error message lists the six kinds.
8. **`hilclaw/harness/__init__.py`**: update the docstring sentence on the C sources of the bf16 runs so that it names six programs, adding `bf16_verification_sdpa_kv_cache.c` of ADR-0165. Keep the claim about the modules that import `numpy` true. No Python module is added.
9. **Size**: at most 300 changed lines outside tests, in at most 5 files. The expected files are the program, the build module and the package docstring. If the work would go over the cap, shorten the header comment, not the behaviour.
10. **Tests.**
    - **New file `tests/harness/test_bf16_verification_sdpa_kv_cache.py`.** Follow the fixture of `tests/harness/test_bf16_verification_rope.py`:
      - a session fixture that builds each stub with `clang_build.build((program, kernel), output, flags=..., trailing_flags=("-lm",))`;
      - it skips without a POSIX system or without `clang`, and fails on CI (`GITHUB_ACTIONS == "true"`) without `clang`;
      - every executable runs through `local_run.run`.

      Follow D12 (DRIVER §5): happy, error, branch and negative cases. **The expected values are computed in the test**, because no array module knows this kind yet:
      - the drawn sequence of draw dr: `draw_inputs("elementwise_add", (1, N), seed=..., draw=dr)[0]` with N the element count of criterion 4. It is the same generator sequence, indices 0 … N − 1 with bits = 8; say so in a short comment. Split it into the five ranges of criterion 5;
      - the expected allocations before the call: the fills and guard rows built in the test;
      - the expected check value: `zlib.crc32` over the bytes of the five ranges, packed as a host-order `uint32`.

      Use small shapes that include P = 0 (l = m), P > 0 with m = 1 (decode-like), P > 0 with m > 1, h = h_kv, h = 4·h_kv, d = 1 and m = l = 1. At least these tests:
      - **Source**: the program is ASCII and declares `sdpa_kv_cache_bf16_contract.PROTOTYPE` byte for byte. It contains no `<math.h>` and no `float`; a textual check is enough.
      - **Generator agreement (the generator half of the ADR-0165 Consequences test)**:
        - Use seeds 0, 1, 2**63 and 2**64 − 1, at least two draws, and the shapes above.
        - Each reported check value equals the expected one.
        - A stub that writes nothing reports `out` all `0x7FC0`. In each reported allocation, the guard rows and rows P … l − 1 are all `0x7FC0`, and rows 0 … P − 1 equal the expected drawn rows.
      - **Conforming cache write**: a stub that copies row i of `k_new` and `v_new` into row P + i of each cache, and `q` into `out`. Its report shows:
        - `out` equal to the drawn `q`;
        - rows P … l − 1 equal to `k_new` and `v_new`;
        - rows 0 … P − 1 unchanged;
        - every guard row `0x7FC0`.

        This also checks that P = l − m reaches the kernel's arithmetic.
      - **Guard rows are reported at their offsets**: stubs that write a marker pattern into the last leading guard row (`cache_k - h_kv*d`) and into the first trailing guard row (`cache_k + l*h_kv*d`), and the same for `cache_v`. Each shows the marker exactly there in the report and nowhere else. These writes stay inside the allocation, so the behaviour is defined.
      - **Fills are restored every draw**: a stub that casts away `const` and overwrites `q`, `k_new`, `v_new`, cache rows 0 … P − 1 and both guard regions. On the second draw it still gets the check value expected for that draw, and the second draw's report shows the fresh fills.
      - **Plain bf16 SDPA kernel**: a stub that widens by integer shift and computes the ADR-0162 decision 6 operation in `float` (scale 1/√d, causal mask t ≤ P + i, max subtraction, `expf`, normalisation, head mapping g = j / (h / h_kv)). It writes the cache rows and rounds `out` to bf16 by round-to-nearest-even on the bit pattern. Its reported `out`, passed through `widen`, is within a loose tolerance stated in the test (for example `atol` = 2**-6) of a test-local float64 evaluation over the drawn rows and the new rows. Run it at a P > 0 shape and at a P = 0 shape. This checks layout, offsets and byte order, not the tolerance.
      - **Calls and arguments**: one call per draw, and m, l, h, h_kv and d reach the kernel unchanged.
      - **Kernel output on stderr**: what a stub prints to standard output appears on stderr, not in the report.
      - **No standard input**: the report of a run fed `b"junk"` on standard input equals that of a run with the null device, with status 0.
      - **Report length**: draws · (4 + 2·m·h·d + 4·(l + 2m)·h_kv·d) + 4 bytes, ending with `end\n`.
      - **Command-line refusals**, each with status 2, one stderr line starting with `bf16_verification_sdpa_kv_cache: ` and empty stdout:
        - wrong argument counts, including the four and five arguments of the other kinds, six and eight arguments;
        - malformed arguments: sign, space, leading zero, empty, non-digit, zero dimension, zero draws, values past the range;
        - l < m;
        - h not a multiple of h_kv (for example h = 3 with h_kv = 2, and h = 1 with h_kv = 2).
      - **Size refusals**, status 3 with one stderr line and empty stdout: dimensions where l + 2m, an array size or the draw's element count does not fit in `size_t`, and dimensions that fit but cannot be allocated, as in the rope test.
      - **Abnormal kernels**: a kernel that aborts leaves the report written so far. A kernel that never returns leaves the first check value (use a short run time limit).
      - Keep builds session-scoped, one per stub, and every test within a few seconds on a CI runner.
    - **Update `tests/harness/test_bf16_verification_build.py`.**
      - Set `PROGRAM_KINDS` to `(*KINDS, "rope", "sdpa_kv_cache")` and update its comment.
      - Keep `"sdpa"` as an unknown kind.
      - Add one real-clang case for `sdpa_kv_cache`: a stub kernel that compiles and a complete report of the expected length.
      - Keep the existing real-clang cases as they are.
      - Do not add tests that target test code (D12 ⑤).
11. **No other behaviour change**:
    - Leave these files unchanged: `bf16_verification.h`; the five existing programs and their tests; `bf16_verification_arrays.py`, `bf16_verification.py`, `bf16_rope_arrays.py`, `bf16_rope_verification.py`, `sdpa_kv_cache_bf16_contract.py`; the first case's files; the CI workflow.
    - Add no dependency.
    - The local `pytest` (with coverage at or above the 80 % line and function gates) and `ruff` must be green. The new `.c` file must pass the C gate command locally where `clang` is available.
12. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0466`, whose body ends with `Task: T-0466`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green (the C gate and the clang tests run there).
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least:
      - the sequence order and the starting indices of the five drawn ranges, against ADR-0165 decision 4;
      - the allocation of l + 2m rows, the operand address passed to the kernel, and the fills of rows P … l − 1 and of the guard rows on every draw, against decision 5;
      - the five check-value ranges, against decision 7, and that the CRC function matches the header's for two ranges;
      - the report layout and length, against decision 8;
      - the cross-dimension refusals and the size checks, including l + 2m;
      - that every identifier except `main` is `static` or the declared symbol;
      - that the header and the other programs are unchanged.

## Out of Scope

- The array side (ADR-0165 slice 2): drawing in Python, the fills and expected allocations, the check value, the per-head reference, `sdpa_kv_cache` in any array module.
- The runner and judge (slice 3), the cache comparison and the verdict.
- The four calibration kernels of ADR-0165 decision 10 (slice 4), and any change to the calibration tests or the CI calibration step.
- Any change to `bf16_verification.h`, to ADR-0017's first-case program, or to the five existing bf16 programs.
- Registering `sdpa_kv_cache` with `correctness.check`, `spec.write` or the instance start (ADR-0165 Boundaries).
- The bf16 timing run, fp16, the model program's cache capacity.
- Editing ADR-0162, ADR-0163, ADR-0164 or ADR-0165, including the "less exact" sentences that ADR-0165 Consequences lists.

## Follow-ups

- Next slice (planner candidate): ADR-0165 code slice 2, the array side of the SDPA-with-KV-cache verification run.

## Result

- **Landed**: PR #279 squash-merged as d53b898e; 2 review rounds (Approve); CI green on all 6 jobs (C gate, Python 3.11 and 3.14, coverage gate, test presence, shellcheck).
- **Language**: C, because the program is linked with a C kernel into one executable and includes the shared C header (ADR-0163 decision 2 as ADR-0165 decision 2 applies it).
- **Changes outside tests**: 3 files, about 210 lines.
  - New program `hilclaw/harness/bf16_verification_sdpa_kv_cache.c`: cross-dimension rules (l >= m, h a multiple of h_kv) exit with status 2, size overflows (including l + 2m and the draw's element count) with status 3; the five ranges are drawn as one sequence per draw; each cache is its own allocation of l + 2m rows, with guard rows and rows P .. l - 1 refilled with `0x7FC0` on every draw; the check value is a static CRC-32 of the program (`check_ranges`) over the five ranges, so `bf16_verification.h` is unchanged.
  - `sdpa_kv_cache` is the last key of `PROGRAM_SOURCES`; docstrings of `bf16_verification_build` and `hilclaw.harness` updated.
- **Tests**: new `tests/harness/test_bf16_verification_sdpa_kv_cache.py` (expected values computed in the test; a small compiled driver checks the program's CRC against the header's `check_value` over two ranges and against `zlib.crc32` over five); `tests/harness/test_bf16_verification_build.py` gains `sdpa_kv_cache` in `PROGRAM_KINDS` plus one real-clang case. Local: ruff green; full pytest on Windows 31501 passed, 1747 skipped (no clang); WSL clang 14 run of the two touched test files 247 passed.
- **Review**: round 1 raised two Low nits; the helper `times` was renamed to `multiplied` (POSIX `times()` clash); the unreachable `new_count` overflow check stays because criterion 4 names it (reviewer agreed).
- **Follow-ups**: ADR-0165 code slice 2, the array side (planner candidate).
