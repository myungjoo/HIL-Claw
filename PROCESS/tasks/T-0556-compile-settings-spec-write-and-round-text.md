---
id: T-0556
title: ADR-0198 slice 2b, second half, for PLAN P3-6 — record the request form in a short ADR, let `spec.write` compose and write a version-3 spec on the technique-selector's request in a `compile_settings` run, and change `orchestration/round-manager.md` steps 6 and 8 and `orchestration/agents/technique-selector.md` so that such a round makes no coder call
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, OD-6, OD-23, FR-1, FR-5, "PLAN P3-6", HQ-0088, HQ-0089, ADR-0198]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0199-od32-compile-settings-spec-write-and-round.md
  - hilclaw/spec_tool.py
  - hilclaw/spec_file.py
  - hilclaw/tools.py
  - hilclaw/turn_definition.py
  - orchestration/round-manager.md
  - orchestration/agents/technique-selector.md
  - tests/test_spec_tool.py
  - tests/test_spec_file.py
  - tests/test_turn_definition.py
  - tests/test_caller_check.py
  - tests/test_turn_permissions.py
  - tests/first_run_stubs.py
estimatedSize: {loc: 450, files: 7}
hq: []
---
## Why

**PLAN P3-6** (커널 밖의 후보) makes and evaluates the first candidate kind that is not a C kernel. The PLAN line still carries "오너 확정 필요(OD-32 ①·⑥·⑦)", but the owner answered the questions behind that mark on 2026-11-05 (HQ-0088 "권고대로 (a)×5", HQ-0089 "권고대로 (a)×4"; HQ-0089's `decision` notes that no HQ blocks P3-6 any more), so P3-6 is selectable. **ADR-0198** (T-0552, PR #368) records those answers and orders the code slices 1, 2a, 2b, 3, 4 (decision 9). Landed so far: slice 1 (T-0552, readers and validators), slice 2a (T-0553, PR #369, the start writes `instance.json` version 2), the first half of slice 2b (T-0554, PR #370, the run-level readers read version 2 as version 1; `case.write`, `cases.lookup` and `catalog.read` refuse a run whose kind is not `c_kernel`) and slice 3 (T-0555, PR #371, `correctness.check`, `sim.run` and `board.run` build a version-3 attempt from the named kernel with the candidate's flags and write `build.json`).

This task is the **second half of slice 2b**: row 3 of ADR-0198 decision 8 ("`spec_tool` (`spec.write`) composes and writes a v3 spec on the technique-selector's request in a `compile_settings` run; v2 elsewhere") and decision 3 (the `technique-selector` chooses the flags and has the version-3 spec of `(round, 1, 1)` written **in step 6**; step 8 is not taken, steps 9 to 12 follow on the same tuple). Today nothing writes a version-3 spec outside tests, so a `compile_settings` run cannot pass a round ≥ 1. After this task it can (in a live session, which is a runtime acceptance item handed over by T-0557).

**Why an ADR here (DRIVER §6 D20 ①, §9).** ADR-0198 fixes the spec's form, place and writer but not `spec.write`'s request form for this kind, what the composed version-3 document holds outside `task.build` (`guidance.techniques`, `feedback`), which of `spec.write`'s checks apply to it (the catalog check 7 and the feedback checks 8 to 10 — note that `spec_feedback` refuses a version-3 spec, row 4 of decision 8, so feeding back over a round that holds one would fail), how a request of the wrong form for the run's kind is answered, and the exact round-manager and technique-selector text. Earlier request forms of this tool were ADR decisions (ADR-0138 decision 3, ADR-0151 decision 3), so these choices go into a short new ADR that lands with the code in this PR.

**Batch and split (D20 ③ and ④; D4 file cap).** The planner created T-0556 (this) and T-0557 (slice 4, the landing: CLAUDE.md's "C 커널" wording, the StandardScenarios scenario, the register links and the runtime acceptance item) together. Merging them would touch about 11 non-test files (over the cap of 10), and slice 4 is document mode, so they stay two tasks; T-0557 depends on this one.

**Order (DRIVER §6 D27 ①).** On `main` `3e36f51e`: no open PR, no open `nightly-failure` issue, no item of `PROCESS/RuntimeAcceptance.md` whose `상태` is `실패` (every item is `미확인`, RA-0056 included, so D27 ④ asks nothing yet), no P2-15 preparation pending, and P3-6 is the first unchecked P3 item that is not waiting (P3-11 and P3-12 wait on HQ-0097 (b) and HQ-0096). If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥/⑦).** Do not ask again or anticipate: HQ-0081 (S6 scale), HQ-0083 (fp16), HQ-0085 (gates), HQ-0095 (which execution is which point), HQ-0096 (vendor oracle, LLM-level unit), HQ-0097 (device-unavailable kind, given-code record). The approved frame is exactly HQ-0089's (ADR-0198 "A-13 reading"): no new member, value or version of `instance.json`, the spec, `build.json`, results, `step`, `events.ndjson`, `artifacts.json` or `STATE.json`. If the work seems to need one, that is a frame change (D23): write the question in `## Result` in the DRIVER §8 structure (Korean: 쟁점, 선택지 (a)/(b)/…, 실행자의 권고, 막히는 것/막히지 않는 것), land the rest and return `DONE`.

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5**: branch `claude/T-0556-<slug>`, the `Task: T-0556` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ADR lines counted, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0556/`, removed at the end), §9 (ADR path).
- `ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md`: decisions **2** (round 0's coder attempt `(0, 1, 1)` is the kernel; the selection role names it), **3** (the selection role, step 6, no step 8), **4** (the version-3 spec: `id` names the attempt, ADR-0004's place, the closed `task.build`, `kernel_round` < `id.round`, `output/` empty), 8 (rows 3, 4 and 5), 9, A-13 reading, Boundaries. The "Record format" of `ARCHITECTURE/decisions/ADR-0001-od4-key-schema.md` for the new ADR.
- `ARCHITECTURE/decisions/ADR-0138-od6-first-case-round-zero-spec.md` decisions 2 and 3 and `ADR-0151-od6-first-case-later-round-spec.md` decisions 1 to 3 (today's request form, checks and composed document); `ADR-0132-od23-first-case-selection.md` decisions 2, 4, 6 and 7 (the technique-selector's role, the hypothesis record, step 6); `ADR-0171-od23-first-case-round-techniques-and-coder-delegation.md` decisions 2 to 6 (the `techniques:` line and step 8); `ADR-0172-od23-first-case-round-one-after-coder-call.md` decisions 2 to 7 (steps 9 to 12 and the stop); `ADR-0146-od18-first-case-caller-check-hook.md` decision 3 and `ADR-0139-od18-first-case-turn-session-permissions.md` (a sub-agent's allowed tools come from its agent file's `tools` line); `ADR-0029-od8-spec-file.md` (written form, write-once name).
- Code: `hilclaw/spec_tool.py` (module docstring: request, checks 1 to 12, composed documents; `_checked`, `_admitted`, `_compose`, `_techniques`, `_content`, `_write`), `hilclaw/spec_file.py` (`parse_versioned`, `final_name`, `write` — version 2 only today), `hilclaw/spec.py` (`SETTINGS_SCHEMA_VERSION`, `validate_versioned`, `_settings`), `hilclaw/instance.py` (`parse_kinded`, `candidate_kind_of`, `CANDIDATE_KINDS`), `hilclaw/run_file_tools.py` (`read`, `c_kernel_only`, the `instance.read` result holding `candidate_kind`), `hilclaw/spec_feedback.py` (its refusal of version 3), `hilclaw/coder_call.py` (refuses a version-3 spec), `hilclaw/tools.py` (`registry` docstring about `spec.write`), `hilclaw/turn_definition.py` (module docstring: the round flow and the roster), `hilclaw/caller_check.py` and `hilclaw/turn_permissions.py` (`holder_lists`).
- `orchestration/round-manager.md` "The round steps" (steps 6 to 12 and the stop, lines ~127–247) and "Your run" (lines ~16–65); `orchestration/agents/technique-selector.md` (whole file, 137 lines); `orchestration/agents/coder-driver.md` (for contrast: today's only `spec.write` caller).
- Tests to read before editing: `tests/test_spec_tool.py`, `tests/test_spec_file.py`, `tests/test_turn_definition.py` (`TECHNIQUE_SELECTOR_TOOLS` and the text assertions on both files), `tests/test_caller_check.py`, `tests/test_turn_permissions.py`, `tests/first_run_stubs.py` and `tests/test_first_run_end_to_end.py` (stub sessions that follow the round text).

## Acceptance Criteria

1. **ADR** `ARCHITECTURE/decisions/ADR-0199-od32-compile-settings-spec-write-and-round.md` (the next free number; take the next one if 0199 is taken), in ADR-0001's record format, records only the choices ADR-0198 leaves to this slice, each with a one-line *Why*, and restates nothing ADR-0198 decided (link to it):
   - `spec.write`'s request for a version-3 spec (for example `{"run_id", "round", "candidate": 1, "attempt": 1, "flags": [...]}`), and whether the kernel reference is composed by the tool as `(0, 1, 1)` (ADR-0198 decision 2's rule of the selection role) or given in the request — the planner's suggestion, not binding: the tool composes it, so the selector cannot name a version-3 or missing attempt;
   - what the composed version-3 document holds besides `task.build` (suggestion: every other section composed as for a round ≥ 1 version-2 spec, with an empty `guidance.techniques` and an empty `feedback.attempts` and no `feedback.base`, since no coder reads it and `spec_feedback` refuses a version-3 attempt), and which of checks 1 to 12 apply, in which order;
   - the answer to a request of the other kind's form: a version-2 (techniques) request for a round ≥ 1 of a `compile_settings` run, and a version-3 (flags) request in a `c_kernel` run or for round 0. Prefer existing kinds (`invalid_request`, or the `run_file_unsupported` of `c_kernel_only`); a new kind is allowed only as a name of the tool layer that no data-plane file holds, as the module's existing new kinds are, and the ADR says so;
   - the round-manager and technique-selector text (criterion 4), and the A-13 reading (no frame element beyond HQ-0089's).
   No register (`Requirements.md`, `OpenDecisionProposals.md`, `StandardScenarios.md`) is edited here: T-0557 adds the link of this ADR with the landing. State that in the ADR's Consequences.
2. **`spec.write` composes and writes a version-3 spec** in a `compile_settings` run (`instance.json` version 2) on a request of the ADR's form for a round ≥ 1, `candidate` 1, `attempt` 1: the document is valid by `spec.validate_versioned`, `schema_version` 3, `id` the attempt, `task.build` exactly `candidate_kind` `"compile_settings"`, `flags` (the request's, in order; possibly empty), `kernel_round` 0, `kernel_candidate` 1, `kernel_attempt` 1 (or as the ADR decides), encoded in the written form of ADR-0029 and written once at `coder/…/spec.json` through `hilclaw.spec_file` (extend `final_name`/`write`, or add versioned entries beside them as ADR-0198 decision 8 did for the readers — the executor's choice, stated in the PR body; `parse`, `final_name` and `write` for version 2 keep their behaviour for every existing caller). No `output/` is written. A flag of the wrong form (not a string of 1 to 255 printable ASCII characters) is refused before anything is written.
3. **Everything else of `spec.write` is unchanged**: round 0 of a `compile_settings` run and every round of a `c_kernel` run compose and write the same bytes as today; the existing kinds and their order are kept; the description string of the tool names the new request form and every kind in order (`test_the_description_names_every_kind_in_order` updated accordingly).
4. **Orchestration text** (ADR-0198 decision 3, the new ADR):
   - `orchestration/agents/technique-selector.md`: its `tools` line gains `mcp__hilclaw__spec_write` (nothing else); in a run whose `instance.json` (from `mcp__hilclaw__instance_read`) states `candidate_kind` `compile_settings`, after writing the hypothesis record it chooses the flags and calls `spec.write` once with the request form of the ADR, does not call `catalog_read` or `cases_lookup` (both refuse such a run, T-0554), and reports in one fixed line form the Round-Manager reads (state the line in the ADR); a `c_kernel` run's instructions are unchanged.
   - `orchestration/round-manager.md`: in a `compile_settings` run, step 8 is not taken — after step 7, the Round-Manager goes on to step 9 on the same tuple when the selector's report says the spec was written, and comes to the stop otherwise (no coder call, no repair); the stop paragraph and step 6 say so. The round-0 steps, steps 9 to 12, the closing steps (where `case.write`'s refusal lets the round go on) and every `c_kernel` path are unchanged.
   - Docstrings that describe the flow or the roster (`hilclaw/turn_definition.py`, the `registry` docstring of `hilclaw/tools.py`, `hilclaw/spec_tool.py`) are updated only where this slice makes them untrue, including the `spec_tool.py` sentence ADR-0198 lists as less exact.
5. **Tests** (D12): happy, error, branch and **negative** cases — a version-3 spec written for round 1 and round 2 of a `compile_settings` run with its exact bytes and its validity by `spec_file.parse_versioned`; an empty `flags`; the refusals of criterion 1's third bullet; a flag of the wrong form; a taken name (`spec_exists`); a missing or invalid `instance.json`; round 0 of a `compile_settings` run unchanged (version 2); `c_kernel` runs unchanged byte for byte; a written version-3 spec that `coder.run` still refuses and that `correctness.check` (T-0555) accepts, where an existing test helper makes that cheap. Text tests for the two orchestration files in the style of `tests/test_turn_definition.py`. If `tests/first_run_stubs.py` follows the round text, extend it only as far as needed to keep `tests/test_first_run_end_to_end.py` passing and, if cheap, to add one stub round ≥ 1 of a `compile_settings` run with no coder call. Every public function of touched modules tested; `hilclaw/` line and function coverage stay ≥ 80%.
6. **Existing tests** stay unchanged except: (a) list assertions under D21 — foreseen: `tests/test_turn_definition.py` `TECHNIQUE_SELECTOR_TOOLS`, the technique-selector entries in `tests/test_caller_check.py` and `tests/test_turn_permissions.py` if they pin its list, `tests/test_spec_file.py::test_the_public_names_and_the_call_forms` if a public name is added; (b) text assertions on the two orchestration files whose quoted sentence this task rewrites; (c) `tests/test_spec_tool.py::test_the_description_names_every_kind_in_order`. List every such edit in the PR body.
7. **Unchanged behaviour** otherwise: version-1 runs, nightly, model and vendor paths behave and write exactly as before; the full test suite passes.
8. **Process**: dev-item-address steps, Draft PR (the ADR is in the PR), context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0556`. Record the language (Python, the existing 2nd-layer modules) and the reason in `## Result`, and the runtime acceptance facts this slice adds (if any beyond ADR-0198's item, which T-0557 hands over).

## Out of Scope

- CLAUDE.md's "C 커널" wording, `ARCHITECTURE/Requirements.md` line 11, the StandardScenarios scenario and re-check, the register links of ADR-0199 and the runtime acceptance item (T-0557).
- A kernel from another run; cases, the S6 metric and model runs of a `compile_settings` run; any change to results, `step` values, `events.ndjson`, `artifacts.json`, `STATE.json` or the layout version; quantization settings and vendor-language kernels (not chosen, D27 ①); HQ-0081, HQ-0083, HQ-0085, HQ-0095 to HQ-0097.
- The ADR wording ADR-0198 lists as less exact (a hold line), apart from the `spec_tool.py` docstring of criterion 4.
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

- T-0557 (slice 4, the landing) follows in this batch; PLAN P3-6 is checked after it.

## Result

- **Outcome**: DONE. PR #372 (Draft, then squash-merged; the merge commit is in the driver's wrap-up). Branch `claude/T-0556-compile-settings-spec-write`. One review round, by a context-isolated `dev-reviewer` (opus), verdict Approve with 3 Nits. Two Nits were fixed after the Approve and needed no new round under D20 (wording and citation only): the `tools.registry` docstring now cites ADR-0199 decision 5, and step 8's paragraph reads "only this paragraph of step 8 applies". The third Nit was not taken. It asked that a round ≥ 1 request carrying neither `techniques` nor `flags` get a message naming both members. Doing that would change the exact message that the existing test `test_the_messages_of_the_techniques_member` asserts, and criterion 6 forbids that edit. ADR-0199 decision 4 records that the message is kept.
- **Order check (D27)** on `main` `ed354868`: unchanged from the Why. No open PR, no open `nightly-failure` issue, no `실패` RA item. Unresolved HQs are HQ-0081, HQ-0095, HQ-0096 and HQ-0097; none is crossed.
- **ADR**: `ARCHITECTURE/decisions/ADR-0199-od32-compile-settings-spec-write-and-round.md`. It records:
  - The request `{run_id, round, candidate 1, attempt 1, flags}`. The tool composes the kernel reference `(0, 1, 1)`.
  - The document: the round-0 document with `schema_version` 3 and `task.build`, an empty `guidance.techniques`, an empty `feedback.attempts` and no `feedback.base`.
  - The checks. 1 to 6 apply. A new check 3a holds the form against the kind. 7 to 10 are skipped for `flags`. 11 and 12 go through the versioned entries.
  - `invalid_request` for the other kind's form. No new kind.
  - The selector's report line `spec: written` / `spec: <kind>`, and the Round-Manager text.
  - The A-13 reading: no frame element beyond HQ-0089's.
  - Registers are left to T-0557. No OD status word changes.
- **`spec_file` choice** (criterion 2): new entries `final_name_versioned` and `write_versioned` beside the strict ones. `parse`, `final_name` and `write` are unchanged.
- **Size**: 7 non-test files, about 355 added and 81 removed lines, ADR included. Tests: about 474 added lines.
- **Existing tests changed**, all listed in the PR body:
  - D21 list assertions: `TECHNIQUE_SELECTOR_TOOLS`, the not-held list in `test_the_technique_selector_still_judges_no_pair_and_writes_no_verdicts`, the technique-selector tuple in `test_holder_lists_the_real_definition`, the two technique-selector parametrize lists in `test_caller_check.py`, `test_the_public_names_and_the_call_forms`, and the input-schema `properties` in `test_the_definition_is_bound_to_the_source_and_does_not_call_it`.
  - Criterion 6 (c): `test_the_description_names_every_kind_in_order`.
- **Tests**: local `pytest` and `ruff check`/`ruff format --check` are green. CI on PR #372 is green: Python 3.11 and 3.14, the coverage gate, C, sh and test presence. `hilclaw/` line coverage is 99% locally (`spec_file` 100%, `spec_tool` 94%), and function coverage stays ≥ 80% (CI coverage gate). `tests/first_run_stubs.py` was not extended. It follows the round text in code, not by parsing, and `test_first_run_end_to_end.py` passes unchanged. A stub compile-settings round would need a compile-settings start and a v3 evaluation in the stub harness, which is more than cheap.
- **Language**: Python, because the slice extends the existing layer-2 modules `spec_tool` and `spec_file`.
- **Runtime acceptance**: nothing beyond ADR-0198's item, which T-0557 hands over: a live round ≥ 1 of a `compile_settings` run in which the technique-selector writes the v3 spec, no coder call is made, and evaluation builds round 0's kernel with the flags. That a live selector follows the new section and a live Round-Manager skips step 8 belongs to that item.
- **§9 notice**: posted on issue #5 after the merge.
- **Storage**: temporary files were under `${TMPDIR}/hilclaw-driver/T-0556/` and were removed with `rm -r`. No images and no installs.
- **Follow-ups**: none. T-0557 (slice 4, the landing) follows as planned.
