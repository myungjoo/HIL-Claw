---
id: T-0429
title: Write ADR-0156 - the operational contract of GEMM in bf16 for C kernels on cpu_standin (kind and dtype values, layout, the operation with fp32 accumulation and the rounding of the fp32 -> bf16 output conversion, the uint16_t prototype and its symbol, operand entries, call guarantees, the input distribution, and the op_signature records of the B-4 projections), and update the OD-6 and OD-31 register entries (first Llama kind contract of PLAN P2-11; extension of OD-6 sub-question 1, part of OD-31 sub-questions 1 to 3)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, OD-16, "#5 B-4", "PLAN P2-11", "PLAN P2-12"]
dependsOn: [T-0417, T-0418, T-0423, T-0428]
touchesFiles: [ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 230, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `9859ff3`):
- ADR-0152 (T-0417) lists the six instance-target kinds of one Llama 3.2 1B forward pass: GEMM, RMSNorm, RoPE, SDPA with KV cache, SwiGLU activation and elementwise add. It also gives their shape sets. Its Consequences ask for "one contract record per kind", each fixing its `kind` value, `op_signature` members, layout, prototype and operands "as ADR-0008 did for `gemm`".
- ADR-0154 (T-0423) records the owner's answers HQ-0064, HQ-0065 and HQ-0066:
  - the dtype of the goal is bf16;
  - inputs and outputs are bf16, and the GEMM dot product is accumulated in fp32;
  - on `cpu_standin` a bf16 value crosses the kernel boundary as a `uint16_t` bit pattern and the kernel converts;
  - the reference is NumPy float64 on widened inputs, with per-instance `rtol`/`atol` and no default;
  - each kind's input distribution is fixed by a driver record, finite inputs only.
  
  Its Consequences say the per-kind contract records are now unblocked. Its Boundaries leave to each contract: the `kind`/`dtype` values, the prototype, the intermediate precisions, the rounding of the fp32 -> bf16 conversion and the input distribution.
- ADR-0153 code slice 1 (the model executor for fp32 `gemm`) is complete (T-0419 to T-0428). Code slice 2 needs "the contract records of the other five kinds (P2-11)". The model executor binds a kernel to a call site by comparing the kernel's `task.contract` against "the contract of the call site's kind, dtype, layout and language" (ADR-0153 decision 3). For the bf16 projections no such contract exists yet.
- The only kernel contract today is ADR-0008: `gemm`, `fp32`, `row_major`, C. Its decision 1 says another dtype has its own contract, defined by its own record.

**PLAN order and D18.** PLAN P2 runs in list order. No round-loop item or P2-5 part can be taken now:
- round 0's board step waits on HQ-0021;
- the round >= 1 steps and P2-6/P2-7 wait on HQ-0048 and HQ-0031;
- the gate half of P2-4 is owner-only (OD-3);
- P2-5's start entry has landed (T-0427), and its run needs the round steps above.

P2-10 comes after P2-5. So the next stage is P2-11 to P2-14.

The T-0428 and T-0423 Follow-ups name the next step: the first contract record of a further kind under P2-11. This task takes **GEMM in bf16 first**, for these reasons:
- B-4 says "GEMM first, then the attention family".
- The bf16 projections are five of the call sites of every layer (QKV, O, gate, up, down), plus lm_head.
- The contract extends ADR-0008, so its design questions are the fewest.
- ADR-0153 slice 1 already builds and loads `gemm` kernels. A bf16 `gemm` contract is therefore the shortest path to a first bf16 kernel running in the model executor.

This is a PLAN checklist item (P2-11), needed by P2-13 and P2-14. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, D16.** The owner has already answered every owner-only part this contract needs: dtype, accumulation of the dot product, boundary representation, oracle, tolerance vocabulary and who fixes inputs (ADR-0154). ADR-0154 assigns what remains to "each kind's contract (the extension of OD-6 sub-question 1, driver)": the `dtype` value, prototype, symbol, conversion rounding, input distribution and op_signature records. This is a design OD closed by an ADR under DRIVER §9.

The record changes no member, file, version or validator of the data plane. A new `dtype` value is not a schema change (ADR-0001 decision 6 and its schema-version rule). It is a document; no `claude`, container, board, model file or API key is used.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0429-<slug>`, commit trailer `Task: T-0429`; lines 86-114);
  - §8 (HQ form; lines 136-142);
  - §9 (OD closure by ADR, owner-only parts, 7-day notice; lines 144-151).
- `CLAUDE.md`: "상시 규칙" (three-layer model, "미결은 발명하지 않는다", "문서 커버리지 재검사", "개발 드라이버와 런타임의 구분", the document mode of A-13) and "현재 프로젝트 상태 주의사항".
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`, whole file (180 lines). It is the model for this record: decisions 1 to 9, Alternatives, Consequences and Boundaries. Read decision 4 on the symbol name in particular: "Contracts of the same kind that differ in dtype … are not defined here, and neither is whether they reuse this name". Read decision 9 for the op_signature rule and how the directory names were computed.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`, whole file (101 lines). It holds the owner answers this record builds on (decisions 2 and 3) and the list of what is left to contracts (Boundaries, first bullet).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`:
  - decision 2 (the operation list);
  - decision 4 (lm_head);
  - decision 5 (shape sets; lines 84-104);
  - decision 7 (shapes outside the sets);
  - Alternatives (QKV as one GEMM);
  - Boundaries ("Whether the bf16/fp16 projections are `gemm` with another dtype or another kind is part of it").
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`:
  - decision 3 (lines 40-47): the inputs, the binding, the fit test and the binding "for every shape", loading, and the call through the prototype;
  - Consequences: the code slices (line 88).
- `ARCHITECTURE/decisions/ADR-0017-od16-cpu-standin-verification-run.md`:
  - decision 3 (drawn inputs; lines 38-47);
  - decision 4 (the reference).
  
  This is the precedent HQ-0066 (3) names for a per-kind input distribution.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`:
  - the `op_signature` field table (line 44: `dtype`);
  - the schema-version rule (lines 69-77: a new `dtype` value raises no version);
  - "Record format" (from line 146).
- `hilclaw/keys.py`: `op_signature_key` (for the directory names) and the name pattern `_NAME` (line 34). `hilclaw/gemm_contract.py`, lines 51-70: the fp32 constants and `op_signature_record`. Read only; do not edit.
- `PROCESS/STATE.json` `humanQuestions`:
  - HQ-0064, HQ-0065 and HQ-0066: the `decision` of each, which ADR-0154 quotes;
  - every unresolved HQ, especially HQ-0033 (the ADR-0116 flags, `-ffp-contract=off`) and HQ-0034 (OpenMP on `cpu_standin`), which this record must not cross.
- `ARCHITECTURE/Requirements.md`:
  - FR-9 (line 27) and C-6 (line 63);
  - the **"행 형식" paragraph (line 84)**: the recording rule for a register row;
  - the OD-6 row (line 97) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - the header's **"기록 규칙" (line 8)**: the recording rule for a proposal section;
  - § OD-6 (from line 59), especially sub-question ① (line 70);
  - § OD-31 (from line 523, about 15 lines).
- `ARCHITECTURE/StandardScenarios.md`:
  - S0 and S1, and their rows of the verdict table (lines 186-187);
  - **the first paragraph of § 검사 결과 (line 170)**: the recording rule for a re-check, and the "최근 재검사" line (line 172).
- `PROCESS/PLAN.md` P2-11 to P2-14 (lines 47-50). Read only; do not edit.

## Acceptance Criteria

1. **New record** `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md` (the slug may be adjusted; the number is ADR-0156 unless that number is taken on `origin/main` when the executor starts, in which case use the next free one and say so in Result). It is in English, in the ADR-0001 "Record format", with these sections: Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References.
   - Status separates three kinds of content:
     - what is **cited**: owner answers through ADR-0154 and the HQ `decision` texts, and accepted records;
     - what is the **record's own**, accepted under DRIVER §9: written by the executor, approved by a context-isolated reviewer, 7-day objection window after the #5 notice;
     - which unresolved HQs were checked and not crossed.
   - Status includes an owner-sentence search of issues #4, #5, #7 and #8, for terms such as bf16, bfloat16, uint16, rounding, 반올림, round-to-nearest, GEMM, projection, weight layout. It lists what was found, or says nothing was found. If a found owner sentence conflicts with a choice of this record on an owner-only value, the executor stops and returns BLOCKED (`requirement-unclear`).
   - Status says that no `claude` process was started and no model file was downloaded (D16).
2. **Scope.** The record defines exactly one contract: the GEMM operation of ADR-0152 for bf16, C kernels, on `cpu_standin` (ADR-0154 decision 2 is about `cpu_standin`). It decides, with a reason for each and the rejected option in Alternatives:
   - **kind and dtype**: whether this is `kind` `gemm` with a new `dtype` value or another `kind` (ADR-0152 Boundaries leaves this to this record), and the exact `dtype` spelling. The spelling must match `hilclaw.keys` `_NAME`.
   - **layout**: whether `row_major` of ADR-0008 decision 2 applies with each element a `uint16_t` holding a bf16 bit pattern, or another layout value is needed. Also whether the weight operand stays in ADR-0008's `[in, out]` (k x n) order.
3. **The operation and its precision:**
   - the plain product as in ADR-0008 decision 3, with the same exclusions (no alpha/beta, no accumulation into the output, no transposition flag, no bias);
   - inputs widened from bf16 to fp32 by the kernel, the dot product accumulated in fp32 (**owner**, via ADR-0154 decision 2, cited as such);
   - what "accumulated in fp32" obliges a kernel to do. The record says whether summation order, FMA and wider-than-fp32 intermediates stay the kernel's choice, as in ADR-0008 decision 3. It does not choose a compiler flag (HQ-0033).
   - **the rounding of the fp32 -> bf16 output conversion**: whether the contract fixes it (and if so which, e.g. round-to-nearest-even) or leaves it to the kernel, with the reason. It also says what happens to an fp32 result outside the finite bf16 range, or states that the contract does not define it for the inputs of criterion 6.
4. **The C prototype and symbol:**
   - the single-line text of `task.contract.prototype`, byte for byte, as ADR-0008 decision 4 gives it for fp32;
   - the C type of an operand (`uint16_t`, which needs `<stdint.h>`) and the dimension parameters;
   - the symbol name, with the reason. Weigh: reusing `hilclaw_gemm` (the model program loads each kernel from its own shared library with local symbols, ADR-0153 decision 3) against a dtype-qualified name, and what each means for ADR-0008 decision 7's rule on the `hilclaw_` prefix and for a harness or program that holds kernels of both dtypes.
5. **Operand entries and call guarantees**, as tables in the form of ADR-0008 decisions 5 and 6:
   - operand entries: `name`, `role`, `dtype`, `shape`, parameter;
   - call guarantees: dimensions, overlap, inputs, output, alignment, memory, repeated calls, completion, result.
   
   It also says what the kernel source provides, as ADR-0008 decision 7 does. It states whether the kernel must compute the product for every set of dimensions it is called with, as ADR-0008 decision 6 does for fp32. This is what ADR-0153 decision 3's binding "for every shape" depends on.
   
   Points that are the same as ADR-0008 may be cited rather than restated, as long as the difference is unambiguous.
6. **Input distribution** (HQ-0066 (3): a driver record fixes it, finite inputs only). The record either fixes it here or assigns it explicitly to the P2-12 harness record, with the reason; it must not leave it unassigned. If it fixes it, it gives at least:
   - the range of the drawn bf16 values and why, e.g. no zero or subnormal inputs or products, as ADR-0017 decision 3 reasons for fp32;
   - that every drawn value is finite and exactly a bf16 value;
   - what is left to the harness record: generator, seed and number of draws.
   
   It must not choose a tolerance value or a default (owner: no default).
7. **op_signature records.** The record gives the rule, as ADR-0008 decision 9 does, and the directory names, computed with `hilclaw.keys.op_signature_key` (run it locally; state the command in Result):
   - for the four B-4 projection shapes (gate/up, down, QKV, O) at M in {1, 32, 512} in the new dtype;
   - lm_head may be listed as well, but the record keeps B-4's exclusion of lm_head from the first runs (ADR-0152 decision 4).
   
   It does not decide how a shape set maps to instances (OD-6 sub-question 3).
8. **Consequences** include:
   - the **A-13 reading**: no schema file, member, file, version or validator changes. A new `dtype` value is a new value of an existing field, and `hilclaw/` is not touched.
   - **the code slice this record makes possible**, for the planner, with no code here: the bf16 counterpart of `hilclaw/gemm_contract.py` (`task_contract`, `covers`, op_signature), its use by `hilclaw/model_binding.py` and the model program, and calibration-style hand-written kernels. Also the P2-12 harness work of a bf16 `gemm` verification run (reference widening, comparison).
   - **Less exact, not edited**: search `ARCHITECTURE/` for statements that only fp32 `gemm` has a contract, or that a bf16 GEMM contract is pending (e.g. ADR-0152 Consequences/Boundaries, ADR-0153 decision 3 "for other kinds, through the prototypes of their future contract records", ADR-0154 Boundaries). List them without editing, and do not claim the list is complete.
   - **Runtime acceptance items**: none expected. If one appears, write it in the DRIVER §8 form, Korean question, reason `runtime-acceptance`, for the driver to record.
9. **Boundaries** name, each with its owner or OD:
   - fp16 (owner, after P2-14);
   - tolerance values (instance parameters, FR-9);
   - build flags and OpenMP (HQ-0033, HQ-0034, OD-6 sub-question ②);
   - the harness mechanism and the parts of the input distribution left to P2-12;
   - corner-case and non-finite inputs (#5 B-7, OD-16);
   - shapes outside an instance's (OD-16 sub-question ①);
   - how a shape set maps to instances (OD-6 sub-question ③);
   - OD-6 sub-question ④ (contract change);
   - the other five kinds' contracts;
   - backends other than `cpu_standin` (#5 B-2, B-7);
   - weights and their conversion to bf16 (OD-31 ⑤, owner);
   - any change to the first case (fp32 `gemm`, ADR-0008, ADR-0017).
10. **`ARCHITECTURE/Requirements.md`**: only the OD-6 row (line 97) and the OD-31 row (line 122) change. Each follows the file's own "행 형식" paragraph (line 84) as written there. Read that paragraph and apply it, not an earlier task's wording.
11. **`ARCHITECTURE/OpenDecisionProposals.md`**: only § OD-6 and § OD-31 change. Each follows the header's "기록 규칙" (line 8) as written there: one `**채택분**` line per section for this record, and the status at the end of each sub-question this record answers in part, rewritten in place:
    - OD-6 ①;
    - OD-31 ① and ②, and ③ if the input distribution is fixed here.
    
    Rewrite the state word at the head of each bullet if it changes. Do not edit the opening paragraph of § OD-31 (owner text).
12. **`ARCHITECTURE/StandardScenarios.md`**: re-check S0 and S1, and any scenario whose row cites OD-6 ① or OD-31, by the file's check rules (CLAUDE.md "문서 커버리지 재검사"). Record the result as the first paragraph of § 검사 결과 (line 170) prescribes. In a verdict-table note, change only an open reference that this record closes; keep anything still open.
13. **No other file changes.** In particular, do not edit:
    - `PROCESS/PLAN.md` or `PROCESS/STATE.json`;
    - ADR-0008, ADR-0152, ADR-0153, ADR-0154 or ADR-0017;
    - any `hilclaw/` file;
    - any test, C file or catalog file.
14. **Process**: document mode (CLAUDE.md A-13).
    - Pass the context-isolated reviewer cycle (dev-item-address steps 10-12) to Approve.
    - Then rebase on `origin/main` and push to `main` directly with the trailers `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0429`.
    - The reviewer checks, at least:
      - that the owner answers are cited without change of meaning, and nothing beyond them is presented as the owner's;
      - that no tolerance value, build flag or OpenMP setting is chosen;
      - that the prototype text and the op_signature directory names are exact;
      - that the three register edits follow the recording rules of their own files.
    - Write the DRIVER §9 owner notice text for issue #5 (ending `— posted by driver`) into Result. Post it after landing only if the driver's instruction says so.

## Out of Scope

- Any code: the bf16 `gemm_contract` counterpart, `model_binding`/`model_program` changes, hand-written bf16 kernels, the P2-12 harness. These are later tasks.
- The contracts of RMSNorm, elementwise add, SwiGLU activation, RoPE and SDPA with KV cache: one later record each.
- fp16, quantised variants, layouts other than the one this record decides, kernel languages other than C, backends other than `cpu_standin`.
- Tolerance values; build flags (HQ-0033); OpenMP (HQ-0034); the weights and their conversion (OD-31 ⑤).
- Editing #5 comments; editing earlier ADRs (list them as less exact instead).
- The PLAN "보류" list and the round-loop items of P2-1 to P2-7.

## Follow-ups

- (planner) Next under P2-13/P2-11: the code slice of this record. That is the bf16 counterpart of `hilclaw/gemm_contract.py`, with binding fit in `hilclaw/model_binding.py` and a hand-written bf16 kernel through the model program, split to the size cap. After that comes the next kind's contract record. Choose the order in that task's Why, unless an HQ answer reopens a round-loop item first.

## Result
