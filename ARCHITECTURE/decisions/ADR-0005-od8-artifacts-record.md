# ADR-0005: The blob record of `artifacts.json` (one part of the rest of OD-8)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): the content of `runs/<run_id>/artifacts.json` — the shape of the file and the members of one blob record. What stays open of OD-8: the isolation means (candidates ① and ②), the fields of every other file, the form of `run_id`, and the registered sub-questions (see Boundaries).
- It builds on decision 6 of [ADR-0004](ADR-0004-od8-data-plane-layout.md) (objection window until 2026-10-14) and on the `id.round` of [ADR-0002](ADR-0002-od6-codegen-spec.md) and the value types of [ADR-0001](ADR-0001-od4-key-schema.md) (windows until 2026-10-13). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- Fixed by the owner (C-3, #5 A-2): binaries are not in git; they live in the content-addressed store `blobs/sha256/<hh>/<hash>`, and git holds only `artifacts.json` with "hash, size, type, producing round, retention class". The retention class is a required field with the values `best` / `final` (permanent) and `intermediate` / `failed` (subject to GC after a grace period that starts when the run ends). The MVP records the class and builds no GC tool. A GC writes `gc_at` into the record of what it removed and commits that edit, so that history keeps "what was there and when it was deleted" (NFR-2). Principle of A-2: git holds knowledge, the store holds reproducible artefacts.
- ADR-0004 decision 6 fixed the place: one file per run, `runs/<run_id>/artifacts.json`, one record per blob the run produced, written by the tool layer together with the blob store; a file that needs a binary names it by hash. Decision 2: the file is at run level because a record changes after its round. It fixed no field.
- `hilclaw/cas.py` stores a blob and returns `BlobRef(digest, size)`: the SHA-256 of the content as 64 lowercase hexadecimal characters and the size in bytes. It writes no record. `hilclaw/layout.py` builds the path of the file and touches no file.
- The round is a non-negative integer, `0` being the bring-up round (ADR-0002). A persistent artefact carries a `schema_version` (NFR-7 ②). The history of the data repository is the audit record and is not rewritten (NFR-2). One small file is the entry point and no whole-directory scan is allowed (#4 §1). Nothing is pushed automatically (#5 A-3). P1 assumes a single run (C-2).
- No source says how a record is written down: member names and value types, the shape of the file, what `type` may hold, what identifies a record, and which changes a record may undergo. The record writer and validator of PLAN P1-6 need these.

## Decision

C-3 / #5 A-2, ADR-0004, ADR-0002 and `hilclaw.cas` are cited where a point follows from them. **Every choice below that cites no source is this record's own** — among them the shape of the file and the place of `schema_version`, the member names `artifacts` and `retention_class`, the closed set of members, the written form, the rule that the first production is kept and the error on a differing size, that the class may be replaced and has no default, the order of writing, and the conditions that raise the version.

### 1. Scope

This record fixes the content of `runs/<run_id>/artifacts.json`: the shape of the file and the members of one blob record. It fixes nothing of any other file, and nothing about when a blob is removed, pushed or fetched.

### 2. Shape of the file

- The file is one JSON object with exactly two members: `schema_version` (the integer `1`) and `artifacts` (an array of records, possibly empty). A record is a JSON object with exactly the members of decision 3; no member name occurs twice in an object.
- **Order**: a new record is appended at the end of the array; a record never moves. The order is the order of addition and carries no other meaning — a reader does not rely on `round` being sorted.
- A missing file and an empty array both mean "no blob recorded for this run" (ADR-0004 decision 1: nothing exists before something is written).
- **Written form** (NFR-2, line-wise diffs in the history): UTF-8 without a byte order mark, LF line ends, a final newline, each record on one line of its own, and its members in the order of the table of decision 3. An addition is then a diff of one added line at the end of the array (and the separator after the previous last record); an edit is a diff of the one line of that record. The exact whitespace is the writer's (the code task of PLAN P1-6), as long as it is the same on every write. A reader accepts any JSON text of this shape.
- **No scan** (#4 §1): every blob record of a run is in one file of known path; neither `blobs/` nor the round directories are walked to list them.

### 3. Members of a record

| Member | Type and form | Required | Source |
|---|---|---|---|
| `sha256` | string of exactly 64 lowercase hexadecimal characters: the SHA-256 of the content, the `digest` of `hilclaw.cas.BlobRef` unchanged | yes | C-3 "hash"; the member name and the bare form are this record's |
| `size` | *integer*: the size of the content in bytes; `0` is valid | yes | C-3 "size"; unit as `hilclaw.cas` |
| `type` | *name*: the kind of content (decision 5) | yes | C-3 "type"; the form is this record's |
| `round` | *integer*: the producing round, the `id.round` of ADR-0002 (`0` = bring-up) | yes | C-3 "생산 라운드"; ADR-0002 |
| `retention_class` | one of `best`, `final`, `intermediate`, `failed` | yes | C-3 / #5 A-2 (required field, the four values) |
| `gc_at` | *string*: the time at which a GC removed the blob from the store. Absent until then | no | C-3 / #5 A-2 ③; the type is this record's, the time form is open |

- *name*, *string* and *integer* are the types of ADR-0001 decision 1 (`[a-z][a-z0-9_]{0,31}`; 1 to 255 printable ASCII characters; 0 to 2^53 − 1). No member holds `null`; an absent `gc_at` is left out.
- **The algorithm is named by the member name**, as the store names it in its path (`blobs/sha256/`). Another algorithm would be another member and a new version (decision 9).
- **`gc_at`**: C-3 fixes that the member exists and what it means. Its time form is not fixed here: the MVP has no GC tool, so no MVP tool writes the member, and the first time stamp form of the data plane belongs to the schemas of PLAN P1-8 or to the GC design. A version 1 validator checks that a present `gc_at` is a *string* and nothing more.

### 4. Producing round

- `round` is the round of the run in whose work the blob was first stored for this run, given to the writer by its caller. It is the only member that says where a blob comes from.
- A record names **no candidate, attempt, role or tool**. C-3 lists the round only, and the direction a requirement needs — from an attempt to its binary — is already served by the file that uses the binary naming it by hash (ADR-0004 decision 6). Required candidate and attempt members would also not fit a blob that belongs to no attempt (a baseline that is not a candidate, OD-28). The reverse direction, from a record to the attempt, is narrowed to one round by `round` and not further (decision 10).

### 5. `type`

`type` says what kind of content the blob is, so that a reader can tell blobs apart without fetching them. No source gives its values. This record fixes **the form only** (a *name*) and **no list**: which binaries the tools produce is not decided (A-2 says "binaries"; the files and tools of each role are OD-23), so a closed list would be invented. A reader treats an unknown value as an unknown kind, not as an error. The vocabulary stays open (Boundaries).

### 6. Identity and duplicates

- **A record is identified by `sha256`; a value occurs at most once in a file.** The store keeps one blob per hash, and ADR-0004 decision 6 says one record per blob.
- When a run stores content that already has a record in its file, **no record is added and the existing one is not changed**: `round` stays the round of the first production, `type` stays the first one given, and the class given with the repeated add is not applied — changing the class is the edit of decision 7. The writer tells its caller that the record existed, and reports an error without writing if the given `size` differs from the recorded one (same hash, other size: the caller or the store is faulty).
- The same `sha256` may be recorded in the files of two runs. Each run's file is complete by itself (`runs/` can become a repository of its own — #5 A-1), and the two records may differ in every member but `sha256` and `size`.

### 7. Allowed changes

A record is written when the blob is stored (ADR-0004 decision 6), which is before the run can know whether the blob backs a `best` or a `final`. So the class must be able to change later, and a change is an edit of the record at run level (ADR-0004 decision 2), kept by the history.

| Change | Allowed |
|---|---|
| Add `gc_at` to a record that has none | yes (C-3) |
| Replace `retention_class` by another of the four values | yes |
| Change `sha256`, `size`, `type` or `round` | never |
| Remove a record, or move it | never — C-3 marks a removed blob by `gc_at`, not by deleting its record; the current file keeps saying what was there (NFR-2) |

- **The writer of a record is always given the class by its caller; there is no default.** Who assigns a class, when it changes and which transitions are legitimate is policy and is not decided here (OD-20, OD-29, OD-23).
- Whether a `gc_at` once written may be changed or removed (content stored again after a GC) is left to the GC design.

### 8. Record and store

- **Order of writing**: the blob is stored first, then the record is written. A failure between the two leaves a blob without a record, which is harmless; a record never precedes its blob.
- **What a record asserts**: that this run produced content with this hash and size, of this kind, in this round, that the blob was in the local store when the record was written, and how the run currently classes it. It becomes durable with the local commit that contains it (#5 A-3); who commits, and when, is not decided here.
- **What a reader may not conclude**: that the blob is in the store now — it may have been removed by a GC (`gc_at`), or never fetched into this checkout, and `hilclaw.cas.has_blob` and `verify_blob` answer that, not the record; that a missing blob without `gc_at` is damage; that a blob in the store without a record in this file is unused (another run may record it); or, from one record alone, that a blob may be removed (another run may class the same hash differently — a matter of the GC design).

### 9. Versioning

- `schema_version` is one integer for the file, starts at `1`, and stands at the top level, not in each record.
- It is raised when a member is added, removed or renamed, when the type, form or meaning of a member changes, or when the shape of the file, the identity rule or the allowed changes change. It is not raised by a new value of `type`, nor by a later record that fixes the time form of `gc_at` (reserved in decision 3).
- It is independent of the layout version of ADR-0004 decision 9, which changes with paths and file names and not with the content of a file.
- Reading a file of an older version, and editing one (a GC may edit the file of a run that ended long ago), is OD-11 and is not decided here.

### 10. Limits

- The record does not guarantee that a blob is present, intact or reachable from another machine.
- Nothing makes the store and the file change together: there is no atomicity between them beyond the order of decision 8, and none between two writers of one file (OD-17; P1 assumes one run, C-2). The file may therefore miss a blob that was stored.
- A record does not say which attempt, file or tool produced or uses the blob; finding that means reading the files of the round that name the hash.
- One `sha256` has one `type` and one `round` per run, those of its first production, even if the same content is produced again as another kind.
- `type` is not checked against a vocabulary, and nothing checks that the class given by a caller is right.

### Example

Synthetic values: the hashes are repeated digits and `example_kind` is not a proposed value of `type`; `TIME-FORM-NOT-DECIDED-HERE` stands for a time whose form is open.

```json
{
"schema_version": 1,
"artifacts": [
{"sha256": "1111111111111111111111111111111111111111111111111111111111111111", "size": 18432, "type": "example_kind", "round": 0, "retention_class": "intermediate"},
{"sha256": "2222222222222222222222222222222222222222222222222222222222222222", "size": 20480, "type": "example_kind", "round": 3, "retention_class": "best"},
{"sha256": "3333333333333333333333333333333333333333333333333333333333333333", "size": 0, "type": "example_kind", "round": 3, "retention_class": "failed", "gc_at": "TIME-FORM-NOT-DECIDED-HERE"}
]
}
```

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A map from hash to record | The hash is a member of the record in C-3; a map either repeats it or drops it. Sorted by hash, an addition lands in the middle of the file and the order of production is lost. |
| 2 | One record per line without an enclosing object (NDJSON) | The owner named the file `artifacts.json`; records are edited (`gc_at`), so the file is not an append-only log; a `schema_version` would need a line of its own kind. |
| 2 | `schema_version` in each record | Records of two versions in one file would decide part of OD-11. |
| 3 | A member `hash` with the bare digest | A reader of the record alone could not tell the algorithm. |
| 3 | `hash` as `sha256:<digest>`, or an object `{algorithm, digest}` | A second written form of the digest beside the one `hilclaw.cas` takes and returns, for an algorithm choice that the owner fixed in the store path. |
| 3 | A fixed time form for `gc_at` now (for example RFC 3339 in UTC) | It would set the time stamp form of the data plane ahead of the event and state schemas (PLAN P1-8) for a member that no MVP tool writes. |
| 3 | `gc_at` with its type left open as well (a string or a number) | A validator would have nothing to check, and a reader could not even tell how to parse the member. A string excludes a numeric time stamp; that much of the form is this record's choice. |
| 3 | An `ext` map, or unknown members allowed | An open record would let a "pushed" or "location" member in without a decision (#5 B-2). |
| 4 | Members `candidate` and `attempt` (or a path of the producing file) | Not in C-3; no requirement needs the reverse lookup today; they do not fit a blob outside any attempt. Kept as a sub-question. |
| 5 | A closed list of `type` values, or a media type | A list: no source gives one. A media type: nearly every binary would be `application/octet-stream`, which tells nothing apart. |
| 6 | One record per production (the same hash several times) | Contradicts "one record per blob"; a GC would have to set `gc_at` on several records for one removal, and the class of a blob would be ambiguous within a run. |
| 6 | Error when a known hash is added with another `type` | The same bytes can legitimately be two kinds (an empty file); failing the second production would fail the step that made it. |
| 7 | An immutable class, the record written only when the class is final | The record would be written long after the blob, so a blob could sit in the store unrecorded for a whole round; and `best` can change with every later round. |
| 8 | Record first, then blob | A failure in between leaves a record that asserts a blob that never existed. |

## Consequences

- `hilclaw/cas.py` and `hilclaw/layout.py` are consistent with this record and unchanged: `BlobRef.digest` and `BlobRef.size` are the values of `sha256` and `size`, and `layout.run_file(data_root, run_id, "artifacts.json")` is the path. The *name* and *integer* forms are those `hilclaw/keys.py` already checks.
- The next code task of PLAN P1-6 can write a module that validates a file against decisions 2 and 3, adds a record after `cas.put_*` (decisions 6 and 8) and applies the two allowed edits (decision 7). From then on, a change of what it accepts is a schema change of `artifacts` in the sense of CLAUDE.md A-13.
- The class is an argument of every call that adds a record. Until the class policy exists (OD-20, OD-29, OD-23), a caller has no rule for choosing it; the tool layer only records what it is given.
- In a database (ADR-0004 decision 9) the file becomes an artefact table keyed by (run, `sha256`).
- The sentence of C-3 is not edited. A more precise wording for the integrator: "`artifacts.json`(`sha256`·`size`·`type`·`round`·`retention_class`, GC 시 `gc_at` — ADR-0005)".

## Boundaries (not decided here)

- **GC** (C-3 follow-up; no OD is registered for it): the tool, when it runs, the grace period and where it is configured, what "run end" means for it, the time form of `gc_at` within a *string*, what happens to a record when its content is stored again after a GC, and how a hash recorded by several runs with different classes is treated.
- **`blob.push` / `blob.fetch`** (#5 B-2, #5 A-3): their meaning on one machine, their backend, and any "pushed" or "location" member of a record.
- **Which artefacts are blobs** beyond "binaries" (A-2), the vocabulary of `type`, and a list of producing tools (OD-23); whole-model binaries (C-6); datasets (#5 B-8).
- **Class policy**: who assigns a retention class, when and to what it changes (OD-20, OD-29, OD-23); `best.json` and how the knowledge tree refers to a blob (OD-20, OD-7).
- **Other files**: fields of `STATE.json`, `instance.json`, `events.ndjson` and the result files, and whether an event is logged for a blob (PLAN P1-8; OD-17, OD-11, OD-3, OD-13).
- Locking, concurrency and atomic writes (OD-17, C-2); the isolation means (rest of OD-8, OD-14, OD-18); who may write the file beyond "the tool layer" (OD-23); reading and migrating older versions (OD-11).
- **Owner-only (DRIVER §9)**: OD-25, OD-3, C-6, #5 B-2, #5 B-8.
- **Sub-questions this record raises** (registered under OD-8): the vocabulary of `type`; whether a record should name the candidate and attempt once the files that name blobs are defined.
- Code, tests, a JSON Schema file, CI, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-6, FR-10, FR-13, NFR-1, NFR-2, NFR-7 ②, C-2, C-3, C-6; register rows OD-3, OD-7, OD-8, OD-11, OD-13, OD-14, OD-17, OD-18, OD-20, OD-23, OD-25, OD-28, OD-29.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8); [StandardScenarios](../StandardScenarios.md) S8, S10; [UsageCases](../UsageCases.md) glossary "CAS", "데이터 plane", UC-E4.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; decision 1, value types); [ADR-0002](ADR-0002-od6-codegen-spec.md) (`id.round`); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 2, 6, 9, 10).
- #5 A-2 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5046307826 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items B-2, B-8 · #4 body §1.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-6, P1-8; `hilclaw/cas.py`, `hilclaw/layout.py`, `hilclaw/keys.py`; task T-0024.
