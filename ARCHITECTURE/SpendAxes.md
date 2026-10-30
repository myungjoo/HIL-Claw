# Axes of `spend`

The one list of the axis names that records have defined for the `spend` of `step_ended` lines of `runs/<run_id>/events.ndjson` ([ADR-0102](decisions/ADR-0102-od8-spend-axis-change.md) decisions 6 and 7). It is an index: the unit, the meaning and the measuring party of an axis are stated only by the defining record, which wins when the two disagree.

- **Adding a row**: a record that defines an axis chooses a *name* of [ADR-0001](decisions/ADR-0001-od4-key-schema.md) that is not in this list and is no placeholder of a record or a test (`example_axis`, `other_example_axis`, `a_axis` and the like), checks that the string is no other name in `hilclaw/`, `tests/` and `ARCHITECTURE/`, and adds its row with the state `defined` in the commit that lands it ([ADR-0102](decisions/ADR-0102-od8-spend-axis-change.md) decision 3: a changed definition is a new axis under a new name, and a name is never reused).
- **States**: `defined` (the defining record is accepted); `not used` (an accepted later record, linked in the row, says no tool of the current contracts states amounts of it any more); `reverted` (the defining record has been reverted; the name stays used). A row is never removed and its name never changes.
- Nothing checks a line's axis names against this list.

| Axis | Defined by | State |
|---|---|---|
