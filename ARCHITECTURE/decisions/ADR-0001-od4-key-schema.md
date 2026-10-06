# ADR-0001: Key schema of `hw_profile` and `op_signature` (P1 minimum of OD-4)

## Status

- **Accepted on 2026-10-06** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes the **P1 minimum** of OD-4 (Open Decisions register in [Requirements](../Requirements.md)): the exact-identification fields of both keys, their canonical form, the derivation of the two directory names of FR-13, and the matching rule of P1. The rest of OD-4 stays open (see Boundaries).
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.

## Context

- FR-13 fixes that cross-run knowledge lives under `db/<hw_profile_key>/<op_signature>/...` in the data repository and that the layout mirrors the future DB schema. Owner and project are meta fields, not path levels (#4 §2c). Nothing said which fields make up either key or how a field set becomes a directory name.
- `hw_profile` is the tuple "accelerator + host environment"; `hw_source` is an attribute of it with two values, external vendor and in-house under development (UsageCases glossary, owner 2026-09-03).
- The first hw_profile is `cpu_standin`: C compiled with clang, on the owner's local PC under WSL first and a LAN machine later (#5 A-7, B-4, B-6). The first operations are the Llama 3.2 1B projection GEMMs — gate/up 2048→8192, down 8192→2048, QKV 2048→3072, O 2048→2048 — with M ∈ {1, 32, 512} as an instance parameter and dtype fp32; the second family is SDPA with KV cache (#5 B-4).
- Stored cases are hints, never ground truth (FR-15). Everything behaves the same on Linux, macOS and WSL (C-7). Persistent artefacts carry a `schema_version` (NFR-7 ②).
- The registered proposal ([OpenDecisionProposals OD-4](../OpenDecisionProposals.md#od-4)) has two layers: an exact-identification layer and a similarity-vector layer. No P1 code needs the second one.

## Decision

### 1. Fields of `hw_profile`

A hw_profile is a record made of **key fields** (they define the key) and **attributes** (they describe the record and never change the key).

| Field | Type | Required | Key | Meaning |
|---|---|---|---|---|
| `schema_version` | integer | yes | yes | Version of this key schema; `1` for this record. |
| `accelerator` | name | yes | yes | Identity of the accelerator or backend, for example `cpu_standin`. |
| `revision` | string | yes | yes | Hardware revision of the accelerator. |
| `toolchain` | map: component → version string | yes, at least one member | yes | Version of every software component between the kernel source and its execution on the accelerator: compiler, and where they exist firmware, driver, runtime. |
| `host` | map: property → string or integer | yes, with members `cpu` and `os` | yes | Host environment: `cpu` is the host CPU model, `os` the host operating environment. Further members (for example the memory size, UC-0) may be added when they are known to change measured performance. |
| `ext` | map: property → string or integer | no | yes | Identification fields of hardware that is not known yet. Absent when there are none. |
| `hw_source` | `external` \| `in_house` | yes | no | HW source: external vendor, or in-house under development. |
| `label` | string | no | no | Free text for humans. |

- A *name* matches `[a-z][a-z0-9_]{0,31}`. A *string* is 1 to 255 printable ASCII characters (0x20-0x7E). An *integer* is in the range 0 to 2^53 - 1. Map member names are names. Key fields hold no other JSON type (no float, boolean, null or array).
- `hw_source` is an attribute, not a key field: it classifies where the hardware comes from and selects its handling (OD-26), while every property that changes measured performance is already a key field. The same accelerator cannot differ in `hw_source` only.

### 2. Fields of `op_signature`

| Field | Type | Required | Key | Meaning |
|---|---|---|---|---|
| `schema_version` | integer | yes | yes | As above. |
| `kind` | name | yes | yes | Operation kind. The first kind is `gemm`. |
| `shape` | map: parameter → integer | yes | yes | Every shape parameter of the operation. The member names are fixed per kind. |
| `dtype` | name | yes | yes | Element type. The first value is `fp32`. |
| `layout` | name | yes | yes | Memory layout of the operands. |
| `ext` | map: property → string or integer | no | yes | Further identification fields of a kind. Absent when there are none. |
| `label` | string | no | no | Free text for humans, for example the model the shape comes from. |

- For `gemm`, `shape` has exactly `m`, `k` and `n`: the product of an m×k and a k×n matrix is an m×n matrix. For a projection of `in`→`out` features over M tokens, `m` = M, `k` = `in`, `n` = `out`. These are names of dimensions only; how the operands are stored or transposed is `layout` and the spec (OD-6).
- **M is part of the key.** B-4 names the three values decode, small batch and prefill. That they need different best kernels is a design argument of this record, not a statement of B-4. The agreed layout keeps one best reference and one set of technique statistics per (hw, op) directory (#4 "합의 레이아웃"); with M in the key both stay well defined without a level below the key.
- Consequences: `db/<hw_profile_key>/` has one directory per (projection shape, M). The four B-4 shapes times three values of M give 12 op_signatures; gate and up share one, because the key names the operation and not its place in a model. FR-7 statistics are kept per M; using the statistics of another M is a similarity question and stays open.

### 3. Canonical form and key derivation

1. **Canonical form**: the JSON object that holds exactly the key fields of the record (attributes and absent optional fields are left out; an empty `ext` is not allowed), serialised as UTF-8 with object members sorted by name at every level, no whitespace, integers in plain decimal, and strings escaped only for `"` and `\`. For this restricted value set this is the RFC 8785 (JCS) form.
2. **Digest**: SHA-256 of the canonical form, as 64 lowercase hexadecimal characters.
3. **Directory name**: `<prefix>-<first 16 characters of the digest>`, where `<prefix>` is the value of `accelerator` for `<hw_profile_key>` and the value of `kind` for `<op_signature>`.

- The names use only `[a-z0-9_-]`, are lowercase (valid and distinct on case-sensitive and case-insensitive file systems), start with a letter, are at most 49 characters long (32 + 1 + 16), and are reproducible by any tool from the field values alone.
- 16 hexadecimal characters are 64 bits; a collision is not expected for any realistic number of keys. A tool that finds an existing directory whose stored canonical form differs from its own reports an error and writes nothing.
- **Reading a key back**: the name shows the accelerator or the operation kind; the remaining fields cannot be recovered from the digest. The full record (key fields and attributes) must therefore be stored with the data so that it can be found from the directory name. Where and under which file name is OD-8.

### 4. Matching rule in P1

Two (hw_profile, op_signature) pairs are the same if and only if both canonical forms are byte-equal. A lookup hits when `db/<hw_profile_key>/<op_signature>/` exists and the canonical forms stored for it equal the ones looked up (decision 3). A hit makes the stored knowledge of that pair available as a hint (FR-15), not as a result to reuse without measuring. A miss means no stored knowledge; P1 tools do not look under other keys.

### 5. What makes a new key

- **New key**: a change of any key field — `accelerator`, `revision`, any component of `toolchain` added, removed or changed in version (a clang upgrade on `cpu_standin` is a new key), any member of `host` added, removed or changed in value (moving the stand-in to a machine with a different `host.cpu` or `host.os` is a new key; two machines with equal `host` members share one), `ext`; for an operation `kind`, any member of `shape` including `m`, `dtype`, `layout`, `ext`; and `schema_version`.
- **Same key**: a change of an attribute (`hw_source`, `label`), of anything stored outside the two records (tool endpoints and transport, document sources), of instance parameters that are not fields of `op_signature` (candidates per round, budget, gates, target, tolerance), and of per-candidate build settings such as compiler flags and thread count, which are not key fields in version 1.
- A new key starts with no stored knowledge. Whether the history of an earlier key is attributed to it is OD-26.

### 6. Versioning and room for unknown hardware

- `schema_version` is an integer, starts at 1, is stored in every record and is part of the canonical form.
- It is raised when the set or meaning of the required key fields, the canonical form or the derivation rule changes. All keys then change; directories written under an older version keep their names and their records. Reading or migrating them is OD-11.
- It is not raised for: a new `kind` with its `shape` members, a new `dtype` or `layout` value, a new member name in `toolchain`, `host` or `ext`, a new attribute. None of these changes the key of a record that is already stored; a profile that is registered again with an added member is a different record with a new key (decision 5).
- Hardware that is not known yet is described without a schema change through the open maps `toolchain` (any number of components), `host` and `ext`. This record names no vendor field.

### 7. First instance (example)

`cpu_standin` × the gate/up projection (2048→8192) at M = 1. `NOT-DECIDED-HERE` is a placeholder for a value that no source gives; it is hashed literally so that the example can be reproduced, and **the two names below are therefore not the names of the real first instance**. The placeholder is deliberately not a valid value where the field is a name or an enumeration (`layout`, `hw_source`), so that it cannot be taken for a real one: the example checks the canonical form and the derivation only, and is not a valid record.

| Field | Value | Source |
|---|---|---|
| hw `accelerator` | `cpu_standin` | #5 A-7 |
| hw `toolchain` | `{"clang": NOT-DECIDED-HERE}` | component: #5 A-7 ②; version: not decided here (read from the host when the profile is registered) |
| hw `revision`, `host.cpu`, `host.os` | `NOT-DECIDED-HERE` | not decided here; the host is the owner's local PC under WSL (#5 B-4 ⑤) |
| hw `hw_source` (attribute) | `NOT-DECIDED-HERE` | not decided here: no source says which of the two values a stand-in has |
| op `kind`, `shape` | `gemm`, `{m: 1, k: 2048, n: 8192}` | #5 B-4 (gate/up, M ∈ {1, 32, 512}) |
| op `dtype` | `fp32` | #5 B-4 |
| op `layout` | `NOT-DECIDED-HERE` | not decided here: B-4 gives no layout |

```
{"accelerator":"cpu_standin","host":{"cpu":"NOT-DECIDED-HERE","os":"NOT-DECIDED-HERE"},"revision":"NOT-DECIDED-HERE","schema_version":1,"toolchain":{"clang":"NOT-DECIDED-HERE"}}
sha256 = b0d8610d8f470856c134056a9541f60ce9e7a5c6bfabbeb9f1b784e57c495f9f  ->  cpu_standin-b0d8610d8f470856

{"dtype":"fp32","kind":"gemm","layout":"NOT-DECIDED-HERE","schema_version":1,"shape":{"k":2048,"m":1,"n":8192}}
sha256 = c43e96fb16cc3f35b841657b1743ba0a1109fb053418b480abc1764c5befe923  ->  gemm-c43e96fb16cc3f35
```

Path: `db/cpu_standin-b0d8610d8f470856/gemm-c43e96fb16cc3f35/`.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | `hw_source` as a key field | Adds no distinction between two pieces of hardware, and a reclassification would cut the history of unchanged hardware. |
| 1 | Toolchain version as an attribute | A cached result could not be invalidated after a compiler or firmware change (registered proposal, #4). |
| 1 | Fixed fields for firmware, driver and SDK | They would be guesses about hardware that #5 B-1 has not named; an open map needs none. |
| 2 | M as a dimension below the key (one directory per projection) | Needs a level below the key (OD-8) and makes "the best of this directory" ambiguous across decode and prefill. |
| 2 | A normalised IR structure hash as a required field | No frontend IR exists in the MVP (OD-9, #5 B-5). It can be added through `ext` or a later version. |
| 3 | Fully readable names that encode every field | Unbounded length, per-kind encoding rules, and version strings need escaping. |
| 3 | Digest only, or the full 64 characters | A listing would say nothing; 64 characters add path length without a practical gain. |
| 5 | Compiler flags and thread count as key fields | No source fixes them per hardware or per operation; they may differ between candidates of one pair, and as key fields they would split the knowledge of that pair. If they turn out to be fixed per profile, they can enter through `ext`. |
| 4 | Nearest-neighbour lookup in P1 | Needs the similarity layer, which no P1 code needs; it stays a proposal. |

## Consequences

- Later tasks can build both directory names from field values. A code task implements the canonical form and the derivation and can test these two steps against the example above; the example is not a test vector for record validation.
- A listing of `db/<hw_profile_key>/` shows only the operation kind; a tool or the stored record resolves the rest.
- Every toolchain or host change starts a new key without history. Under FR-15 this costs a cold start, not correctness.
- The real names of the first instance exist only after the placeholder values are known.

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: the target NPU and its toolchain (#5 B-1) — this record leaves extension points and names no vendor field; whether there is a frontend IR (#5 B-5, OD-9); OD-25; OD-3; C-6.
- **Memory layout of the first GEMM** and the vocabulary of `layout`: B-4 does not give them. Question for the task that writes the spec example (PLAN P1-5), possibly for the owner.
- **How the values of the hw key fields are obtained** (onboarding, OD-26, and the task that registers `cpu_standin`): which components are members of `toolchain` (for example whether an OpenMP runtime is one), the form of version strings, the source and normalisation of the `host.cpu` and `host.os` strings, which optional `host` members a profile carries, what `revision` holds for hardware without a revision of its own, the `hw_source` of a stand-in, and who fills in the record (probing or by hand). Until these are fixed, two tools may derive different keys for the same machine.
- **OD-8**: where the full record of a key is stored, file names, and everything about the directory tree beyond the two path levels of FR-13.
- **OD-26**: the onboarding registry schema, attribution of history when an in-house HW revision changes, sim-only onboarding.
- **OD-6**: which of these fields go into `spec.json`. Three further questions are raised by this record and are not yet registered sub-questions of any OD (follow-up of T-0015: register them): the operational contract of a kind (operands, calling convention) and where per-candidate build settings are recorded — both nearest to OD-6 — and whether one instance may cover several values of M, which may belong to OD-6 or to the `instance.json` schema (OD-8).
- **OD-7** (statistics), **OD-11** (reading or migrating older versions), **OD-13** (measurement).
- **Rest of OD-4**: the similarity-vector layer (FLOPs, bytes moved, arithmetic intensity, …), nearest-neighbour ranking and its "prior only" rule, and the S10 note "an environment change as a new key candidate". They stay registered proposals.
- The `shape` members of the second family (SDPA with KV cache): added when its spec is written; not a schema change (decision 6).
- Code, JSON Schema files and validators: later code tasks.

## References

- [Requirements](../Requirements.md): FR-7, FR-13, FR-14, FR-15, NFR-2, NFR-6, NFR-7 ②, C-2, C-3, C-7; register rows OD-4, OD-6, OD-8, OD-9, OD-11, OD-26.
- [OpenDecisionProposals OD-4](../OpenDecisionProposals.md#od-4) (registered proposal); [UsageCases](../UsageCases.md) glossary (hw_profile, op_signature, hw_source), UC-0.
- #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · B-6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944087839 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506
- #4 body §2a, §2c, "합의 레이아웃"; #4 comment (OD-4 row) https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; task T-0015.

## Record format

This is the first decision record; later records follow it until a separate convention replaces it (provisional).

- Location and name: `ARCHITECTURE/decisions/ADR-NNNN-<slug>.md`, with a four-digit running number.
- Sections, in this order: Status, Context, Decision, Alternatives considered, Consequences, Boundaries (not decided here), References.
- One closure per record: one OD, or one part of an OD, even when it takes several numbered decisions. A superseded record is kept and marked as superseded in its Status; it is never deleted (NFR-2).
- Written in English.
