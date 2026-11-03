---
id: T-0541
title: Add the vendor adapter frame of ADR-0194 decisions 2, 3 and 6 (pure assemble and interpret around the existing executors) with a clang reference adapter checked against the real clang
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [FR-19, OD-33, FR-10, NFR-4, "PLAN P3-8"]
dependsOn: []
touchesFiles:
  - hilclaw/vendor_adapter.py
  - hilclaw/clang_adapter.py
  - tests/test_vendor_adapter.py
  - tests/test_clang_adapter.py
estimatedSize: {loc: 350, files: 2}
hq: []
---
## Why

**PLAN P3-8** ("벤더 어댑터 틀과 환경 점검"): turn the boundary of P3-7 into code. P3-7 is checked (T-0540, ADR-0194, `c10d84b1`). This task is the first of two for P3-8: the adapter frame and a reference adapter for `clang`. T-0542 adds the environment check command on top of it. The driver checks PLAN P3-8 only when both are `DONE`.

**Order (DRIVER §6 D27 ①).** On `main` `3d0b2123` no `nightly-failure` issue is open, no PR is open, `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패` (RA-0056 is `미확인`), and no P2-15 preparation is pending. P3-3 waits on HQ-0090 and HQ-0091 and is treated as handled (D27 ⑦). P3-6 is "오너 확정 필요". P3-7 is checked. So P3-8 is the next P3 item in listed order. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥).** HQ-0092 to HQ-0097 (from T-0540) all list P3-8 under "[막히지 않는 것]". This task anticipates none of their answers. It adds no `device_unavailable` kind (HQ-0097 (a)). It assigns no measuring point (HQ-0095). It writes no vendor target, version or image (HQ-0093, HQ-0094). It does not touch `correctness.check` at a vendor target (HQ-0096). HQ-0088 to HQ-0091 and HQ-0081 are not touched either.

**What the frame is (ADR-0194 decision 2).** An adapter does one of three jobs for one target: build, run or measure. Each job has three parts. **Assemble** is a pure function that returns argument lists, an environment and files to place. **Execute** is an existing executor, unchanged: `clang_build.build` or `local_run.run` on the host, or `standin_container.run_in_container`. **Interpret** is a pure function that maps what the executor returned or raised to one outcome of decision 3. No adapter starts a process of its own. The program an adapter starts is an argument whose default is the adapter's constant, the way `clang_build.build` takes `compiler` (decision 6). A test can therefore point it at a fault-injection script.

**Why clang (ADR-0194 decision 2, last bullet; D29).** The frame is checked with the real `clang`, the tool CI already has. No vendor toolchain is needed and none is faked. A vendor toolchain absent from the machine does not block this task. P3-9 (CUDA) and P3-10 (Qualcomm) add their own adapters on this frame.

**`cpu_standin` and `virtual_npu` are untouched (ADR-0194 decision 2).** Their operations do not move onto the adapters in this task. No argument list, result or file of theirs changes, and their existing tests pass.

**Size.** About 350 LOC in two new modules, excluding tests. The environment check (T-0542) is a separate command with its own surface and tests, so it is kept as a second task of about the same size rather than merged (DRIVER §5 D30, §6 D20 ③).

**D16.** This task is verified on the development machine with the real `clang` where present and with fault scripts that the tests write. It needs no `claude`, board, accelerator, vendor SDK or API key. Docker is not started by any test except through the existing stub clients.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0541-<slug>`, the `Task: T-0541` trailer and the PR body's last line, size recommendation and file cap D30, the test rules D12, the list-assertion rule D21, the storage rule D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0541/`), §3 "BLOCKED 사유", §6 D27 and **the D29 toolchain paragraph** (the executor reads the machine's toolchains before writing code; record what it found in `## Result`).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (one line with language and reason in the commit body and `## Result`), "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0194-od33-vendor-stack-evaluation-design.md`: **decisions 1, 2, 3 and 6 in full** (the binding text of this task), decision 4 (what one timing includes; the measure part's input), decision 7 (the probe parts that T-0542 will call: "No second list of commands"), decision 8 ⑧ (no CUDA C++ here), Consequences "A-13 reading".
- `ARCHITECTURE/decisions/ADR-0060-od18-correctness-check-build-answers-and-settings.md` decision 4 (S6 to S10); `ADR-0168-od18-standin-container-situations.md` decisions 3 and 4 and rows C3, C5 to C10; `ADR-0110` decision 3 and `ADR-0021` decision 5 (why statuses of the attempt's process are never read as tool failures); `ADR-0065-od18-run-tools-operation-form.md` decision 4 (forms (A) and (B)); `ADR-0016-od18-backend-frame.md` decisions 2 and 5 (b), (e).
- Code: `hilclaw/clang_build.py` lines 1-60, 196-260 and 426-455 (`build`, its errors, `compiler_version`); `hilclaw/local_run.py` lines 1-110 (`run`, `RunResult`, `ProgramNotFoundError`); `hilclaw/standin_container.py` lines 54-140 (`run_in_container`, `ContainerResult`); `hilclaw/standin_answer.py` lines 1-60 and 105-280 (the container-side interpretation, which the frame reuses and does not copy); `hilclaw/check_failure.py` lines 85-125 and `hilclaw/run_result.py` (the `CONDITIONS` and kind spellings); `hilclaw/run_operation.py` lines 1-60 and 147-160 (form (A) pair, form (B) condition); `hilclaw/targets.py` lines 57-112 (`Target`).
- Tests: `tests/test_clang_build.py` around line 105 (how clang presence is handled) and around line 1929 (`posix_only`, `windows_only`); `tests/conftest.py` (the container-client guard).

## Acceptance Criteria

1. **Frame module `hilclaw/vendor_adapter.py`.** It defines one outcome value type that every interpret part returns. The value is exactly one of the following:
   - **go on**, carrying what the next job needs: the artefact path after a build, or the ended process's output after a run;
   - **broken**, with `condition` set to one of `build_exit_status`, `build_time_limit`, `exit_status` or `time_limit`, spelt as in `run_result.CONDITIONS`;
   - **tool failure**, with one existing backend kind of `check_failure`: `compiler_unavailable`, `build_output_missing` or `executable_unstartable`.

   Each outcome carries a message. No new condition, kind, result member or `step` value is introduced, and none is spelt anew where an existing constant can be imported.
2. **Interpret on the host, as in the table of ADR-0194 decision 3.** The build interpretation reads a `clang_build.BuildResult` or the error `clang_build.build` raised:
   - `ok` gives go on;
   - a non-zero status gives broken `build_exit_status`;
   - `timed_out` gives broken `build_time_limit`;
   - status 0 with no artefact gives `build_output_missing`. The executor names how the frame observes this case through `clang_build`'s API, where `ok` already requires the artefact;
   - `CompilerNotFoundError` or `CompilerNotStartedError` gives `compiler_unavailable`.

   The run interpretation reads a `local_run.RunResult` or the error `local_run.run` raised:
   - status 0 gives go on;
   - a non-zero status or a signal gives broken `exit_status`;
   - `timed_out` gives broken `time_limit`;
   - `ProgramNotFoundError`, or a program that cannot start, gives `executable_unstartable`. Only these errors, raised before any process ran, map to this kind.

   Errors outside these rows propagate unchanged, so the frame does not swallow a fault of its own.
3. **Interpret in a container: reuse.** For a `standin_container.ContainerResult` (or what `run_in_container` raised), the frame reaches the answer through `standin_answer.read_build`, `read_process` and `place_error`, and converts that answer to its outcome type. It does not keep a second copy of ADR-0168's table. Inside a process container, statuses 125 to 127 stay `exit_status` (ADR-0168 decision 3), and a test asserts this.
4. **The measure part.** A pure function maps one ended timing process to form (A) or form (B) of `run_operation`. Form (A) is the pair of its report bytes and a figure (or `None`); form (B) is one of `run_operation.CONDITIONS`. The function reads only the executor result and the arguments it is handed: no clock, file or variable. Status 0 gives the pair. A non-zero status or a signal gives `exit_status`. A time limit gives `time_limit`. Device synchronisation inside the interval (decision 4) belongs to the harness and is not done here. The figure is the caller's argument: the frame computes no memory figure (ADR-0052 is unchanged; HQ-0090 (나)).
5. **Assemble parts are pure.** Every assemble function returns plain values: argument tuples, an environment mapping or `None`, and the files to place. It starts no process and reads no file, clock or environment variable. A test monkeypatches `subprocess`, `os.environ`, `time` and `open` to raise, then calls each assemble function successfully.
6. **Clang reference adapter `hilclaw/clang_adapter.py`.**
   - **Build:** assemble from a `targets.Target` (`flags`, `trailing_flags`, `env`, `build_time_limit_s`), the sources and the output path into the arguments of `clang_build.build`. The program is an argument whose default is the module's constant `clang`.
   - **Run:** assemble the built executable and its arguments into a `local_run.run` command, with the target's `env` and a time limit capped by the target's `process_time_limit_cap_s`.
   - **Probe:** assemble the version query (`<program> --version`) as a `local_run.run` command, and interpret its result as present with a version (the first non-empty stdout line, stripped, as `clang_build.compiler_version` reads it), absent (`ProgramNotFoundError` or a program that cannot start), or unreadable (non-zero status, time limit or no version line), each with a message. T-0542 calls this probe pair.
   - **Execute:** a thin function per job that calls the existing executor with the assembled values and hands the result to interpret, and nothing else.
7. **Checked with the real clang.** Tests build a test-only `Target`. It is never added to `targets.TABLE` or to any backend table. The tests show that the real `clang`:
   - builds a small C program to go on;
   - fails to compile a broken source with broken `build_exit_status`;
   - produces an executable whose run exits 0 (go on) and one that exits 3 (broken `exit_status`);
   - produces an executable that sleeps past a short limit (broken `time_limit`);
   - is reported present with a version string by the probe.

   A program path that does not exist gives `compiler_unavailable` for the build and `executable_unstartable` for the run, and the probe reports it absent. These tests follow the existing clang test pattern of `tests/test_clang_build.py`. Do not add a new skip rule for clang: CI has clang, and its absence stays a CI failure (D29).
8. **Fault-injection scripts (ADR-0194 decision 6).** Each script is written by the test into its own temporary directory, or kept as a fixture under `tests/`. None lives under `hilclaw/`, on `PATH` or in an image. A script is POSIX sh, or Python run by the test's own interpreter. It is passed only through the program argument, never through an environment variable or `PATH`. It reads no clock, random source or counter. The test names the behaviour it stands for, with its source.

   Scripts stand only for failures hard to cause with the real tool:
   - a compiler that hangs (broken `build_time_limit`);
   - a compiler that crashes by a signal or a non-zero status with no diagnostic (broken `build_exit_status`);
   - a compiler that exits 0 and leaves no artefact (`build_output_missing`);
   - a version query that hangs or prints no line (probe unreadable).

   No script stands for a success, a compile failure, a version string or an argument clang accepts. Scripts needing POSIX execution are marked with the module's existing POSIX-only pattern.
9. **Nothing attaches yet.** No `Target` entry, backend, backend-table entry, tool, `step` value, data-plane file or member is added or changed (ADR-0194 Consequences "A-13 reading"). `cpu_standin` and `virtual_npu` keep their operations, argument lists and results, and every existing test passes unchanged. The only allowed edits are list assertions under DRIVER §5 D21. None are foreseen; any edited assertion is listed in the PR body.
10. **Tests (D12).** New modules each get their test file (`tests/test_vendor_adapter.py`, `tests/test_clang_adapter.py`). Every public function is covered with happy, error, branch and negative cases. Negative cases include wrong argument types and values, refused before anything starts in the style of `clang_build` and `local_run`, with the attribute `parameter` where those modules use it. Package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally, and the clang tests run.
11. **Toolchain reading (D29).** Before writing code, the executor reads which compilers and vendor tools the machine has, without installing anything (for example `clang --version`, `nvcc --version`, `nvidia-smi`), and records the result in `## Result`. Nothing is downloaded or installed in this task.
12. **`## Result`** states:
    - the language line;
    - the public names of both modules and the probe pair's signature, which T-0542 calls;
    - how the frame observes status 0 with no artefact (criterion 2);
    - the fault scripts and the behaviour each stands for;
    - the toolchain reading;
    - any runtime acceptance item for the driver to register (D22), in Korean. None is expected, since the frame runs only on the host.

## Out of Scope

- The environment check command and its report (T-0542).
- Any vendor adapter (`nvcc`, `nvidia-smi`, QNN), CUDA C++ fixtures, device probes and the `device_unavailable` outcome (P3-9, P3-10; HQ-0097 (a)).
- A backend or `Target` entry for a vendor target, the default backend table, and the operation that composes the build, run and measure adapters into a `sim.run` or `board.run` operation (P3-9 and later, after HQ-0095 and HQ-0097).
- Moving `cpu_standin` or `virtual_npu` onto the adapters (ADR-0194 decision 2).
- Giving a container a GPU or device (the rest of OD-33 ⑨).
- Any edit of `ARCHITECTURE/`, `PROCESS/PLAN.md` or `PROCESS/RuntimeAcceptance.md`.

## Follow-ups

- T-0542: the environment check command on the probe parts of this task.

## Result

- **Order check (D27 ①)**: unchanged when the task ran — no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`.
- **Language**: Python — the frame wraps the existing Python executors (`clang_build`, `local_run`, `standin_container`) and reads their Python result and error types, so another language would add a boundary for nothing.
- **Public names.** `hilclaw/vendor_adapter.py`: `Outcome` (`form`, `message`, `carried`, `condition`, `kind`), `GO_ON`, `BROKEN`, `TOOL_FAILURE`, `FORMS`, `go_on`, `broken`, `tool_failure`, `BUILD_TIME_LIMIT`, `BUILD_EXIT_STATUS`, `TIME_LIMIT`, `EXIT_STATUS` (taken from `run_result.CONDITIONS[:4]`), `KINDS` (the three `check_failure` constants), `BuildCall`, `RunCall`, `Probe` (`state`, `version`, `message`), `PRESENT`, `ABSENT`, `UNREADABLE`, `PROBE_STATES`, `interpret_build`, `interpret_run`, `interpret_container_build`, `interpret_container_run`, `measure`, `check_timeout`. `hilclaw/clang_adapter.py`: `PROGRAM` (`"clang"`), `assemble_build`, `assemble_run`, `assemble_probe`, `interpret_probe`, `build`, `run`, `probe`.
- **Probe pair for T-0542**: `clang_adapter.assemble_probe(*, timeout_s, program=PROGRAM) -> vendor_adapter.RunCall` (command `(*program, "--version")`, `env` `None`) and `clang_adapter.interpret_probe(answer, program) -> vendor_adapter.Probe | None`, where `answer` is the `local_run.RunResult` or the `Exception` of `local_run.run(call.command, timeout_s=call.timeout_s, env=call.env)` and `program` is `call.command[0]`; `None` means no row holds the exception and the caller re-raises it. `clang_adapter.probe(*, timeout_s, program=PROGRAM) -> Probe` joins the two. The version is the first stdout line, stripped, and it must not be blank — exactly `clang_build.compiler_version`'s reading (the task's words "first non-empty line" and that function differ for a blank first line; the function's reading was kept, a blank first line is `unreadable`).
- **Status 0 with no artefact on the host**: `clang_build.build` returns a `BuildResult` with `ok` false, `returncode` 0 and `timed_out` false exactly when the compiler exited 0 and left no file (its `ok` requires the artefact); `interpret_build` reads that through `check_build.read_build`, which already maps it to `build_output_missing`, so ADR-0060's table is reused, not copied. In a container, `interpret_container_build` stats only the artefact path it is handed after `standin_answer.read_build` says go on (ADR-0194 decision 2 "files at named paths").
- **Interpretation choices of the executor** (reviewer-visible): a host `OSError` from `local_run.run` counts as "a program that cannot start" only when it carries no `path_role` and its `filename` has the program's last path component (POSIX `subprocess` names the program in a failed exec); any other `OSError` is passed on unchanged. On native Windows the failed-start error names no file, so it is passed on there. `measure` reads a host `local_run.RunResult` only; a timing process in a container keeps ADR-0168 decision 4's waiter reading (`standin_answer.read_timing_process`), so the frame does not measure one (review round 1). In a container, an answer of `standin_answer.place_error` whose kind is outside the three kinds (`settings_refused`, `build_directory_unusable`) or none leaves the exception to be raised unchanged.
- **Fault-injection scripts** (Python, written by `tests/test_clang_adapter.py` into the test's own `tmp_path` and passed only as `program` with the test's own interpreter): `HANG` (`threading.Event().wait()`) — a compiler that never ends (`build_time_limit`) and a version query that never ends (`unreadable`); `SILENT_STATUS` (`sys.exit(70)`, no output) — a compiler that fails with no diagnostic (`build_exit_status`); `SIGNAL` (SIGSEGV to itself, POSIX only) — a compiler that crashes by a signal (`build_exit_status`); `NO_ARTEFACT` / `NO_LINE` (`pass`) — a compiler that exits 0 and writes nothing (`build_output_missing`) and a version query that prints no line (`unreadable`). None reads a clock, random source or counter. Besides these, one POSIX-only test writes a file of junk bytes with the execute bit to show the failed-start path (`executable_unstartable`, probe `absent`, `compiler_unavailable`); it stands for no tool. Success, compile failure, exit 0/3, time limit of a real executable and the version string are shown with the real `clang`.
- **Toolchain reading (D29)**, nothing installed or downloaded: native Windows — `clang` not on the Git Bash `PATH`, `C:\Program Files\LLVM\bin\clang.exe` = clang 22.1.6 (x86_64-pc-windows-msvc); `gcc` 16.2.0 (MinGW-W64); `nvcc` CUDA 12.3 (V12.3, built 2023-11-22); `nvidia-smi` driver 617.14, CUDA UMD 13.4, GPU NVIDIA GeForce RTX 4070 12 GiB; no QNN tools (`qnn-net-run`, `qnn-context-binary-generator`) and no `C:\Qualcomm`; no `docker` on Windows. WSL2 Ubuntu — Ubuntu clang 14.0.0-1ubuntu1.1, no `nvcc`, `nvidia-smi -L` shows the RTX 4070, Docker 29.1.3, Python 3.12.13 (pytest 9.1.1, coverage 7.16.2, ruff, numpy 2.4.6).
- **Runtime acceptance items (D22)**: 없음 — 이 틀과 clang 참조 어댑터는 host에서만 돌고 런타임에 붙지 않는다(Target·백엔드·도구 추가 없음).
- **Size**: 710 lines in the two modules, about half of them docstrings (estimate was 350; above the 600-LOC recommendation of D30 because the criteria ask for the container interpretation and the measure part besides the host parts); 2 source files and 2 test files.
