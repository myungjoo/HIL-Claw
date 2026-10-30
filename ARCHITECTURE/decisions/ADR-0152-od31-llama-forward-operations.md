# ADR-0152: The operations of one Llama 3.2 1B forward pass, which of them are single compute-kernel instance targets, and the shape set of each — with the query-head count left to the owner (part of OD-31 sub-question 1)

## Status

- **Accepted on 2026-10-23** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Two kinds of content.** What an owner decision, a requirement, an accepted record or Meta's reference code says is **cited**, with its source named. **Everything else is this record's own**: the list of operations, which of them is an instance target and where the work of the others goes, the shape sets beyond the values the owner gave, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 45 of its 247 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: Llama, 1B, attention, SDPA, RMSNorm, RoPE, rotary, SwiGLU, lm_head, embedding, prefill, decode, seq_len, KV cache, KV, heads, softmax, forward pass, logit. The sentences found that touch the subject, each read for what it says and no further:
  - **K1** — the owner's B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "GEMM first, then the attention family; both are MVP scope"; "Reference sLM = Llama 3.2 1B (Llama-3 architecture: hidden 2048, intermediate 8192, 16 heads / 8 KV heads, head_dim 64, vocab 128,256, RoPE, SwiGLU, GQA)"; "Attention family boundary: KV cache included; attention configuration (GQA 16/8, head_dim 64, RoPE, causal) follows Llama 3.2 1B"; nntrainer is read "for implementation idioms (… softmax_row, rotary)"; "Kernels: the decoder-layer projections of Llama 3.2 1B — gate/up (2048→8192), down (8192→2048), QKV (2048→3072), O (2048→2048). lm_head (2048→128,256) excluded from the first runs (1 GB fp32 weights, seconds per call)"; "M (tokens) ∈ {1, 32, 512} as instance parameter (decode / small batch / prefill)"; "Second spec (attention family): decode-step and prefill SDPA with KV cache (seq_len ∈ {128, 2048}), single layer, from the same model". It says which operations come first and gives their shapes; it does not list the other operations of a forward pass.
  - **K2** — the owner's C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Level: per-op kernels. Each op the model needs is optimised by an instance, and the forward pass runs on those kernels, generates tokens and matches a reference. Graph-level synthesis and fusion stay later." It does not say what counts as an op. The same comment's statement that an instance still optimises a single compute kernel is marked there as the integrator's reading, and its closing note on the head count is a note, not an owner sentence.
  - **K3** — the #5 A-7 decision comment (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402): "owner stated that both GEMM and the attention family are needed". Nothing beyond K1.
  - Not owner answers, read only as context: the B-4 question of the #5 body ("예: GEMM/GEMV, attention 계열, softmax 등"); a #5 comment on tolerance that names "KV-cache compression" as a lossy technique (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693); the #7 research comment on serving capacity and KV-cache memory (https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5566900982). None says how a forward pass splits into kernels. #4 and #8 hold no match.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `f7f3109`). **HQ-0034** (OpenMP on `cpu_standin`) and **HQ-0031** (injected hypotheses): not touched — no build setting and no hypothesis rule is named. **HQ-0032** (the start function's given id, PR #186), **HQ-0048** (selection side), **HQ-0053** (the coder's sign-in), **HQ-0021** and **HQ-0026** (run tools, compiler log): not touched. **HQ-0054** (runtime acceptance of `spec.write`, OD-6) and **HQ-0045** (evaluator, OD-16): not touched — no spec member or harness check is decided. No unresolved HQ is about OD-9 or a #5 B item.
- **Owner-only parts not decided** (DRIVER §9): the query-head count and every other value of B-4 (decision 6); OD-31 sub-questions 2, 3 and 5 to 10; C-6. **No member, file, kind, value or version of the data plane is added or changed**, and no validator changes (Consequences). It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**, of **OD-31 sub-question 1**: the list of operations, the instance targets among them and their shape sets, with the attention shapes written over the head count. Open of it: the head count (owner) and each kind's contract and `op_signature` (the extension of OD-6 sub-question 1). The OD-31 status word changes to partly answered.
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md) (decision 2), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 1, 3, 6) and [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decision 4). The format follows the "Record format" section of ADR-0001.

## Context

- **The goal** (cited, K2; [Requirements](../Requirements.md) C-6): Llama 3.2 1B run end-to-end on per-op kernels, each op optimised by an instance, at bf16/fp16; graph-level synthesis and fusion stay later. The MVP scope is "단일 compute-kernel 최적화" (C-6, owner 2026-05-22); that the instance unit stays a single compute kernel under the revision is the integrator's reading recorded in C-6. OD-31 sub-question 1 asks for the operations and shapes; B-4 gives the starting point (K1).
- **The first kind** (cited): ADR-0008 defines the contract of `gemm` for fp32, `row_major` and C, and says that "another kind, dtype, layout or language has another contract, defined by its own record" (decision 1). It computes the plain product and excludes "accumulation into the output" and "a bias term" (decision 3). Its kernel must "compute the product for the values it is called with" (decision 6), and whether a caller passes values other than those of the `op_signature` is OD-16 sub-question 1.
- **Meta's reference** (cited), read at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301` of `meta-llama/llama-models`:
  - `models/sku_list.py` lines 327-346 (`llama3_2_base_models`), `arch_args` of `llama3_2_1b`: `dim` 2048, `n_layers` 16, `n_heads` 32, `n_kv_heads` 8, `vocab_size` `LLAMA3_VOCAB_SIZE` (128256, line 19), `ffn_dim_multiplier` 1.5, `multiple_of` 256, `norm_eps` 1e-05, `rope_theta` 500000.0, `use_scaled_rope` True.
  - `models/llama3/model.py`: `Transformer.forward` takes token ids and `start_pos`, looks up `tok_embeddings`, runs the 16 `TransformerBlock`s, applies `norm` and the `output` projection to every position, and returns the logits as float. A block computes `h = x + attention(attention_norm(x))` and `out = h + feed_forward(ffn_norm(h))`. `RMSNorm` is `x * rsqrt(mean(x²) + eps) * weight`. `Attention` has three projections `wq` (`dim` → `n_heads·head_dim`), `wk` and `wv` (`dim` → `n_kv_heads·head_dim`), `head_dim = dim // n_heads`; it rotates `xq` and `xk` with `apply_rotary_emb` (adjacent element pairs as complex numbers, frequencies from `precompute_freqs_cis(dim // n_heads, …, rope_theta, use_scaled_rope)` with `apply_scaling`), writes `xk` and `xv` into `cache_k`/`cache_v` at `start_pos … start_pos + seqlen`, repeats the KV heads (`repeat_kv`, GQA), takes `softmax((q·kᵀ)/√head_dim + mask)` in float and multiplies by the values, then applies `wo` (`n_heads·head_dim` → `dim`). The mask is causal over the new positions and absent when `seqlen` is 1. `FeedForward` is `w2(silu(w1(x)) * w3(x))`. No projection has a bias.
  - `models/llama3/args.py`: `ModelArgs` and its asserts (`n_heads % n_kv_heads == 0`, `dim % n_heads == 0`).
  - **Whether Llama 3.2 1B ties `output` to the embedding is not established here**: `model.py` builds `tok_embeddings` and `output` as two modules, and no file read shows whether their weights are equal.
- **The FFN hidden size** (derived from `model.py` and the `arch_args` above): `TransformerBlock` passes `hidden_dim = 4·dim = 8192`; `FeedForward` takes `int(2·8192/3) = 5461`, then `int(1.5·5461) = int(8191.5) = 8191`, then rounds up to a multiple of 256: `256·⌈8191/256⌉ = 256·32 = 8192`. This equals B-4's "intermediate 8192" and its gate/up and down shapes.
- **The head count conflict** (K1 against itself and against Meta). B-4 writes "16 heads / 8 KV heads" and "GQA 16/8", and also "hidden 2048", "head_dim 64" and "QKV (2048→3072)". With head_dim 64, hidden 2048 = 32 × 64, and the QKV width 3072 = 2048 + 2 × 8 × 64 holds for 32 query heads (16 heads would give a query width of 1024). Meta's parameters give `n_heads` 32 and `head_dim = 2048 / 32 = 64`. Choosing between the two changes a value of an owner answer, which only the owner can do (DRIVER §9; OpenDecisionProposals § OD-31 sub-question 1, "확인이 필요하다"). This record does not choose (decision 6).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope and terms

- **One forward pass**: the computation of `Transformer.forward` of Meta's `model.py` for one sequence, from token ids to logits, in two cases: **prefill**, T new tokens with an empty cache (P = 0), and **one decode step**, T = 1 new token with P tokens already in the cache. T is the number of new tokens, P the number cached before the pass, L = P + T the KV length the pass attends over.
- **Batch 1.** K2 says the pass "generates tokens"; reading this as the tokens of one sequence is this record's own, and Meta's batch dimension does not change any operation's form. B-4 calls M = 32 "small batch"; for a projection the M rows are rows whatever their origin, so B-4's set is taken as it stands. Attention over several sequences at once is not in this record.
- **Instance target**: an operation that is one single compute kernel an instance optimises (C-6 and the integrator's reading of its revision, Context). **Not an instance target**: an operation whose work is part of another target's kernel, or work outside the kernels — the model executor's (OD-31 sub-question 4).
- **Kinds are named in plain words** (GEMM, RMSNorm, RoPE, SDPA with KV cache, SwiGLU activation, elementwise add). They are not `kind` values; each kind's value, `op_signature` members and contract are later records (Boundaries).
- **Reading of K2**, this record's own: "each op the model needs" is read as each operation that computes values — arithmetic on activations. Moving rows unchanged (a table lookup, a copy into a cache, a view) is not read as such an op; decision 3 says where each goes.

### 2. The operations of one forward pass

In the order of `model.py`. "×16" is once per layer.

| # | Operation | Where | Instance target? |
|---|---|---|---|
| 1 | Embedding lookup: T token ids → T rows of the 128256 × 2048 table | once | No — executor (decision 3) |
| 2 | RMSNorm before attention (`attention_norm`) | ×16 | **Yes** — RMSNorm |
| 3 | QKV projection: one product 2048 → 3072 | ×16 | **Yes** — GEMM |
| 4 | Split of the QKV output into Q, K and V; head views | ×16 | No — storage convention (decision 3) |
| 5 | RoPE on Q and K at positions P … P+T−1 | ×16 | **Yes** — RoPE |
| 6 | Write of the new K and V rows into the KV cache | ×16 | No — part of the SDPA kernel |
| 7 | Attention: GQA head sharing, scores scaled by 1/√head_dim, causal mask, softmax, product with V, over the L cached positions | ×16 | **Yes** — SDPA with KV cache |
| 8 | O projection: 2048 → 2048 | ×16 | **Yes** — GEMM |
| 9 | Residual add after attention | ×16 | **Yes** — elementwise add |
| 10 | RMSNorm before the feed-forward (`ffn_norm`) | ×16 | **Yes** — RMSNorm |
| 11 | Gate and up projections: two products 2048 → 8192 | ×16 | **Yes** — GEMM (two calls) |
| 12 | SwiGLU activation: silu(gate) · up, elementwise | ×16 | **Yes** — SwiGLU activation |
| 13 | Down projection: 8192 → 2048 | ×16 | **Yes** — GEMM |
| 14 | Residual add after the feed-forward | ×16 | **Yes** — elementwise add |
| 15 | Final RMSNorm (`norm`) | once | **Yes** — RMSNorm |
| 16 | lm_head (`output`): 2048 → 128256 | once | **Yes** — GEMM (decision 4) |
| — | Token selection from the logits (argmax or sampling) | after | No — outside the forward pass (decision 3) |

Six kinds are instance targets: GEMM, RMSNorm, RoPE, SDPA with KV cache, SwiGLU activation and elementwise add. A decode step runs the same list with T = 1.

### 3. Where the work of the others goes

- **Embedding lookup (1)**: a copy of T rows of the weight table, with no arithmetic. Executor work: how the executor does it, and how it handles any operation with no kernel, is OD-31 sub-question 4.
- **QKV split and head views (4)**, and the reshapes and transposes of `model.py` (`view`, `transpose`, `contiguous`, `repeat_kv`): not operations of the list. Q, K and V are column ranges of the one QKV output; the order and strides in which RoPE and SDPA read them, and in which SDPA writes its output for the O projection, are conventions of those kinds' contracts. A copy that a contract leaves is executor work (sub-question 4).
- **KV cache write (6)**: part of the SDPA kernel. The kernel takes the cache as an operand it updates, writes the new K and V rows at positions P … P+T−1, and attends over positions 0 … L−1. This relies on reading B-4's "SDPA with KV cache" and "KV cache included" as putting the cache's upkeep inside the attention family's kernel (Alternatives).
- **GQA head sharing, scaling, causal mask and softmax (7)**: part of the SDPA kernel; they are the definition of scaled dot-product attention as `model.py` computes it (Alternatives for softmax).
- **RMSNorm's weight multiply**: part of the RMSNorm kernel, as in `RMSNorm.forward`.
- **The RoPE frequency table** (`precompute_freqs_cis` with `apply_scaling`): constants of the model, fixed by `head_dim`, `rope_theta` and the scaling. Whether the RoPE kernel takes them as an operand computed outside the kernels or computes them itself is the RoPE contract's; either way it is not a target of its own.
- **Precision steps** of `model.py` (`.float()`, `type_as`): sub-question 2 (owner).
- **Token selection**: it acts on the logits after the forward pass and is a generation setting. It belongs to sub-question 6 (generation, owner) and sub-question 4 (the executor). This record does not decide whether it is a kernel.

### 4. lm_head

- **Reading of the two owner sentences**: B-4 excludes lm_head "from the first runs", for the cost of the fp32 weights (K1); K2 makes the forward pass run on per-op kernels and match a reference, which needs the logits. So **lm_head is in the end-to-end list as a GEMM instance target**, and **B-4's exclusion stands for the first runs**: this record does not put lm_head into them and does not say when its instance runs (the order of kinds is Boundaries).
- **Its rows**: `model.py` applies `output` to all T positions. Whether the executor feeds all T rows or only the last one is open: it depends on what the model-level comparison reads (sub-question 6) and on the executor (sub-question 4). Both are GEMMs 2048 → 128256 with M rows.
- If the weights are tied to the embedding (not established here, Context), the weight's storage for lm_head is a matter of the weights (sub-question 5) and the GEMM contract's layout, not of this list.

### 5. The shape sets

- **Values used**: hidden 2048, intermediate 8192, vocab 128256 and 8 KV heads — stated by B-4 (intermediate also derived above) and equal to Meta's parameters; 16 layers — Meta's `n_layers` (B-4 gives no layer count). **H** (query heads) and **d_h** (head dimension) are **named parameters**: under answer (a) of decision 6 they are 32 and 64. The token set {1, 32, 512} is B-4's for the projections; this record uses it also for RMSNorm, elementwise add and SwiGLU activation, which act on the same T rows, as its own choice. **RoPE is the exception**, also this record's own: it takes the (T, P) of the SDPA calls, because its output is the Q and K those calls read and its result depends on the positions P … P+T−1, which B-4 gives only through seq_len (Alternatives). The seq_len set {128, 2048} is B-4's for SDPA.

| Kind | Call | Shape set | Waits on the head count? |
|---|---|---|---|
| GEMM | QKV | M × 2048 → M × 3072, M ∈ {1, 32, 512} (B-4) | No — B-4's values |
| GEMM | O | M × 2048 → M × 2048, M ∈ {1, 32, 512} (B-4) | No — B-4's values |
| GEMM | gate, up | M × 2048 → M × 8192, M ∈ {1, 32, 512} (B-4) | No |
| GEMM | down | M × 8192 → M × 2048, M ∈ {1, 32, 512} (B-4) | No |
| GEMM | lm_head | M × 2048 → M × 128256; B-4 gives no M for it, this record takes M ∈ {1, 32, 512} | No |
| RMSNorm | 2, 10, 15 | T × 2048, weight of 2048, eps 1e-05 (Meta); T ∈ {1, 32, 512} | No |
| elementwise add | 9, 14 | two T × 2048 inputs; T ∈ {1, 32, 512} | No |
| SwiGLU activation | 12 | two T × 8192 inputs (gate, up) → T × 8192; T ∈ {1, 32, 512} | No |
| RoPE | 5 | Q as T × H × d_h and K as T × 8 × d_h, positions P … P+T−1, `rope_theta` 500000 with Llama 3 scaling (Meta); for prefill (P = 0) T ∈ {128, 2048} and for a decode step T = 1 at P ∈ {127, 2047}, matching the SDPA calls | **Yes** — H, d_h (and the KV-head count, if the answer changes it) |
| SDPA with KV cache | 6, 7 | prefill: T = S, P = 0, L = S; decode step: T = 1, P = S − 1, L = S; S ∈ {128, 2048} (B-4); Q of T × H × d_h, new K and V of T × 8 × d_h, cache of 8 × d_h per position, output T × H·d_h, causal | **Yes** — H, d_h (and the KV-head count, if the answer changes it) |

- **seq_len** of a decode step is read as L, the KV length it attends over, the new token included (Alternatives).
- **The GEMM shapes are B-4's own values**, not derived here from a head count; they equal Meta's under H = 32, d_h = 64.
- How a shape set maps to instances — one instance per shape or one instance over several — is not decided: whether one instance may cover several values of M or several projections is the owner's reading of B-4 that ADR-0031 decision 4 leaves open (OD-6 sub-question 3), and this record makes no reading of it either.

### 6. The head count

- **Not decided.** No shape of this record states H or d_h. The KV-head count 8 is taken as B-4 and Meta state it; an answer may change it too — 16 query heads of 128 with 4 KV heads, for one, keeps hidden 2048, QKV 2048 → 3072 and O 2048 → 2048 — and then the RoPE and SDPA shapes change with it. The RoPE and SDPA shapes wait on the owner's answer; the GEMM, RMSNorm, elementwise add and SwiGLU shapes do not, as long as the answer leaves B-4's hidden, intermediate, QKV and O values as they are.
- The question for the owner is in Consequences. Under answer (a) nothing of this record changes but the substitution H = 32, d_h = 64. Under (b) or (c), this record is revisited with whatever B-4 values the answer changes.

### 7. Shapes the forward pass meets outside these sets

- A real pass meets other values: a prompt of 7 tokens (T = 7 for every kind), a decode step at L = 300, a prefill of 2048 tokens whose projections have M = 2048, the small synthetic models of PLAN P2-13.
- **This record does not decide whether a kernel must accept them.** For fp32 `gemm`, ADR-0008 decision 6 already obliges a kernel to compute the product "for the values it is called with" (cited). For every other kind and dtype it belongs to that kind's contract record (the extension of OD-6 sub-question 1); whether verification draws such shapes is OD-16 sub-question 1; which kernel the executor calls for a shape no instance ran, and what it does when none fits, is OD-31 sub-question 4.

## Alternatives considered

| Choice | Alternative | Why not |
|---|---|---|
| QKV as one GEMM 2048 → 3072 | Three GEMMs (`wq`, `wk`, `wv`, as `model.py`) | B-4 names "QKV (2048→3072)" as one projection with one shape (K1), and ADR-0008 decision 9 keys it so. One product over the joined weight is one compute kernel; it is not graph-level fusion of two operations but one operation with a wider weight. The three-way form remains reachable as three GEMM calls with the same contract and is not excluded for a later reading. |
| Gate and up as two GEMM calls | One GEMM 2048 → 16384 | B-4 gives gate/up one shape, 2048 → 8192, for each. |
| SwiGLU activation as its own kernel | Inside the gate/up GEMM, as an epilogue | That is fusion of two operations, later under C-6; and ADR-0008 decision 3 makes `gemm` the plain product. |
| Softmax inside SDPA | Score GEMM, softmax and value GEMM as three kernels | B-4's second spec is "SDPA with KV cache" as one spec (K1). Splitting it materialises the T × L score matrix between kernels, and softmax alone is not named by B-4 as a kind (its "softmax_row" is an nntrainer idiom to read). |
| KV cache write inside SDPA | A copy by the executor; or a kind of its own | "KV cache included" in the attention family (K1) is read as the cache's upkeep belonging to the family's kernel. A copy outside would leave the SDPA kernel reading a cache it does not maintain, and a separate kind has no arithmetic to optimise. This is the reading this record relies on; if the owner reads B-4 otherwise, only the SDPA operand list changes. |
| RoPE as its own kernel | Inside the SDPA kernel | Inside would fuse a positional transform into attention (C-6, fusion later). B-4 lists RoPE in the attention family's configuration, not in the "Second spec", and names "rotary" apart from "softmax_row" among nntrainer's idioms (K1). Separate, the SDPA kernel reads keys that are already rotated in the cache, as `model.py` stores them. |
| Residual add as its own kernel | Inside the next RMSNorm or as accumulation in a GEMM | The first is fusion (later); the second is excluded for `gemm` by ADR-0008 decision 3 ("accumulation into the output"). Leaving it to the executor would leave an arithmetic op of the model on no instance kernel, against the reading of K2 in decision 1. |
| RoPE shapes = the (T, P) of the SDPA calls | T ∈ {1, 32, 512} as for the other row-wise kinds | RoPE's result depends on the positions, and B-4 gives positions only with the SDPA calls (prefill from 0, decode at seq_len); the token set alone leaves P unstated, so a position set would have to be invented. Taking the SDPA calls also makes each RoPE shape the producer of one SDPA input. Other T and P are decision 7. |
| Embedding lookup outside the kernels | An instance target | It moves rows and computes nothing; there is no compute kernel for an instance to optimise. If the owner reads K2 as covering it, it becomes a target without changing any other row of decision 2. |
| lm_head in the end-to-end list | Left out until a later decision | K2 needs logits computed on kernels; B-4's exclusion names "the first runs" only and is kept. |
| seq_len of a decode step = L, the new token included | L = S + 1 (S cached before the step) | Both are readings of B-4's "decode-step … SDPA with KV cache (seq_len ∈ {128, 2048})"; L = S keeps the decode and prefill calls at the same KV lengths and the stated values as the lengths attended over. A contract may refine it with no change here. |
| Batch 1 | Batch as B-4's "small batch" for M = 32 | The goal is one sequence's tokens; a batched attention is not asked for by any source. For the GEMMs the set is kept as B-4 states it. |
| Attention shapes over H and d_h | Take Meta's 32 or B-4's 16 | Either changes or overrides a value of an owner answer (decision 6). |

## Consequences

- **A-13 reading**: no member, file, kind, value or version of the data plane is added or changed, and no validator changes. The kinds are named in prose; no `kind` value, `op_signature` member, spec member or key is defined, and `hilclaw/` is not touched.
- **The question for the owner** (DRIVER §8 form; the driver records it as a non-blocking HQ, reason `owner-only-decision`):

  > #5 B-4 답변(2026-10-02, https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285)은 Llama 3.2 1B를 "hidden 2048, intermediate 8192, 16 heads / 8 KV heads, head_dim 64"로, attention 구성을 "GQA 16/8"로 적고, 같은 답변의 projection을 QKV 2048→3072, O 2048→2048로 적었습니다. hidden 2048 = head 수 × head_dim 64와 QKV 3072 = 2048 + 2 × 8 × 64는 query head가 32개일 때만 맞습니다(16개면 query 폭이 1024). Meta의 `meta-llama/llama-models`(commit 0e0b8c5) `models/sku_list.py`도 Llama 3.2 1B를 `dim` 2048, `n_heads` 32, `n_kv_heads` 8(head_dim 2048/32 = 64)로 둡니다. ADR-0152(OD-31 ①, 연산 목록과 shape)는 head 수를 정하지 않고 RoPE·SDPA의 shape를 query head 수 H와 head_dim d_h를 매개변수로 남겼습니다. 어느 쪽입니까? (a) query head 32개, KV head 8개, head_dim 64 — Meta 파라미터와 B-4의 나머지 값(hidden 2048, head_dim 64, QKV 2048→3072)이 함께 함의하는 값이며 "16 heads"·"GQA 16/8"을 32·32/8로 고칩니다. (b) 적힌 대로 16개 — 이때 head_dim(64 또는 128), KV head 수(8, 또는 head_dim 128이면 hidden 2048·QKV 3072·O 2048을 그대로 두는 4)와 hidden·QKV·O 가운데 어느 값이 바뀌는지도 알려 주십시오. (c) 그 밖(설명). 답이 없는 동안 막히는 것: RoPE와 SDPA(KV cache 포함)의 kind 계약과 shape 확정(PLAN P2-11의 attention 계열). 막히지 않는 것: GEMM(B-4의 projection shape, lm_head 포함)·RMSNorm·SwiGLU 활성·elementwise add의 계약 준비(이들도 OD-31 ②·③의 답을 먼저 기다리고, (b)·(c)의 답이 hidden·QKV·O를 바꾸면 그 shape도 다시 본다), P2-5와 그 밖의 진행 중 작업. (a)이면 ADR-0152는 H = 32, d_h = 64를 대입하는 것 말고 바뀌지 않고, (b)·(c)이면 답이 바꾸는 B-4 값과 함께 다시 봅니다.

- **The planner's next steps under P2-11**: one contract record per kind (GEMM in bf16/fp16, RMSNorm, elementwise add, SwiGLU activation, RoPE, SDPA with KV cache), each fixing its `kind` value, `op_signature` members, layout, prototype and operands as ADR-0008 did for `gemm`; then code and harness checks per kind. **Every contract needs the dtype and accumulation precision (sub-question 2) and the oracle and tolerance (sub-question 3), which are the owner's**: the driver asks them as HQs before planning any contract task (PLAN P2-12). The RoPE and SDPA contracts also wait on the head-count answer.
- **Readings for the owner to check**, listed in the #5 notice: K2's "each op the model needs" read as the operations that compute values (the embedding lookup outside the kernels, the residual add a target; decision 1); B-4's "KV cache included" and "SDPA with KV cache" read as the cache write belonging to the SDPA kernel (decision 3); lm_head in the end-to-end list with B-4's first-run exclusion kept (decision 4); a decode step's seq_len read as L (decision 5).
- **Runtime acceptance items**: none. Every fact used is in public documents read at a pinned commit; nothing here needs a live `claude`, a board or a model file.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` and `PROCESS/PLAN.md` for SDPA, attention, softmax, embedding, lm_head and GEMV; not claimed complete):
  - ADR-0001 Context and Boundaries call the second family "SDPA with KV cache"; this record also puts RoPE in the attention family as a kind of its own.
  - The wording of OpenDecisionProposals § OD-31 sub-question 1 lists softmax and embedding among the kinds and names GEMV; here softmax is inside SDPA, the embedding lookup is executor work, and a decode-step projection is a GEMM at M = 1. The wording stays (its recording rule).
  - PLAN P2-11 "forward에 필요한 연산 종류마다 커널 계약": the embedding lookup gets no contract under this record.
  - Requirements C-6 "모델에 필요한 연산을 각각 instance로 최적화" is read in decision 1 as the computing operations; the owner text is unchanged.
- **UsageCases and StandardScenarios** (S0 and S1 re-checked): no use case step changes. S1 step 2 (the op_signature of an instance, several M under OD-6 sub-question 3) is unchanged. S0 step 4 (per-op kernels for a model) keeps its known weakness and its open points (OD-31 sub-questions 4 and 6); its kernel contracts beyond `gemm` stay open under OD-6 sub-question 1 and OD-31 sub-question 1, now named per kind. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **Each kind's contract**: its `kind` value, `op_signature` members, `layout` values, prototype, operands, the order and strides of Q, K, V and the cache, the RoPE pairing convention (Meta's `model.py` pairs adjacent elements), cache capacity, and harness checks — the extension of OD-6 sub-question 1, one record per kind. Whether the bf16/fp16 projections are `gemm` with another dtype or another kind is part of it.
- **The query-head count and any value of B-4** (owner; decision 6).
- **Dtype and accumulation precision** (OD-31 sub-question 2, owner); **oracles and tolerances** (3, owner; #5 B-7).
- **The model executor**: its place, language, kernel choice per shape, the handling of operations with no kernel and of shapes outside the sets, which rows lm_head gets (OD-31 sub-question 4).
- **Weights and tokenizer**, tied or untied embeddings (5, owner); **model-level accuracy, prompts and generation, token selection** (6, owner); **new external dependencies** (7, owner); **the artifact** (8, owner); **model-level performance** (9, owner); **the scenario** (10, owner).
- **The order in which kinds are taken up after `gemm`**, beyond B-4's "GEMM first, then the attention family"; whether lm_head joins a run before or after the attention family.
- Whether one instance covers one or several shapes of a set (OD-6 sub-question 3; ADR-0031 decision 4).
- Batched attention over several sequences; any model other than Llama 3.2 1B; graph-level fusion (C-6, later).
- Any change of the first case (fp32 `gemm`, PLAN P1-5, ADR-0008) or of B-4's first-run settings.

## References

- Owner: #5 B-4 answer (K1), #5 C-6 revision of 2026-10-19 (K2), #5 A-7 decision comment (K3); [Requirements](../Requirements.md) C-6 and OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-31 and § OD-6.
- Records: [ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md).
- Meta, `meta-llama/llama-models` at `0e0b8c519242d5833d8c11bffc1232b77ad7f301`: [`models/sku_list.py`](https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/sku_list.py#L327-L346), [`models/llama3/args.py`](https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/llama3/args.py), [`models/llama3/model.py`](https://github.com/meta-llama/llama-models/blob/0e0b8c519242d5833d8c11bffc1232b77ad7f301/models/llama3/model.py).
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
