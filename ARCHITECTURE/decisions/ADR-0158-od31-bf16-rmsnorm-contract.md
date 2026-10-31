# ADR-0158: Operational contract of RMSNorm in bf16 for C kernels on `cpu_standin` — kind `rmsnorm` with shape members `m` and `n`, dtype `bf16` and layout `row_major`, the fp32 sum of squares and binary32 intermediates with no bf16 rounding before the weight multiply, `eps` as a `float` parameter, round-to-nearest-even output, the entry point `hilclaw_rmsnorm_bf16` over `uint16_t` bit patterns, the value set of the verification inputs and the op_signature records of the ADR-0152 RMSNorm calls (extension of OD-6 sub-question 1; part of OD-31 sub-questions 1 to 3)

## Status

- **Accepted on 2026-10-24.** It defines the second Llama kind contract of PLAN P2-11.
- **Three kinds of content.**
  - **Owner answers**, marked **owner**: the `decision` of HQ-0065 and HQ-0066 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records them. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md)) and of Meta's code, each with its source named.
  - **This record's own**, every other sentence: the kind and member names, the rank-1 reading of `row_major`, the precision of every step but the sum of squares, the place of `eps`, the output rounding, the prototype and symbol, the guarantees, the value set, the op_signature records and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 255 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: RMSNorm, rms norm, norm, eps, epsilon, rsqrt, 정규화, normalization, normalisation, bf16, bfloat16, rounding, 반올림, round-to-nearest. Found, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "dtype **fp32** (bf16 weights upcast); fp16 / q4 are later instance variants".
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16."
  - **Nothing found** on RMSNorm, normalisation, `eps`, `rsqrt` or rounding in any of the four issues.
  - **Conflicts**: K1 is the first case, which stays (ADR-0154 decision 2); K2 is answered by HQ-0065, which puts fp16 after P2-14. No owner sentence conflicts with a choice of this record.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `7b0c112`). **HQ-0033** (the ADR-0116 flags, `-ffp-contract=off` among them): no flag is chosen; for the inputs of decision 9 every square is exact in binary32, so contraction of a multiply and an add into the sum of squares does not change it; a contraction elsewhere (for example of the mean and the addition of eps) skips a rounding, which decision 3 allows as a wider intermediate. **HQ-0034** (OpenMP on `cpu_standin`): not chosen (decision 8). **HQ-0069** (runtime acceptance (lxvii) of the model executor): no runtime fact is used. The other open HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0021 to HQ-0024, HQ-0026 to HQ-0031, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **Not changed**: no schema file, member, file, version or validator of the data plane. `rmsnorm` with its members `m` and `n` is a new kind, which ADR-0001 decision 6 admits without raising `schema_version`; `bf16` and `row_major` are existing values. It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-6 sub-question 1, the contract of (`rmsnorm`, `bf16`, `row_major`, `c`) on `cpu_standin`; of OD-31 sub-question 1, the RMSNorm kind's contract and op_signatures; of sub-question 2, what the fp32 sum of squares obliges, the precision of RMSNorm's other steps and the rounding of its output conversion; of sub-question 3, the value set of the RMSNorm verification inputs. Open of them: Boundaries.
- It builds on ADR-0001 (decisions 2, 3 and 6), ADR-0008 (decisions 1, 2, 4 to 9), ADR-0037, ADR-0156 (decisions 2 to 5 and 9), ADR-0154 (decisions 2 and 3), ADR-0152 (decisions 2, 3, 5 and 7), ADR-0153 (decision 3) and ADR-0157 (decision 4); none of them is edited. **If ADR-0008 or ADR-0156 is reverted, this record is revisited with it.** The format follows the "Record format" section of ADR-0001.

## Context

- **Meta's reference** (cited), `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` lines 31-42: `RMSNorm._norm(x)` is `x * torch.rsqrt(x.pow(2).mean(-1, keepdim=True) + self.eps)`, and `forward(x)` is `self._norm(x.float()).type_as(x)` multiplied by `self.weight`, a vector of `dim` elements. So for a bf16 `x` the normalisation runs in fp32 and its result is cast back to bf16 **before** the weight multiply; the dtype of that product follows `weight`, which the class does not fix. The three norms are built with `eps=args.norm_eps` (lines 242, 243, 270), and `models/sku_list.py` lines 327-346 give `norm_eps` 1e-05 for Llama 3.2 1B (ADR-0152 decision 5 cites the same).
- **The calls** (ADR-0152 decisions 2, 3 and 5): RMSNorm before attention and before the feed-forward in every layer and once at the end (rows 2, 10, 15), T × 2048 with a weight of 2048, T ∈ {1, 32, 512}; the weight multiply is part of the RMSNorm kernel. ADR-0152 decision 7 leaves to this kind's record whether a kernel must accept other shapes.
- **The owner's answers** (ADR-0154 decisions 2 and 3): bf16 inputs and outputs; fp32 accumulation of "RMSNorm 제곱합" among three sums; `uint16_t` bit patterns at the boundary with the kernel converting; a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; each kind's input distribution fixed by a driver record, finite inputs only. ADR-0154 decision 2 leaves "the RMSNorm reciprocal square root and weight multiply" to this record.
- **The executor** (ADR-0153 decision 3) holds `eps` among the model parameters, "never assumed by the executor", binds a kernel by its contract's prototype and operand entries, and accepts a binding "for every shape" only where the contract obliges correctness at every shape. ADR-0157 decision 4 keeps `bf16` out of a generation's range while a call-site kind lacks a bf16 contract.
- **The keys** (ADR-0001 decisions 2 and 6): the `shape` member names are fixed per kind, and a new kind with its members raises no version. `hilclaw.keys` knows `gemm` only and refuses another kind.

## Decision

A sentence marked **owner** renders an HQ `decision` through ADR-0154. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **One contract**: the RMSNorm of ADR-0152 for kind `rmsnorm`, dtype `bf16`, layout `row_major` and kernel language `c`, **on `cpu_standin`** (ADR-0154 decision 2 fixes the `uint16_t` boundary for that target). It binds both sides as ADR-0008 decision 1 says: the caller guarantees what decision 7 lists, and a kernel does what decisions 3, 4, 7 and 8 list, for coder output and hand-written kernels alike. **No fp32 or fp16 RMSNorm contract is defined.**
- Where a point says "as ADR-0008" or "as ADR-0156", that text applies with its kind, symbol and operands read as this record's, and nothing else changes.

### 2. Kind, shape members, dtype and layout

- **Kind `rmsnorm`**, Meta's class name in lower case; it matches the name pattern `[a-z][a-z0-9_]{0,31}` of `hilclaw.keys`.
- **Shape members `m` and `n`, exactly these two**: `m` = T, the number of rows (tokens); `n` = the feature width, the length of each row and of the weight (2048 for Llama 3.2 1B). `m` is the token count of `gemm` and of B-4's "M (tokens)", so the RMSNorm before a projection and that projection carry the same `m`; `m` and `n` are also the r and c of ADR-0008 decision 2. `eps` is not a member (decision 5). By ADR-0001 decision 6 this kind and its members raise no `schema_version`.
- **Dtype `bf16`**, as ADR-0156 decision 2, for all three operands: the weight is bf16 as well (the owner's bf16 inputs).
- **Layout `row_major`**, as ADR-0008 decision 2 with "the C type of its dtype" read as ADR-0156 decision 2 reads it: each element is one `uint16_t` holding a bf16 bit pattern. ADR-0008 decision 2 defines the value for two-dimensional operands and leaves another rank to "the record of the first kind that has one"; this is that kind. **A rank-1 operand of shape `[c]` is one contiguous array of exactly c elements, element j at index j**, no padding, no stride, no header — the storage of a 1 × c matrix.

### 3. The operation and its precision

- **The operation** (Meta's `RMSNorm`): y(i, j) = x(i, j) · w(j) / sqrt(s(i) / n + eps), with s(i) = Σ over j of x(i, j)², for 0 ≤ i < m, 0 ≤ j < n. Each row is normalised over its own n elements; y is a new array; no bias, no residual add, no scaling beyond w.
- **The kernel converts its inputs** (**owner**, HQ-0065 (3)); widening bf16 to binary32 is exact (ADR-0154 decision 3).
- **The sum of squares s(i) is accumulated in fp32** (**owner**, HQ-0065 (2)). What that obliges is ADR-0156 decision 3's reading of the GEMM dot product, applied to the n squares of a row: binary32 accumulators, neither narrower nor wider; the order of the additions is the kernel's choice provided each square enters exactly once; one accumulation step may be any single operation that adds one or several products into a binary32 accumulator (an add, a fused multiply-add, a bf16 dot-product instruction with x as both factors), with that operation's own rounding. A square of a bf16 value has at most 16 significant bits and is exact in binary32 when it neither overflows nor falls below the normal range, which holds for the inputs of decision 9, so fused and unfused steps agree on every square.
- **Every other step holds its values and results in binary32 or a wider format, never a narrower one**: the mean s(i)/n (a correctly rounded division by n, or a multiply by a correctly rounded 1/n — no reciprocal estimate), the addition of eps, the reciprocal square root, the scaling of x(i, j) and the multiply by w(j), in either association, each a correctly rounded multiply (or a division by the root in place of the reciprocal, whose quotient then has a relative error of at most 2^−11 against x(i, j) times the exact reciprocal root). The method of each step is otherwise the kernel's choice. **The reciprocal square root has a relative error of at most 2^−11**, its method being the kernel's choice: `1.0f / sqrtf`, `sqrtf` then a division, an x86 `RSQRTPS` estimate (relative error at most 1.5·2^−12) with or without refinement, or a coarser estimate such as an Arm `FRSQRTE` with enough Newton steps to meet the bound. Reasons: the owner named no precision for it; this is the step a SIMD kernel speeds up most, and binary32 accuracy would rule out the x86 estimate; and 2^−11 is a quarter of the smallest relative half unit in the last place of bf16 (2^−9), so its error stays well below the output rounding, while an unbounded estimate (an 8-bit one, a bit trick without a Newton step) would add error of the size this record refuses for a bf16 intermediate rounding (below). Kernels may still differ at the last bf16 bit of an element near a rounding boundary, as ADR-0156 decision 3 accepts for the step rounding of the GEMM accumulation. The bound is an obligation of the kernel's arithmetic, not a tolerance: the verification compares within the instance's `rtol` and `atol` only and does not test it. Reasons for the format: the owner named no precision for these steps (ADR-0154 decision 2); a narrower one adds error that the float64 reference counts against the kernel, while a wider one only removes error and could not be told apart by the verification, so forbidding it buys nothing; how close the result must be is the tolerance (FR-9; **owner**, HQ-0066 (2), no value here).
- **No value is rounded to bf16 between the normalisation and the weight multiply**; the only rounding to bf16 is that of the output (decision 4). **This departs from Meta's order of roundings**: for a bf16 `x`, `type_as` rounds the normalised value to bf16 before the multiply by `weight`, and the product may be rounded again. Reasons: the owner's "입출력은 bf16" names inputs and outputs, and the normalised value is neither; the reference is float64 without bf16 emulation (**owner**, HQ-0066 (1)), so a second rounding is error counted against every kernel of the contract, about one more half unit in the last place; and a rounding left to the kernel would make a tolerance mean different things for kernels of one contract. The difference from Meta's result is at most about one bf16 unit in the last place per element; whether the model-level comparison needs Meta's order is OD-31 sub-question 6 (owner). Listed in the owner notice.

### 4. The fp32 → bf16 conversion of the output

- **The contract fixes it: round to nearest, ties to even**, from the result of the kernel's last step of decision 3 to bf16, for the reasons of ADR-0156 decision 4, which carry over unchanged (cited). A kernel that computes wider than binary32 may round its result to binary32 as that last step (decision 3 allows binary32) and then round the binary32 value to bf16; this double rounding is allowed.
- **Range**: for the inputs of decision 9 every exact element has a magnitude between 0.25 and 2 (decision 9), so the output never overflows, is never zero and never subnormal. A finite value whose magnitude rounds beyond the largest finite bf16 value becomes an infinity of its sign, as roundTiesToEven defines overflow (as ADR-0156 decision 4). For finite inputs outside that set a binary32 sum of squares can overflow (a single square at |x| of about 2^64, a row's sum somewhat below) or its squares can fall below the normal range (|x| below about 2^−63); such a sum and what follows from it, subnormal inputs and outputs, and what a kernel produces from non-finite inputs are not defined here (Boundaries).

### 5. `eps`, the C prototype and the symbol

```c
void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte, in every spec of this contract whatever the shape: single spaces as shown, no line break, the semicolon included. `size_t` is that of `<stddef.h>`, `uint16_t` that of `<stdint.h>`; valid in C99 and later.
- **`eps` is a kernel parameter of type `float`**, and the `eps` of decision 3 is the value passed. Reasons: ADR-0153 decision 3 makes `eps` a model parameter the executor never assumes, and a parameter carries it to the call; `eps` changes no performance, so as a key field (`ext`) it would split one kernel's knowledge across keys for nothing; a constant of the contract would make a model with another `eps` need another contract. `float` because eps is added in a binary32 step (decision 3): as `uint16_t` it would be rounded to bf16 (the bf16 value nearest to 1e-05 is about 1.0014e-05, 0.14 % off), and `double` would suggest a precision the step does not keep. The caller passes the binary32 value nearest to the model's `eps`.
- **Order**: dimensions first as ADR-0008 decision 4, then the scalar `eps`, then the arrays in the order input x, input w, output y; `void`, since the result is the output only; `restrict` states the no-overlap guarantee of decision 7.
- **Operand type `uint16_t`** (**owner**, HQ-0065 (3)).
- **Symbol `hilclaw_rmsnorm_bf16`**: `hilclaw_`, the kind, `_` and the dtype — the form of ADR-0156 decision 5, for its reasons (a wrong binding fails at `dlsym`, and kernels of several dtypes may share a link unit if contracts of other dtypes come). ADR-0156 set no rule for other kinds, and this record sets none either; it only chooses this name.

### 6. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `x` | `input` | `bf16` | `[m, n]` | `const uint16_t *restrict x` |
| `w` | `input` | `bf16` | `[n]` | `const uint16_t *restrict w` |
| `y` | `output` | `bf16` | `[m, n]` | `uint16_t *restrict y` |

As ADR-0008 decision 5: in parameter order, with the values of the spec's `op_signature` shape in place of `m` and `n`; the dimensions and `eps` have no entry. The complete `task.contract` at T = 1:

```json
{
  "language": "c",
  "prototype": "void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y);",
  "operands": [
    {"name": "x", "role": "input", "dtype": "bf16", "shape": [1, 2048]},
    {"name": "w", "role": "input", "dtype": "bf16", "shape": [2048]},
    {"name": "y", "role": "output", "dtype": "bf16", "shape": [1, 2048]}
  ]
}
```

**Validated on 2026-10-24** with `hilclaw.spec.validate`, inside the committed spec example with its op_signature replaced by the T = 1 record of decision 10, in a throwaway interpreter that added `"rmsnorm": {"m", "n"}` to `hilclaw.keys._SHAPE_MEMBERS` in memory; no repository file was changed.

### 7. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | `m` and `n` are each at least 1; `x` and `y` have exactly m·n elements and `w` exactly n. | Compute the operation for the values it is called with. |
| `eps` | `eps` is finite and greater than 0. | Use the value passed. |
| Overlap | The three arrays do not overlap each other; in particular `y` is not `x` (no in-place call). | — |
| Inputs | Every element of `x` and `w` is an initialised `uint16_t` holding a bf16 bit pattern, stored in the layout of decision 2, and nobody else changes them during the call. | Not modify them. |
| Output | The content of `y` on entry is unspecified. | Not read `y` before writing it, and write **every** one of its m·n elements, each the bf16 pattern of decision 4, before it returns. |
| Alignment | Each pointer is aligned for `uint16_t`. Nothing more is promised. | Not assume a larger alignment. |
| Memory, repeated calls, completion, result | As ADR-0008 decision 6. | As ADR-0008 decision 6. |

- **No in-place call.** In the pass the input of rows 2 and 10 is the residual stream, which the residual add after attention or after the feed-forward still reads (ADR-0152 decision 2), so an in-place RMSNorm would need a copy anyway; distinct arrays keep `restrict` and match the executor's "distinct arrays for each operand" (ADR-0153 decision 3).
- **`eps` greater than 0** keeps the square root away from 0 for a row of zeros.
- **Every set of dimensions**: the obligation is stated for the values passed, so **a kernel must be correct for every m, n ≥ 1** and every such `eps`, and may be specialised for its own shape only while staying correct elsewhere. A binding "for every shape" of ADR-0153 decision 3 is therefore accepted for this contract. Whether a verification passes other values stays OD-16 sub-question 1.
- **No shape that holds a 0**: the caller's guarantee of at least 1 has the same form as ADR-0008's, so ADR-0037's reading carries over — this contract defines no `task.contract` and no call for a shape with a 0.
- **Finiteness** is not part of the input guarantee, as in ADR-0008 decision 6; what a kernel produces for non-finite or subnormal inputs is Boundaries.

### 8. What the kernel source provides

- As ADR-0008 decision 7 with the name of decision 5: **exactly one definition of `hilclaw_rmsnorm_bf16`**, with external linkage and the prototype of decision 5; **no `main`**; no other identifier with external linkage that starts with `hilclaw_` (`hilclaw_gemm` and `hilclaw_gemm_bf16` included).
- It may include the headers ADR-0008 decision 7 allows; `<math.h>` is among them as part of the C standard library. Whether a build links the math library, and whether OpenMP is usable on `cpu_standin` (HQ-0034), are build settings (Boundaries).

### 9. The input value set of verification

- **Owner** (HQ-0066 (3)): each kind's input distribution is fixed by a driver record, finite inputs only. **This record fixes the value set; the rest is the P2-12 harness record's.**
- **x and w**: every drawn element is **exactly one of the 256 bf16 values of magnitude in [0.5, 1) with either sign**, ±(0.5 + j/256) for j = 0 … 127, the set of ADR-0156 decision 9. **eps**: the binary32 value nearest to 1e-05 in every call, the only value the Llama calls pass.
- **Reasons**: no input is zero or subnormal; every square lies in [0.25, 1) and is exact in binary32 (decision 3); a row's sum of squares is at most n, so it never overflows; every exact output element has a magnitude between 0.25 and 2 (|x(i, j)| / sqrt(s(i)/n + eps) lies in about [0.501, 1.993], times |w(j)| in [0.5, 1)), so no output overflows, vanishes or is subnormal. Negative weights are drawn because the operation does not exclude them. A wrong or missing weight, a wrong row or a wrong scaling moves elements by much more than the bf16 rounding. **A single square left out or counted twice is not reliably seen**: it changes a row's root mean square by at most about 0.1 % at n = 2048, less than half a bf16 unit in the last place (at least about 0.2 %); at that width no value set makes every square of a row change it this much (the smallest square of a row holds at most 1/n of the sum, whatever the set; a set with one dominant square can do it for that square alone), and the fp32 obligation of decision 3 stands without being tested. With these inputs eps moves the result by less than the bf16 rounding as well, so a kernel that ignores eps is not detected; the obligation stands either way.
- **Left to the P2-12 harness record**: the generator, its seed, the number of draws, the content of `y` before the call, the `eps` value the reference uses (the binary32 value passed, widened, or 1e-05; they differ by a relative 2.5e-8, which moves the reference by a relative 5e-13 at most for the inputs above), and the widening for the float64 reference — the inputs (**owner**, HQ-0066 (1)) and the output (cited: ADR-0154 decision 3). **No tolerance value or default is chosen** (**owner**, HQ-0066 (2)).

### 10. The `op_signature` records

**Rule**: `{"schema_version": 1, "kind": "rmsnorm", "shape": {"m": T, "n": 2048}, "dtype": "bf16", "layout": "row_major"}` for T ∈ {1, 32, 512}, the shape set of rows 2, 10 and 15 (ADR-0152 decision 5); the three calls of a pass share these records. At T = 1:

```
{"dtype":"bf16","kind":"rmsnorm","layout":"row_major","schema_version":1,"shape":{"m":1,"n":2048}}
sha256 = 57f1bdf44f626c31e71beef7ba688a245eca699394fdbc732d48fffe1b0de702  ->  rmsnorm-57f1bdf44f626c31
```

| T | 1 | 32 | 512 |
|---|---|---|---|
| Directory name | `rmsnorm-57f1bdf44f626c31` | `rmsnorm-953c4d92b64130ba` | `rmsnorm-3aba1dcd072652b7` |

- **Method**: `hilclaw.keys.op_signature_key` in the throwaway interpreter of decision 6 (kind added in memory, no repository change). The same interpreter gave `gemm-485b9bc494d477eb` for the fp32 `gemm` gate/up record at M = 1, the name of ADR-0008 decision 9.
- **How a shape set maps to instances** stays OD-6 sub-question 3. **Change of the contract**: ADR-0008 decision 8 holds as for fp32 (a storage change is a new `layout` value; any other change is OD-6 sub-question 4).

### 11. Order and runs

This record chooses no order of kinds, no instance and no run: when an RMSNorm instance runs is not said here, and B-4's run order ("GEMM first, then the attention family") stands (ADR-0152 Boundaries).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Kind `rms_norm`; members `t` and `d` | Both work. `rmsnorm` is Meta's class name; `m` matches `gemm`'s token count and B-4's M, and `m`, `n` are the r, c of `row_major`. |
| 3 | Round the normalised value to bf16 before the weight multiply, as Meta's `type_as` | A second rounding counted against the kernel by a reference that does not emulate bf16 (HQ-0066 (1)); the intermediate is not an input or output the owner named. Kept for the owner notice and OD-31 sub-question 6. |
| 3 | Leave that rounding, or a format narrower than binary32 for the other steps, to the kernel | Each such rounding adds up to half a bf16 unit in the last place, against a reference that counts it, at the kernel's choice; a tolerance would mean different things for kernels of one contract. The reciprocal square root is bounded instead at a relative error of 2^−11, well below that (decision 3). |
| 3 | Exactly binary32 for every step | The owner named fp32 for the sum only; a wider step removes error and cannot be detected. |
| 5 | `eps` as a constant of the contract (1e-05) | A model with another `eps` would need another contract, and the executor's model parameter (ADR-0153 decision 3) would be ignored. |
| 5 | `eps` as an `ext` key field | Splits one kernel's stored knowledge by a value that changes no performance. |
| 5 | `eps` as `uint16_t` (bf16) or `double` | bf16 changes the value; `double` suggests a precision the binary32 step does not keep. |
| 5 | Symbol `hilclaw_rmsnorm` | Gives up the load-time stop of ADR-0156 decision 5 if an RMSNorm contract of another dtype comes. |
| 7 | Allow in-place (`y` = `x`) | The pass needs its input afterwards (residual add), and in-place loses `restrict` and the executor's distinct arrays. |
| 9 | Values over the whole finite bf16 range, or uniform in [−1, 1]; w fixed at 1 (Meta's initial weight) | The whole range or [−1, 1] brings zero, subnormal and overflowing values, corner cases kept for later (#5 B-7, OD-16); w = 1 hides a wrong or missing weight. |
| 9 | Draw several eps values | Not a value the Llama calls pass, and for these inputs its effect is below the bf16 rounding. |

## Consequences

- **A-13 reading**: no schema file, member, file, version or validator of the data plane changes, and `hilclaw/` is not touched. The new kind `rmsnorm` with members `m` and `n` is a value ADR-0001 decision 6 admits without a version change; the rank-1 meaning of `row_major` fills the place ADR-0008 decision 2 left for it. Teaching `hilclaw.keys` the kind is a later code slice.
- **The code slice this record makes possible** (for the planner; no code here): the kind and its members in `hilclaw.keys`; a contract module like `hilclaw/gemm_bf16_contract.py` (constants, `task_contract`, `covers`, `op_signature_record`, the value set); fit and the "every shape" binding in `hilclaw/model_binding.py`, the executor passing its `eps` model parameter as the nearest binary32 value; whether the build of a kernel library links the math library, which a kernel calling `sqrtf` may need when loaded with `dlopen` (a build setting, with HQ-0033); hand-written bf16 RMSNorm kernels as test fixtures; and the P2-12 harness part (generator over the value set, widening, comparison).
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` for `RMSNorm`, `future contract records`, `other five kinds` and `Each kind's contract`; not claimed complete): ADR-0152 decision 7 and Boundaries ("Each kind's contract"); ADR-0153 decision 3 ("future contract records", "for every other kind, its contract record says") and Consequences code slice (2) ("the other five kinds"); ADR-0154 decision 2 ("the RMSNorm reciprocal square root and weight multiply"), Consequences ("What is now unblocked") and Boundaries ("Each kind's contract"); ADR-0156 Boundaries ("the other five kinds"); ADR-0157 decision 1 (the RMSNorm weights "take the element types their contracts give"), decision 4 and Boundaries ("the other five kinds"). This record now answers them for RMSNorm.
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: no bf16 rounding before the weight multiply, a departure from Meta's `type_as` (decision 3); every step but the sum in binary32 or wider, and the reciprocal square root within a relative error of 2^−11 by any method (decision 3); `eps` as a `float` parameter, not a key field or constant (decision 5); no in-place call (decision 7); the bf16 weight operand and its verification values in ±[0.5, 1) (decisions 2 and 9).
- **UsageCases and StandardScenarios** (S0 and S1 re-checked, and every scenario row citing OD-6 sub-question 1 or OD-31): no use case step changes. S0 step 4 keeps its open kernel contracts outside `gemm`, `rmsnorm` and C, its note now naming `rmsnorm` (OD-6 sub-question 1, OD-31 sub-question 1); S1 step 2 keeps OD-31 sub-question 3 for the vocabulary outside the first case and the Llama kinds on `cpu_standin`. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **fp16**: when and in what form, after PLAN P2-14 (owner, HQ-0065 (1)); **an fp32 RMSNorm contract**, which ADR-0157 decision 4 would need for an fp32 full pass.
- **Tolerance values**: instance parameters set by the user (FR-9; owner, HQ-0066 (2), no default).
- **Build settings and OpenMP**: compiler flags, `-ffp-contract`, linking the math library, the floating-point environment, OpenMP and thread count (HQ-0033, HQ-0034, OD-6 sub-question 2).
- **The harness mechanism** of a bf16 RMSNorm verification and timing run, and the parts of decision 9 left to it (PLAN P2-12).
- **Corner-case, non-finite and subnormal inputs and outputs**, and a sum of squares that is not finite or underflows (#5 B-7, OD-16).
- **Shapes outside an instance's** (OD-16 sub-question 1); **how a shape set maps to instances** (OD-6 sub-question 3; ADR-0031 decision 4); **contract change and keys** (OD-6 sub-question 4).
- **The contracts of the other four kinds** — elementwise add, SwiGLU activation, RoPE, SDPA with KV cache — one record each, and their symbol names.
- **Backends other than `cpu_standin`** and their representation of bf16 (#5 B-2, B-7).
- **The weights and their conversion to bf16**, the RMSNorm weights included (OD-31 sub-question 5, owner); the model-level comparison (sub-question 6, owner).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, ADR-0017, PLAN P1-5) or to ADR-0156.

## References

- Owner: HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1), C-6 revision (K2); [Requirements](../Requirements.md) C-6, FR-5, FR-9, OD-6, OD-16, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6 (sub-questions 1, 3, 4) and § OD-31 (sub-questions 1 to 3, 5, 6).
- Records: [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 2, 3, 6; record format), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decision 4), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md), [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md).
- Meta: `meta-llama/llama-models` at `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` (lines 31-42, 242-243, 270) and `models/sku_list.py` (lines 327-346).
- Code read: `hilclaw/keys.py`, `hilclaw/spec.py` (`validate`), `hilclaw/gemm_bf16_contract.py`; `examples/spec/gemm-485b9bc494d477eb.json`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
