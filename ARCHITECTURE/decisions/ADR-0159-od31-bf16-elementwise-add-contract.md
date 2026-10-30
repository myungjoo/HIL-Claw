# ADR-0159: Operational contract of the elementwise add of the Llama residual stream in bf16 for C kernels on `cpu_standin` — kind `elementwise_add` with shape members `m` and `n`, dtype `bf16` and layout `row_major`, an output that is the correctly rounded bf16 sum (round-to-nearest-even), the entry point `hilclaw_elementwise_add_bf16` over `uint16_t` bit patterns with no in-place call, the value set of the verification inputs, the op_signature records of the ADR-0152 add calls and the names of its two call sites (extension of OD-6 sub-question 1; part of OD-31 sub-questions 1 to 3)

## Status

- **Accepted on 2026-10-24.** It defines the third Llama kind contract of PLAN P2-11.
- **Three kinds of content.**
  - **Owner answers**, marked **owner**: the `decision` of HQ-0065 and HQ-0066 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records them. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md)) and of Meta's code, each with its source named.
  - **This record's own**, every other sentence: the kind and member names, the obligation on the result of the sum, the double-rounding argument, the output rounding, the prototype and symbol, the guarantees (no in-place call among them), the value set, the op_signature records, the call-site names and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 256 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: add (as a word, with its inflections and "addition"), residual, skip connection, elementwise, element-wise, 덧셈, 잔차, bf16, bfloat16, rounding, 반올림, in-place, in place, alias. Found, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "dtype **fp32** (bf16 weights upcast); fp16 / q4 are later instance variants". It says nothing of an add.
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16." It names no kind.
  - **"add" and "alias" as ordinary words only**: 18 hits of "add"/"added"/"adding"/"addition" in #5 (14), #7 (1) and #8 (3) (for example "kept **in addition**" in the A-7 decision comment, "add `coverage==7.16.2`" in the HQ-0003 answer) speak of process, dependencies or registry entries; "alias" occurs once, as "the form of the recorded model value (alias or full model name)" (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6290608368), about a model name. None of them is about an arithmetic add or memory aliasing.
  - **Nothing found** on a residual add, a skip connection, an elementwise add, rounding, in-place calls or aliasing of operands in any of the four issues.
  - **Conflicts**: K1 is the first case, which stays (ADR-0154 decision 2); K2 is answered by HQ-0065, which puts fp16 after P2-14. No owner sentence conflicts with a choice of this record.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `a33703e`). **HQ-0033** (the ADR-0116 flags, `-ffp-contract=off` among them): no flag is chosen; the operation has no multiply, so contraction, which fuses a multiply with an add, has nothing to fuse in the sum and cannot change its result either way; whether another build setting can make a kernel break the obligation of decision 4 is a matter of the build settings (Boundaries). **HQ-0034** (OpenMP on `cpu_standin`): not chosen (decision 9). **HQ-0069** (runtime acceptance (lxvii) of the model executor): no runtime fact is used; the call-site names of decision 12 are inputs to a later code slice, not a claim about a live run. The other open HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0021 to HQ-0024, HQ-0026 to HQ-0031, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **Not changed**: no schema file, member, file, version or validator of the data plane. `elementwise_add` with its members `m` and `n` is a new kind, which ADR-0001 decision 6 admits without raising `schema_version`; `bf16` and `row_major` are existing values. It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-6 sub-question 1, the contract of (`elementwise_add`, `bf16`, `row_major`, `c`) on `cpu_standin`; of OD-31 sub-question 1, the elementwise add kind's contract, op_signatures and call-site names; of sub-question 2, the precision of the add and the rounding of its output conversion; of sub-question 3, the value set of the elementwise add verification inputs. Open of them: Boundaries.
- It builds on ADR-0001 (decisions 2 and 6), ADR-0008 (decisions 1 to 8), ADR-0037, ADR-0152 (decisions 2, 5 and 7), ADR-0153 (decisions 3 and 4), ADR-0154 (decisions 1 to 3), ADR-0156 (decisions 2, 4, 5 and 9), ADR-0157 (decision 4) and ADR-0158 (decisions 2, 3, 5, 7, 9, 10 and 11); none of them is edited. **If ADR-0008 or ADR-0156 is reverted, this record is revisited with it.** The format follows the "Record format" section of ADR-0001.

## Context

- **Meta's reference** (cited), `meta-llama/llama-models` at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` lines 252-253, `TransformerBlock.forward`: `h = x + self.attention(self.attention_norm(x), start_pos, freqs_cis, mask)` and `out = h + self.feed_forward(self.ffn_norm(h))`. The two adds have no module of their own, unlike `attention_norm` and `ffn_norm` (lines 242-243). Their left operand is the residual stream — the block's input `x`, then `h` — and their right operand the output of the attention or the feed-forward module.
- **The calls** (ADR-0152 decisions 2 and 5): rows 9 ("Residual add after attention") and 14 ("Residual add after the feed-forward"), each once per layer, with "two T × 2048 inputs; T ∈ {1, 32, 512}" (unchanged by ADR-0154 decision 1). ADR-0152 Alternatives keep the add as its own kernel: inside the next RMSNorm is fusion (later), and accumulation in a GEMM is excluded by ADR-0008 decision 3. ADR-0152 decision 7 leaves to this kind's record whether a kernel must accept other shapes.
- **The owner's answers** (ADR-0154 decisions 2 and 3): bf16 inputs and outputs; fp32 accumulation for three named sums — the GEMM dot product, the RMSNorm sum of squares and the softmax sum — of which the residual add is not one, and "Every other intermediate precision is not settled by the answer"; `uint16_t` bit patterns at the boundary with the kernel converting; a float64 NumPy reference without bf16 emulation; element-wise `rtol` and `atol` with no default; each kind's input distribution fixed by a driver record, finite inputs only.
- **The executor** (ADR-0153 decision 3) binds a kernel by its contract's prototype and operand entries, accepts a binding "for every shape" only where the contract obliges correctness at every shape, and keeps "distinct arrays for each operand" among the caller's guarantees; it owns every array of a generation (decision 4). ADR-0157 decision 4 keeps `bf16` out of a generation's range while a call-site kind lacks a bf16 contract.
- **The format** (cited: ADR-0156 Context): bf16 has the exponent range of binary32 and 8 significant bits; every bf16 value is exactly a binary32 and a float64 value (ADR-0154 decision 3).

## Decision

A sentence marked **owner** renders an HQ `decision` through ADR-0154. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **One contract**: the elementwise add of ADR-0152 rows 9 and 14 for kind `elementwise_add`, dtype `bf16`, layout `row_major` and kernel language `c`, **on `cpu_standin`** (ADR-0154 decision 2 fixes the `uint16_t` boundary for that target). It binds both sides as ADR-0008 decision 1 says: the caller guarantees what decision 8 lists, and a kernel does what decisions 4, 5, 8 and 9 list, for coder output and hand-written kernels alike. **No fp32 or fp16 contract of this kind is defined.**
- Where a point says "as ADR-0008" or "as ADR-0156", that text applies with its kind, symbol and operands read as this record's, and nothing else changes.

### 2. Kind and shape members

- **Kind `elementwise_add`**, ADR-0152's name of the kind in snake case; it matches the name pattern `[a-z][a-z0-9_]{0,31}` of `hilclaw.keys`. It names the operation, not its place in the model, as ADR-0001 decision 2 does for keys; a later add with broadcasting (a bias add) would be another kind.
- **Shape members `m` and `n`, exactly these two**: `m` = T, the number of rows (tokens); `n` = the width of each row, the hidden width (2048 for Llama 3.2 1B). `m` is the `m` of `gemm` and of `rmsnorm`, so the add, the RMSNorm calls and the projections of a layer at T carry the same `m`; `n` is the `n` of `rmsnorm` and the output width `n` of the O and down projections whose result is the right operand. By ADR-0001 decision 6 this kind and its members raise no `schema_version`.
- **Every operand has the same shape `[m, n]`**: no broadcasting, no rank-1 operand.

### 3. Dtype and layout

- **Dtype `bf16`** for all three operands, as ADR-0156 decision 2 (the owner's bf16 inputs and outputs).
- **Layout `row_major`**, as ADR-0008 decision 2 with "the C type of its dtype" read as ADR-0156 decision 2 reads it: each element is one `uint16_t` holding a bf16 bit pattern, element (i, j) at index i·n + j, contiguous, no padding, no stride, no header. Only the rank-2 meaning is used (ADR-0158 decision 2's rank-1 meaning is not needed). Since all three operands have one shape and one contiguous storage, element (i, j) of each is at the same index, and a kernel may treat each as one array of m·n elements.

### 4. The operation and its precision

- **The operation** (Meta's `x + ...`, lines 252-253): c(i, j) = a(i, j) + b(i, j), for 0 ≤ i < m, 0 ≤ j < n. No scaling, no third operand, no accumulation into a prior content of c.
- **The kernel converts its inputs** (**owner**, HQ-0065 (3)); widening bf16 to binary32 is exact (ADR-0154 decision 3).
- **The obligation is on the result: each element of c is the correctly rounded bf16 value of the exact sum a(i, j) + b(i, j)** under round to nearest, ties to even (decision 5), for finite inputs that are not subnormal and whose exact sum is 0 or not below the normal range (the rest is decision 5 and Boundaries). **The means are the kernel's choice.** A binary32 add followed by the conversion of decision 5 suffices, and so does an add in any wider binary format (the argument below); an instruction of the target that adds bf16 values qualifies when its result is that value. An intermediate narrower than binary32 does not suffice in general: an fp16 sum overflows above 65504 and drops low bits of an operand whose exponent is far below the other's, and a sum truncated to bf16 is not correctly rounded. Reasons: the owner's three sums do not cover this step (ADR-0154 decision 2), so this record chooses it; a binary32 add already gives the correctly rounded result, so the strongest obligation costs a kernel nothing; it leaves exactly one right output bit pattern per element for every kernel of the contract, so a tolerance means the same for all of them; and any method that misses that value adds error that the float64 reference counts against the kernel.
- **Double rounding is innocuous here — the argument.** Let a and b be finite bf16 values, neither subnormal, and |a| ≥ |b|. If b = 0 the sum is a as a real number and nothing is rounded (the sign of a zero is decision 5). Otherwise let 2^e ≤ |a| < 2^(e+1), 2^f ≤ |b| < 2^(f+1) and d = e − f ≥ 0. Write RN32 and RNbf for round to nearest, ties to even, to binary32 and to bf16.
  - **d ≤ 15**: a and b are integer multiples of 2^(f−7) (8 significant bits), so their exact sum s is N·2^(f−7) with |s| < 2^(e+2), that is |N| < 2^(d+9) ≤ 2^24. N fits the 24 significant bits of binary32 and the exponent f − 7 ≥ −133 lies inside binary32's range, so s is a binary32 value unless |s| ≥ 2^128, where RN32(s) and RNbf(s) are both an infinity of the sign of s (the largest finite bf16 value plus half its unit in the last place is 2^128 − 2^119, and a tie there goes to the even neighbour 2^128, which overflows). Otherwise RN32(s) = s and only the bf16 rounding is left: RNbf(RN32(s)) = RNbf(s).
  - **d ≥ 16**: |b| < 2^(f+1) ≤ 2^(e−15). The bf16 neighbours of a lie at a distance of at least 2^(e−8) (2^(e−7) above, 2^(e−8) below when |a| = 2^e), so every real number within 2^(e−9) of a rounds to a in bf16, with no tie. s lies strictly within 2^(e−15) of a; a − 2^(e−15) and a + 2^(e−15) are binary32 values (multiples of 2^(e−24) of magnitude below 2^(e+1)), and rounding is monotone, so RN32(s) lies between them as well. Hence RNbf(RN32(s)) = a = RNbf(s).
  - So **a binary32 add followed by a round-to-nearest-even conversion gives the correctly rounded bf16 sum of any two non-subnormal finite bf16 values**, overflow to infinity included. The same two cases hold for any binary format with at least 24 significant bits and at least the exponent range of binary32 (binary64 among them), with 15 replaced by that count minus 9. **Checked** on 2026-10-24 in a throwaway Python interpreter with exact rational arithmetic (`fractions.Fraction`): all 65536 pairs of the value set of decision 10 and 300000 pseudo-random pairs over the finite bf16 values, half of them with nearby exponents; no pair gave RNbf(RN32(s)) ≠ RNbf(s). The argument, not the check, is the support. Subnormal inputs and a sum below the normal range are Boundaries (decision 5).
- **Compared with Meta** (lines 252-253): in a bf16 model `x + ...` adds two bf16 tensors and returns a bf16 tensor; at the level of `model.py` that output is the only bf16 value the add produces, as in this contract, so **this record departs from Meta's order nowhere**, unlike ADR-0158 decision 3 for RMSNorm. How PyTorch forms that sum internally was not read and is not relied on: if its result is the correctly rounded sum, as an evaluation in binary32 followed by round-to-nearest-even gives by the argument above, the kernel's output equals Meta's bit for bit. Whether the model-level comparison needs anything of Meta's arithmetic is OD-31 sub-question 6 (owner).
- **How close a result must be is the tolerance** (FR-9; **owner**, HQ-0066 (2), no value here). The verification compares within the instance's `rtol` and `atol` only, so a kernel that is not correctly rounded and stays within them is not detected; the obligation stands either way.

### 5. The conversion of the output to bf16

- **The contract fixes it: round to nearest, ties to even**, from the exact sum, or from the binary32 or wider sum of decision 4, to bf16, for the reasons of ADR-0156 decision 4, which carry over unchanged (cited). By decision 4 both give the same bf16 value.
- **Zero**: an exact sum of 0 from two non-zero operands is +0, and (−0) + (−0) is −0, as IEEE 754 defines the sign of an exact zero sum under round to nearest. The comparison with `rtol` and `atol` does not see the sign of a zero.
- **Range**: for the inputs of decision 10 every exact sum has a magnitude of at most 1.9921875, so the output never overflows; a sum is 0 exactly when b(i, j) = −a(i, j), and every other sum has a magnitude of at least 2^−8, so no output is subnormal. For finite inputs outside that set a sum can overflow, becoming an infinity of its sign as roundTiesToEven defines overflow (as ADR-0156 decision 4); subnormal inputs, a non-zero sum below the normal range (from two normal inputs of opposite sign that nearly cancel), and what a kernel produces from non-finite inputs are not defined here (Boundaries).

### 6. The C prototype and the symbol

```c
void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte, in every spec of this contract whatever the shape: single spaces as shown, no line break, the semicolon included. `size_t` is that of `<stddef.h>`, `uint16_t` that of `<stdint.h>`; valid in C99 and later.
- **Order**: dimensions first as ADR-0008 decision 4, then the arrays in the order input a, input b, output c — the names and order of ADR-0008's operands, with c = a + b in the order of Meta's `x + ...`; `void`, since the result is the output only; `restrict` on all three states the no-overlap guarantee of decision 8.
- **Operand type `uint16_t`** (**owner**, HQ-0065 (3)).
- **Symbol `hilclaw_elementwise_add_bf16`**: `hilclaw_`, the kind, `_` and the dtype — the form of ADR-0156 decision 5 and ADR-0158 decision 5, for their reasons (a wrong binding fails at `dlsym`, and kernels of several dtypes may share a link unit if contracts of other dtypes come). This record sets no naming rule for other kinds; it only chooses this name.

### 7. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `a` | `input` | `bf16` | `[m, n]` | `const uint16_t *restrict a` |
| `b` | `input` | `bf16` | `[m, n]` | `const uint16_t *restrict b` |
| `c` | `output` | `bf16` | `[m, n]` | `uint16_t *restrict c` |

As ADR-0008 decision 5: in parameter order, with the values of the spec's `op_signature` shape in place of `m` and `n`; the dimensions have no entry. The complete `task.contract` at T = 1:

```json
{
  "language": "c",
  "prototype": "void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);",
  "operands": [
    {"name": "a", "role": "input", "dtype": "bf16", "shape": [1, 2048]},
    {"name": "b", "role": "input", "dtype": "bf16", "shape": [1, 2048]},
    {"name": "c", "role": "output", "dtype": "bf16", "shape": [1, 2048]}
  ]
}
```

**Validated on 2026-10-24** with `hilclaw.spec.validate`, inside the committed spec example `examples/spec/gemm-485b9bc494d477eb.json` with its op_signature replaced by the T = 1 record of decision 11 (key and record) and its `task.contract` by the object above, in a throwaway interpreter that added `"elementwise_add": frozenset({"m", "n"})` to `hilclaw.keys._SHAPE_MEMBERS` in memory: accepted; the same spec with the shape of `b` changed to `[1, 2049]` was refused. No repository file was changed.

### 8. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | `m` and `n` are each at least 1; `a`, `b` and `c` have exactly m·n elements each. | Compute the operation for the values it is called with. |
| Overlap | The three arrays do not overlap each other; in particular `c` is neither `a` nor `b` (no in-place call). | — |
| Inputs | Every element of `a` and `b` is an initialised `uint16_t` holding a bf16 bit pattern, stored in the layout of decision 3, and nobody else changes them during the call. | Not modify them. |
| Output | The content of `c` on entry is unspecified. | Not read `c` before writing it, and write **every** one of its m·n elements, each the bf16 pattern of decisions 4 and 5, before it returns. |
| Alignment | Each pointer is aligned for `uint16_t`. Nothing more is promised. | Not assume a larger alignment. |
| Memory, repeated calls, completion, result | As ADR-0008 decision 6. | As ADR-0008 decision 6. |

- **No in-place call**, although the add is the one kind where it would be natural: in the pass, neither input of row 9 or row 14 is read after the add (ADR-0152 decision 2: the block's input `x` was last read by rows 2 and 9, and `h` is last read by rows 10 and 14), so writing the sum over the residual operand would be safe. It is refused because (1) `restrict` on every operand, which lets a compiler vectorise without overlap checks, would be lost for one kind only; (2) ADR-0153 decision 3 lists "distinct arrays for each operand" among the caller's guarantees the executor keeps, and an in-place permission would make the executor's rule differ by kind; (3) it costs no copy: with two residual buffers that alternate — row 9 reads the layer input from one and writes h into the other, row 14 reads h and writes the layer output back into the first — every call has distinct arrays, and the model program owns its buffers (ADR-0153 decision 4); and (4) ADR-0158 decision 7 already refuses it for RMSNorm. The two buffers are an example for the code slice, not a buffer layout this record fixes.
- **Every set of dimensions**: the obligation is stated for the values passed, so **a kernel must be correct for every m, n ≥ 1**, and may be specialised for its own shape only while staying correct elsewhere. A binding "for every shape" of ADR-0153 decision 3 is therefore accepted for this contract. Whether a verification passes other values stays OD-16 sub-question 1.
- **No shape that holds a 0**: the caller's guarantee of at least 1 has the same form as ADR-0008's, so ADR-0037's reading carries over — this contract defines no `task.contract` and no call for a shape with a 0.
- **Finiteness** is not part of the input guarantee, as in ADR-0008 decision 6; what a kernel produces for non-finite or subnormal inputs is Boundaries.

### 9. What the kernel source provides

- As ADR-0008 decision 7 with the name of decision 6: **exactly one definition of `hilclaw_elementwise_add_bf16`**, with external linkage and the prototype of decision 6; **no `main`**; no other identifier with external linkage that starts with `hilclaw_` (`hilclaw_gemm`, `hilclaw_gemm_bf16` and `hilclaw_rmsnorm_bf16` included).
- It may include the headers ADR-0008 decision 7 allows. Whether OpenMP is usable on `cpu_standin` (HQ-0034) is a build setting (Boundaries).

### 10. The input value set of verification

- **Owner** (HQ-0066 (3)): each kind's input distribution is fixed by a driver record, finite inputs only. **This record fixes the value set; the rest is the P2-12 harness record's.**
- **a and b**: every drawn element is **exactly one of the 256 bf16 values of magnitude in [0.5, 1) with either sign**, ±(0.5 + j/256) for j = 0 … 127, the set of ADR-0156 decision 9.
- **Reasons and computed facts** (by exact rational arithmetic over all 65536 ordered pairs, in the interpreter of decision 4): no input is zero or subnormal. Every value is a multiple of 2^−8, so every exact sum is too, and the float64 reference's sum is exact. A sum of two values of one sign lies in [1, 1.9921875]; there the bf16 spacing is 2^−7, so a sum with an odd multiple of 2^−8 is a tie, decided by ties-to-even. A sum of two values of opposite sign lies in [−0.49609375, 0.49609375] and is exactly a bf16 value. Of the 65536 pairs, 49152 sums are exact (256 of them 0), and 16384 are ties. **So a correct kernel differs from the reference by 0 on three quarters of the pairs and by exactly 2^−8 on the ties**, a relative difference of at most 1/257 (about 0.0039); this is a fact of the set, not a tolerance.
- **What the set detects**: a dropped operand moves an element by |b| ≥ 0.5; a subtraction in place of the add by 2|b| within one rounding of 2^−8, so by at least 1 − 2^−8; a sum written to the wrong element or read from the wrong row gives a different value unless the drawn values coincide there, which depends on the draws (P2-12); whether these displacements exceed `atol` + `rtol`·|ref| depends on the instance's tolerance and is not promised (as ADR-0156 decision 9). **The output rounding of decision 5 is not detected by this set**: every inexact sum is a tie, exactly half-way between its two bf16 neighbours, so a correct kernel, a truncating one and one that rounds ties away from zero all miss the reference by the same 2^−8 there, and every other sum is exact under any rounding; no `rtol` and `atol` pass the one and fail the others. (Truncation and round-to-nearest-even give different outputs on 8192 of the 65536 pairs, but at the same distance from the reference.) Decision 5 stands untested, as ADR-0158 decision 9 accepts for `eps`. An intermediate with at least 9 significant bits — fp16 among them — gives the correct output on every pair of the set, since every sum there is a multiple of 2^−8 below 2 in magnitude and so needs at most 9 significant bits; such a kernel is not told apart by this set, and its obligation (decision 4) stands either way. **Not detected**: swapped operands, which give the same result because the correctly rounded sum is symmetric in a and b — not an error.
- **Cancellation to zero** occurs when b(i, j) = −a(i, j) (256 of the 65536 pairs). The reference is then exactly 0 and the correct output is +0, so the element passes for any `atol` ≥ 0; a kernel wrong there by e passes only if e ≤ `atol`, because `rtol`·|ref| is 0. That is the comparison of FR-9 working as stated, not a gap: the reference is exact at these elements. The choice of `atol` stays the user's.
- **Left to the P2-12 harness record**: the generator, its seed, the number of draws, whether a and b are drawn independently, the content of `c` before the call, and the widening for the float64 reference — the inputs (**owner**, HQ-0066 (1)) and the output (cited: ADR-0154 decision 3). **No tolerance value or default is chosen** (**owner**, HQ-0066 (2)).

### 11. The `op_signature` records

**Rule**: `{"schema_version": 1, "kind": "elementwise_add", "shape": {"m": T, "n": 2048}, "dtype": "bf16", "layout": "row_major"}` for T ∈ {1, 32, 512}, the shape set of rows 9 and 14 (ADR-0152 decision 5); **the two calls of a layer and all layers share these records**, since the key names the operation and not its place. At T = 1:

```
{"dtype":"bf16","kind":"elementwise_add","layout":"row_major","schema_version":1,"shape":{"m":1,"n":2048}}
sha256 = 1af54bf2a0744c6977bb2d6411d15fb0a9cbdf0a997e159879d84bfe21708bce  ->  elementwise_add-1af54bf2a0744c69
```

| T | 1 | 32 | 512 |
|---|---|---|---|
| Directory name | `elementwise_add-1af54bf2a0744c69` | `elementwise_add-7ca4cdf06f7c3008` | `elementwise_add-dd63031857ec45cd` |

- **Method**: `hilclaw.keys.op_signature_key` in the throwaway interpreter of decision 7 (kind added in memory, no repository change). The same interpreter gave `rmsnorm-57f1bdf44f626c31` for the `rmsnorm` record at T = 1, the name of ADR-0158 decision 10.
- **How a shape set maps to instances** stays OD-6 sub-question 3. **Change of the contract**: ADR-0008 decision 8 holds as for fp32 (a storage change is a new `layout` value; any other change is OD-6 sub-question 4).

### 12. The two call sites

- **`attention_residual`** for row 9 and **`ffn_residual`** for row 14, in that order (the order of ADR-0152 decision 2). Reason: Meta gives the adds no module, so each is named after the module whose output it adds, with the `_residual` suffix for the residual connection, in the prefixes Meta already uses for the norm before it (`attention_norm`, `ffn_norm`, lines 242-243) — the names `hilclaw/model_binding.py` takes for the RMSNorm call sites. Both are distinct from every GEMM and RMSNorm call-site name.
- **The operands each call passes**:

| Call site | `a` | `b` | `c` |
|---|---|---|---|
| `attention_residual` (row 9) | the layer's input, Meta's `x`: the embedding rows (row 1) for the first layer, the output `c` of the previous layer's `ffn_residual` otherwise | the output of the O projection of the same layer (row 8) | Meta's `h`, read by rows 10 and 14 |
| `ffn_residual` (row 14) | `h`, the output `c` of `attention_residual` of the same layer | the output of the down projection of the same layer (row 13) | the layer's output, the next layer's `x`, or after the last layer the input of the final RMSNorm (row 15) |

- `a` is always the residual stream and `b` the module's output, as in Meta's `x + ...`; the correctly rounded sum does not depend on this order (decision 10), which is fixed so that the code slice chooses nothing.

### 13. Order and runs

This record chooses no order of kinds, no instance and no run, as ADR-0158 decision 11: when an elementwise add instance runs is not said here, and B-4's run order ("GEMM first, then the attention family") stands (ADR-0152 Boundaries).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Kind `add` or `residual_add` | `add` would leave no plain name for a later broadcasting (bias) add; `residual_add` names the place in the model, not the operation (ADR-0001 decision 2). |
| 2 | One member `n` = T·2048 over flat operands | For a contiguous add the computation depends on m·n only, but one member loses T, which the GEMM projections and RMSNorm carry in `m`, and the executor's T × 2048 buffers would need a second shape convention. Within the Llama shape set no two records would coincide either way. |
| 4 | Binary32 or wider with no obligation on the result, as ADR-0158 decision 3 for its other steps | Would allow kernels that differ at the last bit for no gain: a binary32 add already gives the correctly rounded result (decision 4). |
| 4 | Exactly binary32 | A wider format gives the same bf16 output (decision 4); forbidding it buys nothing. |
| 4 | Leave the result to the kernel's precision (any intermediate format allowed, the result not obliged) | A narrower intermediate can miss the correctly rounded value (decision 4), adding error the float64 reference counts against the kernel at the kernel's choice; a tolerance would mean different things for kernels of one contract. |
| 5 | Truncation, or the rounding left to the kernel | The reasons of ADR-0156 decision 4 (cited). |
| 6 | Operand names `x`, `y`, `out` or `x`, `h` | Both work; `a`, `b`, `c` are ADR-0008's names for the two inputs and the output and carry no model role, which the call-site table of decision 12 gives. |
| 6 | Symbol `hilclaw_elementwise_add` | Gives up the load-time stop of ADR-0156 decision 5 if a contract of another dtype comes. |
| 8 | Allow in-place (`c` = `a`, or `c` = `a` or `b`), without `restrict` | Natural for a residual add, but loses `restrict` for one kind, makes the executor's "distinct arrays" rule (ADR-0153 decision 3) differ by kind, and saves no copy, since two alternating buffers give distinct arrays (decision 8). |
| 10 | Values over the whole finite bf16 range, or uniform in [−1, 1] | Bring zero, subnormal, overflowing and nearly cancelling sums, corner cases kept for later (#5 B-7, OD-16). |
| 10 | Operands of distant magnitudes (for example b in ±[2^−5, 2^−4)), so that some sums are inexact without a tie | A truncating kernel would then be told apart only under a tolerance the user sets between half and one bf16 unit in the last place, and the set would no longer be the one shared with ADR-0156 and ADR-0158 that one harness generator draws from; decision 5 stands either way. |
| 10 | Inputs of one sign only (no cancellation) | Would leave out the opposite-sign sums, which test the sign handling and give exact results; cancellation to 0 is harmless for the comparison (decision 10). |
| 12 | `residual_1`, `residual_2`, or `attention_add`, `ffn_add` | Numbers say nothing of the place; `_residual` names the connection Meta's code builds, after Meta's module prefixes. |

## Consequences

- **A-13 reading**: no schema file, member, file, version or validator of the data plane changes, and `hilclaw/` is not touched. The new kind `elementwise_add` with members `m` and `n` is a value ADR-0001 decision 6 admits without a version change. Teaching `hilclaw.keys` the kind is a later code slice.
- **The code slice this record makes possible** (for the planner; no code here): the kind and its members in `hilclaw.keys`; a contract module like `hilclaw/rmsnorm_bf16_contract.py` (constants, `task_contract`, `covers`, `op_signature_record`, the value set); the binding check in `hilclaw/model_binding.py` with the call sites `attention_residual` and `ffn_residual` of decision 12, their shapes (rows × hidden) and the "every shape" binding, `bf16` as the only dtype at which the kind is known; hand-written bf16 elementwise add kernels as test fixtures (a correctly rounded one, and for the harness wrong ones whose error the value set makes large, such as one that drops an operand or subtracts, which fail under a tolerance tighter than that error); and the P2-12 harness part (generator over the value set, widening, comparison).
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` for "elementwise add", "other four kinds", "other five kinds", "future contract records" and "Each kind's contract"; not claimed complete): ADR-0152 Status ("Answers": "each kind's contract and `op_signature`" open), decision 1's naming bullet ("each kind's value, `op_signature` members and contract are later records"), decision 7, Consequences (the planner's next steps) and Boundaries ("Each kind's contract"); ADR-0153 decision 3 ("future contract records", "for every other kind, its contract record says"), decision 6 ("each kind's contract"), Consequences code slice (2) ("the other five kinds") and Boundaries ("Each kind's contract"); ADR-0154 Consequences ("What is now unblocked") and Boundaries ("Each kind's contract"); ADR-0156 Boundaries ("the other five kinds"); ADR-0157 decisions 4 and 5 and Boundaries ("the other five kinds"); ADR-0158 Boundaries ("the other four kinds"). This record now answers them for the elementwise add.
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: each output element obliged to be the correctly rounded bf16 sum, by any means, a binary32 or wider add followed by round-to-nearest-even sufficing by the double-rounding argument (decision 4); no departure from Meta's order of roundings (decision 4); no in-place call although the residual add would allow one, with two alternating buffers instead (decision 8); the kind name `elementwise_add` and the members `m`, `n` (decision 2); the call-site names `attention_residual` and `ffn_residual` and their operand order (decision 12); the verification values in ±[0.5, 1), with cancellation to 0, under which the output rounding is not detected (decision 10).
- **UsageCases and StandardScenarios** (S0 and S1 re-checked, and every scenario row citing OD-6 sub-question 1 or OD-31): no use case step changes. S0 step 4 keeps its open kernel contracts outside `gemm`, `rmsnorm`, `elementwise_add` and C, its note now naming `elementwise_add` (OD-6 sub-question 1, OD-31 sub-question 1); S0 step 5 and S1 step 2 keep OD-31 sub-question 3 and #5 B-7 for the vocabulary outside the first case and the Llama kinds on `cpu_standin`. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **fp16**: when and in what form, after PLAN P2-14 (owner, HQ-0065 (1)); **an fp32 contract of this kind**, which ADR-0157 decision 4 would need for an fp32 full pass.
- **Tolerance values**: instance parameters set by the user (FR-9; owner, HQ-0066 (2), no default).
- **Build settings and OpenMP**: compiler flags, `-ffp-contract`, flags that relax IEEE arithmetic, the floating-point environment (flushing subnormals included), OpenMP and thread count (HQ-0033, HQ-0034, OD-6 sub-question 2).
- **The harness mechanism** of a bf16 elementwise add verification and timing run, and the parts of decision 10 left to it (PLAN P2-12).
- **Corner-case, non-finite and subnormal inputs and outputs**, overflowing sums beyond the rule of decision 5, and nearly cancelling sums below the normal range (#5 B-7, OD-16).
- **Shapes outside an instance's** (OD-16 sub-question 1); **how a shape set maps to instances** (OD-6 sub-question 3); **contract change and keys** (OD-6 sub-question 4).
- **The contracts of the other three kinds** — SwiGLU activation, RoPE, SDPA with KV cache — one record each, and their symbol names.
- **Backends other than `cpu_standin`** and their representation of bf16 (#5 B-2, B-7).
- **The weights and their conversion to bf16** (OD-31 sub-question 5, owner); the model-level comparison (sub-question 6, owner).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, PLAN P1-5), to ADR-0156 or to ADR-0158.

## References

- Owner: HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1), C-6 revision (K2); [Requirements](../Requirements.md) C-6, FR-5, FR-9, OD-6, OD-16, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-6 (sub-questions 1, 3, 4) and § OD-31 (sub-questions 1 to 3, 5, 6).
- Records: [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 2 and 6; record format), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0037](ADR-0037-od6-gemm-contract-zero-dimension.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md), [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0157](ADR-0157-od31-executor-call-site-dtype.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md).
- Meta: `meta-llama/llama-models` at `0e0b8c519242d5833d8c11bffc1232b77ad7f301`, `models/llama3/model.py` (lines 242-243, 252-253), read through `gh api`.
- Code read: `hilclaw/keys.py`, `hilclaw/spec.py` (`validate`), `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/model_binding.py`; `examples/spec/gemm-485b9bc494d477eb.json`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
