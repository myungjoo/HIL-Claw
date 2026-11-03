---
id: T-0546
title: Do PLAN P3-13 — time a CUDA kernel on the machine's GPU within the ADR-0194 decision 4 boundary (launch and completion inside, transfers outside) and check the GPU-bound results (device out of memory, device fault, hang) with the real GPU
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [FR-19, OD-33, NFR-3, "PLAN P3-13"]
dependsOn: []
touchesFiles:
  - hilclaw/cuda_adapter.py
  - tests/test_cuda_adapter.py
  - tests/cuda_fixtures/
estimatedSize: {loc: 120, files: 1}
hq: []
---
## Why

**PLAN P3-13** ("GPU에서 돌려 보는 확인") asks to check, with the machine's GPU, the measurement boundary and the results bound to the GPU, following ADR-0194 decision 4 on whether a timing includes the completion of the GPU work. Its precondition holds: P3-9 is checked (T-0543, PR #359). T-0543's `## Result` read a usable GPU on this machine (`NVIDIA GeForce RTX 4070 (driver 617.14)`, on Windows and in WSL2) and states "이 머신에는 GPU가 있으므로 P3-13의 GPU 확인은 런타임 인수 항목으로 적지 않는다". So the P3-13 clause that lets the driver check the item without a task does not apply, and this task does the check. T-0543 built `tests/cuda_fixtures/scale.cu` but did not run it ("not run, P3-13"). **When this task is `DONE`, the driver checks PLAN P3-13.**

**One task (DRIVER §6 D20 ③).** Almost all of the work is a CUDA test fixture and tests, which the size recommendation does not count. The package change is at most a thin timing part in `hilclaw/cuda_adapter.py` (criterion 3), mirroring the one T-0545 added to `hilclaw/qnn_adapter.py`.

**Order (DRIVER §6 D27 ①).** On `main` `20cb12cb`:
- no `nightly-failure` issue is open and no PR is open;
- `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패` (RA-0056 is `미확인`, so D27 ④ asks nothing yet);
- no P2-15 preparation is pending;
- P3-3 waits on HQ-0090 and HQ-0091 (T-0533 landed the rest; ADR-0193 decision 8 checks P3-3 only once both are applied) and is treated as handled (D27 ⑦);
- P3-6, P3-11 and P3-12 are "오너 확정 필요";
- P3-7 to P3-10 are checked; P3-13 is the next selectable P3 item in listed order.

If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥).** This task asks none of these again and anticipates none of their answers:
- HQ-0093: CUDA's place in the order and the toolkit version to record (this task records no version in any record).
- HQ-0094: the runtime's acquisition and licences.
- **HQ-0095 ②: whether both points of CUDA on the local GPU are the same GPU run, or `board` only.** Its "[막히는 것]" names "P3-13의 지점 배정". So this task assigns no point: it adds no `Target` to `targets.TABLE`, no backend to any default table, and no `sim.run`/`board.run` binding, test-only or not. The boundary is checked at the adapter level (criteria 4 and 5).
- HQ-0096 ②: the oracle at a vendor target (no `correctness.check` here).
- **HQ-0097 (a): an absent or unusable device at the start of a run.** That is found by a probe holding no attempt code (ADR-0194 decision 3), T-0543's `device_probe`. This task does not read any status of the fixture's own process as "no device" and adds no kind.
- HQ-0090: no GPU memory figure and no new `unit` (ADR-0194 decision 4 "Unchanged").
- HQ-0088 and HQ-0092: what an attempt's code is at a vendor target. So there is no CUDA timing harness under `hilclaw/`: the timing program is a test fixture (ADR-0194 decision 8).

If the work shows a further owner-only part that none of these HQs covers, write the question in `## Result` in the §8 structure (Korean). Land the rest and return `DONE` (D27 ⑥). A missing toolchain or prerequisite follows criterion 1 instead.

**What exists.**
- `hilclaw/cuda_adapter.py` (T-0543): `assemble_build`/`build` (`nvcc` in the `clang_build.build` form; the adapter adds no flag), `assemble_run`/`run`, the `nvcc --version` probe and the `nvidia-smi` device query. Its build, run and probe-assemble parts delegate to `clang_adapter`.
- `hilclaw/qnn_adapter.py` (T-0545): `assemble_timing` and `measure`, the model for criterion 3. They put the fixture's own leading argument before `timing.driver_arguments(...)`, run it once through `local_run.run`, and hand the ended process to `vendor_adapter.measure`.
- `hilclaw/vendor_adapter.py`: `measure(answer, figure=None)` gives form (A) `(stdout, figure)` or form (B) `"time_limit"` / `"exit_status"` of `hilclaw/run_operation.py`.
- `hilclaw/harness/timing.py`: `driver_arguments`, `parse_report` and `judge_report`, the ADR-0009 report and its judging. `hilclaw/harness/timing_driver.c` is the reference C driver (argument parsing, the stopping rule `converged`, the report).
- `tests/qnn_fixtures/timing.c.in` (T-0545): a timing fixture of the same report form, against QNN's C interface.
- `tests/cuda_fixtures/scale.cu` and `broken.cu`, with the real-`nvcc` tests and their skip rule in `tests/test_cuda_adapter.py`.
- The toolchain, as T-0543 read it: WSL2 Ubuntu 22.04 with `/usr/local/cuda-13.1/bin/nvcc` (release 13.1, V13.1.115, not on the default `PATH`), host compiler g++ 11.4.0, `nvidia-smi` at `/usr/lib/wsl/lib`. On Windows, `nvcc` 12.3 exists but there is no MSVC, so it cannot build there. The executor reads the machine again before writing code (D29).

**D16.** Everything runs on the development machine: the real `nvcc` and the machine's own GPU, used by a test's process on the host (ADR-0194 decisions 2 and 8, and D29: "드라이버는 머신의 GPU로 실행·측정해도 되고"). There is no `claude`, no board and no API key, and no container is given a GPU.

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0546-<slug>`; the `Task: T-0546` trailer and the PR body's last line; size D30 and the file cap; tests D12; list assertions D21; storage D29 (temporary files and builds only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0546/`, removed at the end).
  - §3 "BLOCKED 사유".
  - §6 D27, and **the D29 toolchain paragraph** ("툴체인(D29 …)"). It covers: read the machine before writing code; NVIDIA tools from NVIDIA's official site are pre-allowed; any other tool is requested by an HQ; the driver may run and measure on the machine's GPU; record the command, version, URL and install path in `## Result` and the PR.
  - §8: the HQ structure and runtime acceptance items (D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `PROCESS/PLAN.md`: the P3-13 and P3-9 lines and the paragraph above P3-7.
- `PROCESS/tasks/T-0543-cuda-adapter.md`: whole, **including `## Result`** (the toolchain reading, how the real-`nvcc` tests find `nvcc` and skip, the fault-script set, the device query).
- `PROCESS/tasks/T-0545-qnn-emulator-timing-and-points.md`: `## Acceptance Criteria` 2 to 4 and `## Result` (the QNN timing fixture, its report on a duplicated standard output, `assemble_timing`/`measure`, the review findings: no test of the fixture's own argument parsing, which is test code).
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`:
  - **decision 4 in full** (binding text: launch inside, completion inside, the synchronisation waits, the host clock and no device event timers, transfers outside, warm-up, memory unchanged);
  - decisions 2, 3 (the "Run failure" row and the absent-device paragraph), 5 and 6 (fault-script contract, especially "What it may stand for");
  - decision 8 (CUDA C++ as test fixtures only; a GPU harness is C against the vendor runtime's C interface where one exists);
  - decision 10 V4 ② and V6;
  - Consequences.
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md` decisions 2, 4 and 6 (what a sample covers, the stopping rule, warm-up).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 3, 6, 7 and 8 (the timer, the untimed execution, the repeat loop, the report form).
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md` decision 4 (the operation's return forms).
- `ARCHITECTURE/Requirements.md` line 37: FR-19, especially ④ and ⑤.
- Code:
  - `hilclaw/cuda_adapter.py`, `hilclaw/qnn_adapter.py` (lines 100-175), `hilclaw/vendor_adapter.py` (module docstring, `interpret_run`, `measure`, `check_timeout`), and `hilclaw/harness/timing.py` (docstring, `driver_arguments`, `parse_report`, `judge_report`);
  - `hilclaw/harness/timing_driver.c`;
  - `hilclaw/run_parameters.py` (`TimingParameters`);
  - `hilclaw/local_run.py` (`run`, `RunResult`).
- Tests and fixtures: `tests/test_cuda_adapter.py` (the real-`nvcc` and `nvidia-smi` tests, the test `Target`, the fault scripts), `tests/test_qnn_adapter.py` (the timing tests of T-0545), `tests/qnn_fixtures/timing.c.in`, `tests/cuda_fixtures/scale.cu`.
- NVIDIA documentation the executor cites by version (read, not installed): the CUDA C++ Best Practices Guide, "Using CPU Timers"; the CUDA Runtime API reference for `cudaDeviceSynchronize`, `cudaMalloc`, `cudaGetLastError` and the error codes used.

## Acceptance Criteria

1. **Toolchain reading first (D29).** Before writing code, read the machine on Windows and in WSL2 without installing anything:
   - `nvcc` (versions, paths) and its host compiler;
   - `nvidia-smi` and the GPU;
   - `python -m hilclaw.toolchain_check`, with and without the CUDA `bin` directory on `PATH`.

   Record the reading in `## Result`. If `nvcc` is gone, reinstall it from NVIDIA's official site (pre-allowed) and record the command, version, URL and install path. If a prerequisite from outside NVIDIA's site is needed and not approved, land nothing and return `BLOCKED` (`new-external-dependency`) with an HQ (§8, Korean) naming the tool, its source and its licence. **If the machine has no usable GPU** (the device query does not report `present`), land nothing, write in `## Result` the GPU check as a runtime acceptance item (D22, Korean) and return `DONE`: the P3-13 line then lets the driver check the item. If the GPU is present but a CUDA program cannot run on it for a cause of the machine (for example the WSL2 driver), land nothing and return `BLOCKED` (`new-external-dependency` or the cause) with an HQ stating the cause and what is needed. A fault script never replaces an absent toolchain or GPU (ADR-0194 decision 6).

2. **A CUDA timing fixture (ADR-0194 decision 4).** Add `tests/cuda_fixtures/timing.cu`, a test fixture and never under `hilclaw/` (decision 8). It takes exactly the eight arguments of `hilclaw.harness.timing.driver_arguments`, unchanged, with `timing_driver.c`'s rules, and writes exactly the ADR-0009 decision 8 report on standard output so that `timing.judge_report` accepts it. Its stopping rule is ADR-0007 decision 4's, as `timing_driver.c` computes it. Apart from the kernel and its launch, it uses the CUDA runtime's C interface in C style.

   The boundary is decision 4:
   - **Outside the interval:** creating the device context; allocation (host and device); input generation; the copies to device memory before the first repeat and back after the last (decision 4 "Transfers"); one untimed launch and wait before the first repeat (decision 4 "Warm-up"); reading back and checking the output.
   - **Before each start reading:** a wait for the device to complete all earlier work (`cudaDeviceSynchronize` or an equivalent the executor names), outside the interval.
   - **Inside the interval:** the same fixed number of kernel launches per repeat, and the wait for their completion before the end reading (decision 4 "Synchronisation").
   - **Clock:** the host's monotonic clock (`clock_gettime(CLOCK_MONOTONIC)` on POSIX; on Windows only if it builds there), never device event timers. `resolution_ns` is that clock's resolution.
   - **Errors:** every CUDA call and every launch (through `cudaGetLastError` and the completion wait) is checked. Any error ends the program with a non-zero status and one line on standard error naming the CUDA error, and writes no `stop` line.

   The kernel and the work are the fixture's own. The arguments `m`, `k` and `n` set the work size; say how. It fixes no `-arch`, optimisation level or other flag in the source: those are the test `Target`'s `flags`, as T-0543's tests give them. If the HTP fixture's lesson applies (a library writing to standard output), write the report on a duplicate of the original standard output; otherwise say it is not needed.

   **The executor states, with sources and versions:** that a kernel launch returns before the work completes (asynchronous with respect to the host); which call waits for completion and why its return means the repeat's work is complete; what the harness cannot keep out of the interval (for example the launch overhead, which decision 4 puts inside, or the driver's scheduling), named as decision 4's rest.

3. **The adapter's timing part.** Add the least that fits to `hilclaw/cuda_adapter.py`, mirroring `qnn_adapter.assemble_timing` and `qnn_adapter.measure` without the backend-library argument: `assemble_timing(target, executable, parameters, *, timeout_s)` (the `RunCall` of `<executable> <driver_arguments(**parameters)>` through `assemble_run`) and `measure(target, executable, parameters, *, timeout_s)` (one `local_run.run` of that call, handed to `vendor_adapter.measure` with no figure). They read no clock or file, check every argument before anything starts, raise with `parameter` as `qnn_adapter` does, and report no memory figure (HQ-0090). If a different shape fits better, say why in `## Result`. Update the module docstring for the new parts. Foreseen D21 list-assertion edits: any test of `tests/test_cuda_adapter.py` that pins the module's public names or its pure assemble parts (as `test_assemble_parts_are_pure` was extended in T-0545). List every edited assertion in the PR body.

4. **The boundary checked with the real GPU (FR-19 ④ and ⑤).** In `tests/test_cuda_adapter.py`, real-GPU tests (skipped where `nvcc`, its host compiler or a usable GPU is absent, with the reason stated, as T-0543's tests skip) show:
   - the timing fixture builds with `cuda_adapter.build` (`go_on`);
   - run on the GPU through `cuda_adapter.measure`, it gives a form (A) answer;
   - `timing.judge_report` accepts that answer's report for both `sample_form` values: `resolution_ns` above 0, at least `N_MIN` positive `interval_ns` lines, and a `stop` line the replay agrees with;
   - **completion is inside the interval**: with a work size whose device duration is known to be well above the launch overhead (for example a kernel that runs until a device-side timer has advanced by a set amount, or a size whose duration the executor measures and states), every `interval_ns` is at least that duration less the clock's resolution. State in `## Result` how the duration is known and its source. A launch-only interval would not meet this bound;
   - `cuda_adapter.run` of `tests/cuda_fixtures/scale.cu`'s executable (built by T-0543's test) ends with status 0 on the GPU, closing T-0543's "not run, P3-13".

   No test of the fixture's own argument parsing is added (test code, CLAUDE.md test rule ⑤; T-0545 review round 1). Assemble and interpret tests with recorded inputs run without `nvcc` or a GPU.

5. **GPU-bound results checked with the real GPU (ADR-0194 decisions 3 and 6).** With a usable GPU these failures are easy to cause for real, so **no fault script stands for them** (decision 6 "What it may stand for"). Real-GPU tests show, through `cuda_adapter.measure` or `cuda_adapter.run`:
   - **device out of memory**: a fixture run asking for more device memory than the GPU has (size taken from the device, not hard-coded) ends with a non-zero status after `cudaMalloc` reports `cudaErrorMemoryAllocation`, and is broken `exit_status` (decision 3, "Run failure" row), with no `stop` line;
   - **a device fault**: a fixture kernel that makes an illegal memory access ends with a non-zero status after the completion wait reports the error, and is broken `exit_status`;
   - **a hang on the device**: a fixture kernel that does not end within the time limit ends as `time_limit` through `measure`, the process killed by `local_run.run`. If killing a process with a running kernel leaves the GPU unusable for the next test on this machine, state it and use a fault script for this case only (decision 6 lists a hang); say which way was taken.

   These cases may be modes of `timing.cu` selected by a fixture-only way (for example a separate small fixture file per failure, or a compile-time macro passed in the test `Target`'s `flags`), not by an environment variable read by the adapter. **No status of the fixture's own process is read as "no device"** (decision 3); the absent device stays with `device_probe` and HQ-0097.

   **No `Result`, ADR or runtime acceptance item cites an interval as a figure of a target** beyond this machine's GPU, and no figure is written to the data plane.

6. **Nothing else changes.**
   - `cpu_standin`, `virtual_npu`, `clang_adapter`, `qnn_adapter`, `vendor_adapter`, `toolchain_check`, `run_tool`, `targets.TABLE`, the backend tables, the harness modules and the data plane keep their behaviour.
   - Every existing test passes, with only D21 edits.
   - No `ARCHITECTURE/`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md` edit is made.
   - No container is given a GPU.

7. **Tests (D12).** Every public function of `hilclaw/cuda_adapter.py`, including the parts added, is covered.
   - Cover happy, error, branch and negative cases, including wrong argument types and values refused before anything starts.
   - Package line and function coverage stay at or above 80 %.
   - The full suite, `ruff check`, `ruff format --check` and the C gate command pass locally. CI passes on the PR (the real-GPU tests skip there).
   - The PR body states the `nvcc` version, the host compiler, the GPU and driver version, and the real-GPU test results (D29).

8. **`## Result`** states:
   - the language line;
   - the parts added to `cuda_adapter`, or why another shape;
   - the fixture's command line, its boundary and each criterion 2 statement with its source;
   - one real report from the GPU (first and last lines, the number of intervals), labelled as this machine's GPU figures, and the duration bound of criterion 4 with its numbers;
   - the three GPU-bound results of criterion 5, each with the observed status and standard-error line, and the way taken for the hang;
   - on which platform the real-GPU tests ran or skipped;
   - the toolchain reading, plus any install with its command, version, URL and path;
   - any runtime acceptance item for the driver to add (D22, Korean). Expected candidate: the same timing fixture and GPU-bound results on another C-7 machine with an NVIDIA GPU (native Linux), and the GPU in the runtime's container (ADR-0194 decision 8, the rest of ⑨) stated as not checked;
   - any new HQ (§8 structure, Korean), with what it holds up;
   - storage cleanup per DRIVER §5 D29.

## Out of Scope

- A CUDA `Target` in `targets.TABLE`, a backend in any default table, any `sim.run`/`board.run` binding of a GPU run, and `correctness.check` at a CUDA target (HQ-0093, HQ-0095 ②, HQ-0096 ②, HQ-0097).
- A CUDA timing harness under `hilclaw/harness/` or any runtime form of an attempt's code at a CUDA target (HQ-0088, HQ-0092).
- A GPU memory figure or a new `unit` (HQ-0090).
- A GPU in the runtime's container (ADR-0194 decision 8, the rest of ⑨), a device on another machine, and a CUDA tool image.
- Storage tools (P3-14).

## Follow-ups

## Result
