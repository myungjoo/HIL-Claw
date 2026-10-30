---
id: T-0437
title: Add the RMSNorm call sites to hilclaw/model_binding.py - their shapes over a generation, a binding check with fit against the bf16 RMSNorm contract and "every shape" accepted (ADR-0158 decision 7), the dtype range of ADR-0157 decision 4, and the model eps as its nearest binary32 value - with tests (ADR-0158 code slice, second part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0436]
touchesFiles: [hilclaw/model_binding.py, tests/test_model_binding.py, tests/test_rmsnorm_bf16_contract.py]
estimatedSize: {loc: 190, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `f4fd3e0`):
- ADR-0158 (T-0435) defines the bf16 RMSNorm contract on `cpu_standin`. T-0436 (PR #256, `7acfcaa`) landed part 1 of its code slice: the kind `rmsnorm` (members `m`, `n`) in `hilclaw.keys`, and `hilclaw/rmsnorm_bf16_contract.py` (constants, `PROTOTYPE`, `SHAPES`, `INPUT_PATTERNS`, `EPS`, `op_signature_record`, `task_contract`, `covers`).
- ADR-0158 Consequences list the next part: "fit and the 'every shape' binding in `hilclaw/model_binding.py`, the executor passing its `eps` model parameter as the nearest binary32 value". T-0436's planner follow-up names it as the next step.
- Today `hilclaw/model_binding.py` knows the six GEMM call sites only (its docstring: "it knows no call site of RMSNorm, RoPE, SDPA, SwiGLU or elementwise add"). `hilclaw/model_gemm.py` calls `model_binding.check` for its GEMM-only model run.

**What the accepted records already settle** (so this task invents nothing):
- A call site is a row of ADR-0152 decision 2 that is an instance target, with its kind (ADR-0153 decision 3). The RMSNorm rows are 2, 10 and 15, named in that table after Meta's modules: `attention_norm`, `ffn_norm`, `norm`. Each is T × hidden with a weight of hidden (ADR-0152 decisions 2 and 5; ADR-0158 decisions 2 and 10: `m` = T, `n` = the feature width).
- Fit: compare the bound kernel's `task.contract` with the contract of the call site's kind and dtype on `language`, `prototype` and each operand's `name`, `role`, `dtype` (ADR-0153 decision 3, ADR-0157 decision 3's "compared on").
- A binding "for every shape", and a listed shape other than the spec's own, are accepted for this contract (ADR-0158 decision 7, "Every set of dimensions"; ADR-0153 decision 3).
- The dtype: a dtype at which the kind of a call site has no contract is invalid input, and the outcome names the dtype and the kind (ADR-0157 decision 4). Only `bf16` has an RMSNorm contract (ADR-0158 decision 1: "No fp32 or fp16 RMSNorm contract is defined").
- `eps` is a model parameter the executor never assumes (ADR-0153 decision 3 (a)); the caller passes the binary32 value nearest to the model's `eps`, which must be finite and greater than 0 (ADR-0158 decisions 5 and 7).
- The GEMM-only check stays as it is: ADR-0157 decision 5 keeps the fp32 column of the GEMM call sites "which ADR-0153 slice 1 and its tests use", and says a full fp32 generation becomes invalid input only once the other kinds are call sites of the full pass (ADR-0153 code slice 2).

**So this task adds an RMSNorm binding check beside `check`, not inside it.** Joining the checks of every kind into one generation check belongs to the full pass (ADR-0153 code slice 2), which needs the four remaining contract records. Changing `check` now would make every GEMM-only run (fp32 included) need RMSNorm kernels it never calls. If the executor or reviewer reads ADR-0153 or ADR-0157 as requiring something else, stop and return BLOCKED (`requirement-unclear`) and name the sentence.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json`: HQ-0021 (round 0's board step), HQ-0048 and HQ-0031 (rounds >= 1, P2-6, P2-7). The gate half of P2-4 is owner-only (OD-3). P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is code that P2-13 and P2-14 need: the forward pass cannot bind an RMSNorm kernel without it. It is not a follow-up, wording or hardening item, so D18 does not set it aside.

**§9, A-13 and D16.** No open decision is needed; every rule comes from ADR-0152, ADR-0153, ADR-0157 and ADR-0158 as accepted. Nothing in the data plane changes (`model_binding` reads and writes no file). Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0437-<slug>`, PR title with `T-0437`, commit trailer `Task: T-0437`, last line of the PR body `Task: T-0437`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md` decision 2 (the table, lines 41-66).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` decision 3 (lines 40-46) and decision 5 (lines 58-62).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md` decisions 1 to 5 (lines 30-78).
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`: decision 1 (lines 32-35), decision 2 (lines 37-42), decision 5 (lines 57-67), decision 6 (lines 69-91), decision 7 (lines 93-109), Consequences (lines 159-162).
- `hilclaw/model_binding.py`, the whole file (494 lines). This is the file you change.
- `hilclaw/rmsnorm_bf16_contract.py`, the whole file. Read only; do not edit.
- `hilclaw/model_gemm.py` lines 1-60 and its call of `model_binding.check` (around line 115): the existing caller, which must not change behaviour.
- `tests/test_model_binding.py`, the whole file (839 lines): its helpers (`every_binding`, `good_contract`, `run`, `CONTRACTS`), the outcome and message tests, and the uses of `"rmsnorm"` as an unknown GEMM call site and binding key (lines 154 and 624).
- `tests/test_rmsnorm_bf16_contract.py` lines 485-500 (`test_module_imports_keys_only_and_is_bound_by_no_other_module`) and, as the model for its new form, `tests/test_gemm_bf16_contract.py` lines 467-480 (`..._is_bound_by_the_model_binding_only`).

## Acceptance Criteria

1. **New public names in `hilclaw/model_binding.py`** (Python; no new import other than `hilclaw.rmsnorm_bf16_contract` and the standard library):
   - `RMSNORM_CALL_SITES = ("attention_norm", "ffn_norm", "norm")`, ADR-0152 decision 2 rows 2, 10 and 15, in that order.
   - `RMSNORM_DTYPES = (rmsnorm_bf16_contract.DTYPE,)`: the dtypes at which the `rmsnorm` contract is known (ADR-0157 decision 4).
   - `rmsnorm_shape(dimensions, call_site, rows)`: returns `(rows, dimensions.hidden)`, the `(m, n)` of ADR-0158 decision 2. It raises as `gemm_shape` does: first as `check_dimensions`, then `ValueError` with `parameter` `"call_site"` for a call site not in `RMSNORM_CALL_SITES`, then `TypeError`/`ValueError` with `parameter` `"rows"` for `rows` that is not an `int` from 1 to 2**53 - 1.
   - `rmsnorm_generation_calls(dimensions, *, prompt_length, generation_length)`: per call site in `RMSNORM_CALL_SITES` order, the sorted tuple of distinct shapes of a generation. It uses the same reading of passes as `generation_calls` (one prefill of `prompt_length` rows, then `generation_length - 1` decode passes of one row). It raises like `generation_calls` for its arguments.
   - `check_rmsnorm(dimensions, binding, *, dtype, prompt_length, generation_length)`: returns a `BindingCheck` (the existing named tuple). Details in criterion 2.
   - `rmsnorm_eps(eps)`: returns the binary32 value nearest to `eps` as a Python `float` that is exactly that binary32 value (round to nearest, ties to even, as `struct.pack("<f", ...)` does). Details in criterion 3.
2. **`check_rmsnorm`**, modelled on `check`:
   - **Arguments refused first**, in the order `dimensions`, `dtype`, `prompt_length`, `generation_length`, `binding`, each error carrying `parameter` = the argument's name:
     - `dimensions` as `check_dimensions`;
     - `dtype` exactly a `str` matching `[a-z][a-z0-9_]{0,31}`, as in `check`;
     - `prompt_length` and `generation_length` exactly `int` (`bool` refused) - `TypeError`;
     - `binding` a mapping whose keys are in `RMSNORM_CALL_SITES` (a GEMM call site key is refused), each value a non-empty sequence of `BindingEntry`, with the same kernel reference checks and the same overlap rule as `check` (`"every"` overlaps every other entry of its call site; two entries covering a common shape are malformed). `shapes` is `"every"` or a non-empty tuple of `(m, n)` pairs of `int` from 1 to 2**53 - 1. A triple is refused here, and a pair is still refused by `check`.
   - **Outcomes**, in this order:
     1. `"invalid_input"` (`call_site` and `shape` `None`): a `dtype` not in `RMSNORM_DTYPES`, with a reason that names the dtype and the kind, for example `dtype: no rmsnorm contract is known at the dtype 'fp32'` (ADR-0157 decision 4); then `prompt_length` outside 1 to 2**53 - 1; then `generation_length` outside 1 to 2**53 - 1.
     2. Per call site in `RMSNORM_CALL_SITES` order: `"kernel_unfit"` for each entry whose `contract` is not the bf16 RMSNorm contract, compared on `language`, `prototype` and the operands' `(name, role, dtype)`, with reference values from `rmsnorm_bf16_contract.task_contract`, never from the entry's own contract (operand shapes and extra members ignored, as for GEMM); then `"no_kernel"` for each shape of `rmsnorm_generation_calls` that no entry covers.
     - As in `check`: no `"no_kernel"` outcome is looked for when there is an `"invalid_input"`, and no per-call-site outcome at all when `dtype` is not in `RMSNORM_DTYPES`.
   - A listed shape other than the kernel's own spec shape and an `"every"` entry are accepted (ADR-0158 decision 7).
   - `calls` holds `(call_site, shape, kernel)` for every call of `rmsnorm_generation_calls`, in its order, only when `ok`.
   - Arguments are not modified. Nothing is built, started or read.
3. **`rmsnorm_eps`**:
   - `eps` must be exactly a `float` (`bool`, `int` and other types refused): `TypeError`.
   - `ValueError` for a value that is not finite or not greater than 0 (ADR-0158 decision 7), and for one whose nearest binary32 value is 0 or not finite.
   - Both errors carry `parameter` `"eps"`.
   - `rmsnorm_eps(1e-05) == rmsnorm_bf16_contract.EPS`, bit pattern `0x3727C5AC`.
   - This task passes `eps` to nothing: the model program and `hilclaw/model_gemm.py` do not change.
4. **The GEMM side does not change behaviour.**
   - `check`, `gemm_shape`, `generation_calls`, `CALL_SITES`, `DTYPES` and every existing message stay as they are. `hilclaw/model_gemm.py` is not edited.
   - You may share private helpers between the two checks (for example the fit comparison against a given reference, or the entry validation with a shape arity), as long as every existing test in `tests/test_model_binding.py` passes unchanged. The monkeypatch of `CONTRACTS[dtype].task_contract` in `test_fit_reference_comes_from_the_selected_contract` must keep its effect.
5. **Docstrings.**
   - Rewrite the module docstring: the module now also checks the three RMSNorm call sites against the bf16 RMSNorm contract (ADR-0158). It knows no call site of RoPE, SDPA, SwiGLU or elementwise add. It does not join the GEMM and RMSNorm checks into one generation check (the full pass, ADR-0153 code slice 2). It keeps the other "does not do" points.
   - Update the docstrings of `BindingEntry` (shapes are `(m, k, n)` for a GEMM call site and `(m, n)` for an RMSNorm call site) and of `ModelDimensions` if it names the GEMM shapes only.
   - Each new public function has a Doxygen-like docstring in the module's style. Other comments follow CLAUDE.md "코멘트 최소화".
6. **Tests in `tests/test_model_binding.py`** (D12: happy, error, branch and negative cases, every new public name). At least:
   - `RMSNORM_CALL_SITES` and `RMSNORM_DTYPES` values.
   - `rmsnorm_shape`: small values; at the Llama 3.2 1B hidden width 2048 with T in {1, 32, 512}, the `(m, n)` of `rmsnorm_bf16_contract.SHAPES`; unknown call site (including a GEMM call site name), bad rows, bad dimensions.
   - `rmsnorm_generation_calls`: prefill and decode, generation length 1, prompt of one row; refused arguments.
   - `check_rmsnorm`:
     - ok with an `"every"` binding, with listed shapes covering exactly, and with several disjoint entries; `calls` order;
     - a listed shape other than the kernel's spec shape is accepted;
     - each `"invalid_input"` case and their order; `fp32` and `fp16` named in the reason; no unfit and no `"no_kernel"` for an unknown dtype;
     - `"kernel_unfit"` for a kernel written to the bf16 `gemm` contract, to the fp32 `gemm` contract, for a wrong prototype, language, operand name, role or dtype, a non-mapping contract, a missing member, wrong operand forms;
     - the reference comes from `rmsnorm_bf16_contract.task_contract` (monkeypatched, as the GEMM test does);
     - `"no_kernel"` for a missing call site and an unlisted shape;
     - argument refusals with their `parameter` and order, including a GEMM call-site key, a triple shape, an overlap, and an `"every"` beside another entry;
     - arguments not modified.
   - `check` still refuses an RMSNorm call-site key and an `(m, n)` pair shape.
   - `rmsnorm_eps`: 1e-05 gives `rmsnorm_bf16_contract.EPS`; a value already binary32 comes back unchanged; a tie rounds to even (build one with `struct`); refused types (`bool`, `int`, `str`, `None`); refused values (0.0, -0.0, a negative, `inf`, `nan`, a value below half the smallest subnormal binary32, a value above the largest finite binary32 that rounds to infinity).
7. **Tests in `tests/test_rmsnorm_bf16_contract.py`**: change only the binder test (line 488) so that `hilclaw/model_binding.py` is the one module allowed to name `rmsnorm_bf16_contract`, in the form of `tests/test_gemm_bf16_contract.py`'s `..._is_bound_by_the_model_binding_only`. Rename the test to match. Change nothing else in that file.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except criterion 7's binder test.
   - Line and function coverage of `hilclaw/` stay >= 80%, and `hilclaw/model_binding.py` stays at 100% line coverage if it is there now (otherwise does not drop).
   - CI is green.
9. **No other file changes.** Do not edit `hilclaw/model_gemm.py`, `hilclaw/model_execute.py`, the model program C source, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/keys.py`, any registry or tool module, any `ARCHITECTURE/` or `PROCESS/` file. In `## Result`, list any record sentence that becomes less exact (for example ADR-0153 decision 3 "for other kinds, through the prototypes of their future contract records") without editing it.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0437-<slug>`, Draft PR whose title contains `T-0437` and whose body ends with `Task: T-0437`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: the host side of the executor is Python, ADR-0153 decision 2).
    - The reviewer checks at least:
      - the call-site names and rows against ADR-0152 decision 2, and `(m, n)` = `(rows, hidden)` against ADR-0158 decision 2;
      - the fit comparison against `rmsnorm_bf16_contract.task_contract` and the "every shape" acceptance against ADR-0158 decision 7;
      - the invalid-input reason against ADR-0157 decision 4;
      - `rmsnorm_eps` against ADR-0158 decisions 5 and 7;
      - that `check` and `hilclaw/model_gemm.py` behave as before;
      - that nothing adds meaning beyond the records (no joined full-pass check, no fp32 RMSNorm, no eps default, no tolerance, no build or run).

## Out of Scope

- Joining the GEMM and RMSNorm checks into one generation check, and the full pass and generation loop (ADR-0153 code slice 2, after the contract records of elementwise add, SwiGLU activation, RoPE and SDPA with KV cache).
- Passing `eps` to the model program; the model program, its build and run steps calling `hilclaw_rmsnorm_bf16`; linking the math library (a build setting, with HQ-0033); hand-written bf16 RMSNorm kernel fixtures; any C code.
- The RMSNorm weights as executor inputs and their element type check (ADR-0157 decision 1; they reach the executor with the full pass).
- The P2-12 harness part of ADR-0158 (generator over the value set, widening, comparison, tolerance).
- Registering the RMSNorm contract with `correctness.check`, `spec.write` or the instance start.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, the next pieces toward P2-13 and P2-14 are the contract ADRs of the remaining four kinds (elementwise add, SwiGLU activation, RoPE, SDPA with KV cache; one record each, ADR-0158 Boundaries), then their code slices; the hand-written bf16 RMSNorm kernel fixtures and the math-library link question (HQ-0033) come with the model program's RMSNorm call.

## Result

- **Outcome**: DONE. PR #257 squash-merged as `37d63b7` (branch `claude/T-0437-rmsnorm-bf16-binding-check` deleted; squash message ends with `Task: T-0437`). Review: 1 round, Approve (three non-blocking notes, all answered here; no code change needed). CI green on all jobs (Python 3.11/3.14, Coverage, Test presence, C, sh).
- **Language**: Python, as the host side of the executor is Python (ADR-0153 decision 2).
- **Changes**: `hilclaw/model_binding.py` adds `RMSNORM_CALL_SITES`, `RMSNORM_DTYPES`, `rmsnorm_shape`, `rmsnorm_generation_calls`, `check_rmsnorm` and `rmsnorm_eps`; the fit comparison, per-call-site loop and entry validation became private helpers shared by both checks. `check`, `gemm_shape`, `generation_calls`, `CALL_SITES`, `DTYPES` and existing messages are unchanged; `hilclaw/model_gemm.py` not edited. Tests: new cases in `tests/test_model_binding.py` (happy/error/branch/negative for every new public name); `tests/test_rmsnorm_bf16_contract.py` binder test renamed. Local: 27789 passed, 949 skipped; `model_binding.py` 100%, `hilclaw/` 97%.
- **Size**: `model_binding.py` diff +246/-55 = 301 lines, one over the D4 cap (mostly docstrings required by criterion 5); not split.
- **Record sentences now less exact (not edited, criterion 9)**: ADR-0153 decision 3 ("through the prototypes of their future contract records" - the rmsnorm record and its check now exist); ADR-0157 decision 4 ("With the GEMM call sites only ... {fp32, bf16}" - RMSNorm call sites now have their own range {bf16}, checked separately until the full pass joins the checks).
- **Follow-ups**: none new; the planner follow-up above stands.
