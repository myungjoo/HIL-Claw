# ADR-0058: The committed GEMM spec example of PLAN P1-5 — one first-call spec of version 2 with an empty technique list, where it lives and in which form, what stands for the `spec.json` schema, and when P1-5 is done (one more part of OD-6)

## Status

- **Accepted on 2026-10-14** (UTC) under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Whose the content is.** No owner sentence is new here. #5 B-4 (the four projection shapes, M ∈ {1, 32, 512}, fp32, initial caps N = 1–2) is cited through the records that used it; O1 and O2 of the answer to HQ-0009 are cited through [ADR-0050](ADR-0050-od6-task-objective-members.md). **Every value of the example is cited from a landed record, except the choice of an empty technique list, whose form ADR-0002 gives; the choices among them, the place and name of the file, what stands for the schema and the completion criterion of P1-5 are this record's own design.**
- It settles **one more part of OD-6** (Open Decisions register in [Requirements](../Requirements.md)): the committed GEMM spec example and the "`spec.json` 스키마" that PLAN P1-5 asks for. The register row of OD-6 keeps its status word `확정`. **OD-22 is not closed and not narrowed**: its row stays `제안됨`, and this record names no catalog entry and writes no technique `id` or `text`.
- **It is a record, not code.** No example file, test, schema file or code is added. The example file and its test are the code slice of Consequences.
- It builds on [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 1 to 5, 7 and 8), ADR-0050 (decisions 1 to 5 and the Example), [ADR-0051](ADR-0051-od6-spec-file-version-2.md) (decisions 1 to 3, and through it [ADR-0029](ADR-0029-od8-spec-file.md) decisions 2 and 3), [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 4, 5 and 9), [ADR-0027](ADR-0027-od8-run-id-form.md) (decision 2), [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (Example). **If ADR-0002 or ADR-0050 is reverted, this record falls with it**; if another of them is reverted, the decision that cites it is revisited. No earlier record is edited; sentences of theirs that are now less exact are listed under Consequences.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What is asked for.** PLAN P1-5: "GEMM spec 예시(Llama 3.2 1B projection, M∈{1,32,512}, fp32)와 `spec.json` 스키마 — OD-6 종결 필요(§9 ADR 경로)". ADR-0002 Boundaries leave "Code, JSON Schema files, validators and committed example files" to later code tasks, and list as "open questions for the task that commits the real example" the layout, the prototype and operands, the hw-side strings, "the form of a `run_id`" and "a technique of the stand-in catalog".
- **What landed records have closed since.** The `op_signature` records and keys of the twelve first instances and `task.contract` (ADR-0008 decisions 4, 5 and 9); the form of a run id and its example `20261009t012331z-9f3a6c1e0b7d4a52` (ADR-0027 decision 2); a hw_profile record of "A plainly fictitious machine" and its key `cpu_standin-8c0be275e5925ab0` (ADR-0035 Example); version 2 of the spec and the first value of `task.objective`, `{"objectives": [{"type": "latency_minimisation"}], "constraints": []}`, with "the first committed example carries no value" of a constraint (ADR-0050, owner O2); the text form and the write of a version-2 spec file (ADR-0051, carrying ADR-0029 over).
- **What is still lacking: the technique.** ADR-0050 restates the example of ADR-0002 decision 8 with every closed value and keeps `{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}`, with the row "the technique | **still lacking**: no source gives a technique of the stand-in catalog (OD-22)", and notes that "`NOT-DECIDED-HERE` would pass a check of form".
- **The technique catalog.** FR-8: "P1에서는 기법 후보 = repo 내 문서로 시작". No such document exists: no file of the repository is a catalog entry and no record defines a catalog file. How the catalog is filled is OD-22 (`제안됨`). ADR-0002 decision 2 makes `guidance.techniques` a required "array of `{id, text}`, may be empty", "The techniques to apply in this call".
- **Identity and one op_signature.** "The tuple (`run_id`, `round`, `candidate`, `attempt`) identifies a spec" (ADR-0002 decision 1); a spec has exactly one op_signature, "and so one value of M" (ADR-0002 decision 2). Whether one instance may cover several values of M is sub-question ③ of OD-6 and is open, and whether it may cover several projections no record says either: [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) decision 4 gives a version-1 `instance.json` at most one op_signature and says that this is "a rule about what a file of version 1 can state, not about what an instance may be".
- **Facts of the code, none changed here** (read on 2026-10-14). `hilclaw/spec.py` has `SCHEMA_VERSION = 2` and its `validate` checks the rules of ADR-0002 with ADR-0050; `guidance.techniques` goes through `_array(..., _technique)`, whose default `empty=True` accepts an empty array. `hilclaw/spec_file.py` has `parse` (the text rules of ADR-0029 as ADR-0051 carries them, then `spec.validate`), `final_name` and `write` (which also checks the written form: a final line feed and no carriage return byte). `hilclaw/gemm_contract.py` gives `op_signature_record`, `task_contract` and `FIRST_SHAPES` (the twelve shapes of ADR-0008 decision 9) and builds no spec. `hilclaw/keys.py` gives `op_signature_key` and `hw_profile_key`. The only JSON files of the source repository are `.claude/settings.json`, `PROCESS/STATE.json`, `PROCESS/STATE.schema.json` and `hilclaw.config.json`: no spec file is committed. The one JSON Schema file, `PROCESS/STATE.schema.json`, is read by `hilclaw/driver_state.py`, which interprets a keyword subset with the standard library; the package's only runtime dependency is `numpy`.

## Decision

A value is **cited** where a source is named with it; everything else is **this record's own**.

### Limits

- **L1 — Nothing was run.** No example file was written and nothing was parsed or validated. That the Example below is accepted by `hilclaw.spec_file.parse` is a reading of the sources of `main`; the test of the code slice establishes it.
- **L2 — A spec of correct form, not the spec of a real call** (decision 3).
- **L3 — One file for twelve op_signatures.** The other eleven are covered by a check of form, not by files (decision 2).
- **L4 — One shape of call.** The example is a first call of round 1 with N = 1. It shows no repair spec, no `feedback.base`, no entry of `feedback.attempts`, no N > 1 and no technique entry; their forms stay those of ADR-0002 decisions 2 to 5.
- **L5 — The facts of today are not rules.** That no catalog document and no spec file exist (Context) is true on the day it was checked and binds nothing.

### 1. The technique list: empty

- **The committed example carries `"guidance": {"techniques": []}`.** The array is valid in version 2 as it stands ("may be empty" — cited: ADR-0002 decision 2; ADR-0050 decision 1 leaves `guidance` unchanged), so no field, value or version changes.
- **What the empty list says, only as far as ADR-0002 gives it**: the field is "The techniques to apply in this call", so an empty array names no technique to apply in this call. Nothing more is read into it: whether a real call may or should be issued with an empty list, which techniques the orchestrator selects (FR-8, OD-7), and whether a coder that gets none may choose one itself (OD-12, OD-23) are not decided.
- **Why not the placeholder.** `{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}` passes the check of form (cited: ADR-0050 Example), so a committed file that `parse` accepts would state a catalog entry of that name with that guidance. ADR-0002 decision 8 used the placeholder only in an example it declared "not a valid spec"; a valid committed file is read and copied as a template, and the placeholder would travel with it. The empty array states nothing false.
- **Why not a real technique.** No source gives one (Context). Writing an `id` or a `text` would invent a catalog entry and settle part of OD-22 and of FR-8's "repo 내 문서". **This judgement does not close OD-22**, names no catalog entry, and says nothing of how the catalog is filled or of what its first entry is.
- **The cost.** The example does not show the form of a technique entry; that form stays in the table of ADR-0002 decision 2.

### 2. Which op_signatures: one file, gate/up at M = 1, and a check of form for the twelve

- **One example file**: the first call of round 1 for `cpu_standin` × the gate/up projection (2048→8192) at M = 1, the case ADR-0002 decision 8 and the ADR-0050 Example show. Its `op_signature` record is `{"schema_version": 1, "kind": "gemm", "shape": {"m": 1, "k": 2048, "n": 8192}, "dtype": "fp32", "layout": "row_major"}` with key `gemm-485b9bc494d477eb` (cited: ADR-0008 decision 9).
- **Why not twelve files.** Twelve specs need twelve identifying tuples (ADR-0002 decision 1). The one tuple the records give is that of ADR-0002 decision 8 with the run id of ADR-0027; twelve files under it would be twelve different specs claiming one identity. Any other tuple is a value no record gives: eleven more run ids of the form, or other `round` or `candidate` numbers in one run — and whether one run may cover several op_signatures is said by no record (for several values of M it is sub-question ③ of OD-6, open). No value is made up for the example.
- **The twelve are still covered**: the test of the code slice checks that, for each shape of `hilclaw.gemm_contract.FIRST_SHAPES`, the example with its `task.op_signature` (record and key) and its `task.contract` replaced by the values of that shape is accepted by `hilclaw.spec.validate` (decision 4, check T4). That shows the form for M ∈ {1, 32, 512} and all four projections without a file whose identity would be false.
- **`id` and `feedback`** are cited unchanged from ADR-0002 decision 8: `round` 1, `candidate` 1, `attempt` 1, `candidates` 1, `relation` `single`, `feedback.attempts` empty and no `feedback.base` — with that record's caveat that the empty array "shows the empty form only; a real round 1 follows the bring-up round". No `repair`, `task.build` or `ext`.

### 3. The values: example values, cited

- **`id.run_id`** is `20261009t012331z-9f3a6c1e0b7d4a52`, the example of ADR-0027 decision 2; not the id of a real run.
- **`hw_profile`** is the record and key of the ADR-0035 Example, "A plainly fictitious machine — not the first real instance, not the driver machine and not the repository owner's PC". No string of a real machine is taken.
- **`task.op_signature` and `task.contract`** are those of ADR-0008 decisions 4, 5 and 9 for gate/up at M = 1, as `hilclaw.gemm_contract` gives them.
- **`task.objective`** is `{"objectives": [{"type": "latency_minimisation"}], "constraints": []}` (cited: ADR-0050 Example; no constraint value, owner O2).
- **Therefore the committed example is a spec of correct form and not the spec of a real call**: the machine is fictitious, the run id is an example, no technique was selected for it and no bring-up round precedes it.

### 4. Where it lives and in which form

- **Path: `examples/spec/gemm-485b9bc494d477eb.json`** in the source repository. Not under `ARCHITECTURE/` (records, document mode, nothing there is checked by a test); not under `hilclaw/` (no module reads it, and the package would carry a file it never uses); not under `tests/` (it is the example P1-5 asks for, meant to be read, not a fixture of one test); never in a data plane (it belongs to no run; `HIL-Claw-data` is not touched). The file name is the op_signature key, the value that tells first instances apart.
- **The bytes are one content accepted by `hilclaw.spec_file.parse`**, not only a document accepted by `hilclaw.spec.validate`: the text rules of ADR-0029 decision 2 as ADR-0051 decisions 1 and 2 carry them (UTF-8 without a byte order mark, one JSON object, no member name twice, *integer* places in decimal digits). They are also **in the written form** that binds a writer (LF line ends and a final line feed — cited: ADR-0029 decision 2, carried unchanged by ADR-0051 decision 1). Indentation, line breaks and member order are not fixed (ADR-0029 fixes none).
- **It is no file under a spec path.** The rule of ADR-0029 decision 3 between the `id` of a content and its path binds files below a data root; this file is outside any. `hilclaw.spec_file.write` does not write it, and its name is not its `final_name`.
- **How a later test checks it** (the test is the code slice's): **T1** `hilclaw.spec_file.parse` accepts the bytes; **T2** the bytes end with a line feed and hold no carriage return byte; **T3** the parsed document equals the Example below, with the op side compared with `hilclaw.gemm_contract.op_signature_record(1, 2048, 8192)`, `hilclaw.keys.op_signature_key` of it and `hilclaw.gemm_contract.task_contract(1, 2048, 8192)`, and with `guidance.techniques` empty; **T4** the check of form over `FIRST_SHAPES` of decision 2.

### 5. The "`spec.json` 스키마" of P1-5, and when P1-5 is done

- **The schema is the records, and the check is the code that holds them**: the document is defined by ADR-0002 decisions 2 to 5 and 7 with ADR-0050, and checked by `hilclaw.spec.validate`; the file is defined by ADR-0029 with ADR-0051, and checked by `hilclaw.spec_file.parse` and `write`. **No JSON Schema file is written for P1-5.**
- **Why.** (a) Several rules of a valid spec cannot be stated in JSON Schema: each `key` is the sha256-derived name of its `record`, `candidate` ≤ `candidates`, ascending `repair.failures`, operand shapes drawn from the op_signature shape (the rules are cited from ADR-0002 Consequences; that JSON Schema cannot state them is this record's reading). A schema file would be a second, weaker statement of the same schema. (b) Checking anything against it needs either a validator package, a new external dependency (CLAUDE.md A-13), or a second interpreter in the package beside `spec.validate`, as `hilclaw/driver_state.py` is for the driver's state; without either it is checked by nothing and drifts. (c) ADR-0002 Consequences say a later task "can write the JSON Schema and a validator"; the validator is written and is enough.
- A later record may still add a schema file; it then says how the file is kept in step with `hilclaw/spec.py` and adopts no validator package without the owner's approval under A-13.
- **Completion criterion of P1-5.** The driver ticks P1-5 when all of these are on `main`: (i) this record and its register edits; (ii) version 2 in `hilclaw/spec.py` and `hilclaw/spec_file.py` (on `main` since T-0148); (iii) the file of decision 4 with the content of the Example; (iv) a test under `tests/` that makes the checks T1 to T4 and passes in CI. Nothing else is required: no JSON Schema file, no real machine's values, no technique, no constraint value.

### 6. Values are kept as the cited records spell them

- The op_signature key and record are those of ADR-0008 decision 9; the hw_profile key and record are those of the ADR-0035 Example, `hw_source` `external` included; the prototype is the line of ADR-0008 decision 4, byte for byte. No value of the Example is of this record's making except the choice of an empty `guidance.techniques` (decision 1), whose form is ADR-0002's.

## Example

The content of `examples/spec/gemm-485b9bc494d477eb.json` (the layout of the text is free, decision 4):

```json
{
  "schema_version": 2,
  "id": {"run_id": "20261009t012331z-9f3a6c1e0b7d4a52", "round": 1, "candidate": 1, "attempt": 1, "candidates": 1, "relation": "single"},
  "hw_profile": {"key": "cpu_standin-8c0be275e5925ab0",
    "record": {"schema_version": 1, "accelerator": "cpu_standin", "revision": "host",
               "toolchain": {"clang": "Example clang version 0.0.0 (fictitious-build 1)"},
               "host": {"cpu": "Example(R) Fictitious(TM) X-0000 CPU @ 0.00GHz", "os": "linux exampleos 0.0"}, "hw_source": "external"}},
  "task": {
    "op_signature": {"key": "gemm-485b9bc494d477eb",
      "record": {"schema_version": 1, "kind": "gemm", "shape": {"m": 1, "k": 2048, "n": 8192}, "dtype": "fp32", "layout": "row_major"}},
    "contract": {"language": "c",
      "prototype": "void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);",
      "operands": [
        {"name": "a", "role": "input", "dtype": "fp32", "shape": [1, 2048]},
        {"name": "b", "role": "input", "dtype": "fp32", "shape": [2048, 8192]},
        {"name": "c", "role": "output", "dtype": "fp32", "shape": [1, 8192]}]},
    "objective": {"objectives": [{"type": "latency_minimisation"}], "constraints": []}},
  "guidance": {"techniques": []},
  "feedback": {"attempts": []}
}
```

| Value | Source |
|---|---|
| `schema_version` 2, `task.objective` | cited: ADR-0050 (decisions 1 to 5, Example) |
| `id.run_id` | cited: the example of ADR-0027 decision 2 |
| the other members of `id`, `feedback.attempts` | cited: ADR-0002 decision 8 |
| `hw_profile` record and key | cited: the ADR-0035 Example (fictitious machine) |
| `task.op_signature` record and key, `task.contract` | cited: ADR-0008 decisions 4, 5 and 9 |
| `guidance.techniques` empty | this record (decision 1); the empty form is ADR-0002's |

It differs from the ADR-0050 Example in one value only: `guidance.techniques`.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | Keep the placeholder technique | A valid committed file would state a catalog entry that does not exist (decision 1). |
| 1 | Write a plausible technique (for example loop tiling) | Invents a catalog entry and settles part of OD-22 and FR-8. |
| 1 | Wait with P1-5 until OD-22 gives a technique | Holds back a check of the version-2 form that every value but one already allows; the empty form is already valid. |
| 2 | Twelve files, one per op_signature | Twelve specs under one identifying tuple, or eleven invented run ids (decision 2). |
| 2 | Twelve files differing in `round` or `candidate` | Values no record gives, and it would presume one run covering several op_signatures, which no record says (for several values of M: sub-question ③ of OD-6, open). |
| 3 | The strings of the driver machine or of the owner's PC | A real machine's strings in a committed example; ADR-0035 chose a fictitious one so that no reader takes the example for a real profile. |
| 4 | Under `tests/` as a fixture | It is the example P1-5 asks for, read by people as well as by one test. |
| 4 | Under `hilclaw/` as package data | No module reads it. |
| 4 | Only `spec.validate` must accept it, not `parse` | The example would then not show the text form of a spec file, the half of the schema ADR-0051 defines. |
| 5 | A JSON Schema file checked by a validator package | A new external dependency (A-13), and still weaker than `spec.validate` (decision 5). |
| 5 | A JSON Schema file checked by a stdlib interpreter, as for the driver's state | A second validator of the same schema, to be kept in step for no gain. |

## Consequences

- **The code slice for the planner** (code mode; the example file is outside the document-mode paths): commit `examples/spec/gemm-485b9bc494d477eb.json` with the content of the Example and a test under `tests/` that makes T1 to T4 of decision 4. That task ticks P1-5 by the criterion of decision 5. It needs no new dependency, no schema change and no data-plane file.
- **Sentences of earlier records that are now less exact** (none edited; each stays true of what it describes or of what remains open):
  - ADR-0002 — decision 8 (the placeholder technique and the row "the technique … not decided here"), Consequences ("A later code task can write the JSON Schema and a validator"; "The example becomes a valid spec only after the placeholder values are known") and Boundaries (the bullet "Values of the first GEMM that no source gives, open questions for the task that commits the real example", as far as the technique, the hw strings and the run id go for the committed example; "Code, JSON Schema files, validators and committed example files": no JSON Schema file is to be written for P1-5).
  - ADR-0050 — the Example (the placeholder technique, the row "the technique | **still lacking**" and the sentence after the table), Consequences slice (d) ("which still lacks a technique") and Boundaries ("committed example files").
  - ADR-0035 — Consequences ("What the committed spec example (PLAN P1-5) still lacks after this record": the committed example uses the fictitious machine and needs no real one) and Boundaries ("the committed spec example itself").
  - ADR-0029 — Boundaries ("a committed example with real values (PLAN P1-5); a JSON Schema file").
  - ADR-0008 — Consequences ("Committed spec example"): still true of a spec of a real instance; the committed example is not one.
  - ADR-0004 — the path table row of `spec.json`, "Schema: ADR-0002, PLAN P1-5": by decision 5 the schema of P1-5 is the records decision 5 names (ADR-0002 with ADR-0050, ADR-0029 with ADR-0051); ADR-0051 already read the row as ADR-0050's for a version-2 file.
- **A-13 reading.** Document mode. No section, field, type, value list, rule or version of the spec changes, and no member of `instance.json`, `STATE.json`, an event or a result file is named: no data-plane schema change. No dependency is adopted; decision 5 excludes the one a JSON Schema file would have brought.

## Boundaries (not decided here)

- **OD-22 and FR-8**: the stand-in catalog, how it is filled, its documents and any technique `id` or `text`; whether a real call may carry an empty technique list (FR-8 selection, OD-7); whether a coder may choose a technique itself (OD-12, OD-23).
- **The values of a real call**: a real machine's hw_profile (OD-26 and the task that registers the profile), a real run id, what the orchestrator shows in `feedback` (rest of OD-6), who writes a spec and how it reaches the coder (OD-23).
- **`memory_ceiling` and any constraint value** (ADR-0050 O2, [ADR-0052](ADR-0052-od13-memory-ceiling-measurement.md) decision 7); `profile`, `ext` members, the rest of OD-6 (selection rule, B4, S7, B5) and sub-questions ② and ④; reading another version (OD-11).
- Examples of other shapes of call (repair, N > 1, a base); any JSON Schema file beyond what decision 5 allows; the example file and its test themselves (the code slice).

## References

- [Requirements](../Requirements.md): FR-5, FR-8; register rows OD-6, OD-7, OD-11, OD-12, OD-22, OD-23, OD-26.
- [OpenDecisionProposals OD-6](../OpenDecisionProposals.md#od-6), [OD-22](../OpenDecisionProposals.md#od-22); [StandardScenarios](../StandardScenarios.md) S0, S1, S4, S8.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 1 to 5, 7 and 8; Consequences; Boundaries); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (path table); [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 4, 5 and 9; Consequences); [ADR-0027](ADR-0027-od8-run-id-form.md) (decision 2); [ADR-0029](ADR-0029-od8-spec-file.md) (decisions 2 and 3; Boundaries); [ADR-0031](ADR-0031-od8-instance-record-op-signature.md) (decision 4, cited for what it does not answer); [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (Example; Consequences); [ADR-0050](ADR-0050-od6-task-objective-members.md) (decisions 1 to 5; Example; Consequences); [ADR-0051](ADR-0051-od6-spec-file-version-2.md) (decisions 1 to 3); [ADR-0052](ADR-0052-od13-memory-ceiling-measurement.md) (decision 7).
- `hilclaw/spec.py`, `hilclaw/spec_file.py`, `hilclaw/gemm_contract.py`, `hilclaw/keys.py`, `hilclaw/driver_state.py`; tasks T-0148, T-0179.
- #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-5; CLAUDE.md "브랜치·merge 절차".
