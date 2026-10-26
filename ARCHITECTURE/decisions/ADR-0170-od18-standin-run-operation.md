# ADR-0170: The compiler's log of the waiter's build and the `cpu_standin` operation of `sim.run` and `board.run` — the waiter's log is not kept; the timing build's log is handed over as ADR-0169 says, right after the timing build, whatever the waiter's build then gives (part of OD-18 sub-question ⑲ (다), for the runs of ADR-0144 decision 1)

## Status

- **Accepted on 2026-10-26** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. **The owner has not confirmed it.**
- **Whose content.** No sentence of the owner is used as a decision of this record. #5 A-2 is named only through [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) and [ADR-0108](ADR-0108-od18-run-tools-timing-build-compiler-log.md), as those records quote it. The owner's O2 (the answer to HQ-0020, point 2: "Kept, not returned: in a file of the attempt", as ADR-0108 Context quotes it) is named only through the reading of [ADR-0061](ADR-0061-od18-run-tools-split.md) decision 7 that ADR-0108 Status takes (decision 2). **Everything this record decides is its own design.** **Open HQs checked** (`PROCESS/STATE.json` on `main` `a4e5d091`): the unresolved ones are the owner-only HQ-0070 and HQ-0071 and runtime-acceptance items; of the latter HQ-0060 ([ADR-0145](ADR-0145-od14-first-case-container-measurement.md)), HQ-0073 ([ADR-0168](ADR-0168-od18-standin-container-situations.md)) and HQ-0074 ([ADR-0169](ADR-0169-od18-standin-build-log-and-removal.md)) are the closest; this record adds items beside them (Consequences) and closes none. HQ-0034 (OpenMP) is not touched.
- **Answers**, for the runs of [ADR-0144](ADR-0144-od14-first-case-build-run-container.md) decision 1: **whether the compiler's log of the waiter's build of ADR-0145 decision 3 is kept** — the piece ADR-0169 decision 4 and Boundaries left open, **part of OD-18 sub-question ⑲ (다)** — and **how the keeper is handed the timing build's log in a call that builds twice**. **Not answered**: the size bound of ⑲ (다) (Boundaries). The OD-18 row keeps its status word; OD-14 is not touched.
- **No new value of `error.kind` and no new value of `condition`; no new file, file name or member of the data plane; the bytes rule of ADR-0078 decision 4 and ADR-0108 decision 4 is not touched** (decision 5, the answer to the stop conditions of task T-0481).
- **It is a record and the first slice of its code** (decision 6): `hilclaw/standin_run.py`, the `cpu_standin` operation of `sim.run` and `board.run`, bound to no backend table. Nothing was started for it (CLAUDE.md "개발 드라이버와 런타임의 구분", D16): no container runtime, compiler, kernel or `claude` process; tests stub the client. Statements about code were read at `a4e5d091` and are observations.
- **No sentence of an earlier record is replaced.** Sentences that leave these points open become less exact; Consequences lists those this record found.
- It builds on ADR-0078 (decisions 1 to 4), ADR-0108 (decisions 1 to 5), ADR-0144 (decisions 1 to 3; Q3), ADR-0145 (decision 3), ADR-0168 (decisions 2, 4, 5), ADR-0169 (decisions 2 to 5) and [ADR-0116](ADR-0116-od18-cpu-standin-build-settings.md) (decisions 3, 4). **If ADR-0108, ADR-0145 or ADR-0169 is reverted, this record is revisited with it; if another of them is, the decisions that cite it are.**
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- **What is open, cited.** ADR-0169 decision 4: "The waiter's build (ADR-0145 decision 3) is not answered here. … Keeping the waiter's log too would need either a second file of a timing identity — a new file name of the data plane (CLAUDE.md A-13; ADR-0101 Consequences) — or the logs of two compiler processes in one file, which ADR-0108 decision 1's "The log: everything the compiler process of that build wrote" (cited) does not read as covering. Not keeping it is a reading of A-2's "에러 로그" that ADR-0078 decision 2 did not make for a build of an attempt … **Neither is chosen**". Its Consequences: "the record of the waiter's build's log (decision 4) is needed first, or with it".
- **The waiter's build, cited.** ADR-0145 decision 3: the waiter "is not the kernel's: no kernel file is compiled into it"; its source "is copied into the build directory with the harness program … and is compiled into the waiter's executable by a build of its own in a new container of the same image, with the flags of ADR-0116 decision 3 …; it includes no header but the system's. It is made after the timing build and before the timing process. **One time limit covers both builds** … (whether the operation's own work between the two counts against it is the code slice's)". ADR-0168 C19: the waiter's build is "read as a timing build (C3 to C7, C10, C13), with S9 for a status 0 that leaves no waiter's executable; where B_t is used up before it starts, `build_time_limit` (S8)".
- **The keeper, cited.** ADR-0108 decision 5: handed the log "as text, at most once, before the operation returns or raises"; one file per timing identity (ADR-0108 decision 3). ADR-0169 decision 3: a log is handed over "after the build container is read and before the executable is looked for or the process is started".
- **Observations at `a4e5d091`.** The waiter's source is `hilclaw/harness/timing_waiter.c`, one translation unit beside `timing_driver.c`. The test `tests/harness/test_timing_waiter.py` builds it with a real `clang` under `-std=c99` and under the flags of ADR-0116 decision 3 and requires an empty log (`assert result.log == ""`); that test runs where a `clang` and a new PID namespace can be had, the CI's Linux runner. `hilclaw/run_operation.py` `ask` counts as the form (A) "exactly a `tuple` of length 2, so no subclass of `tuple` (a `Reported` among them) is a pair".

## Decision

A sentence is **cited** when a record, a requirement or a file is named with it; it then says what that source says and adds nothing. Every other sentence is **this record's own**.

### 1. Scope and terms

- **The calls**: a call of `sim.run` or `board.run` at a run of ADR-0144 decision 1 (cited: ADR-0168 decision 1). **The timing build**, **the waiter's build** and **the timing process** are those of ADR-0145 decision 3 (cited). Rows C1 to C19 are ADR-0168's; rows L1 to L8 are ADR-0169 decision 3's.

### 2. The compiler's log of the waiter's build is not kept

- **The operation hands the keeper nothing of the waiter's build**, whatever it gives: no stream of its client is joined to the timing build's log, and no file is written for it. Its client's streams are read for nothing but its status (C19).
- **The reading of A-2 this rests on.** ADR-0078 decision 2 read #5 A-2's "에러 로그" "as including the compiler's log of a build of an attempt" (cited), and ADR-0108 decision 2 took that reading for the timing build because "the log of a timing build is a log of a build of an attempt" (cited). **This record reads "a build of an attempt" as a build that compiles the attempt's source.** The verification build and the timing build do (cited: ADR-0056 decision 4; ADR-0107 decision 3). The waiter's build does not: "no kernel file is compiled into it" (cited: ADR-0145 decision 3). Its inputs are one source file of the installation, the image and fixed flags, the same for every attempt that the installation and image serve. Its log therefore says nothing about any attempt, and it is no "에러 로그" of the attempt in A-2's sense under this reading. **This reading is this record's own and not the owner's.** It does not extend the reading of ADR-0078 decision 2 and does not narrow it: every build that reading keeps is still kept.
- **No owner sentence speaks of the waiter's build's log.** O2, the owner's keeping answer, which ADR-0060 decision 5 applied to S7 and S8 (cited: ADR-0078 decision 2), "was given for the verification build" (cited: ADR-0061 decision 7), and ADR-0108 Status takes that reading: "No owner sentence speaks of keeping the log of a timing build" (cited). The waiter's build is no verification build either, and the reading holds of it as of the timing build. So a waiter's build answered S7 or S8 (C19) has its log not kept against no sentence of the owner. O4, the owner's answer to HQ-0020 point 3, "extends to the timing build the principle that a build that ended not ok is a result, not the keeping of its log" (cited: ADR-0108 Status, reading ADR-0061 decision 7); a failed waiter's build stays a broken result (cited: ADR-0168 C19), and this record does not change that. If the owner reads O2 as covering every build a call answers S7 or S8 for, that is an objection to this decision. If the owner reads A-2 as keeping the log of every compiler a call starts, that is an objection to this decision.
- **Weighed.**
  - **(a) A second file of the timing identity** (for example `build-log-<step>-<EE>-waiter.txt`). This is a new file name of the data plane (cited: CLAUDE.md A-13; ADR-0101 Consequences). It needs the owner, and the A-2 reading above gives no ground to ask for it. Not taken.
  - **(b) The one file, holding the timing build's log followed by the waiter's.** ADR-0108 decision 1 gives the file "everything the compiler process of that build wrote" for "the one call … that the operation of a call makes" (cited). Two processes in it are not that, and nothing may mark where one ends: the bytes rule allows "no header" and adds nothing (cited: ADR-0078 decision 4). The hand-over would also move from where ADR-0169 decision 3 puts it, after the timing build, to after the waiter's build. Then a timing build whose waiter's build raises (C14) or meets a request to end (C18) would have its log handed over by a rule of its own, or not at all. Not taken.
  - **(c) Not kept** (taken), under the reading above. It adds no file and no name. It changes nothing of the timing build's log, which stays the log of one compiler process in the one file, and it keeps the presence rule of ADR-0108 decision 2 as written.
- **The cost.** A call answered `build_exit_status`, `build_time_limit` or `build_output_missing` because of the waiter's build (C19) leaves the file of the timing build's log, which ended ok. Nothing in the file or the result says which build gave the answer, and the waiter's diagnostics are not kept. This is acceptable under ADR-0108 decision 2, which keeps the log of "every build that ended ok, whatever followed" (cited); the waiter's build is one of the things that follow. This record expects the loss to be small. The waiter's source builds without a diagnostic under the flags of ADR-0116 decision 3 (observation: the test's empty log), and a waiter's build that fails is a fault of the installation or the image, not of the attempt. It can be seen again by building that one file with the same image and flags, without any data of the attempt. That it builds without a diagnostic in the image is runtime acceptance item (lxxxi).

### 3. The timing build's log in a call that builds twice

- **The timing build's log follows ADR-0169 decisions 2 and 3** (cited for what it is and when it is handed over: rows L1 to L8 read for the timing build, ADR-0169 decision 4).
- **The order.** The operation hands the timing build's log over after the timing build's container is read and before the timing executable is looked for (cited: ADR-0169 decision 3). This is also before the waiter's build is started, whatever the waiter's build then gives:

| | After an ok timing build, the waiter's build … (ADR-0168 row) | Answer (cited: ADR-0168 decision 2, C19 and the rows named) | The timing build's log |
|---|---|---|---|
| R1 | is not started: what is left of B_t is not above zero | `build_time_limit` (S8) | already handed over |
| R2 | ends with 0 and leaves the waiter's executable | go on to the timing process | already handed over |
| R3 | ends with 0 and leaves no waiter's executable | `build_output_missing` (S9) | already handed over |
| R4 | ends with 125 to 127 (C5) | `compiler_unavailable` (S6) | already handed over |
| R5 | ends with any other status (C6) | `build_exit_status` (S7) | already handed over |
| R6 | passes what B_t left (C10) | `build_time_limit` (S8) | already handed over |
| R7 | raises: C3, C4, C13 (named by C19); C11, C14, C17, C18 (rows of every container, not named by C19) | as each row says | already handed over; after C18 it is not written (cited: ADR-0108 decision 7) |

- **No row hands anything else over**, so the keeper is handed at most one log, the timing build's (cited for the rule: ADR-0108 decision 5).
- **A timing build that gives no log** (L3, L5 to L8) is not followed by the waiter's build: every such row ends the call (cited: ADR-0168 decision 2). A timing build that ended with 0 and left no executable (S9) ends the call after its log is handed over (cited: ADR-0169 L1).

### 4. What else the operation needed that no record decided

- **The flags of the waiter's build.** ADR-0145 decision 3 names "the flags of ADR-0116 decision 3" (cited) and no trailing flag. **This record reads that as those flags alone**: the waiter's build gets no trailing flag of ADR-0116 decision 4. The waiter includes no header but the system's (cited: ADR-0145 decision 3) and calls no function of `libm` (observation), so `-lm` adds nothing to it. ADR-0107 decision 3's sameness binds the builds that compile the kernel sources (cited: "the backend builds the kernel sources with one compiler, one list of flags, one list of trailing flags and one environment in the verification build of every check and in the timing build of every call"), and the waiter's build compiles none.
- **Nothing else.** Every other choice the operation makes is given to the code by an earlier record, or is answered by one, and is named in the module's docstring, not here. The names of the copies and executables are the code's (cited for the manner: ADR-0056 decision 4). Whether the operation's own work between the two builds counts against B_t is the code's (cited: ADR-0145 decision 3). The retry bound of the build directory's removal is the code's (cited: ADR-0096 decision 3). Where the build directory lies follows ADR-0056 decision 4 and ADR-0144 Q2 as `hilclaw/standin_check.py` reads them (observation). The open stream of a timing process with status 0 and no waiter's line stays open (cited: ADR-0168 decision 4), and the operation lets it pass.
- **The longest call is unchanged**: 60 + 1500 + 60 = 1620 s (cited: ADR-0169 decision 5, "For `sim.run` and `board.run` the two builds share B_t … so the same 1620 s holds"). A call holds at most one forced removal, and every container that does not end by itself ends the call (cited: ADR-0168 C10, C11, C18).

### 5. No new kind, file or member; the stop conditions

- **Every answer stays one of ADR-0168's** (C19 for the waiter's build, cited), so **no new value of `error.kind` or `condition`** is needed. **No new file, file name or member of the data plane**: the waiter's log is not kept (decision 2), and the timing build's log goes to the one file of its identity (cited: ADR-0108 decision 3). **The bytes rule of ADR-0078 decision 4 and ADR-0108 decision 4 is not touched**: the file holds what ADR-0169 decision 2 says, and nothing of a second process. This answers the stop conditions of task T-0481. Had keeping the log within those limits been the only defensible answer and impossible, this record would have stopped for the owner.
- **No owner-only decision was met.** No owner sentence keeps the waiter's log (decision 2, through ADR-0061 decision 7 and ADR-0108 Status). The reading of A-2 in decision 2 is made in the manner of ADR-0078 decision 2 and ADR-0108 decision 2: a record's own reading, stated, and open to the owner's objection. It reads the scope of "a build of an attempt", which those records used and did not define, and it removes no log either of them keeps.

### 6. The first code slice

- **`hilclaw/standin_run.py`**: the `cpu_standin` operation of `sim.run` and `board.run` (ADR-0144 slice (4), the run tools' part). It is one callable for both tools: "that the two operations may be one piece of code is the code task's" (cited: [ADR-0038](ADR-0038-od18-cpu-standin-execution-points.md) decision 2). It is called with the five things of `hilclaw/run_operation.py` `ask` and is bound to no backend table. In the order of ADR-0168's Walk-through and ADR-0145 decision 3 (cited), it does the following:
  - reads the image and makes the build directory;
  - copies the kernel files, the timing driver and the waiter's source;
  - runs the timing build, the waiter's build and the timing process in three containers;
  - hands the keeper the timing build's log by decision 3;
  - reads the timing process with `hilclaw/standin_answer.py` (cited: ADR-0168 decision 4);
  - returns the report and the figure as the plain pair that `ask` tells apart (observation);
  - gives every forced removal ADR-0169 decision 5's limit;
  - removes the build directory as ADR-0168 decision 5 says.
  It hands the compiler nothing derived from the seed (cited: ADR-0108 decision 4), imports no NumPy and reads no environment variable of its own. The steps it shares with the operation of `correctness.check` are made public functions of `hilclaw/standin_check.py`. `hilclaw/standin_copies.py` gains one function that copies a further harness program beside the first (observation: `place_copies` copies one).

### Walk-through (calls at a run of ADR-0144 decision 1; no step names a module)

| The call | What the builds give | Log in the file | The answer |
|---|---|---|---|
| `sim.run`; both builds ok; the waiter writes its line, status 0 | timing build: a warning; waiter's build: nothing | the timing build's warning | the report and the figure |
| `board.run`; the timing build fails to link | status 1 | `clang`'s errors | broken, `build_exit_status`; no waiter's build |
| `sim.run`; the timing build ok in 59.9 s; the waiter's build passes the 0.1 s left | ok, then timed out | the timing build's log | broken, `build_time_limit` |
| `sim.run`; the timing build ended ok and, with the operation's own work after it, nothing of the 60 s is left | ok; no waiter's build | the timing build's log | broken, `build_time_limit` (C19) |
| `sim.run`; the image's `clang` cannot compile the waiter | ok, then status 1 | the timing build's log, not the waiter's errors | broken, `build_exit_status` |
| `board.run`; the daemon stops between the builds | ok, then 125 | the timing build's log | `compiler_unavailable` |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | The waiter's log in a second file | A new file name of the data plane (decision 2 (a)). |
| 2 | The waiter's log joined to the timing build's | Two processes in a file of one, with no mark between them, and a hand-over moved (decision 2 (b)). |
| 2 | The waiter's log kept only when its build fails | Still (a) or (b) for that case, and a file whose content depends on which build failed. |
| 3 | Hand over the timing build's log after the waiter's build | Needed only by (b); a raised waiter's build would lose a log ADR-0169 decision 3 hands over. |
| 4 | The trailing flags in the waiter's build | ADR-0145 names the flags of ADR-0116 decision 3 only, and the waiter needs no `libm` (decision 4). |
| — | Leave the choice to the code task | The code would decide which compiler logs the data plane keeps. |

## Consequences

- **Slice for the planner** (code mode; D12 rules): **the `cpu_standin` entry of the default table** (cited: [ADR-0167](ADR-0167-od18-run-tools-registration.md) decision 3 and Boundaries), task T-0482. It binds `hilclaw.standin_check.operation` for `correctness.check` and `hilclaw.standin_run.operation` for `sim.run` and `board.run`.
- **Runtime acceptance items** (CLAUDE.md "개발 드라이버와 런타임의 구분"; not driver tasks — to be recorded by DRIVER §8, reason `runtime-acceptance`), on each kind of machine of C-7 with Docker, after the entry of T-0482 lands: **(lxxxi)** that the image's `clang`, with the flags of ADR-0116 decision 3, builds `timing_waiter.c` in a build container with status 0, writes nothing on either stream, and leaves the waiter's executable as a regular file at the matching path of the host's build directory (decision 2, the cost; with ADR-0145 item (lv) and ADR-0169 item (lxxx)); **(lxxxii)** that the two executables the build containers wrote in the build directory, under the numeric user of ADR-0144 decision 6, can be started by that user in the timing process container: the waiter as its program, and the timing executable by the waiter's `execv` (decision 6; with ADR-0145 item (liii)).
- **A-13 reading.** Code mode: the ADR and the slice land in one PR. **No new value of `error.kind` and no new value of `condition`; no file, file name, member, `step` value or version of the data plane is added, removed or changed**: the one file of a timing identity holds what ADR-0169 decision 2 says, and the waiter's log is not kept (decision 2). "Whether the meaning of a kind covers a case placed under it is caught by review only" (cited: ADR-0101 Consequences); this record states its reading of A-2 (decision 2) for that review and for the owner's objection. **This is therefore read as no "데이터 plane 스키마 변경".** No dependency is added; nothing is required of the development machine (D16).
- **Not edited and now less exact.** Found by reading the records of Context, and by grep on 2026-10-26 over `ARCHITECTURE/decisions/` and `hilclaw/` for "waiter's build", "is needed first", "the code slice's", "nothing calls it yet" and "the harness program of the build". In the records:
  - ADR-0108 decision 1. "The timing build: the one call … that the operation of a call makes; a call makes at most one", and "The log: everything the compiler process of that build wrote". A call at a run of ADR-0144 decision 1 now runs a second build, the waiter's, which is not the timing build and whose log is not kept (decision 2).
  - ADR-0108 decision 4. "its route out is the container's": decided by ADR-0169 for the timing build; the waiter's build has no route because its log is not kept.
  - ADR-0145 decision 3. "whether the operation's own work between the two counts against it is the code slice's": the code now counts it, as its docstring says. Its "with the flags of ADR-0116 decision 3" is now read as those flags alone (decision 4).
  - ADR-0145 Consequences. "ADR-0144 slice (4) then copies the waiter's source, makes the waiter's build within B_t and starts the timing process container with the waiter … it still waits on ADR-0144 decision 7's open answers": it now lands.
  - ADR-0169 decision 4. "Neither is chosen": decision 2 chooses. Also its Walk-through row "`sim.run`; the waiter's build fails — open (decision 4)": the file holds the timing build's log. Also its Boundaries bullet "The log of the waiter's build", now decided, and its Consequences, "the record of the waiter's build's log (decision 4) is needed first, or with it", now written, with the run tools' operations now landing.
  - ADR-0168 Consequences ("Slices for the planner"): the operations of `sim.run` and `board.run` now land.
  - ADR-0144 Consequences slice (4): its run tools' part now lands.
  - ADR-0167 Boundaries: the `cpu_standin` entry no longer waits on the run tools' operations.
  - ADR-0107 decision 3. Its sameness of flags and trailing flags is read as binding the builds of the kernel sources only (decision 4).

  In code, each docstring below is left as it is and stays true of its own module:
  - `hilclaw/standin_copies.py`: "the harness program of the build", one harness program per build directory; "nothing calls it yet". The docstring gains a paragraph for the new function and keeps these sentences.
  - `hilclaw/standin_waiter_line.py`: "What this module does not decide: what a call answers … for … a waiter's build that failed", already listed by ADR-0168.
  - `hilclaw/standin_answer.py`: "nothing imports it yet".
  - `hilclaw/standin_container.py` and `hilclaw/standin_image.py`: "nothing calls it yet".

## Boundaries (not decided here)

- **The size bound** of the log file, ⑲ (다) (cited: ADR-0108 decision 6), and of ⑱ (나) (cited: ADR-0078 decision 4).
- **What ADR-0169 Boundaries keep open** (cited) and this record does not answer. The rest of ⑲ (나): C14 and its kin, the sorting of the run tools' kinds for ADR-0140, and a timing process stream with status 0 and no waiter's line. The rest of ⑱ (마), with C14 for the check. ⑱ (라) and ⑲ (라)'s rest, and OpenMP (HQ-0034, owner-only). OD-14 sub-question ① (나), (라) and (마)'s rest. Leftovers of a dead operation and of a container created after its client was ended (ADR-0144 Boundaries; OD-8 ㉝ (나); OD-17). Whether a caller tells a machine without a container runtime from one without an image (OD-8 ㉝ (가)). The rest of the timeout hierarchy of OD-14 (ADR-0117 decision 6).
- **`profiler.collect`** (not offered on `cpu_standin`, cited: [ADR-0130](ADR-0130-od18-cpu-standin-profiler-collect.md)); a target on another machine (#5 B-2).
- **Owner-only (DRIVER §9)**: the #5 A and B items; OD-3; OD-25; C-6.
- **No sub-question is registered by this record.**

## References

- [Requirements](../Requirements.md): FR-6, FR-10, C-7; register row OD-18.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (⑲); [StandardScenarios](../StandardScenarios.md) S0, S1, S8.
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); ADR-0038 (decision 2); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decision 4); ADR-0061 (decision 7); ADR-0078 (decisions 2 to 4); [ADR-0096](ADR-0096-od18-check-build-directory-removal-failure.md) (decision 3); [ADR-0101](ADR-0101-od8-failure-kind-change-and-step-values.md) (Consequences); [ADR-0107](ADR-0107-od16-verification-and-timing-build-relation.md) (decision 3); ADR-0108 (Status; Context; decisions 1 to 7); ADR-0116 (decisions 3, 4); [ADR-0117](ADR-0117-od14-cpu-standin-time-limits.md) (decision 6); ADR-0130; ADR-0144 (decisions 1 to 3, 6; Q2, Q3; Consequences; Boundaries); ADR-0145 (decision 3; Consequences); ADR-0167 (decision 3; Boundaries); ADR-0168 (decisions 1, 2, 4, 5; C10, C11, C18, C19; Consequences); ADR-0169 (decisions 2 to 5; Walk-through; Consequences; Boundaries).
- `hilclaw/standin_run.py`, `hilclaw/standin_check.py`, `hilclaw/standin_copies.py`, `hilclaw/standin_answer.py`, `hilclaw/standin_waiter_line.py`, `hilclaw/run_operation.py`, `hilclaw/harness/timing.py`, `hilclaw/harness/timing_build.py`, `hilclaw/harness/timing_waiter.c`, `tests/harness/test_timing_waiter.py`; task T-0481.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §8, §9; CLAUDE.md "개발 드라이버와 런타임의 구분" (D16), "브랜치·merge 절차" (A-13).
