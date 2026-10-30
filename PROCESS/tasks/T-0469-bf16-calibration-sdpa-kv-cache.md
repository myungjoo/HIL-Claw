---
id: T-0469
title: Add the calibration of the bf16 SDPA-with-KV-cache verification run (four C kernels and an sdpa_kv_cache table in test_bf16_calibration.py, ADR-0165 decision 10, code slice 4)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0466, T-0467, T-0468]
touchesFiles: [tests/harness/calibration/sdpa_kv_cache_bf16_conforming.c, tests/harness/calibration/sdpa_kv_cache_bf16_failing.c, tests/harness/calibration/sdpa_kv_cache_bf16_failing_cache.c, tests/harness/calibration/sdpa_kv_cache_bf16_violating.c, tests/harness/test_bf16_calibration.py]
estimatedSize: {loc: 0, files: 0}   # all test code: four C fixture kernels and additions to an existing test file, excluded from the cap (D4), as in T-0457, T-0458 and T-0464
hq: []
---
## Why

**State on `main` `861c8553`.** ADR-0165 (T-0465, `24d4e0a4`) records how one built bf16 SDPA-with-KV-cache kernel (kind `sdpa_kv_cache`, contract ADR-0162) is verified on `cpu_standin`. Its Consequences (line 146) list four code slices in landing order. Three are done:
- slice 1: T-0466 (PR #279, `d53b898e`) added `hilclaw/harness/bf16_verification_sdpa_kv_cache.c` and `sdpa_kv_cache` in `bf16_verification_build.PROGRAM_SOURCES`;
- slice 2: T-0467 (PR #280, `35b860bb`) added `hilclaw/harness/bf16_sdpa_kv_cache_arrays.py`;
- slice 3: T-0468 (PR #281, `d946e565`) added the runner `hilclaw/harness/bf16_sdpa_kv_cache_verification.py` (`DrawCounts`, `program_arguments`, `judge_report`, `run_bf16_sdpa_kv_cache_verification`).

**This task is slice 4: "the four calibration kernels with their tests"** (ADR-0165 decision 10). ADR-0003 decision 6 (a) wants them in the change that makes the harness verify the kind; that change is now complete. After this task `sdpa_kv_cache` is calibrated like the other five bf16 kinds (T-0457, T-0458, T-0464), and every instance-target kind of ADR-0152 decision 2 has a calibrated bf16 verification run.

**The four kernels** (decision 10): conforming; violating (V1: right on the functional test's seed and shape, its output and its cache, wrong elsewhere); failing (query head j served by KV head j mod h_kv); and a second failing kernel that computes `out` as the conforming one but writes no cache row, so that a harness that skipped the cache comparison could not pass the calibration.

**The form of the violating kernel.** Decision 10 fixes the functional test's shape at (m, l, h, h_kv, d) = (128, 128, 32, 8, 64). The earlier violating kernels hold the whole correctly rounded output of the known draw as a table. At this shape that table has m·h·d = 262,144 entries, about 1.6 MB of C source. CLAUDE.md keeps large artefacts out of git. This task therefore asks for a violating kernel that recognises the known draw: it holds the first 16 patterns of `q` of draw 0 of the known seed, computes the conforming operation when the 16 elements match, and otherwise writes a constant output. This is still V1 of ADR-0003 decision 3 ("output that is right only on inputs known in advance"). Its wrong output does not depend on the inputs the way the operation does (ADR-0003 decision 7). ADR-0003 decision 7 leaves where the functional test's expected outputs come from to the code task, and decision 10 of ADR-0165 does not prescribe a table. A run-time seed matches all 16 elements with probability 2^−128, a negligible exception in the sense of ADR-0003 decision 4. The reviewer checks this reading (AC 6).

**Where the tests go.** The CI "harness pass" step (`.github/workflows/ci.yml` lines 98-115) runs `tests/harness/test_calibration.py` and `tests/harness/test_bf16_calibration.py` by name and fails if a case is skipped. The new cases go into `test_bf16_calibration.py`, so `ci.yml` needs no edit. They need their own table, fixture and test, because the runner differs (`run_bf16_sdpa_kv_cache_verification` takes five dimensions and returns `DrawCounts`), and there is a fourth state.

**Size.** The C kernels and the test additions are test code. D4 excludes them from the cap, as T-0457, T-0458 and T-0464 counted theirs. No package code, workflow or document changes.

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items that P2-14 needs, so the D18 rule does not apply. Unresolved HQs still hold the round-loop items and P2-5 (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4). Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0468.

**D16.** The tests build with `clang` and run local processes through `run_bf16_sdpa_kv_cache_verification`. Without a POSIX system or without `clang` they skip locally; on CI they fail without `clang`. Nothing starts `claude` or needs a board, a model file or an API key. ADR-0165 Consequences: "Runtime acceptance items: none."

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (test code excluded), the naming and the test rules.
  - For this task: branch `claude/T-0469-<slug>`; commit trailer `Task: T-0469`; code mode, so a Draft PR whose body ends with `Task: T-0469`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "브랜치·merge 절차" (code mode), "테스트 규칙"; "현재 프로젝트 상태 주의사항": "바이너리 금지".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `PROCESS/tasks/T-0464-bf16-calibration-rope.md`: the Acceptance Criteria and the whole `## Result`. This task follows that model, with the differences stated below.
- `ARCHITECTURE/decisions/ADR-0165-od31-bf16-sdpa-kv-cache-verification-run.md`:
  - decision 5 (lines 61-67): the allocations, guard rows and the `0x7FC0` fills;
  - decision 8 (lines 82-88): the cache comparison and the verdict;
  - decision 9 (lines 90-96): the comparison of `out`, the warning about `rtol` with `atol` = 0, and the absolute bound 2.154·10^−3 at d = 64, l = 128;
  - decision 10 (lines 98-104): the whole calibration rule — the functional test's shape, the failing kernel and why it is outside, the second failing kernel, and the list of what no test may require to fail;
  - Consequences, line 146.
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`, decisions 2 to 7 (lines 29-88).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`: decisions 4 to 6 (lines 52-77: the cache operands, the other operands' layout and the operation), decision 8 (lines 90-93, the output conversion), decision 9 (lines 94-102, the prototype) and decision 11 (lines 133-148, the guarantees and obligations at a call).
- `tests/harness/test_bf16_calibration.py`: the whole file (159 lines).
- Under `tests/harness/calibration/`: the three `rope_bf16_*.c` files, for the layout, the header comments and round-to-nearest-even.
- `tests/harness/test_bf16_sdpa_kv_cache_verification.py`, lines 922-1039: the real-`clang` tests of T-0468. Their `KERNEL` text is a sketch of the conforming kernel here; `DECODE_TOLERANCE` is at line 927.
- `hilclaw/harness/bf16_verification_sdpa_kv_cache.c`, lines 1-67: the header comment and the kernel prototype.
- `hilclaw/harness/bf16_sdpa_kv_cache_verification.py`: `DrawCounts` and `run_bf16_sdpa_kv_cache_verification` (from line 97).
- `hilclaw/harness/bf16_sdpa_kv_cache_arrays.py`: `draw_inputs` and `reference`. Use them for the fingerprint constants and the evidence of AC 5, in a throwaway interpreter that changes no repository file.
- `.github/workflows/ci.yml`, lines 98-115: the "harness pass" step.

## Acceptance Criteria

1. **Four new C files under `tests/harness/calibration/`**, ASCII and LF: `sdpa_kv_cache_bf16_conforming.c`, `sdpa_kv_cache_bf16_failing.c`, `sdpa_kv_cache_bf16_failing_cache.c` and `sdpa_kv_cache_bf16_violating.c`. Each file:
   - defines exactly the contract symbol with the program's prototype, `void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out)`, every other identifier `static`;
   - compiles alone under the C gate's line (`clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`);
   - has a short header comment in the form of the existing `*_bf16_*.c` kernels: the state, what it computes, and that it is test data of `tests/harness/test_bf16_calibration.py`, not a reference, a baseline or a catalog entry.
2. **What each kernel does** (ADR-0165 decision 10; ADR-0162 decisions 4, 6 and 8; ADR-0003 decisions 2 and 3):
   - **Conforming**: copies `k_new` into rows P … l − 1 of `cache_k` and `v_new` into those of `cache_v` (P = l − m). Then, for each row i and query head j, with g = j / (h / h_kv), it evaluates in binary32: scores of `q` row (i, j) against key rows 0 … P + i of KV head g, times 1/√d; the row maximum subtracted; `expf`; division by the sum; the weighted sum of value rows. It rounds to bf16 with round-to-nearest-even on the `float` bit pattern. It reads no row past P + i and no guard row. It may follow `KERNEL` of `test_bf16_sdpa_kv_cache_verification.py`. If it calls `expf` or `sqrtf`, it is linked with the file's existing `TRAILING_FLAGS = ("-lm",)`.
   - **Failing**: the conforming kernel with g = j mod h_kv in place of j / (h / h_kv), everything else unchanged, the cache write included.
   - **Failing (cache)**: computes `out` exactly as the conforming kernel, from `q`, `k_new`, `v_new` and cache rows 0 … P − 1 (keys and values at positions P … P + i come from `k_new` and `v_new` directly), and writes **no** cache element.
   - **Violating (V1)**: holds the first 16 patterns of `q` of draw 0 of the test's known seed at the functional test's shape. If the first 16 elements of `q` equal them, it does what the conforming kernel does (output and cache). Otherwise it writes the cache as the conforming kernel does and the constant pattern `0x3F00` (0.5) to every element of `out`. (At P = 0, row 0's exact output is `v_new`(0, g, e) ∈ ±[0.5, 1), so every negative one misses by at least 1.)
     - Compute the 16 constants in a throwaway interpreter from `bf16_sdpa_kv_cache_arrays.draw_inputs(dims, seed=known, draw=0).q[:16]`.
     - Name the seed, the shape and the rule (16 elements of `q`, constant output otherwise) in the header comment.
     - Give the reason for this form in one line in the commit body, the PR body and `## Result`: a table of the 262,144 output patterns would be about 1.6 MB of source.
3. **Additions to `tests/harness/test_bf16_calibration.py`.** Leave the existing `KINDS`, `ROPE`, `STATES`, fixtures, helpers and test functions unchanged. If a line must change, give the reason in `## Result`. Add:
   - an import of `run_bf16_sdpa_kv_cache_verification` from `hilclaw.harness.bf16_sdpa_kv_cache_verification`;
   - one table entry for `sdpa_kv_cache`: dims `(128, 128, 32, 8, 64)` (decision 10; P = 0), the known seed (2026, as for the other rows) and a tolerance, with a one-line margin comment, as the existing rows have (ADR-0003 decision 7);
   - a states table for this kind: the three entries of `STATES` plus `"failing_cache": (Verdict.FAIL, Verdict.FAIL)`. Reuse `STATES` for the first three rather than restating them;
   - a session fixture that builds the four kernels with `build_bf16_verification_executable("sdpa_kv_cache", ...)`. It uses the same `FLAGS`, `TRAILING_FLAGS`, `BUILD_TIMEOUT` and skip-or-fail rules as `executables`;
   - a test parametrized over the four states and `draws` in {1, 3}. It reuses `seed_taken_at_run_time`, and checks the functional verdict on the known seed with one draw and the contract verdict on a run-time seed. Like `rope_verdict`, it asserts that the run is not broken and shows the seed, the broken condition, the exit status, standard error and the counts on failure.
   - The file gains 4 × 2 = 8 cases, 44 in all for the "harness pass" step (6 fp32 + 38 bf16).
   - Give each choice one line of reason in the commit body, the PR body and `## Result`:
     - **Shape**: `(128, 128, 32, 8, 64)`, as decision 10 requires; P = 0 for both runs.
     - **Tolerance (`rtol`, `atol`)**: the test's own values, not the harness's, bounded by decisions 9 and 10:
       - the conforming kernel must pass on any seed, which needs `atol` ≥ 2.154·10^−3 (decision 9 at l = 128). Do not use `atol` = 0 with an `rtol`, because y cancels;
       - the failing and violating kernels must fail, which needs `atol` + `rtol` < 1 on the row-0 elements;
       - for example `rtol` = 0 and `atol` = 2^−8 (3.906·10^−3): about 1.8 times the conforming bound, far below 1.
     - Assert the verdict only (ADR-0003 decision 4). Do not require a count of failing elements. For `failing_cache`, an assertion of `failed == 0` in every draw of the contract run is welcome, because decision 10 says its output passes. Do not assert the exact number of cache differences.
   - Optional: one more test that runs the conforming and the `failing_cache` kernel at the decode op_signature shape `(1, 128, 32, 8, 64)` (P = 127) on a run-time seed, expecting PASS and FAIL. If added, it uses an `atol` of at least 2.2·10^−3 and adds to the case count you record. ADR-0165 Consequences asks for a kernel run at P > 0; T-0468 already has one, so this test is optional.
4. **No other change.**
   - Leave these unchanged: `hilclaw/`, `.github/workflows/ci.yml`, `tests/harness/test_calibration.py`, the existing fixtures under `tests/harness/calibration/`, every other test file, `pyproject.toml` and every document.
   - Add no dependency.
   - The local `pytest` and `ruff check` / `ruff format --check` runs are green.
   - Coverage of `hilclaw/` stays at or above 80 % for lines and functions. It cannot drop, since no package code changes.
5. **Evidence of the states.** On a machine with `clang` (CI counts; WSL if the executor has it), record in `## Result`:
   - for each of the four states, the `DrawCounts` on the known draw and on one run-time seed;
   - the largest deviation of the conforming kernel, relative to `atol` and to the bound 2.154·10^−3, over at least 200 random draws at the functional shape;
   - the smallest deviation of the failing kernel over its failing elements, on the same draws;
   - for the `failing_cache` kernel, that `failed == 0` and `cache_differences > 0` in every draw;
   - the CI log line of the "harness pass" step, which must show `calibration: 44 case(s) selected, 0 skipped`, or the count with the optional test.
6. **Process**: code mode (CLAUDE.md A-13).
   - Open a Draft PR titled with `T-0469`, whose body ends with `Task: T-0469`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - that the conforming kernel follows ADR-0162 decisions 4, 6 and 8: the cache write, the head group g = j / (h / h_kv), the causal mask at P + i, the scale, round-to-nearest-even;
     - that the failing kernel changes only the head mapping, to j mod h_kv;
     - that the `failing_cache` kernel computes `out` as the conforming one and writes no cache element;
     - that the violating kernel's 16 constants are the first 16 elements of `q` of draw 0 of the known seed at the functional shape (regenerate them), and that its reading as V1 holds against ADR-0003 decisions 3, 4 and 7 and ADR-0165 decision 10;
     - that the tolerance passes the conforming kernel with a margin and gives FAIL for the other three;
     - that both runs use the functional shape with P = 0;
     - that no test requires a fault from decision 10's "no test may require these to fail" list to fail.

## Out of Scope

- Any change to `hilclaw/` (program, arrays, runner, build), to `ci.yml`, to `test_calibration.py`, to `test_bf16_sdpa_kv_cache_verification.py` or to the existing fixtures.
- Kernels for the faults that decision 10 says no test may require to fail. Zero, subnormal or non-finite inputs (#5 B-7).
- Calibration at other shapes, or default tolerances, seeds, draws, time limits or build flags of the harness (ADR-0165 Boundaries; OD-16 sub-questions ① and ⑤).
- Registering `sdpa_kv_cache` with `correctness.check`, `spec.write` or the instance start (ADR-0165 Boundaries).
- The bf16 timing run, fp16, the model program's cache capacity.
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`, including the "less exact" sentences that ADR-0165 Consequences lists.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, ADR-0165 has all its code slices and its calibration. Its "Later work" is the record of the bf16 timing run. The planner then picks the next P2-11 to P2-14 work in PLAN order, for example the remaining P2-13 executor slices.

## Result
**DONE.** PR #282 https://github.com/myungjoo/HIL-Claw/pull/282, squash commit `6a002fa7` on `main` (body ends with `Task: T-0469`); branch deleted (remote and local).

**Review**: 1 round, Approve (fresh-context `dev-reviewer`, https://github.com/myungjoo/HIL-Claw/pull/282#issuecomment-6396590422). The reviewer regenerated the 16 violating constants, compiled each file alone under the C gate's line, checked the failing kernel changes only `g = j % h_kv` and the failing_cache kernel writes no cache element, accepted the V1 reading (ADR-0003 decision 3 defines V1 by observable behaviour; 2^-128 is a negligible exception under decision 4; the constant wrong output satisfies decision 7; ADR-0165 decision 10 prescribes no table), and ran the 44 calibration cases under WSL. One minor, non-blocking note, not acted on (it is about this task file's Why, which the executor does not edit): the Why cites ADR-0003 decision 7's "where expected outputs come from" as support for the violating form, but that sentence concerns the functional test's expected outputs; the reading stands on decision 3 and ADR-0165 decision 10 alone.

**CI**: 1 run, all six checks green, https://github.com/myungjoo/HIL-Claw/actions/runs/40185400397. C gate "harness pass": `calibration: 44 case(s) selected, 0 skipped` (6 fp32 + 38 bf16). Python gates and coverage gate: `33875 passed, 50 skipped`; lines 11236/11277 = 99.63%, functions 1088/1088 = 100.00%.

**Changes**: four kernels under `tests/harness/calibration/` (`sdpa_kv_cache_bf16_{conforming,failing,failing_cache,violating}.c`) and, in `test_bf16_calibration.py`, an import of `run_bf16_sdpa_kv_cache_verification`, an `SDPA_KV_CACHE` row with a margin comment, `SDPA_KV_CACHE_STATES` (`STATES` plus `failing_cache`), a `sdpa_kv_cache_executables` session fixture (same `FLAGS`, `TRAILING_FLAGS`, `BUILD_TIMEOUT`, skip-or-fail rules), a `sdpa_kv_cache_run` helper and a test over the four states x draws {1, 3}. No existing line changed. The optional decode-shape test was not added (T-0468 already runs the conforming kernel at P = 127).

**Violating form**: a table of the 262,144 output patterns would be about 1.6 MB of source, so the V1 kernel recognises the known draw by the first 16 elements of `q` (draw 0, seed 2026, shape (128, 128, 32, 8, 64)) and otherwise writes the cache correctly and 0x3F00 (0.5) to every element of `out`. The 16 constants were computed in a throwaway interpreter from `draw_inputs(dims, seed=2026, draw=0).q`; a run-time seed matches them with probability 2^-128.

**Test choices** (test values only):
- Shape (128, 128, 32, 8, 64), as ADR-0165 decision 10 requires; P = 0 for both runs.
- Tolerance rtol = 0, atol = 2**-8 (3.906e-3): about 1.8 times the conforming bound 2.154e-3 of decision 9 (no rtol with atol = 0, since y cancels), far below the miss of >= 1 at row 0 for the failing and violating kernels.
- Known seed 2026, as for the other rows.
- Only the verdict is asserted (ADR-0003 decision 4); for `failing_cache` also `failed == 0` in every draw of the contract run (decision 10). No count of cache differences is asserted.

**Evidence of the states** (WSL clang 14, venv outside the repository, rtol 0, atol 2**-8). `DrawCounts` (failed, non_finite, cache_differences), known seed 2026 (1 draw) / run-time seed 11219411663970703364 (3 draws):
- conforming (0, 0, 0) / (0, 0, 0) x3: PASS / PASS;
- failing (225118, 0, 0) / (225168, 0, 0), (225304, 0, 0), (225105, 0, 0): FAIL / FAIL;
- failing_cache (0, 0, 131072) / (0, 0, 131072) x3: FAIL / FAIL;
- violating (0, 0, 0) / (262035, 0, 0), (262013, 0, 0), (262057, 0, 0): PASS / FAIL.
- Over 200 draws of seed 13284484401230342356: conforming largest |dev| 1.9532e-3 = 0.500 of atol and 0.907 of the bound 2.154e-3; failing 45,017,956 of 52,428,800 elements outside, every draw FAIL, smallest |dev| among the failing elements 3.90625e-3 + 1e-16 (just past atol, as expected of a count near the threshold; the verdict rests on the row-0 misses of >= 1); failing_cache `failed == 0`, `non_finite == 0` and `cache_differences == 131072 > 0` in every draw.

**Local**:
- WSL: `test_calibration.py` + `test_bf16_calibration.py` 44 passed (6 fp32 + 38 bf16). Each new `.c` compiles alone under `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`; `nm` shows only `hilclaw_sdpa_kv_cache_bf16` as a defined global. The new files are ASCII with LF.

- Windows (Python 3.14.4): full `pytest` 32162 passed, 1763 skipped (the new cases skip: no POSIX); `ruff check .` and `ruff format --check .` clean.

**Language**: C for the kernels (kernel language of `cpu_standin`, ADR-0003 decision 5); Python for the test. No layer-2 code changed.

**Follow-ups**: none new. The planner's follow-up stands (ADR-0165 has all its code slices and its calibration; next P2-11 to P2-14 work in PLAN order). No HQ.
