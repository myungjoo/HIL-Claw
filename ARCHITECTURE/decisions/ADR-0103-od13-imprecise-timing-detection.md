# ADR-0103: When a measurement or a run counts as taken in an environment where timing is hard or imprecise — two grounds, the measurement's own evidence and the class of the environment, either one sufficient; a run counts from its first such measurement or class finding on (part (가) of sub-question ⑪ of OD-13)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences quote the owner decision of 2026-10-15, item 3, and its "Left open" line (O1 and O2 below); they are reasons, not decisions of this record. What a requirement, an accepted record or a file of `hilclaw/` says is **cited** with its source. **Everything else is this record's own design**: the two grounds and their combination (decision 2), the measured ground and its constant (decision 3), the class ground and its input (decision 4), the finding of a run (decision 5), the moment and the reproduction (decision 6), and every weighing.
- Answers **part (가) of sub-question ⑪ of OD-13** (Open Decisions register in [Requirements](../Requirements.md)) **for the runs of [ADR-0061](ADR-0061-od18-run-tools-split.md) decision 1**: the first case's local configuration and runs whose hw_profile names the mock. For those runs, the input of the class ground is named and its producing is left to a later record (decision 4). Parts (나), (다) and (라) are not answered. It registers no sub-question. OD-13 keeps its status word.
- **Nothing changes in the data plane or in any behaviour**: no run stops, the improvement rule of [ADR-0007](ADR-0007-od13-measurement-policy.md) is unchanged, no member of any tool result is added (ADR-0063 decision 9), and no `step` value, event kind, spend axis, `schema_version` or data-plane schema is added or changed. Where and in which form the finding is kept is part (나).
- It builds on [ADR-0006](ADR-0006-od8-events-log.md) (decision 5), ADR-0007 (decisions 3, 4, 8, 9), [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decisions 4, 8, 10), ADR-0061 (decisions 1, 2) and [ADR-0063](ADR-0063-od18-run-tools-result-members.md) (decisions 2, 4, 9). **If any of them is reverted, this record is revisited with it.**
- **It is a record, not code**: the members it reads were taken from ADR-0063 and the code was not run. No compiler, container, timing run or `claude` process was started for it.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **The owner's words this record uses**, from the owner decisions of 2026-10-15 (https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913):
  - **O1** — item 3: "Timing where it is hard or imprecise (for example inside the VM of Docker Desktop on macOS or Windows/WSL, or under high noise). The run does not stop for that: it continues and optimizes on relative numbers, under the improvement rule of ADR-0007 as it stands. Every report of such numbers to the user (at the start of the run, with each result or best shown, and in the end notification) carries a warning that the absolute values are not to be trusted and that improvements may be hard to establish. Recording in the data plane that a measurement or a run was made in such an environment is approved; its form is left to a record."
  - **O2** — "Left open: how such an environment is detected (a known environment class, measured noise, or both)".
- NFR-3 records O1. OD-13 registered sub-question ⑪ with four parts; part (가) is O2. ADR-0061 Limit 3 and ADR-0063 Limit 5 leave ⑪ untouched (cited).
- **What a run of the scope produces today** (cited): a result of `sim.run` or `board.run` holds `outcome` (`"converged"`, `"not_converged"` or `"broken"`), and, exactly when the run was completed, `resolution_ns` and `intervals_ns` (ADR-0063 decisions 2, 4 and 9). `"not_converged"` means that the measurement reached `n_max` without CV < `cv_max` (ADR-0007 decision 4), and the replay over `intervals_ns` gives the `outcome` (ADR-0063 decision 4). A broken run "yields no measurement" (ADR-0009 decision 8). Nothing in a result or in the run's files says where the timing run executed: the operation carries out the timing run itself (ADR-0061 decision 2), and the container in which the owner put the build and the timing run (owner decision of 2026-10-15, item 1) is not designed yet (OD-14 sub-question ①).
- **The integrator note on OD-13** (2026-10-15) says that a factor that scales every sample cancels in the ratio judgement, but an additive overhead and a drift between measurements do not. Neither shows in the spread of one measurement.

## Decision

### 1. Scope and terms

- **Scope.** A measurement taken by a call of `sim.run` or `board.run` about one attempt of a run that ADR-0061 decision 1 covers (cited): a run whose hw_profile names `cpu_standin` in the local configuration of [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) decision 1, or names the mock; and such a run itself. At the mock the rule applies as it stands to the result the mock's script yields, so that the contract tests can exercise it (the reason of ADR-0061 decision 1).
- **Terms.** *Measurement*, *sample*, *converged* and *not converged* are those of ADR-0007; *completed* and *broken* those of ADR-0009; *result*, `outcome`, `resolution_ns` and `intervals_ns` those of ADR-0063. A measurement or a run is **found imprecise** when it counts, under this record, as taken in an environment where timing is hard or imprecise in the sense of O1. "Found imprecise" and the names of the constants below are names of this record, not members of any file.
- **What a finding does.** The finding answers the question O1 leaves to it: which numbers carry the warning and which measurement or run is marked. Under O1 it changes nothing else. The run continues, the verdicts of ADR-0007 decision 7 stay what they are, and a measurement that is found imprecise is still a measurement.

### 2. Two grounds, either one sufficient

- A measurement is found imprecise when **the measured ground** (decision 3) or **the class ground** (decision 4) holds for it. That is the owner's third option, "both" (O2), with either ground enough on its own.
- **Why both.** O1 names two kinds of examples: an environment class ("inside the VM of Docker Desktop on macOS or Windows/WSL") and a measured condition ("under high noise"). Each ground sees what the other cannot. The measured ground sees noise wherever it comes from, on every machine kind, by one rule (C-7). But it cannot see an additive overhead or a drift between measurements (the integrator note), and this record expects these to be the typical faults in a VM (an expectation, not a checked fact; Limit 2). The class ground sees the VM whether or not its noise shows in one measurement, but it cannot see a noisy host that is not a VM.
- **Why either one, and not both together.** The two grounds answer different faults, so requiring both would miss each fault the other ground cannot see. Under this record a false finding costs a warning and nothing else (decision 1). A missed finding lets the user trust numbers that O1 says are not to be trusted. **If part (다) attaches a consequence to a finding** (for example, no reuse under FR-18 or no judgement under FR-2), that weighing changes and this record is revisited with it.

### 3. The measured ground: not converged, or a coarse clock

The measured ground holds for a measurement whose result has `outcome` `"converged"` or `"not_converged"` when either of these holds:

1. **Not converged**: `outcome` is `"not_converged"`.
2. **Coarse clock**: `resolution_ns` is greater than `resolution_share_max` times the smallest entry of `intervals_ns`, with `resolution_share_max` = 1 % (in integers: 100 × `resolution_ns` > the smallest interval).

- **Why "not converged" is the noise test.** It is the only statement of high noise that the accepted policy already makes: the spread of all samples stayed at or above `cv_max` = 5 % up to `n_max` (ADR-0007 decision 4). A second noise threshold beside `cv_max` would be a second definition of "high noise" in one harness, and its value could come only from the first runs. The test adds no constant and no input, and its value is replayed from the kept intervals (ADR-0063 decision 4).
- **Why the clock test.** A coarse clock can quantise the intervals of one measurement to the same few values. Their CV is then small, and the measurement converges although each sample may be wrong by up to one resolution. The noise test cannot see this, and a VM is one place where it can happen. One resolution can move a sample by up to `resolution_ns`. Beyond 1 % of the shortest interval, quantisation alone can move a sample by more than half of `delta` = 2 % (ADR-0007 decision 8), so a difference of `delta` between two measurements could be made or hidden by the clock alone. **1 % is this record's own initial value**, for that reason, and is revised with data from the first runs, as ADR-0007's values are.
- The smallest interval is used, not a summary, so the test needs no trimmed mean and holds for the worst sample. A `resolution_ns` of 0 never makes the test hold: the reported resolution is believed, as a backend's report is (cited: ADR-0063 Limit 2).
- **A broken run is no measurement** (cited: ADR-0009 decision 8) and gives no finding either way. Whether repeated broken runs show that "timing is hard" is left to failure handling (OD-10, OD-14).

### 4. The class ground: the timing run executed inside a virtual machine

- The class ground holds for a measurement whose timing run executed in a process that runs as **the guest of a virtual machine**. This includes the VM of Docker Desktop on macOS or Windows and WSL 2.
- **The class is this record's reading of the owner's example.** O1 names the VM of Docker Desktop. The property that makes that VM a hard place for timing is the hypervisor between the process and the CPU and clock: timer virtualisation and the scheduling of virtual CPUs. That property is the same for every VM guest, so the rule names the property and not the product (C-7). A container on a native Linux kernel is not a VM guest and does not meet the class ground. Its noise still meets the measured ground.
- **The input is new: the class of the place where the timing run executed** — whether it was a VM guest. No accepted record produces it. The operation carries out the timing run itself (cited: ADR-0061 decision 2), and the place where it runs is the container of the owner decision of 2026-10-15, item 1, whose design is OD-14 sub-question ①. **This record's own reading** is that the backend's operation, under that design, is the side that can know where its timing run executes. **Producing the input is left to a later record.** This record does not say how the class is established, which component establishes it, or where it is kept.
- **Not used as the input: the first word of `host.os`** (`wsl`, `macos`, `linux`; [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md)). It does not tell WSL 1 from WSL 2 (cited: ADR-0035 decision 4). It describes the machine of the key (cited: ADR-0035 decision 2), and whether that machine is the inside of a container is OD-14 sub-question ① (마). And `macos` is a VM guest only for a run inside a container. Using it would decide part of OD-14 ①.
- **Until the input exists, the class ground never holds**, and a finding rests on the measured ground alone. This is a limit of the present state (Limit 1), not a choice that the class does not matter.
- At the mock, the input is whatever the later record says for the mock. This record gives the mock no class.

### 5. The finding of a run

- **A run is found imprecise at a moment** when, by that moment, (a) one of its measurements has been found imprecise, or (b) the class input of decision 4, once a later record produces it, shows that an execution point of the run is a VM guest.
- **Once found, a run stays found** for the rest of its life. Results are kept, and a line of the events log is never edited or removed (ADR-0007 decision 3; ADR-0006 decision 5), so a later reader computes the same finding for every later moment. A later line that corrects or withdraws an earlier event does not take back a warning already shown, nor the comparisons the numbers have already entered.
- **Why one measurement suffices.** The run's numbers are compared with one another (O1, "relative numbers"). One imprecise measurement can enter a comparison with any other, so the warning about relative numbers applies to the run from then on. A share of measurements would need a constant and would let a run with many clean measurements hide an imprecise best. The cost is that one disturbed measurement marks the whole run (Limit 3).
- The measurements of both execution points count, and a repeated call that returns a stored result changes nothing, since the same result gives the same finding.
- **At the start of a run** no measurement exists, so a finding can rest only on (b). O1 asks for a warning "at the start of the run"; whether the class is known that early is for the record that produces the input (decision 4).

### 6. The moment, and reproducing the finding

- The measured ground of a measurement can be computed **as soon as its result exists**, at the end of the call, from `outcome`, `resolution_ns` and `intervals_ns` alone. A later computation gives the same answer. Which component computes it, and when, is left to the code task that applies this record once part (나) fixes where the mark goes.
- **Reproducible from what is kept** (as ADR-0007 decision 9 asks of a verdict): the measured ground is a function of one stored result and the constants `cv_max` (through the replayed `outcome`) and `resolution_share_max`. The constants are identified by the source commit hash of the instance, the confirmed part of OD-11 (ADR-0007 decision 8). A result does not name that commit, and a repeated call returns a result stored by an earlier commit (cited: ADR-0063 Limit 8), so if a constant changes while a run continues, the finding is reproduced with the constants of the commit that took the measurement only if that commit is known. The run's finding under (a) follows from its stored results. **Under (b) the finding can be reproduced only if the class input is kept where a later reader finds it**; that is for the record that produces it and for part (나).

### 7. The constant

| Name | Initial value | Source | Constant or per instance |
|---|---|---|---|
| `resolution_share_max`, the largest share of the shortest interval a clock resolution may have | 1 % | this record's own (decision 3) | **constant of the policy**, in the harness source |

- It is a constant and not an instance parameter, for the reason ADR-0007 decision 8 gives for `cv_max` and `delta`: it describes the measurement, not the cost of a run, and a user has no basis to choose it. Sub-question ④ of OD-13 (whether constants such as δ become instance parameters) is not answered beyond this constant. Its value was chosen from the initial value of `delta` (decision 3); if `delta` changes or ④ opens it, this constant is revisited with it.
- `cv_max` is reused unchanged. No other constant is introduced.

### 8. Limits

1. **The class ground is not yet active.** Until a record produces the class input (decision 4), a run inside a VM is found imprecise only if its noise or its clock shows it. The owner's first host is a PC under WSL (#5 B-4 ⑤, as ADR-0035 cites it), so this limit affects the owner's own first case.
2. **Facts only a runtime machine can establish** (CLAUDE.md, the development driver and the runtime; DRIVER D16), none tried here: whether and how a process inside the VM of Docker Desktop on macOS or Windows, or under WSL 2, can tell that it is a VM guest; what CV and what reported resolution a timing run shows there and in a container on native Linux; that WSL 2 runs its kernel in a VM (taken from documentation and not checked on a machine, as ADR-0035 decision 6 notes); and that in such a VM the distortion of timing shows mainly as an additive overhead or a drift between measurements and not in the CV of one measurement (decision 2). If such a VM routinely shows a low CV and a fine resolution, the measured ground alone finds nothing there, and Limit 1 matters more.
3. **The measured ground over-finds and under-finds.** "Not converged" does not tell the candidate's own variation (OpenMP thread scheduling, data-dependent run time) from the environment's, and ADR-0007 decision 10 notes that one slow repeat can keep the CV high although the trimmed mean is unaffected. Such a measurement is found imprecise, and under decision 5 its run is too; since one measurement suffices, the share of runs found imprecise rises with the number of measurements a run takes, and if it nears every run the warning stops telling environments apart. A measurement that converges by chance at `n_min` in a noisy environment is not found. Another spread measure (OD-13 sub-question ⑥) would change both. The clock test likewise finds a measurement whose shortest interval is short on a fine clock, a property of the kernel's shape rather than of the environment (OD-13 sub-question ⑧). **The share of measurements and of runs found imprecise is reviewed with data from the first runs**, as ADR-0007's values are; a run rule other than "one measurement suffices" is then a revision of decision 5.
4. **Drift and additive overhead between measurements are not seen** by the measured ground (the integrator note). The paired re-measurement of OD-13 sub-question ① is the registered remedy and is not decided here.
5. **A backend's report is believed** (cited: ADR-0063 Limit 2), and a kernel can forge its intervals (cited: ADR-0009 decision 10). A forged clean report gives no finding (OD-16).
6. **Outside the scope**, for a simulator, a board or another configuration, part (가) is still open.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | **(a) Known environment class only** | Misses high noise on a host that is not a VM, which O1 names as its own example ("or under high noise"). Today it would find nothing at all, since no record produces the class (decision 4). |
| 2 | **(b) Measured noise only** | Works on every machine kind by one rule (C-7) and uses only what a `cpu_standin` run already returns. But it misses a VM whose fault is additive overhead or drift, which O1 names first, and which one measurement's spread does not show (the integrator note). Kept as one of the two grounds. |
| 2 | **(c) Both** | **Chosen**, with either ground sufficient (decision 2). |
| 2 | Both, with both required | Finds only a noisy VM, and misses the two faults that only one ground can see. |
| 2 | **(d) The user declares it as an instance parameter** | O2 asks how the environment "is detected", and a user on a WSL PC (the default premise, C-7) need not know that WSL 2 is a VM. A declaration would be a new member of `instance.json`, which is a data-plane schema change that O1's approval of a mark does not cover. It would also make the same machine marked or not by the user's choice, against C-7. A later record may add a declaration as a third ground. |
| 3 | A noise threshold of its own, above or below `cv_max` | A second definition of high noise beside the one the policy stops on. Its value has no source before the first runs. |
| 3 | No clock test | A quantised measurement converges with a small CV and is not found, which is the case the noise test cannot see. |
| 3 | The clock test against the trimmed mean | Needs a summary that a result does not hold (ADR-0063 decision 4), and is less strict than the shortest interval for the same quantisation. |
| 3 | Broken runs as evidence | A broken run is no measurement and carries no numbers to warn about. Repeated failures are a matter of failure handling (OD-10, OD-14). |
| 4 | The first word of `host.os` as the class input now | Does not tell WSL 1 from WSL 2. It describes the key's machine, which under a container is OD-14 ① (마). And it gets macOS right only for a run inside a container. |
| 5 | A run found imprecise only when a share of its measurements is | Needs a constant with no source, and lets an imprecise best hide among clean measurements. |
| 5 | A run's finding withdrawn when later measurements are clean | A warning already shown cannot be taken back, and the earlier numbers stay in the comparisons. |

## Consequences

- **No code changes because of this record.** A later code task applies decisions 3 and 5 as a pure function over a result, together with the constant `resolution_share_max`, once part (나) fixes where the mark goes. The function reads no clock, runs nothing and writes nothing.
- **For part (나)** (the expected next record): the finding of a measurement is computable from its result, so a mark on a measurement could be derived rather than stored. That choice is part (나). If the mark goes into a tool result, the change falls under [ADR-0100](ADR-0100-od8-tool-result-change.md).
- **For the record that designs the container (OD-14 sub-question ①)**: it is the natural place for the class input of decision 4. This record asks nothing of it beyond naming the input.
- **Statements in accepted records that are not edited and are now less exact:**
  - ADR-0061 Limit 3 and ADR-0063 Limit 5, "untouched": part (가) of ⑪ is now answered for their scope. Parts (나) to (라) remain untouched, and a result still carries no mark.
  - ADR-0063 decision 4, "No threshold on `resolution_ns` is decided": this record decides one. It is a threshold for the finding only and not for the validity of a result.
  - ADR-0009 decision 4, "No threshold on it is decided" (the reported resolution): this record decides one, for the finding only and not for whether a run is completed or broken.
  - ADR-0007 decision 4, "What else a consumer does with the mark … is not decided here": "not converged" is now also the noise test of decision 3. Whether such a measurement may stand as a best or a baseline is still open (OD-13 sub-question ②).
  - ADR-0009 decision 10, "Noise from other processes … shows in the spread only": it still shows only there, and a spread that ends not converged is now a finding.

## Boundaries (not decided here)

- **Sub-question ⑪ (나)**: in which record and member, and in which form, the finding of a measurement or a run is kept, and whether it is stored or derived.
- **Sub-question ⑪ (다)**: whether numbers of a measurement or run found imprecise may be reused across runs (FR-18) or judged against an absolute target (FR-2) or a constraint.
- **Sub-question ⑪ (라)**: where and how the warning is shown to the user (OD-27).
- **The producing of the class input** (decision 4): how a VM guest is recognised, by which component, at which moment, and where it is kept.
- **OD-14 sub-question ①**, the build and run container design, including (마): whether timings and a maximum resident set taken inside a container are those of ADR-0009 and ADR-0052, and which machine the `cpu_standin` hw key describes.
- **OD-13 sub-questions ①** (paired re-measurement), **②** (what is done with a not-converged measurement), **④** beyond `resolution_share_max`, and **⑥** (the spread measure). The improvement rule of ADR-0007 is not changed.
- **Outside the scope**: part (가) for a simulator, a board (#5 B-2, B-3) or any other configuration.
- **Owner-only (DRIVER §9)**: the #5 A and B items, OD-3, OD-25, C-6.
- No change to ADR-0007, ADR-0009, ADR-0061, ADR-0063 or any other record; to NFR-3 or any FR; to `hilclaw/`, tests or CI; to any member of a tool result, `step` value, event kind, spend axis, `schema_version` or data-plane schema.

## References

- [Requirements](../Requirements.md): FR-2, FR-18, NFR-3, C-7; register rows OD-10, OD-11, OD-13, OD-14, OD-16, OD-27.
- [OpenDecisionProposals](../OpenDecisionProposals.md): [OD-13](../OpenDecisionProposals.md#od-13) (sub-questions ①, ②, ④, ⑥, ⑪; the owner decision and the integrator note of 2026-10-15), [OD-14](../OpenDecisionProposals.md#od-14) (sub-question ① (마)); [StandardScenarios](../StandardScenarios.md) (S0, S1-b, S2, S5, S6, S9, S10).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0006](ADR-0006-od8-events-log.md) (decision 5); [ADR-0007](ADR-0007-od13-measurement-policy.md) (decisions 3, 4, 7, 8, 9, 10); [ADR-0009](ADR-0009-od13-cpu-standin-timing-run.md) (decisions 4, 8, 10); [ADR-0035](ADR-0035-od4-cpu-standin-hw-key-values.md) (decisions 2, 4); [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) (decision 1); [ADR-0061](ADR-0061-od18-run-tools-split.md) (decisions 1, 2; Limit 3); [ADR-0063](ADR-0063-od18-run-tools-result-members.md) (decisions 2, 4, 9; Limits 2, 5, 8); [ADR-0100](ADR-0100-od8-tool-result-change.md).
- Owner decisions of 2026-10-15 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913 (item 3, "Left open"); D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506; #5 B-4 ⑤.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 and D16; task T-0302.
