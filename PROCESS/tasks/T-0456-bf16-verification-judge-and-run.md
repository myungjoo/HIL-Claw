---
id: T-0456
title: Add hilclaw/harness/bf16_verification.py, which judges the report of a bf16 verification executable and runs one (ADR-0163 decision 8, code slice 5)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0455]
touchesFiles: [hilclaw/harness/bf16_verification.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification.py]
estimatedSize: {loc: 250, files: 2}
hq: []
---
## Why

**State on `main` `e11ce4b`.** ADR-0163 (T-0451, `c004ccc`) records the verification run of one built bf16 kernel on `cpu_standin` for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. Four code slices have landed:
- T-0452 (`cafb152`): the array side, `hilclaw/harness/bf16_verification_arrays.py` (inputs, check value, widening, reference, counts).
- T-0453 (`5e40098`) and T-0454 (`d6a2a0f`): the shared header `bf16_verification.h` and the four verification programs, one per kind.
- T-0455 (`93c49c2`): the build, `hilclaw/harness/bf16_verification_build.py`.

**This task is the fifth slice: the Python side over a report and over a built executable.** ADR-0163 decision 8 defines the report, the completed and broken conditions and the verdict "as ADR-0017 decision 7", and its Consequences list "reading and judging the report" among the code slices. The array module explicitly does not "split or read a report, decide completed or broken, or give a verdict over draws". Nothing in the package does that yet; only the tests of the programs split reports by hand. This slice adds the counterpart of `hilclaw/harness/verification.py` (the first case's module, 323 lines, mostly docstring) for the four bf16 kinds. After it, a bf16 kernel can be built and verified end to end by the package, which the calibration slice (ADR-0163 decision 9) and later the P2-14 path need.

**Reuse to stay under the size cap.** The result types of the first case (`Broken`, `Verdict`, `Judgement`, `VerificationResult`) and its `END_MARK` say exactly what ADR-0163 decision 8 asks ("as ADR-0017 decision 7"), so the new module reuses them by import instead of defining copies; a caller then handles one set of result types for both runs. The array work is all in `bf16_verification_arrays`. That leaves the argument checks, the form check, the per-draw loop and the process start: about 250 lines with the docstring, in 2 files (cap: 300 lines in 5 files). If the executor finds it over the cap, it keeps `program_arguments` and `judge_report` here and moves `run_bf16_verification` to a follow-up task (DRIVER §5).

**Later slices (not here):** the twelve calibration kernels of ADR-0163 decision 9 and their tests; RoPE and SDPA (a second harness record); the bf16 timing run.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items and P2-14 needs them, so the D18 rule does not apply. Unresolved HQs still hold the round-loop items and P2-5 (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as for T-0451 to T-0455.

**D16.** The module starts a local process through `local_run.run`. The tests use a Python stand-in executable written by the test (the `StandIn` pattern of `tests/harness/test_verification.py`) and, where `clang` exists, stub kernels the tests write. Nothing starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules. Branch `claude/T-0456-<slug>`; commit trailer `Task: T-0456`; code mode, so a Draft PR whose body ends with `Task: T-0456`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화" (a module docstring may be long), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, code mode).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 3 (lines 55-65): the command line per kind and the `eps` constant;
  - decision 4 (lines 67-88) and decision 6 (lines 95-110): what the array side computes, and that a check-value disagreement is broken, never a fail;
  - decision 7 (lines 112-121): the predicate, tolerance checks before a process is started, no tolerance passed to the program;
  - decision 8 (lines 123-127): the channel, the content, the length draws · (4 + 2·m·n) + E, completed/broken/pass/fail, and what the Python side returns;
  - decision 10 (lines 145-155) and Boundaries (lines 195-207).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md` decision 7 (lines 70-79), which ADR-0163 decision 8 applies.
- `hilclaw/harness/verification.py`: the whole file (323 lines). It is the model: the docstring and its conventions, `program_arguments`, `judge_report`, `run_verification`, `_judgement`, `_counts` and `_digits`.
- `hilclaw/harness/bf16_verification_arrays.py`: the whole file (237 lines): `KINDS`, `draw_inputs(kind, dims, ...)`, `check_value`, `reference`, `count_failures`, and the private `_shapes` and `_kind` with the error class it reuses.
- `hilclaw/harness/verification_arrays.py`: `VerificationArgumentError`, `Counts`, `check_tolerance`, `SEED_LIMIT` (lines 60-170).
- `hilclaw/harness/bf16_verification_gemm.c`: the header comment (lines 1-38), for the command line, the report and the exit statuses. The other three programs differ only in `<m> <n> <draws> <seed>` and their operands.
- `hilclaw/harness/bf16_verification_build.py`: the docstring and `build_bf16_verification_executable`, for the real-clang tests.
- `hilclaw/local_run.py`: `RunResult` and the `run` docstring (lines 47-100).
- `hilclaw/harness/__init__.py`: the package docstring (lines 1-25).
- `tests/harness/test_verification.py`: the whole file (887 lines). It is the model for the tests: the `StandIn` executable, the report builders (`rounded_references`, `report_of`, `passing_report`), the `verify`/`judge` helpers, the broken conditions, the refusals and their order.
- `tests/harness/test_bf16_verification_programs.py`: lines 1-330, for the helpers that build expected reports per kind (`inputs`, `copied_first`, `unwritten`, `expected_report`, `split`), the stub kernels per kind and the session build fixture with `-lm` in `trailing_flags`.
- `tests/harness/test_bf16_verification_build.py`: the real-clang tests, for the skip/fail-on-CI pattern without `clang`.

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_verification.py`**, in Python (it uses NumPy through the array side as `verification.py` does; say this in one line of the commit body). Its public names:
   - **`Broken`, `Verdict`, `Judgement`, `VerificationResult`, `END_MARK`**: the objects of `hilclaw.harness.verification`, imported, not redefined (identity holds: `bf16_verification.Broken is verification.Broken`).
   - **`program_arguments(kind, dims, *, draws, seed)`**: returns the program arguments as a tuple of `str` in the order of ADR-0163 decision 3 — the dimensions of `dims` (`(m, k, n)` for `gemm`, `(m, n)` otherwise), then `draws`, then `seed` — spelled in decimal digits as `verification.program_arguments` spells them.
   - **`judge_report(report, kind, dims, *, draws, seed, rtol, atol)`**: returns a `Judgement` for one report.
   - **`run_bf16_verification(executable, kind, dims, *, draws, seed, rtol, atol, timeout_s, cwd=None, env=None)`**: starts one process `<executable prefix> <program_arguments>` with `local_run.run`, handing `timeout_s`, `cwd` and `env` over unchanged, and returns a `VerificationResult`.
   - No parameter has a default except `cwd` and `env`; `draws`, `seed`, `rtol`, `atol` and `timeout_s` are keyword-only.
2. **Argument checks**, all raising `VerificationArgumentError` before any byte of a report is looked at and before anything is started, in this order: `kind` (exactly a `str` of `bf16_verification_arrays.KINDS`; a `str` subclass, `"GEMM"`, `bytes` and `None` are refused), `dims` (exactly a `tuple` of the kind's length whose items are exactly `int` ≥ 1 and writable in decimal digits; a `bool`, a `float`, a list and a wrong length are refused), `draws` (1 ≤ draws < 2**64), `seed` (0 ≤ seed < 2**64), then the tolerance through `check_tolerance`. Then `judge_report` raises `TypeError` for a `report` that is not exactly `bytes`, and `run_bf16_verification` raises `TypeError`/`ValueError` for an `executable` as `run_verification` does; what `local_run.run` raises is passed on. Reusing `bf16_verification_arrays._shapes`/`_kind` and `verification._digits` is allowed and preferred to a copy.
3. **Form check.** With `m` and `n` the first and last item of `dims`, a complete report has exactly `draws * (4 + 2*m*n) + 4` bytes and ends with `END_MARK`. Any other report is `Broken.REPORT_FORM`. The length is computed from `m`, `n` and `draws` alone and compared before any byte is read; nothing is allocated from the expected length.
4. **Per draw, in order** (as `verification._judgement`/`_counts`): regenerate the operands with `bf16_verification_arrays.draw_inputs(kind, dims, seed=seed, draw=d)`; read the 4-byte `uint32_t` check value in host byte order and compare it with `check_value(first, second)` — the first disagreement makes the result `Broken.CHECK_VALUE` and drops the counts taken so far; read the `m*n` `uint16` output patterns after it as an (m, n) array and take `count_failures(output, reference(kind, first, second), rtol=rtol, atol=atol)`. No array of a draw is kept for the next.
5. **Verdict and result**, as ADR-0163 decision 8 and ADR-0017 decision 7: a completed report passes iff no element of any draw failed; `counts` holds one `Counts` per draw. A broken result has `verdict` and `counts` `None`. `run_bf16_verification` returns `Broken.TIMEOUT` for a timed-out process and `Broken.EXIT_STATUS` for a non-zero status or a signal, whatever was written, and otherwise the judgement of the standard output; `run` is the runner's `RunResult` with `stdout` replaced by `b""`, in every case. Nothing returned holds an element, index or deviation of the inputs, reference or output.
6. **Module docstring**, in the form of `verification.py`'s: the rule (ADR-0163 decisions 3, 6, 7 and 8, through ADR-0017 decision 7); the command line per kind; the report form and its length; the conventions (order of the broken conditions; length before content; one draw at a time; one implementation shared by `judge_report` and `run_bf16_verification`; `report` exactly `bytes`; `run` with empty `stdout`; `executable` as a path or a command prefix; the error classes); and what the module does not do — it builds nothing and holds no program path; it holds and defaults no tolerance, seed, number of draws, dimension or time limit; it passes no tolerance and no `eps` to the program; it sets no environment variable and parses no standard error; it does not retry, repair or store anything; it registers no kind with `correctness.check`, `spec.write` or the instance start (ADR-0163 Boundaries).
7. **`hilclaw/harness/__init__.py`**: add the new module to the docstring next to the bf16 sources and the build, and correct the sentence about the modules that import `numpy`: they become four (`verification_arrays`, `verification`, `bf16_verification_arrays`, `bf16_verification`), and the statement must stay true. `bf16_verification_build` still imports no `numpy` (its test checks that). No other Python module changes behaviour.
8. **Size**: at most 300 changed lines outside tests, in at most 5 files. Expected: the new module and the `__init__.py` docstring.
9. **Tests**, in the new file `tests/harness/test_bf16_verification.py`. Follow `tests/harness/test_verification.py` and D12 (DRIVER §5): happy, error, branch and negative cases, and every public name of the new module. Parametrize over the four kinds where the behaviour is the same. Build expected reports in the test from `bf16_verification_arrays` (check value per draw, then output patterns, then `end\n`). At least:
   - **Reused types**: the five names are the objects of `hilclaw.harness.verification`.
   - **`program_arguments`**: order and spelling per kind (five for `gemm`, four otherwise), bounds of `draws` and `seed` (0, 1, 2**64 − 1, 2**64), and every refusal of AC 2 with `VerificationArgumentError`; no defaults; keyword-only parameters.
   - **Pass**: per kind, a report whose outputs are the reference rounded to bf16 (round-to-nearest-even, written in the test from the float64 reference through float32 bit operations) passes under a tolerance of a relative 2^−8 plus a small `atol` for `gemm`, with one `Counts(0, 0)` per draw; also with one draw and with a dimension of 1.
   - **Fail**: one element changed outside the tolerance fails with the right per-draw count; failing draws are counted apart; a NaN or infinity pattern (for example the `0x7FC0` fill) fails and is counted as non-finite; an all-fill (unwritten) output fails in every draw; `rtol = atol = 0` passes an output equal to the reference element for element, for a kind, seed and small shape the test chooses so that every reference element is exact in bf16 (for example `elementwise_add` at a 1 × 1 shape where the two fractions sum to an even number of 1/256).
   - **Broken by form**: a short report, a long report, a wrong end mark, the report of another `draws`, and an empty report; the form follows from `m`, `n` and `draws` alone (a `gemm` report with another `k` but the same length is judged by check value, not by form).
   - **Broken by check value**: a wrong check value in the first and in a later draw, and the report of another seed or another kind of the same length.
   - **`run_bf16_verification` with a stand-in** (the `StandIn` pattern, a Python script started with `sys.executable`): the process gets exactly the program arguments; `cwd` and `env` reach it; no environment variable is set by default; a timeout and a non-zero exit are broken whatever was written; a death by signal after a passing report is broken (POSIX only); `run.stdout` is `b""` while the other members are passed on; `executable` as one path and as a list prefix; an empty prefix, a wrong type and a missing program raise before or at start as in the model tests; bad arguments and bad tolerances raise and start nothing; the time-limit errors are those of `local_run.run`.
   - **Real clang, small** (skip without a POSIX system or without `clang`, fail on CI without `clang`, as `test_bf16_verification_build.py` does): for `elementwise_add`, build with `build_bf16_verification_executable` a stub kernel that computes the sum in `float` and rounds it to bf16 with round-to-nearest-even, and one that copies its first operand; run both with `run_bf16_verification` at a small shape and two draws. The first passes under `rtol = 2**-8`, `atol = 0`, and the second fails. Keep the number of `clang` builds to these two; no test should take more than a few seconds on a CI runner.
10. **No other behaviour change**:
    - Leave unchanged the bf16 programs and header, `bf16_verification_arrays.py`, `bf16_verification_build.py`, the first case's files (`verification_program.c`, `verification_build.py`, `verification.py`, `verification_arrays.py`), `local_run.py`, the contract modules, the existing tests and the CI workflow.
    - Add no dependency.
    - The local `pytest` and `ruff` runs are green, and coverage of `hilclaw/` stays at or above 80% for lines and functions.
11. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0456`, whose body ends with `Task: T-0456`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least: the report length formula and that `m`, `n` are taken from the right items of `dims` for `gemm`; the order of the refusals; the order of the broken conditions; that the result types are the first case's objects; that no tolerance or `eps` reaches the program; that the `__init__.py` statement about `numpy` is true; and that no existing module changed.

## Out of Scope

- The calibration kernels of ADR-0163 decision 9 (three per kind under `tests/harness/calibration/`), and any change to `test_calibration.py` or the CI calibration step. That is the next slice.
- Any change to the bf16 programs, the header, `bf16_verification_arrays.py`, `bf16_verification_build.py` or the first case's modules.
- RoPE and SDPA, the bf16 timing run and its build, and fp16.
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Default tolerances, seeds, draws, time limits or build flags (ADR-0163 Boundaries; HQ-0033, HQ-0034).
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next slice: the calibration of ADR-0163 decision 9 — conforming, failing and violating C kernels per kind (twelve in all; the bf16 `gemm` gets its own three beside the fp32 ones) with tests that build each with `build_bf16_verification_executable` and judge it with `run_bf16_verification` under the test's own seed, draws and tolerance. It will likely need splitting by kind (two kinds per task) to respect the 5-file cap.

## Result
- PR #271, squash-merged as `4162276` after 1 review round (Approve, no change requested); CI green (Python 3.11/3.14, coverage, C, sh, test presence).
- Added `hilclaw/harness/bf16_verification.py` (256 lines: `program_arguments`, `judge_report`, `run_bf16_verification`; `Broken`, `Verdict`, `Judgement`, `VerificationResult`, `END_MARK` imported from `verification`) and corrected the `hilclaw/harness/__init__.py` docstring (four `numpy` modules); 267 changed lines outside tests in 2 files. Tests: `tests/harness/test_bf16_verification.py`, the new module at 100% line coverage; `hilclaw/` lines 97%.
- Language: Python, because the module judges reports with NumPy through the array side, as `hilclaw.harness.verification` does.
- Reviewer note (Info, no change): the check value does not tell `gemm` `(m, k, n)` from `(n, k, m)`, nor `(m, n)` from `(n, m)` for `elementwise_add`/`swiglu`: the flat word sequence is the same, so such a report passes the form and check-value conditions and is judged on its counts. This follows from ADR-0163 decisions 4 and 6 and the array side, not from this slice; a test pins the behaviour.
- Follow-ups: none beyond the calibration slice listed above.
