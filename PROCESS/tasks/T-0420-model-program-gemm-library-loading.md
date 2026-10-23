---
id: T-0420
title: Add the model program of the model executor and its build step - a fixed-source C program hilclaw/model_program.c that loads each fp32 gemm kernel from a shared library of its own with dlopen and calls hilclaw_gemm through dlsym for a list of calls read from an input file, and a module hilclaw/model_build.py that builds a kernel into a shared library and the program into an executable (ADR-0153 code slice 1, second half, build and load part; for PLAN P2-13)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-10, NFR-4, OD-31, "PLAN P2-13"]
dependsOn: [T-0418]
touchesFiles: [hilclaw/model_program.c, hilclaw/model_build.py, tests/test_model_build.py, tests/test_model_program.py]
estimatedSize: {loc: 270, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `985fa3a`):
- PLAN P2-5 cannot move: each remaining part waits on an open owner HQ (HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0032). P2-10 comes after P2-5.
- PLAN P2-11 (the contract records of the five non-GEMM kinds) and P2-12 (bf16/fp16) wait on HQ-0064, HQ-0065 and HQ-0066.
- PLAN P2-13: ADR-0153 (`4498d50`) decides the model executor. Its Consequences name code slice 1: "the host side's binding checks and outcomes, and the build and loading of fp32 `gemm` kernels as shared libraries called by a model program through ADR-0008's prototype, tested with hand-written kernels". The record says slice 1 is possible before the answers to HQ-0064, HQ-0065 and HQ-0066.
- T-0419 (the binding check, `hilclaw/model_binding.py`, Draft PR #244) is BLOCKED on HQ-0067: a test of `tests/test_gemm_contract.py` that open PR #186 also edits.

**This task** is the build and load part of slice 1. It does not use the binding check, so HQ-0067 does not block it:
- a C **model program** of fixed source (ADR-0153 decisions 1 (ii), 2, 3 "Loading" and "The call");
- the Python **build step** that turns one kernel into a shared library of its own, and the program into an executable.

The program takes a plain list of GEMM calls (kernel index, m, k, n, the two input matrices) from an input file and reports each output. The host side's start, input writing, report reading and the outcomes `build failed` and `run failed` (ADR-0153 decision 5) are the next task (Follow-ups). Joining the host side to the binding check of T-0419 comes after HQ-0067 is answered. Both interfaces take a kernel as its source files and its build flags, so they can be joined without a change here.

HQ-0067 says that "the second half (slice 1 second half: build, dlopen, C model program)" waits on it. The planner reads that as a dependency of the joining, not of this code: this task neither reads nor names `hilclaw/model_binding.py`, and its input is not a `BindingCheck`.

**D18 reading.** This is work of a PLAN checklist item (P2-13, code of ADR-0153). The D18 hold rule does not apply (DRIVER §6).

**Not crossed.**
- No dtype other than fp32. No cast, accumulation, oracle, tolerance or input distribution is chosen (HQ-0065, HQ-0066). The program compares nothing.
- No value of H, d_h, the KV-head count or any Llama 3.2 1B dimension is used (HQ-0064).
- No contract is added. No call site or kind other than fp32 `gemm` is handled (P2-11).
- The isolation of the model program's build and process stays open (ADR-0153 Boundaries; OD-14). This task places no directory and starts no container. The tests build and run on the CI runner, as the harness tests do.
- The build flags of ADR-0116 are not changed (HQ-0033). The only flags this code adds are what a shared library needs (ADR-0153 decision 3 "Loading").
- No exposure (CLI, registry or MCP tool) is added (ADR-0153 decision 1).
- No data-plane member, file, kind or version changes. No new external dependency: the standard library, `hilclaw.clang_build`, `hilclaw.local_run` (tests), `numpy` (tests), clang and the C library with `<dlfcn.h>` (ADR-0153 decision 2).
- No `claude` process is started (D16).

**No open PR overlaps.**
- PR #244 touches `hilclaw/model_binding.py` and `tests/test_model_binding.py`.
- PR #186 touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.
- This task must not edit any of them, and must not edit `hilclaw/gemm_contract.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming, size cap, test rules).
- `CLAUDE.md`: "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "브랜치·merge 절차" (code mode).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Decision §1 (lines 28-33), §2 (lines 35-38), §3 (lines 40-46), §5 (lines 58-62), §6 (lines 64-68), Consequences "Code slices" and "Runtime acceptance items" (lines 88 and 91), Boundaries (lines 101-115).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: Decision §4 (the prototype), §6 (guarantees and obligations) and §7 (what the kernel source provides) (lines 46-100).
- `hilclaw/harness/verification_program.c`: the header comment and the declarations (lines 1-80). This is the pattern for the header, the exit statuses, the NaN fill of `c` and the redirection of descriptor 1.
- `hilclaw/harness/verification_build.py` (whole file, 93 lines). This is the pattern for the build module: a fixed program source next to the module, arguments handed to `clang_build.build` unchanged, and the `parameter` attribute.
- `hilclaw/clang_build.py`: the module docstring (lines 1-23), `BuildResult` (lines 43-60) and the docstring of `build` (from line 196).
- `.github/workflows/ci.yml` lines 73-85: the C gate compiles every tracked `*.c` file with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.
- `tests/harness/test_verification.py` lines 807-833: the fixture pattern for clang tests (skip on non-POSIX; when clang is missing, skip locally and fail on CI).
- `tests/test_clang_build.py` lines 2575-2589: an existing shared-library build test.
- `tests/test_gemm_contract.py` lines 386-396: the text `gemm_contract` must not appear in any new `hilclaw/*.py` file, docstrings included.

## Acceptance Criteria

The names below are this task's. The executor may rename them only if the review asks, and records any rename in Result.

1. **The model program `hilclaw/model_program.c`** (C; the language-choice line goes in Result and the commit body).
   - A header comment, as `verification_program.c` has, that names ADR-0153 and ADR-0008. It states the command line, the input file, the report and the exit statuses below, and what the program does not do: it compares nothing, holds no reference or tolerance, reads no clock, no environment variable and no standard input, and is not yet a forward pass (ADR-0153 slice 2).
   - It defines `_POSIX_C_SOURCE 200809L` and uses the C library and POSIX.1-2008 only, `<dlfcn.h>` included.
   - It compiles without a diagnostic under the CI C gate command (`-std=c99 -Wall -Wextra -Wpedantic -Werror`). The `void *` returned by `dlsym` is turned into a function pointer by a method `-Wpedantic` accepts (for example `memcpy` into the pointer), not by a cast.
   - It declares `hilclaw_gemm`'s prototype only as the type of a function pointer and defines no `hilclaw_gemm` of its own.
2. **Command line.** `<program> <input file> <library> [<library> ...]`, with at least one library.
   - Each library is opened with `dlopen(path, RTLD_NOW | RTLD_LOCAL)`, and its `hilclaw_gemm` is found with `dlsym`, before the input file is read.
   - Library *i* (0-based, in command-line order) is the kernel of index *i*.
3. **Input file**, binary, every integer an unsigned 64-bit integer and every element a `float`, all in host byte order:
   - the number of calls N ≥ 1;
   - then for each call, in order: the kernel index (< number of libraries), `m`, `k`, `n` (each ≥ 1), the `m*k` elements of `a`, then the `k*n` elements of `b`, both row-major (ADR-0008 decision 2).
   - The file ends exactly after the last call. A short file, trailing bytes, an index out of range, a zero dimension, or a size that cannot be held is an input error.
4. **Execution and report.**
   - The calls run in file order, one at a time. Each call gets its own distinct `a`, `b` and `c`, aligned for `float` (ADR-0008 decision 6). Every element of `c` is set to the bit pattern `0x7FC00000` before the call.
   - After each call returns, the `m*n` elements of `c` are written to the report, on the standard output the process was started with. After the last call comes the end mark `end\n`. A complete report is Σ 4·m·n + 4 bytes.
   - Descriptor 1 is pointed at standard error before the first call, so what a kernel prints is not part of the report (as in `verification_program.c`).
   - Whether to read the whole file first or call by call is the executor's choice, recorded in the header comment. Either way, an input error found after some calls have run gives no end mark.
5. **Exit statuses**, each other than 0 with one line on standard error and no end mark:
   - 0: the end mark was written;
   - 2: the command line;
   - 3: memory (an array that cannot be held or allocated);
   - 4: a descriptor or a write of the report;
   - 5: the input file (open, read, form; item 3);
   - 6: a library that cannot be loaded, or that has no `hilclaw_gemm` (the line names the library's index, and `dlerror()` text may follow).
   - The executor may renumber these, recorded in Result.
6. **The build module `hilclaw/model_build.py`** (Python). Its boilerplate docstring names ADR-0153 and lists what it does not do: no binding check, no directory placed, nothing run, no input file written, no flag chosen beyond item 7's. The docstring must not contain the text `gemm_contract`.
   - `PROGRAM_SOURCE`: the path of `model_program.c` next to the module.
   - `LIBRARY_FLAGS`: the tuple `("-shared", "-fPIC")`.
7. **`build_kernel_library(kernel_sources, output, *, timeout_s, flags=(), trailing_flags=(), compiler=None, cwd=None, env=None)`**
   - It makes one call of `hilclaw.clang_build.build` with the kernel's sources and `flags` = the caller's `flags` followed by `LIBRARY_FLAGS`. It returns the `BuildResult` unchanged.
   - `kernel_sources` is handled as in `verification_build.build_verification_executable`: one path or a non-empty iterable. No source raises `ValueError`. A non-path, non-iterable value raises `TypeError` with `parameter` `"kernel_sources"`. What `clang_build.build` raises is passed on unchanged.
   - `flags` must be a tuple or list of `str`. Anything else raises `TypeError` with `parameter` `"flags"`, before anything is started. Reason: the flags are concatenated here, which `clang_build` cannot check for the caller.
8. **`build_model_program(output, *, timeout_s, flags=(), trailing_flags=(), compiler=None, cwd=None, env=None)`**
   - It makes one call of `clang_build.build` with `PROGRAM_SOURCE` as the only source and every argument handed over unchanged. It returns the `BuildResult`.
   - It adds no flag. Whether a C library needs `-ldl` is the caller's `trailing_flags`.
9. **Tests `tests/test_model_build.py`** (the build module):
   - These run on every platform with `clang_build.build` replaced by a recorder: the exact arguments handed over for both functions (flag order, `LIBRARY_FLAGS` last, the program source only), the result passed through, and every `TypeError`/`ValueError` path with its `parameter`, including a `str` given as `flags`, a flag that is not `str`, an empty source iterable, a non-iterable source, and an error raised while iterating the sources.
   - `PROGRAM_SOURCE` exists. The module text holds no `gemm_contract`.
   - With real clang, POSIX only (skip elsewhere; when clang is missing, skip locally and fail on CI, per the fixture pattern): a hand-written conforming kernel builds into a shared library; a kernel with a syntax error gives `ok` false with the compiler's text in `log`; and the program builds with the caller's flags.
10. **Tests `tests/test_model_program.py`** (the program; POSIX and clang as in item 9). Each test builds the program with `build_model_program` and kernels with `build_kernel_library`, writes an input file in a `tmp_path`, runs the program with `hilclaw.local_run.run`, and checks the exit status and the report bytes. The expected outputs are computed in the test with `numpy` from small inputs whose products are exact in `float` (for example small integers), so no tolerance is involved. The tests cover:
    - **happy**: one kernel and one call. Two kernels with *different* results for the same inputs (for example the plain product, and the plain product plus 1 in every element), so that a call of index 0 and a call of index 1 in one file give each kernel's own output. This also proves that two libraries of the same symbol are kept apart (ADR-0153 decision 3 "Loading"). Several calls of different shapes in one file, in order.
    - **branch**: a kernel that prints to standard output does not change the report; a kernel that leaves `c` unwritten shows the NaN fill in the report; a library index used twice in one file.
    - **error / negative**: each exit status of item 5. This includes: no library argument; a missing input file; a short file; trailing bytes; an index out of range; a zero dimension; N = 0; a library path that does not exist; and a shared library without `hilclaw_gemm`. Each comes with no end mark and one line on standard error.
11. CLAUDE.md test rules hold: package line and function coverage ≥ 80%, ruff clean, a test file for the new Python module, and the C gate command passes on `hilclaw/model_program.c`. Local `pytest` and `ruff` pass. If the local machine has no POSIX clang (native Windows), the clang tests skip locally and must pass on CI. CI must be green before the self squash-merge. DRIVER §5 naming applies: branch `claude/T-0420-<slug>`, PR title with `T-0420`, and `Task: T-0420` as the last line of the PR body.

## Out of Scope

- The host side's run of the program: making a build directory outside both checkouts, writing the input file, starting the program, reading and parsing the report, the time limit, and the outcomes `build failed` / `run failed` (next task, Follow-ups).
- The binding check, `hilclaw/model_binding.py`, joining with `BindingCheck.calls`, and anything of HQ-0067 or PR #244.
- Weights, the embedding lookup, buffers kept across calls, the KV cache, passes, the generation loop, token selection, and the kinds other than fp32 `gemm` (ADR-0153 slice 2; P2-11).
- The container of ADR-0144 and any change to its image (OD-14; HQ-0059). Any build flag of ADR-0116.
- Edits to `ARCHITECTURE/`, `hilclaw/gemm_contract.py`, `tests/test_gemm_contract.py` and the files of PR #186.

## Follow-ups

- Next task (candidate T-0421, the host-side run of slice 1): a Python module (for example `hilclaw/model_run.py`) that:
  - makes its build directory outside both checkouts (the `hilclaw.checkout_boundary` test, as `hilclaw/scratch.py` does) and removes it;
  - builds each kernel with `build_kernel_library` and the program with `build_model_program`;
  - writes the input file of item 3 from `numpy` float32 arrays;
  - runs the program with `hilclaw.local_run.run` under a time limit;
  - reads the report into one array per call;
  - returns the named outcomes `build_failed` (kernel index, compiler output) and `run_failed` (timeout, exit status, incomplete report) of ADR-0153 decision 5.
  - Its kernel argument takes objects with `sources` and `flags`, so a later task can hand it the `calls` of T-0419's `BindingCheck` once HQ-0067 is answered.
- Runtime acceptance item (lxvii) of ADR-0153 is to be asked "once code slice 1 has landed". It is not asked at the end of this task, because slice 1 is complete only when the host side and the binding check have landed too.

## Result
