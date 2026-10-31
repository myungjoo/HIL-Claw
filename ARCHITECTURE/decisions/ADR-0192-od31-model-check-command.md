# ADR-0192: The command line of the P2-15 check — the transformers reference at float64 and eager attention, loaded offline from safetensors, `torch` read as part of the allowance, the tokenizer of the directory with its special tokens, teacher-forced logits and an explicit greedy loop, a verdict that needs both, every value the user's and the answer on standard output only (part of OD-31 sub-questions 4 to 7)

## Status

- **Accepted on 2026-10-31.** It designs the entry half of what PLAN P2-15 needs (RA-0056) under DRIVER D26. ADR-0176 Boundaries left the reference's configuration to the runtime side, and HQ-0084 ④ makes it a driver task.
- **Two kinds of content.**
  - **Cited**, marked **owner** where it is an owner answer: HQ-0084 as [ADR-0191](ADR-0191-od31-hugging-face-model-files.md) records it, and HQ-0071 as [ADR-0176](ADR-0176-od31-model-level-reference-and-comparison.md) records it. The owner's answers are **not subject to the objection window** below. Statements of accepted records and of upstream code are cited with their source.
  - **This record's own**, every other sentence. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it**, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The search for other owner sentences.** Searched on 2026-10-31: the bodies of #4, #5, #7 and #8 and the 72 of their 316 bodies and comments whose text holds no "posted by driver" marker. Terms: transformers, torch, float64, 토크나이저, tokenizer, special token, begin of text, BOS, eager, attn_impl, 명령줄, command line. Found: float64 as the reference of the first case (#5 comments 5944117402, 5944412285, 6052377983), which ADR-0176 already reads for P2-14; PyTorch as a frontend format or a possible reference (the #5 body, B-5 and B-7), and a `claude` command line (6135246858), neither on this subject; the rest are simulators and a project name. **Conflicts: none.**
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `664ac30f`): HQ-0081 (S6), HQ-0082 (the guard hook), HQ-0083 (fp16; the command is bf16 only) and HQ-0085 (gates).
- **Not changed**: no schema file, member, version or validator of the data plane. No package is added anywhere. No model file was downloaded; no `claude` process, Docker daemon or token was used (D16). It builds on ADR-0176, [ADR-0182](ADR-0182-od14-model-executor-container.md), [ADR-0189](ADR-0189-od31-binding-from-run-incumbents.md), ADR-0191 and [ADR-0155](ADR-0155-od23-first-case-instance-start-command-line.md); none is edited. The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **Owner.** HQ-0084 ④ (a): "오너가 수동 실행할 명령줄을 드라이버 task로 만든다(드라이버 검증은 합성 파일)." ③ (a): transformers is an optional dependency of the runtime machine. HQ-0071: "P2-15 실제 가중치 run은 … 그에 더해 같은 프롬프트에서 처음 N개 greedy 토큰이 reference와 같아야 하며, 둘 다 만족해야 맞는다(N은 사용자 지정)."
- **Upstream** (cited): `huggingface/transformers` at commit `66f51e76efd8542232b8bdd40ade7d1edbaac46f`, the commit ADR-0191 read, under `src/transformers/`: `models/llama/modeling_llama.py` (`model`), `modeling_utils.py` (`utils`), `tokenization_utils_base.py` (`base`), `tokenization_utils_tokenizers.py` (`tok`), `generation/utils.py` (`gen`).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**. Notation as ADR-0166: S, G, V; N is G here.

### 1. The command

`python -m hilclaw.model_check <file>`: one JSON file decoded under ADR-0155 decision 3's rules. A person runs it. It is registered as no tool, starts no `claude`, and runs a coder's kernel only through `model_forward_container` (cited: ADR-0182 decision 7). The steps stop at the first failure, cheap before long: the document, the packages, `model_files.read`, the tokenizer, the data root, the parent, the binding, the executor at `lm_head_rows` `"all"` with `keep_out` naming the model directory and the data root, the report's tokens, the reference, the comparison. The `parent` step is `model_execute`'s own refusal, moved before the binding. The report's prompt must echo the prompt and its ids must lie below V, `bad_report` otherwise: a kernel shares the program's process (cited: ADR-0182 Boundaries), so a damaged run can say anything, and that is the executor's failure, told before the long load.

### 2. The reference's configuration

`LlamaForCausalLM.from_pretrained(directory, dtype=torch.float64, attn_implementation="eager", use_safetensors=True, local_files_only=True, trust_remote_code=False)`, then `eval()`.

- **The class named directly**, not an auto class, so nothing in the directory selects code; `model_files.read` has already required `model_type` `llama` (cited: ADR-0191 decision 7).
- **float64, fixed by this record; the user has no choice to make here.** `dtype` left out means `"auto"` (`utils` lines 3953-3961, 4106-4107), so a BF16 file would run the reference in bf16 and measure rounding against rounding. float64 costs 8 bytes per parameter, about 10 GB for the 1.2 × 10⁹ weights of ADR-0182 Context; float32 would cost half. It is taken because it is the dtype of ADR-0176 decision 2, and because all products and residuals then round far below anything else in the comparison.
- **What float64 does not give** (cited): `model` keeps part of the pass at binary32 whatever the dtype. RMSNorm converts its input to float32 before the square root and scale (lines 62-66), RoPE computes its angles, cosine and sine in float32 (lines 111-116), and eager attention takes its softmax in float32 (line 197). So this reference is not float64 throughout as ADR-0176 decision 2's is; the owner chose transformers as it is (HQ-0071), and this record neither patches it nor calls it float64-exact. **For `rtol` and `atol`**: the reference's own error is of the order of binary32 rounding (2⁻²⁴ relative per such step, more where a dot product cancels), against bf16's 2⁻⁹ per kernel output in the executor (cited: the derivation in `tests/test_model_reference.py`, `tolerance`). A tolerance near the first says nothing useful; the user's values stay the user's. **For RA-0035**: the machine now holds about 10 GB of float64 weights in the Python process after the executor ended, and the bf16 arrays are dropped before the load.
- **Eager, not `sdpa`.** Both compute the same attention. Eager's every line is in the file cited above, and it depends on no attention backend of the installed `torch`; `sdpa` would keep the softmax at float64, a gain the two float32 norms per layer make immaterial.
- **Offline, from safetensors, with no remote code**: the three arguments. `use_safetensors=True` raises rather than opening a pickle (`utils` line 695), and the check is ADR-0191's directory, which holds no pickle it reads.
- **A version that ignores `dtype`** would give a narrower reference silently. So logits of a dtype other than `torch.float64` are refused `wrong_dtype`, and no older argument name is tried.

### 3. `torch`

`transformers` cannot run this model without it (`model` imports it at the top). **Reading for the owner**: HQ-0071's and HQ-0084's allowance of the reference on the runtime machine covers its backend. `torch` stays out of `pyproject.toml`, the `dev` group and CI. It and `transformers` are imported only inside a call; `tokenizers` and `safetensors` come with `transformers`. An absent package is the named outcome `missing_package`, before anything long.

### 4. The tokenizer

`PreTrainedTokenizerFast.from_pretrained(directory, local_files_only=True, trust_remote_code=False)`. It reads the directory's `tokenizer.json` and needs no class the directory names; at the cited commit it is an alias of the backend (`tok` lines 1561-1562) and at earlier ones the class itself, so it runs no code by name. `AutoTokenizer` was weighed: it would let `tokenizer_config.json` choose. **Special tokens are added by the directory's rule** (`encode(text, add_special_tokens=True)`, the default, `base` line 2277): the model was trained with its begin-of-text token at the start, and a run without it would be an input nobody uses. No chat template is applied; the prompt is the user's text, and a text that spells a special token is read as that token. The executor and the reference get the same ids, so the comparison does not depend on any of this; the ids are in the answer for the user to see. A prompt that tokenizes to nothing is `empty_prompt`. Decoding keeps special tokens, so the text shows what the ids hold.

### 5. The reference's two outputs

- **Teacher-forced logits** (cited: ADR-0176 decision 5): one pass over the prompt and the executor's selected tokens but the last, `use_cache=False`, every row, as `model_reference.compare` reads them: S + N − 1 rows of V at `"all"`.
- **Its own first N greedy tokens** from the prompt alone: **an explicit loop**, one whole pass per token with no cache, the next token the first index of the largest value of the last row of its own logits, so the smallest token id on ties (**owner**, HQ-0071). `generate` is not used: it takes sampling and stopping from the directory's generation configuration (`gen` lines 544-571, 925, 2093), so exactness would rest on overriding all of them, and its tie is `torch`'s. There is no sampling, repetition penalty or stop at an end token; the forward program stops at none either (cited: ADR-0176 decision 5). A NaN in the row is `nan_row`, as a NaN stops the executor (cited: the same decision). The cost is N whole passes.

### 6. The verdict and the user's values

- **`match` only when both hold** (**owner**, HQ-0071): `model_reference.compare` passes and the executor's N tokens equal the reference's. There is no second predicate.
- **The user's, with no default** (HQ-0071; ADR-0176 decision 6): the prompt text, N, `rtol`, `atol`, `build_timeout_s` and `run_timeout_s` (ADR-0182 decision 5), `flags` (ADR-0189 decision 6), `program_flags` and `program_trailing_flags` (`hilclaw/model_build.py`), with the model directory and the run of each of the fifteen call sites. A call site with no run is refused in the document, not after the long read.

### 7. The record

The answer goes to standard output only: no file of the data plane, CAS or the checkout is written (OD-31 ⑧, OD-8). The model directory and the runs are only read; the one directory made is the executor's build directory, which it removes (cited: ADR-0182 decision 8). This is no record of a model-level run.

### 8. The answer

One ASCII JSON line with `outcome`, as ADR-0155 decision 5 does. Each kind has its own exit status and only `match` is 0; the table is the docstring of `hilclaw/model_check.py`. A file refusal and a binding refusal are one kind each (`model_file`, `run_binding`) whose `reason` member is the constant of `ModelFileError` or `RunBindingError`: about sixty statuses would tell a script nothing the member does not.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | float32 or bf16 for the reference | Decision 2: float32 saves half the memory and departs from ADR-0176 decision 2; RA-0035 can show whether the saving is needed. bf16 measures rounding against rounding. |
| 2 | The user names the dtype | A value with no use for anyone but a machine short of memory; it can be added if RA-0035 shows the need. |

## Consequences

- **A-13 reading**: no schema file, member, version or validator of the data plane changes and nothing is written to it. No new dependency in CI or the driver; the reference's packages are the owner's allowance of HQ-0071 and HQ-0084 ③. No owner value beyond those the task names was needed.
- **Answers**: of sub-question 4, the executor's entry for the owner's manual run only (⑩ stays open); of 5, the tokenizer's reading; of 6, the P2-15 comparison and its configuration; of 7, the tokenizer needs nothing beyond what `transformers` brings.
- **Runtime acceptance items**, for `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22), to be seen with RA-0056:
  1. With the `transformers` and `torch` the owner installs, the loading call of decision 2 is accepted for the directory obtained and its logits are `torch.float64` (a version that ignores `dtype` gives `wrong_dtype`).
  2. `PreTrainedTokenizerFast` reads that directory's tokenizer, and the prompt's ids in the answer start as the file's rule says (the begin-of-text token expected).
  3. The machine holds the reference's float64 weights (about 10 GB in the Python process, after the executor ended) and N + 1 whole passes finish in a time the owner accepts; this adds to RA-0035.
- **Readings for the owner to check**, listed in the #5 notice: `torch` as part of the allowance (decision 3); float64 fixed, with upstream's float32 steps left as they are, so the reference is not float64-exact (decision 2); eager attention (decision 2); special tokens added and no chat template (decision 4); a NaN in the reference's row refused (decision 5).
- **Less exact, not edited** (search of `ARCHITECTURE/decisions/` for "P2-15 run", "reference's configuration", and "the entry"; not claimed complete): ADR-0176 Boundaries and decision 5 ("named, not built here"), ADR-0189 Boundaries and ADR-0191 Boundaries ("the entry", "the tokenizer"): decisions 1 to 6 here answer them.
- **UsageCases and StandardScenarios** (S0 re-checked): no use case step changes; the command adds no scenario (⑩). Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **The artifact** (⑧), **model-level performance** (⑨), **whether this flow is a scenario and in which tier** (⑩).
- **OD-18's and OD-23's tool form**: the command is no tool, and exposing the executor to an agent stays open.
- **Runs with N > 1 per round** and choosing among runs of a key (cited: ADR-0189 Boundaries; OD-20, OD-7).
- **fp16** (HQ-0083), a nightly configuration (HQ-0076 (2)), the instance documents and the owner's written steps (T-0530).

## References

- Owner: HQ-0084, HQ-0071 in `PROCESS/STATE.json`; [Requirements](../Requirements.md) C-6, FR-9, FR-10, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-31; [RuntimeAcceptance](../../PROCESS/RuntimeAcceptance.md) RA-0035, RA-0050, RA-0056, RA-0058, RA-0061.
- Upstream, read through `gh api`, at the commit of Context.
- Code: `hilclaw/model_check.py`, `hilclaw/model_hf_reference.py`; read: `hilclaw/new_run.py`, `hilclaw/model_forward_container.py`, `hilclaw/model_run_binding.py`, `hilclaw/model_reference.py`, `hilclaw/model_files.py`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §6 D26, §8, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-15.
