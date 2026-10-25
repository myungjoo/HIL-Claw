---
id: T-0467
title: Add the array side of the bf16 SDPA-with-KV-cache verification run, hilclaw/harness/bf16_sdpa_kv_cache_arrays.py (draw of the five ranges, allocations with their fills, check value, per-head reference, expected allocations and counts; ADR-0165 code slice 2)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0466]
touchesFiles: [hilclaw/harness/bf16_sdpa_kv_cache_arrays.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_sdpa_kv_cache_arrays.py]
estimatedSize: {loc: 260, files: 2}
hq: []
---
## Why

**State on `main` `ee65f66f`.** ADR-0165 (T-0465, `24d4e0a4`) records how one built bf16 SDPA-with-KV-cache kernel (kind `sdpa_kv_cache`, contract ADR-0162) is verified on `cpu_standin`. Its Consequences (line 146) list four code slices in landing order. Slice 1 is done: T-0466 (PR #279, `d53b898e`) added the program `hilclaw/harness/bf16_verification_sdpa_kv_cache.c` and `sdpa_kv_cache` in `bf16_verification_build.PROGRAM_SOURCES`.

**This task is slice 2: "the array side — the draw of the five ranges, the allocations with their fills, the check value, the reference per head and the expected allocations with the count of differing elements".**
- It adds one new module of NumPy computations, as `bf16_verification_arrays.py` is for ADR-0163's kinds and `bf16_rope_arrays.py` for `rope`.
- The runner and judge (command line, report length and splitting, the cache comparison over a report, the verdict, starting the process) are slice 3, the next task. The four calibration kernels are slice 4.

**Why a new module.** `bf16_verification_arrays.py` has the API shape of two drawn operands of one or two dimensions. Kind `sdpa_kv_cache` has five drawn ranges of three dimensions, two cache allocations with fills and guard rows, and a cache comparison. Fitting that into the existing API would add a branch to every function there. A module of its own reuses the shared helpers and leaves ADR-0163's and ADR-0164's code and tests unchanged.

**Name.** The module is `bf16_sdpa_kv_cache_arrays.py`. The name `bf16_verification_sdpa_kv_cache.py` is not used: under the CI test-presence check (`.github/workflows/ci.yml` lines 117-146) its test file would be `tests/harness/test_bf16_verification_sdpa_kv_cache.py`, which already exists and tests the C program (the same reason T-0462 gave for `bf16_rope_arrays.py`).

**A trap.** `tests/test_sdpa_kv_cache_bf16_contract.py::test_module_imports_keys_only_and_is_bound_by_the_model_binding_only` (lines 664-678) fails if any `hilclaw/**/*.py` other than `model_binding.py` contains the text `sdpa_kv_cache_bf16_contract`, docstrings included. The new module must not contain that text (criterion 1). Its tests may import the contract module freely.

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items, and P2-14 needs them, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as it did for T-0451 to T-0466.

**D16.** This is pure Python and NumPy. It builds and runs no program, and it needs no `clang`, no `claude`, no board, no model file and no API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules.
  - For this task: branch `claude/T-0467-<slug>`; commit trailer `Task: T-0467`; code mode, so a Draft PR whose body ends with `Task: T-0467`.
- `CLAUDE.md`, "상시 규칙":
  - "코멘트 최소화";
  - "도구 계층 언어 정책";
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md`:
  - the Decision preamble (line 33);
  - decision 1 (lines 35-39): P = l − m;
  - decision 3 (lines 46-52): the dimension rules l ≥ m and h a multiple of h_kv, which the Python side also refuses;
  - decision 4 (lines 54-59): b = 8, one sequence per draw, the order of the five ranges;
  - decision 5 (lines 61-67): the allocations of l + 2m rows and their fills;
  - decision 6 (lines 69-75): widening, the keys and values as the Python side's own arrays, the formula, per query head, cost;
  - decision 7 (lines 77-80): the check value over `q`, `k_new`, `v_new` and the two whole allocations;
  - decision 8, second and fifth bullets (lines 85 and 88): the expected allocations after the call and the count of differing cache elements;
  - decision 9, first bullet (line 92): the comparison of `out`;
  - decision 12, items 3 and 4 (lines 121-122): the computed facts and the cost at the largest shape;
  - Consequences, line 146.
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`:
  - decision 4 (lines 52-60): the cache layout `(t·h_kv + g)·d + e` and the write of rows P … l − 1;
  - decision 5 (lines 61-67): the layouts of `q`, `k_new`, `v_new`, `out`;
  - decision 6 (lines 68-77): the operation, the head mapping, the causal mask;
  - decision 13 (lines 153-160): the value set.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 4 (lines 67-89): the generator;
  - decision 6 (lines 95-111): widening and the check value;
  - decision 7 (lines 112-122): the comparison and the counts.
- `hilclaw/harness/bf16_rope_arrays.py`: the whole file (226 lines). It is the model for the module docstring, the reuse by import, `draw_x`, `_dims` and `_array`.
- `hilclaw/harness/bf16_verification_arrays.py`: the whole file (237 lines), in particular the generator paragraph of the docstring, `draw_inputs`, `_patterns`, `_widened` and `count_failures`.
- `hilclaw/harness/verification_arrays.py`:
  - lines 60-80 (`GOLDEN`, `SEED_LIMIT`, `VerificationArgumentError`, `Counts`);
  - lines 130-220 (`check_tolerance`, `count_failures`, `_mix`, `_integer`, `_shown`, `_fail`).
- `hilclaw/sdpa_kv_cache_bf16_contract.py`: lines 66-82 (`PROTOTYPE`, `SHAPES`, `INPUT_PATTERNS`) and lines 198-212 (`_shape`, for the order and wording of the dimension rules).
- `hilclaw/harness/__init__.py`: the whole file (32 lines).
- `tests/harness/test_bf16_verification_sdpa_kv_cache.py`: lines 225-330 (`Inputs`, `expected_inputs`, `allocation`, `packed_check`, `copied`) and lines 512-534 (`reference`). These are the test-side computations the program was checked against in T-0466; this module must agree with them.
- `tests/harness/test_bf16_rope_arrays.py`: lines 1-140 and one parametrized refusal test, as the model for constants, generator-agreement tests and negative cases.
- `tests/test_sdpa_kv_cache_bf16_contract.py`: lines 664-678 (the trap named in Why).
- `.github/workflows/ci.yml` lines 117-146: the test-presence check.

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_sdpa_kv_cache_arrays.py`**, in Python (it computes on NumPy arrays next to `bf16_verification_arrays.py` and reuses its helpers; say so in one line of the commit body).
   - Its module docstring names ADR-0165 as the rule and states, without restating ADR-0163, everything below:
     - `dims` = `(m, l, h, h_kv, d)` and P = l − m;
     - the sequence of the five ranges and bits = 8, by reference to the generator of `bf16_verification_arrays` (`base(d)` and `word(d, e)` of its docstring);
     - the layouts `q[(i*h + j)*d + e]` and cache element (t, g, e) at `(t*h_kv + g)*d + e`;
     - the allocations of l + 2m rows, their guard rows and the fill `0x7FC0`;
     - the check value and its five ranges;
     - the reference formula, evaluated per query head;
     - the expected allocations after the call;
     - what the module does not do. It starts no process, builds nothing, reads or splits no report and gives no verdict. It holds no tolerance, seed, number of draws or dimension, and gives no argument a default. It returns no index, region or element beyond the counts (ADR-0165 decision 8).
   - It reuses, by import, the helpers of `bf16_verification_arrays` (`_patterns`, `_widened`, `count_failures`) and of `verification_arrays` (`GOLDEN`, `SEED_LIMIT`, `VerificationArgumentError`, `Counts`, `check_tolerance`, `_mix`, `_integer`, `_shown`, `_fail`). It does not copy them.
   - It re-exports `Counts` and `VerificationArgumentError` in `__all__`, as `bf16_rope_arrays` does, and defines `FILL = 0x7FC0` as a public constant.
   - **It does not contain the text `sdpa_kv_cache_bf16_contract`** anywhere, docstring included (Why, "A trap"). Refer to the value set as "the value set of ADR-0162 decision 13".
2. **`dims`** is exactly a `tuple` of five `int`s `(m, l, h, h_kv, d)`, each at least 1 (a `bool` is refused), with l ≥ m and h a multiple of h_kv (ADR-0165 decision 3; ADR-0162 decision 11). Anything else raises `VerificationArgumentError` with the message form `"<name>: must be <rule>, got <shown>"`. The checks run in this order: `dims`, then `dims[0]` … `dims[4]`, then l ≥ m (naming `dims[1]`), then the multiple (naming `dims[2]`). Every public function except `count_failures` takes `dims` first and checks it first. Slice 3 will reuse this check for the refusal "before a process is started" (decision 3), so keep it in one private function.
3. **Array arguments.** Every array argument is exactly a `numpy.ndarray` of dtype `uint16` (except `expected` of `count_failures`, which is `float64`) of exactly the shape this criterion names for `dims`; anything else (a list, another dtype, another shape) raises `VerificationArgumentError` naming the parameter. With P = l − m:
   - `q` and `output`: (m, h, d); `k_new` and `v_new`: (m, h_kv, d);
   - `cached_k` and `cached_v`: (P, h_kv, d) — **the only arrays that may hold a 0 dimension**, when P = 0;
   - an allocation (`cache_k`, `cache_v`, `reported`, `expected` of `count_cache_differences`): (l + 2m, h_kv, d).
   A non-contiguous array of the right dtype and shape is accepted, as in `bf16_rope_arrays.check_value`.
4. **`draw_inputs(dims, *, seed, draw)`** returns a `typing.NamedTuple` `Inputs` with fields `q`, `k_new`, `v_new`, `cached_k`, `cached_v` (exported in `__all__`): the five C-contiguous `uint16` arrays of criterion 3 that the program draws for draw `draw` (ADR-0165 decision 4).
   - The m·(h + 2·h_kv)·d + 2·P·h_kv·d elements take sequence indices 0 … N − 1 in the order `q`, `k_new`, `v_new`, `cached_k`, `cached_v`, each in memory order, all with bits = 8.
   - The five arrays are non-overlapping views of one buffer, as in `bf16_verification_arrays.draw_inputs`.
   - `seed` is from 0 to 2**64 − 1 and `draw` from 0 to 2**64 − 2, checked as there.
   - The peak memory per drawn element stays within that module's stated bound of under 48 bytes; say so in the docstring.
5. **`allocation_before(dims, cached)`** returns a new C-contiguous `uint16` array of shape (l + 2m, h_kv, d): rows m … m + P − 1 equal `cached`, and every other row (the m leading guard rows, rows m + P … m + l − 1, the m trailing guard rows) is `FILL` (ADR-0165 decision 5).
6. **`allocation_after(dims, cached, new)`** returns the allocation a conforming kernel leaves (ADR-0165 decision 8, second bullet): as `allocation_before`, with rows m + P … m + l − 1 equal to `new` (shape (m, h_kv, d)), row m + P + i equal to row i of `new`. The guard rows stay `FILL`.
7. **`check_value(dims, q, k_new, v_new, cache_k, cache_v)`** returns the `int` `zlib.crc32` of the bytes of `q`, `k_new`, `v_new`, `cache_k`, `cache_v` in that order, 2 bytes per element, host order, memory order (ADR-0165 decision 7). The cache arguments are whole allocations. The value equals what `bf16_verification_sdpa_kv_cache.c` reports as a `uint32_t` when `cache_k` and `cache_v` are `allocation_before` of the drawn cached rows.
8. **`reference(dims, q, k_new, v_new, cached_k, cached_v)`** returns the float64 array of shape (m, h, d) (ADR-0165 decision 6; owner, HQ-0066 (1), through ADR-0154 decision 3):
   - widen every operand exactly (pattern `p` becomes binary32 `p << 16`, then float64);
   - K = `cached_k` rows followed by `k_new` rows, V the same for `cached_v` and `v_new` (l rows each). No reported data enters;
   - for each query head j, g = j // (h // h_kv); scores = (Q_j · K_gᵀ) · c with c = `1 / math.sqrt(d)` as a float64 multiplier (not a division); positions t > P + i set to −∞ for row i; subtract the row maximum; `numpy.exp`; divide by the row sum; multiply by V_g;
   - **evaluate one query head at a time**, so at most one m × l score array is held (decision 6, "Evaluated per query head");
   - NumPy float64 only, no bf16 emulation. A NaN pattern in an input propagates and does not raise; use `np.errstate` as the existing `reference` functions do.
9. **`count_failures(output, expected, *, rtol, atol)`** returns the `Counts` of one draw's `out`.
   - The tolerance is checked first by `check_tolerance`.
   - `output` is `uint16` of three dimensions and `expected` `float64` of three dimensions, none of them 0; a shape mismatch is refused naming `output`.
   - The predicate and counts are those of `bf16_verification_arrays.count_failures`; reusing it on a (m·h, d) view is enough, as `bf16_rope_arrays.count_failures` does.
10. **`count_cache_differences(dims, reported, expected)`** returns the `int` number of elements whose `uint16` patterns differ between two allocations, bit for bit and with no tolerance (ADR-0165 decision 8). `0x7FC0` equals `0x7FC0` (patterns are compared as integers, not as values). It returns nothing else. The runner of slice 3 adds the counts of the two allocations.
11. **`hilclaw/harness/__init__.py`**: name the new module in the docstring as the array side of the bf16 SDPA-with-KV-cache verification run of ADR-0165. Keep true the claim about which modules import `numpy`: they become seven, the new one included.
12. **Size**: at most 300 changed lines outside tests, in at most 5 files. The expected files are the module and the package docstring. If the work would go over the cap, shorten the docstring, not the behaviour.
13. **Tests: new file `tests/harness/test_bf16_sdpa_kv_cache_arrays.py`**, required by the test-presence check. Follow D12 (DRIVER §5): happy, error, branch and negative cases, and every public function of the new module. The tests need no `clang`. Use small shapes that include P = 0 (l = m), P > 0 with m = 1, P > 0 with m > 1, h = h_kv, h = 4·h_kv, d = 1 and m = l = 1. At least:
    - **Generator agreement**: for seeds 0, 1, 2**63 and 2**64 − 1, draws 0, 1 and 2**64 − 2, and those shapes, the five arrays of `draw_inputs` equal the split of `bf16_verification_arrays.draw_inputs("elementwise_add", (1, N), seed=..., draw=...)[0]`, N the element count of criterion 4 — the expectation `expected_inputs` of `tests/harness/test_bf16_verification_sdpa_kv_cache.py` used against the program.
    - **An independent check of a few elements** from the integer formula of the generator docstring, as `test_bf16_rope_arrays.py` does. Every pattern lies in `sdpa_kv_cache_bf16_contract.INPUT_PATTERNS`; each result is C-contiguous `uint16`; at P = 0 the cached arrays have shape (0, h_kv, d).
    - **Allocations**: `allocation_before` and `allocation_after` match a test-local construction (as `allocation` and `copied` of the program test): guard rows and unwritten rows all `FILL`, rows in place, a fresh array per call (changing it does not change the next result); at P = 0 no row holds drawn data before the call.
    - **Check value**: it equals `zlib.crc32` of the concatenated `tobytes()` of the five arrays; it equals `packed_check` of the program test (as an `int`, not packed) for the same draw; it changes when one element of any of the five arrays changes, guard rows included; it is the same for a non-contiguous view of equal content.
    - **Reference**:
      - at P = 0, row 0 of every head j equals the widened `v_new[0, g, :]` exactly (one weight of 1);
      - against a test-local scalar loop over (i, j, t, e) in float64 at small shapes, the result agrees to within 1e-12 absolute;
      - the head mapping: with h = 4·h_kv, changing `k_new` and `v_new` of KV head g changes only query heads 4g … 4g + 3;
      - the causal mask: changing `k_new` and `v_new` row m − 1 (m > 1) leaves rows 0 … m − 2 unchanged;
      - cached rows matter at P > 0: changing `cached_v` changes the result;
      - the result is float64 of shape (m, h, d), and it emits no NumPy warning under `filterwarnings("error")`, also with a `0x7FC0` pattern in an input;
      - a bound on held memory is not tested; the per-head loop is checked by review.
    - **Counts**: an output equal to the bf16 round-to-nearest-even of the reference fails nothing under `atol = 2**-8`, `rtol = 0`; `0x7FC0` elements count as failed and non-finite; one element out of tolerance gives `failed == 1`.
    - **Cache differences**: 0 for `allocation_after` against itself; 1 for one changed element in each region (leading guard, rows 0 … P − 1, rows P … l − 1, trailing guard); the full count for an allocation left as `allocation_before` at P > 0 and at P = 0 (the m·h_kv·d unwritten elements).
    - **Negative cases**, each raising `VerificationArgumentError` with the parameter's name, and nothing computed:
      - `dims` that is a list, has 4 or 6 entries, holds a `bool`, `0`, a negative number or a `float`; l < m; h not a multiple of h_kv (for example h = 3 with h_kv = 2, and h = 1 with h_kv = 2);
      - `seed` or `draw` out of range or of a wrong type;
      - arrays of a wrong dtype, a wrong shape (one row short, one guard row short), a list instead of an array; a zero dimension outside the cached arrays;
      - a refused tolerance;
      - a shape mismatch between `output` and `expected`.
    - Do not add tests that target test code (D12 ⑤).
14. **No other behaviour change**:
    - Leave these files unchanged: `bf16_verification_arrays.py`, `bf16_verification.py`, `bf16_rope_arrays.py`, `bf16_rope_verification.py`, `bf16_verification_build.py`, `bf16_verification.h`, the six C programs, `sdpa_kv_cache_bf16_contract.py`, every existing test file and the CI workflow.
    - Add no dependency.
    - The local `pytest` (with coverage at or above the 80 % line and function gates) and `ruff check` / `ruff format --check` are green.
15. **Process**: code mode (CLAUDE.md A-13).
    - Open a Draft PR titled with `T-0467`, whose body ends with `Task: T-0467`.
    - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
    - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
    - The reviewer checks at least:
      - the order and starting indices of the five drawn ranges against ADR-0165 decision 4;
      - the allocation rows, the fills and the guard rows against decision 5, and the expected allocations against decision 8;
      - the five check-value ranges against decision 7;
      - the reference formula, the head mapping, the mask t > P + i, the scale as a multiplier and the per-head evaluation against decision 6 and ADR-0162 decision 6;
      - that the module does not contain the text `sdpa_kv_cache_bf16_contract`;
      - that no ADR-0163 or ADR-0164 module or test changed.

## Out of Scope

- Slice 3, the runner and judge: a new module (planner suggestion: `hilclaw/harness/bf16_sdpa_kv_cache_verification.py`) with the command line `<m> <l> <h> <h_kv> <d> <draws> <seed>`, the report length draws · (4 + 2·m·h·d + 4·(l + 2m)·h_kv·d) + 4 and its form check, splitting a report, the cache comparison over a report, the verdict, and starting the executable through `local_run.run`.
- The four calibration kernels of ADR-0165 decision 10 (slice 4).
- Adding `sdpa_kv_cache` to `bf16_verification_arrays.KINDS` or to `bf16_verification.py`.
- Changing `tests/harness/test_bf16_verification_sdpa_kv_cache.py` to use the new module.
- Registering `sdpa_kv_cache` with `correctness.check`, `spec.write` or the instance start (ADR-0165 Boundaries).
- The bf16 timing run, fp16, tolerance values, seeds, draws, other shapes, the model program's cache capacity.
- Editing any ADR, including the "less exact" sentences that ADR-0165 Consequences lists.

## Follow-ups

- Next task (planner candidate): ADR-0165 code slice 3, the runner and judge of the SDPA-with-KV-cache verification run, built on this module's `draw_inputs`, `allocation_before`, `allocation_after`, `check_value`, `reference`, `count_failures` and `count_cache_differences`, with the result types of `hilclaw.harness.verification`.

## Result
