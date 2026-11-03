---
id: T-0532
title: Add the target table of ADR-0193 decision 3 and make the cpu_standin builds, the instance start and the model-run binding read it
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, OD-32, FR-10, NFR-6, "PLAN P3-2"]
dependsOn: []
touchesFiles:
  - hilclaw/targets.py
  - hilclaw/standin_settings.py
  - hilclaw/standin_check.py
  - hilclaw/standin_run.py
  - hilclaw/standin_openmp.py
  - hilclaw/check_definition.py
  - hilclaw/start_instance.py
  - hilclaw/model_instances.py
  - hilclaw/model_run_binding.py
  - tests/test_targets.py
  - tests/test_model_run_binding.py
  - tests/test_start_instance.py
  - tests/test_check_definition.py
  - tests/test_standin_settings.py
estimatedSize: {loc: 350, files: 9}
hq: []
---
## Why

**PLAN P3-2** ("컴파일 옵션과 대상의 분리"): the build options of `cpu_standin` are CPU constants (`hilclaw/standin_settings.py`) and a model run has one fixed target (`TARGET` in `hilclaw/model_run_binding.py`). P3-2 moves them to values a target decides. P3-1 is checked: its design is ADR-0193, landed on `main` in `d213d9a6`. Decision 3 of that ADR places the target description in a table in the package source, `hilclaw/targets.py`, and decision 8 sizes P3-2 at about 350 LOC in 8 files with nothing to wait for. This is that one task.

**Order (DRIVER §6 D27 ①).** On `main` `2f116108` no `nightly-failure` issue is open, `PROCESS/RuntimeAcceptance.md` RA-0056 is `미확인` with no `실패` value to fix, and no P2-15 preparation is pending. So the next P3 item in listed order is P3-2. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs that do not govern this task (D27 ⑥).** HQ-0088 (candidate kinds), HQ-0089 (record format of other kinds), HQ-0090 (the unit list) and HQ-0091 (oracle and data types at `virtual_npu`) are unanswered. Their own "[막히지 않는 것]" lines name P3-2 as not held up. ADR-0193 decision 3 says the target table changes no data-plane frame: no file, member or value of the data plane holds it. Nothing in this task may anticipate an answer to them: no `candidate_kind`, no unit other than `ns`, no `virtual_npu` entry (that is P3-3), no new data-plane member.

**P2-15 must not change (D27).** The owner's P2-15 check runs `hilclaw.model_check`. For every run it accepts today it must behave as before (ADR-0193 decision 3, "The model run").

**D16.** Verification is on the development machine with the existing tests (clang where the existing tests already use it, stub Docker clients and stub `claude` where they already do). No real `claude`, board or API key.

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0532-<slug>`, the `Task: T-0532` trailer and the PR body's last line, the size cap, the test rules D12, the list-assertion rule D21), §3 "BLOCKED 사유" and "승인된 열린 목록" (D23), §6 D27.
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (state the language and the reason in one line of the commit body and `## Result`), "코멘트 최소화".
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: Status; decision 1 (the survey table, rows lifted by P3-2); **decision 3 in full** (the binding text of this task); decision 4, only the row `model_run` of its table and the sentence after it ("the second-target path of P3-2 is tested with a test's own `Target`"); decision 7; decision 8, row P3-2; Consequences, "A-13 reading".
- `ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md` decision 2 (the one fixed set and where it lives), `ADR-0117-od14-cpu-standin-time-limits.md` decisions 2 to 4 (the build limit and the process cap), `ADR-0188-od18-standin-openmp-in-the-build-set.md` decisions 1 and 2, `ADR-0189-od31-binding-from-run-incumbents.md` decisions 1 and 6, `ADR-0016-od18-backend-frame.md` decisions 2 to 4, `ADR-0060` decision 3 (an operation does not read the hw_profile handed to it for its settings).
- Code: `hilclaw/standin_settings.py` (whole); `hilclaw/standin_check.py` lines 186-275 and 382-400; `hilclaw/standin_run.py` lines 146-210 and 257-295; `hilclaw/standin_openmp.py` lines 55-110; `hilclaw/check_definition.py` lines 120-160; `hilclaw/start_instance.py` (whole); `hilclaw/model_instances.py` lines 76-90 and 170-190; `hilclaw/model_run_binding.py` (whole); `hilclaw/model_check.py` lines 300-330 and 360-380; `hilclaw/contract_table.py` lines 55-75; `hilclaw/run_result.py` around `UNITS`; `hilclaw/instance_start.py` lines 130-190; `hilclaw/s6_metric.py` line 157 (left unchanged, see Out of Scope).
- Tests: `tests/test_model_run_binding.py` (lines 300-330 and 430-445), `tests/test_start_instance.py`, `tests/test_check_definition.py`, `tests/test_standin_settings.py`, `tests/test_model_check.py` around line 376.

## Acceptance Criteria

1. **The table.** A new module `hilclaw/targets.py` (Python) holds a `Target` value type and a read-only table from `accelerator` name to `Target`, with exactly one entry, `cpu_standin` (`hilclaw.standin_profile.ACCELERATOR`). A `Target` carries the members of ADR-0193 decision 3: `flags`, `trailing_flags`, `waiter_flags`, `env`, the build time limit, the process time-limit cap, `contracts` (keys of `hilclaw.contract_table.TABLE`), `memory_limit_bytes` (an `int` or `None`), `unit`, `model_run` (`bool`) and `instance_start` (`bool`). The mock has no `Target`. A lookup function returns the `Target` of a name and raises a documented exception for a name with none.
2. **Validation of a `Target`.** Building one refuses, with `TypeError` or `ValueError` as fits: flags that are not a tuple of `str`; a non-positive or non-numeric time limit or cap (a `bool` refused); a `contracts` item that is not a key of `contract_table.TABLE`; a `memory_limit_bytes` that is not `None` or a positive `int` (a `bool` refused); a `unit` not in `hilclaw.run_result.UNITS`; a `model_run` or `instance_start` that is not exactly a `bool`. Tests cover each refusal (negative cases).
3. **`cpu_standin` keeps its values and results.** Its `Target` reads the constants of `standin_settings.py`, which stay the source of those values (ADR-0193 decision 3; ADR-0116 decision 2 (a)): `flags` = `FLAGS`, `trailing_flags` = `TRAILING_FLAGS`, `waiter_flags` = `WAITER_FLAGS`, `env` = `ENV`, build limit = `BUILD_TIME_LIMIT_S`, cap = `PROCESS_TIME_LIMIT_CAP_S`; `contracts` = all seven keys of `TABLE`; `memory_limit_bytes` = `None`; `unit` = `"ns"`; `model_run` and `instance_start` true. A test asserts each value.
4. **Builds and processes read their target.** The `cpu_standin` operations of `correctness.check`, `sim.run` and `board.run` (`standin_check.py`, `standin_run.py`) take their flags, trailing and waiter flags, build time limit and process time-limit cap from a `Target`, and are built with that `Target`, so an operation reads its own target and never the hw_profile handed to it (ADR-0193 decision 3; ADR-0060 decision 3). `check_definition.default_table` builds the `cpu_standin` backend with the `cpu_standin` `Target`. The process-limit functions of `standin_settings.py` take the cap from their caller (for example a keyword with the current constant as default), so the rule of ADR-0117 decision 4 is unchanged. `standin_openmp.check` reads the `cpu_standin` `Target`'s flags and build limit. `standin_check.operation` and `standin_run.operation` stay callable as today with the `cpu_standin` target, so existing callers and tests keep working.
5. **The instance start.** `start_instance` admits the mock's name and each target whose `instance_start` is true, read from the table, in place of the hand-kept `_ACCELERATORS`; `model_instances.py`, which imports that name, admits the same set. With the one entry, the admitted set equals today's `("mock", "cpu_standin")`.
6. **The model-run binding.** `model_run_binding.binding_from_runs` takes a run whose `accelerator` has a `Target` with `model_run` true and refuses others with the existing `other_target` reason. All call sites of one binding must have one target: a binding whose named runs are at two targets is refused with a new reason that is added to `REASONS` and documented. The binding takes the target table from a parameter or another seam that a test can replace, with the package table as the default; `hilclaw.model_check` passes nothing new and keeps its behaviour for every run it accepts today. `flags` stay the caller's (ADR-0189 decision 6).
7. **The second-target path is tested with a test's own `Target`** (ADR-0193 decision 4): a test table with a second `Target` whose `model_run` is true binds a run at that accelerator; with `model_run` false the run is refused `other_target`; runs at `cpu_standin` and at the test target in one binding are refused with the new reason; an accelerator with no `Target` is refused `other_target`.
8. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21). Pinning assertions this task is expected to touch: `tests/test_model_run_binding.py` line 316 (`model_run_binding.TARGET == standin_profile.ACCELERATOR`, if `TARGET` is removed or replaced) and any assertion that enumerates `REASONS` or `start_instance`'s accelerator name. The existing tests of the argument lists of the `cpu_standin` builds and processes pass with no edit (ADR-0193 decision 3, "Check for P3-2"). Each edited assertion is listed in the PR body.
9. **Tests (D12).** A new `tests/test_targets.py`; every public function of each touched module is covered; happy, error, branch and negative cases; package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally, and clang-based tests run where they already run.
10. **No frame change.** No file, member, value or version of the data plane changes (instance, spec, result, `events.ndjson`, `artifacts.json`, hw_profile key), no open list of DRIVER §3 gets a value, and `run_result.UNITS` is unchanged. If the work shows that one is needed, stop and return `BLOCKED` with the reason (A-13; DRIVER §8) rather than making it.

## Out of Scope

- The `virtual_npu` target, its backend, a memory bound on containers, coverage per target (`contract_table.covers` and its siblings reading `contracts`), and `Target.unit` read where a result is built: all PLAN P3-3.
- `s6_metric._ACCELERATORS` (`hilclaw/s6_metric.py:157`): ADR-0193 decision 1 leaves it unlifted (HQ-0081's neighbour).
- Moving the constants out of `standin_settings.py` (ADR-0193 Alternatives).
- Any edit of `ARCHITECTURE/` (ADR-0193's "Less exact, not edited" list stays as it is) and of `hilclaw/model_forward.c`, `model_forward_run.py` or the behaviour of `model_check`.
- A candidate-kind abstraction (ADR-0193 decision 2), anything that depends on HQ-0088 to HQ-0091.
- A runtime acceptance item: none is expected from this task, since `cpu_standin`'s behaviour does not change.

## Follow-ups

- PLAN P3-3 builds on the table this task adds (ADR-0193 decision 8, ~500 LOC, 1 task).

## Result

- **Outcome**: DONE (pending review; this section is updated at landing). Order check (D27 ①) on `ec58f7c7`: no open `nightly-failure` issue, no open PR, RA-0056 still `미확인`; P3-2 stands as the next item.
- **Language**: Python, as the touched modules and the existing `hilclaw` package (the target table is a value table read by Python tools).
- **What changed**
  - New `hilclaw/targets.py`: `Target` (frozen dataclass; every member checked at construction), `CPU_STANDIN`, `TABLE` (read-only mapping with the one entry `cpu_standin`, built from the `standin_settings.py` constants each time it is read, so those constants stay the source and a test that patches one is still seen), `target(name, table=TABLE)` raising `NoTargetError` (a `LookupError`), `instance_start_accelerators(table=TABLE)`.
  - `standin_check` / `standin_run`: `operation` reads the `cpu_standin` `Target` at each call; new `operation_for(target)` builds the same operation with any `Target`. Flags, trailing flags, waiter flags, build limit and process-limit cap come from the `Target`.
  - `standin_settings`: the four process-limit functions take an optional `cap_s` (default `None` = `PROCESS_TIME_LIMIT_CAP_S` read at the call; refused unless finite and above 0). The rule of ADR-0117 decision 4 is unchanged.
  - `standin_openmp.check`: flags and the default build limit come from the `cpu_standin` `Target` (`timeout_s=None` means that limit).
  - `check_definition.default_table`: still selects `standin_check.operation` and `standin_run.operation` (existing tests pin their identity and monkeypatch them); its docstring states they are the operations built with the `cpu_standin` `Target`.
  - `start_instance._ACCELERATORS` = the mock plus `targets.instance_start_accelerators()` (= `("mock", "cpu_standin")`); `model_instances` imports it unchanged.
  - `model_run_binding`: `TARGET` removed; `binding_from_runs(..., table=targets.TABLE)` takes a run whose accelerator has a `Target` with `model_run` true (else `other_target`), and a run at another accelerator than the binding's first run is refused with the new reason `two_targets` (in `REASONS` after `other_target`). `model_check` passes nothing new.
- **Edited existing assertions (D21)**: `tests/test_model_run_binding.py` `test_a_run_of_another_target_is_refused`: `model_run_binding.TARGET == standin_profile.ACCELERATOR` replaced by `targets.TABLE[standin_profile.ACCELERATOR].model_run is True` (the name `TARGET` is removed); the import lists of that file gain `targets` and `TWO_TARGETS`. `tests/test_run_result.py::test_no_other_module_of_the_package_but_the_tool_function_imports_it`: allowed importers of `run_result` gain `targets.py`. `tests/test_standin_profile.py::test_module_is_bound_by_the_start_only_and_imports_no_store`: files allowed to name `standin_profile` gain `targets.py` (the operations use `targets.CPU_STANDIN`).
- **No frame change**: no data-plane file, member, value or version; `run_result.UNITS` unchanged; no open list used.
- **Runtime acceptance items**: none.
