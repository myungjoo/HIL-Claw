---
id: T-0577
title: PLAN P3-16 (5b) — ADR-0207 slice 5, second half: the `cuda_gpu` operations of `correctness.check`, `sim.run` and `board.run` build and run only in `--gpus all` containers of the named image (probe container first, `nvcc` build, process, the waiter for the timing process), checked on the real GPU
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "HQ-0095", "HQ-0096", "HQ-0097", FR-9, FR-10, FR-19, OD-33, OD-14, NFR-4]
dependsOn: [T-0576]
touchesFiles:
  - hilclaw/cuda_check.py
  - hilclaw/cuda_run.py
  - hilclaw/standin_check.py
  - hilclaw/standin_copies.py
  - tests/test_cuda_check.py
  - tests/test_cuda_run.py
  - tests/test_standin_check.py
  - tests/test_standin_copies.py
estimatedSize: {loc: 420, files: 4}
hq: []
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that a CUDA `gemm` kernel goes through build, correctness, measurement and record with the real `nvcc` and GPU (D29). **ADR-0207** (T-0572, PR #385) decides how. This task is the **second half of slice 5** of its decision 9.

- T-0575 (slice 4) built the `cuda_gpu` operations on a **test-only host executor**. Its module docstrings say "slice 5 moves the build and the process into containers".
- **T-0576** (the first half) adds what that move uses:
  - `--gpus all` on the container start;
  - the `cuda_gpu` image variable;
  - the device check in a probe container;
  - the toolkit and the `cuda:13.1.2` image on this machine.
- After this task, the runtime builds and runs `cuda_gpu` kernels only in containers (NFR-4; ADR-0207 decision 7).

It depends on **T-0576** and cannot start before it is `DONE`. If T-0576 returns BLOCKED, this task waits.

**Slice 6** (default-table entry, run record, given-code bundle) waits on **HQ-0104** and is not planned.

**Order check (D27 ①)** at planning time (main `00253282`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**Brake (D31 ②).** This is the PLAN item's own work, which is exempt. Do not harden existing paths beyond what this slice needs.

**Open HQs (D27 ⑦).** Do not ask again or anticipate HQ-0100, HQ-0102, HQ-0103 or **HQ-0104**. Do not ask again HQ-0088 ① (c), HQ-0090 or #5 B-7. **Which files of an attempt's `output/` a CUDA kernel is (a `.cu` name) is HQ-0104's question.** The `sources` selection of T-0575 stays the caller's (criterion 2).

If an owner-only part appears, write it in `## Result` as an HQ in the DRIVER §8 structure: Korean; the issue; options (a)/(b)… with the executor's recommendation; what it blocks and what it does not. Owner-only parts here are a data-plane frame change under D23, an install that is neither pre-allowed nor approved, and running attempt code outside a container as runtime behaviour. Land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0577-<slug>`, the `Task: T-0577` trailer and the PR body's last line, size D30, tests D12, list assertions D21, **storage D29**: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0577/`).
- `PROCESS/DRIVER.md` §6 lines **D29** (toolchain: "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; FR-19 ⑤ test skipping), **D27 ⑥ ⑦**, **D31**, §8 and §9.
- `PROCESS/PLAN.md`: P3-16 (line ~80).
- `PROCESS/STATE.json` `humanQuestions`: HQ-0095 (② (a)), HQ-0096 (② (a)), HQ-0097 ((a) (i)), HQ-0090 and **HQ-0104**.
- `ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`: **all**, especially decisions 3 (`waiter_flags`, `memory_limit_bytes` None), 6, 7, 8 and 9.
- `ARCHITECTURE/decisions/ADR-0144-od14-first-case-build-run-container.md` decisions 1 to 6. `ADR-0145-od14-first-case-container-measurement.md` (the waiter). `ADR-0168-od18-standin-container-situations.md` (rows C1 to C19). `ADR-0193-od32-generalization-design.md` decision 4 (memory bound).
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` decision 7, `ADR-0060-od18-correctness-check-build-answers-and-settings.md`, `ADR-0110-od18-check-executions-hard-floor.md` decisions 2 and 3.
- `PROCESS/tasks/T-0575-cuda-gpu-backend-operations.md` and `PROCESS/tasks/T-0576-cuda-gpu-container-probe-and-image.md` (`## Result` of each: the image tag, the probe function, the image variable, the machine facts).
- Code:
  - `hilclaw/cuda_check.py` and `hilclaw/cuda_run.py` (today's host executor and its steps)
  - `hilclaw/standin_check.py` (`container_image`, `make_build_dir`, `run_container`, `run_build`, `report_build`, `settled`, `remove_build_dir`)
  - `hilclaw/standin_run.py` (the timing build, the waiter build and the timing process under the waiter)
  - `hilclaw/standin_copies.py` (`place_copies`, `place_harness_copy`)
  - `hilclaw/standin_answer.py`, `hilclaw/standin_waiter_line.py`
  - `hilclaw/standin_container.py` (with T-0576's `gpus` option), `hilclaw/cuda_image.py` (or the name T-0576 chose) and `hilclaw/cuda_adapter.py` (T-0576's probe-container function)
  - `hilclaw/harness/cuda_programs.py`, `hilclaw/harness/timing_waiter.c`
- Tests: `tests/test_cuda_check.py`, `tests/test_cuda_run.py`, `tests/test_standin_check.py`, `tests/test_standin_run.py` (the stub client and how container commands are asserted).

## Acceptance Criteria

1. **Machine check first** (D29). Before writing, read and record in `Result`:
   - `docker info` (the `nvidia` runtime present);
   - `docker image ls cuda`;
   - `nvcc --version` and `gcc --version` inside `cuda:13.1.2`;
   - `nvidia-smi` on the host.

   If the toolkit or the image T-0576 recorded is gone, do not reinstall or pull anything outside T-0576's record. Return BLOCKED with the fact.
2. **The kernel's files stay the caller's.** `operation_for(target, *, sources)` keeps its required keyword `sources`, given by name with no default. The selected files are copied into the call's build directory before the build container starts, as `cpu_standin` places its copies, and are handed to `nvcc` there.
   - Add no `.cu` reading to `kernel_source` or `attempt_kernel` (HQ-0104).
   - If `standin_copies` gains a function for placing given files, it must not change `place_copies` for `cpu_standin`.
3. **`correctness.check` in containers** (`hilclaw/cuda_check.py`). In order:
   1. Check its arguments, as today.
   2. Read the image from T-0576's variable. No image named is the existing C1 answer (`compiler_unavailable`, as `standin_answer.read_image_value` gives it), and a refused value is the C2 answer.
   3. Make the build directory.
   4. Run **the device check in the probe container** of that image with `--gpus all` (T-0576). Its `device_unavailable` is the answer, before any build and any process of the attempt (decision 6).
   5. Place the copies.
   6. Build T-0574's verification program with the selected files by `nvcc` at the target's flags, in a build container with `--gpus all` (decision 7, because of `-arch=native`). The compiler's log goes to the keeper, and the build answers are ADR-0168's (`report_build`/`settled`).
   7. Run the verification process in a process container with `--gpus all`, no memory bound (the target's `memory_limit_bytes` is `None`) and the target-capped limit.
   8. Return the report for the existing judging.

   The build directory is removed on every path, as `standin_check` does. A non-zero status of the attempt's process, 125 to 127 included, is broken `exit_status` (ADR-0168 C8; ADR-0110 decision 3), never a tool failure. A device lost after the probe went on is a run failure (decision 6).
4. **`sim.run` and `board.run` in containers** (`hilclaw/cuda_run.py`). The same order with T-0574's timing driver, then:
   - the waiter of ADR-0145 built from `timing_waiter.c` by `nvcc` at the target's `waiter_flags` (decision 3), in its own build container;
   - the timing process under the waiter in a process container with `--gpus all`, read as `standin_run` reads it: the waiter's line, then form (A) `(report, memory_bytes)`, or `time_limit` or `exit_status`.

   `memory_bytes` is the waiter's figure of the host process. No GPU memory figure is given (HQ-0090). One operation serves both tools (HQ-0095 ② (a)), with no member added. The timing boundary is ADR-0194 decision 4 as T-0574's driver implements it.
5. **No host executor in the operations.** After this task, `operation_for` of both modules builds and runs only in containers. The host-executor path of T-0575 is removed from the operations, and the module docstrings say "in containers" where they said "test-only host executor".

   **No default change**: `check_definition.default_table` is not changed (slice 6), and a call about `cuda_gpu` through the default registry stays `no_backend`. `cpu_standin`, `virtual_npu` and the mock behave and answer exactly as before, and every existing `cpu_standin` container command stays byte-for-byte the same.
6. **The real GPU** (FR-19 ⑤). Build a backend table in a test with `Backend("cuda_gpu", {...})` holding the three operations with a fixture selection, and the image variable set to `cuda:13.1.2`. Call through `check_operation.ask` and `run_operation.ask` (as T-0575 did) with a test-placed fp32 `gemm` kernel at a small shape:
   - `gemm.cu` gives `pass` and a timed result for `sim.run` and `board.run` accepted by `timing.judge_report`, with `memory_bytes` > 0;
   - `gemm_wrong.cu` gives `fail`;
   - `broken.cu` gives broken `build_exit_status` with the log kept;
   - `gemm_exit.cu` gives broken `exit_status`.

   These tests skip with a stated reason where Docker, the image, the toolkit or a usable GPU is absent, so CI skips them. Test the probe's `device_unavailable` and the image-absent answers everywhere with the stub client.
7. **Tests** (D12): happy, error, branch and negative cases for every public function of the touched modules, with the stub client. Cover:
   - each container step's answers (the image, the probe, the build, the process, the waiter's build, the timing process);
   - the order: no build or process container after `device_unavailable`;
   - that every `cuda_gpu` container command holds `--gpus all` and the ADR-0144 decision 6 options;
   - build-directory removal on every path.

   T-0575's tests of the host executor change to the container form. That is this slice's design (ADR-0207 decision 9), so list each changed test in the PR body. Other existing tests stay unchanged except list assertions under D21. Foreseen: the public-name pins of `cuda_check`, `cuda_run` and `standin_copies`.

   Verification: the full suite passes in WSL2 with the CUDA `bin` on `PATH`; `hilclaw/` line and function coverage is ≥ 80%; `ruff check` and `ruff format --check` pass.
8. **Process**:
   - Follow the dev-item-address steps. Open a Draft PR and run a context-isolated review to Approve (≤ 14 rounds, D28). The review prompt names criterion 2 (HQ-0104 not decided) and criterion 5 (only containers; no default change).
   - Once CI is green, self squash-merge with the PR body's last line `Task: T-0577`.
   - No ADR is written, because ADR-0207 decides this slice. If a choice outside it turns out to be a design OD, return BLOCKED under DRIVER §3 rather than inventing it.
   - In `Result` record:
     - the language and reason;
     - the machine outputs;
     - the real-GPU results with tool versions and the image tag;
     - any HQ;
     - any runtime acceptance item (D22). RA-0086 already holds ADR-0207's container items; add one only for a new fact.
   - Remove the task directory with `rm -r` and any work image by its tag (D29). Keep `cuda:13.1.2`.

## Out of Scope

- Installing anything or pulling any image (T-0576 did; nothing more is pre-decided here).
- Slice 6 and HQ-0104: `.cu` attempt names in `kernel_source`, the CUDA given-code bundle in `given_eval`, `instance_start` true, the default-table entry, `run.commit` of a CUDA run, the demonstration through the registry's tool functions.
- bf16 at CUDA, `model_run`, GPU memory figures (HQ-0090), the coder's CUDA path (HQ-0088 ① (c)), retries (OD-17).
- The flaky real-GPU timing test T-0575 observed (`test_real_gpu_interval_holds_the_completion_of_the_kernel`), unless it blocks this task's verification.
- Starting `claude` in any form (D16); a test run (D25).

## Follow-ups

## Result

DONE — PR #390 (squash-merge commit: see the PR). Review rounds: see the PR (round 1 Request changes: restored T-0575's unchanged `select_sources` tests, listed two missed changed tests, fixed a `cuda_adapter` docstring line). No HQ. No new RuntimeAcceptance item.

**Machine check (criterion 1; WSL2 Ubuntu 22.04, kernel 6.18.58.1-microsoft-standard-WSL2, 2026-11-15 ~11:19Z)**
- `docker info`: Docker Engine 29.1.3; runtimes `io.containerd.runc.v2 nvidia runc`, default `runc` (the `nvidia` runtime present). `nvidia-ctk` 1.19.0.
- `docker image ls cuda`: `cuda:13.1.2`, id `1efffc671e20` (`sha256:1efffc671e20f111753d134230188163113cbf3e263f85df66d55f31b99afc1f`), RepoDigest `nvidia/cuda@sha256:d8332c008e2ef270e82d286e5245e771f839645683075bba21ad9e4fa59dbcbb`, 6.95 GB — T-0576's record, unchanged.
- Inside `cuda:13.1.2`: `nvcc` "Cuda compilation tools, release 13.1, V13.1.115" (Build cuda_13.1.r13.1/compiler.37061995_0); `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.
- Host `nvidia-smi`: NVIDIA GeForce RTX 4070, 12282 MiB, driver 615.78.02 / KMD 617.14, CUDA UMD 13.4.
- Nothing installed or pulled by this task.

**Change**
- `hilclaw/cuda_check.py`: the operation now runs image (`HILCLAW_CUDA_IMAGE`; none named = `standin_answer.read_image_value`'s C1 `compiler_unavailable`, `cuda_image.ImageRefusedError` = C2 `compiler_unavailable`) -> build directory -> probe container (`cuda_adapter.check_device_in_container`, `device_unavailable`) -> selection and copies -> `nvcc` build container -> process container, all with `--gpus all`, through `standin_check.carry_out` (build directory removed where every container, the probe's included, allows it). Public steps: `container_image`, `confirm_device(image, build_dir, outcomes)`, `select_sources` (unchanged), `place_sources`, `build_in_container`, `run_process`; T-0575's host `confirm_device()`, `build_executable` and `carry_out` are removed. `sources` stays a required keyword with no default; no `.cu` reading anywhere (HQ-0104).
- `hilclaw/cuda_run.py`: the same order with the timing driver, then the waiter (`standin_run.WAITER_SOURCE`) built by `nvcc` at `waiter_flags` in its own build container within what is left of the build limit, then the timing process under the waiter in a `--gpus all` process container, read by `standin_answer.read_timing_process` (form (A) `(report, memory_bytes)` with the waiter's host figure, or `time_limit`/`exit_status`). One operation for both tools; no member added.
- `hilclaw/standin_copies.py`: new `place_selected_copies(sources, harness_program, build_dir)` (caller-selected files below `kernel/` under their basenames, the harness beside them); `place_copies` unchanged.
- `hilclaw/standin_check.py`: `run_build(..., compiler=COMPILER, gpus=False)`, `run_container(..., gpus=False)`; the defaults keep every `cpu_standin` command byte-for-byte (a test asserts no `--gpus` and `clang` by default).
- `hilclaw/cuda_adapter.py`: `check_device_in_container(..., outcomes=None)` appends what the probe container returned or raised (for ADR-0168 decision 5); a non-list is `TypeError` with `parameter` `"outcomes"`. Module docstring line on `check_device` corrected.
- `check_definition.default_table` unchanged (a `cuda_gpu` call through it stays `no_backend`, tested).
- Choice of this slice, inside ADR-0207: no candidate build is read at `cuda_gpu` (T-0575's choice kept; `coder_loop` is false there), so `report_build` is not applied; the build answers are `run_build`/`settled`'s.
- Test-side note: `tests/cuda_fixtures/gemm_wrong.cu` is `#define GEMM_WRONG 1` + `#include "gemm.cu"`; a copy into the build directory does not carry the include, so the real-GPU test composes the wrong kernel into one file in its own output directory (fixtures unchanged).
- Language: Python (the modules extended and their callers). Size: about 330 non-test lines changed across 5 modules (D30 recommendation kept); 10 files including tests.

**Verification**
- Full suite in a WSL2 clone of the branch with `/usr/local/cuda/bin` on `PATH`, under `coverage run --source=hilclaw`: 42792 passed, 108 skipped (722 s). `hilclaw/` lines 19184/19249 (99.7%), functions 1816/1818. That run was before the round-1 fixes; after them the touched and neighbouring test files (`test_cuda_check`, `test_cuda_run`, `test_cuda_adapter`, `test_standin_check`, `test_standin_copies`, `test_standin_run`, `test_cuda_image`, `test_standin_container`) passed again (985, real-GPU tests included, none skipped) with `cuda_check`, `cuda_run`, `cuda_adapter`, `standin_check`, `standin_copies`, `standin_container` at 100% lines. `ruff check` and `ruff format --check` clean.
- Real GPU (FR-19 (5); RTX 4070, driver 617.14, toolkit 1.19.0, image `cuda:13.1.2` with nvcc 13.1 V13.1.115 and gcc 11.4.0; `HILCLAW_CUDA_IMAGE=cuda:13.1.2`; a backend table built in the test with `Backend("cuda_gpu", {...})`, calls through `check_operation.ask` and `run_operation.ask`):
  - `gemm.cu`: `correctness.check` `pass` at 5x33x7 and 8x8x8; `sim.run` and `board.run` each a `Reported` accepted by `timing.judge_report` (interval form, 20 samples, `resolution_ns 1`, intervals about 30 to 80 us at 5x33x7), `memory_bytes` about 110 MB (110317568 and 110391296 in one hand run: the host process's peak RSS through the waiter);
  - `gemm_wrong.cu` (composed): `fail`;
  - `broken.cu`: broken `build_exit_status`, log kept ("/build/kernel/broken.cu(1): error: expected a \")\"");
  - `gemm_exit.cu`: broken `exit_status` (check, `sim.run`, `board.run`);
  - device lost after the probe (process container started without `--gpus`): broken `exit_status`.
- Skips: the real-GPU tests skip with a stated reason without a POSIX host, `docker`, the image in the local store, or a GPU visible in a probe container (CI skips them).
- No `claude` was started (D16); no test run (D25).

**Runtime acceptance items (D22).** None new; RA-0086 already holds ADR-0207's container items.

**Storage.** Task directories (WSL `/tmp/hilclaw-driver/T-0577/` with the clone, coverage data and smoke script; Git Bash `/tmp/hilclaw-driver/T-0577/` with the PR body) removed with `rm -r` at the end. No work image was made. Kept: tool image `cuda:13.1.2`.
