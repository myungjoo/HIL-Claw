---
id: T-0575
title: PLAN P3-16 (4) — ADR-0207 slice 4, the `cuda_gpu` operations of `correctness.check`, `sim.run` and `board.run` on the host executor (device check first, `nvcc` build, run, the existing judging), held by a test-built backend table and checked on the real GPU
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "HQ-0095", "HQ-0096", "HQ-0097", FR-9, FR-10, FR-19, OD-33]
dependsOn: [T-0573, T-0574]
touchesFiles:
  - hilclaw/cuda_check.py
  - hilclaw/cuda_run.py
  - hilclaw/cuda_adapter.py
  - tests/test_cuda_check.py
  - tests/test_cuda_run.py
  - tests/test_cuda_adapter.py
  - tests/cuda_fixtures/
estimatedSize: {loc: 420, files: 3}
hq: []
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that a CUDA `gemm` kernel goes through build, correctness, measurement and record with the real `nvcc` and GPU (D29). **ADR-0207** (T-0572, PR #385) decides how. This task is **slice 4** of its decision 9: the backend's operations of `cuda_gpu` for the three HW tools on the host executor. Each operation runs the device check first, then the build, then the run, then the existing judging. A test-built table holds them.

- It depends on **T-0573** (slice 2: the `cuda_gpu` target and hw_profile) and **T-0574** (slice 3: the `cuda` contract entry and the two C programs).
- Slice 5 (the runtime GPU container) moves these builds and processes into containers.
- Slice 6 (default-table entry, run record) waits on **HQ-0104**. That HQ's own text says slices 2 to 5 are not blocked by it.

Expected size: about 420 lines in 2 new modules.

**Order check (D27 ①)** at planning time (main `b6333b4b`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**Brake (D31 ②).** This is the PLAN item's own work, which is exempt. Do not harden existing paths beyond what this slice needs.

**Open HQs (D27 ⑦).** Do not ask again or anticipate HQ-0100, HQ-0102, HQ-0103 or **HQ-0104**. Do not ask again HQ-0088 ① (c), HQ-0090 or #5 B-7. **Which files of an attempt's `output/` a CUDA kernel is (a `.cu` name) is HQ-0104's question.** This task must not decide it (criterion 2).

If an owner-only part appears, write it in `## Result` as an HQ in the DRIVER §8 structure: Korean; the issue; options (a)/(b)… with the executor's recommendation; what it blocks and what it does not. Owner-only parts here are a data-plane frame change under D23, an install that is neither pre-allowed nor approved, and running attempt code outside a container as runtime behaviour. Land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0575-<slug>`, the `Task: T-0575` trailer and the PR body's last line, size D30, tests D12, list assertions D21, **storage D29**: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0575/`).
- `PROCESS/DRIVER.md` §6 lines **D29** (toolchain: "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; NVIDIA tools from NVIDIA's official site are pre-allowed; FR-19 ⑤ test skipping), **D27 ⑥ ⑦**, **D31**, §8 and §9.
- `PROCESS/PLAN.md`: P3-16 (line ~80).
- `PROCESS/STATE.json` `humanQuestions`: HQ-0095 (② (a): both points are the same local GPU run), HQ-0096 (② (a)), HQ-0097 ((a) (i)) and **HQ-0104**.
- `ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`: **all**, especially decisions 4, 6 and 8 and slice 4.
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md` decisions 2 to 5. `ADR-0016-od18-backend-frame.md` decisions 2 to 4.
- `ARCHITECTURE/decisions/ADR-0056-od18-correctness-check-verification-executable.md` decision 7 (the order of a check operation) and `ADR-0060-od18-correctness-check-build-answers-and-settings.md` (build answers).
- `ARCHITECTURE/decisions/ADR-0047-od18-correctness-check-operation-tool-failure.md` and `ADR-0068-od18-run-tools-operation-tool-failure.md` (tool failure), `ADR-0078-od18-correctness-check-compiler-log-file.md` (the compiler's log and the keeper), and `ADR-0110-od18-check-executions-hard-floor.md` decisions 2 and 3.
- `ARCHITECTURE/decisions/ADR-0055-od23-coder-output-form.md` (admitted names and the compiled set) and `ADR-0193-od32-generalization-design.md` decision 3.
- `PROCESS/tasks/T-0573-cuda-gpu-target-entry-and-hw-profile.md` and `PROCESS/tasks/T-0574-cuda-gemm-contract-and-c-harness.md` (`## Result` of each). `PROCESS/tasks/T-0572-cuda-target-design-and-device-unavailable.md` `## Result` (machine facts).
- Code:
  - `hilclaw/standin_check.py` and `hilclaw/standin_run.py` (`operation_for(target)`, the step order, the build directory, the answers; the model to follow without containers)
  - `hilclaw/check_operation.py` (`ask`) and `hilclaw/run_operation.py` (`ask`, `CONDITIONS`)
  - `hilclaw/cuda_adapter.py` (`build`, `run`, `measure`, `check_device`)
  - `hilclaw/kernel_source.py` (`read_compiled_set`)
  - `hilclaw/backends.py`
  - `hilclaw/check_definition.py` (`default_table`, unchanged here)
  - `hilclaw/harness/verification.py` and `hilclaw/harness/timing.py`
  - the modules T-0574 added
- Tests: `tests/test_standin_check.py` and `tests/test_standin_run.py` (how an operation is called and its answers asserted), and `tests/test_check_definition.py` (test-built tables).

## Acceptance Criteria

1. **Machine check first** (D29). Read `nvcc --version` and `nvidia-smi` before writing and record them in `Result`. Nothing is installed or pulled.
2. **The kernel's files are the caller's.** Today's `kernel_source.read_compiled_set` compiles the `.c` files of `output/` and admits no `.cu` name. Whether an attempt's `output/` may hold `.cu` files is HQ-0104.
   - Each operation builder takes the selection of the kernel's source files as an argument, for example a function from the output path to source paths, given by name with no default. Add no `.cu` reading to `kernel_source` or `attempt_kernel`.
   - Tests give a selection that picks the test-placed `.cu` fixture of T-0574. Slice 6 gives the one HQ-0104's answer provides.
   - State this in each module docstring.
3. **`hilclaw/cuda_check.py`**: `operation_for(target, *, sources)` (names are your choice), an operation of `correctness.check` with the five positional things `check_operation.ask` hands. In order:
   1. Check its arguments, as `standin_check` does for fp32 `gemm`.
   2. Run **`cuda_adapter.check_device` first**. Its `device_unavailable` tool failure is the answer, before any build or attempt process (decision 6).
   3. Make a build directory under the system temporary directory. It is removed at the end and on every failure path, as `standin_check` does.
   4. Build T-0574's verification program with the selected kernel files through `cuda_adapter.build` at the target's flags. Hand the compiler's log to the keeper. A build failure gives the existing build answers of ADR-0060 (no new kind).
   5. Run the executable with the verification arguments and the process time limit the target's cap allows.
   6. Return the report for the existing judging (`hilclaw.harness.verification`; the oracle per HQ-0096 ② (a)).

   A nonzero status or an incomplete report of the attempt's process is broken, never a tool failure (ADR-0110 decision 3). A device lost after the probe is a run failure (decision 6).
4. **`hilclaw/cuda_run.py`**: `operation_for(target, *, sources)` for `sim.run` and `board.run`. It follows the same order with T-0574's timing driver, and its answer has the form `run_operation.ask` reads.
   - The same operation serves both tools (HQ-0095 ② (a)). Results differ only by the existing `step` values (ADR-0194 decision 5); no member is added.
   - The timing boundary is ADR-0194 decision 4 as T-0574's driver implements it.
   - `memory_bytes` stays the host process's and no GPU memory figure is reported (HQ-0090).
   - The unit is `ns` (target `units_per_ns` 1).
5. **No default change.** `check_definition.default_table` is not changed, and a call about `cuda_gpu` through the default registry stays `no_backend`. `cpu_standin`, `virtual_npu` and the mock behave and answer exactly as before. The host executor is test-only until slice 5 moves it into containers. Say this in the module docstrings and the PR body (NFR-4: the runtime builds and runs kernels only in containers).
6. **The real GPU** (FR-19 ⑤). Build a backend table in a test with `Backend("cuda_gpu", {...})` holding the three operations with the fixture selection. Call `correctness.check`, `sim.run` and `board.run` through the registry's tool functions, or through `check_operation.ask`/`run_operation.ask` if the tool functions need slice 6's start, with a test-placed fp32 `gemm` kernel at a small shape:
   - a correct kernel gives `pass` and a timed result;
   - a wrong kernel gives `fail`;
   - a kernel that does not compile gives the build answer with the compiler's log kept;
   - a kernel that exits nonzero gives broken.

   These tests skip where `nvcc`, its host compiler, `nvidia-smi` or a usable GPU is absent. The device-absent path (`device_unavailable`) is tested everywhere with the existing fault scripts or a stub `nvidia-smi` on `PATH`, because a real absent GPU is hard to cause (D29).
7. **Tests** (D12): happy, error, branch and negative cases for every public function of the two new modules and any touched `cuda_adapter` function. Cover:
   - refused arguments and a missing `sources` selection;
   - a selection that names no file or a non-regular file;
   - each answer above;
   - build-directory removal on every path.

   Existing tests stay unchanged except list assertions under D21. Foreseen: public-name pins of `cuda_adapter` if it gains a helper. List every edit in the PR body. The full suite passes in WSL2 with the CUDA `bin` on `PATH`. `hilclaw/` line and function coverage is ≥ 80%. `ruff check` and `ruff format --check` pass.
8. **Process**:
   - Follow the dev-item-address steps. Open a Draft PR and run a context-isolated review to Approve (≤ 14 rounds, D28). The review prompt names criterion 2 (HQ-0104 not decided) and criterion 5 (no default change, host executor test-only).
   - Once CI is green, self squash-merge with the PR body's last line `Task: T-0575`.
   - No ADR is written, because ADR-0207 decides this slice. If a choice outside ADR-0207 turns out to be a design OD, return BLOCKED under DRIVER §3 rather than inventing it.
   - In `Result` record the language and reason, the machine outputs, the real-GPU results with tool versions, any HQ, and any runtime acceptance item (D22).
   - Remove the task directory with `rm -r` (D29).

## Out of Scope

- The runtime GPU container, `--gpus all`, the probe container, the NVIDIA Container Toolkit install and the image pull (slice 5).
- Slice 6 and HQ-0104: `.cu` attempt names in `kernel_source`, the CUDA given-code bundle, `instance_start` true, the default-table entry, `run.commit` of a CUDA run.
- bf16 at CUDA, `model_run`, GPU memory figures (HQ-0090), the coder's CUDA path (HQ-0088 ① (c)), retries (OD-17).
- Starting `claude` in any form (D16).

## Follow-ups

## Result

PR #388, squash-merged as `51eaec58` (PR body's last line `Task: T-0575`); branch deleted. Review: 2 rounds. Round 1 approved with two nits: test `confirm_device`'s `device_unavailable` without stub programs (added) and say why `cuda_run` does not use `cuda_adapter.measure` (added to the PR body). The test was a change, so round 2 followed. It approved with one nit: record the flaky existing test below here (done). CI green on head `7501933d`. Not BLOCKED; no HQ; no ADR (ADR-0207 decides this slice). No §9 notice.

**Machine check (criterion 1; read before writing; nothing installed or pulled).** WSL2 Ubuntu 22.04:
- `/usr/local/cuda-13.1/bin/nvcc --version` → `Cuda compilation tools, release 13.1, V13.1.115` (build `cuda_13.1.r13.1/compiler.37061995_0`).
- `nvidia-smi` → NVIDIA GeForce RTX 4070, NVIDIA-SMI 615.78.02, KMD 617.14, CUDA UMD 13.4, 12282 MiB.
- `gcc`/`g++` 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3). Python 3.12.13 (venv `~/.venvs/hilclaw-driver`, already present).

**Language.** Python, as the sibling operations `standin_check` and `standin_run`.

**What landed.**
- `hilclaw/cuda_check.py`: `operation_for(target, *, sources)` returns the `correctness.check` operation. Steps, in order:
  1. Argument checks, as `standin_check` makes for fp32 `gemm`.
  2. `confirm_device` (`cuda_adapter.check_device`, 30 s). `device_unavailable` comes before the selection, the build directory and the build.
  3. `select_sources`: an empty selection is `no_kernel_source`; a selection that raises is `kernel_source_unreadable`; a path that is not a regular file is `build_input_missing`; another type raises `TypeError`.
  4. The build directory, from `standin_check.make_build_dir`. It is removed on every path.
  5. `build_executable`: `cuda_adapter.assemble_build` + `clang_build.build`. The log goes to the keeper. The build is answered by `check_build.read_build`/`place_error` (ADR-0060 rows).
  6. `cuda_adapter.run` with `m k n draws seed`, within the target-capped limit; the report is returned for the existing judging.
  
  The shared steps are public, for `cuda_run`.
- `hilclaw/cuda_run.py`: one operation serves `sim.run` and `board.run`. It follows the same order with the timing driver and answers in form (A), `(report, memory_bytes)`. `memory_bytes` is `memory_ceiling.figure(max_rss)` of the host process; no GPU memory figure is given.
- The kernel's files come from a required keyword-only selection (criterion 2; HQ-0104 is not decided). `default_table` is unchanged, and `cuda_gpu` via the default registry stays `no_backend` (criterion 5; test-only host executor, NFR-4).
- New fixture: `tests/cuda_fixtures/gemm_exit.cu`, which calls `exit(3)`.
- **Existing tests changed (D21): none.**

**Size.** 2 new non-test modules, about 470 lines (most of them docstrings). Within the recommendation.

**Verification.**
- Full suite under `coverage run --branch` in a WSL2 clone of `344d7f10`, with the CUDA `bin` on `PATH`: 42645 passed, 108 skipped, 1 failed (the flake below).
  - `hilclaw/` coverage: lines 99 % (19069/19132), functions 2000/2002.
  - `cuda_check.py` and `cuda_run.py`: 100 % line and branch coverage.
- After the round-1 nit, 754 passed in the CUDA, standin and check-definition test files.
- ruff check and format are clean.
- Real-GPU results on the RTX 4070 (nvcc 13.1 V13.1.115, g++ 11.4.0, driver 617.14), through a test-built `BackendTable([Backend("cuda_gpu", ...)])` + `backends.select` + `check_operation.ask` / `run_operation.ask`:
  - `gemm.cu` → `pass` at 5x33x7 and 8x8x8;
  - timed results for `sim.run` and `board.run` accepted by `timing.judge_report`;
  - `gemm_wrong.cu` → `fail`;
  - `broken.cu` → broken `build_exit_status`, with the log file written and naming the file;
  - `gemm_exit.cu` → broken `exit_status` (check and `board.run`);
  - `CUDA_VISIBLE_DEVICES=""` for the run only, after the device check → broken `exit_status`.
- No `claude` was started (D16), and no test run was made (D25).

**Observed (not touched): a flaky existing test.** `tests/test_cuda_adapter.py::test_real_gpu_interval_holds_the_completion_of_the_kernel` failed once in the full coverage run: an interval was below `HOLD_NS - STEP_NS - resolution` on WSL2. It passed in three reruns alone. This looks like timing noise in a real-GPU test under load, a candidate for a later task if it recurs (nightly or CI never runs it, since no GPU is there).

**Runtime acceptance items (D22).** None new. ADR-0207's container items stay with slice 5.

**Storage.** WSL `/tmp/hilclaw-driver/T-0575/` (clone, coverage data, logs) and `%TMP%/hilclaw-driver/T-0575/` (PR body, commit message, sync script, this draft) were removed with `rm -r`. No images, no installs.
