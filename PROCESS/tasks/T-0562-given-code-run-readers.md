---
id: T-0562
title: Land ADR-0200 slice 3a for PLAN P3-11 — the run-level readers and the three evaluation tools read `instance.json` version 3 (rows 2 to 4 of ADR-0200's reader table), while the readers of row 6 keep refusing it
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, FR-19, OD-33, "PLAN P3-11", HQ-0097, ADR-0200]
dependsOn: [T-0561]
touchesFiles:
  - hilclaw/instance.py
  - hilclaw/journaled_tool.py
  - hilclaw/run_file_tools.py
  - hilclaw/run_commit.py
  - hilclaw/further_turn.py
  - hilclaw/run_admission.py
  - hilclaw/check_admission.py
  - hilclaw/check_tool.py
  - hilclaw/run_tool.py
  - hilclaw/spec_tool.py
  - tests/test_instance.py
  - tests/test_journaled_tool.py
  - tests/test_run_file_tools.py
  - tests/test_run_commit.py
  - tests/test_further_turn.py
  - tests/test_run_admission.py
  - tests/test_check_admission.py
  - tests/test_check_tool.py
  - tests/test_run_tool.py
  - tests/test_spec_tool.py
estimatedSize: {loc: 400, files: 10}
hq: []
---
## Why

**PLAN P3-11** continues with **ADR-0200 slice 3a** (decision 8: "Run-level readers and the three evaluation tools read v3 (table rows 2 to 4)", ~400 LOC, 8–10 files). Slice 1 (T-0560) gave `hilclaw.instance` the opt-in version-3 entries (`parse_given`, `validate_given`, `read_given`, `given_code_of`) and left every caller refusing version 3; slice 2 (T-0561, the batch predecessor) makes the start write version 3. ADR-0200 decision 8 says 3a depends only on slice 1; it is ordered after slice 2 (decision 8: "The order is 1, 2, 3a, 3b, 4") so tests can use a real started version-3 run.

**Order and brake**: as in T-0561's Why (D27 ①, D31 ① and ②: PLAN P3-11 work, the PLAN-item exception to the E4 brake). If the order has changed when the task runs (a new `nightly-failure` issue without a task, an RA `실패` item, an open PR touching these files), report it in `## Result` and stop before writing code.

**No new decision.** ADR-0200 decision 7's reader table fixes what each caller does. Open HQs not to be anticipated or asked: HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0100. An owner-only part found during the work goes into `## Result` in the DRIVER §8 structure (Korean), the rest lands, `DONE` (D27 ⑥).

**Size**: at the file cap (10 non-test files) by estimate. The callers listed in `touchesFiles` are the ones that read `instance.json` through `hilclaw.instance` entries today (`layout_version_of_kinded`, `parse_kinded`, `read_kinded`, `read_as_version_1`, and the `instances.Instance` type checks of `run_admission`/`check_admission`); others of rows 2 to 4 (`hw_tool`, `round_end_tool`, `key_store_tool`, `run_objective`, `tools`, `coder_call`, `spec_feedback`) are expected to follow through them without an edit. If more than 10 non-test files must change, finish rows 2 and 3 and propose the rest as a split in `Follow-ups` (DRIVER §5).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0562-<slug>`, the `Task: T-0562` trailer and the PR body's last line, size (D30), tests (D12), list assertions (D21), storage (D29: `${TMPDIR:-/tmp}/hilclaw-driver/T-0562/`, removed at the end).
  - §3 "BLOCKED 사유"; §6 D27 (⑥), D31 ②; §9.
- `PROCESS/tasks/T-0560-given-code-evaluation-design-and-instance-v3-readers.md` and `PROCESS/tasks/T-0561-given-code-instance-start.md` (`## Result` of each).
- **`ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md`**: decisions 4 (a) (round 0 of a given-code run: attempt `(0, 1, 1)`, no spec, no coder call, no repair; rounds ≥ 1 unchanged), 6 (form of version 3; layout version 1), **7 (the reader table, column "3a")** and 8.
- `ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md` decisions 7 and 8 (how version 2 was taught to the same callers — the model to follow).
- Code: `hilclaw/instance.py` (all version entries and accessors, `read_as_version_1`, `layout_version_of_kinded`), the files in `touchesFiles`, and the row-6 callers that must keep refusing: `hilclaw/attempt_kernel.py`, `model_run_binding.py`, `case_lookup.py`, `cases_tool.py`, `catalog_tool.py`, `s6_metric.py`. Find every caller with a search for `instance.` and `instances.` in `hilclaw/`.

## Acceptance Criteria

1. **Rows 2 and 3 read version 3 as its version-1 twin** (ADR-0200 decision 7): `journaled_tool` (the layout read), `hw_tool`, `run_file_tools` (`instance.read`, `state.read`), `round_end_tool`, `key_store_tool`, `run_admission`, `run_objective`, `run_commit`, `further_turn` and `tools` accept a run whose `instance.json` is version 3; its other members mean what they mean at version 1. `instance.read` of `run_file_tools` returns the members as stored, so `given_code` is visible to the Round-Manager.
2. **Row 3, the evaluation tools**: `check_admission`, `check_tool` (`correctness.check`) and `run_tool` (`sim.run`, `board.run`) accept a version-3 run of kind `c_kernel` and evaluate an attempt from its `output/` as a C kernel attempt, so `(0, 1, 1)` holding `given.c` is built and checked like a coder attempt. A version-3 file whose `candidate_kind` is `compile_settings` is refused as unsupported by these tools until ADR-0200 slice 5 (the start of T-0561 never writes one).
3. **Row 4**: `spec_tool` (and through it `coder_call`, `spec_feedback`) reads version 3 for rounds ≥ 1. For round 0 of a version-3 run, where ADR-0200 decision 4 (a) says no spec and no coder call is made, refuse a spec write for `(0, 1, 1)` with an existing error kind if that is natural here, or leave it to slice 3b (T-0563); state the choice in the PR body.
4. **Row 6 keeps refusing version 3** with its existing kind: `attempt_kernel`, `model_run_binding`, `case_lookup`, `cases_tool`, `catalog_tool`, `s6_metric` (and `case.write`'s failure lets the round go on, as ADR-0200 says). If widening a shared accessor of `hilclaw/instance.py` (for example `read_as_version_1` or `layout_version_of_kinded`) would widen a row-6 caller, use an opt-in entry instead; state the choice in the PR body.
5. **Versions 1 and 2 unchanged**: every caller reads them exactly as before; the full test suite passes; no writer changes.
6. **Tests** (D12): for each touched caller, a version-3 run (started by T-0561's start, or a written fixture where the start is not usable) is accepted where the table says so and refused where it does not; happy, error, branch and **negative** cases (version 3 with a malformed `given_code`, `compile_settings` at version 3 at the evaluation tools, version 4); a row-6 caller refusing version 3. The given attempt at `cpu_standin` is checked with the real clang (D29; present on the machine and in CI) in at least one `correctness.check` test. Every public function of touched modules tested; `hilclaw/` line and function coverage ≥ 80%. Existing tests unchanged except list assertions under D21 (foreseen: `tests/test_instance.py::test_the_public_names` if `hilclaw/instance.py` gains a name) and tests that pin "version 3 is refused" at an entry the table now opens, rewritten to the new rule. List every such edit in the PR body.
7. **Docstrings** of touched modules that name "versions 1 and 2" only are corrected (ADR-0200 Consequences lists `run_file_tools.py`'s).
8. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0562`. Record the language choice (Python) in the commit body.

## Out of Scope

- Slice 3b (placement of `(0, 1, 1)`, `orchestration/round-manager.md`), slice 4 (`hilclaw.given_eval`), slice 5 (`compile_settings` with given code).
- Cases, the S6 metric and model runs of a given-code run (row 6; FR-18).
- Vendor targets, HQ-0095, HQ-0096, `device_unavailable`. No `ARCHITECTURE/` edits.
- Starting `claude` in any form (D16); no test run (D25).

## Follow-ups

- T-0563 (slice 3b) follows in this batch.

## Result
