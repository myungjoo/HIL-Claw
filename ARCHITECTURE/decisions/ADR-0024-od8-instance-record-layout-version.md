# ADR-0024: The `instance.json` of a run — how the file states the layout version of its run (one more part of the rest of OD-8)

## Status

- **Accepted on 2026-10-08** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Two kinds of content, and none of the owner's.** No sentence of the owner speaks of the layout version or of its stamp, and this record attributes nothing to the owner. **[ADR-0004](ADR-0004-od8-data-plane-layout.md)'s choices** (decision 9: the tree is layout version 1, what raises that version, that it is recorded per run in `instance.json`, that the path of that file is the same in every layout version) and **[ADR-0018](ADR-0018-od8-instance-record-hw-profile.md)'s choices** (decision 2: the frame of the file, its `schema_version`, what raises it, what a version 1 reader does with another one) were accepted under §9 and have not been confirmed by the owner; they are cited as theirs. **Everything else is this record's own design and has not been confirmed by the owner**: that the stamp follows from `schema_version` and is no member of its own, the pairing of schema version 1 with layout version 1, the clause added to what raises `schema_version`, what the stamp covers, and the list of limits.
- Closes **one more part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): the shape of the stamp, which ADR-0004 decision 9 handed "to the instance schema and to OD-11". This record takes the part that is a matter of the instance schema — in which way the file states the version — and **changes nothing of OD-11**: its register row keeps `제안됨`, none of its proposals is taken, and what a reader does with a run of another version stays there. The register row of OD-8 keeps its status wording.
- What stays open: every other member of `instance.json`, what writes the file, everything of OD-11 beyond its confirmed part, the sub-question this record raises, and every item under Boundaries.
- It builds on ADR-0004 (decisions 1, 9 and 10) and [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7), whose objection windows run until 2026-10-14, and on ADR-0018 (decisions 1, 2, 4 and 6), whose window runs until 2026-10-15. [ADR-0005](ADR-0005-od8-artifacts-record.md), [ADR-0006](ADR-0006-od8-events-log.md), [ADR-0012](ADR-0012-od8-runtime-state-file.md), [ADR-0016](ADR-0016-od18-backend-frame.md), [ADR-0019](ADR-0019-od18-unusable-run-kind.md), [ADR-0020](ADR-0020-od8-instance-record-tolerance.md), [ADR-0022](ADR-0022-od8-instance-record-source-commit.md) and [ADR-0023](ADR-0023-od8-instance-record-n-max.md) are cited for a reading or a comparison, not built on. If one of the records it builds on is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0004 decision 9: "This tree is **layout version 1**. The version is raised when a path, file name or number form fixed here changes; it is not raised when a file is added in a place this record leaves open." And: "The version is recorded **per run, in `instance.json`**: a finished run is not rewritten into a newer layout, because its history is its audit record (NFR-2), so runs of different versions can stand side by side. The path `runs/<run_id>/instance.json` is the same in every layout version: a reader finds the version there before it uses any other path of the run. The name of that stamp, and whether it is a field of its own or follows from a `schema_version`, belongs to the instance schema and to OD-11. `db/` needs no stamp of its own in version 1".
- ADR-0018 decision 2 gave the file its `schema_version` — "the version of the schema of this file" — and kept both shapes open: "**It is not, by this record, the layout version stamp** … neither answer is chosen or excluded — a later record may add a member, or add 'a change of the layout' to what raises this version." The same decision says what raises that version, and that for a `schema_version` other than `1` "a version 1 reader reports an unsupported version and interprets nothing (OD-11)".
- Of the three facts ADR-0004 put into the purpose of the file ("What the instance was started with; source commit (#5 A-1); layout version") this is the last one without a place. ADR-0012, ADR-0018, ADR-0020, ADR-0022 and ADR-0023 each leave "the layout version stamp" to a later record.
- The code holds the number, and nothing reads or writes a stamp as a stamp. `hilclaw/layout.py` has `LAYOUT_VERSION = 1`; no other module uses it and one test pins its value. That module builds every path of a run by formatting and "reads, writes, creates, lists and checks no file". `hilclaw/instance.py` requires `schema_version`, reports an integer other than `1` as an unsupported version before it looks at any other member, and hands a top-level member it does not define back uninterpreted — one case of `tests/test_instance.py` holds a `"layout_version": 99` that way.
- OD-11 is `제안됨`. Its confirmed part is the P1 harness version (#5 A-12). Its two proposals — a pin of the measurement contract with forced re-measurement; "P1 = `schema_version` 스탬프 기록까지", older versions and migration tools in P2, a resume that detects and reports a difference — are unconfirmed, and the second is not written into NFR-7 ② without the owner. **Neither is an input of this record.**
- Fixed and not re-decided: ADR-0004 decisions 1, 9 and 10; the frame of the file and its version rule (ADR-0018 decision 2); the members that exist; that the outcome of a call does not depend on state kept from an earlier call (ADR-0010 decision 7); NFR-7 ② and FR-6 as they stand.

## Decision

A statement is **cited** when a record is named with it. Every other statement is **this record's own** choice or reading — among them that no member is added, the pairing of decision 3, the clause on what raises `schema_version`, the reading of what the stamp covers, and the list of limits.

### 1. Scope

This record fixes one thing of `runs/<run_id>/instance.json`: how the file states the layout version of its run. Nothing else of the file is fixed and nothing of any other file. **A file that holds what ADR-0018, ADR-0020, ADR-0022, ADR-0023 and this record define is still not a complete instance record, and no run can be started from it alone** (ADR-0018 decision 1).

### 2. What the stamp states

- **The stamp states the layout version, in the sense of ADR-0004 decision 9, of the tree of this run**: the directory `runs/<run_id>/` and what is below it. It speaks of what that decision counts — paths, file names and number forms fixed by ADR-0004.
- **What a reader of this record may conclude** from a file that states layout version 1: that the run states that the paths below its directory are those ADR-0004 fixes for version 1 (the tree of its decision 1 and decisions 2 to 4).
- **What it may not conclude.**
  - **Nothing about the content of any file.** A file whose record defines a `schema_version` carries its own; for `artifacts.json`, `events.ndjson` and `STATE.json` it is "independent of the layout version" (cited: ADR-0005 decision 9, ADR-0006 decision 8, ADR-0012 decision 2). This record changes none of those sentences: only the `schema_version` of `instance.json` is tied to the layout version (decision 3).
  - **Not that the tree in fact has that layout, nor which of its files exist.** Nothing checks the tree against the stamp, and the tree "does not check the content of any file" (cited: ADR-0004 decision 10); a missing directory means "nothing yet" (cited: ADR-0004 decision 1).
  - **Nothing about the source** that wrote the run or that reads it. That is the member `source_commit`, for the start of the instance (cited: ADR-0022).
  - **Nothing about `db/` or `blobs/`.** Cited: "`db/` needs no stamp of its own in version 1" (ADR-0004 decision 9); that decision has no such sentence about `blobs/`. This record's reading: a stamp recorded per run speaks for the tree of that run, and runs of different versions may stand beside one `db/` and one `blobs/`, so the stamp of one run is not a statement about either. For the top level the fixed inputs carry one thing: the path `runs/<run_id>/instance.json` is the same in every layout version (cited). What states the layout of `db/`, of `blobs/` or of the rest of the top level, should a later layout version change a path there, is **not decided** (sub-question ㉒, second part).

### 3. The shape of the stamp

- **The stamp follows from `schema_version`. No member is added.** A valid file whose `schema_version` is `1` states layout version 1. The number is a rule of schema version 1, written in this record; it is not a constant of any source.
- **One clause is added to what raises the `schema_version` of this file**: a record that raises the layout version of ADR-0004 decision 9 raises this `schema_version` with it. This is the second of the two things ADR-0018 decision 2 says a later record may do ("add 'a change of the layout' to what raises this version"); ADR-0018 is not edited.
- **The pairing is stated per schema version, by a record.** A record that raises `schema_version` — for a change of the layout or for any other reason of ADR-0018 decision 2 — says which layout version the new schema version states. A reader of this record knows the pairing for version 1 only.
- **How "a reader finds the version there" (cited: ADR-0004 decision 9) is met, and for which file it is not**: a reader of this record reads the file at the path that is the same in every layout version and looks at its `schema_version`, a member every valid file must hold (cited: ADR-0018 decision 2). For a valid file of schema version 1 — the one version whose pairing it knows — it then has the layout version: no valid version 1 file is silent about the layout. For a file of another `schema_version` it finds an unsupported version and no layout version (decision 4); for such a file the sentence of ADR-0004 is not met by a reader of this record.
- **Why not a member of its own.** A version 1 reader passes over a member it does not know (cited: ADR-0018 decision 2), and the sources of today build the paths of version 1 without asking the file. A member that could state another layout version in a file of schema version 1 would be one "a reader that passes over the member would act wrongly" with — the case in which ADR-0018 decision 2 has the version raised. So within schema version 1 such a member could hold the value 1 only: for a valid file it would say what `schema_version` 1 then says already, and a change of the layout would change its form and raise `schema_version` all the same (cited: the same rule). The member would not undo the coupling; it would add a file that is silent, a name that can be misspelt and a second statement beside the first (Alternatives).
- **The cost: the two versions of this file are coupled.** ADR-0018 calls `schema_version` "the version of the schema of this file"; with this record it also stands for the layout of the run. Every change of the layout gives every reader of this file another `schema_version`, though no member rule changed; two schema versions may differ in the layout only; and a file cannot state the two apart. The other files keep their versions independent (decision 2). This file differs because ADR-0004 made it the place of the stamp, at the one path a layout version cannot change, so its version is read before anything else of the run is interpreted.
- **Why this adds to version 1 and does not raise it.** No member is added, removed or changed, and the set of valid version 1 files is the same as before. ADR-0018 decision 2 raises the version when the "meaning" of a member changes; this record reads its own clause as the addition that the same decision names as open to a later record, not as such a change: layout version 1 is the only layout version there is (cited: ADR-0004 decision 9), so no file of version 1 states by this record anything that it could have denied before, and a version 1 reader that does not know this record does nothing differently.

### 4. A file that states no layout version

- **There is no absent case and no invalid value of the stamp.** `schema_version` is required and must be an *integer* (cited: ADR-0018 decision 2); a file that lacks it or holds a value there that is not an *integer* is invalid by that decision. The question the records of the members had to answer — whether a present and invalid member makes the file invalid (ADR-0020 decision 3, ADR-0022 decision 5, ADR-0023 decision 4) — does not arise.
- **A reader of this record has the layout version of a run only when the file of that run is valid and its `schema_version` is `1`**, and then it is 1. A missing file, a file that cannot be read and an invalid file state none.
- **A file of another `schema_version`**: "a version 1 reader reports an unsupported version and interprets nothing (OD-11)" (cited: ADR-0018 decision 2). This record adds nothing to that sentence. Such a reader has no layout version for the run and **does not infer one**: neither that the layout differs — the version may have been raised for another reason — nor that it is the same.
- **Nothing stands in for a stamp that cannot be had**: not `hilclaw.layout.LAYOUT_VERSION` or any other constant of the source the reader runs from — that is the layout the reader's source builds, not what the run recorded (ADR-0023 decision 4 has the same for its bound) —, not the stamp of another run, and not a top-level member of a name such as `layout_version`, which no record defines and a version 1 reader passes over.
- **The layout version of a run depends on two things only**: the `schema_version` the run recorded in its file, and the pairing a record fixes for that version. It depends on no value of the source a reader runs from and on nothing else outside the file of the run.

### 5. How the layout version of a run is read

- **From the file of that run**, `runs/<run_id>/instance.json` below the data root in use; finding the file needs no knowledge of the layout version (cited: ADR-0004 decision 9). A reader of this record reads the file as a whole, which must be valid (cited: ADR-0018 decision 2), and **nothing is kept between calls** (cited: ADR-0010 decision 7; ADR-0018 decision 4): a later call reads the file again.
- **Today nothing reads or writes the stamp as a stamp** (Context). `hilclaw/instance.py` refuses a file of another `schema_version`, so each of its readers already gives nothing for such a run; it does so for the schema, and no code names the layout there. `hilclaw.layout.LAYOUT_VERSION` is compared with nothing.
- **An observation about ADR-0004's "before it uses any other path of the run".** The code of today does not read the file first: `hilclaw/layout.py` builds the paths of a run without reading any file, and a call of a journaled HW tool does its lookup before the selection reads `instance.json` (the order is cited: ADR-0016 decision 2), a lookup that reads `STATE.json` and `events.ndjson` (the code of today: `hilclaw/journaled_step.py`); a call answered in the lookup does not read `instance.json` for the hw_profile at all (cited: ADR-0018 decision 4). **This record changes no order of any call and decides nothing for a tool.** Whether the sentence of ADR-0004 binds the order in which a reader uses the files of a run is not decided (sub-question ㉒, first part).
- **Not said here**: which tool or component reads the stamp, at which moment, what it compares the stamp with, and what a call answers (Boundaries).

### 6. Limits

- **Whoever can write the file changes what it states.** No access control exists and the tree does not enforce the single writer (cited: ADR-0004 decision 10); a file changed after the start is read as it is at that read (cited: ADR-0018 decision 6).
- **Nothing checks the tree against the stamp** (decision 2).
- **The statement is made by the rule, not by an act of the writer.** Whatever writes `"schema_version": 1` states layout version 1, whether or not it looked at the tree it wrote; what writes the file is not decided (Boundaries).
- **A member that looks like a stamp is not one.** A valid version 1 file that also holds `"layout_version": 2` states layout version 1: the member is passed over (cited: ADR-0018 decision 2, the open top level). A person who reads the file may take it for the stamp.
- **Two processes, two sources** (cited: ADR-0010 decision 7; ADR-0018 decision 6) may hold two values of `LAYOUT_VERSION` and build two trees. The stamp of a run does not move with either, and nothing compares a source with it. And where one front takes a file as valid that the other refuses (cited: ADR-0018 decision 6), only one of them has the layout version of the run (decision 4).
- **A run directory without `instance.json` states nothing**: "no instance record was written for this `run_id`" (cited: ADR-0018 decision 2, "A missing file"). The other files of such a directory have no stated layout.
- **A version 1 reader cannot tell why a version is another one** (decision 4).

### Example

The Example of ADR-0023, unchanged: **the stamp is the member `schema_version`, and no member is added**. It is the shape and **not a valid file** (`NOT-DECIDED-HERE` is no valid `hw_source`), and not a complete instance.

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
  "tolerance": {"rtol": 1e-4, "atol": 0.01},
  "source_commit": "0123456789abcdef0123456789abcdef01234567",
  "n_max": 10
}
```

The `schema_version` inside `hw_profile.record` is that of the embedded record (cited: ADR-0018 decision 2) and states no layout.

### Walk-through

What a reader of this record finds when it is asked for the layout version of the run `r1`.

| `runs/r1/instance.json` | What the reader finds |
|---|---|
| Valid, with `"schema_version": 1` | `r1` states layout version 1. Asked again in a later call, it reads the file again |
| Valid, with `"schema_version": 1` and also `"layout_version": 2` | Layout version 1. The other member is passed over and is no stamp |
| A `schema_version` that is an *integer* other than `1` | An unsupported version; nothing is interpreted (ADR-0018 decision 2). No layout version is had for `r1`, and none is inferred |
| Invalid by ADR-0018, ADR-0020, ADR-0022 or ADR-0023 (empty, partial, no `schema_version` or one that is no *integer*, a member that breaks its rule) | The file is invalid: no member of it is used and it states no layout version, though it may hold `"schema_version": 1` |
| Missing or unreadable | No layout version is stated for `r1`. `LAYOUT_VERSION` of the reader's source is not used in its place |
| `runs/r2/instance.json`, below the same data root, is of another `schema_version` | Asked for `r1` the reader finds layout version 1; asked for `r2` it finds an unsupported version. Each from the file of the run it is asked about |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The stamp of a run also speaks for `db/` and `blobs/` | Both are shared by runs that may be of different versions, ADR-0004 gives `db/` no stamp in version 1, and no input says more. |
| 3 | (a) A top-level member of its own (for example `layout_version`), any *integer* a value | A version 1 reader that passes over it would use the paths of version 1 for a run that states another layout: by ADR-0018 decision 2 such a member raises the version. Every file and every reader of today would then be of another version before a first run exists, and reading another version is OD-11. |
| 3 | (a) The same member, the value 1 only, may be absent, `schema_version` stays `1` | See decision 3: it says nothing that `schema_version` 1 does not, and a later layout would raise `schema_version` anyway. It would add a valid file that states no layout — for which "a reader finds the version there" fails, and which every file written without knowledge of the member would be —, a name that can be misspelt, and a rule that calls a file stating another layout damaged, which is a statement about another layout version. |
| 3, 4 | (a) The same member, and an absent one **means** layout version 1 | Shape (b) with a second statement of the same fact beside it, which can then be damaged or misspelt. |
| 3 | (c) Both: a required member and the clause | A further required member is a new version (ADR-0018 decision 2), with the cost of the first row, for a statement made twice. |
| 3 | The layout follows from `source_commit` | That member may be absent and states the start only (ADR-0022 decisions 5 and 6), and a reader would need the source repository and a map from commits to layouts. |
| 3 | A stamp outside the file (a file at the top level, one version for the repository) | Rejected by ADR-0004 (Alternatives, points 1 and 9); not reopened. |
| 4 | A reader that has no stamp takes `LAYOUT_VERSION` of its own source | A constant of whichever source reads the file, not what the run recorded; two sources, two answers for one run. |
| 5 | Say that every reader, or every call of a tool, reads `instance.json` before any other file of the run | A rule for the order of a call, which is the contract of a tool (ADR-0016 decision 2); registered as sub-question ㉒. |

## Consequences

- **The code slice that can now be cut is small, and needs no rule of validity**: no member is added and no file changes from valid to invalid. In `hilclaw/instance.py`, the module docstring gains the record and the sentence that a file the module accepts states layout version 1 by its `schema_version`; "It reads no other version (OD-11)" stays. **Whether a function is needed at all is the code task's**: what this record carries for one is a reader beside the four that exist which, for a valid version 1 file, gives the layout version that schema version states — from a pairing keyed by the schema version, not from `hilclaw.layout.LAYOUT_VERSION` — and fails as `read` does otherwise. **Comparing the stamp with `LAYOUT_VERSION`, refusing a run on that ground and binding anything to a tool are not part of that slice.**
- **Sentences of the code that then change**: the first paragraph of the docstring of `hilclaw/instance.py` and its list of records; in `hilclaw/layout.py`, "What this module does not do" can say that the module reads no stamp and that `LAYOUT_VERSION` is the layout it builds and not what a run states. **Test cases**: none becomes wrong. `test_the_top_level_is_open` keeps its case `{"layout_version": 99, "run_id": "another"}`, which is now the case of decision 6 (a member that looks like a stamp); `test_layout_version_is_one` and the cases about another version (`test_another_version_is_reported_before_any_other_member`, `test_a_file_of_another_version`) stay as they are.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0004 decision 9 ("The name of that stamp, and whether it is a field of its own or follows from a `schema_version`, belongs to the instance schema and to OD-11") and the `instance.json` row of its path table; ADR-0018 decision 2 (the sentence "It is not, by this record, the layout version stamp", and the list "What raises the version", which gains a clause), its decision 4 ("such as the layout version stamp"), its Alternatives row "`schema_version` is also the layout version stamp" and its Boundaries; the Boundaries of ADR-0012, ADR-0020 and ADR-0023 and the Status of ADR-0022 and ADR-0023, which list the stamp as open; ADR-0022 Boundaries ("neither `source_commit` nor `schema_version` is said to serve as it"). The sentences of ADR-0005, ADR-0006 and ADR-0012 on the independence of their `schema_version` stay exact. No sentence of UsageCases became false.
- **What ADR-0019 then gives without a new rule**: its decision 3 already answers a call that meets an `instance.json` of another `schema_version`. This record adds no situation and no kind to it.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. No member is added to any file and no file changes its validity; the record adds one clause to what raises the `schema_version` of `instance.json`, which ADR-0018 decision 2 names as open to a later record, along the D6 route. No member, value list or validity rule of `hw_profile`, `tolerance`, `source_commit`, `n_max`, of the key records or of `STATE.json`, `spec.json`, `artifacts.json` or `events.ndjson` changes.

## Boundaries (not decided here)

- **Everything about another layout version or another `schema_version`** beyond the cited sentence of ADR-0018 decision 2: whether a reader reads, refuses, resumes or migrates such a run; a compatibility guarantee; a migration tool; a difference found at a resume (FR-6); which tool-failure kind a call answers (OD-18; ADR-0019 stands as it is). **No second layout version is defined**, and nothing changes what raises the layout version (ADR-0004 decision 9).
- **The rest of OD-11**: the scope of `schema_version` over further artefacts, the pin of the measurement contract and forced re-measurement, the P1 / P2 boundary of its second proposal, comparability across versions. **No sentence of NFR-7 ② is edited or read more narrowly.**
- **A stamp for `db/`, for `blobs/` or for the repository as a whole** (ADR-0004 decision 9 and its Alternatives; sub-question ㉒).
- **Every other member of `instance.json`** (PLAN P1-8), none of which is named here, and no object that would enclose one: the list of ADR-0023 Boundaries without the layout version stamp. Several wait for the owner.
- **The writer**: what writes `instance.json`, by which steps, and how it knows the layout of the tree it writes (OD-8 sub-questions ⑩, ⑰, ⑱, ⑳ and ㉑; OD-23).
- **Any tool's contract** (OD-18): which tool or component reads the stamp, the moment of a call, the order in which a call reads the files of a run, request and result members, any tool-failure kind.
- **Sub-question this record raises** (registered under OD-8): ㉒ Two parts. (i) Whether ADR-0004 decision 9's "a reader finds the version there before it uses any other path of the run" binds the order in which a reader uses the files of a run — today the paths are built without reading `instance.json`, and a journaled call reads `STATE.json` and `events.ndjson` before it — and, if it does, which reader checks the stamp, at which moment and against what. (ii) What states the layout of `db/`, of `blobs/` and of the rest of the top level once a layout version changes a path there (with the contracts of the tools — OD-18 — and OD-11).
- Any change to a member that exists, to another data-plane file; any change to ADR-0001 to ADR-0023, to `hilclaw/`, to tests, to CI, to `pyproject.toml`, to any settings file, or to the `HIL-Claw-data` repository; a JSON Schema file; any new external dependency.

## References

- [Requirements](../Requirements.md): the three-layer model (§0), FR-6, FR-13, NFR-2, NFR-7 ① ②; register rows OD-8, OD-11, OD-18, OD-23.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-11](../OpenDecisionProposals.md#od-11); [UsageCases](../UsageCases.md) UC-1, UC-4, UC-6; [StandardScenarios](../StandardScenarios.md) S0, S1, S1-b, S2, S3, S5, S6, S8, S10.
- [ADR-0001](ADR-0001-od4-key-schema.md) (decision 1, the *integer* form; record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1 to 4, 9, 10; Alternatives); [ADR-0005](ADR-0005-od8-artifacts-record.md) (decision 9), [ADR-0006](ADR-0006-od8-events-log.md) (decision 8) and [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decision 2; Boundaries); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 7); [ADR-0013](ADR-0013-od8-state-file-replacement.md) and [ADR-0014](ADR-0014-od8-whole-file-writes.md) ("Layout version: unchanged, version 1"); [ADR-0016](ADR-0016-od18-backend-frame.md) (decision 2); [ADR-0018](ADR-0018-od8-instance-record-hw-profile.md) (decisions 1, 2, 4, 6; Alternatives; Boundaries); [ADR-0019](ADR-0019-od18-unusable-run-kind.md) (decision 3); [ADR-0020](ADR-0020-od8-instance-record-tolerance.md) (decision 3); [ADR-0022](ADR-0022-od8-instance-record-source-commit.md) (decisions 5, 6); [ADR-0023](ADR-0023-od8-instance-record-n-max.md) (decision 4; Example; Boundaries).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 (the confirmed part of OD-11, cited in Context only).
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-8; `hilclaw/layout.py`, `hilclaw/instance.py`, `hilclaw/journaled_step.py`, `hilclaw/hw_tool.py`, `tests/test_layout.py`, `tests/test_instance.py`; tasks T-0021, T-0066, T-0067, T-0078, T-0079.
