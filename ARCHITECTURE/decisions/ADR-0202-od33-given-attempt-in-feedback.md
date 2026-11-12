# ADR-0202: The given attempt `(0, 1, 1)` of a given-code run is shown in the `feedback.attempts` of a round ≥ 1 spec and may be its `feedback.base`, with no techniques; and the choices of the command `hilclaw.given_eval` (completes ADR-0200 decisions 4 and 5, closes the ADR-0201 Boundaries question; part of OD-33 and OD-28)

## Status

- **Accepted on 2026-11-12** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor in task T-0564 and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.** The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- **Content**: every sentence is this record's own, except what it cites with its source. No owner sentence is crossed: HQ-0092 (a) and HQ-0097 (b) (i) fix the given code's record and its uses, not how a later round's spec shows it; ADR-0151, ADR-0184, ADR-0200 and ADR-0201 are cited as they stand. ADR-0184 is an owner decision (2026-10-30); this record applies its rule unchanged to one more attempt and changes none of its words.
- **Completes** [ADR-0200](ADR-0200-od33-given-code-evaluation.md) decision 4 (a) ("ADR-0119's baseline rule applies to the given attempt"; "rounds ≥ 1 … do not change") for the spec of a round ≥ 1, and decision 5 (the command) for the points it leaves to its slice. **Closes** the first Boundaries question of [ADR-0201](ADR-0201-od33-given-code-run-fresh-directory.md). It answers no new part of an OD: the OD-28 part "the round-0 baseline of a run with given code is that code's attempt" is ADR-0200's, and each OD keeps its status and its register row.
- **No member, file, kind of a data-plane file, value or version is added or changed.** The entry of the given attempt is an entry of spec version 2's `feedback.attempts` with `techniques` `[]`, which `hilclaw.spec` admits (ADR-0002, ADR-0050); `feedback.base` names it in the existing `ref` form. The command writes only what the tools it calls write. No `claude` process was started (D16).
- **Session entry check** (CLAUDE.md), on 2026-11-12 at `main` `5bab4e64`: no open PR; open `nightly-failure` issue #373 (task T-0559, BLOCKED on HQ-0100); no `실패` item in `PROCESS/RuntimeAcceptance.md`. Unresolved HQs HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0100: none is crossed.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **ADR-0151 decision 3 ⑧** (cited): the earlier attempts of a round ≥ 1 spec are the attempts of candidate 1 "whose `spec.json` exists"; decision 2 (d) gives each entry `techniques`, "the ids of its own spec's `guidance.techniques`".
- **ADR-0184 decision 2** (cited, owner decision): `feedback.base` is the shown attempt verified at both points whose board measurement has the lowest median, the earliest on a tie; `coder.run` copies that attempt's `output/` into the scratch's `base` (decision 3), and the coder prompt asks the coder to start from it.
- **ADR-0200 decision 4 (a)** (cited): in a run whose `instance.json` holds `given_code`, round 0 makes no coder call; `(0, 1, 1)` holds `output/given.c` and has no `spec.json`; ADR-0119's baseline rule applies to it, and rounds ≥ 1 do not change.
- **The gap** (observed in T-0562 and T-0563, recorded in ADR-0201 Boundaries): `hilclaw.spec_feedback` ignores an attempt directory without `spec.json`, so the given attempt never appears in the feedback of round 1 or later and can never be `feedback.base`. A round-1 coder of a given-code loop run then neither sees the given code nor starts from it, and is told by the prompt that "no correct attempt exists yet" although the baseline of its run verified and was measured.
- **ADR-0200 decision 5** (cited) names the command's steps and leaves its argument form, statuses and report to its slice.

## Decision

### 1. The given attempt in the feedback of a round ≥ 1

- **Found**: in a run whose `instance.json` states `given_code` (version 3, ADR-0200 decision 6), the attempt `(0, 1, 1)` is found at ADR-0151 ⑧ when its directory exists and holds no entry `spec.json`, with **`techniques` `[]`** — the given code was written with no technique of the catalog. Every other attempt without `spec.json` stays ignored, and an attempt `(0, 1, 1)` that has a `spec.json` is read from it as before.
- **Shown, failed and chosen by the existing rules**: its standing at the two points, the `failure` of an attempt not verified (its `stage`, its report and a compiler log), and its place among the incumbents of ADR-0184 decision 2 follow exactly the rules every other attempt follows. So a verified and measured given attempt is the `feedback.base` of round 1, and stays the base until a coder attempt is faster.
- **How it is told**: `instance.json` is read, once per call and only when the directory of `(0, 1, 1)` holds no `spec.json`, by the reader of the round tools (`hilclaw.run_file_tools.read`); its failures are the four `run_file_*` kinds, which a round ≥ 1 spec write already gives for that file. A file of version 1 or 2 states no given code, and the directory is ignored as before.
- **At the coder** (observed, `hilclaw/coder_call.py`, `hilclaw/scratch.py`, `hilclaw/coder_runtime.py`): a `feedback.base` naming `(0, 1, 1)` copies `output/given.c` into the scratch's `base`, where the coder prompt tells the coder to start from it. `given.c` is an admitted kernel-file name (ADR-0055), so a coder that keeps the name brings it in as any other file. Nothing of `coder_call` changes.
- *Why*: ADR-0200 decision 4 (a) makes the given attempt the run's round-0 attempt and baseline, and ADR-0184 (owner) carries the fastest verified attempt forward. Leaving the given attempt out would make the given-code loop run's rounds ≥ 1 those of a run whose round 0 never stood, which ADR-0185 reserves for a round 0 without a standing attempt.

### 2. The choices of the command `hilclaw.given_eval` (ADR-0200 decision 5)

- **Form**: `python -m hilclaw.given_eval <request> <c-file>`, the request decoded as by `hilclaw.new_run` (ADR-0155). The statuses, the summary on standard output and the failure lines on standard error are those of the module docstring.
- **The round budget**: a request that states no `round_budget` is started with `round_budget` 1; one that states any other value is refused before anything is written. *Why*: ADR-0200 decision 4 (b) makes the evaluation a run whose budget is 1, and the person need not restate it; a request of another budget is a loop run, which the turn loop starts.
- **The entry of round 0**: `run.fresh`, then `state.write` of the first `STATE.json`, as entry step 2 of `orchestration/round-manager.md` makes it for a fresh run (ADR-0120, ADR-0201 decision 1). The entry's `run.commit` and `state.read` are not made: the run was started by the same call, so nothing is owed and no `STATE.json` exists.
- **Round 0** follows the Round-Manager's round steps: `key.store`, the placement (`hilclaw.given_attempt.place`, ADR-0201 decision 2), `correctness.check` at `sim` and at `board`, each followed by `checks.read` for the standing (ADR-0131 decision 6), then `board.run`, each tool with `execution` 1 and through the default registry so that each is journaled as in a live round 0. A failure of `key.store` is told and the steps go on (round step 1; ADR-0134 decisions 5 and 6). A placement failure other than `output_exists`, a standing other than `"verified"`, and any answer of `board.run` go on to `round.end` and `run.commit` (ADR-0185 decision 2). Each such failure is told when it happens, the first of them gives the command its status, and the summary still follows.
- **A stop** (the run cannot go on: a failure of the entry, `output_exists`, a failure of `round.end` or of `run.commit`) ends the command with its status and the run id, and calls nothing more; the run stays as the failure left it, and a later `run.commit` (the loop's entry step 0, or a person) commits it. *Why*: the command is one non-resumable call, and calling `run.commit` after a failure the command cannot judge could commit a half-written state of another writer.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 1 | Leave the given attempt out of the feedback | Rounds ≥ 1 of a given-code loop run would not start from the run's baseline, against ADR-0200 decision 4 (a) and ADR-0184 |
| 1 | Write a spec for the given attempt so that the reader finds it | A spec without a coder call is version 3, the compile-settings form (owner HQ-0089 ④; ADR-0200 Alternatives) |
| 1 | A `techniques` naming the given code, or a new member marking it | A value or member of the spec the owner has not approved (D23) |
| 1 | Find `(0, 1, 1)` by its `output/given.c` without reading `instance.json` | A coder attempt whose spec is gone would be shown as the given code |
| 2 | Refuse a request without `round_budget` | Asks the person to restate what the command's kind of run fixes |
| 2 | Make the entry's `run.commit` and `state.read` | Both have nothing to do for a run started in the same call; `run.commit` would add a commit of the start alone |
| 2 | `run.commit` at a stop | See decision 2, "A stop" |

## Consequences

- **Code** lands with this record (T-0564): `hilclaw/given_eval.py` (new, decision 2), `hilclaw/spec_feedback.py` (decision 1; `spec.write` and `incumbent` follow it). `hilclaw.model_run_binding` reads `instance.json` with the version-1 reader before it asks for an incumbent, so a given-code run stays refused there (ADR-0200 decision 7, row 6).
- **Registers**: unchanged. ADR-0200 already records the OD-28 and OD-33 parts this record completes; StandardScenarios S12 is unchanged (its steps 2 and 5 cite ADR-0200).
- **Runtime acceptance item** (T-0564 hands it to `PROCESS/RuntimeAcceptance.md`): in a given-code loop run with a budget of at least 2 whose given attempt verified and was measured, the real coder of round 1 starts from `base/given.c`.
- **Less exact, not edited**: ADR-0151 decision 3 ⑧ ("whose `spec.json` exists") and decision 2 (d) ("its own spec's `guidance.techniques`"). The docstring of `hilclaw/spec_tool.py` is corrected for the files the feedback reads.

## Boundaries (not decided here)

- Round 0 with N > 1 in a given-code run (OD-28); given code with `compile_settings` (ADR-0200 slice 5).
- Telling the coder that a base is given code rather than a coder's attempt (no member exists for it, D23).
- A tool comparing an evaluation run's figures with a loop run's (ADR-0200 decision 4 (b)).

## References

- Records: ADR-0001, ADR-0002, ADR-0050, ADR-0055, ADR-0119, ADR-0120, ADR-0131, ADR-0151, ADR-0155, ADR-0184, ADR-0185, ADR-0200, ADR-0201.
- Owner: HQ-0089 ④, HQ-0092 (a), HQ-0097 (b) (i) in `PROCESS/STATE.json`; D6, D16, D23.
- Code: `hilclaw/given_eval.py`, `hilclaw/spec_feedback.py`, `hilclaw/given_attempt.py`, `hilclaw/coder_call.py`, `hilclaw/scratch.py`, `hilclaw/coder_runtime.py`, `hilclaw/model_run_binding.py`; `orchestration/round-manager.md`.
- Process: [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; task T-0564.
