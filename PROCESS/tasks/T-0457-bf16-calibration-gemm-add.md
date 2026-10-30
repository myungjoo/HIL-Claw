---
id: T-0457
title: Add the three-state calibration of the bf16 verification run for gemm and elementwise_add (six C kernels and their tests, ADR-0163 decision 9, code slice 6)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, OD-31, OD-16, "PLAN P2-11", "PLAN P2-12", "PLAN P2-14"]
dependsOn: [T-0456]
touchesFiles: [tests/harness/calibration/, tests/harness/test_bf16_calibration.py, .github/workflows/ci.yml]
estimatedSize: {loc: 2, files: 1}   # non-test: one line in ci.yml. Six C fixture kernels and one test file are test code, excluded from the cap (D4), as in T-0063
hq: []
---
## Why

**State on `main` `73bf5ac`.** ADR-0163 (T-0451, `c004ccc`) records the verification run of one built bf16 kernel on `cpu_standin` for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu`. Five code slices have landed. T-0452 to T-0455 added the arrays, the header, the four programs and the build. T-0456 (`4162276`) added `hilclaw/harness/bf16_verification.py` (`judge_report`, `run_bf16_verification`). The package can now build and verify a bf16 kernel of the four kinds end to end.

**This task is the sixth slice: the calibration of ADR-0163 decision 9 for two of the four kinds.** Decision 9 says that ADR-0003 holds per kind, with "three hand-written C kernels per kind, twelve in all", and that "the bf16 `gemm` gets its own three". ADR-0003 decision 6 (a) wants them in the change that makes the harness verify the kind. That change is now complete, so the kernels are due. No bf16 calibration kernel exists yet. Only the fp32 `gemm` three of T-0063 are under `tests/harness/calibration/`.

**Split.** Twelve kernels plus the tests are too many for one review. This task covers `gemm` and `elementwise_add`. Their kernels need no math library. The next task covers `rmsnorm` and `swiglu` (`sqrtf`, `expf`). It reuses the test file made here.

**Size.** The C kernels and the test file are test code. D4 excludes them from the cap, as T-0063 counted its three kernels. The one non-test change is adding the new test file to the CI "harness pass" step, so that CI runs these cases and fails if they are skipped. The fp32 calibration gets that from `test_calibration.py`.

**PLAN order and D18.** This is the "하네스 검증" of PLAN P2-11 and the bf16 harness of P2-12. Both are checklist items and P2-14 needs them, so the D18 rule does not apply. Unresolved HQs hold the round-loop items and P2-5 (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4). Work therefore continues on P2-11 to P2-14, as for T-0451 to T-0456.

**D16.** The tests build with `clang` and run local processes through `run_bf16_verification`. Without a POSIX system or without `clang` they skip, and they fail on CI without `clang`. Nothing starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (test code excluded), the naming and the test rules. Branch `claude/T-0457-<slug>`; commit trailer `Task: T-0457`; code mode, so a Draft PR whose body ends with `Task: T-0457`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, code mode.
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md`:
  - decision 4 (lines 67-88): the value sets and the generator;
  - decision 6 (lines 95-110), the `gemm` and `elementwise_add` rows of the reference;
  - decision 7 (lines 112-121): the predicate and the notes "for whoever sets a tolerance", every kind plus `gemm` and `elementwise_add`;
  - decision 9 (lines 129-143): the whole calibration rule, the failing-kernel table and the list of what no test may require to fail;
  - decision 10 (lines 145-155).
- `ARCHITECTURE/decisions/ADR-0003-od16-harness-calibration.md`, decisions 2 to 7 (lines 29-88): the three states, V1, "caught", the nature and place of the kernels, and independence from the tolerance.
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`, decision 8 (lines 80-85): the functional test as a run with a seed written in the test, and the contract half as the same run with a seed taken at run time.
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`, decisions 3 to 5 (lines 43-73), for the operation, fp32 accumulation, round-to-nearest-even and the prototype, and decision 9 (lines 121-128).
- `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`, decisions 4 to 6 (lines 49-77) and decision 10 (lines 123-131).
- `tests/harness/test_calibration.py`, the whole file (84 lines), and the three files under `tests/harness/calibration/`. They are the model: the session build fixture with skip and fail-on-CI, `STATES`, the known seed, `seed_taken_at_run_time`, and the one test per state and `draws`. `PROCESS/tasks/T-0063-gemm-three-state-calibration.md` `## Result` explains the choices.
- `hilclaw/harness/bf16_verification.py`: the docstring and `run_bf16_verification`.
- `hilclaw/harness/bf16_verification_build.py`: `build_bf16_verification_executable` (lines 59-110).
- `hilclaw/harness/bf16_verification_arrays.py`: `draw_inputs`, `reference` and `widen`. Use them to compute the violating kernels' constants in a throwaway interpreter.
- `hilclaw/harness/bf16_verification_gemm.c` and `hilclaw/harness/bf16_verification_elementwise_add.c`: the header comments and the kernel prototypes (line 44 of each).
- `tests/harness/test_bf16_verification_programs.py`, lines 52-123 (`KERNEL`, `HELPERS`, `PLAIN`), for a plain bf16 kernel per kind with round-to-nearest-even from `float`.
- `.github/workflows/ci.yml`, lines 85-115: the C gate's compile line for every tracked `*.c`, and the "harness pass" step.

## Acceptance Criteria

1. **Six new C files under `tests/harness/calibration/`**, ASCII and LF: `gemm_bf16_conforming.c`, `gemm_bf16_failing.c`, `gemm_bf16_violating.c`, `elementwise_add_bf16_conforming.c`, `elementwise_add_bf16_failing.c` and `elementwise_add_bf16_violating.c`. The names are a suggestion; any names work that keep them apart from the fp32 `gemm_*.c`. Each:
   - defines exactly the contract symbol with the prototype of the program, `hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)` or `hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)`;
   - compiles alone under the C gate's line (`clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`);
   - has a short header comment like the fp32 fixtures': the state, what it computes, and "test data of `tests/harness/test_bf16_calibration.py`, not a reference, a baseline or a catalog entry".
2. **What each kernel does** (ADR-0163 decision 9, ADR-0003 decisions 2 and 3):
   - **Conforming**: the operation as the contract states it. The kernel widens each bf16 input to `float` (pattern shifted left by 16, through `memcpy`). `gemm` accumulates each sum in `float`; `elementwise_add` adds in `float`. The result is rounded to bf16 with round-to-nearest-even on the `float` bit pattern.
   - **Failing**, from the decision 9 table: for `gemm`, one term of each sum is left out (for example `p = 0`); for `elementwise_add`, the kernel computes a − b in place of a + b. Everything else is as in the conforming kernel.
   - **Violating (V1)**: the kernel ignores its inputs and writes a table of bf16 patterns. The table is the correctly rounded output of draw 0 of the test's known seed at the test's shape, repeated by index modulo its length, as `gemm_violating.c` does. Compute the constants with `bf16_verification_arrays` and round-to-nearest-even in a throwaway interpreter that changes no repository file. Name the seed and shape in the header comment.
3. **New test file `tests/harness/test_bf16_calibration.py`**, on the model of `test_calibration.py`, with these test choices. Give each choice one line of reason in the commit body, the PR body and `## Result`.
   - **The build**: one session-scoped fixture builds the six executables with `build_bf16_verification_executable(kind, source, output, timeout_s=..., flags=(-std=c99 -Wall -Wextra -Wpedantic -Werror -O2))`. It skips without a POSIX system or `clang` and fails on CI (`GITHUB_ACTIONS == "true"`) without `clang`, exactly as `test_calibration.py` does.
   - **A shape per kind and one known seed per kind.** For `gemm`, k must be small enough that every exact output stays far from the 0.25 that a left-out term moves it by, after bf16 rounding and the tolerance (decision 9, `gemm` row). For example, m = 3, k = 4, n = 5 bounds |c| by 4.
   - **A tolerance per kind (`rtol`, `atol`)**: the test's own values, not the harness's.
     - The conforming kernel must pass it on any seed. A correctly rounded output can be off by a relative 2^−8, and for `gemm` an element can lie near zero (decision 7).
     - Every element of the failing kernel must lie outside it, and so must the violating kernel's elements on a random seed.
     - Write the margin as a one-line comment next to the values. ADR-0003 decision 7 asks for it.
   - **The states and their verdicts**, per kind, as `STATES` in `test_calibration.py`. Conforming: pass on the known seed and on a seed taken at run time. Failing: fail and fail. Violating: pass on the known seed's single draw, fail on a run-time seed.
     - The functional half uses one draw. The contract half uses `draws` 1 and 3.
     - The run-time seed comes from `secrets.randbits(64)` and is never the known seed.
     - A broken result is an assertion failure that shows the seed, the broken condition, the return code and stderr.
   - **Parametrize** over kind × state × `draws`: 2 × 3 × 2 = 12 cases. The structure must take the next task's two kinds by adding table rows only. Pass `trailing_flags=("-lm",)` for every kind or for none, and record which one.
4. **`.github/workflows/ci.yml`**: add `tests/harness/test_bf16_calibration.py` to the `python -m pytest` line of the "harness pass" step, so that its cases are counted and a skip fails the step. Change nothing else in the workflow.
5. **No other change.** Leave `hilclaw/`, `tests/harness/test_calibration.py`, the fp32 fixtures, the other tests, `pyproject.toml` and every document unchanged. Add no dependency. The local `pytest` and `ruff` runs are green. Coverage of `hilclaw/` stays at or above 80% for lines and functions; it cannot drop, since no package code changes.
6. **Evidence of the states.** On a machine with `clang` (CI counts; WSL if the executor has it), record in `## Result`:
   - per kind and state, the failing-element counts on the known draw and on one run-time seed;
   - the largest deviation of the conforming kernel relative to the tolerance bound.
   The CI log must show the new cases selected in the "harness pass" step, none skipped.
7. **Process**: code mode (CLAUDE.md A-13).
   - Open a Draft PR titled with `T-0457`, whose body ends with `Task: T-0457`.
   - Run the reviewer cycle (dev-code-review), at most 7 rounds, until CI is green.
   - Then squash-merge with `gh pr merge --squash --body` using the PR body, and delete the branch.
   - The reviewer checks at least:
     - that the conforming kernels follow the contracts (fp32 accumulation, round-to-nearest-even);
     - that the violating constants are draw 0 of the known seed (regenerate them);
     - that each tolerance passes the conforming kernel with a margin and keeps the failing and violating elements outside;
     - that no test requires a fault of decision 9's "no test may require these to fail" list to fail (for example a truncating rounding);
     - that the CI step selects the new file.

## Out of Scope

- The `rmsnorm` and `swiglu` calibration kernels and their rows. That is the next task.
- Any change to `hilclaw/` (programs, header, arrays, build, judge), to `test_calibration.py` or to the fp32 fixtures.
- Kernels for the faults that decision 9 says no test may require to fail, and corner-case or non-finite inputs (#5 B-7).
- RoPE and SDPA, the bf16 timing run, and fp16.
- Default tolerances, seeds, draws, time limits or build flags of the harness (ADR-0163 Boundaries; HQ-0033, HQ-0034).
- Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start.
- Any edit to `ARCHITECTURE/` or `PROCESS/`, except this task file's `## Result`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next task: the `rmsnorm` and `swiglu` calibration kernels (six) as new rows of `tests/harness/test_bf16_calibration.py`. The failing kernels are the weight left out (y = x / rms) and σ(−g) in place of σ(g), per the decision 9 table. They link `-lm`.

## Result
**DONE.** PR #272 https://github.com/myungjoo/HIL-Claw/pull/272, squash commit `20a21d9` on `main`; branch deleted (remote and local).

**Review**: 1 round, Approve (fresh-context `dev-reviewer`, https://github.com/myungjoo/HIL-Claw/pull/272#issuecomment-6391139251). The reviewer regenerated both violating tables bit for bit, built the branch with WSL clang 14 and ran all 12 cases. It also measured the conforming and failing deviations over 3000 random seeds. No blocking finding. Two notes, neither needing a change: (1) AC 3's "the violating kernel's elements on a random seed lie outside" cannot hold for every element by construction (at most 2 of 15 inside over 3000 seeds); the test asserts the FAIL verdict only, as ADR-0003 decision 4 asks; (2) `## Result` was empty on the branch, by design (filled here after the merge).

**CI**: 1 run, 0 failures, https://github.com/myungjoo/HIL-Claw/actions/runs/40144679649. Six checks green on head `1cc3a54`. C gate "harness pass": `calibration: 18 case(s) selected, 0 skipped` (6 fp32 + 12 bf16). Both Python gates: `tests/harness/test_bf16_calibration.py ............` and `32337 passed, 50 skipped`. Coverage gate: lines 10852/10889 = 99.66%, functions 1055/1055 = 100.00%.

**Local** (Windows, venv of T-0060 unchanged): `pytest` 30983 passed, 1404 skipped (the 12 new cases skip: no POSIX). `ruff check .` and `ruff format --check .` are clean. The new files are ASCII with `i/lf`. Each kernel compiles alone under the C gate's line with WSL clang 14.

**Evidence of the states** (WSL clang 14, numpy 2.2.6, rtol 2**-7, atol 1e-3). Failing elements per draw, known seed 2026 (1 draw) / run-time seed 13853735323370704068 (3 draws):
- gemm (3, 4, 5): conforming 0 / 0,0,0; failing 15 / 15,15,15; violating 0 / 15,15,15.
- elementwise_add (3, 5): conforming 0 / 0,0,0; failing 15 / 15,15,15; violating 0 / 15,15,15.
- Largest conforming |dev| / (atol + rtol |ref|) over 1000 random draws: gemm 0.458, elementwise_add 0.439. The reviewer measured 0.462 and 0.442 over 3000 seeds. The failing minimum ratios were 12.6 (gemm) and 79 (add).

**Files** (7 new, 1 changed; all test code except one line of `ci.yml`):
- `tests/harness/calibration/{gemm,elementwise_add}_bf16_conforming.c`: widen through `memcpy`, accumulate or add in `float`, then RNE on the float bit pattern.
- `..._failing.c`: gemm leaves out the term p = 0; add computes a - b.
- `..._violating.c`: a 15-entry table of bf16 patterns, indexed by e mod 15.
- `tests/harness/test_bf16_calibration.py`: tables `KINDS` (dims, known seed, tolerance) and `STATES`, with 12 cases.
- `.github/workflows/ci.yml`: the new file added to the "harness pass" pytest line.

**Violating constants**, produced in a throwaway interpreter:
```python
a, b = va.draw_inputs(kind, dims, seed=2026, draw=0); ref = va.reference(kind, a, b)
f = np.asarray(ref, np.float32); assert (f.astype(np.float64) == ref).all()   # exact
bits = f.view(np.uint32).astype(np.uint64); out = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
```

**Test choices** (provisional, test values only):
- Real `.c` files: the C gate compiles them, as for the fp32 fixtures.
- Session fixture with the C gate's flags: skip without POSIX or clang, fail on CI without clang, as `test_calibration.py`.
- gemm at (3, 4, 5): |c| < 4, so a left-out term (>= 0.25) misses by > 0.23 against a bound < 0.033.
- elementwise_add at (3, 5): small, with 15 elements like the gemm table.
- Known seed 2026 per kind, one draw for the functional test: the violating kernel holds one draw.
- Run-time seed from `secrets.randbits(64)`, never the known seed, shown in the message; draws 1 and 3.
- rtol 2**-7, atol 1e-3 for both kinds: twice the 2**-8 relative error of a correctly rounded output, plus atol for gemm elements near zero. a - b misses by >= 1 - 2**-8 against a bound < 0.017.
- `trailing_flags=("-lm",)` for every kind: harmless here, and the next task's kinds need it, so that task adds rows only.

**Decision 9 list**: no test requires a fault from it to fail. The only required faults are the two from the table.

**Language**: C for the kernels, the kernel language of `cpu_standin` (#5 A-7 (2), ADR-0003 decision 5); Python for the tests. No layer-2 code changed.

**Follow-ups**: none new. The planner's `rmsnorm`/`swiglu` follow-up stands. No HQ.
