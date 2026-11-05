---
id: T-0550
title: Land ADR-0196 slice 2 for PLAN P3-3 — the writers of `sim.run`/`board.run` switch to `sim_run_timing_v3`/`board_run_timing_v3` for every target, `virtual_npu` reports `cycles` (its ns × 3), and the remaining readers (`feedback.base`, `model_run_binding`) read both values
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, OD-33, OD-18, FR-10, NFR-6, "PLAN P3-3", HQ-0090]
dependsOn: []
touchesFiles:
  - hilclaw/run_identity.py
  - hilclaw/run_result.py
  - hilclaw/run_tool.py
  - hilclaw/targets.py
  - hilclaw/spec_feedback.py
  - hilclaw/model_run_binding.py
  - hilclaw/harness/timing_finding.py
  - tests/test_run_identity.py
  - tests/test_run_result.py
  - tests/test_run_tool.py
  - tests/test_targets.py
  - tests/test_spec_feedback.py
  - tests/test_model_run_binding.py
  - tests/harness/test_timing_finding.py
  - tests/
estimatedSize: {loc: 250, files: 7}
hq: []
---
## Why

**PLAN P3-3** (virtual NPU) asks for a backend whose measurement unit, among other things, differs from the CPU on purpose. The owner answered the unit question **HQ-0090** with (a)·(가) on 2026-11-05: `unit` of the `sim.run`/`board.run` result becomes the approved open list "측정 단위" of DRIVER §3 (first values `ns`, `cycles`), new `step` values `sim_run_timing_v3`/`board_run_timing_v3` are used **for all targets**, readers read v2 and v3, `cpu_standin` stays `ns`, and the list reaches `intervals` and `resolution` only.

T-0549 (PR #365, `41dbf4bf`) wrote the §9 record **ADR-0196** (`ARCHITECTURE/decisions/ADR-0196-od32-measurement-unit-list-and-run-result-v3.md`) and landed its **slice 1** (the readers accept v3: `run_identity.STEPS`/`UNITS_OF`, `layout.BUILD_LOG_STEPS`, `timings_tool.STEPS_OF` and `units_differ`, `verdicts_tool`, `s6_metric` admitting `ns` only). Its `## Result` and ADR-0196 decision 6 list **slice 2**, which this task lands: the writers move to v3, `virtual_npu` reports `cycles`, and the two readers not yet changed (`spec_feedback._board_median`, `model_run_binding._timed_attempt_without_spec`) read both board values. ADR-0196 has already made every decision this slice needs (decisions 3 to 7); this task adds no decision. The StepValues states (v3 `defined`, v2 `not used`) are already recorded and do not change with slices (ADR-0196 decision 7).

**PLAN P3-3 stays unchecked after this task**: it also needs the follow-up of **HQ-0091** (oracle and instance start at `virtual_npu`, answered ① (a)·② (a) on 2026-11-05), planned as T-0551 after this task. Do not do any of T-0551's work here.

**Order (DRIVER §6 D27 ①).** On `main` `4b67276a`: no `nightly-failure` issue is open, no PR is open, `PROCESS/RuntimeAcceptance.md` has no `실패` item (RA-0056 is `미확인`), no P2-15 preparation is pending, and P3-3 is the first unchecked P3 item not marked "오너 확정 필요". If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑦).** Do not ask again or anticipate: HQ-0081, HQ-0083 (fp16), HQ-0085 (gates), HQ-0093, HQ-0095 (which execution is which point), HQ-0096, HQ-0097 (device-unavailable kind). The memory figure is untouched ((가)). If the work shows a further owner-only part none of these covers, write the question in `## Result` in the DRIVER §8 structure (Korean), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0550-<slug>`, the `Task: T-0550` trailer and the PR body's last line, size (≤ 10 non-test files; 600 changed lines advised), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0550/`, removed with `rm -r` at the end).
  - §3 "승인된 열린 목록" (the "측정 단위" entry).
- `ARCHITECTURE/decisions/ADR-0196-od32-measurement-unit-list-and-run-result-v3.md` — **whole**; especially decision 2 (v3 definition, v2 keeps `ns`), decision 3 (unit on the `Target`; the mock writes `ns`), decision 4 (readers: both values per point, unit rule per line's value, an attempt with both values, the `feedback.base` and `model_run_binding` rows), **decision 5** (factor 3, `VIRTUAL_NPU_CYCLES_PER_NS`, conversion after the ns judgement, `resolution` 0 stays 0, `memory_bytes` not converted, a target with unit `ns` has factor 1 and `Target` checks it), **decision 6 slice 2** and its rule "no writer writes a v3 result before every reader … reads it".
- `PROCESS/tasks/T-0549-measurement-unit-list-and-v3-run-steps.md` `## Result` (the slice-2 file list, the D21 assertions slice 1 touched).
- `ARCHITECTURE/decisions/ADR-0183-od18-tool-result-format-v2.md` decision 4 (the v2 member list, which v3 keeps).
- `ARCHITECTURE/decisions/ADR-0184-od20-first-case-incumbent-base.md` decision 2 and `ARCHITECTURE/decisions/ADR-0189-od31-binding-from-run-incumbents.md` (the two remaining readers).
- `ARCHITECTURE/decisions/ADR-0193-od32-generalization-design.md` decisions 3 and 4 (the `Target` and the virtual NPU table).
- `ARCHITECTURE/StepValues.md` (the four rows as they stand).
- Code: `hilclaw/run_identity.py` (`step_of`, `STEPS`, `UNITS_OF`), `hilclaw/run_result.py` (`UNITS`, the builders), `hilclaw/run_tool.py` (`_UNIT`, `_target_of`, `_result`, where `target.unit` is read), `hilclaw/targets.py` (`Target`, `CPU_STANDIN`, `VIRTUAL_NPU`, module docstring), `hilclaw/spec_feedback.py` (`_board_median`, ~line 200-280), `hilclaw/model_run_binding.py` (`_timed_attempt_without_spec`), `hilclaw/harness/timing_finding.py` (docstrings), `hilclaw/timings_tool.py` (`STEPS_OF`, `timing_problem(result, step=None)`, `units_differ` — read only), `hilclaw/journaled_tool.py` (`stepped_function`, the `steps` it is handed).

## Acceptance Criteria

1. **Writers to v3** (ADR-0196 decisions 2 and 6 slice 2):
   - `run_identity.step_of` returns `sim_run_timing_v3` for `sim.run` and `board_run_timing_v3` for `board.run`; every tool built on it accepts that value (whatever `steps` tuple `journaled_tool` is handed includes it).
   - `run_result` builds a v3 result whose `unit` is one of the v3 value's units (`run_identity.UNITS_OF`), so `ns` and `cycles` are both accepted by the builder; the member list is ADR-0183 decision 4's, `memory_bytes` unchanged. No code path writes a v2 value any more, so no v2 line with another unit can be written.
   - `targets.Target` holds an integer factor beside `unit` (name per ADR-0196 decision 5), checked at construction: an `int` ≥ 1, not a `bool`; a target with `unit` `ns` must have the factor 1 (ValueError otherwise); `unit` is checked against the list ADR-0196 names. `CPU_STANDIN`: `ns`, 1. `VIRTUAL_NPU`: `cycles`, `VIRTUAL_NPU_CYCLES_PER_NS` = 3. The module docstring's "until the owner answers" sentence is replaced by the fact, citing ADR-0196.
   - `run_tool`: after the harness judgement in `ns` (`outcome` and `condition` unchanged), multiplies `resolution` and every entry of `intervals` by the target's factor, in integers, keeping their order; a `resolution` of 0 stays 0; `memory_bytes` is not converted; the result's `unit` is the target's. The mock writes `ns` under the v3 values.
2. **Remaining readers** (ADR-0196 decision 4 table, slice-2 rows):
   - `spec_feedback._board_median` reads the board lines under both `board_run_timing_v2` and `board_run_timing_v3`, calls `timings_tool.timing_problem` with each line's `step`, and gives no `base` when the shown attempts' measurements hold more than one unit; otherwise the medians are computed as today.
   - `model_run_binding._timed_attempt_without_spec` accepts either board value.
   - `hilclaw/harness/timing_finding.py`: docstrings say it reads the four values (no code change unless needed).
3. **One definition per value at this commit**: every reader of slice 1 already reads v3 (verify, do not re-implement); no writer writes a unit other than `ns` under a v2 value.
4. **Tests** (D12: happy, error, branch and negative; every public function of a touched module). At least:
   - `step_of` returns the two v3 values; an unknown tool still raises as before.
   - `run_result` builds a v3 result with `ns` and with `cycles`, and refuses a unit outside the list (negative).
   - `Target` refuses a factor of 0, a negative factor, a `bool`, a non-`int`, and factor ≠ 1 with unit `ns` (negatives); the two entries hold the stated values.
   - `run_tool` at `virtual_npu` (stub Docker client and stub harness output, as existing `run_tool` tests do): `unit` `cycles`, `intervals` and `resolution` ×3, `resolution` 0 stays 0, `memory_bytes` unchanged, `outcome`/`condition` equal to the `ns` judgement; at `cpu_standin` and the mock: `ns`, values unchanged; the written line's `step` is the v3 value; a build-log file is named with the v3 value.
   - `timings.compare` on two v3 `cycles` results of one run gives the same ratio as on their `ns` originals; an end-to-end run-then-compare test at `virtual_npu` with constructed lines if one exists for `cpu_standin`.
   - `feedback.base`: v3 lines read; a mix of v2 and v3 lines in one unit read as one; measurements in two units give no `base`.
   - `model_run_binding`: an attempt timed under the v3 board value is found.
   - `timing_finding` flags a coarse clock on a `cycles` line written by the converted path (ratio unchanged).
   - Coverage of `hilclaw/` stays ≥ 80 % line and function. No Docker, no `claude`, no network.
5. **Existing tests**: tests that assert the **step value a writer writes** (`sim_run_timing_v2`/`board_run_timing_v2` in expected `events.ndjson` lines or build-log names, about 13 test files under `tests/` such as `test_run_tool.py`, `test_backend_conformance.py`, `test_bf16_end_to_end.py`, `test_first_run_end_to_end.py`, `test_qnn_points.py`, `test_spec_tool.py`, `test_s6_metric.py`) change their expectation to the v3 value, since that is the behaviour this slice changes (owner: "모든 대상에"). Tests that construct v2 lines as **input** to a reader keep doing so (readers still read v2). List every changed test file in the PR body with one line on why. D21 list assertions expected to change, only as far as needed: the public-name set and constants of `run_identity`, `run_result.UNITS`, the `Target` field list in `tests/test_targets.py`. No other existing assertion changes.
6. **Size**: about 250 changed non-test lines, 7 non-test files. No document under `ARCHITECTURE/` changes (ADR-0196 and StepValues already hold the record); if the executor finds a register sentence that is now wrong, list it in `## Result` rather than editing.
7. **Language**: Python, as the existing modules (one line in the commit body).
8. `## Result` lists: PR and merge commit, review rounds, the test files changed under criterion 5, any reader found that still assumes `ns` or a v2 value only (with file and line), any runtime acceptance item (for example a `virtual_npu` timing run on a real container now reporting `cycles`) in the RuntimeAcceptance form, and any new owner-only question in the §8 form.

## Out of Scope

- `correctness.check` and instance start at `virtual_npu`, the per-target admission of the check tool and the start (HQ-0091; T-0551).
- Checking PLAN P3-3 (the driver checks it after T-0551).
- Any change to `memory_bytes`, any new member, event kind or layout version; units other than `ns` and `cycles`; per-point units (ADR-0196 decision 3).
- Editing ADR-0196, earlier ADRs, StepValues, Requirements, OpenDecisionProposals, StandardScenarios, or PLAN.
- Any `claude` process, Docker run or vendor tool.

## Follow-ups

- T-0551 (HQ-0091 follow-up: `correctness.check` and instance start at `virtual_npu`) depends on this task.

## Result

- PR: #366 (squash-merged, branch deleted). Merge commit: 62db40bd on main.
- Review: 2 rounds (dev-reviewer, context-isolated). Round 1 asked for changes: tests/test_run_definition.py still expected v2 steps and ns at virtual_npu, so 40 tests failed. Round 2 approved. The one nit after the approval (a docstring rewrap) was fixed without another review (D20).
- CI: all six gates green on the final head ec939731 (Python 3.11/3.14, Coverage gate (hilclaw), C, sh, Test presence). A full local run on head 41c37f4e gave 38915 passed, 2213 skipped.
- Language: Python, as the existing 2nd-layer modules it changes (one line in the commit body).
- Order check (D27 ①): unchanged from the task's statement at start. No open PR, no nightly-failure issue, no `실패` in RuntimeAcceptance.md.
- What landed (ADR-0196 slice 2):
  - run_identity.step_of returns sim_run_timing_v3 / board_run_timing_v3. No writer writes a v2 value any more.
  - run_result.UNITS = run_identity.UNITS_OF of the v3 value (ns, cycles).
  - targets.Target gains the field units_per_ns: an int >= 1, not a bool, and exactly 1 for unit ns. cpu_standin is ns/1; virtual_npu is cycles/VIRTUAL_NPU_CYCLES_PER_NS = 3. The module docstring sentence is replaced and cites ADR-0196.
  - run_tool converts resolution and intervals by the target's factor after the ns judgement. A resolution of 0 stays 0, memory_bytes is not converted, and the mock keeps ns with factor 1.
  - spec_feedback._board_median reads both board values and calls timing_problem with each line's step. There is no base when the measured attempts hold more than one unit.
  - model_run_binding._timed_attempt_without_spec accepts either board value. Both readers take the values from timings_tool.STEPS_OF.
  - timing_finding: docstrings only.
- Slice-1 readers verified, no change: timings_tool (STEPS_OF, units_differ), verdicts_tool, s6_metric, layout.BUILD_LOG_STEPS, timing_finding (via run_identity.STEPS).
- Existing tests changed under criterion 5 (writer expectations v2 -> v3): test_run_tool.py; test_run_definition.py (also cycles x3 at virtual_npu); test_backend_conformance.py; test_bf16_end_to_end.py; test_first_run_end_to_end.py; test_qnn_points.py; test_run_identity.py (the slice-1 test "step_of still returns v2" is inverted).
- New required Target field units_per_ns=1 added to the test helpers in test_clang_adapter.py, test_cuda_adapter.py, test_qnn_adapter.py, test_standin_check.py and test_model_run_binding.py.
- D21 list assertions modified: test_run_result.py (UNITS == ("ns", "cycles"), and the module's import set gains hilclaw.run_identity); test_targets.py (the GOOD field dict gains units_per_ns; virtual_npu holds cycles/3; "cycles" is removed from the cases of a unit outside the list).
- Readers that still assume ns or v2 only: hilclaw/s6_metric.py:168,274 admits ns only — intended (ADR-0196 decision 4), not a defect. timings_tool.timing_problem(step=None) still defaults to the v2 rule, but no caller in hilclaw/ omits step.
- Register sentences now inexact (not edited; ADR-0196 "Less exact" already lists them): ADR-0193 decisions 3 and 4, ADR-0183 decisions 4, 7 and 8, ADR-0184 decision 2, ADR-0189 decision 2, ADR-0194 decisions 4 and 5. No further one was found.
- Interpretation recorded in the commit body: the "more than one unit gives no base" test looks at the attempts verified at both points, the only ones whose medians are compared (a reading of ADR-0196 decision 4's "shown attempts").
- Runtime acceptance item: recorded by the driver as RA-0076.
- PLAN P3-3: not met. It still waits for T-0551 (HQ-0091 follow-up: correctness.check and instance start at virtual_npu).
- New HQ: none.
- Process note: the round-1 reviewer removed the whole task directory ${TMPDIR}/hilclaw-driver/T-0550/ with `rm -r`, including executor files (outside its scope). Nothing needed for the task was lost; the round-2 brief limited the reviewer to its own subdirectory.
- Cleanup: the task directory was removed with `rm -r`. No work images, host installs or leftover paths. The local and remote branch are deleted.
