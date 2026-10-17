# ADR-0087: What a check of `correctness.check` answers for a `TypeError` of `clang_build.build`, now that `build` states its `parameter` — S4 for a setting, no row for an argument the operation forms; a `TypeError` with no `parameter` stays as the landed records leave it (more of part (마) of sub-question ⑱ of OD-18)

## Status

- **Accepted on 2026-10-17** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences: none is quoted here. Of O1 to O5 of [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) Context, O1 to O3 bear on built results and their logs, which no row of this record is, and O5 on the number of checks; the classing of settings this record cites from ADR-0060 decision 3 rests in part on O4 (the isolated environment whose toolchain holds the compiler) and reaches this record only through that record. What a requirement or an accepted record says is **cited** with its source. **Everything else is this record's own design**: that the operation tells a `TypeError` of `build` apart by `parameter`, and on which reading; that the four values for a setting are S4 and the two for an argument the operation forms are no row, and the readings of S4 and of ADR-0060 decision 4 this rests on, a `TypeError` Python raises inside a check included; that a `TypeError` with no `parameter` stays as left; and every weighing. Statements about code are **observations** at `a46a4d6` of what `build` and `build_verification_executable` state and do, and bind no code; none was established by running code. Names and modules stay the code tasks'.
- Answers **more of part (마) of sub-question ⑱ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)) for `correctness.check` of the first case and of the mock: **the row of a `TypeError` of `build` that carries `parameter`** (decisions 2 to 4). It leaves open a `TypeError` with no `parameter` (decision 5) and the rest decision 8 names. Parts (가), (다), (라) and the size bound of (나) are not answered. OD-18 keeps its status word.
- **No member of any file, result, request or line is added or changed; no value of `condition` and no value of `error.kind` is added, no kind is reserved, and no `schema_version` and no layout version changes** (decision 7).
- **No sentence of an earlier record is replaced or edited.** Consequences lists the sentences that become less exact.
- It builds on [ADR-0086](ADR-0086-od18-correctness-check-path-role.md) (Q2, decisions 1, 2, 6 and 8, alternative (f); its window runs until 2026-10-24), [ADR-0085](ADR-0085-od18-correctness-check-clock-error-return-code.md) (decisions 2 and 6; until 2026-10-24), [ADR-0083](ADR-0083-od18-correctness-check-plain-oserror-before-start.md) (P3, decisions 2 and 4; until 2026-10-24), [ADR-0081](ADR-0081-od18-correctness-check-compiler-run-error.md) (decisions 1 and 2; until 2026-10-24), [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md) (decision 1; until 2026-10-23), [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decision 2; until 2026-10-23), ADR-0060 (decisions 3 to 5 and 7, Consequences; until 2026-10-22), [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 3 to 5; until 2026-10-20) and [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4 and 5; until 2026-10-19). **If one of them is reverted, this record falls with it.**
- **It is a record, not code, and nothing was built or run**: no compiler, container, Python interpreter or `claude` process was started; the sources were read as files.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0060 decision 4 answers a `TypeError` by what it is for: "a `ValueError` or `TypeError` for a setting — a time limit, a flag, the compiler — … → S4, whether the setting is refused for its value or for its type"; "a `TypeError` for an argument that is no setting (a path, an argument of the command) is a defect of the operation's own code and is no row"; and "a `TypeError` of `clang_build.build`, whose docstring does not say which argument, is an error of two rows" (cited). Its Consequences make telling them apart "a condition of the operation's code", for example "by a change of those functions" (cited). ADR-0086 decision 8 kept "the `TypeError` of `clang_build.build`" open under (마). Task T-0261 (PR #164, `a46a4d6`) made that change and placed nothing in a row.
- **Observations at `a46a4d6`** (`hilclaw/clang_build.py`, `hilclaw/harness/verification_build.py`; no code is bound):
  - **T1. The docstring of `build`.** "Any `TypeError` from the checks of `timeout_s`, `flags`, `trailing_flags`, `sources`, `output` and `compiler`, including one that Python itself raises inside them such as for a value that cannot be iterated, is raised with the attribute `parameter` set to the name of that parameter: `"timeout_s"`, `"flags"`, `"trailing_flags"`, `"sources"`, `"output"` or `"compiler"`; a `TypeError` from anywhere else, such as binding the call or creating the compiler process, carries no `parameter`."
  - **T2. How it is set.** `build` runs each check inside a private context manager that catches `TypeError`, sets `parameter` on that object and re-raises it with a bare `raise`, so class, arguments and chain are unchanged (T-0261, "The change, stated" and Result). The checks run in the order of T1; the tests of the source paths run inside the check of `sources` and raise `OSError` with `path_role` (cited: ADR-0086 Q2), the tests of the artefact path run after the check of `output`, and the check of `compiler` (`_resolve`) also raises the `ValueError` for an empty prefix and `CompilerNotFoundError`. The first check that fails is the one raised.
  - **T3. What raises inside a check.** `build`'s own tests raise `TypeError` for a `timeout_s` that is a `bool` or no `int` or `float`, for flags that are one `str` or `bytes` or hold an element that is no `str`, for a source that is no `str` or `os.PathLike`, and for a part of the compiler prefix that is no `str`. Python raises one from `tuple` of the flags or of the compiler, from iterating the sources, and from forming the absolute path of a source or of the output. What iterating a handed object or its `__fspath__` raises is that object's code (cited: ADR-0083 P3); a `TypeError` of it that leaves a check carries the parameter as well (T1).
  - **T4. No other error carries it.** A `TypeError` from binding the call (for example a missing `timeout_s`), one from `subprocess.Popen` or later (for example a `cwd` or an `env` that cannot be handed over), every `ValueError`, every `OSError`, `CompilerNotFoundError` and every error of `compiler_version` carry no `parameter` (T-0261's Result, and its tests).
  - **T5. Through `build_verification_executable`.** It passes on whatever `build` raises unchanged, so the object and its `parameter` are the same (cited for passing on: ADR-0086 decision 1). It raises its own `TypeError`, with no `parameter`, for `kernel_sources` that are neither a path nor iterable, before it calls `build`; a `bytes` path among the kernel sources, or a non-empty one alone, ends as a `TypeError` of `"sources"` in `build`.
- No owner comment on #5 speaks to ADR-0060 decision 4, ADR-0086, T-0261 or ⑱ (마) (checked on 2026-10-17; every comment since 2026-10-16 carries the driver tail).

## Decision

### 1. Scope and terms

- A call of `correctness.check` as ADR-0081 decision 1 has it. The six kinds, S1 to S10 and the keeper are as ADR-0079 decision 1 has them. **A named `TypeError`** is a `TypeError` that `build` raises with a `parameter`; **an unnamed `TypeError`** is one with none (T4), and one of `build_verification_executable` itself (T5). **A setting** is one of ADR-0060 decision 3's table: flags and trailing flags, the compiler and the time limit of the build are "the backend's own"; the path of the executable is "the operation's own" (cited: ADR-0060 decision 3; ADR-0056 decision 4). The sources are the verification program and the compiled set the reader gave the operation (cited: ADR-0056 decisions 3 and 4). **The mock** builds nothing and is unchanged.

### 2. The operation tells them apart by `parameter`

- **From what `build` states alone**: `isinstance(error, TypeError)` and `getattr(error, "parameter", None)`. `"timeout_s"`, `"flags"`, `"trailing_flags"` and `"compiler"` name a setting; `"sources"` and `"output"` name an argument the operation forms; `None` names no check of T1 (T1, T4).
- **On which reading.** "What the operation observes decides the row" (cited: ADR-0060 decision 4). **This record reads what the operation observes as what `build` states of the error — its class and its documented members**, as ADR-0085 decision 2 read `returncode` and ADR-0086 decision 2 read `path_role`. It reads no exception chain (cited for the stop: ADR-0081 decision 2), no message and no private state.
- **"An error of two rows"** (ADR-0060 decision 4) **no longer holds for a named `TypeError`**: the docstring now says which argument (T1), and ADR-0060 decision 3 says which side holds it. It still holds for an unnamed one, whose class says nothing of the argument (decision 5).
- **The order of the tests.** A `TypeError` is neither an `OSError` nor `CompilerNotFoundError`, so no error that ADR-0079 to ADR-0086 answer, and none that ADR-0060 decision 4 places by its class (`NotADirectoryError` before the start, `CompilerNotFoundError`), meets this record's test. A `ValueError` of the same checks carries no `parameter` (T4) and stays as ADR-0060 decision 4 places it, by what it is for.

### 3. A named setting is S4, `settings_refused`

- **The operation raises a named `TypeError` whose `parameter` is `"timeout_s"`, `"flags"`, `"trailing_flags"` or `"compiler"` as S4, `settings_refused`** — "A setting is one the functions refuse (…; an empty compiler prefix or a setting of the wrong type; …)", found "before the process the refused setting belongs to is started" (cited: ADR-0060 decision 4). Each of the four is the backend's own (decision 1), so the sentence "whether the setting is refused for its value or for its type, as every setting is the backend's own" (cited: ADR-0060 decision 4) applies as written. `timeout_s` is the time limit of the build; the time limit of the process is no argument of `build`.
- **A `TypeError` Python raises inside such a check** (for example `tuple(3)` for `flags`; T3) **is read as covered by "a setting of the wrong type"**: the check could not take the value as the setting it must be, which is what the wording names; T1 states it of the same parameter. Reasons: the same setting gives the same answer whether `build`'s own test or Python's raises, and which one raises depends only on how the value is wrong. **The cost, stated**: a fault in the code of a handed object (T3) is read as a refused setting; the object is the backend's own setting, so S4's "follows from the backend's own settings" (cited: ADR-0060 decision 4) still holds of it.

### 4. A named argument the operation forms is no row

- **A named `TypeError` whose `parameter` is `"sources"` or `"output"` is no row**: "a `TypeError` for an argument that is no setting (a path, an argument of the command) is a defect of the operation's own code and is no row" (cited: ADR-0060 decision 4). The artefact path is the path of the executable, the operation's own, and the sources are formed by the operation from what the reader gave it (decision 1); no setting of the backend's is in either. An operation that lets it pass is answered `operation_answer_invalid` (cited: ADR-0045 decisions 4 and 5); "That says what the landed rules do with it; it is no answer of this record" (cited: ADR-0060 decision 4).
- **This record changes nothing ADR-0060 decision 4 says for them; it applies it.** What changed is that the operation can now tell them from a setting (decision 2).
- **Not S5 and not S3.** S5 names "A file of the compiled set is no longer a regular file when the build is called" and S3 "The build directory cannot be made or written" (cited: ADR-0060 decision 4); a value of the wrong type says neither of a file or a directory.
- **The cost, stated.** The path the reader starts from is handed by the tool function, whose "Python type of the path" is the code task's (cited: ADR-0056 decision 3), so a wrong type there is a defect of the tool function's part, not of the backend; it is still answered by a kind that says the backend's answer had neither form. A defect of either side's code is a defect of code, not a property of the attempt or the machine.

### 5. An unnamed `TypeError` stays as left

- **This record places no unnamed `TypeError`.** One from binding the call says the operation's call of `build` is malformed; one from `subprocess.Popen` or later stands under "whatever `clang_build.build` passes on from `subprocess` beyond the `OSError` its docstring names", which "was not read" (cited: ADR-0060 decision 4) and stays open (cited: ADR-0083 decision 2); for it the class is still of two rows — an `env` is a setting (S4), a `cwd` is the operation's own (cited: ADR-0060 decision 3). Through `build_verification_executable` it may also be that function's own for `kernel_sources` (T5), which the operation cannot tell apart by the object. Reading any of them into a row is not this record's.
- **Until then**, an operation that lets it pass is answered `operation_answer_invalid` (cited: ADR-0045 decisions 4 and 5), as ADR-0083 decision 2 has it for a `TypeError` from inside `Popen`.

### 6. No log, and the message

- **No log.** Every named `TypeError` is raised before a compiler process exists (T1, T2), and "S3, S5, S6 and S4 found before the build start no compiler or none that ran, so they have no log" (cited: ADR-0078 decision 2); the operation hands nothing to the keeper.
- **The message of `settings_refused`** may say which setting it was ("for S4 which setting") and of which kind the error was, and shows "no text of an error, no value of a setting" (cited: ADR-0060 decision 5) — so not the message of the `TypeError`, which names the type of the value. No rule is added; the wording is the code's.

### 7. No data-plane change

- `parameter` is an attribute of a Python exception inside the tool function's process, read by the operation; it is no member of a file, a result, a request or a line. S4 is a kind already named (ADR-0060 decision 4), and no row needs no kind. No value of `condition` or `error.kind` is added, no kind is reserved, and no `schema_version` or layout version changes. No case is left open here for want of a new value.

### 8. How far (마) is answered

- **Answered now, for `correctness.check` of the first case and of the mock**: a named `TypeError` of `build` — S4 for `"timeout_s"`, `"flags"`, `"trailing_flags"` and `"compiler"`, one Python raises inside the check included, and no row for `"sources"` and `"output"`, each with no log (decisions 2 to 6); with it the entry "the `TypeError` of `clang_build.build`" of ADR-0086 decision 8, for a named one.
- **Open under (마)**: an unnamed `TypeError` — of `build`, from binding the call or from `subprocess.Popen` or later, or of `build_verification_executable` for `kernel_sources` (decision 5); whatever `clang_build.build` passes on from `subprocess` beyond the `OSError` its docstring names; an unroled `OSError` of `build` — from `os.getcwd`, `os.urandom`, `time.monotonic` or the search for the compiler before the start (cited: ADR-0086 decision 6); the row of a `CompilerRunError` whose `timed_out` is false and whose `returncode` is `None` (cited: ADR-0085 decision 6); and the `ValueError` or `TypeError` and the `OSError` for "a `cwd` that does not exist" of `local_run.run`.

### Walk-through

The names of ADR-0056: run `r1`, `round` 3, `candidate` 2, `attempt` 1, `"execution": 1, "point": "sim"`.

| The call of `build` | `clang_build.build` | The operation | The caller gets |
|---|---|---|---|
| The backend's time limit of the build is the string `"10"` | `TypeError`, `parameter` `"timeout_s"` | raises `settings_refused` (decision 3) | tool failure `settings_refused`; no log file |
| The backend's flags are one `str` | `TypeError`, `"flags"` | the same | the same |
| The backend's flags are the integer `3` (`tuple(3)` raises) | `TypeError` of Python, `"flags"` | the same | the same |
| A trailing flag is no `str` | `TypeError`, `"trailing_flags"` | the same | the same |
| The backend's compiler is `3` | `TypeError` of Python, `"compiler"` | the same | the same |
| The operation's code puts `3` among the sources | `TypeError`, `"sources"` | lets it pass: no row (decision 4) | tool failure `operation_answer_invalid` (landed rules) |
| The operation's code hands `3` as the artefact path | `TypeError` of Python, `"output"` | the same | the same |
| The operation's code calls `build` without `timeout_s` | `TypeError` from binding, no `parameter` | open under (마) (decision 5) | — |
| An `env` that `Popen` cannot hand over | `TypeError` from `Popen`, no `parameter` | the same | — |

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 3, 4 | **(a)** S4 for the four settings, no row for `"sources"` and `"output"` (chosen) | It applies ADR-0060 decision 4's two answers by what `build` now states. The cost: a fault in a handed object's code is read as a refused setting (decision 3), and a wrong-typed path from the tool function as the operation's defect (decision 4). |
| 3, 4 | **(b)** Leave every `TypeError` open | The stop ADR-0060 decision 4 named, "whose docstring does not say which argument", is gone (T1). Left open, a refused setting, S4 by its meaning, is answered by a kind that says the backend's answer had neither form. |
| 4 | **(c)** S4 for every named `TypeError` | `"sources"` and `"output"` are no setting (decision 1); S4 would tell a caller that the backend's settings were refused where the operation's own code formed the argument, against ADR-0060 decision 4's "is no row". |
| 4 | **(d)** S5 for `"sources"`, S3 for `"output"` | Neither wording names a value of the wrong type (decision 4). |
| 4 | **(e)** A new kind for a formed argument of the wrong type | A new value of `error.kind` is a data-plane change (CLAUDE.md A-13), and ADR-0060 decision 4 already gives such an error no row. |
| 3 | **(f)** S4 only for a `TypeError` `build`'s own test raises; one Python raises left open | The same wrong setting would get two answers by how it is wrong (decision 3), though T1 states the same parameter for both. |
| 2 | **(g)** The operation's own step instead of `parameter` — testing the types of its settings before the call | `build` now states the parameter (T1); a test of its own would repeat `build`'s and could accept what `build` refuses, and an error of `build` would still need a row. ADR-0060 decision 4 still allows it. |
| 2 | **(h)** Place by the text of the message | `build` states the parameter, not messages; declined as ADR-0086 alternative (f) declined it. |
| 5 | **(i)** S4 or no row for an unnamed `TypeError` | Its class does not say which argument, and what `Popen` passes on was not read (decision 5). |

## Consequences

- **Code** (code mode, D12 rules; names and modules are the code task's; **this record binds no code**): the operation of `cpu_standin` for `correctness.check`, when it is written, applies ADR-0079 to ADR-0086 and this record. For a `TypeError` of `build` it reads `getattr(error, "parameter", None)`: it raises `settings_refused` for `"timeout_s"`, `"flags"`, `"trailing_flags"` and `"compiler"`, hands no log over, and leaves `"sources"`, `"output"` and an unnamed `TypeError` to the landed rules. **No change of `clang_build.build` is needed for this.**
- **Not edited and now less exact.**
  - ADR-0060 decision 4: "a `TypeError` of `clang_build.build`, whose docstring does not say which argument, is an error of two rows (Consequences)", which the docstring now says for a named one (decision 2); "An operation places such an error by the step of its own at which it met it", since for these errors `build` states the parameter; decision 7: "except for an error that one call raises in one class for two rows" under (가), and "except for an error of two rows (⑱ (마))" under sub-question ⑩, which no longer include a named `TypeError`.
  - ADR-0060 Consequences: "The errors decision 4 names as arising in one class in two rows … cannot be placed by an operation that sees the class alone", which T-0261 changed for the `TypeError` of `build`.
  - ADR-0079 decision 5 and ADR-0080 decision 4: the open entry "a `TypeError` of `clang_build.build`, whose docstring does not say which argument" and "the `TypeError` of `clang_build.build`", now answered for a named one.
  - ADR-0083 decision 2: "Another `Exception` … for example a `TypeError` or `ValueError` from inside the construction of `Popen` — is one of the entries already open under (마): "the `TypeError` of `clang_build.build`" and …", where such a `TypeError` now carries no `parameter` and stays under the entry of what `build` passes on from `subprocess` (decision 5); decision 4's open entry "the `TypeError` of `clang_build.build`".
  - ADR-0084 decision 5, ADR-0085 decision 6 and ADR-0086 decision 8: the open entry "the `TypeError` of `clang_build.build`", now only an unnamed one; ADR-0086 Status, "the rest decision 8 names".
- **A question for the owner**: none is raised; no case is left open for want of a new value of `error.kind` (decision 7).
- **A-13 reading.** Nothing of the data plane is added or changed: no member, no value of `condition` or `error.kind`, no file, no version (decision 7).
- **Runtime acceptance items**: none. No `claude`, compiler or container is started or required.

## Boundaries (not decided here)

- **The row of an unnamed `TypeError` of `build`** and of whatever `build` passes on from `subprocess` (decision 5); the errors of `compiler_version`, which carry no `parameter`, if an operation calls it.
- **The other open entries of (마)** (decision 8).
- **⑱ (가), (다), (라) and the size bound of (나)**; the values and sources of the settings (⑱ (라), OD-14).
- **`local_run.run`** and the timing build of `sim.run` / `board.run` (⑲).
- **Owner-only (DRIVER §9)**: the #5 A and B items; OD-3; OD-25; C-6.
- Any change to ADR-0001 to ADR-0086, to UsageCases, to `hilclaw/`, to tests, to CI or to any settings file; any new external dependency; any new reserved `kind`.

## References

- [Requirements](../Requirements.md): FR-10; register row OD-18.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-question ⑱).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4, 5); [ADR-0056](ADR-0056-od18-correctness-check-verification-executable.md) (decisions 3 to 5); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decisions 3 to 5, 7; Consequences); [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decision 2); [ADR-0079](ADR-0079-od18-correctness-check-build-errors-told-apart.md) (decisions 1, 5); [ADR-0080](ADR-0080-od18-correctness-check-build-errors-now-told-apart.md) (decision 4); [ADR-0081](ADR-0081-od18-correctness-check-compiler-run-error.md) (decisions 1, 2); [ADR-0083](ADR-0083-od18-correctness-check-plain-oserror-before-start.md) (P3; decisions 2, 4); [ADR-0084](ADR-0084-od18-correctness-check-clock-error-after-end.md) (decision 5); [ADR-0085](ADR-0085-od18-correctness-check-clock-error-return-code.md) (decisions 2, 6); [ADR-0086](ADR-0086-od18-correctness-check-path-role.md) (Status; decisions 1, 2, 6, 8; Q2; alternative (f)).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/clang_build.py` and `hilclaw/harness/verification_build.py` at `a46a4d6`; task T-0261 (PR #164).
