# ADR-0002: Payload of the codegen spec and the repair call (P1 minimum of OD-6)

## Status

- **Accepted on 2026-10-06** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes the **P1 minimum** of OD-6 (Open Decisions register in [Requirements](../Requirements.md)): what one spec is, its sections and fields, how it identifies run, round and candidate, the structure of its feedback part, the repair call, the place of the operational contract and of build settings, and versioning. The rest of OD-6 stays open (see Boundaries).
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md), whose own objection window runs until 2026-10-13. If ADR-0001 is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- FR-5 delegates code generation to a headless `claude -p` coder and makes the **spec** handed from the orchestrator to the coder a first-class interface; a repair after a compile failure is a delegated call too. FR-1 ⑴ sends a candidate that fails at the sim point back to code generation with a failure report.
- **This spec is the orchestrator's output to the coder. It is not the input a user gives at instance start** (the "fixed kernel spec file" of #5 B-5, `model_ref`, frontend formats: OD-9). The B-4 values are used below only as the values of the first hw_profile and op_signature.
- Fixed inputs: the application guidance of a technique travels in the spec, the selection criteria stay with the orchestrator (FR-8); references and stored cases are hints (FR-15); verification runs on inputs not exposed to the coder, and runtime seeds and input values do not exist as files (FR-9, OD-16); the number of candidates per round N is an instance parameter that nothing may hard-code, with N = 1 as a special case (FR-1, OD-21, OD-29); persistent artefacts carry a `schema_version` (NFR-7 ②); the interface must translate to a Method A node contract (NFR-6).
- #4 §3b: a round has phase markers and is resumed per substep; "repair = the coder is invoked again and the round resumes from the `phase=coded` checkpoint". The register row still listed "resume vs restart" as under discussion.
- #4 (roster revision): the coder-driver agent is a thin driver that calls `claude -p`, passes the spec, captures the output and manages repair calls; OD-6 is a subset of its contract (OD-23).
- ADR-0001 defined the `hw_profile` and `op_signature` records and handed two questions to OD-6: the operational contract of an operation kind, and where per-candidate build settings are recorded.
- The registered proposal ([OpenDecisionProposals OD-6](../OpenDecisionProposals.md#od-6)) asks for candidate identification (S8) and for several earlier attempts shown side by side with their profiles (#7 S-1 supplement (6)).

## Decision

### 1. Unit and lifecycle of a spec

- **One spec is the input of one coder invocation.** A round with N candidates and r repair calls has N + r specs.
- A spec is written before the call and **never changed afterwards**. A repair call gets a new spec (decision 5).
- The tuple (`run_id`, `round`, `candidate`, `attempt`) identifies a spec, and with it the coder call and its output. The spec that produced a candidate's source is found by that tuple (NFR-2), so every spec is kept, including those of failed and repaired attempts (FR-6).
- The spec is the whole task-specific input of the call: a coder process that knows nothing of earlier calls can do its work from the spec and the sources it refers to.

### 2. Sections and fields

*name*, *string* and *integer* are the types of ADR-0001 (decision 1). *text* is a JSON string of at least one character, with no length limit in version 1. A *ref* is an object with exactly `round`, `candidate` and `attempt` (as in `id`) and names an earlier coder call of the same run. An object holds exactly the members listed for it.

| Field | Type | Required | Meaning |
|---|---|---|---|
| `schema_version` | integer | yes | Version of the spec schema; `1` for this record. |
| `id` | object | yes | Which coder call the spec is for (decision 3). |
| `hw_profile` | object | yes | The target hardware. |
| `task` | object | yes | Kernel description: the operation, what the built kernel must satisfy, the objective. |
| `guidance` | object | yes | Technique guidance (FR-8). |
| `feedback` | object | yes | Earlier attempts shown to the coder (decision 4). |
| `repair` | object | exactly when `id.attempt` > 1 | Failure reports the call has to repair (decision 5). |
| `ext` | map: name → any JSON value | no | Registered extensions (decision 7). Absent when there are none. |

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id.run_id` | string | yes | The run (Loop instance, #4 §2c). Its form is not decided here. |
| `id.round` | integer | yes | Round number; 0 is the bring-up round of FR-1. |
| `id.candidate` | integer ≥ 1 | yes | Index of the candidate in its round, from 1 to `id.candidates`. |
| `id.attempt` | integer ≥ 1 | yes | 1 for the first generation of this candidate; each repair call adds 1. |
| `id.candidates` | integer ≥ 1 | yes | N of this round. The schema sets no upper bound. |
| `id.relation` | `single` \| `same_technique` \| `different_techniques` | yes | How the candidates of the round relate (decision 3). |
| `id.variant` | text | exactly when `id.relation` is `same_technique` | What distinguishes this candidate from the others of the round. |
| `hw_profile.key` | string | yes | The `<hw_profile_key>` directory name of ADR-0001 (decision 3). |
| `hw_profile.record` | object | yes | The full hw_profile record of ADR-0001, key fields and attributes, unchanged. |
| `task.op_signature.key` | string | yes | The `<op_signature>` directory name of ADR-0001. |
| `task.op_signature.record` | object | yes | The full op_signature record of ADR-0001, unchanged. A spec has exactly one, and so one value of M. |
| `task.contract.language` | name | yes | Source language of the kernel; `c` for `cpu_standin` (#5 A-7 ②). |
| `task.contract.prototype` | text | yes | Declaration of the entry point the kernel must define, in that language, exactly as the harness calls it. |
| `task.contract.operands` | array of operand, at least one | yes | One entry per data operand of the prototype: `name` (string, the parameter), `role` (`input` \| `output` \| `inout`), `dtype` (name), `shape` (array of integers). |
| `task.objective` | any JSON value | yes | The target of the instance (FR-2), copied from the instance record. Not validated in version 1. |
| `task.build` | map: name → string, integer or array of strings | no | Build and run settings the orchestrator prescribes for this candidate (decision 6). Absent when there are none. |
| `guidance.techniques` | array of `{id, text}`, may be empty | yes | The techniques to apply in this call: `id` (string) names the catalog entry, `text` (text) is its application guidance, copied when the spec is written. |
| `feedback.base` | ref | no | The attempt whose source is the starting point of this call. Absent when there is none. |
| `feedback.attempts` | array of attempt, may be empty | yes | Earlier attempts of this run, shown side by side. |
| `repair.failures` | array of `{attempt, stage, report}`, at least one | yes | Failure reports of earlier attempts of this candidate (decision 5). |

An entry of `feedback.attempts` has `round`, `candidate`, `attempt` (required; the ref of the call that produced it), `techniques` (required; array of string, the ids it applied, may be empty), `failure` (optional; `{stage, report}`, present exactly when the attempt failed) and `profile` (optional; object, see decision 4). `stage` is a name: `compile`, `sim` or `board`, the three points where FR-1 lets a candidate fail. `report` is text.

- **The two ADR-0001 records are embedded in full and by key.** The coder needs the field values (shape, dtype, layout, toolchain versions, host), which a digest does not give; the key joins the spec to `db/<hw_profile_key>/<op_signature>/`. A spec whose `key` is not the name derived from its `record` is invalid.
- **No field carries verification inputs**: a spec holds no seed, no input or expected value of a verification run, and no shape value other than those of the `op_signature` shape, from which the operand shapes follow (FR-9, OD-16). This binds `report`, `profile` and `ext` as well.

### 3. Identification

- `id.candidates` and `id.relation` describe the round without fixing N: `single` exactly when `id.candidates` is 1; `same_technique` when all candidates apply the techniques of `guidance.techniques` and must differ in how, which `id.variant` states for each; `different_techniques` when each candidate has its own techniques. `id.candidate` ≤ `id.candidates`.

### 4. Feedback part

- `feedback.attempts` holds **any number** of earlier attempts, from any earlier round, each with its own failure report or profile, so several attempts can be compared in one call. The first call of a run has an empty array and no `base`.
- `feedback.base` names the one attempt whose source this call starts from: S0 steps 8-9 improve existing code, and after round 0 that code exists (FR-1). Which attempt the orchestrator picks is not decided, and the record of lineage is OD-20.
- **Not decided**: which and how many attempts the orchestrator selects (top-k and bottom-k, the value of k, whether such a selection is mandatory) and how they are ordered. This stays the registered proposal.
- `profile` is the place for the measured result and the profile summary of an attempt. Version 1 fixes that it is an object; its members are not listed and not validated in version 1 (B4, OD-13).

### 5. Repair call

- This record adopts #4 §3b: a repair is **a new coder invocation**, and the round re-enters at the `coded` checkpoint; the substeps before it are not repeated.
- The repair call gets **a new spec**: same `run_id`, `round` and `candidate`, `attempt` raised by 1, all other sections copied unchanged from the spec of attempt 1 (so `feedback.base` stays that of attempt 1), plus `repair`.
- `repair.failures` has one entry per reported earlier attempt of this candidate, in ascending `attempt`; the last entry is attempt `id.attempt` − 1, whose source is the one to repair. `stage` is `compile` (FR-5) or `sim` (FR-1 ⑴); a failure at `board` eliminates the candidate (FR-1 ⑵) and is never repaired.
- The earlier coder process is not continued: a round resumed after a process death must be able to issue the repair call from files alone (NFR-1), so the spec is self-sufficient (decision 1).
- No limit on repair calls is set here (OD-19).

### 6. The two questions handed over by ADR-0001

- **(a) Operational contract.** The spec carries the contract of the operation kind in `task.contract`: the source language, the exact prototype of the entry point, and one entry per operand with its role, element type and shape. The spec carries the contract and does not define it: the values come from the harness side, which calls the kernel (PLAN P1-3) and is not written yet. Anything about the storage of an operand that the `layout` value of the op_signature does not say is added to the operand entry when the first layout is fixed.
- **(b) Build settings.** Settings the orchestrator **prescribes** for a candidate are in the spec, in `task.build`; version 1 names no member. The settings a candidate was **actually built and run with** are a property of its build and measurement results and are recorded with them, outside the spec; `hilclaw.clang_build` already returns the exact compiler command. Whether the coder may choose settings itself, and the record that holds the used ones, are not decided here.

### 7. Versioning and room for the registered extensions

- `schema_version` is an integer, starts at 1 and is independent of the version of the embedded key records, which carry their own.
- It is raised when a field outside `ext` and outside the embedded records is added or removed, or changes its type, meaning or requirement, and when `profile` or `task.objective` get defined members. It is not raised for a new member of `ext` or `task.build`, a new value of `stage` or `task.contract.language`, or a new operation kind. Reading older versions is OD-11.
- Room without a decision: the structure of a profile summary (B4) goes into `profile`; forbidden patterns (S7), documentation excerpts or the statement that the documentation of a hardware ends at some point (B5, UC-0), and reference pointers (FR-15, for example to nntrainer) go into `ext` until a later record makes them fields. Version 1 names no `ext` member. Nothing a valid call needs may exist only in `ext`.

### 8. First payload (example)

The first call of round 1 for `cpu_standin` × the gate/up projection (2048→8192) at M = 1. `NOT-DECIDED-HERE` stands for a value that no source gives. **The example is therefore not a valid spec**; it shows the shape of the payload only.

```json
{
  "schema_version": 1,
  "id": {"run_id": "NOT-DECIDED-HERE", "round": 1, "candidate": 1, "attempt": 1, "candidates": 1, "relation": "single"},
  "hw_profile": {"key": "cpu_standin-b0d8610d8f470856",
    "record": {"schema_version": 1, "accelerator": "cpu_standin", "revision": "NOT-DECIDED-HERE", "toolchain": {"clang": "NOT-DECIDED-HERE"},
               "host": {"cpu": "NOT-DECIDED-HERE", "os": "NOT-DECIDED-HERE"}, "hw_source": "NOT-DECIDED-HERE"}},
  "task": {
    "op_signature": {"key": "gemm-c43e96fb16cc3f35",
      "record": {"schema_version": 1, "kind": "gemm", "shape": {"m": 1, "k": 2048, "n": 8192}, "dtype": "fp32", "layout": "NOT-DECIDED-HERE"}},
    "contract": {"language": "c", "prototype": "NOT-DECIDED-HERE", "operands": "NOT-DECIDED-HERE"},
    "objective": "NOT-DECIDED-HERE"},
  "guidance": {"techniques": [{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}]},
  "feedback": {"attempts": []}
}
```

| Value | Source |
|---|---|
| the two records and their `key` values | ADR-0001 decision 7, same values and placeholders (accelerator and `clang`: #5 A-7; shape, M, dtype: #5 B-4); the keys are those of the placeholder records, not of the real first instance |
| `round` 1, `attempt` 1, `candidate` 1 | the first call of the first round after bring-up (FR-1) |
| `candidates` 1, `relation` `single` | #5 B-4 (initial caps N = 1–2); `single` follows from N = 1 |
| `contract.language` `c` | #5 A-7 ② |
| `run_id`, `contract.prototype`, `contract.operands`, `objective`, the technique | not decided here: no source gives a run id form, the kernel's prototype and operand order, a target value (OD-1) or a technique of the stand-in catalog |
| `feedback.attempts` empty | shows the empty form only; a real round 1 follows the bring-up round, and what is shown from it is the selection left open in decision 4 |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | One spec per round, listing all candidates | Puts N into the structure of one file and shows every coder the tasks of the others; a repair would have to rewrite a spec that was already used. |
| 1 | One spec per candidate, extended in place on repair | The spec that produced attempt 1 could not be found again unchanged (NFR-2). |
| 2 | Key records by key only | The coder cannot turn a digest back into fields, and where the records are stored is OD-8. |
| 2 | Key records in full only | Works, but every reader would have to derive the names again to join a spec to `db/`; carrying both costs two strings and gives a consistency check. |
| 2 | Guidance as a pointer to the catalog | The catalog may change at a round boundary (NFR-7 ①), so a kept spec would no longer say what the coder was told; it also needs coder read access (OD-8, OD-14). |
| 3 | A list of all sibling candidates with their techniques | More general, but makes each spec depend on the content of the others; the two cases S8 names are covered by `relation`. |
| 4 | Only the previous attempt | The registered proposal needs several attempts side by side; an array costs nothing for the case of one. |
| 4 | No `base`: the best so far is the implied starting point, or the source is embedded in the spec | An implied rule would fix a selection policy (OD-20) and breaks when a run branches (FR-6); embedded source duplicates files whose place is OD-8. |
| 4 | Fixed `top` and `bottom` lists | Ranking needs the objective order (OD-1) and a measurement policy (OD-13); the selection can be added over a plain array. |
| 5 | The same spec plus a separate failure report | The input of the repair call would be two documents, one of them not covered by the spec's identification. |
| 5 | Continuing the earlier coder session | Fails after a process death and hides state outside the files (#4 §1). |
| 6 | Contract as prose in the guidance, or as a header file reference | Prose cannot be checked against the harness; a file reference needs the layout (OD-8). |
| 6 | Used build settings written back into the spec | Breaks immutability, and the coder's own choices are known only after the call. |
| 7 | Free additional fields anywhere | A misspelled field name would pass validation unnoticed; `ext` keeps unknown members in one place. |

## Consequences

- A later code task can write the JSON Schema and a validator from the tables. Rules across fields: `repair` exactly when `attempt` > 1; `single` exactly when `candidates` is 1; `variant` exactly when `same_technique`; `candidate` ≤ `candidates`; each `key` equals the name derived from its `record` (`hilclaw.keys`); `repair.failures` is in ascending `attempt`, its `stage` values are `compile` or `sim`, and its last entry is attempt − 1; every operand `shape` uses only values of the `op_signature` shape.
- The draft layout of #4 has one `rounds/<N>/spec.json` per round. It cannot hold one kept spec per (round, candidate, attempt); OD-8 has to provide for that.
- The spec names earlier sources by ref only. The coder can use them only if the coder-driver makes those sources readable; how is OD-8, OD-14 and OD-23.
- The payload is a plain JSON document with no reference to a Claude Code feature, so it can be the input of a Method A node unchanged (NFR-6).
- Guidance text is copied into every spec: specs grow, and a catalog edit never changes what an earlier spec says.
- The example becomes a valid spec only after the placeholder values are known.

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: the target NPU, its toolchain, kernel language and documents (#5 B-1); the input side — whether the MVP takes a fixed kernel spec file, `model_ref`, frontend formats (#5 B-5, OD-9); the tolerance vocabulary (#5 B-7) — and whether a tolerance is shown to the coder at all stays open, version 1 has no field for it; the target vocabulary (#5 A-4, OD-1) — `task.objective` reserves the place only; the coder's model (#5 A-8); OD-25; OD-3; C-6.
- **Values of the first GEMM that no source gives**, open questions for the task that commits the real example: the memory layout (B-4 has none; "row-major" is the integrator's assumption) and the vocabulary of `layout`; the C prototype of the kernel, the operand roles and their storage order; the `hw_source` of `cpu_standin`, its `revision`, host and clang version strings; the form of a `run_id`; a technique of the stand-in catalog.
- **OD-8**: where a spec file lives and what it is called (`rounds/<N>/spec.json` is the draft of #4, not confirmed), the layout of the coder's output (`coder/`), `instance.json`. Whether one instance may cover several values of M is a question of `instance.json`; a spec has one.
- **OD-23**: the agent roster, which agent writes the spec, how the spec is handed to `claude -p` (prompt template, file or standard input), and the output half of the coder-driver contract — what the coder returns, how it is captured, and the record of the build settings actually used. This record is the input payload only, a subset of that contract.
- **OD-12**: whether the coder may search by itself; excerpts bundled by the orchestrator are not made an MVP requirement here.
- **OD-14 / NFR-4** (coder working directory, permissions, timeouts), **NFR-5** (token accounting), **OD-19** (limits on repair and coder calls), **OD-13** (measurement), **OD-16** beyond the minimum of FR-9, **OD-20** (archive, lineage), **OD-28** (baseline, and what round 0 does beyond FR-1), **OD-29** (parallel or sequential coder calls, k), **OD-7**, **OD-11**.
- **The harness-side contract of a kind** (PLAN P1-3): the values of `task.contract` and what a correctness failure report may say within the rule of decision 2.
- **Rest of OD-6**: the selection rule of the feedback part (contrastive top-k and bottom-k), the profile summary structure (B4), forbidden patterns (S7), documentation excerpts and the documentation-limit statement (B5, UC-0). They stay registered proposals.
- Code, JSON Schema files, validators and committed example files: later code tasks.

## References

- [Requirements](../Requirements.md): FR-1, FR-2, FR-5, FR-6, FR-8, FR-9, FR-13, FR-15, NFR-1, NFR-2, NFR-4, NFR-5, NFR-6, NFR-7, C-6; register rows OD-1, OD-3, OD-6, OD-7, OD-8, OD-9, OD-11, OD-12, OD-13, OD-14, OD-16, OD-19, OD-20, OD-21, OD-23, OD-25, OD-28, OD-29.
- [OpenDecisionProposals OD-6](../OpenDecisionProposals.md#od-6) (registered proposal); [UsageCases](../UsageCases.md) UC-0, UC-2; [StandardScenarios](../StandardScenarios.md) S0, S7, S8.
- [ADR-0001](ADR-0001-od4-key-schema.md) (the two records, value types, Boundaries bullet "OD-6").
- #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, A-8, B-1, B-5, B-7
- #4 body §1, §2c, §3a, §3b, §3c, "합의 레이아웃", §4; #4 roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881
- #7 S-1 supplement, item (6) https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5139423949
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-3, P1-5; `hilclaw/keys.py`, `hilclaw/clang_build.py`; task T-0017.
