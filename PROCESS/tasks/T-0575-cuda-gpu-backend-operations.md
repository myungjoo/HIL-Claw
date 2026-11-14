---
id: T-0575
title: PLAN P3-16 (4) — ADR-0207 slice 4, the `cuda_gpu` operations of `correctness.check`, `sim.run` and `board.run` on the host executor (device check first, `nvcc` build, run, the existing judging), held by a test-built backend table and checked on the real GPU
phase: P3
status: TODO
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
