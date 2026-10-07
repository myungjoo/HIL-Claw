# ADR-0011: The journal of a journaled step and the accounting of the spend of a run (one part of OD-17, with #8 M7)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of OD-17** (Open Decisions register in [Requirements](../Requirements.md)): what is written to `events.ndjson` around a journaled step so that a resumed turn does not spend twice, and where the amount a run has spent is recorded and how a fresh turn obtains the total. The register row keeps its status.
- What stays open of OD-17: `lock{owner, heartbeat}` and fencing by a compare-and-swap push, the declarative retry policy per tool, and the three sub-questions this record raises (see Boundaries).
- **#8 M7**: decision 6 is the rule M7 asks for. The M7 checkbox and the text of #4 §1 are not edited here; Consequences holds the proposed wording, and M7 stays unticked until the integrator reflects it.
- It builds on [ADR-0006](ADR-0006-od8-events-log.md) (line, envelope, order, append only, decision 7), [ADR-0004](ADR-0004-od8-data-plane-layout.md) (the run-level files and their writers) and [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 4 and 7), whose objection windows run until 2026-10-14, and on the `id` integers of [ADR-0002](ADR-0002-od6-codegen-spec.md) (until 2026-10-13). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- Agreed in #4 and taken as fixed. §1: every turn starts with a clear context; one small `STATE.json` is the entry point (current round, `best_ref`, `next_action`, `budget_spent`, gate status), only artefacts it refers to are loaded, and a whole-directory scan is forbidden; the most expensive side effect is journaled at once. §3b: a round holds the board measurement (C-4), which is too expensive to repeat; `STATE.json` has an intra-round `phase` marker, an expensive result is appended to `events.ndjson` as soon as it exists, and a fresh turn skips expensive substeps that are finished. Roster revision: only the Round-Manager writes `STATE.json`, and the journaling is the tool layer's job.
- #7 §5 G4 (a survey finding, not a decision) names four durability defects, two of which concern this record. The `phase` marker is a checkpoint and not a journal: a death after the measurement and before the marker update repeats the measurement. `budget_spent` as a mutable scalar loses the spend of a dead round, so a budget is under-counted. Its proposal for these two, registered as OD-17 and not adopted: an `intent` event before a spend and a `result` event after it, tied by an idempotency key; `budget_spent` derived by folding the log, with `STATE.json` a view that can be rebuilt. The other two defects — a lease without fencing, and retries left to the model — and their proposals are the part of OD-17 this record leaves open.
- #8 M7 (open): that fold collides with #4 §1, because its cost grows with the length of the run, and no document states a snapshot rule.
- ADR-0006 fixed the line and the envelope and named no kind; its decision 7 says that the line of an expensive result carries the result, and its decision 9 that the envelope does not exclude this proposal. ADR-0010 fixed that a tool call has one request and one result, that a result which reports a failed experiment is a result while a tool failure means that no outcome was established, and that the outcome of a call does not depend on state a server process kept.
- FR-3 gives the budget vocabulary; whether the token element sums orchestrator and coder is #5 A-8 (open, owner), HW quota as an axis is OD-2, and stopping the next spend is OD-19. NFR-1 asks for a resume at the exact point after a process death; the local commit is the durability boundary (#5 A-3); P1 assumes one run (C-2).
- The schema of the runtime `STATE.json` (PLAN P1-8) and the first FR-10 tool contract (PLAN P1-1) cannot be written while `phase` and `budget_spent` have no agreed relation to the log.

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice — among them the two kinds and their members, the form of the identity, the rule of a repeated call, the precedence of the log over the marker, and the whole snapshot rule.

### 1. Scope and terms

- This record is about what the log holds around a journaled step and about the spend of a run. It is **not the lock, not a retry or recovery policy, and not enforcement**: it accounts and stops nothing.
- **Journaled step**: one execution of a step whose repetition costs a limited resource, or whose outcome must survive the death of the process that obtained it. The sources name one such step, the board measurement (cited: #4 §3b, C-4); which other steps are journaled is not decided here.
- **Amount**: a quantity of one budget axis. **Spend** of a run: the amounts its journaled steps consumed. This record names **no axis, no unit and no party that measures**.
- **Identity**: what makes two calls the same step (decision 3). **Start line**, **end line**: the two lines of a step. A step is **open** when the log holds its start line and no end line, and **ended** when it holds its end line.
- **Fold**: the computation of decision 6 over lines of the log. **Spend view**: its result — a total per axis, the position it was folded to, and the open steps.

### 2. Two lines around a journaled step

- A journaled step leaves **a start line, complete before the step begins to consume the resource, and an end line, appended as soon as its outcome exists** (the second half is cited: #4 §3b, ADR-0006 decision 7).
- Both are appended by the **tool layer** and never by an agent (cited: ADR-0004 decision 4; #4 roster revision, item 3). Whether the appending part of the tool layer is a hook or the code below the fronts is the rest of OD-18 and is not chosen here.
- **Why not an end line only** (ADR-0006 decision 7 as it stands). A process that dies during the step leaves nothing in the log. The resumed turn runs the step again, and the first execution's spend is neither known nor visible: the failure of #7 G4 is moved from the marker into the tool call, and the budget is under-counted silently. A start line turns it into a state the log shows.
- **The opposite failure is accepted, not removed.** A death after the start line and before anything was consumed leaves an open step that spent nothing, and the log cannot tell it from one that ran. An open step therefore means "may have run; outcome and amount unknown" (decision 4). An uncertainty that is visible was preferred to a repetition that is not.
- No form closes the window between the outcome and the completed end line; how wide it is depends on where the append is placed (rest of OD-18).

### 3. Identity, the two kinds and the repeated call

| `kind` | Envelope numbers | Members of `data` (exactly these) |
|---|---|---|
| `step_started` | those of `round`, `candidate`, `attempt` the step is about (ADR-0006 decision 3) | `step`, `execution` |
| `step_ended` | the same as on its start line | `step`, `execution`, `spend`, and exactly one of `result` and `failure` |

- **Identity** = the envelope numbers of the line together with `step` and `execution`. `step` is a *name* (ADR-0001) that says which step it is; this record lists no value, and the name of the board measurement belongs to its tool contract. `execution` is an *integer* ≥ 1 that counts the executions of that step for that target; it is 1 unless a decision outside this record asked for a further execution.
- The identity is carried **in `data`**; the envelope is unchanged and stays at version 1 (a new kind does not raise it — ADR-0006 decision 8).
- The identity is **given by the caller** and can be derived from files alone. The tool layer does not generate it, and it does not come from a clock or a random source: a turn that repeats a call after a process death presents the same identity. How a request carries it is the tool's contract (PLAN P1-1).
- `result` is the result object of the call itself, a result that reports a failed experiment included (cited: ADR-0006 decision 7, ADR-0010 decision 4). `failure` holds the `kind` and `message` of the tool failure when the step ended without an outcome. `spend` is decision 7.
- **The repeated call.** Before a journaled step starts, the tool layer establishes the state of its identity from the log, and then:
  - **no line** — it appends the start line, runs the step and appends the end line;
  - **ended** — it does not run the step, and nothing is appended. The call returns what the end line holds: the `result`, or the same tool failure again when the line holds `failure`;
  - **open** — it does not run the step. The call is a tool failure, since no outcome is established, and reports that the step is open.
- **An identity is never started twice.** Running the step again is a new identity with a higher `execution`; whether and when that is done is not this record's (OD-10, the retry part of OD-17).
- The outcome of a call thereby depends on the data plane only and on nothing a server process kept (ADR-0010 decision 7). An observation for the rest of OD-18, not a choice: the rule acts before the step runs and settles what the call returns, so a part that runs only after a call cannot carry it out alone.
- These are the only kinds this record names. Every other kind and payload, and how a later change in the `data` of these two is told apart, stays open (OD-8 sub-question ⑧).

### 4. What a resumed turn may conclude

| State of the identity | Known | Not known | What the turn may do |
|---|---|---|---|
| no line | The step did not start under this identity, and no amount is recorded for it | — (within the limits of decision 9) | Run it |
| open | The start line was completed: the tool layer was about to begin | Whether the resource was consumed, how much, and whether an outcome existed | **Neither skip nor run it under this identity** |
| ended | What the end line holds — the `result`, or the `failure` with which the step ended without an outcome — and its amounts | — | Skip it. With a `result`, take it from the line; with a `failure`, the step is over without an outcome and is not run again under this identity |

- For an open step this record chooses **no recovery** — a further execution, waiting, giving up or asking the user are OD-10 and the retry part of OD-17. What the journal guarantees to whoever decides: the step is visible as open, no amount is counted for it, and the tool layer does not run that identity again. What follows a step that ended with a `failure` — a further execution or not — is left to the same places.
- Who writes the result file of an attempt from an end line on resume stays open, as ADR-0006 decision 7 left it (PLAN P1-8, OD-23).

### 5. The `phase` marker

- The marker stays (cited: #4 §3b). It says where a round stands and thereby which identity a resumed turn looks up.
- **For a journaled step the log is authoritative.** A marker that is behind the log — the death between the end line and the marker update, the case of #7 G4 — is corrected by the log: the step is ended and is skipped. A marker that says a journaled step is done while the log holds no end line is wrong: the step is not done, and the disagreement is reported.
- This narrows the sentence of #4 §3b that a fresh turn reads `phase` and skips finished expensive substeps: the marker is read first, and for a journaled step the log decides. For substeps that are not journaled steps the log says nothing, and neither does this record.
- The values of the marker and the definition of the member are not decided here (PLAN P1-8).

### 6. Accounting of the spend — the resolution of #8 M7

- **The authoritative record of an amount spent is the `spend` of a complete `step_ended` line.** For the accounting, an amount has been spent exactly when such a line holds it.
- **Fold**: over a sequence of lines in their order, the sum per axis of every `spend`, and the set of identities that have a start line and no end line. The fold never drops an amount: an end line is counted whatever else the log holds for its identity.
- **`budget_spent` in `STATE.json` is not a record of its own**, as far as amounts accounted through the log are concerned. For them it is the stored spend view of a prefix of the log: the totals, the **position** — the number of complete lines folded, which is stable because a complete line keeps its line number (cited: ADR-0006 decisions 4 and 5) — and the open steps at that position. The form of these members is PLAN P1-8. Where the running value of an axis that is not accounted through the log is kept (decision 7) is not decided here.
- **The snapshot rule.**
  - *When*: the stored view is taken when a round ends, in the write of `STATE.json` that the commit of the round takes (cited: #4 §3c updates `budget_spent` there). A run starts with the empty view at position 0. The stored view does not move in between.
  - *Where*: in `STATE.json`, and nowhere else.
  - *Replay*: at any moment, the current view is the stored view folded further over the **tail**, the complete lines after the position.
  - *Bound*: the tail holds what was appended since the last round ended — the lines of the round in progress and late lines about earlier rounds. The number of lines that are parsed and folded therefore does not grow with the number of rounds. This record gives no number for it: the limits on what one round does are OD-19. The bound is on lines interpreted, not on bytes passed over: with a line count alone, a reader reaches the position by counting line feeds from the start of the file. The byte offset at which the folded prefix ends is as stable as the line number (ADR-0006 decision 5); whether the stored view holds it as well, so that a reader can seek, is PLAN P1-8.
  - *Disagreement*: the log is authoritative. A fold from the first line is always allowed and is never required at the entry of a turn. When its result for the stored prefix differs from the stored view, the difference is reported (NFR-2) and the result of the fold is the one used; the stored view is corrected by the next write at a round end and does not move before it. A position beyond the end of the log is an error of the kind of a damaged line (ADR-0006 decision 6): the stored view is not used, the error is reported and not repaired by the reader, and what was committed is recovered from the history of the data repository. An end line whose identity is not open — a second end line, or one without a start line — is counted and reported.
- **Why this is within #4 §1.** The entry point is still the one small `STATE.json`. The log is one file at a fixed path of the run and not a directory, and what is interpreted of it at the entry of a turn is bounded by one round (see *Bound*). The fold is a deterministic computation of the tool layer: a turn does not obtain a total by loading the log into its context. Which function folds, and how the result reaches the Round-Manager as the only writer of `STATE.json`, is PLAN P1-8 and OD-23.
- A committed `STATE.json` never names a position beyond the log of the same commit; this holds whenever a commit takes both files from the working tree as they are.
- **The lookup of decision 3 has the same bound for a step about the round in progress**: its lines were appended after the previous round ended, so the tail alone decides its state. A step about an earlier round or about the run as a whole needs lines before the position (sub-question ①).

### 7. What an end line holds for the accounting

- **The amounts stand on the end line itself**, next to the outcome and in the same append, so no atomicity between two writes is needed (ADR-0006 decision 10).
- `spend` is an object from an axis *name* to a non-negative *integer*, possibly empty. It states every amount the step consumed of the axes that are accounted through the log. From where the tool layer has an amount belongs to the tool's contract and to the definition of the axis.
- **An amount is an exact integer** in the unit of its axis, so that a sum is the same however the lines are grouped: the stored view folded over the tail equals the fold from the first line. The unit is the axis definition's.
- **A step that ended without an outcome has spent as well**: an end line with `failure` carries `spend` like any other.
- **An open step has no recorded amount, and none is invented.** A total is therefore a lower bound, and the spend view lists the open steps so that whoever compares a total with a budget knows it. How an unknown amount is weighed against a budget is OD-19. An end line appended later for an open identity — when whoever recovers has established the outcome or the amounts (OD-10) — ends the step, and its amounts are counted from then on.
- Whether a given axis is accounted through the log at all is not decided here: a count of rounds or an elapsed time can be obtained from other records (FR-3, OD-2, #5 A-8, OD-19).

### 8. Rebuilding

- **Derivable from the log alone**: the spend view, and for every identity its state and, when it ended, its outcome.
- **Not spoken of**: `next_action`, `best_ref`, gate status, the round pointer, the `phase` marker beyond decision 5, the lock.
- "The whole `STATE.json` is a view that can be rebuilt" (#7 G4) is **neither adopted nor rejected**. It would need every change of those members to be an event, and no such kind exists; #4 §1 persists `next_action` in `STATE.json` as its first defence.

### 9. Limits

- **Two turns at once**: both can find no line and both start the step. The fold then counts both end lines and reports the identity; preventing it is the lock (rest of OD-17).
- **Machine loss before the commit** (#5 A-3): the lines are lost with their amounts although the resource was consumed. After the restore the total is lower than the truth and the step runs again.
- **A tool that spends without writing the lines**: the accounting does not see it (ADR-0006 decision 10: no completeness). For which tools the lines are written is each tool's contract (PLAN P1-1); forcing it is the rest of OD-18.
- **A caller that changes the identity**: the rule of decision 3 holds for a call that presents the same identity. A caller — an agent — that raises `execution` by itself runs an open or an ended step again, and this record does not stop it: who may ask for a further execution, and what checks it, is the retry part of OD-17 and the rest of OD-18 (#7 G4: retries must not be left to the model).
- **An amount is what the tool layer wrote**; nothing verifies it.
- **The clock**: `time` is used for neither the order, the identity nor an amount.
- **The accounting stops nothing**: reaching or passing a budget has no effect by this record (OD-19).

### Example

Synthetic values. `example_step`, `example_axis` and `example_member` are placeholders: this record proposes no step name, no axis and no result member.

```json
{"schema_version": 1, "time": "2026-01-01T00:00:00Z", "kind": "step_started", "round": 3, "candidate": 2, "attempt": 1, "data": {"step": "example_step", "execution": 1}}
{"schema_version": 1, "time": "2026-01-01T00:04:10Z", "kind": "step_ended", "round": 3, "candidate": 2, "attempt": 1, "data": {"step": "example_step", "execution": 1, "spend": {"example_axis": 7}, "result": {"example_member": 1}}}
```

**The three death points** (one turn at a time, no machine loss):

| The process dies | State on resume | Is the step repeated? | Is its spend counted once? |
|---|---|---|---|
| before the start line is complete (a torn tail included) | no line | It runs for the first time; nothing was consumed | Yes, when it ends |
| after the start line and before the end line is complete — during the step, or between the measurement and its record | open | Not under this identity. A further execution is someone's explicit decision (OD-10) | Not counted and shown as unknown; never counted twice. The outcome, if one existed, is lost |
| after the end line and before the marker update, the result file or the commit of the round | ended | No: skipped, with the outcome taken from the line | Yes: the line is in the tail until the round ends and in the stored view afterwards |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | A start line, and the `phase` marker instead of an end line | The marker is written by an agent, later, in another file; nothing makes that write atomic with the outcome (#7 G4). |
| 3 | The names `intent` and `result` of the proposal | A step that ended in a tool failure would be recorded by a line called `result` that holds no result in the sense of ADR-0010. |
| 3 | The identity as a hash of the request | A deliberate second measurement with the same request would be taken for a repetition; the members of a request are not fixed; a hash is not readable in an audit. |
| 3 | The identity as a token the tool layer generates | A fresh turn could not present it again: recognising the repeated call is the purpose. |
| 3 | The identity as an envelope member | A new envelope version (ADR-0006 decision 8) for something only two kinds need. |
| 3 | No `execution`: one execution per step and target | A decision to run an open step again would have no identity to run under, since lines are never edited. |
| 3 | The tool layer runs an open step again | That is a retry policy, and it could spend twice without anybody having decided so. |
| 5 | The marker is authoritative, or the marker is dropped | The first is the checkpoint defect of #7 G4: a death between the end line and the marker update repeats the step. The second contradicts #4 §3b, and the log says nothing about substeps that are not journaled. |
| 6 | The stored value is authoritative and is raised at every spend | `STATE.json` has one writer, which is not the tool layer, and no write is atomic with the line: the spend of a dead round would be lost (#7 G4). |
| 6 | No stored value; a fold from the first line at every turn | The cost at the entry of a turn grows with the run (#8 M7), and `STATE.json` alone would no longer show a total. |
| 6 | A snapshot every N rounds (the proposal as worded) | N is one more value to choose, and the tail would span N rounds; #4 §3c already writes `budget_spent` at every round end. |
| 6 | Snapshots as lines of the log | The reader would have to search the log backwards for the last one, and the entry point would not hold the total. |
| 6 | The stored view also moves inside a round | The start line of a step of the round in progress could then lie before the position, and the lookup of decision 3 would lose its bound. |
| 7 | Amounts as fractional numbers | A sum of fractions depends on the grouping, so the stored view and a full fold could differ without any error. |
| 7 | An estimate for an open step | It would invent a number; an estimate may be made by whoever enforces a budget (OD-19), not written into the record. |

## Consequences

- **The `STATE.json` record and schema of PLAN P1-8 inherit**: `budget_spent` is the stored spend view (totals, position, open steps), taken at the end of a round; `phase` is subordinate to the log for a journaled step; a validator of `STATE.json` alone cannot check the view against the log. A total a resumed turn uses is never reset: it comes from the stored view and the tail (#8 M5 names that risk; enforcement stays OD-19).
- **For the first journaled tool of PLAN P1-1**: its request carries the identity; the tool layer establishes the state of the identity before the step starts, appends the two lines and states the amounts on the end line (in a hook or below the fronts — rest of OD-18); the conformance tests cover the three states of decision 4 and the three death points. Until a recovery rule exists (OD-10, the retry part of OD-17), an open step is a point the run does not pass by itself.
- **`hilclaw/events.py`** is consistent with this record and unchanged: `append` returns after the complete line is written and flushed, which is what a start line needs, and it checks no kind. Follow-ups, not edits: `read` reads the whole file, so the code slice adds a reader that starts at a line position, the fold, and the lookup of an identity.
- **Proposed wording for the integrator, once the objection window has passed** (issue bodies are not edited here). #4 §1, second defence: the one small `STATE.json` stays the entry point; its `budget_spent` is the spend recorded in `events.ndjson` folded up to the end of the last round and stored with the position; a turn folds only the lines after that position, by the tool layer; reading the log from its first line is a check and not part of the entry. #4 §3b, last bullet: a fresh turn reads `phase` to find where the round stands, and for a journaled step the log decides whether it is finished (decision 5 narrows the agreed sentence). #8 M7: `결론:` the snapshot boundary is the end of every round, the stored view lives in `STATE.json`, and the log is authoritative (ADR-0011 decision 6); `반영:` this commit.
- **Not edited and now less exact** (follow-ups): the sentence of the Open Decisions preamble in Requirements that says of ADR-0006 "OD-17은 확정되지 않았다", and the `STATE.json` row of the path table of ADR-0004 ("OD-17 (lock, budget — #8 M7)"). No sentence of UsageCases became false.
- **A-13 reading**: document mode; no code, dependency or schema file changes. This record is a first definition of rules about what is authoritative and what is derived; it writes no member table of `STATE.json`.

## Boundaries (not decided here)

- **The rest of OD-17**: `lock{owner, heartbeat}`, fencing by a compare-and-swap push, the declarative retry policy per tool. Board failure, recovery and reservation, and everything that is done about an open step (OD-10, #5 B-2).
- **Budget enforcement**: stopping the next spend, per-round and per-coder caps, the single ledger across nested `claude -p`, the no-progress circuit breaker (OD-19, #8 M5). The token element and who counts it (#5 A-8, NFR-5). HW quota as an axis (OD-2). Which axes exist, their units and who measures (FR-3). Gates, and "budget 50 %" as a gate (OD-3 / #5 A-5 — owner-only).
- **Other files**: the member table of `STATE.json` and of `instance.json`; the values of `phase`, `next_action` and `best_ref` (OD-20); the result files of an attempt (PLAN P1-8). Reading lines of another version (OD-11).
- **Tools**: which steps other than the board measurement are journaled; the request and result members of any tool and the values of `step` (PLAN P1-1); whether the append sits in a hook or below the fronts (rest of OD-18, PLAN P2-4); which agent may cause it (OD-23).
- The isolation means (OD-8 candidates, OD-14); when the data repository is committed or pushed beyond #5 A-3 and which step commits; promotion to `db/`. How a branch or a continuation of a run (FR-6) relates to the spend of the run it starts from (with OD-8 sub-question ①, where a pointer is added).
- **Owner-only (DRIVER §9)**: OD-3, OD-25, C-6, the #5 A and B items.
- **Sub-questions this record raises** (registered under OD-17): ① a journaled step about an earlier round or about the run as a whole — a later re-measurement, for example — has lines before the stored position, so its lookup reads the log from the first line; whether such steps exist and whether they need an index (with OD-13 sub-question ①, OD-20). ② An ended step whose amount the tool layer cannot state, and how a recorded amount is corrected, since lines are never edited. ③ Whether and when the stored view is checked against a fold from the first line, and by whom (with PLAN P1-8, OD-23).
- Code, tests, a JSON Schema file, CI, and any change to the `HIL-Claw-data` repository.

## References

- [Requirements](../Requirements.md): FR-1, FR-3, FR-6, FR-10, FR-13, NFR-1, NFR-2, NFR-5, C-2, C-4; register rows OD-2, OD-3, OD-8, OD-10, OD-11, OD-17, OD-18, OD-19, OD-20, OD-23.
- [OpenDecisionProposals OD-17](../OpenDecisionProposals.md#od-17), [OD-8](../OpenDecisionProposals.md#od-8), [OD-18](../OpenDecisionProposals.md#od-18), [OD-19](../OpenDecisionProposals.md#od-19); [StandardScenarios](../StandardScenarios.md) S2, S3, S8; [UsageCases](../UsageCases.md) UC-3, UC-4.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format; *name*, *integer*); [ADR-0002](ADR-0002-od6-codegen-spec.md) (`id.round`, `id.candidate`, `id.attempt`); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 2, 4, 10); [ADR-0006](ADR-0006-od8-events-log.md) (decisions 3 to 10); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decisions 4, 6, 7).
- #4 body §1, §2e, §3b, §3c; roster revision https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5138366881 ; the durability proposals https://github.com/myungjoo/HIL-Claw/issues/4#issuecomment-5139248800 (a proposal, not a decision) ; #7 body §5 G4 ; #8 M5, M7.
- #5 A-3 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5537233759 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-5, A-8, B-2.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P1-8, P2-4; `hilclaw/events.py`, `hilclaw/layout.py`, `hilclaw/tools.py`; task T-0040.
