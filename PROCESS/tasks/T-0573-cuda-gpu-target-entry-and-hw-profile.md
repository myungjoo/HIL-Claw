---
id: T-0573
title: PLAN P3-16 (2) — ADR-0207 slice 2, the `cuda_gpu` hw_profile read on the host and with an image, the `Target` member `coder_loop` and the round-loop start's refusal, and the `cuda_gpu` target entry with `instance_start` false
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "HQ-0093", "HQ-0096", FR-10, FR-19, OD-33, OD-4, OD-26]
dependsOn: []
touchesFiles:
  - hilclaw/targets.py
  - hilclaw/cuda_profile.py
  - hilclaw/cuda_adapter.py
  - hilclaw/start_instance.py
  - hilclaw/new_run.py
  - hilclaw/given_eval.py
  - tests/test_targets.py
  - tests/test_cuda_profile.py
  - tests/test_start_instance.py
  - tests/test_new_run.py
  - tests/test_given_eval.py
  - tests/test_cuda_adapter.py
estimatedSize: {loc: 260, files: 6}
hq: []
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that one kind (`gemm`) of CUDA kernel goes through build, correctness, measurement and record with the real `nvcc` and GPU (D29). P3-12's remaining slices wait on HQ-0102 and HQ-0103, so under DRIVER §6 D31 ① P3-16 is the item to plan now. T-0572 (PR #385) landed **ADR-0207**, which decides the CUDA target and lists six slices in its decision 9. Slice 1 (`device_unavailable`) landed with it. Slice 6 waits on **HQ-0104** (the record of a CUDA kernel in a run and the CUDA C++ given-code bundle). That HQ's own text says slices 2 to 5 are not blocked by it.

This task is **slice 2**: the hw_profile of `cuda_gpu` (ADR-0207 decision 2), the new `Target` member `coder_loop` with the round-loop start's refusal, and the `cuda_gpu` entry with `instance_start` false (decision 3). Slices 3 and 4 (T-0574, T-0575) follow it. Expected size about 260 lines.

**Order check (D27 ①)** at planning time (main `b6333b4b`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`; RA-0056 is `미확인`.

**Brake (D31 ②).** This is the PLAN item's own work, so the brake does not apply. Do not harden existing paths beyond what this slice needs.

**Open HQs (D27 ⑦).** Do not anticipate or ask again HQ-0100, HQ-0102, HQ-0103 or **HQ-0104**. Do not ask again HQ-0088 ① (c), HQ-0090 or #5 B-7. If an owner-only part appears (a data-plane frame change under D23, or an install that is neither pre-allowed nor approved), write it in `## Result` as an HQ in the DRIVER §8 structure: Korean, the issue, options (a)/(b)… with the executor's recommendation, what it blocks and what it does not. Land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0573-<slug>`, the `Task: T-0573` trailer and the PR body's last line, size D30, tests D12, list assertions D21, **storage D29**: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0573/`); §6 lines **D29** (toolchain): "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; NVIDIA tools from NVIDIA's official site are pre-allowed; FR-19 ⑤ test skipping. Also §6 lines **D27 ⑥ ⑦** and **D31** (② brake, ③ machines), §8 (HQ structure) and §9.
- `PROCESS/PLAN.md`: P3-16 (line ~80; every sentence binds this task) and the paragraph above P3-15 (line ~77).
- `PROCESS/STATE.json` `humanQuestions`: HQ-0093, HQ-0095, HQ-0096, HQ-0097 and HQ-0104 (`question` and `decision`).
- `CLAUDE.md`: "개발 드라이버와 런타임의 구분" (never start `claude`) and the language policy.
- `ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`: **all of it**, especially decisions 2 and 3 and slice 2 of decision 9.
- `ARCHITECTURE/decisions/ADR-0035-od4-cpu-standin-hw-key-values.md` (decisions 3 to 6 and 8) and `ADR-0186-od14-standin-toolchain-from-image.md` (the toolchain read in one new container of the image). Also `ADR-0001-od4-key-schema.md` decisions 1 and 6 (name rule, open `toolchain` map).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decision 3 (the target table) and `ADR-0197-od32-virtual-npu-oracle-and-instance-start.md` decision 1. Also `ADR-0076-od8-instance-start-required-members.md` decision 1 (which accelerators an instance may start on) and `ADR-0200-od33-given-code-evaluation.md` decision 5.
- `PROCESS/tasks/T-0572-cuda-target-design-and-device-unavailable.md` `## Result` (the machine's CUDA facts) and `PROCESS/tasks/T-0543-cuda-adapter.md` `## Result`.
- Code: `hilclaw/targets.py`, `hilclaw/standin_profile.py` (the model for `cuda_profile.py`: line rules, spelling, `UnreadableFactError`, `_run_in_image`), `hilclaw/cuda_adapter.py` (`interpret_probe`, `device_probe`, `_DEVICE_QUERY`), `hilclaw/start_instance.py` (`_ACCELERATORS`), `hilclaw/new_run.py`, `hilclaw/given_eval.py` (around line 291), `hilclaw/keys.py` (hw_profile key validation).
- Tests: `tests/test_targets.py` (the `GOOD` member dict, `test_the_table_holds_cpu_standin_and_virtual_npu_and_not_the_mock`), `tests/test_standin_profile.py` (how stub programs stand in for machine commands), `tests/test_start_instance.py`, `tests/test_given_eval.py`.

## Acceptance Criteria

1. **Machine check first** (D29). Before writing, read without installing: `nvcc --version` (WSL2 `/usr/local/cuda-13.1/bin/nvcc`), `gcc --version`, and `nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader`. Record the outputs in `Result`. Nothing is installed or pulled in this task; no CUDA image is in the local store and pulling one is slice 5.
2. **`hilclaw/cuda_profile.py`** (new; Python), the hw_profile record of `cuda_gpu` by ADR-0207 decision 2:
   - `accelerator` `cuda_gpu`. `revision` is `<product name> sm_<major><minor>` from the host's device query, and a machine with more than one GPU line has no record. `toolchain` has exactly the three members `nvcc` (the release line as `cuda_adapter.interpret_probe` reads it), `gcc` (the first line of `gcc --version`) and `nvidia_driver` (the `driver_version` of the same query). `host` and `hw_source` follow `cpu_standin`'s rules.
   - `nvcc` and `gcc` are read in one new container of a named image when the caller names one, else on the host, as ADR-0186 does for `clang`. `nvidia_driver` and `revision` are always read on the host.
   - Every fact uses `standin_profile`'s line and spelling rules (reuse them; do not copy them). A fact that cannot be read raises the same kind of error, and nothing is substituted.
   - The device query may be a new function or constant in `cuda_adapter`. Keep `device_probe`'s existing query and outcomes unchanged; `check_device` (slice 1) answers as before.
   - The record passes the package's hw_profile validation (`keys`) unchanged. No data-plane frame changes (decision 2: `cuda_gpu` is a value of a name field, the three members are names of an open map). Say so in the PR body.
3. **`Target.coder_loop`** (decision 3): exactly a `bool`, checked like `model_run` and `instance_start`. `cpu_standin` and `virtual_npu` are `True`. The round-loop instance start refuses an accelerator whose `coder_loop` is false. Today that is `start_instance._ACCELERATORS`, used by `new_run`, including `--given-code`, because that option starts a round-loop run. The refusal is the existing `out_of_scope` answer, with no new outcome. `given_eval` keeps reading `instance_start` only. Add a public helper in `targets` beside `instance_start_accelerators` if it keeps both readers simple. Whether the member has a default is your choice; give the reason in the PR body.
4. **The `cuda_gpu` entry** in `targets.TABLE`, after `virtual_npu`. It has decision 3's table values: flags `("-O2", "-arch=native")`, trailing `()`, waiter `("-O2",)`, env `None`, build limit `120`, the process cap from `standin_settings`, memory `None`, unit `ns` with factor 1, `model_run` false, `instance_start` false and `coder_loop` false. **`contracts` is `()`** in this slice, because the `cuda` contract entry is slice 3 (T-0574) and `Target` refuses keys the contract table lacks. Export a name constant `CUDA_GPU` as the module does for `VIRTUAL_NPU`. Update the module docstring.
   - `check_definition.default_table` is **not** changed (no `cuda_gpu` backend until slice 6). A call about `cuda_gpu` stays `no_backend`.
   - Because `instance_start` is false, neither `new_run` nor `given_eval` admits `cuda_gpu`. Show this in a test.
   - `cpu_standin`, `virtual_npu` and the mock behave and answer exactly as before.
5. **Tests** (D12): happy, error, branch and negative cases for every touched public function. Cover:
   - `cuda_profile` with stub `nvidia-smi`, `nvcc`, `gcc` and `docker` programs placed on `PATH` by the test: the host path and the image path; two GPU lines; no GPU line; a missing program; an unreadable line; non-ASCII; an over-long value.
   - One real-machine test that reads the host record where `nvcc`, `gcc` and `nvidia-smi` with a GPU are present, and skips otherwise (FR-19 ⑤).
   - The `coder_loop` checks, including a non-bool value.
   - The round-loop start refusing a test-built target whose `instance_start` is true and `coder_loop` false, while `given_eval` accepts that target (a test-built table, or monkeypatching the bound tuples).
   - The `cuda_gpu` entry's values.

   Existing tests stay unchanged except list assertions under D21. Foreseen:
   - `test_the_table_holds_cpu_standin_and_virtual_npu_and_not_the_mock` in `tests/test_targets.py` (`tuple(TABLE)`, `len`, `repr`; its name may change with the count).
   - The `GOOD` member dict of `tests/test_targets.py`, and the `Target(...)` constructions in `tests/test_clang_adapter.py`, `tests/test_cuda_adapter.py`, `tests/test_model_run_binding.py`, `tests/test_qnn_adapter.py` and `tests/test_standin_check.py`, if the new member has no default.
   - Public-name pins of `targets` or `start_instance`.

   List every such edit in the PR body. The full suite passes in WSL2 with the CUDA `bin` on `PATH`; `hilclaw/` line and function coverage ≥ 80%; `ruff check` and `ruff format --check` pass.
6. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, then self squash-merge with the PR body's last line `Task: T-0573`. No ADR is written, because ADR-0207 decides this slice. If the real `nvcc` refuses a flag of decision 3, correct it in the entry and record it in `Result` (decision 3 allows this). In `Result` record the language and reason, the machine outputs of criterion 1, any HQ, and any runtime acceptance item for `PROCESS/RuntimeAcceptance.md` (D22). An example of such an item is the hw_profile read on a C-7 machine kind other than WSL2. Remove the task directory with `rm -r` at the end (D29).

## Out of Scope

- The `cuda` contract entry, the CUDA C programs (slice 3, T-0574) and the backend operations (slice 4, T-0575).
- The runtime GPU container, the NVIDIA Container Toolkit install and the image pull (slice 5).
- Anything of slice 6 or HQ-0104: `instance_start` true, a `.cu` attempt file, a CUDA given-code bundle, the default-table entry.
- `model_run` at `cuda_gpu`, GPU memory figures (HQ-0090), several GPUs on one machine.
- Starting `claude` in any form (D16; no test run is needed).

## Follow-ups

## Result

PR #386, squash-merged with the PR body (last line `Task: T-0573`); branch deleted. Review: 2 rounds (round 1 Approve with 3 nits, all fixed; one of them, refusing a leading zero in the compute capability, changed behaviour, so round 2 followed: Approve with one formatting nit, fixed under D20). Not BLOCKED; no HQ.

**Machine check (criterion 1; read only, nothing installed or pulled).** WSL2 (kernel 6.18.58.1-microsoft-standard-WSL2):
- `/usr/local/cuda-13.1/bin/nvcc --version` → `Cuda compilation tools, release 13.1, V13.1.115` (banner `nvcc: NVIDIA (R) Cuda compiler driver`, build `cuda_13.1.r13.1/compiler.37061995_0`).
- `gcc --version` → `gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0`.
- `nvidia-smi --query-gpu=name,compute_cap,driver_version --format=csv,noheader` → `NVIDIA GeForce RTX 4070, 8.9, 617.14`.
- The live record is `revision` `NVIDIA GeForce RTX 4070 sm_89`, `toolchain` `{nvcc: "Cuda compilation tools, release 13.1, V13.1.115", gcc: "gcc (Ubuntu 11.4.0-1ubuntu1~22.04.3) 11.4.0", nvidia_driver: "617.14"}` and `host` `{cpu: "Intel(R) Core(TM) i7-14700KF", os: "wsl ubuntu 22.04"}`, with key `cuda_gpu-7e2377db3ffd0c25`.
- Decision 3's flags stand: `nvcc -O2 -arch=native x.cu` and `nvcc -O2 w.c` built and ran on the host.

**Language.** Python, for the new `hilclaw/cuda_profile.py` and the touched modules, as their siblings are.

**What landed.**
- `cuda_profile.local_record(hw_source, *, timeout_s, image=None)`:
  - It reads `nvcc` and `gcc` on the host, or with an image each in its own new container. `nvidia_driver` and `revision` come from one host query.
  - Zero or several GPU lines give no record.
  - It reuses `standin_profile`'s line, spelling, kernel, host and image readings. `standin_profile` is beyond `touchesFiles`: its split into `_ruled_kernel`, `_host`, `_output` and `_run_in_image(program)` preserves behaviour.
- `Target.coder_loop` (no default) and `targets.coder_loop_accelerators()`.
- The `cuda_gpu` entry: `contracts` `()` and three false booleans.
- `CUDA_GPU` is defined in `targets`, and `cuda_profile.ACCELERATOR` reads it. The other direction would make an import cycle through `cuda_adapter` → `clang_adapter` → `targets`.
- `start_instance.start(..., coder_loop=True)`. `new_run` keeps the round-loop set, also with `--given-code`; `given_eval` passes `coder_loop=False`. `model_instances` keeps importing `_ACCELERATORS`, now the round-loop set.
- `check_definition.default_table` is unchanged.

**Existing tests changed (D21)** are listed in the PR body: `GOOD` and five `Target(...)` helpers gain `coder_loop`; the table-count test is renamed for three entries; `start_instance`'s signature pin and `_ACCELERATORS` pin are updated; and `cuda_profile.py` joins `test_standin_profile`'s list of modules that may name `standin_profile`.

**Verification.**
- Full suite under `coverage run --branch` in a WSL2 clone (Python 3.12.13, CUDA bin on `PATH`) at the round-1 head: 42466 passed, 108 skipped, 0 failed; `hilclaw/` line+branch coverage 99 % (`cuda_profile`, `targets`, `start_instance`, `standin_profile` 100 %). The later commits changed docstrings and the compute-capability pattern; the affected files were re-run and passed.
- The live `cuda_profile` test ran (not skipped) on this GPU.
- ruff check and format are clean. CI is green on the merged head.
- No `claude` was started (D16), and no test run was made (D25).

**Runtime acceptance item (D22)**, for `PROCESS/RuntimeAcceptance.md`:

> PLAN P3-16 / ADR-0207 결정 2. NVIDIA GPU가 하나 있는 C-7의 WSL2 밖 머신 종류(native Linux; Docker 이미지를 지정하는 경우 포함)에서 `hilclaw.cuda_profile.local_record`가 `revision`(`<제품명> sm_<major><minor>`)과 `toolchain`의 `nvcc`·`gcc`·`nvidia_driver`를 읽어 `keys.hw_profile_key`가 받는 레코드를 내는가. 이미지를 지정했을 때 `nvcc`·`gcc`가 이미지의 것이고 `nvidia_driver`가 호스트의 것인가. GPU가 둘 이상인 머신에서 레코드를 내지 않는가. 실패로 드러나면 ADR-0207 결정 2의 읽기 규칙을 다시 본다.

**Follow-ups.** None beyond ADR-0207's later slices.

**Storage.** WSL `/tmp/hilclaw-driver/T-0573/` (repo clone, coverage data, test log, build check files) and `%TMP%/hilclaw-driver/T-0573/` (PR body) were removed with `rm -r`. No images and no installs.

