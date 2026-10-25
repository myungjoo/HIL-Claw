---
id: T-0468
title: Add the runner and judge of the bf16 SDPA-with-KV-cache verification run, hilclaw/harness/bf16_sdpa_kv_cache_verification.py (arguments, report length and splitting, cache comparison, verdict, starting the executable; ADR-0165 code slice 3)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0466, T-0467]
touchesFiles: [hilclaw/harness/bf16_sdpa_kv_cache_verification.py, hilclaw/harness/__init__.py, tests/harness/test_bf16_sdpa_kv_cache_verification.py]
estimatedSize: {loc: 280, files: 2}
hq: []
---
## Why

**State on `main` `29ec755c`.** ADR-0165 (T-0465, `24d4e0a4`) records how one built bf16 SDPA-with-KV-cache kernel (kind `sdpa_kv_cache`, contract ADR-0162) is verified on `cpu_standin`. Its Consequences (line 146) list four code slices in landing order:
- slice 1 is done: T-0466 (PR #279, `d53b898e`) added the program `hilclaw/harness/bf16_verification_sdpa_kv_cache.c` and `sdpa_kv_cache` in `bf16_verification_build.PROGRAM_SOURCES`;
- slice 2 is done: T-0467 (PR #280, `35b860bb`) added `hilclaw/harness/bf16_sdpa_kv_cache_arrays.py` (`FILL`, `Inputs`, `draw_inputs`, `allocation_before`, `allocation_after`, `check_value`, `reference`, `count_failures`, `count_cache_differences`, private `_dims`).

**This task is slice 3: "the runner and judge — arguments, report length, the cache comparison and the verdict".** It adds the runner module `hilclaw/harness/bf16_sdpa_kv_cache_verification.py`. It mirrors `hilclaw/harness/bf16_rope_verification.py` (the runner of `rope`) and differs from it in these ways:
- the shape is `(m, l, h, h_kv, d)` and there is no start position and no standard input (ADR-0165 decision 2: ADR-0017 decision 9 holds; the program reads none);
- each draw's block of the report carries, after the check value, `out` and then both whole cache allocations (decision 8);
- the verdict also needs the bit-exact cache comparison: a completed run passes iff every element of `out` meets the predicate **and** no element of either allocation differs from what is expected (decision 8);
- per draw, the Python side returns the counts of `out` and the number of differing cache elements over both allocations (decision 8, "The Python side returns").

After this task the harness can verify a built `sdpa_kv_cache` kernel end to end. Slice 4, the four calibration kernels of decision 10, is the next task.

**Why a new module and not `bf16_verification.py` or `bf16_rope_verification.py`.** Their `kind`/`dims` checks accept other shapes, and their reports have no cache blocks. T-0467 chose the pair `bf16_sdpa_kv_cache_arrays.py` / `bf16_sdpa_kv_cache_verification.py` for this reason (T-0467 Out of Scope). The CI test-presence check requires `tests/harness/test_bf16_sdpa_kv_cache_verification.py`, which does not exist yet.

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12, checklist items that P2-14 needs, so the D18 rule does not apply. The round-loop items and P2-5 are still held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as for T-0451 to T-0467.

**D16.** The module is Python and starts only an executable the caller has already built. Its tests use a Python stand-in process and, where `clang` exists on a POSIX machine, a verification executable built from a test-local kernel. Nothing needs `claude`, a board, a model file or an API key. ADR-0165 Consequences: "Runtime acceptance items: none."

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap, the naming and the test rules.
  - For this task: branch `claude/T-0468-<slug>`; commit trailer `Task: T-0468`; code mode, so a Draft PR whose body ends with `Task: T-0468`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md`:
  - decision 2 (lines 41-44): no standard input;
  - decision 3 (lines 46-52): the command line `<m> <l> <h> <h_kv> <d> <draws> <seed>`, l ≥ m, h a multiple of h_kv, both sides refuse, P not an argument;
  - decision 5 (lines 61-67): the allocations of l + 2m rows, the fills;
  - decision 6 (lines 69-75): the reference rests only on the Python side's own arrays, never on the reported caches;
  - decision 7 (lines 77-80): the check value over the whole allocations; a disagreement is broken, never a fail;
  - decision 8 (lines 82-88): the report content, the length draws · (4 + 2·m·h·d + 4·(l + 2m)·h_kv·d) + E, the cache comparison with no tolerance, the verdict, and what the Python side returns;
  - decision 9 (lines 90-96): the tolerance applies to `out` only; the absolute bound 2.154·10^−3 at d = 64, l = 128;
  - decision 11 (lines 106-115): parameters, none with a default;
  - decision 12, item 4 (line 122): cost at the largest shape;
  - Consequences, line 146; Boundaries (lines 153-163).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`: decision 3 (line 55), decision 7 (line 112) and decision 8 (line 123): the spelling of the arguments, the comparison, completed/broken/pass/fail.
- `hilclaw/harness/bf16_rope_verification.py`: the whole file (248 lines). It is the model for the docstring, the conventions, `program_arguments`, `judge_report`, the `run_...` function, `_judgement` and `_counts`.
- `hilclaw/harness/bf16_sdpa_kv_cache_arrays.py`: the whole file (281 lines), especially the module docstring and `_dims`.
- `hilclaw/harness/verification.py`: lines 95-160 (`END_MARK`, `Broken`, `Verdict`, `Judgement`, `VerificationResult`) and lines 312-323 (`_digits`).
- `hilclaw/harness/verification_arrays.py`: lines 68-77 (`VerificationArgumentError`, `Counts`) and 130-145 (`check_tolerance`).
- `hilclaw/local_run.py`: `run` and its docstring (from line 85).
- `hilclaw/harness/bf16_verification_sdpa_kv_cache.c`: the header comment (lines 1-56): command line, allocations, fills, check value, report layout and length, exit statuses.
- `hilclaw/harness/__init__.py`: the whole file.
- `tests/harness/test_bf16_rope_verification.py`: lines 1-210 (the stand-in process, the fixtures and helpers) and 249-480 (the refusal, form and check-value tests); the real-`clang` tests at the end of the file.
- `tests/harness/test_bf16_verification_sdpa_kv_cache.py`: lines 1-160 (the kernel template, `HELPERS`, `PLAIN`), lines 370-400 (the `toolchain` and `executable` fixtures and their skip rules) and lines 534-553 (the plain-kernel test and its margin).
- `tests/test_sdpa_kv_cache_bf16_contract.py` lines 664-678: no module of `hilclaw/` other than `model_binding.py` may contain the text `sdpa_kv_cache_bf16_contract`.
- `.github/workflows/ci.yml` lines 117-146: the test-presence check.

## Acceptance Criteria

1. **New module `hilclaw/harness/bf16_sdpa_kv_cache_verification.py`**, in Python. The commit body says why in one line: it is the runner next to `bf16_rope_verification.py` and reuses its result types and `local_run.run`.
   - The module docstring names ADR-0165 as the rule and states:
     - the command line, with P = l − m derived and not on it;
     - that no standard input is sent (decision 2);
     - the report layout and the complete length draws · (4 + 2·m·h·d + 4·(l + 2m)·h_kv·d) + 4;
     - the cache comparison: bit for bit, no tolerance, against `allocation_after` built from the Python side's own arrays, never from the report;
     - the verdict and the per-draw counts (AC 2);
     - the conventions of `bf16_rope_verification.py`, with `dims` of five entries and no `start`, by reference and not restated;
     - what the module does not do: it builds nothing and holds no path of a program; it holds no tolerance, seed, number of draws, dimension or time limit and gives none of them a default; it passes no tolerance to the program, sends no standard input, sets no environment variable and parses no standard error; it does not retry, repair, store or cache anything, writes no file and returns no element, index or region of the inputs, allocations, reference or output; it registers `sdpa_kv_cache` with neither `correctness.check`, `spec.write` nor the instance start (ADR-0165 Boundaries).
   - It imports `END_MARK`, `Broken`, `Judgement`, `Verdict`, `VerificationResult` and `_digits` from `hilclaw.harness.verification`, and `_dims` from `bf16_sdpa_kv_cache_arrays`, and copies none of them. `__all__` re-exports the five public result names plus the new names of this module.
   - **The text `sdpa_kv_cache_bf16_contract` must not appear anywhere in the file**, docstrings included (`tests/test_sdpa_kv_cache_bf16_contract.py` line 678, unchanged).
2. **Per-draw counts.** A new `NamedTuple` in the module, `DrawCounts(failed, non_finite, cache_differences)`, all `int`: the first two are the `Counts` of `bf16_sdpa_kv_cache_arrays.count_failures` for `out`, the third the sum of `count_cache_differences` over the `cache_k` and the `cache_v` allocation. `Judgement.counts` and `VerificationResult.counts` hold a tuple of `DrawCounts`, one per draw. The verdict is `PASS` iff every draw has `failed == 0` and `cache_differences == 0`, otherwise `FAIL`. The docstring of `DrawCounts` names decision 8 and says no index or region is returned. This is an internal interface of the harness, not a data-plane schema (ADR-0165 Status, "Not changed").
3. **`program_arguments(dims, *, draws, seed)`** returns the tuple of `str` `(m, l, h, h_kv, d, draws, seed)` in decimal digits, in the spelling of `bf16_rope_verification.program_arguments`.
   - `dims` is checked by `bf16_sdpa_kv_cache_arrays._dims` (exactly a tuple of five `int`s, each ≥ 1, `bool` refused, l ≥ m, h a multiple of h_kv), then each entry with `_digits`.
   - 1 ≤ `draws` < 2**64 and 0 ≤ `seed` < 2**64.
   - The checks run in parameter order and raise `VerificationArgumentError`, also for an `int` that the interpreter cannot write in decimal digits.
4. **`judge_report(report, dims, *, draws, seed, rtol, atol)`** returns a `Judgement`.
   - Checks before any byte of `report` is looked at, in this order: `dims`, `draws` and `seed` as in `program_arguments`; the tolerance by `verification_arrays.check_tolerance`; `TypeError` for a `report` that is not exactly `bytes`.
   - The length is then compared with the complete length (AC 1) and the end mark is looked for; either failing gives `Broken.REPORT_FORM`. The length is computed from `dims` and `draws` alone; nothing is allocated from it and no draw is regenerated before it holds.
   - For each draw in order, one private implementation shared with AC 5:
     - the inputs with `draw_inputs`, and the two allocations before the call with `allocation_before`;
     - the reported `uint32` (host order) is compared with `check_value(dims, q, k_new, v_new, before_k, before_v)`; the first disagreement gives `Broken.CHECK_VALUE`, with the counts taken so far dropped;
     - `out` (2·m·h·d bytes, host order) is counted against `reference(...)` with `count_failures`;
     - the reported `cache_k` and `cache_v` allocations ((l + 2m)·h_kv·d elements each, in that order, host order) are compared with `allocation_after(dims, cached_k, k_new)` and `allocation_after(dims, cached_v, v_new)` by `count_cache_differences`.
   - No array of a draw is kept for the next draw. `TIMEOUT` and `EXIT_STATUS` are never returned. All parameters after `dims` are keyword-only and none has a default.
5. **`run_bf16_sdpa_kv_cache_verification(executable, dims, *, draws, seed, rtol, atol, timeout_s, cwd=None, env=None)`** returns a `VerificationResult`.
   - Checks before anything is started, in this order: the arguments as in `judge_report`; `TypeError` for an `executable` that is neither a path nor iterable; `ValueError` for an empty `executable` sequence (as `run_bf16_rope_verification`).
   - One process `(*prefix, *program_arguments(...))` is started with `local_run.run(..., timeout_s=timeout_s, cwd=cwd, env=env)` and no `stdin_data`.
   - A timeout gives `Broken.TIMEOUT`; a non-zero exit status gives `Broken.EXIT_STATUS` whatever was written; otherwise the judgement of AC 4.
   - `run.stdout` is replaced by `b""`; every other member of the run result is passed on unfiltered. Errors of `local_run.run` are passed on.
6. **`hilclaw/harness/__init__.py`**: name the new module in the docstring as the Python side of the bf16 SDPA-with-KV-cache verification run of ADR-0165 over an executable that is already built, and keep the count of numpy-importing modules true (eight if the new module imports `numpy`, seven otherwise).
7. **Size**: at most 300 changed lines outside tests, in at most 5 files.
8. **Tests: new file `tests/harness/test_bf16_sdpa_kv_cache_verification.py`.** D12 (DRIVER §5): happy, error, branch and negative cases, and every public function of the new module. Use the Python stand-in-process pattern of `tests/harness/test_bf16_rope_verification.py` (no standard-input recording needed; a stand-in check that nothing is read on standard input is welcome). Build reports in the test from the arrays module (`draw_inputs`, `allocation_before`, `allocation_after`, `check_value`, bf16 round-to-nearest-even of `reference`). Keep shapes small (for example `(2, 5, 4, 2, 3)`, `(1, 1, 1, 1, 1)`, a P = 0 shape) so the suite stays fast. At least:
   - **Public names**: `__all__`; the five result names are the very objects of `hilclaw.harness.verification`; `DrawCounts` fields and order.
   - **`program_arguments`**: order and spelling (including `seed=2**64 - 1`); bounds; each argument refused in parameter order (list `dims`, 4 or 6 entries, `bool`, `0`, negative, `float`, l < m, h not a multiple of h_kv, `10**5000`; `draws` 0, 2**64, `True`, `1.0`, `None`; `seed` −1, 2**64, `1.5`, `"7"`, `None`); no defaults; keyword-only parameters.
   - **`judge_report`, pass**: a conforming report passes with zero counts in every draw, for one draw and for several, at P = 0 and at P > 0, under a test tolerance (for example `atol = 2**-6`, `rtol = 0` at small d; the test passes its own tolerance).
   - **`judge_report`, fail through `out`**: one element outside the tolerance in one draw gives `FAIL` with that draw's `failed` only and `cache_differences == 0`; `0x7FC0` elements in `out` are failed and non-finite.
   - **`judge_report`, fail through the cache, each region compared** (ADR-0165 decision 10, last paragraph but one: "the code task's tests of the judge construct such reports to show each region compared"): with `out` passing, a report whose cache differs in exactly one element of each of these gives `FAIL` with `failed == 0` and the right `cache_differences`: a leading guard row, rows 0 … P − 1, rows P … l − 1 (still `0x7FC0`, the "no write" case), a trailing guard row; in `cache_k` and in `cache_v`; and a block written one row late (into the first trailing guard row) or one row early. A count over several elements and both allocations is summed.
   - **`judge_report`, broken**: every wrong form gives `REPORT_FORM` and no draw is regenerated (show this, for example, with a `monkeypatch` on the new module's reference to `draw_inputs`): one byte short, one byte long, a missing end mark, empty, and the length of another `l` or `h_kv`; a check value that disagrees in the first, middle or last draw gives `CHECK_VALUE`; a report made with another seed gives `CHECK_VALUE`; a report whose reported allocation differs before the call (a different fill in a guard row, so the check value differs) gives `CHECK_VALUE`, never `FAIL`.
   - **`judge_report`, refusals**: every refusal of AC 4, raised before the report is touched or a draw is regenerated, including a refused tolerance and a `bytearray` or `memoryview` report giving `TypeError`.
   - **`run_bf16_sdpa_kv_cache_verification` with the stand-in**: the argv is exactly `program_arguments(dims, draws=..., seed=...)`; `cwd` and `env` are passed through; a passing report gives a completed `PASS`; a cache-only difference gives a completed `FAIL`; a timeout gives `TIMEOUT`; a non-zero status (and a signal on POSIX) gives `EXIT_STATUS` whatever was written; a wrong form or check value is broken; `run.stdout == b""` and `stderr` is kept; every refusal of AC 5 happens before anything is started (the stand-in's record file does not exist); an empty sequence and a non-iterable executable; `ProgramNotFoundError` from `local_run` is passed on.
   - **Real `clang`** (POSIX only; skipped without `clang` locally and failing on CI without it, as the `toolchain` fixture of `test_bf16_verification_sdpa_kv_cache.py` does). Build with `bf16_verification_build.build_bf16_verification_executable("sdpa_kv_cache", ...)` test-local kernels written in the test (they may follow `PLAIN` of that test file; the text rule of AC 1 applies to `hilclaw/` only, not to tests):
     - a plain kernel (copy `k_new`/`v_new` into rows P … l − 1, then a binary32 evaluation with round-to-nearest-even output, linking `-lm` as a trailing flag if it calls `expf`/`sqrtf`) gives `PASS` with all counts 0 at a small shape with m > 1 and P > 0, and **at the decode S = 128 op_signature shape `(1, 128, 32, 8, 64)`** (P = 127; ADR-0165 Consequences: a kernel run at P > 0 shows the drawn cache rows, their expected placement and the leading guard exercised, and that the two generators agree) under `atol = 2.2e-3`, `rtol = 0` (decision 9's bound 2.154·10^−3 at d = 64, l = 128); optionally also at the prefill S = 128 shape `(128, 128, 32, 8, 64)` with one draw;
     - the same kernel that also writes one element of the first trailing guard row of `cache_k` gives `FAIL` with `failed == 0` and `cache_differences == 1` per draw.
     These are not the calibration kernels of ADR-0165 decision 10 and are not placed under `tests/harness/calibration/`.
   - Do not add tests that target test code (D12 ⑤).
9. **No other behaviour change**: leave unchanged `bf16_sdpa_kv_cache_arrays.py`, `bf16_rope_verification.py`, `bf16_verification.py`, `bf16_verification_arrays.py`, `bf16_verification_build.py`, `bf16_verification.h`, the six C programs, `local_run.py`, `verification.py`, `verification_arrays.py`, every existing test file and the CI workflow. Add no dependency. The local `pytest` (coverage at or above the 80 % line and function gates) and `ruff check` / `ruff format --check` are green.
10. **Process**: code mode (CLAUDE.md A-13). Draft PR titled with `T-0468`, body ending with `Task: T-0468`; reviewer cycle (dev-code-review), at most 7 rounds, until CI is green; then `gh pr merge --squash --body` with the PR body, and delete the branch. The reviewer checks at least:
    - the command line against ADR-0165 decision 3, with P absent, and no standard input (decision 2);
    - the report length and split against decision 8 and the program's header comment;
    - the check value over the whole allocations, and broken-not-fail, against decision 7;
    - the cache comparison against decision 8: bit-exact, expected arrays from the Python side only, every region compared;
    - the verdict and `DrawCounts` against decision 8;
    - that every refusal comes before anything is regenerated or started;
    - that `sdpa_kv_cache_bf16_contract` is not named in the new module;
    - that no other module or existing test changed.

## Out of Scope

- Slice 4: the four calibration kernels of ADR-0165 decision 10 (conforming, V1 violating, head-mapping failing, no-cache-write failing) with their tests under `tests/harness/calibration/`.
- Adding `sdpa_kv_cache` to `bf16_verification_arrays.KINDS`, `bf16_verification.py` or `bf16_rope_verification.py`.
- Changing `tests/harness/test_bf16_verification_sdpa_kv_cache.py` or `tests/harness/test_bf16_sdpa_kv_cache_arrays.py` to use the new module.
- Registering `sdpa_kv_cache` with `correctness.check`, `spec.write` or the instance start (ADR-0165 Boundaries).
- Tolerance values, seeds, draws, other shapes, the model program's cache capacity, the bf16 timing run, fp16.
- Editing any ADR, including the "less exact" sentences that ADR-0165 Consequences lists.

## Follow-ups

- Next task (planner candidate): ADR-0165 code slice 4, the four calibration kernels of decision 10 (functional test at `(128, 128, 32, 8, 64)`, P = 0; failing kernel with query head j served by KV head j mod h_kv; second failing kernel that writes no cache row), tested through `run_bf16_sdpa_kv_cache_verification`.

## Result

- **DONE.** PR #281 (`T-0468: Add the runner and judge of the bf16 SDPA-with-KV-cache verification run (ADR-0165 slice 3)`), squash-merged with the PR body as the message; branch `claude/T-0468-bf16-sdpa-kv-cache-verification-runner` deleted.
- Review: 2 rounds by a context-isolated `dev-reviewer` (round 1 Approve with two nits, one fixed — the allocation size computed once per draw — and one declined as not required by AC 8; round 2 Approve, no findings).
- CI green on `0920c7c5`: Python gate 3.11/3.14 (including the real-`clang` tests), Coverage gate, C gate, Test presence, shellcheck. Local: full `pytest` 32162 passed, coverage 97 % total, new module 100 %; `ruff check` / `ruff format --check` clean.
- Language: Python — the runner next to `bf16_rope_verification.py`, reusing its result types and `local_run.run`.
- Size: about 290 changed lines outside tests in 2 files (new module, `hilclaw/harness/__init__.py`), plus the new test file `tests/harness/test_bf16_sdpa_kv_cache_verification.py`.
- Follow-ups: none new. Next task candidate as above: ADR-0165 code slice 4, the four calibration kernels of decision 10, tested through `run_bf16_sdpa_kv_cache_verification`.
