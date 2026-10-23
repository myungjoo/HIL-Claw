---
id: T-0421
title: Add the host side's run of the model program - a module hilclaw/model_run.py that encodes a list of fp32 gemm calls into the program's input file, starts the program with its libraries under a time limit, and reads the report into one output array per call or the named outcome run_failed (ADR-0153 code slice 1, host-side run part; for PLAN P2-13)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-10, OD-31, "PLAN P2-13"]
dependsOn: [T-0420]
touchesFiles: [hilclaw/model_run.py, tests/test_model_run.py]
estimatedSize: {loc: 230, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `08acf7d`):
- PLAN P2-5 cannot move: each remaining part waits on an open owner HQ (HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0032). P2-10 comes after P2-5.
- PLAN P2-11 (the contract records of the five non-GEMM kinds) and P2-12 (bf16/fp16) wait on HQ-0064, HQ-0065 and HQ-0066.
- PLAN P2-13: ADR-0153 decides the model executor. Its Consequences name code slice 1: the host side's binding checks and outcomes, and the build and loading of fp32 `gemm` kernels as shared libraries called by a model program. The record says slice 1 is possible before the answers to HQ-0064, HQ-0065 and HQ-0066.
- T-0420 (`96a186b`) landed the model program `hilclaw/model_program.c` and the build step `hilclaw/model_build.py`. Its header comment fixes the program's command line, input file, report and exit statuses.
- T-0419 (the binding check, `hilclaw/model_binding.py`, Draft PR #244) is BLOCKED on HQ-0067.

**This task** is the host side's run of the program, split from T-0420's follow-up to keep within the size cap:
- encoding the input file from in-memory arrays;
- starting the program with its libraries under a time limit;
- reading the report into one output array per call, or the named outcome **run failed** (ADR-0153 decision 5).

The build directory, the builds through `model_build`, the outcome **build failed**, and one function that does all of it, are the next task (Follow-ups). Joining with the binding check of T-0419 comes after HQ-0067 is answered.

**HQ-0067 reading.** HQ-0067 says the second half of slice 1 waits on it. The driver accepted for T-0420 the reading that this is a dependency of the joining, not of this code. The same holds here: this task neither reads nor names `hilclaw/model_binding.py`, and its input is not a `BindingCheck`.

**D18 reading.** This is work of a PLAN checklist item (P2-13, code of ADR-0153). The D18 hold rule does not apply (DRIVER §6).

**Not crossed.**
- **Dtype (HQ-0065, HQ-0066).** No dtype other than fp32, and no cast: an array that is not already `float32` is refused, never converted. No accumulation, oracle, tolerance or input distribution is chosen. The module compares nothing.
- **Llama dimensions (HQ-0064).** No value of H, d_h, the KV-head count or any Llama 3.2 1B dimension is used.
- **Isolation (OD-14).** The isolation of the model program's process stays open (ADR-0153 Boundaries). The module therefore takes the program as a path or a command prefix, as `hilclaw/harness/verification.py` does. A caller can then put a container start in front, and the module chooses no environment. It places no directory and starts no container.
- **Exposure.** No CLI, registry or MCP tool is added (ADR-0153 decision 1).
- **Data plane and dependencies.** No data-plane member, file, kind or version changes. No new external dependency: the standard library, `numpy` and `hilclaw.local_run`; the tests also use `hilclaw.model_build`.
- **D16.** No `claude` process is started.

**No open PR overlaps.**
- PR #244 touches `hilclaw/model_binding.py` and `tests/test_model_binding.py`.
- PR #186 touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.
- This task must not edit any of them. It also must not edit `hilclaw/gemm_contract.py`, `hilclaw/model_program.c` or `hilclaw/model_build.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming, size cap, test rules).
- `CLAUDE.md`: "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "브랜치·merge 절차" (code mode).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Decision §1 (lines 28-33), §3 (lines 40-46), §5 (lines 58-62), Consequences "A-13 reading" and "Code slices" (lines 87-88), Boundaries (lines 101-115).
- `hilclaw/model_program.c` lines 1-61: the header comment. It is the definition of the command line, the input file, the report, the end mark and the exit statuses this module speaks to.
- `hilclaw/model_build.py` lines 1-37: what the build step does and does not do.
- `hilclaw/harness/verification.py`: the module docstring (lines 1-90), `VerificationResult` (around lines 140-155) and `run_verification` (lines 224-284). These are the pattern for:
  - the program given as a path or a command prefix;
  - the result tuple with the runner's capture and `stdout` emptied;
  - the expected report length computed before any byte is read;
  - the classes raised before the start.
- `hilclaw/local_run.py`: `RunResult` (lines 47-73) and the docstring of `run` (from line 79).
- `tests/test_model_program.py` lines 1-130: the hand-written kernels, the session fixture that builds the program and the libraries (skip on non-POSIX; when clang is missing, skip locally and fail on CI), and the hand-made input bytes.
- `tests/test_gemm_contract.py` lines 386-396: the text `gemm_contract` must not appear in any new `hilclaw/*.py` file, docstrings included.

## Acceptance Criteria

The names below are this task's. The executor may rename them only if the review asks, and records any rename in Result.

1. **Module `hilclaw/model_run.py`** (Python; the language-choice line goes in Result and the commit body).
   - Its boilerplate docstring names ADR-0153 (decisions 1, 3 and 5) and the program's header comment as the definition of the file and report forms.
   - It lists what the module does not do: no binding check; no build; no directory placed and no input path chosen; no container or environment chosen; no time limit default; no comparison, reference or tolerance; no cast; nothing stored or retried.
   - The docstring must not contain the text `gemm_contract`.
2. **`encode_input(calls)` returns `bytes`.** It produces exactly the input file of the program's header comment: N, then for each call the kernel index, `m`, `k`, `n`, `a` and `b`, as `uint64` and `float32` in host byte order.
   - `calls` is a non-empty sequence of `(index, a, b)`.
   - `index` is an `int` (not `bool`) with 0 ≤ index < 2^64.
   - `a` and `b` are 2-D `numpy.ndarray` of dtype exactly `float32`, with `a.shape[1] == b.shape[0]` and every dimension ≥ 1. They are written row-major whatever their memory order (for example via `numpy.ascontiguousarray`), never converted to another dtype.
   - Refusals happen before any bytes are built, and the message names the call's position:
     - `TypeError` for a wrong type: `calls` not a sequence (a `str`/`bytes` included), an entry not a 3-item tuple or list, an index not `int`, or an array not an `ndarray`;
     - `ValueError` for a wrong value: no calls, an index out of range, a wrong dtype, a wrong number of dimensions, a zero dimension, or mismatched inner dimensions.
3. **`output_shapes(calls)`** returns the tuple of `(m, n)` of each call, after the same checks as item 2. Whether `encode_input` and `output_shapes` share one checking helper is the executor's choice; the checks must exist only once.
4. **`run_model_program(program, input_file, libraries, *, shapes, timeout_s, cwd=None, env=None)` returns a `ModelProgramResult`.**
   - **Command.** Exactly one process is started with `hilclaw.local_run.run`, with the command `(*prefix, input_file, *libraries)`. `prefix` is `(program,)` for a `str`/`os.PathLike` program, or the given non-empty sequence. Paths are handed over as `str` via `os.fspath`; a `bytes` path is refused with `TypeError`. `timeout_s`, `cwd` and `env` are handed over unchanged.
   - **Arguments.** `libraries` is a non-empty sequence of `str`/`os.PathLike` (not one `str`). `shapes` is a non-empty sequence of `(m, n)` pairs of `int` ≥ 1 (not `bool`). Both are checked before the start: `TypeError` for a wrong type, `ValueError` for an empty sequence or a dimension < 1. What `local_run.run` raises is passed on unchanged.
   - **`ModelProgramResult`** is a `NamedTuple` `(failed, outputs, run)`:
     - `failed` is `None` or a member of an `enum.Enum` `RunFailed` with `TIMEOUT`, `EXIT_STATUS` and `REPORT_FORM` (the spelling of ADR-0153's "run failed" is this slice's);
     - `outputs` is `None` or a tuple of `float32` arrays of shape `(m, n)`, one per entry of `shapes`, in order;
     - `run` is the `RunResult` with `stdout` replaced by `b""`.
   - **Judgement, in this order.**
     1. A timed-out run is `TIMEOUT`.
     2. A non-zero exit status (a signal included) is `EXIT_STATUS`.
     3. Otherwise the report must be exactly Σ 4·m·n bytes followed by the end mark `b"end\n"`, else `REPORT_FORM`. This covers a short report, extra bytes, and a wrong or missing end mark.
     - In every failed case `outputs` is `None`, whatever the report holds.
   - **Report reading.** The expected length is computed from `shapes` alone and compared before the report is parsed. No array is allocated from the report's length.
   - **Outputs.** Each output is a fresh array that owns its memory (not a view of the report). NaN elements are passed through as they are: the module judges no value.
5. **`parse_report(report, shapes)`** returns the outputs tuple for a complete report or `None` otherwise. `run_model_program` uses it for its third check.
   - `report` must be exactly `bytes`. A `bytearray`, a `memoryview` or a subclass raises `TypeError`, as `verification.judge_report` does.
   - `shapes` is checked as in item 4.
6. **Tests `tests/test_model_run.py`**, in two groups.
   - **Without a process** (run on every platform):
     - `encode_input` gives exactly the bytes of a hand-made encoding (as `tests/test_model_program.py` `input_bytes` builds them), for several calls, including an `a` given in Fortran order;
     - every `TypeError`/`ValueError` path of items 2, 3, 4 and 5, among them a `float64` array, a 1-D array, a `bool` index, an index of 2^64, a zero dimension, mismatched inner dimensions, an empty `calls`, a `str` given as `libraries`, a `bytes` path, and a `bool` in `shapes`;
     - `parse_report` on a complete report, on a report one byte short, on one byte extra, on a wrong end mark, on an empty report, and on a NaN element passed through;
     - `run_model_program` with `local_run.run` replaced by a recorder. These check: the exact command for a path program and for a command prefix; `timeout_s`, `cwd` and `env` handed over; each `RunFailed` member (timeout, a non-zero status with a complete report, status 0 with an incomplete report); `stdout` emptied in `run`; and outputs that are not views of the report.
   - **With real clang** (POSIX only, the fixture pattern of `tests/test_model_program.py`; kernels and the program built with `hilclaw.model_build`):
     - **happy**: two kernels with different results ("plain" and "plus one") and several calls of different shapes, so that `encode_input` → a file in `tmp_path` → `run_model_program` → outputs equal the `numpy` products computed in the test from small-integer inputs (exact in `float32`, no tolerance);
     - **negative**: an index out of range gives `EXIT_STATUS` with the program's status 5, and a library without `hilclaw_gemm` gives `EXIT_STATUS` with status 6;
     - **timeout**: a kernel that never returns, with a short `timeout_s`, gives `TIMEOUT`.
7. CLAUDE.md test rules hold:
   - package line and function coverage ≥ 80%, ruff clean (`ruff check .` and `ruff format --check .`), and a test file for the new module;
   - every public function of the module is tested; local `pytest` passes;
   - if the local machine has no POSIX clang (native Windows), the clang tests skip locally and must pass on CI;
   - CI must be green before the self squash-merge.
   - DRIVER §5 naming applies: branch `claude/T-0421-<slug>`, PR title with `T-0421`, and `Task: T-0421` as the last line of the PR body.

## Out of Scope

- The build directory outside both checkouts and its removal, the builds through `model_build`, the outcome `build failed`, and the one function that runs a list of kernels and calls end to end (next task).
- The binding check, `hilclaw/model_binding.py`, joining with `BindingCheck.calls`, and anything of HQ-0067 or PR #244.
- Weights, the embedding lookup, buffers across calls, the KV cache, passes, the generation loop, token selection, and kinds other than fp32 `gemm` (ADR-0153 slice 2; P2-11).
- The container of ADR-0144, time or memory limits as values (OD-14), and any change to `hilclaw/model_program.c`, `hilclaw/model_build.py` or `hilclaw/gemm_contract.py`.
- Edits to `ARCHITECTURE/`, `tests/test_gemm_contract.py` and the files of PR #186.

## Follow-ups

- Next task (candidate T-0422, completing slice 1's build-and-run path): a function, in `hilclaw/model_run.py` or a module next to it, that does the whole run. Its kernel argument takes objects with `sources` and `flags`, so that, once HQ-0067 is answered, a later task can hand it the `calls` of T-0419's `BindingCheck`. It:
  - makes a build directory outside both checkouts (the `hilclaw.checkout_boundary` test, as `hilclaw/scratch.py` does);
  - builds each kernel with `build_kernel_library` and the program with `build_model_program`;
  - returns the outcome `build_failed` (kernel index, compiler output) for a failed build;
  - writes the input file with `encode_input` and runs the program with `run_model_program`;
  - removes the directory.
- Runtime acceptance item (lxvii) of ADR-0153 is to be asked "once code slice 1 has landed". It is not asked at the end of this task.

## Result

- **Outcome**: DONE. PR #246 (branch `claude/T-0421-model-program-run-and-report`), squash-merged by the executor as `258731c` after 2 review rounds (round 1: Approve with one Minor finding, addressed; round 2: Approve, no findings). CI green at the reviewed head `387b0a5` (C gate, Coverage gate, Python 3.11/3.14, Test presence, sh gate).
- **Change**: `hilclaw/model_run.py` (new, 294 lines) and `tests/test_model_run.py` (new). No other file. Names are those of the task; no rename. `END_MARK` is also public.
- **Language**: Python, because the host side hands `numpy` arrays and one process to `hilclaw.local_run`, as the harness's Python side does (ADR-0153 decision 2).
- **Executor choices**: one checking helper each for calls and for shapes, shared by `encode_input`/`output_shapes` and by `parse_report`/`run_model_program`. `calls`, `shapes`, `libraries` and a command-prefix `program` must be `collections.abc.Sequence` (an iterator is refused with `TypeError`). Every prefix element, the input file and every library go through one path check: `str` or `os.PathLike` whose `os.fspath` is `str`, else `TypeError`. A big-endian `float32` dtype on a little-endian host is refused as a wrong dtype. Checks run in the order shapes, program, input file, libraries; `parse_report` checks shapes before the report type.
- **Review round 1 fix**: the test of a failed run with a complete report now pins the expected outcome per case and adds a timed-out run with a status.
- **Local runs**: native Windows full `pytest`: 26693 passed, 907 skipped (clang tests skip); `ruff check .` and `ruff format --check .` clean; `hilclaw/model_run.py` 100% line and branch coverage from the platform-independent tests. Under WSL with clang and Python 3.12, `tests/test_model_run.py`, `tests/test_model_program.py` and `tests/test_model_build.py` passed (204).
- **Follow-ups**: as listed (candidate T-0422, build-and-run function; runtime acceptance item (lxvii) after slice 1 lands).
