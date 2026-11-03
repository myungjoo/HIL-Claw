---
id: T-0533
title: Add the virtual_npu target and backend of ADR-0193 decision 4 (flags, memory bound, coverage per target, unit read from the target) below the instance start
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, FR-10, FR-14, NFR-6, "PLAN P3-3"]
dependsOn: []
touchesFiles:
  - hilclaw/targets.py
  - hilclaw/contract_table.py
  - hilclaw/check_definition.py
  - hilclaw/run_definition.py
  - hilclaw/run_tool.py
  - hilclaw/standin_container.py
  - hilclaw/standin_check.py
  - hilclaw/standin_run.py
  - hilclaw/standin_profile.py
  - tests/test_targets.py
  - tests/test_contract_table.py
  - tests/test_check_definition.py
  - tests/test_run_definition.py
  - tests/test_run_tool.py
  - tests/test_standin_container.py
  - tests/test_standin_check.py
  - tests/test_standin_run.py
  - tests/test_standin_profile.py
estimatedSize: {loc: 500, files: 9}
hq: []
---
## Why

**PLAN P3-3** ("가상 NPU"): a backend that runs on the development machine with compiler options, memory limit, data types and measurement unit deliberately unlike the CPU's, to make first-case assumptions fail. Its values are for the generalization check only and are no fact or evidence about any real NPU. P3-1 is checked (ADR-0193, `d213d9a6`) and P3-2 is checked (T-0532, PR #349, `1475e57c`: the target table `hilclaw/targets.py`). ADR-0193 decision 4 is the design of this item, and decision 8 sizes it at about 500 LOC in 8 files as one task, plus one small task on the answer to O3 (HQ-0090).

**Order (DRIVER §6 D27 ①).** On `main` `b7e0cfef` no `nightly-failure` issue is open, no PR is open, `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패` (RA-0056 is `미확인`), and no P2-15 preparation is pending. So the next P3 item in listed order is P3-3. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs and what this task does without them (D27 ⑥).** Unanswered: HQ-0090 (O3, whether `unit` becomes an open list with `cycles`), HQ-0091 (O4: ① the oracle and tolerance at `virtual_npu`, ② a data type the CPU lacks), HQ-0088 and HQ-0089 (candidate kinds; not touched here), HQ-0081 (S6; not touched). The "[막히지 않는 것]" lines of HQ-0090 and HQ-0091 name what goes ahead: the target entry, the backend, the flags, the memory bound, coverage per target, `sim.run` and `board.run` below the instance start, and `Target.unit` read with `ns`. This task does exactly that part and nothing that anticipates an answer: no unit other than `ns`, no `cycles` factor, no new `dtype`, no `correctness.check` offered at `virtual_npu`, `instance_start` false.

**PLAN P3-3 stays unchecked after this task.** ADR-0193 decision 8: "The item is not checked before O3 and O4 are answered; an answer that defers a difference closes that difference for the check." So the driver does **not** check P3-3 when this task is `DONE`; the remaining parts wait on HQ-0090 and HQ-0091, and P3 items that do not depend on them (P3-4, P3-5) go on (D27 ⑥).

**P2-15 must not change (D27).** `cpu_standin` keeps its behaviour and results everywhere; `virtual_npu` has `model_run` false, so `hilclaw.model_check` and the model-run binding are unaffected.

**D16.** Verification is on the development machine with stub Docker clients (and clang where existing tests already use it). No real `claude`, board, accelerator or API key. That the memory option behaves as stated on a real container is a runtime acceptance item (ADR-0193 decision 4, "Verification"), which the executor writes in `## Result` for the driver to register (DRIVER §8, D22).

## Required Reading

- `PROCESS/DRIVER.md`: §3-5 and §5 (branch `claude/T-0533-<slug>`, the `Task: T-0533` trailer and the PR body's last line, the size cap, the test rules D12, the list-assertion rule D21), §3 "BLOCKED 사유" and "승인된 열린 목록" (D23), §6 D27, §8 (runtime acceptance items, D22).
- `CLAUDE.md`: A-13 code mode, "테스트 규칙", "도구 계층 언어 정책" (state the language and the reason in one line of the commit body and `## Result`), "코멘트 최소화", "개발 드라이버와 런타임의 구분".
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md`: Status; decision 1 (rows lifted by P3-3); decision 3 (the `Target` members and how the table links to the backend table); **decision 4 in full** (the binding text of this task, including its value table and the bullets after it); decision 8, row P3-3; decision 9, O3 and O4 (what not to anticipate); Consequences, "A-13 reading".
- `PROCESS/STATE.json`: the `question` of HQ-0090 and HQ-0091 (their "[막히는 것]" and "[막히지 않는 것]").
- ADRs: `ADR-0016-od18-backend-frame.md` decisions 2 to 4 (`no_backend`, `not_offered`, selection by `accelerator`); `ADR-0035-od4-cpu-standin-hw-key-values.md` decisions 2 to 5 and 8; `ADR-0144-od14-first-case-build-run-container.md` (the container path; its Q7 on resource bounds); `ADR-0052-od13-memory-ceiling-measurement.md` (what a bound changes in `memory_bytes`); `ADR-0063-od18-run-tools-result-members.md` decision 7 and `ADR-0053-od8-instance-record-objective.md` decision 4 (`memory_ceiling` not admitted); `ADR-0041-od18-correctness-check-dimensions.md` decision 5 and `ADR-0177-od18-od6-contract-table.md` decisions 1 to 3 (the coverage predicates); `ADR-0183-od18-tool-result-format-v2.md` decision 4 (`unit`); `ADR-0117-od14-cpu-standin-time-limits.md` decisions 2 to 4.
- Code: `hilclaw/targets.py` (whole); `hilclaw/contract_table.py` lines 1-150; `hilclaw/check_definition.py` lines 1-60 and 120-200; `hilclaw/run_definition.py` lines 1-60 and 180-225; `hilclaw/run_tool.py` lines 1-60 and 150-312; `hilclaw/check_tool.py` lines 150-223; `hilclaw/run_admission.py` lines 100-190 and `hilclaw/check_admission.py` lines 160-230; `hilclaw/standin_container.py` lines 1-60, 94-230 and 340-352; `hilclaw/standin_check.py` lines 186-300 and 477-512; `hilclaw/standin_run.py` lines 1-90 and 152-330; `hilclaw/standin_profile.py` lines 60-220; `hilclaw/run_result.py` lines 80-160; `hilclaw/instance_start.py` lines 100-200; `hilclaw/start_instance.py` (whole); `hilclaw/spec_tool.py` around line 362.
- Tests: `tests/test_targets.py`, `tests/test_contract_table.py`, `tests/test_check_definition.py`, `tests/test_run_definition.py`, `tests/test_run_tool.py`, `tests/test_standin_container.py`, `tests/test_standin_check.py`, `tests/test_standin_run.py`, `tests/test_standin_profile.py` (to see the stub clients and the pinning assertions).

## Acceptance Criteria

1. **The target entry.** `hilclaw/targets.py` gains a second entry `virtual_npu` (a named constant beside `CPU_STANDIN`) with the values of ADR-0193 decision 4: `flags` = `("-std=gnu11", "-O1", "-ffp-contract=off", "-fno-vectorize", "-fno-slp-vectorize")`; `trailing_flags`, `waiter_flags`, `env`, the build time limit and the process time-limit cap equal to `cpu_standin`'s (read from the same `standin_settings.py` constants); `contracts` = the six bf16 keys of `contract_table.TABLE` (not fp32 `gemm`); `memory_limit_bytes` = `268435456`; `unit` = `"ns"`; `model_run` = `False`; `instance_start` = `False`. A test asserts each value. `cpu_standin`'s entry is unchanged.
2. **Consequences of the two booleans, unchanged code paths.** `instance_start_accelerators()` still answers `("cpu_standin",)` (so `start_instance` admits `("mock", "cpu_standin")` and refuses an instance at `virtual_npu` with the existing `OutOfScopeError`), and `model_run_binding.binding_from_runs` refuses a run at `virtual_npu` with `other_target`. Tests show both.
3. **The backend.** `check_definition.default_table` (and so the run tools' table) holds a third `Backend` named `virtual_npu` that offers `sim.run` and `board.run` with the operations built with the `virtual_npu` `Target` (`standin_run.operation_for`), and **no** `correctness.check`: a `correctness.check` call about `virtual_npu` answers `not_offered` (ADR-0016 decision 3; ADR-0193 decision 4). The mock and `cpu_standin` entries and the identity of their operations are unchanged.
4. **The memory bound.** `standin_container.run_in_container` gains a keyword (for example `memory_limit_bytes=None`) that, when not `None`, adds `--memory <n>` and an equal `--memory-swap <n>` before the image; with `None` the argument list is exactly today's. Wrong values are refused before anything is started in the module's existing style (a `bool`, a non-`int`, a value not above 0: `TypeError` or `ValueError` with the attribute `parameter`). The operations built with a `Target` pass its `memory_limit_bytes` to **each process container** (the timing process of `standin_run`, the verification process of `standin_check`) and to no build container. A process ended over the bound (a stub client exiting as an out-of-memory kill would, for example status 137) yields the existing `broken` result with `condition` `exit_status`; no new condition, member or value is introduced, and `memory_ceiling` stays not admitted. The argument lists of every `cpu_standin` container are byte-for-byte unchanged (the existing tests pass with no edit).
5. **Coverage per target.** The coverage predicates of `contract_table` (`covers`, `check_covers`, `run_covers`, `start_covers`) can answer for a given target: a record is covered at a target only when the covering entry's key is in that `Target`'s `contracts`. The executor chooses the seam (for example an optional target argument or a predicate built per target) and wires it where the accelerator is known, at least in the run tools' admission, so that `sim.run` and `board.run` about `virtual_npu` refuse an fp32 `gemm` record with the existing `op_signature_not_covered` kind and admit the six bf16 contracts. For `cpu_standin` and the mock every predicate answers as today for every record (tests assert this over the seven keys). Where a call site does not know the accelerator (for example `spec.write`), it keeps today's record-only answer; the executor names each such site in `## Result`.
6. **The unit is read from the target.** Where `run_tool` builds a result it takes `unit` from the accelerator's `Target` (`"ns"` for both entries), and for an accelerator with no `Target` (the mock) keeps `"ns"`. `run_result.UNITS`, `timings_tool`'s check of `unit`, and every `step` value stay unchanged.
7. **The hw key of `virtual_npu`.** The hw_profile record of `virtual_npu` can be built on the local machine with `accelerator` `virtual_npu`, `revision` `virtual-1`, `toolchain` and `host` read by the rules of `cpu_standin` (ADR-0035, ADR-0186), and `hw_source` the caller's (ADR-0035 decision 8), for example through an argument of `standin_profile.local_record` or a sibling function. `cpu_standin`'s record is unchanged. Tests use the module's existing stubs for the machine facts.
8. **Below the start, end to end with stubs.** At least one test calls the `sim.run` operation of the `virtual_npu` backend with a bf16 contract and a stub Docker client and shows: the build container gets the `virtual_npu` flags (no `-fopenmp`, `-O1`, the two `-fno-*` flags); the timing process container gets `--memory 268435456 --memory-swap 268435456`; the result carries `unit` `"ns"`.
9. **Existing tests pass unchanged**, apart from assertions that pin a list of public names, imports, fields or binders (DRIVER §5, D21). Pinning assertions this task is expected to touch: in `tests/test_targets.py`, any assertion that the table has exactly one entry or enumerates its names; in `tests/test_check_definition.py` and `tests/test_run_definition.py`, assertions that enumerate the backend names of `default_table` (today the mock and `cpu_standin`); in `tests/test_standin_profile.py`, the allow-list of files that may name `standin_profile`; in `tests/test_run_result.py`, the allow-list of modules that import `run_result`, if `run_tool`'s import changes. Each edited assertion is listed in the PR body.
10. **Tests (D12).** Every public function of each touched module is covered; happy, error, branch and negative cases; package line and function coverage stay at or above 80 %. The full suite and `ruff` pass locally, and clang-based tests run where they already run. No new test file is needed unless a new module is added (then one per module).
11. **No frame change.** No file, member, value or version of the data plane changes beyond what ADR-0193 Consequences ("A-13 reading") states is no frame change: `virtual_npu` as a value of the name field `accelerator` and of the backend table, and `virtual-1` as a value of the existing string member `revision`. `run_result.UNITS` is unchanged, no open list of DRIVER §3 gets a value, and no contract-table entry is added. If the work shows that a frame change is needed, stop and return `BLOCKED` with the reason (A-13; DRIVER §8) rather than making it.
12. **Size.** If the change is seen to exceed 600 LOC or 10 files (tests excluded, DRIVER §5), land the target entry, backend, memory bound and coverage (criteria 1 to 5 and 8) and propose the rest as a split in `## Follow-ups`.
13. **`## Result`** states: the seam chosen for criterion 5 and the call sites left record-only; the language line; the edited assertions; and the runtime acceptance item for the driver to register (D22), in Korean, in the form of `PROCESS/RuntimeAcceptance.md`'s other items: on a real container runtime, a `virtual_npu` timing process given `--memory 268435456 --memory-swap 268435456` is bounded as stated, and a kernel that exceeds the bound yields `broken` with `condition` `exit_status` (source `P3-3`, basis task T-0533).

## Out of Scope

- Any unit other than `ns`, a `cycles` factor in `Target`, new `step` values, and changes to `run_result.UNITS` or `timings_tool` (HQ-0090; the small follow-up task after its answer).
- `correctness.check` at `virtual_npu`, `instance_start` true, a new `dtype` or contract-table entry (HQ-0091).
- `model_run` true for `virtual_npu`; any change to `model_forward.c`, `model_forward_run.py`, `model_run_binding` behaviour for `cpu_standin`, or `model_check` (ADR-0193 decision 4, `model_run` row).
- Candidate kinds and their record format (HQ-0088, HQ-0089); `s6_metric._ACCELERATORS` (ADR-0193 decision 1).
- Any edit of `ARCHITECTURE/` (ADR-0193's "Less exact, not edited" list stays as it is) and of PLAN or RuntimeAcceptance (the driver records the RA item).
- A coarse clock or any difference ADR-0193 decision 4 does not list.

## Follow-ups

- On the answer to HQ-0090 (O3): if (a) or (b), a small task (ADR-0193 decision 8, ~150 LOC plus reader changes) for the unit list, the `cycles` factor and the readers; if (c), the unit difference is closed for the P3-3 check with `ns`.
- On the answer to HQ-0091 (O4): `correctness.check` and the instance start at `virtual_npu` under ① (a), or the decision that it is not checked under ① (b); a new type under ② (b) only.
- PLAN P3-3 is checked by the driver only once both answers have been applied (ADR-0193 decision 8).

## Result

**Order check** (D27 ①), on `main` `edcad743` before any code: no open `nightly-failure` issue, no open PR, no `RuntimeAcceptance.md` item with `상태` `실패`, no P2-15 preparation pending. P3-3 was still the next item.

**What landed** (criteria 1 to 11; the PR is the one whose body ends with `Task: T-0533`).

- `hilclaw/targets.py`: the entry `VIRTUAL_NPU` (`"virtual_npu"`, equal to `standin_profile.VIRTUAL_NPU`) with `VIRTUAL_NPU_FLAGS` (`-std=gnu11 -O1 -ffp-contract=off -fno-vectorize -fno-slp-vectorize`); the trailing flags, waiter flags, environment, build limit and process cap read at each read from the same `standin_settings` constants as `cpu_standin`; `contracts` the six bf16 keys; `memory_limit_bytes` `VIRTUAL_NPU_MEMORY_LIMIT_BYTES` = 268435456; `unit` `ns`; `model_run` and `instance_start` false. `cpu_standin` is unchanged, and `instance_start_accelerators()` is still `("cpu_standin",)`.
- `hilclaw/check_definition.py`: `default_table` holds a third backend `virtual_npu` offering `sim.run` and `board.run` with `standin_run.operation_for(<virtual_npu Target>)` and no `correctness.check` (a call answers `not_offered`). The mock and `cpu_standin` entries and the identity of their operations are unchanged.
- `hilclaw/standin_container.py`: `run_in_container(..., memory_limit_bytes=None)`. An `int` above 0 adds `--memory <n> --memory-swap <n>` before the image. A `bool`, a non-`int` or a value not above 0 is refused before any start (`TypeError` or `ValueError`, `parameter` `memory_limit_bytes`). With `None` the argument list is exactly today's.
- `hilclaw/standin_check.py`, `hilclaw/standin_run.py`: `run_container` passes `memory_limit_bytes` through. The operations hand the target's `memory_limit_bytes` to the process container only (the verification process, the timing process), never to a build container. A process ended over the bound is the existing `exit_status` (`broken`), with no new condition, member or value.
- `hilclaw/run_tool.py`: the run's `accelerator` is looked up in `targets.TABLE`. For a target, the predicate handed to `run_admission.admit` is the bound `covers` joined to `contract_table.served_at(record, target)`, and the result's `unit` is `target.unit`. For an accelerator with no target (the mock) it is the bound `covers` itself and `"ns"`. `run_result.UNITS`, `timings_tool` and every `step` are unchanged.
- `hilclaw/standin_profile.py`: `local_record(..., accelerator=ACCELERATOR)`. `VIRTUAL_NPU` gives `revision` `VIRTUAL_NPU_REVISION` = `virtual-1`, with `toolchain`, `host` and `hw_source` by the `cpu_standin` rules. Any other value is refused before the machine is read.
- `hilclaw/run_definition.py`: docstring only (the run tools join the predicate to the run's target).

**Seam of criterion 5.** `contract_table.covers`, `check_covers`, `run_covers` and `start_covers` take an optional `target` (anything with `contracts`, a `Target`): only the entries whose key is in `target.contracts` are asked. So for `cpu_standin`, and without a target, every predicate answers as before (tests over the seven keys). A new public `contract_table.served_at(record, target)` answers the target's part alone, by the record's `kind`, `dtype` and `layout`, without asking any contract's `covers`. `run_tool` uses it so that the bound predicate is still called exactly once per call (an existing test counts those calls). Wired in the run tools' admission (`sim.run`, `board.run`): fp32 `gemm` at `virtual_npu` is `op_signature_not_covered` and the six bf16 contracts are admitted. **Call sites left record-only**:
- `spec.write` (`spec_tool`, `contract_table.covers`);
- `correctness.check` (`check_definition.definition` / `check_tool`, `check_covers`): `virtual_npu` is `not_offered` at backend selection, before coverage is asked;
- the instance start (`start_instance` / `instance_start.prepare`, `start_covers`): `virtual_npu` is refused as out of scope before coverage matters;
- the S6 metric (`s6_metric`, `start_covers`): it admits `cpu_standin` and the mock alone before coverage is asked (ADR-0193 decision 1 leaves its `_ACCELERATORS` without `virtual_npu`).

`model_run_binding` is unchanged and refuses a `virtual_npu` run with `other_target` (`model_run` false).

**Language**: Python. Every touched module is an existing Python module of the 2-layer package; no module was added.

**Edited assertions (D21, pinning lists)**:
- `tests/test_targets.py`: `test_the_table_holds_cpu_standin_alone_and_not_the_mock`, renamed `test_the_table_holds_cpu_standin_and_virtual_npu_and_not_the_mock` (names, length and repr of the table); the parametrize value `"virtual_npu"` of `test_a_name_with_no_target_is_refused`, replaced by `"synthetic_npu"`.
- `tests/test_check_definition.py`: the backend names of `default_table` in `test_default_table_holds_the_mock_and_cpu_standin_offering_the_three_hw_tools` (renamed `test_default_table_holds_the_mock_cpu_standin_and_virtual_npu`) and `test_building_the_default_table_reads_no_image`; `targets` added to the imports of `default_table` in `test_the_module_imports_what_it_names_and_has_its_public_names_only`.
- `tests/test_backend_conformance.py`: the backend names of `default_table` in `test_the_default_table_offers_the_three_tools_and_no_profiler_at_both_entries` (now with `virtual_npu`; the per-entry checks still cover the mock and `cpu_standin`).
- `tests/test_run_tool.py`: `contract_table` and `targets` added to the imports pinned by `test_the_module_imports_and_names`. The test helper `Bench` gained an `accelerator` keyword (default the mock).
- `tests/test_contract_table.py`: `served_at` added to `test_public_names_of_the_module`.
- `tests/test_standin_profile.py`: `VIRTUAL_NPU` and `VIRTUAL_NPU_REVISION` added to `test_public_names_of_the_module`; `accelerator` added to the parameter list of `test_signature_carries_no_machine_fact`. The allow-list of files that may name `standin_profile` needed no change.
- `tests/test_run_result.py`: no change needed (`run_tool`'s import of `run_result` is unchanged).

**Tests added**:
- `test_targets.py`: the `virtual_npu` values and the reads of the shared constants.
- `test_contract_table.py`: the predicates at a target over the seven keys, and `served_at`, with negative targets and invalid records.
- `test_check_definition.py`: the third backend, and `not_offered` for `correctness.check`.
- `test_run_definition.py`, end to end with a stub Docker client for each bf16 contract and each tool at `virtual_npu`: the build flags (no `-fopenmp`), `--memory 268435456 --memory-swap 268435456` on the timing process only, and `unit` `ns`. Also fp32 `gemm` refused, status 137 giving `broken` / `exit_status`, and no bound on any `cpu_standin` container.
- `test_run_tool.py`: the unit read from the target, the predicate join, and errors.
- `test_standin_container.py`: the memory option and its refusals.
- `test_standin_check.py`, `test_standin_run.py`: the bound on the process container alone.
- `test_standin_profile.py`: the hw key.
- `test_start_instance.py`: `virtual_npu` refused with `OutOfScopeError`.
- `test_model_run_binding.py`: `virtual_npu` refused with `other_target`.

**Frame** (criterion 11): no file, member, value or version of the data plane changed beyond the A-13 reading of ADR-0193 (`virtual_npu` as an `accelerator` and backend name, `virtual-1` as a `revision` value). `run_result.UNITS` is unchanged, no open list got a value, and no contract-table entry was added.

**PLAN P3-3 stays unchecked** (ADR-0193 decision 8): HQ-0090 (the unit) and HQ-0091 (the oracle at `virtual_npu`, a new type) remain open.

**Runtime acceptance item for the driver to register (D22)**, 출처 `P3-3` (근거 task T-0533):

  PLAN P3-3. 실제 컨테이너 런타임(Docker)이 있는 런타임 머신에서 두 가지를 확인한다. ① `virtual_npu`의 timing process 컨테이너를 `--memory 268435456 --memory-swap 268435456`으로 시작하면 실제로 그 메모리 한도(스왑 없이 268435456 바이트)에 묶이는지. ② 그 한도를 넘게 메모리를 쓰는 커널을 `sim.run`이나 `board.run`으로 호출하면 결과가 `broken`, `condition` `exit_status`로 끝나는지(새 condition이나 member가 없고, `memory_ceiling`은 계속 허용되지 않음). verification process에 같은 한도를 거는 코드 경로도 있지만, `virtual_npu`는 아직 `correctness.check`를 제공하지 않으므로(HQ-0091) 확인 대상은 timing process뿐이다. 개발 머신에서는 스텁 Docker 클라이언트로만 검증했다(D16).
