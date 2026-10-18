---
id: T-0316
title: Apply T-0314's two round-7 citation nits to ADR-0110 — the ADR-0026 location for "open or ended" after `end_line_failed`, and the ADR-0011 parts named in the Status builds-on list
phase: P1
status: DONE
commitMode: doc
coversReq: [FR-9, OD-18]
dependsOn: [T-0314]
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0110-od18-check-executions-hard-floor.md
estimatedSize: {loc: 6, files: 1}
hq: []
---
## Why

T-0314 landed ADR-0110 as `4bc7f78` after 7 review rounds. The round-7 Approve left two non-blocking nits about where citations point. They are recorded in T-0314's `## Result

- DONE. Landed on main as d5b1944 (document mode, fast-forward push, no PR). The reviewer is a context-isolated dev-reviewer. It gave Approve in round 1, so the change took 1 round. The commit's trailer block (`Task: T-0316`, `Reviewed-by: reviewer agent (1 rounds, Approve)`, `Co-Authored-By`) parses with `git interpret-trailers --parse`.
- Nit 1 applied. In ADR-0110 decision 3, the bullet "A call that ended with `end_line_failed`" now cites "ADR-0026 decision 2 and the `end_line_failed` row of its decision 3" instead of "ADR-0026 decision 4". The bullet's own words are unchanged, and it quotes nothing.
  - Reason in one line: decision 2 ("After a failed end line": "open, or ended") and the decision 3 row ("the identity is open or ended") state the identity's state, but decision 4 only covers the outcome the failing call returns. So the record now cites 2 and 3, not the reviewer's "2 and 4".
  - The ADR-0026 entry in the Status cites list changed from "decision 4" to "decisions 2 and 3".
  - The ADR-0026 entry in References changed from "decisions 4, 7" to "decisions 2, 3, 7". Decision 7 is still cited by the `start_line_failed` bullet.
- Nit 2 applied. The ADR-0011 parenthesis in the Status builds-on list now reads "(decisions 3, 4, 6 and 9; Consequences)". A grep of ADR-0110 for "ADR-0011" finds exactly that set (decision 3: Context; decision 4: Context and decision 3; decision 6: decision 2 and Walk-through; decision 9: decision 2; Consequences: decision 3 and Alternatives). This set matches the task's list and References. The sentence keeps its form, and the revisit clause is unchanged.
- No decision changes. Only ADR-0110 changed (1 file, 3 lines added and 3 removed; `git diff --check` clean; LF endings). No coverage re-check is owed and no #5 notice is needed. No `claude` process, compiler, container or test was started.
- Finding left unapplied (non-blocking, outside scope): the Status cites list names ADR-0026 decisions 2 and 3 but not decision 7, which the record also cites; the same is true of ADR-0047 decision 7. The reviewer read the Status list as a deliberate subset, so no change is owed. Recorded only as a possible follow-up.
