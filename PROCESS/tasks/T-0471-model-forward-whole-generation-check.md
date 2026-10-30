---
id: T-0471
title: Add hilclaw/model_forward_check.py, the whole-generation check of the bf16 forward pass over the six kinds' binding checks, with the weights', eps, RoPE-constant and mode refusals (ADR-0166 code slice 1)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: []
touchesFiles: [hilclaw/model_forward_check.py, tests/test_model_forward_check.py, hilclaw/rope_table.py, tests/test_rope_table.py]
estimatedSize: {loc: 380, files: 1}
hq: []
---
## Why

**State on `main` `da43429b`.** ADR-0166 (T-0470, `d25a61e4`) designs the bf16 forward pass and generation of the model executor on `cpu_standin`, which is ADR-0153 code slice 2 (PLAN P2-13; P2-14 needs it). Its Consequences (line 167) list six code slices in landing order with fixed cut points. None has landed.

**This task is slice 1: "The whole-generation check of decision 6: a new module `hilclaw/model_forward_check.py` over `hilclaw/model_binding.py`'s six checks, with the weights', `eps`, RoPE-constant and mode refusals; with tests."**
- `hilclaw/model_binding.py` already has the six kinds' checks (`check`, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope`, `check_sdpa`), each over its own call sites and not joined. This slice joins them, as ADR-0166 decision 6 fixes, and adds the refusals no existing check makes.
- It is pure Python. It builds, starts and reads nothing.

**Batch (DRIVER §6 "task 단위" ④).** The planner created T-0471 (slice 1), T-0472 (slice 2, the C program's prefill) and T-0473 (slice 3, decode passes, with slice 4, the host-side input and report) together. Slices 5 and 6 come in a later batch. This task does not depend on the other two, and they do not use this module.

**PLAN order and D18.** P2-13 is a checklist item and P2-14 needs it, so the D18 rule does not apply. The round-loop items and P2-5 are held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14.

**HQ-0071 (open, owner).** It asks OD-31 sub-question 6: the token selection rule, the model-level comparison and the reference. This task does not depend on its answer: ADR-0166 decisions 6 and 7 refuse the generation mode as invalid input until that answer exists, and this module implements exactly that refusal. Do not add a selection rule, a reference or a tolerance. **HQ-0070** (the RoPE scale factor) stays open: the caller gives every RoPE constant; no default is set.

**D16.** Pure Python with tests. Nothing starts `claude`, downloads a model file or needs a board or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (600 LOC, 10 files, tests excluded), the naming and the test rules.
  - For this task: branch `claude/T-0471-<slug>`; commit trailer `Task: T-0471`; code mode, so a Draft PR whose body ends with `Task: T-0471`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화" (a module docstring of an exposed API may be long), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`:
  - Status (lines 3-20), for what is and is not decided;
  - the notation (line 33);
  - decision 2's buffer table, the "Inputs" rows only (lines 45-58), for the weights and their shapes;
  - decision 4 (lines 104-112): the weights, their shapes and the column order of `w_qkv`; `eps`; the RoPE table and its five constants; the token ids;
  - decision 5 (lines 114-122): the embedding table as bf16 patterns;
  - **decision 6 (lines 124-130): the rule this task implements**;
  - decision 7 (lines 132-137): the given-sequence mode and the refused generation mode;
  - Alternatives rows of point 6 (lines 158-159);
  - Consequences, code slice 1 (line 168).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 (line 42, the inputs) and decision 5 (from line 58: the outcomes, no fallback).
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: decision 1 (from line 34) and decision 4 (from line 66).
- `hilclaw/model_binding.py`:
  - the module docstring (lines 1-125);
  - the call-site tuples and constants (lines 146-194), `ModelDimensions`, `BindingEntry`, `Outcome`, `BindingCheck` (lines 197-250);
  - `check_dimensions` (line 252);
  - `check` (lines 336-421) and `check_rmsnorm` (lines 454-509), for the argument refusals, the outcome order and the `parameter` attribute convention;
  - the signatures and docstrings of `check_elementwise_add` (line 544), `check_swiglu` (line 631), `check_rope` (line 727) and `check_sdpa` (lines 838-895);
  - `rmsnorm_eps` (lines 897-922);
  - `_check_rows` (lines 947-1003) and `_invalid_inputs` (lines 1049-1070), to see which length reasons several checks report with the same text.
- `hilclaw/rope_table.py`: the module docstring (lines 1-60 and its "Inputs" paragraph), `frequencies` (lines 93-130), `build` (lines 132-160) and `_checked` (lines 346-361).
- `tests/test_model_binding.py`: skim the helpers at the top and one test class of `check_sdpa`, for how entries, kernel references and contracts are built in tests.

## Acceptance Criteria

1. **New module `hilclaw/model_forward_check.py`**, written in Python because it joins Python functions of the host side (ADR-0153 decision 2); say so in one line of the commit body. Its module docstring states the rule (ADR-0166 decision 6), the conventions this module adds (below) and what it does not do (builds, loads, starts and reads nothing; no selection rule, no reference, no tolerance, no default for any model parameter or RoPE constant, no capacity value).
2. **Inputs as named types.** Define, as `NamedTuple`s or equivalent immutable types with documented fields:
   - the five RoPE constants: `theta`, `scale_factor`, `low_freq_factor`, `high_freq_factor`, `old_context_len` (the names of `rope_table.build`);
   - the weights of ADR-0166 decision 4: `embedding`, the per-layer sequences `attention_norm`, `qkv`, `o`, `ffn_norm`, `gate`, `up`, `down`, then `norm` and `lm_head`.
   Field names and the type names are this task's choice; keep them close to ADR-0166's buffer names. No field has a default.
3. **One public check function**, for example `check(dimensions, binding, *, dtype, eps, rope, weights, prompt, given, generation_length, lm_head_rows)`, returning a `model_binding.BindingCheck`. It:
   - splits `binding` by call site and runs **all six** checks of `model_binding` in the order `check`, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope`, `check_sdpa`, with `prompt_length` = len(prompt) for the five that take it;
   - treats a binding key that is none of the fifteen call-site names (the union of `CALL_SITES`, `RMSNORM_CALL_SITES`, `ELEMENTWISE_ADD_CALL_SITES`, `SWIGLU_CALL_SITES`, `ROPE_CALL_SITES`, `SDPA_CALL_SITES`) as a malformed binding (`ValueError` with `parameter` `"binding"`), as each check does for a key outside its call sites. A call site missing from the binding is passed on so that the check reports its `"no_kernel"` outcomes (state how the split passes an absent call site, for example an empty sub-mapping, and test it);
   - lets every `TypeError`/`ValueError` the six checks raise for a malformed argument propagate unchanged (with its `parameter`), including an odd `head_dim` from the RoPE check.
4. **Join: all, not first** (ADR-0166 decision 6). The outcomes are this module's own `"invalid_input"` outcomes first, then the six checks' outcomes in the order above; an `"invalid_input"` reason whose text equals an earlier one's is given once; reasons of different text for one cause are all kept. `ok` is true exactly when there is no outcome; then `calls` is the six checks' `calls` concatenated in the same order, otherwise empty. Document the order of this module's own outcomes.
5. **This module's own refusals**, each an `Outcome("invalid_input", None, None, reason)` with a reason naming its subject:
   - **the generation mode**: `given` is `None` — it has no selection rule (ADR-0166 decision 7; OD-31 sub-question 6). The given-sequence mode needs `given` of `generation_length` ids, as `model_binding.check` already checks;
   - **`eps`**: a value `model_binding.rmsnorm_eps` refuses with `ValueError`; a wrong type (its `TypeError`) is raised;
   - **RoPE constants**: values that `rope_table` refuses with `ValueError` (non-positive, non-finite, `high_freq_factor` not above `low_freq_factor`) give an invalid-input outcome per bad constant or the first one (state which); a wrong type is raised. **The table size**: `positions` = S + G − 1 with `positions * head_dim` above 2**53 − 1 is invalid input. Do not build the table here (it is costly); check the constants without computing frequencies if you can, for example by calling a small public checking function you add to `hilclaw/rope_table.py` that wraps `_checked`, or by calling `rope_table.frequencies` (state the choice in the commit body). If you add a function to `rope_table.py`, keep `build` and `frequencies` unchanged, and test it. An odd `head_dim` stays the RoPE check's malformed argument (criterion 3), not an outcome here;
   - **the weights** (ADR-0166 decision 6, "The weights' check"): every weight that is not a `numpy.ndarray` raises `TypeError` with `parameter` naming the weight; a per-layer sequence that does not hold `layers` arrays, an array whose shape is not the one ADR-0166 decision 4 gives from the dimensions (embedding (V, D), attention_norm (D,), qkv (D, W) with W = (H + 2·H_kv)·d, o (H·d, D), ffn_norm (D,), gate and up (D, F), down (F, D), norm (D,), lm_head (D, V)), or — at `dtype` `"bf16"` only — whose element type is not `numpy.uint16`, is invalid input naming the weight and, for a per-layer weight, the layer. At any other dtype the element types are not checked and the shapes are. Shapes are compared only when the dimensions are valid (`check_dimensions` passes first).
6. **No new outcome kind and no change** to `hilclaw/model_binding.py`. Arguments are not modified. Every `TypeError`/`ValueError` raised by this module carries `parameter`, as `model_binding` does.
7. **Size**: at most 600 changed lines outside tests, at most 10 files; expected one new module (plus at most one small function in `rope_table.py`).
8. **Tests: new file `tests/test_model_forward_check.py`** (D12, DRIVER §5): happy, error, branch and negative cases, and every public function and type of the new module. At least:
   - a small valid model (for example D = 8, F = 16, V = 11, N = 2, H = 4, H_kv = 2, d = 2) with `"every"` entries of fitting contracts for all fifteen call sites, in the given-sequence mode, under both `lm_head_rows` values: `ok` is true and `calls` equals the concatenation of the six checks' `calls` run separately;
   - **join, all not first**: a binding with an unfit entry at one kind and a missing shape at another reports both, in the order of criterion 4; an empty prompt gives each distinct reason once and keeps the reasons of different text;
   - the generation mode (`given=None`) is refused even when everything else is valid;
   - each weight refusal: wrong layer count, wrong shape of each weight (at least one per-layer weight and the embedding and lm_head), wrong element type at bf16, the same element type accepted (shapes still checked) at `"fp32"` together with the `"invalid_input"` of the kinds with no fp32 contract; a non-array weight raises `TypeError`;
   - `eps` refusals (0.0, negative, `inf`, a value whose nearest binary32 is 0) and `eps` of a wrong type raising;
   - RoPE constant refusals (each constant non-positive, `high_freq_factor` ≤ `low_freq_factor`), a wrong type raising, an odd `head_dim` raising from the RoPE check, and a table size over 2**53 − 1;
   - a binding key outside the fifteen names raising `ValueError`; a call site absent from the binding reported as `"no_kernel"`;
   - arguments are not modified (the binding mapping and the weight arrays are unchanged after the call).
   Keep the tests fast (no `rope_table.build` on large tables).
9. **No other behaviour change**: no dependency added; local `pytest` (with the 80 % line and function coverage gates) and `ruff` green.
10. **Process**: code mode (CLAUDE.md A-13). Draft PR titled with `T-0471`, body ending with `Task: T-0471`; reviewer cycle (dev-code-review), at most 7 rounds, until CI is green; then `gh pr merge --squash --body` with the PR body and delete the branch. The reviewer checks at least: the six checks' order and the split by call site; the join and its de-duplication; each refusal against ADR-0166 decision 6; that no selection rule, reference, tolerance, RoPE constant default or capacity value appears.

## Out of Scope

- The C forward program (slices 2 and 3; T-0472, T-0473), the host side's input encoding and report (slice 4; T-0473), the build-and-run path (slice 5) and the synthetic-model test (slice 6).
- Calling this module from anything else.
- Editing ADR-0153, ADR-0157, ADR-0166 or any "less exact" sentence ADR-0166 Consequences lists, including the docstring of `hilclaw/model_binding.py`.
- A token selection rule, a model-level reference or comparison (HQ-0071), a RoPE scale factor (HQ-0070).

## Follow-ups

- Next in the batch: T-0472 (ADR-0166 code slice 2).

## Result

**DONE.** PR #283, squash-merged as `16333cc4` (branch deleted). Review: 1 round, Approve (two Nits, both docstring-only, fixed after the Approve without re-review per D20). CI green on the final head `4930323a` (Python 3.11/3.14, coverage gate, C, sh, test presence).

- **Language**: Python, because the check joins Python functions of the host side (ADR-0153 decision 2).
- **`hilclaw/model_forward_check.py`** (new): `RopeConstants`, `Weights` (NamedTuples, no defaults) and `check(dimensions, binding, *, dtype, eps, rope, weights, prompt, given, generation_length, lm_head_rows)` returning a `model_binding.BindingCheck`. The binding is split by call site; each of the six checks gets the sub-mapping of its own keys (an empty mapping when none, so an absent call site is reported as `no_kernel`); a key outside the fifteen call sites raises `ValueError` (`parameter` `"binding"`). The six checks run first, so their argument errors propagate unchanged; then `eps`, `rope`, `weights` are refused by type in that order (`parameter` `"eps"`, `"rope"`/`"rope.<field>"`, `"weights"`/`"weights.<field>"`).
- **Own outcomes, in order**: generation mode (`given is None`); `eps` refused by `rmsnorm_eps`; **one per refused RoPE constant** (field order); the table size (`(S + G - 1) * head_dim > 2**53 - 1`, looked at only with a non-empty prompt and G in range); the weights in field order (per-layer: count, then each array's shape and, at `"bf16"` only, element type `uint16` in native byte order).
- **RoPE constant check choice**: a new public `rope_table.constant_refusals` (all types first, then every value refusal; no frequency computed). `_checked` was refactored onto the same helpers; `build`/`frequencies` behaviour unchanged.
- **Tests**: `tests/test_model_forward_check.py` (new, 175 tests) and `constant_refusals` tests in `tests/test_rope_table.py` (public-name and "named only by" tests updated). Full local suite 32405 passed; coverage of both touched modules 100 %; ruff clean.
- **Size**: about 390 changed lines outside tests, 4 files.
- **Follow-ups**: none. No HQ.
- This `## Result` edit is left uncommitted for the driver (DRIVER §3 step 6).
