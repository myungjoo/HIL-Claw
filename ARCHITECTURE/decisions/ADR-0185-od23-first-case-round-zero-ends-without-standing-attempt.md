# ADR-0185: A round 0 whose attempt does not stand ends its round in a first-case run with one candidate per round — after a `coder.run` result with an empty `taken` or a `coder.run` failure, a check that does not verify, or any measurement report, the Round-Manager goes to the closing steps, so the next round retries with the failure as feedback and the round budget ends the run (part of OD-23 and of OD-28, for the runs of ADR-0142)

## Status

- **Accepted on 2026-10-30 by owner decision**: the owner approved the direction "a failed round 0 ends its round like a round ≥ 1 does, so the next round retries with the failure as feedback; the round budget is the terminal state" on 2026-10-30 in chat (record: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6512287389, item 3). The owner's words: "그렇게 진행".
- **Two kinds of content.** The owner decision and what an accepted record says are **cited**, with the source named. **Everything else is this record's own**: which reports still come to the stop, and the wording of the definition.
- **Why now** (cited, the #5 record above, F3): an owner-run real run whose round 0 attempt failed its check came to the stop with no `round.end`. Every later turn then failed at `spec.write` with `spec_exists`, so the run could neither retry nor end.
- **Revises** [ADR-0142](ADR-0142-od23-first-case-round-zero-after-coder-call.md) decisions 2, 3 and 6, for which reports come to the stop (decision 2 of this record). Its other decisions stand.
- **Answers**, for the runs of decision 1 only, the question [ADR-0119](ADR-0119-od28-first-case-baseline.md) decision 5 leaves open: when round 0 leaves no attempt that can stand, the run neither stops nor waits for the user. It retries in the next round, as decision 3 says, and goes on without a baseline until an attempt stands. ADR-0119 decision 5's sentence "This record does not say such a run has a baseline" stays true: no round of such a run has one until then. Nothing of [ADR-0141](ADR-0141-od23-first-case-coder-run-tool.md) decision 5 changes: `spec_exists` still comes to the stop.
- **No member, file, kind, value or version of the data plane is added or changed.** `round.end`, `run.commit` and the files they write are unchanged (cited: ADR-0135, ADR-0143). No tool changes.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What ADR-0142 fixed** (cited): in round 0, a report other than a `coder.run` result with names, a `"verified"` standing at each point and a `"converged"` or `"not_converged"` measurement comes to the stop; "Round 0 is not ended: no `round.end`". A round ≥ 1 already goes to its verdicts and closing steps after a failed attempt (cited: ADR-0172 decisions 2 to 6).
- **What the next round sees** (cited: ADR-0151 decision 2 (d)): its spec shows every earlier attempt whose sim-point standing is settled, with its failure. A round 0 attempt that failed its check is therefore shown to the round 1 coder. An attempt with no output has no check, is undetermined and is not shown.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

Round 0 of the runs of ADR-0142: a run of ADR-0120 decision 1 with `candidates_per_round` 1 that is also a run of ADR-0119 decision 1. The rule is in `orchestration/round-manager.md`.

### 2. Which round 0 reports end the round

- **Step 2 (the coder-driver).**
  - A `coder.run` result whose `taken` holds a name goes on to step 3, as before (cited: ADR-0142 decision 2).
  - A `coder.run` result with an empty `taken`, or a failure kind of `coder.run`, goes to the closing steps.
  - A failure kind of `spec.write` (`spec_exists` among them), or a report that cannot be read, still comes to the stop.
- **Steps 3 and 4 (the evaluator).** A standing other than `"verified"`, a failure kind or a report that cannot be read goes to the closing steps.
- **Step 5 (the experiment-runner).** Every report goes to the closing steps, the `outcome` `"broken"`, a failure kind and a report that cannot be read included.
- **The closing steps of round 0** are unchanged: no `case.write`, then `round.end`, then `run.commit` (cited: ADR-0142 decision 6; ADR-0133 decision 1).
- **The stop** in round 0 follows step 2 only.

### 3. What follows

- The next turn begins round 1. Its spec shows the failed round 0 attempt, when its check ran (cited: ADR-0151). Its coder gets no `feedback.base` and is asked for a plain, correct baseline (cited: [ADR-0184](ADR-0184-od20-first-case-incumbent-base.md) decision 4). That is the retry with the failure as feedback.
- When the round budget is spent, `round.end` writes `run_status` `"over"` (cited: ADR-0135 decision 4). That is the terminal state of a run that never stands.

**Why `spec.write` failures still stop.** After such a failure the round has no spec of its own, so it has no attempt that a later round could show or name: the run's files or the data root are wrong, or the round's spec already exists from an earlier turn. A `coder.run` failure, `no_container_runtime` among them, comes after the spec was written, so the attempt exists, and the next round's spec can show it when it has a check. `spec_exists` stays ADR-0141's interim rule.

**Why every step 5 report ends the round.** A round ≥ 1 does the same (cited: ADR-0172 decision 4). An attempt that stands at both points but has no measurement is no incumbent (ADR-0184 decision 2), so the next round still starts from a plain baseline.

## Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| 1 | A repair attempt in round 0 (`attempt` 2) | The repair spec, its limits and who asks for it are open (OD-19, ADR-0002 decision 5). The next round reaches the same retry with no new rule. |
| 2 | A terminal `run_status` such as `"failed"` after a round 0 failure | It is a new value of `STATE.json`, a data-plane change, and it gives up a run that a retry may still save. |
| 3 | End the round after a `spec.write` failure too | It spends the budget on rounds with no attempt. |

## Consequences

- A run whose round 0 attempt fails no longer stays stuck. Each failed round costs one round of the budget.
- A run with a round budget of 1 ends `"over"` after a failed round 0, as the owner's real runs with budget 1 would.
- The round 0 case is not written, as before (ADR-0133 decision 1). The failure is in the run's log and its spec feedback, not in `db/`.

## Boundaries (not decided here)

- Repair attempts and the limits on coder calls (OD-19).
- Whether a run should end early after several rounds with no verified attempt (OD-19).
- `spec_exists` after an interrupted turn (OD-8 ㉖ (가), OD-23 ① (가)).
- The baseline of a run whose round 0 left no attempt that can stand: which later attempt, if any, the verdicts compare against (ADR-0119 decision 5 for other runs; OD-28, OD-19, OD-10). Until an attempt stands, a comparison against round 0 has no measurement.

## References

- Owner decision: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6512287389
- [ADR-0119](ADR-0119-od28-first-case-baseline.md), [ADR-0133](ADR-0133-od23-first-case-round-promotion.md), [ADR-0135](ADR-0135-od23-first-case-round-end-write.md), [ADR-0141](ADR-0141-od23-first-case-coder-run-tool.md), [ADR-0142](ADR-0142-od23-first-case-round-zero-after-coder-call.md), [ADR-0143](ADR-0143-od8-first-case-turn-end-commit.md), [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md), [ADR-0172](ADR-0172-od23-first-case-round-one-after-coder-call.md), [ADR-0184](ADR-0184-od20-first-case-incumbent-base.md)
- Definition: `orchestration/round-manager.md` ("The round steps" 2 to 5, "The stop", "The closing steps of a round"); tests: `tests/test_turn_definition.py`, `tests/test_first_run_end_to_end.py`
