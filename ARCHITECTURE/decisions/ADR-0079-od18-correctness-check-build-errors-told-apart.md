# ADR-0079: Where a check of `correctness.check` places the errors of one `clang_build.build` call that the code now tells apart — a failed move of the artefact is S9, a failed removal of the temporary file alone is answered by the build the error carries, and an `OSError` from starting the compiler is S6 where the operation can tell that it came from the start (part of part (마) of sub-question ⑱ of OD-18)

## Status

- **Accepted on 2026-10-17** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences are quoted word for word and are not subject to the window below: O1 and O2 of [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) Context (the answer to HQ-0020, points 1 and 2). What a requirement or an accepted record says is **cited** with its source. **Everything else is this record's own design**: the row of each error of decisions 2 to 4, and every weighing. Statements about code are **observations** at `7003362` and bind no code.
- Answers **part (마) of sub-question ⑱ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)) for `correctness.check` **only for the entry of `clang_build.build` that ADR-0060 decision 4 names as "an `OSError` from starting the compiler (S6) or from moving the artefact (S9)", "an `OSError` from starting the compiler for a missing working directory (S3) or a compiler that cannot be started (S6)" and "an `OSError` of `clang_build.build` from removing its temporary file"**, as far as decisions 2 to 4 say: for the start of the compiler it fixes the row, while telling such an error apart from errors of the same class before the start or after the end stays the code's (decision 4). The other entries of (마) stay open and are named in decision 5. Parts (가), (다), (라) and the size bound of (나) are not answered. OD-18 keeps its status word.
- **No member of any file, result, request or line is added or changed; no value of `condition` and no value of `error.kind` is added, no kind is reserved, and no `schema_version` and no layout version changes.** Every answer is one of the six backend kinds of ADR-0060 decision 4, or the outcome the build carried by the error shows.
- **No sentence of an earlier record is replaced or edited.** Consequences lists the sentences that become less exact.
- It builds on ADR-0060 (decision 4; its window runs until 2026-10-22), [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 4 and 5; until 2026-10-20) and [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decisions 2, 6 and 7). **If one of them is reverted, this record falls with it.**
- **It is a record, not code, and nothing was built or run**: no compiler, container or `claude` process was started.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0060 decision 4 lists errors that one call raises "in one class" for two rows, and its Consequences say: "The code task that writes the operation makes them distinguishable — for example by a change of those functions, binding nothing here — or registers what it cannot tell apart; this record gives no kind to an error of two rows (⑱ (마))." Of an error from removing the temporary file it says that the landed rules answer it `operation_answer_invalid` (cited: ADR-0045 decisions 4 and 5) and that "it is no answer of this record".
- ADR-0078 decision 2 keeps "The log of every build whose compiler process was started and has ended", S9 included; its Consequences slice (4) noted that `clang_build.build` passed on the errors from moving and removing "without the log". Task T-0244 changed that function (PR #155, `7003362`) and left the rows open: "This task does not say which row or answer any of them maps to."
- **Observations at `7003362`** (`hilclaw/clang_build.py`; no code is bound):
  - **N1.** "Once the compiler process has ended, an `OSError` from moving the artefact into place is raised as `ArtefactNotPlacedError`, and one from removing the temporary file as `TemporaryNotRemovedError`; both are `OSError` subclasses whose `result` holds the `BuildResult` with the compiler's log. When both fail, `ArtefactNotPlacedError` is raised and the removal's error is its `removal_error`." The move is tried only when the compiler exited with 0 and left its output; `ArtefactNotPlacedError.result` has `ok` false. `TemporaryNotRemovedError.result` is "the `BuildResult` the call would otherwise have returned, `ok` included".
  - **N2.** "An `OSError` from starting the process is passed on as it is, unless removing the temporary file then fails too, whose error is passed on instead" — neither of the two classes of N1, and with no `result`. Before anything is started the call raises `FileNotFoundError`, `IsADirectoryError` or `NotADirectoryError` for a source or output path. Those tests use `pathlib.Path.is_file`, `is_dir` and `exists`, of which the documentation of Python 3.11 to 3.13 says that "other errors (such as permission errors) are propagated", so there an `OSError` of another class can also come before the start; in Python 3.14 all three return false instead (read from its source), so what comes up depends on the Python version (`requires-python` is `>=3.11`). After the compiler ended, the call tests whether the temporary file exists with `is_file` outside the two classes of N1, so where that test propagates an `OSError`, it comes up with no `result` and no log. The class of the error from starting the compiler with a working directory that does not exist is the platform's and was not read.
  - **N3.** The module docstring: "The artefact is written under a temporary name next to `output`", and "Sources and the output are handed to it as absolute paths, so `cwd` does not change what is compiled."
  - **N4.** `hilclaw.harness.verification_build.build_verification_executable` passes on "Whatever `hilclaw.clang_build.build` raises … unchanged". No code calls either new class (checked on 2026-10-17 in `hilclaw/`).
- **O1** (**owner**, as ADR-0060 Context quotes it): "A result: `outcome` `broken` with a new value of `condition` (one value for both, or one each; name them if you wish). One each: `build_exit_status` for S7 and `build_time_limit` for S8." **O2** (**owner**, same): "Kept, not returned: in a file of the attempt, never in the result or in `events.ndjson`; …". No later owner comment on #5 speaks to errors of two rows, to S9 or to ⑱ (마) (checked on 2026-10-17).

## Decision

### 1. Scope and terms

- A call of `correctness.check` as ADR-0060 decision 1 has it: about one attempt of a run of the first case or of a run whose hw_profile names the mock, in ⑥, when the operation of `cpu_standin` calls `clang_build.build` (directly or through `build_verification_executable`, which passes everything on — N4) for the one build of ADR-0056 decision 4.
- **The carried build**: the `BuildResult` an error of N1 holds as `result`. The terms S1 to S10, the build directory and the output path are ADR-0056's, the six kinds ADR-0060's, the keeper ADR-0078's.
- **The mock** builds nothing and is unchanged: a script may raise any of the six kinds (cited: ADR-0060 decision 3).

### 2. A failed move of the artefact: S9, `build_output_missing`

- **`ArtefactNotPlacedError` is S9** — "Status 0 and no executable at the path, or it cannot be moved there" (cited: ADR-0060 decision 4) — **and is raised as `build_output_missing`**, whether or not it also holds a `removal_error`. N1 tries the move only after the compiler exited with 0, so the error is the second case of that row's wording, and the carried build reads S9 by itself (`returncode` 0, `ok` false — cited: ADR-0060 decision 4, "`returncode` 0 (S9)"). The message may say which case of the row it was (cited: ADR-0060 decision 5).
- **The log.** The compiler ended, so its log is kept (cited: ADR-0078 decision 2, "S9"); it is `result.log` of the error, and the operation hands it to the keeper before it raises, as ADR-0078 decision 6 says.

### 3. A failed removal of the temporary file alone: the row of the carried build

- **For `TemporaryNotRemovedError` the operation goes on as if the call had returned the carried build**: `ok` true → an ok build, after which the operation starts the process as for any ok build (S10, a report or a condition, as ADR-0060 and ADR-0043 have them); `timed_out` → S8, (B) `"build_time_limit"`; a non-zero `returncode` → S7, (B) `"build_exit_status"`; `returncode` 0 and `ok` false → S9, `build_output_missing` (the reading of a `BuildResult` cited from ADR-0060 decision 4). **The failed removal itself is in no answer and no message.** The operation no longer lets the error pass, so the landed answer `operation_answer_invalid` (ADR-0045 decisions 4 and 5) is not reached for it.
- **Why.** The temporary file lies "next to `output`" (N3), and the output path lies in the build directory, which the operation makes for that call and removes "with everything in it, before its call returns or raises" (cited: ADR-0056 decision 4). A temporary file left behind is therefore a file of the build directory, and its removal is that removal. What an operation does when that removal fails is "not decided (sub-question ⑰ (다))" (cited: ADR-0056 decision 4); this record does not decide it either. What the carried build shows is what the experiment established about the build; the failed removal says nothing about the attempt.
- **The log.** In every case of this decision the compiler ended, so the log is kept (cited: ADR-0078 decision 2) and handed to the keeper (cited: ADR-0078 decision 6); a write that fails is answered as ADR-0078 decision 7 says.
- **The limit.** This holds because the output path is in the build directory (ADR-0056 decision 4). A later record that puts the executable elsewhere revisits this decision.

### 4. An `OSError` from starting the compiler: S6, `compiler_unavailable`

- **An `OSError` from starting the compiler process — or, after such a failed start, from removing the temporary file (N2) — is S6 and is raised as `compiler_unavailable`, a missing working directory included.** The row is placed by the moment the error belongs to, the start of the build, as the moment column of ADR-0060 decision 4 has S6 ("⑥, at the start of the build") and S3 ("⑥, before the build").
- **Why a missing working directory is S6 and not S3.** The working directory the operation hands the build is its build directory (cited: ADR-0056 decision 4), which it made for that call; S3 is "The build directory cannot be made or written", found "before the build" (cited: ADR-0060 decision 4). **That the operation finds a directory it could not use before the build, and that a directory gone at the start is met at the start, is this record's reading**, in the manner of ADR-0060 decision 4: "The row S3 holds for what the operation finds itself before the build." Both rows are tool failures, so no outcome about the attempt is lost and only the kind differs; and as "`cwd` does not change what is compiled" (N3), a missing one says nothing about the attempt's source either way. The limit "The cause is not established" (cited: ADR-0060 decision 2) covers it.
- **Telling such an error apart is the code's.** By its class alone an operation cannot see that an `OSError` came from the start: N2 shows errors of the same classes before the start and after the end. **This decision applies to an error the operation can tell came from the start** — by a change of `clang_build.build`, as T-0244 made for the move and the removal, or by a step of its own (cited: ADR-0060 decision 4, "An operation places such an error by the step of its own at which it met it"); which way is the code task's. An `OSError` the operation cannot place so stays open under (마) (decision 5); the code task registers it (cited: ADR-0060 decision 4, "a code task that finds an error it cannot place in one row registers it").
- **No log**: no compiler ended (cited: ADR-0078 decision 2 — S3, S5, S6 and S4 found before the build "have no log").

### 5. How far (마) is answered

- **Answered, for `correctness.check` of the first case and of the mock**: the entry of `clang_build.build` for moving the artefact and removing the temporary file after the compiler ended (decisions 2 and 3), and the row of an error from starting the compiler (decision 4).
- **Open under (마)**: telling an error from the start apart from an `OSError` of the same class before the start or after the end (decision 4; N2), including an `OSError` from the path tests of other classes than the three the docstring names, and one from the test of the temporary file after the compiler ended, which carries no log; and, as ADR-0060 decision 4 names them, `FileNotFoundError` or `IsADirectoryError` for a source (S5) or for the output path (S3); a `TypeError` of `clang_build.build`, whose docstring does not say which argument; whatever `clang_build.build` passes on from `subprocess` beyond the `OSError` its docstring names; the `ValueError` or `TypeError` of `local_run.run` for an `env` (S4) or for an argument the operation's own code formed; and the `OSError` of `local_run.run` for "a `cwd` that does not exist" (S3 or S10).

### Walk-through

The names of ADR-0056: run `r1`, `round` 3, `candidate` 2, `attempt` 1, `"execution": 1, "point": "sim"`.

| The build | `clang_build.build` | The operation | The caller gets |
|---|---|---|---|
| Exit 0; the move into place is refused | `ArtefactNotPlacedError` | hands `result.log`; raises `build_output_missing` | Tool failure `build_output_missing` |
| The build passes its time limit; the temporary file the killed compiler left cannot be removed | `TemporaryNotRemovedError`, `result.timed_out` true | hands the log; returns `"build_time_limit"` | A result: `"broken"`, `"build_time_limit"` |
| `gemm.c` does not compile; the temporary file cannot be removed | `TemporaryNotRemovedError`, non-zero `returncode` | hands the log; returns `"build_exit_status"` | A result: `"broken"`, `"build_exit_status"` |
| The compiler's process cannot be started, and the operation can tell the error came from the start | that error, no `result` | hands nothing; raises `compiler_unavailable` | Tool failure `compiler_unavailable` |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | S3, `build_directory_unusable` (the build directory refuses the move) | S3 is "before the build"; S9 names this case in its own words, "or it cannot be moved there". |
| 2 | Let it pass: `operation_answer_invalid` | That kind says the answer had neither form (ADR-0045 decision 4); the row is known, and ADR-0060 decision 4 gives it a kind. |
| 3 | **(a)** Keep the landed answer, `operation_answer_invalid` | Throws away an outcome the build established — for S7 and S8 a result O1 (the owner's) classes as one — over a file the operation's removal of the build directory covers anyway; ADR-0060 decision 4 called that answer "no answer of this record". |
| 3 | **(c)** S9 or another existing kind for every such error | Turns a build that ended ok, S7 or S8 into a tool failure; for S7 and S8 against O1. S3 is before the build. |
| 4 | S3 for a missing working directory, found by a test of the build directory after the error | It observes a later state, not the cause; a directory removed after the start would read as missing at the start; both rows are tool failures, so nothing is gained for the attempt. |
| 4 | Leave the row of a missing working directory open under (마) | The row can be placed by the moment, as ADR-0060 decision 4 places a directory that fails during the build; what stays open is telling the error apart, which is the code's, not the row. |
| 4 | Every `OSError` that is neither class of N1 is S6 | Errors of the same classes come before the start (S5, S3) and after the end of the compiler, the latter of a build whose log ADR-0078 decision 2 keeps (N2). |
| 5 | Answer the other two-row entries in this record too | The code does not tell them apart by class; placing them needs either a code change or a rule this record has no ground for. |

## Consequences

- **Code** (code mode, D12 rules; names and modules are the code task's; **this record binds no code**): the operation of `cpu_standin` for `correctness.check`, when it is written, applies decisions 2 to 4; it stays blocked by what ADR-0078 Consequences names (setting values, ⑱ (라), OD-14; the container, OD-14 ①, ⑱ (다)). **The log of a build whose test of the temporary file propagates an `OSError` after the compiler ended is lost** with the error (Python 3.11 to 3.13, N2), against ADR-0078 decision 2, unless `clang_build.build` changes; a code task changes it or registers the case, as ADR-0078 Consequences slice (4) said of the move and the removal.
- **Not edited and now less exact.** ADR-0060 decision 4 (its list of two-row entries — "an `OSError` from starting the compiler (S6) or from moving the artefact (S9)", "an `OSError` from starting the compiler for a missing working directory (S3) or a compiler that cannot be started (S6)", "an `OSError` of `clang_build.build` from removing its temporary file (below), which comes up in the same class from the same call as S6 and S9" — and "An error the operation lets pass that is no tool failure — one from removing the temporary file … is answered `operation_answer_invalid`"), decision 7 ((가) "except for an error that one call raises in one class for two rows") and Consequences ("Telling the rows apart is a condition of the operation's code"; "this record gives no kind to an error of two rows"); ADR-0078 Context ("An `OSError` from starting the process or from moving the artefact into place is passed on, with no log") and Consequences slice (4), which T-0244 carried out.
- **A-13 reading.** Nothing of the data plane is added or changed: no member, no value of `condition` or `error.kind`, no file, no version.
- **Runtime acceptance items**: none. Which of these errors a real machine produces is the code tasks' observation.

## Boundaries (not decided here)

- **The other entries of (마)** (decision 5).
- **⑱ (가), (다), (라) and the size bound of (나)**; the situations a container adds (OD-14 ①).
- **⑰ (다)**, including what happens when removing the build directory — and so a temporary file left in it — fails.
- **The timing build of `sim.run` / `board.run`** and its errors (⑲ (나), ⑲ (다); ADR-0068 on the unlanded branch of T-0210).
- **Owner-only (DRIVER §9)**: the #5 A and B items; OD-3; OD-25; C-6.
- Any change to ADR-0001 to ADR-0078, to UsageCases, to `hilclaw/`, to tests, to CI or to any settings file; any new external dependency; any new reserved `kind`.

## References

- [Requirements](../Requirements.md): FR-6, FR-10; register row OD-18.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ⑰, ⑱, ⑲).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0043](ADR-0043-od18-correctness-check-operation-form.md) (decision 4); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4, 5); [ADR-0047](ADR-0047-od18-correctness-check-operation-tool-failure.md) (decision 5); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 4, 5); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (Context; decisions 1 to 5, 7; Consequences); [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (Context; decisions 2, 6, 7; Consequences).
- HQ-0020 answer https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-6183004538 · D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/clang_build.py`, `hilclaw/harness/verification_build.py`; tasks T-0244 (PR #155), T-0245.
