---
id: T-0464
title: Add the three-state calibration of the bf16 RoPE verification run (three C kernels and a rope table in test_bf16_calibration.py, ADR-0164 decision 11, code slice 4)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0461, T-0463]
touchesFiles: [tests/harness/calibration/rope_bf16_conforming.c, tests/harness/calibration/rope_bf16_failing.c, tests/harness/calibration/rope_bf16_violating.c, tests/harness/test_bf16_calibration.py]
estimatedSize: {loc: 0, files: 0}   # all test code: three C fixture kernels and additions to an existing test file, excluded from the cap (D4), as in T-0457 and T-0458
hq: []
---
## Why

**State on `main` `8a288adc`.** ADR-0164 (T-0459, `f9b8096`) records how one built bf16 RoPE kernel (kind `rope`) is verified on `cpu_standin`. Its Consequences (line 136) list four code slices. Three are done:
- slice 1: T-0460 (`48f1d05`) gave `hilclaw.local_run.run` the optional `stdin_data` argument;
- slice 2: T-0461 (`4043e70a`) added `hilclaw/harness/bf16_verification_rope.c` and `rope` in `bf16_verification_build.PROGRAM_SOURCES`;
- slice 3: T-0462 (`6297bf58`) added `hilclaw/harness/bf16_rope_arrays.py`, and T-0463 (`e4b2ec12`) added the runner `hilclaw/harness/bf16_rope_verification.py` (`program_arguments`, `judge_report`, `run_bf16_rope_verification`).

**This task is slice 4: the calibration of decision 11.** Decision 11 asks for three hand-written C kernels for `rope`: conforming, violating (V1) and failing (cos and sin swapped). ADR-0003 decision 6 (a) wants them in the change that makes the harness verify the kind. That change is now complete, so these three are due. After this task, `rope` is calibrated like the four kinds of ADR-0163 (T-0457, T-0458).

**Where the tests go.** The CI "harness pass" step (`.github/workflows/ci.yml` lines 98-115) runs `tests/harness/test_calibration.py` and `tests/harness/test_bf16_calibration.py` by name, and fails if a case is skipped. The rope cases are added to `test_bf16_calibration.py`, so `ci.yml` needs no edit. They need their own table, fixture and test function, because the runner differs: `run_bf16_rope_verification` takes `(m, h, d)` and a start position `start`, which `run_bf16_verification` does not. The existing `KINDS`, `STATES`, fixture and test stay as they are.

**Size.** The C kernels and the test additions are test code. D4 excludes them from the cap, as T-0457 and T-0458 counted theirs. No package code, workflow or document changes.

**PLAN order and D18.** This is the harness verification of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items that P2-14 needs, so the D18 rule does not apply. Unresolved HQs still hold the round-loop items and P2-5 (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4). Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0463.

**D16.** The tests build with `clang` and run local processes through `run_bf16_rope_verification`. Without a POSIX system or without `clang` they skip locally, and they fail on CI without `clang`. Nothing starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (test code excluded), the naming and the test rules.
  - For this task: branch `claude/T-0464-<slug>`; commit trailer `Task: T-0464`; code mode, so a Draft PR whose body ends with `Task: T-0464`.
- `CLAUDE.md`, "상시 규칙":
  - "코멘트 최소화";
  - "브랜치·merge 절차" (code mode);
  - "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `PROCESS/tasks/T-0458-bf16-calibration-rmsnorm-swiglu.md`: the Acceptance Criteria and the whole `## Result`. This task follows the same model. Its "Violating constants" paragraph is the precedent for rounding a float64 reference to bf16 and checking for near ties.
- `ARCHITECTURE/decisions/ADR-0164-od31-bf16-rope-verification-run.md`:
  - decision 4 (lines 52-58): the start position P;
  - decision 8 (lines 78-80): the output fill `0x7FC0`;
  - decision 9 (lines 82-86): the reference y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c, with c = row(i, 2p) and s = row(i, 2p + 1);
  - decision 10 (lines 88-91): the comparison, and the note "for whoever sets a tolerance" (every compliant output is within an absolute 2^−8 + 2^−21; an `rtol` with `atol` = 0 can fail a conforming kernel);
  - decision 11 (lines 93-97): the whole calibration rule, the failing kernel, why it is outside with P = 0, and the list of what no test may require to fail.
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`, decisions 2 to 7 (lines 29-88).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`: decision 6 (lines 62-67, the layout of `x`, `freqs_cis` and `out`), decisions 7 and 8 (lines 68-78, the operation and its rounding), decision 9 (lines 79-87, the prototype) and decision 11 (lines 112-125, the guarantees and obligations at a call).
- `tests/harness/test_bf16_calibration.py`: the whole file (100 lines).
- Under `tests/harness/calibration/`: `swiglu_bf16_conforming.c`, `swiglu_bf16_failing.c` and `elementwise_add_bf16_violating.c`, for the layout, the header comments and round-to-nearest-even.
- `tests/harness/test_bf16_rope_verification.py`, lines 751-837: the real-`clang` tests of T-0463. Their `conforming` kernel body is a sketch of the conforming kernel here. Their tolerance `TOLERANCE` is at line 63.
- `hilclaw/harness/bf16_verification_rope.c`, lines 1-62: the header comment and the kernel prototype.
- `hilclaw/harness/bf16_rope_verification.py`, lines 156-221: `run_bf16_rope_verification`.
- `hilclaw/harness/bf16_rope_arrays.py`: `table_rows`, `draw_x` and `reference`. Use them to compute the violating constants in a throwaway interpreter.
- `.github/workflows/ci.yml`, lines 98-115: the "harness pass" step.

## Acceptance Criteria

1. **Three new C files under `tests/harness/calibration/`**, ASCII and LF: `rope_bf16_conforming.c`, `rope_bf16_failing.c` and `rope_bf16_violating.c`. Each file:
   - defines exactly the contract symbol with the program's prototype, `void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out)`;
   - compiles alone under the C gate's line (`clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`);
   - has a short header comment in the form of the existing `*_bf16_*.c` kernels: the state, what it computes, and that it is test data of `tests/harness/test_bf16_calibration.py`, not a reference, a baseline or a catalog entry.
2. **What each kernel does** (ADR-0164 decision 11, ADR-0003 decisions 2 and 3):
   - **Conforming**: the operation of ADR-0161 decision 7.
     - It widens each bf16 element of `x` to `float` (the pattern shifted left by 16, through `memcpy`).
     - It reads c = `freqs_cis[i*d + 2p]` and s = `freqs_cis[i*d + 2p + 1]` for token i, the same for every head.
     - It computes y₀ = x₀·c − x₁·s and y₁ = x₀·s + x₁·c in `float`.
     - It rounds to bf16 with round-to-nearest-even on the `float` bit pattern, as the existing kernels do.
     - It needs no `<math.h>`.
   - **Failing**: cos and sin swapped, y₀ = x₀·s − x₁·c and y₁ = x₀·c + x₁·s. Everything else is as in the conforming kernel.
   - **Violating (V1)**: the kernel ignores `x` and `freqs_cis` and writes a table of bf16 patterns. The table is the correctly rounded output of draw 0 of the test's known seed, at the test's shape and P = 0, repeated by index modulo its length, as the existing violating kernels do.
     - Compute the constants in a throwaway interpreter that changes no repository file, from `draw_x(dims, seed=known, draw=0)`, `table_rows(dims, start=0)` and `reference`.
     - Round the float64 reference to bf16 directly (round-to-nearest-even on float64).
     - Record in `## Result` that no element was a near tie where a binary32 evaluation would round differently, or how one was handled.
     - Name the seed, the shape and P in the header comment.
3. **Additions to `tests/harness/test_bf16_calibration.py`.** Leave the existing `KINDS`, `STATES`, `executables` fixture, `verdict` helper and test function unchanged. If a line must change, give the reason in `## Result`. Add:
   - an import of `run_bf16_rope_verification` from `hilclaw.harness.bf16_rope_verification`;
   - one table entry for `rope`: dims `(m, h, d)`, a known seed, the start position P = 0 and a tolerance. Put a one-line margin comment next to it, as the existing rows have (ADR-0003 decision 7);
   - a session fixture that builds the three rope kernels with `build_bf16_verification_executable("rope", ...)`. It uses the same `FLAGS`, `BUILD_TIMEOUT` and skip-or-fail rules as `executables`;
   - a test parametrized over `STATES` and `draws` in {1, 3}. It reuses `STATES` and `seed_taken_at_run_time`, and checks the functional verdict on the known seed with one draw and the contract verdict on a run-time seed, both at P = 0. Like `verdict`, it asserts that the run is not broken and shows the seed, the broken condition, the exit status and standard error on failure.
   The file gains 3 × 2 = 6 cases, 36 in all for the "harness pass" step (6 fp32 + 30 bf16).
   Give each choice one line of reason in the commit body, the PR body and `## Result`:
   - **Shape**: small, for example `(3, 2, 4)`: 24 elements, rows 0 to 2, so row 0 (c = 1, s = +0) is included.
   - **P**: 0 for both runs, as decision 11 requires for the functional test. The failing kernel is outside at row 0 on every seed.
   - **Tolerance (`rtol`, `atol`)**: the test's own values, not the harness's. Decision 10 and decision 11 bound the choice:
     - the conforming kernel must pass on any seed, which needs `atol` ≥ 2^−8 + 2^−21. Do not use `atol` = 0 with an `rtol`, because an output may cancel;
     - the failing kernel must fail, which needs `atol` + `rtol`·|ref| < 1 on the row-0 elements (|ref| < 1 there);
     - for example `rtol` = 0 and `atol` = 2^−7: twice the conforming bound, and far below 1.
     The failing and violating kernels must get the verdict FAIL on a run-time seed.
   - Assert the verdict only, as ADR-0003 decision 4 asks and as T-0457 and T-0458 did. Do not require every element of the failing kernel to lie outside.
4. **No other change.**
   - Leave these unchanged: `hilclaw/`, `.github/workflows/ci.yml`, `tests/harness/test_calibration.py`, the existing fixtures under `tests/harness/calibration/`, the other tests, `pyproject.toml` and every document.
   - Add no dependency.
   - The local `pytest` and `ruff check` / `ruff format --check` runs are green.
   - Coverage of `hilclaw/` stays at or above 80 % for lines and functions. It cannot drop, since no package code changes.
5. **Evidence of the states.** On a machine with `clang` (CI counts; WSL if the executor has it), record in `## Result`:
   - for each state, the failing-element counts on the known draw and on one run-time seed;
   - the largest deviation of the conforming kernel relative to the tolerance bound, over at least 1000 random draws at the test's shape and P = 0;
   - the smallest deviation of the failing kernel over the elements that fail, on the same draws.
   The CI log of the "harness pass" step must show `calibration: 36 case(s) selected, 0 skipped`, or the equivalent count.
6. **Process**: code mode (CLAUDE.md A-13).
   - Open a Draft PR titled with `T-0464`, whose body ends with `Task: T-0464`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - that the conforming kernel follows ADR-0161 decision 7: the row of token i for every head, the pair (2p, 2p + 1), round-to-nearest-even;
     - that the failing kernel swaps cos and sin and changes nothing else;
     - that the violating constants are draw 0 of the known seed at the test's shape and P = 0 (regenerate them);
     - that the tolerance passes the conforming kernel with a margin and gives FAIL for the failing and violating kernels;
     - that both runs use P = 0;
     - that no test requires a fault from decision 11's "no test may require these to fail" list to fail: a bf16-rounded table, truncation, fused or unfused multiply-adds, the sign of a zero, an input written by the kernel, or table or binding errors.

## Out of Scope

- Any change to `hilclaw/` (program, arrays, runner, build), to `ci.yml`, to `test_calibration.py` or to the existing fixtures.
- Kernels for the faults that decision 11 says no test may require to fail. Zero, subnormal or non-finite inputs (#5 B-7).
- A calibration at P ≠ 0 or at the op_signature shapes. Whether an m = 1 check runs both T = 1 rows (OD-16 sub-question ⑤).
- Default tolerances, seeds, draws, positions, time limits or build flags of the harness (ADR-0164 Boundaries; HQ-0066 (2), HQ-0033).
- Registering `rope` with `correctness.check`, `spec.write` or the instance start.
- SDPA with KV cache verification, the bf16 timing run, and fp16.
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, ADR-0164 has all its code slices and its calibration. The next P2-11/P2-12 work in PLAN order is the harness record of SDPA with KV cache (ADR-0162 decision 13; ADR-0164 "Later work"), a document task that writes the record before any code.

## Result
**DONE.** PR #278 https://github.com/myungjoo/HIL-Claw/pull/278, squash commit `4ffe5ea0` on `main` (body ends with `Task: T-0464`); branch deleted (remote and local).

**Review**: 1 round, Approve, no finding (fresh-context `dev-reviewer`, https://github.com/myungjoo/HIL-Claw/pull/278#issuecomment-6393904653). The reviewer regenerated the 24 violating patterns bit for bit (exact rational RNE), compiled each file alone under the C gate's line with one exported symbol, checked the failing kernel differs only in the two output expressions, re-measured the tolerance margins over 1000 draws on two seeds, and ran the 36 calibration cases under WSL.

**CI**: 1 run, all six checks green, https://github.com/myungjoo/HIL-Claw/actions/runs/40165420767. C gate "harness pass": `calibration: 36 case(s) selected, 0 skipped` (6 fp32 + 30 bf16). Python gates and coverage gate: `33031 passed, 50 skipped`; lines 11047/11088 = 99.63%, functions 1073/1073 = 100.00%.

**Local**:
- WSL (clang 14, venv `/tmp/t0461venv` outside the repository): `test_calibration.py` + `test_bf16_calibration.py` 36 passed. Each `rope_bf16_*.c` compiles alone under `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`; `nm` shows only `hilclaw_rope_bf16`.
- Windows (Python 3.14.4, numpy 2.5.2): full `pytest` 31496 passed, 1585 skipped (the 30 bf16 calibration cases skip: no POSIX); `ruff check .` and `ruff format --check .` clean.
- The new files are ASCII with LF.

**Changes**: three kernels under `tests/harness/calibration/` and, in `test_bf16_calibration.py`, an import of `run_bf16_rope_verification`, a `ROPE` row with a margin comment, a `rope_executables` session fixture (same `FLAGS`, `BUILD_TIMEOUT`, skip-or-fail rules; no `-lm`, the rope program and kernels need none), a `rope_verdict` helper and a test over `STATES` x draws {1, 3}. No existing line changed.

**Test choices** (test values only):
- Shape (3, 2, 4): small, 24 elements, rows 0 to 2, so row 0 (c = 1, s = +0) is included.
- P = 0 for both runs (decision 11); the failing kernel is outside at row 0 on every seed.
- Tolerance rtol = 0, atol = 2**-7: twice the conforming bound 2**-8 + 2**-21 of decision 10 (no rtol with atol = 0, since outputs may cancel), far below the miss of >= 1 at row 0.
- Known seed 2026, as for the other rows.
- Only the verdict is asserted (ADR-0003 decision 4).

**Violating constants**: computed in a throwaway scratchpad interpreter from `draw_x((3, 2, 4), seed=2026, draw=0)`, `table_rows((3, 2, 4), start=0)` and `reference`; the float64 reference was rounded to bf16 directly with RNE in exact rational arithmetic. No near tie: the closest element is 0.189 of a bf16 unit from a midpoint, far beyond a binary32 step; rounding through binary32 gives the same 24 patterns.

**Evidence of the states** (WSL clang 14, rtol 0, atol 2**-7). Failing elements per draw, known seed 2026 (1 draw) / run-time seed 6852932820192447698 (3 draws):
- conforming 0 / 0,0,0 (PASS / PASS);
- failing 24 / 24,23,24 (FAIL / FAIL);
- violating 0 / 24,23,22 (PASS / FAIL).
- Over 1000 draws of seed 2350309344540026136: conforming largest |dev| / atol = 0.4996, i.e. 0.9991 of the bound 2**-8 + 2**-21, no element outside; failing 23463 of 24000 elements outside, every draw FAIL, smallest |dev| / atol among the failing elements 1.011.

**Decision 11 list**: no test requires a fault from it to fail; the only required faults are swapped cos and sin and the V1 table.

**Language**: C for the kernels (kernel language of `cpu_standin`, ADR-0003 decision 5); Python for the test. No layer-2 code changed.

**Follow-ups**: none new. The planner's follow-up stands (harness record of SDPA with KV cache, ADR-0162 decision 13). No HQ.
