---
id: T-0419
title: Add the host-side binding check of the model executor for the GEMM call sites - a new module hilclaw/model_binding.py that derives every GEMM call of a generation from the model dimensions and run settings, checks an explicit binding against them before anything is built, and returns the outcomes no kernel, kernel unfit and invalid input (ADR-0153 code slice 1, first half; for PLAN P2-13)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13"]
dependsOn: [T-0418]
touchesFiles: [hilclaw/model_binding.py, tests/test_model_binding.py]
estimatedSize: {loc: 260, files: 1}
hq: [HQ-0067]
---
## Why

**Where things stand** (as of `main` `9f9dfd8`):
- PLAN P2-5 cannot move: each remaining part waits on an open owner HQ (HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0032). P2-10 comes after P2-5. PLAN P2-11 (the contract records of the five non-GEMM kinds) and P2-12 (bf16/fp16) wait on HQ-0064, HQ-0065 and HQ-0066.
- ADR-0153 (T-0418, `4498d50`) decides the model executor of PLAN P2-13. Its Consequences name two code slices. Slice 1 is "the host side's binding checks and outcomes, and the build and loading of fp32 `gemm` kernels as shared libraries called by a model program through ADR-0008's prototype, tested with hand-written kernels". It says slice 1 is "possible before the answers to HQ-0064, HQ-0065 and HQ-0066" and leaves to the planner whether to take it first.
- **Planner's judgement**: take it now. It is the only P2-11 to P2-14 work that waits on no owner answer, and P2-14 needs it.
- Slice 1 would exceed the DRIVER §5 size cap as one task: a Python check, a build path for shared libraries, a C program using `dlopen`, and a host-side start/report path. It is split. **This task is the first half**: the pure host-side binding check of ADR-0153 decision 3 ("The binding", "Fit") and decision 5 (the three pre-build outcomes), for the six GEMM call sites only. It builds, loads and starts nothing. The second half (shared-library build, model program, `build failed` / `run failed`) is the next task (Follow-ups).

**D18 reading.** This is work of a PLAN checklist item (P2-13, code of ADR-0153), so the D18 hold rule does not apply (DRIVER §6).

**Not crossed.**
- No value of H, d_h or the KV-head count is assumed: they are parameters (HQ-0064; ADR-0153 decision 3 (a), decision 6).
- No dtype, cast, accumulation, oracle or tolerance is chosen: the only contract checked is the existing fp32 `gemm` contract of ADR-0008 (HQ-0065, HQ-0066).
- No contract is invented for RMSNorm, RoPE, SDPA, SwiGLU or elementwise add. Their call sites are not in this module.
- No rule derives a binding from a key's best (OD-20, OD-7). The executor never chooses a kernel itself (ADR-0153 decision 3).
- No exposure (CLI, registry or MCP tool) is added (ADR-0153 decision 1: "The first code slice is a module function").
- No file is read or written. No data-plane member, file, kind or version changes. No new external dependency: standard library only.

**No open PR overlaps.** Open PR #186 (T-0324, BLOCKED by HQ-0032) touches only `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`. This task must not edit `tests/test_gemm_contract.py` or `hilclaw/gemm_contract.py`. It reads only the public names of `hilclaw/gemm_contract.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming, size cap, test rules).
- `CLAUDE.md`: "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "브랜치·merge 절차" (code mode).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Decision §1 (lines 28-33), §3 (lines 40-46), §5 (lines 58-62), §6 (lines 64-68), Consequences "Code slices" (line 88), Boundaries (lines 101-115).
- `ARCHITECTURE/decisions/ADR-0152-od31-llama-forward-operations.md`: Context, the Meta `model.py` bullet (line 23: `wq`, `wk`, `wv`, `wo`, `FeedForward`); Decision §2 table (lines 41-66); §4 (lines 78-83); §5 table (lines 84-104).
- `ARCHITECTURE/decisions/ADR-0008-od6-gemm-kernel-contract.md`: Decision §4 to §6 and §8 (lines 46-112).
- `hilclaw/gemm_contract.py` (whole file; the public names `LANGUAGE`, `PROTOTYPE`, `DTYPE`, `task_contract`).
- `hilclaw/harness/verification_build.py` lines 41-80 (the package convention of a `parameter` attribute on a `TypeError`/`ValueError` raised before anything is started).

## Acceptance Criteria

Module `hilclaw/model_binding.py` (Python; the language-choice line goes in Result and the commit body). It has a boilerplate docstring that names ADR-0153 and lists what it does not do (no build, no load, no process, no file, no exposure, no non-GEMM call site). The names below are this task's. The executor may rename them only if the review asks, and records any rename in Result.

1. **Call sites.** A constant `CALL_SITES`, the tuple `("qkv", "o", "gate", "up", "down", "lm_head")`: the GEMM rows of ADR-0152 decision 2 (rows 3, 8, 11 as two call sites, 13 and 16), as ADR-0153 decision 3 separates them.
2. **Model dimensions.** A `NamedTuple` `ModelDimensions(hidden, intermediate, vocabulary, layers, heads, kv_heads, head_dim)` and a function `check_dimensions(dimensions)`:
   - Each field must be exactly an `int` from 1 to `hilclaw.keys.MAX_INTEGER`. `bool` is refused.
   - `heads` must be a multiple of `kv_heads` (ADR-0153 decision 6; Meta's assert, ADR-0152 Context).
   - A failure raises `TypeError` (wrong type) or `ValueError` (out of range, not a multiple) with `parameter` = `"dimensions"`.
   - No value of Llama 3.2 1B is a default.
3. **GEMM shapes of a pass.** A function `gemm_shape(dimensions, call_site, rows)` returns `(m, k, n)` with `m = rows`. The `(k, n)` values below are derived from ADR-0152 Context (`model.py`) and decision 5. For H = 32, d_h = 64 they equal its GEMM table.
   - `qkv`: (`hidden`, (`heads` + 2·`kv_heads`)·`head_dim`)
   - `o`: (`heads`·`head_dim`, `hidden`)
   - `gate` and `up`: (`hidden`, `intermediate`)
   - `down`: (`intermediate`, `hidden`)
   - `lm_head`: (`hidden`, `vocabulary`)

   An unknown call site raises `ValueError` with `parameter` `"call_site"`. A `rows` that is not such an integer raises `TypeError`/`ValueError` with `parameter` `"rows"`. Dimensions are checked as in 2.
4. **Calls of a generation.** A function `generation_calls(dimensions, *, prompt_length, generation_length, lm_head_rows)` returns, for each call site in `CALL_SITES` order, the sorted tuple of distinct shapes the generation calls it with:
   - The generation is one prefill pass with `rows = prompt_length`, then `generation_length − 1` decode passes with `rows = 1` (ADR-0153 decision 4, read as: the prefill gives the first token after the prompt, and each further token needs one decode pass). Record this reading in the docstring.
   - For `lm_head`, `lm_head_rows` `"all"` uses the rows of each pass, and `"last"` uses 1 for every pass (ADR-0153 decision 4).
   - Ranges: `prompt_length` ≥ 1, `generation_length` ≥ 1, `lm_head_rows` in {`"all"`, `"last"`}. A value outside them here raises `ValueError` (the outcome form is item 6).
5. **Binding and kernel reference.**
   - A `NamedTuple` `KernelReference(sources, contract, flags)`: `sources` is a non-empty tuple of paths, `contract` is the `task.contract` object of the spec the kernel was written to, and `flags` is a tuple of `str` (build settings, carried and not interpreted here).
   - A `NamedTuple` `BindingEntry(kernel, shapes)`: `shapes` is either the string `"every"` or a non-empty tuple of `(m, k, n)` integer triples.
   - A binding is a mapping from call site to a non-empty sequence of `BindingEntry`.
   - **Refused as malformed** (`TypeError`/`ValueError`, `parameter` `"binding"`): a key not in `CALL_SITES`; an entry that is not of these types; and **two entries of one call site that cover a common shape**, where an `"every"` entry overlaps every other entry of its call site. The executor never chooses between kernels (ADR-0153 decision 3). Record this reading in the docstring.
6. **The check.** A function `check(dimensions, binding, *, prompt, generation_length, lm_head_rows, given=None)` returns a `NamedTuple` `BindingCheck(ok, outcomes, calls)`.
   - `prompt` is a non-empty sequence of token ids. `given` is `None` (generation mode) or a sequence of exactly `generation_length` token ids (given-sequence mode, "every token is given", ADR-0153 decision 4).
   - `outcomes` is a tuple of `Outcome(kind, call_site, shape, reason)` NamedTuples, in a documented deterministic order. Kinds are exactly the strings `"invalid_input"`, `"no_kernel"` and `"kernel_unfit"`, the spelling of ADR-0153 decision 5 that the record leaves to the code slice:
     - **`invalid_input`**, with `call_site` and `shape` `None`, for each of: a token id of `prompt` or `given` outside 0 … `vocabulary` − 1; an empty `prompt`; `generation_length` < 1; `lm_head_rows` not `"all"`/`"last"`; `given` of the wrong length. When any `invalid_input` exists, the binding is not checked against shapes and `calls` is empty.
     - **`no_kernel`** (call site, shape) for each shape of `generation_calls` that no entry of that call site covers. A call site absent from the binding gives one outcome per shape.
     - **`kernel_unfit`** (call site, `shape` `None`, reason) for each bound entry whose `contract` does not fit the fp32 `gemm` contract. The comparison is on `language`, `prototype` text and the sequence of operand `(name, role, dtype)` (ADR-0153 decision 3 "Fit"; ADR-0008 decision 8). The reference values come from `gemm_contract.task_contract(1, 1, 1)`, not from copies. A `contract` that is not a mapping, or lacks those members, is unfit with a reason, not an exception.
     - A listed shape other than the spec's own shape is accepted, and an `"every"` entry is accepted. Both rest on ADR-0008 decision 6, cited in the docstring. Operand shapes in `contract` are not compared.
   - `calls` is a tuple of `(call_site, shape, kernel)` for every call of `generation_calls`, in call-site order and then shape order, filled only when `ok`.
   - `ok` is `True` exactly when `outcomes` is empty.
   - Wrong argument types (a token id that is not an `int`, or `bool`) raise `TypeError` with the matching `parameter` (`"prompt"`, `"given"`, `"generation_length"`, `"lm_head_rows"`, `"binding"`, `"dimensions"`). Arguments are not modified. Nothing is built, started or read.
7. **Tests** `tests/test_model_binding.py`, small synthetic dimensions only (for example hidden 8, intermediate 16, vocabulary 11, layers 2, heads 4, kv_heads 2, head_dim 2). One test checks that `gemm_shape` at Llama values (2048, 8192, 128256, 16, 32, 8, 64) gives ADR-0152's GEMM table, as a derivation check. The tests cover:
   - **happy**: a full binding, one `"every"` entry per call site with a contract built from `gemm_contract.task_contract`, gives `ok` and the exact `calls`. A binding with listed shapes that cover exactly the generation's shapes is also `ok`.
   - **branch**: `generation_length` 1 (no decode shape) and > 1; `lm_head_rows` `"all"` and `"last"`; generation and given-sequence modes; several entries per call site with disjoint listed shapes.
   - **error / outcome**: each `invalid_input` case; `no_kernel` for a missing call site and for an unlisted shape; `kernel_unfit` for a wrong prototype, a wrong operand role, a wrong dtype, a wrong language, a non-mapping contract and a missing member; several outcomes reported together in the documented order.
   - **negative**: every `TypeError`/`ValueError` path of items 2-6 with its `parameter`, including overlapping entries, an `"every"` entry beside another entry, an unknown call site key, `bool` dimensions, and `heads` not a multiple of `kv_heads`.
   - Every public function and NamedTuple of the module, and the guarantee that arguments are not modified.
8. CLAUDE.md test rules hold: package line and function coverage ≥ 80%, ruff clean, a test file for the new module. Local `pytest` and `ruff` pass. CI is green before the self squash-merge (DRIVER §5 naming: branch `claude/T-0419-<slug>`, PR title with `T-0419`, last line of the PR body `Task: T-0419`).

## Out of Scope

- Building kernels as shared libraries, the C model program, `dlopen`/`dlsym`, starting a process, the outcomes `build failed` and `run failed`, the report (next task, Follow-ups).
- Weights, the embedding lookup, buffers, the KV cache, token selection, the synthetic tokenizer (ADR-0153 slice 2 and decision 4).
- Call sites and contracts of RMSNorm, RoPE, SDPA, SwiGLU and elementwise add (P2-11; HQ-0064/0065/0066).
- Any dtype other than fp32, any change to `hilclaw/gemm_contract.py` or its tests, any exposure as a tool or CLI, any derivation from `best.json`.
- Edits to `ARCHITECTURE/` (the record exists; this is its code).

## Follow-ups

- Next task (candidate T-0420, the second half of ADR-0153 code slice 1): build each bound fp32 `gemm` kernel into a shared library through `hilclaw.clang_build`, and add a fixed-source C model program that loads each library with `dlopen` and calls `hilclaw_gemm` through `dlsym` for the `calls` of this module's `BindingCheck`. Add the host side that builds, starts and reads the report, with the outcomes `build failed` and `run failed`. Test with hand-written kernels. That task asks runtime acceptance item (lxvii) of ADR-0153 once it lands (DRIVER §8, reason `runtime-acceptance`).

## Result

**Outcome: DONE (resumed after HQ-0067 answered (a))** — PR #244 squash-merged as 99e4664; branch deleted; squash body ends with `Task: T-0419`.

- Resume: origin/main was merged into the branch (eba65c4, no force push), without conflicts. 2944f20 adds `hilclaw/model_binding.py` to the binders list of `tests/test_gemm_contract.py` (authorized by HQ-0067 (a)), keeping the #186 entries; the test is renamed to match.
- Review rounds: 2 after the resume (round 1 Approve, its Low and Nit fixed in 323a19a; round 2 Approve, one Nit: commit 2944f20 lacks a `Task:` line, the squash message carries it).
- Language: Python — the host side of ADR-0153 decision 2 is Python and the check runs in memory with the standard library only.
- Gates: local pytest 26979 passed / 910 skipped; `hilclaw/` line coverage 97%, `model_binding.py` 100%; ruff check and format clean; CI green (Python 3.11/3.14, Coverage, C, sh, Test presence).
- Follow-up: token ids must be exact `int`; a later host side holding them in numpy arrays must convert them first, or the check must accept numpy integers (slice 2).

### Earlier attempt (BLOCKED on HQ-0067)

**BLOCKED** (reason: task requirement conflicts with an existing test whose file the task forbids editing and open PR #186 edits; CLAUDE.md A-13 "requirement unclear" and DRIVER §3 "open PR file conflict risk").

- Branch `claude/T-0419-model-executor-gemm-binding-check`, Draft PR #244 (DONOTMERGE kept), commits `26872fa` (module and tests) and `323a19a` (review round 1 nits). Not merged.
- Implemented as specified: `hilclaw/model_binding.py` (names exactly as in the Acceptance Criteria, no rename; plus public constants `LM_HEAD_ROWS`, `INVALID_INPUT`, `NO_KERNEL`, `KERNEL_UNFIT`) and `tests/test_model_binding.py` (179 tests, module coverage 100%, ruff clean). About 280 code lines plus docstrings (453 lines in all).
- Language: Python - the host side of ADR-0153 decision 2 is Python; pure in-memory checking with the standard library only.
- Review: round 1 Approve (dev-reviewer), with one Low and one Nit, both fixed in `323a19a`; the fix has not been re-reviewed.
- **Blocker**: the full local suite fails `tests/test_gemm_contract.py::test_module_is_bound_by_the_default_registry_only_and_imports_keys_only`. It allows the text `gemm_contract` in `hilclaw/` only in `check_definition.py` and `spec_tool.py`. Acceptance criterion 6 requires the fit reference from `gemm_contract.task_contract` and forbids copies. The fix used before (when `spec_tool.py` became a binder) is to add the new module to that test's binders. This task forbids editing `tests/test_gemm_contract.py`, and open PR #186 (T-0324) changes the same lines. Hiding the import from the text check would defeat the test, so it was not done.
- Resume: after the owner's answer, add `hilclaw/model_binding.py` to the binders of that test (option a), re-review, wait for CI green, then squash-merge PR #244.
- Follow-up (reviewer, Info): token ids are exact `int` only, as criterion 6 says. A later host side that holds ids in `numpy` arrays (ADR-0153 decision 2) must convert them first, or the check must accept `numpy` integers. Candidate for T-0420 or slice 2.
