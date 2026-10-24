---
id: T-0450
title: Add the SDPA call site sdpa to hilclaw/model_binding.py - its (m, l, h, h_kv, d) shapes over a generation (prefill (P, P), decode pass k (1, P + k)) and a binding check with fit against the bf16 sdpa_kv_cache contract and "every shape" accepted (ADR-0162 decisions 3, 10, 11 and 15), with the dtype range of ADR-0157 decision 4 - with tests (ADR-0162 code slice, second part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0449]
touchesFiles: [hilclaw/model_binding.py, tests/test_model_binding.py, tests/test_sdpa_kv_cache_bf16_contract.py]
estimatedSize: {loc: 180, files: 1}
hq: []
---
## Why

**State on `main` `433b8d5`.**
- ADR-0162 (T-0448, `632f02a`) defines the bf16 SDPA with KV cache contract on `cpu_standin`. T-0449 (PR #265, `6756d8c`) landed its first code part: the kind `sdpa_kv_cache` (members `m`, `l`, `h`, `h_kv`, `d`) in `hilclaw.keys` and `hilclaw/sdpa_kv_cache_bf16_contract.py` (`KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES`, `INPUT_PATTERNS`, `op_signature_record`, `task_contract(m, l, h, h_kv, d)`, `covers`).
- ADR-0162 Consequences (line 216) name the second part: "the binding check in `hilclaw/model_binding.py` with the call site `sdpa`, its (m, l) shapes from (T, P, L) and the 'every shape' binding, `bf16` only". T-0449's planner follow-up names it as the next step.
- `hilclaw/model_binding.py` checks the GEMM call sites (`check`) and, separately, RMSNorm, elementwise add, SwiGLU and RoPE (`check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope`; T-0437, T-0440, T-0443, T-0447). The row-wise checks share `_check_rows` (parameterised by T-0447 with `members` and `reference_shape`), `_bind` and `_binding`. Its module docstring says it "knows no call site of SDPA".

**What the accepted records already settle** (so this task invents no rule):
- One kind for prefill and decode; one call site **`sdpa`**, one call per layer (ADR-0162 decisions 2 and 15).
- Shape `(m, l, h, h_kv, d)` = (T, L, `heads`, `kv_heads`, `head_dim`) (decision 3; ADR-0154 decision 1's SDPA row as cited in ADR-0162 Context).
- **Over a generation the shapes are the prefill `(m, l)` = (prompt length, prompt length) and, for decode pass k, `(1, prompt length + k)`** (decision 15, last bullet; passes as ADR-0153 decision 4). **This is the first kind whose shape differs between decode passes**: a generation of length G has G distinct `sdpa` shapes (k = 1 … G − 1 plus the prefill), not at most two.
- Fit: compare on `language`, `prototype` and each operand's `name`, `role`, `dtype` (ADR-0153 decision 3, `_unfit`). The contract has six operands, two of role `inout` (decision 10).
- A binding "for every shape", and a listed shape other than the spec's own, are accepted (decision 11, "Every set of dimensions").
- Only `bf16` has an `sdpa_kv_cache` contract (decision 1); another dtype is invalid input naming the dtype and the kind (ADR-0157 decision 4).
- The caller's dimension guarantees (decision 11: m ≥ 1, l ≥ m, h a multiple of h_kv, d ≥ 1) always hold for the shapes of a generation once `check_dimensions` has passed (`heads` a multiple of `kv_heads` is already its rule). So, unlike RoPE, no extra refusal of model dimensions is needed.

**One reading this task makes, as a code choice** (state it in the docstring and the commit body; the reviewer checks it): the largest `l` of a generation is `prompt_length + generation_length - 1`. A shape member above `keys.MAX_INTEGER` cannot be a key value (ADR-0001), so a generation whose largest `l` exceeds 2**53 - 1 is refused as a run setting outside its range — the `"invalid_input"` of ADR-0153 decision 5 — in the SDPA functions only. If the executor or reviewer reads ADR-0153, ADR-0157 or ADR-0162 as requiring something else, or finds that this needs a record, stop and return BLOCKED (`requirement-unclear`) and name the sentence.

**So this task adds an SDPA binding check beside the other five checks, not inside them**, exactly as T-0447 did for RoPE. Joining the checks into one generation check is the full pass (ADR-0153 code slice 2). The cache buffers, their capacity, the V copy and the operand wiring of decision 15's table are the model program's slice, not a binding check's.

**PLAN order and D18.** PLAN P2 runs in list order. Unresolved HQs in `PROCESS/STATE.json` still hold the round-loop items and P2-5 (HQ-0021: round 0's board step; HQ-0048 and HQ-0024: the round >= 1 steps, P2-6 and P2-7; the gate half of P2-4 is owner-only, OD-3), and P2-10 comes after P2-5. So work goes on with P2-11 to P2-14. This task is code P2-13 and P2-14 need — the forward pass cannot bind an SDPA kernel without it — and ADR-0162 Consequences list it. It is not a follow-up, wording or hardening item; the D18 rule does not set it aside.

**§9, open HQs, A-13 and D16.** No open decision is needed; every rule comes from ADR-0153, ADR-0157 and ADR-0162 as accepted (ADR-0162 owner notice #5 issuecomment-6386983591, 7-day window). No capacity value is chosen or checked (OD-31 sub-question 6, owner). HQ-0033, HQ-0034, HQ-0069 and HQ-0070 are not touched: no build setting, thread, runtime fact or RoPE constant enters a binding check. `model_binding` reads and writes no file, so nothing in the data plane changes. Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task format; naming (branch `claude/T-0450-<slug>`, PR title with `T-0450`, commit trailer `Task: T-0450`, last line of the PR body `Task: T-0450`); size cap; test rules.
- `CLAUDE.md`, "상시 규칙": especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (lines 40-46), decision 4 (lines 48-56), decision 5 (lines 58-62).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 4 (lines 66-71) and decision 5 (lines 73-77).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`: decisions 1 to 3 (lines 37-50), decision 4's "Capacity" bullet (line 56), decision 10 (lines 103-131), decision 11 (lines 133-147), decision 15 (lines 177-189), Consequences (lines 212-220).
- `hilclaw/model_binding.py`, the whole file (1075 lines). This is the file you change. In particular the module docstring (lines 1-84), the constants (lines 121-162), `ModelDimensions`, `BindingEntry`, `Outcome`, `BindingCheck` (lines 165-215), `check_dimensions` (lines 218-241), the RoPE functions `rope_shape`, `rope_generation_calls`, `check_rope` (lines 649-747), and the private helpers `_row_shape`, `_row_generation_calls`, `_check_rows`, `_bind`, `_no_contract`, `_unfit`, `_binding`, `_entry`, `_no_overlap`, `_lengths`, `_pass_rows`, `_integer`, `_parameter` (from line 777).
- `hilclaw/sdpa_kv_cache_bf16_contract.py`, the whole file. Read only; do not edit.
- `tests/test_model_binding.py`: lines 1-98 (imports, `SMALL`, helpers) and the RoPE tests from line 2996 to the end of the file (helpers `rope_shapes`, `rope_binding`, `rope_kernel`, `run_rope`, `expected_rope_calls`; `test_other_checks_refuse_a_rope_kernel` at line 3912). They are the model for the new tests.
- `tests/test_sdpa_kv_cache_bf16_contract.py` lines 95-110 (`OTHER_CONTRACTS`, `OTHER_MODULE_NAMES`) and lines 664-675 (`test_module_imports_keys_only_and_is_named_by_no_other_module`), and, as the model for its new form, `tests/test_rope_bf16_contract.py` line 588 (`test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`).
- `PROCESS/tasks/T-0447-rope-bf16-binding-check.md`, `## Result` (how `_check_rows` was parameterised).

## Acceptance Criteria

1. **New public names in `hilclaw/model_binding.py`** (Python; no new import other than `hilclaw.sdpa_kv_cache_bf16_contract`):
   - `SDPA_CALL_SITES = ("sdpa",)` (ADR-0162 decision 15).
   - `SDPA_DTYPES = (sdpa_kv_cache_bf16_contract.DTYPE,)` (ADR-0157 decision 4, ADR-0162 decision 1).
   - `sdpa_shape(dimensions, call_site, rows, positions)`: returns `(rows, positions, dimensions.heads, dimensions.kv_heads, dimensions.head_dim)`, the `(m, l, h, h_kv, d)` of ADR-0162 decision 3. It raises, in this order: as `check_dimensions` does; `ValueError` with `parameter` `"call_site"` for a call site not in `SDPA_CALL_SITES`; `TypeError`/`ValueError` with `parameter` `"rows"` for `rows` that is not an `int` from 1 to 2**53 - 1; the same with `parameter` `"positions"` for `positions`; then `ValueError` with `parameter` `"positions"` when `positions < rows` (decision 11, l ≥ m). The argument name `positions` is a code choice.
   - `sdpa_generation_calls(dimensions, *, prompt_length, generation_length)`: `(("sdpa", shapes),)` with `shapes` the sorted tuple of the distinct shapes of a generation: `sdpa_shape(dimensions, "sdpa", prompt_length, prompt_length)` and, for k = 1 … `generation_length` - 1, `sdpa_shape(dimensions, "sdpa", 1, prompt_length + k)` (decision 15). It raises as `check_dimensions`, then as `rope_generation_calls` does for the lengths, then `ValueError` with `parameter` `"generation_length"` when `prompt_length + generation_length - 1 > keys.MAX_INTEGER` (the reading in Why), before building any shape.
   - `check_sdpa(dimensions, binding, *, dtype, prompt_length, generation_length)`: returns a `BindingCheck`. Details in criterion 2.
   - Nothing else public is added.
2. **`check_sdpa`** behaves as `check_rope`, with this kind's call site, dtype, contract and five-member shapes:
   - **Arguments refused first**, in the order `dimensions`, `dtype`, `prompt_length`, `generation_length`, `binding`, each error carrying `parameter` = the argument's name, with the same types and messages as `check_rope` (no odd-`head_dim` refusal: an odd `head_dim` is accepted). `binding` keys must be in `SDPA_CALL_SITES`: a GEMM, RMSNorm, elementwise add, SwiGLU or RoPE call-site key is refused. Entries, kernel references, the `"every"` rule and the overlap rule are those of `check_rope`, with `(m, l, h, h_kv, d)` 5-tuples as shapes; a triple is refused, and the type error for a non-tuple shape names `(m, l, h, h_kv, d)`.
   - **Outcomes**, in this order:
     1. `"invalid_input"` (`call_site` and `shape` `None`): a `dtype` not in `SDPA_DTYPES`, with the reason `dtype: no sdpa_kv_cache contract is known at the dtype '<dtype>'` (the existing `_no_contract` form); then `prompt_length`, then `generation_length` outside 1 to 2**53 - 1; then, only when both lengths are in range, `prompt_length + generation_length - 1` above 2**53 - 1, with a reason that names both lengths and the bound.
     2. For the call site `sdpa`: `"kernel_unfit"` for each entry whose `contract` is not the bf16 `sdpa_kv_cache` contract, compared on `language`, `prototype` and the operands' `(name, role, dtype)`, with reference values taken from `sdpa_kv_cache_bf16_contract.task_contract` at call time (for example `task_contract(1, 1, 1, 1, 1)`), never from the entry's own contract (operand shapes and extra members ignored); the label in the reason is `bf16 sdpa_kv_cache`. Then `"no_kernel"` for each shape of `sdpa_generation_calls` that no entry covers, in its order.
     - As in `check_rope`: no `"no_kernel"` outcome is looked for when there is an `"invalid_input"`, and no per-call-site outcome at all when `dtype` is not in `SDPA_DTYPES`.
   - A listed shape other than the kernel's own spec shape, and an `"every"` entry, are accepted (decision 11).
   - `calls` holds `("sdpa", shape, kernel)` for every shape of `sdpa_generation_calls`, in its order, only when `ok`.
   - Arguments are not modified. Nothing is built, started or read. The operand wiring of decision 15's table, the cache buffers, their capacity and the V copy are not checked here.
3. **Reuse the shared helpers; do not duplicate `_check_rows`, `_bind` or `_binding`.**
   - Pass `members=("m", "l", "h", "h_kv", "d")` (a private constant beside `_ROPE_SHAPE`) and a reference shape such as `(1, 1, 1, 1, 1)` to `_check_rows`.
   - The overlong-generation `"invalid_input"` needs a hook `_check_rows` does not have today. Add the smallest one (for example an optional argument giving extra invalid-input reasons, computed after the two length reasons). RMSNorm, elementwise add, SwiGLU and RoPE pass nothing new and behave as before.
   - The lookup of `contract.task_contract` stays at call time, so monkeypatching `sdpa_kv_cache_bf16_contract.task_contract` changes the reference.
   - `sdpa_generation_calls` may reuse `_lengths` and `_integer`; it does not go through `_row_shape`, `_row_generation_calls` or `_pass_rows` (its decode shapes differ per pass).
4. **The other sides do not change behaviour.** `check_dimensions`, `check`, `gemm_shape`, `generation_calls`, `CALL_SITES`, `DTYPES`, every `rmsnorm_*`, `elementwise_add_*`, `swiglu_*` and `rope_*` name, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope`, `rmsnorm_eps` and every existing message stay as they are. Every existing test in `tests/test_model_binding.py` passes unchanged. `hilclaw/model_gemm.py` is not edited.
5. **Docstrings.**
   - Rewrite the module docstring (first line included): the module now also checks the SDPA call site against the bf16 `sdpa_kv_cache` contract (ADR-0162), whose shape is `(m, l, h, h_kv, d)`, with one prefill shape and one decode shape per further token, so a generation of length G has G `sdpa` shapes; state the overlong-generation refusal as this module's reading. Drop "knows no call site of SDPA". Keep the other "does not do" points, extended: it does not join the six checks into one generation check (the full pass, ADR-0153 code slice 2); it does not check which arrays a call passes (add ADR-0162 decision 15); it allocates, sizes and checks no KV cache buffer and knows no capacity (ADR-0162 decision 4; OD-31 sub-question 6); it makes no V copy. The "Readings" bullet on listed shapes and `"every"` names the `sdpa_kv_cache` contract too (ADR-0162 decision 11), with the right count of contracts.
   - Update the docstrings that name the kinds or checks: `ModelDimensions`, `BindingEntry` (a shape is `(m, l, h, h_kv, d)` for the SDPA call site), `Outcome`, `BindingCheck`, and those of `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope` or others that say a check "stands beside" the existing ones.
   - Each new public name has a Doxygen-like docstring in the module's style. Other comments follow CLAUDE.md "코멘트 최소화".
6. **Tests in `tests/test_model_binding.py`** (D12: happy, error, branch and negative cases, every new public name). Keep every generation length small in the SDPA tests (the result has one shape per pass); a length near 2**53 appears only in refusal cases. At least:
   - `SDPA_CALL_SITES` and `SDPA_DTYPES` values.
   - `sdpa_shape`:
     - with `SMALL`, `(rows, positions, 4, 2, 2)`; with dimensions whose `heads`, `kv_heads` and `head_dim` differ from `SMALL`'s, each member follows its own field; an odd `head_dim` is accepted;
     - at hidden 2048, intermediate 8192, heads 32, kv_heads 8, head_dim 64, the four `(m, l)` of ADR-0162 decision 14 — (128, 128), (1, 128), (2048, 2048), (1, 2048) — give exactly `sdpa_kv_cache_bf16_contract.SHAPES` in its order;
     - `positions == rows` accepted; `positions < rows` refused with `parameter` `"positions"`;
     - unknown call site (including a GEMM, RMSNorm, elementwise add, SwiGLU and RoPE name and `sdpa_kv_cache`), bad rows, bad positions (`bool`, `float`, 0, negative, `MAX_INTEGER + 1`), bad dimensions, the order of these refusals, argument order.
   - `sdpa_generation_calls`:
     - prompt 3, generation 4 gives `(1, 4, …)`, `(1, 5, …)`, `(1, 6, …)`, `(3, 3, …)` in sorted order; generation length 1 gives the prefill only; a prompt of one row (prefill `(1, 1, …)` and decode `(1, 2, …)`, …);
     - at Llama dimensions, prompt 127 with generation 2 gives `(1, 128, 32, 8, 64)` and `(127, 127, 32, 8, 64)`;
     - `prompt_length + generation_length - 1` equal to `MAX_INTEGER` is not refused by the length check (test it through `check_sdpa`'s `"invalid_input"` ordering or another way that builds no huge tuple, for example by monkeypatching `keys.MAX_INTEGER` or by asserting the refusal at `MAX_INTEGER + 1` with `prompt_length = MAX_INTEGER`, `generation_length = 2`);
     - refused arguments with their `parameter`; lengths keyword-only.
   - `check_sdpa`:
     - ok with an `"every"` binding; with listed shapes covering exactly; with several disjoint entries (for example the prefill shape in one entry and the decode shapes in another); `calls` order; generation length 1; path sources accepted;
     - a listed shape other than the kernel's spec shape is accepted;
     - a binding listing only the decode shapes gives one `"no_kernel"` for the prefill shape, and one listing only the prefill shape gives one `"no_kernel"` per decode shape;
     - each `"invalid_input"` case and their order, including the overlong generation (`prompt_length = MAX_INTEGER`, `generation_length = 2`) and its absence when a length is itself out of range; `fp32` and `fp16` named in the reason with `sdpa_kv_cache`; no unfit and no `"no_kernel"` for an unknown dtype;
     - `"kernel_unfit"` for a kernel written to the bf16 `rope`, `swiglu`, `elementwise_add` and `rmsnorm` contracts and to the bf16 and fp32 `gemm` contracts; for a wrong prototype, language, operand name, role or dtype; for `cache_k` given role `input` or `output` instead of `inout`; for `k_new` and `v_new` swapped; for five operands instead of six; a non-mapping contract; a missing member; wrong operand forms;
     - fit ignores operand shapes (for example a capacity shape `[256, 8, 64]` for a cache) and extra members;
     - the reference comes from `sdpa_kv_cache_bf16_contract.task_contract` (monkeypatched, as the RoPE tests do);
     - `"no_kernel"` for a missing call site and an unlisted shape;
     - argument refusals with their `parameter` and order, including a GEMM, an RMSNorm, an elementwise add, a SwiGLU and a RoPE call-site key, a triple shape, a four-member shape, an overlap, and an `"every"` beside another entry;
     - arguments not modified.
   - `check`, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu` and `check_rope` each refuse an `sdpa` binding key, and the row-wise checks report `"kernel_unfit"` for an SDPA kernel (as `test_other_checks_refuse_a_rope_kernel` does).
   - Existing tests are not edited, removed or weakened.
7. **Tests in `tests/test_sdpa_kv_cache_bf16_contract.py`**: change only `test_module_imports_keys_only_and_is_named_by_no_other_module` so that `hilclaw/model_binding.py` is the one module allowed to name `sdpa_kv_cache_bf16_contract` and must name it, in the form of `tests/test_rope_bf16_contract.py`'s `test_module_imports_keys_only_and_is_bound_by_the_model_binding_only`, and rename it to that name. Its other assertions (imports, `OTHER_MODULE_NAMES` absent from the module's own text, no `__main__`, no `main`) stay. Change nothing else in that file.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except criterion 7's binder test.
   - Line and function coverage of `hilclaw/` stay >= 80%, and `hilclaw/model_binding.py` stays at 100% line coverage.
   - CI is green.
   - Size: the D4 cap is 300 changed lines outside tests. If exceeded, finish and propose a split in `## Follow-ups`.
9. **No other file changes.** Do not edit `hilclaw/model_gemm.py`, `hilclaw/model_execute.py`, `hilclaw/model_run.py`, `hilclaw/model_program.c`, any `hilclaw/*_contract.py`, `hilclaw/keys.py`, `hilclaw/rope_table.py`, any registry or tool module, any test other than the two named above, any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`. In `## Result`, list any record sentence that becomes less exact (for example ADR-0153 decision 3 "future contract records", ADR-0157 decision 4's range, ADR-0162 Consequences' code slice list) without editing it.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0450-<slug>`, Draft PR whose title contains `T-0450` and whose body ends with `Task: T-0450`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: the host side of the executor is Python, ADR-0153 decision 2) and one line on the overlong-generation reading.
    - The reviewer checks at least:
      - the call-site name against ADR-0162 decision 15, and `(m, l, h, h_kv, d)` = `(rows, positions, heads, kv_heads, head_dim)` against decision 3;
      - the generation shapes (prefill `(P, P)`, decode pass k `(1, P + k)`) against decision 15 and ADR-0153 decision 4;
      - the fit comparison against `sdpa_kv_cache_bf16_contract.task_contract` (six operands, `inout` caches) and the "every shape" acceptance against decision 11;
      - the invalid-input reason against ADR-0157 decision 4, and that the overlong-generation refusal is confined to the SDPA functions, stated as this module's reading, and adds no capacity or longest-sequence value;
      - that `check_dimensions`, `check`, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope`, `rmsnorm_eps` and `hilclaw/model_gemm.py` behave as before;
      - that nothing adds meaning beyond the records (no joined full-pass check, no fp32 SDPA, no cache buffer, capacity or V copy, no scale, no operand wiring, no tolerance, no build or run).

## Out of Scope

- Joining the six checks into one generation check, and the full pass and generation loop (ADR-0153 code slice 2).
- The model program's two cache buffers per layer, their capacity, the V copy and the build and run steps calling `hilclaw_sdpa_kv_cache_bf16` (ADR-0153 decision 4, ADR-0162 decisions 4, 5 and 15); hand-written bf16 SDPA kernel fixtures; any C code.
- The capacity value and the longest sequence (OD-31 sub-question 6, owner).
- The P2-12 harness part of ADR-0162 (generator, draws, cache rows P … l − 1, guard rows, cache comparison, widening, tolerance).
- Registering the contract with `correctness.check`, `spec.write` or the instance start.
- fp16; an fp32 contract of this kind; build settings and OpenMP (HQ-0033; the HQ-0034 follow-up in PLAN "보류").
- Any edit to an ADR, Requirements, OpenDecisionProposals or StandardScenarios.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this task every kind of ADR-0152 decision 2 has a binding check. The next steps toward P2-13 and P2-14 are the model program's cache buffers and V copy and the joined full-pass check (ADR-0153 code slice 2), the hand-written bf16 kernel fixtures, and the P2-12 harness records.

## Result

- **Outcome**: DONE. PR #266 squash-merged as `c9f1205`; branch `claude/T-0450-sdpa-kv-cache-binding-check` deleted.
- **Review**: 2 rounds, both Approve (issuecomment-6387575614, issuecomment-6387592067). Round 1 nit (`sdpa_generation_calls` collected shapes in a set; a list suffices) fixed in `7317939`.
- **CI**: green on all six jobs (run 40118274851). Local: ruff clean; full pytest 29724 passed, 949 skipped; `hilclaw/model_binding.py` at 100% lines.
- **Language**: Python - the host side of the executor is Python (ADR-0153 decision 2).
- **Reading**: the largest `l` of a generation is `prompt_length + generation_length - 1`; above 2**53 - 1 the SDPA functions refuse it as `invalid_input` (ADR-0001, ADR-0153 decision 5). No capacity or longest sequence is set.
- **Changes**: `hilclaw/model_binding.py` gains `SDPA_CALL_SITES`, `SDPA_DTYPES`, `sdpa_shape`, `sdpa_generation_calls`, `check_sdpa`, and an optional `bound` hook in `_check_rows`; tests in `tests/test_model_binding.py`; the import test in `tests/test_sdpa_kv_cache_bf16_contract.py` now allows `model_binding.py` as the one binder.
- **Less exact, not edited**: ADR-0153 decision 3 ("future contract records"); ADR-0157 decision 4 (dtype range applied per check); ADR-0162 Consequences (binding check listed as future work).
- **Follow-ups**: the model program's cache buffers and V copy, the joined full-pass check (ADR-0153 code slice 2; note `check_sdpa` cost grows with `generation_length`), hand-written bf16 kernel fixtures, P2-12 harness records.
