---
id: T-0482
title: Bind the `cpu_standin` entry of the default backend table, offering `correctness.check`, `sim.run` and `board.run` with their landed `cpu_standin` operations (ADR-0167 decision 3 and Boundaries; ADR-0070 decision 3; ADR-0130), and add a backend conformance test that runs the three tools through the registry over the mock and over `cpu_standin` with a stub container client
phase: P1
status: IN_PROGRESS
commitMode: code
coversReq: [FR-10, OD-18, "#5 D12", "PLAN P1-1"]
dependsOn: [T-0481]
touchesFiles: [hilclaw/check_definition.py, hilclaw/tools.py, hilclaw/run_definition.py, hilclaw/standin_check.py, hilclaw/standin_run.py, tests/test_check_definition.py, tests/test_run_definition.py, tests/test_run_tool.py, tests/test_tools.py, tests/test_mcp_front.py, tests/test_backend_conformance.py]
estimatedSize: {loc: 150, files: 5}   # tests excluded from the cap (DRIVER §5, D4/D20); the module name of T-0481's operation may differ, see Required Reading
hq: []
---
## Why

PLAN P1-1's completion criterion (D18) is in three parts:
- `sim.run`, `board.run` and `correctness.check` work on `cpu_standin` and on the mock.
- These three tools and `blob.push`/`blob.fetch` are registered as tools and called through the MCP front.
- `profiler.collect` is not required, because HQ-0025's answer (a) is that `cpu_standin` does not offer it (ADR-0130).

Where things stand:
- The registration and the MCP front are on `main` (ADR-0070, ADR-0167; `hilclaw/mcp_front.py`).
- The `cpu_standin` operation of `correctness.check` is on `main` (`hilclaw/standin_check.py`, T-0480).
- T-0481 lands the operation of `sim.run` and `board.run` (`hilclaw/standin_run.py` unless T-0481's Result names another module).
- The default table still holds only the mock. So a call about a run whose hw_profile names `cpu_standin` is answered `no_backend` (ADR-0167 decision 3; ADR-0070 decision 3).

ADR-0167 decision 3 leaves "when the entry is added … to the record or task that adds such an operation". ADR-0070 decision 3 holds no entry "until the operation of `cpu_standin` for this tool exists in the source". Both operations exist once T-0481 lands, so this task adds the entry. No record leaves a design choice open here, so no ADR is expected. If you find one, stop and return BLOCKED with the reason; do not write an ADR beyond this task's scope.

PLAN P1-1 also names "백엔드 적합성 테스트" (backend conformance test). No test today runs the same contract over both entries of the default table. This task adds one. After it lands, the driver checks P1-1 against its criterion.

This is checklist work (PLAN P1-1), not a D18 deferral. No owner-only decision is involved.

## Required Reading

Line numbers are those of `main` at `f3c68add`; the text wins. Read Python with `PYTHONIOENCODING=utf-8`.

- **PROCESS/DRIVER.md §3-5** (line 72: executor procedure, landed check, resume rule, time limit) and **§5** (lines 86-115: task format, naming, size cap D4/D20, trailers, the test rules D12).
- CLAUDE.md, the whole file. Above all read "개발 드라이버와 런타임의 구분" (no container runtime, `clang` or `claude` is started on this machine; tests use stubs), "테스트 규칙", "브랜치·merge 절차" (code mode) and "코멘트 최소화".
- .claude/skills/dev-item-address/SKILL.md (code mode); .claude/skills/dev-code-review/SKILL.md.
- `PROCESS/tasks/T-0481-adr-standin-run-operation.md` `## Result`: the module, the callable(s) and the ADR T-0481 landed. Read that ADR's Consequences for anything it says about this entry.
- **Records**:
  - ARCHITECTURE/decisions/ADR-0167-od18-run-tools-registration.md decision 3 (lines 46-52) and Boundaries (111-120).
  - ARCHITECTURE/decisions/ADR-0070-od18-correctness-check-registration.md decision 3 (lines 48-60).
  - ARCHITECTURE/decisions/ADR-0016-od18-backend-frame.md decisions 2-4 (lines 30-66).
  - ARCHITECTURE/decisions/ADR-0038-od18-cpu-standin-execution-points.md decision 2 (lines 33-41).
  - ARCHITECTURE/decisions/ADR-0130-od18-cpu-standin-profiler-collect.md decisions (lines 23-40): the entry holds no `profiler.collect` operation.
  - ARCHITECTURE/decisions/ADR-0168-od18-standin-container-situations.md decision 2 rows C1 and C3 (lines 40-46): on a machine with no image named or no container client, the tools answer `compiler_unavailable` / `executable_unstartable`, no longer `no_backend`.
- **Code (whole)**: `hilclaw/check_definition.py` (`default_table` and the module docstring), `hilclaw/run_definition.py`, `hilclaw/tools.py` (`default_registry`, from line 182, and its docstring), `hilclaw/backends.py` (`Backend`, `BackendTable`, `select`), `hilclaw/standin_profile.py` (`ACCELERATOR`), `hilclaw/standin_check.py`, T-0481's module, `hilclaw/mock_check.py`, `hilclaw/mock_run.py` and `hilclaw/mcp_front.py`.
- **Tests (whole)**: `tests/test_check_definition.py`, above all:
  - `test_default_table_holds_the_mock_offering_the_three_hw_tools_of_the_registry` (line 342);
  - `test_a_call_about_a_run_at_another_accelerator_is_no_backend` (line 499, parametrized with `cpu_standin`);
  - `test_no_environment_variable_chooses_the_table_or_the_seeds` (line 543);
  - the fixtures that make a run at `cpu_standin`.

  Also read `tests/test_run_definition.py` (lines 837-900), `tests/test_run_tool.py` (around line 616), `tests/test_tools.py`, `tests/test_mcp_front.py` (`test_mcp_names_is_the_table_of_the_registry`, line 193), and `tests/test_standin_check.py` and T-0481's test file for how the container step and the numeric user are stubbed.

## Acceptance Criteria

1. **The entry.** `check_definition.default_table()` returns a table with two entries:
   - the mock, as today;
   - one `hilclaw.backends.Backend` named `hilclaw.standin_profile.ACCELERATOR` (`"cpu_standin"`). It offers `correctness.check` with `standin_check.operation` and `sim.run`/`board.run` with T-0481's operations, and no other tool. In particular it offers no `profiler.collect` (ADR-0130).

   Keep the module's lazy-import rule: importing `check_definition` or building a definition imports none of the `standin_*` modules or NumPy, and the table imports them when it is built. The table is still built in the source, with no option or environment variable choosing it (ADR-0016 decisions 2 and 4). `HILCLAW_STANDIN_IMAGE` is read by the operation at the call (`standin_image`), not when the table is built. Both run tools' tool functions and the check's still use one table per registry, as today.
2. **Docstrings that this change makes false are corrected, and no others:**
   - `check_definition` (module and `default_table`: "It holds no `cpu_standin` entry, so a call about any other `accelerator` is `no_backend`");
   - `tools.default_registry` ("it has no `cpu_standin` entry");
   - `run_definition` if it says the same;
   - the sentence of `standin_check.py` that it "is bound to no backend table", and the same sentence in T-0481's module.

   Docstrings of other `standin_*` modules that say "nothing calls it yet" are listed as less exact by ADR-0168/ADR-0169 and stay as they are. Earlier ADRs are not edited.
3. **Tests that pinned the old table are updated, not deleted.** A call about a run at `cpu_standin` is no longer `no_backend`. Keep the `no_backend` case for another accelerator (`acc_b`). Show that a call about a `cpu_standin` run reaches the `cpu_standin` operation, and that without `HILCLAW_STANDIN_IMAGE` it answers `compiler_unavailable` (C1) with no container started.
4. **Backend conformance test**, new `tests/test_backend_conformance.py`. Over both entries of the default table (mock and `cpu_standin`), it calls `correctness.check`, `sim.run` and `board.run` through `tools.default_registry` and through the MCP front's call path (`hilclaw.mcp_front`, as `tests/test_mcp_front.py` drives it) for a run at that accelerator. Set the stub container client so that `cpu_standin` builds, runs and reports as a passing kernel would. Assert the same contract on both entries:
   - the end line and result members of each tool;
   - the result form;
   - an answer from a tool failure;
   - a repeated call with the same identity is answered from the log.

   Never start a real `docker`, `clang` or `claude` (D16). The tests pass on every platform the CI and the development machine run.
   - **Negative** cases: a `cpu_standin` call with no image named (C1); a stubbed build that fails (`build_exit_status`, a broken result); a client not found (C3). Each answers as ADR-0168 says, at both the check and the run tools.
   - **Branch**: `profiler.collect` is not registered, and a call by that name is refused by the registry (ADR-0130 decision text).
5. Every public function touched keeps its tests. `python -m pytest`, `ruff check .` and `ruff format --check .` pass. The `hilclaw/` coverage gate (line and function >= 80%) and the test-presence check hold.
6. The commit body names the language (Python) and the reason in one line. The PR body ends with `Task: T-0482`. `## Result` states whether P1-1's completion criterion (PLAN P1-1) is now met, item by item, for the driver's checkbox.

## Out of Scope

- Any new ADR or register edit (see Why). `profiler.collect` registration or contract.
- The docstrings of `standin_answer`, `standin_container`, `standin_copies`, `standin_image` and `standin_waiter_line`, which are listed as less exact. Earlier ADRs.
- OpenMP (HQ-0034, deferred), the open parts of ⑲ (나) and ⑱ (마), and the size bounds.
- Starting a real container runtime, compiler or `claude` (D16).

## Follow-ups

- Driver: if `## Result` confirms the criterion, check PLAN P1-1 (OD-18's rest stays open, as the item says).

## Result

- **Landed**: PR #296, squash-merged (the squash commit on `main` with trailer `Task: T-0482`) after 1 review round (round 1: Approve with four nits, no must-fix or should-fix). Two nits were fixed after approval without a further round (D20: a docstring line wrapped, `hilclaw.standin_profile` added to `HEAVY` in `tests/test_run_definition.py`). The other two are recorded here (the deviation below and this criterion list). CI was green on the last head.
- **Code**: `hilclaw/check_definition.py` `default_table()` holds the mock, as before, and a `Backend` named `standin_profile.ACCELERATOR` (`"cpu_standin"`) offering `correctness.check` with `standin_check.operation` and `sim.run`/`board.run` with `standin_run.operation`, and no `profiler.collect`. The `standin_*` modules are imported inside `default_table` only. Building the table reads no image (tested). Docstrings corrected: `check_definition` (module and `default_table`), `tools.default_registry`, `standin_check` and `standin_run` ("bound to no backend table"). `run_definition` had no false sentence. No ADR or register edit.
- **Tests**:
  - `tests/test_backend_conformance.py` is new. It covers both entries × three tools × two fronts (`tools.default_registry`, `mcp_front.main`) with a stub container client. Contract: the end line and result members, the result form, a tool failure, a broken result (`build_exit_status`) and repeated calls answered from the log. Negative: C1 (no image), C3 (client not found), and a failed build. Branch: `profiler.collect` is refused by the registry and the MCP front, and the table answers it `not_offered`. The image is read at the call, not when the table is built.
  - `tests/test_check_definition.py` and `tests/test_run_definition.py` keep the `no_backend` case for `acc_b`. They add a test that a `cpu_standin` call reaches its operation and answers `compiler_unavailable` with no container started, both times, with the end line holding the failure. The front fixtures use `acc_b` for their `no_backend` case. The import checks now also watch the `standin_*` modules.
- **Deviation from `touchesFiles`**: `tests/test_standin_profile.py` pinned that only `start_instance.py` names `standin_profile`. It now admits `check_definition.py` using `standin_profile.ACCELERATOR`, and asserts that `check_definition.py` does not use `local_record`. `tests/test_run_tool.py`, `tests/test_tools.py` and `tests/test_mcp_front.py` needed no change: `test_run_tool.py` uses its own table.
- **Checks**: `python -m pytest` (full suite) passed locally, and `ruff check .` and `ruff format --check .` are clean. The CI coverage gate and the test-presence check were green.
- **Language**: Python, the language of the table and of the operations it binds.
- **PLAN P1-1 completion criterion (D18), item by item**:
  1. `sim.run`, `board.run` and `correctness.check` work on `cpu_standin` and on the mock: **met within the driver's reach**. The default table binds both entries. The conformance test runs all three tools over both entries through the registry and the MCP front: a stub container client builds, runs and reports as a passing kernel would. That a real container run passes on a machine with Docker remains runtime acceptance (ADR-0170 (lxxxi), (lxxxii) and the earlier items of ADR-0145/ADR-0169), which is not a driver task (D16).
  2. These three and `blob.push`/`blob.fetch` are registered as tools and called through the MCP front: **met**. All five are in `tools.default_registry`, and `tools/list` of the MCP front lists them. The three HW tools are called through the MCP front in the conformance test, and the blob tools in the existing tests.
  3. `profiler.collect` is not required: **met**. HQ-0025's answer (a) is that `cpu_standin` does not offer it (ADR-0130). The `cpu_standin` entry holds no such operation, and the registry refuses a call by that name.

  The criterion is therefore met. OD-18's rest stays open, as the item says.
- **Follow-ups**: none. Driver: check PLAN P1-1. Record the runtime acceptance items (lxxxi) and (lxxxii) of ADR-0170 as an HQ with reason `runtime-acceptance`, if not done yet, since the entry has now landed.
