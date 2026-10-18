# ADR-0096: What the operation of `cpu_standin` for `correctness.check` does when the removal of its build directory fails, in whole or in part — the answer of the call stands as the build and the run established it, and what is left stays (first part of part (다) of sub-question ⑰ of OD-18)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences are those of the owner decision of 2026-10-15, item 1 (O1, Context), quoted word for word; they are not re-decided and are not subject to the 7-day window. What a requirement, an accepted record or a file of `hilclaw/` says is **cited** with its source. **Everything else is this record's own design**: the answer of decision 2, the rules of decision 3, and every weighing.
- Answers **one point of part (다) of sub-question ⑰ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)): "what an operation does when the removal of its build directory fails, a process that outlived its limit and still writes there included" (cited: [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) Boundaries). The other points of (다) stay open (decision 5). OD-18 keeps its status word.
- **Nothing of the data plane changes**: no member of a result, a request, `instance.json`, `build.json`, `artifacts.json`, a spec or a line of `events.ndjson`; no value of `condition` or of `error.kind`; no reserved kind; no path, layout or `schema_version`.
- It builds on ADR-0056 (decisions 2, 4 and 5; its window runs until 2026-10-20), [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decisions 2, 3, 4, 6 and 7; until 2026-10-22), [ADR-0047](ADR-0047-od18-correctness-check-operation-tool-failure.md) (decisions 4 and 5; until 2026-10-19) and [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md) (decision 3; until 2026-10-23). **If ADR-0056 or ADR-0060 is reverted, this record falls with it**; if ADR-0079 is, decision 2 stands on its own reasons.
- **It is a record, not code**: decision 1 was read from `hilclaw/check_build.py`, `hilclaw/check_failure.py` and `hilclaw/scratch.py` at `1ea1fd2` as files; nothing was established by running code, and no compiler, container or `claude` process was started. It binds no code until the code task of Consequences lands.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).
- **Edited after acceptance on 2026-10-18** by task T-0290 (document mode): the third "Why" bullet of decision 2 is headed "The next call never uses a leftover" and its last clause adds what a survivor writes outside the leftover to the space a leftover takes; the bullet that says what this record builds on gives the windows of ADR-0047 and ADR-0079; References lists ADR-0004 and ADR-0078, which the body cites. No decision changed meaning, and the objection window of the notice https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6244972784 is unchanged.

## Context

- **The open point.** "the operation removes the build directory, with everything in it, before its call returns or raises — after a report, a condition or a tool failure alike. What an operation does when that removal fails, in whole or in part, is not decided (sub-question ⑰ (다)): this record says neither that a failed removal changes the answer of a check nor that it does not" (cited: ADR-0056 decision 4). ADR-0079 decision 3 answered a failed removal of `clang_build`'s temporary file by the build it carries and said of the directory: "this record does not decide it either" (cited).
- **What can hold the directory.** "On a timeout only the process it started is killed, not that process's children" (cited: ADR-0056 decision 2, itself citing `hilclaw/clang_build.py`); "A survivor of a build or of a verification process can hold the build directory, or write into it, while the operation removes it and after" (cited: ADR-0056 decision 2). The death of the tool function's process "may leave a build directory behind" (cited: ADR-0056 decision 5).
- **O1 (owner, 2026-10-15, item 1)**: "The toolchain, the build of a kernel, its correctness run and its timing run use an isolated environment: a container, as for the coder call (ADR-0049)." Its design is OD-14 sub-question ①; what it adds to S1 to S10 is OD-18 ⑱ (다). Neither is answered.
- **Why now**: `hilclaw/check_build.py` (T-0285) gives every returned or raised build its row or leaves it unplaced; the operation of `cpu_standin`, which removes the directory, is the next code, and without this record it would make the choice unrecorded.

## Decision

Terms: **the build directory** is the directory ADR-0056 decision 4 places — made by the operation of `cpu_standin` for one call, outside both checkouts, its working directory for the compiler and the verification process. **The answer** of a call is what the operation returns or raises: a report (A), a condition (B) — `"build_time_limit"` and `"build_exit_status"` among them (ADR-0060 decision 4) —, a tool failure of a backend kind, or an error it lets pass. **A failed removal**: after the operation's removal, the build directory or anything below it still exists, or the removal raised an `Exception`.

### 1. What the code does today (observation, binds nothing)

- No module of `hilclaw/` makes or removes a build directory. `hilclaw/check_build.py` "calls no build, starts no process, removes no directory and raises no tool failure" (cited: its docstring); `place_error` answers a `TemporaryNotRemovedError` by its carried build (ADR-0079 decision 3). `hilclaw/check_failure.py` holds eight backend kinds, none for a removal.
- `hilclaw/scratch.py` removes a coder's scratch with `shutil.rmtree`, tries again "a few times within about two seconds", and `remove` "only reports whether the scratch is gone"; a scratch whose removal failed is left to "ADR-0049 sub-question ㉝ (나)" (cited: its docstring). That is the coder scratch's rule, cited as an analogue; it binds nothing for the build directory.

### 2. The answer stands; what is left stays

- **A failed removal, in whole or in part, changes no answer.** The operation returns or raises what it would have returned or raised had the removal succeeded, for every kind of answer:

| The answer before the removal | After a failed removal |
|---|---|
| A report (A) | The same report |
| A condition (B), `"build_time_limit"` and `"build_exit_status"` included | The same condition |
| A tool failure of a backend kind, one `check_build.place_error` gives included | The same kind and message |
| An `Exception` the operation lets pass (one `place_error` does not place: it answers `None`; the landed answer is `operation_answer_invalid` — cited: ADR-0045 decisions 4 and 5) | The same error passes |
| A request to end (`KeyboardInterrupt`, `SystemExit`) | It passes as it is; the identity stays open (cited: ADR-0060 decision 6) |

- **The removal raises nothing past the operation**: no `Exception` of the removal replaces, wraps or is chained into the answer, and the failed removal is in no answer and no message, as ADR-0079 decision 3 has it for the temporary file. **A request to end (`KeyboardInterrupt`, `SystemExit`) that arrives during the removal is no failed removal in this sense and is not swallowed**: it passes, and the identity stays open, as for any raised request to end (cited: ADR-0045 decision 5, "it passes through the tool function unchanged"; ADR-0060 decision 6). **What is left — the directory, or what of it remains — stays where it is.** The operation removes nothing else to make up for it.
- **Why** (this record's own).
  - *What was established.* A report or a condition says what the experiment established about the attempt; a tool failure, why none was. The removal comes after both and adds nothing to either; "the failed removal says nothing about the attempt" (cited: ADR-0079 decision 3).
  - *The attempt cannot steer the answer.* Whatever the attempt's own code started — a child of the verification process or of the compiler that outlived its limit (ADR-0056 decision 2) — can keep the directory busy or write into it. If a failed removal changed the answer, a kernel that fails its check could turn the fail into a tool failure, which "says that no outcome was established" (cited: ADR-0010 decision 4), and the caller could ask for a further `execution` (⑭). That is a manipulation of the verdict by the candidate, the class of OD-16 threat A, against the FR-9 hard floor ("검증을 통과하지 못한 결과는 best·통계에 반영하지 않는다"). Under this decision the verdict is fixed before the removal and nothing in the directory reaches it.
  - *The next call never uses a leftover.* Each call makes a new directory that no other call uses (cited: ADR-0056 decision 4), and decision 3 has the name of a new one drawn so that it is never an entry that exists. So a leftover is never a directory a later call builds or runs in, and a name it holds is drawn around. "No outcome depends on anything an earlier call left" (cited: ADR-0056 decision 4, way (a), after ADR-0016 decision 2 (c)) holds for the name and the content of the directory, **not for the space a leftover takes, nor for what a survivor writes outside the leftover** (next bullet).
- **The cost, stated.** A leftover takes disk space, and a survivor goes on running unconfined, as ADR-0056 decision 2 already says of it. **Nothing records a leftover**: no member of the end line and no file of the data plane holds one, and this record adds none (decision 5). **A leftover, or a survivor, can still reach a later call through what the machine shares**: one that fills a disk can make a later call — of another candidate too — meet S3, a tool failure `build_directory_unusable`, or S7, a broken result — in either case one whose cause is "not established" (cited: ADR-0060 decision 2). A survivor can also write into a later call's build directory, as "a process that writes under an absolute name writes where it can" (cited: ADR-0056 decision 4). Answering a tool failure instead (alternative (b)) prevents neither; what bounds them is the resource ceilings and isolation of OD-14, and the clearing of decision 5.

### 3. Rules for the code that removes

- **A new directory per call.** The operation makes its build directory under a name no existing entry has: where the name it drew is taken, it draws another, as `tempfile.mkdtemp` does, and it never reuses an entry that is there. A name that is taken is therefore not S3 in itself; a directory that cannot be made or written — after the code has given up drawing names, among others — stays S3, `build_directory_unusable`, as ADR-0060 decision 4 has it. How the name is drawn, and how often, is the code's.
- **Trying again is allowed, bounded by the code.** The operation may try the removal again before it returns or raises, as `hilclaw/scratch.py` does. **The bound is the code's**: a fixed, finite constant of the module until OD-14 states otherwise; this record neither gives it a value nor places it outside OD-14. Whether and how often it tries changes nothing of decision 2.
- **Nothing outside the directory.** A removal follows no symbolic link met below the build directory: it removes what lies below it and nothing a name in it points to — the rule ADR-0049 P4 gives a scratch, applied here as this record's own. **This record adds** that no step before a retry changes anything outside the directory either. The kernel's process works in the directory and can place a link there. A note for the code task: the step `hilclaw/scratch.py` takes before a retry leaves a race in which a link's target is given owner bits (cited: its docstring, "the same race, not closed either"), and its `shutil.rmtree`, where `shutil.rmtree.avoids_symlink_attacks` is false (Windows; C-7 presumes WSL), leaves "a name swapped for a link during the removal" as "a race this module does not close" (cited: the same); copied as they are, neither meets this rule.

### 4. Where the answer applies, and the container

- Decision 2 is stated for the build directory of ADR-0056 decision 4 on the host, which is where builds run until a record replaces the host process (cited: ADR-0060 decision 2, "ADR-0056 decision 2 holds as written").
- **What O1's container may change, and is not decided here**: whether the build directory is then a host directory, a mount or a path inside the container; whether the removal of a container ends a survivor and takes its files (for the coder's container: ADR-0049 decision 4, "not verified" (L1)); and the situations the environment adds. That is OD-14 sub-question ① and ⑱ (다); their records say whether decision 2 holds there. What a dead process leaves is decision 5 (with OD-8 ㉝ (나)). This record decides nothing of the container.

### 5. What stays open of part (다) of sub-question ⑰

- **A record of the source bytes and settings a check was built from** (NFR-2) — placed with `build.json` (ADR-0004 decision 3; OD-6 sub-question ②) and with the identification of the image (OD-14 ① (나)).
- **Whether a verification executable is ever kept**, and under which retention class of C-3 — placed with the retention classes (C-3, #5 A-2 — owner's) and with a need to reproduce a fail (OD-10, OD-16).
- **What clears a build directory a failed removal or a dead process left** — placed with ㉝ (나) for the scratch, OD-10 and OD-17: it needs the place and name of the directory (the code task's), a way to tell a leftover from the directory of a live call (the lock, OD-17), and the container of O1.
- **Whether anything records the finding** that a removal failed or a leftover was met — a point this record adds to (다), which did not ask it; placed with the event log content (PLAN P1-8; OD-17) and OD-10.

## Alternatives considered

| Alternative | Why not |
|---|---|
| (a) The answer stands and the directory is left | **Adopted** (decision 2). |
| (b) The call answers a tool failure of a new backend kind ("the build directory could not be removed"), which ADR-0047 decision 5 would allow if named with that situation | It replaces an established report or condition with "no outcome was established", which is false of the experiment, and hands the attempt's code a way to turn its own fail into a tool failure (decision 2). After a tool failure it replaces the more exact kind of what failed. It records the leftover only by losing the answer. |
| (b') The answer stands and the error of the removal is raised as well | An exception that leaves a `finally` replaces the answer, which is (b) by accident. |
| (c) Try again for a bounded time, then (a) or (b) | Adopted with (a) only, as a choice of the code (decision 3). A bound of the record would be a time-limit value, which OD-14 holds and this record does not set; and a retry does not settle a survivor that keeps writing. |
| (d) Leave the point open | The operation of `cpu_standin` is the next code and removes the directory; it would make the choice unrecorded. Nothing undecided is needed for (a): no value, no member and nothing of the container. |
| The operation kills what still holds the directory | It cannot tell what holds it, and ending processes the call did not start directly is the sandbox and process control of OD-14. |
| The operation moves what is left to a quarantine place | A new place on the machine with no rule for clearing it — the open point of decision 5, moved. |

## Consequences

- **The code task** (code mode, one task, together with the rest of the operation; nothing is written here): the operation of `cpu_standin` for `correctness.check` — in a module of `hilclaw/` not yet on `main`, whose name is the code task's — makes its build directory under a new name (decision 3), removes it in a `finally` that lets no `Exception` of the removal past the operation and lets a request to end pass, may try again within a constant of its own, follows no link, and returns or raises the answer it had. Its tests show, with a removal made to fail, that each row of decision 2 is unchanged. **`hilclaw/check_build.py` and `hilclaw/check_failure.py` do not change**: no kind is added, and `check_build`'s "removes no directory" stays true. The operation still waits for T-0243 / HQ-0026 (cited: T-0289 Follow-ups), and the values of its settings are open (ADR-0060 decision 3; ⑱ (라); OD-14).
- **Not edited and now less exact.** ADR-0056 decision 4 ("What an operation does when that removal fails, in whole or in part, is not decided (sub-question ⑰ (다))"; "this record says neither that a failed removal changes the answer of a check nor that it does not") and its sub-question ⑰ (다) where it asks this point; ADR-0060 decision 7 ("(다): not answered") and its Boundaries ("a failed removal of the build directory"); ADR-0079 decision 3 ("this record does not decide it either"); ADR-0060 Boundaries, sub-question ⑱ (다) ("The situations an isolated environment adds … and how S3 to S10 read inside it"), which its register bullet now extends by whether this record holds there. No earlier ADR is edited.
- **Provisional choices**: that a retry is the code's; that the link rule of ADR-0049 P4 applies to the build directory.
- **A-13 reading**: document mode; no code, dependency, settings file or schema file changes, and no member, value or kind of the data plane is added.
- **Runtime acceptance items**: none beyond ADR-0056's.

## Boundaries (not decided here)

- Everything decision 5 lists; the container and its design (OD-14 ①; ⑱ (다)); every setting and time-limit value (OD-14; ⑱ (라)).
- What stops a process that outlived its limit, and resource ceilings (OD-14); the compiler's log file and its keeper (ADR-0078; T-0243, HQ-0026).
- The coder scratch and its leftovers (ADR-0049; OD-8 ㉝).
- Retention, GC and `gc_at` (C-3, #5 A-2, OD-25 — owner-only).
- Code, tests, CI and any settings file.

## References

- [Requirements](../Requirements.md): FR-9, FR-10, NFR-2, NFR-4, C-3; register rows OD-8, OD-10, OD-14, OD-16, OD-17, OD-18.
- [OpenDecisionProposals](../OpenDecisionProposals.md): [OD-18](../OpenDecisionProposals.md#od-18) (⑭, ⑰, ⑱), [OD-14](../OpenDecisionProposals.md#od-14) (①), [OD-16](../OpenDecisionProposals.md#od-16) (threat A), [OD-8](../OpenDecisionProposals.md#od-8) (㉝); [StandardScenarios](../StandardScenarios.md).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0004](ADR-0004-od8-data-plane-layout.md) (decision 3); [ADR-0010](ADR-0010-od18-tool-exposure-form.md) (decision 4); [ADR-0016](ADR-0016-od18-backend-frame.md) (decision 2 (c)); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4, 5); ADR-0047 (decisions 4, 5); [ADR-0049](ADR-0049-od8-coder-call-isolation-means.md) (decision 4, P4, L1, ㉝); ADR-0056 (decisions 2, 4, 5; Boundaries); ADR-0060 (decisions 2, 3, 4, 6, 7; Boundaries); [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (the compiler's log file); ADR-0079 (decision 3).
- Owner decision of 2026-10-15 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6182984913 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; `hilclaw/check_build.py`, `hilclaw/check_failure.py`, `hilclaw/scratch.py`; tasks T-0285, T-0289.
