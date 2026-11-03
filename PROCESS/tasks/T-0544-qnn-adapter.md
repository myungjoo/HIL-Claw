---
id: T-0544
title: Add the Qualcomm QNN adapter of PLAN P3-10 (build, HTP-emulator run and SDK version probe) on the ADR-0194 frame, checked with a real QNN SDK on the machine
phase: P3
status: DONE
commitMode: code
coversReq: [FR-19, OD-33, FR-10, NFR-3, "PLAN P3-10"]
dependsOn: []
touchesFiles:
  - hilclaw/qnn_adapter.py
  - hilclaw/toolchain_check.py
  - tests/test_qnn_adapter.py
  - tests/test_toolchain_check.py
  - tests/qnn_fixtures/
estimatedSize: {loc: 450, files: 2}
hq: []
---
## Why

**PLAN P3-10** ("Qualcomm 대상"): the executor reads the machine and uses the real QNN toolchain it finds, emulator included, to check the same things P3-9 checked for CUDA: the build arguments, the version reading, and the outcomes of the ADR-0194 decision 3 table, with fault-injection scripts only for failures that are hard to cause for real. If QNN is absent, the executor obtains it from Qualcomm's official site (pre-allowed, DRIVER §6 D29). If it cannot, the D29 path applies (land nothing, `BLOCKED`, HQ).

**This task is the first part of P3-10.** P3-10 also asks for two further checks: the measurement boundary checked at the emulator point (ADR-0194 decision 4), and that results keep two points of one target apart (ADR-0194 decision 5). Both need a timing harness and a test-built backend on top of the build and run forms this task chooses. So they come in a later task, which the planner writes once this one has landed. **The driver does not check PLAN P3-10 when this task is `DONE`.**

**Order (DRIVER §6 D27 ①).** On `main` `10f5a0de`:
- no `nightly-failure` issue is open and no PR is open;
- `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패`;
- no P2-15 preparation is pending;
- P3-3 waits on HQ-0090 and HQ-0091 and is treated as handled (D27 ⑦);
- P3-6 is "오너 확정 필요";
- P3-7, P3-8 and P3-9 are checked (T-0540 to T-0543).

So P3-10 is the next P3 item in listed order. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥; PLAN P3-10 "그 답이나 … D23에 걸리는 부분은 HQ로 돌리고 나머지를 진행한다").** The HQs below already ask the owner's parts. This task does not ask them again and anticipates none of their answers:
- HQ-0093: Qualcomm's place in the order, the SoC or Hexagon generation, the QNN version to use (② — the task records the version it used, it does not fix one), and HexKL (③).
- HQ-0094: the runtime's acquisition and licences.
- HQ-0095 ① and ③: which execution is which point, and how a Qualcomm device is reached.
- HQ-0096 ②: the oracle at a vendor target.
- HQ-0097 (a): a new `device_unavailable` kind.

So this task adds:
- no `Target` entry in `targets.TABLE`;
- no backend and no backend-table entry;
- no `sim.run`, `board.run` or `correctness.check` operation for Qualcomm;
- no new condition, kind, `step` value, data-plane member or file;
- no version written into a hw key's `toolchain` map or any record (ADR-0194 decision 7, last bullet; OD-26);
- no HexKL value anywhere (PLAN P3-10; HQ-0093 ③);
- no task out of PLAN's Qualcomm reservation under "P3 밖".

If the work shows a further owner-only part that none of these HQs covers, write the question in `## Result` in the §8 structure (Korean). Land the rest and return `DONE` (D27 ⑥). The exception is a missing toolchain or prerequisite: that follows criterion 1.

**What exists (T-0541 to T-0543).**
- `hilclaw/vendor_adapter.py`: the frame. Its interpret parts give outcomes under existing conditions and kinds. It also has `Probe` with the states `PRESENT`, `ABSENT` and `UNREADABLE`.
- `hilclaw/clang_adapter.py`: the reference adapter.
- `hilclaw/cuda_adapter.py`: the first vendor adapter. Its build, run and probe-assemble parts delegate to `clang_adapter`, and it has its own version reading and a host-only device query.
- `hilclaw/toolchain_check.py`: the read-only report, whose `COMPONENTS` holds `clang`, `nvcc` and `nvidia-smi`.

This task adds the QNN adapter on that frame, the same way, and registers its probe with the check.

**The machine (T-0540 to T-0543 Results; for orientation only).** No QNN tool was found on Windows or WSL2. WSL2 Ubuntu 22.04 has clang 14.0.0 and g++ 11.4.0, and the suite runs there. The ExecuTorch Qualcomm page (ADR-0194 decision 9) names WSL with Ubuntu 22.04 as a verified host. It also names QNN 2.37.0 at `softwarecenter.qualcomm.com/api/download/software/sdks/Qualcomm_AI_Runtime_Community/All/2.37.0.250724/v2.37.0.250724.zip` and says a Linux x64 host can run inference with the QNN HTP emulator. The executor reads the machine again before writing code (D29).

**Size.** About 450 LOC in one new module plus a registration in `toolchain_check`, excluding tests and fixtures. This is within the recommendation (DRIVER §5 D30). It is one task because the adapter's build, run and probe are one feature (D20).

**D16.** Everything runs on the development machine: the real QNN SDK with its x86_64 HTP emulator, and fault scripts written by the tests. No `claude`, no Qualcomm board, no API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3-5 and §5: branch `claude/T-0544-<slug>`; the `Task: T-0544` trailer and the PR body's last line; size D30 and the file cap; tests D12; list assertions D21; **storage D29** — temporary files, the downloaded SDK archive and build outputs only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0544/`, the install outside it, and the archive removed after install.
  - §3 "BLOCKED 사유".
  - §6 D27 and **the D29 toolchain paragraph**: read the machine before writing code; Qualcomm tools (QNN SDK included) from Qualcomm's official site are pre-allowed; record the command, version, URL and install path in `## Result` and the PR; login or terms are the owner's first time per vendor site, and are never automated by entering credentials.
  - §8: the HQ structure and runtime acceptance items (D22).
- `CLAUDE.md`: A-13 code mode (a new external dependency is a BLOCKED reason), "테스트 규칙", "도구 계층 언어 정책" (one line with the language and the reason in the commit body and `## Result`), "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `PROCESS/PLAN.md`: the lines for P3-10 and P3-13, the paragraph above P3-7, and the Qualcomm reservation under "P3 밖".
- `PROCESS/tasks/T-0543-cuda-adapter.md`: whole, **including `## Result`**. It is the pattern for this task: delegation to `clang_adapter`, the version-line reading, fault scripts, real-tool tests with skips, registration and D21 edits.
- `PROCESS/tasks/T-0541-vendor-adapter-frame.md` and `PROCESS/tasks/T-0542-toolchain-environment-check.md`: `## Result` only (public names as landed, probe-pair signatures).
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`:
  - **decisions 2, 3, 6, 7 and 8 in full** (binding text). Key points:
    - a vendor runner or emulator that is missing is S10 `executable_unstartable` on the host, found before any process;
    - no adapter starts a process of its own;
    - the fault-script contract;
    - C++ is admitted only as test fixtures;
    - a harness is C against the vendor runtime's C interface where one exists.
  - decision 9 (the QNN rows) and decision 10, V2 to V6.
  - decisions 4 and 5 for orientation only: they are the follow-up task's.
  - Consequences, "A-13 reading".
- `ARCHITECTURE/Requirements.md` line 37: FR-19, especially ③ (version trace), ④ (an emulator's figure is never a device's) and ⑤ (assemble and interpret are tested without the tool; execution tests are skipped where the vendor tool is absent; the PR states the tool version and the execution-test result).
- `ARCHITECTURE/OpenDecisionProposals.md` § OD-33 (from line 635): the sub-questions, to see what is the owner's.
- Code:
  - `hilclaw/cuda_adapter.py`, `hilclaw/vendor_adapter.py`, `hilclaw/clang_adapter.py` and `hilclaw/toolchain_check.py`, whole;
  - `hilclaw/clang_build.py` lines 1-60 and the `build` signature;
  - `hilclaw/local_run.py` lines 1-110;
  - `hilclaw/targets.py` lines 57-112 (`Target`).
- Tests: `tests/test_cuda_adapter.py` (fault-script and real-tool patterns, skips), and `tests/test_toolchain_check.py` lines 149-200 and 560-608.

## Acceptance Criteria

1. **Toolchain reading first (D29).** Before writing code, the executor reads the machine without installing anything, on Windows and in WSL2:
   - any QNN or QAIRT SDK, for example a `QNN_SDK_ROOT` or `QAIRT_SDK_ROOT` directory, `qnn-net-run`, or `libQnnHtp.so` under `lib/x86_64-linux-clang`;
   - the host compiler and libraries the SDK's documentation requires for x86_64 Linux;
   - `python -m hilclaw.toolchain_check`.

   Record the reading in `## Result`. Then:
   - **If no usable QNN SDK exists where the suite runs**, download the SDK from Qualcomm's official site (pre-allowed, D29). Use the version ADR-0194 decision 9 cites (2.37.0.250724), unless that URL no longer serves it; in that case take the version the site offers and say why. Keep the archive in the task directory and install outside it. Remove the archive after install. Record the command, the version, the URL, the install path and the path of the SDK's licence file (for example `LICENSE.pdf`) in `## Result`. Do not commit or push the SDK or any part of it.
   - **If the download needs a login or a terms acceptance the owner has not done**, land nothing. Return `BLOCKED` (reason `new-external-dependency`) with an HQ in the §8 structure (Korean) that names the site and what the owner has to do once (D29).
   - **If the SDK needs a prerequisite from somewhere other than Qualcomm's site** (an apt package such as `libc++-dev`, or a pip package such as a converter's `onnx` or `torch`): first choose a build and run form that does not need it (criterion 2). If every documented form needs it, land nothing. Return `BLOCKED` (`new-external-dependency`) with an HQ that requests that tool with its source and licence (D29: such tools are requested, not pre-allowed).
   - A fault script never replaces an absent SDK or emulator (ADR-0194 decision 6).
2. **Choose and state the build and run forms.** From the SDK's own documentation and files, choose:
   - how one small kernel fixture is built for the x86_64 HTP emulator;
   - which program the run starts.

   **Prefer** a form in which the built artefact is a C program against QNN's C interface (headers under the SDK's `include/QNN`) that loads the HTP backend library and runs a one-op graph. This is ADR-0194 decision 8's harness language, and it keeps the follow-up timing harness in C. Its build then has the `clang_build.build` command form.

   **Otherwise**, use the SDK's documented runner (for example a model library run by `qnn-net-run --backend <libQnnHtp.so>`) with a hand-written C or C++ model fixture. Do not use a converter that needs a new Python package.

   State the chosen forms, the alternatives considered and their sources (SDK documentation pages or files, with the SDK version) in `## Result` and the PR body.

   The forms are this adapter's implementation, not a record:
   - no `ARCHITECTURE/` edit;
   - no HTP architecture, SoC or optimisation value is fixed in `hilclaw/`;
   - values the run needs (for example a backend library path, `LD_LIBRARY_PATH`, an HTP architecture option) come from the target's `flags`, `trailing_flags` and `env` or from the adapter's arguments. A test-only `Target` built in the tests carries them (HQ-0093 ②).
3. **Module `hilclaw/qnn_adapter.py`, with the parts of `cuda_adapter`.** Use the same signatures and delegation where they fit:
   - `assemble_build`, `build`, `assemble_run`, `run`, `assemble_probe`, `interpret_probe`, `interpret_container_probe` and `probe`;
   - the program constants as module constants that each part takes as `program=` (ADR-0194 decision 6);
   - reuse `clang_adapter` and `vendor_adapter` helpers rather than copying them. If `clang_build` or `local_run` refuses something the chosen form needs, name it in `## Result` and resolve it without changing their behaviour for `clang` or `nvcc`.

   **Outcomes come only from the ADR-0194 decision 3 table:**

   | Situation | Outcome |
   |---|---|
   | Build success | go on |
   | Compile or link failure | broken `build_exit_status` |
   | Build hang | broken `build_time_limit` |
   | Status 0 with no artefact | tool failure `build_output_missing` |
   | Build tool not found | tool failure `compiler_unavailable` |
   | Run ends non-zero or by a signal (this includes an emulator's reported allocation failure) | broken `exit_status` |
   | Run hang | broken `time_limit` |
   | The run's program (runner or emulator) not found or not startable on the host, before any process | tool failure `executable_unstartable` |

   - If the chosen form loads the emulator as a library from a program the attempt built, a missing library is **not** read from that process's status or output (ADR-0194 decision 3; ADR-0110 decision 3). It is reported only by the probe and the environment check (criterion 4).
   - No new condition or kind.
4. **SDK version probe.** One probe pair reads the SDK's version from the real SDK. Examples: a tool's version option, or a version file the SDK ships, read by a program started through the existing executors. No adapter reads files itself outside its interpret part's handed paths, and no adapter starts a process of its own.
   - Choose the reading from the real SDK, and cite it with the exact real output in `## Result`.
   - The rules for `absent`, `unreadable`, the container reading and the re-raised `None` follow `clang_adapter`'s and `cuda_adapter`'s conventions.
   - If the HTP emulator's backend library is a separate component that can be missing while the version tool is present, the executor may add a second probe for it, but only if it can be read through an existing executor without attempt code. State the choice.
   - No probe of a Qualcomm device (no device on this machine; access is HQ-0095 ③).
5. **Registration in `toolchain_check`.** `COMPONENTS` gains the QNN component or components. Each is read on the host and in images unless it is a device query. Each points at `qnn_adapter`'s probe parts, and no command text is written into `toolchain_check`.
   - The exit-status table, the report shape and the existing entries stay.
   - Foreseen D21 list-assertion edit, to be listed in the PR body: `tests/test_toolchain_check.py` line 160, `assert list(COMPONENTS) == ["clang", "nvcc", "nvidia-smi"]`. Line 190 already compares with `list(COMPONENTS)`. Any other edited assertion must be within D21 and listed too.
6. **Checked with the real SDK (FR-19 ⑤).** Execution tests use the real SDK. They are skipped, with a stated reason, where it is absent. How they find the SDK (for example `shutil.which` on a program with the SDK's `bin` directory on `PATH`) is stated in `## Result`. The tests show:
   - a small fixture builds (go on);
   - a broken fixture fails to compile (broken `build_exit_status`);
   - the built fixture runs on the x86_64 HTP emulator and ends with status 0 (go on through the run job);
   - the probe reports `present` with the SDK version.

   Fixtures live under `tests/qnn_fixtures/`, as C (or C++ only if the chosen form needs it, ADR-0194 decision 8). They are never under `hilclaw/` and are not timing harnesses (the follow-up task's). A test-only `Target` is built in the tests, never added to `targets.TABLE`. Clang and CUDA tests keep their rules; no new skip is added for clang.
7. **Fault-injection scripts (ADR-0194 decision 6).** They are:
   - written by the tests and passed only through a `program` argument, or as the run's executable;
   - POSIX sh or Python run by the test's interpreter;
   - free of any clock, random source or counter reads.

   Each test names the documented behaviour it stands for, with its source. They stand only for:
   - the build tool hanging, crashing with no diagnostic, or exiting 0 with no artefact;
   - the runner or emulator hanging;
   - an emulator run that reports an allocation failure by a non-zero status → broken `exit_status`;
   - the version tool hanging.

   No script stands for a success, a compile failure, a version string or an accepted argument. No `Result`, ADR or runtime acceptance item cites a script as a fact of the tool. A missing program is tested with a real missing path, not a script.
8. **Nothing else changes.**
   - `cpu_standin`, `virtual_npu`, `clang_adapter`, `cuda_adapter`, `vendor_adapter`, `targets.TABLE`, the backend tables, the tools and the data plane keep their behaviour.
   - Every existing test passes, with only the D21 edits of criterion 5.
   - No container is given a device.
   - No `ARCHITECTURE/`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md` edit is made.
9. **Tests (D12).** `tests/test_qnn_adapter.py` covers every public function of `hilclaw/qnn_adapter.py`, and the touched `toolchain_check` paths are covered too.
   - Cover happy, error, branch and negative cases. Negative cases include wrong argument types and values, refused before anything starts, with `parameter`, in `clang_adapter`'s style.
   - Assemble and interpret tests use recorded or literal inputs and run without the SDK (FR-19 ⑤).
   - Package line and function coverage stay at or above 80 %. The full suite and `ruff check` and `ruff format --check` pass locally.
   - The PR body states the SDK version used, the host compiler used and the execution-test results (D29).
10. **`## Result`** states:
    - the language line;
    - the public names of `qnn_adapter` and the probe signatures;
    - the chosen build and run forms with their sources (criterion 2);
    - the version reading with its real output;
    - the fault scripts and what each stands for;
    - the toolchain reading, plus any download or install with its command, version, URL, install path and licence-file path;
    - the `python -m hilclaw.toolchain_check` output on the machine after the change;
    - any runtime acceptance item for the driver to register (D22), in Korean. Expected: what the check reads for QNN on each C-7 machine kind, and that a Qualcomm device point is unchecked on this machine (no device; HQ-0095 ③).
    - any new HQ (§8 structure, Korean), with what it holds up;
    - storage cleanup per DRIVER §5 D29, with the remaining paths if cleanup failed.

## Out of Scope

- The measurement boundary at the emulator point, a QNN timing harness, and the separation of two points of one target (ADR-0194 decisions 4 and 5). These are the next P3-10 task, written after this one lands.
- A Qualcomm `Target` entry, a backend, its default-table entry, point assignment and `correctness.check` (HQ-0093, HQ-0095, HQ-0096, HQ-0097).
- Writing the SDK version into a hw key or a data-plane record (HQ-0093 ②, OD-26).
- The Hexagon SDK, `hexagon-sim`, HTP custom op packages built for a Hexagon target, HexKL, AIMET, and any converter that needs a new Python package. If the chosen form turns out to need one of these, use criterion 1's path.
- A Qualcomm device, `adb`, and a QNN tool image. If an image is made for checks anyway, D29's storage and tagging rules apply and its tag goes in `## Result`.
- GPU runs (P3-13) and storage tools (P3-14).

## Follow-ups

## Result

- **Landing**: PR #360 (squash-merge), review 2 rounds (round 1 Request changes: the CI C gate failed on the `*.c` fixtures — Must-fix, fixed by the `*.c.in` rename; the empty `## Result` — Should-fix, a draft put in the PR body; two nits — the MinGW gcc compiler of the real run and a present-but-unusable Linux SDK failing rather than skipping, both recorded below; round 2 Approve with one nit, this section, written here by the executor for the driver to commit). Squash commit `2298c8de`. After round 1 the fixtures became `tests/qnn_fixtures/*.c.in`: CI's C gate builds every tracked `*.c` with `clang -std=c99 -Wpedantic -Werror` and no SDK headers (`broken.c` fails there on purpose, and the SDK headers use C11 anonymous unions); the real-SDK tests copy them to `*.c` in `tmp_path`.
- **Order check (D27 ①)**: unchanged when the task ran (main `35f8e5d4`): no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`; P3-7 to P3-9 checked, P3-10 next. No branch or PR for T-0544 existed before (resume rule).
- **Language**: Python — the adapter wraps the Python adapter parts and executors (`clang_adapter`, `vendor_adapter`, `local_run`) and returns their types. The fixtures under `tests/qnn_fixtures/` are C (ADR-0194 decision 8).
- **Public names of `hilclaw/qnn_adapter.py`**: `BUILD_PROGRAM` (`"clang"`), `VERSION_PROGRAM` (`"qnn-net-run"`), `assemble_build(target, sources, output, *, program=BUILD_PROGRAM)`, `build(target, sources, output, *, program=BUILD_PROGRAM)`, `assemble_run(target, executable, arguments=(), *, timeout_s)`, `run(target, executable, arguments=(), *, timeout_s)`, `assemble_probe(*, timeout_s, program=VERSION_PROGRAM)`, `interpret_probe(answer, program)`, `interpret_container_probe(answer)`, `probe(*, timeout_s, program=VERSION_PROGRAM)`. Build, run and probe-assemble delegate to the `clang_adapter` functions of the same name. The two interpret parts delegate to `clang_adapter`'s and replace only the status-0 reading. `clang_build` and `local_run` refused nothing the form needs and are unchanged. In `toolchain_check.COMPONENTS`, `"qnn-net-run"` maps to `Component(qnn_adapter.assemble_probe, qnn_adapter.interpret_probe, qnn_adapter.interpret_container_probe, qnn_adapter.VERSION_PROGRAM)` and is read on the host and in images.
- **Build and run forms (criterion 2)**: the chosen form is the preferred one: a C program against QNN's C interface (`include/QNN`). It loads the HTP backend library by path (`dlopen`, or `LoadLibraryA` on Windows), takes `QnnInterface_getProviders`, and creates, finalizes and executes a one-op graph (`ElementWiseAdd` of two `UFIXED_POINT_8` tensors of 4, scale 1, offset 0). It prints `sum 11 22 33 44` and exits 0; otherwise it names the failed QNN call and exits 1 (usage error 2).
  - Build: the `clang_build.build` form with `BUILD_PROGRAM`. The include directory and `-ldl` are the target's `flags`/`trailing_flags`.
  - Run: the built program, with the backend library path as the run's argument and the target's `env` (`LD_LIBRARY_PATH`, or `PATH` on Windows).
  - Alternative considered: `qnn-net-run --backend <libQnnHtp.so> --model <model library>` with a hand-written model library. Not chosen: the C harness is decision 8's language, keeps the follow-up timing harness in C and needs no model-library step.
  - Sources (QNN SDK 2.37.0.250724): `docs/QNN/general/backend.html` (the HTP x86_64-linux backend "serves as an functional simulator for the hardware accelerator"; the backend loads `QnnHtpPrepare` for `addNode` and `finalize`); `docs/QNN/general/setup/linux_setup.html` and `windows_setup.html` ("The x86_64 targets are built using clang-14"); the headers `QnnInterface.h`, `QnnGraph.h`, `QnnTensor.h`, `QnnTypes.h` and `QnnOpDef.h`. The Windows x64 host emulator path comes from ExecuTorch's "Qualcomm AI Engine Backend" page (ADR-0194 decision 9).
  - No HTP architecture, SoC or optimisation value is fixed in `hilclaw/`.
- **Version reading**: `qnn-net-run --version`. The version is the first line, of stdout and then of stderr, that begins with `QNN SDK v`, stripped.
  - Real output (Windows x64, `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724\bin\x86_64-windows-msvc\qnn-net-run.exe --version`, status 0): stdout `qnn-net-run pid:108592`, stderr `QNN SDK v2.37.0.250724175447_124859`.
  - Documented in `docs/QNN/general/tools.html` (`--version  Print the QNN SDK version.`).
  - Status 0 without that line is `unreadable`. Absent, time limit, non-zero status, 125/126/127 in an image and the re-raised `None` follow `clang_adapter`'s conventions.
  - No second probe of the backend library. `qnn-net-run --backend <lib> --version` prints the version without loading the backend (checked with a missing `nosuch.dll`: status 0, same line), and no SDK tool loads the library without a model, so it cannot be read without attempt code.
  - A missing emulator library is the built program's failure (status 1, broken `exit_status`) and is not read specially (ADR-0194 decision 3).
- **Fault scripts**: Python, run by the test's interpreter from `tmp_path` and passed only as `program` or as the run's executable; none reads a clock, random source or counter.
  - `HANG`: a compiler that never ends → `build_time_limit`; a run on the HTP emulator that never ends → `time_limit`; a `qnn-net-run --version` that never ends → `unreadable`.
  - `SILENT_STATUS` (`sys.exit(70)`): a compiler crash with no diagnostic → `build_exit_status`.
  - `SIGNAL` (POSIX only): a compiler killed by SIGSEGV → `build_exit_status`.
  - `NO_ARTEFACT`: a compiler that exits 0 with no artefact → `build_output_missing`.
  - `ALLOCATION_FAILURE` (writes `QnnGraph_create failed: 1002`, exits 1): a QNN program whose `QnnGraph_create` returns `QNN_GRAPH_ERROR_MEM_ALLOC` ("create failed due to memory/resource allocation", `include/QNN/QnnGraph.h` and `QnnCommon.h`) and reports it by its status → broken `exit_status`.

  Missing programs are tested with real missing paths (`compiler_unavailable`, `executable_unstartable`, probe `absent`). No fact of a tool rests on these scripts.
- **Toolchain reading (D29)**, before writing code:
  - Windows: no `QNN_SDK_ROOT` or `QAIRT_SDK_ROOT`, no `qnn-net-run`, no `C:\Qualcomm`; MinGW-w64 gcc 16.2.0 (WinLibs); no clang, no MSVC; `vcruntime140.dll`, `vcruntime140_1.dll` and `msvcp140.dll` in System32.
  - WSL2 Ubuntu 22.04.5: no QNN SDK, no `libQnnHtp.so`; clang 14.0.0-1ubuntu1.1 and g++ 11.4.0; no libc++ (`libc++1-14` and `libc++abi1-14` not installed).
  - `python -m hilclaw.toolchain_check` before the change: `clang` present (14.0.0), `nvcc` absent on the default `PATH`, `nvidia-smi` present.
- **Download and install** (D29, Qualcomm's official site, no login or terms prompt):
  - Command: `curl -sSL -o v2.37.0.250724.zip https://softwarecenter.qualcomm.com/api/download/software/sdks/Qualcomm_AI_Runtime_Community/All/2.37.0.250724/v2.37.0.250724.zip`. It redirects to `apigwx-aws.qualcomm.com/qsc/public/v1/api/download/...`; 1,354,151,797 bytes, sha256 `878685c710b0d3b1c3d4694e6d135305720e08bf35d5047424a0431f0d04b0e9`. Downloaded into `/tmp/hilclaw-driver/T-0544/`, unpacked with `unzip`, archive removed.
  - Version (`sdk.yaml`): product QAIRT, version 2.37.0, build_id 250724175447_124859, qnn_backend_api_version 2.18.0.
  - **Install path `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724`** (WSL `/mnt/c/Qualcomm/AIStack/QAIRT/2.37.0.250724`); one copy serves both. It was first unpacked under WSL `~/qairt` and then moved there, because Windows Python's `shutil.which` cannot find `qnn-net-run.exe` on the case-sensitive `\\wsl.localhost` share.
  - Licence file: `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724\LICENSE.pdf` (not read).
  - Nothing of the SDK is committed or pushed. No image was made.
- **The x86_64 Linux form cannot run here**: `bin/x86_64-linux-clang/qnn-net-run` and `lib/x86_64-linux-clang/libQnnHtp.so` need `libc++.so.1`, `libc++abi.so.1` and `libunwind.so.1`, which the SDK does not ship. The SDK's `bin/check-linux-dependency.sh` installs apt `clang`, `libc++-dev` and `libc++abi-dev` on Ubuntu 22.04. They were not installed: they are a non-Qualcomm prerequisite (D29; see the HQ below). The checks therefore ran on the documented Windows x64 host form, which needs none of them. In WSL the fixture compiles and links with clang 14 (`-ldl`), but its run exits 1 (`cannot load .../libQnnHtp.so`), and `qnn-net-run --version` ends with the loader's status 127.
- **Real-SDK execution tests (FR-19 ⑤)** on Windows x64: Python 3.14.4, `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724\bin\x86_64-windows-msvc` prepended to `PATH`, compiler MinGW gcc 16.2.0. There is no clang on Windows; the SDK documents MSVC or clang-14 there, and the C interface is plain C.
  - `add.c` builds (`go_on`) and runs on the HTP emulator (`QnnHtp.dll`), with status 0 and last line `sum 11 22 33 44` (`go_on`).
  - `broken.c` fails (`build_exit_status`, no artefact).
  - `probe` reports `present` with `QNN SDK v2.37.0.250724175447_124859`.
  - `tests/test_qnn_adapter.py`: 65 passed, 1 skipped (the POSIX signal test).
  - How the tests find the SDK: `shutil.which("qnn-net-run")`; the SDK root is its `../..`; the compiler is `clang` on `PATH`, else `gcc` on Windows. Without `qnn-net-run` on `PATH` the three tests skip ("qnn-net-run is not on PATH (FR-19 (5): a vendor tool's execution test)"). With the Linux SDK `bin` on `PATH` and no libc++ they fail rather than skip, because the SDK is present but unusable.
  - The default `clang` build form was checked only to compile and link, in WSL.
- **Local runs** (WSL2, Python 3.12.13, `~/.venvs/hilclaw-driver`, default `PATH`):
  - Full suite: 40632 passed, 95 skipped in 9 min 52 s. The 3 QNN and 3 `nvcc` execution tests skip; the other 89 skips existed before.
  - `coverage run --branch`: `hilclaw/qnn_adapter.py` 100 %; `hilclaw/toolchain_check.py` 98 % (line 291, `raise SystemExit(main())`, is run by a subprocess test).
  - `ruff check`, `ruff format --check` and the C gate command pass.
  - CI on the PR: C gate, Python gates 3.11 and 3.14, Coverage gate, Test presence and sh gate all pass.
- **`python -m hilclaw.toolchain_check` after the change**:
  - Windows, SDK `bin` on `PATH` (status 0): `{"host": {"clang": {"state": "absent", ...}, "nvcc": {"state": "present", "version": "Cuda compilation tools, release 12.3, V12.3.107", ...}, "nvidia-smi": {"state": "present", "version": "NVIDIA GeForce RTX 4070 (driver 617.14)", ...}, "qnn-net-run": {"state": "present", "version": "QNN SDK v2.37.0.250724175447_124859", "message": null}}, "images": {}}`
  - WSL2, default `PATH` (status 0): `qnn-net-run` `absent` ("the program was not found or could not be started"); the other entries as before.
  - WSL2, Linux SDK `bin` and CUDA on `PATH`, image `hilclaw-standin:2026-10-29` (status 10): host `qnn-net-run` `unreadable` ("the version query ended with a non-zero status or by a signal"); image `qnn-net-run` `absent`.
- **D21 list-assertion edits** (`tests/test_toolchain_check.py`):
  - `test_the_table_holds_the_clang_adapter_probe_pair`: `list(COMPONENTS)` gains `"qnn-net-run"`.
  - `test_the_device_query_is_not_read_in_an_image`: `started` gains `("qnn-net-run", ("--version",))`; `list(report["host"])` and `list(report["images"][IMAGE]["components"])` gain `"qnn-net-run"`.
- **Runtime acceptance item (D22)**: 드라이버가 `PROCESS/RuntimeAcceptance.md`에 더할 항목이다(출처 `P3-10`, 근거 task T-0544, ADR-0194).

  PLAN P3-10. 오너가 런타임 머신에서 다음을 확인한다.
  ① C-7의 각 머신 종류(native Linux, macOS Docker Desktop, Windows WSL)에서 `python -m hilclaw.toolchain_check <image>`가 `qnn-net-run`을 맞게 보고하는지 본다. 대상은 QNN SDK의 `bin`이 `PATH`에 있는 host와 그 SDK를 담은 이미지다. SDK가 있으면 `QNN SDK v…` 줄과 함께 `present`, 없으면 `absent`, 있지만 실행되지 않으면(예: x86_64 Linux에서 libc++ 없음) `unreadable`이어야 한다.
  ② libc++가 있는 Linux 머신(또는 이미지)에서 x86_64 Linux 형태가 도는지 본다. `tests/qnn_fixtures/add.c.in`을 clang으로 빌드한 C 프로그램이 `libQnnHtp.so`(HTP 에뮬레이터)를 불러 `sum 11 22 33 44`를 내고 상태 0으로 끝나야 한다.
  ③ Qualcomm 장치 지점은 이 머신에 장치가 없어 확인하지 않았다(접근 수단은 HQ-0095 ③).

  개발 머신에서의 확인 범위: 실행은 Windows x64의 실제 SDK 2.37.0.250724(MinGW gcc 16.2.0 빌드)로만 확인했다. WSL2에서는 libc++가 없어 빌드와 링크까지만 확인했다. T-0544 착지 뒤 확인할 수 있다.
- **New HQ** (§8 구조, 드라이버가 기록):

  질문: x86_64 Linux에서 QNN을 실행하는 데 필요한 libc++ 패키지를 개발 머신의 WSL2 host에 설치해도 될까요?
  - 배경: QNN SDK 2.37.0.250724의 x86_64 Linux 도구(`qnn-net-run`)와 HTP 에뮬레이터 라이브러리(`libQnnHtp.so`)는 `libc++.so.1`, `libc++abi.so.1`, `libunwind.so.1`이 있어야 실행된다. 이 셋은 SDK에 들어 있지 않다.
  - SDK의 요구: SDK의 `bin/check-linux-dependency.sh`는 Ubuntu 22.04에서 apt `libc++-dev`와 `libc++abi-dev`를 설치하라고 한다. Ubuntu jammy universe의 LLVM 14 패키지이고, 라이선스는 Apache-2.0 WITH LLVM-exception이다.
  - 설치 대상: 이 두 패키지와 그 의존 패키지 `libc++1-14`, `libc++abi1-14`, `libunwind-14`.
  - 요청하는 이유: Qualcomm 사이트 밖의 도구라서 D29에 따라 요청한다.

  선택지:
  - (a) WSL2 host에 apt로 설치하는 것을 승인한다. 그러면 다음 P3-10 task가 x86_64 Linux 형태(런타임 이미지와 같은 Linux)로도 실행을 확인한다. (권고)
  - (b) host가 아니라 도구 이미지에 넣는 것만 승인한다. 다만 이미지에 QNN SDK를 넣는 것은 HQ-0094(라이선스)의 답에 걸린다.
  - (c) 설치하지 않는다. 그러면 Linux 형태의 실행 확인은 RuntimeAcceptance 항목으로만 남는다.

  걸리는 것: x86_64 Linux(WSL2)에서의 QNN 실행 확인.
  걸리지 않는 것: T-0544(Windows x64에서 확인하고 착지), 다음 P3-10 task의 Windows x64 형태 확인, P3-13, P3-14.
- **Size**: about 160 lines in `hilclaw/qnn_adapter.py` (over half docstrings) and 10 lines in `hilclaw/toolchain_check.py`; 2 source files, 2 test files and 2 fixture files.
- **Cleanup**: the task directories `/tmp/hilclaw-driver/T-0544/` (WSL2: the downloaded archive, already removed after the install, extracted documentation text, pytest temporaries and logs) and `%TEMP%\hilclaw-driver\T-0544\` (Windows: fixture builds, PR body and commit texts) are removed with `rm -r` after the merge. The installed SDK at `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724` stays (a tool install, D29). No image was created.
