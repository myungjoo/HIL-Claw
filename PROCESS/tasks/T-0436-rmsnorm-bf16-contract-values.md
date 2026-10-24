---
id: T-0436
title: Teach hilclaw.keys the kind rmsnorm (members m, n) and add hilclaw/rmsnorm_bf16_contract.py - the op-side values of the bf16 RMSNorm contract of ADR-0158 (constants, prototype, shapes, input patterns, eps, op_signature_record, task_contract, covers) with tests (ADR-0158 code slice, first part)
phase: P1
status: DONE
commitMode: code
coversReq: [C-6, FR-5, FR-9, OD-31, OD-6, "PLAN P2-11", "PLAN P2-13", "PLAN P2-14"]
dependsOn: [T-0435]
touchesFiles: [hilclaw/keys.py, hilclaw/rmsnorm_bf16_contract.py, tests/test_rmsnorm_bf16_contract.py, tests/test_keys.py]
estimatedSize: {loc: 190, files: 2}
hq: []
---
## Why

**Where things stand** (as of `main` `69cba99`):
- ADR-0158 (T-0435, landed as `0792a9f`) defines the contract of (`rmsnorm`, `bf16`, `row_major`, `c`) on `cpu_standin`. It is the second Llama kind contract of PLAN P2-11, after the bf16 GEMM contract of ADR-0156.
- Its Consequences list the code slice it makes possible:
  1. the kind and its members in `hilclaw.keys`;
  2. a contract module like `hilclaw/gemm_bf16_contract.py` (constants, `task_contract`, `covers`, `op_signature_record`, the value set);
  3. fit and the "every shape" binding in `hilclaw/model_binding.py`, with the executor passing its `eps` as the nearest binary32 value;
  4. the libm linking question (with HQ-0033), hand-written bf16 RMSNorm kernel fixtures, and the P2-12 harness part.
- T-0435's planner follow-up names this slice as the next step.
- Today no code knows the kind: `hilclaw.keys._SHAPE_MEMBERS` holds `gemm` only, so `keys.op_signature_key` refuses every `rmsnorm` record (ADR-0031 line 98 describes that state).

**This task is part 1 of that slice**: items 1 and 2. Parts 3 and 4 import the module and need the kind in `hilclaw.keys`, so this comes first. ADR-0156's slice was split the same way (T-0430 first).

**PLAN order and D18.** PLAN P2 runs in list order. The round-loop items and P2-5 are still held by unresolved HQs in `PROCESS/STATE.json`:
- round 0's board step waits on HQ-0021;
- the round >= 1 steps and P2-6/P2-7 wait on HQ-0048 and HQ-0031;
- the gate half of P2-4 is owner-only (OD-3).

P2-10 comes after P2-5. So the work goes on with P2-11 to P2-14. This task is the code of a P2-11 contract record. P2-13 and P2-14 need it: ADR-0157 decision 4 keeps `bf16` an invalid model dtype while a call-site kind lacks a bf16 contract, and the forward pass cannot bind an RMSNorm kernel without these values. It is not a follow-up, wording or hardening item, so the D18 rule does not set it aside.

**§9, A-13 and D16.**
- No open decision is needed: every value comes from ADR-0158 as accepted.
- A new `kind` value with its shape members raises no `schema_version` (ADR-0001 decision 6). ADR-0158 Consequences ("A-13 reading") names teaching `hilclaw.keys` the kind as the later code slice, and ADR-0031 line 98 already describes how readers of other sources behave towards a kind they do not know. So this is not a data-plane schema change in the A-13 sense. If the executor or reviewer finds otherwise, stop and return BLOCKED (A-13 schema change).
- Nothing here starts `claude` or needs a board, a model file or an API key.

## Required Reading

- `PROCESS/DRIVER.md`:
  - §3 step 5 (executor procedure, resume rule, time limit; line 72);
  - §5 (task format; naming: branch `claude/T-0436-<slug>`, PR title with `T-0436`, commit trailer `Task: T-0436`, last line of the PR body `Task: T-0436`; size cap; test rules; lines 86-114).
- `CLAUDE.md`: "상시 규칙", especially "코멘트 최소화", "도구 계층 언어 정책", "브랜치·merge 절차" (code mode) and "테스트 규칙" (D12).
- `ARCHITECTURE/decisions/ADR-0158-od31-bf16-rmsnorm-contract.md`:
  - decision 1 (scope; lines 32-35);
  - decision 2 (kind, members `m` and `n`, dtype, rank-1 `row_major`; lines 37-42);
  - decision 5 (the prototype, byte for byte, and `eps` as a `float` parameter; lines 57-67);
  - decision 6 (operand entries and the `task.contract` example; lines 69-91);
  - decision 7, the "Every set of dimensions" and "No shape that holds a 0" bullets (lines 93-109);
  - decision 9 (the value set of x and w, and the verification `eps`; lines 116-121);
  - decision 10 (the op_signature rule, the canonical line and the three directory names; lines 123-137);
  - Consequences (lines 159-162).
- `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` decisions 2 and 6 (lines 37-62, 73-78): member names fixed per kind; a new kind raises no version.
- `ARCHITECTURE/decisions/ADR-0031-od8-instance-record-op-signature.md` lines 21 and 98 (what `hilclaw.keys` knowing one more kind means for readers).
- `hilclaw/gemm_bf16_contract.py`, the whole file (175 lines). This is the model for the new module: the same function set, argument checks, error class, message prefix (`shape.<name>: `) and docstring style. Read only; do not edit.
- `hilclaw/keys.py`: lines 1-46 (module docstring, `_NAME`, `_SHAPE_MEMBERS`) and `op_signature_key` (lines 132-162, its docstring says "only ``gemm`` is known").
- `tests/test_gemm_bf16_contract.py`, the whole file (492 lines): the record copies, the bad-value lists, the spec-validation pattern, `test_record_of_another_kind_is_not_covered` (line 401), and the public-names, imports/binder and no-file tests (lines 445-492). Line 467 asserts that no `hilclaw/*.py` file other than `hilclaw/model_binding.py` contains the text `gemm_bf16_contract`. `tests/test_gemm_contract.py` line 386 asserts the same for `gemm_contract` outside its four binders. Read only; do not edit.
- `tests/test_keys.py` lines 578-601 (the `gemm` member test and `test_unknown_kind_is_rejected`, whose regex `^kind: must be a known kind: gemm` must keep matching).
- `examples/spec/gemm-485b9bc494d477eb.json` and `hilclaw/spec.py` `validate`. ADR-0158 decision 6 validated its example inside that spec, with the op_signature replaced.

## Acceptance Criteria

1. **`hilclaw/keys.py`**:
   - `_SHAPE_MEMBERS` gains `"rmsnorm": frozenset({"m", "n"})` (ADR-0158 decision 2).
   - The docstrings that say only `gemm` is known (the `op_signature_key` docstring, and any other in the file) name both kinds and their members.
   - No other change: no new public name, no version change, no other rule.
2. **New module `hilclaw/rmsnorm_bf16_contract.py`** (Python; standard library and `hilclaw.keys` only). Its public names are exactly:
   - `KIND` = `"rmsnorm"`, `DTYPE` = `"bf16"`, `LAYOUT` = `"row_major"`, `LANGUAGE` = `"c"` (decisions 1 and 2);
   - `PROTOTYPE`: the single line of decision 5, byte for byte:
     `void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y);`
   - `SHAPES`: the three `(m, n)` tuples of decision 10, in table order: `(1, 2048)`, `(32, 2048)`, `(512, 2048)`;
   - `INPUT_PATTERNS`: the 256 `uint16_t` bit patterns of the value set of decision 9 for x and w, as a `tuple` of `int` in ascending order (`0x3F00`-`0x3F7F` and `0xBF00`-`0xBF7F`, i.e. ±(0.5 + j/256) for j = 0..127);
   - `EPS`: the verification `eps` of decision 9, the binary32 value nearest to 1e-05, as a Python `float` that is exactly that binary32 value (bit pattern `0x3727C5AC`).
   - The module defines the value set only. It has no generator, seed, draw count, widening or reference `eps` choice: those belong to the P2-12 harness record (decision 9). It chooses no tolerance.
   - `op_signature_record(m, n)`, `task_contract(m, n)` and `covers(record)` behave like the functions of the same names in `hilclaw/gemm_bf16_contract.py`, with two dimensions and this module's constants. In particular:
     - each dimension is exactly an `int` (`bool` and subclasses refused) from 1 to `keys.MAX_INTEGER`;
     - a refused dimension raises `keys.InvalidRecordError` with a message starting `shape.<name>: `; a 0 is refused because ADR-0037's reading carries over (decision 7);
     - `task_contract` returns new objects with the three operand entries of decision 6, in this order: `x` (`input`, `[m, n]`), `w` (`input`, `[n]`), `y` (`output`, `[m, n]`), each `dtype` `"bf16"`;
     - `covers` first validates with `keys.op_signature_key` (re-raising its error). It returns exactly `True` only for kind `rmsnorm`, dtype `bf16`, layout `row_major` and every dimension >= 1, and ignores `ext` and `label`;
     - arguments are not modified.
3. **No coupling to the GEMM modules.**
   - The new module does not import `hilclaw.gemm_contract` or `hilclaw.gemm_bf16_contract`.
   - Its text, docstrings included, contains neither `gemm_contract` nor `gemm_bf16_contract`. The binder tests named in Required Reading would fail otherwise, and those files are not to be edited. A docstring may cite ADR-0156 by number.
   - So the private helpers and the 256 patterns are the module's own. This small duplication is accepted. Say so in the commit body.
   - No other `hilclaw/` module imports or names the new module in this task. It is bound to no tool, registry, `correctness.check`, `spec.write` or `model_binding`. The first case stays fp32 `gemm`.
4. **Docstrings.**
   - The module docstring states the record (ADR-0158, building on ADR-0008, ADR-0037 and ADR-0156) and the values it returns. It also states what the module does not do:
     - no spec building;
     - no binding, no tool, no file, no process, no command-line entry;
     - no harness mechanism for `INPUT_PATTERNS` and `EPS`;
     - no other contract.
   - Each public function has a Doxygen-like docstring in the style of `hilclaw/gemm_bf16_contract.py`. Other comments follow CLAUDE.md "코멘트 최소화".
5. **Tests, `tests/test_keys.py`**: add cases for `rmsnorm`:
   - a valid record gives a name starting `rmsnorm-`, and the T = 1 record of ADR-0158 decision 10 gives `rmsnorm-57f1bdf44f626c31` with the canonical line of that decision;
   - wrong member sets are refused with `^shape: must be a map with exactly the members m, n` (missing `n`, an extra `k`, the `gemm` set);
   - a `gemm` record still requires exactly `m`, `k`, `n`;
   - the unknown-kind message lists `gemm, rmsnorm`.

   Do not remove or weaken an existing test.
6. **Tests, new file `tests/test_rmsnorm_bf16_contract.py`** (D12: happy, error, branch and negative cases, every public function and constant). It covers at least:
   - **Record copies**: the constants and `PROTOTYPE` equal the text copied from decisions 2 and 5; `task_contract(1, 2048)` equals the JSON example of decision 6.
   - **Directory names**: for each shape of `SHAPES`, `keys.op_signature_key(op_signature_record(*shape)).name` equals the decision 10 table. Copy the three names into the test: `rmsnorm-57f1bdf44f626c31`, `rmsnorm-953c4d92b64130ba`, `rmsnorm-3aba1dcd072652b7`. The canonical text at T = 1 equals the decision 10 line.
   - **Spec validation**: a spec built like the one in `tests/test_gemm_bf16_contract.py`, with this module's `op_signature_record` and `task_contract`, passes `hilclaw.spec.validate` for each shape of `SHAPES` and one small shape.
   - **`INPUT_PATTERNS`**: length 256, ascending, all distinct, each an `int` in 0..0xFFFF. Each, widened to fp32 by `pattern << 16` (`struct`), is finite, has magnitude in [0.5, 1), and equals ±(0.5 + j/256). Both signs of every magnitude are present.
   - **`EPS`**: a `float`; packing it as binary32 and unpacking gives it back unchanged; its bit pattern is `0x3727C5AC`; it is the binary32 value nearest to 1e-05 (its neighbours are farther away).
   - **`covers`**:
     - `True` for a record of each shape in `SHAPES` and for a small shape;
     - `True` with an `ext` or `label` present;
     - `False` for an fp32 `rmsnorm` record, for another dtype or layout value, and for a valid record with a 0 dimension;
     - `False` for a valid bf16 `gemm` record;
     - `False` for a record of another kind known only through a monkeypatched `keys._SHAPE_MEMBERS`;
     - raises `InvalidRecordError` for an invalid record or an unknown kind;
     - the argument is unchanged.
   - **Negative dimensions** for `op_signature_record` and `task_contract`: `bool`, an `int` subclass, `float`, `str`, `None`, 0, a negative value, `MAX_INTEGER + 1`. Each error message starts with the right `shape.<name>: `.
   - **Independence**:
     - results are new objects (mutating one does not change the next);
     - the public names are exactly those of criterion 2;
     - the module imports only the standard library, `hilclaw` and `hilclaw.keys`;
     - its text has neither `gemm_contract` nor `gemm_bf16_contract`;
     - no other `hilclaw/*.py` file names `rmsnorm_bf16_contract`;
     - a call writes no file.
7. **Effect of the new kind on other modules.**
   - Before committing, search `hilclaw/` for code that relies on `keys.op_signature_key` refusing a non-`gemm` kind. Candidates include `spec.py`, `spec_tool.py` (it refuses records `gemm_contract.covers` does not cover), `key_records.py`, `case_lookup.py` and `instance.py`.
   - List in `## Result` each place whose answer for an `rmsnorm` record changes. For example, a refusal that used to come from the key check and now comes from the contract check.
   - Nothing may now treat an `rmsnorm` record as covered by a `gemm` contract.
   - If some place would need a code change to stay correct, do not make it here. Stop and return BLOCKED (`requirement-unclear`) with the place named.
8. **Gates.**
   - `ruff check` and `ruff format --check` are clean.
   - The whole `pytest` suite passes locally. Every existing test passes unchanged, except the additions of criterion 5 to `tests/test_keys.py`.
   - Line and function coverage of `hilclaw/` stay >= 80%, and the new module is at 100% line coverage.
   - CI is green. The CI test-existence check finds `tests/test_rmsnorm_bf16_contract.py`.
9. **No other file changes.** Do not edit:
   - `hilclaw/gemm_contract.py`, `hilclaw/gemm_bf16_contract.py`, `hilclaw/model_binding.py`, `hilclaw/spec.py`, `hilclaw/spec_tool.py`, any registry or tool module, any C file;
   - any test other than `tests/test_keys.py` and the new test file;
   - any `ARCHITECTURE/` or `PROCESS/` file. ADR-0031's "knows `gemm` only" becomes less exact. Note that in `## Result` and do not edit the ADR.
10. **Process**: code mode (CLAUDE.md A-13).
    - Branch `claude/T-0436-<slug>`, Draft PR whose title contains `T-0436` and whose body ends with `Task: T-0436`.
    - Context-isolated reviewer cycle (dev-code-review) to Approve; CI green; then squash-merge with `gh pr merge --squash --body` and delete the branch.
    - The commit body has one line on the language choice (Python: pure data and validation over `hilclaw.keys`, as its GEMM counterparts).
    - The reviewer checks at least:
      - the prototype text, the three directory names, the 256 patterns and `EPS` against ADR-0158;
      - that the module adds no meaning beyond ADR-0158 (no tolerance, generator, seed, reference `eps` choice, build flag, binding or registration);
      - the absence of the texts `gemm_contract` and `gemm_bf16_contract` in the new module;
      - the criterion 7 list.

## Out of Scope

- The bf16 RMSNorm fit and "every shape" binding in `hilclaw/model_binding.py`, and the executor's `eps` model parameter passed as nearest binary32 (next part of the slice).
- The model program and build/run steps calling `hilclaw_rmsnorm_bf16`; linking the math library (a build setting, with HQ-0033); hand-written bf16 RMSNorm kernel fixtures; any C code.
- The P2-12 harness: generator, seed, draws, widening, reference `eps`, comparison, tolerance values.
- Registering the contract with `correctness.check`, `spec.write` or the instance start.
- The contracts of RoPE, SDPA with KV cache, SwiGLU activation and elementwise add; fp16; backends other than `cpu_standin`.
- The ADR-0158 round 7 Info wording (decision 9) and the PLAN "보류" items.

## Follow-ups

- (planner) Next part of the ADR-0158 code slice: bf16 RMSNorm fit and "every shape" binding in `hilclaw/model_binding.py`, with the executor's `eps`. If ADR-0153 or ADR-0157 do not settle how an RMSNorm call site enters the binding check, return it as a design question rather than invent it. After that come the contract ADRs of elementwise add, SwiGLU activation, RoPE and SDPA with KV cache.

## Result

- **Outcome**: DONE. PR #256 squash-merged as `7acfcaa` (branch deleted). Review: 2 rounds (round 1 Approve with 3 Info; Info 1 addressed by a test, Info 2 in the PR body; round 2 Approve). CI green on all six jobs (run 40063215612).
- **Language**: Python - pure data and validation over `hilclaw.keys`, as its GEMM counterparts.
- **Changes**: `hilclaw/keys.py` (`_SHAPE_MEMBERS` gains `rmsnorm` with `m`, `n`; `op_signature_key` docstring names both kinds); new `hilclaw/rmsnorm_bf16_contract.py` (`KIND`, `DTYPE`, `LAYOUT`, `LANGUAGE`, `PROTOTYPE`, `SHAPES`, `INPUT_PATTERNS`, `EPS` = binary32 `0x3727C5AC`, `op_signature_record`, `task_contract`, `covers`); tests in `tests/test_keys.py` and new `tests/test_rmsnorm_bf16_contract.py`. Local: 27631 passed, 949 skipped; `hilclaw/` coverage 97%, `keys.py` and the new module 100%.
- **Criterion 7 (places whose answer for an `rmsnorm` record changes)**: `keys.op_signature_key` now accepts it, so `spec.validate`, `instance.json` parsing (`instance.py`), `key_records` (and `key_store_tool`) and `case_lookup` (and `case_tool`) treat it as valid instead of refusing it. `spec_tool`, `instance_start`, and `run_admission`/`check_admission` with the `gemm_contract.covers` their callers pass (e.g. `check_definition`) now refuse it as not covered (`KIND_OP_SIGNATURE_NOT_COVERED`) instead of as an invalid record; they read `shape["k"]` only after `covers` returns `True`. `gemm_contract.covers` and the bf16 GEMM `covers` return `False` instead of raising. Nothing treats an `rmsnorm` record as covered by a GEMM contract; no code change was needed.
- **Less exact, not edited**: ADR-0031 ("`hilclaw.keys` knows `gemm` only", lines 21/98) and ADR-0158 Background ("knows `gemm` only and refuses another kind").
- **Follow-ups**: none new beyond the task's planner follow-up (next part of the ADR-0158 code slice: fit and "every shape" binding in `hilclaw/model_binding.py` with the executor's `eps`).
