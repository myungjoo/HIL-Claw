---
id: T-0544
title: Add the Qualcomm QNN adapter of PLAN P3-10 (build, HTP-emulator run and SDK version probe) on the ADR-0194 frame, checked with a real QNN SDK on the machine
phase: P3
status: IN_PROGRESS
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
