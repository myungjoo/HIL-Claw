---
id: T-0417
title: Write ADR-0152 - the operation list and shapes of one Llama 3.2 1B forward pass, as single compute-kernel instances (OD-31 sub-question 1, for PLAN P2-11)
phase: P1
status: IN_PROGRESS
commitMode: doc
coversReq: [C-6, FR-5, OD-31, OD-6, "#5 B-4", "PLAN P2-11"]
dependsOn: []
touchesFiles: [ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md, ARCHITECTURE/Requirements.md, ARCHITECTURE/OpenDecisionProposals.md, ARCHITECTURE/StandardScenarios.md]
estimatedSize: {loc: 280, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `481720b`):
- PLAN P2-5 (the first end-to-end run) cannot move. Every remaining piece of it waits on an open owner HQ:
  - the selection side of a round >= 1 (HQ-0048);
  - the coder's start in its container (HQ-0053);
  - the run tools' operation and `board.run` registration (HQ-0021);
  - the compiler log (HQ-0026);
  - the instance start (HQ-0032, open PR #186).
- ADR-0151 slices 1 and 2 (T-0415, T-0416) were the last unblocked P2-5 work.
- PLAN P2-10 (nightly) runs after P2-5 and needs an owner HQ first.
- The next PLAN checklist item whose dependencies hold is **P2-11**: the operation contracts for the reach goal P2-14 (Llama 3.2 1B end-to-end, C-6 revision of 2026-10-19).
- P2-11 says that the operation list and shapes need **OD-31 closed by the DRIVER §9 ADR path (sub-question 1)**. Any part that changes a value of the owner's #5 B-4 answer goes to the owner as an HQ.
- Nothing of OD-31 has been recorded yet; its register row says "미착수".

**This task** writes the first OD-31 record: which operations one Llama 3.2 1B forward pass is made of, how they split into single compute-kernel instances (C-6: the instance unit stays one compute kernel; graph-level fusion is later), and the shape set of each. It is a PLAN checklist item, so the D18 hold rule does not apply to it (DRIVER §6). It is on the path to P2-14, the reach goal.

**Owner-only parts this task must not decide** (DRIVER §9; OpenDecisionProposals § OD-31 marks each one's owner):
- bf16 vs fp16 and accumulation precision (sub-question 2);
- oracles and tolerances (3);
- weights and tokenizer (5);
- model-level accuracy, prompts and generation lengths (6);
- new external dependencies (7);
- the artifact (8);
- model-level performance (9);
- the scenario (10).

Sub-question 4 (the model executor) is the driver's, but it is **not** this task.

**A known conflict inside #5 B-4.** The owner's B-4 answer says "16 heads / 8 KV heads" and "GQA 16/8". It also says QKV 2048→3072, hidden 2048 and head_dim 64. Those three values fit 32 query heads (32 × 64 + 2 × 8 × 64 = 3072), not 16. Meta's own parameters for Llama 3.2 1B also give `n_heads` 32 and `n_kv_heads` 8 (source below).
- Choosing between the two changes a value of an owner answer. Only the owner can do that (P2-11; OpenDecisionProposals § OD-31 sub-question 1 already says "확인이 필요하다").
- The ADR must not choose. It records what depends on the head count and words the question for the owner (acceptance criterion 6).
- The driver records that question as a non-blocking HQ when it wraps up this task.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED by HQ-0032) touches `hilclaw/start_instance.py` and three test files only. No open PR edits `ARCHITECTURE/`.

**D16.** The task reads public documents only. It needs no `claude`, no gated weight or tokenizer file, no Hugging Face login, no board and no API key. The architecture parameters come from Meta's public `meta-llama/llama-models` GitHub repository; `gh api` reads it without any extra credential.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, the 2h30m limit, no force push;
  - §5 (lines 86-114): task format; naming convention (branch `claude/T-0417-<slug>`, trailer `Task: T-0417`); size cap;
  - §8 (lines 136-142): HQ form, used for the owner question of criterion 6 and if you return BLOCKED;
  - §9 (lines 144-151): who may close which OD; the #5 notice and the 7-day objection window.
- `CLAUDE.md`, 상시 규칙: "문서 커버리지 재검사", "미결은 발명하지 않는다", "세션 진입 점검", "개발 드라이버와 런타임의 구분", "브랜치·merge 절차" (document mode). Also 현재 프로젝트 상태 주의사항, "MVP 범위".
- `ARCHITECTURE/Requirements.md`:
  - line 63 (C-6 and its 2026-10-19 revision);
  - line 84 ("행 형식", the rule for any edit of a register row);
  - line 122 (the OD-31 row).
- `ARCHITECTURE/OpenDecisionProposals.md`:
  - line 8 ("기록 규칙", the rule for any edit of a section);
  - § OD-31 (lines 520-533): the ten sub-questions and their owners. Sub-question 1 is the one this record answers in part;
  - § OD-6 head (lines 59-62): other kinds' contracts are the extension of OD-6 sub-question 1.
- `ARCHITECTURE/StandardScenarios.md`:
  - line 26 and § 검사 결과 (from line 168): the first paragraph is the recording rule for the "최근 재검사" line and the change history;
  - the S0 row of the verdict table (about line 186).
- The owner's B-4 answer: `gh api repos/myungjoo/HIL-Claw/issues/comments/5944412285 --jq .body`. It gives:
  - the reference model and its listed values;
  - GEMM first, then the attention family with KV cache;
  - the four projections and lm_head's exclusion from the first runs;
  - M ∈ {1, 32, 512};
  - SDPA prefill and decode with seq_len ∈ {128, 2048}.
- The owner's C-6 revision of 2026-10-19: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280029924 (`gh api repos/myungjoo/HIL-Claw/issues/comments/6280029924 --jq .body`).
- Meta's architecture parameters and reference forward pass, read at commit `0e0b8c519242d5833d8c11bffc1232b77ad7f301` of `meta-llama/llama-models`. Cite the commit in the ADR.
  - `models/sku_list.py` lines 325-344 (`llama3_2_base_models`, `arch_args` of `llama3_2_1b`): `dim` 2048, `n_layers` 16, `n_heads` 32, `n_kv_heads` 8, `ffn_dim_multiplier` 1.5, `multiple_of` 256, `norm_eps` 1e-05, `rope_theta` 500000.0, `use_scaled_rope` True, `vocab_size` `LLAMA3_VOCAB_SIZE`.
  - `models/llama3/args.py` and `models/llama3/model.py`: how the FFN hidden size follows from `dim`, `ffn_dim_multiplier` and `multiple_of`; RMSNorm; rotary embedding with scaling; attention with the KV cache and GQA repeat; the SwiGLU feed-forward; the output projection.
  - Read them with `gh api "repos/meta-llama/llama-models/contents/<path>?ref=0e0b8c519242d5833d8c11bffc1232b77ad7f301" --jq .content | base64 -d`.
  - Whether Llama 3.2 1B ties `output` to the embedding: state it only if a file you read at that commit shows it. Otherwise name it as not established here.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` § "Record format" (from line 146): sections and their order, one closure per record, English.
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: the first kind's contract. Read it to see what a per-kind contract decides, so that this record does not decide it for other kinds.
- `ARCHITECTURE/decisions/ADR-0031-od8-instance-record-op-signature.md` decision text: what `op_signature` holds. It shows why naming a `kind` value or `op_signature` member here would be a data-plane decision that this record leaves to each kind's contract record.
- `ARCHITECTURE/decisions/ADR-0151-od6-first-case-later-round-spec.md` lines 1-30: a recent record's Status layout (owner-sentence search, cited vs own content, open HQs checked, §9 status). Use it as a pattern of structure, not of wording.
- `PROCESS/STATE.json` `humanQuestions` entries without `resolvedAt`: check that none is crossed (criterion 8).

## Acceptance Criteria

### The record
1. A new file `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`, in English, in the ADR-0001 record format. The slug may differ; keep the number unless `main` already has an ADR-0152, in which case take the next free number and use it everywhere below.
   - Status: accepted under DRIVER §9 by the reviewer's approval, not confirmed by the owner, open to objection for 7 days after the #5 notice.
   - An owner-sentence search over #4, #5, #7 and #8 (bodies and the comments without the "posted by driver" marker). Terms such as Llama, 1B, attention, SDPA, RMSNorm, RoPE, SwiGLU, lm_head, embedding, prefill, decode, seq_len, KV cache, heads. Quote what is found and read each quote no further than it says.
   - Every sentence is either cited (source named) or the record's own.
2. **The operations of one forward pass.** Decide the list of operations one Llama 3.2 1B forward pass is made of, from token ids to logits, for prefill and for one decode step. Cover at least:
   - the embedding lookup;
   - per layer: RMSNorm; the projections; RoPE; attention with the KV cache and GQA; the output projection; the SwiGLU activation; the residual adds;
   - the final RMSNorm and lm_head.
   For each operation, decide whether it is an **instance target** (a single compute kernel an instance optimizes, C-6) or not. For each "not", say what it is instead (part of another operation's kernel, or work outside the kernels), so that the list is complete.
   - Where the split is a choice, the record weighs it in "Alternatives considered". Examples: QKV as one GEMM as B-4 states, or three; SwiGLU's `silu(gate) * up` as its own kernel or inside a GEMM; softmax and the KV-cache write inside the SDPA kernel or separate; RoPE inside attention or separate.
   - The choice must not contradict B-4 (QKV 2048→3072 as one projection; "SDPA with KV cache") or C-6's "graph-level fusion is later". State where a choice relies on reading those sentences.
   - Token selection after the logits (argmax or sampling) is sub-question 6's or 4's. Name it as outside unless the record shows it is plainly a kernel; do not decide generation settings.
3. **The shapes.** For each instance target, give its shape set from the architecture parameters and B-4:
   - M ∈ {1, 32, 512} for the token dimension of the projections, as B-4 states;
   - seq_len ∈ {128, 2048} for prefill and decode SDPA;
   - batch 1, unless the record argues otherwise.
   Derive the FFN hidden size from `dim`, `ffn_dim_multiplier` and `multiple_of` as `args.py`/`model.py` compute it, and show that it equals B-4's 8192.
   - **lm_head**: B-4 excludes it "from the first runs" (cost). State how the end-to-end list treats it under the C-6 revision, as a reading of the two owner sentences. Do not override B-4's first-run exclusion.
   - **Shapes the forward pass meets that are not in these sets** (for example a prompt of 7 tokens, or a decode step at KV length 300): state whether a kernel of an instance must accept them, and if this record leaves that open, name where it belongs (each kind's contract under OD-6 sub-question 1, or sub-question 4).
4. **Not decided here, and named so** (Boundaries):
   - the `kind` values and `op_signature` members of each new operation, and each kind's kernel contract (the extension of OD-6 sub-question 1, as ADR-0008 did for `gemm`). Write them as plain names in prose, not as data-plane values;
   - the dtype and accumulation precision (sub-question 2, owner);
   - oracles and tolerances (3);
   - the model executor and the handling of operations with no kernel (4);
   - weights and tokenizer (5);
   - model-level accuracy and generation (6);
   - new external dependencies (7);
   - the artifact (8);
   - model-level performance (9);
   - the scenario (10);
   - the order in which kinds are taken up after `gemm`, beyond B-4's "GEMM first, then the attention family".
5. **No data-plane schema change**: no member, file, kind, value or version of the data plane is added or changed, and no validator changes. State this in Consequences ("A-13 reading").
6. **The head-count conflict** (Why):
   - The record states the conflict between B-4's "16 heads / 8 KV heads" and the values that imply 32 heads (B-4's own QKV 2048→3072, hidden 2048 and head_dim 64; Meta's `n_heads` 32).
   - It decides nothing that depends on the head count. In particular it gives no head count for the attention shapes: it writes them with the count as a named parameter and says which shapes wait on the answer. The GEMM shapes do not depend on it.
   - In Consequences it gives a question for the owner, in Korean, in the DRIVER §8 form: the issue; options (a) 32 query heads as Meta's parameters and the other B-4 values imply, (b) 16 as written, (c) something else; and what is and is not blocked while unanswered.
   - In `Result`, give the same question text so that the driver can record it as an HQ (reason `owner-only-decision`, non-blocking).
7. **Consequences** also list:
   - the planner's next steps under P2-11: one contract record per kind, then code. Point out that each contract needs sub-questions 2 and 3, which are the owner's, so the driver must ask them as HQs before any contract task (PLAN P2-12);
   - runtime acceptance items: expected none. If one is found, list it so that the driver can record it as a `runtime-acceptance` HQ;
   - "Less exact, not edited": sentences of earlier records or documents that this record makes less exact, found by a search, not claimed complete;
   - the UsageCases/StandardScenarios reading (criterion 11).
8. **Open HQs checked and not crossed**. List the unresolved HQs in `PROCESS/STATE.json` that touch this subject and show that none is decided. At least:
   - HQ-0031 and HQ-0034 (OpenMP);
   - any HQ about OD-6, OD-9 or #5 B-items.
   If one would have to be decided, stop and return BLOCKED.

### The register and proposals
9. `ARCHITECTURE/Requirements.md`, the OD-31 row only. Follow the "행 형식" rule at line 84:
   - the status word with date and path;
   - one ADR link with a few words of topic under `**확정분**:` (or the status vocabulary the rule uses for a partial answer);
   - `**잔여**:` rewritten in place to name what stays open of sub-question 1 (at least the head count and the per-kind contracts) and sub-questions 2 to 10.
   Do not restate the record or add a dated paragraph. No other row and no C-6 text change.
10. `ARCHITECTURE/OpenDecisionProposals.md` § OD-31 only. Follow the "기록 규칙" at line 8:
    - one adopted-record line for the ADR;
    - sub-question 1's status rewritten in place (`→ 부분 답: [ADR-0152](…). 남음: …`) and its bullet head's status word changed;
    - the question's wording kept.
    No dated notes, no restatement of the record.
11. `ARCHITECTURE/StandardScenarios.md`. This is the coverage re-check that CLAUDE.md requires because Requirements changes:
    - re-check S0 (and any scenario the record touches) by the check rules of that document;
    - update § 검사 결과 by its first paragraph: rewrite the "최근 재검사" line in place; add a history entry only if a verdict changes or a gap is found or closed.
    No ADR summary.
12. No other file changes. `git diff origin/main --stat` lists only `touchesFiles`. In particular there are no changes to:
    - `hilclaw/`, `orchestration/`, `catalog/`, tests, `.claude/`, `.github/` or any settings file;
    - UsageCases, `PROCESS/` (except this task's `Result`) or `HIL-Claw-data`.
    Non-test LOC is under 300 in at most 5 files; record it.

### Process
13. Document mode (CLAUDE.md A-13):
    - Run the `dev-reviewer` cycle (dev-code-review), at most 7 rounds. Ask the reviewer explicitly to check:
      - (a) every architecture value against the cited `llama-models` files at the pinned commit, and the FFN derivation;
      - (b) that no owner-only part (sub-questions 2, 3, 5 to 10, the head count, B-4's values) is decided;
      - (c) that no `kind` value, `op_signature` member or other data-plane value is added;
      - (d) that the operation list is complete from token ids to logits, and each "not an instance target" says where its work goes;
      - (e) that the register and proposals edits follow the "행 형식" and "기록 규칙" texts and the StandardScenarios recording rule.
    - On Approve, rebase on `origin/main` and push to `main` directly, with `Reviewed-by: reviewer agent (N rounds, Approve)` and `Task: T-0417` trailers.
    - A finding that starts with `SECURITY` is BLOCKED.
14. After landing, post the DRIVER §9 notice on #5:
    - in English;
    - with the record's link and the landing commit;
    - stating the 7-day objection window and that the head-count question goes to the owner as an HQ;
    - ending with the line `— posted by driver`.
15. `Result`:
    - landing commit, review rounds, the #5 notice URL;
    - non-test LOC and files;
    - the Korean owner question of criterion 6;
    - any runtime acceptance item;
    - the planner follow-ups.

## Out of Scope

- Each new kind's kernel contract, `kind` value, `op_signature` members, harness checks and code (later P2-11 tasks).
- bf16/fp16, oracles, tolerances (P2-12; owner HQs).
- The model executor (P2-13, OD-31 sub-question 4).
- Weights, tokenizer, accuracy, generation, dependencies, artifacts, model-level performance, the scenario (owner sub-questions 5 to 10).
- Any change of the first case (fp32 `gemm`, PLAN P1-5, ADR-0008) or of B-4's first-run settings.
- Downloading any model file. Starting `claude`.
- Any edit outside `touchesFiles`.

## Follow-ups

- (planner) After this record, P2-11's per-kind contracts need the dtype and oracle answers (OD-31 sub-questions 2 and 3, owner-only). The next planner raises them as an HQ before planning any contract task (PLAN P2-12). The head-count question of criterion 6 is recorded by the driver from this task's `Result`.

## Result

