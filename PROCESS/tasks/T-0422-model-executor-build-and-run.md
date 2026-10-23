---
id: T-0422
title: Add the build-and-run function of the model executor - a module hilclaw/model_execute.py that makes a build directory outside both checkouts, builds each fp32 gemm kernel into a shared library and the model program, returns the named outcome build_failed for a failed build, else writes the input file and runs the program, and removes the directory (ADR-0153 code slice 1, build-and-run path; for PLAN P2-13)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-10, OD-31, "PLAN P2-13"]
dependsOn: [T-0420, T-0421]
touchesFiles: [hilclaw/model_execute.py, tests/test_model_execute.py]
estimatedSize: {loc: 200, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `1421704`):
- PLAN P2-5 cannot move: each remaining part waits on an open owner HQ (HQ-0048, HQ-0053, HQ-0021, HQ-0026, HQ-0032). P2-10 comes after P2-5.
- PLAN P2-11 and P2-12 wait on HQ-0064, HQ-0065 and HQ-0066.
- PLAN P2-13: ADR-0153 decides the model executor. Its code slice 1 is possible before those answers.
  - T-0420 (`96a186b`) landed the model program `hilclaw/model_program.c` and the build step `hilclaw/model_build.py`.
  - T-0421 (`258731c`) landed the host side's run, `hilclaw/model_run.py`: `encode_input`, `output_shapes`, `parse_report`, `run_model_program` and the outcome **run failed** (`RunFailed`).
  - T-0419 (the binding check, `hilclaw/model_binding.py`, Draft PR #244) is BLOCKED on HQ-0067.

**This task** is the candidate T-0422 named in T-0421's Follow-ups. It is the one function that does the whole build-and-run path of slice 1:
- make a build directory of its own outside both checkouts (ADR-0153 Consequences "A-13 reading");
- build each kernel into a shared library and the model program (decision 3 "Loading");
- return the named outcome **build failed** (kernel reference, compiler output) for a failed build (decision 5);
- otherwise write the input file and run the program;
- remove the directory.

**HQ-0067 reading.** HQ-0067 blocks the joining with the binding check (T-0419), not this code. This task neither reads, imports nor names `hilclaw/model_binding.py`. Its kernel argument is duck-typed: any object with the attributes `sources` and `flags`. T-0419's `KernelReference(sources, contract, flags)` has both, so a later task can hand this function the kernels of `BindingCheck.calls` without changing it. The driver accepted this reading for T-0420 and T-0421.

**D18 reading.** This is work of a PLAN checklist item (P2-13, code of ADR-0153 slice 1). The D18 hold rule does not apply (DRIVER §6).

**Not crossed.**
- **Dtype (HQ-0065, HQ-0066).** Only fp32, through `model_run.encode_input`, which refuses any other dtype and casts nothing. No accumulation, oracle, tolerance or input distribution is chosen. The module compares nothing.
- **Llama dimensions (HQ-0064).** No value of H, d_h, the KV-head count or any Llama 3.2 1B dimension is used.
- **Isolation and limits (OD-14).** No container is started, no environment chosen and no time limit given a default. The caller passes both time limits. An optional command prefix is handed to `run_model_program` unchanged, so a caller can put a container start in front.
- **Build flags (HQ-0033, HQ-0034).** No flag value is chosen. Each kernel's flags are its own `flags`. The program's flags and trailing flags (for example `-ldl`) are the caller's. `model_build.LIBRARY_FLAGS` is added by `build_kernel_library` as it is today.
- **`env` checks (HQ-0028, HQ-0029).** `env` is handed over unchanged. No new check of it.
- **Exposure.** No CLI, registry or MCP tool is added (ADR-0153 decision 1).
- **Data plane and dependencies.** No data-plane member, file, kind or version changes, and nothing is written to the data plane. No new external dependency: the standard library, `numpy`, `hilclaw.model_build`, `hilclaw.model_run` and `hilclaw.checkout_boundary` (and `hilclaw.scratch` if the executor reuses its `remove`, item 4).
- **Runtime acceptance item (lxvii).** It is to be asked "once code slice 1 has landed". Slice 1 also holds the binding check, which waits on HQ-0067. So it is not asked at the end of this task (Follow-ups).
- **D16.** No `claude` process is started.

**No open PR overlaps.**
- PR #244 touches `hilclaw/model_binding.py` and `tests/test_model_binding.py`.
- PR #186 touches `hilclaw/start_instance.py`, `tests/test_gemm_contract.py`, `tests/test_standin_profile.py` and `tests/test_start_instance.py`.
- This task must not edit any of them. It also must not edit `hilclaw/gemm_contract.py`, `hilclaw/model_program.c`, `hilclaw/model_build.py`, `hilclaw/model_run.py`, `hilclaw/scratch.py` or `hilclaw/checkout_boundary.py`.

## Required Reading

- `PROCESS/DRIVER.md` §3-5 (executor procedure, resume rule, time limit) and §5 (format, naming, size cap, test rules).
- `CLAUDE.md`: "테스트 규칙", "도구 계층 언어 정책", "코멘트 최소화", "브랜치·merge 절차" (code mode).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md`: Decision §1 (lines 28-33), §3 "Loading" (lines 40-46), §5 (lines 58-62), Consequences "A-13 reading", "Code slices" and "Runtime acceptance items" (lines 87-91, of which 89-90 are not needed), Boundaries (lines 101-115).
- `hilclaw/model_build.py` (whole file, 129 lines): `build_kernel_library`, `build_model_program`, what each raises and returns.
- `hilclaw/model_run.py`: the module docstring (lines 1-45), `RunFailed` and `ModelProgramResult` (lines 61-83), `encode_input`/`output_shapes` (lines 85-118) and `run_model_program` (lines 140-206).
- `hilclaw/clang_build.py` lines 43-61: `BuildResult` (`ok`, `log` is the compiler output).
- `hilclaw/checkout_boundary.py` (whole file, 56 lines): `PACKAGE_DIRECTORY`, `refuse_one_path`, `meets_checkout`.
- `hilclaw/scratch.py`: lines 14-27 (the "outside both checkouts" convention), `create` (lines 113-146), `remove` (lines 149-177), `_refuse_inside_checkout` (lines 193-203) and `_remove` (from line 252). These are the pattern for the parent check, the directory made by `tempfile.mkdtemp` and a removal that follows no link.
- `tests/test_model_run.py` lines 25-55 (the `matrices` helper) and lines 408-525: the hand-written kernels and the session fixture pattern (skip on non-POSIX; when clang is missing, skip locally and fail on CI).
- `tests/test_gemm_contract.py` lines 386-396: the text `gemm_contract` must not appear in any new `hilclaw/*.py` file, docstrings included.

## Acceptance Criteria

The names below are this task's. The executor may rename them only if the review asks, and records any rename in Result.

1. **Module `hilclaw/model_execute.py`** (Python; the language-choice line goes in Result and the commit body).
   - Its boilerplate docstring names ADR-0153 (decision 3 "Loading", decision 5 and Consequences "A-13 reading") and the two modules it joins, `hilclaw.model_build` and `hilclaw.model_run`.
   - It lists what the module does not do: no binding check and no fit check; no container or environment; no time limit default; no flag chosen; no comparison, reference or tolerance; no cast; nothing stored, kept or retried; nothing written outside the build directory.
   - The docstring must not contain the text `gemm_contract` or `model_binding`.
2. **`execute(kernels, calls, *, build_timeout_s, run_timeout_s, program_flags=(), program_trailing_flags=(), compiler=None, env=None, prefix=(), parent=None, keep_out=())` returns a `ModelExecution`.**
   - **`kernels`** is a non-empty sequence (not a `str`/`bytes`) of objects that have the attributes `sources` and `flags`. Kernel `i` is library `i` of the program's command line, the kernel index of `calls`.
   - **`calls`** is the argument of `model_run.encode_input`, checked by `model_run.output_shapes`. In addition, every call's index must be < `len(kernels)`.
   - **`prefix`** is a sequence (default empty) placed in front of the built program's path. With an empty `prefix`, `run_model_program` gets the program's path as `program`. Otherwise it gets the command prefix `(*prefix, program path)`.
   - **`parent`** is the existing directory the build directory is made in (`None`: `tempfile.gettempdir()`). It must not be or lie inside a checkout per `checkout_boundary.meets_checkout(real path, keep_out, containing=False)`. `keep_out` is a sequence of paths. A `keep_out` that is one path raises `TypeError` (`checkout_boundary.refuse_one_path`).
   - **Refusals before anything is made**, with a message that names the argument (and the position for an entry):
     - `TypeError` for `kernels` not a sequence, an entry without `sources` or `flags`, a `prefix` not a sequence, a `parent` that is not `str`/`os.PathLike` of `str`, or a `keep_out` that is one path;
     - `ValueError` for no kernels, a call index ≥ `len(kernels)`, or a `parent` inside a checkout;
     - whatever `encode_input`/`output_shapes` raise for `calls`, passed on unchanged.
3. **Steps, in this order, after the checks.**
   1. Make the build directory with `tempfile.mkdtemp` under `parent`, with a fixed name prefix (a module constant, for example `"hilclaw-model-"`).
   2. Build kernel 0, 1, … in order with `model_build.build_kernel_library(kernel.sources, <directory>/<library name i>, timeout_s=build_timeout_s, flags=kernel.flags, compiler=compiler, env=env)`. The library names are fixed by the module and distinct per index.
   3. Build the program with `model_build.build_model_program(<directory>/<program name>, timeout_s=build_timeout_s, flags=program_flags, trailing_flags=program_trailing_flags, compiler=compiler, env=env)`.
   4. **The first build whose `BuildResult.ok` is false stops the path.** Nothing after it is built and nothing is run. The result has `build_failed = BuildFailed(kernel, build)`, where `kernel` is the kernel's index (`int`) or `None` for the program, and `build` is that `BuildResult` (its `log` is the compiler output).
   5. Otherwise write `encode_input(calls)` to an input file in the directory. Call `model_run.run_model_program(program, input file, library paths in index order, shapes=output_shapes(calls), timeout_s=run_timeout_s, env=env)`. `cwd` is not passed: every path the module hands over is absolute.
   6. **Remove the directory** on every path once it has been made: after a failed build, after the run, and when any step raises (the exception then reaches the caller after the removal). The removal follows no symbolic link or junction and raises nothing on failure. The executor may reuse `hilclaw.scratch.remove(directory, keep_out=keep_out)` or write its own; Result records which.
4. **`ModelExecution`** is a `NamedTuple` `(build_failed, run, removed)`:
   - `build_failed` is `None` or a `BuildFailed` `NamedTuple` `(kernel, build)` (ADR-0153's "build failed"; the spelling is this slice's);
   - `run` is `None` when a build failed, else the `model_run.ModelProgramResult` as returned (its `failed` carries **run failed**);
   - `removed` is whether the build directory no longer exists afterwards.
   - What `model_build`, `clang_build` or `local_run` raise is passed on unchanged, after the removal.
5. **Tests `tests/test_model_execute.py`**, in two groups.
   - **Without a compiler or a process** (run on every platform). `model_build.build_kernel_library`, `model_build.build_model_program` and `model_run.run_model_program` are replaced by recorders as seen from the module. Use `tmp_path` as `parent` (pytest's temporary directory lies outside the repository; if a platform puts it inside, skip that test with a reason). The tests check:
     - **happy**: the exact build calls in order (kernel sources, flags, `LIBRARY_FLAGS` not added by this module, timeouts, `compiler`, `env`), the program build's flags and trailing flags, the run call (absolute paths inside one new directory below `parent`, libraries in index order, `shapes`, `run_timeout_s`, `env`), the input file's bytes equal `encode_input(calls)` at the moment of the run, the `ModelExecution` fields, and the directory gone afterwards with `removed` true;
     - **prefix**: an empty and a non-empty `prefix` give `program` as a path and as `(*prefix, path)`;
     - **build failed**: a failed kernel build (index 1 of 3) stops before kernel 2 and the program, with no run, `BuildFailed(1, that result)` and the directory removed; a failed program build gives `BuildFailed(None, …)`;
     - **run failed passed through**: a recorder returning a `ModelProgramResult` with `RunFailed.TIMEOUT` is returned as `run` unchanged;
     - **exception path**: a recorder that raises (for example `clang_build.CompilerNotFoundError`, or an `OSError` from the run) reaches the caller and the directory is still removed;
     - **negative**: every `TypeError`/`ValueError` of item 2, each with no directory made below `parent` and no recorder called. Among them: an empty `kernels`, a `str` as `kernels`, an entry without `flags`, an index equal to `len(kernels)`, a `float64` array in `calls`, a `parent` inside the repository (for example `checkout_boundary.PACKAGE_DIRECTORY`), a `parent` named in `keep_out`, and a `keep_out` given as one path;
     - the public names (`execute`, `ModelExecution`, `BuildFailed` and any public constant) and their fields.
   - **With real clang** (POSIX only, the fixture pattern of `tests/test_model_run.py`; the kernels are small `SimpleNamespace` or `NamedTuple` objects with `sources` and `flags`, the sources written to `tmp_path`):
     - **happy**: two kernels with different results ("plain" and "plus one") and several calls of different shapes. The outputs equal the `numpy` products computed in the test from small-integer inputs (exact in `float32`, no tolerance), and the build directory is gone;
     - **build failed**: a kernel source with a syntax error gives `BuildFailed` with its index, a non-empty `build.log`, `run` `None`, and the directory gone;
     - **run failed**: an index valid for the host but a library without `hilclaw_gemm` gives `run.failed` `RunFailed.EXIT_STATUS` with status 6.
6. CLAUDE.md test rules hold:
   - package line and function coverage ≥ 80%, ruff clean (`ruff check .` and `ruff format --check .`), and a test file for the new module;
   - every public function of the module is tested; local `pytest` passes;
   - if the local machine has no POSIX clang (native Windows), the clang tests skip locally and must pass on CI;
   - CI must be green before the self squash-merge.
   - DRIVER §5 naming applies: branch `claude/T-0422-<slug>`, PR title with `T-0422`, and `Task: T-0422` as the last line of the PR body.

## Out of Scope

- The binding check, `hilclaw/model_binding.py`, the fit of a kernel's contract, joining with `BindingCheck.calls`, and anything of HQ-0067 or PR #244.
- Weights, the embedding lookup, buffers across calls, the KV cache, passes, the generation loop, token selection, and kinds other than fp32 `gemm` (ADR-0153 slice 2; P2-11).
- The container of ADR-0144, time or memory limits as values (OD-14), and build flag values (HQ-0033, HQ-0034).
- Any edit to `hilclaw/model_program.c`, `hilclaw/model_build.py`, `hilclaw/model_run.py`, `hilclaw/scratch.py`, `hilclaw/checkout_boundary.py` or `hilclaw/gemm_contract.py`. A docstring that becomes less exact, for example the module list of `checkout_boundary`, is named in Result's follow-ups and not edited.
- Edits to `ARCHITECTURE/`, `tests/test_gemm_contract.py` and the files of PR #186.

## Follow-ups

- After HQ-0067 is answered and T-0419 lands: a task that joins the binding check with this function. That task runs `model_binding.check`, and when the check is ok it turns `BindingCheck.calls` into the kernel list and the call indices of `execute`. Its arrays are supplied by the caller or the test.
- Runtime acceptance item (lxvii) of ADR-0153 (the program is built with its kernels' shared libraries and loads them with `dlopen` in the isolated environment of OD-14) is to be asked once code slice 1 has landed, that is, after the joining task above. It is not asked at the end of this task.

## Result

- **Outcome**: DONE. PR #247 (branch `claude/T-0422-model-executor-build-and-run`), squash-merged by the executor as `1f66b3c` after 2 review rounds (round 1: Approve with one Low nit, addressed; round 2: Approve, no findings). CI green at the reviewed head `ba0a495` (C gate, Coverage gate, Python 3.11/3.14, Test presence, sh gate).
- **Change**: `hilclaw/model_execute.py` (new, 275 lines) and `tests/test_model_execute.py` (new). No other file. Names are those of the task; no rename. `PREFIX` (`"hilclaw-model-"`) is the one public constant; the library, program and input file names are private.
- **Language**: Python, because the host side joins the Python modules `hilclaw.model_build` and `hilclaw.model_run` and hands `numpy` arrays to the latter (ADR-0153 decision 2).
- **Executor choices**: the removal reuses `hilclaw.scratch.remove(directory, keep_out=keep_out)`; its `InvalidScratchArgumentError` (for example a directory replaced by a link) is caught and shows as `removed` false, so the removal raises nothing. Checks run in the order kernels, calls (`output_shapes`), call index bound, prefix, keep_out, parent. `kernels`, `prefix` and `keep_out` must be `collections.abc.Sequence` (an iterator is refused with `TypeError`). Every path of `prefix`, `keep_out` and `parent` must be `str` or `os.PathLike` whose `os.fspath` is `str` (`TypeError`) and, after review round 1, hold no NUL character (`ValueError` naming the argument). A kernel's `flags` type is checked only by `build_kernel_library`, after the directory was made; the directory is still removed and the error passed on. A missing `parent` raises the `FileNotFoundError` of `tempfile.mkdtemp`, before anything is made.
- **Local runs**: native Windows full `pytest`: 26733 passed, 910 skipped (clang tests skip); `hilclaw/` coverage 97%; `hilclaw/model_execute.py` 100% line and branch; `ruff check .` and `ruff format --check .` clean. Under WSL with clang and Python 3.12, `tests/test_model_execute.py`, `tests/test_model_run.py`, `tests/test_model_build.py` and `tests/test_model_program.py` passed (247).
- **Follow-ups**: as listed (joining task after HQ-0067 and T-0419; runtime acceptance item (lxvii) after that). Less exact, not edited: the module docstring of `hilclaw/checkout_boundary.py` lists only `hilclaw.scratch` and `hilclaw.selfcheck_session` as its users; `hilclaw.model_execute` now uses it too.
