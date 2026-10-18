# ADR-0098: The vocabulary of `kind` in `events.ndjson` — the kinds that accepted records define, indexed in one list, `ARCHITECTURE/EventKinds.md`, that the defining record's commit extends; nothing checks a line against it (the vocabulary part of sub-question ⑧ of OD-8)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences: no sentence of the owner speaks of the vocabulary of event kinds or of where it is kept, and this record attributes nothing to the owner. What a requirement, an accepted record or a file of `hilclaw/` says is **cited** with its source. **Everything else is this record's own design**: the vocabulary of decision 2, the list and its place (decision 3), the rule by which a name enters it (decision 4), the absence of a check (decision 5), and every weighing.
- Answers **the vocabulary part of sub-question ⑧ of OD-8** (Open Decisions register in [Requirements](../Requirements.md)), the part [ADR-0097](ADR-0097-od8-event-payload-change.md) left open: what list of kinds exists and where it is kept. With ADR-0097, ⑧ is answered; ⑨ and ㉟ stay open (Boundaries). It registers no sub-question. OD-8 keeps its status word.
- **No line that exists today changes and no kind is named**: `schema_version` stays `1`, the envelope stays as [ADR-0006](ADR-0006-od8-events-log.md) has it, the exact `data` members of `step_started` and `step_ended` stay as [ADR-0011](ADR-0011-od17-journal-and-spend.md) has them. The list it creates holds exactly those two kinds.
- It builds on ADR-0006 (decisions 3 and 8; Consequences), ADR-0011 (decision 3), both accepted on 2026-10-07, and ADR-0097 (decision 2), accepted on 2026-10-18. **If ADR-0097 is reverted, decision 4's purpose of checking a name not used before goes with it and this record is revisited; if ADR-0006 or ADR-0011 is, this record is revisited with it.**
- **It is a record, not code**: decision 1 was read from `hilclaw/events.py`, `hilclaw/journal.py` and `hilclaw/journaled_step.py` at `f6f378a` as files; nothing was established by running code, and no compiler, container or `claude` process was started. No code changes because of it (Consequences).
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it, `ARCHITECTURE/EventKinds.md` included.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point.** "**`kind`**: the form only and **no list of values**. Which kinds exist, and what the `data` of each holds, is left to the tasks that define them" (cited: ADR-0006 decision 3). ADR-0097 left "**The vocabulary of `kind`** (the first part of ⑧): what list of kinds exists and where it is kept. Today the names used are those of accepted records (decision 1, an observation); decision 2's 'a name no accepted record has used' relies on those records and fixes no list" (cited: ADR-0097 Boundaries).
- **Why it matters now.** "A later record that wants lines with another definition **defines a new kind under a name no accepted record has used**"; "**A name is never reused** … This holds also for the name of a kind whose record is reverted" (cited: ADR-0097 decision 2). A writer of a defining record has to be able to tell which names are taken.
- **What a reader already has.** "A reader of the envelope treats an unknown value as an unknown kind, not as an error" (cited: ADR-0006 decision 3). "A task that defines a kind states its name, which of `round`, `candidate` and `attempt` it carries, and its `data`" (cited: ADR-0006 Consequences). A kind name has the *name* form of ADR-0001 (cited: ADR-0006 decision 3).
- **The OD-8 text** says ⑧ is to be decided "종류를 정의하는 task들과 함께 (OD-11·OD-23)" (cited: OpenDecisionProposals OD-8, sub-question ⑧). Why this record answers the vocabulary part without defining a kind is in decision 6.

## Decision

Terms: **a kind** is a value of `kind` with a definition, as ADR-0097 uses the word (the definition of a kind: its envelope numbers and its `data`, as the accepted record that names it states them). **A defining record** is the accepted record that names a kind and states its definition (ADR-0006 Consequences). **A taken name** is a name some record has defined as a kind, whether that record is still accepted or has been reverted (ADR-0097 decision 2).

### 1. What the code and the records hold today (observation, binds nothing)

- `hilclaw/events.validate` checks `kind` for the *name* form only: "`kind` is checked against no vocabulary and the content of `data` is not checked" (cited: its docstring); `append` builds the line and calls `validate`, so it checks no vocabulary either; the module "knows no event kind and no member of ``data``" (cited: its module docstring).
- `hilclaw/journal.py` knows exactly two kinds, `STEP_STARTED = "step_started"` and `STEP_ENDED = "step_ended"`, with their member sets in `_MEMBERS`; a line of any other kind is not a step line (`_checked` returns `None`). `hilclaw/journaled_step.py` is the one caller of `events.append` in `hilclaw/`, and it passes `journal.STEP_STARTED` or `journal.STEP_ENDED`.
- No other kind exists in any accepted record or in the code (ADR-0097 decision 1, re-confirmed by a search of `ARCHITECTURE/decisions/` on 2026-10-18). The word `kind` names other vocabularies in the records — the tool-failure kinds of `error.kind` and its reserved kinds (ADR-0010 decision 4, ADR-0015 decision 2, ADR-0016, ADR-0019), the `kind` of an op_signature (ADR-0041), the entry kinds of `hypotheses.json`, of a verdict and of what refers to them (ADR-0059, ADR-0071, ADR-0072, ADR-0073, ADR-0075) — none of which is a value of the `kind` of a line. `example_kind` and `other_example_kind` appear in ADR-0006's example, which says they "are placeholders and not proposed kinds" (cited: ADR-0006).

### 2. What the vocabulary is

- **The vocabulary of `kind` is the set of kinds whose defining record is accepted.** A line whose `kind` is in it is read under that kind's definition (ADR-0097 decision 2). A line whose `kind` is a name never defined, or a placeholder, has no definition, and a reader treats it as an unknown kind, not as an error (ADR-0006 decision 3, unchanged). A line written under a kind whose defining record has been reverted has no definition that this record gives it either; what a reader does with it is OD-11's (third bullet).
- **Today the vocabulary is exactly `step_started` and `step_ended`**, defined by ADR-0011 decision 3.
- **The taken names are a superset of it**: every name of the vocabulary, every name of a kind that a later record stops writing (it stays in the vocabulary — ADR-0097 decision 2 says it "keeps its name and its definition"), and every name of a kind whose defining record has been reverted (out of the vocabulary, still taken). What a reader does with lines written under a reverted kind is OD-11's (Boundaries).
- The placeholders of ADR-0006's example are neither in the vocabulary nor taken; a defining record does not choose them, so that the example never reads as lines of a defined kind.

### 3. Where the list is kept: one index, `ARCHITECTURE/EventKinds.md`

- **There is one list of kinds, the file `ARCHITECTURE/EventKinds.md`**, created with this record. It is an **index**, not a second definition: one row per taken name, with three columns — the name, a link to the defining record (with the decision that states the definition), and the state of the name.
- **The states**, one per row: `defined` — the defining record is accepted (the name is in the vocabulary); `not written` — still in the vocabulary, and an accepted later record, linked in the row, says that no writer writes it any more; `reverted` — the defining record has been reverted (the name is out of the vocabulary and stays taken). A row is never removed and its name is never changed: the list only grows, as the log it describes (ADR-0006 decision 5).
- **What the list does not hold**: no envelope number, no member of `data`, no type or meaning; the defining record states them and is the only source of the definition. The list holds no reason and no history either; git holds them.
- **Which wins**: the defining records stay the source of the vocabulary and of the definitions. If the list and the records disagree — a kind a record defines is missing from the list, or a row names a record that defines no such kind —, the records stand and the list is corrected by a document change, which defines nothing.
- **Why a separate list** (this record's own): the word `kind` names at least four vocabularies in the records (decision 1), and the records that define event kinds belong to several ODs — the only two kinds today come from a record of OD-17, not of OD-8 —, so neither a search of the records nor the OD-8 adopted lines finds the taken names reliably; a superseded record is kept (ADR-0001 Record format), but its names are found only by reading it, and no rule says how a reverted record is kept (DRIVER §9 says only that a task reverts it). One short index is the means by which "a name no accepted record has used" (ADR-0097 decision 2) can be checked.

### 4. How a name enters the list

- **A defining record** chooses a name of the *name* form of ADR-0001 that is **not in the list** (and not a placeholder of decision 2), states its definition in full as ADR-0006 Consequences asks, and **adds the row** of that name with the state `defined` **in the commit that lands the record** — the same commit, as the register rows and the adopted lines are kept with their records. A kind defined otherwise than by a record (an owner decision) enters by the document commit that records it, in the same way.
- **A record that stops a kind being written** sets that row to `not written` and links itself in the row, in the commit that lands it; it does not touch the name or the defining record's link.
- **A task that reverts a defining record** sets that row to `reverted` in its commit; it does not remove the row.
- No row is added by code, by a test or by a run, and the list is not read at run time.

### 5. Nothing checks a line's `kind` against the list

- **No writer and no reader checks a line's `kind` against the list**, and this record asks for no such check. `hilclaw/events.py` stays without a vocabulary; a reader treats a kind it does not know as an unknown kind, not as an error (ADR-0006 decision 3).
- **The guard is the records and their review**: code writes a kind only after its defining record is accepted, through the constants the code task of that record adds (as `hilclaw/journal.py` holds the two kinds of ADR-0011 — decision 1), and a defining record that adds no row, or reuses a taken name, is caught by its review. Neither is detected by code.
- **Why no check** (this record's own): a check at `append` would need a copy of the list in `hilclaw/`, a second list that a new defining record has to change in a code task before any line of its kind can be written, while the only writer already writes named constants only (decision 1); it would also make `hilclaw/events.py` know kinds, which its design avoids (decision 1). A check at a reader would turn an unknown kind into an error, against ADR-0006 decision 3.

### 6. Why the vocabulary part is answered now, without OD-23 and OD-11

- The OD-8 text joins ⑧ to the tasks that define kinds (OD-11, OD-23). **Which kinds exist** stays theirs: this record names no kind, and every kind not yet named is defined by its own record, entering the list by decision 4. **How names are kept and how one enters** depends on no kind, no roster of agents (OD-23) and no read guarantee (OD-11), and ADR-0097 decision 2 already needs it.
- OD-23 decides which agents act and so which events there will be, and OD-18 which part appends; neither changes where a name is recorded. OD-11 decides what a reader does with an older line, a reverted kind's lines included; decision 2 leaves that open.

## Alternatives considered

| Alternative | Why not |
|---|---|
| (a) No separate list: the accepted records are the vocabulary, found by the OD-8 adopted lines, the register rows or a search of `ARCHITECTURE/decisions/` | The vocabulary *is* still the records (decision 2); what (a) lacks is a means to find them. The defining records belong to several ODs (ADR-0011 is OD-17's), so the OD-8 adopted lines and row miss kinds; a search for `kind` meets the tool-failure kinds, op_signature, the entry kinds of `hypotheses.json` and ADR-0006's placeholders (decision 1); a reverted record's names are found only by reading it. "A name no accepted record has used" (ADR-0097 decision 2) would be checked by memory. |
| (b) One list in an `ARCHITECTURE/` document that each defining record updates | **Adopted** (decisions 3 and 4), as an index of names, records and states only, so that it cannot hold a second definition. Its cost: a commit that forgets the row leaves the list behind the records; decision 3 says the records stand and the list is corrected. |
| (c) A list in 2층 code — constants in `hilclaw/events.py` —, with or without a check at `append` | The records define kinds before code exists for them, and a reverted record's name has to stay taken whether or not code ever wrote it, so code cannot be the source of the taken names. Without a check, the constants would duplicate the document list and those of `hilclaw/journal.py`; with a check at `append`, every new kind would need a change of `hilclaw/events.py` before its first line, and the module would know kinds (decision 5). A reader-side check is excluded by ADR-0006 decision 3. A code task would follow, for no failure that occurs today. |
| (d) Leave the part open | ADR-0097 decision 2 relies on telling which names are taken; each later defining record would decide unrecorded how it checks, and a name reused by mistake cannot be withdrawn from lines already written (ADR-0006 decision 5). The answer needs no kind and nothing of OD-11 or OD-23 (decision 6). |
| (e) The list as a section of this record, edited by each later record | A record states its decision when accepted; a section edited by every later record would make this record's text change with records it does not decide, and the OD-8 adopted lines and register row cannot hold it under their recording rules. |

## Consequences

- **No code changes.** `hilclaw/events.py` stays right: it checks the *name* form only and knows no kind (decision 5). `hilclaw/journal.py` and `hilclaw/journaled_step.py` stay right: the two kinds they know are the two rows of the list (decision 1). A later defining record brings its own code task, which adds the constants of its kind where its reader and writer need them; no code task follows from this record.
- **`ARCHITECTURE/EventKinds.md` is created** with this record, holding exactly the rows `step_started` and `step_ended`, both `defined`, both linked to ADR-0011 decision 3.
- **For a defining record**: it checks its name against the list, adds its row in its landing commit (decision 4) and meets ADR-0097 decision 2. For a record that stops a kind or a task that reverts a defining record: it changes the state of the row. A reviewer of such a record checks the row.
- **Not edited and now less exact**: ADR-0006 decision 3 ("the form only and **no list of values**") and its Boundaries ("any list of kinds"; the sub-question "the vocabulary of `kind`"): the line format still has no list, and the list of this record is outside it; ADR-0097 Boundaries ("**The vocabulary of `kind`** (the first part of ⑧) … fixes no list"). No earlier ADR is edited.
- **The cost, stated**: one more document to keep in step with the records; the list is correct only as far as the commits that land defining records keep it, and nothing but review detects a missing row or a reused name.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes, and no member, value or kind of the data plane is added or changed. The new document indexes two kinds that ADR-0011 already defines.
- **Runtime acceptance items**: none.

## Boundaries (not decided here)

- **Every event kind and payload not yet named**: the rest of OD-17 (`intent` / `result` events, idempotency keys), OD-23, OD-10; which results are expensive.
- **OD-11**: whether one file may hold lines of two definitions, what a reader does with an older line or a line of a reverted kind, read guarantees and migration. The OD-11 proposals stay unconfirmed, as [ADR-0024](ADR-0024-od8-instance-record-layout-version.md), [ADR-0051](ADR-0051-od6-spec-file-version-2.md) and ADR-0097 left them.
- **Sub-question ⑨** (the time form of other files) and **sub-question ㉟** (가)/(나) (a change in a tool's `result` members or in an axis of `spend`).
- **The `type` vocabulary of `artifacts.json`** (sub-question ⑥). It is a parallel question — a value list for a member of another file — and this record does not answer it.
- Whether a later record adds a code-side check of `kind` (decision 5 asks for none); any such check would not change how a reader treats an unknown kind (ADR-0006 decision 3).
- Code, tests, a JSON Schema file, CI, any settings file, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-13, NFR-7 ① ②; register rows OD-8, OD-10, OD-11, OD-17, OD-18, OD-23.
- [OpenDecisionProposals](../OpenDecisionProposals.md): [OD-8](../OpenDecisionProposals.md#od-8) (⑥, ⑧, ⑨, ㉟), [OD-11](../OpenDecisionProposals.md#od-11), [OD-17](../OpenDecisionProposals.md#od-17), [OD-23](../OpenDecisionProposals.md#od-23); [StandardScenarios](../StandardScenarios.md); [EventKinds](../EventKinds.md).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; *name*); [ADR-0006](ADR-0006-od8-events-log.md) (decisions 3, 5, 8; Consequences; Boundaries); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decision 3); [ADR-0097](ADR-0097-od8-event-payload-change.md) (decisions 1, 2; Boundaries); [ADR-0010](ADR-0010-od18-tool-exposure-form.md), [ADR-0015](ADR-0015-od18-tool-contract-frame.md), [ADR-0016](ADR-0016-od18-backend-frame.md), [ADR-0019](ADR-0019-od18-unusable-run-kind.md), [ADR-0041](ADR-0041-od18-correctness-check-dimensions.md), [ADR-0059](ADR-0059-od30-round-hypothesis-record.md), [ADR-0071](ADR-0071-od30-hypothesis-verdict-record.md), [ADR-0072](ADR-0072-od30-hypothesis-outcome-case-file.md), [ADR-0073](ADR-0073-od30-case-lookup-and-case-basis.md), [ADR-0075](ADR-0075-od30-injection-at-instance-start.md) (other vocabularies named `kind`); [ADR-0024](ADR-0024-od8-instance-record-layout-version.md), [ADR-0051](ADR-0051-od6-spec-file-version-2.md).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; `hilclaw/events.py`, `hilclaw/journal.py`, `hilclaw/journaled_step.py` at `f6f378a`; task T-0292.
