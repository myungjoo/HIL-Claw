# ADR-0130: `cpu_standin` does not offer `profiler.collect`, and the `profile` step of FR-1 on `cpu_standin` is carried by the results of the run tools (the rest of OD-18 sub-question ⑦ for `cpu_standin`)

## Status

- **Accepted on 2026-10-20** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer.
- **Two kinds of content.** The **owner's decisions** are the answers to HQ-0025 of 2026-10-20 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280027094). Where this record uses one it is quoted and marked **owner**; these are not subject to the 7-day window. **Everything else is this record's own design and has not been confirmed by the owner** — among it what a call answers before the tool exists in a registry, which values of a result the owner's parenthesis names, and what follows for `profile.json` and for a spec's `profile`.
- **The owner-sentence search.** Searched: the body of #5 and those of its comments that hold no "posted by driver" marker, and the body and comments of #4, for "profil" and "프로파일". Besides the HQ-0025 answer, three owner sentences touch the point, each read for what it says and no further: #5 A-7 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402) names "profile" in the loop the stand-in exercises; #5 A-12 point 4 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596) puts "timing, profiling" in the one harness sub-module; #5 A-1 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612) counts "프로파일" among the knowledge text kept in git. None says which tool or target produces a profile.
- Closes **the rest of OD-18 sub-question ⑦ that concerns `profiler.collect`, for `cpu_standin`** (Open Decisions register in [Requirements](../Requirements.md)). [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) answered the part for `sim.run`, `board.run` and `correctness.check` and left this one: "`profiler.collect` was not asked and stays open" (its decision 2). The rule for a target that lacks a point (OD-26) stays open. **The register row of OD-18 keeps its status wording.**
- **It is not the contract of `profiler.collect`, and the tool cannot be registered from it.** No member, file, kind, `step` value or version of the data plane is added or changed. It is a record, not code: no `claude` process was started for it (D16).
- It builds on [ADR-0016](ADR-0016-od18-backend-frame.md) (decisions 2 to 5), ADR-0038 (decisions 1 and 2), [ADR-0061](ADR-0061-od18-run-tools-split.md) (decisions 1, 2, 4 and 5) and [ADR-0063](ADR-0063-od18-run-tools-result-members.md) (decisions 3 to 6, 9 and 10). If one of them is reverted, this record is revisited with it.
- The owner is notified on issue #5. For this record's own design the owner may object within 7 days of that notice; an objection creates a task that reverts those parts and the edits made with them.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- FR-10 names four HW tools, `profiler.collect` among them; FR-1 has a `profile` step after the board point (`board(최종측정) + correctness → profile → evaluate`); #5 A-7 has the stand-in exercise "codegen → compile → run → correctness → profile → evaluate → store".
- ADR-0016 decision 3: "A backend offers the operations it has; the frame requires none", and a call whose selected backend "offers no operation for the called tool" is answered with the reserved kind `not_offered`: "nothing was consumed, no line appended". It registered as sub-question ⑦ "Which of the four the `cpu_standin` backend offers".
- What the run tools return (cited): a completed run's result holds `intervals_ns` and `resolution_ns` (ADR-0063 decision 4), `shape`, `n_max` and `sample_form` (decision 5), from which the samples follow (cited: ADR-0009 decision 7, as ADR-0063 decision 5 cites it), and `memory_bytes` when the run yielded a figure (decision 6). The result holds no summary (decision 4). The members of a result file are not named (decision 10).
- What the data plane and the spec say of a profile (cited): ADR-0004 decision 1 (path table) puts `profile.json` under `measure/` as the "Result of each step for the attempt" whose content is OD-13, and its decision 3 says "a profile is collected by running the attempt's binary at an execution point (`profiler.collect`, FR-10)"; ADR-0002 decision 4 makes a spec's `feedback.attempts[].profile` "the place for the measured result and the profile summary of an attempt", an object whose members "are not listed and not validated in version 1 (B4, OD-13)"; ADR-0051 keeps them unlisted in version 2 (its Boundaries: "`profile` and `ext`: their members").
- **What the code has today** (observations; no code is bound by this record). `hilclaw.backends.HW_TOOLS` lists `profiler.collect`; `hilclaw.tools.default_registry` registers no tool of that name and no run tool; `hilclaw.tools.call` raises `UnknownToolError` for a name the registry does not hold, before any tool function runs.
- **Fixed and not re-decided.** The two answers of HQ-0025, exactly as far as they go; FR-1 and FR-10 for every target other than `cpu_standin`; #5 A-7; the HQ-0005 answer; ADR-0002, ADR-0004, ADR-0016, ADR-0038, ADR-0061 and ADR-0063 as they are.

## Decision

A sentence marked **owner** renders the HQ-0025 answer and quotes it. A value is **cited** when another source is named with it. Everything else is **this record's own**.

### 1. Scope and terms

- This record is about **the backend `cpu_standin`**: a call of a HW tool about a run whose hw_profile names `cpu_standin` as its `accelerator` (selection: cited, ADR-0016 decision 4). It is not about the mock, a simulator, a board or any other accelerator.
- The terms of ADR-0016 (HW tool, backend, operation, target, script, the moments ① to ⑦), ADR-0038 (execution point, offers, the run tools, the local configuration) and ADR-0063 (the members of a result) are used unchanged. **A profile of an attempt** is what FR-1's `profile` step yields for that attempt.

### 2. `cpu_standin` does not offer `profiler.collect`

- **Owner** (HQ-0025 (1), answer (a)): "no - on `cpu_standin` the round's profile is what `sim.run` / `board.run` already return (the timing samples and the memory figure), and a call of `profiler.collect` there answers the reserved kind `not_offered`."
- **What follows for the backend** (from the answer and ADR-0016 decisions 2 and 3). An entry of `cpu_standin` built as the answer says holds **no operation for `profiler.collect`**; it holds operations for the three tools of ADR-0038 decision 2 and for no other. No operation is added by this record.
- **What a call answers, and when.** `not_offered` is the answer of moment ④ of ADR-0016 decision 2 — "the backend is selected and the operation of the called tool is looked up" — so it answers a call of a registered tool function that has passed ① (the request is checked) and ② (the data root), and, if the tool is journaled, found no line for its identity in ③ (cited, same decision). Such a call has consumed nothing at any target and leaves no line (cited, same decision). **Today no `profiler.collect` is registered** (Context), so a call by that name is refused by the registry before any tool function runs and is not yet answered `not_offered`. When the tool is registered, its request and whether it is journaled are its contract's (Boundaries); for a run whose hw_profile names `cpu_standin`, a call that reaches ④ with a backend table that holds the `cpu_standin` entry is answered `not_offered`, whatever that contract adds (without that entry it is `no_backend`, cited: ADR-0016 decision 3).
- **Nothing here makes the tool exist.** The answer states what a call answers at `cpu_standin`; it does not ask that the tool be registered while no backend offers it, and this record does not decide it (Boundaries).

### 3. The `profile` step of FR-1 on `cpu_standin`

- **Owner** (HQ-0025 (2), answer (a)): "yes - the record of the round loop may treat the `profile` step of FR-1 on `cpu_standin` as carried out by the run tools' results, with no further step, until a target that offers `profiler.collect` exists."
- **What the owner's parenthesis names, as this record reads it.** This record reads "the round's profile" as the profiles of the round's attempts (decision 1). "The timing samples" are, in a result of the run tools, the intervals of `intervals_ns` with `resolution_ns` and `sample_form`, from which the samples follow; "the memory figure" is `memory_bytes` (cited: ADR-0063 decisions 4 to 6). The answer says the profile "is what `sim.run` / `board.run` already return", so this record reads the profile of an attempt as **the results of the run-tool calls about that attempt, as they are**, and no other source stands in. This record derives no value and computes no summary from them (ADR-0063 decision 4 keeps none in a result); whether a later record derives a summary for a spec's `profile` or for evaluation is not decided here (B4, OD-13). Which of several results of one point — several `execution` values — the profile draws on is not decided either (OD-18 sub-question ⑳; Boundaries).
- **What follows for an attempt** (this record's own, by citation). A result of a broken run holds no `intervals_ns`, no `resolution_ns` and no `memory_bytes` (cited: ADR-0063 decision 3), so such a run adds no measurement to the profile. Whether an attempt that is not promoted has a profile at all — FR-1 places the step after the board point — is the round loop's (PLAN P2-1) and is not decided here; if it has one on `cpu_standin`, only its sim-point result can stand in for it, since it has no board-point result. Two results about one attempt are two measurements whose samples "are never pooled into one" (cited: ADR-0007 decision 4, as ADR-0061 decision 2 cites it).
- **The permission is the round loop's, not this record's.** The answer lets "the record of the round loop" treat the step so; that record (PLAN P2-1) writes the procedure. This record writes no step of the loop and adds no call to it.
- **"until a target that offers `profiler.collect` exists"** is quoted as the owner's limit. What the loop does on `cpu_standin` once such a target exists is not said by the answer and is not decided here (Boundaries).

### 4. What follows for `profile.json` and for a spec's `profile`

Only as far as the answer makes it necessary.

- **`profile.json`** (ADR-0004). On `cpu_standin` no call of `profiler.collect` is carried out, so no `profile.json` is collected "by running the attempt's binary at an execution point (`profiler.collect`, FR-10)" for an attempt of a `cpu_standin` run. **Whether a `profile.json` is written for such an attempt at all, from what, and by whom is not decided here**: its content is OD-13 (cited: ADR-0004 decision 1, path table) and which agent profiles is OD-23 (cited: ADR-0004 decision 3), and the run tools' result files are not named either (cited: ADR-0063 decision 10). No path is added or removed.
- **A spec's `feedback.attempts[].profile`** (ADR-0002 decision 4). For an earlier attempt of a `cpu_standin` run that has a profile under decision 3, what goes into that place comes from the results of the run-tool calls about that attempt, since those results are the attempt's profile (decision 3). **Which of their values, in what form, and the structure of a profile summary are not decided here** (B4, OD-6, OD-13); `profile` keeps no listed member, and no spec version is raised (cited for the rule: ADR-0002 decision 7, "when `profile` or `task.objective` get defined members").

### Walk-through

One attempt of a run whose hw_profile names `cpu_standin`, in the local configuration. No request member, `step` value or file member is shown. The order of the calls and everything a caller does with an outcome are FR-1's and PLAN P2-1's.

| Place in the loop (FR-1) | The call | What it answers or what follows |
|---|---|---|
| sim step | `sim.run` | A result (ADR-0063 decision 9) |
| board step (promoted attempt) | `board.run` | A result of the same members |
| `profile` step | — (no call) | The results above are the attempt's profile (decision 3) |
| `profile` step, a caller calls `profiler.collect` anyway | `profiler.collect` | Today: refused by the registry, no such tool. Once registered: a call that reaches ④ with a table holding the `cpu_standin` entry is answered `not_offered`; nothing consumed, no line |
| the sim-point run was broken | — | The result holds no measurement; the profile has none from that run |
| a later coder call cites this attempt | (spec written) | Its `feedback.attempts[].profile` draws on the results above; which values and in what form: not decided (decision 4) |

### 5. Limits

- **The stand-in exercises no profiler.** On `cpu_standin` the loop's `profile` step is never a call, so a profile with more than timing and memory — counters, a per-section breakdown, anything a sampling profiler gives — is not exercised, and the path of a call of `profiler.collect` that reaches an operation is exercised at no real target. A test reaches `not_offered` "with a table whose mock was built without the operation of that tool" (cited: ADR-0016 decision 5 (d)).
- **The profile cannot tell a cause the timing does not show.** What the coder is told of an earlier attempt on `cpu_standin` is bounded by the members of the run tools' results (decision 4); a slowdown whose cause shows only in counters is not visible in it.
- **The answer is a starting point.** The owner's note: "this is the MVP starting point, chosen so that the loop runs end to end soon. It is not a permanent answer for `cpu_standin`" (Boundaries).

## Alternatives considered

The owner's answers are not weighed; the options of HQ-0025 that were not chosen are listed with the owner's choice as the reason.

| Point | Alternative | Why not |
|---|---|---|
| 2 | HQ-0025 (1)(b): `cpu_standin` offers `profiler.collect` with a profile taken by means the package already has | The owner chose (1)(a). |
| 2 | HQ-0025 (1)(c): it offers it with a hardware-counter or sampling profiler | The owner chose (1)(a); it would also be a new external dependency (CLAUDE.md A-13) not alike on every system of C-7. |
| 2 | HQ-0025 (1)(d): something else | The owner chose (1)(a). |
| 2 | Register a `profiler.collect` tool function now, so that a call is answered `not_offered` today | A tool function checks a request (ADR-0015 decision 2), and no record states the request, whether the tool is journaled or its `step` values; that is the tool's contract (Boundaries). |
| 3 | HQ-0025 (2)(b): the loop does a further step for the profile on `cpu_standin` | The owner chose (2)(a). |
| 3 | Read the profile as the timing summary of ADR-0007 decision 5, computed from the results | The answer says the profile "is what `sim.run` / `board.run` already return", and ADR-0063 decision 4 keeps no summary in a result; which component computes a summary is OD-13 sub-questions ① and ②. |
| 3 | Read "until a target that offers `profiler.collect` exists" as ending the permission on `cpu_standin` when that happens, and say what the loop then does | The answer names the limit and not what follows; that would be a decision the owner did not make. |
| 4 | Decide that `profile.json` of a `cpu_standin` attempt holds a copy of the run tools' results | It would give a file of the data plane a content (OD-13) and a writer (OD-23) that no record gives — a data-plane schema change (CLAUDE.md A-13). |

## Consequences

- **The code**: no change follows. The `cpu_standin` entry of a backend table holds no operation for `profiler.collect`; none is to be added (observation: no code holds a `cpu_standin` entry yet). Docstrings that become less exact: none.
- **PLAN P2-1** (the round loop) may write the `profile` step on `cpu_standin` as carried out by the results of `sim.run` and `board.run`, with no call. **PLAN P1-1**: under its completion criterion (D18), `profiler.collect` is not required, since HQ-0025 says `cpu_standin` does not offer it; P1-1 stays open on its other parts (the run tools are not yet registered).
- **The records of `profiler.collect`**: this record does not require them, and when they are written is not decided here (Boundaries); PLAN P1-1 does not require the tool (D18).
- **Provisional choices that rest on "`profiler.collect` has no contract"** stay as they are, since it still has none: ADR-0061 decision 4 (its two kinds "Not reserved, provisionally"), ADR-0067 decisions 2 and 4 and its Alternatives row for decisions 2 and 3.
- **Not edited and now less exact** (follow-ups for the integrator): ADR-0004 decision 3, the bullet on `profile.json` ("a profile is collected by running the attempt's binary at an execution point (`profiler.collect`, FR-10)" — not on `cpu_standin`); ADR-0016 decision 3 ("Which of the four the `cpu_standin` backend offers is not carried by the fixed inputs"); ADR-0038 Status ("What stays open: … `profiler.collect`, …"), its decision 2 ("`profiler.collect` was not asked and stays open") and its Consequences ("whether one for `profiler.collect` is open").
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes. The record names **no member** of a request, of a result or of a data-plane file, **no `step` value** and **no new `kind`**; it adds no member to any data-plane file and raises no version.

## Boundaries (not decided here)

- **Whether `cpu_standin` offers `profiler.collect` later.** Owner's note: "the owner may reopen whether `cpu_standin` offers `profiler.collect` once the round loop has run end to end on it. The record lists that under Boundaries and decides nothing about it."
- **The contract of `profiler.collect`**: its request, its result, whether it is journaled, its `step` values, its kinds, its operation form, its input schema and description, whether and when it is registered (also while no backend offers it), and the mock's script and offer for it (ADR-0016 decision 5 (d)).
- **The profile of any other backend**, a real simulator or board, a target on another machine (#5 B-2, B-3 — owner-only), and what the loop on `cpu_standin` does once a target that offers `profiler.collect` exists.
- **The rule for a target that lacks a point** (OD-26; StandardScenarios S1-b; the rest of OD-18 sub-question ⑦).
- **The structure of a profile summary** and the members of a spec's `profile` (B4, OD-6, OD-13); which of several results of one point (several `execution` values) the profile or a spec's `profile` draws on (OD-18 sub-question ⑳); the content and writer of `profile.json`, `sim.json` and `board.json` (OD-13, OD-23); which component computes a summary or compares measurements (OD-13 sub-questions ① and ②, OD-15, OD-29).
- **The round loop's procedure** (PLAN P2-1): the order of calls, whether an attempt that is not promoted is profiled, promotion (OD-15, OD-29), the repair bound (OD-19), triage (OD-10).
- Any change to ADR-0001 to ADR-0129, to `hilclaw/`, to tests, to CI, to any settings file, or to the `HIL-Claw-data` repository; any new external dependency.

## References

- [Requirements](../Requirements.md): FR-1, FR-10, C-7; register rows OD-6, OD-13, OD-18, OD-23, OD-26.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ⑦, ⑳); [StandardScenarios](../StandardScenarios.md) S0, S1, S1-b.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decisions 4, 7); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1, 3); [ADR-0007](ADR-0007-od13-measurement-policy.md) (decisions 4, 5); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decision 7); [ADR-0015](ADR-0015-od18-tool-contract-frame.md) (decision 2); ADR-0016 (decisions 2 to 5); ADR-0038 (decisions 1, 2; Consequences); [ADR-0051](ADR-0051-od6-spec-file-version-2.md) (Boundaries); ADR-0061 (decisions 1, 2, 4, 5); ADR-0063 (decisions 3 to 6, 9, 10); [ADR-0067](ADR-0067-od18-run-tools-admission-kinds.md) (decisions 2, 4; Alternatives).
- HQ-0025 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6280027094 · question https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6220178853 · HQ-0005 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6117798837 · #5 A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · #5 A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · #5 A-1 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5495860612 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1, P2-1; `hilclaw/backends.py`, `hilclaw/tools.py`; tasks T-0088, T-0239.
