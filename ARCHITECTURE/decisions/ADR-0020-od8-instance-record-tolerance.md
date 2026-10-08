# ADR-0020: The `instance.json` of a run — the member that states the tolerance of the correctness check for the first case (one more part of the rest of OD-8)

## Status

- **Accepted on 2026-10-08** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Two kinds of content.** The **owner's decisions** are the answers (2) and (3) to HQ-0004 of 2026-10-08 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052377983): for the first case — `cpu_standin`, kind `gemm`, fp32, a C kernel — the tolerance is per-element `rtol` and `atol`, an instance states both, and there is no default. They are quoted, marked **owner**, and are not subject to the objection window below. **Everything else is this record's own design and has not been confirmed by the owner**: the name, the place and the form of the member, that a valid file may lack it, the validity of its values and how it is read.
- Closes **one more part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): of `runs/<run_id>/instance.json`, the one member in which a run states that tolerance. It gives a place to what [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) left unnamed ("no member of `instance.json` is named"). The register rows of OD-8, OD-5 and OD-16 keep their status wording, and nothing of OD-5 or OD-16 is closed or changed.
- What stays open: every other member of `instance.json`, what writes the file, every tolerance vocabulary beyond the first case (#5 B-7), the contract of every tool, the sub-question this record raises, and every item under Boundaries.
- It builds on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 4 and 10; objection window until 2026-10-14), on ADR-0017 (decisions 1, 5 and 6) and on [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 2, 3 and 6), both until 2026-10-15, and on [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7; until 2026-10-14). ADR-0003, [ADR-0016](ADR-0016-od18-backend-frame.md) and ADR-0019 are cited for a comparison or a consequence, not built on. If one of the records it builds on is reverted, this record is revisited with it.
- The owner is notified on issue #5. For the record's own choices the owner may object within 7 days of that notice; an objection creates a task that reverts them and the edits made with them.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- FR-9: "tolerance는 사용자가 instance 파라미터로 지정·변경한다"; the system does not choose how much accuracy is given up, and a candidate that would pass under a looser tolerance is only reported — adopting it is "사용자가 tolerance를 바꾼 새 instance".
- ADR-0017 fixed the comparison of the first case with the owner's answer and said where its two values come from: they "are parameters of the run, given by the caller from the instance" (decision 5), with no default (decision 6). It named no place: "An instance must state `rtol` and `atol`; no member of `instance.json` is named" (Consequences).
- ADR-0018 gave the file its frame and one member, `hw_profile`, left "the tolerance members of the first case" to a later record (Boundaries) and said how the file grows: later records "add the other members one at a time under the version rule of decision 2", each of which "chooses between a member that may be absent from a valid file and a new version".
- The code takes the two values as arguments and reads them from nowhere: `hilclaw.harness.verification.run_verification(..., rtol, atol)` and `hilclaw.harness.verification_arrays.check_tolerance(rtol, atol)`. `hilclaw/instance.py` defines `schema_version` and `hw_profile` only; it hands back every other top-level member uninterpreted, whatever its name and value.
- Fixed and not re-decided: FR-9; the owner's answer; ADR-0004 (`instance.json` is "What the instance was started with", written by "The start of the instance, once", and the tree enforces none of it — decision 10); ADR-0017 decisions 5 and 6; ADR-0018 decisions 2 and 3; that nothing is kept between calls (ADR-0010 decision 7).

## Decision

A sentence marked **owner** renders the HQ-0004 answer and quotes it. A value is **cited** when another source is named with it. Every other value is **this record's own** choice — among them the name `tolerance`, the object form, that the member may be absent, the JSON form of the two values, that a present and invalid member makes the file invalid, and the list of limits.

### 1. Scope

This record fixes one thing of `runs/<run_id>/instance.json`: the member in which a run states the tolerance of its correctness check, **for the vocabulary of the first case only**. Nothing else of the file is fixed and nothing of any other file. **A file that holds what ADR-0018 and this record define is still not a complete instance record, and no run can be started from it alone** (ADR-0018 decision 1).

### 2. The member

- **Owner** (HQ-0004 (2)): the tolerance of the first case is "per-element `rtol` and `atol`, both instance parameters (FR-9); pass iff |out − ref| ≤ atol + rtol·|ref| for every element of the output; any NaN or infinity in the output fails." And of what it does not answer: "Vendor golden outputs, downstream-metric thresholds, user-defined checks and other dtypes stay open under B-7." The question was asked "for the first case only" (HQ-0004, the question).
- **The member is `tolerance`**, a top-level member (FR-9's word), an object with **exactly** the two members below. The object is **closed**: a `tolerance` that is not an object, lacks one of the two or holds any other member breaks this decision.

| Member | Type and form |
|---|---|
| `tolerance.rtol` | a JSON number, valid by decision 4 |
| `tolerance.atol` | a JSON number, valid by decision 4 |

- **What it states**: the `rtol` and the `atol` of the owner's predicate, for a correctness check of the run. **This record gives the member that meaning for a run of the first case and gives it no meaning for any other run.** The file does not say whether a run is of the first case — its `hw_profile` names the accelerator, and no member states the kind, the dtype or the kernel language (ADR-0018 Boundaries) — so a validator of the file cannot check it and does not. What a `tolerance` member means in the file of a run of another case, and whether such a run may state one in this form, is not decided (#5 B-7).
- **Why one closed object.** The owner's "must state both" becomes a property of the form: a member that is present holds both values, and a file with one of them is invalid. Two top-level members could be half present, since each may be absent or misspelt by itself (decision 3).
- **How a reader tells this vocabulary from another.** In version 1 a `tolerance` member has this form, and the only meaning a record gives it is the one above, for a run of the first case. A later record that gives the member another form or another meaning changes "its type, form or meaning" and so raises the version (cited: ADR-0018 decision 2); a version 1 reader then reports an unsupported version and interprets nothing. A later record that states another vocabulary in another top-level member applies the same rule to its member and judges there whether a version 1 reader may pass over it. Either way a reader of this record never takes another vocabulary for this one. **No name, value or form is given here for any other vocabulary**, and the name `tolerance` is not claimed to be the general one.
- **In version 1 a run states at most one tolerance**: the member is one object. FR-9 makes the tolerance a parameter of the instance and a changed one a new instance (decision 6). Whether a run ever needs more than one — per kind, per dtype or otherwise — is not decided (#5 B-7); a record that admits it changes the member and raises the version.

### 3. A file without the member; the version

- **The member may be absent from a valid file, and `schema_version` stays `1`.** This is the first of the two choices ADR-0018 decision 2 leaves to the record of a member: "A later record that defines a top-level member which may be absent and may be passed over does not raise it." A version 1 reader may pass over the member: the readers of today read the file for the `hw_profile` of a run only, and a reader that needs the tolerance is one that knows the member.
- **A member that is present must be valid.** A file whose `tolerance` breaks decision 2 or decision 4 is **invalid**, in the sense of ADR-0018 decision 2: a reader of this record reports it, uses no member of it — not its `hw_profile` either — and repairs nothing.
- **Owner** (HQ-0004 (3)), on defaults: "none. An instance must state both `rtol` and `atol`; the harness has no default value". With an absent member allowed, that reads as follows. A valid file without the member **states no tolerance**. A reader of this record that is asked for the tolerance of such a run finds that none is stated and has no value to give: it **never substitutes one**. A valid file is therefore still "not thereby enough to start a run" (ADR-0018 decision 2), and by this record it gives a correctness check of the run no tolerance.
- **No path yields a default.** A reader of this record has a tolerance for a run only when the file of that run is valid, is of version 1 and holds the member. A missing file, a file that cannot be read, an invalid file, a file of another version and a valid file without the member each leave it without a value, and nothing in this record supplies one.
- **Why not a required member and version 2.** Every file and every reader of today would be of another version before a first run exists, and reading another version is OD-11 — the reason ADR-0018 gave for the open top level. And a required member would make every instance of that version, whatever its case, state the vocabulary the owner fixed for the first case only.
- **The cost**: validity does not show that a tolerance is stated. A file without the member and a file whose member name is misspelt look alike to a version 1 reader — both state none (decision 7). The owner's "must" binds whatever starts an instance of the first case; where that is checked is not decided (sub-question ⑲).

### 4. The values

- **Type**: each of `rtol` and `atol` is a JSON number in any form JSON has, with or without a fraction or an exponent (`0`, `0.001`, `1e-5`). `true`, `false`, `null`, a string, an array and an object are none. JSON does not tell an integer from another number, and `check_tolerance` accepts an `int` beside a `float`; a rule that accepted `0.0` and refused `0` would be about spelling only. The forms of ADR-0001 decision 1 (*name*, *string*, *integer*; "no float") are rules for key fields: this member is no key field and enters no key.
- **Value**: the number is read as a binary64 value, the type the comparison is evaluated in (cited: ADR-0017 decision 5, "evaluated in float64"). It is valid when it is **finite and not negative** (cited: ADR-0017 decision 5, "a finite number that is not negative"; `check_tolerance`). Zero is valid for either and for both (cited: the same rule; ADR-0017's remark on `atol` = 0 is an observation and no rule). A zero with a minus sign is zero: `-0`, `-0.0`, and a negative literal whose binary64 value is that zero (`-1e-999`). **No upper bound and no relation between the two values is added**: ADR-0017 has none and no fixed input gives one.
- **A literal that binary64 does not hold.** The value is the binary64 number the reader arrives at — with the JSON parser of the frame, the parsed number converted to binary64 (an integer literal is parsed as an exact integer first). A literal for which that is no finite number (`1e999`, or an integer literal of that size) is invalid; it is never read as an infinity and accepted. A positive literal for which that number is zero (`1e-999`) is valid as zero (decision 7).

### 5. How the tolerance of a run is read

- **For a run of the first case, the tolerance that decides the verdict of a correctness check of the run — pass or fail, the gate of FR-9 — is the one stated in this member of the file of that run**, `runs/<run_id>/instance.json` below the data root in use. A reader of this record reads the file as a whole, which must be valid (ADR-0018 decision 2), and **nothing is kept between calls** (cited: ADR-0010 decision 7; ADR-0018 decision 4): a later call reads the file again. How often one call reads the file, and whether it reads it once for several members, is that call's contract. So the tolerance of a run is the same at every call **as long as the calls are given the same data root, run the same source, and the file is not changed** (decision 7).
- **No other source stands in for it or overrides it in that verdict**: no default (**owner**), no value kept from an earlier call, and no value carried by a request. The last follows from the fixed inputs and is stated as a property a later contract must respect: the tolerance is set by the user as an instance parameter and "얼마나 잃을지를 시스템이 고르지 않는다" (FR-9), and the caller gives it "from the instance" (ADR-0017 decision 5). A check about a run whose verdict took its tolerance from the request would let the calling agent loosen the gate FR-9 calls a hard floor — the reasoning by which ADR-0016 decision 4 keeps the hw_profile of a call out of the request. Which members a request has is the tool's contract; this record says only where the value that decides the verdict comes from. **It says nothing of an evaluation that decides no verdict**: FR-9 also has the system report a candidate that would pass under a looser tolerance, and how such a candidate is found — a second evaluation, a returned deviation or otherwise — is not decided (Boundaries).
- **This is about a run.** A verification that is about no run — the calibration tests, which "pass their own values" (**owner**, HQ-0004 (3); [ADR-0003](ADR-0003-od16-harness-calibration.md) decision 7) — reads no file, and the harness keeps taking both values as arguments (ADR-0017 decision 9).
- **Not said here**: which tool or component reads the member, at which moment of a call, and what a call answers when the tolerance cannot be had (Boundaries).

### 6. A changed tolerance

FR-9 lets the user set and change the tolerance, and the file is written once (cited: ADR-0004). The two agree by FR-9's own words: a changed tolerance is "사용자가 tolerance를 바꾼 새 instance". Nothing rewrites this member, and for a run of the first case a reader of this record treats the member of the file of the run as the tolerance of that run for its whole life. How a new instance relates to an earlier run — a new `run_id`, a branch, a continuation — is not decided (OD-8 sub-question ①).

### 7. Limits

- **Whoever can write the file changes the gate of a run.** No access control exists and the tree does not enforce the single writer (cited: ADR-0004 decision 10); the hard floor of FR-9 is as strong as the protection of this file, which is the isolation means (OD-8, OD-14).
- **A file changed after the start** is read as it is at that read (cited: ADR-0018 decision 6), so two checks of one run can be made under two tolerances, and a validator of this file alone cannot tell. No result file records the tolerance a check used (Boundaries).
- **A misspelt name.** A top-level member that is not spelt `tolerance` is passed over (cited: ADR-0018 decision 2, the cost) and the file states no tolerance — never a default. A misspelt name inside the member makes the file invalid, since the object is closed.
- **Two processes, two sources** (cited: ADR-0018 decision 6): a source older than the code of this record passes over the member, so it takes as valid — and has the `hw_profile` of — a file whose `tolerance` a newer source refuses. This is the case ADR-0018 named for a rule added without raising the version.
- **The case is not checked**: the file does not say that the run is of the first case (decision 2).
- **A valid value is not thereby a sensible one.** Both values at zero are valid, and a conforming kernel can fail under them (cited: ADR-0017 decision 5); a very large value lets nearly every finite output pass; a positive literal whose binary64 value is zero is valid as zero (decision 4). Which tolerance is right is the user's (FR-9), and this record gives no advice.

### Example

The placeholders of the Example of ADR-0018 with the new member, so this is the shape of the member and **not a valid file** (`NOT-DECIDED-HERE` is no valid `hw_source`), and not a complete instance. **The two numbers are example values that show two literal forms; they are not default, recommended or typical values.**

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
  },
  "tolerance": {"rtol": 1e-4, "atol": 0.01}
}
```

### Walk-through

What a reader of this record finds when it is asked for the tolerance of the run `r1`, a run of the first case.

| `runs/r1/instance.json` | What the reader finds |
|---|---|
| Valid, version 1, with `"tolerance": {"rtol": 1e-4, "atol": 0.01}` | The tolerance of `r1`: those two values. Asked again in a later call, it reads the file again |
| Valid, version 1, without the member (or with `"tolerence": {…}`) | No tolerance is stated for `r1`. No value is substituted. The `hw_profile` of the run can still be had |
| `"tolerance": {"rtol": 1e-4}`, `{"rtol": -1, "atol": 0}`, `{"rtol": "1e-4", "atol": 0}`, `{"rtol": 1e999, "atol": 0}` or a third member | The file is invalid: no member of it is used, neither the tolerance nor the `hw_profile` |
| Missing, unreadable, or of another version | No tolerance can be had, as ADR-0018 has it for the `hw_profile` |
| The user wants `r1`'s kernel judged under another tolerance | A new instance with its own file (FR-9); the file of `r1` is not rewritten. How the two relate: OD-8 sub-question ① |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Two top-level members `rtol` and `atol` | Each could be absent or misspelt by itself, so "both" would need a rule across members; and two bare names at the top level read as the tolerance of every instance. |
| 2 | An object that also names its vocabulary (a member such as `kind` beside the two values) | It presumes that the vocabularies of #5 B-7 are alternatives of one member, told apart by one name — a shape of the answer the owner has not given — and it needs a rule for a name this reader does not know. The version rule already keeps a version 1 reader from misreading another vocabulary. |
| 2 | A name that carries the vocabulary (for example an `elementwise` object inside `tolerance`) | The same presumption, one level down. |
| 2 | An open object | A misspelt `atol` would leave a member with one value; the closed form reports it. |
| 3 | Required, with `schema_version` 2 | See decision 3. |
| 3 | Required without raising the version | Against ADR-0018 decision 2, which makes a further required top-level member a new version. |
| 3 | A present and invalid member leaves the file valid and counts as "not stated" | Two notions of validity for one file, and a reader that does not need the tolerance would go on with a run whose stated gate cannot be read; ADR-0018 has one rule — an invalid file is reported and no member of it is used. |
| 4 | Only numbers written with a fraction or an exponent | A rule about spelling; `check_tolerance` accepts an `int`. |
| 4 | Decimal strings, to keep the literal exact | The comparison is in binary64 anyway, and a string would need a grammar of its own. |
| 4 | An upper bound, or `atol` > 0 | No fixed input gives one; ADR-0017 states the risk of `atol` = 0 as an observation and adds no rule. |
| 5 | Leave open whether a request may carry the tolerance that decides the verdict | FR-9 and ADR-0017 decision 5 carry the answer; a contract that let a request set the gate would contradict both. |
| 5 | Say that no call about a run ever evaluates under another tolerance | More than the inputs carry: FR-9's report of a candidate that would pass under a looser tolerance may need one, and no record says how that candidate is found. |

## Consequences

- **The code slice that can now be cut** (within the size cap, code mode): in `hilclaw/instance.py`, the validity of the member by decisions 2 to 4 and a reader of the tolerance of a run beside `hw_profile_of`, with tests. The name and the return form of that reader, how "not stated" is told from a value, and whether the validity of the two values shares code with `check_tolerance` are the code task's. Writing the file is not part of the slice (ADR-0018 Consequences).
- **Sentences of the code that then change**: in the docstring of `hilclaw/instance.py`, "It defines no member besides the two and interprets none", "A number beyond the float range in a member not defined here is read as an infinity and is no error" (it stays true of the members not defined; this member is now defined), the order of the checks, and the description of `Instance.others`, in which a `tolerance` member is handed back today. Two cases of `tests/test_instance.py` (`test_the_top_level_is_open`) assert today that a content with `"tolerance": {"rel": "broken"}` or `"tolerance": 0.1` is valid; they change with the slice.
- **What the contract of `correctness.check` can then cite** (PLAN P1-1): where the tolerance that decides the verdict of a call about a run of the first case comes from, that nothing is kept between calls, that a valid file may state none and that no default exists. An invalid `instance.json` found at the selection of a HW tool is a situation of [ADR-0019](ADR-0019-od18-unusable-run-kind.md) — a file that is invalid by this record alone included. **That is this record's reading of ADR-0019**, whose Context ("Fixed and not re-decided") takes what makes the file invalid from ADR-0018 decision 2 and whose decision 3 gives a broken `hw_profile` as the example in its row; that record is not edited or extended here, and what a call answers for a tolerance that is not stated, or for the file read at another moment, is that contract's.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0018 decision 2 ("The file is invalid when … lacks `hw_profile` or holds one that breaks decision 3") and the list of situations of its decision 4 ("invalid by decision 2"), which a `tolerance` that breaks this record joins; ADR-0017 Consequences and Boundaries ("no member of `instance.json` is named"; "`instance.json`" among the files without fields); ADR-0018 Boundaries ("the tolerance members of the first case … the member is a later record's") and its Example ("no objective, tolerance, …"); the row of ADR-0019 decision 3 that lists what makes `instance.json` invalid; the parenthesis of FR-9, which names the vocabulary and not the member. No sentence of UsageCases became false.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The record adds one member that may be absent to a file whose frame says how later records add members (ADR-0018 decision 2), along the D6 route as ADR-0018 did; by that frame's own rule the version stays `1`. **The set of valid version 1 files becomes narrower without a new version**: a file that holds a `tolerance` breaking this record was valid by ADR-0018 alone and is invalid now — the case ADR-0018 decision 6 named ("If a later record adds a rule for a member without raising the version"); no such file exists in a data plane, since nothing writes the file yet. No member, value list or validity rule of `hw_profile`, of the key records or of `STATE.json`, `spec.json`, `artifacts.json` or `events.ndjson` changes.

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: every tolerance vocabulary beyond the first case — vendor golden outputs, downstream-metric thresholds, user-defined checks, other dtypes, other kinds, other backends (#5 B-7; rest of OD-5); any default (**owner**: none) or recommended value; the objective (#5 A-4, OD-1); gates and the autonomy mode (#5 A-5, OD-3); the coder model and the token budget (#5 A-8); the model input (#5 B-5, OD-9); datasets (#5 B-8); OD-25; C-6.
- **The contract of `correctness.check` and of every tool** (PLAN P1-1, OD-18): request and result members, `step` values, whether it is journaled, the moment of a call at which the file is read for the tolerance, and which tool-failure kind a call answers when the tolerance is not stated or the file is invalid at that moment (ADR-0019 Boundaries: "a frame file it reads at another moment"); the split between the harness and a backend (ADR-0016 decision 3); which HW tools `cpu_standin` offers and at which execution point its correctness check is called (OD-18 sub-question ⑦); how a candidate that would pass under a looser tolerance is found and reported (FR-9), and whether a call ever evaluates an output under a tolerance that decides no verdict.
- **Rest of OD-16**: `draws`, the seed and who draws it (sub-question ⑤); shapes outside the `op_signature` (①); whether non-finite or corner-case inputs are drawn (with #5 B-7).
- **Every other member of `instance.json`** (PLAN P1-8), none of which is named here: the list of ADR-0018 Boundaries without the tolerance of the first case, the source commit member and the layout version stamp included.
- **The spec and the result files**: whether the tolerance is shown to the coder or copied into a spec (ADR-0002 Boundaries; rest of OD-6); what a result file records of the tolerance a check used (`eval.json`: PLAN P1-8, OD-23).
- **The writer and other versions**: what writes `instance.json`, by which steps, and how a user's input reaches it (OD-8 sub-questions ⑩ and ⑰; OD-23; UC-1); reading or migrating a file of another version (OD-11); how a new instance with another tolerance relates to an earlier run (OD-8 sub-question ①).
- **Sub-question this record raises** (registered under OD-8): ⑲ Where it is checked that an instance of the first case states its tolerance, as the owner's answer requires — at the start of the instance, at the first correctness check or elsewhere — and what follows when it does not; the validity of the file does not check it (decision 3) (with ⑰, OD-23 and the contract of `correctness.check`).
- Any change to a member that exists (`schema_version`, `hw_profile`), to another data-plane file or to `hilclaw.config.json`; any change to ADR-0001 to ADR-0019, to `hilclaw/`, to tests, to CI, to any settings file, or to the `HIL-Claw-data` repository; a JSON Schema file; any new external dependency.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-1, FR-9, FR-10, FR-13, NFR-2, NFR-7 ②; register rows OD-5, OD-6, OD-8, OD-11, OD-16, OD-18, OD-23.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-5](../OpenDecisionProposals.md#od-5), [OD-16](../OpenDecisionProposals.md#od-16), [OD-11](../OpenDecisionProposals.md#od-11); [UsageCases](../UsageCases.md) UC-1, UC-2; [StandardScenarios](../StandardScenarios.md) S0, S1, S3, S7, S8, S10.
- [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1; record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (Boundaries); [ADR-0003](ADR-0003-od16-harness-calibration.md) (decision 7); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 4, 10); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7); [ADR-0016](ADR-0016-od18-backend-frame.md) (decisions 3, 4; sub-question ⑦); [ADR-0017](ADR-0017-od16-cpu-standin-verification-run.md) (decisions 1, 5, 6, 9; Consequences; Boundaries; sub-question ⑤); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 1, 2, 3, 4, 6; Example; Consequences; Boundaries; sub-question ⑰); [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (Context; decision 3; Boundaries).
- HQ-0004 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6052377983 · question https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6029803639 · #5 A-6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body item B-7.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P1-8; `hilclaw/instance.py`, `hilclaw/harness/verification.py`, `hilclaw/harness/verification_arrays.py` (`check_tolerance`), `hilclaw/run_state.py`; tasks T-0036, T-0062, T-0066, T-0067, T-0068, T-0071.
