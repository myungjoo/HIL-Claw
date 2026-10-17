# ADR-0094: What a check of `correctness.check` answers for the `TypeError` with `parameter` `"env"` that `clang_build.build` now raises for an `env` with no `items` method — S4, `settings_refused`, as the landed rules already answer it — and what is left open (more of part (마) of sub-question ⑱ of OD-18)

## Status

- **Accepted on 2026-10-18** under [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9 (owner decision D6): written by the development driver's executor and accepted by the approval of a context-isolated reviewer. The owner has not confirmed it.
- **Three kinds of content.** **Owner** sentences: none is quoted. Which side holds the environment, cited from [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) decision 3, rests in part on that record's O4 and reaches this record only through it. What an accepted record or a task file says is **cited** with its source. **The rest is this record's own design**: that the landed rules already answer the new error, the reason it gives for that, what it reads as left open, and every weighing. Statements about code are **observations** at `4e05627` of `hilclaw/clang_build.py` and `tests/test_clang_build.py`, read as files; they bind no code, and none was established by running code.
- Answers **more of part (마) of sub-question ⑱ of OD-18** (Open Decisions register in [Requirements](../Requirements.md)) for `correctness.check` of the first case and of the mock: the row of the `TypeError` with `parameter` `"env"` that `build` raises for an `env` with no `items` method (decision 2). This record only confirms that answer of the landed rules. It narrows, and leaves open, the entries decision 3 names, and leaves open the rest decision 5 lists. Parts (가), (다), (라) and the size bound of (나) are not answered. OD-18 keeps its status word.
- **Nothing of the data plane changes**: no member of any file, result, request or line, no value of `condition` or `error.kind`, no reserved kind, no `schema_version` or layout version.
- **No sentence of an earlier record is replaced or edited.** Consequences lists the sentences that become less exact. The number 0088 is held by an unlanded branch on `local_run.run`; this record neither cites nor needs it.
- It builds on [ADR-0093](ADR-0093-od18-correctness-check-temporary-name-value-error.md) (decisions 1, 3 and 5; its window runs until 2026-10-24), [ADR-0089](ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md) (P2; decisions 2, 7 and 9; until 2026-10-24), [ADR-0091](ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md) (decision 3; until 2026-10-24), [ADR-0087](ADR-0087-od18-correctness-check-type-error-parameter.md) (decisions 2 to 4; until 2026-10-24), [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decision 2; until 2026-10-23), ADR-0060 (decisions 3 to 5; until 2026-10-22) and [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4 and 5; until 2026-10-19). **If one of them is reverted, this record falls with it.**
- **It is a record, not code**: nothing in it was established by running code, and no compiler, container or `claude` process was started.
- The owner is notified on issue #5 and may object within 7 days of that notice; an objection creates a task that reverts this record and the edits made with it.
- The format follows the "Record format" section of [ADR-0001](ADR-0001-od4-key-schema.md).

## Context

- ADR-0093 decision 3 kept open, under U4, "`subprocess.Popen`, for the command, `cwd` and `env` `build` hands it, an `env` with no `items` method included", and named as what would let it be placed "a code change that makes `build` refuse an `env` with no `items` method … in a named check before the start" (cited). Task T-0282 (PR #178, `4e05627`) made that change; its task file says "It records no row of `correctness.check`" (cited).
- **Observations at `4e05627`** (no code is bound):
  - **E1. Where the check runs.** In `build`, after `with _parameter("compiler"):` has found the compiler and before `with _parameter("cwd"):`, the step `with _parameter("env"): _check_env(env)` runs. `_check_env` returns for `None`; otherwise it reads `getattr(env, "items", None)`, and when that is `None` it raises `TypeError(f"env must be None or have an items method, not {type(env).__name__}")`. `_parameter` sets `parameter` on a `TypeError` or `ValueError` and re-raises it unchanged. The pid and the random part, the temporary name, the clock and `subprocess.Popen` all come after the check of `cwd`, so none of them is reached.
  - **E2. What the docstring says.** "`env` and `cwd` are checked as `subprocess` would refuse them, with the class it would raise for the same single defect, with one exception: an `env` that is not `None` and has no `items` method is refused with `TypeError`, as `subprocess` has no single class for it (the class differs by platform and start path)" (cited).
  - **E3. The message** holds the name of the type, never the value.
  - **E4. What T-0282's tests show** (`tests/test_clang_build.py`, cited, not run here): for `[("A", "x")]`, `5`, `"A=x"`, `b"A=x"`, `object()` and an object whose `items` is `None`, the error is of type `TypeError` exactly, with `parameter` `"env"`, no `path_role`, the type name and "items method" in the message, and nothing started (`test_an_env_without_items_is_a_type_error_naming_env`); `"SECRET=1"` gives a message with `str` and without `SECRET` (`test_an_env_without_items_message_names_the_type_and_not_the_value`); an `items` that is `3` is refused by the call, a `TypeError` with `"env"` whose message does not say "items method" (`test_an_env_whose_items_cannot_be_called_is_refused_by_the_call`); with `cwd=3` as well, the error carries `"env"` (`test_an_env_without_items_is_named_before_the_cwd`); with `timeout_s=0` as well, the `ValueError` carries `"timeout_s"` (`test_an_earlier_defect_comes_before_an_env_without_items`); the class, message, arguments and `parameter` survive pickling (`test_an_env_without_items_keeps_its_parameter_through_pickling`).
  - **E5. Before T-0282** (cited from its `## Why` as the planner's observations, not established here): `subprocess.Popen` refused such an `env` after the temporary name and the clock were drawn, with no `parameter`, and with a class that depended on the platform, the Python version and the start path.
- No owner comment on #5 speaks to ADR-0093, T-0282, the `env` check or ⑱ (마) (checked on 2026-10-18: every comment since 2026-10-17 carries the driver tail), and HQ-0027 is unanswered.

## Decision

### 1. Scope and terms

- A call of `correctness.check`, the six kinds, S1 to S10 and the keeper, as ADR-0093 decision 1 has them; the operation reads the class (`isinstance`) and `getattr(error, "parameter", None)` (cited: ADR-0087 decision 2). **The environment** is "the backend's own" (cited: ADR-0060 decision 3). **The no-`items` error** is the `TypeError` of E1 with `parameter` `"env"` and no `path_role`. **The mock** builds nothing and is unchanged.

### 2. The no-`items` error is S4, `settings_refused`; the landed rules already say so

- **The operation raises it as S4, `settings_refused`.** "A named `TypeError` or `ValueError` whose `parameter` is `"env"` is S4, `settings_refused`" (cited: ADR-0089 decision 2), and the class and `parameter` are all the operation reads (decision 1), so **that rule already answers the no-`items` error, and this record only confirms it.** The sentence of ADR-0089 decision 2 that kept such an `env` out — "An `env` with no `items` method is not checked (P2)" (cited) — said what the code then did, not a rule against the row; the code now checks it (E1).
- **Why the confirmation holds by meaning, not only by form.** The environment is the backend's own (ADR-0060 decision 3), and S4 names "an environment that cannot be handed over" and "a setting of the wrong type", found "before the process the refused setting belongs to is started", "whether the setting is refused for its value or for its type" (cited: ADR-0060 decision 4). An `env` with no `items` method is an environment of the wrong type, refused before anything is started (E1, E4). ADR-0087 decision 3 places a named `TypeError` of the four settings in S4, and ADR-0089 decision 2 reads `"env"` as it does; ADR-0087 decision 4 places one in no row only for "an argument that is no setting" (cited); the environment is no argument the operation forms.
- **The operation cannot tell it from the other errors of the `"env"` step**: on Windows a key that is no `str` gives a `TypeError` with `"env"` too (cited: ADR-0089 Walk-through), and so does an `items` that cannot be called (E4). Any other row would move those too.
- **The cost, stated** as ADR-0089 decision 2 and ADR-0087 decision 3 state it: a defect in the code that hands the environment over is read as a refused setting.

### 3. What is left open

- **Removed**: an `env` with no `items` method. It no longer reaches `subprocess` (E1), so it is no longer among what `build` passes on from `subprocess`, no longer under U4's entry of `subprocess.Popen` (ADR-0093 decision 3), and no longer a source of an unnamed `TypeError` from `subprocess.Popen` or later.
- **What stays, read from the code** — no claim is made beyond what is read and cited: U4 as ADR-0093 decision 3 reads it, with its entry of `subprocess.Popen` now for the command, a `cwd` that passed its check and an `env` that has an `items` method and passed its check (E1); the draws of the pid and the random part, the command and the clock stay as there. What `subprocess` raises for any of them was not read.
- **An `env` that has `items` and that `subprocess` still refuses** on some platform or start path — T-0282 names three: on native Windows an object with `items` but no `keys` or `values`, the empty key, and a key whose only `=` is its first character (cited: its Out of Scope) — passes the check of E1 and reaches `subprocess.Popen` unchanged. **This record does not place it**: what `Popen` raises for it was not read, and it stays under U4 if a `ValueError`, under the unnamed `TypeError` of `subprocess.Popen` or later if a `TypeError`, and otherwise under what `subprocess` passes on. Until then an operation that lets it pass is answered `operation_answer_invalid` (cited: ADR-0045 decisions 4 and 5).
- **What would let the rest be placed** (named, not decided): a reading of what `subprocess.Popen` raises for those values; or a code change that makes `build` refuse them in the `"env"` step before the start. Either is a later task's.

### 4. No log, and the message

- **No log.** The no-`items` error is raised before any process exists (E1, E4), and S4 "found before the build" has no log (cited: ADR-0078 decision 2); the operation hands nothing to the keeper.
- **The message of `settings_refused` for `"env"`** may say that the environment was refused and of which kind the error was, and shows "no text of an error, no value of a setting" (cited: ADR-0060 decision 5; as ADR-0089 decision 7 applies it). No rule is added; the wording is the code's.

### 5. How far (마) is answered

- **Answered now, for `correctness.check` of the first case and of the mock**: the no-`items` error — S4, with no log (decisions 2 and 4), confirming ADR-0089 decision 2 for it.
- **Narrowed**: U4's entry of `subprocess.Popen`, the unnamed `TypeError` of `subprocess.Popen` or later, and what `subprocess` passes on no longer hold an `env` with no `items` method (decision 3).
- **Still open under (마)**, as the sub-question ⑱ bullet of OpenDecisionProposals lists them on `main`, changed only as decision 3 says: the row of a `CompilerRunError` whose `timed_out` is false and whose `returncode` is `None`; an `OSError` without `path_role` before the start from `os.getcwd`, `os.urandom`, `time.monotonic` or the compiler lookup; an unnamed `TypeError` of `build` (binding the call, `subprocess.Popen` and later, the draws of the pid and the random part, the command and the clock) and of `build_verification_executable` (binding the call); U4, the unnamed pre-start `ValueError` of `build` from the draws of the pid and the random part, the command, `time.monotonic` and `subprocess.Popen`; whatever else `subprocess` passes on, an `env` with `items` that it refuses included; and the `ValueError` or `TypeError` and the `OSError` for a missing `cwd` of `local_run.run`, which wait for its record.

## Alternatives considered

| Point | Alternative | Why not |
|---|---|---|
| 2 | **(a)** S4, confirmed from the landed rules (chosen) | ADR-0089 decision 2 already places a named `TypeError` with `"env"` in S4; the environment is the backend's own (ADR-0060 decision 3) and S4 names a setting of the wrong type (ADR-0060 decision 4). The cost is decision 2's. |
| 2 | **(b)** No row, as handing a value with no `items` method is a defect of the operation's own code | ADR-0060 decision 4 and ADR-0087 decision 4 make that reading for an argument that is no setting; the environment is a setting, and ADR-0087 decision 3, as ADR-0089 decision 2 applies it to `"env"`, reads a fault of a handed setting as S4. The operation could not tell this error from the other `"env"` errors (decision 2), so the row would move them against ADR-0089 decision 2. |
| 2, 3 | **(c)** Keep it open with what `subprocess` passes on until `Popen` is read | It no longer reaches `subprocess` (E1) and carries `parameter` `"env"` (E4); the landed rule answers it by what the operation reads. |
| 2 | **(d)** A kind or row of its own for an `env` of the wrong type | It needs a new value of `error.kind` that no record names, which this record may not add, and S4 already names the situation. |
| 3 | **(e)** S4 also for an `env` with `items` that `subprocess` refuses | What `Popen` raises for it was not read and carries no `parameter`; ADR-0091 decision 3 and ADR-0093 decision 3 keep such errors open. |

## Consequences

- **Code** (code mode, D12 rules; names and modules are the code task's; **this record binds no code**): the operation of `cpu_standin` for `correctness.check`, when it is written, raises `settings_refused` for a `TypeError` or `ValueError` whose `parameter` is `"env"`, as ADR-0089 decision 2 already says; it needs no step of its own for the no-`items` error. A reading of `subprocess.Popen` for an `env` with `items` that it refuses, or a code change for one, is a candidate follow-up, not required by this record. The same change for `local_run.run` waits for HQ-0027.
- **Not edited and now less exact.**
  - ADR-0089 P2: "any other `env` is left to `subprocess`", and the observation "with the class it would raise for the same single defect" without its one exception (E2); decision 2: "An `env` with no `items` method is not checked (P2) and stays under what `build` passes on from `subprocess` (decision 9)"; decision 9: "whatever `clang_build.build` still passes on from `subprocess`, an `env` with no `items` method included".
  - ADR-0093 decision 3: "`subprocess.Popen`, for the command, `cwd` and `env` `build` hands it, an `env` with no `items` method included", and under "What would let it be placed" the code change for "an `env` with no `items` method", now made; decision 5: U4 "as decision 3 reads it", now narrower.
  - ADR-0087 T4: "one from `subprocess.Popen` or later (for example a `cwd` or an `env` that cannot be handed over)", where an `env` with no `items` method no longer reaches `Popen`; decision 5: "an `env` is a setting (S4)", for an unnamed `TypeError` from `Popen`, which no longer holds this case.
- **A question for the owner**: none is raised; no case is left open for want of a new value.
- **A-13 reading.** Nothing of the data plane is added or changed.
- **Runtime acceptance items**: none. No `claude`, compiler or container is started or required.

## Boundaries (not decided here)

- U4 and the other open entries of (마) (decision 5), an `env` with `items` that `subprocess` refuses included; what `subprocess` raises on which platform or start path.
- **`local_run.run`** and every entry that waits for its record and HQ-0027; the timing build of `sim.run` / `board.run` (⑲; HQ-0021).
- **⑱ (가), (다), (라) and the size bound of (나)**.
- **Owner-only (DRIVER §9)**: the #5 A and B items; OD-3; OD-25; C-6.
- Any change to ADR-0001 to ADR-0093, to `hilclaw/`, to tests, to CI or to any settings file; any new external dependency; any new reserved `kind`.

## References

- [Requirements](../Requirements.md): FR-10; register row OD-18.
- [OpenDecisionProposals OD-18](../OpenDecisionProposals.md#od-18) (sub-question ⑱).
- [ADR-0001](ADR-0001-od4-key-schema.md) (record format); [ADR-0045](ADR-0045-od18-correctness-check-neither-form-answer.md) (decisions 4, 5); [ADR-0060](ADR-0060-od18-correctness-check-build-answers-and-settings.md) (decisions 3 to 5); [ADR-0078](ADR-0078-od18-correctness-check-compiler-log-file.md) (decision 2); [ADR-0087](ADR-0087-od18-correctness-check-type-error-parameter.md) (T4; decisions 2 to 5); [ADR-0089](ADR-0089-od18-correctness-check-clang-build-pre-start-checks.md) (P2; decisions 2, 7, 9; Walk-through); [ADR-0091](ADR-0091-od18-correctness-check-sources-output-kernel-sources-value-errors.md) (decision 3); [ADR-0093](ADR-0093-od18-correctness-check-temporary-name-value-error.md) (decisions 1, 3, 5).
- D6 https://github.com/myungjoo/HIL-Claw/issues/5#issuecomment-5986348506.
- [PROCESS/DRIVER.md](../../PROCESS/DRIVER.md) §9; PROCESS/PLAN.md P1-1; `hilclaw/clang_build.py` and `tests/test_clang_build.py` at `4e05627`; task T-0282 (PR #178; `## Why`, `## Out of Scope` and `## Result`).
