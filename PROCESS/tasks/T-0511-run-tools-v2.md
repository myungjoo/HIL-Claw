---
id: T-0511
title: Land ADR-0183 code slice 3 — sim.run / board.run write v2 results under sim_run_timing_v2 / board_run_timing_v2 (contract_key, kind shape, unit "ns", resolution, intervals), run-line readers on the new values
phase: P2
status: BLOCKED
commitMode: code
coversReq: [C-6, FR-9, FR-10, NFR-1, OD-8, OD-13, OD-16, OD-18, OD-31, HQ-0078, "PLAN P2-11", "PLAN P2-14"]
dependsOn: [T-0509, T-0510]
touchesFiles:
  - hilclaw/run_identity.py
  - hilclaw/run_result.py
  - hilclaw/run_tool.py
  - hilclaw/run_admission.py
  - hilclaw/layout.py
  - hilclaw/timings_tool.py
  - hilclaw/verdicts_tool.py
  - hilclaw/harness/timing_finding.py
  - tests/
estimatedSize: {loc: 380, files: 8}   # ADR-0183 decision 9 item 3: "About 350 lines, 8 files"; plus the check-part docstrings of verdicts_tool.py moved here from T-0510; tests excluded from the cap
hq: [HQ-0079]
---
## Why

**State.** ADR-0183 (T-0508, `main` `8b6c7318`) records the owner's answer to HQ-0078: one result format v2 for `correctness.check`, `sim.run` and `board.run`. Its decision 9 **item 3** is this task: "**`sim.run` / `board.run` v2** — `hilclaw/run_identity.py` (the two v2 values), `hilclaw/run_result.py` (the v2 list of decision 4 for any covering entry: `contract_key`, `shape` of the kind, `unit`, `resolution`, `intervals`), `hilclaw/run_tool.py` (the covering entry and dimensions handed to the builder), `hilclaw/run_admission.py` if it does not yet give the covering entry, `hilclaw/layout.py` (the two run values; the two retired ones out), and the run-line readers `hilclaw/timings_tool.py` (the admitted timing result and `shapes_differ` of decision 8), `hilclaw/verdicts_tool.py` and `hilclaw/harness/timing_finding.py`. Only fp32 `gemm` is timed, so the operations and the mock are unchanged. About 350 lines, 8 files." The check-part docstrings of `hilclaw/verdicts_tool.py` (ADR-0183 decision 9 item 2) were moved here from T-0510 to keep that task within 10 files.

**Why P2-14 needs it (PLAN checklist).** After this slice, ADR-0181 decision 8 items 1-4 (the bf16 timing run) can start (ADR-0183 decision 9 item 4; owner order, HQ-0078); they make the bf16 entries `timed`, which the instance start needs for P2-14. P2-11 / P2-14 are checklist items; D18 does not apply. Planned in one batch with T-0509 and T-0510 (D20 ④); ADR-0183 says items 2 and 3 are independent, but both edit `hilclaw/layout.py`, so this task follows T-0510.

**RuntimeAcceptance.** No `실패` item as of `main` `ac8e143c`. ADR-0183 Consequences: none.

**D16.** Tests use the mock backend and the existing stubs (and the existing `clang`-backed `cpu_standin` timing tests where they run); no `claude`, no real Docker daemon, no board.

## Required Reading

- `PROCESS/DRIVER.md` §3-5, §5 (naming `claude/T-0511-<slug>`, `Task: T-0511` trailer in commits and as the last line of the PR body, size cap, D12, D21), §8 (D22).
- `CLAUDE.md` (rules; A-13 code mode, BLOCKED reasons; test rules; language policy; comment minimisation).
- `PROCESS/tasks/T-0509-v2-check-result-builder.md` and `PROCESS/tasks/T-0510-correctness-check-v2.md` `## Result` (how the covering entry and `contract_key` are formed on the check side; the form of `check_standing.STEPS_OF`).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md` — decisions 1 (lines 38-42), 2 (44-57), 4 (82-105), 5 (107-119, the two run lines), 6 (121-125), 7 (127-130), 8 (132-150, rows `timings.compare` and the imprecise-timing finding, and the `shapes_differ` and `unit` bullets), 9 (152-161).
- `ARCHITECTURE/decisions/ADR-0063-od18-run-tools-result-members.md` decisions 2-9 (today's list); `ADR-0062-od18-run-tools-call-identity.md` decision 3; `ADR-0140-od16-first-case-attempt-comparison.md` decision 3 (lines 36-56); `ADR-0103-od13-imprecise-timing-detection.md` decision 3; `ADR-0104-od13-imprecise-timing-mark.md` decisions 3-4.
- Code: `hilclaw/run_identity.py` (89 lines), `hilclaw/run_result.py` (247), `hilclaw/run_tool.py` (296; `_result` at ~274), `hilclaw/run_admission.py` (179; `Admitted` at ~94, `admit`), `hilclaw/layout.py` lines 50-62 and 170-200, `hilclaw/timings_tool.py` (416; admitted-result check ~250-290, `STEP_OF` ~117, `compare` ~330-416), `hilclaw/verdicts_tool.py` lines 1-130 and 280-320, `hilclaw/harness/timing_finding.py` (199), `hilclaw/contract_table.py` (`entry`, `run_covers`, `task_contract`), `hilclaw/harness/timing.py` (the `Judgement` fields `intervals_ns` / `resolution_ns` stay internal to the harness — read only).
- Tests to adapt: `tests/test_run_identity.py` (~137, ~289-295), `tests/test_run_result.py` (~761-770), `tests/test_run_tool.py`, `tests/test_run_admission.py`, `tests/test_layout.py` (~617), `tests/test_timings_tool.py`, `tests/test_verdicts_tool.py`, `tests/harness/test_timing_finding.py`, `tests/test_mock_run.py`, `tests/test_standin_run.py`, `tests/test_run_definition.py`, `tests/test_build_log.py`, `tests/test_backend_conformance.py`, `tests/test_first_run_end_to_end.py` (search `tests/` for `sim_run_timing`, `board_run_timing`, `intervals_ns`, `resolution_ns` in result context).

## Acceptance Criteria

1. **Step values** (ADR-0183 decision 2). `hilclaw.run_identity` binds exactly `sim_run_timing_v2` (`sim.run`) and `board_run_timing_v2` (`board.run`); `STEPS` is those two; `step_of(tool)` gives the value from the tool alone. The constants of `sim_run_timing` / `board_run_timing` are gone (constant names are this slice's). No string of a retired run value remains in `hilclaw/` code.
2. **The v2 result** (decision 4). `hilclaw.run_result` builds, for **any covering entry of `contract_table`** (not only fp32 `gemm`), a result with exactly the members of decision 4 in its table order: `outcome`, `condition` (broken only), `contract_key` (`kind`, `dtype`, `layout` of the entry), `shape` (the `task_contract` parameter names of the kind with the run's dimensions, each `int` ≥ 1), `n_max`, `sample_form`, `unit` (`"ns"`), `resolution`, `intervals`, `memory_bytes` (when a figure was yielded), `ceiling`, `bound` (when `ceiling` is not `"not_stated"`). `unit`, `resolution` and `intervals` are present exactly when `outcome` is `"converged"` or `"not_converged"`; a broken result holds none of `unit`, `resolution`, `intervals`, `memory_bytes`. Types, bounds and the closed value lists of ADR-0063 are unchanged; `unit` admits only `"ns"`. Today's builders (taking `m`, `k`, `n`, `intervals_ns`, `resolution_ns`) are replaced. Refusals keep the module's style (`TypeError` / `ValueError`, message starting with the parameter name).
3. **The tool path.** `hilclaw.run_tool` hands the builder the covering entry and the dimensions in `task_contract` order; `hilclaw.run_admission.Admitted` carries them if it does not already (its field list may change), still admitting only what `run_covers` covers (fp32 `gemm` today); the answers of moment 4 and their order are unchanged. The harness's internal `Judgement.intervals_ns` / `resolution_ns` are mapped onto `intervals` / `resolution`; `hilclaw/harness/timing.py`, the operations (`cpu_standin`, `hilclaw/mock_run.py`) and the report keywords do not change. The build-log file of the timing build is named with the v2 value (decision 7, e.g. `build-log-sim_run_timing_v2-01.txt`).
4. **Build-log names** (decision 7). `hilclaw.layout.BUILD_LOG_STEPS` is exactly the four v2 values (`check_identity.STEPS + run_identity.STEPS`); the two retired run values are no longer admitted by `build_log_file`; its docstring names the four.
5. **`timings.compare`** (decision 8 row and bullets). Reads lines of `sim_run_timing_v2` at `sim` and `board_run_timing_v2` at `board` only (`STEP_OF`). An **admitted timing result** has, for `"converged"` / `"not_converged"`, `intervals` (a list of at least `N_MIN` = 5 `int`s ≥ 1), `unit` exactly `"ns"`, `shape` (an object of at least one member, each an `int` ≥ 1) and `contract_key` (an object of exactly `kind`, `dtype`, `layout`, each a `str`); otherwise `timing_result_invalid` as today. The samples are `intervals`. **`shapes_differ` when the two results' `contract_key` or `shape` differ.** Kinds, request and the rest of the reply are unchanged. `verdicts.write`'s `comparison` entries follow through it.
6. **`verdicts_tool.py`.** Code follows the run constants; its docstrings no longer name the retired check or run values or `intervals_ns` (the check-part docstring edits moved here from T-0510). No change of its request, entries or kinds.
7. **`hilclaw.harness.timing_finding`** reads `outcome`, `resolution` and `intervals` (decision 8 row: names only; it does not read `unit`); its rule, constant and refusals are unchanged.
8. **Untouched**: every check module (T-0510's), `hilclaw/hw_tool.py`, `hilclaw/journaled_tool.py`, `orchestration/` (no prompt change, ADR-0183 decision 8), `hilclaw/contract_table.py` (no `timed` flag changes — ADR-0181's slices).
9. **Tests** (D12: happy, error, branch, negative; every public function of the touched modules covered; coverage ≥ 80 % line and function):
   - end-to-end through the registered tools on the mock **and** `cpu_standin` (where the existing tests run it): `sim.run` and `board.run` append lines under the v2 values with a v2 `result`; the two run lines of ADR-0183 decision 5 reproduced as builder output; a broken run (each condition family: build, process, report, `zero_interval`, `replay`) holds no `unit` / `resolution` / `intervals` / `memory_bytes`;
   - the builder with a covering entry of another kind (e.g. bf16 `rmsnorm` with `{m, n}`) gives that `contract_key` and `shape` (the builder takes any covering entry, ADR-0183 decision 9 item 4), although no tool admits it yet;
   - `timings.compare`: admitted v2 results compared; `unit` other than `"ns"`, missing `contract_key`, `contract_key` with an extra member, `shape` empty → `timing_result_invalid`; two results with equal `shape` `{m, n}` but different `contract_key` → `shapes_differ`; lines under a retired run value are not read;
   - `timing_finding` on v2 results (coarse clock true / false, broken, invalid members);
   - negative: `build_log_file` with a retired run value; `unit` other than `"ns"` refused by the builder.
10. **Existing tests.** Tests that assert a retired run value, `intervals_ns` / `resolution_ns` as result members, or today's run result members are rewritten to v2 — that is this task's change. Beyond that, list assertions touched by changed names may be edited (D21); expected: `tests/test_run_identity.py` (`STEPS == …` ~137, `test_public_names_of_the_module_and_no_default` ~289-295), `tests/test_run_result.py::test_public_names_of_the_module` (~761), `tests/test_run_admission.py` (`Admitted._fields` / public names, if the fields change), `tests/test_layout.py` (`BUILD_LOG_STEPS == …` ~617-618), and public-name assertions of `tests/test_timings_tool.py` / `tests/harness/test_timing_finding.py` if a name changes. No other existing assertion changes; harness tests of `hilclaw.harness.timing` stay as they are. List every edited assertion in the PR body.
11. **No record edits.** No file under `ARCHITECTURE/` changes. Sentences of records that become less exact beyond ADR-0183's Consequences list are named in Result.
12. **Result** records the language (Python) and reason, the files changed (≤ 10 non-test), the `Admitted` fields if changed, the edited list assertions, any runtime acceptance item (none expected), and the planner's next candidate: ADR-0181 decision 8 item 1 (with item 3 reduced as ADR-0183 decision 9 item 4 says).

## Out of Scope

- ADR-0181's bf16 timing slices (bf16 timing programs, run tools for bf16 kinds, `cpu_standin` operation, `timed` flags).
- The open list of units and whether a unit reaches `memory_bytes` (owner, HQ-0078 ⑤); any `n_min`, `cv_max` or other owner-only value.
- `sim.json` / `board.json` / `eval.json` (PLAN P1-8).
- Removing `hw_tool.read_stepped_tool_function` / `journaled_tool.read_stepped_function` (deferred, D18).
- Starting `claude`, a real Docker daemon, a board, real weights or an API key (D16).

## Follow-ups

## Result
