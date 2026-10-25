---
id: T-0472
title: Add hilclaw/model_forward.c, the bf16 forward-pass model program with its input form, library table, six entry points, every buffer and per-layer caches, the prefill pass and the report; generations with G = 1 only (ADR-0166 code slice 2)
phase: P1
status: TODO
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0471]
touchesFiles: [hilclaw/model_forward.c, tests/test_model_forward.py]
estimatedSize: {loc: 520, files: 1}
hq: []
---
## Why

**State on `main` `da43429b`.** ADR-0166 (T-0470, `d25a61e4`) designs the bf16 forward pass and generation of the model executor on `cpu_standin` (ADR-0153 code slice 2; PLAN P2-13, which P2-14 needs). Its Consequences (lines 167-173) list six code slices with fixed cut points. T-0471 is slice 1 (the whole-generation check, Python; this task does not use it).

**This task is slice 2: "The program, prefill only: a new C source `hilclaw/model_forward.c` — command line, input reading and its form checks, the library table and the six entry points, every buffer of decision 2 including the per-layer caches of decision 4 (the prefill's `sdpa` call needs them), the prefill pass of decision 3 and the report; it runs generations with G = 1 and refuses an input with G > 1 as an input-file error. Tested with hand-written fixtures and an input written by the test."**
- `hilclaw/model_program.c` (ADR-0153 slice 1, ADR-0157) stays the GEMM-list program and is not edited (ADR-0166 decision 1).
- **The binary form of the input, library table and report is this task's** (ADR-0166 decision 4 last bullet, decision 7, Boundaries line 195). Criterion 3 proposes one; the executor may change details for a stated reason, but must keep everything ADR-0166 fixes, and must state the final form completely in the program's header comment — T-0473 (slices 3 and 4) reads that header comment as the authority.

**Batch (DRIVER §6 "task 단위" ④).** T-0471, T-0472, T-0473 were created together; this task lists T-0471 in `dependsOn` by that rule only. T-0473 extends this program to decode passes and writes the host-side encoder against this task's header comment.

**PLAN order and D18.** P2-13 is a checklist item and P2-14 needs it; the D18 rule does not apply. The round-loop items and P2-5 are held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, OD-3).

**HQ-0071 (open, owner)** — token selection, model-level comparison, reference: this program has no generation mode, selection rule, reference or tolerance (ADR-0166 decision 7). **HQ-0070** — RoPE scale factor: the program receives the RoPE table as an input and computes no cosine. **HQ-0069** (runtime acceptance (lxvii), `dlopen` in the isolated environment): not crossed; the test builds and loads on the local POSIX system with clang, as `tests/test_model_program.py` does.

**D16.** The program is built with the local `clang` and run as a local process with fixture kernels the test writes. Nothing starts `claude`, downloads a model file, or needs a board or an API key. Where `clang` or POSIX is absent, the tests skip locally and fail on CI, as `tests/test_model_program.py` does.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (600 LOC, 10 files, tests excluded), the naming and the test rules.
  - For this task: branch `claude/T-0472-<slug>`; commit trailer `Task: T-0472`; code mode, so a Draft PR whose body ends with `Task: T-0472`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화" (the file boilerplate comment of a C source may be long), "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`: the Decision section whole (lines 29-143) — notation (line 33), decision 1 (program, dtype, order, entry points), decision 2 (buffers, sharing, the `0x7FC0` fill at allocation), decision 3 (operands of each call, the copies, no cast), decision 4 (cache, inputs), decision 5 (embedding row copy), decision 7 (report); Consequences code slices (lines 167-173); Boundaries (lines 189-198).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 "Loading" and "The call" (lines 45-46), decision 4 (lines 48-56).
- Contract prototypes (byte for byte): `PROTOTYPE` in `hilclaw/gemm_bf16_contract.py` (line 56), `rmsnorm_bf16_contract.py` (line 60), `elementwise_add_bf16_contract.py` (line 59), `swiglu_bf16_contract.py` (line 64), `rope_bf16_contract.py` (line 69), `sdpa_kv_cache_bf16_contract.py` (line 70). Read each module's docstring for the operand layouts and the caller's guarantees.
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`: decision 4 (lines 52-59, the cache operand and what the kernel writes) and decision 15 (call site table).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`: decision 6 (the `freqs_cis` operand, row i = position P + i).
- `hilclaw/model_program.c`: the whole file (314 lines). It is the model for the header comment, the status codes, `fail`, the library loading with `dlopen(RTLD_NOW | RTLD_LOCAL)`/`dlsym`, the reading and form checks of a binary input, the size checks, pointing descriptor 1 at standard error, and the end mark.
- `hilclaw/model_binding.py`: the call-site tuples (lines 146-180), `gemm_shape`, `rmsnorm_shape`, `elementwise_add_shape`, `swiglu_shape`, `rope_shape`, `sdpa_shape`, for the shapes of each call.
- `tests/test_model_program.py`: lines 1-210 (the session fixture `built`, kernel templates, `start`, `assert_failed`) as the model for the tests.
- `.github/workflows/ci.yml` lines 70-90: the C gate compiles every tracked `*.c` alone with `clang -std=c99 -Wall -Wextra -Wpedantic -Werror -O2 -c`.

## Acceptance Criteria

1. **The program `hilclaw/model_forward.c`**, in C because it loads C kernels and runs in one process with them (ADR-0153 decision 2; one line in the commit body). It:
   - defines `_POSIX_C_SOURCE 200809L`; needs the C library and POSIX.1-2008 only (`<dlfcn.h>` included); does no floating-point arithmetic of its own except passing `eps` and the RoPE table through (state this);
   - declares the six prototypes as function-pointer types matching the contracts' `PROTOTYPE` text, and finds each entry point with `dlsym` by its symbol `hilclaw_gemm_bf16`, `hilclaw_rmsnorm_bf16`, `hilclaw_elementwise_add_bf16`, `hilclaw_swiglu_bf16`, `hilclaw_rope_bf16`, `hilclaw_sdpa_kv_cache_bf16` (ADR-0166 decision 1);
   - defines no identifier with external linkage other than `main`;
   - reads no clock, no environment variable and no standard input;
   - compiles alone under the CI C gate command.
2. **Command line**: `<input file> <library> [<library> ...]`, as `model_program.c`. Library i (0-based) is opened with `dlopen(path, RTLD_NOW | RTLD_LOCAL)` before the input file is read.
3. **Input file** (proposed form; host byte order, every integer `uint64_t`, every bf16 element a `uint16_t` pattern, every `float` binary32):
   - the header: D, F, V, N, H, H_kv, d, S, G, and `lm_head_rows` (0 = `"all"`, 1 = `"last"`);
   - `eps`: one `float`;
   - the **library table**: for each of the fifteen call sites in the order `qkv`, `o`, `gate`, `up`, `down`, `lm_head`, `attention_norm`, `ffn_norm`, `norm`, `attention_residual`, `ffn_residual`, `ffn_activation`, `rope_q`, `rope_k`, `sdpa` (the order of `model_binding`'s call-site tuples), G library indices, one per pass in pass order (pass 0 is the prefill). This per-pass encoding is a form of ADR-0166 decision 1's "for each call site and each distinct shape of the generation, the index of its library": the host side writes the same index for passes whose shape is the same;
   - the RoPE table: (S + G − 1)·d `float`s, row-major `[positions, d]`;
   - the token ids: S + G ids, the prompt then the given tokens;
   - the weights, each a bf16 array in its operand layout and the shapes of ADR-0166 decision 4: `embedding` (V·D), then for each layer ℓ = 0 … N − 1: `w_attention_norm` (D), `w_qkv` (D·W, columns Q, K, V ranges, head by head), `w_o` (H·d·D), `w_ffn_norm` (D), `w_gate` (D·F), `w_up` (D·F), `w_down` (F·D); then `w_norm` (D) and `w_lm_head` (D·V).
   The file ends exactly after the last weight. The executor may reorder or regroup these parts for a stated reason; the header comment states the final form.
4. **Form checks before any call** (status 5, input file): a short file or trailing bytes; any dimension, S or G zero; H not a multiple of H_kv; d odd (the RoPE contract needs an even d); `lm_head_rows` not 0 or 1; a library index not below the number of libraries; a token id not below V; **G > 1** ("decode passes are not supported by this build of the program" or similar — slice 3 lifts it); `eps` not finite or not above 0. A size that does not fit in `size_t` (any buffer of ADR-0166 decision 2, any weight, the cache, (S + G − 1)·d) is status 3, found before allocation; a failed allocation is status 3. An entry point that a library bound in the table lacks is status 6, naming the library index and the symbol, found before the first call. Status meanings follow `model_program.c` (0, 2, 3, 4, 5, 6).
5. **Buffers** exactly as ADR-0166 decision 2: allocated once, before the prefill, activation buffers sized for T = S and shared by all layers; `logits` sized S·V for `"all"` and V for `"last"`; per layer two cache buffers of C = S + G − 1 rows of H_kv·d elements; **every activation and cache element set to `0x7FC0` at allocation and not again**. Every operand of one call is a distinct, non-overlapping array.
6. **The prefill pass** (T = S, P = 0) exactly as ADR-0166 decision 3 rows 1-16: the embedding row copy (D patterns per row, no arithmetic); per layer, `attention_norm`, `qkv`, the three range copies (Q columns [0, H·d), K [H·d, H·d + H_kv·d), V [H·d + H_kv·d, W)), `rope_q` before `rope_k` with `freqs_cis` = the table's address advanced by P·d, `sdpa` (m = T, l = P + T) with the layer's two cache buffers from their starts, `o`, `attention_residual` (`a` = `x`, `b` = `o_out`, `c` = `h`), `ffn_norm`, `gate` then `up`, `ffn_activation`, `down`, `ffn_residual` (`a` = `h`, `b` = `down_out`, `c` = `x`); after layer N − 1, `norm` then `lm_head` (`"all"`: (T, D, V) with `a` = `normed`; `"last"`: (1, D, V) with `a` = row T − 1 of `normed`). Each call goes to the entry point of the library the table names for that call site at pass 0. No cast anywhere.
7. **Report**: the S + G token ids as read (`uint64_t`), then the requested logits rows of the pass as bf16 patterns (S rows for `"all"`, one row for `"last"`), then the end mark `end\n`. Descriptor 1 is pointed at standard error before the first library is loaded; the report goes to the original standard output; status 0 only after the end mark. Write the code so that slice 3 adds the decode passes without restructuring (for example a function for one pass taking T and P), but do not implement decode passes.
8. **Header comment** in the form of `model_program.c`: the purpose (ADR-0166, the bf16 forward pass; prefill only in this slice), the command line, the input file form completely, the form checks and size checks, the buffers and the `0x7FC0` fill, the order of calls, the report and its length, the exit statuses. It points to ADR-0166 for the rules instead of restating them, and does not claim a generation mode.
9. **Size**: at most 600 changed lines outside tests, at most 10 files; expected one file. If it would go over, shorten the header comment, not the behaviour, or propose a split in Follow-ups (DRIVER §5).
10. **Tests: new file `tests/test_model_forward.py`** (D12, DRIVER §5), modelled on `tests/test_model_program.py` (session fixture building the program with `build_model_program`-like direct `clang_build.build` of `hilclaw/model_forward.c` — `model_build.py` learns this source only in slice 5, so do not edit it — and fixture libraries with `model_build.build_kernel_library`; skip without POSIX or clang, fail on CI without clang; every run through `local_run.run`). At least:
    - **Fixture kernels**, one per kind, in C to each prototype and its memory obligations: each computes with `float` arithmetic in a fixed order and rounds each output element to bf16 with ties to even on the bit pattern, built with `-ffp-contract=off`; each output depends on every input operand (a simplified operation is enough — not necessarily the kind's mathematics; slice 6 adds the kind-faithful fixtures); the SDPA fixture writes rows P … P + m − 1 of both cache operands from `k_new` and `v_new` (ADR-0162 decision 4) and reads rows 0 … l − 1 of them under the causal rule t ≤ P + i, with head g = j / (h / h_kv).
    - **A NumPy `float32` re-computation in the test** of the same prefill with the same fixture operations in the same order; the reported logits rows and token ids **equal it bit for bit**, for a small model with N ≥ 2, H a multiple of H_kv and larger than it, S ≥ 2, G = 1, weights drawn from a seed as bf16 patterns of small finite values, under both `lm_head_rows` values. The RoPE table may be any `float32` array the test makes (do not call `rope_table.build` with Llama constants).
    - **Library table**: two libraries of the same kind bound to different call sites (for example a `gemm` fixture with a different constant offset for `lm_head`) show the table is followed; one library holding several kinds' symbols works.
    - **Wiring checks**: a fixture variant that writes its output only partly shows `0x7FC0` in the expected places (fill at allocation); kernel output printed to stdout appears on stderr, not in the report.
    - **Refusals** with the right status, one stderr line starting with `model_forward: ` and no end mark: wrong argument count; missing or unreadable input file; each form check of criterion 4 (short file at several cuts, trailing bytes, each zero dimension, H not a multiple of H_kv, odd d, bad `lm_head_rows`, index out of range, token id ≥ V, G = 2, `eps` 0 / negative / NaN / infinite); a library that cannot be loaded; a bound library missing the entry point of its call site's kind (status 6 naming the symbol); sizes that overflow `size_t` (status 3).
    - **Abnormal kernels**: a kernel that aborts leaves no end mark and a non-zero status.
    - **Report length**: 8·(S + G) + 2·(rows)·V + 4 bytes.
    - Builds session-scoped; every test within a few seconds on a CI runner. Do not add tests that target test code (D12 ⑤).
11. **No other behaviour change**: `hilclaw/model_program.c`, `model_build.py`, `model_run.py`, `model_execute.py`, `model_binding.py` and their tests unchanged; no dependency added; local `pytest` (coverage gates) and `ruff` green; the new `.c` passes the C gate command locally where `clang` is available.
12. **Process**: code mode (CLAUDE.md A-13). Draft PR titled with `T-0472`, body ending with `Task: T-0472`; reviewer cycle (dev-code-review), at most 7 rounds, until CI is green (the C gate and clang tests run there); then `gh pr merge --squash --body` with the PR body and delete the branch. The reviewer checks at least: each call's operands against ADR-0166 decision 3's table; the three range-copy offsets; `freqs_cis` offset; the cache size C = S + G − 1 and the `sdpa` arguments; the `0x7FC0` fill at allocation only; no cast and no arithmetic on bf16 patterns in the program; the form and size checks; that the header comment states the complete binary form.

## Out of Scope

- Decode passes (G > 1) and the cache across passes (slice 3, T-0473).
- The host-side encoder, runner and report parser (slice 4, T-0473); the build-and-run path and `model_build.py` (slice 5); the kind-faithful synthetic-model test (slice 6).
- A generation mode, token selection, a model-level reference or tolerance (HQ-0071); any RoPE constant (HQ-0070); a cache capacity value.
- Editing `model_program.c` (including its "not yet a forward pass" sentence) or any ADR.

## Follow-ups

- Next in the batch: T-0473 (ADR-0166 code slices 3 and 4).

## Result
