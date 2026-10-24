---
id: T-0449
title: Teach hilclaw.keys the kind sdpa_kv_cache (members m, l, h, h_kv, d) and add hilclaw/sdpa_kv_cache_bf16_contract.py - the op-side values of the bf16 SDPA with KV cache contract of ADR-0162 (constants, prototype, the four shapes, the input value set, op_signature_record, task_contract, covers) with tests (ADR-0162 code slice, first part)
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0448]
touchesFiles: [hilclaw/keys.py, hilclaw/sdpa_kv_cache_bf16_contract.py, tests/test_sdpa_kv_cache_bf16_contract.py, tests/test_keys.py]
estimatedSize: {loc: 240, files: 2}
hq: []
---
## Why

**State on `main` `389ce34`.**
- ADR-0162 (T-0448, landed as `632f02a`) defines the contract of (`sdpa_kv_cache`, `bf16`, `row_major`, `c`) on `cpu_standin`. It is the sixth and last Llama kind contract of PLAN P2-11. With it, every kind of ADR-0152 decision 2 has a bf16 contract record.
- The other five kinds already have code: kind in `hilclaw.keys`, a contract module and a binding check in `hilclaw/model_binding.py`. For RoPE that was T-0445, T-0446 and T-0447.
- No code knows `sdpa_kv_cache` yet. `hilclaw.keys._SHAPE_MEMBERS` holds `elementwise_add`, `gemm`, `rmsnorm`, `rope` and `swiglu` only, so `keys.op_signature_key` refuses every `sdpa_kv_cache` record.
- ADR-0162 Consequences ("The code slices this record makes possible") list, in order:
  1. the kind and members in `hilclaw.keys` and a contract module (`task_contract`, `covers`, `op_signature_record`, the value set);
  2. the binding check in `hilclaw/model_binding.py` with the call site `sdpa`;
  3. the two cache buffers per layer and the V copy in the model program;
  4. hand-written kernel fixtures;
  5. the P2-12 harness part with its cache comparison.

**This task is item 1.** Every later item imports the module or needs the kind in `hilclaw.keys`, so it comes first. The RMSNorm, add, SwiGLU and RoPE slices were split the same way (T-0436, T-0439, T-0442, T-0445).

**PLAN order and D18.** P2 runs in list order. Unresolved HQs in `PROCESS/STATE.json` still hold the round-loop items and P2-5:
- HQ-0021: round 0's board step;
- HQ-0048 and HQ-0024: the round >= 1 steps, P2-6 and P2-7;
- the gate half of P2-4 is owner-only (OD-3).

P2-10 comes after P2-5, so work goes on with P2-11 to P2-14. This task is the code of a P2-11 contract record. P2-13 and P2-14 need it: ADR-0157 decision 4 keeps `bf16` an invalid model dtype while a call-site kind lacks a bf16 contract. It is not a follow-up, a wording fix or input hardening, so the D18 rule does not set it aside. The HQ-0034 follow-up (OpenMP) is already in the PLAN "보류" section and is not part of this task.

**§9, A-13, open HQs and D16.**
- No open decision is needed. Every value comes from ADR-0162 as accepted (owner notice on #5, issuecomment-6386983591, 7-day window). The value-set constant name and the wording of the two cross-dimension messages (criterion 2) are code choices, not design decisions.
- ADR-0162 Status lists the open HQs it does not cross (HQ-0033, HQ-0034, HQ-0069, HQ-0070). This module holds no build setting, no table and no runtime fact, so it crosses none of them either.
- A new `kind` with its shape members raises no `schema_version` (ADR-0001 decision 6; ADR-0162 Status "Not changed" and Consequences "A-13 reading"). The role `inout` already exists in `hilclaw/spec.py` (`_ROLES`, line 58). So this is not a data-plane schema change in the A-13 sense. If the executor or reviewer finds otherwise, stop and return BLOCKED (A-13 schema change).
- Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (line 72): executor procedure, resume rule, time limit;
  - §5 (lines 86-114): task format; naming (branch `claude/T-0449-<slug>`, PR title with `T-0449`, commit trailer `Task: T-0449`, last line of the PR body `Task: T-0449`); size cap; test rules.
- `CLAUDE.md`, "상시 규칙": especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0162-od31-bf16-sdpa-kv-cache-contract.md`:
  - decisions 1 to 3 (lines 37-50): scope; one kind for prefill and decode; kind `sdpa_kv_cache` with members `m`, `l`, `h`, `h_kv`, `d`. P, the capacity and the scale are not members or parameters;
  - decision 4 (lines 52-59): the cache operands, their dtype, the `[l, h_kv, d]` layout, and no capacity in the contract;
  - decision 5 (lines 61-66): the other operands and their shapes;
  - decisions 6 to 8 (lines 68-92): the operation, the precision and the output rounding. Read them only to know what this module must NOT represent;
  - decision 9 (lines 94-101): the prototype, byte for byte, its operand order and the symbol;
  - decision 10 (lines 103-131): the operand entries, the `task.contract` example at T = 1, L = 128, and its validation (accepted; refused with a capacity shape `[256, 8, 64]`);
  - decision 11 (lines 133-147): the guarantees. In particular, the "Dimensions" row says "m ≥ 1, l ≥ m, h_kv ≥ 1, h a multiple of h_kv, d ≥ 1", and "No shape with a 0" applies;
  - decision 13 (lines 153-159): the input value set, and what is left to P2-12;
  - decision 14 (lines 161-175): the op_signature rule, the canonical line, the sha256 and the four directory names;
  - Consequences (lines 212-220).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md`, decisions 2 and 6: member names are fixed per kind, and a new kind raises no version.
- `hilclaw/rope_bf16_contract.py`, the whole file (200 lines). This is the model for the new module: the same function set, argument checks, extra-rule check (there: even `d`), error class, message prefix (`shape.<name>: `) and docstring style. Read only; do not edit.
- `hilclaw/keys.py`: lines 1-46 (module docstring, `_NAME`, `_SHAPE_MEMBERS`) and `op_signature_key` (lines 138-171). Its docstring names the known kinds and their members (lines 143-155). Line 166 builds the unknown-kind message from the sorted kind names. Line 168 builds the member message from the sorted member names, so the new message reads `exactly the members d, h, h_kv, l, m`.
- `tests/test_rope_bf16_contract.py`, the whole file (616 lines):
  - the record copies;
  - `OTHER_CONTRACTS` and `OTHER_MODULE_NAMES` (lines 92-106);
  - the spec-validation pattern (lines 264-282);
  - the covers tests (lines 487-562);
  - the public-names test, the imports/binder test (line 588) and the no-file test (line 604).

  Line 588's test asserts that the text `rope_bf16_contract` appears in no `hilclaw/*.py` file other than that module and `hilclaw/model_binding.py`. The tests of the gemm, gemm_bf16, rmsnorm_bf16, elementwise_add_bf16 and swiglu_bf16 modules assert the same for their own names. Read only; do not edit.
- `tests/test_keys.py`:
  - lines 598-604 (`test_unknown_kind_is_rejected`);
  - lines 663-668 (`test_unknown_kind_message_lists_all_known_kinds`; its input `"sdpa"` stays unknown);
  - lines 800-880 (the `rope` tests and `test_other_kinds_keep_their_members_beside_rope`).
- `tests/test_instance.py` lines 3190-3201: unknown kinds `attention`, `conv`, `gemm2`, `matmul`. They stay unknown; no edit.
- `PROCESS/tasks/T-0445-rope-bf16-contract-values.md`, `## Result`: the criterion 7 list for `rope`. Use it as the checklist for criterion 7 here.
- `examples/spec/gemm-485b9bc494d477eb.json` and `hilclaw/spec.py` `validate` (from line 71; the operand checks around lines 205-240: operand shape values must be values of the record's shape; `_ROLES` at line 58). ADR-0162 decision 10 validated its example inside that spec, with the op_signature replaced.

## Acceptance Criteria

1. **`hilclaw/keys.py`**:
   - `_SHAPE_MEMBERS` gains `"sdpa_kv_cache": frozenset({"m", "l", "h", "h_kv", "d"})` (ADR-0162 decision 3).
   - The docstrings that name the known kinds (`op_signature_key`, and any other in the file) name all six kinds and their members.
   - No other change. There is no new public name, no version change and no other rule. In particular, `hilclaw.keys` does not learn `l >= m` or "h a multiple of h_kv"; those rules belong to the contract (criterion 2).
   - The unknown-kind message keeps its form, so it becomes `kind: must be a known kind: elementwise_add, gemm, rmsnorm, rope, sdpa_kv_cache, swiglu, got ...`.
2. **New module `hilclaw/sdpa_kv_cache_bf16_contract.py`** (Python; standard library and `hilclaw.keys` only). Its public names are exactly:
   - `KIND` = `"sdpa_kv_cache"`, `DTYPE` = `"bf16"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"` (decisions 1, 3, 4 and 10).
   - `PROTOTYPE`: the single line of decision 9, byte for byte:
     `void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);`
   - `SHAPES`: the four `(m, l, h, h_kv, d)` tuples of decision 14, in the order of its table (S = 128 prefill, S = 128 decode, S = 2048 prefill, S = 2048 decode):
     - `(128, 128, 32, 8, 64)`
     - `(1, 128, 32, 8, 64)`
     - `(2048, 2048, 32, 8, 64)`
     - `(1, 2048, 32, 8, 64)`
   - `INPUT_PATTERNS`: the 256 `uint16_t` bit patterns of the value set of decision 13, as a `tuple` of `int` in ascending order: `0x3F00`-`0x3F7F` and `0xBF00`-`0xBF7F`, i.e. ±(0.5 + j/256) for j = 0..127, the set of ADR-0156 decision 9. The module docstring says that the set applies to every element of `q`, `k_new`, `v_new` and of cache rows 0 … P − 1.
   - What the module does not hold:
     - No scale constant, position, capacity, accuracy-bound constant (`u`, ε, A), domain constant (the bounds of D) or other constant. Decision 3 keeps the scale and P out of the key and the prototype, and decision 4 keeps the capacity out.
     - No generator, seed, draw count, content of cache rows P … l − 1 or of `out` before a call, guard rows, cache comparison or widening. Those belong to the P2-12 harness record (decision 13).
     - No tolerance.
   - `op_signature_record(m, l, h, h_kv, d)`, `task_contract(m, l, h, h_kv, d)` and `covers(record)` behave like the functions of the same names in `hilclaw/rope_bf16_contract.py`, with this module's constants and five dimensions. In particular:
     - **Each dimension** is exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`. A refused dimension raises `keys.InvalidRecordError` with a message starting `shape.<name>: `, checked in the order `m`, `l`, `h`, `h_kv`, `d`. A 0 is refused because ADR-0037's reading carries over (decision 11).
     - **The two cross rules of decision 11** are checked after every dimension passes:
       - `l < m` is refused with a message starting `shape.l: ` that says `l` must be at least `m`;
       - `h % h_kv != 0` is refused with a message starting `shape.h: ` that says `h` must be a multiple of `h_kv`.

       Use the message form of the other checks (`must be ..., got <value>`).
     - **`op_signature_record`** returns a new record with `shape` members `m`, `l`, `h`, `h_kv`, `d`, `dtype` `"bf16"` and `layout` `"row_major"`, and no `ext` or `label`.
     - **`task_contract`** returns new objects: `language` `"c"`, the prototype, and the six operand entries of decision 10 in this order:
       - `q` (`input`, `bf16`, `[m, h, d]`)
       - `k_new` (`input`, `bf16`, `[m, h_kv, d]`)
       - `v_new` (`input`, `bf16`, `[m, h_kv, d]`)
       - `cache_k` (`inout`, `bf16`, `[l, h_kv, d]`)
       - `cache_v` (`inout`, `bf16`, `[l, h_kv, d]`)
       - `out` (`output`, `bf16`, `[m, h, d]`)
     - **`covers`** first validates with `keys.op_signature_key` and re-raises its error. It returns exactly `True` only when all of these hold, and ignores `ext` and `label`:
       - kind `sdpa_kv_cache`, dtype `bf16`, layout `row_major`;
       - every dimension >= 1;
       - `l >= m`;
       - `h` a multiple of `h_kv`.
     - Arguments are not modified.
3. **No coupling to the other contract modules.**
   - The new module does not import `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract`, `hilclaw.rmsnorm_bf16_contract`, `hilclaw.elementwise_add_bf16_contract`, `hilclaw.swiglu_bf16_contract` or `hilclaw.rope_bf16_contract`.
   - Its text, docstrings included, contains none of the strings `gemm_contract`, `gemm_bf16_contract`, `rmsnorm_bf16_contract`, `elementwise_add_bf16_contract`, `swiglu_bf16_contract` and `rope_bf16_contract`. Otherwise the binder tests named in Required Reading would fail, and those files are not to be edited. A docstring may cite ADR-0156 to ADR-0161 by number.
   - So the private helpers and the patterns are the module's own. This small duplication is accepted, as T-0436, T-0439, T-0442 and T-0445 accepted it. Say so in the commit body.
   - No other `hilclaw/` module imports or names the new module in this task. It is bound to no tool, registry, `correctness.check`, `spec.write` or `model_binding`. The first case stays fp32 `gemm`.
4. **Docstrings.**
   - The module docstring states the record (ADR-0162, building on ADR-0008, ADR-0037 and ADR-0156) and the values the module returns. It says that `INPUT_PATTERNS` is the value set of decision 13 and names the operands and cache rows it applies to. It states that the operand shapes are those of the first `l` rows, never a capacity (decisions 4 and 10).
   - It also states what the module does not do:
     - no scale, position, capacity or bound constant;
     - no spec building;
     - no binding, no tool, no file, no process, no command-line entry;
     - no harness mechanism for `INPUT_PATTERNS`;
     - no other contract.
   - It says that the following are not represented in any returned value beyond the prototype text and the two cross rules: the operation (decision 6), the precision and its bound (decision 7), the output rounding (decision 8), the cache write and the other guarantees of a call (decisions 4 and 11), and what the kernel source provides (decision 12).
   - Each public function has a Doxygen-like docstring in the style of `hilclaw/rope_bf16_contract.py`. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests, `tests/test_keys.py`**: add cases for `sdpa_kv_cache`.
   - A valid record gives a name starting `sdpa_kv_cache-`.
   - The T = 1, L = 128 record of ADR-0162 decision 14 gives:
     - the canonical line `{"dtype":"bf16","kind":"sdpa_kv_cache","layout":"row_major","schema_version":1,"shape":{"d":64,"h":32,"h_kv":8,"l":128,"m":1}}`;
     - the sha256 `9f8c153fbe19c8ee934d21fd64dd8d20e788b76208c8e0f03b8117a754bb4361`;
     - the name `sdpa_kv_cache-9f8c153fbe19c8ee`.
   - Wrong member sets are refused with `^shape: must be a map with exactly the members d, h, h_kv, l, m`. Cover at least: `l` missing, an extra `p`, `capacity` in place of `l`, the `rope` set and the `gemm` set.
   - `op_signature_key` accepts `l < m`, `h` not a multiple of `h_kv`, and a 0 dimension. Those rules belong to the contract.
   - The other five kinds keep exactly their members.
   - The two existing assertions on the unknown-kind message (lines 602 and 666) no longer match once `sdpa_kv_cache` is added to the sorted list. Change only their expected text, to `elementwise_add, gemm, rmsnorm, rope, sdpa_kv_cache, swiglu`. Their input `"sdpa"` stays unknown and stays as it is. Do not remove or weaken any other existing test.
6. **Tests, new file `tests/test_sdpa_kv_cache_bf16_contract.py`** (D12: happy, error, branch and negative cases; every public function and constant). It covers at least:
   - **Record copies**:
     - the constants and `PROTOTYPE` equal the text copied from decisions 3, 9 and 10;
     - `task_contract(1, 128, 32, 8, 64)` equals the JSON example of decision 10.
   - **Directory names**: for each shape of `SHAPES`, `keys.op_signature_key(op_signature_record(*shape)).name` equals the decision 14 table. Copy the four names into the test, in the order of `SHAPES`:
     - `sdpa_kv_cache-3a4be50bca85d0dc`
     - `sdpa_kv_cache-9f8c153fbe19c8ee`
     - `sdpa_kv_cache-e9326c7e4ba5e1c7`
     - `sdpa_kv_cache-50b3bf3bcc1ad96d`

     The canonical text and sha256 at T = 1, L = 128 equal the decision 14 lines.
   - **Spec validation**, with a spec built like the one in `tests/test_rope_bf16_contract.py` from this module's `op_signature_record` and `task_contract`:
     - it passes `hilclaw.spec.validate` for each shape of `SHAPES` and for one small shape such as `(2, 3, 4, 2, 5)`;
     - at T = 1, L = 128, the same spec with the shape of `cache_k` set to `[256, 8, 64]` is refused, as decision 10 recorded.
   - **`INPUT_PATTERNS`**:
     - length 256, ascending, all distinct, each an `int` in 0..0xFFFF;
     - each pattern, widened to fp32 by `pattern << 16` (`struct`), is finite, has magnitude in [0.5, 1) and equals ±(0.5 + j/256);
     - both signs of every magnitude are present.
   - **`covers`**:
     - `True` for a record of each shape in `SHAPES`, and for small shapes including `l == m`, `h == h_kv` and `d` odd (for example `(1, 1, 1, 1, 1)` and `(2, 3, 4, 2, 5)`);
     - `True` with an `ext` or `label` present;
     - `False` for an fp32 `sdpa_kv_cache` record and for another dtype or layout value;
     - `False` for a valid record with a 0 dimension (each member), with `l < m`, or with `h` not a multiple of `h_kv` (for example `h = 6, h_kv = 4`);
     - `False` for valid bf16 `gemm`, `rmsnorm`, `elementwise_add`, `swiglu` and `rope` records;
     - `False` for a record of another kind known only through a monkeypatched `keys._SHAPE_MEMBERS` with the same five members;
     - raises `InvalidRecordError` for an invalid record or an unknown kind;
     - leaves the argument unchanged.
   - **The other contracts do not cover this kind**: the `covers` of `hilclaw.gemm_contract`, `hilclaw.gemm_bf16_contract`, `hilclaw.rmsnorm_bf16_contract`, `hilclaw.elementwise_add_bf16_contract`, `hilclaw.swiglu_bf16_contract` and `hilclaw.rope_bf16_contract` each return `False` for a valid `sdpa_kv_cache` record at each shape, at dtype `bf16` and `fp32`. The test file may import those modules; criterion 3 restricts only the new module's own text.
   - **Negative dimensions**, for `op_signature_record` and `task_contract`:
     - for each of the five dimensions: `bool`, an `int` subclass, `float`, `str`, `None`, 0, a negative value and `MAX_INTEGER + 1`; each message starts with the right `shape.<name>: `;
     - `l < m` (for example `(2, 1, 32, 8, 64)`) gives `shape.l: `;
     - `h` not a multiple of `h_kv` (`(1, 1, 6, 4, 2)` and `(1, 1, 1, 2, 1)`) gives `shape.h: `;
     - when several rules fail, the first one in the order of criterion 2 is the one named;
     - wrong argument counts raise `TypeError`.
   - **Independence**:
     - results are new objects; mutating one does not change the next;
     - the public names are exactly those of criterion 2;
     - the module imports only the standard library, `hilclaw` and `hilclaw.keys`;
     - its text has none of the six module names of criterion 3;
     - no other `hilclaw/*.py` file names `sdpa_kv_cache_bf16_contract`. In this task that includes `hilclaw/model_binding.py`; the binding part of the slice will add it as the binder and adjust this test;
     - a call writes no file.
7. **Effect of the new kind on other modules.**
   - Before committing, search `hilclaw/` for code that relies on `keys.op_signature_key` refusing a kind it did not know. Also look for code that assumes every known kind has members `m`, `n` / `m`, `k`, `n` / `m`, `h`, `d`, for example code that reads `shape["n"]` after the key check.
   - Candidates include `spec.py`, `spec_tool.py`, `key_records.py`, `case_lookup.py`, `instance.py`, `instance_start.py`, `run_admission.py`, `check_admission.py`, `check_definition.py` and `model_binding.py`. T-0445 `## Result` lists what changed when `rope` became known; use it as the checklist.
   - Also check whether any code treats the role `inout` in a way a spec of this contract would hit for the first time. For example, code that assumes every non-`input` operand is an `output`, or that counts outputs.
   - List in `## Result` each place whose answer for an `sdpa_kv_cache` record changes. For example, a refusal that used to come from the key check and now comes from the contract check.
   - After this task:
     - nothing may treat an `sdpa_kv_cache` record as covered by another contract;
     - nothing may raise a `KeyError` on a valid `sdpa_kv_cache` record where it used to refuse it.
   - If some place would need a code change to stay correct, do not make it here. Stop and return BLOCKED (`requirement-unclear`) with the place named.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except the two expected-message edits and the additions of criterion 5 in `tests/test_keys.py`.
   - Line and function coverage of `hilclaw/` stay >= 80%, and the new module is at 100% line coverage.
   - CI is green, and the CI test-existence check finds `tests/test_sdpa_kv_cache_bf16_contract.py`.
9. **No other file changes.** Do not edit:
   - any other `hilclaw/` module: the six contract modules, `hilclaw/model_binding.py`, `hilclaw/spec.py`, `hilclaw/spec_tool.py`, any registry, tool or executor module;
   - any C file;
   - any test other than `tests/test_keys.py` and the new test file;
   - any `ARCHITECTURE/` or `PROCESS/` file other than this task file's `## Result`.

   ADR text that says `hilclaw.keys` knows fewer kinds becomes less exact: for example ADR-0031 lines 21 and 98, and ADR-0162 Consequences "A-13 reading" ("`hilclaw/` is not touched"). Note those places in `## Result` and do not edit the ADRs.
10. **Process**: code mode (CLAUDE.md A-13).
    - Use branch `claude/T-0449-<slug>`. Open a Draft PR whose title contains `T-0449` and whose body ends with `Task: T-0449`.
    - Run the context-isolated reviewer cycle (dev-code-review) to Approve and wait for CI green. Then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice: Python, pure data and validation over `hilclaw.keys`, as the other five bf16 contract modules.
    - The reviewer checks at least:
      - the prototype text: operand names and order `q`, `k_new`, `v_new`, `cache_k`, `cache_v`, `out`, and `const` on the three inputs only;
      - the operand roles (`inout` for the caches), dtypes and shapes (`[l, h_kv, d]` for the caches, never a capacity);
      - the four directory names, the sha256 at T = 1, L = 128, and the 256 patterns, all against ADR-0162;
      - that the module adds no meaning beyond ADR-0162: no scale, position, capacity, tolerance, bound, domain, generator, seed, build flag, binding or registration;
      - that the two cross rules are exactly the "Dimensions" row of decision 11;
      - that the new module contains none of the six other module names;
      - that the only edits to existing tests are the two expected-message changes of criterion 5;
      - the criterion 7 list.

## Out of Scope

- The bf16 SDPA binding check in `hilclaw/model_binding.py` with the call site `sdpa`, its (m, l) shapes and the "every shape" binding (decision 15).
- The model program's cache buffers, the V copy, and the build and run steps that call `hilclaw_sdpa_kv_cache_bf16`. Hand-written SDPA kernel fixtures; any C code.
- The P2-12 harness:
  - generator, seed and draws;
  - the content of cache rows P … l − 1 and of `out` before a call, and guard rows;
  - the cache comparison, widening and tolerance values.
- Registering the contract with `correctness.check`, `spec.write` or the instance start.
- Build settings and OpenMP (HQ-0033; the HQ-0034 follow-up in PLAN "보류"); fp16; an fp32 contract of this kind; backends other than `cpu_standin`.
- Any edit to an ADR, Requirements, OpenDecisionProposals or StandardScenarios.
- The PLAN "보류" items.

## Follow-ups

- (planner) Next part of the ADR-0162 code slice: the `sdpa` binding check in `hilclaw/model_binding.py` in the pattern of T-0447. That part adds `model_binding.py` as the binder and adjusts the imports/binder test of the new test file. After it, the next P2-11 to P2-13 steps are the model program's cache buffers and V copy (ADR-0153 decision 4) and the P2-12 harness record.

## Result

