---
id: T-0439
title: Teach hilclaw.keys the kind elementwise_add (members m, n) and add hilclaw/elementwise_add_bf16_contract.py - the op-side values of the bf16 elementwise add contract of ADR-0159 (constants, prototype, shapes, input patterns, op_signature_record, task_contract, covers) with tests (ADR-0159 code slice, first part)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0438]
touchesFiles: [hilclaw/keys.py, hilclaw/elementwise_add_bf16_contract.py, tests/test_elementwise_add_bf16_contract.py, tests/test_keys.py]
estimatedSize: {loc: 180, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `8351b65`):
- ADR-0159 (T-0438, landed as `278cffc`) defines the contract of (`elementwise_add`, `bf16`, `row_major`, `c`) on `cpu_standin`. It is the third Llama kind contract of PLAN P2-11, after GEMM (ADR-0156) and RMSNorm (ADR-0158).
- Its Consequences (line 185) list the code slice it makes possible:
  1. the kind and its members in `hilclaw.keys`;
  2. a contract module like `hilclaw/rmsnorm_bf16_contract.py` (constants, `task_contract`, `covers`, `op_signature_record`, the value set);
  3. the binding check in `hilclaw/model_binding.py` with the call sites `attention_residual` and `ffn_residual`, their shapes and the "every shape" binding;
  4. hand-written bf16 elementwise add kernel fixtures and the P2-12 harness part.
- Today no code knows the kind: `hilclaw.keys._SHAPE_MEMBERS` holds `gemm` and `rmsnorm` only, so `keys.op_signature_key` refuses every `elementwise_add` record.

**This task is part 1 of that slice**: items 1 and 2. Item 3 imports the module and needs the kind in `hilclaw.keys`, so this comes first. ADR-0158's slice was split the same way (T-0436, then T-0437).

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json`:
- round 0's board step waits on HQ-0021;
- the round >= 1 steps and P2-6/P2-7 wait on HQ-0048 and HQ-0031;
- the gate half of P2-4 is owner-only (OD-3).

P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is the code of a P2-11 contract record. P2-13 and P2-14 need it: ADR-0157 decision 4 keeps `bf16` an invalid model dtype while a call-site kind lacks a bf16 contract, and the forward pass cannot bind a residual add kernel without these values. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, A-13 and D16.**
- No open decision is needed: every value comes from ADR-0159 as accepted.
- A new `kind` value with its shape members raises no `schema_version` (ADR-0001 decision 6; ADR-0159 decision 2 and Consequences "A-13 reading"). So this is not a data-plane schema change in the A-13 sense. If the executor or reviewer finds otherwise, stop and return BLOCKED (A-13 schema change).
- Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0439-<slug>`, PR title with `T-0439`, commit trailer `Task: T-0439`, last line of the PR body `Task: T-0439`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0159-od31-bf16-elementwise-add-contract.md`:
  - decision 1 (scope; lines 33-36);
  - decision 2 (kind `elementwise_add`, members `m` and `n`, every operand `[m, n]`; lines 38-42);
  - decision 6 (the prototype, byte for byte, and the symbol; lines 67-76);
  - decision 7 (operand entries and the `task.contract` example at T = 1; lines 78-100);
  - decision 8, the "Every set of dimensions" and "No shape that holds a 0" bullets (lines 114-115);
  - decision 10 (the value set of a and b, and what is left to P2-12; lines 123-130);
  - decision 11 (the op_signature rule, the canonical line, the sha256 and the three directory names; lines 132-146);
  - Consequences (lines 184-186).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decisions 2 and 6 (lines 37-62, 73-78): member names fixed per kind; a new kind raises no version.
- `hilclaw/rmsnorm_bf16_contract.py`, the whole file (178 lines). This is the model for the new module: the same function set (minus `EPS`), argument checks, error class, message prefix (`shape.<name>: `) and docstring style. Read only; do not edit.
- `hilclaw/keys.py`: lines 1-46 (module docstring, `_NAME`, `_SHAPE_MEMBERS`) and `op_signature_key` (from line 132; its docstring names the known kinds, and line 158 builds the unknown-kind message from the sorted kind names).
- `tests/test_rmsnorm_bf16_contract.py`, the whole file (514 lines): the record copies, the bad-value lists, the spec-validation pattern, `test_record_of_another_kind_is_not_covered` (line 421), and the public-names, imports/binder and no-file tests (lines 465-514). Line 488 onwards asserts that the text `rmsnorm_bf16_contract` appears in no `hilclaw/*.py` file other than that module and `hilclaw/model_binding.py`. `tests/test_gemm_bf16_contract.py` (line 472 onwards) and `tests/test_gemm_contract.py` (line 390 onwards) assert the same for `gemm_bf16_contract` and `gemm_contract`. Read only; do not edit.
- `tests/test_keys.py` lines 598-664 (`test_unknown_kind_is_rejected`, the `rmsnorm` tests, `test_unknown_kind_message_lists_both_kinds`).
- `examples/spec/gemm-485b9bc494d477eb.json` and `hilclaw/spec.py` `validate`. ADR-0159 decision 7 validated its example inside that spec, with the op_signature replaced.

## Acceptance Criteria

1. **`hilclaw/keys.py`**:
   - `_SHAPE_MEMBERS` gains `"elementwise_add": frozenset({"m", "n"})` (ADR-0159 decision 2).
   - The docstrings that name the known kinds (the `op_signature_key` docstring, and any other in the file) name all three kinds and their members.
   - No other change: no new public name, no version change, no other rule. The unknown-kind message keeps its form (sorted kind names joined by `, `), so it becomes `kind: must be a known kind: elementwise_add, gemm, rmsnorm, got ...`.
2. **New module `hilclaw/elementwise_add_bf16_contract.py`** (Python; standard library and `hilclaw.keys` only). Its public names are exactly:
   - `KIND` = `"elementwise_add"`, `DTYPE` = `"bf16"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"` (decisions 1 and 2);
   - `PROTOTYPE`: the single line of decision 6, byte for byte:
     `void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);`
   - `SHAPES`: the three `(m, n)` tuples of decision 11, in table order: `(1, 2048)`, `(32, 2048)`, `(512, 2048)`;
   - `INPUT_PATTERNS`: the 256 `uint16_t` bit patterns of the value set of decision 10 for a and b, as a `tuple` of `int` in ascending order (`0x3F00`-`0x3F7F` and `0xBF00`-`0xBF7F`, i.e. ±(0.5 + j/256) for j = 0..127, the set of ADR-0156 decision 9).
   - No `EPS` and no other constant: the contract has no scalar parameter.
   - The module defines the value set only. It has no generator, seed, draw count, independence choice, content of `c` before a call or widening: those belong to the P2-12 harness record (decision 10). It chooses no tolerance.
   - `op_signature_record(m, n)`, `task_contract(m, n)` and `covers(record)` behave like the functions of the same names in `hilclaw/rmsnorm_bf16_contract.py`, with this module's constants. In particular:
     - each dimension is exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`;
     - a refused dimension raises `keys.InvalidRecordError` with a message starting `shape.<name>: `; a 0 is refused because ADR-0037's reading carries over (decision 8);
     - `task_contract` returns new objects with the three operand entries of decision 7, in this order: `a` (`input`, `[m, n]`), `b` (`input`, `[m, n]`), `c` (`output`, `[m, n]`), each `dtype` `"bf16"`;
     - `covers` first validates with `keys.op_signature_key` (re-raising its error). It returns exactly `True` only for kind `elementwise_add`, dtype `bf16`, layout `row_major` and every dimension >= 1, and ignores `ext` and `label`;
     - arguments are not modified.
3. **No coupling to the other contract modules.**
   - The new module does not import `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract` or `hilclaw.rmsnorm_bf16_contract`.
   - Its text, docstrings included, contains none of `gemm_contract`, `gemm_bf16_contract` and `rmsnorm_bf16_contract`. The binder tests named in Required Reading would fail otherwise, and those files are not to be edited. A docstring may cite ADR-0156 and ADR-0158 by number.
   - So the private helpers and the 256 patterns are the module's own. This small duplication is accepted, as T-0436 accepted it. Say so in the commit body.
   - No other `hilclaw/` module imports or names the new module in this task. It is bound to no tool, registry, `correctness.check`, `spec.write` or `model_binding`. The first case stays fp32 `gemm`.
4. **Docstrings.**
   - The module docstring states the record (ADR-0159, building on ADR-0008, ADR-0037 and ADR-0156) and the values it returns. It also states what the module does not do:
     - no spec building;
     - no binding, no tool, no file, no process, no command-line entry;
     - no harness mechanism for `INPUT_PATTERNS`;
     - no other contract;
     - the operation, its precision and the output rounding (decisions 4 and 5), the guarantees of a call (decision 8) and what the kernel source provides (decision 9) are not represented in any returned value beyond the prototype text.
   - Each public function has a Doxygen-like docstring in the style of `hilclaw/rmsnorm_bf16_contract.py`. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests, `tests/test_keys.py`**: add cases for `elementwise_add`:
   - a valid record gives a name starting `elementwise_add-`, and the T = 1 record of ADR-0159 decision 11 gives the canonical line of that decision, the sha256 `1af54bf2a0744c6977bb2d6411d15fb0a9cbdf0a997e159879d84bfe21708bce` and the name `elementwise_add-1af54bf2a0744c69`;
   - wrong member sets are refused with `^shape: must be a map with exactly the members m, n` (missing `n`, an extra `k`, the `gemm` set);
   - `gemm` still requires exactly `m`, `k`, `n`, and `rmsnorm` still exactly `m`, `n`.

   The two existing assertions on the unknown-kind message (line 600, regex `^kind: must be a known kind: gemm`, and line 662, `test_unknown_kind_message_lists_both_kinds`) no longer match the sorted list. Change only their expected text to the new list `elementwise_add, gemm, rmsnorm` (renaming the second test to say all known kinds is allowed). Do not remove or weaken any other existing test.
6. **Tests, new file `tests/test_elementwise_add_bf16_contract.py`** (D12: happy, error, branch and negative cases, every public function and constant). It covers at least:
   - **Record copies**: the constants and `PROTOTYPE` equal the text copied from decisions 2 and 6; `task_contract(1, 2048)` equals the JSON example of decision 7.
   - **Directory names**: for each shape of `SHAPES`, `keys.op_signature_key(op_signature_record(*shape)).name` equals the decision 11 table. Copy the three names into the test: `elementwise_add-1af54bf2a0744c69`, `elementwise_add-7ca4cdf06f7c3008`, `elementwise_add-dd63031857ec45cd`. The canonical text and sha256 at T = 1 equal the decision 11 lines.
   - **Spec validation**: a spec built like the one in `tests/test_rmsnorm_bf16_contract.py`, with this module's `op_signature_record` and `task_contract`, passes `hilclaw.spec.validate` for each shape of `SHAPES` and one small shape; the same spec with the shape of `b` changed to `[1, 2049]` at T = 1 is refused (as decision 7 recorded).
   - **`INPUT_PATTERNS`**: length 256, ascending, all distinct, each an `int` in 0..0xFFFF. Each, widened to fp32 by `pattern << 16` (`struct`), is finite, has magnitude in [0.5, 1), and equals ±(0.5 + j/256). Both signs of every magnitude are present.
   - **`covers`**:
     - `True` for a record of each shape in `SHAPES` and for a small shape;
     - `True` with an `ext` or `label` present;
     - `False` for an fp32 `elementwise_add` record, for another dtype or layout value, and for a valid record with a 0 dimension;
     - `False` for a valid bf16 `gemm` record and a valid bf16 `rmsnorm` record (the latter has the same members `m`, `n`);
     - `False` for a record of another kind known only through a monkeypatched `keys._SHAPE_MEMBERS`;
     - raises `InvalidRecordError` for an invalid record or an unknown kind;
     - the argument is unchanged.
   - **The other contracts do not cover this kind**: `covers` of `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract` and `hilclaw.rmsnorm_bf16_contract` each return `False` for a valid `elementwise_add` record at each shape, at dtype `bf16` and `fp32`. (The test file may import those modules; only the new module's own text is restricted by criterion 3.)
   - **Negative dimensions** for `op_signature_record` and `task_contract`: `bool`, an `int` subclass, `float`, `str`, `None`, 0, a negative value, `MAX_INTEGER + 1`. Each error message starts with the right `shape.<name>: `.
   - **Independence**:
     - results are new objects (mutating one does not change the next);
     - the public names are exactly those of criterion 2;
     - the module imports only the standard library, `hilclaw` and `hilclaw.keys`;
     - its text has none of `gemm_contract`, `gemm_bf16_contract`, `rmsnorm_bf16_contract`;
     - no other `hilclaw/*.py` file names `elementwise_add_bf16_contract`;
     - a call writes no file.
7. **Effect of the new kind on other modules.**
   - Before committing, search `hilclaw/` for code that relies on `keys.op_signature_key` refusing a kind it did not know. Candidates include `spec.py`, `spec_tool.py`, `key_records.py`, `case_lookup.py`, `instance.py`, `instance_start.py`, `run_admission.py`, `check_admission.py` and `model_binding.py`. T-0436 `## Result` lists what changed when `rmsnorm` became known; use it as the checklist.
   - List in `## Result` each place whose answer for an `elementwise_add` record changes. For example, a refusal that used to come from the key check and now comes from the contract check.
   - Nothing may now treat an `elementwise_add` record as covered by a `gemm` or `rmsnorm` contract.
   - If some place would need a code change to stay correct, do not make it here. Stop and return BLOCKED (`requirement-unclear`) with the place named.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except the two expected-message edits and the additions of criterion 5 in `tests/test_keys.py`.
   - Line and function coverage of `hilclaw/` stay >= 80%, and the new module is at 100% line coverage.
   - CI is green. The CI test-existence check finds `tests/test_elementwise_add_bf16_contract.py`.
9. **No other file changes.** Do not edit:
   - `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/model_binding.py`, `hilclaw/spec.py`, `hilclaw/spec_tool.py`, any registry or tool module, any C file;
   - any test other than `tests/test_keys.py` and the new test file;
   - any `ARCHITECTURE/` or `PROCESS/` file. ADR text that says `hilclaw.keys` knows fewer kinds becomes less exact (for example ADR-0031 lines 21 and 98, ADR-0159 Background if it says so). Note that in `## Result` and do not edit the ADRs.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0439-<slug>`, Draft PR whose title contains `T-0439` and whose body ends with `Task: T-0439`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: pure data and validation over `hilclaw.keys`, as its GEMM and RMSNorm counterparts).
    - The reviewer checks at least:
      - the prototype text, the three directory names, the sha256 at T = 1 and the 256 patterns against ADR-0159;
      - that the module adds no meaning beyond ADR-0159 (no tolerance, generator, seed, independence choice, build flag, binding or registration);
      - the absence of the texts `gemm_contract`, `gemm_bf16_contract` and `rmsnorm_bf16_contract` in the new module;
      - that the only edits to existing tests are the two expected-message changes of criterion 5;
      - the criterion 7 list.

## Out of Scope

- The bf16 elementwise add binding check in `hilclaw/model_binding.py` with the call sites `attention_residual` and `ffn_residual` and the "every shape" binding (next part of the slice).
- The model program and build/run steps calling `hilclaw_elementwise_add_bf16`; hand-written bf16 elementwise add kernel fixtures; any C code.
- The P2-12 harness: generator, seed, draws, independence of a and b, the content of `c` before a call, widening, comparison, tolerance values.
- Registering the contract with `correctness.check`, `spec.write` or the instance start.
- The contracts of SwiGLU activation, RoPE and SDPA with KV cache; fp16; an fp32 contract of this kind; backends other than `cpu_standin`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next part of the ADR-0159 code slice: the elementwise add binding check in `hilclaw/model_binding.py` with the call sites `attention_residual` and `ffn_residual` (ADR-0159 decision 12, including the operands each passes), their shapes (rows x hidden) and the "every shape" binding, in the pattern of T-0437. After that, the SwiGLU activation contract record (doc), then RoPE and SDPA with KV cache.

## Result
