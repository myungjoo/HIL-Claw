---
id: T-0494
title: Record the owner's answer to HQ-0071 (OD-31 sub-question 6) and design the model-level reference, the teacher-forced logit comparison and the greedy generation mode of the model executor as one new ADR, and land its first code slice — a NumPy float64 reference forward pass and the logit comparison, with tests
phase: P2
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, FR-13, OD-31, OD-6, S0, "PLAN P2-13", "PLAN P2-14"]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/model_reference.py
  - tests/test_model_reference.py
  - tests/test_model_forward_execute.py
estimatedSize: {loc: 520, files: 5}   # non-test: ADR ~220, new reference/comparison module ~280 (code + docstring), registers ~15, StandardScenarios only if the coverage re-check changes a verdict. Tests are outside the cap; the ADR's lines count (DRIVER §5, D4/D20). The ADR and module file names are suggestions: use the next free ADR number, and split the module in two (reference, comparison) if that reads better. If the ADR and this slice together are seen to exceed the cap, finish the ADR and the reference forward pass, and propose the comparison as a follow-up task (DRIVER §5).
hq: []
---
## Why

**State.** PLAN P2-13 (model executor) is the first P2 item in PLAN order with work left that P2-14 needs; P2-10 is blocked on HQ-0076 (T-0493). The bf16 forward pass of the model executor is landed (ADR-0166, code slices 1 to 6: T-0471 to T-0474; `hilclaw/model_forward_check.py`, `hilclaw/model_forward.c`, `hilclaw/model_forward_run.py`, `hilclaw/model_forward_execute.py`). It builds only the given-sequence mode, refuses the generation mode as invalid input, and has **no model-level reference, comparison or tolerance**: ADR-0166 left those to OD-31 sub-question 6 (owner) and drafted HQ-0071 for them (ADR-0166 decision 7, Consequences "Owner question", Boundaries first bullet). Every one of the three model-level modules says so in its docstring ("OD-31 sub-question 6, HQ-0071").

**HQ-0071 is answered** (`PROCESS/STATE.json`, `resolvedAt` 2026-10-26T01:28:12Z, owner in chat). Its `decision`, quoted:

> (1)(a), (2) P2-14 (b)·P2-15 (c), (3) P2-14 (a)·P2-15 (c) - 오너(채팅, 2026-10-26): (1) greedy — bf16 logits 마지막 행의 argmax, 같은 값이면 가장 작은 token id. (2) P2-14 합성 run은 teacher forcing으로 행마다 reference logits와 원소별 rtol·atol로 비교한다(값은 사용자 지정, 기본값 없음). P2-15 실제 가중치 run은 그에 더해 같은 프롬프트에서 처음 N개 greedy 토큰이 reference와 같아야 하며, 둘 다 만족해야 맞는다(N은 사용자 지정). (3) P2-14의 reference는 NumPy float64 구현이다. P2-15의 reference는 Hugging Face transformers이며, 런타임 머신 쪽의 선택 의존성으로 허용하고 드라이버·CI의 의존성으로는 넣지 않는다.

No record carries this answer yet (no ADR, no register line; OpenDecisionProposals § OD-31 still shows sub-question 6 as `→ 미결.`). P2-14's "the executor generates tokens with those kernels and they match a reference" needs (a) a reference, (b) the comparison the owner chose and (c) a generation mode with the owner's selection rule. This task records the answer, designs (a) to (c) where the answer leaves design to the driver, and lands (a) and (b).

**Design level, owner parts cited.** The owner answered the owner-only parts (selection rule, metric, reference implementation). What remains is design under DRIVER §9 (OD-31 sub-question 4's "the token selection rule and where it is applied", and the driver-side details of sub-question 6 that the HQ itself said "오너가 지정하지 않으면 드라이버 ADR이 정합니다": which logits rows the comparison reads, prompt and generation lengths). Per D20 ① the ADR and its first code slice are one code-mode task. If writing the ADR shows that a choice needs a value no owner sentence gives and that is owner-only (#5 A/B items, C-6, OD-25, OD-3 — for example a Llama-specific tolerance, prompt or length, the weights or tokenizer of sub-question 5, the artifact of sub-question 8), do not choose it: name it in Boundaries, and if it blocks this slice, stop and return BLOCKED with the question (DRIVER §8).

**PLAN order and D18.** P2-13 is a checklist item and P2-14 needs this work; the D18 rule does not apply.

**No RuntimeAcceptance `실패` item is fixed by this task** (none exists as of `main` `341fd8a4`).

**D16.** The P2-15 reference (Hugging Face transformers) is a runtime-machine optional dependency by the owner's answer: it is **not** added to `pyproject.toml`, CI or any driver test, and nothing here loads real Llama weights, a tokenizer, a model file or starts `claude`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (task format, naming convention `claude/T-0494-<slug>`, `Task: T-0494` trailer, size cap, test rules D12, list-assertion rule D21), §8 (HQ and runtime acceptance items, D22), §9 (ADR path: Approve, OD status, owner notice on #5 with `— posted by driver`).
- `CLAUDE.md` (repo) — "상시 규칙" (comments, coverage re-check, "미결은 발명하지 않는다", branch/merge procedure, test rules, language policy, D16 driver/runtime boundary).
- `.claude/skills/dev-item-address/SKILL.md` and `.claude/skills/dev-code-review/SKILL.md`.
- `PROCESS/STATE.json` — the `question` and `decision` of HQ-0071 (and HQ-0070's decision: the RoPE scale factor 32 of Llama 3.2 1B; the synthetic tests keep their own constants).
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md` — whole (decisions 2 to 8, Alternatives rows 7 and 8, Consequences "Owner question", Boundaries).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` — decisions 3 to 6 and Boundaries.
- `ARCHITECTURE/decisions/ADR-0154-od31-owner-answers-heads-bf16-oracle.md` — how earlier owner answers on OD-31 were recorded and cited (form only; do not copy its register edits).
- `ARCHITECTURE/decisions/ADR-0163-od31-bf16-verification-run.md` — the per-kind float64 reference and the predicate (widening, `rtol`/`atol`, non-finite output); `ADR-0164` decision on the RoPE table rows; `ADR-0165` the SDPA reference per query head.
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md` decisions 4 and 6, and `hilclaw/rope_table.py` (`build`, `constant_refusals`).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md` decisions 4, 5 and 15 (GQA, scale, causal rule).
- `hilclaw/model_forward_check.py`, `hilclaw/model_forward_run.py`, `hilclaw/model_forward_execute.py` — module docstrings, `check`, `encode_input`, `ForwardReport`/`ForwardProgramResult`, `execute`.
- `hilclaw/model_binding.py` — `ModelDimensions`, `rmsnorm_eps`, the call-site tuples.
- `tests/test_model_forward.py` lines ~250-440 (`widen`, `narrow`, the per-kind re-computations, `make_model`, `generate`) and `tests/test_model_forward_execute.py` (the synthetic-model test of ADR-0166 decision 8 and its fixture kernels).
- The latest ADR (`ARCHITECTURE/decisions/ADR-0175-od19-first-case-turn-session-output.md`) for the present ADR form (Status, Context, Decision, Walk-through if useful, Alternatives considered, Consequences, Boundaries, References).
- `ARCHITECTURE/Requirements.md` — the "행 형식" paragraph and the OD-31 row.
- `ARCHITECTURE/OpenDecisionProposals.md` — header "기록 규칙" and § OD-31 (sub-questions 4 and 6).
- `ARCHITECTURE/StandardScenarios.md` — the rule section near the top, S0 step 4, and the first paragraph of §검사 결과.

## Acceptance Criteria

1. **ADR** — one new file `ARCHITECTURE/decisions/ADR-NNNN-…md` (next free number; ADR-0176 as of `main` `341fd8a4`) filed under OD-31, in the form of the latest ADRs:
   - **Records HQ-0071's answer as cited owner content** (not subject to the objection window), each of its three parts and both runs (P2-14 synthetic, P2-15 real weights), including that the P2-15 reference is a runtime-machine optional dependency and not a driver or CI dependency. It states which parts of OD-31 sub-questions 4, 6 and 7 the answer closes and which stay open.
   - **Decides, as this record's own** (with reasons and an Alternatives table for each point where more than one choice is reasonable):
     - **the P2-14 reference forward pass**: how the NumPy float64 implementation computes one generation of ADR-0166's pass from the same inputs the executor gets (weights as bf16 patterns, `eps`, the RoPE constants or table, token ids) — at least: how bf16 inputs are widened; whether activations are kept in float64 throughout or rounded to bf16 at kernel boundaries (weigh against HQ-0066 (1)(a), HQ-0071 (3)(a), ADR-0163's per-kind reference and ADR-0166 Alternatives row 8 (b)); whether the RoPE rotation uses the fp32 table of `rope_table.build` widened or float64 angles; the causal GQA attention over the cache as ADR-0162 defines it;
     - **the teacher-forced comparison**: which logits rows it reads (the `lm_head_rows` value(s) it requires or accepts), the per-element predicate and its handling of non-finite output and non-finite reference values, `rtol` and `atol` as caller-given with no default (owner), what the result reports (pass/fail and enough to locate a failing row and element), and how it is joined with the executor's result (a separate function over a `ForwardReport`, or a path through `model_forward_execute`);
     - **the greedy generation mode** for a later slice: where the owner's rule (argmax of the last bf16 logits row, smallest token id on ties) is applied — in `hilclaw/model_forward.c` between passes or on the host side — how ties and non-finite logits are handled, what replaces the generation-mode refusal of ADR-0166 decisions 6 and 7, and what the report then holds; the P2-15 "first N greedy tokens equal the reference's" check is named but its implementation is left to the runtime (D16);
     - prompt and generation lengths: caller-given (no Llama value chosen).
   - **Constraints, stated as cited**: no new external dependency (NumPy is already a runtime dependency, HQ-0004); no data-plane change — no record of a model-level run (sub-question 8, OD-8 stay open; a choice that needs one is a CLAUDE.md A-13 BLOCKED reason); no Llama-specific tolerance, prompt, length, cache capacity, weight file, tokenizer or RoPE constant is chosen (sub-question 5, HQ-0070's answer is for the Llama model parameters, which the caller gives).
   - **Code slices** listed in landing order in Consequences (slice 1 is this task's; the generation mode is a later slice), as ADR-0166 does.
   - **Less exact, not edited**: the sentences of earlier ADRs and docstrings the record makes less exact (at least ADR-0166 decisions 6 and 7, Boundaries first bullet, and the "no … model-level reference or tolerance (OD-31 sub-question 6, HQ-0071)" sentences of the three `model_forward*` docstrings); the docstrings this task's code touches are corrected, others are listed.
   - **Runtime acceptance items**, if any (a fact only the runtime machine shows, e.g. about the P2-15 comparison with Hugging Face transformers), are listed and handed to `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22) by naming them in the task's Result; the ADR says it hands them to that file. Do not add a PLAN P2-15 item: the planner adds that after P2-14 is checked (PLAN P2-15).
2. **Registers** — follow the recording rules written in the files themselves; do not copy wording from earlier task files:
   - `ARCHITECTURE/Requirements.md`: the OD-31 row by its "행 형식" paragraph — the owner's answer as one owner phrase and the new ADR as one link after `**확정분**`, the `**잔여**` part rewritten in place (sub-question 6 and the token-selection part of 4 no longer listed as open where the record closes them), the status cell kept short; no restatement of the ADR, no dated chain.
   - `ARCHITECTURE/OpenDecisionProposals.md` § OD-31 by the header's "기록 규칙" — one `**채택분**` line for the ADR, and the end state and bullet-head status word of sub-questions 4, 6 (and 7 if the record answers part of it) rewritten in place; the questions' wording stays.
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by its rules (CLAUDE.md; S0 step 4 names OD-31 ⑥ as an open point) and record only as the first paragraph of §검사 결과 says (a history line only if a verdict changes).
3. **Code (slice 1)** — a new 2-layer module (suggested `hilclaw/model_reference.py`; the ADR names it) that:
   - computes the reference logits of one teacher-forced generation as the ADR decides, from the same arguments `hilclaw/model_forward_check.check` / `model_forward_execute.execute` take (dimensions, weights, `eps`, RoPE constants, prompt, given tokens, `lm_head_rows` as the ADR allows), refusing malformed or invalid arguments before computing, consistently with how `model_forward_check` refuses them (reuse it rather than duplicating the checks where possible);
   - compares a `ForwardReport`'s logits rows with the reference by the ADR's predicate with caller-given `rtol` and `atol` (no default), and reports the result as the ADR says;
   - casts nothing the ADR does not say, writes nothing to disk, stores nothing, and gives no model parameter a default.
   - The three `model_forward*` docstrings' "no model-level reference or tolerance" sentences are corrected where this slice makes them wrong; the generation-mode refusal stays until its slice.
4. **Tests** (D12: happy, error, branch and negative cases; every public function of the new module; coverage gates hold; a new module gets `tests/test_model_reference.py`):
   - the reference forward pass on a tiny synthetic model equals an independent straightforward float64 computation in the test (or hand-checked values) for at least two layers, H > H_kv, S ≥ 2, G ≥ 3, under each `lm_head_rows` value the ADR allows;
   - through `model_forward_execute.execute` with the fixture kernels of `tests/test_model_forward_execute.py` (clang; skipped where clang/POSIX is missing locally, run on CI): the executor's logits pass the comparison for tolerances that the test states and justifies from the fixtures' bf16 rounding, and fail it when one fixture kernel is miswired (e.g. a shifted RoPE row or a dropped cache row) — showing the comparison catches a wiring error the bit-exact test was built for;
   - the predicate: an element exactly at the bound passes, just over fails; a NaN or infinite output element fails; the ADR's rule for a non-finite reference value;
   - negative cases: missing, negative, non-finite or non-numeric `rtol`/`atol`; a report whose row count or width does not match the arguments; an `lm_head_rows` the ADR does not allow; malformed weights or dimensions (as `model_forward_check` reports them).
   - Existing tests keep passing. Under D21, assertions that pin a list of public names, imports, fields or binders may be edited only as far as this change requires and are listed in the PR body. Foreseen: none in `tests/test_model_forward_check.py`, `tests/test_model_forward_run.py` or `tests/test_model_forward_execute.py` unless the ADR joins the comparison into `execute` (then a public-name or result-field set asserted for `ForwardResult`-like tuples may need the new field). Other existing assertions, including the bit-for-bit synthetic test of ADR-0166 decision 8, are not weakened.
5. **No real `claude`, no model files** (D16): nothing requires a logged-in `claude`, Docker, an image, a token, Llama weights or a tokenizer, a board or network access; no Hugging Face package is installed or imported by the package or tests.
6. **Procedure**: branch `claude/T-0494-<slug>`, Draft PR whose title holds `T-0494` and whose body ends with `Task: T-0494`, review cycle (dev-code-review, ≤ 7 rounds), CI green, squash-merge with that body (DRIVER §5). After merge, the §9 owner notice on #5 for OD-31 (7-day objection window for this record's own parts; the owner's HQ-0071 answer is cited, not under objection), ending with `— posted by driver`. Result records the language choice (Python, NumPy already a dependency) in one line, the next code slice (the greedy generation mode) as the planner's candidate, and any runtime acceptance item.

## Out of Scope

- The greedy generation mode's code (later slice of the new ADR), and removing ADR-0166's generation-mode refusal.
- The P2-15 comparison with Hugging Face transformers, real Llama 3.2 1B weights, a tokenizer, model file conversion or the joined QKV weight from a checkpoint (sub-question 5), the artifact (8), model-level performance (9), the scenario (10).
- Registering the six bf16 kinds with `correctness.check`, `spec.write` or the instance start, and deriving a binding from a key's best (OD-18, OD-6, OD-20, OD-7) — later P2-14 work.
- fp16, an fp32 forward pass, targets other than `cpu_standin`, the executor's isolation and limits (OD-14, NFR-4), any data-plane record of a model run.
- Editing earlier ADRs or the "less exact" sentences outside the docstrings this slice touches (they are listed in the ADR's Consequences; PLAN "보류" already holds the ADR-0166 one as a T-0470 follow-up).

## Follow-ups

## Result
