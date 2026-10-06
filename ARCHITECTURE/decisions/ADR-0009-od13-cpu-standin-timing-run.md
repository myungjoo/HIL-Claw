# ADR-0009: How the timing samples of one measurement are taken from a C kernel at `cpu_standin` (one part of the rest of OD-13)

## Status

- **Accepted on 2026-10-07** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- Closes **one part of the rest of OD-13** (Open Decisions register in [Requirements](../Requirements.md)): sub-question ⑤ of [OpenDecisionProposals OD-13](../OpenDecisionProposals.md#od-13) (calls per repeat, reuse of inputs, an execution before the first repeat) and the mechanism by which the samples of one measurement are taken from a C kernel at the `cpu_standin` execution point. The register row keeps its status.
- What stays open of OD-13: pairing, steady-state labels, session hygiene, the values for a simulator and a board, the handling of "not converged", another spread measure, and the sub-questions ⑦ and ⑧ this record raises (see Boundaries).
- It builds on [ADR-0007](ADR-0007-od13-measurement-policy.md) (what a measurement, a repeat and a sample are; the stopping rule) and [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (how a kernel is called). The objection windows of both run until 2026-10-14; if either is reverted, this record is revisited with it.
- The owner is notified on issue #5. The owner may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0007 says what a sample covers and when the repeats stop, and leaves to "the design of the harness (PLAN P1-3)": the clock, how many kernel calls a repeat times, whether repeats reuse the same inputs, and an execution before the first repeat. ADR-0008 fixes the call `hilclaw_gemm(m, k, n, a, b, c)` and leaves "linking, loading or a separate process, the driver program, how two kernels of one contract are kept apart, the timer, calls per repeat, reuse of inputs, how the arrays are allocated".
- Fixed inputs. #5 A-7 ②: stand-in kernels are C, clang is the single toolchain, OpenMP and SIMD are allowed. #5 A-12 point 4: timing belongs to the harness, one sub-module of the tool package (`harness/`), never part of the coder's scratch; #5 A-12 point 2: layer-2 languages are {Python, POSIX sh, C}. C-7: the same behaviour on Linux, macOS and WSL. #5 B-4: a single call of a first GEMM takes about 0.1 s.
- The pieces exist and are not changed here: `hilclaw/clang_build.py` builds several sources into one artefact with the caller's flags; `hilclaw/local_run.py` runs one process under a required time limit, with no standard input, and returns its output after it has ended; `hilclaw/harness/measurement.py` holds the stopping test `stopping_state` and the constants of ADR-0007.
- Not available as inputs, and not used below: the measured quantity and its direction (OD-1, #5 A-4), the reference oracle and the tolerance (#5 A-7 "still open", B-7), any adopted defence of OD-14 or OD-16.

## Decision

A value below is **cited** when a source is named with it; every other value is **this record's own** choice.

### 1. Scope and terms

- This record is about taking the timing samples of **one measurement of one built attempt** of a C kernel of ADR-0008 at `cpu_standin`. It is not the verification run, not an FR-10 tool contract, and not a mechanism for a simulator, a board or a remote machine.
- **Driver program**: the C source of the harness that defines `main`, prepares the operands, calls the kernel and reads the clock. **Timing executable**: the driver program and the source of one kernel built into one executable. **Timing run**: one process of a timing executable; it takes the repeats of at most one measurement. **Python side**: the code of the harness that builds the executable, starts the run and reads its report.

### 2. From kernel source to a call

- The harness provides the program (FR-9; ADR-0008 decision 7: a kernel has no `main`). The driver program is **one C source file under `hilclaw/harness/`** (cited: #5 A-12 point 4; C is in the layer-2 set and is the language of the call). Its file name, and how it ships with the package, are the code task's.
- The driver source and all source files of **one** kernel are compiled and linked by **one call of `clang_build.build`** into one executable, with the caller's flags (decision 9). The same flags therefore apply to the driver source; it must be written to stay correct under them. The harness adds no flag, so two things follow: **the driver source needs nothing beyond the C library** (no `-lm`: the stopping rule is evaluated without a call into the mathematics library, for example by comparing squares), and **the caller's flags must be ones that produce an executable** — a build that yields an object or a shared library is not a timing executable, and the Python side does not correct it.
- **Two kernels of one contract never meet**: each timing executable holds exactly one kernel, so the one symbol `hilclaw_gemm` is defined once per executable. Nothing is renamed.
- **The kernel runs in a process of its own**, started by the Python side through `local_run.run`, never inside the Python process. Reasons: a kernel that crashes or does not return ends its own process and is bounded by the time limit of the runner; the kernel's threads and run-time library stay out of the Python interpreter; and an executable is something the C gate can build as it is, and it does not stand in the way of the remote path, which is not decided here.
- **Reading next to OD-14.** One process per timing run coincides with the registered proposal "1 후보 = 1 프로세스". It is chosen here as the mechanism of a timing run only. **No sandbox, isolation, resource limit or timeout hierarchy is adopted or rejected with it**; the process is as unprotected as `local_run` says, and OD-14 stays as registered.

### 3. The timer

- The clock is `clock_gettime(CLOCK_MONOTONIC, &t)` of `<time.h>` (POSIX.1-2008; `CLOCK_MONOTONIC` is its Monotonic Clock option, which the three platforms of C-7 provide). The driver source requests that interface itself (`#define _POSIX_C_SOURCE 200809L` before its first include), so that no build flag is needed to make it visible.
- Between the two readings of one repeat lies **exactly the kernel call** `hilclaw_gemm(m, k, n, a, b, c)` of decision 4 and nothing else: no allocation, no output, no arithmetic of the stopping rule. The cost of the two clock calls themselves is inside and is not corrected for.
- The driver reports the **length of the timed interval**: the difference of the two readings as a whole number of **nanoseconds** (unit: this record's own). It also reports once the resolution of the clock, the value of `clock_getres(CLOCK_MONOTONIC, …)`, in nanoseconds. It is elapsed time, not processor time: a kernel may run threads (#5 A-7 ②), and processor time adds them up.
- **Premise**: a POSIX system with clang (C-7: Linux, macOS, WSL). Native Windows is not supported; neither is a clock other than this one.
- The number is the length of an interval. **How the measured quantity is obtained from it stays with OD-1** (ADR-0007 decision 1: "the time itself, or a rate derived from it"); this record names no quantity, no unit of a quantity and no direction. Decision 7 says how the stopping rule is applied without choosing.

### 4. Calls per repeat

- **One repeat times exactly one call.** It is a constant of the mechanism, not a parameter, and so the same for every repeat (ADR-0007 decision 2).
- Reason: the smallest first instance (O 2048→2048 at M = 1) reads a 16 MB weight array per call, which this record estimates at a millisecond or more against an expected clock resolution of a microsecond or less on the platforms of C-7 (both are estimates, not measurements); B-4 puts a call at about 0.1 s. A parameter nobody has a reason to set would have to be recorded per instance to trace a result (ADR-0007 decision 8).
- The reported resolution lets a reader see the margin. No threshold on it is decided; an interval of 0 ns ends the run as broken (decision 8), because a sample must be positive (ADR-0007 decision 1).

### 5. Operands of a timing run

- The driver obtains the three arrays with **three separate `malloc` calls** of m·k, k·n and m·n `float` elements, once, before any call, and frees nothing before the last repeat. `malloc` gives the alignment of `float` and whatever more the platform gives; **nothing more is promised** (ADR-0008 decision 6), and a kernel must not rely on it.
- `a` and `b` are **filled once, before any call**, by a deterministic generator inside the driver from a **seed that is a parameter of the run** (decision 9). Every element is finite and has a magnitude in [0.5, 1) with either sign (range: this record's own): the inputs are initialised as ADR-0008 requires, and neither they nor the sums of their products are subnormal, so a timing does not measure a slow floating-point path. The generator is the code task's and is identified by the source commit. `c` is not initialised (ADR-0008: unspecified on entry).
- **No input value is written to any file** (FR-9; the principle of OD-16): the values exist in the memory of the run only. The seed travels as a command-line argument.
- **Every repeat of a measurement uses the same three arrays and the same input values.** The repeats of one measurement are then repeats of one thing, so their spread is noise of the execution and not of the data, and nothing is generated or allocated between two repeats.
- Reusing inputs is the opening of OD-16 threat B ⑸ (caching across the repeats of a timing loop). This record states the choice and **adopts no defence and rejects none**: fresh buffers per trial, cache flushes and drop detection stay registered proposals.
- **Not decided**: how verification inputs are drawn, and whether the inputs of a timing run are meant to be those of a verification run of the same attempt. Which seed a caller passes — fixed, fresh per run, recorded or not — is open as well (sub-question ⑦, with OD-16).

### 6. An execution before the first timed repeat

- The driver calls the kernel **exactly once, untimed**, with the arguments of the repeats, after the operands are prepared and before the first timed repeat. It is not a repeat, **yields no sample** and its duration is not read or reported (ADR-0007 decision 6).
- Reason: the first call of a process pays for things ADR-0007 decision 2 places outside a sample — "starting and loading the process, … allocating": the first touch of the pages of `c`, lazy binding, and the start of a kernel's threads. One count is fixed (this record's own); it is not a parameter. Every timed repeat is still a sample: nothing is discarded and nothing labelled.
- Not reading that call's duration leaves nothing to compare a first call with. The registered proposals that would use it — the detection of a drop after the first execution (OD-16 threat B ⑸) and steady-state labelling (rest of OD-13) — are **neither adopted nor rejected**; adopting either reopens this decision.

### 7. The repeat loop and the stopping rule

- **The driver program runs the loop and evaluates the stopping rule itself**, after each repeat and outside every timed interval; it stops at the first n at which the rule of ADR-0007 decision 4 is met. The Python side does not steer a run.
- **The driver holds no value of the policy.** The Python side passes `n_min` and `cv_max` from the constants of `measurement.py` and the caller's `n_max` as arguments, so the constants keep living in one place of the harness source (ADR-0007 decision 8).
- **The sample form is a parameter**: `interval` or `reciprocal` (names of this record, not fields). The rule is applied to the samples — the interval lengths, or their reciprocals. The coefficient of variation does not change under a positive factor, so these two forms cover every quantity that is proportional to the interval or to its reciprocal, which are the two cases ADR-0007 decision 1 names. The caller says which; this record gives no default. A quantity of another form reopens this decision.
- **The Python side is the authority.** From the reported intervals and the form it derives the samples in order and replays `stopping_state` on every prefix: the run is accepted only if every proper prefix is `CONTINUE` and the whole sequence gives the state the driver reported. A disagreement — expected only where the spread is within rounding of `cv_max`, since the two sides compute in different arithmetic, a defect of the driver and the forgery of decision 10 aside — makes the run broken. It is never repaired by leaving out or adding a sample.
- **Against ADR-0007 as written.** Decision 1: the repeats of a measurement are consecutive iterations of one loop in one process; no other attempt and no process start lies between them, and between two repeats the driver only evaluates the rule and writes one line. Decision 3: every interval read is reported, in order, and the Python side passes on the whole sequence. Decision 4: the rule is evaluated on all samples so far after each repeat from `n_min` on, and no repeat is taken once it is met. A run that the rule did not end (decision 8) is not a measurement, even with `n_min` or more intervals: decision 4 ends a measurement in no other way. ADR-0007 says this in words only for a run with fewer than `n_min` samples; the wider statement is **this record's reading**. A run whose reported intervals do meet the rule but whose process did not end as decision 8 requires (a non-zero status, a timeout, a missing `stop` line) is broken as well; that is **this record's own choice** — the report of a process that failed is not taken as a measurement — and not something ADR-0007 decision 4 says.
- **Existing modules**: `local_run.run` serves as it is — arguments in, output after the end, a time limit — and `stopping_state` is used unchanged, as the check. Neither module is edited.

### 8. What the driver reports

- **Channel**: the standard output the process was started with, as ASCII lines ending in LF, each written and flushed when its value exists and outside every timed interval, so that a run that ends early leaves what it had taken. Standard error is free text for a reader and is not parsed.
- **A kernel may write to its standard output** — ADR-0008 forbids no output, it only says that output is no result. Before the first kernel call the driver therefore keeps the report channel under a descriptor of its own and points descriptor 1 at standard error (`dup`, `dup2` of `<unistd.h>`, POSIX): what a kernel prints arrives as text on standard error and does not disturb the report. No obligation is added to the contract of ADR-0008.
- **Form**, in this order and with nothing else on the report channel — one `resolution_ns <integer>` line before the untimed call, one `interval_ns <integer>` line per repeat in the order taken, and a last line `stop converged` or `stop not_converged`:

```
resolution_ns 1
interval_ns 104200311
interval_ns 99870122
interval_ns 101004517
interval_ns 100310960
interval_ns 102118803
stop converged
```

- A run is **completed** when it did not time out, its exit status is 0, the captured standard output is exactly of this form, and the replay of decision 7 agrees. **Every other run is broken** and yields no measurement, however many intervals it reported: a non-zero status or a signal, a timeout, a missing `stop` line, a line of another form, an interval of 0, or a disagreement. The driver's own failures (arguments, allocation, clock) end with a non-zero status and a message on standard error; the status values are the code task's.
- The Python side returns, for a completed run, the intervals in order, the resolution and the state; for a broken run, that it is broken and what the runner captured. **What is kept of a broken run and what happens next is OD-10 and OD-14.**
- The form is an interface between two parts of the harness that are always of the same source commit (OD-11 confirmed part); it carries no version and **is not a file or a field of the data plane**.

### 9. Parameters

| Value | Given by | Source |
|---|---|---|
| `m`, `k`, `n` | the caller | The record restricts them no further than ADR-0008 (each ≥ 1); whether shapes outside the `op_signature` are used is OD-16 sub-question ① |
| `n_max` | the caller | cited: ADR-0007 decision 8 (per instance, default 10) |
| `n_min`, `cv_max` | the Python side, from `measurement.py` | cited: ADR-0007 decision 8; not a caller's choice |
| Sample form | the caller, no default | OD-1 (decision 7) |
| Seed of the inputs | the caller, no default | this record's own parameter; its policy is open (decision 5) |
| Time limit of the run | the caller, no default | `local_run` requires one; values and hierarchy: OD-14 |
| Flags, trailing flags, compiler, build time limit, path of the executable | the caller, handed to `clang_build.build` | Build settings: Boundaries |
| Environment and working directory | the caller, handed to `clang_build.build` and to `local_run.run` unchanged | Thread settings of a run travel here; none is set by the harness |
| Calls per repeat = 1; untimed calls = 1; unit ns; input magnitudes in [0.5, 1) | constants of the mechanism | this record's own |

- All parameters of the driver are command-line arguments; it reads no standard input, no file and no environment variable of its own. Their spelling and order are the code task's.
- **No flag, language standard, `-march`, OpenMP runtime, thread count or time-limit value is decided here.** One timing executable may be run more than once; each run is a measurement of its own, and samples are never pooled (ADR-0007 decision 4).

### 10. Limits

- **No protection against forged timing.** The kernel shares the process with the driver: it can cache across repeats, move work into the untimed call or out of the interval, write to the report channel or change the clock's readings. Nothing here detects it (rest of OD-16, threats A and B ⑷ ⑸; ADR-0003).
- **Noise from other processes** and from the machine is not removed or recorded; it shows in the spread only (rest of OD-13: session hygiene).
- **Untimed cost is still spent**: process start, the generation of tens of megabytes of inputs and the untimed call lie outside the samples but inside the time limit and the wall clock of a round (budget: OD-2, OD-19; limits: OD-14).
- The driver never reads `c`. Whether a build could remove a call whose output is unread depends on the flags (link-time optimisation), which are the caller's; the code task makes the calls observable without judging the output.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The kernel as a shared library loaded into the Python process (`ctypes`) | A crash or a hang of the kernel takes the harness with it, and no time limit can end a call inside the interpreter's own process. |
| 2 | A shared library loaded by a fixed driver executable (`dlopen`) | A second artefact and a loader path for no gain: one build per attempt is needed either way. |
| 2 | Driver and kernel compiled separately, then linked | Three compiler processes and two sets of flags to keep apart; `clang_build.build` already takes several sources. |
| 3 | `clock()`, `CLOCK_PROCESS_CPUTIME_ID` | Processor time: the sum over the threads of an OpenMP kernel. |
| 3 | `gettimeofday`, `timespec_get(TIME_UTC)` | Wall-clock time that can be set or stepped during a run. |
| 3 | `CLOCK_MONOTONIC_RAW`, a cycle counter, `omp_get_wtime` | Not in POSIX, not portable across the hosts of C-7, or tied to an OpenMP build. |
| 4 | Calls per repeat as a parameter, or chosen by the driver from a trial | A value to record per instance, or a second adaptive rule beside ADR-0007's; no first instance needs it. Registered as sub-question ⑧ for the first kernel whose call nears the resolution. |
| 5 | Fresh inputs or fresh buffers for every repeat | The spread would mix data and allocation effects into the noise; it is also a registered defence of OD-16, which this record may not adopt. This is a reason for the default of this mechanism only; the OD-16 proposal is not judged (decision 5). |
| 5 | A constant fill, or a seed fixed in the driver source | A constant fill invites zero and subnormal paths; a fixed seed would decide what sub-question ⑦ leaves open. |
| 6 | No untimed call | The first sample would time page allocation, lazy binding and thread start, which ADR-0007 decision 2 excludes from a sample. |
| 6 | The driver touches `c` itself instead | Covers the pages only, not binding or the kernel's threads. |
| 7 | The Python side steers the driver: a sample out, "go" or "stop" back, per repeat | One implementation of the rule, but an exchange with another process between every two repeats, a runner with a standing two-way pipe that `local_run` is not, and a wait that needs its own time limit. |
| 7 | The driver always takes `n_max` repeats; the Python side cuts at the stop | Drops samples that were taken, and takes repeats after the stop was due (ADR-0007 decisions 3 and 4). |
| 7 | One process per repeat | A process start between repeats is not "one uninterrupted sequence", and every sample would be a first call. |
| 7 | The rule applied to the interval lengths only | Would treat the interval as the measured quantity, which is OD-1. |
| 8 | The report written once, after the last repeat | A run that ends early would leave nothing, which would settle part of OD-10 by construction. |
| 8 | The report on descriptor 1 as it is, with a kernel's own output breaking the run | A kernel that conforms to ADR-0008 and prints a line could never be timed: an obligation the contract does not have, and one a spec would not show (ADR-0008 decision 8). |
| 8 | A file, or JSON | A file needs a path and a writer rule in the data plane; a parser of JSON in C is more than three kinds of line need. |

## Consequences

- **The code task** (PLAN P1-2 "타이밍 수집", the timing half of P1-3) writes the driver source in C and the Python side under `hilclaw/harness/`, using `clang_build.build`, `local_run.run` and `stopping_state` as they are. Tests that need a real clang can run on CI only, as in `tests/test_clang_build.py`: the driver clone's environment has no C compiler. The parsing and the replay can be tested everywhere with a stand-in program.
- **C gate** (PLAN P0.5-1): once the driver source exists there is a C file to build, with any kernel of ADR-0008; the gate itself is designed there.
- **Verification half** (rest of P1-3, P1-4): it can reuse the model of decision 2 (harness `main`, one kernel per executable, a process of its own) and the allocation of decision 5. If verification and timing are to share one program or one run, decisions 5 (which inputs), 6 and 8 (the report) are reopened, and the exclusions of ADR-0007 decision 2 (reference, comparison) must still hold for every timed interval.
- **Result files** (PLAN P1-8): beyond what ADR-0007 already asks, a record of a measurement taken this way should be able to hold what the source commit does not determine — the parameters of decision 9 the caller chose and the reported resolution. **No field is named**; whether a seed may be recorded after a run goes with sub-question ⑦.
- **Cost**: a measurement is one untimed and 5 to `n_max` timed calls plus the preparation of the operands, per attempt.
- **A-13 reading**: no code, schema file, field or dependency changes. The report form is an internal interface of the layer-2 package, not a data-plane schema.

## Boundaries (not decided here)

- **Owner-only (DRIVER §9)**: the measured quantity, its unit as a quantity, its direction and "better" (OD-1, #5 A-4); the reference oracle of `cpu_standin` and the tolerance (#5 A-7 "still open", B-7; PLAN P1-3 "오너 확정 필요").
- **Verification**: how verification inputs are drawn, the number of draws, shapes outside the `op_signature` (OD-16 sub-question ①), corner cases; the order of verification and timing and whether they share a program.
- **OD-16, OD-14, OD-8**: every defence against threat A or B, a calibration of the timing side (OD-16 sub-question ③); every sandbox, isolation, resource limit and timeout hierarchy; the isolation means.
- **Build settings**: flags, the language standard, `-march`, the OpenMP runtime and thread count, `task.build`, OD-6 sub-question ②; whether a kernel may link another library.
- **Rest of OD-13**: pairing, steady-state labels, session hygiene, values for a simulator and a board, the handling of "not converged", another spread measure (sub-question ⑥), and the two sub-questions registered with this record — ⑦ the seed policy of timing inputs and their relation to verification inputs, ⑧ calls per repeat for a kernel whose call nears the clock resolution.
- **Elsewhere**: fields and schemas of `sim.json`, `board.json`, `instance.json` and every event kind or payload (PLAN P1-8); the FR-10 tool contract and its exposure form (P1-1, OD-18); failure and retry (OD-10); the baseline (OD-28); the hw side (OD-26); the coder's output form (OD-23); the remote (LAN) path of #5 A-7 ③; any kind other than `gemm` and any kernel language other than C.
- Code, C files, tests, CI changes, `pyproject.toml` and the `HIL-Claw-data` repository: later tasks.

## References

- [Requirements](../Requirements.md): FR-1, FR-9, FR-10, NFR-2, NFR-3, NFR-4, C-4, C-7; register rows OD-1, OD-2, OD-8, OD-10, OD-11, OD-13, OD-14, OD-16, OD-18, OD-19, OD-23, OD-26, OD-28.
- [OpenDecisionProposals OD-13](../OpenDecisionProposals.md#od-13) ("하위 질문" ⑤-⑧), [OD-14](../OpenDecisionProposals.md#od-14), [OD-16](../OpenDecisionProposals.md#od-16) (threats A and B ⑷ ⑸, "하위 질문" ① ③).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0003](ADR-0003-od16-harness-calibration.md) (decision 3, Boundaries); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (the files below `measure/`, none named here); [ADR-0007](ADR-0007-od13-measurement-policy.md) (decisions 1-4, 6, 8, Boundaries); [ADR-0008](ADR-0008-od6-gemm-kernel-contract.md) (decisions 4, 6, 7, Consequences, Boundaries).
- #5 A-7 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944117402 · A-12 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5946779596 · B-4 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5944412285 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506 · #5 body items A-4, B-7.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P0.5-1, P1-2, P1-3, P1-4, P1-8; `hilclaw/clang_build.py` (`build`), `hilclaw/local_run.py` (`run`), `hilclaw/harness/measurement.py` (`stopping_state`, the constants); tasks T-0013, T-0019, T-0029, T-0031.
