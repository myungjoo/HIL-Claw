---
id: T-0528
title: Read a Hugging Face Llama model directory into the executor's dimensions, constants and bf16 weights (HQ-0084, OD-31 sub-questions 5 and 7)
phase: P2
status: DONE
commitMode: code
coversReq: [OD-31, C-6, FR-9, FR-10, "PLAN P2-15", "HQ-0084", D26]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0191-od31-hugging-face-model-files.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/model_files.py
  - tests/test_model_files.py
estimatedSize: {loc: 450, files: 5}   # test code is outside the cap
hq: []
---
## Why

**State.** RA-0056 (PLAN P2-15) is the owner's run of real Llama 3.2 1B weights through the kernels the instances produced. `hilclaw.model_forward_container.execute` takes `ModelDimensions`, `eps`, `RopeConstants` and `Weights` from its caller, and ADR-0166 decision 4 leaves making them to "a test or a later loader, sub-question 5". No such loader exists: `hilclaw/` holds no safetensors reader.

**Owner decision.** HQ-0084, answered 2026-10-31: "① (a) ② (a) ③ (a) ④ (a) - 오너(채팅, 2026-10-30): ① Hugging Face의 safetensors와 tokenizer 파일, base 변형(저장소 이름은 오너가 지정하지 않았다 — 파일은 ②의 경로로 받는다). ② 런타임 머신의 사용자 경로를 입력으로 받고 데이터 plane에 넣지 않는다. ③ transformers와 함께 런타임 머신의 선택 의존성으로 두고 드라이버·CI에는 넣지 않는다. ④ 오너가 수동 실행할 명령줄을 드라이버 task로 만든다(드라이버 검증은 합성 파일)."

**Why now (D26).** This is the PLAN hold line "OD-31 ⑤·⑦ (PLAN P2-15 준비)", which DRIVER §6 D26 names as work for the owner's P2-15 check. Unanswered HQ-0081, HQ-0082, HQ-0083 and HQ-0085 do not touch it.

**The trap this task must not fall into.** ADR-0161 Context and Boundaries record that the Hugging Face converter stores the Q and K projections through `permute(w, n_heads, …)`, in another order of the head elements than the pairing `(2i, 2i + 1)` of the executor's RoPE contract. A loader that only joins the tensors would produce wrong logits at every position while every shape check passes.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `f35826ae`.

**D16.** Verification uses files the tests write. No real weights, Hugging Face access, token, `claude` or Docker daemon is used, and no package is installed.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (branch `claude/T-0528-<slug>`, the `Task: T-0528` trailer in commits and as the last line of the PR body, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D26, §8 (D22) and §9.
- `CLAUDE.md`: A-13 code mode, the BLOCKED reasons, the test rules, comment minimisation, the language policy and the coverage recheck for `ARCHITECTURE/` edits.
- `PROCESS/STATE.json`: the `HQ-0084`, `HQ-0070` and `HQ-0071` entries. `PROCESS/RuntimeAcceptance.md`: RA-0035, RA-0050 and RA-0056.
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`: Context ("Another source of the constants", line 29), decisions 4 to 6, and Boundaries (line 205).
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`: the buffer table, row 4 of the pass table, and decision 4.
- `ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md`: decisions 1 and 2, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph and the OD-31 row. `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" and section OD-31. `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과.
- Code: `hilclaw/model_forward_check.py` (`RopeConstants`, `Weights`, `check`), `hilclaw/model_binding.py` (`ModelDimensions`, `rmsnorm_eps`), `hilclaw/rope_table.py` (`build`, `constant_refusals`), `hilclaw/model_reference.py` (`reference_logits`).
- Tests: `tests/test_model_reference.py` (`sharp_model`, `arguments`).
- Upstream, read with `gh api` and cited by commit as ADR-0161 does: `huggingface/transformers` `src/transformers/models/llama/convert_llama_weights_to_hf.py`, `configuration_llama.py` and `modeling_llama.py`. Do not download any model repository; `meta-llama` repositories are gated and need no reading here.

## Acceptance Criteria

1. **ADR-0191**, in the "Record format" of ADR-0001, records the HQ-0084 answer (owner, not subject to the objection window) and decides under DRIVER §9:
   - **The directory.** The caller names a directory on the runtime machine. What is read from it: `config.json`, and either `model.safetensors` or `model.safetensors.index.json` with its shards. The directory is never copied, stored or recorded in the data plane or CAS (HQ-0084 ②).
   - **The reader.** Whether a safetensors reader is written on the standard library and NumPy, or the `safetensors` package is used. The first is expected: the format is small, the code path then runs in CI, and CI must not gain the package (HQ-0084 ③). State the reason for the choice. If a package turns out to be needed at run time, it is imported lazily and is not added to `pyproject.toml`, the `dev` group, or CI.
   - **The tensor mapping.** A table from each Hugging Face tensor name to its `Weights` field, including the transpose from PyTorch's `[out, in]` to the executor's `[in, out]`, and the join of `qkv` in the column order Q, K, V of ADR-0166.
   - **The Q and K order.** Settle what ADR-0161 Boundaries left open, by reading the upstream converter and modelling code at a cited commit: whether the inverse of `permute` is applied, on which axis, with which head count for K, and before the join. Show the derivation. If a real file could be stored either way and nothing in the directory tells which, say so and state what follows; this can be a runtime acceptance item, not a guess presented as a fact.
   - **The tied head.** What gives `lm_head` when `lm_head.weight` is absent and when it is present, under `tie_word_embeddings`.
   - **The element type.** bf16 tensors are handed over as bit patterns with no conversion. Any other stored dtype is a named refusal; no rounding to bf16 is invented.
   - **The constants.** Which `config.json` members give each `ModelDimensions` field, `eps` and each `RopeConstants` field, including the forms different `transformers` versions write if the upstream reading shows more than one, and that a missing member is a named refusal. No Llama value is written in code as a default (HQ-0070, ADR-0176 decision 6). The value 32 of HQ-0070 is expected from the file, not supplied by the code.
   - **Boundaries** names what stays open: the tokenizer, the `transformers` reference and the entry (T-0529's work; do not design them here), the artifact (⑧), model-level performance (⑨), the scenario (⑩), and fp16 (HQ-0083). It lists its runtime acceptance items for `PROCESS/RuntimeAcceptance.md` (expected at least: the tensor names, the stored dtype and the Q and K order of the file the owner obtains).
   - **The A-13 reading**: no data-plane change and no new dependency in CI or the driver.
2. **A new module `hilclaw/model_files.py`**, with the Doxygen-style public documentation of its neighbours. Later tasks rely on this interface, so keep these names:
   - `read(directory)` returns a `ModelFiles` named tuple with the fields `dimensions` (`ModelDimensions`), `eps`, `rope` (`RopeConstants`) and `weights` (`Weights`, whose arrays are native-order `numpy.uint16`).
   - `ModelFileError` carries a `reason`, one of the module's public named constants, and each refusal below has one.
   - It writes nothing, starts nothing and is registered as no tool.
   - The reader bounds what it allocates from a file: the header length, offsets that leave the data section, overlapping or uncovered ranges, a shape whose byte count does not equal its range, and member names given twice in the JSON are refused before any tensor array is made. No pickle file is ever read.
3. **Tests**, in `tests/test_model_files.py`, on files the tests write with `struct` and `json`:
   - **Happy:** a small synthetic model, one file and sharded, and with a present and an absent `lm_head.weight`. The result passes `model_forward_check.check` for its arrays at `bf16` with no argument or weight reason.
   - **The order, independently.** Build the executor-layout weights, write them in the Hugging Face arrangement with the upstream `permute`, and read them back to bit-equal arrays. A test-local float64 computation of Q and K rotated by the upstream half-split rule on the stored tensors gives the same attention scores, within a bound the test states, as the pair rule on the read weights. Scores are compared because the two head-element orders differ by a permutation.
   - **The whole pass.** `model_reference.reference_logits` on the read result equals its result on the weights the test started from.
   - **Branch:** each form of the constants the ADR names; little-endian bytes reach native patterns.
   - **Error and negative:** a missing directory, config or weights file; malformed JSON; each reader refusal of criterion 2; a truncated file; a missing tensor; an extra tensor if the ADR refuses it; a wrong tensor shape; a non-bf16 dtype; a missing constant; dimensions that do not fit one another; an absent head with tying off; a shard index that names a tensor absent from its shard or a path outside the directory.
   - Every public function is covered. Existing tests keep passing, and their assertions change only as D21 allows; no such edit is foreseen, and each one made is listed in the PR body.
4. **Records.** `Requirements.md` follows its "행 형식" (one link for the new ADR, open parts rewritten in place). `OpenDecisionProposals.md` follows its header's "기록 규칙" (one `채택분` line; the ⑤ and ⑦ statuses rewritten in place). `StandardScenarios.md` §검사 결과 follows the rule in its first paragraph, and coverage is rechecked as CLAUDE.md requires. Restate no ADR content there and add no dated paragraph.
5. **Result** records: the language and the reason; the reader choice; the mapping's Q and K conclusion; any edited assertion; runtime acceptance items for the driver to add; that the §9 notice on #5 is due with its 7-day window.

## Out of Scope

- The tokenizer, the `transformers` reference, the comparison and the command line (T-0529); the instance documents and the owner's steps (T-0530).
- Real weights, a download, a real `claude`, a D25 test run, or a Docker daemon (D16; RA-0056).
- Any data-plane change, a CAS blob, or a record of a model-level run (OD-31 ⑧, A-13).
- A Meta-format checkpoint (HQ-0084 ① (b) was not chosen), fp16 (HQ-0083), and quantised files.

## Follow-ups

## Result

PR #346, squash-merged as 21f5cec7 (code mode, 2 review rounds, Approve, CI green). No BLOCKED, no HQ. Section 9 notice: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6540391360 (7-day window from 2026-10-31).

- Language: Python. The reader feeds NumPy inputs and needs nothing beyond NumPy, and HQ-0084 (3) keeps packages out of CI.
- Reader: own safetensors reader on the standard library and NumPy; `pyproject.toml` and CI unchanged.
- Q and K: the inverse of `permute` is applied on the output axis, with H for Q and H_kv for K, before the transpose and join; V is untouched. The file has no mark of its arrangement and transformers defines these names as half-split, so the reader matches the P2-15 reference however the file was made. A file written with Meta's order under these names would pass the logit comparison and still be wrong (RA-0064).
- Edited assertion (D21): `tests/test_rope_table.py::test_the_module_is_named_only_by_its_known_callers` gains `model_files.py`.
- Size: 589 non-blank added lines outside tests, about 710 with blank lines. DRIVER section 5 does not say whether blank lines count against the 600 cap; the PR body states both counts.
- Coverage: `hilclaw/model_files.py` line coverage 100% locally on the review-fix commit.
- Runtime acceptance items: RA-0062, RA-0063, RA-0064.
- Follow-ups: none. The tokenizer, `transformers` reference and command line stay with T-0529, the owner's steps with T-0530.
