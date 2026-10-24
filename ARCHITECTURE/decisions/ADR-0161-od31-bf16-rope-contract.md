# ADR-0161: Operational contract of RoPE on Q and K of Llama 3.2 1B in bf16 for C kernels on `cpu_standin` — kind `rope` with shape members `m`, `h` and `d`, called twice per layer (Q, then K), the cos/sin table as an operand of correctly rounded binary32 values built outside the kernels, adjacent element pairs, binary32 or wider products and sums before a round-to-nearest-even output, contiguous copies of Q and K and no in-place call, the entry point `hilclaw_rope_bf16`, the value sets of the verification inputs, the op_signature records of the ADR-0152 row 5 calls and the names of its two call sites (extension of OD-6 sub-question 1; part of OD-31 sub-questions 1 to 3)

## Status

- **Accepted on 2026-10-24.** It defines the fifth Llama kind contract of PLAN P2-11.
- **Three kinds of content.**
  - **Owner answers**, marked **owner**: the `decision` of HQ-0064, HQ-0065 and HQ-0066 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records them. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md), [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md), [ADR-0160](ADR-0160-od31-bf16-swiglu-contract.md)), of Meta's code and of Hugging Face's converter, each with its source named.
  - **This record's own**, every other sentence: the kind and member names, the two calls, the table and its precision, the kernel's precision, the output rounding, the prototype and symbol, the guarantees, the value sets, the op_signature records, the call-site names and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 259 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: RoPE, rotary, rope_theta, theta, scaling, scaled, position, positional, frequency, freqs, sin, cos, complex, permute, 회전, 위치, interleave, half, pair, bf16, bfloat16, rounding, 반올림, in-place, in place, stride. Found, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "16 heads / 8 KV heads, head_dim 64, vocab 128,256, RoPE, SwiGLU, GQA", "attention configuration (GQA 16/8, head_dim 64, RoPE, causal) **follows Llama 3.2 1B**", nntrainer's idioms "(… softmax_row, rotary)" and "dtype **fp32** (bf16 weights upcast)". It names RoPE as part of the model and says the attention configuration follows Llama 3.2 1B; it says nothing of the table, the pairing, the precision or the rounding. Its head counts read 32 and 32/8 (**owner**, HQ-0064).
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16." It names no kind.
  - **Ordinary words only**: "위치" (18 hits) is a location (of a file, a tree, a decision); "interleave(d)" and "pair(ed)" (3 each, #7 and #8) are the paired interleaved timing measurement of OD-13. None is about RoPE.
  - **Nothing found** on theta, scaling, frequencies, sin, cos, complex numbers, a permutation, a half split, rounding, in-place calls or strides.
  - **Conflicts**: K1's fp32 is the first case, which stays, and K2 is answered by HQ-0065 (ADR-0154 decision 2). No owner sentence conflicts with a choice of this record.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `0be4dfa`). **HQ-0033** (the ADR-0116 flags `-std=gnu11 -O2 -ffp-contract=off` and the trailing `-lm`, for the first case): no flag is chosen. The kernel of this contract has no sin or cos (decision 4); its multiplies and adds may be contracted into fused multiply-adds, which decision 7's bound admits as shown there, and flags that relax IEEE arithmetic (`-ffast-math` and its parts) could reassociate the two-term sum or flush subnormals, which the bound absorbs inside its domain and which is a build setting outside it (Boundaries). sin and cos are evaluated by the host side's table builder, whose entries decision 4 fixes as correctly rounded values whatever the method, so these C flags cannot change them. **HQ-0034** (OpenMP on `cpu_standin`): not chosen. **HQ-0069** (runtime acceptance (lxvii) of the model executor): no runtime fact is used; the call-site names of decision 15 are inputs to a later code slice. The other open HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0021 to HQ-0024, HQ-0026 to HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **Not changed**: no schema file, member, file, version or validator of the data plane. `rope` with its members `m`, `h` and `d` is a new kind, which ADR-0001 decision 6 admits without raising `schema_version`; `bf16`, `fp32` and `row_major` are existing values. It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-6 sub-question 1, the contract of (`rope`, `bf16`, `row_major`, `c`) on `cpu_standin`; of OD-31 sub-question 1, the RoPE kind's contract, op_signatures and call-site names; of sub-question 2, the precision of the frequencies, angles, sin/cos and rotation, and the rounding of the output; of sub-question 3, the value sets of the RoPE verification inputs. Open of them: Boundaries.
- It builds on ADR-0001 (decisions 2 and 6), ADR-0008 (decisions 1, 2 and 4 to 8), ADR-0037, ADR-0152 (decisions 2, 3, 5 and 7), ADR-0153 (decisions 3 and 4), ADR-0154 (decisions 1 to 3), ADR-0156 (decisions 2, 4, 5 and 9), ADR-0157 (decision 4), ADR-0158 (decisions 3, 5 and 7), ADR-0159 (decisions 4, 8 and 13) and ADR-0160 (decisions 8 and 9); none of them is edited. The format follows the "Record format" section of ADR-0001.

## Context

- **Meta's reference** (cited), `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py`:
  - `apply_scaling` (lines 45-62): constants `scale_factor = 8`, `low_freq_factor = 1`, `high_freq_factor = 4`, `old_context_len = 8192` (lines 47-50); `low_freq_wavelen = old_context_len / low_freq_factor`, `high_freq_wavelen = old_context_len / high_freq_factor` (lines 52-53); `wavelen = 2 * torch.pi / freqs` (line 55); `new_freqs` = `freqs / scale_factor` where `wavelen > low_freq_wavelen`, else `freqs` (line 56); `smooth = (old_context_len / wavelen - low_freq_factor) / (high_freq_factor - low_freq_factor)` (line 57); the result is `(1 - smooth) * new_freqs / scale_factor + smooth * new_freqs` where `high_freq_wavelen <= wavelen <= low_freq_wavelen`, else `new_freqs` (lines 58-62).
  - `precompute_freqs_cis(dim, end, theta, use_scaled)` (lines 65-72): `freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)[: (dim // 2)].float() / dim))`, positions `t` of `float32`, `apply_scaling` if `use_scaled`, `torch.outer(t, freqs)`, and `torch.polar(torch.ones_like(freqs), freqs)`, "complex64" (lines 66-71).
  - `apply_rotary_emb` (lines 83-93): `xq.float().reshape(*xq.shape[:-1], -1, 2)` viewed as complex (lines 88-89), multiplied by `freqs_cis` broadcast over the heads by `reshape_for_broadcast` (lines 75-80, 90), viewed as real and flattened (lines 91-92), and returned with `type_as(xq)` and `type_as(xk)` (line 93).
  - `Attention.forward`: `xq`, `xk` and `xv` from `wq`, `wk` and `wv` (line 172), viewed as (bsz, seqlen, heads, head_dim) (lines 174-176), then `apply_rotary_emb(xq, xk, freqs_cis=freqs_cis)` (line 178). `Transformer` builds the table with `params.dim // params.n_heads`, `params.max_seq_len * 2`, `params.rope_theta` and `params.use_scaled_rope` (lines 273-278) and passes `self.freqs_cis[start_pos : start_pos + seqlen]` (line 285).
  - `models/sku_list.py`, `llama3_2_1b`: `"rope_theta": 500000.0` and `"use_scaled_rope": True` (lines 342-343).
- **Another source of the constants** (cited): Hugging Face `transformers` at commit `f4410762062c274fb53471e551e62b377df44cc1`, `src/transformers/models/llama/convert_llama_weights_to_hf.py`, sets `"factor": 32.0 if llama_version == "3.2" else 8.0`, `low_freq_factor` 1.0, `high_freq_factor` 4.0 and `original_max_position_embeddings` 8192 (lines 376-383), and converts the `wq` and `wk` weights with `permute(w, n_heads, …)`, `w.view(n_heads, dim1 // n_heads // 2, 2, dim2).transpose(1, 2)` (lines 220-221). So the two sources differ in the scale factor of Llama 3.2, and a converted checkpoint stores Q and K projection weights in another order of the head elements. Neither is resolved here (decisions 4 and 5, Boundaries).
- **The call and its shapes** (ADR-0152 decision 2 row 5, decision 5; ADR-0154 decision 1): RoPE on Q (T × 32 × 64) and K (T × 8 × 64) at positions P … P+T−1, `rope_theta` 500000 with Llama 3 scaling (Meta); prefill P = 0 with T ∈ {128, 2048}, a decode step T = 1 at P ∈ {127, 2047}. Q, K and V are column ranges of the one QKV output, and the order and strides in which RoPE reads them are conventions of this contract (ADR-0152 decision 3); so is whether the frequency table is an operand computed outside the kernels (same). RoPE is its own kernel, not inside SDPA (ADR-0152 Alternatives). ADR-0153 Context counts RoPE as one call and says "its contract may make it two"; ADR-0153 decision 3 (b) admits the table as "one more array" of the host side's inputs.
- **The owner's answers** (ADR-0154 decisions 2 and 3): bf16 inputs and outputs, `uint16_t` patterns with the kernel converting; fp32 accumulation for three sums, none of them RoPE's, and "RoPE's angles, frequencies and sin/cos" left to this record; a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; the input distribution fixed by a driver record, finite inputs only.

## Decision

A sentence marked **owner** renders an HQ `decision` through ADR-0154. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **One contract**: RoPE of ADR-0152 row 5 for kind `rope`, dtype `bf16`, layout `row_major` and kernel language `c`, **on `cpu_standin`**. It binds both sides as ADR-0008 decision 1 says, and the host side's table of decision 4 as well. **No fp32 or fp16 contract of this kind is defined.** "As ADR-0008" (or another record) means that text with this record's kind, symbol and operands.

### 2. Two calls of one kind

- **A call rotates one tensor of `h` heads; row 5 is two calls**, Q (h = 32) then K (h = 8), in the order of Meta's line 178. Reasons: Meta applies the same lines to both (91-92), so one kind covers both with h as a member; each call has one input, one output and the table, and the binding check one entry form per call site; a model with other head counts reuses the kind. **One pass is 16 × 13 + 2 = 210 kernel calls**, not ADR-0153's 194; the instance targets are six op_signatures (decision 14) instead of three.

### 3. Kind and shape members

- **Kind `rope`**; it matches `[a-z][a-z0-9_]{0,31}` and names the operation (ADR-0001 decision 2). **Shape members `m`, `h` and `d`, exactly these**: `m` = T, the tokens of the call (the `m` of the other kinds at the same T); `h` = the heads of the rotated tensor (32 for Q, 8 for K); `d` = head_dim (64). By ADR-0001 decision 6 the kind and members raise no `schema_version`.
- **The position is neither a member nor a parameter.** The caller passes the table rows of positions P … P+T−1 (decision 4), as Meta slices `freqs_cis` by `start_pos` (line 285). The kernel's work and cost do not depend on P, so P as a member would split one computation over several keys (P = 127 and P = 2047 at T = 1) for nothing. The (T, P) of ADR-0152 Alternatives stay the verification positions (decision 13).
- **`rope_theta` and the scaling constants reach the kernel only through the table**, unlike ADR-0158's `eps` (a `float` parameter, decision 5 there): `eps` is used by the kernel's arithmetic, while these constants only shape a table that is the same for every layer and call. As members they would split keys by model constant; as parameters or contract constants they would put into the kernel the computation decision 4 keeps out, and the scale factor on which the sources differ (Context).

### 4. The frequency table

- **Built outside the kernels, by the host side** (ADR-0153 decision 3 (b)), once per generation, for positions 0 to the last position of the generation, from the model parameters `head_dim`, `rope_theta` and the four scaling constants (ADR-0153 decision 3 (a), "the RoPE constants"). It is an operand of every call (decision 10), shared by all layers and both calls.
- **The rule** (Meta's lines 45-71 in real arithmetic): for i = 0 … d/2 − 1, f(i) = θ^(−2i/d); λ = 2π / f(i); g(i) = f(i)/s if λ > L/a; g(i) = (1 − σ) · f(i)/s + σ · f(i) with σ = (L/λ − a)/(b − a) if L/b ≤ λ ≤ L/a; g(i) = f(i) otherwise; angle(t, i) = t · g(i); entry (t, 2i) = cos angle(t, i) and entry (t, 2i + 1) = sin angle(t, i). Constants, from Meta's code at the pinned commit: θ = 500000 (`sku_list.py` line 342), s = 8, a = 1, b = 4, L = 8192 (`model.py` lines 47-50). In the middle band λ ≤ L/a, so Meta's `new_freqs` there is `freqs`, as written. For Llama 3.2 1B (computed): i = 0 … 14 keep f(i) (λ < 2048), i = 15 … 17 are smoothed (λ from 2948 to 6695), i = 18 … 31 are divided by 8 (λ > 8192); g(0) = 1 and g(31) ≈ 3.767 · 10^−7, so the largest angle at P = 2047 is 2047.
- **Precision: each entry is the binary32 value nearest to the exact cos or sin of the exact angle, ties to even** (correctly rounded), so the table, and with it the verification inputs, is the same on every machine. The method is the builder's, and its tests check the entries against an evaluation at higher precision; NumPy's float64 `cos` and `sin` have no accuracy their documentation or the C standard guarantees. A float64 evaluation (π as `math.pi`) rounded to binary32 met it on every one of the 131072 entries of rows 0 … 2047 for Llama 3.2 1B (computed with NumPy 2.5.2 on Windows x86-64 against Python's `decimal` at 60 digits), and its g(i) are within a relative 2.1 · 10^−16 of the exact ones. **Why not binary32 angles, as Meta**: at P = 2047, ulp(2047) = 2^−13, so a binary32 angle alone errs by up to 2^−14 ≈ 6.1 · 10^−5 rad; a table built with correctly rounded binary32 frequencies and angles (an idealisation of Meta's order; how PyTorch evaluates `**`, `outer` and `polar` was not read) differs from the exact cos/sin by up to 9.57 · 10^−5 (computed), against 2.98 · 10^−8 for this table. **This departs from Meta's order of roundings**; on the value sets of decision 13 the idealised fp32 table changes the correctly rounded output on 0.16 % of the elements (computed). Whether the model-level comparison needs Meta's order is OD-31 sub-question 6 (owner). Listed in the owner notice.
- **Why outside the kernel**: inside, the kernel would compute sin and cos of angles up to 2047 on every call — 32 calls per pass recomputing one table — and the contract would need an accuracy bound for its argument reduction and carry the constants, the scale factor among them. The table is a model constant (ADR-0152 decision 3), 2048 × 64 binary32 values = 524288 bytes for 2048 positions. **Which scale factor Llama 3.2 1B's weights need** (8 in Meta's code, 32 in Hugging Face's converter, Context) is a property of the weights and the reference, OD-31 sub-questions 5 and 6 (owner); the contract does not depend on it.

### 5. The pairing

- **Adjacent elements form a pair**: elements 2i and 2i + 1 of a head, i = 0 … d/2 − 1, as `reshape(…, -1, 2)` and `view_as_complex` read them (Meta's lines 88-89); **pair i takes table column pair i**, entries (t, 2i) and (t, 2i + 1), as `reshape_for_broadcast` lays `freqs_cis` over the last dimension (lines 75-80, 90). The same pairs in every head. Whether a checkpoint's Q and K weights fit this pairing is Boundaries.

### 6. Dtype, layout and strides

- **`x` and `out`: dtype `bf16`, shape `[m, h, d]`, layout `row_major`**, each element a `uint16_t` bf16 pattern as ADR-0156 decision 2. ADR-0008 decision 2 leaves other ranks to the first record with one; **a rank-3 operand `[r, s, c]` is one contiguous array of r·s·c elements, element (i, j, k) at index (i·s + j)·c + k**, no padding, no stride. Element (i, j, k) is element k of head j of token i, Meta's view (lines 174-175).
- **`freqs_cis`: dtype `fp32`, shape `[m, d]`, layout `row_major`**: row i is the table row of position P + i. `fp32` because the kernel multiplies in binary32 (decision 7); rounded to bf16 the entries would add up to a relative 2^−8 to each term (decision 13).
- **The kernel reads contiguous copies**: the model program copies the Q range and the K range of the QKV output into `x` arrays (ADR-0153 decision 4, "copies a contract leaves"), and RoPE writes `out` arrays that SDPA reads. Reasons: `row_major` has no stride (ADR-0008 decision 2), and a row-stride parameter would have no value in the key or the operand entries' sizes; the copies are T × 2560 bf16 values per layer, 10485760 bytes at T = 2048. Which columns of the QKV output are the Q, K and V ranges follows from how the joined QKV weight is formed (ADR-0153 decision 3 (b); OD-31 sub-question 5). **SDPA then receives** the rotated Q as `[T, 32, 64]` and the rotated new K rows as `[T, 8, 64]`, contiguous bf16; how it reads them and V is the SDPA record's.

### 7. The operation and its precision

- **The operation** (Meta's lines 88-92, complex product): for each token i, head j and pair p, with x₀ = x(i, j, 2p), x₁ = x(i, j, 2p + 1), c = freqs_cis(i, 2p), s = freqs_cis(i, 2p + 1): **y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c**, out(i, j, 2p) and out(i, j, 2p + 1) their bf16 values. The kernel converts its inputs (**owner**, HQ-0065 (3)); widening is exact.
- **Every product and sum is held in binary32 or wider, never narrower, and no value is rounded to a 16-bit format before the output conversion.** Fused multiply-adds and any association are the kernel's choice.
- **The bound: the value v the kernel converts has |v − y| ≤ 2^−22 · (|x₀·c| + |x₁·s|)** (for y₁, |x₀·s| + |x₁·c|), over the domain D: every non-zero product and every non-zero y in the normal binary32 range. Any evaluation with correctly rounded binary32 operations meets it: each of the two products and the sum adds a relative u = 2^−24 at most, so |v − y| ≤ (2u + u²)(|x₀·c| + |x₁·s|) < 4u(…), and a fused multiply-add only removes a rounding. A table or product rounded to 16 bits can break it. The bound is relative to the magnitudes of the terms, not to y, because y may cancel (decision 13).
- **Why not a correctly rounded result** (ADR-0159 decision 4): y is a difference of exact products whose bf16 rounding needs more than binary32 near cancellation and near rounding boundaries; it would buy at most one bf16 unit in the last place there, at the cost of float64 lanes. **Why not "binary32 or wider" alone** (ADR-0158 decision 3): with no approximation step the two say the same, and the bound states what a kernel and a test may rely on. Meta computes the product in `complex64` and rounds once with `type_as` (lines 91-93); the kernel side keeps that order (decision 4 is the departure).

### 8. The output conversion

- **Round to nearest, ties to even**, from v to bf16, as ADR-0156 decision 4 (cited). **Range**: |y₀| and |y₁| are at most (x₀² + x₁²)^(1/2) · (c² + s²)^(1/2), so no output of finite bf16 inputs of normal magnitude overflows; zero and its sign are not fixed by this contract; on the value sets of decision 13 every exact output has a magnitude in [2^−31, 1.409] (computed), so none is zero, subnormal or overflowing. Outside D, subnormal and non-finite inputs and outputs are not defined here (Boundaries).

### 9. The C prototype and the symbol

```c
void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte, in every spec of this contract: single spaces, no line break, the semicolon included; valid in C99 and later. **Order**: dimensions first as ADR-0008 decision 4 (no position or constant, decision 3), then input `x`, the table and output `out`, Meta's argument order (lines 83-86); `void`; `restrict` on all three (decision 11). `float` is binary32 (ADR-0008 decision 4); `uint16_t` is the **owner**'s (HQ-0065 (3)).
- **Symbol `hilclaw_rope_bf16`**, the form of ADR-0156 decision 5 for its reasons.

### 10. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `x` | `input` | `bf16` | `[m, h, d]` | `const uint16_t *restrict x` |
| `freqs_cis` | `input` | `fp32` | `[m, d]` | `const float *restrict freqs_cis` |
| `out` | `output` | `bf16` | `[m, h, d]` | `uint16_t *restrict out` |

As ADR-0008 decision 5. The complete `task.contract` at T = 1 for K (h = 8):

```json
{
  "language": "c",
  "prototype": "void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);",
  "operands": [
    {"name": "x", "role": "input", "dtype": "bf16", "shape": [1, 8, 64]},
    {"name": "freqs_cis", "role": "input", "dtype": "fp32", "shape": [1, 64]},
    {"name": "out", "role": "output", "dtype": "bf16", "shape": [1, 8, 64]}
  ]
}
```

**Validated on 2026-10-24** with `hilclaw.spec.validate`, inside `examples/spec/gemm-485b9bc494d477eb.json` with its op_signature replaced by the K record at T = 1 of decision 14 and its `task.contract` by the object above, in a throwaway interpreter that added `"rope": frozenset({"m", "h", "d"})` to `hilclaw.keys._SHAPE_MEMBERS` in memory: accepted; with the shape of `freqs_cis` changed to `[1, 32]` it was refused (`task.contract.operands[1].shape[1]: must be a value of task.op_signature.record.shape, got 32`). No repository file was changed.

### 11. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | `m` and `h` are at least 1, `d` is even and at least 2; `x` and `out` have m·h·d elements, `freqs_cis` m·d. | Compute the operation for the values it is called with. |
| Overlap | The three arrays do not overlap; `out` is not `x` (no in-place call). | — |
| Inputs | `x` holds initialised bf16 patterns and `freqs_cis` initialised `float` values, in the layouts of decision 6, unchanged by others during the call. | Not modify them. |
| Output | The content of `out` on entry is unspecified. | Not read `out` before writing it; write every element, each the bf16 pattern of decisions 7 and 8. |
| Alignment | Each pointer is aligned for its element type. | Not assume more. |
| Memory, repeated calls, completion, result | As ADR-0008 decision 6. | As ADR-0008 decision 6. |

- **No in-place call.** `x` is a copy no one reads after the call (decision 6), so writing over it would be safe and would save one buffer per call site; refused for the reasons of ADR-0159 decision 8: `restrict` on every operand, ADR-0153 decision 3's "distinct arrays for each operand" kept by kind, and the refusals of ADR-0158 decision 7, ADR-0159 decision 8 and ADR-0160 decision 8.
- **Every set of dimensions** (m, h ≥ 1, d even ≥ 2): the obligation is stated for the values passed, so **a binding "for every shape" of ADR-0153 decision 3 is accepted**. No limit on P: the host side's table holds every position of the generation (decision 4). Whether a verification passes other values stays OD-16 sub-question 1. **No shape with a 0**, as ADR-0037. **Finiteness** is not in the input guarantee (ADR-0008 decision 6).

### 12. What the kernel source provides

- As ADR-0008 decision 7: exactly one definition of `hilclaw_rope_bf16`, no `main`, no other external `hilclaw_` identifier (`hilclaw_gemm`, `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16` and `hilclaw_swiglu_bf16` included). The kernel needs no function of `<math.h>`; it may include it as ADR-0160 decision 9 reads ADR-0008 decision 7, and linking the math library is a build setting.

### 13. The input value sets of verification

- **Owner** (HQ-0066 (3)): fixed here; the rest is the P2-12 harness record's.
- **`x`**: every element is one of the 256 bf16 values of magnitude in [0.5, 1) with either sign, the set of ADR-0156 decision 9 (the rotation is linear in x, so a wider range adds nothing distinctive). **`freqs_cis`**: rows P … P+T−1 of the table of decision 4 for Llama 3.2 1B's parameters: rows 0 … T − 1 for T ∈ {128, 2048}, and row 127 or row 2047 for T = 1 (ADR-0154 decision 1's positions), the same rows for Q and K. The table is built with the constants of decision 4 (s = 8) whatever the answer on the scale factor, since the kernel's verification needs angles, not the model's; the facts below are for it.
- **Computed facts** (every pair (x₀, x₁) of the set against every entry pair of rows 0 … 2047, 2^32 cases, halved by y(−x₀, −x₁) = −y(x₀, x₁); y₁ has the form of y₀ with (x₁, −x₀); NumPy 2.5.2): exact outputs in [2^−31, 1.409] in magnitude, none zero. **The reference** (float64 of the widened inputs) has products exact (8 by 24 significant bits) and one rounding, a relative error of at most 2^−53; the largest angles enter only through the table entries, which are its inputs. **Compliant outputs** are the bf16 values from RNE(y − e) to RNE(y + e), e the bound of decision 7. **Cancellation**: one of them differs from y by more than a relative 2^−8 on 83212 of the 2^31 computed cases (0.0039 %), by up to a relative 457 at the smallest outputs, so what an `rtol` alone accepts there depends on the tolerance the user sets.
- **What the set detects**, as the share of cases where the wrong result differs from y by a relative 2^−6 or more: the sign of the sine term flipped, 73.1 % (small angles barely change); cos and sin swapped, 95.6 %; the table row of the next position, 32.8 % (rows 0 … 2046); the half-split pairing (element j with j + d/2 at frequency j), 83.2 % (a Monte Carlo estimate: NumPy `default_rng(0)`, 100000 heads with uniform rows). Not a compliant output: with a bf16-rounded table, 18.5 % (2.1 % by 2^−6 or more); with truncation in place of decision 8, 49.9 % (relative error up to 0.00775); detected only under a tight enough tolerance. A wrong head count leaves elements unwritten or misplaced, which depends on the harness's sentinel (P2-12). **Not detected by the kernel's verification**, since the kernel does not compute them: a wrong `rope_theta`, a missing or wrong scaling, a wrong position and Q and K swapped are errors of the table builder or the binding, for their own tests in the code slice.
- **Left to P2-12**: generator, seed, draws, which T = 1 row a draw uses, the content of `out` before the call, the widening. **No tolerance value or default** (**owner**, HQ-0066 (2)).

### 14. The `op_signature` records

**Rule**: `{"schema_version": 1, "kind": "rope", "shape": {"m": T, "h": H, "d": 64}, "dtype": "bf16", "layout": "row_major"}` for T ∈ {1, 128, 2048} and H ∈ {32, 8}; **all layers share them**. At T = 1, H = 8:

```
{"dtype":"bf16","kind":"rope","layout":"row_major","schema_version":1,"shape":{"d":64,"h":8,"m":1}}
sha256 = c797475e043d41569f5a69878631c9c59bde735b28fc614aab427b1d9cd4006a  ->  rope-c797475e043d4156
```

| T | 1 | 128 | 2048 |
|---|---|---|---|
| Q (H = 32) | `rope-1fafc8411a47dc19` | `rope-9d2410e4438eac67` | `rope-7e13c7020a9b17fb` |
| K (H = 8) | `rope-c797475e043d4156` | `rope-74ab3d4ad2c2e42c` | `rope-125adcdf54641cca` |

- **Method**: `hilclaw.keys.op_signature_key` in the interpreter of decision 10; it gave `swiglu-7b82bc7d69cda1e0` for ADR-0160's T = 1 record. How a shape set maps to instances stays OD-6 sub-question 3; contract change, OD-6 sub-question 4 (ADR-0008 decision 8).

### 15. The call sites

- **`rope_q` and `rope_k`**, in that order, for the two calls of row 5. Meta gives them no module; the names say the operation and the tensor (`xq`, `xk`, line 178) and are distinct from every call-site name in `hilclaw/model_binding.py`.

| Call site | `x` | `freqs_cis` | `out` |
|---|---|---|---|
| `rope_q` | the model program's copy of the Q range of the output `c` of the GEMM call site `qkv` of the same layer (row 3) | rows P … P+T−1 of the generation's table | read as the query input of the SDPA call of the same layer (rows 6, 7) |
| `rope_k` | the copy of the K range of the same output | the same rows | read by that SDPA call as the new K rows it writes into the cache |

- The SDPA call's operands and name are the SDPA record's.

### 16. Order and runs

No order of kinds, instance or run is chosen, as ADR-0159 decision 13.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | One call rotating Q and K together (members for both head counts) | Fewer calls, but two inputs and outputs per call and a kind tied to a pair of head counts, for an operation Meta writes once for both. |
| 3 | P a member, or a parameter with a whole table | A member splits identical work over keys; a whole-table parameter needs a table size that is no member value. |
| 3 | `rope_theta` and the scaling constants as parameters or contract constants | They would move the table's computation into the kernel (point 4) and bind the scale factor on which the sources differ. |
| 4 | The kernel computes the angles and sin/cos | 32 recomputations per pass, an accuracy bound for argument reduction at angles up to 2047, and the constants in the contract. |
| 4 | A table built in binary32, as Meta | Errs by up to 9.57 · 10^−5 at the largest angles against 2.98 · 10^−8. |
| 4, 6 | A bf16 or float64 table | bf16 adds up to a relative 2^−8 per term (point 13); float64 doubles the bytes for precision binary32 products drop. |
| 5 | Half-split pairs (j with j + d/2) | Not Meta's `apply_rotary_emb`; a checkpoint's layout is Boundaries. |
| 6 | Read Q and K in place in the QKV output with a row stride | No stride in `row_major`, and the stride value is no key member; the copy costs 10 MiB per layer at T = 2048. |
| 7 | Correctly rounded output; or binary32 or wider without a bound | Point 7. |
| 11 | Allow `out` = `x` | Point 11. |
| 15 | `rotary_q`, `attention_rope` | `rope_q`, `rope_k` name both calls and follow the kind. |

## Consequences

- **A-13 reading**: no schema file, member, file, version or validator of the data plane changes, and `hilclaw/` is not touched; the new kind `rope` and its members are values ADR-0001 decision 6 admits.
- **The code slice this record makes possible** (for the planner; no code here): the kind and members in `hilclaw.keys`; a contract module (`task_contract`, `covers`, `op_signature_record`, the value set); a table builder on the host side (decision 4) with tests against the rule, which carry what decision 13 leaves undetected; the binding check in `hilclaw/model_binding.py` with `rope_q`, `rope_k`, shape (rows, heads, head_dim) and the "every shape" binding, `bf16` only; the RoPE constants in the model parameters; hand-written kernels as fixtures (one compliant, wrong ones such as a flipped sine or half-split pairs); the P2-12 harness part.
- **Less exact, not edited** (search of `ARCHITECTURE/` for "RoPE", "other two kinds", "other five kinds", "future contract records", "Each kind's contract" and "counted as one call"; not claimed complete): ADR-0008 decision 2 (other ranks; rank 3 now defined); ADR-0152 decision 1's naming bullet, decision 3 (the table), Boundaries ("Each kind's contract", the pairing); ADR-0153 Context ("counted as one call", 194 calls), decision 3 ("future contract records", the table "if"), Consequences code slice (2) and Boundaries; ADR-0154 decision 2 ("RoPE's angles, frequencies and sin/cos"), Consequences and Boundaries; ADR-0156 and ADR-0157 ("the other five kinds"); ADR-0158 ("the other four kinds"), ADR-0159 ("the other three kinds") and ADR-0160 Boundaries ("the other two kinds — RoPE and SDPA").
- **Runtime acceptance items**: none.
- **Readings for the owner to check**, listed in the #5 notice: the table built outside the kernels with correctly rounded binary32 entries, departing from Meta's binary32 angles (0.16 % of outputs, decision 4); the scale factor of Llama 3.2 1B — 8 in Meta's code, 32 in Hugging Face's converter — left to the weights and reference (decision 4); adjacent pairs, while converted checkpoints permute `wq` and `wk` for half-split pairs (decision 5); two calls per layer and 210 calls per pass (decision 2); contiguous copies of Q and K by the model program (decision 6); no in-place call; the names `rope`, `m`, `h`, `d`, `freqs_cis`, `rope_q`, `rope_k`; the value sets (decision 13).
- **A question for the driver to record as an HQ** (DRIVER §8, reason `owner-only-decision`, non-blocking): "Llama 3.2 1B의 RoPE scaling factor가 Meta `llama-models`(0e0b8c5) `apply_scaling`에서는 8, Hugging Face 변환기(f441076)에서는 32입니다. ADR-0161은 테이블을 커널 밖에서 모델 파라미터로 만들게 해 계약은 이 값과 무관합니다. 어느 값이 맞습니까? (a) 쓸 가중치·reference(OD-31 ⑤·⑥)가 정해질 때 그 출처의 값 (b) Meta 코드의 8 (c) 32. 막히는 것: 모델 수준 대조와 테이블 생성기의 Llama 상수(P2-14). 막히지 않는 것: RoPE 계약·코드 slice·하네스(P2-11·P2-12)."
- **UsageCases and StandardScenarios** (S0 and S1 re-checked, and every scenario row citing OD-6 sub-question 1 or OD-31): no use case step changes. S0 step 4's open kernel contracts are now those outside `gemm`, `rmsnorm`, `elementwise_add`, `swiglu`, `rope` and C; S0 step 5 and S1 step 2 keep OD-31 sub-question 3 and #5 B-7. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **fp16** (owner, HQ-0065 (1), after P2-14); **an fp32 contract of this kind** (ADR-0157 decision 4).
- **Tolerance values** (FR-9; owner, HQ-0066 (2)).
- **Build settings and OpenMP**: flags, `-ffp-contract`, IEEE-relaxing flags, `-lm`, the floating-point environment, threads (HQ-0033, HQ-0034, OD-6 sub-question 2).
- **The harness mechanism** and the parts of decision 13 left to it (P2-12).
- **Corner-case, non-finite and subnormal inputs and outputs**, inputs outside D (#5 B-7, OD-16).
- **Positions and shapes outside an instance's** (OD-16 sub-question 1, ADR-0152 decision 7); **how a shape set maps to instances** (OD-6 sub-question 3); **contract change and keys** (OD-6 sub-question 4).
- **Fusion** of RoPE with the QKV GEMM or with SDPA (later, C-6).
- **The SDPA with KV cache contract**, how it reads the rotated Q and K and V, and its call-site name.
- **The weights and checkpoint format**, including whether the Q and K projection weights are stored for this pairing or permuted (Hugging Face's `permute`, Context) and whether a permutation happens before the QKV weight is joined, and **the scale factor** of decision 4 (OD-31 sub-question 5, owner); **the model-level comparison** (sub-question 6, owner).
- **Backends other than `cpu_standin`** (#5 B-2, B-7).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, PLAN P1-5) or to ADR-0156, ADR-0158, ADR-0159 and ADR-0160.

## References

- Owner: HQ-0064 to HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1), C-6 revision (K2); [Requirements](../Requirements.md) C-6, FR-5, FR-9, OD-6, OD-16, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6 and § OD-31.
- Records: ADR-0001, ADR-0008, ADR-0037, ADR-0152, ADR-0153, ADR-0154, ADR-0156, ADR-0157, ADR-0158, ADR-0159, ADR-0160 (linked in Status).
- Meta: `meta-llama/llama-models` at `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` (lines 45-93, 172-178, 273-285), `models/sku_list.py` (lines 342-343), read through `gh api`.
- Hugging Face: `huggingface/transformers` at `f4410762062c274fb53471e551e62b377df44cc1`, `src/transformers/models/llama/convert_llama_weights_to_hf.py` (lines 220-221, 376-383), read through `gh api`.
- Code read: `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/swiglu_bf16_contract.py`, `hilclaw/model_binding.py`; `examples/spec/gemm-485b9bc494d477eb.json`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
