---
id: T-0562
title: Land ADR-0200 slice 3a for PLAN P3-11 — the run-level readers and the three evaluation tools read `instance.json` version 3 (rows 2 to 4 of ADR-0200's reader table), while the readers of row 6 keep refusing it
phase: P3
status: DONE
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

**Outcome**: DONE — PR #376 (code mode), squash-merged as `93fbc119`, branch deleted. Reviewer (context-isolated, opus) Approve in round 1 with 3 nits; nits 1 and 3 were addressed in the PR body after Approve (D20, no code change) and nit 2 is recorded here. CI green on all six gates; local full suite 39652 passed, 2215 skipped, `hilclaw/` line coverage 99% (touched modules 98–100%).

**Order check (D27 ①)**: unchanged at run time (no open PR; #373 still with T-0559; no `실패` item in RuntimeAcceptance.md).

**What landed** (ADR-0200 slice 3a, reader table rows 2 to 4; row 6 still refuses):
- `hilclaw/instance.py`: `layout_version_of_kinded` and `read_as_version_1` fall back to `read_given` and so read versions 1–3. They were widened in place, with no opt-in entry, because their only callers are `journaled_tool` (the stamp of `correctness.check`/`sim.run`/`board.run` via `hw_tool`), `further_turn` and `run_commit`. All of those are rows 2 and 3, so no row-6 caller is widened. No new public name.
- `hilclaw/run_file_tools.py`: `read` parses with `parse_given`, so `instance.read` returns `given_code` as stored. Every round tool that reads through it reads v3: `round.end`, `key.store`, `coder.run`, `hypotheses.write`, the budget hook and `spec.write`. `c_kernel_only` now also refuses a given-code run with `run_file_unsupported`, so row 6 (`case.write`, `cases.read`, `catalog.read`) keeps its existing kind.
- `hilclaw/check_tool.py`, `hilclaw/run_tool.py`: v3 `c_kernel` runs are evaluated from `output/` as C kernel attempts, `(0, 1, 1)` with `given.c` included. A v3 `compile_settings` run is `run_file_unsupported` until slice 5.
- `hilclaw/spec_tool.py`: rounds ≥ 1 of a v3 run are written as for its twin. Round 0 of a given-code run is refused with `invalid_request` at check 3a (ADR-0200 decision 4 (a)).
- Docstrings corrected: `run_file_tools.py`, `journaled_tool.py`, `hw_tool.py`, `further_turn.py`, `run_commit.py`, `instance.py`.
- The real-clang `correctness.check` test (`tests/test_check_tool.py::test_the_given_attempt_of_a_started_run_is_checked_with_the_real_clang`) starts a run with T-0561's start, places `given.c` from the blob, and checks a right and a wrong kernel at `cpu_standin` through a stub docker with the host clang. It ran under WSL Ubuntu (clang 14, libomp extracted user-locally into the task directory) and on CI.

**Deviation from `touchesFiles`** (reviewer nit 2):
- `hilclaw/hw_tool.py` was edited (docstring only, criterion 7); there are 9 non-test files in total.
- `hilclaw/run_admission.py` and `hilclaw/check_admission.py` needed no change, because a v3 read yields the same `Instance` type.
- Test files outside the list were edited: `test_hw_tool`, `test_case_tool`, `test_cases_tool`, `test_catalog_tool`, `test_coder_call`, `test_round_end_tool`, `test_key_store_tool`, `test_budget_check`, `test_hypotheses_write_tool`, `test_turn_start`. In most of them `schema_version` 3 had been the sentinel for "another version" and became 4, because a bare v3 file is now `run_file_invalid`. Some also gained new v3 or row-6 cases.
- Every edit to an existing test is listed in the PR body.

**Commit trailer**: the squash commit's message is the PR body, which ends with `Task: T-0562` but lacks the `Co-Authored-By` line; the branch commit `c7e38aec` had both. This was not repaired, since repairing it would need a force push.

**Less exact, not edited** (outside the file cap):
- The docstrings of `hilclaw/case_tool.py`, `cases_tool.py` and `catalog_tool.py` describe `c_kernel_only` as refusing "a run whose candidate kind is not `c_kernel`". It now also refuses a given-code run.
- ADR-0198 decision 8 and ADR-0200 decision 7, slice-1 column: they say `layout_version_of_kinded` and `read_as_version_1` read versions 1 and 2. They now read versions 1 to 3, as column 3a requires.

**Observation for the planner (slice 3b/4, not an HQ)**: `spec_feedback` ignores an attempt directory without `spec.json`. So the given attempt `(0, 1, 1)` of a given-code run never appears in the `feedback.attempts` of a round ≥ 1 spec, and it can never be `feedback.base`, the incumbent of ADR-0184. ADR-0200 decision 4 (a) says ADR-0119's baseline rule applies to the given attempt and that rounds ≥ 1 are unchanged. Whether round-1 feedback should show the given attempt is not settled by ADR-0200. Slice 3b or 4 should look at it; if that needs a decision of form, it is §9 or an HQ.

**Runtime acceptance items**: none from this slice (ADR-0200 Consequences: slice 3b hands one over).

**HQ**: none.

**Storage**:
- `%TMP%/hilclaw-driver/T-0562/` and WSL `/tmp/hilclaw-driver/T-0562/` (the user-local libomp extract) were removed with `rm -r`.
- The empty WSL `/tmp/hilclaw-driver` was also removed with `rmdir`; whether this task created it is not known.
- No images were made and nothing was installed. The existing WSL venv `~/.venvs/hilclaw-driver` was used as it was.
- No `claude` process was started and no test run was made (D25).
