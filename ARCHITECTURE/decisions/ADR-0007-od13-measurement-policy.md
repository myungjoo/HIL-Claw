# ADR-0007: Measurement and noise policy for the timing of one attempt, with initial values (P1 minimum of OD-13)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes the **P1 minimum** of OD-13 (Open Decisions register in [Requirements](../Requirements.md)): for the timing measurement of one attempt, how many repeats are taken, which number stands for them, that the raw samples are kept, what is done about warm-up, and the rule by which two measurements are called different — the "OD-13 초기값" of PLAN P1-3. What stays open of OD-13: the paired, interleaved re-measurement of an incumbent, steady-state detection, session hygiene, every value for a simulator or a board beyond an initial value, and what is done with a measurement marked "not converged" (see Boundaries).
- It refers to [ADR-0003](ADR-0003-od16-harness-calibration.md) (calibration covers the correctness verdict only; no defence of the timing is adopted) and to [ADR-0004](ADR-0004-od8-data-plane-layout.md) (the per-attempt result files); the objection windows of both run until 2026-10-14. If either is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- NFR-3 asks that the variance of a performance measurement is taken into account "by repeated measurement / confidence intervals" and leaves the policy to OD-13. S9 step 3 adds that a difference inside the noise is judged "not an improvement".
- OD-13 lists five questions: how the number of repeats is decided, the statistic of a judgement, when a difference counts as an improvement, whether raw samples are kept, and warm-up / steady state. The registered proposal (#7 §5 G2, [OpenDecisionProposals OD-13](../OpenDecisionProposals.md#od-13)) answers them: adaptive repeats (stop when the coefficient of variation is below 5 %, n in [5, 30]); a trimmed mean, never the minimum; paired interleaved measurement and a bootstrap 95 % interval of the ratio that must lie wholly beyond 1 + δ, δ = 2 %; raw per-repeat vectors stored; no fixed warm-up, steady-state detection and labelling instead; session hygiene. This record relies on the summary in #7; the works it names (AdaTune, AutoTVM, MLPerf, MetaSchedule) were not read for it.
- Owner input, fixed: for the initial runs "measurement repeats adaptive per OD-13 with an initial upper bound of 10"; one call of a first GEMM takes about 0.1 s and a round tens of seconds of hardware time (#5 B-4). The first backend is `cpu_standin`, a compiled C kernel on the local PC, OpenMP and SIMD allowed (#5 A-7, C-7). Board time is expensive and shared (C-4).
- Timing is done by the verification harness, one sub-module of the tool package, whose P1 version is the source commit hash recorded for the instance (FR-9, #5 A-12; confirmed part of OD-11).
- Waiting for this record: PLAN P1-3 ("반복 타이밍", "OD-13 초기값") and P1-2 ("타이밍 수집"); the content of `sim.json` and `board.json` (ADR-0004: "Content: OD-13"); the members of a spec's `profile` (ADR-0002); the payload of a measurement event (ADR-0006).
- Not available as inputs, and not used below: the target quantity and the order "better than" (OD-1, #5 A-4), the board farm and the simulator (#5 B-2, B-3), the oracle and the tolerance (#5 B-7).

## Decision

### 1. Scope and terms

- A **measurement** is one uninterrupted sequence of repeats of one built attempt at one execution point. A **repeat** is one timed execution inside it. A **sample** is the one scalar a repeat yields: the value of **the measured quantity** for that repeat.
- The policy is about the sequence of samples only. It chooses **neither the quantity nor its direction** (OD-1); how the quantity is obtained from the timed interval (the time itself, or a rate derived from it) goes with that choice. The rules below use ratios, so they assume that every sample is a positive finite number on a ratio scale; a quantity for which that does not hold is outside this policy.
- It applies now to the `cpu_standin` execution point. For a simulator and a board the same rules and values are **initial values only**: nothing is known of either (#5 B-2, B-3), and they are revisited when it is.

### 2. What a sample covers

- **Inside** the timed interval: the execution of the kernel on operands that are already prepared, and nothing else that the harness can keep out.
- **Outside**: starting and loading the process, building, allocating and generating the inputs, computing the reference, comparing outputs, and recording. A time that includes any of these is not a sample.
- How many calls of the kernel one repeat times is the harness design (PLAN P1-3); it is the same for every repeat of a measurement. The clock, the mechanism that keeps the interval clean and the calling convention of a kernel are not decided here.

### 3. Raw samples are kept

- **Every sample of a measurement is kept, in the order taken.** The summary of decision 5 and the verdict of decision 7 are derived values; a scalar alone is never the record. A judgement can then be redone later with another rule (#7 G2).
- Leaving a sample out of a computation never removes it from the record: a sample the trim of decision 5 leaves out stays, at its position. A rule adopted later that sets samples aside (a steady-state label, the samples taken while throttling of the proposal) labels them under this policy and leaves them in the record.
- This is a requirement on the result files of ADR-0004 that hold a measurement: they must be able to hold the whole ordered sequence and the mark of decision 4. **No field is named here**; the schema is PLAN P1-8 and its code tasks.

### 4. Number of repeats

- After each repeat from the lower bound on, the spread of **all samples taken so far** is computed as the coefficient of variation, CV = s / m, with m the arithmetic mean and s the sample standard deviation (divisor n − 1).
- The measurement **stops** at the first n with n ≥ `n_min` and CV < `cv_max` (converged), or at n = `n_max` (the upper bound). Initial values: `n_min` = 5, `cv_max` = 5 %, `n_max` = 10.
- A measurement that reaches `n_max` without CV < `cv_max` is **usable and marked "not converged"**. It keeps its samples and its summary, and it enters decision 7 like any other: its spread widens the interval there, so it is rarely called different from anything. What else a consumer does with the mark (whether such a measurement may stand as a best or a baseline) is not decided here.
- A run that ends with fewer than `n_min` samples (crash, time limit) is not a measurement under this policy: it has no summary and enters no judgement. What is kept of it and what happens next is OD-10 and OD-14.
- Samples of two measurements are never pooled into one.

### 5. Summary statistic

- The one number that stands for a measurement is the **trimmed mean**: sort the samples, leave out the one lowest and the one highest, take the arithmetic mean of the rest (`trim` = 1 at each end). It is computed on all samples of the measurement, converged or not.
- At the smallest measurement, n = 5, it is the mean of the middle three. As a function it is defined wherever the trim leaves at least one value, that is for n ≥ 3; this is its domain only (the function is also applied to the replicates of decision 7, which are not measurements). Under the policy a summary exists only for a measurement, that is for n ≥ `n_min` (decision 4).
- **Ruled out as the summary: either extreme** (the minimum and the maximum). The proposal rules out the minimum of a time; as the direction is not chosen here, the same holds for the other end. An extreme is the single most favourable or least favourable repeat, not what a run of the kernel yields.

### 6. Warm-up and steady state

- P1 does **nothing special with the first repeats**: every timed repeat is a sample, is kept and enters decisions 4 and 5. No fixed number of samples is discarded, and no number of warm-up repeats is a parameter of this policy.
- No sample is labelled in P1. A label needs a detection rule, and a changepoint detection over at most 10 samples has no basis; because the order is kept (decision 3), a later rule can label the stored samples without a new measurement.
- Whether the harness executes the kernel before the first timed repeat is its design (PLAN P1-3). Such an execution is not a repeat and yields no sample.

### 7. Judging a difference

The rule is fixed for **two given measurements of the same quantity**, A with samples x (n_A) and B with samples y (n_B). It does not ask how the two came to exist.

1. Draw `resamples` = 2000 bootstrap replicates. For each, draw n_A values from x and n_B values from y, independently and with replacement, and compute the ratio r = T(y*) / T(x*), with T the trimmed mean of decision 5.
2. Sort the ratios, r(1) ≤ … ≤ r(R). The `confidence` = 95 % interval is [r(⌊0.025·R⌋ + 1), r(⌈0.975·R⌉)]; for R = 2000 that is [r(51), r(1950)].
3. A and B are **different** if the whole interval lies above 1 + `delta`, or the whole interval lies below 1 / (1 + `delta`), with `delta` = 2 %. Otherwise they are **not different**.

- The rule is symmetric in form (this record's own choice; the proposal states the one bound 1 + δ): the ranks and the two bounds are chosen so that, on the same replicates, exchanging A and B turns every ratio into its reciprocal and gives the same verdict. With a fixed seed (decision 9) the exchanged call may draw other replicates, so for a pair whose interval ends close to a bound the two orders can disagree. The verdict belongs to the ordered pair (A, B); the code task must not assume more.
- "Not different" is the "noise range" of S9 step 3: such a pair is never an improvement, whichever direction counts as better. Whether a pair that *is* different is an improvement or a regression is the direction of the quantity (OD-1); "better" is not defined here.
- **The paired, interleaved re-measurement of the incumbent is not part of the P1 minimum.** It needs the incumbent to be runnable again in the session of the candidate (what is archived of it: OD-20; which baseline: OD-28; the forced re-measurement: OD-11 proposal) and it multiplies hardware time (C-4). The rule above therefore takes the two sample sets as given and resamples them independently. A drift between the two measurements is not cancelled by it (decision 10).

### 8. Parameters and identification

| Parameter | Initial value | Source | Constant or per instance |
|---|---|---|---|
| `n_min`, lower bound of repeats | 5 | cited: #7 §5 G2 | constant of the policy |
| `n_max`, upper bound of repeats | 10 | cited: owner, #5 B-4 (the proposal's 30 is not taken) | **per instance**, default 10, never below `n_min` |
| `cv_max`, stopping threshold on the CV | 5 % | cited: #7 §5 G2 | constant |
| Spread measure | CV with the n − 1 standard deviation, over all samples so far | CV cited: #7 §5 G2, which states it for throughput — applying it to the samples of whatever quantity is measured, the divisor and "all samples" are this record's | constant |
| `trim`, samples left out at each end | 1 | cited: #7 §5 G2 (`sorted(costs)[1:-1]`) | constant |
| `delta`, margin of the difference rule | 2 % | cited: #7 §5 G2 | constant |
| `confidence`, level of the interval | 95 % | cited: #7 §5 G2 | constant |
| `resamples` | 2000 | this record's own initial value | constant |
| Interval form | percentile, with the ranks of decision 7; independent resampling of the two sets; two-sided bounds 1 + `delta` and 1 / (1 + `delta`) | bootstrap interval of the ratio and the bound 1 + δ cited: #7 §5 G2; the rest is this record's own | constant |
| Resampling seed | fixed (decision 9) | this record's own | constant |

- The names in the first column are names of this record, not fields of any file.
- `n_max` is the one value an instance may set: it is the cost of a measurement (C-4), and the owner lists it among the initial run caps next to N and the round budget, which are instance parameters. It is then part of what the instance was started with and is recorded with it (no field named; PLAN P1-8).
- The constants live in the harness source. A result is traced to the policy that produced it through the source commit hash of the instance, the confirmed part of OD-11; a change of a constant is a change of the source. Nothing more of OD-11 is decided.

### 9. Reproducible judgement

- The verdict of decision 7 is a **function of the ordered pair of the two ordered sample sequences and the parameters only**. The resampling generator is seeded with a fixed constant of the policy: no clock, no entropy of the machine, no seed supplied by a caller. The same samples give the same verdict again (NFR-2).
- The generator and the value of the seed are chosen by the code task and identified by the source commit hash, like the other constants. A judgement redone with another version may draw other replicates; what is kept is the samples, and a stored verdict is derived from them.
- This seed draws no input of a kernel and nothing depends on hiding it. It is unrelated to the run-time seeds of verification inputs, which never exist as files (OD-16).

### 10. Limits

- **No protection against forged timing.** A kernel that caches across repeats or moves its work out of the timed interval (threat B ⑷ ⑸) yields clean, converged samples. No defence is adopted (ADR-0003; rest of OD-16).
- **No board health and no fault handling**: a hang, a crash or a reservation conflict is not noise (OD-10).
- **No comparability across sessions, machines or harness versions**: the rule calls two sample sets different; it does not show that the kernels differ rather than the conditions (OD-11, and the pairing left open in decision 7).
- With 5 to 10 samples the bootstrap interval is approximate, and one slow repeat keeps the CV high although the trimmed mean is unaffected by it; such a measurement runs to `n_max` and is marked. **All values are initial values**, to be revised with data from the first runs.

### Worked example (synthetic values, no unit, no direction)

| Measurement | Samples in the order taken | Stops at | CV there | Trimmed mean |
|---|---|---|---|---|
| A | 104, 99, 101, 100, 102 | n = 5, converged | 1.9 % | (100 + 101 + 102) / 3 = 101.0 |
| B | 93, 90, 91, 89, 92 | n = 5, converged | 1.7 % | 91.0 |
| C | 130, 100, 96, 104, 98, 101, 97, 103, 99, 102 | n = 10, **not converged** | 13.2 % at n = 5, 9.5 % at n = 10 | (97 + … + 104) / 8 = 100.5 |
| D | 100, 97, 99, 101, 98 | n = 5, converged | 1.6 % | 99.0 |

| Pair | Ratio of the summaries | 95 % interval (about) | Verdict (bounds 1.02 and 1 / 1.02 = 0.980) |
|---|---|---|---|
| B / A | 0.901 | [0.88, 0.92] | different: wholly below 0.980 |
| D / A | 0.9802 | [0.95, 1.00] | not different: the ratio itself is below 0.9804, the interval is not wholly below it |
| C / A | 0.995 | [0.97, 1.08] | not different |

The second digit of an interval bound depends on the generator and the seed, which the code task fixes; the table is not a test vector for them.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The wall-clock time of the whole process as the sample | It includes the start-up of the process and whatever the process does besides the kernel, which are not the kernel and vary on their own (T-0019 Result). |
| 3 | Keep the summary and an interval only | A judgement could not be redone when a value or a rule of this record is revised (#7 G2), and all values here are initial. |
| 4 | A fixed number of repeats | The noise differs per hardware and workload (#7 G2), and the owner asks for adaptive repeats. |
| 4 | Upper bound 30 (the proposal) | The owner's statement holds for the initial runs (#5 B-4). |
| 4 | The CV of the trimmed samples as the stopping measure | At n = 5 it is the spread of three middle values, nearly always small: the rule would stop at the lower bound and no longer adapt. |
| 4 | A measurement that does not converge is unusable | It would have to be taken again, which costs hardware time (C-4) and needs a retry policy (OD-10); the interval of decision 7 already keeps a noisy measurement from being called different. |
| 5 | The median | Uses one or two samples of five; the proposal's trimmed mean uses three and is as robust to one outlier. |
| 5 | The plain mean | One slow repeat moves it; with at most 10 samples that is the common case. |
| 6 | Discard the first k samples | A fixed warm-up is what the proposal rejects, and a discarded sample is lost to a later rule. |
| 6 | Steady-state detection and labelling now | No basis with at most 10 samples; it stays a registered proposal. |
| 7 | Require the paired, interleaved measurement now | Needs OD-20, OD-28 and the OD-11 proposal, and hardware time (C-4). |
| 7 | Compare the two summaries with the margin `delta` only | Ignores the spread: two noisy measurements 3 % apart would be called different. NFR-3 asks for an interval. |
| 7 | A parametric interval (t-distribution) | Assumes a distribution of the trimmed mean that 5 samples cannot support; the proposal names the bootstrap. |
| 8 | Every value per instance | Each would have to be recorded per instance to trace a result, which is the per-instance pin of the OD-11 proposal, not decided. |
| 8 | `n_max` constant as well | The owner calls it an initial cap, next to instance parameters; it is the cost of a measurement. |
| 9 | A seed from the clock, or supplied by the caller | The same samples could give two verdicts (NFR-2). |

## Consequences

- `hilclaw/local_run.py` is unchanged and stays correct as a runner. Its `duration_s` is the wall clock of a whole process, start-up included, so by decision 2 it **is not a sample**; the harness times the kernel itself (T-0019 follow-up (c)).
- The schemas of `sim.json` and `board.json` (PLAN P1-8) must be able to hold an ordered sequence of samples and the "not converged" mark. By decision 7 of ADR-0006 the event of an expensive result carries the result itself; for a measurement that counts as an expensive result, the result that line carries therefore includes the samples. Which measurements count as expensive stays as ADR-0006 left it, and this record adds no payload member and no event kind.
- The following code task can write three pure functions from this record: the stopping test on the samples so far, the trimmed mean, and the difference verdict of two sample sequences. They run no kernel, read no clock and write no file. Input outside the policy — fewer values than a rule needs, a value that is not a positive finite number — yields no result; whether a function rejects it or its caller must is that task's choice. Where the module lives is a judgement of that task (FR-9 puts timing in the harness sub-module).
- A measurement costs between 5 and `n_max` repeats per attempt and execution point, which stays within the "tens of seconds per round" of #5 B-4 for N = 1-2 at about 0.1 s per call, if a repeat times one call (decision 2 leaves that number to the harness).
- NFR-3 still says "구체 정책 = 미결 → OD-13". Its body is not edited by this record; a proposed wording is left as a follow-up of task T-0028.

## Boundaries (not decided here)

- **Owner-only or blocked (DRIVER §9)**: the target quantity, its unit and direction, the order "better than", multi-objective handling, and with them whether `delta` becomes an instance parameter (OD-1, #5 A-4); the oracle and the tolerance (#5 B-7; PLAN P1-3 "오너 확정 필요"); the board farm and the simulator (#5 B-2, B-3); OD-3.
- **Rest of OD-13** (registered proposals and the sub-questions this record raises): the paired, interleaved re-measurement of an incumbent and a paired form of the rule (adopting it also revises the "uninterrupted sequence" in the definition of a measurement, decision 1); steady-state detection and labelling; session hygiene on a board (clock and power mode, temperature, firmware and driver records, randomised candidate order, samples taken while throttling); the values for a simulator and a board, including whether a deterministic simulator needs repeats at all; what a consumer does with a "not converged" measurement.
- **The design of the harness (PLAN P1-3)**: the timer and the clock, how many kernel calls a repeat times, whether repeats reuse the same inputs, an execution before the first repeat, the kernel calling convention, and the order of verification and timing. Sandbox time limits are OD-14.
- **OD-16**: defences of the timing against a degenerate kernel, and whether the timing side gets a calibration (the sub-question ADR-0003 raised, registered as ③ under OD-16).
- **OD-11**: the measurement-contract pin per instance and the forced re-measurement of an incumbent. **OD-28**: which baseline. **OD-20**: what is archived of a candidate. **OD-2**: the hardware-quota budget axis. **OD-10**: failure, retry and health of a board. **OD-15**, **OD-29**: promotion, rank correlation, the number of promoted candidates.
- **Fields and schemas** of `sim.json`, `board.json`, `profile.json`, `eval.json`, `instance.json`; how further records of one step for one attempt are named (OD-8 sub-question ⑤); every event kind and payload (ADR-0006 Boundaries); the content of a profile (OD-6 rest, B4).
- Code, tests, schema files, CI changes and the `HIL-Claw-data` repository: later tasks.

## References

- [Requirements](../Requirements.md): FR-1, FR-9, FR-10, NFR-2, NFR-3, C-4, C-7; register rows OD-1, OD-2, OD-8, OD-10, OD-11, OD-13, OD-14, OD-15, OD-16, OD-20, OD-28, OD-29.
- [OpenDecisionProposals OD-13](../OpenDecisionProposals.md#od-13) (registered proposal), [OD-11](../OpenDecisionProposals.md#od-11), [OD-16](../OpenDecisionProposals.md#od-16) (threat B ⑷ ⑸); [StandardScenarios](../StandardScenarios.md) S9 step 3, S10 steps 3-4; [UsageCases](../UsageCases.md) UC-E3.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0002](ADR-0002-od6-codegen-spec.md) (decision 4, `profile`); [ADR-0003](ADR-0003-od16-harness-calibration.md) (decision 3, Boundaries); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decisions 1 and 3: `sim.json`, `board.json`); [ADR-0006](ADR-0006-od8-events-log.md) (decision 7, Boundaries).
- #7 body §5 G2 (https://github.com/myungjoo/HIL-Claw/issues/7); mapping of G2 to OD-13: https://github.com/myungjoo/HIL-Claw/issues/7#issuecomment-5139423949. AdaTune, AutoTVM, MLPerf and MetaSchedule are cited through #7 only.
- #5 B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, B-2, B-3, B-7.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-2, P1-3, P1-8; `hilclaw/local_run.py`; tasks T-0019, T-0028.
