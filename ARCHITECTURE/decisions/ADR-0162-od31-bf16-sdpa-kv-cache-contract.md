# ADR-0162: Operational contract of SDPA with KV cache of Llama 3.2 1B in bf16 for C kernels on `cpu_standin` — one kind `sdpa_kv_cache` for prefill and decode with shape members `m`, `l`, `h`, `h_kv` and `d`, two position-major bf16 cache operands of which the kernel sees the first `l` rows and writes the last `m` as exact copies, no capacity in the key or the prototype, the `repeat_kv` head mapping, the scale 1/√d, the causal rule, an error bound over a stated domain with binary32 softmax-sum accumulators and no 16-bit probabilities, a round-to-nearest-even output read by the O projection without a copy, the entry point `hilclaw_sdpa_kv_cache_bf16`, the value sets of the verification inputs, the op_signature records of the ADR-0154 SDPA row and the call site `sdpa` (extension of OD-6 sub-question 1; part of OD-31 sub-questions 1 to 3)

## Status

- **Accepted on 2026-10-25.** It defines the sixth and last Llama kind contract of PLAN P2-11.
- **Three kinds of content.**
  - **Owner answers**, marked **owner**: the `decision` of HQ-0064, HQ-0065 and HQ-0066 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records them. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0002](ADR-0002-od6-codegen-spec.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md), [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md), [ADR-0160](ADR-0160-od31-bf16-swiglu-contract.md), [ADR-0161](ADR-0161-od31-bf16-rope-contract.md)) and of Meta's code, each with its source named.
  - **This record's own**, every other sentence: the kind and member names, the cache operands and their layout, the precision obligation and its bound, the output rounding, the prototype and symbol, the guarantees, the value sets, the op_signature records, the call-site name and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 260 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: SDPA, attention, KV cache, cache, softmax, causal, mask, GQA, repeat_kv, scale, sqrt, seq_len, max_seq_len, capacity, decode, prefill, bf16, bfloat16, rounding, 반올림, 캐시, 어텐션. Found, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "**Attention family boundary**: **KV cache included**; attention configuration (GQA 16/8, head_dim 64, RoPE, causal) **follows Llama 3.2 1B**"; "Second spec (attention family): decode-step and prefill SDPA with KV cache (seq_len ∈ {128, 2048}), single layer, from the same model"; nntrainer's idioms "(… softmax_row, rotary)"; "dtype **fp32** (bf16 weights upcast)". It puts the cache in the family, makes the mask causal and the configuration Llama's, and gives the lengths; it says nothing of the cache's dtype, layout or capacity, the scale, the precision or the rounding. Its head counts read 32 and 32/8 (**owner**, HQ-0064).
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16." It names no kind.
  - **K3** — the A-6 decision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693): "Lossy techniques (quantization, approximate ops, KV-cache compression) therefore remain admissible *within the tolerance the user set*". It is about the techniques a run may use; it says nothing of a kernel contract (decision 4 relates the two).
  - **K4** — the record of B-4's first answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402): "owner stated that **both GEMM and the attention family** are needed". It sets the scope that K1 then fixes; it says nothing of a contract.
  - **Ordinary words only**: "attention", "softmax" and "capacity" in the B-4 and A-4 question texts of the #5 body; "scale" (large-scale serving) and "capacity" (serving capacity) in https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136238336; "cache" as token usage in https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290608368; "캐시" in #4 and #8 (the agent-memory cache, cached reference snapshots, build caches, timing loops); "KV-cache" as serving literature and "capacity" as serving capacity in #7.
  - **Nothing found** on a mask's form, `repeat_kv`, sqrt, max_seq_len, bfloat16, rounding, 반올림 or 어텐션.
  - **Conflicts**: K1's fp32 is the first case, which stays, and K2 is answered by HQ-0065 (ADR-0154 decision 2). No owner sentence conflicts with a choice of this record; K3 is listed for the owner (Consequences).
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `6fe2a3b`). **HQ-0033** (the ADR-0116 flags `-std=gnu11 -O2 -ffp-contract=off` and the trailing `-lm`, for the first case): no flag is chosen. Contraction into fused multiply-adds removes roundings and so keeps the bound of decision 7, whose argument counts each rounding once; flags that relax IEEE arithmetic (`-ffast-math` and its parts) can replace `expf`, the division and the max by approximations, flush subnormals or reassociate, which the bound absorbs where the result still meets it and which is a build setting outside it (Boundaries). **HQ-0034** (OpenMP on every C-7 system): answered (a) on 2026-10-25 and not yet reflected in ADR-0116; this record depends neither on OpenMP nor on threads (threads stay allowed as ADR-0008 decision 6). **HQ-0069** (runtime acceptance (lxvii) of the model executor): no runtime fact is used. **HQ-0070** (the RoPE scale factor): it shapes the RoPE table, not this kernel's operation, whose inputs are rotated rows whatever the factor. The other open HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0021 to HQ-0024, HQ-0026 to HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **Not changed**: no schema file, member, file, version or validator of the data plane. `sdpa_kv_cache` with its members is a new kind, which ADR-0001 decision 6 admits without raising `schema_version`; `bf16`, `row_major` and the role `inout` (ADR-0002) are existing values. It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-6 sub-question 1, the contract of (`sdpa_kv_cache`, `bf16`, `row_major`, `c`) on `cpu_standin`; of OD-31 sub-question 1, the SDPA kind's contract, op_signatures and call-site name; of sub-question 2, the precision of both dot products, the scores, the probabilities and the cast between them, and the rounding of the output; of sub-question 3, the value sets of the SDPA verification inputs. Open of them: Boundaries.
- It builds on ADR-0001 (decisions 2 and 6), ADR-0002 (the operand roles), ADR-0008 (decisions 1, 2 and 4 to 8), ADR-0037, ADR-0152 (decisions 1 to 3 and 7; Alternatives), ADR-0153 (decisions 3 and 4), ADR-0154 (decisions 1 to 3), ADR-0156 (decisions 2 to 5 and 9), ADR-0157 (decision 4), ADR-0158 (decisions 3 and 5), ADR-0159 (decision 13), ADR-0160 (decisions 4 and 9) and ADR-0161 (decisions 3, 6, 10 and 15); none of them is edited. The format follows the "Record format" section of ADR-0001.

## Context

- **Meta's reference** (cited), `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py`, read through `gh api`:
  - `repeat_kv` (lines 96-105): `x[:, :, :, None, :].expand(bs, slen, n_kv_heads, n_rep, head_dim).reshape(bs, slen, n_kv_heads * n_rep, head_dim)`; `Attention.__init__`: `self.n_rep = self.n_local_heads // self.n_local_kv_heads` (line 115), `self.head_dim = args.dim // args.n_heads` (line 116), `self.cache_k` and `self.cache_v` = `torch.zeros((args.max_batch_size, args.max_seq_len, self.n_local_kv_heads, self.head_dim))` (lines 147-162).
  - `Attention.forward` (lines 164-202): `self.cache_k = self.cache_k.to(xq)` and the same for `cache_v` (lines 180-181); `self.cache_k[:bsz, start_pos : start_pos + seqlen] = xk` and `… = xv` (lines 183-184); `keys` and `values` = the cache `[:bsz, : start_pos + seqlen]` (lines 186-187), passed through `repeat_kv` (lines 190-191); `scores = torch.matmul(xq, keys.transpose(2, 3)) / math.sqrt(self.head_dim)` (line 196); `scores = scores + mask` if a mask is given (lines 197-198); `scores = F.softmax(scores.float(), dim=-1).type_as(xq)` (line 199); `output = torch.matmul(scores, values)` (line 200); `output.transpose(1, 2).contiguous().view(bsz, seqlen, -1)` before `self.wo` (lines 201-202).
  - `Transformer.forward` (lines 287-303): `mask = None`; if `seqlen > 1`, `torch.triu` of a `(seqlen, seqlen)` matrix of `-inf` with `diagonal=1`, joined after `torch.zeros((seqlen, start_pos))`; its comment says "the only masked entries are (i, j) for j > cache_len + i, since row i corresponds to token cache_len + i" (lines 299-302).
  - `models/sku_list.py`, `llama3_2_1b`: `"dim": 2048`, `"n_heads": 32`, `"n_kv_heads": 8` (lines 334-337).
- **The call and its shapes** (cited): rows 6 and 7 of ADR-0152 decision 2 are one SDPA kernel that takes the cache as an operand it updates, writes the new K and V rows at P … P+T−1 and attends over 0 … L−1, with L = P + T (decisions 1 and 3); ADR-0154 decision 1's SDPA row: prefill T = S, P = 0, L = S; a decode step T = 1, P = S − 1, L = S; S ∈ {128, 2048}; Q T × 32 × 64, new K and V T × 8 × 64, a cache of 8 × 64 per position, output T × 2048, causal. ADR-0153 decision 4 gives the cache buffers to the model program and leaves "its capacity, its layout and how the kernel is told the capacity" to this contract. ADR-0161 decision 15: `rope_q` and `rope_k` write contiguous `out` arrays that this call reads.
- **The owner's answers** (ADR-0154 decisions 2 and 3): bf16 inputs and outputs as `uint16_t` patterns, the kernel converting; fp32 accumulation for the softmax sum; the two dot products, the scaling, the precision of scores and probabilities and the cast between them left to this record; a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; finite inputs fixed by a driver record.

## Decision

A sentence marked **owner** renders an HQ `decision` through ADR-0154. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **One contract**: SDPA with KV cache, rows 6 and 7 of ADR-0152 decision 2, for kind `sdpa_kv_cache`, dtype `bf16`, layout `row_major` and kernel language `c`, **on `cpu_standin`**. It binds both sides as ADR-0008 decision 1 says, and the model program's cache buffers as far as decision 4 says. **No fp32 or fp16 contract of this kind is defined.** "As ADR-0008" (or another record) means that text with this record's kind, symbol and operands.

### 2. One kind for prefill and decode

- **One kind; m tells the calls apart.** Meta computes both in one `Attention.forward` (lines 164-202). Meta builds no mask at T = 1, and the causal rule of decision 6 gives the same set there: row 0 at position P attends 0 … P = L − 1, every row. Its binding check has one entry form for the one call site. The instance targets are the four op_signatures of decision 14 with one kind or two. One rule also covers a prefill after cached tokens and any prompt length (ADR-0152 decision 7) without a third kind.

### 3. Kind and shape members

- **Kind `sdpa_kv_cache`**; it matches `[a-z][a-z0-9_]{0,31}` and names the operation, the cache upkeep included (ADR-0001 decision 2; ADR-0152 decision 3), not its place. **Shape members `m`, `l`, `h`, `h_kv` and `d`, exactly these**: `m` = T, the new tokens (the `m` of the other kinds); `l` = L, the positions attended; `h` = the query heads (32); `h_kv` = the KV heads (8); `d` = head_dim (64). By ADR-0001 decision 6 they raise no `schema_version`.
- **L is a member, P is neither member nor parameter.** The work is m·l products of length d per query head for each of the two dot products, so cost and best kernel depend on L, and L is B-4's seq_len (ADR-0152 Alternatives line 129); unlike RoPE's position (ADR-0161 decision 3), it is not a value that leaves the work unchanged. P = l − m is fixed by the two, so a member or parameter P would only add a value that can contradict them.
- **The capacity is neither a member nor a parameter** (decision 4): the kernel needs none, and a member would split identical work over keys by buffer size.
- **The scale is a contract constant, 1/√d** (Meta's line 196 divides by `math.sqrt(self.head_dim)`). ADR-0158 decision 5 made `eps` a parameter because it is a model value no member fixes; the scale follows from `d`, so a parameter could only contradict it and a member would repeat `d`. A model with another scale needs another contract (Boundaries).

### 4. The cache operands

- **Two operands, `cache_k` and `cache_v`**, as Meta's two tensors (lines 147-162). K enters the score product and V the value product; one joined array would need an interleaving convention for nothing.
- **Dtype `bf16`.** This record reads ADR-0154 decision 2's "inputs and outputs are bf16" as covering the cache, which is both. Meta casts the cache to `xq`'s dtype (lines 180-181). The rows written are already bf16 (decision 5), so a bf16 cache holds them exactly, and a wider one would double the bytes for nothing.
- **Layout: position-major `[l, h_kv, d]`**, rank 3 as ADR-0161 decision 6 defines it, element (t, g, e) at index (t·h_kv + g)·d + e: Meta's `cache_k` at batch 1 (lines 147-154).
- **Capacity.** The model program holds per layer two buffers of C ≥ l rows of h_kv·d elements (ADR-0153 decision 4); **the operand is the first l rows**, and the pointer passed is the buffer's start. Position-major rows sit at the same index whatever C is, so **the kernel is told nothing about C**; the caller guarantees C ≥ P + T = l, and the kernel accesses no row at or past l (ADR-0008 decision 6, "Memory"). Head-major `[h_kv, C, d]` would need C as a stride, a value of no key or operand entry (ADR-0161 decision 6). **No capacity value is chosen** (Boundaries).
- **What the kernel writes**: row P + i of `cache_k` becomes row i of `k_new` and row P + i of `cache_v` row i of `v_new`, for i = 0 … m − 1, **bit for bit**, as Meta's lines 183-184 copy. **What it leaves**: rows 0 … P − 1 unchanged; nothing past row l − 1 is read or written. **What it may assume**: rows 0 … P − 1 hold the bf16 patterns that earlier calls of the same layer wrote, or the verification placed, unchanged by others during the call; the content of rows P … l − 1 on entry is unspecified.
- **Why exact copies**: the cache is read by later calls of other instances — a prefill kernel and a decode kernel are different op_signatures — and by the model program, so its format is the contract's. K3's KV-cache compression is therefore not open to a kernel of this contract; a compressed cache is another `dtype` or `layout` value, another contract and key (ADR-0008 decision 2), as quantisation is for `gemm`. Listed in the owner notice.

### 5. The other operands

- Each element is a `uint16_t` bf16 pattern as ADR-0156 decision 2; each array rank 3, `row_major` as ADR-0161 decision 6.
- **`q`: `[m, h, d]`**, the `out` of `rope_q`, and **`k_new`: `[m, h_kv, d]`**, the `out` of `rope_k` (ADR-0161 decision 15), read as they are.
- **`v_new`: `[m, h_kv, d]`, a contiguous copy of the V range of the QKV output made by the model program** (ADR-0153 decision 4). Reasons, those of ADR-0161 decision 6: `row_major` has no stride, a row-stride parameter has no value in the key or the operand entries, and the copy is T × 512 bf16 values per layer, 2 MiB at T = 2048.
- **`out`: `[m, h, d]`**: element (i, j, e) at i·h·d + j·d + e, the order Meta's `transpose(1, 2).contiguous().view(bsz, seqlen, -1)` gives (line 201). As memory it is the `[m, h·d]` = T × 2048 matrix of ADR-0008 decision 2, so **the GEMM call site `o` reads it as its `a` operand without a copy**.

### 6. The operation

For token i = 0 … m − 1 at position P + i, query head j = 0 … h − 1 and e = 0 … d − 1, after the write of decision 4 (K and V the caches):

- **GQA**: query head j uses KV head **g = ⌊j / (h / h_kv)⌋**. Meta's `repeat_kv` repeats each KV head n_rep = h / h_kv times in a row (lines 96-105, 115), so heads 0 … 3 use KV head 0 and heads 28 … 31 KV head 7.
- **Scores**: s(t) = (1/√d) · Σ over e of q(i, j, e)·K(t, g, e), the scale after the product as Meta's line 196; for d = 64 it is 1/8 = 2^−3.
- **Causal rule**: row i attends the positions **t = 0 … P + i**, those Meta's mask leaves (lines 299-302); at T = 1 this is every position (decision 2).
- **Softmax** over the attended t: p(t) = e^{s(t)} / Σ over attended t' of e^{s(t')} (line 199).
- **Value product**: y(i, j, e) = Σ over attended t of p(t)·V(t, g, e) (line 200); out(i, j, e) is the bf16 value that decisions 7 and 8 give for it.

### 7. Precision

- **The kernel converts its inputs** (**owner**, HQ-0065 (3)); widening is exact.
- **The softmax sum is accumulated in fp32** (**owner**, HQ-0065 (2)), read as ADR-0156 decision 3 reads the GEMM sum: every partial sum of the denominator held between steps is binary32, neither narrower nor wider, in any order. Multiplying a partial sum by a factor, as a blocked online softmax rescales it, keeps it binary32 and is allowed.
- **Every other value is binary32 or wider, and no value is rounded to a 16-bit format before the output conversion** — neither the scores nor the probabilities. **This departs from Meta's order of roundings**: line 199 rounds the probabilities to `xq`'s dtype with `type_as` before the value product. Reasons, those of ADR-0158 decision 3 and ADR-0160 decision 4: the owner's "입출력은 bf16" names inputs and outputs, and the probabilities are neither; the reference is float64 without bf16 emulation (**owner**, HQ-0066 (1)), so the rounding is error counted against every kernel. On the value sets of decision 13, rounding the probabilities to bf16 changes the round-to-nearest-even output on 41.9 %, 42.5 %, 42.1 % and 43.1 % of the elements at prefill S = 128, decode S = 128, prefill S = 2048 and decode S = 2048, and puts the result outside the bound below, with each element's own A, on 52.3 %, 31.2 %, 5.3 % and 0.0 % (computed: softmax in float64, the probabilities then rounded to bf16). Whether Meta holds the score product in bf16 depends on how PyTorch evaluates `matmul`, which was not read and is not relied on. Whether the model-level comparison needs Meta's order is OD-31 sub-question 6 (owner). Listed in the owner notice.
- **The obligation: the value v the kernel converts has |v − y| ≤ ε(n, A, d) · Σ over attended t of p(t)·|V(t, g, e)|**, over the domain D below, where n = P + i + 1 is the number of attended positions, A the largest a(t) = (1/√d)·Σ over e of |q(i, j, e)·K(t, g, e)| over them, u = 2^−24, γ_k = k·u / (1 − k·u), α = (1 + 2^−14)·exp((γ_{d+1} + 2u(1 + γ_{d+1}))·A) − 1 and **ε = (1 + α)(1 + γ_n)(1 + u) / ((1 − α)(1 − γ_n)) − 1**; to first order ε ≈ 2^−13 + 2^−23·(n + (d + 3)·A). **The method is the kernel's**: the max subtracted (or another offset), the exponential, the order of every sum, a blocked online softmax, a division or a reciprocal, where the scale is applied, fused multiply-adds. The right side is relative to the terms, not to y, because y cancels (decision 13).
- **D**: every element of `q`, `k_new`, `v_new` and of cache rows 0 … P − 1 is ±0 or of magnitude in [2^−30, 2^30]; A ≤ 16; l + d ≤ 2^20. It is the reach of the argument below, not a capacity or a sequence length; outside it no bound is defined (Boundaries).
- **The argument** — a straightforward evaluation meets the bound: binary32 dot products (products of bf16 values exact), multiplied by the binary32 value nearest to 1/√d or divided by the one nearest to √d; the row max μ subtracted; an exponential with relative error at most 2^−14 on [−33, 0]; binary32 sums in any order; then either the sums Σ ê(t)·V divided by the denominator, or each ê(t) divided first. By the standard bound for a sum of k terms in any order (each term carries a factor 1 + θ with |θ| ≤ γ_{k−1}), the score has an error of at most γ_{d+1}·a(t) ≤ γ_{d+1}·A; the subtraction adds at most u·|ŝ − μ| ≤ 2u(1 + γ_{d+1})·A to the exponent, which lies in [−33, 0]; so each computed ê(t) is e^{s(t) − μ}·(1 + α_t) with |α_t| ≤ α. The value sum carries 1 + θ with |θ| ≤ γ_n, the denominator 1 + θ' with |θ'| ≤ γ_{n−1} ≤ γ_n, the division one more u. Then v = Σ p(t)·V(t)·R_t, where R_t is (1 + α_t)(1 + θ_t)(1 + δ) over a p-weighted mean of (1 + α_t')(1 + θ'_t'), so |R_t − 1| ≤ ε and |v − y| ≤ ε·Σ p(t)·|V(t)|. In D every rounded product and quotient is normal (a nonzero scaled score at least 2^−84, ê ≥ e^−33, an attended weight above 2^−68, a nonzero value at least 2^−30, a nonzero numerator at least 2^−101 over a denominator at most 2^20), an addition whose result is subnormal is exact, and nothing overflows. A fused multiply-add only removes a rounding. A blocked online softmax adds to each α_t the error of the rescaling factors it passes through, so whether it meets the bound depends on its exponential and number of rescalings, the kernel's to show. So a library `expf` serves this evaluation where its relative error stays within 2^−14 on [−33, 0], at least 2^9 units in the last place of binary32; **the contract names no library**, the C standard leaving that accuracy implementation-defined (ADR-0160 decision 4).
- **Values** (computed, Python `decimal` at 60 digits; d = 64): ε = 2.01·10^−4 at n = 128 and 4.30·10^−4 at n = 2048 for A = 8, the bound on the value sets of decision 13; 2.65·10^−4 and 4.94·10^−4 (≈ 2^−11) for A = 16. At L = 2048 that is about a quarter of the smallest relative half unit in the last place of bf16 (2^−9), the reason of ADR-0158 decision 3 for 2^−11, but relative to Σ p·|V|, not to |y|: where y cancels the bound allows more than a bf16 unit of y (decision 13). The term in n is the worst case of binary32 sums in any order, so ε grows with longer rows.
- **Why a bound**: a correctly rounded result needs an exponential far beyond binary32 near rounding boundaries (ADR-0160 decision 4's reason); "binary32 or wider" alone (ADR-0158 decision 3) would leave the exponential and the L-term sums unstated, and a test could not rely on it. One bound on v does not depend on the association, so it admits blocked and online orders, the method attention kernels are optimised with, instead of leaving them to a later record.
- **How close a result must be is the tolerance** (FR-9; **owner**, HQ-0066 (2), no value here). The verification does not test the bound, which stands either way.

### 8. The output conversion

- **Round to nearest, ties to even**, from v to bf16, as ADR-0156 decision 4 (cited). The cache writes are copies and convert nothing. **Range**: y is a p-weighted mean of values, so |y| ≤ max |V(t, g, e)| ≤ 2^30 in D and nothing overflows. y = 0 exactly only if, for each distinct score, the values at that score sum to 0 (the scores are algebraic, and the exponentials of distinct algebraic numbers are linearly independent over the algebraic numbers — Lindemann–Weierstrass), for example two equal scores with opposite values; the sign of a zero is not fixed. On the draws of decision 13 every exact output lies in [6.7·10^−9, 0.9961] in magnitude (computed), none zero, subnormal or overflowing. Subnormal and non-finite values are not defined here (Boundaries).

### 9. The C prototype and the symbol

```c
void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte, in every spec of this contract: single spaces, no line break, the semicolon included; valid in C99 and later. **Order**: the dimensions first, in the order of decision 3, as ADR-0008 decision 4 — no position, capacity or stride exists (decisions 3 and 4) — then `q`, `k_new`, `v_new` in Meta's order (line 172), the caches (lines 147, 155) and `out`; `void`; `restrict` on all six (decision 11). `uint16_t` is the **owner**'s (HQ-0065 (3)).
- **Symbol `hilclaw_sdpa_kv_cache_bf16`**, the form of ADR-0156 decision 5 for its reasons.

### 10. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `q` | `input` | `bf16` | `[m, h, d]` | `const uint16_t *restrict q` |
| `k_new` | `input` | `bf16` | `[m, h_kv, d]` | `const uint16_t *restrict k_new` |
| `v_new` | `input` | `bf16` | `[m, h_kv, d]` | `const uint16_t *restrict v_new` |
| `cache_k` | `inout` | `bf16` | `[l, h_kv, d]` | `uint16_t *restrict cache_k` |
| `cache_v` | `inout` | `bf16` | `[l, h_kv, d]` | `uint16_t *restrict cache_v` |
| `out` | `output` | `bf16` | `[m, h, d]` | `uint16_t *restrict out` |

As ADR-0008 decision 5. **The caches take the role `inout`**, the value ADR-0002 gives `role` for an operand both read and written; the shape is that of the operand, the first l rows, never the capacity, so the vocabulary needs no change. The complete `task.contract` at the decode step T = 1, L = 128:

```json
{
  "language": "c",
  "prototype": "void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);",
  "operands": [
    {"name": "q", "role": "input", "dtype": "bf16", "shape": [1, 32, 64]},
    {"name": "k_new", "role": "input", "dtype": "bf16", "shape": [1, 8, 64]},
    {"name": "v_new", "role": "input", "dtype": "bf16", "shape": [1, 8, 64]},
    {"name": "cache_k", "role": "inout", "dtype": "bf16", "shape": [128, 8, 64]},
    {"name": "cache_v", "role": "inout", "dtype": "bf16", "shape": [128, 8, 64]},
    {"name": "out", "role": "output", "dtype": "bf16", "shape": [1, 32, 64]}
  ]
}
```

**Validated on 2026-10-25**, as ADR-0161 decision 10, with `hilclaw.spec.validate`, inside `examples/spec/gemm-485b9bc494d477eb.json` with its op_signature replaced by the T = 1, L = 128 record of decision 14 and its `task.contract` by the object above, in a throwaway interpreter that added `"sdpa_kv_cache": frozenset({"m", "l", "h", "h_kv", "d"})` to `hilclaw.keys._SHAPE_MEMBERS` in memory: accepted; with the shape of `cache_k` set to a capacity `[256, 8, 64]` it was refused (`task.contract.operands[3].shape[0]: must be a value of task.op_signature.record.shape, got 256`). No repository file was changed.

### 11. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | m ≥ 1, l ≥ m, h_kv ≥ 1, h a multiple of h_kv, d ≥ 1; `q` and `out` have m·h·d elements, `k_new` and `v_new` m·h_kv·d, `cache_k` and `cache_v` l·h_kv·d (the first l rows of buffers of at least l rows). | Compute the operation of decision 6 with P = l − m for the values it is called with. |
| Overlap | The six arrays do not overlap; in particular `k_new` and `v_new` are not rows of the caches. | — |
| Inputs | `q`, `k_new`, `v_new` and cache rows 0 … P − 1 hold initialised bf16 patterns in the layouts of decisions 4 and 5, unchanged by others during the call. | Not modify them. |
| Cache rows P … l − 1 | Their content on entry is unspecified. | Not read them before writing them; write them as decision 4 says. |
| Output | The content of `out` on entry is unspecified. | Not read `out` before writing it; write every element, each the bf16 pattern of decisions 7 and 8. |
| Alignment | Each pointer is aligned for `uint16_t`. | Not assume more. |
| Memory, repeated calls, completion | As ADR-0008 decision 6. | As ADR-0008 decision 6, cache rows 0 … P − 1 being inputs of this call although earlier calls wrote them; nothing past row l − 1 of a cache is accessed. |
| Result | The content of `out` and of cache rows P … l − 1 after the return is the result. | As ADR-0008 decision 6, with those two in place of `c`. |

- **Aliasing**: the caches are updated in place, which is one `inout` operand read and written, not two operands sharing memory; ADR-0153 decision 3's "distinct arrays for each operand" holds as written, and `restrict` on every operand states it. Letting `rope_k` write straight into the cache row that `k_new` would then be is refused: it makes `k_new` overlap `cache_k`, saves one T × 512 copy per layer, and breaks `restrict` and ADR-0153 decision 3.
- **Every set of dimensions** (above): the obligation is stated for the values passed, so **a binding "for every shape" of ADR-0153 decision 3 is accepted**, with the numeric bound where D holds. Whether a verification passes other values stays OD-16 sub-question 1. **No shape with a 0**, as ADR-0037; P = 0 is a position, not a dimension. **Finiteness** is not in the input guarantee (ADR-0008 decision 6); inputs outside D and the content of cache rows not written by this contract's kernels are the caller's (Boundaries).

### 12. What the kernel source provides

- As ADR-0008 decision 7: exactly one definition of `hilclaw_sdpa_kv_cache_bf16`, no `main`, no other external `hilclaw_` identifier (`hilclaw_gemm`, `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16`, `hilclaw_swiglu_bf16` and `hilclaw_rope_bf16` included). `<math.h>` and `expf` as ADR-0160 decision 9 (cited); linking the math library is a build setting.

### 13. The input value sets of verification

- **Owner** (HQ-0066 (3)): fixed here; the rest is the P2-12 harness record's.
- **Every element of `q`, `k_new`, `v_new` and of cache rows 0 … P − 1** (decode steps) is one of the 256 bf16 values of magnitude in [0.5, 1) with either sign, the set of ADR-0156 decision 9. Reasons: finite, exact, never zero; A < 8 (each |q·K| < 1, 64 terms, scale 1/8), inside D, so every score lies in (−8, 8) and e^{s − μ} > e^−16 ≈ 1.1·10^−7: no weight underflows to zero; the float64 reference computes every score exactly (products are multiples of 2^−16 below 1 in magnitude, 64 of them fit 53 bits); signed values make a wrong weight move y by much of its size.
- **Computed facts** (NumPy 2.5.2, `default_rng(0)`, one draw per shape, each element chosen uniformly from the set; prefill S = 128, decode S = 128, prefill S = 2048, decode S = 2048): largest A 5.18, 5.13, 5.40, 5.14; smallest e^{s − μ} 5.8·10^−3, 3.0·10^−2, 4.1·10^−3, 1.2·10^−2; |y| in [3.8·10^−7, 0.9961], [2.3·10^−5, 0.2923], [6.7·10^−9, 0.9961], [4.0·10^−5, 0.0616]. **The reference** differs from Python `decimal` at 50 digits by at most 7.9·10^−17·Σ p·|V| (decode S = 2048, heads 0, 5 and 31, all 64 columns). **Cancellation**: the median of Σ p·|V| / |y| is 9.0, 13.5, 35.5 and 55.5, so a compliant output — from RNE(y − e) to RNE(y + e), e the bound of decision 7 with each element's own A — may differ from y by more than a relative 2^−8 on 35.6 %, 49.7 %, 86.9 % and 100 % of the elements; a NumPy float32 evaluation used at most 0.0016 of the bound. What an `rtol` alone accepts therefore depends on the tolerance the user sets.
- **What the set detects**, as the share of elements where the wrong result differs from y by a relative 2^−6 or more, over the four shapes: query head j served by KV head j mod 8, 87.0 % to 87.3 % (heads 0, 10, 21 and 31 map to the same KV head either way and are never detected); no scale, 99.0 % to 100 %; the scale applied twice, 97.1 % to 98.3 %; one future position attended in prefill, 97.2 % (S = 128) and 79.2 % (S = 2048); no mask in prefill, 97.9 % and 98.4 %; the newest position left out in a decode step, 98.0 % and 66.3 %; scores q(t)·k(i) in place of q(i)·k(t) in prefill, 97.6 % and 98.7 %; no normalisation, 99.2 % to 100 %. **Through the cache, not the output**: the written rows are exact copies, so comparing rows P … l − 1 with `k_new` and `v_new` needs no tolerance and catches a write at wrong positions or none; the output alone misses a kernel that attends from `k_new` while writing wrongly. Attention over rows past l shows only through what the harness places there. Both are P2-12's. Meta's probability rounding (decision 7) and the bound itself are detected only under a tolerance tight enough.
- **Left to P2-12**: generator, seed, draws, the content of cache rows P … l − 1 and of `out` before the call, any guard rows past l, the cache comparison, the widening. **No tolerance value or default** (**owner**, HQ-0066 (2)).

### 14. The `op_signature` records

**Rule**: `{"schema_version": 1, "kind": "sdpa_kv_cache", "shape": {"m": T, "l": L, "h": 32, "h_kv": 8, "d": 64}, "dtype": "bf16", "layout": "row_major"}` for the (T, L) of ADR-0154 decision 1; **all 16 layers share them**. At T = 1, L = 128:

```
{"dtype":"bf16","kind":"sdpa_kv_cache","layout":"row_major","schema_version":1,"shape":{"d":64,"h":32,"h_kv":8,"l":128,"m":1}}
sha256 = 9f8c153fbe19c8ee934d21fd64dd8d20e788b76208c8e0f03b8117a754bb4361  ->  sdpa_kv_cache-9f8c153fbe19c8ee
```

| S | prefill (T = S, P = 0, L = S) | decode step (T = 1, P = S − 1, L = S) |
|---|---|---|
| 128 | `sdpa_kv_cache-3a4be50bca85d0dc` | `sdpa_kv_cache-9f8c153fbe19c8ee` |
| 2048 | `sdpa_kv_cache-e9326c7e4ba5e1c7` | `sdpa_kv_cache-50b3bf3bcc1ad96d` |

- **Method**: `hilclaw.keys.op_signature_key` in the interpreter of decision 10; it gave `rope-c797475e043d4156` for ADR-0161's K record at T = 1. How a shape set maps to instances stays OD-6 sub-question 3; contract change, OD-6 sub-question 4 (ADR-0008 decision 8).

### 15. The call site

- **`sdpa`**, one call per layer for rows 6 and 7. Meta writes these lines inside `Attention.forward` with no name of their own; `attention` is Meta's name of the whole module, whose projections are here the call sites `qkv` and `o`, so it would name more than the call. `sdpa` names the operation, as `rope_q` and `rope_k` follow their kind, and differs from every call-site name in `hilclaw/model_binding.py`.

| Operand | In the pass |
|---|---|
| `q` | the `out` of `rope_q` of the same layer (ADR-0161 decision 15) |
| `k_new` | the `out` of `rope_k` of the same layer |
| `v_new` | the model program's copy of the V range of the output `c` of the GEMM call site `qkv` of the same layer |
| `cache_k`, `cache_v` | the first l rows of that layer's two cache buffers (ADR-0153 decision 4) |
| `out` | read as the operand `a` of the GEMM call site `o` of the same layer, without a copy |

- Over a generation (ADR-0153 decision 4) its shapes are the prefill (m, l) = (prompt length, prompt length) and, for decode pass k, (1, prompt length + k).

### 16. Order and runs

No order of kinds, instance or run is chosen, as ADR-0159 decision 13.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Two kinds, prefill and decode | One rule covers both (Meta's one `forward`); two kinds double the binding forms for the same four op_signatures. |
| 3 | P a member; L a call argument only | P is fixed by m and l; without L the key would merge L = 128 and L = 2048, whose cost differs by a factor of 16 or more. |
| 3, 4 | Capacity as a member or parameter | Position-major rows need none; a member splits identical work by buffer size. |
| 3 | The scale as a `float` parameter | It follows from `d`; a parameter could contradict it. |
| 4 | One joined KV array; head-major caches | An interleaving convention for nothing; head-major needs the capacity as a stride. |
| 4 | An fp32 cache | The rows are bf16 values already; twice the bytes. |
| 5 | Read V in place with a row stride | No stride in `row_major` and no key value for it; the copy is 2 MiB per layer at T = 2048. |
| 7 | Probabilities rounded to bf16, as Meta | Error the float64 reference counts against every kernel; changes 42 % of outputs. |
| 7 | Correctly rounded output; binary32 or wider without a bound | Point 7. |
| 11 | `k_new` written by RoPE into the cache rows | Breaks `restrict` and ADR-0153 decision 3 to save one small copy. |
| 13 | Positive values only for V | No cancellation, but y becomes a weighted mean that wrong weights barely move: the KV-head error is detected at 2^−6 on 2.8 % of elements at decode S = 2048, against 87.1 %. |
| 15 | `attention`, `sdpa_kv_cache` | `attention` names Meta's whole module; the kind name is longer and says no more. |

## Consequences

- **A-13 reading**: no schema file, member, file, version or validator of the data plane changes, and `hilclaw/` is not touched; the new kind and its members are values ADR-0001 decision 6 admits, and `inout` is an existing role.
- **With this record every kind of ADR-0152 decision 2 has a bf16 contract on `cpu_standin`.**
- **The code slices this record makes possible** (for the planner; no code here): the kind and members in `hilclaw.keys` and a contract module (`task_contract`, `covers`, `op_signature_record`, the value set); the binding check in `hilclaw/model_binding.py` with the call site `sdpa`, its (m, l) shapes from (T, P, L) and the "every shape" binding, `bf16` only; the two cache buffers per layer and the V copy in the model program; hand-written kernels as fixtures (one compliant, wrong ones such as the j mod 8 mapping, a missing mask or no cache write); the P2-12 harness part with its cache comparison.
- **Less exact, not edited** (search of `ARCHITECTURE/` for "SDPA", "KV cache", "other two kinds", "the other kinds", "future contract records", "Each kind's contract" and "cache operands"; not claimed complete): ADR-0001 Boundaries (the shape members of the second family, now defined); ADR-0008 Boundaries ("The contract of the SDPA family"); ADR-0152 decision 3 (the strides of Q, K, V and of the SDPA output) and Boundaries ("cache capacity", "Each kind's contract"); ADR-0153 decision 3 ("future contract records") and decision 4 ("the SDPA output for the O projection" among the copies — this contract leaves none; "how the kernel is told the capacity" — it is told nothing); ADR-0154 decision 2 (the intermediate precisions of SDPA left open) and Boundaries; ADR-0156 and ADR-0157 ("the other five kinds"), ADR-0158 ("the other four kinds"), ADR-0159 ("the other three kinds"), ADR-0160 ("the other two kinds") and ADR-0161 decision 15 and Boundaries ("the SDPA record's").
- **Runtime acceptance items**: none.
- **Readings for the owner to check**, listed in the #5 notice: the cache read as bf16 under "입출력은 bf16" (decision 4); position-major caches whose capacity the kernel is never told (decision 4); exact cache copies, so KV-cache compression (K3) is another dtype or layout and contract (decision 4); probabilities kept binary32, departing from Meta's `type_as` (42 % of outputs, decision 7); the error bound over D in place of a correctly rounded result, admitting online softmax (decision 7); the V copy and the uncopied output (decision 5); no `k_new` inside the cache; the names `sdpa_kv_cache`, `m`, `l`, `h`, `h_kv`, `d`, `q`, `k_new`, `v_new`, `cache_k`, `cache_v`, `out`, `sdpa`; the value sets (decision 13).
- **UsageCases and StandardScenarios** (S0 and S1 re-checked, and every scenario row citing OD-6 sub-question 1 or OD-31): no use case step changes. S0 step 4's open kernel contracts are now those outside `gemm`, `rmsnorm`, `elementwise_add`, `swiglu`, `rope`, `sdpa_kv_cache` and C; S0 step 5 and S1 step 2 keep #5 B-7 and OD-31 sub-question 3. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **fp16** (owner, HQ-0065 (1), after P2-14); **an fp32 contract of this kind** (ADR-0157 decision 4).
- **Tolerance values** (FR-9; owner, HQ-0066 (2)).
- **Build settings and OpenMP**: flags, `-ffp-contract`, IEEE-relaxing flags, `-lm`, threads (HQ-0033; HQ-0034's answer and its reflection in ADR-0116; OD-6 sub-question 2).
- **The harness mechanism** and the parts of decision 13 left to it (P2-12).
- **Corner-case, non-finite and subnormal inputs and outputs**, inputs outside D, and the content of cache rows the kernels did not write (#5 B-7, OD-16).
- **Positions, lengths and shapes outside an instance's** (OD-16 sub-question 1, ADR-0152 decision 7); **the capacity value and the longest sequence** (OD-31 sub-question 6, owner); **how a shape set maps to instances** (OD-6 sub-question 3); **contract change and keys** (OD-6 sub-question 4).
- **Fusion** with RoPE or the O projection (later, C-6); **another scale, a compressed or quantised cache, a paged or shared cache, batches above 1**: other contracts.
- **The weights** (OD-31 sub-question 5, owner) and **the model-level comparison** (sub-question 6, owner).
- **Backends other than `cpu_standin`** (#5 B-2, B-7).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, PLAN P1-5) or to ADR-0156, ADR-0158, ADR-0159, ADR-0160 and ADR-0161.

## References

- Owner: HQ-0064 to HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1, K4), C-6 revision (K2), A-6 (K3); [Requirements](../Requirements.md) C-6, FR-5, FR-9, OD-6, OD-16, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6 and § OD-31.
- Records: ADR-0001, ADR-0002, ADR-0008, ADR-0037, ADR-0152, ADR-0153, ADR-0154, ADR-0156, ADR-0157, ADR-0158, ADR-0159, ADR-0160, ADR-0161 (linked in Status).
- Meta: `meta-llama/llama-models` at `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` (lines 96-105, 115-116, 147-202, 287-303), `models/sku_list.py` (lines 334-337), read through `gh api`.
- Code read: `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/rope_bf16_contract.py`, `hilclaw/model_binding.py`; `examples/spec/gemm-485b9bc494d477eb.json`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
