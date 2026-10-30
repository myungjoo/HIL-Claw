# ADR-0154: The owner's answers on the head count, the precision and the oracle of the Llama 3.2 1B goal — 32 query heads, 8 KV heads, head_dim 64; bf16 only with fp32 accumulation and `uint16_t` bit patterns at the kernel boundary; a float64 reference, per-instance `rtol` and `atol`, and per-kind input distributions by driver record (part of OD-31 sub-questions 1, 2 and 3)

## Status

- **Accepted on 2026-10-24.** It records three owner answers and draws what follows from them for the kind contracts of PLAN P2-11 and the harness of P2-12.
- **Two kinds of content.**
  - **The owner's answers are cited**, marked **owner**, from the `decision` of HQ-0064, HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (answers given in chat on 2026-10-24, recorded by commit `eafce0a`). They are the owner's and are **not subject to the objection window** below.
  - **Everything else is this record's own**: the restated shape rows, the reading of which values the answers leave open, the readings marked as such, and the lists of Consequences and Boundaries. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts that part and the edits made with it.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 46 of its 251 comments whose text holds no "posted by driver" marker; the bodies of #7 and #8 and their comments (2 and 6). Terms: bf16, fp16, 정밀도, precision, accumulation, 누적, tolerance, rtol, atol, oracle, 오라클, reference, float64, heads, GQA. The owner sentences found that touch the subject, each read for what it says and no further:
  - **K1** — the B-4 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285): "16 heads / 8 KV heads, head_dim 64"; "attention configuration (GQA 16/8, head_dim 64, RoPE, causal)"; "correctness uses random inputs against a float64 reference (FR-9)"; "dtype **fp32** (bf16 weights upcast); fp16 / q4 are later instance variants"; "Correctness oracle for the stand-in: A-7 recommendation (NumPy float64, tolerance as instance parameter) stands, awaiting confirmation" (later confirmed by HQ-0004, K4).
  - **K2** — the C-6 revision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924): "Precision: bf16/fp16."
  - **K3** — the A-6 decision (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693): "Tolerance is a user-adjustable Loop-instance parameter … The vocabulary (per-dtype rtol/atol, downstream-metric thresholds, user-defined checks) is fixed after #5 B-7 is answered."
  - **K4** — the HQ-0004 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052377983): NumPy float64; per-element `rtol` and `atol`, instance parameters; no defaults. The HQ-0005 answer (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6117798837): the same harness, predicate and tolerance at both points on `cpu_standin`. The A-7 and A-12 decisions (comments 5944117402, 5946779596): a system-generated NumPy float64 reference for the stand-in; the harness holds the "f64 reference".
  - Not owner sentences, read only as context: the closing note on the head count of the C-6 revision comment (a note); the #7 research body and its comment 5566900982 ("FP64/FP32 CPU 레퍼런스", "per-(op,dtype) tolerance", corner cases); the same table in #8 comment 5141454502; the #4 comment 5139248800 (pinning the tolerance per instance, OD-11). #4, #7 and #8 hold no owner sentence on the subject.
  - **Conflicts, and which is followed.** K1's "16 heads" and "GQA 16/8" against HQ-0064: the owner corrects them in HQ-0064, which is followed. K2's "bf16/fp16" against HQ-0065 (1): HQ-0065 is the owner's later answer to what "bf16/fp16" means and puts fp16 off rather than dropping it; it is followed. K1's "fp32 … fp16 / q4 are later" is the first case, which stays (decision 2). K1's float64 reference, K3 and K4 agree with HQ-0066. No conflict is left that touches an owner-only value.
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `48acd9c`). **HQ-0033** (the ADR-0116 flags, `-ffp-contract=off` among them) and **HQ-0034** (OpenMP on `cpu_standin`): no build setting is changed or chosen. **HQ-0021**, **HQ-0026** and **HQ-0048** (the parts of P2-5): not touched. **HQ-0022**, **HQ-0024**, **HQ-0028**, **HQ-0029** (code tasks) and **HQ-0031** (injected hypotheses): not touched. The runtime-acceptance HQs (HQ-0013, HQ-0014, HQ-0016 to HQ-0019, HQ-0030, HQ-0035 to HQ-0039, HQ-0042, HQ-0044 to HQ-0047, HQ-0049 to HQ-0052, HQ-0054 to HQ-0063, HQ-0068): no runtime fact is used. HQ-0023 and HQ-0027 (review limits of other records): not touched.
- **Not changed**: **no member, file, kind value, `dtype` value, `op_signature` member or version of the data plane is added or changed**, and no validator changes; the precision and the oracle are named in prose. It is a record, not code: no `claude` process was started, no model file was downloaded, and nothing was tried in a live session (D16).
- **Answers**: of OD-31 sub-question 1, the head count; of sub-question 2, the dtype, the accumulation of three sums and the `cpu_standin` representation; of sub-question 3, the reference, the tolerance vocabulary and who fixes the input distribution. Open of them: Boundaries.
- It builds on and amends [ADR-0152](ADR-0152-od31-llama-forward-operations.md) (decision 5's RoPE and SDPA rows, decision 6), and builds on [ADR-0153](ADR-0153-od31-model-executor.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 1, 3, 6) and [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md). Neither ADR-0152 nor ADR-0153 is edited. The format follows the "Record format" section of ADR-0001.

## Context

- ADR-0152 wrote the RoPE and SDPA shapes over H and d_h and left the head count to the owner (its decision 6), because K1 gives "16 heads" and also hidden 2048, head_dim 64 and QKV 2048 → 3072, which fit 32 query heads. Its Consequences left the dtype, the accumulation precision, the oracle and the tolerance of every contract to the owner (OD-31 sub-questions 2 and 3, PLAN P2-12). ADR-0153 left the same three open (its Status and Boundaries).
- The driver asked them as HQ-0064, HQ-0065 and HQ-0066 (reason `owner-only-decision`, task T-0417). The owner answered all three in chat on 2026-10-24.
- The precedent for the oracle is the first case: fp32 `gemm` on `cpu_standin`, whose reference, tolerance vocabulary and defaults are the owner's HQ-0004 answer and whose input distribution (finite, magnitude in [0.5, 1) with either sign) is ADR-0017's own design.

## Decision

A sentence marked **owner** quotes or renders an HQ `decision`. A sentence is **cited** when another source is named with it. Every other sentence is **this record's own**.

### 1. The head count (HQ-0064)

- **Owner** (HQ-0064): "(a) - 오너(채팅, 2026-10-24): query head 32개, KV head 8개, head_dim 64. #5 B-4의 "16 heads"·"GQA 16/8"은 32·32/8로 고친다. ADR-0152는 H = 32, d_h = 64를 대입한다."
- The owner's correction applies to K1's "16 heads / 8 KV heads" and "GQA 16/8", which read 32 and 32/8. The #5 comment is not edited; this record and HQ-0064 are where the correction is written.
- **The RoPE and SDPA rows of ADR-0152 decision 5, restated with H = 32, KV heads = 8 and d_h = 64.** These rows amend that table; every other value and set is ADR-0152's, unchanged:

| Kind | Call | Shape set | Waits on the head count? |
|---|---|---|---|
| RoPE | 5 | Q as T × 32 × 64 and K as T × 8 × 64, positions P … P+T−1, `rope_theta` 500000 with Llama 3 scaling (Meta); for prefill (P = 0) T ∈ {128, 2048} and for a decode step T = 1 at P ∈ {127, 2047}, matching the SDPA calls | No |
| SDPA with KV cache | 6, 7 | prefill: T = S, P = 0, L = S; decode step: T = 1, P = S − 1, L = S; S ∈ {128, 2048} (B-4); Q of T × 32 × 64, new K and V of T × 8 × 64, cache of 8 × 64 per position, output T × 2048, causal | No |

- **The GEMM shapes of ADR-0152 are unchanged**: they are B-4's values and already equal Meta's under H = 32, d_h = 64 (ADR-0152 decision 5). So are the RMSNorm, elementwise add and SwiGLU activation rows.
- ADR-0152 decision 6 ("Not decided") and its alternative of 16 query heads of 128 with 4 KV heads are superseded by the answer for this goal; nothing else of ADR-0152 changes, as its decision 6 said of answer (a).

### 2. The precision (HQ-0065)

- **Owner** (HQ-0065): "오너(채팅, 2026-10-24): (1) (a) bf16만 - fp16은 Llama 3.2 1B end-to-end(P2-14) 뒤로 미룬다. (2) (a) 입출력은 bf16, 누적(GEMM 내적·RMSNorm 제곱합·softmax 합)은 fp32. (3) (a) 커널 경계는 16비트 비트 패턴(`uint16_t`)으로 하고 변환은 커널이 한다."
- **The dtype of the Llama goal is bf16** (owner). fp16 comes after the Llama 3.2 1B end-to-end of PLAN P2-14 (owner); when and in what form is not decided here. **The first case is unchanged**: fp32 `gemm`, ADR-0008, PLAN P1-5.
- **Inputs and outputs of each kind are bf16; accumulation is fp32** for the three sums the owner named (owner): the GEMM dot product, the RMSNorm sum of squares and the softmax sum. That these are exactly the sums the answer covers is this record's reading.
- **Every other intermediate precision is not settled by the answer**, and this record does not choose one. Examples: RoPE's angles, frequencies and sin/cos; the SiLU of the SwiGLU activation; the accumulation of the two dot products inside SDPA (the Q·Kᵀ scores and the product of the probabilities with V — SDPA is not the GEMM kind, so the answer's "GEMM 내적" is not read as covering them); the scaling of the SDPA scores and the precision in which the scores and the probabilities are held; the cast between the score product and the value product; the RMSNorm reciprocal square root and weight multiply. Each belongs to its kind's contract record (the extension of OD-6 sub-question 1, driver).
- **On `cpu_standin`, a bf16 value crosses the kernel boundary as its 16-bit pattern in a `uint16_t`, and the kernel converts** (owner). The rounding of the kernel's fp32 → bf16 conversion is not stated by the owner, nor whether it belongs to the contract or is left to the kernel. It is left to the contract records (Boundaries).
- The `dtype` value that names bf16 in an `op_signature` or an operand entry, and the prototype that carries `uint16_t`, are the contract records'; ADR-0008 decision 1 already says another dtype has its own contract.

### 3. The oracle, the tolerance and the inputs (HQ-0066)

- **Owner** (HQ-0066): "오너(채팅, 2026-10-24): (1) (a) 입력을 float64로 넓혀 NumPy float64로 계산(새 의존성 없음). (2) (a) 모든 kind에 원소별 rtol·atol, instance 파라미터, 기본값 없음. (3) (a) kind마다 드라이버 ADR이 정한다(유한 입력만)."
- **The reference** widens each bf16 input to float64 and computes the kind's operation in NumPy float64 (owner). It does not emulate bf16 rounding, the question's option (b) that the answer did not take. **No new dependency is added** (owner) — no `ml_dtypes`, no PyTorch.
- **Every kind compares element-wise with `rtol` and `atol`**, both instance parameters with no default (owner). This extends the HQ-0004 answer of the first case (K4) to every Llama kind. This record names no tolerance value.
- **Each kind's input distribution is fixed by a driver record, with finite inputs only** (owner; the question named ADR-0017 as the model). Reading that record as the kind's contract record or its harness record is this record's own. This record fixes no distribution, range, seed or number of draws.
- **This record's own reading**, no value and no default: every bf16 value is exactly representable in float64 (and in fp32), so widening the inputs and the kernel's output to float64 loses nothing. What the comparison sees is the kernel's error, the bf16 rounding of its output included, which a tolerance must allow, against a reference whose own error is that of float64 arithmetic. Widening a 16-bit pattern needs no bf16 type in NumPy: it is the upper half of the fp32 pattern of the same value.

## Alternatives considered

| Choice | Alternative | Why not |
|---|---|---|
| Restate the RoPE and SDPA rows here | Edit ADR-0152 | An accepted record is not edited; a later record restates what it amends (as ADR-0056 and ADR-0078 did). |
| Leave every intermediate precision but the three sums to the contracts | Read "누적은 fp32" as covering every intermediate value | The owner names three sums; reading more into it would present the record's choice as the owner's. |
| Leave the fp32 → bf16 rounding to the contracts | Fix round-to-nearest-even here | The owner's answer says the kernel converts and states no rounding; a contract can fix it with the operation it belongs to. |
| Name no input distribution | Take ADR-0017's range for every kind | The owner gives each kind its own driver record; one range does not suit every kind (RoPE positions, softmax inputs, RMSNorm's eps). |

## Consequences

- **A-13 reading**: no member, file, kind value, `dtype` value, `op_signature` member or version of the data plane is added or changed, and no validator changes; `hilclaw/` is not touched.
- **What is now unblocked**: the per-kind contract records of PLAN P2-11 — GEMM in bf16, RMSNorm, elementwise add, SwiGLU activation, RoPE and SDPA with KV cache — each with its intermediate precisions, conversion rounding, input distribution and layout; and the harness of P2-12. **This record does not choose** the order of the contracts, nor whether the bf16 projections are `gemm` with another dtype or another kind; both stay where ADR-0152 Boundaries put them.
- **ADR-0153's synthetic-model tests** (its decision 6) may now compare against a float64 reference, with `rtol` and `atol` the test passes itself as the calibration tests do (ADR-0017 decision 6); no value is fixed here, and their kernels and inputs follow the contract records.
- **Less exact, not edited** (found by a search of `ARCHITECTURE/` and `PROCESS/PLAN.md` for `bf16/fp16`, `head count`, `16 heads`, `GQA 16/8` and `head 수`; not claimed complete):
  - Requirements C-6 "정밀도는 **bf16/fp16**이다" (the owner's text, kept) and the owner-decision phrase of the OD-31 row;
  - ADR-0152 decision 6, its "Waits on the head count?" column, its Consequences (the HQ-0064 text, "GEMM in bf16/fp16", the owner questions of sub-questions 2 and 3) and Boundaries on the head count, dtype and oracles;
  - ADR-0153 Status ("Open HQs checked", "Owner-only parts not decided") and Boundaries on dtype, oracle and head count; its title;
  - the opening paragraph of OpenDecisionProposals § OD-31 ("정밀도는 **bf16/fp16**", owner text) and the wording of its sub-questions ① and ②;
  - OpenDecisionProposals § OD-4, the first concrete instance ("GQA 16/8");
  - PLAN P2-12 "bf16/fp16";
  - outside the search: `CLAUDE.md` "MVP 범위", `README.md` and DRIVER D18, which say "bf16/fp16" of the goal.
- **Runtime acceptance items**: none. Nothing here needs a live `claude`, a board or a model file.
- **UsageCases and StandardScenarios** (S0 and S1 re-checked): no use case step changes. The tolerance vocabulary of the Llama kinds on `cpu_standin` is no longer open; the vocabulary outside the first case and those kinds on `cpu_standin` stays with #5 B-7. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **Each kind's contract** (the extension of OD-6 sub-question 1, driver): its `kind` and `dtype` values, `op_signature` members, layout, prototype and operands, its intermediate precisions beyond the three sums, the rounding of its fp32 → bf16 conversion and whether the contract or the kernel fixes it, and its input distribution (or the harness record's).
- **fp16**: when and in what form, after PLAN P2-14 (owner).
- **Tolerance values**: instance parameters, set by the user (FR-9); the harness has none.
- **OD-31 sub-question 4**, its open parts (ADR-0153 Boundaries); **sub-questions 5 to 10** (owner parts included).
- **How a shape set maps to instances** (OD-6 sub-question 3; ADR-0031 decision 4).
- **Any change to the first case** (fp32 `gemm`, ADR-0008, ADR-0017, PLAN P1-5) or to B-4's first-run settings.
- The order of the kinds after `gemm`; whether verification draws shapes outside an instance's (OD-16 sub-question 1); corner-case and non-finite inputs (#5 B-7, OD-16); whether these answers hold on a backend other than `cpu_standin` (#5 B-2, B-7).

## References

- Owner: HQ-0064, HQ-0065 and HQ-0066 in `PROCESS/STATE.json` (questions of 2026-10-23, answers in chat of 2026-10-24, commit `eafce0a`); #5 B-4 (K1), C-6 revision (K2), A-6 (K3), HQ-0004 and HQ-0005 answers, A-7 and A-12 (K4); [Requirements](../Requirements.md) C-6, FR-9, OD-6 and OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-31.
- Records: [ADR-0001](ADR-0001-od4-key-schema.md), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md), [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md), [ADR-0031](ADR-0031-od8-instance-record-op-signature.md), [ADR-0152](ADR-0152-od31-llama-forward-operations.md), [ADR-0153](ADR-0153-od31-model-executor.md).
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9, D16; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-11 to P2-14.
