---
id: T-0442
title: Teach hilclaw.keys the kind swiglu (members m, n) and add hilclaw/swiglu_bf16_contract.py - the op-side values of the bf16 SwiGLU activation contract of ADR-0160 (constants, prototype, shapes, the gate and up value sets, op_signature_record, task_contract, covers) with tests (ADR-0160 code slice, first part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0441]
touchesFiles: [hilclaw/keys.py, hilclaw/swiglu_bf16_contract.py, tests/test_swiglu_bf16_contract.py, tests/test_keys.py]
estimatedSize: {loc: 200, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `cf7b1a9`):
- ADR-0160 (T-0441, landed as `58e2aed`) defines the contract of (`swiglu`, `bf16`, `row_major`, `c`) on `cpu_standin`. It is the fourth Llama kind contract of PLAN P2-11, after GEMM (ADR-0156), RMSNorm (ADR-0158) and elementwise add (ADR-0159).
- Its Consequences (line 187) list the code slice it makes possible:
  1. the kind and its members in `hilclaw.keys`;
  2. a contract module like `hilclaw/elementwise_add_bf16_contract.py` (constants, `task_contract`, `covers`, `op_signature_record`, the two value sets);
  3. the binding check in `hilclaw/model_binding.py` with the call site `ffn_activation`, its shape and the "every shape" binding;
  4. hand-written bf16 SwiGLU kernel fixtures and the P2-12 harness part.
- Today no code knows the kind: `hilclaw.keys._SHAPE_MEMBERS` holds `elementwise_add`, `gemm` and `rmsnorm` only, so `keys.op_signature_key` refuses every `swiglu` record.

**This task is part 1 of that slice**: items 1 and 2. Item 3 imports the module and needs the kind in `hilclaw.keys`, so this comes first. ADR-0158's and ADR-0159's slices were split the same way (T-0436/T-0437, T-0439/T-0440).

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json` (round 0's board step on HQ-0021; the round >= 1 steps and P2-6/P2-7 on HQ-0048 (T-0361, the selection role and `hypotheses.write`) and HQ-0024 (T-0233, `injections`); the gate half of P2-4 is owner-only, OD-3). T-0318 (ADR-0112, P2-6) has just landed, but it left no plannable P2-6 code step that does not run into those HQs. P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is the code of a P2-11 contract record. P2-13 and P2-14 need it: ADR-0157 decision 4 keeps `bf16` an invalid model dtype while a call-site kind lacks a bf16 contract, and the forward pass cannot bind a SwiGLU kernel without these values. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, A-13 and D16.**
- No open decision is needed: every value comes from ADR-0160 as accepted (owner notice on #5, issuecomment-6382755408). The names of the two value-set constants are this task's choice (criterion 2); they are code identifiers, not a design decision.
- A new `kind` value with its shape members raises no `schema_version` (ADR-0001 decision 6; ADR-0160 decision 2 and Consequences "A-13 reading"). So this is not a data-plane schema change in the A-13 sense. If the executor or reviewer finds otherwise, stop and return BLOCKED (A-13 schema change).
- Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0442-<slug>`, PR title with `T-0442`, commit trailer `Task: T-0442`, last line of the PR body `Task: T-0442`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0160-od31-bf16-swiglu-contract.md`:
  - decision 1 (scope; lines 34-37);
  - decision 2 (kind `swiglu`, members `m` and `n`, every operand `[m, n]`; lines 39-43);
  - decision 6 (the prototype, byte for byte, the operand order and the symbol; lines 69-78);
  - decision 7 (operand entries and the `task.contract` example at T = 1, and its validation; lines 80-102);
  - decision 8, the "Every set of dimensions" and "No shape that holds a 0" bullets (lines 116-117);
  - decision 10 (the two value sets, and what is left to P2-12; lines 125-133, especially line 128);
  - decision 11 (the op_signature rule, the canonical line, the sha256 and the three directory names; lines 135-149);
  - Consequences (lines 186-188).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decisions 2 and 6 (lines 37-62, 73-78): member names fixed per kind; a new kind raises no version.
- `hilclaw/elementwise_add_bf16_contract.py`, the whole file (176 lines). This is the model for the new module: the same function set, argument checks, error class, message prefix (`shape.<name>: `) and docstring style. Read only; do not edit.
- `hilclaw/keys.py`: lines 1-46 (module docstring, `_NAME`, `_SHAPE_MEMBERS`) and `op_signature_key` (lines 136-168; its docstring names the known kinds, and line 163 builds the unknown-kind message from the sorted kind names).
- `tests/test_elementwise_add_bf16_contract.py`, the whole file (535 lines): the record copies, the bad-value lists, the spec-validation pattern, `OTHER_CONTRACTS`/`OTHER_MODULE_NAMES` (lines 83-84), `test_other_contracts_do_not_cover_a_record_of_this_kind` (line 434), `test_record_of_another_kind_is_not_covered` (line 439), and the public-names, imports/binder and no-file tests (lines 485-535). Lines 507-522 assert that the text `elementwise_add_bf16_contract` appears in no `hilclaw/*.py` file other than that module and `hilclaw/model_binding.py`; `tests/test_rmsnorm_bf16_contract.py`, `tests/test_gemm_bf16_contract.py` and `tests/test_gemm_contract.py` assert the same for their module names. Read only; do not edit.
- `tests/test_keys.py` lines 598-734 (`test_unknown_kind_is_rejected`, the `rmsnorm` tests, `test_unknown_kind_message_lists_all_known_kinds`, the `elementwise_add` tests and `test_other_kinds_keep_their_members_beside_elementwise_add`).
- `PROCESS/tasks/T-0439-elementwise-add-bf16-contract-values.md` `## Result` (the criterion 7 list for `elementwise_add`; use it as the checklist for criterion 7 here).
- `examples/spec/gemm-485b9bc494d477eb.json` and `hilclaw/spec.py` `validate`. ADR-0160 decision 7 validated its example inside that spec, with the op_signature replaced.

## Acceptance Criteria

1. **`hilclaw/keys.py`**:
   - `_SHAPE_MEMBERS` gains `"swiglu": frozenset({"m", "n"})` (ADR-0160 decision 2).
   - The docstrings that name the known kinds (the `op_signature_key` docstring, and any other in the file) name all four kinds and their members.
   - No other change: no new public name, no version change, no other rule. The unknown-kind message keeps its form (sorted kind names joined by `, `), so it becomes `kind: must be a known kind: elementwise_add, gemm, rmsnorm, swiglu, got ...`.
2. **New module `hilclaw/swiglu_bf16_contract.py`** (Python; standard library and `hilclaw.keys` only). Its public names are exactly:
   - `KIND` = `"swiglu"`, `DTYPE` = `"bf16"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"` (decisions 1 and 2);
   - `PROTOTYPE`: the single line of decision 6, byte for byte:
     `void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);`
   - `SHAPES`: the three `(m, n)` tuples of decision 11, in table order: `(1, 8192)`, `(32, 8192)`, `(512, 8192)`;
   - `GATE_PATTERNS`: the 1024 `uint16_t` bit patterns of the gate value set of decision 10, as a `tuple` of `int` in ascending order (`0x3F00`-`0x40FF` and `0xBF00`-`0xC0FF`: every bf16 value of magnitude in [0.5, 8) with either sign);
   - `UP_PATTERNS`: the 256 `uint16_t` bit patterns of the up value set of decision 10, as a `tuple` of `int` in ascending order (`0x3F00`-`0x3F7F` and `0xBF00`-`0xBF7F`, i.e. ±(0.5 + j/256) for j = 0..127, the set of ADR-0156 decision 9).
   - No `EPS`, no accuracy-bound constant, no domain constant and no other constant: the contract has no scalar parameter, and the bound and domain D of decision 4 are kernel obligations, not values the caller passes.
   - The module defines the value sets only. It has no generator, seed, draw count, independence choice, content of `out` before a call or widening: those belong to the P2-12 harness record (decision 10). It chooses no tolerance.
   - `op_signature_record(m, n)`, `task_contract(m, n)` and `covers(record)` behave like the functions of the same names in `hilclaw/elementwise_add_bf16_contract.py`, with this module's constants. In particular:
     - each dimension is exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`;
     - a refused dimension raises `keys.InvalidRecordError` with a message starting `shape.<name>: `; a 0 is refused because ADR-0037's reading carries over (decision 8);
     - `task_contract` returns new objects with the three operand entries of decision 7, in this order: `gate` (`input`, `[m, n]`), `up` (`input`, `[m, n]`), `out` (`output`, `[m, n]`), each `dtype` `"bf16"`;
     - `covers` first validates with `keys.op_signature_key` (re-raising its error). It returns exactly `True` only for kind `swiglu`, dtype `bf16`, layout `row_major` and every dimension >= 1, and ignores `ext` and `label`;
     - arguments are not modified.
3. **No coupling to the other contract modules.**
   - The new module does not import `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract`, `hilclaw.rmsnorm_bf16_contract` or `hilclaw.elementwise_add_bf16_contract`.
   - Its text, docstrings included, contains none of `gemm_contract`, `gemm_bf16_contract`, `rmsnorm_bf16_contract` and `elementwise_add_bf16_contract`. The binder tests named in Required Reading would fail otherwise, and those files are not to be edited. A docstring may cite ADR-0156, ADR-0158 and ADR-0159 by number.
   - So the private helpers and the patterns are the module's own. This small duplication is accepted, as T-0436 and T-0439 accepted it. Say so in the commit body.
   - No other `hilclaw/` module imports or names the new module in this task. It is bound to no tool, registry, `correctness.check`, `spec.write` or `model_binding`. The first case stays fp32 `gemm`.
4. **Docstrings.**
   - The module docstring states the record (ADR-0160, building on ADR-0008, ADR-0037 and ADR-0156) and the values it returns, including which value set belongs to which operand. It also states what the module does not do:
     - no spec building;
     - no binding, no tool, no file, no process, no command-line entry;
     - no harness mechanism for `GATE_PATTERNS` and `UP_PATTERNS`;
     - no other contract;
     - the operation, its precision, the accuracy bound and its domain, and the output rounding (decisions 4 and 5), the guarantees of a call (decision 8) and what the kernel source provides (decision 9) are not represented in any returned value beyond the prototype text.
   - Each public function has a Doxygen-like docstring in the style of `hilclaw/elementwise_add_bf16_contract.py`. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests, `tests/test_keys.py`**: add cases for `swiglu`:
   - a valid record gives a name starting `swiglu-`, and the T = 1 record of ADR-0160 decision 11 gives the canonical line of that decision (`{"dtype":"bf16","kind":"swiglu","layout":"row_major","schema_version":1,"shape":{"m":1,"n":8192}}`), the sha256 `7b82bc7d69cda1e0fd3794adbe3bce2274830ff1c53b3c20997ae095e352dc29` and the name `swiglu-7b82bc7d69cda1e0`;
   - wrong member sets are refused with `^shape: must be a map with exactly the members m, n` (missing `n`, an extra `k`, the `gemm` set);
   - `gemm` still requires exactly `m`, `k`, `n`, and `rmsnorm` and `elementwise_add` still exactly `m`, `n`.

   The two existing assertions on the unknown-kind message (line 602, regex `^kind: must be a known kind: elementwise_add, gemm, rmsnorm`, and line 666 in `test_unknown_kind_message_lists_all_known_kinds`) no longer match the sorted list once `swiglu` is added. Change only their expected text to the new list `elementwise_add, gemm, rmsnorm, swiglu`. Do not remove or weaken any other existing test.
6. **Tests, new file `tests/test_swiglu_bf16_contract.py`** (D12: happy, error, branch and negative cases, every public function and constant). It covers at least:
   - **Record copies**: the constants and `PROTOTYPE` equal the text copied from decisions 2 and 6; `task_contract(1, 8192)` equals the JSON example of decision 7.
   - **Directory names**: for each shape of `SHAPES`, `keys.op_signature_key(op_signature_record(*shape)).name` equals the decision 11 table. Copy the three names into the test: `swiglu-7b82bc7d69cda1e0`, `swiglu-ee76c0d3e36f20f7`, `swiglu-a1d727f15ac574e0`. The canonical text and sha256 at T = 1 equal the decision 11 lines.
   - **Spec validation**: a spec built like the one in `tests/test_elementwise_add_bf16_contract.py`, with this module's `op_signature_record` and `task_contract`, passes `hilclaw.spec.validate` for each shape of `SHAPES` and one small shape; the same spec with the shape of `up` changed to `[1, 8193]` at T = 1 is refused (as decision 7 recorded).
   - **`GATE_PATTERNS`**: length 1024, ascending, all distinct, each an `int` in 0..0xFFFF. Each, widened to fp32 by `pattern << 16` (`struct`), is finite and has magnitude in [0.5, 8); the largest magnitude is 7.96875; every bf16 pattern of magnitude in [0.5, 8) of either sign is present (none missing, for example `0x3EFF` and `0x4100` and their negatives are absent and every pattern between is present); both signs of every magnitude are present.
   - **`UP_PATTERNS`**: length 256, ascending, all distinct, each an `int` in 0..0xFFFF. Each, widened to fp32, is finite, has magnitude in [0.5, 1), and equals ±(0.5 + j/256). Both signs of every magnitude are present. `UP_PATTERNS` is a subset of `GATE_PATTERNS`.
   - **`covers`**:
     - `True` for a record of each shape in `SHAPES` and for a small shape;
     - `True` with an `ext` or `label` present;
     - `False` for an fp32 `swiglu` record, for another dtype or layout value, and for a valid record with a 0 dimension;
     - `False` for a valid bf16 `gemm` record and valid bf16 `rmsnorm` and `elementwise_add` records (the latter two have the same members `m`, `n`);
     - `False` for a record of another kind known only through a monkeypatched `keys._SHAPE_MEMBERS`;
     - raises `InvalidRecordError` for an invalid record or an unknown kind;
     - the argument is unchanged.
   - **The other contracts do not cover this kind**: `covers` of `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract`, `hilclaw.rmsnorm_bf16_contract` and `hilclaw.elementwise_add_bf16_contract` each return `False` for a valid `swiglu` record at each shape, at dtype `bf16` and `fp32`. (The test file may import those modules; only the new module's own text is restricted by criterion 3.)
   - **Negative dimensions** for `op_signature_record` and `task_contract`: `bool`, an `int` subclass, `float`, `str`, `None`, 0, a negative value, `MAX_INTEGER + 1`. Each error message starts with the right `shape.<name>: `. Wrong argument counts raise `TypeError`.
   - **Independence**:
     - results are new objects (mutating one does not change the next);
     - the public names are exactly those of criterion 2;
     - the module imports only the standard library, `hilclaw` and `hilclaw.keys`;
     - its text has none of `gemm_contract`, `gemm_bf16_contract`, `rmsnorm_bf16_contract`, `elementwise_add_bf16_contract`;
     - no other `hilclaw/*.py` file names `swiglu_bf16_contract` (in this task not even `hilclaw/model_binding.py`; the next part of the slice will add it as the one binder and adjust this test);
     - a call writes no file.
7. **Effect of the new kind on other modules.**
   - Before committing, search `hilclaw/` for code that relies on `keys.op_signature_key` refusing a kind it did not know. Candidates include `spec.py`, `spec_tool.py`, `key_records.py`, `case_lookup.py`, `instance.py`, `instance_start.py`, `run_admission.py`, `check_admission.py` and `model_binding.py`. T-0439 `## Result` lists what changed when `elementwise_add` became known; use it as the checklist.
   - List in `## Result` each place whose answer for a `swiglu` record changes. For example, a refusal that used to come from the key check and now comes from the contract check.
   - Nothing may now treat a `swiglu` record as covered by a `gemm`, `rmsnorm` or `elementwise_add` contract.
   - If some place would need a code change to stay correct, do not make it here. Stop and return BLOCKED (`requirement-unclear`) with the place named.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except the two expected-message edits and the additions of criterion 5 in `tests/test_keys.py`.
   - Line and function coverage of `hilclaw/` stay >= 80%, and the new module is at 100% line coverage.
   - CI is green. The CI test-existence check finds `tests/test_swiglu_bf16_contract.py`.
9. **No other file changes.** Do not edit:
   - `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/elementwise_add_bf16_contract.py`, `hilclaw/model_binding.py`, `hilclaw/spec.py`, `hilclaw/spec_tool.py`, any registry or tool module, any C file;
   - any test other than `tests/test_keys.py` and the new test file;
   - any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`. ADR text that says `hilclaw.keys` knows fewer kinds becomes less exact (for example ADR-0031 lines 21 and 98, ADR-0160 Consequences "A-13 reading"). Note that in `## Result` and do not edit the ADRs.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0442-<slug>`, Draft PR whose title contains `T-0442` and whose body ends with `Task: T-0442`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: pure data and validation over `hilclaw.keys`, as its GEMM, RMSNorm and elementwise add counterparts).
    - The reviewer checks at least:
      - the prototype text (operand names and order `gate`, `up`, `out`), the three directory names, the sha256 at T = 1 and the 1024 and 256 patterns against ADR-0160;
      - that the module adds no meaning beyond ADR-0160 (no tolerance, accuracy bound, domain, generator, seed, independence choice, build flag, binding or registration);
      - the absence of the texts `gemm_contract`, `gemm_bf16_contract`, `rmsnorm_bf16_contract` and `elementwise_add_bf16_contract` in the new module;
      - that the only edits to existing tests are the two expected-message changes of criterion 5;
      - the criterion 7 list.

## Out of Scope

- The bf16 SwiGLU binding check in `hilclaw/model_binding.py` with the call site `ffn_activation`, its operands (ADR-0160 decision 12), its shape (rows x intermediate) and the "every shape" binding (next part of the slice).
- The model program and build/run steps calling `hilclaw_swiglu_bf16`; hand-written bf16 SwiGLU kernel fixtures; any C code; linking the math library.
- The P2-12 harness: generator, seed, draws, independence of gate and up, the content of `out` before a call, widening, comparison, tolerance values.
- Registering the contract with `correctness.check`, `spec.write` or the instance start.
- The contracts of RoPE and SDPA with KV cache; fp16; an fp32 contract of this kind; backends other than `cpu_standin`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next part of the ADR-0160 code slice: the SwiGLU binding check in `hilclaw/model_binding.py` with the call site `ffn_activation` (ADR-0160 decision 12, including the operands it passes: `gate` from the GEMM call site `gate`, `up` from the GEMM call site `up`, `out` read by the GEMM call site `down`), its shape (rows x 8192) and the "every shape" binding, in the pattern of T-0440. After that, the RoPE contract record (doc), then SDPA with KV cache.

## Result

- **Outcome**: DONE. PR #260 squash-merged as `3d50823` (branch `claude/T-0442-swiglu-bf16-contract-values` deleted).
- **Review**: 1 round, Approve with one Info (CI pending at review time; then green). Reviewer judged the new kind not to be an A-13 data-plane schema change (`schema_version` stays 1, ADR-0001 decision 6).
- **CI**: green on all six jobs (C gate, Coverage gate, Python gate 3.11/3.14, Test presence, sh gate; run 40086685083). CI full suite: 29208 passed, 50 skipped; `hilclaw/` line coverage 99%, `keys.py` and `swiglu_bf16_contract.py` 100%.
- **Local gates**: `ruff check` and `ruff format --check` clean; full local `pytest` under coverage: 28309 passed, 949 skipped; `hilclaw/` line coverage 97%, `keys.py` and `swiglu_bf16_contract.py` 100%.
- **Language**: Python - pure data and validation over `hilclaw.keys`, as its GEMM, RMSNorm and elementwise add counterparts.
- **Changes**:
  - `hilclaw/keys.py`: `_SHAPE_MEMBERS` gains `swiglu` with `m`, `n`; the `op_signature_key` docstring names all four kinds; the unknown-kind message reads `kind: must be a known kind: elementwise_add, gemm, rmsnorm, swiglu, got ...`.
  - New `hilclaw/swiglu_bf16_contract.py`: `KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES`, `GATE_PATTERNS` (1024), `UP_PATTERNS` (256), `op_signature_record`, `task_contract`, `covers`. No tolerance, bound, domain, generator, seed or binding. Private helpers and the up set duplicate those of the elementwise add module on purpose (commit body says so).
  - `tests/test_keys.py`: only the two expected unknown-kind messages changed; new `swiglu` cases (accepted record, ADR-0160 canonical line, sha256, name `swiglu-7b82bc7d69cda1e0`, member sets including the gemm set, other kinds unchanged).
  - New `tests/test_swiglu_bf16_contract.py` (197 tests).
- **Criterion 7**: `keys.op_signature_key` now accepts a `swiglu` record, so `spec.validate`, `instance.py`, `key_records`/`key_store_tool` and `case_lookup`/`case_tool` treat it as valid. `spec_tool`, `instance_start`, `run_admission`/`check_admission`/`check_definition` with `gemm_contract.covers` now refuse it as `op_signature_not_covered` instead of through the key check (they read `shape["k"]` only after `covers` returns True). The `covers` of the gemm, gemm_bf16, rmsnorm_bf16 and elementwise_add_bf16 contracts return False instead of raising. `model_binding.py` does not rely on the key check refusing the kind. No code change was needed.
- **Less exact, not edited**: ADR-0031 lines 21 and 98; ADR-0160 Consequences "A-13 reading" ("`hilclaw/` is not touched"; teaching `hilclaw.keys` the kind "is a later code slice").
- **Follow-ups**: none new beyond the planner follow-up (SwiGLU binding check in `hilclaw/model_binding.py`, call site `ffn_activation`; the next part will add `model_binding.py` as the one binder and adjust `test_module_imports_keys_only_and_is_named_by_no_other_module`).
