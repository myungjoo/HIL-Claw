---
id: T-0443
title: Add the SwiGLU call site ffn_activation to hilclaw/model_binding.py - its shape (rows x intermediate) over a generation and a binding check with fit against the bf16 swiglu contract and "every shape" accepted (ADR-0160 decisions 2, 8 and 12), with the dtype range of ADR-0157 decision 4 - with tests (ADR-0160 code slice, second part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0442]
touchesFiles: [hilclaw/model_binding.py, tests/test_model_binding.py, tests/test_swiglu_bf16_contract.py]
estimatedSize: {loc: 150, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `eb9f28c`):
- ADR-0160 (T-0441, landed as `58e2aed`) defines the bf16 SwiGLU activation contract on `cpu_standin`. T-0442 (PR #260, `3d50823`) landed part 1 of its code slice:
  - the kind `swiglu` (members `m`, `n`) in `hilclaw.keys`;
  - `hilclaw/swiglu_bf16_contract.py` (`KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES`, `GATE_PATTERNS`, `UP_PATTERNS`, `op_signature_record`, `task_contract`, `covers`).
- ADR-0160 Consequences (line 187) name the next part: "the binding check in `hilclaw/model_binding.py` with the call site `ffn_activation` of decision 12, its shape (rows × intermediate) and the 'every shape' binding, `bf16` as the only dtype at which the kind is known". T-0442's planner follow-up names it as the next step.
- Today `hilclaw/model_binding.py` checks the six GEMM call sites (`check`) and, separately, the three RMSNorm call sites (`check_rmsnorm`, T-0437) and the two elementwise add call sites (`check_elementwise_add`, T-0440). The last two share the private helpers `_row_shape`, `_row_generation_calls` and `_check_rows`. Its docstring says it "knows no call site of RoPE, SDPA or SwiGLU".

**What the accepted records already settle** (so this task invents nothing):
- The call site is ADR-0152 decision 2 row 12 ("SwiGLU activation: silu(gate) · up, elementwise"), named `ffn_activation` (ADR-0160 decision 12). It is the only SwiGLU call site.
- Each call takes two T × intermediate inputs into a T × intermediate output: `m` = T (the rows of the pass), `n` = the intermediate width (ADR-0160 decision 2: "`n` = the intermediate width of each row"; ADR-0152 decision 5). **This differs from the RMSNorm and elementwise add call sites, whose `n` is `hidden`.** In `ModelDimensions` the width is the field `intermediate`.
- Fit: compare the bound kernel's `task.contract` with the contract of the call site's kind and dtype on `language`, `prototype` and each operand's `name`, `role`, `dtype` (ADR-0153 decision 3; the comparison `_check_rows` already makes).
- A binding "for every shape", and a listed shape other than the spec's own, are accepted for this contract (ADR-0160 decision 8, "Every set of dimensions"; ADR-0153 decision 3).
- The dtype: a dtype at which the kind of a call site has no contract is invalid input, and the outcome names the dtype and the kind (ADR-0157 decision 4). Only `bf16` has a `swiglu` contract (ADR-0160 decision 1: "No fp32 or fp16 contract of this kind is defined").
- The contract has no scalar parameter, so there is no counterpart of `rmsnorm_eps`.

**So this task adds a SwiGLU binding check beside `check`, `check_rmsnorm` and `check_elementwise_add`, not inside them**, exactly as T-0440 did for elementwise add. Joining the checks of every kind into one generation check belongs to the full pass (ADR-0153 code slice 2), which needs the two remaining contract records (RoPE, SDPA with KV cache). Which arrays the call passes as `gate`, `up` and `out` (ADR-0160 decision 12's operand table) is also the full pass's, not a binding check's. If the executor or reviewer reads ADR-0153, ADR-0157 or ADR-0160 as requiring something else, stop and return BLOCKED (`requirement-unclear`) and name the sentence.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json` (round 0's board step on HQ-0021; the round >= 1 steps and P2-6/P2-7 on HQ-0048 and HQ-0024; the gate half of P2-4 is owner-only, OD-3), and P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is code that P2-13 and P2-14 need: the forward pass cannot bind a SwiGLU kernel without it, and ADR-0160 Consequences list it as part of the record's code slice. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, A-13 and D16.** No open decision is needed; every rule comes from ADR-0152, ADR-0153, ADR-0157 and ADR-0160 as accepted. Nothing in the data plane changes (`model_binding` reads and writes no file). Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0443-<slug>`, PR title with `T-0443`, commit trailer `Task: T-0443`, last line of the PR body `Task: T-0443`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md` decision 2 (the table, lines 41-66; rows 11, 12 and 13) and decision 5 (lines 84-104).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` decision 3 (lines 40-46) and decision 5 (lines 58-62).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md` decision 4 (lines 66-71) and decision 5 (lines 73-78).
- `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`: decision 1 (lines 34-37), decision 2 (lines 39-43), decision 7 (lines 80-102), decision 8 (lines 104-118), decision 12 (lines 151-160), Consequences (lines 184-191).
- `hilclaw/model_binding.py`, the whole file (823 lines). This is the file you change. In particular the module docstring (lines 1-76), `ModelDimensions`, `BindingEntry`, `Outcome`, `BindingCheck` (lines 124-170), `check_rmsnorm` and the elementwise add part (lines 344-510), and the private helpers `_row_shape`, `_row_generation_calls`, `_check_rows`, `_bind`, `_no_contract`, `_unfit`, `_binding`, `_entry`, `_no_overlap` (from line 539).
- `hilclaw/swiglu_bf16_contract.py`, the whole file. Read only; do not edit.
- `hilclaw/model_gemm.py` lines 1-60 and its call of `model_binding.check`: the existing caller, which must not change behaviour.
- `tests/test_model_binding.py`: lines 1-82 (imports, `SMALL` with `hidden=8, intermediate=16`, helpers), and the elementwise add tests from line 1546 to the end of the file. They are the model for the new tests.
- `tests/test_swiglu_bf16_contract.py` lines 86-97 (`OTHER_CONTRACTS`, `OTHER_MODULE_NAMES`) and lines 561-584 (`test_module_imports_keys_only_and_is_named_by_no_other_module`), and, as the model for its new form, `tests/test_elementwise_add_bf16_contract.py` lines 507-532 (`test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`).
- `PROCESS/tasks/T-0440-elementwise-add-bf16-binding-check.md` `## Result` (how the shared helpers were factored).

## Acceptance Criteria

1. **New public names in `hilclaw/model_binding.py`** (Python; no new import other than `hilclaw.swiglu_bf16_contract`):
   - `SWIGLU_CALL_SITES = ("ffn_activation",)`: ADR-0152 decision 2 row 12, named as ADR-0160 decision 12.
   - `SWIGLU_DTYPES = (swiglu_bf16_contract.DTYPE,)`: the dtypes at which the `swiglu` contract is known (ADR-0157 decision 4, ADR-0160 decision 1).
   - `swiglu_shape(dimensions, call_site, rows)`: returns `(rows, dimensions.intermediate)`, the `(m, n)` of ADR-0160 decision 2. It raises as `elementwise_add_shape` does: first as `check_dimensions`, then `ValueError` with `parameter` `"call_site"` for a call site not in `SWIGLU_CALL_SITES`, then `TypeError`/`ValueError` with `parameter` `"rows"` for `rows` that is not an `int` from 1 to 2**53 - 1.
   - `swiglu_generation_calls(dimensions, *, prompt_length, generation_length)`: per call site in `SWIGLU_CALL_SITES` order, the sorted tuple of distinct shapes of a generation, as `(call_site, shapes)` pairs. Same passes as `generation_calls`, `rmsnorm_generation_calls` and `elementwise_add_generation_calls`; raises like `elementwise_add_generation_calls`.
   - `check_swiglu(dimensions, binding, *, dtype, prompt_length, generation_length)`: returns a `BindingCheck`. Details in criterion 2.
   - Nothing else public is added.
2. **`check_swiglu`** behaves as `check_elementwise_add`, with this kind's call site, dtypes, contract and width:
   - **Arguments refused first**, in the order `dimensions`, `dtype`, `prompt_length`, `generation_length`, `binding`, each error carrying `parameter` = the argument's name, with the same types and messages as `check_elementwise_add`. `binding` keys must be in `SWIGLU_CALL_SITES`: a GEMM, RMSNorm or elementwise add call-site key is refused. Entries, kernel references, the `"every"` rule and the overlap rule are those of `check_elementwise_add`, with `(m, n)` pairs as shapes; a triple is refused.
   - **Outcomes**, in this order:
     1. `"invalid_input"` (`call_site` and `shape` `None`): a `dtype` not in `SWIGLU_DTYPES`, with the reason `dtype: no swiglu contract is known at the dtype '<dtype>'` (the existing `_no_contract` form); then `prompt_length`, then `generation_length` outside 1 to 2**53 - 1.
     2. For `ffn_activation`: `"kernel_unfit"` for each entry whose `contract` is not the bf16 `swiglu` contract, compared on `language`, `prototype` and the operands' `(name, role, dtype)`, with reference values taken from `swiglu_bf16_contract.task_contract` at call time, never from the entry's own contract (operand shapes and extra members ignored); the label in the reason is `bf16 swiglu`. Then `"no_kernel"` for each shape of `swiglu_generation_calls` that no entry covers.
     - As in `check_elementwise_add`: no `"no_kernel"` outcome is looked for when there is an `"invalid_input"`, and no per-call-site outcome at all when `dtype` is not in `SWIGLU_DTYPES`.
   - A listed shape other than the kernel's own spec shape, and an `"every"` entry, are accepted (ADR-0160 decision 8).
   - `calls` holds `(call_site, shape, kernel)` for every call of `swiglu_generation_calls`, in its order, only when `ok`.
   - Arguments are not modified. Nothing is built, started or read. The operand wiring of ADR-0160 decision 12 is not checked here.
3. **Reuse the shared helpers, with the width as their parameter.**
   - `_row_shape` and `_row_generation_calls` today return `(rows, dimensions.hidden)`. Give them a way to take the width (for example a `ModelDimensions` field name or a callable), so that RMSNorm and elementwise add keep `hidden` and SwiGLU uses `intermediate`. `_check_rows` reaches the width through the `site_calls` function it already receives; check that nothing in it assumes `hidden`.
   - Do not duplicate `_check_rows`. Its lookup of `contract.task_contract` at call time must give the same effect for `swiglu_bf16_contract` as `test_check_rmsnorm_reference_comes_from_the_contract_module` shows for RMSNorm.
4. **The GEMM, RMSNorm and elementwise add sides do not change behaviour.** `check`, `gemm_shape`, `generation_calls`, `CALL_SITES`, `DTYPES`, `check_rmsnorm`, `rmsnorm_shape`, `rmsnorm_generation_calls`, `rmsnorm_eps`, `RMSNORM_CALL_SITES`, `RMSNORM_DTYPES`, `check_elementwise_add`, `elementwise_add_shape`, `elementwise_add_generation_calls`, `ELEMENTWISE_ADD_CALL_SITES`, `ELEMENTWISE_ADD_DTYPES` and every existing message stay as they are. Every existing test in `tests/test_model_binding.py` passes unchanged. `hilclaw/model_gemm.py` is not edited.
5. **Docstrings.**
   - Rewrite the module docstring (first line included): the module now also checks the SwiGLU call site against the bf16 `swiglu` contract (ADR-0160), whose `n` is the intermediate width. It knows no call site of RoPE or SDPA. It does not join the GEMM, RMSNorm, elementwise add and SwiGLU checks into one generation check (the full pass, ADR-0153 code slice 2), and it does not check which arrays a call passes (ADR-0159 decision 12, ADR-0160 decision 12). It keeps the other "does not do" points. The "Readings" bullet on listed shapes and `"every"` names the `swiglu` contract too (ADR-0160 decision 8), with the right count of contracts.
   - Update the docstrings that name the kinds or checks: `ModelDimensions` (if it names which call sites use `intermediate`), `BindingEntry` (a shape is `(m, n)` for an RMSNorm, elementwise add or SwiGLU call site), `Outcome`, `BindingCheck`, and those of `check_elementwise_add` or others that say a check "stands beside" the existing ones.
   - Each new public name has a Doxygen-like docstring in the module's style. Other comments follow CLAUDE.md "코멘트 최소화".
6. **Tests in `tests/test_model_binding.py`** (D12: happy, error, branch and negative cases, every new public name). At least:
   - `SWIGLU_CALL_SITES` and `SWIGLU_DTYPES` values.
   - `swiglu_shape`: small values give `(rows, 16)` with `SMALL` (the intermediate width, not the hidden width 8); at hidden 2048 and intermediate 8192 with T in {1, 32, 512}, the result equals `swiglu_bf16_contract.SHAPES`; unknown call site (including a GEMM name such as `gate`, an RMSNorm name and an elementwise add name), bad rows, bad dimensions, argument order.
   - `swiglu_generation_calls`: prefill and decode, generation length 1, prompt of one row; rows match those of `elementwise_add_generation_calls` while `n` is `intermediate`; refused arguments; lengths keyword-only.
   - `check_swiglu`:
     - ok with an `"every"` binding, with listed shapes covering exactly, and with several disjoint entries; `calls` order; generation length 1; path sources accepted;
     - a listed shape other than the kernel's spec shape is accepted;
     - a binding listing `(rows, hidden)` shapes instead of `(rows, intermediate)` gives `"no_kernel"`;
     - each `"invalid_input"` case and their order; `fp32` and `fp16` named in the reason with `swiglu`; no unfit and no `"no_kernel"` for an unknown dtype;
     - `"kernel_unfit"` for a kernel written to the bf16 `elementwise_add` contract (same operand roles and dtype, different names and prototype), to the bf16 `rmsnorm` contract, to the bf16 `gemm` and the fp32 `gemm` contract; for a wrong prototype, language, operand name, role or dtype; for the `gate` and `up` operands swapped; a non-mapping contract; a missing member; wrong operand forms;
     - fit ignores operand shapes and extra members;
     - the reference comes from `swiglu_bf16_contract.task_contract` (monkeypatched, as the RMSNorm and elementwise add tests do);
     - `"no_kernel"` for a missing call site and an unlisted shape;
     - argument refusals with their `parameter` and order, including a GEMM, an RMSNorm and an elementwise add call-site key, a triple shape, an overlap, and an `"every"` beside another entry;
     - arguments not modified.
   - `check`, `check_rmsnorm` and `check_elementwise_add` each refuse an `ffn_activation` binding key.
   - Existing tests are not edited, removed or weakened.
7. **Tests in `tests/test_swiglu_bf16_contract.py`**: change only the binder test `test_module_imports_keys_only_and_is_named_by_no_other_module` (line 561) so that `hilclaw/model_binding.py` is the one module allowed to name `swiglu_bf16_contract` and must name it, in the form of `tests/test_elementwise_add_bf16_contract.py`'s `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`, and rename it to that name. Its other assertions (imports, `OTHER_MODULE_NAMES` absent from the module's own text, no `__main__`, no `main`) stay. Change nothing else in that file.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except criterion 7's binder test.
   - Line and function coverage of `hilclaw/` stay >= 80%, and `hilclaw/model_binding.py` stays at 100% line coverage.
   - CI is green.
   - Size: the D4 cap is 300 changed lines outside tests. If exceeded, finish and propose a split in `## Follow-ups`.
9. **No other file changes.** Do not edit `hilclaw/model_gemm.py`, `hilclaw/model_execute.py`, the model program C source, any `hilclaw/*_contract.py`, `hilclaw/keys.py`, any registry or tool module, any test other than the two named above, any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`. In `## Result`, list any record sentence that becomes less exact (for example ADR-0153 decision 3 "future contract records", ADR-0157 decision 4's range, ADR-0160 Consequences' code slice list) without editing it.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0443-<slug>`, Draft PR whose title contains `T-0443` and whose body ends with `Task: T-0443`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: the host side of the executor is Python, ADR-0153 decision 2).
    - The reviewer checks at least:
      - the call-site name against ADR-0160 decision 12 and ADR-0152 decision 2 row 12, and `(m, n)` = `(rows, intermediate)` against ADR-0160 decision 2;
      - the fit comparison against `swiglu_bf16_contract.task_contract` and the "every shape" acceptance against ADR-0160 decision 8;
      - the invalid-input reason against ADR-0157 decision 4;
      - that `check`, `check_rmsnorm`, `check_elementwise_add`, `rmsnorm_eps` and `hilclaw/model_gemm.py` behave as before (RMSNorm and elementwise add still use `hidden`);
      - that nothing adds meaning beyond the records (no joined full-pass check, no fp32 swiglu, no operand wiring or buffer layout, no in-place allowance, no tolerance, no build or run).

## Out of Scope

- Joining the GEMM, RMSNorm, elementwise add and SwiGLU checks into one generation check, and the full pass and generation loop (ADR-0153 code slice 2, after the contract records of RoPE and SDPA with KV cache).
- The operand wiring of ADR-0160 decision 12 and the extra buffer of decision 8; the model program and its build and run steps calling `hilclaw_swiglu_bf16`; hand-written bf16 SwiGLU kernel fixtures; any C code; linking the math library.
- The P2-12 harness part of ADR-0160 (generator over the two value sets, widening, comparison, tolerance).
- Registering the swiglu contract with `correctness.check`, `spec.write` or the instance start.
- The contracts of RoPE and SDPA with KV cache; fp16; an fp32 contract of this kind.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, ADR-0160's binding part is done. The next piece toward P2-13 and P2-14 is the contract record (doc, OD-31/OD-6) of the RoPE kind, then its code slices, then SDPA with KV cache. The hand-written bf16 SwiGLU kernel fixtures come with the model program's calls of that kind.

## Result

- Outcome: DONE. PR #261 squash-merged as 46bdaa6 (branch `claude/T-0443-swiglu-bf16-binding-check` deleted). Review: 1 round, Approve (context-isolated dev-reviewer). Two Nits, neither needing a code change: (a) list the less exact records in this Result (done below); (b) merge only after CI is green (done).
- Language: Python - the host side of the executor is Python (ADR-0153 decision 2).
- Change: `hilclaw/model_binding.py` gains `SWIGLU_CALL_SITES = ("ffn_activation",)`, `SWIGLU_DTYPES = ("bf16",)`, `swiglu_shape` (returns `(rows, intermediate)`), `swiglu_generation_calls` and `check_swiglu`. `check_swiglu` reuses `_check_rows`: the reference contract comes from `swiglu_bf16_contract.task_contract` at call time; the label is `bf16 swiglu`; an unknown dtype gives the reason `dtype: no swiglu contract is known at the dtype '<dtype>'`. The private helpers `_row_shape` and `_row_generation_calls` now take the `ModelDimensions` field name of the width: `"hidden"` for RMSNorm and elementwise add, `"intermediate"` for SwiGLU. No existing public name, message or behaviour changed, and `hilclaw/model_gemm.py` is untouched.
- Tests: new SwiGLU tests in `tests/test_model_binding.py` (additions only). The binder test in `tests/test_swiglu_bf16_contract.py` is renamed to `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only` and now requires `model_binding.py` as the only binder.
- Gates: `ruff check` and `ruff format --check` clean. Full local pytest: 28442 passed, 949 skipped. Coverage: `hilclaw/` 97% of lines, `model_binding.py` 100%. CI all green: Python 3.11 and 3.14, Coverage, C (clang), sh (shellcheck), test presence.
- Size: 198 changed lines outside tests (153+/45-), under the D4 cap of 300.
- Records now less exact (not edited): ADR-0153 decision 3 ("future contract records"; "for every other kind, its contract record says"); ADR-0157 decision 4 (range stated "with the GEMM call sites only"); ADR-0160 Consequences (the binding-check part of the code slice list has now landed).
- Follow-ups: none from this task. (planner) Next toward P2-13/P2-14: the RoPE contract record, then its code slices, then SDPA with KV cache.
