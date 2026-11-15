---
id: T-0579
title: PLAN P3-16 (6b) — ADR-0207 slice 6, second half: open `cuda_gpu` to given code (`instance_start` true, the start's scope, `given_eval` with a `.cu` file, the `cuda_gpu` backend in the default table) and demonstrate a test-placed fp32 `gemm` kernel through `correctness.check` at both points, `board.run` and `run.commit` on the real GPU
phase: P3
status: DONE
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

- **Outcome**: DONE. PR #392 (squash-merged; merge commit: see the PR). Reviews by a context-isolated `dev-reviewer`: see the PR. Round 1 asked for changes: this Result, stub tests of the real `check_tool`/`run_tool` on a given `cuda_gpu` run, a test name, and the reflow of a docstring. No HQ.
- **ADR-0208 followed as landed; no difference from the task.** The start's scope needed no code change. The given-code accelerators come from the table, `covers_at` with `served_at` already scopes `cuda_gpu` to fp32 `gemm`, and the readers keep `c_kernel` for the absent kind.
- **Criterion 7, the `.c` case.** ADR-0208 decision 2 reads no name of the user's file. A user file named `kernel.c` given at `cuda_gpu` is therefore placed as `given.cu` and evaluated (`test_given_eval`). The `.c` case that reaches the table is an `output/` holding `given.c` at `cuda_gpu`. It is answered `no_kernel_source` after the probe and before any build, for all three tools (`test_cuda_check`).
- **Language**: Python, the language of every touched module. No process or tool is added.

**Machine check (criterion 1; WSL2 Ubuntu 22.04, kernel 6.18.58.1-microsoft-standard-WSL2, 2026-11-15 ~13:20Z)**
- `docker info`: Server Version 29.1.3; Runtimes `nvidia runc io.containerd.runc.v2`; Default Runtime `runc`.
- `docker image ls cuda`: `cuda:13.1.2`, id `1efffc671e20`, 6.95GB (T-0576's image, unchanged).
- Inside `cuda:13.1.2`: `nvcc` "Cuda compilation tools, release 13.1, V13.1.115" (Build cuda_13.1.r13.1/compiler.37061995_0); `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.
- Host `nvidia-smi`: NVIDIA GeForce RTX 4070, 12282 MiB, driver 617.14, compute capability 8.9. WSL `nvcc` at `/usr/local/cuda/bin/nvcc`.
- Nothing installed or pulled.

**Change**
- `targets`: `cuda_gpu` `instance_start=True`; `coder_loop` and `model_run` stay `False`.
- `check_definition.default_table`: `Backend("cuda_gpu", ...)` with `correctness.check` = `cuda_check.operation_for(target, sources=cuda_check.compiled_sources)` and one `cuda_run.operation_for(target, sources=cuda_check.compiled_sources)` for `sim.run` and `board.run`; no `profiler.collect`. The imports stay inside `default_table`.
- `given_eval`: the second argument is described as the code file, and the bad-usage text now says "code file". Exit statuses are unchanged.
- Docstrings: `start_instance`, `instance_start`, `check_tool`, `run_tool`, `cuda_check`, `cuda_run`, `kernel_source`.
- Size: 10 non-test modules, about 130 changed lines (mostly docstrings). New `tests/test_cuda_gpu_demonstration.py`.

**Demonstration on the real GPU (FR-19 (5))**
- `tests/test_cuda_gpu_demonstration.py` calls `given_eval.main` in process, with `HILCLAW_CUDA_IMAGE=cuda:13.1.2`, a data root under pytest's `tmp_path`, and an hw_profile from `cuda_profile.local_record("external", image="cuda:13.1.2")`. The op is fp32 `gemm` 5x33x7, with `draws` 2, `n_max` 20 and tolerance rtol 1e-4 / atol 1e-4. Results: `gemm.cu` gives exit 0; the composed `gemm_wrong.cu` gives exit 10, `sim` fail/not_verified, no `board.run`, the run over and committed. Both pass in WSL2 (about 30 s).
- **A hand run with the same request**, data root `/tmp/hilclaw-driver/T-0579/data`, removed at the end:
  - hw_profile `revision` "NVIDIA GeForce RTX 4070 sm_89"; `toolchain` nvcc "Cuda compilation tools, release 13.1, V13.1.115", gcc "gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0", nvidia_driver "617.14"; `host` "Intel(R) Core(TM) i7-14700KF" / "wsl ubuntu 22.04".
  - Run `20261115t133010z-a8240788df5db824`, exit 0: `{"outcome":"measured","place":{"given_code":"caf3327a…"},"sim":{"outcome":"pass","standing":"verified"},"board":{"outcome":"pass","standing":"verified"},"timing":{"outcome":"not_converged","median":37786.0,"unit":"ns"}}`.
  - `correctness_check_{sim,board}_v2`: `pass`, 2 draws, no failed or non-finite element.
  - `board_run_timing_v3`: `not_converged`, `sample_form` interval, 20 intervals of about 27.7 to 74.5 us, `resolution` 1 ns, `memory_bytes` 110317568 (the host process's peak RSS through the waiter, as T-0577), `ceiling` `not_stated`.
  - Data-root repository: one commit "Commit the owed files of a run (run.commit)".

**Verification**
- Full suite in a WSL2 clone of the branch (first commit), with `/usr/local/cuda/bin` on `PATH`, under `coverage run --source=hilclaw`: 42933 passed, 108 skipped, 1 failed (750 s). The failure was the list assertion in `test_backend_conformance`, fixed in the next commit (D21). `hilclaw/` lines 19217/19280 (99.7%), functions 1820/1822. `check_definition`, `targets` and `start_instance` are at 100%.
- After the round-1 fixes, the touched and neighbouring test files (13 files, the real-GPU tests included) pass again in WSL2: 1867 passed, 4 skipped (the host clang builds no OpenMP program). `ruff check` and `ruff format --check` are clean.
- No `claude` was started (D16), and there was no test run (D25). `given_eval` starts no `claude`.

**Changed existing assertions (D21 and the slice's design; listed in the PR body)**
- `test_targets`: the two `instance_start_accelerators()` tuples gain `cuda_gpu`; `cuda_gpu` `instance_start` is now `True`; `test_no_instance_and_no_coder_loop_starts_at_cuda_gpu` becomes `test_an_instance_but_no_coder_loop_starts_at_cuda_gpu`; `test_a_call_about_cuda_gpu_stays_no_backend` becomes `..._reaches_its_backend`.
- `test_start_instance`: `_GIVEN_ACCELERATORS` gains `cuda_gpu`; `test_no_instance_starts_at_cuda_gpu[True|False]` becomes `test_no_instance_of_the_round_loop_starts_at_cuda_gpu` (`coder_loop=True` only).
- `test_given_eval`: `test_cuda_gpu_is_refused_while_its_instance_start_is_false` is replaced by a refusal for a target with `instance_start` false and one for a name with no target.
- `test_check_definition`: the import set and two name lists gain `cuda_gpu`, and one test is renamed.
- `test_cuda_check`: `test_the_default_table_has_no_cuda_gpu_entry` becomes `..._has_the_cuda_gpu_entry`.
- `test_backend_conformance`: the default-table name list gains `cuda_gpu`.

**HQ**: none.

**Runtime acceptance items (D22)**: none new. RA-0086 already holds ADR-0207's container items. The given-code evaluation at `cuda_gpu` is a person's command (no `claude`), and this task demonstrated it on the development PC's GPU (D31).

**Storage.**
- The task directories are removed with `rm -r` at the end: in WSL, `/tmp/hilclaw-driver/T-0579/` (the clone, the coverage data, the demonstration's data root and script); in Git Bash, `/tmp/hilclaw-driver/T-0579/` (the PR body).
- No work image was made. The tool image `cuda:13.1.2` is kept.
- Left alone: a WSL shell loop from another task (`while pgrep -f "coverage run --branch --source=hilclaw" ...; tail ... /tmp/hilclaw-driver/T-0573/full.log`, pid 285998). Its `pgrep -f` matches its own command line, so it never ends. Owner: T-0573.
