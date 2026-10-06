# ADR-0006: Line format and envelope of `events.ndjson` (one part of the rest of OD-8)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): what one line of `runs/<run_id>/events.ndjson` is and which members every line carries. What stays open of OD-8: every event kind and every payload, the fields of `STATE.json`, `instance.json` and the result files, the isolation means (candidates ① and ②), the form of `run_id`, and the registered sub-questions (see Boundaries).
- **OD-17 is not closed and not changed.** No part of its proposal (`intent` / `result` events, idempotency key, budget fold, fold snapshots, lock and fencing, retry policy) is adopted or rejected here, and #8 M7 stays open.
- It builds on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (the path, the writer, decisions 2, 9 and 10; objection window until 2026-10-14), on the `id` integers of [ADR-0002](ADR-0002-od6-codegen-spec.md) and on the value types of [ADR-0001](ADR-0001-od4-key-schema.md) (windows until 2026-10-13). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- ADR-0004 fixed the place and the writer: one file per run, `runs/<run_id>/events.ndjson`, "events of the run in the order they happen; an expensive result is appended as soon as it exists", written by the tool layer, append only; appends happen at run level, also after a round has ended (decision 2). It fixed no field. The file name says NDJSON: newline-delimited JSON.
- Why the log exists (#4 §3b): a round contains the most expensive step, the board measurement (C-4). If the process dies after the measurement and before the commit of the round, the result must not be lost, so that a fresh turn can skip the finished substep (NFR-1). The journaling is done by the tool layer and not by an agent, because the return value of a sub-agent is lost when it dies (#4 roster revision, item 3).
- One small `STATE.json` is the entry point and no whole-directory scan is allowed (#4 §1). The local commit is the durability boundary; NFR-1 covers the death of a process, not the loss of the machine (#5 A-3). The history of the data repository is the audit record and is not rewritten (NFR-2). A persistent artefact carries a `schema_version` (NFR-7 ②), and components may be replaced at a round boundary of a running run (NFR-7 ①). P1 assumes a single run (C-2). The tree gives no concurrency control and no atomicity (ADR-0004 decision 10).
- `round` is a non-negative integer with `0` for the bring-up round, `candidate` and `attempt` are integers from 1 (ADR-0002). *name*, *string* and *integer* are the types of ADR-0001 decision 1.
- No source says how one event is written down: what a line is, which members every line has, what a reader does with a line that a dying process left half written, and what "append only" allows. The appender and the reader of PLAN P1-8 need these.

## Decision

ADR-0004, ADR-0002, ADR-0001, #4 and #5 A-3 are cited where a point follows from them. **Every choice below that cites no source is this record's own** — among them the member names, the closed set of members, the place of `schema_version`, the `time` member and its form, the absence of a header line and of a sequence member, what a reader accepts and what counts as damage, the treatment of a torn tail, and that the line of an expensive result carries the result.

### 1. Scope

This record fixes what one line of `runs/<run_id>/events.ndjson` is and the members every line carries (the **envelope**). It names **no event kind**, fixes no payload, and fixes nothing of any other file.

### 2. Line format

- The file is a sequence of **lines**. A line is one JSON **object** written as JSON text without a line break inside it, followed by one line feed (U+000A). The line feed ends the line: bytes after the last line feed are not a line (decision 6). The writer emits no carriage return: the line feed alone is the line end of NDJSON and this record's choice (it agrees with the provisional LF derivation of C-7).
- The encoding is UTF-8 without a byte order mark. No member name occurs twice in an object, the objects inside `data` included.
- There are **no blank lines and no header line**. Every line is an event, the first one included; every line is complete by itself and can be read without any other line.
- A missing file and an empty file both mean "no event recorded for this run". This follows ADR-0004 decision 1, which says it of a missing directory; that a missing and an empty file mean the same is this record's.
- The writer writes the members in the order of the table of decision 3 and nothing but the JSON text before the line feed. A reader accepts any order of members and the insignificant white space of JSON anywhere in the line, a carriage return before the line feed included; a line that holds white space only is a blank line and is not accepted. The length of a line is not limited.

### 3. Envelope

A line has exactly the members of this table; everything specific to a kind is inside `data`.

| Member | Type and form | Required | Source |
|---|---|---|---|
| `schema_version` | the *integer* `1`: the version of the line format and envelope (decision 8) | yes | NFR-7 ②; the place is this record's |
| `time` | string of exactly 20 characters `YYYY-MM-DDThh:mm:ssZ`: a date that exists in the Gregorian calendar with a year from `0001` to `9999`, `hh` 00-23, `mm` 00-59, `ss` 00-59 (no leap second), in UTC, read from the clock by the writer when it appends the line | yes | this record |
| `kind` | *name*: what kind of event the line records | yes | this record (the form is ADR-0001's) |
| `round` | *integer*: the `id.round` of ADR-0002 (`0` = bring-up) | no | ADR-0002; that a line names it is this record's |
| `candidate` | *integer* ≥ 1: the `id.candidate` of ADR-0002. Only together with `round` | no | as `round` |
| `attempt` | *integer* ≥ 1: the `id.attempt` of ADR-0002. Only together with `candidate` | no | as `round` |
| `data` | JSON object, possibly empty: the payload of the kind | yes | this record |

- **`kind`**: the form only and **no list of values**. Which kinds exist, and what the `data` of each holds, is left to the tasks that define them (Boundaries). A reader of the envelope treats an unknown value as an unknown kind, not as an error.
- **What a line is about**: a line with none of the three members concerns the run as a whole; with `round`, that round; with `candidate` or `attempt` in addition, that candidate or that attempt. These are the numbers every other artefact of the run is found by (ADR-0004 decision 3), so a reader can attribute a line to a round, a candidate or an attempt without knowing its kind. Which of them a given kind must carry belongs to the definition of the kind. No member holds `null`; an absent member is left out. The run is not named in a line: the path names it.
- **`time`** is in the envelope because the log is never rewritten (decision 5): a time that is not recorded when a line is appended cannot be added later, and commits are made per round (#5 A-3), so without it nothing tells when an event inside a round happened (NFR-2, FR-11). It is the writer's clock reading, not a statement of an agent. It is **not** the order (decision 4), and it is not a measurement: durations and the times a kind needs belong in `data`. The form is fixed **for this file only**; whether other files of the data plane (the `gc_at` of ADR-0005, the state and instance schemas) take the same form is not decided here.
- **`data`** is always present and always an object, so every line has the same shape. Its members are outside the envelope and outside `schema_version` (decision 8).

### 4. Order

- The order of the lines is the order in which they were appended. There is **no sequence member**: the position of a line says the same and cannot disagree with itself. A complete line keeps its position for the life of the file (decision 5), so its line number is stable. The envelope has no identifier member; whether and how a line refers to another line is left to the kinds (Boundaries).
- A reader may conclude that an earlier line was appended before a later one. It may **not** conclude that lines are grouped or sorted by `round` (appends happen after a round has ended — ADR-0004 decision 2), that `time` never decreases (a clock can be set back), or that nothing happened between two lines (decision 10). All of this holds for one appender at a time (C-2); the format does not order the appends of two concurrent writers (OD-17).

### 5. Append only

- The only change the file undergoes is that complete lines are added at its end. **A complete line is never edited, removed or reordered** (NFR-2).
- A later fact about an earlier event — a correction, a completion, a withdrawal — is a new line. What such a line looks like belongs to the kinds.
- The one exception is the removal of a torn tail (decision 6), which removes no line.

### 6. A torn tail

- A process can die in the middle of an append (NFR-1). The writer appends a line so that **the line feed is the last byte written**. A death during the append then leaves a prefix of the line without its line feed: a **torn tail**, the non-empty bytes after the last line feed of the file (the whole content, if there is none).
- **Reader**: a torn tail is not a line and not an event, whether or not its bytes happen to parse. The reader skips it and may report that it exists. An append that did not finish did not happen: the substep that produced the event counts as not journaled.
- **Writer**: before it appends, the writer looks at the end of the file. If there is a torn tail, it removes exactly those bytes and then appends. It reads no earlier line for this.
- **Damage**: a complete line is damaged when its bytes before the line feed are not valid UTF-8 or are not exactly one JSON text that is an object, when a member name occurs twice in any object of the line, or when it breaks decision 3. Damage is an error, the last line included — a dying appender cannot produce it. The reader reports it with its line number and repairs nothing; the writer does not look for it. What is recovered is what was committed, from the history of the data repository. Duplicate names are checked first, then the version, then the rest of decision 3: a complete line that is a JSON object whose `schema_version` is an *integer* other than `1` is not damage — a version 1 reader reports an unsupported version and does not interpret the line (decision 8). A line without the member, or with a value that is not an *integer*, is damage.
- **Committed content is never removed**: a file is committed only when it is empty or ends with a line feed, and the step that commits establishes this by the same removal. A torn tail is thereby never part of a commit, and the removal never touches anything that was committed. Which step commits is not decided here.

### 7. The log and the result files

- ADR-0004 gives each attempt `sim.json`, `board.json`, `profile.json` and `eval.json`. The log does not replace them: they stay the place where the result of a step is looked up by its tuple.
- For the event of an **expensive result**, this record fixes one property: **the line carries the result itself**, completely enough that the result file can be written from the line without running the step again. Binary content is named by hash, as in every file (ADR-0004 decision 6).
- Why it does not instead name where the result already is: the line is appended by the tool layer as soon as the result exists (#4 §3b; the draft layout of #4 adds "the log first"), and the result file is written by the measurement role (ADR-0004 decision 1), which may be held by an agent (OD-23) that dies before it writes. A line that names a file would then point at nothing, and the measurement would be lost — the case the log exists for. One appended line also needs no atomicity between two files (ADR-0004 decision 10).
- Which results count as expensive beyond the board measurement, the members of a result, who writes a result file from a line on resume, and what is done when a line and a file differ, are not decided here.

### 8. Versioning

- `schema_version` stands **in every line**, is one integer and starts at `1`. It covers the line format and the envelope: decisions 2 to 6. It is raised when an envelope member is added, removed or renamed, when the type, form or meaning of one changes, or when the line format, the append rule or the torn-tail rule changes. It is **not** raised by a new value of `kind`, nor by a change in the `data` of a kind; how such a change is told apart is left open (Boundaries).
- Why per line: the file is appended to for the whole life of a run and is never rewritten, while the tool layer may be replaced at a round boundary (NFR-7 ①). A version held once — in a first line or in `instance.json`, which is written once (ADR-0004) — could not be changed afterwards, so it would settle that a run never sees a newer envelope. A version per line settles nothing: whether a file may hold lines of two versions, and how a reader treats an older line, is OD-11.
- It is independent of the layout version of ADR-0004 decision 9, which changes with paths and file names and not with the content of a file.

### 9. Room for OD-17

The registered proposal of OD-17 is neither adopted nor rejected. The envelope does not exclude it: an `intent` and a `result` event can be two kinds or two payloads of one kind; an idempotency key fits in `data`, or becomes an envelope member with a new version; a fold reads lines in their order, and because every line is complete by itself (no header, version per line) a reader can start at any line start, which a fold snapshot with a replayed tail would need. Whether any of this is done, and the resolution of #8 M7, stays with OD-17. Nothing in this record requires the whole log to be read: the writer looks at the end of the file only, and how a resumed turn finds a line is not decided here.

### 10. Durability and limits

- **What an appended line guarantees**: once the append has returned, the line survives the death of the appending process and of the agent that asked for it (NFR-1; #5 A-3: process death and compaction). It does **not** survive the loss of the machine or of the working tree before the next commit, and after the commit only as far as the user pushes (#5 A-3). Whether the writer also asks the operating system to flush is left to the code task; this record claims nothing beyond process death.
- **No concurrency control**: the format assumes one appender at a time (C-2). Two concurrent writers can interleave bytes or remove each other's unfinished append; the lock is OD-17.
- **No atomicity** between a line and a result file, `STATE.json`, `artifacts.json` or the blob store.
- **No completeness**: the log holds what was appended. A missing line does not show that something did not happen, and the envelope does not check a line against the round directories, the kind's payload rules or the existence of the round, candidate or attempt it names.

### Example

Synthetic values. `example_kind` and `other_example_kind` are placeholders and not proposed kinds; `example_member` is not a proposed payload member.

```json
{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "example_kind", "data": {}}
{"schema_version": 1, "time": "2026-01-01T00:00:05Z", "kind": "example_kind", "round": 0, "data": {"example_member": 1}}
{"schema_version": 1, "time": "2026-01-01T00:07:30Z", "kind": "other_example_kind", "round": 3, "candidate": 2, "attempt": 1, "data": {"example_member": "x"}}
```

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A header line (version, run) before the events | A second kind of line; every reader would have to treat line 1 differently, and a reader that starts in the middle would have no version (decision 8). |
| 2 | A JSON array, or one object holding an array (as `artifacts.json`) | An append would rewrite the end of the file, and a torn write would make the whole file unparsable instead of one tail. The file name says NDJSON. |
| 2 | Any JSON value per line (arrays, scalars) | There would be no place for common members. |
| 3 | No `time`; each kind carries its own | Every kind would choose a form again, and a line of an unknown kind could not be placed in time at all. |
| 3 | `time` as a number (epoch seconds), with fractions, or with a zone offset | A number is not readable in a diff or an audit; fractions and offsets give several written forms of one instant, and a precise duration is a measurement that belongs in `data`. |
| 3 | An object `id` or `about` holding `round`, `candidate`, `attempt` (as the spec of ADR-0002) | The `id` of a spec has further members that mean nothing here; three optional members are flatter and say the same. |
| 3 | A `run_id` member | The path already names the run; a second statement could disagree with it. |
| 3 | Unknown members allowed beside `data`, or no `data` (payload members at the top level) | A payload member could collide with a later envelope member, and a reader could not tell the envelope from the payload without knowing the kind. |
| 3 | `data` optional | Two shapes of a line for no gain; `{}` says "nothing" as well. |
| 3 | The name `type` instead of `kind` | A payload may name a blob, whose record has a `type` (ADR-0005); one word would have two meanings in one line. |
| 4 | A sequence member | It repeats the position, can disagree with it, and makes the writer read the last line before every append. |
| 6 | The writer ends a torn tail with a line feed and goes on | Leaves a damaged line in the middle of the file for ever; a reader could no longer tell it from real damage. |
| 6 | A torn tail is an error that stops the run | The death of a process in mid-append is the expected case of NFR-1, not damage. |
| 6 | Accept an unterminated tail that parses | Two rules for one situation, for one byte of difference; "appended" would no longer mean "ended by a line feed". |
| 7 | The line names the result file instead of carrying the result | See decision 7: the file may not exist yet, and nothing makes the two writes atomic. |
| 8 | `schema_version` in a first line or in `instance.json` | See decision 8. `instance.json` is also another file, whose fields are not fixed. |

## Consequences

- `hilclaw/layout.py` is consistent with this record and unchanged: `layout.run_file(data_root, run_id, "events.ndjson")` is the path. The *name* and *integer* forms are those `hilclaw/keys.py` already checks.
- The next code task of PLAN P1-8 can write a module that checks a line against decision 3, appends a line (decisions 2, 5, 6: tail check, line feed last) and reads a file (decision 6: complete lines, torn tail skipped, damage and unsupported version reported). It needs nothing else from the issues.
- A task that defines a kind states its name, which of `round`, `candidate` and `attempt` it carries, and its `data`. The task that defines the event of an expensive result has to meet decision 7; such a line can be long.
- The step that commits the data repository has to remove a torn tail first (decision 6). That step does not exist yet; its task takes this as an input.
- The row of `events.ndjson` in the path table of ADR-0004 says "Fields: PLAN P1-8, OD-17"; the envelope part of it is this record. ADR-0004 is not edited.
- In a database (ADR-0004 decision 9) the file becomes an append-only event table keyed by (run, line number), with the envelope members as columns and `data` as the payload.
- No body of an FR, NFR or C row is edited, and none needs a more precise wording because of this record.

## Boundaries (not decided here)

- **Event kinds and payloads**: every value of `kind`, any list of kinds, the `data` of each kind, which of the three numbers a kind requires, how a line refers to an earlier line, and which results are "expensive" (PLAN P1-1, P1-3, P1-8 and their code tasks; OD-13, OD-10, OD-23).
- **OD-17**, whole: `intent` / `result` pairing, the idempotency key, the budget fold, fold snapshots, the resolution of #8 M7, the lock and fencing, the retry policy. Budget enforcement and the token ledger (OD-19, NFR-5).
- **Gates**: gate events and anything else about gates (OD-3 / #5 A-5 — owner-only).
- **Who appends**: which tool or hook performs the append, MCP versus CLI (OD-18); which agent may cause one (OD-23); the isolation means (rest of OD-8, OD-14).
- **Other files**: the fields of `STATE.json` — the `phase` markers of #4 §3b and how a resumed turn uses the log included —, of `instance.json` and of the per-attempt result files (PLAN P1-8; OD-17, OD-11, OD-20, OD-13); whether an event is logged for a blob.
- Reading or migrating a line of another version, and whether one file may hold two versions (OD-11).
- Promotion of events to `db/`, rotation and size limits of the log, the commit and push cadence beyond #5 A-3 and which step commits, notifications (OD-27).
- **Owner-only (DRIVER §9)**: OD-3, OD-25, C-6, the #5 A and B items.
- **Sub-questions this record raises** (registered under OD-8): the vocabulary of `kind` and how a change in the `data` of a kind is told apart, since `schema_version` covers the envelope only (with OD-11, OD-23); whether the time form of this file is taken for the other times of the data plane (`gc_at` of ADR-0005, the state and instance schemas).
- Code, tests, a JSON Schema file, CI, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-1, FR-3, FR-6, FR-9, FR-10, FR-11, FR-13, NFR-1, NFR-2, NFR-5, NFR-7 ① ②, C-2, C-4, C-7; register rows OD-3, OD-8, OD-10, OD-11, OD-13, OD-14, OD-17, OD-18, OD-19, OD-20, OD-23, OD-25, OD-27.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-17](../OpenDecisionProposals.md#od-17), [OD-18](../OpenDecisionProposals.md#od-18), [OD-11](../OpenDecisionProposals.md#od-11); [StandardScenarios](../StandardScenarios.md) S2, S3; [UsageCases](../UsageCases.md) UC-3, UC-4.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; decision 1, value types; decision 6); [ADR-0002](ADR-0002-od6-codegen-spec.md) (`id.round`, `id.candidate`, `id.attempt`); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 2, 3, 6, 9, 10); [ADR-0005](ADR-0005-od8-artifacts-record.md) (the sibling run-level file; `gc_at`).
- #4 body §1, §2e, §3b, §3c, "합의 레이아웃 (현재안)", §4; roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; the durability proposals https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800 ; candidate ① https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139876430 ; #8 M7.
- #5 A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body item A-5.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P1-3, P1-8; `hilclaw/layout.py`, `hilclaw/keys.py`, `hilclaw/artifacts.py`; task T-0026.
