# `step` values of journaled steps

The one list of the values that records have fixed for `step` in the `data` of `step_started` and `step_ended` lines of `runs/<run_id>/events.ndjson` ([ADR-0101](decisions/ADR-0101-od8-failure-kind-change-and-step-values.md) decisions 7 and 8). It is an index: what a step under a value does, its result definition and its failure kinds are stated only by the fixing record, which wins when the two disagree.

- **Adding a row**: a record that fixes a `step` value chooses a *name* of [ADR-0001](decisions/ADR-0001-od4-key-schema.md) that is not in this list and is no placeholder of a record or a test (`example_step`, `other_step` and the like), checks that the string is no other name in `hilclaw/`, `tests/` and `ARCHITECTURE/`, and adds its row with the state `defined` in the commit that lands it ([ADR-0100](decisions/ADR-0100-od8-tool-result-change.md) decision 3: a value is never reused).
- **States**: `defined` (the fixing record is accepted); `not used` (an accepted later record, linked in the row, says the contract no longer calls a step under it); `reverted` (the fixing record has been reverted; the value stays used). A row is never removed and its value never changes.
- Nothing checks a line's `step` against this list.

| `step` | Tool | Fixed by | State |
|---|---|---|---|
| `correctness_check_sim` | `correctness.check` | [ADR-0040](decisions/ADR-0040-od18-correctness-check-call-identity.md) decision 3 | `defined` |
| `correctness_check_board` | `correctness.check` | [ADR-0040](decisions/ADR-0040-od18-correctness-check-call-identity.md) decision 3 | `defined` |
| `sim_run_timing` | `sim.run` | [ADR-0062](decisions/ADR-0062-od18-run-tools-call-identity.md) decision 3 | `defined` |
| `board_run_timing` | `board.run` | [ADR-0062](decisions/ADR-0062-od18-run-tools-call-identity.md) decision 3 | `defined` |
