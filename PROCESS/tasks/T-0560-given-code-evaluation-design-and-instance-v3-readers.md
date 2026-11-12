---
id: T-0560
title: Apply HQ-0092 and HQ-0097 (b) for PLAN P3-11 — write the §9 ADR for evaluating given code (the bundle, its key, the out-of-loop evaluation and the round-0 baseline use), update the registers, and land its first code slice (validators and readers of `instance.json` version 3 with the optional `given_code` member, with no existing caller widened)
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, FR-19, FR-15, OD-33, OD-28, OD-8, "PLAN P3-11", HQ-0092, HQ-0097]
dependsOn: []
touchesFiles:
  - ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md
  - ARCHITECTURE/Requirements.md
  - ARCHITECTURE/OpenDecisionProposals.md
  - ARCHITECTURE/StandardScenarios.md
  - hilclaw/instance.py
  - hilclaw/instance_file.py
  - tests/test_instance.py
  - tests/test_instance_file.py
estimatedSize: {loc: 520, files: 6}
hq: []
---
## Why

**PLAN P3-11** (주어진 코드의 평가 진입점) is now the first unchecked, unskipped P3 item. Its owner holds are closed:

- **HQ-0092 (a)** (owner 2026-11-05, OD-33 ①): code the user gives is evaluated first, through P3-11; coder-written code at a vendor target comes with the vendor-language candidate kind. Uses (owner): inside the loop, the experiment step of FR-1; "루프 밖의 독립평가는 가설도입과, 측정 후 진행정도 측정에 사용 가능". Integrator's reading (OD-33 ①, FR-19 ①): given code serves the two out-of-loop uses and the round-0 baseline (OD-28).
- **HQ-0097 (b) (i)** (owner 2026-11-12, "권고대로 기록", reflected on `main` in `8dd8b780`): the code is a CAS blob with an `artifacts.json` record of the new `type` `given_code`, class `final`; `instance.json` gets the member `given_code` (the hash), optional and independent of `candidate_kind`; a file holding it has `schema_version` **3**, and readers accept 1, 2 and 3; a file without it stays 1 or 2 as today. **Left to P3-11's §9 ADR, and asked as an HQ if it enters the data plane (D23)**: the composition of the bundle (source, build method, inputs, expected output), the key of given code (OD-33 ⑥'s remaining part; LLM-wide code touches HQ-0096 ①), and whether an out-of-loop independent evaluation is a run with an instance.

**Why one task now (DRIVER §6 D20 ① and ④).** D20 ① puts the ADR with its first code slice. The entry point that builds, runs, checks, measures and records a bundle, the writer of the `given_code` blob and record, and the baseline use in round 0 all depend on decisions this ADR makes, so they are not created ahead; the ADR lists them with sizes and the planner creates them after this task lands. The first slice is the part every later slice reads and the owner's answer fully fixes: validators and readers of `instance.json` version 3. No natural boundary splits the ADR from this slice; together they stay inside DRIVER §5's recommendation.

**Order (DRIVER §6 D27 ①).** On `main` `68b6beb7`: no PR is open; the only open `nightly-failure` issue, #373, already has T-0559 (BLOCKED on HQ-0100), so no nightly task is due (NIGHTLY §6); `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패` (RA-0056 is `미확인`, so D27 ④ asks nothing yet); no P2-15 preparation is pending; P3-1 to P3-10, P3-13 and P3-14 are checked and P3-12 waits on OD-33 ⑤ and P3-11. If that has changed when this task runs, report it in `## Result` and stop before writing code.

**Open HQs (D27 ⑥/⑦).** Do not ask again or anticipate: HQ-0081 (S6 scale), HQ-0083 (fp16) and HQ-0085 (gates) — asked again only after RA-0056; **HQ-0095** (which execution is which measuring point; a vendor backend is not in the default table), **HQ-0096** (① the unit and metrics of LLM-level evaluation, ② the oracle at vendor targets), HQ-0100 (nightly #373). Because HQ-0095 and HQ-0096 ② are open, this ADR designs the evaluation for targets whose oracle and points are already decided (`cpu_standin`; `virtual_npu` per ADR-0197) and states what a vendor target adds once those are answered; it does not decide them. The `device_unavailable` backend kind (HQ-0097 (a)) is not part of this task. If the work shows a further owner-only part (in particular a bundle form, a key or a member that HQ-0097 did not approve), write the question in `## Result` in the DRIVER §8 structure (Korean: 쟁점, 선택지 (a)/(b)/…, 실행자의 권고, 막히는 것/막히지 않는 것), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0560-<slug>`, the `Task: T-0560` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0560/`, removed at the end).
  - §3 "BLOCKED 사유" and "승인된 열린 목록" (what is and is not a frame change; HQ-0097 (b) approves a frame, it does not make an open list).
  - §6 D27 (①, ⑥, ⑦), **D29** (toolchains: the executor checks the machine; real toolchains, no fakes) and **§9** (the ADR path: executor ADR + reviewer Approve + owner notice on #5).
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0092** and **HQ-0097** (question and `decision`, the verbatim source of the owner's answers and of the integrator's readings); HQ-0095, HQ-0096 (not to be anticipated).
- `PROCESS/PLAN.md` P3-11 (line ~72) and P3-12.
- `ARCHITECTURE/Requirements.md`: FR-19 (①, ②, ⑤), FR-15, FR-17, FR-1, FR-9, the OD-33 and OD-28 rows, and "**행 형식**" (the paragraph before the OD register).
- `ARCHITECTURE/OpenDecisionProposals.md`: header "**기록 규칙**"; § OD-33 (① and ⑥ in particular); § OD-28.
- `ARCHITECTURE/StandardScenarios.md`: S12 and its verdict row; the first paragraph of §검사 결과. `ARCHITECTURE/UsageCases.md` UC-E5.
- ADRs: `ADR-0194-od33-vendor-stack-evaluation-design.md` (decisions 2, 3, 5, 7, 10 V1 and V6, A-13 reading); `ADR-0193-od32-generalization-design.md` (decisions 2, 3, 4 — the target table, `instance_start`); `ADR-0197-od32-virtual-npu-oracle-and-instance-start.md`; `ADR-0198-od32-compile-settings-candidate-kind.md` (decision 7 the instance start and layout version, **decision 8 the reader table and the opt-in entries**, decision 9 the slice list — the model for this ADR's); `ADR-0005-od8-artifacts-record.md` (decision 5, `type`); `ADR-0195-p3-14-storage-cleanup-and-cas-gc.md` (decision 7, why class `final`); `ADR-0018-od8-instance-record-hw-profile.md` decision 2; `ADR-0024-od8-instance-record-layout-version.md` and `ADR-0030-od8-layout-stamp-read-order.md` (the layout version a version-3 file states); `ADR-0076-od8-instance-start-required-members.md`; `ADR-0119-od28-first-case-baseline.md` and `ADR-0113-od13-not-converged-best-baseline.md` (the round-0 baseline); `ADR-0129-od23-round-hypotheses-read.md` (FR-15 injection input); `ADR-0177-od18-od6-contract-table.md` (the contracts a given kernel can be checked against); `ADR-0001-od4-key-schema.md` (the key and the "Record format" section); `ADR-0196-od32-measurement-unit-list-and-run-result-v3.md` (results and units).
- Code: `hilclaw/instance.py` (`SCHEMA_VERSION`, `KIND_SCHEMA_VERSION`, `CANDIDATE_KINDS`, `_STATED_LAYOUT`, `_STRICT`, `_KINDED`, `Kinded`, `parse_kinded`, `validate_kinded`, `read_kinded`, `candidate_kind_of`, `layout_version_of_kinded`, `_checked`, `_candidate_kind`), `hilclaw/instance_file.py`, `hilclaw/instance_start.py`, `hilclaw/artifacts.py` (`RETENTION_CLASSES`, `add_record`), `hilclaw/cas.py`, `hilclaw/targets.py`, `hilclaw/check_tool.py`, `hilclaw/run_tool.py`, and the callers of the kinded readers (`hw_tool.py`, `journaled_tool.py`, `run_file_tools.py`, `spec_tool.py`) and of `instance.read`/`validate` (find them with a search; ADR-0198 decision 8 lists them as of its landing).

## Acceptance Criteria

1. **ADR-0200** (`ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md`), in the ADR-0001 record format, with Status separating **owner** content (HQ-0092, HQ-0097 (b) — cited, not subject to the objection window) from **this record's own** §9 decisions (executor + reviewer, owner notified on #5 with the 7-day objection window). Within the approved frame and adding no member, value or version beyond it, it decides:
   1. **The record of the owner's answers**: HQ-0092 (a) and HQ-0097 (b) (i) with its additions, cited from `STATE.json`, with no restatement beyond what the decisions below need.
   2. **The bundle**: what a given-code bundle holds (source, build method, inputs, expected output) and how each maps onto what exists (a contract of the contract table, the target's build settings, the harness's drawn inputs and reference as the oracle where one is decided). State whether the bundle as stored in the `given_code` blob has a format of its own and whether that is a data-plane frame (D23); if it is, write the HQ with the concrete form and decide only what does not depend on it.
   3. **The key of given code** (OD-33 ⑥'s remaining part): for code that implements an existing contract at an existing target, whether the existing `hw_profile` and `op_signature` serve as they are. If any other key is needed (for example LLM-wide code, HQ-0096 ①), do not invent it: name it as outside this ADR or as an HQ.
   4. **The two uses and their shape**: (a) the round-0 baseline (OD-28) of a run whose `instance.json` holds `given_code` — what round 0 does with it instead of or besides the bring-up coder call, and what of the round loop does not change; (b) the out-of-loop independent evaluation (hypothesis introduction, FR-15/FR-17 ②, and progress measurement after the loop) — whether it is a run with an instance (then it uses `given_code`) or not (then where its outcome goes, without a new data-plane file unless asked), and how its figures stay reference, not target (FR-15).
   5. **The entry point**: the user-facing command or tool that takes a bundle and builds, runs, checks, measures and records it; which existing operations it reuses (`correctness.check`, `sim.run`/`board.run` builds and timing, the CAS and `artifacts.json`); the targets it accepts now (those whose oracle and points are decided) and what a vendor target needs before it is accepted (HQ-0095, HQ-0096 ②, the rest of OD-33 ⑨ — named, not decided).
   6. **The instance start and the layout version**: how `given_code` reaches `instance.json` version 3 (ADR-0076, ADR-0198 decision 7), what layout version a version-3 file states (ADR-0024, ADR-0030), and that a file without the member is written exactly as today (version 1, or 2 for `compile_settings`).
   7. **A reader table** (as ADR-0198 decision 8): every caller of the `instance` readers, with what it does with a version-3 file after each slice. A caller that would treat a given-code run as an ordinary one must refuse it (as unsupported) until the slice that teaches it lands.
   8. **The slices** for the planner, with rough sizes against DRIVER §5 (≤ 600 LOC recommended, ≤ 10 files), the slice in which the entry point is verified with a real toolchain on the machine (D29: clang for `cpu_standin` is present), and where PLAN P3-11 is checked.
   9. **A-13 reading**: the frame elements used are exactly those HQ-0097 (b) approved; the `artifacts.json` `type` value `given_code` is the open name form of ADR-0005 decision 5; no approved open list of DRIVER §3 gains a value; nothing else changes the frame.
   10. **Consequences** (registers answered, runtime acceptance items if any, handed to `PROCESS/RuntimeAcceptance.md` through `## Result`, "Less exact, not edited" list) and **Boundaries** (vendor targets and HQ-0095/HQ-0096, LLM-level evaluation (P3-12, OD-33 ⑤), `device_unavailable` (HQ-0097 (a)), GPU or NPU memory figures, coder-written vendor code).
2. **Registers**, by their own recording rules — follow these rules, do not copy earlier task files' wording:
   - `ARCHITECTURE/Requirements.md`: the OD-33 row gains one `**확정분**` link to ADR-0200 and its `**잔여**` is rewritten in place (bundle composition and, if decided, the key); the OD-28 row likewise only if ADR-0200 answers part of it. Follow "행 형식": one link per new ADR, open parts rewritten in place, no restatement of the record, no dated paragraphs.
   - `ARCHITECTURE/OpenDecisionProposals.md`: § OD-33 gains one `**채택분**` line for ADR-0200; sub-questions ① and ⑥ get their state rewritten in place (bullet-head state word and the `→ …` ending, question text kept); § OD-28 likewise only where answered. Follow "기록 규칙".
   - `ARCHITECTURE/StandardScenarios.md`: re-check coverage by its rules (CLAUDE.md "문서 커버리지 재검사"), S12 step 2 and 5 notes and the verdict row only as far as the answered parts narrow them, and update §검사 결과 by its first paragraph.
3. **Code slice 1 — validators and readers only** (Python; record the language choice in the commit body):
   - `hilclaw/instance.py`: a document of `schema_version` 3 is valid exactly when it holds `given_code`, a CAS hash in the form the CAS uses (ADR-0005), and may hold `candidate_kind` under the same rule as version 2; versions 1 and 2 are unchanged and a `given_code` member in them is refused; any other version is refused as today. A public accessor returns the `given_code` hash of a run (`None` for a version-1 or version-2 file), and the layout version a version-3 file states follows ADR-0200.
   - `hilclaw/instance_file.py` only as far as ADR-0200 needs it for reading.
   - **No existing caller is widened in this slice**: the strict entries (`_STRICT`) and the kinded entries (`_KINDED`) keep refusing a version-3 file with their existing error kind, unless ADR-0200's reader table says otherwise for this slice; a new opt-in entry (in the manner of ADR-0198's `parse_kinded`/`read_kinded`) accepts 1, 2 and 3. State the choice in the ADR.
4. **Tests** (D12): extend `tests/test_instance.py` (and `tests/test_instance_file.py` if touched). Cover happy, error, branch and **negative** cases: version 3 without `given_code`; `given_code` of the wrong type, of a malformed hash, empty; `given_code` in a version-1 or version-2 file; version 3 with and without `candidate_kind`, with an out-of-list `candidate_kind`; a version-3 file handed to a strict and to a kinded entry; versions 0 and 4. Every public function of the touched modules is tested; `hilclaw/` line and function coverage stay ≥ 80%. Existing tests stay unchanged except: (a) list assertions under D21 — foreseen: `tests/test_instance.py::test_the_public_names` (new accessor and entry) and `tests/test_instance.py::test_nothing_of_the_module_holds_a_tolerance_value` if it enumerates the module's names, and any public-name set in `tests/test_instance_file.py` if that module gains a name; (b) a test asserting that version 3 is refused at an entry ADR-0200 makes accept it — rewrite it to the new rule. List every such edit in the PR body.
5. **Unchanged behaviour**: no writer writes a version-3 `instance.json`, a `given_code` blob or record in this task; every existing run, tool, nightly and model path behaves and writes exactly as before; the full test suite passes.
6. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0560`; §9 notice of ADR-0200 on issue #5 (English, no bare `@` mentions).

## Out of Scope

- The later slices: the entry point, the writer of the `given_code` blob and record, the instance start taking `given_code`, the round-0 baseline from given code, the out-of-loop evaluation's flow, any `orchestration/` text. Create no other task file.
- Vendor targets in the default backend table; the measuring-point assignment (HQ-0095); the vendor oracle and LLM-level unit (HQ-0096); `device_unavailable` (HQ-0097 (a)); GPU or NPU memory figures; P3-12.
- Any change to results, `step` values, `events.ndjson`, `STATE.json`, `spec.json` or `artifacts.json` validation (the `type` form is already open).
- Starting `claude` in any form (D16); no test run (D25) is needed for a reader slice.

## Follow-ups

- The planner creates the next slice(s) of ADR-0200 after this task lands, in the order its slice list gives; PLAN P3-11 is checked only when the entry point is verified with a real toolchain (PLAN P3-11: "답의 범위에서 코드 묶음을 받아 빌드·실행·검사·측정·기록까지 도는 진입점을 실제 툴체인으로 검증한다").

## Result
