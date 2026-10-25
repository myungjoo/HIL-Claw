---
id: T-0474
title: Add the forward program's build-and-run path (hilclaw/model_build.py forward source, new hilclaw/model_forward_execute.py) and the synthetic-model test of ADR-0166 decision 8 through it (ADR-0166 code slices 5 and 6)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0471, T-0472, T-0473]
touchesFiles: [hilclaw/model_build.py, hilclaw/model_forward_execute.py, tests/test_model_build.py, tests/test_model_forward_execute.py, tests/test_model_forward.py]
estimatedSize: {loc: 380, files: 2}
hq: []
---
## Why

**State.** ADR-0166 (T-0470, `d25a61e4`) designs the bf16 forward pass and generation of the model executor on `cpu_standin` (ADR-0153 code slice 2; PLAN P2-13, which P2-14 needs). Its Consequences (lines 167-173) list six code slices. Slices 1 to 4 have landed: T-0471 (`hilclaw/model_forward_check.py`, the whole-generation check), T-0472 and T-0473 (`hilclaw/model_forward.c`, prefill and decode passes; `hilclaw/model_forward_run.py`, input encoding, one run and report parsing; squash-merged as `f04da8e5`). First check on `main` that T-0471 to T-0473 are `DONE` and read what they landed (dev-item-address step 1).

**This task is slices 5 and 6**, grouped under DRIVER §6 "task 단위" ③ (slice 6 is tests and fixtures only, so it adds nothing to the size cap, and it needs slice 5's path):
- **Slice 5**: "The build-and-run path: the forward program's source and flags in `hilclaw/model_build.py`, and a new module `hilclaw/model_forward_execute.py` that runs slice 1's check, builds one library per distinct kernel and the program, and runs slice 4's steps; with tests."
- **Slice 6**: "The synthetic-model test of decision 8: tests and fixture kernels only."

**What is already there.** `tests/test_model_forward.py` and `tests/test_model_forward_run.py` already compare a generation of the program bit for bit with a NumPy re-computation (N = 2, H = 4, H_kv = 2, S ≥ 2, G ≥ 3, both `lm_head_rows`), with a per-pass library table and a RoPE table the test draws at random. `tests/test_model_forward_check.py` already covers the check's negative cases one at a time. Slice 6 here therefore adds what decision 8 asks that they do not yet show: the generation **through the whole path** — a binding of `KernelReference`s with the bf16 contracts, slice 1's check, the per-shape binding turned into the per-pass library table, the builds, the RoPE table from `rope_table.build` with the test's own constants — equal bit for bit to the re-computation, and the check's outcomes coming out of that path for a binding, a weight and a setting made wrong one at a time. Do not duplicate tests that already exist; reuse their fixture kernels and re-computation (import them from `tests/test_model_forward.py`, as `tests/test_model_forward_run.py` does; move a helper into a shared test module only if that keeps it simpler).

**The binding-to-table step.** T-0473 left "turning a per-shape binding into the per-pass library table" to slice 5 (T-0473 Result; the conventions paragraph of `model_forward_run.py`). For call site s at pass p, the shape is the one `model_binding`'s `*_shape` functions give for that pass's rows (S at pass 0, 1 after; the SDPA positions l = P + T; lm_head one row at every pass for `"last"`), and the library is the one built for the kernel slice 1's `calls` pair with that (call site, shape).

**PLAN order and D18.** P2-13 is a checklist item and P2-14 needs it; the D18 rule does not apply. The round-loop items and P2-5 are held by unresolved HQs (HQ-0021, HQ-0024, HQ-0048, OD-3).

**HQ-0071 (open, owner)** — token selection, model-level comparison, reference: only the given-sequence mode exists (ADR-0166 decision 7); no selection rule, reference or tolerance is added. **HQ-0070** — RoPE scale factor: every RoPE constant is the caller's required argument with no default; tests use their own constants. **HQ-0069** (runtime acceptance (lxvii)) and **HQ-0033** (ADR-0116 flags): not crossed; no build flag of a stand-in kernel is chosen (the binding's `KernelReference.flags` are the caller's), and the forward program's own flags are only what it needs to build (as `model_execute` passes `program_flags`/`program_trailing_flags`, e.g. `-ldl`, from the caller).

**D16.** Built with the local `clang`, run as local processes with fixture kernels the test writes. Nothing starts `claude`, downloads a model file, or needs a board or an API key. Without clang or POSIX the clang tests skip locally and fail on CI; the pure-Python tests (argument refusals, check outcomes before any build, the table mapping, a recorder in place of the builds and the run) run everywhere.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): the executor procedure, the resume rule and the time limit.
  - §5 (lines 86-114): the task format, the size cap (600 LOC, 10 files, tests excluded), the naming and the test rules.
  - §6 "task 단위" ④ (line 126): what to check when an earlier task of the batch closed without a result.
  - For this task: branch `claude/T-0474-<slug>`; commit trailer `Task: T-0474`; code mode, so a Draft PR whose body ends with `Task: T-0474`.
- `CLAUDE.md`, "상시 규칙": "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙".
- `.claude/skills/dev-item-address/SKILL.md`: the whole procedure, in code mode.
- `ARCHITECTURE/decisions/ADR-0166-od31-bf16-forward-pass.md`: decision 4 (lines 104-112), decision 6 (the checks before anything is built), decision 7 (modes and the report), decision 8 (the driver's test of the pass), Consequences code slices (lines 167-173) and the runtime acceptance line (line 176), Boundaries (lines 189-198).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: decision 3 "Loading", decision 5 (lines 58-62: the five named outcomes, no fallback), decision 6 (lines 64-68).
- `hilclaw/model_execute.py`: the whole file (322 lines) — the model for `model_forward_execute.py`: `PREFIX`, `BuildFailed`, `ModelExecution`, `execute`, the build directory outside both checkouts, the removal on every path, and the argument checks (`_checked_*`, `_remove`).
- `tests/test_model_execute.py`: skim the structure (recorder cases, then cases that build with clang).
- `hilclaw/model_build.py`: the whole file (136 lines).
- `tests/test_model_build.py`: `test_public_names` and the program-build tests.
- `hilclaw/model_forward_check.py`: the module docstring and `check` (lines 1-220).
- `hilclaw/model_forward_run.py`: the module docstring, `CALL_SITES`, `encode_input`, `run_forward_program`, `ForwardProgramResult`.
- `hilclaw/model_forward.c`: the header comment (lines 1-122) — the command line, the library table, the exit statuses.
- `hilclaw/model_binding.py`: `ModelDimensions`, `KernelReference`, `BindingEntry`, `BindingCheck` (lines 197-250), `check`'s `calls` form (lines 336-422), and the `*_shape` functions (`gemm_shape` line 278, `rmsnorm_shape` 424, `elementwise_add_shape` 511, `swiglu_shape` 598, `rope_shape` 683, `sdpa_shape` 784).
- The six `hilclaw/*_bf16_contract.py` modules: `task_contract` only (what a fitting `KernelReference.contract` is).
- `tests/test_model_forward.py` (fixture kernels, `make_model`, `generate`, the build fixture) and `tests/test_model_forward_run.py` (how it imports them and builds the RoPE table).
- `tests/test_rope_table.py`: `test_the_module_is_named_only_by_its_known_callers` (line 587), in case the new module names `rope_table`.

## Acceptance Criteria

**Slice 5 — the build-and-run path:**

1. `hilclaw/model_build.py`: the forward program's source as a public constant next to `PROGRAM_SOURCE` (for example `FORWARD_PROGRAM_SOURCE`, the path of `model_forward.c`) and a function that builds it alone, in the form of `build_model_program` (every argument handed to `clang_build.build` unchanged, no flag added, `-ldl` the caller's `trailing_flags`). The forward program is bf16 only: no dtype flag applies to it. Update the module docstring; `PROGRAM_SOURCE`, `build_model_program` and `build_kernel_library` keep their behaviour.
2. New module `hilclaw/model_forward_execute.py` (Python, the host side's language, ADR-0153 decision 2; one line in the commit body), with a module docstring in the form of `model_execute.py`'s: the rule, the steps, the conventions, what it does not do (no selection rule, reference, tolerance, RoPE constant default, cache capacity, fallback, cast, container or environment choice; nothing stored or retried; nothing written outside its build directory).
3. **One entry**, for example `execute(dimensions, binding, *, eps, rope, weights, prompt, given, lm_head_rows, build_timeout_s, run_timeout_s, program_flags=(), program_trailing_flags=(), compiler=None, env=None, prefix=(), parent=None, keep_out=())`, with no default for any model parameter, setting or time limit. Steps, in order:
   - (a) slice 1's `model_forward_check.check` at the dtype `"bf16"` with `generation_length` the length of `given`; what it raises is passed on. If its result is not `ok`, return its `BindingCheck` in the result and **build, write and start nothing** (ADR-0153 decision 5: no kernel, kernel unfit and invalid input build or start nothing).
   - (b) The distinct kernels of the check's `calls`, in first-appearance order; state in the docstring what "distinct" compares (a `KernelReference`'s `contract` may be an unhashable mapping, so equality, not hashing, unless you show it is always hashable). Kernel `i` is library `i`.
   - (c) The per-pass library table for `model_forward_run.encode_input`: for each of the fifteen call sites and each pass p = 0 … G − 1, the index of the kernel bound to that call site's shape at pass p (see Why). A shape absent from `calls` cannot occur after an `ok` check; treat it as an internal error, not a new outcome.
   - (d) A build directory of its own outside both checkouts, as `model_execute` makes it (same rules for `parent` and `keep_out`, removed on every path with `hilclaw.scratch.remove`, `removed` in the result); build each kernel with `build_kernel_library` (its own `sources` and `flags`), then the forward program with item 1's function (`program_flags`, `program_trailing_flags`). The first failed build is the outcome **build failed**, naming the kernel (its index, or `None` for the program) and carrying the `BuildResult`; nothing after it is built or run.
   - (e) Write the input file with `encode_input` and run it once with `run_forward_program` (`run_timeout_s`, `env`, the prefix as in `model_execute`); a run failure is the outcome **run failed** carried by its `ForwardProgramResult` as returned.
4. **The result**: one `NamedTuple` (for example `ForwardExecution(check, build_failed, run, removed)`) that carries which of the five outcomes of ADR-0153 decision 5 happened, or the report. Reuse `model_execute.BuildFailed` rather than defining a second one. Reuse `model_execute`'s argument checks and removal instead of copying them (import them, as `model_forward_run` imports `model_run`'s helpers, or move them into a small shared module if the reviewer prefers; either way `model_execute`'s behaviour and its tests stay unchanged).
5. **Argument refusals** before anything is made: `TypeError`/`ValueError` naming the argument for the arguments this module owns (paths, prefix, parent, keep_out, program flags, time limits as `model_execute` treats them); a `program_flags` item that contains `HILCLAW_MODEL_BF16` is refused as in `model_execute` only if it can affect `model_forward.c` — if it cannot, do not refuse it and say so in the docstring.

**Slice 6 — the synthetic-model test (tests and fixture kernels only):**

6. New `tests/test_model_forward_execute.py` (D12 ④): every public function of the new module; happy, error, branch and negative cases.
   - Pure-Python cases (run everywhere, the builds and the run replaced by a recorder): a not-`ok` check builds and starts nothing and its outcomes come back unchanged — one case each for a binding made wrong (a missing call site: `"no_kernel"`; a kernel whose contract does not fit: `"kernel_unfit"`), a weight made wrong (shape or element type), and a setting made wrong (a token id outside the vocabulary, an `eps` `rmsnorm_eps` refuses, a RoPE constant `rope_table.build` refuses, the generation mode); the distinct-kernel order and the per-pass table for a binding with different kernels per shape (prefill vs decode, `"all"` vs `"last"` for lm_head, SDPA's l growing per pass); a failed kernel build and a failed program build stop the path and the directory is removed; every argument refusal; what a build or the run raises passes on after the directory is removed.
   - Cases that build with clang (skip without POSIX/clang, fail on CI without clang): ADR-0166 decision 8 through `execute` — N ≥ 2, H a multiple of H_kv and larger, S ≥ 2, G ≥ 3, under both `lm_head_rows` values, the RoPE table from `rope_table.build` with the test's own five constants, a binding of `KernelReference`s whose `contract` is each kind's `task_contract` and whose `sources` are the fixture kernels of `tests/test_model_forward.py` (built with contraction off) — whose reported token ids and logits rows **equal, bit for bit**, the NumPy re-computation of the same generation; at least one binding where one call site has a different kernel at the prefill than at the decode passes, so the binding-to-table step is shown on a real run; a kernel that does not compile (build failed); a kernel that aborts (run failed).
7. `tests/test_model_build.py`: the new constant and function (public names, arguments handed over, no flag added, a real clang build of the forward program).

**Both:**

8. **Size**: at most 600 changed lines outside tests, at most 10 files; expected two (`model_build.py`, `model_forward_execute.py`). If it would go over, finish slice 5 and propose the rest in Follow-ups (DRIVER §5).
9. **No other behaviour change**: `model_forward.c`, `model_forward_run.py`, `model_forward_check.py`, `model_execute.py`, `model_run.py`, `model_program.c`, `model_binding.py`, `rope_table.py` unchanged (except a behaviour-preserving move of `model_execute`'s helpers per item 4, if chosen); no dependency added; local `pytest` (80 % line and function coverage gates) and `ruff` green; the C gate command passes locally where `clang` is available.
10. **Process**: code mode (CLAUDE.md A-13). Draft PR titled with `T-0474`, body ending with `Task: T-0474`; reviewer cycle (dev-code-review), at most 7 rounds, until CI is green; then `gh pr merge --squash --body` with the PR body and delete the branch. The reviewer checks at least: nothing is built or started after a not-`ok` check; the per-pass table matches the program's shapes at each pass (rows, SDPA l, lm_head rows); distinct kernels are built once each; the directory is outside both checkouts and removed on every path; no selection rule, reference, tolerance, RoPE constant default or cache capacity appears; the bit-for-bit test runs through `execute`, not around it.
11. **Result**: state in the task's Result that ADR-0166 slices 1 to 5 have landed, so the driver can record ADR-0153's runtime acceptance item **(lxviii)** as an HQ with the reason `runtime-acceptance` (ADR-0166 Consequences, line 176; DRIVER §8). Do not record it yourself.

## Out of Scope

- A generation mode, token selection, a model-level comparison, reference or tolerance (HQ-0071, OD-31 sub-question 6); any Llama RoPE constant (HQ-0070); a cache capacity value or a longest sequence; a tokenizer (sub-question 5 — the test hands token ids directly).
- Deriving a binding from a key's best (OD-20, OD-7); exposure of the executor as a tool or its registration with `correctness.check`, `spec.write` or the instance start (OD-18, OD-23, OD-6); isolation, time and memory limits of the build and process (OD-14, NFR-4); a data-plane record of a model run.
- Editing any ADR, or the "less exact" sentences ADR-0166 Consequences lists (deferred in PLAN "보류", T-0470 follow-up).
- Changing `model_forward.c`'s binary form.

## Follow-ups

- After this task: ADR-0166's code slices are all landed. The driver records ADR-0153's runtime acceptance item (lxviii) as an HQ (see item 11). The rest of P2-13 (the model-level comparison) waits on HQ-0071.

## Result
