# ADR-0082: A `CompilerRunError` of `clang_build.build` whose `timed_out` is true is S8 for a check of `correctness.check`, and the other branch stays open (more of part (마) of sub-question ⑱ of OD-18)

## Status

- **Accepted on 2026-10-17** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences are quoted word for word and are not subject to the window below: O1 and O2 of [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) Context, as that record quotes them. What a requirement or an accepted record says is **cited** with its source. **Everything else is this record's own design**: that the time-limit branch is S8, the reading of S8 and of O1 that this rests on, that a `log` of `None` is handed over as nothing, the reading of ADR-0078 decision 2 for a compiler whose end was not seen, that the `removal_error` changes nothing, that the other branch stays open, and every weighing. Statements about code are **observations** at `d3becf0` of what `build` states (its members and docstrings) and bind no code; names and modules stay the code tasks'.
- Answers **more of part (마) of sub-question ⑱ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)) for `correctness.check` of the first case and of the mock: **the row of a `CompilerRunError` whose `timed_out` is true** (decision 2) and what happens to its `log` (decision 3). It leaves **the row of a `CompilerRunError` whose `timed_out` is false** open (decision 4), and the rest decision 5 names. Parts (가), (다), (라) and the size bound of (나) are not answered. OD-18 keeps its status word.
- **No member of any file, result, request or line is added or changed; no value of `condition` and no value of `error.kind` is added, no kind is reserved, and no `schema_version` and no layout version changes.**
- **No sentence of an earlier record is replaced or edited.** Consequences lists the sentences that become less exact.
- It builds on [ADR-0081](ADR-0081-od18-correctness-check-compiler-run-error.md) (K1 to K4, decisions 1 to 3 and 5; its window runs until 2026-10-24), ADR-0060 (Context O1 and O2, decisions 4 and 5; until 2026-10-22), [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decisions 2, 6 and 7; until 2026-10-23), [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md) (decisions 1, 3 and 5; until 2026-10-23), [ADR-0080](ADR-0080-od18-correctness-check-build-errors-now-told-apart.md) (decisions 2 and 4; until 2026-10-23) and [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 4 and 5; until 2026-10-20). **If one of them is reverted, this record falls with it.** Single sentences rest on [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4 and 5).
- **It is a record, not code, and nothing was built or run**: no compiler, container or `claude` process was started.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0081 decision 2 left the row of `CompilerRunError` open and named what would let a later record place it: "A code change of `clang_build.build` that tells the time-limit branch apart, by a class or by a member of the error, and keeps the output read so far. Then a record can weigh S8 with its log for that branch", and "A record for the other branch, a compiler the call lost while it ran", which "may need a new value of `error.kind`".
- Task T-0251 (PR #159, `d3becf0`) made the first change.
- **Observations at `d3becf0`** (`hilclaw/clang_build.py`; what `build` states, not the exception chain and not private state of `Popen`; no code is bound):
  - **L1.** `CompilerRunError` has the keyword-only members `timed_out` and `log` beside `removal_error`; its classes (ADR-0081 K3) are unchanged. The `build` docstring: its "`timed_out` says whether the time limit had passed before the error and whose `log` is the output read so far, or `None` when none was held".
  - **L2.** The class docstring: "`timed_out` is true when the time limit had passed before the error: the error came from killing the compiler for its time limit, from reading or waiting for it after that kill, or from closing the process afterwards. It is false for an error from the first read, from killing the compiler after that read failed, or from closing the process after a read that ended."
  - **L3.** The same docstring: "`log` is the output the call held when the error was raised, decoded as `BuildResult.log` is: after the time limit, the output read before it and anything read after the kill; after a read that ended, all of it. It is `None` when the call held no output: after the first read failed, or when the time limit passed before any output was read and nothing was read after the kill. On Windows the output is read only after the kill, so a failed kill or a failed read after it leaves `None`. `None` does not mean that the compiler wrote nothing."
  - **L4.** So, after the time limit, `log` holds what the call had read before the failed step, and on Windows it is not `None` only when the error came from closing the process after the read that followed the kill (L2, L3). In the other branch, `log` is not `None` only after an error from closing the process after a read that ended (L2, L3).
  - **L5.** Neither the members nor the docstrings say whether the compiler had ended when the error was raised.
- **Cited, not observed here**: ADR-0081 K2 observed, at `065113b`, that a failed kill leaves the exit of `with process:` waiting for the compiler without a limit, and ADR-0081 decision 3 that an error of that exit itself leaves its end unseen.
- No owner comment on #5 speaks to ADR-0081, `CompilerRunError` or ⑱ (마) (checked on 2026-10-17; every comment since 2026-10-16 carries the driver tail).

## Decision

### 1. Scope and terms

- A call of `correctness.check` as ADR-0081 decision 1 has it. The six kinds, S1 to S10 and the keeper are as ADR-0079 decision 1 has them. **The time-limit branch** is a `CompilerRunError` whose `timed_out` is true; **the other branch** one whose `timed_out` is false. **The mock** builds nothing and is unchanged.

### 2. The time-limit branch is S8, (B) `"build_time_limit"`

- **The operation answers a `CompilerRunError` whose `timed_out` is true as S8**: it returns the form (B) `"build_time_limit"` (cited: ADR-0060 decision 4), and the tool function makes the broken result as for any S8 build.
- **Why.** "What the operation observes decides the row" (cited: ADR-0060 decision 4). It now observes, from what `build` states, that the time limit had passed before the error (L1, L2). S8 is "The build passes its time limit" (cited: ADR-0056 decision 5), and O1 (**the owner's**) makes it a result: "One each: `build_exit_status` for S7 and `build_time_limit` for S8." The error came afterwards, from the steps by which the call ends a build past its limit (L2). **This record reads S8 and O1 as reaching such a build**: the experiment established that the build did not end within its limit, and a later failure to kill, read or close the process says nothing about the attempt, as ADR-0079 decision 3 has it for a failed removal after the end. A tool failure would answer against O1, which is the stop ADR-0081 decision 2 named.
- **That the end of the compiler is not always seen** (L5; ADR-0081 K2 and decision 3) does not change the row. S8 is dated "⑥, the build ended" (cited: ADR-0060 decision 4) and found when "the build ended; `ok` false" (cited: ADR-0056 decision 5); **this record reads both as the end of the call of the build**, which the call reached, and not as a statement that the compiler process was seen to end, and reads `ok` false as the build not having ended ok, which the error shows without a `BuildResult`. The time limit passed before any of the failed steps, so how the compiler ended, or whether it was seen to, comes after what S8 classes. **The cost, stated**: after a failed kill the call waits for the compiler without a limit and can outlast the time limit (ADR-0081 K2, observed at `065113b`), so the call raises, and the check is answered S8, only once the compiler has ended by itself; after an error of the exit of `with process:`, a compiler may still run when the operation removes the build directory, and may write in it afterwards — a failure of that removal is ⑰ (다), as ADR-0080 decision 2 has it for a compiler process that may exist. Neither cost changes with the row.
- **The operation can apply it from what `build` states alone**: the class and its member `timed_out` (L1). It reads no exception chain and no private state.
- **The `removal_error`** changes nothing, as ADR-0081 decision 2 has it for the class: the answer is S8 with or without it, and the failed removal is in no answer and no message, since the file left behind is a file of the build directory, whose removal is ADR-0056 decision 4's and whose failure is ⑰ (다).

### 3. The log of the time-limit branch

- **When `log` is not `None`, the operation hands it to the keeper before it returns**, as for the log of any S8 build (cited: ADR-0078 decisions 2 and 6); a write that fails is answered as ADR-0078 decision 7 says. It is the output the call held (L3, L4). O2 (**the owner's**: "Kept, not returned: in a file of the attempt, never in the result or in `events.ndjson`") applies to it as ADR-0060 decision 5 applied it to S7 and S8.
- **When `log` is `None`, the operation hands nothing over.** An empty text would say that the compiler wrote nothing, which `None` does not mean (L3). The file is then missing, which says that the log "did not reach the tool function" (cited: ADR-0078 decision 2), and that is so.
- **The cost, stated.** A `None` loses the log of an S8 build, against O2 and against the letter of ADR-0078 decision 2 where the compiler ended. On Windows that is every failed kill and every failed read after it (L3). No row, chosen or open, brings it back: the output is not held by the call. Where the compiler's end was not seen (L5), the log handed over is kept although ADR-0078 decision 2 names a compiler that "has ended"; **this record reads that sentence as not forbidding it**, as the text is the output of a compiler killed for its time limit or past it. If that write fails, the sentence of ADR-0078 decision 7 that a caller may rely on, "its compiler ended", is less exact for it (Consequences).

### 4. The other branch stays open

- **The row of a `CompilerRunError` whose `timed_out` is false stays open under (마)**, for the reason of ADR-0081 decision 2: no wording of S3 to S10 names a compiler the call lost while it ran, and this record reads none of them to cover it. A record that adds the situation to the list of ADR-0056 decision 5 may need a new value of `error.kind`, and this record adds none.
- **What has changed since ADR-0081**: `log` is no longer always absent in this branch. It is not `None` after an error from closing the process after a read that ended, and then it is all the output (L3, L4). Whether an operation hands that log over is part of the open row; until a record places it, an operation that lets the error pass is answered `operation_answer_invalid` (cited: ADR-0045 decisions 4 and 5), and "That says what the landed rules do with it; it is no answer of this record" (cited: ADR-0060 decision 4).

### 5. How far (마) is answered

- **Answered now, for `correctness.check` of the first case and of the mock**: the row and the log of the time-limit branch of `CompilerRunError`, with or without a `removal_error` (decisions 2 and 3).
- **Open under (마)**: the row of the other branch (decision 4); the removal error raised in place of an exception that is no `OSError` (ADR-0081 K4 (ii)); the classes of the path tests of ADR-0080 decision 4; and the other entries ADR-0079 decision 5 names, as ADR-0080 decision 4 lists them.

### Walk-through

The names of ADR-0056: run `r1`, `round` 3, `candidate` 2, `attempt` 1, `"execution": 1, "point": "sim"`.

| The build | `clang_build.build` | The operation | The caller gets |
|---|---|---|---|
| Not on Windows, the build passes its time limit; waiting after the kill fails | `CompilerRunError`, `timed_out` true, `log` the output read before the limit (`None` if none was read) | hands the log over (nothing when `None`); (B) `"build_time_limit"` | a broken result, `condition` `"build_time_limit"`; the log in its file (no file when `None`) |
| On Windows, the build passes its time limit; killing the compiler fails | `CompilerRunError`, `timed_out` true, `log` `None` | hands nothing over; (B) `"build_time_limit"` | the same result; no file of the log |
| The same, and the temporary file cannot be removed | the same, with a `removal_error` | the same | the same |
| Reading the pipe fails while the compiler runs | `CompilerRunError`, `timed_out` false, `log` `None` | open under (마) (decision 4) | — |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | **(a)** S8, `"build_time_limit"` (chosen) | It answers what the operation observes (L2) with the row O1 gives it, from what `build` states. The cost: S8 is given where the compiler's end was not seen (decision 2), on this record's reading of S8 and of its moment. |
| 2 | **(b)** Leave it open | The stop of ADR-0081 decision 2 for this branch was that nothing `build` states tells it apart; it now does (L1). Left open, the landed rules answer it `operation_answer_invalid`, a tool failure, against O1, and no record has the operation hand the log the call holds to the keeper. No reason remains that a row would break. |
| 2 | **(c)** S8 only when `log` is not `None`, otherwise open or a tool failure | The row would depend on the platform (L3) and not on the build, and the build passed its time limit either way. The log is lost under any row when the call held none (decision 3). |
| 2 | **(d)** S8 only when the compiler's end was seen | `build` does not state it (L5), so the operation could not apply it. A code change that states it would split one S8 build into two answers by a step after the time limit. |
| 2 | **(e)** An existing kind (`compiler_unavailable`, `build_output_missing`, `build_directory_unusable`, `build_input_missing`, `settings_refused`, `executable_unstartable`) | Each names a situation the class does not show (cited: ADR-0060 decision 4), and each answers a build past its time limit with a tool failure, against O1. |
| 2 | **(f)** A new value of `condition`, or a new kind | A new value of `condition` is a data-plane change (CLAUDE.md A-13; ADR-0060 Context). A new kind would answer a build past its time limit with a tool failure, against O1. Neither is needed: S8 has its value. |
| 3 | Hand an empty text over when `log` is `None` | The file would then say that the compiler wrote nothing, which `None` does not mean (L3). |
| 4 | Place the other branch now, by reading S6, S7 or S9 to cover it | S6 is "its process cannot be started", and it was started; S7 needs a non-zero status and S9 starts with "Status 0" (cited: ADR-0056 decision 5; ADR-0060 decision 4), and no status is stated. ADR-0081 alternatives (a), (b) and (d′) hold unchanged. |

## Consequences

- **Code** (code mode, D12 rules; names and modules are the code task's; **this record binds no code**): the operation of `cpu_standin` for `correctness.check`, when it is written, answers a `CompilerRunError` whose `timed_out` is true with (B) `"build_time_limit"` and hands its `log` to the keeper when it is not `None`; it leaves the other branch to the landed rules. No change of `clang_build.build` is needed for this. A code task that makes `build` state whether the compiler's end was seen would change no row of this record.
- **Not edited and now less exact** (ADR-0081 unless another record is named):
  - K1's class docstring ("It has no `result`: the output read so far is not kept.") and K2's "Neither the class, its members nor the docstring say which branch it came from, whether a time limit passed, or what the compiler wrote."
  - Decision 2: "no log and no return code reach the operation. The time-limit branch is not told apart (K2)", and its cost, "a call of the class whose build passed its time limit (K2) is still answered by a tool failure, against O1", which no longer holds.
  - Decision 3: "Its log reaches neither the operation nor the keeper, because the class keeps no output (K1)", and its cost, which now holds only where `log` is `None` and in the other branch.
  - Decision 5 and Boundaries: "the row of `CompilerRunError`", now the row of the other branch.
  - The walk-through rows "The build passes its time limit; killing the compiler fails" and "The same, and the temporary file cannot be removed" ("open under (마)"); alternative (c) ("nothing `build` states tells the time-limit branch apart (K2), so the operation cannot apply it"); and alternative (e)'s cost ("until then the landed rules answer it with a tool failure, so a call past its time limit is still answered against O1").
  - Decision 3: "The code change of decision 2 brings it back." It does only where `log` is not `None` (L3).
  - The alternatives row of point 3: "The code change of decision 2 keeps that output too." A compiler killed for the call's own error follows a failed first read, after which `log` is `None` (L3).
  - ADR-0078 decision 2, as ADR-0081 Consequences already listed it for the time-limit branch: its log is now lost only where `log` is `None` (decision 3).
  - ADR-0078 decision 7, the sentence a caller may rely on ("its compiler ended"), for a log of the time-limit branch that was handed over although the compiler's end was not seen and whose write then failed (decision 3, L5).
  - Consequences, Code: the operation "leaves `CompilerRunError` to the landed rules until a record places it", which now holds for the other branch only; and "A code task may tell the time-limit branch apart and keep the output read so far (decision 2)", which T-0251 did, keeping no output where the call held none (L3).
- **A-13 reading.** Nothing of the data plane is added or changed: no member, no value of `condition` or `error.kind`, no file, no version.
- **Runtime acceptance items**: none. Which of these errors a real machine produces is the code tasks' observation.

## Boundaries (not decided here)

- **The row of the other branch** of `CompilerRunError`, and whether its `log` is handed over (decision 4).
- **The other open entries of (마)** (decision 5), and any code change that tells them apart, the removal error of ADR-0081 K4 (ii) included.
- **⑱ (가), (다), (라) and the size bound of (나)**; the situations a container adds (OD-14 ①).
- **⑰ (다)**, including a build directory that cannot be removed because a compiler still runs in it, and a temporary file left in it.
- **The timing build of `sim.run` / `board.run`** and `local_run.run` (⑲).
- **Owner-only (DRIVER §9)**: the #5 A and B items; OD-3; OD-25; C-6.
- Any change to ADR-0001 to ADR-0081, to UsageCases, to `hilclaw/`, to tests, to CI or to any settings file; any new external dependency; any new reserved `kind`.

## References

- [Requirements](../Requirements.md): FR-6, FR-10; register row OD-18.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ⑰, ⑱).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4, 5); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 4, 5); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (Context O1, O2; decisions 4, 5); [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decisions 2, 6, 7); [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md) (decisions 1, 3, 5); [ADR-0080](ADR-0080-od18-correctness-check-build-errors-now-told-apart.md) (decisions 2, 4); [ADR-0081](ADR-0081-od18-correctness-check-compiler-run-error.md) (K1 to K4; decisions 1 to 3, 5; walk-through; alternatives).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/clang_build.py` at `d3becf0`; tasks T-0249, T-0250, T-0251 (PR #159).
