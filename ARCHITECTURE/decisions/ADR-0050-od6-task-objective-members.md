# ADR-0050: The members of `task.objective` in version 2 of the spec — a list of objectives and a set of constraints — and the value of the first case (the frame of OD-1 as the repository owner fixed it; one more part of OD-6)

## Status

- **Accepted on 2026-10-13** (UTC) under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Two kinds of content.** The **owner's decisions** are the answer to HQ-0009 of 2026-10-13 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136238336), quoted in full in Context as O1 to O5. Where this record uses one it is quoted and marked **owner**; these are not subject to the 7-day window, and this record means neither to widen nor to narrow them; where its own design limits how far one of them reaches, it says so (decision 5 with L6, and L7), and where it reads one further than its letter, it says that too (exception (b) of decision 6). **Everything else is this record's own design and has not been confirmed by the owner**: every member name, every spelling of a type value, the JSON types, the rules of validity, the wording of the version rule and the limits.
- It defines **one more part of OD-6** (Open Decisions register in [Requirements](../Requirements.md)): the members of `task.objective`, the place [ADR-0002](ADR-0002-od6-codegen-spec.md) reserved. The register row of OD-1 takes the status `확정` **for the frame, by the owner's answer** (O3) and not by this record; what stays open of OD-1 is listed under Boundaries.
- **It is a record, not code.** `hilclaw/spec.py` on `main` knows version 1 only; until the code slice of Consequences lands, nothing accepts a version-2 spec. No schema file, tool or example file is added.
- It builds on ADR-0002 (decisions 2, 7 and 8). **If ADR-0002 is reverted, this record falls with it.** Decision 3 cites [ADR-0007](ADR-0007-od13-measurement-policy.md) and [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md); if either is reverted, decision 3 is revisited. No earlier record is edited; sentences of theirs that are now less exact are listed under Consequences.
- The repository owner is notified on issue #5. For this record's own design the owner may object within 7 days of that notice; an objection creates a task that reverts those parts and the edits made with them.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What is asked for.** FR-2: the target is not fixed by the system; it is offered as "선택 가능한 target type 메뉴(vocabulary)" and stated by the user for each Loop instance. FR-5 makes the spec handed to the coder a first-class interface.
- **What the records left.** ADR-0002 decision 2: `task.objective` is required, "any JSON value", "The target of the instance (FR-2), copied from the instance record. Not validated in version 1"; its example writes `NOT-DECIDED-HERE` there. ADR-0002 decision 7: `schema_version` "is raised when a field outside `ext` and outside the embedded records is added or removed, or changes its type, meaning or requirement, and when `profile` or `task.objective` get defined members." ADR-0007 decision 1: the measurement policy "chooses **neither the quantity nor its direction** (OD-1)". ADR-0009 decision 3: the timing run "names no quantity, no unit of a quantity and no direction". The register row of OD-1 was `차단됨` on #5 A-4.
- **The owner's answer to HQ-0009** (2026-10-13; the question, with the options the letters refer to: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6096527683), quoted in full:
  - **O1** — "**Which target the run states: (a)** — latency minimisation: the time of the kernel call as the harness timing run measures it, lower is better. This is the starting point of early development only: both (a) latency minimisation and (b) throughput maximisation are to be offered, and which a run states is the user's choice per instance at run time (FR-2). The quantity and unit of (b) are not fixed here; an instance may state a type only once its quantity and unit are fixed, so until then latency minimisation is the only type an instance can state."
  - **O2** — "**A constraint beside it: (b) in the vocabulary; the first committed example carries no value.** How it is stated: an instance states, beside its objectives, a set of constraints, each entry of one named constraint type. The first type is the memory ceiling: an upper bound, in bytes, on the memory the kernel's execution uses at the execution point that measures it, operands included. Which measurement of the first case stands for that memory on `cpu_standin`, how it is taken, and at which of the two execution points (HQ-0005) it is judged, is the record's design. A candidate over its ceiling is infeasible and is not compared on the objectives; what the round loop then does with it is what FR-1 does with a failed correctness check at the same execution point. A constraint is optional per instance. Further constraint types are added by later records under #5 A-4 without a change of the first case."
  - **O3** — "**Scope: the frame of the MVP menu is fixed, the rest of #5 A-4 stays open.** The proposal "a single objective plus an optional memory ceiling" is not confirmed. An instance states a list of objective types, each with an optional weight or priority, beside a set of constraint types; the direction of each type is the type's own. Until the rule that combines more than one objective (priority order, weighted sum, Pareto) is decided under A-4, an instance states exactly one objective and neither a weight nor a priority; the members exist so that the schema does not change later. The full list of types is also decided later under A-4; the types named in 1 and 2 are a minimum of the menu, not its list. The OD-1 register row takes the status "확정" for this frame with the rest listed as remaining, as the OD-13 row did for its P1 minimum. The README's goal (speed and concurrent serving capacity) stands as the final goal; the MVP is a subset of it (#8 M15)."
  - **O4** — "**The spec's `schema_version`: (b)** — version 2 of the spec, with the members of `task.objective` defined by the record and checked by the validator. A new objective type or a new constraint type is a new value of a member, not a new member, and does not raise the version; this replaces the corresponding clause of ADR-0002 decision 7."
  - **O5** — "Owner's note: the final goal of the system is the optimisation of large-scale model serving on large-scale systems. A fixed-shape GEMM is one operation of the target model among many; no record is to assume that the other operations are negligible, that latency and throughput coincide in general, or that the objective vocabulary is narrowed to kernel latency."
- **O4 is the owner approval of a change of the spec schema** (CLAUDE.md A-13) for what it names: version 2 and defined members of `task.objective`. Nothing else of the spec is changed here.
- **The cut.** O2 leaves the memory measurement to "the record's design". This record defines the form of a memory-ceiling entry and **does not design that measurement**; it is registered as a sub-question (decision 5).
- **Facts of the repositories, none changed here** (checked on 2026-10-13). `hilclaw/spec.py` has `SCHEMA_VERSION = 1`, refuses every other version and says of itself "Not inspected: ``task.objective``". No spec file is committed: the source repository holds none, and the data repository `HIL-Claw-data` holds only `.gitignore`, `README.md` and three `.gitkeep` files; specs exist in tests only. `hilclaw/spec_file.py`, which reads and writes spec files, has no version of its own: it compares with `spec.SCHEMA_VERSION` and calls `spec.validate`. No module of `hilclaw/` measures the memory an execution uses.

## Decision

Whose a sentence is: **the owner's** where O1 to O5 is named; **cited** where another source is named; **this record's own** otherwise.

### 1. Version 2, and what `task.objective` is in it

- **Owner** (O4): "version 2 of the spec, with the members of `task.objective` defined by the record and checked by the validator."
- **Version 2 of the spec is version 1 of ADR-0002 with one change**: `task.objective` is an **object** with exactly the two members `objectives` (decisions 2 and 3) and `constraints` (decisions 4 and 5), in place of "any JSON value … Not validated in version 1". The `schema_version` of such a spec is the integer `2`. Every other section, field and rule across fields of ADR-0002 holds for version 2 unchanged, and so does the meaning of the field: "The target of the instance (FR-2)" (cited: ADR-0002 decision 2).
- **The types** are those ADR-0002 uses: a *name* matches `[a-z][a-z0-9_]{0,31}` and an *integer* is in the range 0 to 2^53 − 1 (cited: ADR-0001 decision 1); "An object holds exactly the members listed for it" (cited: ADR-0002 decision 2).
- **Version 1 is not touched.** What a version-1 spec is stays what ADR-0002 says; a document whose `schema_version` is 1 is not a version-2 spec, and this record defines no way to state the members below in it. What a reader does with a spec of another version than its own is not decided: "Reading older versions is OD-11" (cited: ADR-0002 decision 7), and OD-11 is open. No stored spec file waits on that question today (Context).
- **This record is about the parsed document, not about a file.** [ADR-0029](ADR-0029-od8-spec-file.md) gives the text form and the write of a spec file for version 1 only: "`schema_version` 1 is the only version a record defines", a file of another version "is set apart", and "A write by decision 4 writes a content of version 1 only" (cited: its decision 2). **The text form and the write of a version-2 spec file are therefore defined by no record, and not by this one** (L8; sub-question ⑤ of OD-6).

| Field | Type | Required | Meaning |
|---|---|---|---|
| `task.objective.objectives` | array of objective entry | yes | The objectives of the instance, as a list (O3). |
| `task.objective.constraints` | array of constraint entry, may be empty | yes | The constraints of the instance, as a set (O2). |
| objective entry: `type` | name | yes | The objective type. Its quantity, unit and direction are the type's own. |
| objective entry: `weight`, `priority` | reserved: no type, no meaning | must be absent (decision 2) | The two members O3 names. |
| constraint entry: `type` | name | yes | The constraint type. The unit and the sense of its bound are the type's own. |
| constraint entry: `bound` | integer | yes | The bound of the constraint, in the unit of the type. |

### 2. The objectives

- **Owner** (O3): "An instance states a list of objective types, each with an optional weight or priority, beside a set of constraint types; the direction of each type is the type's own. Until the rule that combines more than one objective (priority order, weighted sum, Pareto) is decided under A-4, an instance states exactly one objective and neither a weight nor a priority; the members exist so that the schema does not change later."
- **The list is `task.objective.objectives`, an array of objective entries, each an object.** An array of plain names would leave no place for what O3 attaches to each entry.
- **An entry has no member for a direction.** The direction is the type's own (owner, O3); a member would let a spec state a direction its type contradicts.
- **In version 2 as this record leaves it, the array has exactly one entry and that entry has exactly the member `type`** (owner for the rule, O3: "exactly one objective and neither a weight nor a priority"; that it is a rule of validity of the spec is this record's). A spec with an empty array, with two or more entries, or with an entry that carries `weight` or `priority`, is invalid. Whether a later list may hold one type twice is not decided.
- **`weight` and `priority`: this record's reading of "the members exist", provisional.** The two names belong to the objective entry of version 2 and to nothing else: no other member of an entry will take them. **They get no JSON type and no meaning here** — both belong to the combining rule, which is open under #5 A-4 and is the owner's. A spec that carries either is invalid until a record of that rule gives them a type and a meaning. That record is **meant not to raise the version** when it does so and when it admits more than one entry (O3: "so that the schema does not change later"); decision 6 writes the version rule accordingly. Whether an entry may then carry both, or only one of the two ("an optional weight or priority"), is not read either way.
- **What this reading does not give.** A reader of version 2 built before that record refuses a spec that carries a weight, a priority or a second entry: the number 2 alone does not say whether a reader knows the combining rule. The same holds for a new type value under O4.

### 3. The first objective type

- **Owner** (O1): "latency minimisation: the time of the kernel call as the harness timing run measures it, lower is better."
- **Its value of `type` is `latency_minimisation`** (the spelling is this record's). In version 2 as this record leaves it, it is the only admitted value of the `type` of an objective entry.
- **The quantity: cited, with nothing added.** This record reads "as the harness timing run measures it" as pointing at two sentences. ADR-0009 decision 3: "Between the two readings of one repeat lies **exactly the kernel call** `hilclaw_gemm(m, k, n, a, b, c)` of decision 4 and nothing else", and the driver "reports the **length of the timed interval**: the difference of the two readings as a whole number of **nanoseconds**" (and decision 4 of the same record: "**One repeat times exactly one call.**"). ADR-0007 decision 5: "The one number that stands for a measurement is the **trimmed mean**". Of the two cases ADR-0007 decision 1 names ("the time itself, or a rate derived from it"), the owner's words are the first. Which sample form a caller of a timing run passes (ADR-0009 decision 7) is the contract of the run tools and is not decided here; the sentence on direction below speaks only of measurements whose samples are that quantity, the interval lengths.
- **The direction** is the owner's: lower is better. ADR-0007 decision 7 calls two measurements "different" or "not different" and leaves open "Whether a pair that *is* different is an improvement or a regression". For this type, in an ordered pair (A, B) that the rule calls different, B is an improvement on A when B is the lower of the two (the whole interval of the ratios lies below 1 / (1 + `delta`)) and a regression when it is the higher. The rule "does not ask how the two came to exist" (cited, same decision), and neither does this sentence: which measurement is A and which is B — a baseline, an incumbent, a candidate — is not said here (OD-28, OD-20). **Nothing more of an order is given**: the margin `delta` and whether it becomes an instance parameter, what holds for a "not converged" measurement, for two measurements of different sessions and for more than two candidates stay with OD-13 and OD-1.
- **Throughput maximisation** is the owner's as a type "to be offered" (O1) and **gets no value here**: "The quantity and unit of (b) are not fixed here; an instance may state a type only once its quantity and unit are fixed" (O1). No version-2 spec can state it.

### 4. The constraints

- **Owner** (O2): "an instance states, beside its objectives, a set of constraints, each entry of one named constraint type. The first type is the memory ceiling: an upper bound, in bytes, on the memory the kernel's execution uses at the execution point that measures it, operands included." And: "A constraint is optional per instance."
- **The set is `task.objective.constraints`, inside `task.objective`.** O4 approves defined members of `task.objective`; a new member of `task` beside it is not named by O4 and is not taken.
- **The member is required and may be an empty array.** "No constraint" then has one form, the empty array, as ADR-0002 has it for `guidance.techniques` and `feedback.attempts`; an absent member is invalid.
- **It is a set of types**: no two entries have the same `type`, and the order of the entries carries no meaning. Two ceilings of one type would need a rule that says which one binds, and no source gives one.
- **An entry has exactly `type` and `bound`.** The name `bound` carries no unit, because by O4 a later constraint type "is a new value of a member, not a new member": the unit and the sense of the bound (upper or lower) are the type's own, as the direction is for an objective type. A type whose bound is not one integer needs a new member and with it a new version (decision 6).
- **The memory ceiling is the `type` value `memory_ceiling`** (spelling: this record's). Its `bound` is the upper bound in bytes (owner, O2), an *integer* of ADR-0001. **0 is a valid form** and means zero bytes, never "no ceiling" — an instance without a ceiling has no such entry. A validator checks the form and not whether a bound can be met: a bound below the size of the operands can be met by no candidate either, and a special case for 0 would suggest a check that does not exist.
- **Infeasibility is the owner's and is quoted, not extended** (O2): "A candidate over its ceiling is infeasible and is not compared on the objectives; what the round loop then does with it is what FR-1 does with a failed correctness check at the same execution point." Which execution point that is belongs to decision 5, so which case of FR-1 applies is not yet determined.

### 5. What is not judged yet

- **This record defines the form of a memory-ceiling entry and nothing that judges one.** "Which measurement of the first case stands for that memory on `cpu_standin`, how it is taken, and at which of the two execution points (HQ-0005) it is judged" (O2) is a later record's. It is registered as **sub-question ⑨ of OD-13**: it asks what the harness measures and how at `cpu_standin`, which is where ADR-0009 answered the same for time, and the members of the spec do not depend on its answer, so OD-6 is not its place. O2 calls it "the record's design"; this record reads that as the design of a record under DRIVER §9 — a later one, by the cut of Context — so that it needs no further owner answer. The reading is this record's.
- **Until that record exists, nothing can judge a ceiling**: no record names a measurement of memory and no module takes one (Context). The first committed example carries no value (owner, O2).
- **No part of the runtime may treat a ceiling that was not judged as met.** Feasibility is a verdict on a measurement; a candidate whose memory was not measured has no such verdict, and the absence of a verdict is never "within the ceiling". This is a principle that binds whatever is written later; it is not a mechanism, and this record writes none for the round loop.
- **`memory_ceiling` is defined and is not yet an admitted value** (this record's own choice, provisional). In version 2 as this record leaves it, no value of the `type` of a constraint entry is admitted, so a valid spec has an empty `constraints`. **When `memory_ceiling` is admitted is for the record of sub-question ⑨ to say** — that record, not this one, knows from when something can judge a ceiling (a record alone judges nothing; the harness code that follows it does). Reason: a spec that carried a ceiling today would be a statement nothing can judge, and enforcing the principle above for such a run would need a mechanism of the round loop, which is not this record's to write. Refusing the entry needs no such rule. It follows the pattern O1 states for an objective type ("an instance may state a type only once its quantity and unit are fixed"); applying that pattern to a constraint type is this record's choice, not the owner's.
- **The later admission needs no new version**: admitting `memory_ceiling` is admitting a value of `type` (O4; decision 6). **The cost**: until then no instance can state a memory ceiling, although the owner's vocabulary has one.

### 6. What replaces the clause of ADR-0002 decision 7

- **Owner** (O4): "A new objective type or a new constraint type is a new value of a member, not a new member, and does not raise the version; this replaces the corresponding clause of ADR-0002 decision 7."
- The clause is the end of the second bullet of that decision: "and when `profile` or `task.objective` get defined members" (cited). **For `task.objective` it is replaced by the wording below, which is this record's**; for `profile` it stands as written.
- **The general clause of that bullet is not replaced and reaches the new members.** It raises the version "when a field outside `ext` and outside the embedded records is added or removed, or changes its type, meaning or requirement" (cited). In version 2 the members of decision 1 are fields in that sense, as `id.attempt` or `task.contract.language` are in ADR-0002's tables. The wording below says for them what the general clause says, with renaming named as well.
- **From version 2 on, with respect to what is inside `task.objective`, `schema_version` is raised** when a member of `task.objective`, of an objective entry or of a constraint entry is added, removed or renamed, or changes its JSON type, its meaning or its requirement — **with the one exception (b) below**. Examples of what would still raise it: a direction, a unit, a second bound or a margin in an entry, an execution point in an entry, a third member beside `objectives` and `constraints`, a `bound` that is not an integer, `constraints` made optional.
- **It is not raised** when:
  - **(a)** a new value of the `type` of an objective entry or of a constraint entry is admitted (**owner**, O4) — the admission of `memory_ceiling` that the record of sub-question ⑨ provides for is of this kind;
  - **(b)** the record of the combining rule gives `weight` and `priority` their type and meaning and admits them, or admits more than one objective entry. **This is an exception to the wording above and, by its letter, to the general clause of ADR-0002 decision 7, which O4 does not replace. Its only authority is this record's reading of O3, which is provisional**: taken by the letter, a member that goes from "must be absent, no type" to "allowed, with a type" changes its type and its requirement. The reading is that O3 states both limits as temporary in the same sentence that sets them ("Until the rule … is decided under A-4") and says what the reserved members are for ("so that the schema does not change later"); version 2 therefore already announces their lifting, and a version raised at that moment would be the change of schema O3 means to avoid. If the owner does not share the reading, (b) falls and that later record raises the version; nothing else of this record depends on it.
- In both cases the set of valid documents only grows: every spec that was valid stays valid with the same meaning.
- ADR-0002 is not edited. Apart from the replaced clause (owner, O4) and exception (b) (this record's reading), its decision 7 stands as written.

### 7. O5 as a constraint on this text

- **Owner** (O5): "no record is to assume that the other operations are negligible, that latency and throughput coincide in general, or that the objective vocabulary is narrowed to kernel latency."
- No sentence of this record assumes any of the three. **Where the frame leaves room**: the objectives are a list, not one value; each type carries its own quantity, unit and direction, so a type that is maximised and a type that is minimised stand side by side without a shared scale; the list of types is open (O3: "a minimum of the menu, not its list"), and a later type need not be about one kernel call. `latency_minimisation` is the first value of a member, not the shape of the member.
- What the first type measures is the time of one call of one kernel (decision 3). This record does not say what an improvement of it is worth for a model or for serving.

### What the validator of version 2 is to check

A document is a valid version-2 spec when it is valid by ADR-0002 with `schema_version` 2 in place of 1 and, in addition:

1. `task.objective` is an object with exactly the members `objectives` and `constraints`.
2. `objectives` is an array of exactly one entry; the entry is an object with exactly the member `type`; `type` is the name `latency_minimisation`.
3. `constraints` is an array; in version 2 as this record leaves it, it is empty (decision 5).
4. Once `memory_ceiling` is admitted (decision 5): each entry of `constraints` is an object with exactly `type` and `bound`; `type` is an admitted name; `bound` is an integer; no two entries have the same `type`.

### Limits

- **L1 — Form, not measurability.** The validator checks the form of `task.objective`. It does not check that the quantity of a type can be measured on the backend of the instance or at an execution point. The sentences cited in decision 3 are about a C kernel at `cpu_standin`; for a simulator, a board or another kind nothing says how "the time of the kernel call" is taken.
- **L2 — Nothing ties the value to the instance.** ADR-0002 says the value is "copied from the instance record"; no record gives `instance.json` a member that states objectives or constraints, so nothing can check that a spec carries what its instance stated, or that two specs of one run agree (within one candidate, a repair spec copies the section — cited: ADR-0002 decision 5).
- **L3 — One objective only.** The frame says nothing of how two objectives are combined or compared. With one objective, "compared on the objectives" (O2) has the direction of one type and no more of an order (decision 3).
- **L4 — Nothing was run.** No validator accepts a version-2 spec. The example below was checked only as far as the validator of `main` goes: with `schema_version` set to 1 it passes `hilclaw.spec.validate`, which inspects nothing of `task.objective`.
- **L5 — The version number says less than before.** Two readers of version 2 can differ in the type values they admit (decisions 2 and 6); a spec one of them accepts the other may refuse.
- **L6 — No instance can state a memory ceiling or throughput yet** (decisions 3 and 5).
- **L7 — The entry form holds O4 only for types that fit it.** O4 says without condition that a new constraint type "is a new value of a member, not a new member, and does not raise the version". The entry of decision 4 has one integer `bound`, and an objective entry has `type` alone: a later type that needs a threshold with a fraction, a range, two bounds or a parameter of its own does not fit, and admitting it would need a member change and a new version (decision 6). That is a limit of this record's design, not of the owner's sentence; the form is a provisional choice.
- **L8 — No spec file of version 2.** ADR-0029 covers files of version 1 (its decision 2; decision 1 above). It also leaves the numbers inside `task.objective` to "the records that define those members", and its rule for the spelling of an integer binds places "where ADR-0002 or ADR-0001 gives *integer*" in a version-1 file. This record makes `bound` an *integer* of the parsed document and **does not say how it is spelt in a file** (`5.0`, `1e3` or `-0` are neither admitted nor refused), nor that the rules of ADR-0029 carry over to version 2. Until the record of sub-question ⑤ of OD-6 says so, nothing can write or read a version-2 spec file under a record.

## Example

**The `task.objective` of the first case under version 2** — one objective of the latency type, no constraint (owner, O1 and O2; the members and spellings are this record's):

```json
{"objectives": [{"type": "latency_minimisation"}], "constraints": []}
```

**The example of ADR-0002 decision 8, restated**: the first call of round 1 for `cpu_standin` × the gate/up projection (2048→8192) at M = 1. The values that later records closed are cited in the table and not re-decided.

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
  "guidance": {"techniques": [{"id": "NOT-DECIDED-HERE", "text": "NOT-DECIDED-HERE"}]},
  "feedback": {"attempts": []}
}
```

| Value | Source |
|---|---|
| `schema_version` 2, `task.objective` | this record (decisions 1 to 5) |
| `run_id` | cited: the example id of [ADR-0027](ADR-0027-od8-run-id-form.md) decision 2; not the id of a real run |
| `hw_profile` record and key | cited: the Example of [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md), "A plainly fictitious machine"; not a real machine |
| `op_signature` record and key, `task.contract` | cited: [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) decisions 4, 5 and 9 |
| the other members of `id`, `feedback.attempts` | cited: ADR-0002 decision 8, unchanged |
| the technique | **still lacking**: no source gives a technique of the stand-in catalog (OD-22) |

`NOT-DECIDED-HERE` would pass a check of form, and the example is still **not the spec of a real call**: no technique has that name, the machine is fictitious and the run id is an example.

**Form only — a memory-ceiling entry with a synthetic bound.** No committed example carries one (owner, O2), and no version-2 spec is valid with it until `memory_ceiling` is admitted (decision 5):

```json
{"type": "memory_ceiling", "bound": 123456789}
```

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | Stay at version 1 and describe the value in prose | O4 chose version 2 with checked members. |
| 2 | `objectives` as an array of type names | No place for a weight or a priority per entry (O3). |
| 2 | Give `weight` and `priority` a type now (a number, an integer rank) | Their type and meaning are the combining rule's, which is the owner's and open. |
| 2 | Do not name `weight` and `priority` at all until the combining rule | O3: "the members exist so that the schema does not change later". |
| 2 | A `direction` member in an entry | The direction is the type's own (O3). |
| 3 | The type value `latency`, with the direction implied | A reader could take it for a quantity whose direction is stated elsewhere; the value names what the owner named. |
| 4 | `constraints` as a member of `task`, beside `objective` | Not a member O4 names. |
| 4 | `constraints` absent when there is none | Two forms of "no constraint", or a rule that forbids the empty array; ADR-0002 writes its arrays as required and possibly empty. |
| 4 | A map from type name to bound | An entry could never get a further member without changing the JSON type of the whole. |
| 4 | The member name `bytes` | A later constraint type with another unit would need a new member, against O4. |
| 4 | Refuse a bound of 0 | See decision 4. |
| 5 | Accept a well-formed `memory_ceiling` entry now | A valid spec would state a ceiling nothing can judge, and only a rule of the round loop could keep it from counting as met. |
| 5 | Design the memory measurement in this record | A design of the harness and of the execution points of its own size; the members do not depend on it. |

## Consequences

- **Slices for the planner** (no module or function is decided here): (a) the record of sub-question ⑤ of OD-6 (the text form and the write of a version-2 spec file); (a′) version 2 in `hilclaw/spec.py` — the checks listed above, on a parsed document — and with it `hilclaw/spec_file.py` and the tests; code mode, the schema change is approved by O4; (b) the record of sub-question ⑨, then its harness slice; (c) the record of the `instance.json` member that states objectives and constraints (PLAN P1-8), then its code; (d) the committed GEMM spec example (PLAN P1-5), which still lacks a technique.
- **Slices (a) and (a′) are not independent.** `hilclaw/spec_file.py` takes its version and its check from `hilclaw/spec.py` (Context), so a change of the validator's version alone would make the package write and accept version-2 spec files and set version-1 files apart — the state L8 says no record defines. Either the record of sub-question ⑤ comes first, which is the order above, or the code slice keeps the reading and writing of spec files at version 1, and how it would do that hangs on the same sub-question and on OD-11.
- **Today, and until slice (a′) lands,** the package writes and accepts version 1 only, with any JSON value as `task.objective`.
- **A-13 reading.** Document mode; no code, dependency, settings or schema file changes. The data-plane schema change — version 2 of the spec — is the one O4 approves; no member of `instance.json`, `STATE.json`, an event or a result file is named.
- **Sentences of earlier records that are now less exact** (none edited; each stays true of version 1 or of what remains open): ADR-0002 decision 2 (the rows of `schema_version` and `task.objective`), decision 7 (the clause O4 replaces, and the general clause of the same bullet as far as exception (b) of decision 6 goes), decision 8 (the placeholder and the row "a target value (OD-1)"), Consequences ("The example becomes a valid spec only after the placeholder values are known") and Boundaries ("the target vocabulary (#5 A-4, OD-1) — `task.objective` reserves the place only"); ADR-0007 Context ("the target quantity and the order"), decision 1 ("neither the quantity nor its direction"), decision 7 ("is the direction of the quantity (OD-1)") and Boundaries (the first bullet); ADR-0009 Context, decision 3 ("How the measured quantity is obtained from it stays with OD-1"), the row "Sample form" of decision 9 and Boundaries (the first bullet); ADR-0008 Consequences ("Committed spec example") and Boundaries ("`task.objective` (OD-1, #5 A-4)"); the bullets that file the objective under what waits for the owner in [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (Context, Boundaries), [ADR-0020](ADR-0020-od8-instance-record-tolerance.md), [ADR-0034](ADR-0034-od8-instance-record-owner-project.md) and ADR-0035 (Consequences, Boundaries); ADR-0029 decision 2 ("`schema_version` 1 is the only version a record defines") and Boundaries; [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) Boundaries ("the sample form and the objective (OD-1, #5 A-4)"). The docstring of `hilclaw/spec.py` stays true of version 1.

## Boundaries (not decided here)

- **Owner-only, the rest of #5 A-4 / OD-1**: the full list of objective and constraint types; the quantity and unit of throughput; concurrent serving capacity; the roofline extension (B2); the rule that combines more than one objective, and with it the type, meaning and values of `weight` and `priority`.
- **OD-13 and OD-1**: the margin of an improvement, `delta` as an instance parameter, the order beyond the direction of one type, the handling of "not converged". **OD-28**: the baseline. **OD-15, OD-29**: promotion and k. **OD-2, OD-19**: budgets and any target value at which a run stops (FR-3 ④).
- **Sub-question ⑨ of OD-13**: the measurement that stands for the memory of O2 at `cpu_standin`, how it is taken, at which execution point it is judged, and the tool or result member that carries it.
- **Sub-question ⑤ of OD-6** (registered with this record; with OD-8 and OD-11): the text form and the write of a version-2 spec file — whether the rules of ADR-0029 carry over, the spelling of `bound` in a file, and what a writer and a reader of version 1 and of version 2 do beside each other.
- **PLAN P1-8**: the member of `instance.json` the value is copied from, and what an instance start checks. **OD-30**: how the expected effect of a hypothesis record (FR-17) names a metric and a direction. **OD-22**: the stand-in catalog and any technique.
- **Other backends, kinds, dtypes and kernel languages** (#5 B-1, B-2, B-3): how the quantity of a type is measured there. **`profile`** and its members (rest of OD-6, B4). **Reading a spec of another version** (OD-11).
- Code, tests, schema files, committed example files; any edit of FR-2, `README.md`, the #5 body or an earlier record (#8 M15 stays with the integrator).

## References

- [Requirements](../Requirements.md): FR-1, FR-2, FR-3, FR-5, FR-9, FR-17; register rows OD-1, OD-2, OD-6, OD-8, OD-11, OD-13, OD-15, OD-19, OD-20, OD-22, OD-28, OD-29, OD-30.
- [OpenDecisionProposals OD-1](../OpenDecisionProposals.md#od-1), [OD-6](../OpenDecisionProposals.md#od-6) ("하위 질문" ⑤), [OD-13](../OpenDecisionProposals.md#od-13) ("하위 질문" ⑨); [StandardScenarios](../StandardScenarios.md) S0, S1, S1-b, S2, S3, S6, S8, S9.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; decision 1); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 2, 5, 7, 8; Boundaries); [ADR-0007](ADR-0007-od13-measurement-policy.md) (decisions 1, 5, 7); [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 4, 5, 9; Consequences; Boundaries); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decisions 3, 4, 7, 9); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md), [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) and [ADR-0034](ADR-0034-od8-instance-record-owner-project.md) (the bullets on the objective); [ADR-0027](ADR-0027-od8-run-id-form.md) (decision 2); [ADR-0029](ADR-0029-od8-spec-file.md) (decision 2); [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (Example); [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) (the two execution points).
- `hilclaw/spec.py`, `hilclaw/harness/timing.py`, `hilclaw/harness/measurement.py`; tasks T-0017, T-0018, T-0117.
- #5 HQ-0009 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6096527683 · the owner's answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6136238336 · the HQ-0005 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6117798837 · B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body item A-4 · #8 M15.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-5, P1-8; CLAUDE.md "브랜치·merge 절차".
