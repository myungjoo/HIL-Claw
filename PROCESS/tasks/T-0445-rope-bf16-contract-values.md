---
id: T-0445
title: Teach hilclaw.keys the kind rope (members m, h, d) and add hilclaw/rope_bf16_contract.py - the op-side values of the bf16 RoPE contract of ADR-0161 (constants, prototype, the six shapes, the x value set, op_signature_record, task_contract, covers) with tests (ADR-0161 code slice, first part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0444]
touchesFiles: [hilclaw/keys.py, hilclaw/rope_bf16_contract.py, tests/test_rope_bf16_contract.py, tests/test_keys.py]
estimatedSize: {loc: 220, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `19732d3`):
- ADR-0161 (T-0444, landed as `7c8c5c6`) defines the contract of (`rope`, `bf16`, `row_major`, `c`) on `cpu_standin`. It is the fifth Llama kind contract of PLAN P2-11, after GEMM (ADR-0156), RMSNorm (ADR-0158), elementwise add (ADR-0159) and SwiGLU (ADR-0160).
- Its Consequences (line 188) list the code slice it makes possible:
  1. the kind and its members in `hilclaw.keys`;
  2. a contract module (`task_contract`, `covers`, `op_signature_record`, the value set);
  3. a table builder on the host side (decision 4) with tests against the rule;
  4. the binding check in `hilclaw/model_binding.py` with `rope_q`, `rope_k`, shape (rows, heads, head_dim) and the "every shape" binding, `bf16` only;
  5. the RoPE constants in the model parameters;
  6. hand-written kernel fixtures and the P2-12 harness part.
- Today no code knows the kind: `hilclaw.keys._SHAPE_MEMBERS` holds `elementwise_add`, `gemm`, `rmsnorm` and `swiglu` only, so `keys.op_signature_key` refuses every `rope` record.

**This task is part 1 of that slice**: items 1 and 2. Every later item imports the module or needs the kind in `hilclaw.keys`, so this comes first. ADR-0158, ADR-0159 and ADR-0160 slices were split the same way (T-0436/T-0437, T-0439/T-0440, T-0442/T-0443).

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json` (round 0's board step on HQ-0021; the round >= 1 steps and P2-6/P2-7 on HQ-0048 and HQ-0024; the gate half of P2-4 is owner-only, OD-3). P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is the code of a P2-11 contract record; P2-13 and P2-14 need it (ADR-0157 decision 4 keeps `bf16` an invalid model dtype while a call-site kind lacks a bf16 contract). It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, A-13, HQ-0070 and D16.**
- No open decision is needed: every value comes from ADR-0161 as accepted (owner notice on #5, issuecomment-6384664343). The name of the value-set constant is this task's choice (criterion 2); it is a code identifier, not a design decision.
- HQ-0070 (the scale factor, 8 or 32) is open and non-blocking for this task: ADR-0161 decision 4 makes the contract independent of it, and this module holds no table, no scaling constant and no `rope_theta` (criterion 2).
- A new `kind` value with its shape members raises no `schema_version` (ADR-0001 decision 6; ADR-0161 decision 3 and Consequences "A-13 reading"). So this is not a data-plane schema change in the A-13 sense. If the executor or reviewer finds otherwise, stop and return BLOCKED (A-13 schema change).
- Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit);
  - §5 (task format; naming: branch `claude/T-0445-<slug>`, PR title with `T-0445`, commit trailer `Task: T-0445`, last line of the PR body `Task: T-0445`; size cap; test rules).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0161-od31-bf16-rope-contract.md`:
  - decisions 1 to 3 (scope, two calls of one kind, kind `rope` with members `m`, `h`, `d`; position and constants are not members; lines 37-49);
  - decision 4 (the table is built outside the kernels; lines 51-56) - read to know what this module must NOT hold;
  - decision 6 (dtypes, shapes, rank-3 layout; lines 62-66);
  - decision 9 (the prototype, byte for byte, operand order, symbol; lines 79-86);
  - decision 10 (operand entries and the `task.contract` example at T = 1 for K, and its validation; lines 88-110);
  - decision 11 (guarantees, in particular "`d` is even and at least 2", "Every set of dimensions" and "No shape with a 0"; lines 112-124);
  - decision 13 (the `x` value set; what is left to P2-12; lines 130-136);
  - decision 14 (the op_signature rule, the canonical line, the sha256 and the six directory names; lines 138-152);
  - Consequences (lines 186-193).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decisions 2 and 6: member names fixed per kind; a new kind raises no version.
- `hilclaw/swiglu_bf16_contract.py`, the whole file (182 lines). This is the model for the new module: the same function set, argument checks, error class, message prefix (`shape.<name>: `) and docstring style. Read only; do not edit.
- `hilclaw/keys.py`: lines 1-46 (module docstring, `_NAME`, `_SHAPE_MEMBERS`) and `op_signature_key` (around lines 136-170; its docstring names the known kinds; line 165 builds the unknown-kind message from the sorted kind names, line 167 the member message from the sorted member names, so the `rope` member message reads `exactly the members d, h, m`).
- `tests/test_swiglu_bf16_contract.py`, the whole file (587 lines): the record copies, the bad-value lists, the spec-validation pattern, `OTHER_CONTRACTS`/`OTHER_MODULE_NAMES` (lines 86-97), `test_record_of_another_known_kind_is_not_covered` (line 476), `test_other_contracts_do_not_cover_a_record_of_this_kind` (line 487), `test_record_of_another_kind_is_not_covered` (line 492), and the public-names, imports/binder and no-file tests (lines 540-587). Lines 561-574 assert that the text `swiglu_bf16_contract` appears in no `hilclaw/*.py` file other than that module and `hilclaw/model_binding.py`; the tests of the gemm, gemm_bf16, rmsnorm_bf16 and elementwise_add_bf16 modules assert the same for their names. Read only; do not edit.
- `tests/test_keys.py` lines 595-610 (`test_unknown_kind_is_rejected`), 663-667 (`test_unknown_kind_message_lists_all_known_kinds`) and 735-800 (the `swiglu` tests and `test_other_kinds_keep_their_members_beside_swiglu`).
- `PROCESS/tasks/T-0442-swiglu-bf16-contract-values.md` `## Result` (the criterion 7 list for `swiglu`; use it as the checklist for criterion 7 here).
- `examples/spec/gemm-485b9bc494d477eb.json` and `hilclaw/spec.py` `validate` (around lines 205-240: operand shape values must be values of the record's shape). ADR-0161 decision 10 validated its example inside that spec, with the op_signature replaced.

## Acceptance Criteria

1. **`hilclaw/keys.py`**:
   - `_SHAPE_MEMBERS` gains `"rope": frozenset({"m", "h", "d"})` (ADR-0161 decision 3).
   - The docstrings that name the known kinds (the `op_signature_key` docstring, and any other in the file) name all five kinds and their members.
   - No other change: no new public name, no version change, no other rule (in particular `hilclaw.keys` does not learn that `d` must be even; that is the contract's, criterion 2). The unknown-kind message keeps its form, so it becomes `kind: must be a known kind: elementwise_add, gemm, rmsnorm, rope, swiglu, got ...`.
2. **New module `hilclaw/rope_bf16_contract.py`** (Python; standard library and `hilclaw.keys` only). Its public names are exactly:
   - `KIND` = `"rope"`, `DTYPE` = `"bf16"`, `TABLE_DTYPE` = `"fp32"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"` (decisions 1, 3, 6 and 10);
   - `PROTOTYPE`: the single line of decision 9, byte for byte:
     `void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);`
   - `SHAPES`: the six `(m, h, d)` tuples of decision 14, Q row then K row, each in T order: `(1, 32, 64)`, `(128, 32, 64)`, `(2048, 32, 64)`, `(1, 8, 64)`, `(128, 8, 64)`, `(2048, 8, 64)`;
   - `X_PATTERNS`: the 256 `uint16_t` bit patterns of the `x` value set of decision 13, as a `tuple` of `int` in ascending order (`0x3F00`-`0x3F7F` and `0xBF00`-`0xBF7F`, i.e. ±(0.5 + j/256) for j = 0..127, the set of ADR-0156 decision 9).
   - No table, table builder, `rope_theta`, scaling constant, scale factor, position, accuracy-bound constant, domain constant or other constant: decision 3 keeps those out of the kernel's contract and decision 4 gives the table to the host side (a later part of the slice). The `freqs_cis` value set of decision 13 is rows of that table, so this module does not define it.
   - The module has no generator, seed, draw count, choice of T = 1 row, content of `out` before a call or widening: those belong to the P2-12 harness record (decision 13). It chooses no tolerance.
   - `op_signature_record(m, h, d)`, `task_contract(m, h, d)` and `covers(record)` behave like the functions of the same names in `hilclaw/swiglu_bf16_contract.py`, with this module's constants and three dimensions. In particular:
     - each dimension is exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`; in addition `d` must be even (decision 11: "`d` is even and at least 2");
     - a refused dimension raises `keys.InvalidRecordError` with a message starting `shape.<name>: `; a 0 is refused because ADR-0037's reading carries over (decision 11); an odd `d` is refused with a message starting `shape.d: ` that says it must be even;
     - `op_signature_record` returns a new record with `shape` members `m`, `h`, `d`, `dtype` `"bf16"` and `layout` `"row_major"`, and no `ext` or `label`;
     - `task_contract` returns new objects with the three operand entries of decision 10, in this order: `x` (`input`, `bf16`, `[m, h, d]`), `freqs_cis` (`input`, `fp32`, `[m, d]`), `out` (`output`, `bf16`, `[m, h, d]`);
     - `covers` first validates with `keys.op_signature_key` (re-raising its error). It returns exactly `True` only for kind `rope`, dtype `bf16`, layout `row_major`, every dimension >= 1 and an even `d`, and ignores `ext` and `label`;
     - arguments are not modified.
3. **No coupling to the other contract modules.**
   - The new module does not import `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract`, `hilclaw.rmsnorm_bf16_contract`, `hilclaw.elementwise_add_bf16_contract` or `hilclaw.swiglu_bf16_contract`.
   - Its text, docstrings included, contains none of `gemm_contract`, `gemm_bf16_contract`, `rmsnorm_bf16_contract`, `elementwise_add_bf16_contract` and `swiglu_bf16_contract`. The binder tests named in Required Reading would fail otherwise, and those files are not to be edited. A docstring may cite ADR-0156 and ADR-0158 to ADR-0160 by number.
   - So the private helpers and the patterns are the module's own. This small duplication is accepted, as T-0436, T-0439 and T-0442 accepted it. Say so in the commit body.
   - No other `hilclaw/` module imports or names the new module in this task. It is bound to no tool, registry, `correctness.check`, `spec.write` or `model_binding`. The first case stays fp32 `gemm`.
4. **Docstrings.**
   - The module docstring states the record (ADR-0161, building on ADR-0008, ADR-0037 and ADR-0156) and the values it returns, including that `X_PATTERNS` is the value set of `x` and that the `freqs_cis` values are not here. It also states what the module does not do:
     - no table, no `rope_theta` or scaling constant, no position;
     - no spec building;
     - no binding, no tool, no file, no process, no command-line entry;
     - no harness mechanism for `X_PATTERNS`;
     - no other contract;
     - the operation, its precision and bound (decision 7), the output rounding (decision 8), the guarantees of a call (decision 11) and what the kernel source provides (decision 12) are not represented in any returned value beyond the prototype text and the even-`d` rule.
   - Each public function has a Doxygen-like docstring in the style of `hilclaw/swiglu_bf16_contract.py`. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests, `tests/test_keys.py`**: add cases for `rope`:
   - a valid record gives a name starting `rope-`, and the T = 1, H = 8 record of ADR-0161 decision 14 gives the canonical line of that decision (`{"dtype":"bf16","kind":"rope","layout":"row_major","schema_version":1,"shape":{"d":64,"h":8,"m":1}}`), the sha256 `c797475e043d41569f5a69878631c9c59bde735b28fc614aab427b1d9cd4006a` and the name `rope-c797475e043d4156`;
   - wrong member sets are refused with `^shape: must be a map with exactly the members d, h, m` (missing `d`, an extra `n`, the `gemm` set, the `swiglu` set);
   - an odd `d` is accepted by `op_signature_key` (the even rule is the contract's);
   - `gemm` still requires exactly `m`, `k`, `n`, and `rmsnorm`, `elementwise_add` and `swiglu` still exactly `m`, `n`.

   The two existing assertions on the unknown-kind message (line 602 and line 666) no longer match the sorted list once `rope` is added. Change only their expected text to the new list `elementwise_add, gemm, rmsnorm, rope, swiglu`. Do not remove or weaken any other existing test.
6. **Tests, new file `tests/test_rope_bf16_contract.py`** (D12: happy, error, branch and negative cases, every public function and constant). It covers at least:
   - **Record copies**: the constants and `PROTOTYPE` equal the text copied from decisions 3, 6, 9 and 10; `task_contract(1, 8, 64)` equals the JSON example of decision 10.
   - **Directory names**: for each shape of `SHAPES`, `keys.op_signature_key(op_signature_record(*shape)).name` equals the decision 14 table. Copy the six names into the test: `rope-1fafc8411a47dc19`, `rope-9d2410e4438eac67`, `rope-7e13c7020a9b17fb` (Q, T = 1, 128, 2048) and `rope-c797475e043d4156`, `rope-74ab3d4ad2c2e42c`, `rope-125adcdf54641cca` (K). The canonical text and sha256 at T = 1, H = 8 equal the decision 14 lines.
   - **Spec validation**: a spec built like the one in `tests/test_swiglu_bf16_contract.py`, with this module's `op_signature_record` and `task_contract`, passes `hilclaw.spec.validate` for each shape of `SHAPES` and one small shape; the same spec with the shape of `freqs_cis` changed to `[1, 32]` at T = 1, H = 8 is refused (as decision 10 recorded).
   - **`X_PATTERNS`**: length 256, ascending, all distinct, each an `int` in 0..0xFFFF. Each, widened to fp32 by `pattern << 16` (`struct`), is finite, has magnitude in [0.5, 1), and equals ±(0.5 + j/256). Both signs of every magnitude are present.
   - **`covers`**:
     - `True` for a record of each shape in `SHAPES` and for a small shape (for example `(3, 5, 2)`);
     - `True` with an `ext` or `label` present;
     - `False` for an fp32 `rope` record, for another dtype or layout value, for a valid record with a 0 dimension, and for a valid record with an odd `d` (1, 63);
     - `False` for valid bf16 `gemm`, `rmsnorm`, `elementwise_add` and `swiglu` records;
     - `False` for a record of another kind known only through a monkeypatched `keys._SHAPE_MEMBERS` (with members `m`, `h`, `d`);
     - raises `InvalidRecordError` for an invalid record or an unknown kind;
     - the argument is unchanged.
   - **The other contracts do not cover this kind**: `covers` of `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract`, `hilclaw.rmsnorm_bf16_contract`, `hilclaw.elementwise_add_bf16_contract` and `hilclaw.swiglu_bf16_contract` each return `False` for a valid `rope` record at each shape, at dtype `bf16` and `fp32`. (The test file may import those modules; only the new module's own text is restricted by criterion 3.)
   - **Negative dimensions** for `op_signature_record` and `task_contract`, for each of `m`, `h`, `d`: `bool`, an `int` subclass, `float`, `str`, `None`, 0, a negative value, `MAX_INTEGER + 1`; and odd values of `d` (1, 3, 63, `MAX_INTEGER`). Each error message starts with the right `shape.<name>: `. Wrong argument counts raise `TypeError`.
   - **Independence**:
     - results are new objects (mutating one does not change the next);
     - the public names are exactly those of criterion 2;
     - the module imports only the standard library, `hilclaw` and `hilclaw.keys`;
     - its text has none of the five module names of criterion 3;
     - no other `hilclaw/*.py` file names `rope_bf16_contract` (in this task not even `hilclaw/model_binding.py`; a later part of the slice will add the binder and adjust this test);
     - a call writes no file.
7. **Effect of the new kind on other modules.**
   - Before committing, search `hilclaw/` for code that relies on `keys.op_signature_key` refusing a kind it did not know, or that assumes every known kind has members `m`, `n` or `m`, `k`, `n` (for example code that reads `shape["n"]` after the key check). Candidates include `spec.py`, `spec_tool.py`, `key_records.py`, `case_lookup.py`, `instance.py`, `instance_start.py`, `run_admission.py`, `check_admission.py`, `check_definition.py` and `model_binding.py`. T-0442 `## Result` lists what changed when `swiglu` became known; use it as the checklist.
   - List in `## Result` each place whose answer for a `rope` record changes. For example, a refusal that used to come from the key check and now comes from the contract check.
   - Nothing may now treat a `rope` record as covered by a `gemm`, `rmsnorm`, `elementwise_add` or `swiglu` contract, and nothing may raise a `KeyError` on a valid `rope` record where it used to refuse it.
   - If some place would need a code change to stay correct, do not make it here. Stop and return BLOCKED (`requirement-unclear`) with the place named.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except the two expected-message edits and the additions of criterion 5 in `tests/test_keys.py`.
   - Line and function coverage of `hilclaw/` stay >= 80%, and the new module is at 100% line coverage.
   - CI is green. The CI test-existence check finds `tests/test_rope_bf16_contract.py`.
9. **No other file changes.** Do not edit:
   - `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/rmsnorm_bf16_contract.py`, `hilclaw/elementwise_add_bf16_contract.py`, `hilclaw/swiglu_bf16_contract.py`, `hilclaw/model_binding.py`, `hilclaw/spec.py`, `hilclaw/spec_tool.py`, any registry, tool or executor module, any C file;
   - any test other than `tests/test_keys.py` and the new test file;
   - any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`. ADR text that says `hilclaw.keys` knows fewer kinds becomes less exact (for example ADR-0031 lines 21 and 98, ADR-0161 Consequences "A-13 reading"). Note that in `## Result` and do not edit the ADRs.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0445-<slug>`, Draft PR whose title contains `T-0445` and whose body ends with `Task: T-0445`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: pure data and validation over `hilclaw.keys`, as its GEMM, RMSNorm, elementwise add and SwiGLU counterparts).
    - The reviewer checks at least:
      - the prototype text (operand names and order `x`, `freqs_cis`, `out`; `float` for the table), the operand dtypes and shapes, the six directory names, the sha256 at T = 1, H = 8 and the 256 patterns against ADR-0161;
      - that the module adds no meaning beyond ADR-0161 (no table, constant, position, tolerance, accuracy bound, domain, generator, seed, build flag, binding or registration), and that the even-`d` rule is exactly decision 11's;
      - the absence of the five other module names in the new module;
      - that the only edits to existing tests are the two expected-message changes of criterion 5;
      - the criterion 7 list.

## Out of Scope

- The host-side table builder of ADR-0161 decision 4 and its tests; the RoPE constants (`rope_theta`, the scaling constants) in the model parameters; anything that depends on HQ-0070.
- The bf16 RoPE binding check in `hilclaw/model_binding.py` with the call sites `rope_q` and `rope_k` (decision 15), the copies of the Q and K ranges (decision 6) and the "every shape" binding.
- The model program and build/run steps calling `hilclaw_rope_bf16`; hand-written bf16 RoPE kernel fixtures; any C code.
- The P2-12 harness: generator, seed, draws, choice of T = 1 row, the content of `out` before a call, widening, comparison, tolerance values.
- Registering the contract with `correctness.check`, `spec.write` or the instance start.
- The SDPA with KV cache contract; fp16; an fp32 contract of this kind; backends other than `cpu_standin`.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next parts of the ADR-0161 code slice: the host-side table builder with tests against the rule of decision 4 (correctly rounded binary32 entries, checked against a higher-precision evaluation; the scale factor as an input, since HQ-0070 is open), then the RoPE binding check in `hilclaw/model_binding.py` with `rope_q` and `rope_k`, in the pattern of T-0443. After that, the SDPA with KV cache contract record (doc).

## Result


- **Outcome**: DONE. PR #262 squash-merged as `849fffa` (branch `claude/T-0445-rope-bf16-contract-values` deleted).
- **Review**: 1 round, Approve; non-blocking notes: the input change in `test_unknown_kind_message_lists_all_known_kinds` (below) accepted; the less-exact ADR note belongs in this Result; merge only after CI green (done).
- **CI**: green on all six jobs (C gate, Coverage gate, Python gate 3.11/3.14, Test presence, sh gate; run 40098895878).
- **Local gates**: `ruff check` and `ruff format --check` clean; full local `pytest` under coverage: 28757 passed, 949 skipped; `hilclaw/` line coverage 97%, `keys.py` and `rope_bf16_contract.py` 100%.
- **Language**: Python - pure data and validation over `hilclaw.keys`, as its GEMM, RMSNorm, elementwise add and SwiGLU counterparts.
- **Changes**:
  - `hilclaw/keys.py`: `_SHAPE_MEMBERS` gains `rope` with `m`, `h`, `d`; the `op_signature_key` docstring names all five kinds; the unknown-kind message reads `kind: must be a known kind: elementwise_add, gemm, rmsnorm, rope, swiglu, got ...`. No even-`d` rule, no version change.
  - New `hilclaw/rope_bf16_contract.py`: `KIND`, `DTYPE`, `TABLE_DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES` (6), `X_PATTERNS` (256), `op_signature_record`, `task_contract`, `covers`; odd `d` refused with `shape.d: must be even, got ...`. No table, `rope_theta`, scaling constant, position, tolerance, generator or binding. Private helpers and the x set duplicate those of the other bf16 contract modules on purpose (commit body says so).
  - `tests/test_keys.py`: the two expected unknown-kind messages now list `rope`. Deviation from criterion 5's letter: `test_unknown_kind_message_lists_all_known_kinds` used `"rope"` as its unknown kind, which is now known (the record would be refused by the shape check instead), so its input became `"sdpa"`; stated in the commit and PR body, accepted by the reviewer. New `rope` cases (ADR-0161 canonical line, sha256, name `rope-c797475e043d4156`, member sets incl. the gemm and swiglu sets, odd/zero `d` accepted by the keys, other kinds unchanged).
  - New `tests/test_rope_bf16_contract.py`.
- **Criterion 7**: `keys.op_signature_key` now accepts a `rope` record, so `spec.validate`, `instance.py`, `key_records`/`key_store_tool` and `case_lookup`/`case_tool` treat it as valid. `spec_tool`, `instance_start`/`start_instance`, `run_admission`/`check_admission`/`check_definition` (and `check_tool` through it) with `gemm_contract.covers` now refuse it as `op_signature_not_covered` instead of through the key check (they read `shape["k"]`/`shape["n"]` only after `covers` returns True, so no `KeyError`). The `covers` of the gemm, gemm_bf16, rmsnorm_bf16, elementwise_add_bf16 and swiglu_bf16 contracts return False instead of raising (tested). `model_binding.py` does not rely on the key check refusing the kind. No code change was needed. The other contract tests' `REFUSED` entries `dict(RECORD, kind="rope")` stay refused (shape-member mismatch) and pass unchanged.
- **Less exact, not edited**: ADR-0031 lines 21 and 98 (the kinds `hilclaw.keys` knows); ADR-0161 Consequences "A-13 reading" ("`hilclaw/` is not touched").
- **Follow-ups**: none new beyond the planner follow-up (host-side table builder, then the RoPE binding check in `hilclaw/model_binding.py` with `rope_q`/`rope_k`; that part will add `model_binding.py` as the binder and adjust `test_module_imports_keys_only_and_is_named_by_no_other_module`).
