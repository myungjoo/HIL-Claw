---
id: T-0579
title: PLAN P3-16 (6b) — ADR-0207 slice 6, second half: open `cuda_gpu` to given code (`instance_start` true, the start's scope, `given_eval` with a `.cu` file, the `cuda_gpu` backend in the default table) and demonstrate a test-placed fp32 `gemm` kernel through `correctness.check` at both points, `board.run` and `run.commit` on the real GPU
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "ADR-0208", "HQ-0104", "HQ-0095", "HQ-0096", "HQ-0097", FR-9, FR-10, FR-19, OD-33, NFR-4]
dependsOn: [T-0578]
touchesFiles:
  - hilclaw/targets.py
  - hilclaw/instance_start.py
  - hilclaw/start_instance.py
  - hilclaw/given_eval.py
  - hilclaw/check_definition.py
  - hilclaw/check_tool.py
  - hilclaw/run_tool.py
  - hilclaw/cuda_check.py
  - hilclaw/cuda_run.py
  - tests/test_targets.py
  - tests/test_instance_start.py
  - tests/test_start_instance.py
  - tests/test_given_eval.py
  - tests/test_check_definition.py
  - tests/test_check_tool.py
  - tests/test_run_tool.py
  - tests/test_cuda_gpu_demonstration.py
estimatedSize: {loc: 380, files: 9}
hq: []
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that a CUDA `gemm` kernel goes through build, correctness, measurement **and record** with the real `nvcc` and GPU (D29).

- [ADR-0207](../../ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md) decision 9 **slice 6** is the last slice.
- The owner answered its HQ, **HQ-0104 (a)**, on 2026-11-15.
- **T-0578** writes ADR-0208, which records that answer and decides the rest of slice 6. It also lands the frame code:
  - the target-aware reader of `output/` (`.cu` at `cuda_gpu`);
  - the `given.cu` placement;
  - the reading of the absent kind;
  - a `cuda_gpu` `sources` selection, not yet registered.
- **This task** opens `cuda_gpu` to given code and runs the demonstration. When it is `DONE`, PLAN P3-16's completion criterion is met.

It depends on **T-0578** and cannot start before it is `DONE`. If T-0578 returns BLOCKED, this task waits. **If ADR-0208 as landed decides any point below differently, ADR-0208 wins**: follow it, and note the difference in `Result`.

**Order check (D27 ①)** at planning time (main `57509340`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**Brake (D31 ②).** This is the PLAN item's own work, which is exempt. Do not harden existing paths beyond what this slice needs.

**Open HQs (D27 ⑦).** Do not ask again or anticipate:

- HQ-0102 and HQ-0103 (P3-12);
- HQ-0088 ① (c) (the coder's CUDA path);
- HQ-0090 (GPU memory figures);
- #5 B-7.

If an owner-only part appears, write it in `## Result` as an HQ in the DRIVER §8 structure: Korean; the issue; options (a)/(b)… with the executor's recommendation; what it blocks and what it does not. Land the rest and return `DONE` (D27 ⑥). Owner-only parts here are:

- a data-plane frame change beyond HQ-0104 (a) under D23;
- an install that is neither pre-allowed nor approved;
- running attempt code outside a container as runtime behaviour.

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0579-<slug>`, the `Task: T-0579` trailer and the PR body's last line, size D30, tests D12, list assertions D21, and **storage D29** (temporary files and any test data root only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0579/`).
  - §6 lines **D29** (toolchain: "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; FR-19 ⑤ test skipping), **D27 ⑥ ⑦**, **D31**.
  - §8 and §9.
- `PROCESS/PLAN.md` P3-16 (line ~80).
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0104** (the whole `decision`), HQ-0095 (② (a)), HQ-0096 (② (a) and its addition), HQ-0097 ((a) (i)) and HQ-0090.
- ADRs:
  - **ADR-0208** (landed by T-0578): all.
  - [ADR-0207](../../ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md): decisions 3, 5 to 9.
  - [ADR-0197](../../ARCHITECTURE/decisions/ADR-0197-od32-virtual-npu-oracle-and-instance-start.md): decisions 1 to 3 (the precedent of opening a second target).
  - [ADR-0076](../../ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md): decisions 1 to 5.
  - [ADR-0200](../../ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md): decisions 4 to 6. [ADR-0202](../../ARCHITECTURE/decisions/ADR-0202-od33-given-attempt-in-feedback.md): decision 2.
  - [ADR-0070](../../ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md): decision 3. ADR-0167: decision 3.
- `PROCESS/tasks/T-0578-cuda-kernel-record-adr-and-attempt-files.md` and `PROCESS/tasks/T-0577-cuda-gpu-operations-in-containers.md` (`## Result` of each: the ADR's choices, the selection's name, the image tag, the machine facts).
- Code:
  - `hilclaw/targets.py` (`_cuda_gpu`, `instance_start_accelerators`, `coder_loop_accelerators`);
  - `hilclaw/start_instance.py` (`_ACCELERATORS`, `_GIVEN_ACCELERATORS`, `start`), `hilclaw/instance_start.py` (`prepare`, `_NOT_THESE_ACCELERATORS`), `hilclaw/new_run.py`;
  - `hilclaw/given_eval.py` (the docstring's ten steps, `_request_refusal`, the code-file reading);
  - `hilclaw/given_attempt.py`;
  - `hilclaw/check_definition.py` (`default_table`);
  - `hilclaw/check_tool.py` and `hilclaw/run_tool.py` (the run's kind and the given-code refusal);
  - `hilclaw/cuda_check.py` and `hilclaw/cuda_run.py` (`operation_for(target, *, sources)`, T-0578's selection), `hilclaw/cuda_image.py`, `hilclaw/cuda_profile.py` (or the hw_profile module T-0573 chose).
- Tests:
  - `tests/test_given_eval.py`, `tests/test_check_definition.py`, `tests/test_start_instance.py`, `tests/test_instance_start.py`, `tests/test_targets.py`;
  - `tests/test_cuda_check.py` and `tests/test_cuda_run.py` (the real-GPU tests and their skip conditions);
  - `tests/cuda_fixtures/` (`gemm.cu`, `gemm_wrong.cu`, `broken.cu`, `gemm_exit.cu`).

## Acceptance Criteria

1. **Machine check first** (D29). Before writing, read and record in `Result`:
   - `docker info` (the `nvidia` runtime present);
   - `docker image ls cuda`;
   - `nvcc --version` and `gcc --version` inside `cuda:13.1.2`;
   - `nvidia-smi` on the host.

   If the toolkit or the image T-0576 recorded is gone, do not reinstall or pull anything. Return BLOCKED with the fact.
2. **The target entry** (`hilclaw/targets.py`). `cuda_gpu`'s `instance_start` becomes `True`; `coder_loop` stays `False` and `model_run` stays `False` (ADR-0207 decision 3).
   - `instance_start_accelerators()` then names `cuda_gpu`.
   - `coder_loop_accelerators()` does not.
   - `hilclaw.new_run` (the coder's round loop) still refuses `cuda_gpu` as `out_of_scope`.
3. **The start's scope** (`hilclaw/instance_start.py`, `hilclaw/start_instance.py`), as ADR-0208 widens ADR-0076 decision 1:
   - A given-code instance at `cuda_gpu` whose stated `op_signature` is covered by the contract `cuda_gpu` serves (fp32 `gemm`, language `cuda`) is in scope, with `cpu_standin`'s required set.
   - No `op_signature` is `MissingMembersError`, as at `virtual_npu` (ADR-0197 decision 1).
   - Any other `op_signature` is out of scope.
4. **The given-code command** (`hilclaw/given_eval.py`). A request at `cuda_gpu` with one `.cu` file is started, placed as `output/given.cu` (T-0578's placement) and evaluated through the existing ten steps:
   - `correctness.check` at `sim` and `board`, each followed by `checks.read`;
   - `board.run`;
   - `round.end`;
   - `run.commit`.

   The command line's second argument is described as the code file (C at `cpu_standin`/`virtual_npu`, CUDA C++ at `cuda_gpu`). Every existing exit status and its meaning are unchanged. Exit status 19 (`bad_given_code`) keeps its meaning (the file cannot be read or is too large).
5. **The tools** (`hilclaw/check_tool.py`, `hilclaw/run_tool.py`) accept the given-code run at `cuda_gpu` as ADR-0208 reads its absent kind. Every other run is answered as today.
6. **The default table** (`hilclaw/check_definition.py`). Add a `Backend` named `cuda_gpu` that offers:
   - `correctness.check` with `cuda_check.operation_for(target, sources=<T-0578's selection>)`;
   - `sim.run` and `board.run` with `cuda_run.operation_for(...)` built the same way (one operation for both tools, HQ-0095 ② (a));
   - no `profiler.collect`.

   Building the table still reads no image, and still imports no NumPy beyond what it imports today (check the module docstring's import rule). Update `default_table`'s docstring and the module docstring.

   `cpu_standin`, `virtual_npu` and the mock behave and answer exactly as before, and every existing `cpu_standin` container command stays byte-for-byte the same.
7. **The demonstration on the real GPU** (FR-19 ⑤), in a new test module `tests/test_cuda_gpu_demonstration.py`:
   - Run `hilclaw.given_eval` in process, through its public entry, against a data root under the task directory or pytest's `tmp_path`. Use a request at `cuda_gpu`: an hw_profile read on this machine by T-0573's module, the fp32 `gemm` `op_signature` at a small shape, and the user's tolerance. Set `HILCLAW_CUDA_IMAGE=cuda:13.1.2` and use the test-placed `tests/cuda_fixtures/gemm.cu`.
   - Assert:
     - exit status 0;
     - `instance.json` version 3 with `given_code` and no `candidate_kind`;
     - the attempt's `output/given.cu`;
     - `correctness.check` `pass` at both points and standing `verified`;
     - a `board.run` result accepted by `timing.judge_report`, with `memory_bytes` > 0;
     - `run_status` `"over"`;
     - the run committed in the data root's repository.
   - Also show that a wrong kernel (`gemm_wrong.cu`, composed into one file as T-0577's `Result` explains) ends with standing not `verified` and no `board.run`.
   - These tests skip with a stated reason where Docker, the image, the toolkit or a usable GPU is absent, so CI skips them.
   - Test every new branch everywhere with stubs (the stub container client of `tests/test_cuda_check.py`, or a stub backend table), including:
     - `target_refused` for an accelerator still outside `instance_start`;
     - `.c` given code at `cuda_gpu`, which is no kernel source by ADR-0208 and is answered as the table maps it.
8. **Tests** (D12): happy, error, branch and negative cases for every public function of the touched modules. Existing tests stay unchanged except list assertions under D21. Foreseen:
   - the accelerator tuples of `targets` (`instance_start_accelerators`);
   - the backend-name list of `default_table`;
   - the `cuda_gpu` `no_backend` assertions T-0575 to T-0577 added (`a cuda_gpu call through the default registry stays no_backend`).

   Those last ones change because this slice's design registers the backend (ADR-0207 decision 9 slice 6). List each changed assertion in the PR body.

   Verification:
   - the full suite passes in WSL2 with the CUDA `bin` on `PATH`;
   - `hilclaw/` line and function coverage ≥ 80%;
   - `ruff check` and `ruff format --check` pass.
9. **Process**:
   - Follow the dev-item-address steps. No ADR is written: ADR-0207 and ADR-0208 decide this slice. If a choice outside them turns out to be a design OD, return BLOCKED under DRIVER §3 rather than inventing it.
   - Open a Draft PR and run a context-isolated review to Approve (≤ 14 rounds, D28). The review prompt names criterion 2 (`coder_loop` stays false), criterion 6 (`cpu_standin` byte-for-byte) and criterion 7 (the real-GPU demonstration through `run.commit`).
   - Once CI is green, self squash-merge with the PR body's last line `Task: T-0579`.
   - In `Result` record:
     - the language and reason;
     - the machine outputs;
     - the demonstration's results with tool versions, the image tag, the run id and its verdicts and timing;
     - any HQ;
     - any runtime acceptance item (D22). RA-0086 already holds ADR-0207's container items; add one only for a new fact.
   - Remove the task directory, including the demonstration's data root, with `rm -r`, and any work image by its tag (D29). Keep `cuda:13.1.2`.

## Out of Scope

- The coder's CUDA path (HQ-0088 ① (c)) and `coder_loop` true; `model_run` at `cuda_gpu`; bf16 at CUDA; GPU memory figures (HQ-0090); retries (OD-17).
- Multi-file bundles and own build settings (ADR-0200 decision 2).
- Several GPUs on one machine, a GPU on another machine (OD-14, #5 B-2), the Qualcomm target.
- Installing anything or pulling any image.
- The flaky real-GPU timing test on the hold list (T-0575's observation), unless it blocks this task's verification.
- Starting `claude` in any form (D16); a test run (D25). `given_eval` starts no `claude`.

## Follow-ups

## Result
