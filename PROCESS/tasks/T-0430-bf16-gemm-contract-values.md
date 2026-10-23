---
id: T-0430
title: Add hilclaw/gemm_bf16_contract.py - the op-side values of the bf16 GEMM contract of ADR-0156 (constants, prototype, op_signature_record, task_contract, covers, the verification input bit patterns) with its test file (ADR-0156 code slice, first part)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, "PLAN P2-11", "PLAN P2-13"]
dependsOn: [T-0429]
touchesFiles: [hilclaw/gemm_bf16_contract.py, tests/test_gemm_bf16_contract.py]
estimatedSize: {loc: 150, files: 1}
hq: []
---
## Why

**Where things stand** (as of `main` `477d6cb`):
- ADR-0156 (T-0429, landed as `47062f3`) defines the contract of (`gemm`, `bf16`, `row_major`, `c`) on `cpu_standin`. Its Consequences list the code slice it makes possible:
  1. the bf16 counterpart of `hilclaw/gemm_contract.py`: its constants, `task_contract`, `covers` and `op_signature_record` for this contract;
  2. its use by `hilclaw/model_binding.py` (fit and the "every shape" binding) and by the model program, which calls `hilclaw_gemm_bf16` over `uint16_t` buffers;
  3. hand-written bf16 kernels as test fixtures;
  4. the P2-12 harness work of a bf16 verification run.
- The T-0429 Follow-ups name this slice as the planner's next step.
- Today no code knows the bf16 contract. `hilclaw/gemm_contract.py` is bound to fp32 only, and `hilclaw/model_binding.py` checks fit against fp32 `gemm` only.

**This task is part 1 of that slice**: the module that returns the values ADR-0156 fixes. Parts 2 to 4 import it, so it comes first. Parts 2 to 4 need changes to `model_binding.py`, `model_program.c`, `model_build.py`/`model_run.py` and new C fixtures, which do not fit one task under the size cap. They are later tasks.

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held: round 0's board step waits on HQ-0021; the round >= 1 steps and P2-6/P2-7 wait on HQ-0048 and HQ-0031; the gate half of P2-4 is owner-only (OD-3). All of these are unresolved in `PROCESS/STATE.json`. P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is a code slice of a P2-11 contract record that P2-13 and P2-14 need: the model executor cannot bind a bf16 kernel without these values. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9 and D16.** No open decision is needed: every value comes from ADR-0156 as accepted. No data-plane schema, member, file, version or validator changes. `bf16` is a new value of the existing field `dtype` (ADR-0001 decision 6), and `hilclaw.keys` accepts it as it stands. Nothing here starts `claude`, needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0430-<slug>`, PR title with `T-0430`, commit trailer `Task: T-0430`, last line of the PR body `Task: T-0430`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0156-od31-bf16-gemm-contract.md`:
  - decision 1 (scope; lines 32-35);
  - decision 2 (kind, dtype, layout; lines 37-41);
  - decision 5 (the prototype, byte for byte; lines 59-72);
  - decision 6 (operand entries and the `task.contract` example; lines 74-94);
  - decision 7, the "Every set of dimensions" and "No shape that holds a 0" bullets (lines 110-111);
  - decision 9 (the value set of the verification inputs; lines 121-127);
  - decision 10 (the op_signature rule and the 15 directory names; lines 129-151);
  - Consequences, the code slice (lines 173-177).
- `ARCHITECTURE/decisions/ADR-0037-od6-gemm-contract-zero-dimension.md` decision 2 (no shape that holds a 0).
- `hilclaw/gemm_contract.py`, whole file (183 lines). This is the model for the new module: the same functions, argument checks, error class and message prefix (`shape.<name>: `), and the same docstring style. Read only; do not edit.
- `hilclaw/keys.py`: lines 29-46 (`SCHEMA_VERSION`, `MAX_INTEGER`, `_NAME`, `_SHAPE_MEMBERS`) and `op_signature_key` (from line 132).
- `tests/test_gemm_contract.py`:
  - lines 1-160: the record copies, the bad-value lists, `synthetic_spec` and the spec-validation pattern;
  - lines 386-433: the binder test, the public-names test and the no-file test.
  
  The binder test at line 386 asserts that **no** `hilclaw/*.py` file other than the four listed binders contains the text `gemm_contract`. Read only; do not edit.
- `examples/spec/gemm-485b9bc494d477eb.json` and `hilclaw/spec.py` `validate`: the spec ADR-0156 decision 6 validated its `task.contract` example inside.

## Acceptance Criteria

1. **New module `hilclaw/gemm_bf16_contract.py`** (Python; standard library and `hilclaw.keys` only). Its public names are exactly:
   - `KIND` = `"gemm"`, `DTYPE` = `"bf16"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"` (ADR-0156 decisions 1 and 2);
   - `PROTOTYPE`: the single line of ADR-0156 decision 5, byte for byte:
     `void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);`
   - `SHAPES`: the 15 `(m, k, n)` tuples of the ADR-0156 decision 10 table, in table order (rows gate/up, down, QKV, O, lm_head; within a row M = 1, 32, 512);
   - `INPUT_PATTERNS`: the 256 `uint16_t` bit patterns of the value set of ADR-0156 decision 9, as a `tuple` of `int` in ascending order. These are `0x3F00`-`0x3F7F` and `0xBF00`-`0xBF7F`, i.e. ±(0.5 + j/256) for j = 0..127. The module defines the value set only. It has no generator, seed, draw count or widening: those belong to the P2-12 harness record (ADR-0156 decision 9).
   - `op_signature_record(m, k, n)`, `task_contract(m, k, n)` and `covers(record)`: the same contracts as the functions of the same names in `hilclaw/gemm_contract.py`, with `DTYPE`/`PROTOTYPE` of this module. In particular:
     - each dimension is exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`;
     - a refused dimension raises `keys.InvalidRecordError` with a message starting `shape.<name>: ` (a 0 is refused by ADR-0037 decision 2 as ADR-0156 decision 7 reads it);
     - `task_contract` returns new objects with the three operand entries `a`/`b`/`c` of ADR-0156 decision 6, each `dtype` `"bf16"`;
     - `covers` first validates with `keys.op_signature_key` (re-raising its error) and returns exactly `True` only for kind `gemm`, dtype `bf16`, layout `row_major` and every dimension >= 1, ignoring `ext` and `label`;
     - arguments are not modified.
2. **No coupling to the fp32 module.**
   - The new module does not import `hilclaw.gemm_contract`.
   - Its text, docstrings included, does not contain the string `gemm_contract`. The existing binder test in `tests/test_gemm_contract.py` (line 386) would fail otherwise, and that file is not to be edited.
   - The private shape and operand helpers are therefore the module's own. This small duplication is accepted. Say so in the commit body.
   - No other `hilclaw/` module imports or names the new module in this task. It is bound to no tool, registry, `correctness.check` or `spec.write`; the first case stays fp32.
3. **Docstrings.**
   - The module docstring states the record (ADR-0156, building on ADR-0008 and ADR-0037), the values it returns, and what it does not do:
     - no spec building;
     - no binding, no tool, no file, no process, no command-line entry;
     - no harness mechanism for `INPUT_PATTERNS`;
     - no other contract.
   - Each public function has a Doxygen-like docstring in the style of `hilclaw/gemm_contract.py`. Other comments follow CLAUDE.md "코멘트 최소화".
4. **New test file `tests/test_gemm_bf16_contract.py`** (D12: happy, error, branch and negative cases, every public function and constant). It covers at least:
   - **Record copies**: the constants and `PROTOTYPE` equal the text copied from ADR-0156 decisions 2 and 5; `task_contract(1, 2048, 8192)` equals the JSON example of decision 6.
   - **Directory names**: for each shape of `SHAPES`, `keys.op_signature_key(op_signature_record(*shape)).name` equals the decision 10 table, all 15 names copied into the test. The canonical text of gate/up M = 1 equals the decision 10 line.
   - **Spec validation**: a spec built like `synthetic_spec` in `tests/test_gemm_contract.py`, with this module's `op_signature_record` and `task_contract`, passes `hilclaw.spec.validate` for at least one projection shape and one small shape.
   - **`INPUT_PATTERNS`**: length 256, ascending, all distinct, each an `int` in 0..0xFFFF. Each, widened to fp32 by `pattern << 16` (`struct`), is finite, has magnitude in [0.5, 1), and equals ±(0.5 + j/256). Both signs of every magnitude are present.
   - **`covers`**:
     - `True` for a record of each shape in `SHAPES` and for a small shape;
     - `True` with an `ext` or `label` present;
     - `False` for an fp32 record, the fp32 module's record of the same shape included;
     - `False` for another dtype or layout value, and for a valid record with a 0 dimension;
     - raises `InvalidRecordError` for an invalid record or an unknown kind;
     - the argument is unchanged.
   - **Negative dimensions** for `op_signature_record` and `task_contract`: `bool`, an `int` subclass, `float`, `str`, `None`, 0, a negative value, `MAX_INTEGER + 1`. Each error message starts with the right `shape.<name>: `.
   - **Independence**: results are new objects (mutating one does not change the next); the public names are exactly those of criterion 1; the module's imports are only the standard library, `hilclaw` and `hilclaw.keys`, and its text has no `gemm_contract`; a call writes no file.
5. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally, `tests/test_gemm_contract.py` included and unchanged.
   - Line and function coverage of `hilclaw/` stay >= 80%, and the new module itself is at 100% line coverage.
   - CI is green. The CI test-existence check finds `tests/test_gemm_bf16_contract.py`.
6. **No other file changes.** Do not edit:
   - `hilclaw/gemm_contract.py`, `hilclaw/model_binding.py`, `hilclaw/model_program.c`, `hilclaw/keys.py`, `hilclaw/spec.py`;
   - any registry or tool module;
   - `tests/test_gemm_contract.py`, any other test;
   - any `ARCHITECTURE/` or `PROCESS/` file.
7. **Process**: code mode (CLAUDE.md A-13).
   - Branch `claude/T-0430-<slug>`, Draft PR whose title contains `T-0430` and whose body ends with `Task: T-0430`.
   - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
   - The commit body has one line on the language choice (Python: pure data and validation over `hilclaw.keys`, the same as its fp32 counterpart).
   - The reviewer checks at least:
     - the prototype text, the 15 directory names and the 256 patterns against ADR-0156;
     - that the module adds no meaning beyond ADR-0156 (no tolerance, generator, seed, build flag, binding or registration);
     - the absence of the text `gemm_contract` in the new module.

## Out of Scope

- The bf16 fit and "every shape" binding in `hilclaw/model_binding.py` (ADR-0153 decision 3, ADR-0156 decision 7). This includes how the executor learns a call site's dtype. It is the next part of the slice.
- The model program and the build and run steps over `uint16_t` buffers (`hilclaw/model_program.c`, `model_build.py`, `model_run.py`, `model_execute.py`, `model_gemm.py`), and the weights' dtype on the host side.
- Hand-written bf16 kernel fixtures; any C code.
- The P2-12 harness: generator over `INPUT_PATTERNS`, seed, draws, float64 widening, comparison, tolerance values.
- Registering the contract with `correctness.check`, `spec.write` or the instance start; the first case stays fp32 `gemm`.
- The other five kinds' contracts; fp16; backends other than `cpu_standin`.
- The PLAN "보류" items, including the two T-0429 wording follow-ups.

## Follow-ups

- (planner) Next part of the ADR-0156 code slice:
  - bf16 fit and "every shape" binding in `hilclaw/model_binding.py`. If the way a call site's dtype reaches the check is not settled by ADR-0153, return it as a design question, not an invention.
  - then the model program calling `hilclaw_gemm_bf16` over `uint16_t` buffers, with hand-written bf16 kernel fixtures, split to the size cap.
  - then the P2-12 bf16 verification-run harness record and code, and the next kind's contract record.

## Result
