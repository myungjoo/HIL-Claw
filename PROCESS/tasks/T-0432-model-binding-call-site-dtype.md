---
id: T-0432
title: Give hilclaw/model_binding.check the model's dtype - fit against the fp32 or bf16 gemm contract it selects, invalid input for a dtype with no contract (ADR-0157 code slice 1)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0430, T-0431]
touchesFiles: [hilclaw/model_binding.py, hilclaw/model_gemm.py, hilclaw/gemm_bf16_contract.py, tests/test_model_binding.py, tests/test_model_gemm.py, tests/test_gemm_bf16_contract.py]
estimatedSize: {loc: 90, files: 3}
hq: []
---
## Why

**Where things stand** (as of `main` `6bd79ec`):
- ADR-0156 defines the bf16 `gemm` contract on `cpu_standin`. T-0430 added its values in `hilclaw/gemm_bf16_contract.py`. No other module uses it yet.
- ADR-0157 (T-0431, landed as `4fef3b8`) decides where a call site's dtype comes from. It is one dtype per generation, given as a model parameter, with no default. That dtype selects the contract each bound kernel is fitted against. A kernel written to another dtype's contract is **kernel unfit**. A dtype for which the executor knows no contract at every call site's kind is **invalid input**. The fp32 path stays, and its callers pass `fp32`.
- ADR-0157 Consequences list code slice **(1)**: "the model's dtype in `hilclaw/model_binding.py`'s check: the contract selected by the dtype (`hilclaw.gemm_contract` or `hilclaw.gemm_bf16_contract`), kernel unfit for an entry of another dtype, invalid input for a dtype outside the range of decision 4, and the existing fp32 callers passing `fp32`; with tests." This task is that slice.
- Today `hilclaw/model_binding.check` compares every entry with the fp32 contract only. It takes no dtype.

**D18.** This comes from the T-0431 follow-up, so the priority rule applies. It is needed for P2-13 and P2-14. The Llama goal is bf16 (owner, HQ-0065). The executor cannot accept a bf16 kernel for a GEMM call site until its binding check knows the generation's dtype. It is not input hardening, wording or a behaviour-preserving refactor, so it is not set aside.

**PLAN P2 order.** The round-loop items and P2-5 still wait on open HQs (HQ-0021, HQ-0031, HQ-0048; the P2-4 gate is owner-only OD-3). P2-10 follows P2-5. So the work continues on P2-11 to P2-14, as in T-0431.

**D16.** Nothing here starts `claude` or needs a board, a model file or an API key. Nothing is built or run by the changed code. `model_gemm` keeps its fp32 build and run path unchanged.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0432-<slug>`, commit trailer `Task: T-0432`, PR body last line `Task: T-0432`; size cap; the D12 test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`:
  - decision 1 (lines 34-41);
  - decision 2 (lines 43-47);
  - decision 3 table (lines 49-60);
  - decision 4 (lines 66-71);
  - decision 5 (lines 73-77);
  - Alternatives rows for points 4 and 5 (lines 88-90);
  - Consequences, code slice (1) (line 96).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` decision 3 "Fit" (lines 40-46) and decision 5 (lines 58-62).
- `hilclaw/model_binding.py`, the whole module (455 lines).
- `hilclaw/gemm_contract.py`: the module docstring (lines 1-45) and `task_contract`.
- `hilclaw/gemm_bf16_contract.py`: the module docstring (lines 1-43), the constants (lines 50-64) and `task_contract` (lines 126-159).
- `hilclaw/model_gemm.py`, the whole module (169 lines).
- `hilclaw/keys.py` lines 29-35 (`MAX_INTEGER`; the name pattern `_NAME` of ADR-0001's `dtype` field).
- Tests to change:
  - `tests/test_model_binding.py` lines 1-60 (helpers) and every test that calls `check`;
  - `tests/test_model_gemm.py` lines 53-72 (`settings`, `operands_for`);
  - `tests/test_gemm_bf16_contract.py` lines 467-476 (`test_module_imports_keys_only_and_is_bound_nowhere`);
  - for the pattern of the binder list, `tests/test_gemm_contract.py` lines 386-401.

## Acceptance Criteria

1. **`hilclaw/model_binding.check` takes the model's dtype** as a required keyword-only argument `dtype` with no default (ADR-0157 decision 1 and the Alternatives row for point 5).
   - The argument-refusal order becomes `dimensions`, `dtype`, `prompt`, `given`, `generation_length`, `lm_head_rows`, `binding`.
   - A `dtype` that is not exactly a `str` raises `TypeError`.
   - A `str` that is not a name of ADR-0001's `dtype` field (the pattern `[a-z][a-z0-9_]{0,31}`) is a malformed argument (ADR-0157 decision 4, last Reasons sentence) and raises `ValueError`.
   - Both errors carry `parameter` `"dtype"`, like every other argument error of the module.
   - Do not import a private name of `hilclaw.keys`. Restate the pattern in the module if needed.
2. **The range of the dtype** is the dtypes at which the module knows the `gemm` contract: `fp32` (`hilclaw.gemm_contract`) and `bf16` (`hilclaw.gemm_bf16_contract`) (ADR-0157 decision 4). Expose it as a public module constant (for example `DTYPES = ("fp32", "bf16")`) so that later slices can extend it.
3. **A dtype outside the range is an `"invalid_input"` outcome**, not an exception (ADR-0157 decision 4). Examples are `fp16` and `int8`.
   - It is the **first** `"invalid_input"` outcome, before the prompt and setting reasons. `call_site` and `shape` are `None`.
   - Its reason names the dtype and the kind `gemm` that has no contract at it. For example: `dtype: no gemm contract is known at the dtype 'fp16'`.
   - The other invalid-input reasons are still reported after it, in their current order.
   - When the dtype is out of range, **no `"kernel_unfit"` and no `"no_kernel"` outcome** is produced. There is no contract to compare against, and ADR-0157 rejects kernel unfit for an unknown dtype (Alternatives row "Kernel unfit for an unknown dtype"). `calls` is `()`.
4. **The fit check compares each entry with the contract the dtype selects** (ADR-0157 decision 3, row "Contract a fit is checked against"). The reference is `gemm_contract.task_contract(1, 1, 1)` for `fp32` and `gemm_bf16_contract.task_contract(1, 1, 1)` for `bf16`. The comparison is unchanged: `language`, `prototype`, and each operand's `name`, `role`, `dtype`.
   - Reasons name the selected contract. For example: `contract.prototype is not that of the bf16 gemm contract`.
   - A kernel whose `task.contract` is the fp32 contract in a `bf16` generation is `"kernel_unfit"`. So is a bf16 kernel in an `fp32` generation (ADR-0157 decision 2).
   - Operand shapes are still not compared. An `"every"` entry and a listed shape other than the spec's own are accepted for both dtypes (ADR-0157 decision 3; ADR-0008 decision 6; ADR-0156 decision 7).
5. **`hilclaw/model_gemm.run` passes `dtype="fp32"`** to `model_binding.check` (ADR-0157 decision 5: the existing fp32 callers pass `fp32`).
   - Its signature does not change.
   - Its model program still finds `hilclaw_gemm` over `float`. The bf16 program and a `dtype` argument for `run` are code slice (2), not this task.
   - Its docstring states that the binding is checked at the dtype `fp32`, in one sentence. Its "chooses no … dtype" reading stays true or is made exact.
6. **Docstrings** (CLAUDE.md "코멘트 최소화": rewrite in place, no new multi-line comments):
   - `hilclaw/model_binding.py`: the module docstring no longer says "no contract other than fp32 `gemm` and no dtype other than fp32". It names ADR-0157 and the two contracts. The `"every"` reading covers both dtypes. The `check` docstring describes `dtype`, its refusals, the dtype `"invalid_input"` outcome and its place in the order, and the selected contract in item 2.
   - `hilclaw/gemm_bf16_contract.py`: the module docstring states that `hilclaw.model_binding` reads `task_contract` as the reference of its fit check for a `bf16` generation (ADR-0157 decision 3). Only that sentence and any sentence it makes false change. No value or function of the module changes.
7. **Tests** (CLAUDE.md test rules ①-④; ⑤ does not apply because these are tests of `hilclaw/` modules):
   - `tests/test_model_binding.py`: every existing call passes `dtype="fp32"`, for example through the `run` helper. Existing fp32 expectations are unchanged except for reason texts that now name the contract. New tests cover at least:
     - **happy**: a `bf16` binding whose every entry has the `gemm_bf16_contract.task_contract` (one `"every"` entry per site, and one with listed shapes, including a shape other than the kernel spec's own) is `ok`, with `calls` equal to those of the equivalent fp32 check;
     - **branch / mismatch**: an fp32-contract kernel in a `bf16` generation, and a bf16-contract kernel in an `fp32` generation, each give `"kernel_unfit"` per entry with the selected contract named; a mixed binding (one site bf16, the others fp32) in a `bf16` generation gives `"kernel_unfit"` only for the fp32 sites;
     - **invalid input**: `fp16`, and another valid name such as `int8`, give the dtype `"invalid_input"` first, then the other invalid-input reasons in order (for example together with an empty prompt). The same binding with a fitting fp32 contract and with a wrong contract gives no `"kernel_unfit"` and no `"no_kernel"`;
     - **negative (malformed)**: `dtype` missing (`TypeError` from the call), `None`, `1`, `b"fp32"` (TypeError, `parameter == "dtype"`); `""`, `"FP32"`, `"bf-16"`, a 33-character name (ValueError, `parameter == "dtype"`). Also check that `dimensions` is refused before `dtype`, and `dtype` before `prompt`;
     - the bf16 path of every `_unfit` reason the fp32 tests already cover (not a mapping, a missing member, wrong prototype or language, wrong operand count, an operand that is not a mapping, a wrong `name`/`role`/`dtype`). A parametrized form is fine;
     - arguments are not modified (extend the existing check to a `bf16` call).
   - `tests/test_model_gemm.py`: `operands_for` (and any direct `model_binding.check` call) passes `dtype="fp32"`. Add one test that `model_gemm.run` with a binding of bf16-contract kernels returns a not-ok check with `"kernel_unfit"` and builds nothing (`execution is None`). This shows that `run` checks at `fp32`.
   - `tests/test_gemm_bf16_contract.py`: `test_module_imports_keys_only_and_is_bound_nowhere` is changed, and may be renamed, so that `hilclaw/model_binding.py` is the one module allowed (and required) to name `gemm_bf16_contract`. Follow the binder-list pattern of `tests/test_gemm_contract.py` lines 386-401. Its other assertions stay. The binder list of `tests/test_gemm_contract.py` already includes `model_binding.py` and does not change.
   - Coverage of `hilclaw/` stays at line ≥ 80% and function ≥ 80%. `pytest` and `ruff check` (and `ruff format --check` if the CI runs it) pass locally on the whole suite.
8. **No data-plane change**: no schema file, member, file, `kind` or `dtype` value, version or validator. The dtype is an in-memory argument (ADR-0157 Consequences, A-13 reading). No `ARCHITECTURE/` file changes.
9. **Process**: code mode (CLAUDE.md A-13).
   - Branch `claude/T-0432-<slug>`. Draft PR whose title contains `T-0432` and whose body's last line is `Task: T-0432`.
   - Context-isolated reviewer cycle (dev-code-review) to Approve. CI green. Then squash-merge with `gh pr merge --squash --body` carrying that body, and delete the branch.
   - `## Result` records the language (Python) and one line of reason.
   - The reviewer checks at least:
     - that `dtype` has no default and that `model_gemm` passes `fp32`;
     - that an unknown dtype gives `"invalid_input"` with no `"kernel_unfit"` or `"no_kernel"`;
     - that the selected contract, not the kernel's own contract, is the reference (ADR-0157 Alternatives (c));
     - that no fp16 contract, cast, weight check or bf16 program is added.

## Out of Scope

- ADR-0157 code slice (2): the bf16 model program (`hilclaw_gemm_bf16` over `uint16_t`), its input encoding and report, host-side build and run steps, a `dtype` argument of `model_gemm.run`, and bf16 kernel fixtures. `hilclaw/model_program.c`, `model_run.py`, `model_build.py` and `model_execute.py` are not touched.
- The weights' element-type check (ADR-0157 decision 1; goes with ADR-0153 code slice 2).
- fp16 and any other contract or kind; casts; tolerance, reference or model-level comparison.
- Any ADR or other `ARCHITECTURE/` edit, including the "less exact" sentences ADR-0157 lists.
- The PLAN "보류" items, including the T-0431 wording follow-up on ADR-0157.

## Follow-ups

- (planner) After this lands: ADR-0157 code slice (2). It covers the bf16 model program and its host-side run over `uint16_t` buffers with hand-written bf16 kernel fixtures, and then `model_gemm.run`'s `dtype` with the build-and-execute path. Split it to the size cap as ADR-0157 Consequences suggest.

## Result

- PR #253 (https://github.com/myungjoo/HIL-Claw/pull/253), squash-merged as 5a06be3 on main; branch claude/T-0432-model-binding-call-site-dtype deleted.
- Review: 2 rounds (dev-reviewer, dev-code-review). Round 1 Approve with one Low (model_gemm module docstring stated the fp32 check twice), fixed in e74cd7c; round 2 Approve, no findings.
- CI green on the final commit (Python gate 3.11/3.14, coverage, test presence, C, sh). Locally, ruff check, ruff format --check and full pytest pass (27381 passed, 927 skipped); model_binding.py and model_gemm.py at 100% line coverage.
- Change: model_binding.check takes a required keyword-only `dtype` (refusal order dimensions, dtype, prompt, ...; TypeError for a non-str, ValueError for a name outside [a-z][a-z0-9_]{0,31}, parameter "dtype"). Public DTYPES = ("fp32", "bf16"). A dtype outside it is the first "invalid_input" outcome, and no kernel_unfit or no_kernel is produced then. A dtype in range fits each entry against the contract it selects (gemm_contract / gemm_bf16_contract), and reasons name that contract. model_gemm.run passes dtype="fp32". Docstrings of model_binding, model_gemm and gemm_bf16_contract updated. No data-plane or ARCHITECTURE/ change.
- Language: Python. It extends the existing Python modules hilclaw/model_binding.py and model_gemm.py.
- Follow-ups: none new. The planner follow-up already in the task file stands: ADR-0157 code slice (2), the bf16 model program and the `dtype` of model_gemm.run.
