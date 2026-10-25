---
id: T-0460
title: Give local_run.run an optional standard-input argument (ADR-0164 code slice 1)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0459]
touchesFiles: [hilclaw/local_run.py, tests/test_local_run.py]
estimatedSize: {loc: 80, files: 1}   # package code only; tests/test_local_run.py is test code, excluded from the cap (D4)
hq: []
---
## Why

**State on `main` `168d132`.** ADR-0164 (T-0459, `f9b8096`) records the bf16 verification run of kind `rope` on `cpu_standin`. Its decision 3 hands the `freqs_cis` rows to the verification program on the process's **standard input**: the Python side writes 4·m·d bytes (up to 524,288 bytes at the largest shape) and closes the pipe, and the program reads exactly that many bytes. Today `hilclaw.local_run.run` always starts the process with standard input set to the null device (`stdin=subprocess.DEVNULL` in both `_run_without_usage` and `_run_with_usage`; module docstring line 19). ADR-0164 Consequences lists the work as four code slices; this task is **slice 1**: "an optional standard-input argument of `local_run.run`, written while the output is drained and closed, a broken pipe from a process that exits early being its result, not an exception". Decision 3 adds that "the null device [is] kept when it is absent, so every present caller is unchanged".

**Why now, and why this slice before the others.** Slices 2 to 4 (the C program, the Python side, the calibration) all need the rows to reach the program, and slice 3 cannot run a program without this argument. The slice is small and self-contained: one module and its test file.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items, and P2-14 needs every Llama kind verified, so the D18 rule does not apply. Unresolved HQs still hold the round-loop items and P2-5 (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4). Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0459.

**D16.** The tests start local Python child processes (`sys.executable`) through `run`, as the existing tests do. Nothing starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (test code excluded), the naming and the test rules. Branch `claude/T-0460-<slug>`; commit trailer `Task: T-0460`; code mode, so a Draft PR whose body ends with `Task: T-0460`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, code mode.
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`:
  - decision 3 (lines 45-51): the channel, "reads exactly that many bytes … then requires end of input", and "The cost: `local_run.run` gains an optional standard-input argument (code slice 1), with the null device kept when it is absent";
  - decision 13, item 4 (lines 110-116): the size of the input at the largest shape;
  - Consequences (lines 133-145): the slice 1 sentence, and the "less exact once code slice 1 lands" bullet (ADR-0009 Context, ADR-0017 Alternatives), which this task does **not** edit.
- `hilclaw/local_run.py`, the whole file (360 lines): the module docstring, `run`'s docstring (the order of the checks and the `parameter` attribute), `_run_without_usage`, `_run_with_usage`, `_drain`, `_reap`, `_kill_and_reap`.
- `tests/test_local_run.py`: lines 1-80 (the `PRELUDE`, the `Child` helper, `posix_only`/`windows_only`, `TIMEOUT`), lines 155-159 (`test_the_process_sees_end_of_file_on_standard_input`) and lines 200-250 (the timeout and signal tests), as the model for new tests.

## Acceptance Criteria

1. **New keyword-only argument `stdin_data=None` of `hilclaw.local_run.run`** (the name is fixed here so that slice 3 can rely on it):
   - `None` (the default): exactly today's behaviour — standard input is the null device. No present caller (`hilclaw/coder_runtime.py`, `hilclaw/harness/verification.py`, `timing.py`, `bf16_verification.py`) changes, and none of them is edited.
   - A `bytes` object, including `b""`: the process is started with a pipe on standard input; the runner writes all the bytes and then closes the pipe, so the process reads exactly those bytes followed by end of input. `b""` gives a pipe closed at once (end of input, as with the null device).
   - Any other type (including `str`, `bytearray`, `memoryview`, `int`) is refused with `TypeError` **before anything is started**, carrying `parameter == "stdin_data"`, as the other pre-start checks carry theirs. It is checked **after** `cwd`, so the existing order (time limit, command, `env`, `cwd`) and every existing error stay as they are.
2. **No deadlock and no limit beyond today's.** The input is written while stdout and stderr are drained, so a process that writes more than a pipe buffer before reading its input, or reads its input only after writing, completes. Writing counts against the same `timeout_s`: if the limit is reached while input is still unwritten, the run is a timeout result exactly as today (process killed, output captured so far kept, `returncode` `None`).
   - **POSIX path (`_run_with_usage`)**: register the stdin pipe for writing in the same selector loop as the output pipes, write with non-blocking writes in chunks, and close the pipe after the last byte; `os.wait4` and `max_rss` work as before.
   - **Native Windows path (`_run_without_usage`)**: passing the bytes to `subprocess.run` as its input is acceptable (it writes from a thread and closes); keep `stdin=subprocess.DEVNULL` when `stdin_data` is `None`.
3. **A process that does not read its input is a result, not an exception.** If the process exits or closes its standard input before all the bytes are written (a broken pipe, `EPIPE`, or on Windows the `EINVAL` `subprocess` already tolerates), the runner stops writing, closes its end, keeps draining and reports the process's exit status and output as usual. No `BrokenPipeError` or other `OSError` from writing the input leaves `run`. Whether the input was written in full is not reported (the program of ADR-0164 decision 3 checks its own input; the Python side judges the run).
4. **Documentation in the module.** Update the module docstring (the sentence "The process is started without a shell, with no standard input.", and the "Known limits" paragraph: the input is held in memory, without a size limit) and `run`'s docstring (the argument, the null device when it is absent, the `TypeError` with `parameter`, the place of the check in the order, the broken-pipe rule, writing under the time limit). No other comments beyond what the code needs (CLAUDE.md "코멘트 최소화").
5. **Tests in `tests/test_local_run.py`** (CLAUDE.md 테스트 규칙 ①-④), using the existing `Child` helper:
   - **happy**: the child echoes its standard input to stdout, byte for byte, for a small input with every byte value 0-255 (no decoding, no newline translation on Windows) and for an input larger than a pipe buffer (at least 2 MiB, the size of `LOUD`), with `returncode == 0`;
   - **no deadlock**: the child writes more than a pipe buffer to stdout (and to stderr) **before** reading its input, then echoes a digest or the length of what it read; the run completes with both outputs and the input intact;
   - **`b""`**: the child sees end of input at once and exits 0;
   - **default unchanged**: the existing end-of-file test still passes with no `stdin_data`, and `stdin_data=None` gives the same;
   - **broken pipe**: a child that exits at once without reading, given at least 2 MiB of input, gives a result with its own exit status (for example 3) and no exception; a child that closes its standard input after reading a few bytes and then writes to stdout and exits 0 gives that output and `returncode == 0`;
   - **timeout while writing**: a child that never reads and sleeps past a short `timeout_s`, given more than a pipe buffer of input, gives `timed_out is True`, `returncode is None`;
   - **negative**: each refused type gives `TypeError` with `parameter == "stdin_data"` and starts nothing (use the `started` record of `Child`); a refused `stdin_data` together with a bad `cwd` gives the `cwd` error (the order of the checks);
   - POSIX-only cases (for example `max_rss` still handed on with input given) marked `posix_only` as the existing ones are.
   The full local test suite and `ruff check`/`ruff format --check` are green; coverage of `hilclaw/` stays at or above 80% for lines and functions (CI is the gate).
6. **Language**: Python (the module is Python). Record the choice and its reason in one line of the commit body and of `## Result` (CLAUDE.md language policy, DRIVER §5).
7. **Process**: code mode (CLAUDE.md A-13).
   - Open a Draft PR titled with `T-0460`, whose body ends with `Task: T-0460`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least: that `stdin_data=None` leaves every present call's behaviour byte for byte as before (null device, same checks, same errors); that no path can deadlock on a full stdin or output pipe; that a broken pipe never escapes as an exception on either platform path; that a timeout while writing kills the process and keeps the output; that the pipe is closed on every path (no leaked descriptor, no `ResourceWarning`).
8. **Size**: `hilclaw/local_run.py` within 300 changed lines; only the two files of `touchesFiles` change.

## Out of Scope

- Passing `stdin_data` from `hilclaw/harness/bf16_verification.py` or any other caller (slice 3 does it for `rope`).
- The program `bf16_verification_rope.c`, `PROGRAM_SOURCES`, the Python side of `rope` and its calibration (ADR-0164 slices 2-4).
- Editing ADR-0009, ADR-0017, ADR-0164 or any other `ARCHITECTURE/` document, even where ADR-0164 lists a sentence as less exact once this slice lands.
- A size limit on the input or the output, sandboxing, killing the process's children, or any other change to the runner's known limits.
- Editing `PROCESS/PLAN.md` or `PROCESS/STATE.json` (the driver does).

## Follow-ups

- ADR-0164 code slice 2: `hilclaw/harness/bf16_verification_rope.c` and `rope` in `bf16_verification_build.PROGRAM_SOURCES`.
- ADR-0164 code slice 3: the Python side of `rope` (draw of `x`, rows from `rope_table.build`, check value over `x` and the rows, reference, judging with P, the rows passed as `stdin_data`).
- ADR-0164 code slice 4: the three calibration kernels with their tests.
- The harness record of SDPA with KV cache (ADR-0162 decision 13; ADR-0164 "Later work").

## Result
