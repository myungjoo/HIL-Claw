---
id: T-0428
title: Join the model executor's binding check with its build-and-run path - a function that checks a GEMM binding against a generation and, when the check is ok, builds the bound kernels once each and runs one call per checked (call site, shape) with caller-given arrays (ADR-0153 code slice 1, joining; PLAN P2-13)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-9, FR-10, OD-31, "PLAN P2-13"]
dependsOn: [T-0419, T-0422]
touchesFiles: [hilclaw/model_gemm.py, tests/test_model_gemm.py]
estimatedSize: {loc: 170, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `ea382db`):
- ADR-0153 (the model executor, OD-31 sub-question 4 in part) names two code slices in its Consequences. Slice 1 is "the host side's binding checks and outcomes, and the build and loading of fp32 `gemm` kernels as shared libraries called by a model program through ADR-0008's prototype, tested with hand-written kernels".
- Three parts of slice 1 have landed. None of them uses another:
  - `hilclaw/model_binding.py` (T-0419): `check` returns a `BindingCheck`. It carries the outcomes `invalid_input`, `no_kernel` and `kernel_unfit`, and, when ok, `calls` = `(call_site, shape, kernel)` for every distinct shape of each call site of a generation.
  - `hilclaw/model_execute.py` (T-0422): `execute(kernels, calls, ...)` builds each kernel into its own shared library, builds the model program, runs `calls` = `(index, a, b)` once and removes its build directory. Its outcomes are **build failed** (`BuildFailed`) and **run failed** (`ModelProgramResult.failed`).
  - `hilclaw/model_build.py`, `hilclaw/model_run.py` and `hilclaw/model_program.c` (T-0420, T-0421).
- The follow-ups of T-0422 and T-0423 name the missing piece. A function runs `model_binding.check` and, when the check is ok, turns `BindingCheck.calls` into the kernel list and the call indices of `execute`. Its arrays are supplied by the caller or the test. With it, slice 1's five outcomes of ADR-0153 decision 5 come from one call.
- The driver asks runtime acceptance item (lxvii) of ADR-0153 only after this joining lands (T-0422 Follow-ups).

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 have no part that can be taken now:
- round 0's board step waits on HQ-0021;
- the round >= 1 steps and P2-6/P2-7 wait on HQ-0048 and HQ-0031;
- the gate half of P2-4 is owner-only (OD-3);
- P2-5's start entry has landed (T-0427), and its run needs the round steps above.

P2-10 comes after P2-5. The next stage is P2-11 to P2-14. Within it, the T-0427 planner named this joining task as the candidate. It finishes a slice that a recorded decision describes and that has already started, before slice 2 and the next P2-11 contract records. This is slice work of ADR-0153, which P2-13 and so P2-14 need. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, D16.** ADR-0153 decides what this task needs. What the record leaves to the code slice is this task's choice, not an owner decision: the spelling of the outcomes, and how a slice-1 caller supplies arrays before slice 2's forward pass exists. Nothing here touches HQ-0064/0065/0066 (dims are parameters, fp32 only) or any data-plane file. The real test builds with clang on a POSIX machine, as `tests/test_model_execute.py` already does. No `claude`, container, board or API key is used or required.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming convention, size cap, the D12 test rules).
- `CLAUDE.md`: "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode), "테스트 규칙", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`:
  - lines 24-69 (decisions 1 to 6, in particular decision 3 "The binding", "Fit", "Loading", decision 5 with its five outcomes and "No fallback", and decision 6 on hand-written kernels);
  - line 88 (Consequences, code slices).
- `hilclaw/model_binding.py`: lines 1-108 (module docstring, constants, `ModelDimensions`, `KernelReference`, `BindingEntry`, `Outcome`, `BindingCheck`) and lines 166-291 (`generation_calls`, `check`).
- `hilclaw/model_execute.py` lines 1-158 (module docstring, `BuildFailed`, `ModelExecution`, `execute` and its argument checks).
- `hilclaw/model_run.py` lines 54-207 (`RunFailed`, `ModelProgramResult`, `encode_input`, `output_shapes`, `run_model_program`).
- `tests/test_model_execute.py`:
  - lines 1-110: the `Recorder` fixture that replaces the builds and the run;
  - lines 453-568: the public-names test, the hand-written `PRODUCT` kernel sources, the `clang` fixture (skips off POSIX or without clang, fails on CI without clang) and the real builds.
- `tests/test_model_binding.py` lines 1-60 (`SMALL` dimensions, the `kernel` and `every_binding` helpers built from `gemm_contract.task_contract`).
- `tests/test_gemm_contract.py` lines 386-400: no module under `hilclaw/` other than the four listed binders may contain the text `gemm_contract`.

## Acceptance Criteria

1. **Module `hilclaw/model_gemm.py`** (Python, because it joins the Python modules `hilclaw.model_binding` and `hilclaw.model_execute` and hands `numpy` arrays on, per ADR-0153 decision 2; give the reason in one line of the commit body and of Result). Its public names:
   - **`GemmRun`**, a `NamedTuple` with these fields:
     - `check`: the `model_binding.BindingCheck` as `check` returned it;
     - `calls`: a tuple of `(call_site, shape, index)` in program order, where `index` is the kernel's position in the kernel list. It is empty when the check is not ok;
     - `execution`: the `model_execute.ModelExecution` as `execute` returned it, or `None` when the check is not ok.
   - **`run(dimensions, binding, operands, *, prompt, generation_length, lm_head_rows, given=None, build_timeout_s, run_timeout_s, program_flags=(), program_trailing_flags=(), compiler=None, env=None, prefix=(), parent=None, keep_out=())`** returns a `GemmRun`. In order:
     1. It calls `model_binding.check(dimensions, binding, prompt=..., generation_length=..., lm_head_rows=..., given=...)`. What `check` raises is passed on unchanged.
     2. If the check is not ok, it returns `GemmRun(check, (), None)`. Nothing is built, nothing is started, no directory is made and `operands` is not looked at.
     3. If the check is ok, it builds the **kernel list**: the distinct kernels of `check.calls` in order of first use. Two kernel references that compare equal (`==`) are one kernel and get one library. This reading of ADR-0153 decision 3 ("a shared library of its own" per kernel) goes into the module docstring.
     4. It builds the **program calls**: one `(index, a, b)` per entry of `check.calls`, in that order, where `(a, b) = operands[(call_site, shape)]`.
     5. It calls `model_execute.execute(kernels, program_calls, ...)` and hands every keyword above on unchanged. It returns `GemmRun(check, calls, execution)`.
   - **`operands`** is a `collections.abc.Mapping` from `(call_site, shape)` to a pair `(a, b)`. `shape` is the `(m, k, n)` tuple of `check.calls`. When the check is ok, these are refused before `execute` is called, with nothing made:
     - a missing key;
     - a key that is not among the calls of the check;
     - a value that is not a pair;
     - an array whose `shape` attribute is not `(m, k)` for `a` or `(k, n)` for `b`.

     A non-mapping `operands` is refused with `TypeError`; choose whether that happens before or after the check, and state it. A dtype other than `float32`, a non-2-D array or a non-`ndarray` reaches `execute`, and its error from `model_run` is passed on unchanged. Choose `TypeError` or `ValueError` per case, state it in the docstring, and make every message name the key.
   - **Outcomes** (ADR-0153 decision 5). A caller tells the five apart from the returned value alone:
     - `invalid_input`, `no_kernel`, `kernel_unfit`: `check.ok` is false, with its `outcomes`;
     - **build failed**: `execution.build_failed`. Its `kernel` index maps back through `calls` to the call sites that use it;
     - **run failed**: `execution.run.failed`.

     When the run succeeded, `execution.run.outputs[i]` is the output of `calls[i]`. The module docstring states this mapping.
   - **Does not**:
     - no fallback and no NumPy product in place of a kernel (decision 5);
     - it chooses no array, weight, dtype, cast, reference or tolerance; computes nothing from `dimensions` except through `model_binding`; compares nothing;
     - no forward pass, embedding, KV cache or token selection (slice 2);
     - no file outside `execute`'s build directory, no data-plane file, no registry entry, MCP name or command-line entry, no `__main__`.
     - Arguments are not modified.
   - The text `gemm_contract` does not appear in `hilclaw/model_gemm.py`. `tests/test_gemm_contract.py` limits that text to its listed binders; this module reaches the contract only through `model_binding`.
   - **Within the D4 cap**: about 170 LOC of non-test change in 1 non-test file. No change to `hilclaw/model_binding.py`, `hilclaw/model_execute.py`, `hilclaw/model_run.py`, `hilclaw/model_build.py` or `hilclaw/model_program.c`.

2. **Tests `tests/test_model_gemm.py`** (CLAUDE.md "테스트 규칙", DRIVER §5 D12). Tests may import `hilclaw.gemm_contract` to build valid contracts, as `tests/test_model_binding.py` does. No `claude`, no stub `claude`, no container, no board, no network.
   - **Recorded path** (replace `hilclaw.model_execute.execute` by a recorder, with `monkeypatch`):
     - With an "every" binding of six distinct kernels over `SMALL`-like dimensions and generation length > 1, `execute` gets six kernels in first-use order, and program calls in `check.calls` order with the right indices and the exact operand objects. Every keyword is handed on unchanged, and `GemmRun.calls` matches.
     - One kernel reference bound at several call sites, or two equal references, gives one kernel and shared indices.
     - Several entries of one call site with disjoint listed shapes give distinct indices per shape.
     - `generation_length` 1 and `lm_head_rows` `"last"` give the expected fewer calls.
   - **Check not ok**: `invalid_input` (a prompt token outside the vocabulary), `no_kernel` (a listed binding missing the decode shape) and `kernel_unfit` (a wrong contract) each give `execution` `None` and `calls` `()`. In each case the recorder is not called, even when `operands` is empty or malformed in a way only looked at after the check.
   - **Errors passed on**: a malformed binding (the `ValueError` of `check` with `parameter` `"binding"`) and a wrong `dimensions` type each reach the caller, and `execute` is not called.
   - **Operand refusals** (negative): each case of criterion 1 has its own test, with the exception type, the key named in the message, and `execute` not called:
     - missing key; extra key; non-pair value; wrong `a` shape; wrong `b` shape; a non-mapping `operands`.
     - A `float64` array reaches the real `execute` path and raises its `model_run` error, with nothing left in `parent`.
   - **Outcomes through the recorder**:
     - a recorded `BuildFailed` and a recorded run failure are returned unchanged inside `GemmRun.execution`;
     - an exception raised by `execute` reaches the caller.
   - **Arguments not modified**: `binding`, `operands`, `prompt` and `given` deep-compare equal before and after a run.
   - **Real builds** (the `clang` fixture pattern of `tests/test_model_execute.py`: skip off POSIX or without clang, fail on CI without clang; `program_trailing_flags=("-ldl",)`; `parent` under `tmp_path`):
     - (a) Small dimensions; a hand-written `PRODUCT`-style kernel source with a `task_contract` contract bound `"every"` at all six call sites; integer-valued `float32` operands from a seeded generator for every checked `(call_site, shape)`. Every output equals `a @ b` exactly. `execution.removed` is true and `parent` is empty.
     - (b) Two different hand-written kernels at different call sites (for example `plain` and `plus_one`). Each output matches its own kernel.
     - (c) A broken kernel source gives build failed with the index of that kernel.
   - **Public names**: the module's public names beyond what it imports are exactly `GemmRun` and `run`, and `GemmRun._fields == ("check", "calls", "execution")`. The module text contains neither `gemm_contract` nor `__main__`.
   - **Coverage**: `hilclaw/` line coverage >= 80% and function coverage >= 80% stay met. `hilclaw/model_gemm.py` is fully or nearly fully covered on a runner with clang. `tests/test_gemm_contract.py`, `tests/test_model_binding.py` and `tests/test_model_execute.py` pass unchanged.
   - No test of test code, CI or hooks is added (D12 ⑤).

3. **Local gates**:
   - `python -m ruff check .`, `python -m ruff format --check .` and `python -m pytest` pass.
   - On a machine without clang or POSIX, the real-build tests skip locally. Run them where clang is available (for example WSL) if you can, and say in Result where they ran. CI runs them.

4. **Procedure** (dev-item-address, code mode):
   - Work on branch `claude/T-0428-model-gemm-run-joining`.
   - Open a Draft PR whose title contains `T-0428` and whose body ends with `Task: T-0428`.
   - Run the isolated reviewer cycle (dev-code-review) to Approve, at most 7 rounds.
   - Wait for CI green, then squash-merge with `gh pr merge --squash --body` carrying the PR body, and delete the branch.
   - Result records the PR, the merge commit, the review rounds, the language reason, and the choices made for what criterion 1 leaves open: operand error types, the moment of the `operands` type check, and the kernel-equality reading.

5. **Stop conditions.** Return BLOCKED with the reason, and do not work around it, if any of these holds:
   - the joining needs a change to `model_binding`, `model_execute`, `model_run`, `model_build` or `model_program.c`;
   - it needs the text `gemm_contract` in the new module, or an edit to `tests/test_gemm_contract.py`;
   - it needs a value of HQ-0064, HQ-0065 or HQ-0066 (a head count, a dtype other than fp32, a cast, a reference or a tolerance);
   - it needs a new external dependency or any data-plane member, file or kind.

## Out of Scope

- ADR-0153 slice 2: the forward pass, embedding, the copies between kernels, the KV cache, the generation loop, the token selection, and the other five kinds (RMSNorm, RoPE, SDPA, SwiGLU, add), which wait on P2-11 contract records.
- Accepting `numpy` integer token ids in `model_binding.check` (T-0419 reviewer Info). That belongs with slice 2's host side.
- How the executor is offered: a command-line entry, a registry or MCP tool, or a runtime caller (ADR-0153 decision 1, open).
- Deriving a binding from a key's best (OD-20, OD-7).
- Any edit to `ARCHITECTURE/`, `README.md`, or the docstrings of other modules, including the `hilclaw/checkout_boundary.py` docstring, which is already a D18 hold line.
- Asking runtime acceptance item (lxvii). The driver does that after this task lands.

## Follow-ups

- (driver) After this lands, ADR-0153 code slice 1 is complete. Record runtime acceptance item (lxvii) of ADR-0153 as an HQ with reason `runtime-acceptance` (DRIVER §8, `taskId` T-0428). The item: the program is built with its kernels' shared libraries and loads them with `dlopen` in the isolated environment OD-14 gives the model program on each kind of machine of C-7.
- (planner) Next under P2-11 is the first contract record of a further kind, in fp32 or in bf16 per ADR-0154. Choose the order in that task's Why, unless an HQ answer reopens a round-loop item first.

## Result
