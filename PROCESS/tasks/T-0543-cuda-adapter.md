---
id: T-0543
title: Add the CUDA adapter of PLAN P3-9 (nvcc build and probe, nvidia-smi device query) on the ADR-0194 frame, checked with the machine's real nvcc and nvidia-smi
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [FR-19, OD-33, FR-10, "PLAN P3-9"]
dependsOn: []
touchesFiles:
  - hilclaw/cuda_adapter.py
  - hilclaw/toolchain_check.py
  - tests/test_cuda_adapter.py
  - tests/test_toolchain_check.py
  - tests/cuda_fixtures/
estimatedSize: {loc: 450, files: 2}
hq: []
---
## Why

**PLAN P3-9** ("CUDA 대상"): the executor reads the machine and uses the real `nvcc` it finds to check the build arguments and the version reading. Results for "no GPU" and "device out of memory" are tested with fault-injection scripts where they are hard to cause for real. `nvidia-smi` reads the presence and version of the GPU and driver. Running a kernel on the GPU is P3-13, not this task. The driver checks PLAN P3-9 when this task is `DONE`.

**Order (DRIVER §6 D27 ①).** On `main` `a820c1f0` no `nightly-failure` issue is open and no PR is open. `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패`, and no P2-15 preparation is pending. P3-3 waits on HQ-0090 and HQ-0091 and is treated as handled (D27 ⑦). P3-6 is "오너 확정 필요". P3-7 and P3-8 are checked (T-0540, T-0541, T-0542). So P3-9 is the next P3 item in listed order. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥; PLAN P3-9 "그 부분만 HQ로 돌리고 나머지를 진행한다").** The HQs below already ask the owner's parts, so this task does not ask them again and anticipates none of their answers:
- HQ-0093: CUDA's place in the order, and which toolkit version is recorded where (V2 ①, ②).
- HQ-0094: the runtime's acquisition and licences.
- HQ-0095 ②: which point a local GPU run is.
- HQ-0096 ②: the oracle at a vendor target.
- HQ-0097 (a): a new `device_unavailable` kind.

So this task adds:
- no `Target` entry in `targets.TABLE`;
- no backend, and no backend-table entry;
- no `sim.run`, `board.run` or `correctness.check` operation for CUDA;
- no new condition, kind, `step` value, data-plane member or file;
- no version written into a hw key's `toolchain` map or into any record (ADR-0194 decision 7, last bullet; OD-26).

If the work shows a further owner-only part that none of these HQs covers, write the question in `## Result` in the §8 structure (Korean). Land the rest and return `DONE` (D27 ⑥).

**What exists (T-0541, T-0542).**
- `hilclaw/vendor_adapter.py`: the frame. Its interpret parts give outcomes under existing conditions and kinds. It also has `Probe` with the states `PRESENT`, `ABSENT` and `UNREADABLE`.
- `hilclaw/clang_adapter.py`: the reference adapter, with assemble, execute and interpret per job, plus a probe pair.
- `hilclaw/toolchain_check.py`: the read-only report. Its `COMPONENTS` table holds `clang` only. `Component.host_only` is already there for a device query.

This task adds the CUDA adapter on that frame and registers its probes with the check. No probe command is written into `toolchain_check` ("No second list of commands", ADR-0194 decision 7).

**The machine (T-0541 and T-0542 Results; for orientation only).** The executor reads the machine again before writing code (D29).
- The Windows host has `nvcc` 12.3 and `nvidia-smi` (driver 617.14, an RTX 4070). Note that `nvcc` on Windows needs a host C++ compiler.
- WSL2 Ubuntu has CUDA 13.1 under `/usr/local/cuda-13.1`, with `nvcc` not on `PATH`, and `nvidia-smi -L` shows the GPU. The suite usually runs in WSL2.

**Size.** About 450 LOC in one new module plus a registration in `toolchain_check`, excluding tests. This is within the recommendation (DRIVER §5 D30), so there is one task.

**D16.** Everything runs on the development machine: the real `nvcc` and `nvidia-smi`, and fault scripts the tests write. No `claude`, no board, no API key. The GPU is read through `nvidia-smi` only. No kernel is launched on it (P3-13).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 and §5: branch `claude/T-0543-<slug>`; the `Task: T-0543` trailer and the PR body's last line; size D30 and the file cap; tests D12; list assertions D21; storage D29, with temporary files and build outputs only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0543/`.
  - §3 "BLOCKED 사유".
  - §6 D27 and **the D29 toolchain paragraph**: read the machine before writing code; NVIDIA tools from NVIDIA's official site are pre-allowed; record what was used in `## Result` and the PR.
  - §8: the HQ structure and runtime acceptance items (D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (one line with the language and the reason in the commit body and `## Result`), "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `PROCESS/PLAN.md`: lines for P3-9 and P3-13, and the paragraph above P3-7.
- `PROCESS/tasks/T-0541-vendor-adapter-frame.md` and `PROCESS/tasks/T-0542-toolchain-environment-check.md`: whole, **including `## Result`**. Their Results give the public names as landed, the probe-pair signatures, the fault-script style and the machine reading.
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`:
  - **decisions 2, 3, 6, 7 and 8 in full**. These are the binding text: the device absent at start is found by a probe that holds no attempt code, and until V6 (a) is answered that finding is an interpret outcome that no default-table operation returns; fault-script contract; CUDA C++ only as test fixtures.
  - decision 4 (for P3-13; not implemented here);
  - decision 10, V2 to V6;
  - Consequences, "A-13 reading".
- `ARCHITECTURE/Requirements.md`: FR-19, especially ③ (version trace) and ⑤ (tests: assemble and interpret run without the tool; an execution test is skipped where the vendor tool is absent; the PR states the tool version and the execution-test result).
- Code:
  - `hilclaw/vendor_adapter.py`, `hilclaw/clang_adapter.py` and `hilclaw/toolchain_check.py`, whole;
  - `hilclaw/clang_build.py` lines 1-60 and the `build` signature (the command form `<compiler> <flags> <sources> <trailing_flags> -o <output>`, which `nvcc` takes too);
  - `hilclaw/local_run.py` lines 1-110;
  - `hilclaw/targets.py` lines 57-112 (`Target`).
- Tests: `tests/test_clang_adapter.py` (fault-script and real-tool patterns, `posix_only`), and `tests/test_toolchain_check.py` lines 70-180 and around line 347 (`host_only`).

## Acceptance Criteria

1. **Toolchain reading first (D29).** Before writing code, the executor reads the machine without installing anything. This includes Windows and WSL2: `nvcc --version` (also `/usr/local/cuda-*/bin/nvcc`), `nvidia-smi`, and the host C++ compiler `nvcc` needs. The executor also runs `python -m hilclaw.toolchain_check`. Record the reading in `## Result`.
   - If no usable `nvcc` exists where the suite runs, obtain the CUDA toolkit from NVIDIA's official site, which is pre-allowed (D29). Install it outside the task directory. Record the command, the version, the URL and the install path in `## Result`.
   - If that is impossible (for example a login or licence step the owner has not done), land nothing. Return `BLOCKED` (reason `new-external-dependency`) with an HQ in the §8 structure that states what is needed and why.
   - A fault script never replaces an absent `nvcc` (ADR-0194 decision 6).
2. **Module `hilclaw/cuda_adapter.py`, build job.**
   - `assemble_build(target, sources, output, *, program=PROGRAM)` returns the arguments of `clang_build.build` with `compiler` set to `program`, the way `clang_adapter.assemble_build` does. It uses the target's `flags`, `trailing_flags`, `env` and `build_time_limit_s`. `PROGRAM` is the constant `"nvcc"`.
   - The adapter's own `build` (execute) calls `clang_build.build` with the assembled values and hands the result to `vendor_adapter.interpret_build`. The executor reuses `clang_adapter` helpers where they fit rather than copying them. If something in `clang_build` refuses an `nvcc` build (for example a source suffix), the executor names it in `## Result` and resolves it there without changing `clang_build`'s behaviour for `clang`.
   - The adapter adds no flag of its own: no `-arch`, `-gencode` or optimisation level. These are the target's values, and the values for a CUDA target rest on HQ-0093 ②.
3. **Run job.**
   - `assemble_run` and `run` follow `clang_adapter`'s: a host `local_run.run` command with the target's `env`, and a time limit capped by `process_time_limit_cap_s`.
   - A run that ends non-zero gives broken `exit_status`. This includes a CUDA program that reports a device out of memory by its status (ADR-0194 decision 3, the "Run failure" row).
   - This task runs no built CUDA executable on the GPU (P3-13).
4. **nvcc probe pair.**
   - `assemble_probe(*, timeout_s, program=PROGRAM)` assembles `<program> --version`.
   - `interpret_probe(answer, program)` reads the answer on the host, and `interpret_container_probe(answer)` reads it in a container. Both use `clang_adapter`'s conventions for `absent`, `unreadable` and the `None` that is re-raised.
   - The version is the line `nvcc --version` uses for the release, for example `Cuda compilation tools, release 12.3, V12.3.107`. It is not the first line, which is a banner. The executor names the exact reading and its source (the real output on the machine) in `## Result`.
   - A `probe(...)` function joins the pair.
5. **Device query (`nvidia-smi`), host only.**
   - A probe pair assembles one `nvidia-smi` query whose output is machine-readable, for example `--query-gpu=name,driver_version --format=csv,noheader`. The executor picks the exact arguments from the real tool and NVIDIA's documentation and cites them.
   - The pair interprets the answer into exactly one of four outcomes: a usable device, with a version text naming the driver version and the device name or names; **no device** (the tool runs but finds no GPU or cannot talk to the driver); the tool absent (not found or cannot start); or unreadable (anything else, a time limit, or output with no device line).
   - "No device" is a value of this module, not a new `check_failure` kind or condition (HQ-0097 (a)). In the `toolchain_check` report it is shown with the existing `Probe` states. The executor chooses how and states it in `## Result`. The report is outside the data plane (ADR-0194 decision 7), but its existing three states and its shape stay unless the executor shows that a change is needed.
   - This is the probe ADR-0194 decision 3 places before an attempt's process: it holds no attempt code. Nothing reads the attempt's own status or output as "no device".
6. **Registration in `toolchain_check`.** `COMPONENTS` gains `nvcc` (read on the host and in images) and the device query (`host_only=True`). Both point at `cuda_adapter`'s probe parts. No command text is written into `toolchain_check`.
   - The command's exit-status table, report shape and `clang` entry stay as T-0542 landed them.
   - Foreseen D21 list-assertion edits, to be listed in the PR body:
     - `tests/test_toolchain_check.py` line ~158: `assert list(COMPONENTS) == ["clang"]` and the `COMPONENTS["clang"]` comparison.
     - Line ~172: the whole-report equality of `test_real_clang_on_the_host_is_present_with_the_compiler_version`. Narrow it to the `clang` entry, or add the new keys. Do not weaken what it checks of `clang`.
   - Any other edited assertion must be within D21 and listed too.
7. **Checked with the real tools (FR-19 ⑤).** Execution tests run the real `nvcc` and are skipped, with a stated reason, where it is absent. They find it with `shutil.which("nvcc")`; the executor runs them with the CUDA `bin` directory on `PATH` where needed. They show that the real `nvcc`:
   - builds a small CUDA C++ fixture into an executable (go on);
   - fails to compile a broken fixture (broken `build_exit_status`);
   - is reported present by the probe with the version line.

   A test-only `Target` is built in the tests, never added to `targets.TABLE`.

   An execution test of the device query runs the real `nvidia-smi` where present, skipped where absent, and reports a usable device on this machine.

   The fixtures are CUDA C++ sources under `tests/` (for example `tests/cuda_fixtures/`), as ADR-0194 decision 8 admits. They are never under `hilclaw/`. They need no harness: the GPU timing harness is P3-13's.

   Clang tests keep their rule: clang's absence is still a CI failure, and no new skip is added for it.
8. **Fault-injection scripts (ADR-0194 decision 6).** These are written by the tests, passed only through the `program` argument, POSIX sh or Python run by the test's interpreter, and they read no clock, random source or counter. Each test names the documented behaviour it stands for, with its source. They stand only for:
   - `nvidia-smi` with no GPU or no driver (the status and text NVIDIA documents or the real tool prints in that case) → "no device";
   - `nvidia-smi` that hangs → unreadable;
   - a CUDA program that reports a device out of memory by a non-zero status and a CUDA error text → broken `exit_status` through the run job;
   - `nvcc` that hangs, crashes or exits 0 with no artefact, as for clang in T-0541 (`build_time_limit`, `build_exit_status`, `build_output_missing`).

   No script stands for a success, a compile failure, a version string or an accepted argument. No `Result`, ADR or runtime acceptance item cites a script as a fact of the tool.
9. **Nothing else changes.**
   - `cpu_standin`, `virtual_npu`, `clang_adapter`, `vendor_adapter`, `targets.TABLE`, the backend tables, the tools and the data plane keep their behaviour.
   - Every existing test passes, with only the D21 edits of criterion 6.
   - No container is given a GPU (the rest of OD-33 ⑨).
   - No `ARCHITECTURE/`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md` edit is made.
10. **Tests (D12).** `tests/test_cuda_adapter.py` covers every public function of `hilclaw/cuda_adapter.py`, and the touched `toolchain_check` paths are covered too.
    - Cover happy, error, branch and negative cases. Negative cases include wrong argument types and values, refused before anything starts, in `clang_adapter`'s style with `parameter`.
    - Assemble and interpret tests use recorded or literal inputs and run without `nvcc` or a GPU (FR-19 ⑤).
    - Package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally.
    - The PR body states the `nvcc` and `nvidia-smi` versions used and the execution-test results (D29).
11. **`## Result`** states:
    - the language line;
    - the public names of `cuda_adapter` and the probe signatures;
    - the nvcc version reading, the `nvidia-smi` arguments and how "no device" shows in the report;
    - the fault scripts and what each stands for;
    - the toolchain reading, plus any download or install with its command, version, URL and path;
    - the `python -m hilclaw.toolchain_check` output on the machine after the change;
    - any runtime acceptance item for the driver to register (D22), in Korean. Expected: what the check reads for `nvcc` and the device query on each C-7 machine kind. If the machine had no GPU, also the GPU check that PLAN P3-13 names.
    - any new HQ (§8 structure, Korean), with what it holds up.

## Out of Scope

- Running a built CUDA executable on the GPU, the GPU timing harness and the measure boundary of ADR-0194 decision 4 (P3-13).
- A CUDA `Target` entry, a backend, its default-table entry, point assignment and `correctness.check` (HQ-0093, HQ-0095, HQ-0096, HQ-0097).
- Writing the toolkit version into a hw key or a data-plane record (HQ-0093 ②, OD-26).
- Giving a container a GPU, and a CUDA tool image. If an image is made for checks anyway, D29's storage and tagging rules apply and its tag goes in `## Result`.
- Qualcomm (P3-10), and moving `cpu_standin` or `virtual_npu` onto the adapters.

## Follow-ups

## Result
