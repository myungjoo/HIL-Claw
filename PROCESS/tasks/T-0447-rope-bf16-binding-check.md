---
id: T-0447
title: Add the RoPE call sites rope_q and rope_k to hilclaw/model_binding.py - their shapes (rows x heads x head_dim and rows x kv_heads x head_dim) over a generation and a binding check with fit against the bf16 rope contract and "every shape" accepted (ADR-0161 decisions 2, 3, 10, 11 and 15), with the dtype range of ADR-0157 decision 4 - with tests (ADR-0161 code slice, third part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0445]
touchesFiles: [hilclaw/model_binding.py, tests/test_model_binding.py, tests/test_rope_bf16_contract.py]
estimatedSize: {loc: 170, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `66a04cf`):
- ADR-0161 (T-0444, landed as `7c8c5c6`) defines the bf16 RoPE contract on `cpu_standin`. Its code slice has landed in two parts so far:
  - T-0445 (PR #262, `849fffa`): the kind `rope` (members `m`, `h`, `d`) in `hilclaw.keys` and `hilclaw/rope_bf16_contract.py` (`KIND`, `DTYPE`, `TABLE_DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES`, `X_PATTERNS`, `op_signature_record`, `task_contract(m, h, d)`, `covers`);
  - T-0446 (PR #263, `4c3dac5`): the host-side table builder `hilclaw/rope_table.py`.
- ADR-0161 Consequences (line 188) name the next part: "the binding check in `hilclaw/model_binding.py` with `rope_q`, `rope_k`, shape (rows, heads, head_dim) and the 'every shape' binding, `bf16` only". T-0446's planner follow-up names it as the next step.
- Today `hilclaw/model_binding.py` checks the six GEMM call sites (`check`) and, separately, the RMSNorm (`check_rmsnorm`, T-0437), elementwise add (`check_elementwise_add`, T-0440) and SwiGLU (`check_swiglu`, T-0443) call sites. The last three share the private helpers `_row_shape`, `_row_generation_calls` and `_check_rows`, which assume a two-member shape `(m, n)` (`_ROW_SHAPE`) and call `contract.task_contract(1, 1)` for the reference. Its docstring says it "knows no call site of RoPE or SDPA".

**What the accepted records already settle** (so this task invents nothing):
- Row 5 of ADR-0152 decision 2 is **two calls** of the one kind `rope`, Q then K (ADR-0161 decision 2). Their call sites are **`rope_q` and `rope_k`, in that order** (decision 15).
- The shape members are `m`, `h`, `d`: `m` = T, the rows of the pass; `h` = the heads of the rotated tensor; `d` = head_dim (decision 3). For Q, h is the query head count (`ModelDimensions.heads`); for K, h is the KV head count (`ModelDimensions.kv_heads`) (decision 2: "Q (h = 32) then K (h = 8)"; ADR-0152 decision 5 row "RoPE": "Q as T × H × d_h and K as T × 8 × d_h"). So `rope_q` has shape `(rows, heads, head_dim)` and `rope_k` has `(rows, kv_heads, head_dim)`. **This is the first row-wise kind with a three-member shape, and the first whose shape differs between its call sites.**
- The position P is neither a member nor a parameter; `rope_theta` and the scaling constants reach the kernel only through the table (decision 3). So the binding check needs no RoPE constant and no position, and the shapes of a generation are those of its passes' row counts, as for the other row-wise kinds.
- Fit: compare the bound kernel's `task.contract` with the contract of the call site's kind and dtype on `language`, `prototype` and each operand's `name`, `role`, `dtype` (ADR-0153 decision 3; the comparison `_unfit` already makes). The rope contract has three operands `x` (bf16), `freqs_cis` (**fp32**), `out` (bf16) (decision 10).
- A binding "for every shape", and a listed shape other than the spec's own, are accepted for this contract (decision 11, "Every set of dimensions": "a binding 'for every shape' of ADR-0153 decision 3 is accepted").
- The dtype: a dtype at which the kind has no contract is invalid input, and the outcome names the dtype and the kind (ADR-0157 decision 4). Only `bf16` has a `rope` contract (decision 1: "No fp32 or fp16 contract of this kind is defined").
- `d` is even and at least 2 is a caller guarantee (decision 11). `check_dimensions` does not require an even `head_dim`, and must not start to (the GEMM, RMSNorm, elementwise add and SwiGLU sides do not change). This task refuses an odd `head_dim` in the RoPE functions only, with `ValueError` and `parameter` `"dimensions"`, as `check_dimensions` refuses another well-typed model parameter set the contracts cannot run (`heads` not a multiple of `kv_heads`). That placement is a convention of this module, not a rule of the record; say so in the docstring.

**So this task adds a RoPE binding check beside `check`, `check_rmsnorm`, `check_elementwise_add` and `check_swiglu`, not inside them**, exactly as T-0443 did for SwiGLU. Joining the checks of every kind into one generation check belongs to the full pass (ADR-0153 code slice 2), which still needs the SDPA with KV cache contract record. Which arrays a call passes as `x`, `freqs_cis` and `out` (decision 15's operand table), the row slicing of the table for a position P, and the RoPE constants as model parameters are the full pass's or later slices', not a binding check's. If the executor or reviewer reads ADR-0153, ADR-0157 or ADR-0161 as requiring something else, stop and return BLOCKED (`requirement-unclear`) and name the sentence.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json` (round 0's board step on HQ-0021; the round >= 1 steps and P2-6/P2-7 on HQ-0048 and HQ-0024; the gate half of P2-4 is owner-only, OD-3), and P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is code that P2-13 and P2-14 need: the forward pass cannot bind a RoPE kernel without it, and ADR-0161 Consequences list it as part of the record's code slice. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, HQ-0070, A-13 and D16.** No open decision is needed; every rule comes from ADR-0152, ADR-0153, ADR-0157 and ADR-0161 as accepted. HQ-0070 (the scale factor) does not touch the binding check: no RoPE constant enters it. Nothing in the data plane changes (`model_binding` reads and writes no file). Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0447-<slug>`, PR title with `T-0447`, commit trailer `Task: T-0447`, last line of the PR body `Task: T-0447`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: decision 2 row 5 (line 51) and decision 5, the RoPE row (line 98).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (lines 40-46) and decision 5 (lines 58-62).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-71) and decision 5 (lines 73-77).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`: decision 1 (lines 37-39), decision 2 (lines 41-43), decision 3 (lines 45-49), decision 6 (lines 62-66), decision 10 (lines 88-110), decision 11 (lines 112-124), decision 13's "Not detected by the kernel's verification" sentence (line 135), decision 15 (lines 154-163), Consequences (lines 185-193).
- `hilclaw/model_binding.py`, the whole file (931 lines). This is the file you change. In particular the module docstring (lines 1-84), `ModelDimensions`, `BindingEntry`, `Outcome`, `BindingCheck` (lines 136-183), `check_dimensions` (lines 186-209), `check_swiglu` and its neighbours (lines 532-614), and the private helpers `_row_shape`, `_row_generation_calls`, `_check_rows`, `_bind`, `_no_contract`, `_unfit`, `_binding`, `_entry`, `_no_overlap` (from line 644).
- `hilclaw/rope_bf16_contract.py`, the whole file. Read only; do not edit.
- `hilclaw/model_gemm.py` lines 1-60 and its call of `model_binding.check`: the existing caller, which must not change behaviour.
- `tests/test_model_binding.py`: lines 1-98 (imports, `SMALL` with `heads=4, kv_heads=2, head_dim=2`, helpers), and the SwiGLU tests from line 2247 to the end of the file. They are the model for the new tests.
- `tests/test_rope_bf16_contract.py` lines 92-105 (`OTHER_CONTRACTS`, `OTHER_MODULE_NAMES`) and lines 588-599 (`test_module_imports_keys_only_and_is_named_by_no_other_module`), and, as the model for its new form, `tests/test_swiglu_bf16_contract.py` lines 561-575 (`test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`).
- `tests/test_rope_table.py` lines 586-590 (`test_the_module_is_named_by_no_other_module`): it asserts that no other `hilclaw/*.py` file contains the text `rope_table`. Read only.
- `PROCESS/tasks/T-0443-swiglu-bf16-binding-check.md` `## Result` (how the shared helpers were parameterised).

## Acceptance Criteria

1. **New public names in `hilclaw/model_binding.py`** (Python; no new import other than `hilclaw.rope_bf16_contract`):
   - `ROPE_CALL_SITES = ("rope_q", "rope_k")`: ADR-0152 decision 2 row 5, named and ordered as ADR-0161 decision 15.
   - `ROPE_DTYPES = (rope_bf16_contract.DTYPE,)`: the dtypes at which the `rope` contract is known (ADR-0157 decision 4, ADR-0161 decision 1).
   - `rope_shape(dimensions, call_site, rows)`: returns `(rows, dimensions.heads, dimensions.head_dim)` for `rope_q` and `(rows, dimensions.kv_heads, dimensions.head_dim)` for `rope_k`, the `(m, h, d)` of ADR-0161 decisions 2 and 3. It raises, in this order: as `check_dimensions` does; then `ValueError` with `parameter` `"dimensions"` for an odd `head_dim` (ADR-0161 decision 11); then `ValueError` with `parameter` `"call_site"` for a call site not in `ROPE_CALL_SITES`; then `TypeError`/`ValueError` with `parameter` `"rows"` for `rows` that is not an `int` from 1 to 2**53 - 1.
   - `rope_generation_calls(dimensions, *, prompt_length, generation_length)`: per call site in `ROPE_CALL_SITES` order, the sorted tuple of distinct shapes of a generation, as `(call_site, shapes)` pairs. Same passes as `generation_calls` and the other row-wise kinds; raises like `swiglu_generation_calls`, plus the odd `head_dim` refusal right after `check_dimensions`.
   - `check_rope(dimensions, binding, *, dtype, prompt_length, generation_length)`: returns a `BindingCheck`. Details in criterion 2.
   - Nothing else public is added.
2. **`check_rope`** behaves as `check_swiglu`, with this kind's call sites, dtypes, contract and three-member shapes:
   - **Arguments refused first**, in the order `dimensions` (including the odd `head_dim` refusal), `dtype`, `prompt_length`, `generation_length`, `binding`, each error carrying `parameter` = the argument's name, with the same types and messages as `check_swiglu`. `binding` keys must be in `ROPE_CALL_SITES`: a GEMM, RMSNorm, elementwise add or SwiGLU call-site key is refused. Entries, kernel references, the `"every"` rule and the overlap rule are those of `check_swiglu`, with `(m, h, d)` triples as shapes; a pair is refused, and the type error for a non-tuple shape names `(m, h, d)`.
   - **Outcomes**, in this order:
     1. `"invalid_input"` (`call_site` and `shape` `None`): a `dtype` not in `ROPE_DTYPES`, with the reason `dtype: no rope contract is known at the dtype '<dtype>'` (the existing `_no_contract` form); then `prompt_length`, then `generation_length` outside 1 to 2**53 - 1.
     2. Per call site in `ROPE_CALL_SITES` order: `"kernel_unfit"` for each entry whose `contract` is not the bf16 `rope` contract, compared on `language`, `prototype` and the operands' `(name, role, dtype)`, with reference values taken from `rope_bf16_contract.task_contract` at call time (with any valid even `d`, for example `task_contract(1, 1, 2)`), never from the entry's own contract (operand shapes and extra members ignored); the label in the reason is `bf16 rope`. Then `"no_kernel"` for each shape of `rope_generation_calls` that no entry covers.
     - As in `check_swiglu`: no `"no_kernel"` outcome is looked for when there is an `"invalid_input"`, and no per-call-site outcome at all when `dtype` is not in `ROPE_DTYPES`.
   - A listed shape other than the kernel's own spec shape, and an `"every"` entry, are accepted (ADR-0161 decision 11).
   - `calls` holds `(call_site, shape, kernel)` for every call of `rope_generation_calls`, in its order, only when `ok`.
   - Arguments are not modified. Nothing is built, started or read. The operand wiring of ADR-0161 decision 15, the table, its rows for a position and the RoPE constants are not checked here.
3. **Reuse the shared helpers; do not duplicate `_check_rows`, `_bind` or `_binding`.**
   - Give `_check_rows` what it needs for a kind whose shape is not `(m, n)`: the shape members passed to `_binding` (today the constant `_ROW_SHAPE`) and the reference contract (today `contract.task_contract(1, 1)`). For example two more arguments, or a small per-kind description. RMSNorm, elementwise add and SwiGLU keep `("m", "n")` and `task_contract(1, 1)`.
   - The lookup of `contract.task_contract` must stay at call time, so that monkeypatching `rope_bf16_contract.task_contract` changes the reference, as `test_check_rmsnorm_reference_comes_from_the_contract_module` shows for RMSNorm.
   - `rope_shape` does not go through `_row_shape` (the width differs per call site); `rope_generation_calls` may reuse `_pass_rows` and follow `_row_generation_calls`.
4. **The GEMM, RMSNorm, elementwise add and SwiGLU sides do not change behaviour.** `check_dimensions`, `check`, `gemm_shape`, `generation_calls`, `CALL_SITES`, `DTYPES`, `check_rmsnorm`, `rmsnorm_shape`, `rmsnorm_generation_calls`, `rmsnorm_eps`, `RMSNORM_CALL_SITES`, `RMSNORM_DTYPES`, `check_elementwise_add`, `elementwise_add_shape`, `elementwise_add_generation_calls`, `ELEMENTWISE_ADD_CALL_SITES`, `ELEMENTWISE_ADD_DTYPES`, `check_swiglu`, `swiglu_shape`, `swiglu_generation_calls`, `SWIGLU_CALL_SITES`, `SWIGLU_DTYPES` and every existing message stay as they are; in particular `check_dimensions` still accepts an odd `head_dim`. Every existing test in `tests/test_model_binding.py` passes unchanged. `hilclaw/model_gemm.py` is not edited.
5. **Docstrings.**
   - Rewrite the module docstring (first line included): the module now also checks the two RoPE call sites against the bf16 `rope` contract (ADR-0161), whose shape is `(m, h, d)` with `h` the query heads for `rope_q` and the KV heads for `rope_k`, and which needs an even `head_dim` (the odd-`head_dim` refusal is this module's convention). It knows no call site of SDPA. It does not join the GEMM, RMSNorm, elementwise add, SwiGLU and RoPE checks into one generation check (the full pass, ADR-0153 code slice 2), and it does not check which arrays a call passes (ADR-0159, ADR-0160 and ADR-0161 decisions 12, 12 and 15), the frequency table or its rows, or any RoPE constant. It keeps the other "does not do" points. The "Readings" bullet on listed shapes and `"every"` names the `rope` contract too (ADR-0161 decision 11), with the right count of contracts.
   - Update the docstrings that name the kinds or checks: `ModelDimensions` (it now also gives the RoPE shapes, through `heads`, `kv_heads` and `head_dim`), `BindingEntry` (a shape is `(m, h, d)` for a RoPE call site), `Outcome`, `BindingCheck`, and those of `check_swiglu` or others that say a check "stands beside" the existing ones.
   - **The text of `hilclaw/model_binding.py`, docstrings included, must not contain the string `rope_table`** (the test of `tests/test_rope_table.py` in Required Reading would fail). If the table builder is named, name it as "the host-side table builder (ADR-0161 decision 4)".
   - Each new public name has a Doxygen-like docstring in the module's style. Other comments follow CLAUDE.md "코멘트 최소화".
6. **Tests in `tests/test_model_binding.py`** (D12: happy, error, branch and negative cases, every new public name). At least:
   - `ROPE_CALL_SITES` and `ROPE_DTYPES` values.
   - `rope_shape`:
     - with `SMALL`, `rope_q` gives `(rows, 4, 2)` and `rope_k` gives `(rows, 2, 2)`;
     - with dimensions whose `heads` and `kv_heads` differ from `SMALL`'s, each call site follows its own head field only;
     - at hidden 2048, intermediate 8192, heads 32, kv_heads 8, head_dim 64 with T in {1, 128, 2048}, `rope_q` then `rope_k` give exactly `rope_bf16_contract.SHAPES` in its order (Q row then K row, each in the order of T);
     - unknown call site (including a GEMM name, an RMSNorm name, an elementwise add name, `ffn_activation` and `rope`), bad rows, bad dimensions, an odd `head_dim` (1, 3, 63) with `parameter` `"dimensions"`, the order of these refusals, argument order.
   - `rope_generation_calls`: prefill and decode, generation length 1, prompt of one row; the row counts match those of `swiglu_generation_calls` while `h` and `d` come from the head fields; odd `head_dim` refused; refused arguments; lengths keyword-only.
   - `check_rope`:
     - ok with an `"every"` binding for both call sites, with listed shapes covering exactly, and with several disjoint entries; `calls` order (`rope_q` before `rope_k`); generation length 1; path sources accepted;
     - a listed shape other than the kernel's spec shape is accepted;
     - a binding listing `rope_k`'s shapes under `rope_q` (Q and K swapped, with `heads` ≠ `kv_heads`) gives `"no_kernel"` for each uncovered shape (ADR-0161 decision 13 leaves "Q and K swapped" to the binding's tests);
     - each `"invalid_input"` case and their order; `fp32` and `fp16` named in the reason with `rope`; no unfit and no `"no_kernel"` for an unknown dtype;
     - `"kernel_unfit"` for a kernel written to the bf16 `swiglu`, `elementwise_add` and `rmsnorm` contracts and to the bf16 and fp32 `gemm` contracts; for a wrong prototype, language, operand name, role or dtype; for `freqs_cis` given dtype `bf16` instead of `fp32`; for the `x` and `freqs_cis` operands swapped; for two operands instead of three; a non-mapping contract; a missing member; wrong operand forms;
     - fit ignores operand shapes and extra members;
     - the reference comes from `rope_bf16_contract.task_contract` (monkeypatched, as the RMSNorm, elementwise add and SwiGLU tests do);
     - `"no_kernel"` for a missing call site and an unlisted shape;
     - argument refusals with their `parameter` and order, including an odd `head_dim`, a GEMM, an RMSNorm, an elementwise add and a SwiGLU call-site key, a pair shape, a four-member shape, an overlap, and an `"every"` beside another entry;
     - arguments not modified.
   - `check_dimensions`, `check_rmsnorm`, `check_elementwise_add` and `check_swiglu` still accept `SMALL` with an odd `head_dim` (a regression guard for criterion 4), and `check`, `check_rmsnorm`, `check_elementwise_add` and `check_swiglu` each refuse a `rope_q` and a `rope_k` binding key.
   - Existing tests are not edited, removed or weakened.
7. **Tests in `tests/test_rope_bf16_contract.py`**: change only the binder test `test_module_imports_keys_only_and_is_named_by_no_other_module` so that `hilclaw/model_binding.py` is the one module allowed to name `rope_bf16_contract` and must name it, in the form of `tests/test_swiglu_bf16_contract.py`'s `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`, and rename it to that name. Its other assertions (imports, `OTHER_MODULE_NAMES` absent from the module's own text, no `__main__`, no `main`) stay. Change nothing else in that file. Do not edit `tests/test_rope_table.py`.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except criterion 7's binder test.
   - Line and function coverage of `hilclaw/` stay >= 80%, and `hilclaw/model_binding.py` stays at 100% line coverage.
   - CI is green.
   - Size: the D4 cap is 300 changed lines outside tests. If exceeded, finish and propose a split in `## Follow-ups`.
9. **No other file changes.** Do not edit `hilclaw/model_gemm.py`, `hilclaw/model_execute.py`, the model program C source, any `hilclaw/*_contract.py`, `hilclaw/rope_table.py`, `hilclaw/keys.py`, any registry or tool module, any test other than the two named above, any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`. In `## Result`, list any record sentence that becomes less exact (for example ADR-0153 decision 3 "future contract records", ADR-0157 decision 4's range, ADR-0161 Consequences' code slice list) without editing it.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0447-<slug>`, Draft PR whose title contains `T-0447` and whose body ends with `Task: T-0447`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: the host side of the executor is Python, ADR-0153 decision 2).
    - The reviewer checks at least:
      - the call-site names and order against ADR-0161 decision 15, and `(m, h, d)` = `(rows, heads, head_dim)` for `rope_q` and `(rows, kv_heads, head_dim)` for `rope_k` against ADR-0161 decisions 2 and 3 and ADR-0152 decision 5;
      - the fit comparison against `rope_bf16_contract.task_contract` (three operands, `freqs_cis` in `fp32`) and the "every shape" acceptance against ADR-0161 decision 11;
      - the invalid-input reason against ADR-0157 decision 4, and that the odd-`head_dim` refusal is confined to the RoPE functions and stated as this module's convention;
      - that `check_dimensions`, `check`, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `rmsnorm_eps` and `hilclaw/model_gemm.py` behave as before;
      - that nothing adds meaning beyond the records (no joined full-pass check, no fp32 rope, no table, no position, no RoPE constant or scale factor, no operand wiring or buffer layout, no in-place allowance, no tolerance, no build or run).

## Out of Scope

- Joining the GEMM, RMSNorm, elementwise add, SwiGLU and RoPE checks into one generation check, and the full pass and generation loop (ADR-0153 code slice 2, after the SDPA with KV cache contract record).
- The RoPE constants as model parameters (a `ModelDimensions` field or a new parameters type), any Llama 3.2 1B value, and the choice of the scale factor (HQ-0070; OD-31 sub-question 5, owner).
- Calling the table builder, slicing rows P … P+T−1, copying the Q and K ranges, the operand wiring of ADR-0161 decision 15; the model program and its build and run steps calling `hilclaw_rope_bf16`; hand-written bf16 RoPE kernel fixtures; any C code.
- The P2-12 harness part of ADR-0161 (generator, draws, the T = 1 row, widening, comparison, tolerance).
- Registering the rope contract with `correctness.check`, `spec.write` or the instance start.
- The SDPA with KV cache contract; fp16; an fp32 contract of this kind.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, ADR-0161's binding part is done. The next piece toward P2-13 and P2-14 is the SDPA with KV cache contract record (doc, OD-31/OD-6), then its code slices; the RoPE constants in the model parameters and the hand-written bf16 RoPE kernel fixtures come with the full pass.

## Result

- **Outcome**: DONE. PR #264 (squash-merged; the merge commit is the one with the trailer `Task: T-0447` on `main`). Review: 2 rounds, Approve (round 1 Approve with two nits and one note; round 2 on the added `## Result`).
- **CI**: green (coverage gate, Python gates 3.11/3.14, test presence, shellcheck); merge commit `3f775dc`.
- **Language**: Python, the host side of the executor is Python (ADR-0153 decision 2).
- **Changes**:
  - `hilclaw/model_binding.py`: `ROPE_CALL_SITES`, `ROPE_DTYPES`, `rope_shape`, `rope_generation_calls`, `check_rope`; the private `_check_rope_dimensions` (an odd `head_dim` refused with `parameter` `"dimensions"`, in the RoPE functions only); `_check_rows` takes `members` (default `("m", "n")`) and `reference_shape` (default `(1, 1)`), RoPE passes `("m", "h", "d")` and `(1, 1, 2)`; `contract.task_contract` is still looked up at call time. Module docstring and the docstrings of `ModelDimensions`, `BindingEntry`, `Outcome`, `BindingCheck`, `check_rmsnorm`, `check_elementwise_add` and `check_swiglu` updated. The text holds no `rope_table`.
  - `tests/test_model_binding.py`: imports and new tests only (no existing line changed): the criterion 6 cases, plus odd-`head_dim` regression guards for `check_dimensions`, `check`, `check_rmsnorm`, `check_elementwise_add` and `check_swiglu`, and the refusal of `rope_q`/`rope_k` keys and of a rope kernel by the other checks.
  - `tests/test_rope_bf16_contract.py`: the binder test renamed to `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only` in the SwiGLU form.
- **Gates**: `ruff check` and `ruff format --check` clean; full `pytest` 29110 passed, 949 skipped; coverage of `hilclaw/` 97% lines, `hilclaw/model_binding.py` 100%. Size outside tests: about 220 changed lines in one file (under the D4 cap).
- **Record sentences now less exact (not edited)**:
  - ADR-0153 decision 3, "future contract records": the rope contract record now exists and is bound by this check.
  - ADR-0157 decision 4: the range of the model's dtype per kind now also covers `rope` (`bf16` only); the decision's text names only the kinds known when it was written.
  - ADR-0161 Consequences, the code slice list: the item "the binding check in `hilclaw/model_binding.py` with `rope_q`, `rope_k` ..." is now done.
  - ADR-0160 Boundaries, "the other two kinds — RoPE and SDPA": only SDPA is now without a binding check (already listed by ADR-0161 as less exact).
- **Follow-ups**: none from this task beyond the planner note above (the SDPA with KV cache contract record next). Reviewer nit kept as is: `check_rope` validates `dimensions` more than once (harmless, same pattern as the other checks).
