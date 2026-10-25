---
id: T-0470
title: Write ADR-0166, the bf16 forward pass and generation of the model executor on `cpu_standin` (design of ADR-0153 code slice 2; part of OD-31 sub-question 4)
phase: P1
status: DONE
commitMode: doc
coversReq: [C-6, FR-9, FR-10, FR-13, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0428, T-0434, T-0437, T-0443, T-0447, T-0450]
touchesFiles: [ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 260, files: 4}
hq: []
---
## Why

**State on `main` `07d46f6f`.** The model executor of ADR-0153 exists only as code slice 1. That slice is `hilclaw/model_binding.py`, `model_build.py`, `model_run.py`, `model_execute.py`, `model_gemm.py` and `model_program.c`. ADR-0157 code slices 1 and 2 (T-0432 to T-0434) made it run bf16 as well. The program runs a **list of independent GEMM calls** read from an input file. It is not a forward pass (header of `model_program.c`). Since then:
- the contract records of the other five kinds have landed: ADR-0158 (RMSNorm), ADR-0159 (elementwise add), ADR-0160 (SwiGLU), ADR-0161 (RoPE) and ADR-0162 (SDPA with KV cache);
- their host-side binding checks are in `model_binding.py`: `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope` and `check_sdpa`, with T-0437, de26fe2e, T-0443, T-0447 and T-0450;
- the host-side RoPE table builder is `hilclaw/rope_table.py` (T-0446);
- the bf16 verification runs of all six kinds are calibrated: ADR-0163 to ADR-0165, the last slice being T-0469.

ADR-0153 Consequences names **code slice 2**: "the full pass and generation loop over the synthetic model, after the contract records of the other five kinds (P2-11)". That condition now holds. This is PLAN P2-13, and P2-14 needs it.

**Why a record first, not code.** The pass needs choices that no accepted record makes, and which ADR-0153 and ADR-0157 leave to "code slices" or to later records:
- the buffers of one pass and the copies between kernels that the call-site tables of ADR-0159 decision 12, ADR-0160 decision 12, ADR-0161 decision 15 and ADR-0162 decision 15 imply;
- the KV cache allocation per layer;
- how the RoPE table and `eps` reach the program;
- the element type of the embedding table (ADR-0157 Boundaries);
- the check of the weights' element types (ADR-0157 decision 1 and Consequences);
- one whole-generation binding check over the six kinds' checks;
- which of ADR-0153 decision 4's two modes the driver's code can build before OD-31 sub-question 6;
- what the synthetic-model test compares (ADR-0153 decision 6: after sub-questions 2 and 3, which HQ-0065 and HQ-0066 have now answered);
- and how the work splits into tasks within the cap of DRIVER §5 (300 LOC, 5 files excluding tests).

Leaving all of this to code tasks would make each code task invent design. A record under DRIVER §9 is the path for a design-level OD part (OD-31 sub-question 4 is "드라이버" in its attribution).

**The owner-only edges.** Two points touch the owner:
- **The element type of the embedding table.** ADR-0157 Boundaries lists it, and its first Boundaries bullet gives "a cast in the embedding row copy" to sub-question 2 (owner). The owner's answer HQ-0065 says "(1) (a) bf16만", "(2) (a) 입출력은 bf16" and "(3) (a) 커널 경계는 16비트 비트 패턴(`uint16_t`)". The record may read from it that the table is held as bf16 patterns and the row copy is a byte copy with no cast. It may do so only if the record shows the reading follows from the answer's words and from ADR-0157 decision 1 without a new value. It then lists the reading under "Readings for the owner to check". If the executor or the reviewer judges that it does not follow, the record must not choose. It then leaves the embedding element type open, and the task stops BLOCKED (reason: Requirements OD 확정이 필요한 설계 선택, owner-only) with the HQ text of AC 9.
- **Token selection and the model-level comparison** (OD-31 sub-question 6, owner; PLAN P2-13 "⑤~⑧은 … HQ로 묻는다"). No HQ for sub-questions 5 to 8 exists yet in `PROCESS/STATE.json`. The record does not decide them. It drafts the Korean HQ text for sub-question 6, because the generation mode and P2-14's "reference와 맞는다" need it (AC 9). The driver records that HQ from `## Result` (DRIVER §8), as it recorded HQ-0070 from T-0444. The task itself does not wait for it.

**PLAN order and D18.** P2-13 is a checklist item and P2-14 needs it, so the D18 rule does not apply. The round-loop items and P2-5 are held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, and OD-3 for the gate half of P2-4), so work continues on P2-11 to P2-14, as for T-0451 to T-0469. P2-11 and P2-12 are not re-planned here. Registering the six bf16 kinds with `correctness.check`, `spec.write` and the instance start is a separate record (ADR-0163, ADR-0164 and ADR-0165 Boundaries, OD-18 and OD-6). It is out of scope here (Out of Scope).

**D16.** This is a document. Nothing starts `claude`, downloads a model file, or needs a board or an API key. The driver's verification of the code slices this record plans uses synthetic weights, a synthetic tokenizer and hand-written kernels (ADR-0153 decision 6; PLAN P2-13).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the naming, the size cap.
  - §8 (lines 136-142): the HQ fields and Korean question text.
  - §9 (lines 144-151): which OD parts the driver may close and the #5 notice.
  - For this task: branch `claude/T-0470-<slug>`; commit trailer `Task: T-0470`; document mode, so after the reviewer cycle rebase on `origin/main` and push to `main` with the `Reviewed-by: reviewer agent (N rounds, Approve)` trailer.
- `CLAUDE.md`, "상시 규칙": "문서 커버리지 재검사", "미결은 발명하지 않는다", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode).
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in document mode.
- `ARCHITECTURE/decisions/ADR-0001-*.md`, "Record format" (from line 146).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: whole (122 lines). This record builds on it and changes none of its decisions.
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`: whole (126 lines). It is also the model for the Status, Consequences and Boundaries form.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md`: decisions 1 to 3 (lines 31-61) and Boundaries (lines 87-96).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: decisions 2 to 5 (lines 41-104) and Boundaries (lines 150-161).
- Contract records. Read the prototype, operand entries, guarantees at a call and call sites only:
  - ADR-0156 (bf16 `gemm`): decisions 2, 5, 6 and 7 (lines 37-42 and 59-114);
  - ADR-0158: decisions 5 to 7 (lines 57-110);
  - ADR-0159: decisions 7, 8 and 12 (lines 78-117 and 148-159);
  - ADR-0160: decisions 7, 8 and 12 (lines 80-119 and 151-161);
  - ADR-0161: decisions 4 to 6, 10, 11 and 15 (lines 51-67, 88-125 and 154-164);
  - ADR-0162: decisions 4, 5, 10, 11 and 15 (lines 52-67, 103-148 and 177-190).
- Code, read only:
  - `hilclaw/model_program.c` header comment (lines 1-75);
  - the module docstrings of `hilclaw/model_binding.py` (lines 1-125), `hilclaw/model_run.py` (lines 1-56), `hilclaw/model_execute.py` (lines 1-41) and `hilclaw/rope_table.py` (lines 1-25);
  - the signatures of `model_binding.generation_calls`, `check`, `check_rmsnorm`, `check_elementwise_add`, `check_swiglu`, `check_rope` and `check_sdpa`.
- `PROCESS/STATE.json`, `humanQuestions`: HQ-0065, HQ-0066, HQ-0069 and HQ-0070 (do not cross them; HQ-0070, the RoPE scale factor, stays open — the synthetic test gives its own constants).
- `ARCHITECTURE/Requirements.md`: the paragraph "행 형식" (line 84) and the OD-31 row (line 122).
- `ARCHITECTURE/OpenDecisionProposals.md`: the "기록 규칙" bullet (line 8) and § OD-31 (from line 533), sub-questions ②, ④ and ⑥.
- `ARCHITECTURE/StandardScenarios.md`: line 26, the first paragraph of § 검사 결과 (lines 168-172) and the S0 row (line 186).

## Acceptance Criteria

1. **One new record**, `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`, in English, in the ADR-0001 record format (Status, Context, Decision, Alternatives considered, Consequences, Boundaries, References). Its Status:
   - says it is accepted under DRIVER §9 and not confirmed by the owner;
   - separates cited sentences from the record's own;
   - reports an owner-sentence search of #4, #5, #7 and #8, with its terms and its hits read no further than they say;
   - lists the open HQs checked and not crossed;
   - names the part of OD-31 sub-question 4 it answers and what of it stays open.
2. **The pass at bf16** (decision section). For one pass of T rows at position P, in ADR-0152 decision 2's order, the record states:
   - every buffer the model program holds, with its element type and its size in terms of the model parameters and T;
   - for each call site, which buffer each operand of its contract is, taken from the call-site tables of ADR-0159 to ADR-0162 and ADR-0156's layout;
   - every copy the contracts leave (ADR-0153 decision 4) and why it is needed. Where a contract's strides let a call read a producer's buffer in place, the record says so instead of adding a copy;
   - that no cast is made between kernels, citing HQ-0065 (1) and ADR-0157 decision 2.
   Where a contract record already fixes something, cite it; do not restate it.
3. **The KV cache.** The record states:
   - its allocation per layer: capacity at least the positions the generation writes, from the prompt and generation lengths;
   - its pre-call contents and lifetime, within ADR-0153 decision 4 and ADR-0162 decision 4.
   It does not choose a longest sequence or a capacity for Llama 3.2 1B, which ADR-0165 Boundaries gives to sub-question 6.
4. **Inputs the program newly needs.** The record states which arrays and values the host side hands over and by whom they are made:
   - the weights per layer (ADR-0153 decision 3 (b));
   - the RMSNorm weights and `eps`;
   - the RoPE table built by `rope_table.build` from constants the caller gives (no Llama constant is chosen; HQ-0070);
   - the token ids.
   The binary layout of the input file may stay with the code slices (ADR-0153 Boundaries). If so, the record says so.
5. **The embedding table.** The record does exactly one of these:
   - (a) records, as a reading of HQ-0065 and ADR-0157 decision 1, that the table's elements are bf16 patterns and the row copy copies patterns with no cast. It shows the derivation and lists the reading under "Readings for the owner to check".
   - (b) leaves the element type open, attributed to the owner. The task then ends BLOCKED with the HQ of AC 9 (b), and nothing is pushed.
   State in `## Result` which, and why.
6. **Host-side checks before anything is built** (ADR-0153 decision 5):
   - one whole-generation check that runs the six kinds' existing checks and how their outcomes are joined (order, first or all);
   - the element-type check of the weights of ADR-0157 decision 1 and its outcome (invalid input);
   - which run settings are refused.
   No new outcome name unless the record shows the five of ADR-0153 decision 5 do not cover it.
7. **Modes and the report.**
   - The record states which mode the driver's code slices build now. "Given sequence" needs no selection rule. The generation mode's selection rule stays open with sub-question 6.
   - It states the report: token ids and the requested logits rows as bf16 patterns (ADR-0157 decision 3), with lm_head rows "all" or "last".
   - No model-level comparison, reference or tolerance is chosen.
8. **The synthetic-model test and the code slices** (Consequences).
   - The record states what the driver's test of the pass checks, within ADR-0153 decision 6 and HQ-0066. Candidates it weighs in Alternatives:
     - hand-written kernels whose result a Python re-computation predicts exactly;
     - per-kind float64 references with bf16 rounding between calls;
     - checks of call order, buffers and cache only.
     None of them is a model-level acceptance.
   - It lists the code slices in landing order, each within 300 LOC and 5 files excluding tests, naming the modules each touches. Example split: the whole-generation check; the program's pass; the generation loop with the cache; the host-side input encoding and run; the test.
   - It ends with "Runtime acceptance items". (lxviii) of ADR-0153 is already named there; add any new item numbered after the highest existing one, found by searching `ARCHITECTURE/decisions/` for "(lxx".
9. **Owner question**, in the record's Consequences and, as Korean text in DRIVER §8 form (쟁점, 선택지 (a)·(b)·…, 막히는 것과 막히지 않는 것), in `## Result`:
   - (a) always: OD-31 sub-question 6 as the generation mode and P2-14 need it. Cover the token selection rule (for example greedy argmax over the bf16 logits) and what "reference와 맞는다" compares for P2-14's synthetic run and for P2-15 (token match, logit error, reference implementation). Say that the driver's code slices of AC 8 are not blocked by it.
   - (b) only if AC 5 (b): the embedding table's element type.
   Do not ask about sub-questions 5, 7 or 8 unless the record shows the pass needs them.
10. **Register edits.** Follow the rules written in each file, not the wording of earlier tasks:
    - the OD-31 row of `Requirements.md`: add one link to ADR-0166 under `**확정분**:` with a few words of subject, and rewrite `**잔여**:` in place for sub-question ④, by its "행 형식" paragraph;
    - § OD-31 of `OpenDecisionProposals.md`: add one `**채택분**` line for ADR-0166, and rewrite the status at the end of sub-question ④ (and ② if AC 5 (a)) in place, by its "기록 규칙";
    - `StandardScenarios.md`: re-check S0 (step 4's known weakness) and any row the record touches. Update § 검사 결과 by the first paragraph of that section: only the "최근 재검사" line, unless a verdict changes.
    No restatement of the record's content in the registers and no dated paragraph.
11. **Less exact, not edited**: list the sentences of earlier records and code docstrings that become less exact, for example the header of `model_program.c` ("not yet a forward pass") and ADR-0153 decision 4's "none is decided" on casts. Name the search terms used, and do not edit them.
12. **No code, schema or settings change.** In the record's Consequences, an A-13 reading states that no data-plane schema, member, kind, file or validator changes. If the record finds that a model-level run record would be needed, it leaves it to sub-questions 6 and 8 and OD-8, as ADR-0153 does.
13. **§9 notice.** After the push, post one comment on issue #5 naming ADR-0166, the readings for the owner to check and the 7-day objection period. It ends with `— posted by driver`. Give its URL in `## Result`.

## Out of Scope

- Any code: the model program, the host side, `model_binding.py` and tests. Those are the code slices AC 8 lists.
- Registering the bf16 kinds with `correctness.check`, `spec.write` or the instance start (OD-18, OD-6). That is a separate record.
- Deciding OD-31 sub-questions 5 to 10, the RoPE scale factor (HQ-0070), fp16, targets other than `cpu_standin`, the executor's isolation (OD-14), its exposure (OD-18, OD-23), or deriving a binding from `best.json` (OD-20, OD-7).
- Editing any accepted record, including ADR-0153 and ADR-0157 (AC 11 lists, it does not edit).
- `PROCESS/PLAN.md`, `PROCESS/STATE.json` and the deferred lines (the driver's).

## Follow-ups

- The code slices of AC 8, one task each, in the record's order.
- The HQ text of AC 9, recorded by the driver.
- The record of how `correctness.check`, `spec.write` and the instance start reach the six bf16 kinds (P2-14).

## Result

- **Outcome**: DONE. Document mode. `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md` is landed on `main` as `d25a61e4`, together with the register edits in `Requirements.md` (OD-31 row), `OpenDecisionProposals.md` (§ OD-31: an adopted line, ② and ④ status) and `StandardScenarios.md` ("최근 재검사" line). The commit has `Reviewed-by: reviewer agent (4 rounds, Approve)`. The branch `claude/T-0470-od31-bf16-forward-pass` was deleted locally and on the remote.
- **Review**: 4 rounds with a context-isolated `dev-reviewer`.
  - R1: Approve with non-blocking findings and nits: HQ-0034 is answered, an over-reading of HQ-0065 (3), the Status did not name its part of sub-question ②, and some less-exact sentences were missing.
  - R2: Request changes. The slice plan cited the pre-D20 cap of 300 LOC / 5 files; the cache-capacity citation did not match its source; ADR-0153 decision 6's fixture sentence had become less exact; the prefill slice lacked the cache.
  - R3: Request changes (Should-fix). The slice cut points had been lost.
  - R4: Approve, with 3 nits. They were fixed without another review, under D20.
- **AC 5: (a)**, the reading. The table holds bf16 patterns and the row copy makes no cast. The derivation, in decision 5:
  - HQ-0065 (1) to (3) give the dtype bf16 and the representation `uint16_t`.
  - The copied rows are the bf16 operands `x` of `attention_norm` and `a` of `attention_residual`.
  - ADR-0157 decision 1 holds weights in their receiving operand's element type, with no arithmetic on them.
  - Any other table type would therefore need a conversion outside every kernel, which no answer gives.
  - No new value is introduced. The reading is listed under "Readings for the owner to check".
  - All 4 review rounds accepted this reading, so no AC 9 (b) question is needed.
- **Size cap**: AC 8's 300 LOC / 5 files predates D20 (`49a19866`, landed on `main` during this task). The record follows DRIVER §5 (600 LOC / 10 files) and §6 "task 단위" ③. It lists six slices with fixed cut points, which the planner groups into tasks:
  1. the whole-generation check;
  2. the program, prefill only;
  3. the decode passes;
  4. the host-side input and report;
  5. the build-and-run path;
  6. the synthetic test.
  D20 §6 ① (the ADR and its first code slice in one task) postdates this task's planning, so this record is a document-only task.
- **Runtime acceptance**: no new item. ADR-0153's (lxviii) is to be asked once slices 1 to 5 have landed. The highest existing item is ADR-0137's (lxxiv).
- **§9 notice**: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6397327917
- **HQ draft for the driver** (AC 9 (a); reason `owner-only-decision`; `taskId` T-0470; the task is DONE and does not wait for the answer):

  > OD-31 하위 질문 ⑥(모델 수준 정확도의 판정; PLAN P2-13·P2-14·P2-15). ADR-0166(T-0470, main d25a61e4)이 모델 실행기의 bf16 forward pass와 생성 루프를 설계했습니다.
  >
  > 생성 모드는 다음 토큰을 마지막 logits 행에서 고르는 모드입니다. 그 토큰 선택 규칙과, P2-14의 "reference와 맞는다"가 무엇을 비교하는지는 ⑥(오너)으로 남겼습니다. 드라이버 코드는 주어진 시퀀스 모드만 만들고, 생성 모드는 invalid input으로 거부합니다.
  >
  > (1) 토큰 선택 규칙:
  > (a) greedy — bf16 logits 마지막 행의 argmax. 같은 값이면 가장 작은 token id를 고릅니다.
  > (b) 샘플링 — temperature·top-p 등의 값과 seed를 지정해 주십시오.
  > (c) 생성 모드는 두지 않습니다. 주어진 시퀀스 모드만 쓰고, 모델 수준 비교도 teacher forcing으로 합니다.
  > (d) 그 밖.
  >
  > (2) "reference와 맞는다"의 비교 지표. P2-14 합성 run과 P2-15 실제 가중치 run에 각각 답해도 됩니다.
  > (a) 토큰 일치 — 같은 프롬프트에서 reference가 같은 규칙으로 낸 토큰열과 처음 N개 토큰이 같다(N 지정).
  > (b) logit 오차 — 주어진 시퀀스에서 행마다 reference logits와 원소별 rtol·atol로 비교한다(값은 instance처럼 사용자가 지정, 기본값 없음).
  > (c) (a)와 (b) 둘 다.
  > (d) 그 밖(top-k 일치 등).
  >
  > (3) reference 구현:
  > (a) 같은 연산을 NumPy float64로 계산하는 구현 — HQ-0066 (1)의 연장이고 새 의존성이 없습니다.
  > (b) Meta `llama-models`의 PyTorch 구현 — 새 외부 의존성(⑦)입니다.
  > (c) Hugging Face transformers — 새 의존성입니다.
  > (d) 그 밖.
  > 비교가 읽는 lm_head 행("모든 행"/"마지막 행")과 프롬프트·생성 길이는 이 답에 따라 정해집니다. 오너가 지정하지 않으면 드라이버 ADR이 정합니다.
  >
  > 막히는 것:
  > - 실행기의 생성 모드
  > - P2-14의 "reference와 맞는다" 판정과 P2-15의 대조 방법
  > - 모델 수준 run 기록(⑧·OD-8과 함께)
  >
  > 막히지 않는 것:
  > - ADR-0166의 code slice 1~6(주어진 시퀀스 모드와 합성 모델 테스트 — fixture 커널의 Python 재계산과 비트 단위로 비교)
  > - P2-11·P2-12의 그 밖 task
  > - HQ-0070(RoPE scale factor는 (3)의 reference 출처와 함께 정해질 수 있음)

- **Less exact, not edited** (AC 11): the list is in ADR-0166 Consequences, with its search terms. It covers:
  - the header of `hilclaw/model_program.c`;
  - ADR-0153: decision 4 (casts), decision 6 (the pre-answer test and its "to each kind's contract") and the first Boundaries bullet;
  - ADR-0157: decision 1, Context and Boundaries;
  - ADR-0161 decision 6 (the QKV column order);
  - ADR-0159 decision 8 (the example buffers);
  - ADR-0162 and ADR-0165 Boundaries (cache capacity);
  - the docstring of `hilclaw/model_binding.py`.
- **Follow-ups**:
  - the six code slices of ADR-0166 Consequences, grouped by the planner under DRIVER §6 "task 단위";
  - the HQ above;
  - the record registering the bf16 kinds with `correctness.check`, `spec.write` and the instance start (P2-14).
