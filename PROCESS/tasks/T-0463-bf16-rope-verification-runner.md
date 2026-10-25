---
id: T-0463
title: Add the runner side of the bf16 RoPE verification run, hilclaw/harness/bf16_rope_verification.py (arguments, judging a report with P, starting the executable with the rows on standard input; ADR-0164 code slice 3, second half)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0460, T-0461, T-0462]
touchesFiles: [hilclaw/harness/bf16_rope_verification.py, hilclaw/harness/bf16_rope_arrays.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_rope_verification.py]
estimatedSize: {loc: 200, files: 3}
hq: []
---
## Why

**State on `main` `6ecc824a`.** ADR-0164 (T-0459, `f9b8096`) records how one built bf16 RoPE kernel (kind `rope`) is verified on `cpu_standin`. Its Consequences (line 136) list four code slices:
- slice 1 is done: T-0460 (`48f1d05`) gave `hilclaw.local_run.run` the optional `stdin_data` argument;
- slice 2 is done: T-0461 (`4043e70a`) added `hilclaw/harness/bf16_verification_rope.c` and `rope` in `bf16_verification_build.PROGRAM_SOURCES`;
- slice 3, first half, is done: T-0462 (`6297bf58`) added `hilclaw/harness/bf16_rope_arrays.py` (`TABLE_CONSTANTS`, `table_rows`, `draw_x`, `check_value`, `reference`, `count_failures`).

**This task is the second half of slice 3**: "judging the report with P and the bytes on standard input". It adds the runner module `hilclaw/harness/bf16_rope_verification.py`. It mirrors `hilclaw/harness/bf16_verification.py`, the runner of ADR-0163's kinds, and differs from it in three ways:
- the shape is `(m, h, d)`;
- there is a start position P (`start`);
- the rows from `table_rows` are sent as the process's standard input and are used again for the check value and the reference.

After this task the harness can verify a built `rope` kernel end to end. Slice 4, the three calibration kernels, is the next task.

**Why a new module and not `bf16_verification.py`.** That module's `kind` parameter accepts the keys of `bf16_verification_arrays.KINDS` only, and its tests refuse `"rope"` (`BAD_KINDS` in `tests/harness/test_bf16_verification.py`). Adding `start` and standard input there would add a branch to every function. T-0462 chose the pair `bf16_rope_arrays.py` / `bf16_rope_verification.py` for that reason. The test file of the new module is `tests/harness/test_bf16_rope_verification.py`, which does not exist yet; the CI test-presence check requires it.

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items that P2-14 needs, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as it did for T-0451 to T-0462.

**D16.** The module is Python and starts only an executable the caller has already built. Its tests use a Python stand-in process and, where `clang` exists on a POSIX machine, a verification executable built from a test-local kernel. Nothing needs `claude`, a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules.
  - For this task: branch `claude/T-0463-<slug>`; commit trailer `Task: T-0463`; code mode, so a Draft PR whose body ends with `Task: T-0463`.
- `CLAUDE.md`, "상시 규칙":
  - "코멘트 최소화";
  - "도구 계층 언어 정책";
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`:
  - decision 3 (lines 45-50): the rows on standard input; a short or long input is a non-zero status and the run is broken; the Python side keeps its own copy;
  - decision 4 (lines 52-58): P is a run parameter with no default and is not on the command line; refusal before a process is started;
  - decision 5 (lines 60-63): the table is built once per run;
  - decision 7 (lines 70-76): the command line `<m> <h> <d> <draws> <seed>`;
  - decision 9 (lines 82-86): the check value over `x` and the rows; a disagreement is broken, never a fail;
  - decision 10 (lines 88-91): the report length draws · (4 + 2·m·h·d) + 4 and the verdict;
  - decision 12 (lines 99-108): the parameters, none with a default;
  - decision 13, item 4 (line 115): cost;
  - Consequences, line 136.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`: decisions 3, 7 and 8 (the spelling of the arguments, the comparison, the report and the verdict).
- `hilclaw/harness/bf16_verification.py`: the whole file (256 lines). It is the model for the docstring, the conventions, `program_arguments`, `judge_report`, `run_bf16_verification`, `_judgement` and `_counts`.
- `hilclaw/harness/bf16_rope_arrays.py`: the whole file (221 lines), especially `table_rows`, `_dims` and the start check.
- `hilclaw/harness/verification.py`:
  - lines 95-160 (`END_MARK`, `Broken`, `Verdict`, `Judgement`, `VerificationResult`);
  - lines 312-323 (`_digits`).
- `hilclaw/local_run.py`: `run` and its docstring (lines 85-200), in particular `stdin_data` and what happens when a process exits before reading all of it.
- `hilclaw/harness/bf16_verification_rope.c`: the header comment (lines 1-48), covering the command line, standard input, the report and exit status 5.
- `hilclaw/harness/__init__.py`: the whole file (29 lines).
- `tests/harness/test_bf16_verification.py`:
  - lines 1-180: the stand-in process and the helpers;
  - lines 240-330: the refusal tests;
  - lines 440-560: the form and check-value tests;
  - lines 900-937: the real-`clang` tests.
- `tests/harness/test_bf16_verification_rope.py`:
  - lines 1-60 and 220-280: the kernel template, the `executable` fixture and its skip rules;
  - lines 123-140: the stub kernels, including `copy-x`.
- `tests/test_rope_table.py` lines 586-593: only `harness/bf16_rope_arrays.py` may contain the text `rope_table`.
- `.github/workflows/ci.yml` lines 117-146: the test-presence check.

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_rope_verification.py`**, in Python. The commit body says why in one line: it is the runner next to `bf16_verification.py` and reuses its result types and `local_run.run`.
   - The module docstring names ADR-0164 as the rule and states:
     - the command line;
     - the standard input: the 4·m·d bytes of `table_rows(dims, start=start)`, sent once per run;
     - the complete report length draws · (4 + 2·m·h·d) + 4;
     - the conventions of `bf16_verification.py`, with `dims` and `start` in place of `kind` and `dims`, by reference and not restated;
     - what the module does not do: it builds nothing and holds no path of a program. It holds no tolerance, seed, number of draws, dimension, start position or time limit and gives none of them a default. It passes no tolerance and no P to the program, sets no environment variable and parses no standard error. It does not retry, repair, store or cache anything, writes no file and returns no element of the inputs, rows, reference or output. It registers `rope` with neither `correctness.check`, `spec.write` nor the instance start (ADR-0164 Boundaries).
   - It imports `END_MARK`, `Broken`, `Judgement`, `Verdict`, `VerificationResult` and `_digits` from `hilclaw.harness.verification` and re-exports the five public names in `__all__`, as `bf16_verification.py` does. It does not copy them.
   - **The text `rope_table` must not appear anywhere in the file, docstrings included.** `tests/test_rope_table.py::test_the_module_is_named_only_by_the_bf16_rope_verification_arrays` requires this. The module gets rows only through `bf16_rope_arrays.table_rows`, and that test stays unchanged.
2. **`program_arguments(dims, *, draws, seed)`** returns the tuple of `str` `(m, h, d, draws, seed)` in decimal digits, in the spelling of `bf16_verification.program_arguments`.
   - `dims` is checked by the rules of `bf16_rope_arrays` (exactly a tuple of three `int`s, each at least 1, `bool` refused, `d` even), reusing its checker and not copying it.
   - `draws` must satisfy 1 ≤ `draws` < 2**64 and `seed` must satisfy 0 ≤ `seed` < 2**64.
   - The checks run in parameter order and raise `VerificationArgumentError`. This includes an `int` that the interpreter cannot write in decimal digits (`_digits`).
   - `start` is **not** a parameter (ADR-0164 decision 4: P is not on the command line).
3. **Start check without building.** All arguments must be refused before the table is built or a process is started. To allow this, the start check of `bf16_rope_arrays.table_rows` (an `int` ≥ 0, `bool` refused, and (start + m)·d ≤ 2**53 − 1) may move into a private helper of that module, which `table_rows` and the new module both call.
   - The messages and behaviour of `table_rows` stay as they are, and `tests/harness/test_bf16_rope_arrays.py` passes unchanged.
   - This is the only change to `bf16_rope_arrays.py`.
4. **`judge_report(report, dims, *, start, draws, seed, rtol, atol)`** returns a `Judgement`.
   - Checks before any byte of `report` is looked at and before the table is built, in this order:
     - `dims`, `draws` and `seed` as in `program_arguments`;
     - `start` as in AC 3;
     - the tolerance by `verification_arrays.check_tolerance`;
     - `TypeError` for a `report` that is not exactly `bytes`.
   - The length is then compared with draws · (4 + 2·m·h·d) + 4 and the end mark is looked for; either failing gives `Broken.REPORT_FORM`. The length is computed from `dims` and `draws` alone, and nothing is allocated from it.
   - Only then are the rows built, **once**, with `table_rows`. For each draw in order:
     - `x` is drawn with `draw_x`;
     - the reported `uint32` (host order) is compared with `check_value(x, rows)`, and the first disagreement gives `Broken.CHECK_VALUE`, with the counts taken so far dropped;
     - the output (2·m·h·d bytes, host order) is counted against `reference(x, rows)` with `bf16_rope_arrays.count_failures`.
   - The verdict is `PASS` if no element of any draw failed, otherwise `FAIL`, with the tuple of `Counts`.
   - `TIMEOUT` and `EXIT_STATUS` are never returned. No array of a draw is kept for the next draw.
   - All parameters after `dims` are keyword-only, and none has a default.
5. **`run_bf16_rope_verification(executable, dims, *, start, draws, seed, rtol, atol, timeout_s, cwd=None, env=None)`** returns a `VerificationResult`.
   - Checks before anything is started and before the table is built, in this order:
     - the arguments as in `judge_report`;
     - `TypeError` for an `executable` that is neither a path nor iterable;
     - `ValueError` for an empty `executable` sequence.
     These follow `run_bf16_verification`.
   - Then the rows are built once with `table_rows`. One process `(*prefix, *program_arguments(...))` is started with `local_run.run(..., timeout_s=timeout_s, cwd=cwd, env=env, stdin_data=rows.tobytes())`.
   - The **same** rows array is used for every draw's check value and reference. The table is not built a second time (a test shows this, for example by counting calls of `table_rows` through `monkeypatch` on the new module's reference to it).
   - Outcomes:
     - a timeout gives `Broken.TIMEOUT`;
     - a non-zero exit status gives `Broken.EXIT_STATUS`, which includes the program's status 5 for wrong standard input;
     - otherwise the judgement is that of AC 4, through one shared private implementation used by both public functions.
   - `run.stdout` is replaced by `b""`, and every other member of the run result is passed on unfiltered.
   - Errors of `local_run.run` are passed on.
6. **`hilclaw/harness/__init__.py`**: name the new module in the docstring as the Python side of the bf16 RoPE verification run of ADR-0164 over an executable that is already built. Keep the `numpy` claim true: the new module counts as a numpy-importing module only if it imports `numpy`, so state the right number either way.
7. **Size**: at most 300 changed lines outside tests, in at most 5 files.
8. **Tests: new file `tests/harness/test_bf16_rope_verification.py`.** Follow D12 (DRIVER §5): happy, error, branch and negative cases, and every public function of the new module. Use the Python stand-in-process pattern of `tests/harness/test_bf16_verification.py`. Extend the stand-in so that it also records the bytes it read on standard input, and so that it can exit without reading them. Keep shapes and positions small (P + m ≤ 128 at d ≤ 64) so the suite stays fast. At least:
   - **Public names**:
     - `__all__`;
     - the five result names are the very objects of `hilclaw.harness.verification`.
   - **`program_arguments`**:
     - order and spelling, for example `(3, 2, 4)`, `draws=2`, `seed=2**64 - 1`;
     - the bounds;
     - each argument refused in parameter order (list `dims`, 2 or 4 entries, `bool`, `0`, negative, `float`, odd `d`; `draws` 0, 2**64, `True`, `1.0`, `None`; `seed` −1, 2**64, `1.5`, `"7"`, `None`);
     - no defaults;
     - keyword-only parameters.
   - **`judge_report`, happy path**:
     - a report built in the test from `draw_x`, `table_rows`, `check_value` and the bf16 rounding of `reference` passes with zero failures under `atol = 2**-8 + 2**-21`, `rtol = 0`;
     - test this for start 0 and for start 127 with m = 1, and for one draw and for several draws;
     - an output equal to `x` at start 0 and m = 1 passes (row 0 is c = 1, s = +0).
   - **`judge_report`, fail**:
     - one element outside the tolerance in one draw gives `FAIL` with that draw's count only;
     - `0x7FC0` elements are counted as failed and non-finite.
   - **`judge_report`, broken**:
     - every wrong form gives `REPORT_FORM` and no check value is computed: one byte short, one byte long, a missing end mark, empty, and the report length of another `h`;
     - a check value that disagrees in the first, middle or last draw gives `CHECK_VALUE`;
     - a report made with another seed gives `CHECK_VALUE`;
     - **a report made for another `start` with the same length gives `CHECK_VALUE`** (the rows are inside the check value).
   - **`judge_report`, refusals**: every refusal of AC 4, raised before the report or the table is touched. Show that the table was not built, for example with a `monkeypatch` on `bf16_rope_arrays.table_rows` or on the new module's reference to it. This includes:
     - `start` negative, `bool`, `float` or `None`;
     - (start + m)·d above 2**53 − 1;
     - a refused tolerance;
     - a `bytearray` or `memoryview` report giving `TypeError`.
   - **`run_bf16_rope_verification` with the stand-in**:
     - the argv is exactly `program_arguments(dims, draws=..., seed=...)`, and P appears nowhere in it;
     - the bytes received on standard input equal `table_rows(dims, start=start).tobytes()`;
     - `cwd` and `env` are passed through;
     - a passing report gives a completed `PASS`;
     - a timeout gives `TIMEOUT`;
     - a non-zero status (5, and a signal on POSIX) gives `EXIT_STATUS` whatever was written;
     - a wrong form or a wrong check value is broken;
     - a stand-in that exits without reading standard input gives a result, not an exception;
     - `run.stdout == b""` and `stderr` is kept;
     - the table is built once per call;
     - every refusal of AC 5 happens before anything is started (the stand-in's record file does not exist);
     - an empty sequence and a non-iterable executable;
     - `ProgramNotFoundError` from `local_run` is passed on.
   - **Real `clang`** (POSIX only; skipped without `clang` locally and failing on CI without it, as in `test_bf16_verification_rope.py`):
     - build with `build_bf16_verification_executable("rope", ...)` a test-local conforming kernel: a binary32 evaluation of y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c, rounded to bf16 by round-to-nearest-even on the bit pattern, with no `<math.h>`;
     - build a test-local `copy-x` kernel the same way;
     - the conforming kernel gives `PASS` at, for example, `dims=(3, 2, 4)`, `start=0`, `draws=2`, `atol = 2**-8 + 2**-21`, `rtol = 0`, and at `dims=(1, 2, 64)`, `start=127`;
     - the `copy-x` kernel gives `FAIL` at `dims=(3, 2, 4)`, `start=0` (rows 1 and 2 are not the identity).
     These are not the calibration kernels of ADR-0164 decision 11 and are not placed under `tests/harness/calibration/`.
   - Do not add tests that target test code (D12 ⑤).
9. **No other behaviour change**:
   - Leave these files unchanged: `bf16_verification.py`, `bf16_verification_arrays.py`, `bf16_verification_build.py`, `bf16_verification.h`, the five C programs, `rope_table.py`, `rope_bf16_contract.py`, `local_run.py`, `verification.py`, every existing test file (including `tests/test_rope_table.py` and `tests/harness/test_bf16_rope_arrays.py`) and the CI workflow.
   - `bf16_rope_arrays.py` changes only as AC 3 allows.
   - Add no dependency.
   - The local `pytest` (with coverage at or above the 80 % line and function gates) and `ruff check` / `ruff format --check` are green.
10. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0463`, whose body ends with `Task: T-0463`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least:
      - the command line against ADR-0164 decision 7, with P absent;
      - the standard-input bytes against decision 3;
      - the report length and the verdict against decision 10;
      - the check value over `x` and the rows, and broken-not-fail, against decision 9;
      - one table build per run (decision 5);
      - that every refusal comes before the build and before the start (decision 4);
      - that `rope_table` is not named in the new module;
      - that no ADR-0163 module or test changed.

## Out of Scope

- Slice 4: the three calibration kernels of ADR-0164 decision 11 (conforming, V1 violating, and cos/sin swapped failing) with their tests under `tests/harness/calibration/`.
- Adding `rope` to `bf16_verification_arrays.KINDS` or to `bf16_verification.py`.
- Registering `rope` with `correctness.check`, `spec.write` or the instance start (ADR-0164 Boundaries).
- Caching the table across runs.
- Choosing P for a check, whether an m = 1 check runs both T = 1 rows, tolerance values, seeds and draws (OD-16 sub-question ⑤, HQ-0066 (2)).
- SDPA with KV cache verification, the bf16 timing run, fp16.
- Editing any ADR, or `tests/test_rope_table.py`.

## Follow-ups

- Next task (planner candidate): ADR-0164 code slice 4. The three calibration kernels of decision 11, with their tests through `run_bf16_rope_verification`. The functional test uses P = 0, and the failing kernel swaps cos and sin.

## Result
