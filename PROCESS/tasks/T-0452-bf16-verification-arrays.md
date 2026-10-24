---
id: T-0452
title: Add hilclaw/harness/bf16_verification_arrays.py - the array side of ADR-0163's bf16 verification run for gemm, rmsnorm, elementwise_add and swiglu (generator over each value set, check value, widening, float64 reference per kind, failure counts), with its tests (ADR-0163 code slice 1)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0451]
touchesFiles: [hilclaw/harness/bf16_verification_arrays.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_verification_arrays.py]
estimatedSize: {loc: 230, files: 2}
hq: []
---
## Why

**State on `main` `a1cb9a2`.** ADR-0163 (landed as `c004ccc`, T-0451) is the record of the verification run of one built bf16 kernel on `cpu_standin` for the kinds `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. No code implements it yet. `hilclaw/harness/` verifies only the fp32 `gemm` of ADR-0017.

**ADR-0163 Consequences names the code slices.** For each kind they are:
- the verification program in C;
- its build;
- the Python side: the generator over a value set with its index mapping, the widening of `uint16_t` patterns, the per-kind reference and the comparison, and reading and judging the report;
- the three calibration kernels with their tests.

**This task is the first slice: the array side of the Python half, for all four kinds.** It mirrors what `hilclaw/harness/verification_arrays.py` does for the first case. It starts no process, builds nothing and reads no report.
- The pieces are shared by the four kinds and need no clang, so one slice covers them within the size cap.
- It also fixes the generator algorithm in a module docstring. The later C programs must reproduce it bit for bit (ADR-0163 decision 4: "the algorithm is the code task's and is identified by its source commit").

**Later slices (not here):**
- a shared C header and the per-kind verification programs;
- their build;
- the report reader and verdict over an executable;
- the generator-agreement test that needs clang;
- the twelve calibration kernels.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12, both checklist items, and P2-14 needs it. So the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14.

**D16.** Pure Python and NumPy. Nothing starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit;
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules. Branch `claude/T-0452-<slug>`; commit trailer `Task: T-0452`; code mode, so a Draft PR whose body ends with `Task: T-0452`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md` (the whole procedure, code mode).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - the Decision preamble (line 35);
  - decisions 3, 4, 5, 6 and 7 (lines 55-121): the RMSNorm `eps` constant, the value sets, the index mapping, the words, the element order per draw, operand independence, the output fill, the widening, the reference per kind, the check value and the comparison;
  - decision 8 (lines 123-127): only so you know what this module does **not** do;
  - Boundaries (lines 195-207).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`: decisions 3 to 5 (lines 38-64).
- `hilclaw/harness/verification_arrays.py`: the whole file (216 lines). It is the model for the structure, the argument conventions, the error class and the docstring form. Reuse its public names (`GOLDEN`, `SEED_LIMIT`, `Counts`, `VerificationArgumentError`, `check_tolerance`) by import. You may import or copy its private `_mix`; say which in the commit body.
- `tests/harness/test_verification_arrays.py`: the test style to follow.
- `hilclaw/harness/__init__.py` (the package docstring that lists the harness modules).
- The value-set constants and prototypes (read only):
  - `hilclaw/gemm_bf16_contract.py` (`PROTOTYPE`, `INPUT_PATTERNS`);
  - `hilclaw/rmsnorm_bf16_contract.py` (`PROTOTYPE`, `INPUT_PATTERNS`, `EPS`);
  - `hilclaw/elementwise_add_bf16_contract.py` (`PROTOTYPE`, `INPUT_PATTERNS`);
  - `hilclaw/swiglu_bf16_contract.py` (`PROTOTYPE`, `GATE_PATTERNS`, `UP_PATTERNS`).

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_verification_arrays.py`** (Python; give the reason in one line of the commit body). Its module docstring:
   - names ADR-0163 as the rule;
   - states the generator exactly, in the form of `verification_arrays.py`'s docstring, so the later C programs can copy it. It must state:
     - the word construction (the first case's `mix`, `base(d)` and `word(d, e)`, reused as ADR-0163 decision 4 permits);
     - the element sequence per draw: the first operand in memory order, then the second;
     - the index r = word >> (64 − b), with b = 8 or 10;
     - the pattern mapping of ADR-0163 decision 4;
   - states the check value: `zlib.crc32` of the first operand's bytes, then the second's, at 2 bytes per element;
   - states the module's conventions and what it does not do, as `verification_arrays.py` does.
   - **Changing the generator later is a change of the C side's contract.** Say so in one sentence.
2. **Public surface.** Names may differ if the docstring says why. The behaviour is fixed:
   - `KINDS = ("gemm", "rmsnorm", "elementwise_add", "swiglu")`.
   - `EPS_BITS = 0x3727C5AC`, the RMSNorm `eps` of ADR-0163 decision 3.
   - `draw_inputs(kind, dims, *, seed, draw)` returns the two operands of that draw as C-contiguous `uint16` arrays in host byte order:
     - `dims` is `(m, k, n)` for `gemm` and `(m, n)` for the others;
     - shapes: `gemm` `a` (m, k) and `b` (k, n); `rmsnorm` `x` (m, n) and `w` (n,); `elementwise_add` `a` and `b` (m, n); `swiglu` `gate` and `up` (m, n);
     - every element is drawn from its own value set by its own word, so the operands are independent;
     - `swiglu` `gate` uses the 1024-value set (b = 10). Every other operand uses the 256-value set (b = 8);
     - seed and draw ranges are as in `verification_arrays.draw_inputs`.
   - `check_value(first, second)` returns the CRC-32 `int` of a draw's two input arrays.
   - `widen(patterns)` maps a `uint16` array to `float64`: pattern p becomes the binary32 pattern p << 16, then `float64`. It is exact, and `0x7FC0` becomes NaN.
   - `reference(kind, first, second)` returns the `float64` (m, n) reference of ADR-0163 decision 6 on the widened inputs:
     - `gemm`: `matmul`;
     - `rmsnorm`: x · w / sqrt(mean(x²) + eps), where eps is the binary32 value of `EPS_BITS` widened to `float64`;
     - `elementwise_add`: a + b;
     - `swiglu`: g / (1 + `numpy.exp`(−g)) · u.
   - `count_failures(output, expected, *, rtol, atol)` takes `output` as `uint16` patterns, widens them, and applies the predicate and the counts of `verification_arrays.count_failures`. It returns `Counts` and checks the tolerance first.
3. **Argument checking**, under the conventions of `verification_arrays.py`:
   - a `kind` outside `KINDS`, a `dims` of the wrong length or with a bad entry, a bad seed or draw, a wrong dtype, wrong dimensions or a zero-size array, a shape mismatch between the two operands or between `output` and `expected`, and an invalid tolerance each raise `VerificationArgumentError`, naming the argument;
   - nothing is computed before the check.
4. **Size**: at most 300 changed lines outside tests, in at most 5 files. Expected: the new module, plus one sentence in the docstring of `hilclaw/harness/__init__.py`. That docstring now says `verification_arrays` and `verification` are "the two modules that import ``numpy``". Make it true with the new module. Edit nothing else.
5. **Tests**, in the new file `tests/harness/test_bf16_verification_arrays.py`. Follow D12 (DRIVER §5): every public function, plus happy, error, branch and negative cases. At least:
   - **Mapping**: for every index r in 0 … 255 the b = 8 formula of ADR-0163 decision 4 gives `INPUT_PATTERNS[r]` and `UP_PATTERNS[r]`. For every r in 0 … 1023 the b = 10 formula gives `GATE_PATTERNS[r]`. The test recomputes these independently of the module's code path.
   - **Generator**: for a few seeds and draws (including 0, 2**64 − 1 and 2**64 − 2), a scalar pure-Python recomputation of word, index and pattern for each element equals `draw_inputs`, for every kind. Both operands of `swiglu` and the `w` of `rmsnorm` are included.
   - **Draws**: two draws differ, and the same seed and draw repeat bit for bit.
   - **Sets**: every drawn pattern is in its operand's tuple. Over a large draw, the operands are not equal and not derived from each other (for example, `elementwise_add` gives some but not all b = −a pairs).
   - **Shapes and dtypes** per kind, including dimensions of 1.
   - **`EPS_BITS`**: its binary32 value equals `rmsnorm_bf16_contract.EPS`.
   - **`check_value`**: it equals `zlib.crc32` of the concatenated bytes. It changes when one element changes.
   - **`widen`**: it is exact for every pattern of the three tuples and for a few hand-picked patterns. `0x7FC0` gives NaN and `0x7F80` gives inf.
   - **`reference` per kind**, against an independent float64 computation on small hand-written inputs:
     - `elementwise_add` is exact;
     - the `rmsnorm` `eps` is the widened binary32 value, not 1e-05 (a test separates the two at a size where they differ in float64);
     - the `swiglu` reference uses float64 `exp`.
   - **`count_failures`**: pass, fail, a NaN output (the `0x7FC0` fill counts as both failed and non-finite), an infinity, `atol` = 0 against an `rtol`-only pass, and shape and dtype errors.
   - **Negative cases** for every argument rule of criterion 3.
   - The tests need no clang. The module is in `hilclaw/`, so the coverage gate (line ≥ 80 %, function ≥ 80 %) and the test-existence check apply.
6. **No behaviour change** to `verification_arrays.py`, `verification.py`, `verification_program.c`, the contract modules or anything else of the first case. No new dependency: NumPy and the standard library only. The local `pytest` and `ruff` runs are green.
7. **Process**: code mode (CLAUDE.md A-13).
   - Draft PR titled with `T-0452`; its body ends with `Task: T-0452`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - the mapping and the element order against ADR-0163 decision 4;
     - the RMSNorm reference `eps` against ADR-0163 decision 6;
     - that the docstring states the generator completely enough for a C reimplementation;
     - that nothing of the first case changed.

## Out of Scope

- Any C code: the shared header and the four verification programs. Also their build, the report reader, the verdict over an executable (`judge_report`/`run_verification` counterparts) and the generator-agreement test that needs clang.
- The calibration kernels and `test_calibration.py`.
- RoPE and SDPA, the bf16 timing run, and fp16.
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Tolerance values or defaults, seed sources, and the number of draws.
- Any edit to `ARCHITECTURE/`, to the contract modules, or to `verification_arrays.py` beyond import use.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next slice: the shared C header (generator, CRC-32, report writer, all `static`) and the first kind's verification program under `hilclaw/harness/`. The program must reproduce this module's generator bit for bit. The slice also needs its build and a clang test that it agrees with `draw_inputs` and `check_value`. After that come the remaining kinds, the report reader and verdict, and the calibration kernels (ADR-0163 decisions 2, 3, 5, 8 and 9).

## Result
