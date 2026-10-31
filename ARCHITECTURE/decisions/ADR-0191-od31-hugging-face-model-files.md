# ADR-0191: Reading a Hugging Face Llama model directory — the owner's answer to HQ-0084 recorded, `config.json` and safetensors files under a path the caller names and outside the data plane, a reader on the standard library and NumPy, the tensor mapping, the inverse of the converter's `permute` on Q and K, the tied head, bf16 only, and the constants from the file with no default (part of OD-31 sub-questions 5 and 7)

## Status

- **Accepted on 2026-10-31.** It designs the weights half of what PLAN P2-15 needs (RA-0056) under DRIVER D26.
- **Two kinds of content.**
  - **Cited**, marked **owner** where it is an owner answer: the `decision` of HQ-0084, and of HQ-0070 and HQ-0071 as [ADR-0176](ADR-0176-od31-model-level-reference-and-comparison.md) records them. The owner's answers are **not subject to the objection window** below. Statements of accepted records and of upstream code are cited with their source.
  - **This record's own**, every other sentence: the reader, the mapping and its derivation, the refusals, the reading of the head, the forms of the constants and every weighing. That part is accepted under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it**, is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **The owner sentence.** **O1** — HQ-0084, `resolvedAt` 2026-10-31T05:26:27Z (**owner**, in chat), quoted: "① (a) ② (a) ③ (a) ④ (a) - 오너(채팅, 2026-10-30): ① Hugging Face의 safetensors와 tokenizer 파일, base 변형(저장소 이름은 오너가 지정하지 않았다 — 파일은 ②의 경로로 받는다). ② 런타임 머신의 사용자 경로를 입력으로 받고 데이터 plane에 넣지 않는다. ③ transformers와 함께 런타임 머신의 선택 의존성으로 두고 드라이버·CI에는 넣지 않는다. ④ 오너가 수동 실행할 명령줄을 드라이버 task로 만든다(드라이버 검증은 합성 파일)."
- **The search for other owner sentences.** Searched on 2026-10-31: the bodies of #4, #5, #7 and #8 and the 72 of their 315 bodies and comments whose text holds no "posted by driver" marker. Terms: safetensors, tokenizer, 토크나이저, Hugging Face, permute, tie_word, tied, lm_head, 가중치, weight file, checkpoint, config.json. Found: "lm_head … excluded from the first runs" in the B-4 answer (#5 comment 5944412285), a statement on first-run shapes that the C-6 revision and ADR-0152 already read; every other hit is a round checkpoint or `hilclaw.config.json`. **Conflicts: none.**
- **Open HQs checked and not crossed** (`PROCESS/STATE.json` on `main` `6a6bdf19`): HQ-0081 (S6), HQ-0082 (the guard hook), HQ-0083 (fp16; this record reads bf16 only and invents no conversion) and HQ-0085 (gates).
- **Not changed**: no schema file, member, version or validator of the data plane. No package is added anywhere. No model file was downloaded; no `claude` process, Docker daemon or token was used (D16).
- It builds on ADR-0161 (decisions 4 to 6, Boundaries), ADR-0166 (decisions 2 to 5), ADR-0176 and [ADR-0001](ADR-0001-od4-key-schema.md) ("Record format"); none of them is edited.

## Context

- **What is asked for.** `hilclaw.model_forward_execute.execute` takes the dimensions, `eps`, the RoPE constants and the weights from its caller; ADR-0166 decision 4 leaves making them to "a test or a later loader, sub-question 5", and forming the joined QKV weight to it as well (ADR-0161 decision 6).
- **The upstream code** (cited): `huggingface/transformers` at commit `66f51e76efd8542232b8bdd40ade7d1edbaac46f` (`T`); for the older form, tag `v4.46.0`, commit `c2820c94916e34baf4486accae74760972183a2f` (`O`). `T` `src/transformers/models/llama/convert_llama_weights_to_hf.py` (`convert`), `configuration_llama.py` (`config`), `modeling_llama.py` (`model`), `src/transformers/modeling_rope_utils.py` (`rope`). `convert` is identical at ADR-0161's commit `f4410762`.
- **The format** (cited): `huggingface/safetensors` at commit `e246a2560645b7525f5775669ed816eb57c5bcc8`, `README.md` lines 76-77 (an unsigned little-endian 64-bit header length, then the JSON header), 81 (`data_offsets` relative to the byte buffer), 87 (duplicate keys disallowed), 99 (the buffer entirely indexed, no holes), 172 and `safetensors/src/tensor.rs` line 10 (the 100 000 000-byte header limit), line 848 (`BF16`).

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**. Notation as ADR-0166: D, F, V, N, H, H_kv, d.

### 1. The directory

- **Owner (O1 ②)**: the input is a path on the runtime machine; nothing of it enters the data plane. **The caller names a directory.** Read from it: `config.json` and either `model.safetensors` or `model.safetensors.index.json` with its shards. Both weight forms at once are refused: upstream prefers one by its own rule and a stale file beside the other is more likely than a choice. The directory is never copied, stored or recorded, here or in CAS. A symbolic link is followed, since a Hugging Face cache snapshot holds its files that way, so "outside the directory" is decided on the names in the index (decision 8), not on resolved paths.

### 2. The reader

- **Written on the standard library and NumPy** (Python, the language of `hilclaw/model_reference.py`, whose input this is). The format is a length, a JSON header and a little-endian buffer (Context); the code path then runs in CI, which must not gain the package (**owner**, O1 ③). The `safetensors` package would add a dependency for about 100 lines; it is not imported, lazily or otherwise, and `pyproject.toml`, the `dev` group and CI do not change. No pickle file is ever opened.

### 3. The tensor mapping

| Hugging Face tensor (`[out, in]` for a linear weight) | `Weights` field | Change |
|---|---|---|
| `model.embed_tokens.weight` `[V, D]` | `embedding` (V, D) | none (a table, not a linear weight) |
| `model.layers.ℓ.input_layernorm.weight` `[D]` | `attention_norm[ℓ]` | none |
| `model.layers.ℓ.self_attn.q_proj.weight` `[H·d, D]` | `qkv[ℓ]` (D, W), columns [0, H·d) | decision 4, then transpose |
| `model.layers.ℓ.self_attn.k_proj.weight` `[H_kv·d, D]` | `qkv[ℓ]`, columns [H·d, H·d + H_kv·d) | decision 4, then transpose |
| `model.layers.ℓ.self_attn.v_proj.weight` `[H_kv·d, D]` | `qkv[ℓ]`, columns [H·d + H_kv·d, W) | transpose |
| `model.layers.ℓ.self_attn.o_proj.weight` `[D, H·d]` | `o[ℓ]` (H·d, D) | transpose |
| `model.layers.ℓ.post_attention_layernorm.weight` `[D]` | `ffn_norm[ℓ]` | none |
| `model.layers.ℓ.mlp.gate_proj.weight` `[F, D]` | `gate[ℓ]` (D, F) | transpose |
| `model.layers.ℓ.mlp.up_proj.weight` `[F, D]` | `up[ℓ]` (D, F) | transpose |
| `model.layers.ℓ.mlp.down_proj.weight` `[D, F]` | `down[ℓ]` (F, D) | transpose |
| `model.norm.weight` `[D]` | `norm` | none |
| `lm_head.weight` `[V, D]`, if stored | `lm_head` (D, V) | decision 5, transpose |

- The names are `convert` lines 247-268 and `model` lines 158-160, 219-229, 281-282, 346, 420. PyTorch computes `x @ W.T` with W `[out, in]`; the executor computes `a @ b` with b `[in, out]` (ADR-0156 decision 2), so a transpose gives the same product. The column order Q, K, V is ADR-0166 decision 4's. Each array is a new C-contiguous native-order `uint16` array.
- **Any other tensor is refused.** A bias or a buffer in the file is something the pass would not compute; a silent skip would give wrong logits. If a real file holds one the refusal names it, and the item of Consequences covers that.

### 4. The Q and K order

**Conclusion.** The inverse of the converter's `permute` is applied to the stored Q and K, on the output axis (the first), with H for Q and H_kv for K, each before the transpose and the join; V is not touched.

**Derivation.**

1. **The arrangement.** `convert` lines 220-221: `w.view(n_heads, dim1 // n_heads // 2, 2, dim2).transpose(1, 2).reshape(dim1, dim2)`. With `n_heads` = h and `dim1` = h·d, row j·d + 2p + r of Meta's weight (r ∈ {0, 1}, p < d/2) becomes row j·d + r·d/2 + p. Lines 247-253: Q with `n_heads=n_heads`, K with `n_heads=num_key_value_heads, dim1=key_value_dim`, V unpermuted.
2. **The rotation of the stored order.** `model` lines 243-244 view each projection as heads of d. Lines 112-114 make `cos` and `sin` from `cat((freqs, freqs))`, so elements p and p + d/2 share frequency p. Lines 119-123 and 147: element p gets x[p]·cos − x[p + d/2]·sin, element p + d/2 gets x[p + d/2]·cos + x[p]·sin.
3. **The executor's rotation.** With x₀ = x[p] and x₁ = x[p + d/2], step 2 is ADR-0161 decision 7's y₀ = x₀·c − x₁·s, y₁ = x₀·s + x₁·c, at pair p and table columns (2p, 2p + 1). So a head of the stored order rotates exactly as the head rearranged with (p, p + d/2) at (2p, 2p + 1) does under the pair rule. That rearrangement is the inverse of step 1: `reshape(h, 2, d/2, D).transpose(0, 2, 1, 3).reshape(h·d, D)` on the first axis.
4. **The scores agree.** Q and K use the same rearrangement of a head, so the dot products of SDPA are unchanged: a permutation applied to both vectors keeps q·k. V and O are not rearranged and are not paired, so attention's output is unchanged. `tests/test_model_files.py` shows this numerically and shows that the pair rule on tensors left as stored gives other scores at Q and K of different positions.

**Can a file be stored the other way?** The file carries no mark of its arrangement. The tensor names are Hugging Face's, and `model` defines what they mean: whatever made the file, transformers rotates them by the half split of step 2, and that is the P2-15 reference (**owner**, HQ-0071). So this reader's reading is the reference's, independent of how the file was made. **What follows if a file was written with Meta's adjacent order under these names** (a broken conversion): reader and reference still agree, so the logit comparison passes, and both produce a model whose attention is wrong. Only the output's sense would show it. That is a runtime acceptance item (Consequences), not a fact this record can settle without the file.

### 5. The tied head

- **Cited**: `model` line 411 ties `lm_head.weight` to `model.embed_tokens.weight` under `tie_word_embeddings` and line 420 makes the head `[V, D]`; `convert` line 400 sets the flag true for Llama 3.2. `tie_word_embeddings` is required, since the file writes it (below).

| `tie_word_embeddings` | `lm_head.weight` | `lm_head` |
|---|---|---|
| true | absent | the transpose of `embedding` |
| true | present, bit-equal to the embedding | its transpose (the same array) |
| true | present, different | refused `tied_head_differs`: transformers would discard the stored one, and which was meant is not known |
| false | present | its transpose |
| false | absent | refused `absent_head`: transformers would start from random values |

### 6. The element type

- **`BF16` tensors are handed over as bit patterns**, with byte order the only change (ADR-0166 decision 5; HQ-0065 (3) through ADR-0154). **Any other stored dtype is refused** `stored_dtype`, naming the tensor. `torch_dtype` and `dtype` of `config.json` are not read: the header states what is stored. Rounding another type to bf16 would be a rule no source gives.

### 7. The constants

| Result | `config.json` member | Forms |
|---|---|---|
| `hidden`, `intermediate`, `vocabulary`, `layers`, `heads`, `kv_heads` | `hidden_size`, `intermediate_size`, `vocab_size`, `num_hidden_layers`, `num_attention_heads`, `num_key_value_heads` | one |
| `head_dim` | `head_dim` | absent or null: `hidden_size // num_attention_heads` when it divides (`config` lines 87-88; `O` `configuration_llama.py` line 193) |
| `eps` | `rms_norm_eps` | one |
| `theta` | `rope_parameters.rope_theta`, else top-level `rope_theta` | `rope` lines 784, 793, 825; `O` keeps it top-level (`configuration_llama.py` line 188) |
| `scale_factor`, `low_freq_factor`, `high_freq_factor` | `factor`, `low_freq_factor`, `high_freq_factor` of the block | the block is `rope_parameters` (`T`) or `rope_scaling` (`O` `modeling_rope_utils.py` lines 332-334; `T` still takes it, `rope` lines 775-776) |
| `old_context_len` | `original_max_position_embeddings`, in the block or top-level | both allowed if equal; if they differ refused, since `T` prefers the top-level one (`rope` lines 836-841) and `O` reads the block (line 335) |

- **The block's `rope_type`, or the older `type`** (`rope` line 824; `O` lines 195-197 of `configuration_llama.py`), must be `llama3`: `rope` lines 635-661 are ADR-0161 decision 4's rule with `factor` as s, and `rope_table` has no other. Other types and a `partial_rotary_factor` other than 1 are refused `unsupported_model`. Both blocks at once are refused `two_rope_forms`, since `T` takes `rope_scaling` over `rope_parameters` and nothing older writes both.
- **A missing member is refused** `missing_member`, by name. In particular `original_max_position_embeddings` absent is refused, though `T` falls back on `max_position_embeddings` (`rope` line 842), since `O` does not and the value would differ silently. `num_key_value_heads` absent is refused, though `config` lines 89-90 would use the head count, for a Llama 3.2 file writes it and a silent multi-head reading is a different model; so is `tie_word_embeddings`.
- **No Llama value is in the code as a default** (HQ-0070; ADR-0176 decision 6). HQ-0070's 32 is expected from the file: `convert` lines 377-383 write it; nothing supplies it here. Values are refused by `check_dimensions`, `rmsnorm_eps` and `constant_refusals` as those functions refuse them, and an odd `head_dim` as `bad_dimensions`.
- **Values stated against the pass are refused**: `model_type` other than `llama`, `attention_bias` or `mlp_bias` true, `hidden_act` other than `silu` (`model` lines 158-161, 219-229). Absent, these are `config`'s defaults (lines 70, 81, 83), which are what the pass computes, and a bias tensor would be refused by decision 3.

### 8. The refusals and the module

- **`hilclaw/model_files.py`**: `read(directory)` returns `ModelFiles(dimensions, eps, rope, weights)`; `ModelFileError` carries `reason`, one of the module's constants. It writes nothing, starts nothing and is registered as no tool.
- **Before any tensor array is made**, for every file: the header length (`header_length` above the format's 100 000 000 bytes, `truncated` beyond the file); member names given twice (`duplicate_member`, also in `config.json` and the index, against the format's rule, Context); a malformed header; a range that leaves the data section or is reversed (`offset_outside`, which also names a file cut inside its data); `range_overlap`; `range_uncovered` (a hole or trailing bytes, Context); a shape whose byte count is not its range (`shape_bytes`); a tensor missing, extra or of a wrong shape, checked against `config.json`. A layer count larger than the tensors could give is refused before names are listed, so a file's number cannot make the reader loop.
- **The index**: `weight_map` must assign each tensor a plain file name in the directory, with no separator, drive mark or `..` (`shard_path`); every shard must hold exactly what the index gives it (`shard_index`).

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The `safetensors` package, lazily imported | Then CI could not run the code path (O1 ③), and the format needs no library. |
| 2 | `numpy.memmap` | A mapped array is not the new native array the interface gives and needs care on big-endian machines; the arrays are copied by the executor's input encoding anyway. |
| 1 | Prefer one weight form when both exist | A choice among files that may disagree; the refusal is one line to fix. |
| 1 | Refuse a resolved path outside the directory | Would refuse every Hugging Face cache snapshot, whose files are links to `blobs/`. |
| 3 | Skip unknown tensors | A bias would be lost silently. |
| 4 | Change the executor to half-split pairs | Against ADR-0161 decision 5 and every landed kernel; the file is what moves. |
| 4 | Leave Q and K as stored | Wrong logits at every position while every shape check passes. |
| 4 | A flag for the file's arrangement | Nothing in a directory could set it (decision 4). |
| 5 | Use the embedding silently when a tied head differs | Agrees with transformers, but hides a file that disagrees with itself. |
| 7 | Upstream's defaults for missing members | Values no file stated; the owner gave none (HQ-0070). |

## Consequences

- **A-13 reading**: no schema file, member, version or validator of the data plane changes and nothing is written to it; no new dependency in CI or the driver.
- **Answers**: of sub-question 5, the file form, the source's format, the base variant and the storage (O1 ① ②), and the conversion of the weights; of sub-question 7, that the weights need no package.
- **Runtime acceptance items**, for `PROCESS/RuntimeAcceptance.md` (DRIVER §8, D22), to be seen with RA-0056:
  1. `hilclaw.model_files.read` accepts the directory the owner obtains: its tensor names and shapes are those of decision 3, with no extra tensor, and its `config.json` gives the members of decision 7 with `rope_type` `llama3` and `factor` 32.
  2. Every tensor of that file is stored as `BF16`; another stored dtype is refused and needs an owner answer on the conversion (decision 6).
  3. That file's Q and K are in the arrangement of decision 4: the logit comparison against transformers shows only that reader and reference agree, so the owner also sees that the generated text makes sense.
- **Readings for the owner to check**, listed in the #5 notice: a stored head that differs from a tied embedding is refused rather than dropped (decision 5); any other tensor is refused (decision 3); the two absent members refused against upstream's fallbacks (decision 7); both weight forms at once refused (decision 1).
- **Less exact, not edited** (search of `ARCHITECTURE/decisions/` for "sub-question 5", "joined QKV" and "tied"; not claimed complete): ADR-0161 decision 6 and Boundaries (the arrangement and the join), ADR-0166 decisions 4 and 5 and Boundaries (the file form, the conversion, tying, the pairing), ADR-0176 Boundaries (the packages for reading the weights): decisions 3 to 5 here answer them. HQ-0084's tokenizer half stays with them.
- **UsageCases and StandardScenarios** (S0 re-checked): no use case step changes. S0 step 2's known weakness is about `model_ref` and OD-9, the frontend IR, which this record does not decide. Verdicts unchanged, no gap.

## Boundaries (not decided here)

- **The tokenizer, the `transformers` reference and the entry** (O1 ① ③ ④; T-0529), and the owner's steps (T-0530).
- **The artifact** (sub-question 8), **model-level performance** (9), **the scenario** (10), **fp16** (HQ-0083), **a record of a model-level run** (with 8 and OD-8).
- **A Meta-format checkpoint** (not chosen, O1 ①), quantised files, and OD-9.
- **Memory**: `read` holds the arrays in memory and doubles a linear weight during its copy; whether the machine fits a generation stays RA-0035.

## References

- Owner: HQ-0084, HQ-0070, HQ-0071 in `PROCESS/STATE.json`; [Requirements](../Requirements.md) C-6, OD-31; [OpenDecisionProposals](../OpenDecisionProposals.md) § OD-31 (sub-questions 5 and 7); [RuntimeAcceptance](../../PROCESS/RuntimeAcceptance.md) RA-0035, RA-0050, RA-0056.
- Records: ADR-0001, [ADR-0154](ADR-0154-od31-owner-answers-heads-bf16-oracle.md), [ADR-0156](ADR-0156-od31-bf16-gemm-contract.md), [ADR-0161](ADR-0161-od31-bf16-rope-contract.md), [ADR-0166](ADR-0166-od31-bf16-forward-pass.md), ADR-0176.
- Upstream, read through `gh api`, with the commits of Context.
- Code read: `hilclaw/model_forward_check.py`, `hilclaw/model_binding.py`, `hilclaw/rope_table.py`, `hilclaw/model_reference.py`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §6 D26, §8, §9; [PROCESS/PLAN.md](../../PROCESS/PLAN.md) P2-15.
