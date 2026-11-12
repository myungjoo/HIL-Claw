# ADR-0201: A given-code run is fresh with the `artifacts.json` its start wrote, and its Round-Manager reaches the placement of `(0, 1, 1)` through the tool `given.place` (amends ADR-0120 decision 4 for the runs of ADR-0200 decision 4 (a); part of OD-33 and OD-28)

## Status

- **Accepted on 2026-11-12** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor in task T-0563 and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Content**: every sentence is this record's own, except what it cites with its source. No owner sentence is crossed: HQ-0097 (b) (i) fixes the `artifacts.json` record of the given code, not when a run is fresh; ADR-0120 and ADR-0200 are §9 records the owner has not confirmed.
- **Amends** [ADR-0120](ADR-0120-od8-first-state-file.md) decision 4 for one kind of run only and **completes** [ADR-0200](ADR-0200-od33-given-code-evaluation.md) decision 4 (a) and its slice 3b (decision 8). Each OD keeps its status.
- **No member, file, kind of a data-plane file, value or version is added or changed.** The tool name `given.place` and its failure kinds are names of the tool layer: the tool is not journaled, and nothing it answers is stored (D23 — an MCP tool name and its caller are no data-plane frame). No `claude` process was started (D16).
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **ADR-0120 decision 4** (cited): a run directory is fresh when it holds `instance.json` "and no other file of the tree: no `STATE.json`, `events.ndjson`, `artifacts.json` or `rounds/`"; the turn loop takes a fresh run up, and the Round-Manager writes the first `STATE.json` only into it (entry step 2 of `orchestration/round-manager.md`, through `run.fresh`, ADR-0124).
- **ADR-0200 decision 5** (cited): the start of a given-code run stores the blob, then writes `instance.json`, then the `artifacts.json` record of `type` `given_code`. T-0561 implemented that order in `hilclaw.start_instance.start`.
- **The conflict, observed in T-0563**: a given-code run started by that start holds `artifacts.json` before any turn, so it is never fresh. `hilclaw.turn_start` answers it `open_state` (`state_missing`) and starts no session, and a Round-Manager would end at entry step 2. Round 0 of a given-code loop run (ADR-0200 decision 4 (a)) could never begin. ADR-0200 does not mention it.
- **ADR-0200 decision 7** names "the placement of `(0, 1, 1)` (new) — writes `given.c` from the verified blob; called by the command" and leaves open how the Round-Manager of a live turn reaches it. The Round-Manager has no file tools (`orchestration/round-manager.md`, ADR-0124 decision 2), and the round-0 turn of a fresh run does not read `instance.json` before step 2 today.

## Decision

### 1. Freshness of a given-code run

- **A run directory whose `instance.json` states `given_code` (version 3, ADR-0200 decision 6) is fresh when it holds `instance.json`, may hold `artifacts.json`, and holds none of `STATE.json`, `events.ndjson` and `rounds/`.** For every other run ADR-0120 decision 4 is unchanged: `artifacts.json` makes it not fresh.
- **How it is told**: the other names are looked at first, as today. Only when `artifacts.json` is present is `instance.json` read once; the directory is fresh only if `hilclaw.instance.parse_given` accepts it and it states `given_code`. An `instance.json` that is invalid, of another version, or of version 1 or 2 leaves the directory not fresh, as before.
- **Not checked**: what `artifacts.json` holds. Before the first `STATE.json` only the start writes into such a run (ADR-0120 decision 2: the first `STATE.json` is the first write of the round-0 turn), so the file is the start's. A start that failed after `instance.json` and before its record (`GivenCodeUnrecordedError`, T-0561) leaves no `artifacts.json`, and that run is fresh under ADR-0120 as it stands.
- *Why*: the start's record of the given code (owner HQ-0097 (b) (i)) and ADR-0120's "round 0 has not begun" are both true of such a directory. Moving the record into round 0 would change ADR-0200 decision 5 and the start of T-0561 and leave the given code unrecorded between the start and the first turn.

### 2. The Round-Manager's way to the placement

- **The tool `given.place`** (`hilclaw.given_attempt`), registered in the default registry beside `key.store` and admitted for the Round-Manager only (`hilclaw.turn_permissions.ROUND_MANAGER_TOOLS`; the caller check of ADR-0146 holds it for the main session and no agent). Its request is `{"run_id"}`; it places the given code as `output/given.c` of `(0, 1, 1)` after `cas.verify_blob` and returns `{"given_code": <hash>}`. It is not journaled, like the run-file tools (ADR-0124) and `key.store` (ADR-0134). The command of ADR-0200 decision 5 calls the same placement as a function.
- **Round 0, step 2** (`orchestration/round-manager.md`): the Round-Manager first tells whether `instance.json` holds `given_code`, from entry step 6's read or, when the turn did not reach entry step 6 (a round begun at entry step 2), from one `instance.read`. A failed read comes to the stop. A run with `given_code` calls `given.place` once in place of the delegation to `coder-driver`: no spec, no coder call, no repair. Its result goes on to step 3. `output_exists` comes to the stop: an earlier turn of round 0 placed the attempt and ended before `round.end`, which is no attempt that cannot stand, and the stop treats it as the coder path treats `spec_exists` (ADR-0142 decision 2), so a placed given attempt is never closed as if it had failed. Any other failure kind goes to the closing steps, the round having no attempt that stands (ADR-0185 decision 2, as ADR-0200 decision 4 (a) says).
- **The one change for runs without given code**: the round-0 turn of a fresh run now makes that one `instance.read` before it delegates to `coder-driver`. It writes nothing, and every later step is unchanged.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | The start writes the `artifacts.json` record in round 0 (by the placement) | Changes ADR-0200 decision 5 and T-0561's start, and leaves a stored blob unrecorded until the first turn |
| 1 | Accept any `artifacts.json` in a fresh directory | Widens ADR-0120 decision 4 for every run, and a non-given run never has one before its round 0 |
| 1 | Check that `artifacts.json` holds exactly the given-code record | A second parse for what only the start can have written (decision 1, "Not checked") |
| 2 | The Round-Manager calls `given.place` in every round 0 and reads "not stated" as "no given code" | A failure would then be part of the normal path |
| 2 | The turn prompt states that the run has given code | Changes the prompt form of ADR-0123 decision 3 and `hilclaw.turn_start` |
| 2 | The coder-driver places the given code | ADR-0200 decision 4 (a): no coder delegation in round 0 of a given-code run |
| 2 | `output_exists` goes to the closing steps, or an existing `given.c` counts as placed and step 3 follows | The first closes round 0 without the given attempt that an earlier turn placed; the second evaluates a file whose write may not have ended, and differs from the coder path's `spec_exists` |

## Consequences

- **Code** lands with this record (T-0563): `hilclaw/fresh_run.py` (decision 1; `run.fresh` and the loop's step-1 predicate follow it), `hilclaw/given_attempt.py` and its registration and admission, and the round-0 text of `orchestration/round-manager.md` (decision 2).
- **Runtime acceptance item**: T-0563 hands one to `PROCESS/RuntimeAcceptance.md`, as ADR-0200's Consequences say: a live round 0 of a given-code loop run in which the real Round-Manager places the given code, makes no coder call and evaluates `(0, 1, 1)`.
- **Less exact, not edited**: ADR-0120 decision 4 and its table (no exception named); ADR-0124's `run.fresh` row ("reads no file"); ADR-0200 decision 7's reader table (no row for `fresh_run`).

## Boundaries (not decided here)

- Whether round-1 feedback (`spec_feedback`) shows the given attempt, which has no `spec.json` (observed in T-0562's Result).
- Round 0 with N > 1 in a given-code run (OD-28); given code with `compile_settings` (ADR-0200 slice 5).
- What a directory that is not fresh and holds no `STATE.json` means otherwise (ADR-0120, open).

## References

- Records: ADR-0001, ADR-0120, ADR-0123, ADR-0124, ADR-0134, ADR-0146, ADR-0185, ADR-0200.
- Owner: HQ-0097 (b) (i) in `PROCESS/STATE.json`; D6, D16, D23.
- Code: `hilclaw/fresh_run.py`, `hilclaw/given_attempt.py`, `hilclaw/start_instance.py`, `hilclaw/turn_start.py`, `hilclaw/turn_permissions.py`; `orchestration/round-manager.md`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; task T-0563.
