---
id: T-0553
title: ADR-0198 slice 2a for PLAN P3-6 — let the instance start take `candidate_kind` and write `instance.json` version 2 for a `compile_settings` run, version 1 otherwise
phase: P3
status: DONE
commitMode: code
coversReq: [D27, OD-32, OD-8, FR-1, "PLAN P3-6", HQ-0088, HQ-0089, ADR-0198]
dependsOn: []
touchesFiles:
  - hilclaw/instance_start.py
  - hilclaw/start_instance.py
  - hilclaw/instance_file.py
  - hilclaw/new_run.py
  - tests/test_instance_start.py
  - tests/test_start_instance.py
  - tests/test_instance_file.py
  - tests/test_new_run.py
estimatedSize: {loc: 300, files: 4}
hq: []
---
## Why

**PLAN P3-6** (커널 밖의 후보) makes and evaluates the first candidate kind that is not a C kernel. The PLAN line still carries "오너 확정 필요(OD-32 ①·⑥·⑦)", but the owner answered both questions that mark referred to on 2026-11-05 (HQ-0088 "권고대로 (a)×5", HQ-0089 "권고대로 (a)×4"; HQ-0089's `decision` notes that no HQ blocks P3-6 any more). T-0552 (PR #368, `main` `f648837a`) landed **ADR-0198** with its first code slice (validators and readers of `instance.json` v2, spec v3 and `measure/…/build.json` v1, every existing caller kept strict). ADR-0198 decision 9 lists the remaining slices in the order 1, 2a, 2b, 3, 4. This task is **slice 2a**: the start takes `candidate_kind` (decision 7).

**Order (DRIVER §6 D27 ①).** On `main` `3f97caf8`: no open PR, no open `nightly-failure` issue, no item of `PROCESS/RuntimeAcceptance.md` whose `상태` is `실패` (RA-0056 is `미확인`, so D27 ④ asks nothing yet), no P2-15 preparation pending, and P3-6 is the first unchecked P3 item that is not waiting (P3-11 and P3-12 wait on HQ-0097 and HQ-0096). If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Batch.** The planner created T-0553 (slice 2a), T-0554 (the run-level readers of slice 2b) and T-0555 (slice 3) together (D20 ④). Slice 2b is split because its files exceed the cap of DRIVER §5 (≤ 10 files); its other half (the `spec.write` path for a version-3 spec and the `orchestration/` text) is left with slice 4 for a later planner call. Slice 2a stays alone: merged with the readers of T-0554 it would touch about 12 files.

**Open HQs (D27 ⑥/⑦).** Do not ask again or anticipate HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0097. If the work shows an owner-only part none of these covers (in particular a frame element HQ-0089 did not approve), write the question in `## Result` in the DRIVER §8 structure (Korean: 쟁점, 선택지 (a)/(b)/…, 실행자의 권고, 막히는 것/막히지 않는 것), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md` **§3-5 and §5**: branch `claude/T-0553-<slug>`, the `Task: T-0553` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0553/`, removed at the end). §3 "BLOCKED 사유" and "승인된 열린 목록" (the "후보 종류" entry).
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0088** and **HQ-0089** (question and `decision`).
- `ARCHITECTURE/decisions/ADR-0198-od32-compile-settings-candidate-kind.md` — all of it; in particular decision 4 (the form of `instance.json` version 2: `candidate_kind` required, no `c_kernel` at version 2, no `candidate_kind` at version 1), **decision 7** (the start; layout version 1), decision 8 (the reader table: row 1 for this slice; rows 2 to 8 stay as "Slice 2a" says) and decision 9.
- `ARCHITECTURE/decisions/ADR-0076-od8-instance-start-required-members.md` (the required set, decision 4: undefined members carried over as given), `ADR-0115-od8-instance-start-performer.md`, `ADR-0111-od8-run-under-given-id.md` (given id), `ADR-0109-od8-instance-start-name-taken.md` (taken name), `ADR-0025-od8-instance-file-write.md` (the instance file write), `ADR-0155-od23-first-case-instance-start-command-line.md` (the command-line entry `new_run`), `ADR-0197-od32-virtual-npu-oracle-and-instance-start.md` decision 1 (the accelerators of the start).
- Code: `hilclaw/instance.py` (`SCHEMA_VERSION`, `KIND_SCHEMA_VERSION`, `CANDIDATE_KINDS`, `Kinded`, `parse`, `parse_kinded`, `validate`, `validate_kinded`, `_checked`, `_candidate_kind`), `hilclaw/instance_start.py` (`prepare`, `REPORT_ORDER`), `hilclaw/start_instance.py` (`start`, `_covers_of`), `hilclaw/instance_file.py` (`write`), `hilclaw/new_run.py` (`_started` and its outcomes), `hilclaw/targets.py` (`instance_start_accelerators`).
- Tests: `tests/test_instance_start.py`, `tests/test_start_instance.py`, `tests/test_instance_file.py`, `tests/test_new_run.py`, and the cases T-0552 added in `tests/test_instance.py` for version 2.

## Acceptance Criteria

1. **The start writes version 2 exactly for `compile_settings`** (ADR-0198 decision 7): a start request that names `compile_settings` is prepared, validated by `instance.validate_kinded` and written as an `instance.json` of `schema_version` 2 holding that member; a request that names no kind, or names `c_kernel`, writes version 1 without the member, byte for byte as today for a request without it. The required set of ADR-0076, the accelerators and the covered contracts are unchanged for both kinds (decision 7: "its scope are unchanged").
2. **The exact request rule** (how a request states the kind and the version: e.g. whether the request carries `schema_version` 2 with `compile_settings`, or the start sets the version from the kind, and what happens to `c_kernel` and to a mismatch of version and kind) is the executor's reading of decision 7 together with ADR-0076 decision 4. Pick the reading that changes no given value silently (a refusal rather than a rewrite where the request is contradictory), state it in the docstrings of `instance_start.prepare` and `start_instance.start` and in the PR body. It adds no member, value or version beyond decision 4. If decision 7 cannot be read without a choice only the owner can make, return the question as described in Why.
3. **`instance_file.write`** accepts the content of a version-2 file (through `instance.parse_kinded`) and a version-1 file as today; any other version is refused as today. The reasons of refusal and their kinds are unchanged.
4. **`new_run`**: a version-2 start is reported `STARTED` with its run id as a version-1 start is; a request that the new rule refuses is reported with the existing outcome of that refusal (`INVALID` for `InvalidInstanceError`/`UnsupportedVersionError`). No new outcome unless the request rule of criterion 2 needs one; then name it in the PR body.
5. **No reader is widened** (ADR-0198 decision 8, column "Slice 2a"): every caller of rows 2 to 8 still refuses a version-2 `instance.json` with its existing kind; this task touches none of them. A test shows one strict reader (for example `instance.read`) refusing a run the new start wrote, so the boundary is pinned until T-0554.
6. **Tests** (D12): happy, error, branch and **negative** cases — a `compile_settings` start written as version 2 and read back by `instance.read_kinded`; a request without a kind and one with `c_kernel` written as version 1 without the member; an unknown kind; a contradictory version/kind pair by the rule of criterion 2; a version-2 request at an accelerator out of scope and with an uncovered `op_signature` (refused as today); `instance_file.write` of a version-2 content, of a version-3 content (refused). Every public function of the touched modules is tested; `hilclaw/` line and function coverage stay ≥ 80%. Existing tests stay unchanged except (a) list assertions under D21 — foreseen: `tests/test_instance_start.py::test_public_names_of_the_module`, `tests/test_start_instance.py::test_the_public_surface`, `tests/test_instance_file.py::test_signature_and_public_names` if a public name is added; (b) any existing test that asserts the start refuses a request holding `candidate_kind` (ADR-0198 decision 8, "Two narrowings"; T-0552 pinned the narrowing in `tests/test_instance.py`, e.g. `test_a_version_1_document_with_a_kind_is_invalid_at_every_entry`, which stays as it is since it is a rule of the file, not of the start) — rewrite only a start-level assertion to the new rule. List every such edit in the PR body.
7. **Unchanged behaviour**: every existing start, nightly start (`hilclaw/nightly.py`, `model_instances.py`, `model_check.py`, `model_graph.py`) and run writes exactly as before; the full test suite passes.
8. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0553`. Record the language (Python) and the reason in `## Result`.

## Out of Scope

- The run-level readers (T-0554), `spec.write` for version 3 and the `orchestration/` text (a later task), the evaluation tools and `build.json` writing (T-0555), CLAUDE.md's "C 커널" wording and the StandardScenarios scenario (slice 4).
- Any `ARCHITECTURE/` edit: ADR-0198 already decides this slice. If the executor finds a design decision ADR-0198 does not make and the slice needs, stop and report it in `## Result` rather than writing a new ADR in this task.
- Any value of `candidate_kind` beyond `c_kernel` and `compile_settings`; vendor-language kernels, quantization settings, model-level kinds (HQ-0088 ④).
- Starting `claude` in any form (D16); no test run (D25) is needed.

## Follow-ups

- T-0554 (run-level readers read version 2) and T-0555 (slice 3) follow in this batch. After them the planner creates the rest of slice 2b (`spec.write` composing a version-3 spec for the `technique-selector`, `orchestration/round-manager.md` steps 6/8 and `orchestration/agents/technique-selector.md`) and slice 4 (CLAUDE.md wording, scenario, runtime acceptance item); PLAN P3-6 is checked after slice 4.

## Result

- **Outcome**: DONE. PR #369 (Draft -> squash-merged), branch `claude/T-0553-compile-settings-instance-start`. Order check (D27 ①) at `origin/main` `170868bd`: no open PR, no open `nightly-failure` issue, no `실패` item in `PROCESS/RuntimeAcceptance.md`; unchanged from the Why.
- **Review**: 1 round, Approve (context-isolated `dev-reviewer`), 4 nits; nit 3 (cite HQ-0089 ④/③ and ADR-0198 "A-13 reading" in the PR body) applied, the others needed no change.
- **Language**: Python — the touched modules are existing Python modules of the 2nd-layer package.
- **Request rule (criterion 2)**: the request states its version and kind and the start sets neither. v1 without the member -> v1 as today; v1 + exact `"c_kernel"` -> v1 with that member left out (byte-identical to today's start without it); v2 + `"compile_settings"` -> v2 as given; v1 with another kind, v2 with `c_kernel`/another kind/no kind -> `InvalidInstanceError`; another version -> `UnsupportedVersionError` (both `invalid` in `new_run`). No new member, value, version or outcome.
- **Existing tests edited** (outside D21 and criterion 6 (b), forced by criteria 1 and 3, which make version 2 writable; the planner's foreseen list missed them): four "another version is unsupported" assertions moved from version 2 to version 3 — `tests/test_instance_start.py::test_a_document_of_another_version_is_unsupported`, `::test_another_version_without_coder_model_is_unsupported_before_anything`, `tests/test_start_instance.py::test_an_invalid_document_passes_through` (one case), `tests/test_instance_file.py` `REFUSED["version 2"]` -> `"version 3"`. No list assertion changed; no existing test asserted the start refusing `candidate_kind`.
- **Size**: 4 files in `hilclaw/` (~70 changed lines, mostly docstrings) + 4 test files.
- **Coverage**: touched modules `instance_start` 100%, `start_instance` 100%, `instance_file` 100%, `new_run` 99%.
- **Runtime acceptance items**: none (ADR-0198's item is handed over by slice 4).
- **HQ**: none.
- **Follow-ups**: none beyond the task's (T-0554, T-0555, the rest of slice 2b, slice 4).
