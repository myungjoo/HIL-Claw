# ADR-0160: Operational contract of the SwiGLU activation of the Llama feed-forward in bf16 for C kernels on `cpu_standin` — kind `swiglu` with shape members `m` and `n`, dtype `bf16` and layout `row_major`, binary32 or wider intermediates with a relative error of at most 2^−11 before a round-to-nearest-even output and no bf16 rounding of the SiLU, the entry point `hilclaw_swiglu_bf16` over `uint16_t` bit patterns with no in-place call, the value sets of the verification inputs, the op_signature records of the ADR-0152 row 12 calls and the name of its call site (extension of OD-6 sub-question 1; part of OD-31 sub-questions 1 to 3)

## Status

- **Accepted on 2026-10-24.** It defines the fourth Llama kind contract of PLAN P2-11.
- **Three kinds of content.**
  - **Owner answers**, marked **owner**: the `decision` of HQ-0065 and HQ-0066 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records them. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md), [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md)), of Meta's code, of PyTorch's documentation of `F.silu` and of the C standard, each with its source named.
  - **This record's own**, every other sentence: the kind and member names, the precision and the accuracy bound, the domain of the bound, the output rounding, the prototype and symbol, the guarantees (no in-place call among them), the value sets, the op_signature records, the call-site name and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 257 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: SwiGLU, SiLU, swish, sigmoid, activation, gate (with "gated", "gating"), feed-forward, feed forward, FFN, MLP, exp (as a word, with "expf" and "exponential"), 활성화, 게이트, bf16, bfloat16, rounding, round, 반올림, in-place, in place, transcendental, libm, `-lm`, `math.h`. Found, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "Llama-3 architecture: hidden 2048, intermediate 8192, 16 heads / 8 KV heads, head_dim 64, vocab 128,256, RoPE, SwiGLU, GQA", "gate/up (2048→8192), down (8192→2048)" and "dtype **fp32** (bf16 weights upcast)". It names SwiGLU as part of the architecture and the gate/up shapes; it says nothing of how the activation is computed, its precision or its rounding.
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16." It names no kind.
  - **Ordinary words only**: "gate", "gated" and "gating" (33 hits; 32 apart from K1's "gate/up") and "게이트" (16) name the HIL gates of FR-4, OD-3, the CI and review gates and the promotion gate; "round" (64 hits as a word) is the round of the loop; "MLP" (1, #7) is a cost model of an autotuner; "활성화" (1, #4) is the activation of a fork model. None of them is about the feed-forward, an activation function or numeric rounding.
  - **Nothing found** on SiLU, swish, sigmoid, an exponential, a feed-forward or FFN computation, bfloat16, rounding, in-place calls or the math library in any of the four issues.
  - **Conflicts**: K1 is the first case, which stays (ADR-0154 decision 2); K2 is answered by HQ-0065, which puts fp16 after P2-14. No owner sentence conflicts with a choice of this record.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `3a13f24`). **HQ-0033** (the ADR-0116 flags `-std=gnu11 -O2 -ffp-contract=off` and the trailing `-lm`, for the first case): no flag is chosen. Unlike the add of ADR-0159, this operation has multiplies and a transcendental function: contraction can fuse a multiply with an add inside a kernel's own exponential (a polynomial evaluated by Horner's rule, for one) and so change binary32 results at their last bits, which is small against the bound of decision 4 for a kernel not designed at its edge; flags that relax IEEE arithmetic (`-ffast-math` and its parts) can reassociate, assume finite values or let a compiler substitute an approximation of `expf` or of a division, whose error the bound may or may not absorb. Whether a build setting makes a kernel break decision 4 is a matter of the build settings (Boundaries); a kernel that calls `expf` needs the math library at link time, which ADR-0116 decision 4 provides for the first case and which is a build setting for these kernels (decision 9). **HQ-0034** (OpenMP on `cpu_standin`): not chosen (decision 9). **HQ-0069** (runtime acceptance (lxvii) of the model executor): no runtime fact is used; the call-site name of decision 12 is an input to a later code slice, not a claim about a live run. The other open HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0021 to HQ-0024, HQ-0026 to HQ-0031, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **Not changed**: no schema file, member, file, version or validator of the data plane. `swiglu` with its members `m` and `n` is a new kind, which ADR-0001 decision 6 admits without raising `schema_version`; `bf16` and `row_major` are existing values. It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-6 sub-question 1, the contract of (`swiglu`, `bf16`, `row_major`, `c`) on `cpu_standin`; of OD-31 sub-question 1, the SwiGLU activation kind's contract, op_signatures and call-site name; of sub-question 2, the precision of the exponential, the SiLU and the product, and the rounding of the output conversion; of sub-question 3, the value sets of the SwiGLU verification inputs. Open of them: Boundaries.
- It builds on ADR-0001 (decisions 2 and 6), ADR-0008 (decisions 1 to 8), ADR-0037, ADR-0116 (decision 4), ADR-0152 (decisions 2, 5 and 7), ADR-0153 (decisions 3 and 4), ADR-0154 (decisions 2 and 3), ADR-0156 (decisions 2 to 5 and 9), ADR-0157 (decision 4), ADR-0158 (decisions 3, 5, 7 and 8) and ADR-0159 (decisions 3, 4, 6, 8, 11 and 13); none of them is edited. **If ADR-0008 or ADR-0156 is reverted, this record is revisited with it.** The format follows the "Record format" section of ADR-0001.

## Context

- **Meta's reference** (cited), `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py`: `FeedForward.__init__` (lines 205-222) computes the hidden width (lines 214-218) and builds three projections without bias, `w1` and `w3` from `dim` to `hidden_dim` and `w2` back (lines 220-222); `FeedForward.forward` (lines 224-225) is `return self.w2(F.silu(self.w1(x)) * self.w3(x))`. `TransformerBlock` holds it as `self.feed_forward` (line 235) and calls it on `self.ffn_norm(h)` (line 253).
- **The definition of SiLU** (cited): PyTorch's docstring of `torch.nn.functional.silu` (`torch/nn/functional.py` at tag `v2.5.0`, lines 2358-2364): "Apply the Sigmoid Linear Unit (SiLU) function, element-wise", "silu(x) = x * σ(x), where σ(x) is the logistic sigmoid". Only this definition is used; how PyTorch evaluates it was not read.
- **The call** (ADR-0152 decisions 2 and 5): row 12, "SwiGLU activation: silu(gate) · up, elementwise", once per layer, with "two T × 8192 inputs (gate, up) → T × 8192; T ∈ {1, 32, 512}"; the intermediate width 8192 is derived in ADR-0152 Context from the lines above. ADR-0152 Alternatives keep it as its own kernel: inside the gate/up GEMM it would be fusion (later, C-6), and ADR-0008 decision 3 makes `gemm` the plain product. ADR-0152 decision 7 leaves to this kind's record whether a kernel must accept other shapes.
- **The owner's answers** (ADR-0154 decisions 2 and 3): bf16 inputs and outputs; fp32 accumulation for three named sums, of which this operation has none, and "Every other intermediate precision is not settled by the answer", "the SiLU of the SwiGLU activation" among the examples, each belonging "to its kind's contract record"; `uint16_t` bit patterns at the boundary with the kernel converting; a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; each kind's input distribution fixed by a driver record, finite inputs only.
- **The executor** (ADR-0153 decision 3) binds a kernel by its contract's prototype and operand entries, accepts a binding "for every shape" only where the contract obliges correctness at every shape, and keeps "distinct arrays for each operand" among the caller's guarantees; it owns every array of a generation (decision 4). ADR-0157 decision 4 keeps `bf16` out of a generation's range while a call-site kind lacks a bf16 contract.
- **The C standard** (cited: ISO C11 committee draft N1570, 5.2.4.2.2 paragraph 6): "The accuracy of the floating-point operations (+, -, *, /) and of the library functions in <math.h> and <complex.h> that return floating-point results is implementation-defined [...]. The implementation may state that the accuracy is unknown." So no C library's `expf` has an accuracy the standard guarantees.

## Decision

A sentence marked **owner** renders an HQ `decision` through ADR-0154. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **One contract**: the SwiGLU activation of ADR-0152 row 12 for kind `swiglu`, dtype `bf16`, layout `row_major` and kernel language `c`, **on `cpu_standin`** (ADR-0154 decision 2 fixes the `uint16_t` boundary for that target). It binds both sides as ADR-0008 decision 1 says: the caller guarantees what decision 8 lists, and a kernel does what decisions 4, 5, 8 and 9 list, for coder output and hand-written kernels alike. **No fp32 or fp16 contract of this kind is defined.**
- Where a point says "as ADR-0008", "as ADR-0156" or "as ADR-0159", that text applies with its kind, symbol and operands read as this record's, and nothing else changes.

### 2. Kind and shape members

- **Kind `swiglu`**; it matches the name pattern `[a-z][a-z0-9_]{0,31}` of `hilclaw.keys` and names the operation, not its place in the model (ADR-0001 decision 2). **It is the gated activation only**: the three projections of Meta's `FeedForward` are `gemm` calls (ADR-0152 rows 11 and 13), and the kind has no weight operand. A later plain SiLU would be another kind (`silu`), and so would another gated activation (another gate function, or the product in another order).
- **Shape members `m` and `n`, exactly these two**: `m` = T, the number of rows (tokens); `n` = the intermediate width of each row (8192 for Llama 3.2 1B). `m` is the `m` of `gemm`, `rmsnorm` and `elementwise_add` at the same T; `n` is the output width `n` of the gate and up projections (whose results are the two inputs) and the inner dimension `k` of the down projection (whose input is the output). By ADR-0001 decision 6 this kind and its members raise no `schema_version`.
- **Every operand has the same shape `[m, n]`**: no broadcasting, no rank-1 operand.

### 3. Dtype and layout

- **Dtype `bf16`** for all three operands, as ADR-0156 decision 2 (the owner's bf16 inputs and outputs).
- **Layout `row_major`**, as ADR-0008 decision 2 with "the C type of its dtype" read as ADR-0156 decision 2 reads it: each element is one `uint16_t` holding a bf16 bit pattern, element (i, j) at index i·n + j, contiguous, no padding, no stride, no header. As in ADR-0159 decision 3, element (i, j) of each operand is at the same index, and a kernel may treat each as one array of m·n elements.

### 4. The operation and its precision

- **The operation** (Meta's line 225 with the definition of Context): out(i, j) = silu(gate(i, j)) · up(i, j), with silu(x) = x · σ(x) = x / (1 + e^−x), for 0 ≤ i < m, 0 ≤ j < n. **`gate` is the operand of `F.silu`, Meta's `self.w1(x)`; `up` is the other factor, `self.w3(x)`.** Write g, u and y for gate(i, j), up(i, j) and the exact real value silu(g) · u.
- **The kernel converts its inputs** (**owner**, HQ-0065 (3)); widening bf16 to binary32 is exact (ADR-0154 decision 3).
- **Every intermediate value is held in binary32 or a wider binary format, never a narrower one**: the exponential, 1 + e^−g (or any other form of σ), the SiLU value, the product with u and whatever association of these the kernel uses (g · u first, then the division, is allowed). **No value is rounded to bf16 or another 16-bit format before the output conversion of decision 5.**
- **The accuracy bound: the value v that the kernel converts to bf16 has |v − y| ≤ 2^−11 · |y|** for every pair (g, u) of the domain D below. v is the kernel's last binary32 or wider value; a kernel that computes wider than binary32 may round to binary32 as its last step, and then that binary32 value is v. **The method of each step is the kernel's choice**: `expf` or `exp` of the C library, a polynomial or table approximation in SIMD lanes, a division or a reciprocal, in any association, provided v meets the bound. One bound on v, rather than one per step, is the only form that does not depend on the association.
  - **What it asks of the exponential**: for example, the evaluation g · u / (1 + t) with correctly rounded binary32 operations, where t approximates e^−g with a relative error of at most 2^−12, has a relative error of at most (1 + 2^−24)² / ((1 − 2^−12)(1 − 2^−24)) − 1, which is below 2^−12 + 5 · 2^−24 and so below 2^−11 (computed with exact rational arithmetic): an error in t enters 1 + t with the factor t / (1 + t) < 1, and each of the three operations adds a relative 2^−24 at most, as g · u and 1 + t are normal binary32 values in D (below) and the quotient is close to y. So a library `expf` or a polynomial approximation qualifies when its relative error stays within 2^−12 over D — at least 2^11 units in the last place of binary32 —, and an estimate coarser than that (a bit trick without refinement) does not. **The contract names no library as qualifying**: the C standard leaves the accuracy of `expf` implementation-defined (Context), so a kernel that calls `expf` meets the bound where its library's accuracy gives it, a fact about that library and not about this contract.
  - **The domain D**: g = ±0 or 2^−62 ≤ |g| ≤ 126 · ln 2 (about 87.34; the largest such bf16 value is 87); u = ±0 or 2^−62 ≤ |u| ≤ 2^62; and y = 0 or |y| ≥ 2^−126. Reasons: |g| ≤ 126 · ln 2 holds exactly when e^−g and e^g both lie in [2^−126, 2^126], so either form of σ is formed from a normal binary32 exponential and none overflows; the bounds on u and g keep every non-zero product g · u in [2^−124, 2^69), inside the normal binary32 range, and |y| ≤ 87.34 · 2^62 < 2^69; and the last condition excludes results below the normal range. When g or u is zero, y = 0 and the bound makes v = 0. Inputs outside D — very large or very small magnitudes, subnormals, non-finite values — are not covered (Boundaries).
- **Why not a correctly rounded result, as ADR-0159 decision 4 obliges for the add.** There a binary32 add gave the correctly rounded bf16 value for free, by a double-rounding argument. Here y is irrational for every non-zero g and u (if y were rational, e^−g = g · u / y − 1 would be rational, which the Lindemann–Weierstrass theorem excludes for a non-zero rational g), so it is never a tie, but it can lie arbitrarily close to one. A correctly rounded result would need an exponential accurate far beyond binary32 near every such case, a cost on every element for a difference of at most one bf16 unit in the last place at the elements that lie near a rounding boundary; the SIMD approximations a kernel is optimised with would be excluded. ADR-0158 decision 3 faced the same choice for the reciprocal square root and chose a bound; this record does the same.
- **Why 2^−11**: it is a quarter of the smallest relative half unit in the last place of bf16 (2^−9), the reason of ADR-0158 decision 3, so the kernel's error stays well below the output rounding, while an unbounded method could add error of the size of the bf16 rounding refused above. A bound near binary32 accuracy would exclude the fast approximations for no difference visible after the bf16 rounding. Kernels may still differ at the last bf16 bit of an element near a rounding boundary (decision 10 computes how often for its value sets), as ADR-0156 decision 3 and ADR-0158 decision 3 accept.
- **Compared with Meta** (line 225): in a bf16 model, `F.silu(self.w1(x))` is read here as a bf16 tensor and the product with `self.w3(x)` as another, so Meta's order rounds to bf16 twice — the SiLU value and the product. **This contract drops the first rounding** and keeps only that of the output. **This departs from Meta's order of roundings**, as ADR-0158 decision 3 does for RMSNorm, for its reasons: the owner's "입출력은 bf16" names inputs and outputs, and the SiLU value is neither; the reference is float64 without bf16 emulation (**owner**, HQ-0066 (1)), so a second rounding is error counted against every kernel of the contract; and a rounding left to the kernel would make a tolerance mean different things for kernels of one contract. On the value sets of decision 10 the two orders differ by exactly one bf16 unit in the last place on 27.0 % of the pairs and nowhere by more (computed there). If PyTorch held the SiLU value wider than bf16, Meta's order would have one rounding, as here; how PyTorch evaluates `silu` and the product was not read and is not relied on. Whether the model-level comparison needs Meta's order is OD-31 sub-question 6 (owner). Listed in the owner notice.
- **How close a result must be is the tolerance** (FR-9; **owner**, HQ-0066 (2), no value here). The verification compares within the instance's `rtol` and `atol` only and does not test the bound, which stands either way.

### 5. The conversion of the output to bf16

- **The contract fixes it: round to nearest, ties to even**, from v to bf16, for the reasons of ADR-0156 decision 4, which carry over unchanged (cited). A kernel that computes wider than binary32 and rounds to binary32 before the conversion converts that binary32 value, which is then its v (decision 4).
- **Zero**: y = 0 exactly when g or u is zero, and then the output is a zero; its sign is not fixed by this contract, and the comparison with `rtol` and `atol` does not see it.
- **Range**: in D, |y| < 2^69, so no output overflows, and a non-zero y is at least 2^−126, so by the bound a non-zero output rounds to a normal bf16 value (a v within a relative 2^−11 below 2^−126 rounds to 2^−126). For the inputs of decision 10 every exact output has a magnitude in [0.00138, 7.935] (computed), so no output overflows, vanishes or is subnormal. Outside D, an output that overflows is an infinity of its sign as roundTiesToEven defines overflow (as ADR-0156 decision 4); subnormal inputs and outputs and what a kernel produces from non-finite inputs are not defined here (Boundaries).

### 6. The C prototype and the symbol

```c
void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte, in every spec of this contract whatever the shape: single spaces as shown, no line break, the semicolon included. `size_t` is that of `<stddef.h>`, `uint16_t` that of `<stdint.h>`; valid in C99 and later.
- **Order**: dimensions first as ADR-0008 decision 4, then the arrays in the order input `gate`, input `up`, output `out` — the order of Meta's `F.silu(self.w1(x)) * self.w3(x)`; `void`, since the result is the output only; `restrict` on all three states the no-overlap guarantee of decision 8. **The names say the roles**, because, unlike the add of ADR-0159, the operation is not symmetric in its inputs: a call that swaps them computes something else (decision 10).
- **Operand type `uint16_t`** (**owner**, HQ-0065 (3)).
- **Symbol `hilclaw_swiglu_bf16`**: `hilclaw_`, the kind, `_` and the dtype — the form of ADR-0156 decision 5, ADR-0158 decision 5 and ADR-0159 decision 6, for their reasons (a wrong binding fails at `dlsym`, and kernels of several dtypes may share a link unit if contracts of other dtypes come). This record sets no naming rule for other kinds.

### 7. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `gate` | `input` | `bf16` | `[m, n]` | `const uint16_t *restrict gate` |
| `up` | `input` | `bf16` | `[m, n]` | `const uint16_t *restrict up` |
| `out` | `output` | `bf16` | `[m, n]` | `uint16_t *restrict out` |

As ADR-0008 decision 5: in parameter order, with the values of the spec's `op_signature` shape in place of `m` and `n`; the dimensions have no entry. The complete `task.contract` at T = 1:

```json
{
  "language": "c",
  "prototype": "void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);",
  "operands": [
    {"name": "gate", "role": "input", "dtype": "bf16", "shape": [1, 8192]},
    {"name": "up", "role": "input", "dtype": "bf16", "shape": [1, 8192]},
    {"name": "out", "role": "output", "dtype": "bf16", "shape": [1, 8192]}
  ]
}
```

**Validated on 2026-10-24** with `hilclaw.spec.validate`, inside the committed spec example `examples/spec/gemm-485b9bc494d477eb.json` with its op_signature replaced by the T = 1 record of decision 11 (key and record) and its `task.contract` by the object above, in a throwaway interpreter that added `"swiglu": frozenset({"m", "n"})` to `hilclaw.keys._SHAPE_MEMBERS` in memory: accepted; the same spec with the shape of `up` changed to `[1, 8193]` was refused (`task.contract.operands[1].shape[1]: must be a value of task.op_signature.record.shape, got 8193`). No repository file was changed.

### 8. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | `m` and `n` are each at least 1; `gate`, `up` and `out` have exactly m·n elements each. | Compute the operation for the values it is called with. |
| Overlap | The three arrays do not overlap each other; in particular `out` is neither `gate` nor `up` (no in-place call). | — |
| Inputs | Every element of `gate` and `up` is an initialised `uint16_t` holding a bf16 bit pattern, stored in the layout of decision 3, and nobody else changes them during the call. | Not modify them. |
| Output | The content of `out` on entry is unspecified. | Not read `out` before writing it, and write **every** one of its m·n elements, each the bf16 pattern of decisions 4 and 5, before it returns. |
| Alignment | Each pointer is aligned for `uint16_t`. Nothing more is promised. | Not assume a larger alignment. |
| Memory, repeated calls, completion, result | As ADR-0008 decision 6. | As ADR-0008 decision 6. |

- **No in-place call.** In the pass neither input is read after row 12 (ADR-0152 decision 2: the gate and up results are read by row 12 only), so writing the result over `gate` would be safe. It is refused for the reasons of ADR-0159 decision 8: (1) `restrict` on every operand, which lets a compiler vectorise without overlap checks, would be lost for one kind; (2) ADR-0153 decision 3 lists "distinct arrays for each operand" among the caller's guarantees, and an in-place permission would make the executor's rule differ by kind; (3) ADR-0158 decision 7 and ADR-0159 decision 8 refuse it already. Unlike the add, it costs one more buffer of T × 8192 bf16 values, 8 MiB (8,388,608 bytes) at T = 512, allocated once for the generation and shared by all layers (ADR-0153 decision 4); no copy is made.
- **Every set of dimensions**: the obligation is stated for the values passed, so **a kernel must be correct for every m, n ≥ 1**, and may be specialised for its own shape only while staying correct elsewhere. A binding "for every shape" of ADR-0153 decision 3 is therefore accepted for this contract. Whether a verification passes other values stays OD-16 sub-question 1.
- **No shape that holds a 0**: the caller's guarantee of at least 1 has the form of ADR-0008's, so ADR-0037's reading carries over — this contract defines no `task.contract` and no call for a shape with a 0.
- **Finiteness** is not part of the input guarantee, as in ADR-0008 decision 6; inputs outside D (decision 4) are Boundaries.

### 9. What the kernel source provides

- As ADR-0008 decision 7 with the name of decision 6: **exactly one definition of `hilclaw_swiglu_bf16`**, with external linkage and the prototype of decision 6; **no `main`**; no other identifier with external linkage that starts with `hilclaw_` (`hilclaw_gemm`, `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16` and `hilclaw_elementwise_add_bf16` included).
- It may include the headers ADR-0008 decision 7 allows; `<math.h>` is among them as part of the C standard library (as ADR-0158 decision 8), so a kernel may call `expf`. That a build links the math library — ADR-0116 decision 4 puts `-lm` among the trailing flags of the first case — and whether OpenMP is usable on `cpu_standin` (HQ-0034) are build settings of these kernels (Boundaries).

### 10. The input value sets of verification

- **Owner** (HQ-0066 (3)): each kind's input distribution is fixed by a driver record, finite inputs only. **This record fixes the value sets; the rest is the P2-12 harness record's.**
- **gate**: every drawn element is **exactly one of the 1024 bf16 values of magnitude in [0.5, 8) with either sign** (bit patterns 0x3F00 to 0x40FF and 0xBF00 to 0xC0FF; largest magnitude 7.96875). **up**: every drawn element is **exactly one of the 256 bf16 values of magnitude in [0.5, 1) with either sign**, ±(0.5 + j/256) for j = 0 … 127, the set of ADR-0156 decision 9.
- **Why gate is wider.** σ is nearly linear on ±[0.5, 1): a kernel that replaced σ(x) by its tangent line at 0, 1/2 + x/4, would stay within a relative 6.95 % of the reference there, but leaves it by at least 2^−6 for 903 of the 1024 gate values above (computed). The upper edge 8 is where, for positive gates, SiLU comes within the bound of its asymptote g: σ(−8) ≈ 3.35 · 10^−4 < 2^−11, so for g ≥ 8 silu(g) is within a relative 2^−11 of g. The lower edge is that of the shared set; magnitudes below 0.5 add nothing distinctive (silu(x) ≈ x/2 there) and lead toward zero, a corner case. **Why up keeps the shared set**: it enters by one multiply, which the set exercises with both signs, and one harness generator then draws one of the two operands from the set it already has for ADR-0156, ADR-0158 and ADR-0159.
- **Computed facts** (over all 262144 pairs, on 2026-10-24, with Python's `decimal` at 50 significant digits for the exact values, exact rational arithmetic for the bf16 roundings, and NumPy 2.5.2 for the reference): every pair lies in D; every exact output has a magnitude in [0.00138, 7.935], so none is zero, subnormal or overflowing; the silu values lie in [−0.2785, 7.966]. **The reference** g / (1 + e^−g) · u in NumPy float64 has a relative error of at most 3.2 · 10^−16 (about 2^−51.5) against the exact value, far below every bf16 effect here. **A correctly rounded output** differs from the exact value by a relative 0.00389 at most; **any output a kernel meeting decision 4 may give** (a value within a relative 2^−11 of y, rounded) by 0.00437 at most, and on 47242 pairs (18.0 %) y lies within a relative 2^−11 of a rounding boundary, so two such kernels may give neighbouring bf16 values there.
- **What the set detects**, as the share of pairs on which the wrong result differs from y by a relative 2^−6 or more (about 3.6 times the 0.00437 above): a missing SiLU (g · u) or a ReLU in its place, 88.1 % each — on every pair with a negative gate the first is off by at least a relative 1.64 and the second, which gives 0, by exactly 1, and only large positive gates, where SiLU approaches g, are close; a sigmoid in place of SiLU (σ(g) · u), 99.4 % (it coincides with SiLU at g = 1); σ(−g) in place of σ(g), a sign error in the exponent, 100 %, by at least a relative 0.39; swapped `gate` and `up` (silu(u) · g), 98.2 %, and equal where the two drawn values are equal (256 of the pairs). A result written to the wrong element or read from the wrong row gives a different value unless the drawn values coincide there, which depends on the draws (P2-12). Whether these displacements exceed `atol` + `rtol`·|ref| depends on the instance's tolerance and is not promised (as ADR-0156 decision 9).
- **The intermediate bf16 rounding of Meta's order** (decision 4) gives an output different from the correctly rounded one on 70670 pairs (27.0 %), by exactly one bf16 unit in the last place each, with a relative error of up to 0.00726; on 16370 pairs (6.2 %) its error exceeds the 0.00437 any kernel meeting decision 4 may reach. So it is detected only under a tolerance the user sets between those two values, and not otherwise; the obligation of decision 4 stands either way. **Truncation in place of the rounding of decision 5** differs from the correctly rounded output on 130910 pairs (49.9 %), with a relative error of up to 0.00774, above 0.00437 on 52186 pairs (19.9 %): likewise detected only under a tolerance between those values. **The bound itself is not detected**: an output error is the bound's error plus the rounding's, and a kernel slightly outside 2^−11 cannot be told apart from one inside it by any `rtol` and `atol` on these sets.
- **Left to the P2-12 harness record**: the generator, its seed, the number of draws, whether `gate` and `up` are drawn independently, the content of `out` before the call, and the widening for the float64 reference — the inputs (**owner**, HQ-0066 (1)) and the output (cited: ADR-0154 decision 3). **No tolerance value or default is chosen** (**owner**, HQ-0066 (2)).

### 11. The `op_signature` records

**Rule**: `{"schema_version": 1, "kind": "swiglu", "shape": {"m": T, "n": 8192}, "dtype": "bf16", "layout": "row_major"}` for T ∈ {1, 32, 512}, the shape set of row 12 (ADR-0152 decision 5); **all layers share these records**, since the key names the operation and not its place. At T = 1:

```
{"dtype":"bf16","kind":"swiglu","layout":"row_major","schema_version":1,"shape":{"m":1,"n":8192}}
sha256 = 7b82bc7d69cda1e0fd3794adbe3bce2274830ff1c53b3c20997ae095e352dc29  ->  swiglu-7b82bc7d69cda1e0
```

| T | 1 | 32 | 512 |
|---|---|---|---|
| Directory name | `swiglu-7b82bc7d69cda1e0` | `swiglu-ee76c0d3e36f20f7` | `swiglu-a1d727f15ac574e0` |

- **Method**: `hilclaw.keys.op_signature_key` in the throwaway interpreter of decision 7 (kind added in memory, no repository change). The same interpreter gave `elementwise_add-1af54bf2a0744c69` for the `elementwise_add` record at T = 1, the name of ADR-0159 decision 11.
- **How a shape set maps to instances** stays OD-6 sub-question 3. **Change of the contract**: ADR-0008 decision 8 holds as for fp32 (a storage change is a new `layout` value; any other change is OD-6 sub-question 4).

### 12. The call site

- **`ffn_activation`** for row 12. Reason: Meta gives the expression no module of its own; it is the activation inside `feed_forward` (line 235), so it takes the prefix Meta uses for the norm before that module (`ffn_norm`, line 243), which `hilclaw/model_binding.py` already uses for `ffn_norm` and `ffn_residual`. It is distinct from every GEMM (`qkv`, `o`, `gate`, `up`, `down`, `lm_head`), RMSNorm (`attention_norm`, `ffn_norm`, `norm`) and elementwise add (`attention_residual`, `ffn_residual`) call-site name there.
- **The operands the call passes**:

| Call site | `gate` | `up` | `out` |
|---|---|---|---|
| `ffn_activation` (row 12) | the output `c` of the GEMM call site `gate` of the same layer (row 11; Meta's `self.w1(x)`) | the output `c` of the GEMM call site `up` of the same layer (row 11; Meta's `self.w3(x)`) | read as the input `a` of the GEMM call site `down` of the same layer (row 13; Meta's `self.w2(...)`) |

- That the GEMM call site `gate` is the projection whose result enters SiLU follows ADR-0152 row 12 ("silu(gate) · up"); its weight is Meta's `w1`, and that of `up` is `w3`. How those weights reach the executor is OD-31 sub-question 5 (owner).

### 13. Order and runs

This record chooses no order of kinds, no instance and no run, as ADR-0159 decision 13: when a SwiGLU activation instance runs is not said here, and B-4's run order ("GEMM first, then the attention family") stands (ADR-0152 Boundaries).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Kind `swiglu_activation` (ADR-0152's phrase) or `silu_mul` | The suffix adds nothing once the kind is stated to be the gated activation without projections; `silu_mul` names the arithmetic but not the gate-and-up structure the call sites rely on. Either would work. |
| 2 | One member `n` = T·8192 over flat operands | Loses T, which every other kind of a layer carries in `m`, and the executor's T × 8192 buffers would need a second shape convention. |
| 4 | Correctly rounded output, as ADR-0159 decision 4 | Needs an exponential far more accurate than binary32 near every near-tie, excludes SIMD approximations, and buys at most one bf16 unit in the last place at some elements (decision 4). |
| 4 | Binary32 accuracy for the exponential (a few units in the last place), or exactly the C library's `expf` | The difference does not survive the bf16 rounding; a fixed library has no accuracy the C standard guarantees (Context), and fast approximations would be excluded for nothing. |
| 4 | No bound, binary32 or wider only | Admits crude estimates whose error is of the size of the bf16 rounding this record refuses for the SiLU value. |
| 4 | Keep Meta's bf16 rounding of the SiLU value | A second rounding counted against every kernel by the float64 reference, of no input or output the owner names (decision 4). |
| 5 | Truncation, or the rounding left to the kernel | The reasons of ADR-0156 decision 4 (cited). |
| 6 | Operand names `a`, `b`, `c` (ADR-0008, ADR-0159) or `x`, `y` | The inputs are not interchangeable; the names `gate` and `up` carry their roles into the prototype and the operand entries, where a swap would otherwise be invisible. |
| 6 | Symbol `hilclaw_swiglu` | Gives up the load-time stop of ADR-0156 decision 5 if a contract of another dtype comes. |
| 8 | Allow `out` = `gate` (in-place), without `restrict` | Saves one buffer of 8 MiB at T = 512, but loses `restrict` for one kind and makes the executor's "distinct arrays" rule (ADR-0153 decision 3) differ by kind (decision 8). |
| 10 | Both operands from ±[0.5, 1), the shared set | Leaves the exponential's tails untested: a tangent-line σ would stay within 6.95 % (decision 10). |
| 10 | gate over a wider range (for example ±[0.5, 128)) or the whole finite bf16 range | Beyond 8, positive gates give silu(g) within the bound of g and negative ones tiny outputs; wider still reaches the edges of D, overflow and subnormal outputs, corner cases kept for later (#5 B-7, OD-16). |
| 12 | `swiglu`, `ffn_swiglu` or `silu_up` | `swiglu` repeats the kind; `ffn_activation` follows the `ffn_` prefix of the neighbouring call sites and names the place, as call-site names do. |

## Consequences

- **A-13 reading**: no schema file, member, file, version or validator of the data plane changes, and `hilclaw/` is not touched. The new kind `swiglu` with members `m` and `n` is a value ADR-0001 decision 6 admits without a version change. Teaching `hilclaw.keys` the kind is a later code slice.
- **The code slice this record makes possible** (for the planner; no code here): the kind and its members in `hilclaw.keys`; a contract module like `hilclaw/elementwise_add_bf16_contract.py` (constants, `task_contract`, `covers`, `op_signature_record`, the two value sets); the binding check in `hilclaw/model_binding.py` with the call site `ffn_activation` of decision 12, its shape (rows × intermediate) and the "every shape" binding, `bf16` as the only dtype at which the kind is known; hand-written bf16 SwiGLU kernels as test fixtures (one meeting decision 4, and for the harness wrong ones whose error the value sets make large, such as a missing SiLU, a sigmoid or swapped operands, which fail under a tolerance tighter than that error); and the P2-12 harness part (generator over the two value sets, widening, comparison).
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` for "SwiGLU", "other three kinds", "other four kinds", "other five kinds", "future contract records" and "Each kind's contract"; not claimed complete): ADR-0152 decision 1's naming bullet ("each kind's value, `op_signature` members and contract are later records"), decision 7, Consequences (the planner's next steps) and Boundaries ("Each kind's contract"); ADR-0153 decision 3 ("future contract records"), decision 6 ("each kind's contract"), Consequences code slice (2) ("the other five kinds") and Boundaries ("Each kind's contract"); ADR-0154 decision 2 ("the SiLU of the SwiGLU activation" among the unsettled precisions), Consequences ("What is now unblocked") and Boundaries ("Each kind's contract"); ADR-0156 Boundaries ("the other five kinds"); ADR-0157 decisions 4 and 5 and Boundaries ("the other five kinds"); ADR-0158 Boundaries ("the other four kinds"); ADR-0159 Boundaries ("the other three kinds"). This record now answers them for the SwiGLU activation.
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: no correctly rounded result but binary32 or wider intermediates with a relative error of at most 2^−11 before the output rounding, over the domain D, with no library's `expf` named as qualifying (decision 4); the departure from Meta's order — no bf16 rounding of the SiLU value —, one bf16 unit in the last place on 27.0 % of the verification pairs (decisions 4 and 10); no in-place call, at the cost of one more buffer (decision 8); the kind name `swiglu`, the members `m`, `n` and the operand names `gate`, `up`, `out` (decisions 2 and 6); the call-site name `ffn_activation` and its operands (decision 12); gate drawn from ±[0.5, 8) and up from ±[0.5, 1) (decision 10).
- **UsageCases and StandardScenarios** (S0 and S1 re-checked, and every scenario row citing OD-6 sub-question 1 or OD-31): no use case step changes. S0 step 4 keeps its open kernel contracts outside `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and C, its note now naming `swiglu` (OD-6 sub-question 1, OD-31 sub-question 1); S0 step 5 and S1 step 2 keep OD-31 sub-question 3 and #5 B-7 for the vocabulary outside the first case and the Llama kinds on `cpu_standin`. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **fp16**: when and in what form, after PLAN P2-14 (owner, HQ-0065 (1)); **an fp32 contract of this kind**, which ADR-0157 decision 4 would need for an fp32 full pass.
- **Tolerance values**: instance parameters set by the user (FR-9; owner, HQ-0066 (2), no default).
- **Build settings and OpenMP**: compiler flags, `-ffp-contract`, flags that relax IEEE arithmetic, linking the math library (`-lm`) for these kernels, the floating-point environment (flushing subnormals included), OpenMP and thread count (HQ-0033, HQ-0034, OD-6 sub-question 2).
- **The harness mechanism** of a bf16 SwiGLU verification and timing run, and the parts of decision 10 left to it (PLAN P2-12).
- **Corner-case, non-finite and subnormal inputs and outputs**, and every input outside the domain D of decision 4 (#5 B-7, OD-16).
- **Shapes outside an instance's** (OD-16 sub-question 1); **how a shape set maps to instances** (OD-6 sub-question 3); **contract change and keys** (OD-6 sub-question 4).
- **Fusion** of the activation with the gate/up GEMM or with the down GEMM (later, C-6).
- **The contracts of the other two kinds** — RoPE and SDPA with KV cache — one record each, and their symbol names.
- **Backends other than `cpu_standin`** and their representation of bf16 (#5 B-2, B-7).
- **The weights and their conversion to bf16** (OD-31 sub-question 5, owner); the model-level comparison (sub-question 6, owner).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, PLAN P1-5), to ADR-0156, ADR-0158 or ADR-0159.

## References

- Owner: HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1), C-6 revision (K2); [Requirements](../Requirements.md) C-6, FR-5, FR-9, OD-6, OD-16, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6 (sub-questions 1 to 4) and § OD-31 (sub-questions 1 to 3, 5, 6).
- Records: [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 2 and 6; record format), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md), [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md), [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md).
- Meta: `meta-llama/llama-models` at `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` (lines 205-225, 235, 243, 253), read through `gh api`.
- PyTorch: `pytorch/pytorch` at tag `v2.5.0`, `torch/nn/functional.py` lines 2358-2364 (the docstring of `silu`), read through `gh api`.
- C: ISO C11 committee draft N1570, 5.2.4.2.2 paragraph 6.
- Code read: `hilclaw/keys.py`, `hilclaw/spec.py` (`validate`), `hilclaw/elementwise_add_bf16_contract.py`, `hilclaw/model_binding.py`; `examples/spec/gemm-485b9bc494d477eb.json`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
