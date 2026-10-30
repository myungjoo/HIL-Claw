---
id: T-0458
title: Add the three-state calibration of the bf16 verification run for rmsnorm and swiglu (six C kernels and two table rows, ADR-0163 decision 9, code slice 7)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0457]
touchesFiles: [tests/harness/calibration/, tests/harness/test_bf16_calibration.py]
estimatedSize: {loc: 0, files: 0}   # all test code: six C fixture kernels and two rows of an existing test file, excluded from the cap (D4), as in T-0063 and T-0457
hq: []
---
## Why

**State on `main` `905e4c0`.** ADR-0163 (T-0451, `c004ccc`) records the verification run of one built bf16 kernel on `cpu_standin` for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. Slices 1 to 5 (T-0452 to T-0456) added the arrays, the header, the four programs, the build and the judge and runner (`hilclaw/harness/bf16_verification.py`). Slice 6 (T-0457, PR #272, `20a21d9`) added the calibration of decision 9 for `gemm` and `elementwise_add`. It added six kernels under `tests/harness/calibration/` and `tests/harness/test_bf16_calibration.py`, with the tables `KINDS` and `STATES` and 12 cases. The CI "harness pass" step already runs that file and fails if any of its cases is skipped.

**This task is the seventh slice: the same calibration for `rmsnorm` and `swiglu`.** Decision 9 asks for "three hand-written C kernels per kind, twelve in all". ADR-0003 decision 6 (a) wants them in the change that makes the harness verify the kind. That change is complete, so these six are now due. T-0457 built the test file so that these two kinds need only new rows in `KINDS`, and it already passes `-lm` for every kind (T-0457 `## Result`, "Test choices"). After this task, every kind of ADR-0163 has its three kernels.

**Size.** The C kernels and the test rows are test code. D4 excludes them from the cap, as T-0063 and T-0457 counted theirs. No package code, workflow or document changes. `ci.yml` needs no edit, because the step already names the file.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items and P2-14 needs them, so the D18 rule does not apply. Unresolved HQs hold the round-loop items and P2-5 (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4). Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0457.

**D16.** The tests build with `clang` and run local processes through `run_bf16_verification`. Without a POSIX system or without `clang` they skip, and they fail on CI without `clang`. Nothing starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (test code excluded), the naming and the test rules. Branch `claude/T-0458-<slug>`; commit trailer `Task: T-0458`; code mode, so a Draft PR whose body ends with `Task: T-0458`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, code mode.
- `PROCESS/tasks/T-0457-bf16-calibration-gemm-add.md`: the Acceptance Criteria and the whole `## Result`. This task follows the same model; the "Test choices" and "Violating constants" there are the precedent.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 3 (lines 55-65): RMSNorm `eps` as the constant `0x3727C5AC`, which the program passes;
  - decision 4 (lines 67-88): the value sets, including the swiglu gate set of 1024 patterns;
  - decision 6 (lines 95-110), the `rmsnorm` and `swiglu` rows of the reference;
  - decision 7 (lines 112-121): the predicate and the notes "for whoever sets a tolerance", every kind plus `rmsnorm` and `swiglu`;
  - decision 9 (lines 129-143): the whole calibration rule, the failing-kernel table and the list of what no test may require to fail.
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`, decisions 2 to 7 (lines 29-88).
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`, decisions 3 to 5 (lines 44-68) and decision 9 (lines 116-122).
- `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`, decisions 4 to 6 (lines 50-79) and decision 10 (lines 125-134).
- `tests/harness/test_bf16_calibration.py`, the whole file (96 lines), and the six `*_bf16_*.c` files under `tests/harness/calibration/`, for the layout, header comments and round-to-nearest-even of the existing kernels.
- `hilclaw/harness/bf16_verification_rmsnorm.c` and `hilclaw/harness/bf16_verification_swiglu.c`: the header comments and the kernel prototypes (line 51 and line 44).
- `hilclaw/harness/bf16_verification_arrays.py`: `draw_inputs`, `reference` and `widen`. Use them to compute the violating kernels' constants in a throwaway interpreter.
- `tests/harness/test_bf16_verification_programs.py`, lines 101-124 (`PLAIN` for `rmsnorm` and `swiglu`), as a sketch of a plain kernel per kind. Note that the conforming `rmsnorm` kernel here must keep every intermediate in `float` without a bf16 rounding before the output (ADR-0158 decision 3); the sketch already does.

## Acceptance Criteria

1. **Six new C files under `tests/harness/calibration/`**, ASCII and LF, named after T-0457's: `rmsnorm_bf16_conforming.c`, `rmsnorm_bf16_failing.c`, `rmsnorm_bf16_violating.c`, `swiglu_bf16_conforming.c`, `swiglu_bf16_failing.c` and `swiglu_bf16_violating.c` (the fixture builds `KERNELS / f"{kind}_bf16_{state}.c"`). Each:
   - defines exactly the contract symbol with the program's prototype, `void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y)` or `void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out)`;
   - compiles alone under the C gate's line (`clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`);
   - has a short header comment in the form of T-0457's kernels: the state, what it computes, and that it is test data of `tests/harness/test_bf16_calibration.py`, not a reference, a baseline or a catalog entry.
2. **What each kernel does** (ADR-0163 decision 9, ADR-0003 decisions 2 and 3):
   - **Conforming**: the operation as the contract states it. The kernel widens each bf16 input to `float` (pattern shifted left by 16, through `memcpy`).
     - `rmsnorm` accumulates the squares of a row in `float`, uses the `eps` it is passed, applies `1.0f / sqrtf(...)` (or a division by `sqrtf`) and the weight in `float`, with no bf16 rounding before the output.
     - `swiglu` computes g / (1 + `expf`(−g)) · u in `float`.
     - The result is rounded to bf16 with round-to-nearest-even on the `float` bit pattern, as in T-0457's kernels.
   - **Failing**, from the decision 9 table: for `rmsnorm`, the weight left out (y = x / rms); for `swiglu`, σ(−g) in place of σ(g), that is g / (1 + `expf`(g)) · u. Everything else is as in the conforming kernel.
   - **Violating (V1)**: the kernel ignores its inputs (and `eps`) and writes a table of bf16 patterns. The table is the correctly rounded output of draw 0 of the test's known seed at the test's shape, repeated by index modulo its length, as T-0457's violating kernels do. Compute the constants with `bf16_verification_arrays` (the `rmsnorm` reference with the `eps` of ADR-0163 decision 6) and round-to-nearest-even from the float64 reference in a throwaway interpreter that changes no repository file. These references are not exact in binary32, unlike T-0457's: round the float64 value to bf16 directly (round-to-nearest-even on float64), and record in `## Result` that no element of the table was a near tie where a binary32 step would round differently, or how one was handled. Name the seed and shape in the header comment.
3. **Two new rows in `KINDS` of `tests/harness/test_bf16_calibration.py`**, `"rmsnorm"` and `"swiglu"`, each with dims `(m, n)`, a known seed and a tolerance. Change no other line of the file unless a row cannot be added otherwise; if so, give the reason in `## Result`. Give each choice one line of reason in the commit body, the PR body and `## Result`, and a one-line margin comment next to each row, as the existing rows have (ADR-0003 decision 7).
   - **Shape**: small, for example m = 3, n = 5, as for `elementwise_add`.
   - **Tolerance (`rtol`, `atol`)**: the test's own values, not the harness's. The conforming kernel must pass it on any seed. Decision 7 bounds the conforming output: a relative 2^−8 for a correctly rounded output, every exact `rmsnorm` output between 0.25 and 2, and `swiglu` within a relative 0.00437 with exact outputs in [0.00138, 7.935] (ADR-0160 decision 5). The failing and violating kernels must get the verdict FAIL on a run-time seed.
   - **Do not require every failing element to lie outside.** For `rmsnorm` the weight left out moves an element by a relative |1/w − 1|, which is at least 2^−6 for only 253 of the 256 weights (decision 9). An element whose weight is near 1 can pass. The test asserts the verdict only, as ADR-0003 decision 4 asks and as T-0457 did. Check that the known seed's draw 0 still gives FAIL for the failing kernel, and record the per-element counts.
   - The verdict table `STATES`, the run-time seed rule and the parametrization stay as they are. The result is 2 × 3 × 2 more cases, 24 in all for the file.
4. **No other change.** Leave `hilclaw/`, `.github/workflows/ci.yml`, `tests/harness/test_calibration.py`, the existing fixtures, the other tests, `pyproject.toml` and every document unchanged. Add no dependency. The local `pytest` and `ruff` runs are green. Coverage of `hilclaw/` stays at or above 80% for lines and functions; it cannot drop, since no package code changes.
5. **Evidence of the states.** On a machine with `clang` (CI counts; WSL if the executor has it), record in `## Result`:
   - per kind and state, the failing-element counts on the known draw and on one run-time seed;
   - the largest deviation of the conforming kernel relative to the tolerance bound, over at least 1000 random draws, and the smallest of the failing kernel over the elements that fail.
   The CI log of the "harness pass" step must show `calibration: 30 case(s) selected, 0 skipped` (6 fp32 + 24 bf16) or the equivalent count.
6. **Process**: code mode (CLAUDE.md A-13).
   - Open a Draft PR titled with `T-0458`, whose body ends with `Task: T-0458`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - that the conforming kernels follow the contracts (fp32 accumulation of the squares, `eps` as passed, no bf16 rounding before the output, round-to-nearest-even);
     - that the violating constants are draw 0 of the known seed (regenerate them);
     - that each tolerance passes the conforming kernel with a margin and gives FAIL for the failing and violating kernels;
     - that no test requires a fault of decision 9's "no test may require these to fail" list to fail (for example an ignored `eps`, a single square left out, Meta's intermediate rounding, or truncation in `swiglu`).

## Out of Scope

- Any change to `hilclaw/` (programs, header, arrays, build, judge), to `ci.yml`, to `test_calibration.py` or to the existing fixtures.
- Kernels for the faults that decision 9 says no test may require to fail, and corner-case or non-finite inputs (#5 B-7). Gates beyond ±8 for `swiglu` (ADR-0163 Limit 2).
- RoPE and SDPA, the bf16 timing run, and fp16.
- Default tolerances, seeds, draws, time limits or build flags of the harness (ADR-0163 Boundaries; HQ-0033, HQ-0034).
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, ADR-0163 has all its code slices and calibration. The next P2-11/P2-12 work is the verification of the remaining kinds (`rope`, `sdpa_kv_cache`, ADR-0161 and ADR-0162), which needs its own record first, or the model program of P2-13 (ADR-0153). The planner chooses from PLAN order.

## Result
**DONE.** PR #273 https://github.com/myungjoo/HIL-Claw/pull/273, squash commit `bd72a0f` on `main`; branch deleted (remote and local).

**Review**: 1 round, Approve (fresh-context `dev-reviewer`, https://github.com/myungjoo/HIL-Claw/pull/273#issuecomment-6391493312). The reviewer regenerated all 30 violating patterns bit for bit, compiled each file alone under the C gate's line, checked with `nm` that each defines only the contract symbol, and ran the 24 cases under WSL. Over 2000 draws of a fresh seed, the conforming kernels also passed at half the test tolerance. No finding.

**CI**: 1 run, 0 failures, https://github.com/myungjoo/HIL-Claw/actions/runs/40147261889. All six checks green. C gate "harness pass": `calibration: 30 case(s) selected, 0 skipped` (6 fp32 + 24 bf16). Coverage gate: `32349 passed, 50 skipped`; lines 10852/10889 = 99.66%, functions 1055/1055 = 100.00%.

**Local**:
- Windows, venv of T-0060 (numpy 2.4.6): `pytest` 30983 passed, 1416 skipped (the 24 bf16 calibration cases skip: no POSIX). `ruff check .` and `ruff format --check .` are clean.
- WSL (clang 14, venv `/tmp/t0458venv` outside the repository, numpy 2.4.6, pytest 9.1.1): `test_bf16_calibration.py` and `test_calibration.py` 30 passed. Each of the 12 `*_bf16_*.c` compiles alone under the C gate's line.
- The new files are ASCII with `i/lf`.

**Evidence of the states** (WSL clang 14, rtol 2**-7, atol 1e-3). Failing elements per draw, known seed 2026 (1 draw) / run-time seed 2878734870937994324 (3 draws):
- rmsnorm (3, 5): conforming 0 / 0,0,0; failing 15 / 15,15,15; violating 0 / 15,15,15.
- swiglu (3, 5): conforming 0 / 0,0,0; failing 15 / 15,15,15; violating 0 / 15,15,15.
- Largest conforming |dev| / (atol + rtol |ref|) over 1000 random draws: rmsnorm 0.438, swiglu 0.475.
- Failing kernels over 1000 random draws:
  - rmsnorm: 14921 of 15000 elements outside, at least 12 per draw, no draw with all inside, smallest ratio among the failing 1.0095;
  - swiglu: 15000 of 15000 outside, smallest ratio 28.3.
- The known draw 0 gives FAIL for the failing rmsnorm kernel with 15 of 15 outside.

**Violating constants**: computed in a throwaway interpreter in the scratchpad from `draw_inputs(kind, (3, 5), seed=2026, draw=0)` and `reference` (rmsnorm with the binary32 `eps` of `EPS_BITS`). The float64 reference was rounded to bf16 directly, with RNE in exact rational arithmetic. No element is a near tie: the closest is 0.102 (rmsnorm) and 0.099 (swiglu) of a bf16 unit from the midpoint, far beyond a binary32 step (2^-16 of a bf16 unit). Rounding through binary32 gives the same 30 patterns, which confirms this.

**Test choices** (provisional, test values only; the two rows only, no other line of the file changed):
- Shape (3, 5) for both kinds: small, 15 elements like the other tables.
- Known seed 2026 per kind, as for the existing rows.
- rmsnorm rtol 2**-7, atol 1e-3: |ref| lies in [0.25, 2] (ADR-0158 decision 9), so twice the 2**-8 of a correctly rounded output covers the fp32 steps.
- swiglu rtol 2**-7, atol 1e-3: a conforming output is within 0.00437 |ref| (ADR-0160 decision 5); atol covers |ref| >= 0.00138; sigma(-g) misses by >= 0.39 |ref|.
- The verdict only is asserted. A left-out weight near 1 can leave an element inside (decision 9); 79 of 15000 were inside.
- The fixture already passed `-lm` for every kind (T-0457), so no other edit was needed.

**Decision 9 list**: no test requires a fault from it to fail. The only required faults are the two from the table. The conforming rmsnorm kernel uses the passed `eps` and keeps every intermediate in `float`; nothing tests an ignored `eps`, a single square left out, Meta's intermediate rounding or truncation.

**Language**: C for the kernels, the kernel language of `cpu_standin` (#5 A-7 (2), ADR-0003 decision 5); Python for the test rows. No layer-2 code changed.

**Follow-ups**: none new. The planner's follow-up stands (`rope`/`sdpa_kv_cache` verification after their record, or P2-13). No HQ.
