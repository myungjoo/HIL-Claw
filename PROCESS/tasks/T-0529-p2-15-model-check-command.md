---
id: T-0529
title: Add the command line the owner runs for P2-15 — tokenize, generate through the named runs' kernels in containers, and compare with Hugging Face transformers (HQ-0084 ④, HQ-0071)
phase: P2
status: TODO
commitMode: code
coversReq: [OD-31, C-6, FR-9, FR-10, "PLAN P2-15", "HQ-0084", "HQ-0071", D26]
dependsOn: [T-0528]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0192-od31-model-check-command.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/model_hf_reference.py
  - hilclaw/model_check.py
  - tests/test_model_hf_reference.py
  - tests/test_model_check.py
estimatedSize: {loc: 550, files: 6}   # test code is outside the cap
hq: []
---
## Why

**State.** After T-0528 the pieces of the owner's P2-15 run exist apart: `hilclaw.model_files.read` (T-0528), `hilclaw.model_run_binding.binding_from_runs` (ADR-0189), `hilclaw.model_forward_container.execute` (ADR-0182) and `hilclaw.model_reference.compare` (ADR-0176). Nothing joins them, and there is no tokenizer and no `transformers` reference. ADR-0176 decision 5 names the P2-15 check and does not build it.

**Owner decisions.**
- HQ-0084 ④ (a): "오너가 수동 실행할 명령줄을 드라이버 task로 만든다(드라이버 검증은 합성 파일)." ③ (a): transformers and the packages for weights and the tokenizer are optional dependencies of the runtime machine, not of the driver or CI.
- HQ-0071: "P2-15 실제 가중치 run은 … teacher forcing으로 행마다 reference logits와 원소별 rtol·atol로 비교 … 그에 더해 같은 프롬프트에서 처음 N개 greedy 토큰이 reference와 같아야 하며, 둘 다 만족해야 맞는다(N은 사용자 지정)." The reference is Hugging Face transformers. Greedy means the argmax of the last row, with the smallest token id on ties.

**Why now (D26).** This is the entry half of the PLAN hold line "T-0516 follow-up — P2-15 준비", which DRIVER §6 D26 names. The binding half landed as T-0518.

**What stays open.** OD-31 ⑩ (whether this flow becomes a scenario, and in which tier) and ⑧ (the artifact and the run's record) stay the owner's. The command answers HQ-0084 ④ only: it adds no scenario and writes no record.

**RuntimeAcceptance.** No item has the status `실패` as of `main` `f35826ae`. If T-0528 or a later status changes this, follow DRIVER §6.

**D16.** The command never starts `claude`. Verification uses a stub `docker` client, synthetic files and fake `transformers` and `torch` modules that the tests place in `sys.modules`. Neither package is installed or added anywhere.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 and §5 (branch `claude/T-0529-<slug>`, the `Task: T-0529` trailer in commits and as the last line of the PR body, the size cap, D12, D21), §3 "BLOCKED 사유", §6 D26, §8 (D22) and §9.
- `CLAUDE.md`: A-13 code mode, the BLOCKED reasons, the test rules, comment minimisation, the language policy and the coverage recheck for `ARCHITECTURE/` edits.
- `PROCESS/STATE.json`: the `HQ-0084` and `HQ-0071` entries. `PROCESS/RuntimeAcceptance.md`: RA-0035, RA-0050, RA-0056, RA-0058 and RA-0061.
- `PROCESS/tasks/T-0528-read-hugging-face-model-files.md`: criterion 2 and `## Result`; the ADR it landed.
- `ARCHITECTURE/decisions/ADR-0176-od31-model-level-reference-and-comparison.md`: decisions 3 to 6, and Boundaries.
- `ARCHITECTURE/decisions/ADR-0182-od14-model-executor-container.md`: decisions 2, 3, 5 and 7, and 8. `ARCHITECTURE/decisions/ADR-0189-od31-binding-from-run-incumbents.md`: decisions 1, 3 and 6, and Boundaries. `ARCHITECTURE/decisions/ADR-0155-*.md`: the entry's outcomes and decoding rules. `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`: the "Record format" section.
- `ARCHITECTURE/Requirements.md`: the "행 형식" paragraph and the OD-31 row. `ARCHITECTURE/OpenDecisionProposals.md`: the header's "기록 규칙" and section OD-31. `ARCHITECTURE/StandardScenarios.md`: the first paragraph of §검사 결과.
- Code: `hilclaw/new_run.py` and `hilclaw/s6_metric.py` (command-line form, `source=data_root_source.configured`), `hilclaw/model_forward_container.py` (`execute`, its outcomes, `keep_out`, `parent`), `hilclaw/model_run_binding.py`, `hilclaw/model_reference.py` (`compare`, `LogitComparison`), `hilclaw/model_forward_run.py` (`ForwardReport`), `hilclaw/model_build.py` (who gives `-ldl`).
- Tests: `tests/test_model_forward_container.py` (the stub `docker` client, `PROGRAM_FLAGS`, `TRAILING_FLAGS`), `tests/test_model_run_binding.py` (the joined path), `tests/test_model_reference.py`.
- Upstream, read with `gh api` and cited by commit: `huggingface/transformers` `src/transformers/models/llama/modeling_llama.py`, and the `from_pretrained` documentation for `local_files_only`, `trust_remote_code`, `use_safetensors` and the dtype argument.

## Acceptance Criteria

1. **ADR-0192**, in the "Record format" of ADR-0001, decides under DRIVER §9 what ADR-0176 Boundaries gave to the runtime side:
   - **The reference's configuration**: its dtype, its attention implementation and how it loads the files. It loads only from the named directory, offline, from safetensors, with no remote code. Weigh float64, which matches ADR-0176 decision 2 and costs about 8 bytes per parameter, against a narrower type, and say what the choice does to `rtol`, `atol` and RA-0035. If the dtype is left to the user, it has no default.
   - **`torch`.** `transformers` cannot run the model without it. State the reading that HQ-0071's and HQ-0084's allowance of the reference on the runtime machine covers its backend, and list that reading for the owner in the #5 notice. It stays out of `pyproject.toml`, the `dev` group and CI.
   - **The tokenizer**: which class reads the directory's files, whether special tokens such as a begin-of-text token are added, and why. The executor and the reference get the same ids, so the comparison does not depend on this.
   - **The reference's two outputs**: the teacher-forced logits on the executor's selected tokens (ADR-0176 decision 5), rows as the report holds them; and its own first N greedy tokens by the owner's rule on its own logits. Say whether `generate` or an explicit loop is used and why; the rule must be exactly the owner's, with no sampling, repetition penalty or stopping at an end token unless the executor does the same.
   - **The verdict**: `match` only when both hold (owner, HQ-0071). Compare with `model_reference.compare` and do not write a second predicate.
   - **What stays with the user**, with no default (HQ-0071, ADR-0176 decision 6): the prompt text, N, `rtol`, `atol`, the time limits (ADR-0182 decision 5), `flags` (ADR-0189 decision 6) and the program's flags (`hilclaw/model_build.py`).
   - **The record**: the answer goes to standard output only; no file of the data plane, CAS or the checkout is written (OD-31 ⑧, OD-8). Say so as the Boundaries of P1-9 do.
   - **Boundaries**: ⑧, ⑨, ⑩, OD-18's and OD-23's tool form, runs with N > 1 and fp16. It lists runtime acceptance items for `PROCESS/RuntimeAcceptance.md`, not HQs.
   - **The A-13 reading.** If the reading finds that an owner value is needed beyond these, return BLOCKED so the driver asks under §8; do not choose it.
2. **`hilclaw/model_hf_reference.py`**, with public documentation like its neighbours:
   - It imports `transformers` and `torch` only inside a function, so importing the module never needs them. Their absence is a named error that says which package is missing.
   - It returns NumPy arrays and token ids; nothing outside this module touches a `torch` object.
3. **`hilclaw/model_check.py`**: `python -m hilclaw.model_check <file>`, one argument, a JSON file decoded under the rules of `hilclaw/new_run.py`:
   - **Members**, all required unless stated: the model directory, the mapping from call site to run id, `flags`, the prompt text, N, `rtol`, `atol`, `build_timeout_s`, `run_timeout_s`, `program_flags`, `program_trailing_flags`. A `parent` for the build directory is optional, as in `execute`. An unknown or missing member is a named refusal.
   - **Order**, stopping at the first failure so a long step is not spent on a doomed call: the document; the optional packages; `model_files.read`; the tokenizer; the data root (`data_root_source.configured`, as `new_run`); `binding_from_runs`; `model_forward_container.execute` in the generation mode with `lm_head_rows` `"all"` and `keep_out` naming the model directory and the data root; the reference; the comparison.
   - **The answer** is one ASCII JSON line on standard output with a member `outcome`, as `new_run` does, and each kind has its own exit status, with only `match` at 0. `match` and `no_match` carry the prompt's and both sides' token ids, the decoded texts, the index of the first differing token, and the `LogitComparison` counts. Every failure of the earlier steps has its named outcome: refused document, missing package, each `ModelFileError` reason, each `RunBindingError` reason, a binding check that is not `ok`, container unavailable, build failed, run failed.
   - It runs a coder's kernel only through `model_forward_container` (ADR-0182 decision 7), starts no `claude`, and is registered as no tool.
4. **Tests**, in the two matching test files, under the skips of their models:
   - **Reference:** fake `transformers` and `torch` modules assert the loading arguments of criterion 1 and supply logits. Cover the tie rule, N = 1, an absent package, and a fake that returns a wrong shape.
   - **Joined happy path:** synthetic files as T-0528's tests write them, runs as `tests/test_model_run_binding.py` writes them, the stub `docker` client, and a fake reference whose logits are `model_reference.reference_logits` on the same weights. The result is `match` with exit 0, and nothing is added under the data root or the model directory.
   - **`no_match`, each way:** tokens equal and logits outside the tolerance; logits within the tolerance and a differing token; both.
   - **Error and negative:** each named outcome of criterion 3, including non-finite `rtol`, N not positive, an unknown call site, a run with no incumbent, and a prompt that tokenizes to nothing. A failure in an early step starts no container, which the stub's log shows.
   - Every public function is covered. Existing tests keep passing, and their assertions change only as D21 allows. Foreseen: `tests/test_standin_profile.py`, which pins who may name that module, if the new code names it; avoid it as `hilclaw/model_run_binding.py` did where possible. Each edit made is listed in the PR body.
5. **Records.** `Requirements.md` follows its "행 형식" (one link for the new ADR, open parts rewritten in place). `OpenDecisionProposals.md` follows its header's "기록 규칙" (one `채택분` line; the ④, ⑥ and ⑦ statuses rewritten in place, and ⑩ stays open). `StandardScenarios.md` §검사 결과 follows the rule in its first paragraph, and coverage is rechecked as CLAUDE.md requires. Restate no ADR content there and add no dated paragraph.
6. **Result** records: the language and the reason; the reference's configuration; any edited assertion; runtime acceptance items for the driver to add; the §9 notice on #5 with its 7-day window; and the exact command and an example document, which T-0530 uses.

## Out of Scope

- The instance documents and the owner's written steps (T-0530).
- Installing or adding `transformers`, `torch`, `tokenizers` or `safetensors` to `pyproject.toml`, the `dev` group or CI.
- Real weights, a real `claude`, a D25 test run or a Docker daemon (D16; RA-0056). The check stays the owner's.
- A scenario for this flow (OD-31 ⑩), a whole-model artifact (⑧), model-level performance (⑨), choosing among several runs of a key (OD-20, OD-7), fp16 (HQ-0083), and a nightly configuration (HQ-0076 (2)).

## Follow-ups

## Result
