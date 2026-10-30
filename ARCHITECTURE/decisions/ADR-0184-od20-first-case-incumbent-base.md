# ADR-0184: The incumbent carried forward in a first-case run with one candidate per round — the spec of a round ≥ 1 names the fastest attempt verified at both points as `feedback.base`, the coder call copies that attempt's source into the scratch, and the coder prompt asks for a plain baseline while there is no base (part of OD-20, rest of OD-6, part of OD-28, for the runs of ADR-0120 decision 1)

## Status

- **Accepted on 2026-10-30 by owner decision**: the owner approved the direction "carry the incumbent forward; round 0 writes a plain baseline", the spec change included, on 2026-10-30 in chat (record: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6512287389). The owner's words: "그렇게 진행".
- **Two kinds of content.** The owner decision and what an accepted record or code docstring says are **cited**, with the source named. **Everything else is this record's own**: the selection rule, the place of the copy, the failure kind and the prompt wording.
- **Why now** (cited, the #5 record above): three owner-run real runs found that no round ≥ 1 coder call starts from earlier code. The spec of ADR-0151 has no `feedback.base` and the coder gets no source, so each round rewrote the kernel from scratch and later rounds regressed (round 0 0.73 ms, rounds 1 to 4 2.0 to 2.6 ms). The round 0 coder also wrote an already optimised kernel (threads, AVX2), which left later rounds nothing to improve and added timing noise.
- **No member, file, kind, value or version of the data plane is added or changed.** `feedback.base` is a member of spec version 2 (cited: ADR-0002 decision 4 and its field table; ADR-0050 decision 6), so filling it changes no frame (CLAUDE.md A-13). `profile` stays without members, so `schema_version` stays 2 (cited: ADR-0002 decision 7, as ADR-0151 reads it). The owner's approval of a spec change is therefore not used here. The copy in the scratch and the failure kind are not data plane: the scratch is outside both checkouts and removed after the call (cited: ADR-0049 decisions 3 and 4).
- **Revises** [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md) decision 2, for its member `feedback.base`: "no `feedback.base`" becomes decision 2 of this record. Everything else of ADR-0151 stands. **Extends** [ADR-0049](ADR-0049-od8-coder-call-isolation-means.md) decision 4, which leaves "any further kind of file" to a later record, by decision 3. **Extends** [ADR-0126](ADR-0126-od23-coder-call-issuer.md) decision 3 and [ADR-0141](ADR-0141-od23-first-case-coder-run-tool.md) by one failure kind of `coder.run` (decision 3). The prompt wording is a choice ADR-0137 left to its code slice (cited: the docstring of `hilclaw/coder_runtime.py`), so decision 4 changes no decision of ADR-0137.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The open point** (cited): ADR-0002 decision 4 says `feedback.base` "names the one attempt whose source this call starts from: S0 steps 8-9 improve existing code, and after round 0 that code exists (FR-1). Which attempt the orchestrator picks is not decided, and the record of lineage is OD-20." ADR-0002 Alternative 4 rejects an *implied* best-so-far rule and embedded source. ADR-0151 left `feedback.base` out.
- **What exists** (code at `b2cf754`): `spec_feedback.attempts` reads, for each earlier attempt of candidate 1, its spec, its check lines and its standing at the sim and board points. `timings.compare` reads one attempt's measurement at `board_run_timing_v2` by the rule of ADR-0140 decision 3. `scratch.create` places only the copy of `spec.json` in the scratch. The coder prompt names only `spec.json` and `output`.

## Decision

A sentence is **cited** when a source is named with it. Every other sentence is **this record's own**.

### 1. Scope

The runs of ADR-0151 decision 1: a run of ADR-0120 decision 1 whose `instance.json` states `candidates_per_round` 1. The spec is that of the first coder call (`candidate` 1, `attempt` 1) of a round `r` ≥ 1, written by `spec.write`. The coder call is any call of `coder.run` whose spec names a `feedback.base`. Round 0's spec stays ADR-0138's and has no `feedback.base`.

### 2. `feedback.base`: the incumbent

- **Candidates.** The entries that `feedback.attempts` shows (ADR-0151 decision 2 (d)) whose standing is `"verified"` at the sim point and at the board point.
- **Measurement.** An attempt's measurement is the rule of `timings.compare` at the step `board_run_timing_v2` (cited: ADR-0140 decision 3, with ADR-0183 decision 8 for the step value). Its end lines at that step whose `result` is an admitted timing result with the `outcome` `"converged"` or `"not_converged"` must be exactly one. It must also have no end line holding a `failure`, and no start line without an end line. An attempt without a measurement is no candidate. An end line whose `result` is not admitted makes its attempt no candidate and fails nothing. A step line the journal refuses has already failed the read of the checks, as `run_file_invalid`.
- **Choice.** The candidate whose measurement has the lowest median of its `intervals`. On a tie, the earliest `(round, attempt)`. The medians are compared without comparing `contract_key` and `shape`: every attempt of one run is of the run's one `op_signature` (the run's `instance.json` states one `op_signature`).
- **Value.** `{"round", "candidate": 1, "attempt"}` of that attempt, the `ref` form of ADR-0002. With no candidate, the spec has no `feedback.base`.
- **Why the median, and `"not_converged"` too**: the median is the figure ADR-0140's comparison rests on, and a run of a small kernel may never converge (the #5 record above, F1). An attempt left out for that would make the slower converged one the base.
- **Why this is not ADR-0002 Alternative 4**: that alternative rejected a rule *implied* by an absent `base`. Here the rule is stated, and its result is written into the spec, where the lineage can be read.

### 3. The base source in the scratch

- When the spec names a `feedback.base`, `coder.run` copies the bytes of each regular file directly below that attempt's `output` (`rounds/<RRRR>/coder/candidates/<CC>/attempts/<AA>/output`, cited: ADR-0004 decision 3) into the directory `base` directly below the scratch root. Each copy keeps its name. The files are read whole, without following a link, before the scratch is made, like the spec copy (cited: ADR-0049 decision 4).
- `base` is not the place `output` (cited: ADR-0055 decision 5), so nothing of it is brought in unless the coder writes it into `output`.
- A base `output` that is no directory (a symbolic link or a junction among them) or cannot be listed, or an entry of it that is no regular file or cannot be read, fails the call with the new kind **`base_unreadable`**, after `spec_changed` in the order of ADR-0126 decision 3. Nothing is made and the runtime is not run then.

### 4. The coder prompt

The prompt of ADR-0137's runtime gains these sentences, after the rule of `output`:

- When `spec.json` names `feedback.base`, the directory `base` holds the source of that attempt, the fastest correct one so far. The coder starts from it, keeps what makes it fast, and applies the guidance techniques to it rather than starting over.
- When `spec.json` names no `feedback.base`, no correct attempt exists yet. The coder writes a plain, correct, single-threaded kernel with no hand optimisation, the baseline later rounds improve on, and learns from the failures that `feedback.attempts` reports.

The second sentence answers, for these runs, the part of OD-28 "what round 0 does beyond FR-1": round 0 writes a plain baseline. It also covers a round ≥ 1 that follows rounds with no verified attempt.

### Walk-through

An illustration with the medians of the owner's third real run, at round 3: rounds 0 to 2 are verified at both points with medians 0.73, 2.0 and 2.6 ms. `spec.write` for round 3 shows the three entries and names round 0 as `feedback.base`. `coder.run` copies round 0's `kernel.c` into `base/` of the scratch. The coder reads it, applies round 3's techniques to it, and writes the new kernel to `output/`.

## Alternatives considered

| # | Alternative | Why not |
|---|---|---|
| 1 | Let the technique-selector name the base | A choice by a model on figures a tool already has adds a failure mode and no information. The rule is deterministic and its result is written in the spec. |
| 2 | Embed the base source in the spec | Rejected by ADR-0002 Alternative 4: it duplicates files that exist in the run. |
| 3 | The latest verified attempt as base | A regressed latest attempt would carry the regression forward, which is what the real runs showed. |
| 4 | Show each attempt's measured time in `profile` | Defined members of `profile` raise `schema_version` (ADR-0002 decision 7). The owner approved a spec change, but the base alone answers the finding. Left for when the coder needs the figures. |
| 5 | A plain baseline only in round 0 | A round ≥ 1 after rounds with no verified attempt has no base either. Asking it for optimised code repeats round 0's problem. |

## Consequences

- A round ≥ 1 coder call starts from the fastest verified code of its run. The lineage of each attempt is its spec's `feedback.base`.
- The evaluator's verdicts still compare against what ADR-0119 and ADR-0140 name; this record changes no comparison.
- A coder that ignores `base/` is not detected. The prompt is the only means.
- `spec.write`'s result and request are unchanged. `coder.run` has one more failure kind.

## Boundaries (not decided here)

- The archive of candidates and `best_ref` (rest of OD-20), `best.json` (OD-20, OD-8).
- `profile` members and the spec version they need (rest of OD-6, (B4)).
- The base of a repair attempt (ADR-0002 decision 5 copies attempt 1's), of a run with N > 1, and of a resumed or branched run.
- Whether a run with no verified attempt after some rounds should end early (OD-19).

## References

- Owner decision: https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6512287389
- [ADR-0002](ADR-0002-od6-codegen-spec.md), [ADR-0004](ADR-0004-od8-data-plane-layout.md), [ADR-0049](ADR-0049-od8-coder-call-isolation-means.md), [ADR-0055](ADR-0055-od23-coder-output-form.md), [ADR-0119](ADR-0119-od28-first-case-baseline.md), [ADR-0126](ADR-0126-od23-coder-call-issuer.md), [ADR-0137](ADR-0137-od23-first-case-coder-process-start.md), [ADR-0138](ADR-0138-od6-first-case-round-zero-spec.md), [ADR-0140](ADR-0140-od16-first-case-attempt-comparison.md), [ADR-0141](ADR-0141-od23-first-case-coder-run-tool.md), [ADR-0151](ADR-0151-od6-first-case-later-round-spec.md), [ADR-0183](ADR-0183-od18-tool-result-format-v2.md)
- Code: `hilclaw/spec_feedback.py` (`feedback`), `hilclaw/spec_tool.py`, `hilclaw/scratch.py` (`create`, `base`), `hilclaw/coder_call.py`, `hilclaw/coder_tool.py`, `hilclaw/coder_runtime.py` (`PROMPT`)
