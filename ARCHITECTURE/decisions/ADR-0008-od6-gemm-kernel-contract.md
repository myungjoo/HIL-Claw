# ADR-0008: Operational contract of the `gemm` kind for C kernels, with the first `layout` value (one part of the rest of OD-6)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of the rest of OD-6** (Open Decisions register in [Requirements](../Requirements.md)): sub-question ① of [OpenDecisionProposals OD-6](../OpenDecisionProposals.md#od-6), the *values* of the operational contract of the kind `gemm` for kernels written in C — together with the **first `layout` value**, which OD-4 left open ([ADR-0001](ADR-0001-od4-key-schema.md) decision 7). Both register rows keep their status.
- What stays open: the rest of OD-6 (selection rule of the feedback part, profile summary, forbidden patterns, excerpts, sub-questions ② and ③, and the sub-question ④ this record raises), the rest of OD-4 (similarity layer, hw-side values), and every item under Boundaries.
- It gives values to fields that ADR-0001 (`layout`) and [ADR-0002](ADR-0002-od6-codegen-spec.md) (`task.contract`) define, and adds or changes no field of either schema. The objection windows of both records run until 2026-10-13; if either is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- A kernel cannot be written, built into a harness, calibrated or timed before it is known how it is called. Three accepted records leave exactly this open: ADR-0001 makes `layout` a required key field and gives it no value ("B-4 gives no layout"); ADR-0002 decision 6 (a) says that a spec carries the contract of an operation kind in `task.contract` "and does not define it"; [ADR-0003](ADR-0003-od16-harness-calibration.md) makes the calibration kernels of PLAN P1-4 depend on "the kernel prototype".
- Fixed inputs. #5 A-7 ②: stand-in kernels are C, compiled with clang as the single toolchain; OpenMP and SIMD intrinsics are allowed. #5 B-4: the first operations are the decoder projections of Llama 3.2 1B — gate/up 2048→8192, down 8192→2048, QKV 2048→3072, O 2048→2048 — with M ∈ {1, 32, 512}, dtype fp32 ("bf16 weights upcast"); only the shapes are used, no weights. C-7: the same behaviour on Linux, macOS and WSL.
- ADR-0001 decision 2: for `gemm`, `shape` has exactly `m`, `k`, `n` — "the product of an m×k and a k×n matrix is an m×n matrix"; for a projection `in`→`out` over M tokens, `m` = M, `k` = `in`, `n` = `out`; "how the operands are stored or transposed is `layout` and the spec". A `layout` value is a *name* (`[a-z][a-z0-9_]{0,31}`).
- ADR-0002 decision 2: `task.contract` has `language` (name), `prototype` (text: the declaration of the entry point, "exactly as the harness calls it") and `operands` (one `{name, role, dtype, shape}` per data operand; every shape value is a value of the `op_signature` shape). A spec has one `op_signature`, so one value of M.
- FR-9 and ADR-0003: the harness, not the coder, calls the kernel, and the hand-written calibration kernels are called the same way. [ADR-0007](ADR-0007-od13-measurement-policy.md) decision 2: a timing sample covers the execution of the kernel on operands that are already prepared.
- Not available as inputs, and not needed below: the reference oracle and the tolerance (#5 A-7 "still open", B-7), the harness mechanism (PLAN P1-3), build settings, the hw-side values.

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice.

### 1. Scope and terms

- **The operational contract of a kind** is what both sides of a call must know: the meaning of one `layout` value, and the values of `task.contract` — the language, the prototype of the entry point and the operand entries — with the guarantees and obligations of decisions 6 and 7.
- This record defines one contract. It is bound to kind `gemm`, dtype `fp32` (cited: #5 B-4), layout `row_major` (decision 2) and kernel language `c` (cited: #5 A-7 ②). Another kind, dtype, layout or language has another contract, defined by its own record.
- The contract **binds both sides**: the caller (the harness, or any program that calls a kernel) guarantees what decision 6 lists, and a kernel must do what decisions 3, 6 and 7 list. It holds for coder output and for hand-written kernels (the calibration fixtures of ADR-0003) alike.

### 2. The first `layout` value: `row_major`

- **Name**: `row_major`. It matches the name pattern and is accepted by `hilclaw.keys`.
- **Meaning**, for a matrix operand of r rows and c columns: the operand is **one contiguous array of exactly r·c elements** of the C type of its dtype, and element (i, j), counted from 0, is at index **i·c + j**. There is no padding between or after rows, no row stride or leading dimension other than c, no offset before the first element and no header. The elements have the representation of that C type on the host that runs the kernel.
- **Every operand** of the operation is stored this way, with r and c taken from the `shape` of its operand entry in that order (`[r, c]`). No operand is stored transposed, packed or blocked. The value therefore says everything about storage: **an operand entry needs no member beyond the four of ADR-0002**, and the provision of ADR-0002 decision 6 (a) for further storage members is not used.
- The value is defined here for two-dimensional operands. What it means for an operand of another rank is said by the record of the first kind that has one.
- **The vocabulary of `layout` stays open** (ADR-0001 decision 6). Any other storage — column-major, a weight handed over in another order, aligned or padded rows, a packed form — is another `layout` value: another key, and no schema change.

### 3. The operation

- A is the m×k matrix, B the k×n matrix and C the m×n matrix of ADR-0001. The kernel computes the **plain product**: C(i, j) = Σ over p of A(i, p)·B(p, j), for 0 ≤ i < m, 0 ≤ j < n, 0 ≤ p < k. For a projection, A holds the M input vectors as rows, B the weights and C the M output vectors as rows.
- **Excluded**, each because no `op_signature` field or source asks for it and it would be a dead parameter that every kernel has to handle: scaling factors (the α and β of BLAS), accumulation into the output (C is overwritten, not added to), transposition flags, and a bias term (B-4 names projections by their shapes only).
- The product is the real-number product evaluated in `fp32`. The order of the additions, the use of fused multiply-add and the precision of intermediate values are the kernel's choice; how close the result must be is the tolerance (FR-9, #5 B-7) and is not decided here.
- **The weight operand is handed to the kernel as the k×n matrix B, that is in `[in, out]` order.** This is the reading ADR-0001 states ("an m×k and a k×n matrix"), it needs no transposition flag, and every operand shape is written with `op_signature` values in the order of the definition. The alternative — B in the `[out, in]` order that model files commonly use, so that the kernel computes A·Bᵀ — is not excluded: it is another `layout` value (decision 2). No source says in which order the weights reach a kernel at deployment (B-4 uses the shapes only, and "bf16 weights upcast" places a conversion before the kernel in any case), so this choice is a design choice of this record and is listed in the owner notice as a reading to check. Both orders read B in contiguous runs at M = 1, so neither is a handicap for the first kernels.

### 4. The C prototype of the entry point

```c
void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);
```

- **This single line is the text of `task.contract.prototype`**, byte for byte: single spaces as shown, no line break, the terminating semicolon included. It is the same text in every spec of this contract, whatever the shape. `size_t` is the type of `<stddef.h>`; the declaration is valid in C99 and later (`restrict`). Which language standard a build selects is a build setting (Boundaries).
- **Symbol name**: `hilclaw_` followed by the `kind`. The prefix keeps the name apart from the C library, the BLAS interfaces and the kernel's own helpers; the kind keeps it apart from the entry point of any later kind, whose name its own record chooses. Contracts of the same kind that differ in dtype, layout or language are not defined here, and neither is whether they reuse this name.
- **Return type** `void`: the result of a kernel is the output operand only (decision 6), and the contract defines no error return.
- **Dimensions are parameters**, in the order `m`, `k`, `n` of the definition, before the operands. The prototype is then one text for all twelve first instances and for the calibration kernels, which ADR-0003 lets the tests run at any shape of the kind.
- **Operands** in the order A, B, C: `a` and `b` are pointers to `const float`, `c` a pointer to `float`. `fp32` is the C type `float`, which is IEEE 754 binary32 on the platforms of C-7. `restrict` states the no-overlap guarantee of decision 6 in the declaration.

### 5. The operand entries

| `name` | `role` | `dtype` | `shape` | Parameter |
|---|---|---|---|---|
| `a` | `input` | `fp32` | `[m, k]` | `const float *restrict a` |
| `b` | `input` | `fp32` | `[k, n]` | `const float *restrict b` |
| `c` | `output` | `fp32` | `[m, n]` | `float *restrict c` |

The entries are listed in the order of the parameters, with the values of the spec's `op_signature` shape in place of `m`, `k`, `n`. The dimension parameters are not data operands and have no entry. The complete `task.contract` for gate/up (2048→8192) at M = 1, accepted by `hilclaw.spec.validate` inside an otherwise valid spec:

```json
{
  "language": "c",
  "prototype": "void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);",
  "operands": [
    {"name": "a", "role": "input", "dtype": "fp32", "shape": [1, 2048]},
    {"name": "b", "role": "input", "dtype": "fp32", "shape": [2048, 8192]},
    {"name": "c", "role": "output", "dtype": "fp32", "shape": [1, 8192]}
  ]
}
```

### 6. Guarantees and obligations at a call

| Point | The caller guarantees | The kernel must |
|---|---|---|
| Dimensions | `m`, `k`, `n` are each at least 1, and the three arrays have exactly m·k, k·n and m·n elements. | Compute the product for the values it is called with. |
| Overlap | The three arrays do not overlap each other. | — |
| Inputs | Every element of `a` and `b` is an initialised `float`, stored in the layout of decision 2, and nobody else changes them during the call. | Not modify them. |
| Output | The content of `c` on entry is unspecified. | Not read `c` before writing it, and write **every** one of its m·n elements before it returns. |
| Alignment | Each pointer is aligned for `float`. Nothing more is promised. | Not assume a larger alignment. |
| Memory | The caller owns the three arrays, before and after the call. | Access nothing through the three pointers outside the arrays, and keep none of the pointers or addresses derived from them after it returns. |
| Repeated calls | The entry point may be called any number of times in one process, with the same or different dimensions and contents. It is not called again before it has returned. | Give a result that depends on the arguments of this call only — not on an earlier call, its inputs or its output. |
| Completion | — | Have finished all its work on the operands when it returns, including the work of any thread it started. |
| Result | Only the content of `c` after the return is the result of a call. | Not rely on anything else being read: a return value does not exist, and output streams, files and global objects are not results. |

- **Dimension values other than those of the `op_signature`.** The obligation is stated for the values passed, so a kernel that is correct for every m, k, n ≥ 1 satisfies it in all cases, and it may be as specialised as it likes for the shape of its spec as long as it stays correct elsewhere. Whether a caller ever passes other values is OD-16 sub-question ① and **stays open**; this record neither promises the kernel that it does not happen nor makes the harness do it.
- **Alignment**: only the alignment of the element type is promised, because a kernel correct under the weaker promise is correct under every allocation, and a stronger promise could not be withdrawn later without breaking stored kernels (decision 8). A caller may align more; a kernel must not depend on it.
- **State between calls**: a kernel may keep state that does not change its results (a started thread pool, scratch memory of its own). Whether a harness detects a kernel whose result does depend on an earlier call is a defence of OD-16 (threat B ⑸) and is not adopted here; the obligation stands either way.
- Threads are allowed (#5 A-7 ②: OpenMP); how many is a build or run setting (Boundaries).
- The guarantee on the inputs does not say that they are finite. What a kernel must produce for non-finite values, and whether verification draws them, goes with the oracle and the corner cases (Boundaries).

### 7. What the kernel source provides

- The source of a kernel — however many files it has (OD-23) — contains **exactly one definition of `hilclaw_gemm`**, with external linkage and with the prototype of decision 4.
- It defines **no `main`** and no other identifier with external linkage that starts with `hilclaw_`: the caller provides the program, and that prefix is reserved for the contract and the caller. Other helpers are best given internal linkage (`static`).
- It may include the headers of the C standard library, `<omp.h>` and the SIMD intrinsics headers of the target (#5 A-7 ②). Whether it may call into another library is not decided here (a new dependency, and threat B ⑶ of OD-16).
- How the caller gets from the source to a call — linking, loading, a separate process — is the harness mechanism (Boundaries). One consequence is stated because it follows from the prototype alone: two kernels of this contract define the same symbol.

### 8. Change of the contract

- `op_signature` keys do not contain the prototype, and `task.contract.language` is not a key field either. What is recorded with a stored kernel is **its spec**: every spec is kept unchanged (ADR-0002 decision 1) and carries `task.contract`, that is the language, the prototype text and the operand entries — the part of the contract that travels. For two kernels of the same `op_signature`, different `task.contract` objects therefore show different contracts, and this needs no new field. The converse does not hold: a change of a guarantee or an obligation of decisions 6 and 7 that leaves the prototype text as it is cannot be seen in a spec. Telling such kernels apart is part of the sub-question below.
- The contract of (`gemm`, `fp32`, `row_major`, `c`) is the one of this record. It is changed only by a record that supersedes this one (ADR-0001 "Record format"). A change of **storage** is never a change of this contract: it is a new `layout` value and therefore a new key (decision 2, ADR-0001 decisions 5 and 6).
- **Not decided, registered as sub-question ④ of OD-6**: what holds for the knowledge stored for a (hw_profile, op_signature) pair (best reference, statistics) when the contract of that `op_signature` changes in a way that is not storage — parameter order, a guarantee, the symbol name; how kernels written before and after a change that the prototype text does not show are told apart; what holds when the cases of the same `op_signature` under another hw_profile, whose kernels may be written in another language, are used as hints; and whether a change of contract must get a new key, and by which existing means (a `layout` value, a member of `ext`, a schema version).

### 9. The `op_signature` records of the first instances

With the layout fixed, the op side of the first instances is complete. **Rule**: `{"schema_version": 1, "kind": "gemm", "shape": {"m": M, "k": in, "n": out}, "dtype": "fp32", "layout": "row_major"}` for each of the four B-4 shapes and each M ∈ {1, 32, 512}. For gate/up at M = 1 this replaces the op-side placeholder of ADR-0001 decision 7 (the hw side keeps its placeholders, so the full path is still unknown):

```
{"dtype":"fp32","kind":"gemm","layout":"row_major","schema_version":1,"shape":{"k":2048,"m":1,"n":8192}}
sha256 = 485b9bc494d477ebc8c9f02f861c3795beadacfb4cf690680cfaecba09f2d431  ->  gemm-485b9bc494d477eb
```

Path: `db/<hw_profile_key>/gemm-485b9bc494d477eb/`. The twelve directory names, computed with `hilclaw.keys.op_signature_key`:

| Projection (`k`→`n`) | M = 1 | M = 32 | M = 512 |
|---|---|---|---|
| gate/up (2048→8192) | `gemm-485b9bc494d477eb` | `gemm-a463eb52b19cfa97` | `gemm-19d14734352e3486` |
| down (8192→2048) | `gemm-d79390d121a2056a` | `gemm-f5de54ee1d6995e0` | `gemm-4b417959d34765af` |
| QKV (2048→3072) | `gemm-446c3b3c15273a6a` | `gemm-e71a433ce31c1a8f` | `gemm-41e8dce9901bff41` |
| O (2048→2048) | `gemm-a11d79d7b957a0af` | `gemm-dc8beaf05ddb998c` | `gemm-66f7a94f78826a41` |

The names hold as long as ADR-0001 and this layout value stand. An optional `label` does not change them (it is an attribute).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Column-major as the first value | C code and the row-per-token reading of a projection are row-major; the integrator's working assumption was row-major (OpenDecisionProposals OD-4). It remains a possible later value. |
| 2 | A layout value that leaves stride, padding or alignment to members of the operand entry | A new member of the spec is a schema change (ADR-0002 decision 7, CLAUDE.md A-13), and no first kernel needs one. |
| 3 | Weight operand in `[out, in]` order, kernel computes A·Bᵀ | Contradicts the k×n statement of ADR-0001 unless it is a layout of its own; no source asks for it. Kept open as a later layout value and as a reading for the owner to check. |
| 3 | The general BLAS operation C ← α·op(A)·op(B) + β·C | Makes scaling and transposition run-time parameters that no key field fixes; every kernel would carry paths that are never measured. |
| 4 | The `cblas_sgemm` prototype itself | As above, and its `int` dimensions and leading-dimension parameters describe storage that decision 2 already fixes. |
| 4 | Dimensions as constants known from the spec, no parameters | One prototype text per shape; the calibration kernels could not share it; it would settle OD-16 sub-question ① by construction. |
| 4 | `int` dimensions | `size_t` is the C type for object sizes and index arithmetic; the cost is one standard header. |
| 4 | An `int` status as the return value | A second result channel whose meaning the verdict would have to define; ADR-0003 judges the output only. |
| 4 | One fixed symbol for every kind (for example `hilclaw_kernel`) | Entry points of two kinds could not coexist in one program. |
| 6 | A guaranteed alignment of 32 or 64 bytes | Binds every caller to an allocator choice and cannot be weakened later; unaligned SIMD loads are available on the stand-in. It can be offered as another `layout` value. |
| 6 | Output accumulated into, or zero on entry | Accumulation is excluded in decision 3; a zeroed output would put a caller-side pass over C next to every call. |
| 6 | The kernel may assume the dimensions of its `op_signature` | Would close OD-16 sub-question ① in the negative without being asked to. |
| 8 | The prototype, or a contract version, as a key field now | A new key field is a key-schema change; no stored kernel exists yet that a change could strand. Registered as a sub-question instead. |

## Consequences

- **P1-4 fixtures**: the three calibration kernels of ADR-0003 are C sources that each define `hilclaw_gemm` with this prototype; they can be written before the oracle and the tolerance are known. Because they define the same symbol, a harness program holds one kernel at a time unless its mechanism renames or isolates them.
- **Harness call site** (PLAN P1-2, P1-3): the caller prepares `a`, `b` and `c` as three separate arrays in the layout of decision 2 and calls `hilclaw_gemm(m, k, n, a, b, c)`. The timed interval of ADR-0007 covers calls of this form; how many of them one repeat times stays the harness design. The caller reads only `c` afterwards.
- **Committed spec example** (PLAN P1-5): the `op_signature` record, its key and the `task.contract` of the example are now real values. Still missing before the example is a valid spec of a real instance: the hw-side values and the `hw_profile` key, the form of a `run_id`, `task.objective` (OD-1) and a technique of the stand-in catalog.
- **C gate** (PLAN P0.5-1): it has something to build once the first C file of this contract exists; the gate itself is designed there.
- `hilclaw/keys.py` and `hilclaw/spec.py` are unchanged and accept the values of this record. The validator does not check that the `task.contract` of a spec is the one of this record; whether a tool does is left to the code task that writes specs.
- **A-13 reading**: no schema file, field, code or dependency changes. `row_major` is a new value of an existing field (ADR-0001 decision 6: not a schema change), and the `task.contract` object uses the members of ADR-0002 only.
- The same product is `cblas_sgemm(CblasRowMajor, CblasNoTrans, CblasNoTrans, m, n, k, 1.0f, a, k, b, n, 0.0f, c, n)`, so a comparison with that library needs a thin wrapper only. This is a remark on the prototype; it chooses no baseline (OD-28).
- The placeholders in ADR-0001 decision 7 and ADR-0002 decision 8 are not edited by this record; a note in them is a follow-up of task T-0030.

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: the reference oracle of `cpu_standin` (#5 A-7 "still open"; PLAN P1-3 "오너 확정 필요") and the tolerance vocabulary or any tolerance value (#5 B-7); `task.objective` (OD-1, #5 A-4); the target NPU and its kernel language (#5 B-1); OD-3; OD-25; C-6.
- **Verification inputs**: how they are drawn (distribution, seed, number of draws), whether shapes outside the `op_signature` are drawn (OD-16 sub-question ①), corner-case inputs and what a kernel must produce for non-finite values.
- **The harness mechanism** (PLAN P1-3; ADR-0007 Boundaries): linking, loading or a separate process, the driver program, how two kernels of one contract are kept apart, the timer, calls per repeat, reuse of inputs, how the arrays are allocated; sandbox, timeouts and resource limits (OD-14).
- **Build settings**: compiler flags, the language standard, `-march`, the OpenMP runtime and thread count, the members of `task.build`, whether the coder may choose settings (OD-6 sub-question ②), and whether a kernel may link another library.
- **The hw side**: `hw_source`, `revision`, the `host` strings and the clang version string of `cpu_standin` (OD-26 and the task that registers the profile); a technique of the stand-in catalog; the form of a `run_id`.
- **The coder's output**: file names and form under `…/coder/…/output/`, how many source files a kernel has (OD-23; the isolation means of OD-8).
- **The baseline** (OD-28). The contract of the SDPA family and of any kind other than `gemm`; any kernel language other than C; fp16 and q4 variants; any `layout` value other than `row_major`.
- **Rest of OD-6**, including sub-question ④ (decision 8), and **rest of OD-4**.
- Any change of the spec schema, the key schema, `hilclaw/spec.py` or `hilclaw/keys.py`; code, tests, C files, CI changes, committed example files and the `HIL-Claw-data` repository: later tasks.

## References

- [Requirements](../Requirements.md): FR-1, FR-5, FR-9, FR-10, FR-13, FR-15, NFR-4, NFR-6, C-6, C-7; register rows OD-1, OD-4, OD-6, OD-8, OD-13, OD-14, OD-16, OD-23, OD-26, OD-28.
- [OpenDecisionProposals OD-4](../OpenDecisionProposals.md#od-4) ("제안으로 남는 부분", "첫 구체 인스턴스"), [OD-6](../OpenDecisionProposals.md#od-6) ("하위 질문" ①-④), [OD-16](../OpenDecisionProposals.md#od-16) (threat B ⑶ ⑸, "하위 질문" ①), [OD-28](../OpenDecisionProposals.md#od-28).
- [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 2, 3, 5, 6, 7; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 1, 2, 6 (a), 7, 8); [ADR-0003](ADR-0003-od16-harness-calibration.md) (decisions 1, 4, 5; Boundaries); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (`…/coder/…/spec.json`, `…/coder/…/output/`, decision 5); [ADR-0007](ADR-0007-od13-measurement-policy.md) (decision 2, Boundaries).
- #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, B-1, B-7.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P0.5-1, P1-2, P1-3, P1-4, P1-5; `hilclaw/keys.py` (`op_signature_key`), `hilclaw/spec.py` (`validate`); CLAUDE.md (A-13, language policy); task T-0030.
