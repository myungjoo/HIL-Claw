# ADR-0012: The runtime `STATE.json` of a run — the file, the round pointer and the stored spend view (one part of the rest of OD-8)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of the rest of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): of `runs/<run_id>/STATE.json`, the file as a whole, the member that says which round the run is at, and the stored form of the spend view of [ADR-0011](ADR-0011-od17-journal-and-spend.md).
- What stays open of OD-8: every other member of `STATE.json` (gate status, `best_ref`, the lock, `phase`, `next_action` — see Boundaries), `instance.json`, the result files of an attempt, the event kinds and payloads, the isolation means, the form of `run_id`, and the registered sub-questions. OD-17 is not changed: this record gives the form that ADR-0011 decision 6 left to PLAN P1-8 and nothing else of it.
- It builds on ADR-0011 (decisions 1, 3, 6 and 7), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (the path, the writer, decisions 2, 9 and 10) and [ADR-0006](ADR-0006-od8-events-log.md) (the envelope numbers, lines and positions), whose objection windows run until 2026-10-14, and on the `id.round` of [ADR-0002](ADR-0002-od6-codegen-spec.md) and the value types of [ADR-0001](ADR-0001-od4-key-schema.md) (until 2026-10-13). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of ADR-0001.

## Context

- Agreed in #4 and taken as fixed. §1: every turn starts with a clear context; one small `STATE.json` is the entry point (current round, `best_ref`, `next_action`, `budget_spent`, gate status), only artefacts it refers to are loaded, and a whole-directory scan is forbidden. §3: turn ≡ round. §3c: at the end of a round `STATE.json` is updated and the commit of the round takes it. The draft layout names `cur_round`, `best_ref`, `next_action`, `budget_spent`, `gate_status`, `phase` and `lock{owner, heartbeat}`; it is a draft.
- ADR-0004 fixed the path, one file per run, that it is mutable and that only the Round-Manager writes it (#4 roster revision); the layout version is in `instance.json`; which rounds exist is known from `STATE.json` or from listing one directory of known path (decision 3); the tree gives no concurrency control and no atomicity (decision 10). It fixed no field.
- ADR-0011 decision 6 fixed what `budget_spent` is for amounts accounted through the log — the stored spend view of a prefix of `events.ndjson`: totals per axis, the position (the number of complete lines folded) and the open steps — and when it moves: empty at position 0 when a run starts, taken in the write that ends a round, not moved in between. It left to PLAN P1-8 the form of these members and whether the byte offset of the position is stored. An identity is the envelope numbers of a line with `step` and `execution` (decision 3); an amount is a non-negative *integer* per axis *name* (decision 7).
- `hilclaw.journal` holds a view in memory as `SpendView(totals, position, open_steps)`, with the open steps as a set of identities. Its totals are exact sums and can exceed the *integer* range of ADR-0001 (task T-0041).
- `round` is a non-negative integer, `0` being the bring-up round (ADR-0002). A persistent artefact carries a `schema_version` (NFR-7 ②), and components may be replaced at a round boundary of a running run (NFR-7 ①). The local commit is the durability boundary (#5 A-3). P1 assumes one run (C-2).
- Five of the seven members of the draft hang on decisions that are open: gate status on OD-3 / #5 A-5 (owner-only), `best_ref` on OD-20, the lock on the rest of OD-17, `phase` on OD-29 and OD-23 (its granularity under Best-of-N), `next_action` on OD-23. Without the other two, no validator of the file can be written, and the reader of the log that starts at a position does not know its argument.

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice — among them the text form, the place of `schema_version` and what raises it, the rule for members not defined here, the name `round` and what it points at, the member names and forms inside `budget_spent`, the order of the open steps, the unbounded total, the absence of a byte offset, and the rules of decision 6.

### 1. Scope

This record fixes three things of `runs/<run_id>/STATE.json`: the file as a whole (decision 2), the round pointer (decision 3) and the stored spend view (decisions 4 and 5). **Every other member is not fixed here**, and nothing of any other file is.

### 2. The file as a whole

- The file is **one JSON object**. The encoding is UTF-8 without a byte order mark, and no member name occurs twice in any object of the file (both as ADR-0005 and ADR-0006 have it).
- **Written form** (as ADR-0005 decision 2, for line-wise diffs in the history — NFR-2): LF line ends and a final line feed; the members in the order `schema_version`, `round`, `budget_spent`, then the others in an order this record does not fix; inside `budget_spent` the order `totals`, `position`, `open_steps`; the axes of `totals` in ascending order of their names; the open steps in the order of decision 4, and inside an identity object the order `round`, `candidate`, `attempt`, `step`, `execution`. The exact white space is the writer's, as long as it is the same on every write. A reader accepts any JSON text of this shape, in any order of members.
- **`schema_version`** is a top-level member and the *integer* `1` (NFR-7 ②; the place is this record's). It is in the file, not in `instance.json`: that file is written once (ADR-0004), while this one is rewritten for the whole life of a run by a writer that may be replaced at a round boundary. It is independent of the layout version (ADR-0004 decision 9).
- **Required members in version 1**: `schema_version`, `round` and `budget_spent`.
- **Members this record does not define.** The top level is **open in version 1**: the file may hold further members. A reader does not interpret a member it does not know and does not treat it as an error; a validator of this record checks the three members above and, of the others, only the rules for the whole text (the encoding, no member name twice). `budget_spent` and the objects inside it are closed (decision 4).
  - Why open: the members this record leaves out are added by later records, one decision at a time, and the writer is an agent of the first layer while the validator is code of the second (NFR-7 ①: either may be replaced at a round boundary). With a closed set, a file written by the newer of the two would be invalid for the older.
  - **What raises the version**: a member defined by this record is removed or renamed, or its type, form or meaning changes; a member is added inside `budget_spent`; or a later record makes a further top-level member **required**. A later record that defines a top-level member which may be absent does not raise it. So each excluded member can be added without contradicting this record, and whether it is required is that record's choice.
  - The cost: a misspelt name of a member that may be absent is not detected by a version 1 validator. Whether a writer keeps a top-level member it does not know when it replaces the file is not decided here (sub-question ⑫).
- **A missing file** means that no state was written for this `run_id` (as ADR-0004 decision 1 says of a missing directory): no round has begun. The first file holds `round` 0 and the values of decision 4 for a start (cited: ADR-0011 decision 6). What creates it, when in relation to `instance.json`, and whether a run directory that holds other files but not this one counts as a started run, is not decided here (sub-question ⑩). An empty file is not a missing file; it is invalid (decision 6).

### 3. The round pointer

- The member is **`round`**, an *integer*: the `id.round` of ADR-0002 (`0` = bring-up), required.
- **It names the round the run is at: the round that has not ended and that the next turn runs or goes on with.** A run starts with `round` 0. It changes only in the write that ends a round — the same write that takes the stored view (decision 4; #4 §3c) — and then names the next round.
- **The next round is the next integer.** This is this record's reading of ADR-0004 (one sequence of rounds numbered by a single integer, each number used once: `0000`, then `0001`, `0002`), not a sentence of a source. With it, the one number says which rounds exist without a listing (#4 §1; ADR-0004 decision 3): the rounds `0` to `round` − 1 are over, no round above `round` has begun, and the round `round` itself has begun or not — which its directory at a known path shows (ADR-0004 decision 1).
- What a fresh turn concludes at the three moments the sources give:

| Moment | `round` | The turn concludes |
|---|---|---|
| A run has started; the bring-up round has not | `0` | The round to run is 0; nothing has ended |
| A process died inside round *k* (#4 §3b) | *k* — the value written when round *k* − 1 ended, or the start value for *k* = 0 | Round *k* has not ended; the turn goes on with it. What is finished inside it is not said by this member (`phase`, the log — ADR-0011 decisions 4 and 5) |
| The commit of round *k* has been made | *k* + 1 | Rounds 0 to *k* are over; the round to run is *k* + 1 |

- **Not said by this member**: whether a turn runs at all. After the last round of a run, `round` names a round that never begins; that the run is over, stopped or waiting is said by members this record does not define. What makes a round end, whether a round can be given up and how, and how the work of a round is chosen are not defined here either: whatever ends a round does it in the write described above.
- A continuation in the same run (ADR-0004 decision 2 admits rounds with later numbers) goes on from `round`; a new run has its own file. Which of the two a branch is stays OD-8 sub-question ①.

### 4. The stored spend view

- The member is **`budget_spent`** (the name of #4), required: an object with **exactly** the members `totals`, `position` and `open_steps`, all three always present. They are the three parts of the spend view (cited: ADR-0011 decisions 1 and 6) under the names `hilclaw.journal.SpendView` already uses.

| Member | Type and form | At the start of a run |
|---|---|---|
| `totals` | object from an axis *name* to a **total**, possibly empty | `{}` |
| `position` | *integer*: the number of complete lines of `events.ndjson` the view was folded over | `0` |
| `open_steps` | array of identity objects, possibly empty | `[]` |

- **A total** is a JSON number that is a non-negative integer, written in decimal digits without sign, fraction or exponent, and **of any size**: it is not bound by the *integer* range of ADR-0001. An amount is an *integer*, a sum of amounts need not be, and the view is exact by ADR-0011 decision 7 (the stored view folded over the tail equals the fold from the first line). A reader takes a total exactly; one that cannot represent it reports an error and does not round.
- **An axis is in `totals` exactly when an end line of the folded prefix named it**, with total `0` included. The stored view is then the fold's result member for member, and the comparison of ADR-0011 decision 6 (*Disagreement*) needs no rule about absent axes. `totals` holds amounts accounted through the log only.
- `position` is an *integer* of ADR-0001; a log with more lines than that range holds cannot exist, so this bounds no view of a real log.
- **An identity object** has `step` (a *name*) and `execution` (an *integer* ≥ 1), and those of `round`, `candidate` and `attempt` that the lines of the step carry, with the forms and the rule of the envelope (cited: ADR-0006 decision 3 — `candidate` only with `round`, `attempt` only with `candidate`). It has no other member. An absent number is left out; no member holds `null`. The five names are those of the lines, flattened into one object, since none of them collides.
- **No identity occurs twice** in `open_steps`: two objects with the same members and values are the same identity (ADR-0011 decision 3).
- **Order**: the writer writes the open steps in ascending order of `round`, then `candidate`, then `attempt`, then `step` (by code point), then `execution`, an absent number coming before every present one. The order carries no meaning — the open steps are a set — and a reader accepts any order; with the written form of decision 2 it makes the bytes of `budget_spent` a function of the view.
- This form carries every view `hilclaw.journal.fold` returns for a log. Which identities the fold lists as open is ADR-0011's and is not touched: the question raised with T-0041 — whether an identity started again after it ended is among the open steps — is not answered here, and **both answers fit**, since the form holds whatever set the fold gives.
- `budget_spent` is closed. Where the running value of an axis that is not accounted through the log is kept stays undecided, as ADR-0011 decision 6 left it: a record that puts it inside `budget_spent` adds a member and raises the version, one that puts it elsewhere does not, and neither is chosen.

### 5. No byte offset

- **The stored view holds the line count alone.** The cost, stated: a reader reaches the position by counting line feeds from the start of the file, so the bytes passed over at the entry of a turn grow with the run, while the lines parsed and folded do not (ADR-0011 decision 6, *Bound*).
- Why not an offset as well. It would be a second statement of one position, and the two could disagree (the argument of ADR-0006 decision 4 against a sequence member). A reader could check an offset against the line count only by the count it was meant to avoid, so it would either trust a number nothing checks or pay the cost anyway. A reader accepts a carriage return before a line feed (ADR-0006 decision 2), so two files of different bytes can hold the same lines: a line count is right for both and an offset for one. And passing over bytes without parsing them is cheap beside one turn; no run exists whose log shows otherwise.
- A later record may add the offset with a new version, once a measured log shows the need (sub-question ⑬).

### 6. Writing and reading

- **The file is replaced as a whole by its one writer** (cited: ADR-0004 decision 4 — the Round-Manager only). It is never appended to or patched in place.
- **A write that does not end a round carries `round` and `budget_spent` over unchanged** (for `budget_spent`, cited: ADR-0011 decision 6). Later records may write other members inside a round — the `phase` marker of #4 §3b is one — and such a write does not touch these two.
- **The write that ends a round** sets `round` to the next round and `budget_spent` to the view of the log folded to a position the log has reached. Who folds, and how the result reaches the writer, is not decided here (OD-23).
- **Requirement on the writer**: a death of the writing process leaves the previous content or the new content, never a part of one. The technique, and whether the agent writes through a tool of the package, are left to the code task and to OD-23.
- **A file that is not valid.** The file is invalid when it is not UTF-8 without a byte order mark, is not exactly one JSON text that is an object, holds a member name twice in any object, lacks `schema_version` or holds a value there that is not an *integer*, or — at version 1 — lacks a required member or holds one that breaks the types and forms of decisions 3 and 4. The written form of decisions 2 and 4 (line ends, the final line feed, every order) binds the writer only and is no part of validity. A `schema_version` that is an *integer* other than `1` is not damage: a version 1 reader reports an unsupported version and interprets nothing (OD-11). **Invalidity is an error, as damage of the log is** (ADR-0006 decision 6): the reader reports it, uses no member of the file and repairs nothing. A turn has no other entry point, so it does not go on.
- **What is recovered from where**: the file of the last commit, from the history of the data repository (#5 A-3). Together with the log of the working tree it is a consistent pair for the members of this record: committed lines are never removed (ADR-0006 decisions 5 and 6), so the committed view is still the view of a prefix of the log, and the committed `round` names the round that had not ended at that commit; the steps of that round that the log shows as ended are skipped (ADR-0011 decision 4). A round that ended after that commit without a commit of its own is the third limit of decision 7. Who restores the file, and when, is not decided.
- **What a validator of this file alone can check**: everything in the list of invalidity above. **What it cannot**: that the view is the fold of the log, and that `position` is not beyond the end of the log — a reader of both files sees the second, and it is the error ADR-0011 decision 6 names; that `round` is the round the run is at; that an open step is a step of the log. It sets no rule between `round` and the numbers of the open steps: late lines about earlier rounds exist (ADR-0006 decision 4), and which rounds a step may be about is its tool's contract.

### 7. Limits

- **Two writers**: nothing here orders two turns that both replace the file; the later write wins and the other is lost. Preventing it is the lock (rest of OD-17).
- **A write between two round ends that moves `round` or the view**: decision 6 forbids it and nothing enforces it; one file does not show it. A comparison with the committed file does (sub-question ③ of OD-17).
- **The end of a round written and its commit not made**: a process death between the two leaves, in the working tree, a file that names the next round. Nothing in the members of this record says that a commit is owed; which step commits, and how a fresh turn learns it, is not decided (ADR-0006 Boundaries; sub-question ⑪).
- **Machine loss before the commit** (#5 A-3): the file and the log go back to the last commit together, and they agree there (cited: ADR-0011 decision 6 — a committed `STATE.json` names no position beyond the log of the same commit).
- **A stored view that disagrees with the log**: the log is authoritative, and ADR-0011 decision 6 says what happens.
- **A wrong `round`**: nothing checks the pointer against the round directories (ADR-0004 decision 10), and a turn does not walk them to find out.

### Example

Synthetic values. `example_step` and `example_axis` are placeholders: this record proposes no step name and no axis. The first line is the file at the start of a run. The second is the file after round 3 ended, for a log of three lines: the two of the Example of ADR-0011 and a start line of candidate 1 that has no end line. Each file is shown on one line; the white space is the writer's.

```json
{"schema_version": 1, "round": 0, "budget_spent": {"totals": {}, "position": 0, "open_steps": []}}
{"schema_version": 1, "round": 4, "budget_spent": {"totals": {"example_axis": 7}, "position": 3, "open_steps": [{"round": 3, "candidate": 1, "attempt": 1, "step": "example_step", "execution": 1}]}}
```

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A closed set of top-level members; every added member raises the version | Each of the five members still to come would be a new version before a first run exists, and a file of a newer writer would be invalid for an older validator (NFR-7 ①). |
| 2 | Reserve the draft's names (`gate_status`, `best_ref`, …) now | It would fix names of members whose decisions are open, one of them owner-only (OD-3). |
| 2 | `schema_version` in `instance.json` | Written once; the writer of this file can change during a run (the argument of ADR-0006 decision 8). |
| 3 | The pointer names the last round that ended | Nothing has ended before the bring-up round, so the member would be absent or need a value outside `id.round`, and every reader would add one to find the round to run. |
| 3 | A count of the rounds that ended | The same number under a name that says something else; #4 §1 puts the current round into the entry point. |
| 3 | The name `cur_round` of the draft, or `next_round` | The number is called `round` in the spec, the envelope and the blob record; an abbreviation would be the only one, and `next_round` is wrong inside a round. |
| 3 | The next round may be any larger number | The one number would no longer say that the rounds `0` to `round` − 1 are over: finding which exist would need a listing (#4 §1), and nothing in the sources skips a number. |
| 3 | The pointer moves when a round begins | A second write per round would move it, and it would no longer change together with the stored view, whose tail is the lines of the round in progress (ADR-0011 decision 6). |
| 4 | A total as an *integer* of ADR-0001; a larger sum is an error | The write that ends a round would fail on a log every line of which is valid. |
| 4 | A total as a decimal string | Two written forms of a number in one file, for a case no axis is known to reach. |
| 4 | Axes with total 0 left out | The stored view would differ from the fold's result, and a comparison would need a rule for absent axes. |
| 4 | An identity as a nested object (`data` beside the numbers, as on a line), or as one string | Nesting copies a shape that separates envelope from payload, which has no purpose here; a string would need a syntax and an escape rule. |
| 4 | Open steps in the order of their start lines | The view of ADR-0011 holds a set; the order would be a fourth part of it that a fold over a tail must carry. |
| 4 | `open_steps` or `totals` left out when empty | Two shapes of one member; `{}` and `[]` say "none" as well (ADR-0006 on `data`). |
| 5 | A byte offset beside the line count, or instead of it | See decision 5. Instead of it: the position of ADR-0011 is a line count, and the "position beyond the log" error and every report are in lines. |
| 6 | A damaged file is rebuilt from the log and the round directories | Only the spend view can be derived from the log (ADR-0011 decision 8); the pointer would need a walk of the tree (#4 §1), and the reader would repair what it should report. |
| 6 | No requirement on the write | The file is the only entry point and has no rule like that of a torn tail; a half-written file would stop the run until someone restores it. |

## Consequences

- **The validator of PLAN P1-8** can check the list of decision 6 and convert between the stored form and `hilclaw.journal.SpendView`: `totals` to a mapping (a total above `keys.MAX_INTEGER` is valid), `position` unchanged, `open_steps` to a set of `Identity`, an absent number to `None`; on writing, the order of decisions 2 and 4. It needs a JSON parser that keeps integers exact and reports a repeated member name. From then on, a change of what it accepts is a schema change of STATE in the sense of CLAUDE.md A-13. `hilclaw/driver_state.py` validates the driver's `PROCESS/STATE.json`, a different file (DRIVER §2).
- **The reader of `events.ndjson` from a position** takes a line count as its only argument: it passes over that many line feeds without parsing, returns the complete lines after them, and reports the error of ADR-0011 decision 6 when the file holds fewer complete lines.
- `hilclaw/journal.py` and `hilclaw/layout.py` are consistent with this record and unchanged; `layout.run_file(data_root, run_id, "STATE.json")` is the path.
- **A file of version 1 with only these members is not yet enough to run a round**: #4 §1 calls `next_action` the most important member, and it is not defined. This record is the frame the later records add to.
- **Not edited and now less exact** (follow-ups for the integrator): the `STATE.json` row of the path table of ADR-0004 ("Fields: PLAN P1-8, OD-17 (lock, budget — #8 M7), OD-3"); the `STATE.json` line of the draft layout of #4 (`cur_round` is `round`, and `budget_spent` is an object, not a scalar). No sentence of UsageCases became false: UC-1 "STATE를 초기화한다" and UC-3 / UC-4 say nothing of the members.
- In a database (ADR-0004 decision 9) `round` becomes a column of the run row, `totals` and `open_steps` rows keyed by run.
- **A-13 reading**: document mode; no code, dependency or schema file changes. This record is the first definition of three members of the runtime `STATE.json` along the D6 route, as ADR-0005 and ADR-0006 were for their files, and not a change of an existing schema.

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: gate status and anything about gates (OD-3 / #5 A-5); OD-25; C-6; the #5 A and B items.
- **The other members of `STATE.json`**: `best_ref` and the archive (OD-20); `lock{owner, heartbeat}`, fencing and retry (rest of OD-17); the values and the granularity of `phase` (OD-29, OD-23 — ADR-0011 decision 5 stays as it is); the form and vocabulary of `next_action` (OD-23, PLAN P2-1). **No time member is defined**, and the time form of this file stays OD-8 sub-question ⑨.
- **Other files**: all of `instance.json` (target, budget, gates, tolerance, owner, project, the layout version stamp); the result files of an attempt; the form of `run_id`; how a branch or a continuation of a run is represented (OD-8 sub-question ①).
- **Budgets**: axes, units, who measures, enforcement (FR-3, OD-2, #5 A-8, OD-19); where the running value of an axis that is not accounted through the log is kept.
- **Process**: who folds and how the result reaches the Round-Manager (OD-23); when and by whom the stored view is checked against a fold from the first line (OD-17 sub-question ③); what ends a round; which step commits; reading or migrating a file of another version (OD-11).
- Any change to ADR-0011: the T-0041 question is for its revision.
- **Sub-questions this record raises** (registered under OD-8): ⑩ what writes the first `STATE.json` of a run — ADR-0004 gives the file to the Round-Manager and `instance.json` to the start of the instance — and when, and what a run directory without the file means once other files exist (with OD-23). ⑪ How a fresh turn learns that the end of a round was written and its commit is still owed (with "which step commits"). ⑫ Whether a writer keeps a top-level member it does not know when it replaces the file — the writer and the validator can be of different versions (NFR-7 ①; with OD-11). ⑬ Whether the byte offset of the position is added once a log has been measured.
- Code, tests, a JSON Schema file, CI, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-1, FR-3, FR-6, FR-13, NFR-1, NFR-2, NFR-6, NFR-7 ① ②, C-2; register rows OD-3, OD-8, OD-11, OD-17, OD-19, OD-20, OD-23, OD-29.
- [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8), [OD-17](../OpenDecisionProposals.md#od-17), [OD-11](../OpenDecisionProposals.md#od-11), [OD-20](../OpenDecisionProposals.md#od-20); [StandardScenarios](../StandardScenarios.md) S1, S2, S3; [UsageCases](../UsageCases.md) UC-1, UC-3, UC-4.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; *name*, *integer*); [ADR-0002](ADR-0002-od6-codegen-spec.md) (`id.round`, `id.candidate`, `id.attempt`); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1 to 4, 9, 10); [ADR-0005](ADR-0005-od8-artifacts-record.md) (decision 2); [ADR-0006](ADR-0006-od8-events-log.md) (decisions 2 to 6, 8); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decisions 1, 3, 5 to 8).
- #4 body §1, §2e, §3, §3b, §3c, "합의 레이아웃 (현재안)", §4; roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; #7 body §5 G4 ; #8 M5, M7.
- #5 A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body item A-5.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §2, §9; PROCESS/PLAN.md P1-8, P2-1; `hilclaw/journal.py`, `hilclaw/events.py`, `hilclaw/layout.py`, `hilclaw/keys.py`; tasks T-0040, T-0041, T-0042.
