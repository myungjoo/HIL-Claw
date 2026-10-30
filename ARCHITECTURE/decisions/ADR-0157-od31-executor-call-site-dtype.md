# ADR-0157: The dtype of the model executor's call sites — one dtype per generation, given as a model parameter, that selects for each call site the contract a kernel is fitted against, the entry point and the element type of the call; no mixed dtypes, an unknown dtype is invalid input (part of OD-31 sub-question 4)

## Status

- **Accepted on 2026-10-24.** It answers the question ADR-0153 decision 3 leaves implicit — where the dtype of a call site comes from — for the call sites of the Llama 3.2 1B goal, with what the dtype selects given for the GEMM call sites (PLAN P2-13, P2-14).
- **Two kinds of content.**
  - **Cited**, marked **owner** where it is an owner answer: the `decision` of HQ-0065 in `PROCESS/STATE.json` as [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) records it, #5 B-4 and the C-6 revision. The owner's answers are **not subject to the objection window** below. Statements of accepted records ([ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md), ADR-0154, [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md)) are cited with the record named.
  - **This record's own**, every other sentence: the source of the dtype, the refusal of mixed dtypes, what the dtype selects, the outcome of an unknown dtype, what of ADR-0153 code slice 1 changes, and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `821d4bf`). **HQ-0069** (runtime acceptance (lxvii): the model program is built with its kernels' shared libraries and loads them with `dlopen`): a bf16 kernel is built and loaded by the same means, and only the symbol `dlsym` looks for differs, so no new runtime fact is used or added. **HQ-0033** (the ADR-0116 flags) and **HQ-0034** (OpenMP on `cpu_standin`): no build setting is chosen or changed. **HQ-0021**, **HQ-0048** (parts of P2-5) and **HQ-0031** (injected hypotheses): not touched. **HQ-0022**, **HQ-0024**, **HQ-0026**, **HQ-0028**, **HQ-0029** (code tasks), **HQ-0023**, **HQ-0027** (review limits of other records) and the other runtime-acceptance HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0047, HQ-0049 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): not touched.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 254 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: dtype, bf16, fp32, 실행기, executor, mixed, 혼합, cast, 캐스트, precision, 정밀도, call site, 호출 지점. Owner sentences found that touch the subject, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "dtype **fp32** (bf16 weights upcast); fp16 / q4 are later instance variants". It is the first case, which stays (ADR-0154 decision 2).
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16." Answered by HQ-0065 (K3).
  - **K3** — HQ-0065, through ADR-0154 decision 2 (**owner**): "(1) (a) bf16만 - fp16은 Llama 3.2 1B end-to-end(P2-14) 뒤로 미룬다. (2) (a) 입출력은 bf16, 누적(GEMM 내적·RMSNorm 제곱합·softmax 합)은 fp32. (3) (a) 커널 경계는 16비트 비트 패턴(`uint16_t`)으로 하고 변환은 커널이 한다."
  - **Nothing found** on where a call site's dtype comes from, on mixed dtypes in one model run or on casts between kernels. The "executor" hits of #5 (comments 5969015070, 5986348506) and #8 (comment 5968679014) name the development driver's executor; the "혼합" of #4 comment 5138366881 is a hash of tool version and data commit; the A-6 decision (#5 comment 5933950693, "per-dtype rtol/atol") and the HQ-0004 answer (comment 6052377983) are about tolerance; the #7 body and comment 5566900982 and the #8 comment 5141454502 are research text, not owner sentences.
  - **Conflicts**: none. No choice here contradicts K1 to K3.
- **Not changed**: no schema file, member, file, `kind` or `dtype` value, version or validator of the data plane. It is a record, not code: `hilclaw/` and `tests/` are not touched, no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Owner-only parts not decided** (DRIVER §9): casts and the intermediate precisions (OD-31 sub-question 2), fp16 (HQ-0065 (1)), the weights (sub-question 5), tolerance and reference (sub-question 3), the model-level comparison (sub-question 6).
- **Answers part of OD-31 sub-question 4**: the dtype of a call site and what it selects. The rest of sub-question 4 stays as ADR-0153 left it (Boundaries).
- It builds on ADR-0153 (decisions 3, 4 and 5), ADR-0008 (decisions 1, 4, 5 and 6), ADR-0156 (decisions 1, 2, 5, 6 and 7), ADR-0152 (decisions 2 and 5) and ADR-0154 (decision 2); none of them is edited. The format follows the "Record format" section of ADR-0001.

## Context

- **Fit** (cited, ADR-0153 decision 3): "A kernel fits a call site when its `task.contract` is the contract of the call site's kind, dtype, layout and language, compared on the prototype text and the names, roles and dtypes of the operand entries". "The executor never chooses a kernel itself." The kind of each call site is fixed by ADR-0152 decision 2; layout `row_major` and language `c` are the only ones a contract defines so far. **The dtype has no named source**: the host-side inputs are (a) the model parameters, "the dimensions of ADR-0152 decision 5 as named values", (b) the weights, "each already in the dtype and layout of the operand that receives it", (c) the binding and (d) the run settings.
- **Outcomes** (cited, ADR-0153 decision 5): "the host side checks the binding against all of them before anything is built"; **no kernel**, **kernel unfit** and **invalid input** ("a run setting outside its range (a token id outside the vocabulary)"), none of which "builds or starts anything"; then **build failed** and **run failed**.
- **Casts** (cited, ADR-0153 decision 4): "Casts between kernels, or in the embedding row copy, are made only if the answer of sub-question 2 requires them; none is decided."
- **The two GEMM contracts**: fp32 — prototype `hilclaw_gemm` over `float` (ADR-0008 decision 4), a kernel must "Compute the product for the values it is called with" (ADR-0008 decision 6); bf16 on `cpu_standin` — prototype `hilclaw_gemm_bf16` over `uint16_t` bit patterns (ADR-0156 decision 5), and "A binding 'for every shape' of ADR-0153 decision 3 is therefore accepted for this contract" (ADR-0156 decision 7). "A wrong binding fails at loading, not in memory" is ADR-0156 decision 5's reason for the separate symbol.
- **The precision** (owner, K3): the Llama goal is bf16, with bf16 inputs and outputs for every kind; the first case is fp32 `gemm` and stays (ADR-0154 decision 2).
- **The landed ADR-0153 code slice 1** (`hilclaw/model_binding.py`, `model_build.py`, `model_run.py`, `model_execute.py`, `model_gemm.py`, `model_program.c`) knows fp32 `gemm` only: `model_binding` compares every entry with the fp32 contract, `model_program.c` finds `hilclaw_gemm` and passes `float` arrays.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. The source of a call site's dtype: one dtype per generation, a model parameter

- **The model parameters of ADR-0153 decision 3 (a) gain one value, the dtype of the model**, named by the same `dtype` vocabulary as the contracts (the `dtype` field: ADR-0001 decision 2; `bf16`: ADR-0156 decision 2). It has no default and is never assumed, like the dimensions. **Every call site of a generation has that dtype**: the dtype of a call site is the `dtype` of the contract it selects (decision 3). The element type of each operand of a contract is that contract's own; for the GEMM contracts every operand has the contract's dtype (ADR-0008 decision 5, ADR-0156 decision 6).
- **Why a model parameter, not a run setting**: the weights are "each already in the dtype and layout of the operand that receives it" (cited, ADR-0153 decision 3 (b)), so the GEMM weights already carry the dtype of their call sites; the dtype is a property of the model as it is handed over and is the same for every generation over the same weights. As a run setting it could differ between two generations over one set of weights, which those weights would contradict.
- **Why the fit check stays meaningful**: the dtype is known before anything is built and independently of the binding. With the call site's kind it names the contract each bound kernel is compared with (decision 3); a kernel written to another dtype's contract does not match it and is **kernel unfit** (ADR-0153 decision 5). The dtype selects a contract, not a kernel, so the executor still never chooses a kernel (ADR-0153 decision 3).
- **Why not read from the bound kernel's `task.contract`** (option (c)): the fit check would then compare a contract with the contract derived from itself and could only fail for a contract the executor does not know. A kernel of the wrong dtype would pass it: the program would call the entry point that the same contract names, so neither the fit check nor what ADR-0156 decision 5 calls "a second, independent stop" sees a dtype other than the kernel's own; in ADR-0153 slice 1, which has no weights, nothing would catch it, and with weights the dtype a weight is checked against would itself come from the kernel under check.
- **Why not a dtype per call site** (option (b)): it is needed only where call sites of different dtypes meet, which decision 2 refuses.
- **The weights**: each weight array is in the element type of the operand that receives it (cited, ADR-0153 decision 3 (b)); for a GEMM weight (QKV, O, gate, up, down, lm_head) that is the element type of the model's dtype. For `bf16` the host side holds a GEMM weight as the 16-bit patterns of its values in unsigned 16-bit elements, the representation of the kernel boundary (owner, K3 (3)), and does no arithmetic on them. A weight array whose element type differs from that of its receiving operand is refused before anything is built as **invalid input** (ADR-0153 decision 5): like the dtype of decision 4, it is a well-formed input the executor cannot run, so no new outcome is needed. The operands of the other kinds — the RMSNorm weights, a RoPE frequency table — take the element types their contracts give (Boundaries). The element type of the embedding table, and any cast in the embedding row copy, are not decided here (sub-question 2, owner; ADR-0153 decision 4; Boundaries). Weights reach the executor only with the full pass (this record's reading of ADR-0153 Consequences, code slice 2); ADR-0153 slice 1 has none to check.

### 2. No mixed dtypes in one generation

- **All call sites of a generation have one dtype** (decision 1), so call sites of different dtypes never meet and this record introduces no cast between kernels. **A binding entry whose kernel is written to the contract of another dtype is kernel unfit** (ADR-0153 decision 5); no new outcome is needed.
- **Reasons**: a mixed generation needs a cast where an output of one dtype is the input of another, and casts are left to sub-question 2 (cited, ADR-0153 decision 4; sub-question 2 is the owner's). The owner's answer gives every kind bf16 inputs and outputs (K3 (2)), so the Llama goal needs no mixing.
- **Not decided**: whether a later answer of sub-question 2 lets a call site run at another dtype (for example lm_head) or keeps another precision between kernels; such an answer replaces this decision by one with a dtype per call site and its casts (Boundaries).

### 3. What the dtype selects for `gemm`

For each GEMM call site (QKV, O, gate, up, down, lm_head — ADR-0152 decision 2), the model's dtype selects:

| | `fp32` | `bf16` |
|---|---|---|
| Contract a fit is checked against | ADR-0008: (`gemm`, `fp32`, `row_major`, `c`) | ADR-0156: (`gemm`, `bf16`, `row_major`, `c`) on `cpu_standin` |
| Compared on | the prototype text and each operand entry's `name`, `role`, `dtype`, as ADR-0153 decision 3 | the same |
| A binding "for every shape" | accepted (ADR-0008 decision 6) | accepted (ADR-0156 decision 7) |
| A listed shape other than the spec's own | accepted, under the same condition (ADR-0153 decision 3) | accepted, under the same condition |
| Entry point found with `dlsym` | `hilclaw_gemm` (ADR-0008 decision 4) | `hilclaw_gemm_bf16` (ADR-0156 decision 5) |
| Element type of `a`, `b` and `c` passed by the model program | `float` | `uint16_t`, each a bf16 bit pattern in the layout of ADR-0156 decision 2 |

- **The model program runs one generation of one dtype**; it calls the entry point of that dtype for every GEMM call and holds its buffers in that element type. How the program learns the dtype from the host side — an indicator in its input, or one program per dtype — is the code slice's, with the form of its input (ADR-0153 Boundaries).
- **A library without the entry point of the dtype** cannot be called: the program ends without a complete report, the outcome **run failed** (ADR-0153 decision 5). A kernel whose `task.contract` is of another dtype has already been refused by the fit check (decision 1); a library that reaches the program without the entry point — a source that does not match its `task.contract` — meets the second stop of ADR-0156 decision 5.
- **The report** holds the requested logits rows in the element type of lm_head's output operand — `uint16_t` bf16 patterns in a bf16 generation. What a model-level comparison does with them, a widening included, is sub-question 6.

### 4. A dtype the executor knows no contract for

- **The range of the model's dtype** is the set of dtypes at which the executor knows the contract of the kind of **every** call site of the generation. With the GEMM call sites only (ADR-0153 code slice 1) and the contract records ADR-0008 and ADR-0156, it is {`fp32`, `bf16`}; once the other five kinds are call sites (ADR-0153 code slice 2), a dtype is in range only where each of them has a contract record at that dtype.
- **A dtype outside that range is invalid input** (ADR-0153 decision 5), found with the other input checks before anything is built — for example `fp16`, or `bf16` for a kind that has no bf16 contract yet. The outcome names the dtype and, if the dtype is known for some kinds, the kind that lacks a contract.
- **Reasons**: ADR-0153 decision 5 names invalid input for "a run setting outside its range"; this record reads the model's dtype as an input of the same standing — a well-formed value the executor cannot run — so the five outcomes stay as they are. Kernel unfit is about a bound kernel and would be reported for every entry even of a binding that is right for the dtype; no kernel says a shape has no binding. A value that is not a dtype name at all is a malformed argument, handled as the code slice handles a malformed dimension.
- **No fp16 contract is defined here.** fp16 comes after PLAN P2-14 (owner, K3 (1)); until a record defines its contracts, `fp16` is outside the range.

### 5. The fp32 path stays

- **The landed ADR-0153 code slice 1 stays valid as the fp32 path**: its fit check against ADR-0008, its "every shape" acceptance, `hilclaw_gemm` over `float` and its input encoding of `float` elements. **What changes in it**: the binding check takes the model's dtype as one more input (no default — callers of the fp32 path pass `fp32`), compares each entry with the contract the dtype selects (decision 3) and gives the invalid-input outcome of decision 4; the module docstrings that say "no dtype other than fp32" are rewritten by the code slices that add bf16.
- **After ADR-0153 code slice 2**, an fp32 generation is in the range of decision 4 only if the other five kinds gain fp32 contract records; none is planned. What stays is the fp32 column of decision 3 for the GEMM call sites, which ADR-0153 slice 1 and its tests use; a full fp32 generation is invalid input until the other kinds have fp32 contracts.
- **The first case is unchanged**: fp32 `gemm`, ADR-0008, PLAN P1-5 (ADR-0154 decision 2), with its verification run of ADR-0017. Nothing here makes an fp32 generation of Llama 3.2 1B a goal; the goal is bf16 (owner, K3 (1)).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | (a') One dtype per generation as a **run setting** | The weights are already in the dtype (ADR-0153 decision 3 (b)); a run setting could disagree with them from one generation to the next over the same weights. |
| 1 | (b) A dtype **per call site**, with the binding or the model parameters | Only useful when call sites of different dtypes meet, which needs casts that sub-question 2 (owner) has not answered; the owner's answer gives every kind bf16 inputs and outputs. |
| 1 | (c) The dtype **read from the bound kernel's `task.contract`** | Makes the dtype part of the fit check vacuous: a contract is compared with itself, the entry point called comes from the same contract, and a kernel of the wrong dtype is not caught before anything is built. |
| 1 | (d) The dtype **inferred from the weights' arrays** | A 16-bit element does not tell bf16 from another 16-bit format; the binding check of ADR-0153 slice 1 has no weights; and the check of the weights against a named dtype (decision 1) is lost. |
| 2 | Mixed dtypes allowed, a generation needing a cast refused | Needs a per-call-site dtype (above) and a rule for when a cast is needed, while casts themselves are the owner's (sub-question 2). |
| 4 | **Kernel unfit** for an unknown dtype | Reported per bound entry, also for a binding that is right; it hides that the dtype itself cannot run. |
| 4 | A **new outcome** for an unknown dtype | The input checks of ADR-0153 decision 5 already cover an input outside its range; a sixth outcome adds a name for no new handling. |
| 5 | A default dtype `fp32` for the existing callers | The model parameters are "never assumed" (ADR-0153 decision 3 (a)); a default would let a bf16 generation run its fit check against the fp32 contract by omission. |

## Consequences

- **A-13 reading**: no schema file, member, file, `kind` or `dtype` value, version or validator of the data plane changes; the model's dtype is an in-memory input of the host side. `hilclaw/` is not touched.
- **Code slices this record makes possible** (for the planner; each its own task, within the size cap):
  - **(1)** the model's dtype in `hilclaw/model_binding.py`'s check: the contract selected by the dtype (`hilclaw.gemm_contract` or `hilclaw.gemm_bf16_contract`), kernel unfit for an entry of another dtype, invalid input for a dtype outside the range of decision 4, and the existing fp32 callers passing `fp32`; with tests.
  - **(2)** the model program and its host-side build and run steps for bf16: `hilclaw_gemm_bf16` over `uint16_t` buffers, the input encoding and report of 16-bit patterns, with hand-written bf16 kernel fixtures; split to the size cap if needed (for example the program and its run first, the build and execution path second).
  - The element-type check of the weights (decision 1) goes with ADR-0153 code slice 2, where weights first reach the executor.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` for "call site's kind, dtype", "run setting outside", "future contract records", "dtype of the contracts" and "실행기"; not claimed complete):
  - ADR-0153 decision 3 (a) lists the model parameters as "the dimensions of ADR-0152 decision 5 as named values"; decision 1 adds the dtype.
  - ADR-0153 decision 3 "for other kinds, through the prototypes of their future contract records" (already listed by ADR-0156); decision 3 now gives the GEMM entry point per dtype.
  - ADR-0153 decision 5 "a run setting outside its range" for invalid input; decisions 1 and 4 read the model's dtype and the weights' element types as inputs of the same standing.
  - ADR-0153 Status "buffers take the dtype of the contracts" and Boundaries "Dtype, accumulation precision and the casts between kernels": the dtype's source and the absence of mixing are decided here; accumulation and casts stay open.
  - ADR-0156 Consequences, code slice ("its use by `hilclaw/model_binding.py` … and by the model program"): its order and split are this record's Consequences.
- **Runtime acceptance items**: none. Loading a bf16 kernel's library is the same act as ADR-0153's (lxvii) (HQ-0069); nothing here needs a live `claude`, a board or a model file.
- **Readings for the owner to check**, listed in the #5 notice: one dtype per generation, given as a model parameter, and no mixing of dtypes within a generation, read from "입출력은 bf16" for every kind (decisions 1 and 2); bf16 GEMM weights held on the host side as their 16-bit patterns with no arithmetic on them (decision 1); a dtype the executor has no contract for — fp16 among them — and a weight array of another element type than its operand's refused as invalid input (decisions 1 and 4); the logits of a bf16 generation reported as bf16 patterns, their comparison left to sub-question 6 (decision 3).
- **Owner question**: none. Sub-questions 2, 5 and 6 are already open; this record adds no question to them.
- **UsageCases and StandardScenarios** (S0 and S1 re-checked): no use case step changes. S0 step 4 keeps its known weakness and its open points (OD-31 ④ remainder, ⑥); S1 is unchanged. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **Casts and intermediate precisions**, including whether a later answer of sub-question 2 lets a call site (for example lm_head) run at another dtype than the model's (decision 2), any precision kept between kernels, and a cast in the embedding row copy (OD-31 sub-question 2, owner; ADR-0153 decision 4).
- **fp16** and its contracts (owner, HQ-0065 (1): after PLAN P2-14).
- **The weights**: source, file form, conversion to bf16, their order on reading a model file (sub-question 5, owner; ADR-0156 decision 2).
- **Tolerance values, the reference and the model-level comparison**, the widening of reported logits included (sub-questions 3 and 6).
- **The binary form** in which the host side hands the model program its inputs, the dtype among them, and reads its report; whether one program serves both dtypes (code slices, ADR-0153 Boundaries). The element types are named in decision 3; the file layout is not.
- **The contracts of the other five kinds** — RMSNorm, elementwise add, SwiGLU activation, RoPE, SDPA with KV cache — and the dtypes of their operands, the RMSNorm weights and a frequency table included; the element type of the embedding table.
- **Targets other than `cpu_standin`** and their representation of bf16 (#5 B-2, B-7).
- **Deriving a binding from a key's best** (OD-20, OD-7), and the rest of sub-question 4 that ADR-0153 left open: token selection, the executor's isolation (OD-14), its exposure (sub-question 10, OD-18, OD-23).

## References

- Owner: HQ-0065 in `PROCESS/STATE.json` (through ADR-0154); #5 B-4 (K1), C-6 revision (K2); [Requirements](../Requirements.md) C-6 and OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-31 (sub-questions 2, 4, 5, 6).
- Records: [ADR-0001](ADR-0001-od4-key-schema.md) (decision 2; record format), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 1, 4, 5, 6), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md) (decisions 2, 5), [ADR-0153](ADR-0153-od31-model-executor.md) (decisions 3, 4, 5; Consequences; Boundaries), [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md) (decision 2), [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md) (decisions 1, 2, 5, 6, 7; Consequences).
- Code read: `hilclaw/model_binding.py` (docstring, `check`, `_unfit`), `hilclaw/model_program.c` (header comment), `hilclaw/model_run.py` (docstring, `encode_input`), `hilclaw/gemm_bf16_contract.py` (docstring, `task_contract`).
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-13, P2-14.
