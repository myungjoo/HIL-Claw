---
id: T-0434
title: Let the model executor build and run a bf16 generation end to end - a dtype program flag in hilclaw/model_build, a required dtype for model_execute.execute and model_gemm.run (ADR-0157 code slice 2, part 2)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0432, T-0433]
touchesFiles: [hilclaw/model_build.py, hilclaw/model_execute.py, hilclaw/model_gemm.py, tests/test_model_build.py, tests/test_model_execute.py, tests/test_model_gemm.py]
estimatedSize: {loc: 110, files: 3}
hq: []
---
## Why

**Where things stand** (as of `main` `0819b2d`):
- ADR-0157 decides the dtype of the model executor's call sites. There is one dtype per generation. It is a model parameter with no default (decision 1). Its decision 3 table says what the dtype selects for `gemm`: the contract a kernel is fitted against, the entry point found with `dlsym`, and the element type of `a`, `b` and `c`.
- ADR-0157 code slice (1), T-0432 (PR #253): `hilclaw/model_binding.check` takes a required `dtype`. A dtype outside `model_binding.DTYPES` is the outcome `"invalid_input"`. An entry written to the other dtype's contract is `"kernel_unfit"`.
- ADR-0157 code slice (2), part 1, T-0433 (PR #254, `ed44d16`):
  - `hilclaw/model_program.c` builds as the bf16 program when compiled with `-DHILCLAW_MODEL_BF16`. That program calls `hilclaw_gemm_bf16` over `uint16_t` patterns.
  - `hilclaw/model_run` takes a required `dtype` in each of its four functions.
  - `hilclaw/model_execute` still hard-codes `dtype="fp32"` and builds only the fp32 program. `hilclaw/model_gemm.run` checks the binding with `dtype="fp32"`.
- T-0433's planner follow-up names the rest of code slice (2) as **part 2**, which is this task:
  - a `model_build` constant for the bf16 program flag;
  - a required `dtype` for `model_execute.execute`, which builds the matching program and passes the dtype to `model_run`;
  - a `dtype` for `model_gemm.run`, which passes it to `model_binding.check` and runs the bf16 path end to end with hand-written bf16 kernels.
- After this task, the executor's GEMM path runs a bf16 generation from binding check to report. That closes ADR-0157's code slices. The weights' element-type check goes with ADR-0153 code slice 2 (ADR-0157 Consequences).

**Design choices this task makes** (ADR-0157 decision 3 leaves the means to the code slice; T-0433 chose one program per dtype at compile time):
- **Where the dtype's flag lives.** `hilclaw/model_build` gets a public constant that maps each dtype to the extra program flags it needs: `PROGRAM_DTYPE_FLAGS = {"fp32": (), "bf16": ("-DHILCLAW_MODEL_BF16",)}`. Make it read-only, for example a `types.MappingProxyType`. `build_model_program` itself does not change. Its "no flag is added" stays true, and the module's flag knowledge stays in one module, next to `PROGRAM_SOURCE` and `LIBRARY_FLAGS`.
- **Who adds it.** `model_execute.execute` adds the dtype's flags **after** the caller's `program_flags`. A caller's `program_flags` item that names the macro `HILCLAW_MODEL_BF16` is refused, so the dtype stays the only way the program learns its build:
  - "names the macro" means the item contains the substring `HILCLAW_MODEL_BF16`. That covers `-DHILCLAW_MODEL_BF16`, `-UHILCLAW_MODEL_BF16` and the split form `-D` followed by `HILCLAW_MODEL_BF16`.
  - Without this refusal, `dtype="fp32"` with `-DHILCLAW_MODEL_BF16` in `program_flags` would build the bf16 program and parse its report as fp32 (a report-form failure at best). With `-UHILCLAW_MODEL_BF16` and `dtype="bf16"`, the flag comes after the `-D`, so the same thing happens in reverse.
  - This is part of making the dtype select the program (ADR-0157 decision 3). It is not general input hardening.
- **Order of checks in `execute`.** `dtype` is checked first, before `kernels`, with the same rule and messages as `model_run`: a non-`str` raises `TypeError`, and a `str` outside `model_run.DTYPES` raises `ValueError`. Both messages start with `dtype:`. The executor states these choices in one line of the commit body.

**D18.** This is a planner follow-up of T-0433 and ADR-0157, so the priority rule applies. It is needed for P2-14: the owner's goal is bf16 (HQ-0065, ADR-0154 decision 2). Until `execute` and `model_gemm.run` take a dtype, the executor cannot build or run a bf16 generation, even though the program and the binding check can. It is not input hardening, wording or a behaviour-preserving refactor, so it is not set aside.

**PLAN P2 order.** The round-loop items and P2-5 still wait on open HQs (HQ-0021, HQ-0031, HQ-0048; the P2-4 gate is owner-only OD-3). P2-10 follows P2-5. So the work continues on P2-11 to P2-14, as in T-0431 to T-0433.

**D16.** Nothing here starts `claude` or needs a board, a model file or an API key. The real-run tests build the program and hand-written kernels with the local `clang` on a POSIX machine, as `tests/test_model_gemm.py` and `tests/test_model_execute.py` already do. Loading kernels with `dlopen` is HQ-0069's runtime-acceptance item (lxvii). This task uses the same means and adds no runtime fact (ADR-0157 Consequences, "Runtime acceptance items: none").

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0434-<slug>`, commit trailer `Task: T-0434`, PR body last line `Task: T-0434`; size cap; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`:
  - decision 1 (lines 34-41);
  - decision 3, the table and its bullets (lines 49-64);
  - decision 4 (lines 66-71);
  - decision 5 (lines 73-77);
  - Consequences (lines 94-98);
  - Alternatives, row for point 5 (line 90).
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`: decisions 3 to 5 (lines 43-73), for the fixture kernel and the expected values.
- `PROCESS/tasks/T-0433-model-program-bf16-run.md`: `## Why` and `## Result` (what part 1 landed and its design choice).
- `hilclaw/model_build.py`, the whole module (130 lines).
- `hilclaw/model_execute.py`, the whole module (278 lines).
- `hilclaw/model_gemm.py`, the whole module (172 lines).
- `hilclaw/model_run.py`:
  - lines 1-75 (docstring, `DTYPES`, element dtypes);
  - lines 263-270 (`_checked_dtype`, whose rule `execute` copies).
- `hilclaw/model_binding.py`:
  - lines 1-75 (docstring, `DTYPES`);
  - lines 212-320 (`check`).
- `hilclaw/model_program.c`, the header comment, lines 1-60.
- Tests to change:
  - `tests/test_model_build.py` (301 lines), especially `test_library_flags` and `test_model_program_defaults_add_no_flag`;
  - `tests/test_model_execute.py` (592 lines): the recorder (lines 45-110), `test_happy_path_builds_in_order_runs_once_and_removes`, `test_every_model_run_function_gets_dtype_fp32`, `test_public_names_and_fields` and the real-run section from line 524;
  - `tests/test_model_gemm.py` (476 lines): helpers (lines 1-100), `test_binding_is_checked_at_fp32` and the real-run section from line 386.
- For reuse in the new real bf16 tests: `tests/test_model_run.py` lines 735-860 (the bf16 kernel sources, the `built_bf16` fixture, `bf16_of`, `bf16_matrices`).

## Acceptance Criteria

1. **`hilclaw/model_build`**:
   - Add the public read-only mapping `PROGRAM_DTYPE_FLAGS`: `"fp32"` maps to `()` and `"bf16"` to `("-DHILCLAW_MODEL_BF16",)`. Give it a one-line docstring like the other constants. Its keys equal `model_run.DTYPES` in order.
   - Do not import `model_run` from `model_build` if that makes a cycle. A test can assert the equality instead.
   - `build_kernel_library` and `build_model_program` do not change.
   - Make the docstring exact in place. It should say that the flags of a dtype are `PROGRAM_DTYPE_FLAGS`, which the caller puts in the program's flags, and that this module still adds no flag to the program build by itself. Do not add a paragraph that repeats the program's header comment.
2. **`hilclaw/model_execute.execute`** takes a required keyword-only `dtype` with no default (ADR-0157 decision 1; Alternatives, point 5):
   - `dtype` is checked first, before `kernels`. A non-`str` raises `TypeError`; a `str` outside `model_run.DTYPES` raises `ValueError`. Both messages start with `dtype:`.
   - After the existing checks of `kernels`, `calls`, `prefix`, `keep_out` and `parent`, and before anything is made, check `program_flags`:
     - it must be a `tuple` or `list` of `str`. Otherwise raise `TypeError` naming `program_flags`. Today `model_build`/`clang_build` reject this later, inside the build directory; the error now comes before the directory is made;
     - an item containing `HILCLAW_MODEL_BF16` raises `ValueError` naming `program_flags`, the position and the macro.
   - The program is built with `flags=(*program_flags, *model_build.PROGRAM_DTYPE_FLAGS[dtype])`. Kernel library builds are unchanged: no dtype flag is added to a kernel.
   - `model_run.output_shapes`, `encode_input` and `run_model_program` get `dtype=dtype`.
   - Rewrite the module docstring's sentence about the fp32 program in place: `execute` builds the program of the given dtype and hands that dtype to `model_run`. Keep "it chooses no flag" exact, for example "it chooses no flag beyond the dtype's `PROGRAM_DTYPE_FLAGS`". The `execute` docstring states `dtype`, the order of the refusals and where the dtype's flags go.
   - Nothing else in the behaviour changes. That includes the build order, the first-failure stop, the removal on every path and the `ModelExecution`/`BuildFailed` fields.
3. **`hilclaw/model_gemm.run`** takes a required keyword-only `dtype` with no default:
   - It passes `dtype` to `model_binding.check`, which does every dtype check. A dtype outside `model_binding.DTYPES` is the `"invalid_input"` outcome, and a malformed one raises what `check` raises.
   - It passes the same `dtype` to `model_execute.execute`.
   - `run` does not check `dtype` itself before `check`.
   - For `bf16`, the caller's `a` and `b` must be `numpy.uint16` bit patterns. `run` does not cast them: a `float32` array reaches `execute`, and `model_run`'s error is passed on unchanged, as the docstring already says for "an array of another dtype".
   - Rewrite the docstring sentences that say the binding is checked at `fp32` (module "Readings" bullet and `run`'s first paragraph) in place: the binding is checked at the caller's `dtype` (ADR-0157 decisions 1 and 3).
4. **No other module changes.** `hilclaw/model_binding.py`, `hilclaw/model_run.py`, `hilclaw/model_program.c`, `hilclaw/gemm_contract.py` and `hilclaw/gemm_bf16_contract.py` are not touched. There are no other callers of `execute` or `run` in `hilclaw/` (verify with a search). If one exists, it passes `dtype="fp32"`. Record that in `## Result`.
5. **Tests** (CLAUDE.md test rules ①-④; these test `hilclaw/` code, so ⑤ does not apply):
   - `tests/test_model_build.py`: `PROGRAM_DTYPE_FLAGS` has exactly the two entries and their values, has keys equal to `model_run.DTYPES`, and refuses assignment (negative). The public-name test, if any, includes it.
   - `tests/test_model_execute.py`:
     - Every existing call passes `dtype="fp32"`, and its expectations stay unchanged. The program build's flags for `fp32` equal the caller's `program_flags` exactly.
     - **Happy:** with the recorder, `dtype="bf16"` builds the program with `(*program_flags, "-DHILCLAW_MODEL_BF16")`. Kernel builds carry no such flag. Each of the three `model_run` functions gets `"bf16"`.
     - **Branch:** `program_flags=()` with `bf16` gives exactly `("-DHILCLAW_MODEL_BF16",)`. A `list` `program_flags` is accepted.
     - **Negative:**
       - a missing `dtype` gives a `TypeError` from the call;
       - `None`, `1` and `b"bf16"` give `TypeError`; `""`, `"fp16"` and `"BF16"` give `ValueError`;
       - `dtype` is refused before bad `kernels`;
       - `program_flags` items `"-DHILCLAW_MODEL_BF16"`, `"-UHILCLAW_MODEL_BF16"` and `["-D", "HILCLAW_MODEL_BF16"]` are refused with `ValueError` naming the position, at each dtype;
       - a `program_flags` that is a `str` or holds a non-`str` gives `TypeError`;
       - for all of these refusals, nothing is made: no build directory under `parent` and no recorder event;
       - `float32` arrays with `dtype="bf16"` give `model_run`'s `ValueError`, passed on unchanged, and nothing is made.
     - **Real run** (existing `clang` fixture): at least one real bf16 `execute` of two hand-written bf16 kernels over several shapes, outputs equal to the expected patterns. Plus one real bf16 `execute` whose kernel defines only `hilclaw_gemm`: it gives `run.failed` (status 6, the line naming `hilclaw_gemm_bf16`).
   - `tests/test_model_gemm.py`:
     - Every existing call passes `dtype="fp32"`, and its expectations stay unchanged. `test_binding_is_checked_at_fp32` becomes a test that `check` receives the caller's dtype, for each of `fp32` and `bf16`, and that `execute` receives the same.
     - **Negative/branch:**
       - a missing `dtype` gives a `TypeError`;
       - `dtype="fp16"` gives `check.ok` false with `"invalid_input"`, nothing built, and `operands` not looked at;
       - a bf16 call whose binding holds an fp32-contract kernel gives `"kernel_unfit"` and nothing built;
       - a malformed `dtype` (`1`) passes on what `check` raises.
     - **Real run:**
       - a bf16 binding of one hand-written bf16 kernel (its `KernelReference` contract from `gemm_bf16_contract.task_contract`) bound `"every"` at all six call sites of `SMALL`, with operands of small integers held as `uint16` patterns. Every output is `uint16` and equals the expected patterns;
       - plus a two-kernel bf16 binding (plain and plus-one at different sites), as the fp32 tests do.
   - **Expected values for bf16:** compute the `float32` product of the widened inputs (small integers, exact in `float32`) and round to nearest even to the upper 16 bits (ADR-0156 decision 4), in a test helper. Do not assume the plus-one result is exact in bf16. Reusing or copying the helpers of `tests/test_model_run.py` is fine.
   - Coverage of `hilclaw/` stays at line ≥ 80% and function ≥ 80%. `pytest`, `ruff check` and `ruff format --check` pass locally on the whole suite. If the development machine is not POSIX, run the real-run tests under a POSIX environment with `clang` (for example WSL, as T-0433 did) and say so in `## Result`. No CI file changes.
6. **No data-plane change**: no schema file, member, file, `kind` or `dtype` value, version or validator (ADR-0157 Consequences, A-13 reading). No `ARCHITECTURE/` file changes.
7. **Process**: code mode (CLAUDE.md A-13).
   - Branch `claude/T-0434-<slug>`. Draft PR whose title contains `T-0434` and whose body's last line is `Task: T-0434`.
   - Context-isolated reviewer cycle (dev-code-review) to Approve. CI green. Then squash-merge with `gh pr merge --squash --body` carrying that body, and delete the branch.
   - `## Result` records the language (Python) and one line of reason.
   - The reviewer checks at least:
     - that `dtype` has no default in `execute` and `run`, and is checked first in `execute`;
     - that the program's flags for `fp32` are exactly the caller's;
     - that the dtype flag comes after the caller's flags and no caller flag can name the macro;
     - that `run` leaves every dtype decision to `model_binding.check`;
     - that no array is cast;
     - that no fp16 path, tolerance, reference or weight check is added.

## Out of Scope

- The weights' element-type check (ADR-0157 decision 1; goes with ADR-0153 code slice 2) and anything of ADR-0153 code slice 2 (forward pass, embedding, KV cache, token selection).
- fp16, casts, tolerance, reference, model-level comparison and any widening of reported logits (OD-31 sub-questions 2, 3 and 6, owner).
- Changes to `hilclaw/model_program.c`, `hilclaw/model_run.py` or `hilclaw/model_binding.py`.
- Any ADR or other `ARCHITECTURE/` edit, including ADR-0157's "Less exact, not edited" list.
- CI workflow files.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this lands, ADR-0157's code slices are done. The next P2-13/P2-14 step is ADR-0153 code slice 2, the forward pass. It needs contracts for the other five kinds (RMSNorm, elementwise add, SwiGLU, RoPE, SDPA with KV cache) at `bf16` (PLAN P2-11, OD-31 sub-question 1; ADR-0157 decision 4). The planner checks which of those contract records exist under `ARCHITECTURE/decisions/` and plans the first missing one as an ADR task (DRIVER §9). Any part that depends on owner-only sub-questions 2, 5 or 6 goes to an HQ instead.

## Result

- Outcome: DONE. PR #255 (branch claude/T-0434-model-execute-gemm-bf16-path), squash-merged by the executor as 7c1a271 after 2 review rounds (r1 Approve + docstring line-wrap nit, fixed in 4f838f5; r2 Approve, no findings). Branch deleted.
- model_build: read-only PROGRAM_DTYPE_FLAGS (MappingProxyType; fp32 -> (), bf16 -> ("-DHILCLAW_MODEL_BF16",)), keys equal model_run.DTYPES (asserted by a test, no import). build_kernel_library/build_model_program unchanged; docstring updated in place.
- model_execute.execute: required keyword-only dtype, checked first ("dtype:" messages). program_flags must be a tuple/list of str (TypeError); an item containing HILCLAW_MODEL_BF16 is refused with its position (ValueError). Program built with (*program_flags, *PROGRAM_DTYPE_FLAGS[dtype]); no dtype flag on kernels; dtype passed to output_shapes, encode_input, run_model_program.
- model_gemm.run: required keyword-only dtype, passed to model_binding.check (all dtype decisions there) and to execute. No cast.
- Tests: Windows full suite 27477 passed, 949 skipped; ruff check/format clean; hilclaw/ coverage 97%, model_build/model_execute/model_gemm 100%. Real-run tests in WSL Ubuntu (clang, Python 3.12): 400 passed, including real bf16 execute and real bf16 model_gemm.run. CI green on 4f838f5. No CI file changed.
- Language: Python, which extends the existing numpy-based host-side modules.
- No data-plane, schema or ARCHITECTURE/ change. No fp16 path, tolerance, reference or weight check.
- Follow-ups: none new. The planner follow-up stands: ADR-0153 code slice 2, the forward pass, starting from the first missing bf16 contract record for the other five kinds.
