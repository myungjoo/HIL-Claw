---
id: T-0433
title: Let the model program and its host-side run carry a bf16 generation - hilclaw_gemm_bf16 over uint16_t in a bf16 build of model_program.c, and a required dtype in hilclaw/model_run (ADR-0157 code slice 2, part 1)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-10, OD-31, "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0431, T-0432]
touchesFiles: [hilclaw/model_program.c, hilclaw/model_run.py, hilclaw/model_execute.py, hilclaw/model_build.py, tests/test_model_program.py, tests/test_model_run.py, tests/test_model_execute.py]
estimatedSize: {loc: 130, files: 4}
hq: []
---
## Why

**Where things stand** (as of `main` `16c86c8`):
- ADR-0156 defines the bf16 `gemm` contract on `cpu_standin`. The entry point is `hilclaw_gemm_bf16` over `uint16_t` bit patterns (decision 5).
- ADR-0157 decides the dtype of the model executor's call sites. There is one dtype per generation, and it is a model parameter with no default. Its decision 3 table says what the dtype selects for `gemm`: the entry point found with `dlsym` (`hilclaw_gemm` or `hilclaw_gemm_bf16`), and the element type of `a`, `b` and `c` in the model program (`float` or `uint16_t`). The report holds lm_head's output in that element type.
- T-0432 (PR #253, `5a06be3`) landed ADR-0157 code slice (1). `hilclaw/model_binding.check` takes `dtype`, and `hilclaw/model_gemm.run` passes `dtype="fp32"`.
- ADR-0157 Consequences, code slice **(2)**: "the model program and its host-side build and run steps for bf16: `hilclaw_gemm_bf16` over `uint16_t` buffers, the input encoding and report of 16-bit patterns, with hand-written bf16 kernel fixtures; split to the size cap if needed (for example the program and its run first, the build and execution path second)." This task is the **first part**: the program and its run. The build and execution path (`model_build` flag constant, a `dtype` for `model_execute.execute` and `model_gemm.run`) is the second part.
- Today `hilclaw/model_program.c` finds only `hilclaw_gemm` and passes `float` arrays. `hilclaw/model_run` encodes and parses only `float32`.

**The design choice this task makes** (ADR-0157 decision 3 and Boundaries leave it to the code slice: "an indicator in its input, or one program per dtype"): **one program per dtype, chosen at compile time**. The same source `model_program.c` builds the fp32 program when the macro `HILCLAW_MODEL_BF16` is not defined, unchanged in every byte of behaviour. It builds the bf16 program when the macro is defined (`-DHILCLAW_MODEL_BF16`).
- Reason: the program loads every library (and so must know the symbol) **before** it reads the input file. That order is stated in its header comment, and it keeps a library error ahead of any input work. An indicator in the input would reverse that order and change the fp32 input format, which every existing caller and test uses.
- The executor states this reason in one line of the commit body.

**D18.** This is a planner follow-up of T-0432 and ADR-0157, so the priority rule applies. It is needed for P2-14: the owner's goal is bf16 (HQ-0065, ADR-0154 decision 2). The executor cannot call a bf16 kernel at all until the program can find `hilclaw_gemm_bf16` and pass 16-bit buffers. It is not input hardening, wording or a behaviour-preserving refactor, so it is not set aside.

**PLAN P2 order.** The round-loop items and P2-5 still wait on open HQs (HQ-0021, HQ-0031, HQ-0048; the P2-4 gate is owner-only OD-3). P2-10 follows P2-5. So the work continues on P2-11 to P2-14, as in T-0431 and T-0432.

**D16.** Nothing here starts `claude` or needs a board, a model file or an API key. The tests build the program and hand-written kernels with the local `clang` and run them on the development machine, as `tests/test_model_program.py` already does (HQ-0069 is the runtime-acceptance item for loading kernels with `dlopen`. This task uses the same means and does not add a runtime fact).

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0433-<slug>`, commit trailer `Task: T-0433`, PR body last line `Task: T-0433`; size cap; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙".
- `ARCHITECTURE/decisions/ADR-0157-od31-executor-call-site-dtype.md`:
  - decision 1 (lines 34-41);
  - decision 3, the table and its three bullets (lines 49-64);
  - decision 4 (lines 66-71);
  - Consequences, code slice (2) (line 97);
  - Boundaries, "The binary form" (line 116).
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`:
  - decision 2 (lines 37-42, the bit layout);
  - decisions 3 and 4 (lines 43-58, fp32 accumulation and the round-to-nearest-even conversion, for the fixture kernel);
  - decision 5 (lines 59-73).
- `ARCHITECTURE/decisions/ADR-0153-od31-model-executor.md` decision 3 (lines 40-47) and decision 5 (lines 58-63).
- `hilclaw/model_program.c`, the whole file (286 lines).
- `hilclaw/model_run.py`, the whole module (294 lines).
- `hilclaw/model_execute.py` lines 1-40 (docstring) and 93-210 (`execute`, `_build_and_run`).
- `hilclaw/model_build.py` lines 1-25 (docstring).
- Tests to change:
  - `tests/test_model_program.py` (383 lines), especially the fixture `built` and the helpers at lines 1-150;
  - `tests/test_model_run.py` (523 lines), especially the helpers at lines 1-130 and the real-run section from line 408;
  - `tests/test_model_execute.py`: the recorder around lines 60-110 and every call that checks `encode_input`, `output_shapes` or `run_model_program`.

## Acceptance Criteria

1. **`hilclaw/model_program.c` builds as either program from one source** (ADR-0157 decision 3):
   - Without `HILCLAW_MODEL_BF16` defined, its behaviour, command line, input file, report and exit statuses are unchanged. Every existing test in `tests/test_model_program.py` and `tests/test_model_run.py` passes without changes to its expectations.
   - With `HILCLAW_MODEL_BF16` defined:
     - it finds `hilclaw_gemm_bf16` with `dlsym`, through a function pointer type that matches the ADR-0156 decision 5 prototype;
     - every element of the input file and of the report is a `uint16_t` (a bf16 bit pattern) in host byte order. The integers stay `uint64_t`;
     - every element of `c` is set to `0x7FC0` (a bf16 NaN) before the call;
     - a complete report is the sum of `2*m*n` bytes over the calls plus the end mark;
     - a library without the symbol is status 6, and the line names `hilclaw_gemm_bf16`.
   - The size checks (input arrays, an output that does not fit `size_t`) use the element size of the build.
   - Keep the static size assertions, and add one for `uint16_t` if useful. Use conditional compilation in as few places as possible, for example one block that defines the element type, the symbol name, the NaN pattern and the function pointer type.
   - The header comment states both builds in place: the macro, the symbol, the element type and the NaN pattern of each, and the report length in element bytes. It also says that the macro is the only way the program learns its dtype. Rewrite sentences that now say only `float` or only `hilclaw_gemm`. Do not add a second block comment.
   - Only the C library and POSIX.1-2008 are used, as now.
2. **`hilclaw/model_run` takes the dtype explicitly**:
   - Add a public constant `DTYPES = ("fp32", "bf16")`. The element dtype of an array is `numpy.float32` for `fp32` and `numpy.uint16` for `bf16`.
   - `encode_input`, `output_shapes`, `parse_report` and `run_model_program` each take a required keyword-only argument `dtype`, with no default (ADR-0157 decision 1: never assumed; Alternatives row for point 5).
   - In each function, `dtype` is checked **first**, before anything else. A non-`str` raises `TypeError`, and a `str` outside `DTYPES` raises `ValueError`. Both messages start with `dtype:`.
   - `encode_input` and `output_shapes` require every `a` and `b` to have exactly the element dtype of `dtype`. A `float32` array in a `bf16` call, or a `uint16` array in an `fp32` call, is a `ValueError` that names the position, the array and both dtypes. No array is cast or reinterpreted.
   - The bytes are the same layout, with elements of 4 or 2 bytes.
   - `parse_report` and `run_model_program` compute the complete-report length from the shapes and the element size of `dtype`. They return fresh arrays of the element dtype of `dtype` (`uint16` patterns for `bf16`; ADR-0157 decision 3, "The report"). A NaN pattern passes through unchanged.
   - `ModelProgramResult`'s docstring and the module docstring say this. The module docstring's "it casts no array to another dtype" stays true. The docstring states that `run_model_program` does not know which build of the program it starts, and that the caller passes the dtype that matches it.
3. **`hilclaw/model_execute` passes `dtype="fp32"`** to `model_run.output_shapes`, `model_run.encode_input` and `model_run.run_model_program`.
   - Its signature and behaviour do not change. A `dtype` argument for `execute` belongs to the second part.
   - Its docstring says, in one sentence, that it runs the fp32 program (the program built without `HILCLAW_MODEL_BF16`).
4. **`hilclaw/model_build`**: in the docstring, only the sentence that says the program "calls its `hilclaw_gemm`" is made exact. It should say that the program calls `hilclaw_gemm`, or `hilclaw_gemm_bf16` when built with `-DHILCLAW_MODEL_BF16` in the caller's flags. No code changes. "Chooses no flag beyond `LIBRARY_FLAGS`" stays true.
5. **Tests** (CLAUDE.md test rules ①-④; these test `hilclaw/` code, so ⑤ does not apply):
   - `tests/test_model_program.py`:
     - Build a second, bf16 program with `flags=("-O2", "-DHILCLAW_MODEL_BF16")`. It is fine to extend the session fixture.
     - Add hand-written bf16 kernel sources defining `hilclaw_gemm_bf16`. Use at least these: one that widens each pattern to `float` by a 16-bit shift, accumulates in `float` and rounds to nearest even back to a pattern (ADR-0156 decisions 3 and 4); one that adds 1 to that result, for two-kernels-stay-apart; and one that writes nothing.
     - Inputs are small integers, exactly representable in bf16, so that the expected report is exact. Compute the expected patterns in the test, for example with `numpy` float32 → upper 16 bits for exact values.
     - Cover at least:
       - **happy**: one call; several calls of different shapes over two kernels, in order, with the report length `sum(2*m*n) + 4`; output equal to the exact product's patterns;
       - **branch**: an unwritten kernel reports `0x7FC0` in every element; two kernels of one symbol stay apart;
       - **negative**: a library with only `hilclaw_gemm` (an fp32 kernel) in the bf16 program is status 6, and the line names `hilclaw_gemm_bf16`; a bf16-only library in the fp32 program is status 6 naming `hilclaw_gemm`; a bf16 input file that is short by one element, and one with trailing bytes, are status 5;
       - stdout separation: a printing bf16 kernel does not enter the report.
   - `tests/test_model_run.py`:
     - Every existing call passes `dtype="fp32"`, and its expectations stay unchanged.
     - New tests cover at least:
       - **happy**: `encode_input(..., dtype="bf16")` matches hand-made bytes with 2-byte elements; `output_shapes` for bf16; `parse_report` of a complete bf16 report gives `uint16` arrays of the right shapes and values, with a NaN pattern passed through;
       - **branch**: an fp32-length report is incomplete for `dtype="bf16"` and the reverse, so the result is `None`; `run_model_program` with a recorder (no real process) gives `RunFailed.REPORT_FORM` for a report of the other dtype's length;
       - **negative**: `dtype` missing (a `TypeError` from the call) for each of the four functions; `None`, `1` and `b"bf16"` (`TypeError`); `""`, `"fp16"` and `"BF16"` (`ValueError`); `dtype` refused before a bad `calls` or bad `shapes`; a `float32` array with `dtype="bf16"` and a `uint16` array with `dtype="fp32"` (`ValueError` naming the array); a `float16` or `int16` array with `dtype="bf16"` (`ValueError`);
       - `test_public_names` (or its equivalent) includes `DTYPES`.
     - The real-run section adds at least one real bf16 run of two kernels through `run_model_program`, if the section's fixture can build the bf16 program the same way. Otherwise the program-level tests above are enough. State which in `## Result`.
   - `tests/test_model_execute.py`: the recorder accepts `dtype` and the tests assert that `execute` passes `"fp32"` to each of the three `model_run` functions. Existing expectations are otherwise unchanged.
   - Coverage of `hilclaw/` stays at line ≥ 80% and function ≥ 80%. `pytest`, `ruff check` and `ruff format --check` pass locally on the whole suite. The C gate (clang build of the C sources the CI builds) passes. If the CI's C gate compiles `model_program.c`, it still compiles without the macro. If it is easy, add a compile of the bf16 variant there only if the gate's own pattern already lists per-file flags. Otherwise do not touch CI files.
6. **No data-plane change**: no schema file, member, file, `kind` or `dtype` value, version or validator (ADR-0157 Consequences, A-13 reading). No `ARCHITECTURE/` file changes.
7. **Process**: code mode (CLAUDE.md A-13).
   - Branch `claude/T-0433-<slug>`. Draft PR whose title contains `T-0433` and whose body's last line is `Task: T-0433`.
   - Context-isolated reviewer cycle (dev-code-review) to Approve. CI green. Then squash-merge with `gh pr merge --squash --body` carrying that body, and delete the branch.
   - `## Result` records the languages (C for the program, Python for the host side) and one line of reason each.
   - The reviewer checks at least:
     - that the fp32 build is unchanged;
     - that the bf16 build's symbol, element type, NaN pattern and report length follow ADR-0157 decision 3 and ADR-0156 decision 5;
     - that `dtype` has no default in `model_run` and is checked first;
     - that no array is cast or reinterpreted between dtypes;
     - that no fp16 path, tolerance, reference or weight check is added.

## Out of Scope

- ADR-0157 code slice (2), second part: a `model_build` constant for the bf16 program flag, a `dtype` argument of `model_execute.execute` and `model_gemm.run`, and the bf16 build-and-execute path with the binding check at `bf16`.
- The weights' element-type check (ADR-0157 decision 1; goes with ADR-0153 code slice 2) and anything of ADR-0153 code slice 2 (the forward pass).
- fp16, casts, tolerance, reference, model-level comparison and any widening of reported logits (OD-31 sub-questions 2, 3 and 6, owner).
- `hilclaw/model_binding.py`, `hilclaw/model_gemm.py` and `hilclaw/gemm_bf16_contract.py`.
- Any ADR or other `ARCHITECTURE/` edit.
- The PLAN "보류" items.

## Follow-ups

- (planner) After this lands: ADR-0157 code slice (2), second part. That is a `model_build` constant for `-DHILCLAW_MODEL_BF16`, a required `dtype` for `model_execute.execute` (which builds the matching program and passes the dtype to `model_run`), and a `dtype` for `model_gemm.run`. `model_gemm.run` passes its dtype to `model_binding.check` and builds and runs the bf16 path end to end with the hand-written bf16 kernel fixtures.

## Result
