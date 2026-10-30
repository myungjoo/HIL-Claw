# Event kinds of `events.ndjson`

The one list of the names that records have defined as values of `kind` in `runs/<run_id>/events.ndjson` ([ADR-0098](decisions/ADR-0098-od8-event-kind-vocabulary.md)). It is an index: the definition of a kind (its envelope numbers and its `data`) is stated only by the defining record, which wins when the two disagree.

- **Adding a row**: a record that defines a kind chooses a name not in this list and not a placeholder of the example of [ADR-0006](decisions/ADR-0006-od8-events-log.md) (`example_kind`, `other_example_kind`), in the *name* form of [ADR-0001](decisions/ADR-0001-od4-key-schema.md), and adds its row with the state `defined` in the commit that lands it ([ADR-0097](decisions/ADR-0097-od8-event-payload-change.md) decision 2: a name is never reused).
- **States**: `defined` (the defining record is accepted); `not written` (an accepted later record, linked in the row, says no writer writes it any more; still in the vocabulary); `reverted` (the defining record has been reverted; out of the vocabulary, still taken; what a reader does with lines written under it is OD-11's). A row is never removed and its name never changes.
- Nothing checks a line's `kind` against this list; a reader treats a kind it does not know as an unknown kind, not as an error ([ADR-0006](decisions/ADR-0006-od8-events-log.md) decision 3).

| `kind` | Defined by | State |
|---|---|---|
| `step_started` | [ADR-0011](decisions/ADR-0011-od17-journal-and-spend.md) decision 3 | `defined` |
| `step_ended` | [ADR-0011](decisions/ADR-0011-od17-journal-and-spend.md) decision 3 | `defined` |
