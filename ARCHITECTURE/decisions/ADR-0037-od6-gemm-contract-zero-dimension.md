# ADR-0037: An `op_signature` whose shape holds a dimension of 0, and the `gemm` contract of ADR-0008 (one point inside the part of OD-6 that ADR-0008 closed)

## Status

- **Accepted on 2026-10-10** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **No content of this record is a decision of the repository owner, and the repository owner has not confirmed it.**
- **Settles one point inside the part of the rest of OD-6 that [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) closed, and closes nothing further.** The register rows of OD-6 and OD-4 keep their status wording. ADR-0008 is not edited: this record states how it is read for one case.
- It builds on ADR-0008 (decisions 1, 4, 5, 6, 8 and 9; objection window until 2026-10-14) and on [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1 and 2; until 2026-10-13). **If ADR-0008 is reverted, this record falls with it**; if ADR-0001 is reverted, it is revisited with ADR-0008.
- The repository owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

Two accepted records meet in one case, and no record joins them (all cited):

- **ADR-0001 decision 1**: "An *integer* is in the range 0 to 2^53 - 1". **Decision 2**: `shape` is a "map: parameter → integer", and for `gemm` it "has exactly `m`, `k` and `n`". So a `gemm` record whose shape holds a 0 is a valid op_signature record, and it has a key.
- **ADR-0008 decision 1**: "The operational contract of a kind is what both sides of a call must know", and the contract "binds both sides: the caller (the harness, or any program that calls a kernel) guarantees what decision 6 lists". **Decision 6**, the row "Dimensions": the caller guarantees that "`m`, `k`, `n` are each at least 1, and the three arrays have exactly m·k, k·n and m·n elements". ADR-0008 gives no reason for "at least 1", and this record supplies none in its name.
- **ADR-0008 decision 5**: the operand entries of `task.contract` are written "with the values of the spec's `op_signature` shape in place of `m`, `k`, `n`". **Decision 9** gives the rule of the op_signature records "for each of the four B-4 shapes and each M ∈ {1, 32, 512}" and speaks of no other shape.
- **The runs** take no smaller value either: a timing run and a verification run are given `m`, `k`, `n` by the caller, restricted "no further than ADR-0008 (each ≥ 1)" ([ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) decision 9; [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) decisions 3 and 9).

**The gap.** Nothing says whether an op_signature of kind `gemm`, dtype `fp32` and layout `row_major` whose shape holds a 0 has the contract of ADR-0008. Two followers of the records can therefore differ: one writes, for the shape m = 0, k = 2048, n = 8192, the op_signature record and a `task.contract` with the operand shapes `[0, 2048]`, `[2048, 8192]` and `[0, 8192]` — a valid key and, in an otherwise valid spec, a valid spec — and the other refuses to.

**Where it was found, and what the code does today** (facts, none changed here). The code slice that carried the op side of ADR-0008 into the package (task T-0110) met the point and filed it for a later record. `hilclaw.keys.op_signature_key` accepts a `gemm` shape that holds a 0; `hilclaw.spec.validate` accepts a spec that embeds such a record, with operand shape values of 0; `hilclaw.instance.validate` accepts the parsed content of an `instance.json` that states it. `hilclaw.gemm_contract.op_signature_record` and `task_contract` refuse a dimension below 1 with `keys.InvalidRecordError`, and the docstring calls that bound "this module's choice, not a rule of a record"; `tests/test_gemm_contract.py::test_zero_is_accepted_by_keys_and_refused_here` pins the difference. The harness takes no dimension below 1: `timing.driver_arguments`, `verification.program_arguments` and `verification_arrays.draw_inputs` refuse one, and the header comments of `timing_driver.c` and `verification_program.c` give `m`, `k`, `n` as at least 1.

**No owner answer speaks of a dimension of 0.** #5 B-4 names the shapes of the first instances, all at least 1.

## Decision

A sentence below is **cited** when a source is named with it; every other sentence is **this record's own**.

### 1. Scope

- The one contract of ADR-0008 — kind `gemm`, dtype `fp32`, layout `row_major`, kernel language `c` — **in the one case that the shape of an op_signature holds a 0 in `m`, `k` or `n`**.
- Nothing else of ADR-0008 is re-opened: the binding, `row_major`, the operation, the prototype, the operand entries, every row of decision 6, decisions 7 and 8 and the twelve records of decision 9 stand as they are. The binding is not changed; how its sentences are read for this one case is stated in decision 3. Nothing is said of a shape whose three dimensions are each at least 1, of an upper bound, or of another kind, dtype, layout or language.
- No field, type, range or rule of ADR-0001, [ADR-0002](ADR-0002-od6-codegen-spec.md) or [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) changes.

### 2. The rule: the contract of ADR-0008 covers no shape that holds a 0

- **The rule is a statement about the contract — about what ADR-0008 defines — and about nothing else.** For an op_signature record whose `kind` is `gemm`, whose `dtype` is `fp32`, whose `layout` is `row_major` and whose `shape` holds a 0, **ADR-0008 defines no `task.contract` and no call**: no object is "the `task.contract` of this contract" for that shape, and no call of this contract has those dimensions (the second half is cited: decision 6).
- **It is not a statement about the validity of a record, a spec or a file, and not about what a program does.** What each of the four cases below is under ADR-0001, ADR-0002 and ADR-0031 stays what it is today.

| Case | Its validity (cited, unchanged) | What this record says |
|---|---|---|
| Such a record given to `hilclaw.keys.op_signature_key` | A valid op_signature record with a key (ADR-0001 decisions 1 to 3). | It is an op_signature that the contract of ADR-0008 does not cover. Nothing else. |
| The same record as `task.op_signature.record` of a spec | The spec is valid or invalid by ADR-0002 alone; an operand shape value of 0 is then one of the values of the `op_signature` shape, which is what ADR-0002 decision 2 asks ("no shape value other than those of the `op_signature` shape"). | Whatever its `task.contract` holds — also the language `c`, the prototype text of ADR-0008 decision 4 and three entries with a 0 in their shapes — that object is not a `task.contract` of the contract of ADR-0008. Nothing is said here of a kernel written to that spec or of a call of it (Boundaries). |
| The same record as `op_signature.record` of an `instance.json` | The file is valid or invalid by the records of that file alone (ADR-0031 decision 3). It states no kernel contract in any case (ADR-0031 decision 2). | ADR-0008 defines no `task.contract` and no call for the shape that member states. What a run that states it does is not said here (Boundaries). |
| A request for the `task.contract` of such a shape under this contract | — | There is none. **Nothing is substituted**: not the three entries of ADR-0008 decision 5 with a 0 in them, and not those of another shape. |

- **So a program and a person arrive at the same outcome**: asked for the op-side values of this contract for a shape that holds a 0, both answer that the contract has none; asked whether the record, the spec or the file is valid, both answer from ADR-0001, ADR-0002 and ADR-0031 as before.

### 3. How ADR-0008 is thereby read

- **The rule rests on decision 1 and on the row "Dimensions" of decision 6, read together.** The contract is "what both sides of a call must know" (cited), and it has no call with a dimension of 0 (cited). The reading, which is this record's: the operand entries that decision 5 gives for a shape describe the three arrays of a call with the dimensions of that shape, so **where ADR-0008 has no call it has no entries either**, and the contract covers no shape for which it has no call.
- **The two sentences of ADR-0008 that speak most against this reading.** Decision 1 binds the contract to the kind, the dtype, the layout and the kernel language and to nothing else: "Another kind, dtype, layout or language has another contract, defined by its own record" (cited). Decision 8: "The contract of (`gemm`, `fp32`, `row_major`, `c`) is the one of this record" (cited). Neither names a shape. Read by themselves they allow the other reading — every op_signature with those three op-side values has this contract, and one whose shape holds a 0 merely has no call. This record reads them as saying **which contract the four values have** — this one, and no second — **and not as saying that the contract has something for every shape that can be written with them**: what it has for a shape is what decisions 4 to 6 give, and decision 6 gives no call with a 0. The binding itself is untouched: no fifth value is added to it, and the four values have this one contract as before.
- **Decision 9 is read as written**: it gives the records of the twelve first instances and says nothing of another shape. This record neither extends its rule nor limits it.
- **Decision 4**, "the same text in every spec of this contract, whatever the shape", is read with "of this contract": it speaks of the specs the contract has.
- **OD-16 sub-question ① is not touched.** The rule speaks of the shape of an op_signature, not of the dimensions a caller passes to a kernel; whether a caller ever passes dimensions other than those of the op_signature "stays open" (cited: ADR-0008 decision 6; ADR-0017 decision 3). Every call of the contract, whatever its dimensions, keeps the guarantee of decision 6.

**Why this reading and not another.**

- **Against "such an op_signature is one of this contract, and no call of it exists".** At its own shape a kernel of it could never be called (cited: decision 6), so no timing run and no verification run at that shape could exist (cited: ADR-0009 decision 9; ADR-0017 decision 3), while FR-9 has the correctness of a kernel verified and the round loop of FR-1 verifies and measures its candidates. Whether a kernel is ever run at another shape is OD-16 sub-question ①, which is open. A record that took this reading would have to say what a verification and a measurement of such a kernel are — a rule added to ADR-0009 and ADR-0017, or an answer to that sub-question — and no input carries either.
- **Against "no rule".** The two followers of Context keep differing, and whoever next binds the values of the contract chooses again. The point is small and the answer is cheap now: the data repository `HIL-Claw-data` holds no spec, no instance file and no stored record yet (its tree was read on 2026-10-10).
- **Against "a call with a 0 is allowed".** That is a change of the row "Dimensions" of decision 6, and with it of what the rows on alignment and memory mean for an array of no element. The contract "is changed only by a record that supersedes this one" (cited: ADR-0008 decision 8); this record supersedes nothing.

**The cost of this reading, plainly.** The product itself is defined in mathematics for a dimension of 0 — for k = 0 and m, n ≥ 1 it is the m×n matrix of zeros — and **the rule does not rest on the operation being undefined**; it rests on ADR-0008 giving it no call. For a `gemm` of such a shape in `fp32`, `row_major` and C no record therefore defines a `task.contract` or a call; whether a later record does, and how it would stand to ADR-0008, is not decided (Boundaries). And the reading is chosen, not found: ADR-0008 binds its contract to four values and names no shape among them, it nowhere says that the contract stops at a shape that holds a 0, and the two sentences named in decision 3 can be read the other way.

### Walk-through

Four records `{"schema_version": 1, "kind": "gemm", "shape": {"m": …, "k": …, "n": …}, "dtype": "fp32", "layout": "row_major"}`; the names are computed with `hilclaw.keys.op_signature_key`. No row names a tool or a moment of a call.

| `m`, `k`, `n` | `op_signature_key` gives (ADR-0001, unchanged) | This record |
|---|---|---|
| 1, 2048, 8192 | `gemm-485b9bc494d477eb` | Says nothing: no dimension is 0. It is the gate/up record at M = 1 of ADR-0008 decision 9. |
| 0, 2048, 8192 | `gemm-d765fb955295628a` | Not covered by the contract: no `task.contract`, no call. |
| 1, 0, 8192 | `gemm-ae3e9e269ea6e812` | Not covered, although the product is defined (a 1×8192 matrix of zeros). |
| 0, 0, 0 | `gemm-f5ed2636b2d123a9` | Not covered. |

## Alternatives considered

| Alternative | Why not |
|---|---|
| A shape with a 0 is an op_signature of this contract for which no call exists | See decision 3: it needs a rule for the verification and the measurement of a kernel that is never called at its shape, or an answer to OD-16 sub-question ①. |
| No rule; the bound stays the choice of each program | Two programs that follow the records keep differing on the same shape. |
| A call with a dimension of 0 is allowed | A change of ADR-0008 decision 6; only a superseding record makes it (ADR-0008 decision 8). |
| A shape value of 0 is made invalid for `gemm` in the key schema | A change of a range of ADR-0001: a data-plane schema change (CLAUDE.md A-13), and outside this point. The key schema lets a shape value be 0 for every kind, as before. |
| A check for it in the spec validator or the `instance.json` validator | A new rule of ADR-0002 or ADR-0031; a spec or a file valid today would become invalid. Whether a tool or the start of an instance refuses such a record is not decided here (Boundaries). |
| Edit decision 6 or decision 9 of ADR-0008 | ADR-0008 is inside its objection window and is left as it was accepted; the reading is stated here, where it can be reverted alone. |

## Consequences

- **The behaviour of `hilclaw/gemm_contract.py` agrees with the rule, and no change of behaviour follows.** `op_signature_record` returns "the op_signature record of the shape … under this contract" and `task_contract` "the `task.contract` object of the shape … under this contract"; both refuse a dimension of 0, which is what decision 2 says of a request for the values of such a shape. The test named in Context pins both halves: `op_signature_key` accepts the record, the module refuses the shape.
- **One docstring sentence is now untrue**: "The lower bound of 1 is this module's choice, not a rule of a record" (`op_signature_record`). Correcting it is a follow-up in code mode and is not done here. The rest of that sentence — that ADR-0001 lets a shape value be 0 and that a shape with a 0 describes a call the contract never has — stays true.
- **The exception class is not chosen here.** The module raises `keys.InvalidRecordError`, which `hilclaw/keys.py` documents as "A record or a value breaks a rule of ADR-0001"; a dimension of 0 breaks no rule of ADR-0001, with or without this record. Whether the module keeps that class or gets one of its own is left to the same follow-up.
- `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/instance.py` and the harness are unchanged and need no change: this record adds no check to any of them.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. No field, type, range or rule of ADR-0001, ADR-0002 or ADR-0031 changes, and no data-plane file changes. The data repository holds no op_signature record at all (above), so none is made invalid or re-keyed — and the rule would make none invalid if one existed.

## Boundaries (not decided here)

- **Any change of a field, type, range or rule of ADR-0001, ADR-0002 or ADR-0031, and any new check in `hilclaw/keys.py`, `hilclaw/spec.py` or `hilclaw/instance.py`** — a later record and its code task.
- **Whether a tool, the writer of specs or the start of an instance refuses a record whose shape holds a 0** — OD-18, OD-23 and OD-26, and the task that binds the values of the contract.
- **Whether a caller passes dimensions other than those of the op_signature** (OD-16 sub-question ①); **what a kernel does when it is nevertheless called with a 0**; verification inputs and corner cases (ADR-0008 Boundaries; the rest of OD-16).
- **Whether a `gemm` of a shape that holds a 0 ever gets a `task.contract` and a call, and how a record that gave them would stand to ADR-0008 decision 8** ("changed only by a record that supersedes this one") — whether it supersedes ADR-0008 or is something else is not said here.
- **Any other contract or kind; an upper bound of a dimension or of a product of dimensions** — a record of its own, when one is needed.
- **Build settings** (OD-6 sub-question ②), **the objective** (#5 A-4, OD-1), **the committed spec example** (PLAN P1-5), OD-6 sub-questions ③ and ④, and anything HQ-0005, HQ-0006 or HQ-0007 asks.
- Any change to ADR-0001 to ADR-0036, to `hilclaw/`, to tests or to CI; any new external dependency. No question is registered by this record and no OD number is created.

## References

- [Requirements](../Requirements.md): FR-1, FR-5, FR-9, FR-13; register rows OD-4, OD-6, OD-16.
- [OpenDecisionProposals OD-6](../OpenDecisionProposals.md#od-6) ("하위 질문" ①), [OD-16](../OpenDecisionProposals.md#od-16) ("하위 질문" ①); [StandardScenarios](../StandardScenarios.md).
- [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 1, 4, 5, 6, 8, 9; Boundaries); [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 2, 3; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decision 2); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decision 9); [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) (decisions 3, 9); [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decisions 2, 3).
- `hilclaw/gemm_contract.py`, `tests/test_gemm_contract.py`, `hilclaw/keys.py`, `hilclaw/spec.py`, `hilclaw/instance.py`, `hilclaw/harness/timing.py`, `hilclaw/harness/verification.py`, `hilclaw/harness/verification_arrays.py`, `hilclaw/harness/timing_driver.c`, `hilclaw/harness/verification_program.c`; tasks T-0030, T-0110, T-0112.
- #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9.
