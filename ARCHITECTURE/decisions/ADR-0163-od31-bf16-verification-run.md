# ADR-0163: The verification run of one built bf16 kernel on `cpu_standin` for the kinds `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` — one verification program per kind, its command line, a generator over each contract's value set with operands drawn independently, a bf16 NaN in the output before the call, the widening and the float64 reference per kind with the passed RMSNorm `eps`, the input check, the report, the comparison, the verdict and the calibration (P2-12 harness record, first part; part of OD-31 sub-question 3 and of OD-16)

## Status

- **Accepted on 2026-10-25.** It is the first part of the harness record that the bf16 contract records of PLAN P2-11 leave their verification mechanism to (PLAN P2-12).
- **Three kinds of content.**
  - **Owner answers, cited and marked owner**: HQ-0065 and HQ-0066 in `PROCESS/STATE.json`, as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) decisions 2 and 3 record them, and, for the fp32 model, the HQ-0004 answer as [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) decisions 3 to 6 quote it. They are **not subject to the objection window** below.
  - **Cited**: statements of accepted records ([ADR-0003](ADR-0003-od16-harness-calibration.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), ADR-0017, [ADR-0107](ADR-0107-od16-verification-and-timing-build-relation.md), [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0158](ADR-0158-od31-bf16-rmsnorm-contract.md), [ADR-0159](ADR-0159-od31-bf16-elementwise-add-contract.md), [ADR-0160](ADR-0160-od31-bf16-swiglu-contract.md), [ADR-0161](ADR-0161-od31-bf16-rope-contract.md), [ADR-0162](ADR-0162-od31-bf16-sdpa-kv-cache-contract.md)), each with the record and decision named.
  - **This record's own**, every other sentence: the programs, the command lines, the mapping of a word to a value, the independence of operands, the output fill, the RMSNorm reference `eps`, the input check, the report of these kinds, the calibration fixtures and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 261 comments without a "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: verification, 검증, harness, 하네스, seed, 시드, draw, NaN, reference, oracle, tolerance, rtol, atol, 입력 분포, bf16, widen, CRC. Owner sentences that touch the subject, each read for what it says and no further:
  - **K1** — the HQ-0004 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052377983): "The reference is the float64 product of the drawn fp32 inputs widened to float64, computed on the Python side of the harness; the process that runs the kernel holds neither the reference nor the comparison"; "any NaN or infinity in the output fails"; "the verification inputs of this case are drawn finite"; "How the inputs and the kernel's output reach the Python side (regeneration from the seed, a pipe, or otherwise) is the record's design". It is said of the fp32 `gemm` case; HQ-0066 (1) and (2) extend the oracle and the vocabulary to the Llama kinds (ADR-0154 decision 3). It says nothing of bf16, of a generator or of a value set.
  - **K2** — the HQ-0005 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6117798837): "the same harness, predicate and tolerance with inputs drawn anew for each check". Said of the checks of the first case; it says nothing of how inputs are drawn.
  - **K3** — the A-12 decision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596): the scoring apparatus ("input generation, f64 reference, tolerance compare, …") "lives in one sub-module of the package, is never part of the coder's scratch". This record's programs and Python side lie in that sub-module (decision 2). The A-6 decision (comment 5933950693): tolerance "is a user-adjustable Loop-instance parameter". The #5 body item B-7 ("기본 tolerance(예: rtol/atol) 관례가 있는지") is a question, not an answer.
  - **K4** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "dtype **fp32** (bf16 weights upcast); fp16 / q4 are later instance variants"; and the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16." They say which precision the goal uses, which HQ-0065 settles (ADR-0154 decision 2); neither says anything of a generator, a value set or a verification mechanism.
  - Read as context, not as owner sentences (as ADR-0154 Status reads them): the #7 body and comment 5566900982 ("FP64/FP32 CPU 레퍼런스", "per-(op,dtype) tolerance", corner cases with NaN, "후보가 관측 불가한 시드"); #8 comment 5141454502 and the #8 body ("런타임 시드·입력 값이 파일로 존재하지 않을 것"); #4 comments 5139248800 (pin the tolerance per instance, OD-11) and 5139876430 ("매 trial 무작위 입력 + 비관측 시드, OD-16"). The other hits (for example "NaN" inside other words, "draw" in "drawing lessons", "widen" of ADR-0127) are not on the subject. **Nothing was found** on how bf16 inputs are drawn, a generator, `CRC`, `입력 분포`, the output fill or the RMSNorm `eps`.
  - **Conflicts**: none. K1's and K4's fp32 sentences are the first case, which stays (decision 1).
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `1cfcf6f`).
  - **HQ-0033** (the ADR-0116 flags, `-ffp-contract=off` among them): no flag is chosen, and the programs do no floating-point arithmetic (decision 2), so they stay correct under the caller's flags as ADR-0017 decision 2 requires.
  - **HQ-0034** (OpenMP on `cpu_standin`): answered (a) on 2026-10-25, not yet reflected in ADR-0116. This record depends on neither OpenMP nor threads: the programs start no thread, and a kernel's threads are the kernel's (ADR-0156 decision 7, "As ADR-0008 decision 6").
  - **HQ-0070** (the RoPE scale factor): not touched. It is weighed among the reasons RoPE is outside this record and found to bear on the model's table only, not on a verification (decision 1).
  - **HQ-0069** (runtime acceptance (lxvii) of the model executor's loading): not touched; no runtime fact is used.
  - Not touched: HQ-0021 (round 0, P2-5), HQ-0048 (rounds ≥ 1, P2-6), HQ-0022, HQ-0024, HQ-0026, HQ-0028, HQ-0029 (code tasks), HQ-0023, HQ-0027 (review limits of other records) and the runtime-acceptance HQs HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0047, HQ-0049 to HQ-0052, HQ-0054 to HQ-0063 and HQ-0068.
- **Not changed**: no schema file, member, file, version or validator of the data plane. The report is an internal interface of the harness (as ADR-0017 decision 7). It is a record, not code: nothing was built, no `claude` process was started, and the facts computed below were computed in a throwaway interpreter that changed no repository file (D16).
- **Answers**: of **OD-31 sub-question 3**, for `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` in bf16 on `cpu_standin`: the generator over each value set, the independence of operands, the output fill, the widening, the float64 reference per kind and the RMSNorm reference `eps`; not the seed's source or the number of draws. Of **OD-16**: the verification run of these four kinds in bf16 at `cpu_standin` (a confirmed part, as ADR-0017 is for the first case), and part of **sub-question ②** — calibration is repeated per dtype for these kinds. Open of them: Boundaries.
- It builds on ADR-0003 (decisions 2 to 7), ADR-0008 (decision 7), ADR-0017 (decisions 1 to 10), ADR-0107 (decisions 1 and 3), ADR-0116 (decision 4), ADR-0154 (decisions 2 and 3), ADR-0156 (decisions 3, 4, 5, 7, 9 and 10), ADR-0158 (decisions 3, 5, 7, 8 and 9), ADR-0159 (decisions 4, 6, 8 and 10), ADR-0160 (decisions 4, 6, 8, 9 and 10), ADR-0161 (decisions 4 and 13) and ADR-0162 (decision 13); none of them is edited. **If ADR-0017 or one of the four contract records is reverted, this record is revisited with it.** The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What exists.** `hilclaw/harness/` verifies one case: the fp32 `gemm` of ADR-0017. Its program (`verification_program.c`) calls `hilclaw_gemm` over `float`, and its Python side (`verification_arrays.py`) draws binary32 values of magnitude in [0.5, 1) from 64-bit words and compares a `float32` output (observations at `1cfcf6f`).
- **What the contract records leave here.** ADR-0156 decision 9, ADR-0158 decision 9, ADR-0159 decision 10 and ADR-0160 decision 10 fix the value sets and leave to "the P2-12 harness record" the generator, the seed, the number of draws, whether the two operands are drawn independently (ADR-0159, ADR-0160), the content of the output before the call, the RMSNorm reference `eps` (ADR-0158) and the widening for the float64 reference. ADR-0161 decision 13 and ADR-0162 decision 13 leave the same for RoPE and SDPA, with RoPE's T = 1 row and SDPA's cache rows, guard rows and cache comparison.
- **The owner's frame** (ADR-0154 decisions 2 and 3): bf16 crosses the boundary as `uint16_t` bit patterns (**owner**, HQ-0065 (3)); the reference widens each input to float64 and computes in NumPy float64, no new dependency (**owner**, HQ-0066 (1)); element-wise `rtol` and `atol`, instance parameters, no default (**owner**, HQ-0066 (2)); each kind's input distribution by a driver record, finite inputs only (**owner**, HQ-0066 (3)). Widening a 16-bit pattern "is the upper half of the fp32 pattern of the same value" (ADR-0154 decision 3).

## Decision

A sentence marked **owner** renders an HQ answer through the record named. A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**. "As ADR-0017 decision n" applies only the part of that decision the sentence names, with the substitutions stated; nothing else of it is carried over — in particular not its fp32 value range, its `float` patterns or its sentence that two draws differ.

### 1. Scope and terms

- This record is about the **verification run of one built attempt** of a C kernel of ADR-0156 (`gemm`, bf16), ADR-0158 (`rmsnorm`), ADR-0159 (`elementwise_add`) or ADR-0160 (`swiglu`) at `cpu_standin`. The terms of ADR-0017 decision 1 are used with **draw** meaning one set of values of the kind's two array operands.
- **Not covered**: the timing run of a bf16 kernel (the counterpart of ADR-0009 and ADR-0145, a later record); **RoPE and SDPA**, left to a second harness record, because RoPE's `freqs_cis` operand is a table built outside the kernel (ADR-0161 decision 4), whose rows a draw takes rather than drawing from a value set, and which T = 1 row a draw uses is open (ADR-0161 decision 13) — HQ-0070 does not hold it back, since the verification table is built "with the constants of decision 4 (s = 8) whatever the answer on the scale factor" (ADR-0161 decision 13) — and because SDPA needs the content of cache rows P … l − 1, guard rows past l and a cache comparison (ADR-0162 decision 13).
- **It is not an FR-10 tool contract**, as ADR-0017 decision 1: nothing here says whether or how `correctness.check` or an instance reaches these runs.
- **ADR-0017 and the first case are unchanged**: its program, Python side, generator, value range and report stay as they are, for `gemm` fp32 only.

### 2. Program and process

- **One verification program per kind**: four C source files under `hilclaw/harness/`, each separate from the first case's program and from every timing driver, each calling one symbol — `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16` or `hilclaw_swiglu_bf16` (cited: ADR-0156 decision 5, ADR-0158 decision 5, ADR-0159 decision 6, ADR-0160 decision 6). Reasons:
  - The harness provides the program, and a kernel defines no `main` ("the caller provides the program", ADR-0008 decision 7, carried over by each contract record). A program that names a symbol needs it defined at link time, and a kernel source defines exactly one, so one source calling all four would not link with any kernel.
  - **The kind chosen at build time** (one source, a define per kind) would need a flag the harness adds, while the build passes the caller's flags unchanged and "The harness adds no flag" (`verification_build.py`, cited by ADR-0107 Context), and a define reaches the kernel's translation units too, "where a kernel could test it" (ADR-0107 decision 3).
  - **Cost**: four programs to keep. Code they share — the generator, the check value, the report writer — may be one header of the harness included by each; that is the code task's. **Every identifier a program defines besides `main` has internal linkage** (`static`, the shared header's included), so it cannot collide with an external name of the kernel, which may define any name outside the `hilclaw_` prefix; the prefix stays reserved for the contract and the caller (ADR-0008 decision 7).
- **One kernel per executable**, built with its program by one call of `clang_build.build` with the caller's flags, and **a process of its own** through `local_run.run`, for the reasons of ADR-0017 decision 2 (cited).
- **The program does no floating-point arithmetic.** It handles bf16 values only as `uint16_t` patterns and 64-bit integers; RMSNorm's `eps` is a binary32 constant formed from its bit pattern (decision 3). It needs the C library and POSIX only: no `<math.h>`, no `exp` and no `-lm` of its own. A SwiGLU kernel may call `expf` (ADR-0160 decision 9), and an RMSNorm kernel may use `<math.h>` (ADR-0158 decision 8); that the build links the math library is a build setting, with `-lm` among ADR-0116 decision 4's trailing flags for the first case (cited as ADR-0160 decision 9 cites it).
- **ADR-0107's rule is left with the first case.** Its decision 1 limits it to runs at `cpu_standin` for the first case and to the mock, and its rule relates a verification build to a timing build; no bf16 timing run exists. Whether it extends to these kinds is for the record of the bf16 timing run (OD-16 sub-question ⑥ stays as registered).
- **Reading next to OD-14**: as ADR-0017 decision 2, a process per run is a mechanism only; no isolation is adopted or rejected.

### 3. Command line

| Kind | Arguments, in this order |
|---|---|
| `gemm` | `<m> <k> <n> <draws> <seed>` |
| `rmsnorm` | `<m> <n> <draws> <seed>` |
| `elementwise_add` | `<m> <n> <draws> <seed>` |
| `swiglu` | `<m> <n> <draws> <seed>` |

- The dimensions in the order of the kind's prototype (cited: the four decisions of decision 2), then `draws` and the seed. Each dimension is at least 1 (the caller's guarantee of each contract), `draws` at least 1, the seed an unsigned 64-bit integer; their spelling and checks are those of the first case's program (ADR-0017 decision 9 for the rule "command-line arguments and … no standard input, no file and no environment variable"; the digit rules in the program's header at `1cfcf6f`), and the code task may reuse them.
- **RMSNorm `eps` is a constant of the mechanism, not an argument**: the binary32 value nearest to 1e-05, bit pattern `0x3727C5AC`, which is `rmsnorm_bf16_contract.EPS` (9.999999747378752e-06; recomputed). Reasons: ADR-0158 decision 9 fixes `eps` as part of the value set ("the binary32 value nearest to 1e-05 in every call, the only value the Llama calls pass"), so no caller has another value to give; a constant written as a bit pattern needs no text-to-float conversion in the program; and another value would be a change of that value set, a contract record's. A kernel must still be correct for every `eps` > 0 (ADR-0158 decision 7); that only one is used is Limit 3.

### 4. Drawn inputs

- **Value sets** (cited, recomputed against the contract modules at `1cfcf6f`):

| Kind | Operands | Set | Size |
|---|---|---|---|
| `gemm` | `a`, `b` | ±(0.5 + j/256), j = 0 … 127 (ADR-0156 decision 9; `INPUT_PATTERNS`) | 256 = 2^8 |
| `rmsnorm` | `x`, `w` | the same (ADR-0158 decision 9) | 2^8 |
| `elementwise_add` | `a`, `b` | the same (ADR-0159 decision 10) | 2^8 |
| `swiglu` | `gate` | magnitude in [0.5, 8), either sign, patterns `0x3F00`–`0x40FF` and `0xBF00`–`0xC0FF` (ADR-0160 decision 10; `GATE_PATTERNS`) | 1024 = 2^10 |
| `swiglu` | `up` | ±(0.5 + j/256) (ADR-0160 decision 10; `UP_PATTERNS`) | 2^8 |

- **Every element is drawn from its set itself**, never by rounding a wider value (ADR-0156 decision 9: rounding can reach 1.0, outside the set). Every value is finite (**owner**, HQ-0066 (3)).
- **How an element chooses its entry.** The generator gives each element one 64-bit word; its **top b bits**, r = word >> (64 − b) with b = 8 for a set of 256 and b = 10 for the gate set, are the entry's index, and the index gives the bit pattern:
  - b = 8: pattern = `0x3F00` | (r & `0x7F`) | ((r >> 7) << 15) — bits 0 to 6 of r are the fraction j, bit 7 the sign;
  - b = 10: pattern = (`0x3F00` + (r & `0x1FF`)) | ((r >> 9) << 15) — bits 0 to 8 run over the 512 positive patterns `0x3F00` … `0x40FF`, bit 9 is the sign.
  - The pattern of index r is **element r of the contract module's tuple** (`INPUT_PATTERNS`, `GATE_PATTERNS`, `UP_PATTERNS`), checked for all 256 and 1024 indices. The values at the ends are ±0.5 and ±0.99609375 (b = 8) and ±0.5 and ±7.96875 (b = 10).
  - **The choice is uniform**: each of the 2^b indices is the top field of exactly 2^(64−b) of the 2^64 words, so every entry is equally likely when the words are; a set size that is not a power of two would need a rejection or a modulo bias, which these sets do not.
- **The words.** As ADR-0017 decision 3: a deterministic generator from integer arithmetic, implemented **twice** — in each program and once on the Python side — giving the same patterns bit for bit, with the word of an element following from the seed, the draw and its index alone, so the Python side computes it with array operations. **The algorithm is the code task's and is identified by its source commit**, as ADR-0017 decision 3 leaves it; the first case's construction (the words of `verification_program.c` at `1cfcf6f`) has these properties and may be reused, applied to the element indices below. The elements are indexed in one sequence per draw: the first operand in its memory order, then the second (`a` then `b`; `x` (m·n) then `w` (n); `gate` then `up`).
- **The two operands of a kind are drawn independently**: each element of each operand takes its own word, and no element is derived from another. Reasons: it is what the contract records' computed facts assume — for the add, b = −a "(256 of the 65536 pairs)" and sums over "all 65536 ordered pairs" (ADR-0159 decision 10); for SwiGLU, shares "over all 262144 pairs" (ADR-0160 decision 10); with independent draws a draw's pairs are a uniform sample of exactly those pair sets. Cancellation to zero in the add needs b = −a (ADR-0159 decision 10); independent draws give it with probability 1/256 per element, 8 elements on average per row of n = 2048 and 4096 at 512 × 2048 (computed), which no construction is needed for. A drawing that forces b = −a, or other related operands, would construct corner cases, which stay with #5 B-7 and OD-16 threat B ⑵.
- **Seed and `draws`**: parameters of the run with no default, as ADR-0017 decision 3 (one draw per kernel call, its values following from the seed, the draw and the dimensions; the seed must be one the author of the attempt could not know, which binds the caller). Their source and the number an instance uses stay OD-16 sub-question ⑤.
- **Shapes**: those the caller passes, as ADR-0017 decision 3. Whether other shapes are ever passed stays OD-16 sub-question ①.

### 5. The output before the call

- **Before each kernel call the program sets every element of the output (`c`, `y`, `c`, `out`) to `0x7FC0`**, a bf16 quiet NaN (the upper half of the first case's fill `0x7FC00000`, `verification_program.c` at `1cfcf6f`; ADR-0017 decision 4 fills with NaN "written as a bit pattern"), written as an integer, so no build flag changes it. Each contract leaves the output's content on entry unspecified and forbids the kernel to read it before writing it (the "Output" row of ADR-0156 decision 7, ADR-0158 decision 7, ADR-0159 decision 8 and ADR-0160 decision 8), so no obligation is added.
- **Consequence**: an element the kernel does not write widens to a NaN and fails the comparison as non-finite (decision 7), on every draw, the second included — not the previous draw's output.

### 6. The reference

- **The Python side regenerates the inputs** from the seed for each draw and computes the reference from its own arrays, as ADR-0017 decision 4 (cited), so a kernel that overwrites its inputs changes nothing the reference rests on.
- **Widening** (ADR-0154 decision 3's reading): a pattern p becomes the binary32 pattern p · 2^16 (p shifted left by 16 bits), which is then widened to float64. Both steps are exact. The **inputs and the reported output** are widened alike; the output fill of decision 5 becomes a NaN.
- **The float64 formula per kind**, NumPy float64 on the widened arrays (**owner**, HQ-0066 (1)), with no bf16 emulation:

| Kind | Reference | Operation cited |
|---|---|---|
| `gemm` | C = A · B (`matmul`) | ADR-0156 decision 3 |
| `rmsnorm` | y(i, j) = x(i, j) · w(j) / sqrt(s(i)/n + eps), s(i) = Σ_j x(i, j)² | ADR-0158 decision 3 |
| `elementwise_add` | c = a + b, exact in float64 for these sets | ADR-0159 decisions 4 and 10 |
| `swiglu` | out = g / (1 + e^−g) · u, with NumPy's float64 `exp` | ADR-0160 decisions 4 and 10 |

- **SwiGLU's `exp`** is `numpy.exp` in float64, the evaluation ADR-0160 decision 10 measured: relative error at most 3.2 · 10^−16 against the exact value over all 262144 pairs (cited).
- **The RMSNorm reference `eps` is the binary32 value the program passes, widened to float64** (`rmsnorm_bf16_contract.EPS`), not the decimal 1e-05. Reasons: the `eps` of the operation "is the value passed" (ADR-0158 decision 5), so this reference is the contract's operation on the kernel's actual arguments; the difference from 1e-05, a relative 2.5e-8 that moves the reference by a relative 5e-13 at most (ADR-0158 decision 9), is negligible either way, so the choice rests on that reason alone.
- **Input check value**, as ADR-0017 decision 4: before each call the program reports a check value of the bytes of the two input arrays of that draw, in the order of decision 4 (first operand, then second), as they are in memory — 2 bytes per element; the Python side compares it with the value of its regenerated arrays, and a disagreement makes the run **broken**, never a fail. RMSNorm's `eps` is not covered: it is a constant on both sides, and their agreement is a test of the code slice. The check function is the code task's (as ADR-0017 decision 4), with a 32-bit value; the first case's CRC-32 (`zlib.crc32` in its code) suits.

### 7. The comparison

- **Owner** (HQ-0066 (2), through ADR-0154 decision 3; the predicate of HQ-0004 (2), through ADR-0017 decision 5): element-wise `rtol` and `atol`, instance parameters; an element passes iff |out − ref| ≤ atol + rtol·|ref|; any NaN or infinity in the output fails.
- As ADR-0017 decision 5 (cited): on the Python side, in float64, on the widened output; neither `rtol` nor `atol` is passed to the program; each must be finite and not negative, and anything else is refused before a process is started; the reference's own rounding is not accounted for.
- **For whoever sets a tolerance** (no value and no default):
  - **Every kind**: a correctly rounded bf16 output differs from the exact value by up to a relative 2^−8 (half a unit in the last place, 2^(e−8), against a value of at least 2^e; computed), so an `rtol` below that, with `atol` too small to cover it, can fail a conforming kernel.
  - **`gemm`**: the drawn signs are mixed, so an element can lie close to zero while the fp32 accumulation error does not shrink with it; ADR-0017 decision 5's observation that a tolerance with `atol` = 0 can fail a conforming kernel holds here too. A term left out or counted twice moves the exact element by at least 0.25 (ADR-0156 decision 9).
  - **`rmsnorm`**: every exact output has a magnitude between 0.25 and 2, so no element cancels (ADR-0158 decision 9).
  - **`elementwise_add`**: a correct kernel differs from the reference by 0 on three quarters of the pairs and by exactly 2^−8 on the ties, a relative 1/257 at most, and the reference is exactly 0 where b = −a (ADR-0159 decision 10).
  - **`swiglu`**: a correctly rounded output is within a relative 0.00389 of the exact value, and any output of a kernel meeting the bound within 0.00437 (ADR-0160 decision 10).

### 8. The report and the verdict

- **Channel**, as ADR-0017 decision 7: the standard output the process was started with, kept under a descriptor of its own while descriptor 1 points at standard error.
- **Content**, in this order and nothing else: for each draw, the check value of decision 6 as the 4 bytes of a `uint32_t`, written before the call; then, after the one call has returned, the m·n elements of the output as the bytes of their `uint16_t` patterns in memory order (2·m·n bytes; the output has m·n elements for all four kinds); after the last draw, an end mark. **A complete report has draws · (4 + 2·m·n) + E bytes**, E the length of the end mark (4 in the first case's code), so its length follows from `m`, `n` and `draws` alone. Spelling and framing beyond that are the code task's, as ADR-0017 decision 7.
- **Completed, broken, pass and fail** as ADR-0017 decision 7 (cited), with the length above: a run is completed when it did not time out, exited with status 0, its report has exactly that form and every check value agrees; every other run is broken and is neither pass nor fail; a completed run passes iff every element of every draw meets the predicate. **The Python side returns** what ADR-0017 decision 7 lists — the verdict and per draw the number of failing and of non-finite elements, or the broken condition with what the runner captured apart from the report — and no element of an input or of the reference.

### 9. Calibration

- **ADR-0003 holds per kind**, for any tolerance under which the conforming kernel passes and the wrong outputs lie outside (ADR-0003 decision 7): conforming → pass; failing → fail; violating → fail (ADR-0003 decisions 2 and 4). The functional test is a verification run with a seed and dimensions written in the test, as ADR-0017 decision 8 reads it.
- **Three hand-written C kernels per kind, twelve in all**, as test data of the harness's tests (ADR-0003 decision 5), added in the change that makes the harness verify the kind (ADR-0003 decision 6 (a)). **The bf16 `gemm` gets its own three**, beside the fp32 ones: its program, symbol, element type and value set differ, so the fp32 calibration shows nothing about it.
- **Conforming**: the operation as its contract states it. **Violating**: right on the inputs of the functional test and wrong elsewhere (V1, ADR-0003 decision 3). **Failing** — chosen from what each contract record says its set detects:

| Kind | Failing kernel | Why it is outside |
|---|---|---|
| `gemm` | one term of each sum left out | moves the exact element by at least 0.25 (ADR-0156 decision 9); the test picks a shape whose outputs keep the bf16 rounding below that |
| `rmsnorm` | the weight left out (y = x / rms) | a relative \|1/w − 1\|: at least 2 for every negative weight, and at least 2^−6 for 253 of the 256 weight values (computed); "a wrong or missing weight" (ADR-0158 decision 9) |
| `elementwise_add` | a − b in place of a + b | moves an element by at least 1 − 2^−8 (ADR-0159 decision 10) |
| `swiglu` | σ(−g) in place of σ(g) | 100 % of the pairs, by at least a relative 0.39 (ADR-0160 decision 10) |

- **No test may require these to fail**, because the sets cannot detect them under every tolerance a conforming kernel passes: for `gemm`, an output rounding other than round-to-nearest-even that stays within the tolerance (ADR-0156 decision 4), a wider accumulator (ADR-0156 Alternatives) — fused and unfused multiply-adds are both conforming and give equal results on the set (ADR-0156 decision 3), so no test separates them either; for `rmsnorm`, a single square left out or counted twice, an ignored `eps` (ADR-0158 decision 9), Meta's intermediate rounding (at most about one bf16 unit in the last place, ADR-0158 decision 3) and the reciprocal square root bound, which "the verification … does not test" (same decision); for `elementwise_add`, the output rounding (truncation and ties away from zero miss by the same 2^−8), and an fp16 intermediate (ADR-0159 decision 10), while swapped operands are not an error (same decision); for `swiglu`, Meta's intermediate rounding and truncation, detected only under a tolerance between two computed values, and the 2^−11 bound itself (ADR-0160 decision 10).
- The tests pass their own `rtol`, `atol`, seed and `draws` (ADR-0017 decisions 6 and 8).

### 10. Parameters

| Value | Given by | Source |
|---|---|---|
| Dimensions (`m`, `k`, `n` or `m`, `n`) | the caller | each ≥ 1 (each contract's guarantee); other shapes: OD-16 sub-question ① |
| Seed | the caller, no default | as ADR-0017 decision 9; its source and recording: sub-question ⑤ |
| `draws` | the caller, no default, ≥ 1 | as ADR-0017 decision 9; the number an instance uses: sub-question ⑤ |
| `rtol`, `atol` | the caller, from the instance, no default | **owner**, HQ-0066 (2); not passed to the program (decision 7) |
| Time limit of the process | the caller, no default | as ADR-0017 decision 9; values: OD-14 |
| Flags, trailing flags, compiler, build time limit, path of the executable; environment and working directory | the caller | as ADR-0017 decision 9; build settings: Boundaries |
| One call per draw; elements from the value sets by the mapping of decision 4; operands independent; output filled with `0x7FC0`; RMSNorm `eps` = `0x3727C5AC` | constants of the mechanism | this record's own; the sets are the contract records' |

### 11. Limits

1. **As ADR-0017 decision 10** (cited): the kernel shares its process with the program; a pass says the output is right, not how it was produced; nothing is sandboxed (OD-14, OD-8, threat A of OD-16).
2. **What the sets cannot detect** is decision 9's list. A kernel right only on the drawn ranges passes: no zero, subnormal, large or non-finite input is drawn (#5 B-7, OD-16), and for SwiGLU no gate beyond ±8 although the contract's domain reaches about ±87.34 (ADR-0160 decision 4).
3. **One `eps`**: a kernel that is right only at the passed `eps` passes, and `eps` itself moves the result by less than the bf16 rounding (ADR-0158 decision 9).
4. **Cost**, computed from the shape sets of the contract modules: the report per draw at the largest shape is 4 + 2·m·n bytes — `gemm` 131,334,148 at lm_head, M = 512 (65,667,072 elements; lm_head is excluded from the first runs, ADR-0156 decision 10) and 8,388,612 at gate/up, M = 512; `rmsnorm` and `elementwise_add` 2,097,156 at 512 × 2048; `swiglu` 8,388,612 at 512 × 8192. The runner holds the whole report at once. The largest input of one draw is 263,716,864 elements at lm_head, M = 512, and 20,971,520 at down, M = 512, among the other projections; the first case's array code peaks at about 16 bytes per input element (its module docstring), about 4.2 GB at the former. **The Python side is bounded by nothing here** (OD-14).
5. **One machine**: the Python side reads `uint16_t` bytes produced on its own host (as ADR-0017 decision 10).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | One program for all four kinds, the kind chosen by an argument | It names four symbols and links with no kernel, which defines one. |
| 2 | One source, the kind chosen by a define at build time | A flag the harness would add, against the caller's unchanged flags, and readable by the kernel (ADR-0107 decision 3). |
| 2 | Extend the first case's program to bf16 | Changes ADR-0017's program and the first case. |
| 3 | `eps` as an argument | No caller has another value (ADR-0158 decision 9); it needs a text-to-float conversion in the program; another value is a change of the value set. |
| 4 | Draw a binary32 value and round it to bf16 | Can reach 1.0, outside the set (ADR-0156 decision 9). |
| 4 | Index by `word mod size` or by the low bits | Equal in distribution and cost for a power of two; the top bits are the field the first case's construction already takes its values from (`word >> 41`). |
| 4 | Related operands (b = −a on a share of elements, or one word for both operands) | Constructs corner cases (#5 B-7); independent draws already give cancellation at 1/256 and match the pair sets the contract records computed over. |
| 5 | Output left as allocated, or filled with zero | Stale memory or a value that can equal the reference (add at b = −a, `gemm` near zero) would hide an unwritten element. |
| 6 | Reference `eps` = 1e-05 | Not the value of the call (ADR-0158 decision 5); the difference is negligible, so nothing argues for it. |
| 6 | The program sends its inputs with the output | As ADR-0017 Alternatives: the reference would rest on bytes from the kernel's process. |
| 6 | No input check | As ADR-0017 Alternatives: two generators that differ would turn conforming kernels into fails silently. |
| 9 | Reuse the fp32 `gemm` calibration for bf16 `gemm` | Another program, symbol, element type and value set; it shows nothing about them. |
| 9 | A failing kernel the set cannot detect (for example truncation of the add) | No tolerance passes the conforming kernel and fails it (ADR-0159 decision 10). |

## Consequences

- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The report is an internal interface of the harness, not a data-plane schema. NumPy and the standard library suffice.
- **Code slices this record makes possible** (for the planner; no code here), one kind or more per slice: the kind's verification program in C under `hilclaw/harness/`; its build, as `verification_build.py` builds the first case's; the Python side — the generator over a value set with its index mapping, the widening of `uint16_t` patterns, the per-kind reference and the comparison on the widened output, reading and judging the report; and the three calibration kernels of the kind with their tests. A test that needs clang shows that the two generators agree. **Registering a bf16 kind with `correctness.check`, `spec.write` or the instance start is not one of them** (Boundaries).
- **Later work**: the second harness record (RoPE and SDPA; RoPE's table constant waits on HQ-0070 only where the model's values matter) and the record of the bf16 timing run.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` for "P2-12 harness record", "Left to the P2-12", "the harness mechanism", "for no other kind, dtype" and "verification run"; not claimed complete):
  - now answered for verification: the "the rest is the P2-12 harness record's" and "Left to the P2-12 harness record" bullets of ADR-0156 decision 9, ADR-0158 decision 9, ADR-0159 decision 10 and ADR-0160 decision 10; ADR-0156 decision 8 ("how a bf16 verification run is built is the P2-12 harness record's") and its Consequences ("the P2-12 harness work of a bf16 `gemm` verification run"); the Boundaries of ADR-0156, ADR-0158, ADR-0159 and ADR-0160 that keep "The harness mechanism" of a bf16 "verification and timing run" (the timing part stays open);
  - still true: ADR-0161 decision 13, ADR-0162 decision 13 and their Boundaries (the second harness record); ADR-0017 decision 1 ("it holds for no other kind, dtype or kernel language") and ADR-0041 decision 1's citation of it, both about the first case; ADR-0008 decision 7 and Boundaries and ADR-0153 Consequences, which quotes ADR-0008 decision 7 on "the harness mechanism"; the uses of "verification run" in ADR-0002, ADR-0003, ADR-0004, ADR-0009, ADR-0021, ADR-0035, ADR-0037, ADR-0046, ADR-0052, ADR-0061, ADR-0064, ADR-0117, ADR-0145 and ADR-0157, each about the first case, the timing run or verification in general (read at the line found).
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: the two operands drawn independently (decision 4); the output filled with a bf16 NaN (decision 5); the RMSNorm reference `eps` as the passed binary32 value and `eps` as a constant of the mechanism (decisions 3 and 6); one program per kind (decision 2); a calibration of its own for bf16 `gemm` (decision 9).
- **UsageCases and StandardScenarios** (S0, S1 and S7 re-checked, and the rows citing OD-31 sub-question 3 or OD-16: S0 steps 5 and 6, S1 step 2, S7 steps 2 and 3, S8 step 3): no use case step changes. The steps keep their open parts — the shapes and draws of a verification (OD-16 sub-questions ① and ⑤), the build relation outside the first case (⑥) and the vocabulary outside the first case and the Llama kinds on `cpu_standin` (#5 B-7, OD-31 ③). Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **Tolerance values**: instance parameters set by the user (FR-9; **owner**, HQ-0066 (2), no default).
- **Seeds and draws**: where the seed comes from and who draws it, how many draws an instance or a re-verification uses, and whether a seed or what the runner captured is recorded (OD-16 sub-question ⑤).
- **Other shapes** (OD-16 sub-question ①) and **another `eps`** (a change of ADR-0158 decision 9's value set).
- **Corner-case, non-finite and subnormal inputs** and outputs (#5 B-7, OD-16 threat B ⑵).
- **Build settings and OpenMP**: flags, trailing flags, compiler, language standard, the OpenMP runtime and thread count (HQ-0033; HQ-0034 and its reflection in ADR-0116); whether a kernel may link another library.
- **Isolation of the run** (OD-14; ADR-0144 for the first case).
- **RoPE and SDPA verification** (a second harness record; HQ-0070 for the model's RoPE table) and **the bf16 timing run**, with whether ADR-0107's rule extends to these kinds (OD-16 sub-question ⑥).
- **How a check or an instance reaches these runs**: `correctness.check` for bf16 kinds, the instance start and the spec (OD-18, OD-6, [ADR-0021](ADR-0021-od18-correctness-check-split.md), [ADR-0041](ADR-0041-od18-correctness-check-dimensions.md), [ADR-0048](ADR-0048-od18-correctness-check-seed-draw.md)).
- **fp16** (owner, HQ-0065 (1): after PLAN P2-14); **backends other than `cpu_standin`** (#5 B-2, B-7).
- **Any change to ADR-0017, to the first case or to a contract record**, its value set included.
- Code, C files, tests, CI and the `HIL-Claw-data` repository: later tasks.

## References

- Owner: HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (through ADR-0154); HQ-0004 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052377983 (through ADR-0017); HQ-0005 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6117798837; A-6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693; A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596; D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506; #5 body item B-7.
- [Requirements](../Requirements.md): FR-9, FR-10, C-6, C-7; register rows OD-14, OD-16, OD-18, OD-31. [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-16 (threat B ⑵, sub-questions ①, ②, ⑤, ⑥) and § OD-31 (sub-question ③); [StandardScenarios](../StandardScenarios.md) S0, S1, S7.
- Records: ADR-0001 (record format), ADR-0003 (decisions 2 to 7), ADR-0008 (decision 7), ADR-0017 (decisions 1 to 10), ADR-0021, ADR-0041, ADR-0048, ADR-0107 (decisions 1 and 3), ADR-0116 (decision 4), [ADR-0144](ADR-0144-od14-first-case-build-run-container.md), ADR-0154 (decisions 2 and 3), ADR-0156 (decisions 3, 4, 5, 7, 9 and 10), ADR-0158 (decisions 3, 5, 7, 8 and 9), ADR-0159 (decisions 4, 6, 8 and 10), ADR-0160 (decisions 4, 6, 8, 9 and 10), ADR-0161 (decisions 4 and 13), ADR-0162 (decision 13).
- Code read at `1cfcf6f`: `hilclaw/harness/verification_program.c` (header), `hilclaw/harness/verification.py`, `hilclaw/harness/verification_arrays.py`, `hilclaw/harness/verification_build.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/elementwise_add_bf16_contract.py`, `hilclaw/swiglu_bf16_contract.py`; `tests/harness/calibration/` (the first case's three kernels).
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11, P2-12, P2-14.
