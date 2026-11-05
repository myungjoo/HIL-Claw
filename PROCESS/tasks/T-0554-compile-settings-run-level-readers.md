---
id: T-0554
title: ADR-0198 slice 2b, first half, for PLAN P3-6 — the run-level readers read `instance.json` version 2 as version 1, and the case, cases and catalog tools refuse a run whose kind is not `c_kernel`
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, OD-32, OD-8, FR-1, FR-10, "PLAN P3-6", HQ-0089, ADR-0198]
dependsOn: [T-0553]
touchesFiles:
  - hilclaw/instance.py
  - hilclaw/run_file_tools.py
  - hilclaw/journaled_tool.py
  - hilclaw/further_turn.py
  - hilclaw/run_commit.py
  - hilclaw/case_tool.py
  - hilclaw/cases_tool.py
  - hilclaw/catalog_tool.py
  - tests/test_instance.py
  - tests/test_run_file_tools.py
  - tests/test_journaled_tool.py
  - tests/test_further_turn.py
  - tests/test_run_commit.py
  - tests/test_case_tool.py
  - tests/test_cases_tool.py
  - tests/test_catalog_tool.py
estimatedSize: {loc: 350, files: 8}
hq: []
---
## Why

**PLAN P3-6** (커널 밖의 후보): the owner's answers HQ-0088 and HQ-0089 (2026-11-05) are recorded in **ADR-0198** (T-0552, PR #368), whose decision 9 orders the code slices 1, 2a, 2b, 3, 4. T-0553 is slice 2a (the start writes `instance.json` version 2 for `compile_settings`). This task is the **first half of slice 2b**: row 2 of ADR-0198 decision 8's reader table ("read v2 as v1 (its members mean the same)") and the column "Slice 2b" for the rows that must still refuse. Slice 2b as a whole (~8 to 10 files plus the `orchestration/` text) exceeds the file cap of DRIVER §5, so the planner split it: the second half (`spec.write` composing a version-3 spec for the `technique-selector`, `orchestration/round-manager.md` steps 6 and 8, `orchestration/agents/technique-selector.md`) is left for a later planner call, together with slice 4.

After this task a `compile_settings` run can pass the entry of a turn (`state.read`, `instance.read`, `run.fresh`, `state.write`), its journaled stamp check, `key.store`, `hypotheses.write`, `budget.check`, `round.end`, `run.commit`, the further-turn finding, and round 0's `spec.write` and `coder.run` (version-2 spec), because these read `instance.json` through the entries changed here. The evaluation tools still refuse it (T-0555).

**Order (DRIVER §6 D27 ①)** as in T-0553's Why: no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md` (RA-0056 `미확인`), P3-6 the first selectable P3 item. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**A gap in the table, read here by its own rule (the planner's reading, to be confirmed by the executor).** Decision 8 names `run_file_tools` in row 2 but not every caller of `hilclaw.run_file_tools.read` for `instance.json`: `budget_check`, `case_tool`, `cases_tool`, `catalog_tool`, `coder_call`, `hypotheses_write_tool`, `key_store_tool`, `round_end_tool`, `spec_tool` and the `instance.read` tool of `run_file_tools` (observed on `main` `3f97caf8`; re-check with `grep -n 'run_file_tools.read(' hilclaw/*.py`). Widening `run_file_tools.read` widens all of them. By the table's rule — the tools of the round's flow read version 2 as version 1, while cases, the S6 metric and model runs of this kind are not P3-6's (row 8, Boundaries "cases, the S6 metric and model runs of a compile-settings run") — `case_tool` (`case.write`) joins `cases_tool` and `catalog_tool` in refusing a run whose kind is not `c_kernel` with its existing `run_file_unsupported` kind (the round-manager's closing step 1 lets the round go on after `case.write` fails), and every other caller above reads version 2. If the executor finds that a caller's treatment is not implied by the table's rule, it states its reading in the PR body and `## Result`; it does not write a new ADR in this task.

**Open HQs (D27 ⑥/⑦).** As in T-0553: do not ask again or anticipate HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0097; a new owner-only part goes to `## Result` in the DRIVER §8 structure (Korean), the rest lands, `DONE`.

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5**: branch `claude/T-0554-<slug>`, the `Task: T-0554` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0554/`, removed at the end).
- `ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md`: decisions 4 (the form of version 2), 7 (layout version 1 for both versions), **8** (the reader table, columns "Slice 2a" and "Slice 2b"; the opt-in entries), 9, Boundaries.
- `ARCHITECTURE/decisions/ADR-0019-od18-unusable-run-kind.md` (the four `run_file_*` kinds), `ADR-0024-od8-instance-record-layout-version.md` and `ADR-0030-od8-layout-stamp-read-order.md` (the stamp read of a journaled tool), `ADR-0124-od23-round-manager-run-file-access.md` (`instance.read`), `ADR-0133-od23-first-case-round-promotion.md` (`case.write`).
- `orchestration/round-manager.md` "The entry of a turn" and "The closing steps of a round" (to confirm which tools a round calls and that a failing `case.write` lets the round go on). No `orchestration/` file is edited.
- Code: `hilclaw/instance.py` (`parse_kinded`, `read_kinded`, `candidate_kind_of`, `layout_version_of`, `_read`), `hilclaw/run_file_tools.py` (`_INSTANCE_FILE`, `read`, the `instance.read` tool), `hilclaw/run_files.py` (`reading`), `hilclaw/journaled_tool.py` (`_function`, the stamp read), `hilclaw/hw_tool.py` (`_carry_out`: its `read` is bound to the strict `instance.read` by `check_tool`/`run_tool`, so the evaluation tools keep refusing version 2 — the "Slice 2b" cell of row 6), `hilclaw/further_turn.py` (the `instance.read` finding), `hilclaw/run_commit.py` (`_keys`, `_stated_keys`), `hilclaw/case_tool.py`, `hilclaw/cases_tool.py`, `hilclaw/catalog_tool.py`, and the other callers of `run_file_tools.read` named in Why (read only).
- Tests of each touched module, in particular the T-0552 cases in `tests/test_instance.py` (`test_the_strict_entries_refuse_version_2_as_another_version` and the kinded-entry tests).

## Acceptance Criteria

1. **Row 2 reads version 2 as version 1**: `run_file_tools.read(..., "instance.json")` (and through it the `instance.read` tool and every caller named in Why except those of criterion 2), the journaled stamp read of `journaled_tool`, `further_turn`'s finding and `run_commit`'s key reads accept an `instance.json` of version 1 or 2 and treat the members of a version-2 file exactly as those of version 1 (the stamp is layout version 1 for both, decision 7). The `instance.read` tool returns the file's document as it does today (a version-2 document therefore holds `candidate_kind`). Version 3 or any other is refused with the existing kinds and messages; a version-1 file holding `candidate_kind`, or a version-2 file holding `c_kernel` or none, is `run_file_invalid` as decision 4 makes it.
2. **Rows that refuse in slice 2b**: `case_tool`, `cases_tool` and `catalog_tool` refuse a run whose kind is not `c_kernel` with `run_file_unsupported` (a message naming the run's `instance.json` and its kind), before anything is created; `case_lookup`, `s6_metric` and `model_run_binding` keep the strict `instance.read` and refuse version 2 as today; `check_tool`, `run_tool` (through `hw_tool`) refuse a version-2 run with `run_file_unsupported` even though the stamp is read (row 6 "Slice 2b"); `coder_call` reads a version-2 run and still refuses a version-3 spec (`spec_file.parse`); `spec_feedback` and `attempt_kernel` are unchanged.
3. **Smallest change, strict entries kept**: `instance.parse`, `validate`, `read`, `layout_version_of` and the `*_of` accessors stay strict (decision 8's choice); the callers switch to the opt-in entries. If a kinded accessor is needed (for example the layout version of a version-1-or-2 file), add it beside the strict one in `hilclaw/instance.py`. Keep the return types the callers already use (for example `run_file_tools.read` still returns an `Instance` for both versions) unless a refusing caller needs the kind; state the choice in the PR body.
4. **Docstrings** of the touched modules say which versions they read and which kind they refuse; the tool descriptions of `case.write`, `cases.*` and `catalog.*` name the refusal only if their description lists kinds today (keep `tests/test_case_tool.py::test_the_description_names_every_kind_in_order` true).
5. **Tests** (D12): happy, error, branch and **negative** cases for each changed caller — a version-2 `compile_settings` run read by row 2's entries as its version-1 twin; the same run refused by `case.write`, the cases and catalog tools, `correctness.check` and `sim.run`/`board.run` (one call each, `run_file_unsupported`, nothing written); version 3 and 0 refused; a version-1 file with `candidate_kind` and a version-2 file with `c_kernel` refused as `run_file_invalid`; a version-1 run unchanged at every entry. Every public function of the touched modules is tested; `hilclaw/` line and function coverage stay ≥ 80%. Existing tests stay unchanged except (a) list assertions under D21 — foreseen: `tests/test_instance.py::test_the_public_names` (a new accessor), `tests/test_journaled_tool.py::test_the_public_names_and_the_signature`, `tests/test_further_turn.py::test_the_public_names`, `tests/test_cases_tool.py::test_public_names_and_documentation`, `tests/test_catalog_tool.py::test_public_names_and_documentation` if a public name or import changes; (b) a test asserting that a row-2 entry refuses a version-2 file — rewrite it to the new rule. List every such edit in the PR body.
6. **Unchanged behaviour**: every version-1 run, tool, nightly and model path behaves and writes exactly as before; nothing writes a version-3 spec or a `build.json`; the full test suite passes.
7. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0554`. Record the language (Python) and the reason in `## Result`.

## Out of Scope

- `spec.write` composing a version-3 spec, the `technique-selector`'s choice of flags, `orchestration/` text (the second half of slice 2b, a later task).
- The evaluation tools reading a version-2 run and building a version-3 attempt; `build.json` writing; `attempt_kernel` following a kernel reference (T-0555).
- CLAUDE.md's "C 커널" wording, the StandardScenarios scenario, the runtime acceptance item (slice 4). Any `ARCHITECTURE/` edit.
- Cases, the S6 metric and model runs of a `compile_settings` run (ADR-0198 Boundaries).
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

- T-0555 (slice 3) follows in this batch. Then the planner creates the second half of slice 2b and slice 4.

## Result

