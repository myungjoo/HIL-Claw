# ADR-0080: Where a check of `correctness.check` places the two errors `clang_build.build` has told apart since ADR-0079 — `CompilerNotStartedError` is the error from the start that ADR-0079 decision 4 places in S6, and `ArtefactNotCheckedError` is S9 (more of part (마) of sub-question ⑱ of OD-18)

## Status

- **Accepted on 2026-10-17** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences: none is quoted here; O1 and O2 of [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) Context reach this record only through ADR-0060 and [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md), which it cites. What a requirement or an accepted record says is **cited** with its source. **Everything else is this record's own design**: that `CompilerNotStartedError` is an error "the operation can tell came from the start", the row of `ArtefactNotCheckedError`, and every weighing. Statements about code are **observations** at `03f9007` and bind no code; statements about Python are observations of the CPython source named in Context, or are named as taken from task T-0246's Result.
- Answers **more of part (마) of sub-question ⑱ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)) for `correctness.check` of the first case and of the mock: **the two errors of `clang_build.build` that tasks T-0246 and T-0247 added after [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md)** — telling an error from creating the compiler process apart from errors of the same class before the start or after the end, and the error from testing the temporary file after the compiler ended (decisions 2 and 3). It leaves open what decision 4 names: an `OSError` after the compiler process was created and before it ended, the path tests before the start, and the other entries ADR-0079 decision 5 names. Parts (가), (다), (라) and the size bound of (나) are not answered. OD-18 keeps its status word.
- **No member of any file, result, request or line is added or changed; no value of `condition` and no value of `error.kind` is added, no kind is reserved, and no `schema_version` and no layout version changes.** Every answer it gives is one of the six backend kinds of ADR-0060 decision 4; a failed write of the log is answered as ADR-0078 decision 7 says, cited and not changed.
- **No sentence of an earlier record is replaced or edited.** Consequences lists the sentences that become less exact.
- It builds on ADR-0060 (decision 4; its window runs until 2026-10-22), ADR-0078 (decisions 2, 6 and 7; until 2026-10-23) and ADR-0079 (decisions 2 to 5; until 2026-10-23), and on [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) decision 4 as ADR-0079 decision 3 reads it. **If one of them is reverted, this record falls with it.**
- **It is a record, not code, and nothing was built or run**: no compiler, container or `claude` process was started.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0079 decision 4 places "An `OSError` from starting the compiler process — or, after such a failed start, from removing the temporary file" in S6, `compiler_unavailable`, and says: "**This decision applies to an error the operation can tell came from the start** — by a change of `clang_build.build`, as T-0244 made for the move and the removal, or by a step of its own". Its decision 5 kept open "telling an error from the start apart from an `OSError` of the same class before the start or after the end … and one from the test of the temporary file after the compiler ended, which carries no log"; its Consequences said that log "is lost … unless `clang_build.build` changes".
- Task T-0246 (PR #156, `a355078`) and task T-0247 (PR #157, `03f9007`) changed `clang_build.build`. Neither placed its error in a row.
- **Observations at `03f9007`** (`hilclaw/clang_build.py`; no code is bound):
  - **M1.** `build` creates the compiler with `subprocess.Popen`, and only an `OSError` raised by that construction — opening its pipes included — is caught as the start error: "An `OSError` from creating the compiler process is raised as `CompilerNotStartedError`, an `OSError` subclass without `result`; when removing the temporary file then fails too, the removal's error is its `removal_error`." No other line of `build` raises that class. A missing working directory fails that construction (a test of T-0247 attempts a real start with one — taken from T-0247's Result).
  - **M2.** "After the compiler exited with 0, only a `FileNotFoundError` or `NotADirectoryError` from testing whether the temporary file exists reads as no artefact; any other `OSError` of that test is raised as `ArtefactNotCheckedError`, an `OSError` subclass whose `result` holds the `BuildResult` with the compiler's log, and nothing is moved. When removing the temporary file then fails too, `ArtefactNotCheckedError` is raised and the removal's error is its `removal_error`." The test is `os.stat` with `stat.S_ISREG`; its `result` is built with `ok` false and the `returncode` of the process, which is 0 whenever the test is made.
  - **M3.** "Any other `OSError` raised while the process runs is passed on as it is, unless removing the temporary file then fails too, whose error is passed on instead" — with no `result`, in the same classes as the errors before the start.
  - **M4.** Before the start, `_checked_sources` tests each source with `Path.is_file` and `Path.is_dir`, and `build` tests the output path with `is_dir`, `exists` and `is_dir`, then raises `FileNotFoundError`, `IsADirectoryError` or `NotADirectoryError` with a message and no `errno`.
  - **M5.** An `OSError` raised inside the construction of `Popen` after the operating system created the process — for example on POSIX from reading or closing the pipe that reports an exec error, on Windows from closing the thread handle, and on both from closing the parent's copies of the child's pipe ends — is caught as in M1 too. T-0247's reviewer named this case (info), and T-0247's Result calls it "practically unreachable"; this record did not read whether such a process is killed or waited for.
- **Observations of the CPython source** (read in the installed 3.11.9 and 3.14.4; 3.12 and 3.13 were not read). In 3.11, `is_file`, `is_dir` and `exists` return false for an `OSError` whose `errno` is `ENOENT`, `ENOTDIR`, `EBADF` or `ELOOP` or whose `winerror` is 21, 123 or 1921, and raise any other `OSError`. In 3.14 they call `os.path.isfile`, `isdir` and `exists`, whose generic versions return false for every `OSError` (`genericpath.py`); on Windows these come from the `nt` module, whose source was not read. That 3.12 and 3.13 behave as 3.11, and that T-0246 thus turned errors the old test swallowed as false (`ELOOP`, `EBADF`, Windows errors 21, 123 and 1921) into `ArtefactNotCheckedError` on 3.11 to 3.13, is **taken from T-0246's Result** and from ADR-0079 N2, which cites the documentation of 3.11 to 3.13. On 3.14 the old test swallowed every `OSError` where the generic functions apply (as read above; on Windows not read), so there T-0246 moved every class but `FileNotFoundError` and `NotADirectoryError`, a `PermissionError` among them. The new test is `os.stat` (M2) and does not depend on the version.
- No owner comment on #5 speaks to ADR-0079, to errors of two rows, to S9 or to ⑱ (마) (checked on 2026-10-17).

## Decision

### 1. Scope and terms

- A call of `correctness.check` as ADR-0060 decision 1 and ADR-0079 decision 1 have it: the one build of ADR-0056 decision 4, through `clang_build.build` directly or through `build_verification_executable`, which passes everything on (ADR-0079 N4). **The carried build**, the six kinds, S1 to S10 and the keeper are as ADR-0079 decision 1 has them. **The mock** builds nothing and is unchanged.

### 2. `CompilerNotStartedError` is an error the operation can tell came from the start

- **`CompilerNotStartedError` is "an error the operation can tell came from the start" in the sense of ADR-0079 decision 4**, which gives its row and kind; this record does not restate them. Its class is raised only from creating the compiler process (M1), and creating it is the start that ADR-0060 decision 4 dates S6 by ("⑥, at the start of the build"). A missing working directory is among them (M1), as ADR-0079 decision 4 placed it.
- **With a `removal_error`.** ADR-0079 decision 4 places an error "after such a failed start, from removing the temporary file" with the start. The code now raises the start's error and holds the removal's as `removal_error` (M1), so the class tells such a call apart as well. **The failed removal itself is in no answer and no message**, as ADR-0079 decision 3 has it for a removal after the end: a temporary file left behind is a file of the build directory, whose removal is ADR-0056 decision 4's and whose failure is sub-question ⑰ (다).
- **An error from inside the construction after the process exists (M5) is read under the same decision**: the operation sees one class, and nothing in the class tells it apart. **The cost, stated**: in that case a compiler process may exist, and whatever it writes reaches no keeper, because the code hands the operation no log (M1); this answers `compiler_unavailable` for a call in which a compiler may have run, against the letter of ADR-0078 decision 2 if it also ended; and such a process may write the temporary file after the call removed it, a file of the build directory (⑰ (다)). The case is practically unreachable (M5) and gives no outcome about the attempt either way, since S6 and S9 are both tool failures. A code task that makes the case reachable or tells it apart revisits this sentence.
- **No log**: no compiler ended (cited: ADR-0079 decision 4; ADR-0078 decision 2).

### 3. `ArtefactNotCheckedError` is S9, `build_output_missing`

- **`ArtefactNotCheckedError` is S9 — "Status 0 and no executable at the path, or it cannot be moved there" (cited: ADR-0060 decision 4) — and is raised as `build_output_missing`, whether or not it also holds a `removal_error`.** The compiler exited with 0 and nothing was moved to the output path (M2), which lies in the build directory the operation made for that call (cited: ADR-0056 decision 4), so no executable is at the path: the first case of that row's wording. The carried build reads S9 by itself, `returncode` 0 and `ok` false (cited: ADR-0060 decision 4, "`returncode` 0 (S9)"), so this is also the answer of reading the carried build as ADR-0079 decision 3 does; the decision is stated by the row because the code never gives this class another build (M2).
- **The same answer on every Python version.** Where the test reads an error as false, the call returns a build with `returncode` 0 and `ok` false, which is S9 by ADR-0060 decision 4; where it raises, it is S9 by this decision. So the errors T-0246 moved from the first to the second, on 3.11 to 3.13 and on 3.14 (Context), keep their answer, and the version changes no row.
- **The message** may say which case of the row it was (cited: ADR-0060 decision 5); it shows no text of the error.
- **The log.** The compiler ended, so its log is kept (cited: ADR-0078 decision 2, "S9"); it is `result.log` of the error, which the operation hands to the keeper before it raises (cited: ADR-0078 decision 6); a write that fails is answered as ADR-0078 decision 7 says.
- **The `removal_error`** is in no answer and no message, as in decision 2: the file left behind lies in the build directory (ADR-0079 decision 3).

### 4. How far (마) is answered

- **Answered now, for `correctness.check` of the first case and of the mock**: the start errors of ADR-0079 decision 4, as far as the code raises them as `CompilerNotStartedError` (decision 2), and the error from testing the temporary file after the compiler ended (decision 3), which therefore no longer loses the log.
- **Open under (마)**: an `OSError` raised after the compiler process was created and before it ended, and the removal error passed on in its place (M3), which by class cannot be told apart from an error before the start; an `OSError` of another class than the three the docstring names from the path tests before the start (M4), which those tests raise on 3.11 (and, as taken from T-0246's Result, on 3.12 and 3.13) and, by the generic `os.path` functions, not on 3.14 (on Windows not read); and the other entries ADR-0079 decision 5 names — `FileNotFoundError` or `IsADirectoryError` for a source (S5) or for the output path (S3), the `TypeError` of `clang_build.build`, whatever `clang_build.build` passes on from `subprocess` beyond the `OSError` its docstring names, and the `ValueError` or `TypeError` and the `OSError` for "a `cwd` that does not exist" of `local_run.run`.

### Walk-through

The names of ADR-0056: run `r1`, `round` 3, `candidate` 2, `attempt` 1, `"execution": 1, "point": "sim"`.

| The build | `clang_build.build` | The operation | The caller gets |
|---|---|---|---|
| The compiler cannot be started | `CompilerNotStartedError`, no `result` | hands nothing; raises `compiler_unavailable` | Tool failure `compiler_unavailable` |
| The same, and the temporary file cannot be removed | `CompilerNotStartedError` with a `removal_error` | the same | The same |
| Exit 0; testing the temporary file is refused | `ArtefactNotCheckedError`, `result.returncode` 0 | hands `result.log`; raises `build_output_missing` | Tool failure `build_output_missing` |
| Reading the pipe fails while the compiler runs | that `OSError`, no `result` | open under (마) (decision 4) | — |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | Keep start errors open until the code also tells apart the errors after the process was created | ADR-0079 decision 4 asks only that the operation can tell an error came from the start; the class now says so (M1), and the errors after creation are a different class (M3). |
| 2 | A sentence of its own, or (마), for an error inside the construction after the process exists (M5) | The operation cannot tell it apart, so a separate row could not be applied; the case is practically unreachable and any answer is a tool failure; the cost is stated in decision 2. |
| 3 | **(b)** Answer by the row the carried build shows, as ADR-0079 decision 3 does for `TemporaryNotRemovedError` | Gives the same answer here (decision 3), but suggests the build could read otherwise; that class may carry an ok build, this one never does (M2). |
| 3 | **(c)** Leave it open under (마) | The row is known: the compiler exited 0 and no executable is at the path, which is S9's own wording. |
| 3 | **(d)** S3, `build_directory_unusable` (the build directory refuses the test) | S3 is "before the build"; ADR-0079 declined it for the failed move on the same ground. |
| 3 | **(d)** Let it pass: `operation_answer_invalid` | That kind says the answer had neither form (ADR-0045 decision 4); the row is known and ADR-0060 decision 4 gives it a kind. It would also answer an exit 0 without an artefact by the class of the test's error, where ADR-0060 decision 4 answers the returned build S9. |
| 4 | Place the `OSError` after the process was created as S6 or as S9 | It comes in the same classes as errors before the start (M3, M4), so an operation could not apply either; telling it apart is a code change. |

## Consequences

- **Code** (code mode, D12 rules; names and modules are the code task's; **this record binds no code**): the operation of `cpu_standin` for `correctness.check`, when it is written, applies ADR-0079 and this record; it stays blocked by what ADR-0078 Consequences names. A further means of telling apart the errors of decision 4's open list is a later code task.
- **Not edited and now less exact.** ADR-0079 N2 ("An `OSError` from starting the process is passed on as it is, unless removing the temporary file then fails too, whose error is passed on instead"; "it comes up with no `result` and no log"), decision 4 ("By its class alone an operation cannot see that an `OSError` came from the start"), decision 5 ("telling an error from the start apart from an `OSError` of the same class before the start or after the end"; "one from the test of the temporary file after the compiler ended, which carries no log"), the fourth row of its walk-through ("and the operation can tell the error came from the start"), and its Consequences ("**The log of a build whose test of the temporary file propagates an `OSError` after the compiler ended is lost**"); ADR-0060 decision 4, in its list of two-row entries ("an `OSError` from starting the compiler (S6) or from moving the artefact (S9)"; "an `OSError` from starting the compiler for a missing working directory (S3) or a compiler that cannot be started (S6)") and in "one raised once it has started anything is an `OSError` of the two-row entries above", for the classes decisions 2 and 3 place; ADR-0078 decision 2 ("S3, S5, S6 and S4 found before the build start no compiler or none that ran, so they have no log"), for the case of M5 (decision 2).
- **A-13 reading.** Nothing of the data plane is added or changed: no member, no value of `condition` or `error.kind`, no file, no version.
- **Runtime acceptance items**: none. Which of these errors a real machine produces is the code tasks' observation.

## Boundaries (not decided here)

- **The open entries of (마)** (decision 4), and any code change that tells them apart.
- **⑱ (가), (다), (라) and the size bound of (나)**; the situations a container adds (OD-14 ①).
- **⑰ (다)**, including what happens when removing the build directory, and a temporary file left in it, fails.
- **The timing build of `sim.run` / `board.run`** and `local_run.run` (⑲).
- **Owner-only (DRIVER §9)**: the #5 A and B items; OD-3; OD-25; C-6.
- Any change to ADR-0001 to ADR-0079, to UsageCases, to `hilclaw/`, to tests, to CI or to any settings file; any new external dependency; any new reserved `kind`.

## References

- [Requirements](../Requirements.md): FR-6, FR-10; register row OD-18.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-questions ⑰, ⑱).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decision 4); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 4, 5); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decisions 1, 4, 5); [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decisions 2, 6, 7; Consequences); [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md) (N2; decisions 1 to 5; Consequences).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/clang_build.py` at `03f9007`; tasks T-0246 (PR #156), T-0247 (PR #157), T-0248; CPython `Lib/pathlib.py` (3.11.9), `Lib/pathlib/__init__.py` and `Lib/genericpath.py` (3.14.4).
