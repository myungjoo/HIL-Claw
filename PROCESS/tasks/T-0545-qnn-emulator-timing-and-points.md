---
id: T-0545
title: Finish PLAN P3-10 — time a QNN one-op graph at the HTP-emulator point within the ADR-0194 decision 4 boundary, and show through the run tools that two points of one test-built QNN target stay apart (ADR-0194 decision 5)
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [FR-19, OD-33, FR-10, NFR-3, "PLAN P3-10"]
dependsOn: []
touchesFiles:
  - hilclaw/qnn_adapter.py
  - tests/test_qnn_adapter.py
  - tests/test_qnn_points.py
  - tests/qnn_fixtures/
estimatedSize: {loc: 120, files: 1}
hq: []
---
## Why

**PLAN P3-10** ("Qualcomm 대상") asks for three things on the real QNN toolchain. T-0544 (PR #360, `2298c8de`) landed the first: the QNN adapter's build, HTP-emulator run and SDK version probe. It left two, and **the driver did not check P3-10**:

1. "측정 경계는 에뮬레이터 지점에서 검사한다": the measurement boundary of ADR-0194 decision 4, checked at the emulator point.
2. "한 대상이 두 지점을 가질 때 결과에서 구별되는지도 검사한다(수단은 P3-7의 ADR이 정한다, 예: FR-10 mock)": results keep two points of one target apart, by the means of ADR-0194 decision 5.

This task does both. **When it is `DONE`, the driver checks PLAN P3-10.**

**One task, not two (DRIVER §6 D20 ③).** Almost all of the work is test code and C test fixtures, which the size recommendation does not count. The package change is at most a thin part in `hilclaw/qnn_adapter.py` (criterion 3). Split into two, each half would be far under half the recommendation.

**Order (DRIVER §6 D27 ①).** On `main` `f6db8f38`:
- no `nightly-failure` issue is open and no PR is open;
- `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패` (RA-0056 is `미확인`, so D27 ④ asks nothing yet);
- no P2-15 preparation is pending;
- P3-3 waits on HQ-0090 and HQ-0091, and is treated as handled (D27 ⑦);
- P3-6 is "오너 확정 필요";
- P3-7, P3-8 and P3-9 are checked; P3-10 is the next P3 item in listed order.

If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥; PLAN P3-10).** This task asks none of these again and anticipates none of their answers:
- HQ-0093: Qualcomm's place in the order, the SoC or Hexagon generation, the QNN version, HexKL.
- HQ-0094: the runtime's acquisition and licences.
- **HQ-0095 ① and ③: which execution is which point, and how a Qualcomm device is reached.** The two-point binding below is a **test-only** binding. It shows the means of decision 5 and assigns no point. HQ-0095's "[막히지 않는 것]" names "ADR-0194 결정 5의 구별 수단".
- HQ-0096 ②: the oracle at a vendor target.
- HQ-0097 (a): a `device_unavailable` kind.
- **HQ-0098: libc++ on the WSL2 host.** This task does not wait on it. If it has an answer when the task runs, follow it. On (a), install exactly the packages it names on the WSL2 host, record the command and versions (D29), and also run the execution tests in the x86_64 Linux form. Otherwise, run them on the Windows x64 form as T-0544 did.

So this task adds:
- no `Target` to `targets.TABLE`;
- no backend to any default backend table;
- no timing harness under `hilclaw/`, because what an attempt's code is at a QNN target is unanswered (HQ-0088, HQ-0092);
- no new condition, kind, `step` value, `unit` value, data-plane member or file;
- no QNN version in any record;
- no HexKL value.

If the work shows a further owner-only part that none of these HQs covers, write the question in `## Result` in the §8 structure (Korean). Land the rest and return `DONE` (D27 ⑥). A missing toolchain or prerequisite follows criterion 1 instead.

**What exists.**
- `hilclaw/qnn_adapter.py`: `assemble_build`/`build` (the `clang_build.build` form), `assemble_run`/`run` (a built program with arguments and the target's `env`), and the version probe. Its build, run and probe-assemble parts delegate to `clang_adapter`.
- `hilclaw/vendor_adapter.py`: `measure(answer, figure=None)`, which turns one ended timing process on the host into the form (A) `(stdout, figure)` or (B) `time_limit` / `exit_status` of `hilclaw/run_operation.py`.
- `hilclaw/harness/timing.py`: `driver_arguments`, `parse_report` and `judge_report`, the ADR-0009 report and its judging.
- `hilclaw/run_tool.py`: `tool_function("sim.run" | "board.run", …, table=…)`. `tests/test_run_tool.py` builds its own `BackendTable` for a test accelerator.
- `tests/qnn_fixtures/add.c.in`: a C program against QNN's C interface. It loads a backend library by the path given as its argument, then builds, finalizes and executes a one-op `ElementWiseAdd` graph. Fixtures are `*.c.in` because CI's C gate compiles every tracked `*.c` without SDK headers.
- The SDK: QAIRT/QNN 2.37.0.250724 at `C:\Qualcomm\AIStack\QAIRT\2.37.0.250724` (WSL `/mnt/c/...`). Its `lib/x86_64-windows-msvc` holds both `QnnHtp.dll` (the HTP emulator) and `QnnCpu.dll` (the QNN CPU backend). The executor reads the machine again before writing code (D29).

**D16.** Everything runs on the development machine: the real QNN SDK, its HTP emulator and CPU backend, and the stub-free run-tool tests. There is no `claude`, no Qualcomm board and no API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0545-<slug>`; the `Task: T-0545` trailer and the PR body's last line; size D30 and the file cap; tests D12; list assertions D21; storage D29 (temporary files and builds only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0545/`, removed at the end).
  - §3 "BLOCKED 사유".
  - §6 D27, and **the D29 toolchain paragraph** ("툴체인(D29 …)"). It covers: read the machine before writing code; Qualcomm tools are pre-allowed; any other tool is requested by an HQ; record the command, version, URL and install path in `## Result` and the PR.
  - §8: the HQ structure and runtime acceptance items (D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `PROCESS/PLAN.md`: the P3-10 line, the paragraph above P3-7, and the Qualcomm reservation under "P3 밖" (which makes no task).
- `PROCESS/tasks/T-0544-qnn-adapter.md`: whole, **including `## Result`**. It has the chosen build and run forms, how the tests find the SDK, why the x86_64 Linux form does not run here, the fault-script set and the fixture rename.
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`:
  - **decisions 2, 3, 4, 5 and 6 in full** (binding text);
  - decision 8 (C harness against the vendor runtime's C interface; C++ only as test fixtures);
  - decision 10 V4 and V6;
  - Consequences.
- `ARCHITECTURE/decisions/ADR-0007-od13-measurement-policy.md` decisions 2, 4 and 6 (what a sample covers, the stopping rule, warm-up).
- `ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md` decisions 3, 6, 7 and 8: the timer, the untimed execution, the repeat loop and the report form.
- `ARCHITECTURE/decisions/ADR-0065-od18-run-tools-operation-form.md` decisions 2 and 4 (what an operation is handed and returns).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md` decisions 2, 4 and 8 (`step` values per tool and point, the run result, one point per comparison).
- `ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md` decisions 3 and 5 (`not_offered`; tests build their own tables).
- `ARCHITECTURE/Requirements.md` line 37: FR-19, especially ④ and ⑤.
- Code:
  - `hilclaw/qnn_adapter.py`, `hilclaw/vendor_adapter.py` (module docstring and `measure`), and `hilclaw/harness/timing.py` (docstring, `driver_arguments`, `parse_report` and `judge_report`), whole;
  - `hilclaw/harness/timing_driver.c`, the reference C driver for the argument parsing, the stopping rule `converged` and the report writing;
  - `hilclaw/run_tool.py` lines 1-60 and 183-345;
  - `hilclaw/run_parameters.py` (`TimingParameters`, `Bf16TimingParameters`);
  - `hilclaw/backends.py` (`Backend`, `BackendTable`, `select`);
  - `hilclaw/timings_tool.py` docstring.
- Tests: `tests/test_qnn_adapter.py` (the `qnn`/`qnn_sdk` fixtures, `source()`, the real-SDK tests and the fault scripts), and `tests/test_run_tool.py` lines 1-340 (how a test builds a run, a request and its own `BackendTable`, and reads the lines).

## Acceptance Criteria

1. **Toolchain reading first (D29).** Before writing code, read the machine on Windows and in WSL2 without installing anything:
   - the QNN SDK of T-0544 and its `QnnHtp`/`QnnCpu` libraries;
   - the host compilers;
   - `python -m hilclaw.toolchain_check`;
   - HQ-0098's state in `PROCESS/STATE.json`.

   Record the reading in `## Result`. If the SDK is gone, reinstall it as T-0544's `## Result` records (pre-allowed). If a prerequisite from outside Qualcomm's site is needed and not approved, land nothing and return `BLOCKED` (`new-external-dependency`) with an HQ (§8, Korean) naming the tool, its source and its licence. A fault script never replaces an absent SDK or emulator (ADR-0194 decision 6).

2. **A QNN timing fixture at the emulator point (ADR-0194 decision 4).** Add `tests/qnn_fixtures/timing.c.in`. It is a C program against QNN's C interface, a test fixture and never under `hilclaw/`. It takes:
   - the backend library path;
   - then the eight arguments of `hilclaw.harness.timing` (`driver_arguments`), unchanged.

   It writes exactly the ADR-0009 decision 8 report on standard output, so that `timing.judge_report` accepts it. Its stopping rule is ADR-0007 decision 4's, as `timing_driver.c` computes it.

   The boundary is decision 4 read at the emulator:
   - **Outside the interval:** loading the backend; creating the backend, context and graph; `addNode` and `finalize`; tensor allocation and input generation; one untimed `QnnGraph_execute` before the first repeat (decision 4 "Warm-up"); reading back and checking the output.
   - **Inside the interval:** one `QnnGraph_execute` per repeat, between two readings of the host's monotonic clock. `resolution_ns` is that clock's resolution.
   - **The executor states:**
     - whether `QnnGraph_execute` returns only after the work is complete on this backend, with the source (SDK header or doc and its version);
     - if it does not, how the harness waits, and that the wait is inside the interval (decision 4 "Synchronisation");
     - what the harness cannot keep out, for example copies the backend makes inside `execute` when the client gives `QNN_TENSORMEMTYPE_RAW` buffers. Name this as the decision 4 rest ("nothing else the harness can keep out").

   The graph and the op are the fixture's own (for example `ElementWiseAdd` as in `add.c.in`). It is not an attempt's kernel and fixes no HTP architecture, SoC or optimisation value. The arguments `m`, `k` and `n` may set its tensor size; say how. A missing or failing QNN call ends the program with a non-zero status and one line on standard error, and writes no `stop` line.

   It builds with `qnn_adapter.build` on the existing form: include directory in the target's `flags`; `-ldl` in `trailing_flags` on POSIX; the clock headers it needs. Keep it within C99 plus POSIX `clock_gettime` (or `QueryPerformanceCounter` on Windows, chosen by the preprocessor).

3. **The adapter's measure part.** Decide whether `qnn_adapter` needs a part of its own for the timing run. If one is needed, add the least that fits, delegating to `vendor_adapter.measure` and `qnn_adapter.run`, and reading no clock or file. Examples:
   - an `assemble_timing` that puts the backend path before `timing.driver_arguments(...)`;
   - a `measure` that delegates.

   If no part is needed (the test composes `run` with `driver_arguments` and `vendor_adapter.measure`), add none and say so in `## Result`.

   Any part added follows `cuda_adapter`'s and `qnn_adapter`'s signature and refusal style (`parameter` on refused arguments). Foreseen D21 list-assertion edit, if a module constant is added: `tests/test_qnn_adapter.py::test_program_constants`. List every edited assertion in the PR body.

4. **The boundary checked with the real emulator (FR-19 ④ and ⑤).** In `tests/test_qnn_adapter.py`, real-SDK tests (found and skipped as T-0544's are) show:
   - the timing fixture builds (`go_on`);
   - run on the HTP emulator, it gives a form (A) answer from `vendor_adapter.measure`;
   - `timing.judge_report` accepts that answer's report: `resolution_ns`, at least `N_MIN` positive `interval_ns` lines, and a `stop` line that the replay agrees with, for both `sample_form` values;
   - a broken fixture call (for example a missing backend library path) gives `exit_status` through `measure` and writes no `stop` line.

   Assemble and interpret tests with recorded inputs run without the SDK. Fault scripts (decision 6 contract, as in T-0544) may stand only for a timing run that hangs (`time_limit`) or a backend that reports an allocation failure by its status (`exit_status`). Each names the documented behaviour and its source. **No `Result`, ADR or runtime acceptance item cites an emulator interval as a device figure** (FR-19 ④; decision 4, last bullets).

5. **Two points of one test-built target kept apart (ADR-0194 decision 5).** Add `tests/test_qnn_points.py`. It builds, in the test only:
   - a test accelerator name, not in `targets.TABLE`;
   - a `BackendTable` of one `Backend` for it, whose `sim.run` operation runs the timing fixture with the **HTP emulator** library and whose `board.run` operation runs the same fixture with the **QNN CPU backend** library.

   Each operation is built from `qnn_adapter`'s parts and returns what `vendor_adapter.measure` returns, in the ADR-0065 decision 4 forms. It follows the operation signature `run_tool` calls.

   The test states in its docstring, and `## Result` repeats, two things. The binding is test-only and assigns no point (HQ-0095 ①). The CPU backend stands in for "another means" only to show the separation, and is no device figure.

   Through `run_tool.tool_function` with that table and a run built as `tests/test_run_tool.py` builds one, real-SDK tests show:
   - a `sim.run` call and a `board.run` call on the same attempt each end with a converged or not-converged result whose line has its own tool's `step` value (ADR-0183 decision 2), in that tool's record. Each comes from its own operation: the board's run used the CPU library and the sim's the HTP library, seen for example from the build-log file or from which library path each operation was handed;
   - **no fallback**: with the `board.run` operation's library path made missing, `board.run` ends broken `exit_status` (its own run failure). The `sim.run` result stays as it was and is not used for the board;
   - **a point with no means**: a table whose backend offers only `sim.run` answers `board.run` with `not_offered` (ADR-0016 decision 3), and `sim.run` still works;
   - one comparison reads one point only (ADR-0183 decision 8). Show it by naming the existing `timings_tool` test that holds this, or by one new test.

   If `run_tool`'s path cannot run on the platform where the SDK runs (for example a POSIX-only part of the data root on Windows), do not change `run_tool` or its helpers. Instead:
   - keep the tool-function tests, skipped there with that stated reason;
   - also show the same separation at the operation level (each operation called directly with the run tool's arguments) with the real SDK;
   - name the limitation in `## Result` and as a runtime acceptance item (criterion 8).

6. **Nothing else changes.**
   - `cpu_standin`, `virtual_npu`, `clang_adapter`, `cuda_adapter`, `vendor_adapter`, `toolchain_check`, `run_tool`, `targets.TABLE`, the backend tables, the harness modules and the data plane keep their behaviour.
   - Every existing test passes, with only D21 edits.
   - No `ARCHITECTURE/`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md` edit is made.
   - No container is given a device.

7. **Tests (D12).** Every public function of `hilclaw/qnn_adapter.py`, including any part added, is covered.
   - Cover happy, error, branch and negative cases, including wrong argument types and values refused before anything starts.
   - Package line and function coverage stay at or above 80 %.
   - The full suite, `ruff check`, `ruff format --check` and the C gate command pass locally. CI passes on the PR.
   - The PR body states the SDK version, the host compiler and the execution-test results (D29).

8. **`## Result`** states:
   - the language line;
   - any part added to `qnn_adapter`, or that none was needed;
   - the fixture's command line and its boundary, with each criterion 2 statement and its source;
   - one real report from the HTP emulator and one from the CPU backend (first and last lines, the number of intervals), labelled as emulation and host figures, not device figures;
   - the two-point tests and on which platform they ran or skipped;
   - the toolchain reading, plus any install with its command, version and path;
   - any runtime acceptance item for the driver to add (D22, Korean). Expected candidates:
     - the timing fixture on the x86_64 Linux form, if HQ-0098 is not (a);
     - the two-point tool-function path on a platform where it was skipped;
   - any new HQ (§8 structure, Korean), with what it holds up;
   - storage cleanup per DRIVER §5 D29.

## Out of Scope

- Assigning the emulator or any other means to `sim` or `board` for a Qualcomm target, and a Qualcomm `Target`, backend-table entry or `correctness.check` (HQ-0093, HQ-0095, HQ-0096, HQ-0097).
- A QNN timing harness under `hilclaw/harness/` or any runtime form of an attempt's code at a QNN target (HQ-0088, HQ-0092).
- Any new `unit` or memory figure for a vendor target (HQ-0090).
- A Qualcomm device, `adb`, the Hexagon SDK, `hexagon-sim`, HexKL, AIMET, converters, and a QNN tool image.
- GPU timing (P3-13) and storage tools (P3-14).

## Follow-ups

## Result
