---
id: T-0555
title: ADR-0198 slice 3 for PLAN P3-6 — `correctness.check`, `sim.run` and `board.run` read a `compile_settings` run, build a version-3 attempt from the named round's kernel with the target's flags plus the candidate's, and write `measure/…/build.json`; `attempt_kernel` follows the reference
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, OD-32, OD-6, OD-18, FR-5, FR-10, "PLAN P3-6", HQ-0089, ADR-0198, ADR-0116]
dependsOn: [T-0553, T-0554]
touchesFiles:
  - hilclaw/check_tool.py
  - hilclaw/run_tool.py
  - hilclaw/hw_tool.py
  - hilclaw/build_record.py
  - hilclaw/attempt_kernel.py
  - hilclaw/targets.py
  - hilclaw/standin_check.py
  - hilclaw/standin_run.py
  - tests/test_check_tool.py
  - tests/test_run_tool.py
  - tests/test_hw_tool.py
  - tests/test_build_record.py
  - tests/test_attempt_kernel.py
  - tests/test_standin_check.py
  - tests/test_standin_run.py
estimatedSize: {loc: 550, files: 8}
hq: []
---
## Why

**PLAN P3-6** (커널 밖의 후보): **ADR-0198** (T-0552, PR #368) records the owner's answers HQ-0088 and HQ-0089 (2026-11-05) and orders the code slices 1, 2a, 2b, 3, 4 (decision 9; "2a and 3 depend only on 1"). T-0553 (slice 2a) lets the start write a `compile_settings` run; T-0554 (first half of slice 2b) lets the round's flow tools read it while the evaluation tools still refuse it. This task is **slice 3**: the evaluation tools read such a run and evaluate its candidates (decisions 2, 5, 6 and the "Slice 3" column of decision 8). It is ordered after T-0554 because the check and run tools pass the journaled stamp read that T-0554 widens. The remaining half of slice 2b (`spec.write` composing a version-3 spec, the `orchestration/` text) and slice 4 follow in a later planner call; until then nothing writes a version-3 spec outside tests, so this task's tests fabricate one with `hilclaw.spec_file`'s written form.

**Size.** ADR-0198 estimates ~550 LOC and 6 to 8 files; the natural boundary (check tool vs. run tools) would leave two halves sharing the same kernel-reference and `build.json` code, so it stays one task (DRIVER §5, D30). If the files exceed 10 during the work, finish the check tool's half and propose the split in `## Follow-ups`.

**Order (DRIVER §6 D27 ①)** as in T-0553's Why: no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md` (RA-0056 `미확인`), P3-6 the first selectable P3 item. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥/⑦).** As in T-0553: do not ask again or anticipate HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0097; a new owner-only part goes to `## Result` in the DRIVER §8 structure (Korean), the rest lands, `DONE`. Results and `step` values do not change (HQ-0089 ②); if the work seems to need a change to either, that is a frame change (D23) — stop that part and ask.

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5**: branch `claude/T-0555-<slug>`, the `Task: T-0555` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files and build products only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0555/`, working images tagged with the task id, all removed at the end).
- `ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md`: **decisions 2** (the kernel's source and what is checked about it), 4 (the version-3 spec's `task.build`), **5** (`build.json`: the first build, writer and time, write-once, mapping, no file for a C kernel attempt or a call that ends before a build), **6** (target flags then candidate flags, the target's trailing flags; what is refused), 8 (rows 6 and 7, column "Slice 3"), A-13 reading.
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md` decision 2; `ADR-0060-od18-correctness-check-build-answers-and-settings.md` (build answers, `settings_refused`); `ADR-0078-od18-correctness-check-compiler-log-file.md` and `ADR-0108-od18-run-tools-timing-build-compiler-log.md` (one build per call, compiler logs unchanged); `ADR-0056-od18-correctness-check-verification-executable.md` decision 3 and `ADR-0061-od18-run-tools-split.md` decision 3 (the output path); `ADR-0055-od23-coder-output-form.md` (the compiled set); `ADR-0029-od8-spec-file.md` (the written form and the write that gives a name only if free); `ADR-0100-od8-tool-result-change.md`; `ADR-0153-od31-model-executor.md` decision 3 (`attempt_kernel`).
- Code: `hilclaw/check_tool.py` (`_perform`, the `read=instance.read` binding), `hilclaw/run_tool.py` (the same), `hilclaw/hw_tool.py` (`stepped_tool_function`, `_carry_out`), `hilclaw/check_seed.py`, `hilclaw/check_build.py` (`read_build`, `place_error`), `hilclaw/check_failure.py` (`KIND_SETTINGS_REFUSED` and the kinds of a missing or unreadable kernel), `hilclaw/standin_check.py` and `hilclaw/standin_run.py` (`operation_for(target)`, `_build`), `hilclaw/clang_build.py` (what it refuses), `hilclaw/targets.py` (`Target`, `flags`, `trailing_flags`), `hilclaw/build_record.py` (T-0552's validator and reader), `hilclaw/once_write.py` (`write_once`), `hilclaw/layout.py` (`attempt_artefact`, the `measure` role of `build.json`), `hilclaw/spec_file.py` (`parse_versioned`, `final_name`), `hilclaw/attempt_kernel.py`, `hilclaw/kernel_source.py` (`read_compiled_set`), `hilclaw/instance.py` (`read_kinded`, `candidate_kind_of`), `hilclaw/backends.py` (the operation contract and `select`), `hilclaw/mock_check.py`/`mock_run.py` (the mock backend builds nothing).

## Acceptance Criteria

1. **A `c_kernel` run is untouched**: for a version-1 `instance.json`, `correctness.check`, `sim.run` and `board.run` read, build, answer and write exactly as before (no spec read, no `build.json`); existing tests pass unchanged except the D21 edits of criterion 7.
2. **A `compile_settings` run is read** (row 6, "Slice 3"): the three tools accept a version-2 `instance.json` (its members as version 1's) instead of refusing it with `run_file_unsupported`. For the requested attempt they read its `coder/…/spec.json` through `spec_file.parse_versioned`:
   - a **version-2 spec** (round 0's coder attempt, or any coder attempt) is evaluated exactly as in a C kernel run, with the target's settings and no `build.json`;
   - a **version-3 spec** is evaluated from the `output/` of the attempt its `task.build` names (`kernel_round`, `kernel_candidate`, `kernel_attempt`), built with the target's `flags` followed by the candidate's `flags`, then the target's `trailing_flags` (decision 6). Verification, timing, time limits, memory bound, compiler-log files, results and `step` values are the target's and today's.
   The way the candidate's flags reach the build (for example an operation built by `operation_for` with a target whose `flags` are extended, keeping the five-argument operation contract of `hilclaw.backends`) is the executor's choice; prefer one that leaves the backend contract and the mock backend unchanged and state it in the PR body.
3. **Refusals** (decisions 2 and 6), each with an existing kind and no result written: a spec that is missing, unreadable, invalid, of another version, or whose `id` formats to another path; a named attempt that has no version-2 spec (a version-3 attempt is no kernel source) or no compiled set (ADR-0055); a flag `clang_build` refuses (`settings_refused`, as today). Name the kind chosen for each in the module docstrings and the PR body; no new kind (a new kind would be a result frame change — stop and ask, Why).
4. **`build.json`** (decision 5): for a version-3 attempt, the tool that carries out the attempt's first build writes `measure/…/build.json` once — after the build ended and before the result is written — through a write that gives the name only if it is free; a later build finds it and writes nothing. `outcome` `"built"` with no `condition` for a build `check_build.read_build` answers built; `"broken"` with `condition` `build_time_limit` or `build_exit_status` otherwise, the same value as the `broken` result; `flags` and `trailing_flags` the exact argument arrays handed to the compiler. A call that ends before a build ran (`settings_refused`, a missing kernel, a backend that builds nothing) writes none; a version-2 attempt writes none. The document is valid by `build_record.validate`; add the writer to `hilclaw/build_record.py` (or the module the executor finds fitting) with its errors in that module's style.
5. **`attempt_kernel`** (row 7, "Slice 3"): for an attempt whose spec is version 3, `kernel_reference` reads the kernel of the attempt the spec names and returns it with the build settings its caller passes (the module still chooses no settings); a version-2 attempt is read as today; the refusals of criterion 3 map onto its existing `REASONS`.
6. **Docstrings** of the touched modules, including the "no code writes `build.json`" and "a spec is one coder call's" sentences ADR-0198 lists as less exact in `hilclaw/layout.py` and `hilclaw/attempt_kernel.py`, are updated only where this slice makes them untrue.
7. **Tests** (D12), with stub builds as the existing tests use them (a real clang or container build only where an existing test already does so): happy, error, branch and **negative** cases — a version-3 attempt checked at sim and at board and timed by `sim.run`/`board.run`, with the compiler arguments asserted (target flags, then candidate flags, then trailing flags); `build.json` written by the first build only (`built` and both `broken` conditions) and not by the later three; no `build.json` for a version-2 attempt, a `c_kernel` run, `settings_refused`, a missing kernel attempt, a named version-3 attempt, a kernel attempt with no compiled set; a version-3 spec in a `c_kernel` run (refused, existing kind); `attempt_kernel` following a reference. Every public function of the touched modules is tested; `hilclaw/` line and function coverage stay ≥ 80%. Existing tests stay unchanged except (a) list assertions under D21 — foreseen: `tests/test_build_record.py::test_the_public_names`, `tests/test_hw_tool.py::test_the_public_names_and_the_signature`, `tests/test_run_tool.py::test_the_module_imports_and_names`, `tests/test_check_definition.py::test_the_module_imports_what_it_names_and_has_its_public_names_only` and `tests/test_run_definition.py::test_the_module_imports_what_it_names_and_has_its_public_names_only` if a public name or import changes; (b) the T-0554 tests asserting that `correctness.check`, `sim.run` and `board.run` refuse a version-2 run — rewrite them to the new rule. List every such edit in the PR body.
8. **Unchanged behaviour** otherwise: every version-1 run, nightly and model path behaves and writes exactly as before; the full test suite passes.
9. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0555`. Record the language (Python) and the reason in `## Result`. If a build on the machine (clang, Docker) is used for an extra check, record the commands in `## Result` and remove what it made (D29).

## Out of Scope

- `spec.write` composing a version-3 spec, the `technique-selector`'s choice of flags, `orchestration/` text (second half of slice 2b); CLAUDE.md's "C 커널" wording, the StandardScenarios scenario and the runtime acceptance item for a live coder-free round (slice 4).
- Any `ARCHITECTURE/` edit: ADR-0198 decides this slice. If a design decision it does not make is needed, report it in `## Result` instead of writing a new ADR here.
- A kernel from another run; cases, the S6 metric and model runs of a `compile_settings` run; any change to results, `step` values, `events.ndjson`, `artifacts.json` or `STATE.json`; vendor targets and HQ-0095 to HQ-0097.
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

- The planner then creates the second half of slice 2b (`spec.write` composing a version-3 spec on the `technique-selector`'s request in a `compile_settings` run, `orchestration/round-manager.md` steps 6 and 8, `orchestration/agents/technique-selector.md`) and slice 4 (CLAUDE.md wording — HQ-0088 ③, the StandardScenarios scenario — HQ-0088 ⑤, the runtime acceptance item of ADR-0198 Consequences); PLAN P3-6 is checked after slice 4.

## Result

- **Outcome**: DONE. PR #371 (`claude/T-0555-compile-settings-evaluation`), squash-merged into `main`; the merge commit is the squash of PR #371 and carries `Task: T-0555`. 2 review rounds by a context-isolated reviewer (round 1 Approve with four Nits, round 2 Approve with four Nits). CI on GitHub was green before the merge.
- **Order check (D27 ①)**: unchanged at the start: no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`, P3-6 the first selectable P3 item.
- **Language**: Python. Every module touched is a Python module of the 2nd-layer package `hilclaw/`, and the change only extends those modules.
- **What landed**:
  - `correctness.check`, `sim.run` and `board.run` read an `instance.json` of version 2 (row 6, "Slice 3").
  - A kind other than `c_kernel` and `compile_settings` is `run_file_unsupported` before the start line.
  - In a `compile_settings` run the asked attempt's spec is read after the start line by `build_record.evaluated`. A version-2 spec is evaluated as in a C kernel run.
  - A version-3 spec is evaluated from the named attempt's `output/`. It is built with the target's `flags`, then the candidate's `flags`, then the target's `trailing_flags`.
  - `build.json` is written by `CandidateBuild.write` (once, by `once_write.write_once`) after the operation came back and before the end line.
  - A `c_kernel` run reads no spec and writes no `build.json`.
  - `attempt_kernel.kernel_reference` follows a version-3 spec to the named kernel, with `kernel_attempt`/`KernelAttempt` new.
- **How the flags reach the build**: a `contextvars.ContextVar` in `hilclaw/build_record.py` (`building`/`current`). The five-argument operation contract of `hilclaw.backends` and the mock backend are unchanged. `standin_check`/`standin_run` read it (`candidate_target`, `report_build`).
- **Kinds (criterion 3; no new kind)**: listed in the `hilclaw/build_record.py` module docstring and the PR body.
  - `no_kernel_source` for:
    - a missing spec, or a spec of a version other than 2 and 3;
    - a named attempt whose spec is missing or of version 3;
    - a named attempt with no compiled set.
  - `kernel_source_unreadable` for an unreadable or invalid spec, an `id` that formats to another path, and a reader failure.
  - `settings_refused` (raised by the operation) for a candidate flag `clang_build` refuses.
- **Readings that are this task's own (ADR-0198 does not decide them; no ADR written)**:
  1. In `sim.run`/`board.run`, `build.json` records the timing build, which is the kernel's build. A waiter build that fails after it, or the shared build time limit running out, makes the result `broken` while `build.json` says `built`. This reads decision 5 ("the first build of the attempt's candidate") as the kernel build. In the round order the first build is `correctness.check` at `sim`, which has no waiter.
  2. A write of `build.json` that fails with an `OSError` changes no result and is not answered. The name stays free, so a later build of the attempt writes it. No kind exists for this, and adding one would be a frame change.
  3. A status-0 build that leaves no executable (S9, `build_output_missing`) is not recorded, because `check_build.read_build` does not answer it "built". A tool failure raised after a recorded build (for example `executable_unstartable`) still writes `build.json`.
- **Existing tests changed**: listed in the PR body.
  - D21 lists: `test_build_record.py::test_the_public_names`, `test_check_tool.py::test_the_module_holds_what_it_joins_and_nothing_of_its_own`, `test_run_tool.py::test_the_module_imports_and_names`.
  - The T-0554 v2-refusal tests of `test_check_tool.py`/`test_run_tool.py` are rewritten to slice 3.
  - `test_attempt_kernel.py::test_a_spec_of_another_version` changed from `[1, 3]` to `[1, 4]`, because criterion 5 makes version 3 followed.
- **Size**: 8 non-test files.
  - The 8 files: `attempt_kernel.py`, `build_record.py`, `check_tool.py`, `run_tool.py`, `standin_check.py`, `standin_run.py`, `targets.py`, and `journaled_tool.py` (docstring only; not in `touchesFiles`).
  - About 650 changed non-test lines, much of it docstrings.
  - `tests/test_targets.py` is a test file outside `touchesFiles`.
  - `hilclaw/hw_tool.py` was not changed: its sentence about a version-1-only reader is still true as a general statement.
- **Nits not taken**:
  - The output-flag rule is restated in `targets.with_candidate_flags` and not shared with `clang_build`, whose check is private.
  - `_read`/`_evaluated` are duplicated in `check_tool.py` and `run_tool.py`.
- **Runtime acceptance items**: none from this slice. ADR-0198's item, a live coder-free round ≥ 1 of a `compile_settings` run, is handed to `PROCESS/RuntimeAcceptance.md` by slice 4.
- **List assertions amended (D21)**: the three above.
- **Builds and test runs**: none. Builds are stubs only: no clang, no container, no `claude`, no test run (D25).
- **Temporary files**: everything was under `${TMPDIR}/hilclaw-driver/T-0555/`, which was removed at the end. No image was made.
- **Follow-ups**: none new. The planner's follow-ups in this file stand: the second half of slice 2b, then slice 4.
