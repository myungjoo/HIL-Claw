---
id: T-0574
title: PLAN P3-16 (3) — ADR-0207 slice 3, the fp32 `gemm` contract entry in language `cuda` served at `cuda_gpu` only, and the hand-written C verification and timing programs against the CUDA runtime's C interface, checked on the real GPU with a test-placed kernel
phase: P3
status: DONE
commitMode: code
coversReq: [D31, "PLAN P3-16", "ADR-0207", "HQ-0096", FR-9, FR-10, FR-19, OD-33, OD-6]
dependsOn: [T-0573]
touchesFiles:
  - hilclaw/gemm_cuda_contract.py
  - hilclaw/contract_table.py
  - hilclaw/targets.py
  - hilclaw/harness/cuda_verification_program.c
  - hilclaw/harness/cuda_timing_driver.c
  - hilclaw/harness/cuda_programs.py
  - tests/test_gemm_cuda_contract.py
  - tests/test_contract_table.py
  - tests/test_targets.py
  - tests/harness/test_cuda_programs.py
  - tests/cuda_fixtures/gemm.cu
estimatedSize: {loc: 480, files: 6}
hq: []
---
## Why

**PLAN P3-16** (line ~80) asks to show on this PC's GPU that one kind (`gemm`) of CUDA kernel goes through build, correctness, measurement and record with the real `nvcc` and GPU (D29). **ADR-0207** (T-0572, PR #385) decides how. This task is **slice 3** of its decision 9. It covers the contract entry `gemm`/`fp32`/`row_major`/`cuda` (decision 4) and the two hand-written C programs, a verification program and a timing driver, against the CUDA runtime's C interface. The programs are checked on the real GPU with a kernel that a test places.

It depends on **T-0573** (slice 2: the `cuda_gpu` target entry with `contracts` `()`). This task puts the new key into `cuda_gpu.contracts`. Slice 4 (T-0575) builds the backend operations on these programs. Slice 6 waits on **HQ-0104**. That HQ's own text says slices 2 to 5 are not blocked.

**Size.** About 480 lines: 2 C files of about 150 lines each, a contract module and the table edits. The programs and the entry form one feature, and ADR-0207 lists them as one slice, so they are not split (§5, D20 ③).

**Order check (D27 ①)** at planning time (main `b6333b4b`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.

**Brake (D31 ②).** This is the PLAN item's own work, which is exempt from the brake. Do not generate the CUDA programs and do not harden other paths (ADR-0207 decision 4: generation is hardening beyond the demonstration).

**Open HQs (D27 ⑦).** Do not ask again or anticipate HQ-0100, HQ-0102, HQ-0103 or **HQ-0104**. Do not ask again HQ-0088 ① (c), HQ-0090 or #5 B-7. If an owner-only part appears, write it in `## Result` as an HQ in the DRIVER §8 structure (Korean; the issue; options (a)/(b)… with the executor's recommendation; what it blocks and what it does not). Owner-only parts are a data-plane frame change under D23 or an install that is neither pre-allowed nor approved. Land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`: **§3-5 and §5** (branch `claude/T-0574-<slug>`, the `Task: T-0574` trailer and the PR body's last line, size D30, the file cap, tests D12, list assertions D21, **storage D29**: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0574/`).
- `PROCESS/DRIVER.md` §3: the **승인된 열린 목록** "커널 계약 표" (D23). Adding a contract entry and its values is not a frame change.
- `PROCESS/DRIVER.md` §6 lines **D29** (toolchain: "task가 요구하는 벤더 툴체인이 있는지는 planner가 아니라 executor가 코드를 쓰기 전에 머신에서(넣어 둔 이미지 포함) 확인한다"; NVIDIA tools from NVIDIA's official site are pre-allowed; FR-19 ⑤ test skipping), **D27 ⑥ ⑦**, **D31**, §8 and §9.
- `PROCESS/PLAN.md`: P3-16 (line ~80).
- `PROCESS/STATE.json` `humanQuestions`: HQ-0096 (② (a): the oracle is the contract's existing reference with the user's tolerance) and HQ-0104.
- `ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md`: **all**, especially decisions 4 and 8 and slice 3.
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`: decisions 4 (the GPU timing boundary) and 8 (CUDA C++ only as test fixtures; a GPU target's harness is C against the vendor runtime's C interface).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: the contract, decisions 4, 5, 7 and 9. `ADR-0177-od18-od6-contract-table.md`: decision 1 (**"at most one entry per kind, dtype and layout"**, because the record states no language, `ADR-0031-od8-instance-record-op-signature.md` decision 2) and decision 2.
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md` (the verification program's command line and report) and `ADR-0009-od13-cpu-standin-timing-run.md` (the timing driver's command line and report).
- `ARCHITECTURE/Requirements.md`: the register's **"행 형식"** paragraph (line ~85). `ARCHITECTURE/OpenDecisionProposals.md`: the header's **"기록 규칙"** (line 8). `ARCHITECTURE/StandardScenarios.md`: the first paragraph of § 검사 결과. Read these only if criterion 2 leads you to write an ADR.
- `PROCESS/tasks/T-0546-cuda-gpu-timing-and-gpu-bound-results.md` `## Result` (the timing boundary as built on this GPU) and `PROCESS/tasks/T-0572-cuda-target-design-and-device-unavailable.md` `## Result` (machine facts).
- Code: `hilclaw/contract_table.py`, `hilclaw/gemm_contract.py`, `hilclaw/targets.py`, `hilclaw/cuda_adapter.py` (`build`, `run`, `measure`, `_driver_arguments`), `hilclaw/harness/verification_program.c`, `hilclaw/harness/timing_driver.c`, `hilclaw/harness/verification.py` (`program_arguments`, `run_verification`, `judge_report`), `hilclaw/harness/timing.py` (`driver_arguments`, `parse_report`, `run_timing`), `hilclaw/harness/verification_build.py`, `hilclaw/harness/timing_build.py`, and `tests/cuda_fixtures/timing.cu`.
- The readers of `contract_table.TABLE` (criterion 2): `hilclaw/catalog.py`, `catalog_tool.py`, `check_admission.py`, `check_answer.py`, `check_result.py`, `run_admission.py`, `run_result.py`, `model_graph.py`, `model_instances.py`, `harness/bf16_program_generator.py`, `harness/bf16_timing.py` and `harness/bf16_verification_arrays.py`. Also the callers of `contract_table.entry` and `task_contract`.
- Tests: `tests/test_contract_table.py` (the pins named in criterion 5), `tests/test_targets.py` (the `cpu_standin` contracts pin near line 62), `tests/test_cuda_adapter.py` (real-GPU skip fixtures).

## Acceptance Criteria

1. **Machine check first** (D29). Read `nvcc --version` (WSL2 `/usr/local/cuda-13.1/bin`) and `nvidia-smi` before writing, and record them in `Result`. Nothing is installed or pulled.
2. **The contract entry** (decision 4):
   - A new module `hilclaw/gemm_cuda_contract.py`. It has `KIND` `gemm`, `DTYPE` `fp32`, `LAYOUT` `row_major` and `LANGUAGE` `cuda`. Its `PROTOTYPE` is the declaration of decision 4. fp32 `gemm`'s shapes, operands, `covers` and `op_signature_record` are reused from `gemm_contract`, not copied. `task_contract` carries the `cuda` language and this prototype.
   - The entry is appended to `contract_table.TABLE` after the seven existing entries, `checked` and `timed`.
   - **`cpu_standin` does not serve it.** Its `contracts` become the existing seven keys, not `tuple(TABLE)`. `virtual_npu` keeps its six bf16 keys. `cuda_gpu.contracts` becomes exactly this key.
   - **Existing answers do not change.** The table now has two entries for `gemm`/`fp32`/`row_major`, so ADR-0177 decision 1's "at most one entry per kind, dtype and layout" no longer holds as written. Audit every reader of `TABLE` listed in Required Reading. Without a target, `entry`, `covers`, `check_covers`, `run_covers`, `start_covers` and `task_contract` must answer exactly as before for every record. The C entry comes first, so the first match stays the C contract. At `cuda_gpu`, the predicates pick the `cuda` entry. Every other reader must keep its present behaviour at `cpu_standin` and `virtual_npu`; filter by language or target where a reader needs it. Prefer the design that leaves the most readers untouched.
   - Record in the PR body which readers you changed and why.
   - If the audit shows that the selection by target needs a recorded decision beyond ADR-0207 decision 4, write one short §9 ADR in this task. That could be an amendment reading of ADR-0177 decision 1, or how a language is chosen for a record that states none. Check the number at start. The register edits follow the recording rules exactly: the OD-6 or OD-33 row of `Requirements.md` gets one link in `**확정분**:` and its `**잔여**:` rewritten in place (행 형식); § OD-n of `OpenDecisionProposals.md` gets one `- **채택분**` line with end statuses rewritten in place (기록 규칙). No restatement of the ADR and no dated paragraph. Recheck coverage by StandardScenarios' rule and update § 검사 결과 only as its first paragraph says. If the choice changes a data-plane frame (D23), write an HQ instead.
3. **The two C programs** (decision 4; ADR-0194 decisions 4 and 8). Write `hilclaw/harness/cuda_verification_program.c` and `cuda_timing_driver.c` in C against `cuda_runtime_api.h`.
   - They keep the **command lines and report forms** of `verification_program.c` and `timing_driver.c`. This lets `hilclaw.harness.verification` and `hilclaw.harness.timing` judge their output unchanged: the same inputs, reference, comparison and timing report.
   - The harness owns the context, `cudaMalloc`, the copies before the first repeat and after the last, and `cudaDeviceSynchronize`: before the start reading outside the interval, and before the end reading inside it. Transfers stay outside the timed interval. The kernel gets device pointers and allocates and copies nothing.
   - A CUDA runtime error ends the process with a nonzero status and no report that the Python halves would accept as complete. It is never read as a tool failure (ADR-0110 decision 3).
   - A small Python module `hilclaw/harness/cuda_programs.py` (or constants beside the existing build modules; your choice) names the two source paths for slice 4. Every new `hilclaw/` module has a test file (D12 ④).
4. **The real GPU** (FR-19 ⑤).
   - Add a test-placed kernel `tests/cuda_fixtures/gemm.cu`. It defines `extern "C" void hilclaw_gemm(...)` per decision 4 and launches a simple correct kernel. CUDA C++ belongs only in test fixtures (ADR-0194 decision 8).
   - Tests build each program with the kernel through `cuda_adapter.build` at the `cuda_gpu` target's flags on the host.
   - The verification output is judged `pass` by `run_verification` at a small and a non-square shape with the user's `rtol`/`atol` (HQ-0096 ② (a)).
   - A deliberately wrong kernel (a second fixture) is judged `fail`.
   - The timing driver's report is accepted by `run_timing`.
   - These tests skip where `nvcc`, its host compiler, `nvidia-smi` or a usable GPU is absent. CI keeps passing without them. Command-line and report parsing that needs no GPU runs everywhere.
5. **Tests** (D12): happy, error, branch and negative cases for every touched public function.
   - Cover the new contract module, `cuda_gpu` serving exactly the `cuda` key, and `cpu_standin`/`virtual_npu` not serving it.
   - Cover the unchanged answers without a target for fp32 `gemm` records, and the picks at `cuda_gpu`.
   - Cover refused inputs to the programs: a wrong argument count, a leading zero, a zero dimension. Each must exit nonzero without a complete report.
   - **Directed changes to existing tests** (ADR-0207 decision 4 adds a second language): `test_another_language_names_no_entry` and `test_at_most_one_entry_per_kind_dtype_and_layout` in `tests/test_contract_table.py`. Rewrite each to state the new rule, for example "at most one entry per kind, dtype, layout and target-served language". Do not delete them.
   - Beyond those, existing tests stay unchanged except list assertions under D21. Foreseen: `test_the_table_lists_the_seven_contracts_keyed_by_their_binding`, `test_public_names_of_the_module` (if any), the `cpu_standin` contracts pin in `tests/test_targets.py` (`tuple(contract_table.TABLE)`, `len == 7`), the `cuda_gpu` `contracts` pin of T-0573, and the pinned contract lists of `check_result`/`run_result`/`check_answer` tests if the audit touches them.
   - List every edit in the PR body. The full suite passes in WSL2 with the CUDA `bin` on `PATH`. `hilclaw/` line and function coverage stays ≥ 80%. `ruff check` and `ruff format --check` pass. The C files compile warning-free under the existing C gate's flags where that gate applies.
6. **Process**:
   - Follow the dev-item-address steps. Open a Draft PR and run a context-isolated review to Approve (≤ 14 rounds, D28). The review prompt names the audit of criterion 2 (no existing answer changes) and the D23 judgement.
   - Once CI is green, self squash-merge with the PR body's last line `Task: T-0574`. Post a §9 notice on #5 only if an ADR was written.
   - If the change exceeds the 10 non-test file cap, finish the entry, the table, the audit and the verification program. Propose the rest as a split in `Follow-ups` (DRIVER §5).
   - In `Result` record the language and reason (C for the programs per ADR-0194 decision 8; Python for the rest), the machine outputs, the real-GPU test results with tool versions, any HQ, and any runtime acceptance item (D22).
   - Remove the task directory with `rm -r` (D29).

## Out of Scope

- Generating CUDA programs from the contract table (ADR-0207 decision 4).
- The backend operations (slice 4, T-0575), the container and image (slice 5), and slice 6.
- A `.cu` attempt file, a CUDA given-code bundle and `instance_start` true (HQ-0104).
- bf16 at CUDA, `model_run`, GPU memory figures (HQ-0090), the coder's CUDA path (HQ-0088 ① (c)).
- Starting `claude` in any form (D16).

## Follow-ups

- For the slice that opens a `cuda_gpu` run (slice 6, after HQ-0104): `spec_tool` (`covers`, `task_contract`), `catalog_tool._compared`, `run_admission._entry` and `check_answer._ENTRIES` read no target, so they answer with the `c` entry. `targets.covers_at` (used by `start_instance`) and `run_tool._at_target` join `served_at` to a predicate asked without a target, so at `cuda_gpu` they follow the `c` entry's `covers` and flags. Those equal the `cuda` entry's today. That slice must pass the target to these readers (round-1 and round-2 review nits of PR #387).

## Result

PR #387, squash-merged as `c693af83` (PR body's last line `Task: T-0574`); branch deleted. Review: 2 rounds. Round 1 asked for changes: five existing tests failed in the full suite, the audit table did not cover the tests, and the Verification section held a placeholder; two nits. Round 2 approved with one nit, which went into the PR body and `Follow-ups` above. CI green on head `24080d47` (all six checks). Not BLOCKED; no HQ; no ADR (the reviewer agreed none was needed: ADR-0207 decisions 3 and 4 with ADR-0193 decisions 3 and 4 already decide selection by target, and the record of a CUDA kernel in a run stays HQ-0104). No §9 notice was posted.

**Machine check (criterion 1; read only, nothing installed or pulled).** WSL2 Ubuntu 22.04:
- `/usr/local/cuda-13.1/bin/nvcc --version` → `Cuda compilation tools, release 13.1, V13.1.115` (build `cuda_13.1.r13.1/compiler.37061995_0`).
- `nvidia-smi` → NVIDIA GeForce RTX 4070, NVIDIA-SMI 615.78.02, KMD 617.14, CUDA UMD 13.4, 12282 MiB.
- `gcc` 11.4.0 (Ubuntu 11.4.0-1ubuntu1~22.04.3); `clang` 14.0.0.

**Language.** C for the two programs (ADR-0194 decision 8: a GPU target's harness is C against the vendor runtime's C interface). Python for the contract module, the table, the targets and the path module, as their siblings are.

**What landed.**
- `hilclaw/gemm_cuda_contract.py`: `LANGUAGE` `cuda` and decision 4's `extern "C"` device-pointer prototype. Shapes, record and `covers` are `gemm_contract`'s objects.
- The table entry, appended eighth, `checked` and `timed`. Without a target, only the first entry per kind/dtype/layout is asked, so every no-target answer is unchanged. `entry` and `task_contract` take an optional `target`.
- Targets: `cpu_standin` serves the seven `c` keys, `virtual_npu` its six bf16 keys, and `cuda_gpu` exactly the `cuda` key. A `Target` refuses two keys of one kind/dtype/layout.
- `check_answer` takes only `c` entries; otherwise its import raised `RuntimeError`.
- `hilclaw/harness/cuda_verification_program.c` and `cuda_timing_driver.c`, with the command lines and reports of ADR-0017 and ADR-0009. CUDA errors exit 1 without a complete report.
- `hilclaw/harness/cuda_programs.py` names the two source paths.
- `.github/workflows/ci.yml`: the clang C gate skips `hilclaw/harness/cuda_*.c`, because the runner has no CUDA headers. Locally they compile warning-free under the gate's flags with `-isystem /usr/local/cuda-13.1/include`. With `-I`, the CUDA 13.1 `driver_types.h` itself fails `-Wpedantic` under C99.
- Fixtures: `tests/cuda_fixtures/gemm.cu` and `gemm_wrong.cu`.
- The PR body lists the reader audit and every existing-test edit.

**Size.** 8 non-test files (within the cap). About 700 changed non-test lines (671 insertions, 30 deletions), over the 600 recommendation, mostly the two C programs (~260 lines each), which mirror their host-memory siblings.

**Verification.**
- Full suite under `coverage run --branch` in a WSL2 clone of head `24080d47` (Python 3.12, CUDA `bin` on `PATH`): 42548 passed, 108 skipped, 0 failed. `hilclaw/` line+branch coverage 99 %; touched and new modules at 100 %.
- The real-GPU tests ran without skips on the RTX 4070 (nvcc 13.1 V13.1.115, gcc 11.4.0, driver 617.14):
  - pass at 8x8x8 and 5x33x7 (rtol = atol = 1e-4);
  - the wrong kernel judged `fail` with every element counted;
  - the timing report accepted by `run_timing` in both sample forms;
  - `CUDA_VISIBLE_DEVICES=""` ends either program with status 1, one stderr line naming `cudaErrorNoDevice`, and no complete report;
  - refused command lines exit 2 with empty stdout.
- ruff check and format are clean. No `claude` was started (D16), and no test run was made (D25).

**Runtime acceptance items (D22).** None new. The programs are checked by FR-19 ⑤ tests wherever `nvcc` and a GPU exist. ADR-0207's container items stay with slice 5.

**Storage.** WSL `/tmp/hilclaw-driver/T-0574/` (clone, coverage data, logs, sync script) and `%TMP%/hilclaw-driver/T-0574/` (PR body) were removed with `rm -r`. No images and no installs.
