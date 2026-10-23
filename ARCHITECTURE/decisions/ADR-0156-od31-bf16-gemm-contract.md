# ADR-0156: Operational contract of GEMM in bf16 for C kernels on `cpu_standin` — kind `gemm` with dtype `bf16` and layout `row_major`, fp32 accumulation, round-to-nearest-even output, the entry point `hilclaw_gemm_bf16` over `uint16_t` bit patterns, the value set of the verification inputs and the op_signature records of the B-4 projections (extension of OD-6 sub-question 1; part of OD-31 sub-questions 1 to 3)

## Status

- **Accepted on 2026-10-24.** It defines the first Llama kind contract of PLAN P2-11.
- **Three kinds of content.**
  - **Cited**, marked **owner** where it is an owner answer: the `decision` of HQ-0065 and HQ-0066 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records them, and #5 B-4. The owner's answers are **not subject to the objection window** below. Statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154) are cited with the record named.
  - **This record's own**, every other sentence: the kind and dtype values, the layout reading, what fp32 accumulation obliges a kernel to do, the output rounding, the prototype and symbol, the guarantees, the value set of the inputs, the op_signature records, and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
  - **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `432de45`). **HQ-0033** (the ADR-0116 flags, `-ffp-contract=off` among them): no flag is chosen, and for the inputs of decision 9 the contract's result does not depend on whether a compiler contracts a multiply and an add (decision 3). **HQ-0034** (OpenMP on `cpu_standin`): not chosen; decision 8 cites ADR-0008 decision 7 and leaves usability to that HQ. **HQ-0069** (runtime acceptance (lxvii) of the model executor's loading): no runtime fact is used. **HQ-0021**, **HQ-0026**, **HQ-0048** (parts of P2-5) and **HQ-0031** (injected hypotheses): not touched. **HQ-0022**, **HQ-0024**, **HQ-0028**, **HQ-0029** (code tasks), **HQ-0023**, **HQ-0027** (review limits of other records) and the other runtime-acceptance HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0047, HQ-0049 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 253 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: bf16, bfloat16, uint16, rounding, 반올림, round-to-nearest, round to nearest, GEMM, projection, weight layout, `[out, in]`, transpose, 가중치. Owner sentences found that touch the subject, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "GEMM first, then the attention family"; the projections "gate/up (2048→8192), down (8192→2048), QKV (2048→3072), O (2048→2048)"; "lm_head (2048→128,256) excluded from the first runs (1 GB fp32 weights, seconds per call)"; "M (tokens) ∈ {1, 32, 512}"; "dtype **fp32** (bf16 weights upcast); fp16 / q4 are later instance variants"; nntrainer read for idioms ("sgemm/hgemm pack-padding-kernel structure").
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16."
  - **K3** — the A-7 decision comment (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402): "both GEMM and the attention family"; and an owner's note (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136238336): "A fixed-shape GEMM is one operation of the target model among many". Context only.
  - **Nothing found** on `uint16_t` or bit patterns beyond HQ-0065, on rounding (반올림, round-to-nearest), on the weight layout or on the `[out, in]` order. #4, #7 and #8 hold no owner sentence on the subject (#7 comment 5566900982 names GEMM in a simulator survey, not an owner sentence).
  - **Conflicts**: K1's "dtype fp32 (bf16 weights upcast)" is the first case, which stays (ADR-0154 decision 2); K2's "bf16/fp16" is answered by HQ-0065, which puts fp16 after P2-14. No owner sentence conflicts with a choice of this record.
- **Not changed**: no schema file, member, file, version or validator of the data plane. `bf16` is a new value of the existing field `dtype` (ADR-0001 decision 6). It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-6 sub-question 1, the contract of (`gemm`, `bf16`, `row_major`, `c`) on `cpu_standin`; of OD-31 sub-question 1, the GEMM kind's contract and op_signatures; of sub-question 2, the GEMM accumulation obligation and the rounding of its fp32 → bf16 conversion; of sub-question 3, the value set of the GEMM verification inputs. Open of them: Boundaries.
- It builds on ADR-0008 (decisions 1 to 9), ADR-0037, ADR-0154 (decisions 2 and 3), ADR-0152 (decisions 2, 4, 5 and 7), ADR-0153 (decision 3) and ADR-0017 (decisions 3 and 4); none of them is edited. **If ADR-0008 is reverted, this record is revisited with it.** The format follows the "Record format" section of ADR-0001.

## Context

- **The only kernel contract so far** is ADR-0008: `gemm`, `fp32`, `row_major`, C. Its decision 1: "Another kind, dtype, layout or language has another contract, defined by its own record." Its decision 4 leaves open whether contracts of the same kind that differ in dtype "reuse this name".
- **The owner's answers** (ADR-0154 decisions 2 and 3): the dtype of the Llama goal is bf16; "입출력은 bf16, 누적(GEMM 내적 …)은 fp32"; "커널 경계는 16비트 비트 패턴(`uint16_t`)으로 하고 변환은 커널이 한다"; the reference widens the inputs to float64 and computes in NumPy float64; element-wise `rtol` and `atol`, instance parameters, no default; "kind마다 드라이버 ADR이 정한다(유한 입력만)" for the input distribution. ADR-0154 Boundaries leave to each contract its `kind` and `dtype` values, prototype, intermediate precisions, the rounding of the fp32 → bf16 conversion "and whether the contract or the kernel fixes it", and its input distribution.
- **The call sites** (ADR-0152 decisions 2, 4 and 5): QKV, O, gate, up and down in every layer, with the shapes of B-4 at M ∈ {1, 32, 512}, and lm_head 2048 → 128256, in the end-to-end list but excluded from the first runs. ADR-0152 Boundaries: "Whether the bf16/fp16 projections are `gemm` with another dtype or another kind is part of it."
- **The model executor** (ADR-0153 decision 3) binds a kernel to a call site when its `task.contract` is "the contract of the call site's kind, dtype, layout and language", and accepts a binding "for every shape" only where that contract obliges a kernel to be correct at every shape it is called with — "for every other kind, its contract record says". It loads each kernel from a shared library of its own with local symbols.
- **The format** (cited: ADR-0154 decision 3): a bf16 value is exactly representable in fp32 and float64, and its 16-bit pattern "is the upper half of the fp32 pattern of the same value". bf16 has 1 sign bit, 8 exponent bits (the exponent range of fp32) and 7 fraction bits, so 8 significant bits.

## Decision

A sentence marked **owner** renders an HQ `decision` through ADR-0154. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- This record defines **one contract**: the GEMM of ADR-0152 for kind `gemm`, dtype `bf16`, layout `row_major` and kernel language `c`, **on `cpu_standin`** (ADR-0154 decision 2 fixes the `uint16_t` boundary for that target only). It binds both sides as ADR-0008 decision 1 says: the caller guarantees what decision 7 lists, and a kernel does what decisions 3, 4, 7 and 8 list, for coder output and hand-written kernels alike.
- **The fp32 contract of ADR-0008 is unchanged** and stays the contract of (`gemm`, `fp32`, `row_major`, `c`). Where a point below says "as ADR-0008", the text of ADR-0008 applies with `float` read as `uint16_t` and `fp32` as `bf16`, and nothing else changes — except where a decision below says it replaces a sentence of ADR-0008.

### 2. Kind, dtype and layout

- **Kind `gemm`, dtype `bf16`.** The operation is the plain product of ADR-0008 decision 3 over the same three dimensions `m`, `k`, `n` (ADR-0001 decision 2); only the element type differs, and `dtype` is the key field that names the element type (ADR-0001 decision 2). `bf16` matches the name pattern `[a-z][a-z0-9_]{0,31}` of `hilclaw.keys` and is the short form the owner's answers use, next to `fp32`.
- **Layout `row_major`, as ADR-0008 decision 2 defines it.** That definition is in terms of "the C type of its dtype": here each element is one `uint16_t` that holds the bit pattern of a bf16 value, element (i, j) of an r×c operand at index i·c + j, contiguous, no padding, no stride, no header. The pattern is that of the format (Context), sign in bit 15, held in the representation of `uint16_t` on the host. That a value crosses the boundary as a `uint16_t` bit pattern is the owner's (HQ-0065 (3)); this record reads it as the dtype's representation, not a storage choice, so no new `layout` value is needed.
- **The weight operand stays in `[in, out]` order**, the k×n matrix B of ADR-0008 decision 3, for the reasons given there; no transposition flag. The `[out, in]` order of model files remains another `layout` value, not defined here. How weights read from a model file reach this order — a transposition or conversion before the kernel — belongs to the weights (OD-31 sub-question 5, owner) and the executor's inputs (ADR-0153 decision 3 (b): weights "already in the dtype and layout of the operand that receives it"). This reading is listed in the owner notice.

### 3. The operation and its precision

- **The plain product**, with the formula and the exclusions of ADR-0008 decision 3 (its first two bullets): C(i, j) = Σ over p of A(i, p)·B(p, j); no scaling factors, no accumulation into the output, no transposition flag, no bias. **Its third bullet** (the product "evaluated in `fp32`", the precision of intermediate values the kernel's choice) **is replaced for this contract** by the bullets below.
- **The kernel converts its inputs** (**owner**, HQ-0065 (3)) **and accumulates the dot product in fp32** (**owner**, HQ-0065 (2)). That it widens each input from bf16 to fp32 follows from the fp32 accumulation; widening is exact (Context).
- **What fp32 accumulation obliges** (this record's reading of the owner answer): each output element is accumulated in **binary32 accumulators** — every partial sum that is held between accumulation steps is a binary32 value. A partial sum is **never held narrower** — not rounded to bf16 or another 16-bit format before the conversion of decision 4 — and **never wider** (no double or extended-precision accumulator carried across steps), because the owner named fp32 as the accumulation precision and a wider one is not that answer. **The order of the additions** — blocking over k, several partial sums per element in SIMD lanes or threads, a tree — **is the kernel's choice**, provided each of the k products enters the sum exactly once.
- **One accumulation step is the kernel's choice as well**: a single operation that adds one or several products into a binary32 accumulator and leaves a binary32 result — a scalar or SIMD add, a fused multiply-add, or a bf16 dot-product instruction of the target (for example x86 `VDPBF16PS`, Arm `BFDOT` and `BFMMLA`) — counts as one step, **whatever rounding that operation has by its definition in the default floating-point environment** (round to nearest even, or the round to odd of some bf16 instructions) and whether it flushes subnormals. The owner's answer names the precision of the accumulator, not the rounding of each step; these instructions are the target's own means for fp32 accumulation of bf16 products; and their differences are at the last bit of a binary32 partial sum at each step. A rounding mode the kernel selects by changing the floating-point environment is not covered by this sentence (Boundaries). Subnormals do not arise for the inputs of decision 9.
- **Fused multiply-add is the kernel's choice.** A product of two bf16 values has at most 16 significant bits and is exact in binary32 when it neither overflows nor falls below the normal range, which holds for the inputs of decision 9; for them a fused and an unfused multiply-add give the same value. This record names no compiler flag; whether a build setting can make a kernel break the obligation is a matter of the build settings (Boundaries; HQ-0033).
- **How close the result must be is the tolerance** (FR-9; **owner**, HQ-0066 (2): element-wise `rtol` and `atol`, instance parameters, no default). This record names no value.

### 4. The fp32 → bf16 conversion of the output

- **The contract fixes it: round to nearest, ties to even** (IEEE 754 roundTiesToEven) from the binary32 sum to bf16. Each element of `c` is the bf16 value nearest to the kernel's fp32 sum, the one with an even last fraction bit on a tie.
- **Reasons.** It is the default rounding of the binary32 arithmetic the kernel already does. A fixed rule bounds the conversion error at half a bf16 unit in the last place for every kernel of the contract, so an `rtol` and `atol` the user sets mean the same for all of them. Truncation would double that bound and bias every element toward zero, an error that adds up along a forward pass; left to the kernel, it would be a precision choice made by the code rather than by the user's tolerance (FR-9).
- **Out of the finite bf16 range**: a finite fp32 sum whose magnitude rounds beyond the largest finite bf16 value becomes an infinity of its sign, as roundTiesToEven defines overflow. For the inputs of decision 9 this never happens: every exact element is bounded by k in magnitude (decision 9), far inside the range. A sum below the normal bf16 range (a subnormal result), like a sum that is itself not finite, and what a kernel produces from non-finite inputs, are not defined here (Boundaries); for the inputs of decision 9 every sum is zero or at least 2^−16 in magnitude.
- The verification compares within the tolerance only, so a kernel that rounds otherwise and stays within it is not detected; the obligation stands either way.

### 5. The C prototype and symbol

```c
void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte: single spaces as shown, no line break, the terminating semicolon included. It is the same text in every spec of this contract, whatever the shape. `size_t` is the type of `<stddef.h>` and `uint16_t` that of `<stdint.h>`, both present on the platforms of C-7; the declaration is valid in C99 and later.
- **Dimensions, return type and operand order as ADR-0008 decision 4**: `m`, `k`, `n` first, `void`, then A, B, C; `restrict` states the no-overlap guarantee of decision 7.
- **Operand type `uint16_t`** (**owner**, HQ-0065 (3)): the kernel converts on both sides of the boundary.
- **Symbol `hilclaw_gemm_bf16`**: `hilclaw_`, the kind, `_` and the dtype. Reasons:
  - **A wrong binding fails at loading, not in memory.** The fit check of ADR-0153 decision 3 compares prototype texts; a second, independent stop is that `dlsym` of `hilclaw_gemm_bf16` finds nothing in the library of an fp32 kernel, and the reverse. With one name for both, an fp32 kernel called with `uint16_t` arrays would read twice the bytes of each input and write twice those of the output.
  - **A harness or a program may hold kernels of both dtypes in one link unit** — a calibration test of both contracts, a program built for the fp32 first case and a bf16 model — without renaming or isolating them.
  - **ADR-0008 decision 7's rule on the prefix stays as it is**: the prefix `hilclaw_` is reserved for the contract and the caller. The fp32 symbol stays `hilclaw_gemm` (ADR-0008 decision 4); this record changes no fp32 name and sets no naming rule for other kinds, whose records choose their own.
  - Reusing `hilclaw_gemm` would also work in the model executor, which loads each kernel from its own library with local symbols (ADR-0153 decision 3), and in a verification executable that holds one kernel (ADR-0017 decision 2); it gives up the two points above for nothing the shorter name buys.

### 6. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `a` | `input` | `bf16` | `[m, k]` | `const uint16_t *restrict a` |
| `b` | `input` | `bf16` | `[k, n]` | `const uint16_t *restrict b` |
| `c` | `output` | `bf16` | `[m, n]` | `uint16_t *restrict c` |

As ADR-0008 decision 5: in parameter order, with the values of the spec's `op_signature` shape in place of `m`, `k`, `n`; the dimension parameters have no entry. The complete `task.contract` for gate/up (2048→8192) at M = 1, accepted by `hilclaw.spec.validate` inside the committed spec example with its op_signature changed to this record's (checked on 2026-10-24):

```json
{
  "language": "c",
  "prototype": "void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);",
  "operands": [
    {"name": "a", "role": "input", "dtype": "bf16", "shape": [1, 2048]},
    {"name": "b", "role": "input", "dtype": "bf16", "shape": [2048, 8192]},
    {"name": "c", "role": "output", "dtype": "bf16", "shape": [1, 8192]}
  ]
}
```

### 7. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | `m`, `k`, `n` are each at least 1, and the three arrays have exactly m·k, k·n and m·n elements. | Compute the product for the values it is called with. |
| Overlap | The three arrays do not overlap each other. | — |
| Inputs | Every element of `a` and `b` is an initialised `uint16_t` holding a bf16 bit pattern, stored in the layout of decision 2, and nobody else changes them during the call. | Not modify them. |
| Output | The content of `c` on entry is unspecified. | Not read `c` before writing it, and write **every** one of its m·n elements, each the bf16 pattern of decision 4, before it returns. |
| Alignment | Each pointer is aligned for `uint16_t`. Nothing more is promised. | Not assume a larger alignment. |
| Memory | As ADR-0008 decision 6. | As ADR-0008 decision 6. |
| Repeated calls | As ADR-0008 decision 6. | As ADR-0008 decision 6. |
| Completion | — | As ADR-0008 decision 6, the work of any thread it started included. |
| Result | Only the content of `c` after the return is the result of a call. | As ADR-0008 decision 6. |

- **Every set of dimensions.** As for fp32, the obligation is stated for the values passed, so **a kernel of this contract must be correct for every m, k, n ≥ 1** and may be as specialised as it likes for its own shape only as long as it stays correct elsewhere. A binding "for every shape" of ADR-0153 decision 3 is therefore accepted for this contract. Whether a verification ever passes other values stays OD-16 sub-question 1.
- **No shape that holds a 0**: the caller's guarantee of at least 1 is ADR-0008's, so the reading of ADR-0037 holds for this contract as well — it defines no `task.contract` and no call for a shape with a 0.
- **Finiteness** is not part of the input guarantee, as in ADR-0008 decision 6; the verification draws finite inputs only (decision 9), and what a kernel produces for non-finite or subnormal inputs is Boundaries.
- **Alignment, state between calls and threads**: the remarks of ADR-0008 decision 6 apply unchanged.

### 8. What the kernel source provides

- As ADR-0008 decision 7, with the name of decision 5: the source contains **exactly one definition of `hilclaw_gemm_bf16`**, with external linkage and the prototype of decision 5; **no `main`**; no other identifier with external linkage that starts with `hilclaw_` — `hilclaw_gemm` included.
- It may include the headers ADR-0008 decision 7 allows (the C standard library, `<stdint.h>` among them, `<omp.h>` and the SIMD intrinsics headers of the target); whether OpenMP is usable on `cpu_standin` is HQ-0034, and whether it may call another library stays undecided as there.
- Two kernels of this contract define the same symbol; the model executor keeps them apart with one library per kernel (cited: ADR-0153 decision 3). A verification executable of ADR-0017 decision 2 holds one kernel; how a bf16 verification run is built is the P2-12 harness record's.

### 9. The input distribution of verification

- **Owner** (HQ-0066 (3)): each kind's input distribution is fixed by a driver record, with finite inputs only. **This record fixes its value set; the rest is the P2-12 harness record's.**
- **Value set**: every drawn element of `a` and `b` is **exactly one of the 256 bf16 values of magnitude in [0.5, 1) with either sign**, ±(0.5 + j/256) for j = 0 … 127. Every one of them is finite and exactly a bf16 value. A value obtained by rounding a wider draw to bf16 can reach 1.0, which is outside the set, so the harness draws from the set itself.
- **Reasons** (the range of ADR-0017 decision 3, reasoned again for bf16): no input and no product is zero or subnormal; every product has a magnitude in [0.25, 1) and is exact in fp32 (decision 3), so fused and unfused kernels agree on every product; every exact element is bounded by k in magnitude — at most 8192 for the B-4 shapes and 2048 for lm_head — so neither an fp32 partial sum nor the bf16 output overflows, and a non-finite output is never the right answer. A term left out or counted twice moves the exact element by at least 0.25; whether that exceeds the tolerance after the bf16 rounding depends on the `rtol` and `atol` of the instance and is not promised.
- **Left to the P2-12 harness record**: the generator (deterministic, how it chooses among the 256 values, and its second implementation on the Python side if the reference regenerates the inputs as ADR-0017 decision 4 does), the seed and where it comes from, the number of draws, the content of `c` before the call, and the widening of the inputs and the output for the float64 reference — the inputs (**owner**, HQ-0066 (1)) and the output (cited: ADR-0154 decision 3). **No tolerance value or default is chosen** (**owner**, HQ-0066 (2): no default).
- Whether a verification draws shapes other than the op_signature's stays OD-16 sub-question 1.

### 10. The `op_signature` records

**Rule**: `{"schema_version": 1, "kind": "gemm", "shape": {"m": M, "k": in, "n": out}, "dtype": "bf16", "layout": "row_major"}` for each projection shape and each M ∈ {1, 32, 512}. For gate/up at M = 1:

```
{"dtype":"bf16","kind":"gemm","layout":"row_major","schema_version":1,"shape":{"k":2048,"m":1,"n":8192}}
sha256 = 34b9bfc10d87cb7671a18645c35175eb03a4a48ed02ae0fcad38418db39fcb3c  ->  gemm-34b9bfc10d87cb76
```

The directory names, computed with `hilclaw.keys.op_signature_key`:

| Projection (`k`→`n`) | M = 1 | M = 32 | M = 512 |
|---|---|---|---|
| gate/up (2048→8192) | `gemm-34b9bfc10d87cb76` | `gemm-238c4b6857772ce9` | `gemm-3745ff77e935d5bf` |
| down (8192→2048) | `gemm-740aba7178a399ca` | `gemm-83759c5dbd362967` | `gemm-f62196626f63b677` |
| QKV (2048→3072) | `gemm-010447f83b058ec1` | `gemm-7bdb55c59efcb192` | `gemm-7498e7a3efccda9d` |
| O (2048→2048) | `gemm-56b9a02064895971` | `gemm-7aa1a4d9498e59ed` | `gemm-99ae250b0e439e65` |
| lm_head (2048→128256) | `gemm-b64caf7cea838035` | `gemm-4e9cad77ac0d9567` | `gemm-cf79ec18c7b665b0` |

- They differ from the twelve fp32 names of ADR-0008 decision 9 only through `dtype`, a key field (ADR-0001 decision 5).
- **lm_head is listed for completeness; B-4's exclusion of lm_head from the first runs stands** (cited: ADR-0152 decision 4), and when it runs is not said here.
- **How a shape set maps to instances** — one instance per shape or one over several — is not decided (OD-6 sub-question 3).
- **Change of the contract**: ADR-0008 decision 8 holds for this contract as for fp32 — a change of storage is a new `layout` value, and a change that is not storage is OD-6 sub-question 4.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Another kind (for example `gemm_bf16`) | The element type already has its key field; the operation and its shape members are the same. `hilclaw.keys` accepts only kinds it knows the shape members of, so a new kind is a code change for no gain in meaning. |
| 2 | Spelling `bfloat16` | Longer than needed; the owner's answers and ADR-0154 say bf16, next to `fp32`. |
| 2 | A new layout value for bit-pattern storage | The bit pattern at the boundary is the owner's (HQ-0065 (3)) and is read here as the dtype's representation, not a storage arrangement; `row_major` is defined over the C type of the dtype. |
| 2 | Weights in `[out, in]` order | As ADR-0008 decision 3; kept open as another layout value and listed for the owner to check. |
| 3 | Accumulation "at least fp32" (double allowed) | Reads more into the owner's "누적은 fp32" than it says; the verification could not tell the difference, so the record states the owner's precision. |
| 3 | Partial sums held in bf16 | Against the owner's fp32 accumulation. |
| 3 | Every step a separate roundTiesToEven binary32 addition | Excludes the bf16 dot-product instructions a stand-in CPU may have (for example `VDPBF16PS` with AVX512_BF16, `BFDOT` and `BFMMLA` with FEAT_BF16), which accumulate into binary32 with their own step rounding, for differences at the last bit of each step; the owner named the accumulator's precision, not a step rule. |
| 4 | Rounding left to the kernel, or truncation | Truncation doubles the conversion error and biases it; a kernel-chosen rounding makes the meaning of a tolerance differ between kernels of one contract. ADR-0154 left the choice to this record. |
| 5 | Reuse `hilclaw_gemm` | A wrong binding would be found only by the prototype comparison, and a program could not hold both dtypes in one link unit (decision 5). |
| 5 | A C bf16 type (`__bf16`) in the prototype | The owner fixed `uint16_t` at the boundary (HQ-0065 (3)). |
| 9 | Leave the whole distribution to the P2-12 harness record | The value set is what the contract's arithmetic rests on (exact products, no overflow, decisions 3 and 4) and belongs with it; the mechanism stays with the harness. |
| 9 | Values over the whole finite bf16 range, or uniform in [−1, 1] | Brings zero and subnormal inputs, corner cases kept for later (#5 B-7, OD-16), and over the whole range overflow of products and sums to non-finite results; and makes a dropped term invisible. |

## Consequences

- **A-13 reading**: no schema file, member, file, version or validator changes. `bf16` is a new value of the existing field `dtype` (ADR-0001 decision 6: no version change), `hilclaw.keys` and `hilclaw.spec` accept the values of this record as they stand (decisions 6 and 10), and `hilclaw/` is not touched.
- **The code slice this record makes possible** (for the planner; no code here):
  - the bf16 counterpart of `hilclaw/gemm_contract.py` — its constants, `task_contract`, `covers` and `op_signature_record` for this contract;
  - its use by `hilclaw/model_binding.py` (fit and the "every shape" binding) and by the model program, which calls `hilclaw_gemm_bf16` over `uint16_t` buffers;
  - hand-written bf16 kernels in the manner of the calibration kernels, as test fixtures;
  - the P2-12 harness work of a bf16 `gemm` verification run: the generator over the value set of decision 9, the widening of the 16-bit patterns for the float64 reference, and the element-wise comparison.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` for `bf16/fp16 projections`, `GEMM in bf16`, `future contract records`, `hilclaw_gemm`, `fp32 \`gemm\`` and `다른 dtype`; not claimed complete):
  - ADR-0152 Consequences ("GEMM in bf16/fp16" among the contracts to write) and Boundaries ("Whether the bf16/fp16 projections are `gemm` with another dtype or another kind is part of it");
  - ADR-0153 decision 3 ("for other kinds, through the prototypes of their future contract records"; "for every other kind, its contract record says") and Consequences, code slice (2) ("after the contract records of the other five kinds");
  - ADR-0154 Consequences ("What is now unblocked: the per-kind contract records … GEMM in bf16") and Boundaries ("Each kind's contract", the conversion rounding "and whether the contract or the kernel fixes it"), which this record now answers for GEMM;
  - Requirements FR-9, whose tolerance vocabulary names the first case only and keeps "다른 dtype의 tolerance" with #5 B-7, while HQ-0066 (2) gives the vocabulary of every Llama kind on `cpu_standin` (ADR-0154 decision 3).
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: the weights in `[in, out]` order (decision 2); "누적은 fp32" read as binary32 accumulators, neither narrower nor wider, with the rounding of each step, fused steps and the target's bf16 dot-product instructions left to the kernel (decision 3); round-to-nearest-even fixed by the contract (decision 4); the dtype-qualified symbol (decision 5).
- **UsageCases and StandardScenarios** (S0 and S1 re-checked): no use case step changes. S0 step 4 keeps its open contracts of the kinds other than `gemm` and of GEMM outside `cpu_standin` (OD-6 sub-question 1, OD-31 sub-question 1), which stay open under the references its note gives; S1 step 2 keeps OD-31 sub-question 3 for the vocabulary outside the first case and the Llama kinds on `cpu_standin`. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **fp16**: when and in what form, after PLAN P2-14 (owner, HQ-0065 (1)).
- **Tolerance values**: instance parameters set by the user (FR-9; owner, HQ-0066 (2), no default).
- **Build settings and OpenMP**: compiler flags, `-ffp-contract`, the language standard, the evaluation method of floating expressions, whether a kernel may change the floating-point environment of the process (rounding mode, flush of subnormals) and whether it must restore it — what the built-in rounding of an accumulation step may be is decision 3 — OpenMP and thread count (HQ-0033, HQ-0034, OD-6 sub-question 2).
- **The harness mechanism** of a bf16 verification and timing run, and the parts of the input distribution left in decision 9 (PLAN P2-12).
- **Corner-case and non-finite inputs**, subnormal inputs and outputs, and a sum that is not finite (#5 B-7, OD-16).
- **Shapes outside an instance's** (OD-16 sub-question 1).
- **How a shape set maps to instances** (OD-6 sub-question 3; ADR-0031 decision 4).
- **Contract change and keys** (OD-6 sub-question 4).
- **The contracts of the other five kinds** — RMSNorm, elementwise add, SwiGLU activation, RoPE, SDPA with KV cache — one record each, and their symbol names.
- **Backends other than `cpu_standin`** and their representation of bf16 (#5 B-2, B-7).
- **Weights and their conversion to bf16**, their order on reading a model file (OD-31 sub-question 5, owner).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, ADR-0017, PLAN P1-5) or to B-4's first-run settings, lm_head's exclusion included.

## References

- Owner: HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1), C-6 revision (K2), A-7 decision comment (K3); [Requirements](../Requirements.md) C-6, FR-9, OD-6, OD-16, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6 (sub-questions 1 to 4) and § OD-31 (sub-questions 1 to 3, 5).
- Records: [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 2, 3, 5, 6; record format), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) (decisions 2, 3, 4), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decision 4), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md).
- Code read: `hilclaw/keys.py` (`op_signature_key`, the name pattern, the known kinds), `hilclaw/spec.py` (`validate`), `hilclaw/gemm_contract.py`; `examples/spec/gemm-485b9bc494d477eb.json`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
