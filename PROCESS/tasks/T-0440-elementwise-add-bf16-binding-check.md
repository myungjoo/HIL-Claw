---
id: T-0440
title: Add the elementwise add call sites attention_residual and ffn_residual to hilclaw/model_binding.py - their shapes over a generation and a binding check with fit against the bf16 elementwise add contract and "every shape" accepted (ADR-0159 decisions 8 and 12), with the dtype range of ADR-0157 decision 4 - with tests (ADR-0159 code slice, second part)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0439]
touchesFiles: [hilclaw/model_binding.py, tests/test_model_binding.py, tests/test_elementwise_add_bf16_contract.py]
estimatedSize: {loc: 170, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `e765065`):
- ADR-0159 (T-0438, landed as `278cffc`) defines the bf16 elementwise add contract on `cpu_standin`. T-0439 (PR #258, `03b64cb`) landed part 1 of its code slice:
  - the kind `elementwise_add` (members `m`, `n`) in `hilclaw.keys`;
  - `hilclaw/elementwise_add_bf16_contract.py` (`KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES`, `INPUT_PATTERNS`, `op_signature_record`, `task_contract`, `covers`).
- ADR-0159 Consequences (line 185) name the next part: "the binding check in `hilclaw/model_binding.py` with the call sites `attention_residual` and `ffn_residual` of decision 12, their shapes (rows × hidden) and the 'every shape' binding, `bf16` as the only dtype at which the kind is known". T-0439's planner follow-up names it as the next step.
- Today `hilclaw/model_binding.py` checks the six GEMM call sites (`check`) and, separately, the three RMSNorm call sites (`check_rmsnorm`, T-0437). Its docstring says it "knows no call site of RoPE, SDPA, SwiGLU or elementwise add".

**What the accepted records already settle** (so this task invents nothing):
- The call sites are ADR-0152 decision 2 rows 9 ("Residual add after attention") and 14 ("Residual add after the feed-forward"), named `attention_residual` and `ffn_residual`, in that order (ADR-0159 decision 12).
- Each call adds two T × hidden inputs into a T × hidden output: `m` = T (the rows of the pass), `n` = hidden (ADR-0152 decisions 2 and 5; ADR-0159 decision 2).
- Fit: compare the bound kernel's `task.contract` with the contract of the call site's kind and dtype on `language`, `prototype` and each operand's `name`, `role`, `dtype` (ADR-0153 decision 3; the comparison `check_rmsnorm` already makes).
- A binding "for every shape", and a listed shape other than the spec's own, are accepted for this contract (ADR-0159 decision 8, "Every set of dimensions"; ADR-0153 decision 3).
- The dtype: a dtype at which the kind of a call site has no contract is invalid input, and the outcome names the dtype and the kind (ADR-0157 decision 4). Only `bf16` has an elementwise add contract (ADR-0159 decision 1: "No fp32 or fp16 contract of this kind is defined").
- The contract has no scalar parameter, so there is no counterpart of `rmsnorm_eps`.

**So this task adds an elementwise add binding check beside `check` and `check_rmsnorm`, not inside them**, exactly as T-0437 did for RMSNorm. Joining the checks of every kind into one generation check belongs to the full pass (ADR-0153 code slice 2), which needs the three remaining contract records (SwiGLU activation, RoPE, SDPA with KV cache). Which buffer each call passes as `a`, `b` and `c` (ADR-0159 decision 12's operand table, decision 8's two alternating buffers) is also the full pass's, not a binding check's. If the executor or reviewer reads ADR-0153, ADR-0157 or ADR-0159 as requiring something else, stop and return BLOCKED (`requirement-unclear`) and name the sentence.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json`:
- round 0's board step waits on HQ-0021;
- the round >= 1 steps and P2-6/P2-7 wait on HQ-0048 and HQ-0031;
- the gate half of P2-4 is owner-only (OD-3).

P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is code that P2-13 and P2-14 need: the forward pass cannot bind a residual add kernel without it, and ADR-0159 Consequences list it as part of the record's code slice. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, A-13 and D16.** No open decision is needed; every rule comes from ADR-0152, ADR-0153, ADR-0157 and ADR-0159 as accepted. Nothing in the data plane changes (`model_binding` reads and writes no file). Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0440-<slug>`, PR title with `T-0440`, commit trailer `Task: T-0440`, last line of the PR body `Task: T-0440`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md` decision 2 (the table, lines 41-66; rows 9 and 14) and decision 5 (lines 84-104).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` decision 3 (lines 40-46) and decision 5 (lines 58-62).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md` decision 4 (lines 66-71) and decision 5 (lines 73-78).
- `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`: decision 1 (lines 33-36), decision 2 (lines 38-42), decision 7 (lines 78-100), decision 8 (lines 102-116), decision 12 (lines 148-158), Consequences (lines 182-189).
- `hilclaw/model_binding.py`, the whole file (685 lines). This is the file you change. In particular `check_rmsnorm` (lines 362-441), `rmsnorm_shape` and `rmsnorm_generation_calls` (lines 322-359), and the private helpers `_bind`, `_no_contract`, `_unfit`, `_binding`, `_entry`, `_no_overlap`, `_lengths`, `_pass_rows`, `_integer`, `_parameter` (from line 471).
- `hilclaw/elementwise_add_bf16_contract.py`, the whole file. Read only; do not edit.
- `hilclaw/model_gemm.py` lines 1-60 and its call of `model_binding.check`: the existing caller, which must not change behaviour.
- `tests/test_model_binding.py`: lines 1-82 (imports and helpers), line 162 and line 632 (`"rmsnorm"` used as an unknown call site and binding key), line 850 (`test_check_refuses_an_rmsnorm_call_site_key_and_a_pair_shape`), and the RMSNorm tests from line 859 to the end of the RMSNorm part (helpers `norm_kernel`, `norm_binding`, `run_norm`, `expected_norm_calls`, `norm_unfit_reason`, `good_norm_contract`, `bad_norm_binding`, `with_norm_entry`). They are the model for the new tests.
- `tests/test_elementwise_add_bf16_contract.py` lines 485-532 (public names, `test_module_imports_keys_only_and_is_named_by_no_other_module`, no-file test) and, as the model for the new form of the binder test, `tests/test_rmsnorm_bf16_contract.py` lines 488-502 (`test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`).

## Acceptance Criteria

1. **New public names in `hilclaw/model_binding.py`** (Python; no new import other than `hilclaw.elementwise_add_bf16_contract`):
   - `ELEMENTWISE_ADD_CALL_SITES = ("attention_residual", "ffn_residual")`: ADR-0152 decision 2 rows 9 and 14, named and ordered as ADR-0159 decision 12.
   - `ELEMENTWISE_ADD_DTYPES = (elementwise_add_bf16_contract.DTYPE,)`: the dtypes at which the `elementwise_add` contract is known (ADR-0157 decision 4, ADR-0159 decision 1).
   - `elementwise_add_shape(dimensions, call_site, rows)`: returns `(rows, dimensions.hidden)`, the `(m, n)` of ADR-0159 decision 2. It raises as `rmsnorm_shape` does: first as `check_dimensions`, then `ValueError` with `parameter` `"call_site"` for a call site not in `ELEMENTWISE_ADD_CALL_SITES`, then `TypeError`/`ValueError` with `parameter` `"rows"` for `rows` that is not an `int` from 1 to 2**53 - 1.
   - `elementwise_add_generation_calls(dimensions, *, prompt_length, generation_length)`: per call site in `ELEMENTWISE_ADD_CALL_SITES` order, the sorted tuple of distinct shapes of a generation, as `(call_site, shapes)` pairs. It uses the same passes as `generation_calls` and `rmsnorm_generation_calls` (one prefill of `prompt_length` rows, then `generation_length - 1` decode passes of one row) and raises like `rmsnorm_generation_calls`.
   - `check_elementwise_add(dimensions, binding, *, dtype, prompt_length, generation_length)`: returns a `BindingCheck`. Details in criterion 2.
   - Nothing else public is added. There is no `eps`-like function: the contract has no scalar parameter.
2. **`check_elementwise_add`** behaves as `check_rmsnorm`, with this kind's call sites, dtypes and contract:
   - **Arguments refused first**, in the order `dimensions`, `dtype`, `prompt_length`, `generation_length`, `binding`, each error carrying `parameter` = the argument's name, with the same types and messages as `check_rmsnorm`. `binding` keys must be in `ELEMENTWISE_ADD_CALL_SITES`: a GEMM or RMSNorm call-site key is refused. Entries, kernel references, the `"every"` rule and the overlap rule are those of `check_rmsnorm`, with `(m, n)` pairs as shapes; a triple is refused.
   - **Outcomes**, in this order:
     1. `"invalid_input"` (`call_site` and `shape` `None`): a `dtype` not in `ELEMENTWISE_ADD_DTYPES`, with the reason `dtype: no elementwise_add contract is known at the dtype '<dtype>'` (ADR-0157 decision 4; the existing `_no_contract` form); then `prompt_length` outside 1 to 2**53 - 1; then `generation_length` outside 1 to 2**53 - 1.
     2. Per call site in `ELEMENTWISE_ADD_CALL_SITES` order: `"kernel_unfit"` for each entry whose `contract` is not the bf16 elementwise add contract, compared on `language`, `prototype` and the operands' `(name, role, dtype)`, with reference values taken from `elementwise_add_bf16_contract.task_contract` at call time, never from the entry's own contract (operand shapes and extra members ignored); the label in the reason is `bf16 elementwise_add`. Then `"no_kernel"` for each shape of `elementwise_add_generation_calls` that no entry covers.
     - As in `check_rmsnorm`: no `"no_kernel"` outcome is looked for when there is an `"invalid_input"`, and no per-call-site outcome at all when `dtype` is not in `ELEMENTWISE_ADD_DTYPES`.
   - A listed shape other than the kernel's own spec shape, and an `"every"` entry, are accepted (ADR-0159 decision 8).
   - `calls` holds `(call_site, shape, kernel)` for every call of `elementwise_add_generation_calls`, in its order, only when `ok`.
   - Arguments are not modified. Nothing is built, started or read. The operand wiring of ADR-0159 decision 12 is not checked here.
3. **The GEMM and RMSNorm sides do not change behaviour.**
   - `check`, `gemm_shape`, `generation_calls`, `CALL_SITES`, `DTYPES`, `check_rmsnorm`, `rmsnorm_shape`, `rmsnorm_generation_calls`, `rmsnorm_eps`, `RMSNORM_CALL_SITES`, `RMSNORM_DTYPES` and every existing message stay as they are. `hilclaw/model_gemm.py` is not edited.
   - You may factor the shared body of `check_rmsnorm` and `check_elementwise_add` into a private helper (call sites, dtypes, contract module, generation-calls function), as long as every existing test in `tests/test_model_binding.py` passes unchanged. In particular `test_check_rmsnorm_reference_comes_from_the_contract_module` (it monkeypatches `rmsnorm_bf16_contract.task_contract`) must keep its effect, and the new check's reference must be looked up from `elementwise_add_bf16_contract.task_contract` at call time in the same way.
4. **Docstrings.**
   - Rewrite the module docstring: the module now also checks the two elementwise add call sites against the bf16 elementwise add contract (ADR-0159). It knows no call site of RoPE, SDPA or SwiGLU. It does not join the GEMM, RMSNorm and elementwise add checks into one generation check (the full pass, ADR-0153 code slice 2), and it does not check which buffers a call passes. It keeps the other "does not do" points. Its "Readings" bullet on listed shapes and `"every"` names the elementwise add contract too (ADR-0159 decision 8).
   - Update the docstrings that name the kinds or checks: `ModelDimensions`, `BindingEntry` (a shape is `(m, n)` for an RMSNorm or elementwise add call site), `Outcome` and `BindingCheck`.
   - Each new public name has a Doxygen-like docstring in the module's style. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests in `tests/test_model_binding.py`** (D12: happy, error, branch and negative cases, every new public name). At least:
   - `ELEMENTWISE_ADD_CALL_SITES` and `ELEMENTWISE_ADD_DTYPES` values.
   - `elementwise_add_shape`: small values; at hidden width 2048 with T in {1, 32, 512}, the `(m, n)` of `elementwise_add_bf16_contract.SHAPES`; unknown call site (including a GEMM and an RMSNorm call-site name), bad rows, bad dimensions, argument order.
   - `elementwise_add_generation_calls`: prefill and decode, generation length 1, prompt of one row; rows match those of `rmsnorm_generation_calls`; refused arguments; lengths keyword-only.
   - `check_elementwise_add`:
     - ok with an `"every"` binding, with listed shapes covering exactly, and with several disjoint entries; `calls` order; generation length 1; path sources accepted;
     - a listed shape other than the kernel's spec shape is accepted;
     - each `"invalid_input"` case and their order; `fp32` and `fp16` named in the reason with `elementwise_add`; no unfit and no `"no_kernel"` for an unknown dtype;
     - `"kernel_unfit"` for a kernel written to the bf16 `rmsnorm` contract, to the bf16 `gemm` contract and to the fp32 `gemm` contract; for a wrong prototype, language, operand name, role or dtype; a non-mapping contract; a missing member; wrong operand forms;
     - fit ignores operand shapes and extra members;
     - the reference comes from `elementwise_add_bf16_contract.task_contract` (monkeypatched, as the RMSNorm test does);
     - `"no_kernel"` for a missing call site and an unlisted shape;
     - argument refusals with their `parameter` and order, including a GEMM and an RMSNorm call-site key, a triple shape, an overlap, and an `"every"` beside another entry;
     - arguments not modified.
   - `check` and `check_rmsnorm` each refuse an `attention_residual` binding key.
   - Existing tests are not edited, removed or weakened.
6. **Tests in `tests/test_elementwise_add_bf16_contract.py`**: change only the binder test `test_module_imports_keys_only_and_is_named_by_no_other_module` (line 507) so that `hilclaw/model_binding.py` is the one module allowed to name `elementwise_add_bf16_contract` and must name it, in the form of `tests/test_rmsnorm_bf16_contract.py`'s `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`. Rename it to `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`. Its other assertions (imports, `OTHER_MODULE_NAMES` absent from the module's own text, no `__main__`, no `main`) stay. Change nothing else in that file.
7. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except criterion 6's binder test.
   - Line and function coverage of `hilclaw/` stay >= 80%, and `hilclaw/model_binding.py` stays at 100% line coverage.
   - CI is green.
   - Size: the D4 cap is 300 changed lines outside tests. If the change to `hilclaw/model_binding.py` would exceed it, prefer the shared private helper of criterion 3 over duplicating `check_rmsnorm`; if it still exceeds, finish and propose a split in `## Follow-ups`.
8. **No other file changes.** Do not edit `hilclaw/model_gemm.py`, `hilclaw/model_execute.py`, the model program C source, `hilclaw/elementwise_add_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/keys.py`, any registry or tool module, any test other than the two named above, any `ARCHITECTURE/` or `PROCESS/` file. In `## Result`, list any record sentence that becomes less exact (for example ADR-0153 decision 3 "future contract records", ADR-0157 decision 4's range "with the GEMM call sites only", ADR-0159 Consequences) without editing it.
9. **Process**: code mode (CLAUDE.md A-13).
   - Branch `claude/T-0440-<slug>`, Draft PR whose title contains `T-0440` and whose body ends with `Task: T-0440`.
   - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
   - The commit body has one line on the language choice (Python: the host side of the executor is Python, ADR-0153 decision 2).
   - The reviewer checks at least:
     - the call-site names and order against ADR-0159 decision 12 and ADR-0152 decision 2 rows 9 and 14, and `(m, n)` = `(rows, hidden)` against ADR-0159 decision 2;
     - the fit comparison against `elementwise_add_bf16_contract.task_contract` and the "every shape" acceptance against ADR-0159 decision 8;
     - the invalid-input reason against ADR-0157 decision 4;
     - that `check`, `check_rmsnorm`, `rmsnorm_eps` and `hilclaw/model_gemm.py` behave as before;
     - that nothing adds meaning beyond the records (no joined full-pass check, no fp32 elementwise add, no operand wiring or buffer layout, no in-place allowance, no tolerance, no build or run).

## Out of Scope

- Joining the GEMM, RMSNorm and elementwise add checks into one generation check, and the full pass and generation loop (ADR-0153 code slice 2, after the contract records of SwiGLU activation, RoPE and SDPA with KV cache).
- The operand wiring of ADR-0159 decision 12 and the two alternating residual buffers of decision 8; the model program and its build and run steps calling `hilclaw_elementwise_add_bf16`; hand-written bf16 elementwise add kernel fixtures; any C code.
- The P2-12 harness part of ADR-0159 (generator over the value set, widening, comparison, tolerance).
- Registering the elementwise add contract with `correctness.check`, `spec.write` or the instance start.
- The contracts of SwiGLU activation, RoPE and SDPA with KV cache; fp16; an fp32 contract of this kind.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task, ADR-0159's binding part is done. The next pieces toward P2-13 and P2-14 are the contract record (doc, OD-31/OD-6) of the SwiGLU activation kind, then its code slices, then RoPE and SDPA with KV cache (ADR-0159 Boundaries). The hand-written bf16 RMSNorm and elementwise add kernel fixtures come with the model program's calls of those kinds.

## Result
