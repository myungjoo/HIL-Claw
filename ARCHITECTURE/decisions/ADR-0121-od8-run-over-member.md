# ADR-0121: The `STATE.json` member `run_status` that says a first-case run is over, its writer and moment, and when a run that states a round budget is over on it — round 0 counts, and the run is over once `round` reaches `round_budget` (rest of OD-8, part of OD-19, OD-8 sub-question ㉙ (가), for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-19** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Two kinds of content.** What an owner decision, an agreement of #4, a requirement, a use case, a scenario or an accepted record says is **cited**, with its source named. **Everything else is this record's own**: the scope, the name, form and value of the member, the reading of unknown values, the writer and moment, the counting rule, the step-1 conclusions, the readings marked as such, and every weighing.
- **The owner-sentence search.** Searched: the body of #4 and its 6 comments; the body of #5 and the 38 of its 191 comments whose text holds no "posted by driver" marker; the bodies and comments of #7 (2) and #8 (6). Terms: budget, round budget, rounds, end, over, stop, terminate, status, 라운드, 예산, 종료, 끝, 중단, 소진. **No owner sentence says which member says a run is over, what writes it, or whether round 0 counts against a round budget.** The sentences found that touch the points, each read for what it says and no further:
  - **O1** — #5 B-4 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285), under "First spec example (GEMM, MVP round 1) — cost is controlled by instance parameters (FR-3), not by model choice": "Initial run caps: N = 1–2 candidates per round, budget 5–10 rounds, …". The owner counts the budget of the initial runs in rounds (as ADR-0032 decision 2 reads it), and calls the values **caps**. It does not say whether round 0 is among the 5–10.
  - **O2** — #5 A-3 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759): a local commit at the end of every turn (= Round) is an invariant. About the commit (⑪), not about the end of a run.
  - **O3** — #5 owner decision of 2026-10-15 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913), item 2: a request to change the toolchain or the environment "stops the run for the answer in every gate mode"; item 3: imprecise timing does not stop the run. They show that a run can stop and wait; they define no member.
  - **O4** — #5 owner decision of 2026-10-01 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693), item 4: a "target reached" early stop is accepted only after a promotion-gate-level re-verification. Another end of a run, not this record's.
  - **#4 body §1 and its draft layout** (agreed): one small `STATE.json` is the entry point, holding the current round, `best_ref`, `next_action`, `budget_spent` and the gate status; the draft names `budget_spent, gate_status, phase, lock{owner,heartbeat}`. No name or value for "the run is over".
  - **#5 body A-5** ("budget 50% 소진" as a gate candidate) and **A-8** (the token part of the budget) are open owner-only questions, not decisions; this record touches neither.
- **Requirement and plan sentences that touch the points**, not owner decisions: FR-3 "복수 지정 시 **any 소진 → 종료** … 시스템 기본 종료 의미론은 **budget 소진 + best 유지**"; UC-1 and UC-3 "종료조건: budget 소진 …", UC-2 also "사용자 종료"; S1 step 2 "budget=20 라운드"; PROCESS/PLAN.md P2-5 "`cpu_standin` × GEMM, N=1, 5라운드". None says whether round 0 counts.
- **Whether O1 reads two ways about round 0, and why that does not block.** O1 can be read with round 0 among the stated rounds or after them. Under decision 4, a run never runs more rounds than its stated number, so a stated budget within 5–10 is a cap under either reading of O1; the other answer (round 0 not counted) would run one round more than the stated number, which exceeds O1 under the first reading. **The adopted answer holds under both readings.**
- **Not an owner-only item.** OD-8 and OD-19 are design-level ODs and not on the owner-only list of DRIVER §9. Nothing here needs #5 A or B, C-6, OD-25 or OD-3; gates and "waiting at a gate" are left out (Boundaries).
- **What it answers**, for the runs of decision 1 only: one more part of the rest of OD-8 (a member of `STATE.json`), the part of OD-19 that ends such a run on its round budget, and OD-8 sub-question ㉙ (가) for that scope. **OD-8 and OD-19 keep their status words**; OD-19's register cell records a partial answer. No sub-question is registered.
- **Data plane**: `runs/<run_id>/STATE.json` gains one top-level member **that may be absent**; `schema_version` stays `1` by ADR-0012 decision 2's rule. No other file, kind, member or version is added or changed, and what a version-1 validator of `STATE.json` accepts does not change (decision 2). **It is a record, not code**, and no `claude` process was started for it (D16).
- It builds on [ADR-0004](ADR-0004-od8-data-plane-layout.md) (path table), [ADR-0012](ADR-0012-od8-runtime-state-file.md) (decisions 2, 3, 6), [ADR-0032](ADR-0032-od8-instance-record-round-budget.md) (decisions 2 to 5), [ADR-0118](ADR-0118-od18-round-process-boundary.md) (decisions 2, 3) and [ADR-0120](ADR-0120-od8-first-state-file.md) (decisions 1 to 4). **If one of them is reverted, this record is revisited with it.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open member** (cited: ADR-0012 decision 3): `round` does not say "whether a turn runs at all. After the last round of a run, `round` names a round that never begins; that the run is over, stopped or waiting is said by members this record does not define." ADR-0012 decision 2 leaves the top level open in version 1: "A later record that defines a top-level member which may be absent does not raise it", and a reader "does not interpret a member it does not know and does not treat it as an error". Its Boundaries keep `gate_status`, `best_ref`, the lock, `phase` (ADR-0011 decision 5; OD-29, OD-23) and `next_action` (OD-23) for other records.
- **The loop** (cited: ADR-0118 decision 3): step 1 "reads the run's files to tell whether a further turn is to run, and returns if not"; what it reads "is not defined", and until a record answers, the code takes a predicate from its caller. ADR-0120 decision 4 answered one state: a fresh run directory gets the round-0 turn.
- **The budget** (cited: ADR-0032): `round_budget` in `instance.json` is an *integer* ≥ 1 stating the run's budget of loop iterations in rounds (decisions 2, 3); a valid file may lack it, and "not stated" is never "unlimited" or a default (decision 4); "what counts against the budget is not decided here" — whether round 0 counts, whether a round cut short or given up counts, which number is compared, when and by what (decision 2; ㉙ (가)); "nothing compares anything with it" (decision 5). Its lower end 1 was chosen as "the smallest number that states a budget under either answer" (decision 3). ADR-0011 decision 9: "The accounting stops nothing".
- **The writer and the round end** (cited): ADR-0004 gives `STATE.json` to "Round-Manager only (#4 roster revision)", which ADR-0120 treats as an owner sentence (W1). ADR-0012 decision 6: the write that ends a round sets `round` to the next round and `budget_spent` to a fold; a write that does not end a round carries both over. ADR-0118 decision 2 (i): a turn ends "after the write that ends its round".
- **Code, as observation only**: `hilclaw.run_state.parse` hands back every top-level member it does not define in `others`, and `hilclaw.run_state.dump` and `hilclaw.run_state_file.replace` write any `others` the caller gives; `hilclaw.instance` reads `round_budget`; `hilclaw.fresh_run.is_fresh` is ADR-0120 decision 4's test; `hilclaw.turn_loop.run` asks the caller's `further_turn`. Nothing reads a run-status member.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

- **The runs of ADR-0120 decision 1**: new first-case runs of ADR-0076 decision 1, whose `instance.json` the start function of ADR-0115 writes and whose turns the turn loop of ADR-0118 starts. Resumed, continued or branched runs (OD-8 ①) and every other run are outside; nothing here is required or allowed of them.

### 2. (a) The member `run_status`

- **`run_status`** is a top-level member of `runs/<run_id>/STATE.json`. Its value is a JSON string. **This record defines one value, `"over"`**: the run is over; no further round of it begins and no further turn of it runs. It defines no value for "stopped", "waiting" or "paused".
- **The member may be absent, and `schema_version` stays `1`** (cited rule: ADR-0012 decision 2). In a valid version-1 file of a run of this scope, **an absent member states nothing about the run's end**: the run is not over by this record. It is not "running", "stopped" or "waiting" either; those stay undefined.
- **Validity is unchanged.** A version-1 validator of `STATE.json` keeps checking the three members of ADR-0012 and passes this one over, as it does today; a file whose `run_status` holds another value or type is still a valid file. **The reader of this record** (the turn loop's step 1, decision 5, and the Round-Manager) treats every present value other than `"over"` — a string it does not know, or a value that is not a string — as **a value it does not know**: it starts no turn and begins no round on that run, and reports the value. So a value a later record adds is never overrun by a reader of this record.
- **How a later record adds a value** (`"stopped"`, `"waiting"`, `"paused"`, …): it names the string, what it means, what writes it, and what removes it or replaces it when the run goes on. Adding a value raises no version: readers of this record already stop on it. Changing the meaning of `"over"` or the name of the member is a change of a defined member and raises the version (cited rule: ADR-0012 decision 2).
- **Name.** Not `phase` (ADR-0011 decision 5; OD-29, OD-23), `gate_status`, `next_action`, `best_ref` or `lock` (#4 draft; ADR-0012 Boundaries); not a reuse of any of them. Written form: after `budget_spent`, in the order ADR-0012 decision 2 leaves free.

### 3. (b) Writer and moment

- **The Round-Manager writes `run_status`**, the one writer of `STATE.json` (cited: ADR-0004; W1 of ADR-0120). Neither the turn loop nor the start function writes it (as ADR-0120 decision 2 has it for the first file).
- **The moment: the write that ends the run's last round** (ADR-0012 decision 6). In that one write, `round` is the next round (cited: ADR-0012 decision 3, "names a round that never begins"), `budget_spent` is the fold of that write, and `run_status` is `"over"`. There is no write between the end of the last round and the member, so no death leaves a file that has ended its last round and does not say so (Alternatives (3)).
- **A write of its own, in one case only**: a Round-Manager that begins a turn and finds no `run_status`, a stated `round_budget` and a `round` at or beyond it (decision 4) writes `"over"` in a write that does not end a round: `round` and `budget_spent` are carried over (cited: ADR-0012 decision 6). It begins no round. This covers an `instance.json` changed after the start (cited: ADR-0032 decision 6) and a file put back from history.
- **A run that is over is not written again.** No component of this scope writes the run's `STATE.json` once it holds `"over"`; a Round-Manager that finds `"over"` at the start of a turn writes nothing into the run and ends. Whether and what may reopen a run (a continuation in the same run, ADR-0012 decision 3; OD-8 ①) is a later record's.
- **The means is open**: how the Round-Manager reaches `replace` and reads `round_budget` is the open point ADR-0120 decision 2 names (OD-23, OD-18).

### 4. (c) A run that states `round_budget` is over on it

- **Round 0 counts.** Every round the run has ended counts, the bring-up round 0 included (FR-1 calls it a round; ADR-0004 decision 2 numbers it in the run's one sequence).
- **The number compared is `round` of `STATE.json`.** After the write that ends round *k*, `round` is *k* + 1 and the rounds 0 to *k* are over (cited: ADR-0012 decision 3), so `round` is the number of rounds ended. **The run is over on its round budget when `round` ≥ `round_budget`.**
- **When and by what**: the Round-Manager compares in the write that ends a round, using the `round` it is writing and the `round_budget` of the run's `instance.json` read then (cited: ADR-0032 decision 5, "a later call reads the file again"), and at the start of a turn as decision 3 says.
- **A round cut short** — its turn ended before the write that ends it (cited: ADR-0118 decision 2 (ii)) — has not ended; it counts once, when it ends. **A round given up**: whether a round can be given up stays open (ADR-0012 decision 3); by this record anything that moves `round` past a round counts it, and nothing else does.
- **Worked example** (`round_budget` 5, the "5 rounds" of P2-5):

| Write | `round` written | `run_status` | Rounds over |
|---|---|---|---|
| First file (ADR-0120 decision 2) | 0 | absent | none |
| End of round 0 (bring-up, baseline) | 1 | absent | 0 |
| End of rounds 1, 2, 3 | 2, 3, 4 | absent | 0–3 |
| End of round 4 | 5 | `"over"` | 0–4: five rounds run, four after round 0 |

  A run that is to have five rounds after round 0 states `round_budget` 6. **This record does not choose P2-5's value**; its run states one. A `round_budget` of 1 is a run of round 0 alone, which FR-1 requires of every instance (consistent with ADR-0032 decision 3's lower end).
- **Every other end of a run stays open** (Boundaries): wall-clock (㉚), tokens (#5 A-8), the target metric reached early (#5 A-4, OD-1; O4), the user's word (UC-2), a no-progress breaker and non-convergence (OD-19, UC-7), and a round 0 with no attempt that can stand (ADR-0119 decision 5). A record that ends a run on one of them may write `"over"` with its own writer and moment.

### 5. (d) What step 1 of the turn loop concludes

For a run of this scope, step 1 now answers these states, and only these:

| State of `runs/<run_id>/` | Step 1 |
|---|---|
| P1 Fresh run directory (cited: ADR-0120 decision 4) | A further turn (the round-0 turn) |
| P2 `STATE.json` valid, version 1, `run_status` `"over"` | No further turn; the loop returns |
| P3 `STATE.json` valid, version 1, `run_status` present with any other value | No further turn; the loop returns and reports the value (decision 2) |
| P4 `STATE.json` valid, version 1, no `run_status`; `instance.json` valid, version 1, with `round_budget` | A further turn, whatever `round` is (its Round-Manager applies decisions 3 and 4) |

- The loop compares no numbers and writes nothing (cited: ADR-0118 decision 3); the one comparison is the Round-Manager's.
- **Open**, and outside the table: a run whose `instance.json` states no `round_budget` (㉙ (나)); a `STATE.json` or `instance.json` that is missing (beyond P1), invalid or of another version, and the directories ADR-0120 decision 4 leaves open; **what follows a failed turn** (OD-10, OD-17, OD-19, OD-27) — P1 and P4 say a turn is due, not how often a failing one is retried; the lock of two loops (rest of OD-17); and **⑪**: a run whose last round ended and whose commit is still owed shows `"over"` (P2), so no turn of it makes that commit. Until a record answers a state, the code does what ADR-0118 decision 3 has it do today: ask its caller's predicate.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| a | A boolean `over` (or `ended`) | No room for "stopped", "waiting" or "paused" (O3; UC-2 gate; OD-19's rate-limit pause), each of which would need a further member and a rule for two members that disagree. |
| a | An object (`{"state": "over", "reason": "round_budget"}`) | Its only defined reason would be the round budget; the reason of an end is not needed to stop the loop. A later record can add a member for it. |
| a | Reuse `phase`, or take `gate_status` / `next_action` | Their values and meaning are other records' (OD-29, OD-23, OD-3 owner-only); a collision would decide them. |
| a | A present invalid value makes the file invalid (as ADR-0032 decision 4 does for `round_budget`) | It changes what a version-1 validator of `STATE.json` accepts, a STATE schema change in the sense of ADR-0012 Consequences and A-13. The reader's outcome is the same here: no further turn. |
| a | The cost of the adopted form | One string holds one state: "over while waiting" cannot be said, and a later "paused" run that goes on needs the member removed or replaced, which that later record defines (decision 2). |
| b | A write of its own after the last round end | A death between the two writes leaves a run whose last round ended and that does not say it is over; the next turn would have to find it out. |
| b | The turn loop writes it (compares and writes before step 1) | A second writer of `STATE.json` against ADR-0004 and W1, and a data-plane write in a loop that has none (ADR-0118 decision 3) — the reasons ADR-0120 Alternatives (3) gave. |
| b | The start function writes it | It writes `instance.json` once and nothing else (ADR-0120 decision 2); it is not there when a run ends. |
| b | No member: step 1 derives "over" from `round` ≥ `round_budget` | It works for the round budget only; every other end (decision 4) still needs a member, and two ways of saying "over" would then exist. |
| c | Round 0 does not count (the run is over when `round` > `round_budget`) | Under a reading of O1 with round 0 among the stated rounds, it runs one round more than the owner's cap. The adopted answer holds under both readings (Status). |
| c | Compare a count of round directories, or a count in the log | A listing (#4 §1 forbids a whole-tree scan) or a fold for a number `round` already gives (ADR-0012 decision 3). |
| c | A cut-short round counts when it begins | Its turn ends before its round, and the next turn goes on with the same round (ADR-0118 decision 2 (ii)); it would count twice. |

## Consequences

- **The code slice it enables** (code mode, a later task; names and modules are its own): a reader of `run_status` from the `others` of `hilclaw.run_state.parse`; the loop's step-1 predicate for P1 to P4, together with `hilclaw.fresh_run.is_fresh`, falling back to the caller's predicate in every other state; and the loop's command-line entry. Tested against a stub `claude` only (D16). **It still waits on**: ㉙ (나) (a run that states no round budget), what follows a failed turn (OD-10, OD-17, OD-19, OD-27), the lock (rest of OD-17) and ⑪; for the writer side, how the Round-Manager reaches `replace` (OD-23, OD-18) and the round-0 part of the Round-Manager prompt (PLAN P2-1).
- **What `hilclaw/run_state_file.py` accepts does not change** (decision 2): the member is written through the `others` of `replace` and read from `parse`; no validator gains a rule. So the slice is **no STATE schema change** in the sense of ADR-0012 Consequences and CLAUDE.md A-13. A later record that makes a present invalid value invalid would be one.
- **Sentences of accepted records that become less exact** (listed, not edited; follow-ups for the integrator). Found by searching `ARCHITECTURE/decisions/` for "over, stopped or waiting", "㉙" and "round_budget". For the runs of decision 1 they are now answered; what else they name stays open.
  - ADR-0012 decision 3 ("that the run is over, stopped or waiting is said by members this record does not define") and Boundaries ("**Budgets**: … enforcement").
  - ADR-0118 decision 3 ("What it reads in step 1 is not defined … Until a record answers it, the code slice takes from its caller a predicate"), Consequences (1), Walk-through and Boundaries ("**The member that says a run is over, stopped or waiting**").
  - ADR-0120 decision 4 ("No member of the run can say that it is over, stopped or waiting"), Consequences (3) and Boundaries ("the member that says a run is over, stopped or waiting").
  - ADR-0032 decision 2 ("What counts against the budget is not decided here"), decision 3 (the lower end "under either answer"), decision 5 ("nothing compares anything with it"), decision 6 ("The member stops nothing"), the last Walk-through row, Boundaries ("**Enforcement and counting**"; "whether round 0 counts") and the text of ㉙ (i).
  - ADR-0033 decision 5 ("No rule that anything is stopped") and Boundaries ("`round_budget` and sub-questions ㉙ (i) and (ii) stay as ADR-0032 left them").
  - ADR-0011 decision 9 ("The accounting stops nothing … (OD-19)") stays exact: this record ends a run on `round`, not on an amount.
  - ADR-0117 Context and Boundaries ("Round and run limits and budgets, and what counts against them … ㉙"), and ADR-0119 Boundaries ("whether round 0 counts against the round budget (OD-28; ADR-0032; OD-8 ㉙)").
  - The list is not claimed to be complete. In code, the docstring of `hilclaw/turn_loop.py` ("no command-line entry, which waits on the OD-8 member that says a run is over, stopped or waiting") is less exact and is not edited.
- **UsageCases and StandardScenarios**: no sentence becomes false. UC-1, UC-3 "budget 소진" and S1 step 7 now have, for a run of this scope that states a round budget, the rule of decision 4; keeping the best (FR-3 "best 유지") is OD-20's and is not touched.
- **A-13 reading**: document mode. No code, test, setting or dependency changes. The data plane gains one member that may be absent, defined along the D6 route as ADR-0012's frame allows, with the version and every validity rule unchanged.
- **Runtime acceptance items**: none from this record. The Round-Manager slice may raise one (that a live Round-Manager writes `"over"` in the write that ends the last round) and is the place to list it (D16).

## Boundaries (not decided here)

- **Values for "stopped", "waiting" or "paused"**, what writes and removes them, and how a stopped or waiting run goes on (UC-2, UC-4; O3; OD-8 ㉝ (가)); **gates** and waiting at a gate (OD-3, #5 A-5 — owner-only).
- **Every other end of a run**: wall-clock (㉚), tokens (#5 A-8 — owner), the target metric (#5 A-4 — owner, OD-1, FR-9 re-verification), the user's word (UC-2), the no-progress breaker and non-convergence (OD-19, UC-7), a round 0 with no attempt that can stand (ADR-0119 decision 5; OD-10); and FR-3's "any 소진" across several stated axes beyond the round budget.
- **The rest of OD-19**: per-round and coder-call caps, the repair bound, the single ledger, the rate-limit pause, a check on the path of the next spend.
- **㉙ (나) and (다)**: a run that states no round budget, the start without any budget, the owner's 5–10 cap at the start (O1), and where the other axes are stated.
- **Whether a round can be given up**, and how (ADR-0012 decision 3).
- **What follows a failed turn**, the lock of two loops, and **⑪** (the commit, including the commit owed by a run that is over).
- **Keeping the best** and its record (`best_ref`, OD-20); the notification at the end of a run (FR-16, OD-27).
- **Runs outside ADR-0120 decision 1**, and resumed, continued or branched runs (OD-8 ①, OD-20); reopening a run that is over.
- A top-level member the writer does not know (⑫); OD-25, C-6 and the #5 A and B items (owner-only).
- Any change to an earlier record, FR or NFR text, UsageCases, `hilclaw/`, `orchestration/`, tests, CI, `.claude/`, any settings file or the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-3, NFR-1; register rows OD-8, OD-17, OD-18, OD-19, OD-23. [OpenDecisionProposals OD-8](../OpenDecisionProposals.md#od-8) (①, ⑩, ⑪, ⑫, ㉙, ㉚, ㉝), [OD-19](../OpenDecisionProposals.md#od-19), [OD-28](../OpenDecisionProposals.md#od-28). [UsageCases](../UsageCases.md) UC-1 to UC-4. [StandardScenarios](../StandardScenarios.md) S0, S1, S2.
- ADR-0001 (record format); ADR-0004 (path table; decision 2); [ADR-0011](ADR-0011-od17-journal-and-spend.md) (decisions 5, 9); ADR-0012 (decisions 2, 3, 6; Boundaries; Consequences); ADR-0032 (decisions 2 to 6; Walk-through; Boundaries); [ADR-0033](ADR-0033-od8-instance-record-wall-clock-budget.md) (decision 5; Boundaries); [ADR-0076](ADR-0076-od8-instance-start-required-members.md) (decision 1); [ADR-0115](ADR-0115-od8-instance-start-performer.md); [ADR-0117](ADR-0117-od14-cpu-standin-time-limits.md) (Context; Boundaries); ADR-0118 (decisions 2, 3; Consequences; Walk-through; Boundaries); [ADR-0119](ADR-0119-od28-first-case-baseline.md) (decisions 1, 5; Boundaries); ADR-0120 (decisions 1 to 4; Alternatives; Consequences; Boundaries).
- #4 body §1, draft layout; #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · 2026-10-15 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913 · 2026-10-01 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5933950693 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 ; #5 body A-5, A-8.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P2-1, P2-5; `hilclaw/run_state.py`, `hilclaw/run_state_file.py`, `hilclaw/turn_loop.py`, `hilclaw/fresh_run.py`, `hilclaw/instance.py`; task T-0335.
