---
id: T-0462
title: Add the array side of the bf16 RoPE verification run, hilclaw/harness/bf16_rope_arrays.py (draw of x, table rows, check value, reference, counts; ADR-0164 code slice 3, first half)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0461]
touchesFiles: [hilclaw/harness/bf16_rope_arrays.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_rope_arrays.py]
estimatedSize: {loc: 170, files: 2}
hq: []
---
## Why

**State on `main` `67a8df7d`.** ADR-0164 (T-0459, `f9b8096`) records how one built bf16 RoPE kernel (kind `rope`) is verified on `cpu_standin`. Its Consequences (line 136) list four code slices. Two are done:
- slice 1: T-0460 (`48f1d05`) gave `hilclaw.local_run.run` the optional `stdin_data` argument;
- slice 2: T-0461 (`4043e70a`) added the program `hilclaw/harness/bf16_verification_rope.c` and `rope` in `bf16_verification_build.PROGRAM_SOURCES`.

**Slice 3 is "the Python side — the draw of `x`, the table rows from `rope_table.build`, the check value over `x` and the rows, the reference, judging the report with P and the bytes on standard input".** This task does its **array half**, in a new module. The runner half (command line, report form, judging, starting the process with the rows on standard input) is the next task. The split keeps each task under the size cap. It also follows the existing pattern of one array module and one runner module (`bf16_verification_arrays.py` and `bf16_verification.py`).

**Why a new module and not `bf16_verification_arrays.py`.** That module's API has the shape of ADR-0163's kinds: two drawn `uint16` operands, `reference(kind, first, second)`, and two-dimensional outputs. Kind `rope` has one drawn operand of three dimensions and a second operand that is **not drawn**: the `float32` rows from the table, chosen by a start position P (ADR-0164 decisions 4 to 6). Fitting it into that API would add a branch to every function there. A module of its own reuses the shared helpers and leaves the ADR-0163 code and its tests unchanged. In particular `bf16_verification_arrays.KINDS` stays as it is, and so do the tests that rely on it (`tests/harness/test_bf16_verification_build.py` expects `PROGRAM_SOURCES` to be `KINDS + ("rope",)`).

**Name.** The module is `bf16_rope_arrays.py`, and its runner will be `bf16_rope_verification.py`. The name `bf16_verification_rope.py` is not used: under the CI test-presence check (`.github/workflows/ci.yml` lines 117-146) its test file would be `tests/harness/test_bf16_verification_rope.py`, which already exists and tests the C program.

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items, and P2-14 needs them, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as it did for T-0451 to T-0461.

**D16.** This is pure Python and NumPy. It builds and runs no program, and it needs no `clang`, no `claude`, no board, no model file and no API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules.
  - For this task: branch `claude/T-0462-<slug>`; commit trailer `Task: T-0462`; code mode, so a Draft PR whose body ends with `Task: T-0462`.
- `CLAUDE.md`, "상시 규칙":
  - "코멘트 최소화";
  - "도구 계층 언어 정책";
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`:
  - the Decision preamble (line 32);
  - decision 3 (lines 45-50): the Python side keeps its own copy of the rows;
  - decision 4 (lines 52-58): P is a run parameter with no default; the table's constants; any even `d`; refusing (P + m)·d above 2^53 − 1;
  - decision 5 (lines 60-63): `rope_table.build` is the source, with `positions` = P + m;
  - decision 6 (lines 65-68): `x` with b = 8, one sequence in memory order;
  - decision 9 (lines 82-86): widening, the reference and the input check value;
  - decision 10 (lines 88-91): the comparison;
  - decision 12 (lines 99-108): the parameters;
  - decision 13, items 3 and 4 (lines 114-115);
  - Consequences, line 136.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 4 (lines 67-88): the generator;
  - decision 6 (lines 95-110): widening, the reference and the check value;
  - decision 7 (lines 112-121): the comparison and the counts.
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`:
  - decision 4 (lines 51-56): the table;
  - decision 5 (lines 58-60): the pairing;
  - decision 6 (lines 62-66): the layouts of `x` and `freqs_cis`;
  - decision 7 (lines 68-73): the operation;
  - decision 11 (lines 112-124): `d` even and at least 2;
  - decision 13 (lines 130-136): the table's constants θ = 500000, s = 8, a = 1, b = 4, L = 8192.
- `hilclaw/harness/bf16_verification_arrays.py`: the whole file (237 lines). It is the model for the docstring, the argument checks, `_patterns`, `_widened` and `count_failures`.
- `hilclaw/harness/verification_arrays.py`:
  - lines 60-80 (`GOLDEN`, `SEED_LIMIT`, `VerificationArgumentError`, `Counts`);
  - lines 130-220 (`check_tolerance`, `count_failures`, `_mix`, `_integer`, `_shown`, `_fail`).
- `hilclaw/rope_table.py`:
  - the module docstring (lines 1-80);
  - `build` (lines 132-188).
- `hilclaw/rope_bf16_contract.py`: lines 60-82 (`KIND`, `PROTOTYPE`, `SHAPES`, `X_PATTERNS`).
- `hilclaw/keys.py`: `MAX_INTEGER`.
- `hilclaw/harness/__init__.py`: the whole file (27 lines).
- `tests/harness/test_bf16_verification_arrays.py`:
  - lines 1-140: the constants and argument-check style;
  - one parametrized refusal test, as the model for negative cases.
- `tests/harness/test_bf16_verification_rope.py`: lines 141-215 (`TABLE`, `table_rows`, `expected_x`, `packed_check`). These are the test-side computations the program was checked against in T-0461; this module must agree with them.
- `.github/workflows/ci.yml` lines 117-146: the test-presence check.

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_rope_arrays.py`**, in Python (it computes on NumPy arrays next to `bf16_verification_arrays.py`; say so in one line of the commit body).
   - Its module docstring names ADR-0164 as the rule and states, without restating ADR-0163, everything below:
     - the element sequence of `x` and bits = 8, by reference to the generator of `bf16_verification_arrays`;
     - the layouts `x[(i*h + j)*d + k]` and `rows[i*d + c]`;
     - the table's constants;
     - the check value;
     - the reference formula;
     - what the module does not do. It starts no process, builds nothing, reads no report and gives no verdict. It holds no tolerance, seed, number of draws, dimension or start position, and gives no argument a default. It caches no table between calls.
   - It reuses, by import, the helpers of `bf16_verification_arrays` (`_patterns`, `_widened`, `count_failures`) and of `verification_arrays` (`GOLDEN`, `SEED_LIMIT`, `VerificationArgumentError`, `Counts`, `check_tolerance`, `_mix`, `_integer`, `_shown`, `_fail`). It does not copy them.
   - It re-exports `Counts` and `VerificationArgumentError` in `__all__`, as `bf16_verification_arrays` does.
2. **`dims`** is exactly a `tuple` of three `int`s `(m, h, d)`, each at least 1 (a `bool` is refused), with `d` even (ADR-0161 decision 11; ADR-0164 decision 7). Anything else raises `VerificationArgumentError` with the message form `"<name>: must be <rule>, got <shown>"`. The checks run in parameter order: `dims`, then `dims[0]`, `dims[1]` and `dims[2]`, then evenness.
3. **`TABLE_CONSTANTS`**: a read-only mapping (`types.MappingProxyType`) of the keyword arguments of `rope_table.build` other than `head_dim` and `positions`: `theta` 500000.0, `scale_factor` 8.0, `low_freq_factor` 1.0, `high_freq_factor` 4.0, `old_context_len` 8192 (ADR-0161 decision 13, ADR-0164 decision 4).
4. **`table_rows(dims, *, start)`** returns rows `start` … `start + m − 1` of `rope_table.build(head_dim=d, positions=start + m, **TABLE_CONSTANTS)` as a new C-contiguous `float32` array of shape (m, d). These are the rows the next task sends on standard input and the rows `check_value` and `reference` use.
   - `start` is exactly an `int` ≥ 0 (a `bool` is refused).
   - When (start + m)·d exceeds 2**53 − 1 (`keys.MAX_INTEGER`), the function raises `VerificationArgumentError` naming `start`, **before `build` is called** (ADR-0164 decision 4, last bullet).
   - `start` is keyword-only and has no default. There is one `build` call per call of `table_rows`, and no cache.
5. **`draw_x(dims, *, seed, draw)`** returns the C-contiguous `uint16` array `x` of shape (m, h, d) that the program draws for draw `draw` (ADR-0164 decision 6). The m·h·d elements take sequence indices 0 … m·h·d − 1 in memory order, with bits = 8, computed with the generator of `bf16_verification_arrays` (`base(d)` and `word(d, e)` of its docstring).
   - `seed` is from 0 to 2**64 − 1 and `draw` from 0 to 2**64 − 2, checked as there.
   - The peak memory per element stays within that module's stated bound of under 48 bytes; say so in the docstring.
6. **`check_value(x, rows)`** returns the `int` `zlib.crc32` of the bytes of `x` (2 per element, host order, memory order) followed by the bytes of `rows` (4 per element, host order, memory order) (ADR-0164 decision 9, "Input check value").
   - `x` must be a `uint16` array of three dimensions and `rows` a `float32` array of two dimensions, none of their dimensions 0.
   - `rows` must have the shape (m, d) of `x`.
   - A non-contiguous array is made contiguous, not refused, as in `bf16_verification_arrays.check_value`.
   - The value equals what `bf16_verification_rope.c` reports as a `uint32_t` for the same `x` and rows.
7. **`reference(x, rows)`** returns the float64 array of shape (m, h, d), with the same argument checks as `check_value`. `x` is widened exactly (pattern `p` becomes binary32 `p << 16`, then float64) and `rows` is widened exactly to float64. With c = row(i, 2p), s = row(i, 2p + 1) broadcast over the heads j, it computes y[i, j, 2p] = x₀·c − x₁·s and y[i, j, 2p + 1] = x₀·s + x₁·c, where x₀ = x[i, j, 2p] and x₁ = x[i, j, 2p + 1] (owner, HQ-0066 (1), through ADR-0154 decision 3; ADR-0164 decision 9). NumPy float64 only. A NaN or infinity in `rows` propagates and does not raise; use `np.errstate` as the existing `reference` does.
8. **`count_failures(output, expected, *, rtol, atol)`** returns the `Counts` of one draw.
   - `output` is a `uint16` array of shape (m, h, d) and `expected` a float64 array of the same shape. Each has three dimensions, none of them 0; a shape mismatch is refused naming `output`.
   - The tolerance is checked first by `check_tolerance`.
   - The predicate and counts are those of `bf16_verification_arrays.count_failures`. Reusing it on a (m·h, d) view is enough.
9. **`hilclaw/harness/__init__.py`**: name the new module in the docstring as the array side of the bf16 RoPE verification run of ADR-0164. Keep true the claim about which modules import `numpy`: they become five, the new one included.
10. **Size**: at most 300 changed lines outside tests, in at most 5 files. The expected files are the module and the package docstring.
11. **Tests: new file `tests/harness/test_bf16_rope_arrays.py`**, required by the test-presence check. Follow D12 (DRIVER §5): happy, error, branch and negative cases, and every public function of the new module. The tests need no `clang`. At least:
    - **Generator agreement**: for seeds 0, 1, 2**63 and 2**64 − 1, draws 0, 1 and 2**64 − 2, and shapes including (1, 1, 2), (3, 2, 4) and (2, 5, 6), `draw_x` equals `bf16_verification_arrays.draw_inputs("elementwise_add", (m*h, d), seed=..., draw=...)[0].reshape(m, h, d)`. This is the same sequence and bits, and it is the expectation T-0461's program tests used.
    - **An independent check of a few elements** from the integer formula in the docstring, as `test_bf16_verification_arrays.py` does. Every pattern lies in `rope_bf16_contract.X_PATTERNS`; the result is C-contiguous `uint16`.
    - **Rows**:
      - `table_rows((m, h, d), start=0)` row 0 is exactly 1.0 and +0.0 (check the sign bit), and each result equals the matching slice of a direct `rope_table.build` call with the five constants.
      - `start = 127` with m = 1 gives row 127.
      - The result is a fresh C-contiguous `float32` array: changing it does not change a second call's result.
      - `d` other than 64 (for example 2 and 6) is built, not refused.
      - Keep the positions small (at most 128 at d = 64) so the tests stay fast.
    - **Check value**:
      - it equals `zlib.crc32` of `x.tobytes()` followed by `rows.tobytes()`;
      - it differs when one element of `x` or one bit of one row changes;
      - it is the same for a non-contiguous view of equal content;
      - rows with NaN payloads and −0.0 are covered byte for byte, not as values.
    - **Reference**:
      - with row 0 (c = 1, s = +0), the reference equals the widened `x` exactly;
      - against a test-local scalar loop over (i, j, p) at a small shape with arbitrary rows, the result is equal;
      - each token's row is used for all heads, and token i uses row i;
      - the result is float64 of shape (m, h, d);
      - it emits no NumPy warning under `filterwarnings("error")`, also with a NaN row.
    - **Counts**:
      - an output equal to the bf16 rounding of the reference fails nothing under `atol = 2**-8 + 2**-21`, `rtol = 0` (ADR-0164 decision 10);
      - `0x7FC0` elements count as failed and non-finite;
      - one element out of tolerance gives `failed == 1`.
    - **Negative cases**, each raising `VerificationArgumentError` with the parameter's name, and nothing computed:
      - `dims` that is a list, has 2 or 4 entries, holds a `bool`, `0`, a negative number, a `float` or an odd `d`;
      - `start` that is negative, a `bool`, a `float` or `None`, or for which (start + m)·d exceeds 2**53 − 1. Show that `build` was not called, for example with `monkeypatch` on `rope_table.build`;
      - `seed` or `draw` out of range or of a wrong type;
      - arrays of a wrong dtype, a wrong number of dimensions, a zero dimension, a rows shape that does not match `x`, or a list instead of an array;
      - a refused tolerance;
      - a shape mismatch between `output` and `expected`.
    - Do not add tests that target test code (D12 ⑤).
12. **No other behaviour change**:
    - Leave these files unchanged: `bf16_verification_arrays.py`, `bf16_verification.py`, `bf16_verification_build.py`, `bf16_verification.h`, the five C programs, `rope_table.py`, `rope_bf16_contract.py`, `local_run.py`, every existing test file and the CI workflow.
    - Add no dependency.
    - The local `pytest` (with coverage at or above the 80 % line and function gates) and `ruff check` / `ruff format --check` are green.
13. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0462`, whose body ends with `Task: T-0462`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least:
      - the element sequence and bits of `x` against ADR-0164 decision 6;
      - the check-value byte range against decision 9;
      - the reference formula and the broadcast over heads against decision 9 and ADR-0161 decisions 5 to 7;
      - the table's constants and the refusal before `build` against decision 4;
      - that no ADR-0163 module or test changed.

## Out of Scope

- The runner half of slice 3 (next task): the command line `<m> <h> <d> <draws> <seed>`, the report length draws · (4 + 2·m·h·d) + 4 and its form check, judging a report with P, and starting the executable with the rows as `stdin_data`.
- The three calibration kernels of ADR-0164 decision 11 (slice 4).
- Adding `rope` to `bf16_verification_arrays.KINDS` or to `bf16_verification.py`.
- Changing `tests/harness/test_bf16_verification_rope.py` to use the new module.
- Registering `rope` with `correctness.check`, `spec.write` or the instance start (ADR-0164 Boundaries).
- SDPA with KV cache verification, the bf16 timing run, fp16, tolerance values, seeds, draws and the choice of P for a check.
- Editing any ADR.

## Follow-ups

- Next task (planner candidate): ADR-0164 code slice 3, second half. A new module `hilclaw/harness/bf16_rope_verification.py` holding `program_arguments`, `judge_report(report, dims, *, start, draws, seed, rtol, atol)` and `run_bf16_rope_verification(executable, dims, *, start, draws, seed, rtol, atol, timeout_s, cwd=None, env=None)`. It builds the rows once with `table_rows`, sends `rows.tobytes()` through `local_run.run(..., stdin_data=...)` and judges with the result types of `hilclaw.harness.verification`.

## Result

- **Outcome**: DONE. PR #276 (https://github.com/myungjoo/HIL-Claw/pull/276), squash-merged as `6297bf58`; branch `claude/T-0462-bf16-rope-verification-arrays` deleted.
- **Review**: 2 rounds with a context-isolated dev-reviewer (round 1 Approve with one nit, fixed in `437aed0`; round 2 Approve).
- **CI**: green on `437aed0` (Python 3.11/3.14, Coverage, C gate, Test presence, shellcheck).
- **Language**: Python, because the module computes on NumPy arrays next to `bf16_verification_arrays.py` and reuses its helpers.
- **Changes**: new `hilclaw/harness/bf16_rope_arrays.py` (`TABLE_CONSTANTS`, `table_rows`, `draw_x`, `check_value`, `reference`, `count_failures`; shared helpers imported), package docstring updated; new `tests/harness/test_bf16_rope_arrays.py` (154 cases, 100 % line coverage of the module). 231 changed lines outside tests in 2 files.
- **Deviation from AC 12**: `tests/test_rope_table.py::test_the_module_is_named_by_no_other_module` conflicted with AC 4 (call `rope_table.build`); it is now `test_the_module_is_named_only_by_the_bf16_rope_verification_arrays`. Stated in the PR body; reviewer accepted as Low.
- **Follow-ups**: the runner half `hilclaw/harness/bf16_rope_verification.py` (planner candidate T-0463). If it names `rope_table` directly it must be added to the allowed set in `tests/test_rope_table.py`; it can avoid this by getting the rows only through `table_rows`.
