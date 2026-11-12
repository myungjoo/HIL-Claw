---
id: T-0561
title: Land ADR-0200 slice 2 for PLAN P3-11 — the instance start takes a given C file, stores it in the CAS, writes `instance.json` version 3 with `given_code` and records the blob in `artifacts.json` (`type` `given_code`, class `final`)
phase: P3
status: IN_PROGRESS
commitMode: code
coversReq: [D27, FR-19, OD-33, "PLAN P3-11", HQ-0092, HQ-0097, ADR-0200]
dependsOn: []
touchesFiles:
  - hilclaw/start_instance.py
  - hilclaw/instance_start.py
  - hilclaw/new_run.py
  - hilclaw/instance_file.py
  - tests/test_start_instance.py
  - tests/test_instance_start.py
  - tests/test_new_run.py
  - tests/test_instance_file.py
estimatedSize: {loc: 300, files: 4}
hq: []
---
## Why

**PLAN P3-11** (주어진 코드의 평가 진입점) is the first unchecked, unskipped P3 item. Its §9 record, **ADR-0200**, landed with its first slice (readers of `instance.json` version 3) in T-0560 (PR #374, `786a7379`). ADR-0200 decision 8 orders the remaining slices 2, 3a, 3b, 4; this task is **slice 2**: the start takes a C file (ADR-0200 decisions 5 and 6, reader-table row 1, column "2 (start)").

**Order (DRIVER §6 D27 ①, D31 ①).** On `main` `bfb86882`: no PR is open; the only open `nightly-failure` issue, #373, already has T-0559 (BLOCKED on HQ-0100), so no nightly task is due (NIGHTLY §6); `PROCESS/RuntimeAcceptance.md` has no item whose `상태` is `실패`; no P2-15 preparation is pending; P3-11 is not skipped, so it goes before P3-15 to P3-17 (D31 ①). The D31 E4 brake does not apply: this is work PLAN P3-11 itself requires (DRIVER §6 D31 ②, the PLAN-item exception). If this has changed when the task runs, report it in `## Result` and stop before writing code.

**No new decision.** ADR-0200 fixes the content; this task applies it. The owner approved the frame (HQ-0097 (b) (i)); no member, value or version beyond it is added. Open HQs not to be anticipated or asked again: HQ-0081, HQ-0083, HQ-0085, HQ-0095, HQ-0096, HQ-0100. If the work shows an owner-only part ADR-0200 did not settle (D23), write the question in `## Result` in the DRIVER §8 structure (Korean: 쟁점, 선택지 (a)/(b)/…, 실행자의 권고, 막히는 것/막히지 않는 것), land the rest and return `DONE` (D27 ⑥).

## Required Reading

- `PROCESS/DRIVER.md`:
  - **§3-5 and §5**: branch `claude/T-0561-<slug>`, the `Task: T-0561` trailer and the PR body's last line, size (D30: ≤ 600 LOC recommended, ≤ 10 files, tests excluded), tests (D12), list assertions (D21), storage (D29: temporary files only under `${TMPDIR:-/tmp}/hilclaw-driver/T-0561/`, removed at the end).
  - §3 "BLOCKED 사유" and "승인된 열린 목록"; §6 D27 (⑥, ⑦), D31 ②; §9.
- `PROCESS/STATE.json` `humanQuestions`: **HQ-0097** (question and `decision`).
- `PROCESS/tasks/T-0560-given-code-evaluation-design-and-instance-v3-readers.md` `## Result`.
- **`ARCHITECTURE/decisions/ADR-0200-od33-given-code-evaluation.md`** — all of it; in particular decisions 2 (the bundle, ADR-0055 file rules), 5 (the order of the start: blob, then `instance.json`, then the record), 6 (the start takes `given_code`; version 3 for `c_kernel` with N = 1 only; `compile_settings` with `given_code` refused until slice 5; a request without a C file written exactly as today), 7 (reader table) and 8.
- ADRs: `ADR-0076-od8-instance-start-required-members.md` (refusal writes nothing, report order), `ADR-0115-od8-instance-start-performer.md`, `ADR-0155-od23-first-case-instance-start-command-line.md` (the `new_run` command line, its outcome table), `ADR-0198-od32-compile-settings-candidate-kind.md` decision 7 (how the start took `candidate_kind` — the model), `ADR-0025-od8-instance-file-write.md`, `ADR-0005-od8-artifacts-record.md` (decision 5, `type`), `ADR-0195-p3-14-storage-cleanup-and-cas-gc.md` decision 7 ("kept by construction"), `ADR-0055-od23-coder-output-form.md` (kernel-file rules).
- Code: `hilclaw/start_instance.py`, `hilclaw/instance_start.py`, `hilclaw/new_run.py`, `hilclaw/instance_file.py`, `hilclaw/instance.py` (`GIVEN_SCHEMA_VERSION`, `validate_given`, `parse_given`, `read_given`, `given_code_of`, `_given_code`), `hilclaw/cas.py` (`put_file`, `verify_blob`), `hilclaw/artifacts.py` (`add_record`, `RETENTION_CLASSES`), `hilclaw/model_instances.py` (calls `instance_start.prepare`; must behave as before).

## Acceptance Criteria

1. **The start takes a C file** (`hilclaw/start_instance.py`, `hilclaw/instance_start.py` as needed): a start given the path of a C file, for a request of kind `c_kernel` (no `candidate_kind`, or `c_kernel` at version 1) with `candidates_per_round` 1, stores the file with `cas.put_file`, writes `instance.json` of `schema_version` 3 holding `given_code` (the blob's digest) and records the blob with `artifacts.add_record` (`type` `given_code`, `round` 0, class `final`), in the order of ADR-0200 decision 5 (blob, `instance.json`, record). The written file passes `instance.validate_given`/`read_given`, states layout version 1 (ADR-0200 decision 6), and `instance.given_code_of` returns the digest.
2. **Refusals write nothing** (ADR-0076 decision 3; ADR-0200 decision 6): every check — the request's validity, scope and required set as today, a request that already holds `given_code` or states `schema_version` 3 itself (unless ADR-0200 says otherwise; state the choice in the docstring), `candidate_kind` `compile_settings` with a C file, `candidates_per_round` other than 1 with a C file, a C file that cannot be read or exceeds ADR-0055's 256 KiB per file — is made before any blob, `instance.json` or record is written. A failure between `instance.json` and the record leaves the blob and the instance and is reported (decision 5); test it with an injected failure.
3. **A request without a C file is unchanged**: version 1, or 2 for `compile_settings`, byte-for-byte as today; `model_instances` and every other caller of `prepare` behave as before.
4. **`new_run`** (`hilclaw/new_run.py`): accepts the path of a C file in a form the executor chooses (for example an optional second argument), states that form and any new or reused outcome kind in the module docstring and the PR body, and keeps every existing outcome, status and decoding rule for the one-argument form. ADR-0155's text describing "no option" becomes less exact; list it in `## Result` as a "less exact, not edited" follow-up rather than editing ADR-0155.
5. `hilclaw/instance_file.py` only as far as writing version 3 needs it (ADR-0200 decision 7 said it is unchanged until a writer writes version 3).
6. **Tests** (D12): happy, error, branch and **negative** cases for every new or changed public function: the three writes and their order; each refusal of criterion 2 leaving the data root empty of the run, the blob and the record; the injected failure between the instance and the record; `new_run` with and without the C file, with an unreadable or oversize file, with a `compile_settings` request and a C file. `hilclaw/` line and function coverage stay ≥ 80%. Existing tests stay unchanged except list assertions under D21 (foreseen: any public-name set of `tests/test_start_instance.py`, `tests/test_instance_start.py` or `tests/test_new_run.py` if a module gains a public name) and the T-0560 test in `tests/test_instance_start.py` that pins a start request holding `given_code` as refused, which may be rewritten to the new rule only if this slice changes what `prepare` does with such a request. List every such edit in the PR body.
7. **Unchanged elsewhere**: every reader of ADR-0200's reader table rows 2 to 6 still refuses version 3 (slice 3a teaches them); no round, tool, nightly or model path changes; the full test suite passes.
8. **Process**: dev-item-address steps, Draft PR, context-isolated review to Approve (≤ 14 rounds, D28), CI green, self squash-merge with the PR body's last line `Task: T-0561`. Record the language choice (Python) in the commit body.

## Out of Scope

- Slices 3a, 3b, 4 and 5 of ADR-0200 (run readers, placement of `(0, 1, 1)`, `orchestration/` text, the command `hilclaw.given_eval`, `compile_settings` with given code). No `ARCHITECTURE/` edit unless an executor-found contradiction with ADR-0200 forces one (then report it and stop).
- Vendor targets, HQ-0095, HQ-0096, `device_unavailable` (HQ-0097 (a)).
- Starting `claude` in any form (D16); no test run (D25).

## Follow-ups

- T-0562 (slice 3a) and T-0563 (slice 3b) follow in this batch; slice 4 is planned after them.

## Result
