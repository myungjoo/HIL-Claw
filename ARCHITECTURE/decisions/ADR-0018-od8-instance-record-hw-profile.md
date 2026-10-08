# ADR-0018: The `instance.json` of a run — the file and the member that states the hw_profile of the run (one more part of the rest of OD-8; the first part of sub-question ⑥ of OD-18)

## Status

- **Accepted on 2026-10-08** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one more part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): of `runs/<run_id>/instance.json`, the file as a whole and the one member in which a run states the hw_profile it was started with. With that member it answers **the first part of sub-question ⑥ of OD-18** (registered by [ADR-0016](ADR-0016-od18-backend-frame.md)): which file of a run states its hw_profile, and in which member. The register rows of OD-8 and OD-18 keep their status wording.
- What stays open: **every other member of `instance.json`** (see Boundaries — several wait for the owner), what writes the file, when and by which steps, the second and third part of sub-question ⑥ beyond decision 5, the kind of a call about a run that cannot be used (sub-question ④ of OD-18), the rest of OD-8 as [ADR-0014](ADR-0014-od8-whole-file-writes.md) lists it, and the two sub-questions this record raises.
- It builds on [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 3 and 5) and [ADR-0002](ADR-0002-od6-codegen-spec.md) (decision 2), whose objection windows run until 2026-10-13, on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 4, 5, 8, 9 and 10; until 2026-10-14) and on ADR-0016 (decisions 2 and 4; until 2026-10-15). [ADR-0012](ADR-0012-od8-runtime-state-file.md) (until 2026-10-14) is its model, not a rule for this file. If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- ADR-0004 fixed the path `runs/<run_id>/instance.json`, one file per run, its purpose — "What the instance was started with; source commit (#5 A-1); layout version" — and that it is the "immutable instance record", written by "The start of the instance, once" (the tree, the path table, decision 4). It fixed no field ("Fields: PLAN P1-8, OD-11"), and the tree "does not enforce the single writer", "gives no concurrency control" and "does not check the content of any file" (decision 10).
- ADR-0016 decision 4 fixed that the backend of a call of a HW tool about a run follows from the `accelerator` of the hw_profile of the run the request names — "the one selected when the instance was started" (FR-14 ④, UC-1 step 1) — "read from the data plane at each call", and left open where a run states it: "`instance.json` holds 'What the instance was started with' … and has no fixed member … The `spec.json` of an attempt embeds the record in full …, but it exists per coder call only and is a copy composed by a role (OD-23). This record defines no member of either file and chooses neither" (sub-question ⑥).
- The code waits for the answer. `hilclaw.hw_tool.tool_function` takes the reader of the hw_profile of a run as the parameter `hw_profile_of`, called as `hw_profile_of(data_root, run_id)`, and "reads no file for it and names none"; `hilclaw.backends.select` validates the record it is handed in full (`hilclaw.keys.hw_profile_key`) and reads its `accelerator` only. `hilclaw.layout.run_file` builds the path of the file, and no module of `hilclaw/` reads or writes it.
- Fixed and not re-decided. ADR-0001: the hw_profile record, its key fields and attributes, its key and the name of its key directory (decisions 1 and 3); "a change of an attribute (`hw_source`, `label`)" keeps the key (decision 5). ADR-0004 decision 5 and ADR-0014: the stored record `db/<hw_profile_key>/hw_profile.json`, created once; whether a stored attribute may be updated is OD-26. ADR-0002 decision 2: the `hw_profile` section of a spec carries the key name and the full record, a spec whose key is not the name derived from its record is invalid, and `task.objective` is "copied from the instance record". NFR-7 ②: a persistent artefact carries a `schema_version`. NFR-2, NFR-7 ③, #5 A-1 detail 3: `instance.json` records the source commit. A Loop instance is started with one HW (UsageCases glossary: "특정 HW + 특정 모델 + …"; UC-1 step 1).
- **Most of what an instance is started with cannot be given a member today**: the objective (#5 A-4, OD-1), the gates and the autonomy mode (#5 A-5, OD-3), the coder model and the token budget (#5 A-8) wait for the owner; the model input (#5 B-5, OD-9), datasets (#5 B-8), budget axes (OD-2, OD-19) and N (OD-21, OD-29) hang on open decisions. The file therefore gets its frame and one member here, as ADR-0012 gave `STATE.json` its frame and two of seven members.

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice — among them the text form, the place of `schema_version`, its first value and what raises it, the rule for members not defined here, the file chosen, the name and the form of the member, that the stored record is not read for the selection, and the list of situations in decision 4.

### 1. Scope

This record fixes two things of `runs/<run_id>/instance.json`: the file as a whole (decision 2) and the member that states the hw_profile of the run (decisions 3 to 5). **Every other member is not fixed here**, and nothing of any other file is. **A file that holds only what this record defines is not a complete instance record, and no run can be started from it alone.**

### 2. The file as a whole

- The file is **one JSON object**, UTF-8 without a byte order mark, with no member name twice in any object (as ADR-0012 decision 2 has it for `STATE.json`).
- **Written form**: LF line ends and a final line feed bind the writer; a reader accepts any JSON text of this shape. **No member order is fixed**, unlike ADR-0012: that order serves line-wise diffs between the contents of a file that is rewritten, and this file has one content for the life of the run (cited: ADR-0004 — written once).
- **`schema_version`** is a top-level member and the *integer* `1` (NFR-7 ②; the place and the value are this record's). It is the version of the schema of this file: of the rules of this decision and of the top-level members that records define for this file. The embedded hw_profile record carries its own (as ADR-0002 decision 7 says of a spec). **It is not, by this record, the layout version stamp** of ADR-0004 decision 9: whether that stamp "is a field of its own or follows from a `schema_version`" stays with the instance schema and OD-11, and neither answer is chosen or excluded — a later record may add a member, or add "a change of the layout" to what raises this version.
- **Required members in version 1**: `schema_version` and `hw_profile`.
- **Members this record does not define.** The top level is **open in version 1**: the file may hold further members. A reader does not interpret a member it does not know and does not treat it as an error; a validator of this record checks the two members above and, of the others, only the rules for the whole text. The object `hw_profile` is closed (decision 3).
  - Why open: the members an instance needs are added by later records, one decision at a time, and several wait for the owner. With a closed set, as ADR-0002 has it for a spec, each of them would be a new version before a first run exists, and reading a file of another version is OD-11. A spec is the input of one coder call and is written before that call (ADR-0002 decision 1); this file is read by calls of HW tools for the life of a run, by components that may be replaced meanwhile (NFR-7 ①).
  - **What raises the version**: a member defined for this file is removed or renamed, or its type, form or meaning changes; a member is added inside `hw_profile`; a later record makes a further top-level member **required**; or a later record says so for its member, because a reader that passes over the member would act wrongly — whether a member is of that kind is the judgement of the record that defines it. A later record that defines a top-level member which may be absent and may be passed over does not raise it. **A valid file is not thereby enough to start a run**: what a run needs in order to start is said by the records of those members, each of which chooses between a member that may be absent from a valid file and a new version.
  - The cost: a misspelt name of a member that may be absent is not detected by a version 1 validator, and since the file is never rewritten the mistake stays for the life of the run. Sub-question ⑫ of OD-8 (whether a writer keeps a member it does not know) is about a file that is replaced; it does not arise for this file as long as nothing rewrites it, and it is not answered here.
- **A file that is not valid.** The file is invalid when it is not UTF-8 without a byte order mark, is not exactly one JSON text that is an object, holds a member name twice in any object, lacks `schema_version` or holds a value there that is not an *integer*, or — at version 1 — lacks `hw_profile` or holds one that breaks decision 3. An empty file is invalid, not missing. A `schema_version` that is an *integer* other than `1` is not damage: a version 1 reader reports an unsupported version and interprets nothing (OD-11). A reader reports an invalid file, uses no member of it and repairs nothing.
- **A missing file** means that no instance record was written for this `run_id` (as ADR-0004 decision 1 says of a missing directory). What writes the file, and what a run directory that holds other files and not this one means, is not decided (sub-question ⑰); when it is written in relation to the first `STATE.json` stays sub-question ⑩ of OD-8. For a call of a HW tool it is one of the situations of decision 4.
- **How the file comes to be on disk is not decided.** ADR-0014 decision 7 left it open for this file, and it goes with what writes it (sub-question ⑰). Until then nothing excludes a partial file after the death of a writer; such a file is invalid by the rule above and is reported.

### 3. Where a run states its hw_profile

- **The file is `instance.json`, not the `spec.json` of an attempt.** The two reasons ADR-0016 named hold: a spec exists per coder call, so a run has none before its first coder call and N + r of them in a round (ADR-0002 decision 1), and a call would have to say which one; and each is composed by a role that no record has given to anyone (OD-23). A third: ADR-0002 already treats the instance record as the source of one member of a spec (`task.objective`, "copied from the instance record"); which record the `hw_profile` section of a spec carries is not said by this (sub-question ⑱). And the hw_profile is selected when the instance starts (cited: FR-14 ④), which is what this file holds (cited: ADR-0004).
- **The member is `hw_profile`** (the name of the #4 draft and of the section of a spec), required, an object with **exactly** the two members below:

| Member | Type and form |
|---|---|
| `hw_profile.key` | *string*: the `<hw_profile_key>` directory name of ADR-0001 decision 3 |
| `hw_profile.record` | object: the full hw_profile record of ADR-0001 decision 1, key fields and attributes |

- **Valid** when `record` is a valid record by ADR-0001 (what `hilclaw.keys.hw_profile_key` accepts) and `key` is the name derived from it; **a file whose `key` is not that name is invalid**, so neither is trusted over the other. This is the form and the rule of ADR-0002 decision 2 for the same section of a spec, which `hilclaw/spec.py` already checks; nothing of ADR-0002 changes.
- **It states the hw_profile the instance was started with** (cited: FR-14 ④, UC-1 step 1), key fields and attributes as they were given to the start. How the start obtains the record — from the stored record of the selected key or otherwise — is not decided (sub-question ⑱).
- **Why the full record.** The purpose of the file is what the instance was started with, and an attribute may change under the same key (cited: ADR-0001 decision 5; whether a stored one may be updated is OD-26): only a copy made at the start keeps what the run was started with (NFR-2). For the selection a call then reads one file of the run and no stored record of `db/`, which #5 A-1 keeps apart from `runs/` so that either can become a repository. And an operation is called with the hw_profile record (cited: ADR-0016 decision 2), so a call needs the record, not only its key.
- **Why the key beside it.** It names the `db/<hw_profile_key>/` level of the run's knowledge without a derivation (a reader that looks for the runs of a hw_profile key reads one member — one half of the pair of S5 step 1: no file states the op_signature of a run yet, see Boundaries), and its form is that of the same section of a spec. Unlike a second statement that cannot be checked, a disagreement of the two is found by one derivation and makes the file invalid.

### 4. How a HW tool reads it at each call

- The order of a call is ADR-0016 decision 2 and is not changed: the selection is ④, after the lookup and before the start line. **In ④ the tool function reads `runs/<run_id>/instance.json` of the data root of the call, for the `run_id` of the request, and the hw_profile of the call is its `hw_profile.record`.** The file is read as a whole and must be valid by decision 2; no other file is read for the selection, and the stored record `db/<hw_profile_key>/hw_profile.json` is not read or compared.
- **Nothing is kept between calls** (cited: ADR-0010 decision 7; ADR-0016 decision 4): every call that reaches ④ reads the file again. A call answered in the lookup — an ended or an open identity — does not read it for the hw_profile (cited: ADR-0016 decision 2 — nothing is selected for it). Whether a call reads the file for another member, such as the layout version stamp (ADR-0004 decision 9, OD-11), is the record of that member.
- So, for a call about a run, which hw_profile it is about is the same through both fronts and at every call, **as long as both fronts are given the same data root, run the same source, and the file is not changed** (decision 6).
- **Situations in which the hw_profile of the run cannot be had**: the file is missing; it cannot be read; it is invalid by decision 2 (an empty or partial file, and a `hw_profile` that breaks decision 3, included); its `schema_version` is an *integer* other than `1`. In each the call has not started the step — no backend is selected, nothing is consumed, no line is appended (cited: ADR-0016 decision 2) — and it is not `no_backend` (cited: ADR-0016 decision 4). **Which tool-failure kind such a call answers is not decided**: it is sub-question ④ of OD-18, which these situations join.

### 5. One hw_profile per run; a call about no run

- **In version 1 a run states exactly one hw_profile**: the member is one object and is required. The inputs carry one — an instance is started with one HW (cited: FR-14 ④, UC-1 step 1, the glossary) — so no call has to tell which. Whether a run may ever hold more than one is not decided; a record that admits it changes `hw_profile`, or adds a member that a version 1 reader must not pass over (decision 2), and so raises the version, and says then how a call tells which. That part of sub-question ⑥ stays registered.
- **A call about no run has no rule here either**: it names no `run_id`, so no file of this record states its hw_profile. Whether such a call exists — the smoke test of UC-0 step 5 — is OD-26, and that part of sub-question ⑥ stays registered.

### 6. Limits

- **Whoever can write the file changes the backend of a run** (cited: ADR-0016 decision 6). No access control exists, and the tree does not enforce the single writer (ADR-0004 decision 10).
- **A file changed after the start.** "Immutable" is ADR-0004's word and nothing enforces it: a call reads the file as it is at that call, so two calls of one run can be about two hw_profiles, and a validator of this file alone cannot tell. The history of the data repository shows a change of a committed file; which step commits is not decided.
- **The copy and the stored record.** The embedded record and `db/<hw_profile_key>/hw_profile.json` can differ in attributes — not in key fields under one key, short of a collision of the name (ADR-0001 decision 3) — and a stored record may not exist at all for the key of a run: the selection does not look. `hilclaw.key_records.store_op_signature` refuses a key directory below a hw_profile without a stored record, so the package stores no op_signature record below that key until the hw_profile record is stored; who registers, and when, is OD-26.
- **The target is not checked against the record** (cited: ADR-0016 decision 6). The file says what was selected at the start; that the machine reached at a call is still the one its key fields describe is not established, and a hardware revision during a run does not change the file (UC-0 alternative flow, OD-26).
- **Two runs, two hw_profiles, one data root**: each call reads the file of the run its request names. A caller can name another run (ADR-0015 decision 7) and is then answered for that run's hw_profile.
- **Two processes, two validators**: an MCP server runs the source it loaded at its start and a command-line call the source as it is now (cited: ADR-0010 decision 7; ADR-0016 decision 6). If a later record adds a rule for a member without raising the version, one front can take a file as valid that the other refuses, and only one of them has the hw_profile of the run.
- **A member passed over.** A version 1 reader ignores a member it does not know; the guard is the version rule of decision 2, which a later record must apply.

### Example

`cpu_standin` with the placeholder values of the example of ADR-0001 decision 7, hashed literally there: **the key is not the name of the real first instance**, and `NOT-DECIDED-HERE` is no valid `hw_source`, so this is the shape of the member and **not a valid file**. It is visibly not a complete instance: no objective, tolerance, budget, gate or source commit.

```json
{
  "schema_version": 1,
  "hw_profile": {
    "key": "cpu_standin-b0d8610d8f470856",
    "record": {
      "schema_version": 1,
      "accelerator": "cpu_standin",
      "revision": "NOT-DECIDED-HERE",
      "toolchain": {"clang": "NOT-DECIDED-HERE"},
      "host": {"cpu": "NOT-DECIDED-HERE", "os": "NOT-DECIDED-HERE"},
      "hw_source": "NOT-DECIDED-HERE"
    }
  }
}
```

### Walk-through

One call of the journaled HW tool `example.tool` (a placeholder, as in ADR-0016) with the request `{"run_id": "r1", "round": 3, "candidate": 2, "attempt": 1, "execution": 1, …}`, through either front.

| Moment | What is read, and what follows |
|---|---|
| The request is checked, the data root is asked, the lookup | As ADR-0015 and ADR-0016; `instance.json` is not read for the hw_profile. An ended or an open identity is answered here |
| No line: the selection | `runs/r1/instance.json` is read and checked; its `hw_profile.record` is the hw_profile of the call; the `accelerator` of that record selects the backend (`no_backend`, `not_offered` as ADR-0016) |
| The operation is called | The start line is appended; the operation is called with the request and that record; the end line is appended |
| The same request again | Answered in the lookup; the file is not read for the hw_profile |
| A request with `execution` 2 | The file is read again; nothing of the first call is used |
| `runs/r1/instance.json` is missing, unreadable, invalid by decision 2 (empty, partial, a `hw_profile` that breaks decision 3, …) or of another version | The hw_profile of `r1` cannot be had: no backend, no line. The kind is open (sub-question ④ of OD-18) |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A closed set of top-level members ("exactly the listed members", as a spec) | See decision 2: a new version per later record before a first run exists, and reading another version is OD-11. |
| 2 | Unknown members are an error only for an unknown *required* marker (a list of "must understand" names in the file) | A mechanism of its own for a case the version already covers. |
| 2 | No `schema_version` of its own; the source commit or the layout version says the schema | Neither has a member yet, and a version of the schema of this file is what NFR-7 ② asks of a persistent artefact. |
| 2 | `schema_version` is also the layout version stamp | It would decide what ADR-0004 decision 9 left to the instance schema and OD-11; the frame can be stated without it. |
| 2 | A fixed member order, as ADR-0012 | No rewrite, so no diff between two contents of the file. |
| 3 | The `spec.json` of an attempt | See decision 3. |
| 3 | (a) The key name only; the record is read from `db/<hw_profile_key>/hw_profile.json` at each call (`hilclaw.key_records.load_hw_profile` exists) | Every call would depend on the knowledge tree, a finished run would not hold the attributes it was started with once a stored one may change (OD-26), and a missing or damaged stored record would stop a run that had started. |
| 3 | (b) The record only, the key derived when needed | Works; the key beside it costs one derivation at validation and gives the join to `db/` and the form of a spec section. |
| 3 | (c) with "the record wins" or "the key wins" on a disagreement | A reader would go on with a file one half of which is wrong; ADR-0002 makes the same case invalid. |
| 3 | The stored record is also read and compared at each call | A second file per call and a rule for a difference of attributes, which OD-26 has not given (sub-question ⑱). |
| 3 | A member of `STATE.json` | That file is rewritten by the Round-Manager for the life of the run; what a run was started with belongs to the file written once. |
| 5 | An array of hw_profiles now | No input carries more than one, and each call would need a way to tell which. |

## Consequences

- **The code slice that can now be cut** (within the size cap, code mode): a module for `instance.json` — the validity of a content by decision 2 and 3, and the reader of the hw_profile of a run with the signature `hilclaw.hw_tool.tool_function` already takes, `hw_profile_of(data_root, run_id)`, over the path `layout.run_file(data_root, run_id, "instance.json")` — with its tests. It needs a JSON parser that reports a repeated member name, as `hilclaw/run_state.py` has, and can share the check of `hilclaw/spec.py` for the section. **Writing the file is not part of that slice**: it needs the answers to sub-questions ⑩ and ⑰ and belongs with the start of an instance; a test writes its own file.
- **Sentences of the code that then change**: in the docstring of `hilclaw/hw_tool.py`, "Where a run states its hw_profile is open (OD-18 sub-question 6), so this module reads no file for it and names none", and "no reader" in its last paragraph if the module comes to name one. The reader may stay a parameter; binding the real one is the task of the first HW tool.
- **What the conformance tests of P1-1 gain**: a run on disk whose `instance.json` selects the backend through both fronts without a test-only reader, and the situations of decision 4 produced by files. Their kind stays unpinned until sub-question ④ is answered.
- **Later records** add the other members one at a time under the version rule of decision 2. In a database `hw_profile.key` would become a column of the run row and the record a snapshot beside it (an illustration, as the table of ADR-0004 decision 9 is).
- **Not edited and now less exact** (follow-ups for the integrator): the `instance.json` row of the path table of ADR-0004 ("Fields: PLAN P1-8, OD-11"); ADR-0012 Boundaries ("all of `instance.json`"); ADR-0014 decision 7 as far as it lists the content of this file as open; ADR-0016 where it calls the place of sub-question ⑥ open (decisions 4 and 6, the Walk-through, Consequences, Boundaries); the situations listed with sub-question ④ in the Boundaries of ADR-0015, which those of decision 4 join; the `instance.json` line of the draft layout of #4. No sentence of UsageCases became false.
- **A-13 reading**: document mode; no code, dependency or schema file changes. This record is the first definition of a file that had no member, along the D6 route, as ADR-0005, ADR-0006 and ADR-0012 were for theirs; it changes no member, value list or validity rule of the key records, `spec.json`, `artifacts.json`, `events.ndjson` or `STATE.json` and adds no member to `hilclaw.config.json`.

## Boundaries (not decided here)

- **Owner-only or waiting for the owner (DRIVER §9)**: the objective and its form (#5 A-4, OD-1); gates and the autonomy mode (#5 A-5, OD-3); the coder model and the token budget (#5 A-8); the model input (#5 B-5, OD-9); datasets (#5 B-8); the tolerance vocabulary beyond the first case (#5 B-7); how a backend is reached (#5 B-2) and the simulator (#5 B-3); OD-25; C-6.
- **Every other member of `instance.json`** (PLAN P1-8): the tolerance members of the first case (the vocabulary is the owner's answer HQ-0004, [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md); the member is a later record's); budget axes, units and caps (OD-2, OD-19); N per round and its bounds (OD-21, OD-29); `n_max` ([ADR-0007](ADR-0007-od13-measurement-policy.md) decision 8); the op_signature of the run and whether one instance covers several values of M (ADR-0001 and ADR-0002 Boundaries); owner and project (ADR-0004 decision 9); references actually used (FR-14 ②, OD-12); any time member (sub-question ⑨ of OD-8).
- **The source commit member and the layout version stamp.** Both facts are fixed (#5 A-1 detail 3; ADR-0004 decision 9) and neither gets a name or a form here: the stamp is handed to the instance schema and OD-11, and the source commit raises which repository, which form and what a tree with local changes means. The frame is stated without either (decision 2).
- **The writer**: what writes `instance.json`, by which steps it comes to be on disk, and what a run directory without it means (sub-question ⑰; OD-23); when it is written in relation to the first `STATE.json` (sub-question ⑩ of OD-8); the form of `run_id`; how a branch or a continuation of a run with another target or budget relates to a file that is written once (sub-question ① of OD-8).
- **Rest of OD-18**: the kind of a call about a run that cannot be used (sub-question ④); which HW tools `cpu_standin` offers (⑦); the mock in a live session (⑧); the contract of any tool; hooks; the roster (OD-23); the isolation means.
- **Keys and onboarding**: any hw-side value of a record (`revision`, `host`, `toolchain`, `hw_source`); the onboarding procedure, the registration schema, whether a stored attribute may be updated, and a call about no run (OD-26); reading or migrating a file of another version (OD-11).
- **Sub-questions this record raises** (registered under OD-8): ⑰ What writes `instance.json` — ADR-0004 gives it to "The start of the instance, once" and names no component — and by which steps it comes to be under its final name (the once-only step of ADR-0014 decision 3, the replacement of ADR-0013, or another) so that a death of the writer leaves no partial file; and what a run directory that holds other files and not this one means (beside ⑩, which asks it of `STATE.json`; with OD-23). ⑱ How the record embedded in `instance.json` relates to the stored record of its key: whether the start of an instance requires the stored record to exist and takes the embedded one from it, what holds once the attributes of the two differ, and which of the two the `hw_profile.record` of a spec carries (with OD-26, OD-23).
- Any change to ADR-0001 to ADR-0017, to `hilclaw/`, to tests, to CI, to any settings file, or to the `HIL-Claw-data` repository; a JSON Schema file; any new external dependency.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-1, FR-6, FR-10, FR-13, FR-14 ④, NFR-1, NFR-2, NFR-6, NFR-7 ① ② ③, C-3; register rows OD-1, OD-2, OD-3, OD-8, OD-9, OD-11, OD-17, OD-18, OD-19, OD-23, OD-26.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-18](../OpenDecisionProposals.md#od-18), [OD-11](../OpenDecisionProposals.md#od-11), [OD-26](../OpenDecisionProposals.md#od-26); [UsageCases](../UsageCases.md) glossary "Loop instance", UC-0, UC-1, UC-6; [StandardScenarios](../StandardScenarios.md) S0, S1, S2, S3, S5, S10.
- [ADR-0001](ADR-0001-od4-key-schema.md) (decisions 1, 3, 5, 7; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 1, 2, 7); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 4, 5, 8, 9, 10); [ADR-0007](ADR-0007-od13-measurement-policy.md) (decision 8); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7); [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decisions 2, 6, 7; sub-questions ⑩, ⑫); [ADR-0013](ADR-0013-od8-state-file-replacement.md); [ADR-0014](ADR-0014-od8-whole-file-writes.md) (decisions 3, 7); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decisions 4, 7; sub-question ④); [ADR-0016](ADR-0016-od18-backend-frame.md) (decisions 2, 4, 6; sub-question ⑥); [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) (Consequences).
- #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, A-5, A-8, B-2, B-3, B-5, B-7, B-8.
- #4 body §2c, "합의 레이아웃 (현재안)", §4.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P1-8; `hilclaw/hw_tool.py`, `hilclaw/backends.py`, `hilclaw/key_records.py`, `hilclaw/keys.py`, `hilclaw/layout.py`, `hilclaw/run_state.py`, `hilclaw/spec.py`; tasks T-0042, T-0056, T-0064, T-0066.
