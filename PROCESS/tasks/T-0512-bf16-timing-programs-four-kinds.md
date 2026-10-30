---
id: T-0512
title: Land ADR-0181 code slice 1 — bf16 timing programs of gemm, rmsnorm, elementwise_add and swiglu with their shared header, and the Python side that builds them, forms their command lines and judges their reports through hilclaw.harness.timing
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-2, NFR-3, OD-13, OD-16, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - hilclaw/harness/          # new: shared bf16 timing header, four bf16 timing programs, Python build and run modules (names are this slice's)
  - tests/harness/            # new test files for the new Python modules and the programs
estimatedSize: {loc: 540, files: 7}   # header ~200, four programs ~60-80 each, Python ~100-120; tests excluded from the cap
hq: []
---
## Why

**State.** The bf16 timing run is recorded in ADR-0181 (T-0505, `main` `9e806a46`). The owner ordered the result format v2 to land before any bf16 timing slice (HQ-0078). That v2 record is ADR-0183, and its three code slices are on `main`: T-0509 `bbaf1160`, T-0510 `0c73026c` and T-0511 `a9b9d81e`. ADR-0183 decision 9 item 4 says that ADR-0181 decision 8 items 1 to 4 come next, in their order. This task is **ADR-0181 decision 8 item 1**: "The timing programs of the four ADR-0163 kinds (`gemm`, `rmsnorm`, `elementwise_add`, `swiglu`) and their shared header, with the Python side that forms their command lines and judges their reports through `hilclaw.harness.timing` unchanged; compiled and run with a stub kernel in the C gate. No tool path changes."

**Why now (PLAN checklist, D24 ⑤).** The D24 freeze was released on 2026-10-30 (DRIVER §6 D24 ④). Under D24 ⑤, P2-11 to P2-14 first get a real run with the minimal operation set: the six instance kinds of ADR-0152 decision 2, GEMM first (#5 B-4). Today the instance start admits only fp32 `gemm`, because `contract_table.start_covers` asks for entries that are both `checked` and `timed`, and no bf16 entry is `timed` (ADR-0177 decision 2). ADR-0181 slices 1 to 4 end by setting those flags. After that, an instance of each bf16 kind can be started for a real run (ADR-0181 Consequences). P2-11 and P2-14 are checklist items, so D18 does not apply. This task is planned in one batch with T-0513 and T-0514 (D20 ④).

**RuntimeAcceptance.** No item has the status `실패` as of `main` `b7e65818`. ADR-0181's runtime acceptance items are already recorded as RA-0052 to RA-0054. This slice adds none.

**D16.** Tests build with the local `clang`, where present, and run with stub kernels. They do not use `claude`, Docker, a board or real weights.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5. These cover the branch name `claude/T-0512-<slug>`, the `Task: T-0512` trailer in commits and as the last line of the PR body, the size cap, D12 and D21. Also read §8 (D22).
- `CLAUDE.md`: the A-13 code mode, the BLOCKED reasons, the test rules, the language policy and comment minimisation.
- `ARCHITECTURE/decisions/ADR-0181-od13-bf16-timing-run.md`, the whole record (142 lines). Read in particular decision 2 (lines 30-38), decision 3 (40-44), decision 6 (58-77, for context only, since the limits are slice 4's), decision 8 (87-95) and the A-13 reading (101-107).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`, decisions 2 to 9 (lines 28-110). They set the clock, the loop, the untimed call, the report form and the spelling of the parameters.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`, decisions 2 to 4 (lines 44-89). They set the program per kind, the command line and the drawn inputs, with each kind's input value set and bits per operand.
- `ARCHITECTURE/decisions/ADR-0107-od16-verification-and-timing-build-relation.md`, decisions 2 and 3 (lines 32-59).
- Code:
  - `hilclaw/harness/timing_driver.c` (250 lines): the fp32 program whose loop, clock and report are kept. It must not change.
  - `hilclaw/harness/bf16_verification.h` (185 lines): the generator, the argument rules and the statuses.
  - `hilclaw/harness/bf16_verification_{gemm,rmsnorm,elementwise_add,swiglu}.c`: the prototypes, the draws per kind and the `rmsnorm` `eps` constant.
  - `hilclaw/harness/timing.py`, mainly `driver_arguments`, `parse_report`, `judge_report`, `run_timing` and `TimingResult`. It must not change.
  - `hilclaw/harness/timing_build.py` and `hilclaw/harness/bf16_verification_build.py`: the build helpers to mirror.
  - `hilclaw/harness/bf16_verification.py`: `program_arguments(kind, dims, ...)`, the per-kind dimension rules.
  - `hilclaw/harness/measurement.py`: `N_MIN`, `CV_MAX` and `N_MAX_DEFAULT`.
  - `hilclaw/local_run.py`: `run`, `RunResult` and `max_rss`.
  - `hilclaw/harness/memory_ceiling.py`: `figure`.
- Tests to mirror: `tests/harness/test_timing_driver.py` (stub kernels, strict flags, exit statuses), `tests/harness/test_timing.py`, `tests/harness/test_bf16_verification_programs.py` and `tests/harness/test_bf16_verification_build.py`.
- CI: the `clang build` step of `.github/workflows/ci.yml` compiles every tracked `*.c` with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.

## Acceptance Criteria

1. **Four bf16 timing programs and one shared header** under `hilclaw/harness/` (ADR-0181 decision 2). The file names and the way the shared parts are factored are this slice's choice. There is one program per kind (`gemm`, `rmsnorm`, `elementwise_add`, `swiglu`), and each holds exactly one call site of its kernel: `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16` or `hilclaw_swiglu_bf16`. Each prototype is byte for byte the one the kind's verification program declares. `timing_driver.c` and `bf16_verification*.c` / `.h` do not change, except that the shared header may include `bf16_verification.h` for its generator. In that case, the Result notes that slice 4 must copy both headers beside the program (ADR-0181 decision 3).
2. **Kept from ADR-0009 for every kind:**
   - the `CLOCK_MONOTONIC` readings around exactly one kernel call per repeat;
   - exactly one untimed call before the first timed repeat;
   - the loop and the stopping rule run by the program, with `n_min`, `n_max`, `cv_max` and the sample form taken from the command line;
   - descriptor 1 pointed at standard error before the first call;
   - the report form, byte for byte that of `timing_driver.c`: `resolution_ns <i>`, `interval_ns <i>` lines, then `stop converged` or `stop not_converged`;
   - the exit statuses of `timing_driver.c` (2 command line, 3 memory, 4 system, 5 zero interval).
   No floating-point arithmetic is done on the operands. The programs use only the C library and POSIX.1-2008, with no `-lm`.
3. **Command line** (decision 2): the kind's dimensions in `task_contract` order (`m k n` for `gemm`; `m n` for the other three), then `n_min n_max cv_max sample_form seed`. The spelling rules are ADR-0009 decision 9's. A wrong count, spelling or bound is refused with status 2. The `rmsnorm` `eps` is the contract's constant, compiled in as in its verification program.
4. **Operands** (decision 2). Each input array is allocated once with one `malloc` and filled once, before the untimed call, by the generator of `bf16_verification.h`. The fill uses `seed` = the timing seed, draw index 0, and each operand's value set and bits exactly as the kind's verification program draws them (ADR-0163 decision 4). Output arrays are not initialised. Nothing is reset between repeats.
5. **Python side.** New modules under `hilclaw/harness/`; their names are this slice's, for example `bf16_timing_build.py` and `bf16_timing.py`. Each new module has its test file (P0.5-2).
   - (a) A **build function**, mirroring `bf16_verification_build`. It maps each of the four kinds to its program source through a `PROGRAM_SOURCES`-like mapping. It builds that program and the kernel sources into one executable with one `clang_build.build` call, adds no flag of its own, and refuses an unknown kind before anything is started.
   - (b) An **argument function** `(kind, dims, *, n_max, sample_form, seed)`. It returns the program's arguments as `str`, with `n_min` and `cv_max` from `measurement` exactly as `timing.driver_arguments` does. It refuses a kind outside the four, dims of the wrong length or type or below 1, and the `n_max`, `sample_form` and `seed` that `driver_arguments` refuses. Refusals use `timing.TimingArgumentError` or `TypeError` / `ValueError` in the style of the module.
   - (c) A **run function**. It starts one process of a built executable with `local_run.run` and returns a `timing.TimingResult`. It judges the report with `timing.judge_report` / `parse_report` and their replay. It returns the same `Broken` values for timeout, exit status, report form, zero interval and replay as `timing.run_timing`, and takes the memory figure from `memory_ceiling.figure` only for a completed run. **`hilclaw/harness/timing.py` is not changed.**
6. **No tool path changes.** `contract_table` (no `timed` flag), `run_tool`, `run_admission`, `run_parameters`, `run_operation`, `standin_run`, `standin_settings`, `mock_run` and everything outside `hilclaw/harness/` stay unchanged.
7. **C gate.** Every new `.c` compiles under the CI command above, which also checks that the header compiles under `-std=c99 -Wpedantic -Werror`.
8. **Tests.** They follow D12: happy, error, branch and negative cases, every public function of the new modules, and coverage of at least 80 % for lines and for functions. Tests that need `clang` or POSIX are skipped where it is absent, as the existing harness tests are.
   - Each of the four programs is built with a stub kernel of its kind under the strict flags and run. The tests check that:
     - the report parses and judges `converged` or `not_converged` through the run function;
     - the kernel is called exactly `1 + number of interval lines` times;
     - the operands the stub receives are exactly the bf16 verification generator's for the timing seed and draw 0. For example, the stub compares a check value of its inputs with one computed by `bf16_verification_arrays`, or aborts on a mismatch;
     - inputs are unchanged across repeats;
     - kernel output to stdout does not reach the report.
   - Negative cases:
     - each program refuses a wrong argument count and a bad spelling (leading zero, sign, 0 dimension, `n_max < n_min`, bad `cv_max`, bad sample form) with status 2;
     - the Python argument function refuses an unknown kind, `rope`, `sdpa_kv_cache`, wrong dims and a bool;
     - the build function refuses an unknown kind;
     - the run function returns `EXIT_STATUS`, `TIMEOUT`, `REPORT_FORM` and `ZERO_INTERVAL` for a stub that aborts, hangs, prints a malformed report (via a fake executable) or yields a zero interval, as `test_timing.py` does for fp32.
9. **Existing tests.** No existing assertion changes, except a list assertion that pins `hilclaw.harness` module names or imports, if one exists (D21). List any such edit in the PR body.
10. **No record edits.** No file under `ARCHITECTURE/` changes. The Result names sentences that become less exact beyond ADR-0181's Consequences list.
11. **Result** records:
    - the language (C for the programs, Python for the helpers) and the reason;
    - the new file names and the factoring of the header;
    - whether the header includes `bf16_verification.h`;
    - the exact public names of the Python functions, which T-0513 and T-0514 build on;
    - the edited list assertions;
    - runtime acceptance items (none expected);
    - the next candidate, T-0513.

## Out of Scope

- The `rope` and `sdpa_kv_cache` timing programs (T-0513, slice 2).
- Run-tool admission and per-kind timing parameters (T-0514, slice 3).
- The `cpu_standin` operation for bf16, `standin_settings` limits, header copies into the container and the `timed` flags (slice 4, a later task).
- Any `n_min`, `cv_max`, tolerance, seed-source or other owner-only value. OpenMP (HQ-0034). fp16.
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result
