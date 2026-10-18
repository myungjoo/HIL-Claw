# ADR-0097: How a change in the `data` of an event kind of `events.ndjson` is told apart — a changed payload is a new kind, and a kind's definition never changes (the payload-change part of sub-question ⑧ of OD-8)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences: no sentence of the owner speaks of event payloads or of how their change is told apart, and this record attributes nothing to the owner; the requirement it relies on, NFR-7 ① ②, is cited and not re-decided. What an accepted record or a file of `hilclaw/` says is **cited** with its source. **Everything else is this record's own design**: the rule of decision 2, what counts as a change (decision 3), the reading for the `result` object and the axes of `spend` (decision 4), and every weighing.
- Answers **the payload-change part of sub-question ⑧ of OD-8** (Open Decisions register in [Requirements](../Requirements.md)): when the `data` of an existing kind changes, how a line written under the old payload is told apart from one written under the new one. The first part of ⑧, the vocabulary of `kind`, stays open, and so does ⑨ (Boundaries). It registers sub-question ㉟ under OD-8 (decision 4). OD-8 keeps its status word.
- **No line that exists today changes**: `schema_version` stays `1`, the envelope stays as ADR-0006 has it, the exact `data` members of `step_started` and `step_ended` stay as ADR-0011 has them, and no new kind is named.
- It builds on [ADR-0006](ADR-0006-od8-events-log.md) (decisions 3, 5, 6 and 8) and [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decision 3), both accepted on 2026-10-07. **If either is reverted, this record is revisited with it.**
- **It is a record, not code**: decision 1 was read from `hilclaw/events.py` and `hilclaw/journal.py` at `0b59b16` as files; nothing was established by running code, and no compiler, container or `claude` process was started. No code changes because of it (Consequences).
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point.** `schema_version` "covers the line format and the envelope … It is **not** raised by a new value of `kind`, nor by a change in the `data` of a kind; how such a change is told apart is left open (Boundaries)" (cited: ADR-0006 decision 8). ADR-0011 named the only two kinds and left "how a later change in the `data` of these two is told apart" to "OD-8 sub-question ⑧" (cited: ADR-0011 decision 3).
- **Why it matters.** The file "is appended to for the whole life of a run and is never rewritten, while the tool layer may be replaced at a round boundary (NFR-7 ①)" (cited: ADR-0006 decision 8); "A complete line is never edited, removed or reordered" (cited: ADR-0006 decision 5). A line written under one definition of a kind therefore stays in the file after the definition has changed, and NFR-7 ② asks for a `schema_version` on persistent artefacts.
- **What a reader already has.** "A reader of the envelope treats an unknown value [of `kind`] as an unknown kind, not as an error" (cited: ADR-0006 decision 3). "A task that defines a kind states its name, which of `round`, `candidate` and `attempt` it carries, and its `data`" (cited: ADR-0006 Consequences).
- **Why now.** Every tool contract that puts a `result` into a `step_ended` line adds to what a log holds for the life of a run; the question has stood since 2026-10-07.

## Decision

Terms: **the definition of a kind** is what the accepted record that names the kind states of its lines — which of `round`, `candidate` and `attempt` they carry (ADR-0006 decision 3), the members of `data`, which are required, and the type, form and meaning of each. **A payload** is the `data` of a line read under that definition.

### 1. What the code does today (observation, binds nothing)

- `hilclaw/events.validate` checks the envelope only: "`kind` is checked against no vocabulary and the content of `data` is not checked" (cited: its docstring); the module "knows no event kind and no member of `data`" (cited: its module docstring).
- `hilclaw/journal.py` knows exactly two kinds, `STEP_STARTED = "step_started"` and `STEP_ENDED = "step_ended"`, with `_MEMBERS` holding `step`, `execution` for the first and `step`, `execution`, `spend`, `result`, `failure` for the second. A line of either kind whose `data` has a member outside that set is rejected (`_checked`: "without the member"); a line of any other kind is not a step line (`_checked` returns `None`). `result` "is a `dict`; its members are not looked at" (cited: its module docstring).
- No other kind exists in any accepted record or in the code.

### 2. The rule: a changed payload is a new kind

- **The definition of a kind is fixed once the record that names the kind is accepted, and it never changes.** It is the definition as that record states it when accepted; a later edit of that record that changes the definition is a change under decision 3 and is not allowed. A later record that wants lines with another definition **defines a new kind under a name no accepted record has used**, and states its definition in full, as ADR-0006 Consequences asks of any kind.
- **A name is never reused.** A kind that a later record stops writing keeps its name and its definition; no record gives that name another definition. This holds also for the name of a kind whose record is reverted: lines may have been written under it and are never removed (ADR-0006 decision 5), so the name stays used.
- **How a line is told apart**: by its `kind` alone. A line's payload is read under the definition of its `kind`; two lines of one `kind` have one definition, in any file and at any time. Nothing inside `data`, and no other member of the envelope (`schema_version` included), says which definition of the kind applies.
- **Why** (this record's own).
  - *An older reader never misreads a newer line.* A reader that does not know the new kind treats it "as an unknown kind, not as an error" (cited: ADR-0006 decision 3) and does not interpret it under the old definition. A reader of the old kind keeps reading the old lines, which are never rewritten (ADR-0006 decision 5).
  - *It needs nothing that does not exist.* `kind` is in every line and already read first; the envelope, `schema_version` and the two kinds of ADR-0011 stay as they are.
  - *It keeps the envelope version for the envelope.* ADR-0006 decision 8 is kept as written (Alternatives, (c)).
- **What it does not say**: which name a new kind takes (no suffix or pattern is fixed — the defining record chooses a *name* of ADR-0001 not used before); how a new kind relates to the kind it follows (for a journaled step: how the repeated call of ADR-0011 decision 3 establishes the state of an identity from lines of both — the defining record states it, with OD-11 for the older lines); whether a run may hold lines of both, and what a reader does with the older one (OD-11; Boundaries).

### 3. What counts as a change

- **Any change of the definition is a change**, and the rule of decision 2 makes **no distinction between kinds of change**: a member added (required or optional), removed or renamed; a change in the type, form or meaning of a member, a narrowing or a widening of its values included; a change in which of `round`, `candidate` and `attempt` the kind carries.
- **What is not a change**: a value the definition leaves open being used — a new value of `step`, which ADR-0011 decision 3 leaves to the tool contracts ("this record lists no value"), or a new axis *name* in `spend` — and anything the definition says is fixed elsewhere (decision 4).
- **Why no distinction** (this record's own).
  - *Even an addition breaks a reader of today.* `hilclaw/journal.py` rejects a `step_ended` line with a member outside its exact set (decision 1). A rule that let an "added optional member" stay under the old name would need every reader of a kind to pass over unknown members, which no record states and the one reader there is does not do.
  - *A change of meaning cannot be detected.* A member whose meaning changes keeps its name and type; only a rule that does not depend on judging compatibility catches it.
  - *Compatibility is a reader's question.* Which older payloads a reader still accepts, and how, is the read guarantee of OD-11; a rule that sorted changes into compatible and incompatible would decide it in advance.
  - It is the same shape as ADR-0006 decision 8, which raises the envelope version for any added, removed or renamed member and any change of type, form or meaning.

### 4. What a `step_ended` line carries that is defined elsewhere: `result` and the axes of `spend`

- **A change in the members of the `result` object is not a change in the `data` of `step_ended`** under decision 3. The definition of `step_ended` says that `result` is an object, "the result object of the call itself" (cited: ADR-0011 decision 3); it fixes no member of it, and each tool's contract does. The definition of `step_ended` is therefore unchanged when a contract's result changes, and the kind stays `step_ended`.
- **Why not a new kind per result change** (this record's own): the repeated-call rule finds a step's state from the two kinds it names (ADR-0011 decision 3); a new end kind per tool change would make every tool contract a change of the journal and of its reader, and the event layer cannot know any tool's members (decision 1).
- **How a changed result is told apart is the tool contract's, and it is not decided here.** A contract could do it by a new value of `step` (a new identity for the step), by a member of its result, or otherwise; the first changes what the repeated call finds across the change, which is OD-11's and OD-18's to weigh. It is **registered as sub-question ㉟ (가) of OD-8** (Boundaries).
- **The axes of `spend` are the same case.** `spend` is "an object from an axis *name* to a non-negative *integer*", and "The unit is the axis definition's" (cited: ADR-0011 decision 7); the definition of `step_ended` fixes neither the axes nor their units. A new axis, or a change in the unit or meaning of an axis, is therefore **not a change in the `data` of `step_ended`** under decision 3. It is not harmless: the fold of ADR-0011 decision 6 sums the amounts of an axis across lines, so a unit changed under the same axis name would be summed silently with the old one. How such a change is told apart (a new axis name, or otherwise) belongs to the axis definitions (FR-3, OD-19, #5 A-8), and it is **registered as sub-question ㉟ (나) of OD-8**.

## Alternatives considered

| Alternative | Why not |
|---|---|
| (a) A changed payload is a new `kind` name | **Adopted** (decision 2). |
| (b) A version marker inside `data` (for example a member `data_version`, absent meaning 1) | The two kinds that exist have no such member and `hilclaw/journal.py` rejects one, so adding it changes them — a change of the data plane's schema; "absent means 1" is an implicit rule that a reader must know per kind. A reader would have to open the payload to learn how to read it, and a line of a kind it knows by name could still be one it cannot read. Two statements of "which definition" (the name and the marker) could disagree. |
| (c) Raise `schema_version` for a payload change, reopening ADR-0006 decision 8 | A version 1 reader raises an unsupported version for such a line and interprets nothing (cited: ADR-0006 decision 6; `hilclaw/events.validate`), so a change in one kind would leave every line of the new version uninterpreted by every envelope reader, the readers of other kinds included, against "an unknown kind, not … an error" (ADR-0006 decision 3). The envelope and every kind would share one counter, and two kinds changed by two records would raise it twice without saying which kind changed. Nothing new argues for reopening the decision. |
| (d) Distinguish kinds of change: an added optional member keeps the name, others take a new one | Decision 3: today's reader rejects an added member, a change of meaning cannot be detected, and the line between compatible and incompatible is OD-11's. |
| (e) Leave the part open | Every later record that changes a payload would choose the means unrecorded, and the choice cannot be made afterwards for lines already written (ADR-0006 decision 5). The rule needs no value, no member and nothing of OD-11. |

## Consequences

- **No code changes.** `hilclaw/events.py` stays right: it checks no vocabulary and no `data`, and the rule asks nothing of the envelope. `hilclaw/journal.py` stays right: its exact member sets are the definitions of ADR-0011, which the rule fixes, and a line of a later kind is not a step line to it (decision 1). A later record that defines a new kind brings its own code task; that task, not this record, changes `journal.py` if the new kind is a journal kind. No code task follows from this record.
- **For a record that defines a kind**: it chooses a name not used before; it does not edit the definition of an existing kind; if its kind follows another, it says how a reader relates the two (decision 2). A tool contract that fixes the members of its `result` meets ㉟ (가) when it changes them; an axis definition meets ㉟ (나).
- **Not edited and now less exact**: ADR-0006 decision 8 ("how such a change is told apart is left open") and its Boundaries (the sub-question "how a change in the `data` of a kind is told apart"); ADR-0011 decision 3 ("how a later change in the `data` of these two is told apart, stays open (OD-8 sub-question ⑧)"). No earlier ADR is edited.
- **The cost, stated**: kind names accumulate over the life of the system; a reader that wants the lines of a step across a change must know every kind that step has been written under; a mistaken change of a definition in place would be undetectable in the file, and only review of the records guards against it. An older reader ignores a line of a newer kind rather than misreading it, which is not the same as handling it: an older journal reader that met the end line of a step under a newer kind would find the identity without an end line (decision 1: such a line is not a step line to it), and the repeated call of ADR-0011 decision 3 could take the step as not run or open. A record that defines a following kind states what that means for readers of the earlier one (decision 2).
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes, and no member, value or kind of the data plane is added or changed.
- **Runtime acceptance items**: none.

## Boundaries (not decided here)

- **The vocabulary of `kind`** (the first part of ⑧): what list of kinds exists and where it is kept. Today the names used are those of accepted records (decision 1, an observation); decision 2's "a name no accepted record has used" relies on those records and fixes no list.
- **OD-11**: whether one file may hold lines of two definitions of a step (an old and a new kind) and what a reader does with an older line; read guarantees and migration; resumption (FR-6) across a change. The OD-11 proposals stay unconfirmed, as [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) and [ADR-0051](ADR-0051-od6-spec-file-version-2.md) left them.
- **Sub-question ㉟, registered under OD-8**, two parts. (가) How a change in the members of a tool's `result` object, carried by `step_ended`, is told apart — by a new value of `step`, a member of the result, or otherwise — and what the repeated call of ADR-0011 finds across such a change (with OD-18, OD-11). (나) How a change in the unit or meaning of an axis of `spend` is told apart, given that the fold of ADR-0011 decision 6 sums an axis across lines (with FR-3, OD-19, #5 A-8).
- **Sub-question ⑨** (the time form of other files); **sub-question ⑥** (`type` of `artifacts.json`).
- **Every event kind and payload not yet named**: the rest of OD-17 (`intent` / `result` events, idempotency keys), OD-23, OD-10; which results are expensive.
- Code, tests, a JSON Schema file, CI, any settings file, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-3, FR-6, FR-13, NFR-7 ① ②; register rows OD-8, OD-10, OD-11, OD-17, OD-18, OD-19, OD-23.
- [OpenDecisionProposals](../OpenDecisionProposals.md): [OD-8](../OpenDecisionProposals.md#od-8) (⑥, ⑧, ⑨, ㉟), [OD-11](../OpenDecisionProposals.md#od-11), [OD-17](../OpenDecisionProposals.md#od-17); [StandardScenarios](../StandardScenarios.md).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; *name*); [ADR-0006](ADR-0006-od8-events-log.md) (decisions 3, 5, 6, 8; Consequences; Boundaries); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decisions 3, 6, 7); [ADR-0024](ADR-0024-od8-instance-record-layout-version.md) and [ADR-0051](ADR-0051-od6-spec-file-version-2.md) (versions marked without read guarantees).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; `hilclaw/events.py`, `hilclaw/journal.py` at `0b59b16`; task T-0291.
